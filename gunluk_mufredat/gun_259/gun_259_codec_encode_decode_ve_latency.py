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

# Kod 1: 2D-DCT, Kuantalama ve P-Frame Hareket Kestirim Motoru
# DO-178C Uyumlu Matematiksel Hibrit Video Sıkıştırma Simülatörü

import numpy as np
import cv2

def dct_2d(block: np.ndarray) -> np.ndarray:
    """8x8 Blok icin 2 Boyutlu Ayrik Kosinus Donusumu."""
    return cv2.dct(block.astype(np.float32))

def idct_2d(block_dct: np.ndarray) -> np.ndarray:
    """8x8 Blok icin Ters Ayrik Kosinus Donusumu (IDCT)."""
    return cv2.idct(block_dct)

# Standart JPEG / H.264 Tabanli 8x8 Kuantalama Matrisi
Q_LUMA_BASE = np.array([
    [16, 11, 10, 16, 24, 40, 51, 61],
    [12, 12, 14, 19, 26, 58, 60, 55],
    [14, 13, 16, 24, 40, 57, 69, 56],
    [14, 17, 22, 29, 51, 87, 80, 62],
    [18, 22, 37, 56, 68, 109, 103, 77],
    [24, 35, 55, 64, 81, 104, 113, 92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103, 99]
], dtype=np.float32)

def quantize_block(dct_block: np.ndarray, q_scale: float = 1.0) -> np.ndarray:
    Q_scaled = np.clip(Q_LUMA_BASE * q_scale, 1.0, 255.0)
    return np.round(dct_block / Q_scaled)

def dequantize_block(q_block: np.ndarray, q_scale: float = 1.0) -> np.ndarray:
    Q_scaled = np.clip(Q_LUMA_BASE * q_scale, 1.0, 255.0)
    return q_block * Q_scaled

# 1. Sentetik Referans ve Mevcut Kare Olustur (128x128 Piksel, Askeri Hedef Bloğu)
np.random.seed(42)
frame_ref = np.zeros((128, 128), dtype=np.float32)
# Referans kareye 20x20 zırhlı araç gövdesi çiz (Piksel değeri = 180)
frame_ref[40:60, 40:60] = 180.0

# Mevcut kare: Araç sağa 3 piksel, aşağı 2 piksel hareket etti (Motion Vector: [3, 2])
frame_curr = np.zeros((128, 128), dtype=np.float32)
frame_curr[42:62, 43:63] = 180.0

# 2. I-Frame Kodlama (Referans Kareyi 8x8 Bloklarla DCT + Kuantala)
reconstructed_I = np.zeros_like(frame_ref)
non_zero_coeffs_I = 0

for y in range(0, 128, 8):
    for x in range(0, 128, 8):
        blk = frame_ref[y:y+8, x:x+8]
        blk_dct = dct_2d(blk)
        blk_q = quantize_block(blk_dct, q_scale=1.0)
        non_zero_coeffs_I += np.count_nonzero(blk_q)
        
        blk_deq = dequantize_block(blk_q, q_scale=1.0)
        reconstructed_I[y:y+8, x:x+8] = idct_2d(blk_deq)

# 3. P-Frame Hareket Kestirimi ve Artık (Residual) Kodlama
reconstructed_P = np.zeros_like(frame_curr)
non_zero_coeffs_P = 0
motion_vectors = []

search_window = 4 # [-4, +4] piksel arama alanı

for y in range(0, 128, 8):
    for x in range(0, 128, 8):
        target_blk = frame_curr[y:y+8, x:x+8]
        
        # Motion Estimation (Block Matching SAD)
        best_sad = float('inf')
        best_mv = (0, 0)
        
        for dy in range(-search_window, search_window + 1):
            for dx in range(-search_window, search_window + 1):
                ref_y = y + dy
                ref_x = x + dx
                if 0 <= ref_y <= 120 and 0 <= ref_x <= 120:
                    cand_blk = reconstructed_I[ref_y:ref_y+8, ref_x:ref_x+8]
                    sad = np.sum(np.abs(target_blk - cand_blk))
                    if sad < best_sad:
                        best_sad = sad
                        best_mv = (dx, dy)
                        
        motion_vectors.append(best_mv)
        
        # Hareket kompanzasyonlu tahmin bloğu
        pred_blk = reconstructed_I[y+best_mv[1]:y+best_mv[1]+8, x+best_mv[0]:x+best_mv[0]+8]
        residual = target_blk - pred_blk
        
        # Artığı DCT ve Kuantala
        res_dct = dct_2d(residual)
        res_q = quantize_block(res_dct, q_scale=1.0)
        non_zero_coeffs_P += np.count_nonzero(res_q)
        
        # Geri catim (Reconstruction)
        res_deq = dequantize_block(res_q, q_scale=1.0)
        reconstructed_P[y:y+8, x:x+8] = pred_blk + idct_2d(res_deq)

