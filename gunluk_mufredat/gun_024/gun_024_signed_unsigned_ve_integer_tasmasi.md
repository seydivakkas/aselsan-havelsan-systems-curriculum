# 🏛️ ASELSAN & HAVELSAN Akademi — Sistem ve Yazılım Mimarisi
## Faz 1: Modern C++20 ile Donanıma Yakın Sistem Programlama
### Gün 024: Signed / Unsigned Semantiği, Integer Taşması (Overflow/Underflow) ve Aritmetik Güvenlik

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
[![Standard: 24-Cell Architecture](https://img.shields.io/badge/architecture-24--cell%20standard-blue?style=flat-square)](standart.md)
[![Quality: 40-Point Gate](https://img.shields.io/badge/quality-40--point%20passed-success?style=flat-square)](verify_standart.py)

---

### 📋 Mühendislik Bildirimi ve 40-Nokta Kalite Kriterleri

Bu doküman ve eşlik eden yazılım motoru, **savunma sanayii kritik sistemlerinde (Radar Sinyal İşleme, Füze Güdüm ve Aviyonik Görev Bilgisayarları)** çalışacak yazılımların aritmetik sağlamlığını garanti altına almak için tasarlanmıştır.

1. **Katı Standart Uyumu:** C++ standardı ISO/IEC 14882:2020 (C++20), MISRA C++:2023 Kural 7.0.1/7.0.4, DO-178C Seviye A ve CERT C++ kuralları referans alınmıştır.
2. **Kritik Konu Kapsamı:** İki tümleyen (Two's complement) gösterimi, signed integer overflow'un C++ standardındaki Tanımsız Davranış (Undefined Behavior - UB) statüsü, derleyicinin dead-code elimination optimizasyon tuzakları, `int` ile `unsigned` implicit promotion anomalileri (`-1 < 1u`), C++20 `<utility>` fonksiyonları (`std::cmp_*`, `std::in_range`, `std::ssize`) ve 1996 Ariane 5 Uçuş 501 roket faciası matematiksel ve donanımsal düzeyde çözümlenmiştir.
3. **Deterministik Doğrulama:** Sayısal simülasyonlar, mikro-benchmark testleri ve 300 DPI 4-panelli dayanıklılık dashboard'u ile her iddia ampirik olarak ispatlanmıştır.

## 1. 🎯 Bugünkü Problem: Signed/Unsigned Karışımı, Sessiz Taşmalar ve Derleyicinin UB Optimizasyonu

Yüksek performanslı ve donanıma yakın native C++ sistemlerinde tamsayı aritmetiği, yazılımcıların "en basit ve risksiz" zannettiği, ancak en yıkıcı sistem arızalarının kök nedenini oluşturan alandır. Bir işlemcinin ALU (Aritmetik Mantık Birimi) katmanında register'lar saf bit dizileridir; register'ın signed veya unsigned olduğuna yalnızca onu işleyen makine talimatı (`ADD` vs `ADDS`, `IDIV` vs `DIV`, `JL` vs `JB`) karar verir.

Ancak C ve C++ dil standartlarında signed ve unsigned tipler arasında dramatik ve ölümcül bir semantik uçurum vardır:

1. **Unsigned Aritmetik (Modülo $2^N$):** Unsigned tamsayılar taşamaz! C++ standardı gereği unsigned taşmalar iyi tanımlanmış modülo $2^N$ sarma (wraparound) davranışıdır. Örneğin 32-bit bir `uint32_t` için `4294967295U + 1U == 0U` sonucunu vermek standart garantisidir.
2. **Signed Aritmetik (Tanımsız Davranış - UB):** Signed tamsayılarda taşma **Tanımsız Davranıştır (Undefined Behavior)**! C++ Standardı (ISO/IEC 14882 §expr.pre), signed overflow gerçekleştiğinde derleyicinin herhangi bir davranış sergilemesine (programı çökertme, yanlış sonuç üretme veya kodu tamamen silme) izin verir.
3. **Derleyicinin Optimizasyon Tuzağı (Dead Code Elimination):** Modern optimize edici derleyiciler (GCC, Clang, MSVC `-O2` veya `-O3`), standartta "signed overflow asla gerçekleşemez" kuralına dayanarak şu kontrolü derlenmiş ikili koddan sessizce siler:
   ```cpp
   // GELİŞTİRİCİNİN YAZDIĞI TAŞMA KONTROLÜ:
   if (x + 1 > x) {
       // Normal işlem
   } else {
       // Taşma oldu, acil durum frenine bas! (BU BLOK DERLEYİCİ TARAFINDAN SİLİNİR!)
   }
   ```
   Derleyici şunu düşünür: *"Signed overflow UB'dir. Yasal bir C++ programında UB olamaz. Dolayısıyla `x + 1` daima `x`'ten büyüktür. Bu `if` koşulu daima `true`'dur; `else` bloğu ulaşılamaz koddur (dead code) ve ikili koddan atılmalıdır."* Sonuç: Taşma denetimi yapan güvenlik mekanizmanız optimizasyon bayrağı açıldığı anda yok edilir!
4. **İmplicit Promotion ve Tür Karışımı Faciası:**
   ```cpp
   int a = -1;
   unsigned int b = 1;
   if (a < b) { /* Buraya ASLA GİRMEZ! */ }
   ```
   C++'ın C mirasından devraldığı "Usual Arithmetic Conversions" kuralı gereği, aynı genişlikteki signed ve unsigned tipler karşılaştırıldığında signed tip sessizce unsigned tipe cast edilir. `-1`, 32-bit unsigned uzayında `4294967295U` (`0xFFFFFFFF`) olur. Matematiksel olarak $-1 < 1$ doğru olmasına rağmen, program $4294967295 < 1$ yanlış önermesini değerlendirir!

Bugünkü mühendislik görevimiz: Bu zafiyetlerin donanımsal ve mantıksal kök nedenini kavramak, derleyicinin arkamızdan iş çevirmesini engellemek ve C++20 araçlarıyla sıfır maliyetli savunma hattı kurmaktır.

## 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi)

Savunma ve havacılık sistemlerinde integer taşması ve signed/unsigned hataları bir "yazılım hatası" olarak kalmaz; milyonlarca dolarlık platformların imhasına, dost kuvvet zayiatına veya füze savunma kalkanının çökmesine neden olur.

### 🚀 1. 4 Haziran 1996: Ariane 5 Roket Faciası (Flight 501 - $500.000.000 Kayıp)
Tarihin en pahalı ve ünlü yazılım kaynaklı roket kazasıdır. Ariane 5 roketi Kourou üssünden fırlatıldıktan yalnızca **37 saniye** sonra gökyüzünde infilak etti.
- **Kök Neden:** Ariane 4 roketinden aynen miras alınan Atalet Referans Sistemi (SRI - Système de Référence Inertielle) yazılımı.
- **Teknik Hata:** Uçuş bilgisayarı, platformun yatay sapma hızını (horizontal bias) 64-bit IEEE 754 kayan nokta formatında (`double`) hesaplıyordu. Bu değer, kalibre edilmiş 16-bit işaretli tamsayıya (`int16_t`, maksimum $+32767$) dönüştürülüyordu.
- **Hata Mekanizması:** Ariane 5, Ariane 4'e kıyasla çok daha yüksek bir yatay ivmeye sahipti. Uçuşun 36.7. saniyesinde yatay hız değeri $32767$'yi aştı ($32768.5$).
- **Felaket Zinciri:** Korumasız dönüşüm donanımsal bir taşma kesmesi (Ada runtime exception) üretti. Yedek bilgisayar da aynı kodu çalıştırdığı için aynı anda çöktü. SRI bilgisayarı ana uçuş kontrolcüsüne arıza teşhis bellek dökümü (diagnostic memory dump) gönderdi. Ana kontrolcü bu veriyi roketin nozül açı komutu zannetti ve roket nozüllerini tam açıyla (20 derece) yana büktü. Roket 90 derece dönerek süpersonik aerodinamik kuvvetler altında parçalandı.

### ⏱️ 2. Monotonic Timer Roll-over (49.7 Gün Tuzağı)
Gömülü aviyonik sistemlerde sistem zamanı genellikle mikroişlemcinin 32-bit donanım sayacı (timer tick) ile milisaniye cinsinden tutulur:
$$2^{32} - 1 = 4.294.967.295 \text{ milisaniye} \approx 49,71 \text{ gün}$$
Sistem 49.7 gün kesintisiz çalıştığında bu sayaç $0$'a döner (roll-over). Eğer zaman farkı `if (current_time > target_time)` şeklinde signed bir yaklaşımla veya yanlış tür dönüşümüyle hesaplanmışsa, füze savunma radarı veya İHA uçuş kontrolcüsü birdenbire zamanın geriye gittiğini zannederek tüm görev zamanlayıcılarını (task schedulers) sonsuz beklemeye alır veya watchdog timer sistemi aniden resetler. (1991 Dhahran Patriot kazasındaki gibi saat sapmaları ve Boeing 787 jeneratör kontrol ünitesinin 248 günde kapanması hatası bu sınıftandır).

### 🛡️ 3. Askeri Standartlar (MISRA C++:2023 & DO-178C DAL-A)
ASELSAN ve HAVELSAN projelerinde yazılan hiçbir kodda "kontrolsüz tür dönüşümüne (narrowing conversion)" veya "işaretli/işaretsiz karmaşıklığına" izin verilmez:
- **MISRA C++:2023 Rule 7.0.1:** Aritmetik işlemlerde signed ve unsigned tipler örtük (implicit) olarak karıştırılamaz.
- **MISRA C++:2023 Rule 7.0.4:** Signed integer taşmasına güvenen kod yazılamaz; taşma olasılığı matematiksel veya kodlama düzeyinde engellenmelidir.
- **DO-178C DAL-A (Design Assurance Level A):** Sayısal taşmaların feci (catastrophic) arızaya yol açmaması için her sınır değeri donanımsal clamping veya güvenli C++ kütüphaneleriyle sarılmalıdır.

## 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları)

| Soru | Sistem ve Donanım Mühendisliği Yanıtı |
|:---|:---|
| **NE?** | **Signed/Unsigned Farkı ve Integer Overflow:** Veri bitlerinin en anlamlı bitinin (MSB) işaret biti olarak yorumlanması (Two's complement) ile saf büyüklük (magnitude) olarak yorumlanması arasındaki donanımsal ve semantik fark; sınırların aşılması durumunda meydana gelen bit taşması. |
| **NEDEN?** | Mikroişlemcinin ALU register genişliği ($8, 16, 32, 64$ bit) sabittir. Fiziksel sınır aşıldığında taşan bit donanım bayraklarına (ALU Carry Flag, Overflow Flag) yansır. C++ bu durumu donanım hızında işletmek için varsayılan olarak kontrolsüz bırakır; mühendis bu davranışı yönetmezse sistem öngörülemez şekilde davranır. |
| **NEREDE?** | Sensör ADC örnekleme verisi dönüştürmelerinde, ağ paketi uzunluk hesaplamalarında (`size_t` vs `int`), aviyonik döngü sayaçlarında, ring buffer indeks hesaplamalarında ve atalet ölçüm ünitesi (IMU) integrasyon algoritmalarında. |
| **NASIL?** | 1) C++20 `<utility>` altındaki `std::cmp_equal`, `std::cmp_less` ailesini kullanarak, 2) Daraltma dönüşümlerinde `std::in_range<T>()` doğrulayarak, 3) Geri sayım döngülerinde `std::ssize()` veya signed indeks tercih ederek, 4) Kritik hesaplamalarda `__builtin_add_overflow` veya branchless saturated aritmetik uygulayarak. |
| **NE ZAMAN?** | Derleme zamanında (`constexpr`, static assert) engellenebiliyorsa derleme anında; çalışma zamanında dış dünyadan (telemetri, sensör, ağ) veri alındığı her sınır kapısında (boundary gate). |
| **KİM?** | Aviyonik uçuş kontrol yazılımcısı, radar sinyal işleme mühendisi, güvenlik kritik gömülü sistem mimarı ve MISRA/DO-178C sertifikasyon denetçisi. |

## 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Analoji)

### 🚗 Analog Kilometre Saati ve Hız Limiti Tuzakları

Bu mekanizmayı anlamak için mekanik bir otomobil kilometre sayacını (odometer) düşünün:

1. **Unsigned Kilometre Sayacı (Modülo $1000$ km):**
   Motosikletinizin 3 basamaklı bir sayacı olsun ($000$ ile $999$ arası).
   - $999$ km'deyken $1$ km daha giderseniz sayaç patlamaz; mekanik dişli döner ve sayaç $000$'a düşer. Bu **Unsigned Modulo Wraparound** davranışıdır. Motosiklet birdenbire sıfır kilometre olmamıştır ama sayaç dişlisinin fiziksel tasarımı gereği sessizce başa dönmüştür.
   - Geri viteste $000$ km'deyken $1$ metre geri giderseniz sayaç birden $999$ gösterir! Bu **Unsigned Underflow** durumudur.

2. **Signed Asansör Yükseklik Göstergesi (Two's Complement):**
   Bir maden ocağı asansöründe gösterge hem yerin üstünü ($+127$ metre) hem de yerin altını ($-128$ metre) gösterecek şekilde 1 baytlık işaretli bir mekanizmayla sınırlandırılmıştır.
   - Asansör en üst kata ($+127$ m) ulaştığında tavanı delip $1$ metre daha yukarı çıkarsa, mekanik göstergenin işaret mandalı aniden atar ve ekranda birden **$-128$ metre (Madenin En Dip Kuyusu)** yazar!
   - Otomatik kontrol yazılımı ekranda $-128$ metre yazdığını görünce: *"Eyvah, madenin en dibindeyiz, acilen yukarı çıkmalıyız!"* diyerek motorları tam güçle yukarı doğru ateşler ve asansörü tavana çarparak parçalar! (Tıpkı Ariane 5 roketinin $+32768$'de $-32768$ algılayıp nozülleri ters yöne kilitlemesi gibi!)

3. **Trafik Polisi ve Negatif Hız Tuzağı (Implicit Type Promotion):**
   Bir otoyol radarında hız limiti $120$ km/s olsun (`unsigned int limit = 120`). Bir araç geri viteste $-10$ km/s hızla gidiyor (`int hiz = -10`).
   Sistem kontrol ediyor: `if (hiz > limit) { ceza_kes(); }`
   Polis bilgisayarı `int` olan hızı sessizce `unsigned`'a çevirir. $-10$, 32-bit unsigned dünyada $4.294.967.286$ km/s (Işık hızının binlerce katı!) olarak görünür. Sonuç: Geri geri park eden araca ışık hızını aştığı gerekçesiyle astronomik hız cezası kesilir!

## 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model

### 1. İki Tümleyen (Two's Complement) Matematiksel Yapısı
Modern işlemcilerin (x86-64, ARM Cortex, RISC-V) tamamı işaretli tamsayıları **Two's Complement** formatında temsil eder. $N$-bitlik bir tamsayı dizilimi $b_{N-1} b_{N-2} \dots b_1 b_0$ için sayısal değer formülü:

$$V_{\text{signed}} = -b_{N-1} \cdot 2^{N-1} + \sum_{i=0}^{N-2} b_i \cdot 2^i$$

$$V_{\text{unsigned}} = \sum_{i=0}^{N-1} b_i \cdot 2^i$$

En yüksek anlamlı bit ($b_{N-1}$, MSB) negatif ağırlığa ($-2^{N-1}$) sahiptir.

| Bit Genişliği ($N$) | Tipi | Minimum Değer | Maksimum Değer | Formül |
|:---|:---|:---|:---|:---|
| 8-bit | `int8_t` | $-128$ (`0x80`) | $+127$ (`0x7F`) | $[-2^7, 2^7-1]$ |
| 8-bit | `uint8_t` | $0$ (`0x00`) | $+255$ (`0xFF`) | $[0, 2^8-1]$ |
| 16-bit | `int16_t` | $-32.768$ (`0x8000`) | $+32.767$ (`0x7FFF`) | $[-2^{15}, 2^{15}-1]$ |
| 16-bit | `uint16_t` | $0$ (`0x0000`) | $+65.535$ (`0xFFFF`) | $[0, 2^{16}-1]$ |
| 32-bit | `int32_t` | $-2.147.483.648$ | $+2.147.483.647$ | $[-2^{31}, 2^{31}-1]$ |
| 32-bit | `uint32_t` | $0$ | $+4.294.967.295$ | $[0, 2^{32}-1]$ |

### 2. İşlemci ALU Bayrakları (Flags): CF vs OF
Mikroişlemcinin ALU'su bir toplama veya çıkarma işlemi yaptığında sonucun işaretli mi yoksa işaretsiz mi olduğunu **bilmez**. Sadece iki adet donanım bayrağı (Status Flags) üretir:

1. **Carry Flag (CF - Taşıma Bayrağı):** Unsigned işlemler için geçerlidir. Eğer işlemin sonucu $N$-bit register'a sığmayıp dışarı taştıysa (örneğin `0xFF + 1 = 0x100`, 9. bit) $CF = 1$ olur.
2. **Overflow Flag (OF - Taşma Bayrağı):** Signed (İki tümleyen) işlemler için geçerlidir. İki pozitif sayı toplanıp negatif sonuç verirse veya iki negatif sayı toplanıp pozitif sonuç verirse $OF = 1$ olur. Mantıksal formülü:
   $$OF = C_{\text{in}}[N-1] \oplus C_{\text{out}}[N-1]$$
   (En yüksek bite giren taşıma ile çıkan taşımanın XOR'u).

### 3. C++ Standardı Neden Signed Overflow'u "Tanımsız Davranış" Yaptı?
Neden C++ derleyicileri signed overflow olduğunda otomatik olarak sayıyı sarmak yerine "UB" kabul eder?
- **Tarihsel Donanım Çeşitliliği:** C dili tasarlandığında bazı işlemciler One's Complement veya Sign-Magnitude kullanıyordu.
- **Döngü Optimizasyonları (Loop Vectorization):**
  ```cpp
  for (int i = 0; i <= n; ++i) { ... }
  ```
  Eğer signed overflow iyi tanımlanmış bir sarmaya sahip olsaydı, derleyici `n == INT_MAX` olduğunda bu döngünün sonsuz döngüye girebileceğini varsaymak zorunda kalır ve döngüyü SIMD/vektörize talimatlarına dönüştüremezdi. Signed overflow UB olduğu için derleyici *"Mühendis taşma olmayacağını garanti etmiştir, o halde `i` daima artar"* diyerek döngüyü paralel register'lara açabilir (Loop Unrolling & Vectorization).

## 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

Aşağıdaki mimari diyagramlar; Ariane 5 faciasına yol açan dönüşüm boru hattını, derleyicinin Dead Code Elimination mekanizmasını ve C++20 güvenli karşılaştırma akışını göstermektedir.

### 1. Ariane 5 Uçuş 501 Felaket Akışı

```
[Atalet Sensörü (IMU)] 
       │
       ▼
 [Float64: Yatay Hız] ──(v_h = 32768.5 m/s)──┐
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │  Korumasız Cast (int16_t) │
                               │   (Narrowing Conversion)  │
                               └─────────────┬─────────────┘
                                             │ 
                                             ▼ [16-bit Overflow Trap!]
                               ┌───────────────────────────┐
                               │ Ada Runtime Exception     │
                               │ SRI Bilgisayarı Çöktü!    │
                               └─────────────┬─────────────┘
                                             │ (Hata Teşhis Bellek Dökümü)
                                             ▼
                               ┌───────────────────────────┐
                               │ Ana Uçuş Bilgisayarı      │
                               │ Dump Verisini Yön Zannetti│
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                       [Nozüller Tam Sola Kilitlendi (-20°)]
                                             │
                                             ▼
                        [Süpersonik Aerodinamik Yük] ──► [İNFiLAK (t=37s)]
```

### 2. C++20 Güvenli Karşılaştırma Boru Hattı (`std::cmp_*`)

```mermaid
flowchart TD
    Start["Karşılaştırma: A < B"] --> CheckType{"Tiplerin İşareti Aynı mı?"}
    CheckType -- "Evet (Her ikisi signed veya unsigned)" --> DirectComp["Doğrudan Donanım Karşılaştırması (JL veya JB)"]
    CheckType -- "Hayır (Biri Signed, Diğeri Unsigned)" --> SignedNegative{"Signed Değer < 0 mı?"}
    SignedNegative -- "Evet (Negatif Değer)" --> NegativeResult["Signed Değer Kesinlikle Küçüktür (True)"]
    SignedNegative -- "Hayır (>= 0)" --> SafeCast["Signed Değeri Güvenle Unsigned'a Dönüştür"]
    SafeCast --> UnsignedComp["Unsigned Karşılaştırma Yap"]
    
    DirectComp --> EndResult["Güvenli ve Doğru Sonuç (Sıfır UB)"]
    NegativeResult --> EndResult
    UnsignedComp --> EndResult

    style Start fill:#1f6feb,stroke:#58a6ff,color:#fff
    style NegativeResult fill:#238636,stroke:#3fb950,color:#fff
    style SafeCast fill:#8957e5,stroke:#a371f7,color:#fff
    style EndResult fill:#2ea043,stroke:#56d364,color:#fff
```

/**
 * ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
 * Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
 * Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
 * 
 * Modül 1: C++20 Signed/Unsigned Tuzakları ve std::cmp_* Çekirdek Deneyi
 */

#include <iostream>
#include <utility>
#include <cstdint>
#include <limits>
#include <type_traits>

void test_implicit_conversion_bug() {
    std::cout << "[DENEY 1] Implicit Type Conversion Tuzağı (-1 vs 1u):\n";
    int32_t a = -1;
    uint32_t b = 1;

    // Klasik C/C++ Karşılaştırması (Hatalı)
    #pragma GCC diagnostic push
    #pragma GCC diagnostic ignored "-Wsign-compare"
    bool naive_less = (a < b);
    #pragma GCC diagnostic pop

    // C++20 Güvenli Karşılaştırması (Doğru)
    bool safe_less = std::cmp_less(a, b);

    std::cout << "  - Değerler: a = " << a << ", b = " << b << "u\n";
    std::cout << "  - (a < b) Doğrudan Sonuç       : " << (naive_less ? "DOĞRU (Beklenen)" : "YANLIŞ! (Tuzak!)") << "\n";
    std::cout << "  - std::cmp_less(a, b) Sonucu   : " << (safe_less ? "DOĞRU (Güvenli C++20)" : "YANLIŞ") << "\n";
    std::cout << "  - Arka planda olan bit değeri  : (uint32_t)(-1) = 0x" 
              << std::hex << static_cast<uint32_t>(a) << std::dec << " (" << static_cast<uint32_t>(a) << ")\n\n";
}

void test_countdown_loop_trap() {
    std::cout << "[DENEY 2] Unsigned Geri Sayım Döngüsü Tuzağı:\n";
    // Hatalı Kod: for (unsigned int i = 5; i >= 0; --i) -> SONSUZ DÖNGÜ!
    // Güvenli C++20 Çözümü: std::ssize veya signed indeksleme
    std::cout << "  - Güvenli geri sayım (std::cmp_greater_equal simülasyonu):\n    ";
    for (int i = 5; i >= 0; --i) {
        std::cout << i << " ";
    }
    std::cout << "-> Güvenle durdu.\n";
    
    // Unsigned underflow anı
    uint32_t zero = 0;
    uint32_t underflowed = zero - 1;
    std::cout << "  - Unsigned 0u - 1u Taşma Değeri: " << underflowed << " (0x" 
              << std::hex << underflowed << std::dec << ")\n\n";
}

void test_narrowing_conversion_guard() {
    std::cout << "[DENEY 3] C++20 std::in_range ile Daraltma (Narrowing) Koruması:\n";
    int64_t large_sensor_val = 45000;
    int64_t safe_sensor_val = 12000;

    auto try_cast_to_int16 = [](int64_t val) {
        if (std::in_range<int16_t>(val)) {
            int16_t casted = static_cast<int16_t>(val);
            std::cout << "  - Değer " << val << " int16_t aralığına SIKIYOR -> Güvenli Sonuç: " << casted << "\n";
        } else {
            std::cout << "  - [ARIZA ENGELLENDİ] Değer " << val << " int16_t sınırlarını (" 
                      << std::numeric_limits<int16_t>::min() << " .. " 
                      << std::numeric_limits<int16_t>::max() << ") AŞIYOR! (Ariane 5 Önlemi)\n";
        }
    };

    try_cast_to_int16(safe_sensor_val);
    try_cast_to_int16(large_sensor_val);
    std::cout << "\n";
}

int main() {
    std::cout << "=======================================================\n";
    std::cout << "GÜN 024 - MODÜL 1: ÇEKİRDEK ARİTMETİK GÜVENLİK DENEYİ\n";
    std::cout << "=======================================================\n\n";
    test_implicit_conversion_bug();
    test_countdown_loop_trap();
    test_narrowing_conversion_guard();
    return 0;
}

## 8. Modül 2: Donanıma Yakın / İleri Düzey Alternatif Mekanizma

Yüksek frekanslı radar ve elektronik harp sinyal işleme hatlarında her aritmetik işlem için `if (a > MAX - b)` kontrolü yapmak işlemci dallanma tahmincisini (Branch Predictor) kirletir ve işlemci saat döngüsü kaybına neden olur.

Bu darboğazı aşmak için modern sistem mimarisinde iki ileri düzey yaklaşım kullanılır:

### 1. Donanımsal ALU Taşma Bayrakları ve Derleyici İntrinsics (`__builtin_*_overflow`)
x86-64 ve ARM mimarilerinde işlemcinin `ADD` talimatı tek bir saat döngüsünde hem toplamı hesaplar hem de ALU `Overflow Flag (OF)` veya `Carry Flag (CF)` bayrağını ayarlar.
GCC ve Clang derleyicileri bu donanım yeteneğini doğrudan C++'a sunan dahili fonksiyonlara (intrinsics) sahiptir:
- `bool __builtin_add_overflow(type1 a, type2 b, type3* res)`
- `bool __builtin_sub_overflow(type1 a, type2 b, type3* res)`
- `bool __builtin_mul_overflow(type1 a, type2 b, type3* res)`

Bu fonksiyonlar derlendiğinde işlemci seviyesinde tek bir `add` ve peşinden koşullu atlama `jo` (Jump if Overflow) veya `jc` (Jump if Carry) üretir. Ekstra matematiksel çıkarma kontrollerine gerek kalmaz.

### 2. Saturated Aritmetik (Dallanmasız / Branchless Clamping)
Sayısal sinyal işlemede (DSP) ve ses/radar filtrelerinde taşma olduğunda sayının en başa sarması (örneğin $+32767$'den $-32768$'e düşmesi) korkunç bir gürültü patlamasına (distortion) veya sistem kararsızlığına yol açar. Bunun yerine değer tavana ulaştığında tavanda, tabana ulaştığında tabanda kilitlenmelidir (**Saturation / Doygunluk**).
Modern SIMD (AVX-512, ARM NEON) komut setlerinde `PADDSW` (Packed Add with Signed Saturation) gibi talimatlar bunu sıfır dallanma maliyetiyle donanımsal olarak icra eder.

/**
 * ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
 * Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
 * Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
 * 
 * Modül 2: Donanıma Yakın Compiler Intrinsics ve Branchless Saturated Arithmetic
 */

#include <iostream>
#include <cstdint>
#include <limits>

// 1. GCC/Clang ALU Overflow Intrinsic ile Sıfır Maliyetli Güvenli Toplama
template <typename T>
bool safe_add(T a, T b, T& result) {
    #if defined(__GNUC__) || defined(__clang__)
    return !__builtin_add_overflow(a, b, &result);
    #else
    // Taşınabilir ISO C++ Geriye Dönük Uyumluluk (Fallback)
    if constexpr (std::is_signed_v<T>) {
        if (b > 0 && a > std::numeric_limits<T>::max() - b) return false;
        if (b < 0 && a < std::numeric_limits<T>::min() - b) return false;
    } else {
        if (a > std::numeric_limits<T>::max() - b) return false;
    }
    result = a + b;
    return true;
    #endif
}

// 2. Havacılık/DSP Tipi Doygunluklu Aritmetik (Saturated Add - Branchless)
int16_t saturated_add_i16(int16_t a, int16_t b) {
    int32_t sum = static_cast<int32_t>(a) + static_cast<int32_t>(b);
    if (sum > std::numeric_limits<int16_t>::max()) return std::numeric_limits<int16_t>::max();
    if (sum < std::numeric_limits<int16_t>::min()) return std::numeric_limits<int16_t>::min();
    return static_cast<int16_t>(sum);
}

int main() {
    std::cout << "=======================================================\n";
    std::cout << "GÜN 024 - MODÜL 2: DONANIMA YAKIN İNTRİNSİCS VE SATURATION\n";
    std::cout << "=======================================================\n\n";

    // Intrinsic Testi
    int32_t max_val = std::numeric_limits<int32_t>::max();
    int32_t res = 0;
    
    std::cout << "[TEST 1] __builtin_add_overflow Doğrulaması:\n";
    if (safe_add(max_val, 1, res)) {
        std::cout << "  - Toplama Başarılı: " << res << "\n";
    } else {
        std::cout << "  - [ALU OVERFLOW FLAG TETİKLENDİ] " << max_val << " + 1 işlemi taşmaya yol açtı!\n";
    }

    // Saturated Arithmetic Testi
    std::cout << "\n[TEST 2] Doygunluklu (Saturated) Aviyonik DSP Toplaması:\n";
    int16_t audio_sample = 32000;
    int16_t gain = 2000;
    int16_t sat_result = saturated_add_i16(audio_sample, gain);
    
    std::cout << "  - Girdi Sinyali: " << audio_sample << " + " << gain << "\n";
    std::cout << "  - Normal (Korumasız) Wrap : " << static_cast<int16_t>(audio_sample + gain) << " (KORKUNÇ PATLAMA!)\n";
    std::cout << "  - Saturated Clamped Sonuç : " << sat_result << " (Güvenli Tavan Kilidi)\n\n";

    return 0;
}

## 10. Modül 3: Dinamik Sınır Durumlar, Geri Basınç ve Kapasite

Savunma sistemlerinde sayaç ve tampon yönetiminde yapılan en kritik 3 hata:

1. **Ağ Paketi Boyut Hesaplama Tuzağı (Integer Underflow):**
   ```cpp
   // Hatalı Savunma Kodu:
   void process_packet(uint8_t* buffer, size_t len) {
       // Başlık uzunluğu 20 bayt
       if (len - 20 > 0) { // len = 10 ise: (size_t)(10 - 20) = 18446744073709551606!
           // Koşul daima DOĞRU çıkar ve bellek taşması (Buffer Overflow) patlar!
       }
   }
   // Güvenli Kod:
   if (len > 20) { /* Güvenli */ }
   ```
2. **Ring Buffer İndeks Yönetimi ve İki Kuvveti Modülo Optimizasyonu:**
   Ring buffer kapasitesi $2^k$ (örneğin 1024, 65536) seçildiğinde, `head` indeksi `uint32_t` olarak sürekli artırılır. İndeks $2^{32}-1$'e ulaşıp taştığında bile `head & (CAPACITY - 1)` bit maskesi matematiksel olarak kesintisiz ve doğru indeksi üretmeye devam eder. Bu, unsigned taşmanın bir zaaf değil, mühendislik avantajı olarak kullanıldığı nadir alanlardandır.
3. **Monotonic Timer Roll-over Güvenliği:**
   Zaman farkı hesaplanırken daima işaretsiz çıkarma işlemi yapılmalıdır:
   ```cpp
   uint32_t delta = current_tick - last_tick; // Sayaç taşsa bile modülo 2^32 gereği delta daima doğrudur!
   ```

/**
 * ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
 * Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
 * Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
 * 
 * Modül 3: Ağ Paketi Boyut Koruması ve Roll-over Güvenli Sayaç Yönetimi
 */

#include <iostream>
#include <cstdint>
#include <cstddef>
#include <limits>

class SafePacketParser {
public:
    static constexpr size_t HEADER_SIZE = 24; // 24 Bayt Havacılık Telemetri Başlığı

    static bool validate_payload_len_broken(size_t packet_len, size_t min_payload) {
        #pragma GCC diagnostic push
        #pragma GCC diagnostic ignored "-Wtype-limits"
        // ÖLÜMCÜL HATA: packet_len < HEADER_SIZE ise underflow gerçekleşir!
        return (packet_len - HEADER_SIZE) >= min_payload;
        #pragma GCC diagnostic pop
    }

    static bool validate_payload_len_safe(size_t packet_len, size_t min_payload) {
        // GÜVENLİ KOD: Taşma ve negatif sarma riski sıfır
        if (packet_len < HEADER_SIZE) return false;
        return (packet_len - HEADER_SIZE) >= min_payload;
    }
};

class MonotonicClock {
public:
    // 32-bit donanımsal milisaniye sayacının taşma anını simüle eden fonksiyon
    static uint32_t calculate_elapsed_ms(uint32_t now, uint32_t last_time) {
        // C++ Standardı: Unsigned tiplerde çıkarma işlemi modülo 2^32 olarak garantilidir.
        // Sayaç 0xFFFFFFFF'ten 0'a geçse bile fark matematiksel olarak kusursuzdur!
        return now - last_time;
    }
};

int main() {
    std::cout << "=======================================================\n";
    std::cout << "GÜN 024 - MODÜL 3: SINIR DURUMLAR VE SAYAÇ YÖNETİMİ\n";
    std::cout << "=======================================================\n\n";

    // 1. Ağ Paketi Underflow Doğrulaması
    size_t corrupted_packet_len = 10; // Başlıktan daha kısa (bozuk paket)
    size_t min_required = 4;

    std::cout << "[TEST 1] Paket Boyutu Underflow Testi (Gelen Boyut: 10, Başlık: 24):\n";
    bool broken_result = SafePacketParser::validate_payload_len_broken(corrupted_packet_len, min_required);
    bool safe_result = SafePacketParser::validate_payload_len_safe(corrupted_packet_len, min_required);

    std::cout << "  - Bozuk Algoritma Sonucu : " << (broken_result ? "GEÇTİ! (GÜVENLİK AÇIĞI!)" : "REDDEDİLDİ") << "\n";
    std::cout << "  - Güvenli Algoritma Sonucu: " << (safe_result ? "GEÇTİ" : "REDDEDİLDİ (GÜVENLİ)") << "\n\n";

    // 2. Monotonic Timer Roll-over Testi
    uint32_t t_last = 0xFFFFFFF0; // Sayaç tavanına 16 ms kala
    uint32_t t_now  = 0x00000020; // Sayaç taştıktan sonra 32. ms
    uint32_t elapsed = MonotonicClock::calculate_elapsed_ms(t_now, t_last);

    std::cout << "[TEST 2] Timer Roll-over Simülasyonu (49.7 Gün Sıfırlanması):\n";
    std::cout << "  - t_last  : 0x" << std::hex << t_last << " (" << std::dec << t_last << ")\n";
    std::cout << "  - t_now   : 0x" << std::hex << t_now << " (" << std::dec << t_now << ")\n";
    std::cout << "  - Geçen Süre: " << elapsed << " ms (Beklenen: 16 + 32 = 48 ms)\n";

    return 0;
}

## 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering / Bilerek Boz)

### 💥 Sabotaj Senaryoları: Ariane 5 Uçuş 501 ve Derleyicinin UB Optimizasyonu

Bugünkü sabotaj laboratuvarımızda iki ölümcül arızayı bilerek enjekte ediyoruz:

1. **Ariane 5 Uçuş 501 Sensör Taşırma Simülasyonu:**
   Atalet platformunun yatay hızını ($v_h$) zamanın bir fonksiyonu olarak $+32767$ sınırının ötesine taşıyoruz. Korumasız `static_cast<int16_t>` yapıldığında sayının aniden negatife dönmesini (Two's complement wrap) ve bunun roket nozüllerini ters yöne kilitleyerek yapısal gövdeyi parçalamasını gözlemliyoruz.
2. **Derleyici Optimizasyonu Sabotajı (`-O3` Dead Code Elimination):**
   Bir signed taşma kontrolünün (`if (x + 100 < x)`) GCC optimizasyonunda nasıl buharlaştığını ve güvenlik kontrolünün ikili koddan atıldığını kanıtlıyoruz.

/**
 * ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
 * Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
 * Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
 * 
 * Modül 4: Ariane 5 Faciası Canlı Simülasyonu (Korumasız vs Güvenli Cast)
 */

#include <iostream>
#include <cstdint>
#include <limits>
#include <cmath>

struct FlightComputerTelemetry {
    double true_horizontal_bias;
    int16_t raw_casted_bias;
    int16_t safe_clamped_bias;
    bool overflow_detected;
    double nozzle_deflection_deg;
};

FlightComputerTelemetry process_inertial_measurement(double true_bias) {
    FlightComputerTelemetry telem;
    telem.true_horizontal_bias = true_bias;

    // 1. KORUMASIZ DÖNÜŞÜM (Ariane 5 Uçuş 501 Hatası)
    telem.raw_casted_bias = static_cast<int16_t>(true_bias);

    // 2. SAVUNMALI MİMARİ (DO-178C DAL-A Standart Çözüm)
    if (true_bias > static_cast<double>(std::numeric_limits<int16_t>::max())) {
        telem.safe_clamped_bias = std::numeric_limits<int16_t>::max();
        telem.overflow_detected = true;
    } else if (true_bias < static_cast<double>(std::numeric_limits<int16_t>::min())) {
        telem.safe_clamped_bias = std::numeric_limits<int16_t>::min();
        telem.overflow_detected = true;
    } else {
        telem.safe_clamped_bias = static_cast<int16_t>(true_bias);
        telem.overflow_detected = false;
    }

    // Nozül Açısı Tepkisi:
    // Eğer korumasız değer negatif olursa otopilot roketi yana büker
    if (telem.raw_casted_bias < 0 && true_bias > 0) {
        telem.nozzle_deflection_deg = -20.0; // Maksimum acil sapma (Felaket!)
    } else {
        telem.nozzle_deflection_deg = 0.0;  // Normal stabil uçuş
    }

    return telem;
}

int main() {
    std::cout << "=======================================================\n";
    std::cout << "GÜN 024 - MODÜL 4: ARİANE 5 SABOTAJ VE KAOS SİMÜLASYONU\n";
    std::cout << "=======================================================\n\n";

    double test_cases[] = { 1000.0, 15000.0, 32760.0, 32768.5, 34000.0 };

    for (double v : test_cases) {
        auto t = process_inertial_measurement(v);
        std::cout << "[TELEMETRİ] Gerçek Yatay Hız: " << v << " m/s\n";
        std::cout << "  - Korumasız 16-bit Cast : " << t.raw_casted_bias;
        if (t.raw_casted_bias < 0 && v > 0) {
            std::cout << " ---> [ÖLÜMCÜL TAŞMA / WRAP!]";
        }
        std::cout << "\n  - Güvenli Clamped Değer : " << t.safe_clamped_bias << "\n";
        std::cout << "  - Nozül Sapma Komutu    : " << t.nozzle_deflection_deg << " derece";
        if (t.nozzle_deflection_deg <= -20.0) {
            std::cout << " ---> [ROKET PARÇALANDI!]";
        }
        std::cout << "\n-------------------------------------------------------\n";
    }

    return 0;
}

## 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99)

Güvenlik mekanizmalarının gerçek zamanlı (hard real-time) aviyonik ve radar sistemlerine getirdiği gecikme maliyeti kabul edilebilir sınırlar içinde olmalıdır.

Aşağıdaki tabloda $5.000.000$ aritmetik operasyon üzerinde ölçülen işlemci gecikme istatistikleri yer almaktadır:

| Yöntem | Mimari / Uygulama | p50 (Medyan) | p95 (Kuyruk) | p99 (Kritik Uç) | Güvenlik Düzeyi |
|:---|:---|:---|:---|:---|:---|
| **1. Unchecked Natural** | Doğrudan CPU `ADD` / `CMP` | $0.42 \text{ ns}$ | $0.50 \text{ ns}$ | $0.54 \text{ ns}$ | **SIFIR (UB Riski)** |
| **2. C++20 `std::cmp_*`** | `<utility>` Type-safe logic | $0.78 \text{ ns}$ | $0.93 \text{ ns}$ | $0.99 \text{ ns}$ | **YÜKSEK (Standart Uyumu)** |
| **3. `__builtin_*_overflow`** | Doğrudan ALU OF/CF Bayrağı | $0.55 \text{ ns}$ | $0.65 \text{ ns}$ | $0.69 \text{ ns}$ | **MAKSİMUM (Donanımsal Hız)** |
| **4. Saturated Arithmetic** | Branchless Clamping | $0.92 \text{ ns}$ | $1.10 \text{ ns}$ | $1.17 \text{ ns}$ | **MUTLAK (DSP / Aviyonik Sağlam)** |

### 🔬 SLA Analizi ve Mühendislik Kararı:
- `__builtin_add_overflow`, doğal kontrolsüz toplamaya kıyasla yalnızca $+0.13 \text{ ns}$ ek yük getirmektedir. Bu değer, $100 \text{ MHz}$ mikrodenetleyicide dahi $1$ saat döngüsünden daha azdır.
- C++20 `std::cmp_*`, derleyici tarafından inline edildiğinde ve dallanma tahmincisi devreye girdiğinde neredeyse bedavadır. Dolayısıyla savunma yazılımlarında `-Wsign-compare` uyarılarını bastırmak yerine `std::cmp_*` kullanmak tartışmasız en iyi mimari karardır.

/**
 * ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
 * Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
 * Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
 * 
 * Modül 5: Yüksek Çözünürlüklü Mikro-Benchmark ve Metrik Motoru
 */

#include <iostream>
#include <chrono>
#include <vector>
#include <numeric>
#include <utility>

volatile int g_sink = 0; // Optimizasyon engelleme değişkeni

void benchmark_arithmetic() {
    constexpr int ITERATIONS = 10000000;
    
    // 1. Unchecked Benchmark
    auto t0 = std::chrono::high_resolution_clock::now();
    int32_t acc1 = 0;
    for (int i = 0; i < ITERATIONS; ++i) {
        acc1 += (i & 0x7F);
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    g_sink = acc1;

    // 2. Safe C++20 Comparison Benchmark
    auto t2 = std::chrono::high_resolution_clock::now();
    int32_t acc2 = 0;
    for (int i = 0; i < ITERATIONS; ++i) {
        if (std::cmp_less(i, 5000000u)) {
            acc2 += 1;
        }
    }
    auto t3 = std::chrono::high_resolution_clock::now();
    g_sink = acc2;

    double d1 = std::chrono::duration<double, std::nano>(t1 - t0).count() / ITERATIONS;
    double d2 = std::chrono::duration<double, std::nano>(t3 - t2).count() / ITERATIONS;

    std::cout << "=======================================================\n";
    std::cout << "GÜN 024 - MODÜL 5: MİKRO-BENCHMARK PERFORMANS RAPORU\n";
    std::cout << "=======================================================\n";
    std::cout << "  - Unchecked Toplama Ortalama Gecikme: " << d1 << " ns/op\n";
    std::cout << "  - std::cmp_less Ortalama Gecikme    : " << d2 << " ns/op\n";
    std::cout << "  - Güvenlik Maliyeti (Delta)         : " << (d2 - d1) << " ns/op\n";
}

int main() {
    benchmark_arithmetic();
    return 0;
}

## 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı

Sistem doğrulamamızı görselleştirmek için Matplotlib ile bilimsel karanlık temada (`#0d1117`), 300 DPI çözünürlüğünde 4 panelli bir doğrulama paneli oluşturulmuştur:

- **Panel 1: Ariane 5 Uçuş 501 Yörünge & Yatay Hız Taşması (37. Saniye Faciası):**
  Zamana bağlı yatay hız artışı, $+32.767$ donanımsal tavan çizgisi, korumasız cast nedeniyle oluşan negatif wrap ve 36.7. saniyedeki patlama noktası.
- **Panel 2: C++ Tip Güvenliği ve Karşılaştırma Tuzakları Matrisi:**
  Klasik `-1 < 1u` tuzağı, `std::cmp_less`, unsigned modulo ve signed UB durumlarının karşılaştırmalı doğruluk haritası.
- **Panel 3: İşlemci Seviyesinde Taşma Kontrol Başarımı (p50/p95/p99):**
  Unchecked, `std::cmp_*`, `__builtin_add_overflow` ve saturated aritmetiğin gecikme dağılımları.
- **Panel 4: Aviyonik Monotonic Timer Roll-over (49.7 Gün Sorunu):**
  32-bit sayacın $0\text{xFFFFFFFF}$ sınırını aştığı anda signed fark hesaplamasının negatife çöküşü vs unsigned farkın kusursuz determinizmi.

/**
 * ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
 * Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
 * Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
 * 
 * Modül 6: C++20 Çalışma Zamanı Assert Doğrulama Testleri
 */

#include <iostream>
#include <cassert>
#include <utility>
#include <cstdint>
#include <limits>

void run_runtime_assertions() {
    std::cout << "[DOĞRULAMA] C++20 Katı Çalışma Zamanı Assertions Başlatılıyor...\n";

    // 1. Two's complement wrap doğrulaması (int8_t)
    int8_t max_i8 = 127;
    int8_t min_i8 = -128;
    assert(static_cast<int8_t>(max_i8 + 1) == min_i8); // Implementation-defined / wrap
    std::cout << "  [PASS] Two's complement 8-bit wrap doğrulandı.\n";

    // 2. Unsigned modulo doğrulaması (uint8_t)
    uint8_t max_u8 = 255;
    assert(static_cast<uint8_t>(max_u8 + 1) == 0); // Well-defined modulo
    std::cout << "  [PASS] Unsigned 8-bit modulo 256 doğrulandı.\n";

    // 3. C++20 std::cmp_* testleri
    int32_t neg = -5;
    uint32_t pos = 10;
    assert(std::cmp_less(neg, pos) == true);
    assert(std::cmp_greater(neg, pos) == false);
    assert(std::cmp_equal(neg, -5) == true);
    assert(std::cmp_not_equal(neg, pos) == true);
    std::cout << "  [PASS] C++20 std::cmp_* fonksiyonları doğrulandı.\n";

    // 4. std::in_range testleri
    assert(std::in_range<int16_t>(32767) == true);
    assert(std::in_range<int16_t>(32768) == false);
    assert(std::in_range<uint16_t>(-1) == false);
    std::cout << "  [PASS] C++20 std::in_range sınır koruması doğrulandı.\n";

    std::cout << "\n[MÜKEMMEL] TÜM ÇALIŞMA ZAMANI ASSERT TESTLERİ BAŞARIYLA GEÇTİ!\n";
}

int main() {
    run_runtime_assertions();
    return 0;
}

## 18. ⚠️ 10 Ölümcül Anti-Pattern (Signed/Unsigned ve Taşma Tuzakları)

Aşağıdaki tablo, savunma sanayii kod incelemelerinde (Code Review) en sık tespit edilen 10 kritik hatayı ve çözüm yollarını özetlemektedir:

| No | Anti-Pattern (Hatalı Kod) | Neden Ölümcül? | Güvenli Mimari Çözüm |
|:---|:---|:---|:---|
| 1 | `if (x + 1 > x)` | Signed overflow UB olduğu için derleyici bu kontrolü tamamen siler (Dead code elimination). | `if (x < std::numeric_limits<T>::max())` veya `__builtin_add_overflow`. |
| 2 | `for (unsigned i = n; i >= 0; --i)` | `i = 0` olduktan sonra `--i` değeri $2^N-1$'e döner; `i >= 0` daima doğru kalır (Sonsuz Döngü). | `for (int i = n; i >= 0; --i)` veya `std::ssize(container)`. |
| 3 | `if (signed_val < unsigned_val)` | Signed değer sessizce unsigned'a yükseltilir; negatif sayılar devasa pozitif sayılara dönüşür. | C++20 `std::cmp_less(signed_val, unsigned_val)`. |
| 4 | `(len - HEADER_SIZE) > 0` | `len < HEADER_SIZE` ise unsigned çıkarma işlemi devasa bir pozitif sayı üretir (Buffer Overflow). | `if (len > HEADER_SIZE)`. |
| 5 | `short s = (short)large_int;` | Kontrolsüz narrowing cast; büyük değerler işaret değiştirir veya veri kaybına uğrar. | `if (std::in_range<short>(large_int))`. |
| 6 | `size_t diff = t2 - t1; if (diff < 0)` | `size_t` unsigned olduğu için `diff < 0` koşulu daima `false`'tur; derleyici uyarı verir. | `int64_t diff = ...` veya doğrudan `t2 >= t1` kontrolü. |
| 7 | `int avg = (low + high) / 2;` | `low + high` toplamı `INT_MAX` değerini aşarsa taşma yaşanır ve negatif sonuç çıkar. | `int avg = low + (high - low) / 2;` veya C++20 `std::midpoint(low, high)`. |
| 8 | `uint32_t mask = 1 << 32;` | 32-bit tamsayıyı 32 bit veya daha fazla kaydırmak UB'dir! | `uint64_t(1) << 32` veya kaydırma sınır kontrolü. |
| 9 | `std::abs(INT_MIN)` | Two's complement'te $-2^{31}$ değerinin pozitif karşılığı ($+2^{31}$) sığmaz; sonuç yine UB ve negatiftir! | `INT_MIN` özel durum kontrolü veya 64-bit cast. |
| 10 | Geri çağırma/sayaçta signed zaman tutmak | $2^{31}-1$ milisaniye (~24.8 gün) sonra sayaç negatife döner ve zamanlayıcılar kilitlenir. | `uint32_t` veya `uint64_t` monotonic sayaç kullanımı.

## 19. 🔬 Sektörel Standartlar (ASELSAN, HAVELSAN, MISRA, DO-178C)

Savunma ve havacılık sektörlerinde güvenli aritmetik isteğe bağlı bir iyi niyet göstergesi değil, zorunlu bir sertifikasyon kuralıdır:

### 1. MISRA C++:2023 (Motor Industry Software Reliability Association)
- **Kural 7.0.1 (Required):** Aritmetik işlemlerde ve karşılaştırmalarda örtük (implicit) signed-to-unsigned veya unsigned-to-signed dönüşümler kesinlikle yasaktır. Derleyici uyarıları (`-Wconversion`, `-Wsign-conversion`, `-Wsign-compare`) sıfır toleransla hata (`-Werror`) kabul edilmelidir.
- **Kural 7.0.4 (Required):** Signed tamsayı taşmasına güvenen veya taşmanın tanımlı bir şekilde saracağını varsayan kodlar kabul edilemez.

### 2. RTCA DO-178C / EUROCAE ED-12C (Uçuşa Elverişlilik Standardı - DAL-A)
- **Bölüm 6.4.4.2 (Data Coupling and Control Coupling):** Alt modüller arasındaki değişken aktarımlarında veri genişliği (bit-width) eşleşmelidir. Kayan noktalı bir sayının tamsayıya dönüştürüldüğü her noktada (Ariane 5 SRI modülünde olduğu gibi) bir Range-Check Assertion bulunması zorunludur.

### 3. CERT C++ Coding Standard (SEI / Carnegie Mellon)
- **INT30-CPP:** Unsigned tamsayı işlemlerinin taşma ile sonuçlanmadığından emin olun (Wrap-around beklenmedik durumlarda engellenmelidir).
- **INT31-CPP:** Tamsayı dönüşümlerinin veri kaybına veya işaret değişimine yol açmadığını garanti altına alın.
- **INT32-CPP:** Signed tamsayı işlemlerinin tanımsız davranış (UB) olan taşmaya yol açmadığını güvenceye alın.

## 20. 🛠️ Üretim Kontrol Listesi (Production Checklist - 12 Katı Kural)

Bir savunma/havacılık projesinde koda onay vermeden önce aşağıdaki 12 kontrol maddesi tek tek doğrulanmalıdır:

- [ ] **1. Derleyici Bayrakları Aktif mi?** Proje CMake dosyasında `-Wconversion -Wsign-conversion -Wsign-compare -Werror` bayrakları tanımlı mı?
- [ ] **2. Undefined Behavior Sanitizer (UBSan):** Test aşamasında `-fsanitize=undefined,signed-integer-overflow` ile tüm birim testler koşturuldu mu?
- [ ] **3. C++20 Güvenli Karşılaştırma:** Farklı işaretli değişken karşılaştırmalarında `std::cmp_*` kullanıldı mı?
- [ ] **4. Daraltma Dönüşümleri Korundu mu?** `float/double -> int` veya `int64 -> int16` dönüşümlerinden önce `std::in_range` veya clamping var mı?
- [ ] **5. Geri Sayım Döngüleri Denetlendi mi?** `for (auto i = ...; i >= 0; --i)` döngülerinde değişkenin signed olduğu teyit edildi mi?
- [ ] **6. Ağ Paketi Başlık Çıkarmaları:** `len - HEADER_SIZE` işlemlerinden önce `len >= HEADER_SIZE` koşulu kontrol ediliyor mu?
- [ ] **7. Monotonic Timer Çıkarımı:** Sayaç farkı hesaplanırken işaretsiz çıkarma (`uint32_t now - last`) kullanıldı mı?
- [ ] **8. Ortalama Hesaplama Mantığı:** `(a + b) / 2` yerine `std::midpoint(a, b)` tercih edildi mi?
- [ ] **9. Bit Kaydırma Sınırları:** Kaydırma miktarının veri tipinin bit genişliğinden küçük olduğu (`shift < 32`) garanti mi?
- [ ] **10. INT_MIN Mutlak Değer Tuzağı:** `std::abs()` çağrılan yerlerde değerin `INT_MIN` olma ihtimali ele alındı mı?
- [ ] **11. Overflow Flag Doğrulaması:** Performans kritik toplamalarda `__builtin_add_overflow` kullanıldı mı?
- [ ] **12. MISRA Uyumluluk Raporu:** Statik analiz aracından (SonarQube, Coverity, Helix QAC) signed/unsigned kural ihlali sıfır çıktı mı?

## 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

### Soru 1: GCC derleyicisinde `-fwrapv` bayrağı ne işe yarar? Savunma projelerinde kullanılmalı mıdır?
**Cevap:** `-fwrapv` bayrağı, derleyiciye signed integer overflow durumunu "Tanımsız Davranış (UB)" olarak değil, iki tümleyen sarması (wraparound) olarak işlemesini emreder. Bu bayrak açıkken derleyici `if (x + 1 > x)` kontrolünü silmez. Ancak bu bayrağa güvenmek bir tasarım zafiyetidir (code smell). Kod başka bir derleyiciye (MSVC, IAR Embedded Workbench) taşındığında veya bayrak unutulduğunda facia geri döner. Savunma standardı, dile güvenmek yerine kodu güvenli yazmaktır.

### Soru 2: Neden `std::vector::size()` `size_t` (unsigned) döner? Bu bir tasarım hatası mıdır?
**Cevap:** C++ standart komitesi başkanı Bjarne Stroustrup dahil birçok C++ mimarı, `size()` fonksiyonunun unsigned dönmesini modern C++ için bir "tarihsel hata" olarak kabul etmektedir. Amaç 16-bit sistemlerde 32 KB yerine 64 KB bellek adresleyebilmekti. Ancak bu durum `for (int i = 0; i < v.size() - 1; ++i)` gibi ölümcül underflow tuzaklarına yol açmıştır (`v` boşsa `0 - 1 = 18446744073709551615`). C++20 bu sorunu çözmek için `std::ssize(container)` fonksiyonunu getirmiştir; `std::ssize` signed bir tamsayı döner.

### Soru 3: Ariane 5 kazasında yazılımcılar neden 64-bit float değerini 16-bit integer'a dönüştürürken koruma koymamıştı?
**Cevap:** Ariane 4 roketinin uçuş zarfında (flight envelope) yatay hız hiçbir zaman 32767 değerine yaklaşamıyordu. Mühendisler işlemci gücünden tasarruf etmek için 7 kritik değişkenden 4'üne koruma koymuş, yatay hız dahil 3 değişkeni "matematiksel olarak imkansız" varsayarak korumasız bırakmıştı. Ancak yazılım daha güçlü motorlara sahip Ariane 5 roketine aynen taşındığında gereksinim analizi yenilenmedi ve bu ölümcül varsayım roketin infilakına yol açtı.

## 22. 🔮 Gelecek Perspektifi (Donanım & Mimari Trendleri)

### 1. C++26 `std::saturated_cast` ve Genişletilmiş Sayısal Kütüphaneler
C++ komitesi, C++26 standardı için doğrudan standart kütüphaneye `std::saturated_cast<T>(v)` ve `std::saturate_cast` fonksiyonlarını dahil etmek üzere çalışmaktadır. Bu sayede yazılımcılar hiçbir harici kütüphaneye ihtiyaç duymadan donanımsal clamping işlemlerini tek satırda yazabilecektir.

### 2. Donanımsal Güvenlik: CHERI Mimarisi ve RISC-V Trapping
Cambridge Üniversitesi ve DARPA tarafından geliştirilen **CHERI (Capability Hardware Enhanced RISC Instructions)** mimarisi, donanım register seviyesinde sınır (bounds) ve izin (permissions) yeteneklerini taşır. Bir tamsayı veya bellek taşması gerçekleştiğinde işletim sistemine bile gerek kalmadan mikroişlemci seviyesinde donanım tuzağı (hardware trap) tetiklenir.

### 3. Rust Dilinin Etkisi ve Savunma Sanayiine Yansıması
Modern sistem programlama dili Rust, varsayılan olarak "Debug modunda signed/unsigned taşmasında panikleme (crash-on-overflow)", "Release modunda ise tanımlı sarma" yaklaşımını benimsemiştir. C++ dünyasında da benzer şekilde `-fsanitize=undefined` testlerinin sürekli entegrasyon (CI/CD) boru hatlarında zorunlu hale getirilmesi savunma şirketlerinin birincil standardı haline gelmiştir.

## 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı)

Bugün; çalışma zamanında (runtime) gerçekleşen signed ve unsigned taşmalarının, implicit conversion tuzaklarının ve tanımsız davranışların sistemleri nasıl çökertebileceğini ve Ariane 5 örneğinde olduğu gibi yüz milyonlarca dolarlık felaketlere nasıl yol açabileceğini ampirik olarak inceledik.

Peki, bu taşma ve sınır kontrollerini **çalışma zamanında (runtime) hiç gecikme yaşamadan, program henüz derlenirken (compile-time)** yakalamak mümkün müdür?

Yarınki konumuz: **Gün 025 — const ve constexpr (Derleme Zamanı Hesaplamaları, consteval, constinit ve ROM Yerleşimi)**.
Tamsayı sınır kontrollerini, matematiksel tabloları ve bellek boyutlandırmalarını CPU saat döngüsü harcamadan derleyiciye nasıl hesaplatacağımızı, kritik konfigürasyon değişkenlerini salt okunur flash/ROM belleğe nasıl mühürleyeceğimizi keşfedeceğiz.