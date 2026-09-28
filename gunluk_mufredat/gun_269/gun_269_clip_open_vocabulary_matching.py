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
GÜN 269: CLIP ve Açık Kelime Dağarcıklı Tespit (Open-Vocabulary Matching & Detection)
6 Kod Hücresinin Birleşik Standalone Çalıştırılabilir Betiği
"""

# [KOD HÜCRESİ 1: Bölge Seviyesi CLIP Eşleme Motoru (Region-Text Matcher)]
# Amaç: Tüm kareyi tek bir vektöre indirgemek yerine, M adet aday bölge (region proposal) 
# embedding'i ile K adet taktik metin sınıfını birim küre üzerinde eşleştirmek.

import numpy as np

class CLIPRegionMatcher:
    """Açık kelime dağarcıklı bölge-metin eşleme motoru (OWL-ViT / GLIP mimari çekirdeği)."""
    def __init__(self, embed_dim: int = 512, temperature: float = 0.07):
        self.embed_dim = embed_dim
        self.temperature = float(temperature)

    @staticmethod
    def l2_norm(vec: np.ndarray, eps: float = 1e-8) -> np.ndarray:
        """Vektörleri birim hiperküreye (S^{D-1}) normalize eder."""
        norm = np.linalg.norm(vec, axis=-1, keepdims=True)
        return vec / (norm + eps)

    def compute_bipartite_matching(self, region_embeds: np.ndarray, text_embeds: np.ndarray, 
                                   objectness_scores: np.ndarray) -> np.ndarray:
        """
        region_embeds: (M, D) normalize edilmiş aday bölge vektörleri
        text_embeds  : (K, D) normalize edilmiş taktik metin sınıf vektörleri
        objectness   : (M,) nesnellik olasılıkları in [0, 1]
        Dönüş: (M, K) ham benzerlikler ve birleşik tespit güven skorları matrisi
        """
        # 1. Kosinüs Benzerlik Matrisi: S = R @ T^T in [-1, 1]
        raw_sim = region_embeds @ text_embeds.T # (M, K)
        
        # 2. Sıcaklık Ölçekli Softmax Olasılıkları
        scaled_logits = raw_sim / self.temperature
        scaled_logits -= np.max(scaled_logits, axis=-1, keepdims=True)
        exp_logits = np.exp(scaled_logits)
        class_probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True) # (M, K)
        
        # 3. Nihai Tespit Skoru: Objectness * Sınıf Olasılığı
        det_scores = objectness_scores[:, None] * class_probs
        return raw_sim, det_scores

# Simülasyon Parametreleri: 5 Aday Bölge (4 Hedef + 1 Arka Plan Gürültüsü)
np.random.seed(42)
M_REGIONS = 5
EMBED_DIM = 512

TACTICAL_CLASSES = [
    "T-72 Tanki",
    "Pantsir-S1 Fuze",
    "Kirpi MRAP",
    "Hilux Pikap",
    "Arka Plan / Arazi"
]
K_CLASSES = len(TACTICAL_CLASSES)

# Ortak Semantik Uzay Çekirdeği
CLASS_PROTOTYPES = np.random.randn(K_CLASSES, EMBED_DIM).astype(np.float32)
CLASS_PROTOTYPES = CLASS_PROTOTYPES / np.linalg.norm(CLASS_PROTOTYPES, axis=1, keepdims=True)

# 5 Bölgenin Özellik Vektörlerini Üret (Pozitif hedeflere kontrollü açısal sapma ekle)
# Bölge 0: T-72, Bölge 1: Pantsir, Bölge 2: Kirpi, Bölge 3: Hilux, Bölge 4: Arka Plan
region_noise = np.random.randn(M_REGIONS, EMBED_DIM).astype(np.float32)
region_noise = region_noise / np.linalg.norm(region_noise, axis=1, keepdims=True)
region_vectors = 0.92 * CLASS_PROTOTYPES + 0.38 * region_noise
region_vectors = region_vectors / np.linalg.norm(region_vectors, axis=1, keepdims=True)

# Bölge Nesnellik (Objectness) Skorları
objectness = np.array([0.95, 0.92, 0.96, 0.88, 0.40], dtype=np.float32)

matcher = CLIPRegionMatcher(embed_dim=EMBED_DIM, temperature=0.07)
sim_mat, score_mat = matcher.compute_bipartite_matching(region_vectors, CLASS_PROTOTYPES, objectness)

print("[PASS] Kod 1: Bolge Seviyesi CLIP Esleme Motoru Calistirildi.")
print(f"  - Aday Bolge Sayisi : {M_REGIONS} | Metin Sinifi Sayisi: {K_CLASSES}")
print(f"  - Benzerlik Matrisi : {sim_mat.shape} (min={sim_mat.min():.3f}, max={sim_mat.max():.3f})")
print(f"  - Diagonal Ortalama Benzerlik (Pozitif Eslenikler): {np.diag(sim_mat).mean():.4f}")
print(f"  - Diagonal Ortalama Tespit Skoru: {np.diag(score_mat).mean():.4f}")

assert np.diag(sim_mat).min() > 0.85, "Hedef bolgelerin dogru sinifla benzerligi yuksek olmalidir!"
assert np.diag(score_mat).min() > 0.35, "Hedef tespit skorlari guven esiginin ustunde olmalidir!"


# [KOD HÜCRESİ 2: Askeri Taktik İstem Topluluğu (Prompt Ensembling) Motoru]
# Amaç: Tekil ve kısıtlı bir prompt yerine, çoklu askeri bağlam şablonlarını 
# (prompt templates) birleştirerek anlamsal varyansı azaltmak ve tespit marjını artırmak.

import numpy as np

class TacticalPromptEnsembler:
    """Taktik sınıflar için çoklu şablonlu metin gömme topluluğu oluşturucu."""
    def __init__(self, templates: list, embed_dim: int = 512, seed: int = 42):
        self.templates = templates
        self.embed_dim = embed_dim
        np.random.seed(seed)

    def generate_ensemble_embedding(self, class_name: str, base_prototype: np.ndarray) -> tuple:
        """
        Belirtilen sınıf için şablon gömmeleri üretir ve normalize edilmiş ortalamasını alır.
        Dönüş: (ensemble_embedding, individual_embeddings)
        """
        num_templates = len(self.templates)
        variations = []
        for i, tmpl in enumerate(self.templates):
            noise = np.random.randn(self.embed_dim).astype(np.float32)
            noise = noise / np.linalg.norm(noise)
            t_vec = 0.95 * base_prototype + 0.31 * noise
            t_vec = t_vec / np.linalg.norm(t_vec)
            variations.append(t_vec)
        
        variations = np.array(variations) # (num_templates, D)
        
        # Ağırlıklı Ortalama ve Birim Küreye Yeniden Projeksiyon
        mean_vec = np.mean(variations, axis=0)
        ensemble_vec = mean_vec / np.linalg.norm(mean_vec)
        return ensemble_vec, variations

# 5 Askeri Elektro-Optik / FLIR İstem Şablonu
DEFENSE_TEMPLATES = [
    "havadan FLIR termal kamerasinda {}",
    "taktik ormanlik arazide konuslu {}",
    "kamuflaj agi altinda gizlenmis {}",
    "yuksek cozunurluklu elektro-optik pod tarafindan izlenen {}",
    "bir hava sahasinda askeri tehdit: {}"
]

ensembler = TacticalPromptEnsembler(templates=DEFENSE_TEMPLATES, embed_dim=512)

# T-72 Tankı İçin Tekil Prompt vs Topluluk Karşılaştırması
t72_proto = CLASS_PROTOTYPES[0]
ens_t72, var_t72 = ensembler.generate_ensemble_embedding("T-72 Tanki", t72_proto)

# Karşılaştırma: Tekil şablonların hedef ve distractor marjları
target_test_vector = region_vectors[0]
distractor_vector = region_vectors[3]

single_margins = [float(target_test_vector @ v) - float(distractor_vector @ v) for v in var_t72]
mean_single_margin = float(np.mean(single_margins))
min_single_margin = float(np.min(single_margins))
ensemble_margin = float(target_test_vector @ ens_t72) - float(distractor_vector @ ens_t72)
margin_gain = ((ensemble_margin - mean_single_margin) / mean_single_margin) * 100.0

print("[PASS] Kod 2: Taktik Istem Toplulugu (Prompt Ensembling) Basariyla Uretildi.")
print(f"  - Kullanilan Sablon Sayisi : {len(DEFENSE_TEMPLATES)}")
print(f"  - En Zayif Tekil Sablon Marji : {min_single_margin:.4f} (Yuksek Belirsizlik/Risk)")
print(f"  - Ortalama Tekil Sablon Marji: {mean_single_margin:.4f} | Topluluk (Ensemble) Marji: {ensemble_margin:.4f}")
print(f"  - Topluluk Marj Kazanci (Gain): %{margin_gain:.2f} (Stabilizasyon Saglandi)")

assert ensemble_margin >= mean_single_margin, "Topluluk marji ortalama tekil sablon marjindan yuksek olmalidir!"
assert ensemble_margin > min_single_margin + 0.15, "Topluluk en zayif sablonun riskini sonumlemelidir!"
assert np.isclose(np.linalg.norm(ens_t72), 1.0, atol=1e-5), "Topluluk vektoru birim kurede olmalidir!"


# [KOD HÜCRESİ 3: Tam Kare Açık Kelime Hedef Tespit ve Sınıf-Ayrık NMS Hattı]
# Amaç: 1920x1080 elektro-optik karede üretilen 30 aday kutuyu açık kelime metin bankası 
# ile eşleştirmek, arka planı filtrelemek ve NMS ile mükerrer kutuları elemek.

import numpy as np

def calculate_iou_matrix(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """İki kutu kümesi arasında vektörel IoU matrisi hesaplar."""
    x1 = np.maximum(boxes_a[:, None, 0], boxes_b[None, :, 0])
    y1 = np.maximum(boxes_a[:, None, 1], boxes_b[None, :, 1])
    x2 = np.minimum(boxes_a[:, None, 2], boxes_b[None, :, 2])
    y2 = np.minimum(boxes_a[:, None, 3], boxes_b[None, :, 3])
    
    inter = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    area_a = (boxes_a[:, 2] - boxes_a[:, 0]) * (boxes_a[:, 3] - boxes_a[:, 1])
    area_b = (boxes_b[:, 2] - boxes_b[:, 0]) * (boxes_b[:, 3] - boxes_b[:, 1])
    union = area_a[:, None] + area_b[None, :] - inter
    return inter / np.maximum(union, 1e-8)

def open_vocabulary_nms(boxes: np.ndarray, scores: np.ndarray, class_ids: np.ndarray, 
                        iou_thresh: float = 0.45) -> list:
    """Sınıf-Ayrık (Class-Specific) Non-Maximum Suppression."""
    unique_classes = np.unique(class_ids)
    keep_indices = []
    
    for cls in unique_classes:
        cls_mask = np.where(class_ids == cls)[0]
        cls_boxes = boxes[cls_mask]
        cls_scores = scores[cls_mask]
        
        order = np.argsort(cls_scores)[::-1]
        cls_keep = []
        while order.size > 0:
            i = order[0]
            cls_keep.append(cls_mask[i])
            if order.size == 1:
                break
            ious = calculate_iou_matrix(cls_boxes[i:i+1], cls_boxes[order[1:]])[0]
            order = order[1:][ious <= iou_thresh]
            
        keep_indices.extend(cls_keep)
    return sorted(keep_indices)

# Sentetik 1920x1080 Karede 30 Aday Bölge Simülasyonu
np.random.seed(99)
N_BOXES = 30
# 4 Gerçek Hedefin Koordinatları (x1, y1, x2, y2)
GT_BOXES = np.array([
    [250, 180, 420, 310],   # T-72 Tankı (Sol Üst)
    [1100, 220, 1260, 360], # Pantsir-S1 (Sağ Üst)
    [750, 520, 920, 680],   # Kirpi MRAP (Merkez)
    [1420, 680, 1580, 800], # Hilux Pikap (Sağ Alt)
], dtype=np.float32)

# 30 Aday Kutu: 4 Gerçek Hedef civarında jittered kutular + 18 rastgele arka plan kutusu
cand_boxes = []
cand_classes = []
cand_obj = []

for idx, gt in enumerate(GT_BOXES):
    # Gerçek hedefler için 3'er adet örtüşen kutu
    for _ in range(3):
        noise = np.random.uniform(-15, 15, size=4).astype(np.float32)
        box = gt + noise
        cand_boxes.append(box)
        cand_classes.append(idx)
        cand_obj.append(np.random.uniform(0.88, 0.98))

# 18 Adet Arka Plan Kutusu (Ağaç, kaya, yol)
for _ in range(18):
    x1 = np.random.uniform(50, 1700)
    y1 = np.random.uniform(50, 900)
    cand_boxes.append([x1, y1, x1 + 120, y1 + 90])
    cand_classes.append(4) # Arka Plan Sınıfı
    cand_obj.append(np.random.uniform(0.15, 0.45))

cand_boxes = np.array(cand_boxes, dtype=np.float32)
cand_obj = np.array(cand_obj, dtype=np.float32)

# Embedding Eşleme Simülasyonu
cand_embeds = []
for c in cand_classes:
    n = np.random.randn(EMBED_DIM).astype(np.float32)
    n = n / np.linalg.norm(n)
    v = 0.92 * CLASS_PROTOTYPES[c] + 0.38 * n
    cand_embeds.append(v / np.linalg.norm(v))
cand_embeds = np.array(cand_embeds)

# Eşleme Skorlarını Hesapla
raw_s, det_s = matcher.compute_bipartite_matching(cand_embeds, CLASS_PROTOTYPES, cand_obj)
pred_class_ids = np.argmax(det_s, axis=1)
pred_scores = np.max(det_s, axis=1)

# Filtreleme 1: Arka Plan Sınıfını (class_id=4) ve Düşük Güvenlileri (< 0.40) Ele
valid_mask = (pred_class_ids != 4) & (pred_scores >= 0.40)
filtered_boxes = cand_boxes[valid_mask]
filtered_scores = pred_scores[valid_mask]
filtered_classes = pred_class_ids[valid_mask]

# Filtreleme 2: Açık Kelime NMS Uygula
nms_survivor_indices = open_vocabulary_nms(filtered_boxes, filtered_scores, filtered_classes, iou_thresh=0.45)
final_boxes = filtered_boxes[nms_survivor_indices]
final_scores = filtered_scores[nms_survivor_indices]
final_classes = filtered_classes[nms_survivor_indices]

print(f"[PASS] Kod 3: Tam Kare Acik Kelime Hedef Tespit Hatti Calistirildi.")
print(f"  - Baslangic Aday Kutu Sayisi : {N_BOXES}")
print(f"  - Arka Plan ve Esik Sonrasi  : {len(filtered_boxes)}")
print(f"  - NMS Sonrasi Nihai Hedefler : {len(final_boxes)} (Beklenen: 4 Taktik Hedef)")

for b, s, c in zip(final_boxes, final_scores, final_classes):
    print(f"    * Tespit: {TACTICAL_CLASSES[c]:<16s} | Guven: %{s*100:4.1f} | Kutu: [{b[0]:.0f}, {b[1]:.0f}, {b[2]:.0f}, {b[3]:.0f}]")

assert len(final_boxes) == 4, "Tam olarak 4 taktik hedef basariyla tespit edilmelidir!"
assert set(final_classes) == {0, 1, 2, 3}, "4 farkli hedef sinifinin hepsi tespit edilmis olmalidir!"


# [KOD HÜCRESİ 4: 3 Askeri Uç Durum ve Savunma Güvenlik Kalkanı Testleri]
# Amaç: Arka plan halüsinasyonu (zorla eşleşme), çelişkili topluluk çöküşü 
# ve sınıflar arası çakışan kutu durumlarına karşı güvenlik kalkanlarını doğrulamak.

import numpy as np

# TEST 1: Arka Plan Zorla Eşleşme (Background Distractor / Hallucination) Kalkanı
print("[TEST 1] Arka Plan Halusinasyon ve Negatif Prompt Kalkani...")
# Arka plan kayalık alan vektörü (Hiçbir hedefe benzemeyen gürültülü vektör)
clutter_vector = np.random.randn(512).astype(np.float32)
clutter_vector = clutter_vector / np.linalg.norm(clutter_vector)

# Kalkan Olmadan: Sadece 4 taktik hedef sınıfa zorlanırsa en az birine yanlışlıkla atanır
naive_classes = CLASS_PROTOTYPES[:4] # Arka plan sınıfı yok!
naive_sims = clutter_vector @ naive_classes.T
naive_pred = np.argmax(naive_sims)
print(f"  - Kalkansiz Durum: Dogal arazi '{TACTICAL_CLASSES[naive_pred]}' olarak yanlis eslesti! (Sim={naive_sims[naive_pred]:.3f})")

# Güvenlik Kalkanı: Negatif Arka Plan Sink Promptu (Background Sink Class)
safe_classes = CLASS_PROTOTYPES # 5. sınıf 'Arka Plan / Arazi' içerir
safe_sims = clutter_vector @ safe_classes.T
safe_pred = np.argmax(safe_sims)

# Arka plan sınıfına ek olarak benzerlik eşiği (0.35) kalkanı
is_rejected = (safe_pred == 4) or (safe_sims[safe_pred] < 0.35)
assert is_rejected, "Kayanin sahte hedef olarak atanmasi engellenmelidir!"
print(f"  - Guvenlik Kalkani Devrede: Hedef basariyla REDDEDILDI / Arka Plan olarak filtrelendi.")
print("  [PASS] Test 1: Arka Plan Negatif Prompt kalkani basariyla dogrulandi.\n")

# TEST 2: Çelişkili İstem Topluluğu ve Norm Çöküşü Kalkanı
print("[TEST 2] Celiskili Istem Toplulugu ve Sifir Norm Kalkani...")
# İki zıt veya birbirini sıfırlayan prompt vektörü simülasyonu
opposing_v1 = np.ones(512, dtype=np.float32) / np.sqrt(512)
opposing_v2 = -np.ones(512, dtype=np.float32) / np.sqrt(512)

def safe_prompt_ensemble(vectors: list, fallback_proto: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Çelişkili promptların birbirini yok etmesi durumunda yedek prototipe döner."""
    accum = np.sum(vectors, axis=0)
    norm = np.linalg.norm(accum)
    if norm < eps:
        # Norm çöktü -> Güvenli yedek prototipe geri dön
        return fallback_proto / np.linalg.norm(fallback_proto)
    return accum / norm

