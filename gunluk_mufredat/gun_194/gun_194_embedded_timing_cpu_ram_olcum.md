# GÜN 194: Gömülü Sistemlerde Deterministik Zamanlama (Timing), CPU Yükü ve RAM/Stack Profilleme

**Faz 5:** Embedded / RTOS / STM32 (Gerçek Zamanlı Sistemler, Profilleme ve Kaynak Yönetimi)  
**Ön Koşul:** Gün 193 — Gömülü Sistem Hata Yönetimi: Sensör Bağlantı Kopması ve Veriyolu Zaman Aşımı  
**Sonraki Adım:** Gün 195 — Gömülü Mini-Capstone: Aviyonik Sensör Ağ Geçidi (Sensor Gateway)  
**Hedef Sektör:** ASELSAN, ROKETSAN, TUSAŞ, HAVELSAN, TÜBİTAK BİLGEM (Kritik Görev Aviyonikleri, Radar Sinyal İşleme, EKF Seyrüsefer)

---

### Müfredat Bilgileri ve Tasarım Kararı
Gerçek zamanlı aviyonik ve savunma sistemlerinde bir yazılımın **"doğru sonucu üretmesi"** tek başına hiçbir anlam ifade etmez; o sonucun **"belirlenen katı süre (deadline) içinde ve sistem kaynaklarını (CPU/RAM) tüketmeden üretilmesi"** zorunludur. Füze seyrüsefer filtresi doğru açısal hızı hesaplasa bile, hesaplama 2 ms yerine 2.5 ms sürerse füze dengesini kaybedip rotadan çıkar.

Bu modülde:
1. **Çevrim-Doğru (Cycle-Accurate) Zamanlama:** ARM Cortex-M DWT (Data Watchpoint and Trace) `CYCCNT` 32-bit çekirdek çevrim sayacı ve osiloskop/lojik analizör pin sallama (GPIO Toggling) teknikleri,
2. **CPU Yükü ve Görev Profilleme:** FreeRTOS Idle Task Hook ve Hardware Timer tabanlı görev çalışma zamanı istatistikleri (`vTaskGetRunTimeStats`),
3. **Bellek Güvenliği ve Yığın (Stack) Profilleme:** Stack Watermarking (`0xA5A5A5A5` stack boyama), Linker Script segmentleri (`.text`, `.rodata`, `.data`, `.bss`) ve Heap fragmentasyon analizini modelliyoruz.

```
+----------------------------------------------------------------------------------------------------+
|                      GÖMÜLÜ SİSTEM ZAMANLAMA, CPU VE RAM PROFİLLEME MİMARİSİ                       |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  +----------------------------------------------------------------------------------------------+  |
|  | DONANIMSAL ZAMANLAMA KATMANI (HARDWARE TIMING LAYER)                                         |  |
|  | - ARM Cortex-M DWT->CYCCNT : 32-bit Çekirdek Saat Çevrim Sayacı (Nanosaniye Çözünürlük)      |  |
|  | - GPIO Toggling            : Sıfır-Gecikmeli Fiziksel Ölçüm Probu (Osiloskop / Lojik Analizör)|  |
|  | - Hardware Timer (TIM2)    : 1 MHz Bağımsız Mikro-saniye Sayacı                              |  |
|  +----------------------------------------------------------------------------------------------+  |
|                 |                                             |                                    |
|                 v                                             v                                    |
|  +---------------------------------------+   +--------------------------------------------------+  |
|  | RTOS CPU YÜKÜ VE GÖREV PROFİLLEME     |   | RAM VE YIĞIN (STACK/HEAP) ANALİZÖRÜ              |  |
|  | - Total Execution Time (WCET vs BCET) |   | - Stack Watermark: 0xA5A5A5A5 Boyama Deseni      |  |
|  | - Task CPU Utilization (%)            |   | - High Water Mark: Kalan Minimum Yığın Boşluğu   |  |
|  | - Idle Hook Metodu: U = 1 - (Idle/Tot)|   | - Heap Fragmentasyon Oranı & Linker Segmentleri  |  |
|  +---------------------------------------+   +--------------------------------------------------+  |
|                 |                                             |                                    |
|                 +----------------------+----------------------+                                    |
|                                        v                                                           |
|                 [ DO-178C / MIL-STD-882E ZAMANLAMA VE GÜVENLİK KANITI ]                            |
|                 - CPU Yükü <= %70 (Tavan Güvenlik Marjı)                                           |
|                 - Deadline İhlali = 0 (Sıfır Kaçırılan Görev)                                      |
|                 - Stack Güvenlik Marjı >= %30                                                      |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

> **Tasarım Kararı:** `printf` veya yazılımsal loglama gibi ağır I/O fonksiyonları ile zaman ölçmeye çalışmak sistemi yavaşlatarak hatayı gizler (Heisenberg Etkisi / Heisenbug). Aviyonik sistemlerde zamanlama daima donanımsal DWT sayaçları veya fiziksel GPIO pin seviyesi değişimleriyle sıfır ek yükle (zero overhead) ölçülür.

## 1.1 DWT CYCCNT, GPIO Toggling ve Hardware Timer ile Zaman Ölçümü

Gömülü sistemlerde zamanlama ölçümü için kullanılan üç temel donanımsal mekanizma:

### 1. DWT (Data Watchpoint and Trace) CYCCNT Sayacı
ARM Cortex-M3/M4/M7/M33 çekirdeklerinde bulunan CoreDebug ve DWT birimi, işlemcinin her saat darbesinde (clock cycle) 1 artan 32-bitlik bağımsız bir sayaca (`DWT->CYCCNT`) sahiptir.
- **Etkinleştirme:**
  ```c
  CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk; // Trace birimini aç
  DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;           // CYCCNT sayacını başlat
  ```
- **Zaman Dönüşümü:** 168 MHz çalışan bir STM32F4'te her çevrim $5.95\,\text{ns}$ sürer:
  $$\Delta t = \frac{\Delta \text{CYCCNT}}{f_{cpu}} = \frac{\text{Stop} - \text{Start}}{168.000.000}\,\text{s}$$
- **Kritik Kısıt:** 32-bit sayaç 168 MHz'de yaklaşık **25.56 saniyede bir taşar (overflow)**. Uzun süreli ölçümlerde taşma sayısı yazılımla takip edilmelidir.

### 2. GPIO Pin Toggling (Fiziksel Prob Yöntemi)
Kodun başladığı yerde bir GPIO pinini `HIGH` yapmak, bittiği yerde `LOW` yapmak:
```c
GPIOC->BSRR = GPIO_PIN_13;       // 1 çevrim (Pin HIGH)
Critical_Guidance_Algorithm();
GPIOC->BSRR = (GPIO_PIN_13 << 16); // 1 çevrim (Pin LOW)
```
- **Ek Yük (Overhead):** Yalnızca 2 makine komutu (~12 ns). Kodun yürütme dinamiğini bozmaz.
- Osiloskop veya 100 MHz lojik analizör ile ölçülerek deterministik sinyal genişliği ve jitter izlenir.

### 3. Bağımsız Donanım Zamanlayıcısı (Hardware Timer - TIM2/TIM5)
32-bit genel amaçlı bir timer 1 MHz frekansta çalıştırılarak ($1\,\mu\text{s}$ çözünürlük) RTOS görev süreleri ölçülür.

```python
# Kod Hücresi 1: ARM Cortex-M DWT CYCCNT ve GPIO Pin Toggling Zamanlama Ölçüm Motoru
import numpy as np

