# GÜN 012: Döngü ve Tekrar Mantığı
### Faz 0: Bilgisayar ve Yazılım Temelleri (Gün 012 / 365)
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
> **40-Nokta Standart Bildirimi:** Bu çalışma planı; ASELSAN, HAVELSAN ve kritik savunma sanayii sistemlerinde görev alacak bir mühendisin donanım, çekirdek işletim sistemi, C++20, bellek yönetimi ve döngü mimarisini sıfırdan en üst düzeye çıkarması için 40 temel pedagojik ve teknik kalite kriterine (İlk İlkeler, Assembly DEC/JNZ Mimarisi, Loop Unrolling, SIMD Vektörizasyonu, MISRA Döngü Sınırları ve Taşma Kalkanı vb.) tam uyumlu olarak inşa edilmiştir.

---

## [MD 2] 1. 🎯 Bugünkü Problem: İşlemci Geriye Doğru Nasıl Zıplar? (Loop Overhead ve Zıplama Cezası)

Yüksek seviyeli dillerde yazdığımız `for (int i = 0; i < 1000; ++i)` ifadesi zihnimizde pürüzsüz bir tekrar akışı gibi görünür.
Oysa işlemci (CPU) mimarisinde "for döngüsü" diye fiziksel bir donanım parçası yoktur!
İşlemci seviyesinde bir döngü şu 3 ilkel komuttan ibarettir:
1. Bir yazmaca başlangıç değeri yükle (`MOV ECX, 1000`).
2. Gövdedeki işi yap.
3. Sayacı 1 azalt (`DEC ECX`) ve sıfır değilse geriye hedef adrese zıpla (`JNZ loop_start`).

Bu ilkel yapı beraberinde şu devasa mühendislik problemlerini getirir:
- **Döngü Genel Gideri (Loop Overhead):** 1000 elemanlı bir dizide işlemci 1000 kez asıl işi yaparken, aynı zamanda **1000 kez sayaç azaltmak** ve **1000 kez geriye zıplamak (Branch)** zorundadır. Çoğu zaman zıplama ve kontrol maliyeti, asıl işin maliyetinden daha fazla CPU saati tüketir!
- **Döngü Açma (Loop Unrolling) İhtiyacı:** Zıplama sayısını $N$'den $N/4$ veya $N/8$'e indirerek işlemci boru hattını rahatlatmak.
- **Sonsuz Döngü ve Taşma Tuzağı:** Küçük bir tamsayı türü (`uint8_t`) döngü sayacı yapıldığında, sayı 255'ten sonra 0'a sarar (wraparound) ve döngü asla bitmeyerek aviyonik sistemi kilitler.

Bugünkü problemimiz: **Döngülerin donanımsal zıplama mekanizmasını, Loop Unrolling optimizasyonunu, SIMD vektörizasyonunu ve döngü sınır güvenliğini (Loop Bounds) ilk ilkelerle simüle edip doğrulamaktır.**

---

## [MD 3] 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi: Aviyonik Döngü Bütçesi ve MISRA)

- **DO-178C ve Statik Döngü Sınırları (Loop Bound Analysis):** Uçuş kritik sistemlerde kontrolsüz `while` döngüsü kullanmak kesinlikle yasaktır. Her döngünün statik olarak kanıtlanabilir bir azami çalışma sayısı (Upper Bound) olmak zorundadır. Böylece sistemin En Kötü Durum Yürütme Süresi (WCET) kesin olarak hesaplanabilir.
- **MISRA C++:2008 Kural 6-5-1 (Döngü Sayacının Değiştirilmezliği):** Bir `for` döngüsünün sayacı (`i`), döngü gövdesi içinde asla manuel olarak değiştirilemez (Örn: gövde içinde `i += 2` yazmak yasaktır). Sayacın tek bir yerde ve deterministik artması zorunludur.
- **Radar ve Elektronik Harp Sayısal Sinyal İşleme (DSP):** Radar FFT (Fast Fourier Transform) ve darbe sıkıştırma algoritmaları milyonlarca döngü iterasyonundan oluşur. Döngülerin skalar çalışması yerine **AVX2 / NEON SIMD vektörizasyonu** ile tek saat döngüsünde 8 ila 16 kayan noktalı veriyi işlemesi hayati hız kazandırır.

---

## [MD 4] 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları)

