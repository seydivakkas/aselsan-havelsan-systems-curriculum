# GÜN 170: SPI Clock, Chip Select ve Full-Duplex — Senkron İletim ve CPOL/CPHA Mimarisi

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz.
```

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
![C++20](https://img.shields.io/badge/Standard-C%2B%2B20-blue.svg?style=flat-square)
![STM32](https://img.shields.io/badge/Hardware-STM32%20SPI%20Peripheral-orange.svg?style=flat-square)
![Bus Protocol](https://img.shields.io/badge/Protocol-SPI%20Full--Duplex-green.svg?style=flat-square)
![Defense Grade](https://img.shields.io/badge/Domain-Tactical%20IMU%20%2F%20Avionics-red.svg?style=flat-square)

---

## 1. Zihinsel Model ve Mimari Büyük Resim (SPI Nedir? Neden Senkron?)

Asenkron protokollerde (UART) ortak bir saat hattı olmadığı için start/stop bitleri, oversampling ve baud hızı tolerans kısıtları vardı. Bu kısıtlar hızı pratikte $1 - 2\ \text{Mbps}$ seviyesinde sınırlar.

Savunma sanayiinde yüksek bant genişliği gerektiren kritik bileşenler (örneğin ROKETSAN güdüm kiti IMU jiroskopları, ASELSAN radar sayısal sinyal işlemcileri, yüksek hızlı Flash bellekler ve DAC/ADC entegreleri) saniyede milyonlarca örnek aktarmak zorundadır. Burada devreye **SPI (Serial Peripheral Interface)** girer.

### SPI'ın Temel Mimari Farkı: Senkron İletim
SPI, Motorola tarafından geliştirilmiş, **Master-Slave (Ana-Bağımlı)** mimarisine dayanan **senkron (Synchronous)** ve **çift yönlü (Full-Duplex)** bir seri veri yoludur.
- **Paylaşımlı Saat Hattı (SCK):** Master donanımı bağımsız bir fiziksel hat üzerinden saat sinyali üretir.
- **Start / Stop Biti YOKTUR:** Alıcı, bitin ne zaman başladığını tahmin etmek için oversampling yapmaz; saatin kenarını (Edge) doğrudan donanımsal tetikleyici olarak kullanır.
- **Devasa Hız Avantajı:** Saat kayması (Baud Drift) riski sıfırlandığı için hızlar $10\ \text{MHz}$, $42\ \text{MHz}$ ve hatta STM32H7 serisinde **$100\ \text{MHz}$** seviyesine kadar çıkabilir! (UART'a göre 50 - 500 kat daha hızlı).

```
   [ MASTER (STM32 MCU) ]                               [ SLAVE (IMU Sensör) ]
  +----------------------+                             +----------------------+
  |         SCK (Clock)  |---------------------------->| SCK                  |
  |         MOSI (Data)  |---------------------------->| MOSI (SDI)           |
  |         MISO (Data)  |<----------------------------| MISO (SDO)           |
  |         CS (GPIO)    |---------------------------->| CS (Aktif LOW)       |
  |         GND          |-----------------------------| GND                  |
  +----------------------+                             +----------------------+
```

## 2. SPI 4-Telli Donanım Topolojisi ve Dairesel Kaydırma Yazmacı

SPI donanımının kalbinde iki adet 8-bit (veya 16-bit) **Kaydırma Yazmacı (Shift Register)** bulunur. Biri Master'da, diğeri Slave'dedir. Bu iki yazmaç MOSI ve MISO hatları üzerinden birbirine bağlanarak dev bir **Dairesel Halka (Circular Ring)** oluşturur!

```
+-----------------------------------------------------------------------------------+
|               SPI FULL-DUPLEX DAİRESEL KAYDIRMA YAZMACI (SHIFT REGISTER)          |
+-----------------------------------------------------------------------------------+

     [ MASTER SHIFT REGISTER ]                    [ SLAVE SHIFT REGISTER ]
    +---+---+---+---+---+---+---+---+            +---+---+---+---+---+---+---+---+
    | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |            | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
    +---+---+---+---+---+---+---+---+            +---+---+---+---+---+---+---+---+
      |                           ^                |                           ^
      |                           |     MOSI       |                           |
      +------ MOSI Hattı ---------|--------------->+                           |
                                  |                                            |
                                  +<--------------- MISO Hattı ----------------+
                                        MISO

                   [ SCLK (Saat) ] ================================>
                                 (8 Saat Darbesi)
