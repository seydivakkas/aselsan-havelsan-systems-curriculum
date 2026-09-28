# GÜN 153: Serileştirme Mimarisi: Metin Tabanlı (JSON) vs İkili (Binary) Formatlar

**Müfredat:** 365 Günlük ASELSAN / HAVELSAN Savunma Sistemleri C++20 & Linux Sistem Mühendisliği  
**Faz:** F4 — TCP/UDP / Ağ Protokolleri / Serileştirme & Taktik Dağıtık Sistemler  
**Konu:** Veri Serileştirme ve Ayrıştırma (Serialization & Deserialization), Metin Tabanlı (JSON, XML) vs İkili (Raw Binary Struct, BSON, FlatBuffers) Temsil, Bant Genişliği Ek Yükü, CPU Sayısal Dönüşüm Maliyeti (ASCII <-> IEEE 754), Kayan Nokta Hassasiyet Kaybı, Gerçek Zamanlı Determinizm ve Sıfır Kopyalama (Zero-Copy)  
**Ön Koşul:** Gün 152 (Protocol versioning ve backward compatibility)

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

Modern yazılım dünyasında web ve kurumsal sistemler, insan tarafından okunabilirliği (human-readability) ve esnekliği nedeniyle neredeyse tamamen **JSON (JavaScript Object Notation)** formatı üzerine kurulmuştur. Ancak hava savunma radarları, taktik füzeler, sualtı akustik ağları ve İHA atış kontrol sistemlerinde durum taban tabana zıttır.

Bir savaş uçağının Görev Bilgisayarı (Mission Computer) veya bir AESA Radar işlemcisi saniyede $10,000$ adet hedef izleme paketi üretir:
- **Metin Tabanlı (JSON) Yaklaşımı:** Her mesajda `"target_id": 1042, "azimuth": 88.5412, "elevation": 12.301, "range_meters": 45210.8` gibi anahtar metinleri (key strings) ağa basılır. 4 baytlık bir `float` sayısı, metin olarak `"88.541200"` şeklinde $11$ bayta dönüşür. Ayrıştırmak için CPU, metni karakter karakter taramak, string heap bellekleri tahsis etmek (`malloc`) ve karmaşık ASCII-to-Float dönüşümleri (`strtod`, `atof`) yapmak zorundadır.
- **İkili (Binary) Yaklaşımı:** Bellekteki 32-bit float veya 64-bit int verisi, sıfır kopyalama ve sıfır dönüşümle doğrudan ağ arayüzüne basılır. 4 bayt kabloda da tam olarak $4$ bayttır. Ayrıştırma maliyeti CPU için neredeyse **sıfırdır** ($< 10\ \text{ns}$).

```
   +-------------------------------------------------------------------------+
   |             TELDEKİ VERİ (ON-THE-WIRE): JSON vs İKİLİ (BINARY)          |
   +-------------------------------------------------------------------------+

   A) JSON FORMATI (128 Bayt):
      {"id":1042,"lat":39.925000,"lon":32.866000,"alt":1200.5,"spd":320.4}
      [Metin Tabanlı | Anahtarlar Tekrarlanır | ASCII Dönüşüm Gerekir | %500 Boyut Fazlası]

   B) İKİLİ (RAW BINARY STRUCT) FORMATI (20 Bayt):
      [ 0x00000412 ] [ 0x02613568 ] [ 0x01F58090 ] [ 0x44961000 ] [ 0x43A03333 ]
      |-- id: 4B --| |-- lat: 4B --| |-- lon: 4B --| |-- alt: 4B --| |-- spd: 4B --|
      [Saf İkili | Sıfır Fazlalık | Donanımsal Hizalama | Sıfır CPU Dönüşümü | %100 Determinizm]
```

---

## 2. JSON vs Binary: Veri Temsili ve Bellek Anatomisi

Haberleşmede taşınan bir telemetri paketinin iki farklı formatta bellek yerleşimi ve bayt maliyeti:

| Özellik | Metin Tabanlı (JSON) | İkili (Raw Binary Struct / Protobuf) | Savunma Mühendisliği Etkisi |
| :--- | :--- | :--- | :--- |
| **İnsan Tarafından Okunabilirlik** | Mükemmel (Düz metin editörü ile okunur) | Yok (Hex dump / Dissector gerektirir) | JSON test ve GUI'de avantajlıdır |
| **Bant Genişliği Verimliliği** | Çok Düşük (%400 - %800 ek yük) | **Maksimum (Saf bayt, sıfır fazlalık)** | Taktik telsiz ve uydu linklerinde hayati |
| **Ayrıştırma (Parsing) Süresi** | Mikrosaniye seviyesi ($2,000 - 15,000\ \text{ns}$) | **Nanosaniye seviyesi ($5 - 50\ \text{ns}$)** | 1000 Hz atış kontrol döngüsünü belirler |
| **Sayısal Hassasiyet (Precision)** | Riskli (String float yuvarlama hataları) | **Kusursuz (IEEE 754 bit-exact)** | Güdüm füzelerinde hedef şaşmasını önler |
| **Bellek Tahsisi (Allocation)** | Dinamik heap tahsisi (`malloc` / `std::string`) | **Sıfır heap (Stack veya In-place buffer)** | Jitter engelleme, Real-Time OS determinizmi |
| **Şema Güvenliği (Typing)** | Zayıf / Dinamik (Çalışma anında patlar) | **Statik / Derleme Anında Katı Tip Denetimi**| Tip uyumsuzluğu derleyicide yakalanır |

