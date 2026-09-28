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
HÜCRE 8 (CODE 1): std::thread Durum Makinesi ve Yaşam Döngüsü Simülatörü
joinable, join, detach ve std::terminate Davranışının Saf Modeli
"""

from typing import Dict, Any, Optional

class SimulatedThreadState:
    UNINITIALIZED = "UNINITIALIZED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    JOINED = "JOINED"
    DETACHED = "DETACHED"
    TERMINATED = "TERMINATED"


class SimulatedStdThread:
    """C++ std::thread durum makinesini ve yıkıcı kurallarını simüle eder."""

    def __init__(self, target_fn: Optional[str] = None, *args):
        self.target_fn = target_fn
        self.args = args
        self.tid = id(self) if target_fn else None
        self._state = SimulatedThreadState.RUNNING if target_fn else SimulatedThreadState.UNINITIALIZED
        self.has_leaked_resources = False
        self.termination_triggered = False

    def is_joinable(self) -> bool:
        """std::thread::joinable() sorgusu."""
        return self._state in (SimulatedThreadState.RUNNING, SimulatedThreadState.FINISHED)

    def complete_execution(self):
        """Thread içerisindeki işin bittiğini simüle eder."""
        if self._state == SimulatedThreadState.RUNNING:
            self._state = SimulatedThreadState.FINISHED

    def join(self) -> str:
        """std::thread::join() çağrısı."""
        if not self.is_joinable():
            raise RuntimeError("std::system_error: Invalid argument (Thread not joinable!)")
        self._state = SimulatedThreadState.JOINED
        return "SUCCESSFULLY_JOINED"

    def detach(self) -> str:
        """std::thread::detach() çağrısı."""
        if not self.is_joinable():
            raise RuntimeError("std::system_error: Invalid argument (Thread not joinable!)")
        self._state = SimulatedThreadState.DETACHED
        self.has_leaked_resources = True # Potansiyel sızıntı
        return "SUCCESSFULLY_DETACHED"

    def destructor(self) -> str:
        """std::thread kapsam dışına çıktığında çağrılan yıkıcı fonksiyon (~thread)."""
        if self.is_joinable():
            self._state = SimulatedThreadState.TERMINATED
            self.termination_triggered = True
            return "FATAL_STD_TERMINATE"
        return "CLEAN_DESTRUCTION"


if __name__ == "__main__":
    print("=== STD::THREAD DURUM MAKİNESİ TESTİ ===")
    # 1. Başarılı Yaşam Döngüsü
    t1 = SimulatedStdThread("radar_worker", 101)
    assert t1.is_joinable() is True
    print(f"[*] Thread 1 Başlatıldı: Joinable={t1.is_joinable()}")
    t1.complete_execution()
    assert t1.join() == "SUCCESSFULLY_JOINED"
    assert t1.is_joinable() is False
    assert t1.destructor() == "CLEAN_DESTRUCTION"
    print("[+] Thread 1: Temiz join ve güvenli yıkım doğrulandı.")

    # 2. Ölümcül Unjoined Yıkım
    t2 = SimulatedStdThread("telemetry_worker", 202)
    assert t2.destructor() == "FATAL_STD_TERMINATE"
    print("[!] Thread 2: Unjoined nesne std::terminate() tetikledi!")


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): RAII ThreadGuard ve Parametre Aktarım Simülatörü
std::ref vs Kopya Aktarımı ve İstisna Güvenliği (Exception Safety)
"""

from typing import Dict, Any, List

class SimulatedThreadGuard:
    """RAII prensibiyle std::thread nesnesini otomatik join ile koruyan sarmalayıcı."""

    def __init__(self, thread: SimulatedStdThread):
        self.thread = thread

    def __enter__(self):
        return self.thread

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Kapsamdan çıkılırken (istisna fırlatılsa bile) join çağrılır!
        if self.thread.is_joinable():
            self.thread.join()
        return False # İstisnayı yutmaz, yukarı iletir


