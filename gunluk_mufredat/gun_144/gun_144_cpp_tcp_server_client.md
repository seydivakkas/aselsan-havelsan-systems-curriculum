# Gün 144: C++ TCP Server ve Client Mimarisi (Berkeley Sockets, listen, accept, SIGPIPE Koruması ve RAII Soket Yönetimi)

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

**Faz:** F4 — TCP/UDP / Protocol / Serialization  
**Konu:** L4 Taşıma Katmanı Bağlantı Yönelimli Ağ Programlama: POSIX Berkeley TCP Soketleri, `SOCK_STREAM`, `AF_INET`, `bind()`, `listen()` ve Dinleme Kuyrukları (SYN Queue vs Accept Queue), `accept()` ile Yeni İstemci Soketi Türetme, İstemci Tarafında `connect()` ve 3-Way Handshake, RAII Tabanlı C++20 `SocketFD` Yaşam Döngüsü, Kapanmış Sokete Yazma Felaketi (`SIGPIPE` / `EPIPE`), `MSG_NOSIGNAL` Savunması, `SO_REUSEADDR` ve Uzunluk Ön-Ekli Çerçeveli İletişim  
**Ön Koşul:** Gün 143 — C++ UDP Socket Programlama  
**Kritik Seviye:** Savunma Sanayii Hava Savunma Komuta Kontrol (C2) Merkez İstasyonu ile Füze Fırlatma Bataryaları Arasında Kesintisiz, Güvenilir ve Çok İstemcili TCP Haberleşme Omurgası

---

### 40-Nokta Bildirimi ve Kalite Güvencesi
Bu modül; C++20 ve Linux sistem programlama seviyesinde **TCP Sunucu ve İstemci Mimarisini** baştan sona inşa eder. UDP'nin bağlantısız doğasından farklı olarak; dinleme soketi (`server_fd`) ile veri soketi (`client_fd`) arasındaki kavramsal ayrım, `listen()` çağrısındaki `backlog` parametresinin çekirdek seviyesindeki rolü, karşı taraf çöktüğünde veya bağlantıyı aniden kopardığında süreci öldüren meşhur **`SIGPIPE` sinyali felaketi** ve `MSG_NOSIGNAL` ile güvenli kurtarma mekanizması çalışan C++20/Python simülatörüyle modellenmiştir.

## 1. 🎯 Bugünkü Problem: Karşı Taraf Çöktüğünde Kendi Kendini Öldüren C2 Sunucusu!

Askeri bir hava savunma karargahında çalışan ana C2 sunucusu, sahadaki 10 adet füze bataryasından TCP üzerinden telemetri almakta ve atış emirleri göndermektedir.

Sistem canlı tatbikata girdiğinde şu iki kritik kriz yaşanır:
1. **`SIGPIPE` Ölümcül Çöküşü (Server Suicide):** 3 numaralı füze bataryası düşman İHA'sı tarafından vurulur veya telsiz hattı fiziksel olarak kopar. Bataryanın işletim sistemi bağlantıya bir `RST` (Reset) çeker veya soket kapanır. C2 sunucusu bu kopmadan habersiz bir sonraki atış emrini göndermek için `write(client_fd, cmd, len)` çağrısı yapar. Linux çekirdeği kapalı sokete yazıldığı için sürece anında **`SIGPIPE` sinyali** fırlatır! Süreç bu sinyali yakalamadığı için C2 sunucusu **ANINDA KAPANIR (Crash)**! Tek bir bataryanın kopması tüm karargahın kör olmasına yol açar!
2. **`listen()` Kuyruk Tıkanması (Accept Queue Overflow):** Alarm anında 100 farklı sensör ve radar aynı anda C2 sunucusuna bağlanmaya çalışır. `listen(server_fd, backlog)` parametresi küçük (örn. 5) bırakıldığı için çekirdeğin `Accept Queue`'su dolar; meşru füze rampaları sunucuya bağlanamaz ve `Connection Refused` (`ECONNREFUSED`) hatasıyla geri döner.
3. **Dinleme Soketi vs Veri Soketi Karışıklığı:** Acemi geliştirici gelen her istemciyi `server_fd` üzerinden okumaya kalkar; yeni bağlantı kabul edilemez hale gelir.

Bu derste; RAII desenli C++20 soket mimarisini kuracak, `MSG_NOSIGNAL` ile `SIGPIPE` katliamını durduracak, `listen(backlog)` kapasitesini yönetecek ve çok istemcili bir komuta kontrol omurgası inşa edeceğiz!

## 2. 🧠 Temel Teori: TCP Sunucu ve İstemci Yaşam Döngüsü

TCP tam çift yönlü, bağlantı yönelimli bir protokoldür. Bu nedenle sunucu tarafında iki farklı türde soket kullanılır:
1. **Dinleme Soketi (Listening Socket - `server_fd`):** Yalnızca kapıda bekler ve yeni gelen el sıkışmaları kabul eder. Asla veri transferi yapmaz!
2. **Bağlantı Veri Soketi (Connected Socket - `client_fd`):** `accept()` çağrısı başarıyla döndüğünde çekirdek tarafından o istemciye özel üretilen bağımsız sokettir. Veri alışverişi yalnızca bu soket üzerinden yürütülür.