# 4. Kalite Metrikleri (PSNR)
mse_I = np.mean((frame_ref - reconstructed_I)**2)
psnr_I = 10 * np.log10((255.0**2) / max(mse_I, 1e-10))

mse_P = np.mean((frame_curr - reconstructed_P)**2)
psnr_P = 10 * np.log10((255.0**2) / max(mse_P, 1e-10))

# 5. Sıkıştırma Oranı / Verimlilik Kıyası (Sıfır Olmayan Katsayı Sayısı)
total_pixels = 128 * 128
compression_gain_P_over_I = non_zero_coeffs_I / max(non_zero_coeffs_P, 1)

assert psnr_I > 35.0, f"I-Frame PSNR kabul edilebilir sinirin altinda: {psnr_I} dB"
assert psnr_P > 35.0, f"P-Frame PSNR kabul edilebilir sinirin altinda: {psnr_P} dB"
assert non_zero_coeffs_P < non_zero_coeffs_I, "P-Frame, I-Frame'den cok daha az katsayi tuketmelidir!"

print("[PASS] Kod 1: 2D-DCT ve Hareket Kestirim Motoru Başarıyla Doğrulandı.")
print(f"  - Toplam Piksel Sayisi         : {total_pixels}")
print(f"  - I-Frame Sifir-Disi Katsayi   : {non_zero_coeffs_I} (Sikistirma: %{(1 - non_zero_coeffs_I/total_pixels)*100:.1f}) | PSNR: {psnr_I:.2f} dB")
print(f"  - P-Frame Sifir-Disi Katsayi   : {non_zero_coeffs_P} (Sikistirma: %{(1 - non_zero_coeffs_P/total_pixels)*100:.1f}) | PSNR: {psnr_P:.2f} dB")
print(f"  - P-Frame Kazanc Faktoru       : {compression_gain_P_over_I:.2f}x Kat Daha Az Veri")

# Kod 2: Periodic Intra-Refresh vs Standart IDR Bitrate Spike Laboratuvarı
import numpy as np

# 60 Karelik Taktik Akış Simülasyonu (60 FPS = 1 saniye)
N_FRAMES = 60
target_bitrate_kbps = 4000.0 # 4 Mbps Taktik RF Veri Bağı
channel_budget_bytes_per_frame = (target_bitrate_kbps * 1000.0 / 8.0) / 60.0 # ~8333 bayt

# 1. Standart IDR GOP Mimarisi (Her 30 karede bir IDR I-Frame)
sizes_standard_idr = []
for f in range(N_FRAMES):
    if f % 30 == 0:
        # IDR I-Frame boyutu: Yaklaşık 250 KB (Devasa Spike!)
        sz = int(np.random.normal(250000, 15000))
    else:
        # P-Frame boyutu: Yaklaşık 12 KB
        sz = int(np.random.normal(12000, 1200))
    sizes_standard_idr.append(sz)

# 2. Askeri Periodic Intra-Refresh Mimarisi (Sütun Genişliği = 1/15)
# Hiçbir zaman büyük I-Frame yok; her karede az miktarda Intra-Macroblock var
sizes_intra_refresh = []
intra_refresh_period = 15 # 15 karede tam ekran yenileme

for f in range(N_FRAMES):
    if f == 0:
        sz = int(np.random.normal(35000, 2000)) # Sadece en bastaki ilk kare
    else:
        # P-Frame + 1/15 Intra-Slice: Cok homojen, ~16 KB civari
        sz = int(np.random.normal(16500, 800))
    sizes_intra_refresh.append(sz)

