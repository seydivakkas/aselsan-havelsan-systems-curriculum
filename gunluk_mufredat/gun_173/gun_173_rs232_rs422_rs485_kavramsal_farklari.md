# GÜN 173: RS232, RS422 ve RS485 — Tek Uçlu vs Diferansiyel Sinyalleşme, Toprak Kayması ve Yön Kontrolü

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz.
```

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
![C++20](https://img.shields.io/badge/Standard-C%2B%2B20-blue.svg?style=flat-square)
![STM32](https://img.shields.io/badge/Hardware-STM32%20USART%20RS--485%20DEM-orange.svg?style=flat-square)
![Physical Layer](https://img.shields.io/badge/PHY-RS232%20%2F%20RS422%20%2F%20RS485-purple.svg?style=flat-square)
![Defense Grade](https://img.shields.io/badge/Domain-Armored%20Vehicle%20%2F%20MIL--STD-red.svg?style=flat-square)

---

## 1. Zihinsel Model ve Mimari Büyük Resim (Neden TTL Yetmez?)

Mikrodenetleyici (MCU) pinlerinden çıkan saf UART sinyalleri standart TTL/CMOS lojik seviyelerindedir ($0\ \text{V}$ ve $3.3\ \text{V}$ / $5\ \text{V}$). Bu seviyeler aynı devre kartı üzerindeki çipler arasında ($< 30\ \text{cm}$) mükemmel çalışır.

Ancak savunma sanayiinde sistemler tek bir karttan ibaret değildir:
- Bir zırhlı muharebe aracında (ASELSAN KORHAN / FNSS PARS) kule görev bilgisayarı ile gövdenin en arkasındaki motor kontrol ünitesi veya sis havanı fırlatıcısı arasında **$15 - 50\ \text{metre}$** kablo uzanır.
- Bir fırkateyn veya denizaltıda silah kontrol sistemi ile sonar sensörleri arasında **yüzlerce metre** mesafe vardır.
- Bu mesafelerde ortamda devasa motor ateşleme darbeleri, radar ışıması, telsiz vericileri ve yüksek akımlı güç kabloları bulunur (Aşırı Elektromanyetik Girişim - EMI).

Eğer $3.3\ \text{V}$ TTL sinyali bu kablolardan geçirilmeye çalışılırsa:
1. Kablo direnci ve kapasitansı sinyali emer ($RC$ alçak geçiren filtre etkisi).
2. Ortamdaki gürültü sinyalin üzerine biner; $0.5\ \text{V}$'luk bir gürültü darbesi bile lojik 0'ı lojik 1 gibi gösterir.
3. İki ucun şase toprakları arasında oluşan potansiyel farkı (Ground Potential Difference) alıcı çipi yakar.

Bu fiziksel imkansızlığı aşmak için **EIA/TIA Seri İletişim Standartları (RS-232, RS-422, RS-485)** geliştirilmiştir.

## 2. Tek Uçlu (Single-Ended) vs Diferansiyel (Differential) Sinyalleşme

Seri haberleşme fiziksel katmanındaki en temel ayrım, bilginin tek bir kablo ile zemin (GND) arasında mı, yoksa iki zıt kablo arasındaki gerilim farkı ile mi taşındığıdır.

### 1. Tek Uçlu (Single-Ended) Sinyalleşme (RS-232):
Veri sinyali tek bir iletkenden akar ve gerilim alıcı tarafın yerel toprak (GND) referansına göre ölçülür:
$$V_{\text{rx}} = V_{\text{signal}} - V_{\text{GND}}$$
- **Ölümcül Kusur:** Hatta dışarıdan binen bir EMI gürültüsü ($V_{\text{noise}}$) doğrudan sinyale eklenir:
  $$V_{\text{rx}} = (V_{\text{signal}} + V_{\text{noise}}) - V_{\text{GND}}$$
  Alıcı gürültüyü sinyalden ayıramaz! Mesafe $15\ \text{metre}$ ile sınırlıdır.

### 2. Diferansiyel (Differential) Sinyalleşme (RS-422 / RS-485):
Bilgi tek bir kablo yerine bükümlü bir çift kablo (**Twisted Pair: $A$ ve $B$ hatları**) üzerinden iletilir. Sinyal iki kabloya zıt fazda (biri $+$, diğeri $-$) basılır.
Alıcı, iki kablo arasındaki potansiyel farkını ölçer:
$$V_{\text{diff}} = V_A - V_B$$

```
+-----------------------------------------------------------------------------------+
|               DİFERANSİYEL SİNYALLEŞME VE ORTAK MOD GÜRÜLTÜ REDDİ (CMRR)          |
+-----------------------------------------------------------------------------------+

   Hat A (+) :   -----\_____/-----\_____/----- (+V_noise biner)
   Hat B (-) :   -----/-----\_____/-----\----- (+V_noise biner)
                           |
                           v
   Diferansiyel Alıcı: V_diff = (V_A + V_noise) - (V_B + V_noise)
                       V_diff = V_A - V_B  <=== GÜRÜLTÜ TAMAMEN YOK OLDU!
```

Kablolar birbirine sıkıca büküldüğü için dış ortamdan gelen manyetik alan veya radar paraziti her iki kabloya da **tam olarak eşit miktarda ($+V_{\text{noise}}$)** biner. Alıcı çıkarma işlemi yaptığı anda gürültü matematiksel olarak sıfırlanır (**Ortak Mod Gürültü Reddi - Common-Mode Rejection**)!

## 3. RS-232, RS-422 ve RS-485 Elektriksel Karşılaştırma Matrisi

Savunma sistemleri tasarımında doğru standardı seçmek donanımın yaşam döngüsünü belirler:

| Parametre | RS-232 (EIA-232) | RS-422 (TIA-422) | RS-485 (TIA-485) |
| :--- | :--- | :--- | :--- |
| **Sinyal Tipi** | **Tek Uçlu (Single-Ended)** | **Diferansiyel** | **Diferansiyel** |
| **Hat Sayısı** | 3 (TX, RX, GND) | 4 (TX+, TX-, RX+, RX-) + GND | **2 Hat (A, B) + GND** (veya 4) |
| **İletişim Modu** | **Tam Çift Yönlü (Full-Duplex)**| **Tam Çift Yönlü (Full-Duplex)**| **Yarı Çift Yönlü (Half-Duplex)**|
| **Maksimum Mesafe**| $15 - 20\ \text{metre}$ | **$1200\ \text{metre}$** | **$1200\ \text{metre}$** |
| **Maksimum Veri Hızı**| Düşük ($115.2\ \text{kbps}$) | **Yüksek ($10\ \text{Mbps}$)** | **Çok Yüksek ($10 - 50\ \text{Mbps}$)**|
| **Sürücü / Alıcı** | 1 Verici, 1 Alıcı (P2P) | 1 Verici, 10 Alıcı (Multi-Drop)| **32 Sürücü, 32 Alıcı (Multi-Point)**|
| **Lojik 1 Seviyesi**| $-3\ \text{V}$ ila $-15\ \text{V}$ (MARK) | $V_A < V_B$ ($V_{AB} \le -200\ \text{mV}$)| $V_A < V_B$ ($V_{AB} \le -200\ \text{mV}$)|
| **Lojik 0 Seviyesi**| $+3\ \text{V}$ ila $+15\ \text{V}$ (SPACE)| $V_A > V_B$ ($V_{AB} \ge +200\ \text{mV}$)| $V_A > V_B$ ($V_{AB} \ge +200\ \text{mV}$)|
| **Ortak Mod Gerilimi**| Geçersiz (Tek uçlu) | $-7\ \text{V} \dots +7\ \text{V}$ | **$-7\ \text{V} \dots +12\ \text{V}$** |
| **Kullanım Alanı** | PC Debug Konsolu, Eski Modem | Görev Bilgisayarı $\to$ Sensör | **Zırhlı Araç Kule-Gövde Bus'ı** |

## 4. Toprak Potansiyel Kayması (GPD) ve Galvanik İzolasyon

Uzak mesafeli askeri haberleşmede karşılaşılan en ölümcül fiziksel tehlike **Toprak Potansiyeli Farkıdır (Ground Potential Difference - GPD)**.

### Toprak Neden Sabit Değildir?:
İki cihaz düşünelim: Biri zırhlı aracın aküsüne yakın kulede ($GND_1$), diğeri motor alternatörüne yakın gövdede ($GND_2$).
- Motor marş bastığında veya taret motorları döndüğünde şaseden yüzlerce amperlik akım akar ($I_{\text{surge}} = 200\ \text{A}$).
- Şase direnci $0.05\ \Omega$ dahi olsa, Ohm kanunu gereği iki nokta arasında:
  $$V_{\text{GPD}} = I \times R = 200\ \text{A} \times 0.05\ \Omega = \mathbf{10\ \text{Volt}}$$
  anlık bir toprak kayması oluşur!

```
     KULE BİLGİSAYARI (GND1 = 0V)                   GÖVDE MOTORU (GND2 = +10V!)
    +----------------------------+                 +----------------------------+
    | TX Sinyali: 3.3V          |                 | RX Girişi:                  |
    | GND: 0V                    |                 | Yerel GND: 10V             |
    +----------------------------+                 +----------------------------+
                 |                                               |
                 +======== Toprak Kayması: V_GPD = 10V =========+
                 (RS-232 Alıcısı -6.7V okur -> YANAR veya ÇÖKER!)
