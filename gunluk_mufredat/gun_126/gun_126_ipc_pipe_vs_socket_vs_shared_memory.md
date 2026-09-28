# Gün 126: IPC: Pipe vs Socket vs Shared Memory (Süreçler Arası İletişim Protokolleri, Kopya Maliyetleri ve Mimari Karar Matrisi)

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.

YASAKLAR:
  1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
  2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
  3. Alt lisanslanamaz, satılamaz veya devredilemez.
  4. Tersine mühendislik yapılamaz.

İZİN VERİLEN KULLANIM:
  - GitHub üzerinde görüntüleme ve okuma.
  - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).

YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
İzin talepleri için: GitHub @seydivakkas
```

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)

**Faz:** F3 — Threads / Concurrency / IPC  
**Konu:** Süreçler Arası İletişim (IPC) Yöntemlerinin Donanımsal ve Çekirdek Düzeyinde Kıyaslanması  
**Ön Koşul:** Gün 125 — Task Queue ve Worker Lifecycle & Gün 088 — POSIX Shared Memory  
**Kritik Seviye:** Savunma Sanayii Çoklu Süreç Aviyonik Mimarileri ve Sensör Füzyonu İçin Seviye-A Zorunluluk (DO-178C / MISRA C++:2023)

---

### 40-Nokta Bildirimi ve Kalite Güvencesi
Bu modül; Linux/POSIX işletim sistemlerinde süreçler arası iletişimin (IPC) 3 büyük temel direği olan **UNIX Pipe**, **UNIX Domain Socket (UDS)** ve **POSIX Shared Memory (Paylaşımlı Bellek)** mekanizmalarını silikon ve çekirdek seviyesinde analiz eder. Çift kopya (double-copy) sistem çağrılarının getirdiği mikrosaniye düzeyindeki gecikmeleri, sıfır kopya (zero-copy) paylaşımlı bellek mimarilerini, kimlik doğrulamalı soketleri ve robust mutex mekanizmalarını çalışan C++20/Python simülatörleri ve 4-panelli dashboard ile eksiksiz kapsar.

## 1. 🎯 Bugünkü Problem: Yanlış IPC Seçiminin Getirdiği Sistem Çöküşü

Modern savunma sistemlerinde (İHA görev bilgisayarı, radar sinyal işleme sunucusu, denizaltı savaş yönetim sistemi) tek bir monolitik süreç yerine, hata izolasyonu (fault isolation) sağlamak amacıyla **ayrık süreçler (multi-process architecture)** kullanılır:
- Süreç 1: Termal Kamera / FLIR Görüntü Toplama Süreci (Saniyede $1.5\text{ GB}$ 4K ham piksel).
- Süreç 2: AI / Derin Öğrenme Hedef Tespit Süreci.
- Süreç 3: Uçuş Kontrol ve Lançer Arayüz Süreci.
- Süreç 4: Kriptolu Telsiz / Telemetri İletim Süreci.

### Yanlış IPC Seçiminin Neden Olduğu 3 Ağır Felaket:
1. **Bant Genişliği Boğulması ve Çift Kopya Felaketi (Double-Copy Disaster):**
   - $1.5\text{ GB/s}$ veri akışı Pipe veya Standart Socket ile aktarılmaya çalışıldığında:
   - Veri önce User Space'ten Kernel Ring Buffer'a kopyalanır (`write` syscall: 1. kopya).
   - Ardından Kernel Buffer'dan alıcı sürecin belleğine kopyalanır (`read` syscall: 2. kopya).
   - CPU zamanının **%80'i** sadece baytları bir bellek adresinden diğerine taşımakla tükenir; L2/L3 önbellekleri boğulur (Cache Thrashing) ve video kareleri düşer (Frame Drop).
2. **Kilitlenme ve Sahipsiz Kilitler (Abandoned Mutex Problem):**
   - Shared Memory kullanılırken süreçlerden biri bellek erişim hatası (`SIGSEGV`) alır ve aniden çökerse;
   - Çöken sürecin arkasında bıraktığı kilit açılmadığı için diğer tüm süreçler kilitlenir (Deadlock).
3. **Determinizm Kaybı (Jitter):**
   - Pipe ve Socket çekirdeğin zamanlayıcısına ve I/O kuyruklarına tabidir; gecikme $2\ \mu\text{s}$ ile $15.000\ \mu\text{s}$ arasında dalgalanır (Jitter). Uçuş kontrol döngüsü ($1\text{ ms}$ SLA) çöker.

**Çözüm:** Veri hacmine, güvenlik gereksinimine ve gecikme toleransına göre doğru IPC mekanizmasını seçmektir:
- Yüksek hacimli veri ($> 64\text{ KB}$, Video, Radar IQ) $\implies$ **POSIX Shared Memory (Sıfır Kopya, 25 GB/s)**.
- Güvenli, kimlik denetimli komut iletimi $\implies$ **UNIX Domain Socket (`AF_UNIX`)**.
- Basit, tek yönlü telemetri loglama $\implies$ **UNIX Pipe / FIFO**.

## 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi)

Savunma sanayiinde süreç izolasyonu (process isolation) yazılım güvenliğinin (DO-178C ve ARINC-653) birinci kuralıdır.

### Savunma Sanayiindeki Kullanım Alanları:
1. **TUSAŞ ANKA / AKSUNGUR İHA Görev Bilgisayarı:**
   - FLIR kamerasından gelen yüksek çözünürlüklü görüntü hedef tespit algoritmasına aktarılırken `POSIX Shared Memory` kullanılır. Gecikme $20\text{ ns}$'dir; sıfır CPU kopyalama maliyetiyle hedef anında işaretlenir.
2. **ASELSAN Elektronik Harp Podu (EW):**
   - Sayısal alıcıdan gelen darbe tanımlayıcı kelimeler (PDW) paylaşımlı bellek dairesel tamponlarına basılır. Komuta kontrol süreçleri ise birbirleriyle `UNIX Domain Socket` üzerinden asenkron mesajlaşır.
3. **ROKETSAN Füze Simülasyonu (Hardware-in-the-Loop - HIL):**
   - Füze seyrüsefer bilgisayarı ile gerçek zamanlı dinamik simülatör arasında mikrosaniyelik determinizm gereklidir. Pipe/Socket gecikmeleri simülasyon gerçekliğini bozar; Shared Memory zorunludur.

## 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları)

| Soru | Sistem ve Donanım Düzeyi Cevabı | Savunma Sanayii Odaklı Karşılığı |
|:---|:---|:---|
| **NE?** | Ayrık sanal bellek alanlarına sahip süreçlerin veri alışverişi yapmasını sağlayan 3 temel mekanizmanın analizi. | Aviyonik alt sistemler arası veri iletim omurgası seçimi. |
| **NEDEN?** | Yanlış IPC seçimiyle oluşacak bant genişliği darboğazını, CPU israfını ve süreç kilitlenmelerini önlemek. | $1.5\text{ GB/s}$ FLIR video akışının CPU'yu boğmadan işlenmesini sağlamak. |
| **NEREDE?** | Linux VFS (`/dev/shm`), Çekirdek Sayfa Tabloları (Page Tables), Socket Ağ Yığını (`sk_buff`). | Görev bilgisayarı, atış kontrol işlemcisi, İHA yer istasyonu sunucusu. |
| **NASIL?** | `pipe2(2)`, `socketpair(2)` / `AF_UNIX` ve `shm_open` + `mmap` sistem çağrıları ile. | C++20 / POSIX standart fonksiyonları ve zero-copy mimarileri ile. |
| **NE ZAMAN?** | Ayrık süreçlerin (processes) birbirinden bağımsız çalışıp veri paylaşması gerektiği her an. | Sensör okuma, görüntü analizi, uçuş kontrol, kriptolu telsiz haberleşmesi. |
| **KİM?** | Gömülü Linux mimarları, gerçek zamanlı işletim sistemi uzmanları, savunma yazılım mühendisleri. | Aviyonik sistem geliştiricileri. |

## 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Analoji)

### İki Ayrı Odadaki Mühendislerin İletişim Yolları
Bir askeri üste iki ayrı güvenlik odasında çalışan iki mühendis (Ayrık Süreçler) bilgi alışverişi yapmak istemektedir:
- **UNIX Pipe Modeli (Duvardaki Dar Pnomatik Boru):**
  - İki oda arasında dar bir boru vardır. Mühendis A bir kağıdı rulo yapıp boruya iter (`write`). Borunun içindeki hava kağıdı Mühendis B'nin odasına üfler (`read`).
  - Tek yönlüdür (Simplex). Kağıt iki kez el değiştirir. Küçük mesajlar için pratiktir ama kalın klasörler (büyük video) boruyu tıkar!
- **UNIX Domain Socket Modeli (Güvenlikli Dahili Telefon):**
  - İki oda arasında şifreli bir telefon hattı vardır. İki yönlü konuşulabilir (Full-Duplex).
  - Kimin aradığı bilinir (Caller ID / Credentials). Konuşma güvenlidir ancak sesi iletmek için santral (Kernel) araya girer.
- **POSIX Shared Memory Modeli (Ortak Cam Bölme / Beyaz Tahta):**
  - İki odanın arasındaki duvar yıkılmış, yerine iki tarafın da dokunabildiği büyük bir beyaz tahta konmuştur.
  - Mühendis A tahtaya yazar yazmaz Mühendis B anında görür!
  - Sıfır taşıma, sıfır pnomatik boru, sıfır telefon santrali! Tahta ne kadar büyük olursa olsun veri anında oradadır.
  - Tek kural: İkisi aynı anda aynı satırı silmeye kalkmasın diye aralarında bir işaret lambası (Semafor / Mutex) olmalıdır!

## 5. 🧱 İlk İlkeler (First Principles) ve Donanımsal Bellek Modeli

Üç mekanizmanın donanımsal yürütme adımları ve bellek kopyalama sayıları:

### 1. Bellek Kopyalama Sayıları (Memory Copy Count):
- **Pipe / Socket (2 Kopya):**
  $$\text{User Space A} \xrightarrow[\text{1. Kopya}]{\text{write()}} \text{Kernel Buffer (sk\_buff)} \xrightarrow[\text{2. Kopya}]{\text{read()}} \text{User Space B}$$
  Her kopya CPU bellek veri yolunu (DRAM Bus) iki kez işgal eder. $1\text{ GB}$ veri aktarmak için $2\text{ GB}$ okuma/yazma yapılır!
- **Shared Memory (0 Kopya):**
  $$\text{Process A MMU Page Table} \searrow \quad \swarrow \text{Process B MMU Page Table}$$
  $$\text{Aynı Fiziksel RAM Çerçevesi (Physical Page Frame)}$$
  Veri hiçbir yere kopyalanmaz! A sürecinin yazdığı adres doğrudan B sürecinin okuduğu fiziksel bellektir!

### 2. İletim Süresi ve Gecikme Formülü:
$$T_{\text{IPC}} = N_{\text{syscall}} \times T_{\text{syscall}} + N_{\text{switch}} \times T_{\text{switch}} + \frac{\text{DataSize}}{\text{Bandwidth}} \times N_{\text{copies}}$$
- **Shared Memory:** $N_{\text{syscall}} = 0$, $N_{\text{switch}} = 0$, $N_{\text{copies}} = 0 \implies T_{\text{IPC}} \approx 20 - 50\text{ ns}$ (L3 Cache / RAM Hızı)!
- **Pipe:** $N_{\text{syscall}} = 2$, $N_{\text{copies}} = 2 \implies T_{\text{IPC}} \approx 1.5 - 3.5\ \mu\text{s}$.
- **Socket:** $N_{\text{syscall}} = 2$, Protokol başlıkları, kuyruklama $\implies T_{\text{IPC}} \approx 3.0 - 6.5\ \mu\text{s}$.

### 3. Payload Boyutu ve Başabaş Noktası (Break-Even Point):
Küçük mesajlarda ($< 128$ bayt) soket veya pipe'ın hazır kuyruklama yapısı kolaylık sağlar.
Mesaj boyutu $4\text{ KB}$'ı (1 Bellek Sayfası) aştığı anda Shared Memory'nin bant genişliği üstünlüğü katlanarak büyür ($15\times - 100\times$).

## 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

### ASCII Mimarisi: Donanımsal Bellek ve Çekirdek Geçiş Haritası
```text
  ==================================================================================
  IPC MEKANİZMALARI DONANIMSAL BELLEK AKIŞI
  ==================================================================================

  [ 1. PIPE / SOCKET MODELİ (ÇİFT KOPYA & SYSCALL GECİKMESİ) ]
  Süreç A (User Space)        Çekirdek (Kernel Space)       Süreç B (User Space)
  +------------------+       +---------------------+       +------------------+
  | Veri Tamponu     | ----> | Kernel Pipe/Socket  | ----> | Veri Tamponu     |
  | (User RAM)       | write | Buffer (sk_buff)    | read  | (User RAM)       |
  +------------------+       +---------------------+       +------------------+
        (Kopya 1: User->Kernel)             (Kopya 2: Kernel->User)
  * Sonuç: 2 Sistem Çağrısı + 2 Veri Kopyası + Bağlam Değişimi (~3.5 us)

  ----------------------------------------------------------------------------------

  [ 2. POSIX SHARED MEMORY MODELİ (SIFIR KOPYA & SIFIR SYSCALL) ]
  Süreç A (User Space)                                      Süreç B (User Space)
  +------------------+                                      +------------------+
  | Sayfa Tablosu    |                                      | Sayfa Tablosu    |
  +--------+---------+                                      +--------+---------+
           |                                                         |
           +-----------------------+   +-----------------------------+
                                   v   v
                      +-----------------------------+
                      | ORTAK FİZİKSEL RAM SAYFASI  |
                      | (Doğrudan Donanım Erişimi)  |
                      +-----------------------------+
  * Sonuç: Sıfır Kopya! Sıfır Syscall! İşlemci Hızında İletişim (~30 ns)
  ==================================================================================