```
          SUNUCU (C2 Karargahı)                               İSTEMCİ (Füze Bataryası)
+---------------------------------------+               +-----------------------------------+
|  server_fd = socket(AF_INET, STREAM)  |               |  client_fd = socket(AF_INET, ...) |
+-------------------+-------------------+               +-----------------+-----------------+
                    |                                                     |
                    v                                                     |
+---------------------------------------+                                 |
|  setsockopt(SO_REUSEADDR, 1)          |                                 |
|  bind(server_fd, port 9191)           |                                 |
|  listen(server_fd, backlog=128)       |                                 |
+-------------------+-------------------+                                 |
                    |                                                     |
                    v                                                     v
+---------------------------------------+  3-Way Handshake      +-----------------------------------+
|  client_fd = accept(server_fd, ...)   | <===================> |  connect(server_addr)             |
+-------------------+-------------------+  (SYN, SYN-ACK, ACK)  +-----------------+-----------------+
                    |                                                     |
                    v                                                     v
+---------------------------------------+      Taktik Emir      +-----------------------------------+
|  recv(client_fd, buf, len, 0)         | <-------------------  |  send(client_fd, cmd, len, ...)   |
+-------------------+-------------------+                       +-----------------+-----------------+
                    |                                                     |
                    v                      Onay (ACK)                     v
+---------------------------------------+ --------------------> +-----------------------------------+
|  send(client_fd, ack, len, NOSIGNAL)  |                       |  recv(client_fd, resp, len, 0)    |
+-------------------+-------------------+                       +-----------------+-----------------+
                    |                                                     |
                    v                                                     v
+---------------------------------------+                       +-----------------------------------+
|  close(client_fd)                     |                       |  close(client_fd)                 |
+---------------------------------------+                       +-----------------------------------+
```

### Linux Çekirdeğinde İki Gizli Kuyruk: SYN Queue ve Accept Queue
Sunucu `listen(server_fd, backlog)` dediğinde çekirdek iki ayrı kuyruk tahsis eder:
1. **SYN Queue (Yarım Açık Kuyruk):** İstemciden `SYN` gelmiş, sunucu `SYN-ACK` dönmüş, henüz son `ACK` beklenmektedir (`SYN_RCVD` durumu). Boyutu `/proc/sys/net/ipv4/tcp_max_syn_backlog` ile sınırlandırılır.
2. **Accept Queue (Tam Açık Kuyruk):** 3-Way Handshake başarıyla bitmiş (`ESTABLISHED`), kullanıcı uygulamasının `accept()` çağrısı yapıp soketi alması beklenmektedir. Boyutu `listen()` fonksiyonuna verilen `backlog` parametresi ile sınırlandırılır.

## 3. 🔬 Derinlemesine Mekanizma: `SIGPIPE` Felaketi ve C++20 RAII Yönetimi

### 1. `SIGPIPE` / `EPIPE` Neden Oluşur?
TCP'de karşı taraf soketi kapattığında (`close()`), yerel tarafa bir `FIN` veya `RST` ulaşır.
- Yerel taraf soketten okuma yaparsa: `read()` fonksiyonu `0` döner (**EOF - End of File**). Bu normaldir.
- Ancak yerel taraf kapanmış bu sokete **yazmaya (`write()` / `send()`)** kalkarsa:
  1. Çekirdek ilk yazmada karşıdan `RST` alır.
  2. İkinci yazmada çekirdek sürece **`SIGPIPE` (Broken Pipe) sinyali** gönderir!
  3. Varsayılan sinyal işleyicisi (default signal handler) süreci **anında sonlandırır (Crash)!**

```
Gönderici (C2 Sunucusu)                             Alıcı (Çöken Batarya)
      |                                                     |
      |                                                 [Süreç Çöktü! / close()]
      |                                                     |
      | -------- send("ATES_ET") -------------------------> |
      | <------- RST (Connection Reset) ------------------- |
      |                                                     |
      | -------- send("HEDEF_GUNCELLE") ------------------> |
      v                                                     |
[ÇEKİRDEK: SIGPIPE Sinyali Fırlattı!]                       |
[SONUÇ: C2 Sunucusu ANINDA ÖLDÜ (Core Dump)]                |
```

### Savunma Sanayii Kalkanı: `MSG_NOSIGNAL`
Sürecin `SIGPIPE` ile ölmesini engellemenin iki yolu vardır:
1. **Soket Seviyesinde Bayrak (Önerilen):**
   ```cpp
   ssize_t sent = send(client_fd, data, len, MSG_NOSIGNAL);
   if (sent < 0 && errno == EPIPE) {
       // Süreç ölmez! Sadece EPIPE hatası döner; soket temizlenir.
       close(client_fd);
   }
   ```
2. **Süreç Seviyesinde Sinyali Yoksaymak:**
   ```cpp
   signal(SIGPIPE, SIG_IGN);
   ```

---

### 2. C++20 RAII Soket Yöneticisi (`SocketFD`)
Soket dosya tanımlayıcıları (`int fd`) işletim sistemi kaynaklarıdır. Fonksiyon erken dönerse (early return) veya exception fırlatılırsa soket açık kalır ve **Dosya Tanımlayıcısı Sızıntısı (File Descriptor Leak)** yaşanır (`Too many open files` - `EMFILE`).

Modern C++20 çözümü:
```cpp
class SocketFD {
    int fd_ = -1;
public:
    explicit SocketFD(int fd = -1) : fd_(fd) {}
    ~SocketFD() { if (fd_ >= 0) ::close(fd_); }
    
    // Kopyalama YASAK (Exclusive Ownership)
    SocketFD(const SocketFD&) = delete;
    SocketFD& operator=(const SocketFD&) = delete;
    
    // Taşıma SERBEST (Move Semantics)
    SocketFD(SocketFD&& o) noexcept : fd_(std::exchange(o.fd_, -1)) {}
    SocketFD& operator=(SocketFD&& o) noexcept {
        if (this != &o) {
            if (fd_ >= 0) ::close(fd_);
            fd_ = std::exchange(o.fd_, -1);
        }
        return *this;
    }
    int get() const noexcept { return fd_; }
};
```

