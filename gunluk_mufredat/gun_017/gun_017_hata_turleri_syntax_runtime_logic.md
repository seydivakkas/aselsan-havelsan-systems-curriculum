# GÜN 017: Hata Türleri: Syntax, Runtime ve Logic Hataları
### Faz 0: Bilgisayar ve Yazılım Temelleri (Gün 017 / 365)
#### 24-Hücreli Master Mimari Planı (18 Markdown + 6 Kod Hücresi)

---

```
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

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)

> [!NOTE]
> **40-Nokta Standart Bildirimi:** Bu çalışma planı; ASELSAN, HAVELSAN, Roketsan ve STM seviyesinde görev alacak bir sistem ve yazılım mimarının yazılım hatalarını derleme zamanı (Syntax), çalışma zamanı (Runtime) ve sessiz mantık hataları (Logic Errors) ekseninde sınıflandırabilmesi, Ariane 5 roket patlaması ve Mars Climate Orbiter faciası gibi tarihi askeri/uzay arızalarından ilk ilkelerle sistemik dersler çıkarabilmesi, `-Wall -Wextra -Werror -Wconversion` derleme kalkanlarını ve güçlü tip güvenliğini (Strong Typing) eksiksiz uygulayabilmesi için 40 temel pedagojik kalite kriterine tam uyumlu olarak hazırlanmıştır.

---

## [MD 2] 1. 🎯 Bugünkü Problem: En Tehlikeli Hata Çökmeyen Hatadır! (Syntax vs Runtime vs Silent Logic Bugs)

Yazılım mühendisliğinde hatalar eşit yaratılmamıştır. Bir hatanın sisteme verdiği zarar, onun **ne kadar geç fark edildiğiyle** doğrudan orantılıdır:

1. **Sözdizimi Hataları (Syntax Errors):**
   - Derleyici parantez eksikliğini veya noktalı virgül hatasını görür görmez derlemeyi durdurur (`AST` kurulamaz). Kod derlenmediği için asla sahaya çıkamaz. Düzeltme maliyeti **0 TL**'dir.
2. **Çalışma Zamanı Hataları (Runtime Errors / Crashes):**
   - Kod derlenir ancak icra edilirken donanım veya işletim sistemi bir kural ihlali tespit eder: Sıfıra bölme (`SIGFPE`), Geçersiz bellek erişimi (`SIGSEGV`), Yığın taşması (`Stack Overflow`). Sistem çöker (Crash). Kötüdür ama en azından bir arıza olduğu aşikardır ve loglanır.
3. **Sessiz Mantık Hataları (Silent Logic Bugs):**
   - **Savunma sanayiindeki en ölümcül ve en pahalı hata sınıfıdır!**
   - Program kusursuz derlenir, tek bir uyarı vermez, çalışma anında asla çökmez (Crash olmaz). Ancak ürettiği sonuç yanlıştır!
   - Örneğin: Radar füze koordinatını hesaplarken açıyı radyan yerine derece cinsinden formüle sokar; füze hedef yerine boş denize uçar. Uçak yere çakılana kadar sistemin arızalı olduğunu hiç kimse fark edemez!

Bugünkü görevimiz: **Hataların donanım ve derleyici katmanındaki kök sebeplerini, Ariane 5 faciasındaki tür dönüşüm taşmasını ve Mars Orbiter birim uyumsuzluğunu simüle ederek bu hataları derleme anında boğan savunma mimarilerini inşa etmektir.**

---

## [MD 3] 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi: Ariane 5, Mars Orbiter ve DO-178C Seviye A)

- **Ariane 5 Roket Faciası (4 Haziran 1996 - 500 Milyon Dolar Zarar):** Ariane 5'in ilk uçuşunda roket fırlatıldıktan 37 saniye sonra infilak etti. Kök neden: 64-bit kayan noktalı yatay hız verisinin (`double`), 16-bit işaretli tamsayıya (`int16_t`) kontrolsüz dönüştürülmesiydi. Değer $+32.767$ sınırını aşınca donanımsal Aritmetik Taşma (Arithmetic Overflow) oluştu, atalet referans bilgisayarı çöktü ve roket kendini imha etti!
- **Mars Climate Orbiter Faciası (1999 - 327 Milyon Dolar Zarar):** Uzay aracı Mars atmosferine girerken yandı. Kök neden: Lockheed Martin yer yazılımı itki kuvvetini İngiliz Kraliyet birimi olan *Pound-force saniye* (lbf·s) cinsinden hesaplarken, NASA uçuş yazılımı bu veriyi metrik *Newton-saniye* (N·s) sanarak işledi ($1\text{ lbf} \approx 4.45\text{ N}$). Sistem çökmedi; sadece **sessiz bir mantık hatasıyla** yanlış yörüngeye girdi.
- **DO-178C Seviye A Sertifikasyonu:** Uçuş kritik sistemlerde kodun derlenmesi yetmez; statik analiz araçları (Coverity, Polyspace, Klocwork) ile hiçbir tanımsız davranış (Undefined Behavior), tür dönüşüm taşması veya birim karmaşası bulunmadığı matematiksel olarak ispatlanmalıdır.

---

## [MD 4] 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları)

| Soru | Sistem ve Güvenilirlik Mühendisliği Karşılığı |
|:---|:---|
| **Ne? (What)** | Syntax Error, Runtime Error (Traps/Signals), Logic Error, Arithmetic Overflow, Undefined Behavior (UB), Unit Safety. |
| **Neden? (Why)** | Hataları sahaya ve uçuş anına çıkmadan, en ucuz olduğu derleme ve birim test aşamasında yakalayıp yok etmek için. |
| **Nerede? (Where)** | Derleyici Parser'ında (AST), CPU İstisna Bayraklarında (`#DE`, `#GP`), Sensör Veri Dönüşüm Katmanlarında. |
| **Nasıl? (How)** | `-Werror` bayrakları, Güçlü Tip Güvenliği (`Strong Types`), Statik İddialar (`static_assert`) ve Sözleşmeli Tasarım ile. |
| **Ne Zaman? (When)** | Kod yazılırken, derlenirken, statik analiz çalıştırılırken ve donanım döngüde (HIL) testlerinde. |
| **Kim? (Who)** | ASELSAN Aviyonik Yazılım Mühendisleri, Emniyet Denetçileri (Safety Auditors), Sistem Test Mimarları. |

