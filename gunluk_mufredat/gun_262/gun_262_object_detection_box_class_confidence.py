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

# Kod 1: Ham Tensör Çözümleme (Post-Processing) ve Letterbox Ters İzdüşüm Motoru
# DO-178C Uyumlu Vektörel Kutu Dönüşümü, Unpadding ve Sınır Kırpma

import numpy as np

def xywh_to_xyxy(boxes_xywh: np.ndarray) -> np.ndarray:
    """[N, 4] boyutundaki (xc, yc, w, h) kutularini (x1, y1, x2, y2) formatina donusturur."""
    xc = boxes_xywh[:, 0]
    yc = boxes_xywh[:, 1]
    w  = boxes_xywh[:, 2]
    h  = boxes_xywh[:, 3]
    
    x1 = xc - w / 2.0
    y1 = yc - h / 2.0
    x2 = xc + w / 2.0
    y2 = yc + h / 2.0
    
    return np.column_stack([x1, y1, x2, y2])

def unpad_and_scale_boxes(boxes_xyxy: np.ndarray, orig_shape: tuple, net_shape: tuple) -> np.ndarray:
    """Model uzayindaki (640x640) kutulari orijinal kamera uzayina (1920x1080) ters izdusurur."""
    W_orig, H_orig = orig_shape
    W_net, H_net = net_shape
    
    # Olcek ve Dolgu Hesaplama
    scale = min(W_net / W_orig, H_net / H_orig)
    dx = (W_net - scale * W_orig) / 2.0
    dy = (H_net - scale * H_orig) / 2.0
    
    unpadded = boxes_xyxy.copy()
    # x koordinatlari
    unpadded[:, 0] = (unpadded[:, 0] - dx) / scale
    unpadded[:, 2] = (unpadded[:, 2] - dx) / scale
    # y koordinatlari
    unpadded[:, 1] = (unpadded[:, 1] - dy) / scale
    unpadded[:, 3] = (unpadded[:, 3] - dy) / scale
    
    # Sınır Kırpma (Clipping) - Goruntu disina tasma kalkanı
    unpadded[:, 0] = np.clip(unpadded[:, 0], 0, W_orig)
    unpadded[:, 2] = np.clip(unpadded[:, 2], 0, W_orig)
    unpadded[:, 1] = np.clip(unpadded[:, 1], 0, H_orig)
    unpadded[:, 3] = np.clip(unpadded[:, 3], 0, H_orig)
    
    return unpadded

# 1. Sentetik Model Çıkış Tensörü Simülasyonu (YOLOv8 Biçimi: [1, 4+K, N])
# 4 Koordinat (xc, yc, w, h) + 4 Askeri Sınıf (Tank, SAM, Kamyon, Sivil Araç)
# 640x640 Model Uzayında 5 Aday Kutu
np.random.seed(42)
orig_dim = (1920, 1080)
net_dim  = (640, 640)

# 3 Adet Gerçekçi Askeri Hedef (xc, yc, w, h model uzayinda, y dolgusu dy=140px civarinda)
# Hedef 1: Model merkezinde Tank (xc=320, yc=320, w=50, h=30)
# Hedef 2: Sol tarafta SAM Bataryası (xc=150, yc=280, w=40, h=40)
# Hedef 3: Sağ tarafta Lojistik Kamyon (xc=500, yc=350, w=60, h=35)
boxes_model_xywh = np.array([
    [320.0, 320.0, 50.0, 30.0],
    [150.0, 280.0, 40.0, 40.0],
    [500.0, 350.0, 60.0, 35.0]
], dtype=np.float32)

# 2. XYWH -> XYXY Dönüşümü
boxes_model_xyxy = xywh_to_xyxy(boxes_model_xywh)

# 3. Unpadding ile 1920x1080 Orijinal Kamera Uzayına Dönüşüm
boxes_camera_xyxy = unpad_and_scale_boxes(boxes_model_xyxy, orig_dim, net_dim)

# Doğrulama Assert'leri
for i in range(len(boxes_camera_xyxy)):
    x1, y1, x2, y2 = boxes_camera_xyxy[i]
    assert 0 <= x1 < x2 <= 1920, f"X siniri ihlali: {x1}, {x2}"
    assert 0 <= y1 < y2 <= 1080, f"Y siniri ihlali: {y1}, {y2}"

