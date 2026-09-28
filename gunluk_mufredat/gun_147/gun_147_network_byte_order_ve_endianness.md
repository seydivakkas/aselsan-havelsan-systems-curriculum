# GÜN 147: Network Byte Order ve Endianness Mimarisi

**Müfredat:** 365 Günlük ASELSAN / HAVELSAN Savunma Sistemleri C++20 & Linux Sistem Mühendisliği  
**Faz:** F4 — TCP/UDP / Ağ Protokolleri / Serileştirme & Taktik Dağıtık Sistemler  
**Konu:** Ağ Bayt Sırası (Network Byte Order - Big-Endian), Konak Bayt Sırası (Host Byte Order - Little-Endian), POSIX `htons`/`htonl`/`ntohs`/`ntohl`, 64-bit Dönüşümleri, C++20 `std::endian`, `bswap` Donanım Hızlandırması ve Heterojen Savunma Sistemleri  
**Ön Koşul:** Gün 146 (select/poll/epoll ile Event-Driven I/O)

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

Savunma sanayiinde tek bir platform içinde yüzlerce heterojen işlemci mimarisi bir arada çalışır:
- **Görev ve Gösterge Bilgisayarları (Mission Computers):** Modern x86_64 (Intel Xeon / AMD EPYC) veya ARM64 (Cortex-A78) işlemciler (Varsayılan: **Little-Endian**).
- **Radar ve Sonar Sinyal İşleme Kartları (DSP & FPGA):** Texas Instruments TMS320C6000 serisi DSP'ler, eski PowerPC veya Xilinx MicroBlaze çekirdekleri (Geleneksel olarak: **Big-Endian** veya bi-endian).
- **Aviyonik Veri Yolu Arayüzleri (MIL-STD-1553B / ARINC-429 / Ethernet):** Tüm standart ağ ve askeri protokoller veriyi kablo üzerinden **Ağ Bayt Sırası (Network Byte Order = Big-Endian)** ile taşır.

Eğer bir ROKETSAN seyir füzesi güdüm bilgisayarı hedef menzilini ($1000\ \text{metre} = 0x000003E8$) Little-Endian formatta doğrudan ağa basarsa ve alıcı radar bunu Big-Endian kabul edip dönüştürmezse:
Alıcı sistem baytları ters okur: $0xE8030000 = 3,892,510,720\ \text{metre}$ ($3.89\ \text{milyon kilometre}$)!
Hedef Dünya ile Ay arasındaki mesafenin 10 katı uzakta zannedilir; hava savunma bataryası hedefi anında kaybeder, angajman iptal olur veya füze havada patlatılır.

```
   +-------------------------------------------------------------------------+
   |                ENDIANNESS ZİHİNSEL MODELİ: 0x12345678                   |
   +-------------------------------------------------------------------------+

   Değer: 0x12 34 56 78  (MSB = 0x12, LSB = 0x78)

   A) BIG-ENDIAN (Network Byte Order / İnsan Okuma Sırası):
      Bellek Adresi:   [Adres 0]  [Adres 1]  [Adres 2]  [Adres 3]
      Değer (Bayt):    |  0x12   |  0x34   |  0x56   |  0x78   |
                       (En Önemli Bayt - MSB en düşük adreste)

   B) LITTLE-ENDIAN (x86_64 / ARM Host Byte Order):
      Bellek Adresi:   [Adres 0]  [Adres 1]  [Adres 2]  [Adres 3]
      Değer (Bayt):    |  0x78   |  0x56   |  0x34   |  0x12   |
                       (En Önemsiz Bayt - LSB en düşük adreste)
```

---

## 2. Endianness Nedir? Big-Endian vs Little-Endian Bellek Modeli

"Endian" terimi, Jonathan Swift'in *Gulliver'in Gezileri* romanındaki haşlanmış yumurtayı sivri ucundan (little-end) mi yoksa küt ucundan (big-end) mi kırmak gerektiği tartışmasından esinlenerek bilgisayar mimarı Danny Cohen tarafından 1980 yılında ("On Holy Wars and a Plea for Peace", IEN 137) literatüre kazandırılmıştır.

### Tanımlar:
- **MSB (Most Significant Byte - En Anlamlı / En Önemli Bayt):** Bir sayının en yüksek ağırlıklı basamağını içeren bayttır. Örneğin $0x1234$ sayısında `0x12` MSB'dir.
- **LSB (Least Significant Byte - En Önemsiz / En Düşük Bayt):** Bir sayının en düşük basamağını içeren bayttır. $0x1234$ sayısında `0x34` LSB'dir.
- **Big-Endian:** MSB en düşük bellek adresine (`address 0`) yerleştirilir. İnsanların soldan sağa sayı okuma alışkanlığına birebir uygundur.
- **Little-Endian:** LSB en düşük bellek adresine (`address 0`) yerleştirilir. Aritmetik işlemlerde işlemci donanımının toplama/çıkarma yaparken eldeyi (carry) doğal sırayla yaymasını kolaylaştırır (x86 mimarisinin seçilme sebebi).

---

## 3. Network Byte Order Standardı ve POSIX Fonksiyonları

RFC 791 (IPv4) ve RFC 793 (TCP) standartları uyarınca, İnternet Protokol kümesindeki tüm çok baytlı tamsayılar (IP adresleri, port numaraları, paket uzunlukları, TCP sıra numaraları) kablo üzerinde **Big-Endian** olarak iletilmelidir. Bu standarda **Network Byte Order (Ağ Bayt Sırası)** denir.

İşletim sisteminizin yerel donanım mimarisine ise **Host Byte Order (Konak Bayt Sırası)** denir.

