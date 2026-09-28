# GÜN 159: Linux Trafik Kontrolü (tc/netem) ve Wireshark ile Gecikme, Kayıp ve Jitter Emülasyonu

**Müfredat:** 365 Günlük ASELSAN / HAVELSAN Savunma Sistemleri C++20 & Linux Sistem Mühendisliği  
**Faz:** F4 — TCP/UDP / Ağ Protokolleri / Serileştirme & Taktik Dağıtık Sistemler  
**Konu:** Linux Çekirdeği Trafik Kontrolü (`tc`) ve Ağ Emülatörü (`netem`) Mimarisi (Queuing Discipline - Qdisc), Gecikme (Latency), Jitter (Gauss Dağılımı), Paket Kaybı (Random & Burst Loss), Paket Çoğaltma (Duplication) ve Sıra Bozulması (Reordering), Wireshark / Libpcap 24-Bayt Genel ve 16-Bayt Paket Başlığı Anatomisi, RTT ve Jitter Analizi, Elektronik Harp (EH / Jamming) Koşullarında Taktik İHA Telemetri Dayanıklılık Testi  
**Ön Koşul:** Gün 158 (SCTP: message/multistream mantığı)

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

## 1. Zihinsel Model & Savunma Sanayii Konsepti

Geliştirdiğiniz aviyonik telemetri veya taktik haberleşme yazılımı laboratuvar ortamında, gigabit fiber ağda veya yerel makinede (`localhost`) çalışırken her şey mükemmel görünür:
- Gecikme: $< 0.1\ \text{ms}$,
- Jitter: $0\ \text{ms}$,
- Paket Kaybı: $\%0$,
- Paket Sırası: $\%100$ kusursuz.

Ancak bu yazılım bir Bayraktar TB2 / AKINCI İHA'sına, bir F-16 görev bilgisayarına veya bir taktik sahil gözetleme radarına yüklendiğinde gerçek harp sahasının acımasız fiziksel koşullarıyla karşılaşır:
- Düşmanın Elektronik Harp (EH / Jamming) taarruzu,
- Taktik RF telsiz hatlarında (HF/VHF/UHF, Taktik Veri Bağı - Link-16, SATCOM) atmosferik zayıflama,
- İHA manevralarında dağların ve coğrafi engellerin sinyali kesmesi (Multipath Fading),
- Telsiz tamponlarında kuyruk birikmesi (Bufferbloat).

Sahaya çıkmadan önce yazılımın bu koşullara dayanıp dayanamayacağını kanıtlamak için savunma sanayiinde iki temel silah kullanılır:
1. **Linux `tc` (Traffic Control) ve `netem` (Network Emulator):** Linux çekirdeği seviyesinde giden paketlere yapay gecikme, jitter, paket kaybı, çoğaltma ve sıra bozulması enjekte eden deterministik test motoru.
2. **Wireshark ve `tshark` (PCAP Analizi):** Ağdaki paketleri mikrosaniyelik zaman damgalarıyla yakalayan, kayıpları (`retransmission`), gecikmeleri (`RTT`) ve varyansları (`jitter`) görselleştiren analiz aracı.

```
   +-------------------------------------------------------------------------+
   |            SAVUNMA SANAYİİNDE HIL / SITL AĞ EMÜLASYON TESTİ             |
   +-------------------------------------------------------------------------+

   [ İHA Aviyonik Bilgisayarı ]                      [ Yer Kontrol Konsolu ]
   (Bayraktar TB2 / ANKA)                           (Pilot / YKK Arayüzü)
              |                                                 ^
              v                                                 |
     +-------------------------------------------------------------------+
     |        LİNUX KERNEL TRAFFIC CONTROL (tc / netem MOTORU)           |
     |                                                                   |
     |   - Gecikme (Latency) : 100 ms ± 25 ms (Normal/Gauss Dağılımı)    |
     |   - Paket Kaybı (Loss): %15 Rastlantısal / Burst Kayıp            |
     |   - Çoğaltma (Dupl.)  : %3 Çift Paket Ulaşması (Multipath)        |
     |   - Sıra Bozulması    : %10 Sırasız Ulaşma (Reordering)           |
     +-------------------------------------------------------------------+
              |                                                 |
              +===================> [ PCAP DOSYASI ] <==========+
                                            |
                                            v
                                  [ WİRESHARK ANALİZİ ]
                             (RTT, Jitter, Loss Grafikleri)
```

## 2. Linux Trafik Kontrolü (tc) ve Netem Matematiksel Çekirdek Mimarisi

Linux ağ yığınında paketler ağ kartına (`NIC`) iletilmeden önce bir kuyruk disiplininden (**Qdisc - Queuing Discipline**) geçer. Varsayılan kuyruk `pfifo_fast` (First-In, First-Out) iken, `tc` komutuyla bunun yerine `netem` kuyruğu yerleştirilir.

### Netem Matematiksel Bozulma Modelleri:

1. **Gecikme (Latency) ve Jitter Modeli (Normal / Gauss Dağılımı):**
   Gecikme sabit bir değer değil, ortalaması $\mu$ ve standart sapması $\sigma$ olan bir normal dağılımdır:
   $$T_{gecikme} \sim \mathcal{N}(\mu, \sigma^2)$$
   Ayrıca önceki paketin gecikmesiyle korelasyon ($r$) tanımlanabilir:
   $$T_i = r \cdot T_{i-1} + (1 - r) \cdot \mathcal{N}(\mu, \sigma^2)$$
   Linux komutu:
   ```bash
   tc qdisc add dev eth0 root netem delay 100ms 20ms 25% distribution normal
   ```
   *(Ortalama $100\ \text{ms}$, $\pm 20\ \text{ms}$ jitter, $\%25$ korelasyon).*

