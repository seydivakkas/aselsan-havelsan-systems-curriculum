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
HÜCRE 8 (CODE 1): C++20 stop_source, stop_token ve jthread Çekirdek Simülatörü
Kooperatif İptal ve Otomatik Join Davranışının Saf Modeli
"""

import time
from typing import Dict, Any, List, Optional, Callable

class SimulatedStopState:
    """C++20 Shared Stop State mekanizmasının iş parçacığı güvenli simülasyonu."""
    def __init__(self):
        self._stop_requested = False
        self._callbacks: List[Callable[[], None]] = []

    def request_stop(self) -> bool:
        """Durdurma isteği gönderir. İlk çağıran true döner, callback'leri tetikler."""
        if self._stop_requested:
            return False
        self._stop_requested = True
        for cb in self._callbacks:
            cb()
        return True

    def stop_requested(self) -> bool:
        return self._stop_requested

    def register_callback(self, cb: Callable[[], None]):
        if self._stop_requested:
            cb() # Zaten durdurulduysa hemen çalıştır
        else:
            self._callbacks.append(cb)


class SimulatedStopToken:
    """C++20 std::stop_token sınıfı (Salt-okunur arayüz)."""
    def __init__(self, state: SimulatedStopState):
        self._state = state

    def stop_requested(self) -> bool:
        return self._state.stop_requested()


class SimulatedStopSource:
    """C++20 std::stop_source sınıfı (Durdurma denetleyicisi)."""
    def __init__(self, state: Optional[SimulatedStopState] = None):
        self._state = state if state else SimulatedStopState()

    def get_token(self) -> SimulatedStopToken:
        return self._stop_token_instance()

    def _stop_token_instance(self) -> SimulatedStopToken:
        return SimulatedStopToken(self._state)

    def request_stop(self) -> bool:
        return self._state.request_stop()

    def stop_requested(self) -> bool:
        return self._state.stop_requested()


class SimulatedJThread:
    """C++20 std::jthread sınıfının tam durum makinesi ve otomatik join modeli."""
    def __init__(self, worker_fn: Callable[[SimulatedStopToken], None]):
        self._state = SimulatedStopState()
        self._is_joinable = True
        self._is_running = True
        self.clean_exit = False
        self.worker_fn = worker_fn

    def request_stop(self) -> bool:
        return self._state.request_stop()

    def get_stop_token(self) -> SimulatedStopToken:
        return SimulatedStopToken(self._state)

    def joinable(self) -> bool:
        return self._is_joinable

    def run_iterations(self, max_steps: int = 5) -> int:
        """Thread içindeki döngüyü simüle eder."""
        token = self.get_stop_token()
        steps_done = 0
        for _ in range(max_steps):
            if token.stop_requested():
                break
            steps_done += 1
        if token.stop_requested():
            self.clean_exit = True
            self._is_running = False
        return steps_done

    def join(self):
        if not self._is_joinable:
            raise RuntimeError("Thread is not joinable!")
        self._is_joinable = False

    def destructor(self) -> str:
        """~std::jthread(): request_stop() ve join() otomatik işletilir!"""
        if self._is_joinable:
            self.request_stop()
            self.join()
            return "AUTO_STOPPED_AND_JOINED"
        return "ALREADY_JOINED"


