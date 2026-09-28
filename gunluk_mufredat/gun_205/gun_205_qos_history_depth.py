#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

TARGET_DIR = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_205"
PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_205/gun_205_qos_history_depth.png"

# ==============================================================================
# KOD 1: Minimal KEEP_LAST (Depth=1) vs KEEP_ALL Simülasyonu
# Amaç: Odometri (Son Değer Önbelleği) ile Kritik Alarm Günlüğü arasındaki
# kuyruk boyutu ve örnek saklama farkını doğrulamak.
# ==============================================================================

from enum import Enum
from typing import List, Dict, Any
from dataclasses import dataclass

class HistoryKind(Enum):
    KEEP_LAST = 1
    KEEP_ALL = 2

@dataclass
class MinimalSample:
    seq_num: int
    payload: str

class MinimalHistoryCache:
    def __init__(self, kind: HistoryKind, depth: int = 1):
        self.kind = kind
        self.depth = depth
        self.samples: List[MinimalSample] = []
        self.dropped_samples: int = 0

    def add_sample(self, sample: MinimalSample) -> None:
        if self.kind == HistoryKind.KEEP_LAST:
            if len(self.samples) >= self.depth:
                self.samples.pop(0) # En eski örneği at
                self.dropped_samples += 1
            self.samples.append(sample)
        else: # KEEP_ALL
            self.samples.append(sample)

# 1. Deney: Odometri Konusu (KEEP_LAST, depth=1)
odom_cache = MinimalHistoryCache(HistoryKind.KEEP_LAST, depth=1)
for i in range(1, 6):
    odom_cache.add_sample(MinimalSample(seq_num=i, payload=f"POS_LAT_{39.9 + i*0.01:.4f}"))

# 2. Deney: Kritik Alarm Konusu (KEEP_ALL)
alarm_cache = MinimalHistoryCache(HistoryKind.KEEP_ALL)
alarms = ["ENG_OIL_PRESS_WARN", "STALL_MARGIN_ALERT", "HYDRAULIC_SYS_WARN"]
for i, al in enumerate(alarms, start=1):
    alarm_cache.add_sample(MinimalSample(seq_num=i, payload=al))

print("[KOD 1] Odometri (KEEP_LAST, depth=1) Durumu:")
print(f"  - Saklanan Örnek Sayısı : {len(odom_cache.samples)} (Beklenen: 1)")
print(f"  - Saklanan Son Veri     : {odom_cache.samples[0].payload}")
print(f"  - Ezilen (Dropped) Sayı : {odom_cache.dropped_samples} (Beklenen: 4)")

print("\n[KOD 1] Alarm Günlüğü (KEEP_ALL) Durumu:")
print(f"  - Saklanan Örnek Sayısı : {len(alarm_cache.samples)} (Beklenen: 3)")
print(f"  - Ezilen (Dropped) Sayı : {alarm_cache.dropped_samples} (Beklenen: 0)")

assert len(odom_cache.samples) == 1, "KEEP_LAST depth=1 yalnızca 1 örnek saklamalıdır!"
assert odom_cache.samples[0].seq_num == 5, "Saklanan örnek en son üretilen (5) olmalıdır!"
assert len(alarm_cache.samples) == 3, "KEEP_ALL tüm alarmları saklamalıdır!"
assert alarm_cache.dropped_samples == 0, "KEEP_ALL modunda veri kaybı olmamalıdır!"

print("\n[PASS] Kod 1 Minimal History Karşılaştırması Başarıyla Doğrulandı.")

# ==============================================================================
# KOD 2: Çok Anahtarlı (Keyed Instance) Dairesel Bellek (Ring Buffer) Motoru
# Amaç: Radar izleri (Track Instance) üzerinde per-instance depth kontrolü ve
# sabit boyutlu dairesel kuyruk (RingBuffer) mekanizmasını doğrulamak.
# ==============================================================================

from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import deque

@dataclass
class RadarTrackSample:
    track_id: str   # @key
    seq_num: int
    azimuth_deg: float
    range_km: float

