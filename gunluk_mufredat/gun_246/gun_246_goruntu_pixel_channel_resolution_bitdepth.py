# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 246: Görüntü: pixel, channel, resolution, bit depth Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: Ham Piksel Matrisi, Stride Ofseti ve Bit Derinliği Dönüşümleri
# Row-major bellek haritalama, donanımsal pitch hizalama ve sayısal tipler.
# ============================================================================
import numpy as np
from typing import Tuple, Dict, Any

class RawPixelBuffer:
    def __init__(self, width: int, height: int, channels: int, dtype: np.dtype, alignment_bytes: int = 32):
        self.width = width
        self.height = height
        self.channels = channels
        self.dtype = dtype
        self.bytes_per_sample = np.dtype(dtype).itemsize
        self.bytes_per_pixel = self.channels * self.bytes_per_sample
        
        # Minimum satır genişliği
        unaligned_stride = self.width * self.bytes_per_pixel
        # Donanımsal hizalama (Örn: AVX-512 veya DMA için 32 ya da 64 bayt katı)
        remainder = unaligned_stride % alignment_bytes
        self.padding_bytes = (alignment_bytes - remainder) if remainder != 0 else 0
        self.stride_bytes = unaligned_stride + self.padding_bytes
        
        # Toplam ham bayt alanı
        self.total_bytes = self.height * self.stride_bytes
        self.raw_memory = bytearray(self.total_bytes)

    def calculate_byte_offset(self, x: int, y: int, c: int) -> int:
        if not (0 <= x < self.width and 0 <= y < self.height and 0 <= c < self.channels):
            raise IndexError(f"Geçersiz piksel koordinatı: ({x}, {y}, kanal={c})")
        return y * self.stride_bytes + x * self.bytes_per_pixel + c * self.bytes_per_sample

    def set_pixel_channel(self, x: int, y: int, c: int, value: Any):
        offset = self.calculate_byte_offset(x, y, c)
        val_bytes = np.array(value, dtype=self.dtype).tobytes()
        self.raw_memory[offset:offset+self.bytes_per_sample] = val_bytes

    def get_pixel_channel(self, x: int, y: int, c: int) -> Any:
        offset = self.calculate_byte_offset(x, y, c)
        raw_val = self.raw_memory[offset:offset+self.bytes_per_sample]
        return np.frombuffer(raw_val, dtype=self.dtype)[0]

# 1. 4x4 Piksel, 3 Kanallı uint8 Tamponu (Hizalama = 16 bayt)
# Unaligned = 4 * 3 * 1 = 12 bayt. 16 bayta tamamlamak için 4 bayt padding gerekir! Stride = 16 bayt.
buf_rgb8 = RawPixelBuffer(width=4, height=4, channels=3, dtype=np.uint8, alignment_bytes=16)
assert buf_rgb8.stride_bytes == 16, f"Stride 16 olmalıydı: {buf_rgb8.stride_bytes}"
assert buf_rgb8.padding_bytes == 4, f"Padding 4 olmalıydı: {buf_rgb8.padding_bytes}"
assert buf_rgb8.total_bytes == 64, f"Toplam bayt 64 olmalıydı: {buf_rgb8.total_bytes}"

# Piksel (2, 1) için Kırmızı (c=0) ve Yeşil (c=1) değerleri yaz
buf_rgb8.set_pixel_channel(x=2, y=1, c=0, value=255)
buf_rgb8.set_pixel_channel(x=2, y=1, c=1, value=128)
assert buf_rgb8.get_pixel_channel(x=2, y=1, c=0) == 255
assert buf_rgb8.get_pixel_channel(x=2, y=1, c=1) == 128