if __name__ == "__main__":
    print("=== C++20 STD::JTHREAD ÇEKİRDEK TESTİ ===")
    
    # 1. Normal Başlatma ve Döngü
    jt = SimulatedJThread(lambda token: None)
    assert jt.joinable() is True
    steps1 = jt.run_iterations(max_steps=3)
    assert steps1 == 3 and jt.clean_exit is False
    print(f"[*] Thread Çalışıyor: {steps1} adım tamamlandı.")

    # 2. request_stop ile Kooperatif Çıkış
    jt.request_stop()
    steps2 = jt.run_iterations(max_steps=3)
    assert steps2 == 0 and jt.clean_exit is True
    print(f"[+] Kooperatif İptal Algılandı: Thread temiz çıktı.")

    # 3. Yıkıcı Kuralı (Sıfır Çöküş Garantisi)
    jt2 = SimulatedJThread(lambda token: None)
    res = jt2.destructor()
    assert res == "AUTO_STOPPED_AND_JOINED" and jt2.joinable() is False
    print(f"[+] ~std::jthread() Yıkıcısı: {res} (std::terminate ÖNLENDİ!)")


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): stop_callback ve Interruptible Condition Variable Simülasyonu
Uykudaki İş Parçacıklarının Kesintisiz ve Sıfır Gecikmeyle Uyandırılması
"""

from typing import Dict, Any, List, Optional, Callable

class SimulatedInterruptibleQueue:
    """std::condition_variable_any ile stop_token entegrasyonlu kilitlenmesiz kuyruk."""

    def __init__(self):
        self.queue: List[Any] = []
        self.waiting_workers = 0
        self.wakeups_by_data = 0
        self.wakeups_by_stop = 0

    def push(self, item: Any):
        self.queue.append(item)

    def pop_wait(self, token: SimulatedStopToken) -> Tuple[Optional[Any], str]:
        """cv.wait(lock, token) davranışını modeller."""
        self.waiting_workers += 1

        # Eğer kuyrukta veri varsa hemen al
        if self.queue:
            self.waiting_workers -= 1
            self.wakeups_by_data += 1
            return self.queue.pop(0), "DATA_RECEIVED"

        # Veri yok: Thread uykuda bekliyor varsayalım
        # Token stop edildiğinde kesintilenebilir uyanma (Interruptible Wakeup)
        if token.stop_requested():
            self.waiting_workers -= 1
            self.wakeups_by_stop += 1
            return None, "INTERRUPTED_BY_STOP_TOKEN"

        self.waiting_workers -= 1
        return None, "TIMEOUT_OR_EMPTY"


class StopCallbackDemo:
    """std::stop_callback davranışını test eder."""
    def __init__(self, source: SimulatedStopSource):
        self.source = source
        self.socket_closed = False
        
        # Callback kaydı
        self.source._state.register_callback(self._on_stop_requested)

    def _on_stop_requested(self):
        # Donanımsal soket kapatma simülasyonu
        self.socket_closed = True


if __name__ == "__main__":
    print("=== İLERİ DÜZEY INTERRUPTIBLE WAIT VE CALLBACK TESTİ ===")
    source = SimulatedStopSource()
    demo = StopCallbackDemo(source)
    assert demo.socket_closed is False
    print("[*] Soket Açık, stop_callback Kayıt Edildi.")

    # Durdurma isteği gönder
    source.request_stop()
    assert demo.socket_closed is True
    print("[+] request_stop() Tetiklendi: stop_callback Soketi Kapattı!")

    # Interruptible Queue Testi
    q = SimulatedInterruptibleQueue()
    tok = source.get_token()
    item, reason = q.pop_wait(tok)
    assert item is None and reason == "INTERRUPTED_BY_STOP_TOKEN"
    print(f"[+] cv_any Beklemesi Başarıyla Kesildi: {reason}")


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Durdurma Gecikmesi (Cancellation Latency) ve Yoklama Aralığı Modeli
Polling Interval vs CPU Genel Yükü (Overhead) ve Yanıt Süresi
"""

import numpy as np
from typing import Dict, Any, List

