#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

TARGET_DIR = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_207"
PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_207/gun_207_qos_deadline.png"

# ==============================================================================
# KOD 1: Minimal Deadline Sözleşmesi ve Zaman Aşımı Simülatörü
# Amaç: Belirlenen periyodun (12 ms) aşılması durumunda
# on_requested_deadline_missed durumunun tetiklendiğini doğrulamak.
# ==============================================================================

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DeadlineStatus:
    total_count: int = 0
    total_count_change: int = 0
    last_instance_handle: Optional[str] = None

class MinimalDeadlineMonitor:
    def __init__(self, requested_deadline_ms: float):
        self.requested_deadline_ms = requested_deadline_ms
        self.last_arrival_time_ms: Optional[float] = None
        self.status = DeadlineStatus()
        self.received_samples: List[str] = []

    def on_data_arrived(self, current_time_ms: float, payload: str, instance_id: str = "DEFAULT"):
        if self.last_arrival_time_ms is not None:
            delta_t = current_time_ms - self.last_arrival_time_ms
            # Deadline Kontrolü
            if delta_t > self.requested_deadline_ms:
                self.status.total_count += 1
                self.status.total_count_change = 1
                self.status.last_instance_handle = instance_id
                print(f"[ALARM] DEADLINE MISSED! Gecikme: {delta_t:.1f}ms (Tavan: {self.requested_deadline_ms}ms) Hedef: {instance_id}")
            else:
                self.status.total_count_change = 0

        self.last_arrival_time_ms = current_time_ms
        self.received_samples.append(payload)

# Simülasyon: 100 Hz Beklenti (Requested Deadline = 12.0 ms)
monitor = MinimalDeadlineMonitor(requested_deadline_ms=12.0)

# Zaman çizelgesi simülasyonu (ms): t=0, t=10, t=20 (Normal), t=45 (25ms gecikme -> Missed!)
timeline = [
    (0.0, "ALT_1000m"),
    (10.0, "ALT_1002m"),
    (20.0, "ALT_1005m"),
    (45.0, "ALT_1010m") # 25 ms aralık! (Deadline 12 ms idi)
]

for t, data in timeline:
    monitor.on_data_arrived(current_time_ms=t, payload=data)

print(f"\n[KOD 1] Simülasyon Sonuçları:")
print(f"  - Toplam Alınan Örnek      : {len(monitor.received_samples)} (Beklenen: 4)")
print(f"  - Kaçırılan Deadline Sayısı: {monitor.status.total_count} (Beklenen: 1)")

assert len(monitor.received_samples) == 4
assert monitor.status.total_count == 1, "Tam olarak 1 adet deadline ihlali tespit edilmelidir!"

print("\n[PASS] Kod 1 Minimal Deadline Takip Mekanizması Başarıyla Doğrulandı.")

# ==============================================================================
# KOD 2: Çok Anahtarlı (Multi-Instance) Bağımsız Deadline Takip Motoru
# Amaç: Farklı anahtarlara (@key) sahip hedeflerin bağımsız süreölçerlerle
# denetlenmesini ve sinyali kesilen hedefin izole olarak yakalanmasını doğrulamak.
# ==============================================================================

from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class InstanceDeadlineState:
    last_update_ms: float
    missed_count: int = 0
    is_alive: bool = True

class MultiInstanceDeadlineEngine:
    def __init__(self, deadline_period_ms: float):
        self.deadline_period_ms = deadline_period_ms
        self.instances: Dict[str, InstanceDeadlineState] = {}

    def update_sample(self, track_id: str, current_time_ms: float):
        if track_id not in self.instances:
            self.instances[track_id] = InstanceDeadlineState(last_update_ms=current_time_ms)
        else:
            state = self.instances[track_id]
            delta_t = current_time_ms - state.last_update_ms
            if delta_t > self.deadline_period_ms:
                state.missed_count += 1
                state.is_alive = False
            else:
                state.is_alive = True
            state.last_update_ms = current_time_ms

    def check_deadlines_at(self, current_time_ms: float) -> List[str]:
        # Watchdog periyodik kontrolü (Veri gelmese bile süre doldu mu?)
        timed_out_tracks = []
        for tid, state in self.instances.items():
            if state.is_alive and (current_time_ms - state.last_update_ms > self.deadline_period_ms):
                state.missed_count += 1
                state.is_alive = False
                timed_out_tracks.append(tid)
        return timed_out_tracks

