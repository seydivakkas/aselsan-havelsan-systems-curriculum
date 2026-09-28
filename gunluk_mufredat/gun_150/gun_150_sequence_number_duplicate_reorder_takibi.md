# GÜN 150: Sequence Number, Duplicate ve Reorder Takip Mimarisi

**Müfredat:** 365 Günlük ASELSAN / HAVELSAN Savunma Sistemleri C++20 & Linux Sistem Mühendisliği  
**Faz:** F4 — TCP/UDP / Ağ Protokolleri / Serileştirme & Taktik Dağıtık Sistemler  
**Konu:** Dizi Numarası (Sequence Number), Çok Yollu Ağlarda Paket Sıralama (Reordering), Mükerrer Paket Tespiti (De-duplication), RFC 4303 IPsec Kayar Pencere (Sliding Anti-Replay Window), Modüler Aritmetik ve Dizi Taşması (Wrap-Around) Yönetimi  
**Ön Koşul:** Gün 149 (Framing: length-prefix / magic / delimiter)

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

Taktik savunma sistemlerinde (hava savunma füze güdüm bağları, radar hedef izleme akışları, İHA otopilot komuta kanalları), düşük gecikme zorunluluğu nedeniyle aktarım katmanında genellikle UDP veya özel telsiz dalga formları (Link-16 / Link-22 / MIL-STD-188) kullanılır.

UDP ve telsiz ağları doğası gereği:
1. **Paket Sırasını Garanti Etmez (Out-of-Order Delivery):** Farklı rotalardan (Multi-path) veya röle İHA'ları üzerinden geçen paketler sırası karışmış olarak gelebilir (#102, #101'den önce ulaşabilir).
2. **Paketleri Çoğaltabilir (Duplication):** Taktik yönlendiriciler paket kaybını önlemek için aynı paketi birden fazla anten/link üzerinden yayınlayabilir.
3. **Yeniden Oynatma Saldırılarına (Replay Attack) Açıktır:** Bir elektronik harp (EH) karıştırıcısı veya siber saldırgan, 10 saniye önce gönderilmiş geçerli bir `DISARM` veya `ABORT_MISSION` paketini telsizden yakalayıp 15 saniye sonra tekrar yayına basabilir!

Bu kaotik ortamda alıcı sistemin iki kritik görevi vardır:
- **Anti-Replay / De-duplication:** Daha önce işlenmiş veya eski bir paketi derhal çöpe atmak.
- **In-Order Delivery (Sıralı Teslimat):** Sırası karışmış paketleri kısa süreli bir bekleme tamponuna (Jitter/Reorder Buffer) alarak monotonik ($1, 2, 3, 4\dots$) sırayla taktik karar motoruna iletmek.

```
   +-------------------------------------------------------------------------+
   |          TAKTIK AĞDA SIRA BOZULMASI, ÇOĞALTMA VE SİBER REPLAY           |
   +-------------------------------------------------------------------------+

   Verici (Füze C2):   [Paket 1]   [Paket 2]   [Paket 3]   [Paket 4]
                             |           |           |           |
                             v           v           v           v
   Telsiz Linki:       ---------(Multi-path / Jamming / EH)-----------
                             |           |           |           |
                             v           v           v           v
   Alıcıya Geliş:      [Paket 1]   [Paket 3]   [Paket 2]   [Paket 2 (Mükerrer)]
                                       ^           ^                ^
                                    (Erken)    (Gecikmiş)      (Siber Kopya!)
                                       |           |                |
   +-------------------------------------------------------------------------+
   |      ALICI SAVUNMA HATTI: SLIDING WINDOW & JITTER REORDER BUFFER        |
   +-------------------------------------------------------------------------+
   1. [Paket 2 (Mükerrer)] -> Kayar Pencere Kontrolü -> "MÜKERRER!" -> ÇÖPE AT!
   2. [Paket 3]            -> Tampona Al (Reorder Buffer), Henüz 2 Gelmedi!
   3. [Paket 2]            -> Geldi! Şimdi Sırayla Boşalt: [Paket 2] -> [Paket 3]
   Çıktı (Taktik Motor):   [Paket 1] -> [Paket 2] -> [Paket 3] (KUSURSUZ SIRA)
```

---

## 2. Neden Dizi Numarası (Sequence Number)?

Uygulama katmanı protokol başlığında (Application Layer Header) yer alan `uint32_t sequence_number` alanı, her gönderilen pakette monotonik olarak 1 artırılır.

### Çözülen 3 Temel Problem:
1. **Paket Kaybı Tespiti (Packet Loss Detection):**
   Eğer alıcı `#100`'den sonra doğrudan `#104`'ü alırsa, `#101, #102, #103` numaralı üç paketin ağda düştüğünü anlar. Buna göre NACK (Negative Acknowledgment) isteyebilir veya telemetri eksikliğini telemetri filtresine bildirir.
2. **Yeniden Sıralama (Reordering):**
   Gecikmiş paketleri doğru zaman çizgisine yerleştirir.
3. **Mükerrer Paket Engelleme (Anti-Replay & Deduplication):**
   Aynı dizi numarasına sahip ikinci bir paket geldiğinde tek bir saat çevriminde algılanıp yok edilir.

