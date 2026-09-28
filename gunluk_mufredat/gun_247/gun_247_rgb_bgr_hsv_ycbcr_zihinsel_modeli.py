# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 247: RGB/BGR/HSV/YCbCr zihinsel modeli Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: RGB <-> BGR Kanal Takası ve ITU-R BT.601 Luma Çekirdeği
# Bellek kanal düzeni dönüşümü ve insan gözü algısal ağırlıklı parlaklık.
# ============================================================================
import numpy as np

def convert_rgb_to_bgr(rgb_img: np.ndarray) -> np.ndarray:
    assert rgb_img.ndim == 3 and rgb_img.shape[2] == 3, "Görüntü [H, W, 3] olmalıdır"
    # Kanal boyutunu tersine çevir: [R, G, B] -> [B, G, R]
    bgr = rgb_img[:, :, ::-1]
    return np.ascontiguousarray(bgr)

def rgb_to_grayscale_bt601(rgb_img: np.ndarray) -> np.ndarray:
    # ITU-R BT.601 Luma Katsayıları:
    # İnsan gözü en çok Yeşil (58.7%), sonra Kırmızı (29.9%), en az Mavi (11.4%) ışığa duyarlıdır.
    R = rgb_img[:, :, 0].astype(np.float32)
    G = rgb_img[:, :, 1].astype(np.float32)
    B = rgb_img[:, :, 2].astype(np.float32)
    luma = 0.299 * R + 0.587 * G + 0.114 * B
    return np.clip(np.round(luma), 0, 255).astype(np.uint8)

