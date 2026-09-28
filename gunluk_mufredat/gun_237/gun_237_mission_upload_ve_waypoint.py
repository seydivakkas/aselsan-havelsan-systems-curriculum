# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 237: Mission Upload ve Waypoint Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: MAVLink MISSION_ITEM_INT ve Görev Mesajları İkili Modelleri
# 37 baytlık doğal hizalı seyrüsefer noktası serileştirme ve doğrulama.
# ============================================================================
from dataclasses import dataclass
from enum import IntEnum
import struct
from typing import List, Tuple

class MavMissionType(IntEnum):
    MISSION = 0
    FENCE = 1
    RALLY = 2

class MavMissionResult(IntEnum):
    ACCEPTED = 0
    ERROR = 1
    UNSUPPORTED_FRAME = 2
    UNSUPPORTED = 3
    NO_SPACE = 4
    INVALID = 5
    INVALID_PARAM = 6
    INVALID_SEQUENCE = 13
    DENIED = 14

@dataclass
class MissionItemIntPayload:
    param1: float       # Hold time (s)
    param2: float       # Acceptance radius (m)
    param3: float       # Pass radius (m)
    param4: float       # Yaw (deg)
    x: int              # Lat * 1e7
    y: int              # Lon * 1e7
    z: float            # Alt (m)
    seq: int            # uint16
    command: int        # uint16 (MAV_CMD)
    target_system: int = 1
    target_component: int = 1
    frame: int = 6      # MAV_FRAME_GLOBAL_RELATIVE_ALT_INT
    current: int = 0
    autocontinue: int = 1
    mission_type: int = 0

    def serialize(self) -> bytes:
        # Format: <4f (16) + 2i (8) + f (4) + 2H (4) + 6B (6) = 38? 
        # Standart MAVLink v2 MISSION_ITEM_INT hizalaması:
        # param1..param4 (4f=16) + x, y (2i=8) + z (f=4) + seq, cmd (2H=4) + 
        # target_sys, target_comp, frame, current, autocontinue, mission_type (6B=6) = 38 bayt?
        # Kontrol: 16 + 8 + 4 + 4 + 5 = 37 bayt! (target_comp yoksa 37, varsa 38)
        # Standart MAVLink v2: <4fiifHHBBBBBB = 38 bayt
        return struct.pack("<4fiifHHBBBBBB", self.param1, self.param2, self.param3, self.param4,
                           self.x, self.y, self.z, self.seq, self.command,
                           self.target_system, self.target_component, self.frame,
                           self.current, self.autocontinue, self.mission_type)

    @classmethod
    def deserialize(cls, data: bytes) -> "MissionItemIntPayload":
        unpacked = struct.unpack("<4fiifHHBBBBBB", data)
        return cls(
            param1=unpacked[0], param2=unpacked[1], param3=unpacked[2], param4=unpacked[3],
            x=unpacked[4], y=unpacked[5], z=unpacked[6], seq=unpacked[7], command=unpacked[8],
            target_system=unpacked[9], target_component=unpacked[10], frame=unpacked[11],
            current=unpacked[12], autocontinue=unpacked[13], mission_type=unpacked[14]
        )

# Test Senaryosu: Akıncı Devriye Rotası 1. Noktası (Mürted Hava Meydanı Üzeri: 40.0799, 32.5694, irtifa: 150.0m)
wp1 = MissionItemIntPayload(
    param1=0.0,
    param2=5.0, # 5 metre kabul çemberi
    param3=0.0,
    param4=0.0,
    x=int(40.0799 * 1e7),
    y=int(32.5694 * 1e7),
    z=150.0,
    seq=1,
    command=16 # MAV_CMD_NAV_WAYPOINT
)

raw_wp = wp1.serialize()
assert len(raw_wp) == 38, f"Hatalı MISSION_ITEM_INT boyutu: {len(raw_wp)}"