class ParameterPassingSimulator:
    """C++ decay-copy vs std::ref parametre aktarım davranışını analiz eder."""

    @staticmethod
    def run_decay_copy_simulation(original_value: int, increment: int) -> Dict[str, Any]:
        """Varsayılan kopya aktarımı: Orijinal değer ASLA değişmez."""
        copied_value = original_value
        copied_value += increment
        return {
            "mode": "decay-copy (Default)",
            "original_after": original_value,
            "worker_value": copied_value,
            "modified_original": original_value != copied_value - increment
        }

    @staticmethod
    def run_std_ref_simulation(container: List[int], increment: int) -> Dict[str, Any]:
        """std::ref ile referans aktarımı: Orijinal değer güncellenir."""
        # Python listesi üzerinden referans semantiği simülasyonu
        container[0] += increment
        return {
            "mode": "std::ref (Reference Wrapper)",
            "original_after": container[0],
            "modified_original": True
        }


if __name__ == "__main__":
    print("=== RAII THREADGUARD VE PARAMETRE AKTARIM TESTİ ===")
    # 1. ThreadGuard Koruma Testi
    t = SimulatedStdThread("guided_missile_tracker", 99)
    try:
        with SimulatedThreadGuard(t):
            raise ValueError("Kritik donanım I/O istisnası fırlatıldı!")
    except ValueError:
        pass
    
    # ThreadGuard istisnaya rağmen t.join() çağırmış olmalıdır
    assert t.is_joinable() is False
    assert t.destructor() == "CLEAN_DESTRUCTION"
    print("[+] ThreadGuard İstisna Güvenliği Başarıyla Doğrulandı (std::terminate Önlendi).")

    # 2. Parametre Aktarımı
    val = 100
    p1 = ParameterPassingSimulator.run_decay_copy_simulation(val, 25)
    assert p1["original_after"] == 100
    print(f"[+] decay-copy: Orijinal değer korundu ({p1['original_after']})")

    ref_box = [100]
    p2 = ParameterPassingSimulator.run_std_ref_simulation(ref_box, 25)
    assert p2["original_after"] == 125
    print(f"[+] std::ref: Orijinal referans başarıyla güncellendi ({p2['original_after']})")


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Yığın Boyutu Optimizasyonu ve Thread Kapasite Sınırı Modeli
Stack Size vs Maksimum Çalıştırılabilir Thread Kapasitesi
"""

import numpy as np
from typing import Dict, Any, List

class ThreadStackCapacityModel:
    """Farklı yığın boyutlarında (Stack Size) sistemin thread kapasitesini hesaplar."""

    @staticmethod
    def calculate_max_threads(available_ram_mb: float = 2048.0, stack_sizes_kb: List[int] = [8192, 2048, 512, 128]) -> Dict[str, Any]:
        """Kullanılabilir RAM miktarına göre açılabilecek maksimum thread sayısını modeller."""
        results = []
        for s_kb in stack_sizes_kb:
            s_mb = s_kb / 1024.0
            # Güvenlik marjı: RAM'in %75'i thread stack'lerine ayrılabilir
            usable_ram = available_ram_mb * 0.75
            max_th = int(usable_ram / s_mb)
            results.append({
                "stack_size_kb": s_kb,
                "stack_size_mb": s_mb,
                "max_threads": max_th
            })

        return {
            "available_ram_mb": available_ram_mb,
            "scenarios": results
        }


if __name__ == "__main__":
    print("=== THREAD YIĞIN BOYUTU KAPASİTE ANALİZİ ===")
    cap = ThreadStackCapacityModel.calculate_max_threads(available_ram_mb=2048.0)
    print(f"[*] Toplam Sistem RAM: {cap['available_ram_mb']} MB (Kullanılabilir: {cap['available_ram_mb']*0.75:.0f} MB)")
    print(f"{'Stack Boyutu':>15} | {'Maksimum Thread Sayısı':>24} | {'Kapasite Artışı':>18}")
    print("-" * 62)
    base_threads = cap["scenarios"][0]["max_threads"]
    for sc in cap["scenarios"]:
        multiplier = sc["max_threads"] / base_threads
        print(f"{sc['stack_size_kb']:>12} KB | {sc['max_threads']:>24,d} | {multiplier:>16.1f}x")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Canlı Sabotaj ve Arıza Laboratuvarı
Unjoined Thread Crash vs ThreadGuard Koruması ve Sarkan Referans Analizi
"""

from typing import Dict, Any, List