---

## 3. Sayısal Dönüşüm Maliyeti (ASCII vs Native) ve Kayan Nokta Hassasiyet Kaybı

### 1. Sayısal Dönüşüm (String-to-Float) CPU Darboğazı:
Bir JSON belgesinde `"altitude": 14500.875` ifadesini ayrıştırmak için ayrıştırıcı:
1. `"altitude"` string anahtarını hash'lemeli veya tablodan aramalıdır.
2. `1`, `4`, `5`, `0`, `0`, `.`, `8`, `7`, `5` karakterlerini tek tek taramalıdır.
3. Her basamak için $10$ ile çarpıp eklemeli, nokta görünce ondalık böleni işletmelidir.
4. Mantissa ve exponent hesaplayıp IEEE 754 32-bit kayan noktalı sayıya dönüştürmelidir.
Bu işlem, modern bir CPU'da yaklaşık **80 ila 150 saat çevrimi (clock cycle)** tüketir.  
İkili formatta ise bu süre **0 saat çevrimidir**; çünkü gelen 4 bayt zaten IEEE 754 formatındadır!

### 2. Kayan Nokta ve Koordinat Hassasiyet Kaybı:
Dünya coğrafi koordinat sisteminde $1^\circ$ enlem yaklaşık $111,320\ \text{metre}$ mesafeye karşılık gelir.
Bir hedef koordinatını JSON string'e dönüştürürken (`sprintf("%.4f")` veya standart JSON float kesmesi):
- Orijinal Enlem: `39.92548231°`
- JSON'a Yazılan: `"39.9255°"` (4 basamağa yuvarlandı)
- Yeryüzündeki Sapma Mesafesi: $|39.92548231 - 39.9255| \times 111,320 \approx \mathbf{1.97\ \text{metre}}!$
Nokta atışı güdüm mühimmatlarında (Lazer / GPS / INS Güdümlü Füze) $2$ metrelik bir sapma, hedefin tamamen ıskalanması veya sivil kayıplara (collateral damage) yol açabilir! İkili formatta mikro-derece ($10^{-6}$) tamsayı ile sapma sıfırdır.

---

## 4. Gerçek Zamanlı Sistemlerde Determinizm ve Dinamik Bellek (Heap vs Zero-Copy)

Havacılık (DO-178C Level A) ve savunma standartlarında **Dinamik Bellek Ayırma (`malloc`, `free`, `new`, `delete`)** uçuş kritik döngülerde **kesinlikle yasaktır**:
1. **Bellek Parçalanması (Heap Fragmentation):** Saatlerce çalışan bir füze veya İHA görev bilgisayarında sürekli `malloc` yapılması belleği parçalar ve günün sonunda `Out of Memory (OOM)` çöküşüne yol açar.
2. **Determinizm Kaybı (Jitter):** `malloc` işleminin tam olarak kaç mikrosaniye süreceği bilinemez (işletim sistemi bellek yöneticisi serbest blok aramak için listeleri tarar). Bir döngü $20\ \mu\text{s}$ sürerken bir diğeri $4,000\ \mu\text{s}$ sürebilir. Bu durum 100 Hz uçuş kontrol döngüsünü öldürür.

### JSON Kütüphanelerinin Tuzağı:
`nlohmann/json` veya benzeri standart JSON kütüphaneleri, nesneleri `std::string`, `std::vector` ve `std::map` içinde tutar. Tek bir JSON mesajının çözülmesi **onlarca dinamik bellek tahsisine** yol açar!
Buna karşın ikili protokoller:
- Statik veya önceden ayrılmış tamponlar (`std::array`, `char buffer[256]`) kullanır.
- `std::span` ile sıfır bellek kopyalama (Zero-Copy) sağlar.

---

## 5. C++20 ile Serileştirme: JSON vs Raw Struct / std::span

C++20'de iki yaklaşımın kod seviyesindeki mimarisi:

### Yaklaşım A: JSON (Metin Tabanlı - nlohmann/json)
```cpp
#include <nlohmann/json.hpp>
using json = nlohmann::json;

std::string serialize_json(const RadarTrack& track) {
    json j;
    j["id"] = track.id;
    j["azimuth"] = track.azimuth;
    j["range"] = track.range;
    return j.dump(); // std::string heap allocation + ASCII formatting
}
```

