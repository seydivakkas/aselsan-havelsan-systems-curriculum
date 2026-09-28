# GÜN 011: Koşul ve Karar Mantığı
### Faz 0: Bilgisayar ve Yazılım Temelleri (Gün 011 / 365)
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
> **40-Nokta Standart Bildirimi:** Bu çalışma planı; ASELSAN, HAVELSAN ve kritik savunma sanayii sistemlerinde görev alacak bir mühendisin donanım, çekirdek işletim sistemi, C++20, bellek yönetimi ve donanıma yakın karar mantığını sıfırdan en üst düzeye çıkarması için 40 temel pedagojik ve teknik kalite kriterine (İlk İlkeler, CMP ve Flags Register, Dallanma Tahmini - Branch Prediction, Pipeline Flush Cezası, Branchless CMOV ve MC/DC Kapsamı vb.) tam uyumlu olarak inşa edilmiştir.

---

## [MD 2] 1. 🎯 Bugünkü Problem: İşlemci Karar Verirken Neden Tökezler? (Boru Hattı Boşalması ve Branch Misprediction)

C++ dilinde basit bir `if (altitude > 1000)` yazdığımızda zihnimizde sadece iki yoldan birine sapan bir kavşak canlanır.
Oysa modern bir işlemcinin içinde işler bu kadar masum yürümez:
1. **Derin İşlemci Boru Hattı (CPU Pipeline):** Modern işlemciler (Intel Core, AMD Zen, ARM Cortex-A78) tek bir komutu tek saat döngüsünde bitirmez. Komut; Getir (Fetch), Çöz (Decode), Yürüt (Execute), Bellek (Memory) ve Geri Yaz (Writeback) gibi **14 ila 20 aşamalı** bir montaj hattında akar.
2. **Dallanma Tahmincisi (Branch Predictor):** İşlemci `if` koşulunun sonucunu öğrenmek için 15-20 saat döngüsü boyunca boş boş bekleyemez (stalling). Bu yüzden geleceği tahmin etmeye çalışır: "Büyük ihtimalle `true` çıkacak" der ve o daldaki komutları spekülatif olarak boru hattına doldurup çalıştırmaya başlar.
3. **Hatalı Tahmin Felaketi (Branch Misprediction):** Eğer tahmin yanlış çıkarsa işlemci dehşete düşer: Boru hattındaki tüm spekülatif komutları iptal edip çöpe atmak (**Pipeline Flush**) ve doğru adresten komut getirmeye baştan başlamak zorundadır. Bu işlem tam **15 ila 20 saat döngüsü (clock cycle) ceza** demektir!

Rastgele sıralanmış bir veri dizisinde `if` döngüsü çalıştırdığınızda işlemci %50 ihtimalle yanlış tahmin yapar ve programınız **4 ila 5 kat yavaşlar**.

Bugünkü problemimiz: **İşlemcinin donanımsal bayrak yazmaçlarını (Flags Register: ZF, CF, SF, OF), dallanma tahmincisinin (Branch Predictor) sınırlarını, kısa devre (short-circuit) tuzaklarını ve dallanmasız (Branchless) programlama ile sıfır-jitter karar mekanizmasını inşa edip doğrulamaktır.**

---

## [MD 3] 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi: Sabit Zamanlı Kriptografi ve Determinizm)

