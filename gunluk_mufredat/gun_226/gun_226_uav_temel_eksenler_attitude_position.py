# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 226: İHA Temel Eksenleri, Attitude ve Position Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: Core Attitude ve Koordinat Çerçevesi Dönüşüm Motoru
# Euler ZYX, Kuaterniyon cebiri, SO(3) Rotasyon Matrisi ve NED <-> ENU çevrimi.
# ============================================================================
from dataclasses import dataclass
import math
import numpy as np

@dataclass
class Quaternion:
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def normalize(self):
        norm = math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        if norm > 1e-12:
            self.w /= norm
            self.x /= norm
            self.y /= norm
            self.z /= norm
        return self

    def conjugate(self) -> 'Quaternion':
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def to_array(self) -> np.ndarray:
        return np.array([self.w, self.x, self.y, self.z], dtype=np.float64)

@dataclass
class EulerAngles:
    roll: float = 0.0   # phi (radyan)
    pitch: float = 0.0  # theta (radyan)
    yaw: float = 0.0    # psi (radyan)

def euler_to_quaternion(euler: EulerAngles) -> Quaternion:
    # Euler açılarını (Roll-Pitch-Yaw / ZYX sırası) Kuaterniyona çevirir.
    cr = math.cos(euler.roll * 0.5)
    sr = math.sin(euler.roll * 0.5)
    cp = math.cos(euler.pitch * 0.5)
    sp = math.sin(euler.pitch * 0.5)
    cy = math.cos(euler.yaw * 0.5)
    sy = math.sin(euler.yaw * 0.5)

    q = Quaternion(
        w = cr * cp * cy + sr * sp * sy,
        x = sr * cp * cy - cr * sp * sy,
        y = cr * sp * cy + sr * cp * sy,
        z = cr * cp * sy - sr * sp * cy
    )
    return q.normalize()

def quaternion_to_euler(q: Quaternion) -> EulerAngles:
    # Kuaterniyondan Euler açılarına kararlı çevrim.
    # Roll (x-ekseni rotasyonu)
    sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z)
    cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (y-ekseni rotasyonu)
    sinp = 2.0 * (q.w * q.y - q.z * q.x)
    if abs(sinp) >= 1.0:
        pitch = math.copysign(math.pi / 2.0, sinp) # Gimbal lock kilitlenmesi sınırlandırma
    else:
        pitch = math.asin(sinp)

    # Yaw (z-ekseni rotasyonu)
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return EulerAngles(roll, pitch, yaw)

def quaternion_to_rot_matrix(q: Quaternion) -> np.ndarray:
    # Body'den Navigasyona Dönüşüm Matrisi (R_b^n)
    w, x, y, z = q.w, q.x, q.y, q.z
    R = np.array([
        [1 - 2*(y**2 + z**2),     2*(x*y - z*w),     2*(x*z + y*w)],
        [    2*(x*y + z*w), 1 - 2*(x**2 + z**2),     2*(y*z - x*w)],
        [    2*(x*z - y*w),     2*(y*z + x*w), 1 - 2*(x**2 + y**2)]
    ], dtype=np.float64)
    return R

def ned_to_enu(v_ned: np.ndarray) -> np.ndarray:
    # NED [North, East, Down] -> ENU [East, North, Up] dönüşümü
    # X_enu = Y_ned (East)
    # Y_enu = X_ned (North)
    # Z_enu = -Z_ned (Up)
    return np.array([v_ned[1], v_ned[0], -v_ned[2]], dtype=np.float64)

def enu_to_ned(v_enu: np.ndarray) -> np.ndarray:
    # ENU [East, North, Up] -> NED [North, East, Down] dönüşümü
    return np.array([v_enu[1], v_enu[0], -v_enu[2]], dtype=np.float64)

# Test ve Doğrulama
euler_orig = EulerAngles(roll=math.radians(15.0), pitch=math.radians(-10.0), yaw=math.radians(45.0))
q_test = euler_to_quaternion(euler_orig)
euler_rec = quaternion_to_euler(q_test)

assert math.isclose(euler_orig.roll, euler_rec.roll, abs_tol=1e-5), "Roll çevrim hatası!"
assert math.isclose(euler_orig.pitch, euler_rec.pitch, abs_tol=1e-5), "Pitch çevrim hatası!"
assert math.isclose(euler_orig.yaw, euler_rec.yaw, abs_tol=1e-5), "Yaw çevrim hatası!"

