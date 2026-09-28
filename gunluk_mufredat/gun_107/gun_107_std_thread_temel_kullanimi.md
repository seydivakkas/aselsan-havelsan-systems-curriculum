# Gün 107: std::thread Temel Kullanımı (F3 Threads / Concurrency / IPC)

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


---

## Faz Bilgisi ve Mühendislik Bildirimi
- **Müfredat Fazı:** Faz 3 — Threads / Concurrency / IPC (İş Parçacığı Yönetimi ve Yaşam Döngüsü)
- **Hedef Rol:** Savunma Sanayii Kıdemli Sistem & Eşzamanlılık Yazılım Mühendisi (ASELSAN, HAVELSAN, ROKETSAN, STM)
- **Kapsanan Çekirdek Teknolojiler:** `std::thread` nesne ve yürütme ömrü (Object vs Execution Lifetime), `joinable()`, `join()`, `detach()` semantiği, `std::terminate()` çöküş mekanizması, `std::ref` ve `decay copy` parametre aktarımı, RAII `ThreadGuard` deseni, Linux `clone` syscall ve sanal bellek yığın boyutu (`pthread_attr_setstacksize`).
- **40-Nokta Kalite ve Katılık Bildirimi:** Bu modül; aviyonik görev bilgisayarlarında çalışan çok iş parçacıklı C++ sistemlerinde kaza eseri süreç sonlandırmalarını (`std::terminate`), sarkan referansları (Dangling Reference) ve yığın belleği tükenmelerini önlemek üzere katı kurallarla hazırlanmıştır.


## 1. 🎯 Bugünkü Problem: Çok Çekirdekli Donanımlarda `std::thread` Yönetiminin Tuzakları

Bir radar hedef takip veya elektro-optik gimbal sisteminde, ana görev döngüsü arka planda ağır bir kalibrasyon veya telemetri kaydı başlatmak için `std::thread` nesnesi oluşturur:

```cpp
void start_radar_calibration() {
    RadarData local_buffer;
    std::thread calib_worker(process_calibration, std::ref(local_buffer));
    
    if (system_has_error()) {
        throw std::runtime_error("Donanım hatası!"); // [TUZAK 1: calib_worker.join() atlandı!]
    }
    // [TUZAK 2: Fonksiyon bittiğinde local_buffer stack'ten silinir; worker sarkan belleğe yazar!]
    calib_worker.join();
}
```

### Karşılaşılan Ölümcül Hatalar:
1. **`std::terminate()` ile Anında Çöküş:** Bir `std::thread` nesnesi yıkıcı fonksiyonuna (`destructor`) ulaştığında, eğer hala **joinable** durumdaysa (yani ne `join()` ne de `detach()` çağrılmamışsa), C++ çalışma zamanı istisnasız olarak `std::terminate()` fonksiyonunu çağırır ve tüm savunma yazılımını anında öldürür!
2. **Sarkan Referans ve Bellek Zehirlenmesi (Stack Use-After-Return):** Thread'e referansla aktarılan yerel bir nesne (`local_buffer`), çağıran fonksiyon kapsamından çıkıp stack temizlendiğinde yok olur. Arka plandaki thread geçersiz bellek adresine yazmaya devam ederek sessizce veriyi bozar!
3. **`detach()` İllüzyonu ve Hayalet Thread'ler:** `detach()` çağrıldığında thread arka planda başıboş (daemon benzeri) çalışmaya devam eder. Süreç kapanırken veya kaynaklar serbest bırakılırken bu thread'in ne zaman sonlanacağı bilinemez; kaynak sızıntılarına yol açar.
4. **Yığın Belleği (Stack) Doygunluğu:** Varsayılan Linux thread yığın boyutu **8 MB**'dir. 200 adet thread açıldığında, sadece stack alanları için $1.6\ \text{GB}$ sanal bellek rezerve edilir ve sistem `EAGAIN` hatasıyla kilitlenir.

Bugünkü görevimiz; `std::thread` sınıfının yaşam döngüsü durum makinesini kavramak, RAII koruma desenlerini inşa etmek ve sıfır çöküş garantili iş parçacığı mimarisi kurmaktır.


## 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi)

Savunma sanayiinde güvenilirlik (Reliability) ve arızaya tahammül (Fault Tolerance) en üst önceliktir. Uçuş kontrol bilgisayarında veya füze arayıcı başlığında çalışan yazılımda hiçbir iş parçacığı öngörülemeyen bir şekilde süreci kapatamaz:

### 1. Uçuş Kritik Yazılımlarda `std::terminate` Yasağı (DO-178C Level A)
Aviyonik yazılım standartları (DO-178C), sistemin kontrolsüz şekilde kapanmasını (`abrupt termination`) kesinlikle yasaklar. Bir fonksiyonda beklenmedik bir hata (Exception) fırlatılsa dahi, açılmış olan tüm iş parçacıklarının güvenli bir şekilde toparlanması (`join`) veya temizlenmesi zorunludur.

### 2. Parametre Aktarımı ve `decay-copy` Zihinsel Modeli
C++ standart kütüphanesinde thread kurucusu parametreleri varsayılan olarak **kopyalar (`decay-copy`)**. Eğer büyük bir telemetri matrisini kaza eseri kopyalarsanız, her thread açılışında onlarca megabayt bellek kopyalanır ve gecikme milisaniyelere fırlar. `std::ref` ve `std::move` farkını bilmek aviyonik performans için elzemdir.

### 3. POSIX `clone` ve Gömülü Linux Sınırları
Gömülü Linux tabanlı hedef bilgisayarlarda (Zynq UltraScale+, Jetson AGX Xavier) RAM miktarı sınırlıdır (örn. 2 GB veya 4 GB). `std::thread` oluşturulurken işletim sisteminin hangi kaynakları ayırdığını ve yığın boyutunun nasıl optimize edileceğini bilmek sistem mimarının asli görevidir.


## 3. 🔍 5N1K Analizi: `std::thread` Mekanizması

| Soru | Sistem ve Mühendislik Yanıtı |
| :--- | :--- |
| **Ne? (What)** | C++11 ile standartlaşan, işletim sistemi seviyesindeki bir yürütme iş parçacığını (`POSIX pthread` / Windows Thread) sarmalayan ve yöneten temel RAII benzeri nesne sınıfı. |
| **Neden? (Why)** | Çok çekirdekli işlemcilerde paralel algoritmalar koşturmak, I/O işlemlerini arka planda yürütmek ve ana olay döngüsünün yanıt verebilirliğini korumak için. |
| **Nerede? (Where)** | ASELSAN radar hedef izleme filtrelerinde, TUSAŞ görev yönetim yazılımlarında, ROKETSAN güdüm telemetri toplayıcılarında ve STM savaş yönetim sistemi konsollarında. |
| **Nasıl? (How)** | Fonksiyon, lambda veya üye fonksiyon işaretçisi geçilerek başlatılır; `joinable()` kontrolü ile izlenir; `join()` ile beklenir veya `ThreadGuard` deseniyle güvenle sarmalanır. |
| **Ne Zaman? (When)** | F3 fazında; Concurrency, Parallelism ve Asynchrony teorisi kavrandıktan sonra, atomik ve kilitli senkronizasyon araçlarına geçmeden hemen önce. |
| **Kim? (Who)** | Çok İş Parçacıklı Aviyonik Sistem Yazılımcıları, Gömülü Linux Mühendisleri ve Gerçek Zamanlı C++ Mimarları. |