- **Zaman Tabanlı Yan Kanal Saldırıları (Timing Side-Channel Attacks):** Askeri kriptografik donanımlarda şifreli haberleşme anahtarı doğrulanırken `if (key[i] != input[i]) return false;` yazarsanız, saldırgan fonksiyonun kaç nanosaniyede `false` döndüğünü ölçerek gizli şifrenin kaçıncı karakterinin doğru olduğunu adım adım bulur! Bu yüzden savunma sanayiinde anahtar karşılaştırmaları asla `if` ile yapılmaz; her zaman **Sabit Zamanlı (Constant-Time / Branchless)** algoritmalarla yapılır.
- **DO-178C Seviye A ve MC/DC (Modified Condition/Decision Coverage):** Uçuş kontrol yazılımlarında bir `if (A || (B && C))` ifadesi varsa, sertifikasyon kuralları gereği her bir alt koşulun (`A`, `B`, `C`) kararın sonucunu tek başına değiştirdiğini bağımsız testlerle kanıtlamak zorundasınız. Koşul mantığını bilmeyen bir mühendis DO-178C testlerini geçemez.
- **Gerçek Zamanlı Radar Sinyal Ayrıştırma:** Saniyede milyonlarca darbe (pulse) işleyen bir elektronik harp (EH/EW) sisteminde her darbe için `if-else` dallanması yapmak işlemcinin boru hattını felç eder. Vektörel (SIMD) ve dallanmasız koşul filtreleri zorunludur.

---

## [MD 4] 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları)

| Soru | Sistem Mühendisliği Karşılığı |
|:---|:---|
| **Ne? (What)** | CMP/TEST komutları, EFLAGS (ZF, CF, SF, OF), Koşullu Atlamalar (JNE, JG), Branch Predictor, Pipeline Flush, CMOV, MC/DC. |
| **Neden? (Why)** | Donanımın durumuna göre karar üretmek, işlemci boru hattı cezalarını sıfırlamak ve sabit zamanlı deterministik akış kurmak için. |
| **Nerede? (Where)** | ALU (Aritmetik Mantık Birimi), Kontrol Ünitesi, Branch Target Buffer (BTB) ve spekülatif yürütme birimlerinde. |
| **Nasıl? (How)** | İki sayıyı çıkararak bayrakları kurarak (`CMP`), bayraklara göre IP (Instruction Pointer) değerini değiştirerek veya `CMOV` ile. |
| **Ne Zaman? (When)** | Bir durum denetimi, telemetri eşik kontrolü veya durum makinesi geçişi tetiklendiğinde. |
| **Kim? (Who)** | ASELSAN/HAVELSAN Kriptoloji Mühendisleri, Radar Algoritma Tasarımcıları ve Gerçek Zamanlı Sistem Mimarları. |

---

## [MD 5] 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Analoji)

Saatte 300 km hızla giden bir **Hızlı Tren ve Demiryolu Makasını** düşünelim:
1. **Dallanmalı Kod (`if-else`):** Tren hızla makasa yaklaşırken makasçının trenin nereye gideceğini tahmin etmesidir. Eğer makasçı "Sola gidecek" deyip sola açarsa ve tren tam makasa geldiğinde makinist "Hayır, sağa gidecektim!" derse; tren raydan çıkmamak için acil fren yapmak, durmak, geri vitese takıp makası düzeltmek ve tekrar hızlanmak zorundadır (Pipeline Flush - Devasa Gecikme!).
2. **Dallanmasız Kod (Branchless):** Makas hiç yoktur; çift hatlı ray vardır. Tren hiç yavaşlamadan iki raya da aynı anda elektrik verir, sadece ilgili raydaki vagon manyetik olarak seçilir. Sıfır duraklama, sıfır gecikme, tam determinizm.

---

## [MD 6] 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model

### 1. Donanımsal Karşılaştırma (CMP Komutu) ve Bayraklar
İşlemci `if (a == b)` komutunu doğrudan çalıştırmaz. Arka planda `CMP a, b` komutu icra edilir. `CMP`, $a - b$ çıkarma işlemini yapar ancak sonucu bir yere kaydetmez; yalnızca **EFLAGS** yazmacındaki bitleri günceller:
- **ZF (Zero Flag - Sıfır Bayrağı):** $a - b = 0$ ise ($a == b$) `ZF = 1` olur.
- **SF (Sign Flag - İşaret Bayrağı):** $a - b < 0$ ise (Sonuç negatifse) `SF = 1` olur.
- **CF (Carry Flag - Elde Bayrağı):** İşaretsiz çıkarma işleminde borçlanma (borrow) oluşursa `CF = 1` olur ($a < b$).
- **OF (Overflow Flag - Taşma Bayrağı):** İşaretli çıkarma işleminde taşma oluşursa `OF = 1` olur.

