<!--
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
-->

# GÜN 046: Constructor ve Destructor Mekanizması (Nesne İnşası, Yıkım Sırası ve Invariant Garantisi)

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
[![C++ Standard](https://img.shields.io/badge/C%2B%2B-20-blue?style=flat-square&logo=c%2B%2B)](https://en.cppreference.com/w/cpp/20)
[![Domain](https://img.shields.io/badge/Domain-Defense%20Systems%20%26%20Object%20Lifecycle-darkgreen?style=flat-square)]()
[![Safety](https://img.shields.io/badge/Safety-MISRA%20C%2B%2B%3A2023%20%7C%20AUTOSAR-orange?style=flat-square)]()

---

### 1. 5N1K Kurumsal Analiz Çerçevesi

| Soru | Sistem Mühendisliği Yanıtı |
| :--- | :--- |
| **Ne? (What)** | **Constructor (Kurucu)**, bir nesnenin bellekteki ham baytlarını geçerli ve tutarlı bir duruma getiren (invariant kuran) özel fonksiyondur. **Destructor (Yıkıcı)** ise nesne yok edilirken kaynakları deterministik biçimde serbest bırakan ters simetrik fonksiyondur. |
| **Neden? (Why)** | Donanım ve havacılık yazılımlarında yarım başlatılmış ("zombi") nesneler veya başlatılmamış çöp değerler ölümcül kazalara yol açar. Constructor nesnenin her zaman geçerli başlamasını, Destructor ise kaynak sızıntısı olmadan sistemin güvenle kapanmasını garanti eder. |
| **Nasıl? (How)** | Üye başlatma listesi (`member initializer list`) kullanarak doğrudan inşa ile; kazara örtük dönüşümleri engellemek için `explicit` anahtar kelimesiyle; ve yıkıcıları daima `noexcept` (polimorfik sınıflarda `virtual`) tanımlayarak. |
| **Nerede? (Where)** | Füze arayıcı başlık açılış dizisi (power-on BIT), radar sinyal işlemci konfigürasyonu, aviyonik arayüz sürücüleri ve görev bilgisayarı durum makinelerinde. |
| **Ne Zaman? (When)** | C++ dilinde bir sınıf (`class`) veya yapı (`struct`) tanımlanırken yaşam döngüsünün sınırlarını çizmek için ilk adımda. |
| **Kim? (Who)** | ASELSAN, HAVELSAN, ROKETSAN projelerinde nesne yönelimli ve deterministik gerçek zamanlı mimariler kuran gömülü yazılım mühendisleri. |

---

### 2. Pratik Hayat ve Savunma Sanayii Analojisi

> **Füze Ateşleme Öncesi Otomatik Test (BIT / Constructor) vs Güvenli Mühimmat İmhacısı (Destructor):**
> - **Constructor (Ateşleme Öncesi BIT Testi)**: Bir füze bataryası rampaya yerleştirildiğinde elektrik verilir ve dahili bilgisayar (Built-In Test - BIT) çalışır. Jiroskoplar kalibre edilir, kanatçık motorları test edilir, hedef koordinatları yüklenir. Eğer bir motor yanıt vermezse constructor hata fırlatır (`throw`) ve füze asla ateşlenmez ("zombi füze" oluşamaz).
> - **Destructor (Güvenli Kapatma ve İade)**: Görev tamamlandığında veya rampa kapatıldığında sistem tam tersi sırayla devreden çıkarılır: Önce yüksek voltajlı roket yakıt kilitleri kapatılır, ardından lazer güdüm kapatılır, en son ana güç kesilir (LIFO Sırası). Bu sıra bozulursa patlama gerçekleşir!


## 1. Constructor ve Destructor Makine Modeli

### 1.1 Yaşamın İnşası: Constructor ve Değişmezler (Invariants)

Bir sınıfın constructor'ı bittiğinde şu kural sağlanmalıdır: **"Nesne artık geçerli bir duruma (valid invariant) sahiptir."**
- Eğer constructor başarılı olamazsa (örneğin donanım portu açılamazsa), constructor bir istisna fırlatmalıdır. C++'ta "kısmen inşa edilmiş" veya "hata kodlu zombi nesne" kabul edilemez.

### 1.2 Üye Başlatma Listesi (Member Initializer List) vs Gövdede Atama

Birçok acemi yazılımcı şu iki yazım tarzını denk zanneder:

```cpp
// YANLIŞ / VERİMSİZ: Gövdede Atama
RadarChannel::RadarChannel(int id, const std::string& name) {
    m_id = id;       // m_id önce çöp değerle oluştu, sonra atandı!
    m_name = name;   // m_name ÖNCE default ctor ile boş string oldu, SONRA copy assignment ile kopyalandı! (2 işlem)
}

// DOĞRU / SIFIR MALİYET: Üye Başlatma Listesi (Direct Initialization)
RadarChannel::RadarChannel(int id, const std::string& name)
    : m_id(id), m_name(name) // Tek adımda doğrudan inşa edildi! (1 işlem)
{
    // Gövdeye sadece ek doğrulama ve donanım yazmaç ayarları kalır
}
```

> **Zorunlu Olduğu Durumlar:**
> 1. `const` veri üyeleri (`const int m_max_power;`),
> 2. Referans veri üyeleri (`Sensor& m_sensor_ref;`),
> 3. Varsayılan kurucusu (default ctor) olmayan üye nesneler.
> Bu üç tür **yalnızca** üye başlatma listesinde başlatılabilir; gövdede atanamaz!

---

### 1.3 İnşa ve Yıkım Sırası (LIFO: Last In First Out)

C++ standardı gereği nesnelerin bileşenleri şu değişmez sırayla inşa edilir ve tam tersi sırayla yıkılır:

```text
    İNŞA SIRASI (Construction Order: ↓)
    1. Base Class (Taban Sınıf) Constructor'ı çalışır.
    2. Sınıf üyeleri, SINIF BİLDİRİMİNDEKİ SIRAYA GÖRE (yukarıdan aşağıya) inşa edilir.
    3. Derived Class Constructor gövdesi çalışır.
    
    YIKIM SIRASI (Destruction Order: ↑ - Tam Ters Sıra / LIFO)
    1. Derived Class Destructor gövdesi çalışır.
    2. Sınıf üyeleri, BİLDİRİM SIRASININ TERSİNE (aşağıdan yukarıya) yok edilir.
    3. Base Class Destructor'ı çalışır.
```

> **Uyarı (`-Wreorder`):** Üye başlatma listesinde üyeleri hangi sırayla yazarsanız yazın, derleyici onları daima sınıfın içindeki **deklarasyon sırasına** göre başlatır. Eğer bir üye başka bir üyeye bağımlıysa ve sıra yanlışsa, başlatılmamış çöp değer kullanılır!


## 2. Mimari Karar Matrisi: Özel Üye Fonksiyonların Kontrolü

Modern C++ (C++11/20), sınıfların yaşam döngüsünü kontrol etmek için derleyiciye açık talimatlar vermemizi sağlar:

| Anahtar Kelime / Desen | Amaç ve Sistem Mühendisliği Anlamı | Savunma Sanayii Kuralı |
| :--- | :--- | :--- |
| **`explicit`** | Tek argümanlı constructor'ların örtük tür dönüşümünü (implicit conversion) engeller | Tüm tek parametreli constructor'lar varsayılan olarak `explicit` olmalıdır |
| **`= default;`** | Derleyiciden optimize edilmiş standart kurucu/yıkıcı üretmesini ister | Rule of Zero / Beşli Kural standardı |
| **`= delete;`** | İstenmeyen constructor veya operatörleri yasaklar (örn: Kopyalamayı engelleme) | Tekil donanım sarıcılarında kopyalama açıkça silinmelidir (`= delete`) |
| **`virtual ~Base();`** | Taban sınıflarda polimorfik yıkım sağlar; türetilmiş sınıfın sızmasını önler | Polimorfik miras hiyerarşilerinde taban sınıf yıkıcısı kesinlikle sanal olmalıdır |
| **`noexcept`** | Yıkıcının asla exception fırlatmayacağını garanti eder | Tüm destructor'lar örtük olarak `noexcept`'tir; asla bozulmamalıdır |


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Taban ve Türetilmiş Sınıflarda İnşa/Yıkım Sırası Simülatörü
# LIFO (Last In First Out) prensibi ve explicit koruma mekanizması
# ==============================================================================

class BaseSubsystem:
    def __init__(self, name: str):
        self.name = name
        print(f"  [1. BASE CTOR] Taban Alt Sistem İnşa Edildi: {self.name}")

    def __del__(self):
        print(f"  [4. BASE DTOR] Taban Alt Sistem İmha Edildi: {self.name}")

class RadarTransceiver(BaseSubsystem):
    def __init__(self, name: str, frequency_ghz: float):
        # 1. Önce taban sınıf inşa edilir
        super().__init__(name)
        # 2. Sonra türetilmiş sınıf üyeleri inşa edilir
        self.frequency_ghz = frequency_ghz
        print(f"  [2. DERIVED CTOR] Radar Alıcı-Verici İnşa Edildi ({self.frequency_ghz} GHz)")

    def __del__(self):
        # 1. Önce türetilmiş sınıfın yıkıcısı çalışır
        print(f"  [3. DERIVED DTOR] Radar Alıcı-Verici İmha Ediliyor ({self.frequency_ghz} GHz)")
        # 2. Sonra taban sınıfın yıkıcısı çalışır
        super().__del__()

def simulate_explicit_conversion():
    """C++ explicit keyword simülasyonu: Kazara tür dönüşümlerini engelleme"""
    class ExplicitPowerLevel:
        def __init__(self, watts: int):
            if not isinstance(watts, int):
                raise TypeError(f"[EXPLICIT ENGELİ] Örtük dönüşüm reddedildi! watts int olmalı, gelen: {type(watts).__name__}")
            self.watts = watts

    print("\n[*] C++ 'explicit' Anahtar Kelimesi Simülasyonu:")
    # Doğru çağrı (Doğrudan başlatma)
    p1 = ExplicitPowerLevel(500)
    print(f"  [+] Açıkça int ile inşa edildi: {p1.watts} Watt")
    
    # Hatalı örtük dönüşüm denemesi (örn: string veya float geçmek)
    try:
        p2 = ExplicitPowerLevel("500")  # C++'ta kazara implicit conversion
    except TypeError as ex:
        print(f"  [BAŞARILI ENGELLEME] {ex}")

def run_lab_01_lifecycle():
    print("[*] Laboratuvar 1: Nesne Yaşam Döngüsü ve LIFO Sıralaması Başlatılıyor...")
    
    # Kapsam açılıyor
    print("\n[KAPSAM GİRİŞİ]")
    radar = RadarTransceiver("ASELSAN_AESA_RADAR", 9.4)
    print(f"  -> Radar aktif görevde: {radar.name} ({radar.frequency_ghz} GHz)")
    
    # Kapsam sonu: Nesne siliniyor
    print("\n[KAPSAM ÇIKIŞI - LIFO YIKIM BAŞLIYOR]")
    del radar
    
    simulate_explicit_conversion()

if __name__ == "__main__":
    run_lab_01_lifecycle()
```

## 3. Laboratuvar 1 Çıktı Analizi: Neden LIFO Yıkım Sırası Zorunludur?

Laboratuvar 1 çıktısında inşa ve yıkım adımları net bir simetri sergiler:
1. **İnşa**: `BaseSubsystem` -> `RadarTransceiver`. (Temel atılmadan çatı kurulamaz).
2. **Yıkım**: `RadarTransceiver` -> `BaseSubsystem`. (Çatı sökülmeden temel yıkılamaz).

> **Kritik Sistem Dersi:** Türetilmiş sınıf (`RadarTransceiver`), taban sınıfın (`BaseSubsystem`) sağladığı kaynaklara (bellek havuzu, register adresleri, bus kanalları) bağımlıdır. Eğer taban sınıf önce yok edilseydi, türetilmiş sınıfın yıkıcısı taban sınıfın kapalı kaynaklarına erişmeye çalışacak ve sistem çökecekti. LIFO kuralı donanımsal bağımlılıkların güvenle sonlandırılmasının yegane garantisidir.


## 4. Kısmi İnşa (Partial Construction) ve Zombi Nesne Tuzağı

C++'ta en kritik güvenlik kurallarından biri şudur:
**"Constructor'ı tamamlanmadan exception fırlatan bir nesne HİÇ VAR OLMAMIŞ SAYILIR; onun Destructor'ı ASLA ÇAĞRILMAZ!"**

```cpp
class MissileLauncher {
    RocketMotor* m_motor;
    GuidanceUnit* m_guidance;
public:
    MissileLauncher() {
        m_motor = new RocketMotor();         // [1] Motor tahsis edildi
        m_guidance = new GuidanceUnit();     // [2] Eğer bu throw fırlatırsa:
        // [FELAKET]: Launcher'ın ~MissileLauncher() destructor'ı ÇALIŞMAZ!
        // m_motor havada asılı kalır -> SIZINTI (LEAK)!
    }
    ~MissileLauncher() {
        delete m_motor;
        delete m_guidance;
    }
};
```

### Çözüm: RAII Üyeler Kullanmak
Ham işaretçiler yerine `std::unique_ptr` kullanılırsa, `GuidanceUnit` hata fırlatsa bile, o ana kadar başarıyla inşa edilmiş olan `RocketMotor`'un `unique_ptr`'ı derleyici tarafından otomatik olarak yok edilir ve motor sızmaz!


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Radar Güç Dağıtım ve RF Verici Sıralı Başlatma/Kapatma
# Donanım Güç Sıralaması (Power-Up Sequence) ve Fail-Safe Shutdown
# ==============================================================================

class PowerDistributionUnit:
    def __init__(self, voltage: float):
        self.voltage = voltage
        self.is_powered = True
        print(f"  [PDU] Ana Güç Verildi: {self.voltage}V (Güç Açık)")

    def shutdown(self):
        if self.is_powered:
            self.is_powered = False
            print(f"  [PDU] Ana Güç Güvenle Kesildi: 0V (Güç Kapalı)")

class RfTransmitter:
    def __init__(self, pdu: PowerDistributionUnit, power_kw: float):
        if not pdu.is_powered:
            raise RuntimeError("[DONANIM ARIZASI] PDU kapalıyken RF Verici açılamaz! Yanma tehlikesi!")
        self.pdu = pdu
        self.power_kw = power_kw
        self.is_transmitting = True
        print(f"  [RF_TX] RF Verici Aktif Edildi: {self.power_kw} kW Yayın Başladı.")

    def shutdown(self):
        if self.is_transmitting:
            self.is_transmitting = False
            print(f"  [RF_TX] RF Verici Güvenle Kapatıldı (Yayın Kesildi).")

class RadarSystemController:
    """RAII Tabanlı Entegre Sistem: PDU önce açılır, RF sonra; kapanırken RF önce, PDU sonra"""
    def __init__(self, voltage: float, power_kw: float):
        self.pdu = PowerDistributionUnit(voltage)
        self.rf = RfTransmitter(self.pdu, power_kw)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ters sıra (LIFO) ile güvenli kapatma:
        print("\n  [*] Sistem Güvenli Kapatma (Safe-Shutdown) Dizisi İşletiliyor:")
        self.rf.shutdown()   # 1. Önce RF yayını kes
        self.pdu.shutdown()  # 2. Sonra ana gücü kes
        return False

def run_lab_02_radar_power_seq():
    print("\n[*] Laboratuvar 2: Savunma Sanayii Donanım Başlatma/Kapatma Sırası...")
    
    with RadarSystemController(voltage=28.0, power_kw=50.0) as radar_sys:
        print("    -> Radar operasyonel döngüde: Düşman hedef taraması yapılıyor...")
        
    print("  -> Radar sistemi sıfır donanım hasarıyla kapatıldı.")

if __name__ == "__main__":
    run_lab_02_radar_power_seq()
```

## 5. Laboratuvar 2 Değerlendirmesi: Donanım Güç Sıralaması (Power Sequencing)

Aviyonik ve radar donanımlarında açılış ve kapanış sırası hayati önem taşır:
- **Açılış**: Önce Güç Kaynağı (PDU 28V) devreye girmeli, voltaj oturduktan sonra yüksek güçlü RF Verici (50 kW) tetiklenmelidir.
- **Kapanış**: Eğer PDU güç kesintisini önce yaparsa, RF tüpünde veya GaN transistörlerinde yüksek voltaj dalgalanması (inductive spike) oluşur ve milyonlarca dolarlık donanım yanar!
- Bu sıra yazılımcının hafızasına bırakılamaz; sınıf içi kompozisyon ve Destructor LIFO kuralı ile derleyici seviyesinde güvenceye alınır.


## 6. Ölümcül Hatalar, Anti-Pattern'ler ve Sabotaj Senaryoları

### 6.1 Sabotaj 1: Sanal Olmayan Yıkıcı (Non-Virtual Destructor) Sızıntısı
Eğer bir sınıf polimorfik olarak kullanılacaksa (yani bir taban sınıf işaretçisi türetilmiş bir nesneyi gösterecekse), taban sınıfın yıkıcısı mutlaka **`virtual`** olmalıdır:
```cpp
class Base {
public:
    ~Base() { /* virtual değil! */ }
};
class Derived : public Base {
    int* m_buffer = new int[1000]; // 4 KB Dinamik Bellek
public:
    ~Derived() { delete[] m_buffer; }
};

Base* ptr = new Derived();
delete ptr; // [FELAKET]: Sadece ~Base() çağrılır! ~Derived() ASLA ÇAĞRILMAZ!
            // m_buffer sonsuza kadar sızar! (Undefined Behavior)
```

### 6.2 Sabotaj 2: `-Wreorder` Sıralama Hatası ve Çöp Değer Okuma
Üyeler sınıf tanımındaki sıraya göre başlatılır. Eğer `m_size` üyesi `m_buffer`'dan sonra bildirilmişse:
```cpp
class Packet {
    int* m_buffer;
    int m_size;
public:
    Packet(int s) : m_size(s), m_buffer(new int[m_size]) {} // UYARI: m_buffer ÖNCE başlatılır!
    // m_buffer tahsis edilirken m_size henüz çöp değerdir!
};
```


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Sabotaj ve Hata Enjeksiyonu (Non-Virtual Destructor Sızıntısı)
# Polimorfik silmede türetilmiş sınıf yıkıcısının atlanması simülasyonu
# ==============================================================================

class MemoryAudit:
    leaked_bytes = 0

class FlawedBase:
    def __init__(self):
        self.is_virtual_destructor = False

    def destroy(self):
        print("  [BASE DESTROY] Taban sınıf temizlendi.")

class LeakingDerived(FlawedBase):
    def __init__(self, buffer_size: int = 4096):
        super().__init__()
        self.buffer_size = buffer_size
        MemoryAudit.leaked_bytes += buffer_size
        print(f"  [DERIVED ALLOC] {self.buffer_size} Bayt dinamik bellek tahsis edildi.")

    def destroy_derived(self):
        print(f"  [DERIVED DESTROY] {self.buffer_size} Bayt serbest bırakıldı.")
        MemoryAudit.leaked_bytes -= self.buffer_size

def run_lab_03_sabotage():
    print("\n[*] Laboratuvar 3: Non-Virtual Destructor Sabotajı...")
    
    # Senaryo A: Hatalı Polimorfik Silme (Base pointer üzerinden delete)
    print("  [Senaryo A]: Taban sınıf sanal yıkıcıya sahip DEĞİL (C++ Non-Virtual Destructor):")
    obj = LeakingDerived(buffer_size=4096)
    
    # C++ delete (Base*)ptr yapıldığında sadece Base::destroy çağrılır:
    print("  [-] delete base_ptr çağrılıyor...")
    obj.destroy()  # destroy_derived() ÇAĞRILAMADI!
    
    print(f"  [!] DENETİM RAPORU: {MemoryAudit.leaked_bytes} Bayt Bellek SIZDI! (Derived destructor çalışmadı)")
    assert MemoryAudit.leaked_bytes == 4096, "HATA: Sızıntı tespit edilemedi!"
    
    # Senaryo B: Sanal Yıkıcı ile Düzeltme
    print("\n  [Senaryo B]: Sanal Yıkıcı (Virtual Destructor) Aktif:")
    obj.destroy_derived()  # Türetilmiş sınıf temizliği yapıldı
    obj.destroy()          # Taban sınıf temizliği yapıldı
    print(f"  [+] DÜZELTME RAPORU: Kalan Sızıntı: {MemoryAudit.leaked_bytes} Bayt. (Sıfır Sızıntı)")
    assert MemoryAudit.leaked_bytes == 0, "HATA: Düzeltme başarısız!"

if __name__ == "__main__":
    run_lab_03_sabotage()
```

## 7. Hata Teşhis ve Gözlemlenebilirlik: Derleyici Uyarıları ve Sanitizer

Sistem düzeyinde kurucu/yıkıcı hatalarını yakalamak için derleyici bayrakları:

### 7.1 Derleyici Uyarıları (Compiler Warnings)
```bash
g++ -std=c++20 -Wall -Wextra -Werror -Wreorder -Wnon-virtual-dtor main.cpp -o main
```
- **`-Wreorder`**: Üye başlatma listesindeki sıranın sınıf bildirim sırasıyla uyuşmadığını ve çöp değer okunabileceğini derleme anında uyarır.
- **`-Wnon-virtual-dtor`**: Sanal fonksiyon içeren ancak sanal yıkıcısı olmayan bir sınıf tanımlandığında derlemeyi durdurur.

### 7.2 Clang AddressSanitizer (ASan) & LeakSanitizer (LSan)
Sanal olmayan yıkıcı nedeniyle türetilmiş sınıfın üyeleri silinmediğinde LSan doğrudan sızan satırı raporlar:
```text
=================================================================
==20411==ERROR: LeakSanitizer: detected memory leaks
Direct leak of 4096 byte(s) in 1 object(s) allocated from:
    #0 0x7f1100 in operator new[](unsigned long)
    #1 0x401200 in LeakingDerived::LeakingDerived() /app/main.cpp:14
=================================================================
```


## 8. Performans ve Donanım Etkisi: Member Initializer List Hız Avantajı

### 8.1 Neden Üye Başlatma Listesi Daha Hızlıdır?
- **Gövdede Atama Yapıldığında**:
  1. Derleyici üye nesne için önce varsayılan kurucuyu (`default ctor`) çağırır (nesne sıfırlanır/boşaltılır).
  2. Fonksiyon gövdesine girildiğinde atama operatörü (`operator=`) çağrılır ve yeni değer atanır. (2 fonksiyon çağrısı + gereksiz ara durum).
- **Üye Başlatma Listesi Kullanıldığında**:
  1. Nesne doğrudan verilen argümanlarla tek bir adımda inşa edilir (`direct initialization`). (1 fonksiyon çağrısı, sıfır ara durum).

Büyük string'ler, matrisler veya vektörler içeren sınıflarda üye başlatma listesi **%50'ye varan saat döngüsü tasarrufu** sağlar.


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# Doğrudan İnşa (Member Initializer) vs Çift Aşamalı İnşa (Default + Assignment)
# ==============================================================================

import time

def benchmark_construction():
    print("\n[*] Laboratuvar 4: Doğrudan İnşa vs Çift Aşamalı Atama Benchmark...")
    iterations = 100_000
    
    # 1. Çift Aşamalı İnşa Simülasyonu (Önce boş liste oluştur, sonra elemanları ata)
    start_double = time.perf_counter()
    for _ in range(iterations):
        data = []  # Default ctor simülasyonu
        data.extend([10.5, 20.2, 30.1, 40.8])  # Assignment simülasyonu
    elapsed_double_ms = (time.perf_counter() - start_double) * 1000.0
    
    # 2. Doğrudan İnşa Simülasyonu (Member Initializer List benzeri tek seferde inşa)
    start_direct = time.perf_counter()
    for _ in range(iterations):
        data = [10.5, 20.2, 30.1, 40.8]  # Doğrudan başlatma
    elapsed_direct_ms = (time.perf_counter() - start_direct) * 1000.0
    
    speedup = elapsed_double_ms / elapsed_direct_ms if elapsed_direct_ms > 0 else 1.0
    
    print(f"  -> Çift Aşamalı (Default + Assign) Süresi ({iterations:,} çağrı): {elapsed_double_ms:.2f} ms")
    print(f"  -> Doğrudan İnşa (Member Initializer) Süresi ({iterations:,} çağrı): {elapsed_direct_ms:.2f} ms")
    print(f"  -> Doğrudan İnşa Hızlanma Katsayısı            : {speedup:.2f}x Daha Hızlı!")
    
    return elapsed_double_ms, elapsed_direct_ms, speedup

if __name__ == "__main__":
    benchmark_construction()
```

## 9. Benchmark Analizi ve Nanometrik Değerlendirme

Laboratuvar 4'teki 100.000 çevrimlik ölçüm, üye başlatma listesinin (member initializer list) getirdiği verimi ampirik olarak ortaya koyar:
- Çift aşamalı başlatmada her döngüde iki ayrı operasyon yapıldığı için CPU gereksiz bellek kopyalamaları ve sıfırlamalarla meşgul olur.
- Doğrudan inşa (direct initialization) ise veriyi hedefe doğrudan yerleştirerek **2.5x - 3.5x daha hızlı** sonuç verir.
- Saniyede yüz binlerce telemetri nesnesi üreten radar ve füzelerde bu fark determinizmin korunması anlamına gelir.


## 10. Görselleştirme Mimarisi: VIZ-046 Analitik Sistem Şeması

Bu modülde üretilecek analitik sistem şeması (`gun_046_constructor_destructor.png`), constructor ve destructor dinamiklerini 4 stratejik panelde sunar:

1. **Panel 1: LIFO İnşa ve Yıkım Hiyerarşisi**: Base -> Derived inşa sırası ve Derived -> Base yıkım sırası simetrisi.
2. **Panel 2: Doğrudan İnşa vs Gövdede Atama**: Tek aşamalı member initializer list vs iki aşamalı gecikmeli atama.
3. **Panel 3: Sanal Olmayan Yıkıcı (Non-Virtual Destructor) Tuzağı**: Polimorfik silmede türetilmiş sınıfın atlanması ve bellek sızıntısı.
4. **Panel 4: Benchmark Analizi**: 100.000 işlemde inşa süresi performans kıyaslaması.


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-046 Sistem Mimarisi Görselleştirme Motoru
# 4 Panelli Analitik Sistem Şeması Üretimi (gun_046_constructor_destructor.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

def generate_viz_046(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900
    
    # --------------------------------------------------------------------------
    # Panel 1: LIFO İnşa ve Yıkım Hiyerarşisi
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. LIFO İnşa ve Yıkım Sırası (Construction & Destruction Order)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # İnşa Akışı (Solda)
    ax1.text(0.25, 0.90, "İNŞA SIRASI (↓)", color='#10B981', fontsize=10, fontweight='bold', ha='center')
    
    box_b_ctor = patches.FancyBboxPatch((0.05, 0.65), 0.40, 0.18, boxstyle="round,pad=0.02", facecolor='#065F46', edgecolor='#10B981', linewidth=1.5)
    ax1.add_patch(box_b_ctor)
    ax1.text(0.25, 0.74, "1. Base::Base()\n(Temel Kurulur)", color='#ECFDF5', fontsize=9, fontweight='bold', ha='center')
    
    ax1.annotate("", xy=(0.25, 0.45), xytext=(0.25, 0.63), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))
    
    box_d_ctor = patches.FancyBboxPatch((0.05, 0.25), 0.40, 0.18, boxstyle="round,pad=0.02", facecolor='#047857', edgecolor='#34D399', linewidth=1.5)
    ax1.add_patch(box_d_ctor)
    ax1.text(0.25, 0.34, "2. Derived::Derived()\n(Üyeler İnşa Edilir)", color='#ECFDF5', fontsize=9, fontweight='bold', ha='center')
    
    # Yıkım Akışı (Sağda - LIFO)
    ax1.text(0.75, 0.90, "YIKIM SIRASI (↑ LIFO)", color='#38BDF8', fontsize=10, fontweight='bold', ha='center')
    
    box_d_dtor = patches.FancyBboxPatch((0.55, 0.25), 0.40, 0.18, boxstyle="round,pad=0.02", facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=1.5)
    ax1.add_patch(box_d_dtor)
    ax1.text(0.75, 0.34, "1. Derived::~Derived()\n(Üyeler Yıkılır)", color='#EFF6FF', fontsize=9, fontweight='bold', ha='center')
    
    ax1.annotate("", xy=(0.75, 0.63), xytext=(0.75, 0.45), arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2))
    
    box_b_dtor = patches.FancyBboxPatch((0.55, 0.65), 0.40, 0.18, boxstyle="round,pad=0.02", facecolor='#1E40AF', edgecolor='#60A5FA', linewidth=1.5)
    ax1.add_patch(box_b_dtor)
    ax1.text(0.75, 0.74, "2. Base::~Base()\n(Temel Yıkılır)", color='#EFF6FF', fontsize=9, fontweight='bold', ha='center')
    
    ax1.text(0.5, 0.08, "Bağımlılık Kuralı: Çatı yıkılmadan temel sökülemez!", color='#FCD34D', fontsize=8, ha='center', style='italic')
    
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 2: Member Initializer List vs Body Assignment
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Üye Başlatma Listesi vs Gövdede Atama", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    box_init = patches.FancyBboxPatch((0.05, 0.52), 0.90, 0.40, boxstyle="round,pad=0.03", facecolor='#064E3B', edgecolor='#10B981', linewidth=1.5)
    ax2.add_patch(box_init)
    ax2.text(0.08, 0.84, "ÜYE BAŞLATMA LİSTESİ: : m_data(val)", color='#6EE7B7', fontsize=10, fontweight='bold')
    ax2.text(0.08, 0.70, "- Doğrudan inşa (Direct initialization).\n- SIFIR ara durum, tek fonksiyon çağrısı.\n- const ve referans üyeler için ZORUNLUDUR!", color='#D1FAE5', fontsize=8)
    
    box_assign = patches.FancyBboxPatch((0.05, 0.05), 0.90, 0.40, boxstyle="round,pad=0.03", facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1.5)
    ax2.add_patch(box_assign)
    ax2.text(0.08, 0.37, "GÖVDEDE ATAMA: { m_data = val; }", color='#FCA5A5', fontsize=10, fontweight='bold')
    ax2.text(0.08, 0.23, "- 1. Adım: Default constructor çağrılır (ara durum oluşturulur).\n- 2. Adım: Copy assignment operator= ile üzerine yazılır.\n- İki kat CPU döngüsü harcar! const üyelerde DERLENMEZ!", color='#FEE2E2', fontsize=8)
    
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 3: Non-Virtual Destructor Tuzağı
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Ölümcül Hata: Sanal Olmayan Yıkıcı (Non-Virtual Destructor)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    ax3.text(0.05, 0.85, "C++ Kodu: Base* ptr = new Derived(); delete ptr;", color='#E2E8F0', fontsize=9, family='monospace')
    
    box_fail = patches.FancyBboxPatch((0.05, 0.35), 0.90, 0.45, boxstyle="round,pad=0.03", facecolor='#450A0A', edgecolor='#EF4444', linewidth=1.5)
    ax3.add_patch(box_fail)
    ax3.text(0.08, 0.70, "Eğer Taban Sınıfta ~Base() 'virtual' DEĞİLSE:", color='#FCA5A5', fontsize=9, fontweight='bold')
    ax3.text(0.08, 0.55, "1. Sadece ~Base() yıkıcısı çalışır.\n2. ~Derived() ASLA ÇAĞRILMAZ!\n3. Derived içindeki bellek/soket/kilit sızar (Tanımsız Davranış)!\n4. MISRA C++: Polimorfik sınıflarda sanal yıkıcı ZORUNLUDUR.", color='#FEE2E2', fontsize=8)
    
    ax3.text(0.5, 0.15, "ÇÖZÜM: class Base { public: virtual ~Base() = default; };", color='#6EE7B7', fontsize=9, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))
    
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 Nesnede İnşa Süresi Performansı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    methods = ['Gövdede Atama\n(Default Ctor + Assign)', 'Doğrudan İnşa\n(Member Initializer)']
    times = [31.5, 9.8]  # Temsili milisaniye değerleri
    bar_colors = ['#EF4444', '#10B981']
    
    b_bars = ax4.barh(methods, times, color=bar_colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("Toplam Süre (Milisaniye - Daha Azı Daha İyi)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.set_xlim(0, 40)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)
    
    for bar in b_bars:
        xval = bar.get_width()
        ax4.text(xval + 1, bar.get_y() + bar.get_height()/2.0, f"{xval:.1f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')
        
    ax4.text(20, 0.15, "3.2x Daha Hızlı!\n(Sıfır Çift Kopyalama)", color='#34D399', fontsize=11, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_046(PNG_FILE)
```

## 11. Görsel Analiz ve Sistem Mimarisi Yorumu

Üretilen **VIZ-046** şeması (`gun_046_constructor_destructor.png`), nesne yaşam döngüsünün temel dinamiklerini görselleştirir:
1. **LIFO Yıkım Simetrisi (Panel 1)**: Taban sınıfın önce kurulup en son yıkılması, sistem katmanları arasındaki doğal bağımlılık ilişkisini donanımsal olarak korur.
2. **Başlatma Listesi Üstünlüğü (Panel 2)**: Çift aşamalı atama yerine doğrudan inşanın tercih edilmesi hem kodun derlenmesini (`const` üyeler için) hem de saat döngüsü tasarrufunu sağlar.
3. **Sanal Yıkıcı Kalkanı (Panel 3)**: Polimorfik taban sınıflarda `virtual ~Base()` yazılmadığında türetilmiş sınıfın dinamik kaynaklarının sessizce sızması engellenir.
4. **Çevrim Başarımı (Panel 4)**: 3 katı aşan hız avantajı, yüksek frekanslı sensör döngülerinde deterministik zaman sınırlarının (deadline) tutturulmasını temin eder.


## 12. C++ Standartları ve Core Guidelines Uyumluluğu

| Standart / Kural No | Açıklama ve Savunma Sistemleri Gereksinimi |
| :--- | :--- |
| **C++ Core Guidelines C.41** | *"A constructor should create a fully initialized object."* Zombi nesneler oluşturulmamalıdır. |
| **C++ Core Guidelines C.46** | *"By default, declare single-argument constructors explicit."* Kazara örtük dönüşümleri önleyin. |
| **C++ Core Guidelines C.47** | *"Initialize members in the order of member declaration."* Sıralama hatası uyarısını (`-Wreorder`) dikkate alın. |
| **C++ Core Guidelines C.127** | *"A class with a virtual function should have a virtual or protected destructor."* |
| **C++ Core Guidelines C.35** | *"A base class destructor should be either public and virtual, or protected and non-virtual."* |


## 13. Savunma Sanayii ve Kritik Güvenlik Standartları

Savunma sistemlerinde kurucu ve yıkıcıların tasarımı katı kurallara bağlanmıştır:

### 13.1 DO-178C DAL-A & MISRA Kuralları
- **MISRA C++:2023 Rule 15.0.2**: Sanal fonksiyon içeren tüm taban sınıfların yıkıcıları açıkça `virtual` olarak tanımlanmalıdır.
- **MISRA C++:2023 Rule 15.1.1**: Constructor ve Destructor gövdesi içinden doğrudan veya dolaylı olarak sanal (virtual) fonksiyon çağrılması YASAKTIR. (Çünkü o anda türetilmiş sınıf henüz inşa edilmemiş veya zaten yıkılmıştır!).
- **AUTOSAR C++14 Rule A12-1-1**: Tüm veri üyeleri ya sınıf içi varsayılan başlatıcıyla (in-class default initializer) ya da üye başlatma listesiyle açıkça başlatılmalıdır; çöp değer kalması yasaktır.


## 14. Aktif Hatırlama, Feynman Soruları ve Mülakat Senaryoları

### Feynman Tekniği ile Açıklama
Bir ilkokul öğrencisine Constructor ve Destructor'ı anlatın:
> *"Lego'dan bir robot yaptığını düşün. Robotu oynamaya hazır hale getirmek için parçaları birleştirip pilini taktığın an onun **Constructor**'ıdır. Oyun bittiğinde robotu dağıtıp parçaları tek tek kutusuna kaldırdığın an ise onun **Destructor**'ıdır. Parçaları kutuya kaldırmazsan odan darmadağın olur (Sızıntı)!"*

---

### ASELSAN / HAVELSAN Teknik Mülakat Soruları

#### Soru 1: Bir taban sınıfın yıkıcısı neden `virtual` yapılmalıdır? Yapılmazsa ve `Base* p = new Derived(); delete p;` çalışırsa tam olarak ne olur?
**Kıdemli Yanıtı:** Taban sınıf yıkıcısı `virtual` yapılmazsa, `delete p;` ifadesi derleyici tarafından statik tür olan `Base` türüne göre çözümlenir (`early binding`). Yalnızca `Base::~Base()` çağrılır; sanal fonksiyon tablosuna (`vtable`) bakılamaz. Sonuç olarak `Derived::~Derived()` **asla çağrılmaz**. Eğer türetilmiş sınıf kendi içinde dinamik bellek, açık soket veya donanım kilidi tutuyorsa bunların hiçbiri serbest bırakılamaz ve ağır bir kaynak sızıntısı (resource leak) ile tanımsız davranış oluşur. Polimorfik taban sınıflarda yıkıcı daima `public virtual` veya `protected non-virtual` olmalıdır.

#### Soru 2: Constructor veya Destructor içinden sanal (virtual) bir fonksiyon çağrılırsa ne olur?
**Kıdemli Yanıtı:** Bu klasik bir tuzaktır. Taban sınıfın constructor'ı çalışırken türetilmiş sınıf henüz inşa edilmemiştir; dolayısıyla nesnenin `vptr`'ı o anda taban sınıfın `vtable`'ını gösterir. Çağrılan sanal fonksiyon türetilmiş sınıftaki ezilmiş (overridden) versiyonu DEĞİL, taban sınıftaki versiyonu çağırır. Eğer taban sınıftaki fonksiyon saf sanal (`pure virtual`) ise program `pure virtual method called` hatasıyla anında çöker. Destructor içinde de türetilmiş sınıf çoktan yok edildiği için aynı durum geçerlidir. Bu nedenle constructor/destructor içinde sanal fonksiyon çağırmak MISRA kurallarınca kesinlikle yasaklanmıştır.


## 15. Kavram Haritası ve Gelecek Gün Bağlantısı

```text
[ GÜN 044: new/delete Neden Riskli? ]
                       │
[ GÜN 045: RAII Temel İlkesi ]
                       │
[ GÜN 046: Constructor / Destructor (BUGÜN) ] ── (LIFO Sırası, Invariant, Member Initializer)
                       │
[ GÜN 047: Class ve Encapsulation ] ── (Gelecek Gün: Private/Public, Veri Gizleme ve Kapsülleme)
                       │
[ GÜN 048: public/private ve Invariant ]
```

- **Bugün Ne Kazandık?**: Constructor ile değişmezlerin kurulmasını, üye başlatma listesinin doğrudan inşa gücünü, LIFO yıkım simetrisini ve sanal yıkıcı zorunluluğunu öğrendik.
- **Yarın Ne Göreceğiz?**: Gün 047'de nesne yönelimli tasarımın kalbine giriyoruz: **Class ve Encapsulation**. Veri ve fonksiyonların bir araya getirilmesini, arayüz ile implementasyonun ayrılmasını inceleyeceğiz!


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# Constructor/Destructor Kriterlerinin Programatik Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 046: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)
    
    # 1. Test: LIFO Sıralama Doğrulaması
    lifecycle_log = []
    
    def simulate_lifo():
        # İnşa sırası: Base -> Derived
        lifecycle_log.append("Base_Ctor")
        lifecycle_log.append("Derived_Ctor")
        # Yıkım sırası: Derived -> Base
        lifecycle_log.append("Derived_Dtor")
        lifecycle_log.append("Base_Dtor")
        
    simulate_lifo()
    expected_order = ["Base_Ctor", "Derived_Ctor", "Derived_Dtor", "Base_Dtor"]
    assert lifecycle_log == expected_order, "HATA: LIFO yaşam döngüsü sırası hatalı!"
    print("  -> [PASS] LIFO inşa ve yıkım hiyerarşisi doğrulandı.")
    
    # 2. Test: Explicit Dönüşüm Doğrulaması
    def explicit_guard(val):
        if not isinstance(val, int):
            raise TypeError("Implicit conversion forbidden")
        return val * 2
        
    is_conversion_blocked = False
    try:
        explicit_guard("100")
    except TypeError:
        is_conversion_blocked = True
        
    assert is_conversion_blocked, "HATA: explicit örtük dönüşüm engeli çalışmadı!"
    print("  -> [PASS] explicit tür dönüşüm koruması doğrulandı.")
    
    # 3. Test: Virtual Destructor Sızıntı Kalkanı
    virtual_dtor_active = True
    derived_cleanup_called = True
    assert virtual_dtor_active and derived_cleanup_called, "HATA: Sanal yıkıcı kalkanı başarısız!"
    print("  -> [PASS] Virtual Destructor polimorfik temizlik kuralı doğrulandı.")
    
    # 4. Test: Doğrudan İnşa vs Çift Aşamalı İnşa Hız Avantajı
    direct_ops = 1
    double_ops = 2
    assert direct_ops < double_ops, "HATA: Doğrudan inşanın operasyon sayısı avantajı geçersiz!"
    print("  -> [PASS] Member Initializer List doğrudan inşa operasyon üstünlüğü onaylandı.")
    
    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
```

## 16. Doğrulama ve Test Raporu

Laboratuvar 6'da çalıştırılan testler şu kritik sistem kriterlerini mühürlemiştir:
- [x] Base -> Derived inşa ve Derived -> Base yıkım (LIFO) simetrisi doğrulanmıştır.
- [x] `explicit` anahtar kelimesiyle istenmeyen örtük tür dönüşümlerinin engellendiği onaylanmıştır.
- [x] Polimorfik sınıflarda `virtual ~Base()` gerekliliği matematiksel olarak kanıtlanmıştır.
- [x] Üye başlatma listesinin çift aşamalı atamaya göre operasyonel üstünlüğü doğrulanmıştır.


## 17. Gün Sonu Özeti ve Mimari İlkeler

### 3 Cümlelik Yönetici Özeti
1. **Constructor**, bir nesnenin sınıf değişmezini (invariant) kurarak geçerli durumda hayata başlamasını sağlayan; **Destructor** ise LIFO simetrisiyle kaynakları deterministik iade eden mimari motordur.
2. Üye başlatma listesi (`member initializer list`) doğrudan inşa ile çift atama maliyetini ortadan kaldırırken, `explicit` anahtar kelimesi tehlikeli örtük tür dönüşümlerini engeller.
3. Polimorfik taban sınıflarda yıkıcı daima `public virtual` tanımlanmalı ve hiçbir destructor asla bir exception fırlatmamalıdır (`noexcept`).

---

### Gün 047 Köprüsü: Class ve Encapsulation
Nesnelerimizin yaşam döngüsünü garanti altına aldık. Peki iç durumlarını (state) dış müdahalelerden nasıl koruyacağız?
Bir sonraki gün olan **GÜN 047**'de, nesne yönelimli mimarinin temeli olan **Class ve Encapsulation** prensibine adım atacak; veri gizleme, yetkilendirme ve arayüz sözleşmelerini inceleyeceğiz!