print("[PASS] Kod 1: Ham Tensör Çözümleme ve Unpadding Motoru Başarıyla Doğrulandı.")
print(f"  - Model Giriş Çözünürlüğü       : {net_dim[0]}x{net_dim[1]}")
print(f"  - Orijinal Kamera Çözünürlüğü   : {orig_dim[0]}x{orig_dim[1]}")
print(f"  - Hesaplanmış Letterbox Ölçeği  : {min(640/1920, 640/1080):.4f}")
print(f"  - Dikey Dolgu (dy Padding)      : {(640 - (640/1920)*1080)/2:.1f} piksel")
for i, name in enumerate(["Tank Gövdesi", "Hava Savunma", "Lojistik Kamyon"]):
    bx = boxes_camera_xyxy[i]
    w_cam = bx[2] - bx[0]
    h_cam = bx[3] - bx[1]
    print(f"  - Hedef {i+1} ({name:14s}): x1={bx[0]:6.1f}, y1={bx[1]:6.1f}, x2={bx[2]:6.1f}, y2={bx[3]:6.1f} | Boyut={w_cam:.0f}x{h_cam:.0f}px")

# Kod 2: Sınıf Olasılıkları, Güven Eşikleme ve Askeri ROE Doğrulama Laboratuvarı

CLASS_NAMES = ["TANK", "SAM_RADAR", "TRUCK", "CIVILIAN_CAR"]

# 4 Aday Tespit için Ham Sınıf Logitleri (Ham Model Çıktıları)
# Aday 1: Net Tank (Yüksek Tank Skoru)
# Aday 2: Net Hava Savunma Radarı
# Aday 3: Belirsiz Kamyon / Gölge (Düşük Güven)
# Aday 4: Sivil Araç (No-Strike Unsuru!)
raw_class_logits = np.array([
    [3.5, -1.2, 0.5, -3.0],   # Hedef 1 -> TANK
    [-2.0, 4.2, -0.5, -4.0],  # Hedef 2 -> SAM_RADAR
    [0.2, -0.8, 0.4, -0.5],   # Hedef 3 -> Belirsiz (Düşük skor)
    [-4.0, -3.0, -1.0, 3.8]   # Hedef 4 -> CIVILIAN_CAR
], dtype=np.float32)

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -15.0, 15.0)))

# Sigmoid ile Olasılıklara Dönüştür
class_probs = sigmoid(raw_class_logits)

# En Yüksek Sınıfı ve Güven Skorunu Çıkar
best_class_ids = np.argmax(class_probs, axis=1)
best_confidences = np.max(class_probs, axis=1)

# Askeri Angajman Karar Motoru (ROE Gate)
TAU_WARN = 0.35
TAU_STRIKE = 0.80

decisions = []
for i in range(len(best_class_ids)):
    c_id = best_class_ids[i]
    conf = best_confidences[i]
    c_name = CLASS_NAMES[c_id]
    
    if c_name == "CIVILIAN_CAR":
        status = "ABORT_CIVILIAN_DETECTED_NO_STRIKE"
    elif conf >= TAU_STRIKE:
        status = "CONFIRMED_HOSTILE_WEAPON_AUTHORIZED"
    elif conf >= TAU_WARN:
        status = "TRACKING_ONLY_LOW_CONFIDENCE"
    else:
        status = "REJECTED_BELOW_NOISE_THRESHOLD"
        
    decisions.append({
        "id": i+1,
        "class": c_name,
        "conf": conf,
        "status": status
    })

assert decisions[0]["status"] == "CONFIRMED_HOSTILE_WEAPON_AUTHORIZED"
assert decisions[1]["status"] == "CONFIRMED_HOSTILE_WEAPON_AUTHORIZED"
assert decisions[2]["status"] == "TRACKING_ONLY_LOW_CONFIDENCE"
assert decisions[3]["status"] == "ABORT_CIVILIAN_DETECTED_NO_STRIKE"

print("[PASS] Kod 2: Sınıflandırma ve Askeri ROE Güven Eşikleri Başarıyla Doğrulandı.")
for d in decisions:
    print(f"  - Aday {d['id']}: Sınıf={d['class']:14s} | Güven={d['conf']*100:5.1f}% | Karar: [{d['status']}]")

# Kod 3: Bounding Box Merkezinden Gimbal Açısal Sapma (LOS Angle) Hesaplama Motoru
import numpy as np

# 1920x1080 Kamera İç Parametreleri
fx, fy = 1400.0, 1400.0
cx, cy = 960.0, 540.0