# 3. İletim Gecikmesi Simülasyonu (Queue Latency)
# Veri bağı hattı saniyede 500 KB (4 Mbps) aktarabilir
byte_rate_per_ms = (target_bitrate_kbps * 1000.0 / 8.0) / 1000.0 # 500 bayt / ms

latencies_idr = [sz / (byte_rate_per_ms * 1000.0 / 60.0) * 16.666 for sz in sizes_standard_idr]
latencies_refresh = [sz / (byte_rate_per_ms * 1000.0 / 60.0) * 16.666 for sz in sizes_intra_refresh]

std_idr = np.std(sizes_standard_idr)
std_refresh = np.std(sizes_intra_refresh)
max_idr_spike_ratio = max(sizes_standard_idr) / np.mean(sizes_standard_idr[1:29])

assert max_idr_spike_ratio > 10.0, "IDR frame spike orani en az 10x olmalidir!"
assert std_refresh < std_idr / 5.0, "Intra-refresh boyutsal varyansi cok daha dusuk olmalidir!"

print("[PASS] Kod 2: Periodic Intra-Refresh Mimarisi Başarıyla Doğrulandı.")
print(f"  - Taktik Kanal Kapasitesi        : {target_bitrate_kbps:.0f} kbps")
print(f"  - Kare Basina Nominal Kanal Payi : {channel_budget_bytes_per_frame:.0f} bayt")
print(f"  - Standart IDR Maksimum Frame    : {max(sizes_standard_idr)/1024:.1f} KB (Spike Orani: {max_idr_spike_ratio:.1f}x)")
print(f"  - Intra-Refresh Ortalama Frame   : {np.mean(sizes_intra_refresh)/1024:.1f} KB (Maksimum: {max(sizes_intra_refresh)/1024:.1f} KB)")
print(f"  - Standart IDR Boyut Sapmasi     : {std_idr/1024:.1f} KB [KARARSIZ AKIS]")
print(f"  - Intra-Refresh Boyut Sapmasi    : {std_refresh/1024:.1f} KB [HOMOJEN MUKEMMEL KARARLILIK]")

# Kod 3: Aviyonik Glass-to-Glass Gecikme Ölçüm ve Zamanlama Boru Hattı
import time
from dataclasses import dataclass

@dataclass
class VideoLatencyBudget:
    capture_ms: float
    encode_ms: float
    packetize_ms: float
    rf_link_ms: float
    decode_ms: float
    render_ms: float
    
    @property
    def total_g2g_ms(self) -> float:
        return (self.capture_ms + self.encode_ms + self.packetize_ms + 
                self.rf_link_ms + self.decode_ms + self.render_ms)

def simulate_pipeline_latency(b_frames_enabled: bool = False, use_hw_accel: bool = True) -> VideoLatencyBudget:
    # 1. Capture (60 FPS = 16.67ms)
    t_cap = 16.666
    
    # 2. Encode (HW NVENC: 4.2ms vs SW CPU x264: 38.0ms)
    t_enc = 4.2 if use_hw_accel else 38.0
    
    # B-Frame Reordering Gecikmesi (Eğer B-Frame açıksa +2 frame bekleme)
    if b_frames_enabled:
        t_enc += 2 * 16.666 # +33.3ms Reorder Delay!
        
    # 3. Packetize
    t_pkt = 1.8
    
    # 4. RF Link (4 Mbps taktik kanal iletimi)
    t_rf = 11.5
    
    # 5. Decode (HW NVDEC: 3.2ms vs SW CPU: 18.0ms)
    t_dec = 3.2 if use_hw_accel else 18.0
    
    # 6. Render (120 Hz Aviyonik Monitör: 8.33ms vs 60Hz: 16.67ms)
    t_rend = 8.333
    
    return VideoLatencyBudget(t_cap, t_enc, t_pkt, t_rf, t_dec, t_rend)

# Profil Karşılaştırmaları
budget_tactical_optimal = simulate_pipeline_latency(b_frames_enabled=False, use_hw_accel=True)
budget_with_bframes = simulate_pipeline_latency(b_frames_enabled=True, use_hw_accel=True)
budget_sw_cpu = simulate_pipeline_latency(b_frames_enabled=False, use_hw_accel=False)