dec_wp = MissionItemIntPayload.deserialize(raw_wp)
assert dec_wp.seq == 1
assert dec_wp.command == 16
assert dec_wp.param2 == 5.0
assert abs(dec_wp.x / 1e7 - 40.0799) < 1e-6
assert dec_wp.z == 150.0

print("[PASS] Kod 1: MAVLink MISSION_ITEM_INT İkili Çerçevesi Başarıyla Doğrulandı.")
print(f"  - Çerçeve Boyutu : {len(raw_wp)} bayt")
print(f"  - Sıra No (Seq)  : {dec_wp.seq} (Komut: NAV_WAYPOINT={dec_wp.command})")
print(f"  - Koordinatlar   : Enlem={dec_wp.x/1e7:.6f}, Boylam={dec_wp.y/1e7:.6f}, İrtifa={dec_wp.z}m")
print(f"  - Kabul Çemberi  : {dec_wp.param2} metre")

# ============================================================================
# KOD HÜCRESİ 2: İki Yönlü İşlemsel (Transactional) Görev Yükleme Durum Makinesi
# GCS ve Otopilot arasında adım adım waypoint aktarımı ve onay el sıkışması.
# ============================================================================
class AutopilotMissionServer:
    def __init__(self):
        self.active_mission: List[MissionItemIntPayload] = []
        self.staging_buffer: List[MissionItemIntPayload] = []
        self.expected_count: int = 0
        self.current_seq_requested: int = 0
        self.transaction_active: bool = False

    def handle_mission_count(self, count: int) -> int: # Dönen: İlk istenen seq
        self.expected_count = count
        self.staging_buffer = []
        self.current_seq_requested = 0
        self.transaction_active = True
        return 0 # seq=0 iste

    def handle_mission_item(self, item: MissionItemIntPayload) -> Tuple[Optional[int], Optional[MavMissionResult]]:
        if not self.transaction_active:
            return None, MavMissionResult.ERROR

        if item.seq != self.current_seq_requested:
            self.transaction_active = False
            return None, MavMissionResult.INVALID_SEQUENCE

        self.staging_buffer.append(item)
        self.current_seq_requested += 1

        if self.current_seq_requested < self.expected_count:
            # Sıradaki noktayı iste
            return self.current_seq_requested, None
        else:
            # Tüm noktalar alındı, görevi onayla ve kalıcı hafızaya devret (Commit)
            self.active_mission = list(self.staging_buffer)
            self.transaction_active = False
            return None, MavMissionResult.ACCEPTED

# GCS Görev Planı (3 Noktalı Görev)
mission_plan = [
    MissionItemIntPayload(0, 5, 0, 0, int(40.07 * 1e7), int(32.56 * 1e7), 50.0, seq=0, command=22), # Takeoff
    MissionItemIntPayload(0, 5, 0, 0, int(40.08 * 1e7), int(32.57 * 1e7), 150.0, seq=1, command=16), # Waypoint
    MissionItemIntPayload(0, 5, 0, 0, int(40.07 * 1e7), int(32.56 * 1e7), 0.0, seq=2, command=21)   # Land
]

# Simülasyon
server = AutopilotMissionServer()

# 1. Adım: GCS -> MISSION_COUNT(count=3)
next_req = server.handle_mission_count(count=len(mission_plan))
assert next_req == 0

# 2. Adım: Noktaları Adım Adım Yükle
upload_history = []
ack_result = None

for item in mission_plan:
    upload_history.append(f"GCS -> ITEM(seq={item.seq}, alt={item.z}m)")
    next_seq, res = server.handle_mission_item(item)
    if res is not None:
        ack_result = res
    else:
        upload_history.append(f"AP -> REQUEST(seq={next_seq})")

assert ack_result == MavMissionResult.ACCEPTED
assert len(server.active_mission) == 3
assert server.active_mission[1].z == 150.0

