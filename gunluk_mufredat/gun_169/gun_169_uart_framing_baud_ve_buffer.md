# GÜN 169: UART Framing, Baud Toleransı ve Dairesel Tampon (Ring Buffer) Mimarisi

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz.
```

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
![C++20](https://img.shields.io/badge/Standard-C%2B%2B20-blue.svg?style=flat-square)
![STM32](https://img.shields.io/badge/Hardware-STM32%20USART%20Interrupt-orange.svg?style=flat-square)
![Data Structure](https://img.shields.io/badge/Memory-Lock--Free%20SPSC%20Ring%20Buffer-purple.svg?style=flat-square)
![Defense Grade](https://img.shields.io/badge/Domain-Avionics%20%2F%20Radar%20Altimeter-red.svg?style=flat-square)

---

## 1. Zihinsel Model ve Mimari Büyük Resim (Çerçeveleme ve Tamponlama)

Bir önceki gün UART'ın fiziksel sinyalleşmesini ve donanımsal baud üretimini inceledik. Ancak gerçek dünya savunma sistemlerinde (İHA otopilotu, güdüm bilgisayarı, radar altimetresi) veriler tek tek ve keyfi anlarda gelmez; kesintisiz bayt akışları (Byte Streams) halinde yüksek hızda mikrodenetleyiciye akar.

Bu noktada iki kritik mimari soru ortaya çıkar:
1. **Veri Paketini Nasıl Çerçeveleyeceğiz (Framing)?:** 8 bit veri yetecek mi, yoksa 9 bit mi gerekecek? Parity (Eşlik) biti donanımsal olarak nasıl konumlandırılır? Alıcı cihaz yavaşsa veya hat gürültülüyse 2 STOP biti ne işe yarar?
2. **Gelen Veri Nerede Depolanacak (Buffering)?:** Bir bayt $115200\ \text{baud}$ hızında $\approx 86.8\ \mu\text{s}$, $921600\ \text{baud}$ hızında ise sadece $\approx 10.85\ \mu\text{s}$ sürede gelir. Eğer işlemci her baytı beklemek için `while` döngüsünde (polling) durursa, uçuş denetim döngüsü çöker. Eğer kesme ile alır ama güvenli bir tampona koyamazsa, veri ezilir (`ORE`).

### Zihinsel Model Çözümü:
- **Çerçeveleme (Framing):** START, Veri, Parity ve STOP bitlerinin standartlaşmış dizilimi.
- **Kesme Tabanlı RX (Interrupt RXNE):** Donanım her bayt tamamlandığında CPU'yu uyarır (Top-Half).
- **Lock-Free SPSC Ring Buffer (Dairesel Tampon):** Kesme (Üretici - Producer) ile Ana Görev (Tüketici - Consumer) arasında mutex kilidi kullanmadan, sıfır gecikmeli ve thread-safe veri aktarımı sağlayan bellek yapısı.

```
  [ UART RX PİNİ ] 
         | (10.85 µs / bayt @ 921600 baud)
         v
  [ RX Shift Register ] ---> [ USART_RDR ]
                                   | 
                 [ RXNE Donanım Kesmesi Tetiklenir! ]
                                   |
                                   v
                      +--------------------------+
                      | USART_IRQHandler (ISR)   |  <--- ÜRETİCİ (Producer)
                      | RingBuffer.push(byte)    |       (Kilit yok! ~15 çevrim)
                      +--------------------------+
                                   |
                                   v
             [ LOCK-FREE SPSC RING BUFFER (Power-of-Two) ]
             [ 0 | 1 | 2 | 3 | 4 | 5 | ... | 254 | 255 ]
               ^                           ^
             TAIL                        HEAD
                                   |
                                   v
                      +--------------------------+
                      | Nav_Task / Main Loop     |  <--- TÜKETİCİ (Consumer)
                      | RingBuffer.pop(&byte)    |       (Kendi hızında tüketir)
                      +--------------------------+
