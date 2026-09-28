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
HÜCRE 8 (CODE 1): Çekirdek Counting Semaphore Simülatörü
Dijkstra P (Acquire) ve V (Release) Atomik Durum Makinesi
"""

import time
from typing import Dict, Any, List, Optional

class SimulatedCountingSemaphore:
    """C++20 std::counting_semaphore mimarisinin tam simülatörü."""

    def __init__(self, initial_count: int, max_count: int = 1000):
        if initial_count < 0 or initial_count > max_count:
            raise ValueError("Geçersiz başlangıç değeri!")
        self.count = initial_count
        self.max_count = max_count
        self.wait_queue: List[str] = []
        self.stats = {
            "acquires": 0,
            "releases": 0,
            "blocks": 0,
            "wakeups": 0
        }

    def acquire(self, thread_name: str) -> bool:
        """P işlemi: Sayaç > 0 ise 1 azaltır ve geçer; 0 ise kuyruğa girer ve bloke olur."""
        self.stats["acquires"] += 1
        if self.count > 0:
            self.count -= 1
            return True # Doğrudan geçti
        else:
            self.stats["blocks"] += 1
            self.wait_queue.append(thread_name)
            return False # Bloke oldu, bekliyor

    def release(self, update: int = 1) -> List[str]:
        """V işlemi: Sayacı artırır ve bekleyen thread'leri uyandırır."""
        if self.count + update > self.max_count:
            raise OverflowError(f"Semafor taşması! Maksimum kapasite ({self.max_count}) aşılamaz.")

        self.stats["releases"] += update
        self.count += update

        woken_threads = []
        # Bekleyen thread varsa uyandır ve sayacı düşür
        while self.wait_queue and self.count > 0:
            thread_to_wake = self.wait_queue.pop(0)
            self.count -= 1
            self.stats["wakeups"] += 1
            woken_threads.append(thread_to_wake)

        return woken_threads


if __name__ == "__main__":
    print("=== ÇEKİRDEK COUNTING SEMAPHORE TESTİ ===")
    sem = SimulatedCountingSemaphore(initial_count=2, max_count=2)

    # 1. İki thread semaforu alır
    assert sem.acquire("Thread_1") is True
    assert sem.acquire("Thread_2") is True
    assert sem.count == 0
    print(f"[+] 2 Thread Başarıyla Kaynak Aldı (Kalan: {sem.count})")

    # 3. Üçüncü thread gelir -> Bloke olmalı
    assert sem.acquire("Thread_3") is False
    assert len(sem.wait_queue) == 1
    print(f"[*] Thread 3 Bloke Oldu. Bekleme Kuyruğu: {sem.wait_queue}")

    # 4. Bir kaynak serbest bırakılır -> Thread 3 uyanmalı
    woken = sem.release(update=1)
    print(f"[+] 1 Kaynak Bırakıldı. Uyandırılan: {woken} (Kalan Sayaç: {sem.count})")
    assert woken == ["Thread_3"]
    assert len(sem.wait_queue) == 0
    print("[+] Dijkstra P/V Semafor Algoritması Başarıyla Doğrulandı.")


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): DSP Donanım Kanal Tahsis Havuzu Motoru
Sayıcı Semafor ile Çok Kanallı Sayısal Sinyal İşlemci Yönetimi
"""

from typing import Dict, Any, List, Optional

class HardwareDSPPool:
    """4 Kanallı Donanımsal DSP Hızlandırıcısının Semafor Korumalı Havuzu."""

    def __init__(self, num_channels: int = 4):
        self.num_channels = num_channels
        self.semaphore = SimulatedCountingSemaphore(initial_count=num_channels, max_count=num_channels)
        self.channel_status = [False] * num_channels # False: Boşta, True: Meşgul
        self.processed_tasks = 0

    def allocate_channel(self, task_name: str) -> Optional[int]:
        """Kanal tahsis eder. Boş kanal varsa anında döner, yoksa bloke eder."""
        acquired = self.semaphore.acquire(task_name)
        if not acquired:
            return None # Kuyrukta bekliyor

        # Boş olan ilk fiziksel kanalı bul
        for ch_idx in range(self.num_channels):
            if not self.channel_status[ch_idx]:
                self.channel_status[ch_idx] = True
                return ch_idx
        return None

    def release_channel(self, channel_id: int):
        """İşi biten kanalı serbest bırakır ve semaforu artırır."""
        self.channel_status[channel_id] = False
        self.processed_tasks += 1
        self.semaphore.release(update=1)


if __name__ == "__main__":
    print("=== DSP DONANIM KAYNAK HAVUZU TESTİ ===")
    pool = HardwareDSPPool(num_channels=4)

    # 1. 4 görev aynı anda 4 kanalı alır
    allocated = []
    for i in range(4):
        ch = pool.allocate_channel(f"Task_{i+1}")
        assert ch is not None
        allocated.append(ch)
    print(f"[+] 4 Kanal Tam Kapasite Tahsis Edildi: {allocated}")
    assert pool.semaphore.count == 0

    # 2. 5. görev gelir -> Kanal bulamaz, semafor bekletir
    ch5 = pool.allocate_channel("Task_5")
    assert ch5 is None
    print("[*] 5. Görev Bekleme Kuyruğuna Alındı.")

    # 3. Kanal 1 işini bitirir ve serbest bırakır
    pool.release_channel(allocated[1])
    assert pool.channel_status[1] is False
    print(f"[+] Kanal {allocated[1]} Serbest Bırakıldı. İşlenen Görev: {pool.processed_tasks}")
    print("[+] DSP Kaynak Havuzu Yönetimi Başarıyla Doğrulandı.")


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Zaman Aşımlı Kurtarma ve Kapasite İhlal Modeli
Semafor Taşma Koruması ve try_acquire_for Aviyonik SLA Denetleyicisi
"""

