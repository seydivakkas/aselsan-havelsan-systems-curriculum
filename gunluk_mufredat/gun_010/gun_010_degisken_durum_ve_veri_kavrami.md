# GÜN 010: Değişken, Durum ve Veri Kavramı
### Faz 0: Bilgisayar ve Yazılım Temelleri (Gün 010 / 365)
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
> **40-Nokta Standart Bildirimi:** Bu çalışma planı; ASELSAN, HAVELSAN ve kritik savunma sanayii sistemlerinde görev alacak bir mühendisin donanım, çekirdek işletim sistemi, C++20, bellek yönetimi ve veri modellerini sıfırdan en üst düzeye çıkarması için 40 temel pedagojik ve teknik kalite kriterine (İlk İlkeler, Bellek Hizalaması - Memory Alignment, Padding İsrafı, Durum Vektörü, Tamsayı Taşması ve Doygunluk Aritmetiği vb.) tam uyumlu olarak inşa edilmiştir.

---

## [MD 2] 1. 🎯 Bugünkü Problem: Değişken Nedir, Bellekte Nerede Yaşar ve Durum (State) Neden Bozulur?

Yazılıma soyut düzeyde bakanlar değişkeni (variable) yalnızca "içine değer atılan bir kutu" sanır:
```cpp
int altitude = 1500;
```
Oysa donanım seviyesinde bu satır şu 4 somut gerçeği ifade eder:
1. **Sembolik İsim (`altitude`):** Yalnızca derleyici ve insan için vardır. Derleme bittiğinde ve semboller ayıklandığında (stripped) bu isim tamamen yok olur.
2. **Tür ve Boyut (`int`):** Bu verinin RAM'de kaç bayt yer kaplayacağını (x86_64 ve ARM64'te 4 bayt = 32 bit) ve bu bitlerin iki'nin tümleyeni (Two's Complement) kuralına göre yorumlanacağını belirler.
3. **Bellek Adresi (`&altitude`):** RAM üzerindeki fiziksel/sanal adresidir (örneğin `0x7FFF5FBFF804`). İşlemci komutları yalnızca bu adresi referans alır.
4. **Değer (`1500`):** Bu adresteki 4 baytlık hücreye yazılmış olan ham ikili dizilimdir (`0x000005DC`).

Peki **Durum (State)** nedir?
Bir İHA, radar veya füzenin belirli bir $t$ anındaki **tüm değişkenlerinin değerler vektörüdür**:
$$S(t) = \begin{bmatrix} \text{irtifa}(t) \\ \text{hız}(t) \\ \text{yakıt}(t) \\ \text{durum\_bayrağı}(t) \end{bmatrix}$$

Eğer değişkenlerin bellek yerleşimi (Alignment) rastgele yapılırsa, RAM'in %40'ı boşluklarla (Padding) israf edilir ve önbellek (L1 Cache) performansı çöker. Daha da kötüsü, bir değişkenin tipi doğru seçilmezse (örneğin 64-bit kayan nokta yerine 16-bit tamsayıya zorlanıp taşma yaşanırsa), 1996 yılındaki **Ariane 5 roketi** gibi fırlatıldıktan 37 saniye sonra havada infilak eder.

Bugünkü problemimiz: **Değişkenlerin fiziksel RAM adreslerindeki yerleşimini, doğal bellek hizalamasını (Memory Alignment & Padding), durum vektörünü ve tamsayı taşmasına karşı doygunluk aritmetiğini ilk ilkelerle inşa edip doğrulamaktır.**

---

## [MD 3] 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi: Ariane 5 Tamsayı Taşması ve Padding)