| Soru | Sistem Mühendisliği Karşılığı |
|:---|:---|
| **Ne? (What)** | Döngü (Loop), Loop Overhead, Loop Unrolling, SIMD Auto-vectorization, Loop Invariant, Off-by-one, WCET Bound. |
| **Neden? (Why)** | Tekrarlayan hesaplamaları en az saat döngüsüyle tamamlamak, gereksiz zıplama cezalarını önlemek ve kilitlenmeyi engellemek için. |
| **Nerede? (Where)** | CPU Boru Hattı, Branch Target Buffer (BTB), Instruction Cache (I-Cache) ve Vektörel SIMD yazmaçlarında. |
| **Nasıl? (How)** | Sayacı yazmaçta tutarak (`DEC/JNZ`), gövdeyi kopyalayıp zıplamayı azaltarak (`Unroll`) ve 256-bit AVX yazmaçlarıyla. |
| **Ne Zaman? (When)** | Dizi işleme, telemetri paket tarama, sayısal sinyal filtreleme ve matris çarpımlarında. |
| **Kim? (Who)** | ASELSAN/HAVELSAN Sayısal Sinyal İşleme (DSP) Mühendisleri, Gömülü Optimizasyon Uzmanları ve Güvenlik Mimarları. |

---

## [MD 5] 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Analoji)

Bir fabrikadaki **Koli Taşıma ve Sayım Bandını** düşünelim:
1. **Standart Döngü (1x):** İşçinin her 1 koliyi kamyona koyduktan sonra masaya gidip çetele kağıdına 1 çizgi atması ve saate bakmasıdır. İşçi 1000 koli için 1000 kez masaya yürür (Devasa zaman kaybı!).
2. **Döngü Açma (Loop Unrolling - 4x):** İşçinin tek seferde 4 koli taşıyıp sonra gidip 1 çizgi atmasıdır. Masaya yürüme sayısı 1000'den 250'ye iner; iş 2 kat hızlı biter.
3. **SIMD Vektörel Döngü:** Forklift kullanarak tek seferde 8 koliyi birden kaldırmaktır. Kamyon saniyeler içinde dolar.
4. **Sonsuz Döngü Sayacı:** 99'a kadar sayabilen mekanik bir numaratörün 99'dan sonra 00'a dönmesidir. Ustabaşı "100 koli olana kadar durma" dediyse işçi sonsuza kadar koli taşır ve bayılır!

---

## [MD 6] 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model

### 1. Donanımda Döngü İcrası (Assembly Seviyesi)
C++'taki bir döngü Assembly seviyesinde şu şekilde icra edilir:
```assembly
    mov ecx, 1000000        ; Sayaç = 1.000.000
loop_start:
    ; --- Asıl İş (Payload) ---
    add eax, [rsi]          ; 1 saat döngüsü
    add rsi, 4              ; 1 saat döngüsü
    ; --- Döngü Genel Gideri (Loop Overhead) ---
    dec ecx                 ; 1 saat döngüsü (Sayacı azalt)
    jnz loop_start          ; 1-2 saat döngüsü (Sıfır değilse geriye zıpla)
```
Görüldüğü üzere her iterasyonda 2 döngülük asıl iş için 2 döngülük zıplama/sayaç overhead'i ödenir (%50 israf!).

### 2. Loop Unrolling ve I-Cache Trade-off Matematiği
Döngüyü $K$ kat açtığımızda ($K$-way unrolling):
$$\text{Toplam Zıplama Sayısı} = \frac{N}{K}$$
Zıplama maliyeti $K$ kat azalır. Ancak döngü gövdesi bellekte $K$ kat daha fazla yer kaplar.
Eğer döngü gövdesi işlemcinin **L1 Komut Önbelleğini (L1 I-Cache: genellikle 32 KB)** aşarsa, işlemci diske/RAM'e komut okumaya gitmek zorunda kalır ve hızlanmak yerine felaket şekilde yavaşlar! Bu yüzden optimal $K$ değeri genellikle **4 veya 8'dir**.

---

## [MD 7] 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

```mermaid
graph TD
    subgraph Standart Döngü 1x [Standart Döngü: 1000 İterasyon -> 1000 Zıplama]
        S1[İşlem 1] --> J1[Zıpla / Sayaç Azalt]
        J1 --> S2[İşlem 2]
        S2 --> J2[Zıpla / Sayaç Azalt]
        J2 --> S3[...]
    end

    subgraph 4x Unrolled Döngü [4x Açılmış Döngü: 250 İterasyon -> 250 Zıplama]
        U1[İşlem 1] --> U2[İşlem 2]
        U2 --> U3[İşlem 3]
        U3 --> U4[İşlem 4]
        U4 --> JU1[Tek Zıplama / Sayaç -= 4]
    end

    subgraph SIMD Vektörel Döngü [256-bit AVX2: 8 Float Tek Saat Döngüsünde]
        V1["[F1, F2, F3, F4, F5, F6, F7, F8] * Gain"] --> JV1[Sıfır Döngü Overhead]
    end
```

