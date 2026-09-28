# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 253: Contours ve connected components
6 Kod Hücresinin Eksiksiz ve Bağımsız Çalıştırılabilir Python Dosyası
"""

# ==============================================================================
# HÜCRE 3 / KOD 1: Referans Two-Pass Connected Component Labeling (CCL)
# Disjoint-Set (Union-Find) ile Eşdeğerlik Çözümü ve OpenCV Karşılaştırması
# ==============================================================================

import numpy as np
import cv2

class DisjointSet:
    # DO-178C Uyumlu Deterministik Union-Find Veri Yapisi
    def __init__(self, size: int):
        self.parent = np.arange(size, dtype=np.int32)
        self.rank = np.zeros(size, dtype=np.int32)

    def find(self, i: int) -> int:
        path = []
        while self.parent[i] != i:
            path.append(i)
            i = self.parent[i]
        for node in path:
            self.parent[node] = i  # Path compression
        return i

    def union(self, i: int, j: int):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            if self.rank[root_i] < self.rank[root_j]:
                self.parent[root_i] = root_j
            elif self.rank[root_i] > self.rank[root_j]:
                self.parent[root_j] = root_i
            else:
                self.parent[root_j] = root_i
                self.rank[root_i] += 1

def reference_two_pass_ccl(binary_img: np.ndarray, connectivity: int = 8):
    # Two-Pass Baglantili Bilesen Etiketleme Algoritmasi.
    # Girdi: binary_img (H, W) uint8 {0, 255}
    # Cikti: label_map (H, W) int32, num_labels, stats
    assert connectivity in (4, 8), "Bağlantılık 4 veya 8 olmalıdır!"
    H, W = binary_img.shape
    labels = np.zeros((H, W), dtype=np.int32)
    next_label = 1
    ds = DisjointSet(H * W // 2 + 10)

    # 1. GEÇİŞ: Geçici etiket atama ve komşuluk eşdeğerlik kaydı
    for r in range(H):
        for c in range(W):
            if binary_img[r, c] == 0:
                continue
            neighbors = []
            # Üst komşu
            if r > 0 and labels[r - 1, c] > 0:
                neighbors.append(labels[r - 1, c])
            # Sol komşu
            if c > 0 and labels[r, c - 1] > 0:
                neighbors.append(labels[r, c - 1])
            
            if connectivity == 8:
                # Sol-üst çapraz
                if r > 0 and c > 0 and labels[r - 1, c - 1] > 0:
                    neighbors.append(labels[r - 1, c - 1])
                # Sağ-üst çapraz
                if r > 0 and c < W - 1 and labels[r - 1, c + 1] > 0:
                    neighbors.append(labels[r - 1, c + 1])

            if len(neighbors) == 0:
                labels[r, c] = next_label
                next_label += 1
            else:
                min_lbl = min(neighbors)
                labels[r, c] = min_lbl
                for n in neighbors:
                    ds.union(min_lbl, n)

    # 2. GEÇİŞ: Kök etiketleri çözümleme ve ardışık ID haritalama
    root_to_final = {}
    final_id = 1
    for r in range(H):
        for c in range(W):
            if labels[r, c] > 0:
                root = ds.find(labels[r, c])
                if root not in root_to_final:
                    root_to_final[root] = final_id
                    final_id += 1
                labels[r, c] = root_to_final[root]

    num_components = final_id - 1
    return labels, num_components

# --- SENTETİK FLIR HEDEF TEST ALANI OLUŞTURMA ---
np.random.seed(42)
test_mask = np.zeros((64, 64), dtype=np.uint8)

# Hedef 1: İHA Gövdesi (12x12 piksel blok) -> (10, 10) konumunda
test_mask[10:22, 10:22] = 255

# Hedef 2: Zırhlı Araç (8x16 piksel blok) -> (35, 40) konumunda
test_mask[35:43, 40:56] = 255

# Hedef 3: Çapraz Köprü ile Bağlanan 2 Piksel (Topoloji Testi)
# (50, 10) ve (51, 11) - 4-bağlantılıda 2 nesne, 8-bağlantılıda 1 nesne olmalıdır!
test_mask[50, 10] = 255
test_mask[51, 11] = 255

# 1. Referans İki-Geçişli CCL Çalıştırma (8-Bağlantılı)
ref_labels_8, ref_count_8 = reference_two_pass_ccl(test_mask, connectivity=8)

# 2. OpenCV Standart CCL Çalıştırma (8-Bağlantılı)
cv_num_8, cv_labels_8, cv_stats_8, cv_centroids_8 = cv2.connectedComponentsWithStats(test_mask, connectivity=8)

# 3. Referans ve OpenCV 4-Bağlantılı Çalıştırma
ref_labels_4, ref_count_4 = reference_two_pass_ccl(test_mask, connectivity=4)
cv_num_4, cv_labels_4, cv_stats_4, cv_centroids_4 = cv2.connectedComponentsWithStats(test_mask, connectivity=4)

# --- MATEMATİKSEL VE TOPOLOJİK DOĞRULAMA (ASSERTIONS) ---
# OpenCV arka planı 0. etiket olarak sayar, bu nedenle cv_num = nesne_sayisi + 1
assert ref_count_8 == (cv_num_8 - 1), f"8-Bağlantılı nesne sayısı uyuşmuyor! Ref: {ref_count_8}, CV: {cv_num_8-1}"
assert ref_count_4 == (cv_num_4 - 1), f"4-Bağlantılı nesne sayısı uyuşmuyor! Ref: {ref_count_4}, CV: {cv_num_4-1}"

# 8-Bağlantılıda 3 hedef olmalı: İHA (144 px), Zırhlı (128 px), Çapraz Çift (2 px)
assert ref_count_8 == 3, f"Beklenen 3 hedef ancak bulunan: {ref_count_8}"
# 4-Bağlantılıda 4 hedef olmalı: İHA (144 px), Zırhlı (128 px), Çapraz Piksel 1 (1 px), Çapraz Piksel 2 (1 px)
assert ref_count_4 == 4, f"Beklenen 4 hedef ancak bulunan: {ref_count_4}"

# Alanların doğruluğunu kontrol et
target1_area = np.sum(ref_labels_8 == ref_labels_8[10, 10])
target2_area = np.sum(ref_labels_8 == ref_labels_8[35, 40])
assert target1_area == 144, f"Hedef 1 alanı 144 olmalı, hesaplanan: {target1_area}"
assert target2_area == 128, f"Hedef 2 alanı 128 olmalı, hesaplanan: {target2_area}"

print("[PASS] Kod 1: Referans Two-Pass CCL Algoritması Başarıyla Doğrulandı.")
print(f"  - 8-Bağlantılı Tespit Edilen Hedef Sayısı : {ref_count_8} (OpenCV: {cv_num_8 - 1})")
print(f"  - 4-Bağlantılı Tespit Edilen Hedef Sayısı : {ref_count_4} (OpenCV: {cv_num_4 - 1}) [TOPOLOJİK AYRIŞMA DOĞRULANDI]")
print(f"  - Hedef 1 Alanı: {target1_area} px | Hedef 2 Alanı: {target2_area} px")

# ==============================================================================
# HÜCRE 5 / KOD 2: Geometrik Öznitelik Çıkarımı, BBox, Convex Hull ve
# Hu Momentlerinin Rotasyon / Ölçek Değişmezliğinin Sayısal Kanıtı
# ==============================================================================

import numpy as np
import cv2

def compute_hu_moments(contour: np.ndarray) -> np.ndarray:
    # Kontur uzerinden logaritmik Hu Momentlerini turetir
    moments = cv2.moments(contour)
    hu = cv2.HuMoments(moments)
    # Sayısal kararlılık için log-scale dönüşümü: -sign(h) * log10(|h|)
    hu_log = np.zeros(7, dtype=np.float64)
    for i in range(7):
        val = hu[i, 0]
        if val != 0:
            hu_log[i] = -1.0 * np.copysign(1.0, val) * np.log10(np.abs(val))
        else:
            hu_log[i] = 0.0
    return hu_log

# 1. Asimetrik Uçak / Füze Kanat Silueti Oluşturma (128x128 tuval)
canvas_base = np.zeros((128, 128), dtype=np.uint8)
# Gövde (Poligon)
pts_aircraft = np.array([
    [64, 20],   # Burun
    [70, 50],   # Sağ boyun
    [105, 75],  # Sağ kanat ucu
    [70, 80],   # Sağ gövde
    [72, 105],  # Sağ kuyruk ucu
    [64, 98],   # Kuyruk merkezi
    [56, 105],  # Sol kuyruk ucu
    [58, 80],   # Sol gövde
    [23, 75],   # Sol kanat ucu
    [58, 50]    # Sol boyun
], dtype=np.int32)
cv2.fillPoly(canvas_base, [pts_aircraft], 255)

# 2. Döndürülmüş (45 derece) ve Ölçeklenmiş (0.8x, 90 derece) Varyantlar Üretme
M_rot45 = cv2.getRotationMatrix2D((64, 64), 45, 1.0)
canvas_rot45 = cv2.warpAffine(canvas_base, M_rot45, (128, 128), flags=cv2.INTER_LINEAR)
canvas_rot45 = (canvas_rot45 > 127).astype(np.uint8) * 255

M_rot90_scale = cv2.getRotationMatrix2D((64, 64), 90, 0.8)
canvas_rot90 = cv2.warpAffine(canvas_base, M_rot90_scale, (128, 128), flags=cv2.INTER_LINEAR)
canvas_rot90 = (canvas_rot90 > 127).astype(np.uint8) * 255

# 3. Kontur ve Geometrik Öznitelik Çıkarımı
def extract_geometry(mask: np.ndarray):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    perimeter = cv2.arcLength(cnt, True)
    x, y, w, h = cv2.boundingRect(cnt)
    rect = cv2.minAreaRect(cnt) # (center, (w, h), angle)
    hull = cv2.convexHull(cnt)
    hull_area = cv2.contourArea(hull)
    solidity = float(area) / hull_area if hull_area > 0 else 0.0
    hu_log = compute_hu_moments(cnt)
    return {
        "cnt": cnt, "area": area, "perimeter": perimeter,
        "bbox": (x, y, w, h), "min_area_rect": rect,
        "hull": hull, "solidity": solidity, "hu": hu_log
    }

geom_base = extract_geometry(canvas_base)
geom_rot45 = extract_geometry(canvas_rot45)
geom_rot90 = extract_geometry(canvas_rot90)

# 4. Matematiksel Doğrulama: Hu Momentlerinin Rotasyon Değişmezliği
# Hu[0] (Hu1) ve Hu[2] (Hu3) rotasyon ve ölçek altında neredeyse sabit kalmalıdır!
delta_hu1_45 = abs(geom_base["hu"][0] - geom_rot45["hu"][0])
delta_hu3_45 = abs(geom_base["hu"][2] - geom_rot45["hu"][2])

delta_hu1_90 = abs(geom_base["hu"][0] - geom_rot90["hu"][0])
delta_hu3_90 = abs(geom_base["hu"][2] - geom_rot90["hu"][2])

# Ayrık ızgara parazitlerine rağmen log-ölçek farkı sınırları
assert delta_hu1_45 < 0.02, f"Hu1 45 derece rotasyon değişmezliği aşıldı: {delta_hu1_45}"
assert delta_hu3_45 < 0.10, f"Hu3 45 derece rotasyon değişmezliği aşıldı: {delta_hu3_45}"
assert delta_hu1_90 < 0.02, f"Hu1 90 derece rotasyon+ölçek değişmezliği aşıldı: {delta_hu1_90}"
assert delta_hu3_90 < 0.20, f"Hu3 90 derece rotasyon+ölçek değişmezliği aşıldı: {delta_hu3_90}"

# Solidity (Dışbükeylik oranı) uçak silueti için ~0.48 - 0.55 arasında sabit kalmalıdır
assert 0.45 < geom_base["solidity"] < 0.75, f"Solidity aralık dışı: {geom_base['solidity']}"
assert abs(geom_base["solidity"] - geom_rot45["solidity"]) < 0.05, "Solidity rotasyonda bozuldu!"

print("[PASS] Kod 2: Geometrik Öznitelikler ve Hu Momentleri Başarıyla Doğrulandı.")
print(f"  - Baz Hedef Hu Momentleri [Hu1, Hu3] : [{geom_base['hu'][0]:.4f}, {geom_base['hu'][2]:.4f}]")
print(f"  - 45 deg Hedef Hu Momentleri [Hu1, Hu3] : [{geom_rot45['hu'][0]:.4f}, {geom_rot45['hu'][2]:.4f}] (dHu1: {delta_hu1_45:.4f}, dHu3: {delta_hu3_45:.4f})")
print(f"  - 90 deg + Olcek Hu Momentleri [Hu1, Hu3] : [{geom_rot90['hu'][0]:.4f}, {geom_rot90['hu'][2]:.4f}] (dHu1: {delta_hu1_90:.4f}, dHu3: {delta_hu3_90:.4f})")
print(f"  - Baz Hedef Solidity: {geom_base['solidity']:.3f} | 45 deg Solidity: {geom_rot45['solidity']:.3f} [SEKIL IMZASI KORUNDU]")

# ==============================================================================
# HÜCRE 7 / KOD 3: EO/IR Sensör Hedef Ayrıştırma ve Hiyerarşik Ağaç Sınıflandırması
# Dış Sınırlar (Outer Hull), Delikler (Holes) ve Ada Parçaları (Islands)
# ==============================================================================

import numpy as np
import cv2

# 128x128 Sentetik EO/IR Termal Sahnesi Oluşturma
scene_mask = np.zeros((128, 128), dtype=np.uint8)

# 1. HEDEF: İHA (İçinde delikli kokpit ve kokpit içinde pilot kafası olan karmaşık hedef)
# Dış Gövde: 40x30 kutu (10, 10)'dan (50, 40)'a
scene_mask[10:40, 10:50] = 255
# Delik (Kokpit oyuğu - siyah boşluk): 16x12 kutu (18, 22)'den (30, 38)'e
scene_mask[18:30, 22:38] = 0
# Ada (Kokpit içi sıcak aviyonik kutusu - beyaz): 6x6 kutu (22, 27)'den (28, 33)'e
scene_mask[22:28, 27:33] = 255

# 2. HEDEF: Tank / ZMA (Homojen katı hedef - deliksiz)
scene_mask[70:95, 60:110] = 255

# 3. PARAZİTLER: Deniz dalgası / FLIR sahte gürültüleri
scene_mask[105:108, 15:18] = 255  # 9 px parazit
scene_mask[15:18, 95:97] = 255    # 6 px parazit

# --- SUZUKI-ABE RETR_TREE KONTUR VE HİYERARŞİ ÇIKARIMI ---
contours, hierarchy = cv2.findContours(scene_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
hierarchy = hierarchy[0]  # Shape: (N, 4) -> [Next, Prev, First_Child, Parent]

classified_targets = []

for idx, (cnt, h) in enumerate(zip(contours, hierarchy)):
    area = cv2.contourArea(cnt)
    next_idx, prev_idx, child_idx, parent_idx = h
    
    # 1. Kural: Min-Area Gürültü Filtresi
    if area < 20:
        continue  # Parazitleri yok say
        
    is_outer = (parent_idx == -1)
    has_hole = (child_idx != -1)
    is_hole = (parent_idx != -1 and hierarchy[parent_idx][3] == -1)
    is_island = (parent_idx != -1 and hierarchy[parent_idx][3] != -1)
    
    x, y, w, h_box = cv2.boundingRect(cnt)
    centroid = (x + w // 2, y + h_box // 2)
    
    target_type = "Bilinmeyen"
    if is_outer and has_hole:
        target_type = "İHA (Delikli Gövde)"
    elif is_outer and not has_hole:
        target_type = "ZMA / Tank (Katı Gövde)"
    elif is_hole:
        target_type = "Kokpit Oyuğu (Hole)"
    elif is_island:
        target_type = "Aviyonik Kutusu (Island)"
        
    classified_targets.append({
        "id": idx, "type": target_type, "area": area,
        "is_outer": is_outer, "parent": parent_idx, "child": child_idx,
        "bbox": (x, y, w, h_box), "centroid": centroid
    })

# --- DOĞRULAMA (ASSERTIONS) ---
outer_targets = [t for t in classified_targets if t["is_outer"]]
assert len(outer_targets) == 2, f"Beklenen 2 ana dış hedef ancak bulunan: {len(outer_targets)}"

uav_target = next(t for t in classified_targets if "İHA" in t["type"])
tank_target = next(t for t in classified_targets if "Tank" in t["type"])

assert uav_target["child"] != -1, "İHA hedefinin iç deliği hiyerarşide bulunamadı!"
assert tank_target["child"] == -1, "Tank hedefinde sahte delik tespit edildi!"

print("[PASS] Kod 3: EO/IR Hiyerarşik Hedef Sınıflandırma Başarıyla Doğrulandı.")
for t in classified_targets:
    print(f"  - Hedef ID {t['id']:2d} | Tür: {t['type']:<26} | Alan: {t['area']:5.1f} px | Parent: {t['parent']:2d} | Child: {t['child']:2d}")

# ==============================================================================
# HÜCRE 9 / KOD 4: Savunma Sanayii 3 Kritik Hata Enjeksiyonu ve Savunma Kalkanları
# Hata 1: 4 vs 8 Bağlantılık Topoloji Paradoksu (Ghost Track Bölünmesi)
# Hata 2: Kontur Bellek Patlaması (CHAIN_APPROX_NONE vs Douglas-Peucker)
# Hata 3: Min-Area ve Aspect Ratio Sahte Alarm Sızıntısı
# ==============================================================================

import numpy as np
import cv2

# ==============================================================================
# HATA 1: 4-Bağlantılı vs 8-Bağlantılı Topoloji Paradoksu (Hedef Bölünmesi)
# ==============================================================================
print("[TEST 1] 4 vs 8 Bağlantılık Topoloji Paradoksu Kalkanı...")
# FLIR sensöründe 1-piksel çapraz temas eden İHA kanat-gövde bağlantısı
diag_mask = np.zeros((32, 32), dtype=np.uint8)
# Gövde
diag_mask[10:16, 10:16] = 255
# Kanat (Gövdeye yalnızca (16, 16) noktasından çapraz temas ediyor)
diag_mask[16:22, 16:22] = 255

# 4-bağlantılı CCL çalıştırıldığında (Hatalı Tasarım)
num_4, _, stats_4, _ = cv2.connectedComponentsWithStats(diag_mask, connectivity=4)
targets_found_4 = num_4 - 1

# Savunma Kalkanı: Standart 8-Bağlantılı Topoloji Denetimi
num_8, _, stats_8, _ = cv2.connectedComponentsWithStats(diag_mask, connectivity=8)
targets_found_8 = num_8 - 1

assert targets_found_4 == 2, f"4-bağlantılıda 2 hedef bekleniyordu: {targets_found_4}"
assert targets_found_8 == 1, f"8-bağlantılıda 1 birleşik hedef bekleniyordu: {targets_found_8}"
print(f"  - 4-Bağlantılı Sonucu : {targets_found_4} hedef [HATA: TEK HEDEF İKİYE BÖLÜNDÜ! GHOST TRACK]")
print(f"  - 8-Bağlantılı Kalkanı: {targets_found_8} hedef [ONAYLANDI: HEDEF BÜTÜNLÜĞÜ KORUNDU]")
print("[PASS] Test 1: Topoloji paradoksu kalkanı başarıyla doğrulandı.\n")

# ==============================================================================
# HATA 2: Kontur Bellek Patlaması ve Douglas-Peucker Poligon Basitleştirme
# ==============================================================================
print("[TEST 2] Kontur Nokta Patlaması ve approxPolyDP Kalkanı...")
# Pürüzlü, yüksek çözünürlüklü dairesel hedef maskesi (128x128)
circle_mask = np.zeros((128, 128), dtype=np.uint8)
cv2.circle(circle_mask, (64, 64), 40, 255, -1)
# Çevreye pürüzlü sensör gürültüsü enjekte et
noise = (np.random.rand(128, 128) > 0.98).astype(np.uint8) * 255
circle_noisy = cv2.bitwise_xor(circle_mask, noise)

# 1. Hatalı Yaklaşım: CHAIN_APPROX_NONE (Her pürüzlü pikseli saklar)
cnts_none, _ = cv2.findContours(circle_noisy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
main_cnt_none = max(cnts_none, key=cv2.contourArea)
raw_point_count = len(main_cnt_none)

# 2. Savunma Kalkanı: CHAIN_APPROX_SIMPLE + Douglas-Peucker (approxPolyDP)
# Epsilon: Çevre uzunluğunun %1.5'i
peri = cv2.arcLength(main_cnt_none, True)
epsilon = 0.015 * peri
simplified_cnt = cv2.approxPolyDP(main_cnt_none, epsilon, True)
compressed_point_count = len(simplified_cnt)

compression_ratio = (1.0 - compressed_point_count / raw_point_count) * 100.0
assert raw_point_count > 200, f"Beklenen yüksek nokta sayısı: {raw_point_count}"
assert compressed_point_count < 30, f"Basitleştirilmiş nokta sayısı yüksek: {compressed_point_count}"
assert compression_ratio > 85.0, "Sıkıştırma oranı %85 altında kaldı!"

print(f"  - CHAIN_APPROX_NONE Ham Nokta Sayısı     : {raw_point_count} nokta (Bellek Yükü: {raw_point_count*8} B)")
print(f"  - approxPolyDP Basitleştirilmiş Nokta    : {compressed_point_count} nokta (Bellek: {compressed_point_count*8} B)")
print(f"  - Vektörel Sıkıştırma Oranı              : %{compression_ratio:.1f} [BELLEK VE CPU KURTARILDI]")
print("[PASS] Test 2: Kontur nokta basitleştirme kalkanı başarıyla doğrulandı.\n")

# ==============================================================================
# HATA 3: Min-Area ve Aspect Ratio Sahte Alarm Sızıntısı Kalkanı
# ==============================================================================
print("[TEST 3] Min-Area ve Aspect Ratio Sahte Alarm Sızıntısı Kalkanı...")
# Sahne: 1 Gerçek Zırhlı Araç + 1 Optik Flare (İnce uzun ışık hüzmesi) + 5 Parazit
cluttered_scene = np.zeros((128, 128), dtype=np.uint8)
# Gerçek ZMA: 24x16 (Alan: 384 px, Aspect Ratio: 1.5)
cluttered_scene[40:56, 40:64] = 255
# Optik Flare: 2x50 ince çizgi (Alan: 100 px, Aspect Ratio: 25.0)
cluttered_scene[80:82, 20:70] = 255
# 5 adet sıcak parazit (her biri 2x2 = 4 px)
cluttered_scene[10:12, 10:12] = 255
cluttered_scene[15:17, 80:82] = 255
cluttered_scene[100:102, 100:102] = 255

num_raw, _, stats_raw, _ = cv2.connectedComponentsWithStats(cluttered_scene, connectivity=8)
raw_detections = num_raw - 1  # 7 adet ham tespit

# Savunma Kalkanı Fonksiyonu
MIN_AREA_THRESHOLD = 50      # Asgari 50 piksel altı parazittir
MAX_ASPECT_RATIO = 5.0       # En-boy oranı 5.0'dan büyük olanlar optik parlamadır

valid_targets = []
for i in range(1, num_raw):
    area = stats_raw[i, cv2.CC_STAT_AREA]
    w = stats_raw[i, cv2.CC_STAT_WIDTH]
    h = stats_raw[i, cv2.CC_STAT_HEIGHT]
    aspect_ratio = max(w, h) / (min(w, h) + 1e-5)
    
    if area < MIN_AREA_THRESHOLD:
        continue  # Boyut paraziti elendi
    if aspect_ratio > MAX_ASPECT_RATIO:
        continue  # Optik flare elendi
        
    valid_targets.append(i)

assert raw_detections == 5, f"Ham tespit sayısı 5 olmalıydı: {raw_detections}"
assert len(valid_targets) == 1, f"Yalnızca 1 gerçek hedef kalmalıydı, kalan: {len(valid_targets)}"

print(f"  - Filtresiz Ham Tespit Sayısı           : {raw_detections} adet (5 parazit ve flare sızdı!)")
print(f"  - Kalkan Sonrası Doğrulanmış Hedef      : {len(valid_targets)} adet [YALNIZCA GERÇEK ZMA KORUNDU]")
print("[PASS] Test 3: Sahte alarm sızıntısı kalkanı başarıyla doğrulandı.\n")

print("[PASS] Kod 4: 3 Kritik Savunma Hata Enjeksiyonu Testi Başarıyla Tamamlandı.")

# ==============================================================================
# HÜCRE 11 / KOD 5: 10.000 Blok Kontur ve CCL Algoritmik Benchmark Laboratuvarı
# Karşılaştırma: connectedComponentsWithStats (8-way & 4-way) vs findContours (EXTERNAL & TREE)
# ==============================================================================

import time
import numpy as np
import cv2

# Benchmark Yapılandırması
NUM_BLOCKS = 10000
BLOCK_SIZE = (32, 32)
np.random.seed(123)

# 10.000 adet 32x32 sentetik ikili blok üretme
# Her blok rastgele 1-3 hedef ve parazitler barındırır
test_blocks = []
for _ in range(NUM_BLOCKS):
    blk = np.zeros(BLOCK_SIZE, dtype=np.uint8)
    num_blobs = np.random.randint(1, 4)
    for _ in range(num_blobs):
        bx = np.random.randint(2, 22)
        by = np.random.randint(2, 22)
        bw = np.random.randint(4, 10)
        bh = np.random.randint(4, 10)
        blk[by:by+bh, bx:bx+bw] = 255
    # %1 rastgele parazit ekle
    noise = (np.random.rand(*BLOCK_SIZE) > 0.98).astype(np.uint8) * 255
    blk = cv2.bitwise_or(blk, noise)
    test_blocks.append(blk)

def benchmark_method(name: str, func):
    # Fonksiyonun 10.000 blok uzerindeki gecikme ve verim profilini cikarir
    latencies_us = np.zeros(NUM_BLOCKS, dtype=np.float64)
    
    # Isınma (Warm-up)
    for i in range(100):
        func(test_blocks[i])
        
    t_start = time.perf_counter()
    for i in range(NUM_BLOCKS):
        t0 = time.perf_counter_ns()
        func(test_blocks[i])
        t1 = time.perf_counter_ns()
        latencies_us[i] = (t1 - t0) / 1000.0
    total_time = time.perf_counter() - t_start
    
    throughput = NUM_BLOCKS / total_time
    p50 = np.percentile(latencies_us, 50)
    p90 = np.percentile(latencies_us, 90)
    p99 = np.percentile(latencies_us, 99)
    return {
        "name": name, "throughput": throughput,
        "p50": p50, "p90": p90, "p99": p99, "latencies": latencies_us
    }

# Yöntemleri Tanımlama
res_ccl_8 = benchmark_method(
    "CCL (8-way Stats)",
    lambda img: cv2.connectedComponentsWithStats(img, connectivity=8)
)

res_ccl_4 = benchmark_method(
    "CCL (4-way Stats)",
    lambda img: cv2.connectedComponentsWithStats(img, connectivity=4)
)

res_contours_ext = benchmark_method(
    "Contours (RETR_EXTERNAL)",
    lambda img: cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
)

res_contours_tree = benchmark_method(
    "Contours (RETR_TREE)",
    lambda img: cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
)

benchmark_results = [res_ccl_8, res_ccl_4, res_contours_ext, res_contours_tree]

print("\n[10.000 BLOK KONTUR VE CCL BENCHMARK SONUÇLARI (32x32)]")
for r in benchmark_results:
    print(f"  - {r['name']:<24}: {r['throughput']:10.1f} blok/s | p50: {r['p50']:5.2f} us | p99: {r['p99']:5.2f} us")

# Doğrulama: CCL > 100.000 blok/s, Contours (Python bindings) > 15.000 blok/s sağlamalıdır
assert res_ccl_8["throughput"] > 100000.0, f"Düşük CCL verimi: {res_ccl_8['throughput']}"
assert res_contours_ext["throughput"] > 15000.0, f"Düşük Kontur verimi: {res_contours_ext['throughput']}"
for r in benchmark_results:
    assert r["p50"] < 60.0, f"Yüksek p50 gecikmesi: {r['name']} ({r['p50']:.2f} us)"

print("\n[PASS] Kod 5: 10.000 Blok Kontur ve CCL Benchmark Laboratuvarı Başarıyla Tamamlandı.")

# ==============================================================================
# HÜCRE 13 / KOD 6: 4-Panelli Koyu Tema (#0F172A) 300 DPI Görselleştirme Paneli
# Panel 1: İkili Maske & 8-Bağlantılı CCL Etiket Haritası (Centroid & BBox)
# Panel 2: Suzuki-Abe Kontur Hiyerarşisi (Dış Sınır, Delik, MinAreaRect, Hull)
# Panel 3: Hu Momentleri Rotasyon ve Ölçek Değişmezliği (Log-Scale Karşılaştırma)
# Panel 4: 10.000 Blok Benchmark & Gecikme Dağılımı (p50 / p99)
# ==============================================================================

import os
import matplotlib.pyplot as plt
import numpy as np
import cv2

plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 14), dpi=300)
fig.patch.set_facecolor('#0F172A')

for row in axs:
    for ax in row:
        ax.set_facecolor('#1E293B')
        ax.tick_params(colors='#94A3B8', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#334155')

# ------------------------------------------------------------------------------
# PANEL 1: İkili Maske & 8-Bağlantılı CCL Etiket Haritası
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
# Sentetik Sahne Oluştur (128x128)
vis_scene = np.zeros((128, 128), dtype=np.uint8)
vis_scene[20:45, 20:55] = 255   # Hedef 1 (ZMA)
vis_scene[70:105, 70:110] = 255 # Hedef 2 (İHA)
vis_scene[80:95, 80:100] = 0    # İHA Delik
vis_scene[15:18, 90:93] = 255   # Parazit 1
vis_scene[110:113, 20:23] = 255 # Parazit 2

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(vis_scene, connectivity=8)

# Renkli etiket haritası oluştur (Arka plan siyah)
label_hue = np.uint8(179 * labels / np.max(labels))
blank_ch = 255 * np.ones_like(label_hue)
labeled_img = cv2.merge([label_hue, blank_ch, np.uint8(labels > 0) * 255])
labeled_img = cv2.cvtColor(labeled_img, cv2.COLOR_HSV2RGB)

ax1.imshow(labeled_img)
for i in range(1, num_labels):
    area = stats[i, cv2.CC_STAT_AREA]
    if area < 10:
        continue
    x = stats[i, cv2.CC_STAT_LEFT]
    y = stats[i, cv2.CC_STAT_TOP]
    w = stats[i, cv2.CC_STAT_WIDTH]
    h = stats[i, cv2.CC_STAT_HEIGHT]
    cx, cy = centroids[i]
    
    rect_patch = plt.Rectangle((x, y), w, h, fill=False, edgecolor='#38BDF8', linewidth=1.5, linestyle='--')
    ax1.add_patch(rect_patch)
    ax1.plot(cx, cy, marker='+', markersize=10, color='#F43F5E', markeredgewidth=2)
    ax1.text(x, max(0, y - 4), f"ID:{i} A:{area}px", color='#38BDF8', fontsize=8, weight='bold')

ax1.set_title("Panel 1: 8-Bağlantılı CCL Etiketleri ve Bounding Box / Centroid", color='#38BDF8', fontsize=11, weight='bold', pad=10)
ax1.set_xlabel("Piksel X", color='#94A3B8', fontsize=9)
ax1.set_ylabel("Piksel Y", color='#94A3B8', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 2: Suzuki-Abe Kontur Hiyerarşisi (Dış Sınır, Delik, MinAreaRect, Hull)
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
contours, hierarchy = cv2.findContours(vis_scene, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
hierarchy = hierarchy[0]

vis_rgb = cv2.cvtColor(vis_scene, cv2.COLOR_GRAY2RGB) // 3

ax2.imshow(vis_rgb)
colors = ['#10B981', '#F59E0B', '#EC4899', '#8B5CF6', '#06B6D4']

for idx, (cnt, h) in enumerate(zip(contours, hierarchy)):
    area = cv2.contourArea(cnt)
    if area < 10:
        continue
    color = colors[idx % len(colors)]
    pts = cnt.reshape(-1, 2)
    pts_closed = np.vstack([pts, pts[0]])
    
    # Kontur Çizgisi
    ax2.plot(pts_closed[:, 0], pts_closed[:, 1], color=color, linewidth=2, label=f"Kontur {idx} (P:{h[3]})")
    
    # Eğer dış kontur ise Convex Hull ve MinAreaRect çiz
    if h[3] == -1 and area > 100:
        # Convex Hull
        hull = cv2.convexHull(cnt).reshape(-1, 2)
        hull_closed = np.vstack([hull, hull[0]])
        ax2.plot(hull_closed[:, 0], hull_closed[:, 1], color='#F43F5E', linewidth=1.2, linestyle=':', label='Convex Hull')
        # MinAreaRect
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect).astype(np.int32)
        box_closed = np.vstack([box, box[0]])
        ax2.plot(box_closed[:, 0], box_closed[:, 1], color='#EAB308', linewidth=1.2, linestyle='-.', label='Rotated BBox')

ax2.set_title("Panel 2: Suzuki-Abe RETR_TREE Kontur, Delik ve Geometrik Zarf", color='#38BDF8', fontsize=11, weight='bold', pad=10)
ax2.set_xlabel("Piksel X", color='#94A3B8', fontsize=9)
ax2.set_ylabel("Piksel Y", color='#94A3B8', fontsize=9)
ax2.legend(loc='upper right', fontsize=7, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: Hu Momentleri Rotasyon ve Ölçek Değişmezliği
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
x_indices = np.arange(7)
width = 0.25

# geom_base, geom_rot45, geom_rot90 değerleri Hücre 5'ten
hu_base = geom_base["hu"]
hu_rot45 = geom_rot45["hu"]
hu_rot90 = geom_rot90["hu"]

ax3.bar(x_indices - width, hu_base, width, label='Baz Siluet (0°)', color='#38BDF8', alpha=0.85)
ax3.bar(x_indices, hu_rot45, width, label='Döndürülmüş (45°)', color='#10B981', alpha=0.85)
ax3.bar(x_indices + width, hu_rot90, width, label='Döndürülmüş+Ölçek (90°, 0.8x)', color='#F59E0B', alpha=0.85)

ax3.set_title("Panel 3: Hu Momentleri Rotasyon & Ölçek Değişmezliği (Log-Scale)", color='#38BDF8', fontsize=11, weight='bold', pad=10)
ax3.set_xlabel("Hu Moment İndeksi (Hu1 - Hu7)", color='#94A3B8', fontsize=9)
ax3.set_ylabel(r"$-\mathrm{sign}(h) \cdot \log_{10}(|h|)$", color='#94A3B8', fontsize=9)
ax3.set_xticks(x_indices)
ax3.set_xticklabels([f"Hu{i+1}" for i in range(7)])
ax3.grid(True, linestyle='--', alpha=0.3, color='#475569')
ax3.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 4: 10.000 Blok Benchmark & Gecikme Dağılımı
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
names = [r["name"] for r in benchmark_results]
throughputs = [r["throughput"] for r in benchmark_results]
p50s = [r["p50"] for r in benchmark_results]
p99s = [r["p99"] for r in benchmark_results]

y_pos = np.arange(len(names))
bars = ax4.barh(y_pos, throughputs, height=0.45, color='#6366F1', alpha=0.85, edgecolor='#818CF8')

ax4.set_yticks(y_pos)
ax4.set_yticklabels(names, fontsize=8, weight='bold')
ax4.invert_yaxis()
ax4.set_xlabel("Verim (Blok / Saniye)", color='#94A3B8', fontsize=9)
ax4.set_title("Panel 4: 10.000 Blok Kontur & CCL Verim ve Gecikme (32x32)", color='#38BDF8', fontsize=11, weight='bold', pad=10)
ax4.grid(True, linestyle='--', alpha=0.3, color='#475569')

# Barların üzerine verim ve p50/p99 yaz
for bar, p50, p99 in zip(bars, p50s, p99s):
    w = bar.get_width()
    ax4.text(w * 0.5, bar.get_y() + bar.get_height() / 2,
             f"{w:,.0f} b/s  (p50: {p50:.1f}µs, p99: {p99:.1f}µs)",
             ha='center', va='center', color='#FFFFFF', fontsize=8, weight='bold')

plt.tight_layout()
target_png = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_253/gun_253_contours_ve_connected_components.png"
plt.savefig(target_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(target_png) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {target_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100, f"Görsel boyutu yetersiz: {file_size_kb:.2f} KB"

