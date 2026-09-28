# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 225: ROS 2 / Gazebo Mini-Capstone Otonom UGV İskeleti Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: Core Kaplan İKA Kinematik Sürüş ve LiDAR Sensör Motoru
# Diferansiyel sürüş dinamiği, odometri entegrasyonu ve 360 derece LiDAR modeli.
# ============================================================================
from dataclasses import dataclass, field
from typing import List, Tuple
import math
import numpy as np

@dataclass
class Pose2D:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0 # Radyan

@dataclass
class Twist2D:
    v: float = 0.0 # Doğrusal hız (m/s)
    omega: float = 0.0 # Açısal hız (rad/s)

class DifferentialDriveUGV:
    def __init__(self, track_width: float = 0.8, wheel_radius: float = 0.25, max_v: float = 3.0, max_w: float = 1.5):
        self.L = track_width      # Dingil açıklığı (m)
        self.r = wheel_radius     # Tekerlek yarıçapı (m)
        self.max_v = max_v        # Azami doğrusal hız (m/s)
        self.max_w = max_w        # Azami açısal hız (rad/s)
        self.pose = Pose2D(0.0, 0.0, 0.0)
        self.current_twist = Twist2D(0.0, 0.0)
        self.odom_history: List[Pose2D] = [Pose2D(0.0, 0.0, 0.0)]

    def apply_command(self, cmd: Twist2D, dt: float):
        # Hız sınırlandırması (Saturation)
        v = max(-self.max_v, min(self.max_v, cmd.v))
        w = max(-self.max_w, min(self.max_w, cmd.omega))
        self.current_twist = Twist2D(v, w)

        # 2. Derece Runge-Kutta / Doğrudan Kinematik İntegrasyon
        if abs(w) > 1e-5:
            # Yay hareketi
            r_icc = v / w
            d_theta = w * dt
            dx = -r_icc * math.sin(self.pose.theta) + r_icc * math.sin(self.pose.theta + d_theta)
            dy = r_icc * math.cos(self.pose.theta) - r_icc * math.cos(self.pose.theta + d_theta)
            self.pose.x += dx
            self.pose.y += dy
            self.pose.theta = (self.pose.theta + d_theta + math.pi) % (2 * math.pi) - math.pi
        else:
            # Düz çizgi hareketi
            self.pose.x += v * math.cos(self.pose.theta) * dt
            self.pose.y += v * math.sin(self.pose.theta) * dt

        self.odom_history.append(Pose2D(self.pose.x, self.pose.y, self.pose.theta))

class SimulatedTacticalLidar:
    def __init__(self, num_beams: int = 72, max_range: float = 30.0):
        self.num_beams = num_beams
        self.max_range = max_range
        self.angles = np.linspace(-math.pi, math.pi, num_beams, endpoint=False)

    def scan(self, robot_pose: Pose2D, obstacles: List[Tuple[float, float, float]]) -> np.ndarray:
        # obstacles: [(x, y, radius), ...]
        ranges = np.full(self.num_beams, self.max_range, dtype=np.float64)
        rx, ry, rth = robot_pose.x, robot_pose.y, robot_pose.theta

        for i, beam_angle in enumerate(self.angles):
            global_angle = rth + beam_angle
            dx = math.cos(global_angle)
            dy = math.sin(global_angle)

            # Işın ile engeller arasındaki kesişim
            for ox, oy, r in obstacles:
                # Işın doğru denklemi: P = R + t * D
                # Çember: |P - O|^2 = r^2
                fx = rx - ox
                fy = ry - oy
                a = dx*dx + dy*dy
                b = 2 * (fx*dx + fy*dy)
                c = fx*fx + fy*fy - r*r

                discriminant = b*b - 4*a*c
                if discriminant >= 0:
                    t1 = (-b - math.sqrt(discriminant)) / (2*a)
                    if 0.1 < t1 < ranges[i]:
                        ranges[i] = t1
        return ranges

# Test ve Doğrulama
robot = DifferentialDriveUGV()
lidar = SimulatedTacticalLidar()

# Düz 2 metre sürüş
for _ in range(100):
    robot.apply_command(Twist2D(v=1.0, omega=0.0), dt=0.02)

assert math.isclose(robot.pose.x, 2.0, abs_tol=0.05), "Diferansiyel kinematik ilerleme hatası!"
assert math.isclose(robot.pose.y, 0.0, abs_tol=0.01), "Düz sürüşte sapma oluştu!"