# 3 Hedefli Radar Simülasyonu (Deadline = 20.0 ms)
engine = MultiInstanceDeadlineEngine(deadline_period_ms=20.0)

# t = 0ms: 3 hedef de sisteme kaydolur
engine.update_sample("TRK_ALPHA", current_time_ms=0.0)
engine.update_sample("TRK_BRAVO", current_time_ms=0.0)
engine.update_sample("TRK_CHARLIE", current_time_ms=0.0)

# t = 15ms: TRK_ALPHA ve TRK_BRAVO güncellenir (Normal)
engine.update_sample("TRK_ALPHA", current_time_ms=15.0)
engine.update_sample("TRK_BRAVO", current_time_ms=15.0)

# t = 30ms: TRK_ALPHA güncellenir, TRK_CHARLIE hiç gelmez!
engine.update_sample("TRK_ALPHA", current_time_ms=30.0)

# t = 25ms anında Watchdog kontrolü: TRK_CHARLIE 25 ms'dir veri üretmedi (Deadline 20 ms)!
timed_out = engine.check_deadlines_at(current_time_ms=25.0)

print("[KOD 2] Çok Anahtarlı Deadline İzleme Durumu (t = 25 ms):")
print(f"  - Zaman Aşımına Uğrayan Hedefler: {timed_out} (Beklenen: ['TRK_CHARLIE'])")
for tid, state in engine.instances.items():
    print(f"  - {tid:<12} -> Son Görülme: {state.last_update_ms:4.1f}ms, Missed Count: {state.missed_count}, Canlı Mı: {state.is_alive}")

assert timed_out == ["TRK_CHARLIE"], "Yalnızca TRK_CHARLIE zaman aşımına uğramalıdır!"
assert engine.instances["TRK_ALPHA"].missed_count == 0
assert engine.instances["TRK_BRAVO"].missed_count == 0
assert engine.instances["TRK_CHARLIE"].missed_count == 1

print("\n[PASS] Çok Anahtarlı Deadline Takip Motoru %100 Başarıyla Doğrulandı.")

# ==============================================================================
# KOD 3: RxO Deadline Eşleşme Matrisi Simülatörü
# Amaç: Offered.period <= Requested.period kuralının tüm kombinasyonlarda
# doğru çalıştığını ve uyumsuz periyotların reddedildiğini doğrulamak.
# ==============================================================================

periods = [5, 10, 20, 50, 100] # milisaniye cinsinden periyotlar
rxo_deadline_matrix = {}

pass_count = 0
fail_count = 0

for off in periods:
    for req in periods:
        # Kural: Offered <= Requested
        compatible = (off <= req)
        rxo_deadline_matrix[(off, req)] = compatible
        if compatible:
            pass_count += 1
        else:
            fail_count += 1

print("[KOD 3] DDS Deadline RxO Uyumluluk Matrisi (Offered <= Requested):")
header_cols = " | ".join([f"{p}ms".ljust(6) for p in periods])
print(f"{'Offered \\ Requested':<20} | {header_cols}")
print("-" * 65)

for off in periods:
    row_str = f"{off}ms{'':<16} | "
    for req in periods:
        res = "PASS" if rxo_deadline_matrix[(off, req)] else "FAIL"
        row_str += f"{res:<6} | "
    print(row_str)

print(f"\nToplam Test Edilen İkili : {len(rxo_deadline_matrix)}")
print(f"Uyumlu (PASS)            : {pass_count} (Beklenen: 15)")
print(f"Uyumsuz (FAIL)           : {fail_count} (Beklenen: 10)")

assert pass_count == 15
assert fail_count == 10
assert rxo_deadline_matrix[(10, 20)] is True  # 10ms sunan, 20ms isteyeni doyurur
assert rxo_deadline_matrix[(50, 10)] is False # 50ms sunan, 10ms isteyene yetemez!

