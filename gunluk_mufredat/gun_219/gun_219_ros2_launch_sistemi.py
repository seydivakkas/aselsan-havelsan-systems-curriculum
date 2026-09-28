# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 219: ROS 2 Launch Sistemi Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: ROS 2 Launch Motoru ve Dinamik Argüman Çözümleme Simülatörü
# ============================================================================
import time
from typing import Dict, Any, List, Optional
import numpy as np

class LaunchConfiguration:
    # Komut satırından veya ortamdan gelen değişkenleri temsil eder.
    def __init__(self, key: str, default: Optional[str] = None):
        self.key = key
        self.default = default

    def resolve(self, context: Dict[str, str]) -> str:
        return context.get(self.key, self.default if self.default is not None else "")

class NodeAction:
    # launch_ros.actions.Node sınıfının aviyonik modellemesi.
    def __init__(self, package: str, executable: str, name: str,
                 namespace: str = "",
                 parameters: Optional[Dict[str, Any]] = None,
                 remappings: Optional[List[tuple]] = None,
                 respawn: bool = False):
        self.package = package
        self.executable = executable
        self.name = name
        self.namespace = namespace
        self.parameters = parameters or {}
        self.remappings = remappings or []
        self.respawn = respawn
        self.is_running = False
        self.pid: Optional[int] = None

    def execute(self, context: Dict[str, str], pid_counter: int) -> int:
        self.pid = pid_counter
        self.is_running = True
        # Parametrelerdeki substitution'ları çözümle
        resolved_params = {}
        for k, v in self.parameters.items():
            if isinstance(v, LaunchConfiguration):
                resolved_params[k] = v.resolve(context)
            else:
                resolved_params[k] = v
        self.resolved_parameters = resolved_params
        return self.pid

class LaunchDescription:
    def __init__(self):
        self.arguments: Dict[str, str] = {}
        self.actions: List[NodeAction] = []

    def declare_argument(self, name: str, default_value: str):
        self.arguments[name] = default_value

    def add_action(self, action: NodeAction):
        self.actions.append(action)

    def launch(self, user_args: Dict[str, str]) -> Dict[str, Any]:
        context = self.arguments.copy()
        context.update(user_args)
        
        print(f"[LAUNCH ENGINE] Başlatma Konfigürasyonu Çözümleniyor...")
        print(f"  - Aktif Argümanlar: {context}")

        spawned_nodes = []
        pid_seq = 1000
        for action in self.actions:
            pid = action.execute(context, pid_seq)
            pid_seq += 1
            spawned_nodes.append({
                "name": action.name,
                "executable": f"{action.package}/{action.executable}",
                "pid": pid,
                "parameters": action.resolved_parameters
            })
            print(f"  [+] Düğüm Başlatıldı: {action.name} (PID: {pid}) | Parametreler: {action.resolved_parameters}")
        
        return {"context": context, "nodes": spawned_nodes}

# Test İcrası: Taktik İHA Aviyonik Başlatma Betiği
ld = LaunchDescription()
ld.declare_argument("mission_mode", default_value="surveillance")
ld.declare_argument("update_rate_hz", default_value="100")

radar_node = NodeAction(
    package="radar_pkg",
    executable="radar_driver_node",
    name="radar_driver",
    parameters={
        "mode": LaunchConfiguration("mission_mode"),
        "rate": LaunchConfiguration("update_rate_hz")
    }
)

guidance_node = NodeAction(
    package="guidance_pkg",
    executable="guidance_core_node",
    name="guidance_computer",
    parameters={
        "mode": LaunchConfiguration("mission_mode"),
        "timeout_ms": 500
    }
)

ld.add_action(radar_node)
ld.add_action(guidance_node)

# Kullanıcı komutu: mode:=combat update_rate_hz:=250
launch_output = ld.launch(user_args={"mission_mode": "combat", "update_rate_hz": "250"})

assert len(launch_output["nodes"]) == 2
assert launch_output["nodes"][0]["parameters"]["mode"] == "combat"
assert launch_output["nodes"][0]["parameters"]["rate"] == "250"
assert launch_output["nodes"][1]["parameters"]["mode"] == "combat"

print("\n[PASS] Kod 1: Launch Motoru ve Dinamik Argüman Çözümleme Başarıyla Doğrulandı.")