class KeyedInstanceHistoryCache:
    def __init__(self, depth: int, max_instances: int = 10, max_samples: int = 100):
        self.depth = depth
        self.max_instances = max_instances
        self.max_samples = max_samples
        # Instance tabanlı ring buffer: track_id -> deque(maxlen=depth)
        self.instances: Dict[str, deque] = {}
        self.total_samples_count: int = 0
        self.evicted_samples: Dict[str, int] = {}

    def write(self, sample: RadarTrackSample) -> bool:
        tid = sample.track_id
        
        # 1. Yeni instance kontrolü
        if tid not in self.instances:
            if len(self.instances) >= self.max_instances:
                raise RuntimeError(f"RESOURCE_LIMITS_EXCEEDED: max_instances ({self.max_instances}) doldu!")
            self.instances[tid] = deque(maxlen=self.depth)
            self.evicted_samples[tid] = 0

        inst_queue = self.instances[tid]
        
        # 2. Per-instance depth kontrolü (Ring buffer otomatik en eskiyi atar)
        if len(inst_queue) == self.depth:
            self.evicted_samples[tid] += 1
        else:
            self.total_samples_count += 1

        inst_queue.append(sample)
        return True

    def read_instance(self, track_id: str) -> List[RadarTrackSample]:
        if track_id not in self.instances:
            return []
        return list(self.instances[track_id])

# 3 Hedefli Radar Simülasyonu (Derinlik = 3)
radar_cache = KeyedInstanceHistoryCache(depth=3, max_instances=5, max_samples=20)

# Track_A için 5 örnek yaz (2'si ezilmeli, son 3'ü kalmalı)
for i in range(1, 6):
    radar_cache.write(RadarTrackSample("TRK_ALPHA", i, azimuth_deg=45.0 + i, range_km=100.0 - i*2))

# Track_B için 2 örnek yaz (0 ezilmeli, 2'si kalmalı)
for i in range(1, 3):
    radar_cache.write(RadarTrackSample("TRK_BRAVO", i, azimuth_deg=180.0 + i, range_km=50.0 + i*5))

samples_alpha = radar_cache.read_instance("TRK_ALPHA")
samples_bravo = radar_cache.read_instance("TRK_BRAVO")

print("[KOD 2] Per-Instance History Doğrulama Sonuçları:")
print(f"  - TRK_ALPHA Mevcut Örnekler: {[s.seq_num for s in samples_alpha]} (Beklenen: [3, 4, 5])")
print(f"  - TRK_ALPHA Ezilen Örnek   : {radar_cache.evicted_samples['TRK_ALPHA']} (Beklenen: 2)")
print(f"  - TRK_BRAVO Mevcut Örnekler: {[s.seq_num for s in samples_bravo]} (Beklenen: [1, 2])")
print(f"  - TRK_BRAVO Ezilen Örnek   : {radar_cache.evicted_samples['TRK_BRAVO']} (Beklenen: 0)")

assert [s.seq_num for s in samples_alpha] == [3, 4, 5]
assert radar_cache.evicted_samples["TRK_ALPHA"] == 2
assert [s.seq_num for s in samples_bravo] == [1, 2]
assert radar_cache.evicted_samples["TRK_BRAVO"] == 0

print("\n[PASS] Çok Anahtarlı Dairesel Bellek Motoru %100 Başarıyla Doğrulandı.")

# ==============================================================================
# KOD 3: Hızlı Yazar / Yavaş Okuyucu Asimetrisi ve Kuyruk Taşması Simülasyonu
# Amaç: 1000 Hz hızla üreten yazar karşısında 50 Hz tüketen okuyucunun
# farklı Reader History derinliklerindeki (D_R = 1, 5, 20) davranışını ölçmek.
# ==============================================================================

import time
from typing import List, Tuple

class DecoupledNodeSimulation:
    def __init__(self, writer_depth: int, reader_depth: int):
        self.writer_depth = writer_depth
        self.reader_depth = reader_depth
        self.reader_cache: List[int] = []
        self.consumed_samples: List[int] = []
        self.overwritten_count: int = 0

    def publish(self, seq_num: int):
        if len(self.reader_cache) >= self.reader_depth:
            # Okuyucu henüz okuyamadan üzerine yazıldı
            self.reader_cache.pop(0)
            self.overwritten_count += 1
        self.reader_cache.append(seq_num)

    def consume(self):
        # Okuyucu uyanır ve kuyruktaki tüm örnekleri okur
        while self.reader_cache:
            self.consumed_samples.append(self.reader_cache.pop(0))

depth_configs = [1, 5, 20]
results: Dict[int, Tuple[int, int]] = {} # depth -> (consumed, overwritten)

TOTAL_PUBLISHED = 200 # 200 ms'lik döngü (1 ms'de bir üretim = 1000 Hz)
CONSUME_INTERVAL = 20 # Her 20 ms'de bir tüketim = 50 Hz