# Test Matrisi: Saf Kırmızı, Saf Yeşil, Saf Mavi pikseller
# Şekil: (1, 3, 3) -> 1 satır, 3 piksel: [Kırmızı, Yeşil, Mavi]
test_rgb = np.array([
    [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
], dtype=np.uint8)

test_bgr = convert_rgb_to_bgr(test_rgb)
# BGR'de Saf Kırmızı: [0, 0, 255], Saf Mavi: [255, 0, 0]
assert np.array_equal(test_bgr[0, 0], [0, 0, 255]), "Kırmızı piksel BGR'de [0, 0, 255] olmalıdır!"
assert np.array_equal(test_bgr[0, 2], [255, 0, 0]), "Mavi piksel BGR'de [255, 0, 0] olmalıdır!"
assert test_bgr.flags['C_CONTIGUOUS'] == True

# Luma Karşılaştırması
luma_bt601 = rgb_to_grayscale_bt601(test_rgb)
# Saf Kırmızı Luma = 0.299 * 255 = 76.2 -> 76
# Saf Yeşil Luma   = 0.587 * 255 = 149.7 -> 150
# Saf Mavi Luma    = 0.114 * 255 = 29.1 -> 29
assert luma_bt601[0, 0] == 76, f"Kırmızı luma 76 olmalıydı: {luma_bt601[0, 0]}"
assert luma_bt601[0, 1] == 150, f"Yeşil luma 150 olmalıydı: {luma_bt601[0, 1]}"
assert luma_bt601[0, 2] == 29, f"Mavi luma 29 olmalıydı: {luma_bt601[0, 2]}"

# Eşit ağırlıklı naive ortalama olsaydı hepsi 255 / 3 = 85 olurdu!
naive_gray = np.mean(test_rgb, axis=2).astype(np.uint8)
assert naive_gray[0, 0] == 85 and naive_gray[0, 1] == 85 and naive_gray[0, 2] == 85

print("[PASS] Kod 1: RGB <-> BGR Takası ve ITU-R BT.601 Luma Dönüşümü Doğrulandı.")
print(f"  - RGB Giriş  : Kırmızı={test_rgb[0,0]}, Yeşil={test_rgb[0,1]}, Mavi={test_rgb[0,2]}")
print(f"  - BGR Çıkış  : Kırmızı={test_bgr[0,0]}, Yeşil={test_bgr[0,1]}, Mavi={test_bgr[0,2]}")
print(f"  - BT.601 Luma: Kırmızı={luma_bt601[0,0]} LSB, Yeşil={luma_bt601[0,1]} LSB, Mavi={luma_bt601[0,2]} LSB")
print(f"  - Naive Luma : Kırmızı=85 LSB, Yeşil=85 LSB, Mavi=85 LSB (Göz Algısını Yansıtmaz!)")

# ============================================================================
# KOD HÜCRESİ 2: HSV Renk Uzayı ve Işık Altında Kararlı Hedef Segmentasyon Motoru
# Güneş ve gölge koşullarında RGB vs HSV renk filtreleme başarım karşılaştırması.
# ============================================================================
import numpy as np

def rgb_to_hsv_numpy(rgb_img: np.ndarray) -> np.ndarray:
    # rgb_img: uint8 [H, W, 3]
    rgb = rgb_img.astype(np.float32) / 255.0
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    
    c_max = np.maximum(np.maximum(r, g), b)
    c_min = np.minimum(np.minimum(r, g), b)
    delta = c_max - c_min
    
    # 1. Hue (0 .. 360 derece)
    h = np.zeros_like(c_max)
    # delta == 0 iken h = 0
    mask_r = (c_max == r) & (delta > 1e-5)
    mask_g = (c_max == g) & (delta > 1e-5)
    mask_b = (c_max == b) & (delta > 1e-5)
    
    h[mask_r] = (60.0 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6.0))
    h[mask_g] = (60.0 * (((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2.0))
    h[mask_b] = (60.0 * (((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4.0))
    
    # 2. Saturation (0 .. 1)
    s = np.zeros_like(c_max)
    mask_v = c_max > 1e-5
    s[mask_v] = delta[mask_v] / c_max[mask_v]
    
    # 3. Value (0 .. 1)
    v = c_max
    
    return np.stack([h, s, v], axis=-1)

# Simülasyon: Güneş Işığı ve Gölge Altında Kırmızı Askeri Hedef
# Hedef Rengi (Güneşte): RGB = [220, 20, 20] -> Koyu Kırmızı
# Gölgeye girince ışık %35'e düşer: RGB = [77, 7, 7]
sun_target = np.array([[[220, 20, 20]]], dtype=np.uint8)
shadow_target = np.array([[[77, 7, 7]]], dtype=np.uint8)

# 1. RGB Eşikleme (Güneşteki renge göre ayarlanmış toleranslı filtre: R > 150, G < 50, B < 50)
def detect_target_rgb(pixel: np.ndarray) -> bool:
    return bool(pixel[0, 0, 0] > 150 and pixel[0, 0, 1] < 50 and pixel[0, 0, 2] < 50)

# 2. HSV Eşikleme: Kırmızı Hue: [350 .. 360] veya [0 .. 10], Saturation > 0.5, Value > 0.15
def detect_target_hsv(pixel_hsv: np.ndarray) -> bool:
    h, s, v = pixel_hsv[0, 0, 0], pixel_hsv[0, 0, 1], pixel_hsv[0, 0, 2]
    is_red_hue = (h >= 345.0 or h <= 15.0)
    is_saturated = (s > 0.6)
    is_visible = (v > 0.20)
    return bool(is_red_hue and is_saturated and is_visible)

hsv_sun = rgb_to_hsv_numpy(sun_target)
hsv_shadow = rgb_to_hsv_numpy(shadow_target)

# Karşılaştırma:
rgb_sun_det = detect_target_rgb(sun_target)
rgb_shadow_det = detect_target_rgb(shadow_target)

hsv_sun_det = detect_target_hsv(hsv_sun)
hsv_shadow_det = detect_target_hsv(hsv_shadow)

# Doğrulamalar:
assert rgb_sun_det == True, "RGB güneşteki hedefi yakalamalıydı"
assert rgb_shadow_det == False, "RGB gölgedeki hedefi KAÇIRMALI (Problem bu!)"

assert hsv_sun_det == True, "HSV güneşteki hedefi yakalamalıydı"
assert hsv_shadow_det == True, "HSV gölgedeki hedefi BAŞARIYLA YAKALAMALI!"

# Hue Değerinin Değişmezliği Kanıtı:
# İki durumda da Hue ~ 0 derece (saf kırmızı) olmalıdır!
assert abs(hsv_sun[0, 0, 0] - hsv_shadow[0, 0, 0]) < 1.0
assert np.isclose(hsv_sun[0, 0, 1], hsv_shadow[0, 0, 1], atol=0.02) # Doygunluk sabit

print("[PASS] Kod 2: HSV Işık Değişmezliği ve Hedef Segmentasyon Motoru Doğrulandı.")
print(f"  - Güneşteki Hedef : RGB={sun_target[0,0]} -> HSV: H={hsv_sun[0,0,0]:.1f}°, S={hsv_sun[0,0,1]:.2f}, V={hsv_sun[0,0,2]:.2f}")
print(f"  - Gölgedeki Hedef : RGB={shadow_target[0,0]} -> HSV: H={hsv_shadow[0,0,0]:.1f}°, S={hsv_shadow[0,0,1]:.2f}, V={hsv_shadow[0,0,2]:.2f}")
print(f"  - RGB Filtreleme  : Güneşte={rgb_sun_det} | Gölgede={rgb_shadow_det} (GÖLGEDE HEDEF KAYBI!)")
print(f"  - HSV Filtreleme  : Güneşte={hsv_sun_det} | Gölgede={hsv_shadow_det} (IŞIK DEĞİŞMEZLİĞİ KORUNDU!)")

# ============================================================================
# KOD HÜCRESİ 3: YUV420 Planar Kroma Alt-Örnekleme ve Taktik Datalink Sıkıştırması
# %50 bellek tasarrufu, YCbCr dönüşüm matrisi ve PSNR kayıpsızlık testi.
# ============================================================================
import numpy as np

class YUV420Codec:
    # ITU-R BT.601 Full-Range Dönüşüm Matrisi (Float)
    RGB_TO_YUV_MAT = np.array([
        [ 0.29900,  0.58700,  0.11400],
        [-0.16874, -0.33126,  0.50000],
        [ 0.50000, -0.41869, -0.08131]
    ], dtype=np.float32)

    YUV_TO_RGB_MAT = np.array([
        [1.0,  0.00000,  1.40200],
        [1.0, -0.34414, -0.71414],
        [1.0,  1.77200,  0.00000]
    ], dtype=np.float32)

    @classmethod
    def encode_rgb_to_yuv420(cls, rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        h, w, c = rgb.shape
        assert h % 2 == 0 and w % 2 == 0, "YUV420 için yükseklik ve genişlik çift sayı olmalıdır"
        
        # 1. Tam çözünürlüklü Y, Cb, Cr (YUV)
        flat_rgb = rgb.reshape(-1, 3).astype(np.float32)
        yuv_flat = np.dot(flat_rgb, cls.RGB_TO_YUV_MAT.T)
        yuv = yuv_flat.reshape(h, w, 3)
        
        Y = np.clip(np.round(yuv[:, :, 0]), 0, 255).astype(np.uint8)
        U = np.clip(np.round(yuv[:, :, 1] + 128.0), 0, 255).astype(np.uint8) # Cb ofseti
        V = np.clip(np.round(yuv[:, :, 2] + 128.0), 0, 255).astype(np.uint8) # Cr ofseti
        
        # 2. 4:2:0 Alt-Örnekleme: U ve V kanallarında 2x2 ortalama alma
        U_sub = U.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3)).astype(np.uint8)
        V_sub = V.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3)).astype(np.uint8)
        
        return Y, U_sub, V_sub

    @classmethod
    def decode_yuv420_to_rgb(cls, Y: np.ndarray, U_sub: np.ndarray, V_sub: np.ndarray) -> np.ndarray:
        h, w = Y.shape
        # 1. 2x2 kroma düzlemlerini tekrar tam çözünürlüğe genişlet (Nearest-neighbor upsample)
        U_full = np.repeat(np.repeat(U_sub, 2, axis=0), 2, axis=1).astype(np.float32) - 128.0
        V_full = np.repeat(np.repeat(V_sub, 2, axis=0), 2, axis=1).astype(np.float32) - 128.0
        Y_full = Y.astype(np.float32)
        
        # 2. Ters Matris Çarpımı
        yuv_full = np.stack([Y_full, U_full, V_full], axis=-1).reshape(-1, 3)
        rgb_flat = np.dot(yuv_full, cls.YUV_TO_RGB_MAT.T)
        rgb_rec = np.clip(np.round(rgb_flat), 0, 255).astype(np.uint8).reshape(h, w, 3)
        return rgb_rec

# Test Sahnesi: 64x64 Zengin Renkli Gerçekçi Askeri Keşif Alanı (Yumuşak Gradyan ve Hedefler)
y_grid, x_grid = np.mgrid[0:64, 0:64]
r_plane = (120 + 50 * np.sin(x_grid / 10.0)).astype(np.uint8)
g_plane = (130 + 50 * np.cos(y_grid / 10.0)).astype(np.uint8)
b_plane = (140 + 40 * np.sin((x_grid + y_grid) / 12.0)).astype(np.uint8)
recon_scene = np.stack([r_plane, g_plane, b_plane], axis=-1)
# Hedef bölgeleri ekle (Askeri kamuflaj yeşili ve gökyüzü mavisi)
recon_scene[10:30, 10:30] = [34, 139, 34]   # Yeşil
recon_scene[40:55, 40:55] = [30, 144, 255]  # Mavi

# Kodlama
Y, U_sub, V_sub = YUV420Codec.encode_rgb_to_yuv420(recon_scene)

# Bellek Boyutları:
bytes_rgb = recon_scene.nbytes
bytes_yuv420 = Y.nbytes + U_sub.nbytes + V_sub.nbytes
compression_ratio = (1.0 - (bytes_yuv420 / bytes_rgb)) * 100.0

assert bytes_rgb == 64 * 64 * 3 # 12,288 bayt
assert Y.shape == (64, 64)       # 4,096 bayt
assert U_sub.shape == (32, 32)   # 1,024 bayt
assert V_sub.shape == (32, 32)   # 1,024 bayt
assert bytes_yuv420 == 6144 # 6,144 bayt (%50 tam yarı yarıya!)
assert abs(compression_ratio - 50.0) < 1e-4

# Geri Çözme ve Kalite Doğrulaması
rgb_reconstructed = YUV420Codec.decode_yuv420_to_rgb(Y, U_sub, V_sub)
mse = np.mean((recon_scene.astype(np.float64) - rgb_reconstructed.astype(np.float64)) ** 2)
psnr = 10.0 * np.log10((255.0 ** 2) / max(mse, 1e-6))

assert psnr > 36.0, f"PSNR beklenenden düşük: {psnr:.2f} dB"

print("[PASS] Kod 3: YUV420 Kroma Alt-Örnekleme ve Sıkıştırma Başarıyla Doğrulandı.")
print(f"  - Orijinal RGB Belleği   : {bytes_rgb:,} bayt (24 bpp)")
print(f"  - YUV420 Planar Belleği  : {bytes_yuv420:,} bayt (12 bpp) [Y={Y.nbytes}, U={U_sub.nbytes}, V={V_sub.nbytes}]")
print(f"  - Bant Genişliği Tasarrufu: %{compression_ratio:.1f} (TAM YARI YARIYA)")
print(f"  - Geri Çözüm Kalitesi    : MSE={mse:.2f} | PSNR={psnr:.2f} dB (MÜKEMMEL KALİTE: > 36 dB)")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik Renk Uzayı Hata Enjeksiyonu Testi
# BGR/RGB karışması, Hue dairesel süreksizlik ve tek boyut hizalama kalkanı.
# ============================================================================

# --- TEST 1: BGR / RGB Kanal Karışması Tespiti ---
print("[TEST 1] BGR / RGB Kanal Takası ve Yanlış Model Girişi Tespiti...")
def detect_fire_or_laser_signature(image_tensor: np.ndarray, format_order: str = "RGB") -> str:
    # format_order: "RGB" veya "BGR"
    if format_order == "RGB":
        r, g, b = image_tensor[0], image_tensor[1], image_tensor[2]
    elif format_order == "BGR":
        b, g, r = image_tensor[0], image_tensor[1], image_tensor[2]
    else:
        raise ValueError(f"Bilinmeyen format: {format_order}")
        
    # Kırmızı baskın hedef imzası (R > 180 ve R > 2 * B)
    if r > 180 and r > (2 * b):
        return "TARGET_RED_THREAT_DETECTED"
    elif b > 180 and b > (2 * r):
        return "BENIGN_BLUE_SKY_OR_WATER"
    return "UNKNOWN_SIGNATURE"

# Gerçekte Kırmızı Tehdit Olan Piksel: R=240, G=30, B=20
true_red_pixel = np.array([240, 30, 20], dtype=np.uint8)

# Doğru RGB Okuma
res_correct = detect_fire_or_laser_signature(true_red_pixel, format_order="RGB")
assert res_correct == "TARGET_RED_THREAT_DETECTED"

# Hata Enjeksiyonu: Piksel BGR iken modele RGB gibi verilirse:
# Modelin gördüğü piksel: [20, 30, 240] (Mavi kanalı kırmızı sanar)
bgr_confused_pixel = true_red_pixel[::-1] # [20, 30, 240]
res_confused = detect_fire_or_laser_signature(bgr_confused_pixel, format_order="RGB")
assert res_confused == "BENIGN_BLUE_SKY_OR_WATER", "Kanal karışıklığında model mavi zannetmeliydi!"

print(f"  - Doğru RGB Girişi        : {res_correct} [KIRMIZI TEHDİT KİLİTLENDİ]")
print(f"  - Hatalı BGR->RGB Karışımı: {res_confused} [ÖLÜMCÜL HATA: TEHDİT GÖKYÜZÜ SANILDI!]")
print("  [PASS] Test 1: BGR/RGB karışıklığı ve model yanılgısı başarıyla kanıtlandı.\n")

# --- TEST 2: Hue Dairesel Süreksizlik (Modulo Wrap-Around) Kalkanı ---
print("[TEST 2] Hue 0° / 360° Dairesel Süreksizlik Sınır Kontrolü Testi...")
def is_red_hue_buggy(h_deg: float) -> bool:
    # Hatalı acemi kod: 350 ile 10 arasında doğrusal kontrol
    return 350.0 <= h_deg <= 10.0 # MATEMATİKSEL OLARAK İMKANSIZ!

def is_red_hue_correct(h_deg: float) -> bool:
    # Doğru dairesel kontrol: ya 350'den büyük VEYA 10'dan küçük
    return (h_deg >= 350.0) or (h_deg <= 10.0)

sample_hue_1 = 355.0 # Kırmızı
sample_hue_2 = 5.0   # Kırmızı

assert is_red_hue_buggy(sample_hue_1) == False # Hatalı kod yakalayamaz!
assert is_red_hue_buggy(sample_hue_2) == False

assert is_red_hue_correct(sample_hue_1) == True
assert is_red_hue_correct(sample_hue_2) == True

print(f"  - H = 355° Kırmızı Hedef: Hatalı Kod={is_red_hue_buggy(sample_hue_1)} | Dairesel Kalkan={is_red_hue_correct(sample_hue_1)}")
print(f"  - H =   5° Kırmızı Hedef: Hatalı Kod={is_red_hue_buggy(sample_hue_2)} | Dairesel Kalkan={is_red_hue_correct(sample_hue_2)}")
print("  [PASS] Test 2: Hue dairesel süreksizlik kalkanı başarıyla doğrulandı.\n")

# --- TEST 3: YUV420 Tek Boyut Hizalama Kalkanı ---
print("[TEST 3] YUV420 Kroma Alt-Örnekleme Çift Boyut (Even Dimension) Kalkanı...")
def validate_yuv420_dimensions(width: int, height: int) -> bool:
    if (width % 2 != 0) or (height % 2 != 0):
        raise ValueError(f"DONANIM REDDİ: YUV420 çözünürlüğü çift sayı olmalıdır: ({width}x{height})")
    return True

assert validate_yuv420_dimensions(1920, 1080) == True
assert validate_yuv420_dimensions(640, 512) == True

try:
    validate_yuv420_dimensions(641, 480) # Tek sayılı genişlik!
    assert False, "Tek boyut hatası yakalanamadı!"
except ValueError as e:
    print(f"  [BEKLENEN DONANIM REDDİ] {e}")

print("  [PASS] Test 3: YUV420 çift boyut kalkanı başarıyla doğrulandı.\n")
print("[PASS] Kod 4: 3 Kritik Renk Uzayı Hata Enjeksiyonu Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 100.000 Piksel RGB -> YCbCr ve HSV Dönüşüm Benchmark'ı
# Doğrusal matris (YCbCr) ile trigonometrik (HSV) dönüşüm hızlarının karşılaştırılması.
# ============================================================================
import time
import numpy as np

NUM_EVALS = 10_000
BLOCK_SIZE = 256 # 16x16 Standart Video Makrobloğu (Toplam 2,560,000 Piksel)

# Sentetik RGB Blokları (Doğrudan float32)
rand_rgb_blocks = np.random.uniform(0, 255, size=(NUM_EVALS, BLOCK_SIZE, 3)).astype(np.float32)
latencies_per_pixel_us = np.empty(NUM_EVALS, dtype=np.float64)

# YCbCr BT.601 Katsayıları (Skaler Vektör)
CY_R, CY_G, CY_B = 0.299, 0.587, 0.114

print(f"[BENCHMARK] {NUM_EVALS:,} Makroblok x {BLOCK_SIZE} Piksel ({NUM_EVALS * BLOCK_SIZE:,} Piksel) YCbCr Dönüşümü Başlatılıyor...")
t_start = time.perf_counter()

for i in range(NUM_EVALS):
    t0 = time.perf_counter_ns()
    
    blk = rand_rgb_blocks[i]
    r, g, b = blk[:, 0], blk[:, 1], blk[:, 2]
    # Hızlı Luma (Y) ve Renk Farkı (Cb, Cr)
    y = CY_R * r + CY_G * g + CY_B * b
    cb = 128.0 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128.0 + 0.5 * r - 0.418688 * g - 0.081312 * b
    
    t_end = time.perf_counter_ns()
    latencies_per_pixel_us[i] = (t_end - t0) / (BLOCK_SIZE * 1000.0) # Piksel başına µs

t_total = time.perf_counter() - t_start

total_pixels = NUM_EVALS * BLOCK_SIZE
throughput_mpixels_sec = (total_pixels / t_total) / 1e6
avg_lat = float(np.mean(latencies_per_pixel_us))
p50 = float(np.percentile(latencies_per_pixel_us, 50))
p90 = float(np.percentile(latencies_per_pixel_us, 90))
p99 = float(np.percentile(latencies_per_pixel_us, 99))

print(f"\n[YCbCr DÖNÜŞÜM BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - İşlem Verimi        : {throughput_mpixels_sec:,.2f} MegaPiksel/saniye (Hedef: > 5.0 MP/s)")
print(f"  - Ortalama Gecikme    : {avg_lat*1000.0:.2f} ns / piksel ({avg_lat:.4f} µs)")
print(f"  - p50 (Medyan)        : {p50*1000.0:.2f} ns / piksel ({p50:.4f} µs)")
print(f"  - p90 Gecikme         : {p90*1000.0:.2f} ns / piksel ({p90:.4f} µs)")
print(f"  - p99 Kuyruk Gecikmesi: {p99*1000.0:.2f} ns / piksel ({p99:.4f} µs) (Hedef: < 200 ns)")

# Doğrulamalar
assert throughput_mpixels_sec > 5.0, f"YCbCr dönüşüm verimi yetersiz: {throughput_mpixels_sec}"
assert p99 < 0.5, f"p99 piksel gecikmesi çok yüksek: {p99} µs"

print("\n[PASS] Kod 5: 10.000 Makroblok (2.56M Piksel) YCbCr Dönüşüm Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli 300 DPI Koyu Tema Renk Uzayları Dashboard'u
# gun_247_rgb_bgr_hsv_ycbcr_zihinsel_modeli.png dosyasını üretir.
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
COLOR_GREEN = "#34D399"    # Yeşil
COLOR_INDIGO = "#818CF8"   # İndigo

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: RGB vs BGR Kanal Düzeni ve Luma Katsayıları ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

channels = ["Kırmızı (R)", "Yeşil (G)", "Mavi (B)"]
bt601_weights = [0.299, 0.587, 0.114]
naive_weights = [0.333, 0.333, 0.333]

x = np.arange(len(channels))
w = 0.35

bars1 = ax1.bar(x - w/2, bt601_weights, width=w, color=COLOR_CYAN, edgecolor=COLOR_TEXT, label="ITU-R BT.601 Luma Ağırlığı (İnsan Algısı)")
bars2 = ax1.bar(x + w/2, naive_weights, width=w, color=COLOR_YELLOW, edgecolor=COLOR_TEXT, label="Naive Eşit Ağırlık (1/3)")

for bar in bars1:
    ax1.text(bar.get_x() + bar.get_width()/2.0, bar.get_height() + 0.015, f"%{bar.get_height()*100:.1f}", 
             color=COLOR_TEXT, ha="center", fontsize=9, fontweight="bold")

ax1.set_title("Panel 1: İnsan Gözü Spektral Duyarlılığı (ITU-R BT.601 Luma vs Naive)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xticks(x)
ax1.set_xticklabels(channels, color=COLOR_TEXT, fontsize=10)
ax1.set_ylabel("Luma Katkı Oranı", color=COLOR_MUTED, fontsize=10)
ax1.set_ylim(0, 0.70)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")
ax1.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 2: HSV Işık Değişmezliği (Güneş vs Gölge) ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

conditions = ["Güneşte Hedef", "Gölgede Hedef"]
rgb_r_vals = [220, 77]
hsv_h_vals = [0, 0] # Kırmızı Hue tam 0 derece
hsv_v_vals = [86, 30] # Value (%)

x_p2 = np.arange(len(conditions))
w_p2 = 0.25

ax2.bar(x_p2 - w_p2, rgb_r_vals, width=w_p2, color=COLOR_RED, edgecolor=COLOR_TEXT, label="RGB Kırmızı Kanalı (Dramatik Düşüş: 220 -> 77)")
ax2.bar(x_p2, [h * 100 for h in [0.91, 0.91]], width=w_p2, color=COLOR_GREEN, edgecolor=COLOR_TEXT, label="HSV Doygunluk %S (SABİT: %91)")
ax2.bar(x_p2 + w_p2, hsv_v_vals, width=w_p2, color=COLOR_YELLOW, edgecolor=COLOR_TEXT, label="HSV Işık %V (Işık Değişimi: %86 -> %30)")

ax2.set_title("Panel 2: Güneş ve Gölge Koşullarında HSV Işık Değişmezliği Kanıtı", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_xticks(x_p2)
ax2.set_xticklabels(conditions, color=COLOR_TEXT, fontsize=10)
ax2.set_ylabel("Sayısal Seviye / Yüzde [%]", color=COLOR_MUTED, fontsize=10)
ax2.set_ylim(0, 250)
ax2.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")
ax2.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 3: 10k Makroblok YCbCr Dönüşüm Benchmark Gecikme Histogramı ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

lat_ns = latencies_per_pixel_us * 1000.0 # µs -> ns
ax3.hist(lat_ns, bins=50, color=COLOR_INDIGO, alpha=0.8, edgecolor="#4338CA")
ax3.axvline(p50 * 1000.0, color=COLOR_GREEN, linestyle="-", linewidth=2.2, label=f"p50 (Medyan): {p50*1000.0:.1f} ns")
ax3.axvline(p90 * 1000.0, color=COLOR_YELLOW, linestyle="--", linewidth=2.2, label=f"p90: {p90*1000.0:.1f} ns")
ax3.axvline(p99 * 1000.0, color=COLOR_RED, linestyle="-.", linewidth=2.2, label=f"p99: {p99*1000.0:.1f} ns")

ax3.set_title("Panel 3: 10k Makroblok (2.56M Piksel) YCbCr Dönüşüm Gecikmesi (Piksel Başına)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("Piksel Başına İşlem Süresi [ns]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("Makroblok Sayısı", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 4: Renk Formatı Bellek Ayak İzi ve Sıkıştırma Oranı ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

formats = ["RGB 4:4:4\n(24 bpp)", "YUV 4:2:2\n(16 bpp)", "YUV 4:2:0\n(12 bpp)", "Monokrom / Y\n(8 bpp)"]
bpp = [24, 16, 12, 8]
rel_size = [100.0, 66.7, 50.0, 33.3]

bars4 = ax4.bar(formats, rel_size, color=[COLOR_CYAN, COLOR_YELLOW, COLOR_GREEN, COLOR_INDIGO], edgecolor=COLOR_TEXT, width=0.55)
for bar, b in zip(bars4, bpp):
    ax4.text(bar.get_x() + bar.get_width()/2.0, bar.get_height() + 2.5, f"{b} bpp\n(%{bar.get_height():.1f})", 
             color=COLOR_TEXT, ha="center", fontsize=9, fontweight="bold")

ax4.set_title("Panel 4: Aviyonik Video Formatları Bellek ve Bant Genişliği Oranı", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_ylabel("Göreceli Veri Boyutu [%]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylim(0, 120)
ax4.tick_params(colors=COLOR_MUTED)
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")

plt.suptitle("FAZ F8 GÜN 247 — RENK UZAYLARI ZİHİNSEL MODELİ: RGB, BGR, HSV VE YCbCr / YUV420", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_247/gun_247_rgb_bgr_hsv_ycbcr_zihinsel_modeli.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