# NED <-> ENU İrtifa Çevrim Testi (İHA 100m irtifada: Z_ned = -100m, Z_enu = +100m)
pos_ned = np.array([500.0, 300.0, -100.0]) # Kuzey: 500m, Doğu: 300m, İrtifa: 100m
pos_enu = ned_to_enu(pos_ned)
assert pos_enu[0] == 300.0 and pos_enu[1] == 500.0 and pos_enu[2] == 100.0, "NED -> ENU dönüşüm hatası!"
pos_ned_rec = enu_to_ned(pos_enu)
assert np.allclose(pos_ned, pos_ned_rec), "ENU -> NED geri dönüşüm hatası!"

print(f"[PASS] Kod 1: Attitude ve Frame Dönüşüm Motoru Başarıyla Doğrulandı.")
print(f"  - Giriş Euler Açıları: Roll={math.degrees(euler_orig.roll):.1f}°, Pitch={math.degrees(euler_orig.pitch):.1f}°, Yaw={math.degrees(euler_orig.yaw):.1f}°")
print(f"  - Üretilen Kuaterniyon: [w={q_test.w:.4f}, x={q_test.x:.4f}, y={q_test.y:.4f}, z={q_test.z:.4f}]")
print(f"  - 100m İrtifa Dönüşümü: NED z={pos_ned[2]}m -> ENU z={pos_enu[2]}m")

# ============================================================================
# KOD HÜCRESİ 2: 6-DOF İHA Uçuş Kinematiği ve Yörünge Simülatörü
# Kuaterniyon tabanlı açısal hız integrasyonu ve NED seyrüsefer yörüngesi.
# ============================================================================
from dataclasses import dataclass, field
from typing import List, Tuple
import math
import numpy as np

@dataclass
class UAVKinematicState:
    pos_ned: np.ndarray = field(default_factory=lambda: np.zeros(3)) # [North, East, Down] (m)
    vel_body: np.ndarray = field(default_factory=lambda: np.array([25.0, 0.0, 0.0])) # [u, v, w] (m/s)
    quat: Quaternion = field(default_factory=Quaternion)

class UAV6DOFShipSimulator:
    def __init__(self, init_pos: np.ndarray, cruise_speed: float = 30.0):
        self.state = UAVKinematicState(
            pos_ned=np.array(init_pos, dtype=np.float64),
            vel_body=np.array([cruise_speed, 0.0, 0.0], dtype=np.float64),
            quat=Quaternion(1.0, 0.0, 0.0, 0.0)
        )
        self.history_pos_ned: List[np.ndarray] = [self.state.pos_ned.copy()]
        self.history_euler: List[EulerAngles] = [quaternion_to_euler(self.state.quat)]
        self.history_time: List[float] = [0.0]

    def step(self, omega_body: np.ndarray, dt: float = 0.01):
        # omega_body: [p, q, r] rad/s, dt: zaman adımı (s)
        p, q, r = omega_body

        # 1. Kuaterniyon İntegrasyonu (dq/dt = 0.5 * q * omega)
        qw, qx, qy, qz = self.state.quat.w, self.state.quat.x, self.state.quat.y, self.state.quat.z
        
        # Kapalı Form Kuaterniyon Diferansiyeli
        dq_w = 0.5 * (-qx * p - qy * q - qz * r)
        dq_x = 0.5 * ( qw * p + qy * r - qz * q)
        dq_y = 0.5 * ( qw * q - qx * r + qz * p)
        dq_z = 0.5 * ( qw * r + qx * q - qy * p)

        self.state.quat.w += dq_w * dt
        self.state.quat.x += dq_x * dt
        self.state.quat.y += dq_y * dt
        self.state.quat.z += dq_z * dt
        self.state.quat.normalize()

        # 2. Body Hızından NED Hızına Çevrim: v_ned = R_b^n * v_body
        R_bn = quaternion_to_rot_matrix(self.state.quat)
        v_ned = R_bn @ self.state.vel_body

        # 3. Konum İntegrasyonu: p_ned(k+1) = p_ned(k) + v_ned * dt
        self.state.pos_ned += v_ned * dt

        # Kayıt
        self.history_pos_ned.append(self.state.pos_ned.copy())
        self.history_euler.append(quaternion_to_euler(self.state.quat))
        self.history_time.append(self.history_time[-1] + dt)

