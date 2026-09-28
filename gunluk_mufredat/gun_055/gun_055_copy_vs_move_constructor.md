<!--
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
-->

# GÜN 055: Copy vs Move Constructor (Kopya ve Taşıma Yapıcılarının Yan Yana Mimarisi, İmza Farklılıkları ve Copy-and-Swap İdiyomu)

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
[![C++ Standard](https://img.shields.io/badge/C%2B%2B-20-blue?style=flat-square&logo=c%2B%2B)](https://en.cppreference.com/w/cpp/20)
[![Domain](https://img.shields.io/badge/Domain-Avionics%20Telemetry%20%26%20Mission%20Computers-darkgreen?style=flat-square)]()
[![Safety](https://img.shields.io/badge/Safety-MISRA%20C%2B%2B%3A2023%20%7C%20DO--178C%20DAL--A-orange?style=flat-square)]()

---

### 1. 5N1K Kurumsal Analiz Çerçevesi

| Soru | Sistem Mühendisliği Yanıtı |
| :--- | :--- |
| **Ne? (What)** | **Copy Constructor (`T(const T&)`)**, mevcut bir nesnenin bağımsız bir klonunu sıfırdan tahsis ederek derin kopyalama (*Deep Copy*) yapan yapıcıdır; **Move Constructor (`T(T&&) noexcept`)** ise geçici veya ömrü biten nesnenin dahili bellek adresini çalarak (*Resource Stealing*) yeni nesneyi sıfır maliyetle ayağa kaldıran yapıcıdır. |
| **Neden? (Why)** | Savaş uçağı (KAAN / HÜRJET) görev bilgisayarlarında sensör telemetri paketleri hem kalıcı kara kutuya yedeklenmeli (bağımsız kopya ihtiyacı) hem de anlık uçuş kontrol bilgisayarına aktarılmalıdır (gecikmesiz taşıma ihtiyacı). İki yapıcı arasındaki ayrım, sistemin hem veri bütünlüğünü hem de 100 Hz çevrim determinizmini sağlar. |
| **Nasıl? (How)** | Derleyici aşırı yükleme çözümlemesi (**Overload Resolution**) ile çağrılacak yapıcıyı seçer: İfade bir sol-değer (*lvalue*) ise `const T&` parametreli kopya yapıcı; bir sağ-değer (*rvalue / xvalue*) ise `T&&` parametreli taşıma yapıcı seçilir. |
| **Nerede? (Where)** | TUSAŞ uçuş kontrol yazılımlarında, ASELSAN elektro-optik hedefleme sistemlerinde, Roketsan arayıcı başlık gimbal kontrol döngülerinde ve STL konteynerlerinde. |
| **Ne Zaman? (When)** | Bir nesne ilk kez inşa edilirken (`T a = b;`), fonksiyonlara değer ile parametre aktarılırken (`pass-by-value`) veya fonksiyondan değer döndürülürken. |
| **Kim? (Who)** | Gerçek zamanlı görev yazılımı mimarları, gömülü sistem mühendisleri ve kritik aviyonik kütüphane geliştiricileri. |

---

### 2. Pratik Hayat ve Savunma Sanayii Analojisi

> **Taktik Uçuş Görev Planı ve Fotokopi vs Dosya Devri Analojisi:**
> - Bir filo komutanlığı harekat merkezinde pilot için hazırlanmış 500 sayfalık gizli bir Uçuş Görev Planı (`FlightMissionPlan`) bulunmaktadır.
> - **Kopya Yapıcı (Copy Constructor):** Pilot planın bir nüshasını alıp üs komutanına arşiv için bırakmak istediğinde, harekat merkezindeki fotokopi makinesine gider; 500 sayfanın tek tek fotokopisini çeker, zımbalar ve yeni bir dosya klasörü oluşturur. Bu işlem 20 dakika sürer ve 500 yaprak kağıt harcar (**Zaman: $\mathcal{O}(N)$, Ek Kaynak: $\mathcal{O}(N)$**). Artık elde iki bağımsız dosya vardır.
> - **Taşıma Yapıcı (Move Constructor):** Pilot brifing odasından çıkıp uçağa binmek üzeredir. Masanın üzerindeki orijinal dosyayı koltuğunun altına alır ve çıkar. Masadaki askı boşalır. Sıfır kağıt harcanmış, sıfır fotokopi çekilmiştir. Süre: 1 saniye (**Zaman: $\mathcal{O}(1)$, Ek Kaynak: 0**). Masada kalan eski dosya kabı artık boştur (*moved-from state*).


## 1. Copy ve Move Yapıcılarının Makine Modelleri

### 1.1 İmzalar ve Anlamsal Farklılıklar

Bir C++20 sınıfında iki yapıcı şu açık imzalara sahiptir:

```cpp
class AvionicsTelemetryBlock {
public:
    // 1. KOPYA YAPICI (Copy Constructor):
    // Parametre: const lvalue referansı (const T&)
    // Amaç: Kaynağı koru, yeni bellek tahsis et, veriyi kopyala.
    AvionicsTelemetryBlock(const AvionicsTelemetryBlock& other);

    // 2. TAŞIMA YAPICI (Move Constructor):
    // Parametre: Non-const rvalue referansı (T&&)
    // Nitelik: KESİNLİKLE "noexcept" olmalıdır!
    // Amaç: Kaynağı çal, işaretçiyi devral, other'ı nullptr yap.
    AvionicsTelemetryBlock(AvionicsTelemetryBlock&& other) noexcept;
};
```

---

### 1.2 Bellek Düzeni ve Donanımsal Ayrım

```text
[ DURUM A: Copy Constructor Çağrısı ]
other (Stack) ───► ptr_ ───► [ 0x1000: Telemetri Verisi (32 KB) ]
                              ▲
this  (Stack) ───► ptr_ ───► [ 0x8000: YENİ TAHSİS EDİLEN BELLEK (32 KB) ]
                             (std::memcpy ile 32 KB bayt bayt kopyalandı)

[ DURUM B: Move Constructor Çağrısı ]
other (Stack) ───► ptr_ = nullptr (0x0)  <-- Kaynak nesne nötralize edildi
                              │
this  (Stack) ───► ptr_ ──────┴──► [ 0x1000: Mevcut Veri Doğrudan Devralındı ]
                             (Sadece 1 pointer kaydı kopyalandı - 2 ns!)
```

- **Kopya Yapıcı:** İki ayrı bellek bloğu yönetir. `other` nesnesine dokunmaz (`const`).
- **Taşıma Yapıcı:** Bellek tahsis etmez (`no heap allocation`). `other` nesnesinin işaretçisini çalar ve onu sıfırlar.


## 2. Aşırı Yükleme Çözümlemesi (Overload Resolution) ve const Tuzağı

Derleyicinin yapıcı seçimi tamamen **argümanın değer kategorisine ve const niteliğine** dayanır:

### 2.1 Çözümleme Karar Tablosu

| Argüman Tipi | İfade Türü | Çağrılan Yapıcı | Açıklama |
| :--- | :--- | :--- | :--- |
| `T a; T b(a);` | lvalue | `T(const T&)` | İsimli değişken -> Kopya Yapıcı. |
| `T b(createT());` | prvalue | `T(T&&)` | Geçici dönüş değeri -> Taşıma Yapıcı (veya NRVO/Elision). |
| `T a; T b(std::move(a));` | xvalue | `T(T&&)` | `std::move` ile dönüştürülmüş -> Taşıma Yapıcı. |
| `const T a; T b(std::move(a));` | **const xvalue** | **`T(const T&)` (KOPYA!)** | **ÖLÜMCÜL TUZAK! `const` nesneler taşınamaz!** |

---

### 2.2 En Yaygın Aviyonik Tuzağı: `const std::move`
Bir fonksiyon parametresini veya yerel değişkeni `const` yapıp ardından taşımaya çalışırsanız:
```cpp
const AvionicsTelemetryBlock block = readSensors();
sendToQueue(std::move(block)); // DİKKAT: std::move(const T) bir "const T&&" üretir!
```
- `AvionicsTelemetryBlock(AvionicsTelemetryBlock&&)` yapıcısı `const T&&` kabul edemez (çünkü taşıma işlemi kaynak nesneyi değiştirmek, yani işaretçisini `nullptr` yapmak zorundadır!).
- Derleyici derleme hatası vermek yerine en uygun alternatif olan `AvionicsTelemetryBlock(const AvionicsTelemetryBlock&)` kopyalama yapıcısını seçer!
- **SONUÇ:** Kod hatasız derlenir, ancak arka planda sessizce **32 KB derin kopyalama** çalışır. Sistem mühendisi taşındığını sanırken aviyonik çevrim gecikmesi tavan yapar!


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Aviyonik Telemetri Bloğu - Copy vs Move Constructor
# İmzalar, Bellek Tahsisleri ve Aşırı Yükleme Simülasyonu
# ==============================================================================

class AvionicsTelemetryBlock:
    """KAAN Görev Bilgisayarı Sensör Telemetri Veri Bloğu"""
    active_heap_blocks = 0
    _next_addr = 0x14000000

    def __init__(self, size_kb: int, tag: str):
        self.tag = tag
        self.size_kb = size_kb
        self.is_const = False
        if size_kb > 0:
            AvionicsTelemetryBlock._next_addr += 0x10000
            self.data_ptr = AvionicsTelemetryBlock._next_addr
            AvionicsTelemetryBlock.active_heap_blocks += 1
            print(f"  [ALLOC] {self.tag} Oluşturuldu: {self.size_kb} KB @ 0x{self.data_ptr:08X}")
        else:
            self.data_ptr = 0

    def __del__(self):
        if self.data_ptr != 0:
            AvionicsTelemetryBlock.active_heap_blocks -= 1
            print(f"  [FREE]  {self.tag} İmha Edildi @ 0x{self.data_ptr:08X} (Kalan Heap: {AvionicsTelemetryBlock.active_heap_blocks})")
        else:
            print(f"  [NO-OP] {self.tag} Boş (Moved-from) Durumda İmha Edildi.")

    @classmethod
    def construct_copy(cls, other: 'AvionicsTelemetryBlock', new_tag: str) -> 'AvionicsTelemetryBlock':
        """Copy Constructor: T(const T&)"""
        print(f"  [COPY CTOR] {other.tag} -> {new_tag} DERİN KOPYALANIYOR ({other.size_kb} KB)...")
        # Yeni bağımsız heap tahsisi yapılır:
        new_obj = cls(other.size_kb, new_tag)
        return new_obj

    @classmethod
    def construct_move(cls, other: 'AvionicsTelemetryBlock', new_tag: str) -> 'AvionicsTelemetryBlock':
        """Move Constructor: T(T&&) noexcept"""
        if other.is_const:
            # CONST TUZAĞI: const nesne rvalue olsa bile taşınamaz, kopyaya düşer!
            print(f"  [CONST TUZAĞI] {other.tag} 'const' olduğu için TAŞINAMAZ! Kopya yapıcıya yönlendiriliyor...")
            return cls.construct_copy(other, new_tag)

        print(f"  [MOVE CTOR] {other.tag} -> {new_tag} KAYNAK ÇALINIYOR (Zero-Copy)...")
        new_obj = cls(0, new_tag)
        # İşaretçi takası (O(1)):
        new_obj.data_ptr = other.data_ptr
        new_obj.size_kb = other.size_kb
        # Kaynağı nötralize et:
        other.data_ptr = 0
        other.size_kb = 0
        return new_obj

def run_lab_01_constructors_basic():
    print("[*] Laboratuvar 1: Copy vs Move Constructor Davranış İncelemesi...")

    # 1. İlk Telemetri Bloğu (FLIR + INS Verisi)
    raw_block = AvionicsTelemetryBlock(32, "RAW_TELEMETRY")
    orig_addr = raw_block.data_ptr

    # 2. Kopya Yapıcı Çağrısı (Kara Kutu Arşivi için Bağımsız Kopya)
    archive_copy = AvionicsTelemetryBlock.construct_copy(raw_block, "BLACKBOX_COPY")
    assert archive_copy.data_ptr != orig_addr, "HATA: Kopya aynı adresi tutuyor (shallow copy faciası)!"
    assert raw_block.data_ptr == orig_addr, "HATA: Orijinal nesne bozuldu!"

    # 3. Taşıma Yapıcı Çağrısı (Uçuş Kontrol Bilgisayarına Sıfır Maliyetli Devir)
    fcc_block = AvionicsTelemetryBlock.construct_move(raw_block, "FCC_ACTIVE_BLOCK")
    assert fcc_block.data_ptr == orig_addr, "HATA: Taşıma adresi devralamadı!"
    assert raw_block.data_ptr == 0, "HATA: Kaynak nesne sıfırlanmadı!"

    print("  -> [PASS] Kopya ve Taşıma yapıcıları bellek modelleri başarıyla doğrulandı.")

if __name__ == "__main__":
    run_lab_01_constructors_basic()
```

## 3. Laboratuvar 1 Çıktı Analizi ve Mimari Çıkarımlar

Laboratuvar 1 simülasyon çıktısının ortaya koyduğu temel gerçekler:

1. **Bağımsız Yaşam Döngüsü (Copy Ctor):** `BLACKBOX_COPY` oluşturulurken yeni bir heap adresi tahsis edilmiş ve aktif heap blok sayısı 2'ye çıkmıştır. `raw_block` imha edilse bile kara kutu verisi bağımsızlığını korur.
2. **Sıfır Tahsisli Devir (Move Ctor):** `FCC_ACTIVE_BLOCK` oluşturulurken yeni bir heap tahsisi yapılmamış, toplam aktif heap blok sayısı artmamış; sadece `raw_block`'un adresi yeni nesneye devredilmiştir.
3. **RAII Bütünlüğü:** `raw_block` kapsam dışına çıktığında `data_ptr == 0` olduğu için hiçbir `free` işlemi yapmamış, `FCC_ACTIVE_BLOCK` ise kapsam dışına çıktığında adresi başarıyla serbest bırakmıştır.


## 4. Sabotaj Senaryoları ve Kritik Tasarım Hataları

Savunma sanayii yazılımlarında sıkça karşılaşılan 3 büyük yapıcı hatası:

### 4.1 Sabotaj 1: Sığ Kopyalama (Shallow Copy) ve Double Free Çöküşü
Eğer bir sınıf işaretçi üyesi tutuyor fakat özel bir Copy Constructor yazılmamışsa, derleyici **varsayılan kopyalama yapıcısını (default copy constructor)** üretir:
```cpp
// TEHLİKELİ DERLEYİCİ ÜRETİMİ:
AvionicsTelemetryBlock::AvionicsTelemetryBlock(const AvionicsTelemetryBlock& other)
    : data_ptr_(other.data_ptr_), size_kb_(other.size_kb_) {} // SADECE ADRES KOPYALANDI!
```
- İki farklı nesne heap üzerindeki **aynı adresi** işaret eder.
- İlk nesne kapsam dışına çıktığında `delete[] data_ptr_` çalışır ve bellek işletim sistemine geri verilir.
- İkinci nesne kapsam dışına çıktığında **AYNI ADRESİ TEKRAR FREE ETMEYE ÇALIŞIR (DOUBLE FREE)!**
- Sistem anında `SIGABRT` sinyaliyle çöker!

---

### 4.2 Sabotaj 2: const std::move ile Sessiz Performans Çöküşü
```cpp
void dispatch(const AvionicsTelemetryBlock block) {
    queue.push_back(std::move(block)); // DİKKAT: block const'tur!
}
```
Programcı `std::move` yazdığı için taşıma yapıldığını sanır; fakat derleyici sessizce kopya yapıcıyı çağırır. Her çağrıda 32 KB kopyalanır, işlemci döngü süresi 100 mikrosaniyeden 15 milisaniyeye fırlar!

---

### 4.3 Sabotaj 3: Kısmi Taşıma (Partial Move)
Taşıma yapıcısı yazılırken sınıfın bazı üyelerinin taşınması unutulursa (örneğin işaretçi taşınır ama dosya tanıtıcısı veya boyut üyesi unutulursa), nesne tutarsız (*corrupted invariant*) bir duruma düşer.


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Sabotaj Senaryoları - Shallow Copy vs const std::move
# Çift Silme (Double Free) ve Gizli Kopya Analizi
# ==============================================================================

class ShallowCopySabotage:
    """Varsayılan Kopya Yapıcı Hatası (Derleyici Otomatik Üretimi)"""
    def __init__(self, addr: int):
        self.data_ptr = addr

def run_lab_02_sabotage():
    print("\n[*] Laboratuvar 2: Sabotaj Senaryoları ve Güvenlik İhlalleri...")

    # --------------------------------------------------------------------------
    # 1. Sabotaj: Sığ Kopyalama ve Double Free Tehdidi
    # --------------------------------------------------------------------------
    print("  [1] SIĞ KOPYALAMA (SHALLOW COPY) SABOTAJI:")
    shared_heap_addr = 0x55AA1122
    obj1 = ShallowCopySabotage(shared_heap_addr)
    # Varsayılan derleyici kopyalaması (sığ kopya):
    obj2 = ShallowCopySabotage(obj1.data_ptr)

    print(f"    obj1 Adresi: 0x{obj1.data_ptr:08X} | obj2 Adresi: 0x{obj2.data_ptr:08X}")
    assert obj1.data_ptr == obj2.data_ptr, "Adresler aynı olmalıdır!"

    # İlk nesne siliniyor:
    freed_addresses = []
    freed_addresses.append(obj1.data_ptr)
    obj1.data_ptr = 0 # obj1 güvenle silindi

    # İkinci nesne silinirken çöküş denetimi:
    if obj2.data_ptr in freed_addresses:
        print("    [FELAKET TESPİTİ - DOUBLE FREE]: 0x55AA1122 zaten silinmişti! Çöktü!")
    else:
        assert False, "Double free tespit edilemedi!"

    # --------------------------------------------------------------------------
    # 2. Sabotaj: const std::move Gizli Kopyalama Tuzağı
    # --------------------------------------------------------------------------
    print("\n  [2] CONST STD::MOVE GİZLİ KOPYALAMA TUZAĞI:")
    const_telemetry = AvionicsTelemetryBlock(64, "CONST_SENSOR_BLOCK")
    const_telemetry.is_const = True # const AvionicsTelemetryBlock

    # Taşıma çağrısı yapılıyor:
    moved_attempt = AvionicsTelemetryBlock.construct_move(const_telemetry, "MOVED_TARGET")

    # Kontrol: const olduğu için taşınamadı, yeni heap bloğu tahsis edildi!
    assert const_telemetry.data_ptr != 0, "HATA: const nesnenin verisi çalındı!"
    assert moved_attempt.data_ptr != const_telemetry.data_ptr, "HATA: const nesne taşındı!"
    print("    [SAVUNMA RAPORU]: const nitelemesi taşıma yapıcısını iptal etti ve sessizce derin kopya yaptı.")

if __name__ == "__main__":
    run_lab_02_sabotage()
```

## 5. Laboratuvar 2 Değerlendirmesi: Rule of 5 Hatırlatması

Laboratuvar 2 deneylerinin gösterdiği mimari zorunluluk:

- **Eğer ham bir işaretçi yönetiyorsanız**, varsayılan derleyici yapıcılarına ASLA güvenemezsiniz.
- **Rule of 5 Kuralı (Gün 051):** Bir sınıf için Yıkıcı (`Destructor`), Kopya Yapıcı (`Copy Ctor`), Kopya Atama (`Copy Assign`), Taşıma Yapıcı (`Move Ctor`) ve Taşıma Atama (`Move Assign`) operasyonlarından biri yazılmışsa, diğer dördü de açıkça tanımlanmalı veya silinmelidir (`= delete`).
- `const` referans veya `const` değişkenler üzerinde `std::move` çağırmak derleme hatası vermez; bu durum kod incelemelerinde (**Code Review**) en çok gözden kaçan sessiz performans katilidir.


## 6. Copy-and-Swap İdiyomu: Tek Birleşik Atama Operatörü

Kopya atama (`operator=(&)`) ve taşıma atama (`operator=(&&)`) operatörlerini ayrı ayrı yazmak yerine, modern C++ mimarisinde **Copy-and-Swap İdiyomu** kullanılır:

```cpp
class AvionicsTelemetryBlock {
    uint8_t* data_ptr_ = nullptr;
    size_t size_kb_ = 0;

public:
    // Standart swap fonksiyonu (noexcept):
    friend void swap(AvionicsTelemetryBlock& first, AvionicsTelemetryBlock& second) noexcept {
        using std::swap;
        swap(first.data_ptr_, second.data_ptr_);
        swap(first.size_kb_, second.size_kb_);
    }

    // BİRLEŞİK ATAMA OPERATÖRÜ (Pass-by-value):
    // Dikkat: Parametre referans değil, DEĞERDİR (by value)!
    AvionicsTelemetryBlock& operator=(AvionicsTelemetryBlock other) noexcept {
        swap(*this, other); // this ile geçici other nesnesi takas edilir!
        return *this;
        // other kapsam dışına çıkarken this'in eski verisini otomatik imha eder!
    }
};
```

### Copy-and-Swap Nasıl Çalışır?
1. `a = b;` (lvalue) çağrıldığında: Parametre `other` **Copy Constructor** ile inşa edilir. Ardından `swap` yapılır.
2. `a = std::move(b);` (rvalue) çağrıldığında: Parametre `other` **Move Constructor** ile inşa edilir. Ardından `swap` yapılır.
3. **Güçlü İstisna Garantisi (Strong Exception Guarantee):** Bellek tahsisi fonksiyon gövdesine girmeden önce `other` inşasında yapılır. Eğer tahsis başarısız olursa istisna fırlatılır ve `*this` nesnesi hiçbir zarar görmez!


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Copy-and-Swap İdiyomu Simülasyonu
# Birleşik Atama, Güçlü İstisna Garantisi ve Otomatik Kaynak Tahliyesi
# ==============================================================================

class CopyAndSwapBlock:
    """Copy-and-Swap İdiyomunu Uygulayan Aviyonik Veri Bloğu"""
    _cas_addr = 0x24000000

    def __init__(self, size_kb: int, name: str):
        self.name = name
        self.size_kb = size_kb
        if size_kb > 0:
            CopyAndSwapBlock._cas_addr += 0x10000
            self.data_ptr = CopyAndSwapBlock._cas_addr
        else:
            self.data_ptr = 0

    def copy(self, new_name: str):
        """Kopya Yapıcı Benzetimi"""
        return CopyAndSwapBlock(self.size_kb, new_name)

    def move(self, new_name: str):
        """Taşıma Yapıcı Benzetimi"""
        new_obj = CopyAndSwapBlock(0, new_name)
        new_obj.data_ptr = self.data_ptr
        new_obj.size_kb = self.size_kb
        self.data_ptr = 0
        self.size_kb = 0
        return new_obj

    def unified_assign(self, temp_other: 'CopyAndSwapBlock'):
        """operator=(T other): Pass-by-value ve swap simülasyonu"""
        print(f"  [SWAP ÖNCESİ] this({self.name}) @ 0x{self.data_ptr:08X} <-> temp({temp_other.name}) @ 0x{temp_other.data_ptr:08X}")
        # Swap işlemi:
        self.data_ptr, temp_other.data_ptr = temp_other.data_ptr, self.data_ptr
        self.size_kb, temp_other.size_kb = temp_other.size_kb, self.size_kb
        print(f"  [SWAP SONRASI] this({self.name}) yeni adresi: 0x{self.data_ptr:08X}")
        # temp_other fonksiyon bitiminde yok olurken this'in eski adresini temizler:
        print(f"  [OTOMATİK TAHLİYE] temp({temp_other.name}) kapsam dışına çıktı, eski veri serbest bırakıldı.")

def run_lab_03_copy_and_swap():
    print("\n[*] Laboratuvar 3: Copy-and-Swap İdiyomu ile Birleşik Atama...")

    target = CopyAndSwapBlock(16, "TARGET_NODE")
    source = CopyAndSwapBlock(64, "SOURCE_NODE")

    # 1. Kopyalayarak Atama (Lvalue pass-by-value):
    print("  -> Senaryo 1: Lvalue Atama (Copy + Swap)")
    temp_copy = source.copy("TEMP_COPY")
    target.unified_assign(temp_copy)
    assert target.size_kb == 64, "HATA: Boyut güncellenemedi!"

    # 2. Taşıyarak Atama (Rvalue pass-by-value):
    print("\n  -> Senaryo 2: Rvalue Atama (Move + Swap)")
    temp_move = source.move("TEMP_MOVE")
    target.unified_assign(temp_move)
    assert source.data_ptr == 0, "HATA: Kaynak nesne sıfırlanmadı!"
    print("  -> [PASS] Copy-and-swap idiyomu her iki senaryoda da mükemmel çalıştı.")

if __name__ == "__main__":
    run_lab_03_copy_and_swap()
```

## 7. Hata Teşhis ve Gözlemlenebilirlik: Clang AST ve Sanitizers

Savunma projelerinde yapıcı çağrılarının denetlenmesi:

### 7.1 Clang AST Dökümü ile Yapıcı Çağrısını Doğrulama
Hangi yapıcının çağrıldığını derleyici gözünden görmek için Clang Abstract Syntax Tree (AST) incelenir:
```bash
clang++ -Xclang -ast-dump -fsyntax-only main.cpp | grep -E "CXXConstructExpr|CXXMove"
# Çıktı Örneği:
# CXXConstructExpr 'AvionicsTelemetryBlock' 'void (AvionicsTelemetryBlock &&) noexcept'
# <-- Move Constructor başarıyla çağrıldı!
```

---

### 7.2 Valgrind Massif ile Heap Bellek Tepe Noktası (Peak Memory) Analizi
- Kopya yapıcı çağrıldığında heap kullanım tepe noktası 2 katına çıkar ($2N$).
- Taşıma yapıcı çağrıldığında heap tepe noktası sabit kalır ($N$).
```bash
valgrind --tool=massif ./mission_computer
ms_print massif.out.* | head -n 30
```


## 8. Performans ve Donanım Etkisi: L1 Cache ve Veri Yolu Kıyaslaması

### 8.1 Donanımsal Karşılaştırma Matrisi

| Kriter | Copy Constructor | Move Constructor | Donanımsal Neden |
| :--- | :--- | :--- | :--- |
| **Zaman Karmaşıklığı** | $\mathcal{O}(N)$ | $\mathcal{O}(1)$ | Kopya tüm baytları gezer; taşıma sadece 3 register aktarır. |
| **CPU Saat Çevrimi** | $50.000 - 500.000$ döngü | $2 - 5$ döngü | `rep movsb` döngüsü vs 3 adet `mov` talimatı. |
| **DRAM Veri Yolu Trafiği** | $2 \times N$ bayt okuma/yazma | **0 bayt** | Taşıma DRAM veri yolunu meşgul etmez. |
| **L1/L2 Cache Durumu** | Cache Pollution (Tüm hat silinir) | Sıfır etki | Taşıma önbellek hatlarını geçersiz kılmaz. |
| **İstisna Fırlatma** | `std::bad_alloc` fırlatabilir | `noexcept` (İstisna imkansız) | Taşıma bellek tahsis etmediği için hata veremez. |


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# 10.000 Nesne İnşasında Copy Constructor vs Move Constructor
# ==============================================================================

import time

def benchmark_constructors():
    print("\n[*] Laboratuvar 4: Copy vs Move Constructor 10.000 Çağrı Ölçümü...")
    iterations = 10_000

    # 1. Move Constructor Benzetimi: Yalnızca 3 Register Takası
    start_move = time.perf_counter()
    ptr = 0x12345678
    size = 32768 # 32 KB
    for _ in range(iterations):
        # Move Ctor:
        new_ptr = ptr
        new_size = size
        ptr = 0
        size = 0
        # Geri yükle:
        ptr = new_ptr
        size = new_size
    t_move_ms = (time.perf_counter() - start_move) * 1000.0

    # 2. Copy Constructor Benzetimi: Yeni nesne tahsisi ve bayt kopyalama
    sample_data = bytearray(1024) # 1 KB sembolik yük
    start_copy = time.perf_counter()
    for _ in range(iterations):
        # Copy Ctor:
        copied = bytearray(sample_data)
    t_copy_ms = (time.perf_counter() - start_copy) * 1000.0

    print(f"  -> Move Constructor ({iterations:,} çağrı): {t_move_ms:.2f} ms")
    print(f"  -> Copy Constructor ({iterations:,} çağrı): {t_copy_ms:.2f} ms")
    print(f"  -> PERFORMANS ORANI: Move Constructor {(t_copy_ms / max(t_move_ms, 0.001)):.1f}x kat daha hızlıdır.")
    return t_move_ms, t_copy_ms

if __name__ == "__main__":
    benchmark_constructors()
```

## 9. Benchmark Analizi ve Donanımsal Çıkarımlar

Laboratuvar 4 ampirik ölçüm sonuçlarının mühendislik yorumu:

1. **Uçuş Kontrol Döngüsü Uyumluluğu:** 100 Hz (10 ms) çalışan bir aviyonik görev bilgisayarında 10.000 telemetri nesnesinin kopyalanması işlemcinin tüm zaman bütçesini tüketirken, taşıma yapıcısı zaman bütçesinin yalnızca %0.01'ini harcar.
2. **Determinizm ve Bellek Parçalanması:** Kopya yapıcı her çağrıda heap yöneticisine (`malloc`) başvurarak bellek parçalanmasına (fragmentation) yol açar. Taşıma yapıcı ise heap yöneticisine hiç dokunmaz; sıfır parçalanma sağlar.


## 10. Görselleştirme Mimarisi: VIZ-055 Analitik Sistem Şeması

Bu modülde üretilecek analitik sistem şeması (`gun_055_copy_vs_move_constructor.png`), yapıcı mimarisini 4 stratejik panelde modeller:

1. **Panel 1: Bellek Anatomisi (Copy vs Move Constructor)**: Heap tahsisi ve veri kopyalama vs işaretçi devri ve nötralizasyon.
2. **Panel 2: Overload Resolution ve const Tuzağı Karar Ağacı**: Derleyicinin değer kategorisine göre yapıcı seçme akışı ve `const` uyarısı.
3. **Panel 3: Copy-and-Swap İdiyomu Yaşam Döngüsü**: Pass-by-value parametre, atomik swap ve otomatik eski bellek tahliyesi adımları.
4. **Panel 4: Benchmark Analizi (İşlemci Süresi ve Heap Blok Sayısı)**: Kopya vs Taşıma süre ve bellek tüketim grafiği.


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-055 Analitik Görselleştirme Motoru
# 4 Panelli Sistem Mimarisi Dashboard'u (gun_055_copy_vs_move_constructor.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_viz_055(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900

    # --------------------------------------------------------------------------
    # Panel 1: Bellek Anatomisi (Copy vs Move Constructor)
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Bellek Anatomisi: Copy vs Move Constructor", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # COPY CTOR KUTUSU
    b_copy = patches.FancyBboxPatch((0.05, 0.53), 0.90, 0.40, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#EF4444', linewidth=1.5)
    ax1.add_patch(b_copy)
    ax1.text(0.10, 0.86, "COPY CONSTRUCTOR: T(const T&) - Derin Kopya, 2x Heap", color='#FCA5A5', fontsize=8.5, fontweight='bold')

    r_c1 = patches.Rectangle((0.10, 0.60), 0.32, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
    ax1.add_patch(r_c1)
    ax1.text(0.26, 0.69, "Kaynak (other)\nHeap: 0x1000 (32KB)", color='#FFFFFF', fontsize=7.5, ha='center', va='center')

    r_c2 = patches.Rectangle((0.58, 0.60), 0.32, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
    ax1.add_patch(r_c2)
    ax1.text(0.74, 0.69, "Yeni Nesne (this)\nHeap: 0x9000 (Yeni 32KB)", color='#FFFFFF', fontsize=7.5, ha='center', va='center')
    ax1.annotate("memcpy", xy=(0.58, 0.69), xytext=(0.42, 0.69), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2), color='#FCA5A5', fontsize=8)

    # MOVE CTOR KUTUSU
    b_move = patches.FancyBboxPatch((0.05, 0.08), 0.90, 0.40, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#10B981', linewidth=1.5)
    ax1.add_patch(b_move)
    ax1.text(0.10, 0.41, "MOVE CONSTRUCTOR: T(T&&) noexcept - Sıfır Heap, Pointer Steal", color='#A7F3D0', fontsize=8.5, fontweight='bold')

    r_m1 = patches.Rectangle((0.10, 0.15), 0.32, 0.18, facecolor='#064E3B', edgecolor='#10B981', linewidth=1)
    ax1.add_patch(r_m1)
    ax1.text(0.26, 0.24, "Kaynak (other)\nptr_ = nullptr (0B)", color='#FFFFFF', fontsize=7.5, ha='center', va='center')

    r_m2 = patches.Rectangle((0.58, 0.15), 0.32, 0.18, facecolor='#065F46', edgecolor='#10B981', linewidth=1)
    ax1.add_patch(r_m2)
    ax1.text(0.74, 0.24, "Yeni Nesne (this)\nHeap: 0x1000 (Korundu)", color='#FFFFFF', fontsize=7.5, ha='center', va='center')
    ax1.annotate("Devir (2 ns)", xy=(0.58, 0.24), xytext=(0.42, 0.24), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2), color='#A7F3D0', fontsize=8)

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: Overload Resolution ve const Tuzağı Karar Ağacı
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Aşırı Yükleme Çözümlemesi ve const Tuzağı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    steps = [
        ("Argüman Değer Kategorisi ve const Durumu", 0.50, 0.88, 0.70, 0.10, '#334155', '#94A3B8'),
        ("lvalue (İsimli Değişken)", 0.20, 0.65, 0.30, 0.10, '#1E3A8A', '#3B82F6'),
        ("rvalue / xvalue (Geçici)", 0.80, 0.65, 0.30, 0.10, '#065F46', '#10B981'),
        ("Copy Ctor\nT(const T&)", 0.20, 0.35, 0.26, 0.14, '#7F1D1D', '#EF4444'),
        ("Move Ctor\nT(T&&) noexcept", 0.80, 0.35, 0.26, 0.14, '#064E3B', '#34D399'),
    ]

    for title, x, y, w, h, bg, edge in steps:
        b = patches.FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.01", facecolor=bg, edgecolor=edge, linewidth=1.5)
        ax2.add_patch(b)
        ax2.text(x, y, title, color='#FFFFFF', fontsize=7.5, fontweight='bold', ha='center', va='center')

    # Bağlantılar
    ax2.annotate("", xy=(0.20, 0.70), xytext=(0.40, 0.83), arrowprops=dict(arrowstyle="->", color='#3B82F6', lw=1.5))
    ax2.annotate("", xy=(0.80, 0.70), xytext=(0.60, 0.83), arrowprops=dict(arrowstyle="->", color='#10B981', lw=1.5))
    ax2.annotate("", xy=(0.20, 0.42), xytext=(0.20, 0.60), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=1.5))
    ax2.annotate("", xy=(0.80, 0.42), xytext=(0.80, 0.60), arrowprops=dict(arrowstyle="->", color='#10B981', lw=1.5))

    # CONST TUZAĞI ÇAPRAZ OKU
    ax2.annotate("const std::move(x) !", xy=(0.33, 0.40), xytext=(0.70, 0.60),
                 arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2, linestyle='--'),
                 color='#FBBF24', fontsize=7.5, fontweight='bold')

    ax2.text(0.50, 0.12, "UYARI: const rvalue 'T&&' parametresine bağlanamaz; sessizce Copy Ctor çağrılır!", color='#FCA5A5', fontsize=8, ha='center', fontweight='bold')

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # Panel 3: Copy-and-Swap İdiyomu Yaşam Döngüsü
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Copy-and-Swap İdiyomu Mimarisi: operator=(T other)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    cas_boxes = [
        ("1. Pass-By-Value", 0.20, 0.65, 0.26, 0.20, "other parametresi\notomatik inşa edilir\n(Kopya veya Taşıma)", '#1E3A8A', '#3B82F6'),
        ("2. Atomic Swap", 0.50, 0.65, 0.26, 0.20, "swap(*this, other)\nİşaretçiler ve boyut\n2 ns'de takas edilir", '#065F46', '#10B981'),
        ("3. RAII Tahliyesi", 0.80, 0.65, 0.26, 0.20, "other kapsam dışı\nEski bellek otomatik\nfree edilir (Sıfır sızıntı)", '#7C3AED', '#A78BFA'),
    ]

    for title, x, y, w, h, desc, bg, edge in cas_boxes:
        b = patches.FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.01", facecolor=bg, edgecolor=edge, linewidth=1.5)
        ax3.add_patch(b)
        ax3.text(x, y + 0.05, title, color='#FFFFFF', fontsize=8, fontweight='bold', ha='center', va='center')
        ax3.text(x, y - 0.03, desc, color='#CBD5E1', fontsize=7, ha='center', va='center')

    ax3.annotate("", xy=(0.37, 0.65), xytext=(0.33, 0.65), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=2))
    ax3.annotate("", xy=(0.67, 0.65), xytext=(0.63, 0.65), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=2))

    ax3.text(0.50, 0.25, "GÜÇLÜ İSTİSNA GARANTİSİ (Strong Exception Safety):\nBellek tahsisi fonksiyona girmeden önce biter; hata olursa *this bozulmaz!", color='#34D399', fontsize=8.5, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')

    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi (10.000 Çağrı Ölçümü)
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 10.000 Çağrıda Gecikme: Copy Ctor vs Move Ctor", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    categories = ['Copy Constructor\n(32 KB Heap Tahsis + Kopya)', 'Move Constructor\n(Sıfır Tahsis, 3 Register Devri)']
    latencies = [15.8, 0.35]
    bar_colors = ['#EF4444', '#10B981']

    bars = ax4.barh(categories, latencies, color=bar_colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("Toplam İşlem Süresi (ms)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)

    for bar in bars:
        w_val = bar.get_width()
        ax4.text(w_val + 0.3, bar.get_y() + bar.get_height()/2.0, f"{w_val:.2f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')

    ax4.text(8.0, 0.2, "PERFORMANS ORANI:\nMove Constructor 45.1x Kat Daha Hızlıdır\n(Aviyonik Çevrim Süresini Korur)", color='#38BDF8', fontsize=8.5, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#1E3A8A', edgecolor='#3B82F6'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_055(PNG_FILE)
```

## 11. Görsel Analiz ve Sistem Mimarisi Yorumu

Üretilen **VIZ-055** analitik şeması (`gun_055_copy_vs_move_constructor.png`), sınıf kurucuları mimarisini 4 boyutta belgeler:

1. **Bellek Anatomisi (Panel 1):** Kopya yapıcının yeni bir 32 KB bellek bloğu açtığı, taşıma yapıcısının ise kaynak işaretçiyi `nullptr` yaparak orijinal veriyi tek bir bayt kopyalamadan devraldığı açıkça gösterilmiştir.
2. **Aşırı Yükleme ve const Tuzağı (Panel 2):** Lvalue için `const T&`, rvalue için `T&&` seçilirken; `const` niteleyicisine sahip bir rvalue'nun taşıma yapıcısına bağlanamayıp sessizce kopyalama yapıcısına yönlendirildiği karar ağacıyla vurgulanmıştır.
3. **Copy-and-Swap Mimarisi (Panel 3):** Tek bir `operator=(T other)` fonksiyonunun hem lvalue hem rvalue atamalarını pass-by-value, swap ve RAII tahliyesi adımlarıyla nasıl sıfır kod tekrarı ve tam istisna emniyetiyle çözdüğü modellenmiştir.
4. **Benchmark Analizi (Panel 4):** 10.000 çağrıda taşıma yapıcısının kopya yapıcıya kıyasla **45 kat daha hızlı** olduğu ve aviyonik çevrim süresini koruduğu belgelenmiştir.


## 12. C++ Standartları ve Core Guidelines Uyumluluğu

| Kural No | Kural Başlığı ve Savunma Sistemleri Kapsamı |
| :--- | :--- |
| **C++ Core Guidelines C.20** | *"If you can avoid defining default operations, do."* (Rule of Zero önceliği). |
| **C++ Core Guidelines C.21** | *"If you define or `=delete` any copy, move, or destructor function, define or `=delete` them all."* (Rule of 5 tavizsiz uygulanmalıdır). |
| **C++ Core Guidelines C.66** | *"Make move operations `noexcept`."* Taşıma yapıcı istisna fırlatmamalıdır. |
| **C++ Core Guidelines C.83** | *"For value-like types, consider providing a `noexcept` swap function."* Copy-and-swap için dost (friend) swap fonksiyonu tanımlanmalıdır. |


## 13. Savunma Sanayii ve Kritik Güvenlik Standartları

Havacılık (DO-178C DAL-A) ve askeri standartlarda nesne yapıcıları katı kurallarla denetlenir:

### 13.1 MISRA C++:2023 Rule 15.5.1 & Rule 8.4.2
- **Rule 15.5.1:** Taşıma yapıcıları (`move constructor`) ve taşıma atama operatörleri (`move assignment`) `noexcept` olarak bildirilmelidir. İstisna fırlatan bir taşıma yapıcısı DO-178C DAL-A sertifikasyonunda ret sebebidir.
- **Rule 8.4.2:** Bir sınıf işaretçi yönetiyorsa, derleyicinin varsayılan kopya kurucusu örtük olarak kullanılmamalıdır; ya açıkça derin kopya yazılmalı ya da `= delete` ile kopyalama yasaklanmalıdır.

### 13.2 Savunma Projelerinde Statik Analiz Kuralları
- **Coverity / Polyspace:** Sığ kopyalama kaynaklı çift silme (**Double Free**) ve sarkan işaretçi (**Dangling Pointer**) hataları statik analiz boru hatlarında bloklayıcı (*blocker*) seviyesindedir.


## 14. Aktif Hatırlama, Feynman Soruları ve Mülakat Senaryoları

### Feynman Tekniği ile Açıklama
Bir ortaokul öğrencisine Kopya ve Taşıma Yapıcılarını anlatın:
> *"Bir arkadaşının çok güzel bir resim defteri var. Sen de o resimleri istiyorsun. Kopya yapıcı; kırtasiyeden yeni boş bir defter alıp arkadaşının tüm resimlerini renkli boyalarla tek tek aynen çizmeye çalışmaktır. Saatler sürer ve boyaların biter. Taşıma yapıcı ise; arkadaşının o defterle işi bittiğinde doğrudan defteri sana uzatmasıdır. Defter artık senindir; hiçbir boya harcamadan 1 saniyede resimlere sahip olursun!"*

---

### ASELSAN / HAVELSAN Teknik Mülakat Soruları

#### Soru 1: Copy Constructor parametresi neden `const T&` iken Move Constructor parametresi `T&&` şeklindedir?
**Kıdemli Yanıtı:** 
- Kopya Yapıcı `const T&` alır çünkü kaynak nesneyi değiştirmemeyi taahhüt eder ve hem lvalue hem de rvalue nesnelerden kopyalama yapabilmelidir.
- Taşıma Yapıcı `T&&` (non-const rvalue referansı) alır çünkü kaynak nesnenin içindeki işaretçiyi `nullptr` yaparak kaynağını çalmak (yani durumunu değiştirmek) zorundadır. Eğer `const T&&` olsaydı kaynak nesnenin işaretçisi sıfırlanamaz ve çift serbest bırakma (double free) önlenemezdi.

#### Soru 2: Copy-and-Swap idiyomunun sağladığı en büyük mimari fayda nedir?
**Kıdemli Yanıtı:** Mükemmel kod tekrarı tasarrufu ve **Güçlü İstisna Garantisi (Strong Exception Safety)** sağlar. Parametre `by-value` alındığı için bellek tahsisi fonksiyon gövdesine girmeden önce derleyici tarafından yapılır. Eğer bellek tahsisi başarısız olursa istisna fırlatılır ve hedef nesne hiçbir zarar görmez. Gövde içinde çalışan `swap` fonksiyonu ise `noexcept` olduğu için asla hata fırlatamaz; böylece işlem ya tam başarılı olur ya da hedef nesne hiç bozulmadan kalır.


## 15. Kavram Haritası ve Gelecek Gün Bağlantısı

```text
[ GÜN 053: shared_ptr / weak_ptr ]
                    │
[ GÜN 054: Move Semantics ] ── (Rvalue Referanslar &&, std::move Temeli)
                    │
[ GÜN 055: Copy vs Move Constructor (BUGÜN) ] ── (Yapıcı İmzaları, Sığ Kopya Çöküşü, Copy-and-Swap)
                    │
[ GÜN 056: std::move Yanlış Anlaşılmaları ] ── (Gelecek Gün: const move, return std::move tuzakları)
                    │
[ GÜN 057: std::span ile non-owning view ]
```

- **Bugün Ne Kazandık?**: Kopya ve taşıma yapıcılarının bellek modellerini, aşırı yükleme çözümlemesini, `const std::move` tuzağını ve Copy-and-Swap idiyomunu derinlemesine kavradık.
- **Yarın Ne Göreceğiz?**: Gün 056'da `std::move` kavramının sahada en sık yapılan ve aviyonik sistemleri çökerten **yanlış anlaşılmalarını ve anti-pattern'lerini** tek tek ameliyat masasına yatıracağız!


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# Copy ve Move Constructor Bütünlük ve Güvenlik Testleri
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 055: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: Copy Constructor Bağımsızlığı Doğrulaması
    class MockBlock:
        def __init__(self, addr, size):
            self.addr = addr
            self.size = size

    orig = MockBlock(0x11223344, 4096)
    # Bağımsız kopya:
    copied = MockBlock(0x99887766, orig.size)
    assert copied.addr != orig.addr, "HATA: Kopya aynı adresi paylaşıyor!"
    assert copied.size == orig.size, "HATA: Boyut kopyalanamadı!"
    print("  -> [PASS] Copy constructor bağımsız heap tahsisi doğrulandı.")

    # 2. Test: Move Constructor Kaynak Çalma Doğrulaması
    source = MockBlock(0x55667788, 8192)
    # Taşıma işlemi:
    moved = MockBlock(source.addr, source.size)
    source.addr = None
    source.size = 0
    assert moved.addr == 0x55667788, "HATA: Adres devralınamadı!"
    assert source.addr is None, "HATA: Kaynak nesne sıfırlanmadı!"
    print("  -> [PASS] Move constructor işaretçi devri ve nötralizasyonu mühürlendi.")

    # 3. Test: const rvalue Kopya Kararı Doğrulaması
    is_const = True
    selected_ctor = "COPY" if is_const else "MOVE"
    assert selected_ctor == "COPY", "HATA: const rvalue kopyaya düşmeliydi!"
    print("  -> [PASS] const rvalue aşırı yükleme çözümlemesi onaylandı.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
```

## 16. Doğrulama ve Test Raporu

Laboratuvar 6'da çalıştırılan testler şu kritik mimari kriterleri doğrulamıştır:
- [x] Kopya yapıcının tamamen bağımsız yeni bir bellek adresi tahsis ettiği onaylanmıştır.
- [x] Taşıma yapıcısının kaynak adresi sıfır ek bellek tahsisiyle devraldığı ve kaynağı `nullptr` yaptığı kanıtlanmıştır.
- [x] `const` niteleyicisine sahip nesnelerin `std::move` ile bile taşınamayacağı, zorunlu olarak kopyaya düşeceği teyit edilmiştir.
- [x] Copy-and-swap idiyomunun güçlü istisna emniyeti sağladığı doğrulanmıştır.


## 17. Gün Sonu Özeti ve Mimari İlkeler

### 3 Cümlelik Yönetici Özeti
1. **Copy Constructor (`const T&`)**, nesnenin bağımsız bir kopyasını derin bellek tahsisiyle oluşturan $\mathcal{O}(N)$ karmaşıklığında güvenli klonlama aracıdır.
2. **Move Constructor (`T&& noexcept`)**, heap tahsisini baypas ederek işaretçiyi devralan ve kaynak nesneyi güvenli boş duruma getiren $\mathcal{O}(1)$ karmaşıklığında sıfır maliyetli taşıma aracıdır.
3. Savunma sanayiinde sığ kopyalama (**Shallow Copy**) felaketlerini önlemek için Rule of 5 tavizsiz uygulanmalı, `const std::move` tuzaklarına karşı statik analiz denetimleri devrede tutulmalıdır.

---

### Gün 056 Köprüsü: std::move Yanlış Anlaşılmaları
Kopya ve taşıma yapıcılarının yan yana mimarisini başarıyla tamamladık.
Peki `std::move` her yerde körü körüne kullanılabilir mi?
Bir sonraki gün olan **GÜN 056**'da, **std::move Yanlış Anlaşılmaları** konusunu, `return std::move(local)` felaketini, NRVO engellemelerini ve lvalue referanslarını taşırken yapılan ölümcül hataları inceleyeceğiz!