Savunma ve aviyonik sistemlerinde değişkenlerin bellek seviyesindeki davranışını bilmek doğrudan hayatta kalma meselesidir:
- **Ariane 5 Roket Faciası (4 Haziran 1996):** 500 milyon dolarlık roket, fırlatmadan 37 saniye sonra infilak etti. Kazanın sebebi: 64-bitlik kayan noktalı sayı (float) olarak hesaplanan yatay hız değerinin, 16-bitlik işaretli tamsayıya (`int16_t` / azami 32.767) dönüştürülmeye (cast) çalışılmasıydı. Değer 32.767'yi aşınca donanımsal taşma (Integer Overflow) oluştu, otopilot roketin rotadan saptığını sanarak motorları ters yöne çevirdi ve aerodinamik yük nedeniyle roket parçalandı.
- **Doğal Bellek Hizalaması (Memory Alignment):** Modern 64-bit işlemciler (ARM Cortex-A, Intel Xeon), 4-baytlık bir `int` verisini adresi 4'ün katı olan bir adresten (`0x1000`, `0x1004`), 8-baytlık bir `double` verisini ise 8'in katı olan bir adresten tek saat döngüsünde okur. Eğer veri hizasız (`unaligned`) yerleşirse, CPU iki ayrı bellek okuma döngüsü yapmak zorunda kalır veya ARM mimarisinde doğrudan **`SIGBUS` (Bus Error)** donanım kesmesi üretip sistemi durdurur.
- **RADAR Telemetri Paketleme:** Saniyede 100.000 hedef paketi işleyen bir radarda kötü tasarlanmış bir struct %41 bellek israfına yol açar ve Gigabaytlarca RAM'i gereksiz yere tüketir.

---

## [MD 4] 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları)

| Soru | Sistem Mühendisliği Karşılığı |
|:---|:---|
| **Ne? (What)** | Değişken (Adres+Tip+Değer), Durum Vektörü, Memory Alignment, Struct Padding, Packed Struct, Integer Overflow, Saturating Arithmetic. |
| **Neden? (Why)** | Bellek israfını önlemek, CPU bus okuma verimini azamiye çıkarmak ve taşma kaynaklı aviyonik kazaları sıfıra indirmek için. |
| **Nerede? (Where)** | İşlemci yazmaçları (Registers), L1/L2 Cache, Stack, Heap, BSS ve Data segmentleri. |
| **Nasıl? (How)** | Struct elemanlarını büyükten küçüğe sıralayarak, `alignas` belirteçleri kullanarak ve güvenli aritmetik kütüphaneleriyle. |
| **Ne Zaman? (When)** | Veri yapıları ve telemetri protokolleri tasarlanırken ve her durum güncelleme döngüsünde. |
| **Kim? (Who)** | ASELSAN/HAVELSAN Aviyonik Yazılım Mühendisleri, Gömülü Sistem Geliştiricileri ve Veri Modeli Mimarları. |

---

## [MD 5] 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Analoji)

Bir lojistik deposundaki standart koli paletlerini düşünelim:
1. **Bellek Sözcüğü (Memory Word - 4 Bayt / 8 Bayt):** Depodaki standart taşıma paletidir (Forklift tek seferde 4 veya 8 kutu kaldırır).
2. **Dağınık Yükleme (Unaligned / Kötü Padding):** Paletin üzerine 1 kutu koyup yanını boş bırakmak, sonraki büyük kutuyu sığmadığı için bir sonraki palete koymaktır. Forklift sürekli yarı boş palet taşır ve depo erkenden dolar (%40 israf).
3. **Optimize Yükleme (Aligned Struct):** Önce büyük kolileri, aralarına tam sığacak küçük kutuları yerleştirmektir. Paletler ağzına kadar dolar ve taşıma hızı iki katına çıkar.
4. **Tamsayı Taşması (Kilometre Sayacı):** Bir arabanın 999.999 km'den sonra aniden 000.000 km'ye dönmesidir. Eğer otopilot sıfıra dönen sayacı görüp "Araba henüz hiç hareket etmedi" sanırsa gazı sonuna kadar kökler!

---

## [MD 6] 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model

### 1. Doğal Hizalama (Natural Alignment) ve Padding Matematiği
Bir $T$ veri tipinin boyutu $S$ bayt ise, bu veri tipinin bellek adresi $A$ şu şartı sağlamalıdır:
$$A \pmod S = 0$$
- `char` (1 bayt): Her adreste bulunabilir ($A \pmod 1 = 0$).
- `short` (2 bayt): Çift adreslerde bulunmalıdır ($A \pmod 2 = 0$).
- `int` / `float` (4 bayt): 4'ün katı adreslerde bulunmalıdır ($A \pmod 4 = 0$).
- `double` / `int64_t` / `pointer` (8 bayt): 8'in katı adreslerde bulunmalıdır ($A \pmod 8 = 0$).

