# GÜN 202: DDS IDL ve Üretilen Tipler (Generated Types) — OMG IDL 4.2 Sözleşmeleri, fastddsgen Derleme Hattı, TypeSupport ve Sıfır-Bellek C++20 Serileştirmesi

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.

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

### Yönetici Özeti (Executive Summary)
Dağıtık ve heterojen savunma sistemlerinde (örneğin C++20 ile koşan AESA radar kartı, C99 ile koşan ARM Cortex-M füze güdüm bilgisayarı ve Python/Rust ile koşan taktik yer istasyonu) en büyük risk, veri yapıları arasındaki tip ve bellek hizalama uyumsuzluğudur. **OMG IDL (Interface Definition Language)**, programlama dillerinden ve donanım mimarilerinden bağımsız evrensel bir sözleşme dilidir. Geliştirici veriyi tek bir `.idl` dosyasında tanımlar; ardından **`fastddsgen`** veya ROS 2 **`rosidl`** derleyicisi bu dosyadan C++20 veri sınıflarını, CDR serileştirme fonksiyonlarını (`serialize`/`deserialize`), anahtar çıkarma kodlarını (`getKey`) ve **`TypeSupport`** arayüzlerini otomatik olarak üretir. Bu yaklaşım, el ile yazılan serileştirme kodlarındaki insan hatalarını tamamen ortadan kaldırır.

### Junior Mühendis İçin Sezgisel Zihinsel Model (Mental Model)
Bunu uluslararası bir **Mühendislik Teknik Çizimi (Blue-Print)** gibi düşünebilirsiniz:
* **IDL Dosyası (`.idl`):** Standart bir vida ve cıvatanın teknik çizimidir. Çizim tarafsızdır; Türkçe veya İngilizce bilmez, sadece milimetre ve açı değerleri içerir.
* **IDL Derleyicisi (`fastddsgen`):** Bu teknik çizimi okuyup fabrikadaki CNC tezgâhına talimat gönderen CAD/CAM yazılımıdır.
* **Üretilen Kod (`Generated Type`):** CNC tezgâhından çıkan vidanın kendisidir. C++ için `struct`, C için `typedef struct`, Rust için `pub struct` olarak üretilir.
* **TypeSupport (Montaj Kılavuzu):** Vidanın hangi torkla sıkılacağını ve kutulanacağını (CDR Serileştirme) anlatan otomatik üretilmiş koddur.
* **Sonuç:** Almanya'daki mühendis C++ ile, Türkiye'deki mühendis C99 ile çalışsa bile aynı teknik çizimden (`.idl`) üretilen cıvata ve vida birbirine mikron seviyesinde tam oturur!

## Savunma Sanayii Bağlamı ve Endüstri Standartları (OMG IDL v4.2 & DDS XTypes)

Savunma projelerinde (HİSAR, SİPER, GENESİS, MMU KAAN Aviyonik Mimari) alt yükleniciler farklı diller ve işletim sistemleri kullanır. Ortak veri omurgasının hatasız işlemesi için **Tek Doğruluk Kaynağı (Single Source of Truth - SSoT)** ilkesi zorunludur:

```
+-----------------------------------------------------------------------------------+
|                        TEK DOĞRULUK KAYNAĞI: IDL SÖZLEŞMESİ                       |
|                             AvionicsRadarTrack.idl                                |
+-----------------------------------------+-----------------------------------------+
                                          |
                +-------------------------+-------------------------+
                |                                                   |
                v (fastddsgen -typeObject)                          v (fastddsgen)
+-------------------------------+                   +-------------------------------+
|      ÜRETİLEN C++20 KODU      |                   |       ÜRETİLEN C99 KODU       |
|  - AvionicsRadarTrack.h/.cxx  |                   |  - AvionicsRadarTrack.h       |
|  - AvionicsRadarTrackPubSub...|                   |  - C-Style CDR Encoder        |
|  - Rule of Five, Move Sem.    |                   |  - Zero-Heap Struct Layout    |
|  - constexpr MaxCdrSize       |                   |  - ARM Cortex-M Bare-Metal    |
+-------------------------------+                   +-------------------------------+
                |                                                   |
                +-------------------------+-------------------------+
                                          |
                                          v
                      [ KÜRESEL VERİ ALANI (GDS) ]
              Doğrulama: 128-bit TypeObject Hash Tam Eşleşmesi
```

### Standartlar:
1. **OMG IDL v4.2 (ISO/IEC 19516):** Donanım ve dilden bağımsız arayüz tanımlama standardı.
2. **DDS XTypes v1.3 (Extensible and Dynamic Topic Types):** `@key`, `@id`, `@final`, `@appendable` ve `@mutable` etiketleriyle sistemler canlıyken tiplerin geriye dönük uyumlu evrilmesi.
3. **DO-178C Level A / DO-330 Araç Kalifikasyonu:** Otomatik üretilen kodların statik analize (`cppcheck`, `clang-tidy`, `MISRA C++20`) tam uyumlu olması ve çalışma zamanında heap tahsisi yapmaması zorunludur.

## Matematiksel Temeller: Maksimum Serileştirilmiş Boyut (MaxSerializedSize)

Aviyonik sistemlerde bellek havuzlarının başlangıçta (init aşamasında) sabit boyutlu ayrılabilmesi için `fastddsgen` her IDL struct'ı için deterministik bir **`getMaxCdrSerializedSize()`** fonksiyonu üretir.

Bir struct içindeki alanlar $f_1, f_2, \dots, f_k$ olsun. Mevcut akış ofseti $O$ ve alan boyutu $S(f_i)$ olduğunda, yeni ofset:

$$O_{i} = O_{i-1} + P(O_{i-1}, A_i) + S(f_i)$$

Burada $A_i = \min(S(f_i), 8)$ doğal hizalama sınırı ve dolgu baytı:

$$P(O, A) = (A - (O \pmod A)) \pmod A$$

### Maksimum CDR Boyutu Denklemi:
IDL derleyicisi en kötü durum hizalamasını (Worst-Case Padding) hesaba katarak en baştan tavan boyutu hesaplar:

$$S_{max} = 4\text{ Bayt (CDR Başlığı)} + \sum_{i=1}^{k} \Big( (A_i - 1) + S_{max}(f_i) \Big)$$

> **Havacılık Avantajı:** $S_{max}$ derleme zamanında (`constexpr`) bilindiği için, `PreallocatedWHC` ve `PreallocatedRHC` bellek blokları tek bir byte bile taşmadan veya dinamik büyümeye (`realloc`) ihtiyaç duymadan tamı tamına ayrılabilir!

```python
# ==============================================================================
# KOD 1: Minimal IDL Ayrıştırıcı ve C++20 Tip Üreteci (Junior Model)
# Amaç: Bir IDL metnini parse etmek, alanları ve @key etiketini tespit etmek,
# C++20 struct kodunu ve CDR boyut hesaplama metodunu otomatik üretmek.
# ==============================================================================

import re
from dataclasses import dataclass
from typing import List

@dataclass
class IDLField:
    name: str
    idl_type: str
    is_key: bool
    size_bytes: int
    alignment: int

class MiniIDLCompiler:
    TYPE_MAP = {
        "unsigned long": (4, 4, "uint32_t"),
        "float":         (4, 4, "float"),
        "double":        (8, 8, "double"),
        "octet":         (1, 1, "uint8_t"),
        "unsigned short":(2, 2, "uint16_t")
    }

    def __init__(self, idl_source: str):
        self.idl_source = idl_source
        self.struct_name = ""
        self.fields: List[IDLField] = []

    def parse(self):
        # Struct adını yakala
        struct_match = re.search(r"struct\s+(\w+)\s*\{", self.idl_source)
        if struct_match:
            self.struct_name = struct_match.group(1)

        # Alanları yakala: [@key] <type> <name>;
        field_matches = re.findall(r"(@key\s+)?(\w+(?:\s+\w+)?)\s+(\w+)\s*;", self.idl_source)
        for key_tag, idl_type, field_name in field_matches:
            is_key = bool(key_tag)
            idl_type = idl_type.strip()
            if idl_type in self.TYPE_MAP:
                size, align, _ = self.TYPE_MAP[idl_type]
                self.fields.append(IDLField(field_name, idl_type, is_key, size, align))

    def generate_cpp_code(self) -> str:
        lines = [
            f"// Otomatik Üretilen C++20 Başlık Dosyası: {self.struct_name}.h",
            "#pragma once",
            "#include <cstdint>",
            "",
            f"struct {self.struct_name} {{",
        ]
        for f in self.fields:
            _, _, cpp_type = self.TYPE_MAP[f.idl_type]
            key_comment = " // [@key]" if f.is_key else ""
            lines.append(f"    {cpp_type} {f.name};{key_comment}")

        # constexpr MaxSerializedSize metodu
        max_size = 4 # CDR Header
        for f in self.fields:
            max_size += (f.alignment - 1) + f.size_bytes

        lines.extend([
            "",
            f"    static constexpr size_t getMaxCdrSerializedSize() {{",
            f"        return {max_size}; // 4B Header + Dolgular + Veri",
            "    }",
            "};"
        ])
        return "\n".join(lines)

# Test Senaryosu: Örnek Radar Hedef IDL'i
test_idl = '''
struct RadarTrack {
    @key unsigned long track_id;
    float azimuth;
    double range_km;
    unsigned short quality;
};
'''

compiler = MiniIDLCompiler(test_idl)
compiler.parse()
cpp_output = compiler.generate_cpp_code()

print("[KOD 1] IDL Ayrıştırma ve Otomatik C++20 Kod Üretimi:")
print(cpp_output)

# Assertions:
assert compiler.struct_name == "RadarTrack"
assert len(compiler.fields) == 4
assert compiler.fields[0].name == "track_id" and compiler.fields[0].is_key == True
assert compiler.fields[2].alignment == 8 # double 8-byte hizalanmalı

print("\n[PASS] Mini IDL Ayrıştırıcı ve C++20 Kod Üreteci Başarıyla Doğrulandı.")
```

### Kod 1 İncelemesi: `fastddsgen` Kod Üretiminin Arka Planı
Yukarıdaki mini derleyici, gerçek dünyada Java ile yazılmış olan `fastddsgen` aracının çekirdek mantığını modeller:
1. **İnsan Hatasını Sıfırlama:** Geliştirici C++ sınıfını, veri tiplerini ve bellek hizalamasını elle yazmaz. Elle yazılan struct'larda alan sırası değiştirildiğinde unutulan bir padding tüm sistemi çökertebilir.
2. **`@key` Otomasyonu:** IDL içindeki `@key` ifadesi doğrudan C++ koduna taşınır ve `getKey()` fonksiyonu bu alanları hash'leyecek şekilde derlenir.
3. **Statik Tavan Boyut (`getMaxCdrSerializedSize`):** Ağ tamponlarının boyutları çalışma zamanında dinamik olarak değil, derleme zamanında `constexpr` olarak kesinleşir.

## `TopicDataType` ve `TypeSupport` Arayüz Sözleşmesi

`DataWriter` ve `DataReader` şablon (template) sınıflar değildir; çekirdekte `void*` düzeyinde ham ikili baytlarla çalışırlar. Peki DDS çekirdeği kullanıcı struct'ını nasıl serileştirir? Cevap: **`TopicDataType`**.

```
                +------------------------------------+
                |       DomainParticipant            |
                +-----------------+------------------+
                                  | register_type(type_support)
                                  v
+--------------------------------------------------------------------+
|               eprosima::fastdds::dds::TopicDataType                |
|  - serialize(void* data, SerializedPayload_t* payload)             |
|  - deserialize(SerializedPayload_t* payload, void* data)           |
|  - getKey(void* data, InstanceHandle_t* handle, bool force_md5)    |
|  - getSerializedSizeProvider(void* data)                           |
+---------------------------------+----------------------------------+
                                  |
            +---------------------+---------------------+
            |                                           |
            v                                           v
+---------------------------+               +---------------------------+
|        DataWriter         |               |        DataReader         |
|  - write(sample)          |               |  - take(sample)           |
|  - TypeSupport::serialize |               |  - TypeSupport::deserial. |
+---------------------------+               +---------------------------+
```