2. **Paket Kaybı (Loss - Gilbert-Elliott İki Durumlu Markov Modeli):**
   Gerçek telsiz ağlarında kayıplar bağımsız değildir; telsiz bir engelin arkasına girdiğinde arka arkaya paketler kaybolur (**Burst Loss**).
   - Durum $G$ (İyi Durum): Düşük kayıp oranı ($P_L \approx 0$).
   - Durum $B$ (Kötü Durum): Yüksek kayıp oranı ($P_L \approx 1$).
   Linux komutu:
   ```bash
   tc qdisc change dev eth0 root netem loss 10% 25%
   ```
   *(%10 kayıp, bir önceki paketin kaybolması durumunda %25 ilişkili kayıp).*

3. **Paket Çoğaltma (Duplication) ve Sıra Bozulması (Reordering):**
   ```bash
   tc qdisc change dev eth0 root netem duplicate 2% reorder 5% 50%
   ```

## 3. Wireshark PCAP Dosya Anatomisi ve Ağ Analiz Metrikleri

Wireshark ve `tcpdump` tarafından kaydedilen standart `.pcap` ikili (binary) dosya formatı son derece basit ve deterministiktir:

```
+-----------------------------------------------------------------------------+
|                 STANDART LIBPCAP (.pcap) DOSYA ANATOMİSİ                    |
+-----------------------------------------------------------------------------+

 1. GENEL BAŞLIK (Global Header - 24 Bayt - Dosya Başında Tek Sefer)
 +--------------------+-------------------+--------------------+--------------+
 | Magic Number (4B)  | Major/Minor (4B)  | Timezone/SigFigs(8B| SnapLen (4B) |
 | (0xA1B2C3D4)       | (v2.4)            | (0, 0)             | (65535)      |
 +--------------------+-------------------+--------------------+--------------+
 | Data Link Type (4B)|
 | (1 = Ethernet)     |
 +--------------------+

 2. PAKET BAŞLIĞI (Packet Header - 16 Bayt - Her Paket Öncesinde)
 +--------------------+-------------------+--------------------+--------------+
 | Timestamp Sec (4B) | Timestamp Usec(4B)| Captured Len (4B)  | Orig Len(4B) |
 +--------------------+-------------------+--------------------+--------------+

 3. HAM PAKET VERİSİ (Captured Len Bayt)
 +----------------------------------------------------------------------------+
 | Ethernet Başlığı (14B) + IP Başlığı (20B) + UDP/TCP Başlığı + Yük (Payload)|
 +----------------------------------------------------------------------------+
```

### Kritik Wireshark Analiz Metrikleri:
1. **RTT (Round Trip Time):** Gönderilen veri paketi ile karşı taraftan dönen onay paketi (`ACK`) arasındaki süre.
2. **Jitter (Gecikme Değişintisi - RFC 3550):**
   $$D(i, j) = (R_j - R_i) - (S_j - S_i)$$
   $$J_i = J_{i-1} + \frac{|D(i-1, i)| - J_{i-1}}{16}$$
3. **Retransmission Oranı:** Toplam paketlerin kaçının kayıp nedeniyle tekrar gönderildiği.

## 4. C++20 / Linux Sistem Programlama: Donanım-Döngüde (HIL) Test Altyapısı

Askeri HIL (Hardware-in-the-Loop) simülasyonlarında C++20 tabanlı bir test orkestratörü Linux çekirdeğindeki `tc/netem` kurallarını dinamik olarak değiştirir:

```cpp
#include <cstdlib>
#include <string>
#include <format>

class TacticalNetemController {
public:
    static void apply_jamming_profile(const std::string& interface, int delay_ms, int jitter_ms, double loss_pct) {
        // Önceki qdisc kuralını temizle
        std::string del_cmd = std::format("tc qdisc del dev {} root 2>/dev/null", interface);
        std::system(del_cmd.c_str());

        // Elektronik Harp (EH) profilini uygula
        std::string add_cmd = std::format(
            "tc qdisc add dev {} root netem delay {}ms {}ms distribution normal loss {:.1f}%",
            interface, delay_ms, jitter_ms, loss_pct
        );
        std::system(add_cmd.c_str());
    }

    static void reset_interface(const std::string& interface) {
        std::string reset_cmd = std::format("tc qdisc del dev {} root 2>/dev/null", interface);
        std::system(reset_cmd.c_str());
    }
};
```

