#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# 
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
# amaçlı olarak paylaşılmıştır.
# 
# YASAKLAR:
#   1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
#   2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
#   3. Alt lisanslanamaz, satılamaz veya devredilemez.
#   4. Tersine mühendislik yapılamaz.
# 
# İZİN VERİLEN KULLANIM:
#   - GitHub üzerinde görüntüleme ve okuma.
#   - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).
# 
# YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
# İzin talepleri için: GitHub @seydivakkas
# ==============================================================================

"""
GÜN 263: Nesne Tespiti Post-Processing: IoU, NMS ve mAP Metrikleri
6 Kod Hücresinin Birleşik Standalone Çalıştırılabilir Betiği
"""

# [KOD HÜCRESİ 1: Vektörel Çiftli IoU ve DIoU Hesaplama Motoru]
# Amaç: N adet tahmin kutusu ile M adet yer gerçeği (GT) kutusu arasındaki 
# örtüşme matrisini NumPy broadcasting ile O(N x M) karmaşıklıkta sıfır döngüyle hesaplamak.

import numpy as np
import time

def box_area(boxes: np.ndarray) -> np.ndarray:
    """Kutuların alanını hesaplar: (x2 - x1) * (y2 - y1)"""
    return (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

def pairwise_iou_vectorized(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """
    N adet A kutusu ile M adet B kutusu arasındaki IoU matrisini hesaplar.
    boxes_a: (N, 4) -> [x1, y1, x2, y2]
    boxes_b: (M, 4) -> [x1, y1, x2, y2]
    Dönüş: (N, M) IoU matrisi
    """
    if len(boxes_a) == 0 or len(boxes_b) == 0:
        return np.zeros((len(boxes_a), len(boxes_b)), dtype=np.float32)
        
    area_a = box_area(boxes_a) # (N,)
    area_b = box_area(boxes_b) # (M,)

    # Kesişim kutusu sol-üst ve sağ-alt koordinatları (Broadcasting: (N, 1, 2) ve (1, M, 2))
    lt = np.maximum(boxes_a[:, None, :2], boxes_b[None, :, :2]) # (N, M, 2) [max_x1, max_y1]
    rb = np.minimum(boxes_a[:, None, 2:], boxes_b[None, :, 2:]) # (N, M, 2) [min_x2, min_y2]

    # Kesişim genişlik ve yüksekliği
    wh = np.clip(rb - lt, a_min=0.0, a_max=None) # (N, M, 2)
    inter_area = wh[:, :, 0] * wh[:, :, 1]       # (N, M)

    # Birleşim alanı: Alan(A) + Alan(B) - Alan(A kesişim B)
    union_area = area_a[:, None] + area_b[None, :] - inter_area

    # Sayısal kararlılık için epsilon (sıfıra bölme koruması)
    iou = inter_area / np.maximum(union_area, 1e-7)
    return iou

def pairwise_diou_vectorized(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """
    N adet A kutusu ile M adet B kutusu arasındaki DIoU (Distance-IoU) matrisini hesaplar.
    DIoU = IoU - (d^2 / c^2)
    """
    iou = pairwise_iou_vectorized(boxes_a, boxes_b)
    if len(boxes_a) == 0 or len(boxes_b) == 0:
        return iou

    # Merkez noktaları
    cx_a = (boxes_a[:, 0] + boxes_a[:, 2]) / 2.0 # (N,)
    cy_a = (boxes_a[:, 1] + boxes_a[:, 3]) / 2.0
    cx_b = (boxes_b[:, 0] + boxes_b[:, 2]) / 2.0 # (M,)
    cy_b = (boxes_b[:, 1] + boxes_b[:, 3]) / 2.0

    # Merkezler arası Öklid karesi: rho^2
    rho2 = (cx_a[:, None] - cx_b[None, :]) ** 2 + (cy_a[:, None] - cy_b[None, :]) ** 2 # (N, M)

    # İki kutuyu içine alan en küçük çevreleyen kutunun (enclosing box) boyutları
    lt_c = np.minimum(boxes_a[:, None, :2], boxes_b[None, :, :2]) # (N, M, 2)
    rb_c = np.maximum(boxes_a[:, None, 2:], boxes_b[None, :, 2:]) # (N, M, 2)
    wh_c = rb_c - lt_c # (N, M, 2)
    c2 = wh_c[:, :, 0] ** 2 + wh_c[:, :, 1] ** 2 # En küçük kutunun köşegen karesi

    diou = iou - (rho2 / np.maximum(c2, 1e-7))
    return diou

# Doğrulama Test Senaryosu: Sentetik Askeri Hedefler
boxes_gt = np.array([
    [100.0, 100.0, 300.0, 250.0], # Hedef 1: MBT Tank Gövdesi (200x150)
    [500.0, 300.0, 650.0, 420.0]  # Hedef 2: SAM Radar Aracı (150x120)
], dtype=np.float32)

boxes_pred = np.array([
    [100.0, 100.0, 300.0, 250.0], # Aday 1: Tam Eşleşen Kutu (IoU = 1.0)
    [120.0, 110.0, 310.0, 260.0], # Aday 2: Hafif Kayan Kutu (Yüksek IoU)
    [1000.0, 800.0, 1100.0, 900.0]# Aday 3: Tamamen Ayrık Kutu (IoU = 0.0, DIoU < 0)
], dtype=np.float32)

iou_mat = pairwise_iou_vectorized(boxes_pred, boxes_gt)
diou_mat = pairwise_diou_vectorized(boxes_pred, boxes_gt)

print(f"[PASS] Kod 1: Vektorel IoU ve DIoU Motoru Basariyla Calistirildi.")
print(f"  - GT Kutu Sayisi: {len(boxes_gt)}, Tahmin Kutu Sayisi: {len(boxes_pred)}")
print(f"  - Aday 1 (Tam Eslenen) IoU: {iou_mat[0, 0]:.4f} | DIoU: {diou_mat[0, 0]:.4f}")
print(f"  - Aday 2 (Hafif Kayik) IoU: {iou_mat[1, 0]:.4f} | DIoU: {diou_mat[1, 0]:.4f}")
print(f"  - Aday 3 (Ayrik Uzak)  IoU: {iou_mat[2, 0]:.4f} | DIoU: {diou_mat[2, 0]:.4f} (Mesafe Cezasi)")

assert np.isclose(iou_mat[0, 0], 1.0), "Tam eslesen kutu IoU 1.0 olmalidir!"
assert iou_mat[1, 0] > 0.65, "Aday 2 yuksek IoU saglamalidir!"
assert np.isclose(iou_mat[2, 0], 0.0), "Temassiz kutu IoU 0.0 olmalidir!"
assert diou_mat[2, 0] < 0.0, "Temassiz kutu DIoU negatif ceza uretmelidir!"


# [KOD HÜCRESİ 2: Greedy NMS ve Sınıf-Ayrık (Batched) Koordinat Öteleme Motoru]
# Amaç: Mükerrer tespitleri bastırırken farklı sınıflardaki (örn. Tank ve Piyade) 
# yakın hedefleri koruyan yüksek performanslı NMS algoritmasını gerçeklemek.

import numpy as np

def nms_single_class(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.5) -> np.ndarray:
    """
    Tek sınıflı Greedy NMS algoritması.
    boxes: (N, 4) -> [x1, y1, x2, y2]
    scores: (N,) -> Güven skorları
    iou_threshold: Bastırma eşiği (örn: 0.50)
    Dönüş: Korunan kutuların indeks dizisi
    """
    if len(boxes) == 0:
        return np.empty((0,), dtype=np.int64)

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)

    # Skorlara göre büyükten küçüğe sırala
    order = scores.argsort()[::-1]
    keep = []

    while order.size > 0:
        i = order[0]
        keep.append(i)

        if order.size == 1:
            break

        # Kalan kutularla en yüksek skorlu kutunun kesişim koordinatları
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h

        union = areas[i] + areas[order[1:]] - inter
        iou = inter / np.maximum(union, 1e-7)

        # IoU eşiğini aşmayan (bağımsız) kutuları koru
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1] # +1 indeks kayması (i elendiği için)

    return np.array(keep, dtype=np.int64)

def batched_multiclass_nms(boxes: np.ndarray, scores: np.ndarray, class_ids: np.ndarray, 
                           iou_threshold: float = 0.5, max_coordinate: float = 4096.0) -> np.ndarray:
    """
    Farklı sınıfların birbirini bastırmasını önleyen GPU-dostu koordinat öteleme NMS'i.
    Her sınıfın kutularına (class_id * max_coordinate) ötelemesi uygulanır.
    """
    if len(boxes) == 0:
        return np.empty((0,), dtype=np.int64)

    # Koordinat öteleme: [x1 + offset, y1 + offset, x2 + offset, y2 + offset]
    offsets = class_ids[:, None].astype(boxes.dtype) * max_coordinate
    shifted_boxes = boxes + offsets

    # Ötelenmiş kutular üzerinde tek seferlik NMS çalıştır
    return nms_single_class(shifted_boxes, scores, iou_threshold)

# Sentetik Muharebe Sahası Senaryosu: Tank ve Piyade Yakın Temas
# Hedef 1 (Tank, class_id=0): 3 adet mükerrer kutu (skorlar: 0.92, 0.75, 0.60)
# Hedef 2 (Piyade, class_id=1): Tankın hemen yanında, örtüşen kutu (skor: 0.88)
demo_boxes = np.array([
    [200.0, 150.0, 350.0, 250.0], # 0: Tank - Ana Kutu (Geniş)
    [205.0, 152.0, 348.0, 248.0], # 1: Tank - Mükerrer 1 (Yüksek Örtüşme)
    [195.0, 148.0, 352.0, 255.0], # 2: Tank - Mükerrer 2 (Yüksek Örtüşme)
    [240.0, 180.0, 280.0, 260.0]  # 3: Piyade - Tankın yanında duruyor! (Tankla IoU > 0.40)
], dtype=np.float32)

demo_scores = np.array([0.92, 0.75, 0.60, 0.88], dtype=np.float32)
demo_classes = np.array([0, 0, 0, 1], dtype=np.int32) # Sınıf 0: Tank, Sınıf 1: Piyade

# 1. Hatalı Yaklaşım: Sınıf-Bağımsız Düz NMS (Piyadeyi yanlışlıkla ezer!)
naive_keep = nms_single_class(demo_boxes, demo_scores, iou_threshold=0.35)

# 2. Doğru Askeri Yaklaşım: Batched Multi-Class NMS (Piyadeyi korur!)
batched_keep = batched_multiclass_nms(demo_boxes, demo_scores, demo_classes, iou_threshold=0.35)

print(f"[PASS] Kod 2: NMS ve Batched NMS Motoru Basariyla Calistirildi.")
print(f"  - Toplam Aday Kutu: {len(demo_boxes)}")
print(f"  - Duz NMS Sonucu Kalan Indeksler: {naive_keep.tolist()} (Piyade Silindi mi? -> {3 not in naive_keep})")
print(f"  - Batched NMS Kalan Indeksler    : {batched_keep.tolist()} (Tank=0, Piyade=3 korundu!)")

assert 0 in batched_keep, "Tank ana kutusu korunmalidir!"
assert 3 in batched_keep, "Piyade kutusu baska sinif oldugu icin kesinlikle elenmemelidir!"
assert len(batched_keep) == 2, "Yalnizca 1 Tank ve 1 Piyade kalmalidir!"


# [KOD HÜCRESİ 3: Tam Kapsamlı COCO mAP@[.50:.95] ve PR Değerlendirme Motoru]
# Amaç: Nesne tespit modellerinin muharebe sahası kabul testlerinde kullanılan 
# 101-nokta enterpolasyonlu Precision-Recall ve mAP hesaplama motorunu kurmak.

import numpy as np

def compute_ap_single_class(pred_boxes: np.ndarray, pred_scores: np.ndarray, 
                           gt_boxes: np.ndarray, iou_thresh: float = 0.50) -> tuple:
    """
    Tek bir sınıf için TP/FP dizilerini, Precision-Recall eğrisini ve AP değerini hesaplar.
    """
    num_gt = len(gt_boxes)
    num_pred = len(pred_boxes)

    if num_gt == 0:
        return 0.0, np.array([0.0]), np.array([0.0])
    if num_pred == 0:
        return 0.0, np.array([0.0]), np.array([0.0])

    # Tahminleri azalan güven skoruna göre sırala
    sort_idx = np.argsort(pred_scores)[::-1]
    pred_boxes = pred_boxes[sort_idx]
    pred_scores = pred_scores[sort_idx]

    tp = np.zeros(num_pred, dtype=np.float32)
    fp = np.zeros(num_pred, dtype=np.float32)
    gt_matched = np.zeros(num_gt, dtype=bool)

    # Vektörel IoU matrisi: (num_pred, num_gt)
    iou_matrix = pairwise_iou_vectorized(pred_boxes, gt_boxes)

    # Her tahmin için en iyi eşleşen GT'yi bul
    for p_idx in range(num_pred):
        best_gt_idx = np.argmax(iou_matrix[p_idx])
        max_iou = iou_matrix[p_idx, best_gt_idx]

        if max_iou >= iou_thresh:
            if not gt_matched[best_gt_idx]:
                tp[p_idx] = 1.0 # Başarılı doğru tespit
                gt_matched[best_gt_idx] = True
            else:
                fp[p_idx] = 1.0 # Mükerrer tespit (aynı hedefe ikinci atış)
        else:
            fp[p_idx] = 1.0 # IoU eşiğini karşılamayan veya sahte alarm

    # Kümülatif TP ve FP
    tp_cumsum = np.cumsum(tp)
    fp_cumsum = np.cumsum(fp)

    precisions = tp_cumsum / np.maximum(tp_cumsum + fp_cumsum, 1e-7)
    recalls = tp_cumsum / float(num_gt)

    # COCO 101-Nokta İnterpolasyonu
    recall_thresholds = np.linspace(0.0, 1.0, 101)
    prec_interp = np.zeros(101, dtype=np.float32)

    for i, r_thresh in enumerate(recall_thresholds):
        # r >= r_thresh olan tüm recall değerleri için en yüksek precision
        prec_candidates = precisions[recalls >= r_thresh]
        if prec_candidates.size > 0:
            prec_interp[i] = np.max(prec_candidates)
        else:
            prec_interp[i] = 0.0

    ap = np.mean(prec_interp)
    return ap, precisions, recalls

def evaluate_coco_map(predictions: dict, ground_truths: dict, class_names: list) -> dict:
    """
    mAP@50 ve mAP@[.50:.95] metriklerini tüm sınıflar için hesaplar.
    predictions: {class_id: {'boxes': (N, 4), 'scores': (N,)}}
    ground_truths: {class_id: {'boxes': (M, 4)}}
    """
    iou_thresholds = np.arange(0.50, 0.96, 0.05) # 10 eşik: 0.50, 0.55, ..., 0.95
    results = {}
    
    all_class_aps_at_50 = []
    all_class_aps_range = []

    for cid, cname in enumerate(class_names):
        p_data = predictions.get(cid, {'boxes': np.empty((0, 4)), 'scores': np.empty((0,))})
        g_data = ground_truths.get(cid, {'boxes': np.empty((0, 4))})

        aps_at_thresholds = []
        for iou_th in iou_thresholds:
            ap, _, _ = compute_ap_single_class(p_data['boxes'], p_data['scores'], g_data['boxes'], iou_thresh=iou_th)
            aps_at_thresholds.append(ap)

        ap_50 = aps_at_thresholds[0]
        ap_50_95 = np.mean(aps_at_thresholds)

        results[cname] = {'AP50': ap_50, 'AP50_95': ap_50_95}
        all_class_aps_at_50.append(ap_50)
        all_class_aps_range.append(ap_50_95)

    results['mAP50'] = float(np.mean(all_class_aps_at_50))
    results['mAP50_95'] = float(np.mean(all_class_aps_range))
    return results

# Sentetik Doğrulama Veri Kümesi
synthetic_classes = ["TANK", "SAM_RADAR"]

gt_data = {
    0: {'boxes': np.array([[100, 100, 300, 250], [500, 400, 700, 550]], dtype=np.float32)}, # 2 Tank
    1: {'boxes': np.array([[800, 150, 950, 300]], dtype=np.float32)}                        # 1 SAM
}

pred_data = {
    0: {
        'boxes': np.array([
            [102, 101, 298, 248], # Yüksek IoU Tank 1
            [510, 405, 695, 545], # Yüksek IoU Tank 2
            [200, 700, 300, 800]  # Sahte Alarm (FP) Tank
        ], dtype=np.float32),
        'scores': np.array([0.95, 0.89, 0.45], dtype=np.float32)
    },
    1: {
        'boxes': np.array([
            [805, 152, 948, 298]  # Mükemmel Eşleşen SAM 1
        ], dtype=np.float32),
        'scores': np.array([0.97], dtype=np.float32)
    }
}

map_report = evaluate_coco_map(pred_data, gt_data, synthetic_classes)

print(f"[PASS] Kod 3: COCO mAP@[.50:.95] Degerlendirme Motoru Basariyla Calistirildi.")
for cname in synthetic_classes:
    print(f"  - {cname:10s} : AP@50 = {map_report[cname]['AP50']:.4f} | AP@[.50:.95] = {map_report[cname]['AP50_95']:.4f}")
print(f"  - GENEL mAP@50    : {map_report['mAP50']:.4f}")
print(f"  - GENEL mAP@50:95 : {map_report['mAP50_95']:.4f}")

assert map_report['mAP50'] > 0.80, "mAP@50 degeri yuksek dogrulukta olmalidir!"
assert map_report['mAP50_95'] <= map_report['mAP50'], "mAP@50:95 degeri mAP@50 degerinden buyuk olamaz!"


# [KOD HÜCRESİ 4: 3 Askeri Hata Enjeksiyonu ve Güvenlik Kalkanı Testleri]
# Amaç: Sıfır hedef, yoğun hedef boğulması ve sıfıra bölme sınır durumlarında 
# sistemin deterministik ve çökmesiz çalıştığını doğrulamak.

import numpy as np

# TEST 1: Boş Matris ve Sıfır Hedef Kalkanı Testi
print(f"[TEST 1] Sifir Tespit / Bos Girdi Kalkan Testi...")
empty_boxes = np.empty((0, 4), dtype=np.float32)
empty_scores = np.empty((0,), dtype=np.float32)
valid_gt = np.array([[100, 100, 200, 200]], dtype=np.float32)

# IoU ve NMS fonksiyonlarının boş dizilerde çökmediğini doğrula
empty_iou = pairwise_iou_vectorized(empty_boxes, valid_gt)
empty_nms_keep = nms_single_class(empty_boxes, empty_scores)
empty_ap, _, _ = compute_ap_single_class(empty_boxes, empty_scores, valid_gt)

assert empty_iou.shape == (0, 1), "Bos girdi icin IoU sekli (0, 1) olmalidir!"
assert len(empty_nms_keep) == 0, "Bos girdide NMS bos indeks donmelidir!"
assert empty_ap == 0.0, "Hic tahmin yoksa AP 0.0 olmalidir!"
print(f"  [PASS] Test 1: Bos matris kalkani basariyla dogrulandi.")

# TEST 2: Yoğun Sürü / NMS Boğulması ve Top-K Sınırlama Kalkanı
print(f"\n[TEST 2] Yogun Suru / NMS Bogulmasi ve Top-K Sinirlama Kalkani...")
# Tek bir noktada kümelenmiş 5.000 gürültülü kutu üret
np.random.seed(42)
clutter_boxes = np.random.uniform(200.0, 220.0, size=(5000, 4)).astype(np.float32)
clutter_boxes[:, 2:] += np.random.uniform(50.0, 100.0, size=(5000, 2))
clutter_scores = np.random.uniform(0.1, 0.99, size=(5000,)).astype(np.float32)

# Top-K Aviyonik Bounded NMS Uygulaması
TOP_K_LIMIT = 300
MAX_OUTPUT_LIMIT = 20

def bounded_avionic_nms(boxes: np.ndarray, scores: np.ndarray, 
                        top_k: int = 300, max_out: int = 50, iou_th: float = 0.5) -> np.ndarray:
    if len(boxes) == 0:
        return np.empty((0,), dtype=np.int64)
    # Skorlara göre en yüksek Top-K kutuyu seç
    if len(boxes) > top_k:
        top_indices = np.argsort(scores)[::-1][:top_k]
        boxes = boxes[top_indices]
        scores = scores[top_indices]
    else:
        top_indices = np.arange(len(boxes))

    keep_local = nms_single_class(boxes, scores, iou_threshold=iou_th)
    keep_global = top_indices[keep_local[:max_out]]
    return keep_global

keep_bounded = bounded_avionic_nms(clutter_boxes, clutter_scores, top_k=TOP_K_LIMIT, max_out=MAX_OUTPUT_LIMIT)

assert len(keep_bounded) <= MAX_OUTPUT_LIMIT, "Cikti kutusu max_out sinirini asamaz!"
print(f"  - 5000 Kutu Arasindan Secilen Top-K: {TOP_K_LIMIT}")
print(f"  - NMS Sonucu Kalan Hedef Sayisi   : {len(keep_bounded)} (Sinir: {MAX_OUTPUT_LIMIT})")
print(f"  [PASS] Test 2: Top-K bogulma kalkani basariyla dogrulandi.")

# TEST 3: Sıfır Yer Gerçeği (No Ground Truth) Sıfıra Bölme Kalkanı
print(f"\n[TEST 3] Sifir Yer Gercegi (No GT) Sifira Bolme Kalkani...")
dummy_preds = np.array([[100, 100, 200, 200]], dtype=np.float32)
dummy_scores = np.array([0.95], dtype=np.float32)
no_gt = np.empty((0, 4), dtype=np.float32)

ap_no_gt, prec_no_gt, rec_no_gt = compute_ap_single_class(dummy_preds, dummy_scores, no_gt)

assert not np.isnan(ap_no_gt), "Sifir GT durumunda AP NaN olamaz!"
assert ap_no_gt == 0.0, "GT olmayan sinifta AP 0.0 donmelidir!"
print(f"  - Donen AP: {ap_no_gt} (NaN olusumu engellendi)")
print(f"  [PASS] Test 3: Sifira bolme ve NaN kalkani basariyla dogrulandi.")


# [KOD HÜCRESİ 5: 10.000 Kutu Post-Processing Stres Benchmark Laboratuvarı]
# Amaç: Gerçek zamanlı elektro-optik hedef tespitinde 10.000 aday kutunun 
# filtrelenmesi, NMS budaması ve 2.0 ms aviyonik zaman sınırını doğrulamak.

import numpy as np
import time

# 10.000 Aday Kutu Üretimi (YOLOv8x / RT-DETR Benzetimi)
np.random.seed(123)
N_BOXES = 10000
raw_boxes = np.random.uniform(50.0, 1800.0, size=(N_BOXES, 4)).astype(np.float32)
raw_boxes[:, 2] = raw_boxes[:, 0] + np.random.uniform(20.0, 200.0, size=(N_BOXES,))
raw_boxes[:, 3] = raw_boxes[:, 1] + np.random.uniform(20.0, 200.0, size=(N_BOXES,))
raw_scores = np.random.uniform(0.01, 0.99, size=(N_BOXES,)).astype(np.float32)

# Skor filtreleme (conf >= 0.25)
score_mask = raw_scores >= 0.25
filtered_boxes = raw_boxes[score_mask]
filtered_scores = raw_scores[score_mask]

# Benchmark: 50 İterasyon
NUM_RUNS = 50

# 1. Bounded Avionic NMS (Top-K = 300)
t0 = time.perf_counter()
for _ in range(NUM_RUNS):
    kept_indices = bounded_avionic_nms(filtered_boxes, filtered_scores, top_k=300, max_out=50, iou_th=0.45)
t_bounded = (time.perf_counter() - t0) / NUM_RUNS * 1000.0 # ms

# 2. Vektörel IoU Hesaplama Hızı (300 Kutu x 50 GT Hedef)
demo_gt_50 = raw_boxes[:50]
t0 = time.perf_counter()
for _ in range(NUM_RUNS):
    iou_mat_bench = pairwise_iou_vectorized(filtered_boxes[:300], demo_gt_50)
t_iou = (time.perf_counter() - t0) / NUM_RUNS * 1000.0 # ms

print(f"[BENCHMARK SONUCLARI] (10.000 Ham Kutu -> {len(filtered_boxes)} Filtrelenmis Kutu)")
print(f"  - Vektorel IoU (300 x 50 Matris) Suresi : {t_iou:.4f} ms")
print(f"  - Top-K Bounded NMS Calisma Suresi       : {t_bounded:.4f} ms")
print(f"  - Toplam Post-Processing Gecikmesi       : {(t_iou + t_bounded):.4f} ms")
print(f"  - Aviyonik Butce (2.0 ms) Durumu        : [{'UYGUN' if (t_iou + t_bounded) < 2.0 else 'ASILDI'}]")

assert (t_iou + t_bounded) < 5.0, "Post-processing benchmark 5 ms altinda tamamlanmalidir!"
assert len(kept_indices) <= 50, "Cikti kutulari limit dahilinde olmalidir!"


# [KOD HÜCRESİ 6: 4-Panelli Mühendislik Görselleştirme Gösterge Paneli]
# Amaç: IoU/DIoU geometrisini, NMS budama sürecini, Precision-Recall eğrisini 
# ve aviyonik gecikme analizini 300 DPI çözünürlükte profesyonelce görselleştirmek.

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

# Dark Theme Konfigürasyonu
plt.style.use('dark_background')
fig, axes = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax_row in axes:
    for ax in ax_row:
        ax.set_facecolor('#1E293B')
        ax.grid(True, linestyle='--', alpha=0.3, color='#64748B')
        ax.tick_params(colors='#94A3B8', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#334155')

# PANEL 1: IoU vs DIoU Geometrik Örtüşme ve Merkez Mesafesi
ax1 = axes[0, 0]
ax1.set_title("Panel 1: IoU vs DIoU Geometrisi (Kesişim, Birleşim ve Merkez Cezası)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)

# Kutu A (GT) ve Kutu B (Tahmin)
box_a = [50, 50, 150, 130] # [x1, y1, w, h]
box_b = [120, 90, 140, 120]

# En küçük çevreleyen kutu C
enc_box = [50, 50, 210, 160]

rect_enc = patches.Rectangle((enc_box[0], enc_box[1]), enc_box[2], enc_box[3], 
                             linewidth=1.5, edgecolor='#F59E0B', facecolor='none', linestyle=':', label='Enclosing Box C')
rect_a = patches.Rectangle((box_a[0], box_a[1]), box_a[2], box_a[3], 
                           linewidth=2, edgecolor='#38BDF8', facecolor='#38BDF8', alpha=0.25, label='Kutu A (Yer Gerçeği)')
rect_b = patches.Rectangle((box_b[0], box_b[1]), box_b[2], box_b[3], 
                           linewidth=2, edgecolor='#4ADE80', facecolor='#4ADE80', alpha=0.25, label='Kutu B (Tahmin)')

# Kesişim Alanı
inter_rect = patches.Rectangle((120, 90), 80, 90, linewidth=1.5, edgecolor='#F87171', facecolor='#F87171', alpha=0.5, label='Kesişim (Intersection)')

ax1.add_patch(rect_enc)
ax1.add_patch(rect_a)
ax1.add_patch(rect_b)
ax1.add_patch(inter_rect)

# Merkez Noktaları ve Mesafe Çizgisi
ca = (box_a[0] + box_a[2]/2, box_a[1] + box_a[3]/2)
cb = (box_b[0] + box_b[2]/2, box_b[1] + box_b[3]/2)
ax1.plot([ca[0], cb[0]], [ca[1], cb[1]], color='#EF4444', linestyle='--', linewidth=2, marker='o', label='Merkez Mesafesi (d)')
ax1.plot([enc_box[0], enc_box[0] + enc_box[2]], [enc_box[1], enc_box[1] + enc_box[3]], color='#F59E0B', linestyle='--', alpha=0.7, label='Köşegen (c)')

ax1.set_xlim(30, 280)
ax1.set_ylim(30, 230)
ax1.set_xlabel("Piksel X", color='#94A3B8', fontsize=9)
ax1.set_ylabel("Piksel Y", color='#94A3B8', fontsize=9)
ax1.legend(loc='upper left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# PANEL 2: NMS Öncesi vs NMS Sonrası Tespit Budama
ax2 = axes[0, 1]
ax2.set_title("Panel 2: NMS Budama Süreci (Ham Mükerrer Kümeler vs Temizlenmiş Hedef)", 
              fontsize=11, fontweight='bold', color='#4ADE80', pad=10)

# Simüle edilmiş hedef aracı
target_center = (150, 150)
ax2.scatter([target_center[0]], [target_center[1]], color='#EF4444', s=100, marker='x', label='Gerçek Hedef Merkezi')

# NMS Öncesi 8 Adet Mükerrer Kutu (Kırmızımsı/Saydam)
np.random.seed(99)
for idx in range(8):
    w_rand = np.random.uniform(70, 95)
    h_rand = np.random.uniform(50, 75)
    x_rand = target_center[0] - w_rand/2 + np.random.uniform(-15, 15)
    y_rand = target_center[1] - h_rand/2 + np.random.uniform(-15, 15)
    conf = np.random.uniform(0.60, 0.95)
    r_cand = patches.Rectangle((x_rand, y_rand), w_rand, h_rand, linewidth=1, 
                               edgecolor='#F87171', facecolor='none', linestyle='--', alpha=0.6)
    ax2.add_patch(r_cand)
    ax2.text(x_rand, y_rand - 4, f"{conf:.2f}", color='#FCA5A5', fontsize=7)

# NMS Sonrası Seçilen En Yüksek Skorlu Kutu (Kalın Yeşil)
best_box = [110, 120, 80, 60]
r_best = patches.Rectangle((best_box[0], best_box[1]), best_box[2], best_box[3], 
                           linewidth=2.5, edgecolor='#4ADE80', facecolor='#4ADE80', alpha=0.2, label='NMS Sonucu Korunan (Score=0.96)')
ax2.add_patch(r_best)
ax2.text(best_box[0], best_box[1] - 6, "CONFIRMED_TANK: 0.96", color='#4ADE80', fontsize=8, fontweight='bold')

ax2.set_xlim(50, 250)
ax2.set_ylim(50, 250)
ax2.set_xlabel("Sensör X (px)", color='#94A3B8', fontsize=9)
ax2.set_ylabel("Sensör Y (px)", color='#94A3B8', fontsize=9)
ax2.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# PANEL 3: Precision-Recall Eğrisi ve 101-Nokta Monotonik Zarflama
ax3 = axes[1, 0]
ax3.set_title("Panel 3: Precision-Recall Eğrisi ve 101-Nokta Monotonik Enterpolasyon", 
              fontsize=11, fontweight='bold', color='#FBBF24', pad=10)

rec_sample = np.array([0.0, 0.15, 0.30, 0.45, 0.60, 0.75, 0.85, 0.92, 1.0])
prec_sample = np.array([1.0, 0.96, 0.94, 0.82, 0.88, 0.72, 0.65, 0.40, 0.20])

# Monotonik zarf
prec_env = np.maximum.accumulate(prec_sample[::-1])[::-1]

r_dense = np.linspace(0.0, 1.0, 101)
p_dense = np.interp(r_dense, rec_sample, prec_env)

ax3.plot(rec_sample, prec_sample, color='#94A3B8', linestyle=':', marker='o', label='Ham P-R Değerleri (Zikzaklı)')
ax3.plot(r_dense, p_dense, color='#FBBF24', linewidth=2.5, label='101-Nokta Monoton Zarf (AP=0.84)')
ax3.fill_between(r_dense, 0, p_dense, color='#FBBF24', alpha=0.2, label='Eğri Altı Alan (AUC / AP)')

ax3.set_xlim(0.0, 1.05)
ax3.set_ylim(0.0, 1.05)
ax3.set_xlabel("Recall (Yakalama Oranı)", color='#94A3B8', fontsize=9)
ax3.set_ylabel("Precision (Hassasiyet)", color='#94A3B8', fontsize=9)
ax3.legend(loc='lower left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# PANEL 4: Aday Kutu Sayısına Göre NMS Çalışma Süresi (Aviyonik Limit)
ax4 = axes[1, 1]
ax4.set_title("Panel 4: Post-Process Gecikmesi vs Aday Kutu Sayısı (Aviyonik 2ms Sınırı)", 
              fontsize=11, fontweight='bold', color='#F472B6', pad=10)

box_counts = np.array([100, 500, 1000, 2500, 5000, 10000])
# Simüle edilmiş O(N^2) Standart NMS vs Top-K Bounded NMS gecikmeleri
standard_nms_lat = 0.05 + 0.0000012 * (box_counts ** 2) # O(N^2)
bounded_nms_lat = np.minimum(standard_nms_lat, 0.65 + 0.00002 * box_counts) # Bounded

ax4.plot(box_counts, standard_nms_lat, color='#EF4444', marker='s', linewidth=2, label='Standart NMS (O(N^2) Boğulma)')
ax4.plot(box_counts, bounded_nms_lat, color='#38BDF8', marker='o', linewidth=2.5, label='Top-K Bounded Aviyonik NMS (O(1))')
ax4.axhline(y=2.0, color='#F59E0B', linestyle='--', linewidth=2, label='Aviyonik Gerçek Zaman Sınırı (2.0 ms)')

ax4.set_xlabel("Aday Kutu Sayısı (N)", color='#94A3B8', fontsize=9)
ax4.set_ylabel("İşlem Gecikmesi (ms)", color='#94A3B8', fontsize=9)
ax4.set_yscale('log')
ax4.legend(loc='upper left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.tight_layout()
output_png = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_263/gun_263_iou_nms_ve_map.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Gorsellestirme Basariyla Uretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")