### TypeSupport'un 3 Hayati Fonksiyonu:
1. **`serialize()`:** C++ nesnesini alır, doğal hizalama kurallarıyla CDR bayt dizisine yazar.
2. **`deserialize()`:** Ağdan gelen CDR baytlarını okuyup C++ struct alanlarına kopyalar.
3. **`getKey()`:** Yalnızca `@key` işaretli alanları serileştirip MD5 hash'ini alarak $16$-baytlık `InstanceHandle_t` üretir.

```python
# ==============================================================================
# KOD 2: Üretilen TypeSupport ve Çapraz-Endianlık (Endianness) Motoru
# Amaç: TypeSupport arayüzünü gerçekleştirmek, Little-Endian ve Big-Endian
# donanımlar arasında bayt takasını (byte-swapping) doğrulamak ve getKey üretmek.
# ==============================================================================

import struct
import hashlib
from typing import Tuple

@dataclass
class GeneratedRadarTrack:
    track_id: int # @key (uint32)
    x: float      # float (4B)
    y: float      # float (4B)
    altitude: int # uint16 (2B)

class RadarTrackPubSubType:
    # OMG CDR Header: 0x0001 = Little-Endian, 0x0000 = Big-Endian
    CDR_LE = 0x0001
    CDR_BE = 0x0000

    def __init__(self, type_name: str = "defense::radar::RadarTrack"):
        self.type_name = type_name

    def serialize(self, data: GeneratedRadarTrack, is_little_endian: bool = True) -> bytes:
        endian_flag = "<" if is_little_endian else ">"
        hdr_val = self.CDR_LE if is_little_endian else self.CDR_BE

        # CDR Başlığı: 2B Endian + 2B Options (Toplam 4B)
        header = struct.pack(f"{endian_flag}HH", hdr_val, 0x0000)

        # Doğal Hizalama ile Veri Serileştirme:
        # [4B track_id] + [4B x] + [4B y] + [2B alt] + [2B PADDING]
        payload = struct.pack(
            f"{endian_flag}IffHxx",
            data.track_id,
            data.x,
            data.y,
            data.altitude
        )
        return header + payload

    def deserialize(self, raw_bytes: bytes) -> GeneratedRadarTrack:
        assert len(raw_bytes) >= 4, "Geçersiz paket boyutu!"
        # İlk 2 bayttan Endianness tespit edilir
        raw_endian = struct.unpack_from("!H", raw_bytes, 0)[0]
        endian_flag = "<" if raw_endian == 0x0100 or raw_endian == 0x0001 else ">"

        track_id, x, y, alt = struct.unpack_from(f"{endian_flag}IffH", raw_bytes, 4)
        return GeneratedRadarTrack(track_id=track_id, x=x, y=y, altitude=alt)

    def get_key(self, data: GeneratedRadarTrack) -> str:
        # Yalnızca @key alanı olan track_id'yi hash'le
        key_bytes = struct.pack("<I", data.track_id)
        return hashlib.md5(key_bytes).hexdigest()[:16]

# Doğrulama: Çapraz Endianlık Testi
type_support = RadarTrackPubSubType()
original_track = GeneratedRadarTrack(track_id=808, x=150.5, y=300.25, altitude=9500)

# 1. Little-Endian (x86_64 / ARM64) Serileştirme:
bytes_le = type_support.serialize(original_track, is_little_endian=True)
deser_le = type_support.deserialize(bytes_le)

# 2. Big-Endian (Eski Aviyonik PowerPC / DSP) Serileştirme:
bytes_be = type_support.serialize(original_track, is_little_endian=False)
deser_be = type_support.deserialize(bytes_be)

key_handle = type_support.get_key(original_track)

print("[KOD 2] TypeSupport ve Endianness Doğrulama Sonuçları:")
print(f"  - Little-Endian Paket Boyutu: {len(bytes_le)} Bayt | Hex: {bytes_le.hex()[:24]}...")
print(f"  - Big-Endian Paket Boyutu   : {len(bytes_be)} Bayt | Hex: {bytes_be.hex()[:24]}...")
print(f"  - Çıkarılan Instance Handle : {key_handle}")

# Assertions:
assert deser_le == original_track, "Little-Endian serileştirme bozuldu!"
assert deser_be == original_track, "Big-Endian serileştirme bozuldu!"
assert bytes_le != bytes_be, "LE ve BE ikili formatları farklı olmalıdır!"
assert len(bytes_le) == 20, "Toplam boyut 4B Header + 16B Hizalamalı Veri = 20B olmalı!"

print("[PASS] TypeSupport Çapraz Platform CDR Serileştirmesi Başarıyla Doğrulandı.")
```

### Kod 2 İncelemesi: Donanım Mimarisi Şeffaflığı
1. **İkili Uyumluluk (Binary Transparency):** Big-Endian bir uçuş kontrol bilgisayarından çıkan veri ile Little-Endian bir yer kontrol istasyonu konuşurken geliştirici tek satır `ntohl` veya `htons` takas fonksiyonu yazmak zorunda kalmamıştır. CDR başlığı (`0x0001` vs `0x0000`) sayesinde alıcı taraf bayt sırasını otomatik tespit eder ve çözer.
2. **`get_key()` Optimizasyonu:** `get_key()` fonksiyonu tüm struct'ı değil, sadece `@key` alanını hash'lemiştir. Bu sayede $1\text{ KB}$ boyutundaki bir hedef struct'ında bile anahtar çıkarma işlemi birkaç nanosaniyede biter.

## DDS XTypes (Genişletilebilir Tipler) ve TypeObject Parmak İzi

Bir radar yazılımı v1.0 sürümündeyken füzeler sahaya sürülmüş olsun. 2 yıl sonra radara yeni bir özellik eklenip struct'a `float electronic_countermeasure_prob;` alanı eklenirse ne olur? Tüm füzeleri toplatıp yeniden mi derleyeceğiz?