for d in depth_configs:
    sim = DecoupledNodeSimulation(writer_depth=10, reader_depth=d)
    for tick in range(1, TOTAL_PUBLISHED + 1):
        sim.publish(tick)
        if tick % CONSUME_INTERVAL == 0:
            sim.consume()
    # Kalanları tüket
    sim.consume()
    results[d] = (len(sim.consumed_samples), sim.overwritten_count)

print("[KOD 3] Hızlı Yazar (1000 Hz) / Yavaş Okuyucu (50 Hz) Sonuçları:")
for d in depth_configs:
    consumed, dropped = results[d]
    retention_pct = (consumed / TOTAL_PUBLISHED) * 100
    print(f"  - Reader Depth = {d:2d} -> Tüketilen: {consumed:3d}, Ezilen: {dropped:3d}, Teslim Oranı: %{retention_pct:.1f}")

assert results[1][0] == 10, "Depth=1 iken her 20ms'de sadece 1 örnek yakalanabilir (Toplam 10 tüketim)!"
assert results[20][0] == 200, "Depth=20 iken 20ms'de üretilen 20 örneğin tümü tutulmalıdır (0 kayıp)!"
assert results[1][1] == 190, "Depth=1 iken 190 örnek ezilmiş olmalıdır!"

print("\n[PASS] Writer/Reader History Asimetri Testi Başarıyla Tamamlandı.")

# ==============================================================================
# KOD 4: Hata Enjeksiyonu (Fault Injection) ve Savunma Dayanıklılık Testleri
# Senaryolar:
#   Test A: SAMPLE_REJECTED (ResourceLimits Aşımı)
#   Test B: SAMPLE_LOST Tespiti ve Sayacı
#   Test C: KEEP_ALL + RELIABLE Deadlock Koruması (Timeout)
# ==============================================================================

from enum import Enum

class SampleRejectedReason(Enum):
    NOT_REJECTED = 0
    REJECTED_BY_INSTANCES_LIMIT = 1
    REJECTED_BY_SAMPLES_LIMIT = 2
    REJECTED_BY_SAMPLES_PER_INSTANCE_LIMIT = 3

class HardenedDdsEntity:
    def __init__(self, history_kind: HistoryKind, depth: int, max_samples: int, max_blocking_ms: float = 20.0):
        self.history_kind = history_kind
        self.depth = depth
        self.max_samples = max_samples
        self.max_blocking_ms = max_blocking_ms
        self.cache: List[int] = []
        self.sample_rejected_count = 0
        self.sample_lost_count = 0

    def write_sample(self, seq_num: int, is_reader_acked: bool) -> SampleRejectedReason:
        # TEST A: KEEP_ALL modunda ResourceLimits aşımı
        if self.history_kind == HistoryKind.KEEP_ALL:
            if len(self.cache) >= self.max_samples:
                self.sample_rejected_count += 1
                return SampleRejectedReason.REJECTED_BY_SAMPLES_LIMIT
            self.cache.append(seq_num)
            return SampleRejectedReason.NOT_REJECTED

        # TEST B: KEEP_LAST modunda Sample Lost oluşumu
        elif self.history_kind == HistoryKind.KEEP_LAST:
            if len(self.cache) >= self.depth:
                self.cache.pop(0) # Eski örnek ezildi!
                self.sample_lost_count += 1
            self.cache.append(seq_num)
            return SampleRejectedReason.NOT_REJECTED

    def write_reliable_blocking(self, seq_num: int, is_reader_acked: bool) -> bool:
        # TEST C: RELIABLE + KEEP_ALL'da ACK yoksa bloklama ve timeout
        if len(self.cache) >= self.max_samples and not is_reader_acked:
            # max_blocking_time aşıldı simülasyonu
            raise TimeoutError(f"DDS_RETCODE_TIMEOUT: {self.max_blocking_ms}ms içinde okuyucu onayı gelmedi, yazma engellendi!")
        self.cache.append(seq_num)
        return True

# TEST A Çalıştırma: max_samples=3 olan KEEP_ALL sistemine 5 örnek gönderme
entity_a = HardenedDdsEntity(HistoryKind.KEEP_ALL, depth=1, max_samples=3)
rejections = []
for sn in range(1, 6):
    reason = entity_a.write_sample(sn, is_reader_acked=True)
    rejections.append(reason)