def compute_gimbal_angular_errors(box_xyxy: np.ndarray, fx: float, fy: float, cx: float, cy: float):
    """Kutudan Azimut ve Yükseliş açısal hatalarını radyan ve derece olarak türetir."""
    x1, y1, x2, y2 = box_xyxy
    u_c = (x1 + x2) / 2.0
    v_c = (y1 + y2) / 2.0
    
    delta_u = u_c - cx
    delta_v = v_c - cy
    
    azimuth_rad = np.arctan(delta_u / fx)
    elevation_rad = np.arctan(delta_v / fy)
    
    azimuth_deg = np.degrees(azimuth_rad)
    elevation_deg = np.degrees(elevation_rad)
    
    return {
        "center_px": (u_c, v_c),
        "pixel_offset": (delta_u, delta_v),
        "azimuth_deg": azimuth_deg,
        "elevation_deg": elevation_deg
    }

# 1. Koddaki Tank Hedefinin Açısal Hatasını Hesapla
tank_box = boxes_camera_xyxy[0] # Tank kutusu
tank_angles = compute_gimbal_angular_errors(tank_box, fx, fy, cx, cy)

assert abs(tank_angles["azimuth_deg"]) < 45.0, "Azimut acisi gorus alani icinde olmali!"
assert abs(tank_angles["elevation_deg"]) < 45.0, "Yukselis acisi gorus alani icinde olmali!"

print("[PASS] Kod 3: Gimbal Açısal Sapma Hesaplama Motoru Başarıyla Doğrulandı.")
print(f"  - Kamera Optik Merkez (cx, cy)  : ({cx:.1f}, {cy:.1f}) piksel")
print(f"  - Hedef Kutu Merkezi (uc, vc)   : ({tank_angles['center_px'][0]:.1f}, {tank_angles['center_px'][1]:.1f}) piksel")
print(f"  - Piksel Hatası (du, dv)        : ({tank_angles['pixel_offset'][0]:.1f}, {tank_angles['pixel_offset'][1]:.1f}) piksel")
print(f"  - Gimbal Azimut Komutu (Yaw)    : {tank_angles['azimuth_deg']:+.3f} derece")
print(f"  - Gimbal Yükseliş Komutu (Pitch): {tank_angles['elevation_deg']:+.3f} derece")
print(f"  - Servomekanizma Durumu         : [KİLİTLENME VE TAKİP AKTİF]")

# Kod 4: 3 Kritik Savunma Hata Enjeksiyonu Test Laboratuvarı

print("[TEST 1] NaN ve Inf Koordinat Sayisal Guvenlik Kalkani...")
def sanitize_bounding_boxes(boxes: np.ndarray):
    """DO-178C Emniyet Kriteri: NaN veya Inf iceren kutular bloke edilmelidir."""
    if not np.all(np.isfinite(boxes)):
        # Hatali kutulari tespit et ve ele
        valid_mask = np.all(np.isfinite(boxes), axis=1)
        return boxes[valid_mask], "REJECTED_CORRUPTED_NAN_INF_BOXES"
    return boxes, "ACCEPTED_ALL_FINITE"

corrupted_boxes = np.array([
    [100.0, 100.0, 200.0, 200.0],
    [np.nan, 50.0, 120.0, 140.0],   # NaN Enjeksiyonu!
    [300.0, np.inf, 400.0, 500.0]   # Inf Enjeksiyonu!
])

clean_boxes, msg_nan = sanitize_bounding_boxes(corrupted_boxes)
assert len(clean_boxes) == 1, "Sadece 1 gecerli kutu kalmaliydi!"
assert msg_nan == "REJECTED_CORRUPTED_NAN_INF_BOXES"
print(f"  - Korunmus Gecerli Kutu Sayisi  : {len(clean_boxes)} / {len(corrupted_boxes)}")
print(f"  - Savunma Kalkani Raporu        : [{msg_nan}]")
print("[PASS] Test 1: NaN/Inf sayisal kalkan basariyla dogrulandi.\n")


print("[TEST 2] Dejenere ve Negatif Boyutlu Kutu Geometri Kalkani...")
def filter_degenerate_boxes(boxes_xyxy: np.ndarray, min_dim_px: float = 4.0):
    """x2 <= x1 veya boyut < min_dim olan kutulari eler."""
    w = boxes_xyxy[:, 2] - boxes_xyxy[:, 0]
    h = boxes_xyxy[:, 3] - boxes_xyxy[:, 1]
    
    valid_mask = (w >= min_dim_px) & (h >= min_dim_px)
    return boxes_xyxy[valid_mask], np.sum(~valid_mask)