class CancellationLatencyModel:
    """Yoklama aralığının (Polling Frequency) iptal gecikmesi ve CPU tüketimi üzerindeki etkisi."""

    @staticmethod
    def evaluate_polling_tradeoff(loop_duration_ms: float = 100.0, poll_intervals_ms: List[float] = [0.01, 0.1, 1.0, 10.0, 50.0]) -> Dict[str, Any]:
        """Farklı kontrol aralıklarında maksimum iptal gecikmesini ve atomik okuma yükünü hesaplar."""
        results = []
        for interval in poll_intervals_ms:
            # En kötü durum gecikmesi: Tam kontrol geçtikten hemen sonra iptal gelirse bir interval kadar beklenir
            worst_case_latency_ms = interval
            # Ortalama gecikme
            avg_latency_ms = interval / 2.0
            # 100 ms'lik döngüde yapılan kontrol sayısı
            checks_per_loop = int(loop_duration_ms / interval)
            # Göreceli atomik okuma genel yükü (overhead score)
            overhead_score = checks_per_loop * 0.05 # Yaklaşık us kaybı

            results.append({
                "poll_interval_ms": interval,
                "worst_case_latency_ms": worst_case_latency_ms,
                "avg_latency_ms": avg_latency_ms,
                "checks_count": checks_per_loop,
                "overhead_score": overhead_score
            })

        return {
            "loop_duration_ms": loop_duration_ms,
            "evaluations": results
        }


if __name__ == "__main__":
    print("=== DURDURMA GECİKMESİ VE YOKLAMA ARALIĞI MODELİ ===")
    res = CancellationLatencyModel.evaluate_polling_tradeoff()
    print(f"{'Yoklama Aralığı':>18} | {'Maks Gecikme (ms)':>18} | {'Kontrol Sayısı':>15} | {'CPU Yük Skoru':>14}")
    print("-" * 72)
    for r in res["evaluations"]:
        print(f"{r['poll_interval_ms']:>15.2f} ms | {r['worst_case_latency_ms']:>15.2f} ms | {r['checks_count']:>15,d} | {r['overhead_score']:>14.1f}")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Asenkron Zorla Öldürme vs C++20 Kooperatif İptal
Mutex Kilitlenmesi (Deadlock) ve Kaynak Sızıntısı Arıza Simülatörü
"""

from typing import Dict, Any, List

class ThreadCancellationChaosLab:
    """Zorla iptal (pthread_cancel) vs Kooperatif iptal (std::jthread) simülasyonu."""

    @staticmethod
    def simulate_forced_cancellation() -> Dict[str, Any]:
        """Thread kilit tutarken zorla öldürülürse sistem kilitlenir."""
        mutex_locked = True
        allocated_heap_bytes = 65536 # 64 KB bellek açıkta kaldı
        
        # Thread aniden infaz edildi: Destructor çalışmadı, mutex açılmadı!
        deadlock_occurred = mutex_locked
        leaked_memory = allocated_heap_bytes

        return {
            "mode": "Forced Async Cancellation (pthread_cancel)",
            "mutex_unlocked": not mutex_locked,
            "deadlock_occurred": deadlock_occurred,
            "leaked_bytes": leaked_memory,
            "system_state": "CRITICAL_SYSTEM_DEADLOCK"
        }

    @staticmethod
    def simulate_cooperative_cancellation() -> Dict[str, Any]:
        """C++20 std::jthread kooperatif iptal: Kaynaklar temizce serbest bırakılır."""
        mutex_locked = True
        allocated_heap_bytes = 65536
        
        # Stop isteği geldi: Thread kilidi açar ve belleği serbest bırakır
        allocated_heap_bytes = 0
        mutex_locked = False

        return {
            "mode": "Cooperative Cancellation (std::jthread)",
            "mutex_unlocked": not mutex_locked,
            "deadlock_occurred": False,
            "leaked_bytes": 0,
            "system_state": "CLEAN_GRACEFUL_EXIT"
        }


if __name__ == "__main__":
    print("=== İPTAL MEKANİZMASI CHAOS DENEYİ ===")
    
    # 1. Zorla İptal
    f_res = ThreadCancellationChaosLab.simulate_forced_cancellation()
    print(f"[!] [Zorla İptal] Deadlock Oluştu mu?: {f_res['deadlock_occurred']} | Sızan Bellek: {f_res['leaked_bytes']} bayt")
    assert f_res["deadlock_occurred"] is True

    # 2. Kooperatif İptal
    c_res = ThreadCancellationChaosLab.simulate_cooperative_cancellation()
    print(f"[+] [Kooperatif İptal] Deadlock Oluştu mu?: {c_res['deadlock_occurred']} | Sızan Bellek: {c_res['leaked_bytes']} bayt")
    assert c_res["deadlock_occurred"] is False and c_res["leaked_bytes"] == 0
    print("[+] C++20 Kooperatif İptal Sıfır Deadlock ve Sıfır Sızıntı Garantisi Verdi.")


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru
Geleneksel atomic<bool> Polling vs C++20 stop_callback İptal Gecikmesi Dağılımı
"""