print("\n[PASS] Deadline RxO Eşleşme Matrisi %100 Başarıyla Doğrulandı.")

# ==============================================================================
# KOD 4: Hata Enjeksiyonu (Fault Injection) ve Savunma Dayanıklılık Testleri
# Senaryolar:
#   Test A: Ağ Jitter'ı Nedeniyle Deadline İhlali
#   Test B: Donan Sensör Karşısında Otomatik Fail-Safe (Dead Reckoning) Tetikleme
#   Test C: RxO Uyumsuzluğunun Reddedilmesi
# ==============================================================================

class DefenseFlightControlNode:
    def __init__(self, requested_deadline_ms: float):
        self.requested_deadline_ms = requested_deadline_ms
        self.control_mode = "NORMAL_SENSOR_FEED"
        self.missed_deadlines = 0
        self.last_packet_time_ms = 0.0

    def receive_telemetry(self, current_time_ms: float, is_valid: bool):
        delta = current_time_ms - self.last_packet_time_ms
        if delta > self.requested_deadline_ms:
            self.missed_deadlines += 1
            # FAIL-SAFE KORUMASI: 2 ardışık deadline kaçarsa otopilot kestirime geçer
            if self.missed_deadlines >= 2:
                self.control_mode = "FAILSAFE_DEAD_RECKONING"
                print(f"[FAILSAFE AKTİF] Otopilot DEAD RECKONING moduna geçti! (Delta: {delta:.1f}ms)")
        else:
            self.missed_deadlines = 0 # Sıfırla
            self.control_mode = "NORMAL_SENSOR_FEED"

        self.last_packet_time_ms = current_time_ms

# TEST A & B: Sensör Donması ve Fail-Safe Doğrulama
node = DefenseFlightControlNode(requested_deadline_ms=15.0)

# Normal akış: t=0, 10, 20
node.receive_telemetry(0.0, True)
node.receive_telemetry(10.0, True)
node.receive_telemetry(20.0, True)
assert node.control_mode == "NORMAL_SENSOR_FEED"

# Sensör donar: t=40 (20 ms aralık -> 1. ihlal), t=65 (25 ms aralık -> 2. ihlal)
node.receive_telemetry(40.0, True)
assert node.missed_deadlines == 1
assert node.control_mode == "NORMAL_SENSOR_FEED"

node.receive_telemetry(65.0, True)
print(f"[TEST B] Fail-Safe Durumu: {node.control_mode} (Kaçırılan: {node.missed_deadlines})")
assert node.missed_deadlines == 2
assert node.control_mode == "FAILSAFE_DEAD_RECKONING", "2. ihlalde fail-safe aktifleşmelidir!"

# TEST C: RxO Uyumsuzluğu
class EndpointMatcher:
    @staticmethod
    def match(offered_deadline: float, requested_deadline: float) -> bool:
        if offered_deadline > requested_deadline:
            raise ValueError(f"INCOMPATIBLE_QOS: Offered ({offered_deadline}ms) > Requested ({requested_deadline}ms)")
        return True

rxo_failed = False
try:
    EndpointMatcher.match(offered_deadline=50.0, requested_deadline=20.0)
except ValueError as ex:
    rxo_failed = True
    print(f"\n[TEST C] RxO Hatası Başarıyla Yakalandı: {ex}")

assert rxo_failed, "Yavaş yazar hızlı okuyucu ile eşleşemez!"

print("\n[PASS] 3 Kritik Savunma Güvenliği Testi Başarıyla Geçti.")

# ==============================================================================
# KOD 5: 50,000 Paketlik Uçuş Kontrol Jitter ve Deadline Kıyaslaması
# Amaç: Farklı Requested Deadline toleranslarında (11ms, 13ms, 16ms)
# kaçırılan deadline sayısını ve yanlış alarm oranını ölçmek.
# ==============================================================================

import numpy as np

NUM_SAMPLES = 50000
MEAN_PERIOD_MS = 10.0
STD_DEV_MS = 1.8 # Gerçekçi ağ ve scheduling jitter'ı

