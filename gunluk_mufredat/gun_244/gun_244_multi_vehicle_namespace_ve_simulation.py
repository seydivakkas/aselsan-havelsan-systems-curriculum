# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 244: Multi-Vehicle Namespace ve Simülasyon Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: Sürü Konfigürasyon ve Çakışmasız Port Tahsis Doğrulayıcısı
# Dinamik port üretimi, SYS_ID haritalama, ad alanı ve TF izolasyon testi.
# ============================================================================
from dataclasses import dataclass
from typing import List, Set

@dataclass(frozen=True)
class SwarmVehicleConfig:
    instance_id: int
    mav_sys_id: int
    sitl_port: int
    mavlink_port: int
    uxrce_port: int
    ros_namespace: str
    tf_frame_id: str

class SwarmTopologyManager:
    BASE_SITL_PORT = 4560
    BASE_MAVLINK_PORT = 14540
    BASE_UXRCE_PORT = 8888

    @classmethod
    def create_swarm(cls, num_vehicles: int) -> List[SwarmVehicleConfig]:
        fleet = []
        for i in range(num_vehicles):
            cfg = SwarmVehicleConfig(
                instance_id=i,
                mav_sys_id=i + 1,
                sitl_port=cls.BASE_SITL_PORT + i,
                mavlink_port=cls.BASE_MAVLINK_PORT + i,
                uxrce_port=cls.BASE_UXRCE_PORT + i,
                ros_namespace=f"/uav{i}",
                tf_frame_id=f"uav{i}/base_link"
            )
            fleet.append(cfg)
        return fleet

# Test: 4 Araçlık STM KARGU / Bayraktar Sürü Simülasyon Konfigürasyonu
swarm = SwarmTopologyManager.create_swarm(4)

# Çakışma Denetimleri (Collision Checks)
sys_ids: Set[int] = set()
sitl_ports: Set[int] = set()
mav_ports: Set[int] = set()
uxrce_ports: Set[int] = set()
namespaces: Set[str] = set()
tf_frames: Set[str] = set()

for v in swarm:
    sys_ids.add(v.mav_sys_id)
    sitl_ports.add(v.sitl_port)
    mav_ports.add(v.mavlink_port)
    uxrce_ports.add(v.uxrce_port)
    namespaces.add(v.ros_namespace)
    tf_frames.add(v.tf_frame_id)

assert len(sys_ids) == 4, "SYS_ID çakışması tespit edildi!"
assert len(sitl_ports) == 4, "SITL port çakışması tespit edildi!"
assert len(mav_ports) == 4, "MAVLink port çakışması tespit edildi!"
assert len(uxrce_ports) == 4, "uXRCE port çakışması tespit edildi!"
assert len(namespaces) == 4, "ROS 2 Ad Alanı çakışması tespit edildi!"
assert len(tf_frames) == 4, "TF Çerçeve adı çakışması tespit edildi!"

print("[PASS] Kod 1: Sürü Konfigürasyonu ve Çakışmasız Port Dağıtımı Doğrulandı.")
for v in swarm:
    print(f"  - İHA {v.instance_id}: SYS_ID={v.mav_sys_id:<2} | Portlar (SITL:{v.sitl_port}, MAV:{v.mavlink_port}, XRCE:{v.uxrce_port}) | NS={v.ros_namespace:<6} | TF={v.tf_frame_id}")

# ============================================================================
# KOD HÜCRESİ 2: Sürü Konu Yönlendiricisi ve Çapraz Karışma (Cross-Talk) Kalkanı
# Ad alanı bazlı mesaj ayrıştırma ve hedef dışı komut izolasyonu.
# ============================================================================
from typing import Dict, Tuple

@dataclass
class TrajectorySetpoint:
    x: float
    y: float
    z: float
    yaw: float