```

### Full-Duplex Simetrisi ve "Dummy Byte" Kuralı:
1. Master her bir saat darbesi ($1\ \text{SCK}$) ürettiğinde:
   - Master'ın en önemli biti (Bit 7) MOSI hattından Slave'in Bit 0'ına doğru kayar.
   - Aynı anda Slave'in en önemli biti (Bit 7) MISO hattından Master'ın Bit 0'ına doğru kayar.
2. 8 saat darbesi tamamlandığında iki cihazın içindeki baytlar **tamamen yer değiştirmiştir**.
3. **Altın Kural:** SPI'da *"Sadece Veri Oku"* diye bir donanımsal işlem **YOKTUR**!
   - Slave'in verisi Master saat üretmeden hatta çıkamaz.
   - Master, Slave'den 1 bayt okumak istiyorsa, hatta kukla bir bayt (**Dummy Byte**, tipik olarak `0xFF` veya `0x00`) yazmak **ZORUNDADIR**.
   - Gönderilen her bayt karşılığında eşzamanlı olarak mutlaka bir bayt alınır!

## 3. SPI Saat Polaritesi ve Fazı (CPOL ve CPHA): 4 Modun Anatomisi

Sensör üreticileri (Analog Devices, Bosch, ST) ve donanım tasarımcıları saat sinyalinin boşta hangi seviyede kalacağını ve verinin hangi kenarda okunacağını farklı seçebilir. Bu davranış iki kontrol bitiyle tanımlanır:

### 1. CPOL (Clock Polarity - Saat Kutuplanması):
Haberleşme yokken (IDLE durumunda) SCK saat hattının durduğu elektriksel seviye:
- $\text{CPOL} = 0$: Saat hattı boşta **LOW ($0\ \text{V}$)** seviyesindedir. İlk kenar **Yükselen Kenardır (Rising Edge)**.
- $\text{CPOL} = 1$: Saat hattı boşta **HIGH ($3.3\ \text{V}$)** seviyesindedir. İlk kenar **Düşen Kenardır (Falling Edge)**.

### 2. CPHA (Clock Phase - Saat Fazı):
Veri bitinin (MOSI/MISO) hangi saat kenarında örnekleneceğini (Sample/Capture) ve hangi kenarda sürüleceğini (Shift/Setup) belirler:
- $\text{CPHA} = 0$: Veri **ilk saat kenarında** örneklenir; ikinci kenarda yeni bit hatta sürülür.
- $\text{CPHA} = 1$: Veri ilk saat kenarında hatta sürülür; **ikinci saat kenarında** örneklenir.

### SPI 4 Çalışma Modu Tablosu:
| SPI Modu | CPOL | CPHA | Boşta Saat (IDLE) | Veri Örnekleme (Sample) | Veri Sürme (Shift) | Yaygın Kullanım Alanı |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Mod 0** | 0 | 0 | **LOW (0V)** | **1. Kenar (Yükselen)** | 2. Kenar (Düşen) | **Standart IMU, SD Kart, EEPROM** |
| **Mod 1** | 0 | 1 | LOW (0V) | 1. Kenar (Düşen) | 1. Kenar (Yükselen) | Özel ADC / Endüstriyel Sensörler |
| **Mod 2** | 1 | 0 | **HIGH (3.3V)** | **1. Kenar (Düşen)** | 2. Kenar (Yükselen) | Nadir Kullanım |
| **Mod 3** | 1 | 1 | **HIGH (3.3V)** | **2. Kenar (Yükselen)** | 1. Kenar (Düşen) | **Yüksek Hızlı Flash Bellekler (Winbond)** |

> **Önemli Kural:** Master ve Slave'in SPI modu birebir aynı olmak zorundadır! Eğer sensör Mod 0 beklerken Master Mod 1 olarak sürerse, okunan verinin tüm bitleri **1 pozisyon sola kayar (Bit-Shift Corruption)** ve telemetri tamamen bozulur!

## 4. Chip Select (CS / NSS) Yönetimi: Donanımsal vs Yazılımsal (SSM)

SPI veri yolu ortak bir veri yoludur; SCK, MOSI ve MISO hatları birden fazla Slave cihaza paralel bağlanabilir. Hangi cihazın hatta cevap vereceğini **Chip Select (CS / NSS - Slave Select)** hattı belirler.

### Chip Select Pininin Çalışma Kuralları:
1. **Aktif LOW Mantığı:** CS pini boşta iken lojik 1 (HIGH / 3.3V) tutulur. İletişim başlayacağı an Master CS pinini **lojik 0'a (LOW)** çeker.
2. **Yüksek Empedans (Tri-State / High-Z):** Bir Slave'in CS pini HIGH iken, o Slave MISO pinini yüksek empedansa (High-Z / Yüzen) alır; yani hatta elektriksel olarak yokmuş gibi davranır. CS LOW yapıldığında MISO pini aktif çıkışa geçer.
3. **Birden Fazla CS LOW Yapılamaz:** Eğer yazılımsal bir hata sebebiyle iki farklı sensörün (örn. IMU ve Barometre) CS pinleri aynı anda LOW yapılırsa, her iki çip de MISO hattını sürmeye çalışır (Bus Contention / Kısa Devre)! Çipler aşırı ısınabilir veya yanabilir.

### Savunma Standardı: Yazılımsal Slave Yönetimi (Software Slave Management - SSM):
STM32'nin donanımsal NSS pini birden fazla Slave'in bulunduğu karmaşık kartlarda kullanışsızdır. Savunma sanayiinde standart yaklaşım:
- STM32 SPI donanımında `SSM = 1` ve `SSI = 1` (Software Slave Management) ayarlanır. Bu, donanımsal NSS pinini devre dışı bırakır ve iç mantığı Master modunda kilitler.
- Her Slave sensör için standart bir GPIO pini (örn. `PB0` -> IMU_CS, `PB1` -> FLASH_CS, `PB2` -> BARO_CS) atanır.
- İşlem sırası:
  ```cpp
  gpio_write(IMU_CS, LOW);          // 1. Sensörü seç
  delay_ns(50);                     // 2. Setup zamanı tanı (T_setup)
  spi_exchange_byte(cmd);           // 3. Veriyi takas et
  delay_ns(50);                     // 4. Hold zamanı tanı (T_hold)
  gpio_write(IMU_CS, HIGH);         // 5. Sensörü kapat (Hattı serbest bırak)
  ```

```python
# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 1 — SPI Full-Duplex Dairesel Kaydırma Yazmacı (Shift Register Exchange)
8 Saat Darbesi Boyunca Master ve Slave Bit Akışı ve Dummy Byte Mekanizması
"""

from typing import Tuple, List, Dict

class SPIShiftRegisterExchange:
    """Master ve Slave 8-bit Kaydırma Yazmaçlarının Donanımsal Simülatörü"""
    def __init__(self):
        pass

    def transfer_byte(self, master_byte: int, slave_byte: int) -> Dict[str, any]:
        """
        Master ve Slave arasında 8 saat darbesi boyunca bit takasını adım adım işletir.
        MSB First kuralı geçerlidir (En önemli bit 7 önce çıkar).
        """
        m_reg = master_byte & 0xFF
        s_reg = slave_byte & 0xFF

        trace = []
        # Başlangıç durumu
        trace.append({
            "clock_tick": 0,
            "master_reg": f"0b{m_reg:08b}",
            "slave_reg": f"0b{s_reg:08b}",
            "mosi_bit": None,
            "miso_bit": None
        })

        # 8 Saat Darbesi (1..8)
        for tick in range(1, 9):
            # 1. MSB bitleri hatlara sürülür
            mosi_bit = (m_reg >> 7) & 1
            miso_bit = (s_reg >> 7) & 1

            # 2. Yazmaçlar 1 bit sola kaydırılır ve diğer taraftan gelen bit LSB'ye alınır
            m_reg = ((m_reg << 1) & 0xFE) | miso_bit
            s_reg = ((s_reg << 1) & 0xFE) | mosi_bit

            trace.append({
                "clock_tick": tick,
                "master_reg": f"0b{m_reg:08b}",
                "slave_reg": f"0b{s_reg:08b}",
                "mosi_bit": mosi_bit,
                "miso_bit": miso_bit
            })

        return {
            "master_sent": master_byte,
            "slave_sent": slave_byte,
            "master_received": m_reg,
            "slave_received": s_reg,
            "trace": trace
        }

# Test 1: Karşılıklı Veri Takası
# Master IMU'ya Okuma Komutu Gönderiyor: 0x8F (WHO_AM_I Okuma, Bit7=1)
# Slave IMU içinde WHO_AM_I cevabı hazır: 0xEA (Cihaz Kimlik Kodu)
sim = SPIShiftRegisterExchange()
res1 = sim.transfer_byte(master_byte=0x8F, slave_byte=0xEA)

print("[*] SPI Full-Duplex Donanımsal Kaydırma Yazmacı Testi:")
print(f"  [+] Master Gönderdi : 0x{res1['master_sent']:02X} (0b{res1['master_sent']:08b})")
print(f"  [+] Slave Gönderdi  : 0x{res1['slave_sent']:02X} (0b{res1['slave_sent']:08b})")
print(f"  [+] Master Aldı     : 0x{res1['master_received']:02X} (Beklenen: 0xEA)")
print(f"  [+] Slave Aldı      : 0x{res1['slave_received']:02X} (Beklenen: 0x8F)")

# Test 2: Dummy Byte ile Salt Okuma
# Master Dummy (0xFF) gönderiyor, Slave sıcaklık telemetrisi (0x24 = 36 C) dönüyor
res_dummy = sim.transfer_byte(master_byte=0xFF, slave_byte=0x24)
print(f"\n[*] Dummy Byte (0xFF) Okuma Testi:")
print(f"  [+] Master Aldığı Telemetri: 0x{res_dummy['master_received']:02X} ({res_dummy['master_received']} °C)")

assert res1["master_received"] == 0xEA, "Master Slave verisini alamadı!"
assert res1["slave_received"] == 0x8F, "Slave Master verisini alamadı!"
assert res_dummy["master_received"] == 0x24, "Dummy byte okuma başarısız!"
print("\n[HÜCRE 6] SPI dairesel kaydırma yazmacı ve dummy byte mekanizması başarıyla doğrulandı.")
```

## 5. SPI 4 Modunun (Mode 0, 1, 2, 3) Dalga Formu ve Örnekleme Zamanlaması

SPI zamanlamasını anlamanın yolu saat kenarlarını ve veri kararlılık pencerelerini takip etmektir.

```
+-----------------------------------------------------------------------------------+
|               SPI 4 MODUNUN SAAT (SCK) VE ÖRNEKLEME (SAMPLE) DİYAGRAMI            |
+-----------------------------------------------------------------------------------+

                    Kenar 1      Kenar 2      Kenar 3      Kenar 4
                       |            |            |            |
   MODE 0 (0,0):       +-----+      |     +-----+      |     +--
   (Boşta LOW)   ------/     \------------/     \------------/   (Yükselende ÖRNEKLE)
                       ^            v            ^            v
                    [SAMPLE]     [SHIFT]      [SAMPLE]     [SHIFT]

   MODE 1 (0,1):       +-----+      |     +-----+      |     +--
   (Boşta LOW)   ------/     \------------/     \------------/   (Düşende ÖRNEKLE)
                       v            ^            v            ^
                    [SHIFT]      [SAMPLE]     [SHIFT]      [SAMPLE]

   MODE 2 (1,0): ------\     /------------\     /------------\   (Düşende ÖRNEKLE)
   (Boşta HIGH)        +-----+      |     +-----+      |     +--
                       ^            v            ^            v
                    [SAMPLE]     [SHIFT]      [SAMPLE]     [SHIFT]

   MODE 3 (1,1): ------\     /------------\     /------------\   (Yükselende ÖRNEKLE)
   (Boşta HIGH)        +-----+      |     +-----+      |     +--
                       v            ^            v            ^
                    [SHIFT]      [SAMPLE]     [SHIFT]      [SAMPLE]
```

### Zamanlama Kritik Parametreleri (Timing Specs):
- $T_{\text{SCK}}$: Saat periyodu ($10\ \text{MHz} \implies 100\ \text{ns}$).
- $T_{\text{setup}}$ (Veri Kurulum Süresi): Örnekleme kenarından önce verinin hatta kararlı kalması gereken minimum süre (tipik $> 5\ \text{ns}$).
- $T_{\text{hold}}$ (Veri Tutma Süresi): Örnekleme kenarından sonra verinin hatta değişmeden kalması gereken minimum süre (tipik $> 5\ \text{ns}$).

```python
# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 2 — SPI 4 Modu (CPOL/CPHA) Sinyal Üretici ve Zamanlama Simülatörü
Mode 0, 1, 2, 3 İçin Saat Seviyesi, Örnekleme Kenarı ve Veri Çözümleme Doğrulaması
"""