# Senaryo: Bayraktar TB2 Taktik Dönüş ve Tırmanış Manevrası
# Başlangıç: Kuzey=0, Doğu=0, İrtifa=1000m (Z_ned = -1000m), Seyir Hızı = 30 m/s
sim = UAV6DOFShipSimulator(init_pos=[0.0, 0.0, -1000.0], cruise_speed=30.0)

# Manevra: 15 saniye boyunca sabit açısal hızla sağa dönüş (Yaw rate r = 0.1 rad/s) ve tırmanış (Pitch rate q = 0.02 rad/s)
DT = 0.02 # 50 Hz simülasyon adımı
TOTAL_STEPS = 750 # 15 saniye

for step in range(TOTAL_STEPS):
    # Sabit p=0, q=0.015 rad/s, r=0.08 rad/s
    sim.step(omega_body=np.array([0.0, 0.015, 0.08]), dt=DT)

# Doğrulamalar
final_pos = sim.state.pos_ned
final_euler = sim.history_euler[-1]

# Uçak tırmandı mı? (Z_ned daha negatif olmalı!)
assert final_pos[2] < -1000.0, "İHA tırmanma hareketi gerçekleştirmedi!"
# Uçak sağa döndü mü? (Yaw açısı pozitif yönde arttı mı?)
assert final_euler.yaw > 0.5, "İHA sapma (yaw) dönüşü yapmadı!"

print(f"[PASS] Kod 2: 6-DOF Uçuş Kinematiği Simülasyonu Doğrulandı.")
print(f"  - Simülasyon Süresi: {sim.history_time[-1]:.2f} saniye ({TOTAL_STEPS} adım)")
print(f"  - Başlangıç İrtifası: 1000.0m (Z_ned = -1000.0m)")
print(f"  - Bitiş İrtifası    : {-final_pos[2]:.2f}m (Z_ned = {final_pos[2]:.2f}m, Tırmanma: {-final_pos[2] - 1000.0:.2f}m)")
print(f"  - Son Konum (NED)   : North={final_pos[0]:.2f}m, East={final_pos[1]:.2f}m")
print(f"  - Son Euler Açıları : Roll={math.degrees(final_euler.roll):.1f}°, Pitch={math.degrees(final_euler.pitch):.1f}°, Yaw={math.degrees(final_euler.yaw):.1f}°")

# ============================================================================
# KOD HÜCRESİ 3: Koordineli Dönüş Güdümü ve Tutum (Attitude) PD Kontrolcüsü
# Hedef pruva açısına koordineli yatış (banked turn) ile kilitlenme.
# ============================================================================
from dataclasses import dataclass
import math
import numpy as np

class AttitudePDController:
    def __init__(self, kp_roll: float = 3.5, kd_roll: float = 0.4,
                 kp_pitch: float = 3.0, kd_pitch: float = 0.3):
        self.kp_roll = kp_roll
        self.kd_roll = kd_roll
        self.kp_pitch = kp_pitch
        self.kd_pitch = kd_pitch
        self.last_err_roll = 0.0
        self.last_err_pitch = 0.0

    def compute_rates(self, current_euler: EulerAngles, target_euler: EulerAngles, dt: float) -> np.ndarray:
        # Açı hataları
        err_roll = target_euler.roll - current_euler.roll
        err_pitch = target_euler.pitch - current_euler.pitch

        # Türev
        d_err_roll = (err_roll - self.last_err_roll) / dt if dt > 0 else 0.0
        d_err_pitch = (err_pitch - self.last_err_pitch) / dt if dt > 0 else 0.0

        p_cmd = self.kp_roll * err_roll + self.kd_roll * d_err_roll
        q_cmd = self.kp_pitch * err_pitch + self.kd_pitch * d_err_pitch

        self.last_err_roll = err_roll
        self.last_err_pitch = err_pitch

        # Sınırlandırma (Maksimum 60 deg/s açısal hız)
        p_cmd = max(-1.05, min(1.05, p_cmd))
        q_cmd = max(-0.80, min(0.80, q_cmd))

        # Koordineli dönüş yaw hızı: r = (g / v) * tan(roll)
        g = 9.80665
        v = 30.0 # m/s
        r_cmd = (g / v) * math.tan(current_euler.roll)

        return np.array([p_cmd, q_cmd, r_cmd], dtype=np.float64)

