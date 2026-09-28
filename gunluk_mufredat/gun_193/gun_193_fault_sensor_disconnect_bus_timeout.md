# GÜN 193: Gömülü Sistem Hata Yönetimi: Sensör Bağlantı Kopması, Veriyolu Kilitlenmesi ve Zaman Aşımı (Bus Timeout)

**Faz 5:** Embedded / RTOS / STM32 (Gerçek Zamanlı Sistemler, Güvenilirlik ve Hata Kurtarma)  
**Ön Koşul:** Gün 192 — Renode ile Sanal Mikrodenetleyici (Virtual MCU) ve Donanım Emülasyonu  
**Sonraki Adım:** Gün 194 — Gömülü Sistemlerde Zamanlama, CPU Yükü ve RAM Ölçüm Teknikleri  
**Hedef Sektör:** ASELSAN, ROKETSAN, TUSAŞ, BAYKAR, TÜBİTAK SAGE (Füze Güdüm Sistemleri, İHA Uçuş Kontrol, Kritik Aviyonik)

---

### Müfredat Bilgileri ve Tasarım Kararı
Gömülü aviyonik ve savunma sistemlerinde en tehlikeli kod, **"her şeyin mükemmel çalıştığını varsayan"** koddur. Laboratuvar ortamında sorunsuz çalışan bir I2C barometre veya SPI jiroskop sensörü, gerçek bir füze veya İHA gövdesinde aşırı titreşim (vibration), yüksek G kuvveti, termal şok veya EMI (elektromanyetik girişim) altında donanımsal olarak hattan kopabilir veya veriyolunu kilitli bırakabilir.