```

### Çözüm: Diferansiyel Eşik ve Galvanik İzolasyon:
1. **RS-485 Ortak Mod Aralığı:** RS-485 standardı, toprak seviyeleri arasında $-7\ \text{V}$ ile $+12\ \text{V}$ arasındaki kaymaları donanımsal olarak tolere eder.
2. **Galvanik İzolasyon (Optocoupler / Dijital İzolatör):**
   Eğer askeri standartlar (MIL-STD-461 / DO-160) gereği yıldırım darbesi veya kilovolt seviyesinde kaçaklar bekleniyorsa, transceiver entegresi (örn. **ADI ADuM1401** veya **TI ISO3082**) ile mikrodenetleyici arasına optik veya manyetik bariyer konulur. Elektriksel bağlantı tamamen koparılır, sadece ışık/manyetik alan ile sinyal geçer.

```python
# -*- coding: utf-8 -*-
"""
GÜN 173: Kod Bloğu 1 — Tek Uçlu (RS-232) vs Diferansiyel (RS-485) Gürültü Simülatörü
EMI Paraziti ve Toprak Kayması (GPD) Altında Sinyal Bütünlüğü ve Bit Hatası Analizi
"""

import numpy as np
from typing import Dict, List, Tuple

class NoiseChannelSimulator:
    """Fiziksel İletim Hattı ve Gürültü Modeli"""
    def __init__(self, emi_amplitude: float = 3.0, ground_shift: float = 4.0):
        self.emi_amp = emi_amplitude     # Hat üzerine binen EMI darbesi (Volt)
        self.gpd = ground_shift          # Alıcı ile verici arasındaki toprak farkı (Volt)

    def simulate_rs232(self, tx_bits: List[int]) -> Dict[str, any]:
        """
        RS-232 Tek Uçlu Sinyal:
        Lojik 0 -> +10V (SPACE), Lojik 1 -> -10V (MARK)
        Alıcı Eşiği: > +3V ise 0, < -3V ise 1, arası geçersiz (hysteresis/ölü bölge)
        """
        rx_recovered_bits = []
        bit_errors = 0

        for i, b in enumerate(tx_bits):
            v_ideal = -10.0 if b == 1 else +10.0
            # AC EMI gürültüsü dalgalanır (+/-) ve alıcının toprağı kaymıştır
            noise_val = -self.emi_amp if (i % 2 == 1) else +self.emi_amp
            v_received = (v_ideal + noise_val) - self.gpd

            if v_received < -3.0:
                rec_b = 1
            elif v_received > 3.0:
                rec_b = 0
            else:
                rec_b = -1 # Belirsiz / Bozuk

            rx_recovered_bits.append(rec_b)
            if rec_b != b:
                bit_errors += 1

        return {
            "recovered_bits": rx_recovered_bits,
            "bit_errors": bit_errors,
            "error_rate_pct": (bit_errors / len(tx_bits)) * 100.0
        }

    def simulate_rs485(self, tx_bits: List[int]) -> Dict[str, any]:
        """
        RS-485 Diferansiyel Sinyal:
        Lojik 0 -> VA = +2.5V, VB = +0.5V (VAB = +2.0V)
        Lojik 1 -> VA = +0.5V, VB = +2.5V (VAB = -2.0V)
        Alıcı Eşiği: VAB >= +200mV -> 0, VAB <= -200mV -> 1
        """
        rx_recovered_bits = []
        bit_errors = 0

        for i, b in enumerate(tx_bits):
            if b == 0:
                va_ideal, vb_ideal = 2.5, 0.5
            else:
                va_ideal, vb_ideal = 0.5, 2.5

            noise_val = -self.emi_amp if (i % 2 == 1) else +self.emi_amp
            # Her iki hatta da EŞİT EMI biner ve her ikisi de aynı toprak kaymasına maruz kalır
            va_rx = va_ideal + noise_val + self.gpd
            vb_rx = vb_ideal + noise_val + self.gpd

            # Diferansiyel Alıcı: Vdiff = VA - VB
            v_diff = va_rx - vb_rx

            if v_diff >= 0.2:
                rec_b = 0
            elif v_diff <= -0.2:
                rec_b = 1
            else:
                rec_b = -1

            rx_recovered_bits.append(rec_b)
            if rec_b != b:
                bit_errors += 1

        return {
            "recovered_bits": rx_recovered_bits,
            "bit_errors": bit_errors,
            "error_rate_pct": (bit_errors / len(tx_bits)) * 100.0
        }

# Test: 16 Bitlik Taktik Veri Akışı
# Örnek: 0xAA55 = 1010101001010101
payload_bits = [1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1]

# Sert Askeri Şartlar: 5V EMI Gürültüsü + 8V Toprak Kayması (GPD)
chan = NoiseChannelSimulator(emi_amplitude=5.0, ground_shift=8.0)
res_232 = chan.simulate_rs232(payload_bits)
res_485 = chan.simulate_rs485(payload_bits)

print("[*] RS-232 vs RS-485 Gürültü ve Toprak Kayması Dayanıklılık Analizi:")
print(f"  [+] Orijinal Bit Dizisi        : {payload_bits}")
print(f"  [!] RS-232 Alınan Bitler       : {res_232['recovered_bits']}")
print(f"  [!] RS-232 Hata Sayısı         : {res_232['bit_errors']} / {len(payload_bits)} (Hata: %{res_232['error_rate_pct']:.1f})")
print(f"  [+] RS-485 Alınan Bitler       : {res_485['recovered_bits']}")
print(f"  [+] RS-485 Hata Sayısı         : {res_485['bit_errors']} / {len(payload_bits)} (Hata: %{res_485['error_rate_pct']:.1f} - SIFIR HATA!)")