### DDS XTypes Çözümü (Extensibility Annotations):
```idl
@appendable // Sona yeni alan eklenebilir!
struct RadarTrack {
    @key unsigned long track_id;
    float x;
    float y;
    // v2.0 ile eklenen alan:
    @id(3) float ecm_prob;
};
```

1. **`@final` (Kesin):** Tip asla genişletilemez. Bellek eşleme en hızlıdır, sıfır ek yük taşır.
2. **`@appendable` (Eklenebilir):** Tipin sonuna yeni alanlar eklenebilir. Eski alıcılar yeni eklenen alanları sessizce görmezden gelir (Geriye Dönük Uyumluluk).
3. **`@mutable` (Değişken):** Alanlar rastgele sıralarla eklenebilir veya çıkarılabilir (Protobuf benzeri Tag-Length-Value formatı).

```python
# ==============================================================================
# KOD 3: XTypes TypeIdentifier ve Yapısal Tip Hash Doğrulayıcı
# Amaç: IDL tipinin alanlarını ve tiplerini özetleyen TypeObject parmak izi
# üretmek ve iki düğüm arasındaki tip uyuşmazlığını keşifte yakalamak.
# ==============================================================================

import hashlib

class TypeObjectFingerprint:
    @classmethod
    def compute_type_hash(cls, type_name: str, members: List[Tuple[str, str]]) -> str:
        # Üyelerin isim ve tiplerini standart formatta birleştir
        # Örn: "defense::RadarTrack|track_id:uint32|x:float|y:float"
        descriptor = f"{type_name}|" + "|".join([f"{name}:{mtype}" for name, mtype in members])
        # 128-bit MD5 / SHA-256 parmak izi
        return hashlib.sha256(descriptor.encode('utf-8')).hexdigest()[:16]

# Senaryo 1: Radar İstasyonu ve Füze aynı v1.0 sözleşmesini paylaşıyor
members_v1 = [("track_id", "uint32"), ("x", "float"), ("y", "float")]
hash_radar_v1 = TypeObjectFingerprint.compute_type_hash("RadarTrack", members_v1)
hash_missile_v1 = TypeObjectFingerprint.compute_type_hash("RadarTrack", members_v1)

print("[KOD 3] XTypes TypeObject Hash Doğrulaması:")
print(f"  - Radar v1 TypeHash  : {hash_radar_v1}")
print(f"  - Füze  v1 TypeHash  : {hash_missile_v1}")
assert hash_radar_v1 == hash_missile_v1, "Aynı tip tanımları aynı hash'i üretmelidir!"

# Senaryo 2: Geliştirici struct alanını değiştirdi (float -> double)
members_corrupted = [("track_id", "uint32"), ("x", "double"), ("y", "float")]
hash_corrupted = TypeObjectFingerprint.compute_type_hash("RadarTrack", members_corrupted)

print(f"\n  - Değiştirilmiş TypeHash: {hash_corrupted}")
assert hash_corrupted != hash_radar_v1, "Değişen tip tanımı farklı hash üretmelidir!"

print("[PASS] TypeObject Yapısal Parmak İzi ile Tip Tutarlılığı Doğrulandı.")
```

### Kod 3 İncelemesi: Sessiz Veri Bozulmalarına Son
Geleneksel C/C++ ağ soketlerinde struct içine bir `double` ekleyip karşı tarafa haber vermezseniz, kod derlenir ve paketler akar; fakat tüm sayılar tamamen kayar ve saçmalar. DDS XTypes `TypeObject` hash'i sayesinde SEDP el sıkışmasında bu parmak izi karşılaştırılır. Uyuşmazlık varsa düğümler birbirine bağlanmaz (`INCONSISTENT_TOPIC`).

## Hata Modları: IDL Derleme ve Tip Üretim Tuzakları

Savunma sanayiinde `fastddsgen` ve IDL süreçlerinde en sık yapılan 4 kritik hata:
1. **Sınırlandırılmamış String/Dizi Kullanımı (Unbounded Types):**
   IDL'de `string name;` yazmak. Havacılık standartlarında derleme bayrağıyla (`-strict-types`) engellenmelidir; her zaman `string<32> name;` yazılmalıdır.
2. **Derleme Öncesi IDL Temizliği Yapılmaması:**
   IDL değiştiğinde `fastddsgen` çalıştırmayı unutup eski `.cxx` dosyalarıyla projeyi derlemek (Desynchronized Headers).
3. **Struct Alanlarının Bellek Hizalamasını Gözetmemesi:**
   Küçük tiplerin arasına büyük tipler serpiştirilerek gereksiz dolgu baytlarıyla ağ bant genişliğinin israf edilmesi.
4. **Çok Sayıda `@key` Alanı Atamak:**
   Bir struct'ta 5 farklı alana `@key` koymak anahtar hash hesaplama süresini 10 katına çıkarır.

