# GÜN 145: Blocking vs Non-Blocking Socket Mimarisi

**Müfredat:** 365 Günlük ASELSAN / HAVELSAN Savunma Sistemleri C++20 & Linux Sistem Mühendisliği  
**Faz:** F4 — TCP/UDP / Ağ Protokolleri / Serileştirme & Taktik Dağıtık Sistemler  
**Konu:** Bloklanan (Blocking) ve Bloklanmayan (Non-Blocking) Soketler, `fcntl()`, `O_NONBLOCK`, `EAGAIN`/`EWOULDBLOCK`, Asenkron `connect()` (`EINPROGRESS`), Zaman Aşımları (`SO_RCVTIMEO`) ve Gerçek Zamanlı Uçuş/Radar Kontrol Döngüleri  
**Ön Koşul:** Gün 144 (C++ TCP Server/Client, Listen Backlog, Accept, SIGPIPE Koruması)

---

### Telif ve Yasal Uyarı
```text
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

---

## 1. Zihinsel Model & Savunma Sanayii Konsepti

Savunma sanayiinde gerçek zamanlı (hard real-time / soft real-time) görev icra eden sistemlerin (İHA aviyonik uçuş kontrol bilgisayarları, radar hedef takip algoritmaları, füze seyrüsefer ve arayıcı başlık güdüm bilgisayarları) kalbinde **zaman determinizmi** yer alır. Bir Bayraktar TB2 / Akıncı uçuş kontrol döngüsü saniyede 100 veya 200 çevrim ($100\ \text{Hz}$ - $10\ \text{ms}$, $200\ \text{Hz}$ - $5\ \text{ms}$) ile çalışır. Bu döngü içerisinde jiroskop, ivmeölçer, pitot tüpü okunur, Kalman filtresi çalıştırılır, servomotorlara PWM emirleri üretilir ve yer istasyonuna telemetri gönderilir.

Eğer telemetri gönderilen veya yer istasyonundan emir beklenen soket **Bloklanan (Blocking)** modda bırakılmışsa ve yer istasyonundan o çevrimde bir paket gelmemişse ya da radyo linki (RF Link) anlık karartmaya uğramışsa:
1. `recv()` veya `read()` sistem çağrısı yapan işletim sistemi iş parçacığı (thread), Linux çekirdeği tarafından uyku kuyruğuna (`sk->sk_sleep`) alınır ve askıya alınır (`TASK_INTERRUPTIBLE`).
2. Bu iş parçacığı $10\ \text{ms}$ sürmesi gereken kontrol döngüsünü tamamlayamaz; $50\ \text{ms}$, $1000\ \text{ms}$ veya sonsuza kadar bloklu kalır.
3. Sonuç: Aviyonik kanatçık kontrolü yapılamaz, İHA aerodinamik kararsızlığa girer ve düşer (Kritik Görev Çöküşü).

Buna karşılık **Bloklanmayan (Non-Blocking)** soket mimarisinde, soket çekirdeğe `O_NONBLOCK` bayrağı ile kaydedilir. Eğer soketin alma kuyruğunda (`sk_receive_queue`) veri yoksa, sistem çağrısı beklemez; derhal kullanıcı uzayına dönerek `-1` değeri ve `errno = EAGAIN` (veya `EWOULDBLOCK`) fırlatır. Aviyonik döngü hiçbir duraklama yaşamadan seyrüsefer ve kontrol matematiğini hesaplamaya devam eder.

```
   +-------------------------------------------------------------------------+
   |             SAVUNMA SANAYİİ GERÇEK ZAMANLI İLETİŞİM MODELİ             |
   +-------------------------------------------------------------------------+
   
   A) BLOKLANAN SOKET (BLOCKING) - FELAKET SENARYOSU:
   Uçuş Döngüsü (100 Hz, T=10ms)
   [Sensör Oku] -> [Kalman Filtresi] -> [recv() ÇAĞRISI] -------------------> (BLOKLANDI!)
                                               |                                  |
                                               +-- Veri yoksa thread uyutulur.    |
                                               +-- RF Link koptuysa sonsuz bekle! |
                                               v                                  |
   Deadlock / Jitter -> Kanat Kontrolü Kaçtı -> İHA Düştü! <----------------------+

   B) BLOKLANMAYAN SOKET (NON-BLOCKING) - DETERMINİSTİK MODEL:
   Uçuş Döngüsü (100 Hz, T=10ms)
   [Sensör Oku] -> [Kalman Filtresi] -> [recv() ÇAĞRISI] -> EAGAIN / EWOULDBLOCK (0.2 µs)
                                               |
                                               v (Veri yoksa hemen dön, zaman kaybetme)
   [Açısal Hız Hesapla] -> [PWM Emir Üret] -> [Döngüyü 10.0 ms'de Tamamla] -> (GÖREV BAŞARILI)
```

---

## 2. POSIX Berkeley Socket Modelleri: Blocking vs Non-Blocking

POSIX uyumlu işletim sistemlerinde (Linux, QNX, VxWorks), soketler varsayılan (default) olarak **Bloklanan** modda oluşturulur. Bir soketi bloklanmayan hale getirmek için iki temel yöntem kullanılır:

### 1. `fcntl()` (File Control) Sistem Çağrısı ile Çalışma Zamanında Değiştirme
Mevcut bir dosya tanımlayıcısının (file descriptor - `fd`) bayraklarını sorgulamak ve güncellemek:
```cpp
#include <fcntl.h>
#include <unistd.h>
#include <iostream>
#include <cerrno>

bool set_socket_nonblocking(int fd) {
    // 1. Mevcut bayrakları oku (Mevcut diğer bayrakları korumak için şart!)
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags == -1) {
        std::cerr << "fcntl(F_GETFL) hatasi: " << errno << std::endl;
        return false;
    }
    // 2. O_NONBLOCK bayrağını bit düzeyinde OR ile ekle
    if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1) {
        std::cerr << "fcntl(F_SETFL) hatasi: " << errno << std::endl;
        return false;
    }
    return true;
}
```

### 2. Linux Çekirdeği 2.6.27+ `socket()` ve `accept4()` Atomik Bayrakları
Yarış durumlarını (race condition) ve fazladan sistem çağrısı maliyetini önlemek için soket doğrudan non-blocking açılabilir:
```cpp
// Atomik olarak non-blocking soket oluşturma
int fd = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);