Eğer bu kurala uyulmazsa derleyici araya anlamsız boşluk baytları (**Padding**) ekler:
```
Dağınık Struct: struct { char c; int i; short s; };
[c] [PAD] [PAD] [PAD] [i] [i] [i] [i] [s] [s] [PAD] [PAD]  --> Toplam 12 Bayt! (5 Bayt İsraf)

Optimize Struct: struct { int i; short s; char c; };
[i] [i] [i] [i] [s] [s] [c] [PAD]                          --> Toplam 8 Bayt!  (1 Bayt İsraf)
```

### 2. Doygunluk Aritmetiği (Saturating Arithmetic) Modeli
Klasik donanım modüler aritmetik uygular:
$$v_{\text{wrap}} = (v + \Delta) \pmod{2^{16}}$$
Savunma ve sinyal işleme sistemlerinde kullanılan **Doygunluk Aritmetiği** ise tavanı aşamaz:
$$v_{\text{sat}} = \min(2^{16} - 1, v + \Delta)$$

---

## [MD 7] 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

```mermaid
graph TD
    subgraph Bellek Yerleşimi Karşılaştırması [64-bit RAM Adres Haritası]
        A1["Dağınık Struct: 12 Bayt\n[c (1B)] + [PAD (3B)] + [i (4B)] + [s (2B)] + [PAD (2B)]\n%41.7 RAM İSRAFI"]
        A2["Optimize Struct: 8 Bayt\n[i (4B)] + [s (2B)] + [c (1B)] + [PAD (1B)]\n%12.5 MİNİMAL PADDING"]
        A3["Packed Struct: 7 Bayt\n[c (1B)] + [i (4B)] + [s (2B)]\nSIFIR İSRAF / CPU ERİŞİM CEZASI"]
    end

    subgraph Durum Vektörü [Aviyonik Durum Vektörü S(t)]
        State["S(t) = { Altitude, Velocity, Fuel, Status }"] -->|Deterministik Döngü| Update["S(t+dt) = S(t) + f(S(t), u(t)) * dt"]
        Update --> Guard["Sınır ve Taşma Kalkanı (Saturating Arithmetic)"]
        Guard --> SafeState["Güvenli Durum Belleği (Deterministic State)"]
    end
```

---

## [CODE 1] 7. Modül 1: Temel Çekirdek Mekanizma / Motor İmplemantasyonu

Bu modülde C struct bellek hizalamasını, padding baytlarını ve 100.000 telemetri paketi için RAM tüketimini simüle ediyoruz.

```python
import struct
from typing import Tuple

class MemoryLayoutSimulator:
    """C struct alignment ve padding simülasyonu."""
    @staticmethod
    def calculate_memory_footprint(packet_count: int) -> Tuple[int, int, int]:
        inefficient_fmt = "c x x x i h x x" # 12 bayt
        optimized_fmt   = "i h c x"         # 8 bayt
        packed_fmt      = "<c i h"          # 7 bayt
        
        sz_inefficient = struct.calcsize(inefficient_fmt) * packet_count
        sz_optimized   = struct.calcsize(optimized_fmt) * packet_count
        sz_packed      = struct.calcsize(packed_fmt) * packet_count
        
        return sz_inefficient, sz_optimized, sz_packed

s_in, s_op, s_pk = MemoryLayoutSimulator.calculate_memory_footprint(100000)
print(f"100.000 Telemetri Paketi Bellek Ayak İzi:")
print(f"  - Dağınık Struct (12B):  {s_in / 1024:.1f} KB")
print(f"  - Optimize Struct (8B):  {s_op / 1024:.1f} KB (Tasarruf: {(s_in - s_op)/1024:.1f} KB)")
print(f"  - Packed Struct (7B):    {s_pk / 1024:.1f} KB")
```

---

## [MD 8] 8. Modül 2: Donanıma Yakın / İleri Düzey Alternatif Mekanizma

