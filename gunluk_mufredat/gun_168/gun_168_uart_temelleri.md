# GÜN 168: UART Temelleri — Asenkron İletim, Baud Hızı Üretimi, 16x Oversampling, TDR/RDR ve Akış Kontrolü

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz.
```

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
![C++20](https://img.shields.io/badge/Standard-C%2B%2B20-blue.svg?style=flat-square)
![STM32](https://img.shields.io/badge/Hardware-STM32%20USART%20Peripheral-orange.svg?style=flat-square)
![Communication](https://img.shields.io/badge/Protocol-UART%20%2F%20RS--232%20%2F%20RS--485-green.svg?style=flat-square)
![Defense Grade](https://img.shields.io/badge/Domain-Avionics%20%2F%20Telemetry-red.svg?style=flat-square)

---

## 1. Zihinsel Model ve Mimari Büyük Resim (UART Nedir, Neden Asenkron?)

Gömülü sistemler ve savunma sanayii aviyonik mimarilerinde iki mikrodenetleyici veya bir görev bilgisayarı (Mission Computer) ile harici bir alt sistem (GPS/INS, Telemetri Modülü, Lazer Mesafe Ölçer) arasındaki en temel ve vazgeçilmez haberleşme protokolü **UART** (Universal Asynchronous Receiver-Transmitter - Evrensel Asenkron Alıcı-Verici)'tır.

### "Asenkron" Ne Demektir ve Neden Tercih Edilir?
SPI (Serial Peripheral Interface) veya I2C gibi senkron protokollerde, verinin hangi saat vuruşunda geçerli olduğunu bildiren ortak bir **fiziksel saat hattı (SCLK / SCL)** bulunur. Ancak UART'ta harici bir saat hattı **YOKTUR**.
- **Avantajı:** Fiziksel kablo sayısı minimuma iner. Sadece iki hat (TX: Gönderim, RX: Alım) ve ortak zemin referansı (GND) yeterlidir.
- **Mühendislik Meydan Okuması:** Paylaşımlı bir clock olmadan alıcı taraf, gelen bitlerin ne zaman başladığını, her bitin ne kadar sürdüğünü ve bitin tam olarak hangi mikrosaniyede okunması gerektiğini nasıl bilir?

### UART İletim Protokolünün Çözümü:
1. **Önceden Uzlaşılmış Hız (Baud Rate):** Verici ve alıcı, veri alışverişine başlamadan önce saniyede kaç sembol/bit iletileceği konusunda mutabık kalmak zorundadır (örneğin $115200\ \text{bps}$). Bir bitin hattan geçiş süresi:
   $$T_{\text{bit}} = \frac{1}{\text{Baud Rate}} = \frac{1}{115200} \approx 8.6805\ \mu\text{s}$$
2. **Boşta Durum (IDLE State = Lojik 1):** Veri akışı yokken hat sürekli lojik 1 (HIGH / 3.3V) seviyesinde tutulur. Bu, hattın kopup kopmadığını (Line Break) anlamayı sağlar.
3. **Başlangıç Biti (START Bit = Lojik 0):** İletişim başlayacağı an verici hattı $1 \to 0$ seviyesine çeker. Bu düşen kenar (Falling Edge), alıcının dahili sayacını ve zamanlama devresini senkronize eder.
4. **Veri Bitleri (LSB First):** En önemsiz bitten (Bit 0) en önemli bite (Bit 7) doğru 8 adet veri biti hatta sürülür.
5. **İsteğe Bağlı Eşlik Biti (Parity Bit):** Verideki 1'lerin sayısının tek (Odd) veya çift (Even) olduğunu doğrulayarak tek bitlik donanımsal hata sezimi sağlar.
6. **Durdurma Biti (STOP Bit = Lojik 1):** Çerçevenin bittiğini belirtmek için hat en az 1 (veya 1.5, 2) bit süresi boyunca lojik 1'e çekilir. Böylece alıcının saat kayması sıfırlanır ve hat bir sonraki baytın START bitine hazır hale gelir.

```
       IDLE     START               VERİ BİTLERİ (LSB -> MSB)                  STOP     IDLE
  3.3V -----+         +-------+-------+-------+-------+-------+-------+-------+-------+-------
            |         |  D0   |  D1   |  D2   |  D3   |  D4   |  D5   |  D6   |  D7   |       
  0.0V      +---------+-------+-------+-------+-------+-------+-------+-------+       +-------
             <--Tbit--> <----------------- 8 x Tbit -------------------------> <--Tbit->
            (Düşen Kenar)  (Bitlerin merkezinde 16x Oversampling Majority Voting)
```

## 2. Fiziksel Seviye ve Elektriksel Standartlar (TTL, RS-232, RS-422, RS-485)

UART mantıksal bir protokoldür; elektrik sinyallerinin voltaj seviyesini ve iletim ortamını ise fiziksel katman standartları belirler.

### 1. TTL / CMOS Mantığı (0V - 3.3V / 5V):
Mikrodenetleyici (MCU) pinlerinden çıkan saf sinyaldir.
- **Lojik 0:** $0\ \text{V}$ (GND)
- **Lojik 1:** $3.3\ \text{V}$ (veya $5\ \text{V}$)
- **Kullanım:** Aynı kart üzerindeki çipler arası kısa mesafe ($< 30\ \text{cm}$) haberleşme. Yüksek empedanslı hatlar ortamdaki elektromanyetik gürültüden (EMI) anında etkilenir.

### 2. RS-232 Standartı (Ters Çevrilmiş Yüksek Voltaj):
Eski PC seri portları ve laboratuvar cihazlarında kullanılır (MAX3232 seviye dönüştürücü entegre ile sürülür).
- **Lojik 1 (MARK):** $-3\ \text{V}$ ila $-15\ \text{V}$
- **Lojik 0 (SPACE):** $+3\ \text{V}$ ila $+15\ \text{V}$
- **Özellik:** Voltaj farkı yüksek olduğu için gürültüye dayanımı TTL'e göre iyidir ($15 - 20\ \text{metre}$).

### 3. RS-422 ve RS-485 (Diferansiyel Sinyalleşme — Savunma Standardı):
Savunma sanayiinde (örneğin ASELSAN zırhlı araç alt sistemleri, ROKETSAN güdüm kiti kanatçık motorları, MIL-STD haberleşme hatları) tek uçlu (Single-Ended) sinyaller ASLA uzun mesafede kullanılmaz!
- İki kablo kullanılır: $A$ ve $B$ hatları.
- Veri, iki kablo arasındaki potansiyel farktan okunur: $V_{AB} = V_A - V_B$.
- **Ortak Mod Gürültü Reddi (Common-Mode Rejection):** Dışarıdan bir EMI paraziti (motor gürültüsü, radar darbesi) bindiğinde her iki kabloya da aynı miktarda voltaj biner. Diferansiyel alıcı farkı aldığı için $(V_A + V_{\text{noise}}) - (V_B + V_{\text{noise}}) = V_A - V_B$ gürültü tamamen yok olur!
- **Mesafe:** $1200\ \text{metre}$, $10\ \text{Mbps}$ hız.

### Ortak Toprak (GND) Bağlantısının Hayati Önemi:
İki bağımsız sistem (örneğin İHA Görev Bilgisayarı ve Gimbal Kamera) TTL veya RS-232 ile bağlanırken **yalnızca TX ve RX hatlarını bağlamak ölümcül bir amatör hatasıdır**.
- Her voltaj bir referansa göre ölçülür ($V = V_{\text{pin}} - V_{\text{GND}}$).
- Eğer iki cihazın toprak seviyeleri arasında potansiyel farkı (Ground Shift) varsa, verici tarafın $0\ \text{V}$ seviyesi alıcı tarafın gözünde $1.8\ \text{V}$ görünebilir. Eşik voltajı aşıldığında alıcı tüm bitleri 1 veya çöp okur. **GND pini her zaman ortaklanmalıdır!**

## 3. STM32 USART Donanım Mimarisi: Baud Rate Generator (BRR)

STM32 serisi mikrodenetleyicilerde (Cortex-M4/M7/H7) USART donanımı, APB1 veya APB2 çevre birimi veri yollarından (Peripheral Bus) gelen saat frekansını bölerek tam istenen baud hızını üretir.

### Baud Hızı Bölücü Formülü:
STM32 Reference Manual (RM0090 / RM0433) standardına göre:
$$\text{Baud Rate} = \frac{f_{\text{PCLK}}}{8 \times (2 - \text{OVER8}) \times \text{USARTDIV}}$$

Burada:
- $f_{\text{PCLK}}$: USART donanımının bağlı olduğu çevresel saat frekansı (örneğin APB1 için $42\ \text{MHz}$, APB2 için $84\ \text{MHz}$).
- $\text{OVER8}$: CR1 yazmacındaki oversampling seçimi ($0 \implies 16\times\text{ oversampling}$, $1 \implies 8\times\text{ oversampling}$).
- $\text{USARTDIV}$: Kesirli bir bölme katsayısıdır.

### USART_BRR Yazmacının Yapısı (16-bit):
$16\times$ oversampling modunda ($\text{OVER8} = 0$):
- `BRR[15:4]` (12 bit): **DIV_Mantissa** (Bölümün tam sayı kısmı).
- `BRR[3:0]` (4 bit): **DIV_Fraction** (Bölümün kesirli kısmı, $1/16$ adımlarla).

$$\text{Fractional Value} = \text{round}\left( (\text{USARTDIV} - \lfloor\text{USARTDIV}\rfloor) \times 16 \right)$$
$$\text{BRR Register} = (\text{Mantissa} \ll 4) \mid (\text{Fraction} \& 0\text{xF})$$

### Aviyonik Saat Sapması ve İzin Verilen Hata Limiti:
Donanımsal saat kristalinin frekansı, istenen baud hızına tam olarak bölünmeyebilir. Örneğin $42\ \text{MHz}$ APB saatinde $115200\ \text{baud}$ hedeflendiğinde:
$$\text{USARTDIV} = \frac{42000000}{16 \times 115200} = 22.786458$$
- $\text{Mantissa} = 22$
- $\text{Fraction} = \text{round}(0.786458 \times 16) = \text{round}(12.583) = 13 = 0\text{xD}$
- $\text{BRR} = (22 \ll 4) \mid 13 = 0\text{x016D} = 365$
- Gerçekleşen Baud: $\frac{42000000}{16 \times (22 + 13/16)} = \frac{42000000}{16 \times 22.8125} = 115068.49\ \text{bps}$
- **Baud Hata Oranı:**
  $$\text{Error (\%)} = \frac{115068.49 - 115200}{115200} \times 100 = -0.114\%$$
Askeri aviyonik standartlarında (DO-254 / MIL-STD-810) UART iletişiminde kabul edilebilir maksimum saat frekans sapması **$<\pm 2.5\%$** olmalıdır. Aksi takdirde 8. bit ve STOP bitinde örnekleme penceresi kayar ve Framing Error (FE) oluşur!

## 4. Veri Yazmaçları ve Durum Bayrakları: TDR, RDR, TXE, TC, RXNE, ORE

STM32 USART donanımı yüksek performans ve kesintisiz aktarım sağlamak için **çift tamponlu (Double-Buffered)** mimariye sahiptir.

```
+-----------------------------------------------------------------------------------+
|                     STM32 USART ÇİFT TAMPONLU DONANIM BLOK DİYAGRAMI               |
+-----------------------------------------------------------------------------------+

