# GÜN 180: Task/Thread ve Scheduler (Çizelgeleyici) Mimarisi

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, tersine mühendislik yapılamaz.
```

---

## Modül Künyesi
- **Faz:** F5 — Gömülü Sistemler, RTOS ve STM32 Mimarisi
- **Konu:** Task/Thread Kavramı, Görev Durum Makinesi (Task State Machine), FreeRTOS Hazır Listesi (Ready List), Donanımsal O(1) Çizelgeleyici (ARM Cortex-M `CLZ` Komutu), Round-Robin Zaman Dilimleme (Time-Slicing), TCB (Task Control Block) Anatomisi, Yığın Su Seviyesi (Stack High Water Mark), Boşta Görev (Idle Task) ve Tickless Idle Güç Optimizasyonu
- **Hedef Donanım:** ARM Cortex-M4/M7 (STM32F4/F7/H7), FreeRTOS v10/v11, Zephyr RTOS
- **Kritik Kavramlar:** Task vs Process, Ready/Running/Blocked/Suspended Durum Geçişleri, `uxTopReadyPriority` Bitmask Algoritması, Eşit Öncelikli Görevlerin Çizelgelenmesi, 0xA5 Yığın Deseni ve Taşma Tespiti, DO-178C Deterministik Çizelgeleme
- **Savunma Sanayii Senaryosu:** ROKETSAN Füze Güdüm ve Uçuş Bilgisayarında Ataletsel Seyrüsefer (INS EKF), Kanatçık PWM Kontrolü (Fin Actuator), Görev Yönetim Durum Makinesi ve Taktik Telemetri Görevlerinin Çoklu Görev Mimarisi

## 1. Giriş ve Zihinsel Model (Task ve Scheduler Nedir?)

Dün (Gün 179) RTOS'un deterministik yanıt süreleri sağlamak ve Super-Loop'un kooperatif bloklanma sorununu çözmek için neden var olduğunu inceledik. Bugün ise bu sistemin motorunu oluşturan iki temel bileşeni masaya yatırıyoruz: **Task (Görev)** ve **Scheduler (Çizelgeleyici)**.

### Task vs Thread vs Process: Gömülü Dünyadaki Ayrım
Genel amaçlı işletim sistemlerinde (Linux/Windows):
- Bir **Process (Süreç)**, Donanımsal Bellek Yönetim Birimi (MMU) tarafından korunan bağımsız bir sanal adres alanına (Virtual Address Space) sahiptir.
- Bir **Thread (İş Parçacığı)**, aynı sürecin sanal belleğini paylaşan hafif yürütme birimidir.

Ancak tipik bir ARM Cortex-M mikrodenetleyicisinde (STM32 serisi) **MMU YOKTUR!**
Tüm kod tek bir fiziksel RAM ve Flash alanında koşar. Bu nedenle gömülü sistemlerde "Task" ve "Thread" terimleri eşanlamlı kullanılır:
> **Task (Görev):** Sonsuz bir döngü (`for(;;)`) şeklinde yazılan, bağımsız bir yığına (Private Stack), işlemci kayıt bağlamına (CPU Context) ve bir kimlik kartına (TCB) sahip en küçük bağımsız çalışma birimidir.

```
+---------------------------------------------------------------------------------------------------+
|                         GÖMÜLÜ SİSTEMLERDE TEK FİZİKSEL BELLEK ALANI                              |
|                                                                                                   |
|  0x20000000 ┌─────────────────────────────────────────────────────────────┐                       |
|             │ Task 1 Yığını (Stack 1)    ──> R4-R11, R0-R3, PC, LR...     │                       |
|             ├─────────────────────────────────────────────────────────────┤                       |
|             │ Task 2 Yığını (Stack 2)    ──> R4-R11, R0-R3, PC, LR...     │                       |
|             ├─────────────────────────────────────────────────────────────┤                       |
|             │ Çekirdek & Kesme Yığını (MSP Stack)                         │                       |
|             ├─────────────────────────────────────────────────────────────┤                       |
|             │ Global / Statik Değişkenler (.data & .bss)                  │                       |
|  0x20020000 └─────────────────────────────────────────────────────────────┘                       |
+---------------------------------------------------------------------------------------------------+
```

### Scheduler'ın Rolü: Orkestra Şefi
İşlemcide sadece bir adet çekirdek (CPU Core) vardır, ancak sistemde koşan 10 farklı görev bulunabilir. **Scheduler (Çizelgeleyici)**, her saat vuruşunda (SysTick) veya bir asenkron olayda şu soruyu yanıtlayan karar mekanizmasıdır:
> *"Şu anda işlemciyi (CPU) hangi göreve vermeliyim?"*

## 2. Task Durum Makinesi (Task State Machine)

Bir görev hayatı boyunca 4 temel durum arasında geçiş yapar:

```
                          ┌──────────────┐
                          │   SUSPENDED  │ (vTaskSuspend ile donduruldu)
                          └──────┬───────┘
                                 │ vTaskResume()
                                 ▼
                     ┌───────────────────────┐
         ┌──────────>│         READY         │<──────────┐
         │           │ (Çalışmaya Hazır, CPU │           │
         │           │       Bekliyor)       │           │
         │           └───────────┬───────────┘           │
         │ Olay Gerçekleşti      │ Çizelgeleyici         │ Olay Bekleme
         │ veya Zaman Doldu      │ Seçti (Preemption)    │ (Delay, Mutex,
         │                       ▼                       │ Kuyruk Boş)
    ┌────┴─────┐     ┌───────────────────────┐      ┌────┴──────┐
    │ BLOCKED  │<────┤        RUNNING        │─────>│  BLOCKED  │
    └──────────┘     │  (CPU'yu Elinde Tutan │      └───────────┘
                     │       Tek Görev)      │
                     └───────────────────────┘
```

### Durumların Detayları:
1. **RUNNING (Koşan):** Tek çekirdekli sistemde belirli bir anda **yalnızca tek bir görev** bu durumda olabilir. CPU program sayacı (`PC`) bu görevin kodunu işler.
2. **READY (Hazır):** Görevin çalışması için hiçbir engel yoktur; yalnızca CPU'nun kendisine verilmesini beklemektedir. Görevler önceliklerine göre `pxReadyTasksLists[priority]` kuyruğunda sıralanır.
3. **BLOCKED (Blokeli):** Görev bir olayın gerçekleşmesini beklemektedir:
   - Zaman geçişi (`vTaskDelay`, `vTaskDelayUntil`),
   - Bir kaynaktan veri gelmesi (Kuyruktan mesaj bekleme - `xQueueReceive`),
   - Bir kilit serbest kalması (`xSemaphoreTake`).
   > **ÖNEMLİ:** Blokeli görevler **SIFIR CPU KULLANIR!** İşlemciyi asla meşgul etmezler (Super-Loop'taki busy-wait felaketinin tam zıddı).
4. **SUSPENDED (Askıya Alınmış):** Görev bellekten silinmemiştir ancak çizelgeleyici tarafından tamamen yok sayılır. Yalnızca `vTaskResume()` ile tekrar READY yapılabilir.

```python
# KOD HÜCRESİ 1: FreeRTOS Task State Machine & O(1) Bitmask Scheduler Simülatörü
# ------------------------------------------------------------------------------
# Bu simülasyon, FreeRTOS görev durum makinesini (State Machine) ve ARM Cortex-M
# donanımında tek saat çevriminde en yüksek önceliği bulan O(1) Bitmask (CLZ)
# çizelgeleme algoritmasını modeller.

class TaskState:
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"

class SimulatedTask:
    def __init__(self, task_id, name, priority, period_ticks, compute_ticks):
        self.task_id = task_id
        self.name = name
        self.priority = priority # 0 (En düşük / Idle) .. 31 (En yüksek)
        self.period_ticks = period_ticks
        self.compute_ticks = compute_ticks
        self.rem_compute = compute_ticks
        self.block_timeout = 0
        self.state = TaskState.READY
        self.total_run_ticks = 0

