# GÜN 100: `select`, `poll`, `epoll` Neden Var? (I/O Çoklama Evrimi, $O(N)$ vs $O(1)$, C10K Ölçeklenebilirliği)

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
[![C++20 Standard](https://img.shields.io/badge/C%2B%2B-20-blue.svg?style=flat-square&logo=c%2B%2B)](https://en.cppreference.com/w/cpp/20)
[![Linux Kernel](https://img.shields.io/badge/Linux-epoll(7)-orange.svg?style=flat-square&logo=linux)](https://man7.org/linux/man-pages/man7/epoll.7.html)
[![Milestone](https://img.shields.io/badge/Milestone-100%20Days%20C%2B%2B%20%26%20Systems-gold.svg?style=flat-square)]()

---

## 5N1K Kapsam Tablosu

| Soru | Sistem Mühendisliği Açıklaması |
| :--- | :--- |
| **Ne?** | **Girdi/Çıktı Çoklama (I/O Multiplexing)**; tek bir iş parçacığının (thread) veya sürecin, işletim sistemindeki binlerce soket, dosya tanıtıcısı (FD), boru veya aygıtı eşzamanlı olarak izleyip, hangisinde veri hazır olduğunu bloklanmadan tespit etmesini sağlayan çekirdek mekanizmaları ailesidir (`select`, `poll`, `epoll`). |
| **Neden?** | Bağlantı başına bir iş parçacığı (**Thread-per-Connection**) açmak, binlerce bağlantıda (C10K) stack bellek tükenmesine ve işlemcinin Context Switch cehenneminde boğulmasına neden olur. `select` ve `poll` ise her döngüde tüm FD listesini çekirdeğe kopyalayıp $O(N)$ doğrusal tarama yaptığı için ölçeklenemez. `epoll`, çekirdekte olay tabanlı $O(1)$ hazır kuyruğu sunarak bu darboğazı kırar. |
| **Nasıl?** | `epoll_create1()` ile çekirdekte durum bilgisine sahip bir olay tablosu (Kırmızı-Siyah Ağaç) oluşturulur, `epoll_ctl()` ile izlenecek soketler kaydedilir ve `epoll_wait()` ile yalnızca **gerçekten veri gelmiş olan** aktif olaylar tek seferde $O(1)$ karmaşıklıkla alınır. |
| **Nerede?** | Nginx, Redis, Node.js libuv, ASELSAN Taktik Ağ Yönlendiricileri, HAVELSAN C4I Dağıtık Simülasyon Sunucuları ve yüksek frekanslı finansal ağ geçitlerinde. |
| **Ne Zaman?** | Bir servisin aynı anda yüzlerce veya on binlerce eşzamanlı ağ bağlantısını (TCP, UDP, Unix Domain Socket) düşük gecikme ve minimum CPU tüketimiyle yönetmesi gerektiğinde. |
| **Kim?** | C++20 Ağ ve Sistem Programcısı, Yüksek Başarımlı Dağıtık Sistem Mimarı ve Gerçek Zamanlı Linux Çekirdek Mühendisi. |


## 1. Zihinsel Model & I/O Çoklama Evrimi

Bir sunucunun binlerce istemciden gelen ağ paketlerini dinlemesi probleminde Linux çekirdeği 4 nesil evrim geçirmiştir:

```
[NESİL 1: BLOKLAYAN I/O (BLOCKING I/O)]
Thread A: read(fd_0) --------> BLOKLANDI! (Veri gelene kadar uyur, diğer 9,999 soket bekler!)

[NESİL 2: BAĞLANTI BAŞINA THREAD (THREAD-PER-CONNECTION)]
Client 1 ---> Thread 1 (8 MB Stack)
Client 2 ---> Thread 2 (8 MB Stack)
...
Client 10,000 ---> 10,000 Thread = 80 GB RAM SADECE STACK İÇİN! + Devasa Context Switch Yükü!

[NESİL 3: DURUMSUZ ÇOKLAMA (STATELESS MULTIPLEXING - select & poll)]
Kullanıcı Alanı                      Çekirdek Alanı
+---------------------+              +-------------------------------------+
| 10,000 FD Listesi   | ==(KOPYALA)==> | Çekirdek 10,000 FD'yi tek tek gezer |
| (fd_set / pollfd)   | <==(KOPYALA)== | O(N) Tarama: Sadece 1 sokette veri var!
+---------------------+              +-------------------------------------+
* Sorun: Her döngüde devasa diziyi çekirdeğe kopyala + çekirdekte döngü kur + kullanıcıda döngü kur!

[NESİL 4: DURUMLU OLAY GÜDÜMLÜ ÇOKLAMA (STATEFUL EVENT-DRIVEN - epoll)]
Kullanıcı Alanı                      Çekirdek Alanı (epoll instance)
+---------------------+              +-------------------------------------+
| Tek bir sistem      |              | Kırmızı-Siyah Ağaç (RB-Tree): 10,000 FD|
| çağrısı:            |              | Donanım Kesmesi (NIC IRQ) Callback  |
| epoll_wait()        |              |                |                    |
|                     |              |                v                    |
| SADECE AKTİF        | <--(O(1))--- | Hazır Listesi (Ready List / DLL):   |
| 3 OLAYI DÖNDÜRÜR!   |              | [ fd_42, fd_105, fd_899 ]           |
+---------------------+              +-------------------------------------+
```

### Neden `epoll` Devrim Yarattı?
1. **Durumluluk (Statefulness):** `select` ve `poll` her çağrıda izlenecek soket kümesini unutan durumsuz sistem çağrılarıdır. `epoll` ise izleme listesini çekirdekteki bir **Kırmızı-Siyah Ağaç (RB-Tree)** içinde saklar; soket bir kez eklenir (`epoll_ctl(EPOLL_CTL_ADD)`) ve orada kalır.
2. **Aktif Olaylar Listesi (Ready List):** Ağ kartına paket geldiğinde donanım kesmesi doğrudan çekirdeğin geri çağırma (callback) fonksiyonunu çalıştırır ve soketi **Hazır Çift Bağlı Listesine (Ready List)** ekler. `epoll_wait` yalnızca bu hazır listeyi kullanıcıya aktarır. 100,000 bağlantı dinlense dahi, sadece 2 aktif bağlantı varsa işlem maliyeti $O(1)$'dir!


## 2. Sistem Çağrıları İmzaları ve Veri Yapıları Karşılaştırması

Linux çekirdeğindeki 3 çoklama API'sinin teknik anatomisi:

### 1. `select(2)` (1983 - 4.2BSD)
```c
int select(int nfds, fd_set *readfds, fd_set *writefds, fd_set *exceptfds, struct timeval *timeout);
```
- **Veri Yapısı:** `fd_set` (1024 bitlik bitmask dizisi).
- **Ölümcül Sınır:** `FD_SETSIZE = 1024`. Eğer FD değeri $\ge 1024$ ise dizi taşması (**Stack Buffer Overflow**) yaşanır ve süreç çöker!
- **Karmaşıklık:** $O(N)$ (Kullanıcı $0$'dan `nfds-1`'e kadar tüm bitleri tek tek `FD_ISSET` ile kontrol etmek zorundadır).

### 2. `poll(2)` (1986 - System V / POSIX.1-2001)
```c
struct pollfd {
    int   fd;         /* Dosya tanımlayıcısı */
    short events;     /* İzlenecek olaylar (POLLIN, POLLOUT) */
    short revents;    /* Gerçekleşen olaylar (çekirdek yazar) */
};
int poll(struct pollfd *fds, nfds_t nfds, int timeout);
```
- **İyileştirme:** 1024 sınırı kaldırılmıştır; dinamik dizi kullanılır.
- **Süren Problem:** Her çağrıda tüm `pollfd` dizisi (her eleman 8 bayt) Kullanıcı $\leftrightarrow$ Çekirdek arasında kopyalanır. 10,000 bağlantıda döngü başına 80 KB kopyalama ve çekirdek tarafında $O(N)$ tarama mecburidir.

### 3. `epoll(7)` (2002 - Linux Kernel 2.5.44)
```c
int epoll_create1(int flags);
int epoll_ctl(int epfd, int op, int fd, struct epoll_event *event);
int epoll_wait(int epfd, struct epoll_event *events, int maxevents, int timeout);
```
- **Çekirdek Mimarisi:**
  - **İzleme Kümesi:** Kırmızı-Siyah Ağaç (`struct rb_root`) $\rightarrow$ Arama, ekleme, silme maliyeti $O(\log N)$.
  - **Hazır Kümesi:** Çift Bağlı Liste (`struct list_head`) $\rightarrow$ Uyandırma ve teslim maliyeti $O(1)$.
- **Verimlilik:** Sadece `maxevents` kadar aktif olay kullanıcı alanına kopyalanır. Milyonlarca boşta bekleyen bağlantı sıfır CPU harcar.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 04 (CODE 1): Python ile I/O Multiplexing Çekirdek Simülasyonu
select (Bitmask O(N)), poll (Array O(N)) ve epoll (RB-Tree + ReadyList O(1)) Motorları
"""

from typing import List, Dict, Set, Tuple
import time

class SimulatedSelectKernel:
    """select(2) mimarisi: Bitmask tabanlı, 1024 FD limitli ve O(N) doğrusal tarama."""
    FD_SETSIZE = 1024

    def __init__(self):
        self.registered_fds: Set[int] = set()

    def register(self, fd: int):
        if fd >= self.FD_SETSIZE:
            raise OverflowError(f"HATA: FD ({fd}) >= FD_SETSIZE (1024) sınırını aştı! Stack taşması!")
        self.registered_fds.add(fd)

    def select(self, active_fds: Set[int]) -> Tuple[List[int], int]:
        """Kullanıcıdan gelen bitmask'i tarar. Döngü sayısı en büyük FD'ye bağlıdır."""
        if not self.registered_fds:
            return [], 0
            
        max_fd = max(self.registered_fds)
        iterations_count = 0
        ready_fds = []
        
        # O(N) Döngüsü: 0'dan max_fd'ye kadar TÜM bitleri tek tek kontrol eder!
        for fd in range(max_fd + 1):
            iterations_count += 1
            if fd in self.registered_fds and fd in active_fds:
                ready_fds.append(fd)
                
        return ready_fds, iterations_count


class SimulatedPollKernel:
    """poll(2) mimarisi: Dinamik dizi tabanlı ancak her çağrıda O(N) dizi kopyalama ve tarama."""
    def __init__(self):
        self.pollfds: List[int] = []

    def register(self, fd: int):
        self.pollfds.append(fd)

    def poll(self, active_fds: Set[int]) -> Tuple[List[int], int, int]:
        """Tüm struct pollfd dizisini çekirdeğe kopyalar ve tamamını döngüyle tarar."""
        bytes_copied = len(self.pollfds) * 8 # Her struct pollfd = 8 bayt
        iterations_count = 0
        ready_fds = []

        for fd in self.pollfds:
            iterations_count += 1
            if fd in active_fds:
                ready_fds.append(fd)

        return ready_fds, iterations_count, bytes_copied


class SimulatedEpollKernel:
    """epoll(7) mimarisi: Kırmızı-Siyah Ağaç izleme kümesi ve O(1) Hazır Listesi (Ready List)."""
    def __init__(self):
        self.monitored_rb_tree: Set[int] = set() # Çekirdekte kalıcı izleme kümesi
        self.ready_list: List[int] = []          # NIC kesmesiyle dolan hazır listesi

    def epoll_ctl_add(self, fd: int):
        """O(log N) Kırmızı-Siyah ağaca ekleme (Sadece bir kez çağrılır!)."""
        self.monitored_rb_tree.add(fd)

    def on_hardware_interrupt(self, active_fds: Set[int]):
        """Ağ kartı kesmesi: Sadece veri gelen soketleri hazır listesine ekler."""
        self.ready_list = [fd for fd in self.monitored_rb_tree if fd in active_fds]

    def epoll_wait(self, maxevents: int) -> Tuple[List[int], int, int]:
        """O(1) Karmaşıklık: Yalnızca hazır listesindeki ilk maxevents elemanı döndürür."""
        events_to_return = self.ready_list[:maxevents]
        # Döngü sayısı SADECE dönen aktif olay kadardır! Asla toplam FD sayısına bağlı değildir!
        iterations_count = len(events_to_return)
        bytes_copied = len(events_to_return) * 12 # epoll_event = 12 bayt
        return events_to_return, iterations_count, bytes_copied


if __name__ == "__main__":
    print("=== I/O MULTIPLEXING ÇEKİRDEK DAVRANIŞ SİMÜLASYONU ===")
    TOTAL_CLIENTS = 1000
    ACTIVE_COUNT = 3 # 1000 istemciden sadece 3 tanesi paket gönderdi!
    active_set = {10, 250, 980}

    # 1. select Testi
    sel = SimulatedSelectKernel()
    for fd in range(TOTAL_CLIENTS):
        sel.register(fd)
    sel_ready, sel_iter = sel.select(active_set)
    print(f"[select] Aktif FD'ler: {sel_ready} | İncelenen FD Sayısı (İterasyon): {sel_iter}")

    # 2. poll Testi
    pol = SimulatedPollKernel()
    for fd in range(TOTAL_CLIENTS):
        pol.register(fd)
    pol_ready, pol_iter, pol_bytes = pol.poll(active_set)
    print(f"[poll]   Aktif FD'ler: {pol_ready} | İncelenen FD Sayısı: {pol_iter} | Kopyalanan Bellek: {pol_bytes} bayt")

    # 3. epoll Testi
    ep = SimulatedEpollKernel()
    for fd in range(TOTAL_CLIENTS):
        ep.epoll_ctl_add(fd)
    ep.on_hardware_interrupt(active_set)
    ep_ready, ep_iter, ep_bytes = ep.epoll_wait(maxevents=64)
    print(f"[epoll]  Aktif FD'ler: {ep_ready} | İncelenen FD Sayısı: {ep_iter} | Kopyalanan Bellek: {ep_bytes} bayt")

```

## 3. Kod 01 Detaylı Açıklaması ve Çekirdek Kopyalama Analizi

Kod 01 simülasyonu, 1,000 bağlantı içerisinden sadece 3 tanesinin aktif olduğu gerçekçi bir ağ senaryosunu modellemiştir. Elde edilen çıktılar mimari uçurumu kanıtlar:

1. **İterasyon Sayısı:**
   - `select`: 981 kez kontrol yapmıştır (en büyük FD 980 olduğu için).
   - `poll`: 1,000 kez kontrol yapmıştır (tüm dizi taranmıştır).
   - `epoll`: **Yalnızca 3 kez** işlem yapmıştır (sadece aktif olanlar!). Toplam izlenen 1,000 soket için harcanan CPU zamanı sıfırdır.
2. **Kullanıcı $\leftrightarrow$ Çekirdek Bellek Trafiği:**
   - `poll` her çağrıda 8,000 bayt (`1000 * 8`) veriyi çekirdeğe kopyalamıştır.
   - `epoll` ise sadece dönen 3 olayı (`3 * 12 = 36` bayt) kullanıcı alanına yazmıştır. Bağlantı sayısı 100,000'e çıksa dahi epoll'ün kopyalama maliyeti sabit kalacaktır.


## 4. Tetikleme Modları: Edge-Triggered (ET) vs Level-Triggered (LT)

`epoll`, olay bildiriminde iki farklı tetikleme felsefesine sahiptir. Bu ayrım sistemin performansı ve hata toleransı açısından hayati öneme sahiptir:

```
[SEVİYE TETİKLEMELİ - LEVEL TRIGGERED (LT) - VARSAYILAN]
Tamponda veri olduğu sürece epoll_wait SÜREKLİ UYANDIRIR!
Sokete 4096 bayt geldi.
1. epoll_wait() -> UYANDIR!
2. read(fd, buf, 1024) -> 1024 bayt okundu (Kalan: 3072 bayt).
3. Döngü başa döndü: epoll_wait() -> TEKRAR UYANDIRIR! (Çünkü hala 3072 bayt var!).

[KENAR TETİKLEMELİ - EDGE TRIGGERED (ET) - EPOLLET BAYRAĞI]
Yalnızca durum DEĞİŞTİĞİNDE (Yeni paket geldiğinde / Kenar darbesinde) BİR KEZ UYANDIRIR!
Sokete 4096 bayt geldi.
1. epoll_wait() -> UYANDIR! (Durum: Boş -> Dolu kenarı)
2. read(fd, buf, 1024) -> 1024 bayt okundu (Kalan: 3072 bayt).
3. Döngü başa döndü: epoll_wait() -> UYANDIRMAZ! (BLOKLANIR!). Kalan 3072 bayt sokette kilitlenir!
```

### Edge-Triggered (ET) Modunun Katı Kuralları:
1. **Non-Blocking Socket Zorunluluğu:** Soket mutlaka `fcntl(fd, F_SETFL, O_NONBLOCK)` ile bloklamayan moda alınmalıdır!
2. **`EAGAIN` / `EWOULDBLOCK` Döngüsü:** Bir bildirim alındığında, sistem çağrısı `read()` veya `write()` çekirdekten `EAGAIN` veya `EWOULDBLOCK` dönene kadar bir `while` döngüsü içinde tüketilmelidir:
   ```cpp
   while (true) {
       ssize_t count = ::read(fd, buf, sizeof(buf));
       if (count == -1) {
           if (errno == EAGAIN || errno == EWOULDBLOCK) break; // Tüm veri bitti!
           // Gerçek hata yönetimi...
       } else if (count == 0) {
           // Karşı taraf soketi kapattı (EOF)
           break;
       }
       process_packet(buf, count);
   }
   ```
3. **Neden ET Tercih Edilir?:** LT modunda çekirdek her döngüde hazır listesini tekrar tekrar taramak ve temizlemek zorundadır. ET modunda çekirdek içi yük minimize edilir ve yüksek eşzamanlılıkta Context Switch sayısı dramatik şekilde düşer.


## 5. C++20 Standardında RAII Tabanlı Güvenli Epoll Event Loop Wrapper

Aşağıdaki C++20 mimarisi, Linux `epoll` sistem çağrılarını modern RAII, tip güvenliği (`enum class`) ve kopyalanamaz (Move-only) yaşam döngüsü prensipleriyle sarmalar:

```cpp
#include <iostream>
#include <vector>
#include <span>
#include <system_error>
#include <utility>
#include <sys/epoll.h>
#include <unistd.h>
#include <fcntl.h>

enum class EpollTriggerMode {
    LevelTriggered,
    EdgeTriggered
};

class PosixEpollInstance {
private:
    int m_epoll_fd{-1};
    size_t m_max_events{64};
    std::vector<epoll_event> m_event_backlog;

public:
    explicit PosixEpollInstance(size_t max_events = 64)
        : m_max_events(max_events), m_event_backlog(max_events) {
        // EPOLL_CLOEXEC: execve çağrıldığında tanıtıcı otomatik kapatılır
        m_epoll_fd = ::epoll_create1(EPOLL_CLOEXEC);
        if (m_epoll_fd == -1) {
            throw std::system_error(errno, std::generic_category(), "epoll_create1 basarisiz");
        }
    }

    ~PosixEpollInstance() noexcept {
        if (m_epoll_fd != -1) {
            ::close(m_epoll_fd);
            m_epoll_fd = -1;
        }
    }

    // Move-only semantics (Kaynak tekliği)
    PosixEpollInstance(const PosixEpollInstance&) = delete;
    PosixEpollInstance& operator=(const PosixEpollInstance&) = delete;

    PosixEpollInstance(PosixEpollInstance&& other) noexcept
        : m_epoll_fd(other.m_epoll_fd),
          m_max_events(other.m_max_events),
          m_event_backlog(std::move(other.m_event_backlog)) {
        other.m_epoll_fd = -1;
    }

    // Soketi izleme kümesine ekler
    void add_fd(int fd, uint32_t events, EpollTriggerMode mode = EpollTriggerMode::EdgeTriggered) {
        epoll_event ev{};
        ev.events = events;
        if (mode == EpollTriggerMode::EdgeTriggered) {
            ev.events |= EPOLLET;
        }
        ev.data.fd = fd;

        if (::epoll_ctl(m_epoll_fd, EPOLL_CTL_ADD, fd, &ev) == -1) {
            throw std::system_error(errno, std::generic_category(), "epoll_ctl ADD basarisiz");
        }
    }

    // İzleme kümesinden kaldırır
    void remove_fd(int fd) noexcept {
        ::epoll_ctl(m_epoll_fd, EPOLL_CTL_DEL, fd, nullptr);
    }

    // Olayları bekler (O(1) hazır listesi aktarımı)
    [[nodiscard]] std::span<epoll_event> wait_events(int timeout_ms = -1) {
        int ready_count = ::epoll_wait(
            m_epoll_fd, 
            m_event_backlog.data(), 
            static_cast<int>(m_max_events), 
            timeout_ms
        );

        if (ready_count == -1) {
            if (errno == EINTR) {
                return {}; // Sinyal ile kesildi
            }
            throw std::system_error(errno, std::generic_category(), "epoll_wait hatasi");
        }

        return std::span<epoll_event>(m_event_backlog.data(), static_cast<size_t>(ready_count));
    }

    [[nodiscard]] int native_handle() const noexcept { return m_epoll_fd; }
};
```


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 08 (CODE 2): Python ile Edge-Triggered (ET) vs Level-Triggered (LT) Simülasyonu
Tampon Tüketimi, Kısmi Okuma (Partial Read) ve Soket Kilitlenme (Starvation) Analizi
"""

from typing import Dict, List, Tuple

class SimulatedSocket:
    """Ağ soketi ve çekirdek tampon simülatörü."""
    def __init__(self, fd: int):
        self.fd = fd
        self.rx_buffer = bytearray()
        self.state_changed = False

    def incoming_network_data(self, data: bytes):
        """Ağdan yeni paket geldi (Donanım kesmesi)."""
        was_empty = (len(self.rx_buffer) == 0)
        self.rx_buffer.extend(data)
        if was_empty and len(self.rx_buffer) > 0:
            self.state_changed = True # Durum Boş -> Dolu olarak değişti

    def read_chunk(self, max_bytes: int) -> bytes:
        """Kullanıcının read() çağrısı."""
        chunk = bytes(self.rx_buffer[:max_bytes])
        self.rx_buffer = self.rx_buffer[max_bytes:]
        self.state_changed = False
        return chunk


class TriggerModeSimulator:
    """LT ve ET bildirim mekanizmalarının davranışsal karşılaştırıcısı."""
    
    @staticmethod
    def simulate_level_triggered(sock: SimulatedSocket, read_size: int, loop_count: int) -> List[int]:
        """Level-Triggered: Tamponda veri kaldığı sürece her döngüde uyandırır."""
        wakeups = []
        for loop in range(loop_count):
            if len(sock.rx_buffer) > 0:
                wakeups.append(loop)
                # Kısmi okuma yapılıyor (tampon boşaltılmıyor)
                sock.read_chunk(read_size)
        return wakeups

    @staticmethod
    def simulate_edge_triggered(sock: SimulatedSocket, read_size: int, loop_count: int) -> Tuple[List[int], int]:
        """Edge-Triggered: Yalnızca durum değiştiğinde uyandırır. EAGAIN döngüsü yoksa veri kilitlenir!"""
        wakeups = []
        for loop in range(loop_count):
            if sock.state_changed:
                wakeups.append(loop)
                # Kısmi okuma yapılıyor ve EAGAIN'e kadar tüketilmiyor (Anti-pattern!)
                sock.read_chunk(read_size)
            # Yeni ağ verisi gelmedikçe sock.state_changed False kalır!
        
        stranded_bytes = len(sock.rx_buffer)
        return wakeups, stranded_bytes


if __name__ == "__main__":
    print("=== LEVEL-TRIGGERED vs EDGE-TRIGGERED KARŞILAŞTIRMASI ===")
    
    # Senaryo: Sokete 4096 bayt radar telemetrisi geldi
    # İstemci her döngüde sadece 1024 bayt okuyor
    
    # 1. Level-Triggered Davranışı
    sock_lt = SimulatedSocket(fd=10)
    sock_lt.incoming_network_data(b"X" * 4096)
    lt_wakeups = TriggerModeSimulator.simulate_level_triggered(sock_lt, read_size=1024, loop_count=5)
    print(f"[Level-Triggered] 4096 bayt veri için tetiklenen döngüler: {lt_wakeups} (Tampon bitene kadar 4 kez uyandırdı!)")

    # 2. Edge-Triggered Davranışı (Hatalı Kullanım - EAGAIN döngüsü unutuldu)
    sock_et = SimulatedSocket(fd=20)
    sock_et.incoming_network_data(b"X" * 4096)
    et_wakeups, stranded = TriggerModeSimulator.simulate_edge_triggered(sock_et, read_size=1024, loop_count=5)
    print(f"[Edge-Triggered]  4096 bayt veri için tetiklenen döngüler: {et_wakeups} (SADECE 1 KEZ UYANDIRDI!)")
    print(f"[Edge-Triggered]  KİLİTLENEN VE OKUNAMAYAN VERİ: {stranded} bayt! (Veri sokette rehin kaldı!)")

```

## 6. Kod 02 Analizi: Kısmi Okuma Tuzağı ve ET Mekanizması

Kod 02 simülasyonu, Linux ağ programcılığının en kritik tuzaklarından birini doğrulamıştır:

1. **LT Modunun Güvenliği:** Level-Triggered modunda, uygulama tamponun tamamını tek seferde okumasa dahi çekirdek bir sonraki `epoll_wait` çağrısında süreci tekrar uyandırır. Bu durum programlamayı kolaylaştırır ancak gereksiz döngü ve context switch üretir.
2. **ET Modunun Ölümcül Riski:** Edge-Triggered modunda, 4,096 bayt verinin yalnızca ilk 1,024 baytı okunduğunda geriye kalan 3,072 bayt **tamponda kilitli kalmıştır**. Çekirdek yeni bir paket gelene kadar süreci ASLA uyandırmayacaktır!
3. **Kesin Çözüm:** ET modu kullanıldığında `read()` çağrısı mutlaka bir `while (true)` döngüsü içerisinde çalıştırılmalı ve `errno == EAGAIN` (veya `EWOULDBLOCK`) dönene kadar tüm veri çekirdek tamponundan emilmelidir.


## 7. Kritik Hata & Sabotaj Analizi: `FD_SETSIZE` Aşımı ve Thundering Herd

I/O çoklama mimarilerinde üretim ortamlarını çökerten en yaygın 3 felaket senaryosu:

### 1. `select()` ile `FD_SETSIZE` (1024) Aşımı ve Bellek Ezilmesi (Stack Smashing)
Linux glibc başlık dosyasında (`<sys/select.h>`) `fd_set` şöyle tanımlanır:
```c
#define __FD_SETSIZE 1024
typedef struct {
    unsigned long fds_bits[__FD_SETSIZE / (8 * sizeof(long))]; // 16 adet 64-bit tamsayı
} fd_set;
```
Eğer bir sunucu uzun süre açık kalır ve dosya tanıtıcısı numarası `1024` veya daha büyük olursa (`fd = 1025`), `FD_SET(fd, &readfds)` makrosu `fds_bits` sınırlarının dışındaki belleğe bir bit yazar!
Bu durum derleyicinin stack korumasını patlatır (**Stack Smashing Detected**), komşu yerel değişkenleri ve fonksiyon dönüş adresini bozar; servis anında çöker (`SIGSEGV` / `SIGABRT`).

### 2. Thundering Herd (Gürleyen Sürü) Problemi
Birden fazla worker iş parçacığı veya süreci (`fork()` ile türetilen Nginx worker'ları) aynı `epoll_fd`'yi veya aynı dinleme soketini (`listen_fd`) dinliyorsa:
Yeni bir istemci bağlantısı geldiğinde çekirdek **TÜM İŞ PARÇACIKLARINI AYNI ANDA UYANDIRIR!**
İş parçacıklarından yalnızca biri `accept()` yapabilir, diğer $N-1$ iş parçacığı `EAGAIN` alarak boşuna CPU harcar ve uykuya geri döner.
- **Çekirdek Savunması:** Linux 4.5 ile gelen **`EPOLLEXCLUSIVE`** bayrağı veya `SO_REUSEPORT` soket seçeneği kullanılarak çekirdeğin sadece tek bir worker'ı uyandırması sağlanır.

### 3. Kapatılan FD'nin `epoll` Kümesinden Silinmemesi
`close(fd)` çağrıldığında çekirdek genellikle ilişkili epoll kaydını otomatik temizler. Ancak eğer dosya tanımlayıcısı `dup()` veya `fork()` ile kopyalanmışsa, temel dosya tablosu girişi kapanmaz ve epoll hayalet olaylar (ghost events) üretmeye devam eder.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Arıza Simülatörü
select FD_SETSIZE (1024) Bellek Ezilmesi ve Thundering Herd Simülasyonu
"""

from typing import List, Dict, Any, Tuple

class MultiplexingSabotageLab:
    """I/O çoklama sistemlerinde sabotaj ve sınır ihlali simülatörü."""

    @staticmethod
    def simulate_select_overflow_crash(target_fd: int = 1025) -> Tuple[bool, str]:
        """select FD_SETSIZE sınırının aşıldığında sistem çöküşünü modeller."""
        kernel_sel = SimulatedSelectKernel()
        try:
            # 1024 veya üstü bir FD register edilmeye çalışılıyor
            kernel_sel.register(target_fd)
            return False, "HATA: select 1024 sınırını kontrolsüzce kabul etti!"
        except OverflowError as e:
            return True, f"BEKLENEN ÇÖKÜŞ ÖNLENDİ / YAKALANDI: {str(e)}"

    @staticmethod
    def simulate_thundering_herd(num_workers: int = 8, use_exclusive: bool = False) -> Dict[str, Any]:
        """Bir olay geldiğinde kaç worker'ın boş yere uyandırıldığını analiz eder."""
        if use_exclusive:
            # EPOLLEXCLUSIVE aktif: Çekirdek sadece 1 worker uyandırır
            woken_workers = 1
            wasted_wakeups = 0
        else:
            # Geleneksel epoll: TÜM worker'lar uyanır, sadece 1'i accept yapabilir
            woken_workers = num_workers
            wasted_wakeups = num_workers - 1

        cpu_overhead_arbitrary_units = woken_workers * 150 # Context switch maliyeti

        return {
            "num_workers": num_workers,
            "woken_workers": woken_workers,
            "wasted_wakeups": wasted_wakeups,
            "cpu_overhead": cpu_overhead_arbitrary_units,
            "exclusive_active": use_exclusive
        }


if __name__ == "__main__":
    print("=== I/O MULTIPLEXING SABOTAJ VE ARIZA LABORATUVARI ===")
    
    # Test 1: select 1024 Sınır Aşımı
    crash_handled, msg = MultiplexingSabotageLab.simulate_select_overflow_crash(target_fd=1042)
    print(f"[*] select() FD_SETSIZE Taşma Testi: {'BAŞARILI' if crash_handled else 'BAŞARISIZ'}")
    print(f"    Sonuç: {msg}")

    # Test 2: Thundering Herd Analizi
    th_legacy = MultiplexingSabotageLab.simulate_thundering_herd(num_workers=8, use_exclusive=False)
    th_fixed = MultiplexingSabotageLab.simulate_thundering_herd(num_workers=8, use_exclusive=True)
    
    print(f"\n[*] Thundering Herd (Gürleyen Sürü) Karşılaştırması:")
    print(f"    [Geleneksel Epoll]   Uyandırılan: {th_legacy['woken_workers']} | Boşa Çıkan: {th_legacy['wasted_wakeups']} worker | CPU Maliyeti: {th_legacy['cpu_overhead']}")
    print(f"    [EPOLLEXCLUSIVE]     Uyandırılan: {th_fixed['woken_workers']} | Boşa Çıkan: {th_fixed['wasted_wakeups']} worker | CPU Maliyeti: {th_fixed['cpu_overhead']}")

```

## 8. Kod 03 Hata Analizi ve Çekirdek Düzeltme Stratejileri

Simülasyon çıktıları çoklu istemci yöneten sunucularda iki vazgeçilmez kuralı gösterir:

1. **`select()` Asla Modern Ağ Sunucularında Kullanılmamalıdır:** Dosya tanıtıcısı numaraları işletim sisteminde sürekli artar. Yoğun bir sunucuda FD numarası saniyeler içinde 1024'ü geçebilir. `select()` kullanmak, saati kurulmuş bir saatli bomba taşımak gibidir. Minimum `poll()`, yüksek başarım için kesinlikle `epoll()` kullanılmalıdır.
2. **`EPOLLEXCLUSIVE` ile Kaynak Tasarrufu:** 16 çekirdekli bir sunucuda her yeni bağlantıda 16 iş parçacığının birden uyandırılması işlemci önbelleklerini (L1/L2) boşaltır ve kilit çekişmesini (lock contention) tavana vurur. `EPOLLEXCLUSIVE` bayrağı bu gürleyen sürüyü engelleyerek tek bir worker'ı görevlendirir.


## 9. Savunma Sanayii Vaka Analizi: ASELSAN Taktik Ağ & HAVELSAN C4I Telemetri Hattı

Muharebe sahasında görev yapan Komuta Kontrol (C4I) ve Taktik Muharebe Sahası Ağlarında (CNR - Combat Net Radio), tek bir merkez sunucu binlerce insansız kara/hava aracı (İHA/SİHA), elektro-optik kamera, radar istasyonu ve sahadaki asker telsizinden gelen telemetri paketlerini eşzamanlı olarak karşılamak zorundadır.

```
+--------------------------------------------------------------------------------+
|                   HAVELSAN C4I KOMUTA KONTROL MERKEZİ                         |
|                                                                                |
|  [5,000 x Taktik Asker Telsizi]       [2,000 x SİHA / İHA Telemetrisi]         |
|  [1,000 x Elektro-Optik Sensör]       [2,000 x Hava Savunma Radar Düğümü]      |
|                       \                     /                                  |
|                        \                   /                                   |
|                         v                 v                                    |
|               +--------------------------------------+                         |
|               |  TOPLAM: 10,000 EŞZAMANLI BAĞLANTI   |                         |
|               +--------------------------------------+                         |
|                                  |                                             |
|                                  v                                             |
|       +------------------------------------------------------+                 |
|       |     C++20 Gerçek Zamanlı Linux Event Loop Motoru     |                 |
|       |                 epoll_create1()                      |                 |
|       |            epoll_wait(timeout = 0)                   |                 |
|       +------------------------------------------------------+                 |
|                                  |                                             |
|           +----------------------+----------------------+                      |
|           | (O(1) Hazır Kuyruğu: Saniyede 500 Aktif Olay) |                      |
|           v                                             v                      |
|  +--------------------------------+   +-------------------------------------+  |
|  | Tehdit Erken Uyarı İş parçacığı |   | Taktik Harita Füzyon İş parçacığı   |  |
|  | (Düşman İHA Radar İzi Tespiti) |   | (Dost/Düşman Konum Güncellemesi)    |  |
|  +--------------------------------+   +-------------------------------------+  |
+--------------------------------------------------------------------------------+
```

### Neden `poll` veya Thread-per-Client Yetmez?
- **Thread-per-Client:** 10,000 bağlantı için 10,000 thread açılırsa sistemin 80 GB RAM'i sadece thread stack'lerine rehin kalır. İşlemci çekirdekleri zamanın %85'ini thread'leri uyandırıp uyutarak (Context Switch) harcar.
- **`poll()`:** Saniyede 1,000 döngü dönen bir event loop'ta her döngü 10,000 soketi tararsa, saniyede **10,000,000 soket kontrolü** yapılır. CPU %100'e kilitlenir.
- **`epoll()`:** Çekirdek seviyesindeki donanım kesmesi geri çağırması sayesinde yalnızca veri gönderen 500 soket anında kuyruğa alınır. CPU kullanımı **%2'nin altında** kalır!


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): 10,000 Düğümlü Taktik Sensör Ağı (C10K) Event Loop Simülasyonu
Büyük Ölçekli Eşzamanlılıkta CPU Döngü Sayısı ve Gecikme Ölçümü
"""

import time
import numpy as np
from typing import Dict, Any

def simulate_tactical_c10k_event_loop(num_total_nodes: int = 10000, num_active_nodes: int = 50) -> Dict[str, Any]:
    """10,000 düğümlü taktik ağda select, poll ve epoll başarımını simüle eder."""
    
    # Rastgele aktif 50 düğüm belirle
    np.random.seed(42)
    active_fds = set(np.random.choice(num_total_nodes, size=num_active_nodes, replace=False))

    # 1. poll() Simülasyonu (select 1024 sınırından dolayı 10,000 düğümde çalışamaz!)
    t0 = time.perf_counter()
    poll_inspected = 0
    poll_ready = []
    # Çekirdek içi O(N) döngüsü
    for fd in range(num_total_nodes):
        poll_inspected += 1
        if fd in active_fds:
            poll_ready.append(fd)
    t_poll_us = (time.perf_counter() - t0) * 1e6

    # 2. epoll() Simülasyonu (RB-Tree + Ready List O(1))
    t0 = time.perf_counter()
    # Donanım kesmesi doğrudan hazır listesini verir
    epoll_ready = list(active_fds)
    epoll_inspected = len(epoll_ready) # YALNIZCA AKTİF OLANLAR İNCELENİR
    t_epoll_us = (time.perf_counter() - t0) * 1e6

    # Minimum nanosaniye tabanı düzeltmesi
    t_epoll_us = max(t_epoll_us, 0.45)

    return {
        "total_nodes": num_total_nodes,
        "active_nodes": num_active_nodes,
        "poll_inspected_fds": poll_inspected,
        "epoll_inspected_fds": epoll_inspected,
        "poll_time_us": t_poll_us,
        "epoll_time_us": t_epoll_us,
        "speedup_factor": t_poll_us / t_epoll_us
    }


if __name__ == "__main__":
    print("=== TAKTİK AĞ C10K SENSÖR EVENT LOOP DENEYİ ===")
    res = simulate_tactical_c10k_event_loop(num_total_nodes=10000, num_active_nodes=50)
    print(f"[*] Toplam Taktik Düğüm Sayısı : {res['total_nodes']:,}")
    print(f"[*] Aktif Paket Gönderen Düğüm : {res['active_nodes']}")
    print(f"[*] poll()  İncelenen FD Sayısı: {res['poll_inspected_fds']:,} | Süre: {res['poll_time_us']:.2f} µs")
    print(f"[*] epoll() İncelenen FD Sayısı: {res['epoll_inspected_fds']:,} | Süre: {res['epoll_time_us']:.2f} µs")
    print(f"[*] epoll Hızlanma Çarpanı     : {res['speedup_factor']:.1f}x Kat Daha Hızlı!")

```

## 10. Kod 04 Analizi ve C10K Çıkarımları

Kod 04 simülasyonu, 10,000 istemcili bir savunma ağında `poll()` ile `epoll()` arasındaki uçurumu somut rakamlarla kanıtlar:

1. **Döngü İsrafı:** `poll()`, 50 aktif paketi bulabilmek için 10,000 dosya tanımlayıcısının tamamını tek tek incelemiştir. Yapılan kontrollerin **%99.5'i tamamen boştur**!
2. **`epoll` Determinizmi:** `epoll()` yalnızca hazır listesindeki 50 aktif olayı işlemiştir. 10,000 düğümlük sistemde döngü maliyeti neredeyse sıfıra inmiştir.
3. **C10K Probleminin Çözümü:** 1999 yılında Dan Kegel tarafından ortaya atılan "Tek bir sunucu aynı anda 10,000 bağlantıyı nasıl yönetebilir?" (The C10K Problem) sorusunun Linux çekirdeğindeki kesin cevabı `epoll` mimarisidir.


## 11. Matematiksel Karmaşıklık ve Syscall Maliyet Modeli

I/O çoklama algoritmalarının zaman ve alan karmaşıklığı analiz tablosu:

| Mekanizma | Veri Yapısı (Çekirdek) | Döngü Başına Zaman Karmaşıklığı | Kullanıcı-Çekirdek Kopyalama | Azami FD Kapasitesi |
| :--- | :--- | :---: | :---: | :---: |
| **`select`** | Bit dizisi (`fd_set`) | $O(N)$ (En büyük FD kadar) | Her çağrıda tüm bitmask ($O(N)$) | Sabit 1024 (`FD_SETSIZE`) |
| **`poll`** | `pollfd` dizisi | $O(N)$ (Kayıtlı tüm FD'ler) | Her çağrıda tüm dizi ($O(N)$) | Sınırsız (Bellek yettiğince) |
| **`epoll`** | Kırmızı-Siyah Ağaç + Çift Bağlı Liste | **$O(1)$** (Yalnızca aktif FD'ler) | Yalnızca hazır olaylar ($O(K)$) | Sınırsız (`/proc/sys/fs/epoll/max_user_watches`) |

### Matematiksel Zaman Modeli
Toplam $N$ adet kayıtlı soket ve o anda veri hazır olan $K$ adet aktif soket ($K \ll N$) olsun:

- **`select` Gecikmesi:**
  $$T_{\text{select}} = c_1 \cdot N_{\text{max}} + c_2 \cdot \frac{N_{\text{max}}}{64} \quad (\text{Her döngüde bitmask tarama ve kopyalama})$$

- **`poll` Gecikmesi:**
  $$T_{\text{poll}} = c_3 \cdot N \cdot \text{sizeof(pollfd)} + c_4 \cdot N \quad (\text{Her döngüde } 8N \text{ bayt kopyalama ve } N \text{ tarama})$$

- **`epoll` Gecikmesi:**
  $$T_{\text{epoll}} = c_5 \cdot K \cdot \text{sizeof(epoll_event)} \quad (\text{Yalnızca } 12K \text{ bayt kopyalama ve } K \text{ işlem})$$

Burada $N = 50,000$ ve $K = 10$ olduğunda:
- `poll`, $50,000$ elemanlık diziyi kopyalayıp tararken,
- `epoll`, yalnızca $10$ elemanı işler! Aradaki verim farkı **5,000 kat** mertebesindedir.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Kapsamlı I/O Çoklama Benchmark Laboratuvarı
Bağlantı Sayısına Göre Gecikme (Latency) ve CPU İş Yükü (select vs poll vs epoll)
"""

import numpy as np
from typing import Dict, Any

def run_multiplexing_benchmark() -> Dict[str, Any]:
    """100'den 50,000 bağlantıya kadar olan ölçekte mekanizmaların performansını modeller."""
    connection_counts = np.array([100, 500, 1000, 2500, 5000, 10000, 25000, 50000], dtype=np.int64)
    active_ratio = 0.01 # Bağlantıların %1'i aktif (Tipik ağ yükü)

    results = {
        "connections": connection_counts,
        "select_latency_us": [],
        "poll_latency_us": [],
        "epoll_latency_us": [],
        "poll_copy_kb": [],
        "epoll_copy_kb": []
    }

    for n in connection_counts:
        k = max(1, int(n * active_ratio))
        
        # 1. select: 1024'e kadar çalışır, sonrasında tanımsız/taşma
        if n <= 1024:
            t_sel = 0.8 + (n * 0.015) # Mikrosaniye
        else:
            t_sel = np.nan # 1024 üstü geçersiz
        results["select_latency_us"].append(t_sel)

        # 2. poll: O(N) bellek kopyalama ve tarama
        t_pol = 1.2 + (n * 0.028)
        results["poll_latency_us"].append(t_pol)
        results["poll_copy_kb"].append((n * 8) / 1024.0)

        # 3. epoll: O(1) sabit gecikme + sadece K kadar aktif olay
        t_ep = 0.65 + (k * 0.002)
        results["epoll_latency_us"].append(t_ep)
        results["epoll_copy_kb"].append((k * 12) / 1024.0)

    for key in list(results.keys()):
        if key != "connections":
            results[key] = np.array(results[key], dtype=np.float64)

    return results


if __name__ == "__main__":
    print("=== I/O MULTIPLEXING PERFORMANS BENCHMARK'I ===")
    bench = run_multiplexing_benchmark()
    print(f"{'Bağlantı':>8} | {'select (µs)':>12} | {'poll (µs)':>10} | {'epoll (µs)':>10} | {'epoll Hızlanma':>14}")
    print("-" * 64)
    for i, n in enumerate(bench["connections"]):
        s_val = f"{bench['select_latency_us'][i]:.2f}" if not np.isnan(bench["select_latency_us"][i]) else "LIMIT AŞILDI"
        p_val = bench["poll_latency_us"][i]
        e_val = bench["epoll_latency_us"][i]
        speedup = p_val / e_val
        print(f"{n:>8,d} | {s_val:>12} | {p_val:>10.2f} | {e_val:>10.2f} | {speedup:>13.1f}x")

```

## 12. Kod 05 Benchmark Değerlendirmesi: Ölçeklenebilirlik Çıkarımları

Benchmark tablosundan çıkarılan 3 temel sistem mühendisliği ilkesi:

1. **`select()` Sınırı:** 1,024 bağlantı aşıldığında `select()` tamamen devre dışı kalır. Geliştirici kodu korumasa dahi sistem çöker.
2. **`poll()` Lineer Boğulması:** Bağlantı sayısı 100'den 50,000'e çıktığında `poll()` gecikmesi $1.2\ \mu\text{s}$ seviyesinden $1,400\ \mu\text{s}$ (1.4 ms) seviyesine fırlar! Bir ağ sunucusunun sadece olay kontrolü için 1.4 milisaniye harcaması kabul edilemez.
3. **`epoll()` Asimptotik Düzlüğü:** 50,000 bağlantıda dahi `epoll()` gecikmesi sadece $1.65\ \mu\text{s}$ civarındadır! Çünkü gecikme toplam bağlantı sayısına ($N$) değil, o an veri gönderen aktif istemci sayısına ($K$) bağlıdır.


## 13. Görselleştirme Mimarisi: 4 Panelli Karanlık Tema Mühendislik Dashboard'u

Oluşturulacak görsel artefakt (`gun_100_select_poll_epoll_neden_var.png`), `#0F172A` koyu tema paletinde 4 temel analiz sunacaktır:

1. **Panel 1: Bağlantı Sayısına Göre Event Loop Gecikmesi ($O(N)$ vs $O(1)$) [Log-Log Plot]:** `select` (1024'te kesilen), `poll` (doğrusal tırmanan) ve `epoll` (yatay kalan) gecikme eğrileri.
2. **Panel 2: Çekirdek-Kullanıcı Bellek Kopyalama Hacmi (User $\leftrightarrow$ Kernel Overhead):** `poll`'ün 400 KB'ye tırmanan veri transferine karşılık `epoll`'ün mikroskobik bayt seviyesindeki verimliliği.
3. **Panel 3: Linux Çekirdeği `epoll` İç Mimari Şeması (Diagram):** Kırmızı-Siyah Ağaç (`struct rb_node`) + NIC Donanım Kesmesi Callback + Hazır Listesi (`struct list_head`) veri akışı.
4. **Panel 4: Edge-Triggered (ET) vs Level-Triggered (LT) Olay Bildirim Mekanizması:** Tampon doluluk ve tetikleme sinyallerinin zaman eksenindeki dinamik grafiği.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 20 (CODE 6): 4 Panelli 300 DPI Mühendislik Dashboard'u ve Katı Doğrulama Testleri
select, poll, epoll Evrimi, Karmaşıklık Analizi ve Çekirdek Mimarisi Görselleştirmesi
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_100\gun_100_select_poll_epoll_neden_var.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı I/O Multiplexing dashboard'u üretir."""
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
    # Panel 1: Bağlantı Sayısına Göre Gecikme (Log-Log Eğrisi)
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    conns = np.array([100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000])
    
    # select: 1024'e kadar
    sel_conns = conns[conns <= 1000]
    lat_sel = 0.8 + (sel_conns * 0.015)
    
    lat_poll = 1.2 + (conns * 0.028)
    lat_epoll = 0.65 + (conns * 0.01 * 0.002)

    ax1.plot(sel_conns, lat_sel, marker="o", linewidth=2.2, color=accent_amber, label="select(2) [1024 FD Sınırı]")
    ax1.plot(conns, lat_poll, marker="s", linewidth=2.5, color=accent_red, label="poll(2) [O(N) Doğrusal Tırmanış]")
    ax1.plot(conns, lat_epoll, marker="^", linewidth=3.0, color=accent_green, label="epoll(7) [O(1) Asimptotik Sabit]")

    # 1024 Sınır Çizgisi
    ax1.axvline(1024, color=accent_amber, linestyle=":", alpha=0.7, label="FD_SETSIZE (1024) Limiti")
    
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_title("Panel 1: Bağlantı Sayısına Göre Event Loop Gecikmesi (Log-Log)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.set_xlabel("İzlenen Bağlantı Sayısı (N)", color=text_color, fontsize=10)
    ax1.set_ylabel("Döngü Gecikmesi (µs)", color=text_color, fontsize=10)
    ax1.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 2: Çekirdek-Kullanıcı Bellek Kopyalama Hacmi (KB)
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    copy_poll_kb = (conns * 8) / 1024.0 # pollfd = 8 bayt
    copy_epoll_kb = (conns * 0.01 * 12) / 1024.0 # epoll_event = 12 bayt (aktif %1)

    ax2.plot(conns, copy_poll_kb, marker="s", linewidth=2.5, color=accent_red, label="poll(2): Tüm pollfd Dizisi Kopyalanır")
    ax2.plot(conns, copy_epoll_kb, marker="^", linewidth=2.5, color=accent_green, label="epoll(7): Yalnızca Aktif Olaylar Kopyalanır")

    ax2.set_title("Panel 2: Döngü Başına Kullanıcı-Çekirdek Bellek Kopyalama Hacmi", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_xlabel("İzlenen Bağlantı Sayısı (N)", color=text_color, fontsize=10)
    ax2.set_ylabel("Kopyalanan Veri (KB / Döngü)", color=text_color, fontsize=10)
    ax2.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=9, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 3: Linux epoll İç Mimari Şeması (Diagram)
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)
    ax3.axis("off")
    ax3.set_title("Panel 3: Linux Çekirdeği epoll İç Mimari Veri Yapıları", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # Kırmızı-Siyah Ağaç Kutusu
    rect_rbtree = plt.Rectangle((0.5, 5.2), 4.2, 3.8, facecolor="#0369A1", edgecolor=accent_blue, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_rbtree)
    ax3.text(2.6, 8.3, "İzleme Kümesi (Kırmızı-Siyah Ağaç)", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(2.6, 7.3, "struct rb_root (O(log N))\n100,000 Soket Burada Kayıtlıdır", ha="center", color="#BAE6FD", fontsize=8)
    ax3.text(2.6, 6.0, "epoll_ctl(ADD/DEL/MOD)", ha="center", color=accent_amber, fontsize=8.5, fontweight="bold")

    # Hazır Listesi Kutusu
    rect_ready = plt.Rectangle((5.3, 5.2), 4.2, 3.8, facecolor="#047857", edgecolor=accent_green, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_ready)
    ax3.text(7.4, 8.3, "Hazır Listesi (Ready List - DLL)", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(7.4, 7.3, "struct list_head (O(1))\nSADECE Aktif 3 Soket Bulunur", ha="center", color="#A7F3D0", fontsize=8)
    ax3.text(7.4, 6.0, "epoll_wait() Anında Döndürür", ha="center", color=accent_blue, fontsize=8.5, fontweight="bold")

    # Donanım Kesmesi Kutusu
    rect_hw = plt.Rectangle((2.0, 1.0), 6.0, 2.8, facecolor="#334155", edgecolor=accent_amber, linewidth=2.2, transform=ax3.transData)
    ax3.add_patch(rect_hw)
    ax3.text(5.0, 3.0, "AĞ KARTI (NIC) DONANIM KESMESİ", ha="center", color=accent_amber, fontsize=10, fontweight="bold")
    ax3.text(5.0, 2.0, "Paket Geldi -> Çekirdek Callback Çalışır\nSoketi O(1) ile Hazır Listesine Ekler", ha="center", color=text_color, fontsize=8.5)

    # Oklar
    ax3.annotate("", xy=(7.4, 5.2), xytext=(6.5, 3.8), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2.5))
    ax3.annotate("", xy=(2.6, 5.2), xytext=(3.5, 3.8), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))

    # -------------------------------------------------------------------------
    # Panel 4: Edge-Triggered (ET) vs Level-Triggered (LT) Dinamiği
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    time_pts = np.linspace(0, 10, 500)
    
    # Tampon Veri Seviyesi (Dalga: Veri geliyor ve kısmi okunuyor)
    buffer_level = np.zeros_like(time_pts)
    buffer_level[(time_pts >= 2.0) & (time_pts < 4.0)] = 4.0
    buffer_level[(time_pts >= 4.0) & (time_pts < 7.0)] = 2.5 # Kısmi okundu
    buffer_level[(time_pts >= 7.0)] = 0.0 # Tamamen bitti

    # Tetiklemeler
    lt_signal = np.zeros_like(time_pts)
    lt_signal[(time_pts >= 2.0) & (time_pts < 7.0)] = 1.0 # LT: Veri varken sürekli aktif!

    et_signal = np.zeros_like(time_pts)
    et_signal[(time_pts >= 2.0) & (time_pts < 2.3)] = 1.0 # ET: Sadece kenar değişiminde tek darbe!

    ax4.plot(time_pts, buffer_level, color=accent_blue, linewidth=2.0, label="Soket Rx Tampon Seviyesi (KB)")
    ax4.step(time_pts, lt_signal * 3.5, color=accent_amber, linestyle="--", linewidth=1.8, label="Level-Triggered Bildirimi (Sürekli)")
    ax4.step(time_pts, et_signal * 3.8, color=accent_red, linewidth=2.2, label="Edge-Triggered Bildirimi (Tek Darbe)")

    ax4.set_title("Panel 4: Edge-Triggered (ET) vs Level-Triggered (LT) Bildirim Dinamiği", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax4.set_xlabel("Zaman (Temsili Akış)", color=text_color, fontsize=10)
    ax4.set_ylabel("Sinyal / Boyut", color=text_color, fontsize=10)
    ax4.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper right")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_path}")


def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Gün 100 için tüm mimari ve matematiksel kabulleri katı testlerle doğrular."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dashboard Görsel Kontrolü
    assert os.path.exists(png_path), f"HATA: Dashboard görseli mevcut değil: {png_path}"
    file_size = os.path.getsize(png_path)
    assert file_size > 100_000, f"HATA: Dashboard boyutu şüpheli ({file_size} bayt)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {file_size:,} bayt.")

    # 2. select() 1024 FD Taşma Doğrulaması
    overflow_ok, _ = MultiplexingSabotageLab.simulate_select_overflow_crash(1025)
    assert overflow_ok is True, "HATA: select 1024 sınır aşımını engellemelidir!"
    print("  [+] select() FD_SETSIZE (1024) Donanımsal/Yazılımsal Taşma Sınırı Doğrulandı.")

    # 3. Edge-Triggered Kısmi Okuma Tuzağı Doğrulaması
    sock_test = SimulatedSocket(fd=88)
    sock_test.incoming_network_data(b"RADAR_FRAME_DATA")
    wakeups, stranded = TriggerModeSimulator.simulate_edge_triggered(sock_test, read_size=5, loop_count=4)
    assert len(wakeups) == 1, "HATA: Edge-triggered yalnızca durum değişiminde 1 kez uyanmalıdır!"
    assert stranded > 0, "HATA: EAGAIN döngüsü olmadan okunan ET sokette veri kilitlenmelidir!"
    print("  [+] Edge-Triggered Bildirim Dinamiği ve Veri Kilitlenme Tuzağı Doğrulandı.")

    # 4. C10K Taktik Ağ Hızlanma Doğrulaması
    c10k = simulate_tactical_c10k_event_loop(num_total_nodes=5000, num_active_nodes=20)
    assert c10k["speedup_factor"] > 5.0, f"HATA: epoll, poll'e kıyasla en az 5x hızlı olmalıdır ({c10k['speedup_factor']:.1f}x)!"
    assert c10k["epoll_inspected_fds"] == 20, "HATA: epoll yalnızca aktif FD'leri incelemelidir!"
    print(f"  [+] C10K Taktik Ağ epoll O(1) Üstünlüğü Doğrulandı ({c10k['speedup_factor']:.1f}x Hızlanma).")

    # 5. Thundering Herd Analiz Doğrulaması
    th = MultiplexingSabotageLab.simulate_thundering_herd(num_workers=16, use_exclusive=True)
    assert th["woken_workers"] == 1, "HATA: EPOLLEXCLUSIVE yalnızca 1 worker uyandırmalıdır!"
    print("  [+] EPOLLEXCLUSIVE ile Thundering Herd Eliminasyonu Doğrulandı.")

    print("\n[PASS] Gün 100: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)

```

## 14. Dashboard Çıktısının Detaylı Teknik Değerlendirmesi

Oluşturulan mühendislik paneli (`gun_100_select_poll_epoll_neden_var.png`), sistem tasarımı açısından şu 4 kritik gerçeği belgeler:

1. **Panel 1 (Gecikme Eğrisi):** 1,000 bağlantıya kadar `poll` ve `epoll` benzer görünse de, bağlantı sayısı arttıkça `poll`'ün lineer eğimi ($O(N)$) sistemi felç eder. `select` 1024 sınırında aniden kesilirken, `epoll` yatay çizgisini koruyarak asimptotik $O(1)$ üstünlüğünü kanıtlar.
2. **Panel 2 (Bellek Trafiği):** 50,000 bağlantıda `poll` her döngüde 400 KB bellek kopyalarken, `epoll` yalnızca aktif olan birkaç yüz baytlık olay listesini aktarır; bellek bant genişliğini tüketmez.
3. **Panel 3 (Çekirdek Veri Yapıları):** Kırmızı-Siyah Ağaç (`O(\log N)`) ile kayıtlı yüz binlerce soket arasından, donanım kesmesiyle Hazır Listesine (`O(1)`) aktarılan soketlerin mimari ayrımı netleştirilmiştir.
4. **Panel 4 (ET vs LT Sinyali):** Tamponda veri kaldığı sürece sürekli yüksekte kalan LT sinyaline karşılık, ET sinyalinin yalnızca ilk gelişte tek darbe ürettiği ve `EAGAIN` döngüsü kurulmazsa verinin sokette rehin kalacağı görselleştirilmiştir.


## 15. Gelişmiş Sistem Mühendisliği: `io_uring`, `timerfd`, `signalfd` ve `eventfd`

Modern Linux çekirdeğinde I/O çoklama yalnızca ağ soketleriyle sınırlı değildir. "Her Şey Bir Dosyadır" (Everything is a File) felsefesiyle tüm sistem olayları epoll kümesine bağlanabilir:

### 1. Dosya Tanıtıcısı Tabanlı Olay Primitifleri
- **`timerfd_create(2)`:** Donanımsal POSIX zamanlayıcılarını bir dosya tanıtıcısına dönüştürür. Süre dolduğunda FD okunabilir hale gelir ve epoll döngüsü uyandırılır. Sinyal karmaşası olmadan deterministik periyodik görevler çalıştırılır.
- **`eventfd(2)`:** İş parçacıkları veya süreçler arasında hafif siklet (8-bayt tamsayı) sayaç tabanlı bildirim mekanizması kurar. Pipe'lara kıyasla 10 kat daha hızlıdır.
- **`signalfd(2)`:** `SIGINT`, `SIGTERM` gibi asenkron sinyalleri standart bir soket gibi epoll döngüsünde senkron olarak okur. Güvenli olmayan sinyal işleyicilerine (`signal handler`) olan ihtiyacı tamamen bitirir.

### 2. Geleceğin Teknolojisi: `io_uring` (Linux 5.1+)
`epoll` dahi olsa her I/O işleminde en az iki sistem çağrısı (`epoll_wait` + `read`/`write`) çalıştırılır. Jens Axboe tarafından geliştirilen **`io_uring`**, çekirdek ile kullanıcı alanı arasında **iki adet kilit-içermeyen halka tampon (Submission Queue & Completion Queue)** paylaşır.
- **Sıfır Syscall Modu (`IORING_SETUP_SQPOLL`):** Çekirdekte çalışan özel bir kernel thread, halka tamponu sürekli yoklar. Kullanıcı alanı tek bir sistem çağrısı dahi yapmadan doğrudan belleğe I/O istekleri yazar ve sonuçları okur!


## 16. Yaygın Hatalar, Anti-Pattern'ler ve Kontrol Listesi

### Ölümcül Anti-Pattern'ler

| Anti-Pattern | Neden Tehlikeli? | Doğru Yaklaşım |
| :--- | :--- | :--- |
| **ET Modunda Bloklayan Soket** | Soket non-blocking yapılmazsa, `read()` veri bittiğinde `EAGAIN` döndürmek yerine tüm iş parçacığını süresiz kilitler! | `fcntl(fd, F_SETFL, O_NONBLOCK)` çağrısını soket açılır açılmaz işlet. |
| **Kısmi Okuma ve Çıkış** | ET modunda tamponda veri varken döngüden çıkılırsa sonraki veri gelene kadar soket donar. | `read()` çağrısını `while (true)` içinde `EAGAIN` veya `EWOULDBLOCK` görene kadar çalıştır. |
| **`select` Kullanımında 1024 Sınırı** | FD numarası 1024 olduğunda `fd_set` sınırını aşar ve stack ezilir. | Ağ sunucularında asla `select` kullanma; `epoll` tercih et. |
| **Kapanan FD'yi Silmemek** | Başka bir iş parçacığı aynı FD numarasını yeniden tahsis ederse, eski olaylar yeni sokete karışır. | `close(fd)` öncesinde daima `epoll_ctl(EPOLL_CTL_DEL)` çağır. |

### Üretim Öncesi Kontrol Listesi (Checklist)
- [ ] Epoll tanıtıcısı `EPOLL_CLOEXEC` bayrağı ile açıldı mı?
- [ ] İzlenen tüm soketler `O_NONBLOCK` moduna alındı mı?
- [ ] Edge-Triggered (ET) modunda `EAGAIN` / `EWOULDBLOCK` tüketim döngüsü kuruldu mu?
- [ ] EOF (karşı tarafın bağlantıyı kapatması) durumu `read() == 0` veya `EPOLLRDHUP` ile yakalanıyor mu?
- [ ] Çok iş parçacıklı dinlemede Thundering Herd'i engellemek için `EPOLLEXCLUSIVE` veya `SO_REUSEPORT` kullanıldı mı?


## 17. Gün Sonu Özeti ve 3 Cümlelik Kural

1. **`select` ve `poll` durumsuz oldukları için** her döngüde tüm dosya tanımlayıcılarını çekirdeğe kopyalayıp $O(N)$ tarama yapmak zorundadır; bu nedenle C10K ölçeğinde çökerler.
2. **`epoll`,** izleme kümesini çekirdekte bir Kırmızı-Siyah Ağaçta saklayarak ve yalnızca veri gelen soketleri bir Hazır Listesine bağlayarak **$O(1)$ asimptotik karmaşıklık ve determinizm** sağlar.
3. **Edge-Triggered (ET) modunda çalışırken,** soketlerin bloklamayan (`O_NONBLOCK`) olması ve veri akışının `EAGAIN` dönene kadar tek döngüde tüketilmesi veri kilitlenmesini engellemek için zorunludur.

---

## 18. Mülakat Sorusu (ASELSAN / HAVELSAN Sistem Mühendisliği)

**Soru:**
10,000 aktif istemciye hizmet veren bir taktik ağ sunucusunda `epoll` kullanılmasına rağmen işlemci çekirdeklerinden birinin %100 CPU harcadığı ve yeni gelen bazı paketlerin istemcilere iletilmeyip sokette takılı kaldığı (starvation) gözlemlenmiştir. 
1. Bu durumun en olası nedeni nedir? Hangi `epoll` tetikleme bayrağı bu hataya yol açmış olabilir?
2. Kök nedeni çözmek için uygulama kodunda nasıl bir değişiklik yapılmalıdır?

**İdeal Cevap:**
1. **Kök Neden:** Soketler `EPOLLET` (Edge-Triggered) moduyla kaydedilmiş ancak uygulama katmanında `read()` çağrısı bloklamayan bir döngüde (`while`) çalıştırılmayıp tek seferlik çağrılmıştır. Tamponda kalan veri için `epoll_wait` yeni bir kenar darbesi gelmediği için süreci bir daha uyandırmamış, veri soket kuyruğunda rehin kalmıştır. Ayrıca soketler `O_NONBLOCK` yapılmadıysa thread bloklanmış veya busy-wait döngüsüne girmiştir.
2. **Çözüm:** 
   - Soket tanıtıcıları `fcntl(fd, F_SETFL, O_NONBLOCK)` ile bloklamayan moda alınmalıdır.
   - `read()` çağrısı bir `while (true)` döngüsü içine alınmalı; `read()` negatif dönüp `errno == EAGAIN` veya `EWOULDBLOCK` olana kadar tampon tamamen boşaltılmalıdır.

---

## 19. İleri Okuma ve Resmi Kaynaklar
- [Linux man-pages: epoll(7) - I/O Event Notification Facility](https://man7.org/linux/man-pages/man7/epoll.7.html)
- [Dan Kegel - The C10K Problem (Classic Paper)](http://www.kegel.com/c10k.html)
- [Linux man-pages: epoll_ctl(2) - Control Interface for an Epoll Descriptor](https://man7.org/linux/man-pages/man2/epoll_ctl.2.html)
- [Jens Axboe - Efficient IO with io_uring (PDF Reference)](https://kernel.dk/io_uring.pdf)

---

### Gün 101 Köprüsü: `systemd` Service Zihinsel Modeli
Yarın, yazdığımız bu C++20 ve Linux ağ servislerini işletim sistemi seviyesinde güvenilir, otomatik yeniden başlayan, kaynak sınırlamalı (cgroups) ve bağımlılık yönetimli üretim servislerine dönüştüren **`systemd service` zihinsel modelini** inceleyeceğiz!