```python
# ==============================================================================
# KOD 4: Hata Enjeksiyonu (Fault Injection) ve Tip Güvenliği Sınır Testleri
# Senaryolar:
#   Test A: XTypes Tip Uyuşmazlığı Nedeniyle Bağlantı Reddi (Inconsistent Topic)
#   Test B: Bounded String Sınır Aşımı Doğrulaması
#   Test C: Bozuk / Eksik CDR Paketi Çözümleme Hatası (Truncated Payload)
# ==============================================================================

class IDLValidationError(Exception):
    pass

# TEST A: XTypes Keşif Uyuşmazlığı
def check_type_compatibility(hash_a: str, hash_b: str):
    if hash_a != hash_b:
        raise IDLValidationError(
            f"TYPE_INCONSISTENCY: Tip özetleri uyuşmuyor! ({hash_a} != {hash_b}) "
            "Keşif reddedildi, veri aktarımı engellendi."
        )

type_mismatch_caught = False
try:
    check_type_compatibility("a1b2c3d4e5f60000", "ffff000011112222")
except IDLValidationError as e:
    type_mismatch_caught = True
    print(f"[TEST A] Beklenen Tip Uyuşmazlığı Reddi Yakalandı:\n  -> {e}")

assert type_mismatch_caught, "Farklı tipler arasındaki bağlantı engellenmeliydi!"

# TEST B: Sınırlandırılmamış Tip Yasağı (DO-178C Statik Kural Denetimi)
def audit_idl_safety(idl_text: str):
    # 'string ' veya 'sequence<T>' serbest kullanımları yakalar (yanında <N> olmayan)
    unbounded_strings = re.findall(r"\bstring\s+\w+\s*;", idl_text)
    if unbounded_strings:
        raise IDLValidationError(
            f"UNBOUNDED_TYPE_VIOLATION: Statik bellek kuralı ihlali! "
            f"Sınırlandırılmamış string bulundu: {unbounded_strings}"
        )

safety_violation_caught = False
try:
    bad_idl = "struct UnsafeTelemetry { string aircraft_name; };"
    audit_idl_safety(bad_idl)
except IDLValidationError as e:
    safety_violation_caught = True
    print(f"\n[TEST B] Beklenen DO-178C Tip Güvenliği İhlali Yakalandı:\n  -> {e}")

assert safety_violation_caught, "Sınırlandırılmamış string reddedilmeliydi!"

# TEST C: Bozulmuş / Kesilmiş CDR Paketi
truncated_bytes = b"\x00\x01\x00\x00\x01\x02" # 20 bayt olması gerekirken 6 bayt
truncated_caught = False
try:
    type_support.deserialize(truncated_bytes)
except Exception as e:
    truncated_caught = True
    print(f"\n[TEST C] Kesilmiş Paket Ayrıştırma Hatası Yakalandı: {e}")

assert truncated_caught, "Eksik bayt içeren paket exception fırlatmalıydı!"

print("\n[PASS] 3 Kritik IDL Hata Enjeksiyonu ve Güvenlik Testi Geçti.")
```

### Kod 4 Hata Triage ve Çözüm Tablosu

| Hata Kodu / Belirti | Kök Neden (Root Cause) | Saha Sonucu | Kıdemli Mühendis Çözümü |
|---|---|---|---|
| **`TYPE_INCONSISTENCY`** | İki ayrı ekibin IDL dosyasını senkronize etmeden derleme yapması | Radar ile silah sistemi el sıkışamaz, sistem kilitlenir. | IDL dosyalarını ortak bir Git alt modülünde (Submodule) kilitlemek ve CI/CD'de TypeObject doğrulaması yapmak. |
| **`UNBOUNDED_TYPE_VIOLATION`** | IDL içinde `string<N>` yerine serbest `string` kullanılması | Havacılık güvenlik sertifikasyonu (DO-178C) denetiminde yazılım reddedilir. | CI pipeline'ına IDL linter ekleyerek sınırlandırılmamış tipleri otomatik engellemek. |
| **`Truncated Payload`** | Ağ paketinin MTU sınırında bölünmesi veya donanımsal kesilme | Deserializer çöker veya çöp veri üretir. | CDR başlığındaki boyut bilgisini doğrulamak ve güvenli `unpack_from` kullanmak. |

## `fastddsgen` Derleme Hattı ve Savunma Sanayii CI/CD Entegrasyonu

Modern bir aviyonik projede IDL derleme süreci elle değil, CMake ve CI/CD hattıyla tam otomatik yürütülür:

```cmake
# CMakeLists.txt Otomatik IDL Üretim Kuralı
find_program(FASTDDSGEN_BIN fastddsgen REQUIRED)

add_custom_command(
    OUTPUT 
        ${CMAKE_CURRENT_BINARY_DIR}/RadarTrack.cxx
        ${CMAKE_CURRENT_BINARY_DIR}/RadarTrack.h
        ${CMAKE_CURRENT_BINARY_DIR}/RadarTrackPubSubTypes.cxx
        ${CMAKE_CURRENT_BINARY_DIR}/RadarTrackPubSubTypes.h
    COMMAND ${FASTDDSGEN_BIN} -replace -typeObject -d ${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/RadarTrack.idl
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/RadarTrack.idl
    COMMENT "fastddsgen ile C++20 Tipleri Otomatik Derleniyor..."
)

add_library(radar_messages_lib STATIC
    ${CMAKE_CURRENT_BINARY_DIR}/RadarTrack.cxx
    ${CMAKE_CURRENT_BINARY_DIR}/RadarTrackPubSubTypes.cxx
)
```

Bu sayede geliştirici `.idl` dosyasını değiştirdiği anda tüm C++ sınıfları derleme anında otomatik güncellenir.

```python
# ==============================================================================
# KOD 5: Üretilen C++ Serileştirme vs Yansıma/Manuel Ayrıştırma Kıyaslaması
# Amaç: 100,000 örnek üzerinde statik üretilmiş tip serileştirmesi ile
# dinamik sözlük/JSON serileştirme arasındaki hız ve gecikme farkını ölçmek.
# ==============================================================================

import time
import json
import struct

NUM_SAMPLES = 100000

# 1. Üretilmiş Statik Tip Simülasyonu (Doğal İkili Bellek Eşleme)
# [4B id] + [4B x] + [4B y] + [2B alt] + [2B pad] = 16B
TRACK_FMT = "<IffHxx"

t0 = time.perf_counter_ns()
for i in range(NUM_SAMPLES):
    # Statik struct serileştirme (fastddsgen koduna eşdeğer)
    raw_bin = struct.pack(TRACK_FMT, i, 120.5, 450.2, 8500)
    # Deserialization
    _ = struct.unpack(TRACK_FMT, raw_bin)
t1 = time.perf_counter_ns()

gen_duration_ms = (t1 - t0) / 1e6
gen_per_sample_ns = (t1 - t0) / NUM_SAMPLES
gen_throughput_mb_s = ((NUM_SAMPLES * 16) / (1024 * 1024)) / ((t1 - t0) / 1e9)

# 2. Dinamik JSON Yaklaşımı (Klasik Web/IoT Yöntemi - Kıyaslama)
sample_dict = {"track_id": 101, "x": 120.5, "y": 450.2, "alt": 8500}
t2 = time.perf_counter_ns()
for i in range(NUM_SAMPLES):
    json_str = json.dumps(sample_dict)
    _ = json.loads(json_str)
t3 = time.perf_counter_ns()

json_duration_ms = (t3 - t2) / 1e6
speedup = json_duration_ms / gen_duration_ms

print("[KOD 5] Serileştirme Başarım Kıyaslama Sonuçları:")
print(f"  - Toplam İşlenen Örnek            : {NUM_SAMPLES:,}")
print(f"  - Üretilen C++ Tipi Süresi        : {gen_duration_ms:.2f} ms ({gen_per_sample_ns:.1f} ns/örnek)")
print(f"  - Üretilen Tip Veri Hızı          : {gen_throughput_mb_s:.2f} MB/s")
print(f"  - Dinamik JSON Süresi             : {json_duration_ms:.2f} ms")
print(f"  - IDL Üretilen Kod Hız Avantajı   : {speedup:.1f} KAT DAHA HIZLI!")

# Doğrulama:
assert gen_per_sample_ns < 10000.0, "Statik serileştirme 10 mikrosaniyenin altında olmalı!"
assert speedup > 3.0, "Üretilen kod JSON'a kıyasla en az 3 kat hızlı olmalı!"

print("[PASS] Üretilen C++ Tip Başarım Kıyaslaması Başarıyla Tamamlandı.")
```