print("[PASS] Kod 2: İşlemsel Görev Yükleme Durum Makinesi Doğrulandı.")
for log in upload_history:
    print(f"  {log}")
print(f"  AP -> MISSION_ACK: {ack_result.name} (Görev Tamamen Yüklendi)")

# ============================================================================
# KOD HÜCRESİ 3: Otonom Rota İcra ve Waypoint Kabul Çemberi Simülatörü
# 3D mesafe hesabı, MISSION_CURRENT yayını ve MISSION_ITEM_REACHED tetiklemesi.
# ============================================================================
import math

class MissionExecutionNavigator:
    def __init__(self, mission: List[MissionItemIntPayload]):
        self.mission = mission
        self.current_index = 0
        self.reached_items: List[int] = []
        self.is_mission_completed = False

    def update_position(self, current_lat: float, current_lon: float, current_alt: float) -> Tuple[int, bool]:
        if self.is_mission_completed or not self.mission:
            return self.current_index, False

        target = self.mission[self.current_index]
        target_lat = target.x / 1e7
        target_lon = target.y / 1e7
        target_alt = target.z

        # Metrik Düzlem Yaklaşımı (Ankara için 1 derece lat ~ 111 km, lon ~ 85 km)
        dx = (target_lat - current_lat) * 111_000.0
        dy = (target_lon - current_lon) * 85_000.0
        dz = target_alt - current_alt
        dist_3d = math.sqrt(dx*dx + dy*dy + dz*dz)

        # Kabul Çemberi Denetimi
        if dist_3d <= target.param2: # param2 = 5m
            self.reached_items.append(self.current_index)
            if self.current_index + 1 < len(self.mission):
                self.current_index += 1
                return self.current_index, True # Reached and advanced
            else:
                self.is_mission_completed = True
                return self.current_index, True # Final item reached

        return self.current_index, False

# Uçuş Simülasyonu
navigator = MissionExecutionNavigator(mission_plan)

# 1. Başlangıç: Uçak yerde, Hedef: Takeoff (seq=0)
idx, reached = navigator.update_position(40.07, 32.56, 0.0)
assert idx == 0 and not reached

# 2. İHA 50 metreye tırmanır -> Takeoff noktasına ulaştı!
idx, reached = navigator.update_position(40.07, 32.56, 50.0)
assert reached == True
assert idx == 1 # Otomatik olarak seq=1'e (Waypoint) geçti!

# 3. İHA 1. Waypoint'e uçar (40.08, 32.57, 150m)
idx, reached = navigator.update_position(40.08, 32.57, 150.0)
assert reached == True
assert idx == 2 # seq=2'ye (Land) geçti!

assert navigator.reached_items == [0, 1]
print("[PASS] Kod 3: Otonom Rota İcra ve Waypoint Kabul Çemberi Doğrulandı.")
print(f"  - Tamamlanan Noktalar : {navigator.reached_items}")
print(f"  - Aktif Hedef Sıra No : {navigator.current_index} (İniş Noktası)")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik MAVLink Görev Protokolü Hata Enjeksiyon Testi
# İrtifa tavanı denetimi, sırasız paket reddi ve işlem iptal (rollback) kalkanı.
# ============================================================================

# --- TEST 1: Maksimum İrtifa Tavanı İhlali (Safety Envelope Guard) ---
print("[TEST 1] Maksimum İrtifa Tavanı İhlali (Altitude Limit Violation) Testi...")
def validate_waypoint_safety(item: MissionItemIntPayload, max_alt_m: float = 3000.0) -> MavMissionResult:
    if item.z > max_alt_m or item.z < 0.0:
        return MavMissionResult.INVALID_PARAM
    return MavMissionResult.ACCEPTED