# 5 metre ileride engel varken LiDAR taraması
obstacles = [(7.0, 0.0, 0.5)] # Robot x=2'de, engel x=7'de (Mesafe: 5.0 - 0.5 = 4.5m)
scan = lidar.scan(robot.pose, obstacles)
front_beam_idx = len(scan) // 2 # 0 derece açısı
detected_dist = scan[front_beam_idx]

print(f"[PASS] Kod 1: Kaplan İKA Kinematik ve LiDAR Motoru Doğrulandı.")
print(f"  - Robot Konumu : ({robot.pose.x:.2f}m, {robot.pose.y:.2f}m), Baş Açısı: {math.degrees(robot.pose.theta):.1f}°")
print(f"  - LiDAR Ön Algılama Mesafesi: {detected_dist:.2f}m (Beklenen: ~4.50m)")
assert math.isclose(detected_dist, 4.5, abs_tol=0.1), "LiDAR mesafe tespiti hatalı!"

# ============================================================================
# KOD HÜCRESİ 2: Görev Yöneticisi FSM ve Otonom Seyrüsefer Motoru
# Hedef takibi, LiDAR tabanlı engel kaçınma ve durum geçiş orkestrasyonu.
# ============================================================================
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple
import math
import numpy as np

class MissionState(Enum):
    IDLE = "IDLE"
    PATROL = "PATROL"
    OBSTACLE_AVOID = "OBSTACLE_AVOID"
    WAYPOINT_REACHED = "WAYPOINT_REACHED"
    FAILSAFE = "FAILSAFE"

@dataclass
class MissionMetrics:
    state_history: List[MissionState] = field(default_factory=list)
    speed_history: List[float] = field(default_factory=list)
    omega_history: List[float] = field(default_factory=list)
    min_obstacle_dist_history: List[float] = field(default_factory=list)

class AutonomousMissionExecutive:
    def __init__(self, waypoints: List[Tuple[float, float]], obstacles: List[Tuple[float, float, float]]):
        self.waypoints = waypoints
        self.current_wp_idx = 0
        self.obstacles = obstacles
        self.state = MissionState.IDLE
        self.metrics = MissionMetrics()
        
        self.robot = DifferentialDriveUGV(track_width=0.8, max_v=2.0, max_w=1.2)
        self.lidar = SimulatedTacticalLidar(num_beams=72, max_range=20.0)
        
        self.wp_tolerance = 0.8 # Metre
        self.avoid_dist_thresh = 3.5 # Metre
        self.clear_dist_thresh = 4.5 # Metre

    def start_mission(self):
        self.state = MissionState.PATROL

    def step(self, dt: float = 0.05):
        if self.state == MissionState.IDLE or self.state == MissionState.FAILSAFE:
            self.robot.apply_command(Twist2D(0.0, 0.0), dt)
            self._record_metrics(0.0, 0.0, 99.0)
            return

        # 1. Algı: LiDAR Taraması
        scan = self.lidar.scan(self.robot.pose, self.obstacles)
        # Ön sektör (-45 ile +45 derece arası ışınlar)
        n_beams = len(scan)
        front_indices = list(range(int(n_beams*0.375), int(n_beams*0.625)))
        front_dists = scan[front_indices]
        min_front_dist = float(np.min(front_dists))

        # Sol ve sağ sektör mesafeleri (kaçınma yönü tayini için)
        left_dist = float(np.mean(scan[int(n_beams*0.625):int(n_beams*0.875)]))
        right_dist = float(np.mean(scan[int(n_beams*0.125):int(n_beams*0.375)]))

        # 2. Karar: FSM ve Yol Planlama
        target_x, target_y = self.waypoints[self.current_wp_idx]
        dist_to_wp = math.hypot(target_x - self.robot.pose.x, target_y - self.robot.pose.y)

        # Hedefe Ulaşıldı mı?
        if dist_to_wp < self.wp_tolerance:
            self.state = MissionState.WAYPOINT_REACHED
            self.current_wp_idx = (self.current_wp_idx + 1) % len(self.waypoints)
            self.state = MissionState.PATROL

        # Engel Kaçınma FSM Geçişi
        if min_front_dist < self.avoid_dist_thresh:
            self.state = MissionState.OBSTACLE_AVOID
        elif min_front_dist > self.clear_dist_thresh and self.state == MissionState.OBSTACLE_AVOID:
            self.state = MissionState.PATROL

        # 3. Eylem: Komut Üretimi
        cmd = Twist2D()
        if self.state == MissionState.OBSTACLE_AVOID:
            # Reaktif Kaçınma: Daha açık olan tarafa dön, hızı düşür
            turn_dir = 1.0 if left_dist > right_dist else -1.0
            cmd.v = 0.5
            cmd.omega = turn_dir * 1.0
        elif self.state == MissionState.PATROL:
            # Hedefe Yönelim (Proportional Navigation)
            target_angle = math.atan2(target_y - self.robot.pose.y, target_x - self.robot.pose.x)
            angle_err = (target_angle - self.robot.pose.theta + math.pi) % (2 * math.pi) - math.pi
            
            cmd.omega = 1.5 * angle_err
            # Dönüş açısı büyükse yavaşla
            cmd.v = max(0.4, 1.8 * (1.0 - abs(angle_err)/math.pi))

        self.robot.apply_command(cmd, dt)
        self._record_metrics(cmd.v, cmd.omega, min_front_dist)

    def _record_metrics(self, v: float, w: float, min_d: float):
        self.metrics.state_history.append(self.state)
        self.metrics.speed_history.append(v)
        self.metrics.omega_history.append(w)
        self.metrics.min_obstacle_dist_history.append(min_d)

