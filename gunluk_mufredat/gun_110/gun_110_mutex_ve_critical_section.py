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
HÜCRE 8 (CODE 1): Çekirdek Mutex ve Linux Futex Durum Makinesi Simülatörü
Userspace Fast-Path (Atomik CAS) vs Kernel-space Slow-Path (sys_futex) Simülasyonu
"""

import time
from typing import Dict, Any, List, Optional

class SimulatedFutex:
    """Linux 3-durumlu futex (Fast Userspace Mutex) mimarisi simülatörü."""

    UNLOCKED = 0
    LOCKED_NO_WAITERS = 1
    LOCKED_HAS_WAITERS = 2

    def __init__(self):
        self.val = self.UNLOCKED
        self.wait_queue: List[str] = []
        self.stats = {
            "fast_path_locks": 0,
            "slow_path_waits": 0,
            "fast_path_unlocks": 0,
            "kernel_wakeups": 0,
            "total_lock_requests": 0
        }

    def lock(self, thread_name: str) -> Dict[str, Any]:
        """Kilit alma: Önce fast-path userspace CAS dener, doluysa slow-path kernel wait yapar."""
        self.stats["total_lock_requests"] += 1

        # 1. FAST-PATH (Userspace): Kilit boşsa (0 -> 1)
        if self.val == self.UNLOCKED:
            self.val = self.LOCKED_NO_WAITERS
            self.stats["fast_path_locks"] += 1
            return {
                "thread": thread_name,
                "path": "FAST_PATH_USERSPACE",
                "syscall_issued": False,
                "cost_ns": 20,
                "success": True
            }

        # 2. SLOW-PATH (Kernel Space): Kilit dolu, çekişme var
        self.val = self.LOCKED_HAS_WAITERS
        self.wait_queue.append(thread_name)
        self.stats["slow_path_waits"] += 1
        return {
            "thread": thread_name,
            "path": "SLOW_PATH_KERNEL_FUTEX_WAIT",
            "syscall_issued": True,
            "cost_ns": 1500, # ~1.5 us bağlam değişimi ve syscall
            "success": False # Kuyrukta bekliyor
        }

    def unlock(self, thread_name: str) -> Dict[str, Any]:
        """Kilit bırakma: Bekleyen yoksa userspace CAS (1 -> 0), bekleyen varsa FUTEX_WAKE."""
        if self.val == self.LOCKED_NO_WAITERS:
            self.val = self.UNLOCKED
            self.stats["fast_path_unlocks"] += 1
            return {
                "thread": thread_name,
                "path": "FAST_PATH_USERSPACE_UNLOCK",
                "syscall_issued": False,
                "woken_thread": None,
                "cost_ns": 15
            }

        # Bekleyen thread var (val == LOCKED_HAS_WAITERS)
        woken = self.wait_queue.pop(0) if self.wait_queue else None
        if not self.wait_queue:
            self.val = self.LOCKED_NO_WAITERS # Uyandırılan thread kilidi devralacak
        else:
            self.val = self.LOCKED_HAS_WAITERS

        self.stats["kernel_wakeups"] += 1
        return {
            "thread": thread_name,
            "path": "SLOW_PATH_KERNEL_FUTEX_WAKE",
            "syscall_issued": True,
            "woken_thread": woken,
            "cost_ns": 1400
        }


if __name__ == "__main__":
    print("=== LİNUX FUTEX DURUM MAKİNESİ TESTİ ===")
    futex = SimulatedFutex()

    # 1. Thread A kilidi alır (Çekişmesiz -> Fast Path)
    r1 = futex.lock("Thread_A_Radar")
    print(f"[*] Thread A Kilit İsteği: {r1['path']} | Syscall: {r1['syscall_issued']} | Maliyet: {r1['cost_ns']} ns")
    assert r1["path"] == "FAST_PATH_USERSPACE" and not r1["syscall_issued"]

    # 2. Thread B kilidi isterken Thread A içeride (Çekişmeli -> Slow Path FUTEX_WAIT)
    r2 = futex.lock("Thread_B_Telemetry")
    print(f"[*] Thread B Kilit İsteği: {r2['path']} | Syscall: {r2['syscall_issued']} | Maliyet: {r2['cost_ns']} ns")
    assert r2["path"] == "SLOW_PATH_KERNEL_FUTEX_WAIT" and r2["syscall_issued"]

    # 3. Thread A çıkar -> Bekleyen var, FUTEX_WAKE çağrılır
    u1 = futex.unlock("Thread_A_Radar")
    print(f"[+] Thread A Çıkış: {u1['path']} | Uyandırılan: {u1['woken_thread']} | Syscall: {u1['syscall_issued']}")
    assert u1["path"] == "SLOW_PATH_KERNEL_FUTEX_WAKE" and u1["woken_thread"] == "Thread_B_Telemetry"

    # 4. Thread B çıkar -> Sırada bekleyen yok, FAST_PATH unlock
    u2 = futex.unlock("Thread_B_Telemetry")
    print(f"[+] Thread B Çıkış: {u2['path']} | Syscall: {u2['syscall_issued']}")
    assert u2["path"] == "FAST_PATH_USERSPACE_UNLOCK" and not u2["syscall_issued"]
    print("\n[+] Futex Durum Geçişleri Kusursuz Doğrulandı.")


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Kritik Bölge Boyutlandırma Motoru
Kaba Taneli (Coarse-Grained) vs İnce Taneli (Fine-Grained) Kilitleme Verimliliği
"""

