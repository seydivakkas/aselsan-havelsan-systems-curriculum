#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

TARGET_DIR = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_211"
PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_211/gun_211_ros2_package_workspace_colcon.png"

# ==============================================================================
# KOD 1: ROS 2 Paket İskeleti ve Manifest Ayrıştırıcı (Parser)
# Amaç: package.xml (Format 3) ve CMakeLists.txt sözdizimini doğrulamak,
# bağımlılık etiketlerinin semantik analizini gerçekleştirmek.
# ==============================================================================

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Set

@dataclass
class Ros2PackageManifest:
    name: str
    version: str
    maintainer: str
    buildtool_depends: Set[str]
    depends: Set[str]
    exec_depends: Set[str]

PACKAGE_XML_CONTENT = '''<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>radar_track_gateway</name>
  <version>1.0.0</version>
  <description>TUSAŞ/ASELSAN Aviyonik Radar Ağ Geçidi Düğümü</description>
  <maintainer email="seydi@savunma.gov.tr">Seydi Eryılmaz</maintainer>
  <license>ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <depend>rclcpp</depend>
  <depend>sensor_msgs</depend>
  <depend>geometry_msgs</depend>

  <exec_depend>launch_ros</exec_depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
'''

# XML Ayrıştırma ve Doğrulama
root = ET.fromstring(PACKAGE_XML_CONTENT)
pkg_name = root.find("name").text
pkg_ver = root.find("version").text
maintainer = root.find("maintainer").text

buildtool_deps = {elem.text for elem in root.findall("buildtool_depend")}
deps = {elem.text for elem in root.findall("depend")}
exec_deps = {elem.text for elem in root.findall("exec_depend")}

manifest = Ros2PackageManifest(
    name=pkg_name,
    version=pkg_ver,
    maintainer=maintainer,
    buildtool_depends=buildtool_deps,
    depends=deps,
    exec_depends=exec_deps
)

print("[KOD 1] ROS 2 package.xml Ayrıştırma Sonuçları:")
print(f"  - Paket Adı            : {manifest.name}")
print(f"  - Sürüm                : {manifest.version}")
print(f"  - Sorumlu (Maintainer) : {manifest.maintainer}")
print(f"  - Buildtool Bağımlılığı: {manifest.buildtool_depends}")
print(f"  - Ortak Bağımlılıklar  : {manifest.depends}")
print(f"  - Çalışma Bağımlılığı  : {manifest.exec_depends}")

assert manifest.name == "radar_track_gateway"
assert "ament_cmake" in manifest.buildtool_depends
assert "rclcpp" in manifest.depends
assert "sensor_msgs" in manifest.depends
assert "launch_ros" in manifest.exec_depends

print("\n[PASS] Kod 1 ROS 2 Paket Manifest Doğrulaması Başarıyla Tamamlandı.")

# ==============================================================================
# KOD 2: colcon Bağımlılık Ağacı ve Topolojik Sıralama (Topological Sort) Motoru
# Amaç: Paketler arasındaki Yönlü Döngüsüz Çizgeyi (DAG) çözümlemek ve
# hatasız paralel/seri derleme sırasını belirlemek.
# ==============================================================================

from collections import deque, defaultdict
from typing import Dict, List, Set