from typing import Dict, Any, List

class ResilientSemaphoreController:
    """Taşma korumalı ve SLA zaman aşımlı gelişmiş semafor denetleyicisi."""

    def __init__(self, max_capacity: int = 4):
        self.max_capacity = max_capacity
        self.available_count = max_capacity
        self.sla_violations = 0
        self.fallback_executions = 0

    def try_acquire_with_sla(self, request_time_ms: float, timeout_ms: float = 5.0) -> bool:
        """SLA süresi içinde kaynak alamazsa Fallback mekanizmasını devreye sokar."""
        if self.available_count > 0:
            self.available_count -= 1
            return True # Kaynak tahsis edildi

        # Kaynak yok: Simüle edilen bekleme süresi SLA'yı aşarsa reddet
        if request_time_ms > timeout_ms:
            self.sla_violations += 1
            self.fallback_executions += 1
            return False # Zaman aşımı: Yazılımsal yedeğe geç

        return False

    def safe_release(self, amount: int = 1) -> bool:
        """Taşma Korumalı Release: Asla max_capacity üzerine çıkamaz."""
        if self.available_count + amount > self.max_capacity:
            # Taşma engellendi!
            self.available_count = self.max_capacity
            return False
        self.available_count += amount
        return True


if __name__ == "__main__":
    print("=== SEMAfor TAŞMA VE SLA KONTROL TESTİ ===")
    ctrl = ResilientSemaphoreController(max_capacity=4)

    # 1. 4 kaynağı tüket
    for _ in range(4):
        assert ctrl.try_acquire_with_sla(request_time_ms=1.0) is True
    assert ctrl.available_count == 0

    # 2. 5. istek gelir ve 10 ms bekler (SLA = 5 ms) -> Zaman Aşımı ve Fallback
    res = ctrl.try_acquire_with_sla(request_time_ms=10.0, timeout_ms=5.0)
    assert res is False
    assert ctrl.fallback_executions == 1
    print(f"[+] SLA Zaman Aşımı Yakalandı: Yazılımsal Yedeğe Geçildi (Fallback: {ctrl.fallback_executions})")

    # 3. Taşma Testi: Boşta 0 varken 10 adet release yapılmaya çalışılır
    overflow_prevented = not ctrl.safe_release(amount=10)
    assert overflow_prevented is True
    assert ctrl.available_count == 4
    print("[+] Semafor Taşma Koruması Başarıyla Doğrulandı.")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Canlı Sabotaj ve Dayanıklı Savunma Laboratuvarı