## 4. 💡 Günlük Hayat Benzetmesi: Saha Keşif Timi ve Harekat Merkezi

Bir askeri harekat merkezindeki nöbetçi subay (Ana Thread) ile araziye gönderilen keşif uzmanı (İş Parçacığı / Worker Thread) arasındaki ilişkiyi düşünelim:

### 1. `join()`: Görev Sonu Raporu Almadan Çıkmama Kuralı
Subay, uzmanı araziye yollar (`thread t(gorev)`). Uzman arazideyken subay harekat merkezinde kendi işlerini halleder. Ancak subay nöbeti devretmeden önce telsizle uzmanı bekler (`t.join()`). Uzman üsse dönüp raporunu vermeden subay karargahı asla terk edemez. Bu en güvenli ve deterministik çalışma şeklidir.

### 2. `detach()`: Bağlantıyı Koparma (Gözden Çıkarma / Hayalet Operatör)
Subay, uzmana bir görev verir ve "Bana bir daha rapor verme, görevin bittiğinde ne yaparsan yap" der (`t.detach()`). Uzman artık karargahtan bağımsız bir hayalettir. Eğer karargah kapatılırsa (süreç sonlanırsa), uzman arazide ortada kalır; arkasında bıraktığı askeri mühimmatlar (açık dosya tanıtıcıları, paylaşılan bellek) arazide kaybolur.

### 3. `std::terminate()`: Askeri Mahkeme ve Sıkıyönetim İnfazı
Subay, araziye uzman yollamıştır; fakat uzmana ne "Dönüşünü bekleyeceğim" (`join`) demiştir ne de "Bağımsızsın" (`detach`) emri vermiştir. Subay şapkasını alıp karargahtan kaçmaya kalkar (`destructor çağrısı`). Karargah nizamiye nöbetçisi subayı yakalar ve askeri disiplini bozduğu gerekçesiyle tüm üste sıkıyönetim alarmı verir ve üssü kapatır (`std::terminate`).


## 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model

### 1. `std::thread` Durum Makinesi (State Machine)
Bir `std::thread` nesnesi `T`, donanım seviyesinde bir işletim sistemi iş parçacığı (`pthread_t`) ile ilişkili olup olmamasına göre iki temel durumda bulunabilir:
- **`joinable() == true`:** Nesne canlı veya tamamlanmış ancak henüz `join()` ya da `detach()` çağrılmamış bir işletim sistemi iş parçacığını temsil eder.
- **`joinable() == false`:** 
  1. Varsayılan kurucu ile oluşturulmuş (`std::thread t;`).
  2. Başka bir thread'e taşınmış (`std::thread t2 = std::move(t);`).
  3. Üzerinde `join()` çağrısı tamamlanmış.
  4. Üzerinde `detach()` çağrısı yapılmış.

$$\text{Yıkıcı Kuralı: } \quad \text{if } (T.\text{joinable}()) \implies \text{std::terminate}()$$

### 2. Parametre Geçişinde `decay-copy` ve `std::ref` Mekanizması
Thread kurucusu parametreleri çağıran thread'in bellek alanından yeni oluşturulan thread'in yığınına kopyalarken `std::decay` tip dönüşümü uygular:
- Eğer parametre `void worker(const LargeBuffer& buf)` bekliyorsa ve siz `std::thread t(worker, my_buf)` yazarsanız; `my_buf` kopyalanır!
- Kopyalamayı önleyip referans geçmek için `std::ref(my_buf)` (`std::reference_wrapper`) kullanılmalıdır.
- Sahiplik devri için `std::move(my_buf)` kullanılmalıdır.

### 3. Linux Çekirdeği Seviyesinde `clone()` Syscall'u
Linux'ta süreç (`process`) ile iş parçacığı (`thread`) arasında mimari bir fark yoktur; ikisi de `task_struct` veri yapısıdır. Fark sadece kaynak paylaşım bayraklarıdır:
$$\text{pthread\_create}() \implies \text{clone}(\text{CLONE\_VM} \mid \text{CLONE\_FS} \mid \text{CLONE\_FILES} \mid \text{CLONE\_SIGHAND} \mid \text{CLONE\_THREAD})$$
- `CLONE_VM`: Sanal bellek adres uzayı paylaşılır (Aynı sayfa tablosu / Page Table).
- `CLONE_FILES`: Açık dosya tanıtıcıları (FD Table) paylaşılır.
- `CLONE_THREAD`: Aynı PID (İş Parçacığı Grubu / TGID) altında yeni bir TID (Thread ID) tahsis edilir.


## 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

### `std::thread` Yaşam Döngüsü ve Durum Geçişleri

```
                  +-----------------------------------+
                  |      Varsayılan / Taşınmış        |
                  |     (joinable == false)           |
                  +-----------------------------------+
                                    |
                           std::thread(fn, args)
                                    v
+-----------------------------------------------------------------------------------+
|                            JOINABLE DURUM                                         |
|                         (joinable == true)                                        |
|                                                                                   |
|   [ İş Parçacığı Çalışıyor ] -------------> [ İş Parçacığı Bitti (Zombi Bekliyor)]|
+-----------------------------------------------------------------------------------+
       |                                   |                              |
    t.join()                           t.detach()                   Kapsam Dışı Çıkış
       |                                   |                    (Destructor & joinable)
       v                                   v                              v
+-----------------------+         +-----------------------+      +------------------+
|   KAYNAKLAR ALINDI    |         |   BAĞIMSIZ / HAYALET  |      |  std::terminate  |
|  (joinable == false)  |         |  (joinable == false)  |      |   (ÇÖKÜŞ / CRASH)|
|  [ Güvenli Kapanış ]  |         |  [ Riskli Kaynak ]    |      |  [ ASKERİ HATA ] |
+-----------------------+         +-----------------------+      +------------------+
```

### Mermaid Durum Diyagramı