class ColconBuildScheduler:
    def __init__(self):
        # package -> set of dependencies
        self.dependencies: Dict[str, Set[str]] = {}

    def add_package(self, pkg_name: str, deps: List[str]):
        self.dependencies[pkg_name] = set(deps)

    def resolve_build_order(self) -> List[List[str]]:
        # Kahn Algoritması ile Dalga (Wave/Stage) Tabanlı Paralel Derleme Sırası
        in_degree = {pkg: 0 for pkg in self.dependencies}
        reverse_graph = defaultdict(list)

        for pkg, deps in self.dependencies.items():
            for d in deps:
                if d in self.dependencies: # Sadece çalışma alanı içi paketler
                    in_degree[pkg] += 1
                    reverse_graph[d].append(pkg)

        queue = deque([pkg for pkg, deg in in_degree.items() if deg == 0])
        build_stages: List[List[str]] = []

        total_processed = 0
        while queue:
            current_stage = list(queue)
            queue.clear()
            build_stages.append(current_stage)
            total_processed += len(current_stage)

            for pkg in current_stage:
                for dependent in reverse_graph[pkg]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if total_processed != len(self.dependencies):
            raise ValueError("DÖNGÜSEL BAĞIMLILIK (Circular Dependency) Tespit Edildi! Derleme imkansız.")

        return build_stages

# Savunma Aviyonik Çalışma Alanı (Workspace) Senaryosu
scheduler = ColconBuildScheduler()
scheduler.add_package("radar_interfaces", deps=[]) # Temel Mesaj Paketi
scheduler.add_package("radar_driver", deps=["radar_interfaces"]) # Donanım Sürücüsü
scheduler.add_package("kalman_tracker", deps=["radar_interfaces"]) # İzleyici Modülü
scheduler.add_package("fusion_manager", deps=["radar_driver", "kalman_tracker"]) # Füzyon Yöneticisi
scheduler.add_package("mission_gui", deps=["fusion_manager"]) # Kokpit Göstergesi

stages = scheduler.resolve_build_order()

print("[KOD 2] colcon Paralel Derleme Kademeleri (Build Stages):")
for stage_idx, stage_pkgs in enumerate(stages, start=1):
    print(f"  - Aşama {stage_idx} (Eşzamanlı Derlenebilir): {stage_pkgs}")

assert stages[0] == ["radar_interfaces"], "İlk aşamada sadece arayüz paketi derlenmelidir!"
assert set(stages[1]) == {"radar_driver", "kalman_tracker"}, "2. aşamada sürücü ve izleyici paralel derlenmelidir!"
assert stages[2] == ["fusion_manager"]
assert stages[3] == ["mission_gui"]

print("\n[PASS] colcon DAG Çözümleme ve Topolojik Sıralama Başarıyla Doğrulandı.")

# ==============================================================================
# KOD 3: Overlay / Underlay ve AMENT_PREFIX_PATH Arama Simülatörü
# Amaç: Overlay çalışma alanının Underlay sistem paketlerini güvenli şekilde
# nasıl gölgelediğini (shadowing) ve ortam değişkeni zincirini doğrulamak.
# ==============================================================================

class Ros2EnvironmentResolver:
    def __init__(self):
        self.ament_prefix_path: List[str] = []
        # path -> dict(pkg_name -> version)
        self.disk_storage: Dict[str, Dict[str, str]] = {}

    def add_workspace_layer(self, layer_path: str, packages: Dict[str, str]):
        self.disk_storage[layer_path] = packages
        # Yeni eklenen katman en başa geçer (Overlay mantığı)
        self.ament_prefix_path.insert(0, layer_path)

    def find_package(self, pkg_name: str) -> Optional[Tuple[str, str]]:
        # AMENT_PREFIX_PATH sırasıyla aranır
        for layer in self.ament_prefix_path:
            if pkg_name in self.disk_storage.get(layer, {}):
                version = self.disk_storage[layer][pkg_name]
                return (layer, version)
        return None

resolver = Ros2EnvironmentResolver()

# 1. Aşama: Sistem ROS 2 (Underlay) Yüklenir
resolver.add_workspace_layer(
    layer_path="/opt/ros/jazzy",
    packages={
        "rclcpp": "21.0.1",
        "sensor_msgs": "5.1.0",
        "nav2_core": "1.2.0" # Resmi paket
    }
)