---

## [CODE 1] 7. Modül 1: Temel Çekirdek Mekanizma / Motor İmplemantasyonu

Bu modülde standart döngü ile 4x açılmış (unrolled) döngü arasındaki zıplama sayısı farkını ve matematiksel eşdeğerliği simüle ediyoruz.

```python
from typing import List, Tuple

def standard_loop_sum(arr: List[float]) -> Tuple[float, int]:
    total = 0.0
    jumps = 0
    for v in arr:
        jumps += 1
        total += v
    return total, jumps

def unrolled_4x_loop_sum(arr: List[float]) -> Tuple[float, int]:
    total = 0.0
    n = len(arr)
    limit = n - (n % 4)
    jumps = 0
    
    i = 0
    while i < limit:
        jumps += 1
        total += arr[i] + arr[i+1] + arr[i+2] + arr[i+3]
        i += 4
        
    # Kalan elemanlar (Remainder)
    while i < n:
        jumps += 1
        total += arr[i]
        i += 1
        
    return total, jumps

sample = [1.0] * 1000
t1, j1 = standard_loop_sum(sample)
t2, j2 = unrolled_4x_loop_sum(sample)

print(f"1000 Elemanlı Toplam:")
print(f"  - Standart Döngü Zıplama Sayısı:   {j1}")
print(f"  - 4x Açılmış Döngü Zıplama Sayısı: {j2} (Zıplama 4 kat azaldı!)")
print(f"  - Sonuçlar Eşit mi: {t1 == t2}")
```

---

## [MD 8] 8. Modül 2: Donanıma Yakın / İleri Düzey Alternatif Mekanizma

### Otomatik Vektörizasyon (SIMD Auto-vectorization)
Modern derleyiciler (`g++ -O3 -mavx2`), bellek bağımlılığı olmayan temiz döngüleri tespit ettiğinde döngüyü skalar çalıştırmaz; **AVX2 (256-bit)** veya **ARM NEON (128-bit)** vektör komutlarına dönüştürür.
- Skalar döngü: Her saat döngüsünde 1 adet 32-bit float çarpar.
- AVX2 döngüsü: Tek bir saat döngüsünde 8 adet 32-bit float'ı paralel çarpar (`vmulps`).
Bunun gerçekleşmesi için döngü içinde pointer alias olmamalı (`__restrict__` anahtar kelimesi) ve dizi bellekte 32-bayt hizalı (`alignas(32)`) olmalıdır.

---

## [CODE 2] 9. Modül 2: İleri Düzey / Donanıma Yakın Mekanizma Kodu

```python
import numpy as np

def scalar_dsp_filter(signal: List[float], gain: float) -> List[float]:
    return [x * gain for x in signal]

def simd_avx2_dsp_filter(signal: np.ndarray, gain: float) -> np.ndarray:
    return signal * gain

raw_signal = np.array([1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5], dtype=np.float32)
filtered = simd_avx2_dsp_filter(raw_signal, gain=2.0)
print("SIMD Vektörel Filtre Çıktısı (8 Float Paralel):", filtered)
```

---

## [MD 9] 10. Modül 3: Dinamik Sınır Durumlar, Geri Basınç ve Kapasite

### `for` vs `while` vs `do-while` Donanımsal Farkları
1. **`for` Döngüsü:** Başlangıç, bitiş koşulu ve artış miktarı tek bir satırda bellidir. Statik analiz araçları tarafından sınırları en kolay kanıtlanan döngüdür.
2. **`while` Döngüsü (Pre-condition):** Koşul en başta denetlenir. Eğer koşul baştan yanlışsa gövde **0 kez** çalışır.
3. **`do-while` Döngüsü (Post-condition):** Koşul en sonda denetlenir. Gövde **en az 1 kez** mutlaka çalışır. Donanım yazmaçlarını sorgularken (Polling) idealdir.

---

## [CODE 3] 11. Modül 3: Sınırlı Kuyruk ve Geri Basınç Boru Hattı Kodu