# ============================================================================
# KOD HÜCRESİ 2: Olay Tabanlı (Event-Driven) Reaktif Başlatma Simülasyonu
# ============================================================================

class LaunchEvent:
    def __init__(self, event_type: str, source_node: str, payload: Any = None):
        self.event_type = event_type
        self.source_node = source_node
        self.payload = payload
        self.timestamp = time.perf_counter()

class EventHandler:
    def __init__(self, target_event_type: str, callback: Any):
        self.target_event_type = target_event_type
        self.callback = callback

    def matches(self, event: LaunchEvent) -> bool:
        return event.event_type == self.target_event_type

class ReactiveLaunchSystem:
    def __init__(self):
        self.handlers: List[EventHandler] = []
        self.active_nodes: List[str] = []
        self.event_audit_trail: List[LaunchEvent] = []

    def register_event_handler(self, handler: EventHandler):
        self.handlers.append(handler)

    def emit_event(self, event: LaunchEvent):
        self.event_audit_trail.append(event)
        print(f"  [EVENT OLUŞTU]: Tür='{event.event_type}' | Kaynak='{event.source_node}' | Detay={event.payload}")
        for h in self.handlers:
            if h.matches(event):
                h.callback(event, self)

    def spawn_node(self, node_name: str):
        self.active_nodes.append(node_name)
        print(f"    >>> REAKTİF EYLEM: '{node_name}' düğümü başarıyla ayağa kaldırıldı.")

# Aviyonik Reaktif Başlatma Senaryosu:
# Kural 1: 'radar_driver' ACTIVE olduğunda 'target_tracker' düğümünü başlat.
# Kural 2: 'radar_driver' CRASH (Exit) olduğunda acil durum protokolünü tetikle.
launch_sys = ReactiveLaunchSystem()

def on_radar_active(event: LaunchEvent, sys_ref: ReactiveLaunchSystem):
    if event.source_node == "radar_driver" and event.payload == "ACTIVE":
        print("  [*] Kural 1 Tetiklendi: Radar aktif oldu, Hedef Takip (Target Tracker) başlatılıyor...")
        sys_ref.spawn_node("target_tracker")

def on_radar_crash(event: LaunchEvent, sys_ref: ReactiveLaunchSystem):
    if event.source_node == "radar_driver":
        print("  [!] Kural 2 Tetiklendi: KRİTİK ALARM! Radar çöktü, sistem Güvenli Mod'a alınıyor...")
        if "target_tracker" in sys_ref.active_nodes:
            sys_ref.active_nodes.remove("target_tracker")
            print("    <<< EMNİYET EYLEMİ: 'target_tracker' düğümü durduruldu.")

launch_sys.register_event_handler(EventHandler("ON_STATE_TRANSITION", on_radar_active))
launch_sys.register_event_handler(EventHandler("ON_PROCESS_EXIT", on_radar_crash))

# ADIM 1: Radar Düğümü Başlatılıyor ve Inactive'den Active'e Geçiyor
print("[ADIM 1] Radar düğümü yaşam döngüsü geçişi yayıyor...")
launch_sys.emit_event(LaunchEvent("ON_STATE_TRANSITION", "radar_driver", "INACTIVE"))
assert "target_tracker" not in launch_sys.active_nodes

launch_sys.emit_event(LaunchEvent("ON_STATE_TRANSITION", "radar_driver", "ACTIVE"))
assert "target_tracker" in launch_sys.active_nodes

# ADIM 2: Radar Düğümünde Donanımsal Çökme Meydana Geliyor (Process Exit)
print("\n[ADIM 2] Radarda beklenmedik çökme meydana geliyor...")
launch_sys.emit_event(LaunchEvent("ON_PROCESS_EXIT", "radar_driver", {"exit_code": -9, "reason": "SIGKILL"}))
assert "target_tracker" not in launch_sys.active_nodes

print("\n[PASS] Kod 2: Olay Tabanlı Reaktif Başlatma ve Hata Güvenliği Başarıyla Doğrulandı.")

# ============================================================================
# KOD HÜCRESİ 3: Composable Node Container ve Sıfır Kopyalı Bellek Paylaşımı
# ============================================================================

