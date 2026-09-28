# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 232: MAVLink System ve Component ID Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: MAVLink Adresleme ve Hedefli Başlık Çerçevesi Modeli
# SYS_ID / COMP_ID standartları ve iki katmanlı komut yönlendirme paketi.
# ============================================================================
from dataclasses import dataclass, field
from enum import IntEnum
import struct
from typing import Optional, Tuple, Dict, List

class MavComponent(IntEnum):
    ALL = 0
    AUTOPILOT1 = 1
    TELEMETRY_RADIO = 68
    CAMERA = 100
    CAMERA2 = 101
    GIMBAL = 154
    COMPANION = 191
    OBSTACLE_AVOIDANCE = 196
    WARHEAD = 195

@dataclass
class MavlinkRoutingHeader:
    magic: int = 0xFD          # MAVLink v2
    payload_len: int = 0
    incompat_flags: int = 0
    compat_flags: int = 0
    seq: int = 0
    src_sys_id: int = 1        # Gönderen Sistem (Uçak No)
    src_comp_id: int = 1       # Gönderen Bileşen (Otopilot)
    msg_id: int = 0            # 24-bit mesaj kimliği

@dataclass
class CommandLongPayload:
    target_system: int         # Hedef Sistem (0 = Broadcast)
    target_component: int      # Hedef Bileşen (0 = Broadcast)
    command: int               # MAV_CMD (uint16)
    confirmation: int          # uint8
    params: List[float]        # 7 adet float parametre (param1..param7)

    def serialize(self) -> bytes:
        # Format: 7f (params), H (command), B (target_sys), B (target_comp), B (confirmation) = 28 + 2 + 1 + 1 + 1 = 33 bayt
        return struct.pack("<7fHBBB", *self.params, self.command, self.target_system, self.target_component, self.confirmation)

    @classmethod
    def deserialize(cls, data: bytes) -> "CommandLongPayload":
        p1, p2, p3, p4, p5, p6, p7, cmd, t_sys, t_comp, conf = struct.unpack("<7fHBBB", data)
        return cls(
            target_system=t_sys, target_component=t_comp,
            command=cmd, confirmation=conf,
            params=[p1, p2, p3, p4, p5, p6, p7]
        )

# Test ve Doğrulama
# GCS (SYS=255, COMP=0) -> İHA-2 Otopilotuna (SYS=2, COMP=1) ARM Komutu (#400)
cmd_arm = CommandLongPayload(
    target_system=2,
    target_component=MavComponent.AUTOPILOT1,
    command=400, # MAV_CMD_COMPONENT_ARM_DISARM
    confirmation=0,
    params=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] # param1 = 1.0 (ARM)
)
raw_cmd = cmd_arm.serialize()
assert len(raw_cmd) == 33, f"CommandLong boyutu hatalı: {len(raw_cmd)}"

decoded_cmd = CommandLongPayload.deserialize(raw_cmd)
assert decoded_cmd.target_system == 2
assert decoded_cmd.target_component == MavComponent.AUTOPILOT1
assert decoded_cmd.command == 400
assert decoded_cmd.params[0] == 1.0

# GCS (SYS=255, COMP=0) -> İHA-1 Gimbal'ına (SYS=1, COMP=154) Açı Komutu (#205)
cmd_gimbal = CommandLongPayload(
    target_system=1,
    target_component=MavComponent.GIMBAL,
    command=205, # MAV_CMD_DO_MOUNT_CONTROL
    confirmation=0,
    params=[-45.0, 0.0, 90.0, 0.0, 0.0, 0.0, 2.0] # Pitch=-45 deg, Yaw=90 deg
)
raw_gimbal = cmd_gimbal.serialize()
decoded_gimbal = CommandLongPayload.deserialize(raw_gimbal)
assert decoded_gimbal.target_system == 1
assert decoded_gimbal.target_component == MavComponent.GIMBAL
assert decoded_gimbal.params[0] == -45.0