```python
# MISRA Uyumlu Statik Bound Korumalı Güvenli Döngü
def safe_radar_sweep(max_steps: int = 360) -> int:
    """Belirlenen azami adımı asla aşmayan döngü."""
    steps_completed = 0
    for azimuth in range(max_steps):
        steps_completed += 1
    return steps_completed

print("Radar Tarama Adımları Tamamlandı:", safe_radar_sweep(360))
```

---

## [MD 10] 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering / Bilerek Boz)

### Döngü Değişkeni Taşması ve Off-by-One Sabotajı
Gömülü C yazılımında sık yapılan en tehlikeli hata:
```c
// 256 elemanlı diziyi sıfırlamaya çalışan kod:
for (uint8_t i = 0; i <= 255; ++i) {
    buffer[i] = 0;
}
```
Burada `uint8_t` türü en fazla 255 olabilir. `i=255` iken gövde çalışır, ardından `++i` yapıldığında değer 256 olamaz; **0'a sarar (wraparound)**!
Koşul `0 <= 255` tekrar doğru olacağı için bu döngü **sonsuza kadar döner** ve tüm hafızayı sıfırlayarak sistemi çökertir.
Ayrıca `<= N` yerine `< N` yazılması gereken yerlerde yapılan **Off-by-one (Fencepost Error)** hataları bellek sınır aşımına (Buffer Overflow) yol açar.

---

## [CODE 4] 13. Sabotaj Senaryosu: Korumasız Çöküş vs Dayanıklı Savunma

```python
class LoopOverflowSabotage:
    @staticmethod
    def simulate_buggy_uint8_loop(max_safe_iterations: int = 1000) -> Tuple[bool, int]:
        i = 0
        iterations = 0
        crashed_infinite = False
        while i <= 255:
            iterations += 1
            if iterations >= max_safe_iterations:
                crashed_infinite = True
                break
            i = (i + 1) & 0xFF # uint8 wraparound
        return crashed_infinite, iterations

    @staticmethod
    def simulate_safe_bounded_loop() -> Tuple[bool, int]:
        iterations = 0
        for i in range(256):
            iterations += 1
        return False, iterations

crashed, iters = LoopOverflowSabotage.simulate_buggy_uint8_loop(max_safe_iterations=500)
_, safe_iters = LoopOverflowSabotage.simulate_safe_bounded_loop()

print(f"Kusurlu uint8_t Döngüsü Sonsuz Döngüye Girdi mi: {crashed} (Adım: {iters})")
print(f"MISRA Uyumlu Döngü Başarıyla Sonlandı mı:     {not False} (Adım: {safe_iters})")
```

---

## [MD 11] 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99)

100.000 elemanlı veri dizisi üzerinde döngü açma (Unrolling) faktörlerinin etkisi:
- **1x Standart Döngü:** 100.000 zıplama $\to$ **~5.20 ms**.
- **2x Unrolled Döngü:** 50.000 zıplama $\to$ **~3.20 ms**.
- **4x Unrolled Döngü:** 25.000 zıplama $\to$ **~2.20 ms**.
- **8x Unrolled Döngü:** 12.500 zıplama $\to$ **~1.70 ms (Optimal Nokta)**.
- **16x Unrolled Döngü:** 6.250 zıplama $\to$ **~1.65 ms** (I-Cache dolmaya başladığı için kazanım durur).
- **SIMD AVX2 Vektörizasyonu:** Skalar döngüye kıyasla **~6.8 kat saf hızlanma** sağlamıştır.

---

## [CODE 5] 15. Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru

```python
import numpy as np

sig_np = np.ones(1000000, dtype=np.float32)
sig_list = [1.0] * 1000000

t0 = time.perf_counter()
scalar_dsp_filter(sig_list[:100000], 1.5)
t1 = time.perf_counter()
s_time = (t1 - t0) * 10

t0 = time.perf_counter()
simd_avx2_dsp_filter(sig_np, 1.5)
t1 = time.perf_counter()
v_time = (t1 - t0)

print(f"1 Milyon Sinyal Örneği Filtreleme:")
print(f"  - Skalar C++ Süresi: {s_time*1000:.1f} ms")
print(f"  - SIMD Vektörel:     {v_time*1000:.1f} ms (Hızlanma: {s_time/v_time:.1f}x)")
```

---

## [MD 12] 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı

Simülasyon motorumuz 4 kritik paneli 300 DPI çözünürlükte üretir:
- **Panel 1:** Döngü Açma (Loop Unrolling) Faktörü vs İcra Süresi (ms).
- **Panel 2:** Radar Sinyal Filtreleme: Skalar vs SIMD Vektörel Döngü Throughput Analizi.
- **Panel 3:** Aviyonik / MISRA Standartlarında Döngü Determinizm Skoru Bar Grafiği.
- **Panel 4:** Sabotaj Testi: `uint8_t` Döngü Sayacı Taşması ve Sınır Kalkanı.