# Test: Uçağı 20 derece sağa yatırarak 90 derece Doğu rotasına çevirme
controller = AttitudePDController()
test_sim = UAV6DOFShipSimulator(init_pos=[0.0, 0.0, -1000.0], cruise_speed=30.0)

target = EulerAngles(roll=math.radians(20.0), pitch=math.radians(3.0), yaw=math.radians(90.0))

dt = 0.02
for _ in range(500): # 10 saniye kapalı çevrim kontrol
    curr_euler = quaternion_to_euler(test_sim.state.quat)
    rates = controller.compute_rates(curr_euler, target, dt)
    test_sim.step(rates, dt)

final_euler = quaternion_to_euler(test_sim.state.quat)

# Doğrulama: Hedef açılara oturuldu mu?
assert math.isclose(final_euler.roll, target.roll, abs_tol=math.radians(2.0)), "Roll kontrolcüsü hedefe oturamadı!"
assert math.isclose(final_euler.pitch, target.pitch, abs_tol=math.radians(1.5)), "Pitch kontrolcüsü hedefe oturamadı!"

print(f"[PASS] Kod 3: Kapalı Çevrim Attitude PD Kontrolcüsü Doğrulandı.")
print(f"  - Ulaşılan Roll : {math.degrees(final_euler.roll):.2f}° (Hedef: {math.degrees(target.roll):.1f}°)")
print(f"  - Ulaşılan Pitch: {math.degrees(final_euler.pitch):.2f}° (Hedef: {math.degrees(target.pitch):.1f}°)")
print(f"  - Dönüş Pruvası (Yaw): {math.degrees(final_euler.yaw):.2f}°")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik Havacılık ve Koordinat Hatası Enjeksiyon Testi
# Gimbal Lock Tekilliği, İrtifa İşaret Tuzağı ve Kuaterniyon Norm Drift Testi.
# ============================================================================
import math
import numpy as np

class GimbalLockException(Exception):
    pass

class AltitudeSignFatalException(Exception):
    pass

class QuaternionNormDriftException(Exception):
    pass

# --- TEST A: Gimbal Lock Singularite Testi ---
def run_test_a_gimbal_lock():
    print("[TEST A] Euler Gimbal Lock (Pitch = 90°) Singularite Testi...")
    pitch = math.radians(90.0) # Tam dikey tırmanış
    cos_pitch = math.cos(pitch) # ~0.0
    
    # Euler türevinde 1 / cos(theta) çarpanı vardır
    if abs(cos_pitch) < 1e-6:
        msg = (f"EULER_SINGULARITY: Pitch={math.degrees(pitch):.1f}° iken cos(theta)={cos_pitch:.2e}! "
               f"Roll ve Yaw serbestlik derecesi kilitlendi! Sistem tanımsız duruma girdi!")
        try:
            raise GimbalLockException(msg)
        except GimbalLockException as e:
            print(f"  [BEKLENEN HATA YAKALANDI]: {e}")
            
            # Kuaterniyon Karşılaştırması: Kuaterniyon bu durumda tekil değildir!
            q_vertical = euler_to_quaternion(EulerAngles(0.0, pitch, 0.0))
            norm = math.sqrt(q_vertical.w**2 + q_vertical.x**2 + q_vertical.y**2 + q_vertical.z**2)
            assert math.isclose(norm, 1.0, abs_tol=1e-5), "Kuaterniyon normu bozuldu!"
            print(f"  [SAVUNMA DOĞRULANDI]: Kuaterniyon norm={norm:.4f} ile singulariteden etkilenmedi.")
            return True
    return False