class CortexM_DWT:
    """ARM Cortex-M DWT->CYCCNT 32-bit Çevrim Sayacı Simülatörü"""
    def __init__(self, core_clock_hz=168_000_000):
        self.clock_hz = core_clock_hz
        self.cyccnt = 0
        self.is_enabled = False
        self.overflow_count = 0

    def enable(self):
        self.is_enabled = True
        self.cyccnt = 0

    def advance_cycles(self, cycles):
        assert self.is_enabled, "DWT birimi aktif değil!"
        prev = self.cyccnt
        self.cyccnt = (self.cyccnt + cycles) & 0xFFFFFFFF
        if self.cyccnt < prev:
            self.overflow_count += 1

    def get_cycles(self):
        return self.cyccnt

    def cycles_to_time_us(self, cycles):
        return (cycles / self.clock_hz) * 1_000_000.0

class VirtualGpioPin:
    """Lojik Analizör Probu için GPIO Çıkış Pini"""
    def __init__(self, pin_name):
        self.name = pin_name
        self.state = 0 # 0: LOW, 1: HIGH
        self.transitions = [] # (timestamp_cycles, state)

    def set_high(self, current_cycles):
        self.state = 1
        self.transitions.append((current_cycles, 1))

    def set_low(self, current_cycles):
        self.state = 0
        self.transitions.append((current_cycles, 0))

# Simülasyon: Aviyonik Kalman Filtresi Algoritmasının 100 Kez Yürütülmesi
dwt = CortexM_DWT(core_clock_hz=168_000_000) # 168 MHz STM32F4
dwt.enable()

probe_pin = VirtualGpioPin("PC13_ISR_PROBE")
execution_cycles_log = []

# Nominal çevrim: 2500 çevrim (~14.88 µs) + önbellek kaçırma ve dal dallanma jitter'ı
np.random.seed(42)
for i in range(100):
    start_cyc = dwt.get_cycles()
    probe_pin.set_high(start_cyc)
    
    # Simüle edilen algoritma süresi (Jitter: Normal dağılım)
    alg_cycles = int(np.random.normal(loc=2500, scale=85))
    dwt.advance_cycles(alg_cycles)
    
    stop_cyc = dwt.get_cycles()
    probe_pin.set_low(stop_cyc)
    
    elapsed = (stop_cyc - start_cyc) & 0xFFFFFFFF
    execution_cycles_log.append(elapsed)

cycles_arr = np.array(execution_cycles_log)
times_us = (cycles_arr / 168_000_000.0) * 1_000_000.0

bcet_us = np.min(times_us)
wcet_us = np.max(times_us)
avg_us = np.mean(times_us)
jitter_us = wcet_us - bcet_us

print(f"[OK] DWT CYCCNT ve GPIO Problama Testi Başarıyla Tamamlandı:")
print(f"  - İşlemci Frekansı      : {dwt.clock_hz / 1e6:.0f} MHz")
print(f"  - En İyi Süre (BCET)    : {bcet_us:.3f} µs ({np.min(cycles_arr)} cycles)")
print(f"  - Ortalama Süre (AVG)   : {avg_us:.3f} µs ({int(np.mean(cycles_arr))} cycles)")
print(f"  - En Kötü Süre (WCET)   : {wcet_us:.3f} µs ({np.max(cycles_arr)} cycles)")
print(f"  - Jitter Genişliği      : {jitter_us:.3f} µs")
print(f"  - GPIO Geçiş Sayısı     : {len(probe_pin.transitions)} edge")

assert wcet_us < 20.0, "WCET bütçesi (20 µs) aşıldı!"
assert bcet_us > 10.0, "BCET beklenenden düşük!"
```

## 1.2 Kod Analizi ve Matematiksel Model: WCET, BCET ve Jitter Dağılımı

Gerçek zamanlı sistem analizinde üç temel süre metriği tanımlanır:

### 1. Yürütme Süreleri
- **BCET (Best-Case Execution Time):** Tüm koşullu dallanmaların en hızlı yoldan aktığı, önbelleğin (L1 I/D Cache) tam isabet aldığı en kısa yürütme süresi.
- **ACET (Average-Case Execution Time):** İstatistiksel ortalama yürütme süresi.
- **WCET (Worst-Case Execution Time):** Tüm döngülerin maksimum adımda döndüğü, tüm interrupt'ların üst üste bindiği en kötü yürütme süresi:
  $$\text{WCET} = \max_{x \in Inputs} \{ T_{exec}(x) \}$$

### 2. Jitter (Zaman Dalgalanması)
$$J = \text{WCET} - \text{BCET}$$
Aviyonik uçuş kontrol sistemlerinde $J$ değerinin görev periyoduna ($T_{period}$) oranı kritik bir parametredir:
$$\text{Jitter Oranı} = \frac{J}{T_{period}} \le 0.05\, (\%5\text{'ten küçük olmalıdır})$$

### 3. Heisenberg Ölçüm İlkesi (Probe Overhead)
Bir koda zamanlama ölçümü için eklenen her komut, kodun kendi süresini uzatır.
- `DWT->CYCCNT` okuması: 1 saat çevrimi ($5.95\,\text{ns}$). İhmal edilebilir.
- `printf("%d", timer);`: Yaklaşık **15.000 saat çevrimi (~90 µs)**. Sistemin zamanlamasını tamamen bozar! Bu nedenle gömülü sistemlerde profil loglaması UART/DWT tamponu ile RAM'de tutulur ve ancak test bittiğinde dışarı basılır.

## 1.3 Gömülü Sistemlerdeki Yeri ve Donanım Sınırlamaları

Savunma ve aviyonik standartlarında (DO-178C, FAA CAST-32A, ISO 26262):

### 1. %70 CPU Tavan Kuralı (The 70% CPU Utilization Rule)
Gerçek zamanlı bir mikrodenetleyicinin toplam CPU yükünün **nominal koşullarda %70'i geçmemesi** şart koşulur. Kalan %30'luk marj:
- Beklenmeyen kesme fırtınaları (Interrupt Bursts),
- DMA bus contention (veriyolu çekişmesi),
- Hata kurtarma (FDIR) algoritmalarının devreye girmesi durumunda sistemin kilitlenmesini engellemek için ayrılmış güvenlik tamponudur.

### 2. Stack Sınırları ve Statik Analiz
Cortex-M'de yığın (Stack) yüksek bellek adresinden düşük bellek adresine doğru büyür (Full Descending Stack). Yığın taşarsa (Stack Overflow), altta duran `.bss` veya `.data` segmentindeki global değişkenlerin üzerine yazar; bu da sistemde tespiti imkansız sessiz veri bozulmalarına (Memory Corruption) yol açar.

## 2.1 RTOS CPU Yükü Ölçümü: Idle Task Hook vs Run-Time Stats

FreeRTOS veya Zephyr gibi bir RTOS altında CPU yükünü ölçmenin en zarif yolu **Boşta Görevi (Idle Task)** izlemektir.

```
+------------------------------------------------------------------------------------+
|                         RTOS CPU YÜKÜ VE IDLE HOOK MEKANİZMASI                     |
+------------------------------------------------------------------------------------+
|                                                                                    |
|  ZAMAN EKSENİ (100 ms Pencere):                                                    |
|  +------------------+---------+------------------+---------+--------------------+  |
|  | Task_Guidance    | IDLE    | Task_Radar       | IDLE    | Task_Telemetry     |  |
|  | (30 ms)          | (15 ms) | (25 ms)          | (15 ms) | (15 ms)            |  |
|  +------------------+---------+------------------+---------+--------------------+  |
|                                                                                    |
|  Toplam Aktif Çalışma = 30 + 25 + 15 = 70 ms                                       |
|  Toplam Boşta Kalma   = 15 + 15 = 30 ms                                            |
|  CPU Yükü (Utilization) = (100 - 30) / 100 = %70.0                                 |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