Eğer sürücü yazılımı `while (!(I2C->SR1 & I2C_SR1_RXNE));` gibi korumasız bir döngü içeriyorsa, sensörün kopması **tüm mikrodenetleyicinin o döngüde kilitlenmesine**, diğer tüm kritik RTOS görevlerinin aç kalmasına ve nihayetinde bir hava aracının düşmesine yol açar. Bu modülde:
1. Donanımsal veriyolu kilitlenmeleri (Örn: I2C hattında slave cihazın SDA'yı `LOW` seviyesinde takılı bırakması - SDA Stuck Low),
2. Sınırlı zaman aşımı mekanizmaları (Bounded Polling & Hardware Timer Timeout),
3. 9-Darbe Veriyolu Kurtarma Protokolü (9-Clock Bus Recovery Sequence),
4. FDIR (Fault Detection, Isolation, and Recovery) durum makinesi ve yedekli sensöre kesintisiz geçiş mimarisini modelliyoruz.

```
+----------------------------------------------------------------------------------------------------+
|                         GÖMÜLÜ SİSTEM HATA VE KURTARMA (FDIR) MİMARİSİ                             |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [ FİZİKSEL KATMAN ]                  [ SÜRÜCÜ VE DENETİM ]             [ SİSTEM SEVİYESİ (FDIR) ] |
|                                                                                                    |
|  +--------------------+               +---------------------+            +-----------------------+ |
|  | Birincil IMU Sensör|               | Donanım Sürücüsü    |            | FDIR Durum Makinesi   | |
|  | (SPI1 / 1000 Hz)   | --KOPMA!---X  | Bounded Timeout     | ---------> | - Hata Tespiti (5 ms) | |
|  +--------------------+   (Floating)  | - Deadlock Engelleme|            | - İzolasyon           | |
|                                       +---------------------+            | - Yedeğe Geçiş        | |
|                                                                          +-----------------------+ |
|                                                                                      |             |
|  +--------------------+               +---------------------+                        |             |
|  | Yedek IMU Sensör   |               | Yedek Sürücü        | <----------------------+             |
|  | (SPI2 / 1000 Hz)   | ------------> | Veri Akışı Aktif    | (Sıfır Kesinti, Güdüm Devam Eder)    |
|  +--------------------+               +---------------------+                                      |
|                                                                                                    |
|  +--------------------+                                                                            |
|  | I2C Barometre      | --KİLİTLENDİ-- [ SCL 9-Clock Recovery ] ===> GPIO Bit-Bang ile Veriyolunu  |
|  | (SDA = LOW Stuck)  |                 (Kurtarma Rutini)            Yeniden Hayata Döndürme       |
|  +--------------------+                                                                            |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

> **Tasarım Kararı:** Aviyonik yazılım standartlarında (DO-178C DAL-A ve MISRA-C/C++), hiçbir donanım işlemi sonsuz bir bekleme döngüsüne (`while`) emanet edilemez. Her donanım register sorgusu katı bir zaman aşımı süresi ($T_{timeout}$) ile sınırlandırılmalı ve donanım yanıt vermediğinde sistem kilitlenmek yerine hatayı güvenli bir şekilde izole ederek yedek donanıma geçmelidir.

## 1.1 Donanımsal Hata Sınıfları ve Veriyolu Kilitlenme Anatomisi

Gömülü sistemlerde sensör ve çevre birimleri düzeyinde karşılaşılan 4 ana hata sınıfı:

### 1. I2C Veriyolu Kilitlenmesi (SDA Stuck Low)
I2C protokolünde master ve slave hatları **Açık Kollektör / Açık Savak (Open-Drain)** mimarisine sahiptir ve hatlar pull-up dirençleriyle $V_{DD}$ seviyesine çekilir.
- **Kilitlenme Senaryosu:** Master bir okuma işlemi sırasında tam slave cihaza ACK gönderirken veya slave 8-bit veri basarken bir gürültü/reset meydana gelirse, slave SDA hattını `0` (GND) seviyesinde tutmaya devam eder.
- Master işlemci donanımsal I2C periferiğini resetlese dahi, slave cihaz veriyolunu serbest bırakmadığı için tüm I2C veriyolu felç olur.

### 2. SPI MISO Yüzen Hat (Floating Line & Sentinel Values)
SPI veriyolunda sensör kablosu koptuğunda MISO pini havada kalır (floating).
- Pull-up veya pull-down direncine bağlı olarak işlemci her okumada sürekli `0xFF` veya `0x00` okur.
- Eğer yazılım `0xFF` değerini geçerli bir telemetri olarak kabul ederse, uçuş kontrol algoritması füzeyi veya uçağı aniden takla attırabilir.

### 3. CAN Bus-Off Durumu
CAN transceiver hattında fiziksel kısa devre veya aşırı gürültü olduğunda, donanımsal iletim/alım hata sayaçları (`TEC` veya `REC`) 255'i aşar ve denetleyici kendini veriyolundan izole eder (**Bus-Off State**). Otomatik kurtarma protokolü işletilmezse düğüm sonsuza kadar dilsiz kalır.

### 4. Clock Stretching Zaman Aşımı
Bazı yavaş I2C köleleri (Örn: kriptografik çipler veya gaz sensörleri), ADC çevrimini bitirene kadar SCL saat hattını `LOW` seviyesinde tutarak master'ı bekletir (Clock Stretching). Slave kilitlenirse master SCL'in serbest kalmasını beklerken donar.

```python
# Kod Hücresi 1: I2C SDA Stuck Low Kilitlenmesi ve 9-Clock Darbeli Kurtarma Algoritması
import time

class I2CSlaveDevice:
    """Sanal I2C Sensör (Arıza durumunda SDA'yı GND seviyesinde takılı bırakan köle)"""
    def __init__(self, addr):
        self.addr = addr
        self.sda_line = 1 # 1: Float/Pull-up (High), 0: GND (Low)
        self.internal_bit_counter = 0
        self.is_stuck = False

    def trigger_fault_lockup(self):
        """Donanımsal gürültü sonucu kölenin SDA'yı LOW seviyesinde kitlemesi"""
        self.is_stuck = True
        self.sda_line = 0
        self.internal_bit_counter = 4 # 8-bitlik paketin ortasında kilitlendi

    def clock_pulse(self):
        """SCL hattından gelen her saat darbesinde köle iç durumunu ilerletir"""
        if self.is_stuck:
            self.internal_bit_counter += 1
            # 9 darbe tamamlandığında köle işlemi bitirir ve SDA'yı serbest bırakır
            if self.internal_bit_counter >= 9:
                self.is_stuck = False
                self.sda_line = 1 # SDA serbest bırakıldı!

class I2CMasterController:
    """STM32 I2C Master Denetleyicisi ve GPIO Kurtarma Sürücüsü"""
    def __init__(self, slave):
        self.slave = slave
        self.bus_state = "IDLE"
        self.recovery_attempts = 0

    def read_sda(self):
        return self.slave.sda_line

    def perform_transaction(self, timeout_ticks=10):
        """Normal I2C Veri İletişimi (Bounded Polling ile)"""
        ticks = 0
        while self.read_sda() == 0:
            ticks += 1
            if ticks >= timeout_ticks:
                self.bus_state = "BUS_LOCKED_SDA_LOW"
                return False, "TIMEOUT: SDA hattı kilitli!"
        self.bus_state = "TRANSACTION_SUCCESS"
        return True, "OK"

    def execute_9_clock_recovery_sequence(self):
        """
        NXP I2C Spesifikasyonu ve STM32 AN2824 Standardı 9-Clock Darbe Kurtarma:
        1. I2C donanım modülünü kapat (I2C_CR1_PE = 0)
        2. SCL ve SDA pinlerini GPIO Open-Drain çıkışına çevir
        3. SCL hattına 9 kez HIGH-LOW saat darbesi üret (Slave iç kaydırma yazmacını boşaltsın)
        4. Her darbede SDA'yı kontrol et
        5. Sonunda STOP koşulu (SCL HIGH iken SDA'yı LOW'dan HIGH'a çek) üret
        6. I2C donanımını yeniden başlat
        """
        self.recovery_attempts += 1
        pulses_applied = 0
        
        # 9 Darbe Uygulama Döngüsü
        for i in range(1, 10):
            pulses_applied += 1
            # SCL Saat Darbesi
            self.slave.clock_pulse()
            if self.read_sda() == 1:
                # Köle SDA'yı serbest bıraktı!
                break
        
        # STOP Koşulu Üretimi (SDA LOW -> HIGH while SCL is HIGH)
        assert self.read_sda() == 1, "9 darbe sonrasında SDA hala serbest bırakılamadı!"
        self.bus_state = "RECOVERED_HEALTHY"
        return pulses_applied

# Deneyin Çalıştırılması
sensor = I2CSlaveDevice(addr=0x68)
master = I2CMasterController(sensor)

# 1. Normal Durumda İletişim
ok, msg = master.perform_transaction()
assert ok, "Normal işlem başarısız oldu!"
print(f"[OK] Normal I2C İşlemi: Durum = {master.bus_state}, Mesaj = {msg}")

# 2. Donanımsal Kilitlenme Enjeksiyonu
sensor.trigger_fault_lockup()
ok, msg = master.perform_transaction(timeout_ticks=5)
print(f"[ARIZA] Kilitlenme Algılandı: Durum = {master.bus_state}, Mesaj = {msg}")
assert not ok, "Kilitlenme tespit edilemedi!"
assert master.bus_state == "BUS_LOCKED_SDA_LOW", "Hatalı durum kodu!"

# 3. 9-Clock Kurtarma Rutininin İşletilmesi
pulses = master.execute_9_clock_recovery_sequence()
print(f"[KURTARMA] 9-Clock Darbe Rutini Tamamlandı:")
print(f"  - Uygulanan SCL Darbe Sayısı : {pulses} clock")
print(f"  - SDA Hattı Durumu           : {'HIGH (Serbest)' if master.read_sda() == 1 else 'LOW (Kilitli)'}")
print(f"  - Veriyolu Yeni Durumu       : {master.bus_state}")

assert master.read_sda() == 1, "SDA serbest değil!"
assert master.bus_state == "RECOVERED_HEALTHY", "Veriyolu sağlıklı duruma dönemedi!"
```

## 1.2 Kod Analizi ve Matematiksel Model: Bounded Timeout ve Exponential Backoff

Gömülü sistemlerde zaman aşımı sürelerinin belirlenmesi rastgele seçilemez; fiziksel veriyolu parametrelerine dayanmalıdır.

### 1. Deterministik Zaman Aşımı Hesabı (Worst-Case Execution Time - WCET)

Bir SPI veya I2C bayt transferinin maksimum süresi ($T_{transfer}$):
$$T_{transfer} = \frac{N_{bits}}{f_{clock}} + T_{processing}$$

Örnek: 100 kHz Standart Mod I2C veriyolunda 1 bayt (9 saat çevrimi):
$$T_{byte} = \frac{9}{100.000} = 90\,\mu\text{s}$$

Sensörün en fazla 5 ms clock stretching yapabildiği üretici bilgi formunda (datasheet) belirtilmişse, sürücünün kabul edeceği maksimum zaman aşımı süresi ($T_{timeout}$):
$$T_{timeout} = T_{transfer} + T_{stretch\_max} + T_{margin}$$
$$T_{timeout} = 0.09\,\text{ms} + 5.0\,\text{ms} + 1.0\,\text{ms} = 6.09\,\text{ms}$$
Eğer işlem $6.1\,\text{ms}$ içinde tamamlanmazsa, işlemcinin beklemeyi kesip hata bayrağını kaldırması **matematiksel bir zorunluluktur**.

### 2. Üstel Geri Çekilme (Exponential Backoff) Modeli

Bir çevre birimi arızalandığında sürekli tekrar denemek (tight polling) CPU'yu tüketir ve veriyolunu gürültüye boğar. Bunun yerine $k$. denemedeki bekleme süresi:
$$T_{retry}(k) = T_{base} \times 2^{\min(k, k_{max})}$$
$$T_{base} = 5\,\text{ms}, \quad k \in [0, 3] \implies 5\,\text{ms}, 10\,\text{ms}, 20\,\text{ms}, 40\,\text{ms}$$
Bu süre sonunda hata devam ediyorsa sensör **KALICI ARIZA (PERMANENT_FAULT)** durumuna geçirilir.

## 1.3 Gömülü Sistemlerdeki Yeri ve Donanım Sınırlamaları

Savunma ve havacılık standartlarında (DO-178C DAL-A/B, ARP4754A, ISO 26262 ASIL-D):
- **Tek Nokta Hata Toleransı (Single Point of Failure - SPoF):** Kritik bir sensörün (Örn: Uçuş Kontrol IMU'su) kopması durumunda hava aracı kontrolden çıkamaz.
- **Fail-Operational vs Fail-Safe:** 
  - *Fail-Safe:* Tren sinyalizasyonunda arıza olursa tren durur (güvenli durum).
  - *Fail-Operational:* Havada uçan bir İHA veya füze "duramaz"; birincil sistem çökse dahi ikincil (yedek) sistem sıfır gecikmeyle görevi devralmak zorundadır.

```
Sensör Mimarisi Karşılaştırması:
  [ Tekil Sensör (Tehlikeli) ] : [ Sensör 1 ] ----(Koparsa)----> HardFault / Kaza
  
  [ Çift Yedekli (Fail-Safe)  ] : [ Birincil ] ---X (Koptu)
                                 [ Yedek    ] --------------> FDIR Geçişi (Kesintisiz Uçuş)
```

## 2.1 Sensör Hata Durum Makinesi (Fault Management FSM)

Sensör sağlığını izlemek için 5 durumlu sonlu durum makinesi (Finite State Machine) kullanılır:

```
+------------------------------------------------------------------------------------+
|                      FDIR SENSÖR SAĞLIK DURUM MAKİNESİ                             |
+------------------------------------------------------------------------------------+
|                                                                                    |
|                [ INIT ]                                                            |
|                   |                                                                |
|                   v                                                                |
|          +-----------------+  Ardışık Başarı    +------------------+               |
|          | SENSOR_HEALTHY  | <================= | SENSOR_DEGRADED  |               |
|          +-----------------+                    +------------------+               |
|                   |                                      ^                         |
|                   | 1 Hata / Timeout                     | 1 Başarılı Yeniden      |
|                   +--------------------------------------+ Deneme                  |
|                   |                                                                |
|                   | K_fail >= 3 (Eşik Aşıldı)                                      |
|                   v                                                                |
|          +-----------------+                                                       |
|          | SENSOR_FAULT    | ===> [ YEDEK SENSÖRE GEÇİŞ (SWITCH TO REDUNDANT) ]    |
|          +-----------------+                                                       |
|                   |                                                                |
|                   | Arka Plan Bus Recovery Başarılı                                |
|                   v                                                                |
|          +-----------------+                                                       |
|          | SENSOR_RECOVERY |                                                       |
|          +-----------------+                                                       |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

- **HEALTHY:** Tüm transferler zamanında ve geçerli CRC/değer aralığında dönüyor.
- **DEGRADED:** Tekil bir timeout veya geçersiz paket alındı; retry sayacı devrede.
- **FAULT:** 3 ardışık hata oluştu. Sensör verisi geçersiz kılındı (Invalidated), FDIR yöneticisi yedek sensöre geçiş yaptı.
- **RECOVERY:** Arka planda donanımsal bus reset uygulanıyor.

```python
# Kod Hücresi 2: C++20 Yaklaşımıyla FDIR Sensör Yöneticisi ve Kesintisiz Yedekleme Motoru
from enum import Enum
import numpy as np

class SensorStatus(Enum):
    HEALTHY = 1
    DEGRADED = 2
    FAULT = 3
    RECOVERY = 4

class SimulatedImuSensor:
    """Sanal IMU Sensörü (Açısal Hız Derece/Saniye Üretir)"""
    def __init__(self, name, is_primary=True):
        self.name = name
        self.is_primary = is_primary
        self.is_connected = True
        self.read_counter = 0

    def disconnect(self):
        """Fiziksel kablo kopması simülasyonu"""
        self.is_connected = False

    def read_gyro_z(self):
        self.read_counter += 1
        if not self.is_connected:
            # Kablo koptuğunda MISO floating (0xFF / Sentinel) döner
            return None, "HARDWARE_DISCONNECT_TIMEOUT"
        
        # Normal telemetri (Örn: 50 rad/s rotasyon + gürültü)
        nominal_val = 45.0 + np.sin(self.read_counter * 0.1) * 2.0
        return nominal_val, "OK"

class FDIR_SensorManager:
    """Savunma Sanayii Seviyesinde Hata Tespit, İzolasyon ve Kurtarma Yöneticisi"""
    def __init__(self, primary_sensor, secondary_sensor):
        self.primary = primary_sensor
        self.secondary = secondary_sensor
        self.active_sensor = self.primary
        self.state = SensorStatus.HEALTHY
        self.consecutive_failures = 0
        self.MAX_ALLOWED_FAILURES = 3
        self.switchover_events = []
        self.telemetry_history = []

    def update(self):
        val, status = self.active_sensor.read_gyro_z()
        
        if status == "OK":
            self.consecutive_failures = 0
            if self.state == SensorStatus.DEGRADED:
                self.state = SensorStatus.HEALTHY
            self.telemetry_history.append((self.active_sensor.name, val))
            return val
        else:
            # Hata durumu algılandı
            self.consecutive_failures += 1
            if self.consecutive_failures < self.MAX_ALLOWED_FAILURES:
                self.state = SensorStatus.DEGRADED
                # Önceki geçerli değeri tut (Zero-Order Hold)
                last_val = self.telemetry_history[-1][1] if self.telemetry_history else 0.0
                self.telemetry_history.append((f"{self.active_sensor.name}_HOLD", last_val))
                return last_val
            else:
                # Eşik aşıldı: İzolasyon ve Yedeğe Geçiş!
                self.state = SensorStatus.FAULT
                event = f"FAILOVER: {self.active_sensor.name} koptu! {self.secondary.name} devreye alınıyor."
                self.switchover_events.append(event)
                # Sensör değişimi
                self.active_sensor = self.secondary
                self.consecutive_failures = 0
                self.state = SensorStatus.HEALTHY
                
                # Yedekten ilk okumayı yap
                new_val, _ = self.active_sensor.read_gyro_z()
                self.telemetry_history.append((self.active_sensor.name, new_val))
                return new_val

# Simülasyon Senaryosu: 50 Çevrimlik Görevde 20. Çevrimde Birincil Sensörün Kopması
primary_imu = SimulatedImuSensor("IMU_Primary_SPI1", is_primary=True)
secondary_imu = SimulatedImuSensor("IMU_Secondary_SPI2", is_primary=False)
fdir = FDIR_SensorManager(primary_imu, secondary_imu)

for cycle in range(50):
    if cycle == 20:
        # 20. Çevrimde füze titreşimiyle birincil sensör kablosu kopuyor!
        primary_imu.disconnect()
    
    gyro_reading = fdir.update()

print(f"[OK] FDIR Sensör Yöneticisi Simülasyonu Tamamlandı:")
print(f"  - Toplam Okuma Çevrimi       : 50 çevrim")
print(f"  - Tetiklenen Olaylar         : {fdir.switchover_events}")
print(f"  - Nihai Aktif Sensör         : {fdir.active_sensor.name}")
print(f"  - Nihai Durum                : {fdir.state.name}")

assert len(fdir.switchover_events) == 1, "Failover olayı gerçekleşmedi!"
assert fdir.active_sensor == secondary_imu, "Yedek sensöre geçilemedi!"
assert fdir.state == SensorStatus.HEALTHY, "Sistem sağlıklı duruma dönemedi!"
```

## 2.2 Kod Analizi & Bellek Yönetimi: Sıfır Dinamik Bellek ve Zero-Order Hold

FDIR yöneticisinde uygulanan kritik aviyonik tasarım kalıpları:

1. **Sıfır Dinamik Bellek (Zero Heap Allocation):** Sensör kopması gibi bir kriz anında işletim sisteminden `malloc` veya `new` ile bellek istemek, heap parçalanması (fragmentation) veya bellek yetersizliği durumunda ikinci bir felaket yaratır. Tüm yedek sensör nesneleri, durum değişkenleri ve hata kuyrukları **statik bellek alanında (BSS / Data segmentinde)** önceden tahsis edilmiştir.
2. **Zero-Order Hold (ZOH) Arıza Maskeleme:** Sensörün koptuğu ilk 1-2 çevrimde sistem hemen panikleyip acil durum moduna geçmez; önceki geçerli telemetri değerini dondurarak (Zero-Order Hold) güdüm algoritmasına besler. Bu sayede geçici gürültülerde uçuş dinamiği sarsılmaz.
3. **Deterministik Geçiş Süresi ($T_{switch} < 10\,\mu\text{s}$):** Yedek sensöre geçiş, yalnızca bir fonksiyon işaretçisi (function pointer) veya referans takası (`self.active_sensor = self.secondary`) ile tek bir çevrimde tamamlanır.

## 2.3 Edge Case'ler ve Kritik Hatalar: Gömülü Hata Tuzakları

| Kritik Hata | Belirti / Sonuç | Kök Neden (Root Cause) | Çözüm / Savunma |
| :--- | :--- | :--- | :--- |
| **Sonsuz Polling Kilitlenmesi** | İşlemci tamamen donar, Watchdog reset atar | Sürücünün `while (!TXE);` şeklinde timeoutsız bayrak beklemesi | Tüm döngüler donanımsal SysTick sayacıyla sınırlandırılmalıdır (`TIMEOUT_MS`). |
| **Yüzen Pin (Floating Pin) Kabulü** | Uçuş kontrolcüsü çılgınca manevra yapar | SPI MISO koptuğunda okunan `0xFF` değerinin geçerli telemetri sanılması | Değer aralığı doğrulama (Plausibility check) ve CRC-16 sağlama kuralı uygulanmalıdır. |
| **Çift Arıza (Double Fault)** | Hem birincil hem yedek sensörün kopması | Ortak güç hattı veya veriyolu fiziksel hasarı | Sistem Güvenli İniş / Paraşüt Açma (Failsafe Mode) durumuna geçmelidir. |
| **I2C Clock Stretching Deadlock** | Tüm RTOS kilitlenir | Arızalı slave'in SCL'i kalıcı olarak sıfıra çekmesi | I2C çevre biriminin dahili SMBus Timeout özelliği (`SMBTIMEOUT`) aktif edilmelidir. |

## 3.1 Watchdog Entegrasyonu ve Çok Görevli Check-In Mimarisi

Gömülü sistemlerde iki tür donanımsal bekçi köpeği (Watchdog) bulunur:
1. **Bağımsız Watchdog (IWDG):** Ana saat kaynağından bağımsız, düşük hızlı iç RC osilatörüyle (LSI - 32 kHz) çalışır. CPU ana saati dursa bile saymaya devam eder ve süre dolunca işlemciye donanımsal RESET atar.
2. **Pencere Watchdog (WWDG):** Sayacın belirli bir zaman aralığında (pencere) yenilenmesini zorunlu kılar; ne çok erken ne de çok geç beslenmelidir.

### Çok Görevli (Multi-Task) Watchdog Check-In Mimarisi

Bir RTOS sisteminde watchdog'u yalnızca tek bir periyodik görevin içine koymak **en yaygın mimari hatadır**:
- Eğer `Task_Sensors` sonsuz döngüde kilitlenirse ama `Task_Heartbeat` çalışmaya devam edip watchdog'u beslerse, sistem fiilen felç olduğu halde watchdog işlemciyi resetlemez!
- **Doğru Çözüm:** Watchdog Denetleyici Görevi (Watchdog Supervisor). Her kritik RTOS görevi periyodunu tamamladığında bir bit bayrağını (Event Flag / Bitmask) kaldırır. Watchdog Supervisor ancak **tüm görevler check-in yapmışsa** IWDG'yi besler.

```python
# Kod Hücresi 3: Çok Görevli (Multi-Task) Watchdog Supervisor ve Kilitlenme Tespiti
class MultiTaskWatchdogSupervisor:
    """Tüm RTOS Görevlerinin Senkronizasyonunu Denetleyen Watchdog Yöneticisi"""
    def __init__(self, timeout_ms=50):
        self.timeout_ms = timeout_ms
        self.registered_tasks = {}
        self.last_checkin_times = {}
        self.hardware_watchdog_counter = timeout_ms
        self.system_reset_triggered = False
        self.faulty_task_detected = None

    def register_task(self, task_name, expected_period_ms):
        self.registered_tasks[task_name] = expected_period_ms
        self.last_checkin_times[task_name] = 0

    def task_checkin(self, task_name, current_time_ms):
        """Görev periyodunu tamamladığında check-in yapar"""
        self.last_checkin_times[task_name] = current_time_ms

    def supervise_step(self, current_time_ms):
        """Watchdog yöneticisinin periyodik denetim adımı"""
        all_tasks_alive = True
        
        for task_name, expected_period in self.registered_tasks.items():
            elapsed = current_time_ms - self.last_checkin_times[task_name]
            # Beklenen periyodun 2 katı süre geçmişse görev kilitlenmiştir
            if elapsed > (expected_period * 2.0):
                all_tasks_alive = False
                self.faulty_task_detected = task_name
                break
                
        if all_tasks_alive:
            # Tüm görevler sağlıklı: Donanımsal Watchdog beslenir (Kick/Reload)
            self.hardware_watchdog_counter = self.timeout_ms
        else:
            # Donanımsal watchdog beslenmez, sayacı geri sayar!
            self.hardware_watchdog_counter -= 10
            if self.hardware_watchdog_counter <= 0:
                self.system_reset_triggered = True

# Simülasyon: 3 Görevli Aviyonik Sistem
# Task 1: Guidance (10 ms), Task 2: Sensors (20 ms), Task 3: Telemetry (50 ms)
supervisor = MultiTaskWatchdogSupervisor(timeout_ms=60)
supervisor.register_task("Task_Guidance", 10)
supervisor.register_task("Task_Sensors", 20)
supervisor.register_task("Task_Telemetry", 50)

# 1. Aşama: İlk 40 ms tüm görevler düzenli besleniyor
for t in range(0, 40, 10):
    supervisor.task_checkin("Task_Guidance", t)
    if t % 20 == 0:
        supervisor.task_checkin("Task_Sensors", t)
    if t % 50 == 0:
        supervisor.task_checkin("Task_Telemetry", t)
    supervisor.supervise_step(t)

assert not supervisor.system_reset_triggered, "Hatalı reset tetiklendi!"

# 2. Aşama: t=40 ms anında Task_Sensors I2C veriyolunda kilitleniyor (Check-in yapamıyor)
for t in range(40, 160, 10):
    supervisor.task_checkin("Task_Guidance", t)
    # Task_Sensors kilitlendi: checkin YAPMIYOR!
    if t % 50 == 0:
        supervisor.task_checkin("Task_Telemetry", t)
    supervisor.supervise_step(t)
    if supervisor.system_reset_triggered:
        print(f"[WATCHDOG RESET] Sistem {t}. ms anında Resetlendi!")
        print(f"  - Kilitlenen Görev: {supervisor.faulty_task_detected}")
        break

print(f"[OK] Multi-Task Watchdog Denetimi Başarıyla Doğrulandı:")
print(f"  - Reset Durumu       : {supervisor.system_reset_triggered}")
print(f"  - Tespit Edilen Görev: {supervisor.faulty_task_detected}")
assert supervisor.system_reset_triggered, "Watchdog sistemi resetleyemedi!"
assert supervisor.faulty_task_detected == "Task_Sensors", "Yanlış görev tespit edildi!"
```

## 3.2 Hata Enjeksiyonu ve Doğrulama: Unbounded vs Bounded Loop

Yazılım geliştiriciler genellikle "bu donanım asla bozulmaz" varsayımıyla kod yazarlar. Aşağıda, savunma sanayiinde yasaklanan **Sınırsız Döngü (Unbounded Loop)** ile zorunlu kılınan **Sınırlı Döngü (Bounded Loop)** arasındaki davranış farkı açıkça test edilmektedir.

```python
# Kod Hücresi 4: Kırılma Senaryosu: Sınırsız Polling Kilitlenmesi vs Sınırlı Timeout Sürücüsü
import time

def dangerous_unbounded_driver(hardware_ready_flag, max_sim_steps=1000):
    """
    YASAKLANMIŞ KOD (Anti-Pattern):
    while (!ready) şeklinde sonsuz döngü. Donanım yanıt vermezse CPU kilitlenir!
    """
    steps = 0
    # Gerçek donanımda while not hardware_ready_flag: pass olurdu
    while not hardware_ready_flag:
        steps += 1
        if steps >= max_sim_steps:
            # Simülasyonun donmaması için yapay kesme
            return False, "SIMULATION_DEADLOCK_DETECTED"
    return True, "SUCCESS"

def safe_bounded_driver(hardware_ready_flag, timeout_us=100, step_cost_us=10):
    """
    SAVUNMA SANAYİİ STANDARDI:
    Donanımsal saat veya çevrim sayacıyla sınırlandırılmış güvenli döngü.
    """
    elapsed_us = 0
    while not hardware_ready_flag:
        elapsed_us += step_cost_us
        if elapsed_us >= timeout_us:
            # Güvenli çıkış, hata kodu üretimi, CPU kilitlenmesi ENGELLENDİ
            return False, "ERR_HARDWARE_TIMEOUT"
    return True, "SUCCESS"

# Test Senaryosu: Sensör Fiziksel Olarak Koptu (hardware_ready_flag daima FALSE)
SENSOR_DISCONNECTED = False

# 1. Tehlikeli Sürücü Testi
deadlock_caught, dead_msg = dangerous_unbounded_driver(SENSOR_DISCONNECTED, max_sim_steps=500)
print(f"[TEST 1: TEHLİKELİ KOD] Sınırsız Döngü Sonucu:")
print(f"  - Kilitlenme Belirtisi: {dead_msg} (CPU %100 Kilitlendi)")
assert not deadlock_caught, "Tehlikeli kod kilitlenmedi!"

# 2. Güvenli Sürücü Testi
safe_ok, safe_msg = safe_bounded_driver(SENSOR_DISCONNECTED, timeout_us=80, step_cost_us=10)
print(f"[TEST 2: GÜVENLİ KOD] Sınırlı Döngü Sonucu:")
print(f"  - Kurtarma Sonucu    : {safe_msg} (CPU Kilitlenmeden Güvenle Çıkıldı)")
assert not safe_ok, "Beklenen timeout gerçekleşmedi!"
assert safe_msg == "ERR_HARDWARE_TIMEOUT", "Hatalı hata mesajı!"
```

## 3.3 Hata Analizi ve Düzeltme Stratejisi

Güvenli bir gömülü sürücü yazarken uyulması gereken 3 altın kural:
1. **Döngü Sınırlandırması (Loop Bounds):** `while` yerine sabit bir timeout sayacı (`uint32_t timeout = 10000; while (--timeout)`) veya SysTick zaman damgası (`HAL_GetTick() - start < TIMEOUT`) kullanılmalıdır.
2. **Hata Kodlarının Yukarı İletilmesi:** Sürücü fonksiyonu asla `void` olmamalıdır; C++20 `std::expected<Data, ErrorCode>` veya C enum hata kodu dönmelidir.
3. **Donanım Periferik Sıfırlaması (Software Reset):** Timeout oluştuğunda sadece fonksiyondan çıkmak yetmez; ilgili çevre biriminin kontrol yazmacındaki reset biti (Örn: `I2C_CR1_SWRST`) tetiklenerek silikon durum makinesi başlangıç durumuna getirilmelidir.

## 4.1 Savunma Sanayiinde Hata Yönetimi: ASELSAN / ROKETSAN Aviyonik Güvenlik Standartları

Füze güdüm kitlerinde (Örn: ROKETSAN MAM-L, TEBER, SOM) ve aviyonik görev bilgisayarlarında (ASELSAN):
- Füzenin uçuş süresi saniyelerle ölçülür. 500 Hz ile koşan bir seyrüsefer döngüsünde (2 ms periyot), tek bir sensörün kilitlenmesi nedeniyle 10 ms gecikme yaşanması, füzenin hedeften yüzlerce metre sapmasına yol açar.
- **MIL-STD-882E:** Her arıza senaryosu için "Ciddiyet (Severity)" ve "Olasılık (Probability)" matrisleri tanımlanır. Sensör kopması "Catastrophic" (Kritik/Ölümcül) sınıfına girer; bu nedenle sistemin çift yedekli (Dual-Redundant) donanımla desteklenmesi ve FDIR algoritmasıyla $T_{switch} < 5\,\text{ms}$ sürede yedeğe geçmesi şart koşulur.

```python
# Kod Hücresi 5: 500 Hz Roket Güdüm Döngüsünde IMU Kopması ve FDIR Kurtarma Simülasyonu
class RocketGuidanceSystem:
    """500 Hz (2 ms) Periyotlu Roket Güdüm ve FDIR Seyrüsefer Simülatörü"""
    def __init__(self):
        self.dt = 0.002 # 2 ms (500 Hz)
        self.sim_time = 0.0
        self.true_trajectory = []
        self.estimated_trajectory = []
        self.primary_imu_active = True
        self.fdir_switch_time = None
        self.altitude = 1000.0 # Başlangıç irtifası (m)
        self.velocity = 250.0  # Uçuş hızı (m/s)

    def step(self, primary_disconnected=False):
        self.sim_time += self.dt
        
        # Gerçek fiziksel hareket
        self.altitude += self.velocity * self.dt
        self.true_trajectory.append((self.sim_time, self.altitude))
        
        # Sensör okuması ve FDIR Denetimi
        if primary_disconnected:
            if self.primary_imu_active:
                # Arıza algılandı! FDIR 1 çevrimde yedeğe geçiyor (2 ms gecikmeyle)
                self.primary_imu_active = False
                self.fdir_switch_time = self.sim_time
                # Yedek sensör devreye girdi
                measured_alt = self.altitude + np.random.normal(0, 0.2) # Yedek sensör gürültüsü
            else:
                # Zaten yedek sensördeyiz
                measured_alt = self.altitude + np.random.normal(0, 0.2)
        else:
            measured_alt = self.altitude + np.random.normal(0, 0.05) # Birincil hassas sensör
            
        self.estimated_trajectory.append((self.sim_time, measured_alt))

# 100 Adımlık Uçuş Simülasyonu (200 ms)
# t = 50 ms (25. adım) anında birincil IMU kablosu kopuyor
rocket = RocketGuidanceSystem()

for step_idx in range(100):
    time_ms = step_idx * 2
    is_cut = (time_ms >= 50) # 50 ms sonrasında kablo koptu
    rocket.step(primary_disconnected=is_cut)

print(f"[OK] 500 Hz Roket Güdüm Simülasyonu Tamamlandı:")
print(f"  - Toplam Uçuş Süresi         : {rocket.sim_time * 1000:.1f} ms")
print(f"  - FDIR Yedeğe Geçiş Zamanı   : {rocket.fdir_switch_time * 1000:.1f} ms (Hedef: 52 ms)")
print(f"  - Nihai İrtifa               : {rocket.altitude:.2f} m")

# Maksimum sapma kontrolü (FDIR sayesinde sapma < 0.8 metre kalmalı)
diffs = [abs(true_pt[1] - est_pt[1]) for true_pt, est_pt in zip(rocket.true_trajectory, rocket.estimated_trajectory)]
max_error = max(diffs)
print(f"  - Maksimum Seyrüsefer Hatası : {max_error:.4f} m (Tolerans: < 1.0 m)")
assert max_error < 1.0, f"Güdüm hatası toleransı aştı: {max_error} m"
assert rocket.fdir_switch_time is not None, "FDIR yedeğe geçiş yapamadı!"
```

## 4.2 Benchmark ve Performans Çıkarımları: Timeout Stratejileri Karşılaştırması

Farklı hata yakalama ve kurtarma stratejilerinin mikrodenetleyici üzerindeki maliyet analizi:

| Strateji Türü | Kilitlenme Riski | CPU Yükü (Polling) | Algılama Gecikmesi | Kurtarma Mekanizması |
| :--- | :--- | :--- | :--- | :--- |
| **Sonsuz While Döngüsü** | **Kritik (%100 Kilitlenme)** | %100 (CPU Bloke Olur) | Algılanamaz (Sonsuz) | Yalnızca IWDG Donanımsal Reset |
| **Yazılımsal Bounded Polling** | **Sıfır** | Döngü boyunca yüksek | $10 - 100\,\mu\text{s}$ | Hata Kodu / FDIR Durum Değişimi |
| **Donanımsal Timer Kesmesi** | **Sıfır** | Sıfır (Asenkron) | Tam zamanında ($1\,\mu\text{s}$) | Otomatik ISR / DMA İptali |
| **Multi-Task Watchdog** | **Sıfır** | <%1 (Çok Düşük) | $10 - 50\,\text{ms}$ | Görev Yeniden Başlatma / Güvenli Mod |

```python
# Kod Hücresi 6: Profesyonel 4-Panelli FDIR ve Bus Timeout Performans Dashboard'u (Dark Theme)
import os
import matplotlib.pyplot as plt
import numpy as np

# Robust Fallback for PNG_FILE
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_193_fault_sensor_disconnect_bus_timeout.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_193\gun_193_fault_sensor_disconnect_bus_timeout.png"

# Renk Paleti ve Stil Ayarları (Savunma Sanayii Karanlık Tema)
plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.grid(True, linestyle='--', alpha=0.3, color='#64748B')
    ax.tick_params(colors='#CBD5E1', labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#475569')

# ------------------------------------------------------------------------------
# PANEL 1: I2C 9-Clock Darbeli Kurtarma Zaman Çizelgesi (SCL Toggling & SDA Release)
# ------------------------------------------------------------------------------
time_steps = np.arange(0, 14, 1)
scl_wave = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1]
# SDA 5. clock darbesine kadar 0'da takılı, sonra serbest kalıp 1 oluyor, sonunda STOP koşulu
sda_wave = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1]

axs[0, 0].step(time_steps, scl_wave, where='post', color='#38BDF8', linewidth=2.5, label='SCL (Master 9-Clock)')
axs[0, 0].step(time_steps, [s - 1.5 for s in sda_wave], where='post', color='#F59E0B', linewidth=2.5, label='SDA (Slave Stuck -> Released)')
axs[0, 0].axvline(8, color='#10B981', linestyle='--', linewidth=1.5, label='SDA Serbest (8. Darbe)')
axs[0, 0].axvline(12, color='#EC4899', linestyle=':', linewidth=1.5, label='STOP Koşulu')

axs[0, 0].set_title("Panel 1: I2C 9-Clock Veriyolu Kurtarma Protokolü (SDA Stuck Low)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[0, 0].set_yticks([-1.5, -0.5, 0, 1])
axs[0, 0].set_yticklabels(['SDA LOW', 'SDA HIGH', 'SCL LOW', 'SCL HIGH'], fontsize=8)
axs[0, 0].set_xlabel("Saat Çevrim Adımı (Clock Pulses)", fontsize=9, color='#CBD5E1')
axs[0, 0].legend(loc='lower right', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

# ------------------------------------------------------------------------------
# PANEL 2: FDIR Reaksiyon Zaman Çizelgesi ve İrtifa Takibi (500 Hz Füze Güdümü)
# ------------------------------------------------------------------------------
sim_t_ms = np.linspace(0, 100, 50)
alt_ideal = 1000 + 250 * (sim_t_ms / 1000.0)
alt_measured = alt_ideal + np.random.normal(0, 0.15, size=len(sim_t_ms))
# 50 ms'de kopma
alt_measured[sim_t_ms >= 50] += np.random.normal(0, 0.35, size=np.sum(sim_t_ms >= 50))

axs[0, 1].plot(sim_t_ms, alt_ideal, color='#94A3B8', linestyle=':', linewidth=2, label='Gerçek Uçuş Rotası')
axs[0, 1].plot(sim_t_ms, alt_measured, color='#38BDF8', linewidth=2, label='FDIR IMU Seyrüsefer Verisi')
axs[0, 1].axvline(50, color='#EF4444', linestyle='--', linewidth=2, label='Kablo Kopması (t=50 ms)')
axs[0, 1].axvline(52, color='#10B981', linestyle='-', linewidth=2, label='Yedek Sensör Aktif (t=52 ms)')

axs[0, 1].set_title("Panel 2: FDIR Reaksiyonu: Birincil Kopma ve Kesintisiz Yedeğe Geçiş", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[0, 1].set_xlabel("Uçuş Süresi (Milisaniye - ms)", fontsize=9, color='#CBD5E1')
axs[0, 1].set_ylabel("İrtifa (Metre - m)", fontsize=9, color='#CBD5E1')
axs[0, 1].legend(loc='upper left', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

# ------------------------------------------------------------------------------
# PANEL 3: Timeout Stratejileri Karşılaştırması: Kurtarma Süresi ve Güvenilirlik
# ------------------------------------------------------------------------------
strategies = ['Sonsuz While\n(Yasak)', 'Yazılımsal\nPolling', 'Timer\nTimeout', 'Multi-Task\nWatchdog']
recovery_latency_us = [999999, 45, 12, 50000] # Logaritmik ölçek için
colors_bar = ['#EF4444', '#F59E0B', '#10B981', '#38BDF8']

bars = axs[1, 0].bar(strategies, recovery_latency_us, color=colors_bar, width=0.5, edgecolor='#FFFFFF', linewidth=0.5, alpha=0.85)
axs[1, 0].set_yscale('log')
axs[1, 0].set_title("Panel 3: Hata Kurtarma Gecikmesi Karşılaştırması (µs - Log Ölçek)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[1, 0].set_ylabel("Kurtarma Gecikmesi (µs)", fontsize=9, color='#CBD5E1')

for bar in bars:
    yval = bar.get_height()
    label = f"{int(yval):,} µs" if yval < 900000 else "SONSUZ / CRASH"
    axs[1, 0].text(bar.get_x() + bar.get_width()/2.0, yval * 1.5, label, ha='center', va='bottom', fontsize=8, color='#F8FAFC', fontweight='bold')

# ------------------------------------------------------------------------------
# PANEL 4: Multi-Task Watchdog Supervisor Check-In Monitörü
# ------------------------------------------------------------------------------
tasks = ['Guidance (10ms)', 'Sensors (20ms)', 'Telemetry (50ms)']
last_seen_delays = [8, 48, 42] # Sensors 48 ms gecikmiş (Periyot 20 ms -> Kilitlendi!)
thresholds = [20, 40, 100]

x_indices = np.arange(len(tasks))
axs[1, 1].bar(x_indices - 0.15, last_seen_delays, width=0.3, label='Geçen Süre (ms)', color='#F59E0B', alpha=0.85)
axs[1, 1].bar(x_indices + 0.15, thresholds, width=0.3, label='Timeout Eşiği (ms)', color='#EF4444', alpha=0.6)

axs[1, 1].set_xticks(x_indices)
axs[1, 1].set_xticklabels(tasks, fontsize=9)
axs[1, 1].set_title("Panel 4: Watchdog Supervisor: Görev Check-in Durumu & Arıza Tespiti", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[1, 1].set_ylabel("Milisaniye (ms)", fontsize=9, color='#CBD5E1')
axs[1, 1].legend(loc='upper left', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

plt.tight_layout()
fig.subplots_adjust(top=0.92)
fig.suptitle("ASELSAN / ROKETSAN GÖMÜLÜ SİSTEMLER — GÜN 193: FAULT: SENSOR DISCONNECT VE BUS TIMEOUT YÖNETİMİ", 
             fontsize=13, fontweight='bold', color='#F8FAFC')

# Kaydetme ve Boyut Doğrulama
os.makedirs(os.path.dirname(PNG_FILE), exist_ok=True)
plt.savefig(PNG_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(PNG_FILE) / 1024
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {PNG_FILE}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100, f"Görsel boyutu yetersiz: {file_size_kb:.2f} KB"
```

## 4.3 Endüstriyel Pratikler ve Anti-Pattern'ler

### En İyi Mühendislik Pratikleri (DO's)
1. **Daima Bounded Timeout Kullanın:** Donanımsal çevresel birimlerin register bayraklarını beklerken (`RXNE`, `TXE`, `TC`) mutlaka kesin bir çevrim veya zaman aşımı sınırı koyun.
2. **I2C Hat Kurtarma Fonksiyonu Ekleyin:** Kart açılışında (`SystemInit` / `MX_I2C_Init`) I2C çevresel birimini açmadan önce SDA hattını GPIO olarak okuyun; eğer SDA `LOW` ise doğrudan 9-clock kurtarma darbesi uygulayın.
3. **Plausibility (Mantıklılık) Filtresi:** Sensörden gelen telemetrinin yalnızca fiziksel olarak mümkün olan aralıkta olup olmadığını (Örn: Füze ivmesi $-50\text{g}$ ile $+50\text{g}$ arası) kontrol edin; kopma durumundaki `0x00` ve `0xFF` değerlerini filtreleyin.

### Kaçınılması Gereken Hatalar (DON'Ts - Anti-Patterns)
1. **Sonsuz `while` Döngüleri:** `while (SPI1->SR & SPI_SR_BSY);` gibi korumasız döngüler yazmak, sahada donanımın tek bir gürültüde kilitlenmesine davetiye çıkarır.
2. **Watchdog'u Tek Göreve Emanet Etmek:** Tüm sistem kilitlenirken watchdog'u beslemeye devam eden bağımsız bir timer kesmesi yazmayın (Watchdog Masking Anti-Pattern).
3. **Hataları Sessizce Yutmak (Silent Failure):** Zaman aşımı olduğunda bunu loglamadan veya FDIR durum makinesine bildirmeden sadece `return 0;` demek sistemin kör uçuş yapmasına neden olur.

## 4.4 Mülakat Soruları ve Yanıtları

### Soru 1: I2C veriyolunda "SDA Stuck Low" kilitlenmesi neden meydana gelir ve yazılımla nasıl kurtarılır?
**Cevap:** I2C açık-kollektör (open-drain) yapıda çalıştığı için hat ancak tüm cihazlar çekmeyi bıraktığında `HIGH` olur. Eğer master tam bir veri okurken slave 0 (ACK veya veri biti) basarken master reset yerse veya haberleşme kesilirse, slave bir sonraki saat darbesini bekleyerek SDA hattını sürekli GND seviyesine çeker. Donanım I2C modülü SDA'yı serbest bırakamaz çünkü veriyolunu meşgul görür. Çözüm: Master SCL ve SDA pinlerini geçici olarak GPIO çıkışına alır; SCL pinine el ile (bit-banging) en fazla 9 adet saat darbesi basar. Slave her darbede iç kaydırma yazmacını ilerletir, 9 darbe dolunca işlemi tamamlayıp SDA'yı serbest bırakır. Master ardından bir STOP koşulu üreterek I2C donanım modülünü yeniden başlatır.

### Soru 2: FDIR (Fault Detection, Isolation, and Recovery) mimarisinde "İzolasyon" aşaması ne anlama gelir?
**Cevap:** İzolasyon, arızalanan veya hatalı veri üreten bir bileşenin sistemin geri kalanını etkilemesini engelleme sürecidir. Örneğin arızalanan bir birincil IMU sensörünün SPI Chip Select hattı devre dışı bırakılır, ilgili kesmeler (IRQ) NVIC üzerinde kapatılır, DMA kanalları durdurulur ve sensör füzyon algoritmasında (Kalman Filtresi) o sensörün güvenilirlik ağırlığı sıfırlanır. Böylece arızalı sensörün sisteme çöp veri basması engellenir.

### Soru 3: Bağımsız Watchdog (IWDG) ile Pencere Watchdog (WWDG) arasındaki kullanım farkı nedir?
**Cevap:** IWDG, ana osilatör çökse dahi dahili bağımsız düşük hızlı osilatörle (LSI 32 kHz) çalışır ve işlemcinin tamamen kilitlendiği (deadlock) durumlarda sistemi resetlemek için kullanılır. WWDG ise ana sistem saatine (PCLK1) bağlıdır ve sayacın sadece belirli bir zaman penceresi içinde (ne çok erken ne çok geç) yenilenmesini denetler. Kodun beklenenden hızlı çalışıp bir döngüyü atlaması veya sonsuz hızlı bir döngüye girmesi gibi mantıksal hataları yakalamakta WWDG tercih edilir.

## 4.5 Bilgi Kontrolü (Self-Check Test)

### 1. I2C veriyolunda SDA hattı köle (slave) tarafından LOW seviyesinde kilitlendiğinde hangi standart kurtarma yöntemi uygulanır?
- A) Mikrodenetleyiciye 12V aşırı gerilim uygulamak
- B) SCL pininden en fazla 9 adet saat darbesi basarak slave'in kaydırma yazmacını boşaltmak
- C) Veriyolu pull-up dirençlerini sökmek
- D) SPI moduna geçmek
*Cevap: B. 9-clock pulse yöntemi NXP I2C spesifikasyonunda tanımlı resmi kurtarma protokolüdür.*