print(f"[PASS] Kod 1: MAVLink System & Component ID Adresleme Modeli Doğrulandı.")
print(f"  - ARM Komutu Hedefi    : SYS={decoded_cmd.target_system}, COMP={MavComponent(decoded_cmd.target_component).name} ({decoded_cmd.target_component})")
print(f"  - Gimbal Komutu Hedefi : SYS={decoded_gimbal.target_system}, COMP={MavComponent(decoded_gimbal.target_component).name} ({decoded_gimbal.target_component})")
print(f"  - Komut Çerçeve Boyutu : {len(raw_cmd)} bayt (33 bayt standart MAVLink COMMAND_LONG)")

# ============================================================================
# KOD HÜCRESİ 2: Çok Portlu Akıllı MAVLink Yönlendirici (Smart Router)
# GCS, Otopilot, Companion ve Telsiz portları arasında akıllı paket filtreleme.
# ============================================================================
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

@dataclass
class RoutedPacket:
    src_sys: int
    src_comp: int
    target_sys: int
    target_comp: int
    msg_id: int
    payload_str: str

class MavlinkSmartRouter:
    def __init__(self, my_sys_id: int):
        self.my_sys_id = my_sys_id
        # Portlar: 'RADIO', 'AUTOPILOT', 'COMPANION', 'GCS'
        self.port_routes: Dict[int, str] = {} # sys_id -> port_name
        self.local_components: Set[int] = {
            MavComponent.AUTOPILOT1,
            MavComponent.COMPANION,
            MavComponent.GIMBAL
        }
        self.packet_log: List[Tuple[str, str, RoutedPacket]] = [] # (in_port, out_port, pkt)

    def register_route(self, sys_id: int, port_name: str):
        self.port_routes[sys_id] = port_name

    def route_packet(self, in_port: str, pkt: RoutedPacket) -> List[str]:
        forwarded_ports = []

        # 1. KURAL: Broadcast Mesajı (target_sys == 0)
        if pkt.target_sys == 0:
            all_ports = {'RADIO', 'AUTOPILOT', 'COMPANION', 'GCS'}
            # Gelen port hariç tüm portlara ilet
            for p in all_ports:
                if p != in_port:
                    forwarded_ports.append(p)
                    self.packet_log.append((in_port, p, pkt))
            return forwarded_ports

        # 2. KURAL: Kendi Sistemimiz mi? (target_sys == MY_SYS_ID)
        if pkt.target_sys == self.my_sys_id:
            # Yerel bileşen yönlendirmesi
            if pkt.target_comp == 0 or pkt.target_comp == MavComponent.AUTOPILOT1:
                forwarded_ports.append('AUTOPILOT')
                self.packet_log.append((in_port, 'AUTOPILOT', pkt))
            elif pkt.target_comp == MavComponent.COMPANION:
                forwarded_ports.append('COMPANION')
                self.packet_log.append((in_port, 'COMPANION', pkt))
            elif pkt.target_comp == MavComponent.GIMBAL:
                forwarded_ports.append('GIMBAL')
                self.packet_log.append((in_port, 'GIMBAL', pkt))
            return forwarded_ports

        # 3. KURAL: Başka Bir Sistem (target_sys != MY_SYS_ID)
        out_port = self.port_routes.get(pkt.target_sys, 'RADIO')
        if out_port != in_port:
            forwarded_ports.append(out_port)
            self.packet_log.append((in_port, out_port, pkt))
            
        return forwarded_ports

# Simülasyon Senaryosu (İHA 1 Router'ı)
uav1_router = MavlinkSmartRouter(my_sys_id=1)
uav1_router.register_route(sys_id=255, port_name='GCS')
uav1_router.register_route(sys_id=2, port_name='RADIO')

# 1. GCS'ten İHA-1 Otopilotuna Özel Komut
pkt1 = RoutedPacket(src_sys=255, src_comp=0, target_sys=1, target_comp=1, msg_id=76, payload_str="ARM_UAV1")
dest1 = uav1_router.route_packet(in_port='GCS', pkt=pkt1)
assert dest1 == ['AUTOPILOT'], f"İHA-1 Otopilotuna yönlendirilemedi: {dest1}"