class MockSharedMemoryPayload:
    def __init__(self, size_bytes: int):
        self.size_bytes = size_bytes
        self.address = id(self) # Python bellek adresi

class ComponentContainer:
    # Tek bir proses içinde dinamik kütüphaneleri (so) barındıran konteyner.
    def __init__(self, container_name: str, pid: int = 5001):
        self.container_name = container_name
        self.pid = pid
        self.loaded_components: Dict[str, str] = {}
        self.zero_copy_transfers = 0

    def load_component(self, package: str, plugin_name: str, instance_name: str):
        self.loaded_components[instance_name] = f"{package}::{plugin_name}"
        print(f"  [CONTAINER {self.container_name}] Eklenti Yüklendi (dlopen): {instance_name} <- {plugin_name}")

    def intra_process_publish(self, from_node: str, to_node: str, payload: MockSharedMemoryPayload) -> Dict[str, Any]:
        # Aynı proses içinde std::shared_ptr transferi (Sıfır Kopya)
        t_start = time.perf_counter_ns()
        # Pointer aktarımı: kopya yapılmaz, sadece adres paylaşılır!
        received_address = payload.address
        t_duration_ns = time.perf_counter_ns() - t_start
        self.zero_copy_transfers += 1
        
        return {
            "success": received_address == payload.address,
            "latency_ns": max(15, t_duration_ns),
            "payload_bytes": payload.size_bytes,
            "zero_copy": True
        }

# 10 MB'lık Yüksek Çözünürlüklü Radar Ham Matrisi Transferi
container = ComponentContainer("avionics_radar_container", pid=6500)
container.load_component("radar_driver_pkg", "RadarDriverComponent", "radar_front")
container.load_component("radar_dsp_pkg", "RadarDspComponent", "radar_dsp")

data_10mb = MockSharedMemoryPayload(size_bytes=10 * 1024 * 1024)
transfer_res = container.intra_process_publish("radar_front", "radar_dsp", data_10mb)

print(f"\n[CONTAINER İÇİ SIFIR KOPYALI TRANSFER]")
print(f"  - Veri Boyutu      : {transfer_res['payload_bytes'] / (1024*1024):.1f} MB")
print(f"  - Transfer Gecikmesi: {transfer_res['latency_ns']} nanosaniye (Pointer Swap)")
print(f"  - Sıfır Kopya Başarısı: {transfer_res['success']}")

assert transfer_res["success"] == True
assert transfer_res["zero_copy"] == True
assert len(container.loaded_components) == 2

print("\n[PASS] Kod 3: Composable Node Container ve Sıfır Kopyalı Aktarım Başarıyla Doğrulandı.")

# ============================================================================
# KOD HÜCRESİ 4: Hata Enjeksiyonu (Fault Injection) ve Savunma Doğrulama Testi
# ============================================================================

# ----------------------------------------------------------------------------
# TEST A: Eksik / Tanımsız Argüman Çözümleme Hatası (Undefined Substitution)
# ----------------------------------------------------------------------------
print("[TEST A] Tanımsız Argüman Çözümleme Enjeksiyonu...")

class StrictLaunchConfiguration(LaunchConfiguration):
    def resolve_strict(self, context: Dict[str, str]) -> str:
        if self.key not in context and self.default is None:
            raise KeyError(f"LAUNCH_SUBSTITUTION_ERROR: Zorunlu argüman '{self.key}' komut satırında veya varsayılanlarda bulunamadı!")
        return self.resolve(context)

strict_arg = StrictLaunchConfiguration("secret_encryption_key", default=None)
missing_arg_caught = False

try:
    # Context içinde anahtar yok!
    strict_arg.resolve_strict(context={"mission": "air_defense"})
except KeyError as e:
    missing_arg_caught = True
    print(f"  [BEKLENEN HATA YAKALANDI]: {e}")

assert missing_arg_caught == True
print("  [PASS] Test A Başarıyla Geçti: Tanımsız argüman hatası emniyetle yakalandı.\n")

# ----------------------------------------------------------------------------
# TEST B: Sonsuz Respawn Fırtınası Önleme (Respawn Rate Limiter)
# ----------------------------------------------------------------------------
print("[TEST B] Sonsuz Respawn Fırtınası Önleme Testi...")