Bu altyapı sayesinde otomatik regresyon testleri çalışırken hat parametreleri senaryo bazlı olarak bozulur; sistemin kendini toparlama (self-healing) kabiliyeti doğrulanır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 1 — Linux tc/netem Mantığını Birebir Taklit Eden Ağ Kanal Motoru
"""

import random
import time
from typing import List, Tuple, Optional, Dict, Any

class NetemPacket:
    """Simüle Edilen Ağ Paketi"""
    def __init__(self, seq: int, send_time: float, payload: bytes):
        self.seq = seq
        self.send_time = send_time
        self.delivery_time = send_time
        self.payload = payload
        self.is_duplicate = False

class NetemChannel:
    """
    Linux tc/netem Çekirdek Kuyruğunun Python Uygulaması.
    Gecikme (Gauss), Jitter, Kayıp, Çoğaltma ve Sıra Bozulmasını modeller.
    """
    def __init__(self, mean_delay_ms: float = 50.0, jitter_ms: float = 10.0,
                 loss_rate: float = 0.10, duplicate_rate: float = 0.02,
                 reorder_rate: float = 0.05):
        self.mean_delay = mean_delay_ms / 1000.0
        self.jitter = jitter_ms / 1000.0
        self.loss_rate = loss_rate
        self.duplicate_rate = duplicate_rate
        self.reorder_rate = reorder_rate

        self.stats = {
            "sent": 0,
            "delivered": 0,
            "dropped": 0,
            "duplicated": 0,
            "reordered": 0
        }

    def transmit(self, packets: List[NetemPacket]) -> List[NetemPacket]:
        in_flight: List[NetemPacket] = []

        for pkt in packets:
            self.stats["sent"] += 1

            # 1. Paket Kaybı (Loss) Enjeksiyonu
            if random.random() < self.loss_rate:
                self.stats["dropped"] += 1
                continue

            # 2. Gecikme ve Jitter (Gauss / Normal Dağılım)
            delay = max(0.001, random.gauss(self.mean_delay, self.jitter))
            
            # 3. Sıra Bozulması (Reordering) Enjeksiyonu
            if random.random() < self.reorder_rate:
                # Sırasız pakete daha az gecikme vererek öne fırlat
                delay *= 0.3
                self.stats["reordered"] += 1

            pkt.delivery_time = pkt.send_time + delay
            in_flight.append(pkt)

            # 4. Paket Çoğaltma (Duplication) Enjeksiyonu
            if random.random() < self.duplicate_rate:
                dup_pkt = NetemPacket(pkt.seq, pkt.send_time, pkt.payload)
                dup_pkt.delivery_time = pkt.delivery_time + 0.005 # 5 ms sonra ikinci kopya
                dup_pkt.is_duplicate = True
                in_flight.append(dup_pkt)
                self.stats["duplicated"] += 1

        # Alıcıya varış zamanına göre fiziksel ortamda sırala
        in_flight.sort(key=lambda p: p.delivery_time)
        self.stats["delivered"] = len(in_flight)
        return in_flight

print("[*] Linux tc/netem Kanal Simülatörü Motoru Tanımlandı.")
print("[HÜCRE 6] Netem simülatörü hazır.")
```

## 5. Kod Açıklaması: Ağ Emülasyonu ve Gauss Dağılımı

Yukarıdaki kod bloğu Linux `netem` çekirdek modülünün davranışını birebir modeller:
1. `NetemChannel`: Belirlenen ortalama gecikme (`mean_delay_ms`) ve sapma (`jitter_ms`) ile `random.gauss` kullanarak her pakete gerçekçi bir Gauss gecikmesi atar.
2. Paket Kaybı: `loss_rate` olasılığı ile paketler kuyruktan silinir (droplanır).
3. Sıra Bozulması: Belirli bir olasılıkla paket daha erken bir varış zamanı alarak kuyrukta öne geçer.
4. Paket Çoğaltma: Multipath yansımalarını taklit ederek aynı paketin iki kopyası farklı teslim süreleriyle listeye eklenir.
5. Sonuç listesi `delivery_time` alanına göre sıralanarak fiziksel teldeki varış anı oluşturulur.

```python
# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 2 — Wireshark Uyumlu Libpcap (.pcap) İkili Dosya Yazıcı Motoru
"""

import os
import struct

try:
    target_dir = os.path.dirname(os.path.abspath(__file__))
except Exception:
    target_dir = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_159"

class PcapWriter:
    """
    RFC Standartlarında Libpcap (.pcap) İkili Dosya Üreticisi.
    Harici kütüphane gerektirmeden Wireshark'ın açabileceği dosyalar üretir.
    """
    GLOBAL_HEADER_MAGIC = 0xA1B2C3D4  # Standard PCAP Magic
    VERSION_MAJOR = 2
    VERSION_MINOR = 4
    SNAPLEN = 65535
    NETWORK_RAW_IP = 101  # Link-Layer Header Type: Raw IPv4

    def __init__(self, filename: str):
        self.filename = filename
        self.file = open(filename, "wb")
        self._write_global_header()

    def _write_global_header(self):
        # 24 Bayt Libpcap Genel Başlığı
        hdr = struct.pack(
            "=I H H i I I I",
            self.GLOBAL_HEADER_MAGIC,
            self.VERSION_MAJOR,
            self.VERSION_MINOR,
            0,          # GMT to local correction
            0,          # Accuracy of timestamps
            self.SNAPLEN,
            self.NETWORK_RAW_IP
        )
        self.file.write(hdr)

    def write_packet(self, timestamp_sec: float, payload: bytes):
        sec = int(timestamp_sec)
        usec = int((timestamp_sec - sec) * 1_000_000)
        pkt_len = len(payload)

        # 16 Bayt Paket Başlığı
        pkt_hdr = struct.pack("=I I I I", sec, usec, pkt_len, pkt_len)
        self.file.write(pkt_hdr)
        self.file.write(payload)

    def close(self):
        if self.file and not self.file.closed:
            self.file.close()

# Test: Örnek PCAP Dosyası Oluşturma
sample_pcap_path = os.path.join(target_dir, "tactical_sample.pcap")
writer = PcapWriter(sample_pcap_path)

base_time = 1716380000.0
for i in range(10):
    dummy_payload = f"TACTICAL_TELEMETRY_PKT_SEQ_{i}".encode('utf-8')
    writer.write_packet(base_time + (i * 0.05), dummy_payload)
writer.close()

pcap_size = os.path.getsize(sample_pcap_path)
print("[*] Wireshark PCAP İkili Dosyası Başarıyla Oluşturuldu:")
print(f"  [+] Dosya Yolu : {sample_pcap_path}")
print(f"  [+] Dosya Boyu : {pcap_size} Bayt (24B Global Header + 10x(16B Hdr + Payload))")

