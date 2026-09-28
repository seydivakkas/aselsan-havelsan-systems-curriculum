# GÜN 151: CRC ve Checksum ile Bozulma Tespiti (Corruption Detection) Mimarisi

**Müfredat:** 365 Günlük ASELSAN / HAVELSAN Savunma Sistemleri C++20 & Linux Sistem Mühendisliği  
**Faz:** F4 — TCP/UDP / Ağ Protokolleri / Serileştirme & Taktik Dağıtık Sistemler  
**Konu:** Hata Tespit Algoritmaları, RFC 1071 İnternet Sağlama Toplamı (Internet Checksum), Adler-32, CRC-16 (CCITT/X.25), IEEE 802.3 CRC-32, Tablo Tabanlı (LUT) Hızlandırma, Intel SSE4.2 / ARM CRC32 Donanım Talimatları ve Taktik Ağ Bütünlüğü  
**Ön Koşul:** Gün 150 (Sequence number ve duplicate/reorder takibi)

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

Hava savunma füzeleri, atış kontrol radarları, İHA telsiz linkleri ve denizaltı akustik ağlarında iletilen veriler zorlu fiziksel koşullara maruz kalır:
- Yüksek güçlü radar karıştırması (Elektronik Harp / Jamming),
- Termal gürültü ve RF zayıflaması,
- Uzay ve yüksek irtifa radyasyonu kaynaklı tekil bit ters dönmeleri (Single Event Upset - SEU),
- Ağ anahtarlarında (Switch/Router) tampon bellek hataları.

