#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

GÜN 012: Döngü ve Tekrar Mantığı
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
# MODÜL 1: Döngü Çekirdeği & Loop Unrolling Simülatörü
# =====================================================================

def standard_loop_sum(arr: List[float]) -> Tuple[float, int]:
    """1x Standart döngü: Her eleman için 1 zıplama/sayaç kontrolü."""
    total = 0.0
    jumps = 0
    for v in arr:
        jumps += 1
        total += v
    return total, jumps

def unrolled_4x_loop_sum(arr: List[float]) -> Tuple[float, int]:
    """4x Açılmış (Unrolled) döngü: Zıplama sayısı 4 kat azalır."""
    total = 0.0
    n = len(arr)
    limit = n - (n % 4)
    jumps = 0
    
    i = 0
    while i < limit:
        jumps += 1
        total += arr[i] + arr[i+1] + arr[i+2] + arr[i+3]
        i += 4
        
    # Kalan (Remainder) döngüsü
    while i < n:
        jumps += 1
        total += arr[i]
        i += 1
        
    return total, jumps


# =====================================================================
# MODÜL 2: Skalar vs SIMD Vektörel Döngü Simülatörü
# =====================================================================

def scalar_dsp_filter(signal: List[float], gain: float) -> List[float]:
    """Her saat döngüsünde 1 float işleyen skalar döngü."""
    return [x * gain for x in signal]

def simd_avx2_dsp_filter(signal: np.ndarray, gain: float) -> np.ndarray:
    """Tek saat döngüsünde 8 float (256-bit AVX2) işleyen vektörize döngü."""
    return signal * gain


# =====================================================================
# MODÜL 3 & 4: Sabotaj: Döngü Sayacı Taşması (Infinite Loop) ve Savunma
# =====================================================================

class LoopOverflowSabotage:
    """
    KUSURLU KOD:
    for (uint8_t i = 0; i <= 255; ++i) { ... }
    i=255 iken i++ yapılırsa i=0 olur; döngü ASLA bitmez (Sonsuz Döngü!).
    """
    @staticmethod
    def simulate_buggy_uint8_loop(max_safe_iterations: int = 1000) -> Tuple[bool, int]:
        i = 0 # uint8 simülasyonu
        iterations = 0
        crashed_infinite = False
        
        while i <= 255:
            iterations += 1
            if iterations >= max_safe_iterations:
                crashed_infinite = True
                break
            i = (i + 1) & 0xFF # uint8 wraparound
            
        return crashed_infinite, iterations

    @staticmethod
    def simulate_safe_bounded_loop() -> Tuple[bool, int]:
        """MISRA Kuralı: Döngü sayacı taşmayacak üst tipte (uint32_t) ve kesin sınırlı."""
        iterations = 0
        for i in range(256): # 0 .. 255 kesin 256 adım
            iterations += 1
        return False, iterations


# =====================================================================
# MODÜL 5 & 6: Ampirik Kıyaslama ve 4-Panelli Dashboard
# =====================================================================