### 2. Havada uçan bir füze veya İHA sisteminde kritik sensör koptuğunda sistemin hangi felsefeyle tasarlanmış olması gerekir?
- A) Fail-Safe (Derhal motorları durdurup kapanma)
- B) Fail-Operational (Yedek sensöre kesintisiz geçerek görevi sürdürme)
- C) Best-Effort (Rastgele değerlerle uçuşa devam etme)
- D) Manual Override (Yalnızca yer istasyonundan komut bekleme)
*Cevap: B. Havada durma imkanı olmayan araçlar Fail-Operational olmak zorundadır.*

### 3. SPI MISO hattı fiziksel olarak koptuğunda (Floating) işlemci genellikle hangi hatalı sabit değeri okur?
- A) Yalnızca 0x55
- B) Pull-up/pull-down durumuna göre sürekli 0xFF veya 0x00
- C) Asla veri okunamaz, işlemci anında HardFault verir
- D) 3.1415
*Cevap: B. Boşta kalan hat pull-up varsa 0xFF, pull-down varsa 0x00 olarak okunur.*

### 4. Çok görevli (Multi-Task) bir RTOS sisteminde Watchdog nasıl beslenmelidir?
- A) Sadece en yüksek öncelikli görevde periyodik olarak
- B) Bir hardware timer kesmesinde arka planda otomatik olarak
- C) Watchdog Supervisor aracılığıyla, tüm kritik görevler periyotlarında check-in yapmışsa
- D) Hiçbir zaman beslenmemelidir
*Cevap: C. Tek görevin beslemesi diğer görevlerin kilitlenmesini gizler; Supervisor tüm görevleri denetlemelidir.*