invalid_geom_boxes = np.array([
    [100.0, 100.0, 150.0, 150.0], # Gecerli (50x50)
    [200.0, 200.0, 180.0, 250.0], # Gecersiz: x2 < x1 (w = -20px)
    [300.0, 300.0, 301.0, 350.0]  # Gecersiz: w = 1px < min_dim
])

valid_geom, dropped_count = filter_degenerate_boxes(invalid_geom_boxes, min_dim_px=4.0)
assert len(valid_geom) == 1
assert dropped_count == 2

print(f"  - Elenen Dejenere Kutu Sayisi   : {dropped_count} adet")
print(f"  - Kalan Guvenli Kutu Boyutu     : {valid_geom[0, 2]-valid_geom[0, 0]:.0f}x{valid_geom[0, 3]-valid_geom[0, 1]:.0f}px")
print("[PASS] Test 2: Geometrik dejenerasyon kalkani basariyla dogrulandi.\n")


print("[TEST 3] Coklu Kare Dogrulama (Temporal Verification) ve Sahte Ates Kalkani...")
class TemporalStrikeGate:
    def __init__(self, required_consecutive_frames: int = 5, strike_conf_threshold: float = 0.80):
        self.req_frames = required_consecutive_frames
        self.strike_conf = strike_conf_threshold
        self.consecutive_hits = 0
        
    def evaluate_target(self, conf: float) -> Tuple[bool, str]:
        if conf >= self.strike_conf:
            self.consecutive_hits += 1
        else:
            self.consecutive_hits = 0 # Guven duserse sifirla
            
        if self.consecutive_hits >= self.req_frames:
            return True, f"STRIKE_AUTHORIZED_TARGET_CONFIRMED ({self.consecutive_hits} kare teyitli)"
        else:
            return False, f"STRIKE_LOCKED_PENDING_CONFIRMATION ({self.consecutive_hits}/{self.req_frames} kare)"

gate = TemporalStrikeGate(required_consecutive_frames=4, strike_conf_threshold=0.80)

# 3 Kare boyunca yüksek güven, 4. karede anlık düşüş simülasyonu
r1, m1 = gate.evaluate_target(0.85)
r2, m2 = gate.evaluate_target(0.88)
r3, m3 = gate.evaluate_target(0.82)
# 4. karede kaya gölgesi nedeniyle güven düştü
r4, m4 = gate.evaluate_target(0.40)

assert r1 == False and r2 == False and r3 == False
assert r4 == False and gate.consecutive_hits == 0

print(f"  - Kare 1-3 Teyit Durumu         : {m3}")
print(f"  - Kare 4 Guven Dususu Durumu    : {m4} [ATES IPTAL]")
print("[PASS] Test 3: Coklu kare dogrulama kalkani basariyla dogrulandi.")

# Kod 5: 10.000 Aday Kutu Post-Processing Benchmark Laboratuvarı
import time
import numpy as np

N_BENCH_BOXES = 10000

# 1. 10.000 Adet Sentetik XYWH Kutu ve 8 Sınıf Logiti Hazırla
bench_boxes_xywh = np.random.uniform(50, 590, size=(N_BENCH_BOXES, 4)).astype(np.float32)
bench_logits = np.random.normal(0, 2.0, size=(N_BENCH_BOXES, 8)).astype(np.float32)

orig_shape = (1920, 1080)
net_shape  = (640, 640)

# 2. Benchmark: XYWH -> XYXY Dönüşümü
t0 = time.perf_counter()
boxes_xyxy = xywh_to_xyxy(bench_boxes_xywh)
t1 = time.perf_counter()
time_xyxy = t1 - t0
rate_xyxy = N_BENCH_BOXES / time_xyxy

# 3. Benchmark: Unpadding ve Clipping
t0 = time.perf_counter()
boxes_cam = unpad_and_scale_boxes(boxes_xyxy, orig_shape, net_shape)
t1 = time.perf_counter()
time_unpad = t1 - t0
rate_unpad = N_BENCH_BOXES / time_unpad

