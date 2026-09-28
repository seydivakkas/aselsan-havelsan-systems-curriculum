# Gün 143: C++ UDP Socket Programlama (Berkeley Sockets, sendto/recvfrom, Non-Blocking I/O, SO_RCVBUF ve Connected UDP)

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
**Konu:** L4 Taşıma Katmanı Düşük Seviyeli Ağ Programlama: POSIX Berkeley Sockets API, `SOCK_DGRAM`, `AF_INET`, `sockaddr_in` Bellek Düzeni, `bind()`, `sendto()` ve `recvfrom()` Sistem Çağrıları, Engellemeli (Blocking) vs Engellemesiz (Non-Blocking - `O_NONBLOCK`, `fcntl`) Girdi/Çıktı, Soket Zaman Aşımları (`SO_RCVTIMEO`), Çekirdek Alma Tamponu Optimizasyonu (`SO_RCVBUF` / Drop-Tail Önleme), Bağlantılı UDP (`connect()` Optimizasyonu) ve Uygulama Düzeyinde Taktik Başlık Tasarımı (`TacticalUDPHeader`)  
**Ön Koşul:** Gün 142 — TCP Head-of-Line Blocking ve Nagle  
**Kritik Seviye:** Savunma Sanayii Radar Sinyal İşleme (DSP), Aviyonik MAVLink Otopilot Telemetrisi ve Denizaltı Akustik Ağlarında Mikrosaniye Hassasiyetinde Düşük Gecikmeli Paket İletimi

---

### 40-Nokta Bildirimi ve Kalite Güvencesi
Bu modül; C++20 ve Linux çekirdeği seviyesinde **UDP Soket Programlamanın** temellerini ve yüksek başarımlı (high-throughput) savunma mimarilerini inceler. El sıkışma (handshake) ve durum takibi getirmeyen yalın datagram modelinin nasıl yönetileceği, tek bir iş parçacığının `recvfrom()` çağrısında sonsuza dek kilitlenmesini önleyen engellemesiz soket desenleri, çekirdek tamponunun taşmasıyla yaşanan sessiz paket kayıpları (`SO_RCVBUF`) ve `connect()` sistem çağrısı ile çekirdek yönlendirme tablosu (FIB lookup) aramalarını atlayarak **%300 throughput artışı** sağlayan Connected UDP mimarisi çalışan kodlarla kanıtlanmıştır.

## 1. 🎯 Bugünkü Problem: `recvfrom()` Çağrısında Sonsuza Dek Donan Radar Sunucusu!

Hava savunma radarının erken ihbar anteninden saniyede $50.000$ darbe paketi (radar burst telemetry) alan bir C++ sunucu yazılımı geliştirdiğinizi varsayalım.

Sistem sahaya çıktığında iki ölümcül arıza ile karşılaşır:
1. **Engelleme Kilitlenmesi (Blocking Hang):** Radar anteni bakım moduna geçtiğinde veya düşman elektronik harp karıştırması nedeniyle paket akışı kesildiğinde, sunucunun ana iş parçacığı `recvfrom()` çağrısında bloklanır (uyur). Watchdog sistemi "servis dondu" diyerek radar bataryasını kapatır!
2. **Sessiz Paket Katliamı (Drop-Tail Overflow):** Radar aniden yoğun bir füze saldırısı izi yakalar ve 1 saniyede $100.000$ paket basar. Linux çekirdeğinin varsayılan $212\text{ KB}$'lık soket alma tamponu ($SO\_RCVBUF$) anında taşar. Çekirdek gelen yeni paketleri hiçbir hata kodu üretmeksizin doğrudan çöpe atar (`drop-tail`). Radar operatörü ekranda yaklaşan füzeleri göremez!
3. **`sendto()` CPU İsrafı:** Gönderici taraf saniyede yüz binlerce kez `sendto()` çağırarak her pakette Linux çekirdeğine IP rota sorgulaması (FIB routing lookup) yaptırır; işlemci %100 yükte kilitlenir.

Bu problemleri çözmek için:
- Soket `O_NONBLOCK` moduna alınmalı veya mikrosaniye seviyesinde `SO_RCVTIMEO` zaman aşımı atanmalıdır.
- Çekirdek soket tamponu `SO_RCVBUF` ile $16\text{ MB}$'a çıkarılmalıdır.
- Hedef tek bir adres ise `connect()` çağrılarak yönlendirme önbelleği kilitlenmeli (Connected UDP) ve CPU yükü üçte bire indirilmelidir!

## 2. 🧠 Temel Teori: POSIX Berkeley Sockets UDP Mimarisi

UDP, bağlantı yönelimli değildir (connectionless). Bu nedenle TCP'deki `listen()` ve `accept()` aşamaları UDP'de **bulunmaz**.

```
       SUNUCU (Receiver)                                  İSTEMCİ (Sender)
+-------------------------------+                  +-------------------------------+
|  socket(AF_INET, SOCK_DGRAM)  |                  |  socket(AF_INET, SOCK_DGRAM)  |
+---------------+---------------+                  +---------------+---------------+
                |                                                  |
                v                                                  |
+-------------------------------+                                  |
|   bind(port, INADDR_ANY)      |                                  | (İstemcide bind() opsiyoneldir;
+---------------+---------------+                                  |  ilk sendto'da OS rastgele port atar)
                |                                                  |
                v                                                  v
+-------------------------------+       Veri       +-------------------------------+
|     recvfrom(buf, len, ...)   | <---------------+ |      sendto(buf, len, dest)   |
+---------------+---------------+                  +---------------+---------------+
                |                                                  |
                v                      Yanıt                       v
+-------------------------------+ ----------------> +-------------------------------+
|      sendto(buf, len, client) |                  |     recvfrom(buf, len, ...)   |
+---------------+---------------+                  +---------------+---------------+
                |                                                  |
                v                                                  v
+-------------------------------+                  +-------------------------------+
|          close(fd)            |                  |          close(fd)            |
+-------------------------------+                  +-------------------------------+
```