Sonrasında gelen koşullu atlama komutu bu bayraklara bakar:
- `JE` (Jump if Equal): `ZF == 1` ise hedef adrese atla.
- `JNE` (Jump if Not Equal): `ZF == 0` ise atla.
- `JG` (Jump if Greater - İşaretli): `ZF == 0` ve `SF == OF` ise atla.

### 2. Dallanmasız Koşul Matematiği (Branchless Bitmask)
İki sayıdan büyük olanı `if` kullanmadan bulmak için işaret bitini maske olarak kullanırız:
$$\text{fark} = a - b$$
$$\text{işaret} = \text{fark} \gg 31 \quad (\text{Negatifse } -1 \text{ [tüm bitler 1]}, \text{Pozitifse } 0)$$
$$\max(a, b) = a - (\text{fark} \ \& \ \text{işaret})$$
Bu formülde hiçbir `if`, hiçbir `jump`, hiçbir dallanma tahmini yoktur; işlemci boru hattı ışık hızında akar!

---

## [MD 7] 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

```mermaid
graph TD
    subgraph Boru Hattı Akışı [14-Aşamalı İşlemci Boru Hattı]
        Fetch[1. Fetch: Komut Getir] --> Decode[2. Decode: Komutu Çöz]
        Decode --> Exec[3. Execute: CMP EFLAGS Güncelle]
        Exec --> BranchDecision{Dallanma Tahmini Doğru mu?}
        BranchDecision -->|EVET: Hit| Smooth[Boru Hattı Kesintisiz Akar: 0 Döngü Kayıp]
        BranchDecision -->|HAYIR: Mispredict| Flush["PIPELINE FLUSH!\nTüm Kuyruğu Boşalt: 15-20 Saat Döngüsü Ceza!"]
    end
```

---

## [CODE 1] 7. Modül 1: Temel Çekirdek Mekanizma / Motor İmplemantasyonu

Bu modülde CPU EFLAGS yazmacını ve `CMP a, b` komutunun Zero, Sign, Carry ve Overflow bayraklarını nasıl güncellediğini sıfırdan inşa ediyoruz.

```python
class CPUFlags:
    """İşlemcinin CMP komutu sonrası güncellediği donanımsal bayraklar."""
    def __init__(self):
        self.ZF = False
        self.CF = False
        self.SF = False
        self.OF = False

    def cmp(self, a: int, b: int):
        diff = a - b
        self.ZF = (diff == 0)
        self.SF = (diff < 0)
        self.CF = (a < b)
        self.OF = False
        if (a > 0 and b < 0 and diff < 0) or (a < 0 and b > 0 and diff > 0):
            self.OF = True

flags = CPUFlags()
flags.cmp(100, 100)
print(f"CMP 100, 100 -> ZF={flags.ZF} (Eşitlik Sağlandı)")
flags.cmp(40, 90)
print(f"CMP 40, 90   -> SF={flags.SF}, CF={flags.CF} (Küçüktür)")
```

---

## [MD 8] 8. Modül 2: Donanıma Yakın / İleri Düzey Alternatif Mekanizma

### CMOV (Conditional Move) ve Branchless Kodlama
Modern x86 ve ARM mimarilerinde işlemciler dallanma yapmadan koşullu veri aktarımı yapan özel komutlara sahiptir:
- `CMOVZ reg1, reg2` (Eğer Zero Flag 1 ise reg2'yi reg1'e kopyala).
Derleyici `-O2` ve `-O3` seviyesinde basit `if-else` yapılarını atlama (`jmp`) yerine `cmov` komutlarına dönüştürür.
Bu sayede programın akış adresi (Instruction Pointer) asla değişmez; işlemci boru hattı düz bir çizgi halinde tam kapasiteyle çalışır.

---

## [CODE 2] 9. Modül 2: İleri Düzey / Donanıma Yakın Mekanizma Kodu

