# -*- coding: utf-8 -*-
"""
GÜN 193: Fault: Sensor Disconnect ve Bus Timeout Yönetimi
Standalone Python Doğrulama ve Görselleştirme Betiği
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_193\gun_193_fault_sensor_disconnect_bus_timeout.png"

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