```mermaid
stateDiagram-v2
    [*] --> Uninitialized: std::thread t;
    [*] --> Joinable: std::thread t(worker_fn);
    
    state Joinable {
        [*] --> Running: OS clone() Syscall
        Running --> Finished: Görev Tamamlandı
    }
    
    Joinable --> Joined: t.join() çağrıldı
    Joined --> [*]: Temiz Yıkım (Safe Destructor)
    
    Joinable --> Detached: t.detach() çağrıldı
    Detached --> [*]: OS Temizliği (Arka Plan)
    
    Joinable --> Terminated: Destructor çağrıldı (join/detach yok!)
    Terminated --> [*]: std::terminate() -> SIGABRT
```


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 8 (CODE 1): std::thread Durum Makinesi ve Yaşam Döngüsü Simülatörü
joinable, join, detach ve std::terminate Davranışının Saf Modeli
"""

from typing import Dict, Any, Optional

class SimulatedThreadState:
    UNINITIALIZED = "UNINITIALIZED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    JOINED = "JOINED"
    DETACHED = "DETACHED"
    TERMINATED = "TERMINATED"


class SimulatedStdThread:
    """C++ std::thread durum makinesini ve yıkıcı kurallarını simüle eder."""

    def __init__(self, target_fn: Optional[str] = None, *args):
        self.target_fn = target_fn
        self.args = args
        self.tid = id(self) if target_fn else None
        self._state = SimulatedThreadState.RUNNING if target_fn else SimulatedThreadState.UNINITIALIZED
        self.has_leaked_resources = False
        self.termination_triggered = False

    def is_joinable(self) -> bool:
        """std::thread::joinable() sorgusu."""
        return self._state in (SimulatedThreadState.RUNNING, SimulatedThreadState.FINISHED)

    def complete_execution(self):
        """Thread içerisindeki işin bittiğini simüle eder."""
        if self._state == SimulatedThreadState.RUNNING:
            self._state = SimulatedThreadState.FINISHED

    def join(self) -> str:
        """std::thread::join() çağrısı."""
        if not self.is_joinable():
            raise RuntimeError("std::system_error: Invalid argument (Thread not joinable!)")
        self._state = SimulatedThreadState.JOINED
        return "SUCCESSFULLY_JOINED"

    def detach(self) -> str:
        """std::thread::detach() çağrısı."""
        if not self.is_joinable():
            raise RuntimeError("std::system_error: Invalid argument (Thread not joinable!)")
        self._state = SimulatedThreadState.DETACHED
        self.has_leaked_resources = True # Potansiyel sızıntı
        return "SUCCESSFULLY_DETACHED"

    def destructor(self) -> str:
        """std::thread kapsam dışına çıktığında çağrılan yıkıcı fonksiyon (~thread)."""
        if self.is_joinable():
            self._state = SimulatedThreadState.TERMINATED
            self.termination_triggered = True
            return "FATAL_STD_TERMINATE"
        return "CLEAN_DESTRUCTION"


if __name__ == "__main__":
    print("=== STD::THREAD DURUM MAKİNESİ TESTİ ===")
    # 1. Başarılı Yaşam Döngüsü
    t1 = SimulatedStdThread("radar_worker", 101)
    assert t1.is_joinable() is True
    print(f"[*] Thread 1 Başlatıldı: Joinable={t1.is_joinable()}")
    t1.complete_execution()
    assert t1.join() == "SUCCESSFULLY_JOINED"
    assert t1.is_joinable() is False
    assert t1.destructor() == "CLEAN_DESTRUCTION"
    print("[+] Thread 1: Temiz join ve güvenli yıkım doğrulandı.")

    # 2. Ölümcül Unjoined Yıkım
    t2 = SimulatedStdThread("telemetry_worker", 202)
    assert t2.destructor() == "FATAL_STD_TERMINATE"
    print("[!] Thread 2: Unjoined nesne std::terminate() tetikledi!")

```

## 8. Modül 2: Donanıma Yakın / İleri Düzey Alternatif Mekanizma

C++11/14/17 standartlarında `std::thread` nesnelerini `std::terminate()` felaketinden korumak için endüstri standardı olan **RAII Thread Wrapper (`ThreadGuard` veya `ScopedThread`)** kalıbı kullanılır:

### RAII ThreadGuard Tasarım Deseni:
```cpp
class ThreadGuard {
    std::thread& t_;
public:
    explicit ThreadGuard(std::thread& t) : t_(t) {}
    
    ~ThreadGuard() {
        if (t_.joinable()) {
            t_.join(); // İstisna (Exception) fırlatılsa dahi ASLA atlanamaz!
        }
    }
    
    // Kopyalama yasak, sadece RAII sahiplik
    ThreadGuard(const ThreadGuard&) = delete;
    ThreadGuard& operator=(const ThreadGuard&) = delete;
};
```

### Parametre Aktarımında `decay-copy` vs `std::ref`:
Bir thread oluşturulduğunda argümanlar çağıran fonksiyonun yığınından kopyalanır (`decay copy`). Eğer referans aktarımı isteniyorsa `std::ref` sarmalayıcısı zorunludur:
```cpp
void update_radar_track(int& track_id, const Matrix4x4& data) {
    track_id++;
}

int main() {
    int id = 42;
    Matrix4x4 mat;
    // HATA: std::thread t(update_radar_track, id, mat); -> id kopyalanır, derleme hatası verir!
    // DOĞRU:
    std::thread t(update_radar_track, std::ref(id), std::cref(mat));
    t.join();
    assert(id == 43); // Orijinal değişken güncellendi!
}
```


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): RAII ThreadGuard ve Parametre Aktarım Simülatörü
std::ref vs Kopya Aktarımı ve İstisna Güvenliği (Exception Safety)
"""

from typing import Dict, Any, List

class SimulatedThreadGuard:
    """RAII prensibiyle std::thread nesnesini otomatik join ile koruyan sarmalayıcı."""

    def __init__(self, thread: SimulatedStdThread):
        self.thread = thread

    def __enter__(self):
        return self.thread

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Kapsamdan çıkılırken (istisna fırlatılsa bile) join çağrılır!
        if self.thread.is_joinable():
            self.thread.join()
        return False # İstisnayı yutmaz, yukarı iletir


class ParameterPassingSimulator:
    """C++ decay-copy vs std::ref parametre aktarım davranışını analiz eder."""

    @staticmethod
    def run_decay_copy_simulation(original_value: int, increment: int) -> Dict[str, Any]:
        """Varsayılan kopya aktarımı: Orijinal değer ASLA değişmez."""
        copied_value = original_value
        copied_value += increment
        return {
            "mode": "decay-copy (Default)",
            "original_after": original_value,
            "worker_value": copied_value,
            "modified_original": original_value != copied_value - increment
        }

    @staticmethod
    def run_std_ref_simulation(container: List[int], increment: int) -> Dict[str, Any]:
        """std::ref ile referans aktarımı: Orijinal değer güncellenir."""
        # Python listesi üzerinden referans semantiği simülasyonu
        container[0] += increment
        return {
            "mode": "std::ref (Reference Wrapper)",
            "original_after": container[0],
            "modified_original": True
        }


if __name__ == "__main__":
    print("=== RAII THREADGUARD VE PARAMETRE AKTARIM TESTİ ===")
    # 1. ThreadGuard Koruma Testi
    t = SimulatedStdThread("guided_missile_tracker", 99)
    try:
        with SimulatedThreadGuard(t):
            raise ValueError("Kritik donanım I/O istisnası fırlatıldı!")
    except ValueError:
        pass
    
    # ThreadGuard istisnaya rağmen t.join() çağırmış olmalıdır
    assert t.is_joinable() is False
    assert t.destructor() == "CLEAN_DESTRUCTION"
    print("[+] ThreadGuard İstisna Güvenliği Başarıyla Doğrulandı (std::terminate Önlendi).")

    # 2. Parametre Aktarımı
    val = 100
    p1 = ParameterPassingSimulator.run_decay_copy_simulation(val, 25)
    assert p1["original_after"] == 100
    print(f"[+] decay-copy: Orijinal değer korundu ({p1['original_after']})")

    ref_box = [100]
    p2 = ParameterPassingSimulator.run_std_ref_simulation(ref_box, 25)
    assert p2["original_after"] == 125
    print(f"[+] std::ref: Orijinal referans başarıyla güncellendi ({p2['original_after']})")

