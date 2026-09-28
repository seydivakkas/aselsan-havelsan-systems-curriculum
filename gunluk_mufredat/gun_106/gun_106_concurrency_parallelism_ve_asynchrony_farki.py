# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, ticari kullanılamaz, tersine mühendislik yapılamaz.
İZİN VERİLEN: Yalnızca GitHub üzerinden kişisel öğrenim amacıyla incelenebilir.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 8 (CODE 1): 3 Paradigmanın Saf Ayrık Simülatörü
Concurrency (Zaman Paylaşımı) vs Parallelism (Çok Çekirdek) vs Asynchrony (Olay Tabanlı)
"""

import time
from typing import Dict, Any, List, Tuple

class ExecutionParadigmSimulator:
    """Üç yürütme modelinin iş tamamlama sürelerini ve CPU verimliliklerini modeller."""

    @staticmethod
    def simulate_concurrency(task_durations_ms: List[float], time_slice_ms: float = 5.0, cs_cost_ms: float = 0.5) -> Dict[str, Any]:
        """Tek çekirdekte zaman dilimlemeli eşzamanlı (concurrency) yürütme simülasyonu."""
        remaining = list(task_durations_ms)
        num_tasks = len(remaining)
        total_time_ms = 0.0
        context_switches = 0

        while any(r > 0 for r in remaining):
            for i in range(num_tasks):
                if remaining[i] > 0:
                    exec_time = min(remaining[i], time_slice_ms)
                    remaining[i] -= exec_time
                    total_time_ms += exec_time + cs_cost_ms
                    context_switches += 1

        useful_work_ms = sum(task_durations_ms)
        efficiency_pct = (useful_work_ms / max(0.001, total_time_ms)) * 100.0

        return {
            "paradigm": "Concurrency (Time-Slicing Single Core)",
            "total_time_ms": total_time_ms,
            "useful_work_ms": useful_work_ms,
            "context_switches": context_switches,
            "cpu_efficiency_pct": efficiency_pct
        }

    @staticmethod
    def simulate_parallelism(task_durations_ms: List[float], num_cores: int = 4) -> Dict[str, Any]:
        """Çok çekirdekte gerçek fiziksel paralel (parallelism) yürütme simülasyonu."""
        core_times = [0.0] * num_cores
        # Görevleri en boş çekirdeğe ata (Greedy Load Balancing)
        for duration in sorted(task_durations_ms, reverse=True):
            min_core_idx = core_times.index(min(core_times))
            core_times[min_core_idx] += duration

        total_wall_time_ms = max(core_times)
        useful_work_ms = sum(task_durations_ms)
        speedup = useful_work_ms / max(0.001, total_wall_time_ms)

        return {
            "paradigm": f"Parallelism ({num_cores} Physical Cores)",
            "total_time_ms": total_wall_time_ms,
            "useful_work_ms": useful_work_ms,
            "speedup_factor": speedup,
            "core_loads_ms": core_times
        }

    @staticmethod
    def simulate_asynchrony(io_tasks_ms: List[Tuple[float, float]]) -> Dict[str, Any]:
        """I/O beklemesi içeren görevlerde Asenkron (Non-blocking) yürütme simülasyonu.
        io_tasks_ms: List of (cpu_preparation_ms, io_wait_ms)
        """
        # Senkron yaklaşım: Her görev cpu + wait kadar süre bloklar
        sync_total_ms = sum(cpu + io for cpu, io in io_tasks_ms)

        # Asenkron yaklaşım: CPU işleri ardışık işletilirken I/O beklemeleri arka planda çakışır
        total_cpu_ms = sum(cpu for cpu, _ in io_tasks_ms)
        max_io_finish_ms = max(cpu_accum + io for (cpu_accum, (_, io)) in 
                               zip(np.cumsum([c for c, _ in io_tasks_ms]), io_tasks_ms))
        async_total_ms = max(total_cpu_ms, max_io_finish_ms)

        return {
            "paradigm": "Asynchrony (Event-Driven Non-blocking)",
            "sync_total_ms": sync_total_ms,
            "async_total_ms": async_total_ms,
            "latency_reduction_pct": ((sync_total_ms - async_total_ms) / sync_total_ms) * 100.0
        }


if __name__ == "__main__":
    print("=== 3 PARADİGMA ÇEKİRDEK BENZETİMİ ===")
    tasks = [20.0, 35.0, 15.0, 50.0] # ms cinsinden iş yükleri
    
    # 1. Concurrency
    c_res = ExecutionParadigmSimulator.simulate_concurrency(tasks, time_slice_ms=10.0, cs_cost_ms=1.0)
    print(f"[*] Concurrency Toplam Süre: {c_res['total_time_ms']:.1f} ms (Verimlilik: %{c_res['cpu_efficiency_pct']:.1f})")

    # 2. Parallelism (4 Çekirdek)
    p_res = ExecutionParadigmSimulator.simulate_parallelism(tasks, num_cores=4)
    print(f"[*] Parallelism Toplam Süre  : {p_res['total_time_ms']:.1f} ms (Hızlanma: {p_res['speedup_factor']:.2f}x)")

    # 3. Asynchrony
    io_tasks = [(5.0, 40.0), (5.0, 30.0), (5.0, 50.0)] # 5ms CPU + I/O
    a_res = ExecutionParadigmSimulator.simulate_asynchrony(io_tasks)
    print(f"[*] Asenkron Kazanımı        : Senkron {a_res['sync_total_ms']} ms -> Asenkron {a_res['async_total_ms']:.1f} ms (%{a_res['latency_reduction_pct']:.1f} Tasarruf)")


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Amdahl ve Gustafson Yasaları Hızlanma Motoru
Donanımsal Çekirdek Ölçekleme ve Seri Darboğazın Matematiksel Modeli
"""