import numpy as np
from typing import Dict, List, Tuple

class SPIModeSimulator:
    """SPI 4 Modunun Saat ve Veri Zamanlama Simülatörü"""
    def __init__(self, mode: int):
        assert mode in [0, 1, 2, 3], "Mod 0, 1, 2 veya 3 olmalıdır!"
        self.mode = mode
        self.cpol = 1 if mode in [2, 3] else 0
        self.cpha = 1 if mode in [1, 3] else 0

    def get_clock_edges(self, num_bits: int = 8) -> List[Dict[str, any]]:
        """Her bit için 2 saat kenarının (Edge 1, Edge 2) polarite ve aksiyonunu döner"""
        edges = []
        for bit_idx in range(num_bits):
            # Kenar 1
            e1_type = "FALLING" if self.cpol == 1 else "RISING"
            e1_action = "SHIFT" if self.cpha == 1 else "SAMPLE"
            edges.append({"bit": bit_idx, "edge_num": 1, "type": e1_type, "action": e1_action})

            # Kenar 2
            e2_type = "RISING" if self.cpol == 1 else "FALLING"
            e2_action = "SAMPLE" if self.cpha == 1 else "SHIFT"
            edges.append({"bit": bit_idx, "edge_num": 2, "type": e2_type, "action": e2_action})

        return edges

    def sample_data(self, data_bits: List[int]) -> List[int]:
        """Verilen bit akışını bu modun kurallarına göre çözümler"""
        # İdeal senkron hatta doğru modda okunan veri orijinal veriye eşittir
        return list(data_bits)

# Doğrulama: 4 Modun Karakteristiği
modes_info = {}
for m in [0, 1, 2, 3]:
    sim_m = SPIModeSimulator(m)
    edges = sim_m.get_clock_edges(num_bits=1) # 1. bitin kenarları
    modes_info[m] = {
        "cpol": sim_m.cpol,
        "cpha": sim_m.cpha,
        "idle_level": "HIGH" if sim_m.cpol == 1 else "LOW",
        "sample_edge": [e for e in edges if e["action"] == "SAMPLE"][0]["type"]
    }

print("[*] SPI 4 Çalışma Modu Özellikleri:")
print(f"{'Mod':>5} | {'CPOL':>5} | {'CPHA':>5} | {'Boşta (IDLE)':>14} | {'Örnekleme Kenarı'}")
print("-" * 55)
for m, info in modes_info.items():
    print(f"Mod {m:>1} | {info['cpol']:>5} | {info['cpha']:>5} | {info['idle_level']:>14} | {info['sample_edge']}")

# Katı Doğrulamalar
assert modes_info[0]["cpol"] == 0 and modes_info[0]["cpha"] == 0
assert modes_info[0]["idle_level"] == "LOW" and modes_info[0]["sample_edge"] == "RISING"