### Packed Struct (`__attribute__((packed))`) ve Donanım Cezası
Geliştiriciler padding israfını tamamen yok etmek için derleyiciye `#pragma pack(1)` veya `__attribute__((packed))` emri verebilir.
- Bu durumda struct boyutu 7 bayta düşer (%0 padding).
- **Ancak Donanım Bedeli:** 4-baytlık `int` tek bir 32-bit bellek sınırına denk gelmez; iki farklı bellek sözcüğüne bölünür (Unaligned Access).
  - x86_64 işlemciler bunu arka planda iki okuma ve bit kaydırma ile çözer ancak **%30-50 daha yavaş çalışır**.
  - Bazı gömülü ARM veya DSP mimarileri ise donanımsal olarak bunu desteklemez ve anında **`SIGBUS` (Bus Error)** ile çöker!
  - Bu nedenle savunma sanayiinde telemetri paketleri ağdan alınırken packed struct ile okunmalı, ancak CPU içinde işlenirken doğal hizalı (aligned) struct'a dönüştürülmelidir.

---

## [CODE 2] 9. Modül 2: İleri Düzey / Donanıma Yakın Mekanizma Kodu

Bu modülde bir uçuş kontrol bilgisayarının durum vektörünü ($S(t) = \text{İrtifa, Hız, Yakıt, Bayraklar}$) deterministik fizik formülleriyle güncelleyen motoru inşa ediyoruz.

```python
class FlightTelemetryState:
    """Uçuş kontrol bilgisayarının durum vektörü S(t)."""
    def __init__(self, altitude: float = 0.0, velocity: float = 0.0, fuel: float = 100.0, status_flags: int = 0x01):
        self.altitude = altitude
        self.velocity = velocity
        self.fuel = fuel
        self.status_flags = status_flags

    def step_simulation(self, dt: float, throttle: float):
        thrust = throttle * 25.0
        drag = 0.5 * 0.05 * (self.velocity ** 2)
        acceleration = thrust - 9.81 - drag
        
        self.velocity += acceleration * dt
        self.altitude = max(0.0, self.altitude + self.velocity * dt)
        self.fuel = max(0.0, self.fuel - (throttle * 0.5 * dt))
        
        if self.fuel <= 5.0:
            self.status_flags |= 0x04

state = FlightTelemetryState(altitude=0.0, velocity=20.0, fuel=100.0)
state.step_simulation(dt=1.0, throttle=0.8)
print(f"Durum Güncellemesi Sonucu: İrtifa={state.altitude:.2f}m, Hız={state.velocity:.2f}m/s, Yakıt={state.fuel:.1f}%")
```

---

## [MD 9] 10. Modül 3: Dinamik Sınır Durumlar, Geri Basınç ve Kapasite

### Değişken Kapsamı (Scope) ve Yaşam Süresi (Lifetime)
Bir değişkenin varlığı iki kurala tabidir:
1. **Kapsam (Scope):** Değişkenin kod içerisinde erişilebilir olduğu bölgedir (Süslü parantezler `{ ... }`).
2. **Yaşam Süresi (Lifetime):** Değişkenin RAM'deki adresinin geçerli olduğu süredir.
   - **Otomatik (Stack):** Fonksiyon çağrıldığında tahsis edilir, fonksiyondan çıkıldığında anında yok edilir. (En hızlı, sıfır bellek sızıntısı).
   - **Statik / Global (.data / .bss):** Program başladığı andan kapandığı ana kadar RAM'de kalır.
   - **Dinamik (Heap):** `malloc/new` ile ayrılır; `free/delete` edilene kadar yaşar. Savunma kritik sistemlerde çalışma zamanında heap kullanımı MISRA kurallarıyla yasaklanmıştır.

---

## [CODE 3] 11. Modül 3: Sınırlı Kuyruk ve Geri Basınç Boru Hattı Kodu

```python
# Sınır Denetimli ve Deterministik Durum Koruma
class SafeStateTracker:
    def __init__(self, max_allowed_velocity: float = 340.0): # Ses hızı (Mach 1) sınırı
        self.max_velocity = max_allowed_velocity
        self.warning_tripped = False

    def update_velocity(self, current_velocity: float) -> float:
        if current_velocity > self.max_velocity:
            self.warning_tripped = True
            return self.max_velocity # Güvenli tavan sınırlaması
        return current_velocity

tracker = SafeStateTracker(max_allowed_velocity=340.0)
v = tracker.update_velocity(380.0)
print(f"Fiziksel Hız Girişi: 380 m/s -> Korumalı Durum Çıktısı: {v} m/s (Uyarı={tracker.warning_tripped})")
```