# 2. 14-Bit Termal Sensör Tamponu (uint16 saklanır, 0..16383 aralığı)
buf_thermal16 = RawPixelBuffer(width=4, height=4, channels=1, dtype=np.uint16, alignment_bytes=16)
# 4 * 1 * 2 = 8 bayt. 16 bayt hizalamada padding = 8 bayt, Stride = 16 bayt.
assert buf_thermal16.stride_bytes == 16
buf_thermal16.set_pixel_channel(x=3, y=2, c=0, value=14250) # Örn: Sıcak hedef pikseli
assert buf_thermal16.get_pixel_channel(x=3, y=2, c=0) == 14250

# 3. float32 Normalize Tensör Tamponu (AI Girişi: 0.0 - 1.0)
buf_ai_f32 = RawPixelBuffer(width=4, height=4, channels=1, dtype=np.float32, alignment_bytes=32)
buf_ai_f32.set_pixel_channel(x=0, y=0, c=0, value=0.875)
assert np.isclose(buf_ai_f32.get_pixel_channel(x=0, y=0, c=0), 0.875)

print("[PASS] Kod 1: Ham Piksel Matrisi ve Row-major Stride Adresleme Doğrulandı.")
print(f"  - RGB8 Tamponu    : 4x4, Stride={buf_rgb8.stride_bytes} bayt (Satır Başı Dolgu: {buf_rgb8.padding_bytes} bayt)")
print(f"  - Termal16 Tamponu: 4x4 uint16, Piksel (3,2) = {buf_thermal16.get_pixel_channel(3, 2, 0)} LSB")
print(f"  - AI float32      : 4x4 float32, Piksel (0,0) = {buf_ai_f32.get_pixel_channel(0, 0, 0):.4f}")

# ============================================================================
# KOD HÜCRESİ 2: EO/IR Sensör Akış Simülatörü ve Bant Genişliği Analizörü
# Farklı çözünürlük, kanal sayısı, bit derinliği ve FPS için bellek profili.
# ============================================================================
from dataclasses import dataclass
from typing import List

@dataclass
class SensorConfig:
    name: str
    width: int
    height: int
    channels: int
    bit_depth: int       # Bit cinsinden (8, 14, 16)
    fps: int
    storage_bytes_per_sample: int # Bellekte tutulan bayt (14-bit -> 2 bayt uint16)

    @property
    def frame_size_bytes(self) -> int:
        return self.width * self.height * self.channels * self.storage_bytes_per_sample

    @property
    def frame_size_mb(self) -> float:
        return self.frame_size_bytes / (1024.0 * 1024.0)

    @property
    def bandwidth_gbps(self) -> float:
        # Ham veri akışı: width * height * channels * bit_depth * fps
        return (self.width * self.height * self.channels * self.bit_depth * self.fps) / 1e9

    @property
    def memory_throughput_mb_s(self) -> float:
        # RAM'e saniyede yazılan ham bayt miktarı
        return (self.frame_size_bytes * self.fps) / (1024.0 * 1024.0)

sensor_arsenal = [
    SensorConfig("VGA Termal FLIR (LWIR)", 640, 512, channels=1, bit_depth=14, fps=60, storage_bytes_per_sample=2),
    SensorConfig("720p HD Gimbal EO", 1280, 720, channels=3, bit_depth=8, fps=60, storage_bytes_per_sample=1),
    SensorConfig("1080p FHD Keşif Podu", 1920, 1080, channels=3, bit_depth=8, fps=60, storage_bytes_per_sample=1),
    SensorConfig("4K UHD Geniş Alan EO", 3840, 2160, channels=3, bit_depth=8, fps=30, storage_bytes_per_sample=1),
]

print(f"{'Sensör Adı':<25} | {'Çözünürlük':<12} | {'Bit':<5} | {'Kare (MB)':<10} | {'Bant Genişliği':<15} | {'RAM Yazma':<12}")
print("-" * 88)

results = []
for s in sensor_arsenal:
    print(f"{s.name:<25} | {s.width}x{s.height:<7} | {s.bit_depth:<5} | {s.frame_size_mb:<10.2f} | {s.bandwidth_gbps:<8.2f} Gbps | {s.memory_throughput_mb_s:<8.1f} MB/s")
    results.append(s)