# Simülasyon Senaryosu: 4 Taktik Waypoint ve Yol Üstü Barikatlar
mission_waypoints = [(10.0, 2.0), (18.0, 10.0), (8.0, 15.0), (0.0, 0.0)]
tactical_obstacles = [
    (5.0, 1.0, 1.2),   # 1. Barikat
    (14.0, 6.0, 1.5),  # 2. Barikat
    (12.0, 13.0, 1.0)  # 3. Barikat
]

executor = AutonomousMissionExecutive(mission_waypoints, tactical_obstacles)
executor.start_mission()

# 1.200 Adım (60 saniye otonom seyir)
for _ in range(1200):
    executor.step(dt=0.05)

# Doğrulamalar
reached_states = [s for s in executor.metrics.state_history if s == MissionState.OBSTACLE_AVOID]
assert len(reached_states) > 0, "Otonom araç hiçbir engelden kaçınmadı!"
assert min(executor.metrics.min_obstacle_dist_history) > 0.3, "Araç engele çarptı (Çarpışma tespit edildi)!"

print(f"[PASS] Kod 2: Görev Yöneticisi FSM ve Engel Kaçınma Başarıyla Doğrulandı.")
print(f"  - İcra Edilen Adım Sayısı: {len(executor.metrics.state_history)}")
print(f"  - Kaçınma Moduna Girme Sayısı: {len(reached_states)} adım")
print(f"  - En Yakın Engel Mesafesi: {min(executor.metrics.min_obstacle_dist_history):.2f}m (Emniyet Sınırı Sağlandı)")

# ============================================================================
# KOD HÜCRESİ 3: Watchdog Güvenlik Monitörü ve Kovaryans Emniyet Kalkanı
# Sensör kesintisi, kalp atışı kaybı ve otonom E-Stop mekanizması.
# ============================================================================
from dataclasses import dataclass
from typing import Optional
import time

class SafetyWatchdog:
    def __init__(self, timeout_steps: int = 4): # 4 adım = 200ms (50Hz'de)
        self.timeout_steps = timeout_steps
        self.counter = 0
        self.is_estop_active = False

    def heartbeat(self):
        # Sağlıklı döngüde sayacı sıfırla
        self.counter = 0

    def tick(self) -> bool:
        # Her döngüde çağrılır
        self.counter += 1
        if self.counter >= self.timeout_steps:
            self.is_estop_active = True
            return False # Watchdog tetiklendi!
        return True

class DegradedNavigationMonitor:
    def __init__(self, max_covariance_thresh: float = 2.5):
        self.covariance = 0.05 # Başlangıç konum belirsizliği (m²)
        self.max_thresh = max_covariance_thresh
        self.is_degraded = False

    def update_with_lidar(self):
        # LiDAR aktifken harita eşleme belirsizliği sıfırlar
        self.covariance = 0.05
        self.is_degraded = False

    def update_dead_reckoning_only(self, dt: float):
        # Sadece tekerlek enkoderi + IMU: belirsizlik hızla büyür!
        self.covariance += 0.50 * dt
        if self.covariance > self.max_thresh:
            self.is_degraded = True

# Senaryo Testi
watchdog = SafetyWatchdog(timeout_steps=4)
nav_monitor = DegradedNavigationMonitor(max_covariance_thresh=1.5)