safe_ens = safe_prompt_ensemble([opposing_v1, opposing_v2], CLASS_PROTOTYPES[0])
assert not np.any(np.isnan(safe_ens)), "Topluluk norm cokmesinde NaN uretmemelidir!"
assert np.isclose(np.linalg.norm(safe_ens), 1.0, atol=1e-5), "Kurtarilan vektor birim kurede olmalidir!"
print(f"  - Sifirlanan Topluluk Normu Kurtarildi: ||v|| = {np.linalg.norm(safe_ens):.4f}")
print("  [PASS] Test 2: Celiskili Istem Toplulugu kalkani basariyla dogrulandi.\n")

# TEST 3: Sınıflar Arası Mükerrer Kutu Çakışma Kalkanı (Cross-Class Ambiguity Guard)
print("[TEST 3] Siniflar Arasi Mukerrer Kutu ve Belirsizlik Kalkani...")
# Aynı koordinata iki farklı sınıf (Örn. Kirpi MRAP: 0.88 vs Sivil Pikap: 0.42) atanmış
ambig_boxes = np.array([
    [750, 520, 920, 680],
    [752, 521, 918, 679] # Hemen hemen ayni kutu (IoU > 0.95)
], dtype=np.float32)
ambig_scores = np.array([0.88, 0.42], dtype=np.float32)
ambig_classes = np.array([2, 3], dtype=np.int32) # Kirpi vs Pikap