# 2. GCS'ten İHA-2'ye Komut (İHA-1 telsiz üzerinden duyar, dışarı yönlendirir)
pkt2 = RoutedPacket(src_sys=255, src_comp=0, target_sys=2, target_comp=1, msg_id=76, payload_str="ARM_UAV2")
dest2 = uav1_router.route_packet(in_port='GCS', pkt=pkt2)
assert dest2 == ['RADIO'], f"İHA-2 komutu telsize yönlendirilemedi: {dest2}"

# 3. İHA-1 Otopilotundan Herkese Broadcast Telemetri (target_sys = 0)
pkt_bc = RoutedPacket(src_sys=1, src_comp=1, target_sys=0, target_comp=0, msg_id=30, payload_str="ATTITUDE_BROADCAST")
dest_bc = uav1_router.route_packet(in_port='AUTOPILOT', pkt=pkt_bc)
assert 'GCS' in dest_bc and 'RADIO' in dest_bc and 'COMPANION' in dest_bc
assert 'AUTOPILOT' not in dest_bc, "Yankı döngüsü (Echo loop) oluştu!"

print(f"[PASS] Kod 2: Akıllı MAVLink Çok Portlu Yönlendirici Doğrulandı.")
print(f"  - İHA-1 Yerel Komut Hedefi     : {dest1} (Doğrudan otopilota teslim)")
print(f"  - İHA-2 Hedefli Paket Yolu    : {dest2} (Telsiz ağına aktarıldı)")
print(f"  - Broadcast Telemetri Dağıtımı: {dest_bc} (Yankısız tüm portlara dağıtıldı)")

# ============================================================================
# KOD HÜCRESİ 3: Sürü İHA Çapraz Komut İzolasyonu ve Güvenlik Testi
# Paylaşımlı telsiz ortamında SYS_ID filtreleme ve yanlış araç komut kalkanı.
# ============================================================================
class KarguAutopilotNode:
    def __init__(self, sys_id: int):
        self.sys_id = sys_id
        self.comp_id = MavComponent.AUTOPILOT1
        self.is_armed = False
        self.target_locked = False
        self.accepted_commands_count = 0
        self.ignored_commands_count = 0

    def receive_command(self, cmd: CommandLongPayload) -> Optional[int]:
        # 1. KONTROL: Sistem Kimliği Denetimi
        if cmd.target_system != 0 and cmd.target_system != self.sys_id:
            self.ignored_commands_count += 1
            return None # Bize ait değil, sessizce düşür (ACK gönderme!)

        # 2. KONTROL: Bileşen Kimliği Denetimi
        if cmd.target_component != 0 and cmd.target_component != self.comp_id:
            self.ignored_commands_count += 1
            return None # Otopilota ait değil (Gimbal veya Kameraya ait)

        # 3. Komutu Yürüt
        self.accepted_commands_count += 1
        if cmd.command == 400: # ARM
            self.is_armed = bool(cmd.params[0] == 1.0)
            return 0 # MAV_RESULT_ACCEPTED
        elif cmd.command == 2000: # Özel Mühimmat Kilidi
            self.target_locked = True
            return 0
            
        return 3 # MAV_RESULT_UNSUPPORTED

# Sürü Oluşturma
uav1 = KarguAutopilotNode(sys_id=1) # Kargu-1
uav2 = KarguAutopilotNode(sys_id=2) # Kargu-2

# GCS'ten Yalnızca Kargu-2'ye Yönelik Mühimmat ve Dalış Komutu (#400 ARM + #2000 LOCK)
cmd_arm_uav2 = CommandLongPayload(target_system=2, target_component=1, command=400, confirmation=0, params=[1.0, 0,0,0,0,0,0])
cmd_lock_uav2 = CommandLongPayload(target_system=2, target_component=1, command=2000, confirmation=0, params=[1.0, 0,0,0,0,0,0])