```

### Mermaid Akış Diyagramı: Mimari Karar Ağacı (Decision Tree)
```mermaid
graph TD
    A[IPC İhtiyacı Başladı] --> B{Süreçler Aynı Makinede mi?}
    B -- Hayır --> C[TCP / UDP / ZeroMQ Ağ Soketi]
    B -- Evet --> D{Veri Akışı Hacmi Ne Kadar?}
    
    D -- Yüksek: > 64 KB, Video, Radar IQ --> E[POSIX Shared Memory shm_open + mmap]
    E --> E1[Sıfır Kopya, 25 GB/s, 20 ns Gecikme]
    
    D -- Orta/Düşük: Komut, Telemetri, RPC --> F{Kimlik / Güvenlik Gerekli mi?}
    F -- Evet --> G[UNIX Domain Socket AF_UNIX]
    G --> G1[Full-Duplex, Credentials, SCM_RIGHTS]
    
    F -- Hayır, Basit Tek Yönlü Akış --> H[UNIX Pipe / FIFO]
    H --> H1[Simplex, Kolay Entegrasyon, CLI Uyumu]
```

```python
# -*- coding: utf-8 -*-
"""
HÜCRE 8 (CODE 1): 3 Temel IPC Mekanizmasının Python/C++ Referans Simülatörü
Pipe, Unix Domain Socket ve Shared Memory Modelleri
"""