```

## 2. UART Çerçeveleme Anatomisi: 8N1, 8E1, 8O1, 9-bit Data ve 2 Stop Biti

UART haberleşmesinde çerçeveleme (Framing), bir baytın elektriksel hattan hangi kurallarla akacağını belirler. İsimlendirme standardı: `<Veri Biti><Eşlik Tipi><Durdurma Biti>` biçimindedir.

### 1. Standart 8N1 (8 Data, No Parity, 1 Stop):
En yaygın formattır. Toplam $1 + 8 + 0 + 1 = 10\ \text{bit}$ sürer.
- **Verimlilik:** $\%80$ (10 bitin 8 biti gerçek veri, 2 biti protokol yükü).

### 2. Eşlik Korumalı 8E1 ve 8O1 (Even / Odd Parity):
Tek bitlik donanımsal bozulmaları yakalamak için kullanılır.
- **8E1 (Even Parity):** Verideki '1' bitlerinin sayısı sayılır. Eğer 1'lerin sayısı tek ise Parity biti `1` yapılır; çift ise `0` yapılır (Toplam 1 sayısı her zaman ÇİFT olur).
- **8O1 (Odd Parity):** Toplam 1 sayısı her zaman TEK olacak şekilde Parity biti ayarlanır.
- **Toplam Süre:** $1 + 8 + 1 + 1 = 11\ \text{bit}$. Verimlilik: $\%72.7$.

### 3. Çift Durdurma Biti (2 Stop Bits - 8N2):
Savunma sanayiinde uzun kablolu hatlarda veya optik izolatörlü (Optocoupler) devrelerde tercih edilir.
- Optokuplörlerin transistör kapanma süresi (Turn-off delay) sinyalin düşen/yükselen kenarlarını yuvarlar.
- 2 Stop biti kullanıldığında hat en az $2 \times T_{\text{bit}}$ süre lojik 1 kalır. Bu, yavaş alıcının iç lojik durumunu sıfırlamasını ve alıcı ile verici arasındaki saat kaymalarının (clock skew) bir sonraki bayta taşmamasını garantiler.

### 4. 9-bit Veri Modu (Multiprocessor Communication):
STM32'de `USART_CR1_M` biti ile 9-bit mod seçilebilir.
- 9. bit genellikle **Adres / Veri ayrımı** için kullanılır.
- $9.\ \text{bit} = 1$ ise gelen bayt bir alt sistem cihaz adresidir (örneğin 0x12 = İHA Kanatçık Motoru).
- $9.\ \text{bit} = 0$ ise gelen bayt o adrese ait komut/veridir. Bus üzerindeki diğer dinleyiciler adres eşleşene kadar CPU kesmesi almaz (Mute Mode)!

## 3. Baud Toleransı ve Kümülatif Zamanlama Hatası (Cumulative Bit Drift)

Asenkron iletimde verici ve alıcının saat kaynakları bağımsız osilatörlerden beslenir. Sıcaklık, voltaj dalgalanması veya kesirli bölücü (BRR) yuvarlama hataları nedeniyle vericinin saat frekansı $f_{\text{TX}}$ ile alıcının saat frekansı $f_{\text{RX}}$ arasında kaçınılmaz bir frekans sapması ($\Delta f$) vardır.

### Kümülatif Zaman Kayması Matematiği:
Her bit periyodundaki mutlak hata:
$$\delta t = T_{\text{TX}} - T_{\text{RX}} = \frac{1}{\text{Baud}_{\text{TX}}} - \frac{1}{\text{Baud}_{\text{RX}}}$$

Alıcı, her çerçevenin başında gelen START bitinin düşen kenarında ($t = 0$) sayacını sıfırlar. Ancak her geçen bit ile birlikte zaman hatası kümülatif olarak birikir:
$$\Delta T_N = N \times \delta t \quad (N = 0, 1, 2, \dots, 9)$$

### Örnekleme Penceresi ve Çökme Noktası:
$16\times$ oversampling kullanan bir alıcıda, $N$. bitin tam ortası $t_{\text{mid}} = (N + 0.5) \times T_{\text{bit}}$ anıdır. Alıcının çoğunluk oylaması yaptığı aralık ise dilim 8, 9, 10'dur (yani $[0.4375, 0.625] \times T_{\text{bit}}$).
- Eğer kümülatif kayma $\Delta T_N$ yarım bit süresini ($\pm 0.5 \times T_{\text{bit}}$) aşarsa, alıcı $N$. biti değil, bir önceki veya bir sonraki biti örnekler!
- En kritik nokta en sondaki **STOP BİTİ ($N = 9$)** anıdır:
  $$9.5 \times \left| \frac{\Delta \text{Baud}}{\text{Baud}} \right| < 0.5 \implies \left| \frac{\Delta \text{Baud}}{\text{Baud}} \right| < \frac{0.5}{9.5} \approx 5.26\%$$
- **Pratik Aviyonik Eşiği:** Majority voting penceresinin ($8/16 = 0.5$) sınırda kalmaması ve gürültü marjı için askeri standartlarda kabul edilebilir maksimum sapma:
  $$\text{Maksimum İzin Verilen Baud Hatası} \le \pm 2.5\% \dots 3.75\%$$
Eğer sapma bu değeri aşarsa alıcı STOP biti yerinde lojik 0 görür ve **Framing Error (`FE`)** bayrağını kaldırır!

## 4. Kesme Tabanlı RX Mimarisi: Neden Polling Yetmez?

Polling (yoklama) yönteminde işlemci `while (!(USART1->SR & USART_SR_RXNE));` satırında bekler. Bu yöntem aviyonik sistemlerde kesinlikle yasaktır:
1. **CPU Felci:** Bir bayt beklerken geçen $86.8\ \mu\text{s}$ sürede uçuş kontrol algoritması çalışamaz.
2. **Paket Kaçırma:** CPU başka bir fonksiyon çalıştırırken RX hattına veri gelirse ve okunmadan ikinci bayt gelirse `USART_SR_ORE` (Overrun) bayrağı kalkar ve veri yok olur.

### Çözüm: Interrupt-Driven RXNE (Kesme Tabanlı Alım):
STM32'de `USART_CR1` yazmacındaki `RXNEIE` (RXNE Interrupt Enable) biti `1` yapılır.
- Donanım hatta 8 biti tamamlayıp `USART_RDR`'a aktardığı mikrosaniyede NVIC'e kesme darbesi yollar.
- CPU anında `USARTx_IRQHandler` fonksiyonuna dalar.
- **Top-Half İlkesi:** Kesme fonksiyonu içinde asla `printf`, `malloc`, karmaşık matematik veya gecikme (delay) yapılmaz! Yapılacak tek işlem:
  1. `RDR` yazmacından baytı oku (Bu işlem `RXNE` bayrağını otomatik temizler).
  2. Baytı **Dairesel Tampona (Ring Buffer)** yaz (`push`).
  3. Kesmeden derhal çık ($< 15$ CPU çevrimi).

```python
# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 1 — UART Çerçeveleme (Framing) Kodlayıcı ve Parity Hesaplayıcı
8N1, 8E1, 8O1, 8N2 Formatlarında Bit Dizilimi ve Eşlik Doğrulama
"""

from typing import List, Dict, Tuple

class UARTFrameEncoder:
    """UART Çerçeve Oluşturucu ve Parity Motoru"""
    
    @staticmethod
    def calculate_parity(data_byte: int, parity_type: str) -> int:
        """Even veya Odd parity bitini hesaplar"""
        # 1'lerin sayısını hesapla (popcount)
        ones_count = bin(data_byte).count('1')
        if parity_type.upper() == 'E': # Even (Çift)
            return 1 if (ones_count % 2 != 0) else 0
        elif parity_type.upper() == 'O': # Odd (Tek)
            return 0 if (ones_count % 2 != 0) else 1
        return 0 # No parity

    @classmethod
    def encode_byte(cls, data_byte: int, data_bits: int = 8, parity: str = 'N', stop_bits: int = 1) -> List[int]:
        """
        Bir baytı UART bit akışına dönüştürür.
        Format: START(0) + DATA (LSB First) + [PARITY] + STOP(1...1)
        """
        frame = [0] # 1. Start Biti (Daima 0)

        # 2. Veri Bitleri (LSB first)
        for i in range(data_bits):
            frame.append((data_byte >> i) & 1)

        # 3. Eşlik Biti (Varsa)
        if parity.upper() in ['E', 'O']:
            p_bit = cls.calculate_parity(data_byte, parity)
            frame.append(p_bit)

        # 4. Durdurma Bitleri (1 veya 2 adet lojik 1)
        for _ in range(stop_bits):
            frame.append(1)

        return frame

    @classmethod
    def decode_frame(cls, frame: List[int], data_bits: int = 8, parity: str = 'N', stop_bits: int = 1) -> Dict[str, any]:
        """Gelen bit çerçevesini çözer, Parity ve Framing Error denetimi yapar"""
        expected_len = 1 + data_bits + (1 if parity.upper() in ['E', 'O'] else 0) + stop_bits
        if len(frame) != expected_len:
            return {"valid": False, "error": "FRAME_LENGTH_MISMATCH", "data": None}

        # 1. Start Bit Kontrolü
        if frame[0] != 0:
            return {"valid": False, "error": "START_BIT_ERROR", "data": None}

        # 2. Veri Bitlerini Topla (LSB first)
        data_byte = 0
        for i in range(data_bits):
            data_byte |= (frame[1 + i] << i)

        # 3. Parity Kontrolü
        cursor = 1 + data_bits
        if parity.upper() in ['E', 'O']:
            rx_parity = frame[cursor]
            calc_p = cls.calculate_parity(data_byte, parity)
            if rx_parity != calc_p:
                return {"valid": False, "error": "PARITY_ERROR", "data": data_byte}
            cursor += 1

        # 4. Stop Bit Kontrolü (Framing Error Check)
        for s in range(stop_bits):
            if frame[cursor + s] != 1:
                return {"valid": False, "error": "FRAMING_ERROR", "data": data_byte}

        return {"valid": True, "error": None, "data": data_byte, "char": chr(data_byte) if 32 <= data_byte <= 126 else None}

# Test ve Doğrulama: 'M' Harfi (ASCII 77 = 0x4D = 0b01001101)
# 1'lerin sayısı = 4 (Çift)
test_val = 0x4D # 'M'

# 8N1 Çerçevesi
frame_8n1 = UARTFrameEncoder.encode_byte(test_val, 8, 'N', 1)
# 8E1 Çerçevesi: 4 adet 1 var -> Even parity için P=0 olmalı
frame_8e1 = UARTFrameEncoder.encode_byte(test_val, 8, 'E', 1)
# 8O1 Çerçevesi: 4 adet 1 var -> Odd parity için P=1 olmalı
frame_8o1 = UARTFrameEncoder.encode_byte(test_val, 8, 'O', 1)
# 8N2 Çerçevesi: 2 Stop biti
frame_8n2 = UARTFrameEncoder.encode_byte(test_val, 8, 'N', 2)

dec_8n1 = UARTFrameEncoder.decode_frame(frame_8n1, 8, 'N', 1)
dec_8e1 = UARTFrameEncoder.decode_frame(frame_8e1, 8, 'E', 1)

print("[*] UART Çerçeveleme (Framing) Doğrulama Testi:")
print(f"  [+] 'M' (0x4D) 8N1 Frame ({len(frame_8n1)} bit): {frame_8n1}")
print(f"  [+] 'M' (0x4D) 8E1 Frame ({len(frame_8e1)} bit): {frame_8e1}")
print(f"  [+] 'M' (0x4D) 8O1 Frame ({len(frame_8o1)} bit): {frame_8o1}")
print(f"  [+] 'M' (0x4D) 8N2 Frame ({len(frame_8n2)} bit): {frame_8n2}")
print(f"  [+] 8N1 Çözümleme : {dec_8n1['char']} (Hata: {dec_8n1['error']})")
print(f"  [+] 8E1 Çözümleme : {dec_8e1['char']} (Hata: {dec_8e1['error']})")

# Kasıtlı Parity Bozulması Testi
corrupted_8e1 = list(frame_8e1)
corrupted_8e1[9] ^= 1 # Parity bitini ters çevir
dec_corrupt = UARTFrameEncoder.decode_frame(corrupted_8e1, 8, 'E', 1)
print(f"  [!] Bozuk Parity Testi: {dec_corrupt['error']}")

assert dec_8n1["valid"] is True and dec_8n1["data"] == 0x4D, "8N1 çözülemedi!"
assert dec_8e1["valid"] is True and dec_8e1["data"] == 0x4D, "8E1 çözülemedi!"
assert dec_corrupt["error"] == "PARITY_ERROR", "Parity hatası yakalanamadı!"
assert frame_8o1[9] == 1, "Odd parity biti 1 olmalıydı!"
print("\n[HÜCRE 6] UART framing ve parity doğrulama motoru başarıyla onaylandı.")
```

## 5. Kümülatif Saat Kayması (Baud Drift) ve Framing Error (FE)

Verici ve alıcı arasındaki baud hızı farkı yüzde olarak büyüdükçe, alıcının dahili saat darbeleri vericinin bit sınırlarından uzaklaşır.

### Saat Kaymasının Adım Adım İlerlemesi:
Aşağıdaki tabloda $\%4.5$ saat kayması olan bir sistemde alıcının örnekleme noktalarının ideal merkezden sapması gösterilmiştir:

| Bit Sırası | Nominal Merkez | Alıcının Örneklediği An | Kümülatif Sapma | Durum |
| :--- | :--- | :--- | :--- | :--- |
| **START** | $0.50\ T_{\text{bit}}$ | $0.50\ T_{\text{bit}}$ | $0.00\ T_{\text{bit}}$ | Senkronize |
| **D0** | $1.50\ T_{\text{bit}}$ | $1.54\ T_{\text{bit}}$ | $+0.04\ T_{\text{bit}}$ | Güvenli |
| **D3** | $4.50\ T_{\text{bit}}$ | $4.68\ T_{\text{bit}}$ | $+0.18\ T_{\text{bit}}$ | Güvenli |
| **D7** | $8.50\ T_{\text{bit}}$ | $8.86\ T_{\text{bit}}$ | $+0.36\ T_{\text{bit}}$ | Kritik (Majority sınırda) |
| **STOP** | $9.50\ T_{\text{bit}}$ | $10.05\ T_{\text{bit}}$ | $+0.55\ T_{\text{bit}}$ | **ÇÖKME (Framing Error)** |

Alıcı STOP bitini örneklemek istediğinde, zaman kayması yarım biti aştığı için alıcı artık STOP bitini değil, bir sonraki baytın START bitini (lojik 0) veya hattın belirsiz geçiş bölgesini okur! Lojik 1 göremeyen donanım anında **Framing Error (`FE = 1`)** bayrağını kaldırır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 2 — Baud Hızı Saat Kayması (Clock Drift) ve Framing Error (FE) Simülatörü
Frekans Sapmasının Kümülatif Zamanlama Hatası ve STOP Biti Üzerindeki Yıkıcı Etkisi
"""