from typing import Dict, Any, List

class CriticalSectionGranularitySim:
    """Kritik bölge kapsamının sistem verimi ve çekişme oranına etkisini modeller."""

    @staticmethod
    def simulate_granularity(total_ops: int = 10000, num_threads: int = 8) -> Dict[str, Any]:
        """Kaba taneli kilitleme (I/O ve hesaplama kilit içinde) vs İnce taneli kilitleme (yalnızca durum güncelleme)."""
        
        # Süreler mikrosaniye (us) cinsinden
        prep_calc_us = 50.0   # Veri hazırlama, koordinat dönüşümü
        state_write_us = 2.0  # Ortak veri yapısına yazma (Tek gerçek kritik bölge)
        post_log_us = 40.0    # Telemetri formatlama, loglama

        # 1. KABA TANELİ (COARSE-GRAINED): Her şey kilit altında!
        # Kilit tutma süresi: prep + write + log = 92 us
        coarse_lock_hold_us = prep_calc_us + state_write_us + post_log_us
        # Seri darboğaz: Saniyede işlenebilecek maksimum işlem = 1,000,000 / lock_hold_us
        coarse_max_throughput = (1_000_000.0 / coarse_lock_hold_us)
        # Çekişme oranı: 8 thread aynı anda bu kilidi isterse neredeyse %100 çekişme
        coarse_contention_pct = min(98.0, (num_threads * coarse_lock_hold_us / (coarse_lock_hold_us + 10.0)) * 15.0)

        # 2. İNCE TANELİ (FINE-GRAINED / OPTIMIZED): Yalnızca state_write_us kilit altında!
        fine_lock_hold_us = state_write_us # Yalnızca 2 us!
        fine_max_throughput = (1_000_000.0 / fine_lock_hold_us)
        fine_contention_pct = min(15.0, (num_threads * fine_lock_hold_us / (prep_calc_us + post_log_us)) * 100.0)

        speedup_factor = coarse_lock_hold_us / fine_lock_hold_us # 92 / 2 = 46x teorik kilit kapasitesi!

        return {
            "num_threads": num_threads,
            "coarse": {
                "lock_duration_us": coarse_lock_hold_us,
                "max_ops_per_sec": coarse_max_throughput,
                "contention_pct": coarse_contention_pct
            },
            "fine": {
                "lock_duration_us": fine_lock_hold_us,
                "max_ops_per_sec": fine_max_throughput,
                "contention_pct": fine_contention_pct
            },
            "speedup_factor": speedup_factor
        }


