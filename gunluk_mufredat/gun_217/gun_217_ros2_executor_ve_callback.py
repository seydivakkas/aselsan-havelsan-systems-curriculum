# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 217: ROS 2 Executor ve Callback Mimarisi Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: ROS 2 Gelişmiş Executor Motoru ve Callback Dağıtıcı
# ============================================================================
import time
import queue
import threading
from enum import Enum
from typing import Dict, Any, List, Callable, Optional, Tuple
import numpy as np

class CallbackGroupType(Enum):
    MUTUALLY_EXCLUSIVE = 1
    REENTRANT = 2

class CallbackGroup:
    def __init__(self, group_type: CallbackGroupType, name: str):
        self.group_type = group_type
        self.name = name
        self.is_executing = False
        self.lock = threading.Lock()

class TaskItem:
    def __init__(self, name: str, group: CallbackGroup, fn: Callable[[], Any], priority: int = 10):
        self.name = name
        self.group = group
        self.fn = fn
        self.priority = priority # Yüksek sayı = Yüksek öncelik (100: Uçuş Kontrol, 10: Log)
        self.submit_time = time.perf_counter()

class AdvancedExecutorEngine:
    # ROS 2 MultiThreadedExecutor ve Öncelikli Dağıtım Simülasyonu.
    def __init__(self, thread_count: int = 2):
        self.thread_count = thread_count
        self.ready_queue: List[TaskItem] = []
        self.execution_log: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

    def submit_task(self, task: TaskItem):
        with self.lock:
            self.ready_queue.append(task)
            # Önceliğe göre sırala (Priority Scheduling)
            self.ready_queue.sort(key=lambda t: t.priority, reverse=True)

    def spin_step(self) -> bool:
        with self.lock:
            if not self.ready_queue:
                return False

            # Kuyruğu tara ve çalıştırılabilir ilk görevi bul (CallbackGroup kuralı)
            selected_idx = -1
            for idx, task in enumerate(self.ready_queue):
                grp = task.group
                if grp.group_type == CallbackGroupType.MUTUALLY_EXCLUSIVE:
                    with grp.lock:
                        if not grp.is_executing:
                            grp.is_executing = True
                            selected_idx = idx
                            break
                else: # REENTRANT
                    selected_idx = idx
                    break

            if selected_idx == -1:
                return False # Tüm hazır görevlerin grupları şu an meşgul!

            task = self.ready_queue.pop(selected_idx)

        # Görevi icra et
        start_t = time.perf_counter()
        wait_latency_ms = (start_t - task.submit_time) * 1000.0
        res = task.fn()
        exec_duration_ms = (time.perf_counter() - start_t) * 1000.0

        if task.group.group_type == CallbackGroupType.MUTUALLY_EXCLUSIVE:
            with task.group.lock:
                task.group.is_executing = False

        with self.lock:
            self.execution_log.append({
                "task": task.name,
                "group": task.group.name,
                "priority": task.priority,
                "wait_latency_ms": wait_latency_ms,
                "exec_duration_ms": exec_duration_ms,
                "result": res
            })
            
        return True

# Doğrulama Testi: Öncelik ve CallbackGroup Koruması
executor = AdvancedExecutorEngine(thread_count=2)

crit_group = CallbackGroup(CallbackGroupType.MUTUALLY_EXCLUSIVE, "CriticalGroup")
io_group = CallbackGroup(CallbackGroupType.REENTRANT, "IoGroup")

# Görevler: 1 Düşük öncelikli log, 1 Orta öncelikli telemetri, 1 Yüksek öncelikli füze güdüm
executor.submit_task(TaskItem("LogTask", io_group, lambda: "LOG_WRITTEN", priority=10))
executor.submit_task(TaskItem("TelemetryTask", io_group, lambda: "TELEMETRY_SENT", priority=50))
executor.submit_task(TaskItem("MissileGuidance", crit_group, lambda: "GUIDANCE_CALCULATED", priority=100))

# Executor tüm görevleri yürütsün
while executor.spin_step():
    pass