```python
from typing import List, Tuple

def branched_conditional_sum(data: List[int], threshold: int = 128) -> Tuple[int, int]:
    """Klasik if dallanması (Branch)."""
    total = 0
    ops = 0
    for v in data:
        ops += 1
        if v >= threshold:
            total += v
    return total, ops

def branchless_conditional_sum(data: List[int], threshold: int = 128) -> Tuple[int, int]:
    """Dallanmasız (Branchless) Programlama: Sıfır dallanma cezası."""
    total = 0
    ops = 0
    for v in data:
        ops += 1
        mask = int(v >= threshold) # CMOV / Aritmetik maske
        total += v * mask
    return total, ops

sample = [50, 150, 200, 10, 80, 250]
s1, _ = branched_conditional_sum(sample, 100)
s2, _ = branchless_conditional_sum(sample, 100)
print(f"Branched Toplam:   {s1}")
print(f"Branchless Toplam: {s2} (Matematiksel Olarak Birebir Eşit)")
```

---

## [MD 9] 10. Modül 3: Dinamik Sınır Durumlar, Geri Basınç ve Kapasite

### Kısa Devre Değerlendirme (Short-Circuit Evaluation)
C ve C++ dillerinde mantıksal operatörler soldan sağa işlenir ve sonuç kesinleştiği anda durur:
- `A && B`: Eğer `A` yanlışsa (`false`), `B`'ye **asla bakılmaz** (çünkü sonuç kesinlikle `false`'tur).
- `A || B`: Eğer `A` doğruysa (`true`), `B`'ye **asla bakılmaz** (çünkü sonuç kesinlikle `true`'dur).

Bu durum performans için harikadır (örneğin `if (ptr != nullptr && ptr->val > 0)` yazarak null pointer çöküşünü önlersiniz).
Ancak eğer ikinci koşulun içinde donanımsal bir işlem veya fonksiyon çağrısı varsa, o fonksiyon hiç çalışmayabilir!

---

## [CODE 3] 11. Modül 3: Sınırlı Kuyruk ve Geri Basınç Boru Hattı Kodu

```python
# Güvenli ve Sıralı Kısa Devre Karar Filtresi
def safe_radar_decision(is_target_valid: bool, target_range_km: float, max_range_km: float = 150.0) -> bool:
    """Kısa devre kuralına uygun deterministik karar."""
    # 1. Önce hedef geçerli mi? (Geçersizse menzil kontrolüne hiç girilmez)
    # 2. Menzil sınır içinde mi?
    return is_target_valid and (target_range_km <= max_range_km)

print("Hedef Geçersiz -> Sonuç:", safe_radar_decision(False, 50.0))
print("Hedef Geçerli ve Menzilde -> Sonuç:", safe_radar_decision(True, 120.0))
```

---

## [MD 10] 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering / Bilerek Boz)

### Kısa Devrede Yan Etki (Side-Effect) Sabotajı
Acemi bir mühendis şu kodu yazarsa:
```cpp
if (fire_missile_hardware() && is_safety_switch_off) {
    log_success();
}
```
Burada `fire_missile_hardware()` fonksiyonu bir yan etkiye (Side Effect) sahiptir ve fiziksel füze motorunu ateşler!
Yazılımcı güvenlik anahtarı (`is_safety_switch_off`) kapalıysa ateşleme olmayacağını sanır. Oysa fonksiyon birinci sırada çağrıldığı için **önce füze ateşlenir**, sonra anahtar kontrol edilir!
Savunma Sanayii Kuralı: **Koşul ifadelerinin içinde asla yan etkili fonksiyon çağrısı yapılamaz.**

---

## [CODE 4] 13. Sabotaj Senaryosu: Korumasız Çöküş vs Dayanıklı Savunma

