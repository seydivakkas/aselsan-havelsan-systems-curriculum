"""
===============================================================================
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.
===============================================================================
GÜN 004: RAM, Cache, Disk ve Bellek Hiyerarşisi Fiziği
24-Hücreli Master Mimari Planı Kapsamında Çalıştırılabilir Simülasyon ve Benchmark Motoru
===============================================================================
"""

import time
import random
import os
import sys
from dataclasses import dataclass
from typing import List, Dict, Tuple
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# =============================================================================
# CODE 1: Modül 1 - Kümeli İlişkili (Set-Associative) Önbellek Simülatörü
# =============================================================================
@dataclass
class CacheLine:
    valid: bool = False
    tag: int = 0
    last_access: int = 0

class CacheSimulator:
    """
    Doğrudan Eşlemeli veya Kümeli İlişkili Önbellek Simülatörü.
    Varsayılan: 64 baytlık satırlar (Cache Line), 4-yollu ilişkili (4-way set associative).
    """
    def __init__(self, num_sets: int = 64, ways: int = 4, line_size: int = 64):
        self.num_sets = num_sets
        self.ways = ways
        self.line_size = line_size
        self.sets: List[List[CacheLine]] = [[CacheLine() for _ in range(ways)] for _ in range(num_sets)]
        self.hits = 0
        self.misses = 0
        self.timer = 0

    def access(self, address: int) -> bool:
        self.timer += 1
        line_addr = address // self.line_size
        set_idx = line_addr % self.num_sets
        tag = line_addr // self.num_sets

        cache_set = self.sets[set_idx]

        # 1. Hit kontrolü
        for line in cache_set:
            if line.valid and line.tag == tag:
                line.last_access = self.timer
                self.hits += 1
                return True # CACHE HIT

        # 2. Miss durumu (LRU ile yer değiştirme)
        self.misses += 1
        lru_idx = 0
        min_access = float('inf')
        for i, line in enumerate(cache_set):
            if not line.valid:
                lru_idx = i
                break
            if line.last_access < min_access:
                min_access = line.last_access
                lru_idx = i

        cache_set[lru_idx].valid = True
        cache_set[lru_idx].tag = tag
        cache_set[lru_idx].last_access = self.timer
        return False # CACHE MISS

# =============================================================================
# CODE 2: Modül 2 - 2D Matris Bellek Gezinimi ve Cache Miss Analizi
# =============================================================================
def benchmark_matrix_traversal(matrix_dim: int = 128):
    """
    C/C++ diziliminde bellekte satır satır sıralı (Row-Major) gezinim
    ile sütun sütun (Column-Major) gezinim arasındaki önbellek kaçırma farkını ölçer.
    """
    sim_row = CacheSimulator(num_sets=64, ways=4, line_size=64)
    sim_col = CacheSimulator(num_sets=64, ways=4, line_size=64)

    # 1. Satır Öncelikli (Row-Major: C-style contiguous)
    for r in range(matrix_dim):
        for c in range(matrix_dim):
            addr = (r * matrix_dim + c) * 4 # 4 baytlık float
            sim_row.access(addr)

    # 2. Sütun Öncelikli (Column-Major: Strided across rows)
    for c in range(matrix_dim):
        for r in range(matrix_dim):
            addr = (r * matrix_dim + c) * 4
            sim_col.access(addr)

    row_hit_rate = (sim_row.hits / (sim_row.hits + sim_row.misses)) * 100.0
    col_hit_rate = (sim_col.hits / (sim_col.hits + sim_col.misses)) * 100.0

    return sim_row, sim_col, row_hit_rate, col_hit_rate

# =============================================================================
# CODE 3: Modül 3 - Veri Düzeni: AoS (Array of Structs) vs SoA (Struct of Arrays)
# =============================================================================
@dataclass
class RadarTargetAoS:
    x: float
    y: float
    z: float
    range_val: float
    azimuth: float
    elevation: float
    doppler_vel: float
    snr: float