### Kod 5 Analizi: Neden IDL ile Kod Üretimi?
* **Nanosaniye Seviyesinde Yürütme:** Statik üretilen serileştirme kodu örnek başına nanosaniyeler mertebesinde tamamlanmıştır.
* **Metin Ayrıştırma Yükünden Kurtuluş:** JSON veya dinamik sözlük yaklaşımı string parsing, bellek tahsisi ve sayı dönüşümü yüzünden defalarca daha yavaş kalmış ve yüksek CPU çekişmesi yaratmıştır. Bu sonuç, savunma sistemlerinde neden saf ikili CDR ve IDL kullanıldığını matematiksel olarak açıklar.

## Gerçek Dünyadaki Teknoloji: Fast DDS `fastddsgen` ve ROS 2 `rosidl`

Savunma ve robotik projelerinde iş akışı:

### 1. `fastddsgen` CLI Kullanımı:
```bash
# C++20 Uyumlu Tip ve TypeObject Üretimi
fastddsgen -replace -typeObject -cs AvionicsRadarTrack.idl
```
Oluşan Dosyalar:
* `AvionicsRadarTrack.h` & `.cxx`: Veri modeli.
* `AvionicsRadarTrackPubSubTypes.h` & `.cxx`: TypeSupport ve serileştirme.

### 2. ROS 2 `rosidl` Boru Hattı:
ROS 2 geliştiricisi `RadarTrack.msg` dosyasını yazar:
```text
uint32 track_id
float32 x
float32 y
float32 altitude
```
ROS 2 derleme sistemi (`colcon build`) arka planda bu `.msg` dosyasını önce bir `.idl` dosyasına çevirir, ardından DDS sağlayıcısının (Fast DDS / Cyclone DDS) kod üretecini tetikleyerek C++20 header ve kütüphanelerini üretir.

Resmi Doküman Referansı: *eProsima fastddsgen User Manual, "Code Generation from IDL", v2.14, 2024.*

## Bellek İzi ve Kaynak Yönetimi (Resource Footprint)

Otomatik üretilen tip desteğinin sistem kaynaklarına etkisi:
* **Statik Kod Boyutu (Flash / Text Segment):** Her bir IDL struct için üretilen TypeSupport ve CDR fonksiyonları derlenmiş ikili dosyaya (binary) yaklaşık $6 - 18\text{ KB}$ ekler.
* **Çalışma Zamanı Belleği (RAM):**
  - Sıfır dinamik bellek: `serialize()` ve `deserialize()` fonksiyonları kullanıcı tarafından sağlanan statik tamponlar üzerinde çalıştığı için heap harcamaz ($0\text{ Bayt malloc}$).
* **TypeObject Meta-Verisi:** XTypes uyumluluk tablosu bellek üzerinde yaklaşık $1 - 2\text{ KB}$ statik salt-okunur veri (`.rodata`) kaplar.

## Kıdemli Mühendis Tuzakları ve Anti-Pattern'ler (Senior Anti-Patterns)

### 1. "IDL Dosyası Yerine Elle C++ Struct Yazıp Ham Void* Göndermek":
* **Hata:** IDL kullanmayıp C++ struct'ını doğrudan `memcpy` ile sokete basmak.
* **Sonuç:** Farklı derleyici bayrakları (`-O3`, `-m32` vs `-m64`) veya mimari farklarında struct dolguları kayar ve sistem çöker.
* **Doğrusu:** Her zaman resmi IDL derleyicisinin ürettiği CDR kodunu kullanmak.

### 2. "IDL İçinde Mantıksız Alan Sıralaması Yapmak":
* **Hata:** `octet flag1; double val1; octet flag2; double val2;` şeklinde sıralama yapmak.
* **Sonuç:** Her `double` alanından önce 7 bayt boşluk (padding) eklenir; 18 baytlık veri 32 bayta fırlar!
* **Doğrusu:** Alanları azalan boyut sırasına göre dizmek (`double` $\to$ `float` $\to$ `short` $\to$ `octet`).

### 3. "IDL Değişikliklerinde Eski Üretilmiş Dosyaları Silmemek":
* **Hata:** IDL'de alan silindiğinde eski header dosyasının projede kalması ve derleme uyumsuzluğu üretmesi.
* **Doğrusu:** CMake içinde `fastddsgen -replace` parametresiyle temiz derleme sağlamak.