class FreeRTOSSchedulerO1:
    def __init__(self, max_priorities=32):
        self.max_priorities = max_priorities
        # Her öncelik seviyesi için Ready List (Çift yönlü bağlı liste simülasyonu)
        self.ready_lists = [[] for _ in range(max_priorities)]
        self.blocked_list = []
        # Donanımsal 32-bit Bitmask: Hangi öncelikte hazır görev var?
        self.ready_priority_bitmask = 0
        self.current_running_task = None
        self.tick_count = 0
        
    def add_task(self, task):
        self._add_to_ready(task)
        
    def _add_to_ready(self, task):
        task.state = TaskState.READY
        self.ready_lists[task.priority].append(task)
        # Bitmask'te ilgili önceliğin bitini 1 yap (O(1))
        self.ready_priority_bitmask |= (1 << task.priority)
        
    def _remove_from_ready(self, task):
        if task in self.ready_lists[task.priority]:
            self.ready_lists[task.priority].remove(task)
            if len(self.ready_lists[task.priority]) == 0:
                # O öncelikte hiç görev kalmadıysa biti 0 yap (O(1))
                self.ready_priority_bitmask &= ~(1 << task.priority)

    def find_highest_priority_clz(self):
        """ARM Cortex-M __CLZ (Count Leading Zeros) donanımsal O(1) emülasyonu"""
        if self.ready_priority_bitmask == 0:
            return 0 # Sadece Idle Task kalmış
        # Python'da 32-bit integer CLZ eşdeğeri: bit_length
        highest_prio = self.ready_priority_bitmask.bit_length() - 1
        return highest_prio

    def step_tick(self):
        self.tick_count += 1
        
        # 1. Blokeli görevlerin zaman aşımını kontrol et
        unblocked = []
        for task in self.blocked_list:
            task.block_timeout -= 1
            if task.block_timeout <= 0:
                unblocked.append(task)
                
        for task in unblocked:
            self.blocked_list.remove(task)
            task.rem_compute = task.compute_ticks
            self._add_to_ready(task)
            
        # 2. Çalışan görevin durumunu güncelle
        if self.current_running_task is not None:
            self.current_running_task.rem_compute -= 1
            self.current_running_task.total_run_ticks += 1
            
            if self.current_running_task.rem_compute <= 0:
                # Görev işini bitirdi -> Bir sonraki periyoda kadar BLOCKED durumuna geç
                self.current_running_task.state = TaskState.BLOCKED
                self.current_running_task.block_timeout = max(1, self.current_running_task.period_ticks - self.current_running_task.compute_ticks)
                self.blocked_list.append(self.current_running_task)
                self.current_running_task = None
            else:
                # İş henüz bitmedi, hazır listesine geri bırak (Time-Slicing için arkaya ekle)
                self._add_to_ready(self.current_running_task)
                self.current_running_task = None
                
        # 3. O(1) CLZ ile en yüksek öncelikli görevi seç
        top_prio = self.find_highest_priority_clz()
        if len(self.ready_lists[top_prio]) > 0:
            next_task = self.ready_lists[top_prio].pop(0)
            if len(self.ready_lists[top_prio]) == 0:
                self.ready_priority_bitmask &= ~(1 << top_prio)
            next_task.state = TaskState.RUNNING
            self.current_running_task = next_task
            return next_task.name, next_task.priority
            
        return "IDLE_TASK", 0

# Test Senaryosu Oluştur
sched = FreeRTOSSchedulerO1()
t_ins = SimulatedTask(1, "INS_EKF", priority=4, period_ticks=5, compute_ticks=1)
t_pwm = SimulatedTask(2, "Fin_PWM", priority=4, period_ticks=5, compute_ticks=1)
t_telem = SimulatedTask(3, "Telemetry", priority=1, period_ticks=10, compute_ticks=3)
t_idle = SimulatedTask(0, "IdleTask", priority=0, period_ticks=1, compute_ticks=1)

for t in [t_ins, t_pwm, t_telem, t_idle]:
    sched.add_task(t)

print("=" * 68)
print("FREERTOS O(1) BITMASK SCHEDULER VE TASK STATE MACHINE SİMÜLASYONU")
print("=" * 68)

execution_log = []
for tick in range(1, 21):
    running_name, running_prio = sched.step_tick()
    execution_log.append((tick, running_name, running_prio, sched.ready_priority_bitmask))
    if tick <= 10 or tick >= 18:
        print(f"Tick {tick:02d}: Koşan Görev = {running_name:<10} (Öncelik {running_prio}) | Bitmask: 0x{sched.ready_priority_bitmask:08X} ({bin(sched.ready_priority_bitmask)})")

# Matematiksel doğrulama
assert t_ins.total_run_ticks > 0, "HATA: INS_EKF çalışmalıydı!"
assert t_pwm.total_run_ticks > 0, "HATA: Fin_PWM çalışmalıydı!"
assert sched.ready_priority_bitmask & (1 << 0) != 0 or sched.current_running_task.name == "IdleTask", "Idle task her zaman hazır olmalı!"
print("\n[BAŞARILI]: Donanımsal O(1) Bitmask CLZ algoritması ve Task State Machine doğrulandı.")
```

## 3. Scheduler Mimarisi: O(1) Bitmask ve ARM Cortex-M CLZ Komutu

Gerçek zamanlı bir işletim sisteminde çizelgeleyicinin (Scheduler) karmaşıklığı **asla sistemdeki görev sayısına bağlı olmamalıdır!**
Eğer sistemde 5 görev varken seçim 1 µs sürüyor ama 50 görev varken 10 µs sürüyorsa, bu sistem **deterministik değildir**.

### Generic C Scheduler vs Port-Optimized Scheduler

FreeRTOS mimarisinde `FreeRTOSConfig.h` dosyasında iki mod seçeneği bulunur:

#### 1. Generic C Scheduler (`configUSE_PORT_OPTIMISED_TASK_SELECTION = 0`)
Tüm işlemcilerde çalışan standart C döngüsüdür:
```c
// En yüksek önceliği bulmak için yukarıdan aşağıya döngü: O(MAX_PRIORITIES)
UBaseType_t uxTopPriority = configMAX_PRIORITIES - 1;
while (listLIST_IS_EMPTY(&(pxReadyTasksLists[uxTopPriority]))) {
    uxTopPriority--;
}
```
Eğer 32 öncelik seviyeniz varsa, en kötü durumda bu döngü 32 kez döner. Bu durum determinizmi zedeler.

#### 2. Port-Optimised Task Selection (`configUSE_PORT_OPTIMISED_TASK_SELECTION = 1`)
ARM Cortex-M işlemcilerde donanımsal **`CLZ` (Count Leading Zeros)** komutu bulunur.
FreeRTOS, hazır listesinde görev bulunan öncelikleri 32-bitlik tek bir `uxTopReadyPriority` tam sayısında bit bayrakları olarak tutar.

```assembly
; ARM Cortex-M Montaj Kodu (Tek Çevrimde En Yüksek Önceliği Bulma):
LDR  R0, =uxTopReadyPriority   ; Hazır görevler bitmask'ini yükle
LDR  R0, [R0]                  ; R0 = 0x00000018 (Örn. Bit 3 ve Bit 4 hazır)
CLZ  R1, R0                    ; R1 = Baştaki sıfır sayısı (27)
RSB  R1, R1, #31               ; R1 = 31 - 27 = 4 (EN YÜKSEK ÖNCELİK 4!)
```

```
+---------------------------------------------------------------------------------------------------+
|               DONANIMSAL O(1) ÖNCELİK BULMA MEKANİZMASI (ARM CORTEX-M CLZ)                        |
|                                                                                                   |
|  uxTopReadyPriority Bit Haritası (32-bit register):                                               |
|  Bit:     31 30 29 ... 7  6  5  4  3  2  1  0                                                     |
|  Değer:  [ 0  0  0 ... 0  0  0  1  1  0  0  1 ]                                                  |
|                                 ▲  ▲        ▲                                                     |
|                                 │  │        └─ Priority 0 (Idle Task)                             |
|                                 │  └────────── Priority 3 (Telemetry)                             |
|                                 └───────────── Priority 4 (INS & Fin PWM) ──> EN YÜKSEK ÖNCELİK!   |
|                                                                                                   |
|  CLZ Komutu Baştaki Sıfırları Sayar (Leading Zeros = 27).                                         |
|  En Yüksek Öncelik = 31 - 27 = 4!                                                                 |
|  İŞLEM SÜRESİ: Sistemde ister 1 görev olsun ister 1000 görev olsun TAM 1 SAAT ÇEVRİMİ (O(1))!     |
+---------------------------------------------------------------------------------------------------+
```

```python
# KOD HÜCRESİ 2: Round-Robin Time-Slicing vs Non-Time-Slicing
# ------------------------------------------------------------------------------
# Aynı önceliğe sahip birden fazla görev hazır olduğunda:
# 1. configUSE_TIME_SLICING = 1: Her SysTick kesmesinde adil Round-Robin geçişi
# 2. configUSE_TIME_SLICING = 0: Bir görev bitene veya cooperatively yield edene kadar CPU'yu tutar.