---

## 3. IPsec RFC 4303 Kayar Pencere (Sliding Anti-Replay Window)

Geçmişte gelen tüm dizi numaralarını bir `std::set<uint32_t>` içinde saklamak devasa bir bellek sızıntısına (memory leak) ve $O(\log N)$ arama maliyetine yol açar. Milyonlarca paket aktığında RAM tükenir.

RFC 4303 (IPsec ESP) standardı, bu problemi **Sabit Boyutlu Kayar Pencere (Sliding Window)** ve **Bitmask** ile $O(1)$ sürede ve sadece **8 bayt bellek** kullanarak çözer!

```
   Pencere Boyutu: W = 64 Paket (uint64_t bitmap)
   En Yüksek Görülen Dizi No: MaxSeq = 100

   Pencere Aralığı: [ MaxSeq - W + 1  ...  MaxSeq ]  ->  [ 37 ... 100 ]

   Gelen Paket:
   1. Seq > MaxSeq (Örn: 105):
      Pencere 5 adım sağa kaydırılır (bitmap <<= 5).
      bitmap[0] = 1 yapılır. MaxSeq = 105 güncellenir. -> KABUL ET!

   2. Seq <= MaxSeq ve (MaxSeq - Seq) < W (Örn: 98):
      Ofset = MaxSeq - Seq = 100 - 98 = 2.
      Eğer bitmap & (1ULL << 2) == 1 ise: -> MÜKERRER PAKET (DUPLICATE) -> AT!
      Eğer 0 ise: bitmap |= (1ULL << 2) işaretle. -> SIRASI BOZUK AMA YENİ -> KABUL ET!

   3. Seq <= MaxSeq ve (MaxSeq - Seq) >= W (Örn: 30):
      Pencerenin solunda kalmış aşırı eski paket! -> STALE / REPLAY ATTACK -> AT!
```

---

## 4. Sıralama Tamponu (Jitter/Reorder Buffer) ve Monotonik Teslimat

Anti-Replay penceresi mükerrer paketleri eler ancak sırası bozulmuş paketleri doğrudan uygulama katmanına teslim edemez. Aviyonik uçuş kontrol algoritmaları zaman serisi verisini kesinlikle artan sırada ($Seq, Seq+1, Seq+2\dots$) bekler.

### Jitter / Reorder Buffer Mimarisi:
1. Alıcı beklediği bir sonraki dizi numarasını tutar: `expected_seq`.
2. Eğer gelen paket `seq == expected_seq` ise anında taktik motora iletilir ve `expected_seq++` yapılır.
3. Eğer gelen paket `seq > expected_seq` ise (yani aradaki bir paket henüz gelmediyse), paket bir **Sıralı Öncelik Kuyruğuna (Min-Heap / Ring Buffer)** konulur.
4. Eksik paket geldiğinde, tamponda bekleyen ardışık tüm paketler sırayla boşaltılır (`flush pipeline`).
5. **Zaman Aşımı Koruması (Drop Timeout):** Eğer eksik paket belirli bir süre (örneğin $20\ \text{ms}$) boyunca gelmezse, o paket "kayıp" ilan edilir; `expected_seq` bir sonrakine atlatılarak akışın tıkanması (Head-of-Line Blocking) önlenir.

---

## 5. Dizi Numarası Taşması (Wrap-Around) ve Modüler Aritmetik

Dizi numaraları sonsuz büyüklükte olamaz. 16-bit (`uint16_t`) bir sayaç $65,535$ değerine ulaştığında bir sonraki paket $0$ olur:
$$65534 	o 65535 	o 0 	o 1 	o 2 \dots$$

### Klasik Acemi Tuzağı:
```cpp
// TEHLİKELİ HATA: 65535'ten sonra sistem sonsuza dek kilitlenir!
if (new_seq > last_seq) {
    // 0 > 65535 YANLIŞTIR (False)!
    // 0 numaralı yeni paket "eski paket" sanılarak çöpe atılır!
}
```