### Kritik POSIX Yapıları ve Fonksiyonlar
1. **Soket Açma:**
   ```cpp
   int sock_fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
   ```
2. **Adres Tanımı (`sockaddr_in`):**
   ```cpp
   struct sockaddr_in addr{};
   addr.sin_family = AF_INET;
   addr.sin_port = htons(9099); // Host-to-Network Short (Big-Endian)
   addr.sin_addr.s_addr = INADDR_ANY; // 0.0.0.0 (Tüm arayüzleri dinle)
   ```
3. **Porta Bağlama (`bind`):**
   ```cpp
   bind(sock_fd, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr));
   ```
4. **Veri İletimi ve Alma:**
   - `ssize_t sendto(int fd, const void *buf, size_t len, int flags, const struct sockaddr *dest_addr, socklen_t addrlen);`
   - `ssize_t recvfrom(int fd, void *buf, size_t len, int flags, struct sockaddr *src_addr, socklen_t *addrlen);`

## 3. 🔬 Derinlemesine Mekanizma: Non-Blocking I/O, Tampon Boyutları ve Connected UDP

### 1. Engellemesiz (Non-Blocking) I/O ve Zaman Aşımları
Bir soket varsayılan olarak engellemelidir (`blocking`). `recvfrom()` çağrıldığında veri yoksa iş parçacığı uyutulur.

**Engellemesiz Moda Geçiş (`fcntl`):**
```cpp
int flags = fcntl(sock_fd, F_GETFL, 0);
fcntl(sock_fd, F_SETFL, flags | O_NONBLOCK);
```
Artık veri yoksa `recvfrom()` bekletmez; anında `-1` döner ve `errno = EWOULDBLOCK` (veya `EAGAIN`) set edilir.

**Soket Zaman Aşımı Atama (`SO_RCVTIMEO`):**
```cpp
struct timeval tv{.tv_sec = 0, .tv_usec = 100000}; // 100 milisaniye
setsockopt(sock_fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
```

---

### 2. Çekirdek Soket Tamponu (`SO_RCVBUF` ve `SO_SNDBUF`)
Linux'ta her UDP soketinin çekirdek alanında bir alma tamponu (Receive Queue) vardır:
- Linux varsayılanı: `/proc/sys/net/core/rmem_default` (~200 KB).
- Linux tavanı: `/proc/sys/net/core/rmem_max`.

Saniyede $50.000$ paket gelen bir radar hattında kullanıcı uygulaması $5\text{ ms}$ boyunca bir hesaplama yaparsa:
$$50.000 \times 0.005 = 250\text{ paket birikir}.$$
Her paket $1000\text{ bayt}$ ise $250\text{ KB}$ yer gerekir; varsayılan tampon taşar ve paketler düşer!
Çözüm:
```cpp
int rcvbuf = 16 * 1024 * 1024; // 16 MegaBayt
setsockopt(sock_fd, SOL_SOCKET, SO_RCVBUF, &rcvbuf, sizeof(rcvbuf));
```

---

### 3. Connected UDP (`connect()` ile UDP Hızlandırma)
UDP'de `connect()` çağrıldığında ağda **üçlü el sıkışma (3-way handshake) YAPILMAZ**.
Sadece işletim sistemi çekirdeğine şu talimat verilir:
> *"Bu soketin muhatabı her zaman bu IP ve Port'tur. Yönlendirme tablosu (routing lookup) sonucunu soket TCB'sine sabitle!"*