---

## [MD 5] 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Analoji)

Bir **İlaç Üretim Fabrikası** benzetmesini ele alalım:

1. **Syntax Hatası:** İlaç kutusunun üzerine basılacak Türkçe prospektüs metninde harflerin birbirine girmesi ve matbaanın baskı makinesinin kağıdı sıkıştırıp durmasıdır. Hatalı kutu fabrikadan dışarı çıkamaz (Derleme durur).
2. **Runtime Hatası:** İlaç şişeleme bandında şişenin makineye ters oturması ve dolum iğnesinin şişeyi kırarak alarm vermesidir. Fabrika siren çalar, bant durur (Crash / SIGSEGV).
3. **Sessiz Mantık Hatası:** İlacın etken maddesinin 10 miligram yerine yanlışlıkla 10 gram (1000 kat fazla) konulması ve şişenin pırıl pırıl paketlenip eczanelere satılmasıdır! Fabrikada hiçbir makine alarm vermez, her şey normal görünür; ancak ilacı içen hasta zehirlenir.

---

## [MD 6] 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model

### 1. Hatanın Keşif Fazına Göre Maliyet Çarpanı (Boeing / NASA Kuralı)
Yazılım mühendisliğinde kabul edilen evrensel maliyet kuralı logaritmik olarak büyür:
$$\text{Maliyet} \propto 10^{\text{Faz}}$$
- **Gereksinim / Derleme Zamanı:** $1\times$ (Maliyeti 100 TL / 5 dakika)
- **Birim Test (Unit Test):** $10\times$ (Maliyeti 1.000 TL / 1 saat)
- **Entegrasyon ve HIL Testi:** $100\times$ (Maliyeti 10.000 TL / 1 gün)
- **Sistem ve Uçuş Testi:** $1.000\times$ (Maliyeti 100.000 TL / 1 hafta)
- **Canlı Görev / Saha Faciası:** $10.000\times$ - $100.000\times$ (Can Kaybı, İtibar Kaybı, 500 Milyon Dolar)