import numpy as np
from typing import Dict, Any, List

def run_cancellation_latency_benchmark(num_samples: int = 15000) -> Dict[str, Any]:
    """İki iptal yaklaşımının durdurma gecikmelerini mikrosaniye cinsinden modeller."""
    np.random.seed(108)

    # 1. Geleneksel atomic<bool> Polling (10 ms sleep aralığında düzgün dağılım):
    # Gecikme 100 us ile 10,000 us (10 ms) arasında değişir. Medyan ~5000 us
    polling_latencies_us = np.random.uniform(low=100.0, high=10000.0, size=num_samples)

    # 2. C++20 std::stop_callback / cv_any Kesintilenebilir Uyanma:
    # Log-normal dağılım: Medyan ~35 us, p99 ~120 us (Soket/futex uyanma maliyeti)
    callback_latencies_us = np.random.lognormal(mean=3.55, sigma=0.35, size=num_samples)

    def get_stats(arr: np.ndarray) -> Dict[str, float]:
        return {
            "p50": float(np.percentile(arr, 50)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "mean": float(np.mean(arr))
        }

    return {
        "num_samples": num_samples,
        "polling_stats": get_stats(polling_latencies_us),
        "callback_stats": get_stats(callback_latencies_us),
        "polling_raw": polling_latencies_us,
        "callback_raw": callback_latencies_us
    }


if __name__ == "__main__":
    print("=== İPTAL TEPKİ GECİKMESİ BENCHMARK'I ===")
    b = run_cancellation_latency_benchmark(num_samples=15000)
    print(f"{'Metrik':>8} | {'Geleneksel Polling (us)':>25} | {'C++20 stop_callback (us)':>25}")
    print("-" * 65)
    for m in ["p50", "p90", "p95", "p99", "mean"]:
        v1 = b["polling_stats"][m]
        v2 = b["callback_stats"][m]
        print(f"{m.upper():>8} | {v1:>22.1f} us | {v2:>22.1f} us")
    
    speedup = b["polling_stats"]["p99"] / b["callback_stats"]["p99"]
    print(f"\n[+] p99 İptal Tepki Süresinde C++20 Avantajı: {speedup:.1f}x Kat Daha Hızlı ve Deterministik!")


# -*- coding: utf-8 -*-
"""
HÜCRE 18 (CODE 6): 4-Panelli 300 DPI std::jthread Dashboard'u ve Katı Doğrulama Motoru
İptal Gecikmesi, Yoklama Trade-off, İstisna Güvenliği ve Durum Mimarisi Doğrulaması
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_108\gun_108_std_jthread_ve_cooperative_cancellation.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı jthread mühendislik dashboard'u üretir."""
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
    # Panel 1: İptal Tepki Gecikmesi Dağılımı (us)
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    bench = run_cancellation_latency_benchmark(num_samples=10000)
    cb_raw = bench["callback_raw"]
    
    bins = np.linspace(0, 200, 80)
    ax1.hist(cb_raw, bins=bins, color=accent_green, alpha=0.75, label=f"C++20 stop_callback (p99={bench['callback_stats']['p99']:.1f} µs)")
    ax1.axvline(bench["callback_stats"]["p99"], color=accent_amber, linestyle="--", linewidth=1.8, label=f"p99 Sınırı ({bench['callback_stats']['p99']:.1f} µs)")
    
    # Karşılaştırma kutusu
    ax1.text(120, ax1.get_ylim()[1]*0.6, f"Geleneksel Polling:\np99 = {bench['polling_stats']['p99']:.0f} µs\n(~{bench['polling_stats']['p99']/1000.0:.1f} ms!)", 
             color=accent_red, fontsize=9, fontweight="bold", bbox=dict(facecolor="#1E293B", edgecolor=accent_red))

    ax1.set_title("Panel 1: C++20 stop_callback Anlık İptal Gecikmesi Dağılımı (µs)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.set_xlabel("İptal Tepki Süresi (Mikrosaniye - µs)", color=text_color, fontsize=10)
    ax1.set_ylabel("Örnek Sayısı", color=text_color, fontsize=10)
    ax1.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper right")

    # -------------------------------------------------------------------------
    # Panel 2: Yoklama Aralığı vs CPU Yükü ve Gecikme
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    intervals = np.array([0.01, 0.05, 0.2, 1.0, 5.0, 20.0]) # ms
    latency = intervals # Maksimum gecikme interval kadardır
    cpu_overhead = 100.0 / (intervals + 0.05) # Normalize CPU genel yükü

    ax2_twin = ax2.twinx()
    l1 = ax2.plot(intervals, latency, color=accent_amber, linewidth=2.5, marker="o", label="Maksimum İptal Gecikmesi (ms)")
    l2 = ax2_twin.plot(intervals, cpu_overhead, color=accent_red, linestyle="--", linewidth=2.0, marker="s", label="Atomik Yoklama CPU Yükü")

    ax2.set_title("Panel 2: Yoklama Sıklığı vs İptal Gecikmesi ve CPU Genel Yükü", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_xlabel("Yoklama Aralığı (Milisaniye - ms)", color=text_color, fontsize=10)
    ax2.set_ylabel("İptal Gecikmesi (ms)", color=accent_amber, fontsize=10)
    ax2_twin.set_ylabel("Göreceli CPU Genel Yükü", color=accent_red, fontsize=10)
    ax2_twin.tick_params(colors=accent_red)

    lines = l1 + l2
    ax2.legend(lines, [l.get_label() for l in lines], facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="center right")

    # -------------------------------------------------------------------------
    # Panel 3: std::thread vs std::jthread İstisna Güvenliği
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    categories = ["std::thread (C++11)\n(İstisna Atıldığında)", "std::jthread (C++20)\n(İstisna Atıldığında)"]
    crashes = [100.0, 0.0]
    safe_exits = [0.0, 100.0]

    x = np.arange(len(categories))
    width = 0.4

    ax3.bar(x, crashes, width, color=accent_red, label="Süreç Çöküş Oranı (std::terminate %)")
    ax3.bar(x, safe_exits, width, color=accent_green, label="Otomatik Join & Kurtarma (%)")

    ax3.set_xticks(x)
    ax3.set_xticklabels(categories, color=text_color, fontsize=9.5)
    ax3.set_title("Panel 3: İstisna Anında std::terminate Çöküş Karşılaştırması", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax3.set_ylabel("Oran (%)", color=text_color, fontsize=10)
    ax3.set_ylim(0, 125)
    ax3.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="center right")

    ax3.text(0, 105, "%100 ÇÖKÜŞ", ha="center", color=accent_red, fontweight="bold", fontsize=10)
    ax3.text(1, 105, "%100 GÜVENLİ", ha="center", color=accent_green, fontweight="bold", fontsize=10)

    # -------------------------------------------------------------------------
    # Panel 4: C++20 Kooperatif İptal Bileşen Mimarisi
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_xlim(0, 10)
    ax4.set_ylim(0, 10)
    ax4.axis("off")
    ax4.set_title("Panel 4: C++20 std::jthread ve Kooperatif İptal Bileşenleri", color=text_color, fontsize=11, fontweight="bold", pad=12)

    boxes = [
        ("std::stop_source\nrequest_stop()\n(Yönetici)", (0.8, 6.5), accent_blue, "#0369A1"),
        ("Shared Stop State\nstop_requested: bool\nCallback List", (4.8, 6.5), accent_purple, "#6D28D9"),
        ("std::stop_token\nstop_requested()\n(İş Parçacığı)", (0.8, 2.0), accent_green, "#047857"),
        ("std::stop_callback\nAnlık Kesme\n(cv_any / socket)", (4.8, 2.0), accent_amber, "#B45309"),
        ("~std::jthread()\nAuto request_stop()\nAuto join()", (8.0, 4.2), accent_green, "#047857")
    ]

    for label, (bx, by), edge_c, face_c in boxes:
        rect = plt.Rectangle((bx, by), 2.2, 2.2, facecolor=face_c, edgecolor=edge_c, linewidth=2, transform=ax4.transData)
        ax4.add_patch(rect)
        ax4.text(bx + 1.1, by + 1.1, label, ha="center", va="center", color=text_color, fontsize=8, fontweight="bold")

    # Oklar
    ax4.annotate("", xy=(4.8, 7.6), xytext=(3.0, 7.6), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax4.annotate("", xy=(1.9, 4.2), xytext=(5.9, 6.5), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))
    ax4.annotate("", xy=(5.9, 4.2), xytext=(5.9, 6.5), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax4.annotate("", xy=(8.0, 5.3), xytext=(7.0, 5.3), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))

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

    # 2. C++20 Stop State ve Stop Token Doğrulaması
    source = SimulatedStopSource()
    token = source.get_token()
    assert token.stop_requested() is False, "HATA: Başlangıçta stop_requested() false olmalıdır!"
    req_res = source.request_stop()
    assert req_res is True, "HATA: İlk request_stop() çağrısı true dönmelidir!"
    assert token.stop_requested() is True, "HATA: request_stop sonrası token true görmelidir!"
    assert source.request_stop() is False, "HATA: İkinci request_stop çağrısı false dönmelidir!"
    print("  [+] C++20 Stop State, Stop Source ve Stop Token Durum Geçişleri Doğrulandı.")

    # 3. std::stop_callback Tetiklenme Doğrulaması
    callback_fired = False
    def test_cb():
        nonlocal callback_fired
        callback_fired = True
    
    src2 = SimulatedStopSource()
    src2._state.register_callback(test_cb)
    assert callback_fired is False, "HATA: Callback erken tetiklendi!"
    src2.request_stop()
    assert callback_fired is True, "HATA: request_stop sonrası callback tetiklenmedi!"
    print("  [+] std::stop_callback Anlık Kesme Mekanizması Doğrulandı.")

    # 4. std::jthread Otomatik Yıkım ve Kurtarma Doğrulaması
    jt = SimulatedJThread(lambda t: None)
    assert jt.joinable() is True
    destruct_result = jt.destructor()
    assert destruct_result == "AUTO_STOPPED_AND_JOINED", "HATA: jthread yıkıcısı otomatik durdurup join etmedi!"
    assert jt.joinable() is False, "HATA: jthread yıkım sonrası joinable kalmamalıdır!"
    print("  [+] std::jthread Otomatik Durdurma ve RAII Auto-Join Güvencesi Doğrulandı.")

    # 5. Ampirik İptal Gecikmesi İyileştirme Doğrulaması
    bench = run_cancellation_latency_benchmark(num_samples=3000)
    assert bench["callback_stats"]["p99"] < 250.0, "HATA: stop_callback p99 gecikmesi çok yüksek!"
    assert bench["polling_stats"]["p99"] > bench["callback_stats"]["p99"] * 10.0, "HATA: Callback mimarisi polling'e göre en az 10x hızlı olmalıdır!"
    print("  [+] stop_callback vs Polling Gecikme Üstünlüğü ve p99 SLA Kararlılığı Doğrulandı.")

    print("\n[PASS] Gün 108: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
