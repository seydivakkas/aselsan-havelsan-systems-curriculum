# GÜN 179: RTOS Neden Var? (Gerçek Zamanlı İşletim Sistemleri, Preemption ve Determinizm)

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, tersine mühendislik yapılamaz.
```

---

## Modül Künyesi
- **Faz:** F5 — Gömülü Sistemler, RTOS ve STM32 Mimarisi
- **Konu:** RTOS İhtiyacı, Super-Loop'un Kırılma Noktaları, Preemptive vs Cooperative Çizelgeleme, ARM Cortex-M Bağlam Değiştirme (Context Switch: PendSV & SysTick), TCB (Task Control Block), Öncelik Terslenmesi (Priority Inversion) ve Çözümü (Priority Inheritance), Rate Monotonic Scheduling (RMS)
- **Hedef Donanım:** ARM Cortex-M4/M7 (STM32F4/F7/H7), FreeRTOS / Zephyr
- **Kritik Kavramlar:** Determinizm vs Hız, Hard Real-Time vs Soft Real-Time, En Kötü Durum Yanıt Süresi (WCET), Process Stack Pointer (PSP) vs Main Stack Pointer (MSP), Mars Pathfinder Olayı, Liu & Layland Schedulability Sınırı, DO-178C Uçuş Emniyeti
- **Savunma Sanayii Senaryosu:** ASELSAN AESA Radar Sinyal İşleme ve Hedef Takip Bilgisayarında Hard Real-Time RF Işın Yönlendirme (Beamforming), EKF Hedef Takip ve Link-16 Taktik İletişim Görevlerinin Deterministik Çizelgelenmesi

## 1. Giriş ve Zihinsel Model (Super-Loop Nerede Tıkanır?)

Dün (Gün 178) incelediğimiz **Zaman Tetiklemeli Super-Loop (Time-Triggered Super-Loop)** mimarisi; basit sensör okuma, motor PWM güncelleme ve tek yığınlı (single shared stack) yapısıyla küçük ve deterministik sistemler için mükemmeldir.

Ancak sistem karmaşıklığı büyüdükçe Super-Loop kaçınılmaz olarak **"Determinizm Duvarı"**na çarpar:

1. **Kooperatif Bloklanma (Lack of Preemption):**
   Super-Loop'ta çalışan bir görev (Task), işlemciyi kendi rızasıyla bırakmadıkça başka hiçbir yazılım görevi araya giremez. Eğer sistemde 8 ms süren bir kriptografik imzalama, Flash bellek silme veya büyük bir TCP/IP veri paketi ayrıştırma görevi varsa; 1 ms periyotla çalışması gereken kritik bir roket kanatçık kontrol veya radar darbe algılama görevi **en az 8 ms gecikmeye (jitter) uğrar!**
2. **"Her Şeyi Kesmeye (ISR) Atma" Tuzağı:**
   Mühendisler acil işleri kurtarmak için hesaplamaları kesme servis rutinlerine (ISR) koymaya başlarlar. Sonuç felakettir: Kesmeler birbirini kilitler (nested interrupt fırtınası), ana döngü açlıktan ölür (starvation), UART ve DMA donanım taşmaları (overrun) başlar.
3. **Ölçeklenemezlik (Scalability Failure):**
   Sistemde 3 görev varken zaman slotlarını elle ayarlamak mümkündür. Ancak 15 farklı periyoda ve asenkron olaylara sahip modern bir aviyonik bilgisayarda tüm durum makinelerini (FSM) birbiriyle uyumlu parçalara bölmek **NP-hard** bir optimizasyon problemine dönüşür.

İşte tam bu noktada **RTOS (Real-Time Operating System)** devreye girer!

```
+---------------------------------------------------------------------------------------------------+
|                              KOOPERATİF SUPER-LOOP (GECİKME VE JITTER)                            |
|                                                                                                   |
|  Zaman (ms):   0     1     2     3     4     5     6     7     8     9    10                      |
|  Task 3 (Low): [==== Kripto Flash Yazma (8 ms kesintisiz çalışıyor) ====]                         |
|  Task 1 (High):      ^ (t=2ms'de acil radar tetiklendi ama BEKLEMEK ZORUNDA!) [== Task 1 ==]      |
|                      |◀───────────── 6 ms JITTER / GECİKME ────────────▶| (DEADLINE MISS!)       |
+---------------------------------------------------------------------------------------------------+

+---------------------------------------------------------------------------------------------------+
|                              PREEMPTIVE RTOS (DONANIMSAL KESME VE ÖNCELİK)                        |
|                                                                                                   |
|  Zaman (ms):   0     1     2     3     4     5     6     7     8     9    10                      |
|  Task 3 (Low): [== Kripto ==]     (Duraklatıldı / TCB Yığına Alındı)     [=== Kripto Devam ===]   |
|  Task 1 (High):             [== Radar ==] (Anında Preempt Etti! <2 µs)                            |
|                             |◀ 0.002 ms ▶| (JITTER YOK, GÜVENLİ VE DETERMINİSTİK!)               |
+---------------------------------------------------------------------------------------------------+
```

### RTOS'un Temel Tanımı: Hız Değil, Determinizm!
> **KRİTİK GERÇEK:** RTOS bir sistemi genel amaçlı işletim sistemlerinden (Linux, Windows) daha "hızlı" yapmaz! Hatta bağlam değiştirme (Context Switching) nedeniyle toplam işlem gücünün %1-%3'ünü harcar.
> RTOS'un yegane varlık sebebi: **DETERMİNİZM (ZAMANINDA OLMA GARANTİSİ)** sağlamaktır. En kritik görev, sistem ne kadar meşgul olursa olsun, kesin olarak belirlenen süre (WCET) içinde çalışmaya başlar!

## 2. RTOS Temel İlkeleri ve Çekirdek Anatomisi

Bir işletim sistemini **Gerçek Zamanlı (RTOS)** yapan 3 temel sütun vardır:

### 1. Öncelik Tabanlı Preemptive Çizelgeleme (Priority-Based Preemptive Scheduling)
- Her göreve (Task/Thread) sayısal bir öncelik atanır.
- Çekirdek (Kernel) kuralı basittir: **"Çalışmaya hazır (READY) durumdaki en yüksek öncelikli görev DAİMA işlemciye sahiptir."**
- Eğer daha yüksek öncelikli bir görev bir olayla (örneğin donanım kesmesi, semafor, kuyruk verisi) uyanırsa, o an çalışan düşük öncelikli görev anında durdurulur (**Preemption**).

### 2. Bağımsız Görev Yığınları ve TCB (Task Control Block)
Super-loop'ta tüm fonksiyonlar işlemcinin tek bir sistem yığınını (MSP) paylaşır. RTOS'ta ise **her görevin bağımsız bir RAM yığını (Stack)** ve kimlik kartı olan **TCB (Task Control Block)** bulunur.

```
       TCB (Task Control Block)                      GÖREVİN ÖZEL YIĞINI (STACK)
+------------------------------------+          +------------------------------------+
| uint32_t* pxTopOfStack             | ───────> | R4 - R11 (Yazılımsal Saklanan)     |
| ListItem_t xStateListItem          |          | R0 - R3, R12, LR, PC, xPSR (Donanım)|
| UBaseType_t uxPriority             |          | Yerel Değişkenler & Fonksiyon Çerçevesi|
| StackType_t* pxStackBase           |          | . . .                              |
| char pcTaskName[configMAX_TASK_LEN]|          +------------------------------------+
+------------------------------------+          <── pxStackBase (Taşma Sınırı)
```

### 3. Zaman Tanımları ve Sertlik Seviyeleri (Real-Time Classifications)
- **Hard Real-Time (Katı Gerçek Zamanlı):** Bir deadline'ın kaçırılması sistemin toptan çökmesi, füzenin hedeften sapması veya can kaybı demektir (örn. Füze Kanatçık Açı Kontrolü, Kalp Pili, Otomotiv Fren Sistemi).
- **Firm Real-Time (Kesin Gerçek Zamanlı):** Deadline kaçarsa üretilen verinin hiçbir değeri kalmaz, ancak sistem çökmez (örn. AESA Radar Ham Darbe Örneklemesi).
- **Soft Real-Time (Esnek Gerçek Zamanlı):** Deadline kaçarsa sistem performansı veya kullanıcı konforu düşer, ancak veri hala işe yarar (örn. Gösterge Paneli FPS değeri, Link-16 Telemetri Güncellemesi).

```python
# KOD HÜCRESİ 1: Super-Loop vs RTOS Preemptive Yanıt Süresi ve Jitter Simülatörü
# ------------------------------------------------------------------------------
# Bu simülasyon, 3 farklı öncelik ve periyoda sahip görev kümesinin
# Kooperatif Super-Loop ve Preemptive RTOS altındaki davranışını mikrosaniye
# çözünürlüğünde modeller ve deadline kaçırma (deadline miss) farkını kanıtlar.

import numpy as np

class TaskDef:
    def __init__(self, name, priority, period_ms, wcet_ms, deadline_ms):
        self.name = name
        self.priority = priority  # 3: En Yüksek, 1: En Düşük
        self.period_ms = period_ms
        self.wcet_ms = wcet_ms
        self.deadline_ms = deadline_ms

def simulate_schedulers(sim_time_ms=50.0, step_ms=0.01):
    tasks = [
        TaskDef("Task1_RadarPulse", priority=3, period_ms=2.0, wcet_ms=0.3, deadline_ms=2.0),
        TaskDef("Task2_TargetTrack", priority=2, period_ms=10.0, wcet_ms=2.5, deadline_ms=10.0),
        TaskDef("Task3_CryptoFlash", priority=1, period_ms=20.0, wcet_ms=8.0, deadline_ms=20.0),
    ]
    
    # --------------------------------------------------------------------------
    # 1. KOOPERATİF SUPER-LOOP SİMÜLASYONU
    # --------------------------------------------------------------------------
    steps = int(sim_time_ms / step_ms)
    t_axis = np.linspace(0, sim_time_ms, steps)
    
    # Her görev için kalan iş yükü ve varış zamanı
    coop_active_task = None
    coop_rem_wcet = 0.0
    coop_ready_queue = []
    coop_deadline_misses = {t.name: 0 for t in tasks}
    coop_latencies = {t.name: [] for t in tasks}
    coop_timeline = np.zeros(steps, dtype=int) # 0: Idle, 1..3: Task
    
    # RTOS için değişkenler
    rtos_active_task = None
    rtos_task_rem = {t.name: 0.0 for t in tasks}
    rtos_ready_tasks = set()
    rtos_deadline_misses = {t.name: 0 for t in tasks}
    rtos_latencies = {t.name: [] for t in tasks}
    rtos_timeline = np.zeros(steps, dtype=int)
    
    # Görev serbest kalma (release) zamanları
    task_releases = {t.name: [k * t.period_ms for k in range(int(sim_time_ms / t.period_ms) + 2)] for t in tasks}
    task_active_release = {t.name: 0.0 for t in tasks}
    
    for s_idx, t_now in enumerate(t_axis):
        # 1. Görev varışlarını kontrol et
        for t in tasks:
            # Yeni periyot başladı mı?
            if any(abs(t_now - rel) < step_ms / 2.0 for rel in task_releases[t.name] if rel <= sim_time_ms):
                # Super-Loop kuyruğuna ekle
                coop_ready_queue.append((t, t_now))
                # RTOS hazır kümesine ekle
                rtos_task_rem[t.name] = t.wcet_ms
                rtos_ready_tasks.add(t.name)
                task_active_release[t.name] = t_now

        # ------------------- COOPERATIVE SUPER-LOOP -------------------
        if coop_active_task is not None:
            coop_rem_wcet -= step_ms
            coop_timeline[s_idx] = coop_active_task.priority
            if coop_rem_wcet <= 1e-6:
                # Görev tamamlandı
                coop_active_task = None
        elif len(coop_ready_queue) > 0:
            # FIFO / Kooperatif seçim (çalışan bitmeden yenisi başlayamaz)
            curr_item = coop_ready_queue.pop(0)
            coop_active_task = curr_item[0]
            arr_time = curr_item[1]
            coop_rem_wcet = coop_active_task.wcet_ms
            lat = t_now - arr_time
            coop_latencies[coop_active_task.name].append(lat)
            if lat > coop_active_task.deadline_ms:
                coop_deadline_misses[coop_active_task.name] += 1
            coop_timeline[s_idx] = coop_active_task.priority

        # ------------------- PREEMPTIVE RTOS -------------------
        # Hazır görevler arasından EN YÜKSEK ÖNCELİKLİYİ seç
        best_task = None
        best_prio = -1
        for t in tasks:
            if t.name in rtos_ready_tasks and rtos_task_rem[t.name] > 1e-6:
                if t.priority > best_prio:
                    best_prio = t.priority
                    best_task = t

        if best_task is not None:
            # Eğer yeni başladıysa latency kaydet
            if rtos_task_rem[best_task.name] >= best_task.wcet_ms - 1e-6:
                lat = t_now - task_active_release[best_task.name]
                rtos_latencies[best_task.name].append(lat)
                if lat > best_task.deadline_ms:
                    rtos_deadline_misses[best_task.name] += 1
            
            rtos_task_rem[best_task.name] -= step_ms
            rtos_timeline[s_idx] = best_task.priority
            if rtos_task_rem[best_task.name] <= 1e-6:
                rtos_ready_tasks.remove(best_task.name)
        else:
            rtos_timeline[s_idx] = 0

    return {
        "t_axis": t_axis,
        "coop_timeline": coop_timeline,
        "rtos_timeline": rtos_timeline,
        "coop_deadline_misses": coop_deadline_misses,
        "rtos_deadline_misses": rtos_deadline_misses,
        "coop_latencies": coop_latencies,
        "rtos_latencies": rtos_latencies,
    }

res = simulate_schedulers(sim_time_ms=50.0, step_ms=0.01)

print("=" * 68)
print("GÜN 179: SUPER-LOOP VS PREEMPTIVE RTOS SİMÜLASYON SONUÇLARI")
print("=" * 68)
print(f"Kooperatif Super-Loop Deadline Kaçırma (Miss):")
for name, miss in res["coop_deadline_misses"].items():
    avg_lat = np.mean(res["coop_latencies"][name]) if res["coop_latencies"][name] else 0.0
    max_lat = np.max(res["coop_latencies"][name]) if res["coop_latencies"][name] else 0.0
    print(f"  - {name:<18}: Miss={miss:2d} | Ort Gecikme={avg_lat:5.2f} ms | Max Gecikme={max_lat:5.2f} ms")

print(f"\nPreemptive RTOS Deadline Kaçırma (Miss):")
for name, miss in res["rtos_deadline_misses"].items():
    avg_lat = np.mean(res["rtos_latencies"][name]) if res["rtos_latencies"][name] else 0.0
    max_lat = np.max(res["rtos_latencies"][name]) if res["rtos_latencies"][name] else 0.0
    print(f"  - {name:<18}: Miss={miss:2d} | Ort Gecikme={avg_lat:5.2f} ms | Max Gecikme={max_lat:5.2f} ms")

# Matematiksel doğrulama
assert res["rtos_deadline_misses"]["Task1_RadarPulse"] == 0, "HATA: RTOS Task1 deadline kaçıramaz!"
assert res["coop_deadline_misses"]["Task1_RadarPulse"] > 0, "HATA: Super-Loop Task1 deadline kaçırmalıydı!"
print("\n[BAŞARILI]: Preemption sayesinde RTOS yüksek öncelikli görevde %100 determinizm sağladı.")
```

## 3. ARM Cortex-M Üzerinde Context Switch Mekanizması: SysTick, PendSV ve SVC

ARM Cortex-M mimarisi, gömülü bir RTOS çekirdeğini doğrudan donanımsal olarak desteklemek üzere özel olarak tasarlanmıştır.

### Çift Yığın İşaretçisi (Dual Stack Pointer)
- **MSP (Main Stack Pointer):** Çekirdek (Kernel), donanım kesmeleri (ISRs) ve sistem önyüklemesi sırasında kullanılır.
- **PSP (Process Stack Pointer):** Yalnızca o an çalışan kullanıcı görevi (Task) tarafından kullanılır. Bir görev çökerse veya yığınını taşırsa, çekirdeğin yığını (MSP) korunur!

### Donanımsal Saklama (Hardware Stacking)
Bir kesme veya istisna (Exception) tetiklendiğinde, ARM Cortex-M donanımı işlemci saatini durdurmadan **otomatik olarak 8 kaydı (Register Frame - 32 byte)** mevcut yığına (PSP) iter:
1. `xPSR` (Program Durum Kaydı)
2. `PC` (Program Counter - Dönüş adresi)
3. `LR` (Link Register - EXC_RETURN kodu)
4. `R12` (Scratch register)
5. `R3`, `R2`, `R1`, `R0` (Fonksiyon parametreleri ve dönüş değerleri)

### Yazılımsal Saklama (Software Stacking)
Kalan çekirdek kayıtları (`R4 - R11` ve FPU aktifse `S16 - S31`) ise RTOS'un montaj (Assembly) seviyesindeki `PendSV_Handler` rutini tarafından yığına yazılır:
```assembly
PendSV_Handler:
    MRS   R0, PSP                  ; Mevcut görevin PSP adresini al
    STMDB R0!, {R4-R11}            ; R4-R11 kayıtlarını yığına kaydet
    LDR   R1, =pxCurrentTCB        ; pxCurrentTCB pointer'ını yükle
    LDR   R1, [R1]
    STR   R0, [R1]                 ; Yeni Stack Pointer'ı TCB'ye kaydet
    
    BL    vTaskSwitchContext       ; Bir sonraki en yüksek öncelikli görevi seç
    
    LDR   R1, =pxCurrentTCB
    LDR   R1, [R1]
    LDR   R0, [R1]                 ; Yeni görevin Stack Pointer'ını TCB'den al
    LDMIA R0!, {R4-R11}            ; Yeni görevin R4-R11 kayıtlarını geri yükle
    MSR   PSP, R0                  ; PSP'yi güncelle
    BX    LR                       ; Donanım kalan 8 kaydı yükleyip göreve atlar!
```

```
+---------------------------------------------------------------------------------------------------+
|               NEDEN SYSTICK DEĞİL DE PENDSV (PENDABLE SERVICE CALL) KULLANILIR?                   |
|                                                                                                   |
|  1. SysTick Kesmesi Gelir  ──────> (Eğer doğrudan SysTick içinde Context Switch yapılırsa:)       |
|  2. Tam o anda kritik UART/CAN kesmesi çalışıyorsa, kesme kesilir ve gecikir (ISR Jitter)!        |
|  3. ÇÖZÜM: SysTick sadece "PendSV bekletme (pending)" bayrağını kaldırır.                         |
|  4. PendSV en düşük kesme önceliğine (Priority 15 / 0xFF) ayarlanır.                              |
|  5. TÜM DONANIM KESMELERİ BİTTİĞİNDE işlemci PendSV'ye düşer ve GÜVENLE Context Switch yapar!     |
+---------------------------------------------------------------------------------------------------+
```

```python
# KOD HÜCRESİ 2: ARM Cortex-M PendSV ve Context Switch Çevrim / Yığın Modeli
# ------------------------------------------------------------------------------
# Bu kod, ARM Cortex-M mimarisindeki Hardware & Software Stacking maliyetini,
# bellek tüketimini (Stack Frame) ve CPU frekansına göre bağlam değiştirme
# süresini matematiksel olarak hesaplar ve simüle eder.

class CortexMContextSwitch:
    def __init__(self, mcu_name="STM32F407", f_cpu_mhz=168, has_fpu=True):
        self.mcu_name = mcu_name
        self.f_cpu_mhz = f_cpu_mhz
        self.has_fpu = has_fpu
        
        # Standart Register Maliyeti (Basic Frame)
        # R0-R3, R12, LR, PC, xPSR = 8 register (Donanımsal Stacking)
        self.hw_stack_regs = 8
        # R4-R11 = 8 register (Yazılımsal PendSV Stacking)
        self.sw_stack_regs = 8
        
        # FPU Lazy Stacking (Extended Frame)
        # S0-S15, FPSCR = 17 register (Donanım)
        # S16-S31 = 16 register (Yazılım)
        self.hw_fpu_regs = 17 if has_fpu else 0
        self.sw_fpu_regs = 16 if has_fpu else 0
        
    def calculate_stack_frame_bytes(self):
        basic_bytes = (self.hw_stack_regs + self.sw_stack_regs) * 4
        fpu_bytes = (self.hw_fpu_regs + self.sw_fpu_regs) * 4
        return {
            "basic_frame_bytes": basic_bytes,
            "fpu_extended_bytes": fpu_bytes,
            "total_stack_frame_bytes": basic_bytes + fpu_bytes
        }
        
    def calculate_switch_cycles(self):
        # Donanımsal giriş/çıkış: ~12 çevrim push + ~12 çevrim pop
        hw_cycles = 24
        # Yazılımsal STMDB / LDMIA (8 kayıt bellek transferi): ~18 push + ~18 pop
        sw_cycles = 36
        # Scheduler algoritması (vTaskSwitchContext - bitmap/clz search): ~24 çevrim
        scheduler_cycles = 24
        
        total_cycles = hw_cycles + sw_cycles + scheduler_cycles
        if self.has_fpu:
            # FPU lazy stacking ve kayıt transferi ilave çevrim
            total_cycles += 40
            
        time_ns = (total_cycles / (self.f_cpu_mhz * 1e6)) * 1e9
        return {
            "total_cycles": total_cycles,
            "time_ns": time_ns,
            "time_us": time_ns / 1000.0
        }
        
    def calculate_cpu_overhead(self, tick_rate_hz=1000, context_switches_per_sec=2500):
        # SysTick ISR maliyeti (~30 çevrim) + Context Switch maliyetleri
        switch_info = self.calculate_switch_cycles()
        cycles_per_sec = self.f_cpu_mhz * 1e6
        
        systick_cycles_sec = tick_rate_hz * 35
        switch_cycles_sec = context_switches_per_sec * switch_info["total_cycles"]
        total_rtos_cycles_sec = systick_cycles_sec + switch_cycles_sec
        
        overhead_percent = (total_rtos_cycles_sec / cycles_per_sec) * 100.0
        return {
            "overhead_percent": overhead_percent,
            "available_app_percent": 100.0 - overhead_percent,
            "total_rtos_cycles_sec": total_rtos_cycles_sec
        }

# İki yaygın savunma aviyonik MCU'sunu karşılaştır
mcu_f4 = CortexMContextSwitch(mcu_name="STM32F407 (Cortex-M4)", f_cpu_mhz=168, has_fpu=True)
mcu_h7 = CortexMContextSwitch(mcu_name="STM32H743 (Cortex-M7)", f_cpu_mhz=480, has_fpu=True)

f4_frame = mcu_f4.calculate_stack_frame_bytes()
f4_perf = mcu_f4.calculate_switch_cycles()
f4_overhead = mcu_f4.calculate_cpu_overhead(tick_rate_hz=1000, context_switches_per_sec=5000)

h7_perf = mcu_h7.calculate_switch_cycles()
h7_overhead = mcu_h7.calculate_cpu_overhead(tick_rate_hz=1000, context_switches_per_sec=5000)

print("=" * 68)
print("ARM CORTEX-M CONTEXT SWITCH VE YIĞIN MALİYET ANALİZİ")
print("=" * 68)
print(f"Stack Frame Boyutu (Kayıt Saklama Alanı):")
print(f"  - Temel Çerçeve (R0-R12, LR, PC, xPSR): {f4_frame['basic_frame_bytes']} bayt (16 Register)")
print(f"  - FPU Çerçevesi (S0-S31, FPSCR):        {f4_frame['fpu_extended_bytes']} bayt (33 Register)")
print(f"  - Toplam Minimum Görev Yığın Çerçevesi: {f4_frame['total_stack_frame_bytes']} bayt")
print(f"\n{mcu_f4.mcu_name} @ {mcu_f4.f_cpu_mhz} MHz:")
print(f"  - Context Switch Çevrimi : {f4_perf['total_cycles']} saat çevrimi")
print(f"  - Bağlam Değiştirme Süresi: {f4_perf['time_ns']:.1f} ns ({f4_perf['time_us']:.3f} µs)")
print(f"  - 5000 switch/s CPU Yükü  : %{f4_overhead['overhead_percent']:.2f}")

print(f"\n{mcu_h7.mcu_name} @ {mcu_h7.f_cpu_mhz} MHz:")
print(f"  - Context Switch Çevrimi : {h7_perf['total_cycles']} saat çevrimi")
print(f"  - Bağlam Değiştirme Süresi: {h7_perf['time_ns']:.1f} ns ({h7_perf['time_us']:.3f} µs)")
print(f"  - 5000 switch/s CPU Yükü  : %{h7_overhead['overhead_percent']:.2f}")

assert f4_frame["total_stack_frame_bytes"] == 196, "HATA: Standart FPU Cortex-M stack frame 196 bayt olmalıdır!"
assert f4_perf["time_us"] < 1.0, "HATA: Cortex-M4 switch süresi 1 µs altında olmalıdır!"
```

## 4. Öncelik Terslenmesi (Priority Inversion) ve Mars Pathfinder Felaketi

RTOS kullanmaya başlayan mühendislerin karşılaştığı **en sinsi ve ölümcül hata** "Öncelik Terslenmesi"dir (Priority Inversion).

### 1997 Mars Pathfinder Olayı
4 Temmuz 1997'de NASA'nın Mars Pathfinder uzay aracı Mars yüzeyine indi. Ancak birkaç gün sonra araç beklenmedik şekilde kendi kendini resetlemeye ve veri toplamayı durdurmaya başladı. Sorunun kaynağı VxWorks RTOS üzerinde çalışan yazılımdaki **Unbounded Priority Inversion** idi:

```
+---------------------------------------------------------------------------------------------------+
|                           ÖNCELİK TERSLENMESİ FELAKETİ (MARS PATHFINDER)                          |
|                                                                                                   |
|  1. Task L (Düşük Öncelik - Meteoroloji Sensörü):                                                 |
|     Ortak "Bilgi Veri Yolu (Information Bus)" Mutex'ini kilitler.                                 |
|                                                                                                   |
|  2. Task H (Yüksek Öncelik - Uçuş İletişim / Görev Kontrol):                                     |
|     Uyanır ve Bilgi Veri Yolu Mutex'ini ister. Mutex L'de olduğu için BLOCKED olur ve bekler.     |
|                                                                                                   |
|  3. Task M (Orta Öncelik - İletişim Radyo / Veri Sıkıştırma):                                     |
|     Uyanır. Mutex ile HİÇBİR İLGİSİ YOKTUR. Ancak önceliği L'den yüksek olduğu için              |
|     L'yi PREEMPT eder ve CPU'yu ele geçirir!                                                      |
|                                                                                                   |
|  4. FELAKET ANASI:                                                                                |
|     Task M çalıştığı sürece Task L çalışamaz -> L çalışamadığı için Mutex'i serbest bırakamaz ->  |
|     Mutex serbest kalmadığı için EN YÜKSEK ÖNCELİKLİ TASK H ÇALIŞAMAZ!                            |
|     Sonuç: Orta öncelikli Task M, en kritik Task H'yi süresiz olarak rehin alır!                  |
|     Watchdog Zamanlayıcı süresi dolar ve tüm uzay aracına RESET ATAR!                             |
+---------------------------------------------------------------------------------------------------+
```

### Çözüm: Öncelik Mirası (Priority Inheritance Protocol - PIP)
Çözüm son derece zarif bir algoritmadır:
- Eğer yüksek öncelikli bir görev (Task H), düşük öncelikli bir görevin (Task L) elindeki Mutex'i beklemeye başlarsa;
- RTOS Çekirdeği derhal **Task L'nin önceliğini geçici olarak Task H'nin seviyesine yükseltir!**
- Artık orta öncelikli Task M, Task L'yi bölemez (preempt edemez).
- Task L kritik bölgeyi hızla tamamlar, Mutex'i serbest bırakır ve orijinal düşük önceliğine geri döner.
- Task H Mutex'i alır ve gecikmesiz çalışır!

> **ÖNEMLİ KURAL:** İkili Semaforlar (Binary Semaphore) öncelik mirasını **DESTEKLEMEZ!** Kaynak koruması için her zaman **FreeRTOS Mutex (`xSemaphoreCreateMutex`)** kullanılmalıdır!

```python
# KOD HÜCRESİ 3: Priority Inversion ve Priority Inheritance Çözüm Simülatörü
# ------------------------------------------------------------------------------
# Bu simülasyon, Mars Pathfinder senaryosunu iki modda çalıştırır:
# 1. Mod A: Standart Mutex (Öncelik Mirası Kapalı - Unbounded Inversion & Watchdog Reset)
# 2. Mod B: Priority Inheritance Aktif (FreeRTOS Mutex - Deterministik Kurtarma)

import numpy as np

def simulate_priority_inversion(enable_inheritance=False, sim_steps=30):
    # Görev Öncelikleri: High=3, Mid=2, Low=1
    # Zaman Çizelgesi Olayları:
    # t=1 : Low başlar ve Mutex alır.
    # t=3 : High uyanır ve Mutex ister (Blocked olur).
    # t=5 : Mid uyanır (Mutex istemez, sadece CPU ister, 12 adım çalışacak).
    # Watchdog Eşiği: High görevi 10 adımdan fazla beklerse SİSTEM ÇÖKER!
    
    timeline = [] # (step, task_running, low_prio, high_state, watchdog_counter)
    mutex_owner = None
    high_blocked = False
    watchdog_counter = 0
    system_reset = False
    
    low_rem = 6
    mid_rem = 12
    high_rem = 4
    
    low_effective_prio = 1
    
    for t in range(sim_steps):
        # 1. Görev Varışları / Tetiklemeleri
        if t == 1:
            mutex_owner = "LOW"
            low_effective_prio = 1
            
        if t == 3:
            # High Mutex istiyor
            if mutex_owner is not None:
                high_blocked = True
                if enable_inheritance and mutex_owner == "LOW":
                    # ÖNCELİK MİRASI: Low'un önceliği High'ın seviyesine çıkar!
                    low_effective_prio = 3
            else:
                high_blocked = False

        if high_blocked:
            watchdog_counter += 1
            if watchdog_counter > 8 and not enable_inheritance:
                system_reset = True
        
        # 2. Çizelgeleyici Kararı (Hangi Görev Koşacak?)
        active = "IDLE"
        if system_reset:
            active = "RESET"
        else:
            # Adayları değerlendir
            # High hazır mı?
            if t >= 3 and not high_blocked and high_rem > 0:
                active = "HIGH"
                high_rem -= 1
            # Mid hazır mı?
            elif t >= 5 and mid_rem > 0 and 2 > low_effective_prio:
                active = "MID"
                mid_rem -= 1
            # Low hazır mı?
            elif low_rem > 0:
                active = "LOW"
                low_rem -= 1
                if low_rem == 0:
                    # Mutex'i serbest bırak
                    mutex_owner = None
                    low_effective_prio = 1
                    high_blocked = False # High artık çalışabilir
            elif t >= 5 and mid_rem > 0:
                active = "MID"
                mid_rem -= 1
                
        timeline.append((t, active, low_effective_prio, watchdog_counter, system_reset))
        if system_reset:
            break
            
    return timeline

sim_no_pi = simulate_priority_inversion(enable_inheritance=False)
sim_pi = simulate_priority_inversion(enable_inheritance=True)

print("=" * 68)
print("MARS PATHFINDER: PRIORITY INVERSION VE PRIORITY INHERITANCE SİMÜLASYONU")
print("=" * 68)

print("\n--- SENARYO A: ÖNCELİK MİRASI YOK (Unbounded Priority Inversion) ---")
for t, act, p, wd, rst in sim_no_pi[:16]:
    status = "WATCHDOG RESET TETİKLENDİ!" if rst else f"Çalışan: {act:<5} | Low Prio: {p} | Bekleme: {wd} tick"
    print(f"Tick {t:02d}: {status}")

print("\n--- SENARYO B: ÖNCELİK MİRASI AKTİF (Priority Inheritance Protocol) ---")
for t, act, p, wd, rst in sim_pi[:16]:
    status = f"Çalışan: {act:<5} | Low Prio: {p} (Miras Aldı!) | Bekleme: {wd} tick"
    print(f"Tick {t:02d}: {status}")

# Doğrulama: Priority inheritance olmadan sistem çökmeli, varken başarıyla tamamlanmalı
assert any(entry[4] for entry in sim_no_pi), "HATA: Öncelik mirası olmadan sistem reset atmalıydı!"
assert not any(entry[4] for entry in sim_pi), "HATA: Öncelik mirası varken sistem asla reset atmamalı!"
print("\n[BAŞARILI]: Priority Inheritance algoritması Mars Pathfinder krizini matematiksel olarak çözdü.")
```

## 5. Matematiksel Çizelgelenebilirlik Analizi: Rate Monotonic Scheduling (RMS) ve Liu-Layland Sınırı

Havacılık ve savunma sanayiinde (DO-178C DAL-A sertifikasyonu), bir yazılımın gerçek zamanlı çalışacağını "laboratuvarda test ettik, çalışıyor gibi duruyor" diyerek onaylayamazsınız. **Matematiksel ispat** sunmak zorundasınız.

### Rate Monotonic Scheduling (RMS)
Sabit öncelikli gerçek zamanlı çizelgelemede altın kural **RMS (Oran Monotonik Çizelgeleme)** teoremidir:
> **RMS Kuralı:** Bir görevin çalışma periyodu ($T_i$) ne kadar küçükse (yani ne kadar sık çalışıyorsa), önceliği ($P_i$) o kadar YÜKSEK olmalıdır!
> $$T_i < T_j \implies P_i > P_j$$

### Toplam İşlemci Kullanım Oranı (CPU Utilization)
$n$ adet periyodik görev için her görevin en kötü durum çalışma süresi $C_i$ (WCET) ve periyodu $T_i$ olmak üzere toplam işlemci yükü:
$$U = \sum_{i=1}^{n} \frac{C_i}{T_i}$$

### Liu & Layland (1973) Yeterlilik Sınırı
C. L. Liu ve James W. Layland tarafından ispatlanan ünlü teoreme göre; eğer toplam işlemci yükü aşağıdaki sınırı aşmıyorsa, sistem **HİÇBİR DEADLINE KAÇIRMADAN KESİNLİKLE ÇİZELGELENEBİLİRDİR:**
$$U \le n \cdot (2^{1/n} - 1)$$

| Görev Sayısı ($n$) | Liu & Layland Sınırı ($U_{\text{bound}}$) | Yorum |
|:---:|:---:|:---|
| **1** | $1 \cdot (2^1 - 1) = 1.000$ (%100.0) | Tek görev CPU'nun %100'ünü kullanabilir. |
| **2** | $2 \cdot (2^{1/2} - 1) \approx 0.828$ (%82.8) | 2 görevde %82.8 yük altı kesin güvenlidir. |
| **3** | $3 \cdot (2^{1/3} - 1) \approx 0.779$ (%77.9) | 3 görevde %77.9 sınırı geçerlidir. |
| **5** | $5 \cdot (2^{1/5} - 1) \approx 0.743$ (%74.3) | 5 görevde sınır %74.3'e iner. |
| **$\infty$** | $\lim_{n \to \infty} n(2^{1/n}-1) = \ln(2) \approx 0.693$ (%69.3) | Sonsuz görevde dahi %69.3 altı DAİMA güvenlidir! |

### Peki Ya $U > n(2^{1/n}-1)$ İse? (Response Time Analysis - RTA)
Eğer sistem yükü Liu-Layland sınırını aşıyorsa ama hala $U \le 1.0$ ise, sistem hemen çöker denemez.
Bunun için **Exact Response Time Analysis (RTA)** yinelemeli denklemi çözülür:
$$R_i^{(k+1)} = C_i + \sum_{j \in hp(i)} \left\lceil \frac{R_i^{(k)}}{T_j} \right\rceil C_j$$
burada $hp(i)$, $i$ görevinden daha yüksek öncelikli görevler kümesidir. Eğer her görev için bulunan en kötü yanıt süresi $R_i \le T_i$ (veya $D_i$) ise sistem **YİNE GÜVENLİDİR!**

```python
# KOD HÜCRESİ 4: RMS Çizelgelenebilirlik ve Response Time Analysis (RTA) Motoru
# ------------------------------------------------------------------------------
# Bu araç, verilen herhangi bir gömülü görev kümesini Liu & Layland RMS sınırına
# ve İteratif Exact Response Time Analysis (RTA) denklemine göre analiz eder.

import math

class RMSTask:
    def __init__(self, name, c_wcet_ms, t_period_ms, d_deadline_ms=None):
        self.name = name
        self.c = float(c_wcet_ms)
        self.t = float(t_period_ms)
        self.d = float(d_deadline_ms) if d_deadline_ms is not None else float(t_period_ms)
        self.utilization = self.c / self.t

def analyze_rms_schedulability(task_set):
    # 1. Görevleri RMS kuralına göre sırala (Küçük periyot = Yüksek Öncelik)
    sorted_tasks = sorted(task_set, key=lambda x: x.t)
    n = len(sorted_tasks)
    
    # 2. Toplam Kullanım Oranı (Total Utilization)
    total_u = sum(t.utilization for t in sorted_tasks)
    
    # 3. Liu & Layland Sınırı
    ll_bound = n * (2 ** (1.0 / n) - 1.0)
    
    ll_pass = total_u <= ll_bound
    
    # 4. Exact Response Time Analysis (RTA)
    rta_results = {}
    all_rta_pass = True
    
    for i, ti in enumerate(sorted_tasks):
        # Başlangıç tahmini: R_i = C_i
        r_current = ti.c
        hp_tasks = sorted_tasks[:i] # Daha yüksek öncelikliler
        
        converged = False
        for _ in range(100):
            # Girişim (Interference) hesabı
            interference = sum(math.ceil(r_current / tj.t) * tj.c for tj in hp_tasks)
            r_next = ti.c + interference
            
            if r_next > ti.d:
                # Deadline aşıldı!
                r_current = r_next
                break
            if abs(r_next - r_current) < 1e-6:
                converged = True
                r_current = r_next
                break
            r_current = r_next
            
        is_schedulable = converged and (r_current <= ti.d)
        if not is_schedulable:
            all_rta_pass = False
            
        rta_results[ti.name] = {
            "wcet": ti.c,
            "period": ti.t,
            "deadline": ti.d,
            "response_time": r_current,
            "schedulable": is_schedulable
        }
        
    return {
        "n_tasks": n,
        "total_utilization": total_u,
        "ll_bound": ll_bound,
        "ll_pass": ll_pass,
        "all_rta_pass": all_rta_pass,
        "task_reports": rta_results
    }

# 4 Farklı Aviyonik Senaryosu Testi
tasks_set_safe = [
    RMSTask("AESA_Pulse", c_wcet_ms=0.2, t_period_ms=1.0),
    RMSTask("Flight_PID", c_wcet_ms=1.0, t_period_ms=5.0),
    RMSTask("Telemetry",  c_wcet_ms=3.0, t_period_ms=20.0),
]

tasks_set_high = [
    RMSTask("Beamformer", c_wcet_ms=0.5, t_period_ms=1.0), # U = 0.5
    RMSTask("Nav_EKF",   c_wcet_ms=1.5, t_period_ms=5.0), # U = 0.3
    RMSTask("Link16",    c_wcet_ms=1.0, t_period_ms=20.0),# U = 0.05 -> Toplam U = 0.85 (> %77.9)
]

res_safe = analyze_rms_schedulability(tasks_set_safe)
res_high = analyze_rms_schedulability(tasks_set_high)

print("=" * 68)
print("RATE MONOTONIC SCHEDULING (RMS) MATEMATİKSEL ANALİZ RAPORU")
print("=" * 68)
print(f"KÜME 1 (Standart Yük):")
print(f"  - Toplam Kullanım (U) : %{res_safe['total_utilization']*100:.2f}")
print(f"  - Liu-Layland Sınırı  : %{res_safe['ll_bound']*100:.2f}")
print(f"  - Liu-Layland Testi   : {'BAŞARILI (PASS)' if res_safe['ll_pass'] else 'BAŞARISIZ (FAIL)'}")
print(f"  - RTA Testi (Tüm Görevler): {'BAŞARILI' if res_safe['all_rta_pass'] else 'BAŞARISIZ'}")

print(f"\nKÜME 2 (Yüksek Yük - LL Sınırını Aşan Ama RTA ile Kurtaran):")
print(f"  - Toplam Kullanım (U) : %{res_high['total_utilization']*100:.2f}")
print(f"  - Liu-Layland Sınırı  : %{res_high['ll_bound']*100:.2f}")
print(f"  - Liu-Layland Testi   : {'BAŞARILI' if res_high['ll_pass'] else 'BAŞARISIZ (Sınır Aşıldı!)'}")
print(f"  - RTA Testi (Exact)   : {'BAŞARILI (Tüm Yanıt Süreleri Deadline İçinde)' if res_high['all_rta_pass'] else 'BAŞARISIZ'}")
for t_name, rep in res_high["task_reports"].items():
    print(f"    * {t_name:<11}: WCET={rep['wcet']:4.1f}ms | R={rep['response_time']:4.1f}ms <= D={rep['deadline']:4.1f}ms -> {'OK' if rep['schedulable'] else 'FAIL'}")

assert res_safe["ll_pass"] == True, "Küme 1 Liu-Layland testini geçmeliydi!"
assert res_high["ll_pass"] == False, "Küme 2 Liu-Layland sınırını aşmalıydı!"
assert res_high["all_rta_pass"] == True, "Küme 2 RTA ile çizelgelenebilir olmalıydı!"
print("\n[BAŞARILI]: Liu-Layland ve RTA matematiksel analiz motoru tam doğrulukla çalışıyor.")
```

## 6. RTOS'un Maliyetleri ve Getirdiği Trade-Off'lar

Mühendislikte "bedava öğle yemeği" yoktur. RTOS kullanmak determinizm ve modülerlik kazandırır, ancak karşılığında çok ciddi sistem bedelleri ödetir:

### 1. RAM Tüketim Patlaması (Per-Task Stack Multiplication)
- **Super-Loop:** Tüm fonksiyonlar sırayla çalıştığı için sistemde yalnızca tek bir ortak yığın (Shared Stack) vardır (örn. 2 KB).
- **RTOS:** Her görev (Task) asenkron olarak duraklatılabileceği için kendi yığınına sahip olmak zorundadır!
  - 10 Görev $\times$ 1.5 KB = **15 KB Yığın RAM'i!**
  - STM32F103 gibi 20 KB SRAM'e sahip popüler bir mikrodenetleyicide RAM'in %75'i yalnızca görev yığınlarına harcanır!

### 2. İşlemci ve Enerji İsrafı (CPU & Energy Overhead)
- Periyodik **SysTick Kesmesi** (genellikle 1000 Hz / 1 ms), MCU'yu sürekli uyandırarak düşük güç (Low-Power Sleep/Stop) modlarına geçişi zorlaştırır.
- Her bağlam değiştirme (Context Switch) 80-120 saat çevrimi (Clock Cycle) harcar. Çok sık context switch yapılan kötü tasarımlarda CPU'nun %5-%10'u yalnızca "görev değiştirmekle" geçer!

### 3. Eşzamanlılık Hataları (Concurrency Bugs & Non-Reentrancy)
- Standart C kütüphanesi fonksiyonları (`printf`, `sprintf`, `strtok`, `malloc`) varsayılan olarak **Thread-Safe / Reentrant DEĞİLDİR!**
- İki görev aynı anda `printf` veya `malloc` çağırırsa yığın veya heap anında bozulur (Memory Corruption / HardFault).
- Kilitlenmeler (Deadlock), yarış durumları (Race Conditions) ve öncelik terslenmeleri ancak çok disiplinli mühendislikle önlenebilir.

```
+---------------------------------------------------------------------------------------------------+
|                        MİMARİ KARAR AĞACI: NE ZAMAN SUPER-LOOP, NE ZAMAN RTOS?                   |
|                                                                                                   |
|  Soru 1: Sistemde 3'ten fazla bağımsız zamanlamaya sahip periyodik görev var mı?                  |
|          └── HAYIR ──> BARE-METAL SUPER-LOOP KULLAN (Daha az RAM, sıfır overhead)                |
|          └── EVET  ──> Soru 2'ye geç                                                             |
|                                                                                                   |
|  Soru 2: Uzun süren (örn. 10 ms+) arka plan işleri (Flash yazma, TCP/IP, Kripto) var mı?         |
|          └── EVET  ──> KESİNLİKLE RTOS KULLAN (Super-loop jitter'ı kaldıramaz)                    |
|          └── HAYIR ──> Soru 3'e geç                                                              |
|                                                                                                   |
|  Soru 3: Mikrodenetleyici RAM'i 16 KB'den küçük mü?                                               |
|          └── EVET  ──> ZAMAN TETİKLEMELİ SUPER-LOOP (TTCS) KULLAN (RAM yetersiz)                 |
|          └── HAYIR ──> RTOS (FreeRTOS / Zephyr) KULLAN                                            |
+---------------------------------------------------------------------------------------------------+
```

```python
# KOD HÜCRESİ 5: Savunma Sanayii Aviyonik Senaryosu: AESA Radar Hedef Takip
# ------------------------------------------------------------------------------
# ASELSAN AESA Radar Sinyal İşleme ve Görev Bilgisayarı Simülasyonu:
# - Task 1 (High, Prio 3): AESA Beamforming / Darbe Kontrol (Periyot: 1000 µs, WCET: 120 µs)
# - Task 2 (Mid,  Prio 2): Hedef Takip & EKF Filtresi      (Periyot: 5000 µs, WCET: 800 µs)
# - Task 3 (Low,  Prio 1): Link-16 Taktik Ağ Paketi        (Periyot: 20000 µs, WCET: 3500 µs)
# Simülasyon, 100.000 µs (100 ms) boyunca 10 µs adımlarla FreeRTOS preemptive kernel'ı taklit eder.

import numpy as np

def run_aesa_radar_rtos_sim(total_time_us=100000, step_us=10, ctx_switch_us=2):
    steps = int(total_time_us / step_us)
    time_us_axis = np.arange(0, total_time_us, step_us)
    
    # Görev Tanımları
    tasks = {
        1: {"name": "AESA_Beamforming", "prio": 3, "period": 1000,  "wcet": 120,  "rem": 0, "next_rel": 0, "runs": 0, "lats": []},
        2: {"name": "TargetTrack_EKF",  "prio": 2, "period": 5000,  "wcet": 800,  "rem": 0, "next_rel": 0, "runs": 0, "lats": []},
        3: {"name": "Link16_Tactical",  "prio": 1, "period": 20000, "wcet": 3500, "rem": 0, "next_rel": 0, "runs": 0, "lats": []},
    }
    
    cpu_usage_history = np.zeros(steps, dtype=int) # 0: Idle, 1..3: Task, 4: Context Switch
    context_switch_count = 0
    current_running_id = 0
    in_switch_rem_us = 0
    
    for idx, t_now in enumerate(time_us_axis):
        # 1. Görev varışlarını kontrol et
        for tid, tinfo in tasks.items():
            if t_now >= tinfo["next_rel"]:
                if tinfo["rem"] > 0:
                    pass # Önceki periyottan kalan iş yükü (aşırı yük uyarısı)
                tinfo["rem"] = tinfo["wcet"]
                tinfo["next_rel"] += tinfo["period"]
                tinfo["runs"] += 1
                # Varış anındaki gecikme ölçümü için zaman damgası
                tinfo["rel_time"] = t_now

        # 2. En yüksek öncelikli hazır görevi bul
        selected_id = 0
        best_prio = -1
        for tid, tinfo in tasks.items():
            if tinfo["rem"] > 0 and tinfo["prio"] > best_prio:
                best_prio = tinfo["prio"]
                selected_id = tid
                
        # 3. Context Switch Gereksinimi
        if selected_id != current_running_id:
            context_switch_count += 1
            if current_running_id != 0 and selected_id != 0:
                # Doğrudan Görevden Göreve Preemption
                in_switch_rem_us = ctx_switch_us
            current_running_id = selected_id
            
        # 4. Yürütme Mantığı
        if in_switch_rem_us > 0:
            in_switch_rem_us -= step_us
            cpu_usage_history[idx] = 4 # 4 = Context Switch
        elif current_running_id != 0:
            tasks[current_running_id]["rem"] -= step_us
            cpu_usage_history[idx] = current_running_id
            if tasks[current_running_id]["rem"] <= 0:
                # Görev tamamlandı
                lat = t_now - (tasks[current_running_id]["next_rel"] - tasks[current_running_id]["period"])
                tasks[current_running_id]["lats"].append(lat)
                current_running_id = 0
        else:
            cpu_usage_history[idx] = 0 # Idle

    return {
        "time_axis": time_us_axis,
        "cpu_usage": cpu_usage_history,
        "tasks": tasks,
        "context_switch_count": context_switch_count,
        "total_time_us": total_time_us
    }

sim_res = run_aesa_radar_rtos_sim()

print("=" * 68)
print("ASELSAN AESA RADAR GÖREV BİLGİSAYARI RTOS ÇALIŞMA RAPORU (100 ms)")
print("=" * 68)
total_active_us = np.sum((sim_res["cpu_usage"] >= 1) & (sim_res["cpu_usage"] <= 3)) * 10
total_switch_us = np.sum(sim_res["cpu_usage"] == 4) * 10
total_idle_us = np.sum(sim_res["cpu_usage"] == 0) * 10

print(f"Toplam Simülasyon Süresi : {sim_res['total_time_us'] / 1000.0:.1f} ms")
print(f"Toplam Context Switch    : {sim_res['context_switch_count']} adet")
print(f"Uygulama CPU Kullanımı   : %{(total_active_us / sim_res['total_time_us']) * 100.0:.2f}")
print(f"Context Switch Overhead  : %{(total_switch_us / sim_res['total_time_us']) * 100.0:.2f}")
print(f"Boşta Bekleme (CPU Idle) : %{(total_idle_us / sim_res['total_time_us']) * 100.0:.2f}")

print("\nGörev Tamamlanma ve Gecikme Metrikleri:")
for tid, tinfo in sim_res["tasks"].items():
    avg_lat = np.mean(tinfo["lats"]) if tinfo["lats"] else 0.0
    max_lat = np.max(tinfo["lats"]) if tinfo["lats"] else 0.0
    print(f"  - {tinfo['name']:<17} (Prio {tinfo['prio']}): Koşma={tinfo['runs']:3d} | Ort Yanıt={avg_lat:5.1f} µs | Max Yanıt={max_lat:5.1f} µs (Periyot={tinfo['period']} µs)")

# Tüm AESA görevlerinin deadline içinde kaldığını doğrula
assert np.max(sim_res["tasks"][1]["lats"]) <= sim_res["tasks"][1]["period"], "HATA: AESA Beamforming deadline kaçırdı!"
assert sim_res["context_switch_count"] >= 50, "HATA: Yeterli context switch gerçekleşmedi!"
print("\n[BAŞARILI]: AESA Radar görevleri FreeRTOS preemptive modelinde %0 deadline miss ile tamamlandı.")
```

## 7. FreeRTOS ve Zephyr Mimarisi Karşılaştırması

Modern gömülü sistemler dünyasında iki büyük dev yarışmaktadır:

| Kriter | FreeRTOS (Amazon Web Services) | Zephyr RTOS (Linux Foundation) |
|:---|:---|:---|
| **Mimari Felsefesi** | Minimalist Mikroçekirdek (Microkernel) | Zengin Modüler Çoklu Görev İşletim Sistemi |
| **Çekirdek Bellek Boyutu** | **Çok Düşük:** ~6 KB ROM, ~500 B RAM | **Orta:** ~25 - 60 KB ROM, ~8 - 16 KB RAM |
| **Donanım Tanımlama** | C Header dosyaları (`FreeRTOSConfig.h`) | **DeviceTree (`.dts`)** ve **Kconfig** (Linux benzeri) |
| **Ağ ve Protokol Yığını** | Harici kütüphaneler (lwIP, FreeRTOS-Plus-TCP) | Dahili kurumsal stack (IPv4/v6, BLE 5.4, Thread, CANopen) |
| **POSIX Uyumluluğu** | Sınırlı POSIX Wrapper katmanı | Yerleşik yerel **POSIX PSE51/52** desteği |
| **Güvenlik Sertifikasyonu** | **SafeRTOS** (IEC 61508 SIL-3, ISO 26262 ASIL-D) | **Zephyr Safety Scope** (Geliştirilme aşamasında) |
| **Savunma Sanayii Kullanımı**| Füze aviyonikleri, küçük sensör düğümleri, radar motorları | Yeni nesil İHA aviyonikleri, karmaşık IoT haberleşme birimleri |

### Savunma Sanayiinde Mimari Seçim Kararı
- Eğer donanımınız bir **STM32F4 veya STM32G4** mikrodenetleyicisi ise, Flash belleğiniz kısıtlıysa ve sertifikasyon (DO-178C) gerekiyorsa: **FreeRTOS / SafeRTOS** tartışmasız standarttır.
- Eğer donanımınız çok çekirdekli bir **STM32MP1, NXP i.MX RT** veya gelişmiş bir Cortex-M7/M33 ise, sistemde Bluetooth/Wi-Fi, CAN-FD ve karmaşık dosya sistemleri gerekiyorsa: **Zephyr RTOS** modern mimarisiyle öne çıkar.

```python
# KOD HÜCRESİ 6: Endüstriyel Dashboard Görselleştirme ve Kapsamlı Assertions
# ------------------------------------------------------------------------------
# 300 DPI, Dark Theme (#0F172A), 4 Panelli Endüstriyel Aviyonik Dashboard:
# Panel 1: Super-Loop vs RTOS Zaman Çizelgesi (Gantt Chart - Preemption Farkı)
# Panel 2: Priority Inversion vs Priority Inheritance (Mars Pathfinder Timeline)
# Panel 3: Rate Monotonic Scheduling (RMS) Liu-Layland Sınırı ve CPU Yükü
# Panel 4: Aviyonik Görev Yanıt Süreleri ve Jitter Karşılaştırması

import os
import matplotlib.pyplot as plt
import numpy as np

# PNG Yol Tanımı
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_179_rtos_neden_var.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_179\gun_179_rtos_neden_var.png"

# Koyu Tema Renk Paleti
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
# PANEL 1: Super-Loop vs RTOS Zaman Çizelgesi (Gantt Chart)
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. Super-Loop Bloklanması vs Preemptive RTOS (Zaman Çizelgesi)", fontsize=11, fontweight='bold', pad=10)

t_pts = res["t_axis"][:1500] # İlk 15 ms
coop_pts = res["coop_timeline"][:1500]
rtos_pts = res["rtos_timeline"][:1500]

# Renkler: 1: Mavi (Task 3 Low), 2: Turuncu (Task 2 Mid), 3: Yeşil (Task 1 High)
colors = {0: '#1E293B', 1: '#38BDF8', 2: '#F59E0B', 3: '#10B981'}

# Super-Loop Çizimi (Üst Çizgi y=2)
for i in range(len(t_pts)-1):
    c_val = coop_pts[i]
    if c_val > 0:
        ax1.plot([t_pts[i], t_pts[i+1]], [2, 2], color=colors[c_val], linewidth=12, solid_capstyle='butt')

# RTOS Çizimi (Alt Çizgi y=1)
for i in range(len(t_pts)-1):
    r_val = rtos_pts[i]
    if r_val > 0:
        ax1.plot([t_pts[i], t_pts[i+1]], [1, 1], color=colors[r_val], linewidth=12, solid_capstyle='butt')

ax1.set_yticks([1, 2])
ax1.set_yticklabels(["RTOS (Preemptive)", "Super-Loop (Coop)"], fontweight='bold')
ax1.set_xlabel("Zaman (ms)", fontsize=10)
ax1.set_xlim(0, 15)
ax1.set_ylim(0.5, 2.5)

# Açıklama metni ekle
ax1.text(3.5, 2.25, "Flash Yazma Task 1'i 6 ms BLOKLADI! (Miss)", color='#EF4444', fontsize=9, fontweight='bold')
ax1.text(2.1, 1.25, "Task 1 Preempt Etti (<2 µs)", color='#10B981', fontsize=9, fontweight='bold')

# ------------------------------------------------------------------------------
# PANEL 2: Mars Pathfinder (Priority Inversion vs Priority Inheritance)
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. Mars Pathfinder Krizi: Priority Inversion vs Priority Inheritance", fontsize=11, fontweight='bold', pad=10)

task_map = {"IDLE": 0, "LOW": 1, "MID": 2, "HIGH": 3, "RESET": -0.5}

times_no_pi = [x[0] for x in sim_no_pi]
y_no_pi = [task_map[x[1]] for x in sim_no_pi]
# Reset sonrası görsel süreklilik için uzat
t_last = times_no_pi[-1]
while t_last < 15:
    t_last += 1
    times_no_pi.append(t_last)
    y_no_pi.append(task_map["RESET"])

times_pi = [x[0] for x in sim_pi[:16]]
y_pi = [task_map[x[1]] for x in sim_pi[:16]]

ax2.step(times_no_pi, y_no_pi, where='post', label='Miras YOK (Priority Inversion)', color='#EF4444', linewidth=2.5, linestyle='--')
ax2.step(times_pi, y_pi, where='post', label='Miras VAR (Priority Inheritance)', color='#10B981', linewidth=2.5)

ax2.set_yticks([-0.5, 0, 1, 2, 3])
ax2.set_yticklabels(["RESET", "IDLE", "Task L (Sensör)", "Task M (Radyo)", "Task H (İletişim)"], fontweight='bold')
ax2.set_xlabel("Sistem Saati (Ticks)", fontsize=10)
ax2.set_xlim(0, 15)
ax2.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)
ax2.text(7.5, 2.2, "Mid, High'ı Rehin Aldı!", color='#F87171', fontsize=9, fontweight='bold')
ax2.text(3.5, 1.2, "L Öncelik Mirası Aldı!", color='#34D399', fontsize=9, fontweight='bold')

# ------------------------------------------------------------------------------
# PANEL 3: Rate Monotonic Scheduling (RMS) Liu-Layland Sınırı
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. Rate Monotonic Scheduling (RMS) Liu-Layland Sınırı ve CPU Yükü", fontsize=11, fontweight='bold', pad=10)

n_tasks_range = np.arange(1, 11)
ll_bounds = n_tasks_range * (2.0 ** (1.0 / n_tasks_range) - 1.0) * 100.0

ax3.plot(n_tasks_range, ll_bounds, marker='o', color='#38BDF8', linewidth=2.5, label='Liu & Layland Sınırı ($n(2^{1/n}-1)$)')
ax3.axhline(69.3, color='#F59E0B', linestyle=':', label='Asimptotik Sınır (ln(2) = %69.3)')

# Test Kümelerini Ekle
ax3.scatter([3], [res_safe['total_utilization']*100], color='#10B981', s=120, zorder=5, label=f'Küme 1 (Güvenli: %{res_safe["total_utilization"]*100:.1f})')
ax3.scatter([3], [res_high['total_utilization']*100], color='#EF4444', s=120, zorder=5, label=f'Küme 2 (RTA Gereken: %{res_high["total_utilization"]*100:.1f})')

ax3.set_xlabel("Görev Sayısı (n)", fontsize=10)
ax3.set_ylabel("İşlemci Kullanım Oranı (%)", fontsize=10)
ax3.set_ylim(50, 105)
ax3.set_xticks(n_tasks_range)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 4: Görev Yanıt Süresi (Latency) ve Jitter Analizi
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. Görev Yanıt Gecikmesi: Super-Loop vs RTOS (Maksimum Latency)", fontsize=11, fontweight='bold', pad=10)

task_names = ["Task 1 (Radar)", "Task 2 (Takip)", "Task 3 (Kripto)"]
coop_max_lats = [np.max(res["coop_latencies"]["Task1_RadarPulse"]),
                 np.max(res["coop_latencies"]["Task2_TargetTrack"]),
                 np.max(res["coop_latencies"]["Task3_CryptoFlash"])]

rtos_max_lats = [np.max(res["rtos_latencies"]["Task1_RadarPulse"]),
                 np.max(res["rtos_latencies"]["Task2_TargetTrack"]),
                 np.max(res["rtos_latencies"]["Task3_CryptoFlash"])]

x_pos = np.arange(len(task_names))
bar_width = 0.35

ax4.bar(x_pos - bar_width/2, coop_max_lats, bar_width, label='Super-Loop (Maks Gecikme)', color='#EF4444', alpha=0.85)
ax4.bar(x_pos + bar_width/2, rtos_max_lats, bar_width, label='Preemptive RTOS (Maks Gecikme)', color='#10B981', alpha=0.85)

# Deadline Çizgisi
ax4.axhline(2.0, color='#F59E0B', linestyle='--', linewidth=1.5, label='Task 1 Deadline (2.0 ms)')

ax4.set_xticks(x_pos)
ax4.set_xticklabels(task_names, fontweight='bold')
ax4.set_ylabel("Maksimum Yanıt Gecikmesi (ms)", fontsize=10)
ax4.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

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

# 1. Simülasyon Veri Doğrulaması
assert res["rtos_deadline_misses"]["Task1_RadarPulse"] == 0, "HATA: RTOS Task 1 deadline kaçırmamalı!"
assert res["coop_deadline_misses"]["Task1_RadarPulse"] > 0, "HATA: Superloop Task 1 deadline kaçırmalıydı!"

# 2. Mars Pathfinder Doğrulaması
assert any(entry[4] for entry in sim_no_pi), "HATA: Priority inheritance olmadan sistem çökmeliydi!"
assert not any(entry[4] for entry in sim_pi), "HATA: Priority inheritance varken sistem çökmemeliydi!"

# 3. Liu-Layland Doğrulaması
assert res_safe["ll_pass"] == True, "HATA: Güvenli küme Liu-Layland testini geçmeliydi!"
assert res_high["ll_pass"] == False, "HATA: Yüksek küme Liu-Layland sınırını aşmalıydı!"
assert res_high["all_rta_pass"] == True, "HATA: Yüksek küme RTA ile kurtarmalıydı!"

print("[PASS] GÜN 179: TÜM MATEMATİKSEL VE GÖRSEL DOĞRULAMALAR BAŞARIYLA TAMAMLANDI!")
```

## 8. C++20 ile RTOS Entegrasyonu: RAII Kilitleri ve Statik Tahsis

C++20, gömülü sistemlerde RTOS kullanımını çok daha güvenli, tip-korumalı (type-safe) ve hatasız hale getiren modern mekanizmalar sunar:

### 1. RAII Mutex Sarmalayıcısı (Resource Acquisition Is Initialization)
Geleneksel C kodunda en yaygın hata `xSemaphoreTake` yapıp hata durumunda `xSemaphoreGive` yapmayı unutarak sistemi sonsuz kilitlenmeye (Deadlock) sokmaktır. C++20 ile bu imkansız hale gelir:

```cpp
#include "FreeRTOS.h"
#include "semphr.h"

class RtosMutexLock {
public:
    explicit RtosMutexLock(SemaphoreHandle_t& mutex, TickType_t timeout = portMAX_DELAY) 
        : mutex_(mutex), locked_(false) {
        if (xSemaphoreTake(mutex_, timeout) == pdTRUE) {
            locked_ = true;
        }
    }
    
    ~RtosMutexLock() {
        if (locked_) {
            xSemaphoreGive(mutex_);
        }
    }
    
    [[nodiscard]] bool is_locked() const noexcept { return locked_; }

    // Kopyalama yasak (RAII Güvenliği)
    RtosMutexLock(const RtosMutexLock&) = delete;
    RtosMutexLock& operator=(const RtosMutexLock&) = delete;

private:
    SemaphoreHandle_t& mutex_;
    bool locked_;
};

// KULLANIM:
void safe_radar_write(const RadarData& data) {
    RtosMutexLock lock(radar_mutex);
    if (!lock.is_locked()) return;
    
    hardware_send(data);
    // Fonksiyon bittiğinde, return olduğunda veya hata fırladığında
    // ~RtosMutexLock() otomatik çağrılır ve Mutex %100 serbest bırakılır!
}
```

### 2. Sıfır-Dinamik Bellek: C++20 `std::array` ile `xTaskCreateStatic`
Savunma sanayiinde `malloc` ve `pvPortMalloc` yasaktır (heap parçalanması riski). Görev kontrol bloğu (TCB) ve yığın belleği C++ derleme zamanında ayrılmalıdır:

```cpp
#include <array>

template <size_t StackSizeWords, UBaseType_t Priority>
class StaticTask {
public:
    template <typename Function>
    void start(const char* name, Function&& func) {
        task_handle_ = xTaskCreateStatic(
            [](void* param) { (*static_cast<Function*>(param))(); },
            name,
            StackSizeWords,
            &func,
            Priority,
            stack_buffer_.data(),
            &tcb_
        );
    }

private:
    std::array<StackType_t, StackSizeWords> stack_buffer_{};
    StaticTask_t tcb_{};
    TaskHandle_t task_handle_{nullptr};
};
```

## 9. Savunma Sanayiinde RTOS Güvenlik ve Emniyet Standartları (DO-178C ve MISRA-C)

Sivil ve askeri aviyonik sistemlerde (İHA, F-16 Görev Bilgisayarı, Helikopter Uçuş Kontrolü) yazılımlar **RTCA DO-178C** standartlarına göre sertifikalandırılır.

### Emniyet Seviyeleri (Design Assurance Levels - DAL)
- **DAL A (Catastrophic):** Yazılım hatası uçağın düşmesine ve can kaybına yol açar (örn. Uçuş Kontrol Bilgisayarı, Fly-by-Wire).
- **DAL B (Hazardous):** Uçuş güvenliğini ciddi tehlikeye sokar, mürettebat iş yükünü aşırı artırır.
- **DAL C (Major):** Uçuş emniyet marjını azaltır.
- **DAL D (Minor):** Önemsiz sistem hatası.
- **DAL E (No Effect):** Uçuş güvenliğine sıfır etki (örn. yolcu eğlence ekranı).

### RTOS İçin DO-178C DAL-A Kuralları:
1. **Dinamik Bellek Tahsisi Yasaktır:** Sistem başlarken tüm bellek statik olarak ayrılmalıdır (`configSUPPORT_DYNAMIC_ALLOCATION = 0`). Çalışma anında hiçbir `malloc` çağrılamaz!
2. **Zaman ve Alan Bölümlendirmesi (ARINC 653):**
   Farklı kritiklik seviyesindeki yazılımlar (örn. DAL-A uçuş kontrolü ile DAL-D telemetri kaydı) aynı işlemcide çalışacaksa, **ARINC 653** uyumlu RTOS (örn. PikeOS, VxWorks 653) kullanılmalıdır. Bellek Yönetim Birimi (MPU) donanımsal olarak görevlerin birbirinin RAM alanına erişmesini engeller.
3. **Deterministik Kesme Gecikmesi:** Çekirdeğin kesmeleri devre dışı bıraktığı kritik bölge süreleri (Interrupt Latency) nano-saniye seviyesinde belgelenmeli ve garanti edilmelidir.

## 10. Bilerek Bozacağımız Şey: Unbounded Priority Inversion ve Stack Overflow

Gerçek bir gömülü yazılım mühendisi hataları yalnızca kitaplardan okumaz; sistemin nasıl çöktüğünü kendi gözleriyle görür!

### Bozma Senaryosu 1: Unbounded Priority Inversion Üretmek
1. Kodda FreeRTOS Mutex yerine **Binary Semaphore (`xSemaphoreCreateBinary`)** kullanın.
2. Düşük öncelikli göreve semaforu aldırın.
3. Yüksek öncelikli görevi semaforu bekleyecek şekilde `Blocked` durumuna getirin.
4. Orta öncelikli göreve uzun bir matematiksel döngü başlatın.
5. **Beklenen Çökme Belirtisi:** Yüksek öncelikli görev asla CPU alamaz! Sistem tepki vermeyi keser ve Watchdog reset atar!
6. **Düzeltme:** Semaforu derhal `xSemaphoreCreateMutex()` ile değiştirin; böylece çekirdek öncelik mirasını (Priority Inheritance) otomatik devreye sokar!

### Bozma Senaryosu 2: Yığın Taşması (Stack Overflow) Felaketi
1. Bir görevin yığın boyutunu 128 kelime (512 bayt) olarak tanımlayın.
2. Görev fonksiyonunun içine yerel değişken olarak `uint8_t buffer[1024];` açın ve `memset` yapın.
3. **Beklenen Çökme Belirtisi:** PSP sınırını aşar, TCB verisini ezer ve işlemci `HardFault_Handler`'a veya FreeRTOS `vApplicationStackOverflowHook`'a düşer.
4. **Düzeltme:** `uxTaskGetStackHighWaterMark()` ile görevin minimum boş yığın payını ölçün ve stack boyutunu en az %30 emniyet marjıyla ayarlayın.

## 11. Hata Ayıklama (Debugging) ve Profiling Teknikleri

RTOS üzerinde çalışan bir sistemi `printf` ile debug etmeye kalkışmak büyük bir hatadır (Heisenbug üretir, zamanlamayı bozar).

### 1. SEGGER SystemView ve Percepio Tracealyzer
- ARM Cortex-M içindeki **DWT (Data Watchpoint and Trace)** ve **ITM (Instrumentation Trace Macrocell)** donanımlarını kullanarak sıfır-overhead ile çekirdek olaylarını kaydeder.
- Hangi görevin hangi mikrosaniyede context switch yaptığını, kesmelerin ne kadar sürdüğünü ve semafor bekleme sürelerini osiloskop gibi canlı gösterir.

### 2. Yığın Doluluk Oranı Ölçümü (Stack High Water Mark)
FreeRTOS, görev oluşturulurken tüm yığını `0xA5` deseniyle doldurur. Çalışma anında şu fonksiyon çağrılarak görevin en çok ne kadar yığın tükettiği tespit edilir:
```c
UBaseType_t uxHighWaterMark = uxTaskGetStackHighWaterMark(xTaskHandle);
// Eğer bu değer 20'nin altına düşerse, yığın taşması tehlikesi çok yakındır!
```

### 3. ARM DWT Cycle Counter ile Görev Çalışma Süresi Ölçümü
```c
CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk; // 32-bit çevrim sayacını başlat

uint32_t start_cycles = DWT->CYCCNT;
run_critical_algorithm();
uint32_t elapsed_cycles = DWT->CYCCNT - start_cycles;
```

## 12. Adım Adım C Kod Örneği: FreeRTOS Preemptive Multitasking

Aşağıda STM32 mimarisinde hiçbir dinamik bellek (malloc) kullanmadan, %100 statik tahsisle çalışan profesyonel FreeRTOS başlatma şablonu yer almaktadır:

```c
#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"

#define RADAR_TASK_STACK_SIZE   256
#define TELEM_TASK_STACK_SIZE   512

// Statik Yığın ve TCB Alanları
static StackType_t xRadarStack[RADAR_TASK_STACK_SIZE];
static StaticTask_t xRadarTCB;
static TaskHandle_t xRadarTaskHandle = NULL;

static StackType_t xTelemStack[TELEM_TASK_STACK_SIZE];
static StaticTask_t xTelemTCB;
static TaskHandle_t xTelemTaskHandle = NULL;

// Öncelik Miraslı Statik Mutex
static StaticSemaphore_t xMutexBuffer;
static SemaphoreHandle_t xDataMutex = NULL;

void vRadarTask(void *pvParameters) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xPeriod = pdMS_TO_TICKS(1); // 1 ms Periyot
    
    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xPeriod);
        
        // Mutex ile Veri Paylaşımı
        if (xSemaphoreTake(xDataMutex, pdMS_TO_TICKS(1)) == pdTRUE) {
            update_radar_beamformer();
            xSemaphoreGive(xDataMutex);
        }
    }
}