# Doğrulamalar:
flir = results[0]
assert flir.frame_size_bytes == 640 * 512 * 1 * 2 # 655,360 bayt (0.625 MB)
assert abs(flir.frame_size_mb - 0.625) < 1e-3

fhd = results[2]
assert fhd.frame_size_bytes == 1920 * 1080 * 3 * 1 # 6,220,800 bayt (~ 5.93 MB)
assert fhd.memory_throughput_mb_s > 350.0 # ~ 355.9 MB/s

uhd = results[3]
assert uhd.bandwidth_gbps > 5.9 # ~ 5.97 Gbps ham sensör akışı

print("\n[PASS] Kod 2: EO/IR Sensör Akış Simülatörü ve Bant Genişliği Analizörü Doğrulandı.")
print(f"  - 4K Kamera Saniyede     : {uhd.memory_throughput_mb_s:.1f} MB RAM trafiği oluşturur.")
print(f"  - 1080p60 EO Kamera Hattı: {fhd.bandwidth_gbps:.2f} Gbps ham veri taşır.")
print(f"  - Termal FLIR (60 FPS)   : {flir.memory_throughput_mb_s:.1f} MB/s ile son derece kompakt ve etkindir.")

# ============================================================================
# KOD HÜCRESİ 3: Termal 14-bit Radiometric AGC ve Dinamik Kontrast Motoru
# Yüksek dinamik aralıklı FLIR verisini yapay zeka ve pilot ekranına uyarlama.
# ============================================================================
import numpy as np

def generate_synthetic_thermal_scene(size: int = 128) -> np.ndarray:
    # 14-bit FLIR aralığı: 0 .. 16383 LSB
    # Arka plan arazi: 15°C - 22°C (3800 - 4500 LSB)
    np.random.seed(42)
    scene = np.random.normal(loc=4100, scale=80, size=(size, size)).astype(np.uint16)
    
    # Soğuk nehir yatağı (10°C -> 3000 LSB)
    scene[30:50, :] = np.random.normal(loc=3100, scale=40, size=(20, size)).astype(np.uint16)
    
    # Sıcak Zırhlı Kara Aracı (Motor ve Gövde: 60°C - 75°C -> 11000 - 13500 LSB)
    # 16x16 piksel hedef
    target_patch = np.random.normal(loc=12500, scale=200, size=(16, 16)).astype(np.uint16)
    scene[70:86, 70:86] = target_patch
    
    return np.clip(scene, 0, 16383)

class ThermalAGC:
    @staticmethod
    def naive_bit_shift(thermal_raw: np.ndarray) -> np.ndarray:
        # Hatalı/Acemi yaklaşım: 14-bit veriyi doğrudan 6 bit sağa kaydırarak 8-bite indir
        # 16383 >> 6 = 255
        return (thermal_raw >> 6).astype(np.uint8)

    @staticmethod
    def linear_min_max_agc(thermal_raw: np.ndarray) -> Tuple[np.ndarray, int, int]:
        # Savunma AGC yaklaşımı: Sahnenin min ve max değerlerine göre normalize et
        p_min = int(np.min(thermal_raw))
        p_max = int(np.max(thermal_raw))
        
        dynamic_span = max(p_max - p_min, 1)
        # float dönüşümü ve ölçekleme
        scaled = ((thermal_raw.astype(np.float32) - p_min) / dynamic_span) * 255.0
        scaled_u8 = np.clip(scaled, 0.0, 255.0).astype(np.uint8)
        return scaled_u8, p_min, p_max

thermal_14bit = generate_synthetic_thermal_scene(128)
naive_img = ThermalAGC.naive_bit_shift(thermal_14bit)
agc_img, min_lsb, max_lsb = ThermalAGC.linear_min_max_agc(thermal_14bit)

# Doğrulamalar:
assert thermal_14bit.dtype == np.uint16
assert naive_img.dtype == np.uint8
assert agc_img.dtype == np.uint8