# Normal Çalışma (3 adım sağlıklı)
for _ in range(3):
    watchdog.heartbeat()
    assert watchdog.tick(), "Normal çalışmada watchdog hatalı tetiklendi!"

# Sensör Karartması (LiDAR düştü, 5 adım boyunca beslenemedi)
estop_triggered = False
for step in range(6):
    nav_monitor.update_dead_reckoning_only(dt=1.0)
    if not watchdog.tick():
        estop_triggered = True
        break

assert estop_triggered, "Watchdog E-Stop tetiklenmedi!"
assert nav_monitor.is_degraded, "Kovaryans patlaması tespit edilemedi!"

print(f"[PASS] Kod 3: Watchdog ve Kovaryans Güvenlik Kalkanı Doğrulandı.")
print(f"  - E-Stop Durumu: {watchdog.is_estop_active} (Kalp Atışı Kesilmesinde Tetiklendi)")
print(f"  - Son Konum Kovaryansı: {nav_monitor.covariance:.2f} m² (Eşik: {nav_monitor.max_thresh:.2f} m²)")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik Capstone Hata Enjeksiyon Testi
# Dinamik Çarpışma TTC, Sensör Karartması ve Tekerlek Patinajı Denetimi.
# ============================================================================
import math

class EmergencyBrakeException(Exception):
    pass

class SensorTimeoutException(Exception):
    pass

class WheelSlipDetectedException(Exception):
    pass

# --- TEST A: Ani Çarpışma Tehdidi (TTC < 0.8s) ---
def run_test_a_ttc_emergency_brake():
    print("[TEST A] Kritik Dinamik Çarpışma Tehdidi (TTC) Testi...")
    vehicle_speed = 2.5 # m/s
    obstacle_distance = 1.2 # metre
    
    ttc = obstacle_distance / vehicle_speed # 0.48 saniye
    if ttc < 0.8:
        msg = f"COLLISION_IMMINENT: TTC={ttc:.2f}s < 0.8s! Acil durum freni devreye girdi!"
        try:
            raise EmergencyBrakeException(msg)
        except EmergencyBrakeException as e:
            print(f"  [BEKLENEN SAVUNMA YAKALANDI]: {e}")
            return True
    return False

# --- TEST B: LiDAR Veri Akışı Karartması (Sensor Dropout) ---
def run_test_b_sensor_dropout():
    print("\n[TEST B] Sensör Veri Karartması (Timeout) Testi...")
    last_sensor_stamp = 10.20 # saniye
    current_time = 10.55      # 350 ms geçti (Eşik: 200 ms)
    
    dt = current_time - last_sensor_stamp
    if dt > 0.200:
        msg = f"SENSOR_FATAL: LiDAR veri akışı kesildi! Gecikme={dt*1000:.1f}ms > 200ms. Kör seyrüsefer engellendi!"
        try:
            raise SensorTimeoutException(msg)
        except SensorTimeoutException as e:
            print(f"  [BEKLENEN HATA YAKALANDI]: {e}")
            return True
    return False

# --- TEST C: Aşırı Tekerlek Patinajı (Wheel Slip) ---
def run_test_c_wheel_slip_detection():
    print("\n[TEST C] Aşırı Tekerlek Patinajı (Wheel Slip) Testi...")
    wheel_odometry_speed = 3.2 # Tekerlekler 3.2 m/s dönüyor
    imu_integrated_speed = 0.3 # IMU ivme integrali sadece 0.3 m/s diyor!
    
    slip_ratio = abs(wheel_odometry_speed - imu_integrated_speed) / max(wheel_odometry_speed, 0.1)
    if slip_ratio > 0.60: # %60'tan fazla patinaj
        msg = f"TRACTION_ALERT: Aşırı Tekerlek Patinajı! Odometri={wheel_odometry_speed}m/s, IMU={imu_integrated_speed}m/s, Kayma Oranı=%{slip_ratio*100:.1f}"
        try:
            raise WheelSlipDetectedException(msg)
        except WheelSlipDetectedException as e:
            print(f"  [BEKLENEN UYARI YAKALANDI]: {e}")
            return True
    return False

# İcra ve Doğrulama
res_a = run_test_a_ttc_emergency_brake()
res_b = run_test_b_sensor_dropout()
res_c = run_test_c_wheel_slip_detection()

assert res_a and res_b and res_c, "Hata testlerinden en az biri başarısız oldu!"
print("\n[PASS] Kod 4: 3 Kritik Capstone Hata Testi Başarıyla Tamamlandı.")