### Standart POSIX C Dönüşüm Fonksiyonları (`<arpa/inet.h>` / `<netinet/in.h>`):
```cpp
#include <arpa/inet.h>

// 16-bit (uint16_t - Örn. Port Numaraları)
uint16_t htons(uint16_t hostshort); // Host to Network Short
uint16_t ntohs(uint16_t netshort);  // Network to Host Short

// 32-bit (uint32_t - Örn. IPv4 Adresi, Dizi Sıra Numaraları)
uint32_t htonl(uint32_t hostlong);  // Host to Network Long
uint32_t ntohl(uint32_t netlong);   // Network to Host Long
```

### 64-bit Dönüşümleri (`uint64_t` - Zaman Damgaları, Hassas Koordinatlar):
POSIX standardında `htonll` / `ntohll` resmi olarak her platformda bulunmaz. Linux glibc sistemlerinde `<endian.h>` başlığı altında şu fonksiyonlar sunulur:
```cpp
#include <endian.h>

uint64_t htobe64(uint64_t host_64bits); // Host to Big-Endian 64
uint64_t be64toh(uint64_t big_endian_64bits); // Big-Endian to Host 64
uint64_t htole64(uint64_t host_64bits); // Host to Little-Endian 64
```

---

## 4. C++20 `<bit>` Başlığı: `std::endian` ve `std::byteswap`

C++20 standartlaşması ile birlikte derleme zamanında (compile-time `constexpr`) donanımın endianness tipini sorgulamak ve taşınabilir kod yazmak son derece kolaylaşmıştır:

```cpp
#include <bit>
#include <iostream>

void inspect_platform_endianness() {
    if constexpr (std::endian::native == std::endian::little) {
        std::cout << "Mevcut Mimari: Little-Endian (x86_64 / ARM default)
";
    } else if constexpr (std::endian::native == std::endian::big) {
        std::cout << "Mevcut Mimari: Big-Endian (Network Order / DSP / PowerPC)
";
    } else {
        std::cout << "Mevcut Mimari: Egzotik (Mixed / PDP-endian)
";
    }
}
```

### C++23 `std::byteswap` ve C++20 `constexpr` Bayt Ters Çevirme
C++20'de derleme zamanı bayt çevirici şablonu (template):
```cpp
#include <concepts>
#include <cstdint>

template <std::integral T>
constexpr T portable_byteswap(T value) noexcept {
    if constexpr (sizeof(T) == 1) {
        return value;
    } else if constexpr (sizeof(T) == 2) {
        return static_cast<T>((value << 8) | (value >> 8));
    } else if constexpr (sizeof(T) == 4) {
        return static_cast<T>(
            ((value & 0x000000FFU) << 24) |
            ((value & 0x0000FF00U) << 8)  |
            ((value & 0x00FF0000U) >> 8)  |
            ((value & 0xFF000000U) >> 24)
        );
    } else if constexpr (sizeof(T) == 8) {
        return static_cast<T>(
            ((value & 0x00000000000000FFULL) << 56) |
            ((value & 0x000000000000FF00ULL) << 40) |
            ((value & 0x0000000000FF0000ULL) << 24) |
            ((value & 0x00000000FF000000ULL) << 8)  |
            ((value & 0x000000FF00000000ULL) >> 8)  |
            ((value & 0x0000FF0000000000ULL) >> 24) |
            ((value & 0x00FF000000000000ULL) >> 40) |
            ((value & 0xFF00000000000000ULL) >> 56)
        );
    }
}
```
Modern derleyiciler (GCC / Clang) bu bit kaydırma mantığını doğrudan tek bir makine talimatına (`BSWAP` veya `REV`) optimize eder!

---

## 5. IEEE-754 Kayan Nokta (Float/Double) Endianness Sorunu ve Çözümleri

Radar hedef mesafeleri, füze hız vektörleri ve İHA oryantasyon açıları genellikle `float` (32-bit) veya `double` (64-bit) olarak hesaplanır.

### Tuzak: `htonl()` Doğrudan `float` Üzerinde Çalışmaz!
`htonl(float_val)` yazamazsınız çünkü `htonl` fonksiyonu tamsayı (`uint32_t`) bekler. C-style cast `(uint32_t)float_val` yaparsanız sayının bit dizilimi değil, matematiksel değeri tamsayıya yuvarlanır (veri kaybı).

### Doğru Yöntem 1: `std::bit_cast` (C++20) ile Type-Punning Güvenliği
```cpp
#include <bit>
#include <arpa/inet.h>

float host_to_network_float(float val) {
    // 1. Bitlerini bozmadan uint32_t olarak yorumla (Undefined Behavior yok!)
    uint32_t as_int = std::bit_cast<uint32_t>(val);
    // 2. Network Byte Order'a çevir
    uint32_t net_int = htonl(as_int);
    // 3. Tekrar float bitlerine dönüştür
    return std::bit_cast<float>(net_int);
}
```