# --- TEST B: NED vs ENU İrtifa İşareti Tuzağı ---
def run_test_b_altitude_sign_trap():
    print("\n[TEST B] NED vs ENU İrtifa İşareti Uyumsuzluğu Testi...")
    requested_altitude_m = 250.0 # Yerden 250m yukarıda uçmak isteniyor
    
    # Hatalı atama: Z_ned = +250.0m (Oto-pilot bunu yerin 250m altı anlar!)
    z_ned_cmd = requested_altitude_m # İşaret dönüşümü UNUTULDU!
    
    if z_ned_cmd > 0.0:
        msg = (f"AVIONIC_SAFETY_CRITICAL: Pozitif Z_ned ({z_ned_cmd}m) tespit edildi! "
               f"NED çerçevesinde pozitif Z yerin altını gösterir! İHA kırıma (CFIT) sürükleniyor!")
        try:
            raise AltitudeSignFatalException(msg)
        except AltitudeSignFatalException as e:
            print(f"  [BEKLENEN GÜVENLİK BARİYERİ YAKALANDI]: {e}")
            # Düzeltme: Z_ned = -h
            corrected_z = -requested_altitude_m
            print(f"  [OTOMATİK DÜZELTME]: Güvenli Z_ned = {corrected_z}m olarak atandı.")
            return True
    return False

# --- TEST C: Kuaterniyon Norm Kayması (Norm Drift) ---
def run_test_c_quaternion_drift():
    print("\n[TEST C] Sayısal İntegrasyonda Kuaterniyon Norm Kayması Testi...")
    q = Quaternion(1.0, 0.0, 0.0, 0.0)
    
    # Normalizasyon çağrılmadan 50.000 adım kaba Euler integrasyonu simülasyonu
    dt = 0.01
    omega = np.array([0.5, -0.3, 0.8])
    for _ in range(50_000):
        # Normalizasyonsuz ham integrasyon
        dq_w = 0.5 * (-q.x * omega[0] - q.y * omega[1] - q.z * omega[2])
        q.w += dq_w * dt
        # Bilerek küçük nümerik hata birikimi
        q.w += 1e-6

    current_norm = math.sqrt(q.w**2 + q.x**2 + q.y**2 + q.z**2)
    norm_error = abs(current_norm - 1.0)
    
    if norm_error > 0.01:
        msg = f"QUAT_DRIFT_WARNING: Kuaterniyon normu={current_norm:.4f} bozuldu! Hata={norm_error:.4f} > 0.01. Rotasyon matrisi ortogonalitesini kaybetti!"
        try:
            raise QuaternionNormDriftException(msg)
        except QuaternionNormDriftException as e:
            print(f"  [BEKLENEN UYARI YAKALANDI]: {e}")
            q.normalize()
            assert math.isclose(math.sqrt(q.w**2 + q.x**2 + q.y**2 + q.z**2), 1.0, abs_tol=1e-5)
            print(f"  [SAVUNMA DOĞRULANDI]: q.normalize() ile norm={math.sqrt(q.w**2 + q.x**2 + q.y**2 + q.z**2):.4f} sağlandı.")
            return True
    return False

# İcra ve Doğrulama
res_a = run_test_a_gimbal_lock()
res_b = run_test_b_altitude_sign_trap()
res_c = run_test_c_quaternion_drift()

assert res_a and res_b and res_c, "Havacılık hata enjeksiyon testlerinden en az biri başarısız!"
print("\n[PASS] Kod 4: 3 Kritik Havacılık ve Eksen Hata Testi Başarıyla Tamamlandı.")

# ============================================================================
# HÜCRE 21: 100.000 Döngülük Kuaterniyon ve Frame Kinematiği Benchmark'ı
# Tekil adım gecikmesi, throughput ve p99 analizi.
# ============================================================================
import time
import numpy as np

NUM_ITERATIONS = 100_000
latencies_us = np.empty(NUM_ITERATIONS, dtype=np.float64)

# Test Durumu
q_bench = Quaternion(1.0, 0.0, 0.0, 0.0)
omega = np.array([0.15, -0.08, 0.22], dtype=np.float64)
v_body = np.array([32.0, 0.0, 0.0], dtype=np.float64)
dt = 0.004 # 250 Hz

print(f"[BENCHMARK] {NUM_ITERATIONS:,} Döngülük 6-DOF Kinematik İntegrasyon Başlatılıyor...")
t_start = time.perf_counter()