print("[TEST A] ResourceLimits Aşımı Testi:")
print(f"  - Başarılı Yazılan Örnek : {len(entity_a.cache)} (Beklenen: 3)")
print(f"  - Reddedilen Örnek Sayısı: {entity_a.sample_rejected_count} (Beklenen: 2)")
print(f"  - Son Reddedilme Nedeni  : {rejections[-1].name}")

assert len(entity_a.cache) == 3
assert entity_a.sample_rejected_count == 2
assert rejections[-1] == SampleRejectedReason.REJECTED_BY_SAMPLES_LIMIT

# TEST B Çalıştırma: depth=2 olan KEEP_LAST sisteminde Sample Lost sayımı
entity_b = HardenedDdsEntity(HistoryKind.KEEP_LAST, depth=2, max_samples=10)
for sn in range(1, 6):
    entity_b.write_sample(sn, is_reader_acked=True)

print("\n[TEST B] SAMPLE_LOST Sayacı Testi:")
print(f"  - Önbellekte Kalan Örnek : {len(entity_b.cache)} (Beklenen: 2)")
print(f"  - Kayıp/Ezilen Örnek     : {entity_b.sample_lost_count} (Beklenen: 3)")

assert entity_b.sample_lost_count == 3
assert len(entity_b.cache) == 2

# TEST C Çalıştırma: Deadlock Engelleme (Timeout)
entity_c = HardenedDdsEntity(HistoryKind.KEEP_ALL, depth=1, max_samples=2, max_blocking_ms=10.0)
entity_c.write_reliable_blocking(1, is_reader_acked=False)
entity_c.write_reliable_blocking(2, is_reader_acked=False)

timeout_detected = False
try:
    entity_c.write_reliable_blocking(3, is_reader_acked=False) # Tampon dolu ve ACK yok!
except TimeoutError as ex:
    timeout_detected = True
    print(f"\n[TEST C] Deadlock Engellendi: {ex}")

assert timeout_detected, "Zaman aşımı tetiklenmeli ve sonsuz kilitlenme engellenmelidir!"

print("\n[PASS] 3 Kritik Savunma Güvenliği Testi Başarıyla Geçti.")

# ==============================================================================
# KOD 5: 50,000 Paketlik Radar İz Bellek ve Başarım Kıyaslaması
# Amaç: Farklı History Depth (1, 5, 20) ve KEEP_ALL profillerinde
# bellek tutma verimliliğini, atılan örnekleri ve işlem süresini ölçmek.
# ==============================================================================

import time
import sys
from collections import deque
from typing import Dict, List

NUM_TRACKS = 10
TOTAL_UPDATES = 50000

configs = [
    ("KEEP_LAST (D=1)", HistoryKind.KEEP_LAST, 1),
    ("KEEP_LAST (D=5)", HistoryKind.KEEP_LAST, 5),
    ("KEEP_LAST (D=20)", HistoryKind.KEEP_LAST, 20),
    ("KEEP_ALL", HistoryKind.KEEP_ALL, 0)
]

benchmark_results = {}

for name, kind, d in configs:
    # Bellek yapısı: track_id -> deque
    storage: Dict[int, deque] = {tid: deque(maxlen=d if kind == HistoryKind.KEEP_LAST else None) for tid in range(NUM_TRACKS)}
    
    t_start = time.perf_counter_ns()
    dropped_count = 0
    
    for i in range(TOTAL_UPDATES):
        tid = i % NUM_TRACKS
        q = storage[tid]
        if kind == HistoryKind.KEEP_LAST and len(q) == d:
            dropped_count += 1
        q.append(i)
        
    t_elapsed_ns = time.perf_counter_ns() - t_start
    total_stored = sum(len(q) for q in storage.values())
    avg_latency_us = (t_elapsed_ns / TOTAL_UPDATES) / 1000.0
    
    # Yaklaşık bellek hesabı (her tam sayı 8 bayt + deque overhead ~64 bayt)
    approx_mem_kb = (total_stored * 72) / 1024.0
    
    benchmark_results[name] = {
        "stored": total_stored,
        "dropped": dropped_count,
        "latency_us": avg_latency_us,
        "mem_kb": approx_mem_kb
    }

print("[KOD 5] 50,000 Paketlik Radar Takip History Kıyaslama Sonuçları:")
for name, data in benchmark_results.items():
    print(f"\n--- {name} ---")
    print(f"  - Saklanan Toplam Örnek : {data['stored']:,}")
    print(f"  - Atılan (Ezilen) Örnek : {data['dropped']:,}")
    print(f"  - Bellek Ayak İzi       : {data['mem_kb']:.2f} KB")
    print(f"  - Ortalama İşlem Süresi : {data['latency_us']:.4f} µs")