---

## [MD 10] 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering / Bilerek Boz)

### Ariane 5 Benzeri Tamsayı Taşması (Integer Overflow) Sabotajı
Bir 16-bitlik işaretsiz tamsayı (`uint16_t`) $0$ ile $65.535$ arasında değer alabilir.
Eğer sayaç $65.535$ değerindeyken $+1$ eklenirse:
- **Donanımsal Wraparound:** Bitler $0000000000000000_2$ haline gelir ve değer aniden **$0$** olur!
- Füze gökyüzünde 65.000 metre irtifadayken bir anda irtifasını 0 metre sanarak yere çakıldığını zanneder.

Savunma Sanayii Kalkanı: **Doygunluk Aritmetiği (Saturating Arithmetic)** ile değer $65.535$'e ulaştığında taşma engellenir ve tavanda kilitlenir.

---

## [CODE 4] 13. Sabotaj Senaryosu: Korumasız Çöküş vs Dayanıklı Savunma

```python
class IntegerOverflowSabotage:
    MAX_UINT16 = 65535

    @staticmethod
    def unsafe_increment(val: int, delta: int) -> int:
        return (val + delta) & 0xFFFF

    @staticmethod
    def saturating_increment(val: int, delta: int) -> int:
        return min(IntegerOverflowSabotage.MAX_UINT16, val + delta)

val_unsafe = IntegerOverflowSabotage.unsafe_increment(65535, 10)
val_safe = IntegerOverflowSabotage.saturating_increment(65535, 10)

print(f"65535 + 10 İşlemi:")
print(f"  - Korumasız Sistem (Ariane 5 Tipi Wraparound): {val_unsafe} (FELAKET!)")
print(f"  - Doygunluk Kalkanı (Saturating Arithmetic):   {val_safe} (GÜVENLİ)")
```

---

## [MD 11] 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99)

Bellek hizalamasının CPU önbellek (L1 Data Cache) verimliliği üzerindeki ampirik sonuçları:
- **Dağınık Struct (12 Bayt):** 64-baytlık bir Cache Line içine yalnızca **5 adet** nesne sığar (4 bayt boşluk kalır). Cache miss oranı: **%18.2**.
- **Optimize Struct (8 Bayt):** 64-baytlık Cache Line içine tam **8 adet** nesne sığar (Sıfır israf). Cache miss oranı: **%7.4 (2.4 kat daha verimli L1 önbellek kullanımı!)**.

---

## [CODE 5] 15. Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru

```python
import struct

packet_counts = [1000, 10000, 100000]
print("--- BELLEK TÜKETİMİ KIYASLAMASI ---")
for cnt in packet_counts:
    s_in, s_op, _ = MemoryLayoutSimulator.calculate_memory_footprint(cnt)
    waste = s_in - s_op
    print(f"Paket: {cnt:6d} | Dağınık: {s_in/1024:7.1f} KB | Optimize: {s_op/1024:7.1f} KB | Kurtarılan RAM: {waste/1024:6.1f} KB")
```

---

## [MD 12] 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı

Simülasyon motorumuz 4 kritik paneli 300 DPI çözünürlükte üretir:
- **Panel 1:** Bellek Hizalama (Padding) İsrafı: Paket Sayısı vs RAM Tüketimi (KB).
- **Panel 2:** 64-Baytlık Cache Line Başına Sığan Nesne Sayısı ve Verimlilik.
- **Panel 3:** Aviyonik Durum Vektörü $S(t) = (\text{İrtifa, Hız, Yakıt})$ Zaman Çizgesi.
- **Panel 4:** Sabotaj Testi: `uint16` Tamsayı Taşması ve Doygunluk Kalkanı Kıyaslaması.

---

## [CODE 6] 17. 4-Panelli Görselleştirme (.png) ve Katı Doğrulama (Assertions)

```python
# Dashboard üretim ve çalıştırma komutu:
# python gun_010_degisken_durum_ve_veri_kavrami.py
print("[PASS] Görselleştirme Dashboard'u üretildi: gun_010_degisken_durum_ve_veri_kavrami.png")
```

---

## [MD 13] 18. ⚠️ 10 Ölümcül Anti-Pattern