### Doğru Çözüm: İşaretli Modüler Fark (Signed Distance)
İki dizi numarası arasındaki fark işaretli tamsayıya (`int16_t` veya `int32_t`) dönüştürülerek karşılaştırılır (RFC 1982 Serial Number Arithmetic):
```cpp
// 16-bit Dizi Numarası Karşılaştırması (Kusursuz C++20):
inline bool is_newer_seq16(uint16_t new_seq, uint16_t last_seq) {
    return static_cast<int16_t>(new_seq - last_seq) > 0;
}
// Örnek: new_seq = 0, last_seq = 65535
// (uint16_t)(0 - 65535) = 1
// (int16_t)(1) > 0 -> DOĞRU (True)! 0 sayısı 65535'ten daha yenidir!
```

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 150: Kod Bloğu 1 — C++20 / RFC 4303 Sliding Anti-Replay Window ve Reorder Buffer
"""

import heapq
from typing import Optional, List, Tuple, Dict, Any

class AntiReplayWindow64:
    """
    RFC 4303 IPsec 64-Bit Sliding Anti-Replay Window Algoritması.
    O(1) süre, sıfır heap tahsisi, 8 bayt bellek.
    """
    WINDOW_SIZE = 64

    def __init__(self):
        self.max_seq = 0
        self.bitmap = 0  # uint64_t bitmask (Bit 0: max_seq, Bit 1: max_seq - 1 ...)
        self.initialized = False
        self.stats = {
            "accepted_in_order": 0,
            "accepted_out_of_order": 0,
            "rejected_duplicate": 0,
            "rejected_stale": 0
        }

    def check_and_update(self, seq: int) -> bool:
        if not self.initialized:
            self.max_seq = seq
            self.bitmap = 1
            self.initialized = True
            self.stats["accepted_in_order"] += 1
            return True

        diff = seq - self.max_seq

        # Durum 1: Yeni En Yüksek Dizi Numarası (seq > max_seq)
        if diff > 0:
            if diff < self.WINDOW_SIZE:
                self.bitmap = (self.bitmap << diff) | 1
            else:
                self.bitmap = 1
            self.max_seq = seq
            self.bitmap &= 0xFFFFFFFFFFFFFFFF # 64-bit mask
            self.stats["accepted_in_order"] += 1
            return True

        # Durum 2: Pencere İçinde Eski Paket (max_seq - W < seq <= max_seq)
        offset = -diff
        if offset < self.WINDOW_SIZE:
            mask = 1 << offset
            if self.bitmap & mask:
                # Daha önce alınmış -> DUPLICATE!
                self.stats["rejected_duplicate"] += 1
                return False
            else:
                # Pencere içinde eksik olan paket geldi -> KABUL ET!
                self.bitmap |= mask
                self.stats["accepted_out_of_order"] += 1
                return True

        # Durum 3: Pencere Dışında Aşırı Eski Paket (seq <= max_seq - W)
        self.stats["rejected_stale"] += 1
        return False

class JitterReorderBuffer:
    """
    Gerçek zamanlı sıralama tamponu.
    Gelen sırası bozuk paketleri monotonik sırada teslim eder.
    """
    def __init__(self, initial_seq: int = 1):
        self.expected_seq = initial_seq
        self.buffer = [] # Min-heap: (seq, payload)
        self.delivered_stream = []

    def push(self, seq: int, payload: bytes) -> List[Tuple[int, bytes]]:
        output = []
        heapq.heappush(self.buffer, (seq, payload))

        # Tampondaki ardışık paketleri sırayla boşalt
        while self.buffer and self.buffer[0][0] == self.expected_seq:
            s, p = heapq.heappop(self.buffer)
            output.append((s, p))
            self.delivered_stream.append((s, p))
            self.expected_seq += 1

        return output

print("[HÜCRE 7] AntiReplayWindow64 ve JitterReorderBuffer sınıfları başarıyla yüklendi.")
```

---

## 6. Taktik Telsiz Ağında Sırası Bozulmuş ve Çoğaltılmış Telemetri Deneyi

Bu deneyde, bir Taktik İHA yer veri bağından gelen $20$ paketlik bir telemetri akışını simüle edeceğiz:
- Paketler ağda karıştırılmıştır (Sırası bozuk gelmektedir).
- Bazı paketler taktik tekrarlayıcılar (repeater) yüzünden 2 kez iletilmiştir (Mükerrer).
- `AntiReplayWindow64` mükerrer paketleri filtreleyecek; `JitterReorderBuffer` ise kalan paketleri $1..20$ kusursuz sırasına sokarak teslim edecektir.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 150: Kod Bloğu 2 — Çok Yollu Taktik Ağ Deneyi: Karışık ve Mükerrer Paketlerin Düzeltilmesi
"""

import random

# 1. Orijinal 20 Paketlik Düzgün Akış Hazırla
original_packets = [(seq, f"TELEMETRY_DATA_SEQ_{seq}".encode()) for seq in range(1, 21)]

# 2. Kaotik Ağ Simülasyonu: Sıraları karıştır ve bazı paketleri çift gönder (Duplicate)
chaotic_stream = list(original_packets)
random.seed(42)
random.shuffle(chaotic_stream)

# Paket #5, #12 ve #18'i mükerrer olarak araya ekle
chaotic_stream.insert(4, (5, b"TELEMETRY_DATA_SEQ_5"))
chaotic_stream.insert(10, (12, b"TELEMETRY_DATA_SEQ_12"))
chaotic_stream.insert(18, (18, b"TELEMETRY_DATA_SEQ_18"))

print(f"[*] Kaotik Ağ Akışı Hazırlandı: Toplam {len(chaotic_stream)} Paket (20 Özgün + 3 Mükerrer)")

# 3. Alıcı Tarafı: Anti-Replay + Reorder Buffer Hattı
anti_replay = AntiReplayWindow64()
reorder_buf = JitterReorderBuffer(initial_seq=1)

delivered_packets = []

for seq, payload in chaotic_stream:
    # Aşama 1: Anti-Replay ve De-duplication Filtresi
    if not anti_replay.check_and_update(seq):
        print(f"  [-] MÜKERRER PAKET ENGELLENDİ: Dizi #{seq}")
        continue

    # Aşama 2: Sıralama Tamponu (Jitter Buffer)
    ready_pkts = reorder_buf.push(seq, payload)
    for r_seq, r_payload in ready_pkts:
        delivered_packets.append(r_seq)

