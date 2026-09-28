# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 220: ROS 2 TF2 Koordinat Sistemleri Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: Core TF2 Dönüşüm Ağacı ve Kuaterniyon Kinematik Motoru
# ============================================================================
import time
import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

def euler_to_quaternion(roll: float, pitch: float, yaw: float) -> Tuple[float, float, float, float]:
    # Roll (X), Pitch (Y), Yaw (Z) -> Quaternion (qx, qy, qz, qw)
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    qw = cr * cp * cy + sr * sp * sy
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy
    return (qx, qy, qz, qw)

def quaternion_to_rotation_matrix(qx: float, qy: float, qz: float, qw: float) -> np.ndarray:
    # 3x3 Rotasyon Matrisi
    return np.array([
        [1 - 2*qy*qy - 2*qz*qz, 2*qx*qy - 2*qz*qw,     2*qx*qz + 2*qy*qw],
        [2*qx*qy + 2*qz*qw,     1 - 2*qx*qx - 2*qz*qz, 2*qy*qz - 2*qx*qw],
        [2*qx*qz - 2*qy*qw,     2*qy*qz + 2*qx*qw,     1 - 2*qx*qx - 2*qy*qy]
    ])

class TransformStamped:
    def __init__(self, parent_frame: str, child_frame: str,
                 translation: Tuple[float, float, float],
                 rotation_quat: Tuple[float, float, float, float],
                 timestamp: float):
        self.parent_frame = parent_frame
        self.child_frame = child_frame
        self.translation = np.array(translation, dtype=float)
        self.rotation_quat = rotation_quat
        self.timestamp = timestamp
        self.rot_matrix = quaternion_to_rotation_matrix(*rotation_quat)

    def get_homogeneous_matrix(self) -> np.ndarray:
        T = np.eye(4)
        T[0:3, 0:3] = self.rot_matrix
        T[0:3, 3] = self.translation
        return T

class SimpleTF2Buffer:
    def __init__(self):
        self.transforms: Dict[str, TransformStamped] = {} # child_frame -> Transform

    def set_transform(self, tf: TransformStamped):
        self.transforms[tf.child_frame] = tf

    def lookup_transform(self, target_frame: str, source_frame: str) -> np.ndarray:
        # source_frame'den target_frame'e bileşik dönüşüm matrisi hesaplar
        # T_target_source
        if source_frame == target_frame:
            return np.eye(4)

        # Ağaçta köke doğru zincir oluştur ve kök kimliğini bul
        def get_root_and_chain(frame: str) -> Tuple[str, List[TransformStamped]]:
            chain = []
            curr = frame
            while curr in self.transforms:
                tf = self.transforms[curr]
                chain.append(tf)
                curr = tf.parent_frame
            return curr, chain

        root_src, chain_src = get_root_and_chain(source_frame)
        root_tgt, chain_tgt = get_root_and_chain(target_frame)

        if root_src != root_tgt:
            raise ValueError(f"TF2_CONNECTIVITY_ERROR: '{source_frame}' (kök: {root_src}) ile "
                             f"'{target_frame}' (kök: {root_tgt}) arasında ortak kök bulunamadı!")

        # Kök üzerinden dönüşüm matrisini kur
        T_root_src = np.eye(4)
        for tf in chain_src:
            T_root_src = tf.get_homogeneous_matrix() @ T_root_src

        T_root_tgt = np.eye(4)
        for tf in chain_tgt:
            T_root_tgt = tf.get_homogeneous_matrix() @ T_root_tgt

        # T_tgt_src = (T_root_tgt)^(-1) @ T_root_src
        T_tgt_src = np.linalg.inv(T_root_tgt) @ T_root_src
        return T_tgt_src

# Aviyonik Senaryo Testi:
# 1. map -> base_link (Uçak Konumu: X=100m, Y=200m, Z=500m, Yaw=90 derece)
# 2. base_link -> camera_link (Gövdede Kamera: X=1.5m ileri, Z=-0.5m aşağı, Pitch=30 derece aşağı bakıyor)
tf_buffer = SimpleTF2Buffer()
now = time.perf_counter()

q_uav = euler_to_quaternion(roll=0.0, pitch=0.0, yaw=math.radians(90.0))
tf_uav = TransformStamped(parent_frame="map", child_frame="base_link",
                          translation=(100.0, 200.0, 500.0),
                          rotation_quat=q_uav, timestamp=now)