import numpy as np
from typing import Dict, List, Tuple

class ClockDriftSimulator:
    """Verici ve Alıcı Arasındaki Saat Frekansı Sapmasını Simüle Eden Motor"""
    def __init__(self, nominal_baud: int = 115200):
        self.nominal_baud = nominal_baud
        self.t_bit_ideal = 1.0 / nominal_baud

    def simulate_transmission(self, drift_percent: float, bits: List[int]) -> Dict[str, any]:
        """
        drift_percent: +3.0 -> Alıcı %3 daha hızlı, -3.0 -> Alıcı %3 daha yavaş
        bits: [START(0), D0..D7, STOP(1)] (10 bit)
        """
        drift_ratio = 1.0 + (drift_percent / 100.0)
        rx_baud = self.nominal_baud * drift_ratio
        t_bit_rx = 1.0 / rx_baud

        # Alıcının her bit için örnekleme anları (Start bit düşen kenarı t=0 kabul edilir)
        sample_times = [(i + 0.5) * t_bit_rx for i in range(len(bits))]
        
        sampled_values = []
        timing_errors_fraction = []
        framing_error = False

        for i, t_sample in enumerate(sample_times):
            # İdeal verici dalga formunda t_sample anındaki gerçek bit hangisi?
            tx_bit_index = int(t_sample / self.t_bit_ideal)
            
            # Kümülatif sapmanın bit periyoduna oranı
            ideal_center = (i + 0.5) * self.t_bit_ideal
            error_fraction = (t_sample - ideal_center) / self.t_bit_ideal
            timing_errors_fraction.append(error_fraction)

            if tx_bit_index < len(bits):
                read_val = bits[tx_bit_index]
            else:
                read_val = 1 # Hat stop sonrası idle (1)

            sampled_values.append(read_val)

            # Stop biti kontrolü (Son bit)
            if i == len(bits) - 1:
                # Stop biti lojik 1 olmalıdır
                if read_val != 1 or tx_bit_index != (len(bits) - 1):
                    framing_error = True

        return {
            "drift_percent": drift_percent,
            "framing_error": framing_error,
            "timing_errors_fraction": timing_errors_fraction,
            "sampled_values": sampled_values,
            "max_drift_fraction": max(abs(e) for e in timing_errors_fraction)
        }

# Simülasyon: Farklı Baud Sapmalarında 8N1 Çerçevesi
test_bits = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1] # Alternatif bitler + Stop(1)
drift_tests = [-6.0, -3.5, -1.0, 0.0, +1.0, +3.5, +6.0]

sim_engine = ClockDriftSimulator(nominal_baud=115200)

print(f"[*] Baud Hızı Saat Sapması (Baud Drift) Dayanıklılık Analizi:")
print(f"{'Drift (%)':>10} | {'Maks Kayma (Bit)':>18} | {'Stop Biti Hata?':>16} | {'Sonuç'}")
print("-" * 60)

for d in drift_tests:
    res = sim_engine.simulate_transmission(d, test_bits)
    status_str = "[FAIL] Framing Error" if res["framing_error"] else "[PASS] Kararlı"
    print(f"{d:>9.1f}% | {res['max_drift_fraction']:>17.3f}x | {str(res['framing_error']):>16} | {status_str}")

# Katı Doğrulama Testi
res_safe = sim_engine.simulate_transmission(1.5, test_bits)
res_fatal = sim_engine.simulate_transmission(6.0, test_bits)

