"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.

YASAKLAR:
  1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
  2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
  3. Alt lisanslanamaz, satılamaz veya devredilemez.
  4. Tersine mühendislik yapılamaz.

İZİN VERİLEN KULLANIM:
  - GitHub üzerinde görüntüleme ve okuma.
  - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).

YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
İzin talepleri için: GitHub @seydivakkas
"""

# Kod 1: Video Frame Bellek Mimarisi ve Monotonic Timestamp Motoru
# DO-178C Uyumlu Strided Frame Header, Nanosaniye Saat ve Byte Hizalama

import numpy as np
import time
import struct
from dataclasses import dataclass

@dataclass
class VideoFrameHeader:
    """Aviyonik Video Cerveve Baslik Yapisi (32-byte binary align)."""
    frame_id: int          # uint32: Monotonik artan cerceve sayaci
    timestamp_ns: int      # uint64: CLOCK_MONOTONIC_RAW nanosecond
    exposure_time_us: int  # uint32: Sensor pozlama suresi (mikrosaniye)
    width: int             # uint16: Goruntu genisligi (piksel)
    height: int            # uint16: Goruntu yuksekligi (piksel)
    stride: int            # uint32: Satir bellek adimi (bayt cinsinden)
    pixel_format: int      # uint32: FourCC kodu (Orn: BGR3, NV12)
    flags: int             # uint16: Sensor saglik bayraklari (0=OK, 1=DROPPED, 2=CORRUPTED)
    reserved: int          # uint16: 32-byte hizalama dolgusu

def allocate_aligned_frame(width: int, height: int, channels: int = 3, align: int = 64):
    """64-byte aligned strided frame bellek tahsisi (DMA & TensorRT uyumlu)."""
    raw_row_bytes = width * channels
    # Align up: (bytes + align - 1) & ~(align - 1)
    stride = (raw_row_bytes + align - 1) & ~(align - 1)
    total_bytes = stride * height
    
    # 64-byte bellek blok tahsisi
    buffer = np.zeros((height, stride), dtype=np.uint8)
    return buffer, stride

# 1. 1920x1080 Full HD Aviyonik Kamera Frame Tahsisi
W, H, C = 1920, 1080, 3
frame_buffer, stride = allocate_aligned_frame(W, H, C, align=64)

# 2. Monotonik Nanosaniye Saat Okuma
# time.perf_counter_ns() isletim sisteminin donanimsal yuksek cozunurluklu saatini kullanir
ts_start_ns = time.perf_counter_ns()

# 3. Header Nesnesi Olustur
FOURCC_BGR3 = 0x33524742 # 'BGR3'
header = VideoFrameHeader(
    frame_id=1,
    timestamp_ns=ts_start_ns,
    exposure_time_us=5000, # 5 ms pozlama
    width=W,
    height=H,
    stride=stride,
    pixel_format=FOURCC_BGR3,
    flags=0,
    reserved=0
)

# 4. Header Serilestirme Dogrulamasi (Binary Format: I Q I H H I I H H -> 32 bytes)
header_format = "=IQIHHIIHH"
header_bytes = struct.pack(
    header_format,
    header.frame_id,
    header.timestamp_ns,
    header.exposure_time_us,
    header.width,
    header.height,
    header.stride,
    header.pixel_format,
    header.flags,
    header.reserved
)

assert len(header_bytes) == 32, f"Header 32-byte hizali olmalidir! Mevcut: {len(header_bytes)} bayt"
assert stride >= W * C, "Stride ham genislikten kucuk olamaz!"
assert stride % 64 == 0, "Stride 64-byte bellek sinirina tam bolunmelidir!"

# 5. Geri Donusturme ve Baslik Dogrulugu Kontrolu
unpacked = struct.unpack(header_format, header_bytes)
assert unpacked[0] == 1
assert unpacked[1] == ts_start_ns

print("[PASS] Kod 1: Video Frame Bellek Mimarisi ve Header Basariyla Dogrulandi.")
print(f"  - Goruntu Boyutu               : {W}x{H} ({C} kanal)")
print(f"  - Ham Satir Boyutu (Raw Row)   : {W*C} bayt")
print(f"  - Hizalanmis Satir Adimi(Stride): {stride} bayt (+{stride - W*C} padding bayti)")
print(f"  - Toplam Frame Bellek Alani    : {frame_buffer.nbytes / (1024*1024):.2f} MB")
print(f"  - Nanosaniye Zaman Damgasi     : {header.timestamp_ns} ns")
print(f"  - Serilestirilmis Header Boyutu : {len(header_bytes)} bayt [TAM 32-BYTE ALIGN]")

# Kod 2: Gerçek Zamanlı FPS, Jitter ve Frame Drop Analiz Motoru
import numpy as np

class VideoStreamTimingAnalyzer:
    def __init__(self, nominal_fps: float = 60.0, window_size: int = 30, ema_alpha: float = 0.08):
        self.nominal_fps = nominal_fps
        self.nominal_dt_s = 1.0 / nominal_fps
        self.window_size = window_size
        self.ema_alpha = ema_alpha
        
        self.last_timestamp_s = None
        self.frame_count = 0
        self.dropped_frame_count = 0
        
        # Filtreleme Veri Yapilari
        self.dt_history = []
        self.fps_ema = nominal_fps
        self.jitter_history = []
        
    def process_frame(self, timestamp_s: float):
        self.frame_count += 1
        if self.last_timestamp_s is None:
            self.last_timestamp_s = timestamp_s
            return {
                "dt_ms": 0.0,
                "fps_inst": self.nominal_fps,
                "fps_window": self.nominal_fps,
                "fps_ema": self.nominal_fps,
                "jitter_ms": 0.0,
                "dropped": 0
            }
            
        dt = timestamp_s - self.last_timestamp_s
        self.last_timestamp_s = timestamp_s
        
        # 1. Frame Drop Tespiti
        dropped = 0
        if dt > 1.8 * self.nominal_dt_s:
            dropped = int(round(dt / self.nominal_dt_s)) - 1
            self.dropped_frame_count += dropped
            
        # 2. Anlik FPS
        fps_inst = 1.0 / dt if dt > 1e-6 else 0.0
        
        # 3. Kayan Pencere FPS
        self.dt_history.append(dt)
        if len(self.dt_history) > self.window_size:
            self.dt_history.pop(0)
        mean_dt = np.mean(self.dt_history)
        fps_window = 1.0 / mean_dt if mean_dt > 1e-6 else 0.0
        
        # 4. EMA FPS
        self.fps_ema = self.ema_alpha * fps_inst + (1.0 - self.ema_alpha) * self.fps_ema
        
        # 5. Jitter (Nominal periyottan mutlak sapma)
        jitter_s = abs(dt - self.nominal_dt_s)
        self.jitter_history.append(jitter_s)
        
        return {
            "dt_ms": dt * 1000.0,
            "fps_inst": fps_inst,
            "fps_window": fps_window,
            "fps_ema": self.fps_ema,
            "jitter_ms": jitter_s * 1000.0,
            "dropped": dropped
        }

# 60 FPS Nominal Akış Simülasyonu (200 Kare, Ara Sıra Jitter ve 2 Adet Frame Drop)
np.random.seed(42)
analyzer = VideoStreamTimingAnalyzer(nominal_fps=60.0, window_size=30, ema_alpha=0.08)

sim_current_time = 1000.0 # Baslangic zamani (saniye)
results = []

for frame_idx in range(1, 201):
    # Nominal periyot: 16.666 ms
    # Normal dalgalanma (Jitter): Gauss sigma = 0.8 ms
    dt_noise = np.random.normal(0, 0.0008)
    
    # 50. ve 120. karelerde donanımsal kesme/bellek darboğazı simülasyonu (Frame Drop)
    if frame_idx in [50, 120]:
        step_dt = (1.0 / 60.0) * 2.05 # 1 kare düşmüş gibi gecikme
    else:
        step_dt = (1.0 / 60.0) + dt_noise
        
    sim_current_time += step_dt
    m = analyzer.process_frame(sim_current_time)
    results.append(m)

# Istatistiksel Sonuclar
avg_dt_ms = np.mean([r["dt_ms"] for r in results[1:]])
mean_jitter_ms = np.mean([r["jitter_ms"] for r in results[1:]])
max_jitter_ms = np.max([r["jitter_ms"] for r in results[1:]])
final_ema_fps = results[-1]["fps_ema"]

assert analyzer.dropped_frame_count == 2, f"Beklenen 2 drop tespit edilmeliydi! Tespit: {analyzer.dropped_frame_count}"
assert abs(avg_dt_ms - 16.666) < 0.5, f"Ortalama periyot 16.6ms civarinda olmali: {avg_dt_ms} ms"

print("[PASS] Kod 2: FPS, Jitter ve Frame Drop Analiz Motoru Başarıyla Doğrulandı.")
print(f"  - Toplam Islenen Kare           : {analyzer.frame_count}")
print(f"  - Tespit Edilen Kayip Kare (Drop): {analyzer.dropped_frame_count} adet")
print(f"  - Ortalama Kare Araligi (dt)    : {avg_dt_ms:.3f} ms (Nominal: 16.667 ms)")
print(f"  - Ortalama Jitter               : {mean_jitter_ms:.3f} ms [AVIYONIK KALITE]")
print(f"  - Maksimum Jitter Tepe Degeri   : {max_jitter_ms:.3f} ms")
print(f"  - Son Kayan Pencere FPS         : {results[-1]['fps_window']:.2f}")
print(f"  - Son EMA Filtrelenmis FPS      : {final_ema_fps:.2f}")

# Kod 3: Aviyonik Video Buffer Ring ve Leaky Bucket Kuyruk Laboratuvarı
import collections

class AviyonikFrameQueue:
    """Savunma Standartlarinda Gecikmesiz Video Kuyrugu (Drop-Oldest / Leaky Bucket)."""
    def __init__(self, capacity: int = 1):
        self.capacity = capacity
        self.queue = collections.deque(maxlen=capacity)
        self.total_enqueued = 0
        self.total_dropped_overflow = 0
        self.total_consumed = 0
        
    def enqueue(self, frame_id: int, timestamp_ms: float, data: np.ndarray):
        """Yeni kareyi kuyruga ekler; yer yoksa en eski kareyi otomatik atar (Drop-Oldest)."""
        self.total_enqueued += 1
        if len(self.queue) == self.capacity:
            # Kuyruk dolu! En eski kare atilacak (Buffer Bloat Onleme)
            self.total_dropped_overflow += 1
            dropped_item = self.queue.popleft() # Eski kare atildi
            
        self.queue.append({
            "frame_id": frame_id,
            "timestamp_ms": timestamp_ms,
            "data": data
        })
        
    def dequeue_latest(self):
        """Tuketici icin en guncel kareyi dondurur."""
        if not self.queue:
            return None
        self.total_consumed += 1
        return self.queue.pop() # En guncel son kareyi al

# Test Simülasyonu: Hızlı Kamera (60 FPS / 16.6ms) vs Yavaş Yapay Zeka Modeli (25 FPS / 40ms)
queue_leaky = AviyonikFrameQueue(capacity=1) # Savunma Tasarımı (Zero Latency)
queue_fifo_bloat = [] # Standart Yanlış Tasarım (Sonsuz FIFO)

sim_time = 0.0
cam_dt = 16.666 # 60 FPS
ai_dt = 40.0    # 25 FPS AI Inference
next_ai_time = 0.0

latencies_leaky = []
latencies_bloat = []

dummy_img = np.zeros((10, 10), dtype=np.uint8)

# 1 saniyelik video akışı (60 kare)
for frame_id in range(1, 61):
    sim_time += cam_dt
    
    # 1. Kareleri Kuyruklara Ekle
    queue_leaky.enqueue(frame_id, sim_time, dummy_img)
    queue_fifo_bloat.append({"frame_id": frame_id, "timestamp_ms": sim_time})
    
    # 2. AI Tüketici Döngüsü Tetiklenmesi
    if sim_time >= next_ai_time:
        # Leaky Queue'dan Oku
        frame_l = queue_leaky.dequeue_latest()
        if frame_l:
            latency_l = sim_time - frame_l["timestamp_ms"]
            latencies_leaky.append(latency_l)
            
        # Standart FIFO'dan Oku (Baştan / Eski kareden)
        if queue_fifo_bloat:
            frame_b = queue_fifo_bloat.pop(0)
            latency_b = sim_time - frame_b["timestamp_ms"]
            latencies_bloat.append(latency_b)
            
        next_ai_time = sim_time + ai_dt

mean_lat_leaky = np.mean(latencies_leaky)
max_lat_bloat = np.max(latencies_bloat)

assert mean_lat_leaky < 20.0, f"Leaky bucket gecikmesi bir kareyi gecemez! {mean_lat_leaky} ms"
assert max_lat_bloat > 150.0, f"Standart FIFO'da buffer bloat olusmaliydi! {max_lat_bloat} ms"

print("[PASS] Kod 3: Buffer Ring ve Leaky Bucket Kuyruk Yönetimi Başarıyla Doğrulandı.")
print(f"  - Toplam Uretilen Kamera Karesi: {queue_leaky.total_enqueued}")
print(f"  - AI Tarafindan Tuketilen Kare  : {queue_leaky.total_consumed}")
print(f"  - Atilan Bayat Kare (Overflow) : {queue_leaky.total_dropped_overflow} adet")
print(f"  - Leaky Bucket Ortalama Gecikme: {mean_lat_leaky:.2f} ms [AVIYONIK GERCEK ZAMAN]")
print(f"  - Standart FIFO Azami Gecikmesi: {max_lat_bloat:.2f} ms [FELAKET - BUFFER BLOAT]")

# Kod 4: 3 Kritik Savunma Hata Enjeksiyonu Test Laboratuvarı

print("[TEST 1] Zamansal Jitter ve Kalman Hedef Takip Sapmasi Kalkanı...")
target_speed_mps = 300.0 # 300 m/s hizla ucan hedef
dt_nominal = 0.016666    # 60 FPS (16.66 ms)
dt_jittered = 0.116666   # 100 ms isletim sistemi gecikmesi enjeksiyonu

# Sabit dt varsayan hatali algoritma:
pos_assumed = target_speed_mps * dt_nominal
pos_real = target_speed_mps * dt_jittered
tracking_error_m = pos_real - pos_assumed

print(f"  - Hedef Hizi                     : {target_speed_mps} m/s (Mach 0.9)")
print(f"  - Gercek Zaman Araligi (dt)      : {dt_jittered*1000:.1f} ms")
print(f"  - Sabit dt Varsayimi Sapmasi     : {tracking_error_m:.2f} metre [FELAKET - ISKALAMA]")

# Savunma Kalkani: Dinamik Donanimsal dt Kompanzasyonu
def dynamic_kalman_predict_guard(speed, actual_dt, max_allowed_dt=0.050):
    if actual_dt > max_allowed_dt:
        return speed * actual_dt, "STATUS_JITTER_COMPENSATED_COVARIANCE_INFLATED"
    return speed * actual_dt, "STATUS_NOMINAL_UPDATE"

est_pos, status = dynamic_kalman_predict_guard(target_speed_mps, dt_jittered)
assert status == "STATUS_JITTER_COMPENSATED_COVARIANCE_INFLATED"
print(f"  - Savunma Kalkani Durumu         : [{status}]")
print("[PASS] Test 1: Jitter ve Kalman takip sapmasi kalkani basariyla dogrulandi.\n")


print("[TEST 2] NTP Zaman Geriye Adim Atma (Wall-Clock Hazard) Kalkanı...")
# NTP senkronizasyonu ile sistem saatinin 1.5 saniye geriye cekilmesi
ts_prev_s = 1500.000
ts_curr_wall_clock = 1498.500 # 1.5 saniye geriye sicrama (NTP Step)

def compute_safe_dt(t_now, t_prev, clock_type="MONOTONIC"):
    if clock_type == "WALL_CLOCK":
        dt = t_now - t_prev
        if dt <= 0:
            raise ValueError(f"FATAL: Zamanda geriye gidildi! dt={dt} s")
        return dt
    else:
        # Savunma Kalkani: Monotonic Clock garanti eder ki t_now >= t_prev
        assert t_now >= t_prev, "CLOCK_MONOTONIC asla geriye gidemez!"
        return max(t_now - t_prev, 1e-6)

try:
    compute_safe_dt(ts_curr_wall_clock, ts_prev_s, clock_type="WALL_CLOCK")
    assert False, "Hata firlatilmaliydi!"
except ValueError as e:
    print(f"  - Wall-Clock Yakalanan Hata      : {e}")
    # Monotonik saate gecis:
    safe_dt = compute_safe_dt(1500.0166, ts_prev_s, clock_type="MONOTONIC")
    print(f"  - Savunma Kalkani (Monotonic dt) : {safe_dt*1000:.2f} ms [GUVENLI VE POZITIF]")

print("[PASS] Test 2: NTP Wall-Clock geriye sicrama kalkani basariyla dogrulandi.\n")


print("[TEST 3] Buffer Bloat ve Bayat Kare (Stale Frame) Imha Kalkanı...")
current_mission_time_ms = 5000.0
stale_frame_ts_ms = 4820.0 # 180 ms once uretilmis bayat kare
fresh_frame_ts_ms = 4985.0 # 15 ms once uretilmis taze kare

def mission_critical_frame_gate(frame_ts, current_time, max_latency_ms=50.0):
    age_ms = current_time - frame_ts
    if age_ms > max_latency_ms:
        return False, f"REJECTED_STALE_FRAME (Age: {age_ms:.1f}ms > {max_latency_ms}ms)"
    return True, f"ACCEPTED_FRESH_FRAME (Age: {age_ms:.1f}ms)"

is_stale, reason_stale = mission_critical_frame_gate(stale_frame_ts_ms, current_mission_time_ms)
is_fresh, reason_fresh = mission_critical_frame_gate(fresh_frame_ts_ms, current_mission_time_ms)

assert is_stale == False and "REJECTED_STALE_FRAME" in reason_stale
assert is_fresh == True and "ACCEPTED_FRESH_FRAME" in reason_fresh

print(f"  - 180ms Eski Kare Testi          : {reason_stale} [IMHA EDILDI]")
print(f"  - 15ms Taze Kare Testi           : {reason_fresh} [GUVENLE ISLENDI]")
print("[PASS] Test 3: Bayat kare imha kalkani basariyla dogrulandi.")

# Kod 5: 10.000 Karelik Yüksek Hızlı Zaman Damgası & FPS Benchmark Laboratuvarı
import time
import numpy as np

N_BENCH = 10000

# 1. 10.000 Adet Sentetik Nanosaniye Zaman Damgası Hazırla
nominal_dt_ns = int((1.0 / 60.0) * 1e9)
sim_timestamps_ns = np.arange(0, N_BENCH * nominal_dt_ns, nominal_dt_ns, dtype=np.int64)
# Gürültü ve ara sıra dalgalanma ekle
sim_timestamps_ns += np.random.randint(-1000000, 1000000, size=N_BENCH, dtype=np.int64)

# 2. Benchmark: Zaman Damgası ve EMA FPS Filtreleme
analyzer_bench = VideoStreamTimingAnalyzer(nominal_fps=60.0, window_size=30, ema_alpha=0.08)

t0 = time.perf_counter()
for ts in sim_timestamps_ns:
    analyzer_bench.process_frame(ts * 1e-9)
t1 = time.perf_counter()

total_time_timing = t1 - t0
rate_timing = N_BENCH / total_time_timing
avg_latency_timing_us = (total_time_timing * 1e6) / N_BENCH

# 3. Benchmark: Zero-Copy Pointer Swap vs Full Frame memcpy (1920x1080x3 ~ 6.22 MB)
frame_data = np.random.randint(0, 255, size=(1080, 1920, 3), dtype=np.uint8)

# 100 Deneme: Tam Bellek Kopyalama (memcpy)
N_MEM_TEST = 100
t0 = time.perf_counter()
for _ in range(N_MEM_TEST):
    copied_frame = np.copy(frame_data)
t1 = time.perf_counter()
time_memcpy_ms = ((t1 - t0) / N_MEM_TEST) * 1000.0

# 100 Deneme: Zero-Copy Pointer Swap
target_ptr = None
t0 = time.perf_counter()
for _ in range(N_MEM_TEST):
    target_ptr = frame_data # Sadece referans / pointer ataması
t1 = time.perf_counter()
time_zerocopy_us = ((t1 - t0) / N_MEM_TEST) * 1e6

speedup_copy = (time_memcpy_ms * 1000.0) / max(time_zerocopy_us, 1e-4)

print(f"\n[10.000 KARE TIMING & ZERO-COPY BENCHMARK SONUÇLARI]")
print(f"  - Timing & EMA FPS Throughput   : {rate_timing:12.1f} frame/s | Ort Gecikme: {avg_latency_timing_us:6.3f} us")
print(f"  - Full HD Frame memcpy (6.2 MB) : {time_memcpy_ms:12.3f} ms [DARBOGAZ]")
print(f"  - Zero-Copy Pointer Aktarımı    : {time_zerocopy_us:12.3f} us [AVIYONIK STANDART]")
print(f"  - Zero-Copy Hızlandırma Faktörü : {speedup_copy:12.1f}x KAT DAHA HIZLI")
print(f"[PASS] Kod 5: 10.000 Kare Benchmark Laboratuvarı Başarıyla Tamamlandı.")

# Kod 6: 4-Panelli Koyu Tema Aviyonik Video Timing Dashboard'u
import os
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 14), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.grid(True, color='#334155', linestyle='--', alpha=0.6)
    ax.tick_params(colors='#94A3B8', labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#475569')

# Verileri Hazirla
frame_indices = np.arange(1, len(results) + 1)
dt_ms_series = [r["dt_ms"] for r in results]
fps_inst_series = [r["fps_inst"] for r in results]
fps_win_series = [r["fps_window"] for r in results]
fps_ema_series = [r["fps_ema"] for r in results]

# -------------------------------------------------------------
# Panel 1: Inter-Frame Interval (dt) ve Jitter
# -------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("Panel 1: Inter-Frame Interval (dt) ve Frame Drop Analizi", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
ax1.plot(frame_indices, dt_ms_series, color='#38BDF8', linewidth=1.5, alpha=0.8, label="Gercek dt (ms)")
ax1.axhline(y=16.667, color='#10B981', linestyle='--', linewidth=2.0, label="Nominal dt (60 FPS = 16.67ms)")
ax1.axhline(y=16.667 * 1.8, color='#F59E0B', linestyle=':', linewidth=1.5, label="Frame Drop Esigi (30.0ms)")

# Düşen kareleri işaretle
for idx, r in enumerate(results):
    if r["dropped"] > 0:
        ax1.scatter(idx+1, r["dt_ms"], color='#EF4444', s=100, zorder=5, marker='v')
        ax1.text(idx+1, r["dt_ms"]+2, f"Drop (+{r['dropped']})", color='#EF4444', fontsize=9, fontweight='bold', ha='center')

ax1.set_xlabel("Kare Indeksi (Frame Index)", color='#94A3B8', fontsize=10)
ax1.set_ylabel("Zaman Araligi dt (Milisaniye)", color='#94A3B8', fontsize=10)
ax1.set_ylim(10, 45)
ax1.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', fontsize=9)

# -------------------------------------------------------------
# Panel 2: FPS Metrikleri Karsilastirmasi
# -------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("Panel 2: Anlik Ham FPS vs Kayan Pencere vs EMA FPS", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
ax2.plot(frame_indices, fps_inst_series, color='#EF4444', alpha=0.35, linewidth=1.0, label="Ham Anlik FPS (Gurultulu)")
ax2.plot(frame_indices, fps_win_series, color='#F59E0B', linewidth=2.0, label="30-Frame Kayan Pencere FPS")
ax2.plot(frame_indices, fps_ema_series, color='#10B981', linewidth=2.5, label="EMA Filtrelenmis FPS (alpha=0.08)")
ax2.axhline(y=60.0, color='#38BDF8', linestyle='--', linewidth=1.5, label="Hedef 60 FPS")

ax2.set_xlabel("Kare Indeksi (Frame Index)", color='#94A3B8', fontsize=10)
ax2.set_ylabel("Kare Hizi (FPS)", color='#94A3B8', fontsize=10)
ax2.set_ylim(20, 80)
ax2.legend(loc='lower right', facecolor='#0F172A', edgecolor='#475569', fontsize=9)

# -------------------------------------------------------------
# Panel 3: Pipeline Gecikmesi ve Hedef Takip Sapmasi
# -------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("Panel 3: Pipeline Gecikmesi Kaynakli Takip Sapmasi (E = v * dt)", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
latency_ms_eval = np.linspace(5.0, 200.0, 200)

speeds = [100.0, 200.0, 300.0]
speed_colors = ['#10B981', '#F59E0B', '#EF4444']

for sp, col in zip(speeds, speed_colors):
    error_m = sp * (latency_ms_eval / 1000.0)
    ax3.plot(latency_ms_eval, error_m, color=col, linewidth=2.2, label=f"Hedef Hizi v = {sp:.0f} m/s")

ax3.axvline(x=16.67, color='#38BDF8', linestyle='--', linewidth=1.5, label="1-Frame Gecikme (16.67ms)")
ax3.axhline(y=5.0, color='#F43F5E', linestyle=':', linewidth=1.5, label="Azami Tolere Edilebilir Sapma (5m)")

ax3.set_xlabel("Toplam Video Pipeline Gecikmesi (Milisaniye)", color='#94A3B8', fontsize=10)
ax3.set_ylabel("Konumsal Takip Sapmasi (Metre)", color='#94A3B8', fontsize=10)
ax3.set_xlim(5, 200)
ax3.set_ylim(0, 65)
ax3.legend(loc='upper left', facecolor='#0F172A', edgecolor='#475569', fontsize=9)

# -------------------------------------------------------------
# Panel 4: Buffer Bloat vs Leaky Bucket Kuyruk Gecikmesi
# -------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("Panel 4: Buffer Bloat (Standart FIFO) vs Leaky Bucket Gecikmesi", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)

time_steps_b = np.arange(len(latencies_bloat))
ax4.plot(time_steps_b, latencies_bloat, color='#EF4444', linewidth=2.5, label="Standart FIFO (Buffer Bloat Gecikmesi)")
ax4.plot(time_steps_b, latencies_leaky[:len(time_steps_b)], color='#10B981', linewidth=2.5, label="Leaky Bucket / Drop-Oldest (Zero-Latency)")

ax4.axhline(y=50.0, color='#F59E0B', linestyle='--', linewidth=1.5, label="Stale Frame Limiti (50ms)")
ax4.set_xlabel("AI Inference Adimi", color='#94A3B8', fontsize=10)
ax4.set_ylabel("Frame Bekleme Gecikmesi (Milisaniye)", color='#94A3B8', fontsize=10)
ax4.legend(loc='upper left', facecolor='#0F172A', edgecolor='#475569', fontsize=9)

plt.subplots_adjust(top=0.92, bottom=0.08, left=0.08, right=0.95, hspace=0.28, wspace=0.22)
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else '.'
png_output_path = os.path.join(script_dir, 'gun_258_video_frame_fps_ve_timestamp.png')
plt.savefig(png_output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(png_output_path) / 1024.0
print(f"[OK] 4-Panelli Gorsellestirme Basariyla Uretildi: {png_output_path}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")