import numpy as np

def simulate_round_robin(time_slicing_enabled=True, total_ticks=24):
    # 3 Adet Eşit Öncelikli Görev (Öncelik 2)
    # Her birinin 6 tick iş yükü var
    tasks = {
        "Fin_Actuator_Left":  {"rem": 6, "runs": []},
        "Fin_Actuator_Right": {"rem": 6, "runs": []},
        "Fin_Actuator_Rudder": {"rem": 6, "runs": []},
    }
    
    ready_queue = list(tasks.keys())
    timeline = []
    context_switch_count = 0
    last_task = None
    
    for tick in range(total_ticks):
        if not ready_queue:
            timeline.append("IDLE")
            continue
            
        current = ready_queue[0]
        
        if last_task is not None and last_task != current:
            context_switch_count += 1
        last_task = current
        
        tasks[current]["rem"] -= 1
        tasks[current]["runs"].append(tick)
        timeline.append(current)
        
        if tasks[current]["rem"] <= 0:
            # Görev tamamlandı -> Kuyruktan çıkar
            ready_queue.pop(0)
        else:
            if time_slicing_enabled:
                # Time-slicing aktif: Görevi kuyruğun en arkasına at (Round-Robin)
                ready_queue.pop(0)
                ready_queue.append(current)
            else:
                # Time-slicing kapalı: Görev işi bitene kadar kuyruğun başında kalır!
                pass
                
    return {
        "timeline": timeline,
        "context_switch_count": context_switch_count,
        "tasks": tasks
    }

res_ts_on = simulate_round_robin(time_slicing_enabled=True)
res_ts_off = simulate_round_robin(time_slicing_enabled=False)

print("=" * 68)
print("ROUND-ROBIN TIME-SLICING ETKİSİ (EŞİT ÖNCELİKLİ GÖREVLER)")
print("=" * 68)
print(f"Zaman Dilimleme AÇIK  (configUSE_TIME_SLICING = 1):")
print(f"  - Context Switch Sayısı : {res_ts_on['context_switch_count']} adet")
print(f"  - İlk 9 Tick Sıralaması: {res_ts_on['timeline'][:9]}")

print(f"\nZaman Dilimleme KAPALI (configUSE_TIME_SLICING = 0):")
print(f"  - Context Switch Sayısı : {res_ts_off['context_switch_count']} adet")
print(f"  - İlk 9 Tick Sıralaması: {res_ts_off['timeline'][:9]}")

# Doğrulama: Time slicing açıkken görevler 1'er tick sırayla koşmalı
assert res_ts_on["timeline"][0] != res_ts_on["timeline"][1], "Time-slicing açıkken ardışık tickler farklı görev olmalı!"
assert res_ts_off["timeline"][0] == res_ts_off["timeline"][1], "Time-slicing kapalıyken görev bitene kadar koşmalı!"
print("\n[BAŞARILI]: Round-Robin Time-Slicing adaleti ve context switch farkı doğrulandı.")
```

## 4. Eşit Öncelikler ve Round-Robin Zaman Dilimleme (Time-Slicing)

Gerçek zamanlı sistem tasarımında sıkça karşılaşılan bir soru şudur:
> *"Sistemde aynı önceliğe atanmış 2 veya daha fazla görev varsa Scheduler ne yapar?"*

FreeRTOS bu durumu iki konfigürasyon bayrağı ile yönetir:

### 1. `configUSE_PREEMPTION = 1` ve `configUSE_TIME_SLICING = 1` (Varsayılan Model)
- SysTick kesmesi (varsayılan 1 ms) her tetiklendiğinde, hazır listesindeki aynı öncelikli görevler arasında **Round-Robin** rotasyonu yapılır.
- Görev 1 bir zaman dilimi (time slice - 1 ms) koşar, ardından Görev 2'ye geçer, sonra Görev 3'e geçer.
- **Avantajı:** Adalet (Fairness). Hiçbir görev aynı öncelikteki kardeş görevini aç bırakamaz (starvation).
- **Dezavantajı:** Her 1 ms'de bir bağlam değiştirme (Context Switch) yaşanır; CPU overhead artar.

### 2. `configUSE_TIME_SLICING = 0` (Zaman Dilimlemesiz Preemptive Model)
- Aynı öncelikteki bir görev çalışmaya başladığında, SysTick kesmesi gelse dahi CPU'yu bırakmaz!
- Görev ancak şu üç durumda CPU'yu devreder:
  1. Kendisinden daha yüksek öncelikli bir görev uyandığında (Preemption),
  2. Bir kaynağı beklemek için bloke olduğunda (`vTaskDelay`, kuyruk bekleme),
  3. Kendi rızasıyla `taskYIELD()` çağırarak işlemciyi kardeşine devrettiğinde.
- **Kullanım Yeri:** Aviyonik füze kanat kontrolünde 4 kanatçık motorunun hesaplaması kesintisiz arka arkaya bitsin istendiğinde gereksiz context switch'leri önlemek için tercih edilir.

```python
# KOD HÜCRESİ 3: TCB Bellek Haritası ve Stack High Water Mark Analizörü
# ------------------------------------------------------------------------------
# FreeRTOS, görev yığınını 0xA5 deseniyle başlatır.
# Bu kod, bellek haritasını, yığının aşağı doğru büyümesini (Full Descending Stack)
# ve uxTaskGetStackHighWaterMark() fonksiyonunun çalışma prensibini modeller.

class SimulatedTCB:
    def __init__(self, name, priority, stack_size_words=256):
        self.name = name
        self.priority = priority
        self.stack_size_words = stack_size_words
        self.stack_size_bytes = stack_size_words * 4
        
        # 1. Yığını FreeRTOS standardı olan 0xA5 deseniyle doldur
        self.stack_memory = bytearray([0xA5] * self.stack_size_bytes)
        
        # ARM Cortex-M Full-Descending Stack: Yığın en yüksek adresten başlar, aşağı büyür
        self.stack_base_offset = 0 # En alt adres (Taşma sınırı)
        self.stack_top_offset = self.stack_size_bytes # Başlangıç SP adresi (Full-descending stack)
        self.current_sp = self.stack_top_offset
        
    def simulate_push(self, num_bytes):
        """Fonksiyon çağrısı veya yerel değişken tahsisi (Yığın aşağı büyür)"""
        new_sp = self.current_sp - num_bytes
        if new_sp < self.stack_base_offset:
            raise MemoryError(f"CRITICAL STACK OVERFLOW! Task '{self.name}' yığın sınırını {abs(new_sp)} bayt aştı!")
            
        # Belleği rastgele çalışma verisiyle ez (0xA5 desenini boz)
        for offset in range(new_sp, self.current_sp):
            self.stack_memory[offset] = 0x55 # Çalışma verisi
        self.current_sp = new_sp
        
    def simulate_pop(self, num_bytes):
        """Fonksiyon dönüşü (SP yukarı çıkar, ancak eski veri bellekte kalır)"""
        self.current_sp = min(self.stack_top_offset, self.current_sp + num_bytes)

    def get_stack_high_water_mark(self):
        """uxTaskGetStackHighWaterMark(): Taban adresinden itibaren bozulmamış 0xA5 sayısını say"""
        unused_bytes = 0
        for byte_val in self.stack_memory:
            if byte_val == 0xA5:
                unused_bytes += 1
            else:
                break
        # FreeRTOS bu değeri KELİME (Word = 4 bayt) cinsinden döndürür
        return unused_bytes // 4

# Test Senaryosu: 1024 Baytlık (256 Word) Aviyonik Telemetri Görevi
tcb = SimulatedTCB("TelemTask", priority=2, stack_size_words=256)

print("=" * 68)
print("TCB BELLEK HARİTASI VE STACK HIGH WATER MARK ANALİZİ")
print("=" * 68)
init_hwm = tcb.get_stack_high_water_mark()
print(f"Görev Başlatıldı (Toplam Yığın: {tcb.stack_size_bytes} bayt / {tcb.stack_size_words} kelime):")
print(f"  - Başlangıç Stack High Water Mark: {init_hwm} kelime (%{init_hwm/tcb.stack_size_words*100:.1f} boş alan)")

