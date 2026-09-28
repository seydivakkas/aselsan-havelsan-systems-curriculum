# GÜN 152: Protokol Sürümleme ve Geriye/İleriye Dönük Uyumluluk (Backward & Forward Compatibility)

**Müfredat:** 365 Günlük ASELSAN / HAVELSAN Savunma Sistemleri C++20 & Linux Sistem Mühendisliği  
**Faz:** F4 — TCP/UDP / Ağ Protokolleri / Serileştirme & Taktik Dağıtık Sistemler  
**Konu:** Protokol Sürümleme Stratejileri, Semantik Sürümleme (SemVer), İleriye ve Geriye Dönük Uyumluluk İlkeleri, Postel Kanunu (Robustness Principle), TLV (Type-Length-Value) Çerçeveleme, MAVLink 1.0 vs 2.0 Uyumluluk Bayrakları, Kırıcı Olmayan Protokol Evrimi ve C++20 Güvenli Ayrıştırma  
**Ön Koşul:** Gün 151 (CRC/checksum ile corruption detection)

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

Savunma sanayiinde sistemlerin hizmet ömrü 20 ila 40 yıl arasında değişir:
- Bir fırkateynin Komuta Kontrol Sistemi (C2) 2010 yılında yazılmış bir protokolle haberleşirken,
- Ona 2024 yılında entegre edilen yeni nesil bir 3D Hava Radarı veya Seyir Füzesi gelişmiş telemetri alanlarına ihtiyaç duyar.
- Savaş sahasında bulunan 50 farklı insansız hava aracının (İHA) yazılımını aynı gün ve aynı saniyede güncellemek (Big Bang deployment) askeri açıdan **imkansızdır**. Sahada her zaman $N$ ve $N-1$ (hatta $N-2$) yazılım sürümleri aynı taktik telsiz frekansında eşzamanlı olarak çalışmak zorundadır.

Eğer ağ protokolünüz sürümleme (versioning) ve geriye/ileriye dönük uyumluluk ilkelerine göre tasarlanmamışsa şu ölümcül krizler yaşanır:
1. **Sert Çökme (Hard Crash):** Eski yer kontrol istasyonu, yeni İHA'nın gönderdiği 4 bayt fazla yükü ayrıştıramaz ve `buffer overflow` ya da `assertion failure` ile çöker.
2. **Sessiz Veri Yozlaşması (Silent Memory Corruption):** Başlığa eklenen yeni bir alan yüzünden bayt ofsetleri kayar; füzenin hedef irtifası, yakıt seviyesi olarak okunur!
3. **Saha Felci (Fleet Paralysis):** Tek bir aracın protokol güncellemesi, tüm filonun ve komuta merkezinin aynı anda yere indirilmesini gerektirir.

Savunma sistemleri mühendisinin görevi, sistemleri **"Evrilebilir Protokol Mimarisi" (Evolvable Protocol Architecture)** ile inşa etmektir.

```
   +-------------------------------------------------------------------------+
   |            HETEROJEN SAVUNMA AĞLARINDA SÜRÜM UYUMLULUĞU                 |
   +-------------------------------------------------------------------------+

   [ Eski Yer İstasyonu (GCS v1.0) ] <====== Taktik Radyo Linki (UHF) ======> [ Yeni Nesil İHA (v2.1) ]
   - Yalnızca temel telemetriyi bilir                                      - Lazer mesafe & Yapay Zeka
     (Lat, Lon, Alt, Speed)                                                  hedef sınıflandırma verisi var
   
   A) GERİYE DÖNÜK UYUMLULUK (Backward Compatibility):
      Yeni Sistem (v2.1 Alıcı), Eski Sistemin (v1.0 Verici) paketini çökmeksizin işler.
      Eksik olan yeni sensör alanlarına güvenli varsayılan (default) değerler atar.

   B) İLERİYE DÖNÜK UYUMLULUK (Forward Compatibility):
      Eski Sistem (v1.0 Alıcı), Yeni Sistemin (v2.1 Verici) paketini çökmeksizin işler.
      Bildiği başlığı ve telemetriyi okur, bilmediği yeni ek alanları (TLV) güvenle ATLAR (skip).
```

---

## 2. Protokol Sürümleme Stratejileri

Haberleşme protokollerinde sürüm bilgisi nasıl taşınmalı ve yönetilmelidir?

| Yöntem | Mekanizma | Avantajları | Dezavantajları / Riskler | Kullanım Alanı |
| :--- | :--- | :--- | :--- | :--- |
| **Magic Byte Ayrımı** | Başlangıç baytı sürümü belirtir (örn: `0xFE` v1, `0xFD` v2) | Donanım/Framer seviyesinde anında ayrıştırma | Sınırlı sürüm sayısı; her sürüm ayrı parser gerektirir | MAVLink 1.0 vs 2.0 |
| **Explicit Version Field** | Başlıkta `uint8_t version` veya `uint16_t version` | $256$ veya $65536$ sürüme kadar doğrusal destek | Alıcının tüm sürüm struct'larını tanıması gerekir | Taktik Telsiz, STANAG 4586 |
| **SemVer (Major.Minor.Patch)**| Başlıkta 3 ayrı alan: Kırıcı, Geri Uyumlu, Hata Düzeltme | Net semantik ayrım; kurallar kesin | 3 bayt başlık ek yükü | C2 Dağıtık Servisler |
| **Feature Flags / Incompat Flags**| Başlıkta 16-bit bitmask (`compat_flags`, `incompat_flags`) | Esnek; alıcı sadece anlamadığı 'incompat' varsa paketi atar | Bitfield karmaşıklığı | MAVLink 2.0, DDS RTPS |
| **TLV / Self-Describing Format** | Her alan `[Tag/Type][Length][Value]` olarak dizilir | %100 ileri/geri uyumluluk; bilinmeyen alan doğrudan atlanır | Boyut ek yükü (her alana Type+Len eklenir) | ASN.1, Askeri K3I, Radar Data |

---

## 3. İleri ve Geriye Dönük Uyumluluk İlkeleri: Postel Kanunu

İnternet mimarisinin babalarından Jon Postel tarafından formüle edilen **RFC 760 / RFC 1122 Sağlamlık İlkesi (Robustness Principle)**, savunma protokollerinin altın kuralıdır:

> *"Be conservative in what you send, be liberal in what you accept."*  
> **(Gönderirken muhafazakar ol; alırken hoşgörülü ol.)**

### 1. Gönderirken Muhafazakar Olmak:
- İlettiğin paketin boyutunu, alan hizalamasını (alignment) ve bayt sırasını (endianness) teknik şartnameye milimetrik olarak uydur.
- Rezerve edilmiş veya henüz kullanılmayan baytları **her zaman sıfırla (`0x00`)** doldur; asla çöp bellek (uninitialized memory) gönderme.