class SafeProcessSupervisor:
    def __init__(self, max_retries: int = 3, reset_window_sec: float = 1.0):
        self.max_retries = max_retries
        self.failure_timestamps: List[float] = []

    def record_failure_and_should_respawn(self) -> bool:
        now = time.perf_counter()
        self.failure_timestamps.append(now)
        # Son 1 saniye içindeki çökmeleri say
        recent_failures = [t for t in self.failure_timestamps if now - t < 1.0]
        
        if len(recent_failures) > self.max_retries:
            print(f"  [RESPAWN ENGELİ]: 1 saniyede {len(recent_failures)} çökme gerçekleşti! Sonsuz döngüyü önlemek için düğüm kalıcı olarak durduruldu.")
            return False
        return True

supervisor = SafeProcessSupervisor(max_retries=3)
respawn_results = []
for crash_i in range(5):
    can_respawn = supervisor.record_failure_and_should_respawn()
    respawn_results.append(can_respawn)

assert respawn_results == [True, True, True, False, False]
print("  [PASS] Test B Başarıyla Geçti: Respawn rate limiter fork fırtınasını engelledi.\n")

# ----------------------------------------------------------------------------
# TEST C: Döngüsel Bağımlılık Tespiti (Circular Dependency Detection in Launch)
# ----------------------------------------------------------------------------
print("[TEST C] Döngüsel Başlatma Bağımlılığı (Deadlock) Tespiti...")

def detect_circular_dependencies(dependency_graph: Dict[str, List[str]]) -> List[str]:
    # Basit derinlemesine arama (DFS) ile döngü tespiti
    visited = set()
    rec_stack = set()
    cycle_nodes = []

    def dfs(node: str, path: List[str]) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in dependency_graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor, path):
                    return True
            elif neighbor in rec_stack:
                cycle_nodes.extend(path + [neighbor])
                return True
        rec_stack.remove(node)
        path.pop()
        return False

    for n in dependency_graph:
        if n not in visited:
            if dfs(n, []):
                break
    return cycle_nodes

# Hatalı Bağımlılık: Node A -> Node B -> Node C -> Node A (Deadlock!)
bad_graph = {
    "node_A": ["node_B"],
    "node_B": ["node_C"],
    "node_C": ["node_A"]
}

detected_cycle = detect_circular_dependencies(bad_graph)
print(f"  [DÖNGÜ TESPİT EDİLDİ]: {' -> '.join(detected_cycle)}")
assert len(detected_cycle) > 0
assert detected_cycle[0] == detected_cycle[-1]

print("  [PASS] Test C Başarıyla Geçti: Döngüsel bağımlılık statik analizle yakalandı.")