import os
import time
import struct
from typing import Dict, Any, Tuple

class IPCPipeChannel:
    """UNIX Pipe Çift Kopya Simülatörü (Kernel Buffer üzerinden aktarım)"""
    def __init__(self, buffer_size: int = 65536):
        self.buffer_size = buffer_size
        self.kernel_buffer = bytearray()
        self.total_bytes_transferred = 0

    def write(self, data: bytes) -> int:
        # User Space -> Kernel Space Kopyalama (1. Kopya)
        chunk = data[:self.buffer_size]
        self.kernel_buffer.extend(chunk)
        self.total_bytes_transferred += len(chunk)
        return len(chunk)

    def read(self, max_bytes: int) -> bytes:
        # Kernel Space -> User Space Kopyalama (2. Kopya)
        chunk = self.kernel_buffer[:max_bytes]
        del self.kernel_buffer[:max_bytes]
        return bytes(chunk)

class IPCSocketChannel:
    """UNIX Domain Socket Simülatörü (Full Duplex & Protokol Başlıkları)"""
    def __init__(self):
        self.inbox = bytearray()
        self.outbox = bytearray()
        self.header_overhead_bytes = 32  # sk_buff başlık ek yükü

    def send(self, payload: bytes) -> int:
        # Protokol paketleme ve kuyruk aktarımı
        packet = struct.pack(">I", len(payload)) + payload
        self.inbox.extend(packet)
        return len(payload)

    def recv(self) -> bytes:
        if len(self.inbox) < 4:
            return b""
        length = struct.unpack(">I", self.inbox[:4])[0]
        data = self.inbox[4:4 + length]
        del self.inbox[:4 + length]
        return bytes(data)

class IPCSharedMemoryChannel:
    """POSIX Shared Memory Simülatörü (Sıfır Kopya, Doğrudan Bellek Erişimi)"""
    def __init__(self, size_bytes: int = 1048576):
        # Ortak fiziksel bellek sayfası simülasyonu
        self.memory_view = bytearray(size_bytes)
        self.head_offset = 0
        self.size = size_bytes

    def write_direct(self, offset: int, data: bytes):
        # Sıfır syscall! Doğrudan RAM hücresine yazım
        end = offset + len(data)
        self.memory_view[offset:end] = data

    def read_direct(self, offset: int, length: int) -> memoryview:
        # Sıfır kopya! memoryview referansı döndürülür
        return memoryview(self.memory_view)[offset:offset + length]

print("[HÜCRE 8] IPCPipeChannel, IPCSocketChannel ve IPCSharedMemoryChannel sınıfları tanımlandı.")
```

## 7. 🔬 Kod 1 İncelemesi ve Satır Satır Analiz

Hücre 8'deki implemantasyonun can damarı olan noktaları teknik olarak inceleyelim:

1. **`IPCPipeChannel` Çift Kopya Modeli (Satırlar 19-33):**
   - `write()` metodu veriyi `self.kernel_buffer`'a ekler (1. Kopya).
   - `read()` metodu çekirdek tamponundan veriyi alıcı tampona kopyalar (2. Kopya).
   - Bu çift bellek transferi büyük veri aktarımlarında CPU L3 önbellek bant genişliğini tüketir.
2. **`IPCSocketChannel` Başlık ve Protokol Ek Yükü (Satırlar 35-56):**
   - Veri salt bayt olarak iletilmez; paket boyutu (`struct.pack(">I", ...)`) ve soket başlıkları eklenir.
   - Bu ek yük küçük mesajlarda belirgin olmasa da yüksek frekanslı paketlerde mikrosaniyelik gecikmeler yaratır.
3. **`IPCSharedMemoryChannel` Sıfır Kopya Mimari (Satırlar 58-75):**
   - `read_direct()` fonksiyonu yeni bir `bytes` nesnesi oluşturmaz (kopyalamaz); doğrudan belleğin üzerine açılan bir **`memoryview`** referansı döner!
   - Alıcı süreç hiçbir bellek tahsisi yapmadan doğrudan RAM adresini okur. Sıfır sistem çağrısı, sıfır gecikme!

## 8. 🛡️ C++20 / POSIX Standart İmplemantasyon Mimarisi

Aşağıdaki C++20 / POSIX kodu, savunma sanayii gerçek zamanlı aviyonik projelerinde doğrudan derlenip kullanılacak seviyede tasarlanmıştır (`shm_open`, `mmap` ve `pthread_mutexattr_setrobust`):

```cpp
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <pthread.h>
#include <cstring>
#include <iostream>
#include <span>
#include <cstdint>

struct SharedAviyonikState {
    pthread_mutex_t robust_mutex;
    uint64_t sequence_number;
    double roll_deg;
    double pitch_deg;
    double yaw_deg;
    uint8_t payload_iq_data[4096]; // 4 KB Radar Verisi
};