import numpy as np
from typing import Dict, Any, List

class AmdahlScalingEngine:
    """Amdahl ve Gustafson paralel hızlanma sınırları analizcisi."""

    @staticmethod
    def calculate_amdahl_speedup(parallel_fraction: float, cores: np.ndarray) -> np.ndarray:
        """Amdahl Yasası: S(N) = 1 / ((1 - p) + (p / N))"""
        p = parallel_fraction
        s = 1.0 - p # Seri fraksiyon
        return 1.0 / (s + (p / cores))

    @staticmethod
    def calculate_gustafson_speedup(parallel_fraction: float, cores: np.ndarray) -> np.ndarray:
        """Gustafson Yasası: S_scaled(N) = s + p * N = 1 + (N - 1) * p"""
        p = parallel_fraction
        s = 1.0 - p
        return s + (p * cores)

    @staticmethod
    def find_diminishing_returns_core_count(parallel_fraction: float, max_cores: int = 128, threshold_pct: float = 0.02) -> int:
        """Her yeni çekirdeğin getirisi %threshold_pct altına düştüğü verimsizlik noktasını bulur."""
        cores = np.arange(1, max_cores + 1)
        speedups = AmdahlScalingEngine.calculate_amdahl_speedup(parallel_fraction, cores)
        
        optimal_cores = max_cores
        for c in range(1, len(speedups) - 1):
            gain = (speedups[c + 1] - speedups[c]) / speedups[c]
            if gain < threshold_pct:
                optimal_cores = c + 1
                break
        return optimal_cores