// Bağlantı kabulünde istemci soketini atomik non-blocking alma
int client_fd = accept4(listen_fd, (struct sockaddr*)&addr, &len, SOCK_NONBLOCK | SOCK_CLOEXEC);
```

### `EAGAIN` ve `EWOULDBLOCK` Eşitliği
POSIX.1 standardı uyarınca çoğu modern Linux mimarisinde `EAGAIN` ve `EWOULDBLOCK` aynı sayısal değere (`11`) sahiptir. Ancak taşınabilir C++ kodlarında her iki makro da kontrol edilmelidir:
```cpp
ssize_t bytes = recv(fd, buffer, sizeof(buffer), 0);
if (bytes < 0) {
    if (errno == EAGAIN || errno == EWOULDBLOCK) {
        // Hata değildir! Şu anda çekirdek tamponunda veri yok demektir.
        // Thread uyutulmadan diğer görevlere geçmelidir.
    } else if (errno == EINTR) {
        // Sistem çağrısı bir sinyal (signal) tarafından kesildi, tekrar dene.
    } else {
        // Gerçek bir soket hatası (bağlantı koptu vb.)
    }
} else if (bytes == 0) {
    // Karşı taraf bağlantıyı kapattı (TCP FIN alındı - EOF)
}
```

---

## 3. Non-Blocking Bağlantı ve `EINPROGRESS` Mekanizması

TCP protokolünde `connect()` çağrısı 3'lü el sıkışmayı (3-Way Handshake: SYN -> SYN-ACK -> ACK) başlatır.
- **Bloklanan Sokette `connect()`:** Sunucu yanıt verene kadar veya TCP zaman aşımı süresi dolana kadar (Linux'ta varsayılan olarak yaklaşık $75-127\ \text{saniye}$) çağıran iş parçacığını dondurur.
- **Bloklanmayan Sokette `connect()`:** Çekirdek ilk `SYN` paketini ağ kartının gönderme kuyruğuna yazar ve **derhal** `-1` döndürür. Bu sırada `errno` değeri `EINPROGRESS` ("İşlem Sürüyor") olarak atanır.

### Asenkron `connect()` Yaşam Döngüsü ve Doğrulama
Bir istemci non-blocking `connect()` başlattığında bağlantının kurulduğunu veya başarısız olduğunu nasıl anlar?
1. `connect(fd, ...)` çağrılır. Dönüş `-1` ve `errno == EINPROGRESS` ise el sıkışma arka planda devam ediyordur.
2. `fd`, I/O multiplexer'a (`select`, `poll` veya `epoll`) **yazılabilirlik (writeability - `EPOLLOUT`)** için kaydedilir.
3. El sıkışma başarıyla tamamlandığında soket yazılabilir hale gelir.
4. **Kritik Adım (`getsockopt`):** Soket yazılabilir oldu diye bağlantı mutlaka başarılı demek değildir! Hedef IP portu kapalıysa (`RST` döndüyse) veya zaman aşımına uğradıysa da soket yazılabilir işaretlenir. Bağlantının gerçek durumunu öğrenmek için `getsockopt` ile soket seviyesindeki hata sorgulanmalıdır:

```cpp
int error = 0;
socklen_t len = sizeof(error);
int res = getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &len);

if (res < 0) {
    // getsockopt çağrısının kendisi başarısız oldu
} else if (error != 0) {
    // Bağlantı başarısız! error değişkeni ECONNREFUSED, ETIMEDOUT vb. içerir.
    std::cerr << "Baglanti basarisiz: " << strerror(error) << std::endl;
} else {
    // Bağlantı başarıyla kuruldu! Güvenle veri gönderilip alınabilir.
    std::cout << "TCP baglantisi basariyla kuruldu (ESTABLISHED)." << std::endl;
}
```

---

## 4. Busy-Polling Tehlikesi: %100 CPU Yanması vs Event-Driven Hazırlık

Bloklanmayan soketlere yeni başlayan mühendislerin düştüğü en büyük tuzak **Busy-Polling (Meşgul Bekleme / Spin-Loop)** yöntemidir:

```cpp
// TEHLİKELİ ANTI-PATTERN: Çekirdeği eriten döngü!
while (true) {
    ssize_t n = recv(fd, buf, sizeof(buf), 0);
    if (n > 0) {
        process_data(buf, n);
    } else if (errno == EAGAIN || errno == EWOULDBLOCK) {
        // Veri yok, hemen tekrar dene!
        continue; // CPU çekirdeği %100'e kilitlenir!
    }
}
```

### Busy-Polling Neden Kabul Edilemez?
1. **%100 CPU Saturasyonu:** İşlemci çekirdeği saniyede milyonlarca kez gereksiz `recv()` sistem çağrısı yapar.
2. **Termal Kısılma (Thermal Throttling):** Savunma elektroniği kutularında (kapalı aviyonik podlar, radar soğutma blokları) sıcaklık $90^\circ\text{C}$ üzerine çıkarak işlemcinin saat frekansını düşürür.
3. **Batarya / Güç Tüketimi:** İHA veya taşınabilir telsizlerin batarya ömrünü tüketir.
4. **Önbellek Kirlenmesi (Cache Thrashing):** Sürekli kullanıcı-uzayı çekirdek-uzayı bağlam değişimi (context switch) L1/L2 önbellekleri kirletir.

### Doğru Tasarım: Olay Güdümlü (Event-Driven) I/O Multiplexing
Bloklanmayan soketler tek başlarına birer döngüde çağrılmak için değil; `select()`, `poll()` veya modern Linux'un süper-ölçeklenebilir `epoll` mekanizması ile birlikte çalışmak üzere tasarlanmıştır. İş parçacığı, kernel tarafından "Bu sokette yeni veri geldiğinde beni uyandır" diyerek sıfır CPU harcayarak uyur.

---

## 5. Zaman Aşımı (Timeout) Mimarisi: `SO_RCVTIMEO` / `SO_SNDTIMEO`

Karmaşık bir `epoll` veya durum makinesi kurmanın aşırı mühendislik (over-engineering) olacağı basit telemetri istemcilerinde, soketi tamamen non-blocking yapmak yerine **Zaman Aşımlı Bloklanan (Timed-Blocking)** modda çalıştırmak tercih edilebilir.

Linux Berkeley soket arayüzü, soket seçenekleri (`setsockopt`) üzerinden alma ve gönderme zaman aşımlarını mikrosaniye hassasiyetinde belirleme imkanı sunar:

```cpp
#include <sys/socket.h>
#include <sys/time.h>

struct timeval timeout;
timeout.tv_sec = 0;
timeout.tv_usec = 15000; // 15 milisaniye zaman aşımı

// Alma zaman aşımı (Receive Timeout)
setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

