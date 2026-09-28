# -*- coding: utf-8 -*-
# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
# amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz.


# -*- coding: utf-8 -*-
"""
HÜCRE 04 (CODE 1): Python ile Donanımsal PMU Sayacı ve Sampling Simülatörü
CPU Saat Döngüleri, Instructions, IPC Hesabı, Cache Miss ve PMI Kesme Mekanizması
"""

import numpy as np
from typing import Dict, Any, List

class SimulatedPmuCore:
    """İşlemci donanımsal PMU (Performance Monitoring Unit) simülatörü."""
    
    def __init__(self, sample_period_cycles: int = 100000):
        self.sample_period = sample_period_cycles
        self.total_cycles: int = 0
        self.total_instructions: int = 0
        self.cache_references: int = 0
        self.cache_misses: int = 0
        self.branch_instructions: int = 0
        self.branch_misses: int = 0
        
        # Sampling ile yakalanan çağrı yığını profili: {fonksiyon_adı: numune_sayısı}
        self.samples: Dict[str, int] = {}
        self.cycle_counter: int = 0

    def execute_block(self, func_name: str, instructions: int, cache_miss_prob: float, branch_miss_prob: float):
        """Bir fonksiyon bloğunun yürütülmesini ve donanım sayaçlarının artışını simüle eder."""
        # Her komut baz 1 döngü sürer; her cache miss +150 döngü, her branch miss +20 döngü ekler
        mem_misses = int(instructions * cache_miss_prob)
        br_misses = int((instructions * 0.15) * branch_miss_prob) # Komutların %15'i dallanma
        
        stall_cycles = (mem_misses * 150) + (br_misses * 20)
        executed_cycles = instructions + stall_cycles

        self.total_instructions += instructions
        self.total_cycles += executed_cycles
        self.cache_references += int(instructions * 0.4) # %40 bellek okuma/yazma
        self.cache_misses += mem_misses
        self.branch_instructions += int(instructions * 0.15)
        self.branch_misses += br_misses

        # Donanımsal PMU Sampling Kesmesi (PMI)
        self.cycle_counter += executed_cycles
        while self.cycle_counter >= self.sample_period:
            self.cycle_counter -= self.sample_period
            self.samples[func_name] = self.samples.get(func_name, 0) + 1

    def get_metrics(self) -> Dict[str, Any]:
        ipc = self.total_instructions / max(1, self.total_cycles)
        cache_miss_pct = (self.cache_misses / max(1, self.cache_references)) * 100.0
        branch_miss_pct = (self.branch_misses / max(1, self.branch_instructions)) * 100.0

        return {
            "cycles": self.total_cycles,
            "instructions": self.total_instructions,
            "ipc": float(ipc),
            "cache_miss_pct": float(cache_miss_pct),
            "branch_miss_pct": float(branch_miss_pct),
            "samples": self.samples
        }


if __name__ == "__main__":
    print("=== DONANIMSAL PMU VE PERF SAMPLING SİMÜLASYONU ===")
    pmu = SimulatedPmuCore(sample_period_cycles=500000)

    # 1. Kötü Tasarlanmış Radar Fonksiyonu (Rastgele bellek erişimi, yüksek miss)
    pmu.execute_block(func_name="cfar_bad_pointer_chasing", instructions=2000000, cache_miss_prob=0.15, branch_miss_prob=0.12)
    
    # 2. İyi Optimize Edilmiş Vektörel FFT (Cache dostu sıralı erişim)
    pmu.execute_block(func_name="doppler_fft_vectorized", instructions=5000000, cache_miss_prob=0.005, branch_miss_prob=0.01)

    # 3. Kalman Filtresi
    pmu.execute_block(func_name="kalman_matrix_update", instructions=1500000, cache_miss_prob=0.02, branch_miss_prob=0.03)

    metrics = pmu.get_metrics()
    print(f"[*] Toplam Saat Döngüsü (Cycles)     : {metrics['cycles']:,}")
    print(f"[*] Toplam Yürütülen Komut          : {metrics['instructions']:,}")
    print(f"[*] Instructions Per Cycle (IPC)    : {metrics['ipc']:.2f}")
    print(f"[*] L1D/LLC Cache Miss Oranı        : %{metrics['cache_miss_pct']:.2f}")
    print(f"[*] Branch Misprediction Oranı      : %{metrics['branch_miss_pct']:.2f}")
    
    print("\n--- [PERF REPORT / HOTSPOT ÖRNEKLEME SONUÇLARI] ---")
    total_samples = sum(metrics["samples"].values())
    for fn, count in sorted(metrics["samples"].items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_samples) * 100.0
        print(f"  %{pct:5.2f} | Numune: {count:4d} | {fn}()")


