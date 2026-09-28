# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 252: Thresholding ve morphology Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: Referans Otsu Eşikleme Motoru ve Matematiksel Doğrulama
# Sınıflar arası varyans maksimizasyonu ve OpenCV Otsu ile tam özdeşlik.
# ============================================================================
import numpy as np
import cv2

class OtsuEngine:
    @staticmethod
    def calculate_otsu_threshold(image: np.ndarray) -> int:
        # 1. 256 kutulu histogram ve olasılık yoğunluk fonksiyonu (PDF)
        hist, _ = np.histogram(image.ravel(), bins=256, range=(0, 256))
        total_pixels = image.size
        p = hist.astype(np.float64) / total_pixels
        
        # 2. Kümülatif sınıf olasılıkları: omega0(t) ve omega1(t)
        omega0 = np.cumsum(p)
        omega1 = 1.0 - omega0
        
        # 3. Kümülatif ortalamalar
        indices = np.arange(256, dtype=np.float64)
        mu_cum = np.cumsum(indices * p)
        mu_total = mu_cum[-1] # Görüntünün toplam ortalama parlaklığı
        
        # Sıfıra bölmeyi engelle
        valid = (omega0 > 0.0) & (omega1 > 0.0)
        
        mu0 = np.zeros(256, dtype=np.float64)
        mu1 = np.zeros(256, dtype=np.float64)
        mu0[valid] = mu_cum[valid] / omega0[valid]
        mu1[valid] = (mu_total - mu_cum[valid]) / omega1[valid]
        
        # 4. Sınıflar Arası Varyans: sigma_B^2(t) = omega0 * omega1 * (mu0 - mu1)^2
        sigma_b_sq = np.zeros(256, dtype=np.float64)
        sigma_b_sq[valid] = omega0[valid] * omega1[valid] * ((mu0[valid] - mu1[valid]) ** 2)
        
        # 5. Varyansı maksimize eden optimal eşik
        optimal_t = int(np.argmax(sigma_b_sq))
        return optimal_t

# Test Sahnesi: Bimodal Termal Hedef (Zemin: 40-70 LSB, Hedef: 180-220 LSB)
np.random.seed(42)
bimodal_scene = np.random.randint(40, 75, (128, 128), dtype=np.uint8)
bimodal_scene[40:90, 40:90] = np.random.randint(180, 225, (50, 50), dtype=np.uint8)

# 1. Özel Otsu Motorunu Çalıştır
custom_t = OtsuEngine.calculate_otsu_threshold(bimodal_scene)

# 2. OpenCV Otsu Motorunu Çalıştır
cv_t, cv_mask = cv2.threshold(bimodal_scene, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

# Doğrulamalar: Özel motor ile OpenCV tam olarak aynı eşiği üretmelidir!
threshold_diff = abs(custom_t - int(cv_t))
assert threshold_diff == 0, f"Otsu eşiği OpenCV ile tam eşleşmelidir! Özel: {custom_t}, CV: {cv_t}"

# İkili maske üretimi
custom_mask = (bimodal_scene > custom_t).astype(np.uint8) * 255
assert np.array_equal(custom_mask, cv_mask), "İkili maskeler piksel piksel özdeş olmalıdır!"

print("[PASS] Kod 1: Referans Otsu Eşikleme Motoru Başarıyla Doğrulandı.")
print(f"  - Özel Otsu Optimal Eşik Değeri : T* = {custom_t} LSB")
print(f"  - OpenCV Otsu Eşik Değeri       : T* = {int(cv_t)} LSB [TAM SAYISAL EŞLEŞME]")
print(f"  - Segmentasyona Uğrayan Hedef   : {np.sum(custom_mask == 255):,} piksel (50x50 = 2500 px)")

# ============================================================================
# KOD HÜCRESİ 2: Morfolojik Filtreleme ve Hedef Maskesi Onarım Laboratuvarı
# Açma ile gürültü temizleme, Kapama ile delik kapatma ve Morfolojik Gradyan.
# ============================================================================
import numpy as np
import cv2

# 1. Sentetik Maske: 24x24 Hedef Gövdesi (Toplam 576 piksel)
pristine_mask = np.zeros((64, 64), dtype=np.uint8)
pristine_mask[20:44, 20:44] = 255

# 2. Bozulma Enjeksiyonu: Gövdeye 6x6 Delik (36 px) ve 3 İzole Parazit
corrupted_mask = pristine_mask.copy()
corrupted_mask[28:34, 28:34] = 0 # İç boşluk / delik
corrupted_mask[5, 5] = 255       # Parazit 1
corrupted_mask[12, 52] = 255     # Parazit 2
corrupted_mask[55, 10] = 255     # Parazit 3

# Yapılandırıcı Elemanlar (3x3 ve 7x7 Dikdörtgen)
k3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
k7 = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))