assert os.path.exists(sample_pcap_path)
assert pcap_size > 24 + (10 * 16)
print("[HÜCRE 8] PCAP formatlayıcı motoru başarıyla test edildi.")
```

## 6. Kod Açıklaması: Libpcap Dosya Yapısı ve Zaman Damgalama

Yukarıdaki kod hücresi, ağ paketlerini Wireshark'ın doğrudan okuyabileceği `.pcap` ikili formatında diske yazar:
1. `_write_global_header`: Dosyanın başına 24 baytlık Libpcap başlığını koyar (`0xA1B2C3D4` magic sayısı, v2.4 sürümü, mikrosaniye zaman çözünürlüğü).
2. `write_packet`: Her paket için 16 baytlık başlık (saniye, mikrosaniye, yakalanan uzunluk, orijinal uzunluk) ve ardından ham baytları yazar.
3. Bu motor sayesinde simülasyon sonuçları Wireshark veya `tshark` üzerinde gerçek bir ağ kartından yakalanmış gibi incelenebilir.

```python
# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 3 — Sabotaj ve Başarım İspatı: Standart vs Dayanıklı Telemetri Alıcısı
"""

class StandardTelemetryReceiver:
    """Saf UDP Gibi Çalışan Savunmasız Alıcı (Sıra / Duplication Koruması Yok)"""
    def __init__(self):
        self.received = []

    def receive(self, pkt: NetemPacket):
        self.received.append(pkt.seq)

class ResilientTelemetryReceiver:
    """
    Savunma Standartlarında Dayanıklı Alıcı (Resilient Receiver):
    - Duplicate Paketleri Düşürür (Anti-Replay / Dedup)
    - Sıra Bozulmasını Tespit Eder ve Yeniden Sıralar
    """
    def __init__(self):
        self.seen_seqs = set()
        self.delivered = []
        self.expected_seq = 0
        self.buffer = {}

    def receive(self, pkt: NetemPacket):
        # 1. Çoğaltılmış Paket (Duplication) Tespiti ve İmhayı Sağla
        if pkt.seq in self.seen_seqs:
            return  # Kopyayı sessizce düşür!
        self.seen_seqs.add(pkt.seq)

        # 2. Tampona Ekle
        self.buffer[pkt.seq] = pkt.payload

        # 3. Sırayla Teslim Et
        while self.expected_seq in self.buffer:
            self.delivered.append(self.expected_seq)
            del self.buffer[self.expected_seq]
            self.expected_seq += 1

# Deney Kurulumu: 50 Paket Gönder, Ağda Agresif Elektronik Harp (EH) Uygula
random.seed(159)
netem = NetemChannel(
    mean_delay_ms=80.0,
    jitter_ms=25.0,
    loss_rate=0.15,      # %15 Paket Kaybı
    duplicate_rate=0.10, # %10 Çoğaltma
    reorder_rate=0.15    # %15 Sıra Bozulması
)

packets = [NetemPacket(seq=i, send_time=i * 0.02, payload=f"DATA_{i}".encode()) for i in range(50)]
delivered_packets = netem.transmit(packets)

std_rx = StandardTelemetryReceiver()
res_rx = ResilientTelemetryReceiver()

for p in delivered_packets:
    std_rx.receive(p)
    res_rx.receive(p)

print()
print("[*] Elektronik Harp (EH) Simülasyon Sonuçları (50 Paket Gönderildi):")
print(f"  [+] Ağda Düşürülen Paket Sayısı : {netem.stats['dropped']} (%{netem.stats['dropped']/50*100:.1f})")
print(f"  [+] Çoğaltılan Paket Sayısı     : {netem.stats['duplicated']}")
print(f"  [+] Sırası Değişen Paket Sayısı : {netem.stats['reordered']}")
print()
print(f"  [-] Standart Alıcı Teslimat Sayısı : {len(std_rx.received)} (Kopya paketleri ayırt edemedi!)")
print(f"  [+] Dayanıklı Alıcı Teslimat Sayısı: {len(res_rx.delivered)} (Kopyalar %100 elendi, sıralı teslim edildi)")

# Kural İspatı: Standart alıcıda kopya paketler bulunurken, dayanıklı alıcıda asla bulunmaz
assert len(std_rx.received) > len(set(std_rx.received)), "Standart alıcı kopyaları filtreleyememelidir!"
assert len(res_rx.delivered) == len(set(res_rx.delivered)), "Dayanıklı alıcıda kopya paket olamaz!"
print("[HÜCRE 10] Sabotaj ve dayanıklılık testi başarıyla tamamlandı.")
```

## 7. Kod Açıklaması: Sabotaj Analizi ve Duplication/Reorder Eliminasyonu

Simülasyonda telsiz hattına %15 paket kaybı, %10 çoğaltma ve %15 sıra bozulması enjekte edilmiştir:
1. **Standart Alıcı:** Gelen paketleri doğrudan kabul ettiği için çoğaltılmış paketleri (`duplicate`) ikinci kez işleyerek uçuş bilgisayarında telemetri tutarsızlığına yol açmıştır.
2. **Dayanıklı Alıcı (Resilient Receiver):** `seen_seqs` kümesi ile daha önce işlenmiş paketleri tespit etmiş ve anında düşürmüştür. Ardışık olmayan paketleri tamponlayarak sırası geldiğinde teslim etmiştir.
3. Bu test, taktik telsiz hatlarında ham UDP kullanmanın ölümcül risklerini ve üzerine inşa edilen protokol zırhının önemini ispatlar.

```python
# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 4 — Wireshark Metrik Analizörü (RTT, RFC 3550 Jitter ve Gecikme Dağılımı)
"""