# 1. Normal Çalışma: 32 baytlık interrupt frame + 64 baytlık yerel değişken
tcb.simulate_push(96)
tcb.simulate_pop(64) # Fonksiyon döndü
hwm_step1 = tcb.get_stack_high_water_mark()
print(f"\nAdım 1: Normal Fonksiyon Çağrısı (96 bayt tepe tüketimi):")
print(f"  - Kalan High Water Mark: {hwm_step1} kelime ({hwm_step1*4} bayt hiç dokunulmadı)")

# 2. Ağır Yük: İç içe derin fonksiyon çağrıları (600 bayt tüketim)
tcb.simulate_push(600)
hwm_step2 = tcb.get_stack_high_water_mark()
print(f"\nAdım 2: Derin İç İçe Çağrılar (Toplam 696 bayt tepe tüketimi):")
print(f"  - Kalan High Water Mark: {hwm_step2} kelime ({hwm_step2*4} bayt kaldı!)")

# 3. Yığın Taşması Eşiği Testi
overflow_detected = False
try:
    # 400 bayt daha tahsis etmeye çalış (Toplam 1096 bayt > 1024 bayt!)
    tcb.simulate_push(400)
except MemoryError as e:
    overflow_detected = True
    print(f"\n[GÜVENLİK YAKALANDI]: {e}")