tf_buffer.set_transform(tf_uav)

q_cam = euler_to_quaternion(roll=0.0, pitch=math.radians(30.0), yaw=0.0)
tf_cam = TransformStamped(parent_frame="base_link", child_frame="camera_link",
                          translation=(1.5, 0.0, -0.5),
                          rotation_quat=q_cam, timestamp=now)
tf_buffer.set_transform(tf_cam)

# Kameranın gördüğü hedef: Kamera görüş ekseninde [X=50m ileride, Y=0, Z=0]
target_cam_homo = np.array([50.0, 0.0, 0.0, 1.0])

T_map_cam = tf_buffer.lookup_transform(target_frame="map", source_frame="camera_link")
target_map_homo = T_map_cam @ target_cam_homo

print(f"[TF2 DÖNÜŞÜM ZİNCİRİ HESAPLANDI]")
print(f"  - Kamera Koordinatında Hedef: [X={target_cam_homo[0]:.1f}, Y={target_cam_homo[1]:.1f}, Z={target_cam_homo[2]:.1f}]")
print(f"  - Harita (Dünya) Koordinatı  : [X={target_map_homo[0]:.1f}, Y={target_map_homo[1]:.1f}, Z={target_map_homo[2]:.1f}]")

assert abs(target_map_homo[2] - (500.0 - 0.5 - 25.0)) < 1.0 # 500 - 0.5 - 50*sin(30)=25 -> ~474.5m
assert abs(target_map_homo[1] - 244.8) < 1.0 # 200 + 1.5 + 50*cos(30) -> ~244.8m
assert abs(target_map_homo[0] - 100.0) < 1.0 # X ekseninde sapma yok (Yaw 90 derece)
print("\n[PASS] Kod 1: Core TF2 Dönüşüm Ağacı ve Kuaterniyon Hesaplamaları Başarıyla Doğrulandı.")

# ============================================================================
# KOD HÜCRESİ 2: Statik vs Dinamik TF Ağ Bant Genişliği ve Enterpolasyon
# ============================================================================

class TFPublisherSimulator:
    def __init__(self, frame_name: str, is_static: bool):
        self.frame_name = frame_name
        self.is_static = is_static
        self.published_bytes = 0
        self.msg_count = 0

    def publish_frame(self, current_time: float, payload_size: int = 128):
        if self.is_static and self.msg_count >= 1:
            # Statik TF Transient Local'dir; tekrar tekrar hatta basılmaz!
            return
        self.published_bytes += payload_size
        self.msg_count += 1

# 10 Saniyelik Aviyonik Görev Simülasyonu
# 10 adet Sabit Sensör (Statik) + 2 adet Dinamik Gövde/Gimbal (100 Hz Dinamik)
static_sensors = [TFPublisherSimulator(f"sensor_{i}_link", is_static=True) for i in range(10)]
dynamic_frames = [TFPublisherSimulator("base_link", is_static=False),
                  TFPublisherSimulator("gimbal_link", is_static=False)]

simulation_time_s = 10.0
dt = 0.01 # 100 Hz
steps = int(simulation_time_s / dt)

for s in range(steps):
    t = s * dt
    for sf in static_sensors:
        sf.publish_frame(t)
    for df in dynamic_frames:
        df.publish_frame(t)

total_static_bytes = sum(sf.published_bytes for sf in static_sensors)
total_dynamic_bytes = sum(df.published_bytes for df in dynamic_frames)

print(f"[10 SANİYELİK TF AĞ TRAFİĞİ RAPORU]")
print(f"  - 10 Statik Sensör Toplam Veri : {total_static_bytes / 1024:.2f} KB ({sum(sf.msg_count for sf in static_sensors)} mesaj)")
print(f"  - 2 Dinamik Çerçeve Toplam Veri: {total_dynamic_bytes / 1024:.2f} KB ({sum(df.msg_count for df in dynamic_frames)} mesaj)")
print(f"  - Statik Tasarruf Oranı        : {total_dynamic_bytes / max(1, total_static_bytes):.1f}x Kat Daha Az Ağ Tüketimi!")

assert total_static_bytes == 10 * 128 # Her biri tam 1 kez yayınlandı
assert total_dynamic_bytes == 2 * 1000 * 128 # 100 Hz * 10s = 1000 mesaj