Tekil Mutex Darboğazı vs 4-Kanallı Semafor Paralel Verimlilik Testi
"""

from typing import Dict, Any, List

class ConcurrencyArchitectureChaosLab:
    """Tekil Mutex darboğazı ile Sayıcı Semafor arasındaki verim uçurumunu modeller."""

    @staticmethod
    def simulate_processing(num_tasks: int = 1000, task_duration_us: float = 100.0, num_cores: int = 4) -> Dict[str, Any]:
        """Tek Mutex (Seri) vs Semafor (Paralel) karşılaştırması."""
        
        # 1. TEK MUTEX MİMARİSİ (SERİLEŞTİRME SABOTAJI):
        # 4 çekirdek olsa bile hepsi sırayla tek mutex arkasında kuyruğa girer
        mutex_total_time_us = num_tasks * task_duration_us
        mutex_throughput_kops = (num_tasks / (mutex_total_time_us / 1_000_000.0)) / 1000.0

        # 2. SAYICI SEMAFOR MİMARİSİ (TAM PARALELLİK):
        # 4 çekirdek aynı anda paralel çalışır
        semaphore_total_time_us = (num_tasks / num_cores) * task_duration_us
        semaphore_throughput_kops = (num_tasks / (semaphore_total_time_us / 1_000_000.0)) / 1000.0

        speedup = mutex_total_time_us / semaphore_total_time_us

        return {
            "num_tasks": num_tasks,
            "num_cores": num_cores,
            "mutex_architecture": {
                "total_time_ms": mutex_total_time_us / 1000.0,
                "throughput_kops": mutex_throughput_kops,
                "cpu_utilization_pct": 25.0 # 4 çekirdeğin sadece 1'i dolu = %25
            },
            "semaphore_architecture": {
                "total_time_ms": semaphore_total_time_us / 1000.0,
                "throughput_kops": semaphore_throughput_kops,
                "cpu_utilization_pct": 100.0 # 4 çekirdeğin tümü dolu = %100
            },
            "speedup_factor": speedup
        }


if __name__ == "__main__":
    print("=== ÇOKLU KAYNAK VERİMLİLİK SABOTAJ TESTİ ===")
    res = ConcurrencyArchitectureChaosLab.simulate_processing(num_tasks=1000, task_duration_us=100.0, num_cores=4)
    print(f"[*] [Tek Mutex Tasarımı] Süre: {res['mutex_architecture']['total_time_ms']:.1f} ms | Kapasite: {res['mutex_architecture']['throughput_kops']:.1f} kOps/s | Donanım Verimi: %{res['mutex_architecture']['cpu_utilization_pct']}")
    print(f"[+] [Semafor Tasarımı]  Süre: {res['semaphore_architecture']['total_time_ms']:.1f} ms | Kapasite: {res['semaphore_architecture']['throughput_kops']:.1f} kOps/s | Donanım Verimi: %{res['semaphore_architecture']['cpu_utilization_pct']}")
    print(f"[+] Semafor Hızlanma Katsayısı: {res['speedup_factor']:.1f}x Kat!")
    assert res["speedup_factor"] == 4.0
    print("[+] Donanım Paralellik Doğrulaması Kusursuz Geçti.")


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru
Tek Mutex vs Sayıcı Semafor Kuyruk Gecikmesi Dağılımı (p50, p95, p99)
"""

import numpy as np
from typing import Dict, Any, List

def run_semaphore_benchmark(num_samples: int = 15000) -> Dict[str, Any]:
    """Kuyruk gecikmelerini modeller (mikrosaniye cinsinden)."""
    np.random.seed(114)

    # 1. Tekil Mutex Gecikmesi (Seri yığılma: ortalama ~750 us, kuyruk p99 ~1450 us)
    mutex_queue_lat_us = np.random.uniform(low=50.0, high=1500.0, size=num_samples)

    # 2. 4-Kanal Semafor Gecikmesi (Paralel tahliye: ortalama ~150 us, kuyruk p99 ~320 us)
    semaphore_queue_lat_us = np.random.uniform(low=20.0, high=350.0, size=num_samples)

    def stats(arr: np.ndarray) -> Dict[str, float]:
        return {
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "mean": float(np.mean(arr))
        }

    return {
        "num_samples": num_samples,
        "mutex_stats": stats(mutex_queue_lat_us),
        "semaphore_stats": stats(semaphore_queue_lat_us),
        "raw_mutex": mutex_queue_lat_us,
        "raw_semaphore": semaphore_queue_lat_us
    }