assert hwm_step1 == 256 - (96 // 4), "Adım 1 HWM hesabı doğru olmalı!"
assert overflow_detected == True, "HATA: Yığın taşması yakalanamadı!"
print("\n[BAŞARILI]: 0xA5 yığın deseni ve High Water Mark tespit mekanizması doğrulandı.")
```

## 5. TCB Anatomisi ve Yığın Güvenliği (Stack High Water Mark)

### TCB (Task Control Block) İç Yapısı
FreeRTOS çekirdeğinde her görevin durumu `TCB_t` yapısında saklanır. Bu yapı `tasks.c` içinde şu kritik alanlardan oluşur:

```c
typedef struct tskTaskControlBlock {
    volatile StackType_t *pxTopOfStack; /* Görevin geçerli Yığın İşaretçisi (PSP) - DAİMA İLK ELEMANDIR! */
    ListItem_t           xStateListItem;/* Hazır/Blokeli listesinde bulunma düğümü */
    ListItem_t           xEventListItem;/* Semafor/Kuyruk bekleme listesi düğümü */
    UBaseType_t          uxPriority;    /* Görevin sayısal önceliği */
    StackType_t          *pxStack;      /* Yığının başlangıç (en alt) bellek adresi */
    char                 pcTaskName[configMAX_TASK_NAME_LEN]; /* Görev adı (Debug için) */
    #if (configUSE_MUTEXES == 1)
        UBaseType_t      uxBasePriority;/* Öncelik Mirası (Inheritance) için orijinal öncelik */
    #endif
} tskTCB;
```

> **ASSEMBLY OPTİMİZASYON SIRRI:** `pxTopOfStack` elemanının yapının en başında (offset 0) bulunması tesadüf değildir! Cortex-M montaj kodunda `LDR R0, [R1]` komutu hiçbir ofset toplaması yapmadan doğrudan geçerli yığın işaretçisine erişir.

### Yığın Taşması Nasıl Yakalanır? (Stack Overflow Detection)
FreeRTOS iki farklı taşma kontrol yöntemi (`configCHECK_FOR_STACK_OVERFLOW`) sunar:
1. **Yöntem 1 (`Method 1`):** Her context switch sırasında `pxTopOfStack` değerinin `pxStack` taban sınırını aşıp aşmadığı kontrol edilir. (Hızlıdır ancak fonksiyon içinde geçici taşmaları kaçırabilir).
2. **Yöntem 2 (`Method 2`):** Yığının en altındaki son 16 baytın `0xA5` deseni kontrol edilir. Derin bir yerel dizi bu alanı ezmişse derhal yakalanır ve `vApplicationStackOverflowHook()` çağrılır!

```python
# KOD HÜCRESİ 4: Tickless Idle ve Güç Tüketimi Matematiksel Modeli
# ------------------------------------------------------------------------------
# Klasik RTOS: Her 1 ms'de bir SysTick kesmesi CPU'yu uyandırır (1000 uyandırma/sn).
# Tickless Idle: Gelecekteki ilk göreve kadar (örn. 50 ms) SysTick durdurulur,
# Low-Power Timer kurulur ve MCU STOP/STANDBY modunda derin uykuya dalar.

class LowPowerModel:
    def __init__(self, v_supply=3.3, i_run_ma=40.0, i_sleep_ma=0.015, battery_mah=2500):
        self.v_supply = v_supply
        self.i_run_ma = i_run_ma       # Aktif Mod Akımı (STM32 @ 168 MHz)
        self.i_sleep_ma = i_sleep_ma   # Düşük Güç Stop Modu Akımı (15 µA)
        self.battery_mah = battery_mah # 2500 mAh Li-Ion Pil
        
    def calculate_consumption(self, active_duty_cycle_percent=5.0, tickless_enabled=False):
        # active_duty_cycle_percent: Görevlerin gerçek CPU kullanma yüzdesi (örn. %5)
        # Geriye kalan %95 zamanda sistem boştadır (Idle)
        
        t_active_ratio = active_duty_cycle_percent / 100.0
        t_idle_ratio = 1.0 - t_active_ratio
        
        if not tickless_enabled:
            # Standart RTOS: Idle durumunda her 1 ms'de bir SysTick uyanır.
            # SysTick ISR süresi: ~20 µs = %2 ek çalışma yükü!
            # Ayrıca derin uykuya (STOP) geçilemez, sadece hafif uyku (WFI) kullanılır (i_idle = 8 mA)
            i_idle_mode_ma = 8.0
            avg_current_ma = (t_active_ratio * self.i_run_ma) + (t_idle_ratio * i_idle_mode_ma)
        else:
            # Tickless Idle: SysTick durdurulur, STOP modunda 15 µA tüketilir
            avg_current_ma = (t_active_ratio * self.i_run_ma) + (t_idle_ratio * self.i_sleep_ma)
            
        battery_hours = self.battery_mah / avg_current_ma
        battery_days = battery_hours / 24.0
        
        return {
            "avg_current_ma": avg_current_ma,
            "battery_hours": battery_hours,
            "battery_days": battery_days
        }

lp = LowPowerModel(v_supply=3.3, i_run_ma=45.0, i_sleep_ma=0.02, battery_mah=3000)

res_standard = lp.calculate_consumption(active_duty_cycle_percent=4.0, tickless_enabled=False)
res_tickless = lp.calculate_consumption(active_duty_cycle_percent=4.0, tickless_enabled=True)

energy_saving_percent = (1.0 - res_tickless["avg_current_ma"] / res_standard["avg_current_ma"]) * 100.0

print("=" * 68)
print("TICKLESS IDLE GÜÇ TÜKETİMİ VE PİL ÖMRÜ MATEMATİKSEL ANALİZİ")
print("=" * 68)
print(f"Standart Periyodik SysTick Modu (configUSE_TICKLESS_IDLE = 0):")
print(f"  - Ortalama Akım Tüketimi: {res_standard['avg_current_ma']:.2f} mA")
print(f"  - Pil Ömrü               : {res_standard['battery_days']:.1f} gün ({res_standard['battery_hours']:.0f} saat)")

print(f"\nTickless Idle Düşük Güç Modu (configUSE_TICKLESS_IDLE = 1):")
print(f"  - Ortalama Akım Tüketimi: {res_tickless['avg_current_ma']:.2f} mA")
print(f"  - Pil Ömrü               : {res_tickless['battery_days']:.1f} gün ({res_tickless['battery_hours']:.0f} saat)")
print(f"\nEnerji Tasarrufu Oranı   : %{energy_saving_percent:.2f}")

assert res_tickless["avg_current_ma"] < res_standard["avg_current_ma"], "Tickless idle daha az akım çekmeli!"
assert energy_saving_percent > 70.0, "Enerji tasarrufu %70'ten büyük olmalı!"
print("\n[BAŞARILI]: Tickless Idle mimarisinin batarya ömrünü katlama etkisi matematiksel olarak kanıtlandı.")
```

## 6. Boşta Görev (Idle Task), Kanca Fonksiyonları (Hooks) ve Tickless Idle

### Idle Task'in Görevleri Nelerdir?
`vTaskStartScheduler()` çağrıldığında FreeRTOS otomatik olarak **Priority 0 (En düşük öncelik)** seviyesinde `prvIdleTask` adında bir sistem görevi oluşturur:
1. **Hafıza Temizliği (Garbage Collection):** Kendisini silen bir görev (`vTaskDelete(NULL)`) kendi yığınını silemez çünkü hala o yığının içinde koşmaktadır! Silinen görevlerin TCB ve Stack belleklerini serbest bırakma işi Idle Task'e aittir.
2. **Idle Hook (`vApplicationIdleHook`):** Sistem boştayken çalışacak kullanıcı kodudur (örn. Watchdog tazeleme, arka plan CRC testi, LED yakıp söndürme).

### Tickless Idle Mimarisi: Pil Ömrünü Katlayan Çözüm
Geleneksel RTOS'larda her 1 milisaniyede SysTick kesmesi gelir. Bu durum bataryalı gömülü sistemlerde felakettir:
- İşlemci tam uykuya dalacakken 1 ms sonra SysTick kesmesiyle zorla uyandırılır!
- **Tickless Idle (`configUSE_TICKLESS_IDLE = 1`)**:
  1. Scheduler hazırda hiçbir görev olmadığını ve bir sonraki görevin 50 ms sonra uyanacağını tespit eder.
  2. SysTick sayacını geçici olarak durdurur.
  3. Düşük güçlü bir donanım zamanlayıcısını (LPTIM veya RTC) 50 ms sonraya ayarlar.
  4. İşlemciyi derin uyku moduna (`WFI - Wait For Interrupt` / STOP) sokar.
  5. 50 ms sonra uyandığında SysTick değişkenini tek seferde 50 artırarak zamanı telafi eder!

```python
# KOD HÜCRESİ 5: Savunma Sanayii Aviyonik Senaryosu: Füze Uçuş Bilgisayarı
# ------------------------------------------------------------------------------
# ROKETSAN Füze Güdüm Bilgisayarı Görev Seti Simülasyonu:
# - Task 1: INS Navigation EKF (Prio 4, 10 ms periyot, 2 ms WCET)
# - Task 2: Fin Control PWM    (Prio 4, 10 ms periyot, 2 ms WCET - Time-Sliced!)
# - Task 3: Mission FSM        (Prio 2, 20 ms periyot, 3 ms WCET)
# - Task 4: Telemetry Link     (Prio 1, 50 ms periyot, 5 ms WCET)
# - Task 0: Idle Task          (Prio 0, Arka plan sistem sağlığı)
# Simülasyon 100 ms boyunca görev durumlarını ve CPU kullanımını kaydeder.

import numpy as np

def simulate_missile_flight_computer(sim_duration_ms=100, tick_ms=1):
    ticks = int(sim_duration_ms / tick_ms)
    time_axis = np.arange(0, sim_duration_ms, tick_ms)
    
    tasks = {
        "INS_EKF":     {"prio": 4, "period": 10, "wcet": 2, "rem": 0, "next_wake": 0, "state_history": []},
        "Fin_Actuator":{"prio": 4, "period": 10, "wcet": 2, "rem": 0, "next_wake": 0, "state_history": []},
        "Mission_FSM": {"prio": 2, "period": 20, "wcet": 3, "rem": 0, "next_wake": 0, "state_history": []},
        "Telemetry":   {"prio": 1, "period": 50, "wcet": 5, "rem": 0, "next_wake": 0, "state_history": []},
    }
    
    cpu_running_history = []
    
    # Eşit öncelikli görevler için Round-Robin kuyruğu
    prio4_rr_turn = 0
    
    for t in time_axis:
        # 1. Periyodu gelen görevleri READY yap
        for name, tinfo in tasks.items():
            if t >= tinfo["next_wake"]:
                tinfo["rem"] = tinfo["wcet"]
                tinfo["next_wake"] += tinfo["period"]

        # 2. Hazır görevleri filtrele
        ready_tasks = [name for name, tinfo in tasks.items() if tinfo["rem"] > 0]
        
        # 3. En yüksek önceliği bul
        if not ready_tasks:
            current_task = "Idle_Task"
        else:
            max_prio = max(tasks[name]["prio"] for name in ready_tasks)
            candidates = [name for name in ready_tasks if tasks[name]["prio"] == max_prio]
            
            if len(candidates) > 1:
                # Eşit öncelikli görevlerde Time-Slicing Round-Robin
                current_task = candidates[prio4_rr_turn % len(candidates)]
                prio4_rr_turn += 1
            else:
                current_task = candidates[0]
                
        cpu_running_history.append(current_task)
        
        # 4. Çalışan görevin süresini azalt ve durumları kaydet
        if current_task != "Idle_Task":
            tasks[current_task]["rem"] -= tick_ms
            
        for name, tinfo in tasks.items():
            if current_task == name:
                st = "RUNNING"
            elif tinfo["rem"] > 0:
                st = "READY"
            else:
                st = "BLOCKED"
            tinfo["state_history"].append(st)

    return {
        "time_axis": time_axis,
        "cpu_running_history": cpu_running_history,
        "tasks": tasks
    }

missile_sim = simulate_missile_flight_computer()

print("=" * 68)
print("ROKETSAN FÜZE GÜDÜM BİLGİSAYARI ÇOKLU GÖREV ÇALIŞMA RAPORU (100 ms)")
print("=" * 68)
cpu_counts = {}
for t_name in missile_sim["cpu_running_history"]:
    cpu_counts[t_name] = cpu_counts.get(t_name, 0) + 1

for t_name, count in sorted(cpu_counts.items(), key=lambda x: -x[1]):
    print(f"  - {t_name:<15}: %{count/100*100:5.1f} CPU Zamanı ({count} ms)")

# Doğrulama: Tüm görevler başarıyla çalışmış olmalı
assert cpu_counts["INS_EKF"] == 20, "INS_EKF 10 periyot x 2 ms = 20 ms koşmalı!"
assert cpu_counts["Fin_Actuator"] == 20, "Fin_Actuator 10 periyot x 2 ms = 20 ms koşmalı!"
assert cpu_counts["Mission_FSM"] == 15, "Mission_FSM 5 periyot x 3 ms = 15 ms koşmalı!"
assert cpu_counts["Telemetry"] == 10, "Telemetry 2 periyot x 5 ms = 10 ms koşmalı!"
assert cpu_counts["Idle_Task"] == 35, "Idle Task kalan 35 ms'yi doldurmalı!"
print("\n[BAŞARILI]: Füze uçuş bilgisayarı görev seti %100 deterministik zamanlamayla tamamlandı.")
```

## 7. Savunma Sanayii Aviyonik Senaryosu (ROKETSAN Füze Bilgisayarı)

Füze aviyonik mimarisinde görevlerin öncelik dağılımı rastgele yapılamaz. Yanlış bir önceliklendirme füzenin hedeften kilometrelerce sapmasına neden olur:

### Taktik Füze Görev Öncelik Hiyerarşisi
1. **Öncelik 4 (Uçuş Emniyeti - Hard Real-Time):**
   - **`INS_EKF` (100 Hz / 10 ms):** Gyro ve ivmeölçer verilerini entegre ederek anlık konum, hız ve açısal yönelimi hesaplar.
   - **`Fin_Actuator` (100 Hz / 10 ms):** Hesaplanan açıları 4 bağımsız elektromekanik kanatçığa PWM sinyali olarak uygular. Time-Slicing ile EKF ile işlemciyi eşit paylaşır.
2. **Öncelik 2 (Görev Yönetimi - Firm Real-Time):**
   - **`Mission_FSM` (50 Hz / 20 ms):** Uçuş fazı geçişlerini yönetir: Fırlatma -> Güdüm -> Hedef Arama -> Terminal Vuruş.
3. **Öncelik 1 (Taktik Veri Bağı - Soft Real-Time):**
   - **`Telemetry` (20 Hz / 50 ms):** Yer istasyonuna kriptolu telemetri paketleri yayınlar.
4. **Öncelik 0 (Idle Hook):**
   - Pil gerilimi, işlemci sıcaklığı izleme ve arka plan Flash ROM CRC doğrulaması.

Toplam işlemci yükü:
$$U = \frac{2}{10} + \frac{2}{10} + \frac{3}{20} + \frac{5}{50} = 0.20 + 0.20 + 0.15 + 0.10 = 0.65\quad (\%65)$$
Liu & Layland sınırının ($n=4 \implies \%75.6$) altında kaldığı için sistem **%100 matematiksel güvenceyle çizelgelenebilirdir!**

```python
# KOD HÜCRESİ 6: Endüstriyel Dashboard Görselleştirme ve Kapsamlı Assertions
# ------------------------------------------------------------------------------
# 300 DPI, Dark Theme (#0F172A), 4 Panelli Endüstriyel Aviyonik Dashboard:
# Panel 1: Görev Durum Makinesi Yaşam Döngüsü (Running, Ready, Blocked)
# Panel 2: Eşit Öncelikli Görevlerde Round-Robin Time-Slicing Dağılımı
# Panel 3: TCB Bellek Haritası ve Stack High Water Mark (0xA5 Deseni)
# Panel 4: Klasik Tick vs Tickless Idle Güç Tüketimi Karşılaştırması

import os
import matplotlib.pyplot as plt
import numpy as np

# PNG Dosya Yolu
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_180_task_thread_ve_scheduler.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_180\gun_180_task_thread_ve_scheduler.png"

# Koyu Tema Ayarları
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#475569'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.tick_params(colors='#E2E8F0', labelsize=9)
    ax.xaxis.label.set_color('#F8FAFC')
    ax.yaxis.label.set_color('#F8FAFC')
    ax.title.set_color('#38BDF8')
    ax.grid(True, linestyle='--', alpha=0.25, color='#94A3B8')

# ------------------------------------------------------------------------------
# PANEL 1: Görev Durum Makinesi Yaşam Döngüsü (Gantt Chart)
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. Görev Durum Makinesi Yaşam Döngüsü (İlk 30 ms)", fontsize=11, fontweight='bold', pad=10)

t_limit = 30
task_colors = {"INS_EKF": "#38BDF8", "Fin_Actuator": "#10B981", "Mission_FSM": "#F59E0B", "Telemetry": "#EC4899", "Idle_Task": "#64748B"}
y_levels = {"INS_EKF": 4, "Fin_Actuator": 3, "Mission_FSM": 2, "Telemetry": 1, "Idle_Task": 0}

for idx, t_name in enumerate(missile_sim["cpu_running_history"][:t_limit]):
    ax1.barh(y_levels[t_name], 1, left=idx, color=task_colors[t_name], height=0.7, edgecolor='none')

ax1.set_yticks(list(y_levels.values()))
ax1.set_yticklabels(list(y_levels.keys()), fontweight='bold')
ax1.set_xlabel("Zaman (ms)", fontsize=10)
ax1.set_xlim(0, t_limit)

# ------------------------------------------------------------------------------
# PANEL 2: Round-Robin Time-Slicing Karşılaştırması
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. Eşit Öncelikli Görevlerde Round-Robin Time-Slicing (1 ms Dilimler)", fontsize=11, fontweight='bold', pad=10)

ts_tasks = ["Fin_Left", "Fin_Right", "Fin_Rudder"]
c_map = {"Fin_Actuator_Left": "#38BDF8", "Fin_Actuator_Right": "#10B981", "Fin_Actuator_Rudder": "#F59E0B"}

# Time Slicing AÇIK (Üst)
for i, t_act in enumerate(res_ts_on["timeline"][:18]):
    ax2.barh(1.8, 1, left=i, color=c_map[t_act], height=0.5, edgecolor='#0F172A')

# Time Slicing KAPALI (Alt)
for i, t_act in enumerate(res_ts_off["timeline"][:18]):
    ax2.barh(0.8, 1, left=i, color=c_map[t_act], height=0.5, edgecolor='#0F172A')

ax2.set_yticks([0.8, 1.8])
ax2.set_yticklabels(["Time-Slicing KAPALI", "Time-Slicing AÇIK"], fontweight='bold')
ax2.set_xlabel("Zaman Dilimi (Ticks)", fontsize=10)
ax2.set_xlim(0, 18)
ax2.text(2, 2.15, "Adil Dağılım: Sırayla 1'er Tick", color='#38BDF8', fontsize=9, fontweight='bold')
ax2.text(2, 1.15, "Bloklayıcı Dağılım: Biri Bitmeden Diğeri Başlamaz", color='#EF4444', fontsize=9, fontweight='bold')

# ------------------------------------------------------------------------------
# PANEL 3: TCB Bellek Haritası ve Stack High Water Mark
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. TCB Yığın Bellek Haritası ve High Water Mark (0xA5 Deseni)", fontsize=11, fontweight='bold', pad=10)

stack_depth = np.arange(0, 256) # 256 kelime
# 0..74 kelime: Kullanılmamış 0xA5 deseni
# 75..255 kelime: Kullanılmış çalışma alanı
memory_profile = np.array([1 if i < hwm_step2 else 2 for i in stack_depth])

ax3.bar(stack_depth[:hwm_step2], np.ones(hwm_step2), color='#10B981', width=1.0, label=f'Dokunulmamış Alan (0xA5): {hwm_step2} Kelime')
ax3.bar(stack_depth[hwm_step2:], np.ones(256 - hwm_step2), color='#EF4444', width=1.0, label=f'Tepe Yığın Tüketimi: {256-hwm_step2} Kelime')

ax3.axvline(hwm_step2, color='#F59E0B', linestyle='--', linewidth=2, label=f'High Water Mark Sınırı ({hwm_step2*4} Bayt)')
ax3.set_xlabel("Yığın Ofseti (Kelimeler - 4 Bayt)", fontsize=10)
ax3.set_ylabel("Doluluk Durumu", fontsize=10)
ax3.set_xlim(0, 256)
ax3.set_ylim(0, 1.5)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 4: Klasik Tick vs Tickless Idle Güç Tüketimi
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. Düşük Güç Analizi: Klasik SysTick vs Tickless Idle", fontsize=11, fontweight='bold', pad=10)

modes = ["Klasik SysTick (1000 Hz)", "Tickless Idle (LPTIM)"]
currents = [res_standard["avg_current_ma"], res_tickless["avg_current_ma"]]
battery_days = [res_standard["battery_days"], res_tickless["battery_days"]]

x_pos = np.arange(len(modes))
ax4_bar = ax4.bar(x_pos, currents, width=0.45, color=['#EF4444', '#10B981'], edgecolor='#475569')

ax4.set_xticks(x_pos)
ax4.set_xticklabels(modes, fontweight='bold')
ax4.set_ylabel("Ortalama Akım Tüketimi (mA)", fontsize=10)
ax4.set_ylim(0, 15)

for i, bar in enumerate(ax4_bar):
    h = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2, h + 0.4, f"{h:.2f} mA\n({battery_days[i]:.1f} Gün Pil)", 
             ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=9)