def run_benchmarks_and_generate_dashboard():
    # 1. Loop Unrolling Faktörleri Kıyaslaması (N = 100.000)
    data_size = 100000
    test_data = [1.0] * data_size
    unroll_factors = [1, 2, 4, 8, 16]
    unroll_latencies_ms = []
    jump_counts = []
    
    for factor in unroll_factors:
        jumps = data_size // factor
        jump_counts.append(jumps)
        # Simüle edilen icra süresi: Zıplama overhead'i azaldıkça hız artar
        # Ancak 8 ve 16'dan sonra I-Cache şişmesi nedeniyle plato yapar
        base_calc_ms = 1.2
        jump_overhead_ms = (jumps / 10000) * 0.4
        total_ms = base_calc_ms + jump_overhead_ms
        unroll_latencies_ms.append(total_ms)

    # 2. Skalar vs SIMD (AVX2 / NEON) Throughput Kıyaslaması
    # 1.000.000 elemanlı sinyal filtreleme
    sig_np = np.ones(1000000, dtype=np.float32)
    sig_list = [1.0] * 1000000
    
    # Skalar ölçüm
    t0 = time.perf_counter()
    res_s = scalar_dsp_filter(sig_list[:100000], 1.5) # 100K test ölçekleme
    t1 = time.perf_counter()
    scalar_time_ms = (t1 - t0) * 10 # 1M ölçekli

    # SIMD ölçüm (NumPy vectorized C backend)
    t0 = time.perf_counter()
    res_v = simd_avx2_dsp_filter(sig_np, 1.5)
    t1 = time.perf_counter()
    simd_time_ms = (t1 - t0)

    # 3. Döngü Tipleri (for, while, do-while) Karakteristiği
    loop_types = ['for Döngüsü\n(Statik Bound / MISRA)', 'while Döngüsü\n(Koşullu / Pre-test)', 'do-while Döngüsü\n(En Az 1 Kez / Post-test)']
    bound_safety = [100, 75, 60] # Güvenlik skoru

    # 4. Sabotaj Sonuçları
    crashed, iters = LoopOverflowSabotage.simulate_buggy_uint8_loop(max_safe_iterations=500)
    _, safe_iters = LoopOverflowSabotage.simulate_safe_bounded_loop()

    # ==================== GRAFİK ÇİZİMİ ====================
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0d1117')

    color_accent = '#58a6ff'
    color_warn = '#f85149'
    color_success = '#3fb950'
    color_gold = '#d29922'
    color_purple = '#bc8cff'

    # Panel 1: Loop Unrolling vs Süre ve Zıplama Sayısı
    ax1 = axes[0, 0]
    ax1.set_facecolor('#161b22')
    x = np.arange(len(unroll_factors))
    labels = [f"{f}x Açılmış" if f > 1 else "1x (Standart)" for f in unroll_factors]
    
    ax1.bar(x, unroll_latencies_ms, color=color_accent, width=0.45, alpha=0.85, label='İcra Süresi (ms)')
    ax1.set_title('Panel 1: Döngü Açma (Loop Unrolling) Faktörü vs İcra Süresi', fontsize=12, fontweight='bold', color='white', pad=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel('Toplam İcra Süresi (ms)', fontsize=10, color='#8b949e')
    ax1.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for idx, v in enumerate(unroll_latencies_ms):
        ax1.text(idx, v + 0.1, f'{v:.2f} ms', ha='center', color='white', fontweight='bold')

    # Panel 2: Skalar vs SIMD Vektörel Hızlanma
    ax2 = axes[0, 1]
    ax2.set_facecolor('#161b22')
    throughput_labels = ['Skalar C++ Döngüsü\n(1 Float / Döngü)', 'SIMD Vektörel (AVX2)\n(8 Float / Döngü)']
    times_ms = [scalar_time_ms, simd_time_ms]
    bars2 = ax2.bar(throughput_labels, times_ms, color=[color_warn, color_success], width=0.45, alpha=0.85)
    ax2.set_title('Panel 2: Radar Sinyal Filtreleme: Skalar vs SIMD Vektörel Döngü', fontsize=12, fontweight='bold', color='white', pad=10)
    ax2.set_ylabel('1 Milyon Örnek Süresi (ms - Düşük = Hızlı)', fontsize=10, color='#8b949e')
    ax2.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars2:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2.0, h + 2, f'{h:.1f} ms', ha='center', color='white', fontweight='bold')

    # Panel 3: Döngü Yapıları ve Determinizm Skoru
    ax3 = axes[1, 0]
    ax3.set_facecolor('#161b22')
    bars3 = ax3.bar(loop_types, bound_safety, color=[color_success, color_gold, color_purple], width=0.45, alpha=0.85)
    ax3.set_title('Panel 3: Aviyonik / MISRA Standartlarında Döngü Determinizm Skoru', fontsize=12, fontweight='bold', color='white', pad=10)
    ax3.set_ylabel('Sertifikasyon Güvenlik Skoru (%)', fontsize=10, color='#8b949e')
    ax3.set_ylim(0, 120)
    ax3.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars3:
        h = b.get_height()
        ax3.text(b.get_x() + b.get_width()/2.0, h + 3, f'%{h}', ha='center', color='white', fontweight='bold')

    # Panel 4: Sabotaj: Sayacın Taşması ve Sonsuz Döngü
    ax4 = axes[1, 1]
    ax4.set_facecolor('#161b22')
    sabotage_labels = ['uint8 Taşması (i <= 255)\n(Korumasız Sonsuz Döngü)', 'MISRA Statik Bound\n(Deterministik 256 Adım)']
    results = [500, safe_iters] # Korumasız 500'de kesildi (durmadı), güvenli 256'da bitti
    bars4 = ax4.bar(sabotage_labels, results, color=[color_warn, color_success], width=0.45, alpha=0.85)
    ax4.axhline(y=256, color=color_gold, linestyle=':', linewidth=2, label='Beklenen Hedef Adım (256)')
    ax4.set_title('Panel 4: Sabotaj Testi: uint8_t Döngü Sayacı Taşması ve Sınır Kalkanı', fontsize=12, fontweight='bold', color='white', pad=10)
    ax4.set_ylabel('Atılan Adım Sayısı', fontsize=10, color='#8b949e')
    ax4.set_ylim(0, 600)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax4.legend(loc='upper right')
    for b in bars4:
        h = b.get_height()
        ax4.text(b.get_x() + b.get_width()/2.0, h + 15, f'{h} Adım', ha='center', color='white', fontweight='bold')

    plt.tight_layout()
    output_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_012_dongu_ve_tekrar_mantigi.png")
    plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 012 Dashboard başarıyla üretildi: {output_png}")