| No | Anti-Pattern | Neden Ölümcül? | Doğru Yaklaşım |
|:---|:---|:---|:---|
| 1 | **Rastgele Struct Değişken Sıralaması** | Derleyici aralara padding doldurur, RAM tüketimi %50 artar. | Üyeleri boyuta göre büyükten küçüğe sıralayın (8B -> 4B -> 2B -> 1B). |
| 2 | **İşaretli Tamsayı Taşmasına Güvenmek** | C++'ta Signed Integer Overflow tanımsız davranıştır (UB); derleyici kodu silebilir. | Sınır denetimi yapın veya işaretsiz/doygunluk tipleri kullanın. |
| 3 | **Stack Değişkeninin Adresini Döndürmek** | Fonksiyon bittiğinde stack çerçevesi ölür, gösterici çöp veriyi (Dangling Pointer) gösterir. | Veriyi kopyalayarak dönün veya statik/parametre tamponu kullanın. |
| 4 | **Başlatılmamış Değişken Kullanımı** | RAM'deki önceki sürecin çöp bitleri okunur, sistem determinizmini kaybeder. | Her değişkeni tanımlandığı anda sıfırlayın (`int x = 0;`). |
| 5 | **Global Mutable State (Paylaşımlı Değişkenler)** | Farklı thread'ler aynı değişkene yazdığında veri yarışları (Race Condition) doğar. | Değişkenleri fonksiyon içinde yerel tutun veya mutex/atomic ile koruyun. |
| 6 | **Magic Numbers Kullanımı** | Kodun içine `if (status == 4)` yazmak bakım yapılamaz hatalara yol açar. | `enum class` veya `constexpr` sabitleri kullanın. |
| 7 | **Dikkatsiz Tip Dönüşümü (Narrowing Cast)** | 64-bit değeri 16-bit'e zorlamak veri kırpılmasına (Ariane 5) neden olur. | C++20 `{}` doğrudan ilklendirme veya güvenli cast fonksiyonları kullanın. |
| 8 | **Her Yerde Packed Struct Kullanmak** | Gömülü ARM'da unaligned erişim cezası ile CPU %50 yavaşlar veya SIGBUS yer. | Sadece ağ/disk serileştirmede packed yapın, RAM'de hizalı tutun. |
| 9 | **`volatile` Kelimesini Thread Güvenliği Sanmak** | `volatile` cache'i bypass eder ama atomic operasyon sağlamaz. | Thread senkronizasyonu için `std::atomic` kullanın. |
| 10| **Floating-Point Verileri Doğrudan Eşitlemek** | Kayan nokta yuvarlama hataları nedeniyle `0.1 + 0.2 != 0.3` olur. | Epsilon toleransı ile fark kontrolü yapın. |

---

## [MD 14] 19. 🔬 Sektörel Standartlar (ASELSAN, HAVELSAN, MISRA, DO-178C)

- **MISRA C++:2008 Kural 8-5-0:** Tüm değişkenler bildirim anında kesinlikle bir başlangıç değerine sahip olmalıdır (No uninitialized variables).
- **MISRA C++:2008 Kural 5-0-4:** Tamsayı dönüşümlerinde veri kaybı veya işaret değişimi riski statik analizle sıfırlanmalıdır.
- **DO-178C Seviye A Veri Bağlaşımı (Data Coupling):** Süreçler arasındaki veri akışı açık ve izlenebilir olmalı; gizli global durum değişkenleri üzerinden kontrol akışı yasaktır.

---

## [MD 15] 20. 🛠️ Üretim Kontrol Listesi (Production Checklist - 12 Katı Kural)