# Görseli Kaydet
plt.tight_layout()
plt.savefig(PNG_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

# ------------------------------------------------------------------------------
# KATI DOĞRULAMA (ASSERTIONS)
# ------------------------------------------------------------------------------
assert os.path.exists(PNG_FILE), f"HATA: Dashboard görseli üretilemedi: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"\n[+] Visual Artifact Oluşturuldu: {PNG_FILE} ({png_size:,} bayt)")
assert png_size > 100000, f"HATA: Görsel boyutu 100 KB'den küçük ({png_size} bayt)!"

# Simülasyon Doğrulamaları
assert cpu_counts["INS_EKF"] == 20, "HATA: INS_EKF çalışma süresi tutarsız!"
assert cpu_counts["Idle_Task"] == 35, "HATA: Idle task çalışma süresi tutarsız!"
assert res_ts_on["context_switch_count"] > res_ts_off["context_switch_count"], "HATA: Time-slicing daha çok context switch üretmeli!"
assert energy_saving_percent > 70.0, "HATA: Tickless tasarrufu hesaplama hatası!"

print("[PASS] GÜN 180: TÜM MATEMATİKSEL VE GÖRSEL DOĞRULAMALAR BAŞARIYLA TAMAMLANDI!")
```

## 8. C++20 ile Task ve Scheduler Entegrasyonu (Modern C++)

C++20, FreeRTOS görevlerini tip-güvenli (type-safe), nesne yönelimli ve derleme zamanı (compile-time) garantili sınıflara dönüştürür:

### Tip-Güvenli Modern C++20 Görev Sınıfı
Geleneksel C dilindeki `void *pvParameters` cast işlemlerinin getirdiği bellek bozulmalarını C++20 şablonları (Templates) ve `std::invocable` konseptleri ile tamamen ortadan kaldırırız:

```cpp
#include "FreeRTOS.h"
#include "task.h"
#include <concepts>
#include <array>
#include <string_view>

template <size_t StackWords, UBaseType_t Priority>
class RtosTask {
public:
    template <typename Callable>
    requires std::invocable<Callable>
    void start(std::string_view name, Callable&& callable) {
        callable_holder_ = [c = std::forward<Callable>(callable)]() mutable { c(); };
        
        handle_ = xTaskCreateStatic(
            &RtosTask::task_entry_point,
            name.data(),
            StackWords,
            this,
            Priority,
            stack_buffer_.data(),
            &tcb_
        );
    }

    void suspend() noexcept { if (handle_) vTaskSuspend(handle_); }
    void resume() noexcept  { if (handle_) vTaskResume(handle_); }

    [[nodiscard]] UBaseType_t get_high_water_mark() const noexcept {
        return uxTaskGetStackHighWaterMark(handle_);
    }

private:
    static void task_entry_point(void* param) {
        auto* self = static_cast<RtosTask*>(param);
        self->callable_holder_();
        vTaskDelete(nullptr); // Görev sonlanırsa kendini temizle
    }

    std::array<StackType_t, StackWords> stack_buffer_{};
    StaticTask_t tcb_{};
    TaskHandle_t handle_{nullptr};
    std::function<void()> callable_holder_{};
};

// KULLANIM:
void flight_init() {
    static RtosTask<512, 4> ins_task;
    ins_task.start("INS_EKF", []() {
        TickType_t xLastWakeTime = xTaskGetTickCount();
        for (;;) {
            vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(10));
            run_ekf_fusion();
        }
    });
}
```

## 9. DO-178C ve Emniyet Kritik Sistemlerde Scheduler Tasarımı

Sivil ve askeri havacılıkta (DO-178C DAL-A/B) görev çizelgeleyicisi tasarlanırken katı kurallar uygulanır:

1. **Statik Görev Tahsisi Zorunluluğu:**
   - Görevler yalnızca sistem önyüklemesi (Boot) sırasında oluşturulabilir (`xTaskCreateStatic`).
   - Uçuş sırasında çalışma anında hiçbir görev silinemez veya yeni görev açılamaz! Görev oluşturma ve silme fonksiyonlarının dinamik çağrılması yasaktır.
2. **Kritik Süreçler İçin `Time-Slicing` Yasaklanması:**
   - Eşit öncelikli görevler arasında öngörülemeyen zaman dilimleme jitter'ı yaratmamak için DO-178C seviye A sistemlerde genellikle **her göreve benzersiz bir öncelik (Unique Priority)** atanır.
3. **Maksimum Kesme Kapanma Süresi (Interrupt Latency Boundary):**
   - Çizelgeleyicinin kritik bölgeleri (Critical Sections) korumak için kesmeleri kapattığı süre (`taskENTER_CRITICAL()`) mikrodenetleyici saat çevrimi seviyesinde kanıtlanmalı ve donanım kesmelerini kaçırmayacağı garanti edilmelidir.

## 10. Bilerek Bozacağımız Şey: Stack Overflow ve Idle Task Starvation

Mühendisliği mükemmelleştiren şey, sistemin nasıl çöktüğünü ve o çöküşten nasıl kurtulacağını bilmektir.

### Bozma Senaryosu 1: Idle Task Starvation (Açlık Çökmesi)
1. Priority 1 veya daha yüksek bir görev yazın:
   ```c
   void vStarvingTask(void *pvParameters) {
       for (;;) {
           // HATA: Hiçbir vTaskDelay() veya bloklayıcı API çağırmadı!
           process_data_infinite();
       }
   }
   ```
2. Başka bir görevde `vTaskDelete(xOtherTaskHandle)` çağırın.
3. **Beklenen Çökme Belirtisi:** Priority 1 görevi CPU'yu %100 meşgul ettiği için Priority 0 seviyesindeki `prvIdleTask` asla çalışamaz!
   - Silinen görevin belleği temizlenemez (RAM sızıntısı),
   - Idle Hook çağrılamaz,
   - Sistem bir süre sonra RAM yetersizliğinden veya Watchdog aşımından kilitlenir!
4. **Düzeltme:** Görevlerin içinde CPU'yu serbest bırakan `vTaskDelayUntil()` veya olay bazlı semafor bekleme çağrıları bulunmalıdır.

### Bozma Senaryosu 2: Yığın Taşması ve 0xA5 Bozulması
1. Görev stack boyutunu 64 kelime (256 bayt) olarak tanımlayın.
2. Görev içinde büyük bir dizi açın: `char log_msg[300]; sprintf(log_msg, "Data: %d", val);`.
3. **Beklenen Çökme Belirtisi:** Yığın işaretçisi `pxStack` sınırını deler, bitişikteki TCB verisini ezer. FreeRTOS Method 2 kontrolü son 16 bayttaki `0xA5` deseninin bozulduğunu fark eder ve sistemi güvenli kilitlenme fonksiyonuna (`vApplicationStackOverflowHook`) yönlendirir.

## 11. Hata Ayıklama ve Gözlemlenebilirlik (Tracing, DWT, Segger SystemView)

Çoklu görev ortamında klasik `printf` debug yöntemi yarış durumlarını (Race Conditions) maskeler (Heisenbug).

### 1. SEGGER SystemView ile Canlı Görev Takibi
FreeRTOS çekirdeği içine yerleştirilmiş Trace Hook makroları (`traceTASK_SWITCHED_IN`, `traceTASK_SWITCHED_OUT`) sayesinde SEGGER J-Link / SystemView donanımı minimum ek yükle (< %1 CPU) görev geçişlerini mikrosaniye çözünürlüğünde kaydeder.

### 2. ARM DWT Data Watchpoint ile Yığın Taşması Koruması
ARM Cortex-M işlemcilerdeki DWT donanımı, bir bellek adresine yazma yapıldığında işlemciyi donanımsal olarak durdurabilir:
```c
// Görevin en alt yığın adresine bir Hardware Watchpoint koy:
DWT->COMP[0] = (uint32_t)pxCurrentTCB->pxStack;
DWT->MASK[0] = 0; // Tek bayt hassasiyet
DWT->FUNCTION[0] = DWT_FUNCTION_DATAVSIZE_WORD | DWT_FUNCTION_FUNCTION_WATCH;
// Yığın işaretçisi bu adrese bir şey yazdığı anda CPU anında DebugTrap fırlatır!
```

## 12. Adım Adım C Kod Örneği: FreeRTOS Statik Görev ve Scheduler Başlatma

Aşağıda STM32F4/F7 üzerinde %100 statik bellek ile derlenebilen, sıfır heap maliyetli üretim seviyesi FreeRTOS şablonu yer almaktadır:

```c
#include "FreeRTOS.h"
#include "task.h"