# Telsiz hattından iki araca da paket aynı anda ulaşır (Shared RF Broadcast)
res1_uav1 = uav1.receive_command(cmd_arm_uav2)
res1_uav2 = uav2.receive_command(cmd_arm_uav2)

res2_uav1 = uav1.receive_command(cmd_lock_uav2)
res2_uav2 = uav2.receive_command(cmd_lock_uav2)

# Doğrulamalar
# Kargu-2 komutları kabul etmiş olmalı
assert res1_uav2 == 0 and res2_uav2 == 0, "Kargu-2 kendi komutlarını kabul etmedi!"
assert uav2.is_armed == True, "Kargu-2 arm olamadı!"
assert uav2.target_locked == True, "Kargu-2 hedefe kilitlenemedi!"
assert uav2.accepted_commands_count == 2

# Kargu-1 komutları tamamen yok saymış ve standby kalmış olmalı
assert res1_uav1 is None and res2_uav1 is None, "Kargu-1 başka aracın komutuna ACK döndü (İhlal)!"
assert uav1.is_armed == False, "Kargu-1 yanlışlıkla ARM oldu (Feci Emniyet Hatası)!"
assert uav1.target_locked == False
assert uav1.ignored_commands_count == 2
assert uav1.accepted_commands_count == 0

print(f"[PASS] Kod 3: Sürü İHA Çapraz Komut İzolasyonu Başarıyla Doğrulandı.")
print(f"  - Kargu-2 (SYS=2) Durumu : ARMED=%s | KİLİTLİ=%s | Kabul Edilen: %d" % 
      (uav2.is_armed, uav2.target_locked, uav2.accepted_commands_count))
print(f"  - Kargu-1 (SYS=1) Durumu : ARMED=%s | KİLİTLİ=%s | Reddedilen: %d (Sessizce İhmal)" % 
      (uav1.is_armed, uav1.target_locked, uav1.ignored_commands_count))

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik MAVLink Adresleme ve Güvenlik Hata Enjeksiyon Testi
# Mükerrer SYS_ID tespiti, olmayan bileşen reddi ve broadcast disarm kalkanı.
# ============================================================================

# --- HATA TESTİ 1: Mükerrer Sistem Kimliği (Duplicate SYS_ID Detection) ---
print("[TEST 1] Mükerrer Sistem Kimliği Çatışması (System ID Conflict) Testi...")
class DuplicateSysIdDetector:
    def __init__(self):
        self.node_ip_map: Dict[int, str] = {} # sys_id -> ip_address
        self.conflict_detected = False
        self.conflict_sys_id = None

    def process_heartbeat(self, sys_id: int, source_ip: str) -> bool:
        if sys_id in self.node_ip_map:
            if self.node_ip_map[sys_id] != source_ip:
                self.conflict_detected = True
                self.conflict_sys_id = sys_id
                return False # ÇATIŞMA!
        else:
            self.node_ip_map[sys_id] = source_ip
        return True

detector = DuplicateSysIdDetector()
assert detector.process_heartbeat(sys_id=1, source_ip="192.168.1.101") == True
# İkinci bir uçak yanlışlıkla aynı SYS_ID (1) ile farklı IP'den geldi:
conflict_res = detector.process_heartbeat(sys_id=1, source_ip="192.168.1.102")
assert conflict_res == False, "Çakışan SYS_ID yakalanamadı!"
assert detector.conflict_detected == True
print(f"  - Kayıtlı Araç IP : 192.168.1.101 (SYS_ID: 1)")
print(f"  - Çakışan Araç IP : 192.168.1.102 (SYS_ID: 1)")
print(f"  - Alarm Durumu    : DUPLICATE_SYS_ID_ALARM (Güvenlik Kalkanı Devrede)")
print("  [PASS] Test 1: Mükerrer SYS_ID çatışması başarıyla tespit edildi.\n")