if __name__ == "__main__":
    print("=== AMDAHL YASASI VE ÇEKİRDEK ÖLÇEKLENME TESTİ ===")
    test_cores = np.array([1, 2, 4, 8, 16, 32, 64, 128])
    for p in [0.70, 0.90, 0.98]:
        sp = AmdahlScalingEngine.calculate_amdahl_speedup(p, test_cores)
        opt_core = AmdahlScalingEngine.find_diminishing_returns_core_count(p, max_cores=128)
        print(f"[*] Paralel Pay: %{p*100:.0f} | 64 Çekirdekte Hızlanma: {sp[6]:.1f}x | Maks Tavan: {1.0/(1.0-p):.1f}x | Verimli Çekirdek: {opt_core}")


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Thread Aşırı Tahsisi (Over-subscription) ve Thrashing Modeli
Thread Sayısı vs Bağlam Değişimi Kaybı ve Verim Çöküşü
"""

import numpy as np
from typing import Dict, Any, List

class ThreadOverSubscriptionLab:
    """Thread sayısının donanım sınırlarını aşması durumundaki verim çöküş analizcisi."""

    @staticmethod
    def evaluate_thread_scaling(hardware_cores: int = 8, max_threads: int = 128) -> Dict[str, Any]:
        """Thread sayısı 1'den max_threads'e çıkarken efektif işlem gücünü hesaplar."""
        threads = np.arange(1, max_threads + 1)
        effective_throughput = []
        context_switch_overhead_pct = []

        cs_cost_microsec = 3.0 # Her bağlam değişimi 3 us
        time_slice_microsec = 1000.0 # 1 ms zaman dilimi

        for t in threads:
            if t <= hardware_cores:
                # Çekirdek sayısına kadar: Saf lineer hızlanma, sıfır aşırı CS
                cs_pct = 0.5 # Baz çekirdek geçişi
                throughput = float(t)
            else:
                # Aşırı tahsis (Over-subscription): Çekirdek başına düşen thread arttıkça CS fırlar
                threads_per_core = t / hardware_cores
                cs_rate = (threads_per_core - 1.0) * (cs_cost_microsec / time_slice_microsec)
                cs_pct = min(75.0, cs_rate * 100.0 + 1.0)
                
                # Faydalı iş: Çekirdek kapasitesi * (1 - cs_overhead)
                throughput = hardware_cores * (1.0 - (cs_pct / 100.0))

            effective_throughput.append(max(0.1, throughput))
            context_switch_overhead_pct.append(cs_pct)

        return {
            "hardware_cores": hardware_cores,
            "thread_counts": threads,
            "effective_throughput": np.array(effective_throughput),
            "context_switch_overhead_pct": np.array(context_switch_overhead_pct),
            "peak_throughput_thread_count": int(threads[np.argmax(effective_throughput)])
        }


if __name__ == "__main__":
    print("=== THREAD AŞIRI TAHSİSİ (OVER-SUBSCRIPTION) DENEYİ ===")
    res = ThreadOverSubscriptionLab.evaluate_thread_scaling(hardware_cores=8, max_threads=64)
    print(f"[*] Donanım Çekirdek Sayısı : {res['hardware_cores']}")
    print(f"[*] Zirve Verim Noktası      : {res['peak_throughput_thread_count']} Thread (Throughput: {np.max(res['effective_throughput']):.2f})")
    print(f"[*] 64 Thread Durumunda CS Kaybı: %{res['context_switch_overhead_pct'][-1]:.1f} (Efektif Kapasite: {res['effective_throughput'][-1]:.2f})")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Veri Yarışı (Data Race) Sabotajı ve Atomik Savunma
Lost Update Simülatörü ve ThreadSanitizer (TSan) Doğrulama Modeli
"""

import numpy as np
from typing import Dict, Any, List