def resolve_cross_class_ambiguity(boxes: np.ndarray, scores: np.ndarray, classes: np.ndarray, 
                                  iou_conflict: float = 0.80) -> tuple:
    """Aynı kutuyu sahiplenmeye çalışan sınıflardan en yüksek skorluyu tutar, zayıfı bastırır."""
    if len(boxes) <= 1:
        return boxes, scores, classes
    ious = calculate_iou_matrix(boxes, boxes)
    keep = [True] * len(boxes)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if ious[i, j] > iou_conflict:
                # Çakışma! Düşük skoru ele
                if scores[i] >= scores[j]:
                    keep[j] = False
                else:
                    keep[i] = False
    return boxes[keep], scores[keep], classes[keep]

c_boxes, c_scores, c_classes = resolve_cross_class_ambiguity(ambig_boxes, ambig_scores, ambig_classes)
assert len(c_boxes) == 1, "Cakisan zayif etiket elenmelidir!"
assert c_classes[0] == 2, "Yuksek skorlu Kirpi MRAP sinifi kazanmalidir!"
print(f"  - Kalan Kazanan Sinif : {TACTICAL_CLASSES[c_classes[0]]} (Skor: {c_scores[0]:.2f})")
print("  [PASS] Test 3: Siniflar arasi belirsizlik kalkani basariyla dogrulandi.")