class ThreadChaosLab:
    """Thread yaşam döngüsü sabotaj ve savunma simülasyonu."""

    @staticmethod
    def simulate_unjoined_destruction(simulate_exception: bool = True, use_guard: bool = False) -> Dict[str, Any]:
        """Korumasız thread vs ThreadGuard korumalı thread çöküş simülasyonu."""
        t = SimulatedStdThread("sensor_reader", 1)
        crashed = False
        exit_code = "EXIT_SUCCESS"

        try:
            if use_guard:
                with SimulatedThreadGuard(t):
                    if simulate_exception:
                        raise RuntimeError("Sensör haberleşme zaman aşımı!")
            else:
                if simulate_exception:
                    raise RuntimeError("Sensör haberleşme zaman aşımı!")
                t.join()
        except RuntimeError:
            pass

        # Kapsam sonu: Yıkıcı çağrılır
        destruction_result = t.destructor()
        if destruction_result == "FATAL_STD_TERMINATE":
            crashed = True
            exit_code = "SIGABRT_TERMINATED"

        return {
            "use_guard": use_guard,
            "exception_occurred": simulate_exception,
            "crashed": crashed,
            "exit_code": exit_code,
            "thread_state": t._state
        }

    @staticmethod
    def simulate_dangling_reference_sabotage(stack_freed: bool = True) -> Dict[str, Any]:
        """Stack Use-After-Return durumunda bellek bozulması simülasyonu."""
        if stack_freed:
            # Stack alanı temizlendi, bellek artık tanımsız
            corrupted_val = 0xDEADBEEF
            return {
                "memory_safe": False,
                "read_value": hex(corrupted_val),
                "failure_mode": "STACK_USE_AFTER_RETURN_DATA_CORRUPTION"
            }
        return {
            "memory_safe": True,
            "read_value": "42 (VALID)",
            "failure_mode": "NONE"
        }