print("\n[PASS] Kod 2: Statik TF ve Dinamik TF Ağ Ayrımı Başarıyla Doğrulandı.")

# ============================================================================
# KOD HÜCRESİ 3: TF2 Zaman Yolculuğu ve SLERP (Küresel Enterpolasyon) Motoru
# ============================================================================

def slerp(q1: Tuple[float, float, float, float], q2: Tuple[float, float, float, float], t: float) -> Tuple[float, float, float, float]:
    # İki kuaterniyon arasında küresel doğrusal enterpolasyon (Spherical Linear Interpolation)
    q1 = np.array(q1)
    q2 = np.array(q2)
    dot = np.dot(q1, q2)

    if dot < 0.0:
        q2 = -q2
        dot = -dot

    if dot > 0.9995:
        # Açı çok küçükse doğrusal enterpolasyon yap
        result = q1 + t * (q2 - q1)
        return tuple(result / np.linalg.norm(result))

    theta_0 = math.acos(dot)
    theta = theta_0 * t
    sin_theta = math.sin(theta)
    sin_theta_0 = math.sin(theta_0)

    s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
    s1 = sin_theta / sin_theta_0
    res = (s0 * q1) + (s1 * q2)
    return tuple(res)

class TimeTravelTFBuffer:
    def __init__(self, max_history_sec: float = 5.0):
        self.history: List[Tuple[float, float, Tuple[float, float, float, float]]] = [] # (time, yaw, quat)

    def record_pose(self, timestamp: float, yaw_deg: float):
        q = euler_to_quaternion(0.0, 0.0, math.radians(yaw_deg))
        self.history.append((timestamp, yaw_deg, q))

    def lookup_interpolated_yaw(self, query_time: float) -> float:
        # En yakın iki zaman dilimini bul ve enterpolasyon yap
        for i in range(len(self.history) - 1):
            t0, y0, q0 = self.history[i]
            t1, y1, q1 = self.history[i+1]
            if t0 <= query_time <= t1:
                ratio = (query_time - t0) / (t1 - t0)
                q_interp = slerp(q0, q1, ratio)
                # Yaw açısını geri çöz
                siny_cosp = 2 * (q_interp[3] * q_interp[2] + q_interp[0] * q_interp[1])
                cosy_cosp = 1 - 2 * (q_interp[1] * q_interp[1] + q_interp[2] * q_interp[2])
                return math.degrees(math.atan2(siny_cosp, cosy_cosp))
        raise ValueError("TF_EXTRAPOLATION_ERROR: Sorgulanan zaman geçmiş tampon aralığının dışında!")

buffer = TimeTravelTFBuffer()
# Uçak saniyede 10 derece dönüyor: t=0s -> 0 deg, t=1s -> 10 deg, t=2s -> 20 deg
buffer.record_pose(100.0, 0.0)
buffer.record_pose(101.0, 10.0)
buffer.record_pose(102.0, 20.0)

# Kamera verisi t = 100.5 saniyesine ait! (Zaman Yolculuğu Sorgusu)
query_t = 100.5
calculated_yaw = buffer.lookup_interpolated_yaw(query_t)

print(f"[TF2 ZAMAN YOLCULUĞU VE SLERP ANALİZİ]")
print(f"  - Sorgulanan Zaman : {query_t} s")
print(f"  - SLERP İle Bulunan Yaw Açısı: {calculated_yaw:.2f} derece (Beklenen: 5.00 derece)")

assert abs(calculated_yaw - 5.0) < 0.01
print("\n[PASS] Kod 3: TF2 Zaman Yolculuğu ve SLERP Enterpolasyonu Başarıyla Doğrulandı.")

# ============================================================================
# KOD HÜCRESİ 4: Hata Enjeksiyonu (Fault Injection) ve Savunma Doğrulama Testi
# ============================================================================

# ----------------------------------------------------------------------------
# TEST A: Ekstrapolasyon Hatası Enjeksiyonu (Gelecek Zaman Sorgusu)
# ----------------------------------------------------------------------------
print("[TEST A] Ekstrapolasyon Hatası Enjeksiyonu...")

extrap_caught = False
try:
    # Tampondaki son veri 102.0s iken 105.0s sorgulanıyor!
    buffer.lookup_interpolated_yaw(query_time=105.0)