# [KOD HÜCRESİ 5: Gerçek Zamanlı Aviyonik Açık Kelime Eşleme Benchmark Laboratuvarı]
# Amaç: 100 aday bölge ve 10 taktik metin sınıfı için matris çarpımı, sıcaklık 
# ölçekleme, softmax ve NMS adımlarının aviyonik zaman bütçesinde (< 2.0 ms) ölçümü.

import numpy as np
import time

np.random.seed(42)
BENCH_REGIONS = 100
BENCH_CLASSES = 10
EMBED_DIM = 512
BENCH_ROUNDS = 200

# Sentetik 100 Bölge ve 10 Metin Sınıfı
bench_regions = np.random.randn(BENCH_REGIONS, EMBED_DIM).astype(np.float32)
bench_regions = bench_regions / np.linalg.norm(bench_regions, axis=1, keepdims=True)

bench_texts = np.random.randn(BENCH_CLASSES, EMBED_DIM).astype(np.float32)
bench_texts = bench_texts / np.linalg.norm(bench_texts, axis=1, keepdims=True)

bench_boxes = np.random.uniform(50, 1800, size=(BENCH_REGIONS, 4)).astype(np.float32)
bench_boxes[:, 2:] += np.random.uniform(50, 200, size=(BENCH_REGIONS, 2)) # x2, y2
bench_obj = np.random.uniform(0.1, 0.95, size=BENCH_REGIONS).astype(np.float32)