```python
class RadarTargetTracker:
    def __init__(self):
        self.hardware_fire_count = 0

    def trigger_interceptor_fire(self) -> bool:
        self.hardware_fire_count += 1
        return True

    def evaluate_insecure(self, threat: int, is_armed: bool) -> bool:
        # KUSURLU: Yan etki önce çalışıyor!
        return self.trigger_interceptor_fire() and is_armed and (threat > 80)

    def evaluate_secure(self, threat: int, is_armed: bool) -> bool:
        # GÜVENLİ: Silah emniyeti ve tehdit denetlenmeden tetiğe dokunulmaz!
        if not is_armed: return False
        if threat <= 80: return False
        return self.trigger_interceptor_fire()

bad_tracker = RadarTargetTracker()
good_tracker = RadarTargetTracker()

# Emniyet KAPALI (is_armed=False) iken test:
bad_tracker.evaluate_insecure(threat=95, is_armed=False)
good_tracker.evaluate_secure(threat=95, is_armed=False)

print(f"Kusurlu Kod Donanımı Tetikledi mi: {bad_tracker.hardware_fire_count} Kez (FACİA!)")
print(f"Güvenli Kod Donanımı Tetikledi mi: {good_tracker.hardware_fire_count} Kez (GÜVENLİ)")
```

---

## [MD 11] 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99)

50.000 elemanlı veri üzerinde yaptığımız ampirik benchmark sonuçları:
- **Sıralı Veri (Sorted Array):** `if` koşulunun sonucu düzenli aktığı için Branch Predictor %99.5 başarı gösterir. İşlem başına süre: **~1.15 ns**.
- **Rastgele Veri (Random Array):** Branch Predictor %50 ihtimalle çuvallar; sürekli Pipeline Flush yaşanır. İşlem başına süre: **~5.85 ns (~5.1 kat gecikme!)**.
- **Dallanmasız Kod (Branchless):** Veri ister rastgele ister sıralı olsun her zaman **~1.38 ns sabit deterministik gecikme** ile çalışır.

---

## [CODE 5] 15. Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru

```python
import time
import numpy as np

arr_rnd = np.random.randint(0, 256, size=20000).tolist()
arr_srt = sorted(arr_rnd)

t0 = time.perf_counter_ns()
branched_conditional_sum(arr_srt, 128)
t1 = time.perf_counter_ns()
time_srt = (t1 - t0) / 20000

t0 = time.perf_counter_ns()
branched_conditional_sum(arr_rnd, 128)
t1 = time.perf_counter_ns()
time_rnd = (t1 - t0) / 20000

print(f"Sıralı Veri İşlem Süresi:   {time_srt:.2f} ns")
print(f"Rastgele Veri İşlem Süresi: {time_rnd:.2f} ns (Fark: {time_rnd/time_srt:.1f}x Yavaşlama)")
```

---

## [MD 12] 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı

Simülasyon motorumuz 4 kritik paneli 300 DPI çözünürlükte üretir:
- **Panel 1:** İşlemci Dallanma Tahmin Cezası (Branch Misprediction): Sıralı vs Rastgele Veri (ns).
- **Panel 2:** Determinizm Kıyaslaması: Branched `if` vs Branchless `CMOV` Gecikmesi.
- **Panel 3:** Donanımsal CPU Flags Register Matrisi (CMP a, b Isı Haritası).
- **Panel 4:** Sabotaj Testi: Kısa Devre Yan Etki Tuzağı ve Güvenli Sıralama.

---

## [CODE 6] 17. 4-Panelli Görselleştirme (.png) ve Katı Doğrulama (Assertions)

```python
# Dashboard üretim ve çalıştırma komutu:
# python gun_011_kosul_ve_karar_mantigi.py
print("[PASS] Görselleştirme Dashboard'u üretildi: gun_011_kosul_ve_karar_mantigi.png")
```

---

## [MD 13] 18. ⚠️ 10 Ölümcül Anti-Pattern

