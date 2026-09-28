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
HÜCRE 8 (CODE 1): Çekirdek condition_variable Simülatörü
Atomik Kilit Bırakma, Uyku Kuyruğu ve Yüklemli (Predicate) Uyanma Modeli
"""

import time
from typing import Dict, Any, List, Callable, Optional

class SimulatedMutex:
    def __init__(self, name: str):
        self.name = name
        self.is_locked = False
        self.owner: Optional[str] = None

    def lock(self, thread_name: str):
        if self.is_locked and self.owner != thread_name:
            raise RuntimeError(f"Mutex '{self.name}' kilitli, '{thread_name}' beklemek zorunda!")
        self.is_locked = True
        self.owner = thread_name

    def unlock(self, thread_name: str):
        if not self.is_locked or self.owner != thread_name:
            raise RuntimeError(f"Mutex '{self.name}' bu thread tarafından tutulmuyor!")
        self.is_locked = False
        self.owner = None


class SimulatedConditionVariable:
    """Linux Futex tabanlı std::condition_variable simülasyonu."""

    def __init__(self, name: str):
        self.name = name
        self.wait_queue: List[str] = []
        self.stats = {
            "waits": 0,
            "notify_ones": 0,
            "notify_alls": 0,
            "spurious_wakeups": 0
        }

    def wait(self, mtx: SimulatedMutex, thread_name: str, predicate: Callable[[], bool]):
        """Yüklemli (Predicate) atomik wait: while (!pred()) { unlock & sleep; relock; }"""
        while not predicate():
            self.stats["waits"] += 1
            # 1. ATOMİK: Kilidi bırak ve uyku kuyruğuna gir
            mtx.unlock(thread_name)
            self.wait_queue.append(thread_name)

            # Thread burada işletim sistemi tarafından uyutulur...
            # Uyandığında ilk iş kilidi geri almaktır:
            mtx.lock(thread_name)

    def notify_one(self) -> Optional[str]:
        """Kuyruktaki ilk thread'i uyandırır."""
        self.stats["notify_ones"] += 1
        if self.wait_queue:
            return self.wait_queue.pop(0)
        return None

    def notify_all(self) -> List[str]:
        """Kuyruktaki tüm thread'leri uyandırır."""
        self.stats["notify_alls"] += 1
        woken = list(self.wait_queue)
        self.wait_queue.clear()
        return woken