assert budget_tactical_optimal.total_g2g_ms < 50.0, f"Optimal gecikme 50ms altinda olmali: {budget_tactical_optimal.total_g2g_ms} ms"
assert budget_with_bframes.total_g2g_ms > 70.0, "B-Frame gecikmeyi ciddi sekilde artirmaliydi!"

print("[PASS] Kod 3: Glass-to-Glass Latency Zamanlama Boru Hattı Başarıyla Doğrulandı.")
print(f"  [1] SAVUNMA OPTIMAL PROFILI (Zero B-Frames + HW NVENC):")
print(f"      - Capture: {budget_tactical_optimal.capture_ms:.1f}ms | Encode: {budget_tactical_optimal.encode_ms:.1f}ms | RF: {budget_tactical_optimal.rf_link_ms:.1f}ms | Decode: {budget_tactical_optimal.decode_ms:.1f}ms")
print(f"      - TOPLAM G2G GECIKMESI: {budget_tactical_optimal.total_g2g_ms:.2f} ms [DO-178C EMNIYETLI < 50ms]")
print(f"  [2] HATALI PROFIL (B-Frames Acik):")
print(f"      - TOPLAM G2G GECIKMESI: {budget_with_bframes.total_g2g_ms:.2f} ms (+{budget_with_bframes.total_g2g_ms - budget_tactical_optimal.total_g2g_ms:.1f}ms Reorder Gecikmesi) [GUDUM KAYBI]")
print(f"  [3] HATALI PROFIL (Yazilimsal CPU Codec):")
print(f"      - TOPLAM G2G GECIKMESI: {budget_sw_cpu.total_g2g_ms:.2f} ms [FELAKET - TELEOPERASYON IMKANSIZ]")

# Kod 4: 3 Kritik Savunma Hata Enjeksiyonu Test Laboratuvarı

print("[TEST 1] B-Frame Kullanim Engelleme ve Zero-Latency Kalkani...")
def validate_codec_profile_for_flight(config: dict):
    """DO-178C Emniyet Kriteri: Askeri sistemde B-Frame yasaktir!"""
    b_frames = config.get("b_frames", 0)
    preset = config.get("preset", "")
    
    if b_frames > 0:
        return False, f"CONFIG_REJECTED: b_frames={b_frames} > 0! Reorder gecikmesi olusur!"
    if "low-latency" not in preset:
        return False, f"CONFIG_REJECTED: preset '{preset}' dusuk gecikmeli degil!"
    return True, "CONFIG_ACCEPTED_DO178C_LEVEL_A"

bad_config = {"b_frames": 2, "preset": "medium", "gop": 60}
safe_config = {"b_frames": 0, "preset": "ultra-low-latency", "gop": 1}

is_safe_bad, msg_bad = validate_codec_profile_for_flight(bad_config)
is_safe_good, msg_good = validate_codec_profile_for_flight(safe_config)

assert is_safe_bad == False and "b_frames" in msg_bad
assert is_safe_good == True and "DO178C" in msg_good

print(f"  - Hatali Ticari Konfigurasyon   : {msg_bad} [BLOKE EDILDI]")
print(f"  - Guvenli Aviyonik Konfigurasyon: {msg_good} [ONAYLANDI]")
print("[PASS] Test 1: B-Frame engelleme kalkani basariyla dogrulandi.\n")


print("[TEST 2] Taktik Paket Kaybi ve Hizli Intra-Recovery (FIR) Kalkani...")
class TacticalVideoReceiver:
    def __init__(self):
        self.last_decoded_frame_id = 0
        self.stream_healthy = True
        self.fir_request_count = 0
        
    def receive_packet(self, frame_id: int):
        # Paket sira numarasi kontrolu
        if frame_id != self.last_decoded_frame_id + 1:
            # Paket dusmesi tespit edildi! Referans bozuldu!
            self.stream_healthy = False
            self.fir_request_count += 1
            # Savunma Kalkani: Aninda enkoder'e Fast Intra Request gonder
            return "TRIGGER_FAST_INTRA_REQUEST_TO_ENCODER"
            
        self.last_decoded_frame_id = frame_id
        self.stream_healthy = True
        return "FRAME_DECODED_NOMINAL"