assert benchmark_results["KEEP_LAST (D=1)"]["stored"] == 10
assert benchmark_results["KEEP_LAST (D=5)"]["stored"] == 50
assert benchmark_results["KEEP_LAST (D=20)"]["stored"] == 200
assert benchmark_results["KEEP_ALL"]["stored"] == 50000
assert benchmark_results["KEEP_ALL"]["dropped"] == 0

print("\n[PASS] 50,000 Paketlik Radar İz Benchmark Testi Başarıyla Tamamlandı.")

# ==============================================================================
# KOD 6: 4-Panelli Master Görselleştirme Paneli (Publication-Quality Artifact)
# Amaç: History QoS bellek modellerini, hızlı/yavaş ayrışmasını,
# per-instance derinlik davranışını ve başarım kıyaslamasını görselleştirmek.
# ==============================================================================

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# PNG dosya yolu belirleme (Dizin garantili)
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_205_qos_history_depth.png")
    except Exception:
        PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_205/gun_205_qos_history_depth.png"

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
# PANEL 1: KEEP_LAST (Ring Buffer) vs KEEP_ALL Bellek Yapısı
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. DDS History Bellek Mimarisi (Ring Buffer vs Dinamik Kuyruk)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

# KEEP_LAST Ring Buffer Şematiği
theta = np.linspace(0, 2*np.pi, 6, endpoint=False)
x_circle = 0.35 + 0.2 * np.cos(theta)
y_circle = 0.55 + 0.2 * np.sin(theta)

for i, (x, y) in enumerate(zip(x_circle, y_circle)):
    color = '#10B981' if i < 3 else '#64748B'
    ax1.scatter(x, y, s=650, color=color, edgecolors='#38BDF8', linewidth=2, zorder=4)
    ax1.text(x, y, f"S_{i+1}", color='white', ha='center', va='center', fontweight='bold', fontsize=9)

ax1.text(0.35, 0.55, "KEEP_LAST\nDepth = 5\n(Ring Buffer)", color='#38BDF8', ha='center', va='center', fontweight='bold', fontsize=10)
ax1.annotate("En Eski Ezilir (Eviction)", xy=(x_circle[0], y_circle[0]), xytext=(0.05, 0.85),
             arrowprops=dict(facecolor='#EF4444', shrink=0.08, width=2, headwidth=8),
             color='#F87171', fontweight='bold', fontsize=9)

# KEEP_ALL Çizgisel Şematiği
y_bars = np.linspace(0.8, 0.2, 5)
for i, y_b in enumerate(y_bars):
    ax1.add_patch(plt.Rectangle((0.70, y_b - 0.04), 0.22, 0.08, facecolor='#6366F1', edgecolor='#A5B4FC', linewidth=1.5))
    ax1.text(0.81, y_b, f"Alarm_{i+1} (Olay {i+1})", color='white', ha='center', va='center', fontsize=9, fontweight='bold')

ax1.text(0.81, 0.90, "KEEP_ALL (Kayıpsız Liste)", color='#818CF8', ha='center', va='center', fontweight='bold', fontsize=10)
ax1.text(0.81, 0.10, "Risk: ResourceLimits Yoksa OOM!", color='#F87171', ha='center', va='center', fontstyle='italic', fontsize=9)

ax1.set_xlim(0, 1)
ax1.set_ylim(0, 1)
ax1.axis('off')

# ------------------------------------------------------------------------------
# PANEL 2: Hızlı Yazar / Yavaş Okuyucu Veri Kaybı Dinamiği
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. Hızlı Yazar (1 kHz) / Yavaş Okuyucu (50 Hz) Veri Tutma Oranı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

depths = ['Depth = 1\n(Son Değer)', 'Depth = 5\n(Kısa Tampon)', 'Depth = 20\n(Tam Tampon)']
delivered = [10, 50, 200]
dropped = [190, 150, 0]

x_pos = np.arange(len(depths))
w = 0.35

rects1 = ax2.bar(x_pos - w/2, delivered, w, label='Tüketilen Örnek', color='#10B981', alpha=0.9, edgecolor='#059669')
rects2 = ax2.bar(x_pos + w/2, dropped, w, label='Ezilen (Kayıp) Örnek', color='#EF4444', alpha=0.9, edgecolor='#DC2626')