assert modes_info[3]["cpol"] == 1 and modes_info[3]["cpha"] == 1
assert modes_info[3]["idle_level"] == "HIGH" and modes_info[3]["sample_edge"] == "RISING"
print("\n[HÜCRE 8] SPI 4 modu zamanlama ve saat kenarı kuralları başarıyla doğrulandı.")
```

## 6. Yazılımsal Chip Select (SSM) ve CS Setup/Hold Zamanlama İhlalleri

Savunma sınıfı aviyonik donanımlarda karşılaşılan en yaygın donanım arızalarından biri **CS Setup ($T_{\text{setup}}$) ve Hold ($T_{\text{hold}}$) zamanlama ihlalleridir**.

### Kritik Zamanlama Gereksinimleri:
Sensör veri sayfalarında (Datasheet) şu süreler garanti edilmelidir:
1. **$T_{\text{CSS}}$ (CS to SCLK Setup Time):** CS pini LOW yapıldıktan sonra ilk SCK saat kenarı üretilene kadar geçmesi gereken minimum bekleme süresi (tipik $20 - 50\ \text{ns}$).
   - *İhlal edilirse:* Sensör iç durum makinesi uyanamaz, ilk saat darbesini kaçırır ve ilk bit ezilir!
2. **$T_{\text{CSH}}$ (SCLK to CS Hold Time):** Son saat darbesi bittikten sonra CS pini tekrar HIGH yapılmadan önce beklenmesi gereken minimum süre (tipik $20 - 50\ \text{ns}$).
   - *İhlal edilirse:* Son bit (Bit 0) henüz sensörün iç kaydırma yazmacına yazılamadan arayüz kapanır ve son bit bozulur!
3. **$T_{\text{CS\_HIGH}}$ (CS High Minimum Time):** İki ardışık SPI paketi arasında CS pininin HIGH kalması gereken süre ($50 - 100\ \text{ns}$). Sensörün dahili komutları tamamlaması için gereklidir.

```
   CS Pini   ---+                                                     +---
                \                                                     /
                |   <--T_setup-->                     <--T_hold-->    |
   SCK Hattı    |                 +---+   ...   +---+                 |
   (Mode 0)  ---+-----------------/   \---------/   \-----------------+---
                                   Bit 7         Bit 0
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 3 — SPI Çoklu-Slave (Multi-Slave) CS Çekişmesi ve Zamanlama Koruması
Bağımsız CS Pinleri, Bus Contention Koruması ve T_setup / T_hold Doğrulaması
"""

from typing import Dict, List, Optional

class SPISlaveDevice:
    """Sanal SPI Sensörü (Örn: IMU, Barometre, Flash)"""
    def __init__(self, name: str, device_id: int):
        self.name = name
        self.device_id = device_id
        self.cs_pin = 1 # 1: Pasif (HIGH), 0: Seçili (LOW)
        self.miso_active = False

    def set_cs(self, level: int):
        self.cs_pin = level
        self.miso_active = (level == 0) # CS LOW olunca MISO aktifleşir

class SPIMasterBusController:
    """Çoklu Slave SPI Bus Denetleyicisi ve Çekişme (Contention) Koruması"""
    def __init__(self, slaves: List[SPISlaveDevice]):
        self.slaves = slaves
        self.bus_contention_detected = False

    def select_slave(self, slave_index: int) -> bool:
        # Önce tüm slave'leri kapat (HIGH yap)
        for s in self.slaves:
            s.set_cs(1)

        # İstenen slave'i aç (LOW yap)
        if 0 <= slave_index < len(self.slaves):
            self.slaves[slave_index].set_cs(0)
            return True
        return False

    def deselect_all(self):
        for s in self.slaves:
            s.set_cs(1)

    def check_bus_health(self) -> bool:
        """Aynı anda birden fazla slave MISO sürüyorsa kısa devre (contention) oluşur!"""
        active_drivers = sum(1 for s in self.slaves if s.miso_active)
        if active_drivers > 1:
            self.bus_contention_detected = True
            return False
        return True

# Test ve Simülasyon
imu_sensor = SPISlaveDevice("ADIS16488_IMU", device_id=0x01)
baro_sensor = SPISlaveDevice("MS5611_BARO", device_id=0x02)
flash_mem = SPISlaveDevice("W25Q128_FLASH", device_id=0x03)

bus_mgr = SPIMasterBusController([imu_sensor, baro_sensor, flash_mem])

# 1. Normal Çalışma (Sırayla Seçim)
bus_mgr.select_slave(0) # IMU seçildi
assert bus_mgr.check_bus_health() is True, "Normal seçimde bus sağlıklı olmalı!"
assert imu_sensor.miso_active is True and baro_sensor.miso_active is False

bus_mgr.select_slave(1) # Barometre seçildi
assert bus_mgr.check_bus_health() is True
assert imu_sensor.miso_active is False and baro_sensor.miso_active is True

bus_mgr.deselect_all()
assert sum(1 for s in bus_mgr.slaves if s.miso_active) == 0, "Tüm slave'ler pasif olmalı!"

# 2. Hata Enjeksiyonu: Donanımsal Sabotaj (Aynı anda 2 CS LOW yapıldı)
imu_sensor.set_cs(0)
baro_sensor.set_cs(0) # SABOTAJ!
is_healthy = bus_mgr.check_bus_health()

print("[*] SPI Çoklu-Slave Bus Çekişme (Contention) Testi:")
print(f"  [+] Tekil Seçim Sağlık Durumu : Sağlıklı (1 Aktif MISO Sürücüsü)")
print(f"  [!] Çift CS Seçimi Durumu     : {is_healthy} (Çekişme Algılandı: {bus_mgr.bus_contention_detected})")

assert is_healthy is False, "Çift CS seçildiğinde bus contention yakalanmalıydı!"
print("\n[HÜCRE 10] Çoklu slave CS çekişme koruma mekanizması başarıyla doğrulandı.")
```

## 7. STM32 SPI Bare-Metal Donanım Sürücüsü ve Bayraklar (TXE, RXNE, BSY)

STM32 SPI çevre birimi (SPI1..SPI6) durum yazmacında (SR) üç kritik bayrak yönetir:

### Durum Bayrakları (Status Register - SPI_SR):
1. **TXE (Transmit Buffer Empty - Bit 1):**
   - Donanım veri yazmacı (`SPI_DR`) boşaldığında `1` olur. Master yeni bir bayt yazabilir.
2. **RXNE (Receive Buffer Not Empty - Bit 0):**
   - Hattan 8 bit tamamlanıp `SPI_DR` yazmacına aktarıldığında `1` olur. Yazılım DR'ı okuduğunda otomatik sıfırlanır.
3. **BSY (Busy Flag - Bit 7):**
   - SPI arayüzü saat üretmeye ve veri aktarmaya devam ettiği sürece `1`'dir.
   - **Ölümcül Hata:** Veri aktarımı bittiğinde CS pinini HIGH yapmadan önce sadece `TXE`'ye bakmak **büyük bir hatadır**! `TXE = 1` olduğunda son bit hala teldedir. CS pinini çekmeden önce **kesinlikle `BSY == 0` olması beklenmelidir!**

```c
// Standart STM32 Bare-Metal SPI Bayt Takası
uint8_t spi_exchange_byte(uint8_t tx_data) {
    while (!(SPI1->SR & SPI_SR_TXE));  // 1. TX tamponunun boşalmasını bekle
    SPI1->DR = tx_data;                // 2. Veriyi yaz (Saat üretimi başlar)
    while (!(SPI1->SR & SPI_SR_RXNE)); // 3. Gelen baytın tamamlanmasını bekle
    return (uint8_t)SPI1->DR;          // 4. Alınan baytı oku ve dön
}

void spi_cs_release(void) {
    while (SPI1->SR & SPI_SR_BSY);     // 5. Hattın tamamen boşalmasını bekle!
    GPIO_SET_HIGH(CS_PIN);             // 6. CS pinini ancak şimdi kapat!
}
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 4 — C++20 STM32 Bare-Metal SPI Master Sürücü Simülasyonu
Sanal SPI Yazmaçları (SR, DR, CR1), TXE, RXNE, BSY Bayrakları ve Timeout Koruması
"""

from typing import Tuple, Optional

class VirtualSTM32SPIHardware:
    """STM32 SPI Donanımının Sanal Register Modeli"""
    SPI_SR_RXNE = (1 << 0)
    SPI_SR_TXE  = (1 << 1)
    SPI_SR_BSY  = (1 << 7)

    def __init__(self, connected_slave_byte: int = 0xAA):
        self.SR = self.SPI_SR_TXE # Başlangıçta TX boş, BSY=0, RXNE=0
        self.DR_tx = 0
        self.DR_rx = 0
        self.slave_response = connected_slave_byte
        self.cycles = 0

    def write_DR(self, byte_val: int):
        self.DR_tx = byte_val & 0xFF
        self.SR &= ~self.SPI_SR_TXE # TXE temizlendi (dolu)
        self.SR |= self.SPI_SR_BSY   # Hat meşgul (BSY=1)

    def step_clock(self):
        """Donanımın saat çevrimi: Veri takasını tamamlar"""
        if self.SR & self.SPI_SR_BSY:
            self.DR_rx = self.slave_response # Slave'den gelen veri RX'e yazıldı
            self.SR |= self.SPI_SR_RXNE      # RXNE = 1
            self.SR |= self.SPI_SR_TXE       # TXE = 1
            self.SR &= ~self.SPI_SR_BSY      # Aktarım bitti (BSY = 0)

    def read_DR(self) -> int:
        val = self.DR_rx
        self.SR &= ~self.SPI_SR_RXNE # Okununca RXNE temizlenir
        return val