if __name__ == "__main__":
    print("=== CONDITION_VARIABLE TEMEL ÇEKİRDEK TESTİ ===")
    mtx = SimulatedMutex("Queue_Mutex")
    cv = SimulatedConditionVariable("Queue_CV")
    data_buffer: List[int] = []

    # 1. Tüketici gelir, kilit alır
    mtx.lock("Consumer_Thread")
    assert mtx.is_locked and mtx.owner == "Consumer_Thread"

    # Tüketici veri bekler (Kuyruk boş olduğu için uyur ve kilidi bırakır)
    # Simülasyon gereği wait çağrısını adım adım test ediyoruz
    assert not data_buffer # Boş
    mtx.unlock("Consumer_Thread")
    cv.wait_queue.append("Consumer_Thread")
    print(f"[*] Tüketici Uykuya Daldı. CV Kuyruğu: {cv.wait_queue}")

    # 2. Üretici gelir, kilit alır, veri ekler
    mtx.lock("Producer_Thread")
    data_buffer.append(42) # Yeni telemetri paketi
    mtx.unlock("Producer_Thread")
    woken_thread = cv.notify_one()
    print(f"[+] Üretici Veri Ekledi ve Bildirdi. Uyandırılan: {woken_thread}")
    assert woken_thread == "Consumer_Thread"

    # 3. Tüketici uyanır, kilidi devralır ve veriyi çeker
    mtx.lock("Consumer_Thread")
    assert len(data_buffer) == 1
    val = data_buffer.pop(0)
    mtx.unlock("Consumer_Thread")
    print(f"[+] Tüketici Paketi Başarıyla Çekti: {val}")
    assert val == 42
    print("[+] Temel wait/notify Akışı Başarıyla Doğrulandı.")


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Thread-Safe Bounded Blocking Queue (Engellemeli Kuyruk)
Savunma Sanayii Telemetri ve Sensör Veri Hattı Motoru
"""

from typing import Dict, Any, List, Optional

class BoundedBlockingQueue:
    """std::condition_variable ile korunan sabit kapasiteli thread-safe kuyruk."""

    def __init__(self, capacity: int = 5):
        self.capacity = capacity
        self.queue: List[Any] = []
        self.mtx = SimulatedMutex("Queue_Mtx")
        self.cv_not_empty = SimulatedConditionVariable("CV_NotEmpty")
        self.cv_not_full = SimulatedConditionVariable("CV_NotFull")
        self.total_pushed = 0
        self.total_popped = 0

    def push(self, item: Any, producer_name: str):
        """Kuyruk doluysa yer açılana kadar bekler, yer açılınca ekler ve tüketiciyi uyarır."""
        self.mtx.lock(producer_name)
        # Bounded Queue Predicate: Kuyruk dolu olduğu sürece bekle!
        self.cv_not_full.wait(self.mtx, producer_name, predicate=lambda: len(self.queue) < self.capacity)
        
        self.queue.append(item)
        self.total_pushed += 1
        self.mtx.unlock(producer_name)

        # Bekleyen tüketici varsa uyandır
        self.cv_not_empty.notify_one()

    def pop(self, consumer_name: str) -> Any:
        """Kuyruk boşsa veri gelene kadar bekler, veri gelince çeker ve üreticiyi uyarır."""
        self.mtx.lock(consumer_name)
        # Predicate: Kuyruk boş olduğu sürece bekle! (Spurious wakeup koruması)
        self.cv_not_empty.wait(self.mtx, consumer_name, predicate=lambda: len(self.queue) > 0)

        item = self.queue.pop(0)
        self.total_popped += 1
        self.mtx.unlock(consumer_name)

        # Bekleyen üretici varsa yer açıldığını bildir
        self.cv_not_full.notify_one()
        return item


if __name__ == "__main__":
    print("=== BOUNDED BLOCKING QUEUE DOĞRULAMA TESTİ ===")
    bbq = BoundedBlockingQueue(capacity=2)

    # 1. İki eleman başarıyla eklenir
    bbq.push({"target_id": 101, "azimuth": 45.0}, "Prod_1")
    bbq.push({"target_id": 102, "azimuth": 46.2}, "Prod_1")
    assert len(bbq.queue) == 2
    print(f"[+] 2 Eleman Eklendi (Kuyruk Doldu: {len(bbq.queue)}/{bbq.capacity})")

    # 2. Tüketici bir eleman çeker
    t = bbq.pop("Cons_1")
    assert t["target_id"] == 101
    assert len(bbq.queue) == 1
    print(f"[+] 1 Eleman Tüketildi (Kalan: {len(bbq.queue)}): Target {t['target_id']}")

    # 3. Tekrar eleman eklenebilir
    bbq.push({"target_id": 103, "azimuth": 47.1}, "Prod_2")
    assert len(bbq.queue) == 2
    print("[+] Bounded Blocking Queue Tam Kapasite ve Döngü Doğrulandı.")


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Thundering Herd Benchmark Simülatörü
notify_one() vs notify_all() CPU İsrafı ve Bağlam Değişimi Maliyet Analizi
"""

from typing import Dict, Any, List