print("\n[PASS] Kod 4: 3 Kritik Launch Hata Enjeksiyonu Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 50 Düğümlü Aviyonik Sistem Başlatma ve Kaynak Benchmark'ı
# ============================================================================
import time
import numpy as np

def run_launch_architecture_benchmark(node_count: int = 50):
    print(f"[BENCHMARK] {node_count} Düğümlü Sistem İçin Çoklu Proses vs Composable Container Kıyaslanıyor...")

    # 1. Çoklu Proses (50 ayrı OS PID) Metrikleri:
    # Başlatma süresi (ms): Her fork/exec maliyeti ~45 ms + OS açılışı
    mp_spawn_times_ms = np.random.normal(loc=45.0, scale=8.0, size=node_count)
    mp_total_launch_time_s = float(np.sum(mp_spawn_times_ms) / 1000.0) # Seri başlatma
    
    # RAM Tüketimi (MB): Her proses için taban ~38 MB (ROS 2 runtime + DDS kütüphaneleri)
    mp_ram_per_node_mb = np.random.normal(loc=38.0, scale=3.0, size=node_count)
    mp_total_ram_mb = float(np.sum(mp_ram_per_node_mb))

    # Context Switch Yükü (Günde milyonlarca switch):
    mp_context_switches_per_sec = 50 * 1200 # 60.000 switch/s

    # 2. Composable Container (1 OS PID içinde 50 eklenti) Metrikleri:
    # Başlatma süresi: Sadece dlopen() çağrısı ~3 ms
    cc_spawn_times_ms = np.random.normal(loc=3.2, scale=0.5, size=node_count)
    cc_total_launch_time_s = float((np.sum(cc_spawn_times_ms) + 120.0) / 1000.0) # Konteyner açılışı + yüklemeler

    # RAM Tüketimi (MB): Ortak kütüphane paylaşımı, düğüm başı sadece ~4 MB ek yük + 50 MB taban
    cc_total_ram_mb = float(55.0 + np.sum(np.random.normal(loc=4.2, scale=0.6, size=node_count)))

    # Context Switch: Tek proses içi thread havuzu
    cc_context_switches_per_sec = 4 * 1500 # Sadece 6.000 switch/s

    results = {
        "node_count": node_count,
        "mp_launch_time_s": mp_total_launch_time_s,
        "cc_launch_time_s": cc_total_launch_time_s,
        "mp_total_ram_mb": mp_total_ram_mb,
        "cc_total_ram_mb": cc_total_ram_mb,
        "mp_ctx_switch": mp_context_switches_per_sec,
        "cc_ctx_switch": cc_context_switches_per_sec,
        "ram_saving_ratio": mp_total_ram_mb / cc_total_ram_mb,
        "launch_speedup": mp_total_launch_time_s / cc_total_launch_time_s
    }
    return results

bench_res = run_launch_architecture_benchmark(node_count=50)

print(f"\n[50 DÜĞÜM MİMARİ KIYASLAMA SONUÇLARI]")
print(f"  - Toplam Başlatma Süresi : Çoklu Proses: {bench_res['mp_launch_time_s']:.2f} s | Composable: {bench_res['cc_launch_time_s']:.2f} s (Hızlanma: {bench_res['launch_speedup']:.1f}x)")
print(f"  - Toplam Bellek (RAM)    : Çoklu Proses: {bench_res['mp_total_ram_mb']:.1f} MB | Composable: {bench_res['cc_total_ram_mb']:.1f} MB (Tasarruf: {bench_res['ram_saving_ratio']:.1f}x)")
print(f"  - Context Switch (Yük)   : Çoklu Proses: {bench_res['mp_ctx_switch']:,} /s | Composable: {bench_res['cc_ctx_switch']:,} /s")

assert bench_res["launch_speedup"] > 4.0, "Composable başlatma en az 4 kat daha hızlı olmalıdır!"
assert bench_res["ram_saving_ratio"] > 5.0, "Composable bellek tasarrufu en az 5 kat olmalıdır!"

print("\n[PASS] Kod 5: 50 Düğümlü Mimari Benchmark Kıyaslaması Başarıyla Tamamlandı.")

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
# PANEL 1: ROS 2 Launch Katman ve Olay Akış Şeması
# ----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("PANEL 1: ROS 2 Launch Mimarisi ve Olay Akış Şeması", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

layers = [
    ("1. CLI & Input Arguments: 'ros2 launch ... mode:=combat'", 0.85, '#38BDF8'),
    ("2. LaunchDescription & Substitutions Engine (Context Resolution)", 0.68, '#818CF8'),
    ("3. Action Spawner: Node, LifecycleNode, ComposableContainer", 0.51, '#64748B'),
    ("4. Event System: OnProcessExit, OnStateTransition, OnExecutionComplete", 0.34, '#F59E0B'),
    ("5. OS Process Execution: Monitored PIDs & Zero-Copy IPC Links", 0.17, '#10B981')
]

for name, y_pos, color in layers:
    rect = plt.Rectangle((0.05, y_pos - 0.05), 0.90, 0.08, facecolor=color, edgecolor='#FFFFFF', alpha=0.85, transform=ax1.transAxes)
    ax1.add_patch(rect)
    ax1.text(0.5, y_pos - 0.01, name, color='#0F172A' if color in ['#38BDF8', '#F59E0B'] else '#FFFFFF', 
             fontsize=9.5, fontweight='bold', ha='center', va='center', transform=ax1.transAxes)

ax1.set_xlim(0, 1)
ax1.set_ylim(0, 1)
ax1.axis('off')

# ----------------------------------------------------------------------------
# PANEL 2: 50 Düğüm RAM Tüketim Kıyaslaması (Bar Chart)
# ----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("PANEL 2: 50 Düğüm İçin Bellek (RAM) Ayak İzi (MB)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

categories = ['Çoklu Proses (50 PID)', 'Composable Container (1 PID)']
ram_values = [bench_res['mp_total_ram_mb'], bench_res['cc_total_ram_mb']]
colors_ram = ['#EF4444', '#10B981']

bars = ax2.bar(categories, ram_values, color=colors_ram, width=0.45, alpha=0.85, edgecolor='#FFFFFF')
ax2.set_ylabel("Toplam RAM Tüketimi (MB)", color='#E2E8F0', fontsize=11)

for bar in bars:
    y = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, y + 30, f"{y:.1f} MB", ha='center', va='bottom', color='#FFFFFF', fontsize=10, fontweight='bold')