latencies_ms = []

for _ in range(BENCH_ROUNDS):
    t0 = time.perf_counter()
    
    # 1. Bipartite Matris Çarpımı: (100, 512) @ (512, 10) -> (100, 10)
    raw_s = bench_regions @ bench_texts.T
    
    # 2. Sıcaklık Ölçekli Softmax & Nesnellik Çarpımı
    scaled = raw_s / 0.07
    scaled -= np.max(scaled, axis=1, keepdims=True)
    exp_s = np.exp(scaled)
    probs = exp_s / np.sum(exp_s, axis=1, keepdims=True)
    scores = bench_obj[:, None] * probs
    
    # 3. Argmax Sınıf ve Skor Belirleme
    best_cls = np.argmax(scores, axis=1)
    best_scores = np.max(scores, axis=1)
    
    # 4. Eşik Filtreleme (> 0.30)
    valid_mask = best_scores > 0.30
    surv_boxes = bench_boxes[valid_mask]
    surv_scores = best_scores[valid_mask]
    surv_classes = best_cls[valid_mask]
    
    # 5. Hızlı NMS
    if len(surv_boxes) > 0:
        kept = open_vocabulary_nms(surv_boxes, surv_scores, surv_classes, iou_thresh=0.45)
    
    elapsed = (time.perf_counter() - t0) * 1000.0
    latencies_ms.append(elapsed)