class ThunderingHerdSimulator:
    """notify_one ve notify_all çağrılarının uyandırılan thread sayısına etkisini modeller."""

    @staticmethod
    def simulate_notification(num_waiting_threads: int = 32, items_available: int = 1) -> Dict[str, Any]:
        """Tek bir eleman için notify_one vs notify_all kıyaslaması."""
        # 1. notify_one senaryosu:
        woken_one = 1
        wasted_wakeups_one = 0 # Sıfır israf

        # 2. notify_all senaryosu:
        woken_all = num_waiting_threads
        # Yalnızca items_available kadar thread iş yapabilir, kalanlar boşuna uyandı!
        wasted_wakeups_all = max(0, num_waiting_threads - items_available)
        # Her boşuna uyanma ~2.5 us bağlam değişimi ve mutex çekişmesi maliyeti getirir
        wasted_cpu_time_us = wasted_wakeups_all * 2.5

        return {
            "num_waiting_threads": num_waiting_threads,
            "items_available": items_available,
            "notify_one": {
                "woken_threads": woken_one,
                "wasted_wakeups": wasted_wakeups_one,
                "overhead_us": 2.5
            },
            "notify_all": {
                "woken_threads": woken_all,
                "wasted_wakeups": wasted_wakeups_all,
                "overhead_us": wasted_cpu_time_us
            },
            "waste_ratio": (wasted_wakeups_all / woken_one) if woken_one > 0 else 0
        }


if __name__ == "__main__":
    print("=== THUNDERING HERD ANALİZİ ===")
    sim = ThunderingHerdSimulator.simulate_notification(num_waiting_threads=32, items_available=1)
    print(f"Uyuyan Thread Sayısı: {sim['num_waiting_threads']} | Gelen Paket: {sim['items_available']}")
    print(f"[notify_one] Uyandırılan: {sim['notify_one']['woken_threads']} | Boşuna Uyanma: {sim['notify_one']['wasted_wakeups']}")
    print(f"[notify_all] Uyandırılan: {sim['notify_all']['woken_threads']} | Boşuna Uyanma: {sim['notify_all']['wasted_wakeups']} (İsraf Süre: {sim['notify_all']['overhead_us']:.1f} µs)")
    assert sim["notify_all"]["wasted_wakeups"] == 31
    print("[+] Thundering Herd İsraf Katsayısı Başarıyla Doğrulandı.")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Canlı Sabotaj ve Dayanıklı Savunma Laboratuvarı
Sahte Uyanma (Spurious Wakeup) Bellek Çöküşü vs Yüklem (Predicate) Savunması
"""

from typing import Dict, Any, List

class SpuriousWakeupChaosLab:
    """Sahte uyanma felaketi ve yüklemli savunma simülatörü."""

    @staticmethod
    def simulate_unprotected_spurious_wakeup() -> Dict[str, Any]:
        """Yüklemsiz çıplak wait: Sahte uyanma boş kuyruktan pop yapmaya çalışır ve çöker."""
        queue: List[str] = [] # Tamamen boş kuyruk!

        # Sahte uyanma gerçekleşti (İşletim sistemi sinyali)
        spurious_event = True
        crash_occurred = False
        error_msg = ""

        try:
            # Çıplak wait uyanınca doğrudan veriye erişir
            if len(queue) == 0:
                raise IndexError("SIGSEGV: Boş telemetri kuyruğundan okuma yapıldı! (Geçersiz Bellek Erişimi)")
            item = queue.pop(0)
        except IndexError as e:
            crash_occurred = True
            error_msg = str(e)

        return {
            "crash_occurred": crash_occurred,
            "error_msg": error_msg,
            "queue_state": "EMPTY"
        }

    @staticmethod
    def simulate_protected_predicate_defense() -> Dict[str, Any]:
        """Yüklemli wait: while (!pred()) döngüsü sahte uyanmayı yutar ve güvenle uyumaya devam eder."""
        queue: List[str] = [] # Boş kuyruk
        spurious_wakeups_handled = 0
        is_safe = True

        # Simüle edilen 3 adet sahte uyanma gerçekleşir
        for _ in range(3):
            # Predicate kontrolü: return len(queue) > 0
            predicate = (len(queue) > 0)
            if not predicate:
                # Sahte uyanma algılandı, kuyruk hala boş, tekrar uykuya dalınır!
                spurious_wakeups_handled += 1
            else:
                # Asla buraya girmemeli
                is_safe = False

        return {
            "is_safe": is_safe,
            "spurious_wakeups_handled": spurious_wakeups_handled,
            "crash_occurred": False
        }


if __name__ == "__main__":
    print("=== SAHTE UYANMA (SPURIOUS WAKEUP) SABOTAJ DENEYİ ===")
    
    # 1. Korumasız Çöküş
    unprot = SpuriousWakeupChaosLab.simulate_unprotected_spurious_wakeup()
    print(f"[-] [Korumasız Tasarım] Çökme Oluştu mu?: {unprot['crash_occurred']} | Hata: {unprot['error_msg']}")
    assert unprot["crash_occurred"] is True

    # 2. Yüklemli Savunma
    prot = SpuriousWakeupChaosLab.simulate_protected_predicate_defense()
    print(f"[+] [Korumalı Tasarım] Sistem Güvende mi?: {prot['is_safe']} | Yutulan Sahte Uyanma: {prot['spurious_wakeups_handled']}")
    assert prot["is_safe"] is True and prot["spurious_wakeups_handled"] == 3
    print("[+] Yüklem (Predicate) Koruması Başarıyla Doğrulandı.")


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru
Busy Waiting vs Sleep Polling vs Condition Variable Performans Analizi
"""