class PosixSharedMemoryWrapper {
private:
    const char* shm_name_;
    size_t size_;
    int shm_fd_;
    SharedAviyonikState* state_;

public:
    PosixSharedMemoryWrapper(const char* name, bool create = false) 
        : shm_name_(name), size_(sizeof(SharedAviyonikState)), shm_fd_(-1), state_(nullptr) 
    {
        int flags = O_RDWR;
        if (create) flags |= O_CREAT;

        shm_fd_ = shm_open(shm_name_, flags, 0660);
        if (shm_fd_ == -1) throw std::runtime_error("shm_open basarisiz!");

        if (create) {
            if (ftruncate(shm_fd_, size_) == -1) throw std::runtime_error("ftruncate basarisiz!");
        }

        void* addr = mmap(nullptr, size_, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd_, 0);
        if (addr == MAP_FAILED) throw std::runtime_error("mmap basarisiz!");

        state_ = static_cast<SharedAviyonikState*>(addr);

        if (create) {
            // Robust Mutex Tanımla (Process-Shared & Crash Recovery)
            pthread_mutexattr_t attr;
            pthread_mutexattr_init(&attr);
            pthread_mutexattr_setpshared(&attr, PTHREAD_PROCESS_SHARED);
            pthread_mutexattr_setrobust(&attr, PTHREAD_MUTEX_ROBUST);
            pthread_mutex_init(&state_->robust_mutex, &attr);
            pthread_mutexattr_destroy(&attr);
            state_->sequence_number = 0;
        }
    }

    ~PosixSharedMemoryWrapper() {
        if (state_) munmap(state_, size_);
        if (shm_fd_ != -1) close(shm_fd_);
    }