// Gönderme zaman aşımı (Send Timeout)
setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
```

### Davranış Karakteristiği:
- Sokette veri varsa `recv()` anında veriyi alır ve döner.
- Sokette veri yoksa thread en fazla `15 ms` bloklanır. Süre dolduğunda sistem çağrısı `-1` döner ve `errno` değeri `EAGAIN` veya `EWOULDBLOCK` olur.
- Bu sayede kontrol döngüleri sonsuza kadar kilitlenmekten korunmuş olur.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 145: Kod Bloğu 1 — C++20 Blocking vs Non-Blocking POSIX Soket Katmanı & Çekirdek Simülasyonu
"""

import time
import errno
import collections
from typing import Tuple, Optional, Dict, Any, List

class LinuxKernelSocketBuffer:
    """
    Linux Çekirdeği sk_buff ve Soket Durumunu Simüle Eden Çekirdek Yapısı.
    Bloklanan ve bloklanmayan soketlerin kernel içi kuyruk ve kilit davranışını modeller.
    """
    def __init__(self, fd: int, is_nonblocking: bool = False, rcv_timeout_sec: float = 0.0):
        self.fd = fd
        self.is_nonblocking = is_nonblocking
        self.rcv_timeout_sec = rcv_timeout_sec
        self.receive_queue: collections.deque = collections.deque()
        self.send_queue: collections.deque = collections.deque()
        self.is_connected = False
        self.is_connecting = False
        self.connect_start_time = 0.0
        self.handshake_duration = 0.020  # 20 ms ağ RTT süresi
        self.pending_error = 0
        self.stats = {
            "recv_calls": 0,
            "eagain_hits": 0,
            "bytes_received": 0,
            "bytes_sent": 0,
            "blocking_wait_time_sec": 0.0
        }

    def set_nonblocking(self, enabled: bool):
        self.is_nonblocking = enabled

    def set_rcv_timeout(self, timeout_sec: float):
        self.rcv_timeout_sec = timeout_sec

    def initiate_connect(self, remote_addr: Tuple[str, int]) -> int:
        """
        POSIX connect() sistem çağrısı simülasyonu.
        """
        self.is_connecting = True
        self.connect_start_time = time.perf_counter()
        
        if self.is_nonblocking:
            # Non-blocking modda kernel anında EINPROGRESS döner!
            return -errno.EINPROGRESS
        else:
            # Blocking modda thread el sıkışma tamamlanana kadar uyutulur
            time.sleep(self.handshake_duration)
            self.is_connected = True
            self.is_connecting = False
            self.stats["blocking_wait_time_sec"] += self.handshake_duration
            return 0

    def update_connection_state(self):
        """Çekirdek arka planında 3'lü el sıkışmanın ilerlemesi."""
        if self.is_connecting:
            now = time.perf_counter()
            if now - self.connect_start_time >= self.handshake_duration:
                self.is_connecting = False
                self.is_connected = True
                self.pending_error = 0

    def check_socket_error(self) -> int:
        """getsockopt(fd, SOL_SOCKET, SO_ERROR) çağrısı simülasyonu."""
        self.update_connection_state()
        if self.is_connecting:
            return errno.EINPROGRESS
        err = self.pending_error
        self.pending_error = 0 # Bir kez okununca sıfırlanır
        return err

    def send(self, data: bytes) -> int:
        if not self.is_connected:
            raise BrokenPipeError("Soket bağlı değil! (ENOTCONN / EPIPE)")
        self.send_queue.append(data)
        self.stats["bytes_sent"] += len(data)
        return len(data)

    def inject_incoming_packet(self, data: bytes):
        """Ağ kartından (NIC) gelen paketin kernel tamponuna girişi."""
        self.receive_queue.append(data)

    def recv(self, max_bytes: int) -> bytes:
        """
        POSIX recv() sistem çağrısı davranışı.
        """
        self.stats["recv_calls"] += 1
        
        # 1. Kuyrukta veri varsa anında dön
        if self.receive_queue:
            chunk = self.receive_queue.popleft()
            self.stats["bytes_received"] += len(chunk)
            return chunk

        # 2. Kuyrukta veri yoksa mod kontrolü:
        if self.is_nonblocking:
            # Bloklanmayan soket anında EAGAIN / EWOULDBLOCK fırlatır!
            self.stats["eagain_hits"] += 1
            raise BlockingIOError(errno.EAGAIN, "Resource temporarily unavailable (EAGAIN)")

        # 3. Timeout tanımlı bloklanan soket
        if self.rcv_timeout_sec > 0.0:
            start_wait = time.perf_counter()
            while (time.perf_counter() - start_wait) < self.rcv_timeout_sec:
                time.sleep(0.001)
                if self.receive_queue:
                    chunk = self.receive_queue.popleft()
                    self.stats["bytes_received"] += len(chunk)
                    return chunk
            self.stats["blocking_wait_time_sec"] += self.rcv_timeout_sec
            self.stats["eagain_hits"] += 1
            raise BlockingIOError(errno.EAGAIN, "Resource temporarily unavailable (SO_RCVTIMEO)")

        # 4. Saf bloklanan soket (Veri gelene kadar sonsuz bekler - simülasyonda 50ms sınır koyuyoruz)
        simulated_hang_time = 0.050
        time.sleep(simulated_hang_time)
        self.stats["blocking_wait_time_sec"] += simulated_hang_time
        if self.receive_queue:
            chunk = self.receive_queue.popleft()
            self.stats["bytes_received"] += len(chunk)
            return chunk
        raise TimeoutError("Bloklanan soket veri gelmediği için thread'i kilitledi!")

print("[HÜCRE 7] LinuxKernelSocketBuffer C++20 / POSIX socket simülatörü hazırlandı.")
```

---

## 6. Taktik İHA Uçuş Kontrol Döngüsü ve Telemetri Test Senaryosu

Bu deneyde, bir taktik İHA'nın otopilot ana döngüsünü ($100\ \text{Hz}$ / $10\ \text{ms}$ çevrim süresi) simüle edeceğiz. Döngünün her adımında otopilot 3 kritik alt adımı yürütür:
1. **Atalet Ölçüm Ünitesi (IMU) & Hava Veri Bilgisayarı:** Pitch/Roll/Yaw açılarını ve sürati hesaplar ($2.0\ \text{ms}$).
2. **Uçuş Kontrol ve Yüzey PWM Emirleri:** Kalman filtresi ve PID katsayılarıyla kanatçık servolarına emir üretir ($2.0\ \text{ms}$).
3. **Yer İstasyonu Telemetri Ağı:** Yerden gelen taktik komutları (`recv()`) okur ve durum telemetrisi gönderir.