### Doğru Yöntem 2: Sabit Noktalı (Fixed-Point Integer Scaling) İletim
Savunma sanayiinde IEEE-754 belirsizliklerinden kaçınmak için ondalıklı sayılar genellikle ölçekli tamsayılara (Fixed-Point) dönüştürülür:
```cpp
// Örnek: Füze İrtifası (0.01 metre hassasiyet)
double altitude_m = 12500.45;
uint32_t scaled_alt = static_cast<uint32_t>(altitude_m * 100.0); // 1250045
uint32_t net_alt = htonl(scaled_alt); // Ağ üzerinden gönder
```

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 1 — C++20 Endianness Dönüştürücü, Bit-Cast ve Bellek Dizilim Simülatörü
"""

import struct
import sys
from typing import Tuple, List, Dict, Any

class EndiannessEngine:
    """
    POSIX ve C++20 std::endian donanım bellek dönüşümlerini simüle eden sınıf.
    """
    HOST_IS_LITTLE = (sys.byteorder == 'little')

    @staticmethod
    def inspect_system_endian() -> str:
        return "Little-Endian (LSB first)" if EndiannessEngine.HOST_IS_LITTLE else "Big-Endian (MSB first)"

    @staticmethod
    def uint16_to_bytes(val: int, is_big_endian: bool) -> bytes:
        fmt = ">H" if is_big_endian else "<H"
        return struct.pack(fmt, val)

    @staticmethod
    def uint32_to_bytes(val: int, is_big_endian: bool) -> bytes:
        fmt = ">I" if is_big_endian else "<I"
        return struct.pack(fmt, val)

    @staticmethod
    def uint64_to_bytes(val: int, is_big_endian: bool) -> bytes:
        fmt = ">Q" if is_big_endian else "<Q"
        return struct.pack(fmt, val)

    @staticmethod
    def float32_to_bytes(val: float, is_big_endian: bool) -> bytes:
        fmt = ">f" if is_big_endian else "<f"
        return struct.pack(fmt, val)

    @staticmethod
    def bytes_to_uint32(b: bytes, is_big_endian: bool) -> int:
        fmt = ">I" if is_big_endian else "<I"
        return struct.unpack(fmt, b)[0]

    @staticmethod
    def bytes_to_float32(b: bytes, is_big_endian: bool) -> float:
        fmt = ">f" if is_big_endian else "<f"
        return struct.unpack(fmt, b)[0]

    @staticmethod
    def bswap32(val: int) -> int:
        """x86 BSWAP / ARM REV donanım talimatı simülasyonu."""
        return (
            ((val & 0x000000FF) << 24) |
            ((val & 0x0000FF00) << 8)  |
            ((val & 0x00FF0000) >> 8)  |
            ((val & 0xFF000000) >> 24)
        )

# Test Değeri: 0x12345678 (Ondalık: 305419896)
sample_val = 0x12345678
bytes_be = EndiannessEngine.uint32_to_bytes(sample_val, is_big_endian=True)
bytes_le = EndiannessEngine.uint32_to_bytes(sample_val, is_big_endian=False)

print(f"[HÜCRE 7] EndiannessEngine Yüklendi.")
print(f"  [+] Yerel Sistem Mimarisi : {EndiannessEngine.inspect_system_endian()}")
print(f"  [+] 0x12345678 Big-Endian (Network Order)  : {[hex(b) for b in bytes_be]}")
print(f"  [+] 0x12345678 Little-Endian (Host Order)  : {[hex(b) for b in bytes_le]}")

assert bytes_be == bytes([0x12, 0x34, 0x56, 0x78])
assert bytes_le == bytes([0x78, 0x56, 0x34, 0x12])
```

---

## 6. Taktik Füze Güdüm ve Radar İz Paketi Deney Senaryosu

Bir hava savunma füzesi güdüm bilgisayarı (x86_64 Little-Endian) ile kara radar istasyonu (PowerPC/DSP Big-Endian) arasında bir taktik telemetri paketi iletilmektedir:

```cpp
#pragma pack(push, 1)
struct TacticalMissileTelemetry {
    uint16_t message_id;    // 0x0101 (257)
    uint32_t target_range_m;// 1000 metre (0x000003E8)
    uint32_t missile_speed; // 850 m/s Mach 2.5 (0x00000352)
    float    heading_deg;   // 85.5 derece
};
#pragma pack(pop)
```

### Deney Akışı:
1. **Host to Network Dönüşümü (`htonl`/`htons`):** Verici füze bilgisayarı tüm alanları Big-Endian formata dönüştürüp ağa basar.
2. **Kablo Üzerinde İletim:** Veriler standart Network Byte Order ile akar.
3. **Network to Host Dönüşümü (`ntohl`/`ntohs`):** Alıcı radar istasyonu verileri kendi yerel mimarisine çevirerek hatasız okur.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 2 — Heterojen Taktik Füze Telemetrisi: Serialization & Endian Safe İletim
"""

class TacticalTelemetryPacket:
    def __init__(self, msg_id: int, range_m: int, speed_mps: int, heading: float):
        self.msg_id = msg_id
        self.range_m = range_m
        self.speed_mps = speed_mps
        self.heading = heading

    def serialize_network_order(self) -> bytes:
        """Host -> Network Byte Order (Big-Endian) dönüşümü (htons, htonl, bit_cast)."""
        # >H: uint16 big-endian, >I: uint32 big-endian, >f: float32 big-endian
        return struct.pack(">H I I f", self.msg_id, self.range_m, self.speed_mps, self.heading)

    @classmethod
    def deserialize_network_order(cls, data: bytes):
        """Network Byte Order -> Host dönüşümü (ntohs, ntohl, bit_cast)."""
        msg_id, range_m, speed_mps, heading = struct.unpack(">H I I f", data)
        return cls(msg_id, range_m, speed_mps, heading)

# 1. Füze Tarafı (x86_64 Little-Endian) Paketi Hazırlar
telemetry_tx = TacticalTelemetryPacket(
    msg_id=0x0101,
    range_m=1000,      # 1000 metre
    speed_mps=850,     # 850 m/s
    heading=85.5       # 85.5 derece
)

wire_bytes = telemetry_tx.serialize_network_order()

# 2. Radar İstasyonu (DSP / Big-Endian veya ARM Little-Endian) Paketi Çözer
telemetry_rx = TacticalTelemetryPacket.deserialize_network_order(wire_bytes)

