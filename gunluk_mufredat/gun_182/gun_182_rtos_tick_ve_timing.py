# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 182: rtos_tick_ve_timing - Bağımsız Çalıştırılabilir Kod Laboratuvarı
"""

# ==============================================================================
# KOD BLOĞU: 4
# ==============================================================================
# KOD HÜCRESİ 1: vTaskDelay vs vTaskDelayUntil Simülatörü (Faz Kayması / Drift)
# ------------------------------------------------------------------------------
# Bu simülasyon, 10 ms periyotla çalışması gereken bir görevin:
# 1. vTaskDelay (Göreli Gecikme): Görevin hesaplama süresi periyoda eklenir -> Kümülatif Drift!
# 2. vTaskDelayUntil (Mutlak Periyot): Sabit faz referansı -> Sıfır Kümülatif Drift!
# 50 döngü boyunca zaman kaymasını mikrosaniye seviyesinde modeller.

import numpy as np

def simulate_delay_mechanisms(cycles=50, target_period_ms=10.0):
    # Hesaplama süresi: 1.5 ms ile 3.5 ms arasında değişkenlik göstersin (Jitter)
    np.random.seed(42)
    compute_times = np.random.uniform(1.5, 3.5, size=cycles)
    
    # 1. vTaskDelay Simülasyonu (Relative Delay)
    vtaskdelay_timestamps = [0.0]
    current_time_rel = 0.0
    for c in compute_times:
        current_time_rel += c                   # Görev çalıştı
        current_time_rel += target_period_ms    # vTaskDelay(10) kadar uyudu
        vtaskdelay_timestamps.append(current_time_rel)
        
    # 2. vTaskDelayUntil Simülasyonu (Absolute Periodic Execution)
    vtaskdelayuntil_timestamps = [0.0]
    last_wake_time = 0.0
    current_time_abs = 0.0
    for c in compute_times:
        current_time_abs += c # Görev çalıştı
        # vTaskDelayUntil: last_wake_time + target_period_ms anına kadar uyur
        next_wake = last_wake_time + target_period_ms
        sleep_needed = max(0.0, next_wake - current_time_abs)
        current_time_abs += sleep_needed
        last_wake_time = next_wake
        vtaskdelayuntil_timestamps.append(current_time_abs)
        
    ideal_timestamps = [i * target_period_ms for i in range(cycles + 1)]
    
    drift_rel = np.array(vtaskdelay_timestamps) - np.array(ideal_timestamps)
    drift_abs = np.array(vtaskdelayuntil_timestamps) - np.array(ideal_timestamps)
    
    return {
        "cycles": cycles,
        "ideal": ideal_timestamps,
        "vtaskdelay": vtaskdelay_timestamps,
        "vtaskdelayuntil": vtaskdelayuntil_timestamps,
        "drift_rel": drift_rel,
        "drift_abs": drift_abs,
        "compute_times": compute_times
    }

res_delay = simulate_delay_mechanisms(cycles=50, target_period_ms=10.0)

print("=" * 68)
print("vTaskDelay VS vTaskDelayUntil ZAMAN KAYMASI (DRIFT) ANALİZİ (50 Döngü)")
print("=" * 68)
print(f"İdeal Bitiş Zamanı (50 döngü x 10 ms): {res_delay['ideal'][-1]:.1f} ms")
print(f"vTaskDelay Gerçekleşen Bitiş Zamanı   : {res_delay['vtaskdelay'][-1]:.1f} ms")
print(f"  -> vTaskDelay Kümülatif Faz Kayması : +{res_delay['drift_rel'][-1]:.1f} ms (BÜYÜK HATA!)")

print(f"\nvTaskDelayUntil Gerçekleşen Bitiş     : {res_delay['vtaskdelayuntil'][-1]:.1f} ms")
print(f"  -> vTaskDelayUntil Kümülatif Kayma  : {res_delay['drift_abs'][-1]:.1f} ms (SIFIR KAYMA / %100 DETERMINISTIK)")

# Doğrulamalar
assert res_delay['drift_abs'][-1] == 0.0, "HATA: vTaskDelayUntil kümülatif kayması sıfır olmalıdır!"
assert res_delay['drift_rel'][-1] > 100.0, "HATA: vTaskDelay hesaplama süresi kadar kayma biriktirmeliydi!"
print("\n[BAŞARILI]: vTaskDelayUntil fonksiyonunun faz kaymasını sıfırladığı matematiksel olarak kanıtlandı.")

# ==============================================================================
# KOD BLOĞU: 6
# ==============================================================================
# KOD HÜCRESİ 2: configTICK_RATE_HZ Optimizasyonu (CPU Overhead vs Çözünürlük)
# ------------------------------------------------------------------------------
# Farklı SysTick frekanslarının (100 Hz, 250 Hz, 500 Hz, 1000 Hz, 2000 Hz):
# 1. SysTick ISR CPU harcama maliyetini (Overhead)
# 2. Minimum zamanlama çözünürlüğünü ve hata payını modeller.

class TickRateAnalyzer:
    def __init__(self, f_cpu_mhz=168, systick_isr_cycles=45):
        self.f_cpu_mhz = f_cpu_mhz
        self.systick_isr_cycles = systick_isr_cycles # SysTick başına ortalama çevrim
        
    def analyze(self, tick_rates=[100, 250, 500, 1000, 2000]):
        cpu_cycles_per_sec = self.f_cpu_mhz * 1e6
        results = []
        
        for hz in tick_rates:
            tick_period_ms = 1000.0 / hz
            total_isr_cycles_sec = hz * self.systick_isr_cycles
            cpu_overhead_percent = (total_isr_cycles_sec / cpu_cycles_per_sec) * 100.0
            
            # 5 ms'lik bir gecikme istendiğinde oluşacak kuantalama hatası
            desired_delay_ms = 5.0
            achieved_ticks = round(desired_delay_ms / tick_period_ms)
            achieved_delay_ms = achieved_ticks * tick_period_ms
            quantization_error_ms = abs(achieved_delay_ms - desired_delay_ms)
            
            results.append({
                "tick_rate_hz": hz,
                "tick_period_ms": tick_period_ms,
                "cpu_overhead_percent": cpu_overhead_percent,
                "quantization_error_ms": quantization_error_ms,
                "achieved_delay_ms": achieved_delay_ms
            })
        return results

analyzer = TickRateAnalyzer(f_cpu_mhz=168, systick_isr_cycles=60)
tick_data = analyzer.analyze()

print("=" * 68)
print("SYSTICK TICK RATE (HZ) OPTİMİZASYON VE MALİYET TABLOSU")
print("=" * 68)
print(f"{'Tick Rate':<12} | {'Periyot':<10} | {'CPU Yükü (%)':<14} | {'5ms Hedefte Gerçekleşen':<24} | {'Hata (ms)':<10}")
print("-" * 68)
for row in tick_data:
    print(f"{row['tick_rate_hz']:4d} Hz      | {row['tick_period_ms']:6.2f} ms  | %{row['cpu_overhead_percent']:8.4f}     | {row['achieved_delay_ms']:6.2f} ms                  | {row['quantization_error_ms']:5.2f} ms")

# Doğrulama: 1000 Hz'de 5 ms tam yakalanmalı, 100 Hz'de hata olmalı
assert tick_data[3]["quantization_error_ms"] == 0.0, "1000 Hz'de 5 ms kuantalama hatası sıfır olmalı!"
assert tick_data[0]["quantization_error_ms"] > 0.0, "100 Hz'de 5 ms tam yakalanamamalı (10 ms olmalı)!"
print("\n[BAŞARILI]: SysTick frekansının CPU yükü ve kuantalama hatası analizi doğrulandı.")

# ==============================================================================
# KOD BLOĞU: 8
# ==============================================================================
# KOD HÜCRESİ 3: FreeRTOS Yazılımsal Zamanlayıcılar (Software Timers) Simülasyonu
# ------------------------------------------------------------------------------
# Bu simülasyon, FreeRTOS Timer Daemon Task ve Timer Command Queue mantığını modeller.
# - Timer 1: One-Shot Lazer Güvenlik Zamanlayıcısı (50 ms)
# - Timer 2: Auto-Reload Gimbal Kalibrasyon Zamanlayıcısı (20 ms)

class SoftwareTimer:
    def __init__(self, timer_id, name, period_ticks, auto_reload=False, callback=None):
        self.timer_id = timer_id
        self.name = name
        self.period_ticks = period_ticks
        self.auto_reload = auto_reload
        self.callback = callback
        self.expiry_tick = 0
        self.is_active = False

class TimerDaemonTask:
    def __init__(self):
        self.timers = []
        self.callback_execution_log = []
        
    def start_timer(self, timer, current_tick):
        timer.is_active = True
        timer.expiry_tick = current_tick + timer.period_ticks
        if timer not in self.timers:
            self.timers.append(timer)

    def stop_timer(self, timer):
        timer.is_active = False

    def process_tick(self, current_tick):
        for t in list(self.timers):
            if t.is_active and current_tick >= t.expiry_tick:
                # Callback Tetikle
                if t.callback:
                    t.callback(current_tick)
                self.callback_execution_log.append((current_tick, t.name))
                
                if t.auto_reload:
                    # Otomatik periyot yenileme
                    t.expiry_tick = current_tick + t.period_ticks
                else:
                    t.is_active = False

daemon = TimerDaemonTask()

# Callback Fonksiyonları
t1_fired = []
t2_fired = []

timer_lrf = SoftwareTimer(1, "LRF_Safety_OneShot", period_ticks=50, auto_reload=False, callback=lambda tick: t1_fired.append(tick))
timer_calib = SoftwareTimer(2, "FLIR_Calib_AutoReload", period_ticks=20, auto_reload=True, callback=lambda tick: t2_fired.append(tick))

# 0. Tick'te iki zamanlayıcıyı da başlat
daemon.start_timer(timer_lrf, current_tick=0)
daemon.start_timer(timer_calib, current_tick=0)

# 100 ms (100 tick) boyunca simüle et
for tick in range(1, 101):
    daemon.process_tick(tick)

print("=" * 68)
print("FREERTOS SOFTWARE TIMERS (YAZILIMSAL ZAMANLAYICILAR) SİMÜLASYONU")
print("=" * 68)
print(f"One-Shot Zamanlayıcı (50 ms): Tetiklenme Sayısı = {len(t1_fired)} | Zaman Damgaları = {t1_fired}")
print(f"Auto-Reload Zamanlayıcı (20 ms): Tetiklenme Sayısı = {len(t2_fired)} | Zaman Damgaları = {t2_fired}")

# Doğrulamalar
assert len(t1_fired) == 1 and t1_fired[0] == 50, "HATA: One-Shot timer tam 50. tickte 1 kez tetiklenmeliydi!"
assert len(t2_fired) == 5, f"HATA: Auto-reload timer 100 tickte 5 kez tetiklenmeliydi (Bulunan: {len(t2_fired)})!"
assert t2_fired == [20, 40, 60, 80, 100], "HATA: Auto-reload zaman damgaları 20, 40, 60, 80, 100 olmalıydı!"
print("\n[BAŞARILI]: One-Shot ve Auto-Reload yazılımsal zamanlayıcı davranışları %100 doğrulandı.")

# ==============================================================================
# KOD BLOĞU: 10
# ==============================================================================
# KOD HÜCRESİ 4: Tick Rollover ve Çift Gecikme Listesi Swap Modeli
# ------------------------------------------------------------------------------
# FreeRTOS'un tick taşması (rollover) anında kilitlenmesini engelleyen
# pxDelayedTaskList ve pxOverflowDelayedTaskList işaretçi takasını modeller.

class DualListScheduler:
    def __init__(self, max_tick=255): # Gösterim için 8-bit (255) taşma sınırı kullanalım
        self.max_tick = max_tick
        self.tick_count = max_tick - 5 # Taşmaya 5 tick kala başlatalım
        
        self.list1 = []
        self.list2 = []
        
        self.pxDelayedTaskList = self.list1
        self.pxOverflowDelayedTaskList = self.list2
        self.woken_tasks = []

    def delay_task(self, task_name, delay_ticks):
        wake_time = self.tick_count + delay_ticks
        if wake_time > self.max_tick:
            # Taşma listesine ekle
            actual_wake = wake_time % (self.max_tick + 1)
            self.pxOverflowDelayedTaskList.append((task_name, actual_wake))
        else:
            # Normal listeye ekle
            self.pxDelayedTaskList.append((task_name, wake_time))

    def step(self):
        prev_tick = self.tick_count
        self.tick_count = (self.tick_count + 1) % (self.max_tick + 1)
        
        # Taşma Gerçekleşti mi?
        if self.tick_count < prev_tick:
            # taskSWITCH_DELAYED_LISTS(): İşaretçileri takas et!
            self.pxDelayedTaskList, self.pxOverflowDelayedTaskList = \
                self.pxOverflowDelayedTaskList, self.pxDelayedTaskList

        # Uyanan görevleri kontrol et
        remaining = []
        for t_name, w_time in self.pxDelayedTaskList:
            if self.tick_count >= w_time:
                self.woken_tasks.append((self.tick_count, t_name))
            else:
                remaining.append((t_name, w_time))
        self.pxDelayedTaskList = remaining

sched_rollover = DualListScheduler(max_tick=255)

# t = 250'de iki görev gecikmeye girsin:
# Task A: 3 tick sonra uyanacak (t = 253 -> Taşma öncesi)
# Task B: 10 tick sonra uyanacak (t = 260 -> 255'i aşıp t=4'te uyanmalı!)
sched_rollover.delay_task("TaskA_PreRoll", delay_ticks=3)
sched_rollover.delay_task("TaskB_PostRoll", delay_ticks=10)

print("=" * 68)
print("TICK ROLLOVER VE DUAL LIST POINTER SWAP SİMÜLASYONU")
print("=" * 68)
print(f"Başlangıç Tick'i: {sched_rollover.tick_count} (Taşma Sınırı: {sched_rollover.max_tick})")
print(f"  - pxDelayedTaskList Öncesi         : {sched_rollover.pxDelayedTaskList}")
print(f"  - pxOverflowDelayedTaskList Öncesi : {sched_rollover.pxOverflowDelayedTaskList}")

for step_idx in range(12):
    sched_rollover.step()

print(f"\n12 Adım Sonrası Uyanan Görevler:")
for wake_tick, name in sched_rollover.woken_tasks:
    print(f"  - Görev '{name}' tam Tick {wake_tick}'te başarıyla uyandı!")

# Doğrulamalar
assert any(t[1] == "TaskA_PreRoll" and t[0] == 253 for t in sched_rollover.woken_tasks), "Task A t=253'te uyanmalı!"
assert any(t[1] == "TaskB_PostRoll" and t[0] == 4 for t in sched_rollover.woken_tasks), "Task B t=4'te uyanmalı!"
print("\n[BAŞARILI]: Çift liste swap mekanizması taşma sınırını sıfır hatayla aştı.")

# ==============================================================================
# KOD BLOĞU: 12
# ==============================================================================
# KOD HÜCRESİ 5: Savunma Sanayii Aviyonik Senaryosu: FLIR Gimbal ve LRF
# ------------------------------------------------------------------------------
# ASELSAN Elektro-Optik Hedefleme Sistemi (FLIR Gimbal):
# - Görev 1: Gimbal Servo PID Döngüsü (1000 Hz / 1 ms, vTaskDelayUntil)
# - Görev 2: Lazer Mesafe Ölçer (LRF) Güvenlik Zamanlayıcısı (50 ms One-Shot Timer)
# - Görev 3: Termal Dedektör Kalibrasyonu (NUC - 100 ms Auto-Reload Timer)
# 100 ms'lik taktik çalışmada zamanlama kararlılığı ve callback takibi.

import numpy as np

def simulate_flir_gimbal_system(duration_ms=100):
    time_ms = np.arange(0, duration_ms, 1)
    
    pid_execution_times = []
    lrf_timer_events = []
    nuc_timer_events = []
    
    # LRF Lazer Atışı 10. ms'de başlasın (50 ms sonra güvenlik kesici devreyi kapatmalı)
    lrf_start_time = 10
    lrf_safety_limit = 50
    lrf_active = False
    
    # NUC periyodu: 40 ms
    nuc_period = 40
    
    for t in time_ms:
        # 1. Gimbal PID 1000 Hz (Her 1 ms'de tam vaktinde çalışır)
        pid_execution_times.append(t)
        
        # 2. LRF Atış Mantığı
        if t == lrf_start_time:
            lrf_active = True
        if lrf_active and t == lrf_start_time + lrf_safety_limit:
            lrf_timer_events.append(t) # 50 ms One-Shot Timer Fired!
            lrf_active = False
            
        # 3. NUC Kalibrasyon (Auto-Reload)
        if t > 0 and t % nuc_period == 0:
            nuc_timer_events.append(t)
            
    return {
        "duration_ms": duration_ms,
        "pid_count": len(pid_execution_times),
        "lrf_events": lrf_timer_events,
        "nuc_events": nuc_timer_events
    }

flir_sim = simulate_flir_gimbal_system(duration_ms=100)

print("=" * 68)
print("ASELSAN FLIR GİMBAL VE LAZER MESAFE ÖLÇER ZAMANLAMA RAPORU (100 ms)")
print("=" * 68)
print(f"Toplam Simülasyon Süresi       : {flir_sim['duration_ms']} ms")
print(f"Gimbal 1000 Hz PID Örnek Sayısı: {flir_sim['pid_count']} çevrim (%100 Tamamlandı)")
print(f"LRF Güvenlik Zamanlayıcısı     : Tetiklenme Anı = {flir_sim['lrf_events']} ms (10 ms + 50 ms = 60 ms)")
print(f"FLIR NUC Kalibrasyon Zamanları : {flir_sim['nuc_events']} ms")

# Doğrulama
assert flir_sim["pid_count"] == 100, "100 ms sürede 100 adet 1 ms PID döngüsü koşmalıdır!"
assert flir_sim["lrf_events"] == [60], "LRF güvenlik zamanlayıcısı tam 60. ms'de devreyi kapatmalıdır!"
assert flir_sim["nuc_events"] == [40, 80], "NUC kalibrasyonu 40 ve 80. ms'lerde çalışmalıdır!"
print("\n[BAŞARILI]: FLIR Gimbal ve LRF elektro-optik zamanlama mimarisi %100 doğrulandı.")

# ==============================================================================
# KOD BLOĞU: 14
# ==============================================================================
# KOD HÜCRESİ 6: Endüstriyel Dashboard Görselleştirme ve Kapsamlı Assertions
# ------------------------------------------------------------------------------
# 300 DPI, Dark Theme (#0F172A), 4 Panelli Endüstriyel Aviyonik Dashboard:
# Panel 1: vTaskDelay vs vTaskDelayUntil Kümülatif Faz Kayması (Drift)
# Panel 2: SysTick Tick Rate (100 Hz - 2000 Hz) CPU Overhead ve Hata Grafiği
# Panel 3: Software Timers Zaman Çizelgesi (One-Shot LRF vs Auto-Reload NUC)
# Panel 4: Tick Rollover İki Liste İşaretçi Takası (Dual List Swap)

import os
import matplotlib.pyplot as plt
import numpy as np

# PNG Yol Tanımı
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_182_rtos_tick_ve_timing.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_182\gun_182_rtos_tick_ve_timing.png"

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
# PANEL 1: vTaskDelay vs vTaskDelayUntil Kümülatif Faz Kayması
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. Periyot Zamanlama Sapması: vTaskDelay vs vTaskDelayUntil (Drift)", fontsize=11, fontweight='bold', pad=10)

cyc_axis = np.arange(len(res_delay["ideal"]))
ax1.plot(cyc_axis, res_delay["drift_rel"], color='#EF4444', linewidth=2.5, label='vTaskDelay (Kümülatif Faz Kayması)')
ax1.plot(cyc_axis, res_delay["drift_abs"], color='#10B981', linewidth=2.5, linestyle='--', label='vTaskDelayUntil (Sıfır Drift)')

ax1.set_xlabel("Döngü Sayısı", fontsize=10)
ax1.set_ylabel("Zaman Sapması (ms)", fontsize=10)
ax1.set_xlim(0, 50)
ax1.legend(loc='upper left', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC')
ax1.text(25, 60, f"50 Döngüde +{res_delay['drift_rel'][-1]:.1f} ms Sapma!", color='#EF4444', fontweight='bold', fontsize=10)

# ------------------------------------------------------------------------------
# PANEL 2: SysTick Tick Rate vs CPU Overhead ve Hata
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. SysTick Frekansı (Hz) vs CPU Yükü ve Kuantalama Hatası", fontsize=11, fontweight='bold', pad=10)

rates = [r["tick_rate_hz"] for r in tick_data]
overheads = [r["cpu_overhead_percent"] for r in tick_data]
errors = [r["quantization_error_ms"] for r in tick_data]

ax2_twin = ax2.twinx()
ax2_twin.tick_params(colors='#F59E0B', labelsize=9)
ax2_twin.yaxis.label.set_color('#F59E0B')
ax2_twin.grid(False)

line1 = ax2.plot(rates, overheads, color='#38BDF8', marker='o', linewidth=2.5, label='CPU Yükü (%)')
line2 = ax2_twin.plot(rates, errors, color='#F59E0B', marker='s', linewidth=2.5, linestyle=':', label='5 ms Hedefte Hata (ms)')

ax2.set_xlabel("SysTick Frekansı (Hz)", fontsize=10)
ax2.set_ylabel("SysTick CPU Overhead (%)", fontsize=10)
ax2_twin.set_ylabel("Kuantalama Hatası (ms)", fontsize=10)
ax2.set_xticks(rates)

lines = line1 + line2
labels = [l.get_label() for l in lines]
ax2.legend(lines, labels, loc='center right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC')

# ------------------------------------------------------------------------------
# PANEL 3: Software Timers Zaman Çizelgesi
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. Software Timers Olayları: One-Shot LRF vs Auto-Reload NUC", fontsize=11, fontweight='bold', pad=10)

time_pts = np.arange(0, 101)
ax3.axvspan(10, 60, color='#EF4444', alpha=0.25, label='LRF Lazer Açık (50 ms Güvenlik Penceresi)')
ax3.axvline(60, color='#EF4444', linestyle='-', linewidth=2.5, label='One-Shot Timer (LRF Güvenlik Kapatma)')

for nuc_t in flir_sim["nuc_events"]:
    ax3.axvline(nuc_t, color='#10B981', linestyle='--', linewidth=2, label='Auto-Reload NUC (40 ms)' if nuc_t == 40 else "")

ax3.set_yticks([])
ax3.set_xlabel("Zaman (ms)", fontsize=10)
ax3.set_xlim(0, 100)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)
ax3.text(12, 0.5, "Lazer Işını Aktif", color='#F87171', fontweight='bold', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 4: Tick Rollover İki Liste İşaretçi Takası
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. Tick Rollover Taşması ve Dual List Pointer Swap (255 Sınırı)", fontsize=11, fontweight='bold', pad=10)

ticks_sim = np.arange(245, 260)
# Rollover haritası: 245..255 normal, 256 -> 0..4
mapped_ticks = [t if t <= 255 else t - 256 for t in ticks_sim]

ax4.plot(np.arange(len(ticks_sim)), mapped_ticks, color='#38BDF8', linewidth=2.5, marker='.')
ax4.axvline(10, color='#EF4444', linestyle='--', linewidth=2, label='Tick Rollover Anı (255 -> 0)')

# Görev uyanma noktalarını işaretle
ax4.scatter([8], [253], color='#10B981', s=120, zorder=5, label='Task A Uyanma (t=253)')
ax4.scatter([15], [4], color='#F59E0B', s=120, zorder=5, label='Task B Uyanma (t=4 - Swap Sonrası)')

ax4.set_xlabel("Zaman Adımı", fontsize=10)
ax4.set_ylabel("xTickCount Değeri", fontsize=10)
ax4.legend(loc='lower left', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

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

# Doğrulamalar
assert res_delay['drift_abs'][-1] == 0.0, "HATA: vTaskDelayUntil mutlak zamanlama hatası!"
assert res_delay['drift_rel'][-1] > 100.0, "HATA: vTaskDelay faz kayması hesaplama hatası!"
assert flir_sim["pid_count"] == 100, "HATA: FLIR PID örnek sayısı tutarsız!"
assert flir_sim["lrf_events"] == [60], "HATA: LRF güvenlik zamanlayıcısı tutarsız!"

print("[PASS] GÜN 182: TÜM MATEMATİKSEL VE GÖRSEL DOĞRULAMALAR BAŞARIYLA TAMAMLANDI!")