if __name__ == "__main__":
    print("=== KRİTİK BÖLGE BOYUTLANDIRMA VE VERİMLİLİK ANALİZİ ===")
    sim = CriticalSectionGranularitySim.simulate_granularity(num_threads=8)
    print(f"Kaba Taneli Kilit Tutma Süresi : {sim['coarse']['lock_duration_us']:.1f} µs | Maksimum Kapasite: {sim['coarse']['max_ops_per_sec']:,.0f} ops/s | Çekişme: %{sim['coarse']['contention_pct']:.1f}")
    print(f"İnce Taneli Kilit Tutma Süresi : {sim['fine']['lock_duration_us']:.1f} µs | Maksimum Kapasite: {sim['fine']['max_ops_per_sec']:,.0f} ops/s | Çekişme: %{sim['fine']['contention_pct']:.1f}")
    print(f"[+] Kilit Darboğazı İyileştirme Katsayısı: {sim['speedup_factor']:.1f}x Kat!")
    assert sim["speedup_factor"] > 40.0


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Öncelik Ters Dönmesi (Mars Pathfinder) ve Priority Inheritance Simülatörü
Korumasız Çöküş vs PTHREAD_PRIO_INHERIT Savunması
"""

from typing import Dict, Any, List

class PriorityInversionSimulator:
    """Gerçek zamanlı görevlerin öncelik ters dönmesi ve çözüm simülasyonu."""

    @staticmethod
    def run_scenario(enable_priority_inheritance: bool = False) -> Dict[str, Any]:
        """Mars Pathfinder senaryosunu iki farklı kilit politikasıyla yürütür."""
        timeline: List[Dict[str, Any]] = []
        watchdog_deadline_ms = 120.0
        h_completion_time_ms = 0.0
        watchdog_triggered = False

        # Görev süreleri (ms)
        l_critical_work_ms = 40.0
        m_unrelated_work_ms = 100.0
        h_work_after_lock_ms = 20.0

        t = 0.0

        # t=0: L başlar ve kilidi alır
        timeline.append({"time_ms": t, "event": "Task_L_Start_And_Lock", "active_task": "L", "l_prio": "LOW"})
        t += 10.0 # L 10 ms kritik iş yapar

        # t=10: H uyanır ve kilidi ister -> Kilit L'de olduğu için BLOKE olur!
        timeline.append({"time_ms": t, "event": "Task_H_Wait_Lock_Blocked", "active_task": "L", "l_prio": "LOW"})

        if enable_priority_inheritance:
            # PRIORITY INHERITANCE DEVREDE: L'nin önceliği HIGH olur!
            timeline.append({"time_ms": t, "event": "PI_BOOST_L_PRIO_TO_HIGH", "active_task": "L", "l_prio": "HIGH"})
            # t=15: M çalışmak ister ama L artık HIGH öncelikli olduğu için M araya GİREMEZ!
            t += 30.0 # L kalan 30 ms kritik işini kesintisiz tamamlar
            timeline.append({"time_ms": t, "event": "Task_L_Release_Lock", "active_task": "H", "l_prio": "LOW_RESTORED"})
            # H derhal kilidi devralır ve çalışır
            t += h_work_after_lock_ms
            h_completion_time_ms = t
            timeline.append({"time_ms": t, "event": "Task_H_Completed_Success", "active_task": "M", "l_prio": "LOW"})
            # Ardından M çalışır
            t += m_unrelated_work_ms
        else:
            # KORUMASIZ SENARYO:
            # t=15: M uyanır. M'nin önceliği MEDIUM, L'nin önceliği LOW. M, L'yi PREEMPT eder!
            t += 5.0 # L 5 ms daha çalışır
            timeline.append({"time_ms": t, "event": "Task_M_Preempts_L", "active_task": "M", "l_prio": "LOW"})
            # M 100 ms boyunca CPU'yu esir alır!
            t += m_unrelated_work_ms
            timeline.append({"time_ms": t, "event": "Task_M_Finished", "active_task": "L", "l_prio": "LOW"})
            # Şimdi L tekrar çalışabilir ve kilidi bırakabilir
            t += 25.0
            timeline.append({"time_ms": t, "event": "Task_L_Release_Lock_Delayed", "active_task": "H", "l_prio": "LOW"})
            # H ancak şimdi başlayabilir
            t += h_work_after_lock_ms
            h_completion_time_ms = t
            if h_completion_time_ms > watchdog_deadline_ms:
                watchdog_triggered = True
                timeline.append({"time_ms": watchdog_deadline_ms, "event": "WATCHDOG_RESET_SYSTEM_CRASH", "active_task": "NONE", "l_prio": "NONE"})

        return {
            "priority_inheritance": enable_priority_inheritance,
            "h_completion_time_ms": h_completion_time_ms,
            "watchdog_deadline_ms": watchdog_deadline_ms,
            "watchdog_triggered": watchdog_triggered,
            "timeline": timeline
        }


if __name__ == "__main__":
    print("=== ÖNCELİK TERS DÖNMESİ (MARS PATHFINDER) TESTİ ===")
    # 1. Korumasız
    unprot = PriorityInversionSimulator.run_scenario(enable_priority_inheritance=False)
    print(f"[*] [Korumasız] H Tamamlanma: {unprot['h_completion_time_ms']:.1f} ms | Deadline: {unprot['watchdog_deadline_ms']} ms | Watchdog Çöküş: {unprot['watchdog_triggered']}")
    assert unprot["watchdog_triggered"] is True

    # 2. Priority Inheritance ile Korunan
    prot = PriorityInversionSimulator.run_scenario(enable_priority_inheritance=True)
    print(f"[+] [Korumalı]  H Tamamlanma: {prot['h_completion_time_ms']:.1f} ms | Deadline: {prot['watchdog_deadline_ms']} ms | Watchdog Çöküş: {prot['watchdog_triggered']}")
    assert prot["watchdog_triggered"] is False
    print("[+] Priority Inheritance Protokolü Başarıyla Doğrulandı.")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Canlı Sabotaj ve Dayanıklı Savunma Laboratuvarı
Kilit Sızıntısı (Mutex Leak / Deadlock) vs RAII Lock Guard Savunması
"""