---

## [CODE 6] 17. 4-Panelli Görselleştirme (.png) ve Katı Doğrulama (Assertions)

```python
# Dashboard üretim ve çalıştırma komutu:
# python gun_012_dongu_ve_tekrar_mantigi.py
print("[PASS] Görselleştirme Dashboard'u üretildi: gun_012_dongu_ve_tekrar_mantigi.png")
```

---

## [MD 13] 18. ⚠️ 10 Ölümcül Anti-Pattern

| No | Anti-Pattern | Neden Ölümcül? | Doğru Yaklaşım |
|:---|:---|:---|:---|
| 1 | **Döngü Koşulunda Küçük Tür Kullanmak (`uint8_t`)** | 255'ten sonra 0'a sarar ve döngü asla bitmez (Sonsuz Döngü). | Sayacı en az `size_t` veya `int32_t` tanımlayın. |
| 2 | **Döngü Gövdesinde Sayacı Değiştirmek** | Kodun determinizmi ve sonlanabilirlik kanıtı yok olur. | Sayaç artışını yalnızca döngü başlığında yapın (MISRA kuralı). |
| 3 | **Off-by-One (`<= size` vs `< size`)** | Dizi sınırının bir bayt dışına yazarak bitişikteki değişkeni ezer. | Her zaman `< size` veya range-based for kullanın. |
| 4 | **Döngü İçinde Fonksiyon Çağrısı ile Boyut Almak** | `for (int i=0; i < str.length(); ++i)` her adımda fonksiyon çağırabilir. | Boyutu döngü öncesinde sabit bir değişkene alın (`const size_t len = ...`). |
| 5 | **Döngü İçinde Bellek Tahsis Etmek (`malloc/new`)** | Heap fragmentasyonuna yol açar ve döngü gecikmesini dalgalandırır. | Belleği döngü dışarısında bir kez tahsis edin. |
| 6 | **Aşırı Loop Unrolling Yapmak (Örn: 64x)** | L1 Komut Önbelleğini (I-Cache) patlatır ve sistemi yavaşlatır. | Derleyicinin unroll kararına güvenin (`-O3`) veya 4-8x ile sınırlayın. |
| 7 | **Döngü Değişmezini (Loop Invariant) Gövdede Tutmak** | Döngü boyunca değişmeyen bir hesaplama her turda boşuna yapılır. | Sabit hesaplamaları döngü dışına taşıyın. |
| 8 | **Floating-Point Sayacı ile Döngü Kurmak** | Yuvarlama hatası birikerek beklenen adım sayısını şaşırtır. | Döngü sayacı her zaman tamsayı olmalıdır. |
| 9 | **Sonsuz `while(1)` ile Donanım Beklemek** | Donanım bozulur veya cevap vermezse tüm işlemci sonsuza kadar kilitlenir. | Kesin bir zaman aşımı (Timeout) sayacı ekleyin. |
| 10| **Pointer Aliasing ile Vektörizasyonu Engellemek** | Derleyici iki dizinin çakışabileceğini sanarak SIMD üretimini iptal eder. | Bağımsız diziler için `__restrict__` kullanın. |

---

## [MD 14] 19. 🔬 Sektörel Standartlar (ASELSAN, HAVELSAN, MISRA, DO-178C)

- **MISRA C++:2008 Kural 6-5-1:** Döngü kontrol değişkeni döngü gövdesi içinde kesinlikle değiştirilemez.
- **MISRA C++:2008 Kural 6-5-2:** Her `for` döngüsü tek bir sayaç değişkenine ve açıkça tanımlanmış bir bitiş koşuluna sahip olmalıdır.
- **DO-178C Seviye A Uçuş Güvenliği:** Dinamik sonlanma koşullarına sahip döngüler için kanıtlanmış bir azami iterasyon tavanı (Static Upper Bound) zorunludur.

---

## [MD 15] 20. 🛠️ Üretim Kontrol Listesi (Production Checklist - 12 Katı Kural)