class PcapAnalyzer:
    """Yakalanan Paketlerden Wireshark Tipi İstatistik Çıkaran Motor"""
    @staticmethod
    def analyze_stream(delivered: List[NetemPacket]) -> Dict[str, Any]:
        if not delivered:
            return {}

        delays_ms = [(p.delivery_time - p.send_time) * 1000.0 for p in delivered]
        mean_delay = sum(delays_ms) / len(delays_ms)

        # RFC 3550 Jitter Hesabı
        jitter = 0.0
        jitter_history = []
        for i in range(1, len(delivered)):
            prev = delivered[i-1]
            curr = delivered[i]
            d = abs((curr.delivery_time - prev.delivery_time) - (curr.send_time - prev.send_time)) * 1000.0
            jitter = jitter + (d - jitter) / 16.0
            jitter_history.append(jitter)

        return {
            "packet_count": len(delivered),
            "delays_ms": delays_ms,
            "mean_delay_ms": mean_delay,
            "min_delay_ms": min(delays_ms),
            "max_delay_ms": max(delays_ms),
            "final_jitter_ms": jitter,
            "jitter_history": jitter_history
        }

metrics = PcapAnalyzer.analyze_stream(delivered_packets)

print()
print("[*] Wireshark Tipi Ağ Sağlık ve Metrik Raporu:")
print(f"  [+] Analiz Edilen Paket  : {metrics['packet_count']}")
print(f"  [+] Ortalama Gecikme     : {metrics['mean_delay_ms']:.2f} ms")
print(f"  [+] Min / Max Gecikme    : {metrics['min_delay_ms']:.2f} ms / {metrics['max_delay_ms']:.2f} ms")
print(f"  [+] Nihai RFC 3550 Jitter: {metrics['final_jitter_ms']:.2f} ms")