from typing import Dict, Any, List

class SimulatedMutex:
    def __init__(self):
        self.is_locked = False
        self.owner = None

    def lock(self, thread_id: str) -> bool:
        if self.is_locked:
            return False # Kilit zaten tutuluyor, Deadlock!
        self.is_locked = True
        self.owner = thread_id
        return True

    def unlock(self):
        self.is_locked = False
        self.owner = None


class RAIIScopedLock:
    """C++ std::lock_guard benzeri RAII context manager."""
    def __init__(self, mtx: SimulatedMutex, thread_id: str):
        self.mtx = mtx
        self.thread_id = thread_id

    def __enter__(self):
        acquired = self.mtx.lock(self.thread_id)
        if not acquired:
            raise RuntimeError(f"Deadlock! Mutex halihazırda {self.mtx.owner} tarafından tutuluyor.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Exception çıksa dahi YIKICI (Destructor) kilidi koşulsuz bırakır!
        self.mtx.unlock()
        return False # Exception'ı yukarı fırlatmaya devam et


class MutexSabotageLab:
    """Manuel kilit kullanımının felaketi vs RAII'nin kusursuz güvenliği."""

    @staticmethod
    def bad_manual_lock_handler(mtx: SimulatedMutex, pkt_valid: bool) -> str:
        """Kötü tasarım: Erken return kilidi serbest bırakmayı unutur."""
        mtx.lock("Thread_Manual")
        if not pkt_valid:
            # Kasıtlı Hata: return öncesi unlock() unutuldu!
            return "EARLY_RETURN_MUTEX_LEAKED"
        mtx.unlock()
        return "SUCCESS"

    @staticmethod
    def safe_raii_lock_handler(mtx: SimulatedMutex, pkt_valid: bool) -> str:
        """Kusursuz tasarım: RAII Guard ile kilit sızıntısı imkansızdır."""
        try:
            with RAIIScopedLock(mtx, "Thread_RAII"):
                if not pkt_valid:
                    return "EARLY_RETURN_SAFE"
                return "SUCCESS"
        except Exception as e:
            return f"EXCEPTION_HANDLED: {e}"


if __name__ == "__main__":
    print("=== KİLİT SIZINTISI VE RAII SAVUNMA TESTİ ===")
    mtx_bad = SimulatedMutex()
    
    # 1. Sabotaj Testi: Geçersiz paket gelir, early return olur
    status_bad = MutexSabotageLab.bad_manual_lock_handler(mtx_bad, pkt_valid=False)
    print(f"[*] Manuel Kilit İşleyici Sonucu: {status_bad} | Mutex Kilitli mi?: {mtx_bad.is_locked}")
    assert mtx_bad.is_locked is True # Kilit sızdırıldı!

    # Sonraki thread kilit almayı dener -> SİSTEM KİLİTLENDİ (DEADLOCK)
    second_attempt = mtx_bad.lock("Thread_Next")
    print(f"[-] İkinci Thread Kilit Alabilir mi?: {second_attempt} (DEADLOCK FELAKETİ)")
    assert second_attempt is False

    # 2. RAII Savunma Testi:
    mtx_safe = SimulatedMutex()
    status_safe = MutexSabotageLab.safe_raii_lock_handler(mtx_safe, pkt_valid=False)
    print(f"[+] RAII Kilit İşleyici Sonucu: {status_safe} | Mutex Kilitli mi?: {mtx_safe.is_locked}")
    assert mtx_safe.is_locked is False # RAII yıkıcı kilidi otomatik bıraktı!

    # Sonraki thread kilidi rahatça alır
    safe_second = mtx_safe.lock("Thread_Next")
    assert safe_second is True
    mtx_safe.unlock()
    print("[+] RAII Emniyeti Başarıyla Doğrulandı.")


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru
Sıfır vs Hafif vs Ağır Çekişmede Mutex Gecikme Dağılımı (p50, p95, p99)
"""

import numpy as np
from typing import Dict, Any, List

def run_mutex_contention_benchmark(num_samples: int = 15000) -> Dict[str, Any]:
    """Farklı kilit çekişme seviyelerindeki gecikme profillerini modeller (mikrosaniye cinsinden)."""
    np.random.seed(110)

    # 1. Sıfır Çekişme (Uncontended Fast Path): ~0.025 us (25 ns)
    uncontended_us = np.random.lognormal(mean=-3.7, sigma=0.20, size=num_samples)

    # 2. Hafif Çekişme (Light Contention - 4 threads): ~0.2 us, kuyruk p99 ~ 2.5 us
    light_contention_us = np.random.lognormal(mean=-1.5, sigma=0.65, size=num_samples)

    # 3. Ağır Çekişme (Heavy Contention - 32 threads): ~8 us, kuyruk p99 ~ 80 us
    heavy_contention_us = np.random.lognormal(mean=2.0, sigma=0.75, size=num_samples)

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
        "uncontended": calc_stats(uncontended_us),
        "light": calc_stats(light_contention_us),
        "heavy": calc_stats(heavy_contention_us),
        "raw_uncontended": uncontended_us,
        "raw_light": light_contention_us,
        "raw_heavy": heavy_contention_us
    }


if __name__ == "__main__":
    print("=== MUTEX ÇEKİŞME VE GECİKME BENCHMARK'I ===")
    res = run_mutex_contention_benchmark(15000)
    print(f"{'Rejim':>20} | {'p50 (µs)':>12} | {'p95 (µs)':>12} | {'p99 (µs)':>12} | {'Ortalama (µs)':>14}")
    print("-" * 78)
    for regime in ["uncontended", "light", "heavy"]:
        st = res[regime]
        print(f"{regime.upper():>20} | {st['p50']:>12.4f} | {st['p95']:>12.4f} | {st['p99']:>12.4f} | {st['mean']:>14.4f}")


# -*- coding: utf-8 -*-
"""
HÜCRE 18 (CODE 6): 4-Panelli 300 DPI Mutex & Critical Section Dashboard'u ve Katı Doğrulama
Futex Geçişleri, Kapsam Verimi, Öncelik Ters Dönmesi ve Gecikme Dağılımı Doğrulaması
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_110\gun_110_mutex_ve_critical_section.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı Mutex & Critical Section mühendislik dashboard'u üretir."""
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
    # Panel 1: Linux Futex Fast-Path vs Slow-Path Geçişleri
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    contention_pct = np.linspace(0, 100, 50)
    # Fast path oranı çekişme arttıkça düşer
    fast_path_pct = 100.0 - contention_pct
    slow_path_pct = contention_pct

    ax1.plot(contention_pct, fast_path_pct, color=accent_green, linewidth=2.5, label="Fast-Path (Userspace CAS, ~20 ns)")
    ax1.plot(contention_pct, slow_path_pct, color=accent_red, linewidth=2.5, linestyle="--", label="Slow-Path (sys_futex Syscall, ~1.5 µs)")
    ax1.axvline(50, color=accent_amber, linestyle=":", linewidth=1.5, label="Çekişme Eşiği (%50)")

    ax1.set_title("Panel 1: Kilit Çekişmesi vs Futex Fast/Slow Path Dağılımı", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.set_xlabel("Sistem Kilit Çekişme Oranı (%)", color=text_color, fontsize=10)
    ax1.set_ylabel("İcra Yüzdesi (%)", color=text_color, fontsize=10)
    ax1.set_ylim(-2, 105)
    ax1.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="center left")

    # -------------------------------------------------------------------------
    # Panel 2: Kritik Bölge Kapsamı (Coarse vs Fine-Grained)
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    categories = ["Kaba Taneli Kilit\n(Coarse-Grained: 92 µs)", "İnce Taneli Kilit\n(Fine-Grained: 2 µs)"]
    throughput_kops = [10.87, 500.0] # kOps/sec

    x = np.arange(len(categories))
    width = 0.4

    bars = ax2.bar(x, throughput_kops, width, color=[accent_red, accent_green])
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories, color=text_color, fontsize=9.5)
    ax2.set_title("Panel 2: Kritik Bölge Boyutlandırması vs İşlem Kapasitesi (kOps/s)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_ylabel("Maksimum İşlem Hacmi (kOps/s)", color=text_color, fontsize=10)
    ax2.set_yscale("log")
    ax2.set_ylim(1, 1000)

    ax2.text(0, 15, "10.8 kOps/s\n(Aşırı Darboğaz)", ha="center", color=accent_red, fontweight="bold", fontsize=9)
    ax2.text(1, 550, "500 kOps/s\n(46x Hızlanma!)", ha="center", color=accent_green, fontweight="bold", fontsize=9)

    # -------------------------------------------------------------------------
    # Panel 3: Öncelik Ters Dönmesi (Mars Pathfinder Zaman Çizelgesi)
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    # Görev çubukları (Gantt benzeri)
    # Korumasız: L(0-15), M(15-115), L(115-140), H(140-160) -> Crash at 120
    # Korumalı: L(0-40, boosted), H(40-60), M(60-160) -> Success at 60
    y_labels = ["Korumalı (PIP)", "Korumasız (Arıza)"]
    ax3.set_yticks([0, 1])
    ax3.set_yticklabels(y_labels, color=text_color, fontsize=9.5)

    # Korumasız bloklar
    ax3.barh(1, 15, left=0, height=0.4, color=accent_blue, label="Task L (Low Prio)")
    ax3.barh(1, 100, left=15, height=0.4, color=accent_amber, label="Task M (Medium Prio - Preemption)")
    ax3.barh(1, 25, left=115, height=0.4, color=accent_blue)
    ax3.barh(1, 20, left=140, height=0.4, color=accent_purple, label="Task H (High Prio - Delayed)")
    ax3.axvline(120, color=accent_red, linestyle="--", linewidth=2, label="Watchdog Deadline (120 ms)")

    # Korumalı bloklar
    ax3.barh(0, 40, left=0, height=0.4, color=accent_blue)
    ax3.barh(0, 20, left=40, height=0.4, color=accent_purple)
    ax3.barh(0, 100, left=60, height=0.4, color=accent_amber)

    ax3.set_title("Panel 3: Öncelik Ters Dönmesi (Mars Pathfinder) Zaman Çizelgesi (ms)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax3.set_xlabel("Zaman (Milisaniye - ms)", color=text_color, fontsize=10)
    ax3.set_xlim(0, 170)
    ax3.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8, loc="upper right")

    ax3.text(122, 1.25, "WATCHDOG RESET!", color=accent_red, fontweight="bold", fontsize=8.5)
    ax3.text(62, 0.25, "H Başarıyla Tamamlandı (60 ms)", color=accent_green, fontweight="bold", fontsize=8.5)

    # -------------------------------------------------------------------------
    # Panel 4: Kilit Çekişmesinde Gecikme Dağılımları (Histogram)
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    bench = run_mutex_contention_benchmark(10000)
    
    bins = np.linspace(0, 20, 80)
    ax4.hist(bench["raw_light"], bins=bins, color=accent_blue, alpha=0.6, label=f"Hafif Çekişme (p99={bench['light']['p99']:.2f} µs)")
    ax4.hist(bench["raw_heavy"], bins=bins, color=accent_red, alpha=0.6, label=f"Ağır Çekişme (p99={bench['heavy']['p99']:.2f} µs)")

    ax4.set_title("Panel 4: Kilit Çekişmesi Gecikme Dağılımı ve Kuyruk Sıçraması (µs)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax4.set_xlabel("İşlem Süresi (Mikrosaniye - µs)", color=text_color, fontsize=10)
    ax4.set_ylabel("Örnek Frekansı", color=text_color, fontsize=10)
    ax4.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper right")

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

    # 2. Futex Fast/Slow Path Davranış Doğrulaması
    f = SimulatedFutex()
    r_fast = f.lock("T1")
    assert r_fast["path"] == "FAST_PATH_USERSPACE" and not r_fast["syscall_issued"]
    r_slow = f.lock("T2")
    assert r_slow["path"] == "SLOW_PATH_KERNEL_FUTEX_WAIT" and r_slow["syscall_issued"]
    u_wake = f.unlock("T1")
    assert u_wake["path"] == "SLOW_PATH_KERNEL_FUTEX_WAKE" and u_wake["woken_thread"] == "T2"
    u_fast = f.unlock("T2")
    assert u_fast["path"] == "FAST_PATH_USERSPACE_UNLOCK" and not u_fast["syscall_issued"]
    print("  [+] Linux Futex 3-Durumlu Durum Makinesi Başarıyla Doğrulandı.")

    # 3. Kritik Bölge Boyutlandırma Doğrulaması
    gran = CriticalSectionGranularitySim.simulate_granularity(num_threads=8)
    assert gran["speedup_factor"] > 30.0, "HATA: İnce taneli kilitleme belirgin hızlanma sağlamalıdır!"
    print("  [+] Kritik Bölge Boyutlandırma ve Amdahl Hızlanması Doğrulandı.")

    # 4. Öncelik Ters Dönmesi Doğrulaması
    p_unprot = PriorityInversionSimulator.run_scenario(enable_priority_inheritance=False)
    assert p_unprot["watchdog_triggered"] is True, "HATA: Korumasız senaryo watchdog reset üretmelidir!"
    p_prot = PriorityInversionSimulator.run_scenario(enable_priority_inheritance=True)
    assert p_prot["watchdog_triggered"] is False, "HATA: Priority Inheritance görevi kurtarmalıdır!"
    print("  [+] Mars Pathfinder Öncelik Ters Dönmesi ve PIP Çözümü Doğrulandı.")

    # 5. RAII vs Manuel Kilit Doğrulaması
    m_test = SimulatedMutex()
    status = MutexSabotageLab.bad_manual_lock_handler(m_test, pkt_valid=False)
    assert m_test.is_locked is True, "HATA: Manuel kilit early return'de sızmalıdır!"
    m_safe = SimulatedMutex()
    status_s = MutexSabotageLab.safe_raii_lock_handler(m_safe, pkt_valid=False)
    assert m_safe.is_locked is False, "HATA: RAII guard kilit bırakmayı garanti etmelidir!"
    print("  [+] RAII Kilit Sızıntısı Savunması Başarıyla Doğrulandı.")

    print("\n[PASS] Gün 110: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