assert res_safe["framing_error"] is False, "%1.5 sapmada framing error olmamalı!"
assert res_fatal["framing_error"] is True, "%6.0 sapmada STOP biti kaymalı ve FE oluşmalı!"
print("\n[HÜCRE 8] Baud drift ve kümülatif framing error simülatörü başarıyla doğrulandı.")
```

## 6. Lock-Free SPSC Ring Buffer (Dairesel Tampon) Mimarisi

Kesme fonksiyonu (`USART_IRQHandler`) ile ana kod arasında paylaşılan en güvenli veri yapısı **Lock-Free SPSC (Single Producer Single Consumer) Ring Buffer**'dır.

### Temel Prensipler:
1. **Tek Üretici (Producer):** Yalnızca `USART_IRQHandler` `head` (yazma) indeksini artırır.
2. **Tek Tüketici (Consumer):** Yalnızca ana görev `tail` (okuma) indeksini artırır.
3. **Kilit Yok (Lock-Free):** Mutex, semafor veya kesme kapatma (`__disable_irq()`) gerekmez! Çünkü üretici ve tüketici asla aynı indeksi modifiye etmez.
4. **Power-of-Two (2'nin Kuvveti) Optimizasyonu:**
   Tampon boyutu ($N$) 2'nin bir kuvveti seçilirse ($16, 32, 64, 128, 256, 1024$):
   İndeks sarmalama işlemi yavaş modulo bölmesi (`index % N`) yerine tek çevrimlik mantıksal VE (`index & (N - 1)`) ile yapılır:
   $$\text{Mask} = N - 1 \implies \text{next\_index} = (\text{index} + 1) \ \& \ \text{Mask}$$
   ARM Cortex-M çekirdeğinde `SDIV` donanımsal bölme komutu $2 - 12$ çevrim sürerken, `AND` komutu **$1$ çevrim** sürer!

```
     BOŞ TAMPON (head == tail)            DOLU TAMPON (next_head == tail)
          [0]  [1]  [2]  [3]                     [0]  [1]  [2]  [3]
         +----+----+----+----+                  +----+----+----+----+
         |    |    |    |    |                  | D0 | D1 | D2 |    |
         +----+----+----+----+                  +----+----+----+----+
           ^                                      ^              ^
        HEAD, TAIL                               TAIL           HEAD (1 slot boş kalır)
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 3 — C++20 Uyumlu Lock-Free SPSC Ring Buffer Simülasyonu
Power-of-Two Maskeleme, Taşma (Overflow) Koruması ve Kilit-Siz İndeks Yönetimi
"""

from typing import Optional, List

class LockFreeSPSCRingBuffer:
    """
    Tek Üretici (ISR) - Tek Tüketici (Thread) Dairesel Tampon.
    Tampon boyutu kesinlikle 2'nin kuvveti olmalıdır (Örn: 16, 64, 256).
    """
    def __init__(self, capacity_power_of_two: int = 16):
        # 2'nin kuvveti kontrolü: (N & (N - 1)) == 0
        assert (capacity_power_of_two & (capacity_power_of_two - 1)) == 0, "Kapasite 2'nin kuvveti olmalıdır!"
        self.capacity = capacity_power_of_two
        self.mask = capacity_power_of_two - 1
        self.buffer = [0] * self.capacity
        self.head = 0 # Üretici yazar
        self.tail = 0 # Tüketici okur
        self.overflow_drops = 0

    def push_from_isr(self, byte_val: int) -> bool:
        """Üretici (ISR) Metodu: Kilit yok, atomik indeks ilerletme"""
        next_head = (self.head + 1) & self.mask
        if next_head == self.tail:
            # Tampon tamamen dolu! Taşma politikası: Yeni gelen baytı at (Drop)
            self.overflow_drops += 1
            return False

        self.buffer[self.head] = byte_val & 0xFF
        self.head = next_head
        return True

    def pop_to_consumer(self) -> Optional[int]:
        """Tüketici (Ana Görev) Metodu: Kilit yok"""
        if self.head == self.tail:
            return None # Tampon boş

        byte_val = self.buffer[self.tail]
        self.tail = (self.tail + 1) & self.mask
        return byte_val

    def available(self) -> int:
        """Tampondaki okunmaya hazır bayt sayısı"""
        return (self.head - self.tail) & self.mask

    def is_full(self) -> bool:
        return ((self.head + 1) & self.mask) == self.tail

# Test ve Doğrulama
ring = LockFreeSPSCRingBuffer(capacity_power_of_two=8) # Kapasite 8 (Maks 7 bayt saklar)

# 1. 5 Bayt Yaz
test_data = [0x10, 0x20, 0x30, 0x40, 0x50]
for b in test_data:
    assert ring.push_from_isr(b) is True

print("[*] Lock-Free SPSC Ring Buffer Doğrulama Testi:")
print(f"  [+] 5 bayt yazıldı. Hazır bayt sayısı : {ring.available()}")
assert ring.available() == 5

# 2. 2 Bayt Oku
read_b1 = ring.pop_to_consumer()
read_b2 = ring.pop_to_consumer()
print(f"  [+] 2 bayt okundu: 0x{read_b1:02X}, 0x{read_b2:02X}. Kalan: {ring.available()}")
assert read_b1 == 0x10 and read_b2 == 0x20
assert ring.available() == 3

# 3. Tamponu Doldur (Maks 7 bayt saklayabilir, 4 bayt daha yazalım)
for b in [0x60, 0x70, 0x80, 0x90]:
    ring.push_from_isr(b)

print(f"  [+] Tampon dolduruldu. Hazır bayt: {ring.available()}, Dolu mu: {ring.is_full()}")
assert ring.is_full() is True

# 4. Taşma (Overflow) Testi: Doluyken 1 bayt daha zorla
overflow_result = ring.push_from_isr(0xFF)
print(f"  [!] Taşma denemesi kabul edildi mi: {overflow_result} (Düşen paketler: {ring.overflow_drops})")
assert overflow_result is False
assert ring.overflow_drops == 1

# 5. Kalan tüm baytları oku (Wrap-around testi)
drained = []
while True:
    b = ring.pop_to_consumer()
    if b is None:
        break
    drained.append(b)

print(f"  [+] Boşaltılan baytlar: {[hex(x) for x in drained]}")
assert drained == [0x30, 0x40, 0x50, 0x60, 0x70, 0x80, 0x90]
assert ring.available() == 0
print("\n[HÜCRE 10] Lock-free ring buffer ve power-of-two maskeleme başarıyla doğrulandı.")
```

## 7. STM32 USART RX Interrupt (RXNE) ve Halka Tampon Entegrasyonu

Gömülü C/C++ mimarisinde UART sürücüsü iki katmana bölünür:

### 1. Donanım Kesme Katmanı (Interrupt Handler - Top Half):
Mikrodenetleyici vektör tablosunda tanımlı olan kesme rutini:
```c
void USART1_IRQHandler(void) {
    uint32_t sr = USART1->SR;

    // 1. RXNE Bayrağı Kontrolü (Yeni veri geldi mi?)
    if (sr & USART_SR_RXNE) {
        uint8_t received_byte = (uint8_t)(USART1->DR & 0xFF);
        // Doğrudan Lock-Free Ring Buffer'a it
        g_uart_rx_ring.push_from_isr(received_byte);
    }

    // 2. Hata Bayrakları Kontrolü (ORE, FE, PE)
    if (sr & (USART_SR_ORE | USART_SR_FE | USART_SR_PE)) {
        // STM32'de ORE/FE bayrağını temizlemek için SR okunur ardından DR okunur
        volatile uint32_t dummy = USART1->DR;
        (void)dummy;
        g_uart_error_count++;
    }
}
```

### 2. Kullanıcı Katmanı (User Task - Bottom Half):
Ana döngü veya FreeRTOS görevi:
```cpp
void Telemetry_Task(void *params) {
    while (true) {
        if (auto byte_opt = g_uart_rx_ring.pop_to_consumer(); byte_opt.has_value()) {
            parser.feed_byte(*byte_opt);
        } else {
            vTaskDelay(pdMS_TO_TICKS(1)); // Tampon boşsa CPU'yu diğer görevlere bırak
        }
    }
}
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 4 — Kesme Tabanlı Sanal STM32 USART RXNE ve Ring Buffer Sürücüsü
Sanal Donanım Kesmesi, Top-Half Tamponlama ve CPU Yükü Karşılaştırması
"""