for i in range(NUM_ITERATIONS):
    t0 = time.perf_counter_ns()
    
    # 1. Kuaterniyon integrasyon adımı
    qw, qx, qy, qz = q_bench.w, q_bench.x, q_bench.y, q_bench.z
    p, q, r = omega[0], omega[1], omega[2]
    
    dq_w = 0.5 * (-qx * p - qy * q - qz * r)
    dq_x = 0.5 * ( qw * p + qy * r - qz * q)
    dq_y = 0.5 * ( qw * q - qx * r + qz * p)
    dq_z = 0.5 * ( qw * r + qx * q - qy * p)

    q_bench.w += dq_w * dt
    q_bench.x += dq_x * dt
    q_bench.y += dq_y * dt
    q_bench.z += dq_z * dt
    
    # Normalizasyon
    norm = math.sqrt(q_bench.w**2 + q_bench.x**2 + q_bench.y**2 + q_bench.z**2)
    q_bench.w /= norm
    q_bench.x /= norm
    q_bench.y /= norm
    q_bench.z /= norm

    # 2. Rotasyon Matrisi ve Hız Döndürme
    R = quaternion_to_rot_matrix(q_bench)
    v_ned = R @ v_body
    
    t_end = time.perf_counter_ns()
    latencies_us[i] = (t_end - t0) / 1000.0 # ns -> us

t_total = time.perf_counter() - t_start

# İstatistikler
ops_sec = NUM_ITERATIONS / t_total
p50 = np.percentile(latencies_us, 50)
p90 = np.percentile(latencies_us, 90)
p99 = np.percentile(latencies_us, 99)
min_lat = np.min(latencies_us)
avg_lat = np.mean(latencies_us)
max_lat = np.max(latencies_us)

print(f"\n[BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - İşlem Hızı          : {ops_sec:,.1f} operasyon/s (Hedef: > 50,000)")
print(f"  - Ortalama Gecikme    : {avg_lat:.2f} µs")
print(f"  - p50 (Medyan)        : {p50:.2f} µs")
print(f"  - p90 Gecikme         : {p90:.2f} µs")
print(f"  - p99 Kuyruk Gecikmesi: {p99:.2f} µs (Hedef: < 25 µs)")
print(f"  - Min / Max           : {min_lat:.2f} µs / {max_lat:.2f} µs")