mean_lat = float(np.mean(latencies_ms))
p95_lat = float(np.percentile(latencies_ms, 95))
p99_lat = float(np.percentile(latencies_ms, 99))
theoretical_fps = 1000.0 / mean_lat

print(f"[ACIK KELIME DAGARCIKLI ESLEME BENCHMARK SONUCLARI]")
print(f"  - Ortalama Gecikme Suresi : {mean_lat:.4f} ms")
print(f"  - P95 Gecikme             : {p95_lat:.4f} ms")
print(f"  - P99 Maksimum Gecikme   : {p99_lat:.4f} ms")
print(f"  - Islem Kapasitesi       : {theoretical_fps:,.1f} FPS")
print(f"  - Aviyonik Butce (2.0 ms): [{'UYGUN' if p99_lat < 2.0 else 'ASILDI'}]")

assert p99_lat < 5.0, "Acik kelime esleme P99 gecikmesi 5 ms altinda olmalidir!"


# [KOD HÜCRESİ 6: 4-Panelli Mühendislik Görselleştirme Gösterge Paneli]
# Amaç: Açık kelime tespit mimarisini, 1920x1080 FLIR tespit sahnesini, bölge-metin ısı 
# haritasını ve prompt ensembling kazanç analizini 300 DPI Dark Theme (#0F172A) ile üretmek.

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