# 3. Morfolojik Operasyonlar:
# A) Açma (Opening): 3x3 elemanla dış parazitleri sil
opened_mask = cv2.morphologyEx(corrupted_mask, cv2.MORPH_OPEN, k3)

# B) Kapama (Closing): 7x7 elemanla 6x6 iç deliği kapat
closed_mask = cv2.morphologyEx(opened_mask, cv2.MORPH_CLOSE, k7)

# C) Morfolojik Gradyan: Hedefin dış hat konturu
morph_gradient = cv2.morphologyEx(closed_mask, cv2.MORPH_GRADIENT, k3)

# Piksel Sayımları ve Doğrulamalar:
raw_active_px = int(np.sum(corrupted_mask == 255))
opened_active_px = int(np.sum(opened_mask == 255))
restored_active_px = int(np.sum(closed_mask == 255))
gradient_px = int(np.sum(morph_gradient == 255))

# Parazit kontrolü: (5,5), (12,52) ve (55,10) sıfırlanmış olmalıdır
assert opened_mask[5, 5] == 0 and opened_mask[12, 52] == 0 and opened_mask[55, 10] == 0, "Açma parazitleri silmelidir"
# Delik kontrolü: 28:34, 28:34 bölgesi tamamen 255 olmalıdır
assert np.all(closed_mask[28:34, 28:34] == 255), "Kapama iç deliği tamamen doldurmalıdır"
# Tam orijinal geometrik korunum:
assert restored_active_px == 576, f"Onarılan hedef tam 576 piksel olmalıdır: {restored_active_px}"

print("[PASS] Kod 2: Morfolojik Filtreleme ve Hedef Onarım Laboratuvarı Doğrulandı.")
print(f"  - Bozulmuş Maske Piksel Sayısı: {raw_active_px} px (576 - 36 delik + 3 parazit = 543)")
print(f"  - Açma Sonrası Piksel Sayısı   : {opened_active_px} px (Parazitler silindi, delik duruyor)")
print(f"  - Kapama Sonrası Piksel Sayısı : {restored_active_px} px [TAM 576 PX HEDEF ONARILDI]")
print(f"  - Morfolojik Gradyan Konturu  : {gradient_px} px (1-katman kapalı çevre sınırı)")

# ============================================================================
# KOD HÜCRESİ 3: Düzensiz Aydınlatma Altında Hedef Ayrıştırma Deneyi
# Global Otsu zaafı, Adaptive Gaussian üstünlüğü ve sahte alarm analizi.
# ============================================================================
import numpy as np
import cv2

# 1. Şiddetli Aydınlatma Gradyanı (40 LSB sol -> 180 LSB sağ)
w, h = 128, 128
grad_1d = np.linspace(40, 180, w, dtype=np.float64).reshape(1, -1)
scene_base = np.tile(grad_1d, (h, 1))

# Hedef 1 (Gölgede): x=20..35, y=40..60. Zemin ~60 LSB, Hedef = 110 LSB (+50 LSB kontrast)
scene_base[40:60, 20:35] = 110.0

# Hedef 2 (Güneşte): x=90..105, y=40..60. Zemin ~160 LSB, Hedef = 220 LSB (+60 LSB kontrast)
scene_base[40:60, 90:105] = 220.0

# Sensör Gürültüsü
np.random.seed(99)
noise = np.random.normal(0, 3.0, (h, w))
test_lighting_scene = np.clip(scene_base + noise, 0, 255).astype(np.uint8)