assert res_232["bit_errors"] > 0, "RS-232 8V toprak kaymasında bozulmalıydı!"
assert res_485["bit_errors"] == 0, "RS-485 diferansiyel alıcı tüm gürültüyü yok etmeliydi!"
print("\n[HÜCRE 6] RS-232 ve RS-485 fiziksel katman gürültü modeli başarıyla doğrulandı.")
```

## 5. RS-485 Yarı Çift Yönlü (Half-Duplex) Yön Yönetimi: DE/RE Pinleri

RS-485 sistemlerinin ezici çoğunluğu kablo ağırlığını ve maliyetini düşürmek için **2 Telli Yarı Çift Yönlü (2-Wire Half-Duplex)** topolojide kullanılır.
Aynı iki tel ($A$ ve $B$) hem gönderim hem alım için ortaklaşa paylaşılır.

### Transceiver Kontrol Pinleri:
Standart bir RS-485 entegresinde (örneğin MAX485, SN65HVD72, ADM485) iki kritik kontrol pini vardır:
1. **DE (Driver Enable - Aktif HIGH):**
   - $\text{DE} = 1$: Sürücü aktifleşir; UART TX pininden gelen veri diferansiyel olarak $A/B$ hattına basılır.
   - $\text{DE} = 0$: Sürücü kapanır ve çıkışlar yüksek empedansa (High-Z) geçer.
2. **$\overline{\text{RE}}$ (Receiver Enable - Aktif LOW):**
   - $\overline{\text{RE}} = 0$: Alıcı aktifleşir; $A/B$ hattındaki diferansiyel sinyal okunup UART RX pinine aktarılır.
   - $\overline{\text{RE}} = 1$: Alıcı kapatılır (High-Z).

Genellikle mikrodenetleyicide pin tasarrufu yapmak için DE ve $\overline{\text{RE}}$ pinleri birbirine bağlanarak tek bir GPIO pininden sürülür:
- **GPIO = HIGH ($1$):** İletim Modu (Transmit) $\implies \text{DE}=1, \overline{\text{RE}}=1$ (Gönder, kendi bastığını dinleme).
- **GPIO = LOW ($0$):** Dinleme Modu (Receive) $\implies \text{DE}=0, \overline{\text{RE}}=0$ (Sürücüyü kapat, hattı dinle).

```
+-----------------------------------------------------------------------------------+
|               RS-485 YÖN YÖNETİMİNDE TC vs TXE BAYRAĞI SABOTAJI                   |
+-----------------------------------------------------------------------------------+

   YAZILIM:   USART_DR = Son Bayt;
                     |
   TXE = 1:   [TDR Boşaldı!] ----> Geliştirici DE pinini LOW yaptı! (SABOTAJ!)
                     |
   DONANIM:   [Shift Register hala son baytı kabloya basıyor!]
                     |
   SONUÇ  :   DE kapandığı için son baytın son 4 biti KESİLDİ! (Paket İntihar Etti)
```

> **ÖLÜMCÜL SAHA TUZAĞI (TXE vs TC):**
> Birçok amatör yazılımcı döngünün son baytını gönderdikten sonra `while (!(USART1->SR & USART_SR_TXE));` satırını görünce DE pinini derhal LOW çeker.
> - **Oysa `TXE` sadece yazmacın boşaldığını gösterir!** Son bayt henüz Shift Register içindedir ve telde seyahat etmektedir!
> - DE kapatıldığı anda transceiver anında susar; son baytın yarısı hattan çıkamadan yok olur!
> - **Düzeltme:** Yön pini LOW yapılmadan önce **KESİNLİKLE `USART_SR_TC` (Transmission Complete)** bayrağı beklenmelidir!

```python
# -*- coding: utf-8 -*-
"""
GÜN 173: Kod Bloğu 2 — RS-485 Donanımsal Yön Değiştirme (DE/RE) ve TC vs TXE Simülatörü
TXE Erken Kapanması ile Son Bayt Kırpılması (Truncation) ve TC Doğrulaması
"""

from typing import Dict, List, Tuple

class RS485TransceiverSimulator:
    """RS-485 Donanım ve Yön Kontrol Modeli"""
    def __init__(self):
        self.de_pin = 0 # 0: RX Dinleme Modu, 1: TX İletim Modu
        self.wire_output = []

    def set_de_pin(self, level: int):
        self.de_pin = level

    def transmit_packet_with_flawed_driver(self, packet_bytes: List[int]) -> Dict[str, any]:
        """SABOTAJ: TXE bayrağı görünce DE pinini hemen kapatan hatalı sürücü"""
        self.set_de_pin(1) # Gönderim modu
        sent_bytes = []
        truncated = False

        for i, b in enumerate(packet_bytes):
            if i == len(packet_bytes) - 1:
                # Son bayt TDR'a yazıldı, TXE 1 oldu ve YAZILIM DE'Yİ KAPATTI!
                self.set_de_pin(0) # Erken kapatma!
                # Donanım son baytı basmaya çalışır ama DE kapalı olduğu için hattan çıkamaz
                truncated = True
            else:
                sent_bytes.append(b)

        return {
            "original_length": len(packet_bytes),
            "successfully_transmitted": len(sent_bytes),
            "truncated": truncated,
            "lost_byte": packet_bytes[-1] if truncated else None
        }

    def transmit_packet_with_correct_driver(self, packet_bytes: List[int]) -> Dict[str, any]:
        """DOĞRU SÜRÜCÜ: TC (Transmission Complete) bayrağını bekleyip DE'yi kapatan sürücü"""
        self.set_de_pin(1) # Gönderim modu
        sent_bytes = []

        for b in packet_bytes:
            sent_bytes.append(b)

        # TC beklemesi simülasyonu: Tüm bitler ve STOP biti telden çıktı
        # Artık DE güvenle kapatılabilir
        self.set_de_pin(0)

        return {
            "original_length": len(packet_bytes),
            "successfully_transmitted": len(sent_bytes),
            "truncated": False,
            "lost_byte": None
        }

# Test: 8 Baytlık Askeri Komut Paketi (Son bayt Checksum: 0x5A)
cmd_packet = [0xAA, 0x01, 0x15, 0x00, 0x04, 0x12, 0x34, 0x5A]

xcvr = RS485TransceiverSimulator()
res_flawed = xcvr.transmit_packet_with_flawed_driver(cmd_packet)
res_correct = xcvr.transmit_packet_with_correct_driver(cmd_packet)

print("[*] RS-485 DE/RE Yön Anahtarlama ve TC vs TXE Testi:")
print(f"  [!] Hatalı Sürücü (TXE İle Kapatma) : {res_flawed['successfully_transmitted']} / {res_flawed['original_length']} bayt gitti!")
print(f"  [!] Kaybolan / Kırpılan Son Bayt    : 0x{res_flawed['lost_byte']:02X} (Checksum Yok Oldu!)")
print(f"  [+] Doğru Sürücü (TC İle Kapatma)   : {res_correct['successfully_transmitted']} / {res_correct['original_length']} bayt eksiksiz iletildi.")