### Yaklaşım B: İkili (C++20 std::span & memcpy)
```cpp
#include <span>
#include <cstring>

void serialize_binary(const RadarTrack& track, std::span<uint8_t> out_buf) {
    // Sıfır heap, derleme anında boyut denetimi, doğrudan bellek kopyası
    static_assert(sizeof(RadarTrack) == 20);
    std::memcpy(out_buf.data(), &track, sizeof(RadarTrack));
}
```

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 153: Kod Bloğu 1 — Serileştirme Motoru: JSON vs İkili (Raw Binary) Paket Üretici
"""

import json
import struct
import zlib
from typing import Dict, Any, Tuple

class TacticalTarget:
    """
    Hava savunma radarı tarafından tespit edilen kritik hedef kaydı.
    """
    # İkili Format: target_id (uint32), azimuth (float), elevation (float), range_m (float), speed_mps (float)
    BINARY_FORMAT = ">I f f f f"
    BINARY_SIZE = struct.calcsize(BINARY_FORMAT) # 20 Bayt

    def __init__(self, target_id: int, azimuth: float, elevation: float, range_m: float, speed_mps: float):
        self.target_id = target_id
        self.azimuth = azimuth
        self.elevation = elevation
        self.range_m = range_m
        self.speed_mps = speed_mps

    # 1. Metin Tabanlı Serileştirme (JSON)
    def to_json_bytes(self) -> bytes:
        data = {
            "target_id": self.target_id,
            "azimuth": self.azimuth,
            "elevation": self.elevation,
            "range_m": self.range_m,
            "speed_mps": self.speed_mps
        }
        # Boşluksuz kompakt JSON
        return json.dumps(data, separators=(',', ':')).encode('utf-8')

    @classmethod
    def from_json_bytes(cls, raw_bytes: bytes) -> 'TacticalTarget':
        data = json.loads(raw_bytes.decode('utf-8'))
        return cls(
            target_id=data["target_id"],
            azimuth=float(data["azimuth"]),
            elevation=float(data["elevation"]),
            range_m=float(data["range_m"]),
            speed_mps=float(data["speed_mps"])
        )

    # 2. İkili Serileştirme (Raw Binary Struct)
    def to_binary_bytes(self) -> bytes:
        return struct.pack(self.BINARY_FORMAT, self.target_id, self.azimuth, self.elevation, self.range_m, self.speed_mps)

    @classmethod
    def from_binary_bytes(cls, raw_bytes: bytes) -> 'TacticalTarget':
        target_id, az, el, rng, spd = struct.unpack(cls.BINARY_FORMAT, raw_bytes[:cls.BINARY_SIZE])
        return cls(target_id, az, el, rng, spd)

print("[HÜCRE 7] Taktik Serileştirme Motoru Başarıyla Yüklendi.")
sample = TacticalTarget(target_id=1042, azimuth=88.5412, elevation=12.301, range_m=45210.8, speed_mps=320.4)
json_b = sample.to_json_bytes()
bin_b = sample.to_binary_bytes()

print(f"  [+] JSON Paket Boyutu   : {len(json_b)} Bayt | Örnek: {json_b.decode('utf-8')}")
print(f"  [+] İkili Paket Boyutu  : {len(bin_b)} Bayt | Hex: {bin_b.hex()}")
print(f"  [+] Boyut Kazanç Oranı  : {len(json_b) / len(bin_b):.2f}x Daha Kompakt!")
```

---

## 6. Taktik İHA Telemetri Senaryosu (1000 Hz Radar İzi & Hedef Takibi)

Bu senaryoda bir AESA Radarı, hava sahasındaki 10 kritik hedef için saniyede 1,000 kez telemetri güncellemesi üretmektedir:
- **Paket Hacmi:** $10 \times 1000 = 10,000\ \text{paket/saniye}$.
- **Taktik Telsiz / Veri Bağı:** UHF Taktik Telsiz Linki azami $2.0\ \text{Mbps}$ bant genişliğine sahiptir.

### İnceleme Soruları:
1. JSON kullanıldığında gerekli bant genişliği telsiz sınırını aşar mı? (Kanal doygunluğu ve paket düşürme).
2. İkili format kullanıldığında telsiz hattında ne kadar boşluk kalır?
3. Aşağıdaki kod hücresinde bu veri akışını simüle edip tam bayt ve bant genişliği metriklerini hesaplayacağız.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 153: Kod Bloğu 2 — 1000 Hz Taktik Veri Akışı ve Bant Genişliği Ölçümü
"""

# 10 Kritik Hedeflik Taktik Hava Resmi
targets = [
    TacticalTarget(
        target_id=1000 + i,
        azimuth=45.0 + (i * 2.5),
        elevation=10.0 + (i * 0.5),
        range_m=20000.0 + (i * 500.0),
        speed_mps=250.0 + (i * 10.0)
    ) for i in range(10)
]

# Her iki formatta toplam bayt hacmi (1 saniyelik 1000 Hz akış için)
hertz = 1000
total_json_bytes_sec = sum(len(t.to_json_bytes()) for t in targets) * hertz
total_bin_bytes_sec = sum(len(t.to_binary_bytes()) for t in targets) * hertz

# Bant Genişliği (Mbps - Megabit per second)
json_mbps = (total_json_bytes_sec * 8) / 1_000_000.0
bin_mbps = (total_bin_bytes_sec * 8) / 1_000_000.0

RADIO_LINK_LIMIT_MBPS = 2.0 # 2.0 Mbps Taktik UHF Telsiz Sınırı

print()
print("[*] 1000 Hz Radar İzi Bant Genişliği Raporu:")
print(f"  [+] JSON Saniyede İletilen Bayt   : {total_json_bytes_sec:,} Bayt/s")
print(f"  [+] JSON Gerekli Bant Genişliği  : {json_mbps:.2f} Mbps")
print(f"  [+] İkili Saniyede İletilen Bayt  : {total_bin_bytes_sec:,} Bayt/s")
print(f"  [+] İkili Gerekli Bant Genişliği : {bin_mbps:.2f} Mbps")
print(f"  [+] Telsiz Kapasite Sınırı       : {RADIO_LINK_LIMIT_MBPS:.2f} Mbps")

json_fits = json_mbps <= RADIO_LINK_LIMIT_MBPS
bin_fits = bin_mbps <= RADIO_LINK_LIMIT_MBPS

print(f"  [+] JSON Telsizden Geçebilir mi? : {json_fits} (KANAL BOĞULDU! PAKETLER DÜŞER!)")
print(f"  [+] İkili Telsizden Geçebilir mi?: {bin_fits} (KUSURSUZ İLETİM! SIKIŞMA YOK!)")