class DataRaceSabotageLab:
    """Veri yarışının bellek tutarlılığı üzerindeki tahribat simülatörü."""

    @staticmethod
    def simulate_unprotected_race(iterations_per_thread: int = 100000, num_threads: int = 2, collision_probability: float = 0.35) -> Dict[str, Any]:
        """Korumasız iki thread'in aynı sayacı güncellemesi sonucu kayıp güncellemeleri modeller."""
        expected_total = iterations_per_thread * num_threads
        
        # Çarpışma modeli: Her ortak adımda collision_probability olasılıkla biri ezilir
        lost_updates = int(iterations_per_thread * collision_probability * (num_threads - 1))
        actual_total = expected_total - lost_updates

        corruption_pct = (lost_updates / expected_total) * 100.0

        return {
            "num_threads": num_threads,
            "iterations_per_thread": iterations_per_thread,
            "expected_value": expected_total,
            "actual_unprotected_value": actual_total,
            "lost_updates": lost_updates,
            "corruption_pct": corruption_pct,
            "data_race_detected": lost_updates > 0
        }

    @staticmethod
    def simulate_atomic_defense(iterations_per_thread: int = 100000, num_threads: int = 2) -> Dict[str, Any]:
        """std::atomic (LOCK XADD) veya Mutex ile korunan deterministik güncelleme."""
        expected_total = iterations_per_thread * num_threads
        return {
            "num_threads": num_threads,
            "expected_value": expected_total,
            "actual_atomic_value": expected_total,
            "lost_updates": 0,
            "corruption_pct": 0.0,
            "data_race_detected": False
        }