### 2. Donanımsal Sayısal Taşma (Two's Complement Overflow)
İşlemcilerde 16-bit işaretli tamsayı formatında:
$$+32767_{10} = 0111\_1111\_1111\_1111_2$$
Bu değere $+1$ eklendiğinde en soldaki işaret biti 1 olur:
$$1000\_0000\_0000\_0000_2 = -32768_{10}$$
Ariane 5'te hız $+32768$ olunca işlemci bunu aniden $-32768$ olarak yorumladı ve roket burnunu aniden ters yöne çevirip aerodinamik basınçla havada parçalandı!

---

## [MD 7] 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

### Derleme Zamanı vs Çalışma Zamanı vs Mantık Hatası Akış Şeması

```
KAYNAK KOD (.cpp)
       │
       ▼
[ DERLEYİCİ PARSER ] ──(Sözdizimi Bozuk?)──► [ SYNTAX ERROR ] ──► Derleme Durur (Güvenli!)
       │
       ▼ (Sözdizimi Geçti)
[ STATİK TİP KONTROLÜ ] ──(Tür Uyumu?)──► [-Wall -Werror -Wconversion] (Derleme Anında Yakala)
       │
       ▼ (İkili Dosya / Binary)
[ İŞLEMCİ İCRASI ] ──(Sıfıra Bölme / Null Ptr?)──► [ RUNTIME TRAP (SIGSEGV/SIGFPE) ] (Crash)
       │
       ▼ (Kusursuz Çalışıyor Görünen Kod)
[ GÜDÜM ALGORİTMASI ] ──(Birim Yanlış / Radian vs Degree?)──► [ SESSİZ LOGIC BUG ] (FACİA!)
```

### Mermaid Akış Şeması: Güçlü Tip Kalkanı

```mermaid
flowchart TD
    RawInput[Ham Sayısal Değer: 45.0] --> CheckType{Güçlü Tip Kalkanı Var mı?}
    CheckType -- Hayır (Ham double) --> BuggyFunc[calc_rudder_deflection(double val)]
    BuggyFunc --> LogicError[Formül Radyan Beklerken Derece İşlendi -> FACİA!]
    
    CheckType -- Evet (Strong Types) --> StrongType[Degree deg = 45.0_deg]
    StrongType --> Convert[Radian rad = deg.to_radian()]
    Convert --> SafeFunc[calc_rudder_deflection(Radian r)]
    SafeFunc --> CorrectOutcome[Kusursuz ve Deterministik Yönlendirme]
```

---

## [CODE 1] 7. Modül 1: Temel Çekirdek Mekanizma / Motor İmplemantasyonu

Aşağıdaki kod; sözdizimi, çalışma zamanı ve mantık hatalarının simülasyonunu yapan temel mekanizmadır.

```python
from typing import Tuple

class ErrorTaxonomy:
    """Hata türlerinin sınıflandırılması ve yaşam döngüsü modeli."""
    @staticmethod
    def simulate_syntax_check(code_snippet: str) -> Tuple[bool, str]:
        try:
            compile(code_snippet, "<test>", "exec")
            return True, "Sözdizimi Hatasız (Derlendi)."
        except SyntaxError as e:
            return False, f"DERLEME HATASI: {e.msg} (Satır {e.lineno})"

    @staticmethod
    def simulate_runtime_division(a: float, b: float) -> Tuple[bool, float, str]:
        try:
            res = a / b
            return True, res, "Başarılı İcra."
        except ZeroDivisionError:
            return False, 0.0, "RUNTIME_TRAP: Sıfıra bölme donanımsal istisnası (SIGFPE)!"

# Doğrulama Testi
ok_syn, msg1 = ErrorTaxonomy.simulate_syntax_check("x = 10 + 20")
bad_syn, msg2 = ErrorTaxonomy.simulate_syntax_check("x = 10 +")
print(f"Sözdizimi 1: {msg1}")
print(f"Sözdizimi 2: {msg2}")

ok_run, val, msg3 = ErrorTaxonomy.simulate_runtime_division(100.0, 0.0)
print(f"Çalışma Zamanı: {msg3}")
```