# Naive shift'te arka plan (4100 >> 6 = 64) ile nehir (3100 >> 6 = 48) arasındaki kontrast çok düşüktür (fark ~ 16)
# AGC'de ise min (3000) 0'a, max (13000) 255'e açılır; zırhlı hedef 255'te parlar!
target_pixel_14 = thermal_14bit[75, 75]
target_pixel_naive = naive_img[75, 75]
target_pixel_agc = agc_img[75, 75]

bg_pixel_agc = agc_img[10, 10]
contrast_agc = int(target_pixel_agc) - int(bg_pixel_agc)
contrast_naive = int(target_pixel_naive) - int(naive_img[10, 10])

assert contrast_agc > contrast_naive * 1.5, "AGC kontrastı naive yaklaşımdan belirgin derecede yüksek olmalıdır!"

print("[PASS] Kod 3: Termal 14-bit Radiometric AGC ve Dinamik Kontrast Doğrulandı.")
print(f"  - Sahne Dinamik Aralığı  : {min_lsb} LSB .. {max_lsb} LSB (Fark: {max_lsb - min_lsb} seviye)")
print(f"  - Zırhlı Hedef Pikseli   : 14-bit={target_pixel_14} LSB | Naive U8={target_pixel_naive} | AGC U8={target_pixel_agc}")
print(f"  - Hedef/Arka Plan Kontrast: Naive={contrast_naive} seviye -> AGC={contrast_agc} seviye (Kontrast Artışı: %{((contrast_agc/contrast_naive)-1)*100:.1f})")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik Görsel Algılama Hata Enjeksiyonu Testi
# Stride uyuşmazlığı, sayısal taşma kalkanı ve NCHW/NHWC tensör dönüşümü.
# ============================================================================

# --- TEST 1: Stride Uyuşmazlığı ve Kayma Tespiti ---
print("[TEST 1] Pitch/Stride Uyuşmazlığı (Stride Misalignment) Denetimi...")
def verify_stride_integrity(width: int, channels: int, bytes_per_elem: int, actual_stride: int) -> bool:
    minimal_stride = width * channels * bytes_per_elem
    if actual_stride < minimal_stride:
        raise ValueError(f"HATA: Stride ({actual_stride}) minimum satır genişliğinden ({minimal_stride}) küçük olamaz!")
    # Stride'ın donanımsal hizalamaya uygunluğu (Örn: 8 bayt katı)
    is_aligned = (actual_stride % 8) == 0
    return is_aligned

assert verify_stride_integrity(width=640, channels=3, bytes_per_elem=1, actual_stride=1920) == True # 1920 % 8 == 0
assert verify_stride_integrity(width=640, channels=1, bytes_per_elem=2, actual_stride=1280) == True

try:
    verify_stride_integrity(width=640, channels=3, bytes_per_elem=1, actual_stride=1900) # 1900 < 1920!
    assert False, "Yetersiz stride hatası yakalanamadı!"
except ValueError as e:
    print(f"  [BEKLENEN HATA YAKALANDI] {e}")
print("  [PASS] Test 1: Stride bellek bütünlüğü başarıyla doğrulandı.\n")

# --- TEST 2: Güvenli Doyumlu Tip Dönüşümü (Saturating Cast) ---
print("[TEST 2] Sayısal Taşma ve Tersine Dönme (Roll-over) Kalkanı...")
def unsafe_cast_u16_to_u8(val: int) -> int:
    return val & 0xFF # Tehlikeli modüler kesme

def safe_saturating_cast_u16_to_u8(val: int, v_min: int = 0, v_max: int = 16383) -> int:
    # Güvenli ölçekleme ve 0..255 aralığına doyumlu kırpma
    if val < v_min: return 0
    if val > v_max: return 255
    scaled = ((val - v_min) / (v_max - v_min)) * 255.0
    return int(np.clip(scaled, 0, 255))

hot_target_lsb = 14500 # Sıcak hedef
unsafe_result = unsafe_cast_u16_to_u8(hot_target_lsb)
safe_result = safe_saturating_cast_u16_to_u8(hot_target_lsb)