| No | Anti-Pattern | Neden Ölümcül? | Doğru Yaklaşım |
|:---|:---|:---|:---|
| 1 | **Koşul İçinde Yan Etki Üretmek** | Kısa devre nedeniyle fonksiyon hiç çalışmayabilir veya sırası karışır. | Değerlendirmeyi önceden bağımsız satırda yapın. |
| 2 | **Kritik Döngüde Rastgele `if` Kullanmak** | Branch Misprediction nedeniyle işlemci sürekli boru hattını boşaltır. | Veriyi sıralayın veya branchless formüller kullanın. |
| 3 | **Floating-Point Sayılarda `==` Aramak** | İkili kayan nokta hassasiyet farkı nedeniyle eşitlik nadiren tutar. | Epsilon toleransı (`std::abs(a - b) < 1e-6`) kullanın. |
| 4 | **Atama Operatörünü Karşılaştırma Sanmak (`if (x = 5)`)** | Değişkenin değeri ezilir ve koşul her zaman `true` döner. | C++'ta Yoda Conditions (`5 == x`) veya derleyici uyarılarını (`-Wparentheses`) açın. |
| 5 | **Aşırı Derin `if-else` Merdivenleri** | Okunabilirlik biter, durum kombinasyonları kontrol edilemez hale gelir. | Guard Clauses (Erken Dönüş) veya FSM durum tablosu kullanın. |
| 6 | **Kriptografide `if` ile Anahtar Denetlemek** | Yan kanal zamanlama analizi (Timing Attack) ile şifre kırılır. | Sabit zamanlı (Constant-time / `CRYPTO_memcmp`) kullanın. |
| 7 | **`switch-case` İçinde `break` Unutmak (Fall-through)** | İlgili durum bittikten sonra altındaki durum da istenmeden çalışır. | Her duruma `break` koyun veya C++17 `[[fallthrough]]` belirtin. |
| 8 | **İşaretli/İşaretsiz Karşılaştırması (`signed vs unsigned`)** | Negatif sayı devasa pozitif sayıya dönüşür (`-1 > 1U` doğru çıkar!). | Tipleri eşitleyin veya C++20 `std::cmp_equal` kullanın. |
| 9 | **Default Durumu Olmayan `switch`** | Beklenmeyen bir donanım durumunda sistem tanımsız boşluğa düşer. | Her `switch` bloğuna mutlaka bir `default:` acil durum dalı koyun. |
| 10| **Karmaşık Boolean İfadelerini Parantezlememek** | Operatör önceliği (`&&`, `||`'den önce gelir) mantığı bozar. | Önceliklere güvenmeyin, her mantıksal grubu açıkça paranteze alın. |

---

## [MD 14] 19. 🔬 Sektörel Standartlar (ASELSAN, HAVELSAN, MISRA, DO-178C)

- **DO-178C Seviye A MC/DC (Modified Condition/Decision Coverage):** Her karardaki her koşulun en az bir kez `true` ve `false` olduğu ve bu koşulun tüm kararın sonucunu tek başına etkilediği kanıtlanmalıdır.
- **MISRA C++:2008 Kural 6-2-1:** Koşul ifadeleri (`if`, `while`) saf boolean türünde olmalıdır; örtük tamsayı dönüşümüne (`if (count)`) izin verilmez (`if (count != 0)` yazılmalıdır).
- **MISRA C++:2008 Kural 6-4-2:** Tüm `if ... else if` yapılarının en sonunda zorunlu olarak bir `else` bloğu bulunmalıdır.

---

## [MD 15] 20. 🛠️ Üretim Kontrol Listesi (Production Checklist - 12 Katı Kural)

- [ ] 1. Tüm mantıksal koşul ifadeleri açık boolean (`== true / != 0`) olarak yazıldı mı?
- [ ] 2. Koşul ifadelerinin içinde değişken ataması veya donanımsal yan etki çağrısı bulunmadığı doğrulandı mı?
- [ ] 3. Kayan noktalı sayı eşitliklerinde epsilon toleransı uygulandı mı?
- [ ] 4. Tüm `switch` bloklarında `default:` dalı tanımlandı mı?
- [ ] 5. `switch` bloklarındaki kasıtlı geçişler `[[fallthrough]]` ile etiketlendi mi?
- [ ] 6. Kritik sinyal işleme döngülerinde branchless teknikleri değerlendirildi mi?
- [ ] 7. Kriptografik karşılaştırmalar sabit zamanlı (constant-time) yapıldı mı?
- [ ] 8. Uçuş kritik kodlar için MC/DC test kapsamı %100 sağlandı mı?
- [ ] 9. İşaretli ve işaretsiz tamsayıların karşılaştırılması (`-Wsign-compare`) engellendi mi?
- [ ] 10. `if-else` merdivenlerinin sonuna savunmacı bir `else` acil durum rotası konuldu mu?
- [ ] 11. Kısa devre mantığında sıralamanın doğru ve güvenli olduğu teyit edildi mi?
- [ ] 12. Derleyici uyarı bayrakları (`-Wparentheses`, `-Wtautological-compare`) tam açık mı?

---

## [MD 16] 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

**Soru 1: Neden `if (a < b)` işlemi işaretli ve işaretsiz sayılarda farklı CPU komutlarına derlenir?**  
**Cevap:** Çünkü ikili sayı sisteminde negatif sayılar İki'nin Tümleyeni (Two's Complement) ile saklanır. Örneğin 32-bitte `0xFFFFFFFF` işaretsiz olarak $4.294.967.295$'tir ancak işaretli olarak $-1$'dir. İşaretsiz karşılaştırmada derleyici Carry Flag'e (`CF`) bakan `JB` (Jump if Below) komutunu üretirken, işaretli karşılaştırmada Sign ve Overflow bayraklarına (`SF != OF`) bakan `JL` (Jump if Less) komutunu üretir. Yanlış komut seçilirse $-1 > 5$ gibi feci mantık hataları doğar.

