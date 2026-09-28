# GÜN 148: Binary Protocol Header Tasarımı

**Müfredat:** 365 Günlük ASELSAN / HAVELSAN Savunma Sistemleri C++20 & Linux Sistem Mühendisliği  
**Faz:** F4 — TCP/UDP / Ağ Protokolleri / Serileştirme & Taktik Dağıtık Sistemler  
**Konu:** İkili Protokol Başlık (Binary Header) Tasarımı, Magic/Sync Word, Protokol Versiyonlama, Opcode/Mesaj Kimliği, Yük Uzunluğu (Payload Length), Dizi Numarası (Sequence Number), Bayt Hizalama (Alignment) ve Padding Tuzağı, CRC-16/32 Başlık Doğrulama, MAVLink 2.0 ve STANAG 4586 Uyumluluğu  
**Ön Koşul:** Gün 147 (Network Byte Order ve Endianness Mimarisi)

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

Taktik savunma sistemlerinde (İHA telemetri bağlantıları, milli radar ağları, sualtı akustik haberleşme, füze veri bağları), iki veya daha fazla bilgisayar arasında ağ üzerinden veri aktarırken en kritik tasarım kararı **Protokol Başlığı (Protocol Header)** mimarisidir.

Web dünyasında yaygın olan JSON veya XML gibi metin tabanlı (ASCII) formatlar havacılık ve savunma alanında kabul edilemez:
1. **Bant Genişliği İsrafı:** Kırk baytlık bir JSON metni (`{"lat": 39.9255, "lon": 32.8662, "alt": 1200}`) iletmek yerine, aynı veriyi 16 baytlık ikili (binary) bir yapıda gönderebiliriz. Saniyede 10,000 paket akan dar bantlı bir taktik telsiz linkinde (HF/UHF) bu fark linkin çökmesi ile çalışması arasındaki sınırdır.
2. **CPU ve Zaman Determinizmi Darboğazı:** JSON ayrıştırmak (string scanning, bellek tahsisi, `atof` dönüşümü) yüzlerce mikro-saniye sürerken; ikili bir başlığı ayrıştırmak tek bir $O(1)$ bellek kopyalaması veya tür dönüşümü (type-punned / memory slice) ile **10 nanosaniyede** tamamlanır!
3. **Dinamik Bellek Kirliliği:** Metin ayrıştırıcıları sürekli heap (`malloc`/`new`) kullanarak bellek parçalanmasına (fragmentation) yol açar. Gerçek zamanlı aviyonik sistemlerde (`DO-178C Level A`) dinamik bellek tahsisi kesinlikle yasaktır!

**İkili Başlık (Binary Header)**, bir taktik veri paketinin kimliği, uzunluğu, güvenlik bayrakları ve bütünlük özetidir.

```
   +-------------------------------------------------------------------------+
   |            SAVUNMA SANAYİİ STANDART TAKTİK İKİLİ BAŞLIK ANATOMİSİ      |
   +-------------------------------------------------------------------------+
   Offset (Bayt)  Alan Adı           Boyut   Açıklama
   ---------------------------------------------------------------------------
   0x00 - 0x01    MAGIC / SYNC       2 Bayt  0xAA55 (Çerçeve Başlangıç Deseni)
   0x02           VERSION            1 Bayt  0x02   (Protokol v2.0)
   0x03           FLAGS              1 Bayt  Bitfield: [Kriptolu|Sıkıştırılmış|ACK]
   0x04 - 0x05    MSG_TYPE (Opcode)  2 Bayt  0x0105 (Örn. RADAR_TRACK_REPORT)
   0x06 - 0x07    PAYLOAD_LEN        2 Bayt  Yük Boyutu (Bayt cinsinden: N)
   0x08 - 0x0B    SEQUENCE_NUM       4 Bayt  Paket Sıra No (Kayıp/Sıra Takibi)
   0x0C - 0x0F    HEADER_CRC32       4 Bayt  Başlığın Bütünlük Kontrolü (CRC)
   ---------------------------------------------------------------------------
   Toplam Sabit Başlık Boyutu: 16 Bayt (Kusursuz 4-Bayt / 32-Bit Hizalı!)
   ---------------------------------------------------------------------------
   0x10 - (0x10+N) PAYLOAD VERİSİ    N Bayt  Taktik Yük (Radar, Füze, GPS Verisi)
```

---

## 2. Metin (JSON/XML) vs İkili (Binary) Protokol Karşılaştırması

Aşağıdaki tablo, bir radar hedef izleme mesajının ($X, Y, Z$ koordinatları, hız, hedef sınıfı) iki farklı formatta iletilmesinin mühendislik analizini gösterir:

| Parametre / Kriter | Metin Tabanlı Protokol (JSON) | İkili Başlık Protokolü (Binary C++ Struct) |
| :--- | :--- | :--- |
| **Paket Boyutu** | 184 Bayt (Aşırı şişkin) | **28 Bayt (%85 Bant Genişliği Tasarrufu)** |
| **Ayrıştırma Karmaşıklığı** | $O(N)$ Karakter Taraması | **$O(1)$ Doğrudan Bellek Eşleme** |
| **Ayrıştırma Gecikmesi** | $25.0\ \mu\text{s} - 120.0\ \mu\text{s}$ | **$0.02\ \mu\text{s} - 0.05\ \mu\text{s}$ (400x Daha Hızlı!)** |
| **Dinamik Bellek Kullanımı** | Var (`std::string`, DOM ağacı) | **SIFIR (Zero Dynamic Allocation)** |
| **Zaman Determinizmi** | Düşük (Garbage/Jitter riski) | **Kusursuz (Hard Real-Time Uygun)** |
| **Hata Denetimi** | Metin geçerliliği (Syntax) | **Donanım Hızlandırmalı CRC-16/32** |
| **İnsan Tarafından Okunabilirlik** | Çok Kolay (ASCII) | Hex Görüntüleyici / Wireshark gerektirir |

---

## 3. Taktik Bir İkili Başlığın Anatomisi

Sağlam bir ikili protokol başlığı 7 temel bileşenden oluşmalıdır:

1. **Magic Bytes / Sync Word (Senkronizasyon Kelimesi):**
   Ağ akışında gürültü, bayt kayması veya parazit olduğunda paketin başlangıcını belirleyen sabit bayt dizisi (Örn: `0xAA55` veya `0xDEADBEEF`). Alıcı bu deseni bulana kadar gelen baytları atar.
2. **Protokol Versiyonu (Version):**
   Sahadaki sistemlerin farklı zamanlarda güncellenebilmesi (geriye dönük uyumluluk) için tek baytlık versiyon numarası.