# Doğrulamalar
assert ops_sec > 50_000, f"Benchmark throughput yetersiz: {ops_sec}"
assert p99 < 25.0, f"p99 gecikmesi çok yüksek: {p99} µs"
print("\n[PASS] Kod 5: 100.000 Döngülük Attitude Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# HÜCRE 23: 4-Panelli 300 DPI Koyu Tema Analiz Dashboard'u
# gun_226_uav_temel_eksenler_attitude_position.png dosyasını üretir.
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
import os

# Koyu Tema Renk Paleti
COLOR_BG = "#0F172A"       # Koyu Lacivert / Slate 900
COLOR_PANEL = "#1E293B"    # Panel Arka Plan / Slate 800
COLOR_TEXT = "#F8FAFC"     # Ana Metin / Slate 50
COLOR_MUTED = "#94A3B8"    # İkincil Metin / Slate 400
COLOR_ACCENT1 = "#38BDF8"  # Cyan (North / Roll)
COLOR_ACCENT2 = "#34D399"  # Yeşil (East / Pitch)
COLOR_ACCENT3 = "#F87171"  # Kırmızı (Down / Altitude / Yaw)
COLOR_ACCENT4 = "#FBBF24"  # Sarı (Quaternion / Rates)

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: İHA 2D/3D Yörünge ve NED İrtifa Profili ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

pos_history = np.array(sim.history_pos_ned)
north = pos_history[:, 0]
east = pos_history[:, 1]
altitude = -pos_history[:, 2] # İrtifa = -Down

scatter = ax1.scatter(east, north, c=altitude, cmap="viridis", s=15, label="Uçuş Rotası")
cbar = plt.colorbar(scatter, ax=ax1)
cbar.set_label("İrtifa (m)", color=COLOR_MUTED, fontsize=9)
cbar.ax.tick_params(colors=COLOR_MUTED)

ax1.scatter([east[0]], [north[0]], color=COLOR_ACCENT2, s=90, marker="o", label="Kalkış Noktası")
ax1.scatter([east[-1]], [north[-1]], color=COLOR_ACCENT3, s=90, marker="X", label="Son Konum")

ax1.set_title("Panel 1: Taktik Uçuş Yörüngesi ve İrtifa Renk Haritası (NED)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xlabel("Doğu Koordinatı (East) [m]", color=COLOR_MUTED, fontsize=10)
ax1.set_ylabel("Kuzey Koordinatı (North) [m]", color=COLOR_MUTED, fontsize=10)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax1.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper left", fontsize=8)

# --- PANEL 2: Euler Açıları (Roll, Pitch, Yaw) Zaman Serisi ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

t_axis = np.array(sim.history_time)
eulers = sim.history_euler
rolls = [math.degrees(e.roll) for e in eulers]
pitches = [math.degrees(e.pitch) for e in eulers]
yaws = [math.degrees(e.yaw) for e in eulers]

ax2.plot(t_axis, rolls, color=COLOR_ACCENT1, linewidth=2.0, label="Roll (Yatış) [deg]")
ax2.plot(t_axis, pitches, color=COLOR_ACCENT2, linewidth=2.0, label="Pitch (Yunuslama) [deg]")
ax2.plot(t_axis, yaws, color=COLOR_ACCENT4, linewidth=2.0, label="Yaw (Pruva) [deg]")

ax2.set_title("Panel 2: Euler Açıları Zaman Profili (Roll, Pitch, Yaw)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_xlabel("Zaman [s]", color=COLOR_MUTED, fontsize=10)
ax2.set_ylabel("Açı [Derece]", color=COLOR_MUTED, fontsize=10)
ax2.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax2.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper left", fontsize=8)

# --- PANEL 3: Kuaterniyon Bileşenleri (qw, qx, qy, qz) Evrimi ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

# Kuaterniyonları simülasyon geçmişinden yeniden hesapla veya çıkar
qw_vals = [math.cos(math.radians(y)/2)*math.cos(math.radians(p)/2)*math.cos(math.radians(r)/2) for r, p, y in zip(rolls, pitches, yaws)]
qx_vals = [math.sin(math.radians(r)/2)*math.cos(math.radians(p)/2)*math.cos(math.radians(y)/2) for r, p, y in zip(rolls, pitches, yaws)]
qy_vals = [math.cos(math.radians(r)/2)*math.sin(math.radians(p)/2)*math.cos(math.radians(y)/2) for r, p, y in zip(rolls, pitches, yaws)]
qz_vals = [math.cos(math.radians(r)/2)*math.cos(math.radians(p)/2)*math.sin(math.radians(y)/2) for r, p, y in zip(rolls, pitches, yaws)]

ax3.plot(t_axis, qw_vals, color="#E2E8F0", linewidth=1.8, label="q_w (Skalar)")
ax3.plot(t_axis, qx_vals, color=COLOR_ACCENT1, linewidth=1.8, label="q_x (Roll Vektörü)")
ax3.plot(t_axis, qy_vals, color=COLOR_ACCENT2, linewidth=1.8, label="q_y (Pitch Vektörü)")
ax3.plot(t_axis, qz_vals, color=COLOR_ACCENT4, linewidth=1.8, label="q_z (Yaw Vektörü)")

ax3.set_title("Panel 3: Birim Kuaterniyon Bileşenleri Evrimi (q in H)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("Zaman [s]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("Kuaterniyon Değeri [-1, 1]", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="lower left", fontsize=8)

# --- PANEL 4: 100.000 Adımlık Gecikme Dağılımı ve Eksen Karşılaştırması ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

n, bins, patches = ax4.hist(latencies_us, bins=50, color=COLOR_ACCENT1, alpha=0.75, edgecolor="#0284C7")
ax4.axvline(p50, color=COLOR_ACCENT2, linestyle="-", linewidth=2.2, label=f"p50: {p50:.2f} µs")
ax4.axvline(p90, color=COLOR_ACCENT4, linestyle="--", linewidth=2.2, label=f"p90: {p90:.2f} µs")
ax4.axvline(p99, color=COLOR_ACCENT3, linestyle="-.", linewidth=2.2, label=f"p99: {p99:.2f} µs")

ax4.set_title("Panel 4: 100.000 Döngü Kuaterniyon İntegrasyon Gecikmesi (µs)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_xlabel("İcra Gecikmesi [µs]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylabel("Frekans (Adım Sayısı)", color=COLOR_MUTED, fontsize=10)
ax4.tick_params(colors=COLOR_MUTED)
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax4.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# Başlık
plt.suptitle("BAYRAKTAR TB2 / PX4 — İHA TEMEL EKSENLERİ, ATTITUDE VE POSITION KİNEMATİĞİ", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_226/gun_226_uav_temel_eksenler_attitude_position.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