# --- HATA TESTİ 2: Olmayan Bileşen Reddi (Component Not Found) ---
print("[TEST 2] Uçakta Mevcut Olmayan Alt Bileşene Komut Gönderimi Testi...")
def handle_target_component_check(target_comp: int, available_components: List[int]) -> int:
    if target_comp not in available_components and target_comp != 0:
        return 4 # MAV_RESULT_FAILED (Bileşen Yok)
    return 0 # MAV_RESULT_ACCEPTED

available_comps = [MavComponent.AUTOPILOT1, MavComponent.COMPANION]
# Olmayan Lazer Mesafe Sensörüne (COMP: 196) komut basılırsa:
res_comp = handle_target_component_check(target_comp=196, available_components=available_comps)
assert res_comp == 4, "Olmayan bileşene gönderilen komut reddedilemedi!"
print(f"  - Mevcut Bileşenler   : {[c.name for c in available_comps]}")
print(f"  - İstenen Bileşen     : OBSTACLE_AVOIDANCE (COMP: 196)")
print(f"  - Dönen MAVLink ACK   : MAV_RESULT_FAILED (Hata Kodu: 4)")
print("  [PASS] Test 2: Olmayan bileşene yönlendirme güvenle engellendi.\n")

# --- HATA TESTİ 3: Tehlikeli Genel Yayın DISARM Engeli (Broadcast Disarm Guard) ---
print("[TEST 3] Havadayken Genel Yayın DISARM Kalkanı (Broadcast Disarm Guard)...")
def execute_disarm_guard(is_in_air: bool, target_sys: int) -> int:
    # Kural: Havada iken broadcast (target_sys == 0) ile disarm KESİNLİKLE YASAKTIR!
    if is_in_air and target_sys == 0:
        return 2 # MAV_RESULT_DENIED (Emniyet Reddi)
    return 0 # MAV_RESULT_ACCEPTED

# Havada uçuş sırasında yanlışlıkla target_system=0 ile gelen Disarm isteği
guard_res = execute_disarm_guard(is_in_air=True, target_sys=0)
assert guard_res == 2, "Havadaki filoyu öldüren broadcast disarm kabul edildi (Feci Hata)!"
print("  - Hava Aracı Durumu   : HAVADA UÇUŞTA (IN_AIR=True)")
print("  - Komut Hedefi        : target_system = 0 (Tüm Araçlar / Broadcast)")
print("  - Alınan Karar        : MAV_RESULT_DENIED (Komut Kesin Olarak Reddedildi)")
print("  [PASS] Test 3: Havadaki filoyu çökertebilecek broadcast disarm engellendi.\n")

print("[PASS] Kod 4: 3 Kritik MAVLink Adresleme ve Yönlendirme Hata Testi Başarılı.")

# ============================================================================
# KOD HÜCRESİ 5: 100.000 Paketlik MAVLink Akıllı Yönlendirici Benchmark'ı
# Çok portlu paket yönlendirme verimi, O(1) tablo erişimi ve p99 analizi.
# ============================================================================
import time
import numpy as np

NUM_ROUTED_PACKETS = 100_000
latencies_us = np.empty(NUM_ROUTED_PACKETS, dtype=np.float64)

benchmark_router = MavlinkSmartRouter(my_sys_id=1)
benchmark_router.register_route(sys_id=255, port_name='GCS')
benchmark_router.register_route(sys_id=2, port_name='RADIO')
benchmark_router.register_route(sys_id=3, port_name='RADIO')

test_pkts = [
    RoutedPacket(src_sys=255, src_comp=0, target_sys=1, target_comp=1, msg_id=76, payload_str="LOCAL_AP"),
    RoutedPacket(src_sys=255, src_comp=0, target_sys=2, target_comp=1, msg_id=76, payload_str="EXTERNAL_UAV2"),
    RoutedPacket(src_sys=1, src_comp=1, target_sys=0, target_comp=0, msg_id=30, payload_str="BROADCAST_TELEMETRY"),
    RoutedPacket(src_sys=255, src_comp=0, target_sys=1, target_comp=154, msg_id=205, payload_str="LOCAL_GIMBAL")
]

print(f"[BENCHMARK] {NUM_ROUTED_PACKETS:,} MAVLink Paketi Yönlendiriliyor...")
t_start = time.perf_counter()