[ VERİCİ YOLU (TX) ]
  CPU / DMA  -----> [ USART_TDR (Transmit Data Register) ]
                                | (Donanımsal Anında Transfer)
                                v
                    [ TX Shift Register (Kaydırma Yazmacı) ] ----> [ TX Pini (Seri Çıkış) ]
                    (Bitler tek tek hatta verilirken TDR boşalır: TXE = 1)
                    (Tüm bitler ve STOP biti bittiğinde:          TC = 1)

[ ALICI YOLU (RX) ]
  [ RX Pini (Seri Giriş) ] ----> [ RX Shift Register (Kaydırma Yazmacı) ]
                                            | (8-bit tamamlanınca aktarılır)
                                            v
  CPU / DMA  <----- [ USART_RDR (Receive Data Register) ]  (Yeni veri geldi: RXNE = 1)
                    (Eğer CPU RDR'yi okumadan yeni veri gelirse:    ORE = 1 Overrun!)
```

### Kritik Durum Bayrakları (Status Register - USART_SR / USART_ISR):
1. **TXE (Transmit Data Register Empty):**
   - TDR yazmacındaki veri Shift Register'a aktarıldığı anda donanım tarafından `1` yapılır.
   - **Anlamı:** "TDR boştur, yeni bir bayt yazabilirsin." Verinin hattan çıkıp bittiği anlamına **GELMEZ**!
2. **TC (Transmission Complete):**
   - Shift Register'daki son bit (STOP biti) dahil tüm veri hattan çıktığında ve TDR'da yeni veri yoksa `1` olur.
   - **Kritik Kullanım:** RS-485 alıcı-verici yön pinini (DE - Driver Enable) dinleme moduna geri çekmek için TXE değil, **kesinlikle TC beklenmelidir**! TXE görüp DE pini LOW yapılırsa son baytın yarısı hattan çıkamadan kesilir!
3. **RXNE (Read Data Register Not Empty):**
   - Shift Register'daki bitler tamamlanıp RDR yazmacına aktarıldığında `1` olur. CPU RDR'den okuma yaptığında donanımsal olarak otomatik `0`'a düşer.
4. **ORE (Overrun Error):**
   - `RXNE = 1` iken (yani önceki bayt henüz CPU tarafından okunmamışken) Shift Register'a yeni bir bayt biter ve RDR'ye yazılmaya çalışılırsa tetiklenir. Önceki veri korunur, yeni gelen veri **KAYBOLUR**. Aviyonik sistemlerde telemetri kaybının bir numaralı sebebidir.
5. **FE (Framing Error):**
   - Beklenen STOP biti zamanında hatta lojik 1 tespit edilemezse oluşur. Genellikle baud hızı uyumsuzluğu, aşırı hat gürültüsü veya kablo kopması durumunda görülür.

```python
# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 1 — STM32 Baud Rate Generator (BRR) Hesaplayıcı
Farklı PCLK Frekanslarında Mantissa, Fraction ve Hata Yüzdesi Analizi
"""

from typing import Dict, List, Tuple

class STM32BaudRateCalculator:
    """
    STM32 USART Baud Rate Register (BRR) Hesaplama Motoru.
    Standart 16x oversampling (OVER8=0) ve yüksek hızlı 8x oversampling (OVER8=1) destekler.
    """
    def __init__(self, pclk_hz: int):
        self.pclk_hz = pclk_hz

    def calculate_brr(self, target_baud: int, over8: int = 0) -> Dict[str, float]:
        oversampling = 8 if over8 == 1 else 16
        usart_div = self.pclk_hz / (oversampling * target_baud)
        
        mantissa = int(usart_div)
        fraction_float = (usart_div - mantissa) * oversampling
        fraction = round(fraction_float)

        # Fraction taşma kontrolü (Örn: 16x'te fraction 16 olursa mantissa 1 artar)
        if fraction >= oversampling:
            mantissa += 1
            fraction = 0

        # Donanımsal BRR yazmaç değeri
        if over8 == 0:
            brr_reg = (mantissa << 4) | (fraction & 0x0F)
            actual_div = mantissa + (fraction / 16.0)
        else:
            # OVER8=1 iken fraction 3-bit'tir (Bit [2:0]), Bit 3 sıfır olmalıdır
            brr_reg = (mantissa << 4) | (fraction & 0x07)
            actual_div = mantissa + (fraction / 8.0)

        actual_baud = self.pclk_hz / (oversampling * actual_div) if actual_div > 0 else 0
        error_pct = ((actual_baud - target_baud) / target_baud) * 100.0

        return {
            "pclk_mhz": self.pclk_hz / 1e6,
            "target_baud": target_baud,
            "over8": over8,
            "usart_div": round(usart_div, 4),
            "mantissa": mantissa,
            "fraction": fraction,
            "brr_hex": f"0x{brr_reg:04X}",
            "actual_baud": round(actual_baud, 2),
            "error_pct": round(error_pct, 4),
            "is_avionics_safe": abs(error_pct) < 2.5
        }

# Simülasyon ve Doğrulama
pclk_apb1 = 42_000_000 # 42 MHz (STM32F4 APB1 Bus)
pclk_apb2 = 84_000_000 # 84 MHz (STM32F4 APB2 Bus)
standard_bauds = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

calc_apb1 = STM32BaudRateCalculator(pclk_apb1)
results_apb1 = [calc_apb1.calculate_brr(b, over8=0) for b in standard_bauds]

print(f"[*] STM32 USART BRR Analizi (PCLK = {pclk_apb1/1e6} MHz, OVER8=0):")
print(f"{'Target Baud':>12} | {'BRR Hex':>8} | {'Mantissa':>8} | {'Fraction':>8} | {'Actual Baud':>12} | {'Error (%)':>10} | {'Safety'}")
print("-" * 75)
for r in results_apb1:
    safe_str = "[PASS] Safe" if r["is_avionics_safe"] else "[FAIL] Risky"
    print(f"{r['target_baud']:>12} | {r['brr_hex']:>8} | {r['mantissa']:>8} | {r['fraction']:>8} | {r['actual_baud']:>12.2f} | {r['error_pct']:>9.3f}% | {safe_str}")

# Katı Doğrulama Testi
res_115200 = calc_apb1.calculate_brr(115200, over8=0)
assert res_115200["mantissa"] == 22, f"Beklenen mantissa 22, bulunan: {res_115200['mantissa']}"
assert res_115200["fraction"] == 13, f"Beklenen fraction 13, bulunan: {res_115200['fraction']}"
assert res_115200["brr_hex"] == "0x016D", f"Beklenen BRR 0x016D, bulunan: {res_115200['brr_hex']}"
assert abs(res_115200["error_pct"]) < 0.2, "Baud hatası %0.2'den küçük olmalı!"
print("\n[HÜCRE 6] STM32 Baud Rate Generator hesaplama motoru başarıyla doğrulandı.")
```

## 5. UART 16x/8x Oversampling ve Majority Voting Mantığı

Asenkron hatta gelen bitlerin tam ortasını bulmak ve hat gürültüsünü süzmek için STM32 donanımı **Oversampling (Aşırı Örnekleme)** tekniğini kullanır.

### $16\times$ Oversampling Çalışma Prensibi:
Alıcı donanım, beklenen her bit süresi ($T_{\text{bit}}$) boyunca dahili saatini $16$ eşit dilime böler (Dilim $0$ ila $15$).
1. **Düşen Kenar Tespiti (Falling Edge Detection):**
   - Hat boşta (IDLE = 1) iken sürekli taranır.
   - Lojik 0 tespit edildiğinde START bitinin başladığı varsayılır. Donanım saat sayacını sıfırlar.
2. **Başlangıç Biti Doğrulaması:**
   - Örnekleme dilimleri 8, 9 ve 10'da hat tekrar okunur.
   - Bu 3 örnekten en az 2'si lojik 0 değilse (örneğin hat anlık bir gürültü darbesi almışsa), sahte alarm kabul edilir ve alıcı derhal IDLE durumuna geri döner.
3. **Veri Bitlerinin Örneklenmesi (Majority Voting - 2/3 Çoğunluk Oylaması):**
   - Takip eden her bit için dilim 8, 9 ve 10 anlarında hat seviyesi 3 kez okunur.
   - **Çoğunluk Kuralı:**
     - Eğer okunan değerler $[1, 1, 0]$ ise bit **$1$** kabul edilir, ancak durum yazmacındaki Gürültü Bayrağı (`NF - Noise Flag`) set edilir!
     - Eğer okunan değerler $[0, 0, 1]$ ise bit **$0$** kabul edilir (`NF = 1`).
     - Eğer okunan değerler $[1, 1, 1]$ veya $[0, 0, 0]$ ise gürültüsüz temiz bit olarak kaydedilir (`NF = 0`).

```
  Tek Bit Süresi (Tbit) = 16 Alt Örnekleme Darbesi (0 .. 15)
  | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
                                    ^   ^   ^
                                    |---|---|
                         Majority Voting Örnekleme Noktaları
                         (En kararlı bölge, kenar gürültülerinden uzak)
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 2 — UART RX 16x Oversampling ve Majority Voting Simülatörü
Gürültülü Sayısal Sinyalin Örneklenmesi, Çoğunluk Oylaması ve NF (Noise Flag) Tespiti
"""

import numpy as np
from typing import List, Tuple, Dict

class UARTOversamplingReceiver:
    """
    16x Oversampling Alıcı Donanım Simülatörü.
    Start bit düşen kenar tespiti ve 8-9-10 dilimlerinde majority voting uygular.
    """
    def __init__(self, samples_per_bit: int = 16):
        self.samples_per_bit = samples_per_bit

    def decode_stream(self, raw_samples: List[int]) -> Dict[str, any]:
        idx = 0
        n_samples = len(raw_samples)
        decoded_bits = []
        noise_flags = []
        sample_points = []

        # 1. Start Bit Arama (1 -> 0 düşen kenar)
        while idx < n_samples and raw_samples[idx] == 1:
            idx += 1

        if idx >= n_samples:
            return {"status": "NO_START_BIT", "bits": [], "noise": []}

        # Start bit düşen kenar bulundu. Örnekleme sayacını başlat
        start_edge = idx
        
        # 1 Start Biti + 8 Veri Biti + 1 Stop Biti = 10 Bit Toplam
        for bit_idx in range(10):
            bit_start = start_edge + bit_idx * self.samples_per_bit
            if bit_start + 10 >= n_samples:
                break # Akış erken bitti

            # 8, 9, 10 numaralı örnekleme dilimleri
            s8 = raw_samples[bit_start + 8]
            s9 = raw_samples[bit_start + 9]
            s10 = raw_samples[bit_start + 10]
            sample_points.append(bit_start + 9) # Orta nokta

            vote_sum = s8 + s9 + s10
            bit_val = 1 if vote_sum >= 2 else 0
            has_noise = (vote_sum == 1 or vote_sum == 2) # Tam mutabakat yoksa gürültü vardır

            decoded_bits.append(bit_val)
            noise_flags.append(has_noise)

        # Doğrulama: Bit 0 Start bit (0 olmalı), Bit 9 Stop bit (1 olmalı)
        is_valid_frame = (len(decoded_bits) == 10 and decoded_bits[0] == 0 and decoded_bits[-1] == 1)
        
        # 8-bit veri (LSB first)
        data_byte = 0
        if is_valid_frame:
            data_bits = decoded_bits[1:9]
            for i, b in enumerate(data_bits):
                data_byte |= (b << i)

        return {
            "status": "SUCCESS" if is_valid_frame else "FRAMING_ERROR",
            "decoded_bits": decoded_bits,
            "data_byte_hex": f"0x{data_byte:02X}" if is_valid_frame else None,
            "data_char": chr(data_byte) if is_valid_frame and 32 <= data_byte <= 126 else None,
            "noise_detected": any(noise_flags),
            "noise_flags": noise_flags,
            "sample_points": sample_points
        }

# Test: 'A' Harfi (ASCII 65 = 0x41 = 0b01000001)
# LSB first: D0=1, D1=0, D2=0, D3=0, D4=0, D5=0, D6=1, D7=0
# Tam UART Çerçevesi: [START=0, 1, 0, 0, 0, 0, 0, 1, 0, STOP=1]
tx_bits = [0, 1, 0, 0, 0, 0, 0, 1, 0, 1]

# 16x oversampling ile ideal sinyal üret
sim_samples = []
# Başlangıçta 8 örnek IDLE (1)
sim_samples.extend([1] * 8)
for b in tx_bits:
    sim_samples.extend([b] * 16)
# Sonda 8 örnek IDLE (1)
sim_samples.extend([1] * 8)

# Hatta Gürültü Enjekte Et: 
# D0 bitinin 8. dilimine yapay gürültü darbesi koy (Normalde 1, gürültüyle 0 yap)
# Sinyal indeksi: 8 (idle) + 16 (start) + 8 (D0'ın 8. örneği) = 32
sim_samples[32] = 0 # Anlık glitch

rx_sim = UARTOversamplingReceiver()
rx_result = rx_sim.decode_stream(sim_samples)

print("[*] UART 16x Oversampling ve Majority Voting Testi:")
print(f"  [+] Durum            : {rx_result['status']}")
print(f"  [+] Çözülen Bayt (Hex): {rx_result['data_byte_hex']} ({rx_result['data_char']})")
print(f"  [+] Gürültü Sezildi mi: {rx_result['noise_detected']} (NF Bayrağı Set Edildi)")
print(f"  [+] Çözülen Bitler   : {rx_result['decoded_bits']}")

assert rx_result["status"] == "SUCCESS", "Frame başarılı çözülmeliydi!"
assert rx_result["data_byte_hex"] == "0x41", f"Beklenen 0x41 ('A'), okunan: {rx_result['data_byte_hex']}"
assert rx_result["noise_detected"] is True, "D0 bitindeki glitch sezilmeliydi!"
print("\n[HÜCRE 8] 16x Oversampling ve Majority Voting simülatörü başarıyla doğrulandı.")
```

## 6. Donanım Akış Kontrolü (Hardware Flow Control - RTS/CTS)

Yüksek hızlı veri aktarımında ($> 115200\ \text{baud}$) alıcı mikrodenetleyici başka bir kritik kesmeyle meşgulse veya işletim sistemi (RTOS) görev geçişi yapıyorsa, `USART_RDR` yazmacındaki veri zamanında okunamaz ve **Overrun Error (ORE)** meydana gelir.

Bu felaketi donanımsal olarak engellemek için **RTS / CTS (Request to Send / Clear to Send)** hatları kullanılır.

### RTS ve CTS Pinlerinin Çalışma Mantığı:
STM32'de Hardware Flow Control aktifleştirildiğinde (`USART_CR3_RTSE` ve `USART_CR3_CTSE` bitleri):

1. **RTS (Request to Send / Ready to Receive - Alıcı Çıkışı):**
   - Alıcı MCU tarafından sürülür.
   - Alıcının RDR yazmacı boşken ve yeni veri kabul edebiliyorken $\text{RTS} = 0$ (Aktif LOW) seviyesindedir.
   - RDR yazmacına yeni bir bayt aktarıldığı anda donanım RTS pinini otomatik olarak $1$ (HIGH) seviyesine çeker! Bu, vericiye *"Dur! Bendeki baytı CPU henüz okumadı, yeni bayt gönderme!"* mesajıdır.
   - CPU RDR'yi okuduğu anda donanım RTS'yi tekrar $0$'a düşürerek trafiği açar.
2. **CTS (Clear to Send - Verici Girişi):**
   - Verici MCU tarafından dinlenir (Alıcının RTS pinine bağlanır).
   - Verici yeni bir bayt göndermeden önce donanımsal olarak CTS pinine bakar.
   - Eğer $\text{CTS} = 0$ ise baytın START bitini hatta sürer.
   - Eğer $\text{CTS} = 1$ ise verici donanımı aktarımı Shift Register seviyesinde beklemeye alır; hat IDLE (1) kalır. CTS tekrar 0 olana kadar tek bir bit bile çıkmaz!

```
   [ VERİCİ MCU ]                             [ ALICI MCU ]
  +--------------+                           +--------------+
  |           TX |-------------------------->| RX           |
  |           RX |<--------------------------| TX           |
  |          CTS |<--------------------------| RTS          |
  |          RTS |-------------------------->| CTS          |
  |          GND |---------------------------| GND          |
  +--------------+                           +--------------+
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 3 — Donanım Akış Kontrolü (RTS/CTS) vs Overrun Error (ORE) Simülasyonu
Akış Kontrolsüz Veri Kaybı ile RTS/CTS Güvenli Aktarımının Karşılaştırmalı Modeli
"""

from typing import List, Dict

class UARTSinkDevice:
    """Yavaş alıcı cihaz simülasyonu (Küçük FIFO tamponu ve sınırlı CPU tüketim hızı)"""
    def __init__(self, fifo_capacity: int = 4, use_hardware_flow_control: bool = False):
        self.fifo_capacity = fifo_capacity
        self.use_hw_flow = use_hardware_flow_control
        self.fifo = []
        self.rts_pin = 0 # 0: Ready to Receive (LOW), 1: FIFO Dolu / Meşgul (HIGH)
        self.overrun_errors = 0
        self.received_bytes = []

    def can_accept_byte(self) -> bool:
        if self.use_hw_flow:
            return self.rts_pin == 0
        return True # Akış kontrolü yoksa daima hat açık varsayılır

    def receive_byte(self, byte_val: int):
        if len(self.fifo) >= self.fifo_capacity:
            # Overrun Error! Eski veri okunmadan yeni veri geldi, yeni veri ezildi
            self.overrun_errors += 1
        else:
            self.fifo.append(byte_val)
            self.received_bytes.append(byte_val)
            # Eğer tampon dolduysa ve HW flow açıksa RTS'yi 1 (HIGH) yap
            if self.use_hw_flow and len(self.fifo) >= self.fifo_capacity:
                self.rts_pin = 1

    def process_one_byte_from_fifo(self):
        """Alıcı CPU bir baytı işleyip tamponu boşaltır"""
        if self.fifo:
            self.fifo.pop(0)
            if self.use_hw_flow and len(self.fifo) < self.fifo_capacity:
                self.rts_pin = 0 # Yer açıldı, RTS tekrar LOW (Gönderime hazır)

# Test Senaryosu: 12 Baytlık Hızlı Telemetri Verisi
telemetry_data = list(b"ROKETSAN_NAV") # 12 bayt

# Senaryo A: Donanım Akış Kontrolü YOK (Akış Kontrolsüz Patlama)
sink_no_flow = UARTSinkDevice(fifo_capacity=4, use_hardware_flow_control=False)
for b in telemetry_data:
    sink_no_flow.receive_byte(b) # CPU hiç okuma fırsatı bulamadan peş peşe 12 bayt geldi

# Senaryo B: Donanım Akış Kontrolü AKTİF (RTS/CTS ile Vericiyi Frenleme)
sink_with_flow = UARTSinkDevice(fifo_capacity=4, use_hardware_flow_control=True)
bytes_to_send = list(telemetry_data)
tx_cycles = 0

while bytes_to_send or sink_with_flow.fifo:
    tx_cycles += 1
    # Verici CTS (Alıcının RTS'si) pinini dinler
    if bytes_to_send and sink_with_flow.can_accept_byte():
        next_byte = bytes_to_send.pop(0)
        sink_with_flow.receive_byte(next_byte)
    
    # Her 2 döngüde bir alıcı CPU bir bayt tüketebilsin
    if tx_cycles % 2 == 0:
        sink_with_flow.process_one_byte_from_fifo()

print("[*] Donanım Akış Kontrolü (RTS/CTS) Dayanıklılık Raporu:")
print(f"  [!] Akış Kontrolsüz Alınan Bayt : {len(sink_no_flow.received_bytes)} / {len(telemetry_data)}")
print(f"  [!] Akış Kontrolsüz ORE Hataları: {sink_no_flow.overrun_errors} bayt kayboldu!")
print(f"  [+] RTS/CTS ile Alınan Bayt     : {len(sink_with_flow.received_bytes)} / {len(telemetry_data)}")
print(f"  [+] RTS/CTS ile ORE Hataları    : {sink_with_flow.overrun_errors} (SIFIR Veri Kaybı)")

assert sink_no_flow.overrun_errors == 8, f"Beklenen ORE 8, bulunan: {sink_no_flow.overrun_errors}"
assert sink_with_flow.overrun_errors == 0, "RTS/CTS ile ORE kesinlikle 0 olmalı!"
assert len(sink_with_flow.received_bytes) == 12, "Tüm veri eksiksiz alınmalıydı!"
print("\n[HÜCRE 10] Donanım akış kontrolü ve ORE koruma modeli başarıyla doğrulandı.")
```

## 7. STM32 Polling (Yoklama) Tabanlı Bare-Metal UART Sürücüsü

En temel gömülü sürücü seviyesi **Polling (Yoklama / Bloklayıcı)** yöntemidir. Bu yöntemde CPU, USART durum yazmacındaki (SR) bayrakların `1` olmasını bir `while` döngüsü içinde bekler.

### Polling İletim Algoritması:
1. `USART_SR_TXE` bayrağını bekle:
   ```c
   while (!(USART1->SR & USART_SR_TXE)); // TDR boşalana kadar bekle
   USART1->DR = byte_to_send;            // Veriyi yaz
   ```
2. Son bayttan sonra iletimin bittiğini garantilemek için `USART_SR_TC` bayrağını bekle:
   ```c
   while (!(USART1->SR & USART_SR_TC));  // Shift register tamamen boşalsın
   ```

### Polling Yönteminin Bedeli ve Riskleri:
- **CPU İsrafı (CPU Wastage):** $115200\ \text{baud}$ hızında 1 baytın iletimi $\approx 86.8\ \mu\text{s}$ sürer. $168\ \text{MHz}$ hızında çalışan bir Cortex-M4 çekirdeği bu sürede yaklaşık **$14.500$ makine komutu** çalıştırabilecekken `while` döngüsünde boşuna yanar!
- **Kilitlenme Riski (Deadlock / Hang):** Eğer donanım hattı koptuysa veya USART saati RCC tarafından açılmadıysa, `while` döngüsü sonsuza kadar döner ve Watchdog Timer (WDT) sistemi resetler. Bu nedenle endüstriyel sürücülerde **daima bir Timeout (Zaman Aşımı) sayacı** bulunmalıdır!

```python
# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 4 — C++20 STM32 Bare-Metal USART Driver Simülatörü
MMIO Yazmaçları, TXE, TC, RXNE Yoklaması ve Timeout Korumalı Bloklayıcı Sürücü
"""

from typing import Optional, Tuple

class VirtualSTM32USART:
    """
    STM32 USART Donanımının Sanal Yazmaç Modeli (MMIO):
    SR  : Status Register (TXE, TC, RXNE, ORE, FE, PE)
    DR  : Data Register (TDR yazma / RDR okuma)
    CR1 : Control Register 1 (UE, TE, RE)
    """
    USART_SR_PE   = (1 << 0)
    USART_SR_FE   = (1 << 1)
    USART_SR_NF   = (1 << 2)
    USART_SR_ORE  = (1 << 3)
    USART_SR_RXNE = (1 << 5)
    USART_SR_TC   = (1 << 6)
    USART_SR_TXE  = (1 << 7)

    def __init__(self):
        self.SR = self.USART_SR_TXE | self.USART_SR_TC # Başlangıçta hat boşta
        self.TDR = 0
        self.RDR = 0
        self.tx_shift_reg = None
        self.rx_shift_reg = None
        self.tx_wire = [] # Hatta çıkan baytlar

    def write_DR(self, value: int):
        self.TDR = value & 0xFF
        self.SR &= ~self.USART_SR_TXE # TDR doldu, TXE = 0
        self.SR &= ~self.USART_SR_TC  # İletim başladı, TC = 0

    def read_DR(self) -> int:
        val = self.RDR
        self.SR &= ~self.USART_SR_RXNE # RDR okundu, RXNE temizlendi
        return val

    def step_hardware_cycle(self):
        """Donanımın arka plan saat çevrimi"""
        # TDR'dan Shift Register'a aktarım
        if not (self.SR & self.USART_SR_TXE) and self.tx_shift_reg is None:
            self.tx_shift_reg = self.TDR
            self.SR |= self.USART_SR_TXE # TDR boşaldı, yeni bayt kabul edebilir

        # Shift Register'dan kabloya aktarım
        elif self.tx_shift_reg is not None:
            self.tx_wire.append(self.tx_shift_reg)
            self.tx_shift_reg = None
            if self.SR & self.USART_SR_TXE:
                self.SR |= self.USART_SR_TC # Hem TDR hem Shift boşaldı -> TC = 1

    def inject_rx_byte(self, byte_val: int):
        """Dış dünyadan RX pinine bayt gelmesi"""
        if self.SR & self.USART_SR_RXNE:
            self.SR |= self.USART_SR_ORE # Önceki okunmadan geldi: Overrun!
        else:
            self.RDR = byte_val & 0xFF
            self.SR |= self.USART_SR_RXNE # Yeni veri hazır

class STM32PollingUARTDriver:
    """Üretim standardında C++20 benzeri Timeout korumalı Polling sürücüsü"""
    def __init__(self, hardware: VirtualSTM32USART):
        self.hw = hardware

    def transmit_byte(self, byte_val: int, timeout_cycles: int = 100) -> bool:
        cycles = 0
        # 1. TXE bekle
        while not (self.hw.SR & VirtualSTM32USART.USART_SR_TXE):
            self.hw.step_hardware_cycle()
            cycles += 1
            if cycles >= timeout_cycles:
                return False # Zaman aşımı!

        # 2. Veriyi yaz
        self.hw.write_DR(byte_val)
        self.hw.step_hardware_cycle()
        return True

    def flush_tx(self, timeout_cycles: int = 100) -> bool:
        """Tüm bitlerin hattan çıktığını garantile (TC bekle)"""
        cycles = 0
        while not (self.hw.SR & VirtualSTM32USART.USART_SR_TC):
            self.hw.step_hardware_cycle()
            cycles += 1
            if cycles >= timeout_cycles:
                return False
        return True

    def receive_byte(self, timeout_cycles: int = 100) -> Tuple[bool, Optional[int]]:
        cycles = 0
        while not (self.hw.SR & VirtualSTM32USART.USART_SR_RXNE):
            self.hw.step_hardware_cycle()
            cycles += 1
            if cycles >= timeout_cycles:
                return False, None
        return True, self.hw.read_DR()

# Sürücü Doğrulama Testi
virt_hw = VirtualSTM32USART()
driver = STM32PollingUARTDriver(virt_hw)

# 1. İletim Testi
test_payload = b"ASELSAN"
for b in test_payload:
    assert driver.transmit_byte(b) is True, "Bayt iletimi başarısız!"
assert driver.flush_tx() is True, "TC bekleme zaman aşımına uğradı!"

transmitted_str = bytes(virt_hw.tx_wire).decode('ascii')
print("[*] Polling Tabanlı UART İletim Testi:")
print(f"  [+] Gönderilen String : {transmitted_str}")
assert transmitted_str == "ASELSAN", "Gönderilen veri eşleşmiyor!"

# 2. Alım Testi
virt_hw.inject_rx_byte(0x5A) # Dışarıdan 0x5A geldi
success, rx_byte = driver.receive_byte()
print(f"  [+] Alınan Bayt       : 0x{rx_byte:02X} (Başarılı: {success})")
assert success is True and rx_byte == 0x5A, "Alınan bayt hatalı!"
print("\n[HÜCRE 12] C++20 bare-metal polling UART sürücüsü başarıyla doğrulandı.")
```

## 8. Savunma Sanayii Aviyonik Senaryosu: Görev Bilgisayarı - GPS/INS

Taktik İHA ve güdümlü mühimmat aviyonik mimarisinde Görev Bilgisayarı (Mission Computer), hassas seyrüsefer için harici bir GPS/INS (Küresel Konumlama ve Ataletsel Seyrüsefer Sistemi) alıcısına bağlıdır.

### Aviyonik UART Entegrasyon Parametreleri:
- **Fiziksel Standart:** Diferansiyel RS-422 (Uçuş gövdesindeki motor ateşleyicileri ve radar altimetresi parazitlerinden korunmak için).
- **Protokol:** $115200\ \text{bps}$, 8 Veri Biti, Eşlik Yok (No Parity), 1 Stop Biti ($8\text{N}1$).
- **Paket Biçimi:** NMEA-0183 (`$GNGGA` / `$GNRMC`) veya İkili UBX/NovAtel telemetri çerçevesi.
- **Güvenilirlik Gereksinimi:** Checksum doğrulaması, Frame Error (FE) izolasyonu ve hat gürültüsü filtrelemesi.

### Karşılaşılan Aviyonik Hata Senaryoları:
1. **Baud Hızı Sapması (Baud Drift):** İHA yüksek irtifada $-40^\circ\text{C}$ sıcaklığa maruz kaldığında kristal osilatörün frekansı kayar. %2'yi aşan sapmalarda STOP biti kayar ve `FE = 1` oluşur.
2. **Kablo Titreşimi ve Temassızlık:** Şok ve titreşim anında hatta mikro-kesintiler oluşur; alıcı bunu sahte bir START biti olarak algılayabilir.

```python
# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 5 — Aviyonik GPS Telemetri Çözücü ve Hata Enjeksiyon Testi
NMEA Checksum Doğrulaması, Framing Error (FE) ve Baud Drift İzolasyonu
"""

from typing import Optional, Dict

class AvionicsGPSTelemetryParser:
    """NMEA-0183 Aviyonik Telemetri Çözücü ve Hata İzleme Modülü"""
    def __init__(self):
        self.valid_packets = 0
        self.checksum_errors = 0
        self.framing_errors = 0

    @staticmethod
    def calculate_nmea_checksum(sentence_content: str) -> str:
        """NMEA-0183 standardı: '$' ile '*' arasındaki tüm karakterlerin XOR toplamı"""
        csum = 0
        for char in sentence_content:
            csum ^= ord(char)
        return f"{csum:02X}"

    def parse_sentence(self, raw_sentence: str, has_framing_error: bool = False) -> Dict[str, any]:
        if has_framing_error:
            self.framing_errors += 1
            return {"valid": False, "error": "FRAMING_ERROR", "data": None}

        # Format kontrolü: $ ile başlamalı, * içermeli
        if not raw_sentence.startswith("$") or "*" not in raw_sentence:
            self.checksum_errors += 1
            return {"valid": False, "error": "MALFORMED_FORMAT", "data": None}

        parts = raw_sentence[1:].split("*")
        content = parts[0]
        received_csum = parts[1].strip()

        expected_csum = self.calculate_nmea_checksum(content)
        if received_csum.upper() != expected_csum.upper():
            self.checksum_errors += 1
            return {"valid": False, "error": "CHECKSUM_MISMATCH", "expected": expected_csum, "received": received_csum}

        # Başarılı paket ayrıştırma
        self.valid_packets += 1
        fields = content.split(",")
        packet_type = fields[0]

        parsed_data = {"type": packet_type}
        if packet_type in ["GNGGA", "GPGGA"] and len(fields) >= 10:
            parsed_data["utc_time"] = fields[1]
            parsed_data["latitude"] = f"{fields[2]} {fields[3]}"
            parsed_data["longitude"] = f"{fields[4]} {fields[5]}"
            parsed_data["fix_quality"] = int(fields[6]) if fields[6].isdigit() else 0
            parsed_data["altitude_m"] = float(fields[9]) if fields[9] else 0.0

        return {"valid": True, "error": None, "data": parsed_data}

# Test ve Simülasyon
parser = AvionicsGPSTelemetryParser()

# 1. Geçerli Aviyonik GPS Paketi ($GNGGA)
# Koordinatlar: 39°55'48" N (ASELSAN Macunköy), 32°45'12" E, Rakım: 875.4m
valid_content = "GNGGA,123519.00,3955.80,N,03245.20,E,1,08,0.9,875.4,M,36.0,M,,"
valid_csum = AvionicsGPSTelemetryParser.calculate_nmea_checksum(valid_content)
valid_sentence = f"${valid_content}*{valid_csum}"

res_valid = parser.parse_sentence(valid_sentence)
print("[*] Aviyonik GPS/INS Telemetri Doğrulama Testi:")
print(f"  [+] Geçerli NMEA Paketi  : {valid_sentence}")
print(f"  [+] Ayrıştırılan Veri    : {res_valid['data']}")

# 2. Checksum Hata Enjeksiyonu (Hatta 1 bit ters döndü)
corrupted_sentence = valid_sentence.replace("875.4", "975.4") # Rakım bozuldu ama checksum eski kaldı
res_corrupt = parser.parse_sentence(corrupted_sentence)
print(f"  [!] Bozuk Paket Durumu   : {res_corrupt['error']} (Beklenen: {res_corrupt.get('expected')}, Gelen: {res_corrupt.get('received')})")

# 3. Framing Error Enjeksiyonu (Baud rate drift sebebiyle STOP biti kaçırıldı)
res_fe = parser.parse_sentence(valid_sentence, has_framing_error=True)
print(f"  [!] Framing Error Durumu : {res_fe['error']}")

assert res_valid["valid"] is True, "Geçerli paket reddedildi!"
assert res_valid["data"]["altitude_m"] == 875.4, "Rakım hatalı çözüldü!"
assert res_corrupt["valid"] is False and res_corrupt["error"] == "CHECKSUM_MISMATCH", "Bozuk checksum yakalanmalıydı!"
assert res_fe["valid"] is False and res_fe["error"] == "FRAMING_ERROR", "Framing error yakalanmalıydı!"
print("\n[HÜCRE 14] Aviyonik telemetri hata enjeksiyonu ve çözümleme motoru başarıyla doğrulandı.")
```

## 9. Üretim Seviyesi C++20 Bare-Metal Driver / RAII Wrapper

Modern savunma yazılımlarında C++20 standartları, donanım register erişimlerini tip güvenli (type-safe), sıfır maliyetli soyutlama (zero-cost abstraction) ve RAII prensipleriyle sarmalar.

```cpp
// ============================================================================
// C++20 STM32 Bare-Metal USART RAII Sürücüsü
// ============================================================================
#include <cstdint>
#include <concepts>
#include <span>

namespace defense::hal {

struct USART_TypeDef {
    volatile uint32_t SR;    // Durum Yazmacı (Offset 0x00)
    volatile uint32_t DR;    // Veri Yazmacı  (Offset 0x04)
    volatile uint32_t BRR;   // Baud Rate    (Offset 0x08)
    volatile uint32_t CR1;   // Kontrol 1    (Offset 0x0C)
    volatile uint32_t CR2;   // Kontrol 2    (Offset 0x10)
    volatile uint32_t CR3;   // Kontrol 3    (Offset 0x14)
};

template <uintptr_t BaseAddress>
class UartDevice {
public:
    static constexpr USART_TypeDef* Regs = reinterpret_cast<USART_TypeDef*>(BaseAddress);

    static void init(uint32_t pclk_hz, uint32_t baud_rate) noexcept {
        // 1. Baud Rate Hesapla (OVER8 = 0 -> 16x oversampling)
        uint32_t usart_div = (pclk_hz + (baud_rate / 2)) / baud_rate; // Yuvarlama optimizasyonu
        Regs->BRR = usart_div;

        // 2. CR1: Transmitter Enable (TE), Receiver Enable (RE), USART Enable (UE)
        Regs->CR1 = (1 << 3) | (1 << 2) | (1 << 13);
    }

    [[nodiscard]] static bool write_byte(uint8_t byte, uint32_t timeout_cycles = 100'000) noexcept {
        while (!(Regs->SR & (1 << 7))) { // TXE bekle
            if (--timeout_cycles == 0) return false;
        }
        Regs->DR = byte;
        return true;
    }

    static void flush() noexcept {
        while (!(Regs->SR & (1 << 6))); // TC (Transmission Complete) bekle
    }

    [[nodiscard]] static bool write(std::span<const uint8_t> buffer) noexcept {
        for (uint8_t b : buffer) {
            if (!write_byte(b)) return false;
        }
        flush();
        return true;
    }
};

// USART1 Base: 0x40011000 (STM32F4 APB2)
using TelemetryUart = UartDevice<0x40011000UL>;

} // namespace defense::hal
```

## 10. Bilerek Bozduğumuz Şey (Sabotaj ve Arıza Analizi)

### Sabotaj 1: TXE Bayrağını Beklemeden Peş Peşe TDR'a Yazmak
Geliştiricinin yaptığı tipik hata:
```c
// YANLIŞ KOD (SABOTAJ):
USART1->DR = 'A';
USART1->DR = 'B'; // TXE kontrolü YOK!
```
- **Ne Olur?:** İlk yazılan `'A'` baytı henüz TDR'dan Shift Register'a aktarılmadan üzerine `'B'` yazılır.
- **Sonuç:** `'A'` baytı donanımsal olarak ezilir ve hattan **ASLA ÇIKMAZ**. Alıcı sadece `'B'` okur. Telemetri paketinin ilk baytı kaybolduğu için tüm çerçeve bozulur.

### Sabotaj 2: RS-485 İletişiminde TC Yerine TXE Bekleyip Yön Pinini Çekmek
```c
// YANLIŞ KOD (SABOTAJ):
for(int i=0; i<len; i++) {
    while(!(USART1->SR & USART_SR_TXE));
    USART1->DR = buffer[i];
}
while(!(USART1->SR & USART_SR_TXE)); // HATA! Son bayt TDR'dan yeni çıktı ama henüz kabloda!
RS485_DIR_GPIO->BSRR = RS485_DIR_PIN_RESET; // Yön pinini dinlemeye çevir!
```
- **Ne Olur?:** `TXE = 1` olduğunda son bayt henüz Shift Register'da iletilmektedir (STOP biti çıkmamıştır). Transceiver dinleme moduna geçtiği anda son baytın son 3-4 biti hattan kesilir!
- **Düzeltme:** Döngü bitiminde `while(!(USART1->SR & USART_SR_TC));` beklenmelidir!

## 11. Karşılaştırma Matrisi: Polling vs Interrupt vs DMA Tabanlı UART

| Karşılaştırma Kriteri | Polling (Yoklama / Bloklayıcı) | Interrupt (Kesme Tabanlı) | DMA (Direct Memory Access) |
| :--- | :--- | :--- | :--- |
| **CPU Yükü (Overhead)** | **Çok Yüksek (%100 meşgul)** | **Orta (Bayt başına 1 ISR)** | **Sıfıra Yakın (Blok bitince 1 ISR)** |
| **Maksimum Baud Hızı** | Düşük ($< 115200\ \text{bps}$) | Orta ($< 460800\ \text{bps}$) | **Çok Yüksek ($> 5\ \text{Mbps}$)** |
| **Gecikme (Latency)** | Anında (Deterministik) | Düşük (Kesme gecikmesi kadar) | Sıfır aktarım gecikmesi |
| **Kod Karmaşıklığı** | Minimal (10-20 satır) | Orta (Halka Tampon / Ring Buffer) | Yüksek (DMA kanalları, bellek hizalama) |
| **Overrun Riski** | Çok yüksek (Başka işlem varsa) | Düşük (ISR hızlıysa) | **Donanımsal olarak neredeyse imkansız** |
| **Kullanım Alanı** | Bootloader, Erken Debug Printf | Düşük hızlı sensörler, CLI/Shell | **Radar, Yüksek Hızlı Aviyonik Telemetri** |

## 12. Donanım ve Yazmaç Haritası (STM32 USART1 / USART2 / USART3 / UART4)

STM32F4 serisinde USART modüllerinin bellek adresleri ve veri yolu dağılımı:

```
  +-------------------------------------------------------------------------------+
  |                 STM32 ÇEVRESEL VERİ YOLU (BUS) VE USART DAĞILIMI              |
  +-------------------------------------------------------------------------------+
  
  [ APB2 Yüksek Hızlı Bus (84 MHz) ]
    |---> USART1 : 0x40011000 - 0x400113FF (TX: PA9/PB6, RX: PA10/PB7)
    |---> USART6 : 0x40011400 - 0x400117FF (TX: PC6/PG14, RX: PC7/PG9)
  
  [ APB1 Standart Hızlı Bus (42 MHz) ]
    |---> USART2 : 0x40004400 - 0x400047FF (TX: PA2/PD5, RX: PA3/PD6)
    |---> USART3 : 0x40004800 - 0x40004BFF (TX: PB10/PD8, RX: PB11/PD9)
    |---> UART4  : 0x40004C00 - 0x40004FFF (TX: PA0/PC10, RX: PA1/PC11)
    |---> UART5  : 0x40005000 - 0x400053FF (TX: PC12, RX: PD2)
```

> **Önemli Not:** USART1 ve USART6 APB2 veri yolundadır ($84\ \text{MHz}$ clock); USART2, 3, 4, 5 ise APB1 veri yolundadır ($42\ \text{MHz}$ clock). Baud rate hesaplarken doğru bus frekansının seçilmesi zorunludur!

## 13. Mülakat ve Saha Tuzakları (Top 5 Gotchas)

1. **"TXE yandı, verim karşıya ulaştı" Yanılgısı:**
   - Hayır! `TXE` sadece verinin TDR'dan Shift Register'a geçtiğini gösterir. Veri hala telde seyahat etmektedir. İletişimi kapatmak veya gücü kesmek için `TC` bayrağı beklenmelidir.
2. **Ortak Toprağı (GND) Bağlamayı Unutmak:**
   - Sahada iki kart haberleşirken GND hattı bağlanmazsa lojik eşik seviyeleri kayar. Sistem masada çalışır, sahada motorlar devreye girdiğinde tüm veriler çöpe döner.
3. **GPIO Alternatif Fonksiyon (AF) ve Clock Gating:**
   - RCC üzerinden USART saati açılsa bile (`RCC->APB2ENR |= RCC_APB2ENR_USART1EN`), ilgili GPIO pinlerinin modu `AF` (Alternate Function) yapılmazsa ve `GPIO_AFR` yazmacına USART atanmazsa pin sessiz kalır.
4. **Baud Rate Saat Sapmasını Ölçmemek:**
   - Hatalı kristal veya yanlış PLL ayarı sonucu baud sapması %3'ün üzerine çıkarsa iletim görünüşte çalışır fakat her 100 pakette 1-2 tanesi Framing Error ile düşer.
5. **Overrun Hatasını Temizlememek:**
   - Bir kez `ORE` oluştuğunda bazı STM32 serilerinde `RXNE` bayrağı kilitlenir. `ORE` bayrağını temizlemek için `USART_SR` okunup ardından `USART_DR` okunmalıdır!

## 14. 5N1K Özeti

- **Ne?:** UART (Universal Asynchronous Receiver-Transmitter), iki cihaz arasında harici bir saat hattı olmaksızın, önceden belirlenmiş baud hızıyla çift yönlü (Full-Duplex) seri veri aktarımı sağlayan donanım çevre birimidir.
- **Neden?:** Minimum pin sayısı (TX, RX, GND) ile yüksek güvenilirlikte, basit ve endüstri standardı haberleşme kurmak için.
- **Nasıl?:** Boşta lojik 1 olan hattı START biti ile 0'a çekip alıcının saatini senkronize ederek, $16\times$ aşırı örnekleme ve majority voting ile bitleri okuyarak çalışır.
- **Nerede?:** Aviyonik görev bilgisayarları, GPS/INS sensörleri, motor sürücüleri, telsiz modemleri ve hata ayıklama (debug console) terminallerinde.
- **Ne Zaman?:** SPI veya I2C gibi kısa mesafe kart içi veri yollarının yetersiz kaldığı, kablolu ve bağımsız sistem entegrasyonlarında.
- **Kim?:** Gömülü yazılım mühendisleri, aviyonik sistem mimarları ve savunma sanayii donanım entegrasyon uzmanları.

## 15. Gün Sonu Özeti ve Yetkinlik Kontrolü

### 3 Cümlelik Özet:
1. **UART Nedir?:** UART, harici saat sinyali taşımayan, mutabık kalınan baud hızı ve start/stop çerçeveleme mekanizmasıyla çalışan asenkron seri haberleşme donanımıdır.
2. **Hangi Problemi Çözer?:** Minimum kablo ile farklı saat frekanslarında koşan bağımsız işlemcilerin güvenilir veri alışverişi yapmasını sağlar.
3. **Getirdiği Risk / Trade-off:** Hatalı baud yapılandırmasında framing error, yavaş alıcılarda overrun error (ORE) ve polling kullanımında yüksek CPU bloklanması riskini getirir.

### Yetkinlik Kontrol Listesi:
- [x] UART'ın asenkron çalışma prensibini ve $T_{\text{bit}}$ süre hesabını açıklayabiliyorum.
- [x] STM32 BRR yazmacındaki Mantissa ve Fraction hesaplarını yapabiliyorum.
- [x] $16\times$ Oversampling ve dilim 8, 9, 10 Majority Voting gürültü eleme mantığını anladım.
- [x] TXE (TDR boş) ile TC (İletim bitti) bayrakları arasındaki hayati farkı biliyorum.
- [x] Donanım akış kontrolünün (RTS/CTS) Overrun Error'ü nasıl engellediğini simüle edebiliyorum.
- [x] NMEA aviyonik telemetri çerçevelerinin checksum ve framing doğrulamalarını uygulayabiliyorum.

## 16. İleri Okuma ve Kaynaklar

1. **STMicroelectronics Reference Manual (RM0090 / RM0433):** *USART Functional Description, Baud Rate Generation and Hardware Flow Control Sections.*
2. **ARM Cortex-M Programming & Peripheral Architecture:** *Joseph Yiu - The Definitive Guide to ARM Cortex-M3 and Cortex-M4 Processors.*
3. **NMEA 0183 Standard for Interfacing Marine Electronic Devices:** *National Marine Electronics Association.*
4. **Texas Instruments Application Report (AN-908):** *RS-422 and RS-485 Circuit Implementation Guide for High Reliability Systems.*
5. **C++20 Embedded Systems Architecture:** *Bjarne Stroustrup - A Tour of C++ (Concurrency and Hardware Abstraction).*

## 17. 24-Hücreli Master Mimari Onay Beyanı

Bu eğitim modülü, ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ standartlarında C++20 ve STM32 Gömülü Sistemler Müfredatı kapsamında hazırlanmıştır.

```
+-----------------------------------------------------------------------------------+
|               GÜN 168 MASTER MİMARİ MÜHENDİSLİK DOĞRULAMA RAPORU                  |
+-----------------------------------------------------------------------------------+
| 1. Toplam Hücre Sayısı        : 24 Hücre (18 Markdown, 6 Python Kodu)             |
| 2. Fiziksel Katman Modelleri  : TTL, RS-232, RS-422, RS-485, GND Zemin Analizi   |
| 3. STM32 Donanım Mimarisi     : BRR Mantissa/Fraction, 16x Oversampling, TDR/RDR  |
| 4. Akış Kontrolü              : RTS/CTS vs ORE Simülasyonu                        |
| 5. Aviyonik Senaryosu         : GPS NMEA Telemetri Çözücü ve Hata Enjeksiyonu     |
| 6. Görsel Artefact            : 300 DPI 4-Panelli Koyu Tema Dashboard (.PNG)      |
| 7. Özel Lisans                : Telif Hakkı (c) 2026 Seydi Eryılmaz               |
+-----------------------------------------------------------------------------------+
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. UART Sinyal Zamanlaması ve 16x Oversampling Majority Voting (Start, Data, Stop)
2. STM32 Baud Rate Hata Oranı Eğrisi (Farklı PCLK ve Baud Değerlerinde % Sapma)
3. Donanım Akış Kontrolü (RTS/CTS) ve Alıcı Tamponu Seviyesi (ORE Önleme)
4. UART İletim Süresi ve CPU Bloklanma Karşılaştırması (Baud Hızlarına Göre Gecikme)
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# Matplotlib dark mode ve font ayarları
plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

C_BG = '#1E293B'
C_CYAN = '#38BDF8'
C_GREEN = '#34D399'
C_RED = '#F87171'
C_YELLOW = '#FBBF24'
C_PURPLE = '#A855F7'
C_WHITE = '#F8FAFC'

# ------------------------------------------------------------------------------
# PANEL 1: UART Sinyal Zamanlaması ve 16x Oversampling (Dilim 8, 9, 10)
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

# 'A' Harfi (0x41 = 0b01000001) -> Frame: START(0), 1, 0, 0, 0, 0, 0, 1, 0, STOP(1)
bits = [0, 1, 0, 0, 0, 0, 0, 1, 0, 1]
bit_labels = ['START\n(0)', 'D0\n(1)', 'D1\n(0)', 'D2\n(0)', 'D3\n(0)', 'D4\n(0)', 'D5\n(0)', 'D6\n(1)', 'D7\n(0)', 'STOP\n(1)']

t_step = []
signal_val = []
for i, b in enumerate(bits):
    t_step.extend([i, i + 0.999])
    signal_val.extend([b, b])

ax1.plot(t_step, signal_val, color=C_CYAN, linewidth=2.5, label='UART TX/RX Sinyali (TTL 3.3V)')

# 16x oversampling noktalarını göster (Özellikle D0 bitinde dilim 8, 9, 10)
d0_center = 1.5 # 1. bitin ortası
ax1.axvspan(1.45, 1.65, color=C_YELLOW, alpha=0.3, label='Majority Voting Penceresi (Örnek 8, 9, 10)')
ax1.scatter([1.48, 1.53, 1.58], [1, 1, 1], color=C_GREEN, s=60, zorder=5, label='Temiz Örnekleme (NF=0)')

# D1 bitinde temsili glitch ve gürültü bayrağı
ax1.scatter([2.48, 2.53, 2.58], [0, 1, 0], color=C_RED, s=60, zorder=5, label='Gürültülü Örnekleme (NF=1)')

ax1.set_xticks(range(10))
ax1.set_xticklabels(bit_labels, fontsize=9, color=C_WHITE)
ax1.set_yticks([0, 1])
ax1.set_yticklabels(['0V (LOW)', '3.3V (HIGH)'], fontsize=10, color=C_WHITE)
ax1.set_title("Panel 1: UART Çerçevesi ve 16x Oversampling (Majority Voting)", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.set_xlabel("Bit Çerçeve İndeksi", color=C_WHITE, fontsize=10)
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax1.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 2: STM32 Baud Rate Hata Oranı Eğrisi (% Sapma)
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

bauds = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
pclk_42 = 42_000_000 # 42 MHz APB1
pclk_84 = 84_000_000 # 84 MHz APB2

def calc_errors(pclk, baud_list):
    errs = []
    for b in baud_list:
        div = pclk / (16.0 * b)
        mant = int(div)
        frac = round((div - mant) * 16)
        if frac >= 16:
            mant += 1
            frac = 0
        act_div = mant + frac / 16.0
        act_b = pclk / (16.0 * act_div)
        err = ((act_b - b) / b) * 100.0
        errs.append(err)
    return errs

errs_42 = calc_errors(pclk_42, bauds)
errs_84 = calc_errors(pclk_84, bauds)

x_pos = np.arange(len(bauds))
width = 0.35

ax2.bar(x_pos - width/2, errs_42, width, label='APB1 (42 MHz PCLK)', color=C_PURPLE, alpha=0.85)
ax2.bar(x_pos + width/2, errs_84, width, label='APB2 (84 MHz PCLK)', color=C_GREEN, alpha=0.85)

# Aviyonik ±2.5% tolerans çizgisi
ax2.axhline(2.5, color=C_RED, linestyle='--', linewidth=1.5, label='Aviyonik Limit (+2.5%)')
ax2.axhline(-2.5, color=C_RED, linestyle='--', linewidth=1.5, label='Aviyonik Limit (-2.5%)')

ax2.set_xticks(x_pos)
ax2.set_xticklabels([str(b) for b in bauds], fontsize=9, color=C_WHITE, rotation=30)
ax2.set_ylabel("Baud Hatası (%)", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: STM32 Baud Rate Hata Oranı (% Sapma Analizi)", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='lower left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: Donanım Akış Kontrolü (RTS/CTS) ve Alıcı Tamponu Seviyesi
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

time_ticks = np.arange(0, 20, 1)
# Tampon doluluk simülasyonu
fifo_no_flow = [0, 1, 2, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]
ore_events =   [0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 8, 8, 8, 8, 8, 8, 8]
fifo_with_flow = [0, 1, 2, 3, 4, 3, 4, 3, 4, 3, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0]
rts_pin_level =  [0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]

ax3.plot(time_ticks, fifo_no_flow, color=C_RED, linestyle=':', linewidth=2, label='Akış Kontrolsüz FIFO (Kilitlenme)')
ax3.plot(time_ticks, ore_events, color='#EF4444', linewidth=2.5, label='Biriken ORE Hataları (Veri Kaybı)')
ax3.plot(time_ticks, fifo_with_flow, color=C_CYAN, linewidth=2.5, label='RTS/CTS ile Güvenli FIFO (Maks: 4)')
ax3.step(time_ticks, np.array(rts_pin_level) * 3.8, color=C_YELLOW, where='post', linewidth=1.8, label='RTS Pini Durumu (HIGH = Dur)')

ax3.axhline(4, color=C_WHITE, linestyle='--', alpha=0.5, label='FIFO Kapasitesi (4 Bayt)')
ax3.set_xlabel("Zaman Çevrimleri (Ticks)", color=C_WHITE, fontsize=10)
ax3.set_ylabel("Tampon / Hata Sayısı", color=C_WHITE, fontsize=10)
ax3.set_title("Panel 3: Donanım Akış Kontrolü (RTS/CTS) ile ORE İzolasyonu", color=C_WHITE, fontsize=12, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax3.legend(loc='upper left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 4: UART İletim Süresi ve CPU Bloklanma Karşılaştırması
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

# 1 Bayt = 10 Bit (1 Start + 8 Data + 1 Stop)
byte_times_us = [(10.0 / b) * 1e6 for b in bauds]
cpu_cycles_168mhz = [t * 168.0 for t in byte_times_us] # 168 MHz MCU'da boşa harcanan komut çevrimi

ax4.plot(bauds, byte_times_us, marker='o', color=C_CYAN, linewidth=2.5, label='1 Bayt İletim Süresi (µs)')
ax4.set_xscale('log')
ax4.set_yscale('log')
ax4.set_xlabel("Baud Hızı (Log Ölçek, bps)", color=C_WHITE, fontsize=10)
ax4.set_ylabel("İletim Süresi (µs)", color=C_CYAN, fontsize=10)
ax4.tick_params(axis='y', labelcolor=C_CYAN)

ax4_twin = ax4.twinx()
ax4_twin.plot(bauds, cpu_cycles_168mhz, marker='s', color=C_YELLOW, linewidth=2, linestyle='--', label='Polling CPU İsrafı (Çevrim)')
ax4_twin.set_yscale('log')
ax4_twin.set_ylabel("168 MHz CPU Çevrim İsrafı", color=C_YELLOW, fontsize=10)
ax4_twin.tick_params(axis='y', labelcolor=C_YELLOW)

ax4.set_title("Panel 4: Baud Hızına Göre İletim Gecikmesi ve CPU Yükü", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')

plt.suptitle("GÜN 168: STM32 UART/USART Temelleri ve Aviyonik Entegrasyon Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_168_uart_temelleri.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_168\gun_168_uart_temelleri.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 168 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. Baud Rate Hesaplama Motoru Assertions
calc_test = STM32BaudRateCalculator(42_000_000)
brr_115200 = calc_test.calculate_brr(115200, over8=0)
assert brr_115200["mantissa"] == 22, "Mantissa değeri hatalı!"
assert brr_115200["fraction"] == 13, "Fraction değeri hatalı!"
assert brr_115200["brr_hex"] == "0x016D", "BRR Hex değeri hatalı!"
assert abs(brr_115200["error_pct"]) < 0.2, "Baud hatası %0.2'den küçük olmalı!"

# 3. 16x Oversampling Decoder Assertions
rx_test = UARTOversamplingReceiver()
# ASCII 'B' = 66 = 0x42 = 0b01000010 -> LSB first: D0=0, D1=1, D2=0, D3=0, D4=0, D5=0, D6=1, D7=0
raw_b_bits = [0, 0, 1, 0, 0, 0, 0, 1, 0, 1] # Start + Data + Stop
stream_samples = []
for b in raw_b_bits:
    stream_samples.extend([b] * 16)
dec_res = rx_test.decode_stream(stream_samples)
assert dec_res["status"] == "SUCCESS", "Frame çözülemedi!"
assert dec_res["data_byte_hex"] == "0x42", f"Beklenen 0x42 ('B'), okunan: {dec_res['data_byte_hex']}"

# 4. Donanım Akış Kontrolü Assertions
sink_test = UARTSinkDevice(fifo_capacity=2, use_hardware_flow_control=True)
sink_test.receive_byte(1)
assert sink_test.rts_pin == 0, "Tampon 1 baytta henüz dolmadı, RTS 0 olmalı!"
sink_test.receive_byte(2)
assert sink_test.rts_pin == 1, "Tampon 2 baytla doldu, RTS 1 olmalı!"
assert sink_test.can_accept_byte() is False, "Tampon doluyken yeni bayt kabul edilmemeli!"
sink_test.process_one_byte_from_fifo()
assert sink_test.rts_pin == 0, "Tampon boşaltılınca RTS 0 olmalı!"

# 5. Aviyonik NMEA Telemetri Çözücü Assertions
gps_parser = AvionicsGPSTelemetryParser()
csum = gps_parser.calculate_nmea_checksum("GPGGA,120000.00,3900.00,N,03200.00,E,1,08,1.0,1000.0,M,0.0,M,,")
nmea_str = f"$GPGGA,120000.00,3900.00,N,03200.00,E,1,08,1.0,1000.0,M,0.0,M,,*{csum}"
parsed = gps_parser.parse_sentence(nmea_str)
assert parsed["valid"] is True, "Geçerli NMEA cümlesi çözülemedi!"
assert parsed["data"]["altitude_m"] == 1000.0, "Rakım hatalı!"

print("\n[PASS] Gün 168: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
```