# 14500 & 0xFF = 164 (rastgele düşük bir değer, sıcak hedef soğuk gibi görünür!)
# Güvenli dönüşümde ise 14500 -> ~ 225 parlak beyaz görünür!
assert unsafe_result != safe_result
assert safe_result > 220, f"Sıcak hedef doyumda yüksek olmalıydı: {safe_result}"
print(f"  - Sıcak Hedef (14500 LSB) -> Güvensiz Cast: {unsafe_result} (HATA: Yanıltıcı Değer!)")
print(f"  - Sıcak Hedef (14500 LSB) -> Doyumlu Cast: {safe_result} [DOĞRU PARLAK HEDEF]")
print("  [PASS] Test 2: Güvenli doyumlu tip dönüşümü başarıyla doğrulandı.\n")

# --- TEST 3: NCHW vs NHWC Tensör Boyut Sıralaması Dönüşümü ---
print("[TEST 3] OpenCV [H, W, C] -> TensorRT [1, C, H, W] Tensör Düzeni Dönüşümü...")
def transform_cv_to_tensorrt(image_hwc: np.ndarray) -> np.ndarray:
    # 1. Kontrol
    assert image_hwc.ndim == 3, "Görüntü 3 boyutlu olmalıdır [H, W, C]"
    # 2. Transpose: [H, W, C] -> [C, H, W]
    image_chw = np.transpose(image_hwc, (2, 0, 1))
    # 3. Batch boyutu ekleme: [C, H, W] -> [1, C, H, W]
    image_nchw = np.expand_dims(image_chw, axis=0)
    # 4. Bellek sürekliliği (Contiguous memory)
    return np.ascontiguousarray(image_nchw, dtype=np.float32) / 255.0

test_img_cv = np.zeros((480, 640, 3), dtype=np.uint8)
test_img_cv[100, 200, 0] = 255 # Mavi piksel

tensorrt_tensor = transform_cv_to_tensorrt(test_img_cv)
assert tensorrt_tensor.shape == (1, 3, 480, 640), f"Şekil hatalı: {tensorrt_tensor.shape}"
assert tensorrt_tensor.flags['C_CONTIGUOUS'] == True, "Tensör bellekte sürekli (contiguous) değil!"
assert np.isclose(tensorrt_tensor[0, 0, 100, 200], 1.0), "Piksel değeri normalize aktarılamadı!"

print(f"  - OpenCV Giriş Şekli     : {test_img_cv.shape} (H={test_img_cv.shape[0]}, W={test_img_cv.shape[1]}, C={test_img_cv.shape[2]})")
print(f"  - TensorRT Çıkış Şekli    : {tensorrt_tensor.shape} (N=1, C=3, H=480, W=640) [C_CONTIGUOUS: {tensorrt_tensor.flags['C_CONTIGUOUS']}]")
print("  [PASS] Test 3: NCHW tensör dönüşümü başarıyla doğrulandı.\n")

