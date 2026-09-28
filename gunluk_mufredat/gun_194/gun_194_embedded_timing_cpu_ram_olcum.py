# -*- coding: utf-8 -*-
"""
GÜN 194: Embedded Timing, CPU ve RAM Ölçümü
Standalone Python Doğrulama ve Görselleştirme Betiği
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_194\gun_194_embedded_timing_cpu_ram_olcum.png"

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