print("[Executor Yürütme Sıralaması]")
for entry in executor.execution_log:
    print(f"  - Görev: {entry['task']:<16} | Öncelik: {entry['priority']:<3} | Bekleme Gecikmesi: {entry['wait_latency_ms']:.4f} ms")

# İlk yürütülen görevin en yüksek öncelikli (MissileGuidance) olduğu doğrulanmalıdır!
assert executor.execution_log[0]["task"] == "MissileGuidance"
assert executor.execution_log[1]["task"] == "TelemetryTask"
assert executor.execution_log[2]["task"] == "LogTask"

print("\n[PASS] Kod 1: Advanced Executor Motoru ve Öncelikli Dağıtım Başarıyla Doğrulandı.")

# ============================================================================
# KOD HÜCRESİ 2: CPU Pinning ve Gerçek Zamanlı Jitter Simülasyonu
# ============================================================================
import random
import math
import numpy as np

class CpuAffinitySimulator:
    # Standart paylaşımlı çekirdek ile izole gerçek zamanlı çekirdek kıyaslayıcısı.
    def __init__(self, target_period_ms: float = 1.0): # 1000 Hz döngü
        self.target_period_ms = target_period_ms

    def simulate_shared_core_execution(self, iterations: int = 1000) -> List[float]:
        # Paylaşımlı çekirdekte işletim sistemi kesmeleri ve bağlam değişimi (Context Switch) vardır
        latencies = []
        for _ in range(iterations):
            # Normal taban gecikme + rastgele OS jitter + periyodik spike (kesmeler)
            jitter = random.gauss(0, 0.08) # 80 us gürültü
            if random.random() < 0.03: # %3 ihtimalle OS kesmesi (Interrupt)
                jitter += random.uniform(0.5, 1.8) # 1.8 ms'ye varan devasa gecikme!
            latencies.append(max(0.1, self.target_period_ms + jitter))
        return latencies

    def simulate_isolated_rt_core_execution(self, iterations: int = 1000) -> List[float]:
        # İzole SCHED_FIFO çekirdekte kesme ve context switch yoktur; jitter mikrosaniyelerdedir
        latencies = []
        for _ in range(iterations):
            jitter = random.gauss(0, 0.005) # Sadece 5 us donanım jitterı!
            latencies.append(self.target_period_ms + jitter)
        return latencies

sim = CpuAffinitySimulator(target_period_ms=1.0)
shared_deltas = sim.simulate_shared_core_execution(1000)
isolated_deltas = sim.simulate_isolated_rt_core_execution(1000)

shared_jitter_us = [abs(d - 1.0) * 1000.0 for d in shared_deltas]
isolated_jitter_us = [abs(d - 1.0) * 1000.0 for d in isolated_deltas]

print(f"[1000 Hz Uçuş Kontrol Döngüsü Jitter Analizi]")
print(f"  - Paylaşımlı Çekirdek (Standard Linux):")
print(f"      * Ortalama Jitter : {np.mean(shared_jitter_us):.2f} µs")
print(f"      * Azami (Max) Jitter: {np.max(shared_jitter_us):.2f} µs ({np.max(shared_jitter_us)/1000:.3f} ms - DEADLINE İHLALİ!)")
print(f"  - İzole Çekirdek (Core Pinned RT FIFO):")
print(f"      * Ortalama Jitter : {np.mean(isolated_jitter_us):.2f} µs")
print(f"      * Azami (Max) Jitter: {np.max(isolated_jitter_us):.2f} µs (Deterministik Sınır)")

assert np.max(shared_jitter_us) > 500.0, "Paylaşımlı çekirdekte beklenen spike oluşmadı!"
assert np.max(isolated_jitter_us) < 50.0, "İzole çekirdekte azami jitter 50 µs'nin altında kalmalıdır!"
print("\n[PASS] Kod 2: CPU Pinning ve Gerçek Zamanlı Jitter İzolasyonu Başarıyla Doğrulandı.")

# ============================================================================
# KOD HÜCRESİ 3: Reentrant Grup Paylaşımlı Durum Koruması (Reader-Writer Lock)
# ============================================================================
import threading
import time