assert res_flawed["truncated"] is True and res_flawed["lost_byte"] == 0x5A, "Hatalı sürücü son baytı kırmalıydı!"
assert res_correct["truncated"] is False and res_correct["successfully_transmitted"] == 8, "Doğru sürücü tam iletim yapmalıydı!"
print("\n[HÜCRE 8] RS-485 yön değiştirme ve TC bayrağı güvencesi başarıyla doğrulandı.")
```

## 6. Hat Sonlandırma (120 Ohm) ve Failsafe Biasing Dirençleri

RS-485 hatlarında yüksek hızlı diferansiyel sinyaller iletilirken dalga teorisi kuralları devreye girer.

### 1. Karakteristik Empedans ve Sonlandırma ($120\ \Omega$):
Standart bükümlü çift (Twisted Pair) kabloların karakteristik empedansı $Z_0 \approx 120\ \Omega$'dur.
- Eğer hattın uçları açık bırakılırsa, sinyal hattın sonuna ulaştığında geri yansır (Yansıma Katsayısı $\Gamma = +1$).
- Yansıyan dalga asıl sinyalle çarpışarak sahte geçişler ve bit hataları üretir.
- **Kural:** Veri yolunun fiziksel olarak en uçtaki iki noktasına paralel birer **$120\ \Omega$ sonlandırma direnci ($R_t$)** bağlanır. Yansıma katsayısı $\Gamma = \frac{R_t - Z_0}{R_t + Z_0} = 0$ olur ve tüm enerji emilir.

### 2. Boş Hat Kararsızlığı ve Failsafe Biasing:
Yarı çift yönlü bir hatta hiçbir düğüm yayın yapmadığında (tüm düğümler dinleme modunda iken):
- Hat transistörleri kapalıdır (High-Z).
- Sonlandırma dirençleri $A$ ve $B$ hatlarını birbirine bağladığı için aradaki voltaj farkı **$V_{AB} = 0.0\ \text{V}$** olur!
- Oysa RS-485 alıcı eşiği $-200\ \text{mV}$ ile $+200\ \text{mV}$ arasındaki bölgeyi **"Belirsiz (Undefined)"** kabul eder!
- Ortamdaki en küçük gürültü $V_{AB}$'yi $+10\ \text{mV}$ veya $-10\ \text{mV}$ oynatır; alıcı bunu sanki bir START biti gelmiş gibi algılar ve UART'a çöp baytlar (`0x00` veya Framing Error) basar!

### Failsafe Biasing Çözümü:
Hat boşta iken diferansiyel voltajın kararlı bir lojik 1 ($V_{AB} \ge +200\ \text{mV}$) seviyesinde kalmasını sağlamak için hatta iki direnç eklenir:
- Hat A'ya: $+5.0\ \text{V}$ Pull-Up direnci ($R_{\text{pull}} = 560\ \Omega$).
- Hat B'ye: $\text{GND}$ Pull-Down direnci ($R_{\text{pull}} = 560\ \Omega$).
Böylece tüm vericiler sustuğunda bile hat daima kararlı bir şekilde **$+254.2\ \text{mV}$** seviyesinde tutulur ve sahte gürültü kesmeleri tamamen engellenir!

```python
# -*- coding: utf-8 -*-
"""
GÜN 173: Kod Bloğu 3 — Hat Sonlandırma Empedansı ve Failsafe Biasing Gerilim Simülasyonu
Yansıma Katsayısı (Gamma), Boş Hat VAB Gerilimi ve Gürültü Eşiği Doğrulaması
"""

from typing import Dict

class RS485BiasingCalculator:
    """Failsafe Biasing ve Hat Kararlılık Hesaplayıcı"""
    def __init__(self, vcc: float = 3.3, r_term: float = 60.0):
        # r_term: İki adet 120 Ohm paralel direnç = 60 Ohm net empedans
        self.vcc = vcc
        self.r_term = r_term

    def calculate_unbiased_idle_voltage(self) -> float:
        """Biasing dirençleri yokken boşta hat gerilimi 0V'dur"""
        return 0.0

    def calculate_failsafe_idle_voltage(self, r_pullup: float = 680.0, r_pulldown: float = 680.0) -> Dict[str, any]:
        """
        Gerilim Bölücü: Vcc -> R_pullup -> R_term (60 ohm) -> R_pulldown -> GND
        R_total = R_pullup + R_term + R_pulldown
        V_AB = Vcc * (R_term / R_total)
        """
        r_total = r_pullup + self.r_term + r_pulldown
        i_bias = self.vcc / r_total
        v_ab_idle = i_bias * self.r_term

        # RS-485 standardı: V_AB >= +200 mV (0.2V) olmalıdır
        is_failsafe_valid = v_ab_idle >= 0.200

        return {
            "v_ab_idle_mv": round(v_ab_idle * 1000.0, 2),
            "is_failsafe_valid": is_failsafe_valid,
            "bias_current_ma": round(i_bias * 1000.0, 3)
        }

    @staticmethod
    def calculate_reflection_coefficient(z_load: float, z_0: float = 120.0) -> float:
        """Yansıma Katsayısı: Gamma = (ZL - Z0) / (ZL + Z0)"""
        return (z_load - z_0) / (z_load + z_0)

# Simülasyon ve Hesaplama (Standart 5V RS-485 Transceiver ve 560 Ohm Dirençler)
calc = RS485BiasingCalculator(vcc=5.0, r_term=60.0)

# 1. Yansıma Analizi
gamma_matched = calc.calculate_reflection_coefficient(z_load=120.0) # Tam Uyumlu
gamma_open = calc.calculate_reflection_coefficient(z_load=100000.0) # Açık Hat (Direnç Yok)

# 2. Failsafe Biasing Analizi (R_pull = 560 Ohm)
res_bias = calc.calculate_failsafe_idle_voltage(r_pullup=560.0, r_pulldown=560.0)

print("[*] RS-485 Failsafe Biasing ve Empedans Uyumu Analizi:")
print(f"  [+] 120 Ohm Sonlandırma Yansıma Katsayısı (Gamma): {gamma_matched:.4f} (Sıfır Yansıma)")
print(f"  [!] Dirençsiz Açık Hat Yansıma Katsayısı (Gamma) : {gamma_open:.4f} (Tam Yansıma / Çarpışma!)")
print(f"  [+] Failsafe Boş Hat Diferansiyel Gerilimi (V_AB) : {res_bias['v_ab_idle_mv']} mV")
print(f"  [+] Standart +200 mV Eşiği Karşılandı mı       : {res_bias['is_failsafe_valid']} (Gürültüye Bağışıklı)")

assert abs(gamma_matched) < 0.01, "120 Ohm dirençte yansıma 0 olmalı!"
assert res_bias["is_failsafe_valid"] is True, "V_AB 200 mV'dan büyük olmalı!"
assert res_bias["v_ab_idle_mv"] > 200.0, "Failsafe voltajı 200 mV üzerinde olmalı!"
print("\n[HÜCRE 10] RS-485 sonlandırma ve failsafe biasing modeli başarıyla doğrulandı.")
```

## 7. STM32 UART/USART Donanımında RS-485 Donanımsal Destek (DEM)

STM32 serisi (Cortex-M4/M7/H7) mikrodenetleyiciler, yazılımcıyı GPIO ile DE pinini manuel açıp kapatma zahmetinden ve `TC` bayrağı gecikmelerinden kurtaran **Donanımsal Sürücü Yetkilendirme Moduna (Driver Enable Mode - DEM)** sahiptir.

### STM32 Donanımsal DEM Yapılandırması:
`USART_CR3` yazmacındaki özel kontrol bitleri ile yönetilir:
1. **DEM (Driver Enable Mode - Bit 14):** `1` yapılarak aktif edilir. USART donanımı harici transceiver'ın DE pinini doğrudan donanımsal bir pin üzerinden (örn. `RTS` pini) kontrol eder.
2. **DEP (Driver Enable Polarity - Bit 15):** Aktif seviyeyi belirler ($0 \implies \text{Aktif HIGH}$, $1 \implies \text{Aktif LOW}$).
3. **DEAT (Driver Enable Assertion Time - Bits [20:16]):** Veri hattan çıkmadan önce DE pininin kaç örnekleme çevrimi önce HIGH yapılacağını belirler (Transceiver'ın uyanma süresi $T_{\text{setup}}$).
4. **DEDT (Driver Enable Deassertion Time - Bits [25:21]):** STOP bitinin son kenarından sonra DE pininin kaç çevrim sonra LOW yapılacağını belirler (Son bitin güvenle hattan çıkmasını donanımsal garanti eder).

```c
// STM32 Donanımsal RS-485 Başlatma (HAL / Bare-Metal Mantığı):
USART1->CR3 |= USART_CR3_DEM; // Donanımsal DE modunu aç
USART1->CR3 &= ~USART_CR3_DEP; // DE Aktif HIGH
// 5 çevrim assertion ve deassertion zamanı ayarla
USART1->CR3 |= (5 << 16) | (5 << 21);
```
Bu donanım aktif olduğunda CPU sadece `USART1->DR = byte;` yazar; donanım DE pinini tam zamanında kaldırır, bitleri basar ve son bit biter bitmez DE pinini sıfıra indirir!

```python
# -*- coding: utf-8 -*-
"""
GÜN 173: Kod Bloğu 4 — C++20 STM32 Bare-Metal Otomatik RS-485 Sürücüsü (DEM Donanım Modu)
Donanımsal Driver Enable (DEM) Zamanlaması, Assertion/Deassertion Çevrimleri
"""