# 2. Aşama: Mühendisin Savunma Çalışma Alanı (Overlay) Yüklenir
# Mühendis, nav2_core içine özel bir anti-jamming yaması yapmıştır (Sürüm: 1.2.0-aselsan-patch)
resolver.add_workspace_layer(
    layer_path="/home/seydi/defense_ws/install",
    packages={
        "nav2_core": "1.2.0-aselsan-patch", # Gölgeleyen paket
        "mission_autopilot": "0.1.0"         # Özel yeni paket
    }
)

print("[KOD 3] AMENT_PREFIX_PATH Katman Sıralaması:")
for idx, p in enumerate(resolver.ament_prefix_path):
    print(f"  - Katman {idx + 1}: {p}")

found_nav2 = resolver.find_package("nav2_core")
found_rclcpp = resolver.find_package("rclcpp")

print(f"\n[KOD 3] Paket Arama Sonuçları:")
print(f"  - nav2_core Nereden Yüklendi? : {found_nav2[0]} (Sürüm: {found_nav2[1]})")
print(f"  - rclcpp Nereden Yüklendi?    : {found_rclcpp[0]} (Sürüm: {found_rclcpp[1]})")

assert found_nav2[0] == "/home/seydi/defense_ws/install", "Overlay altındaki paket öncelikli olmalıdır!"
assert found_nav2[1] == "1.2.0-aselsan-patch"
assert found_rclcpp[0] == "/opt/ros/jazzy", "Overlay'de olmayan paket Underlay'den çekilmelidir!"

print("\n[PASS] ROS 2 Overlay/Underlay Zincirleme Mekanizması Başarıyla Doğrulandı.")

# ==============================================================================
# KOD 4: Hata Enjeksiyonu (Fault Injection) ve Savunma Dayanıklılık Testleri
# Senaryolar:
#   Test A: Döngüsel Bağımlılık (Circular Dependency) Tespiti
#   Test B: Eksik Paket Bağımlılığı ve Derleme Reddi
#   Test C: ament_package() Çağrısı Olmadan Kayıt Eksikliği
# ==============================================================================

# TEST A: Döngüsel Bağımlılık Testi
bad_scheduler = ColconBuildScheduler()
bad_scheduler.add_package("pkg_alpha", deps=["pkg_beta"])
bad_scheduler.add_package("pkg_beta", deps=["pkg_gamma"])
bad_scheduler.add_package("pkg_gamma", deps=["pkg_alpha"]) # DÖNGÜ: alpha -> beta -> gamma -> alpha!

cycle_caught = False
try:
    bad_scheduler.resolve_build_order()
except ValueError as ex:
    cycle_caught = True
    print(f"[TEST A] Beklenen Döngüsel Bağımlılık Yakalandı: {ex}")

assert cycle_caught, "Döngüsel bağımlılık tespit edilmelidir!"

# TEST B: Eksik Bağımlılık Kontrolü
class StrictDependencyValidator:
    @staticmethod
    def validate_dependencies(available_pkgs: Set[str], required_deps: Set[str]):
        missing = required_deps - available_pkgs
        if missing:
            raise LookupError(f"UNMET_DEPENDENCIES: Şu paketler çalışma alanında bulunamadı: {missing}")
        return True

available = {"rclcpp", "std_msgs"}
required = {"rclcpp", "std_msgs", "aselsan_crypto_msgs"} # crypto_msgs eksik!

missing_caught = False
try:
    StrictDependencyValidator.validate_dependencies(available, required)
except LookupError as ex:
    missing_caught = True
    print(f"\n[TEST B] Eksik Bağımlılık Hatası Yakalandı: {ex}")

assert missing_caught

# TEST C: ament_package() Eksikliği Simülasyonu
class MockCmakeBuilder:
    def __init__(self, has_ament_package_call: bool):
        self.has_ament_package_call = has_ament_package_call
        self.is_registered_in_index = False

    def build_and_install(self):
        # ament_package() makrosu, paketi ~/.ament_index/ üzerine kaydeder
        if self.has_ament_package_call:
            self.is_registered_in_index = True
        else:
            self.is_registered_in_index = False