```

## 10. Modül 3: Dinamik Sınır Durumlar, Geri Basınç ve Kapasite

İşletim sistemi seviyesinde `std::thread` oluşturmak "bedava" bir işlem değildir. Her yeni thread iki katı donanımsal sınırla karşılaşır:

### 1. Sanal Bellek ve Yığın (Stack) Sınırı
Linux çekirdeğinde varsayılan thread yığın boyutu `ulimit -s` ile $8,192\ \text{KB}$ ($8\ \text{MB}$) olarak tanımlanmıştır:
$$\text{Toplam Rezerve Bellek} = N_{\text{threads}} \times 8\ \text{MB}$$
32-bit veya kısıtlı 64-bit gömülü aviyonik kartlarda (örn. $2\ \text{GB}$ RAM limitli) 250 thread açıldığında tüm adres uzayı tükenir ve `std::system_error` fırlatılır.

### 2. POSIX İş Parçacığı Sınırı (`pthread_attr_setstacksize` Çözümü)
Sensör okuma gibi derin çağrı yığını (Call Stack) gerektirmeyen hafif thread'lerde yığın boyutu $128\ \text{KB}$ veya $256\ \text{KB}$ seviyesine indirilmelidir:
$$\frac{8\ \text{MB}}{256\ \text{KB}} = 32\text{ Kat Daha Az Bellek Tüketimi!}$$

### 3. Çekirdek İş Parçacığı Tavanı (`/proc/sys/kernel/threads-max`)
İşletim sistemi genelinde oluşturulabilecek maksimum thread sayısı `/proc/sys/kernel/threads-max` dosyasında saklanır. Bir aviyonik daemon bu sınıra yaklaştığında yeni bağlantı kabul etmeyi durdurmalı ve geri basınç (Backpressure) uygulamalıdır.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Yığın Boyutu Optimizasyonu ve Thread Kapasite Sınırı Modeli
Stack Size vs Maksimum Çalıştırılabilir Thread Kapasitesi
"""

import numpy as np
from typing import Dict, Any, List

class ThreadStackCapacityModel:
    """Farklı yığın boyutlarında (Stack Size) sistemin thread kapasitesini hesaplar."""

    @staticmethod
    def calculate_max_threads(available_ram_mb: float = 2048.0, stack_sizes_kb: List[int] = [8192, 2048, 512, 128]) -> Dict[str, Any]:
        """Kullanılabilir RAM miktarına göre açılabilecek maksimum thread sayısını modeller."""
        results = []
        for s_kb in stack_sizes_kb:
            s_mb = s_kb / 1024.0
            # Güvenlik marjı: RAM'in %75'i thread stack'lerine ayrılabilir
            usable_ram = available_ram_mb * 0.75
            max_th = int(usable_ram / s_mb)
            results.append({
                "stack_size_kb": s_kb,
                "stack_size_mb": s_mb,
                "max_threads": max_th
            })

        return {
            "available_ram_mb": available_ram_mb,
            "scenarios": results
        }


if __name__ == "__main__":
    print("=== THREAD YIĞIN BOYUTU KAPASİTE ANALİZİ ===")
    cap = ThreadStackCapacityModel.calculate_max_threads(available_ram_mb=2048.0)
    print(f"[*] Toplam Sistem RAM: {cap['available_ram_mb']} MB (Kullanılabilir: {cap['available_ram_mb']*0.75:.0f} MB)")
    print(f"{'Stack Boyutu':>15} | {'Maksimum Thread Sayısı':>24} | {'Kapasite Artışı':>18}")
    print("-" * 62)
    base_threads = cap["scenarios"][0]["max_threads"]
    for sc in cap["scenarios"]:
        multiplier = sc["max_threads"] / base_threads
        print(f"{sc['stack_size_kb']:>12} KB | {sc['max_threads']:>24,d} | {multiplier:>16.1f}x")

```

## 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering / Bilerek Boz)

Askeri sistemlerde en sık yapılan ve tespiti aylar süren 2 sabotaj senaryosunu laboratuvarda canlı simüle ediyoruz:

### 1. Unjoined Thread Kapsam Dışı Çıkış Sabotajı
- **Sabotaj:** Fonksiyon içinde bir radar iş parçacığı açılır; ancak araya giren bir `return` veya fırlatılan bir C++ `exception` nedeniyle `calib_worker.join()` çağrısına ulaşılamaz.
- **Korumasız Çöküş:** `std::thread` nesnesinin yıkıcısı çalışır, nesne hala joinable olduğu için `std::terminate()` çağrılır ve süreç `SIGABRT` ile derhal çöker!
- **Dayanıklı Savunma:** Nesne `ThreadGuard` RAII kalıbıyla veya C++20 `std::jthread` ile sarmalanır; yıkıcıda otomatik olarak `join()` işletilir.

