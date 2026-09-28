# ==============================================================================
# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
# YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz, tersine mühendislik yapılamaz.
# İZİN VERİLEN KULLANIM: GitHub üzerinde görüntüleme/okuma, kişisel öğrenim.
# Yazarın açık yazılı izni olmaksızın hiçbir kullanım hakkı tanınmaz.
# İzin talepleri için: GitHub @seydivakkas
# ==============================================================================

# [KOD HÜCRESİ 1: Taktik Elektro-Optik Hedef Tespit Modeli ve FP32/FP16 Dönüşümü]
# Amaç: Savunma sistemleri için çok katmanlı konvolüsyonel hedef tespit modeli kurmak,
# bu modeli FP32 ve FP16 (Half Precision) formatlarında derleyerek bellek/ağırlık boyutlarını ölçmek.

import os
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class TacticalEOVisionBackbone(nn.Module):
    """
    Aviyonik FLIR ve Elektro-Optik Gimbal Kameraları için Hedef Tespit Omurgası.
    FP16 çıkarımında Tensor Core hızlandırmasına tam uyum için kanal sayıları 8'in katı olarak seçilmiştir.
    """
    def __init__(self, in_channels: int = 3, feature_dim: int = 8):
        super().__init__()
        # Blok 1: 3x3 Conv -> BN -> ReLU (Kanal: 3 -> 32)
        self.conv1 = nn.Conv2d(in_channels, 32, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(32)
        self.act1 = nn.ReLU(inplace=True)
        
        # Blok 2: 3x3 Conv -> BN -> ReLU (Kanal: 32 -> 64)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(64)
        self.act2 = nn.ReLU(inplace=True)
        
        # Blok 3: 3x3 Conv -> BN -> ReLU (Kanal: 64 -> 128)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn3 = nn.BatchNorm2d(128)
        self.act3 = nn.ReLU(inplace=True)
        
        # Global Havuzlama ve Aviyonik Çıktı Projeksiyonu
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.head = nn.Linear(128, feature_dim)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.act1(self.bn1(self.conv1(x)))
        x = self.act2(self.bn2(self.conv2(x)))
        x = self.act3(self.bn3(self.conv3(x)))
        x = self.pool(x)
        x = torch.flatten(x, 1)
        feat = self.head(x)
        # L2 Birim Küre Normalizasyonu (Hedef Vektörü)
        norm = torch.norm(feat, p=2, dim=1, keepdim=True).clamp(min=1e-4)
        return feat / norm

torch.manual_seed(42)
model_fp32 = TacticalEOVisionBackbone(in_channels=3, feature_dim=8).to(device)
model_fp32.eval()

# FP16 (Half Precision) Kopyası
model_fp16 = TacticalEOVisionBackbone(in_channels=3, feature_dim=8)
model_fp16.load_state_dict(model_fp32.state_dict())
model_fp16 = model_fp16.half().to(device)
model_fp16.eval()

# Model Ağırlık Bellek Tüketimini Hesapla
def get_model_size_kb(model: nn.Module) -> float:
    total_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
    total_bytes += sum(b.numel() * b.element_size() for b in model.buffers())
    return total_bytes / 1024.0

size_fp32_kb = get_model_size_kb(model_fp32)
size_fp16_kb = get_model_size_kb(model_fp16)
memory_saving_pct = (1.0 - (size_fp16_kb / size_fp32_kb)) * 100.0

print(f"[PASS] Kod 1: Taktik Algilama Modeli FP32 ve FP16 Olarak Hazirlandi.")
print(f"  - Calisma Donanimi (Device) : {device} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")
print(f"  - Toplam Parametre Sayisi   : {sum(p.numel() for p in model_fp32.parameters()):,} adet")
print(f"  - FP32 Model Boyutu (VRAM)  : {size_fp32_kb:.2f} KB (4 bayt / parametre)")
print(f"  - FP16 Model Boyutu (VRAM)  : {size_fp16_kb:.2f} KB (2 bayt / parametre)")
print(f"  - VRAM Bellek Tasarrufu     : %{memory_saving_pct:.1f} (Tam 2x Azalma!)")

assert abs(memory_saving_pct - 50.0) < 1.0, "FP16 model agirligi tam %50 daha az bellek kaplamalidir!"


# [KOD HÜCRESİ 2: IEEE 754 FP32 vs FP16 Bit Yapısı ve Dinamik Aralık Simülatörü]
# Amaç: Tek duyarlıklı (FP32) ve yarı duyarlıklı (FP16) kayan nokta formatlarının
# bit dağılımını, sayısal sınırlarını ve dinamik aralık uçlarını matematiksel olarak modellemek.

import numpy as np

# IEEE 754 Kayan Nokta Formatı Özellikleri
fp_specs = {
    'FP32 (Single)': {
        'total_bits': 32,
        'sign_bits': 1,
        'exp_bits': 8,
        'mantissa_bits': 23,
        'bias': 127,
        'min_positive_normal': 1.17549435e-38,
        'max_finite': 3.4028235e+38,
        'decimal_precision': 7
    },
    'FP16 (Half)': {
        'total_bits': 16,
        'sign_bits': 1,
        'exp_bits': 5,
        'mantissa_bits': 10,
        'bias': 15,
        'min_positive_normal': 6.1035156e-05,
        'max_finite': 65504.0,
        'decimal_precision': 3.3
    }
}

print("[ANALIZ] IEEE 754 Kayan Nokta Mimari Karşılaştırması:")
for name, spec in fp_specs.items():
    print(f"\n--- {name} ---")
    print(f"  * Toplam Bit Genişliği : {spec['total_bits']} bit (İşaret: {spec['sign_bits']}, Üs: {spec['exp_bits']}, Kesir: {spec['mantissa_bits']})")
    print(f"  * Üs Kayması (Bias)    : {spec['bias']}")
    print(f"  * En Küçük Pozitif Sayı: {spec['min_positive_normal']:.2e}")
    print(f"  * En Büyük Sayı (Max)  : {spec['max_finite']:,}")
    print(f"  * Ondalık Hassasiyet   : ~{spec['decimal_precision']} basamak")

# Taşma (Overflow) ve Altına Taşma (Underflow) Test Değerleri
val_nominal = 12.345678
val_overflow_candidate = 70000.0  # FP16 max: 65,504
val_underflow_candidate = 1.0e-6  # FP16 min normal: 6.1e-5

# Sayısal Dönüşüm Testi
val_nom_fp16 = np.float16(val_nominal)
with np.errstate(over='ignore'):
    val_over_fp16 = np.float16(val_overflow_candidate)
val_under_fp16 = np.float16(val_underflow_candidate)

print("\n[KRİTİK UÇ DEĞER DÖNÜŞÜMLERİ]")
print(f"  - Nominal Değer ({val_nominal}) -> FP16: {val_nom_fp16} (Hassasiyet kaybı: {abs(val_nominal - float(val_nom_fp16)):.6f})")
print(f"  - Aşırı Değer ({val_overflow_candidate}) -> FP16: {val_over_fp16} (Taşma / Overflow -> Sonsuzluk!)")
print(f"  - Küçük Değer ({val_underflow_candidate}) -> FP16: {val_under_fp16} (Altına Taşma / Underflow -> Sıfır veya Subnormal!)")

assert np.isinf(val_over_fp16), "65504 uzerindeki sayilar FP16'da kesinlikle Inf olmalidir!"
assert abs(val_nominal - float(val_nom_fp16)) < 0.01, "Nominal aralikta FP16 hassasiyeti korunmalidir!"


# [KOD HÜCRESİ 3: Çıkarım Doğrulaması ve Sayısal Hassasiyet (Precision Parity & Drift)]
# Amaç: FP32 referans modeli ile FP16 modeli arasındaki sayısal farkı (Precision Drift)
# farklı sensör girdi aralıklarında ölçmek ve kosinüs benzerliğinin korunduğunu kanıtlamak.

import numpy as np
import torch

# Test Girdileri (Nominal Sensör Aralıkları)
test_inputs_np = [
    np.random.randn(1, 3, 128, 128).astype(np.float32),          # Tek çerçeve (Single frame)
    np.random.randn(4, 3, 128, 128).astype(np.float32),          # Çoklu hedef grubu (Batch=4)
    (np.random.rand(2, 3, 128, 128).astype(np.float32) - 0.5) * 4 # Geniş dinamik aralık
]

parity_metrics = []
print("[PASS] Kod 3: FP32 vs FP16 Sayisal Hassasiyet ve Parite Denetleniyor...")

for idx, x_np in enumerate(test_inputs_np):
    x_fp32 = torch.from_numpy(x_np).to(device)
    x_fp16 = x_fp32.half()
    
    with torch.no_grad():
        out_fp32 = model_fp32(x_fp32).cpu().numpy()
        out_fp16 = model_fp16(x_fp16).float().cpu().numpy() # Karşılaştırma için float32'ye cast
        
    abs_diff = np.abs(out_fp32 - out_fp16)
    max_err = float(np.max(abs_diff))
    mean_err = float(np.mean(abs_diff))
    
    # Kosinüs Benzerliği (Açısal Yönelim)
    dot_prod = np.sum(out_fp32 * out_fp16, axis=1)
    norm_fp32 = np.linalg.norm(out_fp32, axis=1)
    norm_fp16 = np.linalg.norm(out_fp16, axis=1)
    cos_sim = float(np.mean(dot_prod / (norm_fp32 * norm_fp16)))
    
    parity_metrics.append({
        'batch_shape': list(x_np.shape),
        'max_error': max_err,
        'mean_error': mean_err,
        'cos_sim': cos_sim
    })
    
    print(f"  * Test #{idx+1} {list(x_np.shape)}: Maks Hata = {max_err:.2e} | Ort Hata = {mean_err:.2e} | Kosinüs Uyumu = {cos_sim:.8f}")

max_parity_drift = max(m['max_error'] for m in parity_metrics)
min_cos_similarity = min(m['cos_sim'] for m in parity_metrics)

print(f"\n  -> En Yuksek FP16 Sapmasi (Max Drift): {max_parity_drift:.2e} (Aviyonik Limit: < 5.0e-3)")
print(f"  -> En Dusuk Kosinus Benzerligi        : {min_cos_similarity:.8f} (Hedef: > 0.9999)")

assert max_parity_drift < 5.0e-3, "FP16 mutlak sayisal sapmasi 5e-3 aviyonik esiginin altinda olmalidir!"
assert min_cos_similarity > 0.9999, "FP16 kosinus acisal yonelimi %99.99 uzerinde korunmalidir!"


# [KOD HÜCRESİ 4: 3 Askeri Uç Durum ve Savunma Güvenlik Kalkanı Testleri]
# Amaç: Aviyonik platformlarda FP16 çıkarımının getirdiği taşma ve altına taşma risklerine karşı
# 3 kritik savunma kalkanı geliştirmek ve doğrulamak:
# 1. Aşırı Parlama ve Taşma Kalkanı (FP16 Overflow & Inf Guard)
# 2. Altına Taşma ve Sıfırlanma Kalkanı (FP16 Underflow & Zero-Collapse Guard)
# 3. Karışık Hassasiyet (Mixed Precision) Açısal Normalizasyon Kalkanı (Selective FP32 Guard)

import numpy as np
import torch

# TEST 1: Aşırı Parlama ve Taşma Kalkanı (FP16 Overflow / Inf Guard)
print("[TEST 1] Asiri Parlama ve Tasmanlik Kalkani (Overflow Guard)...")

def defense_fp16_overflow_guard(input_tensor: torch.Tensor, max_val: float = 15.0) -> torch.Tensor:
    """
    Lazer karıştırıcı veya optik parlama nedeniyle gelen aşırı değerleri
    FP16'nın ara konvolüsyon katmanlarında taşma yapmasını önleyecek güvenli dinamik aralıkta [-15.0, 15.0] kırpar.
    """
    return torch.clamp(input_tensor, min=-max_val, max=max_val)

# Şok derecesinde aşırı parlak sensör verisi (örneğin 100,000 genlik)
extreme_flare_raw = torch.randn(1, 3, 128, 128, device=device) * 100000.0
# Korumasız half dönüşümü taşmaya yol açar
raw_half = extreme_flare_raw.half()
is_overflowed = torch.isinf(raw_half).any().item()

# Kalkanlı dönüşüm
safe_flare = defense_fp16_overflow_guard(extreme_flare_raw).half()
safe_has_inf = torch.isinf(safe_flare).any().item()

print(f"  - Korumasız Girdide Inf/Taşma Tespit Edildi mi? : {is_overflowed}")
print(f"  - Güvenlik Kalkanı Sonrası Inf/Taşma Var mı?    : {safe_has_inf}")

with torch.no_grad():
    out_safe = model_fp16(safe_flare)
assert not torch.isnan(out_safe).any() and not torch.isinf(out_safe).any(), "Kalkan sonrasi model ciktisinda NaN/Inf olmamalidir!"
print("  [PASS] Test 1: Asiri parlama ve tasma kalkani basariyla dogrulandi.\n")

# TEST 2: Altına Taşma ve Sıfırlanma Kalkanı (Underflow & Zero-Collapse Guard)
print("[TEST 2] Altina Tasma ve Sifirlanma Kalkani (Underflow Guard)...")

def safe_fp16_l2_normalize(features: torch.Tensor, eps_fp16: float = 1e-4) -> torch.Tensor:
    """
    FP16'da 1e-12 gibi küçük epsilon değerleri altına taşarak sıfırlanır (underflow).
    Bu fonksiyon FP16'nın sayısal çözünürlüğüne uygun eps (1e-4) kullanarak sıfıra bölmeyi engeller.
    """
    norm = torch.norm(features, p=2, dim=1, keepdim=True).clamp(min=eps_fp16)
    return features / norm

# Mikro genlikli zayıf sensör sinyali
tiny_features = torch.tensor([[1e-7, 2e-7, 0.0, 1e-8]], dtype=torch.float16, device=device)
# Korumalı normalizasyon
normed_features = safe_fp16_l2_normalize(tiny_features)
has_nan = torch.isnan(normed_features).any().item()

print(f"  - Mikro Özellikler Normlandı: {normed_features.cpu().numpy()}")
print(f"  - Çıktıda Sıfıra Bölme / NaN Oluştu mu?: {has_nan}")
assert not has_nan, "FP16 altina tasma kalkaninda asla NaN uretilmemelidir!"
print("  [PASS] Test 2: Altina tasma ve sifirlanma kalkani basariyla dogrulandi.\n")

# TEST 3: Karışık Hassasiyet (Mixed Precision) Açısal Koruma Kalkanı
print("[TEST 3] Karisik Hassasiyet (Mixed Precision) Acisal Koruma Kalkani...")

class MixedPrecisionDefenseWrapper(nn.Module):
    """
    Omurga katmanlarını FP16'da (hızlı ve az bellek) koştururken,
    kritik hedef açısal normalizasyon ve sınıflandırma başlığını FP32'de yürüten hibrit mimari.
    """
    def __init__(self, fp16_backbone: nn.Module):
        super().__init__()
        self.backbone = fp16_backbone
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Girdiyi FP16'ya al
        x_fp16 = x.half()
        # Omurga çıkarımı (FP16 Tensor Core Hızı)
        feat_fp16 = self.backbone(x_fp16)
        # Kritik normalizasyonu FP32'ye yükselt (Zero precision loss)
        feat_fp32 = feat_fp16.float()
        norm_fp32 = torch.norm(feat_fp32, p=2, dim=1, keepdim=True).clamp(min=1e-12)
        return feat_fp32 / norm_fp32

mixed_engine = MixedPrecisionDefenseWrapper(model_fp16).to(device)
x_test = torch.randn(2, 3, 128, 128, device=device)
with torch.no_grad():
    mixed_out = mixed_engine(x_test)

final_norm = torch.norm(mixed_out, p=2, dim=1).cpu().numpy()
print(f"  - Karışık Hassasiyet Çıktı Normları: {final_norm} (FP32 Hassasiyeti Korundu)")
assert np.allclose(final_norm, 1.0, atol=1e-5), "Karisik hassasiyet birim kureyi korumalidir!"
print("  [PASS] Test 3: Karisik hassasiyet koruma kalkani basariyla dogrulandi.")


# [KOD HÜCRESİ 5: FP32 vs FP16 Aviyonik Çıkarım ve Gecikme Benchmark Laboratuvarı]
# Amaç: Tek duyarlıklı (FP32) ve yarı duyarlıklı (FP16) çıkarımın gecikme (latency),
# P99 kuyruk süresi, bellek transfer hızı ve aviyonik gerçek zamanlılık bütçesini (< 1.5 ms) karşılaştırmak.

import time
import numpy as np
import torch

BENCH_ROUNDS = 200
test_x_fp32 = torch.randn(1, 3, 128, 128, dtype=torch.float32, device=device)
test_x_fp16 = test_x_fp32.half()

# 1. FP32 Çıkarım Benchmarkı
fp32_latencies = []
# Isınma (Warmup)
for _ in range(25):
    with torch.no_grad():
        _ = model_fp32(test_x_fp32)
if device.type == 'cuda':
    torch.cuda.synchronize()

for _ in range(BENCH_ROUNDS):
    if device.type == 'cuda':
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    with torch.no_grad():
        _ = model_fp32(test_x_fp32)
    if device.type == 'cuda':
        torch.cuda.synchronize()
    fp32_latencies.append((time.perf_counter() - t0) * 1000.0)

# 2. FP16 Çıkarım Benchmarkı
fp16_latencies = []
# Isınma (Warmup)
for _ in range(25):
    with torch.no_grad():
        _ = model_fp16(test_x_fp16)
if device.type == 'cuda':
    torch.cuda.synchronize()

for _ in range(BENCH_ROUNDS):
    if device.type == 'cuda':
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    with torch.no_grad():
        _ = model_fp16(test_x_fp16)
    if device.type == 'cuda':
        torch.cuda.synchronize()
    fp16_latencies.append((time.perf_counter() - t0) * 1000.0)

fp32_mean = float(np.mean(fp32_latencies))
fp32_p99 = float(np.percentile(fp32_latencies, 99))

fp16_mean = float(np.mean(fp16_latencies))
fp16_p99 = float(np.percentile(fp16_latencies, 99))
speedup = fp32_mean / fp16_mean

print(f"[FP32 vs FP16 ÇIKARIM GECİKMESİ BENCHMARK SONUÇLARI (N={BENCH_ROUNDS} Tur)]")
print(f"  * Donanım Aygıtı (Device)     : {device} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")
print(f"  * FP32 Çıkarım (Tek Duyarlık) : Ort={fp32_mean:.4f} ms | P99={fp32_p99:.4f} ms | FPS={1000.0/fp32_mean:,.1f}")
print(f"  * FP16 Çıkarım (Yarı Duyarlık): Ort={fp16_mean:.4f} ms | P99={fp16_p99:.4f} ms | FPS={1000.0/fp16_mean:,.1f}")
print(f"  * Hızlanma Çarpanı            : {speedup:.2f}x")
print(f"  * VRAM Boyut Azalması         : %{memory_saving_pct:.1f}")
print(f"  * Aviyonik Bütçe (1.5 ms)     : [{'UYGUN' if fp16_mean < 1.5 else 'ASILDI'}]")

assert fp16_mean < 1.5, "FP16 ortalama gecikmesi 1.5 ms aviyonik butcenin altinda olmalidir!"
assert fp16_p99 < 15.0, "FP16 P99 gecikmesi 15 ms altinda olmalidir!"


# [KOD HÜCRESİ 6: 4-Panelli Mühendislik Görselleştirme Gösterge Paneli]
# Amaç: IEEE 754 bit yapısını, Tensör Çekirdeği bellek tasarrufunu, sayısal hata dağılımını 
# ve FP32 vs FP16 benchmark performansını 300 DPI Dark Theme (#0F172A) ile üretmek.

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

# PANEL 1: IEEE 754 FP32 vs FP16 Bit Dağılımı ve Dinamik Aralık
ax1 = axes[0, 0]
ax1.set_title("Panel 1: IEEE 754 FP32 vs FP16 Bit Formati ve Dinamik Aralik", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)

# FP32 Çizimi (1 Sign, 8 Exp, 23 Mantissa)
ax1.text(15, 140, "FP32 (Single Precision) - 32 Bit", color='#38BDF8', fontsize=9, fontweight='bold')
r_s32 = patches.Rectangle((15, 105), 8, 25, facecolor='#EF4444', edgecolor='#334155')
r_e32 = patches.Rectangle((23, 105), 64, 25, facecolor='#F59E0B', edgecolor='#334155')
r_m32 = patches.Rectangle((87, 105), 184, 25, facecolor='#10B981', edgecolor='#334155')
ax1.add_patch(r_s32)
ax1.add_patch(r_e32)
ax1.add_patch(r_m32)
ax1.text(19, 117, "S(1)", color='#FFF', fontsize=7, ha='center', va='center')
ax1.text(55, 117, "Exponent (8 bit)", color='#000', fontsize=8, ha='center', va='center', fontweight='bold')
ax1.text(179, 117, "Mantissa / Fraction (23 bit)", color='#000', fontsize=8, ha='center', va='center', fontweight='bold')
ax1.text(15, 90, "Dinamik Aralık: 1.18e-38 ile 3.40e+38 | Hassasiyet: ~7 basamak", color='#94A3B8', fontsize=7.5)

# FP16 Çizimi (1 Sign, 5 Exp, 10 Mantissa)
ax1.text(15, 65, "FP16 (Half Precision) - 16 Bit (50% Daha Az Bellek)", color='#4ADE80', fontsize=9, fontweight='bold')
r_s16 = patches.Rectangle((15, 30), 8, 25, facecolor='#EF4444', edgecolor='#334155')
r_e16 = patches.Rectangle((23, 30), 40, 25, facecolor='#F59E0B', edgecolor='#334155')
r_m16 = patches.Rectangle((63, 30), 80, 25, facecolor='#10B981', edgecolor='#334155')
ax1.add_patch(r_s16)
ax1.add_patch(r_e16)
ax1.add_patch(r_m16)
ax1.text(19, 42, "S(1)", color='#FFF', fontsize=7, ha='center', va='center')
ax1.text(43, 42, "Exp(5)", color='#000', fontsize=7.5, ha='center', va='center', fontweight='bold')
ax1.text(103, 42, "Mantissa (10 bit)", color='#000', fontsize=8, ha='center', va='center', fontweight='bold')
ax1.text(15, 15, "Dinamik Aralık: 6.10e-05 ile 65,504 | Hassasiyet: ~3.3 basamak", color='#94A3B8', fontsize=7.5)

ax1.set_xlim(0, 290)
ax1.set_ylim(0, 165)
ax1.set_xticks([])
ax1.set_yticks([])

# PANEL 2: Tensör Çekirdekleri ve VRAM Boyut Tasarrufu
ax2 = axes[0, 1]
ax2.set_title("Panel 2: VRAM Boyut Tasarrufu ve Tensor Core Avantaji", 
              fontsize=11, fontweight='bold', color='#4ADE80', pad=10)

models_mem = ['FP32 Model\n(4B / param)', 'FP16 Model\n(2B / param)']
mem_vals = [size_fp32_kb, size_fp16_kb]
mem_cols = ['#EF4444', '#10B981']

bars2 = ax2.bar(models_mem, mem_vals, color=mem_cols, edgecolor='#334155', width=0.45)
ax2.set_ylabel("Model Bellek Boyutu (KB)", color='#94A3B8', fontsize=9)
for bar in bars2:
    h = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, h + 8, f"{h:.1f} KB", ha='center', va='bottom', color='#F1F5F9', fontsize=9, fontweight='bold')