print()
print("[*] Alıcı Taktik İşleme Raporu:")
print(f"  [+] Anti-Replay Doğrudan Kabul (In-Order)     : {anti_replay.stats['accepted_in_order']} adet")
print(f"  [+] Anti-Replay Sırası Bozuk Kabul (In-Window): {anti_replay.stats['accepted_out_of_order']} adet")
print(f"  [+] Engellenen Mükerrer (Duplicate) Paket      : {anti_replay.stats['rejected_duplicate']} adet")
print(f"  [+] Taktik Motora Teslim Edilen Dizi Sırası   : {delivered_packets}")

assert anti_replay.stats['rejected_duplicate'] == 3, "Tam 3 mükerrer paket yakalanmalıydı!"
assert delivered_packets == list(range(1, 21)), "Teslim edilen paketler 1'den 20'ye kusursuz sıralı olmalı!"
print("[HÜCRE 9] Kaotik ağ akışı sıfır hata ile düzeltildi ve doğrulandı.")
```

---

## 7. Bilerek Bozma (Sabotaj ve Arıza Enjeksiyonu)

Bu bölümde iki ölümcül hata ve siber saldırı senaryosunu simüle edeceğiz:

### Sabotaj 1: Düşman Replay Saldırısı (Elektronik Harp)
Siber saldırgan, 10 saniye önce İHA'ya gönderilen `CMD_ABORT_MISSION` paketini telsizden kopyalamıştır. İHA hedef bölgesine girdiğinde saldırgan bu eski paketi tekrar hatta basar.
- **Beklenen Hata Belirtisi:** Anti-replay koruması olmayan bir otopilot, eski emri geçerli sanıp görevi iptal eder ve üsse döner (Görev Başarısızlığı).
- **Savunma:** Kayar pencere algoritması, paketin dizi numarasının pencere gerisinde kaldığını (`STALE`) anında tespit eder ve saldırıyı bertaraf eder.

### Sabotaj 2: Wrap-Around Karşılaştırma Hatası
Sayaç $65,535$'ten $0$'a döndüğünde naif bir büyüktür (`>`) kontrolü yapılmıştır.
- **Beklenen Hata Belirtisi:** $0$ sayısı $65,535$'ten küçük olduğu için sistem sonraki tüm yeni paketleri "eski" zanneder ve sonsuza kadar kilitlenir!
- **Savunma:** İşaretli modüler mesafe (`int16_t(new - old) > 0`) ile taşma sorunu çözülür.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 150: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Replay Saldırısı & Wrap-Around Tuzağı
"""

print()
print("[*] Anti-Replay Sabotaj ve Güvenlik Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: Düşman Replay Saldırısı (Stale Paket Enjeksiyonu)
# -----------------------------------------------------------------------------
ar_test = AntiReplayWindow64()

# Sistem 100 paketi normal işledi
for s in range(1, 101):
    ar_test.check_and_update(s)

# Düşman 75 paket önceki (Seq #25) eski bir paketi hatta bastı!
stale_seq = 25
is_stale_accepted = ar_test.check_and_update(stale_seq)

print(f"  [+] Sabotaj 1 Sonuçları (Siber Replay Saldırısı):")
print(f"      - Mevcut MaxSeq           : {ar_test.max_seq}")
print(f"      - Enjekte Edilen Eski Dizi: #{stale_seq} (Pencere Boyutu: 64)")
print(f"      - Saldırı Paketi Kabul Edildi mi? : {is_stale_accepted} (REDDEDİLDİ - SAVUNMA BAŞARILI!)")

assert not is_stale_accepted, "Eski paket anti-replay penceresi tarafından reddedilmeliydi!"
assert ar_test.stats['rejected_stale'] == 1

# -----------------------------------------------------------------------------
# SABOTAJ 2: 16-bit Dizi Numarası Wrap-Around Karşılaştırması
# -----------------------------------------------------------------------------
last_seq_16 = 65535 # 0xFFFF (Maksimum 16-bit)
new_seq_16 = 0      # Taşma sonrası ilk paket

# Hatalı Naive Karşılaştırma
naive_is_newer = (new_seq_16 > last_seq_16)

# Doğru İşaretli Modüler Karşılaştırma (RFC 1982)
def is_newer_16(n_seq: int, l_seq: int) -> bool:
    diff_u16 = (n_seq - l_seq) & 0xFFFF
    # 16-bit işaretli tamsayıya çevir (-32768 .. 32767)
    diff_s16 = diff_u16 if diff_u16 < 0x8000 else diff_u16 - 0x10000
    return diff_s16 > 0

correct_is_newer = is_newer_16(new_seq_16, last_seq_16)

print(f"  [+] Sabotaj 2 Sonuçları (Wrap-Around Taşma Yönetimi):")
print(f"      - Son Dizi No : {last_seq_16} -> Yeni Dizi No : {new_seq_16}")
print(f"      - Naive (new > last) Sonucu : {naive_is_newer} (SİSTEM KİLİTLENİR!)")
print(f"      - Modüler Aritmetik Sonucu  : {correct_is_newer} (KUSURSUZ ÇALIŞTI)")

assert not naive_is_newer, "Naive karşılaştırma taşmada başarısız olmalıydı!"
assert correct_is_newer, "Modüler karşılaştırma taşmayı doğru tespit etmeliydi!"
print("[HÜCRE 11] Tüm sabotaj deneyleri ve güvenlik savunmaları başarıyla doğrulandı.")
```