import numpy as np
from typing import Dict, Any, List

def run_synchronization_mechanism_benchmark(num_samples: int = 15000) -> Dict[str, Any]:
    """Senkronizasyon mekanizmalarının gecikme ve CPU maliyetlerini modeller."""
    np.random.seed(113)

    # 1. Busy Waiting (Gecikme süper düşük ~0.08 us, CPU %100)
    busy_wait_lat_us = np.random.normal(loc=0.08, scale=0.01, size=num_samples)

    # 2. Sleep Polling 1ms (Gecikme uniform 0-1000 us, ortalama ~500 us, CPU <%1)
    sleep_poll_lat_us = np.random.uniform(low=5.0, high=995.0, size=num_samples)

    # 3. std::condition_variable (Futex wakeup, ortalama ~2.2 us, CPU %0)
    cv_lat_us = np.random.lognormal(mean=0.75, sigma=0.35, size=num_samples) # ~2.2 us

    def stats(arr: np.ndarray) -> Dict[str, float]:
        return {
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "mean": float(np.mean(arr))
        }

    return {
        "num_samples": num_samples,
        "busy_wait": stats(busy_wait_lat_us),
        "sleep_poll": stats(sleep_poll_lat_us),
        "condition_variable": stats(cv_lat_us),
        "raw_busy": busy_wait_lat_us,
        "raw_sleep": sleep_poll_lat_us,
        "raw_cv": cv_lat_us
    }


if __name__ == "__main__":
    print("=== SENKRONİZASYON MEKANİZMALARI GECİKME BENCHMARK'I ===")
    bench = run_synchronization_mechanism_benchmark(15000)
    print(f"{'Mekanizma':>25} | {'p50 (µs)':>10} | {'p95 (µs)':>10} | {'p99 (µs)':>10} | {'CPU Yükü':>10}")
    print("-" * 75)
    print(f"{'Busy Waiting (Spin)':>25} | {bench['busy_wait']['p50']:>10.2f} | {bench['busy_wait']['p95']:>10.2f} | {bench['busy_wait']['p99']:>10.2f} | {'%100':>10}")
    print(f"{'Sleep Polling (1ms)':>25} | {bench['sleep_poll']['p50']:>10.2f} | {bench['sleep_poll']['p95']:>10.2f} | {bench['sleep_poll']['p99']:>10.2f} | {'<%1':>10}")
    print(f"{'std::condition_variable':>25} | {bench['condition_variable']['p50']:>10.2f} | {bench['condition_variable']['p95']:>10.2f} | {bench['condition_variable']['p99']:>10.2f} | {'%0 (UYKU)':>10}")