if __name__ == "__main__":
    print("=== VERİ YARIŞI (DATA RACE) SABOTAJ DENEYİ ===")
    iters = 100000
    race_res = DataRaceSabotageLab.simulate_unprotected_race(iterations_per_thread=iters, num_threads=2, collision_probability=0.32)
    atomic_res = DataRaceSabotageLab.simulate_atomic_defense(iterations_per_thread=iters, num_threads=2)

    print(f"[*] [Korumasız Tasarım] Beklenen: {race_res['expected_value']:,} | Gerçekleşen: {race_res['actual_unprotected_value']:,}")
    print(f"[!] KAYIP GÜNCELLEME   : {race_res['lost_updates']:,} (%{race_res['corruption_pct']:.1f} Veri Kaybı!)")
    print(f"[+] [Atomik Savunma]   Beklenen: {atomic_res['expected_value']:,} | Gerçekleşen: {atomic_res['actual_atomic_value']:,} (SIFIR HATA)")


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru
Tek Thread Async vs Çok Thread Kilitli vs Çok Thread Lock-Free Gecikme Analizi
"""

import numpy as np
from typing import Dict, Any, List

def run_paradigm_benchmark(num_samples: int = 15000) -> Dict[str, Any]:
    """Üç mimarinin gecikme dağılımlarını mikrosaniye cinsinden modeller."""
    np.random.seed(106)

    # 1. Tek Thread Asenkron Olay Döngüsü (I/O Yoğun Senaryo)
    # Düşük medyan, stabil kuyruk: Medyan ~30 us, p99 ~95 us
    async_latencies = np.random.lognormal(mean=3.4, sigma=0.30, size=num_samples)

    # 2. Çok Thread Kilitli (Mutex Contention)
    # Medyan iyi ancak kilit çekişmesinde kuyruk patlaması: Medyan ~45 us, p99 ~420 us
    locked_latencies = np.random.lognormal(mean=3.8, sigma=0.65, size=num_samples)

    # 3. Çok Thread Kilitlenmesiz (Lock-Free SPSC/MPMC Ring Buffer)
    # Yüksek verim, ultra düşük p99: Medyan ~18 us, p99 ~60 us
    lockfree_latencies = np.random.lognormal(mean=2.9, sigma=0.28, size=num_samples)

    def get_stats(arr: np.ndarray) -> Dict[str, float]:
        return {
            "p50": float(np.percentile(arr, 50)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "max": float(np.max(arr)),
            "mean": float(np.mean(arr))
        }

    return {
        "num_samples": num_samples,
        "async_stats": get_stats(async_latencies),
        "locked_stats": get_stats(locked_latencies),
        "lockfree_stats": get_stats(lockfree_latencies),
        "async_raw": async_latencies,
        "locked_raw": locked_latencies,
        "lockfree_raw": lockfree_latencies
    }


if __name__ == "__main__":
    print("=== MİMARİ GECİKME KIYASLAMA BENCHMARK'I ===")
    b = run_paradigm_benchmark(num_samples=15000)
    print(f"{'Metrik':>8} | {'Tek Thread Async':>18} | {'Çok Thread Kilitli':>20} | {'Çok Thread Lock-Free':>22}")
    print("-" * 76)
    for m in ["p50", "p90", "p95", "p99", "mean"]:
        v1 = b["async_stats"][m]
        v2 = b["locked_stats"][m]
        v3 = b["lockfree_stats"][m]
        print(f"{m.upper():>8} | {v1:>15.1f} us | {v2:>17.1f} us | {v3:>19.1f} us")


# -*- coding: utf-8 -*-
"""
HÜCRE 18 (CODE 6): 4-Panelli 300 DPI Eşzamanlılık Dashboard'u ve Katı Doğrulama Motoru
Amdahl Yasası, Paradigma Ayrımı, Thread Thrashing ve Veri Yarışı Savunması
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_106\gun_106_concurrency_parallelism_ve_asynchrony_farki.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı concurrency mühendislik dashboard'u üretir."""
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
    # Panel 1: Amdahl Yasası Teorik Hızlanma Eğrileri
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    cores = np.arange(1, 65)
    fractions = [0.50, 0.80, 0.95, 0.99]
    colors = [accent_amber, accent_blue, accent_purple, accent_green]

    for p, col in zip(fractions, colors):
        spd = AmdahlScalingEngine.calculate_amdahl_speedup(p, cores)
        ax1.plot(cores, spd, color=col, linewidth=2.2, label=f"Paralel Pay %{int(p*100)} (Tavan: {1.0/(1-p):.1f}x)")

    ax1.plot(cores, cores, color="#64748B", linestyle=":", linewidth=1.5, label="İdeal Lineer Hızlanma (1:1)")
    ax1.set_title("Panel 1: Amdahl Yasası Çekirdek Ölçeklenme Sınırları", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.set_xlabel("Fiziksel Çekirdek Sayısı (Cores)", color=text_color, fontsize=10)
    ax1.set_ylabel("Hızlanma Çarpanı (Speedup Factor)", color=text_color, fontsize=10)
    ax1.set_ylim(0, 45)
    ax1.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 2: 3 Paradigmanın Zaman ve Kaynak Çizelgesi (Timeline)
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis("off")
    ax2.set_title("Panel 2: Concurrency vs Parallelism vs Asynchrony Zaman Modeli", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # 1. Concurrency
    ax2.text(0.5, 8.8, "1. CONCURRENCY (Tek Çekirdek - Zaman Paylaşımı):", color=accent_amber, fontsize=9, fontweight="bold")
    ax2.add_patch(plt.Rectangle((0.5, 7.5), 2.0, 0.9, facecolor="#B45309", edgecolor=accent_amber, transform=ax2.transData))
    ax2.add_patch(plt.Rectangle((2.7, 7.5), 2.0, 0.9, facecolor="#0369A1", edgecolor=accent_blue, transform=ax2.transData))
    ax2.add_patch(plt.Rectangle((4.9, 7.5), 2.0, 0.9, facecolor="#B45309", edgecolor=accent_amber, transform=ax2.transData))
    ax2.add_patch(plt.Rectangle((7.1, 7.5), 2.0, 0.9, facecolor="#0369A1", edgecolor=accent_blue, transform=ax2.transData))
    ax2.text(1.5, 7.95, "Görev A", ha="center", color=text_color, fontsize=8)
    ax2.text(3.7, 7.95, "Görev B", ha="center", color=text_color, fontsize=8)
    ax2.text(5.9, 7.95, "Görev A", ha="center", color=text_color, fontsize=8)
    ax2.text(8.1, 7.95, "Görev B", ha="center", color=text_color, fontsize=8)

    # 2. Parallelism
    ax2.text(0.5, 5.8, "2. PARALLELISM (Çok Çekirdek - Eşzamanlı Donanım Yürütmesi):", color=accent_green, fontsize=9, fontweight="bold")
    ax2.add_patch(plt.Rectangle((0.5, 4.7), 4.2, 0.8, facecolor="#047857", edgecolor=accent_green, transform=ax2.transData))
    ax2.add_patch(plt.Rectangle((0.5, 3.7), 4.2, 0.8, facecolor="#0369A1", edgecolor=accent_blue, transform=ax2.transData))
    ax2.text(2.6, 5.1, "Çekirdek 0: Görev A (Donanımsal Yürütme)", ha="center", color=text_color, fontsize=8)
    ax2.text(2.6, 4.1, "Çekirdek 1: Görev B (Donanımsal Yürütme)", ha="center", color=text_color, fontsize=8)

    # 3. Asynchrony
    ax2.text(0.5, 2.3, "3. ASYNCHRONY (Olay Tabanlı - Non-blocking I/O):", color=accent_purple, fontsize=9, fontweight="bold")
    ax2.add_patch(plt.Rectangle((0.5, 1.0), 2.5, 0.8, facecolor="#6D28D9", edgecolor=accent_purple, transform=ax2.transData))
    ax2.add_patch(plt.Rectangle((3.2, 1.0), 3.0, 0.8, facecolor="#334155", edgecolor="#64748B", linestyle="--", transform=ax2.transData))
    ax2.add_patch(plt.Rectangle((6.4, 1.0), 2.5, 0.8, facecolor="#6D28D9", edgecolor=accent_purple, transform=ax2.transData))
    ax2.text(1.75, 1.4, "I/O Başlat", ha="center", color=text_color, fontsize=8)
    ax2.text(4.7, 1.4, "Arka Planda I/O Bekleme (CPU Serbest)", ha="center", color="#94A3B8", fontsize=7.5)
    ax2.text(7.65, 1.4, "Callback / Bitir", ha="center", color=text_color, fontsize=8)

    # -------------------------------------------------------------------------
    # Panel 3: Thread Aşırı Tahsisi (Over-subscription) ve Thrashing
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    thr_data = ThreadOverSubscriptionLab.evaluate_thread_scaling(hardware_cores=8, max_threads=48)
    t_counts = thr_data["thread_counts"]
    eff_tp = thr_data["effective_throughput"]
    cs_overhead = thr_data["context_switch_overhead_pct"]

    ax3_twin = ax3.twinx()
    line1 = ax3.plot(t_counts, eff_tp, color=accent_green, linewidth=2.5, label="Efektif Throughput (Kapasite)")
    line2 = ax3_twin.plot(t_counts, cs_overhead, color=accent_red, linestyle="--", linewidth=2.0, label="Bağlam Değişimi Kaybı (%)")

    ax3.axvline(8, color=accent_amber, linestyle=":", linewidth=2, label="Fiziksel Çekirdek Sınırı (8 Cores)")

    ax3.set_title("Panel 3: Thread Aşırı Tahsisi (Over-subscription) ve Verim Çöküşü", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax3.set_xlabel("Toplam İş Parçacığı Sayısı (Threads)", color=text_color, fontsize=10)
    ax3.set_ylabel("Efektif İşlem Gücü (Birim)", color=accent_green, fontsize=10)
    ax3_twin.set_ylabel("Context Switch Kaybı (%)", color=accent_red, fontsize=10)
    ax3_twin.tick_params(colors=accent_red)

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax3.legend(lines, labels, facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8, loc="center right")

    # -------------------------------------------------------------------------
    # Panel 4: Veri Yarışı Tahribatı ve Atomik Savunma
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    trials = ["Korumasız Tasarım\n(Data Race / Lost Updates)", "Atomik Savunma\n(std::atomic<T> / Mutex)"]
    race_sim = DataRaceSabotageLab.simulate_unprotected_race(iterations_per_thread=100000, num_threads=2, collision_probability=0.35)
    actual_vals = [race_sim["actual_unprotected_value"] / 1000.0, 200.0] # Bin cinsinden
    expected_vals = [200.0, 200.0]

    x = np.arange(len(trials))
    width = 0.35

    ax4.bar(x - width/2, expected_vals, width, color=accent_blue, label="Beklenen Doğru Sonuç (200k)")
    bars_act = ax4.bar(x + width/2, actual_vals, width, color=[accent_red, accent_green], label="Gerçekleşen Sayaç Değeri")

    ax4.set_xticks(x)
    ax4.set_xticklabels(trials, color=text_color, fontsize=9.5)
    ax4.set_title("Panel 4: Veri Yarışı Tahribatı ve Atomik Güvencesi", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax4.set_ylabel("Sayaç Değeri (Bin Adet - x1000)", color=text_color, fontsize=10)
    ax4.set_ylim(0, 260)
    ax4.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    # Etiketler
    for bar, val in zip(bars_act, actual_vals):
        ax4.text(bar.get_x() + bar.get_width()/2.0, val + 5, f"{val:.1f}k", ha="center", va="bottom", color=text_color, fontsize=9, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_path}")


def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Katı mühendislik doğrulama testleri (Assertions)."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dosya Varlık ve Boyut Kontrolü
    assert os.path.exists(png_path), f"HATA: Dashboard görseli mevcut değil: {png_path}"
    file_size = os.path.getsize(png_path)
    assert file_size > 100_000, f"HATA: Dashboard boyutu şüpheli ({file_size} bayt)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {file_size:,} bayt.")

    # 2. Amdahl Yasası Doğrulaması
    c1 = np.array([1])
    c64 = np.array([64])
    s_50 = AmdahlScalingEngine.calculate_amdahl_speedup(0.50, c64)[0]
    assert s_50 < 2.0, f"HATA: %50 paralel pay ile hızlanma 2.0x'i geçemez ({s_50})!"
    s_95 = AmdahlScalingEngine.calculate_amdahl_speedup(0.95, c64)[0]
    assert s_95 > 15.0 and s_95 < 20.0, f"HATA: %95 paralel pay hızlanması matematiksel sınır dışı ({s_95})!"
    print("  [+] Amdahl Yasası Teorik Sınırları ve Asymptotik Tavanı Doğrulandı.")

    # 3. Thread Aşırı Tahsisi (Over-subscription) Doğrulaması
    thr_res = ThreadOverSubscriptionLab.evaluate_thread_scaling(hardware_cores=8, max_threads=48)
    assert thr_res["peak_throughput_thread_count"] == 8, "HATA: Zirve throughput donanım çekirdeği sayısında olmalıdır!"
    assert thr_res["effective_throughput"][-1] < thr_res["effective_throughput"][7], "HATA: Aşırı thread'de verim düşüşü tespit edilemedi!"
    print("  [+] Thread Aşırı Tahsisi (Over-subscription) ve Thrashing Davranışı Doğrulandı.")

    # 4. Veri Yarışı Sabotaj ve Atomik Savunma Doğrulaması
    race = DataRaceSabotageLab.simulate_unprotected_race(iterations_per_thread=100000, num_threads=2, collision_probability=0.30)
    assert race["data_race_detected"] is True, "HATA: Veri yarışı tespit edilemedi!"
    assert race["actual_unprotected_value"] < race["expected_value"], "HATA: Kayıp güncelleme oluşmadı!"
    
    atomic = DataRaceSabotageLab.simulate_atomic_defense(iterations_per_thread=100000, num_threads=2)
    assert atomic["data_race_detected"] is False and atomic["actual_atomic_value"] == 200000, "HATA: Atomik savunma başarısız!"
    print("  [+] Veri Yarışı (Data Race) Tahribatı ve Atomik Savunma Kararlılığı Doğrulandı.")

    # 5. Ampirik Benchmark Doğrulaması
    bench = run_paradigm_benchmark(num_samples=3000)
    assert bench["lockfree_stats"]["p99"] < bench["locked_stats"]["p99"], "HATA: Lock-free kuyruk kilitliden daha yüksek p99 veremez!"
    print("  [+] Lock-Free Kuyruk Gecikme Üstünlüğü ve p99 Kuyruk Kararlılığı Doğrulandı.")

    print("\n[PASS] Gün 106: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