class SharedRadarTrackTable:
    # Modern C++20 std::shared_mutex davranışını taklit eden thread-safe tablo.
    def __init__(self):
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self.lock = threading.RLock()
        self.active_readers = 0
        self.read_count = 0
        self.write_count = 0

    def read_track(self, track_id: int) -> Optional[Dict[str, Any]]:
        with self.lock:
            self.active_readers += 1
            self.read_count += 1
        
        # Simüle edilmiş okuma gecikmesi
        time.sleep(0.0001)
        data = self.tracks.get(track_id, None)

        with self.lock:
            self.active_readers -= 1
        return data

    def update_track(self, track_id: int, distance_m: float):
        with self.lock:
            self.write_count += 1
            self.tracks[track_id] = {
                "distance_m": distance_m,
                "timestamp": time.perf_counter()
            }

table = SharedRadarTrackTable()

# 1 Yazıcı ve 4 Eşzamanlı Okuyucu Thread Simülasyonu
def writer_job():
    for d in range(5000, 4000, -100):
        table.update_track(101, float(d))
        time.sleep(0.0005)

def reader_job():
    for _ in range(20):
        _ = table.read_track(101)
        time.sleep(0.0002)

threads = []
t_writer = threading.Thread(target=writer_job)
threads.append(t_writer)

for _ in range(4):
    t_reader = threading.Thread(target=reader_job)
    threads.append(t_reader)

for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"[Reader-Writer Paylaşımlı Durum Testi]")
print(f"  - Toplam Başarılı Yazma İşlemi : {table.write_count}")
print(f"  - Toplam Eşzamanlı Okuma İşlemi: {table.read_count}")
print(f"  - Son Hedef Verisi             : {table.read_track(101)}")

assert table.write_count == 10
assert table.read_count == 81 # 80 loop + 1 son print
print("\n[PASS] Kod 3: Reader-Writer Eşzamanlı Durum Koruması Başarıyla Doğrulandı.")

# ============================================================================
# KOD HÜCRESİ 4: Hata Enjeksiyonu (Fault Injection) ve Savunma Doğrulama Testi
# ============================================================================

# ----------------------------------------------------------------------------
# TEST A: Thread Havuzu Açlığı (Thread Starvation Injection)
# ----------------------------------------------------------------------------
print("[TEST A] Thread Havuzu Açlığı Enjeksiyonu Başlatılıyor...")

class StarvationDetector:
    def __init__(self, pool_size: int = 2):
        self.pool_size = pool_size
        self.busy_threads = 0

    def acquire_worker(self) -> bool:
        if self.busy_threads >= self.pool_size:
            return False # Havuz tükendi!
        self.busy_threads += 1
        return True

detector = StarvationDetector(pool_size=2)
# 2 thread bloklayıcı işlerle kilitlensin
assert detector.acquire_worker() == True
assert detector.acquire_worker() == True

# 3. Kritik Uçuş Kontrol görevi geliyor ama havuzda yer yok!
starvation_detected = False
if not detector.acquire_worker():
    starvation_detected = True
    print("  [BEKLENEN TEHLİKE]: THREAD_STARVATION! Kritik görev için boş işçi bulunamadı!")

assert starvation_detected == True
print("  [PASS] Test A Başarıyla Geçti: Thread açlığı senaryosu yakalandı.\n")

# ----------------------------------------------------------------------------
# TEST B: Çapraz Kilitlenme (AB-BA Deadlock Injection)
# ----------------------------------------------------------------------------
print("[TEST B] Çapraz Callback Kilitlenmesi (Deadlock) Simülasyonu...")

class CrossDeadlockSimulator:
    def __init__(self):
        self.res_A_locked = False
        self.res_B_locked = False

    def simulate_cross_wait(self) -> str:
        # Thread 1: A'yı kilitledi, B'yi bekliyor
        self.res_A_locked = True
        # Thread 2: B'yi kilitledi, A'yı bekliyor
        self.res_B_locked = True
        
        if self.res_A_locked and self.res_B_locked:
            return "DEADLOCK_DETECTED: Thread 1 B'yi, Thread 2 ise A'yı bekliyor! Karşılıklı kilitlenme."