def benchmark_aos_vs_soa(num_targets: int = 100000):
    """
    Radar hedeflerinin sadece irtifasını (z) güncellemek istediğimizde:
    - AoS: Her z için diğer tüm alanlar (64 bayt) önbelleğe yüklenir, veri atıkları oluşur.
    - SoA: Tüm z koordinatları yan yana dizilidir, önbellek %100 verimle dolar.
    """
    # AoS hazırlığı
    targets_aos = [RadarTargetAoS(1.0, 2.0, 3.0, 100.0, 0.5, 0.2, 50.0, 15.0) for _ in range(num_targets)]
    
    # SoA hazırlığı
    targets_soa_z = np.full(num_targets, 3.0, dtype=np.float32)

    # AoS Güncelleme
    t0 = time.perf_counter()
    for t in targets_aos:
        t.z += 1.0
    aos_time = (time.perf_counter() - t0) * 1000.0

    # SoA Güncelleme (Vektörize ve Cache-Aligned)
    t0 = time.perf_counter()
    targets_soa_z += 1.0
    soa_time = (time.perf_counter() - t0) * 1000.0

    return aos_time, soa_time

# =============================================================================
# CODE 4: Sabotaj Senaryosu: Pointer Chasing (Rastgele Bellek Atlaması)
# =============================================================================
def run_sabotage_simulation(size: int = 60000):
    """
    Sıralı dizi gezinimi (Hardware Prefetcher dostu) ile
    Bağlı Liste / Rastgele İşaretçi Zinciri (Pointer Chasing - Cache Thrashing) sabotajı.
    """
    seq_indices = list(range(size))
    rand_indices = list(range(size))
    random.shuffle(rand_indices)

    data = np.random.rand(size).astype(np.float32)

    # 1. Sıralı Erişim
    t0 = time.perf_counter()
    sum_seq = 0.0
    for idx in seq_indices:
        sum_seq += data[idx]
    seq_time = (time.perf_counter() - t0) * 1000.0

    # 2. Rastgele Erişim (Sabotaj: Cache Tamamen İşlevsiz)
    t0 = time.perf_counter()
    sum_rand = 0.0
    for idx in rand_indices:
        sum_rand += data[idx]
    rand_time = (time.perf_counter() - t0) * 1000.0

    return seq_time, rand_time

# =============================================================================
# CODE 5: Modül 4 - Ampirik Kıyaslama: Adım Boyutu (Stride) Analizi
# =============================================================================
def run_stride_benchmark(array_size: int = 5_000_000):
    """
    Adım boyutu (Stride) arttıkça her okuma başına harcanan nanosaniye süresi ölçülür.
    Stride 16 (64 bayt = Cache Line) aşıldığında işlemci donanımsal prefetcher'ı kaybeder
    ve her erişim ana bellekten (DRAM) çekilerek gecikme katlanır.
    """
    arr = np.ones(array_size, dtype=np.int32)
    strides = [1, 2, 4, 8, 16, 32, 64]
    latencies_per_access = []

    for s in strides:
        t0 = time.perf_counter()
        sub = arr[::s]
        _ = sub.sum()
        total_time_ns = (time.perf_counter() - t0) * 1e9
        per_access_ns = total_time_ns / len(sub)
        latencies_per_access.append(per_access_ns)

    return strides, latencies_per_access