print("[PASS] Kod 4: 3 Kritik Görsel Algılama Hata Enjeksiyonu Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 100.000 Piksel Normalizasyon & Bit Dönüşüm Benchmark'ı
# Yüksek hızlı piksel dönüşümü, MegaPiksel/saniye verimi ve persentil analizi.
# ============================================================================
import time
import numpy as np

NUM_BLOCKS = 100_000
BLOCK_SIZE = 16 # Her adımda 16 piksellik SIMD vektörü dönüştürülür (Toplam 1.6 Milyon piksel)

# 14-bit rastgele FLIR verisi üret
raw_u16_blocks = np.random.randint(3000, 14000, size=(NUM_BLOCKS, BLOCK_SIZE), dtype=np.uint16)
latencies_us = np.empty(NUM_BLOCKS, dtype=np.float64)

scale_factor = 1.0 / 16383.0 # Çarpma bölmeden 3 kat daha hızlıdır

print(f"[BENCHMARK] {NUM_BLOCKS:,} Blok x {BLOCK_SIZE} Piksel ({NUM_BLOCKS * BLOCK_SIZE:,} Piksel) Normalizasyonu Başlatılıyor...")
t_start = time.perf_counter()

for i in range(NUM_BLOCKS):
    t0 = time.perf_counter_ns()
    
    # SIMD benzeri 16 piksellik float dönüşümü ve normalizasyon
    block = raw_u16_blocks[i]
    norm_f32 = block.astype(np.float32) * scale_factor
    
    t_end = time.perf_counter_ns()
    latencies_us[i] = (t_end - t0) / 1000.0 # ns -> us

t_total = time.perf_counter() - t_start

total_pixels = NUM_BLOCKS * BLOCK_SIZE
throughput_mpixels_sec = (total_pixels / t_total) / 1e6
avg_lat = float(np.mean(latencies_us))
p50 = float(np.percentile(latencies_us, 50))
p90 = float(np.percentile(latencies_us, 90))
p99 = float(np.percentile(latencies_us, 99))

print(f"\n[PİKSEL DÖNÜŞÜM BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - İşlem Verimi        : {throughput_mpixels_sec:,.2f} MegaPiksel/saniye (Hedef: > 5.0 MP/s)")
print(f"  - Ortalama Gecikme    : {avg_lat:.2f} µs / 16-piksel blok")
print(f"  - p50 (Medyan)        : {p50:.2f} µs")
print(f"  - p90 Gecikme         : {p90:.2f} µs")
print(f"  - p99 Kuyruk Gecikmesi: {p99:.2f} µs (Hedef: < 15.0 µs)")

# Doğrulamalar
assert throughput_mpixels_sec > 5.0, f"Piksel verimi yetersiz: {throughput_mpixels_sec} MP/s"
assert p99 < 15.0, f"p99 kuyruk gecikmesi çok yüksek: {p99} µs"

print("\n[PASS] Kod 5: 100.000 Piksel Blok Dönüşüm Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli 300 DPI Koyu Tema Görsel Algılama Dashboard'u
# gun_246_goruntu_pixel_channel_resolution_bitdepth.png dosyasını üretir.
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
import os

COLOR_BG = "#0F172A"       # Slate 900
COLOR_PANEL = "#1E293B"    # Slate 800
COLOR_TEXT = "#F8FAFC"     # Slate 50
COLOR_MUTED = "#94A3B8"    # Slate 400
COLOR_CYAN = "#38BDF8"     # Cyan
COLOR_YELLOW = "#FBBF24"   # Sarı
COLOR_RED = "#F87171"      # Kırmızı
COLOR_GREEN = "#34D399"    # Zümrüt Yeşili
COLOR_INDIGO = "#818CF8"   # İndigo

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: Bit Derinliği ve Sayısal Dinamik Aralık Karşılaştırması ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

bit_depths = [1, 8, 10, 12, 14, 16]
dr_db = [6.02 * b for b in bit_depths]
levels = [2**b for b in bit_depths]
labels_p1 = [f"{b}-bit\n({levels[i]:,} Seviye)" for i, b in enumerate(bit_depths)]

bars1 = ax1.bar(labels_p1, dr_db, color=COLOR_CYAN, edgecolor=COLOR_TEXT, width=0.55)
for bar, val in zip(bars1, dr_db):
    ax1.text(bar.get_x() + bar.get_width()/2.0, val + 2.5, f"{val:.1f} dB", 
             color=COLOR_TEXT, ha="center", fontsize=9, fontweight="bold")

ax1.axhline(48.16, color=COLOR_YELLOW, linestyle="--", linewidth=1.5, label="8-bit EO Standardı (48.2 dB)")
ax1.axhline(84.28, color=COLOR_RED, linestyle="--", linewidth=1.5, label="14-bit FLIR Standardı (84.3 dB)")

ax1.set_title("Panel 1: Bit Derinliği ve Sayısal Dinamik Aralık (Dynamic Range dB)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_ylabel("Dinamik Aralık [dB]", color=COLOR_MUTED, fontsize=10)
ax1.set_ylim(0, 115)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")
ax1.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper left", fontsize=8)

# --- PANEL 2: Çözünürlük ve Ham Veri Bant Genişliği (Gbps) Matrisi ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

res_names = [s.name.split()[0] for s in sensor_arsenal]
bw_vals = [s.bandwidth_gbps for s in sensor_arsenal]
ram_vals = [s.memory_throughput_mb_s for s in sensor_arsenal]

x_pos = np.arange(len(res_names))
w = 0.35

bars2_1 = ax2.bar(x_pos - w/2, bw_vals, width=w, color=COLOR_YELLOW, edgecolor=COLOR_TEXT, label="Ham Bant Genişliği (Gbps)")
ax2_twin = ax2.twinx()
bars2_2 = ax2_twin.bar(x_pos + w/2, ram_vals, width=w, color=COLOR_GREEN, edgecolor=COLOR_TEXT, label="RAM Trafiği (MB/s)")

ax2.set_title("Panel 2: Çözünürlük, Bit Derinliği ve Donanım Veri Yolu Yükü", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_xticks(x_pos)
ax2.set_xticklabels([f"{s.name}\n({s.width}x{s.height})" for s in sensor_arsenal], fontsize=8, color=COLOR_MUTED)
ax2.set_ylabel("Ham Veri Akışı [Gbps]", color=COLOR_YELLOW, fontsize=10)
ax2_twin.set_ylabel("RAM Yazma Hızı [MB/s]", color=COLOR_GREEN, fontsize=10)
ax2.tick_params(colors=COLOR_MUTED)
ax2_twin.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6)

# --- PANEL 3: 100k Piksel Blok Dönüşüm Gecikme Dağılımı ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

ax3.hist(latencies_us, bins=50, color=COLOR_INDIGO, alpha=0.8, edgecolor="#4338CA")
ax3.axvline(p50, color=COLOR_GREEN, linestyle="-", linewidth=2.2, label=f"p50 (Medyan): {p50:.2f} µs")
ax3.axvline(p90, color=COLOR_YELLOW, linestyle="--", linewidth=2.2, label=f"p90: {p90:.2f} µs")
ax3.axvline(p99, color=COLOR_RED, linestyle="-.", linewidth=2.2, label=f"p99: {p99:.2f} µs")

ax3.set_title("Panel 3: 100k Blok Piksel Normalizasyon Gecikme Dağılımı (16-Piksel SIMD)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("İşlem Gecikmesi [µs]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("Blok Sayısı", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 4: Termal 14-bit AGC Histogramı ve Kontrast Analizi ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

ax4.hist(thermal_14bit.ravel(), bins=60, color=COLOR_CYAN, alpha=0.5, label="14-bit FLIR Ham Spektrum (LSB)")
ax4.axvline(min_lsb, color=COLOR_GREEN, linestyle="--", linewidth=1.8, label=f"Min Eşik: {min_lsb} LSB")
ax4.axvline(max_lsb, color=COLOR_RED, linestyle="--", linewidth=1.8, label=f"Max Eşik (Zırhlı Hedef): {max_lsb} LSB")

ax4.set_title("Panel 4: Radyometrik FLIR Spektrumu ve Min-Max Dinamik AGC Haritalama", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_xlabel("Piksel Sayısal Değeri (14-bit LSB)", color=COLOR_MUTED, fontsize=10)
ax4.set_ylabel("Piksel Sayısı", color=COLOR_MUTED, fontsize=10)
ax4.tick_params(colors=COLOR_MUTED)
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax4.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

plt.suptitle("FAZ F8 GÜN 246 — GÖRÜNTÜ TEMELLERİ: PİKSEL, KANAL, ÇÖZÜNÜRLÜK VE BİT DERİNLİĞİ", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_246/gun_246_goruntu_pixel_channel_resolution_bitdepth.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