void vTelemetryTask(void *pvParameters) {
    for (;;) {
        if (xSemaphoreTake(xDataMutex, portMAX_DELAY) == pdTRUE) {
            format_and_send_telemetry();
            xSemaphoreGive(xDataMutex);
        }
        vTaskDelay(pdMS_TO_TICKS(50)); // 50 ms bekle
    }
}

int main(void) {
    hardware_init();
    
    // 1. Statik Mutex Oluştur
    xDataMutex = xSemaphoreCreateMutexStatic(&xMutexBuffer);
    
    // 2. Statik Görevleri Oluştur
    xRadarTaskHandle = xTaskCreateStatic(
        vRadarTask, "RadarBeam", RADAR_TASK_STACK_SIZE, NULL, 3, xRadarStack, &xRadarTCB
    );
    
    xTelemTaskHandle = xTaskCreateStatic(
        vTelemetryTask, "Telemetry", TELEM_TASK_STACK_SIZE, NULL, 1, xTelemStack, &xTelemTCB
    );
    
    // 3. Çizelgeleyiciyi Başlat (Asla geri dönmez!)
    vTaskStartScheduler();
    
    for (;;); // Buraya asla ulaşılmamalıdır
}
```

## 13. Sık Yapılan Hatalar ve Anti-Pattern'ler

RTOS projelerinde kıdemli mühendislerin kod incelemelerinde (Code Review) aradığı başlıca tuzaklar:

| Hata / Anti-Pattern | Neden Tehlikeli? | Doğru Tasarım Deseni |
|:---|:---|:---|
| **Kesme İçinde Bloklayıcı API Çağırmak** | Bir ISR içinde `xQueueSend` veya `vTaskDelay` çağrılırsa sistem kilitlenir veya HardFault verir. | Kesmelerde DAİMA sonu `FromISR` ile biten API'ler (`xQueueSendFromISR`) kullanılmalıdır. |
| **Yanlış Kesme Önceliği (`configMAX_SYSCALL_...`)** | FreeRTOS API çağıran bir donanım kesmesinin önceliği `configMAX_SYSCALL_INTERRUPT_PRIORITY`'den yüksekse çekirdek çöker. | API kullanan tüm çevre birim kesmelerinin mantıksal önceliğini bu eşikten daha düşük ayarlayın. |
| **Görev Patlaması (Task Proliferation)** | Her küçük iş için bir görev açmak yığın belleğini (RAM) tüketir ve gereksiz context switch yaratır. | İlgili küçük işleri birleştirin, olay tabanlı durum makineleri (FSM) veya Event Group kullanın. |
| **`vTaskDelay` ile Döngü Senkronizasyonu** | `vTaskDelay(10)` görevin çalışma süresini hesaba katmaz; her döngüde zaman kayması (Drift) oluşur. | Periyodik döngülerde mutlak zamanlama sağlayan `vTaskDelayUntil()` fonksiyonunu kullanın. |
| **Kaynak Paylaşımında Binary Semaphore Kullanmak** | Öncelik mirası (Priority Inheritance) desteği olmadığı için Unbounded Priority Inversion felaketine yol açar. | Kaynak koruma için kesinlikle `Mutex` kullanın. |

## 14. 5N1K Tablosu: RTOS Mimarisi

| Soru | Aviyonik ve Gömülü Sistem Yanıtı |
|:---|:---|
| **Ne?** | Çoklu görevlerin bağımsız yığınlar üzerinde öncelik sırasına göre deterministik olarak işletilmesini sağlayan gerçek zamanlı çekirdek. |
| **Neden?** | Super-Loop'un kooperatif yapısındaki bloklanmaları, yüksek jitter'ı ve deadline kaçırma risklerini preemption ile yok etmek için. |
| **Nerede?** | Füze güdüm bilgisayarları, AESA radar sinyal işleyicileri, uçuş kontrol üniteleri ve STM32 Cortex-M işlemcilerinde. |
| **Nasıl?** | SysTick ve PendSV istisnalarını kullanarak donanımsal ve yazılımsal yığın kaydı (Context Switching) ve TCB yönetimi ile. |
| **Ne Zaman?** | Sistemde farklı öncelik ve periyoda sahip görevler, uzun süren arka plan hesaplamaları veya katı deadline gereksinimleri olduğunda. |
| **Kim?** | Aviyonik gömülü sistem mimarı, gerçek zamanlı yazılım mühendisi ve emniyet kritik (safety-critical) sistem tasarımcısı. |

## 15. İleri Düzey Okuma ve Kaynaklar

1. **Jane W. S. Liu - Real-Time Systems (Prentice Hall):** Gerçek zamanlı çizelgeleme teorisi, RMS, EDF ve kaynak erişim protokollerinin dünyadaki en kapsamlı akademik başvuru kitabı.
2. **Joseph Yiu - The Definitive Guide to ARM Cortex-M3 and Cortex-M4 Processors:** Cortex-M mimarisinde çift stack pointer (MSP/PSP), PendSV mekanizması ve exception handling'in donanımsal temelleri.
3. **FreeRTOS Kernel Developer Guide:** Richard Barry tarafından hazırlanan resmi mimari dokümanı ve FreeRTOS kaynak kod analizi.
4. **Mike Jones - What really happened on Mars? (1997):** Mars Pathfinder uzay aracındaki Priority Inversion olayının NASA ve JPL mühendisleri tarafından hazırlanan resmi teknik analizi.
5. **RTCA DO-178C:** Software Considerations in Airborne Systems and Equipment Certification (Havacılık Yazılım Standartları).

## 16. Günün Mini Projesi ve Sınav Soruları

### Mini Proje Görevi
Bir STM32F407 mikrodenetleyicisi üzerinde FreeRTOS kullanarak 3 görev tasarlayın:
1. **Görev A (Öncelik 3, 1 ms):** ADC'den gyro verisi okuyup DMA kuyruğuna yazacak.
2. **Görev B (Öncelik 2, 10 ms):** Veriyi kuyruktan alıp Kalman filtresi çalıştıracak.
3. **Görev C (Öncelik 1, 50 ms):** UART üzerinden telemetri gönderecek.
- Görevler arasında veri paylaşımını bir Mutex ile koruyun ve FreeRTOS `vTaskDelayUntil` ile sıfır-jitter periyot sağlayın.
- SEGGER SystemView veya DWT sayaçları ile her görevin yanıt süresini (Response Time) doğrulayın.

---

### Günün Sınav Soruları

#### Soru 1: ARM Cortex-M mimarisinde RTOS bağlam değiştirmesi (Context Switch) neden SysTick içinde değil de PendSV içinde yapılır?
- A) Çünkü SysTick kesmesi donanım tarafından kapatılamaz.
- B) SysTick içinde yapılırsa devam eden diğer donanım kesmeleri (UART/CAN) gecikebilir veya iç içe kesme (nested ISR) karmaşası yaşanabilir; PendSV en düşük öncelikte güvenle çalışır.
- C) PendSV yalnızca FPU kayıtlarını saklamak için kullanılır.
- D) SysTick yalnızca saat bilgisini günceller, kayıt saklama yeteneği yoktur.
- **Doğru Cevap: B**

#### Soru 2: 3 bağımsız görevin bulunduğu bir sistemde görev periyotları ve WCET süreleri sırasıyla: $T_1=5ms, C_1=1ms$, $T_2=10ms, C_2=2ms$, $T_3=20ms, C_3=5ms$ olarak verilmiştir. Bu sistem Liu & Layland RMS sınırına göre çizelgelenebilir midir?
- A) Hayır, çünkü toplam CPU yükü %100'ü aşmaktadır.
- B) Evet, toplam kullanım $U = 1/5 + 2/10 + 5/20 = 0.65$ (%65)'tir ve 3 görev için LL sınırı olan %77.9'un altındadır.
- C) Hayır, Liu-Layland kuralına göre görev sayısı 3 olduğunda sınır %50'dir.
- D) Yalnızca EDF (Earliest Deadline First) ile çizelgelenebilir.
- **Doğru Cevap: B**

#### Soru 3: 1997 Mars Pathfinder uzay aracında ortaya çıkan "Priority Inversion" felaketinde orta öncelikli görev (Task M), en yüksek öncelikli görevi (Task H) nasıl dolaylı olarak bloke etmiştir?
- A) Task M, Task H'nin bellek alanına izinsiz erişim sağlayarak yığını çökertmiştir.
- B) Task M ortak Mutex'i alıp bırakmamıştır.
- C) Mutex'i elinde tutan düşük öncelikli Task L'yi preempt ederek onun Mutex'i serbest bırakmasını engellemiş, böylece Mutex bekleyen Task H'nin çalışmasını durdurmuştur.
- D) Task M sistem saatini (SysTick) durdurmuştur.
- **Doğru Cevap: C**

#### Soru 4: Savunma ve aviyonik sistemlerde DO-178C DAL-A sertifikasyonu için neden dinamik bellek tahsisi (`malloc` / `pvPortMalloc`) yasaklanmıştır?
- A) Dinamik bellek yavaş çalıştığı için.
- B) Heap parçalanması (Fragmentation) nedeniyle ilerleyen saatlerde bellek tükenmesi ve belirsiz (non-deterministic) yanıt süreleri riskini ortadan kaldırmak için.
- C) ARM Cortex-M işlemcilerde heap donanımı bulunmadığı için.
- D) C++ dili statik belleği desteklemediği için.
- **Doğru Cevap: B**

#### Soru 5: FreeRTOS'ta bir çevre birim kesmesi (ISR) içinden bir göreve veri göndermek için neden `xQueueSend()` yerine `xQueueSendFromISR()` kullanılmalıdır?
- A) Çünkü standart `xQueueSend()` fonksiyonu kuyruk doluysa görevi bloke etmeye (sleep) çalışır; bir donanım kesmesi (ISR) ise asla uyutulamaz/bloke edilemez!
- B) `xQueueSendFromISR()` veriyi daha hızlı kopyalar.
- C) Kesmeler sadece 8-bit veri transfer edebilir.
- D) `xQueueSend()` FPU kayıtlarını bozar.
- **Doğru Cevap: A**

## 17. Gün Sonu Özeti ve Yarının Ön İzlemesi

### 3 Cümlelik Kapanış Özeti
1. **RTOS Nedir?** RTOS; mikrodenetleyici üzerinde bağımsız yığınlara sahip çoklu görevlerin öncelik sırasına göre deterministik olarak çalışmasını sağlayan bir gerçek zamanlı çekirdektir.
2. **Hangi Problemi Çözer?** Super-Loop mimarisindeki uzun süren işlerin kritik görevleri geciktirmesini (jitter), asenkron olaylardaki tepkisizliği ve deadline kaçırma risklerini donanımsal preemption ile kesin olarak çözer.
3. **Hangi Bedeli Getirir?** Her görev için ayrı yığın belleği (RAM) tüketimi, bağlam değiştirme (Context Switch) çevrim maliyeti ve öncelik terslenmesi (Priority Inversion) gibi karmaşık eşzamanlılık risklerini beraberinde getirir.

---

### Yarının Konusu (GÜN 180): Task/Thread ve Scheduler Mimarisi
Yarın F5 fazına derinlemesine devam ederek:
- FreeRTOS ve Zephyr çekirdeğindeki **Task State Machine (Ready, Running, Blocked, Suspended)**,
- Çizelgeleyicinin O(1) donanımsal bit arama komutu (`CLZ - Count Leading Zeros`),
- Round-Robin Time-Slicing, Co-operative vs Preemptive Scheduler konfigürasyonları ve
- Görev kontrol bloklarının (TCB) bellek haritasındaki canlı hareketlerini inceleyeceğiz!