#define INS_TASK_STACK_SIZE    256
#define FIN_TASK_STACK_SIZE    256

// Statik Yığın ve TCB Bellekleri
static StackType_t xInsStack[INS_TASK_STACK_SIZE];
static StaticTask_t xInsTCB;
static TaskHandle_t xInsTaskHandle = NULL;

static StackType_t xFinStack[FIN_TASK_STACK_SIZE];
static StaticTask_t xFinTCB;
static TaskHandle_t xFinTaskHandle = NULL;

// FreeRTOS Statik Idle Task Bellek Sağlayıcısı (Zorunlu Callback)
void vApplicationGetIdleTaskMemory(StaticTask_t **ppxIdleTaskTCBBuffer,
                                  StackType_t **ppxIdleTaskStackBuffer,
                                  uint32_t *pulIdleTaskStackSize) {
    static StaticTask_t xIdleTCB;
    static StackType_t uxIdleStack[configMINIMAL_STACK_SIZE];
    *ppxIdleTaskTCBBuffer = &xIdleTCB;
    *ppxIdleTaskStackBuffer = uxIdleStack;
    *pulIdleTaskStackSize = configMINIMAL_STACK_SIZE;
}

// 1. Görev: INS Ataletsel Seyrüsefer
void vInsTask(void *pvParameters) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(10); // 10 ms periyot (100 Hz)

    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        read_gyro_accel();
        update_ekf_navigation();
    }
}

// 2. Görev: Kanatçık PWM Çıkışı (Eşit Öncelikli)
void vFinTask(void *pvParameters) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(10);

    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        calculate_fin_deflection();
        apply_pwm_to_servos();
    }
}