```python
# ==============================================================================
# KOD 6: 4-Panelli Master Görselleştirme Paneli (Publication-Quality Artifact)
# Amaç: IDL derleme hattını, CDR bayt hizalamasını, XTypes uyumluluğunu
# ve serileştirme hız kıyaslamasını gösteren teknik dashboard üretmek.
# ==============================================================================

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# PNG dosya yolu belirleme (Dizin garantili)
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_202_idl_ve_generated_type.png")
    except Exception:
        PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_202/gun_202_idl_ve_generated_type.png"

# Koyu Tema ve Tipografi Ayarları
plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.grid(True, linestyle='--', alpha=0.3, color='#64748B')
    ax.tick_params(colors='#E2E8F0', labelsize=10)
    for spine in ax.spines.values():
        spine.set_color('#475569')

# ------------------------------------------------------------------------------
# PANEL 1: IDL Derleme Boru Hattı ve Üretilen Bileşenler
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. OMG IDL Derleme Hattı (fastddsgen & rosidl Pipeline)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

pipeline_nodes = [
    ("Sözleşme Dosyası\nRadarTrack.idl\n(Tek Doğruluk Kaynağı)", 0.2, 0.7, "#6366F1"),
    ("fastddsgen Derleyicisi\n(AST & Kod Üretim Motoru)", 0.5, 0.7, "#D97706"),
    ("Üretilen C++ Sınıfı\nRadarTrack.h / .cxx\n(C++20 Veri Tipi)", 0.8, 0.85, "#0284C7"),
    ("TypeSupport Arayüzü\nRadarTrackPubSubTypes.h\n(serialize/deserialize/getKey)", 0.8, 0.45, "#059669"),
    ("DDS Çekirdeği\nDataWriter / DataReader", 0.5, 0.2, "#38BDF8")
]

for text, x, y, col in pipeline_nodes:
    ax1.text(x, y, text, ha='center', va='center', color='#F8FAFC', weight='bold', fontsize=8.5,
             bbox=dict(boxstyle='round,pad=0.5', facecolor=col, edgecolor='#CBD5E1', alpha=0.9))

arrow_kw = dict(arrowstyle='->', color='#38BDF8', lw=2)
ax1.annotate('', xy=(0.38, 0.7), xytext=(0.31, 0.7), arrowprops=arrow_kw)
ax1.annotate('', xy=(0.69, 0.82), xytext=(0.61, 0.73), arrowprops=arrow_kw)
ax1.annotate('', xy=(0.69, 0.48), xytext=(0.61, 0.67), arrowprops=arrow_kw)
ax1.annotate('', xy=(0.58, 0.25), xytext=(0.72, 0.40), arrowprops=arrow_kw)

ax1.set_xlim(0.05, 0.95)
ax1.set_ylim(0.05, 0.98)
ax1.axis('off')

# ------------------------------------------------------------------------------
# PANEL 2: CDR Little-Endian vs Big-Endian Bellek Düzeni
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. OMG CDR Bellek Düzeni (Little-Endian vs Big-Endian)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

# Little Endian Bar (y=1.5)
le_blocks = [("HDR LE (4B)", 4, "#6366F1"), ("track_id (4B)", 4, "#38BDF8"), ("x: 150.5 (4B)", 4, "#34D399"), ("alt: 9500 (2B)", 2, "#FBBF24"), ("PAD (2B)", 2, "#EF4444")]
start = 0
for name, w, c in le_blocks:
    ax2.barh(1.5, w, left=start, height=0.4, color=c, edgecolor='#CBD5E1', alpha=0.9)
    ax2.text(start + w/2.0, 1.5, name, ha='center', va='center', color='#0F172A' if c=='#FBBF24' else '#F8FAFC', weight='bold', fontsize=8)
    start += w

# Big Endian Bar (y=0.5)
be_blocks = [("HDR BE (4B)", 4, "#818CF8"), ("track_id (4B)", 4, "#0284C7"), ("x: 150.5 (4B)", 4, "#059669"), ("alt: 9500 (2B)", 2, "#D97706"), ("PAD (2B)", 2, "#DC2626")]
start = 0
for name, w, c in be_blocks:
    ax2.barh(0.5, w, left=start, height=0.4, color=c, edgecolor='#CBD5E1', alpha=0.9)
    ax2.text(start + w/2.0, 0.5, name, ha='center', va='center', color='#0F172A' if c=='#D97706' else '#F8FAFC', weight='bold', fontsize=8)
    start += w

ax2.set_yticks([0.5, 1.5])
ax2.set_yticklabels(['Big-Endian (PowerPC)', 'Little-Endian (x86/ARM)'], color='#E2E8F0', fontsize=9.5)
ax2.set_xlabel("Akıştaki Bayt Ofseti (0 - 16 Bayt)", color='#CBD5E1', fontsize=10)
ax2.set_xlim(0, 18)
ax2.set_ylim(0.0, 2.0)

# ------------------------------------------------------------------------------
# PANEL 3: DDS XTypes Genişletilebilirlik Seviyeleri (Extensibility)
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. DDS XTypes Genişletilebilirlik Seviyeleri (Extensibility Rules)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

categories = ['@final', '@appendable', '@mutable']
overhead = [0, 4, 16] # Bayt cinsinden metaveri ek yükü
flexibility = [1, 3, 5] # Esneklik skoru

x = np.arange(len(categories))
width = 0.35

ax3.bar(x - width/2, overhead, width, label='Protokol Ek Yükü (Bayt/Örnek)', color='#EF4444', edgecolor='#CBD5E1', alpha=0.85)
ax3.bar(x + width/2, flexibility, width, label='Tip Evrilme Esnekliği (1-5 Puan)', color='#34D399', edgecolor='#CBD5E1', alpha=0.85)

ax3.set_xticks(x)
ax3.set_xticklabels(categories, color='#E2E8F0', fontsize=10, weight='bold')
ax3.set_ylabel("Değer / Puan", color='#CBD5E1', fontsize=10)
ax3.set_ylim(0, 20)
ax3.legend(loc='upper left', facecolor='#1E293B', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

ax3.annotate('En Yüksek Hız!\n(Aviyonik Seçimi)', xy=(0, 0.5), xytext=(0.05, 7),
             arrowprops=dict(facecolor='#38BDF8', shrink=0.05), color='#38BDF8', weight='bold', fontsize=8.5)

# ------------------------------------------------------------------------------
# PANEL 4: Üretilen C++ Kodu vs Dinamik JSON Serileştirme Kıyaslaması
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. Serileştirme Süresi: Üretilen C++ Kodu vs Dinamik JSON", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

methods = ['fastddsgen Üretilen C++', 'Dinamik JSON Parser']
latencies = [gen_per_sample_ns, gen_per_sample_ns * speedup]
colors_bar = ['#34D399', '#EF4444']

bars = ax4.bar(methods, latencies, color=colors_bar, width=0.45, edgecolor='#CBD5E1', alpha=0.85)
for bar in bars:
    yval = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 50, f"{yval:.1f} ns",
             ha='center', va='bottom', color='#F8FAFC', weight='bold', fontsize=10)

ax4.set_ylabel("Örnek Başına Süre (Nanosaniye)", color='#CBD5E1', fontsize=10)
ax4.set_ylim(0, max(latencies) * 1.3)

info_txt = (
    "PERFORMANS FARKI:\n"
    "-----------------\n"
    f"- Hız Kazancı : {speedup:.1f} Kat Hızlı\n"
    "- Sıfır Heap Ayrımı\n"
    "- Deterministik CDR\n"
    "- Derleme Zamanı Boyut"
)
ax4.text(0.55, 0.65, info_txt, transform=ax4.transAxes,
         fontsize=8.5, color='#E2E8F0', fontfamily='monospace',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.9))

plt.tight_layout()
fig.subplots_adjust(top=0.93)
fig.suptitle("GÜN 202: OMG IDL, FASTDDSGEN KOD ÜRETİMİ, TYPESUPPORT VE XTYPES",
             fontsize=15, color='#F8FAFC', weight='bold')

plt.savefig(PNG_FILE, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(PNG_FILE) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {PNG_FILE}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'den küçük olamaz!"
```