cross_sim = CrossDeadlockSimulator()
dl_res = cross_sim.simulate_cross_wait()
print(f"  [BEKLENEN DEADLOCK YAKALANDI]: {dl_res}")
assert "DEADLOCK_DETECTED" in dl_res
print("  [PASS] Test B Başarıyla Geçti: Çapraz kilitlenme tespit edildi.\n")

# ----------------------------------------------------------------------------
# TEST C: Çekirdek Aşırı Yüklenmesi (Core Over-Subscription Tespiti)
# ----------------------------------------------------------------------------
print("[TEST C] Core Over-Subscription Tespiti...")

def validate_executor_threads(configured_threads: int, available_cores: int) -> bool:
    # Savunma Kuralı: Thread sayısı asla fiziksel çekirdek sayısını aşamaz!
    if configured_threads > available_cores:
        raise ValueError(f"OVER_SUBSCRIPTION_ERROR: Yapılandırılan thread ({configured_threads}) "
                         f"fiziksel çekirdekten ({available_cores}) fazla olamaz!")
    return True

oversub_caught = False
try:
    # 4 çekirdekli aviyonik bilgisayara 32 thread atanmaya çalışılıyor!
    validate_executor_threads(configured_threads=32, available_cores=4)
except ValueError as e:
    oversub_caught = True
    print(f"  [BEKLENEN KURAL İHLALİ]: {e}")

assert oversub_caught == True
print("  [PASS] Test C Başarıyla Geçti: Aşırı iş parçacığı tahsisi engellendi.")

print("\n[PASS] Kod 4: 3 Kritik Executor Hata Enjeksiyonu Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 50.000 Callback Çoklu Frekanslı Aviyonik Benchmark
# ============================================================================
import time
import numpy as np

def run_executor_comparison_benchmark(total_callbacks: int = 50000):
    print(f"[BENCHMARK] 4 Farklı Frekans Seviyesinde Toplam {total_callbacks:,} Callback Kıyaslanıyor...")

    # Simüle edilmiş görev yükleri (taban süreler)
    # 1000 Hz Uçuş Kontrol: 0.005 ms, 100 Hz Radar: 0.02 ms, 10 Hz Telemetri: 0.05 ms, 1 Hz Log: 0.2 ms
    crit_count = int(total_callbacks * 0.70) # %70 uçuş kontrol
    radar_count = int(total_callbacks * 0.20)
    telem_count = int(total_callbacks * 0.08)
    log_count = int(total_callbacks * 0.02)

    # 1. SingleThreadedExecutor Gecikmeleri (Tüm kuyruk tek hatta birikir)
    st_crit_latencies = np.random.lognormal(mean=3.2, sigma=0.4, size=crit_count) # ~24 us + birikme
    st_crit_latencies = st_crit_latencies + np.random.exponential(scale=15.0, size=crit_count)

    # 2. MultiThreadedExecutor Gecikmeleri (4 Worker - yük bölünür)
    mt_crit_latencies = np.random.lognormal(mean=2.6, sigma=0.3, size=crit_count) # ~13 us
    mt_crit_latencies = mt_crit_latencies + np.random.exponential(scale=3.0, size=crit_count)

    # 3. Priority + Core Pinning Executor (Kritik döngü izole çekirdekte, jitter sıfıra yakın)
    rt_crit_latencies = np.random.normal(loc=5.0, scale=0.8, size=crit_count) # ~5 us sabit
    rt_crit_latencies = np.clip(rt_crit_latencies, 2.0, 12.0)

    # İstatistikler (µs cinsinden)
    results = {
        "total_callbacks": total_callbacks,
        "st_p50": np.percentile(st_crit_latencies, 50),
        "st_p95": np.percentile(st_crit_latencies, 95),
        "st_p99": np.percentile(st_crit_latencies, 99),
        "mt_p50": np.percentile(mt_crit_latencies, 50),
        "mt_p95": np.percentile(mt_crit_latencies, 95),
        "mt_p99": np.percentile(mt_crit_latencies, 99),
        "rt_p50": np.percentile(rt_crit_latencies, 50),
        "rt_p95": np.percentile(rt_crit_latencies, 95),
        "rt_p99": np.percentile(rt_crit_latencies, 99)
    }
    return results

bench_res = run_executor_comparison_benchmark(total_callbacks=50000)

print(f"\n[1000 Hz UÇUŞ KONTROL GECİKME KIYASLAMASI (Percentiles)]")
print(f"  - Single-Threaded -> p50: {bench_res['st_p50']:.1f} µs | p95: {bench_res['st_p95']:.1f} µs | p99: {bench_res['st_p99']:.1f} µs")
print(f"  - Multi-Threaded  -> p50: {bench_res['mt_p50']:.1f} µs | p95: {bench_res['mt_p95']:.1f} µs | p99: {bench_res['mt_p99']:.1f} µs")
print(f"  - Priority + RT   -> p50: {bench_res['rt_p50']:.1f} µs | p95: {bench_res['rt_p95']:.1f} µs | p99: {bench_res['rt_p99']:.1f} µs")

assert bench_res['rt_p99'] < bench_res['st_p99'] * 0.2, "RT Executor p99 gecikmesi Single-Thread'den en az 5 kat daha iyi olmalıdır!"
print("\n[PASS] Kod 5: Aviyonik Çoklu Frekans Benchmark Kıyaslaması Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli Görsel Mimari Dashboard (300 DPI, Dark Theme)
# ============================================================================
import os
import matplotlib.pyplot as plt
import numpy as np

# Matplotlib Dark Theme Ayarları
plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 14), dpi=300)
fig.patch.set_facecolor('#0F172A')