### 1. Idle Hook Sayacı Yöntemi
İşlemci yapacak hiçbir iş bulamadığında en düşük öncelikli `Idle Task` çalışır. Bu görevin içine bir sayaç konur:
```c
void vApplicationIdleHook(void) {
    ulIdleCycleCount++; // Boşta geçen çevrim sayacı
}
```
1 saniyelik bir timer kesmesinde bu sayacın değeri okunur:
$$\text{CPU Yükü (\%)} = 100 \times \left(1 - \frac{\text{ulIdleCycleCount}}{\text{ulMaxIdleCycles}}\right)$$

### 2. FreeRTOS Run-Time Stats (`configGENERATE_RUN_TIME_STATS = 1`)
RTOS her bağlam değişiminde (`vTaskSwitchContext`) yüksek çözünürlüklü bir donanım sayacından o görevin çalıştığı süreyi biriktirir. `vTaskGetRunTimeStats()` çağrıldığında her görevin harcadığı mutlak zaman ve yüzde tablosu üretilir.

```python
# Kod Hücresi 2: FreeRTOS Benzeri Görev CPU Yükü (Task Utilization) ve Idle Hook Profilleyici
class VirtualRTOSTask:
    """RTOS Görev Kontrol Bloğu (TCB) Profilleme Eklentisi"""
    def __init__(self, name, priority, period_ms, wcet_ms):
        self.name = name
        self.priority = priority
        self.period_ms = period_ms
        self.wcet_ms = wcet_ms
        self.total_runtime_us = 0
        self.execution_count = 0

class VirtualRTOSScheduler:
    """Deterministik RTOS Profilleme ve İstatistik Motoru"""
    def __init__(self):
        self.tasks = []
        self.idle_runtime_us = 0
        self.total_elapsed_us = 0

    def register_task(self, task):
        self.tasks.append(task)

    def simulate_timeline(self, duration_ms=1000):
        self.total_elapsed_us = duration_ms * 1000
        
        # Görevlerin periyodik tetiklenme ve WCET tüketimlerinin hesaplanması
        for task in self.tasks:
            task.execution_count = duration_ms // task.period_ms
            task.total_runtime_us = task.execution_count * int(task.wcet_ms * 1000)
            
        total_active_us = sum(t.total_runtime_us for t in self.tasks)
        assert total_active_us <= self.total_elapsed_us, "Aşırı yükleme! Toplam görev süresi periyodu aştı!"
        self.idle_runtime_us = self.total_elapsed_us - total_active_us

    def get_cpu_statistics(self):
        stats = {}
        total_active_us = sum(t.total_runtime_us for t in self.tasks)
        total_time_us = total_active_us + self.idle_runtime_us
        
        for t in self.tasks:
            utilization = (t.total_runtime_us / total_time_us) * 100.0
            stats[t.name] = {
                "runtime_ms": t.total_runtime_us / 1000.0,
                "exec_count": t.execution_count,
                "utilization_pct": utilization
            }
            
        idle_pct = (self.idle_runtime_us / total_time_us) * 100.0
        total_cpu_load = 100.0 - idle_pct
        return stats, total_cpu_load, idle_pct

# Aviyonik Görev Seti
sched = VirtualRTOSScheduler()
task_guidance  = VirtualRTOSTask("Guidance_100Hz", priority=3, period_ms=10, wcet_ms=2.5) # 2.5 ms / 10 ms = %25
task_radar     = VirtualRTOSTask("Radar_DSP_50Hz", priority=2, period_ms=20, wcet_ms=4.0) # 4.0 ms / 20 ms = %20
task_telemetry = VirtualRTOSTask("Telemetry_10Hz", priority=1, period_ms=100, wcet_ms=15.0) # 15 ms / 100 ms = %15

for t in [task_guidance, task_radar, task_telemetry]:
    sched.register_task(t)

sched.simulate_timeline(duration_ms=1000) # 1 saniyelik uçuş döngüsü
task_stats, cpu_load, idle_pct = sched.get_cpu_statistics()

print(f"[OK] RTOS Görev CPU Profilleme İstatistikleri (1000 ms Örnekleme):")
for name, data in task_stats.items():
    print(f"  - {name:<16}: Toplam = {data['runtime_ms']:>6.1f} ms | Koşum = {data['exec_count']:>4} | CPU = %{data['utilization_pct']:>5.2f}")

print(f"  - {'IDLE_TASK':<16}: Boşta  = {sched.idle_runtime_us / 1000.0:>6.1f} ms | CPU = %{idle_pct:>5.2f}")
print(f"  - Toplam CPU Yükü : %{cpu_load:.2f} (Tavan Sınır: %70.0)")

assert cpu_load <= 70.0, f"CPU yükü tavan sınırını aştı: %{cpu_load:.2f}"
assert abs((cpu_load + idle_pct) - 100.0) < 0.01, "Yüzde toplamı %100 değil!"
```

## 2.2 Kod Analizi & Bellek Yönetimi: TCB Çalışma Zamanı Sayaçları

Gerçek bir FreeRTOS uygulamasında `vTaskGetRunTimeStats` şu adımlarla çalışır:

1. **Task Control Block (TCB) Genişletmesi:** Her görev için TCB yapısına `uint32_t ulRunTimeCounter` eklenir.
2. **Context-Switch Hook (`traceTASK_SWITCHED_IN` / `traceTASK_SWITCHED_OUT`):**
   - Görev CPU'ya girdiğinde o anki donanımsal timer değeri kaydedilir:
     `ulTaskStartTime = portGET_RUN_TIME_COUNTER_VALUE();`
   - Görev CPU'dan çıkarken geçen süre o görevin TCB'sine eklenir:
     `pxCurrentTCB->ulRunTimeCounter += (portGET_RUN_TIME_COUNTER_VALUE() - ulTaskStartTime);`
3. **Statik Raporlama:** Çıktı formatlanırken dinamik bellek ayrılmaz; geliştirici tarafından sağlanan statik bir karakter dizisine (`char pcWriteBuffer[512]`) yazılır.

## 2.3 Edge Case'ler ve Kritik Hatalar: Profilleme Tuzakları

| Kritik Hata | Belirti / Sonuç | Kök Neden (Root Cause) | Çözüm / Doğru Yaklaşım |
| :--- | :--- | :--- | :--- |
| **DWT Sayacının Taşması (Overflow)** | Süre ölçümü negatif veya devasa pozitif çıkar | 32-bit sayacın 168 MHz'de 25 saniyede sıfırlanması | `(stop - start)` çıkarma işlemi uint32_t olarak yapılmalıdır; modulo aritmetiği taşmayı otomatik telafi eder. |
| **Profil Koduyla Heisenberg Etkisi** | Kod profilleme açıkken çalışır, kapatılınca çöker | Ölçüm kodunun zamanlamayı geciktirip yarış durumunu (race condition) gizlemesi | Ölçümler daima tek çevrimlik DWT/GPIO ile yapılmalı; ağır loglamalar kaldırılmalıdır. |
| **Yanlış Idle Task Önceliği** | CPU yükü daima %100 görünür | Başka bir görevin `tskIDLE_PRIORITY` (Öncelik 0) seviyesinde sonsuz döngüde çalışması | Kullanıcı görevleri asla öncelik 0 yapılmamalıdır. |
| **Stack Canary Bozulması** | Sistemin aniden `HardFault` veya garip değişken sapması vermesi | Görevin ayrılan yığın derinliğini aşması | Stack Watermark denetimi yapılmalı ve yığın boyutu genişletilmelidir. |

## 3.1 RAM ve Yığın (Stack) Profilleme: Stack Watermarking (0xA5A5A5A5)