## Görsel Çıktı Analizi ve Mimari Sentez

Üretilen `gun_202_idl_ve_generated_type.png` teknik gösterge paneli dört kritik ilkeyi belgeler:
1. **Panel 1 (Derleme Hattı):** Tek bir `.idl` teknik sözleşmesinin `fastddsgen` üzerinden nasıl hem C++ veri modeline hem de `TopicDataType` serileştirme motoruna dönüştüğünü modeller.
2. **Panel 2 (Çapraz Endianlık):** 4 baytlık CDR başlığı sayesinde Little-Endian (x86/ARM) ile Big-Endian (PowerPC/DSP) mimarilerinin bayt seviyesinde nasıl ayrıştığını ve şeffaf çözüldüğünü gösterir.
3. **Panel 3 (XTypes Kuralları):** `@final` modunun sıfır bayt protokol yüküyle en yüksek aviyonik hızı sağladığını, `@appendable` ve `@mutable` modlarının ise geriye dönük evrilme esnekliği getirdiğini karşılaştırır.
4. **Panel 4 (Hız Kıyaslaması):** Üretilen statik C++ kodunun dinamik JSON yaklaşımına kıyasla katbekat daha hızlı olduğunu ve nanosaniyeler mertebesinde deterministik çalıştığını kanıtlar.

## Aktif Hatırlama ve Savunma Sanayii Mülakat Soruları

### Soru 1: DDS'te serileştirme için neden Protobuf veya JSON yerine OMG IDL ve CDR kullanılır?
**Cevap:** Protobuf ve JSON dinamik metin/anahtar ayrıştırması (parsing) ve değişken uzunluklu tamsayı (`varint`) dönüşümleri gerektirir; bu da CPU yükü ve heap tahsisatı demektir. OMG IDL'den üretilen CDR (Common Data Representation) kodu ise C++ struct yapısıyla doğrudan doğal bellek hizalamalıdır. Veri doğrudan `memcpy` ile tampona yazılır, çalışma zamanında sıfır dinamik bellek ayrılır ve nanosaniye mertebesinde deterministik yürütme sağlanır.

### Soru 2: IDL derleyicisinin ürettiği `getMaxCdrSerializedSize()` fonksiyonunun aviyonik DO-178C sertifikasyonundaki kritik rolü nedir?
**Cevap:** DO-178C Level A standartlarında uçuş sırasında `malloc` veya dinamik bellek büyütme yasaktır. `getMaxCdrSerializedSize()` fonksiyonu, struct'ın en kötü durum dolgu baytları (padding) dahil alabileceği maksimum tavan boyutunu derleme zamanında (`constexpr`) hesaplar. Bu sayede DDS Writer History Cache (WHC) ve soket tamponları sistem açılışında sabit boyutlu tahsis edilir ve uçuş anında bellek taşması riski kesin olarak sıfırlanır.

### Soru 3: Bir IDL dosyasında bir struct alanına `@key` eklenmesi derlenen `TopicDataType` sınıfında neyi değiştirir?
**Cevap:** `TopicDataType` sınıfının `getKey()` fonksiyonu değişir. Bu fonksiyon tüm struct'ı kopyalamak yerine, sadece `@key` işaretli alanları serileştirip MD5 hash'ini alarak $16$-baytlık benzersiz bir `InstanceHandle_t` üretir. Bu sayede DataWriter ve DataReader her gelen verinin hangi fiziksel hedefe (örneğin hangi uçağa) ait olduğunu anında ayırt eder.

## Gün Sonu Özeti ve Gün 203 Önizlemesi

### 3 Cümlelik Gün Sonu Özeti:
1. **OMG IDL ve Üretilen Tipler**, dağıtık savunma sistemlerinde donanım ve dilden bağımsız Tek Doğruluk Kaynağı (SSoT) olarak veri sözleşmelerini kesinleştirir.
2. **`fastddsgen` araç zinciri**, IDL dosyalarından C++20 sınıflarını, TypeSupport arayüzlerini ve doğal hizalamalı CDR serileştirme rutinlerini otomatik üreterek insan hatasını sıfırlar.
3. **XTypes TypeObject parmak izi**, ağdaki düğümlerin yapısal tiplerini keşif anında denetleyerek tip uyuşmazlıklarını ve sahte veri bozulmalarını en baştan engeller.

---

### Yarın: GÜN 203 — DDS Discovery (Keşif Protokolü)
Yarın, ağdaki katılımcıların, yayıncıların ve okuyucuların merkezi bir sunucu olmaksızın birbirini nasıl otomatik keşfettiğini (**SPDP ve SEDP protokolleri, Endpoint Discovery**) derinlemesine kodlayacağız!