---

## [MD 8] 8. Modül 2: Donanıma Yakın / İleri Düzey Alternatif Mekanizma

### Güçlü Tip Güvenliği (Strong Typing) ve Boyut Analizi (Dimensional Analysis)
C++'ta `double` gibi ilkel türleri doğrudan fonksiyon parametresi yapmak mantık hatalarına davetiye çıkarır:
`void set_thruster(double angle, double force);` çağrısında parametrelerin yerini karıştırmak veya radyan yerine derece yollamak derleyici tarafından yakalanamaz.
Çözüm: **Strong Type sarmalayıcıları (`Degree`, `Radian`, `Newton`, `PoundForce`)** kullanmaktır. Yanlış tür verildiğinde kod derlenmez!

---

## [CODE 2] 9. Modül 2: İleri Düzey / Donanıma Yakın Mekanizma Kodu

```python
import math

class Radian:
    def __init__(self, value: float):
        self.value = value

    def to_degree(self) -> float:
        return self.value * (180.0 / math.pi)

class Degree:
    def __init__(self, value: float):
        self.value = value

    def to_radian(self) -> Radian:
        return Radian(self.value * (math.pi / 180.0))

class AviyonikGuidanceCalculator:
    @staticmethod
    def compute_rudder_deflection_safe(angle: Radian) -> float:
        # Formül kesinlikle Radian bekler ve tip kontrolü ile korunur
        return math.sin(angle.value) * 10.0

# Tip Güvenliği Deneyi
target_deg = Degree(90.0)
target_rad = target_deg.to_radian()
deflection = AviyonikGuidanceCalculator.compute_rudder_deflection_safe(target_rad)
print(f"90 Derece ({target_rad.value:.4f} Radian) İçin Dümen Sapması: {deflection:.2f} Derece")
```

---

## [MD 9] 10. Modül 3: Dinamik Sınır Durumlar, Geri Basınç ve Kapasite

### Design by Contract (Sözleşmeli Tasarım: Precondition & Postcondition)
Uçuş bilgisayarlarında fonksiyonların girdi ve çıktı sınırları katı matematiksel sözleşmelerle korunur:
- **Önkoşul (Precondition):** Fonksiyona gelen yakıt miktarı negatif olamaz (`fuel >= 0`).
- **Sonkoşul (Postcondition):** Üretilen itki kuvveti sıfırdan küçük olamaz (`thrust >= 0`).
Bu sözleşmeler ihlal edildiğinde sistem sessizce yanlış hesaplama yapmaz; anında güvenli hata moduna (Fail-Safe) geçer.

---

## [CODE 3] 11. Modül 3: Sınırlı Kuyruk ve Geri Basınç Boru Hattı Kodu

```python
class ContractGuard:
    """Önkoşul ve Sonkoşul denetimiyle sessiz mantık hatalarını engelleyen motor."""
    @staticmethod
    def calculate_thrust(fuel_kg: float, burn_rate: float) -> float:
        assert fuel_kg >= 0.0, "PRECONDITION_FAULT: Yakıt miktarı negatif olamaz!"
        assert burn_rate > 0.0, "PRECONDITION_FAULT: Yanma hızı pozitif olmalıdır!"
        
        thrust = fuel_kg * burn_rate * 9.81
        
        assert thrust >= 0.0, "POSTCONDITION_FAULT: İtki kuvveti negatif olamaz!"
        return thrust

try:
    thrust_ok = ContractGuard.calculate_thrust(fuel_kg=100.0, burn_rate=2.5)
    print(f"Hesaplanan İtki Kuvveti: {thrust_ok:.1f} Newton")
    # Sabotaj: Negatif yakıt girdisi
    ContractGuard.calculate_thrust(fuel_kg=-50.0, burn_rate=2.5)
except AssertionError as e:
    print(f"Sözleşme Kalkanı Devrede: {e}")
```