# -*- coding: utf-8 -*-
"""
HÜCRE 08 (CODE 2): Python ile AoS vs SoA Bellek Erişim ve Cache Line Simülasyonu
64 Baytlık Cache Line Doygunluğu ve Donanımsal Önyükleyici (Hardware Prefetcher) Modeli
"""

from typing import Dict, Any, List

class CacheLineSimulator:
    """CPU L1D 64-bayt önbellek satırı transfer simülatörü."""
    CACHE_LINE_BYTES = 64

    @staticmethod
    def simulate_aos_access(num_elements: int, struct_size: int = 64, payload_offset: int = 8) -> Dict[str, Any]:
        """AoS: Her eleman için ayrı bir cache line çekilir, verimsizdir."""
        total_bytes_transferred = num_elements * struct_size
        useful_bytes_used = num_elements * payload_offset # Sadece 8 bayt kullanılıyor
        efficiency_pct = (useful_bytes_used / total_bytes_transferred) * 100.0

        return {
            "num_elements": num_elements,
            "transferred_kb": total_bytes_transferred / 1024.0,
            "useful_kb": useful_bytes_used / 1024.0,
            "efficiency_pct": efficiency_pct,
            "cache_lines_loaded": num_elements
        }

    @staticmethod
    def simulate_soa_access(num_elements: int, element_size: int = 8) -> Dict[str, Any]:
        """SoA: Bitişik dizilim sayesinde tek bir 64 baytlık satır 8 elemanı birden besler."""
        total_bytes = num_elements * element_size
        cache_lines = (total_bytes + CacheLineSimulator.CACHE_LINE_BYTES - 1) // CacheLineSimulator.CACHE_LINE_BYTES
        total_bytes_transferred = cache_lines * CacheLineSimulator.CACHE_LINE_BYTES
        efficiency_pct = (total_bytes / total_bytes_transferred) * 100.0

        return {
            "num_elements": num_elements,
            "transferred_kb": total_bytes_transferred / 1024.0,
            "useful_kb": total_bytes / 1024.0,
            "efficiency_pct": efficiency_pct,
            "cache_lines_loaded": cache_lines
        }


if __name__ == "__main__":
    print("=== AOS vs SOA CACHE LINE DOYGUNLUK DENEYİ ===")
    N = 100000 # 100,000 radar hücresi
    aos_res = CacheLineSimulator.simulate_aos_access(num_elements=N, struct_size=64, payload_offset=8)
    soa_res = CacheLineSimulator.simulate_soa_access(num_elements=N, element_size=8)

    print(f"[*] [Array of Structures - AoS]:")
    print(f"    RAM'den Çekilen Veri     : {aos_res['transferred_kb']:.1f} KB (6.25 MB)")
    print(f"    Gerçekten Kullanılan Veri: {aos_res['useful_kb']:.1f} KB")
    print(f"    Önbellek Verimliliği     : %{aos_res['efficiency_pct']:.2f}")
    print(f"    Yüklenen Cache Line      : {aos_res['cache_lines_loaded']:,}")

    print(f"\n[*] [Structure of Arrays - SoA]:")
    print(f"    RAM'den Çekilen Veri     : {soa_res['transferred_kb']:.1f} KB (0.78 MB)")
    print(f"    Gerçekten Kullanılan Veri: {soa_res['useful_kb']:.1f} KB")
    print(f"    Önbellek Verimliliği     : %{soa_res['efficiency_pct']:.2f}")
    print(f"    Yüklenen Cache Line      : {soa_res['cache_lines_loaded']:,}")
    print(f"\n[+] SoA Mimarisi RAM Veriyolu Trafiğini {aos_res['transferred_kb']/soa_res['transferred_kb']:.1f} KAT AZALTTI!")


# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Arıza Simülatörü
Pointer Chasing (Bağlı Liste) ile Cache Throttling ve Düşük IPC Simülasyonu
"""

import random
import time
from typing import Dict, Any, Tuple

class MemoryAccessSabotageLab:
    """Bellek erişim deseni (Locality of Reference) sabotaj simülatörü."""

    @staticmethod
    def simulate_pointer_chasing_vs_contiguous(array_size: int = 100000) -> Dict[str, Any]:
        """Sıralı dizi (Contiguous) ile dairesel bağlı liste (Pointer Chasing) karşılaştırması."""
        # Sıralı dizi simülasyonu
        contiguous_array = list(range(array_size))
        
        # Rastgele düğümlere zıplayan bağlı liste simülasyonu (Pointer Chasing)
        random_indices = list(range(array_size))
        random.seed(42)
        random.shuffle(random_indices)

        # 1. Sıralı Erişim: Yüksek L1 hit, donanımsal prefetch devrede
        t0 = time.perf_counter()
        acc1 = 0
        for val in contiguous_array:
            acc1 += val
        t_seq = time.perf_counter() - t0

        # 2. Rastgele İşaretçi Takibi: Her adım L3/DRAM miss üretir!
        t0 = time.perf_counter()
        acc2 = 0
        for idx in random_indices:
            acc2 += contiguous_array[idx]
        t_rand = time.perf_counter() - t0

        slowdown = t_rand / max(1e-9, t_seq)

        return {
            "array_size": array_size,
            "sequential_time_ms": t_seq * 1000.0,
            "pointer_chasing_time_ms": t_rand * 1000.0,
            "slowdown_factor": slowdown,
            "status": "CACHE_THRASHING_CONFIRMED" if slowdown > 2.0 else "INCONCLUSIVE"
        }


if __name__ == "__main__":
    print("=== BELLEK ERİŞİM SABOTAJ LABORATUVARI (POINTER CHASING) ===")
    res = MemoryAccessSabotageLab.simulate_pointer_chasing_vs_contiguous(array_size=200000)
    print(f"[*] Dizi Boyutu            : {res['array_size']:,} Eleman")
    print(f"[*] Sıralı Erişim Süresi   : {res['sequential_time_ms']:.2f} ms")
    print(f"[*] Rastgele Zıplama Süresi: {res['pointer_chasing_time_ms']:.2f} ms")
    print(f"[*] Donanımsal Yavaşlama    : {res['slowdown_factor']:.1f}x Kat Daha Yavaş!")
    print(f"[*] Teşhis Durumu          : {res['status']}")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Radar Hedef Algılama Profil Analizcisi ve Alev Grafiği Üreticisi
Çağrı Yığını Hiyerarşisi, Sıcak Nokta (Hotspot) ve Alev Grafiği Veri Yapısı Modeli
"""

from typing import Dict, List, Any

class FlameGraphNode:
    """Alev Grafiği çağrı yığını ağaç düğümü."""
    def __init__(self, name: str, value: int = 0):
        self.name = name
        self.value = value # Numune (sample) sayısı
        self.children: Dict[str, 'FlameGraphNode'] = {}

    def add_stack(self, stack: List[str], count: int):
        self.value += count
        if not stack:
            return
        head = stack[0]
        tail = stack[1:]
        if head not in self.children:
            self.children[head] = FlameGraphNode(head)
        self.children[head].add_stack(tail, count)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "children": [child.to_dict() for child in self.children.values()]
        }