np.random.seed(42)
intervals = np.random.normal(MEAN_PERIOD_MS, STD_DEV_MS, NUM_SAMPLES)
# Fiziksel kısıt: zaman farkı negatif olamaz
intervals = np.maximum(intervals, 1.0)

test_deadlines = [11.0, 13.0, 16.0]
benchmark_results = {}

for dl in test_deadlines:
    missed_count = int(np.sum(intervals > dl))
    miss_rate_pct = (missed_count / NUM_SAMPLES) * 100.0
    benchmark_results[dl] = {
        "missed": missed_count,
        "rate_pct": miss_rate_pct
    }

print("[KOD 5] 50,000 Örnekli Uçuş Kontrol Jitter ve Deadline İstatistikleri:")
for dl, res in benchmark_results.items():
    print(f"\n--- Requested Deadline = {dl:.1f} ms ---")
    print(f"  - Kaçırılan Paket Sayısı : {res['missed']:,} / {NUM_SAMPLES:,}")
    print(f"  - Deadline İhlal Oranı   : %{res['rate_pct']:.2f}")

assert benchmark_results[11.0]["missed"] > benchmark_results[13.0]["missed"]
assert benchmark_results[13.0]["missed"] > benchmark_results[16.0]["missed"]
assert benchmark_results[16.0]["rate_pct"] < 1.0, "3-Sigma toleransında ihlal %1'in altında olmalıdır!"

print("\n[PASS] 50,000 Paketlik Uçuş Kontrol Benchmark Testi Başarıyla Tamamlandı.")

# ==============================================================================
# KOD 6: 4-Panelli Master Görselleştirme Paneli (Publication-Quality Artifact)
# Amaç: Deadline mekanizmasını, per-instance takibini,
# RxO matrisini ve 50,000 örnekli jitter istatistiklerini belgelemek.
# ==============================================================================

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# PNG dosya yolu belirleme (Dizin garantili)
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_207_qos_deadline.png")
    except Exception:
        PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_207/gun_207_qos_deadline.png"

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
# PANEL 1: Deadline Zaman Dalga Formu ve Alarm Tetiklenmesi
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. DDS Deadline İzleme Dalga Formu ve Watchdog Alarmı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

t_points = [0, 10, 20, 45, 55]
y_vals = [1, 1, 1, 1, 1]

ax1.plot([0, 60], [1, 1], color='#475569', linestyle='--', linewidth=1.5)
ax1.scatter([0, 10, 20, 55], [1, 1, 1, 1], color='#10B981', s=250, label='Zamanında Gelen Örnek', zorder=5)
ax1.scatter([45], [1], color='#EF4444', s=350, marker='X', label='Deadline İhlali Sonrası Örnek', zorder=6)

# Deadline Eşik Çizgisi
ax1.axvline(x=32, color='#F59E0B', linestyle=':', linewidth=2, label='Deadline Eşiği (t = 20 + 12 = 32ms)')
ax1.annotate("Requested Deadline Missed!\n(Delta = 25ms > 12ms)", xy=(32, 1), xytext=(22, 1.4),
             arrowprops=dict(facecolor='#EF4444', shrink=0.08, width=2, headwidth=7),
             color='#FCA5A5', fontweight='bold', fontsize=9)

ax1.set_xlim(-5, 65)
ax1.set_ylim(0.5, 1.8)
ax1.set_xlabel("Zaman (Milisaniye)", color='#E2E8F0', fontsize=10)
ax1.set_yticks([])
ax1.legend(loc='lower left', facecolor='#1E293B', edgecolor='#475569', labelcolor='#E2E8F0')

# ------------------------------------------------------------------------------
# PANEL 2: Çok Anahtarlı (Per-Instance) Radar Takip Durumu
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. Çok Anahtarlı Radar Takip Deadline İzolasyonu (Per-Instance)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

tracks = ['TRK_ALPHA (F-16)', 'TRK_BRAVO (İHA)', 'TRK_CHARLIE (Füze)']
last_seen = [30.0, 15.0, 0.0]
status_cols = ['#10B981', '#10B981', '#EF4444']
labels = ['CANLI (0 ihlal)', 'CANLI (0 ihlal)', 'ZAMAN AŞIMI (1 ihlal)']