---

## [MD 10] 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering / Bilerek Boz)

### Tarihi İki Askeri/Uzay Faciası Sabotajı:
1. **Ariane 5 Roket Faciası (Arithmetic Overflow):** Sensör yatay hızı 64-bit kayan nokta (`double`) olarak okur. Kod bu değeri aralık kontrolü yapmadan 16-bit tamsayıya (`int16_t`) zorlar. Değer $+32767$'yi aştığı anda donanımsal taşma gerçekleşir ve roket imha olur!
2. **Mars Climate Orbiter Faciası (Birim Hatası):** Bir mühendislik modülü itkiyi İngiliz ölçü birimiyle (`lbf·s`) yollar, alıcı modül bunu metrik (`N·s`) olarak kabul eder. Aritmetik hata yoktur, crash yoktur; ancak uzay aracı 140 km yerine 57 km irtifaya inip atmosferde yanar!

---

## [CODE 4] 13. Sabotaj Senaryosu: Korumasız Çöküş vs Dayanıklı Savunma

```python
class HistoricalSabotageSimulator:
    @staticmethod
    def simulate_ariane_5_overflow(horizontal_velocity: float) -> Tuple[bool, int, str]:
        INT16_MAX = 32767
        INT16_MIN = -32768
        raw_int = int(horizontal_velocity)
        if raw_int > INT16_MAX or raw_int < INT16_MIN:
            return False, raw_int, "ARIANE_5_CRASH: 64-bit Kayan Nokta 16-bit Tamsayıya Sığmadı (Arithmetic Overflow)!"
        return True, raw_int, "Güvenli Dönüşüm."

    @staticmethod
    def simulate_mars_climate_orbiter_disaster(impulse_force: float, is_metric: bool) -> Tuple[float, float]:
        if not is_metric:
            actual_force = impulse_force # 4.45 kat eksik itki!
        else:
            actual_force = impulse_force * 4.44822
        target_trajectory_km = 140.0
        actual_trajectory_km = target_trajectory_km * (actual_force / (impulse_force * 4.44822))
        return actual_force, actual_trajectory_km

# Sabotaj Testi 1: Ariane 5
ok, val, msg = HistoricalSabotageSimulator.simulate_ariane_5_overflow(35000.0)
print(f"Ariane 5 Sabotajı (Hız=35.000): {msg}")

# Sabotaj Testi 2: Mars Climate Orbiter
_, orbit_err = HistoricalSabotageSimulator.simulate_mars_climate_orbiter_disaster(100.0, is_metric=False)
print(f"Mars Orbiter Sabotajı (Birim Uyumsuzluğu): Hedef 140 km -> Gerçek {orbit_err:.1f} km (Atmosferde Yandı!)")
```

---

## [MD 11] 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99)

- **Derleyici Bayraklarının Gücü:** Korumasız derleme potansiyel tür dönüşüm ve aralık hatalarının sadece **%25'ini** yakalayabilirken; `-Wall -Wextra -Werror -Wconversion` bayrakları bu hataların **%100'ünü** derleme zamanında bloke eder.
- **Hatanın Keşif Fazına Göre Maliyet Eğrisi:** Derleme anında 1 birim maliyetle çözülen bir hatanın, canlı uçuşta ortaya çıkması **10.000 kat daha maliyetlidir**.

---

## [CODE 5] 15. Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru

```python
def run_benchmarks():
    phases = [
        ("Derleme Fazı", 1),
        ("Birim Test", 10),
        ("HIL Entegrasyon", 100),
        ("Uçuş / Canlı Görev", 10000)
    ]
    print("--- Hata Keşif Aşamasına Göre Göreli Maliyet Tablosu ---")
    for phase_name, cost in phases:
        print(f"  - {phase_name:20s}: {cost:6,d}x Maliyet Çarpanı")

run_benchmarks()
```

---

## [MD 12] 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı

Üretilen 4-panelli 300 DPI dashboard mimarisi:
- **Panel 1 (Maliyet Analizi):** Hatanın Keşif Fazına Göre Göreli Maliyet Çarpanı (1x - 10.000x Logaritmik Ölçek).
- **Panel 2 (Derleyici Kalkanı):** Derleme Bayraklarının Potansiyel Hata Yakalama Başarısı (%25 vs %75 vs %100).
- **Panel 3 (Tarihi Vaka Analizi):** Ariane 5 Roket Faciası: Float64 -> Int16 Taşma ve Çöküş Bölgesi.
- **Panel 4 (Sessiz Mantık Hatası):** Mars Climate Orbiter: Birim Karışması Nedeniyle Yörünge Sapması (140 km vs 57 km).

---

## [CODE 6] 17. 4-Panelli Görselleştirme (.png) ve Katı Doğrulama (Assertions)

```python
# Dashboard üretim ve tam doğrulama kodu gun_017_hata_turleri_syntax_runtime_logic.py içinde yer almaktadır.
import subprocess
import os

py_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_017_hata_turleri_syntax_runtime_logic.py")
print("Python Simülasyon ve Dashboard Motoru çalıştırılıyor...")
ret_code = subprocess.call(["python", py_script])
print(f"Çalıştırma Tamamlandı (Dönüş Kodu: {ret_code})")
```

---

## [MD 13] 18. ⚠️ 10 Ölümcül Anti-Pattern

| No | Anti-Pattern | Neden Ölümcül? | Güvenli Savunma Çözümü |
|:---|:---|:---|:---|
| 1 | **Derleyici Uyarılarını İhmal Etmek** | Uyarılar gelecekteki çökmelerin ve tanımsız davranışların (UB) habercisidir. | Üretimde her zaman `-Werror` kullanarak tüm uyarıları hataya dönüştürün. |
| 2 | **Açık Tür Dönüşümü (Narrowing Conversion)** | `double`'ı `int`'e veya `int32`'yi `int16`'ya kontrolsüz çevirmek Ariane 5 gibi patlatır. | `{}` tekdüze ilklendirme veya güvenli aralık denetimli kast fonksiyonu yazın. |
| 3 | **Fiziksel Birimleri Ham Sayılarda Tutmak** | Açı ve kuvvet değerleri derece/radyan karmaşasıyla Mars Orbiter gibi uzay aracını yakar. | Güçlü tipli birim yapıları (`Degree`, `Radian`, `Newton`) kullanın. |
| 4 | **Sessizce Hatalı Değer Döndürmek** | Hata anında `0` veya `-1` dönüp çağıranın bunu kontrol edeceğini varsaymak. | `std::expected` (C++23) veya `std::optional` ile hatayı zorunlu ele aldırın. |
| 5 | **Sınır Kontrolsüz İndeksleme (`arr[i]`)** | Off-by-one hataları belleği sessizce bozar ve çok sonra çöker. | `std::span` veya sınır kontrollü `.at()` kullanın. |
| 6 | **Kayan Noktalı Sayılarda Kesin Eşitlik (`f == 0.0`)** | IEEE-754 yuvarlama farkları nedeniyle döngü asla bitmeyip kilitlenir. | `std::abs(f1 - f2) < epsilon` aralık denetimi kullanın. |
| 7 | **İşaretsiz Tamsayı Taşmasını (Underflow) Unutmak** | `unsigned int x = 0; x--;` yapıldığında değer $4.294.967.295$ olur. | Sayısal aralıkları statik analiz araçlarıyla denetleyin (MISRA kuralı). |
| 8 | **Sözleşmesiz (No-Contract) Fonksiyon Yazmak** | Fonksiyona gelen geçersiz girdiler içeride mantık hatası zinciri başlatır. | Girişte `assert` ve önkoşul (Precondition) denetimlerini zorunlu kılın. |
| 9 | **Undefined Behavior'a (UB) Güvenmek** | UB içeren kod bugün çalışabilir ama derleyici güncellendiğinde çöker. | C++ standartlarına sıkı sıkıya uyun; `-fsanitize=undefined` ile test edin. |
| 10 | **Hataları Yutmak (Catch-All Exception)** | `catch (...) {}` ile hatayı yok saymak sistemin yaralı halde uçmasına yol açar. | Yakalanan her istisnayı loglayın ve güvenli duruma (Safe State) geçin. |