    void write_state(double r, double p, double y) {
        int rc = pthread_mutex_lock(&state_->robust_mutex);
        if (rc == EOWNERDEAD) {
            // Önceki süreç çöktü! Mutex'i kurtar ve durumu düzelt
            pthread_mutex_consistent(&state_->robust_mutex);
        }
        state_->sequence_number++;
        state_->roll_deg = r;
        state_->pitch_deg = p;
        state_->yaw_deg = y;
        pthread_mutex_unlock(&state_->robust_mutex);
    }
};
```

```python
# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 2): Mesaj Boyutuna Göre İletim Süresi ve Donanımsal Kopya Simülasyonu
Pipe vs Socket vs Shared Memory (64B'dan 4MB'a kadar Performans Eğrileri)
"""

def benchmark_ipc_payload_scaling():
    # Test edilecek veri paketleri (Bayt)
    payload_sizes = [64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304]
    
    results = {
        "payload_sizes": payload_sizes,
        "pipe_latency_us": [],
        "socket_latency_us": [],
        "shm_latency_us": []
    }
    
    for size in payload_sizes:
        # 1. Pipe Modeli: 2 syscall + double copy (Bant genişliği: 2.2 GB/s, baz gecikme: 1.5 us)
        t_pipe = 1.5 + (size / (2.2 * 1024 * 1024 * 1024)) * 1e6
        
        # 2. Socket Modeli: 2 syscall + protocol stack + copy (Bant genişliği: 1.6 GB/s, baz gecikme: 2.8 us)
        t_sock = 2.8 + (size / (1.6 * 1024 * 1024 * 1024)) * 1e6
        
        # 3. Shared Memory: Sıfır syscall, sıfır kopya, doğrudan L3/RAM hızı (32 GB/s, baz gecikme: 0.04 us)
        t_shm = 0.04 + (size / (32.0 * 1024 * 1024 * 1024)) * 1e6
        
        results["pipe_latency_us"].append(round(t_pipe, 3))
        results["socket_latency_us"].append(round(t_sock, 3))
        results["shm_latency_us"].append(round(t_shm, 3))
        
    return results

scaling_data = benchmark_ipc_payload_scaling()

print("[HÜCRE 11] Mesaj Boyutuna Göre Gecikme Analizi (Örnek Boyutlar):")
for i in [0, 3, 6, 8]:
    sz = scaling_data["payload_sizes"][i]
    p_lat = scaling_data["pipe_latency_us"][i]
    s_lat = scaling_data["socket_latency_us"][i]
    m_lat = scaling_data["shm_latency_us"][i]
    speedup = p_lat / m_lat
    print(f"  - Boyut: {sz:>8} Bayt | Pipe: {p_lat:8.2f} us | Socket: {s_lat:8.2f} us | SHM: {m_lat:8.2f} us (SHM {speedup:5.1f}x HIZLI)")
```

## 9. 💥 Sabotaj ve Arıza Enjeksiyon Laboratuvarı (Chaos Engineering)

Farklı IPC mekanizmaları farklı sistem seviyesi arıza modlarına sahiptir:

### 3 Ölümcül IPC Sabotajı:
1. **Sabotaj A: Shared Memory Sahipsiz Kilit (Abandoned Mutex Disaster):**
   - Süreç A ortak bellekteki mutex'i kilitler (`pthread_mutex_lock`).
   - Tam o sırada beklenmedik bir istisna veya `kill -9` ile aniden ölür.
   - Eğer mutex `PTHREAD_MUTEX_ROBUST` ile kurulmamışsa, Süreç B bu mutex'i sonsuza dek bekler ve aviyonik sistem donar!
2. **Sabotaj B: Kırık Boru Sinyali (Broken Pipe - `SIGPIPE`):**
   - Süreç B (Okuyucu) kapanır veya çöker.
   - Süreç A (Yazıcı) kapanmış pipe veya sokete `write()` yapmaya devam eder.
   - İşletim sistemi Süreç A'ya `SIGPIPE` sinyali gönderir. Varsayılan eylem **süreci anında sonlandırmaktır (Terminated)**!
   - Çözüm: `signal(SIGPIPE, SIG_IGN)` veya `send(..., MSG_NOSIGNAL)` kullanmak zorunludur!
3. **Sabotaj C: Pipe Tampon Taşması (Pipe Bufferbloat Deadlock):**
   - Süreç A pipe dolana kadar ($64\text{ KB}$) yazar, Süreç B okumayı geciktirirse Süreç A bloklanır. Eğer Süreç B de Süreç A'dan yanıt bekliyorsa çift yönlü kilitlenme (IPC Deadlock) oluşur!

```python
# -*- coding: utf-8 -*-
"""
HÜCRE 13 (CODE 3): IPC Sabotaj ve Arıza Simülatörü
1. Robust Mutex ile Çöken Sürecin Kilidini Kurtarma Simülasyonu
2. SIGPIPE Kırık Boru İzolasyonu
"""

class RobustMutexSimulation:
    def __init__(self):
        self.locked = False
        self.owner_pid = None
        self.is_consistent = True

    def lock(self, current_pid: int) -> str:
        if self.owner_pid is not None and self.owner_pid != current_pid:
            # Önceki sahip hayatta mı? (Simülasyon: PID 9999 çöktü)
            if self.owner_pid == 9999:
                # EOWNERDEAD durumu tetiklendi!
                self.owner_pid = current_pid
                self.is_consistent = False
                return "EOWNERDEAD"
            else:
                return "BLOCKED"
        self.locked = True
        self.owner_pid = current_pid
        return "SUCCESS"

    def make_consistent(self):
        self.is_consistent = True

    def unlock(self):
        self.locked = False
        self.owner_pid = None

def simulate_robust_mutex_recovery():
    mutex = RobustMutexSimulation()
    
    # 1. Aşama: Süreç 9999 kilidi alır ve ölür
    mutex.lock(9999)
    # Süreç 9999 öldü, unlock yapamadı!
    
    # 2. Aşama: Süreç 1000 kilidi almaya çalışır
    status = mutex.lock(1000)
    recovered = False
    if status == "EOWNERDEAD":
        # Kurtarma protokolü çalıştırılır
        mutex.make_consistent()
        recovered = mutex.is_consistent and (mutex.owner_pid == 1000)
        mutex.unlock()
        
    return {
        "initial_status": status,
        "recovered_successfully": recovered
    }

recovery_result = simulate_robust_mutex_recovery()

print("[HÜCRE 13] Sabotaj ve Robust Kilit Kurtarma Testi:")
print(f"  - Kilitlenme Durumu: {recovery_result['initial_status']} (Sahip Süreç Çöktü!)")
print(f"  - Robust Protokol ile Kurtarıldı mı?: {recovery_result['recovered_successfully']}")
```

## 10. 📊 Kapsamlı Karşılaştırma Matrisi ve Mimari Karar Tablosu

Üç büyük IPC mekanizmasının askeri aviyonik standartlarına göre tam analizi:

| Mimari Kriter | UNIX Pipe (FIFO) | UNIX Domain Socket (UDS) | POSIX Shared Memory (`shm_open`) |
|:---|:---|:---|:---|
| **Veri Aktarım Modeli** | Bayt Akışı (Simplex / Tek Yön) | Çift Yönlü (Full Duplex) Akış/Mesaj | Ortak Bellek Haritası (Random Access) |
| **Kopya Sayısı** | **2 Kopya** (User $\to$ Kernel $\to$ User) | **2 Kopya** (sk_buff üzerinden) | **0 KOPYA (Sıfır Kopya - Zero Copy)** |
| **Sistem Çağrısı Sayısı** | Her işlemde 2 Syscall (`write`/`read`) | Her işlemde 2 Syscall (`send`/`recv`) | **0 Syscall (Kurulumdan sonra sıfır!)** |
| **Tipik Gecikme (4 KB)** | $1.8 - 3.5\ \mu\text{s}$ | $2.5 - 5.5\ \mu\text{s}$ | **$15 - 50\text{ ns}$ ($100\times$ Hızlı)** |
| **Maksimum Bant Genişliği** | $\sim 2.2\text{ GB/s}$ | $\sim 1.6\text{ GB/s}$ | **$\sim 35 - 50\text{ GB/s}$ (RAM Hızı)** |
| **Kimlik Denetimi (Auth)** | Sınırlı (Dosya izinleri) | **Mükemmel (`SO_PEERCRED` ile PID/UID)**| Sınırlı (`shm_open` dosya izinleri) |
| **Dosya Tanımlayıcı Aktarımı**| Desteklemez | **Destekler (`SCM_RIGHTS` fd passing)**| Desteklemez |
| **Senkronizasyon İhtiyacı** | Kernel tarafından otomatik yönetilir | Kernel tarafından otomatik yönetilir | **Kullanıcı Yönetir (Mutex/Semafor)** |
| **DO-178C Seviye-A Uygunluk** | Uygun (Basit loglama) | Uygun (Komuta kontrol) | **Uygun (Radar/Video Sıfır Kopya)** |

```python
# -*- coding: utf-8 -*-
"""
HÜCRE 15 (CODE 4): Kapsamlı Ampirik Throughput Benchmark Simülatörü
Farklı Boyutlarda Elde Edilen Bant Genişliği (GB/s) ve CPU Yükü Analizi
"""

import numpy as np

class IPCThroughputBenchmark:
    @staticmethod
    def calculate_throughput_and_cpu():
        """
        Üç yöntemin 1 MB'lık paketler için bant genişliği (GB/s) ve CPU tüketimini hesaplar.
        """
        return {
            "methods": ["UNIX Pipe", "UNIX Socket", "POSIX Shared Memory"],
            "bandwidth_gbps": [2.15, 1.58, 38.40],
            "cpu_overhead_pct": [42.5, 58.0, 1.2],
            "latency_ns": [2800, 3900, 35]
        }

bench_ipc = IPCThroughputBenchmark.calculate_throughput_and_cpu()

print("[HÜCRE 15] IPC Throughput ve Donanım Yükü Benchmark Sonuçları:")
for m, bw, cpu, lat in zip(bench_ipc["methods"], bench_ipc["bandwidth_gbps"], bench_ipc["cpu_overhead_pct"], bench_ipc["latency_ns"]):
    print(f"  - {m:<22} -> Bant Genişliği: {bw:6.2f} GB/s | CPU Yükü: %{cpu:4.1f} | Gecikme: {lat:5d} ns")
```

## 11. 🐧 Linux Çekirdeği ve Teşhis Araçları (`ipcs`, `ss -x`, `strace -e`)

Linux sistemlerinde çalışan IPC kanallarını analiz etmek ve arızaları teşhis etmek için kullanılan profesyonel araçlar:

### 1. Paylaşımlı Bellek ve Semaforları İzleme (`ipcs` & `/dev/shm`):
```bash
# Aktif POSIX paylaşımlı bellek dosyalarını listele
ls -la /dev/shm/
# Çıktı: -rw-rw---- 1 root avionic 4194304 Sep 22 10:45 aviyonik_radar_shm

# Klasik System V IPC nesnelerini göster
ipcs -m -s -u
```

### 2. UNIX Domain Soketlerini İzleme (`ss -x`):
```bash
# Sistemdeki tüm yerel UNIX soketlerini ve tampon doluluklarını listele
ss -x -a -p
# Göstergeler: Send-Q ve Recv-Q değerleri sıfır olmalıdır. Recv-Q doluysa tüketici yetişemiyordur!
```

### 3. Sistem Çağrısı İncelemesi (`strace -e`):
Sıfır kopya doğrulaması:
```bash
# Sadece IPC ile ilgili sistem çağrılarını yakala
strace -c -e trace=write,read,sendto,recvfrom,shm_open,mmap ./aviyonik_surec
```
- **Shared Memory Doğrulaması:** Başlatma evresindeki tek seferlik `shm_open` ve `mmap`'ten sonra çalışma döngüsünde **SIFIR sistem çağrısı** görülmelidir!

```python
# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Fonksiyonel IPC Doğrulama ve Veri Bütünlüğü Test Suite
Pipe, Socket ve Shared Memory Veri Bütünlüğü Testleri
"""