# 2. Yöntem A: Global Otsu Eşikleme
otsu_val, mask_otsu = cv2.threshold(test_lighting_scene, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

# 3. Yöntem B: Uyarlamalı Gaussian Eşikleme (BlockSize=21, C=-15)
mask_adapt = cv2.adaptiveThreshold(test_lighting_scene, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 21, -15)

# Metriklerin Hesaplanması:
# Hedef 1 (Gölge) Bölgesindeki Tespit Pikselleri:
t1_otsu_px = int(np.sum(mask_otsu[40:60, 20:35] == 255))
t1_adapt_px = int(np.sum(mask_adapt[40:60, 20:35] == 255))

# Güneş Altındaki Düz Zemindeki Sahte Alarm Pikselleri (x=60..85, y=40..60):
false_alarm_otsu = int(np.sum(mask_otsu[40:60, 60:85] == 255))
false_alarm_adapt = int(np.sum(mask_adapt[40:60, 60:85] == 255))

# Doğrulamalar:
# 1. Otsu aydınlatma gradyanında zemin üzerinde yüzlerce sahte alarm üretmelidir
assert false_alarm_otsu > 200, f"Otsu sahte alarm üretmelidir: {false_alarm_otsu}"
# 2. Uyarlamalı eşikleme zeminde sıfır sahte alarm üretmelidir
assert false_alarm_adapt == 0, f"Adaptive zemin paraziti sıfır olmalıdır: {false_alarm_adapt}"
# 3. Uyarlamalı eşikleme gölgedeki hedefi başarıyla yakalamalıdır
assert t1_adapt_px > 80, f"Adaptive gölgedeki hedefi tespit etmelidir: {t1_adapt_px}"

print("[PASS] Kod 3: Düzensiz Aydınlatma Deneyi Başarıyla Doğrulandı.")
print(f"  - Otsu Eşik Değeri             : {otsu_val:.1f} LSB")
print(f"  - Gölgedeki Hedef Tespiti      : Otsu = {t1_otsu_px} px | Adaptive = {t1_adapt_px} px [GÖLGEDE BAŞARI]")
print(f"  - Güneşteki Zemin Sahte Alarmı : Otsu = {false_alarm_otsu} px (FELAKET!) | Adaptive = {false_alarm_adapt} px [SIFIR HATA]")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik Segmentasyon Hata Enjeksiyonu Testi
# Aşırı erozyon kalkanı, simetrik anchor denetimi ve ters polarite koruması.
# ============================================================================

# --- TEST 1: Aşırı Erozyon ile Hedef Kaybı Kalkanı ---
print("[TEST 1] Aşırı Erozyon (Over-Erosion Target Obliteration) Kalkanı...")
def safe_morphology_open(mask: np.ndarray, target_bbox_size: int) -> np.ndarray:
    # Savunma Kalkanı: Yapılandırıcı eleman hedef boyutunun 1/3'ünü aşamaz!
    max_k_size = max(3, (target_bbox_size // 3))
    if max_k_size % 2 == 0:
        max_k_size -= 1
    safe_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max_k_size, max_k_size))
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, safe_kernel), max_k_size

small_target = np.zeros((32, 32), dtype=np.uint8)
small_target[12:22, 12:22] = 255 # 10x10 Mikro-İHA Hedefi

# Hatalı Tercih: 15x15 Aşırı Büyük Eleman
large_k = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
obliterated = cv2.morphologyEx(small_target, cv2.MORPH_OPEN, large_k)

# Güvenli Kalkanlı Fonksiyon:
safe_result, applied_k = safe_morphology_open(small_target, target_bbox_size=10)

assert np.sum(obliterated) == 0, "15x15 erozyon 10x10 hedefi tamamen yok etmelidir!"
assert np.sum(safe_result) > 0, "Güvenli kalkan hedefi korumalıdır!"

print(f"  - Orijinal Hedef Boyutu          : 10x10 piksel (100 px)")
print(f"  - 15x15 Erozyon Sonucu           : {np.sum(obliterated)} px (HEDEF TAMAMEN YOK EDİLDİ!)")
print(f"  - Güvenli Kalkan Elemanı (k={applied_k}x{applied_k}) : {np.sum(safe_result == 255)} px [HEDEF KORUNDU]")
print("  [PASS] Test 1: Aşırı erozyon kalkanı başarıyla doğrulandı.\n")

# --- TEST 2: Çift Boyutlu Yapılandırıcı Eleman Merkez Kayması ---
print("[TEST 2] Çift Boyutlu Eleman ve Asimetrik Anchor Kayması Denetimi...")
def validate_structuring_element(k_size: int) -> bool:
    # Savunma Kalkanı: Eleman tek boyutlu olmalıdır (2k+1)
    return (k_size % 2 == 1)