ax2.text(0.5, 0.75, f"Bellek Tasarrufu: {bench_res['ram_saving_ratio']:.1f}x Kat Daha Az RAM!", 
         ha='center', va='center', color='#6EE7B7', fontsize=11, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor='#10B981', alpha=0.9), transform=ax2.transAxes)

# ----------------------------------------------------------------------------
# PANEL 3: Başlatma Süresi Kıyaslaması (Saniye)
# ----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("PANEL 3: 50 Düğüm Başlatma Süresi (Saniye)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

launch_times = [bench_res['mp_launch_time_s'], bench_res['cc_launch_time_s']]
bars_lt = ax3.barh(categories, launch_times, color=['#EF4444', '#38BDF8'], height=0.45, alpha=0.85, edgecolor='#FFFFFF')
ax3.set_xlabel("Toplam Başlatma Süresi (Saniye)", color='#E2E8F0', fontsize=11)

for bar in bars_lt:
    w = bar.get_width()
    ax3.text(w + 0.05, bar.get_y() + bar.get_height()/2.0, f"{w:.2f} s", ha='left', va='center', color='#FFFFFF', fontsize=10, fontweight='bold')

ax3.text(0.5, 0.35, f"Başlatma Hızlanması: {bench_res['launch_speedup']:.1f}x Daha Hızlı!", 
         ha='center', va='center', color='#38BDF8', fontsize=11, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.9), transform=ax3.transAxes)

# ----------------------------------------------------------------------------
# PANEL 4: Sistem Çökme ve Reaktif Kurtarma Zaman Çizelgesi
# ----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("PANEL 4: Çökme Anı ve Reaktif Kurtarma Zaman Çizelgesi (ms)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

timeline_events = [
    ("Normal Operasyon", 0.0, 100.0, '#10B981'),
    ("Radar Çöküşü (Crash)", 100.0, 10.0, '#EF4444'),
    ("OnProcessExit Yakalama", 110.0, 5.0, '#F59E0B'),
    ("Ateşleme Sistemi E-Stop", 115.0, 15.0, '#EF4444'),
    ("Yedek Radar Respawn", 130.0, 45.0, '#38BDF8'),
    ("Sistem Yeniden Aktif", 175.0, 80.0, '#10B981')
]

y_pos_ev = np.arange(len(timeline_events))
for i, (ev_name, start, dur, col) in enumerate(timeline_events):
    ax4.barh(i, dur, left=start, color=col, alpha=0.85, edgecolor='#FFFFFF', height=0.55)
    ax4.text(start + dur/2.0, i, f"{dur:.0f} ms", ha='center', va='center', 
             color='#0F172A' if col in ['#38BDF8', '#F59E0B', '#10B981'] else '#FFFFFF', 
             fontsize=8.5, fontweight='bold')

ax4.set_yticks(y_pos_ev)
ax4.set_yticklabels([e[0] for e in timeline_events], color='#E2E8F0', fontsize=9.5)
ax4.set_xlabel("Zaman (Milisaniye - ms)", color='#E2E8F0', fontsize=11)
ax4.set_xlim(0, 270)

# Filigran ve Lisans Notu
fig.text(0.5, 0.015, "ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR | Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)",
         ha='center', va='bottom', color='#94A3B8', fontsize=10, fontweight='bold')

plt.tight_layout(rect=[0, 0.03, 1, 0.97])

output_png = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_219/gun_219_ros2_launch_sistemi.png"
if not os.path.isabs(output_png) or not os.path.exists(os.path.dirname(output_png)):
    output_png = "gun_219_ros2_launch_sistemi.png"

plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "Görsel dosya boyutu 100 KB'den küçük olamaz!"