print()
print("[*] Taktik Füze Telemetri Güvenli İletim Deneyi:")
print(f"  [+] Kabloya Basılan Ham Paket (Hex) : {wire_bytes.hex(' ').upper()}")
print(f"  [+] Çözümlenen Mesaj Kimliği (ID)   : 0x{telemetry_rx.msg_id:04X} ({telemetry_rx.msg_id})")
print(f"  [+] Çözümlenen Hedef Menzili        : {telemetry_rx.range_m} metre (Beklenen: 1000 m)")
print(f"  [+] Çözümlenen Füze Sürati          : {telemetry_rx.speed_mps} m/s (Beklenen: 850 m/s)")
print(f"  [+] Çözümlenen Baş Açısı            : {telemetry_rx.heading:.1f} derece (Beklenen: 85.5°)")

assert telemetry_rx.range_m == 1000
assert telemetry_rx.speed_mps == 850
assert abs(telemetry_rx.heading - 85.5) < 1e-4
print("[HÜCRE 9] Heterojen telemetri iletimi %100 doğrulukla tamamlandı.")
```

---

## 7. Bilerek Bozma (Sabotaj ve Arıza Enjeksiyonu)

Bu bölümde savunma sistemlerinde en çok can yakan iki endianness hatasını simüle edeceğiz:

### Sabotaj 1: Endianness Dönüşümünün Unutulması (1000 Metre -> 3.89 Milyar Metre)
x86 Little-Endian sistem, hedef menzilini ($1000 = 0x000003E8$) ham bellek kopyasıyla (`memcpy(&buf, &range, 4)`) ağa basar. Kabloya `E8 03 00 00` gider.
Alıcı radar bunu Network Byte Order (Big-Endian) kabul edip doğrudan okursa:
- **Sonuç:** $0xE8030000 = 3,892,510,720\ \text{metre}$!
- **Hata Sınıfı:** Katastrofik Hedef Koordinat Kaybı (Füze hedefi bulamaz ve düşer).

### Sabotaj 2: Çift Dönüşüm Tuzağı (Double-Swap Bug)
Geliştirici hem alt katmandaki socket kütüphanesinde hem de üst uygulama katmanında `htons()` çağırır:
- Sayı iki kez ters çevrildiği için tekrar yanlış konak sırasına (Little-Endian) döner.
- Port numarası `8080` ($0x1F90$) -> İlk `htons` -> `36895` ($0x901F$) -> İkinci `htons` -> `8080`! Fakat ağ hattında `90 1F` yerine `1F 90` iletilerek paket yanlış porta yönlendirilir (`ECONNREFUSED`).

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Endianness İhmali ile Hedef Kaçırma & Double-Swap
"""

print()
print("[*] Endianness Sabotaj ve Arıza Enjeksiyon Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: Endianness Dönüşümü Yapılmadan Ham Bellek İletimi
# -----------------------------------------------------------------------------
true_range_m = 1000 # 0x000003E8

# Hatalı Kod: Little-Endian x86 ham bellek sırasıyla gönderildi
raw_le_bytes = EndiannessEngine.uint32_to_bytes(true_range_m, is_big_endian=False)
# raw_le_bytes: [0xe8, 0x03, 0x00, 0x00]

# Radar İstasyonu Network Order (Big-Endian) sanarak okudu:
corrupted_range_m = EndiannessEngine.bytes_to_uint32(raw_le_bytes, is_big_endian=True)

print(f"  [+] Sabotaj 1 Sonuçları (Endian Dönüşüm İhmali):")
print(f"      - Gerçek Hedef Menzili      : {true_range_m} metre (1.00 km)")
print(f"      - Ağdan Okunan Bozuk Menzil : {corrupted_range_m:,} metre ({corrupted_range_m/1e6:.2f} milyon km!)")
print(f"      - Hata Oranı                : %{((corrupted_range_m - true_range_m)/true_range_m)*100:,.1f}")

assert corrupted_range_m == 3892510720, "Beklenen bozuk menzil değeri 3,892,510,720 olmalıdır!"

# -----------------------------------------------------------------------------
# SABOTAJ 2: Çift htons() Tuzağı (Double-Swap)
# -----------------------------------------------------------------------------
original_port = 8080 # 0x1F90

# 1. Dönüşüm (Host -> Network)
swap_once = struct.unpack(">H", struct.pack("<H", original_port))[0] # 0x901F = 36895
# 2. Hatalı İkinci Dönüşüm (Tekrar swap!)
swap_twice = struct.unpack(">H", struct.pack("<H", swap_once))[0] # 0x1F90 = 8080

print(f"  [+] Sabotaj 2 Sonuçları (Double-Swap Port Hatası):")
print(f"      - Hedef Port                : {original_port} (0x{original_port:04X})")
print(f"      - Doğru Network Portu       : {swap_once} (0x{swap_once:04X})")
print(f"      - Çift Swap Sonrası Değer   : {swap_twice} (Hatalı Şekilde Geri Döndü!)")

assert swap_twice == original_port, "Çift swap sayıyı aslına geri döndürmüş olmalıdır."
print("[HÜCRE 11] Tüm sabotaj deneyleri başarıyla tamamlandı ve doğrulandı.")
```

---

## 8. Donanım Seviyesi Dönüşüm Benchmarkı (`BSWAP` Assembly vs Döngü)

Gerçek zamanlı radar ve 5G baz istasyonu sinyal işleme hatlarında saniyede on milyonlarca paket akar. Endian dönüşümünün verimliliği doğrudan hat hızını (throughput) belirler:

### Dönüşüm Yöntemleri:
1. **Yazılımsal Döngü (Naive Byte Shift / Loop):** Baytları tek tek kaydırıp OR işlemi uygulamak ($O(N)$ operasyon, dallanma tahmini ve pipeline gecikmeleri).
2. **Donanım Hızlandırmalı Talimat (`BSWAP` / `REV`):** Modern x86 işlemcilerde `bswap` talimatı tek bir saat çevriminde ($1\ \text{clock cycle}$) 32-bit veya 64-bit bir yazmacın (register) bayt sırasını donanımsal olarak tersine çevirir!

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 4 — Benchmark: 1,000,000 Paket Başına Endian Dönüşüm Performansı
"""

import time
import struct

def run_endianness_benchmark(iterations: int = 1_000_000) -> Dict[str, Any]:
    sample_val = 0xA1B2C3D4
    
    # 1. Yöntem: struct.pack / unpack (C kütüphanesi simülasyonu)
    t0 = time.perf_counter_ns()
    for _ in range(iterations):
        _ = struct.pack(">I", sample_val)
    t1 = time.perf_counter_ns()
    time_struct_ns = t1 - t0
    
    # 2. Yöntem: Saf Bit Manipülasyonu (bswap32 donanım optimizasyonu)
    t0 = time.perf_counter_ns()
    for _ in range(iterations):
        _ = (
            ((sample_val & 0x000000FF) << 24) |
            ((sample_val & 0x0000FF00) << 8)  |
            ((sample_val & 0x00FF0000) >> 8)  |
            ((sample_val & 0xFF000000) >> 24)
        )
    t1 = time.perf_counter_ns()
    time_bswap_ns = t1 - t0

    return {
        "iterations": iterations,
        "struct_duration_ms": time_struct_ns / 1e6,
        "struct_per_op_ns": time_struct_ns / iterations,
        "bswap_duration_ms": time_bswap_ns / 1e6,
        "bswap_per_op_ns": time_bswap_ns / iterations,
        "speedup": time_struct_ns / max(1, time_bswap_ns)
    }

bench_res = run_endianness_benchmark(iterations=500_000)

print()
print(f"[*] Endianness Dönüşüm Benchmarkı ({bench_res['iterations']:,} İşlem):")
print(f"  [+] struct.pack (>I) Toplam Süre   : {bench_res['struct_duration_ms']:.2f} ms ({bench_res['struct_per_op_ns']:.2f} ns/op)")
print(f"  [+] bswap Bit Operasyonu Süresi    : {bench_res['bswap_duration_ms']:.2f} ms ({bench_res['bswap_per_op_ns']:.2f} ns/op)")
print(f"  [+] Donanım Bitwise Hızlanma Oranı : {bench_res['speedup']:.2f}x Daha Hızlı")

assert bench_res['bswap_per_op_ns'] < 500.0, "Dönüşüm operasyonu nanosaniye seviyesinde olmalıdır!"
print("[HÜCRE 13] Benchmark testleri başarıyla tamamlandı.")
```

---

## 9. Gerçek Dünya Taktik Senaryosu: ASELSAN Radar - Görev Bilgisayarı Protokolü

Hava Savunma Taktik Ağında bir radar istasyonundan görev bilgisayarına akan hedef iz paketi protokolü:
- **Paket Başlığı:**
  - `uint16_t sync_word`: `0xAA55` (Senkronizasyon deseni)
  - `uint16_t packet_len`: Toplam paket boyutu
  - `uint32_t track_id`: Benzersiz hedef takip kimliği
  - `int32_t  pos_x_cm`: X ekseni hedef mesafesi (cm ölçekli)
  - `int32_t  pos_y_cm`: Y ekseni hedef mesafesi (cm ölçekli)
  - `uint16_t velocity_mps`: Hedef sürati (m/s)

Bu senaryoda, C++20 standardında endianness-aware bir protokol kodlayıcı/kod çözücü (codec) geliştireceğiz.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 5 — ASELSAN Radar Taktik İz Ayrıştırıcı: Endian-Aware Güvenli Çerçeve İletimi
"""

class RadarTrackFrame:
    SYNC_WORD = 0xAA55

    def __init__(self, track_id: int, x_cm: int, y_cm: int, vel_mps: int):
        self.track_id = track_id
        self.x_cm = x_cm
        self.y_cm = y_cm
        self.vel_mps = vel_mps

    def encode(self) -> bytes:
        """Tüm alanları Network Byte Order (Big-Endian) ile paketler."""
        payload_len = 16 # 2B sync + 2B len + 4B trk + 4B x + 4B y + 2B vel = 18B
        # >H: sync, >H: len, >I: track_id, >i: x_cm, >i: y_cm, >H: vel_mps
        return struct.pack(">H H I i i H", self.SYNC_WORD, 18, self.track_id, self.x_cm, self.y_cm, self.vel_mps)

    @classmethod
    def decode(cls, frame_bytes: bytes):
        if len(frame_bytes) != 18:
            raise ValueError("Geçersiz paket boyutu!")
        sync, plen, trk, x, y, vel = struct.unpack(">H H I i i H", frame_bytes)
        if sync != cls.SYNC_WORD:
            raise ValueError(f"Senkronizasyon hatası! Geçersiz sync word: 0x{sync:04X}")
        return cls(track_id=trk, x_cm=x, y_cm=y, vel_mps=vel)

# Radar Örneği Oluştur (Menzil: X=45km, Y=12km, Hız=340m/s - Ses Hızı)
frame_tx = RadarTrackFrame(track_id=1042, x_cm=4_500_000, y_cm=1_200_000, vel_mps=340)
wire_data = frame_tx.encode()

# Görev Bilgisayarı Paketi Çözer
frame_rx = RadarTrackFrame.decode(wire_data)