Gömülü sistemlerde RAM en kıt kaynaktır (Örn: STM32F4'te 128 KB SRAM). Bellek profilinde iki kritik bölge bulunur:

### 1. Linker Script Bellek Segmentleri
- `.text` (Flash): Makine kodları ve fonksiyonlar.
- `.rodata` (Flash): `const` sabitler ve string dizgileri.
- `.data` (RAM): İlk değeri olan global ve statik değişkenler (Flash'tan RAM'e kopyalanır).
- `.bss` (RAM): İlk değeri sıfır olan global ve statik değişkenler.
- `Heap` (RAM): Dinamik bellek alanı.
- `Stack` (RAM): Fonksiyon yerel değişkenleri, dönüş adresleri ve ISR bağlamı.

### 2. Stack Watermarking (Yığın Boyama Deseni)
Bir görevin ne kadar yığın harcadığını çalışma anında anlamanın en etkili yöntemi:
1. Görev oluşturulurken, o göreve tahsis edilen yığın belleğinin tamamı bilinen sihirli bir desenle (Magic Pattern) doldurulur (FreeRTOS standardı: `0xA5` baytı).
2. Sistem çalışırken yığın tepeden aşağıya doğru büyür ve dokunduğu yerlerdeki `0xA5` desenini gerçek verilerle ezer.
3. Profilleyici yığının en dip adresinden yukarı doğru tarama yapar. İlk `0xA5` harici baytın görüldüğü yer, o görevin hayatı boyunca ulaştığı **Maksimum Yığın Derinliğini (Peak Stack Usage)** verir.
4. Kalan el değmemiş `0xA5` bayt sayısı **Yüksek Su Seviyesi (High Water Mark)** olarak adlandırılır.

```python
# Kod Hücresi 3: Stack Watermark (0xA5A5A5A5) Boyama ve Heap Fragmentasyon Analizörü
class VirtualTaskStack:
    """0xA5 Sihirli Deseniyle Boyanmış Sanal Görev Yığını"""
    MAGIC_PATTERN = 0xA5
    
    def __init__(self, task_name, stack_size_words=256):
        self.task_name = task_name
        self.size_words = stack_size_words
        # Tüm yığını 0xA5 baytıyla boya (Watermarking)
        self.memory = bytearray([self.MAGIC_PATTERN] * (stack_size_words * 4))

    def simulate_call_depth(self, words_used):
        """Fonksiyon çağrıları ve yerel değişkenlerle yığının tepeden aşağı ezilmesi"""
        assert words_used <= self.size_words, f"STACK OVERFLOW! {self.task_name} yığını patlattı!"
        bytes_to_overwrite = words_used * 4
        # Yığın sonundan (üst adres) aşağıya doğru ezilir
        start_idx = len(self.memory) - bytes_to_overwrite
        for i in range(start_idx, len(self.memory)):
            self.memory[i] = 0xAA # Gerçek veri ile boyandı

    def get_high_water_mark_words(self):
        """Tabandan yukarı doğru ilk el değmemiş 0xA5 sayısını say"""
        untouched_bytes = 0
        for b in self.memory:
            if b == self.MAGIC_PATTERN:
                untouched_bytes += 1
            else:
                break
        return untouched_bytes // 4

class VirtualHeapAllocator:
    """FreeRTOS heap_4 Benzeri First-Fit Dinamik Bellek ve Fragmentasyon Simülatörü"""
    def __init__(self, total_bytes=10240):
        self.total_bytes = total_bytes
        self.free_bytes = total_bytes
        self.allocations = {} # id -> size
        self.next_id = 1

    def allocate(self, size_bytes):
        aligned_size = (size_bytes + 7) & ~7 # 8-bayt hizalama
        if aligned_size <= self.free_bytes:
            alloc_id = self.next_id
            self.next_id += 1
            self.allocations[alloc_id] = aligned_size
            self.free_bytes -= aligned_size
            return alloc_id
        return None

    def free(self, alloc_id):
        if alloc_id in self.allocations:
            size = self.allocations.pop(alloc_id)
            self.free_bytes += size

    def get_fragmentation_ratio(self):
        # Basit fragmentasyon metriği: ayrık boş blok oranı
        return 1.0 - (self.free_bytes / self.total_bytes)

# Test 1: Stack Watermark Testi
stack_guidance = VirtualTaskStack("Task_Guidance", stack_size_words=512) # 2048 Bayt
stack_guidance.simulate_call_depth(words_used=340) # En derin çağrıda 340 kelime harcandı

hwm_words = stack_guidance.get_high_water_mark_words()
used_words = stack_guidance.size_words - hwm_words
stack_usage_pct = (used_words / stack_guidance.size_words) * 100.0

print(f"[OK] Stack Watermarking (0xA5A5A5A5) Doğrulaması:")
print(f"  - Tahsis Edilen Yığın   : {stack_guidance.size_words} words ({stack_guidance.size_words * 4} bayt)")
print(f"  - Maksimum Kullanılan   : {used_words} words ({used_words * 4} bayt)")
print(f"  - High Water Mark (HWM) : {hwm_words} words ({hwm_words * 4} bayt boş alan)")
print(f"  - Yığın Kullanım Oranı  : %{stack_usage_pct:.1f} (Güvenlik Sınırı: <= %75)")

assert hwm_words == (512 - 340), "HWM hesabı hatalı!"
assert stack_usage_pct < 75.0, "Yığın doluluk oranı çok yüksek!"

# Test 2: Heap Tahsis ve Fragmentasyon Testi
heap = VirtualHeapAllocator(total_bytes=8192)
a1 = heap.allocate(1024)
a2 = heap.allocate(2048)
a3 = heap.allocate(512)
heap.free(a2) # Aradaki bloğu serbest bırak (Fragmentasyon oluşur)

print(f"[OK] Dinamik Bellek (Heap) Profillemesi:")
print(f"  - Toplam Heap   : {heap.total_bytes} bayt")
print(f"  - Boş Bellek    : {heap.free_bytes} bayt")
print(f"  - Doluluk Oranı : %{heap.get_fragmentation_ratio() * 100.0:.1f}")
assert heap.free_bytes == (8192 - 1024 - 512), "Heap boş alan hesabı hatalı!"
```

## 3.2 Hata Enjeksiyonu ve Doğrulama: Stack Overflow ve Deadline Miss

İki ölümcül gömülü sistem hatası simülasyonda bilerek oluşturulur:
1. **Stack Overflow (Yığın Taşması):** Fonksiyon derin özyinelemeye (deep recursion) girer veya yığına büyük bir dizi (`uint8_t buffer[4096]`) tahsis eder.
2. **Deadline Miss (Zaman Sınırı İhlali):** 10 ms periyoda sahip bir görev, beklenmeyen bir döngü nedeniyle 12.5 ms sürerek bir sonraki çevrimin başlangıcını ezer.

```python
# Kod Hücresi 4: Kırılma Senaryosu: Stack Canary İhlali ve Deadline Miss Denetimi
class StackCanaryGuard:
    """Yığın Taşmasını Algılayan Donanımsal/Yazılımsal Canary Mekanizması"""
    CANARY_MAGIC = 0xDEADBEEF
    
    def __init__(self, capacity_words=128):
        self.capacity = capacity_words
        self.canary_value = self.CANARY_MAGIC
        self.stack_overflow_detected = False

    def push_data(self, word_count):
        if word_count > self.capacity:
            # Canary ezildi!
            self.canary_value = 0xBAD00000
            self.stack_overflow_detected = True
            return False, "HARDFAULT: Stack Overflow! Canary Bozuldu!"
        return True, "OK"

class DeadlineMonitor:
    """Görev Deadline (Katı Zaman Sınırı) Takipçisi"""
    def __init__(self, task_name, deadline_ms=10.0):
        self.task_name = task_name
        self.deadline_ms = deadline_ms
        self.deadline_miss_count = 0
        self.fault_log = []

    def check_execution_time(self, actual_runtime_ms):
        if actual_runtime_ms > self.deadline_ms:
            self.deadline_miss_count += 1
            err = f"DEADLINE MISS! {self.task_name} süresi: {actual_runtime_ms:.2f} ms > Limit: {self.deadline_ms:.2f} ms"
            self.fault_log.append(err)
            return False, err
        return True, "OK"

# 1. Stack Overflow Testi
canary = StackCanaryGuard(capacity_words=128)
ok, msg = canary.push_data(word_count=160) # 128 kelimelik alana 160 kelime yazıldı!
print(f"[TEST 1: STACK OVERFLOW] Sonuç:")
print(f"  - Canary Durumu   : {hex(canary.canary_value)} (Beklenen: != 0xDEADBEEF)")
print(f"  - Hata Bildirimi  : {msg}")
assert canary.stack_overflow_detected, "Stack overflow yakalanamadı!"

# 2. Deadline Miss Testi
monitor = DeadlineMonitor("Guidance_Loop", deadline_ms=10.0)
ok1, _ = monitor.check_execution_time(8.2)  # Geçerli
ok2, msg2 = monitor.check_execution_time(12.8) # İhlal!
print(f"[TEST 2: DEADLINE MISS] Sonuç:")
print(f"  - İhlal Bildirimi : {msg2}")
print(f"  - Toplam İhlal    : {monitor.deadline_miss_count}")
assert not ok2, "Deadline ihlali tespit edilemedi!"
assert monitor.deadline_miss_count == 1, "İhlal sayısı hatalı!"
```

## 3.3 Hata Analizi ve Düzeltme Stratejisi: MPU Guard Ring

Gömülü mimarilerde yığın taşmalarını donanımsal olarak yakalamak için:
1. **FreeRTOS Stack Overflow Hook:**
   - `configCHECK_FOR_STACK_OVERFLOW = 2`: Hem TCB işaretçisi kontrol edilir hem de yığının son 16 baytında `0xA5` deseninin bozulup bozulmadığı taranır. Bozulma varsa `vApplicationStackOverflowHook` tetiklenir.
2. **Cortex-M MPU Guard Ring:**
   - Bellek Koruma Birimi (MPU) kullanılarak, her görevin yığınının bittiği sınır adresine 32 baytlık **Erişilemez (No Access)** bir MPU bölgesi konur.
   - Yığın taştığı mikro-saniyede donanım doğrudan `MemManage Fault` üretir; böylece komşu değişkenler ezilmeden işlemci güvenli duruma geçer.

## 4.1 Savunma Sanayiinde Ölçüm: ASELSAN / TUSAŞ Aviyonik Profilleme Standartları

Savunma sanayiinde uçuş yazılımları için teslim kriterleri:
- **WCET Kanıtı:** Kritik döngüler (Güdüm, Seyrüsefer, Kontrol) en az 1.000.000 döngü boyunca çalıştırılmalı ve ölçülen maksimum süre ($WCET$) matematiksel deadline'ın %60'ını aşmamalıdır.
- **Sıfır Dinamik Bellek Kuralı:** Görevler başladıktan sonra `malloc`, `free`, `new`, `delete` çağrıları MISRA kuralı olarak yasaktır (Deterministic Static Allocation).
- **Yığın Güvenlik Marjı:** Her RTOS görevinin `High Water Mark` değeri, ayrılan yığının en az **%25'i kadar boş kalmalıdır**.

```python
# Kod Hücresi 5: Çok Görevli Aviyonik Radar & Görev Bilgisayarı Tam Profilleme Simülasyonu
class AvionicsSystemBenchmark:
    """Aviyonik Görev Bilgisayarı Tam Sistem Zamanlama ve Bellek Profilleme Motoru"""
    def __init__(self):
        self.tasks = {
            "Radar_DSP": {"period_ms": 20, "deadline_ms": 15.0, "stack_alloc": 1024, "history": []},
            "Flight_Control": {"period_ms": 10, "deadline_ms": 6.0, "stack_alloc": 512, "history": []},
            "Telemetry_Comm": {"period_ms": 50, "deadline_ms": 25.0, "stack_alloc": 256, "history": []}
        }
        self.system_clock_mhz = 168.0

    def run_benchmark(self, cycles=200):
        np.random.seed(101)
        for c in range(cycles):
            # Radar DSP: Ağır FFT hesaplaması (11-14 ms)
            dsp_time = np.random.normal(loc=12.2, scale=0.6)
            dsp_stack = int(np.random.normal(loc=680, scale=20))
            self.tasks["Radar_DSP"]["history"].append((dsp_time, dsp_stack))
            
            # Flight Control: Matris çarpımı (3.5 - 5.0 ms)
            fc_time = np.random.normal(loc=4.1, scale=0.3)
            fc_stack = int(np.random.normal(loc=310, scale=15))
            self.tasks["Flight_Control"]["history"].append((fc_time, fc_stack))
            
            # Telemetry: Paket hazırlama (12 - 18 ms)
            telem_time = np.random.normal(loc=14.5, scale=1.1)
            telem_stack = int(np.random.normal(loc=160, scale=10))
            self.tasks["Telemetry_Comm"]["history"].append((telem_time, telem_stack))

    def evaluate(self):
        report = {}
        for name, data in self.tasks.items():
            times = [h[0] for h in data["history"]]
            stacks = [h[1] for h in data["history"]]
            wcet = max(times)
            bcet = min(times)
            peak_stack = max(stacks)
            hwm = data["stack_alloc"] - peak_stack
            deadline = data["deadline_ms"]
            
            report[name] = {
                "WCET_ms": wcet,
                "BCET_ms": bcet,
                "Jitter_ms": wcet - bcet,
                "Deadline_ms": deadline,
                "Deadline_Margin_pct": ((deadline - wcet) / deadline) * 100.0,
                "Peak_Stack_Words": peak_stack,
                "High_Water_Mark_Words": hwm,
                "Stack_Safety_Margin_pct": (hwm / data["stack_alloc"]) * 100.0
            }
        return report

bench = AvionicsSystemBenchmark()
bench.run_benchmark(cycles=300)
results = bench.evaluate()

print(f"[OK] Aviyonik Sistem Tam Profilleme Değerlendirme Raporu:")
for task, res in results.items():
    print(f"  - [{task}]")
    print(f"      WCET: {res['WCET_ms']:.2f} ms | Limit: {res['Deadline_ms']:.1f} ms | Zaman Marjı: %{res['Deadline_Margin_pct']:.1f}")
    print(f"      Tepe Yığın: {res['Peak_Stack_Words']} words | HWM: {res['High_Water_Mark_Words']} words | Yığın Marjı: %{res['Stack_Safety_Margin_pct']:.1f}")
    assert res['Deadline_Margin_pct'] > 0, f"{task} deadline ihlali yaptı!"
    assert res['Stack_Safety_Margin_pct'] > 20.0, f"{task} yığın güvenlik marjı yetersiz!"
```

## 4.2 Benchmark ve Performans Çıkarımları: Profilleme Yöntemleri Karşılaştırması

| Yöntem | Çözünürlük | Ek Yük (Overhead) | Donanım İhtiyacı | En Uygun Senaryo |
| :--- | :--- | :--- | :--- | :--- |
| **DWT CYCCNT** | **1 Çevrim (~5.95 ns)** | **1 çevrim (<6 ns)** | Cortex-M Dahili | Kritik algoritmalar (FFT, Kalman, Şifreleme) |
| **GPIO Toggling** | **10 - 20 ns** | **2 çevrim (~12 ns)** | Osiloskop / Lojik Analizör | ISR tepki süresi ve bağlam değişimi ölçümü |
| **Hardware Timer** | **1 µs** | **~10 çevrim** | Boşta Timer (TIM2) | RTOS görev süreleri ve Run-Time Stats |
| **SysTick Polling** | **1 ms** | **Düşük** | Standart RTOS Saati | Uzun süreli telemetri ve sistem çalışma süresi |
| **UART / Printf** | **Kötü (1-10 ms)** | **15.000+ çevrim** | Seri Port | **YASAK:** Gerçek zamanlı kodda kullanılmaz! |

```python
# Kod Hücresi 6: Profesyonel 4-Panelli Gömülü Zamanlama, CPU ve RAM Profilleme Dashboard'u
import os
import matplotlib.pyplot as plt
import numpy as np

# Robust Fallback for PNG_FILE
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_194_embedded_timing_cpu_ram_olcum.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_194\gun_194_embedded_timing_cpu_ram_olcum.png"

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
# PANEL 1: DWT CYCCNT Zamanlama Dağılımı ve WCET / BCET Jitter Histogramı
# ------------------------------------------------------------------------------
np.random.seed(42)
execution_times_us = np.random.normal(loc=14.88, scale=0.52, size=1000)
wcet_val = np.max(execution_times_us)
bcet_val = np.min(execution_times_us)

n, bins, patches = axs[0, 0].hist(execution_times_us, bins=30, color='#38BDF8', alpha=0.8, edgecolor='#0F172A')
axs[0, 0].axvline(bcet_val, color='#10B981', linestyle='--', linewidth=2, label=f"BCET: {bcet_val:.2f} µs")
axs[0, 0].axvline(np.mean(execution_times_us), color='#F59E0B', linestyle='-', linewidth=2, label=f"AVG: {np.mean(execution_times_us):.2f} µs")
axs[0, 0].axvline(wcet_val, color='#EF4444', linestyle='--', linewidth=2, label=f"WCET: {wcet_val:.2f} µs")
axs[0, 0].axvline(20.0, color='#EC4899', linestyle=':', linewidth=2, label="Deadline Limiti: 20.0 µs")

axs[0, 0].set_title("Panel 1: DWT CYCCNT Yürütme Süresi & Jitter Dağılımı (168 MHz)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[0, 0].set_xlabel("Yürütme Süresi (Mikrosaniye - µs)", fontsize=9, color='#CBD5E1')
axs[0, 0].set_ylabel("Örnek Sayısı", fontsize=9, color='#CBD5E1')
axs[0, 0].legend(loc='upper right', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

# ------------------------------------------------------------------------------
# PANEL 2: RTOS Görev CPU Yükü Dağılımı (Utilization Pasta / Halka Grafiği)
# ------------------------------------------------------------------------------
labels_cpu = ['Guidance (100Hz)', 'Radar DSP (50Hz)', 'Telemetry (10Hz)', 'Idle Task (Boşta)']
sizes_cpu = [25.0, 20.0, 15.0, 40.0]
colors_cpu = ['#38BDF8', '#818CF8', '#F59E0B', '#10B981']

wedges, texts, autotexts = axs[0, 1].pie(
    sizes_cpu, labels=labels_cpu, autopct='%1.1f%%', startangle=140,
    colors=colors_cpu, textprops=dict(color='#F8FAFC', fontsize=9),
    wedgeprops=dict(width=0.45, edgecolor='#0F172A', linewidth=2)
)
for at in autotexts:
    at.set_color('#0F172A')
    at.set_fontweight('bold')

axs[0, 1].set_title("Panel 2: RTOS Görev CPU Yükü Dağılımı (Toplam Yük: %60.0)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

# ------------------------------------------------------------------------------
# PANEL 3: Görev Yığın (Stack) Kullanımı ve High Water Mark Güvenlik Marjı
# ------------------------------------------------------------------------------
tasks = ['Radar_DSP', 'Flight_Control', 'Telemetry']
allocated_words = [1024, 512, 256]
peak_used_words = [740, 350, 185]
hwm_remaining   = [1024 - 740, 512 - 350, 256 - 185]

x_pos = np.arange(len(tasks))
width = 0.45

axs[1, 0].bar(x_pos, peak_used_words, width, label='Tepe Yığın Kullanımı (Peak)', color='#EF4444', alpha=0.85, edgecolor='#FFFFFF', linewidth=0.5)
axs[1, 0].bar(x_pos, hwm_remaining, width, bottom=peak_used_words, label='High Water Mark (Kalan Güvenli Alan)', color='#10B981', alpha=0.85, edgecolor='#FFFFFF', linewidth=0.5)

axs[1, 0].set_title("Panel 3: Görev Yığın (Stack) Derinliği ve High Water Mark (0xA5)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[1, 0].set_xticks(x_pos)
axs[1, 0].set_xticklabels(tasks, fontsize=9)
axs[1, 0].set_ylabel("Kelime Sayısı (Words - 4B)", fontsize=9, color='#CBD5E1')
axs[1, 0].legend(loc='upper right', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

for i in range(len(tasks)):
    pct = (peak_used_words[i] / allocated_words[i]) * 100.0
    axs[1, 0].text(i, peak_used_words[i] / 2, f"%{pct:.1f}", ha='center', va='center', color='#FFFFFF', fontweight='bold', fontsize=8)

# ------------------------------------------------------------------------------
# PANEL 4: Linker Bellek Haritası ve Heap Fragmentasyon Zaman Çizelgesi
# ------------------------------------------------------------------------------
time_axis = np.linspace(0, 60, 100)
# Heap kullanım dalgalanması
heap_alloc_kb = 3.2 + 1.5 * np.sin(time_axis / 5.0) + np.random.normal(0, 0.1, size=len(time_axis))
heap_limit_kb = np.full_like(time_axis, 8.0)

axs[1, 1].plot(time_axis, heap_alloc_kb, color='#F59E0B', linewidth=2.5, label='Kullanılan Heap (KB)')
axs[1, 1].plot(time_axis, heap_limit_kb, color='#EF4444', linestyle='--', linewidth=2, label='Toplam Heap Sınırı (8 KB)')
axs[1, 1].fill_between(time_axis, heap_alloc_kb, color='#F59E0B', alpha=0.2)

axs[1, 1].set_title("Panel 4: Dinamik Bellek (Heap) Kullanımı ve Fragmentasyon Eğrisi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[1, 1].set_xlabel("Zaman (Saniye - s)", fontsize=9, color='#CBD5E1')
axs[1, 1].set_ylabel("Bellek Miktarı (Kilobayt - KB)", fontsize=9, color='#CBD5E1')
axs[1, 1].set_ylim(0, 10)
axs[1, 1].legend(loc='upper right', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

plt.tight_layout()
fig.subplots_adjust(top=0.92)
fig.suptitle("ASELSAN / HAVELSAN GÖMÜLÜ SİSTEMLER — GÜN 194: DETERMINISTIC TIMING, CPU & RAM PROFILING", 
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
1. **DWT CYCCNT Kullanın:** Mikro-saniyenin altındaki algoritmik süreleri ölçmek için harici kütüphaneler yerine Cortex-M'in dahili DWT sayacını kullanın.
2. **CI/CD Entegrasyonu ile Otomatik HWM Denetimi:** Her otomatik test koşumunda tüm görevlerin `High Water Mark` değerini toplayın; kalan yığın boşluğu %25'in altına düştüğünde derleme boru hattını (pipeline) kırın.
3. **Linker Map Dosyasını Denetleyin:** Derleme sonrası üretilen `.map` dosyasındaki `.bss` ve `.data` boyutlarını otomatik scriptlerle takip ederek beklenmedik RAM artışlarını anında yakalayın.

### Kaçınılması Gereken Hatalar (DON'Ts - Anti-Patterns)
1. **Printf ile Zaman Ölçmek:** Zaman duyarlı döngülerin içine `printf` koymak kodu binlerce çevrim yavaşlatır ve gerçek dünya davranışını tahrif eder.
2. **Sıfır Güvenlik Marjı ile Yığın Belirlemek:** Bir fonksiyonun yerel değişkenlerinin toplamına göre yığın boyutu belirlemeyin; araya girebilecek iç içe kesmelerin (Nested ISRs) yığına basacağı yığın çerçevesini (Stack Frame) hesaba katın.
3. **%100 CPU Yükü Hedeflemek:** Mikrodenetleyiciyi sürekli %95+ yükte çalıştırmak, en ufak bir kesme dalgalanmasında deadline kaçırılmasına neden olur.

## 4.4 Mülakat Soruları ve Yanıtları

### Soru 1: ARM Cortex-M mimarisinde DWT CYCCNT sayacı ile zaman ölçerken 32-bit taşma (overflow) durumu nasıl yönetilir?
**Cevap:** DWT CYCCNT 32-bit unsigned bir sayactır. İki zaman damgası arasındaki fark `uint32_t elapsed = (uint32_t)(stop_cycles - start_cycles);` şeklinde hesaplandığında, C/C++ ikinin tümleyeni (two's complement) aritmetiği sayesinde sayaç bir kez taşmış olsa bile sonuç matematiksel olarak kesinlikle doğrudur. Örneğin `start = 0xFFFFFFF0` ve `stop = 0x00000020` ise, `(uint32_t)(0x00000020 - 0xFFFFFFF0) = 0x30 = 48` çevrim doğru olarak bulunur. Ancak geçen süre 32-bitin maksimum karşılığı olan $2^{32} / f_{cpu}$ süresini (168 MHz'de ~25.56 saniye) aşarsa tek başına çıkarma yetmez; taşma kesmesi (overflow interrupt) ile tur sayısı biriktirilmelidir.

### Soru 2: FreeRTOS'ta "Stack High Water Mark" nedir ve nasıl çalışır?
**Cevap:** High Water Mark, bir görevin oluşturulduğu andan itibaren yığınında kalan **en az boş alan miktarını** (kelime cinsinden) temsil eder. FreeRTOS görev yığınını ilk başta `0xA5` deseniyle boyar (Stack Paint). Görev çalıştıkça fonksiyon çağrıları bu deseni ezer. `uxTaskGetStackHighWaterMark()` çağrıldığında sistem yığının tabanından yukarı doğru taranmamış `0xA5` baytlarını sayar. Bu değer ne kadar sıfıra yakınsa görev yığın taşmasına (Stack Overflow) o kadar yaklaşmış demektir. Aviyonikte bu değerin tahsis edilen yığının en az %20-30'u seviyesinde kalması istenir.

### Soru 3: Heisenberg Etkisi (Heisenbug) gömülü profil oluşturmada ne anlama gelir ve nasıl engellenir?
**Cevap:** Profilleme kodunun kendisinin CPU zamanı ve bellek tüketmesi nedeniyle sistemin orijinal zamanlamasını ve davranışını bozması durumudur. Örneğin iki görev arasındaki bir yarış durumu (Race Condition), araya bir `printf` konulduğunda görevlerin sıralaması değiştiği için aniden ortadan kaybolabilir; loglama kaldırıldığında ise hata yeniden ortaya çıkar. Çözüm: Ölçümlerde donanımsal DWT sayaçları veya fiziksel GPIO pin seviyesi değişimleri gibi sıfıra yakın gecikmeli (1-2 çevrim) müdahalesiz (non-intrusive) teknikler kullanmaktır.

## 4.5 Bilgi Kontrolü (Self-Check Test)

### 1. 168 MHz hızında çalışan bir STM32F4'te DWT CYCCNT sayacının her çevrimi ne kadar sürer?
- A) 1 milisaniye
- B) 5.95 nanosaniye
- C) 100 mikrosaniye
- D) 1 pikosaniye
*Cevap: B. 1 / 168.000.000 saniye = 5.952 nanosaniyedir.*

### 2. Havacılık ve savunma yazılım standartlarında (DO-178C) nominal CPU yükünün tavan sınırı genellikle yüzde kaçtır?
- A) %100
- B) %70
- C) %50
- D) %10
*Cevap: B. Kalan %30 beklenmeyen kesmeler ve arıza kurtarma için güvenlik marjıdır.*

### 3. FreeRTOS'ta stack boyama (Stack Watermarking) için varsayılan olarak hangi sihirli bayt kullanılır?
- A) 0x00
- B) 0xFF
- C) 0xA5
- D) 0x55
*Cevap: C. FreeRTOS standart olarak yığını 0xA5 deseniyle boyar.*

### 4. Linker Map dosyasında ilk değeri sıfır olan veya değer atanmamış global değişkenler hangi segmentte yer alır?
- A) .text
- B) .rodata
- C) .bss
- D) .heap
*Cevap: C. İlk değeri sıfır olan statik ve global değişkenler .bss segmentinde tutulur.*

### 5. Aşağıdaki profil alma yöntemlerinden hangisi en yüksek Heisenberg etkisine (aşırı gecikmeye) sahiptir?
- A) GPIO Toggling
- B) DWT CYCCNT okuması
- C) UART üzerinden printf çağrısı
- D) Hardware Timer okuması
*Cevap: C. Printf binlerce saat çevrimi tüketerek sistemin zamanlamasını bozar.*

## 4.6 Günün Sözü ve Düşünce Sorusu

> *"Ölçemediğiniz bir sistemin deterministik olduğunu iddia edemezsiniz; gömülü dünyada varsayımlar değil, çevrim sayaçları konuşur."*

### Düşünce Sorusu
Bir gömülü sistemde Cortex-M MPU (Memory Protection Unit) ile yığının altına 32 baytlık erişilemez bir bölge (Guard Ring) koymanın, yazılımsal `configCHECK_FOR_STACK_OVERFLOW = 2` yöntemine kıyasla en büyük avantajı nedir?
**Cevap:** Yazılımsal kontrol yalnızca RTOS bağlam değişimi (context switch) anında çalışır. Eğer bir görev bağlam değişimi olmadan önce yığını taşırıp komşu veriyi ezer ve ardından eski seviyesine dönerse yazılımsal kontrol bunu yakalayamaz. Donanımsal MPU Guard Ring ise işlemci o yasaklı adrese yazmaya çalıştığı **tam o saat çevriminde** donanımsal `MemManage Fault` üreterek veri bozulmasını sıfır mikrosaniye gecikmeyle ve kesinlikle engeller.

## 5.1 İleri Düzey Okuma ve Kaynakça

1. **ARM Limited:** *Cortex-M4 Technical Reference Manual - Data Watchpoint and Trace (DWT) Unit.*
2. **Real Time Engineers Ltd:** *FreeRTOS Real-Time Kernel - Tracing and Run-Time Statistics.* https://www.freertos.org/rtos-run-time-stats.html
3. **FAA / RTCA:** *CAST-32A: Multi-core Positioning Paper - Timing and Resource Contention.*
4. **Wilhelm, R., et al. (2008):** *The worst-case execution-time problem—overview of methods and survey of tools.* ACM Transactions on Embedded Computing Systems.
5. **STMicroelectronics:** *PM0214: STM32 Cortex-M4 programming manual.*

## 5.2 Gün Sonu Özeti ve Özel Lisans

### Günün Özeti (3 Cümlelik Kural)
1. **Embedded Timing / CPU / RAM Ölçümü Nedir?:** Mikrodenetleyicinin DWT sayaçları, GPIO probları ve RTOS hook mekanizmalarıyla kodun çevrim süresini (WCET), işlemci yükünü ve yığın (Stack) derinliğini belirleme disiplinidir.
2. **Hangi Problemi Çözer?:** Kodun zaman sınırını (deadline) aşıp aşmadığını, CPU'nun aşırı yüklenip yüklenmediğini ve yığın taşması (Stack Overflow) ile belleğin sessizce bozulup bozulmadığını çalışma anında kanıtlar.
3. **Hangi Trade-off / Hata Sınıfını Getirir?:** Ağır loglama fonksiyonları (printf) Heisenberg etkisi yaratarak zamanlamayı bozar; DWT 32-bit taşması (overflow) hesaba katılmazsa süreler anlamsız negatif değerlere dönüşür.

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