y_idx = np.arange(len(tracks))
bars = ax2.barh(y_idx, [30, 25, 25], color=['#0284C7', '#0284C7', '#7F1D1D'], alpha=0.6, edgecolor='white')

for i, (trk, col, lbl) in enumerate(zip(tracks, status_cols, labels)):
    ax2.text(1, i, f"{trk} -> {lbl}", color=col, fontweight='bold', va='center', fontsize=10)

ax2.axvline(x=20, color='#F59E0B', linestyle='--', linewidth=2, label='Deadline Limiti (20 ms)')
ax2.set_yticks(y_idx)
ax2.set_yticklabels(['', '', ''])
ax2.set_xlabel("Geçen Süre (ms)", color='#E2E8F0', fontsize=10)
ax2.legend(loc='lower right', facecolor='#1E293B', edgecolor='#475569', labelcolor='#E2E8F0')

# ------------------------------------------------------------------------------
# PANEL 3: 5x5 RxO Deadline Matrisi Isı Haritası
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. DDS Deadline RxO Matrisi (Offered <= Requested)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

periods_ticks = ["5ms", "10ms", "20ms", "50ms", "100ms"]
matrix_m = np.zeros((5, 5))
for i, off in enumerate([5, 10, 20, 50, 100]):
    for j, req in enumerate([5, 10, 20, 50, 100]):
        matrix_m[i, j] = 1 if off <= req else 0

ax3.imshow(matrix_m, cmap='RdYlGn', vmin=0, vmax=1.2, aspect='auto')
ax3.set_xticks(range(5))
ax3.set_yticks(range(5))
ax3.set_xticklabels(periods_ticks, color='#E2E8F0', fontsize=9)
ax3.set_yticklabels(periods_ticks, color='#E2E8F0', fontsize=9)
ax3.set_xlabel("Requested Deadline (DataReader)", color='#E2E8F0', fontsize=10)
ax3.set_ylabel("Offered Deadline (DataWriter)", color='#E2E8F0', fontsize=10)

for i in range(5):
    for j in range(5):
        txt = "PASS" if matrix_m[i, j] == 1 else "FAIL"
        col = "black" if matrix_m[i, j] == 1 else "white"
        ax3.text(j, i, txt, ha='center', va='center', color=col, fontweight='bold', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 4: 50,000 Paketlik Jitter Dağılımı ve Eşik Analizi
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. 50,000 Paketlik Uçuş Kontrol Jitter Dağılımı ve 3-Sigma Eşiği", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

counts, bins, _ = ax4.hist(intervals, bins=60, color='#6366F1', alpha=0.75, edgecolor='#4338CA', density=True)

ax4.axvline(x=10.0, color='#38BDF8', linestyle='-', linewidth=2, label='Nominal (10ms)')
ax4.axvline(x=11.0, color='#EF4444', linestyle='--', linewidth=2, label='Sıkı Eşik: 11ms (%28 İhlal)')
ax4.axvline(x=13.0, color='#F59E0B', linestyle='--', linewidth=2, label='Dengeli Eşik: 13ms (%4 İhlal)')
ax4.axvline(x=16.0, color='#10B981', linestyle='-', linewidth=2.5, label='3-Sigma Eşik: 16ms (%0.05 İhlal)')

ax4.set_xlabel("İki Paket Arasındaki Süre (ms)", color='#E2E8F0', fontsize=10)
ax4.set_ylabel("Olasılık Yoğunluğu", color='#E2E8F0', fontsize=10)
ax4.legend(loc='upper right', facecolor='#1E293B', edgecolor='#475569', labelcolor='#E2E8F0', fontsize=9)

plt.tight_layout()
plt.savefig(PNG_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

# Üretilen PNG Dosya Boyutu Kontrolü
file_size_bytes = os.path.getsize(PNG_FILE)
file_size_kb = file_size_bytes / 1024.0

print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {PNG_FILE}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'nin üzerinde olmalıdır!"