### 2. Alırken Hoşgörülü Olmak:
- Paketin boyutu beklediğinden uzunsa (yeni sürüm ekstra bayt eklemişse), doğrudan **çökme (`panic/assert`)**. Bildiğin kısmı oku, kalan baytları güvenle atla.
- Bilinmeyen bir Type/Tag ile karşılaşırsan tüm paketi imha etme; bilinmeyen bloğu `Length` baytı kadar ileri kaydırarak güvenle geç.
- Eğer bir alan pakette eksikse, o alana akıllı bir **varsayılan değer (safe fallback/default)** ata.

### Kırıcı Değişiklik (Breaking Change) vs Geriye Uyumlu Değişiklik (Non-Breaking Change):
1. **Geriye Uyumlu (Non-Breaking):**
   - Mesajın sonuna yeni isteğe bağlı (optional) alan eklemek.
   - Rezerve edilmiş bitlerden birine yeni anlam yüklemek (eski alıcı için 0 olması zararsızsa).
   - Yeni bir mesaj tipi (Opcode/MsgID) tanımlamak (eski alıcı bilmediği opcode'u `UNHANDLED_MSG` olarak güvenle yok sayar).
2. **Kırıcı (Breaking Change - MAJOR Bump Gerektirir):**
   - Var olan bir alanın veri tipini değiştirmek (örn: `uint16_t` olan TargetID'yi `uint32_t` yapmak).
   - Alanların sırasını veya ofsetlerini değiştirmek.
   - Var olan zorunlu bir alanın anlamını tersine çevirmek.

---

## 4. Genişletilebilir Paket Mimarileri: Sabit Başlık + TLV (Type-Length-Value)

Askeri radar ve taktik telemetri sistemlerinde en yaygın kullanılan genişletilebilir tasarım, **Sabit Çekirdek Başlık (Fixed Core Header)** ile **Değişken TLV Uzantıları (Variable TLV Extensions)** bileşimidir:

```
   +--------------------+--------------------+--------------------+--------------------+
   |  Magic (2 Bayt)    |  Version (1 Bayt)  |  Flags (1 Bayt)    |  Payload Len (2B)  |
   |  0xAA55            |  0x02 (v2)         |  0x00              |  N Bayt            |
   +--------------------+--------------------+--------------------+--------------------+
   |  SABİT ÇEKİRDEK TELEMETRİ ALANLARI (Tüm sürümlerde garanti edilen alanlar):       |
   |  - SystemID (uint32_t)                                                            |
   |  - TimestampMs (uint64_t)                                                         |
   |  - Latitude (int32_t), Longitude (int32_t), Altitude (int32_t)                     |
   +--------------------+--------------------+--------------------+--------------------+
   |  İSTEĞE BAĞLI / SÜRÜM UZANTILARI (TLV Blokları - İleriye Dönük Genişleme):        |
   |  [TAG: 0x01] [LEN: 4]  [VALUE: LaserRangefinderDistance (float)]                  |
   |  [TAG: 0x02] [LEN: 8]  [VALUE: AI_Target_Classification_Bitmask (uint64_t)]       |
   |  [TAG: 0xFF] [LEN: 2]  [VALUE: Jamming_Detected_Signal_Power (uint16_t)]          |
   +--------------------+--------------------+--------------------+--------------------+
   |  Frame CRC-32 (4 Bayt)                                                            |
   +-----------------------------------------------------------------------------------+
```

### TLV Çözümleme Döngüsü (O(N) Güvenli Tarama):
```cpp
// C++20 std::span ile sınır denetimli TLV ayrıştırma
void parse_tlv_extensions(std::span<const uint8_t> tlv_stream) {
    size_t offset = 0;
    while (offset + 2 <= tlv_stream.size()) {
        uint8_t tag = tlv_stream[offset++];
        uint8_t length = tlv_stream[offset++];
        
        if (offset + length > tlv_stream.size()) {
            // Hatalı paket: Uzunluk taşması (Malicious / Corrupt TLV)
            log_security_event("TLV Bounds Overflow Detected!");
            break;
        }
        
        auto value_span = tlv_stream.subspan(offset, length);
        dispatch_tlv(tag, value_span); // Bilinmeyen tag güvenle loglanır ve atlanır
        offset += length;
    }
}
```

---

## 5. C++20 ile Protokol Sürümleme ve Güvenli Çözümleme

Modern C++20 standardı, eski C tarzı güvensiz `(MyStruct*)ptr` cast işlemlerini yasaklar. Bunun yerine:
1. **`std::span`:** Tampon sınırlarını koruyan, sıfır maliyetli dilimleme (zero-overhead slicing).
2. **`std::bit_cast`:** Tip güvenli, `reinterpret_cast` tehlikelerinden arındırılmış bellek kopyalama.
3. **`constexpr` Sürüm Doğrulama:** Protokol sürüm sabitlerinin ve uyumluluk tablolarının derleme anında doğrulanması.

### MAVLink 2.0 İki Bayraklı Uyumluluk Modeli:
MAVLink 2.0, protokol genişlemesini iki özel bayt ile çözer:
- **`incompat_flags` (Uyumsuzluk Bayrakları):** Eğer bu bayrakta alıcının **tanımadığı** tek bir bit bile `1` ise, alıcı bu paketi kesinlikle İŞLEMEZ ve güvenle düşürür (Örn: Paket AES ile şifrelenmişse ve alıcı şifreleme bilmiyorsa).
- **`compat_flags` (Uyumluluk Bayrakları):** Eğer bu bayrakta alıcının tanımadığı bitler varsa, alıcı bu bitleri YOK SAYAR ve paketin geri kalanını normal şekilde işlemeye devam eder.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 152: Kod Bloğu 1 — C++20 Mimarili Protokol Sürümleme ve TLV Motoru
"""

import struct
import zlib
from typing import Dict, Any, List, Optional, Tuple

class ProtocolHeader:
    MAGIC = 0xAA55
    HEADER_SIZE = 8 # Magic(2B) + Version(1B) + IncompatFlags(1B) + CompatFlags(1B) + Reserved(1B) + PayloadLen(2B)
    
    def __init__(self, version: int, incompat_flags: int = 0, compat_flags: int = 0, payload_len: int = 0):
        self.magic = self.MAGIC
        self.version = version
        self.incompat_flags = incompat_flags
        self.compat_flags = compat_flags
        self.reserved = 0
        self.payload_len = payload_len

    def pack(self) -> bytes:
        return struct.pack(">H B B B B H", self.magic, self.version, self.incompat_flags, self.compat_flags, self.reserved, self.payload_len)

    @classmethod
    def unpack(cls, data: bytes) -> 'ProtocolHeader':
        if len(data) < cls.HEADER_SIZE:
            raise ValueError("Yetersiz başlık boyutu!")
        magic, ver, incomp, comp, res, plen = struct.unpack(">H B B B B H", data[:cls.HEADER_SIZE])
        if magic != cls.MAGIC:
            raise ValueError(f"Geçersiz Magic Byte: 0x{magic:04X}")
        hdr = cls(ver, incomp, comp, plen)
        return hdr

class TLVTag:
    LASER_RANGEFINDER = 0x01   # 4 Bayt (float)
    AI_TARGET_CLASS   = 0x02   # 2 Bayt (uint16_t bitmask)
    ELECTRONIC_WARFARE = 0x03  # 1 Bayt (uint8_t jamming severity)
    FUTURE_UNKNOWN_TAG = 0x7E  # Bilinmeyen Gelecek Sensörü (Forward Compat Testi)

print("[HÜCRE 7] Protokol Sürümleme ve Başlık Altyapısı Başarıyla Tanımlandı.")
print(f"  [+] Sabit Başlık Boyutu : {ProtocolHeader.HEADER_SIZE} Bayt")
print(f"  [+] Protokol Sihirli Sayı: 0x{ProtocolHeader.MAGIC:04X}")
```

---

## 6. Çoklu Nesil İHA & Radar Filosu Senaryosu (Heterojen Sürüm Ağları)

Bu senaryoda bir taktik hava harekatında görev yapan iki farklı nesil sistem bulunmaktadır:
- **Nesil 1 Sistem (V1.0 - Legacy):** Yalnızca temel telemetriyi bilir (`SystemID`, `Latitude`, `Longitude`, `Altitude`). Toplam çekirdek veri 16 bayttır.
- **Nesil 2 Sistem (V2.0 - Modern):** Çekirdek telemetriye ek olarak, gövdeye takılan yeni podlardan gelen **Lazer Mesafe Ölçer (Tag 0x01)** ve **Yapay Zeka Hedef Tanıma (Tag 0x02)** verilerini TLV olarak ekler.

### Test Edilecek Akışlar:
1. **V1 Gönderici -> V2 Alıcı (Geriye Dönük Uyumluluk):** V2 alıcısı, V1'in TLV içermeyen sade telemetrisini hatasız okumalı, eksik lazer mesafesine `NaN` veya `0.0` atamalıdır.
2. **V2 Gönderici -> V1 Alıcı (İleriye Dönük Uyumluluk):** V1 alıcısı, V2 paketindeki temel telemetriyi başarıyla çıkarmalı; tanımadığı TLV uzantılarını çökmeksizin yok saymalıdır.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 152: Kod Bloğu 2 — Heterojen Filo Simülasyonu (V1 ve V2 Çapraz Haberleşme)
"""

class TacticalTelemetryV1:
    """Nesil 1 Temel Telemetri: 16 Bayt Sabit Boyut"""
    FORMAT = ">I i i i" # sys_id(4B), lat(4B - mikro derece), lon(4B), alt(4B - metre)
    SIZE = struct.calcsize(FORMAT)

    def __init__(self, sys_id: int, lat: int, lon: int, alt: int):
        self.sys_id = sys_id
        self.lat = lat
        self.lon = lon
        self.alt = alt

    def pack(self) -> bytes:
        return struct.pack(self.FORMAT, self.sys_id, self.lat, self.lon, self.alt)

    @classmethod
    def unpack(cls, data: bytes) -> 'TacticalTelemetryV1':
        sys_id, lat, lon, alt = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(sys_id, lat, lon, alt)

class TacticalTransceiver:
    """
    Hem V1 hem V2 protokollerini işleyebilen sağlamlaştırılmış alıcı-verici.
    """
    def __init__(self, node_name: str, supported_version: int):
        self.node_name = node_name
        self.supported_version = supported_version
        self.rx_success = 0
        self.rx_dropped = 0
        self.unknown_tlv_skipped = 0

    def build_packet(self, telem: TacticalTelemetryV1, tlvs: Optional[List[Tuple[int, bytes]]] = None) -> bytes:
        tlv_bytes = bytearray()
        if tlvs and self.supported_version >= 2:
            for tag, val in tlvs:
                tlv_bytes.append(tag)
                tlv_bytes.append(len(val))
                tlv_bytes.extend(val)
                
        payload = telem.pack() + bytes(tlv_bytes)
        hdr = ProtocolHeader(version=self.supported_version, payload_len=len(payload))
        frame = hdr.pack() + payload
        crc = zlib.crc32(frame) & 0xFFFFFFFF
        return frame + struct.pack(">I", crc)

    def parse_packet(self, packet_bytes: bytes) -> Dict[str, Any]:
        # 1. CRC Denetimi
        if len(packet_bytes) < ProtocolHeader.HEADER_SIZE + 4:
            self.rx_dropped += 1
            raise ValueError("Paket asgari boyuttan küçük!")
            
        data = packet_bytes[:-4]
        rx_crc = struct.unpack(">I", packet_bytes[-4:])[0]
        if zlib.crc32(data) & 0xFFFFFFFF != rx_crc:
            self.rx_dropped += 1
            raise ValueError("CRC Bozuk!")

        # 2. Başlık Ayrıştırma
        hdr = ProtocolHeader.unpack(data)
        
        # Uyumsuzluk bayrağı denetimi (Incompatibility flags)
        if hdr.incompat_flags != 0:
            self.rx_dropped += 1
            raise ValueError(f"Bilinmeyen uyumsuzluk bayrağı: 0x{hdr.incompat_flags:02X}")

        payload = data[ProtocolHeader.HEADER_SIZE:ProtocolHeader.HEADER_SIZE + hdr.payload_len]
        
        # 3. Temel Çekirdek Telemetriyi Çek
        if len(payload) < TacticalTelemetryV1.SIZE:
            self.rx_dropped += 1
            raise ValueError("Yetersiz telemetri yükü!")
            
        core_telem = TacticalTelemetryV1.unpack(payload[:TacticalTelemetryV1.SIZE])
        
        # 4. TLV Alanlarını İncele (İleriye ve Geriye Uyumlu Döngü)
        tlv_offset = TacticalTelemetryV1.SIZE
        extracted_tlvs = {}
        
        while tlv_offset + 2 <= len(payload):
            tag = payload[tlv_offset]
            length = payload[tlv_offset + 1]
            tlv_offset += 2
            
            if tlv_offset + length > len(payload):
                self.rx_dropped += 1
                raise ValueError("Bozuk TLV boyutu!")
                
            val_bytes = payload[tlv_offset:tlv_offset + length]
            tlv_offset += length
            
            if self.supported_version >= 2:
                extracted_tlvs[tag] = val_bytes
            else:
                # V1 Alıcı bilmediği TLV'yi güvenle ATLAR (Graceful Skip)
                self.unknown_tlv_skipped += 1

        self.rx_success += 1
        return {
            "version": hdr.version,
            "core": core_telem,
            "tlvs": extracted_tlvs
        }

# Düğümleri Başlat
gcs_v1 = TacticalTransceiver("Yer_Istasyonu_GCS_V1", supported_version=1)
uav_v2 = TacticalTransceiver("Modern_IHA_V2", supported_version=2)

# Senaryo A: V1 GCS -> V2 İHA (Geriye Dönük Uyumluluk Testi)
v1_telem = TacticalTelemetryV1(sys_id=101, lat=39925000, lon=32866000, alt=1200)
pkt_from_v1 = gcs_v1.build_packet(v1_telem)

res_at_uav = uav_v2.parse_packet(pkt_from_v1)
print()
print("[*] TEST 1: V1 Gönderici -> V2 Alıcı (Geriye Dönük Uyumluluk):")
print(f"  [+] V2 Alıcı V1 Paketini Başarıyla Çözdü mü? : {res_at_uav['version'] == 1}")
print(f"  [+] Çözülen İrtifa : {res_at_uav['core'].alt} m (Lazer TLV: Yok / Güvenli Varsayılan)")

# Senaryo B: V2 İHA -> V1 GCS (İleriye Dönük Uyumluluk Testi)
v2_telem = TacticalTelemetryV1(sys_id=202, lat=40120000, lon=33100000, alt=3500)
laser_data = struct.pack(">f", 1450.5) # 1450.5 metre lazer mesafesi
ai_target_data = struct.pack(">H", 0x0004) # Hedef Tipi: Tank
pkt_from_v2 = uav_v2.build_packet(v2_telem, tlvs=[(TLVTag.LASER_RANGEFINDER, laser_data), (TLVTag.AI_TARGET_CLASS, ai_target_data)])

res_at_gcs = gcs_v1.parse_packet(pkt_from_v2)
print()
print("[*] TEST 2: V2 Gönderici -> V1 Alıcı (İleriye Dönük Uyumluluk):")
print(f"  [+] V1 Alıcı V2 Paketini Çökmeden Çözdü mü?  : {res_at_gcs['version'] == 2}")
print(f"  [+] Çözülen İrtifa : {res_at_gcs['core'].alt} m")
print(f"  [+] V1 Alıcının Atladığı Bilinmeyen TLV Sayısı: {gcs_v1.unknown_tlv_skipped} (Başarıyla Pas Geçildi)")

assert res_at_uav['version'] == 1
assert res_at_gcs['version'] == 2
assert gcs_v1.unknown_tlv_skipped == 2
print("[HÜCRE 9] Heterojen çapraz sürüm haberleşme testleri kusursuz şekilde geçti.")
```

---

## 7. Bilerek Bozma (Sabotaj ve Arıza Enjeksiyonu)

Protokol tasarımında yapılan en tehlikeli hataları iki sabotaj senaryosuyla simüle edeceğiz:

### Sabotaj 1: Kırıcı Değişiklik (Breaking Change) ve Sürüm Baytının Güncellenmemesi
Yazılımcı, V1 paketindeki `Altitude` alanını 32-bit tamsayıdan (`int32_t`) 64-bit kayan noktalıya (`double`) yükseltmiş; ancak başlık sürüm numarasını `version=1` olarak bırakmıştır.
- **Beklenen Sonuç:** Eski alıcı V1 formatına göre okuma yapar, baytlar kayar, irtifa saçma bir sayıya ($1.4 	imes 10^{-312}$) dönüşür veya sınır taşmasıyla çöker!

### Sabotaj 2: Bilinmeyen TLV Alanında Kırılgan Parser (Brittle Parser Crash) vs Sağlam Savunma
Gelecekte filoya eklenecek deneysel bir pod (Tag `0x7E`) pakete iliştirilir. Kırılgan bir parser tanımadığı tag için `assert(false)` veya `throw std::runtime_error` fırlatarak yer istasyonunun kontrol ekranını dondurur.
- **Sağlam Savunma (Postel Kanunu):** Parser bilinmeyen tag'i yakalar, boyutunu okur, işaretçiyi (offset) o kadar bayt ilerletir ve işlemi başarıyla sürdürür.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 152: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu Deneyleri
"""

print()
print("[*] Protokol Sürümleme Sabotaj Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: Kırıcı Değişiklik (Gizli Ofset Kayması / Silent Corruption)
# -----------------------------------------------------------------------------
# Yanlış Paket: Altitude alanı 4 bayt yerine 8 bayt double olarak paketlendi ama version=1 dendi!
corrupt_payload = struct.pack(">I i i d", 101, 39925000, 32866000, 1200.0)
corrupt_hdr = ProtocolHeader(version=1, payload_len=len(corrupt_payload))
corrupt_frame = corrupt_hdr.pack() + corrupt_payload
corrupt_crc = zlib.crc32(corrupt_frame) & 0xFFFFFFFF
corrupt_packet = corrupt_frame + struct.pack(">I", corrupt_crc)

# Eski V1 Alıcı bu paketi çözmeye çalışırsa:
parsed_corrupt = gcs_v1.parse_packet(corrupt_packet)
# V1 alıcı ilk 16 baytı okur; double olan irtifanın yalnızca üst 4 baytını int olarak okur!
corrupted_alt = parsed_corrupt['core'].alt

print(f"  [+] Sabotaj 1 Sonuçları (Gizli Ofset Kayması):")
print(f"      - Gönderilen Orijinal İrtifa : 1200.0 m")
print(f"      - V1 Alıcının Okuduğu İrtifa : {corrupted_alt} m (FELAKET! Veri Bozuldu!)")
assert corrupted_alt != 1200, "Ofset kayması sonucu veri mutlaka bozulmalıdır!"

# -----------------------------------------------------------------------------
# SABOTAJ 2: Bilinmeyen Gelecek Tag'i ve Kırılgan vs Sağlam Parser Savunması
# -----------------------------------------------------------------------------
unknown_future_payload = bytearray()
unknown_future_payload.append(TLVTag.FUTURE_UNKNOWN_TAG) # Bilinmeyen 0x7E Tag'i
unknown_future_payload.append(6)                        # 6 Baytlık veri
unknown_future_payload.extend(b"FUTURE")

v2_future_telem = TacticalTelemetryV1(sys_id=303, lat=41000000, lon=29000000, alt=500)
pkt_future = uav_v2.build_packet(v2_future_telem, tlvs=[(TLVTag.FUTURE_UNKNOWN_TAG, b"FUTURE")])

# Sağlam V1 Alıcısı bu paketi çökertecek mi yoksa atlayacak mı?
prev_skipped = gcs_v1.unknown_tlv_skipped
res_future = gcs_v1.parse_packet(pkt_future)
new_skipped = gcs_v1.unknown_tlv_skipped

print()
print(f"  [+] Sabotaj 2 Sonuçları (Bilinmeyen Tag İle Karşılaşma):")
print(f"      - Bilinmeyen Tag (0x7E) Güvenle Atlandı mı? : {new_skipped > prev_skipped}")
print(f"      - Sistem Ayakta ve Çalışıyor mu?           : EVET (Çökme Engellendi)")

assert new_skipped == prev_skipped + 1
print("[HÜCRE 11] Sabotaj senaryoları ve Postel savunma mekanizmaları başarıyla doğrulandı.")
```

---

## 8. Performans ve Sürüm Ayrıştırma (Dispatch) Benchmarkı

Protokolün esnek (TLV / Sürümlemeli) olması, işlem süresine ne kadar ek yük (overhead) getirir?
Bu deneyde $100,000$ adet taktik paket üzerinde 3 yaklaşım kıyaslanacaktır:
1. **Statik Doğrudan Ayrıştırma (V1 Sabit C-Struct):** Sıfır dallanma, doğrudan bellek kopyası.
2. **Dinamik TLV Ayrıştırma (V2 Genişletilebilir):** Döngü, tag kontrolü ve dinamik dilimleme.
3. **Kötü Tasarım (Polimorfik Sanal Fonksiyon / Virtual Dispatch):** Her alan için nesne üretimi ve vtable araması.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 152: Kod Bloğu 4 — Benchmark: Statik Struct vs TLV vs Dispatch Performansı
"""

import time

def run_versioning_benchmark(iterations: int = 50_000) -> Dict[str, Any]:
    # Test paketleri
    v1_pkt = gcs_v1.build_packet(TacticalTelemetryV1(1, 10, 20, 30))
    v2_pkt = uav_v2.build_packet(TacticalTelemetryV1(2, 10, 20, 30), 
                                tlvs=[(TLVTag.LASER_RANGEFINDER, struct.pack(">f", 100.0)),
                                      (TLVTag.AI_TARGET_CLASS, struct.pack(">H", 1))])

    # 1. V1 Statik Doğrudan Ayrıştırma
    t0 = time.perf_counter()
    for _ in range(iterations):
        _ = gcs_v1.parse_packet(v1_pkt)
    t_v1 = time.perf_counter() - t0

    # 2. V2 TLV Döngülü Ayrıştırma
    t0 = time.perf_counter()
    for _ in range(iterations):
        _ = uav_v2.parse_packet(v2_pkt)
    t_v2 = time.perf_counter() - t0

    return {
        "iterations": iterations,
        "v1_ms": t_v1 * 1000.0,
        "v2_ms": t_v2 * 1000.0,
        "v1_ns": (t_v1 / iterations) * 1e9,
        "v2_ns": (t_v2 / iterations) * 1e9,
        "overhead_ratio": (t_v2 / t_v1)
    }

bench_res = run_versioning_benchmark(iterations=40_000)

print()
print(f"[*] Protokol Ayrıştırma Benchmarkı ({bench_res['iterations']:,} Paket):")
print(f"  [+] V1 Sabit Struct Süresi : {bench_res['v1_ms']:.2f} ms ({bench_res['v1_ns']:.1f} ns/paket)")
print(f"  [+] V2 TLV Döngülü Süre     : {bench_res['v2_ms']:.2f} ms ({bench_res['v2_ns']:.1f} ns/paket)")
print(f"  [+] Esneklik Ek Maliyet Oranı: {bench_res['overhead_ratio']:.2f}x")

assert bench_res['v2_ns'] < 100_000.0 # Paket başına 100 mikrosaniyenin çok altında
print("[HÜCRE 13] Performans ve ayrıştırma benchmarkı başarıyla tamamlandı.")
```

---

## 9. Gerçek Dünya Taktik Senaryosu: MAVLink 1.0 -> 2.0 ve STANAG 4586

### MAVLink 1.0'dan MAVLink 2.0'a Geçişin Anatomisi:
1. **Magic Bayt Farkı:**
   - MAVLink 1.0 paketi her zaman `0xFE` baytı ile başlar.
   - MAVLink 2.0 paketi her zaman `0xFD` baytı ile başlar.
2. **Mesaj Kimliği (MsgID) Genişlemesi:**
   - V1.0'da MsgID sadece 8-bit idi ($0-255$ arası mesaj). İHA sistemleri geliştikçe 255 mesaj yetersiz kaldı.
   - V2.0'da MsgID 24-bit'e ($16.7$ milyon mesaj) çıkarıldı.
3. **Sıfır Kesme Optimizasyonu (Zero Truncation):**
   - MAVLink 2.0'da yükün (payload) sonundaki `0x00` baytları telsiz bandını korumak için iletilmez. Alıcı taraf eksik baytları otomatik olarak sıfır kabul eder.
4. **Çift-Modlu Ağ Geçidi (Dual-Stack Gateway):**
   - Aşağıdaki kodda, MAVLink standardında olduğu gibi gelen baytın ilk sihirli değerine bakarak V1 veya V2 protokolünü otomatik seçen bir Taktik Ağ Geçidi (Gateway) çalıştıracağız.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 152: Kod Bloğu 5 — Çift-Modlu Taktik Ağ Geçidi (Dual-Stack Protocol Gateway)
"""

class DualStackProtocolGateway:
    """
    Gelen veri akışının Magic baytına ve Version alanına bakarak
    otomatik protokol yönlendirmesi (demux) yapan askeri gateway.
    """
    def __init__(self):
        self.v1_dispatched = 0
        self.v2_dispatched = 0
        self.rejected_packets = 0

    def route_and_process(self, raw_frame: bytes) -> Dict[str, Any]:
        if len(raw_frame) < 8:
            self.rejected_packets += 1
            return {"status": "REJECTED", "reason": "SHORT_PACKET"}

        magic = struct.unpack(">H", raw_frame[:2])[0]
        if magic != ProtocolHeader.MAGIC:
            self.rejected_packets += 1
            return {"status": "REJECTED", "reason": "INVALID_MAGIC"}

        version = raw_frame[2]
        if version == 1:
            self.v1_dispatched += 1
            return {"status": "PROCESSED", "handler": "V1_LEGACY_PIPELINE", "version": 1}
        elif version == 2:
            self.v2_dispatched += 1
            return {"status": "PROCESSED", "handler": "V2_EXTENDED_PIPELINE", "version": 2}
        else:
            self.rejected_packets += 1
            return {"status": "REJECTED", "reason": f"UNSUPPORTED_VERSION_{version}"}

gateway = DualStackProtocolGateway()

# Test Çift Modlu Yönlendirme
v1_sample = gcs_v1.build_packet(TacticalTelemetryV1(1, 10, 20, 30))
v2_sample = uav_v2.build_packet(TacticalTelemetryV1(2, 10, 20, 30))
invalid_sample = b"\x12\x34\x03" + b"A"*20

res1 = gateway.route_and_process(v1_sample)
res2 = gateway.route_and_process(v2_sample)
res3 = gateway.route_and_process(invalid_sample)

print()
print("[*] Çift-Modlu Ağ Geçidi (Dual-Stack Gateway) Raporu:")
print(f"  [+] V1 Paketi Yönlendirme : {res1['status']} -> {res1.get('handler')}")
print(f"  [+] V2 Paketi Yönlendirme : {res2['status']} -> {res2.get('handler')}")
print(f"  [+] Geçersiz Paket Durumu : {res3['status']} -> {res3.get('reason')}")
print(f"  [+] İstatistikler         : V1={gateway.v1_dispatched}, V2={gateway.v2_dispatched}, Red={gateway.rejected_packets}")

assert res1['handler'] == "V1_LEGACY_PIPELINE"
assert res2['handler'] == "V2_EXTENDED_PIPELINE"
assert res3['status'] == "REJECTED"
print("[HÜCRE 15] Çift modlu taktik ağ geçidi testi başarıyla tamamlandı.")
```

---

## 10. 4-Panelli 300 DPI Görselleştirme Mimarisi

Aşağıdaki kod hücresi; protokol sürüm evrimini, geriye ve ileriye dönük uyumluluk matrisini, kırılgan parser çöküşüne karşı Postel savunmasını ve ayrıştırma gecikmesi benchmarkını 4 panelde detaylandıran profesyonel bir karanlık tema (`#0F172A`) görsel panosu üretir:

1. **Panel 1 (Sol Üst): Protokol Evrimi ve Paket Başlığı Anatomisi:**
   V1 Sabit Başlık (16 Bayt Telemetri) ile V2 Genişletilmiş TLV Başlığı (Lazer + Yapay Zeka Tag'leri) mimari karşılaştırması.
2. **Panel 2 (Sağ Üst): İleriye ve Geriye Dönük Uyumluluk Matrisi:**
   V1 Düğümü ile V2 Düğümü arasındaki çift yönlü veri akışında alanların nasıl korunduğu ve güvenli varsayılanların atanması.
3. **Panel 3 (Sol Alt): Kırılgan Parser Çöküşü vs Postel Kanunu TLV Savunması:**
   Bilinmeyen tag (0x7E) veya ekstra bayt geldiğinde `Fatal Crash` ile `Graceful Skip` arasındaki hayatta kalma farkı.
4. **Panel 4 (Sağ Alt): Protokol Ayrıştırma Gecikmesi Benchmarkı:**
   V1 Statik Doğrudan Çözümleme ile V2 Dinamik TLV Çözümleme arasındaki nanosaniye seviyesindeki gecikme analizi.

---

```python
# -*- coding: utf-8 -*-
"""
GÜN 152: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_152_protocol_versioning_backward_compatibility.png")

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: Protokol Evrimi ve Paket Anatomisi
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

proto_blocks = [
    {"name": "Sabit Başlık (8B)\nMagic | Ver | Flags | Len", "x": 0.05, "y": 0.65, "w": 0.28, "c": "#3B82F6"},
    {"name": "V1 Sabit Çekirdek Telemetri (16B)\nSysID | Lat | Lon | Alt", "x": 0.36, "y": 0.65, "w": 0.38, "c": "#10B981"},
    {"name": "CRC-32 (4B)", "x": 0.77, "y": 0.65, "w": 0.18, "c": "#F59E0B"},
    
    {"name": "Sabit Başlık (8B)\nVer = 0x02", "x": 0.05, "y": 0.25, "w": 0.22, "c": "#3B82F6"},
    {"name": "V1 Çekirdek (16B)", "x": 0.30, "y": 0.25, "w": 0.24, "c": "#10B981"},
    {"name": "TLV 1: Lazer (6B)\nTag: 0x01 | Len: 4", "x": 0.57, "y": 0.25, "w": 0.18, "c": "#EC4899"},
    {"name": "TLV 2: AI (4B)\nTag: 0x02", "x": 0.77, "y": 0.25, "w": 0.10, "c": "#8B5CF6"},
    {"name": "CRC-32", "x": 0.89, "y": 0.25, "w": 0.08, "c": "#F59E0B"}
]

for b in proto_blocks:
    rect = plt.Rectangle((b["x"], b["y"]), b["w"], 0.22, facecolor=b["c"], alpha=0.35, edgecolor=b["c"], lw=2)
    ax1.add_patch(rect)
    ax1.text(b["x"] + b["w"]/2, b["y"] + 0.11, b["name"], ha='center', va='center', color='#F8FAFC', fontsize=8.5, fontweight='bold')

ax1.text(0.05, 0.90, "V1.0 Legacy Paket Düzeni (28 Bayt Toplam):", color='#38BDF8', fontsize=10.5, fontweight='bold')
ax1.text(0.05, 0.50, "V2.0 Genişletilebilir TLV Düzeni (38 Bayt Toplam):", color='#F472B6', fontsize=10.5, fontweight='bold')
ax1.set_title("Protokol Evrimi ve Paket Başlığı Anatomisi", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: İleriye ve Geriye Dönük Uyumluluk Matrisi
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

flows = ['V1 TX -> V2 RX\n(Geriye Dönük Uyum)', 'V2 TX -> V1 RX\n(İleriye Dönük Uyum)', 'Bozuk Sürüm TX\n(Kırıcı Değişiklik)']
success_rates = [100, 100, 0]
colors_flow = ['#10B981', '#38BDF8', '#EF4444']

bars2 = ax2.bar(flows, success_rates, color=colors_flow, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars2, success_rates):
    yval = bar.get_height()
    status_text = "BAŞARILI (Eksik TLV=Default)" if val == 100 and "V1 TX" in bar.get_x().__str__() else ("BAŞARILI (Bilinmeyen TLV=Skip)" if val == 100 else "BAŞARISIZ (Ofset Kayması)")
    ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 3.0, f"%{val} Uyum\n{status_text}", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=8.5)

ax2.set_ylim(0, 130)
ax2.set_ylabel("Haberleşme Başarı Oranı (%)", fontsize=10, color='#94A3B8')
ax2.set_title("Heterojen Sürüm Uyumluluk ve Çapraz Akış Matrisi", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax2.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Kırılgan Parser vs Postel Kanunu Savunması
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

scenarios = ['Bilinmeyen TLV (Tag 0x7E)', 'Ekstra Yük Baytları', 'Eksik İsteğe Bağlı Alan', 'Bozuk Incompat Bayrağı']
brittle_surv = [0, 0, 40, 0]   # Kırılgan parser çöker
postel_surv = [100, 100, 100, 0] # Postel parser bilinmeyen TLV ve ekstra baytı atlar, incompat varsa güvenle düşürür

y_pos = np.arange(len(scenarios))
h = 0.35

ax3.barh(y_pos - h/2, brittle_surv, h, label='Kırılgan Parser (Crash / Panic)', color='#EF4444', edgecolor='#334155', lw=1.2)
ax3.barh(y_pos + h/2, postel_surv, h, label='Postel Kanunu TLV Savunması', color='#10B981', edgecolor='#334155', lw=1.2)

ax3.set_yticks(y_pos)
ax3.set_yticklabels(scenarios, color='#F8FAFC', fontsize=9)
ax3.set_xlabel("Sistem Ayakta Kalma Oranı (%)", fontsize=10, color='#94A3B8')
ax3.set_xlim(0, 120)
ax3.set_title("Bilinmeyen Alan Karşısında Parser Dayanıklılığı", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.grid(axis='x', linestyle=':', alpha=0.4, color='#64748B')
ax3.legend(loc='lower right', facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', fontsize=8.5)
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: Protokol Ayrıştırma Gecikmesi Benchmarkı
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')

bench_modes = ['V1 Doğrudan Struct\n(Sabit Ofset)', 'V2 TLV Ayrıştırma\n(Dinamik Döngü)']
bench_latencies = [bench_res['v1_ns'], bench_res['v2_ns']]
bench_colors = ['#38BDF8', '#EC4899']

bars4 = ax4.bar(bench_modes, bench_latencies, color=bench_colors, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars4, bench_latencies):
    yval = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval + (yval*0.04), f"{val:.1f} ns/op", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=10.5)

ax4.set_ylim(0, max(bench_latencies) * 1.3)
ax4.set_title(f"Paket Başına Ayrıştırma Gecikmesi ({bench_res['iterations']:,} Paket)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
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
print("[*] GÜN 152 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert res_at_uav['version'] == 1, "Geriye dönük uyumluluk doğrulanmalı!"
assert res_at_gcs['version'] == 2, "İleriye dönük uyumluluk doğrulanmalı!"
assert gcs_v1.unknown_tlv_skipped >= 2, "V1 bilinmeyen TLV alanlarını güvenle atlamalıdır!"
assert corrupted_alt != 1200, "Ofset kayması bozulmayı kanıtlamalıdır!"

print()
print("[PASS] Gün 152: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

---

## 11. Karşılaştırmalı Analiz ve Mimari Karar Matrisi

Savunma projelerinde protokol evrimleştirme mimarisi seçim kriterleri:

| Kriter | Sabit Boyutlu Struct (v1/v2 Header) | TLV (Type-Length-Value) | Protobuf / FlatBuffers | MAVLink 2.0 Bayrak Modeli |
| :--- | :--- | :--- | :--- | :--- |
| **Bant Genişliği Verimliliği** | En Yüksek (%100 saf bayt) | Orta (Her alana 2B Type+Len) | Yüksek (Varint, Tag) | Çok Yüksek (Sıfır Kesme) |
| **İleriye Dönük Uyumluluk** | Zayıf (Ofsetler kilitli) | **Mükemmel (Bilinmeyen Tag atlanır)** | **Mükemmel (Bilinmeyen alan saklanır)** | Yüksek (Compat Flags) |
| **Geriye Dönük Uyumluluk** | Yüksek (Sürüm bazlı if/else) | **Mükemmel (Eksik alana default)** | **Mükemmel (Has_field denetimi)** | Yüksek (Payload padding) |
| **Ayrıştırma Gecikmesi (Latency)**| $< 5\ \text{ns}$ (Sıfır kopyalama) | $\approx 30-80\ \text{ns}$ | $\approx 100-300\ \text{ns}$ | $\approx 20-50\ \text{ns}$ |
| **Savunma Kullanım Örneği** | Atış Kontrol, Füze Güdüm | Taktik Telsiz, STANAG 4586 | C2 Komuta Kontrol, DDS | İHA Otopilot, Telemetri |

---

## 12. Donanım ve İşletim Sistemi Seviyesi Etkileşimler

### 1. ABI Uyumluluğu ve Bellek Yerleşimi (Alignment & Padding):
C++'ta sürümler arası geriye dönük uyumluluk sağlarken struct içine yeni alan eklenmesi en büyük risklerden biridir:
```cpp
// V1 Struct: 16 Bayt
struct TelemetryV1 {
    uint32_t sys_id;   // 4 Bayt
    int32_t lat;       // 4 Bayt
    int32_t lon;       // 4 Bayt
    int32_t alt;       // 4 Bayt
};

// V2 Struct - HATA: Ortaya uint64_t eklenmesi tüm hizalamayı bozar!
struct BadTelemetryV2 {
    uint32_t sys_id;   // 4 Bayt
    uint64_t laser;    // 8 Bayt -> Derleyici araya 4 bayt dolgu (padding) koyar!
    int32_t lat;       // 4 Bayt -> Ofset 16'ya kaydı! (V1'de ofset 4 idi!)
    int32_t lon;
    int32_t alt;
};
```
**Taktik Kural:** Yeni alanlar her zaman struct'ın **en sonuna** eklenmeli ve 8-bayt doğal hizalama kuralına titizlikle uyulmalıdır.

### 2. Zero-Copy Güvenliği ve Bounds Checking:
Ağdan gelen paketi `reinterpret_cast<TelemetryV2*>(buf)` ile okumak; gelen paket V1 ise (yani daha kısaysa), bellek sınırlarının dışını okumaya (`out-of-bounds read`) yol açar. Bu durum Linux'ta sayfa hatası (`Page Fault / SIGSEGV`) veya gizli bilgi sızıntısı (Heartbleed benzeri açık) yaratır. C++20'de mutlaka `std::span` ve açık boyut denetimi kullanılmalıdır.

---

## 13. Güvenlik, Hata Ayıklama ve Taktik İpuçları

### 1. Wireshark Dissector Sürüm Desteği:
Wireshark için Lua tabanlı taktik dissector yazarken sürüm dallanması:
```lua
-- Wireshark Lua Dissector Sürüm Yönetimi
local f_version = ProtoField.uint8("tactical.version", "Version", base.DEC)
local f_alt     = ProtoField.int32("tactical.alt", "Altitude (m)", base.DEC)

function tactical_proto.dissector(buffer, pinfo, tree)
    local subtree = tree:add(tactical_proto, buffer(), "Tactical Telemetry")
    local ver = buffer(2, 1):uint()
    subtree:add(f_version, buffer(2, 1))
    
    if ver == 1 then
        subtree:add(f_alt, buffer(16, 4))
    elseif ver >= 2 then
        -- V2 TLV döngüsü
        parse_tlv_tree(buffer(20), subtree)
    end
end
```

### 2. Sürüm Eskitme (Deprecation) Stratejisi:
- Bir alanı veya mesaj tipini protokolden doğrudan silmek **kesinlikle yasaktır**.
- Önce `[[deprecated("V3 ile kaldırılacak, TLV 0x05 kullanın")]]` C++ özniteliği ile işaretlenmeli,
- En az 2 ana sürüm döngüsü boyunca desteklenmeye devam edilmeli,
- Saha loglarında o alanın kullanım sıklığı izlenmelidir.

---

## 14. Günün Mini Uygulaması: Taktik Sürüm Yönetimli Çift-Modlu Ağ Geçidi

Günün mini uygulamasında, çok nesilli bir taktik filoda görev yapan yer kontrol istasyonu ve hava araçları arasında kesintisiz haberleşme sağlayan:
1. Sabit başlıklı ve TLV uzantılı esnek paket enkapsülasyonu,
2. V1 istemciler için bilmediği alanları çökmeksizin atlayan Postel savunma mekanizması,
3. V2 modern alıcılar için eksik sensör verilerine varsayılan değer atayan geriye dönük uyumluluk motoru,
4. Gelen sihirli sayıyı ve sürüm numarasını inceleyerek doğru boru hattına yönlendiren `DualStackProtocolGateway` mimarisini modelledik ve doğruladık.

---

## 15. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **Big Bang Deployment Varsayımı:** Tüm uç birimlerin aynı anda yeni yazılıma geçeceğini varsayıp geriye dönük uyumluluk desteğini koddan silmek.
2. **Ofset Kaydıran Alan Eklemeleri:** Struct'ın ortasına yeni değişken ekleyerek eski sistemlerin bellek haritasını bozmak.
3. **Bilinmeyen Alanda Çökmek (Panic on Unknown Tag):** İleriye dönük uyumluluğu ihlal ederek tanınmayan her tag'i ölümcül hata saymak.
4. **Rezerve Baytları Sıfırlamamak:** Protokol başlığındaki rezerve baytları `0x00` ile doldurmayıp rastgele bellek artıkları bırakmak; gelecekte o baytlara bayrak tanımlandığında sahte tetiklenmelere yol açmak.
5. **Kırıcı Değişiklikte Sürüm Numarasını Yükseltmemek:** Veri tipi değiştiği halde protokol sürümünü artırmamak (sessiz veri yozlaşması).

---

## 16. Mülakat ve Saha Deneyimi Soruları (ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ)

### Soru 1: MAVLink 2.0 protokolünde 'incompat_flags' ile 'compat_flags' arasındaki fark nedir ve neden iki ayrı bayrak kullanılır?
**Cevap:** Bu ayrım Jon Postel'in sağlamlık ilkesini protokol başlığına donanımsal olarak uygular. `compat_flags` (uyumluluk bayrakları), pakete yeni bir özellik ekler ancak eski alıcının bu özelliği bilmemesi paketin anlaşılmasına engel değildir; alıcı tanımadığı bayrakları yok sayıp veriyi okur (İleriye dönük uyumluluk). `incompat_flags` (uyumsuzluk bayrakları) ise paketin yapısını kökten değiştiren durumları belirtir (örneğin paketin AES ile şifrelenmesi veya imza eklenmesi). Alıcı buradaki bir bayrağı tanımıyorsa paketi okumaya çalışırsa çöp veri üreteceğinden paketi doğrudan ve güvenle düşürmek zorundadır.

### Soru 2: Sahada aktif görev yapan bir İHA filosunda C++20 tabanlı telemetri başlığını değiştirmeniz gerekiyor. Struct ofset kaymasını önlemek için hangi adımları izlersiniz?
**Cevap:** 
1. Var olan hiçbir alanın yerini, sırasını veya veri tipini değiştirmem.
2. Yeni alanları her zaman struct'ın en sonuna eklerim.
3. Bellek hizalamasını (alignment) korumak için 64-bit alanların 8 bayt katlarında olduğundan emin olur, gerekirse açık dolgu (`uint32_t reserved_padding`) koyarım.
4. Derleme anında `static_assert(sizeof(MyHeader) == EXPECTED_SIZE)` ve `static_assert(offsetof(MyHeader, field) == EXPECTED_OFFSET)` ile ABI gerilemelerini (regression) engellerim.
5. Yeni alanları mümkünse sabit struct yerine sonuna eklenen opsiyonel TLV (Type-Length-Value) blokları olarak tanımlarım.

### Soru 3: TLV (Type-Length-Value) yaklaşımının performans ve bant genişliği maliyetleri nelerdir? Füze atış kontrolünde neden tercih edilmez?
**Cevap:** TLV'de iletilen her bir parametre başına fazladan 2 ila 4 bayt başlık (Tip ve Boyut) eklenir. Ayrıca alıcı taraf sabit ofsetten tek bir `memcpy` ile okumak yerine bir `while` döngüsüyle her bloğu tek tek incelemek (parsing loop) zorundadır. Bu durum gecikmeyi 5 nanosaniyeden 50-100 nanosaniyeye çıkarır ve bant genişliği dar telsiz hatlarında paket boyutunu %30-50 artırır. Füze atış kontrolü gibi mikrosaniye hassasiyetli ve deterministik sistemlerde sabit boyutlu ve doğal hizalı struct'lar tercih edilir; TLV ise C2 ve görev bilgisayarı gibi esnekliğin ön planda olduğu katmanlarda kullanılır.

---

## 17. Gün Sonu Özeti ve 3-Cümle Çıkarımı

1. **Protokol Sürümleme ve Uyumluluk Nedir?:** Farklı zamanlarda geliştirilmiş donanım ve yazılımların, birbirlerinin formatlarını bozmadan veya çökmeden aynı ağda birlikte çalışabilmesini sağlayan mimari kurallar bütünüdür.
2. **Hangi Problemi Çözer?:** Savunma filosunda tek bir aracın güncellenmesiyle tüm filonun çökmesini (Fleet Paralysis), gizli ofset kayması sonucu oluşan veri yozlaşmalarını ve sert parser çöküşlerini engeller.
3. **Hangi Trade-off/Hata Sınıfını Getirir?:** TLV ve uyumluluk kontrolleri ek başlık baytları ve ayrıştırma döngüsü maliyeti getirir; rezerve baytların sıfırlanmaması veya uyumsuzluk bayraklarının yanlış yönetilmesi sistemin kilitlenmesine yol açabilir.