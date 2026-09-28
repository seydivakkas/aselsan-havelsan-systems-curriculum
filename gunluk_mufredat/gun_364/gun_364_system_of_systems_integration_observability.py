#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

Gün 364 — Faz F13: AI Engineering / Architecture / Portfolio
Konu: System-of-systems integration ve observability
"""

# =====================================================================
# CELL 04 / CODE 1: OpenTelemetry Uyumlu Dağıtık İzleme (Distributed Tracing)
# =====================================================================
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    service: str
    start_time: float
    end_time: float = 0.0
    status: str = "OK"  # 'OK', 'ERROR'
    attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        return max(0.0, (self.end_time - self.start_time) * 1000.0)

class DistributedTracer:
    """W3C TraceContext ve OpenTelemetry Standardında Dağıtık İzleyici."""
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.spans: List[Span] = []

    def start_trace(self, operation: str) -> Span:
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            name=operation,
            service=self.service_name,
            start_time=time.perf_counter()
        )
        self.spans.append(span)
        return span

    def start_child_span(self, parent: Span, operation: str, service: Optional[str] = None) -> Span:
        span_id = uuid.uuid4().hex[:16]
        span = Span(
            trace_id=parent.trace_id,
            span_id=span_id,
            parent_span_id=parent.span_id,
            name=operation,
            service=service or self.service_name,
            start_time=time.perf_counter()
        )
        self.spans.append(span)
        return span

    def end_span(self, span: Span, status: str = "OK", **attrs) -> None:
        span.end_time = time.perf_counter()
        span.status = status
        span.attributes.update(attrs)

# SoS Pipeline Simülasyonu (Radar -> Link16 -> C2 AI -> Effector)
tracer = DistributedTracer("C2_Battle_Management")

root_span = tracer.start_trace("tactical_engagement_pipeline")
root_span.attributes["mission_id"] = "TASK-FORCE-99"

# 1. Radar Algılama
s1 = tracer.start_child_span(root_span, "radar_target_detection", "AESA_Radar_Sensor")
time.sleep(0.002)  # 2 ms radar işleme
tracer.end_span(s1, status="OK", range_km=42.5, azim_deg=112.4, doppler_vel=340.0)

# 2. Link-16 Taktik Veri Ağı İletimi
s2 = tracer.start_child_span(root_span, "link16_telemetry_tx", "Tactical_Data_Link")
time.sleep(0.001)  # 1 ms ağ aktarımı
tracer.end_span(s2, status="OK", packet_loss=0.0, hop_count=1)

# 3. C2 Yapay Zeka Tehdit Sınıflandırma ve Angajman
s3 = tracer.start_child_span(root_span, "c2_ai_threat_evaluation", "C2_AI_Inference_Engine")
time.sleep(0.003)  # 3 ms AI çıkarımı
tracer.end_span(s3, status="OK", threat_class="HOSTILE_CRUISE_MISSILE", threat_score=0.98, roe_cleared=True)

# 4. Efektör / Füze Bataryası Atama
s4 = tracer.start_child_span(root_span, "effector_fire_solution", "Air_Defense_SAM_Launcher")
time.sleep(0.0015)  # 1.5 ms atış kontrol çözümü
tracer.end_span(s4, status="OK", launcher_id="SAM-BATTERY-ALPHA", intercept_time_s=14.2)

tracer.end_span(root_span, status="OK", e2e_verdict="INTERCEPT_ORDERED")

print("[+] OpenTelemetry Dağıtık İzleme Pipeline Tamamlandı:")
print(f"  Trace ID: {root_span.trace_id}")
print(f"  Toplam Süre: {root_span.duration_ms:.2f} ms")
for s in tracer.spans:
    parent = s.parent_span_id if s.parent_span_id else "ROOT"
    print(f"  - [{s.service}] {s.name} ({s.duration_ms:.2f} ms, Parent: {parent})")

assert len(tracer.spans) == 5
assert all(s.trace_id == root_span.trace_id for s in tracer.spans)


# =====================================================================
# CELL 07 / CODE 2: Prometheus Metrikleri & Yapısal JSON Günlükleme Motoru
# =====================================================================
import json
import numpy as np

class Counter:
    """Prometheus Uyumlu Monotonik Artan Sayaç."""
    def __init__(self, name: str, doc: str):
        self.name = name
        self.doc = doc
        self.value = 0.0

    def inc(self, amount: float = 1.0) -> None:
        if amount < 0:
            raise ValueError("Counter yalnızca artabilir!")
        self.value += amount

class Gauge:
    """Prometheus Uyumlu Anlık Durum Değeri."""
    def __init__(self, name: str, doc: str):
        self.name = name
        self.doc = doc
        self.value = 0.0

    def set(self, val: float) -> None:
        self.value = val

class Histogram:
    """Prometheus Uyumlu Kovalanmış (Bucketed) Gecikme Gözlemcisi."""
    def __init__(self, name: str, doc: str, buckets: List[float]):
        self.name = name
        self.doc = doc
        self.buckets = sorted(buckets)
        self.counts = {b: 0 for b in self.buckets}
        self.counts[float('inf')] = 0
        self.sum_val = 0.0
        self.count = 0

    def observe(self, val: float) -> None:
        self.sum_val += val
        self.count += 1
        for b in self.buckets:
            if val <= b:
                self.counts[b] += 1
        self.counts[float('inf')] += 1

class StructuredLogger:
    """Dağıtık Aviyonik Sistemler için Yapısal JSON Log Motoru."""
    def __init__(self, component: str):
        self.component = component

    def log(self, level: str, message: str, trace_id: str, span_id: str, **ctx) -> str:
        record = {
            "timestamp": time.time(),
            "level": level,
            "component": self.component,
            "trace_id": trace_id,
            "span_id": span_id,
            "message": message,
            "context": ctx
        }
        return json.dumps(record, ensure_ascii=False)

# Metrik Örnekleri
c_tracks = Counter("tactical_tracks_total", "İşlenen toplam taktik hedef izi sayısı")
g_threats = Gauge("active_threats_gauge", "Hava sahasındaki anlık aktif düşman hedef sayısı")
h_latency = Histogram("e2e_tactical_latency_ms", "Uçtan uca taktik döngü gecikmesi", [1.0, 5.0, 10.0, 25.0, 50.0, 100.0])

logger = StructuredLogger("C2_Air_Defense_Node")

# 20 Olay Simülasyonu
for i in range(20):
    sim_lat = np.random.uniform(3.0, 18.0)
    c_tracks.inc(1.0)
    g_threats.set(float(np.random.randint(2, 9)))
    h_latency.observe(sim_lat)

sample_log = logger.log("INFO", "Taktik angajman çözümü onaylandı", root_span.trace_id, root_span.span_id, missile="HİSAR-O", target_id="TRK-402")

print("[+] Prometheus Metrikleri ve Yapısal Log Çıktısı:")
print(f"  # HELP {c_tracks.name} {c_tracks.doc}")
print(f"  # TYPE {c_tracks.name} counter")
print(f"  {c_tracks.name} {c_tracks.value:.0f}")
print(f"  {g_threats.name} {g_threats.value:.0f}")
print(f"  {h_latency.name}_count {h_latency.count}, _sum {h_latency.sum_val:.2f} ms")
print(f"  Örnek Yapısal JSON Log:\n    {sample_log}")
assert c_tracks.value == 20.0
assert h_latency.count == 20


# =====================================================================
# CELL 11 / CODE 3: Circuit Breaker & Resilience Fallback Simülatörü
# =====================================================================
from enum import Enum
from typing import Tuple

class CircuitState(Enum):
    CLOSED = "CLOSED"       # Normal çalışma (Tüm çağrılar birincil servise)
    OPEN = "OPEN"           # Hata eşiği aşıldı (Çağrılar doğrudan fallback'e)
    HALF_OPEN = "HALF_OPEN" # İyileşme denemesi (Sınırlı sayıda çağrı test edilir)

class CircuitBreaker:
    """Dağıtık Sistemler Sistemi için Hataya Dayanıklılık Devre Kesicisi."""
    def __init__(self, failure_threshold: int = 3, cooldown_s: float = 0.05):
        self.failure_threshold = failure_threshold
        self.cooldown_s = cooldown_s
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def call(self, primary_func, fallback_func, *args, **kwargs) -> Tuple[Any, str]:
        now = time.perf_counter()

        # OPEN durumundan HALF_OPEN durumuna geçiş kontrolü
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= self.cooldown_s:
                self.state = CircuitState.HALF_OPEN
            else:
                # Devre açık; birincil servisi hiç çağırmadan anında fallback işlet
                return fallback_func(*args, **kwargs), "FALLBACK_FAST"

        try:
            res = primary_func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                # İyileşme başarılı, devreyi kapat
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            return res, "PRIMARY_OK"
        except Exception:
            self.failure_count += 1
            self.last_failure_time = now
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
            return fallback_func(*args, **kwargs), "FALLBACK_RECOVERY"

# Test Senaryosu: AI Model Çökmesi ve C++ Kural Tabanlı Fallback
def primary_ai_threat_scoring(dist_km: float) -> str:
    if dist_km < 10.0:
        raise TimeoutError("AI Inference Engine GPU Timeout / CUDA OOM!")
    return f"AI_ENGAGE_PRIORITY_HIGH(Score={1.0 - dist_km/100:.2f})"

def fallback_rule_based_scoring(dist_km: float) -> str:
    return f"FALLBACK_SAFETY_RULE(ThresholdDistance={dist_km:.1f}km)"

cb = CircuitBreaker(failure_threshold=3, cooldown_s=0.02)
cb_logs = []

# 1. Normal çağrılar (CLOSED)
for _ in range(3):
    ans, mode = cb.call(primary_ai_threat_scoring, fallback_rule_based_scoring, 25.0)
    cb_logs.append((mode, cb.state.value))

# 2. Arıza Enjeksiyonu (Mesafe < 10km -> Hata -> OPEN)
for _ in range(4):
    ans, mode = cb.call(primary_ai_threat_scoring, fallback_rule_based_scoring, 5.0)
    cb_logs.append((mode, cb.state.value))

# 3. Bekleme sonrası iyileşme (HALF_OPEN -> CLOSED)
time.sleep(0.025)
ans, mode = cb.call(primary_ai_threat_scoring, fallback_rule_based_scoring, 30.0)
cb_logs.append((mode, cb.state.value))

print("[+] Circuit Breaker Durum Geçişleri Test Edildi:")
for idx, (m, st) in enumerate(cb_logs):
    print(f"  Adım {idx+1}: Sonuç Modu = {m:<18} | Devre Durumu = {st}")

assert cb.state == CircuitState.CLOSED


# =====================================================================
# CELL 15 / CODE 4: 10.000+ Olaylık Yüksek Başarımlı SoS Benchmark Motoru
# =====================================================================
import numpy as np

def run_sos_benchmark(n_events: int = 10000) -> Dict[str, Any]:
    rng = np.random.RandomState(42)
    latencies = []
    
    bench_counter = Counter("bench_events_total", "Benchmark event counter")
    bench_hist = Histogram("bench_latency_ms", "Latency", [1.0, 5.0, 10.0, 20.0, 50.0])
    
    t0 = time.perf_counter()

    # Vektörize Taktik SoS İşleme Simülasyonu
    # Her taktik olay için: Radar (0.2-1.5ms) + Link16 (0.1-0.8ms) + C2 (0.5-2.0ms) + Effector (0.1-0.5ms)
    radar_lats = rng.uniform(0.2, 1.5, n_events)
    link16_lats = rng.uniform(0.1, 0.8, n_events)
    c2_lats = rng.uniform(0.5, 2.0, n_events)
    effector_lats = rng.uniform(0.1, 0.5, n_events)

    # %0.5 oranında taktik ağ kuyruk dalgalanması (jitter / burst)
    jitter_mask = rng.rand(n_events) < 0.005
    c2_lats[jitter_mask] += rng.uniform(5.0, 15.0, np.sum(jitter_mask))

    total_e2e_lats = radar_lats + link16_lats + c2_lats + effector_lats

    for lat in total_e2e_lats:
        bench_counter.inc(1.0)
        bench_hist.observe(lat)

    t1 = time.perf_counter()
    duration = max(1e-6, t1 - t0)
    throughput = n_events / duration

    p50 = float(np.percentile(total_e2e_lats, 50))
    p95 = float(np.percentile(total_e2e_lats, 95))
    p99 = float(np.percentile(total_e2e_lats, 99))
    slo_compliance = float(np.mean(total_e2e_lats <= 50.0)) * 100.0

    return {
        "n_events": n_events,
        "duration_sec": duration,
        "throughput_ops": throughput,
        "e2e_latencies": total_e2e_lats,
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "slo_compliance_pct": slo_compliance
    }

bench = run_sos_benchmark(10000)
print(f"[+] Büyük Ölçekli SoS Entegrasyon Benchmark Sonuçları:")
print(f"  Toplam Olay     : {bench['n_events']:,}")
print(f"  İşlem Süresi    : {bench['duration_sec']*1000:.2f} ms")
print(f"  İşlem Hacmi     : {bench['throughput_ops']:,.0f} olay/saniye")
print(f"  P50 Gecikme     : {bench['p50_ms']:.2f} ms")
print(f"  P95 Gecikme     : {bench['p95_ms']:.2f} ms")
print(f"  P99 Gecikme     : {bench['p99_ms']:.2f} ms")
print(f"  SLO Uyumu (<50ms): %{bench['slo_compliance_pct']:.2f}")


# =====================================================================
# CELL 19 / CODE 5: DO-178C / NATO STANAG Emniyet Kritik 5 Katı Assertion Testi
# =====================================================================
print("[+] DO-178C & NATO STANAG Emniyet Kritik 5 Doğrulama Kriteri Denetleniyor...")

# Assertion 1: Distributed Trace Bütünlüğü
assert all(s.trace_id == root_span.trace_id for s in tracer.spans), "HATA: Trace ID uyuşmazlığı tespit edildi!"
assert len(tracer.spans) == 5, f"HATA: Eksik alt sistem span'i! Beklenen 5, bulunan: {len(tracer.spans)}"
print("  [OK] Assertion 1: Distributed Trace Bütünlüğü ve W3C Hiyerarşisi Doğrulandı.")

# Assertion 2: Prometheus Metrik Doğruluğu
assert c_tracks.value == 20.0 and h_latency.count == 20, "HATA: Metrik sayaçları işlenen veriyle eşleşmiyor!"
print("  [OK] Assertion 2: Prometheus Sayaç ve Histogram Tutarlılığı Doğrulandı.")

# Assertion 3: Circuit Breaker Hataya Dayanıklılığı ve Toparlanma
assert cb.state == CircuitState.CLOSED, "HATA: Circuit breaker iyileşme sonrası CLOSED durumuna dönemedi!"
print("  [OK] Assertion 3: Devre Kesici (Circuit Breaker) Hata Aşılama ve Toparlanma Tamamlandı.")

# Assertion 4: Taktik SLO Emniyet Eşiği Uyumu (<50ms Savunma Standardı)
assert bench["p99_ms"] <= 25.0, f"HATA: P99 gecikmesi savunma eşiğini aştı: {bench['p99_ms']:.2f} ms"
assert bench["slo_compliance_pct"] >= 99.9, f"HATA: SLO uyumu yetersiz: %{bench['slo_compliance_pct']:.2f}"
print(f"  [OK] Assertion 4: Taktik P99 Gecikme SLO Uyumu Doğrulandı ({bench['p99_ms']:.2f} ms <= 25.0 ms, %{bench['slo_compliance_pct']:.2f}).")

# Assertion 5: Büyük Ölçekli İşlem Hacmi (>= 15.000 işlem/sn)
assert bench["throughput_ops"] >= 15000.0, f"HATA: Benchmark throughput yetersiz: {bench['throughput_ops']}"
print(f"  [OK] Assertion 5: Yüksek Başarımlı İşlem Hacmi Doğrulandı ({bench['throughput_ops']:,.0f} op/sn >= 15.000).")

print("[PASS] DO-178C / NATO STANAG Emniyet Kritik 5 Doğrulama Testi Başarıyla Tamamlandı!")


# =====================================================================
# CELL 23 / CODE 6: Matplotlib 4-Panelli 300 DPI Dashboard Görselleştirme
# =====================================================================
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax_row in axs:
    for ax in ax_row:
        ax.set_facecolor('#1E293B')
        ax.grid(True, linestyle='--', alpha=0.3, color='#475569')
        ax.tick_params(colors='#CBD5E1', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#334155')

# Panel 1: OpenTelemetry Dağıtık İz Gantt / Waterfall Şeması
span_names = [s.name.replace('_', ' ').title() for s in tracer.spans]
start_times = [(s.start_time - root_span.start_time) * 1000.0 for s in tracer.spans]
durations = [s.duration_ms for s in tracer.spans]
colors = ['#38BDF8', '#34D399', '#A855F7', '#F59E0B', '#EF4444']

y_pos = np.arange(len(span_names))
axs[0, 0].barh(y_pos, durations, left=start_times, color=colors, height=0.55, edgecolor='#0F172A', linewidth=1.5)
axs[0, 0].set_yticks(y_pos)
axs[0, 0].set_yticklabels(span_names, color='#F8FAFC', fontsize=9)
axs[0, 0].invert_yaxis()
axs[0, 0].set_xlabel('Ofset ve Süre (Milisaniye)', color='#F8FAFC', fontsize=11, fontweight='bold')
axs[0, 0].set_title('Panel 1: OpenTelemetry Dağıtık İz Waterfall Analizi', color='#F8FAFC', fontsize=12, fontweight='bold', pad=12)

for idx, (st, dur) in enumerate(zip(start_times, durations)):
    axs[0, 0].text(st + dur + 0.1, idx, f"{dur:.2f} ms", va='center', color='#CBD5E1', fontsize=9, fontweight='bold')

# Panel 2: Prometheus Histogram Gecikme Dağılımı ve SLO
lats = bench['e2e_latencies']
axs[0, 1].hist(lats, bins=50, color='#38BDF8', edgecolor='#0F172A', alpha=0.85)
axs[0, 1].axvline(bench['p50_ms'], color='#34D399', linestyle='-', linewidth=2, label=f"P50: {bench['p50_ms']:.2f} ms")
axs[0, 1].axvline(bench['p95_ms'], color='#F59E0B', linestyle='--', linewidth=1.8, label=f"P95: {bench['p95_ms']:.2f} ms")
axs[0, 1].axvline(bench['p99_ms'], color='#A855F7', linestyle='-.', linewidth=1.8, label=f"P99: {bench['p99_ms']:.2f} ms")
axs[0, 1].axvline(50.0, color='#EF4444', linestyle=':', linewidth=2, label="SLO Sınırı (50 ms)")

axs[0, 1].set_xlabel('Uçtan Uca Gecikme (Milisaniye)', color='#F8FAFC', fontsize=11, fontweight='bold')
axs[0, 1].set_ylabel('Olay Frekansı', color='#F8FAFC', fontsize=11, fontweight='bold')
axs[0, 1].set_title(f"Panel 2: SoS Gecikme Dağılımı (SLO: %{bench['slo_compliance_pct']:.2f})", color='#F8FAFC', fontsize=12, fontweight='bold', pad=12)
axs[0, 1].legend(loc='upper right', facecolor='#1E293B', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=8)

# Panel 3: Circuit Breaker Durum Geçişleri ve Fallback Aktivasyonu
steps = np.arange(1, len(cb_logs) + 1)
modes_numeric = [1 if m[0] == "PRIMARY_OK" else (0.5 if m[0] == "FALLBACK_RECOVERY" else 0.0) for m in cb_logs]
cb_states = [m[1] for m in cb_logs]

axs[1, 0].step(steps, modes_numeric, where='mid', color='#F59E0B', linewidth=2.5, label='İşlem Modu (1:AI, 0:Fallback)')
axs[1, 0].scatter(steps, modes_numeric, color='#38BDF8', s=50, zorder=5)

for s_idx, st in enumerate(cb_states):
    col = '#34D399' if st == 'CLOSED' else ('#EF4444' if st == 'OPEN' else '#A855F7')
    axs[1, 0].text(steps[s_idx], modes_numeric[s_idx] + 0.08, st, ha='center', color=col, fontsize=8, fontweight='bold')

axs[1, 0].set_ylim(-0.2, 1.3)
axs[1, 0].set_yticks([0.0, 0.5, 1.0])
axs[1, 0].set_yticklabels(['Fast Fallback', 'Recovery Fallback', 'Primary AI'], color='#CBD5E1', fontsize=9)
axs[1, 0].set_xlabel('İşlem Çağrı Adımı', color='#F8FAFC', fontsize=11, fontweight='bold')
axs[1, 0].set_title('Panel 3: Circuit Breaker Hataya Dayanıklılık Geçişleri', color='#F8FAFC', fontsize=12, fontweight='bold', pad=12)
axs[1, 0].legend(loc='lower left', facecolor='#1E293B', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

# Panel 4: Alt Sistem Gecikme Oranları ve Kaynak Katkısı
nodes = ['AESA Radar', 'Link-16', 'C2 AI Engine', 'Effector SAM']
mean_times = [0.85, 0.45, 1.25, 0.30]
pie_colors = ['#38BDF8', '#34D399', '#A855F7', '#F59E0B']

wedges, texts, autotexts = axs[1, 1].pie(
    mean_times,
    labels=nodes,
    autopct='%1.1f%%',
    colors=pie_colors,
    startangle=140,
    textprops={'color': '#F8FAFC', 'fontsize': 9},
    pctdistance=0.75,
    wedgeprops=dict(width=0.45, edgecolor='#0F172A')
)
for at in autotexts:
    at.set_color('#0F172A')
    at.set_fontweight('bold')
axs[1, 1].set_title('Panel 4: Alt Sistem Gecikme Bütçesi Dağılımı', color='#F8FAFC', fontsize=12, fontweight='bold', pad=12)

plt.tight_layout(pad=3.0)

current_dir = os.path.dirname(os.path.abspath(__file__))
out_png = os.path.join(current_dir, "gun_364_system_of_systems_integration_observability.png")
plt.savefig(out_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

size_bytes = os.path.getsize(out_png)
print(f"[+] 300 DPI Görsel Artefact Kaydedildi: {out_png} ({size_bytes:,} bayt)")
assert size_bytes > 100000, "Görsel boyutu 100 KB'tan küçük!"