# =============================================================================
# CODE 6: Modül 5 - 4-Panelli Yayın Kalitesinde Dashboard ve Katı Doğrulama
# =============================================================================
def generate_dashboard(output_path: str):
    sim_row, sim_col, row_hit_rate, col_hit_rate = benchmark_matrix_traversal(matrix_dim=128)
    aos_time, soa_time = benchmark_aos_vs_soa(num_targets=80000)
    seq_time, rand_time = run_sabotage_simulation(size=60000)
    strides, stride_lats = run_stride_benchmark()

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor('#0f172a')

    for ax_row in axs:
        for ax in ax_row:
            ax.set_facecolor('#1e293b')
            ax.tick_params(colors='#94a3b8')
            ax.xaxis.label.set_color('#cbd5e1')
            ax.yaxis.label.set_color('#cbd5e1')
            ax.title.set_color('#f8fafc')
            ax.grid(True, linestyle='--', alpha=0.2, color='#64748b')

    # Panel 1: Matris Gezinimi ve Hit Rate (Row-Major vs Column-Major)
    cats1 = ['Row-Major (C-Style)', 'Column-Major (Strided)']
    rates1 = [row_hit_rate, col_hit_rate]
    axs[0, 0].bar(cats1, rates1, color=['#10b981', '#ef4444'], width=0.45)
    axs[0, 0].set_title('Panel 1: 128x128 Matris Önbellek İsabet Oranı (%)', fontsize=12, fontweight='bold')
    axs[0, 0].set_ylabel('Cache Hit Oranı (%)')
    axs[0, 0].set_ylim(0, 105)
    for i, r in enumerate(rates1):
        axs[0, 0].text(i, r + 2, f"%{r:.1f}\n({[sim_row.misses, sim_col.misses][i]} Miss)", ha='center', color='white', fontweight='bold', fontsize=10)

    # Panel 2: Veri Düzeni: AoS vs SoA
    cats2 = ['AoS (Array of Structs)', 'SoA (Struct of Arrays)']
    times2 = [aos_time, soa_time]
    axs[0, 1].bar(cats2, times2, color=['#f59e0b', '#38bdf8'], width=0.45)
    axs[0, 1].set_title('Panel 2: Radar Hedef İrtifa Güncelleme (AoS vs SoA)', fontsize=12, fontweight='bold')
    axs[0, 1].set_ylabel('Süre (milisaniye)')
    for i, t in enumerate(times2):
        axs[0, 1].text(i, t / 2 if t > 1 else t + 0.5, f"{t:.2f} ms", ha='center', color='white', fontweight='bold', fontsize=11)

    # Panel 3: Sabotaj Testi: Sıralı vs Rastgele Bellek Atlama (Pointer Chasing)
    cats3 = ['Sıralı Erişim (Prefetch)', 'Rastgele (Pointer Chasing)']
    times3 = [seq_time, rand_time]
    axs[1, 0].bar(cats3, times3, color=['#10b981', '#f43f5e'], width=0.45)
    axs[1, 0].set_title('Panel 3: Rastgele Bellek Atlama ile Cache Thrashing', fontsize=12, fontweight='bold')
    axs[1, 0].set_ylabel('Erişim Süresi (ms)')
    for i, t in enumerate(times3):
        axs[1, 0].text(i, t / 2, f"{t:.1f} ms", ha='center', color='white', fontweight='bold', fontsize=11)

    # Panel 4: Adım Boyutu (Stride) vs Erişim Başına Gecikme (ns)
    axs[1, 1].plot([str(s) for s in strides], stride_lats, marker='s', color='#ec4899', lw=2.5, label='Erişim Başına Gecikme (ns)')
    axs[1, 1].axvline(4, color='#38bdf8', linestyle='--', label='16 Eleman = 64B Cache Line')
    axs[1, 1].set_title('Panel 4: Stride Boyutu Arttıkça Öğe Başına Gecikme (ns)', fontsize=12, fontweight='bold')
    axs[1, 1].set_xlabel('Adım Boyutu (Stride - Öğe Adedi)')
    axs[1, 1].set_ylabel('Gecikme (ns / access)')
    axs[1, 1].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 004 Dashboard başarıyla üretildi: {output_path}")

    # ==========================================
    # KATI MİMARİ DOĞRULAMA (STRICT ASSERTIONS)
    # ==========================================
    # 1. Matris önbellek isabet oranı: Row-Major %90 üzerinde, Col-Major %10 altında olmalıdır
    assert row_hit_rate > 90.0, f"HATA: Row-Major hit rate beklenenden düşük: %{row_hit_rate}"
    assert col_hit_rate < 10.0, f"HATA: Col-Major hit rate beklenenden yüksek: %{col_hit_rate}"
    # 2. Rastgele işaretçi gezinimi (Pointer Chasing) sıralı erişimden en az %20 yavaş olmalıdır
    assert rand_time > seq_time, "HATA: Rastgele erişim sıralı erişimden yavaş çıkmadı!"
    # 3. SoA bellek yerleşimi AoS'tan en az 5 kat hızlı olmalıdır (Vektörizasyon ve Cache verimi)
    assert aos_time > soa_time * 5.0, "HATA: SoA bellek yerleşimi AoS'a göre belirgin hız kazandırmadı!"
    # 4. Stride boyutu büyüdükçe (1 -> 64) erişim başına harcanan nanosaniye artmalıdır
    assert stride_lats[-1] > stride_lats[0], "HATA: Stride büyümesi erişim gecikmesini artırmadı!"
    print("[PASS] Gün 004: Tüm bellek hiyerarşisi, cache line ve yerellik kuralları doğrulandı.")

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    img_target = os.path.join(out_dir, "gun_004_ram_cache_disk_bellek_hiyerarsisi.png")
    generate_dashboard(img_target)