assert not json_fits, "JSON taktik telsiz sınırını mutlaka aşmalıdır!"
assert bin_fits, "İkili format taktik telsiz sınırının altında kalmalıdır!"
print("[HÜCRE 9] Taktik bant genişliği ve kanal doygunluğu testi başarıyla tamamlandı.")
```

---

## 7. Bilerek Bozma (Sabotaj ve Arıza Enjeksiyonu)

Protokol tasarımında metin tabanlı serileştirmenin getirdiği ölümcül riskleri iki deneyle kanıtlayacağız:

### Sabotaj 1: Taktik Koordinat Hassasiyet Kaybı ve Balistik Sapma
Füze güdümünde hedef enlemi $39.92548231^\circ$ iken, JSON'a aktarılırken geliştirici tarafından bayt tasarrufu amacıyla 4 ondalık basamağa yuvarlanmıştır (`%.4f` -> `"39.9255"`).
- $1^\circ$ enlemin $111,320\ \text{metre}$ olduğu coğrafi modelde oluşan sapma:
$$\Delta x = |\text{lat}_{orig} - \text{lat}_{json}| \times 111,320\ \text{m}$$
- **Beklenen Sonuç:** İkili formatta mikro-derece tamsayı temsili ile sapma $0.000\ \text{m}$ iken; JSON formatında yaklaşık **2 metrelik** ölümcül hedef ıskalama hatası gözlemlenecektir!

### Sabotaj 2: Tip Uyuşmazlığı ve Bozuk JSON Formatı ile Ayrıştırıcı Çökmesi
Ağ paraziti veya düşman elektronik taarruzu nedeniyle JSON metnindeki bir tırnak işareti (`"`) veya süslü parantez (`}`) bozulur ya da sayı yerine `"CORRUPTED_STRING_VALUE"` gelir.
- **Kırılgan Sonuç:** Standart JSON kütüphanesi `ValueError` / `JSONDecodeError` fırlatır, ayrıştırma çöker.
- **İkili Sağlamlık:** Sabit boyutlu ikili struct'ta sözdizimi (syntax) kavramı yoktur; CRC denetiminden geçen her bayt doğrudan doğal bellek haritasına oturur.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 153: Kod Bloğu 3 — Sabotaj Deneyleri: Hassasiyet Sapması ve Bozuk JSON Formatı
"""

import math

print()
print("[*] Serileştirme Sabotaj ve Hassasiyet Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: Taktik Koordinat Hassasiyet Kaybı ve Hedef Sapması
# -----------------------------------------------------------------------------
# GPS / Taktik Enlem Koordinatı (1 Derece enlem ≈ 111,320 metredir)
orig_lat = 39.92548231 # Yüksek hassasiyetli hedef enlemi (derece)

# İkili format: Mikro-derece (int32) olarak saklanır (tamamen deterministik ve hassas)
bin_lat_bytes = struct.pack(">i", int(orig_lat * 1e6))
recovered_bin_lat = struct.unpack(">i", bin_lat_bytes)[0] / 1e6

# JSON formatı: Geliştirici bayt tasarrufu için veya std::to_string ile %.4f kestiğinde:
json_str = f'{{"target_id":1042,"lat":{orig_lat:.4f},"lon":32.8660,"alt":1200.0}}'.encode('utf-8')
recovered_json_lat = json.loads(json_str.decode('utf-8'))["lat"]

# Yeryüzünde oluşan balistik sapma mesafesi (Metre)
DEGREE_TO_METERS = 111_320.0
miss_distance_bin_m = abs(orig_lat - recovered_bin_lat) * DEGREE_TO_METERS
miss_distance_json_m = abs(orig_lat - recovered_json_lat) * DEGREE_TO_METERS

print(f"  [+] Sabotaj 1 Sonuçları (Taktik Koordinat Sapması):")
print(f"      - Orijinal Hedef Enlemi      : {orig_lat:.8f}°")
print(f"      - İkili Okunan Enlem         : {recovered_bin_lat:.8f}° (Sapma: {miss_distance_bin_m:.4f} m)")
print(f"      - JSON'dan Okunan Enlem      : {recovered_json_lat:.8f}° (Sapma: {miss_distance_json_m:.2f} m!)")
print(f"      - Balistik Iskalama Riski    : {miss_distance_json_m:.2f} METRE! (Nokta atışı füze hedefi vuramayabilir!)")

assert miss_distance_json_m > 1.0, "JSON koordinat sapması 1 metrenin üzerinde olmalıdır!"
assert miss_distance_bin_m < 0.15, "İkili koordinat sapması santimetre seviyesinde kalmalıdır!"

# -----------------------------------------------------------------------------
# SABOTAJ 2: Bozuk JSON Şeması ve Tip Uyuşmazlığı
# -----------------------------------------------------------------------------
corrupt_json_str = b'{"target_id":1042,"azimuth":88.5,"elevation":"CORRUPTED_STRING_VALUE","range_m":45210.8}'
json_crashed = False

try:
    _ = TacticalTarget.from_json_bytes(corrupt_json_str)
except Exception as e:
    json_crashed = True
    print()
    print(f"  [+] Sabotaj 2 Sonuçları (Tip Uyuşmazlığı Çökmesi):")
    print(f"      - Yakalanan İstisna : {type(e).__name__} -> {e}")
    print(f"      - Parser Durumu     : ÇÖKTÜ (Görev Bilgisayarı Kilitlendi!)")

assert json_crashed == True, "Bozuk JSON alanında parser çökmelidir!"
print("[HÜCRE 11] Tüm sabotaj deneyleri başarıyla kanıtlandı.")
```

---

## 8. Yüksek Hacimli Performans ve Gecikme Benchmarkı

Bir taktik radar işlemcisinde $30,000$ adet hedef paketinin serileştirilmesi (Packing) ve ayrıştırılması (Unpacking) süreçlerinde:
1. **JSON Süresi ve Gecikmesi (Serialization & Deserialization)**
2. **İkili Format Süresi ve Gecikmesi (Raw Struct Packing & Unpacking)**
ölçülecek; işlemci çekirdeği başına azami paket işleme kapasitesi (Throughput - paket/saniye) karşılaştırılacaktır.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 153: Kod Bloğu 4 — Benchmark: 30,000 Paket Başına JSON vs Binary Hız ve Gecikme
"""