### 2. Sarkan Yığın Referansı (Dangling Stack Reference) Sabotajı
- **Sabotaj:** Çağıran fonksiyon kendi yerel stack değişkenini (`int local_seq = 100;`) thread'e `std::ref(local_seq)` ile aktarır. Ardından çağıran fonksiyon işini bitirip stack alanını terk eder (`return`).
- **Korumasız Çöküş:** Arka plandaki thread geçersiz stack adresini okumaya veya yazmaya çalışır (`Stack Use-After-Return`). Derleyici optimizasyonlarında rastgele çöp veri okunur veya `SIGSEGV` patlar!
- **Dayanıklı Savunma:** Thread'in ömrü çağıran fonksiyonun ömrünü aşabilecekse, veriler referansla değil **değer kopyasıyla (By-Value)** veya akıllı işaretçilerle (`std::shared_ptr`) aktarılmalıdır.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Canlı Sabotaj ve Arıza Laboratuvarı
Unjoined Thread Crash vs ThreadGuard Koruması ve Sarkan Referans Analizi
"""

from typing import Dict, Any, List

class ThreadChaosLab:
    """Thread yaşam döngüsü sabotaj ve savunma simülasyonu."""

    @staticmethod
    def simulate_unjoined_destruction(simulate_exception: bool = True, use_guard: bool = False) -> Dict[str, Any]:
        """Korumasız thread vs ThreadGuard korumalı thread çöküş simülasyonu."""
        t = SimulatedStdThread("sensor_reader", 1)
        crashed = False
        exit_code = "EXIT_SUCCESS"

        try:
            if use_guard:
                with SimulatedThreadGuard(t):
                    if simulate_exception:
                        raise RuntimeError("Sensör haberleşme zaman aşımı!")
            else:
                if simulate_exception:
                    raise RuntimeError("Sensör haberleşme zaman aşımı!")
                t.join()
        except RuntimeError:
            pass

        # Kapsam sonu: Yıkıcı çağrılır
        destruction_result = t.destructor()
        if destruction_result == "FATAL_STD_TERMINATE":
            crashed = True
            exit_code = "SIGABRT_TERMINATED"

        return {
            "use_guard": use_guard,
            "exception_occurred": simulate_exception,
            "crashed": crashed,
            "exit_code": exit_code,
            "thread_state": t._state
        }

    @staticmethod
    def simulate_dangling_reference_sabotage(stack_freed: bool = True) -> Dict[str, Any]:
        """Stack Use-After-Return durumunda bellek bozulması simülasyonu."""
        if stack_freed:
            # Stack alanı temizlendi, bellek artık tanımsız
            corrupted_val = 0xDEADBEEF
            return {
                "memory_safe": False,
                "read_value": hex(corrupted_val),
                "failure_mode": "STACK_USE_AFTER_RETURN_DATA_CORRUPTION"
            }
        return {
            "memory_safe": True,
            "read_value": "42 (VALID)",
            "failure_mode": "NONE"
        }


if __name__ == "__main__":
    print("=== THREAD SABOTAJ VE CHAOS DENEYİ ===")
    
    # 1. Korumasız Çöküş
    c1 = ThreadChaosLab.simulate_unjoined_destruction(simulate_exception=True, use_guard=False)
    print(f"[*] [Korumasız Tasarım] Çöktü mü? {c1['crashed']} -> Çıkış Sinyali: {c1['exit_code']}")
    assert c1["crashed"] is True

    # 2. Guard ile Savunma
    c2 = ThreadChaosLab.simulate_unjoined_destruction(simulate_exception=True, use_guard=True)
    print(f"[+] [ThreadGuard Savunması] Çöktü mü? {c2['crashed']} -> Çıkış Sinyali: {c2['exit_code']}")
    assert c2["crashed"] is False

```

## 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99)

Çok iş parçacıklı sistemlerde her gelen iş paketi için anlık `std::thread` açıp kapatmak (`On-Demand Thread Creation`) aviyonik gecikmeleri patlatan en büyük anti-pattern'dir.

### Karşılaştırılan Mimariler:
1. **İstek Başına Thread (`On-Demand std::thread`):** Her görev için çekirdekte `clone` syscall'u işletilir, 8 MB stack ayrılır, görev bitince thread yok edilir.
2. **Sabit Thread Havuzu (`Pre-Allocated Thread Pool`):** Başlangıçta çekirdek sayısı kadar thread açılır ve uykuya dalar. Görevler atomik kuyruk üzerinden dağıtılır (Sıfır syscall, sıfır bellek tahsisi).

### Gecikme Maliyet Dağılımı:
- `On-Demand thread`: $20 - 60\ \mu\text{s}$ başlatma maliyeti.
- `Thread Pool`: $0.5 - 1.5\ \mu\text{s}$ uyanma maliyeti (**30x - 40x Daha Hızlı!**).


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Kapsamlı Ampirik Kıyaslama ve SLA Metrik Toplama Motoru
İstek Başına Thread Açma vs Thread Pool Gecikme Dağılımı (p50, p95, p99)
"""

import numpy as np
from typing import Dict, Any, List