for i in range(NUM_ROUTED_PACKETS):
    pkt = test_pkts[i % 4]
    t0 = time.perf_counter_ns()
    
    # Yönlendirme Kararı
    ports = benchmark_router.route_packet(in_port='GCS', pkt=pkt)
    
    t_end = time.perf_counter_ns()
    latencies_us[i] = (t_end - t0) / 1000.0 # ns -> us

t_total = time.perf_counter() - t_start

throughput_pkt_per_sec = NUM_ROUTED_PACKETS / t_total
avg_lat = np.mean(latencies_us)
p50 = np.percentile(latencies_us, 50)
p90 = np.percentile(latencies_us, 90)
p99 = np.percentile(latencies_us, 99)

print(f"\n[MAVLINK ROUTER BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - Yönlendirme Hızı    : {throughput_pkt_per_sec:,.1f} paket/s (Hedef: > 150,000)")
print(f"  - Ortalama Gecikme    : {avg_lat:.2f} µs")
print(f"  - p50 (Medyan)        : {p50:.2f} µs")
print(f"  - p90 Gecikme         : {p90:.2f} µs")
print(f"  - p99 Kuyruk Gecikmesi: {p99:.2f} µs (Hedef: < 15.0 µs)")

# Doğrulamalar
assert throughput_pkt_per_sec > 150_000, f"Yönlendirme hızı yetersiz: {throughput_pkt_per_sec}"
assert p99 < 15.0, f"p99 gecikmesi çok yüksek: {p99} µs"