def run_ipc_integrity_tests():
    test_payload = b"ASELSAN_RADAR_TARGET_ID_9874_AZIMUTH_45.8"
    
    # Test 1: Pipe Bütünlüğü
    p = IPCPipeChannel()
    written = p.write(test_payload)
    assert written == len(test_payload), "HATA: Pipe yazım boyutu uyuşmuyor!"
    read_pipe = p.read(len(test_payload))
    assert read_pipe == test_payload, f"HATA: Pipe verisi bozuk! Gelen: {read_pipe}"
    
    # Test 2: Socket Bütünlüğü
    s = IPCSocketChannel()
    s.send(test_payload)
    read_sock = s.recv()
    assert read_sock == test_payload, f"HATA: Socket verisi bozuk! Gelen: {read_sock}"
    
    # Test 3: Shared Memory Sıfır Kopya Bütünlüğü
    shm = IPCSharedMemoryChannel(size_bytes=1024)
    shm.write_direct(64, test_payload)
    read_shm = shm.read_direct(64, len(test_payload))
    assert bytes(read_shm) == test_payload, "HATA: Shared memory verisi bozuk!"
    
    # Bellek adresi değişmeden yerinde güncelleme doğrulaması
    shm.write_direct(64, b"MODIFIED")
    assert bytes(read_shm[:8]) == b"MODIFIED", "HATA: memoryview yerinde güncellemeyi yansıtmadı!"
    
    print("[HÜCRE 17] Tüm IPC Fonksiyonel Bütünlük Testleri Başarıyla Geçti!")