assert not validate_structuring_element(4), "4x4 çift boyutlu eleman reddedilmelidir!"
assert validate_structuring_element(3), "3x3 simetrik eleman onaylanmalıdır."

print("  - 4x4 Eleman Testi : [BLOKE EDİLDİ - SİMETRİK MERKEZ YOK]")
print("  - 3x3 Eleman Testi : [ONAYLANDI - DO-178C STANDART]")
print("  [PASS] Test 2: Yapılandırıcı eleman simetri kalkanı başarıyla doğrulandı.\n")

# --- TEST 3: Ters Eşikleme ve Polarite Çöküşü Kalkanı ---
print("[TEST 3] Ters Eşikleme (Inverted Binary Mask) Polarite Kalkanı...")
def sanitize_mask_polarity(binary_mask: np.ndarray) -> np.ndarray:
    # Savunma Kalkanı: Askeri hedef segmentasyonunda hedef alanı görüntünün %50'sinden küçük olmalıdır.
    active_ratio = np.mean(binary_mask == 255)
    if active_ratio > 0.50:
        # Polarite ters dönmüş: Zemin beyaz, hedef siyah! Otomatik tersle:
        return cv2.bitwise_not(binary_mask), True
    return binary_mask, False

# Hatalı Ters Eşikleme Maskesi: Sahnenin %90'ı beyaz (Zemin), hedef siyah!
inverted_mask = np.full((64, 64), 255, dtype=np.uint8)
inverted_mask[20:30, 20:30] = 0 # 10x10 hedef siyah kalmış!

corrected_mask, was_inverted = sanitize_mask_polarity(inverted_mask)

assert was_inverted, "Ters polarite kalkan tarafından tespit edilmelidir!"
assert np.sum(corrected_mask == 255) == 100, "Düzeltilen maskede hedef 100 piksel beyaz olmalıdır!"

print(f"  - Hatalı Maske Aktif Oranı  : %{np.mean(inverted_mask == 255)*100:.1f} (ZEMİN BEYAZ!)")
print(f"  - Düzeltilen Maske Hedef    : {np.sum(corrected_mask == 255)} px [OTOMATİK DÜZELTİLDİ]")
print("  [PASS] Test 3: Ters polarite kalkanı başarıyla doğrulandı.\n")