class STM32SPIMasterDriver:
    """C++20 Benzeri Robust SPI Master Sürücüsü"""
    def __init__(self, hw: VirtualSTM32SPIHardware):
        self.hw = hw

    def exchange_byte(self, byte_to_send: int, timeout_cycles: int = 100) -> Tuple[bool, int]:
        # 1. TXE Bekle
        cycles = 0
        while not (self.hw.SR & VirtualSTM32SPIHardware.SPI_SR_TXE):
            self.hw.step_clock()
            cycles += 1
            if cycles >= timeout_cycles:
                return False, 0

        # 2. Veriyi Yaz
        self.hw.write_DR(byte_to_send)

        # 3. RXNE Bekle
        cycles = 0
        while not (self.hw.SR & VirtualSTM32SPIHardware.SPI_SR_RXNE):
            self.hw.step_clock()
            cycles += 1
            if cycles >= timeout_cycles:
                return False, 0

        # 4. Veriyi Oku
        received_byte = self.hw.read_DR()
        return True, received_byte

    def wait_until_idle(self, timeout_cycles: int = 100) -> bool:
        """CS kapatılmadan önce BSY bayrağının düşmesini bekle"""
        cycles = 0
        while (self.hw.SR & VirtualSTM32SPIHardware.SPI_SR_BSY):
            self.hw.step_clock()
            cycles += 1
            if cycles >= timeout_cycles:
                return False
        return True

# Sürücü Doğrulama Testi
virt_spi = VirtualSTM32SPIHardware(connected_slave_byte=0x3F)
spi_driver = STM32SPIMasterDriver(virt_spi)

# Veri Takası: 0x80 gönder, 0x3F al
success, rx_val = spi_driver.exchange_byte(0x80)
is_idle = spi_driver.wait_until_idle()

print("[*] STM32 Bare-Metal SPI Sürücü Doğrulama Testi:")
print(f"  [+] Gönderilen Bayt : 0x80")
print(f"  [+] Alınan Bayt     : 0x{rx_val:02X} (Başarılı: {success})")
print(f"  [+] BSY Boşta mı    : {is_idle} (CS güvenle HIGH yapılabilir)")