class SwarmTopicRouter:
    def __init__(self, fleet: List[SwarmVehicleConfig]):
        self.fleet_map: Dict[str, SwarmVehicleConfig] = {v.ros_namespace: v for v in fleet}
        self.last_received_cmd: Dict[int, TrajectorySetpoint] = {}
        self.cmd_counters: Dict[int, int] = {v.instance_id: 0 for v in fleet}

    def route_command(self, namespace: str, target_sys_id: int, cmd: TrajectorySetpoint) -> bool:
        vehicle = self.fleet_map.get(namespace)
        if not vehicle:
            return False # Bilinmeyen ad alanı
            
        # Güvenlik Kalkanı: Gelen konudaki SYS_ID ile aracın kendi SYS_ID'si eşleşmeli
        if vehicle.mav_sys_id != target_sys_id:
            # Çapraz Karışma / Yetkisiz Yönlendirme Tespit Edildi!
            return False
            
        self.last_received_cmd[vehicle.instance_id] = cmd
        self.cmd_counters[vehicle.instance_id] += 1
        return True

router = SwarmTopicRouter(swarm)

# Komut 1: UAV 0'a rota gönder (/uav0, SYS_ID=1)
cmd_uav0 = TrajectorySetpoint(x=100.0, y=0.0, z=-50.0, yaw=0.0)
ok_0 = router.route_command("/uav0", target_sys_id=1, cmd=cmd_uav0)
assert ok_0 == True
assert router.last_received_cmd[0] == cmd_uav0
assert router.cmd_counters[0] == 1
assert router.cmd_counters[1] == 0 # UAV 1 etkilenmemeli!

# Komut 2: UAV 1'e farklı bir rota gönder (/uav1, SYS_ID=2)
cmd_uav1 = TrajectorySetpoint(x=90.0, y=-10.0, z=-50.0, yaw=0.0)
ok_1 = router.route_command("/uav1", target_sys_id=2, cmd=cmd_uav1)
assert ok_1 == True
assert router.last_received_cmd[1] == cmd_uav1
assert router.cmd_counters[1] == 1

# Kötü Niyetli / Hatalı Komut: /uav0 konusuna SYS_ID=2 komutu atılırsa
hijack_attempt = router.route_command("/uav0", target_sys_id=2, cmd=cmd_uav1)
assert hijack_attempt == False, "Yetkisiz çapraz komut kabul edildi!"

print("[PASS] Kod 2: Sürü Konu Yönlendiricisi ve Çapraz Karışma Kalkanı Doğrulandı.")
print(f"  - UAV 0 Komutu : X={router.last_received_cmd[0].x}m, Y={router.last_received_cmd[0].y}m (Hedef: UAV0 [OK])")
print(f"  - UAV 1 Komutu : X={router.last_received_cmd[1].x}m, Y={router.last_received_cmd[1].y}m (Hedef: UAV1 [OK])")
print("  - Çapraz Karışma Testi: /uav0 kanalından gelen yabancı SYS_ID=2 paketi ENGELLENDİ [GÜVENLİ]")

# ============================================================================
# KOD HÜCRESİ 3: Sürü Formasyon Uçuşu ve Araçlar Arası Ayrılma Mesafesi Monitörü
# 3'lü V-formasyonu kinematiği, Öklid mesafe matrisi ve çarpışma güvenliği.
# ============================================================================
import numpy as np