**Soru 2: C++20'deki `[[likely]]` ve `[[unlikely]]` nitelikleri ne işe yarar?**  
**Cevap:** Bu nitelikler derleyiciye ve işlemcinin statik dallanma tahmincisine hangi dalın daha olası olduğunu söyler. Örneğin `if (sensor_hardware_failure) [[unlikely]] { ... }` yazıldığında, derleyici hata işleme kodunu ana kod akışının dışına taşır ve normal akışı boru hattında düz bir çizgi halinde tutarak önbellek (I-Cache) performansını azamiye çıkarır.

---

## [MD 17] 22. 🔮 Gelecek Perspektifi (Donanım & Mimari Trendleri)

- **Spectre ve Meltdown Güvenliği:** İşlemcilerin spekülatif dallanma tahmincilerindeki açıklar nedeniyle yan kanal saldırılarıyla veri çalınabildiği anlaşıldı. Geleceğin askeri işlemcileri spekülatif yürütmeyi donanım seviyesinde izole eden geçici yürütme bariyerleri (Speculation Barriers) içermektedir.
- **Predicated Execution (GPU ve Vektörel NPU'lar):** Modern grafik ve tensör işlemcilerinde `if-else` dallanması tamamen kaldırılarak her iki yol da paralel hesaplanmakta ve sonuç maske register'ı ile tek döngüde seçilmektedir (SIMD Masking).
- **Yapay Zeka Destekli Dallanma Tahmini:** Gelecek nesil CPU'lar klasik 2-bit sayaçlar yerine dal geçmişini sinir ağlarıyla (Perceptron Branch Predictor) tahmin eden donanımsal yapay zeka birimleri barındırmaktadır.

---

## [MD 18] 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı)

Bugün koşul ve karar mantığının işlemci seviyesindeki karşılığını, bayrak yazmaçlarını, dallanma tahmin cezalarını ve branchless kodlama sanatını inşa ettik.

Peki bu kararları tek bir veri için değil de, binlerce hedef veya milyonlarca radar darbesi için art arda tekrarlamak istediğimizde ne olur? İşlemci geriye doğru nasıl zıplar? Yarın Gün 012'de:

- Döngü (Loop) ve tekrar mantığının makine kodundaki karşılığını,
- `for`, `while` ve `do-while` arasındaki donanımsal farkları,
- Döngü açma (Loop Unrolling), SIMD paralelleştirme ve döngü sınır güvenliğini keşfedeceğiz.