b_invalid = MockCmakeBuilder(has_ament_package_call=False)
b_invalid.build_and_install()
print(f"\n[TEST C] ament_package() Eksik Paket: Ament Index Kaydı = {b_invalid.is_registered_in_index}")
assert not b_invalid.is_registered_in_index, "ament_package() olmadan paket ROS 2 tarafından keşfedilemez!"

print("\n[PASS] 3 Kritik colcon / CMake Hata Enjeksiyonu Senaryosu Başarıyla Geçti.")

# ==============================================================================
# KOD 5: 50 Paketlik Büyük Savunma Aviyonik Çalışma Alanı Kıyaslaması
# Amaç: 50 paketlik Yönlü Çizgede (DAG) seri derleme ile paralel colcon
# derlemesinin süresini, CPU çekirdek kullanımını ve hızlanmasını ölçmek.
# ==============================================================================

import time
import numpy as np

NUM_PACKAGES = 50
np.random.seed(42)

# Her paketin C++20 derleme maliyeti (saniye cinsinden simülasyon: 2.0s - 8.0s)
package_compile_times = {f"pkg_{i:02d}": np.random.uniform(2.0, 8.0) for i in range(NUM_PACKAGES)}

# 6 Katmanlı Hiyerarşik Bağımlılık Yapısı
layers = 6
pkgs_per_layer = NUM_PACKAGES // layers
pkg_layers = {}
for i in range(NUM_PACKAGES):
    l_idx = min(i // pkgs_per_layer, layers - 1)
    pkg_layers[f"pkg_{i:02d}"] = l_idx

# 1. Seri Derleme Süresi (Tüm paketlerin toplamı)
total_serial_time_sec = sum(package_compile_times.values())

# 2. Paralel colcon Derleme Simülasyonu (8 Worker Thread)
NUM_WORKERS = 8
parallel_layer_times = []

for l in range(layers):
    layer_pkgs = [p for p, l_idx in pkg_layers.items() if l_idx == l]
    times_in_layer = [package_compile_times[p] for p in layer_pkgs]
    
    # Bir katmandaki işleri 8 worker'a dağıt
    worker_loads = [0.0] * NUM_WORKERS
    for t in sorted(times_in_layer, reverse=True):
        min_worker = np.argmin(worker_loads)
        worker_loads[min_worker] += t
    parallel_layer_times.append(max(worker_loads))

total_parallel_time_sec = sum(parallel_layer_times)
speedup = total_serial_time_sec / total_parallel_time_sec
efficiency_pct = (speedup / NUM_WORKERS) * 100.0

print(f"[KOD 5] 50 Paketlik Aviyonik Çalışma Alanı Derleme Sonuçları:")
print(f"  - Toplam Paket Sayısı         : {NUM_PACKAGES}")
print(f"  - Seri Derleme Süresi         : {total_serial_time_sec:.1f} saniye ({total_serial_time_sec/60:.2f} dakika)")
print(f"  - Paralel colcon (8 Worker)   : {total_parallel_time_sec:.1f} saniye ({total_parallel_time_sec/60:.2f} dakika)")
print(f"  - Elde Edilen Hızlanma (Speedup): {speedup:.2f}x Kat Daha Hızlı!")
print(f"  - Çekirdek Verimliliği (Eff)   : %{efficiency_pct:.1f}")

assert total_parallel_time_sec < total_serial_time_sec
assert speedup > 3.0, "8 çekirdekte en az 3x hızlanma elde edilmelidir!"

print("\n[PASS] 50 Paketlik Büyük Çalışma Alanı Kıyaslama Testi Başarıyla Tamamlandı.")

# ==============================================================================
# KOD 6: 4-Panelli Master Görselleştirme Paneli (Publication-Quality Artifact)
# Amaç: ROS 2 çalışma alanı anatomisini, colcon bağımlılık çizgesini,
# overlay katmanlamasını ve derleme başarımını görselleştirmek.
# ==============================================================================

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# PNG dosya yolu belirleme (Dizin garantili)
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_211_ros2_package_workspace_colcon.png")
    except Exception:
        PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_211/gun_211_ros2_package_workspace_colcon.png"

# Koyu Tema ve Tipografi Ayarları
plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.grid(True, linestyle='--', alpha=0.3, color='#64748B')
    ax.tick_params(colors='#E2E8F0', labelsize=10)
    for spine in ax.spines.values():
        spine.set_color('#475569')

# ------------------------------------------------------------------------------
# PANEL 1: ROS 2 Çalışma Alanı (Workspace) Anatomisi
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. ROS 2 Çalışma Alanı (Workspace) 4 Temel Kutusu", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

boxes = [
    ("src/", "Kaynak Kodlar (C++/Python)\npackage.xml & CMakeLists\n(Git'e Eklenen Tek Dizin)", "#059669", 0.05, 0.52),
    ("build/", "Derleyici Ara Dosyaları (.o)\nCMake Önbellek & Talaşlar\n(Silinebilir Çöp Kutusu)", "#D97706", 0.53, 0.52),
    ("install/", "Nihai Ürünler (bin, lib, share)\nsetup.bash Betikleri\n(Robot Buradan Çalışır)", "#2563EB", 0.05, 0.08),
    ("log/", "Derleme Kayıtları & Uyarılar\ncolcon build Logları\n(Hata Ayıklama Geçmişi)", "#7C3AED", 0.53, 0.08)
]

for name, desc, col, x, y in boxes:
    ax1.add_patch(plt.Rectangle((x, y), 0.42, 0.38, facecolor=col, alpha=0.3, edgecolor=col, linewidth=2))
    ax1.text(x + 0.04, y + 0.28, name, color='white', fontweight='bold', fontsize=12)
    ax1.text(x + 0.04, y + 0.12, desc, color='#E2E8F0', fontsize=8, va='center')

ax1.set_xlim(0, 1)
ax1.set_ylim(0, 1)
ax1.axis('off')

# ------------------------------------------------------------------------------
# PANEL 2: colcon Bağımlılık Çizgesi (DAG) ve Aşamalar
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. colcon Bağımlılık Çizgesi (DAG) ve Derleme Kademeleri", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

nodes = [
    ("radar_interfaces\n(Aşama 1)", 0.15, 0.5, "#10B981"),
    ("radar_driver\n(Aşama 2)", 0.45, 0.75, "#0284C7"),
    ("kalman_tracker\n(Aşama 2)", 0.45, 0.25, "#0284C7"),
    ("fusion_manager\n(Aşama 3)", 0.75, 0.5, "#F59E0B"),
    ("mission_gui\n(Aşama 4)", 0.92, 0.5, "#EC4899")
]

for name, x, y, col in nodes:
    ax2.add_patch(plt.Rectangle((x-0.08, y-0.12), 0.16, 0.24, facecolor=col, edgecolor='white', linewidth=1.2))
    ax2.text(x, y, name, color='white', ha='center', va='center', fontweight='bold', fontsize=7)

# Oklar
ax2.annotate("", xy=(0.37, 0.75), xytext=(0.23, 0.55), arrowprops=dict(facecolor='#38BDF8', width=1.5, headwidth=6))
ax2.annotate("", xy=(0.37, 0.25), xytext=(0.23, 0.45), arrowprops=dict(facecolor='#38BDF8', width=1.5, headwidth=6))
ax2.annotate("", xy=(0.67, 0.55), xytext=(0.53, 0.75), arrowprops=dict(facecolor='#38BDF8', width=1.5, headwidth=6))
ax2.annotate("", xy=(0.67, 0.45), xytext=(0.53, 0.25), arrowprops=dict(facecolor='#38BDF8', width=1.5, headwidth=6))
ax2.annotate("", xy=(0.84, 0.50), xytext=(0.83, 0.50), arrowprops=dict(facecolor='#38BDF8', width=1.5, headwidth=6))

ax2.set_xlim(0.05, 1.02)
ax2.set_ylim(0.05, 0.95)
ax2.axis('off')

# ------------------------------------------------------------------------------
# PANEL 3: Overlay / Underlay ve AMENT_PREFIX_PATH
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. Katmanlı Çalışma Alanı (Overlay / Underlay Zinciri)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

# Overlay
ax3.add_patch(plt.Rectangle((0.05, 0.52), 0.90, 0.38, facecolor='#1E3A8A', alpha=0.6, edgecolor='#3B82F6', linewidth=1.5))
ax3.text(0.10, 0.82, "1. Öncelik: OVERLAY (~/defense_ws/install)", color='#93C5FD', fontweight='bold', fontsize=10)
ax3.text(0.10, 0.68, "nav2_core [v1.2.0-aselsan-patch] -> (GÖLGELEYEN / ÖNCELİKLİ)", color='#FCD34D', fontweight='bold', fontsize=8)
ax3.text(0.10, 0.58, "mission_autopilot [v0.1.0] -> (Kullanıcıya Özel Yeni Paket)", color='white', fontsize=8)

# Underlay
ax3.add_patch(plt.Rectangle((0.05, 0.08), 0.90, 0.38, facecolor='#334155', alpha=0.6, edgecolor='#64748B', linewidth=1.5))
ax3.text(0.10, 0.38, "2. Öncelik: UNDERLAY (/opt/ros/jazzy)", color='#CBD5E1', fontweight='bold', fontsize=10)
ax3.text(0.10, 0.24, "rclcpp [v21.0.1], sensor_msgs [v5.1.0] -> (Sistem Temel Kütüphaneleri)", color='white', fontsize=8)
ax3.text(0.10, 0.14, "nav2_core [v1.2.0-official] -> (GÖLGELENDİ / DEVRE DIŞI)", color='#EF4444', fontstyle='italic', fontsize=8)

ax3.set_xlim(0, 1)
ax3.set_ylim(0, 1)
ax3.axis('off')

# ------------------------------------------------------------------------------
# PANEL 4: 50 Paketlik Seri vs Paralel colcon Derleme Kıyaslaması
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. 50 Paketlik Çalışma Alanı: Seri vs Paralel (8 Worker) Süre", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

strategies = ['Seri Derleme\n(Tek Çekirdek)', 'colcon build\n(8 Paralel Worker)']
times_sec = [total_serial_time_sec, total_parallel_time_sec]
colors = ['#EF4444', '#10B981']

bars = ax4.bar(strategies, times_sec, width=0.45, color=colors, edgecolor='white', linewidth=1.2)
ax4.set_ylabel("Toplam Derleme Süresi (Saniye)", color='#E2E8F0', fontsize=10)

for b in bars:
    h = b.get_height()
    ax4.text(b.get_x() + b.get_width()/2., h + 4, f"{h:.1f} sn\n({h/60:.1f} dk)", ha='center', va='bottom', color='white', fontweight='bold', fontsize=9)

ax4.text(0.5, total_serial_time_sec*0.65, f"Hızlanma Oranı: {speedup:.2f}x\nÇekirdek Verimi: %{efficiency_pct:.1f}",
         color='#FCD34D', ha='center', fontweight='bold', fontsize=10,
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#1E293B', edgecolor='#F59E0B'))

ax4.set_ylim(0, total_serial_time_sec * 1.25)

plt.tight_layout()
plt.savefig(PNG_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

# Üretilen PNG Dosya Boyutu Kontrolü
file_size_bytes = os.path.getsize(PNG_FILE)
file_size_kb = file_size_bytes / 1024.0

print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {PNG_FILE}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'nin üzerinde olmalıdır!"