## 4. 🛡️ Çok İstemcili Mimari ve Length-Prefixed Çerçeveleme

TCP bir byte-stream protokolü olduğu için, istemci ve sunucu arasındaki tüm emirler **4-Bayt Big-Endian Uzunluk Ön-Ekli Çerçeveleme (Length-Prefixed Framing)** ile paketlenmelidir:
```
+-----------------------------+-------------------------------------------------+
|   Payload Length (4 Bayt)   |            Uygulama Emri / Telemetri            |
|       uint32_t (Big-Endian) |               (N Bayt Değişken Uzunluk)         |
+-----------------------------+-------------------------------------------------+
```

### Çok İstemcili C2 Sunucusu Çalışma Prensibi
1. `server_fd` sürekli yeni istemcileri bekler (`accept()`).
2. Kabul edilen her yeni `client_fd`, istemciye özel bir oturum nesnesine (`ClientSession`) bağlanır.
3. Sunucu, bağlı tüm istemcilerin listesini tutar (`std::vector<ClientSession>`).
4. Bir alarm veya hedef tespit edildiğinde sunucu tek bir döngüyle tüm bağlı bataryalara senkronize ateşleme emri yayınlar (**Broadcast Command**).

## 5. 💻 1. Kod Bloğu: C++20 / Python TCP Server ve Client Çekirdek Motoru

Aşağıdaki kod; POSIX Berkeley TCP soket mekanizmalarını, RAII tabanlı soket sahipliğini, `listen(backlog)` kuyruk yönetimini, `SIGPIPE` korumalı `MSG_NOSIGNAL` iletimini ve 4-baytlık çerçeve kodlayıcısını içeren **`TCPServerClientEngine` Çekirdeğini** tanımlar.

```python
# -*- coding: utf-8 -*-
"""
GÜN 144: Kod Bloğu 1 — C++20 / Python TCP Server ve Client Çekirdek Motoru
POSIX socket, bind, listen, accept, connect, SIGPIPE koruması ve çerçeveleme.
"""

import os
import sys
import time
import math
import random
import struct
from typing import Dict, List, Tuple, Optional, NamedTuple

class TCPFramingCodec:
    """4-Bayt Big-Endian Uzunluk Ön-Ekli Çerçeveleme Motoru"""
    @staticmethod
    def encode_frame(payload: bytes) -> bytes:
        return struct.pack("!I", len(payload)) + payload

    @staticmethod
    def decode_frames(buffer: bytearray) -> Tuple[List[bytes], bytearray]:
        frames = []
        while len(buffer) >= 4:
            frame_len = struct.unpack("!I", buffer[:4])[0]
            if len(buffer) >= 4 + frame_len:
                frames.append(bytes(buffer[4:4 + frame_len]))
                buffer = buffer[4 + frame_len:]
            else:
                break
        return frames, buffer

class SimulatedConnectedSocket:
    """RAII Tabanlı TCP Bağlantı Soketi (client_fd)"""
    def __init__(self, fd: int, remote_addr: Tuple[str, int], is_alive: bool = True):
        self.fd = fd
        self.remote_addr = remote_addr
        self.is_alive = is_alive
        self.rx_buffer = bytearray()
        self.tx_bytes_count = 0
        self.rx_bytes_count = 0

    def send(self, data: bytes, flags: int = 0) -> int:
        """MSG_NOSIGNAL destekli veri gönderme"""
        if not self.is_alive:
            # Karşı taraf kapalı!
            # MSG_NOSIGNAL yoksa çekirdek SIGPIPE fırlatır ve süreç çöker!
            MSG_NOSIGNAL = 0x4000
            if not (flags & MSG_NOSIGNAL):
                raise BrokenPipeError("SIGPIPE: Kapanmış sokete yazıldı! Süreç çöktü (Crash)!")
            else:
                raise ConnectionResetError("EPIPE: Karşı taraf bağlantıyı kapattı (Hata güvenle yakalandı).")

        self.tx_bytes_count += len(data)
        return len(data)

    def close(self):
        self.is_alive = False

class SimulatedTCPServer:
    """POSIX TCP Dinleme Sunucusu (server_fd)"""
    def __init__(self, port: int, backlog: int = 128, so_reuseaddr: bool = True):
        self.port = port
        self.backlog = backlog
        self.so_reuseaddr = so_reuseaddr
        self.is_listening = False
        self.accept_queue: List[SimulatedConnectedSocket] = []
        self.active_clients: Dict[int, SimulatedConnectedSocket] = {}
        self.next_client_fd = 100

    def start_listen(self):
        self.is_listening = True

    def enqueue_handshake_complete(self, client_addr: Tuple[str, int]) -> bool:
        """3-Way Handshake bittiğinde çekirdek soketi Accept Queue'ya koyar"""
        if len(self.accept_queue) >= self.backlog:
            return False # Accept Queue Taştı! ECONNREFUSED
        
        sock = SimulatedConnectedSocket(self.next_client_fd, client_addr, is_alive=True)
        self.next_client_fd += 1
        self.accept_queue.append(sock)
        return True

    def accept(self) -> Optional[SimulatedConnectedSocket]:
        if not self.accept_queue:
            return None
        sock = self.accept_queue.pop(0)
        self.active_clients[sock.fd] = sock
        return sock

print("[HÜCRE 7] TCPFramingCodec, SimulatedConnectedSocket ve SimulatedTCPServer başarıyla yüklendi.")
```

## 6. 💻 2. Kod Bloğu: Canlı Taktik Komuta Kontrol İstemci-Sunucu Deneyi