import time

def run_serialization_benchmark(iterations: int = 30_000) -> Dict[str, Any]:
    target = TacticalTarget(1042, 88.5412, 12.301, 45210.8, 320.4)
    
    # 1. JSON Serileştirme & Ayrıştırma
    t0 = time.perf_counter()
    for _ in range(iterations):
        raw = target.to_json_bytes()
        _ = TacticalTarget.from_json_bytes(raw)
    t_json = time.perf_counter() - t0

    # 2. İkili Serileştirme & Ayrıştırma
    t0 = time.perf_counter()
    for _ in range(iterations):
        raw = target.to_binary_bytes()
        _ = TacticalTarget.from_binary_bytes(raw)
    t_bin = time.perf_counter() - t0

    return {
        "iterations": iterations,
        "t_json_ms": t_json * 1000.0,
        "t_bin_ms": t_bin * 1000.0,
        "json_ns_per_op": (t_json / iterations) * 1e9,
        "bin_ns_per_op": (t_bin / iterations) * 1e9,
        "speedup": t_json / t_bin,
        "json_throughput": iterations / t_json,
        "bin_throughput": iterations / t_bin
    }

bench_res = run_serialization_benchmark(iterations=30_000)

print()
print(f"[*] Serileştirme Hız Benchmarkı ({bench_res['iterations']:,} İşlem):")
print(f"  [+] JSON Toplam Süre      : {bench_res['t_json_ms']:.2f} ms ({bench_res['json_ns_per_op']:.1f} ns/op)")
print(f"  [+] JSON Kapasite         : {bench_res['json_throughput']:,.0f} paket/sn")
print(f"  [+] İkili Toplam Süre     : {bench_res['t_bin_ms']:.2f} ms ({bench_res['bin_ns_per_op']:.1f} ns/op)")
print(f"  [+] İkili Kapasite        : {bench_res['bin_throughput']:,.0f} paket/sn")
print(f"  [+] İkili Hızlandırma     : {bench_res['speedup']:.2f}x DAHA HIZLI!")

assert bench_res['speedup'] > 2.0, "İkili format JSON'dan en az 2 kat hızlı olmalıdır!"
print("[HÜCRE 13] Serileştirme benchmarkı başarıyla tamamlandı.")
```

---

## 9. Gerçek Dünya Taktik Senaryosu: Askeri Telsizden Web Komuta Merkezine (Hibrit Ağ Geçidi)

Savunma mimarisinde hem ikili hem metin tabanlı formatların bir arada kullanıldığı en tipik senaryo **Taktik Ağ Geçitleridir (Tactical Gateway / Edge Node)**:
- **Taktik Saha Ağı:** İHA, Radar ve Füzeler arasında kısıtlı telsiz hattında saf **İkili (Binary)** telemetri akar (STANAG 4586 / Link 16).
- **Komuta Kontrol Karargahı (HQ):** Web tarayıcıları, harita sunucuları ve WebSocket arayüzleri insan operatörlerin izlemesi için **JSON** bekler.
- **Ağ Geçidi Görevi:** Uçtan gelen ikili baytları anında çözer, veri bütünlüğünü doğrular ve karargaha JSON akışı olarak aktarır.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 153: Kod Bloğu 5 — Hibrit Taktik Ağ Geçidi (Binary Radar -> JSON C2 Web Gateway)
"""

class TacticalHybridGateway:
    """
    Taktik telsizden gelen yüksek hızlı ikili telemetriyi
    karargah Web ve Harita sunucuları için JSON formatına dönüştüren ağ geçidi.
    """
    def __init__(self):
        self.packets_bridged = 0
        self.bytes_in_binary = 0
        self.bytes_out_json = 0

    def process_incoming_binary_packet(self, binary_packet: bytes) -> bytes:
        self.bytes_in_binary += len(binary_packet)
        # 1. Hızlı İkili Ayrıştırma (Zero CPU bottleneck)
        target = TacticalTarget.from_binary_bytes(binary_packet)
        
        # 2. Karargah Operatör Ekranı İçin Zenginleştirilmiş JSON Üretimi
        c2_view = {
            "track_id": f"TRK-{target.target_id:04d}",
            "coordinates": {
                "azimuth_deg": round(target.azimuth, 2),
                "elevation_deg": round(target.elevation, 2),
                "range_km": round(target.range_m / 1000.0, 2)
            },
            "kinematics": {
                "speed_mach": round(target.speed_mps / 340.29, 2) # Mach sayısı
            },
            "threat_level": "CRITICAL" if target.speed_mps > 300.0 else "NORMAL"
        }
        json_out = json.dumps(c2_view).encode('utf-8')
        self.bytes_out_json += len(json_out)
        self.packets_bridged += 1
        return json_out

gateway = TacticalHybridGateway()

# Simülasyon: Radardan gelen 5 ikili hedefi C2 ekranına dönüştür
sample_bin_packet = TacticalTarget(1042, 88.54, 12.30, 45210.0, 350.0).to_binary_bytes()
json_c2_display = gateway.process_incoming_binary_packet(sample_bin_packet)

print()
print("[*] Hibrit Taktik Ağ Geçidi Raporu:")
print(f"  [+] Gelen İkili Boyutu   : {len(sample_bin_packet)} Bayt")
print(f"  [+] Üretilen C2 JSON     : {json_c2_display.decode('utf-8')}")
print(f"  [+] Çıkış JSON Boyutu    : {len(json_c2_display)} Bayt")
print(f"  [+] Dönüştürülen Paket   : {gateway.packets_bridged}")

assert gateway.packets_bridged == 1
assert b"TRK-1042" in json_c2_display
assert b"CRITICAL" in json_c2_display
print("[HÜCRE 15] Hibrit ağ geçidi testi başarıyla tamamlandı.")
```