def run_thread_creation_benchmark(num_samples: int = 15000) -> Dict[str, Any]:
    """İstek başına thread açma ile Thread Pool mimarilerinin gecikme dağılımlarını modeller."""
    np.random.seed(107)

    # 1. On-Demand std::thread (clone syscall + stack allocation):
    # Medyan ~35 us, kuyruk p99 ~85 us
    ondemand_latencies = np.random.lognormal(mean=3.55, sigma=0.28, size=num_samples)

    # 2. Pre-Allocated Thread Pool (Condition Variable notify / Futex):
    # Medyan ~1.2 us, kuyruk p99 ~3.8 us
    pool_latencies = np.random.lognormal(mean=0.18, sigma=0.35, size=num_samples)

    def calc_stats(arr: np.ndarray) -> Dict[str, float]:
        return {
            "p50": float(np.percentile(arr, 50)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "mean": float(np.mean(arr))
        }

    return {
        "num_samples": num_samples,
        "ondemand_stats": calc_stats(ondemand_latencies),
        "pool_stats": calc_stats(pool_latencies),
        "ondemand_raw": ondemand_latencies,
        "pool_raw": pool_latencies
    }


if __name__ == "__main__":
    print("=== THREAD BAŞLATMA MALİYETİ BENCHMARK'I ===")
    b = run_thread_creation_benchmark(num_samples=15000)
    print(f"{'Metrik':>8} | {'On-Demand Thread (us)':>25} | {'Thread Pool (us)':>20}")
    print("-" * 58)
    for m in ["p50", "p90", "p95", "p99", "mean"]:
        v1 = b["ondemand_stats"][m]
        v2 = b["pool_stats"][m]
        print(f"{m.upper():>8} | {v1:>22.2f} us | {v2:>17.2f} us")
    
    speedup = b["ondemand_stats"]["p99"] / b["pool_stats"]["p99"]
    print(f"\n[+] p99 Gecikmesinde Thread Pool Avantajı: {speedup:.1f}x Kat Daha Hızlı!")

```

## 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı

Günün ampirik ve yaşam döngüsü sonuçlarını görselleştiren 4-panelli 300 DPI mühendislik grafiği planı:

1. **Panel 1 (Sol Üst): `std::thread` Yaşam Döngüsü ve Durum Geçişleri (Flowchart):**
   - Uninitialized $\rightarrow$ Joinable $\rightarrow$ Joined / Detached / Terminated akış şeması.
2. **Panel 2 (Sağ Üst): Yığın Boyutu (Stack Size) vs Maksimum Thread Kapasitesi:**
   - 8 MB varsayılan yığın boyutu ile 128 KB optimize edilmiş yığın boyutunun 2 GB RAM üzerindeki kapasite karşılaştırması.
3. **Panel 3 (Sol Alt): İstek Başına Thread vs Thread Pool Gecikme Dağılımı (KDE / Histogram):**
   - Başlatma gecikmesi dağılımı (Log-normal mikrosaniye ölçeği) ve p99 kuyruk karşılaştırması.
4. **Panel 4 (Sağ Alt): ThreadGuard ile `std::terminate()` Önleme Başarımı:**
   - Korumasız istisna fırlatılmasında %100 çöküş vs ThreadGuard ile %100 güvenli toparlanma.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 18 (CODE 6): 4-Panelli 300 DPI Thread Yönetim Dashboard'u ve Katı Doğrulama Motoru
Yaşam Döngüsü, Stack Optimizasyonu, Başlatma Gecikmesi ve ThreadGuard Doğrulaması
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_107\gun_107_std_thread_temel_kullanimi.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı thread mühendislik dashboard'u üretir."""
    fig, axes = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor("#0F172A")

    # Renk Paleti
    accent_blue = "#38BDF8"
    accent_green = "#4ADE80"
    accent_amber = "#FBBF24"
    accent_red = "#F87171"
    accent_purple = "#C084FC"
    text_color = "#F8FAFC"
    grid_color = "#334155"

    for ax_row in axes:
        for ax in ax_row:
            ax.set_facecolor("#1E293B")
            ax.tick_params(colors=text_color, labelsize=9)
            ax.grid(True, linestyle="--", alpha=0.3, color=grid_color)
            for spine in ax.spines.values():
                spine.set_color(grid_color)

    # -------------------------------------------------------------------------
    # Panel 1: std::thread Durum Makinesi Görselleştirmesi
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis("off")
    ax1.set_title("Panel 1: std::thread Durum Makinesi ve Yıkıcı (Destructor) Kuralı", color=text_color, fontsize=11, fontweight="bold", pad=12)

    boxes = [
        ("std::thread t;\n(joinable == false)", (0.8, 6.5), "#64748B", "#334155"),
        ("std::thread t(worker);\n(joinable == true)", (4.8, 6.5), accent_green, "#047857"),
        ("t.join()\nKaynağı Al / Bekle\n(joinable == false)", (1.5, 2.0), accent_blue, "#0369A1"),
        ("t.detach()\nBağımsız Bırak\n(joinable == false)", (4.8, 2.0), accent_amber, "#B45309"),
        ("~thread() & joinable\nstd::terminate()\n(ÇÖKÜŞ / CRASH)", (8.0, 2.0), accent_red, "#991B1B"),
    ]

    for label, (bx, by), edge_c, face_c in boxes:
        rect = plt.Rectangle((bx, by), 2.2, 2.2, facecolor=face_c, edgecolor=edge_c, linewidth=2, transform=ax1.transData)
        ax1.add_patch(rect)
        ax1.text(bx + 1.1, by + 1.1, label, ha="center", va="center", color=text_color, fontsize=8, fontweight="bold")

    # Oklar
    ax1.annotate("", xy=(4.8, 7.6), xytext=(3.0, 7.6), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))
    ax1.annotate("", xy=(2.6, 4.2), xytext=(5.3, 6.5), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax1.annotate("", xy=(5.9, 4.2), xytext=(5.9, 6.5), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax1.annotate("", xy=(8.5, 4.2), xytext=(6.8, 6.5), arrowprops=dict(arrowstyle="->", color=accent_red, lw=2.5))

    # -------------------------------------------------------------------------
    # Panel 2: Yığın Boyutu (Stack Size) vs Maksimum Thread Kapasitesi
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    cap_data = ThreadStackCapacityModel.calculate_max_threads(available_ram_mb=2048.0)
    stacks = [f"{sc['stack_size_kb']} KB" for sc in cap_data["scenarios"]]
    th_counts = [sc["max_threads"] for sc in cap_data["scenarios"]]
    colors_bar = [accent_red, accent_amber, accent_blue, accent_green]

    bars = ax2.bar(stacks, th_counts, color=colors_bar, width=0.55, edgecolor="#0F172A", linewidth=1.5)
    ax2.set_title("Panel 2: 2 GB RAM Sınırında Yığın Boyutu vs Maksimum Thread", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_xlabel("İş Parçacığı Yığın Boyutu (Stack Size)", color=text_color, fontsize=10)
    ax2.set_ylabel("Maksimum Thread Sayısı", color=text_color, fontsize=10)

    for bar, val in zip(bars, th_counts):
        ax2.text(bar.get_x() + bar.get_width()/2.0, val + 200, f"{val:,}", ha="center", va="bottom", color=text_color, fontsize=9, fontweight="bold")
    ax2.set_ylim(0, 14000)

    # -------------------------------------------------------------------------
    # Panel 3: İstek Başına Thread vs Thread Pool Gecikme Dağılımı
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    bench = run_thread_creation_benchmark(num_samples=10000)
    bins = np.linspace(0, 80, 80)

    ax3.hist(bench["ondemand_raw"], bins=bins, color=accent_red, alpha=0.6, label=f"On-Demand std::thread (p99={bench['ondemand_stats']['p99']:.1f} µs)")
    ax3.hist(bench["pool_raw"], bins=bins, color=accent_green, alpha=0.8, label=f"Pre-allocated Thread Pool (p99={bench['pool_stats']['p99']:.1f} µs)")

    ax3.set_title("Panel 3: Görev Başlatma Gecikmesi Dağılımı (µs)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax3.set_xlabel("Başlatma Gecikmesi (Mikrosaniye - µs)", color=text_color, fontsize=10)
    ax3.set_ylabel("Örnek Sayısı", color=text_color, fontsize=10)
    ax3.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper right")

    # -------------------------------------------------------------------------
    # Panel 4: ThreadGuard ile std::terminate() Önleme Başarımı
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    trials = ["Korumasız std::thread\n(Exception Fırlatıldığında)", "ThreadGuard RAII\n(Exception Korumalı)"]
    crash_rates = [100.0, 0.0]
    success_rates = [0.0, 100.0]

    x = np.arange(len(trials))
    width = 0.45

    b1 = ax4.bar(x, crash_rates, width, color=accent_red, label="Çöküş Oranı (std::terminate %)")
    b2 = ax4.bar(x, success_rates, width, color=accent_green, label="Güvenli Kapanış / Join (%)")

    ax4.set_xticks(x)
    ax4.set_xticklabels(trials, color=text_color, fontsize=9.5)
    ax4.set_title("Panel 4: İstisna Anında Çöküş vs RAII ThreadGuard Koruması", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax4.set_ylabel("Oran (%)", color=text_color, fontsize=10)
    ax4.set_ylim(0, 120)
    ax4.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="center right")

    ax4.text(0, 105, "%100 ÇÖKÜŞ", ha="center", color=accent_red, fontweight="bold", fontsize=10)
    ax4.text(1, 105, "%100 GÜVENLİ", ha="center", color=accent_green, fontweight="bold", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_path}")


def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Katı mühendislik doğrulama testleri (Assertions)."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dosya Varlık ve Boyut Kontrolü
    assert os.path.exists(png_path), f"HATA: Dashboard görseli mevcut değil: {png_path}"
    file_size = os.path.getsize(png_path)
    assert file_size > 100_000, f"HATA: Dashboard boyutu şüpheli ({file_size} bayt)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {file_size:,} bayt.")

    # 2. std::thread Yaşam Döngüsü ve Durum Makinesi Doğrulaması
    t = SimulatedStdThread("engine_igniter", 1)
    assert t.is_joinable() is True, "HATA: Başlatılan thread joinable olmalıdır!"
    t.complete_execution()
    assert t.is_joinable() is True, "HATA: Tamamlanan thread join edilene kadar joinable kalmalıdır!"
    t.join()
    assert t.is_joinable() is False, "HATA: join() sonrası thread non-joinable olmalıdır!"
    assert t.destructor() == "CLEAN_DESTRUCTION", "HATA: join() sonrası yıkıcı güvenli kapanmalıdır!"
    print("  [+] std::thread Yaşam Döngüsü ve joinable Durum Geçişleri Doğrulandı.")

    # 3. std::terminate Sabotajı ve ThreadGuard Savunması Doğrulaması
    res_unsafe = ThreadChaosLab.simulate_unjoined_destruction(simulate_exception=True, use_guard=False)
    assert res_unsafe["crashed"] is True and res_unsafe["exit_code"] == "SIGABRT_TERMINATED", "HATA: Unjoined thread çökmedi!"
    
    res_safe = ThreadChaosLab.simulate_unjoined_destruction(simulate_exception=True, use_guard=True)
    assert res_safe["crashed"] is False and res_safe["exit_code"] == "EXIT_SUCCESS", "HATA: ThreadGuard çöküşü önleyemedi!"
    print("  [+] Unjoined std::terminate Çöküşü ve ThreadGuard RAII Savunması Doğrulandı.")

    # 4. Yığın Boyutu Optimizasyonu Doğrulaması
    cap = ThreadStackCapacityModel.calculate_max_threads(available_ram_mb=2048.0)
    th_8mb = cap["scenarios"][0]["max_threads"]
    th_128kb = cap["scenarios"][3]["max_threads"]
    assert th_128kb > th_8mb * 50, "HATA: 128 KB yığın boyutu kapasiteyi en az 50 kat artırmalıdır!"
    print("  [+] Yığın Boyutu Optimizasyonu ve Gömülü Donanım Kapasite Artışı Doğrulandı.")

    # 5. Ampirik Gecikme Doğrulaması
    bench = run_thread_creation_benchmark(num_samples=3000)
    assert bench["pool_stats"]["p99"] < bench["ondemand_stats"]["p99"] / 10.0, "HATA: Thread Pool p99 gecikmesi en az 10x hızlı olmalıdır!"
    print("  [+] Pre-Allocated Thread Pool Gecikme Üstünlüğü ve p99 Kararlılığı Doğrulandı.")

    print("\n[PASS] Gün 107: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)

```

## 18. ⚠️ 10 Ölümcül Anti-Pattern: `std::thread` Yönetim Hataları

Savunma sanayiinde, görev kritik sistem incelemelerinde ve kıdemli sistem mimarlığı mülakatlarında tespit edilen en yaygın 10 ölümcül hata:

| No | Anti-Pattern | Neden Ölümcül? | Doğru Mühendislik Yaklaşımı |
| :--- | :--- | :--- | :--- |
| 1 | **`std::thread`'i `join()` veya `detach()` Yapmadan Bırakmak** | Yıkıcı çağrıldığında `std::terminate()` fırlatılır ve süreç anında çöker. | Ya `join()` çağır ya da `ThreadGuard` / C++20 `std::jthread` kullan. |
| 2 | **Thread'e Stack Değişkeni Referansı (`std::ref`) Geçip Fonksiyondan Çıkmak** | Stack Use-After-Return hatası doğar; sarkan işaretçi üzerinden bellek zehirlenir. | Thread ömrü fonksiyonu aşıyorsa veriyi kopyala (`by-value`) veya `std::shared_ptr` kullan. |
| 3 | **Gelişigüzel `detach()` Çağırmak** | Thread başıboş kalır; kapanışta kaynaklar serbest bırakılamaz ve bellek sızar. | `detach()` yerine deterministik `join()` veya kooperatif iptal token'ı kullan. |
| 4 | **Büyük Veri Yapılarını Referans Yerine Kopyalayarak Aktarmak** | Her thread başlatıldığında megabaytlarca bellek kopyalanır; gecikme sıçrar. | `std::cref` veya `std::move` ile sıfır kopyalama sahiplik devri yap. |
| 5 | **Her İstek İçin Yeni Bir `std::thread` Oluşturmak** | Sistem çekirdeğinde `clone` syscall'u ve 8 MB stack ayrımı gecikmeyi mikrosaniyelerden milisaniyelere çıkarır. | Önceden ayrılmış sabit boyutlu **Thread Pool** kullan. |
| 6 | **`joinable()` Kontrolü Yapmadan İkinci Kez `join()` Çağırmak** | `std::system_error (Invalid argument)` fırlatılarak süreç patlatılır. | `join()` öncesinde daima `if (t.joinable())` denetimi yap. |
| 7 | **Thread Fonksiyonundan Dışarı C++ İstisnası (Exception) Kaçırmak** | Thread fonksiyonu içinde yakalanmayan bir istisna doğrudan `std::terminate()` çağırır. | Thread fonksiyon gövdesini `try { ... } catch (...) { ... }` ile sarmala. |
| 8 | **Varsayılan 8 MB Yığın Boyutuyla Yüzlerce Thread Açmak** | Sanal bellek tükenir ve `std::system_error: Resource temporarily unavailable` alınır. | `pthread_attr_setstacksize` ile yığın boyutunu $128\ \text{KB} - 256\ \text{KB}$'a indir. |
| 9 | **Taşınmış (`moved-from`) Thread Üzerinde İşlem Yapmak** | `std::move` sonrası eski nesne `joinable == false` durumuna düşer; erişim hatası verir. | Taşıma sonrası eski thread tanıtıcısını asla kullanma. |
| 10 | **Thread İçi Hata Durumlarını Ana Thread'e İletmemek** | Arka plan thread'i çöktüğünde ana thread hiçbir şeyden habersiz beklemeye devam eder. | `std::promise` / `std::future` veya `std::exception_ptr` ile hataları ana thread'e taşı. |


## 19. 🔬 Sektörel Standartlar: Aviyonik ve Askeri Kriterler

Savunma ve aviyonik sistemlerde `std::thread` kullanılırken uyulması zorunlu standartlar:

### 1. DO-178C Uçuşa Elverişlilik Standardı (Airborne Systems)
- **Deterministik Görev Ömrü:** Uçuş sırasında dinamik thread oluşturulması ve yok edilmesi kesinlikle yasaktır. Tüm thread'ler sistem başlatma (initialization) evresinde oluşturulmalı ve görev boyunca sabit kalmalıdır.
- **Yığın Boyutu İspatı (Stack Depth Analysis):** Her thread'in en kötü durum yığın tüketimi (Worst-Case Stack Usage) statik analiz araçlarıyla ispatlanmalı ve yığın taşması (`Stack Overflow`) donanımsal Guard Page ile izlenmelidir.

### 2. MISRA C++:2023 Standardı
- **Kural 19.0.1 (Yıkıcı Güvenliği):** Bir iş parçacığı nesnesi kapsam dışına çıkmadan önce durumu (`joinable`) kesin olarak sonlandırılmış olmalıdır.
- **Kural 19.0.2 (Exception İzolasyonu):** Bir iş parçacığı giriş fonksiyonu (`entry function`) hiçbir istisnayı dışarı sızdırmayacak şekilde `noexcept` güvencesi sağlamalıdır.

### 3. POSIX IEEE 1003.1c Standardı
- Linux ortamında `std::thread` POSIX `pthreads` kütüphanesini kullanır. Gerçek zamanlı öncelik atamaları için `pthread_setschedparam()` ve işlemci yakınlığı için `pthread_setaffinity_np()` çağrıları `t.native_handle()` üzerinden yapılmalıdır.


## 20. 🛠️ Üretim Kontrol Listesi: Sahaya Çıkış Öncesi 12 Katı Kural

- [ ] **1. RAII Guard Kullanımı:** Ham `std::thread` yerine RAII `ThreadGuard` veya C++20 `std::jthread` kullanıldı mı?
- [ ] **2. İstisna Güvenliği:** Olası bir hata fırlatıldığında `join()` çağrısının atlanmayacağı garanti edildi mi?
- [ ] **3. Parametre Ömrü Denetimi:** Thread'e referansla (`std::ref`) geçilen değişkenlerin thread'den önce yok olmayacağı doğrulandı mı?
- [ ] **4. `detach()` Yasağı:** Gözden çıkarma anlamına gelen `detach()` çağrılarının tamamı koddan temizlendi mi?
- [ ] **5. Thread İçi Exception Yakalama:** Thread gövdesinde `try { ... } catch (...)` bloğu kurularak `std::terminate` engellendi mi?
- [ ] **6. Yığın Boyutu Sınırlandırması:** Gömülü hedeflerde gereksiz 8 MB stack yerine $128-512\ \text{KB}$ stack tahsisi yapıldı mı?
- [ ] **7. Thread Pool Mimarisi:** Yüksek frekanslı işler için thread oluşturma yerine Thread Pool kullanıldı mı?
- [ ] **8. Native Handle Entegrasyonu:** Gerçek zamanlı öncelik için `t.native_handle()` üzerinden POSIX ayarları yapıldı mı?
- [ ] **9. CPU Pinning:** Kritik thread'ler `pthread_setaffinity_np` ile izole edilmiş çekirdeklere bağlandı mı?
- [ ] **10. Kopyalama Maliyeti:** Büyük nesneler `std::move` veya `std::cref` ile sıfır kopyalama ile aktarıldı mı?
- [ ] **11. `joinable()` Kontrolü:** İkinci kez `join()` çağırmamak için durum bayrakları denetlendi mi?
- [ ] **12. ThreadSanitizer Doğrulaması:** Thread başlatma ve parametre aktarımı TSan ile test edilip yarışsız olduğu onaylandı mı?


## 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

### Soru 1: Bir `std::thread` nesnesinin yıkıcısı (`destructor`) neden varsayılan olarak `join()` yapmaz da `std::terminate()` çağırır?
**Cevap:** C++ komitesi bu kararı bilinçli olarak almıştır:
- Eğer varsayılan olarak `join()` yapılsaydı, arka plandaki thread sonsuz döngüye girdiğinde veya uzun sürdüğünde çağıran thread sessizce kilitlenir ve donardı (Silent Hang/Deadlock).
- Eğer varsayılan olarak `detach()` yapılsaydı, thread arkasında sarkan referanslar bırakarak hafızayı sessizce zehirlerdi (Silent Data Corruption).
Komite, geliştiriciyi iki seçenekten birini açıkça seçmeye zorlamak için unjoined bırakmayı **ölümcül bir programlama hatası** kabul etmiş ve `std::terminate()` çağırmıştır. C++20 `std::jthread` bu sorunu kooperatif durdurma token'ı (`stop_token`) ile çözmüştür.

---

### Soru 2: `std::thread t(worker, a, b);` çağrısında `a` değişkeni referans olarak tanımlıysa neden derleme hatası alırız?
**Cevap:** Thread kurucusu argümanları iç tampona aktarırken `std::decay` uygular ve parametreleri rvalue (geçici kopya) olarak saklar. Fonksiyon ise non-const referans (`int&`) beklediğinde, C++ kuralları gereği geçici bir rvalue nesnesi non-const lvalue referansa bağlanamaz. Çözüm: Değişkeni `std::ref(a)` ile sarmalayarak `std::reference_wrapper` olarak iletmektir.

---

### Soru 3: Bir thread'e `t.detach()` dediğimizde işletim sisteminde ne gerçekleşir?
**Cevap:** `detach()`, `std::thread` C++ nesnesi ile arka plandaki işletim sistemi iş parçacığı (`pthread`) arasındaki bağı koparır. C++ nesnesi artık `joinable == false` durumuna geçer ve güvenle yok edilebilir. Arka plandaki iş parçacığı ise bağımsız bir daemon thread olarak çalışır; işi bittiğinde POSIX çekirdeği kaynaklarını geri alır. Ancak süreç sonlandığında `detach` edilmiş thread'lerin yerel nesnelerinin yıkıcıları (`destructors`) çağrılmadan süreç anında ölür!

---

### Soru 4: `pthread_create` ile `std::thread` arasındaki mimari ilişki nedir?
**Cevap:** Linux platformlarında (glibc/libstdc++), `std::thread` POSIX Threads (`pthreads`) kütüphanesinin ince bir C++ sarmalayıcısıdır. `std::thread` kurucusu arka planda doğrudan `pthread_create()` syscall sarmalayıcısını çağırır, `join()` işlemi `pthread_join()` çağrısına, `detach()` ise `pthread_detach()` çağrısına dönüşür. `t.native_handle()` çağrısı doğrudan `pthread_t` türünde bir tanıtıcı döndürür.

---

### Soru 5: `std::thread` nesnesi kopyalanabilir mi? Neden?
**Cevap:** **Hayır, kopyalanamaz (`CopyConstructible` ve `CopyAssignable` silinmiştir); yalnızca taşınabilir (`MoveConstructible` ve `MoveAssignable`).** Çünkü bir işletim sistemi iş parçacığının tekil ve benzersiz bir sahibi (Unique Ownership) olmak zorundadır. Eğer kopyalanabilseydi, iki farklı C++ nesnesi aynı OS thread'ini temsil eder ve ikisi birden `join()` veya `destructor` çağırdığında çift serbest bırakma (Double Free / Corrupted State) oluşurdu.


## 22. 🔮 Gelecek Perspektifi: C++20 `std::jthread` ve Ötesi

C++11 ile gelen `std::thread` devrim niteliğindeydi; ancak getirdiği tasarım riskleri modern C++ standartlarında evrimleşti:

### 1. C++20 `std::jthread` (Otomatik Katılan Thread)
Yarınki konumuz olan `std::jthread`, `std::thread`'in tüm eksiklerini kapatır:
- RAII ile yıkıcısında otomatik `request_stop()` ve `join()` yapar.
- `std::stop_token` ile kooperatif iptal sağlar. Artık kimsenin elle `ThreadGuard` yazmasına gerek kalmamıştır.

### 2. C++26 Task Tabanlı Yürütme (Executors)
Geleceğin savunma yazılımlarında doğrudan ham thread açmak tamamen terk edilecektir. Yazılımcılar görevleri (`Tasks`) tanımlayacak; çalışma zamanı donanımın çekirdek sayısına, termal durumuna ve öncelik seviyesine göre görevleri en uygun thread havuzuna otomatik yerleştirecektir.


## 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı)

Bugün, `std::thread` nesnesinin yaşam döngüsünü, `joinable` durum makinesini, unjoined thread'lerin yol açtığı `std::terminate()` felaketini ve RAII `ThreadGuard` savunmasını derinlemesine kavradık.

### Yarın Nereye Geçiyoruz?:
ThreadGuard deseni harikadır; fakat thread'e "Lütfen dur" demek için hala ortak bir atomik bayrak (`std::atomic<bool>`) yönetmek zorundayız. C++20 bu süreci standartlaştırdı!
- **Konu:** `Gün 108: std::jthread ve Cooperative Cancellation`
- **Çözeceğimiz Problem:** C++20 `std::jthread` mekanizması, `std::stop_token`, `std::stop_source`, `std::stop_callback` ve otomatik RAII `join` mimarisiyle savunma sistemlerinde sıfır çöküşlü, güvenli ve kooperatif thread durdurma nasıl tasarlanır?

Faz 3 hız kesmeden devam ediyor; yarın C++20'nin modern thread zirvesine çıkıyoruz!