### Deney Senaryosu:
- **Senaryo A (Bloklanan Soket):** Yer istasyonundan her çevrimde veri gelmez (RF link gecikmesi veya periyodik paket gönderimi). Bloklanan soket çağrıldığında uçuş döngüsü $10\ \text{ms}$ yerine $50\ \text{ms}$ duraklar. Kontrol gecikmesi birikerek İHA'nın aerodinamik kontrol kaybı yaşamasına sebep olur.
- **Senaryo B (Bloklanmayan Soket):** `O_NONBLOCK` aktif edildiğinde, veri yoksa `EAGAIN` alınır ve aviyonik döngü $0.05\ \text{ms}$ içinde sonraki çevrime geçer. Uçuş kontrol döngüsü kusursuz şekilde $10.0\ \text{ms}$ ritmini korur.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 145: Kod Bloğu 2 — Taktik İHA 100 Hz Kontrol Döngüsü Deneyi: Blocking vs Non-Blocking
"""

import time

def run_uav_flight_loop(use_nonblocking: bool, cycles: int = 50) -> Dict[str, Any]:
    sock = LinuxKernelSocketBuffer(fd=42, is_nonblocking=use_nonblocking)
    sock.is_connected = True
    
    # Yer istasyonundan sadece her 10 çevrimde bir komut gelsin
    command_arrival_schedule = {5: b"CMD_WAYPOINT_ALT_5000M", 15: b"CMD_HEADING_SET_045", 25: b"CMD_ARM_PAYLOAD"}
    
    cycle_durations = []
    deadlines_missed = 0
    commands_processed = 0
    eagain_count = 0
    
    TARGET_CYCLE_TIME = 0.010 # 10 ms (100 Hz)
    
    for c in range(cycles):
        t_start = time.perf_counter()
        
        # 1. IMU ve Sensör İşleme (2 ms)
        time.sleep(0.002)
        
        # 2. Ağ Komut Alımı (recv)
        if c in command_arrival_schedule:
            sock.inject_incoming_packet(command_arrival_schedule[c])
            
        cmd = None
        try:
            cmd = sock.recv(256)
            commands_processed += 1
        except BlockingIOError:
            # Non-blocking sokette veri yoksa normal durum!
            eagain_count += 1
        except TimeoutError:
            # Bloklanan sokette veri yoksa thread kilitlendi!
            deadlines_missed += 1
            
        # 3. Servomotor PWM ve Yüzey Kontrolü (2 ms)
        time.sleep(0.002)
        
        t_end = time.perf_counter()
        duration = t_end - t_start
        cycle_durations.append(duration * 1000.0) # ms cinsinden
        
        if duration > TARGET_CYCLE_TIME * 1.5:
            deadlines_missed += 1

    avg_cycle_ms = sum(cycle_durations) / len(cycle_durations)
    max_cycle_ms = max(cycle_durations)
    jitter_ms = max_cycle_ms - min(cycle_durations)
    
    return {
        "mode": "Non-Blocking" if use_nonblocking else "Blocking",
        "cycles": cycles,
        "avg_cycle_ms": avg_cycle_ms,
        "max_cycle_ms": max_cycle_ms,
        "jitter_ms": jitter_ms,
        "deadlines_missed": deadlines_missed,
        "commands_processed": commands_processed,
        "eagain_count": eagain_count,
        "durations": cycle_durations
    }

res_blocking = run_uav_flight_loop(use_nonblocking=False, cycles=30)
res_nonblocking = run_uav_flight_loop(use_nonblocking=True, cycles=30)

print()
print("[+] İHA Aviyonik 100 Hz (10 ms Hedef) Kontrol Döngüsü Test Sonuçları:")
print(f"  [A] BLOKLANAN SOKET (Blocking):")
print(f"      - Ortalama Çevrim Süresi : {res_blocking['avg_cycle_ms']:.2f} ms (Hedef: 10.0 ms)")
print(f"      - Maksimum Çevrim Süresi : {res_blocking['max_cycle_ms']:.2f} ms")
print(f"      - Jitter (Dalgalanma)    : {res_blocking['jitter_ms']:.2f} ms")
print(f"      - Kaçırılan Deadline     : {res_blocking['deadlines_missed']} çevrim (UÇUŞ GÜVENLİK TEHLİKESİ!)")

print(f"  [B] BLOKLANMAYAN SOKET (Non-Blocking):")
print(f"      - Ortalama Çevrim Süresi : {res_nonblocking['avg_cycle_ms']:.2f} ms (Mükemmel Kararlılık)")
print(f"      - Maksimum Çevrim Süresi : {res_nonblocking['max_cycle_ms']:.2f} ms")
print(f"      - Jitter (Dalgalanma)    : {res_nonblocking['jitter_ms']:.2f} ms")
print(f"      - Kaçırılan Deadline     : {res_nonblocking['deadlines_missed']} çevrim (SIFIR HATA)")
print(f"      - Güvenle Geçilen EAGAIN : {res_nonblocking['eagain_count']} adet")

assert res_blocking['deadlines_missed'] > 0, "Bloklanan soket deadline kaçırmalıydı!"
assert res_nonblocking['deadlines_missed'] == 0, "Non-blocking soket hiçbir deadline kaçırmamalı!"
print("[HÜCRE 9] Uçuş döngüsü deneyi başarıyla tamamlandı ve doğrulandı.")
```

---

## 7. Bilerek Bozma (Sabotaj ve Arıza Enjeksiyonu)

Bu bölümde iki ölümcül yazılım hatasını simüle edip sonuçlarını gözlemleyeceğiz:

### Sabotaj 1: 100% CPU Kilitlenmesi (Unthrottled Busy-Polling Yangını)
Bloklanmayan soketten veri okumak isteyen bir iş parçacığı, `EAGAIN` aldığında hiçbir uyku (`sleep`) veya olay bekleyicisi (`epoll`/`poll`) koymadan sonsuz döngüde `recv()` çağırır.
- **Beklenen Hata Belirtisi:** 100,000 döngüde harcanan CPU zamanı tavan yapar, işlemci çekirdeği tam güç tüketimine geçer.
- **Savunma Mekanizması:** Olay mekanizması (`epoll`) veya en kötü durumda mikrosaniye seviyesinde zaman aşımlı uyku (`std::this_thread::sleep_for`) ya da `SO_RCVTIMEO` kullanımı.

### Sabotaj 2: Körlemesine Yazma (Unchecked `EINPROGRESS` Felaketi)
Asenkron non-blocking `connect()` çağrıldığında sistem `-1` ve `errno == EINPROGRESS` döner. Geliştirici bu durumu kontrol etmeyip veya el sıkışmanın tamamlanmasını `getsockopt(SO_ERROR)` ile denetlemeden anında `send()` yapmaya kalkışır.
- **Beklenen Hata Belirtisi:** Çekirdek soket henüz `ESTABLISHED` durumuna geçmediği için `ENOTCONN` (Socket is not connected) hatası fırlatır veya bağlantı koptuysa `SIGPIPE` / `EPIPE` ile süreç sonlanır!

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 145: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Busy-Wait CPU Yangını & Unchecked EINPROGRESS
"""

import time
import errno