### 5. MISRA-C ve DO-178C standartlarına göre donanımsal bayrak beklemelerinde hangi yaklaşım yasaktır?
- A) SysTick tabanlı zaman aşımı
- B) Donanımsal timer kesmesi
- C) Sınırsız `while (!ready);` döngüsü
- D) C++20 `std::expected` kullanımı
*Cevap: C. Sınırsız döngüler donanım kilitlenmesinde işlemciyi bloke ettiği için kesinlikle yasaktır.*

## 4.6 Günün Sözü ve Düşünce Sorusu

> *"Kusursuz donanım yoktur; yalnızca henüz kilitlenmemiş veriyolları ve henüz kopmamış kablolar vardır. Güvenilirlik, arızanın gerçekleşmeyeceğini ummak değil, gerçekleştiğinde sistemin nasıl hayatta kalacağını tasarlamaktır."*

### Düşünce Sorusu
Bir aviyonik uçuş bilgisayarında birincil ve ikincil IMU sensörleri aynı SPI veriyolunu (SPI1) paylaşıyorsa, birincil sensörün silikon düzeyinde kısa devre yapması durumunda yedek sensör sistemi kurtarabilir mi?
**Cevap:** Hayır. Eğer her iki sensör aynı fiziksel SPI veriyoluna bağlıysa, birincil sensörün SCK veya MISO hattını GND'ye kısa devre etmesi tüm veriyolunu çökerteceğinden yedek sensör de çalışamaz hale gelir. Gerçek aviyonik mimarilerde (DO-178C DAL-A), birincil sensör `SPI1`'e, yedek sensör ise tamamen bağımsız bir donanımsal çevre birimi olan `SPI2`'ye bağlanır (Tam Donanımsal İzolasyon).