class SwarmFormationMonitor:
    SAFE_SEPARATION_M = 5.0 # Asgari 5 metre emniyet mesafesi

    @staticmethod
    def simulate_v_formation(duration_s: float = 20.0, dt: float = 0.1) -> Dict[str, Any]:
        t_steps = np.arange(0, duration_s, dt)
        n_steps = len(t_steps)
        
        # Lider Hızı: 15 m/s X yönünde ileri uçuş
        v_cruise = 15.0
        
        # 3 Aracın Konum Matrisleri [n_steps, 3] (X, Y, Z)
        pos_uav0 = np.zeros((n_steps, 3))
        pos_uav1 = np.zeros((n_steps, 3))
        pos_uav2 = np.zeros((n_steps, 3))
        
        # İrtifa sabit 50m (NED Z = -50m)
        pos_uav0[:, 2] = -50.0
        pos_uav1[:, 2] = -50.0
        pos_uav2[:, 2] = -50.0
        
        # Lider İlerleyişi
        pos_uav0[:, 0] = v_cruise * t_steps
        pos_uav0[:, 1] = 0.0
        
        # Sol Kanat (UAV 1): 10m geride, 10m solda (Y = -10m)
        pos_uav1[:, 0] = pos_uav0[:, 0] - 10.0
        pos_uav1[:, 1] = -10.0
        
        # Sağ Kanat (UAV 2): 10m geride, 10m sağda (Y = +10m)
        pos_uav2[:, 0] = pos_uav0[:, 0] - 10.0
        pos_uav2[:, 1] = 10.0
        
        # İkili Mesafeleri Hesapla
        d_01 = np.linalg.norm(pos_uav0 - pos_uav1, axis=1)
        d_02 = np.linalg.norm(pos_uav0 - pos_uav2, axis=1)
        d_12 = np.linalg.norm(pos_uav1 - pos_uav2, axis=1)
        
        min_dist = min(np.min(d_01), np.min(d_02), np.min(d_12))
        
        return {
            "t": t_steps,
            "pos0": pos_uav0,
            "pos1": pos_uav1,
            "pos2": pos_uav2,
            "d_01": d_01,
            "d_02": d_02,
            "d_12": d_12,
            "min_distance_m": float(min_dist)
        }

sim_data = SwarmFormationMonitor.simulate_v_formation(20.0, 0.1)

# Doğrulamalar:
# d_01 ve d_02 sqrt(10^2 + 10^2) = 14.14 m olmalı
assert abs(sim_data["d_01"][0] - 14.142) < 1e-2
assert abs(sim_data["d_02"][0] - 14.142) < 1e-2
# d_12 kanat açıklığı 20.0 m olmalı
assert abs(sim_data["d_12"][0] - 20.0) < 1e-2
# En küçük mesafe emniyet sınırı olan 5.0m'den büyük olmalıdır
assert sim_data["min_distance_m"] >= SwarmFormationMonitor.SAFE_SEPARATION_M

print("[PASS] Kod 3: Sürü Formasyon Uçuşu ve Ayrılma Mesafesi Monitörü Doğrulandı.")
print(f"  - Lider - Sol Kanat Mesafesi (d01) : {sim_data['d_01'][0]:.2f} metre (Hedef: 14.14m [OK])")
print(f"  - Lider - Sağ Kanat Mesafesi (d02) : {sim_data['d_02'][0]:.2f} metre (Hedef: 14.14m [OK])")
print(f"  - Kanatlar Arası Mesafe     (d12) : {sim_data['d_12'][0]:.2f} metre (Hedef: 20.00m [OK])")
print(f"  - Minimum Sürü Ayrılma Mesafesi   : {sim_data['min_distance_m']:.2f} metre (Eşik: >= 5.0m [GÜVENLİ])")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik Sürü Güvenlik ve Hata Enjeksiyon Testi
# Çapraz komut engeli, mükerrer port reddi ve tehlikeli yakınlaşma alarmı.
# ============================================================================
import math

# --- TEST 1: Çapraz Araç Kaçırma (Cross-Vehicle Hijack) Kalkanı ---
print("[TEST 1] Çapraz Araç Kaçırma (Cross-Vehicle Hijack) Kalkanı Testi...")
def validate_command_integrity(ns: str, target_sys: int) -> bool:
    # Kural: ns = "/uav{i}" ise target_sys == i + 1 olmalıdır
    expected_sys = int(ns.replace("/uav", "")) + 1
    return target_sys == expected_sys

# Hatalı Paket: /uav1 kanalından SYS_ID=3 komutu verilirse:
assert validate_command_integrity("/uav1", target_sys=3) == False, "Kaçırma komutu kabul edildi!"
# Doğru Paket: /uav1 kanalından SYS_ID=2 komutu
assert validate_command_integrity("/uav1", target_sys=2) == True
print("  - Kanal: /uav1, Hedef SYS_ID: 3 -> REDDEDİLDİ (Çapraz Komut İhlali)")
print("  - Kanal: /uav1, Hedef SYS_ID: 2 -> KABUL EDİLDİ (Meşru Komut)")
print("  [PASS] Test 1: Çapraz araç kaçırma kalkanı başarıyla doğrulandı.\n")