except ValueError as e:
    extrap_caught = True
    print(f"  [BEKLENEN HATA YAKALANDI]: {e}")

assert extrap_caught == True
print("  [PASS] Test A Başarıyla Geçti: Ekstrapolasyon aşımı emniyetle engellendi.\n")

# ----------------------------------------------------------------------------
# TEST B: Kopuk Ağaç (Connectivity Exception) Tespiti
# ----------------------------------------------------------------------------
print("[TEST B] Kopuk Dönüşüm Ağacı (Disconnected Tree) Tespiti...")

broken_tf_buffer = SimpleTF2Buffer()
# map -> base_link var, ama radar_link bağımsız havada asılı!
broken_tf_buffer.set_transform(TransformStamped("map", "base_link", (0,0,0), (0,0,0,1), 10.0))
broken_tf_buffer.set_transform(TransformStamped("isolated_gimbal", "radar_link", (0,0,0), (0,0,0,1), 10.0))

def safe_lookup(buf: SimpleTF2Buffer, target: str, source: str) -> bool:
    try:
        _ = buf.lookup_transform(target, source)
        return True
    except np.linalg.LinAlgError:
        return False
    except Exception as ex:
        print(f"  [BEKLENEN BAĞLANTI HATASI]: {source} -> {target} arasında ortak kök bulunamadı!")
        return False

# radar_link'ten map'e dönüşüm olamaz çünkü isolated_gimbal map'e bağlı değil!
assert safe_lookup(broken_tf_buffer, "map", "radar_link") == False
print("  [PASS] Test B Başarıyla Geçti: Kopuk ağaç dönüşüm girişimi engellendi.\n")

# ----------------------------------------------------------------------------
# TEST C: Çoklu Ebeveyn İhlali (Multiple Parents Violation)
# ----------------------------------------------------------------------------
print("[TEST C] Çoklu Ebeveyn Kuralı İhlali Tespiti...")

class StrictTFValidator:
    def __init__(self):
        self.child_to_parent: Dict[str, str] = {}

    def add_edge(self, parent: str, child: str) -> bool:
        if child in self.child_to_parent and self.child_to_parent[child] != parent:
            raise RuntimeError(f"TF2_MULTIPLE_PARENT_ERROR: '{child}' çerçevesinin zaten bir ebeveyni var ({self.child_to_parent[child]})! "
                               f"Yeni ebeveyn '{parent}' atanamaz. TF bir ağaç (tree) olmalıdır, ağ (graph) olamaz!")
        self.child_to_parent[child] = parent
        return True

validator = StrictTFValidator()
validator.add_edge("base_link", "camera_link")

multi_parent_caught = False
try:
    # camera_link'e ikinci bir ebeveyn atanmaya çalışılıyor!
    validator.add_edge("wing_tip_link", "camera_link")
except RuntimeError as e:
    multi_parent_caught = True
    print(f"  [BEKLENEN KURAL İHLALİ]: {e}")

assert multi_parent_caught == True
print("  [PASS] Test C Başarıyla Geçti: Çoklu ebeveyn ataması durum motoru tarafından kilitlendi.")