ax2.set_ylabel("Paket Sayısı (Toplam 200)", color='#E2E8F0', fontsize=10)
ax2.set_xticks(x_pos)
ax2.set_xticklabels(depths, color='#E2E8F0', fontsize=10)
ax2.legend(facecolor='#1E293B', edgecolor='#475569', labelcolor='#E2E8F0')

for r in rects1:
    h = r.get_height()
    ax2.text(r.get_x() + r.get_width()/2., h + 3, f"{int(h)}", ha='center', va='bottom', color='#A7F3D0', fontweight='bold', fontsize=9)
for r in rects2:
    h = r.get_height()
    ax2.text(r.get_x() + r.get_width()/2., h + 3, f"{int(h)}", ha='center', va='bottom', color='#FECACA', fontweight='bold', fontsize=9)

ax2.set_ylim(0, 230)

# ------------------------------------------------------------------------------
# PANEL 3: Çok Anahtarlı (Multi-Instance) Radar İz Bellek Dağılımı
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. Çok Anahtarlı Radar İz Bellek Ayrımı (Per-Instance Depth = 3)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

tracks = ['TRK_ALPHA\n(F-16)', 'TRK_BRAVO\n(İHA-TB2)', 'TRK_CHARLIE\n(Seyir Füzesi)']
inst_colors = ['#0284C7', '#D97706', '#9333EA']

for idx, (trk, col) in enumerate(zip(tracks, inst_colors)):
    y_center = 2 - idx
    ax3.text(0.1, y_center, trk, color='white', fontweight='bold', va='center', fontsize=10)
    for slot in range(3):
        x_slot = 0.45 + slot * 0.18
        ax3.add_patch(plt.Rectangle((x_slot, y_center - 0.25), 0.14, 0.5, facecolor=col, alpha=0.8, edgecolor='white', linewidth=1.5))
        sn_val = (idx+1)*10 + slot + 1
        ax3.text(x_slot + 0.07, y_center, f"SN_{sn_val}", color='white', ha='center', va='center', fontweight='bold', fontsize=9)

ax3.text(0.63, -0.3, "Her hedefe ait ring buffer tamamen izoledir. Asla birbirini ezmez!",
         color='#FCD34D', ha='center', fontstyle='italic', fontsize=10)

ax3.set_xlim(0, 1.05)
ax3.set_ylim(-0.5, 2.7)
ax3.axis('off')

# ------------------------------------------------------------------------------
# PANEL 4: 50,000 Örnekli Başarım ve Bellek Ayak İzi Kıyaslaması
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. 50,000 Paketlik Radar Takip: Bellek Ayak İzi vs Kayıp Oranı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

configs_labels = ['D=1', 'D=5', 'D=20', 'KEEP_ALL']
mem_vals = [0.70, 3.52, 14.06, 3515.62] # KB
drop_pcts = [99.98, 99.90, 99.60, 0.0]

ax4_twin = ax4.twinx()

line1 = ax4.plot(configs_labels, mem_vals, color='#F59E0B', marker='o', linewidth=2.5, markersize=8, label='Bellek Ayak İzi (KB)')
line2 = ax4_twin.plot(configs_labels, drop_pcts, color='#EC4899', marker='s', linewidth=2.5, markersize=8, linestyle='--', label='Atılan Örnek Oranı (%)')

ax4.set_yscale('log')
ax4.set_ylabel("Bellek Ayak İzi (KB - Logaritmik)", color='#F59E0B', fontsize=10)
ax4_twin.set_ylabel("Atılan (Ezilen) Örnek Oranı (%)", color='#EC4899', fontsize=10)
ax4.set_xlabel("DDS History Konfigürasyonu", color='#E2E8F0', fontsize=10)

ax4.tick_params(axis='y', colors='#F59E0B')
ax4_twin.tick_params(axis='y', colors='#EC4899')
ax4_twin.grid(False)

# Birleşik Lejant
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax4.legend(lines, labels, loc='center left', facecolor='#1E293B', edgecolor='#475569', labelcolor='#E2E8F0')

plt.tight_layout()
plt.savefig(PNG_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

# Üretilen PNG Dosya Boyutu Kontrolü
file_size_bytes = os.path.getsize(PNG_FILE)
file_size_kb = file_size_bytes / 1024.0

print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {PNG_FILE}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'nin üzerinde olmalıdır!"