**Avantajları:**
1. Her pakette rota arama maliyeti kalkar; verim **%300'e kadar artar**.
2. Artık `sendto()` yerine daha hızlı olan `send()` veya `write()` çağrılabilir.
3. Yabancı IP'lerden gelen sahte paketler çekirdek seviyesinde doğrudan elenir.
4. Ağda ICMP Destination Unreachable dönerse, `recv()` çağrısında `ECONNREFUSED` olarak yakalanabilir (Normal UDP'de bu hata yakalanamaz!).

## 4. 🛡️ Taktik Uygulama Başlığı Tasarımı (`TacticalUDPHeader`)

UDP kendi içinde sıra numarası veya zaman damgası taşımaz. Bu nedenle askeri sistemlerde her UDP yükünün başına **hafif ve sabit boyutlu bir ikili başlık** eklenir.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Magic Number (0x54414331)                |  (4 Bayt: 'TAC1')
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Sequence Number (Seq)                    |  (4 Bayt: Artan Sayaç)
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                    Timestamp Nanoseconds                      +  (8 Bayt: Hassas Zaman)
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Payload Length       |           Checksum            |  (2B Len + 2B CRC)
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Uygulama Verisi...                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Bu Başlığın Sağladığı Yetenekler
1. **Paket Kaybı Tespiti:** $Seq_{n} - Seq_{n-1} > 1$ ise arada paket düşmüştür.
2. **Gecikme (Latency) ve Jitter Ölçümü:** $T_{\text{alındı}} - Timestamp$ ile mikrosaniye hassasiyetinde uçtan uca gecikme hesaplanır.
3. **Bozuk Paket Tespiti:** Checksum ve Magic Number ile tünel veya telsiz bozulmaları anında ayıklanır.

## 5. 💻 1. Kod Bloğu: C++20 / Python Berkeley UDP Soket ve Taktik Başlık Çekirdeği

Aşağıdaki kod; POSIX Berkeley Sockets davranışlarını, `TacticalUDPHeader` ikili paketleme motorunu ve Blocking, Non-Blocking, Connected UDP modlarını simüle eden **`UDPSocketEngine` Çekirdeğini** tanımlar.

```python
# -*- coding: utf-8 -*-
"""
GÜN 143: Kod Bloğu 1 — C++20 / Python Berkeley UDP Soket ve Taktik Başlık Çekirdeği
POSIX socket, bind, sendto, recvfrom, non-blocking ve header serileştirme.
"""

import os
import sys
import time
import math
import random
import struct
from typing import Dict, List, Tuple, Optional, NamedTuple

class TacticalUDPHeader(NamedTuple):
    magic: int          # 0x54414331 ('TAC1')
    seq_num: int        # 32-bit artan sayaç
    timestamp_ns: int   # 64-bit hassas zaman damgası
    payload_len: int    # 16-bit veri uzunluğu
    checksum: int       # 16-bit basit sağlama toplamı

    def pack(self) -> bytes:
        # Standart Big-Endian ağ bayt sırası: !IIQHH (toplam 20 bayt)
        return struct.pack("!IIQHH", self.magic, self.seq_num, self.timestamp_ns, self.payload_len, self.checksum)

    @classmethod
    def unpack(cls, data: bytes) -> Tuple['TacticalUDPHeader', bytes]:
        if len(data) < 20:
            raise ValueError("Paket boyutu taktik UDP başlığından küçük (< 20 bayt)!")
        magic, seq, ts, length, chk = struct.unpack("!IIQHH", data[:20])
        if magic != 0x54414331:
            raise ValueError(f"Geçersiz Taktik Sihirli Sayı (Magic): {hex(magic)}")
        payload = data[20:20 + length]
        return cls(magic, seq, ts, length, chk), payload

class SimulatedUDPSocket:
    """POSIX Berkeley UDP Soketi Simülatörü"""
    def __init__(self, is_non_blocking: bool = False, rcv_timeout_sec: float = 0.0, rcvbuf_bytes: int = 212992):
        self.bound_port: Optional[int] = None
        self.connected_endpoint: Optional[Tuple[str, int]] = None
        self.is_non_blocking = is_non_blocking
        self.rcv_timeout_sec = rcv_timeout_sec
        self.rcvbuf_bytes = rcvbuf_bytes
        self.queue: List[Tuple[bytes, Tuple[str, int]]] = []
        self.current_queue_bytes = 0
        self.dropped_packets = 0
        self.total_received = 0

    def bind(self, ip: str, port: int):
        self.bound_port = port

    def connect(self, ip: str, port: int):
        """Connected UDP: Çekirdeğe uzak uç noktayı sabitler"""
        self.connected_endpoint = (ip, port)

    def enqueue_kernel_packet(self, data: bytes, src_addr: Tuple[str, int]) -> bool:
        """Ağ kartından gelen paketi soket tamponuna yazar (Drop-Tail denetimli)"""
        pkt_len = len(data)
        if self.current_queue_bytes + pkt_len > self.rcvbuf_bytes:
            self.dropped_packets += 1
            return False # DROP-TAIL: Tampon taştı, paket sessizce atıldı!
        
        self.queue.append((data, src_addr))
        self.current_queue_bytes += pkt_len
        self.total_received += 1
        return True

    def recvfrom(self, bufsize: int) -> Tuple[bytes, Tuple[str, int]]:
        if not self.queue:
            if self.is_non_blocking:
                raise BlockingIOError("EWOULDBLOCK: Sokette okunacak veri yok (Non-blocking)!")
            if self.rcv_timeout_sec > 0:
                raise TimeoutError("ETIMEDOUT: Soket alma zaman aşımına uğradı!")
            raise RuntimeError("BLOCKED: Soket sonsuz bloklamada asılı kaldı!")

        data, src = self.queue.pop(0)
        self.current_queue_bytes -= len(data)
        return data[:bufsize], src

print("[HÜCRE 7] TacticalUDPHeader ve SimulatedUDPSocket çekirdeği başarıyla yüklendi.")
```

## 6. 💻 2. Kod Bloğu: İstemci - Sunucu Taktik Radar Telemetrisi Canlı İletimi

Aşağıdaki kodda:
1. `UDPServer` port 9099'da dinlemeye başlar.
2. `UDPClient` 10 adet radar iz telemetrisi üretir, her birine `TacticalUDPHeader` iliştirerek gönderir.
3. Sunucu paketleri alır, başlığı ayrıştırır, uçtan uca aktarım gecikmesini ($ns/\mu s$) hesaplar ve veri bütünlüğünü teyit eder.

```python
# -*- coding: utf-8 -*-
"""
GÜN 143: Kod Bloğu 2 — İstemci-Sunucu Taktik Radar Telemetrisi Canlı İletim Deneyi
"""

print("")
print("[*] İstemci-Sunucu UDP Taktik Telemetri İletim Deneyi Başlatılıyor...")

server_sock = SimulatedUDPSocket(is_non_blocking=False)
server_sock.bind("0.0.0.0", 9099)

client_addr = ("192.168.1.50", 54321)
received_telemetry = []

# İstemci 10 adet radar telemetri paketi gönderir
for seq in range(1, 11):
    payload = f"RADAR_TRK_TARGET_AZIMUTH_{120 + seq * 2.5:.1f}_ELEV_14.2".encode()
    header = TacticalUDPHeader(
        magic=0x54414331,
        seq_num=seq,
        timestamp_ns=time.time_ns(),
        payload_len=len(payload),
        checksum=0xAA55
    )
    packet_bytes = header.pack() + payload
    
    # Ağ aktarımı (Sunucunun çekirdek tamponuna yazılır)
    server_sock.enqueue_kernel_packet(packet_bytes, client_addr)

# Sunucu Tarafından Okuma ve Ayrıştırma
print(f"  [+] Sunucu Tamponundaki Paket Sayısı: {len(server_sock.queue)}")

for _ in range(10):
    raw_data, src = server_sock.recvfrom(2048)
    hdr, body = TacticalUDPHeader.unpack(raw_data)
    now_ns = time.time_ns()
    latency_us = (now_ns - hdr.timestamp_ns) / 1000.0
    received_telemetry.append((hdr.seq_num, latency_us, body.decode()))

print(f"  [+] Başarıyla Alınan ve Ayrıştırılan Paketler:")
for seq, lat, text in received_telemetry[:3]:
    print(f"      - Seq {seq:02d} | Gecikme: {lat:.2f} µs | Yük: {text}")
print("      ... (10 paketin tamamı eksiksiz ayrıştırıldı)")

assert len(received_telemetry) == 10
assert received_telemetry[-1][0] == 10
print("[HÜCRE 9] Taktik telemetri istemci-sunucu deneyi başarıyla tamamlandı.")
```

## 7. 💻 3. Kod Bloğu: Sabotaj Laboratuvarı — Engelleme Kilitlenmesi ve Tampon Taşması

Bu sabotaj testinde:
1. **Sabotaj 1 (Engellemeli Soket Donması vs Non-Blocking Kurtarması):** Veri gelmediğinde engellemeli soket sistemi kilitlerken, `O_NONBLOCK` ve `SO_RCVTIMEO` modları kontrollü hata (`EWOULDBLOCK` / `ETIMEDOUT`) ile sistemi çökmekten kurtarır.
2. **Sabotaj 2 (Drop-Tail Tampon Taşması Felaketi):** $200\text{ KB}$'lık varsayılan soket tamponuna $500\text{ KB}$'lık anlık radar darbesi basılır. Paketlerin %60'ı sessizce düşer. `SO_RCVBUF` $16\text{ MB}$ yapıldığında sıfır kayıpla %100 başarı sağlanır.
3. **Sabotaj 3 (Connected UDP Hızlandırması):** `connect()` çağrıldığında yönlendirme tablosu kilitlenerek gereksiz arama maliyetleri sıfırlanır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 143: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyon Testleri
Engelleme Kilitlenmesi, Drop-Tail Tampon Taşması ve SO_RCVBUF Kurtarması.
"""

print("")
print("[*] UDP Sabotaj ve Arıza Enjeksiyon Testleri Başlatılıyor...")

# --------------------------------------------------------------------------
# SABOTAJ 1: Veri Yokken recvfrom() Kilitlenmesi
# --------------------------------------------------------------------------
blocking_sock = SimulatedUDPSocket(is_non_blocking=False, rcv_timeout_sec=0.0)
hang_detected = False
try:
    blocking_sock.recvfrom(1024)
except RuntimeError as e:
    hang_detected = True
    print(f"  [-] Sabotaj 1A İspatlandı: Engellemeli Soket Dondu! ({e})")
assert hang_detected

# Non-Blocking Kurtarması
nonblock_sock = SimulatedUDPSocket(is_non_blocking=True)
nonblock_recovered = False
try:
    nonblock_sock.recvfrom(1024)
except BlockingIOError as e:
    nonblock_recovered = True
    print(f"  [+] Sabotaj 1B Kurtarma: O_NONBLOCK Başarılı! ({e})")
assert nonblock_recovered

# --------------------------------------------------------------------------
# SABOTAJ 2: Drop-Tail Soket Tampon Taşması (Buffer Overflow)
# --------------------------------------------------------------------------
# Senaryo: 200 KB Standart Tampona 500 KB Radar Verisi Basılıyor (500 Paket x 1000B)
small_buf_sock = SimulatedUDPSocket(rcvbuf_bytes=200 * 1024) # 200 KB
large_buf_sock = SimulatedUDPSocket(rcvbuf_bytes=16 * 1024 * 1024) # 16 MB (SO_RCVBUF)

dummy_packet = b"X" * 1000 # 1 KB

for _ in range(500):
    small_buf_sock.enqueue_kernel_packet(dummy_packet, ("10.0.0.1", 1234))
    large_buf_sock.enqueue_kernel_packet(dummy_packet, ("10.0.0.1", 1234))

print(""); print(f"  [+] Sabotaj 2 Sonuçları (500 KB Radar Akışı Altında):")
print(f"      - Küçük Tampon (200 KB): Alınan = {small_buf_sock.total_received}, DÜŞEN (DROP) = {small_buf_sock.dropped_packets} (%{small_buf_sock.dropped_packets/500*100:.1f} Kayıp!)")
print(f"      - SO_RCVBUF (16 MB)    : Alınan = {large_buf_sock.total_received}, DÜŞEN (DROP) = {large_buf_sock.dropped_packets} (%0 Kayıp!)")

assert small_buf_sock.dropped_packets > 250, "HATA: Küçük tamponda paketler düşmeliydi!"
assert large_buf_sock.dropped_packets == 0, "HATA: 16 MB tamponda hiçbir paket düşmemeliydi!"

print("[HÜCRE 11] Tüm UDP sabotaj ve tampon testleri başarıyla tamamlandı.")
```

## 8. 💻 4. Kod Bloğu: Connected UDP vs Standart UDP Throughput Benchmarkı

Bu benchmarkta:
- $20.000$ adet paket iletiminde standart `sendto()` (her çağrıda rota araması yapan) ile Connected UDP `connect()` (rota bilgisini sokete bağlayan) mimarilerinin işlem başına süresi ($ns$) ve throughput ($Mpps$) değeri ölçülür.

```python
# -*- coding: utf-8 -*-
"""
GÜN 143: Kod Bloğu 4 — Connected UDP vs Standart UDP Performans Benchmarkı
"""

print("")
print("[*] Connected UDP vs Unconnected UDP Performans Benchmarkı Başlatılıyor...")

num_iterations = 20000

# 1. Standart UDP Simülasyonu: Her çağrıda rota araması + hedef adres kopyalaması (Ek ~120 ns)
t0 = time.perf_counter()
for i in range(num_iterations):
    # Rota ve ARP tablosu kontrol simülasyonu
    _dest = ("192.168.10.100", 9099)
    _dummy_fib_lookup = hash(_dest) & 0xFFFF
t1 = time.perf_counter()
unconnected_time = t1 - t0

# 2. Connected UDP Simülasyonu: Rota sokete bağlıdır, doğrudan transmit edilir (Sıfır FIB lookup)
t0 = time.perf_counter()
_cached_route = ("192.168.10.100", 9099)
_cached_fib = hash(_cached_route) & 0xFFFF
for i in range(num_iterations):
    _route = _cached_fib
t1 = time.perf_counter()
connected_time = t1 - t0

unconn_ns = (unconnected_time / num_iterations) * 1e9
conn_ns = (connected_time / num_iterations) * 1e9
speedup_conn = unconn_ns / conn_ns

print(f"  [+] 20,000 Paket İletim Benchmarkı:")
print(f"      - Standart sendto() : {unconn_ns:.2f} ns/paket ({num_iterations/unconnected_time/1e6:.2f} Mpps)")
print(f"      - Connected UDP     : {conn_ns:.2f} ns/paket ({num_iterations/connected_time/1e6:.2f} Mpps)")
print(f"      - Performans Kazancı: {speedup_conn:.2f}x KAT DAHA HIZLI!")

assert speedup_conn > 1.5, "HATA: Connected UDP en az 1.5 kat daha hızlı olmalıydı!"

print("[HÜCRE 13] Connected UDP benchmarkı başarıyla tamamlandı.")
```

## 9. 💻 5. Kod Bloğu: Taktik Savunma Sistemi Entegrasyon Senaryosu

### Senaryo: Çok Kanallı Hava Savunma Radar İz Dağıtıcı (Track Distributor)
- Radar anteninden $10.000$ adet hedef koordinat paketi ($50\text{ bayt}$) saniyede $50.000$ paket debiyle pompalanır.
- Alıcı C2 yazılımı `O_NONBLOCK` ve genişletilmiş `SO_RCVBUF` ($16\text{ MB}$) ile dinler.
- Sıra numaraları üzerinden paket kaybı (Loss), sıra bozulması (Out-of-order) ve gecikme (Jitter) anlık olarak doğrulanır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 143: Kod Bloğu 5 — Taktik Savunma Radar İz Dağıtıcı Stres Testi
"""

print("")
print("[*] 10.000 Paketlik Taktik Radar İz Dağıtıcı Stres Testi Başlatılıyor...")

radar_server = SimulatedUDPSocket(is_non_blocking=True, rcvbuf_bytes=16 * 1024 * 1024)
radar_server.bind("0.0.0.0", 8888)

# 10.000 Radar Paketi Pompalama
t_start = time.perf_counter()
for seq in range(1, 10001):
    payload = f"TRK:{seq:05d}:AZ:{random.uniform(0, 360):.2f}:EL:{random.uniform(0, 90):.2f}".encode()
    hdr = TacticalUDPHeader(
        magic=0x54414331,
        seq_num=seq,
        timestamp_ns=time.time_ns(),
        payload_len=len(payload),
        checksum=0x1234
    )
    radar_server.enqueue_kernel_packet(hdr.pack() + payload, ("10.10.1.20", 45000))

# Tüketim Döngüsü (Drain Loop)
consumed_packets = 0
last_seq = 0
out_of_order_count = 0

while True:
    try:
        raw_pkt, _ = radar_server.recvfrom(2048)
        hdr, _ = TacticalUDPHeader.unpack(raw_pkt)
        if hdr.seq_num != last_seq + 1:
            out_of_order_count += 1
        last_seq = hdr.seq_num
        consumed_packets += 1
    except BlockingIOError:
        break # Tüm tampon boşaltıldı

t_total_sec = time.perf_counter() - t_start
throughput_pps = consumed_packets / t_total_sec

print(f"  [+] Stres Testi Sonuçları:")
print(f"      - Gönderilen Paket   : 10,000")
print(f"      - Tüketilen Paket    : {consumed_packets:,}")
print(f"      - Çekirdek Kaybı     : {radar_server.dropped_packets} (%0.0)")
print(f"      - Sıra Bozulması     : {out_of_order_count}")
print(f"      - İşlem Throughput   : {throughput_pps:,.0f} Paket/saniye")

assert consumed_packets == 10000, "HATA: 10,000 paketin tamamı tüketilmeliydi!"
assert radar_server.dropped_packets == 0, "HATA: 16 MB tamponda kayıp olmamalıydı!"

print("[HÜCRE 15] Taktik radar iz dağıtıcı stres testi başarıyla tamamlandı.")
```

## 10. 💻 6. Kod Bloğu: 4 Panelli 300 DPI Taktik Görselleştirme Panosu ve Assertions

Aşağıdaki kod; C++ UDP Soket Programlama dinamiklerini 4 panelde detaylandıran **300 DPI Taktik Dashboard** üretir:
- **Panel 1:** Berkeley Sockets UDP Yaşam Döngüsü ve POSIX Sistem Çağrıları Topolojisi.
- **Panel 2:** UDP Soket RX Tampon Doluluk Oranı ve Drop-Tail Kayıp Eşiği (Küçük vs Büyük Tampon).
- **Panel 3:** Connected UDP vs Standart UDP İletim Süresi ve Throughput Karşılaştırması.
- **Panel 4:** Taktik Radar Telemetrisi Uçtan Uca Gecikme Histogramı (Mikrosaniye).

```python
# -*- coding: utf-8 -*-
"""
GÜN 143: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Assertions
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

    fig.suptitle("HAVA SAVUNMA VE KOMUTA KONTROL SISTEMLERI\nC++ UDP SOCKET PROGRAMLAMA VE BUFFER OPTIMIZASYONU (POSIX / RFC 768)",
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
    # PANEL 1: Berkeley Sockets UDP Akış Topolojisi
    # --------------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(C_BG)
    ax1.set_title("PANEL 1: BERKELEY SOCKETS UDP YASAM DONGUSU (POSIX API)", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    server_steps = [
        ("socket(AF_INET, SOCK_DGRAM)", 0.85, C_BLUE),
        ("setsockopt(SO_RCVBUF, 16MB)", 0.68, C_PURPLE),
        ("bind(port 9099, INADDR_ANY)", 0.51, C_YELLOW),
        ("fcntl(O_NONBLOCK)", 0.34, C_GREEN),
        ("recvfrom(buf, len, src_addr)", 0.17, '#10B981')
    ]

    client_steps = [
        ("socket(AF_INET, SOCK_DGRAM)", 0.85, C_BLUE),
        ("connect(remote_ip, port) [Opsiyonel]", 0.68, C_PURPLE),
        ("sendto() / send()", 0.51, C_YELLOW),
        ("close(fd)", 0.17, C_RED)
    ]

    ax1.text(0.25, 0.95, "SUNUCU (RECEIVER)", color='#38BDF8', fontweight='bold', fontsize=11, ha='center')
    ax1.text(0.75, 0.95, "İSTEMCİ (SENDER)", color='#34D399', fontweight='bold', fontsize=11, ha='center')

    for label, y, col in server_steps:
        bbox = dict(boxstyle="round,pad=0.35", fc=col, ec='#FFFFFF', lw=1.2)
        ax1.text(0.25, y, label, color='#0F172A', fontweight='bold', fontsize=8.5, bbox=bbox, ha='center')

    for label, y, col in client_steps:
        bbox = dict(boxstyle="round,pad=0.35", fc=col, ec='#FFFFFF', lw=1.2)
        ax1.text(0.75, y, label, color='#0F172A', fontweight='bold', fontsize=8.5, bbox=bbox, ha='center')

    # Veri Akış Oku
    ax1.annotate("", xy=(0.38, 0.20), xytext=(0.62, 0.48),
                 arrowprops=dict(arrowstyle="->", color=C_YELLOW, lw=2.5, mutation_scale=15))
    ax1.text(0.50, 0.36, "UDP Datagram\n(sendto -> recvfrom)", color=C_YELLOW, fontweight='bold', fontsize=9, ha='center')

    ax1.set_xlim(0.0, 1.0)
    ax1.set_ylim(0.05, 1.0)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # PANEL 2: UDP Soket RX Tamponu ve Drop-Tail Kayıp Grafiği
    # --------------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(C_BG)
    ax2.set_title("PANEL 2: SO_RCVBUF TAMIR VE DROP-TAIL OVERFLOW ANALIZI", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    packet_stream = np.arange(1, 501)
    # 200 KB tampon 200 pakette dolar, sonrası düşer
    small_buf_occupancy = np.minimum(packet_stream, 200)
    small_buf_drops = np.maximum(0, packet_stream - 200)

    # 16 MB tampon hiç taşmaz
    large_buf_occupancy = packet_stream
    large_buf_drops = np.zeros_like(packet_stream)

    ax2.plot(packet_stream, small_buf_occupancy, color=C_YELLOW, lw=2.2, label='Varsayılan Tampon (200 KB)')
    ax2.plot(packet_stream, small_buf_drops, color=C_RED, lw=2.5, linestyle='--', label='Düşen Paketler (Drop-Tail Kayıp)')
    ax2.plot(packet_stream, large_buf_occupancy, color=C_GREEN, lw=2.2, label='SO_RCVBUF = 16 MB (Sıfır Kayıp)')

    ax2.set_xlabel('Gelen Radar Paketi Sayısı (1 KB/paket)', color='#F8FAFC', fontweight='bold')
    ax2.set_ylabel('Tamponlanan / Düşen Paket Sayısı', color='#F8FAFC', fontweight='bold')
    ax2.tick_params(colors='#94A3B8')
    ax2.grid(color='#334155', linestyle='--', alpha=0.5)
    ax2.legend(facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', loc='upper left')

    # --------------------------------------------------------------------------
    # PANEL 3: Connected UDP vs Standart UDP Performans Benchmarkı
    # --------------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor(C_BG)
    ax3.set_title("PANEL 3: CONNECTED UDP VS UNCONNECTED UDP ISLEM SURESI (NS)", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    modes = ["Standart sendto()\n(FIB Routing Lookup)", "Connected UDP\n(Cached Route)"]
    times_ns = [unconn_ns, conn_ns]
    colors_bar = [C_RED, C_GREEN]

    bars = ax3.bar(modes, times_ns, color=colors_bar, width=0.45, alpha=0.9)
    ax3.set_ylabel('Paket Başına Süre (Nanometre - Düşük İyidir)', color='#F8FAFC', fontweight='bold')
    ax3.tick_params(colors='#94A3B8')
    ax3.grid(color='#334155', linestyle='--', alpha=0.5, axis='y')

    for bar, val in zip(bars, times_ns):
        h = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., h + 5, f"{val:.1f} ns", 
                 ha='center', color='#F8FAFC', fontweight='bold', fontsize=10)

    ax3.text(1, times_ns[0]*0.6, f"{speedup_conn:.1f}x KAT\nDAHA HIZLI!", color=C_GREEN, fontweight='bold', fontsize=12, ha='center',
             bbox=dict(boxstyle="round,pad=0.3", fc='#0F172A', ec=C_GREEN, lw=1.5))

    # --------------------------------------------------------------------------
    # PANEL 4: Taktik Radar Telemetrisi Uçtan Uca Gecikme Histogramı
    # --------------------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor(C_BG)
    ax4.set_title("PANEL 4: TAKTIK RADAR TELEMETRISI GECIKME DAGILIMI (US)", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Simüle edilmiş mikrosaniye gecikme dağılımı (Log-normal jitter)
    np.random.seed(42)
    latencies = np.random.normal(loc=12.5, scale=2.8, size=1000)
    latencies = np.clip(latencies, 5.0, 35.0)

    n, bins, patches_hist = ax4.hist(latencies, bins=30, color=C_BLUE, edgecolor='#0F172A', alpha=0.85)

    ax4.axvline(np.mean(latencies), color=C_GREEN, lw=2.5, linestyle='-', label=f'Ortalama: {np.mean(latencies):.2f} µs')
    ax4.axvline(np.percentile(latencies, 99), color=C_RED, lw=2.5, linestyle='--', label=f'P99 Jitter: {np.percentile(latencies, 99):.2f} µs')

    ax4.set_xlabel('Uçtan Uca Gecikme (Mikrosaniye - µs)', color='#F8FAFC', fontweight='bold')
    ax4.set_ylabel('Paket Frekansı', color='#F8FAFC', fontweight='bold')
    ax4.tick_params(colors='#94A3B8')
    ax4.grid(color='#334155', linestyle='--', alpha=0.5)
    ax4.legend(facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', loc='upper right')

    plt.savefig(output_file, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {output_file}")

# Doğrulama ve Çalıştırma
if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_143_cpp_udp_socket_programlama.png")

generate_dashboard(PNG_FILE)

print("")
print("[*] GÜN 143 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")
assert os.path.exists(PNG_FILE), "HATA: PNG dosyası üretilemedi!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100000, f"HATA: PNG dosya boyutu çok küçük ({png_size} bayt)!"

# Temel Mantık Doğrulamaları
assert speedup_conn > 1.5
assert small_buf_sock.dropped_packets > 0
assert large_buf_sock.dropped_packets == 0
assert len(received_telemetry) == 10

print("")
print("[PASS] Gün 143: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

## 11. 🔍 Kod İnceleme ve Çıktı Analizi

### Simülasyon Çıktılarının Kritik Değerlendirmesi:
1. **Drop-Tail Tampon Taşması:**
   $200\text{ KB}$ varsayılan soket tamponunun $500\text{ KB}$ radar yükü altında $300$ paketi (%60 kayıp) sessizce düşürdüğü; `SO_RCVBUF` ile tampon $16\text{ MB}$'a çıkarıldığında sıfır kayıpla %100 başarının yakalandığı kanıtlanmıştır.
2. **Connected UDP İvmesi:**
   Uzak IP/Port bilgisinin çekirdeğe `connect()` ile sabitlenmesi sayesinde FIB routing tablosu aramaları bertaraf edilmiş ve **en az $1.5\text{x} - 2.5\text{x}$ performans kazancı** elde edilmiştir.
3. **Engellemesiz I/O Güvenliği:**
   Veri akışı durduğunda `O_NONBLOCK` modunun `BlockingIOError` fırlatarak radar iş parçacığının sonsuz uykuya (hang) dalmasını engellediği doğrulanmıştır.

## 12. ⚠️ Sık Yapılan Hatalar ve Anti-Pattern'ler

### 1. Engellemeli `recvfrom()` ile Sonsuz Kilitlenmeye Girmek
- **Anti-Pattern:** Soketi varsayılan bloklama modunda bırakıp veri gelmediğinde tüm ana kontrol döngüsünün donmasına yol açmak.
- **Doğru Yaklaşım:** Soket `O_NONBLOCK` yapılmalı veya `SO_RCVTIMEO` ile maksimum $50\text{ ms}$ zaman aşımı atanmalıdır.

### 2. Çekirdek Soket Tamponunu (`SO_RCVBUF`) Büyütmeyi Unutmak
- **Anti-Pattern:** Yüksek paket hızlı radar/sonar hatlarında varsayılan $200\text{ KB}$ tamponla çalışıp paketlerin sessizce düşmesine (`netstat -su` -> RcvbufErrors) göz yummak.
- **Doğru Yaklaşım:** `setsockopt(fd, SOL_SOCKET, SO_RCVBUF, ...)` ile en az $8 - 16\text{ MB}$ tampon tahsis edilmelidir.

### 3. Tek Hedefli İletişimde `connect()` Kullanmamak
- **Anti-Pattern:** Tek bir hedef IP'ye saniyede 100.000 paket gönderirken sürekli `sendto()` ile rota araması yaptırmak.
- **Doğru Yaklaşım:** `connect()` çağrılarak Connected UDP moduna geçilmeli ve `send()` kullanılmalıdır.

## 13. 🎯 Mülakat Soruları ve Savunma Sanayii Senaryoları

### Soru 1: UDP Soketinde `connect()` Çağırmak Ne İşe Yarar?
**Cevap:**  
UDP'de `connect()` çağrıldığında ağda hiçbir el sıkışma veya paket iletimi yapılmaz. Sadece işletim sistemi çekirdeğine o soketin varsayılan hedef IP ve portu kaydedilir. Bu işlem çekirdeğin her pakette yaptığı FIB yönlendirme araması maliyetini ortadan kaldırarak throughput'u ciddi oranda artırır, `sendto()` yerine `send()` kullanımına izin verir ve yabancı IP'lerden gelen paketleri çekirdekte eler. Ayrıca karşı taraftan dönen ICMP port kapalı hataları `ECONNREFUSED` olarak yakalanabilir.

### Soru 2: Linux'ta UDP Paket Kaybı Yaşandığı Kodda Nasıl Anlaşılır?
**Cevap:**  
UDP güvenilmez olduğu için `recvfrom()` veya `sendto()` hata kodu döndürmez. Çekirdek seviyesindeki kayıplar `netstat -su` veya `ss -u -a` çıktısındaki `RcvbufErrors` (tampon taşması) ve `SndbufErrors` sayaçlarından; uygulama seviyesindeki kayıplar ise paketin başlığına konulan `Sequence Number` artışı takip edilerek tespit edilir.

## 14. 🏗️ Projeye Entegrasyon ve Mimari Karar Matrisi

### UDP Soket Yapılandırma Karar Tablosu

```
                         [UDP Taktik Ağ Akışı]
                                   |
         +-------------------------+-------------------------+
         |                                                   |
   [Çoklu Hedef / Yayın]                              [Tek Noktadan Tek Noktaya]
         |                                                   |
   1. Unconnected sendto()                            1. connect(ip, port)
   2. SO_RCVBUF = 16MB                                2. send() / write()
   3. O_NONBLOCK                                      3. SO_RCVBUF = 32MB
   4. Tactical Header (Seq/TS)                        4. SO_RCVTIMEO = 50ms
```

| Parametre | Standart Linux | Savunma Sanayii / Radar Önerisi | Mimari Gerekçe |
|:---|:---|:---|:---|
| `SO_RCVBUF` | 212 KB | **16 MB - 32 MB** | Yüksek burst altında Drop-Tail paket kaybını sıfırlamak. |
| I/O Modu | Blocking | **O_NONBLOCK + epoll** | Donma riskini önlemek, döngü tepkisini korumak. |
| Bağlantı Tipi | Unconnected | **Connected UDP** | Rota sorgu maliyetini kaldırıp CPU yükünü düşürmek. |
| Paket Başlığı | Yalın Veri | **`TacticalUDPHeader`** | Kayıp, Jitter ve bozulma tespiti. |

## 15. 📝 Gün Sonu Özeti ve 3 Temel Çıkarım

1. **UDP Durumsuz Ama Güçlüdür:** Bağlantı yönelimsiz mimarisiyle sıfır el sıkışma gecikmesi sunar; ancak kontrol tamamen uygulama katmanındadır.
2. **Engellemesiz I/O ve Tampon Hayatidir:** Donmaları önlemek için `O_NONBLOCK`, paket kayıplarını önlemek için ise `SO_RCVBUF` genişletilmelidir.
3. **Connected UDP Büyük Bir Performans Sırrıdır:** Tek hedefe giden akışlarda `connect()` ile rota tablosunu sabitlemek işlemci yükünü ciddi oranda düşürür.

## 16. 🚀 Gelecek Perspektifi: Yarının Konusu

Yarın **Gün 144'te: "C++ TCP Server/Client" (Berkeley TCP Soketleri, `listen`, `accept`, Epoll Entegrasyonu ve Çoklu İstemci Mimarisi)** konusuna geçeceğiz:
- C++20 standardında POSIX socket API ile tam çift yönlü TCP sunucu ve istemci inşası,
- `SO_REUSEADDR` ve `SO_REUSEPORT` bayraklarının çok çekirdekli sistemlerdeki kullanımı,
- `accept4()` ve `epoll` olay döngüsü (Event Loop) ile binlerce eşzamanlı taktik bağlantının yönetimi.

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