ax2.text(0.5, 0.45, f"VRAM Kazancı: %{memory_saving_pct:.1f} Tasarruf\n"
                     f"Tensör Çekirdeği (HMMA): 2x - 4x Donanım Hızlanması\n"
                     f"Bant Genişliği: 2 Kat Daha Az DRAM Trafiği",
         transform=ax2.transAxes, fontsize=8.5, color='#FBBF24', ha='center',
         bbox=dict(boxstyle="round,pad=0.5", facecolor='#0F172A', edgecolor='#FBBF24', alpha=0.9))

# PANEL 3: Sayısal Hata ve Kosinüs Benzerliği Dağılımı
ax3 = axes[1, 0]
ax3.set_title("Panel 3: Sayisal Hassasiyet (Precision Drift) ve Aci Uyumu", 
              fontsize=11, fontweight='bold', color='#FBBF24', pad=10)

test_names = [f"Test #{i+1}" for i in range(len(parity_metrics))]
max_errs = [m['max_error'] * 1e4 for m in parity_metrics]  # 1e-4 ölçeğinde
cos_diffs = [(1.0 - m['cos_sim']) * 1e7 for m in parity_metrics] # 1e-7 ölçeğinde

x_pos = np.arange(len(test_names))
w = 0.35
b_err = ax3.bar(x_pos - w/2, max_errs, w, label='Maks Mutlak Hata (x1e-4)', color='#F59E0B', edgecolor='#334155')
b_cos = ax3.bar(x_pos + w/2, cos_diffs, w, label='Açısal Kayıp (1 - CosSim) (x1e-7)', color='#38BDF8', edgecolor='#334155')