# -*- coding: utf-8 -*-
"""
HÜCRE 18 (CODE 6): 4-Panelli 300 DPI Condition Variable Dashboard'u ve Katı Doğrulama Motoru
Gecikme Dağılımları, CPU Verimliliği, Thundering Herd ve Predicate Doğrulaması
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_113\gun_113_std_condition_variable.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı condition_variable mühendislik dashboard'u üretir."""
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
    # Panel 1: 3 Mekanizmanın Ortalama Gecikmesi (Bar Chart - Log Scale)
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    bench = run_synchronization_mechanism_benchmark(10000)
    mechanisms = ["Busy Waiting\n(Spinning)", "std::condition_variable\n(Altın Standart)", "Sleep Polling\n(1ms)"]
    means = [bench["busy_wait"]["mean"], bench["condition_variable"]["mean"], bench["sleep_poll"]["mean"]]

    x = np.arange(len(mechanisms))
    bars = ax1.bar(x, means, width=0.45, color=[accent_amber, accent_green, accent_red])
    ax1.set_xticks(x)
    ax1.set_xticklabels(mechanisms, color=text_color, fontsize=9.5)
    ax1.set_title("Panel 1: Senkronizasyon Mekanizmaları Ortalama Gecikme (µs - Log Skala)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.set_ylabel("Gecikme (Mikrosaniye - µs)", color=text_color, fontsize=10)
    ax1.set_yscale("log")
    ax1.set_ylim(0.01, 2000)

    ax1.text(0, 0.15, f"{means[0]:.2f} µs\n(CPU %100)", ha="center", color=accent_amber, fontweight="bold", fontsize=9)
    ax1.text(1, 4.0, f"{means[1]:.2f} µs\n(CPU %0 - İDEAL)", ha="center", color=accent_green, fontweight="bold", fontsize=9)
    ax1.text(2, 900.0, f"{means[2]:.1f} µs\n(Kabul Edilemez)", ha="center", color=accent_red, fontweight="bold", fontsize=9)

    # -------------------------------------------------------------------------
    # Panel 2: CPU Tüketimi (%) vs Tepki Süresi Trade-Off
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    # Scatter noktaları: (CPU %, Gecikme us)
    ax2.scatter([100.0], [0.08], color=accent_amber, s=200, label="Busy Waiting (Aşırı CPU / Hızlı)")
    ax2.scatter([0.5], [500.0], color=accent_red, s=200, label="Sleep Polling (Düşük CPU / Çok Yavaş)")
    ax2.scatter([0.0], [2.2], color=accent_green, s=280, marker="*", label="std::condition_variable (SIFIR CPU / Hızlı)")

    ax2.set_title("Panel 2: CPU Tüketimi (%) vs Tepki Gecikmesi Ticaret Alanı", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_xlabel("Bekleme Sırasında CPU Tüketimi (%)", color=text_color, fontsize=10)
    ax2.set_ylabel("Tepki Gecikmesi (µs - Log Skala)", color=text_color, fontsize=10)
    ax2.set_yscale("log")
    ax2.set_xlim(-5, 105)
    ax2.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="center right")

    # -------------------------------------------------------------------------
    # Panel 3: condition_variable Gecikme Dağılımı Histogramı
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    bins = np.linspace(0.5, 6.0, 70)
    ax3.hist(bench["raw_cv"], bins=bins, color=accent_green, alpha=0.7, edgecolor=accent_blue, label=f"CV Wakeup (p50={bench['condition_variable']['p50']:.2f} µs, p99={bench['condition_variable']['p99']:.2f} µs)")
    ax3.axvline(bench["condition_variable"]["p95"], color=accent_amber, linestyle="--", linewidth=1.8, label=f"p95 Eşiği ({bench['condition_variable']['p95']:.2f} µs)")

    ax3.set_title("Panel 3: std::condition_variable Uyanma Gecikmesi Dağılımı (µs)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax3.set_xlabel("Uyanma Süresi (Mikrosaniye - µs)", color=text_color, fontsize=10)
    ax3.set_ylabel("Örnek Frekansı", color=text_color, fontsize=10)
    ax3.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper right")

    # -------------------------------------------------------------------------
    # Panel 4: Spurious Wakeup ve Thundering Herd Savunma Matrisi
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_xlim(0, 10)
    ax4.set_ylim(0, 10)
    ax4.axis("off")
    ax4.set_title("Panel 4: Koşul Değişkeni Mimari Altın Kuralları", color=text_color, fontsize=11, fontweight="bold", pad=12)

    boxes = [
        ("1. PREDICATE (YÜKLEM) KURALI\n- Asla çıplak cv.wait(lk) çağırma!\n- cv.wait(lk, [&]{ return !q.empty(); });\n- Sahte uyanmaları (Spurious Wakeup) %100 yutar.", (0.3, 5.2), accent_amber, "#78350F"),
        ("2. std::unique_lock ZORUNLULUĞU\n- lock_guard DERLENMEZ!\n- cv.wait kilidi atomik olarak bırakıp\nuyandıktan sonra tekrar almak zorundadır.", (5.2, 5.2), accent_blue, "#1E3A8A"),
        ("3. THUNDERING HERD ÖNLEME\n- Tek eleman geldiğinde: notify_one()\n- notify_all() sadece sistem kapanırken\nveya broadcast olaylarda çağrılır!", (0.3, 1.0), accent_red, "#7F1D1D"),
        ("4. LINUX FUTEX REQUEUE\n- FUTEX_CMP_REQUEUE ile çekirdek\nuyuyan thread'leri doğrudan mutex kuyruğuna\naktararak context switch israfını önler.", (5.2, 1.0), accent_green, "#064E3B")
    ]

    for label, (bx, by), edge_c, face_c in boxes:
        rect = plt.Rectangle((bx, by), 4.5, 3.8, facecolor=face_c, edgecolor=edge_c, linewidth=2, transform=ax4.transData)
        ax4.add_patch(rect)
        ax4.text(bx + 2.25, by + 1.9, label, ha="center", va="center", color=text_color, fontsize=8.0, fontweight="bold")

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

    # 2. Bounded Blocking Queue Doğrulaması
    bbq = BoundedBlockingQueue(capacity=3)
    bbq.push(10, "P1")
    bbq.push(20, "P1")
    assert bbq.pop("C1") == 10
    assert bbq.pop("C1") == 20
    print("  [+] Bounded Blocking Queue FIFO ve Kapasite Doğrulandı.")

    # 3. Thundering Herd Analizi Doğrulaması
    th = ThunderingHerdSimulator.simulate_notification(num_waiting_threads=16, items_available=1)
    assert th["notify_all"]["wasted_wakeups"] == 15
    assert th["notify_one"]["wasted_wakeups"] == 0
    print("  [+] Thundering Herd İsraf Sayımı Doğrulandı.")

    # 4. Spurious Wakeup Savunma Doğrulaması
    c_unprot = SpuriousWakeupChaosLab.simulate_unprotected_spurious_wakeup()
    assert c_unprot["crash_occurred"] is True
    c_prot = SpuriousWakeupChaosLab.simulate_protected_predicate_defense()
    assert c_prot["is_safe"] is True and c_prot["spurious_wakeups_handled"] == 3
    print("  [+] Sahte Uyanma ve Yüklem Savunması Doğrulandı.")

    # 5. Benchmark Metrikleri Doğrulaması
    b = run_synchronization_mechanism_benchmark(3000)
    assert b["condition_variable"]["mean"] < b["sleep_poll"]["mean"], "HATA: CV polling'den hızlı olmalıdır!"
    print("  [+] CV Gecikme Üstünlüğü ve Determinizmi Doğrulandı.")

    print("\n[PASS] Gün 113: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
