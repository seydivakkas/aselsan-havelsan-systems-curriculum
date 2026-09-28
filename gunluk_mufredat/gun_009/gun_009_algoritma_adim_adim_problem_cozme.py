#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

GÜN 009: Algoritma ve Adım Adım Problem Çözme
Çalıştırılabilir Simülasyon, Sabotaj, Benchmark & 4-Panelli Doğrulama Dashboard'u
"""

import os
import sys
import time
import random
from typing import Dict, List, Optional, Tuple

# Windows Konsol UTF-8 Ayarı
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Matplotlib headless backend
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


# =====================================================================
# MODÜL 1: Algoritmik Karmaşıklık Motoru (Big-O Benchmark)
# =====================================================================

def linear_search(arr: List[int], target: int) -> Tuple[int, int]:
    """O(N) Karmaşıklığında Doğrusal Arama. (index, adım_sayısı) döner."""
    steps = 0
    for idx, val in enumerate(arr):
        steps += 1
        if val == target:
            return idx, steps
    return -1, steps

def binary_search(arr: List[int], target: int) -> Tuple[int, int]:
    """O(log N) Karmaşıklığında İkili Arama. (index, adım_sayısı) döner."""
    low = 0
    high = len(arr) - 1
    steps = 0
    while low <= high:
        steps += 1
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid, steps
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1, steps


# =====================================================================
# MODÜL 2: Deterministik Sonlu Durum Makinesi (FSM - Finite State Machine)
# =====================================================================

class MissileState:
    SAFE = "GÜVENLİ / BEKLEME"
    LOCKED = "HEDEFE KİLİTLİ"
    LAUNCHED = "ATEŞLENDİ / UÇUŞ"
    TERMINAL_GUIDANCE = "SON YAKLAŞMA GÜDÜMÜ"
    DETONATED = "İMHA EDİLDİ"
    FAIL_SAFE = "GÜVENLİ İPTAL / ACİL DURUM"


class MissileFSM:
    """Aviyonik ve füze sistemlerinde kullanılan deterministik durum makinesi."""
    def __init__(self):
        self.state = MissileState.SAFE
        self.history: List[str] = [self.state]

    def transition(self, event: str) -> str:
        """Deterministik O(1) durum geçişi."""
        prev = self.state
        if self.state == MissileState.SAFE:
            if event == "LOCK_ACQUIRED":
                self.state = MissileState.LOCKED
        elif self.state == MissileState.LOCKED:
            if event == "FIRE_COMMAND":
                self.state = MissileState.LAUNCHED
            elif event == "LOCK_LOST":
                self.state = MissileState.SAFE
        elif self.state == MissileState.LAUNCHED:
            if event == "RADAR_TERMINAL_RANGE":
                self.state = MissileState.TERMINAL_GUIDANCE
            elif event == "ABORT":
                self.state = MissileState.FAIL_SAFE
        elif self.state == MissileState.TERMINAL_GUIDANCE:
            if event == "PROXIMITY_TRIGGER":
                self.state = MissileState.DETONATED
            elif event == "TARGET_LOST":
                self.state = MissileState.FAIL_SAFE
                
        self.history.append(self.state)
        return self.state


# =====================================================================
# MODÜL 3 & 4: Sabotaj & Watchdog Kalkanı (Halt Problem / Sonsuz Döngü)
# =====================================================================

class WatchdogTimer:
    """Sonsuz döngüye giren algoritmaları öldürüp sistemi kurtaran mekanizma."""
    def __init__(self, max_allowed_steps: int = 1000):
        self.max_steps = max_allowed_steps

    def execute_with_guard(self, step_generator) -> Tuple[bool, int, str]:
        steps = 0
        for val in step_generator:
            steps += 1
            if steps >= self.max_steps:
                return False, steps, "FAIL_SAFE_WATCHDOG_TRIP: İzin verilen adım sınırı aşıldı!"
        return True, steps, "COMPLETED_NORMALLY"


def faulty_algorithm_infinite_loop():
    """Bozuk / Sonsuz döngüye giren algoritma simülasyonu."""
    x = 0
    while True:
        x += 1
        yield x


# =====================================================================
# MODÜL 5 & 6: Ampirik Kıyaslama ve 4-Panelli Dashboard
# =====================================================================

def run_benchmarks_and_generate_dashboard():
    # 1. Big-O Karşılaştırması (N = 10 .. 2000)
    n_sizes = [10, 50, 100, 250, 500, 1000, 2000]
    lin_steps = []
    bin_steps = []
    quad_steps = [] # O(N^2)
    
    for n in n_sizes:
        arr = list(range(n))
        # En kötü durum (Worst Case): eleman dizide yok
        _, s_lin = linear_search(arr, -1)
        _, s_bin = binary_search(arr, -1)
        lin_steps.append(s_lin)
        bin_steps.append(s_bin)
        quad_steps.append(n * n / 100) # Ölçeklendirilmiş O(N^2)

    # 2. WCET ve Jitter Analizi
    # Deterministik Algoritma vs Non-deterministik / Dalgalı Algoritma
    np.random.seed(42)
    det_latencies = np.random.normal(loc=15.0, scale=0.3, size=1000) # Sabit ~15 us
    non_det_latencies = np.random.exponential(scale=12.0, size=1000) + 10.0 # P99 kuyruklu

    # 3. FSM Durum Geçişleri Ölçümü
    fsm = MissileFSM()
    fsm_events = ["LOCK_ACQUIRED", "FIRE_COMMAND", "RADAR_TERMINAL_RANGE", "PROXIMITY_TRIGGER"]
    fsm_latencies_ns = []
    
    for ev in fsm_events:
        t0 = time.perf_counter_ns()
        for _ in range(10000):
            fsm.transition(ev)
        t1 = time.perf_counter_ns()
        fsm_latencies_ns.append((t1 - t0) / 10000)

    # 4. Watchdog Sabotaj Testi
    wd = WatchdogTimer(max_allowed_steps=500)
    success, steps_taken, msg = wd.execute_with_guard(faulty_algorithm_infinite_loop())

    # ==================== GRAFİK ÇİZİMİ ====================
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0d1117')

    color_accent = '#58a6ff'
    color_warn = '#f85149'
    color_success = '#3fb950'
    color_gold = '#d29922'
    color_purple = '#bc8cff'

    # Panel 1: Big-O Büyüme Hızı (Logaritmik Ölçek)
    ax1 = axes[0, 0]
    ax1.set_facecolor('#161b22')
    ax1.plot(n_sizes, bin_steps, marker='o', color=color_success, linewidth=2.5, label='İkili Arama - O(log N)')
    ax1.plot(n_sizes, lin_steps, marker='s', color=color_accent, linewidth=2.5, label='Doğrusal Arama - O(N)')
    ax1.plot(n_sizes, quad_steps, marker='^', color=color_warn, linewidth=2.5, label='Karesel Algoritma - O(N²)')
    ax1.set_yscale('log')
    ax1.set_title('Panel 1: Algoritmik Büyüme Hızı: O(log N) vs O(N) vs O(N²)', fontsize=12, fontweight='bold', color='white', pad=10)
    ax1.set_xlabel('Girdi Boyutu (N Eleman)', fontsize=10, color='#8b949e')
    ax1.set_ylabel('Gerekli İşlem Adımı (Log Ölçek)', fontsize=10, color='#8b949e')
    ax1.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax1.legend(loc='upper left')

    # Panel 2: WCET ve Jitter Analizi
    ax2 = axes[0, 1]
    ax2.set_facecolor('#161b22')
    ax2.hist(det_latencies, bins=30, alpha=0.8, color=color_success, label=f'Deterministik (WCET={np.max(det_latencies):.1f}µs)')
    ax2.hist(non_det_latencies, bins=30, alpha=0.6, color=color_warn, label=f'Non-deterministik (Kuyruk/Jitter={np.max(non_det_latencies):.1f}µs)')
    ax2.set_title('Panel 2: Aviyonik Kritik Kısıtı: WCET vs Jitter Gecikme Dağılımı', fontsize=12, fontweight='bold', color='white', pad=10)
    ax2.set_xlabel('Gecikme (Mikrosaniye - µs)', fontsize=10, color='#8b949e')
    ax2.set_ylabel('Örnek Frekansı', fontsize=10, color='#8b949e')
    ax2.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax2.legend(loc='upper right')

    # Panel 3: FSM Durum Geçiş Gecikmesi
    ax3 = axes[1, 0]
    ax3.set_facecolor('#161b22')
    state_names = ['Kilitlenme\n(Safe->Locked)', 'Fırlatma\n(Locked->Launch)', 'Son Güdüm\n(Launch->Terminal)', 'İmha\n(Terminal->Detonated)']
    ax3.bar(state_names, fsm_latencies_ns, color=color_purple, width=0.45, alpha=0.85)
    ax3.set_title('Panel 3: Füze Durum Makinesi (FSM) O(1) Geçiş Gecikmesi', fontsize=12, fontweight='bold', color='white', pad=10)
    ax3.set_ylabel('Geçiş Gecikmesi (ns)', fontsize=10, color='#8b949e')
    ax3.set_ylim(0, max(fsm_latencies_ns) * 1.5)
    ax3.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for idx, v in enumerate(fsm_latencies_ns):
        ax3.text(idx, v + max(fsm_latencies_ns)*0.05, f'{v:.1f} ns', ha='center', color='white', fontweight='bold')

    # Panel 4: Watchdog Kalkanı ve Sonsuz Döngü Engelleme
    ax4 = axes[1, 1]
    ax4.set_facecolor('#161b22')
    categories = ['Korumasız Sistem\n(Sonsuz Kilitlenme / Crash)', 'Watchdog Korumalı\n(Fail-Safe Kurtarma)']
    recovery_rate = [0, 100]
    ax4.bar(categories, recovery_rate, color=[color_warn, color_success], width=0.45, alpha=0.85)
    ax4.set_title('Panel 4: Sabotaj Testi: Sonsuz Döngüye Karşı Watchdog Kalkanı', fontsize=12, fontweight='bold', color='white', pad=10)
    ax4.set_ylabel('Sistemin Hayatta Kalma Oranı (%)', fontsize=10, color='#8b949e')
    ax4.set_ylim(0, 115)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#30363d')

    plt.tight_layout()
    output_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_009_algoritma_adim_adim_problem_cozme.png")
    plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 009 Dashboard başarıyla üretildi: {output_png}")


# =====================================================================
# DOĞRULAMA VE ASSERT TESTLERİ
# =====================================================================

def verify_all():
    print("--- GÜN 009 SİSTEM VE MİMARİ DOĞRULAMA TESTLERİ BAŞLIYOR ---")
    
    # Test 1: Algoritmik Doğruluk (Linear vs Binary)
    test_arr = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    idx1, s1 = linear_search(test_arr, 70)
    idx2, s2 = binary_search(test_arr, 70)
    assert idx1 == 6 and idx2 == 6
    assert s2 < s1 # İkili arama doğrusal aramadan daha az adımda bulmalıdır
    print(f"[PASS] Test 1: Arama algoritmaları doğrulandı (Linear: {s1} adım, Binary: {s2} adım).")

    # Test 2: FSM Determinizm Testi
    fsm = MissileFSM()
    assert fsm.state == MissileState.SAFE
    fsm.transition("LOCK_ACQUIRED")
    assert fsm.state == MissileState.LOCKED
    fsm.transition("FIRE_COMMAND")
    assert fsm.state == MissileState.LAUNCHED
    print("[PASS] Test 2: Aviyonik Durum Makinesi (FSM) geçişleri doğrulandı.")

    # Test 3: Watchdog Sabotaj Koruması
    wd = WatchdogTimer(max_allowed_steps=200)
    ok, steps, msg = wd.execute_with_guard(faulty_algorithm_infinite_loop())
    assert ok == False
    assert steps == 200
    assert "FAIL_SAFE" in msg
    print("[PASS] Test 3: Watchdog zamanlayıcısı sonsuz döngüyü başarıyla kesti ve sistemi kurtardı.")

    # Test 4: Dashboard Üretimi
    run_benchmarks_and_generate_dashboard()
    print("[PASS] Test 4: 4-Panelli 300 DPI Dashboard üretildi.")
    print("[PASS] Gün 009: Tüm algoritma, karmaşıklık ve determinizm kuralları doğrulandı.")


if __name__ == "__main__":
    verify_all()