---

## 10. 4-Panelli 300 DPI Görselleştirme Mimarisi

Aşağıdaki kod hücresi; paket boyutlarını, bant genişliği tüketimini, ayrıştırma gecikmesi benchmarkını ve kayan nokta hassasiyet sapmasını 4 panelde detaylandıran profesyonel bir karanlık tema (`#0F172A`) görsel panosu üretir:

1. **Panel 1 (Sol Üst): Teldeki Paket Boyutları (Wire Size):**
   Aynı telemetri verisinin Standart JSON, Kompakt JSON ve Saf İkili Struct formatlarında bayt cinsinden büyüklükleri.
2. **Panel 2 (Sağ Üst): 1000 Hz Veri Akışında Bant Genişliği Tüketimi (Mbps):**
   Taktik UHF telsiz limiti ($2.0\ \text{Mbps}$) karşısında JSON ve İkili formatların kanal doluluk oranları.
3. **Panel 3 (Sol Alt): Serileştirme ve Ayrıştırma İşlem Süresi (Nanosaniye / Paket):**
   JSON ve İkili formatların paket başına CPU gecikmesi ($ns/op$) ve hızlanma faktörü ($Speedup$).
4. **Panel 4 (Sağ Alt): Yeryüzünde Hedef Koordinat Sapması (Metre):**
   JSON string kesmesi kaynaklı balistik ıskalama mesafesi ile İkili formatın santimetre seviyesindeki kesinliği.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 153: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_153_serialization_json_vs_binary.png")

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: Paket Boyutları Karşılaştırması (Wire Size)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')

formats = ['Standart JSON\n(Genişletilmiş)', 'Kompakt JSON\n(Boşluksuz)', 'Saf İkili Struct\n(Raw Binary C++)']
sizes = [len(sample.to_json_bytes()) + 32, len(sample.to_json_bytes()), len(sample.to_binary_bytes())]
colors_size = ['#EF4444', '#F59E0B', '#10B981']

bars1 = ax1.bar(formats, sizes, color=colors_size, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars1, sizes):
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 2.0, f"{val} Bayt\n({val/sizes[2]:.1f}x)", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=9.5)

ax1.set_ylim(0, max(sizes) * 1.35)
ax1.set_ylabel("Paket Boyutu (Bayt)", fontsize=10, color='#94A3B8')
ax1.set_title("Teldeki Paket Boyutu (On-The-Wire Overhead)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax1.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax1.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 2: 1000 Hz Bant Genişliği vs Telsiz Limiti
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

streams = ['JSON (10 Hedef @ 1000 Hz)', 'İkili (10 Hedef @ 1000 Hz)']
bw_values = [json_mbps, bin_mbps]
colors_bw = ['#EF4444', '#10B981']

bars2 = ax2.bar(streams, bw_values, color=colors_bw, width=0.4, edgecolor='#334155', lw=1.5)
ax2.axhline(RADIO_LINK_LIMIT_MBPS, color='#38BDF8', linestyle='--', linewidth=2, label=f'Taktik Telsiz Sınırı ({RADIO_LINK_LIMIT_MBPS} Mbps)')

for bar, val in zip(bars2, bw_values):
    yval = bar.get_height()
    status = "AŞILDI! (Telsiz Boğuldu)" if val > RADIO_LINK_LIMIT_MBPS else "UYGUN (Kanal Temiz)"
    ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.3, f"{val:.2f} Mbps\n{status}", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=9)