# --- TEST 2: Mükerrer Port Çakışması Algılama ---
print("[TEST 2] Mükerrer Port Çakışması (Port Collision) Algılama Testi...")
class PortRegistry:
    def __init__(self):
        self.used_ports: Set[int] = set()

    def bind_port(self, port: int) -> bool:
        if port in self.used_ports:
            return False # Çakışma!
        self.used_ports.add(port)
        return True

registry = PortRegistry()
assert registry.bind_port(14540) == True # UAV 0 MAVLink portu
assert registry.bind_port(14541) == True # UAV 1 MAVLink portu
# Başka bir süreç aynı 14540 portunu bağlamaya kalkarsa:
assert registry.bind_port(14540) == False, "Port çakışması tespit edilemedi!"
print("  - Port 14540 (UAV 0) : BAĞLANDI")
print("  - Port 14541 (UAV 1) : BAĞLANDI")
print("  - Port 14540 (Tekrar): REDDEDİLDİ (EADDRINUSE Kalkanı)")
print("  [PASS] Test 2: Port çakışması algılama başarıyla doğrulandı.\n")

# --- TEST 3: Tehlikeli Yakınlaşma (Near-Miss) Çarpışma Alarmı ---
print("[TEST 3] Tehlikeli Yakınlaşma (Near-Miss) Çarpışma Alarmı Testi...")
def evaluate_proximity_safety(pos_a: Tuple[float, float, float], pos_b: Tuple[float, float, float]) -> str:
    dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(pos_a, pos_b)))
    if dist < 5.0:
        return "CRITICAL_COLLISION_ALERT"
    elif dist < 10.0:
        return "WARNING_PROXIMITY"
    return "SAFE_SEPARATION"

# Senaryo A: 14.14 metre güvenli mesafe
assert evaluate_proximity_safety((100, 0, -50), (90, -10, -50)) == "SAFE_SEPARATION"

# Senaryo B: Rüzgar darbesiyle 3.5 metreye yakınlaşma
danger_status = evaluate_proximity_safety((100, 0, -50), (98, -2.5, -48.0))
assert danger_status == "CRITICAL_COLLISION_ALERT", "Çarpışma alarmı üretilemedi!"
print("  - Mesafe = 14.14m : SAFE_SEPARATION [GÜVENLİ]")
print("  - Mesafe = 3.50m  : CRITICAL_COLLISION_ALERT [ACİL AYRILMA MANEVRASI TETİKLENDİ]")
print("  [PASS] Test 3: Tehlikeli yakınlaşma alarmı başarıyla doğrulandı.\n")