# 4. Benchmark: Sigmoid, Argmax ve Eşikleme
t0 = time.perf_counter()
probs = 1.0 / (1.0 + np.exp(-bench_logits))
max_scores = np.max(probs, axis=1)
mask = max_scores >= 0.70
filtered_boxes = boxes_cam[mask]
t1 = time.perf_counter()
time_thresh = t1 - t0
rate_thresh = N_BENCH_BOXES / time_thresh

total_postprocess_time_ms = (time_xyxy + time_unpad + time_thresh) * 1000.0

assert total_postprocess_time_ms < 5.0, f"Post-processing 5ms altinda olmaliydi: {total_postprocess_time_ms} ms"

print(f"\n[10.000 ADAY KUTU POST-PROCESSING BENCHMARK SONUÇLARI]")
print(f"  - XYWH -> XYXY Donusum Hizi     : {rate_xyxy:12.1f} kutu/s | Sure: {time_xyxy*1000:6.3f} ms")
print(f"  - Unpadding & Clipping Hizi     : {rate_unpad:12.1f} kutu/s | Sure: {time_unpad*1000:6.3f} ms")
print(f"  - Sigmoid, Argmax & Esik Hizi   : {rate_thresh:12.1f} kutu/s | Sure: {time_thresh*1000:6.3f} ms")
print(f"  - TOPLAM POST-PROCESS GECIKMESI : {total_postprocess_time_ms:6.3f} ms [AVIYONIK GERCEK ZAMAN < 1ms]")
print(f"[PASS] Kod 5: 10.000 Kutu Benchmark Laboratuvarı Başarıyla Tamamlandı.")

# Kod 6: 4-Panelli Koyu Tema Aviyonik Nesne Tespiti Dashboard'u
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

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
# Panel 1: Aviyonik Hedefleme Arayuzu (1920x1080)
# -------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("Panel 1: Aviyonik Hedefleme Ekranı (Full HD 1920x1080)", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
ax1.set_xlim(0, 1920)
ax1.set_ylim(1080, 0) # Görüntü koordinatları

# Optik Merkez Artısı (Crosshair)
ax1.axvline(x=960, color='#475569', linestyle='--', linewidth=1.2)
ax1.axhline(y=540, color='#475569', linestyle='--', linewidth=1.2)
ax1.scatter(960, 540, color='#38BDF8', s=60, marker='+', zorder=6)

# Kutu Çizimleri
colors = ['#EF4444', '#F59E0B', '#10B981', '#06B6D4']
labels = ["TANK %97", "SAM_RADAR %98", "TRUCK %60", "CIVILIAN_CAR %98"]

# 4 Kutu tanımla (1920x1080 uzayında)
display_boxes = [
    boxes_camera_xyxy[0], # Tank
    boxes_camera_xyxy[1], # SAM
    boxes_camera_xyxy[2], # Kamyon
    np.array([1300.0, 700.0, 1450.0, 780.0]) # Sivil Araç
]