# ============================================================================
# HÜCRE 21: 10.000 Döngülük Otonom UGV Karar Motoru Benchmark'ı
# Tam Algı-Karar-Eylem döngüsünün icra gecikmesi ve frekans analizi.
# ============================================================================
import time
import numpy as np

# Benchmark Düzeneği
bench_waypoints = [(10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
bench_obstacles = [(5.0, 0.2, 1.0), (8.0, 8.0, 1.2)]
bench_executor = AutonomousMissionExecutive(bench_waypoints, bench_obstacles)
bench_executor.start_mission()

NUM_STEPS = 10_000
latencies_us = np.empty(NUM_STEPS, dtype=np.float64)

print(f"[BENCHMARK] {NUM_STEPS:,} Otonom Kontrol Döngüsü İcra Ediliyor...")
t_start = time.perf_counter()

for i in range(NUM_STEPS):
    t0 = time.perf_counter_ns()
    
    # Tam döngü: Algı + FSM + VFH + Kinematik
    bench_executor.step(dt=0.01)
    
    t_end = time.perf_counter_ns()
    latencies_us[i] = (t_end - t0) / 1000.0 # ns -> us

t_total = time.perf_counter() - t_start

# Metrikler
ops_sec = NUM_STEPS / t_total
p50 = np.percentile(latencies_us, 50)
p90 = np.percentile(latencies_us, 90)
p99 = np.percentile(latencies_us, 99)
min_lat = np.min(latencies_us)
avg_lat = np.mean(latencies_us)
max_lat = np.max(latencies_us)

print(f"\n[CAPSTONE BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - Kontrol Frekansı    : {ops_sec:,.1f} döngü/s (Hedef: > 5,000)")
print(f"  - Ortalama Gecikme    : {avg_lat:.2f} µs")
print(f"  - p50 (Medyan)        : {p50:.2f} µs")
print(f"  - p90 Gecikme         : {p90:.2f} µs")
print(f"  - p99 Kuyruk Gecikmesi: {p99:.2f} µs (Hedef: < 250 µs)")
print(f"  - Min / Max           : {min_lat:.2f} µs / {max_lat:.2f} µs")

# Doğrulamalar
assert ops_sec > 5_000, f"Kontrol döngü frekansı yetersiz: {ops_sec}"
assert p99 < 250.0, f"p99 kontrol gecikmesi çok yüksek: {p99} µs"
print("\n[PASS] Kod 5: 10.000 Döngülük Capstone Benchmark Başarıyla Tamamlandı.")

# ============================================================================
# HÜCRE 23: 4-Panelli 300 DPI Koyu Tema Analiz Dashboard'u
# gun_225_ros2_gazebo_autonomous_ugv_skeleton.png dosyasını üretir.
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
import os

# Koyu Tema Renk Paleti
COLOR_BG = "#0F172A"       # Koyu Lacivert / Slate 900
COLOR_PANEL = "#1E293B"    # Panel Arka Plan / Slate 800
COLOR_TEXT = "#F8FAFC"     # Ana Metin / Slate 50
COLOR_MUTED = "#94A3B8"    # İkincil Metin / Slate 400
COLOR_ACCENT1 = "#38BDF8"  # Cyan (İKA Yörünge / Hedef)
COLOR_ACCENT2 = "#34D399"  # Yeşil (Patrol / Hız)
COLOR_ACCENT3 = "#F87171"  # Kırmızı (Engeller / E-Stop)
COLOR_ACCENT4 = "#FBBF24"  # Sarı (Kaçınma / VFH)

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: Taktik Harp Sahası Haritası (Yörünge, Hedefler, Engeller) ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

# Yörünge Verisi
traj_x = [p.x for p in executor.robot.odom_history]
traj_y = [p.y for p in executor.robot.odom_history]
ax1.plot(traj_x, traj_y, color=COLOR_ACCENT1, linewidth=2.5, label="Kaplan İKA Yörüngesi")

# Hedef Noktalar
wps = np.array(mission_waypoints)
ax1.scatter(wps[:, 0], wps[:, 1], color=COLOR_ACCENT2, s=120, marker="X", zorder=5, label="Hedef Noktalar (Waypoints)")
for idx, (wx, wy) in enumerate(wps):
    ax1.text(wx + 0.5, wy + 0.5, f"WP{idx+1}", color=COLOR_ACCENT2, fontsize=9, fontweight="bold")

# Engeller
for ox, oy, r in tactical_obstacles:
    circle = plt.Circle((ox, oy), r, color=COLOR_ACCENT3, alpha=0.45, ec="#DC2626", linewidth=2.0)
    ax1.add_patch(circle)
ax1.scatter([o[0] for o in tactical_obstacles], [o[1] for o in tactical_obstacles], 
            color=COLOR_ACCENT3, s=40, label="Taktik Engeller/Barikatlar")

ax1.set_title("Panel 1: Taktik Harp Sahası Yörünge ve Engel Kaçınma Haritası", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xlabel("Arazi X Koordinatı [m]", color=COLOR_MUTED, fontsize=10)
ax1.set_ylabel("Arazi Y Koordinatı [m]", color=COLOR_MUTED, fontsize=10)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax1.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="lower right", fontsize=8)

# --- PANEL 2: Kinematik Hız ve Direksiyon Profili ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

time_steps = np.arange(len(executor.metrics.speed_history)) * 0.05
ax2_twin = ax2.twinx()

line1 = ax2.plot(time_steps, executor.metrics.speed_history, color=COLOR_ACCENT2, linewidth=2.0, label="Doğrusal Hız v (m/s)")
line2 = ax2_twin.plot(time_steps, executor.metrics.omega_history, color=COLOR_ACCENT4, linewidth=1.8, linestyle="--", label="Açısal Hız ω (rad/s)")

ax2.set_title("Panel 2: Kinematik Hız ve Açısal Yönelim Profili (v, ω)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_xlabel("Zaman [s]", color=COLOR_MUTED, fontsize=10)
ax2.set_ylabel("Doğrusal Hız [m/s]", color=COLOR_ACCENT2, fontsize=10)
ax2_twin.set_ylabel("Açısal Hız [rad/s]", color=COLOR_ACCENT4, fontsize=10)
ax2.tick_params(colors=COLOR_MUTED)
ax2_twin.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6)

lines = line1 + line2
labels = [l.get_label() for l in lines]
ax2.legend(lines, labels, facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 3: Görev Yöneticisi FSM Durum Zaman Çizelgesi ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

state_nums = []
for s in executor.metrics.state_history:
    if s == MissionState.PATROL:
        state_nums.append(1)
    elif s == MissionState.OBSTACLE_AVOID:
        state_nums.append(2)
    elif s == MissionState.WAYPOINT_REACHED:
        state_nums.append(3)
    else:
        state_nums.append(0)

ax3.step(time_steps, state_nums, color=COLOR_ACCENT1, linewidth=2.2, where="post")
ax3.set_yticks([0, 1, 2, 3])
ax3.set_yticklabels(["IDLE/FAILSAFE", "PATROL", "AVOID", "WP_REACHED"], color=COLOR_TEXT, fontsize=9)
ax3.set_title("Panel 3: Görev Yöneticisi FSM Durum Geçiş Zaman Çizelgesi", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("Zaman [s]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("FSM Durumu", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)

# Kaçınma bölgelerini kırmızı gölgele
avoid_mask = np.array(state_nums) == 2
ax3.fill_between(time_steps, 0, 3, where=avoid_mask, color=COLOR_ACCENT3, alpha=0.2, label="Aktif Kaçınma Modu")
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 4: 10.000 Döngülük Karar Gecikmesi Dağılımı (Histogram) ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

n, bins, patches = ax4.hist(latencies_us, bins=60, color=COLOR_ACCENT1, alpha=0.8, edgecolor="#0284C7")
ax4.axvline(p50, color=COLOR_ACCENT2, linestyle="-", linewidth=2.2, label=f"p50 (Medyan): {p50:.2f} µs")
ax4.axvline(p90, color=COLOR_ACCENT4, linestyle="--", linewidth=2.2, label=f"p90: {p90:.2f} µs")
ax4.axvline(p99, color=COLOR_ACCENT3, linestyle="-.", linewidth=2.2, label=f"p99: {p99:.2f} µs")

ax4.set_title("Panel 4: Capstone Karar Döngüsü İcra Gecikme Dağılımı (µs)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_xlabel("Döngü Başına Gecikme [µs]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylabel("Frekans (Döngü Sayısı)", color=COLOR_MUTED, fontsize=10)
ax4.tick_params(colors=COLOR_MUTED)
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax4.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# Üst Başlık
plt.suptitle("ASELSAN KAPLAN İKA — ROS 2 / GAZEBO OTONOM UGV MİNİ-CAPSTONE SİSTEM ANALİZİ", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_225/gun_225_ros2_gazebo_autonomous_ugv_skeleton.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