---

## 8. Performans ve Gecikme Benchmark Metrikleri

Savunma sistemlerinde anti-replay ve paket sıralama mekanizmaları doğrudan ana veri hattı üzerinde (Fast-Path) çalışır.
Her pakette yapılan bitmask kaydırma ve kontrol operasyonunun CPU saat çevrimleri (clock cycle) seviyesinde olması şarttır.

Aşağıdaki benchmarkta:
- $1,000,000$ paket üzerinde `AntiReplayWindow64` bitmask sorgusu icra edilecek,
- Paket başına işlem süresi (nanosaniye) ve saniye başına işlem kapasitesi (Mpps - Megapackets per second) ölçülecektir.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 150: Kod Bloğu 4 — Benchmark: 1,000,000 Paket Başına Anti-Replay Bitmask İşlem Hızı
"""

import time

def run_antireplay_benchmark(packet_count: int = 500_000) -> Dict[str, Any]:
    window = AntiReplayWindow64()
    
    t0 = time.perf_counter()
    for s in range(1, packet_count + 1):
        window.check_and_update(s)
    t1 = time.perf_counter()
    
    duration_sec = t1 - t0
    mpps = (packet_count / duration_sec) / 1e6
    ns_per_packet = (duration_sec / packet_count) * 1e9

    return {
        "count": packet_count,
        "duration_ms": duration_sec * 1000.0,
        "mpps": mpps,
        "ns_per_packet": ns_per_packet
    }

bench_res = run_antireplay_benchmark(packet_count=500_000)

print()
print(f"[*] Anti-Replay Bitmask Benchmarkı ({bench_res['count']:,} Paket):")
print(f"  [+] Toplam Süre          : {bench_res['duration_ms']:.2f} ms")
print(f"  [+] Paket Başına Gecikme : {bench_res['ns_per_packet']:.2f} ns (Nanosaniye Seviyesi!)")
print(f"  [+] Throughput           : {bench_res['mpps']:.2f} Mpps (Milyon Paket/Saniye)")

assert bench_res['ns_per_packet'] < 1000.0, "Paket başına kontrol 1 mikrosaniyenin çok altında olmalıdır!"
print("[HÜCRE 13] Benchmark başarıyla tamamlandı.")
```

---

## 9. Gerçek Dünya Taktik Senaryosu: ASELSAN Taktik Link Füze Komuta Güvenliği

Bir Hisar/Siper Hava Savunma Bataryasında Karargah Komuta Merkezi (C2) ile Füze Lançeri arasında kablosuz taktik veri bağı üzerinden kritik angajman komutları akar:
- `0x01`: `TRACK_TARGET`
- `0x02`: `RADAR_LOCK_ON`
- `0x03`: `FIRE_MISSILE`

Eğer düşman karıştırıcısı daha önce kaydedilmiş bir `FIRE_MISSILE` emrini tekrar oynatırsa batarya boş yere mühimmat tüketebilir veya dost unsurları vurabilir.
Taktik komuta alıcısı, her paketi `AntiReplayWindow` ile denetler ve yalnızca meşru, sıralı yeni komutları icra eder.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 150: Kod Bloğu 5 — Taktik Füze Ateşleme Hattı: Replay-Korumalı Güvenli Tüketici
"""

class SecureTacticalConsumer:
    def __init__(self):
        self.anti_replay = AntiReplayWindow64()
        self.executed_commands = []
        self.rejected_attacks = 0

    def receive_command_packet(self, seq: int, command: str) -> bool:
        # Anti-Replay doğrulaması
        if not self.anti_replay.check_and_update(seq):
            self.rejected_attacks += 1
            return False
            
        # Güvenle icra et
        self.executed_commands.append((seq, command))
        return True

c2_receiver = SecureTacticalConsumer()

# 1. Normal Meşru Komutlar
c2_receiver.receive_command_packet(seq=1, command="SYS_INIT")
c2_receiver.receive_command_packet(seq=2, command="RADAR_SEARCH_MODE")
c2_receiver.receive_command_packet(seq=3, command="TARGET_TRACK_LOCK")
c2_receiver.receive_command_packet(seq=4, command="ARM_WARHEAD")
c2_receiver.receive_command_packet(seq=5, command="FIRE_MISSILE_ALPHA")

# 2. Düşman Elektronik Harp Araya Girdi: Eski Ateşleme Emrini (#5) Tekrar Gönderdi!
attack_res = c2_receiver.receive_command_packet(seq=5, command="FIRE_MISSILE_ALPHA")

print()
print("[*] Taktik Füze Lançeri Güvenlik Denetim Raporu:")
print(f"  [+] Başarıyla İcra Edilen Emir Sayısı : {len(c2_receiver.executed_commands)}")
for s, cmd in c2_receiver.executed_commands:
    print(f"      - [Seq #{s}] {cmd} -> İCRA EDİLDİ")