ax2.set_ylim(0, max(bw_values) * 1.35)
ax2.set_ylabel("Gerekli Bant Genişliği (Mbps)", fontsize=10, color='#94A3B8')
ax2.set_title("Taktik Telsiz Kanal Kapasitesi ve Doygunluk", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax2.legend(loc='upper right', facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', fontsize=9)
ax2.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Paket Ayrıştırma Süresi (Nanosaniye / Paket)
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

bench_labels = ['JSON (String Parse + Alloc)', 'İkili (Direct Unpack / Span)']
latencies = [bench_res['json_ns_per_op'], bench_res['bin_ns_per_op']]
colors_lat = ['#EF4444', '#10B981']

bars3 = ax3.bar(bench_labels, latencies, color=colors_lat, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars3, latencies):
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + (yval * 0.04), f"{val:.1f} ns/op", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=10)

ax3.set_ylim(0, max(latencies) * 1.25)
ax3.set_ylabel("Gecikme (Nanosaniye - ns)", fontsize=10, color='#94A3B8')
ax3.set_title(f"Serileştirme/Ayrıştırma Gecikmesi ({bench_res['speedup']:.1f}x Hız Farkı)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: Yeryüzünde Hedef Koordinat Sapması (Metre)
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')

error_labels = ['JSON Yuvarlama\n(%.4f String Format)', 'İkili Mikroderece\n(int32 Bit-Exact)']
miss_meters = [miss_distance_json_m, miss_distance_bin_m]
colors_err = ['#EF4444', '#10B981']

bars4 = ax4.bar(error_labels, miss_meters, color=colors_err, width=0.4, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars4, miss_meters):
    yval = bar.get_height()
    label_txt = f"{val:.2f} m Sapma\n(HEDEF ISKALANDI!)" if val > 0.5 else f"{val:.4f} m\n(TAM İSABET)"
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 0.08, label_txt, ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=9.5)

ax4.set_ylim(0, max(miss_distance_json_m * 1.35, 2.5))
ax4.set_ylabel("Hedef Konum Hatası (Metre)", fontsize=10, color='#94A3B8')
ax4.set_title("Coğrafi Koordinatlarda Balistik Sapma Mesafesi", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
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
print("[*] GÜN 153 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert len(sample.to_binary_bytes()) == 20, "İkili struct tam olarak 20 bayt olmalıdır!"
assert len(sample.to_json_bytes()) > 60, "JSON formatı ikili boyuttan en az 3 kat büyük olmalıdır!"
assert json_mbps > RADIO_LINK_LIMIT_MBPS, "JSON telsiz bant genişliğini aşmalıdır!"
assert bin_mbps < RADIO_LINK_LIMIT_MBPS, "İkili telsiz bandına sığmalıdır!"
assert bench_res['speedup'] > 2.0, "İkili format JSON'dan belirgin biçimde hızlı olmalıdır!"
assert miss_distance_json_m > 1.0, "JSON koordinat sapması 1 metrenin üzerinde olmalıdır!"

print()
print("[PASS] Gün 153: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

---

## 11. Karşılaştırmalı Analiz ve Mimari Karar Matrisi

Savunma ve dağıtık sistem mimarilerinde format seçim karar matrisi:

| Parametre | JSON | Raw Binary Struct (C++) | FlatBuffers / Cap'n Proto | Protocol Buffers (Protobuf) |
| :--- | :--- | :--- | :--- | :--- |
| **Bant Genişliği** | Çok Kötü (%500 Fazla) | **Maksimum (%100 Saf)** | Mükemmel (%90 Saf) | Çok İyi (Varint sıkıştırma) |
| **Ayrıştırma Gecikmesi**| Yavaş ($> 2,000\ \text{ns}$) | **Anında ($< 10\ \text{ns}$)** | **Anında ($< 10\ \text{ns}$)** | Hızlı ($100 - 300\ \text{ns}$) |
| **Sıfır Kopyalama (Zero-Copy)**| İmkansız | **Doğrudan Destekli** | **Doğrudan Destekli** | Desteklenmez (Unpack gerektirir)|
| **Şema Evrimi / Uyumluluk**| Dinamik | Zayıf (Manuel TLV gerekir)| Mükemmel (ID bazlı) | Mükemmel (Tag bazlı) |
| **Kullanım Alanı** | Web GUI, REST API | Radar, Aviyonik, Füze | Gerçek Zamanlı Oyun/Simülasyon | Mikroservisler, Dağıtık C2 |

---

## 12. Donanım ve İşletim Sistemi Seviyesi Etkileşimler

### 1. CPU Önbellek Verimliliği (Cache Lines & Memory Footprint):
Modern x86_64 ve ARM işlemcilerde L1/L2 önbellek satırları $64$ bayttır:
- 20 baytlık bir ikili telemetri kaydı, tek bir 64-baytlık önbellek satırına **3 adet** sığar. İşlemci bir döngüde 3 hedefi tek bir bellek erişimiyle önbelleğe çeker.
- 100 baytlık bir JSON mesajı ise iki farklı önbellek satırına taşar. Ayrıştırıcı string aramaları yaparken sık sık **Cache Miss (Önbellek Kaçırma)** yaşar ve CPU ana bellek (RAM) gecikmesine takılır.

### 2. SIMD Hızlandırması (simdjson):
Eğer kurumsal bir C2 sisteminde JSON kullanmak zorunluysa, standart `nlohmann/json` yerine Daniel Lemire'in geliştirdiği **`simdjson`** kütüphanesi tercih edilmelidir:
- AVX-512 ve ARM NEON vektör talimatlarını kullanarak saniyede gigabaytlarca JSON metnini sıfır heap tahsisiyle ayrıştırabilir.

---

## 13. Güvenlik, Hata Ayıklama ve Taktik İpuçları

### 1. JSON Kaynak Tüketim Saldırıları (ReDoS & Billion Laughs):
Kötü niyetli bir siber aktör, savunma komuta kontrol ağına milyonlarca iç içe geçmiş JSON objesi (`{"a":{"a":{"a":...}}}`) veya devasa float sayı dizileri göndererek parser'ın bellek tüketimini patlatabilir (Stack Overflow veya OOM Killer).  
**Savunma:** JSON parser konfigürasyonunda `max_depth = 16` ve `max_size = 4096` sınırları katı olarak tanımlanmalıdır.

### 2. Taktik Wireshark İpuçları:
İkili protokolleri sahadayken Wireshark ile incelerken, otomatik dissector yoksa:
```bash
# Wireshark'ta belirli ofsetteki 32-bit float'ı okuma filtresi:
data.f[12:4] > 1000.0
```

---

## 14. Günün Mini Uygulaması: Taktik Hibrit Ağ Geçidi

Günün mini uygulamasında, bir hava savunma radarı ile taktik komuta merkezi arasında çalışan:
1. 20 baytlık yüksek hızlı ikili telemetri paketlerini sıfır kopyalama ile işleyen,
2. Taktik telsiz hattının bant genişliğini aşmayarak kanal boğulmasını önleyen,
3. Kayan nokta açısal hassasiyet kaybını ortadan kaldıran,
4. Karargah operatörleri için güvenli ve zenginleştirilmiş JSON verisi üreten `TacticalHybridGateway` sistemini tasarladık ve doğruladık.

---

## 15. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **Yüksek Frekanslı Veride JSON Kullanmak:** 100 Hz veya 1000 Hz sensör döngülerinde metin tabanlı serileştirme kullanarak işlemciyi ve telsiz hattını boğmak.
2. **Kayan Noktalı Sayılarda String Yuvarlaması Yapmak:** Hassas hedef koordinatlarını JSON'a aktarırken basamak kesmek (`%.2f`) ve füzenin hedefi onlarca metre ıskalamasına sebep olmak.
3. **Hard Real-Time Döngüde `malloc` Tetikleyen Parser Kullanmak:** Jitter toleransı sıfır olan uçuş döngülerinde dinamik bellek ayıran JSON kütüphanelerine güvenmek.
4. **İkili Veride Bayt Sıralamasını (Endianness) Unutmak:** Farklı mimarilerde (ARM vs x86) çalışan düğümler arasında ağ bayt sırası (`htons` / `htonl` / `big-endian`) dönüşümü yapmadan doğrudan `memcpy` yapmak.

---

## 16. Mülakat ve Saha Deneyimi Soruları (ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ)

### Soru 1: Bir taktik İHA telemetri akışında JSON yerine ikili (binary) format tercih edilmesinin en kritik 3 mühendislik sebebi nedir?
**Cevap:**
1. **Bant Genişliği Verimliliği:** Taktik telsiz ve uydu linkleri (UHF/VHF/Satcom) sınırlı bant genişliğine sahiptir ($< 2\ \text{Mbps}$). JSON anahtar metinleri nedeniyle %400-800 ek yük getirirken, ikili format saf bayt taşır.
2. **Ayrıştırma Gecikmesi ve Determinizm:** İkili veriler bellekten doğrudan okunabilir ($< 10\ \text{ns}$); JSON ise string parsing ve ASCII-to-float dönüşümü gerektirerek yüzlerce kat daha yavaş çalışır ve döngü gecikmesine (jitter) yol açar.
3. **Dinamik Bellek ve Güvenilirlik:** JSON parser'lar heap üzerinde dinamik bellek tahsis eder (`malloc`), bu da aviyonik DO-178C standartlarında bellek parçalanması riski nedeniyle yasaktır. İkili format sıfır heap ile çalışır.

### Soru 2: Sayısal kayan noktalı verilerin (float/double) JSON serileştirmesinde ortaya çıkan 'Epsilon / Precision Loss' problemi füze güdümünde neye yol açar?
**Cevap:** Ondalık kayan noktalı sayılar ikili tabanda IEEE 754 formatında saklanır. Sayı JSON metnine dönüştürülürken basamak yuvarlaması yapılır ve metinden tekrar sayıya dönüştürüldüğünde en düşük anlamlı bitlerde (LSB) farklar oluşur. $50-100\ \text{km}$ menzildeki bir füze angajmanında hedef azimut açısındaki mikroskopik bir derece sapması, hedef konumunda onlarca metrelik balistik ıskalama mesafesi (miss-distance) oluşturarak füzenin hedefi vuramamasına sebep olur.

### Soru 3: Web tabanlı modern Komuta Kontrol (C2) arayüzleri JSON isterken, telsizden ikili veri akıyorsa bu mimari ikilem nasıl çözülür?
**Cevap:** Taktik Ağ Geçidi (Tactical Gateway / Edge Broker) mimarisi kullanılır. Uç birimler (radar, İHA, füze) kısıtlı taktik ağda tamamen ikili (STANAG 4586 / MAVLink / DDS) haberleşir. Karargaha veya yer istasyonuna yerleştirilen C++20 tabanlı yüksek performanslı bir ağ geçidi, ikili paketleri doğrular, sıfır kopyalama ile çözer ve operatörlerin izlediği WebSocket veya REST tabanlı Web-GUI sunucularına JSON olarak servis eder.

---

## 17. Gün Sonu Özeti ve 3-Cümle Çıkarımı

1. **JSON vs Binary Serileştirme Nedir?:** Veri yapılarının ağ üzerinden iletilirken ya insan tarafından okunabilir metin formatında (JSON) ya da donanımın doğrudan anladığı saf makine baytları (Binary) biçiminde paketlenmesidir.
2. **Hangi Problemi Çözer?:** İkili serileştirme; taktik telsiz hatlarında kanal boğulmasını, CPU string parsing gecikmesini, dinamik bellek parçalanmasını ve kayan nokta hassasiyet kayıplarını kökten çözer.
3. **Hangi Trade-off/Hata Sınıfını Getirir?:** İkili format insan tarafından doğrudan okunamaz, özel dissector/şema gerektirir ve bayt sırası (endianness) veya struct hizalama (padding) hatalarına karşı titizlikle yönetilmelidir.