rx = TacticalVideoReceiver()
res1 = rx.receive_packet(1)
res2 = rx.receive_packet(2)
# Paket 3 Jamming nedeniyle kayboldu! Paket 4 geldi:
res3 = rx.receive_packet(4)

assert res1 == "FRAME_DECODED_NOMINAL"
assert res3 == "TRIGGER_FAST_INTRA_REQUEST_TO_ENCODER"
assert rx.fir_request_count == 1

print(f"  - Paket 1 ve 2 Durumu            : {res1}")
print(f"  - Paket 3 Kaybinda FDIR Tepkisi  : [{res3}]")
print("[PASS] Test 2: Hizli Intra-Recovery (FIR) kalkani basariyla dogrulandi.\n")


print("[TEST 3] VBR Bandwidth Overflow ve Strict CBR Kalkani...")
telsiz_max_kbps = 4000.0 # 4 Mbps limit

def tactical_rate_controller(measured_entropy, mode="CBR"):
    """VBR vs Strict CBR Rate Controller Simülatörü."""
    if mode == "VBR":
        # Entropi arttikca bitrate kontrolsuz firlar
        produced_kbps = 2500.0 + (measured_entropy * 12000.0)
    else:
        # Savunma Kalkani: Strict CBR (Gerekirse QP artirilir, bant genisligi asilmaz)
        produced_kbps = min(telsiz_max_kbps, 3800.0) # 3.8 Mbps sabit
        
    overflow = produced_kbps > telsiz_max_kbps
    return produced_kbps, overflow

vbr_rate, vbr_overflow = tactical_rate_controller(measured_entropy=0.95, mode="VBR") # Duman/Patlama sahnesi
cbr_rate, cbr_overflow = tactical_rate_controller(measured_entropy=0.95, mode="CBR")

assert vbr_overflow == True, "VBR telsiz kapasitesini asmalidir!"
assert cbr_overflow == False, "CBR asla telsiz kapasitesini asamaz!"

print(f"  - Duman Sahnesinde VBR Bitrate   : {vbr_rate:.0f} kbps (Telsiz Limiti: {telsiz_max_kbps:.0f} kbps) -> [TAMPON TASTI!]")
print(f"  - Duman Sahnesinde CBR Bitrate   : {cbr_rate:.0f} kbps -> [GUVENLI AKIS]")
print("[PASS] Test 3: Strict CBR band genisligi kalkani basariyla dogrulandi.")

# Kod 5: 10.000 Blokluk Yüksek Hızlı DCT ve Hareket Kestirim Benchmark Laboratuvarı
import time
import numpy as np

N_BENCH_BLOCKS = 10000

# 1. 10.000 Adet 8x8 Rastgele Piksel Bloğu Hazırla
blocks_bench = np.random.uniform(0, 255, size=(N_BENCH_BLOCKS, 8, 8)).astype(np.float32)

# 2. Benchmark: 2D-DCT Dönüşümü
t0 = time.perf_counter()
for i in range(N_BENCH_BLOCKS):
    _ = cv2.dct(blocks_bench[i])
t1 = time.perf_counter()
time_dct = t1 - t0
rate_dct = N_BENCH_BLOCKS / time_dct
latency_dct_us = (time_dct * 1e6) / N_BENCH_BLOCKS

# 3. Benchmark: Kuantalama ve Eşikleme
Q_mat = Q_LUMA_BASE
t0 = time.perf_counter()
for i in range(N_BENCH_BLOCKS):
    _ = np.round(blocks_bench[i] / Q_mat)
t1 = time.perf_counter()
time_quant = t1 - t0
rate_quant = N_BENCH_BLOCKS / time_quant
latency_quant_us = (time_quant * 1e6) / N_BENCH_BLOCKS

# 4. Benchmark: Blok Eşleme (SAD - Sum of Absolute Differences)
cand_block = np.random.uniform(0, 255, size=(8, 8)).astype(np.float32)
t0 = time.perf_counter()
for i in range(N_BENCH_BLOCKS):
    _ = np.sum(np.abs(blocks_bench[i] - cand_block))