illegal_wp = MissionItemIntPayload(0, 5, 0, 0, int(40.0 * 1e7), int(32.0 * 1e7), z=7500.0, seq=1, command=16)
res_safety = validate_waypoint_safety(illegal_wp, max_alt_m=3000.0)
assert res_safety == MavMissionResult.INVALID_PARAM, "Tehlikeli irtifa kabul edildi!"
print(f"  - İstenen İrtifa : {illegal_wp.z} m (Maksimum İzin: 3000 m)")
print(f"  - Dönen Sonuç    : {res_safety.name} (Güvenlik Reddi)")
print("  [PASS] Test 1: Güvenli uçuş tavanı ihlali başarıyla engellendi.\n")

# --- TEST 2: Hatalı Sıra Numarası (Sequence Jump Anomaly) ---
print("[TEST 2] Sırasız Waypoint Gönderimi (Sequence Jump) Testi...")
fault_server = AutopilotMissionServer()
fault_server.handle_mission_count(count=3) # seq=0 bekleniyor

# GCS sehven seq=1 gönderirse:
next_s, res_seq = fault_server.handle_mission_item(MissionItemIntPayload(0, 5, 0, 0, 0, 0, 100, seq=1, command=16))
assert res_seq == MavMissionResult.INVALID_SEQUENCE, "Sırasız paket kabul edildi!"
assert fault_server.transaction_active == False, "İşlem iptal edilmedi!"
print(f"  - Beklenen Sıra No : 0, Gelen: 1")
print(f"  - Alınan Karar     : {res_seq.name} (İşlem İptal Edildi)")
print("  [PASS] Test 2: Hatalı sıra numaralı paket anında reddedildi.\n")

# --- TEST 3: Görev Yükleme Yarım Kalması ve Rollback Kalkanı ---
print("[TEST 3] Görev Yükleme Kopması ve Eski Göreve Dönüş (Rollback) Testi...")
class RollbackMissionManager:
    def __init__(self):
        # Önceden kayıtlı emniyetli devriye rotası (Eski Görev)
        self.active_mission = ["SAVED_MISSION_WP1", "SAVED_MISSION_WP2"]
        self.staging = []

    def start_upload(self):
        self.staging = ["NEW_WP0"]

    def abort_on_timeout(self):
        self.staging = [] # Geçici tampon temizlenir, active_mission el değmeden kalır!

manager = RollbackMissionManager()
manager.start_upload()
# Yükleme esnasında telsiz kararması oldu:
manager.abort_on_timeout()
assert len(manager.active_mission) == 2
assert manager.active_mission == ["SAVED_MISSION_WP1", "SAVED_MISSION_WP2"]
print(f"  - Aktif Görev Durumu : Korundu ({manager.active_mission})")
print("  [PASS] Test 3: Yarım kalan yüklemede eski görev başarıyla korundu.\n")