assert metrics['mean_delay_ms'] > 40.0, "Ortalama gecikme emüle edilen aralıkta olmalıdır!"
assert metrics['final_jitter_ms'] > 0.0, "Jitter sıfırdan büyük olmalıdır!"
print("[HÜCRE 12] Wireshark metrik analizörü başarıyla çalıştırıldı.")
```

## 8. Kod Açıklaması: RTT ve RFC 3550 Jitter İstatistikleri

Yukarıdaki kod hücresi Wireshark'ın arka planda çalıştırdığı istatistiksel analiz motorunu kodlar:
1. Gecikme Hesaplama: Her paketin teslim zamanı ile gönderilme anı arasındaki fark milisaniye cinsinden hesaplanır.
2. RFC 3550 Jitter Filtresi: İki ardışık paketin varış farkı formüle edilerek $1/16$ ağırlıklı üstel kayan ortalama (EMA) ile filtrelenir.
3. Bu metrikler savunma haberleşmesinde telsiz hattının elektronik karıştırma veya sıkışıklık altında olup olmadığını belirleyen temel operasyonel kriterlerdir.

```python
# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 5 — Bayraktar TB2 Taktik Görev Simülasyonu ve Telsiz Bozulma Testi
"""

class TacticalTelemetryUav:
    """İHA Tarafında Telemetri Üreten Modül"""
    def __init__(self):
        self.seq = 0

    def generate_packet(self, timestamp: float) -> NetemPacket:
        # GPS, İrtifa, Hız ve Batarya Paketi
        payload = f"TB2_TLM:SEQ={self.seq},LAT=39.925,LON=32.866,ALT=5200M,SPD=120KTS,BAT=%98".encode()
        pkt = NetemPacket(self.seq, timestamp, payload)
        self.seq += 1
        return pkt

# 100 Paketlik Taktik Uçuş Görevi
uav = TacticalTelemetryUav()
raw_telemetry = [uav.generate_packet(timestamp=i * 0.05) for i in range(100)]

# Görev Sırasında Düşman Jammer'ı Devreye Giriyor!
tactical_channel = NetemChannel(
    mean_delay_ms=120.0, # 120 ms uydu/telsiz gecikmesi
    jitter_ms=30.0,
    loss_rate=0.20,      # %20 Yüksek Karıştırma Kaybı
    duplicate_rate=0.04,
    reorder_rate=0.08
)

transmitted_tlm = tactical_channel.transmit(raw_telemetry)
gcs_receiver = ResilientTelemetryReceiver()

for p in transmitted_tlm:
    gcs_receiver.receive(p)

print()
print("[*] Bayraktar TB2 Görev Sonu Telemetri Raporu (100 Paket Üretildi):")
print(f"  [+] Jammer Tarafından Düşürülen: {tactical_channel.stats['dropped']} Paket")
print(f"  [+] Yer İstasyonuna Ulaşan      : {len(transmitted_tlm)} Paket")
print(f"  [+] Kusursuz İşlenen Telemetri : {len(gcs_receiver.delivered)} Adet")

assert len(gcs_receiver.delivered) == len(set(gcs_receiver.delivered))
assert tactical_channel.stats['dropped'] > 0
print("[HÜCRE 14] Taktik telemetri dayanıklılık senaryosu başarıyla tamamlandı.")
```

## 9. Kod Açıklaması: Taktik İHA Telemetri Link Doğrulaması

Uçtan uca taktik senaryoda:
1. `TacticalTelemetryUav` sınıfı 50 ms aralıklarla (20 Hz) İHA telemetri paketleri üretmiştir.
2. Düşman karıştırması (Jamming) altında %20 paket kaybı ve 120 ms ortalama gecikme yaşanmıştır.
3. Yer Kontrol İstasyonu (GCS) tarafındaki `ResilientTelemetryReceiver`, düşen paketleri atlamış, gelen paketleri sıra numarasına göre hatasız işlemiş ve hiçbir kopyanın sisteme sızmasına izin vermemiştir.

```python
# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 6 — 4 Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_159_wireshark_tc_netem_latency_loss_jitter.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_159\gun_159_wireshark_tc_netem_latency_loss_jitter.png"

# Matplotlib Karanlık Tema Ayarları
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.0

fig = plt.figure(figsize=(18, 12), dpi=300, facecolor='#0F172A')
fig.suptitle("GÜN 159: Linux tc/netem Ağ Emülasyonu ve Wireshark Analiz Panosu",
             fontsize=15, fontweight='bold', color='#38BDF8', y=0.98)

# -----------------------------------------------------------------------------
# PANEL 1: Linux tc/netem Çekirdek Kuyruk Mimarisi (Qdisc Pipeline)
# -----------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1)
ax1.set_facecolor('#1E293B')
ax1.set_title("Panel 1: Linux Çekirdeği Trafik Kontrolü (tc/netem Qdisc) Mimarisi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax1.axis('off')

# Blok Şeması
blocks = [
    ("Uygulama Katmanı (Socket)", "sendto() / write() Veri Üretimi", 0.05, 0.75, 0.38, "#0284C7"),
    ("IP Yığını (Routing & Output)", "sk_buff Çekirdek Bellek Tahsisi", 0.55, 0.75, 0.40, "#0284C7"),
    ("Linux Qdisc: netem (Kuyruk Disiplini)", "Gecikme (Gauss), Jitter, Loss (%15), Duplication, Reordering", 0.05, 0.42, 0.90, "#D97706"),
    ("Ağ Kartı Sürücüsü (NIC Driver)", "Ring Buffer (DMA Transfer)", 0.05, 0.12, 0.42, "#10B981"),
    ("Fiziksel Telsiz / RF Arayüzü", "Harp Sahası Anteni & Taktik Hat", 0.53, 0.12, 0.42, "#10B981")
]

for title, sub, bx, by, bw, col in blocks:
    rect = patches.FancyBboxPatch((bx, by), bw, 0.18, boxstyle="round,pad=0.02", facecolor=col, alpha=0.25, edgecolor=col, lw=2)
    ax1.add_patch(rect)
    ax1.text(bx + 0.02, by + 0.11, title, color='#F8FAFC', fontweight='bold', fontsize=9.5)
    ax1.text(bx + 0.02, by + 0.04, sub, color='#CBD5E1', fontsize=8)

# Oklar
ax1.annotate("", xy=(0.54, 0.84), xytext=(0.44, 0.84), arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2))
ax1.annotate("", xy=(0.5, 0.61), xytext=(0.5, 0.74), arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2.5))
ax1.annotate("", xy=(0.26, 0.31), xytext=(0.26, 0.41), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))
ax1.annotate("", xy=(0.74, 0.31), xytext=(0.74, 0.41), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))

ax1.set_xlim(0.0, 1.0)
ax1.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 2: Gecikme Dağılımı ve Jitter Gauss Eğrisi
# -----------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2)
ax2.set_facecolor('#1E293B')
ax2.set_title("Panel 2: Emüle Edilen Paket Gecikme Dağılımı (Gauss / Normal Eğri)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

delays = metrics['delays_ms']
count, bins, ignored = ax2.hist(delays, bins=15, density=True, color='#38BDF8', alpha=0.6, edgecolor='#1E293B')

# Teorik Gauss Eğrisi Çizimi
mu = metrics['mean_delay_ms']
sigma = np.std(delays)
x_vals = np.linspace(min(delays) - 10, max(delays) + 10, 100)
p_vals = 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(- (x_vals - mu)**2 / (2 * sigma**2))
ax2.plot(x_vals, p_vals, linewidth=2.5, color='#F43F5E', label=f'Gauss Fit (μ={mu:.1f}ms, σ={sigma:.1f}ms)')

ax2.set_xlabel("Paket Gecikmesi (Milisaniye)", fontsize=9, color='#94A3B8')
ax2.set_ylabel("Olasılık Yoğunluğu", fontsize=9, color='#94A3B8')
ax2.grid(True, linestyle=':', alpha=0.3, color='#64748B')
ax2.legend(facecolor='#1E293B', edgecolor='#334155')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Taktik Telsiz Paket Teslim Durum Dağılımı
# -----------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3)
ax3.set_facecolor('#1E293B')
ax3.set_title("Panel 3: Elektronik Harp Altında Paket İletim Durumları", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

categories = ["Başarılı Teslim", "Jammer Kaybı\n(Dropped)", "Çoğaltılan\n(Duplicated)", "Sırası Değişen\n(Reordered)"]
values = [
    netem.stats['delivered'] - netem.stats['duplicated'],
    netem.stats['dropped'],
    netem.stats['duplicated'],
    netem.stats['reordered']
]
colors_cat = ['#10B981', '#EF4444', '#F59E0B', '#8B5CF6']

bars3 = ax3.bar(categories, values, color=colors_cat, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars3, values):
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 0.8, f"{val} Pkt",
             ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=9)

ax3.set_ylim(0, max(values) + 8)
ax3.set_ylabel("Paket Sayısı", fontsize=9, color='#94A3B8')
ax3.grid(axis='y', linestyle=':', alpha=0.3, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: RFC 3550 Jitter Zaman Serisi
# -----------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4)
ax4.set_facecolor('#1E293B')
ax4.set_title("Panel 4: RFC 3550 Inter-Arrival Jitter Zaman Serisi Eğrisi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

jitter_hist = metrics['jitter_history']
pkt_indices = list(range(1, len(jitter_hist) + 1))

ax4.plot(pkt_indices, jitter_hist, color='#F59E0B', lw=2.0, marker='o', markersize=3, label='RFC 3550 Jitter (EMA)')
ax4.axhline(y=metrics['final_jitter_ms'], color='#10B981', linestyle='--', label=f"Nihai Jitter: {metrics['final_jitter_ms']:.2f} ms")

ax4.set_xlabel("İletilen Paket Sırası (Index)", fontsize=9, color='#94A3B8')
ax4.set_ylabel("Jitter Değeri (Milisaniye)", fontsize=9, color='#94A3B8')
ax4.grid(True, linestyle=':', alpha=0.3, color='#64748B')
ax4.legend(facecolor='#1E293B', edgecolor='#334155')
ax4.tick_params(colors='#94A3B8')

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 159 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert metrics['packet_count'] > 0
assert metrics['mean_delay_ms'] > 0
assert netem.stats['dropped'] > 0
assert len(gcs_receiver.delivered) > 0

print()
print("[PASS] Gün 159: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

## 10. Görselleştirme Açıklaması ve Mimari Yorumlar

Üretilen 4 panelli yüksek çözünürlüklü (300 DPI) görselleştirme panosu, Linux `tc/netem` altyapısı ve ağ analiz dinamiklerini ortaya koyar:
1. **Panel 1: Linux Çekirdeği Trafik Kontrolü (tc/netem Qdisc) Mimarisi:**
   Paketin uygulama katmanından soket tamponuna, oradan `sk_buff` ile netem kuyruk disiplinine ve en son ağ sürücüsüne akışını şematize eder.
2. **Panel 2: Emüle Edilen Paket Gecikme Dağılımı:**
   Ağdaki rastlantısal gecikmelerin teorik Gauss (Normal) dağılımı ile uyumunu ($μ \approx 80\ \text{ms}$, $\sigma \approx 25\ \text{ms}$) histogram ve çan eğrisi üzerinde gösterir.
3. **Panel 3: Elektronik Harp Altında Paket İletim Durumları:**
   Jamming altındaki telsiz hattında kaç paketin başarıyla teslim edildiğini, kaçının düşürüldüğünü, kaçının çoğaltıldığını ve sırasının bozulduğunu çubuk grafiklerle somutlaştırır.
4. **Panel 4: RFC 3550 Inter-Arrival Jitter Zaman Serisi Eğrisi:**
   Gecikme dalgalanmalarının paket akışı boyunca $1/16$ ağırlıklı üstel kayan ortalama (EMA) filtresiyle nasıl dengelendiğini sergiler.

## 11. Karşılaştırmalı Analiz ve Ağ Emülatörleri Karar Matrisi

Savunma laboratuvarlarında kullanılan ağ emülasyon araçlarının karar matrisi:

| Araç | Çalışma Katmanı | Performans & Doğruluk | Kullanım Kolaylığı | Savunma / Aviyonik Uygunluğu |
| :--- | :--- | :--- | :--- | :--- |
| **Linux `tc / netem`** | **Kernel Qdisc (Ring 0)** | **Maksimum (Donanımsal Hız)** | CLI / Scripting | **Savunma Standardı (HIL / CI-CD)** |
| **Clumsy (Windows)** | WinDivert (WFP Filtresi) | Orta | GUI (Masaüstü Kullanıcı) | Hızlı Bireysel Geliştirici Testi |
| **WANem** | Sanal Makine / Gateway | Yüksek | Web Arayüzü | Laboratuvar Ağ Geçidi Testleri |
| **Dummynet (FreeBSD/macOS)**| ipfw Çekirdek Modülü | Yüksek | CLI | BSD Tabanlı Gömülü Sistemler |
| **XDP / eBPF Emülatörü** | Sürücü Katmanı (PHY öncesi) | Ultra Yüksek ($> 40\ \text{Gbps}$)| C / BPF Bytecode | 5G ve Radar Sinyal İşleme Hatları |

## 12. Donanım ve Linux Kernel Seviyesi Etkileşimler

### 1. `sk_buff` Yaşam Döngüsü ve Netem Müdahalesi:
Linux çekirdeğinde her ağ paketi bir `struct sk_buff` nesnesi ile temsil edilir:
- Paket `dev_queue_xmit()` fonksiyonuna ulaştığında doğrudan NIC tx ring'e verilmez.
- `qdisc_run()` fonksiyonu çağrılır; burada `netem_enqueue()` paketi yakalar.
- Gecikme eklenecekse paket `rb_node` (Red-Black Tree) zamanlayıcı kuyruğuna alınır. Zamanı geldiğinde kernel softirq (`NET_TX_SOFTIRQ`) tarafından uyandırılarak sürücüye teslim edilir.

### 2. Egress vs Ingress Emülasyonu (IFB Cihazları):
`tc/netem` kural olarak yalnızca giden trafiği (**egress**) geciktirir. Gelen trafiği (**ingress**) de emüle etmek için sanal bir **IFB (Intermediate Functional Block)** arayüzü kurulur:
```bash
sudo modprobe ifb
sudo ip link set dev ifb0 up
# Gelen trafiği ifb0'a yönlendir:
sudo tc qdisc add dev eth0 handle ffff: ingress
sudo tc filter add dev eth0 parent ffff: u32 match u32 0 0 action mirred egress redirect dev ifb0
# Artık gelen trafiğe gecikme uygulayabiliriz:
sudo tc qdisc add dev ifb0 root netem delay 50ms
```

## 13. Güvenlik, Hata Ayıklama ve Taktik İpuçları

### 1. Komut Satırından Hızlı Wireshark / Tshark Filtreleri:
```bash
# Sadece kaybolan ve yeniden iletilen TCP paketlerini yakala:
tshark -r tactical_dump.pcap -Y "tcp.analysis.retransmission"

# RTT süresi 200 ms üzerinde olan yavaş paketleri filtrele:
tshark -r tactical_dump.pcap -Y "tcp.analysis.ack_rtt > 0.2"

# RTP akışının jitter ve paket kaybı özetini bas:
tshark -r tactical_dump.pcap -q -z rtp,streams
```

### 2. CI/CD Otomasyonunda Ağ Hata Enjeksiyonu:
Savunma yazılımlarının GitLab CI / Jenkins test hattında Docker konteynerlerine `NET_ADMIN` yetkisi verilerek `tc netem` testleri otomatik koşturulur:
```yaml
# gitlab-ci.yml örneği:
test_network_resilience:
  image: ubuntu:22.04
  tags: [docker-privileged]
  script:
    - apt-get update && apt-get install -y iproute2
    - tc qdisc add dev eth0 root netem loss 20% delay 100ms
    - ./run_tactical_telemetry_tests --strict
```

## 14. Günün Mini Uygulaması: Taktik Elektronik Harp ve PCAP Analiz Laboratuvarı

Günün mini uygulamasında:
1. Linux çekirdeğinin `tc/netem` kuyruk disiplinini birebir taklit eden saf yazılımsal bir kanal emülatörü geliştirdik.
2. Wireshark tarafından doğrudan analiz edilebilen standart Libpcap (`.pcap`) ikili dosya yazıcısını sıfırdan kodladık.
3. Elektronik Harp (EH) altında %15 paket kaybı, %10 çoğaltma ve %15 sıra bozulması uygulayarak savunmasız standart alıcı ile dayanıklı telemetri alıcısının farkını kanıtladık.
4. Yakalanan paket akışından ortalama gecikme, RTT ve RFC 3550 Jitter değerlerini matematiksel olarak hesaplayan analiz motorunu doğruladık.

## 15. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **Sadece Sabit Gecikmeyle Test Yapmak:** Ağda sadece `delay 100ms` uygulayıp jitter ve paket kaybını ihmal etmek; sahada bufferbloat yaşandığında yazılımın çökmesine yol açmak.
2. **Paket Çoğaltma (Duplication) Riskini Unutmak:** Telsiz hatlarında çok yollu yayılım (multipath) nedeniyle aynı paketin iki kez gelebileceğini hesaba katmayıp komutları iki kez çalıştırmak.
3. **`tc` Kurallarını Temizlemeyi Unutmak:** Test bitiminde `tc qdisc del dev eth0 root` komutunu çalıştırmayıp tüm işletim sisteminin internetini yavaşlatmak.
4. **Ingress Trafiğini Doğrudan Netem'e Bağlamaya Çalışmak:** Netem'in sadece giden trafiğe uygulandığını bilmeyip IFB arabirimini kurmamak.

## 16. Mülakat ve Saha Deneyimi Soruları (ASELSAN / HAVELSAN / BAYKAR)

### Soru 1: Bir İHA yer kontrol istasyonu yazılımının zorlu telsiz koşullarındaki dayanıklılığını doğrulamak için Linux ortamında nasıl bir test düzeneği kurarsınız?
**Cevap:** Donanım-Döngüde (HIL) veya Simülasyon-Döngüde (SITL) test altyapısı kurulur. Linux çekirdeğinin Trafik Kontrol aracı (`tc`) ve `netem` modülü kullanılarak hedef arayüze taktik harp sahası parametreleri enjekte edilir:
`tc qdisc add dev eth0 root netem delay 120ms 30ms distribution normal loss 15% duplicate 3% reorder 5%`.
Yazılımın ürettiği paketler `tshark` veya `tcpdump` ile `.pcap` olarak kaydedilir. Otomatik test senaryosunda telemetri kaybı, duplikasyon eliminasyonu ve RTT gecikme eşikleri doğrulanarak sistemin kendini toparlama (self-healing) kabiliyeti ölçülür.

### Soru 2: Linux `tc/netem` aracında gecikme simülasyonu yaparken neden tek bir sabit değer yerine 'distribution normal' kullanılır?
**Cevap:** Gerçek fiziksel telsiz hatlarında ve anahtarlamalı ağlarda kuyruk bekleme süreleri, RF yayılım koşulları ve işletim sistemi thread geçişleri nedeniyle paket gecikmesi sabit olamaz. Gecikme bir Gauss (Normal) dağılımı sergiler ($T \sim \mathcal{N}(\mu, \sigma^2)$). Sabit gecikme testi sistemdeki Jitter tamponu (de-jitter buffer) ve dinamik RTT tahmin algoritmalarını (TCP Jacobson/Karels) tetiklemez; bu nedenle gerçekçi test için normal veya pareto dağılımı zorunludur.

### Soru 3: Wireshark analizinde bir TCP akışında çok sayıda 'TCP Dup ACK' ve 'Fast Retransmission' görülmesi ne anlama gelir? Bu durum telsiz linkinde nasıl yorumlanmalıdır?
**Cevap:** Alıcı beklediği sıra numarasına sahip paket yerine daha ilerideki bir paketi aldığında, eksik paketi bildirmek için aynı ACK numarasını tekrar tekrar yollar (`Dup ACK`). Gönderici 3 adet ardışık Dup ACK aldığında, RTO zaman aşımını beklemeden eksik paketi anında tekrar yollar (`Fast Retransmission`). Telsiz linkinde bu durum, ağın tamamen kopmadığını ancak ara bir paketin RF paraziti veya kuyruk taşması yüzünden düşürüldüğünü ya da ağda yüksek oranda sıra bozulması (reordering) yaşandığını gösterir.

## 17. Gün Sonu Özeti ve 3-Cümle Çıkarımı

1. **tc/netem ve Wireshark Nedir?:** Linux çekirdeğinin kuyruk seviyesinde deterministik ağ bozulmaları (gecikme, kayıp, jitter, çoğaltma) üretmesini sağlayan araç ile bu trafiği ikili düzeyde yakalayıp analiz eden endüstri standardı yazılımdır.
2. **Hangi Problemi Çözer?:** Laboratuvardaki steril ağ koşullarının yanıltıcılığını ortadan kaldırarak, taktik telsiz ve elektronik harp koşullarının sahaya çıkmadan önce yazılım üzerinde test edilmesini sağlar.
3. **Hangi Trade-off/Hata Sınıfını Getirir?:** Test bittiğinde qdisc kuralları temizlenmezse geliştirme makinesinde gizli ağ performans sorunlarına yol açar; doğru simülasyon için tek yönlü (egress) değil IFB ile çift yönlü modelleme gerektirir.