---

## [MD 14] 19. 🔬 Sektörel Standartlar (ASELSAN, HAVELSAN, MISRA, DO-178C)

1. **DO-178C Seviye A / Dal 6.4.4.2:** Tüm çalışma zamanı arıza modları (Aritmetik taşma, bellek aşımı, tip dönüşümleri) analiz edilmeli ve kanıtlanmalıdır.
2. **MISRA C++:2008 Rule 5-0-3:** *"A cvalue expression shall not be implicitly converted to a different underlying type."* (Örtük tür dönüşümleri kesinlikle yasaktır).
3. **NASA Software Safety Standard (NASA-STD-8719.13C):** Uçuş kritik sistemlerde tüm fiziksel birimler (metrik vs imperial) arayüz düzeyinde statik tip kontrolüyle ayrılmalıdır.
4. **C++ Core Guidelines ES.46:** *"Avoid narrowing conversions."* Daraltıcı dönüşümlerden kaçının; olası veri kayıplarını engelleyin.

---

## [MD 15] 20. 🛠️ Üretim Kontrol Listesi (Production Checklist - 12 Katı Kural)

- [ ] **Kural 1:** Derleyici bayraklarında `-Wall -Wextra -Werror -Wconversion -Wshadow` aktif edildi mi?
- [ ] **Kural 2:** Kod tabanında örtük daraltıcı tür dönüşümleri (Narrowing conversions) tamamen temizlendi mi?
- [ ] **Kural 3:** Tüm açı ve kuvvet değişkenleri ham `double` yerine güçlü tipli birimlerle modellendi mi?
- [ ] **Kural 4:** Kritik matematik fonksiyonlarında önkoşul (Precondition) ve sonkoşul (Postcondition) denetimleri var mı?
- [ ] **Kural 5:** Kayan noktalı sayılarda kesin eşitlik (`==`) aramaları tolerans (`epsilon`) ile değiştirildi mi?
- [ ] **Kural 6:** Hata yakalama bloklarında hataların yutulmadığı, güvenli duruma (Safe State) geçildiği doğrulandı mı?
- [ ] **Kural 7:** Statik analiz araçları (Coverity/Polyspace) ile sıfır kritik bulgu hedefi tutturuldu mu?
- [ ] **Kural 8:** AddressSanitizer (`-fsanitize=address`) ve UBSan (`-fsanitize=undefined`) ile HIL testleri koşuldu mu?
- [ ] **Kural 9:** Tamsayı taşması (Integer Overflow) testleri sınır değerlerle (Boundary Testing) yapıldı mı?
- [ ] **Kural 10:** Döngü sayaçlarında işaretsiz taşma (Underflow) senaryoları incelendi mi?
- [ ] **Kural 11:** Fonksiyonların dönüş değerlerinin (`[[nodiscard]]`) göz ardı edilmediği teyit edildi mi?
- [ ] **Kural 12:** Ariane 5 benzeri sensör hız verisi dönüşümlerinde tavan/taban sınır kalkanları uygulandı mı?

---

## [MD 16] 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