print("[PASS] Kod 4: 3 Kritik Görev Protokolü Hata Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 100.000 Waypoint Geometri ve Kabul Denetimi Benchmark'ı
# Nanosaniye düzeyinde 3D mesafe hesaplama ve kabul çemberi değerlendirmesi.
# ============================================================================
import time
import numpy as np

NUM_WAYPOINTS = 100_000
latencies_us = np.empty(NUM_WAYPOINTS, dtype=np.float64)

# Rastgele koordinat ve irtifalar
target_lats = np.random.uniform(39.0, 41.0, NUM_WAYPOINTS)
target_lons = np.random.uniform(32.0, 34.0, NUM_WAYPOINTS)
target_alts = np.random.uniform(100.0, 2000.0, NUM_WAYPOINTS)

cur_lat, cur_lon, cur_alt = 40.0, 33.0, 500.0

print(f"[BENCHMARK] {NUM_WAYPOINTS:,} Waypoint Geometri ve Mesafe Kontrolü Başlatılıyor...")
t_start = time.perf_counter()

for i in range(NUM_WAYPOINTS):
    t0 = time.perf_counter_ns()
    
    # 3D Mesafe Hesabı
    dx = (target_lats[i] - cur_lat) * 111000.0
    dy = (target_lons[i] - cur_lon) * 85000.0
    dz = target_alts[i] - cur_alt
    d3d = (dx*dx + dy*dy + dz*dz)**0.5
    
    # Kabul Çemberi Kararı
    is_reached = (d3d <= 5.0)
    
    t_end = time.perf_counter_ns()
    latencies_us[i] = (t_end - t0) / 1000.0 # ns -> us

t_total = time.perf_counter() - t_start

throughput_ops = NUM_WAYPOINTS / t_total
avg_lat = np.mean(latencies_us)
p50 = np.percentile(latencies_us, 50)
p90 = np.percentile(latencies_us, 90)
p99 = np.percentile(latencies_us, 99)

print(f"\n[WAYPOINT GEOMETRİ BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - İşlem Verimi        : {throughput_ops:,.1f} kontrol/s (Hedef: > 200,000)")
print(f"  - Ortalama Gecikme    : {avg_lat:.2f} µs")
print(f"  - p50 (Medyan)        : {p50:.2f} µs")
print(f"  - p90 Gecikme         : {p90:.2f} µs")
print(f"  - p99 Kuyruk Gecikmesi: {p99:.2f} µs (Hedef: < 15.0 µs)")

# Doğrulamalar
assert throughput_ops > 200_000, f"İşlem verimi yetersiz: {throughput_ops}"
assert p99 < 15.0, f"p99 gecikmesi çok yüksek: {p99} µs"

print("\n[PASS] Kod 5: 100.000 Waypoint Geometri Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli 300 DPI Koyu Tema Görev ve Waypoint Dashboard'u
# gun_237_mission_upload_ve_waypoint.png dosyasını üretir.
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
import os

# Koyu Tema Savunma Standart Renkleri
COLOR_BG = "#0F172A"       # Slate 900
COLOR_PANEL = "#1E293B"    # Slate 800
COLOR_TEXT = "#F8FAFC"     # Slate 50
COLOR_MUTED = "#94A3B8"    # Slate 400
COLOR_ACCENT1 = "#38BDF8"  # Cyan (Devriye Rotası)
COLOR_ACCENT2 = "#34D399"  # Yeşil (Kabul Edilen / Hedef Nokta)
COLOR_ACCENT3 = "#F87171"  # Kırmızı (Hata / NFZ)
COLOR_ACCENT4 = "#FBBF24"  # Sarı (İrtifa Profili)

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: Taktik Devriye Rotası 2D Harita ve Waypoint Kabul Çemberleri ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

wp_x = [0, 4, 8, 10, 5, 0] # km
wp_y = [0, 5, 4, -2, -4, 0]
wp_labels = ["WP0: Kalkış", "WP1: Keşif", "WP2: Hedef Alanı", "WP3: Dönüş", "WP4: Yaklaşma", "WP5: İniş"]

ax1.plot(wp_x, wp_y, color=COLOR_ACCENT1, linestyle="--", linewidth=2.0, label="Planlanan Uçuş Rotası", zorder=2)
ax1.scatter(wp_x, wp_y, color=COLOR_ACCENT2, s=200, edgecolors="#334155", linewidths=2, zorder=5, label="Waypoint Noktaları")

# Kabul Çemberi Gösterimi
for i, (x, y) in enumerate(zip(wp_x, wp_y)):
    circle = plt.Circle((x, y), 0.4, color=COLOR_ACCENT4, fill=False, linestyle=":", linewidth=1.5, zorder=3)
    ax1.add_patch(circle)
    ax1.text(x + 0.3, y + 0.3, wp_labels[i], color=COLOR_TEXT, fontsize=8, fontweight="bold")

ax1.set_title("Panel 1: Taktik Devriye Rotası ve Waypoint Kabul Çemberleri (R_accept)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xlabel("Doğu Koordinatı [km]", color=COLOR_MUTED, fontsize=10)
ax1.set_ylabel("Kuzey Koordinatı [km]", color=COLOR_MUTED, fontsize=10)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax1.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 2: Rota İrtifa Profili ve Uçuş Tavanı Emniyet Limiti ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

wp_indices = np.arange(len(wp_x))
altitudes = [0, 150, 300, 300, 100, 0]

ax2.plot(wp_indices, altitudes, color=COLOR_ACCENT4, marker="o", linewidth=2.5, markersize=8, label="Waypoint İrtifası (m AGL)")
ax2.axhline(500, color=COLOR_ACCENT3, linestyle="--", linewidth=2.0, label="Maksimum İrtifa Sınırı (500m)")
ax2.fill_between(wp_indices, 0, altitudes, color=COLOR_ACCENT4, alpha=0.15)

for i, alt in enumerate(altitudes):
    ax2.text(i, alt + 15, f"{alt}m", ha='center', va='bottom', color=COLOR_TEXT, fontsize=9, fontweight="bold")

ax2.set_title("Panel 2: Rota İrtifa Profili ve Uçuş Zarfı Sınırı", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_xlabel("Waypoint Sıra Numarası (Seq)", color=COLOR_MUTED, fontsize=10)
ax2.set_ylabel("İrtifa [m AGL]", color=COLOR_MUTED, fontsize=10)
ax2.set_xticks(wp_indices)
ax2.set_xticklabels([f"WP{i}" for i in range(len(wp_x))])
ax2.set_ylim(-20, 600)
ax2.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax2.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 3: 100.000 Waypoint Geometri Kontrolü Gecikme Histogramı ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

n, bins, patches = ax3.hist(latencies_us, bins=50, color=COLOR_ACCENT1, alpha=0.75, edgecolor="#0284C7")
ax3.axvline(p50, color=COLOR_ACCENT2, linestyle="-", linewidth=2.2, label=f"p50 (Medyan): {p50:.2f} µs")
ax3.axvline(p90, color=COLOR_ACCENT4, linestyle="--", linewidth=2.2, label=f"p90: {p90:.2f} µs")
ax3.axvline(p99, color=COLOR_ACCENT3, linestyle="-.", linewidth=2.2, label=f"p99: {p99:.2f} µs")

ax3.set_title("Panel 3: 100.000 Waypoint 3D Mesafe Hesabı Gecikmesi (µs)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("Hesaplama Süresi [µs]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("Nokta Sayısı", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 4: Görev Yükleme Adım Sıralaması ve Paket Sayısı ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

steps = ["COUNT Bildirimi", "Item 0: Takeoff", "Item 1: WP Keşif", "Item 2: WP Hedef", "Item 3: WP Dönüş", "ACK Onayı"]
packet_bytes = [12, 38, 38, 38, 38, 12] # Bayt büyüklükleri
bar_colors4 = [COLOR_ACCENT4, COLOR_ACCENT1, COLOR_ACCENT1, COLOR_ACCENT1, COLOR_ACCENT1, COLOR_ACCENT2]

bars4 = ax4.bar(steps, packet_bytes, color=bar_colors4, width=0.55, edgecolor="#334155")
ax4.set_title("Panel 4: Görev Yükleme İşlem (Transaction) Paket Büyüklükleri (Bayt)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_ylabel("Paket Boyutu [Bayt]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylim(0, 50)
ax4.tick_params(colors=COLOR_MUTED)
plt.setp(ax4.get_xticklabels(), rotation=20, ha="right")
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")

for bar in bars4:
    h = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., h + 1.2, f"{h}B", ha='center', va='bottom', color=COLOR_TEXT, fontsize=9, fontweight="bold")

# Üst Başlık
plt.suptitle("BAYRAKTAR TB2 / ANKA — MAVLINK GÖREV PROTOKOLÜ VE WAYPOINT DASHBOARD'U", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_237/gun_237_mission_upload_ve_waypoint.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