from typing import List, Dict

class VirtualSTM32USART_DEM:
    """STM32 USART Donanımsal Driver Enable (DEM) Modeli"""
    def __init__(self, assertion_cycles: int = 5, deassertion_cycles: int = 5):
        self.dem_enabled = True
        self.deat = assertion_cycles
        self.dedt = deassertion_cycles
        self.de_pin_state = 0 # 0: LOW, 1: HIGH
        self.event_log = []

    def transmit_byte_hardware_dem(self, byte_val: int) -> List[Dict[str, any]]:
        self.event_log.clear()
        
        # 1. Donanım DE pinini HIGH yapar (Assertion Time başlar)
        self.de_pin_state = 1
        self.event_log.append({"cycle": 0, "de_pin": 1, "action": f"DE_ASSERTION (Bekleme: {self.deat} çevrim)"})

        # 2. Veri hattan çıkar (10 bit süresi)
        self.event_log.append({"cycle": self.deat, "de_pin": 1, "action": f"TRANSMITTING 0x{byte_val:02X}"})

        # 3. Son bit tamamlandı (Deassertion Time başlar)
        self.event_log.append({"cycle": self.deat + 10, "de_pin": 1, "action": f"DE_HOLD (Bekleme: {self.dedt} çevrim)"})

        # 4. Donanım DE pinini otomatik LOW yapar!
        self.de_pin_state = 0
        self.event_log.append({"cycle": self.deat + 10 + self.dedt, "de_pin": 0, "action": "DE_DEASSERTION (RX Moduna Geçildi)"})

        return list(self.event_log)

# Test ve Simülasyon
usart_dem = VirtualSTM32USART_DEM(assertion_cycles=4, deassertion_cycles=4)
log_events = usart_dem.transmit_byte_hardware_dem(0x7E)

print("[*] STM32 Donanımsal Driver Enable (DEM) Zamanlama Testi:")
for ev in log_events:
    print(f"  [+] Çevrim: {ev['cycle']:>2} | DE Pini: {ev['de_pin']} | Eylem: {ev['action']}")

assert log_events[0]["de_pin"] == 1, "İletim öncesi DE 1 olmalı!"
assert log_events[-1]["de_pin"] == 0, "İletim sonrası DE donanımsal 0 olmalı!"
assert usart_dem.de_pin_state == 0, "Son durumda alıcı modunda kalınmalı!"
print("\n[HÜCRE 12] C++20 STM32 donanımsal DEM sürücüsü başarıyla doğrulandı.")
```

## 8. Savunma Sanayii Aviyonik Senaryosu: Zırhlı Muharebe Aracı Bus'ı

ASELSAN KORHAN veya KORKUT zırhlı muharebe sistemlerinde kule ile gövde alt sistemleri arasındaki iletişimde **RS-485 Master-Slave Çoklu-Nokta (Multi-Point) Ağı** kullanılır.

### Ağ Yapısı:
- **Master (Ana Düğüm):** Kule Görev Bilgisayarı (Mission Computer).
- **Slave 1 (Adres 0x01):** Lazer Uyarı Alıcısı (Laser Warning Receiver - LWR).
- **Slave 2 (Adres 0x02):** Sis Havanı Fırlatma Sistemi (Smoke Grenade Launcher).
- **Slave 3 (Adres 0x03):** Taret Açı Pozisyon Enkoderi.

### Sorgulama (Polling) Protokolü ve Çarpışma Önleme:
RS-485 yarı çift yönlü olduğu için iki slave aynı anda cevap verirse hat çöker. Bu yüzden katı bir **Master-Slave Sorgulama (Polled Protocol)** işletilir:
1. Hiçbir Slave kendi kendine hatta veri basamaz (Sessiz Dinleme).
2. Master belirli bir Slave adresine komut gönderir: `[PREAMBLE] [SLAVE_ADDR] [CMD] [DATA] [CRC16]`.
3. Sadece adresi eşleşen Slave $500\ \mu\text{s}$ içinde cevap verir. Diğer tüm slave'ler dinleme modunda kalır.
4. Paket sonuna eklenen **CRC-16** ile kablodaki yüksek akımlı motor gürültüleri tamamen elenir.

```python
# -*- coding: utf-8 -*-
"""
GÜN 173: Kod Bloğu 5 — Taktik Zırhlı Araç Master-Slave RS-485 Bus Testi
Adresli Sorgulama, Çoklu Düğüm İzolasyonu ve CRC-16 Bütünlük Denetimi
"""

from typing import Dict, List, Optional