int main(void) {
    hardware_clock_init();

    // Statik Görevleri Oluştur
    xInsTaskHandle = xTaskCreateStatic(
        vInsTask, "INS_Task", INS_TASK_STACK_SIZE, NULL, 4, xInsStack, &xInsTCB
    );

    xFinTaskHandle = xTaskCreateStatic(
        vFinTask, "Fin_Task", FIN_TASK_STACK_SIZE, NULL, 4, xFinStack, &xFinTCB
    );

    // Çizelgeleyiciyi Başlat (Asla geri dönmez)
    vTaskStartScheduler();

    for (;;); // Ulaşılırsa RAM yetersizliği veya donanım hatası vardır
}
```

## 13. Sık Yapılan Hatalar ve Anti-Pattern'ler

| Hata / Anti-Pattern | Neden Tehlikeli? | Doğru Tasarım Deseni |
|:---|:---|:---|
| **Görev Fonksiyonundan `return` Etmek** | Görev fonksiyonu bir döngüden çıkıp `return` ederse geçerli yığın çöker ve HardFault oluşur. | Görev işi bittiğinde mutlaka `vTaskDelete(NULL)` çağrılarak kontrollü silinmelidir. |
| **`vTaskDelay` ile Sıkı Periyot Beklemek** | `vTaskDelay(10)` görevin çalışma süresini hesaba katmaz; periyot zamanla kayar (Time Drift). | Mutlak periyodik zamanlama için `vTaskDelayUntil()` kullanılmalıdır. |
| **Idle Task'i Aç Bırakmak (Starvation)** | Hiçbir görevin bloke olmaması Idle Task'i engeller, bellek temizliği yapılamaz. | Tüm periyodik görevler `vTaskDelayUntil` veya kuyruk beklemesi ile CPU'yu düzenli bırakmalıdır. |
| **Yığın Boyutunu Bayt ile Karıştırmak** | `xTaskCreate`'e verilen yığın boyutu STM32'de **Kelime (Word = 4 Bayt)** cinsindendir. 256 yazarsanız 1024 bayt tahsis edilir! | Boyut hesabını yaparken `sizeof(StackType_t)` katsayısını unutmayın. |
| **ISR İçinde Normal Task API Çağırmak** | Kesme rutininde `xTaskResume` veya `vTaskDelay` çağrılırsa çekirdek kilitlenir. | Kesmelerde yalnızca `FromISR` son ekli fonksiyonlar kullanılmalıdır. |

## 14. 5N1K Tablosu: Task ve Scheduler Mimarisi

| Soru | Aviyonik ve Gömülü Sistem Yanıtı |
|:---|:---|
| **Ne?** | Bağımsız yığınlara sahip görevleri öncelik kurallarına göre işlemciye atayan deterministik işletim sistemi bileşeni. |
| **Neden?** | Tek bir CPU çekirdeğinde birden fazla gerçek zamanlı işlevi deterministik, adil ve emniyetli olarak paylaştırmak için. |
| **Nerede?** | STM32 ARM Cortex-M donanımında, NVIC, SysTick ve PendSV istisnaları üzerinde. |
| **Nasıl?** | Donanımsal O(1) Bitmask CLZ arama, hazır listeleri ve Round-Robin zaman dilimleme algoritmalarıyla. |
| **Ne Zaman?** | Mikrodenetleyici başlatıldıktan sonra `vTaskStartScheduler()` çağrıldığı andan itibaren kesintisiz olarak. |
| **Kim?** | Aviyonik yazılım mimarı, gömülü sistem kontrol mühendisi ve gerçek zamanlı çekirdek geliştiricisi. |

## 15. İleri Düzey Okuma ve Kaynaklar

1. **FreeRTOS Source Code Architecture:** `tasks.c` ve `queue.c` dosyalarının mimari incelemesi.
2. **ARM Cortex-M Generic User Guide:** `CLZ` (Count Leading Zeros) ve `SVC` / `PendSV` donanım referans kılavuzu.
3. **Zephyr Project Documentation - Scheduling:** Zephyr RTOS'un çok kuyruklu (Multi-Queue) ve kırmızı-siyah ağaç (Red-Black Tree) tabanlı EDF çizelgeleyicisi.
4. **Jean J. Labrosse - MicroC/OS-III The Real-Time Kernel:** O(1) çizelgeleme tabloları ve bellek koruma birimleri üzerine klasik eser.
5. **DO-178C Tool Qualification & Structural Coverage:** Havacılıkta RTOS doğrulama süreçleri.

## 16. Günün Mini Projesi ve Sınav Soruları

### Mini Proje Görevi
STM32F4 üzerinde FreeRTOS kullanarak:
1. İki adet eşit öncelikli (Öncelik 3) görev oluşturun: `Task_Motor_A` ve `Task_Motor_B`.
2. `FreeRTOSConfig.h` içinde önce `configUSE_TIME_SLICING = 1`, ardından `0` yaparak bir mantıksal analizör (Logic Analyzer) veya DWT sayaçları ile görev geçiş frekansını osiloskopta gözlemleyin.
3. `uxTaskGetStackHighWaterMark()` ile her iki görevin yığın emniyet payını ekrana yazdırın.

---

### Günün Sınav Soruları

#### Soru 1: FreeRTOS'ta `configUSE_PORT_OPTIMISED_TASK_SELECTION = 1` ayarlandığında, ARM Cortex-M donanımı en yüksek öncelikli hazır görevi hangi komutla O(1) karmaşıklığında bulur?
- A) `NOP`
- B) `CLZ` (Count Leading Zeros)
- C) `WFI` (Wait For Interrupt)
- D) `LDMIA`
- **Doğru Cevap: B**

#### Soru 2: FreeRTOS bir görevi başlatırken yığın (stack) belleğini hangi sabit bayt deseniyle doldurur?
- A) `0x00`
- B) `0xFF`
- C) `0xA5`
- D) `0xDE`
- **Doğru Cevap: C**

#### Soru 3: Eşit önceliğe sahip 2 görev hazır durumdayken, `configUSE_TIME_SLICING = 1` olduğunda görevler işlemciyi nasıl paylaşır?
- A) Biri tamamen bitene kadar diğeri bekler.
- B) Her SysTick kesmesinde (Round-Robin) sırayla 1'er zaman dilimi koşarlar.
- C) Önceliği yüksek olan göreve otomatik terfi edilir.
- D) Görevler aynı anda çift çekirdekte koşar.
- **Doğru Cevap: B**

#### Soru 4: Bir görev kendisini silmek istediğinde (`vTaskDelete(NULL)`), görev yığınının ve TCB belleğinin serbest bırakılmasından hangi sistem görevi sorumludur?
- A) SysTick Kesmesi
- B) PendSV İstisnası
- C) Idle Task (Boşta Görev)
- D) Watchdog Timer
- **Doğru Cevap: C**

#### Soru 5: Bataryalı bir gömülü sistemde `Tickless Idle` modu etkinleştirildiğinde ne gerçekleşir?
- A) İşlemci saat frekansı iki katına çıkarılır.
- B) SysTick kesmesi geçici olarak durdurulur ve MCU LPTIM ile bir sonraki görev vaktine kadar derin uyku moduna geçer.
- C) Görevlerin öncelikleri sıfırlanır.
- D) RAM belleği Flash'a yedeklenir.
- **Doğru Cevap: B**

## 17. Gün Sonu Özeti ve Yarının Ön İzlemesi

### 3 Cümlelik Kapanış Özeti
1. **Task ve Scheduler Nedir?** Task, bağımsız yığın ve CPU kayıt bağlamına sahip yürütme birimidir; Scheduler ise bu görevleri öncelik kurallarına göre işlemciye atayan deterministik orkestra şefidir.
2. **Hangi Problemi Çözer?** Sistemdeki çok sayıda bağımsız periyodik ve asenkron işlevin tek çekirdek üzerinde adil, öngörülebilir ve $O(1)$ karmaşıklığında yönetilmesini sağlar.
3. **Hangi Bedeli Getirir?** Her görev için ayrı yığın belleği ayrılması, bağlam değiştirme (Context Switch) çevrim kaybı ve yığın taşması (Stack Overflow) gibi kritik izleme gereksinimlerini getirir.

---

### Yarının Konusu (GÜN 181): Priority ve Preemption
Yarın F5 fazında RTOS derinleşmesine devam ederek:
- Öncelik seviyelerinin matematiksel tasarımı,
- Preemption anında NVIC kesme öncelikleri ile RTOS öncelikleri arasındaki kritik fark (`configMAX_SYSCALL_INTERRUPT_PRIORITY`),
- Kritik bölgelerin (Critical Sections) kesme gecikmesine (`Interrupt Latency`) etkisi ve
- Preemption kilitleri (`vTaskSuspendAll()`) konularını inceleyeceğiz!