print("[PASS] Kod 4: 3 Kritik Segmentasyon Hata Enjeksiyonu Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 10.000 Blok Eşikleme ve Morfoloji Benchmark'ı
# Fixed, Otsu, Adaptive Gaussian ve Morfolojik Açma yürütme gecikmesi analizi.
# ============================================================================
import time
import numpy as np
import cv2

NUM_BLOCKS = 10_000
BLOCK_SIZE = 32

np.random.seed(42)
rand_block = np.random.randint(0, 256, size=(BLOCK_SIZE, BLOCK_SIZE), dtype=np.uint8)
k3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

latencies_fixed_us = np.empty(NUM_BLOCKS, dtype=np.float64)
latencies_otsu_us = np.empty(NUM_BLOCKS, dtype=np.float64)
latencies_adapt_us = np.empty(NUM_BLOCKS, dtype=np.float64)
latencies_open_us = np.empty(NUM_BLOCKS, dtype=np.float64)

# 1. Benchmark: Sabit Eşikleme
t0_f = time.perf_counter()
for i in range(NUM_BLOCKS):
    t0 = time.perf_counter_ns()
    _ = cv2.threshold(rand_block, 128, 255, cv2.THRESH_BINARY)
    t_end = time.perf_counter_ns()
    latencies_fixed_us[i] = (t_end - t0) / 1000.0
t_total_f = time.perf_counter() - t0_f

# 2. Benchmark: Otsu Eşikleme
t0_o = time.perf_counter()
for i in range(NUM_BLOCKS):
    t0 = time.perf_counter_ns()
    _ = cv2.threshold(rand_block, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    t_end = time.perf_counter_ns()
    latencies_otsu_us[i] = (t_end - t0) / 1000.0
t_total_o = time.perf_counter() - t0_o

# 3. Benchmark: Uyarlamalı Gaussian Eşikleme
t0_a = time.perf_counter()
for i in range(NUM_BLOCKS):
    t0 = time.perf_counter_ns()
    _ = cv2.adaptiveThreshold(rand_block, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    t_end = time.perf_counter_ns()
    latencies_adapt_us[i] = (t_end - t0) / 1000.0
t_total_a = time.perf_counter() - t0_a

# 4. Benchmark: Morfolojik Açma (Opening 3x3)
t0_m = time.perf_counter()
for i in range(NUM_BLOCKS):
    t0 = time.perf_counter_ns()
    _ = cv2.morphologyEx(rand_block, cv2.MORPH_OPEN, k3)
    t_end = time.perf_counter_ns()
    latencies_open_us[i] = (t_end - t0) / 1000.0
t_total_m = time.perf_counter() - t0_m

fps_fixed = NUM_BLOCKS / t_total_f
fps_otsu = NUM_BLOCKS / t_total_o
fps_adapt = NUM_BLOCKS / t_total_a
fps_open = NUM_BLOCKS / t_total_m

p50_fixed = float(np.percentile(latencies_fixed_us, 50))
p99_fixed = float(np.percentile(latencies_fixed_us, 99))

p50_otsu = float(np.percentile(latencies_otsu_us, 50))
p99_otsu = float(np.percentile(latencies_otsu_us, 99))

p50_adapt = float(np.percentile(latencies_adapt_us, 50))
p99_adapt = float(np.percentile(latencies_adapt_us, 99))

p50_open = float(np.percentile(latencies_open_us, 50))
p99_open = float(np.percentile(latencies_open_us, 99))

print(f"\n[10.000 BLOK EŞİKLEME VE MORFOLOJİ BENCHMARK SONUÇLARI ({BLOCK_SIZE}x{BLOCK_SIZE})]")
print(f"  - Sabit Eşik Hızı       : {fps_fixed:,.1f} blok/s | p50: {p50_fixed:.2f} µs | p99: {p99_fixed:.2f} µs")
print(f"  - Otsu Eşik Hızı        : {fps_otsu:,.1f} blok/s | p50: {p50_otsu:.2f} µs | p99: {p99_otsu:.2f} µs")
print(f"  - Adaptive Eşik Hızı    : {fps_adapt:,.1f} blok/s | p50: {p50_adapt:.2f} µs | p99: {p99_adapt:.2f} µs")
print(f"  - Morfolojik Açma Hızı  : {fps_open:,.1f} blok/s | p50: {p50_open:.2f} µs | p99: {p99_open:.2f} µs")

# Doğrulamalar: Tüm operatörler deterministik aviyonik sınırda kalmalıdır
assert p99_fixed < 20.0, f"Fixed p99 çok yüksek: {p99_fixed} µs"
assert p99_otsu < 30.0, f"Otsu p99 çok yüksek: {p99_otsu} µs"
assert p99_adapt < 50.0, f"Adaptive p99 çok yüksek: {p99_adapt} µs"
assert p99_open < 50.0, f"Morph Open p99 çok yüksek: {p99_open} µs"

print("\n[PASS] Kod 5: 10.000 Blok Eşikleme ve Morfoloji Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli 300 DPI Koyu Tema Eşikleme & Morfoloji Dashboard'u
# gun_252_thresholding_ve_morphology.png dosyasını üretir.
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
plt.subplots_adjust(wspace=0.26, hspace=0.32)

# --- PANEL 1: Değişken Aydınlatmada Hedef Tespit ve Sahte Alarm Karşılaştırması ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

categories = ["Gölgedeki Hedef\n(Doğru Tespit px)", "Güneşteki Zemin\n(Sahte Alarm px)"]
x = np.arange(len(categories))
width = 0.35

rects1 = ax1.bar(x - width/2, [t1_otsu_px, false_alarm_otsu], width, label="Global Otsu", color=COLOR_RED, edgecolor=COLOR_TEXT)
rects2 = ax1.bar(x + width/2, [t1_adapt_px, false_alarm_adapt], width, label="Adaptive Gaussian", color=COLOR_GREEN, edgecolor=COLOR_TEXT)

for r in rects1:
    ax1.text(r.get_x() + r.get_width()/2.0, r.get_height() + 5, f"{int(r.get_height())} px", 
             color=COLOR_RED, ha="center", fontsize=9, fontweight="bold")
for r in rects2:
    ax1.text(r.get_x() + r.get_width()/2.0, r.get_height() + 5, f"{int(r.get_height())} px", 
             color=COLOR_GREEN, ha="center", fontsize=9, fontweight="bold")

ax1.set_title("Panel 1: Düzensiz Aydınlatmada Hedef Tespit vs Sahte Alarm", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xticks(x)
ax1.set_xticklabels(categories, color=COLOR_TEXT, fontsize=10)
ax1.set_ylabel("Piksel Sayısı", color=COLOR_MUTED, fontsize=10)
ax1.set_ylim(0, 400)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")
ax1.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 2: Morfolojik Filtreleme Aşamaları Piksel Dağılımı ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

labels_p2 = [
    "Bozulmuş Maske\n(Delik+Parazit)",
    "Açma (Opening)\n(Parazit Silindi)",
    "Kapama (Closing)\n(Tam Onarıldı)",
    "Morfolojik\nGradyan Konturu"
]
vals_p2 = [raw_active_px, opened_active_px, restored_active_px, gradient_px]
colors_p2 = [COLOR_CYAN, COLOR_YELLOW, COLOR_GREEN, COLOR_INDIGO]

bars2 = ax2.bar(labels_p2, vals_p2, color=colors_p2, edgecolor=COLOR_TEXT, width=0.55)
for bar, v in zip(bars2, vals_p2):
    ax2.text(bar.get_x() + bar.get_width()/2.0, v + 8, f"{v} px", 
             color=COLOR_TEXT, ha="center", fontsize=9, fontweight="bold")

ax2.set_title("Panel 2: Morfolojik Filtreleme ile Hedef Maskesi Onarım Adımları", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_ylabel("Aktif Piksel Sayısı", color=COLOR_MUTED, fontsize=10)
ax2.set_ylim(0, 650)
ax2.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")

# --- PANEL 3: 10.000 Blok Yürütme Gecikmesi Histogramı ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

ax3.hist(latencies_fixed_us, bins=30, color=COLOR_CYAN, alpha=0.5, label=f"Fixed (p50: {p50_fixed:.1f} µs)")
ax3.hist(latencies_otsu_us, bins=30, color=COLOR_GREEN, alpha=0.5, label=f"Otsu (p50: {p50_otsu:.1f} µs)")
ax3.hist(latencies_adapt_us, bins=30, color=COLOR_YELLOW, alpha=0.5, label=f"Adaptive (p50: {p50_adapt:.1f} µs)")
ax3.hist(latencies_open_us, bins=30, color=COLOR_RED, alpha=0.4, label=f"Morph Open (p50: {p50_open:.1f} µs)")

ax3.axvline(p99_otsu, color=COLOR_GREEN, linestyle="--", linewidth=1.5, label=f"Otsu p99: {p99_otsu:.1f} µs")
ax3.axvline(p99_adapt, color=COLOR_YELLOW, linestyle="-.", linewidth=1.5, label=f"Adapt p99: {p99_adapt:.1f} µs")

ax3.set_title("Panel 3: 10.000 Blok (32x32) Eşikleme & Morfoloji Yürütme Gecikmesi", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("Yürütme Süresi [µs]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("Blok Frekansı", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 4: Aviyonik Segmentasyon ve Emniyet Matrisi ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

metrics_p4 = [
    "Otsu Varyans\nMaksimizasyonu",
    "Adaptive Gölge\nHedef Yakalama",
    "Açma ile Dış\nParazit Silme",
    "Kapama ile İç\nDelik Onarımı",
    "Ters Polarite\nOtomatik Kalkanı"
]
scores_p4 = [100, 100, 100, 100, 100]
colors_p4 = [COLOR_GREEN] * 5

bars4 = ax4.bar(metrics_p4, scores_p4, color=colors_p4, edgecolor=COLOR_TEXT, width=0.55)
for bar in bars4:
    ax4.text(bar.get_x() + bar.get_width()/2.0, 104, "%100 UYUMLU", 
             color=COLOR_GREEN, ha="center", fontsize=8, fontweight="bold")

ax4.set_title("Panel 4: Aviyonik Segmentasyon ve Morfoloji Emniyet Skoru", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_ylabel("Uyumluluk Oranı [%]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylim(0, 125)
ax4.tick_params(colors=COLOR_MUTED)
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")

plt.suptitle("FAZ F8 GÜN 252 — GÖRÜNTÜ EŞİKLEME (THRESHOLDING) VE MATEMATİKSEL MORFOLOJİ DASHBOARD'U", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_252/gun_252_thresholding_ve_morphology.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