## 5.1 İleri Düzey Okuma ve Kaynakça

1. **NXP Semiconductors:** *UM10204: I2C-bus specification and user manual (Rev. 7.0).*
2. **STMicroelectronics Application Note:** *AN2824: I2C bus recovery and debugging on STM32 microcontrollers.*
3. **NASA Office of Safety and Mission Assurance:** *NASA Fault Management Handbook (NASA-HDBK-1002).*
4. **RTCA DO-178C / EUROCAE ED-12C:** *Software Considerations in Airborne Systems and Equipment Certification.*
5. **MISRA C:2012 Guidelines:** *Rule 14.3 - Controlling expressions shall not be invariant.*

## 5.2 Gün Sonu Özeti ve Özel Lisans

### Günün Özeti (3 Cümlelik Kural)
1. **Fault: Sensor Disconnect / Bus Timeout Nedir?:** Titreşim, gürültü veya donanımsal arıza sonucu sensör kablosunun kopması veya veriyolunun kilitlenmesi (Örn: I2C SDA Stuck Low) durumunda işlemcinin bloke olmasını engelleyen hata yönetimidir.
2. **Hangi Problemi Çözer?:** Sürücülerin korumasız `while` döngülerinde kilitlenerek tüm RTOS görevlerini ve aviyonik uçuş döngüsünü felç etmesini önler.
3. **Hangi Trade-off / Hata Sınıfını Getirir?:** Zaman aşımı süresi çok kısa seçilirse geçici gürültülerde yanlış pozitif arıza üretilir; çok uzun seçilirse sistemin kurtarma tepkisi gecikir.

---

### Özel Lisans Uyarısı

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