ax3.set_xticks(x_pos)
ax3.set_xticklabels(test_names, color='#F1F5F9', fontsize=9)
ax3.set_ylabel("Hata Seviyesi (Ölçeklenmiş)", color='#94A3B8', fontsize=9)
ax3.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

for bar in b_err:
    y = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, y + 0.1, f"{y:.1f}", ha='center', va='bottom', color='#F59E0B', fontsize=8, fontweight='bold')
for bar in b_cos:
    y = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, y + 0.1, f"{y:.1f}", ha='center', va='bottom', color='#38BDF8', fontsize=8, fontweight='bold')

# PANEL 4: Çıkarım Gecikmesi, Jitter ve Aviyonik Bütçe
ax4 = axes[1, 1]
ax4.set_title("Panel 4: Cikarim Gecikmesi, Jitter ve Aviyonik Butce", 
              fontsize=11, fontweight='bold', color='#F472B6', pad=10)

bench_cats = ['FP32\n(Ortalama)', 'FP32\n(P99 Kuyruk)', 'FP16\n(Ortalama)', 'FP16\n(P99 Kuyruk)']
lat_vals = [fp32_mean, fp32_p99, fp16_mean, fp16_p99]
bench_cols = ['#EF4444', '#F59E0B', '#10B981', '#38BDF8']

bars4 = ax4.bar(bench_cats, lat_vals, color=bench_cols, edgecolor='#334155', width=0.55)
ax4.set_ylabel("Gecikme (ms) [Log Ölçek]", color='#94A3B8', fontsize=9)
ax4.set_yscale('log')
ax4.axhline(y=1.5, color='#EF4444', linestyle='--', linewidth=1.5, label='Aviyonik Limit (1.5 ms)')

for bar in bars4:
    y = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2.0, y * 1.25, f"{y:.3f}ms", 
             ha='center', va='bottom', color='#F1F5F9', fontsize=8, fontweight='bold')

ax4.text(0.5, 0.05, f"Hizlanma: {speedup:.2f}x | Maks Sapma: {max_parity_drift:.2e}", 
         transform=ax4.transAxes, fontsize=8, color='#94A3B8', ha='center',
         bbox=dict(boxstyle="round", facecolor='#0F172A', edgecolor='#334155'))
ax4.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.tight_layout()
output_png = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_272/gun_272_fp16_inference.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Gorsellestirme Basariyla Uretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")