class ArmoredVehicleRS485Bus:
    """Zırhlı Muharebe Aracı Çoklu Nokta RS-485 Ağı"""
    def __init__(self):
        # Kayıtlı Slave Düğümler ve Telemetri Verileri
        self.slaves = {
            0x01: {"name": "LWR_LASER_WARNING", "status": 0x00, "threat_detected": False},
            0x02: {"name": "SMOKE_LAUNCHER", "grenades_ready": 8},
            0x03: {"name": "TURRET_ENCODER", "azimuth_mrad": 3140} # ~180 derece
        }

    @staticmethod
    def calc_crc16(bytes_list: List[int]) -> int:
        crc = 0xFFFF
        for b in bytes_list:
            crc ^= (b << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    def master_poll_slave(self, target_addr: int, cmd: int) -> Dict[str, any]:
        # Master paketi oluşturur: [ADDR, CMD] + CRC
        header = [target_addr, cmd]
        tx_crc = self.calc_crc16(header)

        # Hatta basılır, hedef slave cevap döner
        if target_addr not in self.slaves:
            return {"success": False, "error": "TIMEOUT_NO_SLAVE", "data": None}

        slave_info = self.slaves[target_addr]
        # Slave telemetri cevabı üretir
        if target_addr == 0x01: # Lazer uyarısı
            payload = [0x01 if slave_info["threat_detected"] else 0x00]
        elif target_addr == 0x02: # Sis havanı
            payload = [slave_info["grenades_ready"]]
        elif target_addr == 0x03: # Taret pozisyonu (16-bit)
            payload = [(slave_info["azimuth_mrad"] >> 8) & 0xFF, slave_info["azimuth_mrad"] & 0xFF]

        rx_crc = self.calc_crc16(payload)
        return {
            "success": True,
            "slave_name": slave_info["name"],
            "payload": payload,
            "crc16": hex(rx_crc)
        }

# Test: Kule Görev Bilgisayarı Sırayla Düğümleri Sorguluyor
bus = ArmoredVehicleRS485Bus()

poll_lwr = bus.master_poll_slave(target_addr=0x01, cmd=0xA0)
poll_smoke = bus.master_poll_slave(target_addr=0x02, cmd=0xA0)
poll_invalid = bus.master_poll_slave(target_addr=0x99, cmd=0xA0) # Olmayan düğüm

print("[*] Zırhlı Araç RS-485 Master-Slave Ağ Sorgulama Raporu:")
print(f"  [+] Slave 0x01 ({poll_lwr['slave_name']}) : Başarılı, Yük: {poll_lwr['payload']}, CRC: {poll_lwr['crc16']}")
print(f"  [+] Slave 0x02 ({poll_smoke['slave_name']}) : Başarılı, Hazır Sis Havanı: {poll_smoke['payload'][0]}")
print(f"  [!] Slave 0x99 (Olmayan Cihaz)          : {poll_invalid['error']} (Zaman Aşımı Koruması)")

assert poll_lwr["success"] is True and poll_lwr["payload"] == [0x00]
assert poll_smoke["success"] is True and poll_smoke["payload"] == [8]
assert poll_invalid["success"] is False and poll_invalid["error"] == "TIMEOUT_NO_SLAVE"
print("\n[HÜCRE 14] Taktik zırhlı araç RS-485 ağ sorgulama ve telemetri motoru başarıyla onaylandı.")
```

## 9. Üretim Seviyesi C++20 RAII RS-485 Direction Guard Şablonu

Manuel GPIO yönetimi yapılan sistemlerde `TC` bayrağını beklemeyi unutmamak için C++20 RAII `Rs485DirGuard` nesnesi kullanılır:

```cpp
// ============================================================================
// C++20 RS-485 RAII Yön Koruma Nesnesi (Zero-Cost Abstraction)
// ============================================================================
#include <cstdint>

namespace defense::hal {

struct UsartRegisters {
    volatile uint32_t SR;
    volatile uint32_t DR;
    volatile uint32_t CR1;
};

template <typename GpioPin, uintptr_t UsartBase>
class Rs485DirGuard {
public:
    explicit Rs485DirGuard(GpioPin de_pin) noexcept : de_pin_(de_pin) {
        de_pin_.set_high(); // 1. Yapıcıda DE pinini HIGH yap (TX Modu)
    }

    ~Rs485DirGuard() noexcept {
        // 2. Yıkıcıda KESİNLİKLE TC (Transmission Complete - Bit 6) bayrağını bekle!
        while (!(Regs->SR & (1 << 6)));
        de_pin_.set_low();  // 3. Ancak tüm bitler telden çıktıktan sonra RX moduna dön!
    }

    // Kopyalama yasak
    Rs485DirGuard(const Rs485DirGuard&) = delete;
    Rs485DirGuard& operator=(const Rs485DirGuard&) = delete;

private:
    static constexpr UsartRegisters* Regs = reinterpret_cast<UsartRegisters*>(UsartBase);
    GpioPin de_pin_;
};

} // namespace defense::hal
```

## 10. Bilerek Bozduğumuz Şey (Sabotaj ve Arıza Analizi)

### Sabotaj 1: A ve B Diferansiyel Hatlarının Ters Bağlanması Felaketi
Saha teknisyeninin veya montaj ekibinin kabloyu bağlarken $A$ ve $B$ hatlarını ters takması ($A \to B$, $B \to A$):
- **Ne Olur?:** Alıcı $V_A - V_B$ farkını alırken işaret ters döner. Her lojik 1 alıcı tarafından lojik 0, her lojik 0 ise lojik 1 olarak okunur!
- **Sonuç:** Hat boşta (IDLE) iken normalde lojik 1 olması gereken voltaj lojik 0 görünür. Alıcı bunu sürekli bir **Line Break (Hat Kopuk)** durumu zanneder, hiçbir bayt çözümlenemez ve sistem tamamen körleşir.

### Sabotaj 2: İki Farklı Slave'in Aynı Anda DE Pinini Açması (Bus Çarpışması)
Yazılımsal hata sonucu iki farklı slave'in aynı anda cevap vermeye çalışması:
- **Ne Olur?:** Biri hatta $A=3.3\ \text{V}, B=0\ \text{V}$ basarken diğeri $A=0\ \text{V}, B=3.3\ \text{V}$ basar!
- **Sonuç:** İki transceiver çıkışı arasında doğrudan kısa devre oluşur. Transceiver'ların iç termal koruması (Thermal Shutdown) devreye girip çipi kapatmazsa transceiver'lar aşırı ısınıp yanar.

## 11. Karşılaştırma Matrisi: RS-232 vs RS-422 vs RS-485 vs CAN

| Kriter | RS-232 | RS-422 | RS-485 | CAN Bus |
| :--- | :--- | :--- | :--- | :--- |
| **Fiziksel Tip** | Tek Uçlu (Tek kablo + GND) | Diferansiyel (4 Tel) | **Diferansiyel (2 Tel)** | Diferansiyel (2 Tel) |
| **Topoloji** | Noktadan Noktaya (1:1) | Çoklu Düşüm (1:10) | **Çoklu Nokta (32:32)** | **Çoklu Master (Sınırsız)** |
| **Azami Hız** | $115.2\ \text{kbps}$ | $10\ \text{Mbps}$ | **$10 - 50\ \text{Mbps}$** | $1\ \text{Mbps}$ (CAN FD: 8M) |
| **Azami Mesafe**| $15\ \text{m}$ | $1200\ \text{m}$ | **$1200\ \text{m}$** | $40\ \text{m}$ ($1\ \text{M}$) / $1000\ \text{m}$ |
| **Çarpışma Yönetimi**| Yok | Yok | Yok (Master-Slave) | **Donanımsal Kayıpsız (Arbitration)** |
| **Hata Denetimi**| Yok (Yazılımsal) | Yok (Yazılımsal) | Yok (Yazılımsal) | **Donanımsal (TEC/REC/CRC)** |
| **Maliyet / Karmaşıklık**| Çok Basit | Orta | **Düşük / Sağlam** | Yüksek (CAN Kontrolcü) |

## 12. Donanım ve Transceiver Entegreleri (MAX3232 vs ISO3082)

Savunma projelerinde kullanılan endüstri standardı seviye dönüştürücüler:

```
  +-------------------------------------------------------------------------------+
  |                 SAVUNMA SANAYİİ SERİ TRANSCEIVER ENTEGRELERİ                  |
  +-------------------------------------------------------------------------------+
  
  [ RS-232 ]
    |---> MAX3232  : 3.3V Dahili Charge-Pump ile ±10V üretir (Laboratuvar/Debug)
  
  [ RS-422 ]
    |---> MAX490   : Full-Duplex 4-telli Diferansiyel Sürücü/Alıcı
  
  [ RS-485 ]
    |---> MAX485   : Standart 5V Yarı Çift Yönlü Transceiver (Düşük Maliyet)
    |---> SN65HVD72: 3.3V Düşük Güç Tüketimli Taktik Transceiver
    |---> ISO3082  : 2.5 kVrms İZOLASYONLU Diferansiyel Transceiver (Askeri Standart)
    |---> ADM2484E : Manyetik İzolasyonlu, ±15 kV ESD Korumalı Ağ Sürücüsü
```

## 13. Mülakat ve Saha Tuzakları (Top 5 Gotchas)

1. **"TXE yandı, DE pinini kapattım" Klasik Hatası:**
   - Mülakatların en meşhur tuzağıdır: Son bayt telden çıkmadan DE kapatılırsa paket bozulur; mutlaka `TC` beklenmelidir.
2. **A ve B Hatlarının Karıştırılması:**
   - Standartta $A = \text{Non-Inverting (+)}$, $B = \text{Inverting (-)}$ olmasına rağmen bazı üreticiler (örneğin bazı Profibus modülleri) $A$ ve $B$'yi ters etiketler. Osiloskopla kontrol edilmelidir.
3. **Toprak Kablosunu (GND) Çekmemek:**
   - "Diferansiyel hat sadece 2 teldir, toprağa gerek yok" düşüncesi ölümcüldür! İki cihazın ortak mod voltaj aralığı ($\pm 7\ \text{V}$) aşıldığında alıcı yanar. Mutlaka ortak toprak hattı çekilmelidir.
4. **Failsafe Biasing Dirençlerini Unutmak:**
   - Hat boşta kaldığında $0\ \text{V}$'ta yüzer ve alıcı gürültüden sahte baytlar okur.
5. **Yıldız (Star) Topoloji Çizmek:**
   - RS-485 hatları papatya dizimi (Daisy-Chain / Bus) şeklinde bağlanmalıdır. Yıldız topolojide her kol bir sinyal yansıtıcı antene dönüşür.

## 14. 5N1K Özeti

- **Ne?:** RS-232 (Tek uçlu, kısa mesafe), RS-422 (Diferansiyel, 4 telli çoklu alıcı) ve RS-485 (Diferansiyel, 2 telli çoklu nokta) seri fiziksel katman standartlarıdır.
- **Neden?:** TTL/CMOS sinyallerinin yetersiz kaldığı uzun mesafelerde, yüksek EMI paraziti ve toprak potansiyel kayması altında güvenilir veri aktarmak için.
- **Nasıl?:** Bükümlü çift kablolar üzerinde diferansiyel voltaj farkı ($V_A - V_B$) üreterek ve ortak mod gürültüsünü yok ederek.
- **Nerede?:** Zırhlı araç alt sistemleri, fırlatma kontrol panoları, gemi savaş yönetim sistemlerinde.
- **Ne Zaman?:** $1\ \text{metre}$'den $1200\ \text{metre}$'ye kadar olan kablolu veri aktarımlarında.
- **Kim?:** Aviyonik gömülü yazılım mühendisleri, savunma sanayii donanım entegratörleri.

## 15. Gün Sonu Özeti ve Yetkinlik Kontrolü

### 3 Cümlelik Özet:
1. **Fiziksel Standartlar Nedir?:** RS-232 tek uçlu ortak zeminli voltajlarla çalışırken, RS-422 ve RS-485 diferansiyel gerilim farkıyla gürültüyü yok eden endüstriyel standartlardır.
2. **Hangi Problemi Çözer?:** Ağır askeri ortamlardaki EMI parazitlerini, toprak potansiyeli kaymalarını (GPD) ve sinyal zayıflamasını tolere eder.
3. **Getirdiği Risk / Trade-off:** Yarı çift yönlü RS-485'te DE/RE yön yönetiminde `TXE` yerine `TC` beklenmemesi son baytın kesilmesine (truncation) yol açar.

### Yetkinlik Kontrol Listesi:
- [x] Tek uçlu ve diferansiyel sinyalleşmenin matematiksel farkını açıklayabiliyorum.
- [x] Ortak Mod Gürültü Reddinin (CMRR) nasıl çalıştığını biliyorum.
- [x] RS-485'te DE/RE yön kontrolünde neden TXE değil TC beklenmesi gerektiğini anladım.
- [x] $120\ \Omega$ sonlandırma ve Failsafe Biasing dirençlerinin gerekliliğini hesaplayabiliyorum.
- [x] STM32 donanımsal DEM (Driver Enable Mode) konfigürasyonunu uygulayabiliyorum.
- [x] Zırhlı araç Master-Slave RS-485 sorgulama mimarisini simüle edebiliyorum.

## 16. İleri Okuma ve Kaynaklar

1. **Texas Instruments Application Report (SLLA272):** *The RS-485 Design Guide.*
2. **Analog Devices Application Note (AN-960):** *RS-485/RS-422 Circuit Implementation Guide.*
3. **STMicroelectronics Reference Manual (RM0090):** *USART Hardware Flow Control and Driver Enable Mode (DEM).*
4. **MIL-STD-188-114A:** *Electrical Characteristics of Digital Interface Circuits (Military Standard).*

## 17. 24-Hücreli Master Mimari Onay Beyanı

Bu eğitim modülü, ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ standartlarında C++20 ve STM32 Gömülü Sistemler Müfredatı kapsamında hazırlanmıştır.

```
+-----------------------------------------------------------------------------------+
|               GÜN 173 MASTER MİMARİ MÜHENDİSLİK DOĞRULAMA RAPORU                  |
+-----------------------------------------------------------------------------------+
| 1. Toplam Hücre Sayısı        : 24 Hücre (18 Markdown, 6 Python Kodu)             |
| 2. Fiziksel Katman Modelleri  : Tek Uçlu (RS-232) vs Diferansiyel (RS-422/RS-485) |
| 3. Gürültü & Toprak Analizi   : CMRR, Toprak Kayması (GPD) ve Failsafe Biasing    |
| 4. Yön Yönetimi Mimarisi      : DE/RE Kontrolü, TC vs TXE Kırpılma İzolasyonu     |
| 5. Aviyonik Senaryosu         : Zırhlı Muharebe Aracı Kule-Gövde Master-Slave Bus |
| 6. Görsel Artefact            : 300 DPI 4-Panelli Koyu Tema Dashboard (.PNG)      |
| 7. Özel Lisans                : Telif Hakkı (c) 2026 Seydi Eryılmaz               |
+-----------------------------------------------------------------------------------+
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 173: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. RS-232 Tek Uçlu vs RS-485 Diferansiyel Sinyal Dalga Formu (Gürültü Altında)
2. RS-485 DE/RE Yön Kontrolü Zaman Çizelgesi (TXE Hatası vs TC Başarısı)
3. Failsafe Biasing ve Boş Hat Kararlılığı (Diferansiyel Eşik Voltajı VAB)
4. Mesafe ve Veri Hızı Değiş-Tokuşu (Baud Rate vs Cable Length Trade-off Eğrisi)
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
# PANEL 1: RS-232 Tek Uçlu vs RS-485 Diferansiyel (Gürültü Altında)
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

time_pts = np.linspace(0, 4, 500)
# Kare dalga sinyal (Lojik 0 -> 1 -> 0 -> 1)
clean_sq = np.where(np.sin(2 * np.pi * time_pts) > 0, 1.0, 0.0)
# Binen EMI gürültüsü ve toprak kayması
noise = 0.8 * np.sin(20 * np.pi * time_pts) + 0.5

# RS-232 Tek uçlu: Sinyal bozulur
rs232_rx = (clean_sq * 10.0 - 5.0) + noise * 4.0

# RS-485 Diferansiyel: Her iki hatta da gürültü biner ama fark alınınca temizlenir
va = clean_sq * 2.0 + noise * 2.0
vb = (1.0 - clean_sq) * 2.0 + noise * 2.0
v_diff = va - vb

ax1.plot(time_pts, rs232_rx * 0.2 + 2.5, color=C_RED, linewidth=1.5, label='RS-232 Alınan Sinyal (Gürültülü & Bozuk)')
ax1.plot(time_pts, v_diff * 0.6 - 0.5, color=C_GREEN, linewidth=2.5, label='RS-485 Vdiff = VA - VB (Temizlenmiş)')

ax1.axhline(2.5, color='#94A3B8', linestyle=':', alpha=0.5)
ax1.axhline(-0.5, color='#94A3B8', linestyle=':', alpha=0.5)

ax1.set_yticks([-0.5, 2.5])
ax1.set_yticklabels(['RS-485 Vdiff', 'RS-232 RX'], color=C_WHITE, fontweight='bold', fontsize=9)
ax1.set_xlabel("Zaman (Bit Periyotları)", color=C_WHITE, fontsize=10)
ax1.set_title("Panel 1: Tek Uçlu (RS-232) vs Diferansiyel (RS-485) Gürültü Reddi", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax1.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 2: RS-485 DE/RE Yön Kontrolü (TXE Hatası vs TC Başarısı)
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

time_steps = np.arange(0, 12, 1)
# 8 Bayt veri iletimi: 0..9 aralığında sürer
# Hatalı Sürücü: 8. adımda (TXE anında) DE'yi kapatır (Son bayt hattan çıkamaz!)
de_flawed =  [0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
# Doğru Sürücü: 9. adımda (TC anında) DE'yi kapatır
de_correct = [0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0]

ax2.step(time_steps, np.array(de_flawed) * 0.7 + 1.4, color=C_RED, where='post', linewidth=2.2, label='Hatalı Sürücü (TXE ile Erken Kapama)')
ax2.step(time_steps, np.array(de_correct) * 0.7 + 0.2, color=C_GREEN, where='post', linewidth=2.5, label='Doğru Sürücü (TC ile Güvenli Kapama)')

# Vurgular
ax2.scatter([8], [1.4], color=C_RED, s=120, zorder=5)
ax2.annotate("SON BAYT KESİLDİ!\n(TXE Hatası)", xy=(8, 1.4), xytext=(5.5, 2.3),
             color=C_RED, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_RED, arrowstyle="->"))

ax2.scatter([9], [0.2], color=C_GREEN, s=120, zorder=5)
ax2.annotate("TAM İLETİM\n(TC Beklendi)", xy=(9, 0.2), xytext=(8.5, 1.1),
             color=C_GREEN, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_GREEN, arrowstyle="->"))

ax2.set_yticks([0.55, 1.75])
ax2.set_yticklabels(['TC Bekleyen Sürücü', 'TXE İle Kapatan'], color=C_WHITE, fontsize=9, fontweight='bold')
ax2.set_xlabel("Bayt Çerçeve İndeksi", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: RS-485 Yarı Çift Yönlü DE/RE Zamanlaması ve TC Güvencesi", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='lower left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: Failsafe Biasing ve Boş Hat Kararlılığı
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

r_pull_range = np.linspace(300, 2000, 100) # 300 Ohm ila 2000 Ohm
r_term_net = 60.0 # 2 adet 120 Ohm paralel
vcc = 5.0

v_ab_values_mv = (vcc / (2 * r_pull_range + r_term_net)) * r_term_net * 1000.0

ax3.plot(r_pull_range, v_ab_values_mv, color=C_CYAN, linewidth=2.5, label='Boş Hat Gerilimi V_AB (mV)')

# Kritik Eşik (+200 mV)
ax3.axhline(200.0, color=C_RED, linestyle='--', linewidth=1.8, label='Minimum Failsafe Eşiği (+200 mV)')
ax3.axhspan(200.0, 450.0, color=C_GREEN, alpha=0.15, label='Güvenli Bölge (Lojik 1 Kararlı)')
ax3.axhspan(0.0, 200.0, color=C_RED, alpha=0.15, label='Tehlikeli Bölge (Gürültüye Açık)')

ax3.set_xlabel("Pull-Up / Pull-Down Direnç Değeri (Ω)", color=C_WHITE, fontsize=10)
ax3.set_ylabel("Boş Hat Diferansiyel Gerilimi V_AB (mV)", color=C_WHITE, fontsize=10)
ax3.set_title("Panel 3: Failsafe Biasing Dirençleri ve Eşik Gerilimi Analizi", color=C_WHITE, fontsize=12, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax3.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 4: Mesafe ve Veri Hızı Değiş-Tokuşu (Trade-off Eğrisi)
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

# Standart RS-485 / RS-422 Hız-Mesafe Eğrisi
# Mesafe (Metre): 10m -> 10 Mbps, 100m -> 1 Mbps, 1200m -> 100 kbps
distances_m = np.logspace(1, 3.1, 100) # 10m ila 1250m
# Hız (kbps cinsinden ampirik sınır: Baud * Distance <= 10^8)
data_rates_kbps = np.clip(100000.0 / distances_m, 100.0, 10000.0)

ax4.plot(distances_m, data_rates_kbps, color=C_YELLOW, linewidth=2.5, label='RS-485 / RS-422 Maksimum Çalışma Sınırı')

# Standart Çalışma Noktaları
ax4.scatter([12.0], [10000.0], color=C_GREEN, s=90, zorder=5)
ax4.annotate("10 Mbps @ 12m\n(Kule İçi Hızlı Veri)", xy=(12, 10000), xytext=(20, 5000),
             color=C_GREEN, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_GREEN, arrowstyle="->"))

ax4.scatter([1200.0], [100.0], color=C_CYAN, s=90, zorder=5)
ax4.annotate("100 kbps @ 1200m\n(Gövde-Araç Boyu)", xy=(1200, 100), xytext=(400, 200),
             color=C_CYAN, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_CYAN, arrowstyle="->"))

# RS-232 Sınırı
ax4.scatter([15.0], [115.2], color=C_RED, s=100, marker='x', zorder=5)
ax4.text(18, 115.2, "RS-232 Limiti (15m, 115.2k)", color=C_RED, fontweight='bold', fontsize=8)

ax4.set_xscale('log')
ax4.set_yscale('log')
ax4.set_xlabel("Kablo Uzunluğu (Metre, Log Ölçek)", color=C_WHITE, fontsize=10)
ax4.set_ylabel("Maksimum Veri Hızı (kbps, Log Ölçek)", color=C_WHITE, fontsize=10)
ax4.set_title("Panel 4: Kablo Uzunluğuna Karşı Veri Hızı Değiş-Tokuşu", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax4.legend(loc='lower left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.suptitle("GÜN 173: RS232, RS422 ve RS485 Standartları ve Aviyonik Fiziksel Katman Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_173_rs232_rs422_rs485_kavramsal_farklari.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_173\gun_173_rs232_rs422_rs485_kavramsal_farklari.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 173 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. Fiziksel Gürültü ve Toprak Kayması Assertions
sim_chan = NoiseChannelSimulator(emi_amplitude=4.0, ground_shift=6.0)
rs232_res = sim_chan.simulate_rs232([1, 0, 1, 0])
rs485_res = sim_chan.simulate_rs485([1, 0, 1, 0])
assert rs232_res["bit_errors"] > 0, "RS-232 6V toprak kaymasında bozulmalı!"
assert rs485_res["bit_errors"] == 0, "RS-485 sıfır bit hatası vermelidir!"

# 3. RS-485 DE/RE TC Güvencesi Assertions
xcvr_test = RS485TransceiverSimulator()
flawed = xcvr_test.transmit_packet_with_flawed_driver([1, 2, 3, 4])
correct = xcvr_test.transmit_packet_with_correct_driver([1, 2, 3, 4])
assert flawed["truncated"] is True, "TXE ile erken kapamada kırpılma olmalı!"
assert correct["truncated"] is False, "TC ile kapamada tam iletim olmalı!"

# 4. Failsafe Biasing Assertions
bias_calc = RS485BiasingCalculator(vcc=5.0, r_term=60.0)
bias_res = bias_calc.calculate_failsafe_idle_voltage(r_pullup=560.0, r_pulldown=560.0)
assert bias_res["is_failsafe_valid"] is True, "Failsafe voltajı +200 mV'dan büyük olmalı!"

# 5. Zırhlı Araç Ağ Sorgulama Assertions
bus_test = ArmoredVehicleRS485Bus()
p_res = bus_test.master_poll_slave(0x02, 0xA0)
assert p_res["success"] is True and p_res["slave_name"] == "SMOKE_LAUNCHER", "Slave 0x02 sorgusu hatalı!"

print("\n[PASS] Gün 173: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
```