assert success is True and rx_val == 0x3F, "SPI bayt takası hatalı!"
assert is_idle is True, "SPI aktarım sonrası meşgul kaldı!"
print("\n[HÜCRE 12] C++20 bare-metal SPI sürücüsü başarıyla doğrulandı.")
```

## 8. Savunma Sanayii Aviyonik Senaryosu: ROKETSAN / ASELSAN IMU Sensör

Taktik seviye güdümlü mühimmatlarda (örneğin CİRİT, HİSAR, TEBER) füzeyi hedefe yönlendiren en kritik sensör **Ataletsel Ölçüm Birimidir (Inertial Measurement Unit - IMU)**.

### Aviyonik IMU SPI İletişim Protokolü:
- **Hız:** $10\ \text{MHz}$ SPI Saat Frekansı ($T_{\text{bit}} = 100\ \text{ns}$).
- **Mod:** SPI Mod 3 ($\text{CPOL}=1, \text{CPHA}=1$) veya Mod 0.
- **Komut Formatı (16-bit Sözcük):**
  - Bit 15: $1 \implies \text{Read}$, $0 \implies \text{Write}$
  - Bits [14:8]: 7-bit Kayıt Adresi (`Register Address`)
  - Bits [7:0]: Yazılacak Veri veya Dummy Byte (`0x00`)
- **Burst Read (Patlama Okuması):**
  İvme ($a_x, a_y, a_z$) ve dönü hızı ($\omega_x, \omega_y, \omega_z$) 6 eksenli veri olarak tek bir CS LOW penceresinde ardışık $12\ \text{bayt}$ olarak okunur.
- **Veri Bütünlüğü Doğrulaması:**
  SPI'da donanımsal parity olmadığı için aviyonik paketlerin sonuna 16-bit **CRC (Cyclic Redundancy Check)** eklenir. Titreşim veya EMI sebebiyle 1 bit dahi bozulursa tüm telemetri çöpe atılır ve arıza sayacı artırılır!

```python
# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 5 — Taktik IMU SPI Kayıt Okuma ve CRC-16 Bütünlük Testi
Burst-Read ile 6 Eksen Telemetri Çekimi ve SPI Bit Bozulma İzolasyonu
"""

from typing import Dict, List, Tuple

class TacticalIMUSensor:
    """ROKETSAN Taktik IMU Sensör Modeli (Örn: ADIS16488 benzeri)"""
    def __init__(self):
        # 6 Eksen Ham Sensör Değerleri (16-bit Signed Integer)
        # Gyro X, Y, Z (dps) ve Accel X, Y, Z (g)
        self.registers = {
            0x02: 0x0012, # GYRO_X (+18 dps)
            0x04: 0xFFF0, # GYRO_Y (-16 dps)
            0x06: 0x0005, # GYRO_Z (+5 dps)
            0x08: 0x03E8, # ACCEL_X (+1000 mg = +1.0g)
            0x0A: 0x0000, # ACCEL_Y (0.0g)
            0x0C: 0xFC18, # ACCEL_Z (-1000 mg = -1.0g)
        }

    @staticmethod
    def calculate_crc16(data_bytes: List[int]) -> int:
        """CCITT-16 CRC Algoritması (Polinom: 0x1021, Init: 0xFFFF)"""
        crc = 0xFFFF
        for byte in data_bytes:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    def read_burst_telemetry(self, inject_bit_error: bool = False) -> Dict[str, any]:
        """Tüm eksenleri 12 bayt halinde okur ve CRC ekler"""
        payload = []
        for reg_addr in [0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C]:
            val16 = self.registers[reg_addr]
            payload.append((val16 >> 8) & 0xFF) # High Byte
            payload.append(val16 & 0xFF)        # Low Byte

        crc = self.calculate_crc16(payload)

        # Hata Enjeksiyonu
        if inject_bit_error:
            payload[3] ^= 0x01 # 4. baytın 1 bitini boz

        return {
            "payload_bytes": payload,
            "crc_transmitted": crc,
            "is_valid": self.calculate_crc16(payload) == crc
        }

# Test ve Simülasyon
imu = TacticalIMUSensor()

# 1. Normal Hatasız Okuma
res_clean = imu.read_burst_telemetry(inject_bit_error=False)
print("[*] Taktik Aviyonik IMU SPI Telemetri Testi:")
print(f"  [+] Okunan 12 Bayt    : {[f'0x{b:02X}' for b in res_clean['payload_bytes']]}")
print(f"  [+] Hesaplanan CRC-16 : 0x{res_clean['crc_transmitted']:04X}")
print(f"  [+] Bütünlük Durumu   : {res_clean['is_valid']} (Kabul Edildi)")

# 2. Gürültülü Hat / Bozuk Bit Testi
res_corrupt = imu.read_burst_telemetry(inject_bit_error=True)
print(f"  [!] Bozuk Paket Durumu: {res_corrupt['is_valid']} (CRC Uyuşmazlığı Reddedildi)")

assert res_clean["is_valid"] is True, "Temiz telemetri CRC kontrolünü geçmeliydi!"
assert res_corrupt["is_valid"] is False, "Bozuk telemetri CRC tarafından yakalanmalıydı!"
print("\n[HÜCRE 14] Taktik IMU telemetri ve CRC-16 doğrulama motoru başarıyla onaylandı.")
```

## 9. Üretim Seviyesi C++20 RAII SPI Transaction Sürücüsü

Modern gömülü C++20 mimarisinde Chip Select yönetiminin manuel yapılması hata riskini artırır. RAII (Resource Acquisition Is Initialization) prensibiyle yazılmış bir `SpiTransaction` nesnesi oluşturulduğunda CS pinini otomatik LOW yapar, nesnenin ömrü bittiğinde (scope'tan çıkıldığında) donanımın boşalmasını (`BSY`) bekleyip CS pinini otomatik HIGH çeker!

```cpp
// ============================================================================
// C++20 RAII SPI Transaction Wrapper
// ============================================================================
#include <cstdint>
#include <span>

namespace defense::hal {

struct SpiRegisters {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t SR;
    volatile uint32_t DR;
};

template <uintptr_t SpiBase, typename GpioCsPin>
class SpiTransaction {
public:
    explicit SpiTransaction(GpioCsPin cs_pin) noexcept : cs_pin_(cs_pin) {
        cs_pin_.set_low(); // 1. CS LOW yap
        // T_setup beklemesi (donanımsal asm nop döngüsü)
        for (volatile int i = 0; i < 5; ++i); 
    }

    ~SpiTransaction() noexcept {
        // 2. Hat boşalana kadar bekle (BSY bayrağı sıfırlanmalı)
        while (Regs->SR & (1 << 7));
        cs_pin_.set_high(); // 3. CS HIGH yap
    }

    // Kopyalama yasak (RAII tekilliği)
    SpiTransaction(const SpiTransaction&) = delete;
    SpiTransaction& operator=(const SpiTransaction&) = delete;

    uint8_t transfer_byte(uint8_t tx) noexcept {
        while (!(Regs->SR & (1 << 1))); // TXE bekle
        Regs->DR = tx;
        while (!(Regs->SR & (1 << 0))); // RXNE bekle
        return static_cast<uint8_t>(Regs->DR);
    }

private:
    static constexpr SpiRegisters* Regs = reinterpret_cast<SpiRegisters*>(SpiBase);
    GpioCsPin cs_pin_;
};

} // namespace defense::hal
```

## 10. Bilerek Bozduğumuz Şey (Sabotaj ve Arıza Analizi)

### Sabotaj 1: Yanlış CPHA Seçimi ve 1-Bit Kayma (Bit Shifting) Felaketi
Sensör Mode 0 ($\text{CPOL}=0, \text{CPHA}=0$) beklerken Master'ın yanlışlıkla Mode 1 ($\text{CPOL}=0, \text{CPHA}=1$) olarak yapılandırılması:
- **Ne Olur?:** Sensör ilk saat kenarında (Rising) veriyi okumak isterken, Master Mode 1 gereği veriyi ancak ilk kenarda hatta sürer!
- **Sonuç:** Sensör ilk biti henüz hat oturmadan (setup time ihlali) veya bir önceki rastgele seviyeden okur. Okunan tüm baytın bitleri **1 pozisyon sola kayar**. $0\text{x40}$ beklenen değer $0\text{x80}$ olarak okunur. Sensör kimliği doğrulanamaz ve sistem kilitlenir.

### Sabotaj 2: BSY Beklemeden CS Pinini HIGH Yapmak
```c
// ÖLÜMCÜL KOD (SABOTAJ):
SPI1->DR = data_byte;
while (!(SPI1->SR & SPI_SR_TXE)); // HATA! TXE sadece yazmacın boşaldığını gösterir!
GPIO_SET_HIGH(CS_PIN);            // SABOTAJ: Son 3 bit henüz teldeyken CS kapatıldı!
```
- **Ne Olur?:** `TXE` 1 olduğu anda baytın sadece ilk birkaç biti hattan çıkmıştır; son bitler kaydırma yazmacındadır.
- **Sonuç:** CS aniden HIGH olunca Slave anında MISO hattını Tri-State'e alır ve iletişimi keser. Son bitler yok olur, paket bozulur.

## 11. Karşılaştırma Matrisi: SPI vs UART vs I2C

| Karşılaştırma Kriteri | SPI (Serial Peripheral Int.) | I2C (Inter-Integrated Circuit) | UART (Asynchronous) |
| :--- | :--- | :--- | :--- |
| **Senkron / Asenkron** | **Senkron (Ortak SCK)** | Senkron (Ortak SCL) | Asenkron (Clock hattı yok) |
| **Maksimum Hız** | **Çok Yüksek ($10 - 50+\ \text{MHz}$)** | Düşük/Orta ($100\ \text{k} - 1\ \text{MHz}$) | Düşük ($115.2\ \text{k} - 1\ \text{Mbps}$) |
| **Kablo / Hat Sayısı** | 4 Hat (SCK, MOSI, MISO, CS) | **2 Hat (SDA, SCL)** | 2 Hat (TX, RX) + GND |
| **İletişim Yönü** | **Tam Çift Yönlü (Full-Duplex)** | Yarı Çift Yönlü (Half-Duplex) | Tam Çift Yönlü (Full-Duplex) |
| **Protokol Yükü (Overhead)** | **%0 (Start/Stop/Adres biti yok)** | Yüksek (Start, Stop, 7-bit Adres, ACK) | Orta (Start, Stop, Parity) |
| **Çoklu Aygıt (Multi-Device)** | Her aygıt için ayrı CS pini | Paylaşımlı veri yolunda adresleme | Noktadan noktaya (Point-to-Point) |
| **Kullanım Alanı** | **IMU, Flash Bellek, Yüksek Hızlı ADC** | Sıcaklık Sensörü, RTC, EEPROM | Görev Bilgisayarı, GPS, Debug Shell |

## 12. Donanım ve Yazmaç Haritası (STM32 SPI1..SPI6)

STM32F4 serisinde SPI çevre birimlerinin bus ve hız dağılımı:

```
  +-------------------------------------------------------------------------------+
  |                 STM32 ÇEVRESEL VERİ YOLU (BUS) VE SPI MODÜLLERİ               |
  +-------------------------------------------------------------------------------+
  
  [ APB2 Yüksek Hızlı Bus (84 MHz) ]
    |---> SPI1 : 0x40013000 (Maksimum Hız: 42 MHz) -> SCK: PA5, MISO: PA6, MOSI: PA7
    |---> SPI4 : 0x40013400 (Maksimum Hız: 42 MHz) -> SCK: PE2, MISO: PE5, MOSI: PE6
    |---> SPI5 : 0x40015000 (Maksimum Hız: 42 MHz) -> SCK: PF7, MISO: PF8, MOSI: PF9
    |---> SPI6 : 0x40015400 (Maksimum Hız: 42 MHz) -> SCK: PG13, MISO: PG12, MOSI: PG14
  
  [ APB1 Standart Hızlı Bus (42 MHz) ]
    |---> SPI2 : 0x40003800 (Maksimum Hız: 21 MHz) -> SCK: PB13, MISO: PB14, MOSI: PB15
    |---> SPI3 : 0x40003C00 (Maksimum Hız: 21 MHz) -> SCK: PC10, MISO: PC11, MOSI: PC12
```

> **Hız Notu:** Taktik IMU ve yüksek hızlı Flash bellekler daima APB2 veri yolundaki **SPI1** modülüne bağlanmalıdır ($42\ \text{MHz}$ azami saat frekansı).

## 13. Mülakat ve Saha Tuzakları (Top 5 Gotchas)

1. **"Sadece okumak istiyorum, neden veri göndereyim?" Tuzağı:**
   - Mülakatlarda en sık sorulan sorudur: SPI Master saat üretmeden Slave veri basamaz. Okumak için mutlaka dummy byte (`0xFF`) gönderilmelidir.
2. **BSY Bayrağını Beklemeden CS Pinini Kapatmak:**
   - Saha arızalarında son baytın bozulmasının bir numaralı sebebidir. `TXE` yetmez, `BSY == 0` beklenmelidir.
3. **MISO Hattında Pull-Up Direnci Bulunmaması:**
   - Tüm slave'ler pasifken (CS HIGH) MISO hattı High-Z'dedir. Eğer hatta zayıf bir Pull-Up yoksa hat ortamdaki EMI parazitlerini toplar ve sahte baytlar okunur.
4. **Maksimum SPI Saat Frekansını Aşmak:**
   - Sensör datasheet'inde $f_{\text{max}} = 10\ \text{MHz}$ yazarken, işlemciyi $42\ \text{MHz}$'de sürmek sinyal kenarlarını bozar ve veri okunamaz.
5. **CPOL/CPHA Uyumsuzluğunu Osiloskopsuz Çözmeye Çalışmak:**
   - Mod hatasında veriler 1 bit kayar. Geliştirici kodda bit kaydırma (`val << 1`) hilesi yapar; bu taktik seviyede affedilemez bir tasarım hatasıdır.

## 14. 5N1K Özeti

- **Ne?:** SPI (Serial Peripheral Interface), saat hattı paylaşımlı, tam çift yönlü (Full-Duplex), yüksek hızlı senkron seri haberleşme protokolüdür.
- **Neden?:** Sensörler ve belleklerle $10 - 50+\ \text{Mbps}$ hızında, sıfır protokol yükü (overhead) ile veri takas etmek için.
- **Nasıl?:** Master'ın ürettiği SCK darbeleri eşliğinde, Master ve Slave'in kaydırma yazmaçlarını dairesel halka olarak döndürerek.
- **Nerede?:** Taktik IMU jiroskop/ivmeölçerlerinde, yüksek hızlı NOR Flash çiplerinde, ADC/DAC çeviricilerde.
- **Ne Zaman?:** UART ve I2C bant genişliğinin telemetri aktarımına yetmediği yüksek hızlı sensör çevrimlerinde ($> 1\ \text{kHz}$).
- **Kim?:** Aviyonik gömülü sistem mühendisleri, güdüm kontrol yazılımcıları.

## 15. Gün Sonu Özeti ve Yetkinlik Kontrolü

### 3 Cümlelik Özet:
1. **SPI Nedir?:** SPI, paylaşımlı saat hattı (SCK) üzerinden kaydırma yazmaçlarının takas edilmesiyle çalışan senkron, tam çift yönlü bir protokoldür.
2. **Hangi Problemi Çözer?:** Asenkron saat kayması (baud drift) sorununu yok ederek $10-50\ \text{MHz}$ hızlarda sıfır protokol yüküyle veri aktarımı sağlar.
3. **Getirdiği Risk / Trade-off:** Her aygıt için bağımsız CS pini gerektirir (pin israfı), donanımsal onay/hata denetimi yoktur ve mod uyumsuzluğunda 1-bit kayma hatası üretir.

### Yetkinlik Kontrol Listesi:
- [x] SPI'ın senkron çalışma mantığını ve dairesel kaydırma yazmacı takasını açıklayabiliyorum.
- [x] Dummy byte göndermeden SPI'dan veri okunamayacağını biliyorum.
- [x] CPOL ve CPHA bitlerinin 4 SPI modunu nasıl oluşturduğunu ve dalga formunu çizebiliyorum.
- [x] CS pinini kapatmadan önce neden BSY bayrağının beklenmesi gerektiğini anladım.
- [x] Çoklu slave sistemlerde MISO bus çekişmesinin nasıl önleneceğini tasarlayabiliyorum.
- [x] Taktik IMU burst-read telemetrisini ve CRC-16 bütünlük kontrolünü uygulayabiliyorum.

## 16. İleri Okuma ve Kaynaklar

1. **Motorola SPI Block Guide (V04.01):** *Original Serial Peripheral Interface Specification.*
2. **STMicroelectronics Reference Manual (RM0090):** *SPI Functional Description, Master/Slave Modes and Flag Management.*
3. **Analog Devices Application Note (AN-1407):** *High Reliability SPI Interface Design for Tactical IMUs.*
4. **C++20 Embedded Design Patterns:** *RAII for Hardware Peripherals and Zero-Cost Bus Abstractions.*

## 17. 24-Hücreli Master Mimari Onay Beyanı

Bu eğitim modülü, ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ standartlarında C++20 ve STM32 Gömülü Sistemler Müfredatı kapsamında hazırlanmıştır.

```
+-----------------------------------------------------------------------------------+
|               GÜN 170 MASTER MİMARİ MÜHENDİSLİK DOĞRULAMA RAPORU                  |
+-----------------------------------------------------------------------------------+
| 1. Toplam Hücre Sayısı        : 24 Hücre (18 Markdown, 6 Python Kodu)             |
| 2. Protokol Modelleri         : SPI Full-Duplex Shift Register, Dummy Byte        |
| 3. Zamanlama Mimarisi         : CPOL, CPHA, 4 Çalışma Modu Analizi                |
| 4. Donanım Kontrolü           : Yazılımsal CS (SSM), BSY Bayrağı ve Çekişme Önleme|
| 5. Aviyonik Senaryosu         : Taktik IMU Burst-Read ve CRC-16 Bütünlük Testi    |
| 6. Görsel Artefact            : 300 DPI 4-Panelli Koyu Tema Dashboard (.PNG)      |
| 7. Özel Lisans                : Telif Hakkı (c) 2026 Seydi Eryılmaz               |
+-----------------------------------------------------------------------------------+
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. SPI Full-Duplex Dairesel Kaydırma Yazmacı Değişimi (Master & Slave 8-Clock Ring)
2. SPI 4 Modu (CPOL ve CPHA) Saat ve Örnekleme Zamanlama Diyagramı
3. Çoklu-Slave Chip Select (CS) ve MISO Çekişmesi Önleme Mimarisi
4. Veri Yolu Hızı ve Bant Genişliği Karşılaştırması (UART vs I2C vs SPI 10M/42M)
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
# PANEL 1: SPI Full-Duplex Dairesel Kaydırma Yazmacı Değişimi
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

# 8 Saat vuruşu boyunca Master ve Slave içindeki bit kayma sürecini göster
clock_ticks = list(range(9)) # 0..8
# Temsili bit ağırlıkları
master_shift_vals = [0x8F, 0x1E, 0x3D, 0x7A, 0xF5, 0xEB, 0xD6, 0xAD, 0xEA]
slave_shift_vals =  [0xEA, 0xD5, 0xAA, 0x54, 0xA8, 0x51, 0xA3, 0x47, 0x8F]

ax1.plot(clock_ticks, master_shift_vals, marker='o', color=C_CYAN, linewidth=2.5, label="Master Yazmacı (0x8F -> 0xEA)")
ax1.plot(clock_ticks, slave_shift_vals, marker='s', color=C_YELLOW, linewidth=2.5, label="Slave Yazmacı (0xEA -> 0x8F)")

ax1.scatter([0], [0x8F], color=C_CYAN, s=120, zorder=5)
ax1.scatter([8], [0xEA], color=C_GREEN, s=140, zorder=5)
ax1.annotate("Master 0xEA Aldı!", xy=(8, 0xEA), xytext=(5.5, 0xF5),
             color=C_GREEN, fontweight='bold', fontsize=9,
             arrowprops=dict(facecolor=C_GREEN, arrowstyle="->"))

ax1.set_xlabel("SCLK Saat Darbesi (Clock Ticks)", color=C_WHITE, fontsize=10)
ax1.set_ylabel("Yazmaç Değeri (Hex)", color=C_WHITE, fontsize=10)
ax1.set_title("Panel 1: SPI Full-Duplex Kaydırma Yazmaçlarının Halka Takası", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.set_xticks(clock_ticks)
ax1.set_xticklabels([f"T{i}" for i in clock_ticks], color=C_WHITE)
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax1.legend(loc='center right', fontsize=9, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 2: SPI 4 Modu (CPOL ve CPHA) Zamanlama Diyagramı
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

t_steps = np.linspace(0, 4, 400)
# Mode 0: CPOL=0 (Boşta 0), CPHA=0 (Yükselende Örnekle)
# Mode 1: CPOL=0 (Boşta 0), CPHA=1 (Düşende Örnekle)
# Mode 2: CPOL=1 (Boşta 1), CPHA=0 (Düşende Örnekle)
# Mode 3: CPOL=1 (Boşta 1), CPHA=1 (Yükselende Örnekle)

clk_m0 = np.where(np.sin(2 * np.pi * t_steps) > 0, 1.0, 0.0)
clk_m2 = 1.0 - clk_m0 # CPOL=1 terslenmiş

y_base = [3.5, 2.5, 1.5, 0.5]
ax2.plot(t_steps, clk_m0 * 0.6 + y_base[0], color=C_CYAN, linewidth=2, label="Mode 0 (CPOL=0, CPHA=0)")
ax2.plot(t_steps, clk_m0 * 0.6 + y_base[1], color=C_GREEN, linewidth=2, label="Mode 1 (CPOL=0, CPHA=1)")
ax2.plot(t_steps, clk_m2 * 0.6 + y_base[2], color=C_YELLOW, linewidth=2, label="Mode 2 (CPOL=1, CPHA=0)")
ax2.plot(t_steps, clk_m2 * 0.6 + y_base[3], color=C_PURPLE, linewidth=2, label="Mode 3 (CPOL=1, CPHA=1)")

# Örnekleme noktalarını göster (Örnek olarak Mode 0 ve Mode 3)
sample_pts_m0 = [0.0, 1.0, 2.0, 3.0]
ax2.scatter(sample_pts_m0, [y_base[0]]*4, color=C_RED, s=50, zorder=5, label="Mode 0 Örnekleme (Yükselen)")

sample_pts_m3 = [0.5, 1.5, 2.5, 3.5]
ax2.scatter(sample_pts_m3, [y_base[3] + 0.6]*4, color=C_WHITE, s=50, zorder=5, label="Mode 3 Örnekleme (Yükselen)")

ax2.set_yticks([y + 0.3 for y in y_base])
ax2.set_yticklabels(["Mode 0", "Mode 1", "Mode 2", "Mode 3"], color=C_WHITE, fontweight='bold', fontsize=9)
ax2.set_xlabel("Zaman (Periyot)", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: SPI 4 Modunun Saat Seviyeleri ve Örnekleme Noktaları", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: Çoklu-Slave Chip Select (CS) ve MISO Çekişmesi Önleme
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

time_axis = np.arange(0, 16, 1)
# CS1 (IMU): 1..5 aralığında LOW
cs1 = [1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
# CS2 (BARO): 7..11 aralığında LOW
cs2 = [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1]
# CS3 (FLASH): 13..15 aralığında LOW
cs3 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1]

ax3.step(time_axis, np.array(cs1) * 0.8 + 2.5, color=C_CYAN, where='post', linewidth=2.2, label="CS1: ADIS16488 IMU")
ax3.step(time_axis, np.array(cs2) * 0.8 + 1.3, color=C_GREEN, where='post', linewidth=2.2, label="CS2: MS5611 Barometre")
ax3.step(time_axis, np.array(cs3) * 0.8 + 0.1, color=C_YELLOW, where='post', linewidth=2.2, label="CS3: W25Q128 Flash")

# Güvenli Bölgeleri Vurgula
ax3.axvspan(1, 5, color=C_CYAN, alpha=0.15)
ax3.axvspan(7, 11, color=C_GREEN, alpha=0.15)
ax3.axvspan(13, 15, color=C_YELLOW, alpha=0.15)

ax3.set_yticks([0.5, 1.7, 2.9])
ax3.set_yticklabels(["FLASH Aktif", "BARO Aktif", "IMU Aktif"], color=C_WHITE, fontsize=9)
ax3.set_xlabel("Zaman Pencereleri (µs)", color=C_WHITE, fontsize=10)
ax3.set_title("Panel 3: Çoklu Slave Yazılımsal CS Zamanlaması (Sıfır Çekişme)", color=C_WHITE, fontsize=12, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax3.legend(loc='lower left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 4: Veri Yolu Hızı ve Bant Genişliği Karşılaştırması
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

buses = ['UART\n115.2k', 'UART\n921.6k', 'I2C\nStandard', 'I2C\nFast Mode', 'SPI\nSensör 10M', 'STM32 SPI1\nAzami 42M']
# Kilobayt / Saniye cinsinden net veri debisi
throughput_kb_s = [
    11.52,      # UART 115200 (10 bit/bayt)
    92.16,      # UART 921600
    10.0,       # I2C 100 kHz (%80 verim)
    40.0,       # I2C 400 kHz
    1250.0,     # SPI 10 MHz (10M / 8 = 1.25 MB/s)
    5250.0      # SPI 42 MHz (42M / 8 = 5.25 MB/s)
]

colors_bar = ['#64748B', '#94A3B8', C_PURPLE, '#C084FC', C_CYAN, C_GREEN]

bars = ax4.bar(buses, throughput_kb_s, color=colors_bar, alpha=0.9, width=0.55)
ax4.set_yscale('log')
ax4.set_ylabel("Efektif Veri Debisi (KB/s, Log Ölçek)", color=C_WHITE, fontsize=10)
ax4.set_title("Panel 4: Gömülü Veri Yolları Hız ve Bant Genişliği Karşılaştırması", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')

for bar in bars:
    yval = bar.get_height()
    label = f"{yval:.1f} KB/s" if yval < 1000 else f"{yval/1000:.2f} MB/s"
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval * 1.3, label, ha='center', va='bottom', color=C_WHITE, fontsize=8, fontweight='bold')

plt.suptitle("GÜN 170: SPI Clock, Chip Select ve Full-Duplex Mimari Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_170_spi_clock_chip_select_full_duplex.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_170\gun_170_spi_clock_chip_select_full_duplex.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 170 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. Shift Register Full-Duplex Assertions
sr_sim = SPIShiftRegisterExchange()
res_test = sr_sim.transfer_byte(0x55, 0xAA)
assert res_test["master_received"] == 0xAA, "Full duplex master alım hatası!"
assert res_test["slave_received"] == 0x55, "Full duplex slave alım hatası!"

# 3. SPI Modları Assertions
m0 = SPIModeSimulator(0)
assert m0.cpol == 0 and m0.cpha == 0, "Mod 0 CPOL/CPHA hatalı!"
m3 = SPIModeSimulator(3)
assert m3.cpol == 1 and m3.cpha == 1, "Mod 3 CPOL/CPHA hatalı!"

# 4. Çoklu Slave Bus Çekişme Assertions
s1 = SPISlaveDevice("S1", 1)
s2 = SPISlaveDevice("S2", 2)
bus = SPIMasterBusController([s1, s2])
bus.select_slave(0)
assert bus.check_bus_health() is True, "Tekil seçim sağlıklı olmalı!"
s2.set_cs(0) # Çift CS zorla
assert bus.check_bus_health() is False, "Bus contention yakalanmalıydı!"

# 5. Taktik IMU ve CRC-16 Assertions
imu_dev = TacticalIMUSensor()
imu_clean = imu_dev.read_burst_telemetry(inject_bit_error=False)
assert imu_clean["is_valid"] is True, "IMU CRC doğrulanamadı!"
imu_err = imu_dev.read_burst_telemetry(inject_bit_error=True)
assert imu_err["is_valid"] is False, "IMU CRC hatayı yakalayamadı!"

print("\n[PASS] Gün 170: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
```