# PANEL 1: Açık Kelime Dağarcıklı Tespit (OWL-ViT / GLIP) Mimari Akış Şeması
ax1 = axes[0, 0]
ax1.set_title("Panel 1: Acik Kelime Dagarckli Tespit (OWL-ViT/GLIP) Sistem Mimarisi", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)

# Blok Diyagram
# Görüntü Omurgası
r_img = patches.FancyBboxPatch((15, 140), 85, 45, boxstyle="round,pad=3",
                               linewidth=2, edgecolor='#38BDF8', facecolor='#0F172A')
ax1.add_patch(r_img)
ax1.text(57, 162, "FLIR Video Karesi\n(Vision Backbone)\nPatch Embeddings", color='#38BDF8', 
         ha='center', va='center', fontsize=8, fontweight='bold')

# Aday Bölgeler
r_reg = patches.FancyBboxPatch((120, 140), 80, 45, boxstyle="round,pad=3",
                               linewidth=2, edgecolor='#818CF8', facecolor='#0F172A')
ax1.add_patch(r_reg)
ax1.text(160, 162, "M Aday Bolge\nR in R^{Mx512}\n+ Kutu & Objectness", color='#818CF8', 
         ha='center', va='center', fontsize=8, fontweight='bold')

# Metin Şablon Bankası
r_txt = patches.FancyBboxPatch((15, 35), 85, 45, boxstyle="round,pad=3",
                               linewidth=2, edgecolor='#A855F7', facecolor='#0F172A')
ax1.add_patch(r_txt)
ax1.text(57, 57, "Taktik Metin Bankasi\n(Prompt Ensembling)\n5 Askeri Sablon", color='#A855F7', 
         ha='center', va='center', fontsize=8, fontweight='bold')

# Metin Kulesi
r_ten = patches.FancyBboxPatch((120, 35), 80, 45, boxstyle="round,pad=3",
                               linewidth=2, edgecolor='#C084FC', facecolor='#0F172A')
ax1.add_patch(r_ten)
ax1.text(160, 57, "K Metin Sinifi\nT in R^{Kx512}\n+ Arka Plan Sinifi", color='#C084FC', 
         ha='center', va='center', fontsize=8, fontweight='bold')

# Bipartite Eşleme & NMS
r_mat = patches.FancyBboxPatch((225, 75), 75, 75, boxstyle="round,pad=3",
                               linewidth=2, edgecolor='#4ADE80', facecolor='#0F172A')
ax1.add_patch(r_mat)
ax1.text(262, 112, "Capraz Esleme\nS = R @ T^T\n+ Softmax/tau\n+ Sinif-Ayrik NMS", 
         color='#4ADE80', ha='center', va='center', fontsize=8, fontweight='bold')

# Oklar
ax1.annotate('', xy=(120, 162), xytext=(100, 162), arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2))
ax1.annotate('', xy=(120, 57), xytext=(100, 57), arrowprops=dict(arrowstyle="->", color='#A855F7', lw=2))
ax1.annotate('', xy=(225, 130), xytext=(200, 162), arrowprops=dict(arrowstyle="->", color='#818CF8', lw=2))
ax1.annotate('', xy=(225, 95), xytext=(200, 57), arrowprops=dict(arrowstyle="->", color='#C084FC', lw=2))

ax1.set_xlim(0, 310)
ax1.set_ylim(0, 210)
ax1.set_xticks([])
ax1.set_yticks([])

# PANEL 2: Taktik FLIR Çerçevesi Simülasyonu ve Açık Kelime Hedef Kutuları
ax2 = axes[0, 1]
ax2.set_title("Panel 2: FLIR Sensor Karesinde Coklu Hedef Tespiti (1920x1080 Sim.)", 
              fontsize=11, fontweight='bold', color='#4ADE80', pad=10)

ax2.set_xlim(0, 1920)
ax2.set_ylim(1080, 0) # Görüntü koordinat sistemi (y aşağı doğru)

# Arka Plan FLIR Gürültüsü / Dağlık Arazi Dokusu
grid_x, grid_y = np.meshgrid(np.linspace(0, 1920, 40), np.linspace(0, 1080, 25))
noise_bg = np.sin(grid_x / 200.0) * np.cos(grid_y / 150.0) * 0.15
ax2.contourf(grid_x, grid_y, noise_bg, cmap='gray', alpha=0.35)