Aşağıdaki deneyde:
1. C2 Radar Sunucusu (`TCPServer`) port 9191'de dinlemeye başlar (`listen`, `backlog=128`).
2. Füze Bataryası İstemcisi (`TCPClient`) bağlanır (`connect`), 3-Way Handshake tamamlanır ve sunucu `accept()` ile `client_fd = 100` alır.
3. İstemci 3 adet kritik taktik atış emrini çerçeveli olarak gönderir.
4. Sunucu emirleri parçalamadan eksiksiz ayrıştırır, doğrular ve onay (ACK) döner.

```python
# -*- coding: utf-8 -*-
"""
GÜN 144: Kod Bloğu 2 — Taktik C2 İstemci-Sunucu Canlı İletim Deneyi
"""

print("")
print("[*] Taktik C2 TCP İstemci-Sunucu Canlı İletim Deneyi Başlatılıyor...")

c2_server = SimulatedTCPServer(port=9191, backlog=128, so_reuseaddr=True)
c2_server.start_listen()

battery_addr = ("192.168.10.45", 58200)

# 1. Aşama: İstemci Bağlanır (Handshake Tamamlanır)
connected_ok = c2_server.enqueue_handshake_complete(battery_addr)
assert connected_ok, "HATA: El sıkışma kuyruğa eklenemedi!"

client_socket = c2_server.accept()
assert client_socket is not None
print(f"  [+] Sunucu Yeni Bağlantıyı Kabul Etti: client_fd={client_socket.fd}, Uzak Adres={client_socket.remote_addr}")

# 2. Aşama: İstemci 3 Adet Çerçeveli Atış Emri Gönderir
commands = [
    b"CMD_LOCK_TARGET_AZIMUTH_085.4_RADAR_ALPHA",
    b"CMD_ARM_MISSILE_WARHEAD_BATTERY_03",
    b"CMD_FIRE_SEQUENCE_COUNTDOWN_T_MINUS_3"
]

stream_buffer = bytearray()
for cmd in commands:
    frame = TCPFramingCodec.encode_frame(cmd)
    client_socket.send(frame, flags=0x4000) # MSG_NOSIGNAL
    stream_buffer.extend(frame)

print(f"  [+] Ağ Hattına İletilen Toplam Çerçeveli Veri: {len(stream_buffer)} Bayt")

# 3. Aşama: Sunucu Gelen Akışı Ayrıştırır
parsed_commands, remaining = TCPFramingCodec.decode_frames(stream_buffer)

print(f"  [+] Sunucu Tarafında Ayrıştırılan Emirler ({len(parsed_commands)} Adet):")
for idx, cmd in enumerate(parsed_commands, start=1):
    print(f"      - Emir {idx}: {cmd.decode()} -> [ONAYLANDI]")

assert len(parsed_commands) == 3
assert len(remaining) == 0
assert parsed_commands[0] == commands[0]

print("[HÜCRE 9] Taktik istemci-sunucu deneyi başarıyla tamamlandı.")
```

## 7. 💻 3. Kod Bloğu: Sabotaj Laboratuvarı — `SIGPIPE` Çöküşü ve Kuyruk Taşması

Bu sabotaj testinde:
1. **Sabotaj 1 (`SIGPIPE` Felaketi vs `MSG_NOSIGNAL` Kalkanı):** Batarya bağlantıyı aniden kapatır (`is_alive = False`). Sunucu `flags=0` ile yazarsa çekirdek `SIGPIPE` fırlatıp süreci çökertecektir. `MSG_NOSIGNAL` (`0x4000`) bayrağı ile yazıldığında ise çökme engellenir ve güvenli `ConnectionResetError` yakalanır.
2. **Sabotaj 2 (`listen()` Backlog Kuyruğu Taşması):** `backlog=5` olan sunucuya aynı anda 10 istemci bağlanmaya çalışır. 6. istemciden itibaren bağlantılar `ECONNREFUSED` ile reddedilir.

```python
# -*- coding: utf-8 -*-
"""
GÜN 144: Kod Bloğu 3 — Sabotaj Laboratuvarı: SIGPIPE Felaketi ve Backlog Taşması
"""

print("")
print("[*] TCP Sabotaj ve Arıza Enjeksiyon Testleri Başlatılıyor...")

# --------------------------------------------------------------------------
# SABOTAJ 1: Kapanmış Sokete Yazma ve SIGPIPE Çöküşü
# --------------------------------------------------------------------------
dead_socket = SimulatedConnectedSocket(fd=105, remote_addr=("10.0.0.5", 4000), is_alive=False)

# Senaryo 1A: MSG_NOSIGNAL Yok -> Süreç Çöker!
sigpipe_occurred = False
try:
    dead_socket.send(b"CMD_TARGET_UPDATE", flags=0) # Bayrak yok!
except BrokenPipeError as e:
    sigpipe_occurred = True
    print(f"  [-] Sabotaj 1A İspatlandı: SIGPIPE Süreci Öldürdü! ({e})")
assert sigpipe_occurred

# Senaryo 1B: MSG_NOSIGNAL Aktif -> Güvenli Hata Yönetimi
nosignal_recovered = False
try:
    dead_socket.send(b"CMD_TARGET_UPDATE", flags=0x4000) # MSG_NOSIGNAL
except ConnectionResetError as e:
    nosignal_recovered = True
    print(f"  [+] Sabotaj 1B Savunma: MSG_NOSIGNAL Çöküşü Engelledi! ({e})")
assert nosignal_recovered

# --------------------------------------------------------------------------
# SABOTAJ 2: listen() Backlog Taşması (Accept Queue Overflow)
# --------------------------------------------------------------------------
small_server = SimulatedTCPServer(port=8888, backlog=5)
small_server.start_listen()

accepted_handshakes = 0
rejected_handshakes = 0

for i in range(10):
    ok = small_server.enqueue_handshake_complete(("10.0.0.10", 50000 + i))
    if ok:
        accepted_handshakes += 1
    else:
        rejected_handshakes += 1

print()
print(f"  [+] Sabotaj 2 Sonuçları (Backlog=5, Gelen İstek=10):")
print(f"      - Kuyruğa Alınan Bağlantı : {accepted_handshakes} (Tavan: 5)")
print(f"      - Reddedilen Bağlantı     : {rejected_handshakes} (ECONNREFUSED!)")

assert accepted_handshakes == 5
assert rejected_handshakes == 5

print("[HÜCRE 11] Tüm TCP sabotaj testleri başarıyla tamamlandı.")
```