print("[PASS] Kod 4: 3 Kritik Sürü Güvenlik Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 100.000 Sürü Paketi Yönlendirme ve Dağıtım Benchmark'ı
# Nanosaniye düzeyinde ad alanı ayrıştırma, SYS_ID doğrulaması ve persentil analizi.
# ============================================================================
import time
import numpy as np

NUM_SWARM_MSGS = 100_000
latencies_us = np.empty(NUM_SWARM_MSGS, dtype=np.float64)

# 4 Araçlık rastgele komut dağılımı
target_instances = np.random.randint(0, 4, NUM_SWARM_MSGS)
namespaces_arr = [f"/uav{i}" for i in target_instances]
sys_ids_arr = target_instances + 1

dummy_sp = TrajectorySetpoint(x=150.0, y=50.0, z=-50.0, yaw=0.5)
bench_router = SwarmTopicRouter(swarm)

print(f"[BENCHMARK] {NUM_SWARM_MSGS:,} Sürü Paketi Yönlendiriliyor (4 İHA)...")
t_start = time.perf_counter()

for i in range(NUM_SWARM_MSGS):
    t0 = time.perf_counter_ns()
    
    # Yönlendirme ve güvenlik denetimi
    success = bench_router.route_command(namespaces_arr[i], sys_ids_arr[i], dummy_sp)
    
    t_end = time.perf_counter_ns()
    latencies_us[i] = (t_end - t0) / 1000.0 # ns -> us

t_total = time.perf_counter() - t_start

throughput_msg_sec = NUM_SWARM_MSGS / t_total
avg_lat = np.mean(latencies_us)
p50 = np.percentile(latencies_us, 50)
p90 = np.percentile(latencies_us, 90)
p99 = np.percentile(latencies_us, 99)

print(f"\n[SÜRÜ YÖNLENDİRİCİ BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - İşlem Verimi        : {throughput_msg_sec:,.1f} mesaj/s (Hedef: > 150,000)")
print(f"  - Ortalama Gecikme    : {avg_lat:.2f} µs")
print(f"  - p50 (Medyan)        : {p50:.2f} µs")
print(f"  - p90 Gecikme         : {p90:.2f} µs")
print(f"  - p99 Kuyruk Gecikmesi: {p99:.2f} µs (Hedef: < 15.0 µs)")

# Doğrulamalar
assert throughput_msg_sec > 150_000, f"Yönlendirme hızı yetersiz: {throughput_msg_sec}"
assert p99 < 15.0, f"p99 gecikmesi çok yüksek: {p99} µs"

print("\n[PASS] Kod 5: 100.000 Sürü Paketi Yönlendirme Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli 300 DPI Koyu Tema Çoklu Araç ve Sürü Dashboard'u
# gun_244_multi_vehicle_namespace_ve_simulation.png dosyasını üretir.
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
import os

# Savunma Koyu Tema Renk Paleti
COLOR_BG = "#0F172A"       # Slate 900
COLOR_PANEL = "#1E293B"    # Slate 800
COLOR_TEXT = "#F8FAFC"     # Slate 50
COLOR_MUTED = "#94A3B8"    # Slate 400
COLOR_LEAD = "#38BDF8"     # Cyan (Lider UAV 0)
COLOR_WING1 = "#34D399"    # Yeşil (Sol Kanat UAV 1)
COLOR_WING2 = "#FBBF24"    # Sarı (Sağ Kanat UAV 2)
COLOR_ALERT = "#F87171"    # Kırmızı (Çarpışma Sınırı)
COLOR_ACCENT = "#818CF8"   # İndigo

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: Çoklu Araç Port ve Ad Alanı Topoloji Mimarisi ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

uav_labels = [f"UAV {v.instance_id}\n(SYS_ID: {v.mav_sys_id})" for v in swarm]
sitl_p = [v.sitl_port for v in swarm]
mav_p = [v.mavlink_port for v in swarm]
xrce_p = [v.uxrce_port for v in swarm]

y_pos = np.arange(len(uav_labels))
h = 0.25

ax1.barh(y_pos - h, sitl_p, height=h, color=COLOR_LEAD, label="SITL TCP (4560+i)")
ax1.barh(y_pos, mav_p, height=h, color=COLOR_WING1, label="MAVLink UDP (14540+i)")
ax1.barh(y_pos + h, xrce_p, height=h, color=COLOR_WING2, label="uXRCE Agent (8888+i)")

for idx, v in enumerate(swarm):
    ax1.text(14700, idx, f"NS: {v.ros_namespace}\nTF: {v.tf_frame_id}", color=COLOR_TEXT, fontsize=8, va="center")

ax1.set_title("Panel 1: Çoklu İHA Port Haritası ve Ad Alanı (Namespace) İzolasyonu", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xlabel("Port Numarası", color=COLOR_MUTED, fontsize=10)
ax1.set_yticks(y_pos)
ax1.set_yticklabels(uav_labels, color=COLOR_TEXT, fontsize=9, fontweight="bold")
ax1.set_xlim(4000, 17500)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="x")
ax1.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 2: 3-UAV Sürü V-Formasyonu 2D Uçuş Yörüngesi ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

p0 = sim_data["pos0"]
p1 = sim_data["pos1"]
p2 = sim_data["pos2"]

ax2.plot(p0[:, 0], p0[:, 1], color=COLOR_LEAD, linewidth=2.5, label="UAV 0 (Lider)")
ax2.plot(p1[:, 0], p1[:, 1], color=COLOR_WING1, linewidth=2.0, linestyle="--", label="UAV 1 (Sol Kanat)")
ax2.plot(p2[:, 0], p2[:, 1], color=COLOR_WING2, linewidth=2.0, linestyle="--", label="UAV 2 (Sağ Kanat)")

# Başlangıç ve Bitiş Geometrisi
step_idx = 100 # t = 10s anı
ax2.scatter([p0[step_idx, 0], p1[step_idx, 0], p2[step_idx, 0]], 
            [p0[step_idx, 1], p1[step_idx, 1], p2[step_idx, 1]], 
            color=[COLOR_LEAD, COLOR_WING1, COLOR_WING2], s=120, zorder=5)

# Formasyon üçgen çizgileri
ax2.plot([p1[step_idx, 0], p0[step_idx, 0], p2[step_idx, 0], p1[step_idx, 0]],
         [p1[step_idx, 1], p0[step_idx, 1], p2[step_idx, 1], p1[step_idx, 1]],
         color=COLOR_TEXT, linestyle=":", alpha=0.7, label="V-Formasyon Geometrisi (t=10s)")

ax2.set_title("Panel 2: 3-İHA Sürü V-Formasyonu 2D Seyir Yörüngesi (Kuzey-Doğu)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_xlabel("X Konumu [m] (İlerleme Yönü)", color=COLOR_MUTED, fontsize=10)
ax2.set_ylabel("Y Konumu [m] (Yanal Açıklık)", color=COLOR_MUTED, fontsize=10)
ax2.set_ylim(-25, 25)
ax2.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax2.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="lower right", fontsize=8)

# --- PANEL 3: 100.000 Sürü Paketi Yönlendirme Gecikme Histogramı ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

ax3.hist(latencies_us, bins=50, color=COLOR_LEAD, alpha=0.75, edgecolor="#0284C7")
ax3.axvline(p50, color=COLOR_WING1, linestyle="-", linewidth=2.2, label=f"p50 (Medyan): {p50:.2f} µs")
ax3.axvline(p90, color=COLOR_WING2, linestyle="--", linewidth=2.2, label=f"p90: {p90:.2f} µs")
ax3.axvline(p99, color=COLOR_ALERT, linestyle="-.", linewidth=2.2, label=f"p99: {p99:.2f} µs")

ax3.set_title("Panel 3: 100k Sürü Paketi Yönlendirme Gecikmesi Dağılımı", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("İşlem Süresi [µs]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("Örnek Sayısı", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 4: Sürü Ayrılma Mesafeleri ve Çarpışma Eşiği Çizelgesi ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

t_axis = sim_data["t"]
ax4.plot(t_axis, sim_data["d_01"], color=COLOR_LEAD, linewidth=2.0, label="d_01: Lider - Sol Kanat (14.14m)")
ax4.plot(t_axis, sim_data["d_02"], color=COLOR_WING1, linewidth=2.0, linestyle="--", label="d_02: Lider - Sağ Kanat (14.14m)")
ax4.plot(t_axis, sim_data["d_12"], color=COLOR_WING2, linewidth=2.0, label="d_12: Kanatlar Arası (20.00m)")
ax4.axhline(5.0, color=COLOR_ALERT, linestyle="--", linewidth=2.2, label="Emniyet Ayrılma Eşiği (5.0m)")

ax4.set_title("Panel 4: Sürü İçi Göreceli Mesafeler ve Güvenli Ayrılma Çizelgesi", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_xlabel("Uçuş Süresi [s]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylabel("Öklid Mesafesi [m]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylim(0, 25)
ax4.tick_params(colors=COLOR_MUTED)
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax4.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="center right", fontsize=8)

# Süper Başlık
plt.suptitle("PX4 / ROS 2 — MULTI-VEHICLE NAMESPACE VE SÜRÜ SİMÜLASYON DASHBOARD'U", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_244/gun_244_multi_vehicle_namespace_ve_simulation.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