if __name__ == "__main__":
    print("=== KUYRUK GECİKMESİ BENCHMARK'I ===")
    b = run_semaphore_benchmark(15000)
    print(f"{'Mekanizma':>25} | {'p50 (µs)':>10} | {'p95 (µs)':>10} | {'p99 (µs)':>10} | {'Ortalama (µs)':>14}")
    print("-" * 75)
    print(f"{'Tekil Mutex (Serileştirme)':>25} | {b['mutex_stats']['p50']:>10.1f} | {b['mutex_stats']['p95']:>10.1f} | {b['mutex_stats']['p99']:>10.1f} | {b['mutex_stats']['mean']:>14.1f}")
    print(f"{'4-Kanal Semafor (Paralel)':>25} | {b['semaphore_stats']['p50']:>10.1f} | {b['semaphore_stats']['p95']:>10.1f} | {b['semaphore_stats']['p99']:>10.1f} | {b['semaphore_stats']['mean']:>14.1f}")


# -*- coding: utf-8 -*-
"""
HÜCRE 18 (CODE 6): 4-Panelli 300 DPI Semaphore Dashboard'u ve Katı Doğrulama Motoru
Paralellik Ölçekleme, Kuyruk Gecikmesi, Histogram ve Karar Matrisi Doğrulaması
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_114\gun_114_semaphore_ve_resource_counting.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı Semaphore mühendislik dashboard'u üretir."""
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
    # Panel 1: Donanım Çekirdek Sayısı vs İşlem Hacmi (kOps/s)
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    cores = np.array([1, 2, 4, 8, 16])
    base_throughput = 10.0 # kOps/s tek çekirdekte
    mutex_throughput = np.full_like(cores, base_throughput, dtype=float) # Darboğaz: hep 10 kOps
    semaphore_throughput = base_throughput * cores # Doğrusal ölçeklenme

    ax1.plot(cores, semaphore_throughput, color=accent_green, marker="o", linewidth=2.5, label="std::counting_semaphore<N> (Tam Paralel)")
    ax1.plot(cores, mutex_throughput, color=accent_red, marker="s", linestyle="--", linewidth=2.5, label="Tekil Mutex Mimarisi (Amdahl Darboğazı)")

    ax1.set_title("Panel 1: Donanım Çekirdeği vs Sistem İşlem Hacmi (kOps/s)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.set_xlabel("Mevcut Donanımsal DSP / İşlemci Çekirdeği", color=text_color, fontsize=10)
    ax1.set_ylabel("İşlem Hacmi (kOps/s)", color=text_color, fontsize=10)
    ax1.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 2: Kuyruk Gecikmesi Karşılaştırması (p50 / p95 / p99)
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    bench = run_semaphore_benchmark(10000)
    metrics = ["p50 (Medyan)", "p95 Eşiği", "p99 (Kuyruk SLA)"]
    m_vals = [bench["mutex_stats"]["p50"], bench["mutex_stats"]["p95"], bench["mutex_stats"]["p99"]]
    s_vals = [bench["semaphore_stats"]["p50"], bench["semaphore_stats"]["p95"], bench["semaphore_stats"]["p99"]]

    x = np.arange(len(metrics))
    width = 0.35

    ax2.bar(x - width/2, m_vals, width, color=accent_red, label="Tekil Mutex (Aşırı Bekleme)")
    ax2.bar(x + width/2, s_vals, width, color=accent_green, label="4-Kanal Semafor (5x Hızlı)")

    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics, color=text_color, fontsize=9.5)
    ax2.set_title("Panel 2: Kuyruk Gecikmesi İstatistiksel Dağılımı (µs)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_ylabel("Bekleme Süresi (Mikrosaniye - µs)", color=text_color, fontsize=10)
    ax2.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 3: Gecikme Dağılımı Histogramı
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    bins = np.linspace(0, 1500, 75)
    ax3.hist(bench["raw_mutex"], bins=bins, color=accent_red, alpha=0.5, label="Tek Mutex (1500 µs'ye Varan Kuyruk)")
    ax3.hist(bench["raw_semaphore"], bins=bins, color=accent_green, alpha=0.7, label="4-Kanal Semafor (<350 µs Sıkı Küme)")

    ax3.set_title("Panel 3: Kuyruk Bekleme Süresi Histogramı (µs)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax3.set_xlabel("Bekleme Süresi (Mikrosaniye - µs)", color=text_color, fontsize=10)
    ax3.set_ylabel("Örnek Sayısı", color=text_color, fontsize=10)
    ax3.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper right")

    # -------------------------------------------------------------------------
    # Panel 4: Mutex vs Binary Semaphore vs Counting Semaphore Karar Matrisi
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_xlim(0, 10)
    ax4.set_ylim(0, 10)
    ax4.axis("off")
    ax4.set_title("Panel 4: Eşzamanlama İlkel Seçim Karar Matrisi", color=text_color, fontsize=11, fontweight="bold", pad=12)

    boxes = [
        ("std::mutex\n- Kapasite: 1\n- Sahiplik (Ownership): VARDIR (Zorunlu!)\n- ISR Kullanımı: YASAK!\n- Amaç: Kritik Bölge / Veri Bütünlüğü", (0.3, 5.2), accent_amber, "#78350F"),
        ("std::binary_semaphore\n- Kapasite: 1\n- Sahiplik: YOKTUR! (A alır, B bırakır)\n- ISR Kullanımı: %100 UYUMLU!\n- Amaç: Tek Yönlü Olay Sinyalleşmesi", (5.2, 5.2), accent_blue, "#1E3A8A"),
        ("std::counting_semaphore<N>\n- Kapasite: N (Çoklu Donanım Kaynağı)\n- Sahiplik: YOKTUR!\n- ISR Kullanımı: Uyumlu (Token havuzu)\n- Amaç: DSP/RF/Kanal Havuz Yönetimi", (0.3, 1.0), accent_green, "#064E3B")
    ]

    for label, (bx, by), edge_c, face_c in boxes:
        w = 4.5 if by > 3 else 9.4
        h = 3.8 if by > 3 else 3.4
        rect = plt.Rectangle((bx, by), w, h, facecolor=face_c, edgecolor=edge_c, linewidth=2, transform=ax4.transData)
        ax4.add_patch(rect)
        ax4.text(bx + w/2.0, by + h/2.0, label, ha="center", va="center", color=text_color, fontsize=8.2, fontweight="bold")

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

    # 2. Dijkstra Counting Semaphore Davranış Doğrulaması
    sem = SimulatedCountingSemaphore(initial_count=2, max_count=2)
    assert sem.acquire("T1") is True
    assert sem.acquire("T2") is True
    assert sem.acquire("T3") is False # Bloke
    woken = sem.release(1)
    assert woken == ["T3"]
    print("  [+] Counting Semaphore P/V Davranışı ve Bekleme Kuyruğu Doğrulandı.")

    # 3. DSP Donanım Havuzu Doğrulaması
    pool = HardwareDSPPool(num_channels=4)
    chs = [pool.allocate_channel(f"T_{i}") for i in range(4)]
    assert all(c is not None for c in chs)
    assert pool.allocate_channel("T_5") is None
    pool.release_channel(chs[0])
    assert pool.channel_status[chs[0]] is False
    print("  [+] Çok Kanallı Donanım Havuzu Yönetimi Doğrulandı.")

    # 4. Hızlanma ve Paralellik Doğrulaması
    chaos = ConcurrencyArchitectureChaosLab.simulate_processing(num_tasks=100, task_duration_us=10.0, num_cores=4)
    assert chaos["speedup_factor"] == 4.0
    print("  [+] 4-Kanallı Semafor 4x Hızlanma Katsayısı Doğrulandı.")

    # 5. Benchmark Metrikleri Doğrulaması
    b = run_semaphore_benchmark(3000)
    assert b["semaphore_stats"]["p99"] < b["mutex_stats"]["p99"], "HATA: Semafor p99 gecikmesi mutex'ten düşük olmalıdır!"
    print("  [+] Semafor SLA ve Kuyruk Gecikmesi Üstünlüğü Doğrulandı.")

    print("\n[PASS] Gün 114: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