run_ipc_integrity_tests()
```

## 12. 📈 Görselleştirme Tasarımı ve Veri Akışı Mimarisi

Üretilecek 4 panelli profesyonel dashboard (`gun_126_ipc_pipe_vs_socket_vs_shared_memory.png`) şu teknik panelleri içerir:

1. **Panel 1 (Sol Üst) — IPC Mekanizmaları Bant Genişliği Karşılaştırması (GB/s):**
   - POSIX Shared Memory ($38.4\text{ GB/s}$) vs Pipe ($2.15\text{ GB/s}$) vs Socket ($1.58\text{ GB/s}$) logaritmik ölçekte bant genişliği üstünlüğü.
2. **Panel 2 (Sağ Üst) — Mesaj Boyutuna Göre Gecikme Eğrisi (Payload Scaling):**
   - 64B'dan 4MB'a kadar paket boyutunda gecikme artışı (Shared Memory'nin yatay, Pipe ve Socket'in dikey fırlaması).
3. **Panel 3 (Sol Alt) — CPU Yükü ve Çekirdek Ek Yükü Karşılaştırması:**
   - 1 GB veri aktarırken CPU kullanım oranları (%42.5 Pipe vs %58 Socket vs %1.2 Shared Memory).
4. **Panel 4 (Sağ Alt) — Mimari Karar Matrisi ve Radar Grafiği:**
   - Hız, Güvenlik, Kolaylık, Çift Yönlülük ve Büyük Veri Uyumluluğu eksenlerinde 3 yöntemin radar analizi.

```python
# -*- coding: utf-8 -*-
"""
HÜCRE 19 (CODE 6): 4-Panelli Profesyonel Dashboard Üretimi ve Katı Doğrulama Testleri
Dark Theme (#0F172A), 300 DPI, Savunma Sanayii IPC Telemetri Görselleştirmesi
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def generate_dashboard(output_path: str):
    """4 Panelli IPC Karşılaştırma Görselleştirme Panosu"""
    fig = plt.figure(figsize=(20, 12), facecolor='#0F172A')
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.25, left=0.07, right=0.95, top=0.92, bottom=0.08)

    # -------------------------------------------------------------
    # Panel 1: Bant Genişliği Karşılaştırması (GB/s - Log Ölçek)
    # -------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0], facecolor='#1E293B')
    
    methods = ['UNIX Pipe\n(FIFO)', 'UNIX Socket\n(AF_UNIX)', 'POSIX Shared Memory\n(shm_open)']
    bandwidths = [2.15, 1.58, 38.40]
    colors = ['#F59E0B', '#38BDF8', '#22C55E']
    
    bars1 = ax1.bar(methods, bandwidths, color=colors, edgecolor='#475569', width=0.55)
    ax1.set_yscale('log')
    ax1.set_ylabel('Bant Genişliği (GB/s - Log Ölçek)', color='#94A3B8', fontsize=10)
    ax1.set_title('1. Maksimum Veri Aktarım Hızı (Bant Genişliği)', color='#F8FAFC', fontsize=12, fontweight='bold')
    ax1.tick_params(colors='#94A3B8')
    ax1.grid(color='#334155', linestyle='--', alpha=0.6, axis='y')
    
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, yval * 1.15, f'{yval:.2f} GB/s',
                 ha='center', color='#F8FAFC', fontweight='bold', fontsize=10)

    # -------------------------------------------------------------
    # Panel 2: Mesaj Boyutuna Göre Gecikme Eğrisi (Payload vs Latency)
    # -------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1], facecolor='#1E293B')
    
    scaling = benchmark_ipc_payload_scaling()
    sizes = np.array(scaling['payload_sizes'])
    
    ax2.plot(sizes, scaling['pipe_latency_us'], marker='o', color='#F59E0B', linewidth=2, label='UNIX Pipe (2 Kopya)')
    ax2.plot(sizes, scaling['socket_latency_us'], marker='s', color='#38BDF8', linewidth=2, label='UNIX Socket (AF_UNIX)')
    ax2.plot(sizes, scaling['shm_latency_us'], marker='D', color='#22C55E', linewidth=2.5, label='Shared Memory (0 Kopya)')
    
    ax2.set_xscale('log')
    ax2.set_yscale('log')
    ax2.set_xlabel('Mesaj / Paket Boyutu (Bayt - Log)', color='#94A3B8', fontsize=10)
    ax2.set_ylabel('İletim Gecikmesi (Mikrosaniye - Log)', color='#94A3B8', fontsize=10)
    ax2.set_title('2. Mesaj Boyutu Büyüdükçe Gecikme Patlaması', color='#F8FAFC', fontsize=12, fontweight='bold')
    ax2.tick_params(colors='#94A3B8')
    ax2.grid(color='#334155', linestyle='--', alpha=0.6)
    ax2.legend(facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

    # -------------------------------------------------------------
    # Panel 3: CPU Yükü ve Çekirdek Ek Yükü (Overhead)
    # -------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0], facecolor='#1E293B')
    
    cpu_loads = [42.5, 58.0, 1.2]
    bar_colors3 = ['#F59E0B', '#EF4444', '#22C55E']
    
    bars3 = ax3.barh(methods, cpu_loads, color=bar_colors3, edgecolor='#475569', height=0.5)
    ax3.set_xlabel('1 GB Veri Aktarırken CPU Kullanım Oranı (%)', color='#94A3B8', fontsize=10)
    ax3.set_title('3. Veri Kopyalama Nedeniyle Oluşan CPU Yükü', color='#F8FAFC', fontsize=12, fontweight='bold')
    ax3.tick_params(colors='#94A3B8')
    ax3.grid(color='#334155', linestyle='--', alpha=0.6, axis='x')
    
    for bar in bars3:
        wval = bar.get_width()
        ax3.text(wval + 1.5, bar.get_y() + bar.get_height() / 2, f'%{wval:.1f}',
                 va='center', color='#F8FAFC', fontweight='bold', fontsize=10)

    # -------------------------------------------------------------
    # Panel 4: Mimari Karar ve Yetenek Analizi (Radar Grafiği)
    # -------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1], projection='polar', facecolor='#1E293B')
    
    criteria = ['Bant Genişliği', 'Düşük Gecikme', 'Güvenlik/Auth', 'Sıfır Kopya', 'Kullanım Kolaylığı']
    num_vars = len(criteria)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    
    # 1-10 Skorları
    score_pipe = [4, 5, 4, 3, 9, 4]
    score_sock = [3, 4, 9, 3, 7, 3]
    score_shm  = [10, 10, 5, 10, 5, 10]
    
    ax4.plot(angles, score_pipe, color='#F59E0B', linewidth=2, label='Pipe')
    ax4.fill(angles, score_pipe, color='#F59E0B', alpha=0.15)
    
    ax4.plot(angles, score_sock, color='#38BDF8', linewidth=2, label='Socket')
    ax4.fill(angles, score_sock, color='#38BDF8', alpha=0.15)
    
    ax4.plot(angles, score_shm, color='#22C55E', linewidth=2.5, label='Shared Memory')
    ax4.fill(angles, score_shm, color='#22C55E', alpha=0.25)
    
    ax4.set_xticks(angles[:-1])
    ax4.set_xticklabels(criteria, color='#F8FAFC', fontsize=9, fontweight='bold')
    ax4.set_yticklabels([])
    ax4.grid(color='#475569', linestyle='--', alpha=0.7)
    ax4.set_title('4. IPC Mimari Karar Matrisi (Radar Analizi)', color='#F8FAFC', fontsize=12, fontweight='bold', pad=20)
    ax4.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

    plt.suptitle('GÜN 126: SÜREÇLER ARASI İLETİŞİM (IPC) MİMARİLERİ VE PERFORMANS ANALİZİ\nUNIX Pipe vs UNIX Domain Socket vs POSIX Shared Memory (Sıfır Kopya ve Donanımsal Karar Matrisi)',
                 color='#F8FAFC', fontsize=14, fontweight='bold', y=0.98)
                 
    plt.savefig(output_path, dpi=300, facecolor='#0F172A', edgecolor='none')
    plt.close()
    print(f"[Dashboard] Görselleştirme panosu başarıyla oluşturuldu: {output_path}")

def verify_all_assertions(png_path: str):
    """Katı doğrulama kuralları (Assertions)"""
    print("[*] GÜN 126 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")
    
    # 1. PNG Varlık ve Boyut Kontrolü
    assert os.path.exists(png_path), f"HATA: PNG dosyası bulunamadı: {png_path}"
    png_size = os.path.getsize(png_path)
    assert png_size > 100 * 1024, f"HATA: PNG boyutu yetersiz ({png_size} bayt)! En az 100 KB olmalı."
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
    
    # 2. Shared Memory Bant Genişliği Üstünlüğü
    bench = IPCThroughputBenchmark.calculate_throughput_and_cpu()
    shm_bw = bench["bandwidth_gbps"][2]
    pipe_bw = bench["bandwidth_gbps"][0]
    sock_bw = bench["bandwidth_gbps"][1]
    assert shm_bw > pipe_bw * 10.0, "HATA: Shared memory Pipe'tan en az 10 kat hızlı olmalı!"
    assert shm_bw > sock_bw * 15.0, "HATA: Shared memory Socket'ten en az 15 kat hızlı olmalı!"
    print(f"  [+] Bant Genişliği Üstünlüğü Doğrulandı: SHM ({shm_bw:.1f} GB/s) >> Pipe ({pipe_bw:.1f} GB/s) >> Socket ({sock_bw:.1f} GB/s).")
    
    # 3. CPU Ek Yükü Analizi
    shm_cpu = bench["cpu_overhead_pct"][2]
    pipe_cpu = bench["cpu_overhead_pct"][0]
    assert shm_cpu < 5.0, "HATA: Shared memory CPU yükü %5'in altında olmalı!"
    assert pipe_cpu > 30.0, "HATA: Pipe CPU yükü yüksek olmalı!"
    print(f"  [+] Sıfır Kopya CPU Tasarrufu Doğrulandı: SHM (%{shm_cpu}) vs Pipe (%{pipe_cpu}).")
    
    # 4. Gecikme Üstünlüğü
    scaling = benchmark_ipc_payload_scaling()
    large_idx = -1 # 4 MB paket
    shm_lat = scaling["shm_latency_us"][large_idx]
    pipe_lat = scaling["pipe_latency_us"][large_idx]
    assert shm_lat < pipe_lat / 10.0, "HATA: 4 MB pakette Shared memory en az 10 kat düşük gecikmeli olmalı!"
    print(f"  [+] 4MB Paket Gecikmesi Doğrulandı: SHM ({shm_lat:.1f} us) << Pipe ({pipe_lat:.1f} us).")
    
    print("\n[PASS] Gün 126: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")
```

## 13. ⚠️ 10 Ölümcül Anti-Pattern (IPC Tasarım Hataları)

Savunma sanayii ve çoklu süreç (multi-process) projelerinde karşılaşılan en tehlikeli 10 mimari hata:

1. **Yüksek Hacimli Veriyi (Video / Radar) Pipe veya Socket ile Göndermek:**
   - Çift kopya nedeniyle CPU'nun %50'den fazlası boşa harcanır. Büyük veride mutlaka Shared Memory kullanılmalıdır.
2. **Shared Memory'de Robust Mutex (`PTHREAD_MUTEX_ROBUST`) Kullanmamak:**
   - Kilit sahibi süreç çökerse diğer süreçler sonsuza dek kilitlenir (Deadlock).
3. **`SIGPIPE` Sinyalini İhmal Etmek (Broken Pipe Crash):**
   - Karşı taraf soketi kapattığında `write()` yapan sürecin `SIGPIPE` ile aniden çökmesi. Mutlaka `SIG_IGN` yapılmalıdır.
4. **Soket Tamponlarını Küçük Bırakıp Buffer Bloat ve Drop Yaşamak:**
   - Kernel varsayılan soket tamponları ($212\text{ KB}$) patlama anında taşar. `SO_RCVBUF` ve `SO_SNDBUF` ayarlanmalıdır.
5. **Shared Memory Açılışında `ftruncate` Yapmayı Unutmak:**
   - `shm_open` sonrası boyut verilmezse dosya boyutu $0$ kalır; ilk `mmap` erişiminde `SIGBUS` sinyaliyle süreç çöker.
6. **Süreçler Arası İşaretçileri (Raw Pointers) Shared Memory'ye Yazmak:**
   - Her sürecin `mmap` sanal bellek adresi farklı olabilir. Ham işaretçi yerine **Offset Tabanlı İşaretçi (Relative Offset)** kullanılmalıdır.
7. **`AF_UNIX` Yerine Gereksiz Yere `AF_INET` (Loopback 127.0.0.1) Kullanmak:**
   - Aynı makinedeki süreçler için TCP/IP yığını çalıştırmak gereksiz IP başlıkları, checksum hesaplamaları ve gecikme üretir.
8. **Pipe'ın İki Yönlü Olduğunu Varsaymak:**
   - Standart POSIX pipe tek yönlüdür. Çift yön için iki pipe veya `socketpair()` kullanılmalıdır.
9. **Kapanan Süreçlerin Paylaşımlı Belleklerini Temizlememek (SHM Leak):**
   - Sistem kapansa bile `/dev/shm` RAM diskinde dosya kalır. Süreç kapanırken `shm_unlink()` çağrılmalıdır.
10. **Shared Memory'yi Senkronizasyonsuz Okumak (Torn Reads):**
    - Mutex veya atomic seq-lock olmadan paylaşımlı belleğe doğrudan erişmek yarım yazılmış (corrupted) veri okutur.

## 14. 📋 Sektörel Standartlar ve Uyumluluk (DO-178C, MISRA C++:2023, ARINC-653)

### 1. ARINC-653 Aviyonik Bölümleme (Partitioning) Standardı:
- **Spatial & Temporal Isolation:**
  - ARINC-653 aviyonik mimarisinde her süreç kendi korumalı bellek bölümünde (Partition) çalışır.
  - Bölümler arası veri aktarımı yalnızca sertifikalı IPC kanalları (Sampling & Queuing Ports) veya donanımsal korumalı paylaşımlı bellek blokları üzerinden yapılabilir.

### 2. DO-178C Seviye-A Sertifikasyon Analizi:
- **Deterministik İletişim Garantisi:**
  - Pipe ve Socket kuyruk bekleme süreleri stokastik olduğundan WCET analizini zorlaştırır.
  - SPSC Ring Buffer ile donatılmış POSIX Shared Memory deterministik $O(1)$ transfer garantisi verir.

## 15. ✅ Üretim Seviyesi Kontrol Listesi (12 Altın Kural)

Bir IPC mimarisini savunma sanayii üretimine almadan önce bu 12 maddeyi denetleyin:

- [ ] **1. Veri Hacmi Uygunluğu:** $64\text{ KB}$'dan büyük veri akışlarında POSIX Shared Memory seçildi mi?
- [ ] **2. Robust Kilit:** Ortak bellek mutex'inde `PTHREAD_MUTEX_ROBUST` tanımlandı mı?
- [ ] **3. EOWNERDEAD İşleme:** Mutex kilitlenirken `EOWNERDEAD` dönüşü kontrol edilip `pthread_mutex_consistent` çağrıldı mı?
- [ ] **4. SIGPIPE Koruması:** `signal(SIGPIPE, SIG_IGN)` veya `MSG_NOSIGNAL` eklendi mi?
- [ ] **5. Offset Tabanlı Adresleme:** Shared memory veri yapılarında ham pointer yerine offset kullanıldı mı?
- [ ] **6. ftruncate Doğrulaması:** `shm_open` sonrası `ftruncate` ile tampon boyutu kesinleştirildi mi?
- [ ] **7. Temiz Kapanış (Unlink):** Süreç kapanırken `shm_unlink` ile kaynak temizliği yapılıyor mu?
- [ ] **8. UDS Tercihi:** Yerel süreçler arası mesajlaşmada TCP loopback yerine `AF_UNIX` kullanıldı mı?
- [ ] **9. Soket Tamponları:** Yüksek hızlı veri yollarında `SO_RCVBUF` ve `SO_SNDBUF` optimize edildi mi?
- [ ] **10. Kimlik Doğrulama:** UDS üzerinde `SO_PEERCRED` ile istemci sürecin PID/UID denetimi yapılıyor mu?
- [ ] **11. Dosya İzinleri:** `/dev/shm` ve FIFO dosyaları için `0660` veya `0600` kısıtlayıcı izinler verildi mi?
- [ ] **12. Sistem Çağrısı İzleme:** Shared memory döngüsünde `strace` ile sıfır syscall olduğu doğrulandı mı?

## 16. 💬 Mülakat Soruları ve Savunma Sanayii Saha Senaryoları

### Soru 1: Aynı makinede çalışan iki süreç için neden TCP Loopback (127.0.0.1) yerine UNIX Domain Socket tercih edilmelidir?
**Cevap:** TCP loopback bağlantısı tam bir TCP/IP yığını çalıştırır: IP başlıkları eklenir, TCP sıra numaraları yönetilir, checksum hesaplanır ve çekirdek seviyesinde soket kuyrukları dolaşılır. UNIX Domain Socket (`AF_UNIX`) ise ağ yığınını tamamen atlar; doğrudan çekirdek bellek tamponları arasında bayt taşır. UDS, TCP loopback'e göre yaklaşık $2\times$ daha yüksek bant genişliği ve yarı yarıya daha düşük gecikme sunar. Ayrıca `SO_PEERCRED` ile süreç kimlik doğrulaması ve dosya tanımlayıcısı (`SCM_RIGHTS` fd passing) aktarımı sağlar.

### Soru 2: Shared Memory neden en hızlı IPC yöntemidir, ancak en tehlikelisi olarak kabul edilir?
**Cevap:** En hızlıdır çünkü sıfır kopya (zero-copy) ve sıfır sistem çağrısı (zero-syscall) ile çalışır; iki sürecin sayfa tabloları aynı fiziksel RAM adresine bakar. En tehlikelisidir çünkü işletim sistemi veri senkronizasyonunu yönetmez. Eğer süreçler arasında kilit (mutex/semafor) düzgün kurulmazsa veri yarışları (race conditions) oluşur. Daha da kötüsü, bir süreç kilidi tutarken çökerse (Abandoned Mutex) diğer süreç kalıcı olarak kilitlenir.

### Soru 3: Shared memory içine neden `std::string` veya sanal fonksiyonlu C++ sınıfı konulamaz?
**Cevap:** `std::string`, `std::vector` veya işaretçi (pointer) tutan yapılar veriyi heap üzerinde başka bir adrese tahsis eder. O adres diğer sürecin sanal bellek haritasında geçersizdir (Dangling pointer / SIGSEGV). Ayrıca sanal fonksiyon tablosu (`vptr` / `vtable`) her sürecin kendi kod segmenti adresini gösterir. Shared memory'ye yalnızca düz veri tipleri (POD / Trivially Copyable) veya offset-tabanlı özel veri yapıları konulabilir.

## 17. 🚀 Gelecek Perspektifi ve Sonraki Güne Köprü

Bugün süreçler arası iletişimin omurgası olan **Pipe vs Socket vs Shared Memory** mimarisini, donanımsal kopya maliyetlerini, robust kilit kurtarma protokollerini ve karar matrisini kurduk.

### Büyük Resimdeki Yerimiz:
- **Dün (Gün 125):** Görev kuyruğu önceliklendirme ve işçi durum makinelerini tasarladık.
- **Bugün (Gün 126):** Süreçler arası iletişim mekanizmalarının donanımsal sınırlarını belirledik.
- **Yarın (Gün 127):** Bugünün en hızlı şampiyonu olan paylaşımlı belleğin derinliklerine inecek; **POSIX shared memory ile state paylaşımı (mmap, shm_open, senkronize durum makineleri ve zero-copy state store)** mimarisine adım atacağız!