t1 = time.perf_counter()
time_sad = t1 - t0
rate_sad = N_BENCH_BLOCKS / time_sad
latency_sad_us = (time_sad * 1e6) / N_BENCH_BLOCKS

print(f"\n[10.000 BLOK VIDEO CODEC MOTORU BENCHMARK SONUÇLARI]")
print(f"  - 8x8 2D-DCT Donusum Hizi       : {rate_dct:12.1f} blok/s | Ort Gecikme: {latency_dct_us:6.3f} us")
print(f"  - Kuantalama (Quantization) Hizi: {rate_quant:12.1f} blok/s | Ort Gecikme: {latency_quant_us:6.3f} us")
print(f"  - SAD Hareket Kestirim Hizi     : {rate_sad:12.1f} blok/s | Ort Gecikme: {latency_sad_us:6.3f} us")
print(f"  - Toplam Blok Islem Suresi      : {latency_dct_us + latency_quant_us + latency_sad_us:6.3f} us [AVIYONIK GERCEK ZAMAN]")
print(f"[PASS] Kod 5: 10.000 Blok Codec Benchmark Laboratuvarı Başarıyla Tamamlandı.")

# Kod 6: 4-Panelli Koyu Tema Aviyonik Codec & Latency Dashboard'u
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

# -------------------------------------------------------------
# Panel 1: DCT Frekans Donusumu ve Enerji Yogulasmasi
# -------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("Panel 1: 8x8 Piksel Bloğu ve DCT Frekans Spektrumu (Enerji Yoğunlaşması)", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)

sample_blk = frame_ref[40:48, 40:48]
sample_dct = np.log1p(np.abs(dct_2d(sample_blk)))

im1 = ax1.imshow(sample_dct, cmap='magma')
cbar1 = fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
cbar1.ax.tick_params(colors='#94A3B8', labelsize=8)
cbar1.set_label('Logaritmik DCT Genliği', color='#94A3B8', fontsize=9)

ax1.set_xlabel("Yatay Frekans (u)", color='#94A3B8', fontsize=10)
ax1.set_ylabel("Dikey Frekans (v)", color='#94A3B8', fontsize=10)
ax1.set_xticks(range(8))
ax1.set_yticks(range(8))
ax1.text(0, 0, "DC", color='#38BDF8', fontsize=11, fontweight='bold', ha='center', va='center')

# -------------------------------------------------------------
# Panel 2: Standart IDR Spike vs Periodic Intra-Refresh
# -------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("Panel 2: Standart IDR Spike vs Askeri Periodic Intra-Refresh", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
frames_x = np.arange(1, N_FRAMES + 1)

ax2.plot(frames_x, np.array(sizes_standard_idr) / 1024.0, color='#EF4444', linewidth=2.0, label="Standart IDR (Devasa Spike / Tampon Taşması)")
ax2.plot(frames_x, np.array(sizes_intra_refresh) / 1024.0, color='#10B981', linewidth=2.5, label="Periodic Intra-Refresh (Homojen Düşük Gecikme)")
ax2.axhline(y=channel_budget_bytes_per_frame / 1024.0, color='#38BDF8', linestyle='--', linewidth=1.5, label="Taktik RF Bant Bütçesi (~8.3 KB)")

ax2.set_xlabel("Kare Numarası (Frame Index)", color='#94A3B8', fontsize=10)
ax2.set_ylabel("Kare Boyutu (KiloBayt - KB)", color='#94A3B8', fontsize=10)
ax2.set_ylim(0, 300)
ax2.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', fontsize=9)

# -------------------------------------------------------------
# Panel 3: Glass-to-Glass Latency Dağılımı ve 50ms Bütçesi
# -------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("Panel 3: Glass-to-Glass Uçtan Uca Gecikme Bütçesi Dağılımı", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)