from typing import List

class VirtualSTM32InterruptUART:
    """Sanal Donanım ve Kesme Motoru Modeli"""
    def __init__(self, rx_buffer_size: int = 64):
        self.ring_buffer = LockFreeSPSCRingBuffer(rx_buffer_size)
        self.rxne_interrupt_count = 0
        self.error_interrupt_count = 0
        self.cpu_cycles_spent_in_isr = 0

    def hardware_incoming_byte(self, byte_val: int, has_framing_error: bool = False):
        """Donanımın RX pininden bir bayt tamamlandığında NVIC kesmesi fırlatması"""
        # 1. Donanım Kesme Hizmet Rutini (USART1_IRQHandler Simülasyonu)
        self.rxne_interrupt_count += 1
        self.cpu_cycles_spent_in_isr += 15 # Top-half ortalama 15 çevrim sürer

        if has_framing_error:
            self.error_interrupt_count += 1
        else:
            # Ring buffer'a ekle
            self.ring_buffer.push_from_isr(byte_val)

    def read_available_data(self) -> List[int]:
        """Tüketici katmanının tamponu boşaltması"""
        collected = []
        while True:
            b = self.ring_buffer.pop_to_consumer()
            if b is None:
                break
            collected.append(b)
        return collected

# Simülasyon: 20 Baytlık Sensör Telemetri Verisi Akışı
sensor_stream = list(b"ASELSAN_RADAR_ALT_99")
uart_system = VirtualSTM32InterruptUART(rx_buffer_size=32)

# Donanımdan peş peşe baytlar akıyor
for b in sensor_stream:
    uart_system.hardware_incoming_byte(b)

# 1 bayt Framing Error enjekte et
uart_system.hardware_incoming_byte(0x00, has_framing_error=True)

# Tüketici veriyi okur
received_bytes = uart_system.read_available_data()
received_text = bytes(received_bytes).decode('ascii')

# CPU Yükü Karşılaştırması (Polling vs Interrupt)
# 20 Bayt @ 115200 baud -> ~1.73 ms sürer. 168 MHz'de toplam çevrim: 290,000 çevrim
total_mcu_cycles = 290_000
isr_cycles = uart_system.cpu_cycles_spent_in_isr
interrupt_cpu_overhead_pct = (isr_cycles / total_mcu_cycles) * 100.0

print("[*] Kesme Tabanlı UART RX ve CPU Yükü Analizi:")
print(f"  [+] Alınan Telemetri     : {received_text}")
print(f"  [+] Tetiklenen RXNE ISR  : {uart_system.rxne_interrupt_count} adet")
print(f"  [+] Yakalanan Hata       : {uart_system.error_interrupt_count} adet FE")
print(f"  [+] ISR Toplam Çevrim    : {isr_cycles} çevrim")
print(f"  [+] Kesme Tabanlı CPU Yükü: %{interrupt_cpu_overhead_pct:.3f} (Polling: %100.0)")

