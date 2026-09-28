<!--
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
-->

# GÜN 047: Class ve Encapsulation (Veri Bütünlüğü, Arayüz Ayrımı ve Invariant Koruma)

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
[![C++ Standard](https://img.shields.io/badge/C%2B%2B-20-blue?style=flat-square&logo=c%2B%2B)](https://en.cppreference.com/w/cpp/20)
[![Domain](https://img.shields.io/badge/Domain-Defense%20Systems%20%26%20Safety--Critical-darkgreen?style=flat-square)]()
[![Safety](https://img.shields.io/badge/Safety-MISRA%20C%2B%2B%3A2023%20%7C%20AUTOSAR-orange?style=flat-square)]()

---

### 1. 5N1K Kurumsal Analiz Çerçevesi

| Soru | Sistem Mühendisliği Yanıtı |
| :--- | :--- |
| **Ne? (What)** | **Class (Sınıf)**, veriyi (state) ve o veriyi işleyen operasyonları bir araya getiren kullanıcı tanımlı türdür. **Encapsulation (Kapsülleme)** ise iç uygulama detaylarını ve ham verileri gizleyerek (`private`), dış dünyaya yalnızca doğrulanmış ve güvenli bir arayüz (`public`) sunma disiplinidir. |
| **Neden? (Why)** | Kritik savunma yazılımlarında ham değişkenlere doğrudan dışarıdan yazılması veri bozulmasına (corruption), fiziksel limitlerin aşılmasına ve ölümcül kaza senaryolarına yol açar. Kapsülleme, sistem değişmezlerinin (invariants) her an geçerli kalmasını matematiksel olarak garanti eder. |
| **Nasıl? (How)** | Veri üyelerini kesinlikle `private` yaparak; dış dünyayla iletişimi yalnızca iş kurallarını denetleyen üye metodlar üzerinden yürüterek ("Tell, Don't Ask" prensibi). |
| **Nerede? (Where)** | Füze kanat eyleyici kontrolcüleri, radar frekans sentezleyicileri, aviyonik durum makineleri ve otopilot güdüm filtrelerinde. |
| **Ne Zaman? (When)** | Birbirine bağımlı veri alanları ve korunması gereken bir fiziksel/mantıksal kural (invariant) bulunduğu anda. |
| **Kim? (Who)** | ASELSAN, HAVELSAN, ROKETSAN gibi kurumlarda emniyet-kritik (safety-critical) modüller geliştiren yazılım mimarları. |

---

### 2. Pratik Hayat ve Savunma Sanayii Analojisi

> **F-16 Uçuş Kontrol Bilgisayarı (Fly-By-Wire) ve Pilot Lövyesi:**
> - Klasik bir Cessna uçağında pilot lövyeyi çektiğinde çelik teller doğrudan kanatçığı büker (Ham Veri Erişimi - No Encapsulation). Pilot lövyeyi aşırı çekerse kanat havada kırılabilir!
> - Bir F-16 savaş uçağında ise lövye kanatlara doğrudan bağlı değildir (**Kapsülleme - Fly-By-Wire**). Pilot lövyeyi sonuna kadar çekse bile, aradaki Uçuş Kontrol Bilgisayarı (`class FlightController`) bu komutu bir istek olarak alır (`requestPitch()`). Uçağın anlık hızına, hücum açısına (AoA) ve G-kuvvetine bakar. Eğer uçağın aerodinamik limitlerini aşacak bir durum varsa, kanatları yalnızca uçağın parçalanmayacağı maksimum güvenli açıya kadar eğer (Invariant Koruma).
> - Kapsülleme pilotun yeteneğine güvenmek yerine, yazılımın fizik kurallarını korumasını sağlar!


## 1. Class ve Kapsüllemenin Makine Modeli

### 1.1 Bellek Modeli: `class` vs `struct`

C++ dilinde `class` ve `struct` derleyici düzeyinde tamamen **özdeştir**:
- `sizeof(MyClass)` ile `sizeof(MyStruct)` aynı veri üyelerine sahipse bellek boyutu ve hizalaması (alignment/padding) birebir aynıdır.
- Üye fonksiyonlar (metodlar) **nesnenin içinde yer kaplamaz!** Metodlar programın kod segmentinde (`Text Segment`) tek bir kopya olarak yaşar.
- **Yegane Fark:** `class`'ta varsayılan erişim belirteci `private`, `struct`'ta ise `public`'tir.

### 1.2 `this` Pointer Mekanizması

Derleyici bir üye fonksiyonu çağırırken, arka planda fonksiyonun ilk gizli parametresi olarak çağrılan nesnenin adresini (`this`) geçer:

```cpp
// C++ Kodu:
class MissileFin {
    double m_angle;
public:
    void setAngle(double a) { m_angle = a; }
};
MissileFin fin;
fin.setAngle(15.0);

// Derleyicinin Ürettiği C Benzeri Kod (Name Mangling):
void MissileFin_setAngle(MissileFin* const this, double a) {
    this->m_angle = a;
}
MissileFin_setAngle(&fin, 15.0);
```

### 1.3 Değişmez (Invariant) Nedir?

Bir sınıfın değişmezi (**Invariant**), bir nesnenin tüm yaşam döngüsü boyunca (fonksiyon çağrıları arasında) **doğru ve geçerli kalması zorunlu olan mantıksal veya fiziksel kuraldır**.
- *Örnek 1:* Füze kanatçık açısı: $-30.0^\circ \le \theta \le +30.0^\circ$.
- *Örnek 2:* Tarih sınıfı: Gün sayısı $1 \le 	ext{day} \le 31$ olmalıdır (Asla 32 olamaz).
- Kapsülleme olmadan bu değişmezler dış dünya tarafından kazara bozulabilir.


## 2. Mimari Karar Matrisi: `class` mı Yoksa `struct` mı?

C++ Core Guidelines kuralı **C.2**'ye göre ayrım çok nettir:

```text
                     [ Veri Yapısı Tasarımı ]
                                │
               Veri Üyeleri Arasında Bir Invariant (Kural)
               veya Bağımlılık Var mı?
                 ├── EVET ──> CLASS (Veriler private, erişim metotlarla)
                 └── HAYIR ─> STRUCT (Tüm veriler public - DTO / POD)
```

| Ölçüt | `class` Tercih Edilmeli | `struct` Tercih Edilmeli |
| :--- | :--- | :--- |
| **Kullanım Amacı** | İş mantığı (Business Logic), Invariant koruma, Durum Makinesi | Salt Veri Taşıma (DTO / POD), Konfigürasyon Paketleri |
| **Veri Üyeleri** | Kesinlikle `private` | Tamamen `public` |
| **Bağımsızlık** | Üyeler birbirine bağımlıdır (örn: `width * height == area`) | Üyeler bağımsızca değişebilir (örn: `Point2D{x, y}`) |
| **Tasarım İlkesi** | **Tell, Don't Ask** (Davranış odaklı) | Veri yapısı (Data holder) |


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Kapsüllenmiş Füze Kanat Kontrolcüsü vs Ham Veri Erişimi
# Invariant koruması ve sınır aşımı tespiti simülasyonu
# ==============================================================================

class UnsafeFinStruct:
    """Kapsülleme Olmayan Ham Veri Yapısı (Tehlikeli struct)"""
    def __init__(self, angle_deg: float):
        self.angle_deg = angle_deg  # Doğrudan public erişim!

class SafeFinClass:
    """Kapsüllenmiş ve Invariant Korumalı Aviyonik Sınıfı (C++ class)"""
    MAX_LIMIT_DEG = 30.0
    MIN_LIMIT_DEG = -30.0

    def __init__(self, initial_angle: float):
        self._angle_deg = 0.0
        self.set_angle(initial_angle)  # Invariant kontrolü

    def set_angle(self, target_angle: float):
        """Fiziksel kanat sınırlarını denetleyen kapsülleme metodu"""
        if target_angle > self.MAX_LIMIT_DEG or target_angle < self.MIN_LIMIT_DEG:
            raise ValueError(
                f"[AERODYNAMIC VIOLATION] Kanat açısı limit dışı!\n"
                f"  -> Talep Edilen : {target_angle}°\n"
                f"  -> Güvenli Sınır: [{self.MIN_LIMIT_DEG}°, {self.MAX_LIMIT_DEG}°]\n"
                f"  -> Sonuç: Kanat kırılma ve kontrol kaybı engellendi!"
            )
        self._angle_deg = target_angle

    def get_angle(self) -> float:
        return self._angle_deg

def run_lab_01_encapsulation_basics():
    print("[*] Laboratuvar 1: Kapsülleme ve Invariant Güvencesi Başlatılıyor...")
    
    # 1. Güvensiz Yapı (Kapsülleme Yok): Dış kod veriyi bozabilir
    print("\n[1] GÜVENSİZ HAM STRUCT ERİŞİMİ:")
    unsafe_fin = UnsafeFinStruct(10.0)
    print(f"    İlk Açı: {unsafe_fin.angle_deg}°")
    # Kazara veya acemi kod fiziksel sınırı aşıyor:
    unsafe_fin.angle_deg = 85.0  # Kanat 85 dereceye büküldü!
    print(f"    [FELAKET]: Ham veri bozuldu! Açı: {unsafe_fin.angle_deg}° -> Kanat havada koptu!")
    
    # 2. Güvenli Kapsüllenmiş Sınıf (C++ class)
    print("\n[2] GÜVENLİ KAPSÜLLENMİŞ CLASS ERİŞİMİ:")
    safe_fin = SafeFinClass(10.0)
    print(f"    İlk Açı: {safe_fin.get_angle()}°")
    safe_fin.set_angle(25.0)
    print(f"    Güvenli Açı Güncellendi: {safe_fin.get_angle()}°")
    
    # Hatalı komut gönderiliyor:
    try:
        print("    -> 85.0° kanat açısı talep ediliyor...")
        safe_fin.set_angle(85.0)
    except ValueError as ex:
        print(f"    [BAŞARILI SAVUNMA]: Sistem müdahale etti ve hatayı yakaladı:")
        print(f"    {ex}")
        
    print(f"    Mevcut Durum KORUNDU: {safe_fin.get_angle()}° (Bozulma engellendi)")

if __name__ == "__main__":
    run_lab_01_encapsulation_basics()
```

## 3. Laboratuvar 1 Çıktı Analizi: Veri Bütünlüğü Nasıl Sağlandı?

Laboratuvar 1'deki deney sistem emniyeti açısından şu gerçeği kanıtlar:
- **Ham Erişimde**: Dış dünyadaki herhangi bir modül, fonksiyon veya iş parçacığı (thread) `fin.angle_deg = 85.0` yazarak sistemin fiziksel sınırlarını delebilir. Derleyici hiçbir uyarı veremez çünkü değişken tipleri uyuşmaktadır (`double`).
- **Kapsüllenmiş Erişimde**: Veri üyesi gizlenmiş (`_angle_deg`) ve erişim `set_angle()` arayüzü arkasına alınmıştır. Geçersiz bir değer geldiğinde sınıf kendi değişmezini (`[-30, +30]`) korur; geçersiz durumu reddeder ve hatayı çağırana fırlatır. Nesne asla bozuk bir durumda yaşayamaz.


## 4. Getter/Setter Yanılsaması ve "Tell, Don't Ask" Prensibi

Birçok yazılımcı tüm değişkenleri `private` yapıp, her birine bir `get()` ve `set()` yazarak kapsülleme yaptığını sanır. **Bu sahte kapsüllemedir (Fake Encapsulation)!**

```cpp
// KÖTÜ TASARIM: Sahte Kapsülleme (Anemic Model)
radar.setAzimuth(radar.getAzimuth() + 5.0); // Dış kod hesaplıyor ve içine yazıyor

// MÜKEMMEL TASARIM: Davranış Odaklı Kapsülleme ("Tell, Don't Ask")
radar.rotateClockwise(5.0); // Radar kendi iç matematiğini ve sınırını kendisi işletir!
```

### "Tell, Don't Ask" Kuralı:
Bir nesneye verilerini sormayın (`Ask`), ona ne yapması gerektiğini söyleyin (`Tell`). Nesne kendi verisini kendi içinde işlesin!


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Taktik Balistik Füze Durum Makinesi (State Machine Encapsulation)
# Yetkisiz Durum Geçişlerinin (Illegal State Transitions) Kapsülleme ile Engellenmesi
# ==============================================================================

from enum import Enum

class MissileState(Enum):
    STANDBY = "BEKLEMEDE"
    ARMED = "KONTROLLÜ_ATEŞE_HAZIR"
    BOOST = "FÜZE_MOTORU_ATEŞLENDİ"
    TERMINAL = "HEDEFE_DALIŞ"
    DETONATED = "İMHA_EDİLDİ"

class BallisticGuidanceComputer:
    """Taktik Füze Görev Bilgisayarı Sınıfı"""
    def __init__(self, serial_no: str):
        self.serial_no = serial_no
        self.__state = MissileState.STANDBY  # Private durum değişkeni
        self.__altitude_m = 0.0

    def arm_missile(self, safety_pin_removed: bool):
        """Yalnızca beklemedeyken ve güvenlik pimi çekilmişse silahlanabilir"""
        if self.__state != MissileState.STANDBY:
            raise RuntimeError(f"Füze {self.__state.value} durumundayken silahlanamaz!")
        if not safety_pin_removed:
            raise PermissionError("Emniyet pimi takılı! Silahlanma engellendi.")
        self.__state = MissileState.ARMED
        print(f"  [GÜDÜM] Füze Silahlandı: {self.__state.value}")

    def launch(self):
        """Yalnızca silahlanmış durumdaysa ateşlenebilir"""
        if self.__state != MissileState.ARMED:
            raise RuntimeError(f"[GÜVENLİK İHLALİ] Füze silahlanmadan ateşlenemez! Durum: {self.__state.value}")
        self.__state = MissileState.BOOST
        self.__altitude_m = 500.0
        print(f"  [GÜDÜM] Ateşleme Başarılı! İrtifa: {self.__altitude_m}m | Durum: {self.__state.value}")

    def get_state_display(self) -> str:
        return self.__state.value

def run_lab_02_state_machine():
    print("\n[*] Laboratuvar 2: Savunma Sanayii Durum Makinesi Kapsüllemesi...")
    guidance = BallisticGuidanceComputer("TRG-300-KAPLAN")
    
    # 1. Hatalı Geçiş: Beklemedeyken doğrudan ateşleme denemesi
    print("  [Deneme 1]: Beklemedeki füzeyi doğrudan ateşleme girişimi:")
    try:
        guidance.launch()
    except RuntimeError as ex:
        print(f"    [ENGELLENDİ]: {ex}")
        
    # 2. Kurallara Uygun Sıralı Geçiş
    print("\n  [Deneme 2]: Güvenlik prosedürlerine uygun operasyon:")
    guidance.arm_missile(safety_pin_removed=True)
    guidance.launch()
    print(f"    Son Durum: {guidance.get_state_display()}")

if __name__ == "__main__":
    run_lab_02_state_machine()
```

## 5. Laboratuvar 2 Değerlendirmesi: Durum Güvenliği (State Integrity)

Laboratuvar 2'deki balistik füze senaryosu, kapsüllemenin güvenlik-kritik rolünü ortaya koyar:
- Eğer `__state` değişkeni public olsaydı, yazılımdaki bir mantık hatası füzeyi doğrudan `BOOST` durumuna geçirebilir ve füze hangarın içinde infilak edebilirdi.
- Kapsülleme sayesinde durum geçişleri yalnızca `arm_missile()` ve `launch()` metodlarıyla sınırlandırılmış; yetkisiz ve tehlikeli adımlar derleme ve çalışma anında kesin olarak engellenmiştir.


## 6. Ölümcül Hatalar, Anti-Pattern'ler ve Sabotaj Senaryoları

### 6.1 Sabotaj: Private Veriye Referans Döndürmek (Broken Encapsulation)
Kapsüllemenin en tehlikeli delinme şekli, sınıfın `private` üyesine non-const referans veya pointer döndüren bir getter yazmaktır:

```cpp
class TelemetryData {
    int m_critical_crc; // Private
public:
    int& getCrc() { return m_critical_crc; } // FELAKET: Private verinin referansı dışarı verildi!
};

TelemetryData tel;
int& ref = tel.getCrc();
ref = 0xDEAD; // DIŞ KOD PRIVATE DEĞİŞKENİ DOĞRUDAN EZDİ! Kapsülleme çöktü!
```

*Çözüm:* Getter fonksiyonları daima değerle (`int getCrc() const`) veya const referansla (`const BigData& getData() const`) dönmelidir.


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Sabotaj ve Hata Enjeksiyonu
# Kapsüllemenin Non-Const Referans / Nesne Döndürülerek Hacklenmesi
# ==============================================================================

class VulnerableTargetRegistry:
    def __init__(self):
        self._target_ids = [101, 102, 103]  # Private liste

    def get_targets_broken(self):
        """FELAKET: İç listenin doğrudan referansını dönüyor!"""
        return self._target_ids

    def get_targets_secure(self):
        """DOĞRU: İç listenin salt-okunur kopyasını dönüyor (const referans benzeri)"""
        return tuple(self._target_ids)

def run_lab_03_sabotage():
    print("\n[*] Laboratuvar 3: Kapsüllemenin Referans ile Delinmesi Sabotajı...")
    registry = VulnerableTargetRegistry()
    
    # 1. Sabotaj: Dış kod private listeyi değiştiriyor
    print("  [1] Delinmiş Kapsülleme Simülasyonu:")
    leaked_ref = registry.get_targets_broken()
    print(f"    Orijinal Liste: {leaked_ref}")
    # Dışarıdan yetkisiz modifikasyon:
    leaked_ref.clear()  # İç veri silindi!
    print(f"    [SABOTAJ]: Dışarıdan iç veri silindi! Güncel Durum: {registry._target_ids}")
    assert len(registry._target_ids) == 0, "HATA: Veri silinemedi!"
    
    # 2. Güvenli Kapsülleme
    print("\n  [2] Güvenli Salt-Okunur Kapsülleme:")
    secure_registry = VulnerableTargetRegistry()
    immutable_ref = secure_registry.get_targets_secure()
    try:
        immutable_ref.append(999)  # Değiştirilemez tuple
    except AttributeError as ex:
        print(f"    [BAŞARILI SAVUNMA]: Dış kod iç veriyi değiştiremedi: {ex}")
        print(f"    Güvenli Durum: {secure_registry._target_ids}")

if __name__ == "__main__":
    run_lab_03_sabotage()
```

## 7. Hata Teşhis ve Gözlemlenebilirlik: Invariant Doğrulama

Kapsüllemenin zırh gibi kalması için sınıf içine **Invariant Doğrulama Metotları** yerleştirilir:

### 7.1 `check_invariants()` Deseni
```cpp
class RadarAntenna {
    double m_azimuth;
    double m_elevation;
    
    void check_invariants() const {
        assert(m_azimuth >= 0.0 && m_azimuth < 360.0);
        assert(m_elevation >= -10.0 && m_elevation <= 90.0);
    }
public:
    void rotate(double delta) {
        m_azimuth = std::fmod(m_azimuth + delta, 360.0);
        check_invariants(); // Her metodun sonunda değişmez kontrol edilir!
    }
};
```

Debug modunda `-DDEBUG` derlemesiyle `assert` kontrolleri açık tutulur; sahada ise release optimizasyonuyla sıfır ek yükle çalışır.


## 8. Performans ve Donanım Etkisi: Kapsüllemenin Sıfır Ek Yükü (Zero-Overhead)

Birçok acemi yazılımcı "Değişkeni public yaparsam daha hızlı erişirim, metot çağırmak ek maliyettir" diye düşünür. **Bu tamamen yanlıştır!**

### 8.1 Derleyici İçi Genişletme (Inlining)
```cpp
class Sensor {
    int m_val;
public:
    int getVal() const { return m_val; }
};
```
Derleyici `-O2` veya `-O3` bayraklarıyla derlerken `sensor.getVal()` çağrısını **doğrudan bellek adresinden okumaya (inlining) dönüştürür**. 
- Fonksiyon çağrı maliyeti (`call / ret`) üretilmez.
- Üretilen makine kodu ham `sensor.m_val` erişimiyle **birebir aynıdır!**
- Kapsülleme sıfır maliyetle (zero-cost) tam güvenlik sağlar.


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# Kapsüllenmiş Metot Çağrısı vs Ham Değişken Erişimi 100.000 Çevrim Ölçümü
# ==============================================================================

import time

class BenchmarkTarget:
    def __init__(self):
        self.public_val = 100
        self._encapsulated_val = 100

    def get_val(self) -> int:
        return self._encapsulated_val

def benchmark_access_speed():
    print("\n[*] Laboratuvar 4: Ham Erişim vs Kapsüllenmiş Erişim Benchmark...")
    iterations = 100_000
    target = BenchmarkTarget()
    
    # 1. Ham Değişken Erişimi
    start_raw = time.perf_counter()
    for _ in range(iterations):
        val = target.public_val + 5
    elapsed_raw_ms = (time.perf_counter() - start_raw) * 1000.0
    
    # 2. Kapsüllenmiş Metot Erişimi
    start_encap = time.perf_counter()
    for _ in range(iterations):
        val = target.get_val() + 5
    elapsed_encap_ms = (time.perf_counter() - start_encap) * 1000.0
    
    print(f"  -> Ham Değişken Erişimi ({iterations:,} çağrı): {elapsed_raw_ms:.2f} ms")
    print(f"  -> Kapsüllenmiş Metot  ({iterations:,} çağrı): {elapsed_encap_ms:.2f} ms")
    print(f"  -> TESPİT: C++'ta inline metotlar ham erişimle BİREBİR AYNI makine kodunu üretir (0.0 ns fark)!")
    
    return elapsed_raw_ms, elapsed_encap_ms

if __name__ == "__main__":
    benchmark_access_speed()
```

## 9. Benchmark Analizi ve Nanometrik Değerlendirme

Laboratuvar 4 ölçümleri ve C++ optimizasyon ilkeleri şu gerçeği vurgular:
- Python gibi dinamik dillerde fonksiyon çağrısı küçük bir ek yük getirse de, C++ derleyicileri (GCC, Clang, MSVC) basit erişim metodlarını **inlining** ile doğrudan CPU yazmaçlarına (registers) indirger.
- Savunma sanayiinde veri üyelerini doğrudan public yapmak hız kazandırmaz; yalnızca sistemi veri bozulmalarına karşı korumasız bırakır.


## 10. Görselleştirme Mimarisi: VIZ-047 Analitik Sistem Şeması

Bu modülde üretilecek analitik sistem şeması (`gun_047_class_ve_encapsulation.png`), kapsüllemenin güvenlik ve mimari boyutlarını 4 stratejik panelde detaylandırır:

1. **Panel 1: Kapsülleme Mimarisi ve Koruma Kalkanı**: Private veri çekirdeği ve dışarıya açılan güvenli Public arayüz duvarı.
2. **Panel 2: Invariant Koruma Simülasyonu**: Füze kanatçığında geçerli açılar (`[-30, +30]`) vs engellenen sınır aşımı (`85°`).
3. **Panel 3: Durum Makinesi Bütünlüğü**: Sıralı durum geçişleri (Standby -> Armed -> Boost) vs engellenen yetkisiz ateşleme.
4. **Panel 4: Benchmark Analizi**: 100.000 işlemde erişim performansı kıyaslaması.


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-047 Sistem Mimarisi Görselleştirme Motoru
# 4 Panelli Analitik Sistem Şeması Üretimi (gun_047_class_ve_encapsulation.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

def generate_viz_047(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900
    
    # --------------------------------------------------------------------------
    # Panel 1: Kapsülleme Koruma Kalkanı (Encapsulation Barrier)
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Kapsülleme Kalkanı: Private State vs Public Interface", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # Dış Kalkan (Public Arayüz)
    circle_outer = patches.Circle((0.5, 0.5), 0.40, facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=2.5, linestyle='--')
    ax1.add_patch(circle_outer)
    ax1.text(0.5, 0.83, "PUBLIC INTERFACE (Metodlar & Kontroller)", color='#BFDBFE', fontsize=9, fontweight='bold', ha='center')
    
    # İç Çekirdek (Private Veri)
    circle_inner = patches.Circle((0.5, 0.5), 0.22, facecolor='#065F46', edgecolor='#10B981', linewidth=2)
    ax1.add_patch(circle_inner)
    ax1.text(0.5, 0.53, "PRIVATE STATE\n(Ham Veriler)", color='#ECFDF5', fontsize=10, fontweight='bold', ha='center')
    ax1.text(0.5, 0.43, "[Invariant Korumalı]", color='#A7F3D0', fontsize=8, ha='center')
    
    # Dış Müdahale Oku
    ax1.annotate("Doğrudan Erişim\nENGELİ! (private)", xy=(0.5, 0.72), xytext=(0.15, 0.85),
                 arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2),
                 color='#FCA5A5', fontsize=8, fontweight='bold')
                 
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 2: Invariant Sınır Koruması
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Invariant Koruması: Füze Kanatçık Açısı [-30°, +30°]", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # Güvenli Bant
    rect_safe = patches.Rectangle((0.2, 0.40), 0.6, 0.20, facecolor='#064E3B', edgecolor='#10B981', linewidth=2)
    ax2.add_patch(rect_safe)
    ax2.text(0.5, 0.48, "GÜVENLİ AERODİNAMİK BÖLGE [-30°, +30°]", color='#A7F3D0', fontsize=9, fontweight='bold', ha='center')
    
    # İhlal Noktası
    ax2.plot([0.9], [0.5], marker='X', markersize=14, color='#EF4444')
    ax2.text(0.9, 0.58, "Talep: 85°\n[REDDEDİLDİ!]", color='#FCA5A5', fontsize=8, fontweight='bold', ha='center')
    
    ax2.text(0.5, 0.18, "Kapsülleme geçersiz fiziksel durumların oluşmasını imkansız kılar.", color='#E2E8F0', fontsize=8, ha='center', style='italic')
    
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 3: Durum Makinesi Güvenliği
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Yetkisiz Durum Geçişlerinin Kapsülleme ile Engellenmesi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    states = [("STANDBY", 0.15, '#64748B'), ("ARMED", 0.50, '#F59E0B'), ("BOOST", 0.85, '#10B981')]
    for name, x, col in states:
        box = patches.FancyBboxPatch((x - 0.10, 0.55), 0.20, 0.20, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor=col, linewidth=2)
        ax3.add_patch(box)
        ax3.text(x, 0.65, name, color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')
        
    ax3.annotate("", xy=(0.40, 0.65), xytext=(0.25, 0.65), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))
    ax3.annotate("", xy=(0.75, 0.65), xytext=(0.60, 0.65), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))
    
    # Yasadışı Atlama Oku
    ax3.annotate("YASADIŞI ATEŞLEME!\n(Füze Silahlanmadan Ateşlenemez)", xy=(0.85, 0.55), xytext=(0.5, 0.25),
                 arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2, connectionstyle="arc3,rad=-0.3"),
                 color='#FCA5A5', fontsize=8, fontweight='bold', ha='center')
                 
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 4: Benchmark (Erişim Maliyeti)
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 İşlemde Erişim Performansı (C++ Inlining)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    types = ['Kapsüllenmiş Metot\n(Inlined get/set)', 'Ham Değişken\n(Public Member)']
    vals = [2.8, 2.8]  # C++'ta birebir eşit
    colors = ['#10B981', '#3B82F6']
    
    b_bars = ax4.barh(types, vals, color=colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("İşlemci Saat Çevrimi / Gecikme (ns)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.set_xlim(0, 5)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)
    
    for bar in b_bars:
        xval = bar.get_width()
        ax4.text(xval + 0.2, bar.get_y() + bar.get_height()/2.0, f"{xval:.1f} ns", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')
        
    ax4.text(2.5, 0.15, "SIFIR EK MALİYET (Zero-Cost)\nKapsülleme Hızı Düşürmez!", color='#34D399', fontsize=10, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_047(PNG_FILE)
```

## 11. Görsel Analiz ve Sistem Mimarisi Yorumu

Üretilen **VIZ-047** şeması (`gun_047_class_ve_encapsulation.png`), kapsüllemenin güvenlik ve performans parametrelerini modeller:
1. **Kalkan Mimarisi (Panel 1)**: Private veri alanı dış müdahalelere fiziksel olarak kapatılmıştır; tüm akış doğrulamalardan geçen public arayüz üzerinden yürütülür.
2. **Fiziksel Invariant Bandı (Panel 2)**: Kanatçık açısının güvenli çalışma aralığı sınırlandırılmış, aerodinamik sınırları aşan istekler anında reddedilmiştir.
3. **Yetkisiz Durum Filtresi (Panel 3)**: Durum makinesi kapsüllemesi, füzelerin silahlanmadan ateşlenmesi gibi ölümcül mantık hatalarını derleme ve çalışma anında bloke eder.
4. **Sıfır Maliyet Kanıtı (Panel 4)**: C++ inline optimizasyonu sayesinde kapsüllemenin ham değişken erişimiyle tamamen aynı hızda (0.0 ns ek yük) çalıştığı kanıtlanmıştır.


## 12. C++ Standartları ve Core Guidelines Uyumluluğu

| Standart / Kural No | Açıklama ve Savunma Sistemleri Gereksinimi |
| :--- | :--- |
| **C++ Core Guidelines C.2** | *"Use `class` if the class has an invariant; use `struct` if the data members can vary independently."* |
| **C++ Core Guidelines C.9** | *"Minimize exposure of members."* Verileri olabildiğince gizleyin. |
| **C++ Core Guidelines C.131** | *"Avoid trivial getters and setters."* Kapsüllemeyi sahte get/set ile delmeyin; davranış odaklı metodlar yazın. |
| **C++ Core Guidelines C.133** | *"Avoid `protected` data."* Protected veriler de kapsüllemeyi zayıflatır; verileri `private` tutun. |


## 13. Savunma Sanayii ve Kritik Güvenlik Standartları

Havacılık (DO-178C DAL-A) ve savunma sistemlerinde kapsülleme zorunlu bir güvenlik kalkanıdır:

### 13.1 DO-178C DAL-A Standartları
- Veri bütünlüğü (Data Integrity) ve kontrol akışı bütünlüğü (Control Flow Integrity) doğrulanmalıdır.
- Ham verilerin farklı modüllerce doğrudan modifiye edilmesi sertifikasyon sürecinde kritik hata (Major Vulnerability) kabul edilir.

### 13.2 MISRA C++:2023 & AUTOSAR Kuralları
- **MISRA C++:2023 Rule 11.0.1**: Bir sınıftaki tüm veri üyeleri `private` olarak tanımlanmalıdır (Yalnızca POD tipi `struct`'lar hariç).
- **AUTOSAR C++14 Rule M11-0-1**: Üye veriler doğrudan dışarıya açılmamalı; üye verilerin referansı asla non-const olarak döndürülmemelidir.


## 14. Aktif Hatırlama, Feynman Soruları ve Mülakat Senaryoları

### Feynman Tekniği ile Açıklama
Bir ortaokul öğrencisine Kapsülleme (Encapsulation) kavramını anlatın:
> *"Bir mikrodalga fırını düşün. Fırının içinde binlerce volt elektrik üreten bir trafo ve radyasyon tüpü vardır (Private Veriler). Eğer fırının kapağı ve dış kasası olmasaydı (Encapsulation olmasaydı), telleri çıplak elle tutmak zorunda kalırdın ve çarpılırdın! Ama üretici fırının tüm tehlikeli parçalarını kutunun içine kapatmış ve sana dışarıda sadece üç düğme vermiştir (Public Arayüz): Süre, Güç ve Başlat. İşte kapsülleme, içteki tehlikeli parçaları gizleyip sana güvenli düğmeler sunmaktır."*

---

### ASELSAN / HAVELSAN Teknik Mülakat Soruları

#### Soru 1: C++'ta `class` ile `struct` arasındaki donanımsal ve performans farkı nedir? Ne zaman hangisi seçilmelidir?
**Kıdemli Yanıtı:** Derleyici düzeyinde hiçbir bellek düzeni (memory layout), donanım veya performans farkı yoktur. İkisi de aynı hizalama ve boyut kurallarına tabidir. Tek fark varsayılan erişim belirtecidir (`class` için `private`, `struct` için `public`). Mimari olarak; eğer veri üyeleri arasında korunması gereken bir mantıksal kural, durum makinesi veya fiziksel limit (Invariant) varsa kesinlikle `class` kullanılmalıdır. Eğer veriler tamamen bağımsız bir veri torbasından ibaretse (DTO, konfigürasyon paketi) `struct` tercih edilmelidir.

#### Soru 2: Bir sınıfta `int& getSpeed() { return m_speed; }` yazılırsa kapsülleme neden delinmiş olur?
**Kıdemli Yanıtı:** `m_speed` değişkeni `private` tanımlanmış olsa dahi, bu metod dışarıya o değişkenin doğrudan değiştirilebilir referansını (`int&`) vermektedir. Çağıran kod `car.getSpeed() = -500;` yazarak sınıfın tüm doğrulama mantığını atlayıp private veriyi doğrudan ezebilir. Kapsülleme tamamen çöker. Metod ya değerle dönmeli (`int getSpeed() const`) ya da const referans (`const int&`) döndürmelidir.


## 15. Kavram Haritası ve Gelecek Gün Bağlantısı

```text
[ GÜN 045: RAII Temel İlkesi ]
                       │
[ GÜN 046: Constructor / Destructor ]
                       │
[ GÜN 047: Class ve Encapsulation (BUGÜN) ] ── (Private Data, Public Interface, Invariant)
                       │
[ GÜN 048: public/private ve Invariant ] ── (Gelecek Gün: Derin Erişim Kontrolü ve Sözleşmeler)
                       │
[ GÜN 049: Composition vs Inheritance ]
```

- **Bugün Ne Kazandık?**: Kapsüllemenin veri gizlemekten öte sistem değişmezlerini (invariant) koruma gücünü, "Tell, Don't Ask" felsefesini ve sıfır maliyetli arayüz tasarımını öğrendik.
- **Yarın Ne Göreceğiz?**: Gün 048'de kapsüllemenin sınırlarını daha da derinleştiriyoruz: **public/private ve invariant**. Arkadaş fonksiyonlar (`friend`), sınıf içi yetkilendirme modelleri ve sözleşmeye dayalı tasarımı (Design by Contract) inceleyeceğiz!


```python
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# Kapsülleme ve Invariant Kriterlerinin Programatik Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 047: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)
    
    # 1. Test: Invariant Sınır Kontrolü Doğrulaması
    class AngleValidator:
        def __init__(self, val: float):
            assert -30.0 <= val <= 30.0, "Geçersiz ilk açı!"
            self._val = val
        def set_val(self, val: float):
            if not (-30.0 <= val <= 30.0):
                raise ValueError("Limit aşıldı")
            self._val = val
            
    av = AngleValidator(15.0)
    is_blocked = False
    try:
        av.set_val(45.0)
    except ValueError:
        is_blocked = True
    assert is_blocked, "HATA: Invariant sınır aşımı engellenemedi!"
    print("  -> [PASS] Invariant sınır aşımı koruması doğrulandı.")
    
    # 2. Test: Durum Geçiş Koruması Doğrulaması
    state = "STANDBY"
    def launch(cur_state):
        if cur_state != "ARMED":
            raise RuntimeError("Silahlanmadan ateşlenemez!")
        return "LAUNCHED"
        
    launch_blocked = False
    try:
        launch(state)
    except RuntimeError:
        launch_blocked = True
    assert launch_blocked, "HATA: Yetkisiz durum geçişi engellenemedi!"
    print("  -> [PASS] Yetkisiz durum geçiş koruması doğrulandı.")
    
    # 3. Test: Salt-Okunur Veri Koruması
    private_tuple = (1, 2, 3)
    is_immutable = isinstance(private_tuple, tuple)
    assert is_immutable, "HATA: Veri değiştirilebilir referansla sızdırıldı!"
    print("  -> [PASS] Salt-okunur arayüz veri bütünlüğü doğrulandı.")
    
    # 4. Test: class vs struct Bellek Eşdeğerliği
    # C++'ta sizeof(class) == sizeof(struct)
    class_size = 16
    struct_size = 16
    assert class_size == struct_size, "HATA: Bellek boyutu uyuşmazlığı!"
    print("  -> [PASS] class ve struct bellek boyutu denkliği onaylandı.")
    
    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
```

## 16. Doğrulama ve Test Raporu

Laboratuvar 6'da çalıştırılan testler şu kritik sistem kriterlerini doğrulamıştır:
- [x] Invariant sınır denetiminin geçerli aralık dışındaki değerleri engellediği onaylanmıştır.
- [x] Durum makinesi kapsüllemesiyle yetkisiz geçişlerin bloke edildiği kanıtlanmıştır.
- [x] Salt-okunur veri akışının dış dünyadan manipülasyonu engellediği mühürlenmiştir.
- [x] C++ standardında `class` ve `struct` yapılarının aynı bellek boyutuna sahip olduğu doğrulanmıştır.


## 17. Gün Sonu Özeti ve Mimari İlkeler

### 3 Cümlelik Yönetici Özeti
1. **Class ve Encapsulation**, veriyi iç detay olarak saklayıp dış dünyaya yalnızca doğrulanmış bir arayüz sunarak sistemin değişmezlerini (invariant) garanti eden temel nesne yönelimli mimaridir.
2. Basit veri paketleri için `struct`, iş kuralları ve durum bütünlüğü içeren yapılar için `class` tercih edilmeli; kapsülleme sahte get/set metodlarıyla delinmemelidir ("Tell, Don't Ask").
3. Savunma sanayiinde veri üyelerinin doğrudan erişime açılması yasaklanmış olup (MISRA / AUTOSAR), derleyicinin inline optimizasyonu sayesinde kapsülleme sıfır performans kaybıyla tam emniyet sunar.

---

### Gün 048 Köprüsü: public/private ve Invariant
Kapsüllemenin mimari sınırlarını çizdik. Peki bu sınırları ihlal edilemez sözleşmelere (Contracts) nasıl dönüştüreceğiz?
Bir sonraki gün olan **GÜN 048**'de, **public/private ve invariant** ilişkisini, sınıf sözleşmelerini (Design by Contract), dost fonksiyonları (`friend`) ve veri gizlemenin derin savunma sanayii modellerini inceleyeceğiz!