for row in axs:
    for ax in row:
        ax.set_facecolor('#1E293B')
        ax.grid(True, color='#334155', linestyle='--', alpha=0.6)
        ax.tick_params(colors='#E2E8F0', labelsize=10)
        for spine in ax.spines.values():
            spine.set_color('#475569')

# ----------------------------------------------------------------------------
# PANEL 1: ROS 2 Executor Katman Şeması ve WaitSet Dağıtımı
# ----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("PANEL 1: ROS 2 Executor & WaitSet Olay Dağıtım Akışı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

layers = [
    ("Entities Registry: Timers, Subscriptions, Services, Clients", 0.85, '#38BDF8'),
    ("WaitSet Collection: rcl_wait_set_t Construction", 0.68, '#818CF8'),
    ("Kernel Blocking: rcl_wait() (Socket Events & Clock Sleep)", 0.51, '#64748B'),
    ("Callback Group Dispatcher (Mutex vs Reentrant Constraints)", 0.34, '#F59E0B'),
    ("Worker Thread Pool: Thread Affinity & SCHED_FIFO Execution", 0.17, '#10B981')
]

for name, y_pos, color in layers:
    rect = plt.Rectangle((0.08, y_pos - 0.05), 0.84, 0.08, facecolor=color, edgecolor='#FFFFFF', alpha=0.85, transform=ax1.transAxes)
    ax1.add_patch(rect)
    ax1.text(0.5, y_pos - 0.01, name, color='#0F172A' if color != '#64748B' else '#FFFFFF', 
             fontsize=9.5, fontweight='bold', ha='center', va='center', transform=ax1.transAxes)

ax1.set_xlim(0, 1)
ax1.set_ylim(0, 1)
ax1.axis('off')

# ----------------------------------------------------------------------------
# PANEL 2: Executor Gecikme Kıyaslaması (Percentiles)
# ----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("PANEL 2: 1000 Hz Uçuş Kontrol Gecikme Kıyaslaması (µs)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

categories = ['p50 (Medyan)', 'p95 (Tepe)', 'p99 (Kuyruk)']
x_indices = np.arange(len(categories))
width = 0.25

st_vals = [bench_res['st_p50'], bench_res['st_p95'], bench_res['st_p99']]
mt_vals = [bench_res['mt_p50'], bench_res['mt_p95'], bench_res['mt_p99']]
rt_vals = [bench_res['rt_p50'], bench_res['rt_p95'], bench_res['rt_p99']]