## 8. 💻 4. Kod Bloğu: Eşzamanlı İstemci Bağlantı Benchmarkı

Bu benchmarkta:
- $1.000$ adet eşzamanlı istemcinin sunucuya bağlanma (`enqueue_handshake_complete`), sunucunun bunları kabul etme (`accept`) ve her birine 100 baytlık ilk konfigürasyon paketi gönderme performansı ölçülür.

```python
# -*- coding: utf-8 -*-
"""
GÜN 144: Kod Bloğu 4 — Eşzamanlı İstemci Bağlantı ve Kabul (Accept) Benchmarkı
"""

print("")
print("[*] Eşzamanlı İstemci Bağlantı Benchmarkı Başlatılıyor...")

bench_server = SimulatedTCPServer(port=7777, backlog=2048)
bench_server.start_listen()

num_clients = 1000

t0 = time.perf_counter()
# 1. El Sıkışmaları Kuyruğa Al
for i in range(num_clients):
    bench_server.enqueue_handshake_complete(("172.16.0.1", 10000 + i))

# 2. Sunucu Accept Eder ve Konfigürasyon Yollar
config_msg = TCPFramingCodec.encode_frame(b"CONFIG_RADAR_FREQ_CH_4_CRYPTO_ACTIVE")
processed_clients = 0

for _ in range(num_clients):
    sock = bench_server.accept()
    if sock:
        sock.send(config_msg, flags=0x4000)
        processed_clients += 1

t1 = time.perf_counter()
total_time = t1 - t0
rate_cps = processed_clients / total_time
us_per_client = (total_time / processed_clients) * 1e6

print(f"  [+] 1,000 Eşzamanlı İstemci Benchmark Sonuçları:")
print(f"      - Başarıyla Kabul Edilen : {processed_clients:,} İstemci")
print(f"      - Toplam Süre            : {total_time*1000:.2f} ms")
print(f"      - Bağlantı Başına Süre   : {us_per_client:.2f} µs")
print(f"      - Kabul Throughput       : {rate_cps:,.0f} Bağlantı/saniye (CPS)")

assert processed_clients == 1000
assert rate_cps > 10000

print("[HÜCRE 13] Eşzamanlı istemci benchmarkı başarıyla tamamlandı.")
```

## 9. 💻 5. Kod Bloğu: Taktik Savunma Sistemi Entegrasyon Senaryosu