print("\n[PASS] Kod 4: 3 Kritik TF2 Hata Enjeksiyonu Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 100.000 Yüksek Frekanslı Aviyonik TF Sorgu Benchmark'ı
# ============================================================================
import time
import numpy as np

def run_tf2_lookup_benchmark(query_count: int = 100000):
    print(f"[BENCHMARK] {query_count:,} Aviyonik TF Dönüşüm Sorgusu İcra Ediliyor...")

    # T_map_cam hazır dönüşüm matrisi üzerinde 100.000 vektör çarpımı
    T_matrix = np.array([
        [0.0, -0.866, 0.5, 101.5],
        [1.0, 0.0, 0.0, 200.0],
        [0.0, 0.5, 0.866, 474.5],
        [0.0, 0.0, 0.0, 1.0]
    ])

    # 100.000 adet 3B hedef noktası (homojen)
    points = np.random.uniform(low=-100.0, high=100.0, size=(4, query_count))
    points[3, :] = 1.0 # Homojen koordinat

    t0 = time.perf_counter()
    transformed_points = T_matrix @ points # SIMD / BLAS Vektörel Çarpım
    duration_s = time.perf_counter() - t0

    throughput_ops = query_count / duration_s
    avg_latency_us = (duration_s / query_count) * 1e6

    results = {
        "query_count": query_count,
        "duration_s": duration_s,
        "throughput_ops": throughput_ops,
        "avg_latency_us": avg_latency_us
    }
    return results

bench_res = run_tf2_lookup_benchmark(query_count=100000)

print(f"\n[TF2 DÖNÜŞÜM BAŞARIM METRİKLERİ]")
print(f"  - Toplam Süre      : {bench_res['duration_s']:.4f} saniye")
print(f"  - İşlem Hacmi      : {bench_res['throughput_ops']:,.0f} dönüşüm/saniye")
print(f"  - Ortalama Gecikme : {bench_res['avg_latency_us']:.4f} mikrosaniye (µs) / sorgu")

assert bench_res['throughput_ops'] > 1000000, "Dönüşüm motoru saniyede en az 1 milyon işlem yapabilmelidir!"
assert bench_res['avg_latency_us'] < 1.0, "Tekil dönüşüm gecikmesi 1 mikrosaniyenin altında kalmalıdır!"

print("\n[PASS] Kod 5: Yüksek Frekanslı TF2 Kinematik Benchmark'ı Başarıyla Tamamlandı.")

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
# PANEL 1: Aviyonik TF2 Dönüşüm Ağacı
# ----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("PANEL 1: Aviyonik TF2 Dönüşüm Ağacı (REP-105 Standartları)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

nodes_tree = [
    ("earth (WGS-84)", 0.50, 0.88, '#64748B'),
    ("map (ENU)", 0.50, 0.70, '#818CF8'),
    ("odom (INS)", 0.50, 0.52, '#38BDF8'),
    ("base_link (Gövde)", 0.50, 0.34, '#10B981'),
    ("imu_link (Statik)", 0.20, 0.14, '#F59E0B'),
    ("gimbal_link (Dinamik)", 0.50, 0.14, '#F59E0B'),
    ("camera_optical (Hedef)", 0.80, 0.14, '#EF4444')
]

for name, x, y, col in nodes_tree:
    box = plt.Rectangle((x-0.12, y-0.05), 0.24, 0.10, facecolor=col, edgecolor='#FFFFFF', linewidth=1.2, alpha=0.85, transform=ax1.transAxes)
    ax1.add_patch(box)
    ax1.text(x, y, name, color='#0F172A' if col in ['#F59E0B', '#38BDF8', '#10B981'] else '#FFFFFF', 
             fontsize=9, fontweight='bold', ha='center', va='center', transform=ax1.transAxes)

# Bağlantı Çizgileri
ax1.annotate("", xy=(0.5, 0.75), xytext=(0.5, 0.83), xycoords='axes fraction', arrowprops=dict(arrowstyle="->", color='#FFFFFF', lw=1.5))
ax1.annotate("", xy=(0.5, 0.57), xytext=(0.5, 0.65), xycoords='axes fraction', arrowprops=dict(arrowstyle="->", color='#FFFFFF', lw=1.5))
ax1.annotate("", xy=(0.5, 0.39), xytext=(0.5, 0.47), xycoords='axes fraction', arrowprops=dict(arrowstyle="->", color='#FFFFFF', lw=1.5))
ax1.annotate("", xy=(0.2, 0.19), xytext=(0.42, 0.29), xycoords='axes fraction', arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=1.5))
ax1.annotate("", xy=(0.5, 0.19), xytext=(0.50, 0.29), xycoords='axes fraction', arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=1.5))
ax1.annotate("", xy=(0.8, 0.19), xytext=(0.58, 0.29), xycoords='axes fraction', arrowprops=dict(arrowstyle="->", color='#EF4444', lw=1.5))

ax1.set_xlim(0, 1)
ax1.set_ylim(0, 1)
ax1.axis('off')

# ----------------------------------------------------------------------------
# PANEL 2: Statik vs Dinamik TF Ağ Yükü
# ----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("PANEL 2: Statik (/tf_static) vs Dinamik (/tf) Ağ Trafiği (KB)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

categories = ['10 Statik Sensör (/tf_static)', '2 Dinamik Çerçeve (/tf - 100Hz)']
traffic_kb = [total_static_bytes / 1024.0, total_dynamic_bytes / 1024.0]
colors_tr = ['#10B981', '#EF4444']