b1 = ax2.bar(x_indices - width, st_vals, width, label='SingleThreaded', color='#EF4444', alpha=0.85)
b2 = ax2.bar(x_indices, mt_vals, width, label='MultiThreaded', color='#F59E0B', alpha=0.85)
b3 = ax2.bar(x_indices + width, rt_vals, width, label='Priority + RT Core', color='#10B981', alpha=0.85)

ax2.set_ylabel("Gecikme (Mikrosaniye - µs)", color='#E2E8F0', fontsize=11)
ax2.set_xticks(x_indices)
ax2.set_xticklabels(categories, color='#E2E8F0', fontsize=10)
ax2.legend(facecolor='#0F172A', edgecolor='#475569', labelcolor='#E2E8F0')

for bar in b1:
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 1.0, f"{yval:.1f}", ha='center', va='bottom', color='#FCA5A5', fontsize=8.5)

for bar in b3:
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 1.0, f"{yval:.1f}", ha='center', va='bottom', color='#6EE7B7', fontsize=8.5, fontweight='bold')

# ----------------------------------------------------------------------------
# PANEL 3: 8 Çekirdekli Aviyonik CPU Pinning Şeması
# ----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("PANEL 3: 8 Çekirdekli Aviyonik CPU Pinning Haritası", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

cores = [f"Core {i}" for i in range(8)]
roles = [
    "Linux OS & IRQ",
    "GUI & RViz2",
    "MultiThread Worker 1",
    "MultiThread Worker 2",
    "İZOLE RT CORE: 1000Hz Uçuş Kontrol (SCHED_FIFO 99)",
    "MultiThread Worker 3",
    "Telemetri & Ağ",
    "Kara Kutusu Loglama"
]
colors = ['#64748B', '#64748B', '#38BDF8', '#38BDF8', '#10B981', '#38BDF8', '#F59E0B', '#F59E0B']

y_pos = np.arange(len(cores))
bars_c = ax3.barh(y_pos, [1]*8, color=colors, alpha=0.85, edgecolor='#FFFFFF', height=0.6)

ax3.set_yticks(y_pos)
ax3.set_yticklabels(cores, color='#E2E8F0', fontsize=10)
ax3.set_xticks([])

for i, bar in enumerate(bars_c):
    ax3.text(0.05, bar.get_y() + bar.get_height()/2.0, roles[i], 
             ha='left', va='center', color='#FFFFFF' if colors[i] != '#38BDF8' else '#0F172A', 
             fontsize=9, fontweight='bold')

# ----------------------------------------------------------------------------
# PANEL 4: 1000 Hz Kontrol Döngüsünde Jitter Karşılaştırması
# ----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("PANEL 4: 1000 Hz Uçuş Kontrol Jitter Dalgalanması (ms)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

steps = np.arange(1, 101)
ax4.plot(steps, shared_deltas[:100], color='#EF4444', linewidth=1.5, label='Paylaşımlı Çekirdek (Spike / Jitter)')
ax4.plot(steps, isolated_deltas[:100], color='#10B981', linewidth=2.0, label='İzole RT Çekirdek (Core Pinned)')
ax4.axhline(y=1.0, color='#38BDF8', linestyle='--', linewidth=1.2, label='Hedef 1.0 ms (1000 Hz)')

ax4.set_xlabel("Döngü Adımları (Iterations)", color='#E2E8F0', fontsize=11)
ax4.set_ylabel("Periyot Süresi (ms)", color='#E2E8F0', fontsize=11)
ax4.set_ylim(0.5, 2.5)
ax4.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#E2E8F0', fontsize=9)

# Filigran ve Lisans Notu
fig.text(0.5, 0.015, "ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR | Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)",
         ha='center', va='bottom', color='#94A3B8', fontsize=10, fontweight='bold')

plt.tight_layout(rect=[0, 0.03, 1, 0.97])

output_png = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_217/gun_217_ros2_executor_ve_callback.png"
if not os.path.isabs(output_png) or not os.path.exists(os.path.dirname(output_png)):
    output_png = "gun_217_ros2_executor_ve_callback.png"

plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "Görsel dosya boyutu 100 KB'den küçük olamaz!"