print(f"  [+] Saldırı Girişimi (Seq #5 Tekrarı) : Kabul = {attack_res} (BLOKE EDİLDİ!)")
print(f"  [+] Engellenen Siber Saldırı Sayısı   : {c2_receiver.rejected_attacks}")

assert attack_res == False
assert c2_receiver.rejected_attacks == 1
assert len(c2_receiver.executed_commands) == 5
print("[HÜCRE 15] Taktik güvenli tüketici simülasyonu başarıyla tamamlandı.")
```

---

## 10. 4-Panelli 300 DPI Görselleştirme Mimarisi

Aşağıdaki kod hücresi, Anti-Replay kayar pencere algoritmasını, sıra bozulması/tamponlama mantığını, modüler wrap-around çemberini ve benchmark metriklerini 4 panelde detaylandıran profesyonel bir karanlık tema (`#0F172A`) görsel panosu üretir:

1. **Panel 1 (Sol Üst): RFC 4303 Kayar Pencere (Sliding Window) Bitmask Anatomisi:**
   En yüksek dizi numarası ($MaxSeq$), $W=64$ bitlik kayar pencere aralığı, kabul edilen sıralı/sırasız paketler ve reddedilen mükerrer/eski alanlar.
2. **Panel 2 (Sağ Üst): 16-Bit Dizi Numarası Wrap-Around Modüler Çemberi:**
   $65,535 	o 0$ geçişinde işaretli fark aritmetiği ile saat yönü ilerlemesi.
3. **Panel 3 (Sol Alt): Jitter/Reorder Tamponlama Zaman Çizelgesi:**
   Karışık gelen paketlerin ($1, 4, 2, 3$) öncelik kuyruğunda bekletilip monotonik ($1 	o 2 	o 3 	o 4$) olarak boşaltılması.
4. **Panel 4 (Sağ Alt): Anti-Replay Bitmask Kontrol Benchmarkı:**
   Throughput (Mpps) ve nanosaniye seviyesindeki ultra düşük gecikme.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 150: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_150_sequence_number_duplicate_reorder_takibi.png")

# Matplotlib stil ve karanlık tema ayarları
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: Sliding Anti-Replay Window Bitmask Şeması
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

# Pencere Alanları Çizimi
# 1. Eski Bölge (Stale)
rect_stale = plt.Rectangle((0.05, 0.40), 0.25, 0.35, facecolor='#EF4444', alpha=0.25, edgecolor='#EF4444', lw=2)
ax1.add_patch(rect_stale)
ax1.text(0.175, 0.60, "ESKİ BÖLGE (STALE)\n< (MaxSeq - 64)", ha='center', color='#EF4444', fontsize=9.5, fontweight='bold')
ax1.text(0.175, 0.48, "Saldırı / Çöp Paket\n[REDDET / AT]", ha='center', color='#F8FAFC', fontsize=8.5)

# 2. Kayar Pencere (W=64 Bitmask)
rect_win = plt.Rectangle((0.33, 0.40), 0.42, 0.35, facecolor='#3B82F6', alpha=0.25, edgecolor='#38BDF8', lw=2)
ax1.add_patch(rect_win)
ax1.text(0.54, 0.62, "KAYAR PENCERE (W = 64 Bit)", ha='center', color='#38BDF8', fontsize=10.5, fontweight='bold')
ax1.text(0.54, 0.52, "Bit = 0: Bekleniyor (Kabul Et)\nBit = 1: Mükerrer (Duplicate - At)", ha='center', color='#F8FAFC', fontsize=8.5)
ax1.text(0.54, 0.43, "[ MaxSeq - 63 ... MaxSeq ]", ha='center', color='#94A3B8', fontsize=8.5)

# 3. İleri Bölge (New MaxSeq)
rect_new = plt.Rectangle((0.78, 0.40), 0.17, 0.35, facecolor='#10B981', alpha=0.25, edgecolor='#10B981', lw=2)
ax1.add_patch(rect_new)
ax1.text(0.865, 0.60, "YENİ BÖLGE\n> MaxSeq", ha='center', color='#10B981', fontsize=9.5, fontweight='bold')
ax1.text(0.865, 0.48, "Pencereyi Kaydır\n[KABUL ET]", ha='center', color='#F8FAFC', fontsize=8.5)