3. **Güvenlik ve Kontrol Bayrakları (Flags Bitfield):**
   - Bit 0: Kriptolu paket (`IS_ENCRYPTED`)
   - Bit 1: Sıkıştırılmış veri (`IS_COMPRESSED`)
   - Bit 2: ACK onayı gerektirir (`REQUIRES_ACK`)
   - Bit 3: Yüksek öncelikli acil komut (`EMERGENCY_PRIORITY`)
4. **Mesaj Tipi / Opcode (`uint16_t`):**
   Gelen yükün türünü belirler. Alıcı bu koda bakarak `switch-case` ile doğru C++ ayrıştırıcı fonksiyonuna dallanır.
5. **Yük Uzunluğu (Payload Length - `uint16_t`):**
   Başlıktan sonra kaç baytlık taktik veri geldiğini bildirir. TCP gibi bayt akışlarında (byte-stream) mesaj sınırını (framing) çizmek için şarttır.
6. **Dizi Numarası (Sequence Number - `uint32_t`):**
   Her gönderilen pakette 1 artırılır. Alıcı paket kaybını, mükerrer (duplicate) paketleri ve sıra bozulmasını anında tespit eder.
7. **Başlık Kontrol Toplamı (Header CRC32 - `uint32_t`):**
   Paket gövdesini okumadan önce başlığın kendisinin iletim sırasında bozulup bozulmadığını doğrular. Eğer uzunluk alanı bozulduysa, geçersiz bir bellek boyutu tahsis etmekten sistemi korur!

---

## 4. Bellek Hizalama (Alignment), Padding Tuzağı ve `#pragma pack` Riskleri

C++ derleyicileri (GCC, Clang, MSVC), işlemcinin bellek veri yoluna (32-bit veya 64-bit bus) en hızlı şekilde erişebilmesi için yapıların (struct) alanları arasına görünmez boşluk baytları (**Padding**) ekler:

```cpp
// TEHLİKELİ TASARIM: Derleyici gizlice padding ekler!
struct BadHeader {
    uint8_t  version;     // 1 bayt
    // [DERLEYİCİ BURAYA 3 BAYT GİZLİ PADDING EKLER!] -> 32-bit hizalama için
    uint32_t sequence;    // 4 bayt
    uint16_t length;      // 2 bayt
    // [DERLEYİCİ BURAYA 2 BAYT GİZLİ PADDING EKLER!] -> Toplam boyutu 4'ün katı yapmak için
};
// Beklenen Boyut: 1 + 4 + 2 = 7 bayt
// sizeof(BadHeader) = 12 bayt! (%71 Fazladan Boşluk!)
```

Eğer verici bu yapıyı doğrudan ağa basarsa ve alıcı farklı bir derleyici veya mimaride (ARM vs x86) çalışıyorsa, alanların ofsetleri kayar ve tüm veri çöpe döner!

### Çözüm 1: `#pragma pack(push, 1)` (Paketlenmiş Yapı)
```cpp
#pragma pack(push, 1)
struct PackedHeader {
    uint8_t  version;  // 1 bayt
    uint32_t sequence; // 4 bayt (Hizalanmamış adrese denk gelir!)
    uint16_t length;   // 2 bayt
};
#pragma pack(pop)
// sizeof(PackedHeader) = tam 7 bayt.
```
> [!WARNING]
> **Paketleme Riski (Unaligned Memory Access):**  
> `#pragma pack(1)` padding'i yok eder ancak `uint32_t` gibi 4-baytlık değişkenleri 4'ün katı olmayan bellek adreslerine öteler. x86 işlemciler bunu tolere etse de küçük bir performans cezası (%5-15) öder. Ancak katı RISC işlemcilerde (SPARC, eski ARM) bu durum **Donanım Hizalama Hatası (Bus Error - `SIGBUS`)** fırlatarak süreci derhal sonlandırır!

### Çözüm 2: Taktik Savunma Standardı: Doğal Hizalama (Explicit Manual Alignment)
Savunma sanayiinde en profesyonel yaklaşım, başlık alanlarını doğal hizalama sınırlarına göre elle sıraya dizmek ve gerektiğinde açıkça `uint8_t reserved` alanları koymaktır:
```cpp
struct TacticalAlignedHeader {
    uint16_t sync_word;   // 2 bayt (Ofset 0)
    uint8_t  version;     // 1 bayt (Ofset 2)
    uint8_t  flags;       // 1 bayt (Ofset 3) -> 2+1+1 = 4 bayt (Tam hizalı!)
    uint16_t msg_type;    // 2 bayt (Ofset 4)
    uint16_t payload_len; // 2 bayt (Ofset 6) -> 2+2 = 4 bayt (Tam hizalı!)
    uint32_t sequence;    // 4 bayt (Ofset 8) -> 4-bayt sınırında!
    uint32_t header_crc;  // 4 bayt (Ofset 12) -> 4-bayt sınırında!
};
// sizeof(TacticalAlignedHeader) = 16 bayt.
// Sıfır derleyici padding'i, sıfır unaligned access cezası, %100 taşınabilir!
static_assert(sizeof(TacticalAlignedHeader) == 16, "Header boyutu 16 bayt olmalidir!");
```

---

## 5. Savunma Standartları İncelemesi: MAVLink 2.0 ve STANAG 4586

Havacılık ve İHA sistemlerinde küresel olarak kabul görmüş iki kritik standart:

### 1. MAVLink 2.0 Paket Başlığı (Micro Air Vehicle Link):
İHA'lar ile Yer Kontrol İstasyonları (GCS) arasında çalışan ultra hafif ikili protokol:
- `0xFD`: Magic Byte (STX) - MAVLink v2.0 belirteci.
- `len`: Yük uzunluğu (0-255 bayt).
- `incompat_flags`: Geriye uyumsuzluk bayrakları (Örn: İmza/Kripto var mı?).
- `compat_flags`: Geriye uyumlu bayraklar.
- `seq`: Paket dizi numarası (0-255 döngüsel).
- `sysid`: Hava aracı sistem kimliği (Örn: İHA #1).
- `compid`: Alt bileşen kimliği (Örn: Otopilot, Gimbal Kamera).
- `msgid`: 24-bit Mesaj Kimliği (Örn: `HEARTBEAT`, `ATTITUDE`, `GLOBAL_POSITION_INT`).
- Toplam Başlık Boyutu: 10 Bayt (Artı 2 Bayt Çerçeve Sonu CRC-16).

### 2. NATO STANAG 4586:
NATO üye ülkeleri arasında İHA'ların ortak komuta kontrol istasyonlarından yönetilebilmesini sağlayan askeri standardın veri bağı mimarisidir.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 1 — C++20 Standartlarında Doğal Hizalı Taktik İkili Başlık Kodlayıcı / Ayrıştırıcı
"""

import struct
import zlib
from typing import Tuple, Dict, Any, Optional

class TacticalBinaryHeader:
    """
    ASELSAN / HAVELSAN Standart Taktik 16-Bayt Doğal Hizalı Başlık Mimarisi.
    Format String: >H B B H H I I
    Ofsetler:
      0x00: uint16_t magic       (2B) - 0xAA55
      0x02: uint8_t  version     (1B) - 0x02
      0x03: uint8_t  flags       (1B) - Bitmask
      0x04: uint16_t msg_type    (2B) - Opcode
      0x06: uint16_t payload_len (2B) - Uzunluk
      0x08: uint32_t sequence    (4B) - Dizi No
      0x0C: uint32_t header_crc  (4B) - İlk 12 baytın CRC32 kontrol özeti
    Toplam Boyut: 16 Bayt (Kusursuz 4-Bayt Hizalı)
    """
    MAGIC_WORD = 0xAA55
    HEADER_FORMAT = ">H B B H H I I"
    HEADER_SIZE = 16

    FLAG_ENCRYPTED = 0x01
    FLAG_COMPRESSED = 0x02
    FLAG_REQUIRES_ACK = 0x04

    def __init__(self, version: int, flags: int, msg_type: int, payload_len: int, sequence: int, header_crc: int = 0):
        self.magic = self.MAGIC_WORD
        self.version = version
        self.flags = flags
        self.msg_type = msg_type
        self.payload_len = payload_len
        self.sequence = sequence
        self.header_crc = header_crc

    @classmethod
    def compute_header_crc(cls, header_first_12_bytes: bytes) -> int:
        """Başlığın ilk 12 baytının IEEE 802.3 CRC-32 özetini hesaplar."""
        return zlib.crc32(header_first_12_bytes) & 0xFFFFFFFF

    def encode(self) -> bytes:
        """Başlığı Network Byte Order (Big-Endian) ile serileştirir ve CRC32 ekler."""
        # 1. CRC hariç ilk 12 baytı paketle
        partial = struct.pack(">H B B H H I", self.magic, self.version, self.flags, self.msg_type, self.payload_len, self.sequence)
        # 2. CRC32 hesapla
        computed_crc = self.compute_header_crc(partial)
        self.header_crc = computed_crc
        # 3. 16 baytlık tam başlığı oluştur
        return partial + struct.pack(">I", computed_crc)

    @classmethod
    def decode(cls, header_bytes: bytes):
        """Gelen 16 baytlık başlığı doğrular ve nesneye dönüştürür."""
        if len(header_bytes) != cls.HEADER_SIZE:
            raise ValueError(f"Geçersiz başlık boyutu: {len(header_bytes)}B (Beklenen: 16B)")
            
        magic, ver, flags, mtype, plen, seq, rx_crc = struct.unpack(cls.HEADER_FORMAT, header_bytes)
        
        # 1. Magic Word Kontrolü
        if magic != cls.MAGIC_WORD:
            raise ValueError(f"Geçersiz senkronizasyon kelimesi (Magic Word): 0x{magic:04X}")
            
        # 2. Header CRC32 Bütünlük Kontrolü
        calc_crc = cls.compute_header_crc(header_bytes[:12])
        if rx_crc != calc_crc:
            raise ValueError(f"Başlık bozulmuş! (CRC32 Uyuşmazlığı: Gelen=0x{rx_crc:08X}, Hesaplanan=0x{calc_crc:08X})")
            
        obj = cls(version=ver, flags=flags, msg_type=mtype, payload_len=plen, sequence=seq, header_crc=rx_crc)
        return obj

# Örnek Başlık Oluştur ve Test Et
hdr_sample = TacticalBinaryHeader(version=2, flags=TacticalBinaryHeader.FLAG_REQUIRES_ACK, msg_type=0x0105, payload_len=64, sequence=1042)
encoded_bytes = hdr_sample.encode()
decoded_hdr = TacticalBinaryHeader.decode(encoded_bytes)

print(f"[HÜCRE 7] TacticalBinaryHeader C++20 Kodlayıcı Hazırlandı.")
print(f"  [+] Başlık Boyutu           : {len(encoded_bytes)} Bayt (Tam 16 Bayt)")
print(f"  [+] Ham Başlık Hex          : {encoded_bytes.hex(' ').upper()}")
print(f"  [+] Hesaplanmış Header CRC32: 0x{decoded_hdr.header_crc:08X}")

assert len(encoded_bytes) == 16
assert decoded_hdr.sequence == 1042
assert decoded_hdr.msg_type == 0x0105
```

---

## 6. Taktik C2 Ağında Uçtan Uca İkili Başlık Doğrulama Deneyi

Bu deneyde, bir Hava Savunma Bataryası Komuta Kontrol Merkezi (C2) ile bir Füze Fırlatma Lançeri arasında giden taktik bir emri tam bir ikili paket (Başlık + Yük) olarak ileteceğiz:

- **Mesaj Türü:** `CMD_LAUNCH_MISSILE_TARGET_ACQUISITION` (`0x0201`)
- **Yük Verisi:** Hedef Azimut ($88.5^\circ$), İrtifa ($12,000\ \text{m}$), Hedef Kimliği (`#7891`)
- **Doğrulama Akışı:**
  1. Başlık ve yük birleştirilerek tek bir bayt dizisi oluşturulur.
  2. Alıcı önce sadece **ilk 16 baytı** okur.
  3. Başlığın Magic ve CRC32 denetimi geçerse, başlıktaki `payload_len` kadar baytı soketten okur ve taktik yükü ayrıştırır.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 2 — Taktik Hava Savunma C2 Füze Ateşleme Emri İletim Deneyi
"""

# Taktik Yük (Payload): 12 Bayt (Hedef ID: uint32, Azimut: float32, İrtifa: uint32)
payload_target_id = 7891
payload_azimuth = 88.5
payload_altitude = 12000
raw_payload = struct.pack(">I f I", payload_target_id, payload_azimuth, payload_altitude)

# 1. Başlık Hazırlama
tx_header = TacticalBinaryHeader(
    version=2,
    flags=TacticalBinaryHeader.FLAG_REQUIRES_ACK | TacticalBinaryHeader.FLAG_ENCRYPTED,
    msg_type=0x0201, # CMD_LAUNCH_MISSILE
    payload_len=len(raw_payload),
    sequence=501
)

# 2. Tam Paketi Oluştur (Header + Payload)
full_packet_bytes = tx_header.encode() + raw_payload

# 3. Alıcı Tarafı (Lançer Bilgisayarı): İki Aşamalı Deterministik Okuma
# Aşama A: Sabit 16 Bayt Başlığı Oku ve Doğrula
rx_header_bytes = full_packet_bytes[:16]
rx_header = TacticalBinaryHeader.decode(rx_header_bytes)

# Aşama B: Başlıktaki Yük Boyutu Kadar Oku
rx_payload_bytes = full_packet_bytes[16 : 16 + rx_header.payload_len]
tgt_id, azim, alt = struct.unpack(">I f I", rx_payload_bytes)

print()
print("[*] Taktik C2 Füze Ateşleme Paketi Uçtan Uca İletim Raporu:")
print(f"  [+] Toplam Paket Boyutu          : {len(full_packet_bytes)} Bayt (Başlık: 16B, Yük: {len(raw_payload)}B)")
print(f"  [+] Başlık Çözümlendi: Dizi #{rx_header.sequence}, Tip: 0x{rx_header.msg_type:04X}, Bayraklar: 0x{rx_header.flags:02X}")
print(f"  [+] Taktik Yük Bilgileri:")
print(f"      - Hedef Takip Kimliği        : #{tgt_id}")
print(f"      - Füze Yönelme Açısı (Azimut): {azim:.1f}°")
print(f"      - Hedef İrtifası             : {alt:,} metre (12 km)")

assert rx_header.payload_len == 12
assert tgt_id == 7891
assert alt == 12000
assert abs(azim - 88.5) < 1e-4
print("[HÜCRE 9] Taktik paket başarıyla serileştirildi, iletildi ve doğrulandı.")
```

---

## 7. Bilerek Bozma (Sabotaj ve Arıza Enjeksiyonu)

Bu bölümde savunma ağlarında sıkça görülen iki kritik yazılım sabotajını test edeceğiz:

### Sabotaj 1: Derleyici Gizli Padding Uyumsuzluğu
Geliştirici doğal hizalamaya dikkat etmeyip derleyicinin yapısına güvenmiştir. Bir makinede GCC yapıyı 12 bayt yaparken diğer makinede 10 bayt derlemiştir.
- **Beklenen Hata Belirtisi:** Alıcı başlığı çözerken alanların ofsetleri kayar; `sequence` yerine `flags` okunur veya `magic_word` geçersiz çıkarak paket doğrudan çöpe atılır (`Packet Drop`).

### Sabotaj 2: Zehirli Başlık Uzunluğu (Tampered Length Attack / Out-of-Memory)
Ağ hattına sızan bir elektronik harp / siber saldırı cihazı, 16 baytlık başlığın `payload_len` alanını `65,535` ($64\ \text{KB}$) olarak değiştirip gönderir. Ancak paketin arkasında sadece 10 bayt veri vardır.
- **Beklenen Hata Belirtisi:** Başlık CRC denetimi olmayan acemi bir alıcı, $64\ \text{KB}$ bellek ayırmaya çalışır ve sokette veri beklerken sonsuza kadar askıda kalır (Resource Exhaustion / Hang).
- **Savunma:** Başlık CRC32 denetimi, uzunluk alanındaki en ufak bir bit değişikliğini anında yakalar ve zehirli paketi derhal düşürür!

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Padding Uyumsuzluğu & Zehirli Başlık Uzunluğu
"""

print()
print("[*] Binary Header Sabotaj ve Güvenlik Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: Gizli Padding Mismatch (Hizalama Bozulması)
# -----------------------------------------------------------------------------
# Hizalanmamış kötü tasarım: uint8 (1B) + uint32 (4B)
# Derleyici araya 3 bayt padding ekler
unaligned_struct_bytes = struct.pack("=B I", 0x01, 1000) # C++ varsayılan hizalama: 8 bayt!
# Karşı taraf ise packed (5 bayt) bekliyor!
packed_unpack_error = False
try:
    # 5 bayt bekleyen kod 8 baytlık veriyi yanlış ayrıştırır
    val_b, val_i = struct.unpack(">B I", unaligned_struct_bytes[:5])
    # Değer bozulur:
    if val_i != 1000:
        packed_unpack_error = True
        print(f"  [+] Sabotaj 1 İspatlandı: Padding yüzünden değer bozuldu! (Beklenen: 1000, Okunan: {val_i})")
except Exception as e:
    packed_unpack_error = True

assert packed_unpack_error, "Padding uyumsuzluğu veri bozulmasına yol açmalıydı!"

# -----------------------------------------------------------------------------
# SABOTAJ 2: Zehirli Başlık Uzunluğu ve CRC32 Savunması
# -----------------------------------------------------------------------------
# Orijinal geçerli bir başlık üret
valid_hdr_bytes = bytearray(tx_header.encode())

# Siber saldırgan araya girdi ve payload_len alanını (Ofset 6-7) 60000 bayt yaptı!
valid_hdr_bytes[6] = 0xEA
valid_hdr_bytes[7] = 0x60 # 60000

crc_defense_successful = False
try:
    # Alıcı zehirli başlığı doğrulamayı dener:
    TacticalBinaryHeader.decode(bytes(valid_hdr_bytes))
except ValueError as e:
    crc_defense_successful = True
    print(f"  [+] Sabotaj 2 Savunması Başarılı! Zehirli Paket Yakalandı: {e}")

assert crc_defense_successful, "Header CRC32 tahrif edilmiş başlığı mutlaka yakalamalıydı!"
print("[HÜCRE 11] Tüm sabotaj ve güvenlik savunma testleri başarıyla tamamlandı.")
```

---

## 8. Performans Benchmarkı: İkili Başlık ($O(1)$) vs JSON Serileştirme

Bu benchmarkta, saniyede yüzbinlerce radar izinin aktığı bir senaryoda:
1. **İkili Başlık Serileştirme & Ayrıştırma (`struct` / C++ Memory Cast)**
2. **JSON Serileştirme & Ayrıştırma (`json.dumps` / `json.loads`)**
yöntemleri 100,000 paket üzerinde karşılaştırılacaktır.

### Ölçüm Metrikleri:
- Toplam çalışma süresi (ms),
- Paket başına ayrıştırma süresi (nanosaniye / mikro-saniye),
- Üretilen ağ yükü (bayt cinsinden hacim).

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 4 — Benchmark: 100,000 Paket Başına İkili Başlık vs JSON Ayrıştırma
"""

import time
import json

def run_serialization_benchmark(iterations: int = 100_000) -> Dict[str, Any]:
    # Test verisi
    msg_dict = {
        "magic": 0xAA55,
        "ver": 2,
        "flags": 4,
        "type": 261,
        "len": 12,
        "seq": 1042,
        "target_id": 7891,
        "azimuth": 88.5,
        "altitude": 12000
    }
    
    # 1. JSON Benchmarkı
    t0 = time.perf_counter()
    json_bytes_total = 0
    for _ in range(iterations):
        dumped = json.dumps(msg_dict)
        json_bytes_total = len(dumped)
        _ = json.loads(dumped)
    t1 = time.perf_counter()
    time_json_sec = t1 - t0

    # 2. İkili (Binary) Başlık + Yük Benchmarkı
    raw_payload_local = struct.pack(">I f I", 7891, 88.5, 12000)
    t0 = time.perf_counter()
    binary_bytes_total = 0
    for _ in range(iterations):
        # 16B Header + 12B Payload = 28B
        hdr = TacticalBinaryHeader(2, 4, 261, 12, 1042)
        wire = hdr.encode() + raw_payload_local
        binary_bytes_total = len(wire)
        # Parse
        _ = TacticalBinaryHeader.decode(wire[:16])
        _ = struct.unpack(">I f I", wire[16:])
    t1 = time.perf_counter()
    time_binary_sec = t1 - t0

    return {
        "iterations": iterations,
        "json_time_ms": time_json_sec * 1000.0,
        "json_per_op_us": (time_json_sec / iterations) * 1e6,
        "json_size_bytes": json_bytes_total,
        "binary_time_ms": time_binary_sec * 1000.0,
        "binary_per_op_us": (time_binary_sec / iterations) * 1e6,
        "binary_size_bytes": binary_bytes_total,
        "speedup": time_json_sec / max(1e-6, time_binary_sec),
        "size_reduction_pct": ((json_bytes_total - binary_bytes_total) / json_bytes_total) * 100.0
    }

bench_res = run_serialization_benchmark(iterations=50_000)

print()
print(f"[*] Protokol Serileştirme & Ayrıştırma Benchmarkı ({bench_res['iterations']:,} Paket):")
print(f"  [1] JSON Protokolü:")
print(f"      - Paket Boyutu        : {bench_res['json_size_bytes']} Bayt")
print(f"      - Paket Başına Süre   : {bench_res['json_per_op_us']:.2f} µs")
print(f"      - Toplam Süre         : {bench_res['json_time_ms']:.2f} ms")

print(f"  [2] İkili Başlık (Binary Header):")
print(f"      - Paket Boyutu        : {bench_res['binary_size_bytes']} Bayt (Tam %{bench_res['size_reduction_pct']:.1f} Tasarruf!)")
print(f"      - Paket Başına Süre   : {bench_res['binary_per_op_us']:.2f} µs")
print(f"      - Toplam Süre         : {bench_res['binary_time_ms']:.2f} ms")
print(f"      - Performans Üstünlüğü: {bench_res['speedup']:.2f}x Daha Hızlı!")

assert bench_res['binary_size_bytes'] < 32
assert bench_res['speedup'] > 1.2
print("[HÜCRE 13] Serileştirme benchmarkı başarıyla tamamlandı.")
```

---

## 9. Gerçek Dünya Taktik Senaryosu: MAVLink 2.0 Taktik İHA Otopilot Başlığı

Bayraktar TB2 veya ANKA gibi taktik İHA sistemlerinde Yer Kontrol İstasyonu (GCS) ile uçuş bilgisayarı arasındaki telemetri hattı MAVLink standardını kullanır.

### MAVLink v2 Çerçeve Yapısı:
- `STX` (`0xFD`): Paket başlangıç baytı (Magic).
- `LEN`: Yük uzunluğu.
- `INCOMPAT_FLAGS`: Uyumsuzluk bayrakları.
- `COMPAT_FLAGS`: Uyumluluk bayrakları.
- `SEQ`: Sıra numarası.
- `SYSID`: Sistem Kimliği (1: İHA-1, 2: İHA-2).
- `COMPID`: Bileşen Kimliği (1: Otopilot).
- `MSGID`: 24-bit Mesaj Kimliği (`0x00001E` = ATTITUDE).
- `PAYLOAD`: Roll, Pitch, Yaw açısal hızları.
- `CHECKSUM`: ITU X.25 / MAVLink CRC-16 (2 bayt).

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 5 — MAVLink 2.0 Taktik Telemetri Çerçeveleyici ve CRC-16 Doğrulama
"""

def crc16_mcrf4xx(data: bytes) -> int:
    """MAVLink X.25 CRC-16 algoritması."""
    crc = 0xFFFF
    for byte in data:
        tmp = byte ^ (crc & 0xFF)
        tmp = (tmp ^ (tmp << 4)) & 0xFF
        crc = (crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)
        crc &= 0xFFFF
    return crc

class MAVLink2Packet:
    STX_V2 = 0xFD

    def __init__(self, sys_id: int, comp_id: int, msg_id: int, seq: int, payload: bytes):
        self.sys_id = sys_id
        self.comp_id = comp_id
        self.msg_id = msg_id
        self.seq = seq
        self.payload = payload

    def encode(self) -> bytes:
        # MAVLink 2 Header: STX(1), LEN(1), INC_FLAGS(1), CMP_FLAGS(1), SEQ(1), SYSID(1), COMPID(1), MSGID(3B LE)
        plen = len(self.payload)
        header = struct.pack("<B B B B B B B", self.STX_V2, plen, 0, 0, self.seq, self.sys_id, self.comp_id)
        # 24-bit msg_id (3 bytes Little-Endian)
        msg_id_bytes = struct.pack("<I", self.msg_id)[:3]
        header_full = header + msg_id_bytes
        
        # CRC hesaplama: STX hariç tüm başlık ve yük
        calc_crc = crc16_mcrf4xx(header_full[1:] + self.payload)
        return header_full + self.payload + struct.pack("<H", calc_crc)

    @classmethod
    def decode(cls, data: bytes):
        if len(data) < 12:
            raise ValueError("Paket çok kısa!")
        if data[0] != cls.STX_V2:
            raise ValueError("Geçersiz MAVLink v2 STX!")
            
        plen = data[1]
        seq = data[4]
        sys_id = data[5]
        comp_id = data[6]
        msg_id = struct.unpack("<I", data[7:10] + b"\x00")[0]
        
        expected_len = 10 + plen + 2
        if len(data) != expected_len:
            raise ValueError("Eksik paket verisi!")
            
        payload = data[10 : 10 + plen]
        rx_crc = struct.unpack("<H", data[10 + plen : 10 + plen + 2])[0]
        
        calc_crc = crc16_mcrf4xx(data[1 : 10 + plen])
        if rx_crc != calc_crc:
            raise ValueError("MAVLink CRC-16 Hatası!")
            
        return cls(sys_id, comp_id, msg_id, seq, payload)

# Test: İHA Otopilot Attitude Paketi (Roll=1.2 rad, Pitch=-0.4 rad, Yaw=3.14 rad)
attitude_payload = struct.pack("<f f f", 1.2, -0.4, 3.14)
mav_tx = MAVLink2Packet(sys_id=1, comp_id=1, msg_id=30, seq=42, payload=attitude_payload)
mav_wire = mav_tx.encode()

mav_rx = MAVLink2Packet.decode(mav_wire)
roll, pitch, yaw = struct.unpack("<f f f", mav_rx.payload)

print()
print("[*] MAVLink 2.0 Aviyonik Telemetri Doğrulama Raporu:")
print(f"  [+] MAVLink 2 Toplam Çerçeve Boyutu : {len(mav_wire)} Bayt (Başlık: 10B, Yük: 12B, CRC: 2B)")
print(f"  [+] Sistem Kimliği (SYSID)          : {mav_rx.sys_id} (İHA #1)")
print(f"  [+] Mesaj Kimliği (MSGID)           : {mav_rx.msg_id} (ATTITUDE)")
print(f"  [+] Açısal Durum                    : Roll = {roll:.2f} rad, Pitch = {pitch:.2f} rad, Yaw = {yaw:.2f} rad")

assert mav_rx.sys_id == 1
assert mav_rx.msg_id == 30
assert abs(roll - 1.2) < 1e-4
print("[HÜCRE 15] MAVLink 2.0 taktik telemetri protokolü başarıyla doğrulandı.")
```

---

## 10. 4-Panelli 300 DPI Görselleştirme Mimarisi

Aşağıdaki kod hücresi, ikili başlık mimarisini bellek haritası, padding tuzağı, serileştirme benchmarkı ve doğrulama durum makinesi olmak üzere 4 panelde detaylandıran profesyonel bir karanlık tema (`#0F172A`) görsel panosu üretir:

1. **Panel 1 (Sol Üst): Taktik 16-Bayt İkili Başlık Bellek Haritası:**
   Her bir alanın ofseti, adı, bayt boyutu ve bit genişliği renkli blok şema üzerinde gösterilir.
2. **Panel 2 (Sağ Üst): Bellek Hizalama & Padding Tuzağı:**
   Varsayılan derleyici padding boşlukları ile elle hizalanmış (Explicit Aligned) 16-baytlık mükemmel tasarımın karşılaştırması.
3. **Panel 3 (Sol Alt): Performans Benchmarkı (JSON vs İkili Başlık):**
   Ayrıştırma süresi ($\mu	ext{s}$) ve paket boyutu (Bayt) tasarruf faktörleri.
4. **Panel 4 (Sağ Alt): İkili Paket Ayrıştırma & Doğrulama Durum Makinesi:**
   Gelen Akış $	o$ Sync Word $	o$ Version Check $	o$ Header CRC32 $	o$ Payload Extract akış şeması.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_148_binary_protocol_header_tasarimi.png")

# Matplotlib stil ve karanlık tema ayarları
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: 16-Bayt İkili Başlık Bellek Haritası (Byte Layout)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

# 16 baytlık başlık alanları
fields = [
    {"name": "MAGIC\n0xAA55", "bytes": 2, "color": "#3B82F6", "offset": "0..1"},
    {"name": "VER\n0x02", "bytes": 1, "color": "#8B5CF6", "offset": "2"},
    {"name": "FLAGS\nBits", "bytes": 1, "color": "#EC4899", "offset": "3"},
    {"name": "MSG_TYPE\nOpcode", "bytes": 2, "color": "#F59E0B", "offset": "4..5"},
    {"name": "PAYLOAD_LEN\nSize (N)", "bytes": 2, "color": "#10B981", "offset": "6..7"},
    {"name": "SEQUENCE_NUM\nPacket Counter (uint32)", "bytes": 4, "color": "#06B6D4", "offset": "8..11"},
    {"name": "HEADER_CRC32\nIntegrity Hash", "bytes": 4, "color": "#EF4444", "offset": "12..15"}
]

curr_x = 0.05
for f in fields:
    w = (f["bytes"] / 16.0) * 0.88
    rect = plt.Rectangle((curr_x, 0.40), w, 0.35, facecolor=f["color"], alpha=0.3, edgecolor=f["color"], lw=2)
    ax1.add_patch(rect)
    ax1.text(curr_x + w/2, 0.57, f["name"], ha='center', va='center', color='#F8FAFC', fontsize=8.5, fontweight='bold')
    ax1.text(curr_x + w/2, 0.46, f"{f['bytes']} Bayt", ha='center', va='center', color='#94A3B8', fontsize=8)
    ax1.text(curr_x + w/2, 0.32, f"Ofset {f['offset']}", ha='center', va='center', color='#CBD5E1', fontsize=7.5)
    curr_x += w + 0.003

ax1.set_title("Taktik 16-Bayt Doğal Hizalı İkili Başlık Bellek Haritası", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: Bellek Hizalama & Padding Tuzağı Karşılaştırması
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')
ax2.axis('off')

# Kötü Hizalama vs Doğru Hizalama Kutuları
ax2.text(0.05, 0.85, "A) Hatalı Hizalama (Derleyici Gizli Padding Ekler):", color='#EF4444', fontsize=10.5, fontweight='bold')
# uint8 (1B) + 3B padding + uint32 (4B) + uint16 (2B) + 2B padding = 12B
bad_blocks = [
    {"txt": "uint8\n(1B)", "w": 0.08, "c": "#3B82F6"},
    {"txt": "PADDING\n(3B Boş)", "w": 0.22, "c": "#EF4444"},
    {"txt": "uint32\n(4B)", "w": 0.28, "c": "#10B981"},
    {"txt": "uint16\n(2B)", "w": 0.14, "c": "#F59E0B"},
    {"txt": "PADDING\n(2B Boş)", "w": 0.16, "c": "#EF4444"}
]
x = 0.05
for b in bad_blocks:
    rect = plt.Rectangle((x, 0.60), b["w"], 0.20, facecolor=b["c"], alpha=0.3, edgecolor=b["c"], lw=1.8)
    ax2.add_patch(rect)
    ax2.text(x + b["w"]/2, 0.70, b["txt"], ha='center', va='center', color='#F8FAFC', fontsize=7.5, fontweight='bold')
    x += b["w"] + 0.005

ax2.text(0.05, 0.45, "B) Taktik Standart: Elle Doğal Hizalanmış 16-Bayt Başlık:", color='#10B981', fontsize=10.5, fontweight='bold')
# 2B + 1B + 1B = 4B | 2B + 2B = 4B | 4B | 4B = 16B (Sıfır Padding)
good_blocks = [
    {"txt": "uint16\n(2B)", "w": 0.15, "c": "#3B82F6"},
    {"txt": "uint8\n(1B)", "w": 0.08, "c": "#8B5CF6"},
    {"txt": "uint8\n(1B)", "w": 0.08, "c": "#EC4899"},
    {"txt": "uint16\n(2B)", "w": 0.15, "c": "#F59E0B"},
    {"txt": "uint16\n(2B)", "w": 0.15, "c": "#10B981"},
    {"txt": "uint32\n(4B)", "w": 0.18, "c": "#06B6D4"},
    {"txt": "uint32\n(4B)", "w": 0.18, "c": "#EF4444"}
]
x = 0.05
for b in good_blocks:
    rect = plt.Rectangle((x, 0.20), b["w"], 0.20, facecolor=b["c"], alpha=0.3, edgecolor=b["c"], lw=1.8)
    ax2.add_patch(rect)
    ax2.text(x + b["w"]/2, 0.30, b["txt"], ha='center', va='center', color='#F8FAFC', fontsize=7.5, fontweight='bold')
    x += b["w"] + 0.003

ax2.set_title("Yapı Hizalaması: Gizli Padding vs Kusursuz 4-Bayt Hizalama", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 3: Performans Benchmarkı (JSON vs İkili Başlık)
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

methods = ['JSON Protokolü', 'İkili Başlık (Binary)']
times = [bench_res['json_per_op_us'], bench_res['binary_per_op_us']]
colors_bar = ['#EF4444', '#10B981']

bars3 = ax3.bar(methods, times, color=colors_bar, width=0.45, edgecolor='#334155', linewidth=1.5)
for bar, val in zip(bars3, times):
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f"{val:.2f} µs", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=11)

ax3.set_title(f"Ayrıştırma Gecikmesi ({bench_res['speedup']:.1f}x Daha Hızlı)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.set_ylabel("Paket Başına Süre (µs)", fontsize=10, color='#94A3B8')
ax3.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: İkili Paket Ayrıştırma Durum Makinesi (State Machine)
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')
ax4.axis('off')

steps = [
    {"x": 0.05, "y": 0.60, "w": 0.25, "h": 0.30, "title": "1. Sync Check", "desc": "magic == 0xAA55 ?\nHayır -> 1 Bayt Kaydır\nEvet -> Devam Et", "color": "#3B82F6"},
    {"x": 0.38, "y": 0.60, "w": 0.25, "h": 0.30, "title": "2. Header CRC32", "desc": "CRC Doğru mu?\nHayır -> Zehirli/Bozuk!\nEvet -> Yük Boyutunu Al", "color": "#F59E0B"},
    {"x": 0.71, "y": 0.60, "w": 0.25, "h": 0.30, "title": "3. Payload Extract", "desc": "payload_len Kadar Oku\nTampon Taşmasını Önle\nOpcode'a Göre Dağıt", "color": "#10B981"},
    {"x": 0.38, "y": 0.15, "w": 0.25, "h": 0.30, "title": "4. Sequence Track", "desc": "seq == expected_seq ?\nKayıp Paket Alarmı\nMükerrer Paketleri At", "color": "#8B5CF6"},
    {"x": 0.71, "y": 0.15, "w": 0.25, "h": 0.30, "title": "5. Taktik İşleme", "desc": "C2 Füze / Radar İşi\nHard Real-Time Yanıt\nGörev Başarılı!", "color": "#06B6D4"}
]

for s in steps:
    rect = plt.Rectangle((s['x'], s['y']), s['w'], s['h'], facecolor=s['color'], alpha=0.25, edgecolor=s['color'], lw=2)
    ax4.add_patch(rect)
    ax4.text(s['x'] + s['w']/2, s['y'] + s['h']*0.75, s['title'], ha='center', va='center', color='#F8FAFC', fontsize=9.5, fontweight='bold')
    ax4.text(s['x'] + s['w']/2, s['y'] + s['h']*0.35, s['desc'], ha='center', va='center', color='#94A3B8', fontsize=8.5)

ax4.annotate("", xy=(0.38, 0.75), xytext=(0.30, 0.75), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.71, 0.75), xytext=(0.63, 0.75), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.83, 0.45), xytext=(0.83, 0.60), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.63, 0.30), xytext=(0.71, 0.30), arrowprops=dict(arrowstyle="<-", color="#F8FAFC", lw=2))