print("\n[PASS] Kod 5: 100.000 Paketlik Yönlendirme Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli 300 DPI Koyu Tema MAVLink Adresleme Dashboard'u
# gun_232_mavlink_system_component_id.png dosyasını üretir.
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
import os

# Koyu Tema Savunma Standart Renkleri
COLOR_BG = "#0F172A"       # Slate 900
COLOR_PANEL = "#1E293B"    # Slate 800
COLOR_TEXT = "#F8FAFC"     # Slate 50
COLOR_MUTED = "#94A3B8"    # Slate 400
COLOR_ACCENT1 = "#38BDF8"  # Cyan (Unicast Yönlendirme)
COLOR_ACCENT2 = "#34D399"  # Yeşil (Kabul Edilen / Sağlıklı)
COLOR_ACCENT3 = "#F87171"  # Kırmızı (Filtrelenen / Hata)
COLOR_ACCENT4 = "#FBBF24"  # Sarı (Broadcast)

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: Sürü İHA SYS_ID Ağ Dağılımı ve Paket Akış Matrisi ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

nodes = ["GCS\n(SYS:255)", "Lider Akıncı\n(SYS:10)", "Kargu-1\n(SYS:1)", "Kargu-2\n(SYS:2)", "Kargu-3\n(SYS:3)"]
x_pos = [0, 3, 6, 6, 6]
y_pos = [2, 2, 4, 2, 0]
colors = ["#C084FC", COLOR_ACCENT1, COLOR_ACCENT2, COLOR_ACCENT4, COLOR_ACCENT2]

ax1.scatter(x_pos, y_pos, s=1200, color=colors, edgecolors="#334155", linewidths=2, zorder=5)

for i, txt in enumerate(nodes):
    ax1.text(x_pos[i], y_pos[i], txt, ha='center', va='center', color=COLOR_TEXT, fontsize=8, fontweight="bold", zorder=6)

# Bağlantı Çizgileri
ax1.annotate("", xy=(3, 2), xytext=(0, 2), arrowprops=dict(arrowstyle="<->", color=COLOR_MUTED, lw=2))
ax1.annotate("", xy=(6, 4), xytext=(3, 2), arrowprops=dict(arrowstyle="->", color=COLOR_MUTED, lw=1.5, ls="--"))
ax1.annotate("", xy=(6, 2), xytext=(3, 2), arrowprops=dict(arrowstyle="->", color=COLOR_ACCENT4, lw=2.5)) # Kargu-2'ye aktif komut
ax1.annotate("", xy=(6, 0), xytext=(3, 2), arrowprops=dict(arrowstyle="->", color=COLOR_MUTED, lw=1.5, ls="--"))

ax1.text(4.5, 2.3, "Hedefli Komut (SYS:2)", color=COLOR_ACCENT4, fontsize=9, fontweight="bold")
ax1.set_title("Panel 1: Sürü İHA Taktik Veri Bağı ve SYS_ID Yönlendirme Topolojisi", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xlim(-1.5, 7.5)
ax1.set_ylim(-1, 5)
ax1.axis("off")

# --- PANEL 2: İHA İçi Alt Sistem COMP_ID Ayrımı ve Mesaj Dağılımı ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

components = ["Autopilot\n(COMP: 1)", "Companion AI\n(COMP: 191)", "Gimbal Pod\n(COMP: 154)", "EO/IR Kamera\n(COMP: 100)", "Mühimmat\n(COMP: 195)"]
packet_shares = [45.0, 25.0, 15.0, 10.0, 5.0] # Yüzdelik trafik
bar_colors = [COLOR_ACCENT2, COLOR_ACCENT1, "#818CF8", "#F472B6", COLOR_ACCENT3]

bars = ax2.bar(components, packet_shares, color=bar_colors, width=0.55, edgecolor="#334155")
ax2.set_title("Panel 2: İHA İçi Alt Sistem COMP_ID Veri Trafiği Dağılımı (%)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_ylabel("Trafik Payı [%]", color=COLOR_MUTED, fontsize=10)
ax2.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")

for bar in bars:
    h = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., h + 1.0, f"%{h:.1f}", ha='center', va='bottom', color=COLOR_TEXT, fontsize=8, fontweight="bold")

# --- PANEL 3: 100.000 Paketlik Yönlendirici Gecikme Dağılımı ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

n, bins, patches = ax3.hist(latencies_us, bins=50, color=COLOR_ACCENT1, alpha=0.75, edgecolor="#0284C7")
ax3.axvline(p50, color=COLOR_ACCENT2, linestyle="-", linewidth=2.2, label=f"p50 (Medyan): {p50:.2f} µs")
ax3.axvline(p90, color=COLOR_ACCENT4, linestyle="--", linewidth=2.2, label=f"p90: {p90:.2f} µs")
ax3.axvline(p99, color=COLOR_ACCENT3, linestyle="-.", linewidth=2.2, label=f"p99: {p99:.2f} µs")

ax3.set_title("Panel 3: MAVLink Router Paket Yönlendirme Gecikmesi (µs)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("Yönlendirme Gecikmesi [µs]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("Paket Adedi", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 4: Sürü Güvenlik Bariyeri & Yönlendirme İstatistikleri ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

categories = ["Doğru Yönlendirilen", "İzole Edilen Komut", "Mükerrer SYS_ID Engeli", "Yasaklı Broadcast Disarm"]
counts = [100000, 2, 1, 1]
palette = [COLOR_ACCENT2, COLOR_ACCENT1, COLOR_ACCENT4, COLOR_ACCENT3]

bars4 = ax4.bar(categories, counts, color=palette, width=0.5, edgecolor="#334155")
ax4.set_yscale("log")
ax4.set_title("Panel 4: Sürü Emniyet Kalkanı ve Yönlendirme İstatistiği", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_ylabel("İşlem Sayısı (Logaritmik Ölçek)", color=COLOR_MUTED, fontsize=10)
ax4.tick_params(colors=COLOR_MUTED)
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")

for i, count in enumerate(counts):
    ax4.text(i, count * 1.35, f"{count:,}", ha='center', va='bottom', color=COLOR_TEXT, fontsize=8, fontweight="bold")

# Üst Başlık
plt.suptitle("BAYRAKTAR AKINCI / STM KARGU — MAVLINK SYSTEM & COMPONENT ID YÖNLENDİRME DASHBOARD'U", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_232/gun_232_mavlink_system_component_id.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