print()
print("[*] ASELSAN Radar Taktik Çerçeve Kodlama ve Doğrulama Raporu:")
print(f"  [+] Çerçeve Boyutu               : {len(wire_data)} bayt")
print(f"  [+] Senkronizasyon Kelimesi      : 0x{RadarTrackFrame.SYNC_WORD:04X}")
print(f"  [+] Çözümlenen Hedef İz Kimliği  : #{frame_rx.track_id}")
print(f"  [+] Hedef Konumu (X, Y)          : X = {frame_rx.x_cm/1e5:.2f} km, Y = {frame_rx.y_cm/1e5:.2f} km")
print(f"  [+] Hedef Hızı                   : {frame_rx.vel_mps} m/s (Mach {frame_rx.vel_mps/340:.1f})")

assert frame_rx.track_id == 1042
assert frame_rx.x_cm == 4_500_000
assert frame_rx.y_cm == 1_200_000
assert frame_rx.vel_mps == 340
print("[HÜCRE 15] Taktik radar çerçevesi başarıyla doğrulandı.")
```

---

## 10. 4-Panelli 300 DPI Görselleştirme Mimarisi

Aşağıdaki kod hücresi, Big-Endian ve Little-Endian mimarilerini bellek dizilimi, hedef menzil sapması, donanım `bswap` hızlanması ve ağ paket akışı olmak üzere 4 panelde detaylandıran profesyonel bir karanlık tema (`#0F172A`) görsel panosu üretir:

1. **Panel 1 (Sol Üst): Bellek Bayt Dizilimi Mimarisi (Big-Endian vs Little-Endian):**
   $0x12345678$ 32-bit tamsayısının bellek adreslerindeki ($0, 1, 2, 3$) fiziksel yerleşimi ve MSB/LSB konumları.
2. **Panel 2 (Sağ Üst): Taktik Füze Hedef Menzil Sapması (Logaritmik Ölçek):**
   Doğru Big-Endian menzili ($1,000\ \text{m} = 1.0\ \text{km}$) ile hatalı Little-Endian okunan menzil ($3,892,510,720\ \text{m} = 3.89\ \text{milyon km}$) arasındaki ölümcül uçurum.
3. **Panel 3 (Sol Alt): Endian Dönüşüm Benchmark Performansı:**
   Yazılımsal `struct.pack` fonksiyonu ile donanımsal `bswap` bit manipülasyonunun işlem süresi ve hızlanma faktörü.
4. **Panel 4 (Sağ Alt): Uçtan Uca Ağ İletim Akış Şeması:**
   Host (Little-Endian) $\to$ `htonl()` $\to$ Kablo (Big-Endian) $\to$ `ntohl()` $\to$ Host (Little-Endian) dönüşüm yaşam döngüsü.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_147_network_byte_order_ve_endianness.png")

# Matplotlib stil ve karanlık tema ayarları
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: Bellek Bayt Dizilimi (Big-Endian vs Little-Endian)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

# Kutu Çizimleri
be_bytes = ["0x12\n(MSB)", "0x34", "0x56", "0x78\n(LSB)"]
le_bytes = ["0x78\n(LSB)", "0x56", "0x34", "0x12\n(MSB)"]

# Big-Endian Çizim
ax1.text(0.05, 0.85, "A) BIG-ENDIAN (Network Byte Order):", color='#38BDF8', fontsize=11, fontweight='bold')
for i, b in enumerate(be_bytes):
    rect = plt.Rectangle((0.05 + i*0.22, 0.58), 0.18, 0.22, facecolor='#3B82F6', alpha=0.3, edgecolor='#38BDF8', lw=2)
    ax1.add_patch(rect)
    ax1.text(0.05 + i*0.22 + 0.09, 0.69, b, ha='center', va='center', color='#F8FAFC', fontsize=10, fontweight='bold')
    ax1.text(0.05 + i*0.22 + 0.09, 0.52, f"Adres {i}", ha='center', color='#94A3B8', fontsize=9)

# Little-Endian Çizim
ax1.text(0.05, 0.40, "B) LITTLE-ENDIAN (Host Order - x86_64 / ARM):", color='#10B981', fontsize=11, fontweight='bold')
for i, b in enumerate(le_bytes):
    rect = plt.Rectangle((0.05 + i*0.22, 0.13), 0.18, 0.22, facecolor='#10B981', alpha=0.3, edgecolor='#34D399', lw=2)
    ax1.add_patch(rect)
    ax1.text(0.05 + i*0.22 + 0.09, 0.24, b, ha='center', va='center', color='#F8FAFC', fontsize=10, fontweight='bold')
    ax1.text(0.05 + i*0.22 + 0.09, 0.07, f"Adres {i}", ha='center', color='#94A3B8', fontsize=9)