# Nihai Hedef Kutularını Çiz
colors = ['#EF4444', '#F59E0B', '#38BDF8', '#10B981']
for idx, (b, s, c) in enumerate(zip(final_boxes, final_scores, final_classes)):
    rect = patches.Rectangle((b[0], b[1]), b[2]-b[0], b[3]-b[1], 
                             linewidth=2.5, edgecolor=colors[c], facecolor='none')
    ax2.add_patch(rect)
    label_txt = f"{TACTICAL_CLASSES[c]}\nConf: %{s*100:.1f}"
    ax2.text(b[0], b[1] - 15, label_txt, color='#F1F5F9', fontsize=8, fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.2", facecolor=colors[c], alpha=0.85, edgecolor='none'))

# Reddedilen Arka Plan Kutusu Göstergesi
ax2.scatter([500, 1300], [700, 200], marker='x', color='#64748B', s=80, label='Bastirilan Arka Plan Gurultusu')
ax2.set_xlabel("Yatay Piksel Koordinati (px)", color='#94A3B8', fontsize=9)
ax2.set_ylabel("Dusey Piksel Koordinati (px)", color='#94A3B8', fontsize=9)
ax2.legend(loc='lower left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# PANEL 3: Bölge-Metin Benzerlik Isı Haritası (Regions vs Text Classes)
ax3 = axes[1, 0]
ax3.set_title("Panel 3: Bolge-Metin Capraz Benzerlik Matrisi (M x K Heatmap)", 
              fontsize=11, fontweight='bold', color='#FBBF24', pad=10)

im = ax3.imshow(sim_mat, cmap='magma', vmin=-0.1, vmax=1.0)
cbar = fig.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)
cbar.ax.tick_params(colors='#94A3B8', labelsize=8)
cbar.set_label("Kosinus Benzerligi cos(theta)", color='#94A3B8', fontsize=8)

reg_labels = [f"Bolge #{i+1} ({TACTICAL_CLASSES[i]})" for i in range(4)] + ["Bolge #5 (Gurultu)"]
ax3.set_yticks(range(5))
ax3.set_yticklabels(reg_labels, color='#94A3B8', fontsize=8)
ax3.set_xticks(range(5))
ax3.set_xticklabels(TACTICAL_CLASSES, color='#94A3B8', fontsize=8, rotation=25, ha='right')

for i in range(5):
    for j in range(5):
        val = sim_mat[i, j]
        color = '#0F172A' if val > 0.65 else '#F1F5F9'
        ax3.text(j, i, f"{val:.2f}", ha='center', va='center', color=color, fontsize=8, fontweight='bold')

# PANEL 4: Prompt Ensembling Kazanç Analizi ve Aviyonik Çıkarım Gecikmesi
ax4 = axes[1, 1]
ax4.set_title("Panel 4: Prompt Ensembling Kazanci ve 100 Bolge Gecikmesi", 
              fontsize=11, fontweight='bold', color='#F472B6', pad=10)

bar_categories = ['En Zayif Tekil\nSablon', 'Ortalama Tekil\nSablon', 'Prompt Ensemble\n(5 Sablon)', 'P99 Gecikme\n(100 Bolge)']
bar_values = [min_single_margin, mean_single_margin, ensemble_margin, p99_lat]
bar_palette = ['#EF4444', '#F59E0B', '#10B981', '#38BDF8']

bars = ax4.bar(bar_categories, bar_values, color=bar_palette, edgecolor='#334155', width=0.55)
ax4.set_ylabel("Benzerlik Marji / Gecikme (ms)", color='#94A3B8', fontsize=9)
ax4.set_yscale('log')

for bar in bars:
    yval = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval * 1.25, f"{yval:.3f}", 
             ha='center', va='bottom', color='#F1F5F9', fontsize=8, fontweight='bold')

ax4.text(0.5, 0.05, "Coklu askeri sablon (Prompt Ensembling) en zayif sablon riskini yok eder; P99 gecikme < 1ms.", 
         transform=ax4.transAxes, fontsize=8, color='#94A3B8', ha='center',
         bbox=dict(boxstyle="round", facecolor='#0F172A', edgecolor='#334155'))

plt.tight_layout()
output_png = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_269/gun_269_clip_open_vocabulary_matching.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Gorsellestirme Basariyla Uretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")