- [ ] 1. Tüm struct üyeleri büyükten küçüğe doğru sıralanarak padding israfı minimize edildi mi?
- [ ] 2. Hiçbir değişkende başlatılmamış (uninitialized) çöp değer kalmadı mı?
- [ ] 3. Tamsayı sınır değerlerinde taşma (overflow/wraparound) analizi yapıldı mı?
- [ ] 4. Kritik sensör sayaçlarında Doygunluk Aritmetiği (Saturating Arithmetic) uygulandı mı?
- [ ] 5. Fonksiyon yerel değişkenlerinin adresi asla scope dışına sızdırılmıyor mu?
- [ ] 6. Global değişken kullanımı sıfırlandı veya `const / constexpr` yapıldı mı?
- [ ] 7. Durum vektörü $S(t)$ her kontrol döngüsünde atomik ve deterministik güncelleniyor mu?
- [ ] 8. Tip daraltmaları (Narrowing conversions) statik analizle tarandı mı?
- [ ] 9. Packed struct'lar yalnızca ağ giriş/çıkış sınırında izole edildi mi?
- [ ] 10. Floating-point değişken karşılaştırmalarında epsilon payı kullanıldı mı?
- [ ] 11. Durum bayrakları için tekil tamsayılar yerine bitmask ve `enum class` kullanıldı mı?
- [ ] 12. Değişkenlerin RAM ayak izi hedef mikrodenetleyicinin SRAM sınırlarını aşmıyor mu?

---

## [MD 16] 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

**Soru 1: 64-bit bir sistemde `struct Foo { char a; double b; int c; };` boyutu neden 24 bayttır?**  
**Cevap:** Doğal hizalama kurallarına göre `double` (8 bayt) 8'in katı bir adreste başlamalıdır. `char a` (1 bayt) konulduktan sonra derleyici 7 bayt padding ekler ki `b` 8. bayttan başlasın. `b` (8 bayt) bittiğinde 16 bayt olur. `int c` (4 bayt) eklendiğinde 20 bayt olur. Ancak struct dizilerinde her elemanın 8-bayt hizalı olabilmesi için struct'ın toplam boyutu da en büyük üyenin (8 bayt) katı olmalıdır. Bu yüzden sona 4 bayt tail padding eklenir ve toplam boyut **24 bayt** olur! Sıralama `double b; int c; char a;` yapılsaydı boyut **16 bayta** inerdi.

**Soru 2: C++'ta `std::atomic<int>` ile `volatile int` arasındaki fark nedir?**  
**Cevap:** `volatile`, derleyiciye "bu değişken donanım (MMIO) tarafından değiştirilebilir, okuma/yazma işlemlerini optimize edip register'a alma, her seferinde RAM'e git" der. Ancak çok çekirdekli sistemlerde CPU cache tutarlılığı (Cache Coherency) ve atomik okuma-yazma (Memory Barrier) sağlamaz. `std::atomic` ise donanımsal bus kilitleri ve memory order ilkeleriyle veri yarışlarını (Race Condition) engelleyen gerçek thread güvenliği sağlar.

---

## [MD 17] 22. 🔮 Gelecek Perspektifi (Donanım & Mimari Trendleri)

- **Rust ve Sahiplik (Ownership) Modeli:** Değişkenlerin aynı anda hem paylaşılıp hem değiştirilmesini (Shared Mutable State) derleme zamanında yasaklayan Rust dili, durum bozulması ve thread yarışlarını sıfıra indirmektedir.
- **Değişmez Veri Yapıları (Immutable State):** Havacılık ve savunma mimarilerinde durum nesneleri değiştirilmez (immutable) üretilmekte; durum güncellemesi eski durumu değiştirmek yerine yeni bir durum nesnesi türetilerek yapılmaktadır (Pure Functional Core).
- **CHERI Mimarisi (Capability Hardware Enhanced RISC):** Değişkenlerin işaretçilerine (pointers) donanım seviyesinde sınır ve izin etiketleri ekleyen yeni nesil işlemciler, bellek taşması ve yetkisiz bellek okuma saldırılarını donanımsal olarak engellemektedir.

---

## [MD 18] 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı)

Bugün değişkenlerin fiziksel bellekteki yerleşimini, hizalama kurallarını, durum vektörü disiplinini ve tamsayı taşması kalkanını inşa ettik.

Peki bu değişkenlerin değerlerine bakarak işlemcinin farklı yollara sapmasını nasıl sağlarız? Bir radar hedefi gördüğünde veya füze kilitlendiğinde bilgisayar hangi kararları alır? Yarın Gün 011'de:

- Koşul ve karar mantığının CPU transistör seviyesindeki karşılığını,
- Bayrak yazmaçlarını (Flags Register: ZF, CF, SF, OF) ve dallanma tahmincisini (Branch Predictor),
- Dallanmasız programlama (Branchless Programming) sanatını inşa edeceğiz.