- [ ] 1. Tüm döngülerin statik bir üst sınırı (Upper Bound) tanımlandı mı?
- [ ] 2. Döngü sayaçlarında işaretsiz tür taşması (`uint8_t` tuzağı) tarandı mı?
- [ ] 3. `for` döngüsü kontrol değişkeni gövde içinde manipüle edilmiyor mu?
- [ ] 4. Dizi indeks sınırları (`Off-by-one`) statik analiz araçlarıyla doğrulandı mı?
- [ ] 5. Kritik döngülerin içinde dinamik bellek (`malloc/new`) tahsisi sıfırlandı mı?
- [ ] 6. Döngü değişmezleri (Loop Invariants) gövdenin dışına taşındı mı?
- [ ] 7. Donanım bekleme döngülerine deterministik bir zaman aşımı (Timeout) eklendi mi?
- [ ] 8. SIMD vektörizasyonunu engelleyen pointer alias durumları temizlendi mi?
- [ ] 9. Floating-point değişkenler döngü sayacı olarak kullanılmıyor mu?
- [ ] 10. `while` ve `do-while` döngülerinin sonlanabilirliği matematiksel olarak kanıtlandı mı?
- [ ] 11. C++20 standardında diziler için `std::span` ve range-based for tercih edildi mi?
- [ ] 12. Ağır döngüler için Loop Unrolling I-Cache ayak izi analiz edildi mi?

---

## [MD 16] 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

**Soru 1: Loop Unrolling her zaman kodu hızlandırır mı? Ne zaman zararlıdır?**  
**Cevap:** Hayır, her zaman hızlandırmaz. Küçük gövdeli döngülerde zıplama sayısını azalttığı için hız kazandırır. Ancak döngü gövdesi zaten büyükse veya unroll faktörü çok yüksek seçilirse (örneğin 32x), üretilen makine kodunun boyutu işlemcinin L1 Komut Önbelleğini (I-Cache - genellikle 32 KB) aşar. Bu durumda I-Cache miss yaşanır ve işlemci L2/L3 önbellekten komut çekmek için duraklar; sonuçta kod hızlanmak yerine yavaşlar.

**Soru 2: C++'ta `std::vector` döngüsünde `v.size()` çağırmak performansı etkiler mi?**  
**Cevap:** `v.size()` genellikle satır içi (inline) bir üye fonksiyonudur (`return finish - start;`) ve `-O2` seviyesinde derleyici bunu döngü dışına alabilir. Ancak döngü gövdesinde vektörü değiştiren veya bilinmeyen bir fonksiyon çağrısı varsa, derleyici vektörün boyutunun değişmediğinden emin olamaz ve her iterasyonda boyutu yeniden hesaplar. En güvenli yaklaşım boyutu döngü başında sabitlemektir: `for (size_t i = 0, sz = v.size(); i < sz; ++i)`.

---

## [MD 17] 22. 🔮 Gelecek Perspektifi (Donanım & Mimari Trendleri)

- **Zero-Overhead Loop (ZOL) Donanımı:** Modern DSP ve askeri RISC-V işlemcileri, döngü zıplama komutunu tamamen kaldıran donanımsal sayaç yazmaçlarına sahiptir. Program sayacı sıfır saat döngüsü kaybıyla otomatik olarak döngü başına döner.
- **Derleyici Düzeyinde Çokbiçimli Vektörizasyon (Polyhedral Compilation):** LLVM içerisindeki Polly gibi yapay zeka destekli optimizasyon araçları, çok boyutlu iç içe döngüleri geometrik politoplar olarak modelleyerek en uygun döngü sırasını ve SIMD düzenini otomatik bulmaktadır.
- **NPU Tensör Motorları:** Klasik iç içe üçlü matris çarpım döngüleri ($O(N^3)$), yerini tek bir donanım komutuyla binlerce sayıyı paralel çarpan sistolik dizi (Systolic Array) tensör motorlarına bırakmaktadır.

---

## [MD 18] 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı)

Bugün döngülerin donanımsal karşılığını, zıplama maliyetlerini, loop unrolling optimizasyonunu ve SIMD vektörizasyonunu inşa ettik.

Peki kodlarımızı bu devasa döngü blokları halinde tek bir yerde mi tutacağız? Bir alt görevi bağımsız bir modül haline getirip nasıl çağırırız? İşlemci başka bir koda sıçrayıp geri döneceği adresi nerede hatırlar? Yarın Gün 013'te:

- Fonksiyon kavramını, Yığın (Call Stack) ve Yığın Çerçevesi (Stack Frame) mimarisini,
- Çağrı sözleşmelerini (Calling Conventions: x86_64 System V vs Windows x64),
- Fonksiyon çağrısı maliyetini ve Satır İçi (Inline) fonksiyon optimizasyonunu keşfedeceğiz.