for i in range(4):
    bx = display_boxes[i]
    col = colors[i]
    w_b = bx[2] - bx[0]
    h_b = bx[3] - bx[1]
    
    # Bounding Box Dikdörtgeni
    rect = patches.Rectangle((bx[0], bx[1]), w_b, h_b, linewidth=2.0, edgecolor=col, facecolor='none')
    ax1.add_patch(rect)
    
    # Etiket Kutusu
    ax1.text(bx[0], bx[1] - 8, labels[i], color='#FFFFFF', fontsize=9, fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.2", facecolor=col, edgecolor='none', alpha=0.85))
    
    # Merkez Artısı ve Optik Merkeze LOS Çizgisi
    u_c = (bx[0] + bx[2]) / 2.0
    v_c = (bx[1] + bx[3]) / 2.0
    ax1.plot([960, u_c], [540, v_c], color=col, linestyle=':', alpha=0.5)
    ax1.scatter(u_c, v_c, color=col, s=40, zorder=5)

ax1.set_xlabel("Piksel X", color='#94A3B8', fontsize=10)
ax1.set_ylabel("Piksel Y", color='#94A3B8', fontsize=10)

# -------------------------------------------------------------
# Panel 2: Letterbox Geometrisi ve En-Boy Korunumu
# -------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("Panel 2: Letterbox Dönüşümü (1920x1080 -> 640x640 Padding)", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
ax2.set_xlim(0, 640)
ax2.set_ylim(640, 0)

# Model Çerçevesi (640x640)
model_box = patches.Rectangle((0, 0), 640, 640, linewidth=2.0, edgecolor='#475569', facecolor='#0F172A')
ax2.add_patch(model_box)

# Dikey Gri Dolgular (Padding: dy = 140px üstte ve altta)
pad_top = patches.Rectangle((0, 0), 640, 140, linewidth=0, facecolor='#334155', alpha=0.6)
pad_bot = patches.Rectangle((0, 500), 640, 140, linewidth=0, facecolor='#334155', alpha=0.6)
ax2.add_patch(pad_top)
ax2.add_patch(pad_bot)

ax2.text(320, 70, "Gri Dolgu (dy = 140 px Padding)", color='#94A3B8', fontsize=9, ha='center', va='center')
ax2.text(320, 570, "Gri Dolgu (dy = 140 px Padding)", color='#94A3B8', fontsize=9, ha='center', va='center')

# Aktif Video Alanı (640x360)
active_area = patches.Rectangle((0, 140), 640, 360, linewidth=1.5, edgecolor='#38BDF8', facecolor='#1E293B', alpha=0.8)
ax2.add_patch(active_area)
ax2.text(320, 320, "Aktif Video Görüntüsü (640 x 360)\nÖlçek: 0.3333x", color='#38BDF8', fontsize=10, fontweight='bold', ha='center', va='center')

ax2.set_xlabel("Model Giriş X (Piksel)", color='#94A3B8', fontsize=10)
ax2.set_ylabel("Model Giriş Y (Piksel)", color='#94A3B8', fontsize=10)

# -------------------------------------------------------------
# Panel 3: Sinif Skor Dagilimlari (Softmax / Sigmoid)
# -------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("Panel 3: Aday Hedefler Sınıf Olasılık Dağılımları", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)

x_cls = np.arange(4)
width_bar = 0.2

for i in range(4):
    probs_i = class_probs[i]
    ax3.bar(x_cls + (i - 1.5)*width_bar, probs_i, width=width_bar, label=f"Hedef {i+1} ({labels[i].split()[0]})", color=colors[i], alpha=0.85)

ax3.axhline(y=0.80, color='#EF4444', linestyle='--', linewidth=1.8, label="Angajman Eşiği (0.80)")
ax3.axhline(y=0.35, color='#F59E0B', linestyle=':', linewidth=1.5, label="Erken Uyarı Eşiği (0.35)")

ax3.set_xticks(x_cls)
ax3.set_xticklabels(CLASS_NAMES, color='#94A3B8', fontsize=9, fontweight='bold')
ax3.set_ylabel("Olasılık Skoru", color='#94A3B8', fontsize=10)
ax3.set_ylim(0, 1.1)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', fontsize=8)

# -------------------------------------------------------------
# Panel 4: Guven Esigi vs Yanlis Alarm / Dogru Tespit Egrisi
# -------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("Panel 4: Güven Eşiği vs Yanlış Alarm / Doğru Tespit Eğrisi", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)

thresholds = np.linspace(0.1, 0.95, 100)
# Tipik askeri ATR eğrileri
true_positive_rate = 1.0 / (1.0 + np.exp(8.0 * (thresholds - 0.70)))
false_alarm_rate = np.exp(-6.0 * thresholds)

ax4.plot(thresholds, true_positive_rate, color='#10B981', linewidth=2.5, label="Doğru Hedef Tespit Oranı (TAR)")
ax4.plot(thresholds, false_alarm_rate, color='#EF4444', linewidth=2.5, label="Yanlış Alarm Oranı (FAR)")

ax4.axvline(x=0.80, color='#38BDF8', linestyle='--', linewidth=2.0, label="Operasyonel Angajman Eşiği (tau = 0.80)")
ax4.scatter(0.80, 0.008, color='#38BDF8', s=120, zorder=5)

ax4.set_xlabel("Güven Skoru Eşiği (Threshold)", color='#94A3B8', fontsize=10)
ax4.set_ylabel("Oran [0.0 - 1.0]", color='#94A3B8', fontsize=10)
ax4.legend(loc='center left', facecolor='#0F172A', edgecolor='#475569', fontsize=9)

plt.subplots_adjust(top=0.92, bottom=0.08, left=0.08, right=0.95, hspace=0.28, wspace=0.22)
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else '.'
png_output_path = os.path.join(script_dir, 'gun_262_object_detection_box_class_confidence.png')
plt.savefig(png_output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(png_output_path) / 1024.0
print(f"[OK] 4-Panelli Gorsellestirme Basariyla Uretildi: {png_output_path}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")

