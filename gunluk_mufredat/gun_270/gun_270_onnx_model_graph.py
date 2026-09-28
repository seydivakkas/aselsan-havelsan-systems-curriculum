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
GÜN 270: ONNX Model Graph ve Hesaplama Çizgesi Mimarisi
6 Kod Hücresinin Birleşik Standalone Çalıştırılabilir Betiği
"""

# [KOD HÜCRESİ 1: Taktik Algılama Omurgası (Backbone) ve ONNX İhracı]
# Amaç: PyTorch üzerinde tanımlanan taktik elektro-optik hedef algılama modelini
# dinamik eksenlerle (dynamic_axes) standart bir ONNX hesaplama çizgesine ihraç etmek.

import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import onnx

class TacticalPerceptionBackbone(nn.Module):
    """Aviyonik elektro-optik gimbal podu hedef özellik çıkarıcı omurgası."""
    def __init__(self, num_classes: int = 5):
        super().__init__()
        # Katman 1: Konvolüsyon + Batch Normalization + LeakyReLU
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(16)
        
        # Katman 2: Derin Konvolüsyon + Batch Normalization + LeakyReLU
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(32)
        
        # Katman 3: Global Ortalama Havuzlama (Spatial Reduction)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        
        # Katman 4: Sınıflandırma ve Embedding Başlığı
        self.fc = nn.Linear(32, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Blok 1: [B, 3, H, W] -> [B, 16, H/2, W/2]
        x = F.leaky_relu(self.bn1(self.conv1(x)), negative_slope=0.1)
        # Blok 2: [B, 16, H/2, W/2] -> [B, 32, H/4, W/4]
        x = F.leaky_relu(self.bn2(self.conv2(x)), negative_slope=0.1)
        # Havuzlama: [B, 32, 1, 1] -> [B, 32]
        x = self.pool(x)
        x = torch.flatten(x, 1)
        # Projeksiyon ve L2 Normalizasyonu
        logits = self.fc(x)
        embedding = F.normalize(logits, p=2, dim=-1)
        return embedding

# Model Başlatma ve Eval Moduna Alma
torch.manual_seed(42)
tactical_model = TacticalPerceptionBackbone(num_classes=5).eval()

# Örnek Giriş Tensörü (FLIR Çerçevesi Simülasyonu: [1, 3, 64, 64])
dummy_input = torch.randn(1, 3, 64, 64, dtype=torch.float32)

# ONNX Çıktı Dosyası Yolu
ONNX_FILE_PATH = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_270/gun_270_model.onnx"

# PyTorch'tan ONNX'e İhraç (TorchScript Symbolic Tracer)
torch.onnx.export(
    tactical_model,
    dummy_input,
    ONNX_FILE_PATH,
    export_params=True,
    opset_version=18,
    do_constant_folding=True,
    input_names=['sensor_input'],
    output_names=['tactical_embedding'],
    dynamic_axes={
        'sensor_input': {0: 'batch_size', 2: 'frame_height', 3: 'frame_width'},
        'tactical_embedding': {0: 'batch_size'}
    },
    dynamo=False
)

# ONNX Şema ve DAG Doğrulaması
onnx_model = onnx.load(ONNX_FILE_PATH)
onnx.checker.check_model(onnx_model)

print("[PASS] Kod 1: Taktik Algilama Modeli ONNX Cizgesine Basariyla Ihrac Edildi.")
print(f"  - Kaydedilen Dosya  : {ONNX_FILE_PATH}")
print(f"  - Dosya Boyutu      : {os.path.getsize(ONNX_FILE_PATH):,} bayt")
print(f"  - IR Versiyonu      : {onnx_model.ir_version}")
print(f"  - Opset Versiyonu   : {onnx_model.opset_import[0].version}")
print(f"  - Producer Adi      : {onnx_model.producer_name}")

assert os.path.exists(ONNX_FILE_PATH), "ONNX modeli diske yazilmis olmalidir!"
assert onnx_model.ir_version >= 8, "Guncel ONNX IR versiyonu kullanilmalidir!"


# [KOD HÜCRESİ 2: ONNX Model Grafiği (DAG) Ayrıştırma ve Topolojik İnceleme]
# Amaç: ONNX Protocol Buffers nesnesini programatik olarak ayrıştırıp
# düğümleri (nodes), parametre tensörlerini (initializers) ve girdi/çıktıları listelemek.

import onnx
from collections import Counter

# ONNX Modelini Yükle
onnx_model = onnx.load(ONNX_FILE_PATH)
graph = onnx_model.graph

print(f"[PASS] Kod 2: ONNX Hesaplama Cizgesi (DAG) Ayristiriliyor...")
print(f"  - Cizge Adi (Graph Name): {graph.name}")
print(f"  - Toplam Dugum (Node) Sayisi: {len(graph.node)}")
print(f"  - Agirlik Tensor (Initializer) Sayisi: {len(graph.initializer)}")

# 1. Girdi ve Çıktı İmzaları
print("\n--- Girdi ve Cikti Tensor Imzalari ---")
for inp in graph.input:
    shape_dims = [dim.dim_param or dim.dim_value for dim in inp.type.tensor_type.shape.dim]
    print(f"  * GIRDI : Name='{inp.name}', Type={inp.type.tensor_type.elem_type}, Dims={shape_dims}")

for out in graph.output:
    shape_dims = [dim.dim_param or dim.dim_value for dim in out.type.tensor_type.shape.dim]
    print(f"  * CIKTI : Name='{out.name}', Type={out.type.tensor_type.elem_type}, Dims={shape_dims}")

# 2. Operatör Tipleri ve Dağılımı
op_counts = Counter([node.op_type for node in graph.node])
print("\n--- Operator Tipi Histogrami ---")
for op_type, count in op_counts.most_common():
    print(f"  - {op_type:<20s} : {count} adet")

# 3. Parametre Boyutu Analizi
total_params = 0
for init in graph.initializer:
    dims = list(init.dims)
    param_count = 1
    for d in dims:
        param_count *= d
    total_params += param_count

print(f"\n  -> Toplam Agirlik Parametre Sayisi: {total_params:,} parametre ({total_params * 4 / 1024:.2f} KB FP32)")

assert len(graph.node) >= 6, "Cizgede en az 6 hesaplama dugumu bulunmalidir!"
assert 'Conv' in op_counts, "Model en az bir Conv dugumu icermelidir!"
assert total_params > 1000, "Agirlik tensorleri dogru yuklenmis olmalidir!"


# [KOD HÜCRESİ 3: ONNX Runtime Çıkarımı ve PyTorch Sayısal Parite Doğrulaması]
# Amaç: PyTorch Eager modu ile ONNX Runtime C++ çıkarım motoru arasındaki
# sayısal farkı (precision parity) ölçmek; |y_torch - y_ort| < 1e-5 olduğunu kanıtlamak.

import numpy as np
import torch
import onnxruntime as ort

# ONNX Runtime Çıkarım Oturumu (InferenceSession) Başlatma
session_options = ort.SessionOptions()
session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
ort_session = ort.InferenceSession(ONNX_FILE_PATH, session_options, providers=['CPUExecutionProvider'])

# Çoklu Batch ve Dinamik Boyut Test Girdileri
test_batches = [
    torch.randn(1, 3, 64, 64, dtype=torch.float32),
    torch.randn(4, 3, 64, 64, dtype=torch.float32),
    torch.randn(2, 3, 96, 96, dtype=torch.float32)  # Farklı çözünürlük
]

print("[PASS] Kod 3: ONNX Runtime Cikarimi ve Sayisal Parite Test Ediliyor...")

parity_results = []
for idx, x_tensor in enumerate(test_batches):
    # 1. PyTorch Çıkarımı
    with torch.no_grad():
        torch_out = tactical_model(x_tensor).cpu().numpy()
        
    # 2. ONNX Runtime Çıkarımı
    ort_inputs = {'sensor_input': x_tensor.numpy()}
    ort_out = ort_session.run(None, ort_inputs)[0]
    
    # 3. Hata Metrikleri
    abs_diff = np.abs(torch_out - ort_out)
    max_err = float(np.max(abs_diff))
    mean_err = float(np.mean(abs_diff))
    
    # Kosinüs Benzerliği (Açısal Uyum)
    cos_sim = np.sum(torch_out * ort_out, axis=1) / (np.linalg.norm(torch_out, axis=1) * np.linalg.norm(ort_out, axis=1))
    min_cos_sim = float(np.min(cos_sim))
    
    parity_results.append({
        'batch': x_tensor.shape,
        'max_error': max_err,
        'mean_error': mean_err,
        'cos_sim': min_cos_sim
    })
    
    print(f"  - Test #{idx+1} Girdi Sekli: {list(x_tensor.shape)}")
    print(f"    Maksimum Mutlak Hata: {max_err:.2e} | Ortalama Hata: {mean_err:.2e} | Kosinus Uyumu: {min_cos_sim:.8f}")

# En Yüksek Hatayı Doğrula
highest_error = max([r['max_error'] for r in parity_results])
assert highest_error < 1e-5, f"Sayisal parite hatasi 1e-5 altinda olmalidir! (Mevcut: {highest_error})"
print(f"\n  -> En Yuksek Parite Hatasi: {highest_error:.2e} (Mukemmel Sayisal Uyum!)")


# [KOD HÜCRESİ 4: 3 Askeri Uç Durum ve Savunma Güvenlik Kalkanı Testleri]
# Amaç: Dinamik tensör boyutu uyuşmazlığı, bozuk/geçersiz hesaplama çizgesi 
# ve sayısal taşma (numerical drift) durumlarında güvenlik kalkanlarını doğrulamak.

import numpy as np
import onnx
import onnxruntime as ort

# TEST 1: Uyumsuz Kanal / Boyut Kalkanı (Input Shape & Dimension Guard)
print("[TEST 1] Uyumsuz Girdi Kanali ve Statik Boyut Kalkani...")
# Yanlışlıkla 1 kanallı termal gri görüntü gönderilmiş (Model 3 kanal bekliyor)
invalid_channel_input = np.random.randn(1, 1, 64, 64).astype(np.float32)

def safe_sensor_input_adapter(raw_frame: np.ndarray, expected_channels: int = 3) -> np.ndarray:
    """Gelen ham sensör çerçevesini modelin beklediği NCHW tensör formatına güvenle adapte eder."""
    if raw_frame.ndim == 3: # HWC formatı gelmişse
        raw_frame = np.transpose(raw_frame, (2, 0, 1))[None, :]
    elif raw_frame.ndim == 4 and raw_frame.shape[1] == 1 and expected_channels == 3:
        # Tek kanallı FLIR görüntüsünü 3 kanala çoğalt (Monochrome to 3-Channel)
        raw_frame = np.repeat(raw_frame, 3, axis=1)
    return raw_frame

adapted_input = safe_sensor_input_adapter(invalid_channel_input, expected_channels=3)
assert adapted_input.shape[1] == 3, "Kanal sayisi basariyla 3'e adapte edilmelidir!"

# ONNX Runtime'da test et
out_adapted = ort_session.run(None, {'sensor_input': adapted_input})[0]
assert out_adapted.shape == (1, 5), "Adapte edilen girdi basariyla calistirilmalidir!"
print(f"  - Hatali Giris: (1, 1, 64, 64) -> Adapte Edilen: {adapted_input.shape} -> Cikti: {out_adapted.shape}")
print("  [PASS] Test 1: Sensor girdi adaptasyon kalkani basariyla dogrulandi.\n")

# TEST 2: Çizge Doğrulama ve Bozuk Düğüm Kalkanı (Model Graph Integrity Guard)
print("[TEST 2] Cizge Dogrulama ve Bozuk Dugum / Kopuk Kenar Kalkani...")
# Bilinçli olarak bozulmuş bir ONNX modeli simüle et
corrupted_model = onnx.load(ONNX_FILE_PATH)
# İlk düğümün girdi adını var olmayan bir hayalet tensörle değiştir
corrupted_model.graph.node[0].input[0] = "hayalet_olmayan_tensor"

is_graph_broken = False
try:
    onnx.checker.check_model(corrupted_model)
except onnx.checker.ValidationError as e:
    is_graph_broken = True
    print(f"  - Beklenen Guvenlik Uyarisi Yakalandi: {str(e)[:75]}...")

assert is_graph_broken, "Bozuk cizge onnx.checker tarafindan kesinlikle yakalanmalidir!"
print("  [PASS] Test 2: ONNX Cizge Butunlugu kalkani basariyla dogrulandi.\n")

# TEST 3: Dejenere Aktivasyon ve Norm Kararlılık Kalkanı (Numerical Precision Guard)
print("[TEST 3] Sayisal Hassasiyet ve Norm Kararlilik Kalkani...")
# Dejenere aşırı büyük girdi
extreme_input = np.random.randn(2, 3, 64, 64).astype(np.float32) * 500.0

out_extreme = ort_session.run(None, {'sensor_input': extreme_input})[0]
# Çıktı L2 normunun 1.0 olduğunu doğrula
out_norms = np.linalg.norm(out_extreme, axis=1)

assert not np.any(np.isnan(out_extreme)), "Asiri buyuk girdilerde NaN uretilmemelidir!"
assert np.allclose(out_norms, 1.0, atol=1e-4), "L2 normalizasyonu birim kureyi korumalidir!"
print(f"  - Asiri Girdi Aktivasyonunda Normlar: {out_norms} (Birim Kure Korundu)")
print("  [PASS] Test 3: Sayisal kararlilik kalkani basariyla dogrulandi.")


# [KOD HÜCRESİ 5: PyTorch Eager vs ONNX Runtime Aviyonik Çıkarım Benchmark Laboratuvarı]
# Amaç: PyTorch Eager modu ile ONNX Runtime C++ çıkarım motorunun gecikme (latency),
# P99 zamanlaması ve aviyonik gerçek zamanlılık bütçesini (< 2.0 ms) karşılaştırmak.

import time
import numpy as np
import torch

BENCH_ROUNDS = 200
test_x = torch.randn(1, 3, 64, 64, dtype=torch.float32)
test_x_np = test_x.numpy()

# 1. PyTorch Eager Modu Benchmarkı
torch_latencies = []
# Isınma (Warmup)
for _ in range(25):
    with torch.no_grad():
        _ = tactical_model(test_x)

for _ in range(BENCH_ROUNDS):
    t0 = time.perf_counter()
    with torch.no_grad():
        _ = tactical_model(test_x)
    torch_latencies.append((time.perf_counter() - t0) * 1000.0)

# 2. ONNX Runtime Benchmarkı
ort_latencies = []
# Isınma (Warmup)
for _ in range(25):
    _ = ort_session.run(None, {'sensor_input': test_x_np})

for _ in range(BENCH_ROUNDS):
    t0 = time.perf_counter()
    _ = ort_session.run(None, {'sensor_input': test_x_np})
    ort_latencies.append((time.perf_counter() - t0) * 1000.0)

torch_mean = float(np.mean(torch_latencies))
torch_p99 = float(np.percentile(torch_latencies, 99))

ort_mean = float(np.mean(ort_latencies))
ort_p99 = float(np.percentile(ort_latencies, 99))
speedup = torch_mean / ort_mean

print(f"[CIKARIM GECIKMESI BENCHMARK SONUCLARI (N={BENCH_ROUNDS} Tur)]")
print(f"  * PyTorch Eager Modu : Ort={torch_mean:.4f} ms | P99={torch_p99:.4f} ms | FPS={1000.0/torch_mean:,.1f}")
print(f"  * ONNX Runtime (CPU) : Ort={ort_mean:.4f} ms | P99={ort_p99:.4f} ms | FPS={1000.0/ort_mean:,.1f}")
print(f"  * Hizlanma Carpani   : {speedup:.2f}x daha hizli")
print(f"  * Aviyonik Butce (2.0 ms): [{'UYGUN' if ort_mean < 2.0 else 'ASILDI'}]")

assert ort_mean < 2.0, "ONNX Runtime ortalama gecikmesi 2.0 ms aviyonik butcenin altinda olmalidir!"
assert ort_p99 < 15.0, "ONNX Runtime P99 gecikmesi 15 ms altinda olmalidir!"


# [KOD HÜCRESİ 6: 4-Panelli Mühendislik Görselleştirme Gösterge Paneli]
# Amaç: ONNX model çizge mimarisini, DAG topolojisini, operatör dağılımını 
# ve PyTorch-ONNX sayısal parite analizini 300 DPI Dark Theme (#0F172A) ile üretmek.

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

# PANEL 1: PyTorch'tan TensorRT'ye ONNX İhraç ve Dönüşüm Boru Hattı
ax1 = axes[0, 0]
ax1.set_title("Panel 1: PyTorch'tan TensorRT'ye ONNX Model Graph Donusum Hatti", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)

# Blok Kutuları
# 1. PyTorch
r1 = patches.FancyBboxPatch((15, 80), 60, 50, boxstyle="round,pad=3",
                            linewidth=2, edgecolor='#EF4444', facecolor='#0F172A')
ax1.add_patch(r1)
ax1.text(45, 105, "PyTorch Model\n(Eager Mode)\nPython/C++", color='#EF4444', 
         ha='center', va='center', fontsize=8, fontweight='bold')

# 2. Symbolic Tracer
r2 = patches.FancyBboxPatch((90, 80), 60, 50, boxstyle="round,pad=3",
                            linewidth=2, edgecolor='#F59E0B', facecolor='#0F172A')
ax1.add_patch(r2)
ax1.text(120, 105, "torch.onnx.export\n(Symbolic Tracer)\nOpset 18", color='#F59E0B', 
         ha='center', va='center', fontsize=8, fontweight='bold')

# 3. ONNX Model Graph
r3 = patches.FancyBboxPatch((165, 75), 65, 60, boxstyle="round,pad=3",
                            linewidth=2.5, edgecolor='#4ADE80', facecolor='#0F172A')
ax1.add_patch(r3)
ax1.text(197, 105, "ONNX Graph\n(DAG Protobuf)\nNodes + Tensors\n+ Dynamic Axes", color='#4ADE80', 
         ha='center', va='center', fontsize=8, fontweight='bold')

# 4. TensorRT Builder
r4 = patches.FancyBboxPatch((245, 80), 60, 50, boxstyle="round,pad=3",
                            linewidth=2, edgecolor='#818CF8', facecolor='#0F172A')
ax1.add_patch(r4)
ax1.text(275, 105, "TensorRT Engine\n(CUDA Kernels)\nFP16 / INT8 PTQ", color='#818CF8', 
         ha='center', va='center', fontsize=8, fontweight='bold')

# Oklar
ax1.annotate('', xy=(90, 105), xytext=(75, 105), arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2))
ax1.annotate('', xy=(165, 105), xytext=(150, 105), arrowprops=dict(arrowstyle="->", color='#4ADE80', lw=2))
ax1.annotate('', xy=(245, 105), xytext=(230, 105), arrowprops=dict(arrowstyle="->", color='#818CF8', lw=2))

ax1.text(197, 35, "Evrensel Donanim-Bagimsiz Ara Temsil (IR):\nCPU, CUDA, Jetson Orin, NPU, FPGA", 
         color='#FBBF24', fontsize=8, fontweight='bold', ha='center',
         bbox=dict(boxstyle="round", facecolor='#1E293B', edgecolor='#FBBF24', alpha=0.8))

ax1.set_xlim(0, 320)
ax1.set_ylim(0, 210)
ax1.set_xticks([])
ax1.set_yticks([])

# PANEL 2: Taktik Hesaplama Çizgesi (DAG) Topolojisi
ax2 = axes[0, 1]
ax2.set_title("Panel 2: Taktik Algilama Hesaplama Cizgesi (DAG Topolojisi)", 
              fontsize=11, fontweight='bold', color='#4ADE80', pad=10)

layers = [
    ("Girdi Tensörü", "sensor_input: [B, 3, H, W]", "#38BDF8"),
    ("Conv1 + BN1", "16 filtre (3x3, s=2) + LeakyReLU", "#818CF8"),
    ("Conv2 + BN2", "32 filtre (3x3, s=2) + LeakyReLU", "#818CF8"),
    ("Global Havuz", "AdaptiveAvgPool2d -> [B, 32, 1, 1]", "#A855F7"),
    ("Flatten + Gemm", "Linear(32, 5) -> [B, 5]", "#F59E0B"),
    ("L2 Normalizasyon", "tactical_embedding: [B, 5]", "#22C55E")
]

y_pos = np.linspace(180, 25, len(layers))
for idx, ((name, desc, col), y) in enumerate(zip(layers, y_pos)):
    r = patches.FancyBboxPatch((30, y-10), 220, 22, boxstyle="round,pad=2",
                               linewidth=1.5, edgecolor=col, facecolor='#0F172A')
    ax2.add_patch(r)
    ax2.text(45, y+1, f"{name}:", color=col, fontsize=8, fontweight='bold')
    ax2.text(125, y+1, desc, color='#F1F5F9', fontsize=7)
    if idx < len(layers) - 1:
        ax2.annotate('', xy=(140, y-10), xytext=(140, y_pos[idx+1]+12),
                     arrowprops=dict(arrowstyle="<-", color='#64748B', lw=1.5))

ax2.set_xlim(0, 280)
ax2.set_ylim(0, 210)
ax2.set_xticks([])
ax2.set_yticks([])

# PANEL 3: ONNX Operatör Dağılımı ve Katman Analizi
ax3 = axes[1, 0]
ax3.set_title("Panel 3: ONNX Cizgesindeki Operator Dagilimi", 
              fontsize=11, fontweight='bold', color='#FBBF24', pad=10)

op_names = list(op_counts.keys())
op_vals = list(op_counts.values())
bar_colors = ['#38BDF8', '#818CF8', '#A855F7', '#F59E0B', '#10B981', '#EC4899', '#64748B']

bars3 = ax3.barh(op_names, op_vals, color=bar_colors[:len(op_names)], edgecolor='#334155', height=0.6)
ax3.set_xlabel("Operator Dugum Sayisi (Adet)", color='#94A3B8', fontsize=9)
for bar in bars3:
    w = bar.get_width()
    ax3.text(w + 0.08, bar.get_y() + bar.get_height()/2.0, f"{int(w)} adet", 
             ha='left', va='center', color='#F1F5F9', fontsize=8, fontweight='bold')

ax3.set_xlim(0, max(op_vals) + 1.2)

# PANEL 4: PyTorch vs ONNX Runtime Sayısal Parite ve Gecikme
ax4 = axes[1, 1]
ax4.set_title("Panel 4: Cikarim Gecikmesi ve Sayisal Parite Analizi", 
              fontsize=11, fontweight='bold', color='#F472B6', pad=10)

categories = ['PyTorch Eager\n(Ortalama)', 'PyTorch Eager\n(P99)', 'ONNX Runtime\n(Ortalama)', 'ONNX Runtime\n(P99)']
times = [torch_mean, torch_p99, ort_mean, ort_p99]
t_colors = ['#EF4444', '#F59E0B', '#10B981', '#38BDF8']

bars4 = ax4.bar(categories, times, color=t_colors, edgecolor='#334155', width=0.55)
ax4.set_ylabel("Cikarim Suresi (ms)", color='#94A3B8', fontsize=9)
ax4.set_yscale('log')
ax4.axhline(y=2.0, color='#EF4444', linestyle='--', linewidth=1.5, label='Aviyonik Limit (2.0 ms)')

for bar in bars4:
    yval = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval * 1.25, f"{yval:.3f}ms", 
             ha='center', va='bottom', color='#F1F5F9', fontsize=8, fontweight='bold')

ax4.text(0.5, 0.05, f"Maksimum Parite Hatasi: {highest_error:.2e} | Hizlanma: {speedup:.2f}x", 
         transform=ax4.transAxes, fontsize=8, color='#94A3B8', ha='center',
         bbox=dict(boxstyle="round", facecolor='#0F172A', edgecolor='#334155'))
ax4.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.tight_layout()
output_png = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_270/gun_270_onnx_model_graph.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Gorsellestirme Basariyla Uretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")