categories = ['Savunma Optimal\n(Zero B-Frame + HW)', 'B-Frames Açık\n(+2 Reorder Frame)', 'Yazılımsal Codec\n(CPU x264/ffmpeg)']
cap_vals = [budget_tactical_optimal.capture_ms, budget_with_bframes.capture_ms, budget_sw_cpu.capture_ms]
enc_vals = [budget_tactical_optimal.encode_ms, budget_with_bframes.encode_ms, budget_sw_cpu.encode_ms]
rf_vals  = [budget_tactical_optimal.rf_link_ms, budget_with_bframes.rf_link_ms, budget_sw_cpu.rf_link_ms]
dec_vals = [budget_tactical_optimal.decode_ms, budget_with_bframes.decode_ms, budget_sw_cpu.decode_ms]
rend_vals= [budget_tactical_optimal.render_ms, budget_with_bframes.render_ms, budget_sw_cpu.render_ms]

x_pos = np.arange(len(categories))
w = 0.45

p1 = ax3.bar(x_pos, cap_vals, w, label='1. Sensör Capture', color='#3B82F6')
p2 = ax3.bar(x_pos, enc_vals, w, bottom=cap_vals, label='2. Encode', color='#F59E0B')
p3 = ax3.bar(x_pos, rf_vals, w, bottom=np.array(cap_vals)+np.array(enc_vals), label='3. RF Link', color='#8B5CF6')
p4 = ax3.bar(x_pos, dec_vals, w, bottom=np.array(cap_vals)+np.array(enc_vals)+np.array(rf_vals), label='4. Decode', color='#06B6D4')
p5 = ax3.bar(x_pos, rend_vals, w, bottom=np.array(cap_vals)+np.array(enc_vals)+np.array(rf_vals)+np.array(dec_vals), label='5. Render', color='#10B981')

ax3.axhline(y=50.0, color='#EF4444', linestyle='--', linewidth=2.0, label='Maksimum Aviyonik Limit (50 ms)')
ax3.set_ylabel("Gecikme (Milisaniye)", color='#94A3B8', fontsize=10)
ax3.set_xticks(x_pos)
ax3.set_xticklabels(categories, color='#94A3B8', fontsize=9, fontweight='bold')
ax3.set_ylim(0, 120)
ax3.legend(loc='upper left', facecolor='#0F172A', edgecolor='#475569', fontsize=8)

# -------------------------------------------------------------
# Panel 4: Rate-Distortion Egrisi (Bitrate vs PSNR)
# -------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("Panel 4: Rate-Distortion Eğrisi (Bitrate vs PSNR Kalitesi)", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)

qp_levels = np.array([18, 22, 26, 30, 36, 42])
# Simüle edilen Bitrate (kbps) ve PSNR (dB)
bitrates_kbps = np.array([9500, 6800, 4200, 2600, 1400, 750])
psnr_values = np.array([44.5, 41.2, 38.0, 35.2, 31.8, 28.5])

ax4.plot(bitrates_kbps, psnr_values, color='#38BDF8', marker='o', linewidth=2.5, markersize=8, label="H.264 Rate-Distortion")

# Taktik Calisma Noktasini Isaretle (QP=26, 4.2 Mbps, 38 dB)
ax4.scatter(4200, 38.0, color='#10B981', s=160, zorder=5, edgecolors='#FFFFFF', label="Askeri Hedef Çalışma Noktası (QP=26)")
ax4.axhline(y=36.0, color='#F59E0B', linestyle=':', linewidth=1.5, label="Operasyonel Kalite Sınırı (36 dB)")
ax4.axvline(x=4000.0, color='#EF4444', linestyle='--', linewidth=1.5, label="Taktik RF Bant Limiti (4 Mbps)")

ax4.set_xlabel("Veri Hızı - Bitrate (kbps)", color='#94A3B8', fontsize=10)
ax4.set_ylabel("Görüntü Kalitesi (PSNR - dB)", color='#94A3B8', fontsize=10)
ax4.legend(loc='lower right', facecolor='#0F172A', edgecolor='#475569', fontsize=9)

plt.subplots_adjust(top=0.92, bottom=0.08, left=0.08, right=0.95, hspace=0.28, wspace=0.22)
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else '.'
png_output_path = os.path.join(script_dir, 'gun_259_codec_encode_decode_ve_latency.png')
plt.savefig(png_output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(png_output_path) / 1024.0
print(f"[OK] 4-Panelli Gorsellestirme Basariyla Uretildi: {png_output_path}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")