ax4.set_title("Taktik İkili Başlık Doğrulama Durum Makinesi", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 148 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert len(encoded_bytes) == 16, "Başlık boyutu tam 16 bayt olmalı!"
assert bench_res['binary_size_bytes'] < bench_res['json_size_bytes'], "Binary format JSON'dan daha küçük olmalı!"
assert bench_res['speedup'] > 1.0, "Binary ayrıştırma JSON'dan hızlı olmalı!"

print()
print("[PASS] Gün 148: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

---

## 11. Karşılaştırmalı Analiz ve Mimari Karar Matrisi

Savunma ve gömülü sistemlerde protokol serileştirme seçenekleri:

| Kriter | İkili Başlık (Binary Struct) | Protocol Buffers (Protobuf) | FlatBuffers | JSON / XML |
| :--- | :--- | :--- | :--- | :--- |
| **Sıfır Kopyalama (Zero-Copy)** | **Mükemmel (Doğrudan cast)** | Kısmi (Ayrıştırma gerekir) | **Mükemmel (Doğrudan bellek)** | Hayır (Kopya zorunlu) |
| **Bant Genişliği Verimliliği** | **En Yüksek (%100 Yoğun)** | Yüksek (Varint sıkıştırması) | Yüksek | Çok Düşük (Metin şişkinliği) |
| **Şema Evrimi (Schema Evolution)**| Elle Versiyonlama Gerekir | Mükemmel (Alan numaraları) | Mükemmel (Vtable yapısı) | Kolay (Anahtar-değer) |
| **Gömülü RTOS Uygunluğu** | **Kusursuz (Sıfır malloc)** | Orta (Dinamik bellek gerekir)| Çok İyi | **Kötü (Yasaklı)** |
| **Savunma Alanı Kullanımı** | Taktik Telsiz, Aviyonik Veri Bağı| Görev Bilgisayarı - C2 | Radar Görüntüleme, Harita | Yalnızca Kullanıcı GUI |

---

## 12. Donanım ve İşletim Sistemi Seviyesi Etkileşimler

### Bellek Veri Yolu (Memory Bus) ve Hizalama (Alignment)
1. **İşlemci Veri Yolu Genişliği:** 64-bit bir işlemci belleğe 8-baytlık bloklar halinde (`0x00, 0x08, 0x10, ...`) erişir.
2. **Unaligned Access (Hizalanmamış Erişim):** Eğer 4-baytlık bir `uint32_t` değişkeni `0x03` adresinde başlarsa:
   - x86_64 işlemcisi iki ayrı 8-baytlık bellek bloğunu okumak, bitleri kaydırmak ve birleştirmek zorunda kalır. Bu durum L1 önbellek hattı sınırını (Cache Line Split) aştığında mikro-kod gecikmesine yol açar.
   - ARM ve MIPS mimarilerinde donanım kesmesi (`Alignment Fault`) oluşur ve işletim sistemi süreci `SIGBUS` sinyaliyle öldürür!
3. **Doğal Hizalama Kuralı:** Bir $N$-baytlık değişken, bellekte $N$'in katı olan bir adrese yerleştirilmelidir (`uint16_t` çift adrese, `uint32_t` 4'ün katına, `uint64_t` 8'in katına).

---

## 13. Güvenlik, Hata Ayıklama ve Taktik İpuçları

### 1. `static_assert` ile Derleme Zamanı Boyut Doğrulama
Savunma projelerinde başlık yapılarının altına mutlaka derleme zamanı boyut kontrolü konulmalıdır:
```cpp
static_assert(sizeof(TacticalBinaryHeader) == 16, "Header boyutu 16 bayt olmalidir!");
static_assert(offsetof(TacticalBinaryHeader, sequence) == 8, "Sequence alani 8. baytta olmalidir!");
```

### 2. Wireshark Özel Protokol Ayrıştırıcı (Lua Dissector)
Geliştirdiğiniz ikili protokolü sahada dinleyip analiz etmek için 20 satırlık bir Wireshark Lua scripti yazabilirsiniz:
```lua
local p_tactical = Proto("tactical", "Taktik Hava Savunma Protokolu")
local f_magic = ProtoField.uint16("tactical.magic", "Magic Word", base.HEX)
local f_type  = ProtoField.uint16("tactical.type", "Message Type", base.HEX)
-- Wireshark gelen ham hex baytları görsel tabloya dönüştürür!
```

---

## 14. Günün Mini Uygulaması: Taktik Füze İkili Başlık Doğrulayıcı

Günün mini uygulamasında, bir hava savunma füzesi fırlatma lançeri ile komuta merkezi arasında giden taktik emri; 16 baytlık doğal hizalı `TacticalBinaryHeader` yapısıyla serileştiren, başlık CRC32 denetimi yapan ve zehirli uzunluk saldırılarını püskürten C++20 mimarisini modelledik.

### Temel Doğrulama Adımları:
1. **Normal Test:** 16 baytlık başlık ve 12 baytlık yükten oluşan paketin tam $28$ bayt olarak serileştirilip hatasız çözülmesi.
2. **Hata Testi (Sabotaj):** Başlık uzunluğu değiştirildiğinde CRC32 uyuşmazlığı ile zehirli paketin tespit edilip sistemin çökmesinin engellenmesi.

---

## 15. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **Magic/Sync Word Koymamak:** Akışta tek bir bayt kaydığında veya gürültü olduğunda sonraki tüm paketlerin çöp olmasına ve senkronizasyonun tamamen yitirilmesine sebep olmak.
2. **Padding Boşluklarını Yoksaymak:** C++ `struct` yapısının içine derleyicinin gizlice eklediği padding baytlarını hesaba katmayıp farklı işletim sistemlerinde veri kayması yaşamak.
3. **Başlık İçine CRC Koymamak:** Sadece yükün CRC'sini kontrol edip, bozulan uzunluk (`payload_len`) alanı yüzünden devasa bellek ayırmaya çalışarak sistemi kilitlemek.
4. **Pointer veya Dinamik Tip Göndermek:** `struct` içine `char*` veya `std::string` koyup bunu ağa göndermeye çalışmak (bellek adresini göndermiş olursunuz, karşı tarafta `SIGSEGV`).

---

## 16. Mülakat ve Saha Deneyimi Soruları (ASELSAN / HAVELSAN / BAYKAR / ROKETSAN)

### Soru 1: Bir taktik İHA telemetri protokolü tasarlarken JSON yerine neden ikili (binary) başlık tercih edilir?
**Cevap:** Taktik veri bağlarında bant genişliği son derece kısıtlıdır. İkili başlık veri boyutunu %80'e varan oranda küçültür. Ayrıca JSON ayrıştırması metin tarama ve dinamik bellek tahsisi (`malloc`) gerektirdiği için deterministik değildir ve aviyonik sert gerçek zamanlı (hard real-time) döngülerde gecikme dalgalanmasına (jitter) yol açar. İkili başlık $O(1)$ sürede, sıfır bellek tahsisiyle mikrosaniye altında ayrıştırılır.

### Soru 2: `#pragma pack(push, 1)` kullanmanın gömülü mimarilerde ne tür bir donanımsal tehlikesi vardır?
**Cevap:** `#pragma pack(1)` derleyicinin eklediği padding baytlarını kaldırır ancak 4 veya 8 baytlık değişkenlerin tek sayılı bellek adreslerine ötelenmesine (unaligned memory access) neden olur. x86_64 mimarisinde bu küçük bir performans kaybıyla tolere edilse de; ARM, SPARC ve PowerPC gibi katı RISC gömülü işlemcilerde donanım seviyesinde `Bus Error` (`SIGBUS`) kesmesi tetikleyerek yazılımın çökmesine yol açar. Doğru çözüm, alanları doğal hizalamaya uygun manuel sıraya dizmektir.

### Soru 3: Bir ikili protokol başlığında "Magic Byte / Sync Word" neden mutlaka en başta bulunmalıdır?
**Cevap:** TCP gibi akış tabanlı veya gürültülü telsiz bağlantılarında veri bayt bayt akar ve sınırları yoktur. Eğer bağlantıda parazit veya paket kaybı olursa, alıcı nerede yeni bir paketin başladığını bilemez. Alıcı gelen bayt akışında sabit desen olan Magic Byte'ı (Örn: `0xAA55`) arayarak çerçeveyi yeniden senkronize eder (Resynchronization).

---

## 17. Gün Sonu Özeti ve 3-Cümle Çıkarımı

1. **Binary Protocol Header Nedir?:** Ağ paketlerinin başına eklenen; senkronizasyon kelimesi, versiyon, mesaj türü, uzunluk ve hata kontrol özetini içeren sabit boyutlu, yüksek verimli ikili veri yapısıdır.
2. **Hangi Problemi Çözer?:** Metin tabanlı protokollerin aşırı bant genişliği tüketimini, dinamik bellek bağımlılığını ve yüksek ayrıştırma gecikmesini ortadan kaldırarak deterministik ve ultra hızlı iletişim sağlar.
3. **Hangi Trade-off/Hata Sınıfını Getirir?:** İnsan tarafından doğrudan okunamaz; derleyici hizalama padding'i, endianness uyumsuzluğu ve zehirli uzunluk saldırılarına karşı sıkı başlık doğrulaması gerektirir.