ax1.set_title("0x12345678 Değerinin Fiziksel Bellek Adresi Dizilimi", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: Taktik Füze Hedef Menzil Sapması (Logaritmik Ölçek)
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

ranges = [true_range_m, corrupted_range_m]
labels = ['Doğru Okuma\n(Big-Endian)', 'Hatalı Okuma\n(Endian İhmali)']
colors_r = ['#10B981', '#EF4444']

bars2 = ax2.bar(labels, ranges, color=colors_r, width=0.45, edgecolor='#334155', linewidth=1.5)
ax2.set_yscale('log')

ax2.text(0, true_range_m * 2.5, f"{true_range_m:,} m\n(1 km)", ha='center', color='#F8FAFC', fontweight='bold', fontsize=11)
ax2.text(1, corrupted_range_m * 0.2, f"{corrupted_range_m:,} m\n(3.89 Milyon km!)", ha='center', color='#F8FAFC', fontweight='bold', fontsize=11)

ax2.set_title("Füze Hedef Menzil Sapması (Logaritmik Ölçek)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax2.set_ylabel("Menzil Mesafesi (Metre - Log)", fontsize=10, color='#94A3B8')
ax2.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Endian Dönüşüm Benchmark Performansı
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

bench_methods = ['struct.pack (>I)', 'bswap Bitwise']
bench_durations = [bench_res['struct_duration_ms'], bench_res['bswap_duration_ms']]
colors_b = ['#F59E0B', '#38BDF8']

bars3 = ax3.bar(bench_methods, bench_durations, color=colors_b, width=0.45, edgecolor='#334155', linewidth=1.5)
for bar, val in zip(bars3, bench_durations):
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 1.0, f"{val:.1f} ms", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=11)

ax3.set_title(f"500,000 Dönüşüm İşlemi Süresi ({bench_res['speedup']:.1f}x Hızlanma)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.set_ylabel("Toplam Süre (Milisaniye - ms)", fontsize=10, color='#94A3B8')
ax3.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: Uçtan Uca Ağ İletim Akış Şeması
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')
ax4.axis('off')

flow_steps = [
    {"x": 0.05, "y": 0.60, "w": 0.25, "h": 0.30, "title": "1. Verici (Host LE)", "desc": "Değer: 1000 m\nBellek: E8 03 00 00\nx86_64 Register", "color": "#3B82F6"},
    {"x": 0.38, "y": 0.60, "w": 0.25, "h": 0.30, "title": "2. htonl() / htobe32", "desc": "Byte-Swap (bswap)\nMSB <-> LSB\n00 00 03 E8", "color": "#F59E0B"},
    {"x": 0.71, "y": 0.60, "w": 0.25, "h": 0.30, "title": "3. Kablo (Network BE)", "desc": "RFC 791 Standardı\nBig-Endian Akış\n00 00 03 E8", "color": "#10B981"},
    {"x": 0.38, "y": 0.15, "w": 0.25, "h": 0.30, "title": "4. ntohl() / be32toh", "desc": "Alıcı Byte-Swap\nHost Formatına Çevir\nE8 03 00 00", "color": "#8B5CF6"},
    {"x": 0.71, "y": 0.15, "w": 0.25, "h": 0.30, "title": "5. Alıcı (Host LE)", "desc": "Değer: 1000 m\nKusursuz Okuma!\nRadar Kilitlendi", "color": "#06B6D4"}
]

for s in flow_steps:
    rect = plt.Rectangle((s['x'], s['y']), s['w'], s['h'], facecolor=s['color'], alpha=0.25, edgecolor=s['color'], lw=2)
    ax4.add_patch(rect)
    ax4.text(s['x'] + s['w']/2, s['y'] + s['h']*0.75, s['title'], ha='center', va='center', color='#F8FAFC', fontsize=9.5, fontweight='bold')
    ax4.text(s['x'] + s['w']/2, s['y'] + s['h']*0.35, s['desc'], ha='center', va='center', color='#94A3B8', fontsize=8.5)

ax4.annotate("", xy=(0.38, 0.75), xytext=(0.30, 0.75), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.71, 0.75), xytext=(0.63, 0.75), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.83, 0.45), xytext=(0.83, 0.60), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.63, 0.30), xytext=(0.71, 0.30), arrowprops=dict(arrowstyle="<-", color="#F8FAFC", lw=2))