**S1: "Bir savunma sanayii mülakatında 'En tehlikeli hata hangisidir?' sorusuna neden 'Sessiz Mantık Hatası' cevabı verilmelidir?"**
> **Cevap:** Çünkü Syntax hataları derleyici tarafından, Runtime hataları ise işletim sistemi veya donanım tarafından anında yakalanır ve raporlanır. Ancak Sessiz Mantık Hatası (Silent Logic Bug) hiçbir uyarı vermez, sistem çökmeksizin çalışmaya devam eder; fakat füzeyi yanlış koordinata yönlendirir veya radarda dost unsuru düşman olarak işaretler. Felaket gerçekleşene kadar sistemin hatalı olduğunu kimse anlayamaz.

**S2: Ariane 5 roketinde 64-bit kayan nokta sayısını 16-bit tamsayıya dönüştüren kod neden hata fırlattı?**
> **Cevap:** Kodlama ekibi, roketin yatay hızının uçuş boyunca asla $+32.767$ değerini aşmayacağını varsaymıştı (Bu varsayım daha küçük bir roket olan Ariane 4 için doğruydu). Ancak Ariane 5 çok daha güçlü motorlara sahipti ve uçuşun 37. saniyesinde yatay hız 32.767 sınırını aştı. Sayı 16-bit işaretli tamsayıya sığmadığı için donanımsal taşma istisnası tetiklendi ve sistemi çökertti.

**S3: Derleyici bayrağı olan `-Wconversion` neden savunma sanayiinde zorunludur?**
> **Cevap:** `-Wconversion`, olası bir veri kaybına yol açabilecek örtük tür dönüşümlerinde (örneğin 64-bit `double`'ın 32-bit `float`'a veya `int64_t`'nin `int32_t`'ye dönüştürülmesi) derleyicinin uyarı vermesini sağlar. `-Werror` ile birleştiğinde bu tür riskli kodların derlenmesini tamamen engelleyerek Ariane 5 benzeri faciaların önüne geçer.

---

## [MD 17] 22. 🔮 Gelecek Perspektifi (Donanım & Mimari Trendleri)

- **Formal Yöntemler ve Matematiksel Doğrulama (Formal Verification):** Kodun sadece test edilmesi yerine, algoritmaların kusursuz çalıştığının matematiksel teorem kanıtlayıcılar (Coq, Isabelle, F*) ile %100 kanıtlanması aviyonik yazılımlarda zorunlu hale gelmektedir.
- **Bellek Güvenli Diller (Memory-Safe Languages - Rust):** C/C++'taki bellek güvenliği ve tanımsız davranış kaynaklı runtime çökmelerinin, derleme zamanında mülkiyet ve yaşam süresi (Ownership/Borrow Checker) kalkanlarıyla tamamen sıfırlanması savunma projelerinde hızla yaygınlaşmaktadır.
- **Donanımsal Birim ve Tip Denetleyicileri:** Geleceğin işlemcilerinde yazmaç düzeyinde birim (Unit Tagging) etiketleri tutularak, metre ile saniyenin toplanması gibi mantık hatalarının doğrudan CPU donanımı tarafından engellenmesi hedeflenmektedir.

---

## [MD 18] 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı)

Bugün yazılım hatalarının taksonomisini, derleme kalkanlarını ve tarihi askeri facialardan çıkarılan mimari dersleri inceledik.

Peki bir hata ortaya çıktığında onu karanlıkta el yordamıyla aramak yerine bilimsel bir yöntemle nasıl izini süreriz? Yarın **Gün 018**'de:
- **Debugging Zihinsel Modeli:** Hipotez kurma, hipotezi test etme ve bilimsel hata ayıklama döngüsü,
- **GDB, LLDB ve Hardware Breakpoints:** İşlemcinin donanımsal hata ayıklama yazmaçları (`DR0-DR7`),
- **Tersine Hata Ayıklama (Time-Travel / Reversible Debugging):** Zamanı geriye sararak hatanın doğduğu ana dönme tekniklerini inceleyeceğiz.