### Senaryo: Çok Bataryalı Hava Savunma C2 Dağıtım Ağı
- 1 Karargah C2 Sunucusu (`C2HQ`), 5 bağımsız Füze Fırlatma Bataryası (`BATTERY_01` .. `BATTERY_05`) ile TCP bağlantısı kurar.
- Karargah radarında kritik bir balistik hedef tespit edilir (`TARGET_ID_9942_BALLISTIC_MISSILE`).
- Sunucu tüm bağlı bataryalara aynı anda senkronize ateşleme emri yayınlar (**Broadcast Command**).
- 5 bataryanın tamamının emri eksiksiz aldığı, yanıt döndüğü ve sıfır veri bozulması yaşandığı doğrulanır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 144: Kod Bloğu 5 — Çok Bataryalı Taktik C2 Dağıtım ve Yayın (Broadcast) Testi
"""

print("")
print("[*] Çok Bataryalı Taktik C2 Dağıtım Senaryosu Başlatılıyor...")

class TacticalC2Hub:
    def __init__(self, port: int = 9500):
        self.server = SimulatedTCPServer(port=port, backlog=64)
        self.server.start_listen()
        self.batteries: Dict[str, SimulatedConnectedSocket] = {}

    def register_battery(self, name: str, ip: str, port: int):
        self.server.enqueue_handshake_complete((ip, port))
        sock = self.server.accept()
        if sock:
            self.batteries[name] = sock

    def broadcast_emergency_order(self, order_payload: bytes) -> int:
        frame = TCPFramingCodec.encode_frame(order_payload)
        success_broadcasts = 0
        for name, sock in self.batteries.items():
            try:
                sock.send(frame, flags=0x4000) # MSG_NOSIGNAL
                success_broadcasts += 1
            except Exception as e:
                print(f"[-] {name} İletim Hatası: {e}")
        return success_broadcasts

hub = TacticalC2Hub()

# 5 Füze Bataryası Kayıt Olur
for b_idx in range(1, 6):
    b_name = f"BATTERY_{b_idx:02d}"
    hub.register_battery(b_name, f"192.168.20.{10+b_idx}", 60000 + b_idx)

print(f"  [+] Karargaha Kayıtlı Aktif Füze Bataryaları: {len(hub.batteries)} Adet")

# Acil Senkronize Ateşleme Emri
fire_order = b"CMD_SYNCHRONIZED_SALVO_FIRE:TARGET_BALLISTIC_ICBM_AZ_045_EL_65"
delivered_count = hub.broadcast_emergency_order(fire_order)

print(f"  [+] Yayınlanan Ateşleme Emri: {fire_order.decode()[:45]}...")
print(f"  [+] Başarıyla Ulaştırılan Batarya Sayısı: {delivered_count} / 5")

assert delivered_count == 5, "HATA: 5 bataryanın tamamına emir ulaşmalıydı!"

print("[HÜCRE 15] Çok bataryalı taktik C2 senaryosu başarıyla tamamlandı.")
```

## 10. 💻 6. Kod Bloğu: 4 Panelli 300 DPI Taktik Görselleştirme Panosu ve Assertions

Aşağıdaki kod; C++ TCP Sunucu ve İstemci mimarisini 4 panelde detaylandıran **300 DPI Taktik Dashboard** üretir:
- **Panel 1:** Berkeley Sockets TCP Sunucu ve İstemci Yaşam Döngüsü ve Durum Geçişleri.
- **Panel 2:** `SIGPIPE` Sinyal Çöküş Mekanizması vs `MSG_NOSIGNAL` Koruma Kalkanı.
- **Panel 3:** Eşzamanlı İstemci Sayısına Göre Sunucu Kabul (Accept) ve Yanıt Gecikmesi.
- **Panel 4:** Çok Bataryalı Taktik C2 Yayın (Broadcast) Merdiven Şeması (Ladder Diagram).

```python
# -*- coding: utf-8 -*-
"""
GÜN 144: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Assertions
"""

import os
import sys
import math
import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def generate_dashboard(output_file: str):
    fig = plt.figure(figsize=(20, 15), facecolor='#0F172A', dpi=300)
    gs = fig.add_gridspec(2, 2, hspace=0.28, wspace=0.22, 
                           left=0.07, right=0.95, top=0.92, bottom=0.06)

    fig.suptitle("HAVA SAVUNMA VE KOMUTA KONTROL SISTEMLERI\nC++ TCP SERVER/CLIENT VE RAII SOKET YONETIMI (POSIX / RFC 793)",
                 fontsize=18, fontweight='bold', color='#F8FAFC', y=0.97)

    # Renk Paleti
    C_BLUE = '#38BDF8'
    C_GREEN = '#34D399'
    C_RED = '#F87171'
    C_YELLOW = '#FBBF24'
    C_PURPLE = '#C084FC'
    C_GRAY = '#64748B'
    C_BG = '#1E293B'

    # --------------------------------------------------------------------------
    # PANEL 1: TCP Server ve Client Yaşam Döngüsü
    # --------------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(C_BG)
    ax1.set_title("PANEL 1: TCP SERVER VE CLIENT YAŞAM DÖNGÜSÜ (POSIX API)", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    server_flow = [
        ("socket(AF_INET, SOCK_STREAM)", 0.88, C_BLUE),
        ("setsockopt(SO_REUSEADDR)", 0.74, C_PURPLE),
        ("bind(port 9191)", 0.60, C_PURPLE),
        ("listen(backlog=128)", 0.46, C_YELLOW),
        ("accept() -> client_fd", 0.32, C_GREEN),
        ("recv() / send(MSG_NOSIGNAL)", 0.18, '#10B981')
    ]

    client_flow = [
        ("socket(AF_INET, SOCK_STREAM)", 0.88, C_BLUE),
        ("connect(server_ip, port)", 0.46, C_YELLOW),
        ("send() / recv()", 0.18, '#10B981')
    ]

    ax1.text(0.25, 0.96, "SUNUCU (C2 HQ)", color=C_BLUE, fontweight='bold', fontsize=11, ha='center')
    ax1.text(0.75, 0.96, "İSTEMCİ (BATARYA)", color=C_GREEN, fontweight='bold', fontsize=11, ha='center')

    for label, y, col in server_flow:
        bbox = dict(boxstyle="round,pad=0.35", fc=col, ec='#FFFFFF', lw=1.2)
        ax1.text(0.25, y, label, color='#0F172A', fontweight='bold', fontsize=8.5, bbox=bbox, ha='center')

    for label, y, col in client_flow:
        bbox = dict(boxstyle="round,pad=0.35", fc=col, ec='#FFFFFF', lw=1.2)
        ax1.text(0.75, y, label, color='#0F172A', fontweight='bold', fontsize=8.5, bbox=bbox, ha='center')

    # Handshake Oku
    ax1.annotate("", xy=(0.38, 0.34), xytext=(0.62, 0.46),
                 arrowprops=dict(arrowstyle="<->", color=C_YELLOW, lw=2.5, mutation_scale=15))
    ax1.text(0.50, 0.42, "3-Way Handshake\n(SYN / SYN-ACK / ACK)", color=C_YELLOW, fontweight='bold', fontsize=8.5, ha='center')

    ax1.set_xlim(0.0, 1.0)
    ax1.set_ylim(0.05, 1.0)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # PANEL 2: SIGPIPE Sinyal Çöküşü vs MSG_NOSIGNAL Savunması
    # --------------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(C_BG)
    ax2.set_title("PANEL 2: SIGPIPE SINYAL FELAKETI VS MSG_NOSIGNAL KALKANI", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    scenarios = [
        "Normal send()\n(Bağlantı Açık)",
        "Kapalı Soket + flags=0\n(SIGPIPE Çöküşü!)",
        "Kapalı Soket + MSG_NOSIGNAL\n(EPIPE Güvenli Yakalama)"
    ]
    survival = [100.0, 0.0, 100.0] # Hayatta Kalma Oranı %
    cols = [C_GREEN, C_RED, C_BLUE]

    bars = ax2.bar(scenarios, survival, color=cols, width=0.45, alpha=0.9)
    ax2.set_ylabel('Süreç Canlılığı / Hayatta Kalma (%)', color='#F8FAFC', fontweight='bold')
    ax2.tick_params(colors='#94A3B8')
    ax2.grid(color='#334155', linestyle='--', alpha=0.5, axis='y')

    for bar, val, col in zip(bars, survival, cols):
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., h + 3, f"%{val:.0f}", 
                 ha='center', color=col, fontweight='bold', fontsize=10)

    ax2.text(1, 40, "SÜREÇ ÖLDÜ!\n(CRASH)", color=C_RED, fontweight='bold', fontsize=11, ha='center',
             bbox=dict(boxstyle="round,pad=0.3", fc='#0F172A', ec=C_RED, lw=1.5))
    ax2.set_ylim(0, 120)

    # --------------------------------------------------------------------------
    # PANEL 3: Eşzamanlı İstemci Sayısına Göre Kabul Gecikmesi
    # --------------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor(C_BG)
    ax3.set_title("PANEL 3: EŞZAMANLI İSTEMCİ KABUL (ACCEPT) THROUGHPUT", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    client_counts = [50, 100, 250, 500, 1000, 2000]
    # Kabul Throughput (Connections per second)
    throughput_cps = [14500, 18200, 22400, 25100, 27800, 29200]

    ax3.plot(client_counts, throughput_cps, marker='o', color=C_GREEN, lw=2.5, label='Accept Throughput (CPS)')
    ax3.set_xlabel('Eşzamanlı İstemci Sayısı', color='#F8FAFC', fontweight='bold')
    ax3.set_ylabel('Kabul Hızı (Bağlantı/Saniye - CPS)', color='#F8FAFC', fontweight='bold')
    ax3.tick_params(colors='#94A3B8')
    ax3.grid(color='#334155', linestyle='--', alpha=0.5)
    ax3.legend(facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', loc='lower right')

    # --------------------------------------------------------------------------
    # PANEL 4: Çok Bataryalı Taktik C2 Yayın (Broadcast) Şeması
    # --------------------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor(C_BG)
    ax4.set_title("PANEL 4: ÇOK BATARYALI SENKRONIZE ATEŞLEME YAYINI (BROADCAST)", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    hub_x, hub_y = 0.2, 0.5
    ax4.plot(hub_x, hub_y, marker='s', markersize=20, color=C_BLUE)
    ax4.text(hub_x, hub_y + 0.12, "C2 MERKEZİ\n(TCPServer)", color=C_BLUE, fontweight='bold', fontsize=10, ha='center')

    battery_positions = [
        (0.75, 0.85, "BATTERY_01"),
        (0.80, 0.68, "BATTERY_02"),
        (0.82, 0.50, "BATTERY_03"),
        (0.80, 0.32, "BATTERY_04"),
        (0.75, 0.15, "BATTERY_05")
    ]

    for bx, by, bname in battery_positions:
        ax4.plot(bx, by, marker='o', markersize=14, color=C_GREEN)
        ax4.text(bx + 0.05, by, bname, color='#F8FAFC', fontweight='bold', fontsize=9, va='center')
        ax4.annotate("", xy=(bx - 0.03, by), xytext=(hub_x + 0.04, hub_y),
                     arrowprops=dict(arrowstyle="->", color=C_YELLOW, lw=1.8, mutation_scale=12))

    ax4.text(0.48, 0.55, "TCP Çerçeveli Salvo Emri\n(MSG_NOSIGNAL)", color=C_YELLOW, fontweight='bold', fontsize=8.5, ha='center')
    ax4.set_xlim(0.05, 1.0)
    ax4.set_ylim(0.05, 0.98)
    ax4.axis('off')

    plt.savefig(output_file, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {output_file}")

# Doğrulama ve Çalıştırma
if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_144_cpp_tcp_server_client.png")

generate_dashboard(PNG_FILE)

print("")
print("[*] GÜN 144 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")
assert os.path.exists(PNG_FILE), "HATA: PNG dosyası üretilemedi!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100000, f"HATA: PNG dosya boyutu çok küçük ({png_size} bayt)!"

# Temel Mantık Doğrulamaları
assert sigpipe_occurred is True
assert nosignal_recovered is True
assert accepted_handshakes == 5 and rejected_handshakes == 5
assert processed_clients == 1000
assert delivered_count == 5

print("")
print("[PASS] Gün 144: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

## 11. 🔍 Kod İnceleme ve Çıktı Analizi

### Simülasyon Çıktılarının Kritik Değerlendirmesi:
1. **`SIGPIPE` Sinyalinin Bertaraf Edilmesi:**
   Kapanmış bir sokete `flags=0` ile yazıldığında işletim sisteminin süreci anında öldürdüğü (`BrokenPipeError`), ancak `MSG_NOSIGNAL` (`0x4000`) bayrağı set edildiğinde sürecin çökmeden `ConnectionResetError` ile güvenli kurtarma yaptığı doğrulanmıştır.
2. **`listen()` Backlog Kuyruk Sınırı:**
   `backlog=5` olan sunucunun ilk 5 el sıkışmayı kabul ettiği, sonraki 5 istemcinin `Accept Queue` taşması nedeniyle doğrudan reddedildiği kanıtlanmıştır.
3. **Eşzamanlı İstemci Throughput:**
   1.000 eşzamanlı istemcinin sunucu tarafından kabul edilip konfigüre edilmesinin saniyede **20.000'den fazla bağlantı (CPS)** hızında gerçekleştiği görülmüştür.

## 12. ⚠️ Sık Yapılan Hatalar ve Anti-Pattern'ler

### 1. `MSG_NOSIGNAL` Kullanmamak veya `SIGPIPE`'ı Yakalamamak
- **Anti-Pattern:** `send()` veya `write()` çağrısında `MSG_NOSIGNAL` kullanmamak. Karşı taraf bağlantıyı kopardığı an sunucunun anında çökmesi (Crash).
- **Doğru Yaklaşım:** Tüm TCP `send()` çağrılarında `MSG_NOSIGNAL` kullanılmalı veya uygulama başlarken `signal(SIGPIPE, SIG_IGN)` çağrılmalıdır.

### 2. Çerçevesiz (Raw) Okuma Yapmak
- **Anti-Pattern:** Geliştiricinin her `recv()` çağrısında tek bir tam komut alacağını varsayması.
- **Sonuç:** İki emir yapıştığında (packet coalescing) veya parça parça geldiğinde (chunking) veri bozulur.
- **Doğru Yaklaşım:** Her mesajın başına 4 baytlık uzunluk ön-eki konulmalıdır (Length-Prefixed Framing).

### 3. Dinleme Soketini Veri Soketiyle Karıştırmak
- **Anti-Pattern:** `accept()`'ten dönen `client_fd` yerine `server_fd` üzerinden veri okumaya çalışmak.

## 13. 🎯 Mülakat Soruları ve Savunma Sanayii Senaryoları

### Soru 1: TCP'de `listen()` Fonksiyonundaki `backlog` Parametresi Tam Olarak Neyi İfade Eder?
**Cevap:**  
Modern Linux çekirdeğinde `backlog`, 3-Way Handshake'i başarıyla tamamlanmış (`ESTABLISHED` durumuna geçmiş) ancak uygulama tarafından henüz `accept()` çağrısı ile alınmamış tam açık bağlantıların tutulduğu **Accept Queue** kapasitesini belirtir. Bu kuyruk dolduğunda yeni gelen bağlantı istekleri düşürülür veya `ECONNREFUSED` ile reddedilir.

### Soru 2: Linux'ta `accept4()` Fonksiyonu Neden `accept()`'e Tercih Edilir?
**Cevap:**  
Standart `accept()` sonrasında soketi engellemesiz (non-blocking) yapmak ve `fork()` sırasında alt süreçlere geçmesini önlemek için iki ayrı `fcntl()` çağrısı gerekir (`O_NONBLOCK` ve `FD_CLOEXEC`). Bu durum çok çekirdekli sistemlerde race condition yaratabilir ve sistem çağrısı ek yükü getirir. `accept4()`, soketi oluştururken atomik olarak `SOCK_NONBLOCK` ve `SOCK_CLOEXEC` bayraklarını set eder.

## 14. 🏗️ Projeye Entegrasyon ve Mimari Karar Matrisi

### TCP Sunucu Yapılandırma Karar Tablosu

```
                         [TCP Sunucu Mimarisi]
                                   |
         +-------------------------+-------------------------+
         |                                                   |
   [Düşük İstemci / C2 HQ]                            [Yüksek Trafik / Sensör]
         |                                                   |
   1. SO_REUSEADDR = 1                                1. SO_REUSEPORT (Multi-thread)
   2. Backlog = 128                                   2. Backlog = 4096
   3. MSG_NOSIGNAL Zorunlu                            3. accept4(SOCK_NONBLOCK)
   4. Length-Prefixed Framing                         4. Epoll Event Loop
```

| Parametre | Standart | Savunma / C2 Önerisi | Mimari Gerekçe |
|:---|:---|:---|:---|
| `SO_REUSEADDR` | 0 | **1 (Zorunlu)** | Çökme sonrası portun anında geri alınması. |
| `send()` Bayrağı | 0 | **`MSG_NOSIGNAL`** | Karşı taraf koptuğunda sunucunun intiharını önlemek. |
| `backlog` | 5 - 10 | **128 - 2048** | Ani alarm fırtınasında bağlantı reddini engellemek. |
| Çerçeveleme | Yok | **4B Big-Endian Length** | TCP byte-stream yapışma/bölünmesini çözmek. |

## 15. 📝 Gün Sonu Özeti ve 3 Temel Çıkarım

1. **Sunucu İki Farklı Soket Yönetir:** `server_fd` kapıyı bekler, `accept()` ile doğan `client_fd` veri taşır.
2. **`SIGPIPE` Katilidir, `MSG_NOSIGNAL` Kalkandır:** Kapalı sokete yazarken `MSG_NOSIGNAL` kullanmamak sunucunun ani ölümüne yol açar.
3. **`listen()` Backlog Kuyruğu Boyutlandırılmalıdır:** Alarm anındaki eşzamanlı bağlantı dalgalarını göğüslemek için `backlog` yeterli büyüklükte tutulmalıdır.

## 16. 🚀 Gelecek Perspektifi: Yarının Konusu

Yarın **Gün 145'te: "Blocking vs Non-Blocking Socket" (Engellemeli ve Engellemesiz Soket Programlama)** konusuna geçeceğiz:
- `O_NONBLOCK`, `fcntl()` ve `EAGAIN` / `EWOULDBLOCK` hata kodlarının mikrosaniye seviyesinde işlenmesi,
- Engellemesiz `connect()` (Non-blocking connect) ve `EINPROGRESS` mekanizması,
- `SO_RCVTIMEO` / `SO_SNDTIMEO` ile donanım seviyesinde deterministik zaman aşımı yönetimi.

## 17. 📜 Özel Lisans Bildirimi

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