print()
print("[*] TCP Sabotaj ve Arıza Enjeksiyon Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: Busy-Wait CPU Yanması vs Kontrollü Event Bekleme
# -----------------------------------------------------------------------------
sock_busy = LinuxKernelSocketBuffer(fd=88, is_nonblocking=True)
sock_busy.is_connected = True

# 1A) Kötü Kod: Busy-polling ile 100,000 kez EAGAIN döndürme
t_start_busy = time.perf_counter()
busy_spins = 0
for _ in range(100_000):
    try:
        sock_busy.recv(128)
    except BlockingIOError:
        busy_spins += 1
t_busy_duration = time.perf_counter() - t_start_busy

# 1B) Doğru Kod: Event-driven bekleme veya backoff (örnek 10 deneme arası 0.5 ms sleep)
t_start_event = time.perf_counter()
event_spins = 0
for _ in range(10):
    try:
        sock_busy.recv(128)
    except BlockingIOError:
        event_spins += 1
        time.sleep(0.0005) # 500 mikrosaniye çekirdek dinlendirme
t_event_duration = time.perf_counter() - t_start_event

print(f"  [+] Sabotaj 1 Sonuçları (Busy-Polling vs Kontrollü Bekleme):")
print(f"      - Busy-Wait 100k Deneme Süresi : {t_busy_duration*1000:.2f} ms (CPU %100 Yandı!)")
print(f"      - 100k Döngüde Boşa Çağrı     : {busy_spins} adet gereksiz recv() sistem çağrısı")
print(f"      - Kontrollü 10 Döngü Süresi   : {t_event_duration*1000:.2f} ms (CPU Dinlendirildi)")

# -----------------------------------------------------------------------------
# SABOTAJ 2: Unchecked EINPROGRESS (Bağlantı Bitmeden Veri Gönderme)
# -----------------------------------------------------------------------------
sock_unready = LinuxKernelSocketBuffer(fd=89, is_nonblocking=True)
rc = sock_unready.initiate_connect(("192.168.1.100", 8080))
assert rc == -errno.EINPROGRESS, "Non-blocking connect anında EINPROGRESS dönmeliydi!"

premature_send_error = None
try:
    # Henüz 3-Way Handshake bitmeden veri gönderilmeye çalışılıyor!
    sock_unready.send(b"CRITICAL_MISSILE_FIRE_COMMAND")
except BrokenPipeError as e:
    premature_send_error = str(e)

print(f"  [+] Sabotaj 2 Sonuçları (Unchecked EINPROGRESS):")
print(f"      - Connect Dönüşü             : -1 (errno = EINPROGRESS / {errno.EINPROGRESS})")
print(f"      - Erken Gönderim Hatası      : {premature_send_error}")

# Doğru Yaklaşım: Handshake süresi beklenir ve getsockopt doğrulanır
time.sleep(sock_unready.handshake_duration + 0.005)
err_code = sock_unready.check_socket_error()
assert err_code == 0, "Handshake sonrası soket hatası 0 olmalı!"

# Artık güvenle gönderilir
bytes_sent = sock_unready.send(b"CRITICAL_MISSILE_FIRE_COMMAND")
print(f"      - getsockopt(SO_ERROR) Sonucu : 0 (SUCCESS - Bağlantı Kuruldu)")
print(f"      - Güvenli Gönderim           : {bytes_sent} bayt başarıyla iletildi.")

print("[HÜCRE 11] Sabotaj ve arıza testleri başarıyla tamamlandı.")
```

---

## 8. Performans ve Gecikme Benchmark Metrikleri

Gerçek zamanlı askeri sistemlerde sistem çağrısı (syscall) maliyeti, determinizm ve CPU çekirdek tüketimi bir arada değerlendirilir.
Aşağıdaki tabloda üç temel soket I/O yaklaşımının mimari karşılaştırması yer almaktadır:

| Parametre / Metrik | Saf Bloklanan (Blocking) | Bloklanmayan (Busy-Polling) | Olay Güdümlü Non-Blocking (`epoll`) |
| :--- | :--- | :--- | :--- |
| **Sistem Çağrısı Başına Gecikme** | Değişken (0.5 µs - $\infty$) | Deterministik (~0.3 µs) | Deterministik (~0.4 µs) |
| **Gecikme Jitter'ı (Varyans)** | Çok Yüksek (Kritik Risk) | Çok Düşük (Sıfır Bekleme) | Çok Düşük (Mikrosaniye Seviyesi) |
| **CPU Tüketimi (1 Boş Soket)** | %0 (Thread Uyuyor) | **%100 (Çekirdeği Kilitler)** | %0 (Kernel Uyandırır) |
| **Ölçeklenebilirlik ($N$ Soket)** | $O(N)$ Thread Gerekir | Tek Çekirdekte $N$ Soket Taranır | $O(1)$ Olay Bildirimi |
| **Uçuş Kontrolüne Uygunluk** | **YASAK (Deadlock Riski)** | Kısmen (Sıkı Zamanlayıcı ile) | **TAVSİYE EDİLEN STANDART** |
| **Hata Kodu Yönetimi** | `EINTR`, `ETIMEDOUT` | `EAGAIN`, `EWOULDBLOCK` | `EPOLLIN`, `EPOLLOUT`, `EPOLLERR` |

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 145: Kod Bloğu 4 — Benchmark: Soket Modu Gecikme Dağılımı ve Jitter Analizi
"""

import time
import numpy as np

def benchmark_socket_latency_distribution(num_samples: int = 1000) -> Dict[str, Any]:
    # 1. Non-Blocking Soket Çağrı Süreleri
    sock_nb = LinuxKernelSocketBuffer(fd=10, is_nonblocking=True)
    sock_nb.is_connected = True
    
    nb_latencies_us = []
    for _ in range(num_samples):
        t0 = time.perf_counter_ns()
        try:
            sock_nb.recv(64)
        except BlockingIOError:
            pass
        t1 = time.perf_counter_ns()
        nb_latencies_us.append((t1 - t0) / 1000.0) # mikrosaniye

    # 2. Timed-Blocking Soket Çağrı Süreleri (1 ms timeout)
    sock_tb = LinuxKernelSocketBuffer(fd=11, is_nonblocking=False, rcv_timeout_sec=0.001)
    sock_tb.is_connected = True
    
    tb_latencies_us = []
    # 100 örnek alıyoruz çünkü bekleme süresi var
    for _ in range(100):
        t0 = time.perf_counter_ns()
        try:
            sock_tb.recv(64)
        except BlockingIOError:
            pass
        t1 = time.perf_counter_ns()
        tb_latencies_us.append((t1 - t0) / 1000.0)

    nb_arr = np.array(nb_latencies_us)
    tb_arr = np.array(tb_latencies_us)
    
    return {
        "nb_mean_us": float(np.mean(nb_arr)),
        "nb_p99_us": float(np.percentile(nb_arr, 99)),
        "nb_max_us": float(np.max(nb_arr)),
        "tb_mean_us": float(np.mean(tb_arr)),
        "tb_p99_us": float(np.percentile(tb_arr, 99)),
        "tb_samples": tb_arr,
        "nb_samples": nb_arr
    }

bench_res = benchmark_socket_latency_distribution(num_samples=1000)

print()
print("[*] Soket Modları Mikrosaniye Seviyesi Gecikme Benchmark Sonuçları:")
print(f"  [+] Non-Blocking recv() [EAGAIN Hızlı Dönüş]:")
print(f"      - Ortalama Gecikme : {bench_res['nb_mean_us']:.3f} µs")
print(f"      - 99. Yüzdelik (P99): {bench_res['nb_p99_us']:.3f} µs")
print(f"      - Maksimum Tepe    : {bench_res['nb_max_us']:.3f} µs")

print(f"  [+] Timed-Blocking recv() [SO_RCVTIMEO = 1.0 ms]:")
print(f"      - Ortalama Gecikme : {bench_res['tb_mean_us']:.2f} µs (~1.0 ms)")
print(f"      - 99. Yüzdelik (P99): {bench_res['tb_p99_us']:.2f} µs")

assert bench_res['nb_mean_us'] < 100.0, "Non-blocking dönüş mikrosaniye mertebesinde olmalıdır!"
print("[HÜCRE 13] Benchmark testleri başarıyla tamamlandı.")
```

---

## 9. Gerçek Dünya Taktik Senaryosu: Radar Hedef İzleme ve Sensör Füzyon Hattı

ASELSAN Hava Savunma Erken İkaz ve Komuta Kontrol Sistemlerinde birden fazla radar ve elektro-optik sensörden veri toplanır:
1. **AESA Arama Radarı (X-Band):** $50\ \text{Hz}$ hedef iz (track) paketleri.
2. **IFF (Dost-Düşman Tanıma) Sorgulayıcı:** $20\ \text{Hz}$ kimlik doğrulama paketleri.
3. **FLIR / Termal Elektro-Optik Kamera:** $30\ \text{Hz}$ açı ve hedef görüntü telemetrisi.

Eğer tek bir iş parçacığı bu üç sensör soketini sırayla bloklanan modda okumaya çalışırsa:
- AESA radarında veri yoksa soket kilitlenir; o sırada IFF'ten gelen kritik "Dost Uçak" sinyali okunamaz.
- Sonuç: Füzyon hattı karar veremez veya yanlış hedef sınıflandırması yapar.

### Non-Blocking Round-Robin Sensör Füzyon Çözümü
Sensör soketleri non-blocking açılır. Füzyon döngüsü her çevrimde tüm soketleri hızla tarar (`drain_sensor_socket`). Verisi olan sensörlerin paketleri anında füzyon matrisine eklenir, verisi olmayanlar ise $0.2\ \mu\text{s}$ içinde geçilir.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 145: Kod Bloğu 5 — ASELSAN Radar Sensör Füzyon Hattı: Çoklu Non-Blocking Soket Taraması
"""

import time
from typing import List, Dict, Any

class SensorStream:
    def __init__(self, name: str, fd: int):
        self.name = name
        self.sock = LinuxKernelSocketBuffer(fd=fd, is_nonblocking=True)
        self.sock.is_connected = True
        self.total_packets_received = 0

def run_sensor_fusion_engine(duration_cycles: int = 100) -> Dict[str, Any]:
    sensors = [
        SensorStream("AESA_RADAR", fd=201),
        SensorStream("IFF_INTERROGATOR", fd=202),
        SensorStream("FLIR_OPTICAL", fd=203)
    ]
    
    # Sensör paket üretim sıklıkları
    # AESA her 2 çevrimde bir, IFF her 5 çevrimde bir, FLIR her 3 çevrimde bir
    fused_tracks = []
    
    for cycle in range(duration_cycles):
        # 1. Sensörlere arka planda veri gelişi
        if cycle % 2 == 0:
            sensors[0].sock.inject_incoming_packet(f"RADAR_TRK_TGT_{cycle}:AZ=45.2,EL=12.1".encode())
        if cycle % 5 == 0:
            sensors[1].sock.inject_incoming_packet(f"IFF_REPLY_TGT_{cycle}:FRIENDLY_MIL".encode())
        if cycle % 3 == 0:
            sensors[2].sock.inject_incoming_packet(f"FLIR_HOTSPOT_TGT_{cycle}:CONF=0.98".encode())
            
        # 2. Non-Blocking Döngüsel Tarama (Round-Robin Poll)
        cycle_packets = []
        for s in sensors:
            while True:
                try:
                    data = s.sock.recv(256)
                    s.total_packets_received += 1
                    cycle_packets.append((s.name, data.decode()))
                except BlockingIOError:
                    # Bu sensörün tamponu boşaldı, diğer sensöre geç
                    break
                    
        if cycle_packets:
            fused_tracks.append((cycle, cycle_packets))
            
    return {
        "cycles": duration_cycles,
        "fused_events_count": len(fused_tracks),
        "aesa_count": sensors[0].total_packets_received,
        "iff_count": sensors[1].total_packets_received,
        "flir_count": sensors[2].total_packets_received
    }

fusion_res = run_sensor_fusion_engine(duration_cycles=50)

print()
print("[*] ASELSAN Radar Füzyon Çoklu Sensör Non-Blocking Testi:")
print(f"  [+] İşlenen Çevrim Sayısı        : {fusion_res['cycles']}")
print(f"  [+] Füzyon Yapılan Olay Sayısı   : {fusion_res['fused_events_count']}")
print(f"  [+] AESA Radar İz Paketi         : {fusion_res['aesa_count']} adet")
print(f"  [+] IFF Kimlik Doğrulama Paketi  : {fusion_res['iff_count']} adet")
print(f"  [+] FLIR Termal İz Paketi        : {fusion_res['flir_count']} adet")

assert fusion_res['aesa_count'] == 25
assert fusion_res['iff_count'] == 10
assert fusion_res['flir_count'] == 17
print("[HÜCRE 15] Sensör füzyon non-blocking akış motoru başarıyla doğrulandı.")
```

---

## 10. 4-Panelli 300 DPI Görselleştirme Mimarisi

Aşağıdaki kod hücresi, bloklanan ve bloklanmayan soket mimarilerinin aviyonik kontrol döngüsü, CPU tüketimi, gecikme ve asenkron bağlantı yaşam döngüsünü 4 panelde detaylandıran profesyonel bir karanlık tema (`#0F172A`) görsel panosu üretir:

1. **Panel 1 (Sol Üst): İHA 100 Hz Uçuş Kontrol Döngüsü Zaman Çizgisi (Blocking vs Non-Blocking):**
   Bloklanan sokette veri gecikmesi olduğunda döngü süresinin $10\ \text{ms}$ deadline sınırını aşıp $50\ \text{ms}$'ye fırlaması; non-blocking modda ise döngünün kararlı $4-5\ \text{ms}$ bandında kalması.
2. **Panel 2 (Sağ Üst): CPU Tüketim Profili & Isıl Yük Analizi:**
   Unthrottled Busy-Polling (%100 CPU saturasyonu ve termal risk), Bloklanan Soket (%0 CPU fakat kilitlenme), ve Event-Driven / Rate-Limited Non-Blocking (%2-%5 ideal operasyonel tüketim).
3. **Panel 3 (Sol Alt): Non-Blocking `connect()` ve `EINPROGRESS` Durum Makinesi:**
   SYN gönderimi, `EINPROGRESS` anlık dönüşü, kernel el sıkışması, `epoll(EPOLLOUT)` tetiklenmesi ve `getsockopt(SO_ERROR)` doğrulama akış şeması.
4. **Panel 4 (Sağ Alt): Soket Modu Gecikme Dağılımı ve Jitter (Keman/Kutu Grafiği):**
   Non-Blocking `EAGAIN` dönüşünün mikrosaniye mertebesindeki ultra-düşük varyansı ile Timed-Blocking modunun gecikme dağılımının karşılaştırması.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 145: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_145_blocking_vs_non_blocking_socket.png")

# Matplotlib stil ve karanlık tema ayarları
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: İHA Kontrol Döngüsü Timeline (Blocking vs Non-Blocking)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')

cycles = np.arange(1, len(res_blocking['durations']) + 1)
ax1.plot(cycles, res_blocking['durations'], color='#EF4444', marker='o', linewidth=2.2, label='Bloklanan Soket (Blocking Jitter)')
ax1.plot(cycles, res_nonblocking['durations'], color='#10B981', marker='s', linewidth=2.2, label='Bloklanmayan Soket (Non-Blocking)')

# 10 ms deadline çizgisi
ax1.axhline(10.0, color='#F59E0B', linestyle='--', linewidth=2, label='100 Hz Hedef Sınır (10 ms Deadline)')

ax1.set_title("İHA 100 Hz Uçuş Kontrol Döngüsü: Çevrim Süresi ve Deadline İhlali", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax1.set_xlabel("Çevrim Numarası (Cycle #)", fontsize=10, color='#94A3B8')
ax1.set_ylabel("Çevrim Süresi (Milisaniye - ms)", fontsize=10, color='#94A3B8')
ax1.grid(True, linestyle=':', alpha=0.4, color='#64748B')
ax1.legend(loc='upper right', facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC')
ax1.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 2: CPU Tüketim Profili & Enerji Analizi
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

categories = ['Bloklanan\n(Blocking Sleep)', 'Busy-Polling\n(Spin-Loop EAGAIN)', 'Event-Driven\n(epoll + Non-Blocking)']
cpu_usage = [0.5, 100.0, 3.2] # % CPU
colors_bar = ['#38BDF8', '#EF4444', '#10B981']

bars = ax2.bar(categories, cpu_usage, color=colors_bar, width=0.5, edgecolor='#334155', linewidth=1.5)
for bar, val in zip(bars, cpu_usage):
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 2.0, f"%{val:.1f}", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=11)

ax2.set_ylim(0, 115)
ax2.set_title("CPU Çekirdek Tüketimi ve Isıl/Enerji Profili", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax2.set_ylabel("CPU Kullanımı (%)", fontsize=10, color='#94A3B8')
ax2.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Non-Blocking connect() & EINPROGRESS Durum Makinesi
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')
ax3.axis('off')

# Blok Şeması Kutuları ve Açıklamaları
boxes = [
    {"x": 0.05, "y": 0.70, "w": 0.24, "h": 0.18, "text": "1. socket(SOCK_NONBLOCK)\nfcntl(O_NONBLOCK)\nSoket Çekirdeğe Kayıtlı", "color": "#3B82F6"},
    {"x": 0.38, "y": 0.70, "w": 0.24, "h": 0.18, "text": "2. connect(fd, &addr)\nDönüş: -1\nerrno = EINPROGRESS", "color": "#F59E0B"},
    {"x": 0.71, "y": 0.70, "w": 0.25, "h": 0.18, "text": "3. 3-Way Handshake\nKernel TCP Katmanı\nSYN -> SYN/ACK -> ACK", "color": "#8B5CF6"},
    {"x": 0.22, "y": 0.25, "w": 0.26, "h": 0.20, "text": "4. epoll_wait()\nEPOLLOUT Tetiklenir!\nSoket Yazılabilir", "color": "#06B6D4"},
    {"x": 0.58, "y": 0.25, "w": 0.32, "h": 0.20, "text": "5. getsockopt(SO_ERROR)\nerr == 0 ? ESTABLISHED\nerr != 0 ? ECONNREFUSED", "color": "#10B981"}
]

for b in boxes:
    rect = plt.Rectangle((b['x'], b['y']), b['w'], b['h'], facecolor=b['color'], alpha=0.25, edgecolor=b['color'], linewidth=2)
    ax3.add_patch(rect)
    ax3.text(b['x'] + b['w']/2, b['y'] + b['h']/2, b['text'], ha='center', va='center', color='#F8FAFC', fontsize=9.5, fontweight='bold')

# Oklar
ax3.annotate("", xy=(0.38, 0.79), xytext=(0.29, 0.79), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax3.annotate("", xy=(0.71, 0.79), xytext=(0.62, 0.79), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax3.annotate("", xy=(0.35, 0.45), xytext=(0.83, 0.70), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2, connectionstyle="arc3,rad=0.3"))
ax3.annotate("", xy=(0.58, 0.35), xytext=(0.48, 0.35), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))

ax3.set_title("Non-Blocking connect() & EINPROGRESS Yaşam Döngüsü", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 4: Soket Çağrı Süresi Dağılımı ve Jitter (Kutu Grafiği)
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')

box_data = [bench_res['nb_samples'], bench_res['tb_samples']]
bp = ax4.boxplot(box_data, patch_artist=True, tick_labels=['Non-Blocking (EAGAIN)', 'Timed-Blocking (1ms)'])

colors_box = ['#10B981', '#F59E0B']
for patch, color in zip(bp['boxes'], colors_box):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)
    patch.set_edgecolor('#F8FAFC')
for median in bp['medians']:
    median.set(color='#FFFFFF', linewidth=2)

ax4.set_yscale('log')
ax4.set_title("recv() Sistem Çağrısı Gecikme Dağılımı (Logaritmik Ölçek)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax4.set_ylabel("Gecikme Süresi (µs - Log)", fontsize=10, color='#94A3B8')
ax4.grid(True, linestyle=':', alpha=0.4, color='#64748B')
ax4.tick_params(colors='#94A3B8')

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 145 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert res_blocking['deadlines_missed'] > 0, "Bloklanan soket döngüsü başarısız olmalıydı."
assert res_nonblocking['deadlines_missed'] == 0, "Non-blocking soket döngüsü sıfır hata ile tamamlanmalıydı."
assert bench_res['nb_mean_us'] < 200.0, "Non-blocking çağrı süresi 200 µs altında olmalı."

print()
print("[PASS] Gün 145: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

---

## 11. Karşılaştırmalı Analiz ve Mimari Karar Matrisi

Havacılık, uzay ve savunma sanayii yazılımlarında ağ mimarisi tasarlanırken seçilen soket I/O paradigmasının artı ve eksileri:

| Kriter / Mimari Karar | Bloklanan (Blocking) | Bloklanmayan (Non-Blocking) | Timed-Blocking (`SO_RCVTIMEO`) | Asenkron / Olay Güdümlü (`epoll`) |
| :--- | :--- | :--- | :--- | :--- |
| **Geliştirme Kolaylığı** | Çok Kolay (Senkron akış) | Orta (Hata kodu yönetimi) | Kolay (Basit zaman aşımı) | Yüksek (Durum makinesi gerekir) |
| **Zaman Determinizmi** | **Kötü (Sonsuz kilitlenme)** | **Kusursuz (Anında döner)** | Kabul Edilebilir (Üst sınır var) | **Kusursuz (Olay bazlı)** |
| **CPU Verimliliği** | Mükemmel (%0 uyku) | Kötü (Busy-poll edilirse) | Mükemmel (%0 uyku) | **En Yüksek (%0 bekleme)** |
| **Gereken Thread Sayısı** | Bağlantı başına 1 thread | Tek thread çoklu soket | Bağlantı başına 1 thread | Tek thread binlerce soket |
| **Savunma Alanı Kullanımı** | Basit CLI test araçları | Kontrol döngüleri (İHA, Radar) | Basit telemetri alıcıları | Taktik C2, Dağıtık Radar Ağı |

---

## 12. Donanım ve İşletim Sistemi Seviyesi Etkileşimler

### Linux Kernel İç Mimarisi (`sk_buff` ve `wait_queue_head_t`)
Bir soket üzerinde `recv()` çağrıldığında Linux çekirdeğinde (`net/socket.c` ve `net/ipv4/tcp.c`) şu işlemler gerçekleşir:
1. **Bloklanan Soket:** `tcp_recvmsg()` fonksiyonu `sk->sk_receive_queue` kuyruğuna bakar. Kuyruk boşsa:
   - Süreç (process/thread) mevcut CPU çekirdeğinden çıkarılır.
   - `sk_sleep(sk)` işaretçisi üzerinden soketin bekleme kuyruğuna (`wait_queue_head_t`) eklenir.
   - Durumu `TASK_INTERRUPTIBLE` yapılır ve çekirdek zamanlayıcısı (`schedule()`) başka bir sürece CPU verir.
   - Ağ kartından (NIC) paket gelip DMA ile belleğe yazıldığında, NIC donanım kesmesi (Hardware IRQ) tetiklenir, ardından `ksoftirqd` (SoftIRQ) `sk_buff` paketini ayrıştırır ve soket bekleme kuyruğundaki thread'i `wake_up_interruptible()` ile uyandırır.
2. **Bloklanmayan Soket:** Eğer soket bayraklarında `O_NONBLOCK` (`file->f_flags & O_NONBLOCK`) set edilmişse:
   - `tcp_recvmsg()` kuyruk boşsa **asla `schedule()` çağırmaz**.
   - Thread uyutulmaz; anında `-EAGAIN` hata koduyla kullanıcı uzayına dönülür. Bağlam değişimi (context switch) maliyeti sıfırdır.

---

## 13. Güvenlik, Hata Ayıklama ve Taktik İpuçları

### 1. `strace` ile Bloklanan Çağrıları Keşfetme
Sahada çalışan bir C++ sürecinin kilitlenip kilitlenmediğini anlamak için:
```bash
# Sürecin hangi sistem çağrısında asılı kaldığını izleme:
strace -p <PID> -e trace=network,poll,select,epoll_wait -T

# Eğer çıktıda şunu görüyorsanız, thread sonsuz bloklanmıştır:
# recvfrom(3, ... ) = ? ERESTARTSYS (To be restarted) <unfinished ...>
```

### 2. `ss` ve `netstat` ile Soket Bellek Kuyruklarını İnceleme
```bash
# Soketlerin Alıcı (Recv-Q) ve Gönderici (Send-Q) kuyruk boyutları:
ss -tuna

# Eğer Recv-Q doluysa fakat uygulama okumuyorsa, uygulama başka bir sokette bloklanmış olabilir!
```

### 3. Kısmi Yazma (Partial Send) Yönetimi
Non-blocking soketlerde `send()` çağrısı çekirdek gönderim tamponu (`sk_sndbuf`) dolduğunda istediğiniz tüm baytları yazamaz! Gönderilen bayt miktarını mutlaka kontrol etmeli ve kalan kısmı tamponlayıp soket tekrar yazılabilir (`EPOLLOUT`) olduğunda iletmelisiniz.

---

## 14. Günün Mini Uygulaması: Taktik Aviyonik Telemetri İstemci-Sunucu

Günün mini uygulamasında, bir yer istasyonu ve İHA aviyonik bilgisayarı arasında `O_NONBLOCK` soket kullanarak karşılıklı veri alışverişi yapan, bağlantıyı `EINPROGRESS` kontrolüyle kuran ve veri gelmediğinde döngü determinizmini koruyan C++20 mimarisini modelledik.

### Temel Doğrulama Adımları:
1. **Normal Test:** Kesintisiz veri akışında non-blocking soketin veriyi sıfır gecikmeyle alması.
2. **Hata Testi (Sabotaj):** Veri kesintisinde blocking soketin döngüyü kilitlediğinin, non-blocking soketin ise `EAGAIN` ile döngüyü $10.0\ \text{ms}$'de tamamladığının ispatı.

---

## 15. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **Busy-Polling (Aralıksız Döngü):** `recv()` çağrısının `EAGAIN` döndüğü durumda CPU'yu dinlendirmeden veya `epoll` kullanmadan döngüyü çevirmek. CPU çekirdeğini %100 tüketir ve gömülü sistemleri aşırı ısıtır.
2. **EAGAIN ile Gerçek Hatayı Karıştırmak:** `recv() < 0` olduğunda `errno == EAGAIN` veya `EWOULDBLOCK` kontrolü yapmadan bağlantıyı kapatmak (`close(fd)`). Bu durum geçici olarak veri yokken sağlam bağlantının koparılmasına yol açar.
3. **EINPROGRESS Kontrolünü Atlamak:** Non-blocking `connect()` sonrası `getsockopt(fd, SOL_SOCKET, SO_ERROR, ...)` ile soket durumunu doğrulamadan veri yazmaya çalışmak.
4. **Kısmi Gönderimleri (Partial Write) Yoksaymak:** `send()` fonksiyonunun gönderilmek istenen veriden daha az bayt yazabileceğini unutmak ve kalan veriyi çöpe atmak.

---

## 16. Mülakat ve Saha Deneyimi Soruları (ASELSAN / HAVELSAN / TUSAŞ)

### Soru 1: Bir İHA uçuş kontrol bilgisayarında telemetri soketi neden asla varsayılan bloklanan modda bırakılmamalıdır?
**Cevap:** Otopilot kontrol döngüsü sert gerçek zamanlı (hard real-time, örn. $100\ \text{Hz}$ / $10\ \text{ms}$) çalışır. Bloklanan soket, yer istasyonu yanıt vermediğinde veya RF link koptuğunda `recv()` çağrısında thread'i uykuya alır (`TASK_INTERRUPTIBLE`). Döngü zamanında tamamlanamaz, kanatçık kontrol emirleri üretilemez ve hava aracı aerodinamik kontrolünü kaybederek kaza kırıma uğrar. Soket `O_NONBLOCK` olmalıdır.

### Soru 2: Non-blocking bir sokette `connect()` fonksiyonu `-1` döndüğünde ve `errno == EINPROGRESS` olduğunda bağlantının başarıyla tamamlandığı nasıl doğrulanır?
**Cevap:** Soket bir I/O multiplexer'a (`epoll` veya `poll`) yazılabilirlik (`EPOLLOUT`) filtresiyle kaydedilir. 3-Way Handshake bittiğinde soket yazılabilir tetiklenir. Ancak bu bağlantının kurulduğunu garanti etmez (karşı taraf `RST` dönmüş veya timeout olmuş da olabilir). Bu nedenle `getsockopt(fd, SOL_SOCKET, SO_ERROR, &err, &len)` çağrılarak hata kodu okunur. Eğer `err == 0` ise bağlantı başarıyla kurulmuştur.

### Soru 3: Non-blocking soket kullanırken CPU kullanımını %0'da tutup aynı zamanda mikrosaniye seviyesinde tepki süresi nasıl elde edilir?
**Cevap:** Soketler tek başlarına busy-poll döngüsünde çalıştırılmaz. Linux çekirdeğinin `epoll_wait()` sistem çağrısı kullanılır. Thread, çekirdek tarafından olay gelene kadar uyutulur (sıfır CPU tüketimi). NIC'ten paket ulaştığında donanım kesmesi thread'i anında uyandırır ve mikrosaniye mertebesinde tepki üretilir.

---

## 17. Gün Sonu Özeti ve 3-Cümle Çıkarımı

1. **Blocking vs Non-Blocking Soket Nedir?:** Bloklanan soket veri hazır olana kadar çağıran iş parçacığını donduran varsayılan model iken; bloklanmayan soket (`O_NONBLOCK`) veri yoksa anında `EAGAIN` dönerek thread'in akışını kesmeyen asenkron I/O modelidir.
2. **Hangi Problemi Çözer?:** Gerçek zamanlı aviyonik, radar ve füze seyrüsefer döngülerinde ağ gecikmeleri veya paket eksikliği yüzünden kritik kontrol döngülerinin kilitlenmesini (deadlock ve jitter) engeller.
3. **Hangi Trade-off/Hata Sınıfını Getirir?:** Daha karmaşık bir durum makinesi, asenkron `connect()` (`EINPROGRESS`) ve kısmi yazma yönetimi gerektirir; tedbirsiz döngülerde %100 CPU tüketen Busy-Polling felaketine yol açabilir.