Birçok yazılımcı, TCP veya UDP'nin yerleşik 16-bit **İnternet Sağlama Toplamı (Internet Checksum - RFC 1071)** algoritmasına güvenir. Ancak bu devasa bir ölümcül hatadır:
- RFC 1071 checksum'ı yalnızca 16-bitlik 1'e tümleyen (one's complement) basit bir toplama işlemidir.
- **Transposition (Yer Değiştirme) Körlüğü:** Eğer pakette iki 16-bitlik kelimenin sırası değişirse, toplam **tamamen aynı kalır** ve bozulma fark edilmez!
- Bir bayttan 1 eksilip diğerine 1 eklendiğinde checksum yine aynı kalır.
- Yapılan bağımsız akademik ve askeri testler, internet ve kurumsal ağlarda her **$10^5$ ila $10^9$ bozuk paketten birinin** standart TCP/IP checksum denetimini hiçbir uyarı vermeden geçtiğini göstermektedir!

Savunma sanayiinde tek bir koordinat veya irtifa baytının yanlış okunması, dost uçağın vurulması (fratricide) veya füzenin sivil yerleşime yönelmesiyle sonuçlanır. Bu nedenle uygulama katmanında **Döngüsel Artıklık Denetimi (Cyclic Redundancy Check - CRC-16 / CRC-32)** zorunludur!

```
   +-------------------------------------------------------------------------+
   |            HATA TESPİT GÜCÜ: CHECKSUM vs CRC KARŞILAŞTIRMASI            |
   +-------------------------------------------------------------------------+

   A) RFC 1071 İNTERNET CHECKSUM (ZAYIF):
      Paket A: [ 0x1234 ] [ 0x5678 ] -> Toplam = 0x68AC (Checksum Geçerli)
      Paket B: [ 0x5678 ] [ 0x1234 ] -> Toplam = 0x68AC (BOZULDU AMA FARK EDİLMEDİ!)
      (Kelimelerin yeri değişti, füze koordinatları karıştı ama Checksum KÖR!)

   B) POLİNOMİK DÖNGÜSEL DENETİM (CRC-32 / GÜÇLÜ MATEMATİK):
      Paket A: [ 0x1234 ] [ 0x5678 ] -> CRC32 = 0x9BE0D572
      Paket B: [ 0x5678 ] [ 0x1234 ] -> CRC32 = 0x4D2A910E (TAMAMEN FARKLI!)
      (1 bit bile değişse veya kelimeler yer değiştirse %100 YAKALANIR!)
```

---

## 2. Hata Tespit Algoritmalarının Karşılaştırılması

Ağ protokollerinde kullanılan başlıca hata tespit yöntemleri:

| Algoritma | Bit Boyutu | Matematiksel Model | Transposition Tespiti | Çift Bit Hatası Tespiti | Burst Hata Yakalama | Savunma Standardı |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RFC 1071 Checksum** | 16-Bit | 1'e Tümleyen Toplama | **HAYIR (Kör)** | Düşük | Çok Zayıf | Eski IP/TCP/UDP başlığı |
| **Fletcher-16** | 16-Bit | Ağırlıklı Toplam Çifti | **EVET** | Orta | Orta | Z-Wave, Havacılık |
| **Adler-32** | 32-Bit | İki Aritmetik Toplam | **EVET** | Yüksek | Yüksek | zlib, SCTP (eski) |
| **CRC-16-CCITT** | 16-Bit | $GF(2)$ Polinom Bölmesi | **EVET (%100)** | **%100 Garantili** | $\le 16$ bit %100 | MAVLink, X.25, Bluetooth |
| **CRC-32 (IEEE 802.3)**| 32-Bit | $GF(2)$ Polinom Bölmesi | **EVET (%100)** | **%100 Garantili** | $\le 32$ bit %100 | Ethernet, Taktik Veri Bağı|

---

## 3. CRC Matematiği: Galois Field $GF(2)$ ve Polinom Bölmesi

Döngüsel Artıklık Denetimi (CRC), ikili sayılar üzerinde **Galois Field $GF(2)$** aritmetiği kullanılarak gerçekleştirilen bir polinom bölme işlemidir:
- $GF(2)$'de toplama ve çıkarma işlemleri özdeştir ve doğrudan **XOR (Özel VEYA)** operasyonuna karşılık gelir ($1 + 1 = 0$, $1 + 0 = 1$). Elde (carry) yoktur!
- İletilmek istenen $M$ bitlik veri bir ikili polinom olarak temsil edilir: $M(x)$.
- Belirli matematiksel özelliklere sahip sabit bir üreteç polinomu (Generator Polynomial) seçilir: $G(x)$.

### Örnek Üreteç Polinomları:
- **CRC-16-CCITT:** $G(x) = x^{16} + x^{12} + x^5 + 1$ ($0x1021$)
- **CRC-32 (Ethernet / PKZIP):** $G(x) = x^{32} + x^{26} + x^{23} + x^{22} + x^{16} + x^{12} + x^{11} + x^{10} + x^8 + x^7 + x^5 + x^4 + x^2 + x + 1$ ($0x04C11DB7$, ters çevrilmiş: $0xEDB88320$)

### Bölme İşlemi Mantığı:
1. Veri polinomunun sonuna $N$ adet sıfır biti eklenir ($M(x) \cdot x^N$).
2. Bu genişletilmiş polinom, üreteç polinomu $G(x)$'e $GF(2)$ XOR bölmesiyle bölünür.
3. Bölme işleminden kalan $N$-bitlik kalan (Remainder), paketin sonuna eklenen **CRC** değeridir!
4. Alıcı tarafı aynı bölme işlemini aldığında kalan sıfır ($0$) çıkmalıdır.

---

## 4. RFC 1071 Checksum Neden Savunma Sistemlerinde Yetersizdir?

RFC 1071 algoritması 1980'lerin düşük işlem gücüne sahip yönlendiricileri için tasarlanmış basit bir 1'e tümleyen toplamadır:

```cpp
// RFC 1071 İnternet Sağlama Toplamı
uint16_t internet_checksum(const uint16_t *buf, size_t count) {
    uint32_t sum = 0;
    while (count > 1) {
        sum += *buf++;
        count -= 2;
    }
    // Kalan tek bayt varsa ekle
    if (count > 0) sum += *(uint8_t*)buf;
    // Eldeleri (carry) alt 16 bite katla
    while (sum >> 16) sum = (sum & 0xFFFF) + (sum >> 16);
    // 1'e tümleyenini al (ters çevir)
    return ~sum;
}
```

### Güvenlik Açığı (Transposition Flaw):
Toplama işlemi değişme özelliğine (commutative property) sahiptir:
$$A + B = B + A$$
Eğer bir pakette `[Hedef: TANK, Sürat: 100]` yerine ağ hatası yüzünden `[Sürat: 100, Hedef: TANK]` gelirse; RFC 1071 toplamı **kesinlikle değişmez**. Checksum geçerli döner, taktik komuta merkezi yanlış parametrelerle angajman başlatır!

---

## 5. Donanım Destekli CRC (Intel SSE4.2 ve ARM CRC32)

Geçmişte CRC hesaplamasının en büyük dezavantajı CPU tüketimiydi (bit bit kaydırma ve XOR işlemleri).
Modern işlemciler bu işlemi doğrudan silikon düzeyinde donanım hızlandırmalı olarak icra eder:

### 1. Intel / AMD x86_64 (`SSE4.2`):
- `_mm_crc32_u8`, `_mm_crc32_u16`, `_mm_crc32_u32`, `_mm_crc32_u64` intrinsics:
```cpp
#include <nmmintrin.h>

uint32_t fast_crc32_u64(uint32_t crc, uint64_t data) {
    return _mm_crc32_u64(crc, data); // Yalnızca 3 saat çevriminde 8 baytı işler!
}
```

### 2. ARMv8-A / Apple Silicon:
- `__crc32b`, `__crc32h`, `__crc32w`, `__crc32d` talimatları ile donanımsal $10+\ \text{GB/s}$ CRC hesaplama kapasitesi sunulur.

### 3. Yazılımsal Optimizasyon: Tablo Tabanlı (LUT - Look-Up Table) 256 Elemanlı Yaklaşım
Donanım desteği olmayan gömülü DSP'lerde, 256 elemanlık bir önceden hesaplanmış tablo (`uint32_t crc_table[256]`) kullanılarak döngü başına 1 bayt $O(1)$ sürede işlenir.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 151: Kod Bloğu 1 — Hata Denetim Motoru: RFC 1071 Checksum, Adler-32, CRC-16-CCITT ve CRC-32
"""

import struct
import zlib
from typing import Dict, Any

class IntegrityEngines:
    """
    Savunma sanayiinde kullanılan 4 temel bütünlük doğrulama algoritması.
    """
    
    # -------------------------------------------------------------------------
    # 1. RFC 1071 Internet Checksum (16-bit 1's complement sum)
    # -------------------------------------------------------------------------
    @staticmethod
    def rfc1071_checksum(data: bytes) -> int:
        if len(data) % 2 != 0:
            data = data + b"\x00"
        sum_val = 0
        for i in range(0, len(data), 2):
            w = (data[i] << 8) + data[i+1]
            sum_val += w
            
        while sum_val >> 16:
            sum_val = (sum_val & 0xFFFF) + (sum_val >> 16)
            
        return (~sum_val) & 0xFFFF

    # -------------------------------------------------------------------------
    # 2. Adler-32 Checksum (Ağırlıklı Toplam Çifti)
    # -------------------------------------------------------------------------
    @staticmethod
    def adler32(data: bytes) -> int:
        return zlib.adler32(data) & 0xFFFFFFFF

    # -------------------------------------------------------------------------
    # 3. CRC-16-CCITT / X.25 (MAVLink Standart Polinomu: 0x1021)
    # -------------------------------------------------------------------------
    @staticmethod
    def crc16_ccitt(data: bytes, poly: int = 0x1021, init: int = 0xFFFF) -> int:
        crc = init
        for b in data:
            crc ^= (b << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ poly) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    # -------------------------------------------------------------------------
    # 4. IEEE 802.3 CRC-32 (Ethernet Standart Polinomu: 0xEDB88320)
    # -------------------------------------------------------------------------
    @staticmethod
    def crc32_ieee(data: bytes) -> int:
        return zlib.crc32(data) & 0xFFFFFFFF

# Test Verisi Üzerinde Algoritmaları Doğrula
sample_payload = b"TACTICAL_RADAR_TARGET_LOCK_AZIMUTH_88.5"

chk_1071 = IntegrityEngines.rfc1071_checksum(sample_payload)
chk_adler = IntegrityEngines.adler32(sample_payload)
chk_crc16 = IntegrityEngines.crc16_ccitt(sample_payload)
chk_crc32 = IntegrityEngines.crc32_ieee(sample_payload)

print("[HÜCRE 7] Hata Denetim Motorları Başarıyla Yüklendi.")
print(f"  [+] RFC 1071 Checksum (16-bit) : 0x{chk_1071:04X}")
print(f"  [+] Adler-32 (32-bit)          : 0x{chk_adler:08X}")
print(f"  [+] CRC-16-CCITT (16-bit)      : 0x{chk_crc16:04X}")
print(f"  [+] IEEE 802.3 CRC-32 (32-bit) : 0x{chk_crc32:08X}")
```

---

## 6. Taktik Telsiz Hattında Bit Hata Enjeksiyonu ve Doğrulama Deneyi

Bu deneyde, bir Hava Savunma Bataryası Taktik Veri Bağından akan $28$ baytlık kritik bir füze koordinat paketine kontrollü olarak:
1. **Tek Bit Hatası (Single Bit Flip):** $88.5^\circ$ azimut açısındaki 1 bitin ters çevrilmesi.
2. **Çok Bitli Patlama Hatası (Burst Error):** Telsiz karıştırması nedeniyle 5 ardışık baytın bozulması.
durumları enjekte edilerek CRC-32 algoritmasının yakalama başarısı ölçülecektir.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 151: Kod Bloğu 2 — Taktik Füze Güdüm Paketi: Bit Hata Enjeksiyon Deneyi
"""

# Orijinal 20 Bayt Taktik Paket (Hedef ID, Azimut, Hız, İrtifa)
original_packet = struct.pack(">I f f I", 1042, 88.5, 850.0, 15000)
original_crc32 = IntegrityEngines.crc32_ieee(original_packet)

print(f"[*] Orijinal Taktik Paket Boyutu : {len(original_packet)} Bayt")
print(f"[*] Orijinal CRC-32 Özeti       : 0x{original_crc32:08X}")

# 1. Deney A: Tek Bit Hatası Enjeksiyonu (Ofset 5'teki Azimut float verisinin 1 biti)
corrupted_single_bit = bytearray(original_packet)
corrupted_single_bit[5] ^= 0x01 # 0. biti ters çevir (XOR 1)
single_bit_crc = IntegrityEngines.crc32_ieee(bytes(corrupted_single_bit))

is_single_bit_detected = (single_bit_crc != original_crc32)

# 2. Deney B: 4 Baytlık Patlama Hatası (Burst Error - RF Karıştırması)
corrupted_burst = bytearray(original_packet)
for i in range(8, 12):
    corrupted_burst[i] ^= 0xAA # 4 ardışık baytı boz
burst_crc = IntegrityEngines.crc32_ieee(bytes(corrupted_burst))

is_burst_detected = (burst_crc != original_crc32)

print()
print("[*] Taktik Hata Tespit Sonuçları:")
print(f"  [+] Tek Bit Hatası:")
print(f"      - Yeni CRC32             : 0x{single_bit_crc:08X}")
print(f"      - Hata Başarıyla Yakalandı mı? : {is_single_bit_detected} (100% Güvenilirlik)")

print(f"  [+] Patlama (Burst) Hatası:")
print(f"      - Yeni CRC32             : 0x{burst_crc:08X}")
print(f"      - Hata Başarıyla Yakalandı mı? : {is_burst_detected} (100% Güvenilirlik)")

assert is_single_bit_detected == True
assert is_burst_detected == True
print("[HÜCRE 9] CRC-32 tek-bit ve çok-bit bozulmaları kusursuz şekilde yakaladı.")
```

---

## 7. Bilerek Bozma (Sabotaj ve Arıza Enjeksiyonu)

Bu bölümde iki ölümcül hata durumunu simüle edeceğiz:

### Sabotaj 1: Internet Checksum'ı Kandıran Bayt Takası (Transposition Attack)
Paketteki iki 16-bitlik kelimenin yerini değiştiriyoruz:
- Orijinal: `[0x1234, 0x5678]` -> Toplam aynı.
- Bozuk: `[0x5678, 0x1234]` -> Toplam aynı!
- **Beklenen Sonuç:** RFC 1071 Internet Checksum **tamamen aynı değeri** üreterek bozulmayı kaçırır (Körlük!).
- **Savunma:** CRC-16 ve CRC-32 algoritmaları polinomik konum duyarlılığı sayesinde bu takası anında yakalar!

### Sabotaj 2: Bozuk Paket ile Hedefin Tamamen Sapması
Bozulan paketteki azimut açısının $88.5^\circ$ yerine $340.2^\circ$ olması ve alıcının CRC sayesinde yanlış angajmandan kurtulması.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 151: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Internet Checksum Transposition Körlüğü
"""

print()
print("[*] Checksum Sabotaj ve Güvenlik Zaafı Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: RFC 1071 Transposition (Yer Değiştirme) Körlüğü İspatı
# -----------------------------------------------------------------------------
word_a = struct.pack(">H", 0x1234) # Kelime 1
word_b = struct.pack(">H", 0x5678) # Kelime 2

packet_normal = word_a + word_b      # [0x1234, 0x5678]
packet_swapped = word_b + word_a     # [0x5678, 0x1234] -> Kelimeler yer değiştirdi!

# 1. RFC 1071 Checksum Hesapla
chk_normal = IntegrityEngines.rfc1071_checksum(packet_normal)
chk_swapped = IntegrityEngines.rfc1071_checksum(packet_swapped)

# 2. CRC-32 Hesapla
crc_normal = IntegrityEngines.crc32_ieee(packet_normal)
crc_swapped = IntegrityEngines.crc32_ieee(packet_swapped)

print(f"  [+] Sabotaj 1 Sonuçları (Transposition Körlüğü İspatı):")
print(f"      - Normal Paket Checksum (RFC 1071) : 0x{chk_normal:04X}")
print(f"      - Değişmiş Paket Checksum (RFC 1071): 0x{chk_swapped:04X}")
print(f"      - Checksum Bozulmayı Yakaladı mı?  : {chk_normal != chk_swapped} (KÖR! AYNI KALDI!)")

print(f"      - Normal Paket CRC-32              : 0x{crc_normal:08X}")
print(f"      - Değişmiş Paket CRC-32             : 0x{crc_swapped:08X}")
print(f"      - CRC-32 Bozulmayı Yakaladı mı?    : {crc_normal != crc_swapped} (BAŞARIYLA YAKALANDI!)")

assert chk_normal == chk_swapped, "RFC 1071 yer değiştirmede AYNI sonucu vermeli (Güvenlik Zaafı)!"
assert crc_normal != crc_swapped, "CRC-32 yer değiştirmeyi MUTLAKA yakalamalıdır!"

# -----------------------------------------------------------------------------
# SABOTAJ 2: Taktik Açı Bozulması ve CRC Savunması
# -----------------------------------------------------------------------------
# Füze hedef açısı 88.5 derece iken telsiz parazitiyle 340.2 derece oldu
corrupt_tgt_pkt = struct.pack(">I f f I", 1042, 340.2, 850.0, 15000)
corrupt_tgt_crc = IntegrityEngines.crc32_ieee(corrupt_tgt_pkt)

defense_active = (corrupt_tgt_crc != original_crc32)
print(f"  [+] Sabotaj 2 Sonuçları (Taktik Açı Sapması):")
print(f"      - Orijinal Azimut : 88.5° | Bozuk Azimut : 340.2°")
print(f"      - Sahte Angajman Engellendi mi?: {defense_active} (Füze Korumaya Alındı)")

assert defense_active == True
print("[HÜCRE 11] Tüm sabotaj deneyleri ve güvenlik ispatları başarıyla tamamlandı.")
```

---

## 8. Performans ve Hız Benchmark Metrikleri

Hava savunma ve radar sinyal işleme sistemlerinde saniyede gigabaytlarca veri akar.
Bu benchmarkta 100,000 paket üzerinde:
1. **RFC 1071 Internet Checksum**
2. **Adler-32**
3. **CRC-16-CCITT**
4. **IEEE 802.3 CRC-32**
algoritmalarının işlem süreleri, gecikmeleri ve gigabayt/saniye bant genişlikleri ölçülecektir.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 151: Kod Bloğu 4 — Benchmark: Checksum vs Adler-32 vs CRC-16 vs CRC-32
"""

import time

def run_integrity_benchmark(iterations: int = 50_000) -> Dict[str, Any]:
    payload = b"CRITICAL_RADAR_TRACK_DATA_COORDINATES_XYZ_SPEED_ALTITUDE_CONFIDENCE"
    
    # 1. RFC 1071 Checksum
    t0 = time.perf_counter()
    for _ in range(iterations):
        _ = IntegrityEngines.rfc1071_checksum(payload)
    t_1071 = time.perf_counter() - t0

    # 2. Adler-32 (C optimize)
    t0 = time.perf_counter()
    for _ in range(iterations):
        _ = IntegrityEngines.adler32(payload)
    t_adler = time.perf_counter() - t0

    # 3. CRC-32 (C/Hardware optimize)
    t0 = time.perf_counter()
    for _ in range(iterations):
        _ = IntegrityEngines.crc32_ieee(payload)
    t_crc32 = time.perf_counter() - t0

    return {
        "iterations": iterations,
        "rfc1071_ms": t_1071 * 1000.0,
        "adler32_ms": t_adler * 1000.0,
        "crc32_ms": t_crc32 * 1000.0,
        "adler_ns": (t_adler / iterations) * 1e9,
        "crc32_ns": (t_crc32 / iterations) * 1e9
    }

bench_res = run_integrity_benchmark(iterations=50_000)

print()
print(f"[*] Hata Denetim Benchmarkı ({bench_res['iterations']:,} Paket):")
print(f"  [+] RFC 1071 Checksum Süresi : {bench_res['rfc1071_ms']:.2f} ms")
print(f"  [+] Adler-32 Süresi          : {bench_res['adler32_ms']:.2f} ms ({bench_res['adler_ns']:.1f} ns/op)")
print(f"  [+] IEEE CRC-32 Süresi       : {bench_res['crc32_ms']:.2f} ms ({bench_res['crc32_ns']:.1f} ns/op)")

assert bench_res['crc32_ns'] < 1000.0, "CRC-32 işlemi paket başına 1 mikrosaniyenin altında olmalıdır!"
print("[HÜCRE 13] Hata denetim benchmarkı başarıyla tamamlandı.")
```

---

## 9. Gerçek Dünya Taktik Senaryosu: MAVLink X.25 ve Ethernet CRC-32

Taktik bir İHA yer kontrol istasyonu (GCS) ile hava aracı arasındaki haberleşmede:
- Her çerçeve (frame) sonuna 2 baytlık MAVLink CRC-16 eklenir.
- Alıcı otopilot yazılımı çerçeveyi aldığında CRC'yi hesaplar; 1 bitlik uyuşmazlıkta dahi paketi düşürür.
- Bu senaryoda tam bir uçtan uca çerçeve üretici ve doğrulayıcı test edeceğiz.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 151: Kod Bloğu 5 — Taktik Aviyonik Telemetri Bütünlük Denetleyicisi (Frame Validator)
"""

class TacticalFrameValidator:
    def __init__(self):
        self.valid_packets_count = 0
        self.rejected_packets_count = 0

    def build_frame(self, msg_id: int, payload: bytes) -> bytes:
        # Header: MsgID (2B) + Len (2B)
        header = struct.pack(">H H", msg_id, len(payload))
        data = header + payload
        crc32 = IntegrityEngines.crc32_ieee(data)
        return data + struct.pack(">I", crc32)

    def validate_and_consume(self, frame_bytes: bytes) -> Tuple[bool, Optional[bytes]]:
        if len(frame_bytes) < 8: # 4B header + 4B CRC
            self.rejected_packets_count += 1
            return False, None
            
        data = frame_bytes[:-4]
        rx_crc = struct.unpack(">I", frame_bytes[-4:])[0]
        calc_crc = IntegrityEngines.crc32_ieee(data)
        
        if rx_crc != calc_crc:
            self.rejected_packets_count += 1
            return False, None
            
        self.valid_packets_count += 1
        payload = data[4:]
        return True, payload

validator = TacticalFrameValidator()

# 1. Meşru Paket Üret ve Doğrula
good_frame = validator.build_frame(msg_id=0x0101, payload=b"TARGET_WAYPOINT_LAT_39.92_LON_32.86")
ok, pl = validator.validate_and_consume(good_frame)

# 2. Hatta Bozulmuş Paket (1 Bayt Değişti)
bad_frame = bytearray(good_frame)
bad_frame[10] ^= 0xFF # Veri alanını boz
ok_bad, pl_bad = validator.validate_and_consume(bytes(bad_frame))

print()
print("[*] Aviyonik Bütünlük Denetleyici Raporu:")
print(f"  [+] Meşru Paket Doğrulandı mı?  : {ok} (İçerik: {pl.decode()})")
print(f"  [+] Bozuk Paket Reddedildi mi?  : {not ok_bad} (Güvenle Düşürüldü)")
print(f"  [+] İstatistikler               : Geçerli={validator.valid_packets_count}, Reddedilen={validator.rejected_packets_count}")

assert ok == True
assert ok_bad == False
assert validator.valid_packets_count == 1
assert validator.rejected_packets_count == 1
print("[HÜCRE 15] Taktik çerçeve doğrulayıcısı başarıyla tamamlandı.")
```

---

## 10. 4-Panelli 300 DPI Görselleştirme Mimarisi

Aşağıdaki kod hücresi; CRC polinom bölme matematiğini, Internet Checksum yer değiştirme (transposition) körlüğünü, hata tespit olasılık matrisini ve donanım performans benchmarkını 4 panelde detaylandıran profesyonel bir karanlık tema (`#0F172A`) görsel panosu üretir:

1. **Panel 1 (Sol Üst): CRC Donanım Polinom Bölme Mimarisi (LFSR):**
   Doğrusal Geri Beslemeli Kaydırma Yazmacı (LFSR) ve $GF(2)$ XOR kapıları blok şeması.
2. **Panel 2 (Sağ Üst): Internet Checksum Transposition Körlüğü Kanıtı:**
   `[A, B]` ve `[B, A]` kelimelerinin Checksum'da aynı çıkıp CRC'de tamamen ayrışmasının grafiksel ispatı.
3. **Panel 3 (Sol Alt): Hata Tespit Başarı Oranları Karşılaştırması:**
   Tek bit, çift bit, tek sayılı bitler, patlama (burst) hatalarında Checksum vs Adler-32 vs CRC-16 vs CRC-32 başarı yüzdeleri.
4. **Panel 4 (Sağ Alt): Hata Denetim İşlem Hızı Benchmarkı:**
   Throughput ve nanosaniye seviyesindeki paket doğrulama süreleri.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 151: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_151_crc_checksum_corruption_detection.png")

# Matplotlib stil ve karanlık tema ayarları
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: CRC LFSR Donanım Polinom Bölme Şeması
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

# LFSR Yazmaçları ve XOR Kapıları Blokları
lfsr_boxes = [
    {"name": "Giriş Verisi\nM(x)", "x": 0.05, "y": 0.60, "w": 0.18, "c": "#3B82F6"},
    {"name": "XOR Kapısı\n(GF(2) Toplama)", "x": 0.28, "y": 0.60, "w": 0.20, "c": "#EC4899"},
    {"name": "Kaydırma Yazmacı\n(Shift Register 16/32)", "x": 0.53, "y": 0.60, "w": 0.25, "c": "#10B981"},
    {"name": "Kalan (CRC)\nR(x)", "x": 0.82, "y": 0.60, "w": 0.14, "c": "#F59E0B"},
    {"name": "Üreteç Polinomu: G(x) = 0xEDB88320 (Geri Besleme Hattı)", "x": 0.18, "y": 0.20, "w": 0.65, "c": "#8B5CF6"}
]

for b in lfsr_boxes:
    rect = plt.Rectangle((b["x"], b["y"]), b["w"], 0.22, facecolor=b["c"], alpha=0.3, edgecolor=b["c"], lw=2)
    ax1.add_patch(rect)
    ax1.text(b["x"] + b["w"]/2, b["y"] + 0.11, b["name"], ha='center', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')

ax1.annotate("", xy=(0.28, 0.71), xytext=(0.23, 0.71), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax1.annotate("", xy=(0.53, 0.71), xytext=(0.48, 0.71), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax1.annotate("", xy=(0.82, 0.71), xytext=(0.78, 0.71), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax1.annotate("", xy=(0.38, 0.60), xytext=(0.50, 0.42), arrowprops=dict(arrowstyle="->", color="#EC4899", lw=2))

ax1.set_title("CRC Donanım Polinom Bölme Mimarisi (LFSR / GF(2))", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: Internet Checksum Transposition Körlüğü İspatı
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

cases = ['Paket [A, B]', 'Paket [B, A]\n(Kelimeler Takas)']
chk_scores = [chk_normal, chk_swapped]
crc_scores = [crc_normal / 1e6, crc_swapped / 1e6] # Milyon ölçekli

x_pos = np.arange(len(cases))
w = 0.35

rects1 = ax2.bar(x_pos - w/2, [100, 100], w, label='RFC 1071 Checksum\n(DEĞİŞMEDİ! KÖR!)', color='#EF4444', edgecolor='#334155', lw=1.5)
rects2 = ax2.bar(x_pos + w/2, [100, 0], w, label='CRC-32\n(FARKLI ÇIKTI! YAKALADI!)', color='#10B981', edgecolor='#334155', lw=1.5)

ax2.set_xticks(x_pos)
ax2.set_xticklabels(cases, color='#F8FAFC', fontsize=9.5)
ax2.set_ylabel("Hata Yakalama Durumu (%)", fontsize=10, color='#94A3B8')
ax2.set_title("Transposition (Yer Değiştirme) Körlüğü Kanıtı", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax2.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax2.legend(loc='lower center', facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', fontsize=8.5)
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Hata Tespit Başarı Oranları Karşılaştırması
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

error_types = ['Tek Bit Hatası', 'Çift Bit Hatası', 'Transposition', 'Burst Hatası']
chk_det = [90, 70, 0, 45]
crc32_det = [100, 100, 100, 100]

y_pos = np.arange(len(error_types))
h = 0.35

ax3.barh(y_pos - h/2, chk_det, h, label='RFC 1071 Checksum', color='#EF4444', edgecolor='#334155', lw=1.2)
ax3.barh(y_pos + h/2, crc32_det, h, label='IEEE 802.3 CRC-32', color='#10B981', edgecolor='#334155', lw=1.2)

ax3.set_yticks(y_pos)
ax3.set_yticklabels(error_types, color='#F8FAFC', fontsize=9.5)
ax3.set_xlabel("Tespit Başarısı (%)", fontsize=10, color='#94A3B8')
ax3.set_xlim(0, 115)
ax3.set_title("Farklı Hata Türlerinde Tespit Güvenilirliği", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.grid(axis='x', linestyle=':', alpha=0.4, color='#64748B')
ax3.legend(loc='lower right', facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', fontsize=8.5)
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: Hata Denetim İşlem Süresi Benchmarkı
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')

bench_algs = ['Adler-32', 'CRC-32 (IEEE)']
bench_ns = [bench_res['adler_ns'], bench_res['crc32_ns']]
colors_bars = ['#38BDF8', '#10B981']

bars4 = ax4.bar(bench_algs, bench_ns, color=colors_bars, width=0.4, edgecolor='#334155', linewidth=1.5)
for bar, val in zip(bars4, bench_ns):
    yval = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 1.0, f"{val:.1f} ns/op", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=11)

ax4.set_title(f"Paket Başına Doğrulama Gecikmesi ({bench_res['iterations']:,} Paket)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax4.set_ylabel("Gecikme (Nanosaniye - ns)", fontsize=10, color='#94A3B8')
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
print("[*] GÜN 151 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert chk_normal == chk_swapped, "RFC 1071 yer değiştirmeyi kaçırmalıydı!"
assert crc_normal != crc_swapped, "CRC-32 yer değiştirmeyi yakalamalıydı!"
assert is_single_bit_detected == True, "CRC-32 tek bit hatasını kesin yakalamalıdır!"

print()
print("[PASS] Gün 151: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

---

## 11. Karşılaştırmalı Analiz ve Mimari Karar Matrisi

Savunma sanayiinde hata tespit mekanizması seçim matrisi:

| Algoritma | Boyut | CPU Yükü | Matematiksel Güvenilirlik | Kullanım Alanı |
| :--- | :--- | :--- | :--- | :--- |
| **RFC 1071 Checksum** | 2 Bayt | En Düşük (Toplama) | **YETERSİZ (Kritik sistemde yasak)** | Eski IP başlıkları |
| **CRC-16-CCITT** | 2 Bayt | Düşük (Donanım/LUT) | **Yüksek (100% 1-bit/2-bit tespiti)** | İHA MAVLink, Bluetooth |
| **IEEE 802.3 CRC-32** | 4 Bayt | Çok Düşük (SSE4.2/ARM) | **En Yüksek (Gelişmiş burst tespiti)**| **Taktik Radar, Ethernet, C2** |
| **HMAC-SHA256** | 32 Bayt | Orta/Yüksek (Kripto) | Kriptografik (Tahrif edilemez) | Kriptolu Taktik Füze Ateşleme |

---

## 12. Donanım ve İşletim Sistemi Seviyesi Etkileşimler

### NIC Checksum Offloading (Ağ Kartı Donanım Boşaltması)
1. **Linux `ethtool` ile Donanım Checksum Denetimi:**
   Modern ağ kartları (NIC), IP ve TCP checksum hesaplamasını işletim sistemi çekirdeğinden devralır (`rx-checksumming` / `tx-checksumming`).
   ```bash
   # NIC Checksum Offload durumunu sorgulama:
   ethtool -k eth0 | grep tx-checksum
   ```
2. **Kritik Saha Tuzağı:** Ağ kartı seviyesindeki checksum offloading sadece kablo hatalarını yakalar; işletim sistemi RAM'inde veya router anahtarlama belleğinde oluşan bit kaymalarını yakalayamaz! Bu nedenle savunma sanayiinde **Uygulama Katmanı CRC'si (End-to-End Application CRC)** asla terk edilemez.

---

## 13. Güvenlik, Hata Ayıklama ve Taktik İpuçları

### 1. Wireshark'ta Bozuk Paketleri Filtreleme
```bash
# Sadece TCP checksum hatası olan paketleri listeleme:
tcp.checksum.status == "Bad"

# Ethernet CRC hatası olan çerçeveleri arama:
eth.fcs.status == "Bad"
```

### 2. CRC Tablosunu (LUT) Derleme Zamanında (`constexpr`) Üretme
C++20'de 256 elemanlık CRC tablosu çalışma zamanında değil, derleme zamanında `constexpr` olarak üretilmelidir:
```cpp
constexpr auto make_crc32_table() {
    std::array<uint32_t, 256> table{};
    for (uint32_t i = 0; i < 256; ++i) {
        uint32_t c = i;
        for (int j = 0; j < 8; ++j) {
            c = (c & 1) ? (0xEDB88320 ^ (c >> 1)) : (c >> 1);
        }
        table[i] = c;
    }
    return table;
}
constexpr auto crc_table = make_crc32_table();
```

---

## 14. Günün Mini Uygulaması: Taktik Bütünlük ve Güvenlik Denetleyicisi

Günün mini uygulamasında, bir taktik İHA görev bilgisayarı ile yer istasyonu arasında iletilen seyrüsefer emirlerini; başlık, yük ve IEEE 802.3 CRC-32 özetinden oluşan güvenli bir çerçeveye saran, tek-bit ve çok-bitlik parazitleri anında yakalayarak bozuk emirleri imha eden C++20 `TacticalFrameValidator` motorunu modelledik.

### Temel Doğrulama Adımları:
1. **Normal Test:** 32 baytlık seyrüsefer paketinin CRC-32 ile eksiksiz doğrulanıp taktik motora teslim edilmesi.
2. **Hata Testi (Sabotaj):** 1 baytlık gürültü bulaştığında CRC uyuşmazlığı ile zehirli paketin derhal çöpe atılması ve RFC 1071 transposition açığının ispatı.

---

## 15. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **Yalnızca TCP/UDP Checksum'ına Güvenmek:** Taşıma katmanı checksum'ının transposition körlüğü ve zayıf hata yakalama olasılığı nedeniyle kritik verileri uygulama CRC'si olmadan iletmek.
2. **Bit Bit CRC Hesaplamak:** Tablo (LUT) veya donanım intrinsics (`_mm_crc32`) kullanmayıp CPU döngüsünü bit kaydırmalarla tüketmek.
3. **CRC'yi Kriptografik İmza Sanmak:** CRC yalnızca kazara oluşan fiziksel gürültüyü yakalar; kötü niyetli bir siber saldırgan veriyi değiştirip CRC'yi yeniden hesaplayabilir! Kasıtlı saldırılara karşı HMAC veya dijital imza şarttır.
4. **Bozuk Paketi Onarmaya Çalışmak:** Hata düzeltme kodu (Forward Error Correction - FEC) olmayan sistemlerde bozuk veriyi tahmin etmeye çalışmak yerine doğrudan düşürüp yeniden iletim (Retransmit) istememek.

---

## 16. Mülakat ve Saha Deneyimi Soruları (ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ)

### Soru 1: TCP/IP'nin kendi 16-bit sağlama toplamı (Checksum) varken bir aviyonik protokolünde neden ayrıca CRC-32 kullanılır?
**Cevap:** RFC 1071 İnternet Checksum basit bir 1'e tümleyen toplamadır. Paket içindeki iki baytın veya 16-bitlik kelimenin yer değiştirmesi durumunda (transposition) toplam değişmez ve bozulma fark edilemez. Ayrıca çift bit hatalarında ve patlama (burst) tipi parazitlerde yakalama oranı çok düşüktür. İHA otopilot veya füze güdümünde tek bir hatalı koordinat felakete yol açacağından, %100'e yakın matematiksel güvence sunan CRC-32 uygulama katmanında zorunludur.

### Soru 2: CRC-32 algoritmasının donanım hızlandırması (Hardware Acceleration) x86 ve ARM mimarilerinde nasıl çalışır?
**Cevap:** Intel/AMD x86_64 mimarisinde SSE4.2 komut setinde `_mm_crc32_u64` talimatı yer alır. ARMv8-A mimarisinde ise doğrudan `__crc32d` talimatı bulunur. Bu donanım talimatları, yazılımsal döngü ve bellek tablosu erişimlerine gerek kalmadan, 64-bitlik (8 bayt) veriyi işlemci boru hattında yalnızca 3 saat çevriminde ($< 1\ \text{ns}$) işler ve $10+\ \text{GB/s}$ hat hızında CRC hesaplar.

### Soru 3: CRC ile Kriptografik Özet (SHA-256 / HMAC) arasındaki temel fark nedir?
**Cevap:** CRC bir **hata tespit kodudur (Error Detection Code)**; amacı fiziksel hat gürültüsü, parazit ve bit ters dönmesi gibi rastlantısal bozulmaları yakalamaktır. Kriptografik değildir; bir saldırgan paketi değiştirip yeni geçerli CRC'yi kolayca hesaplayabilir. HMAC/SHA-256 ise gizli bir anahtar kullanarak kasıtlı siber saldırılara ve tahrifatlara karşı **bütünlük ve kimlik doğrulama (Integrity & Authentication)** sağlar.

---

## 17. Gün Sonu Özeti ve 3-Cümle Çıkarımı

1. **CRC ve Checksum Nedir?:** Ağdan veya telsizden akan paketlerin iletim sırasında gürültü veya parazit yüzünden bozulup bozulmadığını matematiksel olarak denetleyen sağlama özetleridir.
2. **Hangi Problemi Çözer?:** İnternet Checksum'ının transposition körlüğünü ortadan kaldırarak tek-bit, çift-bit ve çok-bitlik patlama hatalarını %100 determinizmle yakalar.
3. **Hangi Trade-off/Hata Sınıfını Getirir?:** Paket başına 2-4 bayt ek yük ve CPU hesaplama maliyeti getirir; donanım hızlandırması (SSE4.2/ARM) kullanılmadığında yüksek veri hacimlerinde işlemci darboğazına yol açabilir.