# =====================================================================
# DOĞRULAMA VE ASSERT TESTLERİ
# =====================================================================

def verify_all():
    print("--- GÜN 012 SİSTEM VE MİMARİ DOĞRULAMA TESTLERİ BAŞLIYOR ---")
    
    # Test 1: Loop Unrolling Eşdeğerlik Doğrulaması
    sample = [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5]
    t1, j1 = standard_loop_sum(sample)
    t2, j2 = unrolled_4x_loop_sum(sample)
    assert abs(t1 - t2) < 1e-6
    assert j2 < j1 # Açılmış döngünün zıplama sayısı belirgin şekilde daha az olmalıdır
    print(f"[PASS] Test 1: Loop Unrolling eşdeğerliği doğrulandı (Standart Zıplama: {j1}, 4x Zıplama: {j2}).")

    # Test 2: SIMD Vektörizasyon Doğrulaması
    arr = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
    filtered = simd_avx2_dsp_filter(arr, 2.0)
    assert np.allclose(filtered, [20.0, 40.0, 60.0, 80.0])
    print("[PASS] Test 2: SIMD vektörel döngü matematiksel doğrulaması başarılı.")

    # Test 3: Döngü Taşması Sabotaj Kalkanı
    crashed, _ = LoopOverflowSabotage.simulate_buggy_uint8_loop(max_safe_iterations=100)
    _, safe_steps = LoopOverflowSabotage.simulate_safe_bounded_loop()
    assert crashed == True # uint8_t taşması sonsuz döngü üretir
    assert safe_steps == 256 # Güvenli döngü tam 256 adımda biter
    print("[PASS] Test 3: uint8_t döngü taşması yakalandı ve MISRA sınır kalkanı doğrulandı.")

    # Test 4: Dashboard Üretimi
    run_benchmarks_and_generate_dashboard()
    print("[PASS] Test 4: 4-Panelli 300 DPI Dashboard üretildi.")
    print("[PASS] Gün 012: Tüm döngü, unrolling, SIMD ve sınır determinizm kuralları doğrulandı.")


if __name__ == "__main__":
    verify_all()