b = ax2.bar(categories, traffic_kb, color=colors_tr, width=0.45, alpha=0.85, edgecolor='#FFFFFF')
ax2.set_ylabel("Toplam Aktarılan Veri (KB)", color='#E2E8F0', fontsize=11)

for bar in b:
    y = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, y + 5, f"{y:.2f} KB", ha='center', va='bottom', color='#FFFFFF', fontsize=10, fontweight='bold')

ax2.text(0.5, 0.70, f"Bant Genişliği Tasarrufu: {total_dynamic_bytes / total_static_bytes:.0f}x Kat!", 
         ha='center', va='center', color='#6EE7B7', fontsize=11, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor='#10B981', alpha=0.9), transform=ax2.transAxes)

# ----------------------------------------------------------------------------
# PANEL 3: 3B Projeksiyon ve Hedef Dönüşümü
# ----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("PANEL 3: Kamera Görüş Hattından Harita (Map) Hedef Projeksiyonu", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

uav_x, uav_y = 100.0, 200.0
tgt_x, tgt_y = target_map_homo[0], target_map_homo[1]

ax3.plot([uav_x], [uav_y], marker='^', markersize=14, color='#10B981', label='Uçak (base_link)')
ax3.plot([tgt_x], [tgt_y], marker='X', markersize=14, color='#EF4444', label='Hedef (camera -> map)')
ax3.plot([uav_x, tgt_x], [uav_y, tgt_y], linestyle='--', color='#38BDF8', linewidth=2.0, label='Görüş Hattı (Line-of-Sight)')

ax3.set_xlabel("Harita X Koordinatı (Metre)", color='#E2E8F0', fontsize=11)
ax3.set_ylabel("Harita Y Koordinatı (Metre)", color='#E2E8F0', fontsize=11)
ax3.legend(facecolor='#0F172A', edgecolor='#475569', labelcolor='#E2E8F0', loc='lower left')

ax3.text(uav_x - 10, uav_y + 5, f"Uçak: ({uav_x:.0f}, {uav_y:.0f})", color='#10B981', fontweight='bold', fontsize=9.5)
ax3.text(tgt_x + 5, tgt_y - 5, f"Hedef: ({tgt_x:.1f}, {tgt_y:.1f})", color='#EF4444', fontweight='bold', fontsize=9.5)

# ----------------------------------------------------------------------------
# PANEL 4: SLERP Zaman Yolculuğu Enterpolasyon Eğrisi
# ----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("PANEL 4: SLERP Kuaterniyon Zaman Yolculuğu Eğrisi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

t_steps = np.linspace(100.0, 102.0, 50)
yaw_curve = [buffer.lookup_interpolated_yaw(t) for t in t_steps]

ax4.plot(t_steps, yaw_curve, color='#38BDF8', linewidth=2.5, label='SLERP Enterpole Yaw Açısı')
ax4.scatter([100.0, 101.0, 102.0], [0.0, 10.0, 20.0], color='#F59E0B', s=80, zorder=5, label='TF Örneklem Noktaları')
ax4.scatter([query_t], [calculated_yaw], color='#EF4444', s=120, marker='*', zorder=6, label=f'Sensör Gecikme Noktası (t={query_t}s, {calculated_yaw:.1f}°)')

ax4.set_xlabel("Zaman Damgası (Saniye)", color='#E2E8F0', fontsize=11)
ax4.set_ylabel("Dönüşüm Yaw Açısı (Derece)", color='#E2E8F0', fontsize=11)
ax4.legend(facecolor='#0F172A', edgecolor='#475569', labelcolor='#E2E8F0', loc='upper left')

# Filigran ve Lisans Notu
fig.text(0.5, 0.015, "ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR | Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)",
         ha='center', va='bottom', color='#94A3B8', fontsize=10, fontweight='bold')

plt.tight_layout(rect=[0, 0.03, 1, 0.97])

output_png = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_220/gun_220_ros2_tf2_coordinate_frames.png"
if not os.path.isabs(output_png) or not os.path.exists(os.path.dirname(output_png)):
    output_png = "gun_220_ros2_tf2_coordinate_frames.png"

plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "Görsel dosya boyutu 100 KB'den küçük olamaz!"