def build_radar_flamegraph_data() -> FlameGraphNode:
    """Radar hedef işleme hattının temsili çağrı yığını profili."""
    root = FlameGraphNode("root")
    
    # [main -> RadarEngine::run -> DopplerFFT] = 5,200 numune
    root.add_stack(["main", "RadarEngine::run", "DopplerFFT::execute", "kiss_fft_stride"], 5200)
    
    # [main -> RadarEngine::run -> CFAR_Detector] = 3,800 numune
    root.add_stack(["main", "RadarEngine::run", "CFAR_Detector::calculate_threshold"], 3800)
    
    # [main -> RadarEngine::run -> KalmanTracker] = 1,000 numune
    root.add_stack(["main", "RadarEngine::run", "KalmanTracker::update"], 1000)

    return root


if __name__ == "__main__":
    print("=== RADAR ALEV GRAFİĞİ (FLAME GRAPH) HİYERARŞİSİ ===")
    flame_root = build_radar_flamegraph_data()
    print(f"[*] Kök Düğüm Toplam Numune: {flame_root.value:,}")
    for child in flame_root.children.values():
        print(f"  └─ {child.name} (%{(child.value/flame_root.value)*100:.1f})")
        for sub in child.children.values():
            print(f"      └─ {sub.name} (%{(sub.value/flame_root.value)*100:.1f})")


# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Kapsamlı Bellek Erişim Deseni Benchmark Laboratuvarı
Sıralı (Sequential), Adımlı (Strided) ve Rastgele (Random) Erişimde IPC ve Gecikme Modeli
"""

import numpy as np
from typing import Dict, Any

def run_memory_stride_benchmark() -> Dict[str, Any]:
    """Farklı adım (stride) büyüklüklerine göre L1/L2/LLC önbellek ıskalama oranını modeller."""
    strides = np.array([1, 2, 4, 8, 16, 32, 64, 128], dtype=np.int64) # Eleman adımı
    
    # Stride büyüdükçe cache line paylaşımı düşer ve miss oranı fırlar
    # Stride 1: 64B cache line / 8B double = 8 eleman tek line'da (Miss: %12.5)
    # Stride 8: Her eleman yeni bir 64B cache line (Miss: %100)
    
    cache_miss_rates = []
    ipcs = []
    latencies_ns = []

    for s in strides:
        if s == 1:
            miss_rate = 1.2
            ipc = 2.45
            lat = 1.5
        elif s == 2:
            miss_rate = 3.5
            ipc = 2.10
            lat = 2.2
        elif s == 4:
            miss_rate = 8.2
            ipc = 1.65
            lat = 4.8
        elif s == 8:
            miss_rate = 18.5
            ipc = 1.10
            lat = 12.0
        elif s == 16:
            miss_rate = 32.0
            ipc = 0.72
            lat = 24.5
        elif s == 32:
            miss_rate = 48.0
            ipc = 0.48
            lat = 45.0
        else: # >= 64 (Rastgele benzeri)
            miss_rate = 68.0
            ipc = 0.32
            lat = 72.0

        cache_miss_rates.append(miss_rate)
        ipcs.append(ipc)
        latencies_ns.append(lat)

    return {
        "strides": strides,
        "miss_rates_pct": np.array(cache_miss_rates),
        "ipcs": np.array(ipcs),
        "latencies_ns": np.array(latencies_ns)
    }


if __name__ == "__main__":
    print("=== BELLEK ADIM (STRIDE) VE IPC BENCHMARK'I ===")
    bench = run_memory_stride_benchmark()
    print(f"{'Adım (Stride)':>14} | {'Cache Miss (%)':>16} | {'IPC':>8} | {'Erişim (ns)':>14} | {'Verim Durumu':>14}")
    print("-" * 74)
    for i, s in enumerate(bench["strides"]):
        status = "MÜKEMMEL" if bench["ipcs"][i] > 2.0 else ("İYİ" if bench["ipcs"][i] > 1.0 else "DARBOĞAZ!")
        print(f"{s:>14d} | {bench['miss_rates_pct'][i]:>15.1f}% | {bench['ipcs'][i]:>8.2f} | {bench['latencies_ns'][i]:>12.1f} ns | {status:>14}")


# -*- coding: utf-8 -*-
"""
HÜCRE 20 (CODE 6): 4 Panelli 300 DPI Mühendislik Dashboard'u ve Katı Doğrulama Testleri
perf CPU Profiling, PMU Mimarisi, Bellek Piramidi ve Alev Grafiği Görselleştirmesi
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_103\gun_103_perf_ile_cpu_profiling.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı perf CPU profiling dashboard'u üretir."""
    fig, axes = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor("#0F172A")

    # Renk Paleti
    accent_blue = "#38BDF8"
    accent_green = "#4ADE80"
    accent_amber = "#FBBF24"
    accent_red = "#F87171"
    accent_purple = "#C084FC"
    text_color = "#F8FAFC"
    grid_color = "#334155"

    for ax_row in axes:
        for ax in ax_row:
            ax.set_facecolor("#1E293B")
            ax.tick_params(colors=text_color, labelsize=9)
            ax.grid(True, linestyle="--", alpha=0.3, color=grid_color)
            for spine in ax.spines.values():
                spine.set_color(grid_color)

    # -------------------------------------------------------------------------
    # Panel 1: Stride vs Cache Miss ve IPC (Çift Eksenli Eğri)
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    strides = [1, 2, 4, 8, 16, 32, 64, 128]
    miss_rates = [1.2, 3.5, 8.2, 18.5, 32.0, 48.0, 68.0, 75.0]
    ipcs = [2.45, 2.10, 1.65, 1.10, 0.72, 0.48, 0.32, 0.28]

    x = np.arange(len(strides))
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(s) for s in strides], color=text_color, fontsize=9.5, fontweight="bold")
    ax1.set_xlabel("Bellek Erişim Adımı (Stride Büyüklüğü - Eleman)", color=text_color, fontsize=10)

    # Sol Eksen: Cache Miss
    line1 = ax1.plot(x, miss_rates, marker="o", linewidth=2.5, color=accent_red, label="Cache Miss Oranı (%)")
    ax1.set_ylabel("Cache Miss Oranı (%)", color=accent_red, fontsize=10, fontweight="bold")
    ax1.set_ylim(0, 100)

    # Sağ Eksen: IPC
    ax1_twin = ax1.twinx()
    ax1_twin.tick_params(colors=accent_green, labelsize=9)
    for spine in ax1_twin.spines.values():
        spine.set_color(grid_color)
    line2 = ax1_twin.plot(x, ipcs, marker="s", linewidth=2.5, color=accent_green, label="Instructions Per Cycle (IPC)")
    ax1_twin.set_ylabel("IPC (Döngü Başına Komut)", color=accent_green, fontsize=10, fontweight="bold")
    ax1_twin.set_ylim(0, 3.0)

    ax1.set_title("Panel 1: Bellek Adımına (Stride) Göre Cache Miss ve IPC İlişkisi", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # -------------------------------------------------------------------------
    # Panel 2: CPU Bellek Piramidi ve Erişim Gecikmesi (Logaritmik Bar)
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    tiers = ["CPU Register\n(~0.25 ns)", "L1 Önbellek\n(~1.0 ns)", "L2 Önbellek\n(~3.5 ns)", "L3 Önbellek\n(~12 ns)", "DRAM (RAM)\n(~70 ns)"]
    latencies_ns = [0.25, 1.0, 3.5, 12.0, 70.0]
    colors = [accent_purple, accent_green, accent_blue, accent_amber, accent_red]

    bars = ax2.bar(tiers, latencies_ns, color=colors, width=0.55, edgecolor="#0F172A", linewidth=1.5)
    ax2.set_yscale("log")
    ax2.set_title("Panel 2: Donanımsal Bellek Hiyerarşisi Erişim Gecikmesi (Log Ölçek)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_ylabel("Gecikme (Nanosaniye - log scale)", color=text_color, fontsize=10)

    for bar, val in zip(bars, latencies_ns):
        y_pos = val * 1.3
        ax2.text(bar.get_x() + bar.get_width()/2.0, y_pos, f"{val:.2f} ns", ha="center", va="bottom", color=text_color, fontsize=9.5, fontweight="bold")
    ax2.set_ylim(0.1, 200)

    # -------------------------------------------------------------------------
    # Panel 3: Linux perf Donanımsal PMU Sampling Mimarisi (Diagram)
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)
    ax3.axis("off")
    ax3.set_title("Panel 3: Donanımsal PMU Örnekleme (Sampling) Mimarisi", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # PMU Sayaç Kutusu
    rect_pmu = plt.Rectangle((0.5, 5.5), 4.0, 3.5, facecolor="#0369A1", edgecolor=accent_blue, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_pmu)
    ax3.text(2.5, 8.2, "CPU DONANIMI (PMU)", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(2.5, 7.0, "MSR Sayaçları (Cycles, Inst)\nHer 100K saatte sayaç taşar!\n-> PMI Donanım Kesmesi", ha="center", color="#BAE6FD", fontsize=8)

    # Linux Çekirdeği Kutusu
    rect_kern = plt.Rectangle((5.5, 5.5), 4.0, 3.5, facecolor="#047857", edgecolor=accent_green, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_kern)
    ax3.text(7.5, 8.2, "LINUX ÇEKİRDEĞİ", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(7.5, 7.0, "perf_event_open Sürücüsü\nProgram Sayacını (RIP) Oku\nÇağrı Yığınını (RBP) Kaydet", ha="center", color="#A7F3D0", fontsize=8)

    # Çıktı / Alev Grafiği Kutusu
    rect_out = plt.Rectangle((2.0, 1.0), 6.0, 3.0, facecolor="#334155", edgecolor=accent_amber, linewidth=2.2, transform=ax3.transData)
    ax3.add_patch(rect_out)
    ax3.text(5.0, 3.2, "KULLANICI ALANI (perf.data)", ha="center", color=accent_amber, fontsize=10, fontweight="bold")
    ax3.text(5.0, 2.2, "Alev Grafiği (Flame Graph) & perf report\nSıcak Nokta (Hotspot) Fonksiyon Tespiti", ha="center", color=text_color, fontsize=8.5)
    ax3.text(5.0, 1.4, "< %1 Ek Yük ile Canlı Profiling", ha="center", color=accent_green, fontsize=8.5, fontweight="bold")

    # Oklar
    ax3.annotate("", xy=(5.5, 7.2), xytext=(4.5, 7.2), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2.5))
    ax3.annotate("", xy=(5.0, 4.0), xytext=(7.5, 5.5), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))

    # -------------------------------------------------------------------------
    # Panel 4: Radar Algoritması Çağrı Yığını ve Temsili Alev Grafiği
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_xlim(0, 100)
    ax4.set_ylim(0, 5)
    ax4.axis("off")
    ax4.set_title("Panel 4: Radar Takip Servisi Temsili Alev Grafiği (Flame Graph)", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # Katman 1: main() [%100]
    r_main = plt.Rectangle((2, 0.5), 96, 0.8, facecolor="#B91C1C", edgecolor="#0F172A", linewidth=1.5, transform=ax4.transData)
    ax4.add_patch(r_main)
    ax4.text(50, 0.9, "main() [ %100 CPU ]", ha="center", va="center", color=text_color, fontsize=9, fontweight="bold")

    # Katman 2: RadarEngine::run() [%98]
    r_run = plt.Rectangle((4, 1.5), 92, 0.8, facecolor="#C2410C", edgecolor="#0F172A", linewidth=1.5, transform=ax4.transData)
    ax4.add_patch(r_run)
    ax4.text(50, 1.9, "RadarEngine::run() [ %98 CPU ]", ha="center", va="center", color=text_color, fontsize=9, fontweight="bold")

    # Katman 3: DopplerFFT [%52], CFAR [%36], Kalman [%10]
    r_fft = plt.Rectangle((4, 2.5), 50, 0.8, facecolor="#D97706", edgecolor="#0F172A", linewidth=1.5, transform=ax4.transData)
    ax4.add_patch(r_fft)
    ax4.text(29, 2.9, "DopplerFFT [ %52 ]", ha="center", va="center", color=text_color, fontsize=8.5, fontweight="bold")

    r_cfar = plt.Rectangle((55, 2.5), 32, 0.8, facecolor="#E11D48", edgecolor="#0F172A", linewidth=1.5, transform=ax4.transData)
    ax4.add_patch(r_cfar)
    ax4.text(71, 2.9, "CFAR [ %36 ]", ha="center", va="center", color=text_color, fontsize=8.5, fontweight="bold")

    r_kalman = plt.Rectangle((88, 2.5), 8, 0.8, facecolor="#059669", edgecolor="#0F172A", linewidth=1.5, transform=ax4.transData)
    ax4.add_patch(r_kalman)
    ax4.text(92, 2.9, "Kalman", ha="center", va="center", color=text_color, fontsize=7.5, fontweight="bold")

    # Katman 4: Alt Sıcak Nokta: kiss_fft_stride [%50]
    r_kfft = plt.Rectangle((4, 3.5), 48, 0.8, facecolor="#EA580C", edgecolor="#0F172A", linewidth=1.5, transform=ax4.transData)
    ax4.add_patch(r_kfft)
    ax4.text(28, 3.9, "kiss_fft_stride() [ %50 - ANA DARBOĞAZ! ]", ha="center", va="center", color=text_color, fontsize=8, fontweight="bold")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_path}")


def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Gün 103 için tüm mimari ve matematiksel kabulleri katı testlerle doğrular."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dashboard Görsel Doğrulaması
    assert os.path.exists(png_path), f"HATA: Dashboard görseli mevcut değil: {png_path}"
    file_size = os.path.getsize(png_path)
    assert file_size > 100_000, f"HATA: Dashboard boyutu şüpheli ({file_size} bayt)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {file_size:,} bayt.")

    # 2. PMU Simülatörü ve IPC Doğrulaması
    pmu = SimulatedPmuCore(sample_period_cycles=100000)
    pmu.execute_block("test_func", instructions=1000000, cache_miss_prob=0.01, branch_miss_prob=0.02)
    metrics = pmu.get_metrics()
    assert metrics["ipc"] > 0.1, "HATA: IPC hesaplaması geçersiz!"
    assert metrics["cycles"] >= metrics["instructions"], "HATA: Saat döngüsü komut sayısından az olamaz!"
    print("  [+] Donanımsal PMU Metrikleri ve IPC Hesaplama Doğrulandı.")

    # 3. AoS vs SoA Cache Line Verimlilik Doğrulaması
    aos = CacheLineSimulator.simulate_aos_access(num_elements=1000, struct_size=64, payload_offset=8)
    soa = CacheLineSimulator.simulate_soa_access(num_elements=1000, element_size=8)
    assert soa["efficiency_pct"] > aos["efficiency_pct"] * 5.0, "HATA: SoA önbellek verimi AoS'tan en az 5 kat yüksek olmalıdır!"
    print(f"  [+] SoA vs AoS Cache Doygunluğu Doğrulandı (SoA: %{soa['efficiency_pct']:.1f} vs AoS: %{aos['efficiency_pct']:.1f}).")

    # 4. Bellek Adımı (Stride) ve Cache-Miss Eğilimi Doğrulaması
    stride_bench = run_memory_stride_benchmark()
    assert stride_bench["ipcs"][0] > stride_bench["ipcs"][-1] * 3.0, "HATA: Sıralı erişim IPC'si rastgele erişimden en az 3 kat yüksek olmalıdır!"
    print("  [+] Bellek Adımı (Stride) Büyümesiyle IPC Çöküşü Doğrulandı.")

    # 5. Alev Grafiği Ağaç Bütünlüğü Doğrulaması
    flame_root = build_radar_flamegraph_data()
    assert flame_root.value == 10000, "HATA: Alev grafiği toplam numune sayısı eşleşmedi!"
    print("  [+] Alev Grafiği Çağrı Yığını Ağaç Bütünlüğü Doğrulandı.")

    print("\n[PASS] Gün 103: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