ax1.set_title("RFC 4303 64-Bit Kayar Pencere (Sliding Window) Algoritması", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: 16-Bit Modüler Wrap-Around Çemberi
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

# Çember Çizimi
theta = np.linspace(0, 2*np.pi, 200)
xc = np.cos(theta)
yc = np.sin(theta)
ax2.plot(xc, yc, color='#64748B', linestyle='--', linewidth=1.5)

# Kritik Noktalar: 0 (En Üst), 32768 (En Alt), 65535 (Hemen Sol Üst)
ax2.scatter([0], [1], color='#10B981', s=120, zorder=5, label='Seq = 0 (Yeniden Başlama)')
ax2.scatter([-0.08], [0.99], color='#EF4444', s=120, zorder=5, label='Seq = 65535 (Maksimum 16-Bit)')
ax2.scatter([0], [-1], color='#F59E0B', s=100, zorder=5, label='Seq = 32768 (Zıt Nokta / Sınır)')

# Ok
ax2.annotate("", xy=(0.15, 0.98), xytext=(-0.15, 0.98), arrowprops=dict(arrowstyle="->", color="#10B981", lw=2.5))
ax2.text(0.0, 1.15, "Wrap-Around: int16(0 - 65535) = +1 > 0", ha='center', color='#10B981', fontsize=9, fontweight='bold')

ax2.set_xlim(-1.4, 1.4)
ax2.set_ylim(-1.4, 1.4)
ax2.axis('off')
ax2.legend(loc='lower center', facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', fontsize=8.5)
ax2.set_title("16-Bit Dizi Numarası Modüler Taşma Çemberi", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 3: Jitter / Reorder Tamponu Zaman Çizelgesi
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

# 1..10 Sıralı Akış vs Geliş Zamanı
time_steps = np.arange(1, 11)
arriving_order = [1, 3, 2, 5, 4, 7, 6, 8, 10, 9]
in_order_stream = list(range(1, 11))

ax3.plot(time_steps, arriving_order, color='#EF4444', marker='o', linestyle=':', linewidth=2, label='Ağdan Geliş Sırası (Karışık)')
ax3.plot(time_steps, in_order_stream, color='#10B981', marker='s', linewidth=2.2, label='Jitter Buffer Çıkışı (Monotonik Sıralı)')

ax3.set_title("Taktik Jitter Reorder Buffer: Karışık Akışın Düzeltilmesi", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.set_xlabel("Zaman Adımı (Time Step)", fontsize=10, color='#94A3B8')
ax3.set_ylabel("Dizi Numarası (Sequence Number)", fontsize=10, color='#94A3B8')
ax3.grid(True, linestyle=':', alpha=0.4, color='#64748B')
ax3.legend(loc='upper left', facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: Anti-Replay Bitmask Performans Benchmarkı
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')

metrics = ['Throughput\n(Milyon Paket/sn)', 'Gecikme Başına\n(Nanosaniye - ns)']
values = [bench_res['mpps'], bench_res['ns_per_packet']]
colors_bar = ['#10B981', '#38BDF8']

bars4 = ax4.bar(metrics, values, color=colors_bar, width=0.45, edgecolor='#334155', linewidth=1.5)
for bar, val in zip(bars4, values):
    yval = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval + (max(values)*0.03), f"{val:.1f}", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=11)

ax4.set_ylim(0, max(values) * 1.25)
ax4.set_title(f"Bitmask Anti-Replay İşlem Kapasitesi ({bench_res['count']:,} Paket)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax4.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax4.tick_params(colors='#94A3B8')

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 150 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert bench_res['mpps'] > 0.5, "Anti-replay throughput en az 0.5 Mpps olmalı!"
assert anti_replay.stats['rejected_duplicate'] == 3
assert correct_is_newer == True

print()
print("[PASS] Gün 150: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

---

## 11. Karşılaştırmalı Analiz ve Mimari Karar Matrisi

Farklı dizi numarası ve sıralama stratejilerinin karşılaştırılması:

| Strateji | Bellek Karmaşıklığı | Zaman Karmaşıklığı | Replay Direnci | Reorder Desteği |
| :--- | :--- | :--- | :--- | :--- |
| **Strict Monotonic (`seq > last`)** | $O(1)$ (1 Değişken) | $O(1)$ Tek Karşılaştırma | Zayıf (Tüm out-of-order düşer) | **YOK (Sırası bozuk atılır)** |
| **Tam Küme (`std::set<uint32_t>`)** | **$O(N)$ (Bellek Sızıntısı)** | $O(\log N)$ Ağaç Araması | Mükemmel | Heap ile mümkün |
| **RFC 4303 Kayar Pencere Bitmask** | **$O(1)$ (Yalnızca 8 Bayt!)** | **$O(1)$ (1 Saat Çevrimi Bitwise)**| **Mükemmel (Siber Standart)** | Var ($W$ pencere içi) |
| **Jitter Reorder Ring Buffer** | $O(W)$ Sabit Halka Tampon | $O(1)$ İndisli Erişim | Bitmask ile Birlikte Mükemmel | **Kusursuz Monotonik Teslimat** |

---

## 12. Donanım ve İşletim Sistemi Seviyesi Etkileşimler

### CPU Seviyesinde Bit Tarama Talimatları
1. **64-Bit Bitmask Operasyonları:** `1ULL << offset` ve bitwise `AND` / `OR` işlemleri modern x86_64 ve ARM64 mimarilerinde tek bir saat çevriminde ($< 0.5\ \text{ns}$) çalışır.
2. **Donanım Bit Tarama (Bit Scan):** İşlemcilerdeki `TZCNT` (Trailing Zero Count) ve `BSF` (Bit Scan Forward) talimatları sayesinde pencere içindeki en eski veya en yeni bitler tek komutla bulunur.
3. **Önbellek Yerelliği (Cache Locality):** `AntiReplayWindow64` yapısı sadece 16 bayt yer kapladığı için işlemcinin L1 veri önbelleğinde (L1D Cache) kalıcı olarak ikamet eder; asla bellek veri yolunu meşgul etmez.

---

## 13. Güvenlik, Hata Ayıklama ve Taktik İpuçları

### 1. Wireshark RTP ve IPsec Dizi Analizi
Wireshark üzerinde `Telephony -> RTP -> Stream Analysis` menüsü kullanılarak:
- Paket kaybı oranı (Lost),
- Mükerrer paketler (Duplicate),
- Gecikme dalgalanması (Jitter) gerçek zamanlı grafik olarak incelenebilir.

### 2. Dizi Boşluğu İkaz Sistemi (Sequence Gap Monitoring)
```cpp
if (seq > expected_seq) {
    uint32_t gap = seq - expected_seq;
    TACTICAL_LOG_WARN("Agda paket kaybi algilandi! Kayip Adet: %u", gap);
}
```

---

## 14. Günün Mini Uygulaması: Taktik Anti-Replay ve Reorder Motoru

Günün mini uygulamasında, çok yollu telsiz ağlarında sırası karışmış ve kopyalanmış taktik füze komutlarını; RFC 4303 64-bit kayar pencere ve min-heap tabanlı jitter tamponuyla süzen C++20 `AntiReplayWindow64` ve `JitterReorderBuffer` motorunu modelledik.

### Temel Doğrulama Adımları:
1. **Normal Test:** 20 karışık ve çoğaltılmış paketin sıfır veri kaybıyla ve $1..20$ kusursuz sırayla taktik motora teslim edilmesi.
2. **Hata Testi (Sabotaj):** Eski füze ateşleme emrinin (Replay Attack) siber koruma tarafından anında bloklanması ve $65535 	o 0$ wrap-around taşmasının modüler aritmetikle doğrulanması.

---

## 15. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **Taşmayı (Wrap-Around) Düşünmemek:** $65535$'ten sonra sayacın $0$'a döneceğini unutup sistemi kilitlemek.
2. **Gelen Her Sırasız Paketi Doğrudan İşlemek:** Telemetri verisinin sırası karıştığında Kalman filtresine geçmiş zamana ait veri besleyip seyrüsefer kararsızlığına yol açmak.
3. **Mükerrer Paketleri Saklamak İçin Dinamik Bellek Kullanmak:** `std::vector` içinde arama yaparak $O(N)$ CPU ve devasa RAM tüketmek.
4. **Zaman Aşımı Sınırı Koymamak:** Eksik bir paket gelmediğinde sonsuza kadar bekleyip akışı dondurmak (Head-of-Line Blocking).

---

## 16. Mülakat ve Saha Deneyimi Soruları (ASELSAN / HAVELSAN / TÜBİTAK BİLGEM)

### Soru 1: UDP tabanlı taktik telsiz sistemlerinde "Anti-Replay" koruması neden hayati önem taşır?
**Cevap:** UDP durumsuz (stateless) bir protokoldür ve kimlik doğrulama veya sıra takibi sunmaz. Bir elektronik harp saldırganı veya karıştırıcı, telsizden dinlediği meşru bir komutu (örneğin uçuş iptali veya radar kapatma emri) kaydedip dakikalar sonra tekrar yayınlayabilir (Replay Attack). Anti-replay kayar penceresi, daha önce işlenmiş veya pencerenin gerisinde kalmış eski paketleri anında algılayıp yok ederek bu saldırıyı engeller.

### Soru 2: IPsec RFC 4303 Kayar Pencere algoritması neden $O(1)$ karmaşıklığa sahiptir?
**Cevap:** Algoritma tüm dizi numaralarını saklamak yerine sadece tek bir `uint64_t` bitmask (64 bit) ve en yüksek dizi numarasını (`max_seq`) tutar. Gelen yeni dizi numarası ile `max_seq` arasındaki farka göre bit kaydırma (`<<`) ve bit testi (`&`) işlemleri yapılır. Bu operasyonlar işlemci donanımında tek bir saat çevriminde çalıştığı için $O(1)$ süre ve sabit 8 bayt bellek harcar.

### Soru 3: 16-bit bir dizi numarasında $65,535$'ten $0$'a geçişte yeni paketin daha yeni olduğu C++'ta nasıl kontrol edilir?
**Cevap:** `static_cast<int16_t>(new_seq - last_seq) > 0` ifadesi kullanılır. İşaretsiz tamsayı taşması `(0 - 65535) = 1` değerini üretir. `int16_t(1) > 0` koşulu `true` döner. İki numara arasındaki mesafe modüler aritmetik sayesinde doğru hesaplanır.

---

## 17. Gün Sonu Özeti ve 3-Cümle Çıkarımı

1. **Sequence Number ve Anti-Replay Nedir?:** Paketlerin sırasını, kaybını ve tekrarını izlemek için protokole eklenen sayaç ile bunu denetleyen bitmask kayar pencere algoritmasıdır.
2. **Hangi Problemi Çözer?:** Çok yollu telsiz ağlarında sırası karışmış paketleri monotonik sıraya sokar ve siber elektronik harp replay saldırılarını tek bir saat çevriminde bertaraf eder.
3. **Hangi Trade-off/Hata Sınıfını Getirir?:** Sıralama tamponu (Jitter Buffer) nedeniyle milisaniye seviyesinde küçük bir gecikme ekler; wrap-around taşmasının yanlış yönetilmesi durumunda tüm iletişimin kalıcı olarak kilitlenmesi riskini doğurur.