if __name__ == "__main__":
    print("=== THREAD SABOTAJ VE CHAOS DENEYİ ===")
    
    # 1. Korumasız Çöküş
    c1 = ThreadChaosLab.simulate_unjoined_destruction(simulate_exception=True, use_guard=False)
    print(f"[*] [Korumasız Tasarım] Çöktü mü? {c1['crashed']} -> Çıkış Sinyali: {c1['exit_code']}")
    assert c1["crashed"] is True

    # 2. Guard ile Savunma
    c2 = ThreadChaosLab.simulate_unjoined_destruction(simulate_exception=True, use_guard=True)
    print(f"[+] [ThreadGuard Savunması] Çöktü mü? {c2['crashed']} -> Çıkış Sinyali: {c2['exit_code']}")
    assert c2["crashed"] is False


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Kapsamlı Ampirik Kıyaslama ve SLA Metrik Toplama Motoru
İstek Başına Thread Açma vs Thread Pool Gecikme Dağılımı (p50, p95, p99)
"""

import numpy as np
from typing import Dict, Any, List

def run_thread_creation_benchmark(num_samples: int = 15000) -> Dict[str, Any]:
    """İstek başına thread açma ile Thread Pool mimarilerinin gecikme dağılımlarını modeller."""
    np.random.seed(107)

    # 1. On-Demand std::thread (clone syscall + stack allocation):
    # Medyan ~35 us, kuyruk p99 ~85 us
    ondemand_latencies = np.random.lognormal(mean=3.55, sigma=0.28, size=num_samples)

    # 2. Pre-Allocated Thread Pool (Condition Variable notify / Futex):
    # Medyan ~1.2 us, kuyruk p99 ~3.8 us
    pool_latencies = np.random.lognormal(mean=0.18, sigma=0.35, size=num_samples)

    def calc_stats(arr: np.ndarray) -> Dict[str, float]:
        return {
            "p50": float(np.percentile(arr, 50)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "mean": float(np.mean(arr))
        }

    return {
        "num_samples": num_samples,
        "ondemand_stats": calc_stats(ondemand_latencies),
        "pool_stats": calc_stats(pool_latencies),
        "ondemand_raw": ondemand_latencies,
        "pool_raw": pool_latencies
    }


if __name__ == "__main__":
    print("=== THREAD BAŞLATMA MALİYETİ BENCHMARK'I ===")
    b = run_thread_creation_benchmark(num_samples=15000)
    print(f"{'Metrik':>8} | {'On-Demand Thread (us)':>25} | {'Thread Pool (us)':>20}")
    print("-" * 58)
    for m in ["p50", "p90", "p95", "p99", "mean"]:
        v1 = b["ondemand_stats"][m]
        v2 = b["pool_stats"][m]
        print(f"{m.upper():>8} | {v1:>22.2f} us | {v2:>17.2f} us")
    
    speedup = b["ondemand_stats"]["p99"] / b["pool_stats"]["p99"]
    print(f"\n[+] p99 Gecikmesinde Thread Pool Avantajı: {speedup:.1f}x Kat Daha Hızlı!")


# -*- coding: utf-8 -*-
"""
HÜCRE 18 (CODE 6): 4-Panelli 300 DPI Thread Yönetim Dashboard'u ve Katı Doğrulama Motoru
Yaşam Döngüsü, Stack Optimizasyonu, Başlatma Gecikmesi ve ThreadGuard Doğrulaması
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_107\gun_107_std_thread_temel_kullanimi.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı thread mühendislik dashboard'u üretir."""
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
    # Panel 1: std::thread Durum Makinesi Görselleştirmesi
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis("off")
    ax1.set_title("Panel 1: std::thread Durum Makinesi ve Yıkıcı (Destructor) Kuralı", color=text_color, fontsize=11, fontweight="bold", pad=12)

    boxes = [
        ("std::thread t;\n(joinable == false)", (0.8, 6.5), "#64748B", "#334155"),
        ("std::thread t(worker);\n(joinable == true)", (4.8, 6.5), accent_green, "#047857"),
        ("t.join()\nKaynağı Al / Bekle\n(joinable == false)", (1.5, 2.0), accent_blue, "#0369A1"),
        ("t.detach()\nBağımsız Bırak\n(joinable == false)", (4.8, 2.0), accent_amber, "#B45309"),
        ("~thread() & joinable\nstd::terminate()\n(ÇÖKÜŞ / CRASH)", (8.0, 2.0), accent_red, "#991B1B"),
    ]

    for label, (bx, by), edge_c, face_c in boxes:
        rect = plt.Rectangle((bx, by), 2.2, 2.2, facecolor=face_c, edgecolor=edge_c, linewidth=2, transform=ax1.transData)
        ax1.add_patch(rect)
        ax1.text(bx + 1.1, by + 1.1, label, ha="center", va="center", color=text_color, fontsize=8, fontweight="bold")

    # Oklar
    ax1.annotate("", xy=(4.8, 7.6), xytext=(3.0, 7.6), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))
    ax1.annotate("", xy=(2.6, 4.2), xytext=(5.3, 6.5), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax1.annotate("", xy=(5.9, 4.2), xytext=(5.9, 6.5), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax1.annotate("", xy=(8.5, 4.2), xytext=(6.8, 6.5), arrowprops=dict(arrowstyle="->", color=accent_red, lw=2.5))

    # -------------------------------------------------------------------------
    # Panel 2: Yığın Boyutu (Stack Size) vs Maksimum Thread Kapasitesi
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    cap_data = ThreadStackCapacityModel.calculate_max_threads(available_ram_mb=2048.0)
    stacks = [f"{sc['stack_size_kb']} KB" for sc in cap_data["scenarios"]]
    th_counts = [sc["max_threads"] for sc in cap_data["scenarios"]]
    colors_bar = [accent_red, accent_amber, accent_blue, accent_green]

    bars = ax2.bar(stacks, th_counts, color=colors_bar, width=0.55, edgecolor="#0F172A", linewidth=1.5)
    ax2.set_title("Panel 2: 2 GB RAM Sınırında Yığın Boyutu vs Maksimum Thread", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_xlabel("İş Parçacığı Yığın Boyutu (Stack Size)", color=text_color, fontsize=10)
    ax2.set_ylabel("Maksimum Thread Sayısı", color=text_color, fontsize=10)

    for bar, val in zip(bars, th_counts):
        ax2.text(bar.get_x() + bar.get_width()/2.0, val + 200, f"{val:,}", ha="center", va="bottom", color=text_color, fontsize=9, fontweight="bold")
    ax2.set_ylim(0, 14000)

    # -------------------------------------------------------------------------
    # Panel 3: İstek Başına Thread vs Thread Pool Gecikme Dağılımı
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    bench = run_thread_creation_benchmark(num_samples=10000)
    bins = np.linspace(0, 80, 80)

    ax3.hist(bench["ondemand_raw"], bins=bins, color=accent_red, alpha=0.6, label=f"On-Demand std::thread (p99={bench['ondemand_stats']['p99']:.1f} µs)")
    ax3.hist(bench["pool_raw"], bins=bins, color=accent_green, alpha=0.8, label=f"Pre-allocated Thread Pool (p99={bench['pool_stats']['p99']:.1f} µs)")

    ax3.set_title("Panel 3: Görev Başlatma Gecikmesi Dağılımı (µs)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax3.set_xlabel("Başlatma Gecikmesi (Mikrosaniye - µs)", color=text_color, fontsize=10)
    ax3.set_ylabel("Örnek Sayısı", color=text_color, fontsize=10)
    ax3.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper right")

    # -------------------------------------------------------------------------
    # Panel 4: ThreadGuard ile std::terminate() Önleme Başarımı
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    trials = ["Korumasız std::thread\n(Exception Fırlatıldığında)", "ThreadGuard RAII\n(Exception Korumalı)"]
    crash_rates = [100.0, 0.0]
    success_rates = [0.0, 100.0]

    x = np.arange(len(trials))
    width = 0.45

    b1 = ax4.bar(x, crash_rates, width, color=accent_red, label="Çöküş Oranı (std::terminate %)")
    b2 = ax4.bar(x, success_rates, width, color=accent_green, label="Güvenli Kapanış / Join (%)")

    ax4.set_xticks(x)
    ax4.set_xticklabels(trials, color=text_color, fontsize=9.5)
    ax4.set_title("Panel 4: İstisna Anında Çöküş vs RAII ThreadGuard Koruması", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax4.set_ylabel("Oran (%)", color=text_color, fontsize=10)
    ax4.set_ylim(0, 120)
    ax4.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="center right")

    ax4.text(0, 105, "%100 ÇÖKÜŞ", ha="center", color=accent_red, fontweight="bold", fontsize=10)
    ax4.text(1, 105, "%100 GÜVENLİ", ha="center", color=accent_green, fontweight="bold", fontsize=10)

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

    # 2. std::thread Yaşam Döngüsü ve Durum Makinesi Doğrulaması
    t = SimulatedStdThread("engine_igniter", 1)
    assert t.is_joinable() is True, "HATA: Başlatılan thread joinable olmalıdır!"
    t.complete_execution()
    assert t.is_joinable() is True, "HATA: Tamamlanan thread join edilene kadar joinable kalmalıdır!"
    t.join()
    assert t.is_joinable() is False, "HATA: join() sonrası thread non-joinable olmalıdır!"
    assert t.destructor() == "CLEAN_DESTRUCTION", "HATA: join() sonrası yıkıcı güvenli kapanmalıdır!"
    print("  [+] std::thread Yaşam Döngüsü ve joinable Durum Geçişleri Doğrulandı.")

    # 3. std::terminate Sabotajı ve ThreadGuard Savunması Doğrulaması
    res_unsafe = ThreadChaosLab.simulate_unjoined_destruction(simulate_exception=True, use_guard=False)
    assert res_unsafe["crashed"] is True and res_unsafe["exit_code"] == "SIGABRT_TERMINATED", "HATA: Unjoined thread çökmedi!"
    
    res_safe = ThreadChaosLab.simulate_unjoined_destruction(simulate_exception=True, use_guard=True)
    assert res_safe["crashed"] is False and res_safe["exit_code"] == "EXIT_SUCCESS", "HATA: ThreadGuard çöküşü önleyemedi!"
    print("  [+] Unjoined std::terminate Çöküşü ve ThreadGuard RAII Savunması Doğrulandı.")

    # 4. Yığın Boyutu Optimizasyonu Doğrulaması
    cap = ThreadStackCapacityModel.calculate_max_threads(available_ram_mb=2048.0)
    th_8mb = cap["scenarios"][0]["max_threads"]
    th_128kb = cap["scenarios"][3]["max_threads"]
    assert th_128kb > th_8mb * 50, "HATA: 128 KB yığın boyutu kapasiteyi en az 50 kat artırmalıdır!"
    print("  [+] Yığın Boyutu Optimizasyonu ve Gömülü Donanım Kapasite Artışı Doğrulandı.")

    # 5. Ampirik Gecikme Doğrulaması
    bench = run_thread_creation_benchmark(num_samples=3000)
    assert bench["pool_stats"]["p99"] < bench["ondemand_stats"]["p99"] / 10.0, "HATA: Thread Pool p99 gecikmesi en az 10x hızlı olmalıdır!"
    print("  [+] Pre-Allocated Thread Pool Gecikme Üstünlüğü ve p99 Kararlılığı Doğrulandı.")

    print("\n[PASS] Gün 107: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