ax4.set_title("Uçtan Uca Ağ İletim ve Dönüşüm Döngüsü", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 147 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert corrupted_range_m == 3892510720
assert telemetry_rx.range_m == 1000
assert frame_rx.track_id == 1042

print()
print("[PASS] Gün 147: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

---

## 11. Karşılaştırmalı Analiz ve Mimari Karar Matrisi

Farklı sistemler ve diller arasında bayt sırası yönetimi stratejileri:

| Strateji | Uygun Olduğu Senaryo | Avantajları | Dezavantajları / Riskler |
| :--- | :--- | :--- | :--- |
| **Strict Big-Endian (Network Order)** | İnternet standartları (TCP/IP), Taktik Link-16 | RFC standartlarına tam uyum, deterministik | LE işlemcilerde `bswap` maliyeti |
| **Receiver-Makes-Right (NDR)** | CORBA, Eski DDS standartları | Verici kendi sırasıyla yazar, alıcı uydurur | Başlıkta endian bayrağı gerektirir |
| **Fixed-Point Scaling** | Füze telemetrisi, aviyonik seyrüsefer | Donanımlar arası IEEE-754 belirsizliğini önler | Hassasiyet sınırları önceden bilinmeli |
| **C++20 `std::endian` & Bitcast** | Modern C++20/23 sistem kütüphaneleri | Derleme zamanı (`constexpr`), sıfır UB | C++20 destekli derleyici gerektirir |

---

## 12. Donanım ve İşletim Sistemi Seviyesi Etkileşimler

### CPU Seviyesinde Donanım Talimatları
Modern işlemciler endianness dönüşümünü hızlandırmak için özel silikon devrelerine sahiptir:
1. **x86_64 Mimarisi (`BSWAP`):**
   - `BSWAP %eax` talimatı 32-bit register'ı tek saat vuruşunda ters çevirir.
   - 64-bit için `BSWAP %rax` veya 16-bit için `ROL $8, %ax` kullanılır.
   - GCC ve Clang `__builtin_bswap16`, `__builtin_bswap32` ve `__builtin_bswap64` yerleşiklerini doğrudan bu talimata derler.
2. **ARMv8 / AArch64 Mimarisi (`REV`):**
   - `REV W0, W0` (32-bit ters çevirme).
   - `REV X0, X0` (64-bit ters çevirme).
   - `REV16 W0, W0` (Her 16-bit yarı-kelimeyi kendi içinde ters çevirme).

---

## 13. Güvenlik, Hata Ayıklama ve Taktik İpuçları

### 1. `wireshark` ve `tcpdump` ile Hex Dump İnceleme
Ağda akan bir paketin endianness hatası içerip içermediğini tespit etmek için:
```bash
tcpdump -i eth0 -X -s 0 'port 8080'
```
Eğer giden port hex çıktısında `1F 90` (8080) yerine `90 1F` (36895) olarak görünüyorsa, `htons` dönüşümü unutulmuş demektir!

### 2. GDB ile Bellek İnceleme (`x/4xb`)
```bash
# Değişkenin bellekteki gerçek bayt dizilimini görmek için:
(gdb) x/4xb &target_range_m
# Çıktı Little-Endian ise: 0xe8 0x03 0x00 0x00
# Çıktı Big-Endian ise:    0x00 0x00 0x03 0xe8
```

---

## 14. Günün Mini Uygulaması: Heterojen Taktik Telemetri İstemci-Sunucu

Günün mini uygulamasında, heterojen işlemcilere (x86 Little-Endian ve DSP Big-Endian) sahip iki taktik düğüm arasında; senkronizasyon kelimesi, takip kimliği ve koordinat verilerini Network Byte Order standardında paketleyip hatasız çözen C++20 `RadarTrackFrame` yapısını modelledik.

### Temel Doğrulama Adımları:
1. **Normal Test:** 1000 metre menzilli telemetri paketinin uçtan uca hatasız iletildiğinin doğrulanması.
2. **Hata Testi (Sabotaj):** Endianness ihmal edildiğinde menzilin $1000\ \text{m}$ yerine $3,892,510,720\ \text{m}$'ye fırlayarak hedefi kaybettiğinin matematiksel ispatı.

---

## 15. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **`sizeof(T) == 1` Bayt Verileri Dönüştürmeye Çalışmak:** `char` veya `uint8_t` için `htons()` çağırmak gereksizdir; tek baytlık verilerde endianness kavramı yoktur.
2. **C-Style Cast ile Float Sayıyı Tamsayıya Çevirip `htonl` Uygulamak:** `htonl((uint32_t)float_val)` yazmak sayının ondalık kısmını atar ve veriyi bozar; mutlaka `std::bit_cast` kullanılmalıdır.
3. **Double-Swap (İki Kez Çevirme):** Hem kütüphane hem uygulama katmanında `htons` çağırarak veriyi tekrar bozuk konak sırasına döndürmek.
4. **Metin Tabanlı Protokollerde Endianness Aramak:** JSON, XML veya ASCII string (`"1000"`) taşınırken endianness dönüşümü yapılmaz; endianness yalnızca ikili (binary) tamsayı ve kayan nokta verileri için geçerlidir.

---

## 16. Mülakat ve Saha Deneyimi Soruları (ASELSAN / ROKETSAN / HAVELSAN)

### Soru 1: Bir x86_64 füze güdüm bilgisayarından Big-Endian bir DSP radar kartına binary UDP paketi gönderirken hangi alanlar dönüştürülmelidir?
**Cevap:** Paketteki 1 bayttan büyük (`uint16_t`, `uint32_t`, `int32_t`, `uint64_t`) tüm ikili tamsayı ve kayan nokta alanları `htons()`, `htonl()` veya `htobe64()` ile Network Byte Order'a (Big-Endian) dönüştürülmelidir. Tek baytlık bayraklar (`uint8_t`) ve ASCII metin dizileri dönüştürülmez.

### Soru 2: Big-Endian bir işletim sisteminde çalışan bir programda `htonl(x)` çağrılırsa ne olur?
**Cevap:** Big-Endian sistemlerde Host Byte Order zaten Network Byte Order ile aynıdır. Bu nedenle glibc ve modern derleyicilerde Big-Endian derleme hedefinde `htonl(x)` ve `htons(x)` birer boş makro (no-op: `((x))`) olarak tanımlanır; işlemci hiçbir döngü veya `bswap` komutu çalıştırmaz, sıfır maliyetle veriyi olduğu gibi bırakır.

### Soru 3: C++20'de derleme zamanında mimarinin endianness durumunu nasıl kontrol ederiz?
**Cevap:** `<bit>` başlığı altında yer alan `if constexpr (std::endian::native == std::endian::little)` kontrolü yapılır. Bu sayede kod derlenirken gereksiz dallanmalar tamamen elenir ve sıfır çalışma zamanı ek yüküyle (zero runtime overhead) en uygun donanım talimatı üretilir.

---

## 17. Gün Sonu Özeti ve 3-Cümle Çıkarımı

1. **Network Byte Order ve Endianness Nedir?:** Farklı işlemci mimarilerinin çok baytlı verileri belleğe yazma yönü farkıdır; internet ve taktik savunma ağları standart olarak Big-Endian (en önemli bayt en başta) kabul eder.
2. **Hangi Problemi Çözer?:** x86_64, ARM, PowerPC ve DSP gibi heterojen donanımların ağ üzerinden birbirleriyle sayısal veri alışverişi yaparken değerlerin ters yorumlanıp bozulmasını engeller.
3. **Hangi Trade-off/Hata Sınıfını Getirir?:** Her bayt için dönüşüm (`bswap`) mikro-maliyeti getirir; dönüşümün unutulması durumunda menzilin 1 kilometreden 3.89 milyar kilometreye fırlaması gibi ölümcül hedef koordinat hatalarına yol açar.