assert received_text == "ASELSAN_RADAR_ALT_99", "Gelen telemetri verisi eşleşmiyor!"
assert uart_system.error_interrupt_count == 1, "Framing error yakalanmalıydı!"
assert interrupt_cpu_overhead_pct < 0.5, "Kesme yükü %0.5'in altında olmalı!"
print("\n[HÜCRE 12] Kesme tabanlı sanal USART ve ring buffer sürücüsü başarıyla doğrulandı.")
```

## 8. Savunma Sanayii Aviyonik Senaryosu: Radar Altimetre Telemetrisi

Seyir füzeleri (Cruise Missiles - SOM, ATMACA) yer yüzeyine çok yakın uçuş (Terrain Following) yapabilmek için milimetrik hassasiyette bir Radar Altimetresine ihtiyaç duyar.

### Sistem Parametreleri:
- **Veri Yolu Hızı:** $921600\ \text{baud}$ (Her bayt $\approx 10.85\ \mu\text{s}$).
- **Veri Akışı:** Saniyede $500\ \text{paket}$, her paket $32\ \text{bayt}$ $\implies 16.000\ \text{bayt/saniye}$.
- **Güdüm Algoritması WCET (Worst-Case Execution Time):** Kalman filtresi ve navigasyon çözümü her çevrimde CPU'yu $5\ \text{ms}$ boyunca $\%100$ meşgul eder.

### Aviyonik Tampon Boyutlandırma Kuralı:
Eğer tüketici görev (Navigation Task) $5\ \text{ms}$ boyunca ring buffer'dan veri çekemezse, bu sürede hattan kaç bayt birikir?
$$N_{\text{burst}} = \text{Data Rate} \times T_{\text{latency}} = 16.000\ \text{bayt/s} \times 0.005\ \text{s} = 80\ \text{bayt}$$
- Eğer geliştirici standart $64\ \text{bayt}$ tampon seçerse: Tampon $80 - 64 = 16\ \text{bayt}$ taşar, radar irtifa telemetrisi ezilir (`ORE`) ve füze yere çakılır!
- **Mühendislik Kararı:** $N_{\text{burst}} = 80\ \text{bayt}$ için 2'nin bir sonraki kuvveti olan **$128$ veya $256\ \text{bayt}$** ring buffer seçilmelidir!

```python
# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 5 — Aviyonik Radar Altimetre WCET Tampon Boyutlandırma Testi
921600 Baud Hızında Görev Gecikmesi (Task Jitter) ve Tampon Taşma Analizi
"""

def test_buffer_sizing(buffer_capacity: int, burst_bytes: int) -> Dict[str, any]:
    ring = LockFreeSPSCRingBuffer(capacity_power_of_two=buffer_capacity)
    # Patlama anında gelen verileri it
    for i in range(burst_bytes):
        ring.push_from_isr(i & 0xFF)

    return {
        "capacity": buffer_capacity,
        "burst_bytes": burst_bytes,
        "saved_bytes": ring.available(),
        "dropped_bytes": ring.overflow_drops,
        "is_safe": ring.overflow_drops == 0
    }

# Senaryo: 5 ms görev bloklanmasında biriken 80 baytlık veri patlaması
burst_size = 80

res_64 = test_buffer_sizing(buffer_capacity=64, burst_bytes=burst_size)
res_128 = test_buffer_sizing(buffer_capacity=128, burst_bytes=burst_size)
res_256 = test_buffer_sizing(buffer_capacity=256, burst_bytes=burst_size)

print("[*] Aviyonik Radar Altimetre Tampon Boyutlandırma Raporu (80 Bayt Patlama):")
print(f"  [!] 64-Bayt Tampon  : Kaydedilen = {res_64['saved_bytes']}, Düşen = {res_64['dropped_bytes']} bayt -> [FAIL] TEHLİKELİ")
print(f"  [+] 128-Bayt Tampon : Kaydedilen = {res_128['saved_bytes']}, Düşen = {res_128['dropped_bytes']} bayt -> [PASS] GÜVENLİ")
print(f"  [+] 256-Bayt Tampon : Kaydedilen = {res_256['saved_bytes']}, Düşen = {res_256['dropped_bytes']} bayt -> [PASS] ASKERİ MARJ")

assert res_64["is_safe"] is False and res_64["dropped_bytes"] > 0, "64 bayt taşmalıydı!"
assert res_128["is_safe"] is True and res_128["dropped_bytes"] == 0, "128 bayt sıfır kayıp sağlamalı!"
assert res_256["is_safe"] is True and res_256["dropped_bytes"] == 0, "256 bayt sıfır kayıp sağlamalı!"
print("\n[HÜCRE 14] Aviyonik WCET tampon boyutlandırma analizi başarıyla doğrulandı.")
```

## 9. Üretim Seviyesi C++20 Lock-Free Ring Buffer Şablonu

Modern savunma sistemlerinde C++20 `std::atomic`, `concepts` ve `std::span` ile sıfır ek maliyetli (zero-cost) dairesel tampon mimarisi:

```cpp
// ============================================================================
// C++20 Lock-Free SPSC Ring Buffer (Power-of-Two Optimized)
// ============================================================================
#include <cstdint>
#include <concepts>
#include <atomic>
#include <optional>
#include <array>

namespace defense::containers {

template <typename T, size_t Capacity>
requires (Capacity > 1 && ((Capacity & (Capacity - 1)) == 0)) // 2'nin kuvveti konsepti
class SpscRingBuffer {
public:
    static constexpr size_t Mask = Capacity - 1;

    // Üretici (ISR) Çağırır
    bool push(T item) noexcept {
        const size_t current_head = head_.load(std::memory_order_relaxed);
        const size_t next_head = (current_head + 1) & Mask;

        // Tail'i acquire ile oku
        if (next_head == tail_.load(std::memory_order_acquire)) {
            return false; // Tampon dolu
        }

        buffer_[current_head] = item;
        head_.store(next_head, std::memory_order_release); // Veriyi yayınla
        return true;
    }

    // Tüketici (Ana Kod) Çağırır
    std::optional<T> pop() noexcept {
        const size_t current_tail = tail_.load(std::memory_order_relaxed);

        // Head'i acquire ile oku
        if (current_tail == head_.load(std::memory_order_acquire)) {
            return std::nullopt; // Tampon boş
        }

        T item = buffer_[current_tail];
        tail_.store((current_tail + 1) & Mask, std::memory_order_release);
        return item;
    }

    [[nodiscard]] size_t size() const noexcept {
        return (head_.load(std::memory_order_relaxed) - tail_.load(std::memory_order_relaxed)) & Mask;
    }

private:
    std::array<T, Capacity> buffer_{};
    alignas(64) std::atomic<size_t> head_{0}; // False sharing önlemek için cache-line hizalı
    alignas(64) std::atomic<size_t> tail_{0};
};

} // namespace defense::containers
```

## 10. Bilerek Bozduğumuz Şey (Sabotaj ve Arıza Analizi)

### Sabotaj 1: 2'nin Kuvveti Olmayan Tampon ve Yavaş Modulo (`%`) Kullanımı
Bir geliştiricinin `Capacity = 100` seçip indeksi `(head + 1) % 100` ile ilerletmesi:
- **Ne Olur?:** ARM Cortex-M4 çekirdeğinde donanımsal bölme komutu (`UDIV`) $2$ ila $12$ çevrim sürer ve pipeline'ı durdurur.
- **Sonuç:** $921600\ \text{baud}$ hızında her $10.85\ \mu\text{s}$'de bir kesmeye giren işlemci, her baytta modulo hesaplarken kesme süresini gereksiz uzatır. Yüksek hızda yeni kesme yetişemez ve `ORE` oluşur!

### Sabotaj 2: ISR İçinde `printf` veya Bloklayıcı Çağrı Yapmak
```c
// ÖLÜMCÜL KOD (SABOTAJ):
void USART1_IRQHandler(void) {
    if (USART1->SR & USART_SR_RXNE) {
        uint8_t b = USART1->DR;
        printf("Gelen Bayt: %02X\n", b); // SABOTAJ!
    }
}
```
- **Ne Olur?:** `printf` fonksiyonu dahili olarak yüzlerce bayt formatlar ve kendisi de başka bir UART üzerinden bloklayıcı iletim yapar!
- **Sonuç:** Bir baytın kesmesi bitmeden arkadan gelen 10 adet bayt kaçırılır, sistem tamamen kilitlenir.

## 11. Karşılaştırma Matrisi: Ring Buffer Tasarım Tercihleri

| Tasarım Kriteri | Modulo Tabanlı (`% N`) | Power-of-Two Maskeleme (`& Mask`) | Mutex / Kilit Korumalı Tampon |
| :--- | :--- | :--- | :--- |
| **Boyut Esnekliği** | İstenen her sayı (örn. 100) | **Yalnızca $2^k$ (64, 128, 256)** | İstenen her sayı |
| **CPU Çevrim Maliyeti** | $8 - 14$ çevrim (`UDIV`) | **$1$ çevrim (`AND`)** | $> 50$ çevrim (OS syscall) |
| **ISR Güvenliği** | Güvenli (SPSC ise) | **Mükemmel (Kilit-siz, sıfır bekleme)** | **YASAK! (ISR içinde kilit alınamaz)** |
| **Bellek Hizalaması** | Standart | Standart / Cache-line hizalı | Kernel nesnesi tahsisi |
| **Savunma Standardı** | Düşük hızlı sistemler | **DO-178C / MISRA Aviyonik Standart** | Sadece RTOS görevleri arası |

## 12. Donanım ve Yazmaç Haritası (STM32 USART CR1/CR2/CR3)

STM32 USART çerçeveleme ve kesme kontrol bitleri:

```
  USART_CR1 (Control Register 1):
  [13] UE   : USART Enable
  [12] M    : Word Length (0: 8 Data Bits, 1: 9 Data Bits)
  [10] PCE  : Parity Control Enable (1: Eşlik biti aktif)
  [9]  PS   : Parity Selection (0: Even Parity, 1: Odd Parity)
  [5]  RXNEIE : RXNE Interrupt Enable (Alım kesmesini açar)
  [3]  TE   : Transmitter Enable
  [2]  RE   : Receiver Enable

  USART_CR2 (Control Register 2):
  [13:12] STOP : Stop Bits Selection
                 00: 1 Stop Bit
                 01: 0.5 Stop Bit (SmartCard için)
                 10: 2 Stop Bits (Uzun hatlar için)
                 11: 1.5 Stop Bits
```

## 13. Mülakat ve Saha Tuzakları (Top 5 Gotchas)

1. **"8E1 gönderiyorum ama alıcı 9 bit okuyor" Tuzağı:**
   - STM32'de Parity açıldığında (`PCE = 1`), parity biti veri uzunluğuna **DAHİLDİR**. 8 bit veri + 1 bit parity göndermek istiyorsanız `CR1_M` bitini `1` (9-bit mode) yapmalısınız! Aksi takdirde son veri biti ezilir.
2. **Ring Buffer'da Head ve Tail'i `volatile` Yapmamak:**
   - Kesme `head` değerini değiştirirken ana döngü bunu register caching sebebiyle göremez ve tamponu hep boş zanneder.
3. **Tampon Doluyken Veri Geldiğinde Kilitlenmek:**
   - Doluluk kontrolü yapılmazsa `head` `tail`'in üzerine yazar; tampon bir anda tamamen boş algılanır ve tüm geçmiş veri kaybolur.
4. **NVIC Önceliğini Yanlış Yapılandırmak:**
   - Eğer UART kesmesinin önceliği motor kontrol veya sensör kesmelerinden yüksek verilirse, UART kesmesi motor PWM güncellemelerini geciktirebilir.
5. **Framing Error Oluştuğunda Bayrağı Temizlememek:**
   - Hat parazitinden dolayı `FE` oluştuğunda bazı STM32 çekirdekleri DR okunana kadar yeni veri alımını durdurur.

## 14. 5N1K Özeti

- **Ne?:** UART Framing (8N1, 8E1, 8N2), baud toleransı limitleri ve kesme tabanlı lock-free dairesel tampon (ring buffer) mimarisi.
- **Neden?:** Yüksek hızlı aviyonik veri akışlarında veri kaybını (ORE), çerçeveleme hatalarını (FE) ve CPU'nun polling döngülerinde kilitlenmesini engellemek için.
- **Nasıl?:** Donanım saat kaymasını $\pm 2.5\%$ altında tutarak, RXNE kesmesinde veriyi 2'nin kuvveti boyutlu dairesel tampona itip ana görevde tüketerek.
- **Nerede?:** Radar altimetreleri, füze güdüm kitleri, İHA telemetri modemleri ve taktik haberleşme cihazlarında.
- **Ne Zaman?:** Veri hızının $> 115200\ \text{baud}$ olduğu ve CPU'nun aynı anda kontrol algoritmaları koşturduğu tüm zamanlarda.
- **Kim?:** Aviyonik gömülü yazılım mühendisleri, savunma sanayii sistem mimarları.

## 15. Gün Sonu Özeti ve Yetkinlik Kontrolü

### 3 Cümlelik Özet:
1. **UART Framing ve Buffer Nedir?:** UART framing, elektriksel hattan akan bitlerin start, parity ve stop kurallarıdır; buffer ise kesmeyle yakalanan baytların ana koda aktarıldığı dairesel kuyruktur.
2. **Hangi Problemi Çözer?:** Bağımsız osilatörlerin saat kaymasını tolere eder, kesmelerle CPU yükünü $\%100$'den $\%0.2$'ye düşürür ve veri taşmasını önler.
3. **Getirdiği Risk / Trade-off:** Yanlış boyutlandırılmış tampon telemetri kaybına (drop), $\%3.75$'i aşan baud sapması ise framing error'a yol açar.

### Yetkinlik Kontrol Listesi:
- [x] 8N1, 8E1, 8O1 ve 8N2 çerçeve yapılarını ve parity hesaplamasını biliyorum.
- [x] Kümülatif baud drift matematiğini ve STOP bitinde neden FE oluştuğunu anladım.
- [x] Lock-Free SPSC Ring Buffer'da power-of-two (`& Mask`) optimizasyonunu uygulayabiliyorum.
- [x] STM32 `RXNEIE` kesmesi ve Top-Half mimarisini açıklayabiliyorum.
- [x] Aviyonik WCET görev gecikmesine göre minimum tampon boyutu hesabı yapabiliyorum.

## 16. İleri Okuma ve Kaynaklar

1. **STMicroelectronics Reference Manual (RM0090):** *USART Interrupts, Parity and Stop Bit Control Registers.*
2. **Lock-Free Queue Implementation on ARM:** *Dmitry Vyukov - Lock-Free Multi-Producer Multi-Consumer Queue Principles.*
3. **DO-178C Airborne Systems Software Guidelines:** *Data Buffer Sizing and Worst-Case Execution Time (WCET) Verification.*
4. **Embedded C++ Design Patterns:** *Miro Samek - Practical Statecharts & Event-Driven Embedded Systems.*

## 17. 24-Hücreli Master Mimari Onay Beyanı

Bu eğitim modülü, ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ standartlarında C++20 ve STM32 Gömülü Sistemler Müfredatı kapsamında hazırlanmıştır.

```
+-----------------------------------------------------------------------------------+
|               GÜN 169 MASTER MİMARİ MÜHENDİSLİK DOĞRULAMA RAPORU                  |
+-----------------------------------------------------------------------------------+
| 1. Toplam Hücre Sayısı        : 24 Hücre (18 Markdown, 6 Python Kodu)             |
| 2. Çerçeveleme Modelleri      : 8N1, 8E1, 8O1, 8N2, Parity ve Stop Bitleri        |
| 3. Kümülatif Saat Kayması     : Baud Drift ve Framing Error (FE) Analizi          |
| 4. Tampon Mimarisi            : Lock-Free SPSC Ring Buffer (Power-of-Two Mask)    |
| 5. Aviyonik Senaryosu         : Radar Altimetre 921600 Baud WCET Boyutlandırması  |
| 6. Görsel Artefact            : 300 DPI 4-Panelli Koyu Tema Dashboard (.PNG)      |
| 7. Özel Lisans                : Telif Hakkı (c) 2026 Seydi Eryılmaz               |
+-----------------------------------------------------------------------------------+
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. UART Framing Formatları Karşılaştırması (8N1 vs 8E1 vs 8N2)
2. Baud Hızı Saat Kayması (Clock Drift) ve Kümülatif Örnekleme Sapması (FE Bölgesi)
3. Lock-Free Ring Buffer Dairesel Bellek Modeli (Head, Tail, Boş, Dolu, Wrap-Around)
4. Aviyonik WCET Görev Gecikmesine Karşı Minimum Tampon Boyutu Eğrisi
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

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
# PANEL 1: UART Framing Formatları (8N1 vs 8E1 vs 8N2)
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

formats = ['8N1 (10 Bit)', '8E1 (11 Bit)', '8N2 (11 Bit)']
y_positions = [2.5, 1.5, 0.5]

# 8N1: START(0), D0..D7(8), STOP(1)
# 8E1: START(0), D0..D7(8), PARITY(1), STOP(1)
# 8N2: START(0), D0..D7(8), STOP1(1), STOP2(1)

def plot_frame_bar(ax, y, labels, colors, widths):
    x_curr = 0
    for l, c, w in zip(labels, colors, widths):
        ax.barh(y, w, left=x_curr, height=0.5, color=c, edgecolor='#0F172A', alpha=0.9)
        ax.text(x_curr + w/2, y, l, ha='center', va='center', color='#0F172A', fontweight='bold', fontsize=8)
        x_curr += w

# 8N1
plot_frame_bar(ax1, 2.5, ['START', '8 DATA BITS', 'STOP'], [C_YELLOW, C_CYAN, C_GREEN], [1, 8, 1])
# 8E1
plot_frame_bar(ax1, 1.5, ['START', '8 DATA BITS', 'PARITY', 'STOP'], [C_YELLOW, C_CYAN, C_PURPLE, C_GREEN], [1, 8, 1, 1])
# 8N2
plot_frame_bar(ax1, 0.5, ['START', '8 DATA BITS', 'STOP 1', 'STOP 2'], [C_YELLOW, C_CYAN, C_GREEN, '#10B981'], [1, 8, 1, 1])

ax1.set_yticks(y_positions)
ax1.set_yticklabels(formats, fontsize=10, color=C_WHITE, fontweight='bold')
ax1.set_xlabel("Bit Süresi (Tbit Cinsinden)", color=C_WHITE, fontsize=10)
ax1.set_title("Panel 1: UART Çerçeveleme (Framing) Formatları Anatomisi", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.set_xlim(0, 12)
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')

# ------------------------------------------------------------------------------
# PANEL 2: Baud Hızı Saat Kayması (Clock Drift) ve Kümülatif Örnekleme Sapması
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

bits_seq = np.arange(0, 10, 1) # Start, D0..D7, Stop
drifts = [0.0, 2.0, 3.75, 5.0, 6.5]
colors_drift = [C_GREEN, C_CYAN, C_YELLOW, C_RED, '#EF4444']

for d, c in zip(drifts, colors_drift):
    # Kümülatif kayma: Delta T = i * (d / 100)
    cumulative_drift = bits_seq * (d / 100.0)
    label_str = f"Saat Sapması %{d:.2f}"
    if d == 0.0:
        label_str += " (İdeal)"
    elif d == 3.75:
        label_str += " (Aviyonik Limit)"
    elif d >= 5.0:
        label_str += " (Framing Error!)"
    ax2.plot(bits_seq, cumulative_drift, marker='o', color=c, linewidth=2, label=label_str)

# Hata Bölgesi (+0.5 Tbit sınırı)
ax2.axhline(0.5, color=C_RED, linestyle='--', linewidth=1.5, label='Kritik Eşik (+0.5 Tbit FE Sınırı)')
ax2.axhspan(0.5, 0.7, color=C_RED, alpha=0.2)
ax2.text(1, 0.53, "FRAMING ERROR (FE) BÖLGESİ", color=C_RED, fontweight='bold', fontsize=9)

ax2.set_xticks(bits_seq)
ax2.set_xticklabels(['START', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'STOP'], fontsize=8, color=C_WHITE)
ax2.set_ylabel("Kümülatif Kayma (Tbit Kesri)", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: Kümülatif Saat Kayması ve STOP Biti Sapması", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='upper left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: Lock-Free Ring Buffer Dairesel Bellek Modeli
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

# 16 Elemanlı Dairesel Tampon Çizimi
n_slots = 16
angles = np.linspace(0, 2*np.pi, n_slots, endpoint=False)
radii = np.ones(n_slots) * 5

# Temsili Dolu Yuvalar (Tail: 3, Head: 10 -> Yuvalar 3..9 dolu)
slot_colors = []
for i in range(n_slots):
    if 3 <= i <= 9:
        slot_colors.append(C_CYAN) # Dolu
    else:
        slot_colors.append('#334155') # Boş

x_coords = radii * np.cos(angles)
y_coords = radii * np.sin(angles)

ax3.scatter(x_coords, y_coords, s=550, c=slot_colors, edgecolors=C_WHITE, linewidth=1.5, zorder=3)

for i in range(n_slots):
    label = f"{i}"
    if i == 3:
        label += "\nTAIL"
    elif i == 10:
        label += "\nHEAD"
    ax3.text(x_coords[i], y_coords[i], label, ha='center', va='center', color=C_WHITE, fontsize=8, fontweight='bold')

# Merkez Bilgi Notu
ax3.text(0, 0.5, "Lock-Free SPSC\nPower-of-Two (16)", ha='center', va='center', color=C_WHITE, fontsize=11, fontweight='bold')
ax3.text(0, -1.5, "Dolu: 7 Bayt\nBoş: 8 Bayt\nMask: 0x0F", ha='center', va='center', color=C_YELLOW, fontsize=9)

ax3.set_xlim(-7, 7)
ax3.set_ylim(-7, 7)
ax3.set_aspect('equal')
ax3.axis('off')
ax3.set_title("Panel 3: Lock-Free Dairesel Tampon (Head/Tail ve Power-of-Two)", color=C_WHITE, fontsize=12, fontweight='bold')

# ------------------------------------------------------------------------------
# PANEL 4: Aviyonik WCET Görev Gecikmesine Karşı Minimum Tampon Boyutu
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

latency_ms = np.linspace(1, 20, 100) # 1 ms ila 20 ms WCET görev gecikmesi
# 921600 baud -> ~92160 byte/s (Teorik maks), tipik aviyonik telemetri: 20000 byte/s
data_rate_bytes_sec = 20_000

min_buffer_bytes = data_rate_bytes_sec * (latency_ms / 1000.0)

ax4.plot(latency_ms, min_buffer_bytes, color=C_CYAN, linewidth=2.5, label='Gereken Tampon (20 KB/s Veri Akışı)')

# Standart 2'nin kuvveti tampon eşikleri
ax4.axhline(64, color='#94A3B8', linestyle=':', label='64-Bayt Eşiği')
ax4.axhline(128, color=C_YELLOW, linestyle='--', label='128-Bayt Eşiği')
ax4.axhline(256, color=C_GREEN, linestyle='-.', label='256-Bayt Eşiği (Aviyonik Önerilen)')

# 5 ms kritik nokta (Güdüm WCET)
ax4.scatter([5.0], [100.0], color=C_RED, s=80, zorder=5)
ax4.annotate("5 ms Güdüm Gecikmesi\n(100 Bayt Birikir)", xy=(5, 100), xytext=(8, 150),
             color=C_RED, fontweight='bold', fontsize=9,
             arrowprops=dict(facecolor=C_RED, arrowstyle="->"))

ax4.set_xlabel("WCET Görev Bloklanma Süresi (ms)", color=C_WHITE, fontsize=10)
ax4.set_ylabel("Gereken Minimum Tampon (Bayt)", color=C_WHITE, fontsize=10)
ax4.set_title("Panel 4: Görev Gecikmesine Göre Tampon Boyutlandırma Eğrisi", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax4.legend(loc='upper left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.suptitle("GÜN 169: UART Framing, Baud Toleransı ve Lock-Free Dairesel Tampon Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_169_uart_framing_baud_ve_buffer.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_169\gun_169_uart_framing_baud_ve_buffer.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 169 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. Framing ve Parity Assertions
enc = UARTFrameEncoder()
f_test = enc.encode_byte(0x55, 8, 'E', 1)
d_test = enc.decode_frame(f_test, 8, 'E', 1)
assert d_test["valid"] is True and d_test["data"] == 0x55, "Framing decode hatası!"

# 3. Baud Drift Assertions
drift_sim = ClockDriftSimulator(115200)
res_drift_ok = drift_sim.simulate_transmission(2.0, [0, 1, 0, 1, 0, 1, 0, 1, 0, 1])
res_drift_fail = drift_sim.simulate_transmission(6.0, [0, 1, 0, 1, 0, 1, 0, 1, 0, 1])
assert res_drift_ok["framing_error"] is False, "2% drift tolere edilmeliydi!"
assert res_drift_fail["framing_error"] is True, "6% drift FE oluşturmalıydı!"

# 4. Lock-Free SPSC Ring Buffer Assertions
rb = LockFreeSPSCRingBuffer(32)
for i in range(10):
    rb.push_from_isr(i)
assert rb.available() == 10, "Ring buffer available hatalı!"
popped = [rb.pop_to_consumer() for _ in range(5)]
assert popped == list(range(5)), "Okunan bayt sırası hatalı!"
assert rb.available() == 5, "Kalan bayt sayısı hatalı!"

# 5. WCET Buffer Sizing Assertions
r_sz = test_buffer_sizing(buffer_capacity=128, burst_bytes=80)
assert r_sz["is_safe"] is True and r_sz["dropped_bytes"] == 0, "128 bayt sıfır kayıp sağlamalı!"

print("\n[PASS] Gün 169: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
```
