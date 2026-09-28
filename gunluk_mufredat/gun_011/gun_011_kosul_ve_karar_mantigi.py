#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

GÜN 011: Koşul ve Karar Mantığı
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
# MODÜL 1: CPU Flags Register ve Karşılaştırma (CMP) Motoru
# =====================================================================

class CPUFlags:
    """İşlemcinin CMP komutu sonrası güncellediği donanımsal bayraklar."""
    def __init__(self):
        self.ZF = False # Zero Flag (Sıfır Bayrağı)
        self.CF = False # Carry Flag (Elde Bayrağı - Unsigned taşma)
        self.SF = False # Sign Flag (İşaret Bayrağı - Negatif sonuç)
        self.OF = False # Overflow Flag (Taşma Bayrağı - Signed taşma)

    def cmp(self, a: int, b: int):
        """CMP a, b komutu: Arka planda (a - b) çıkarır, bayrakları kurar."""
        diff = a - b
        self.ZF = (diff == 0)
        self.SF = (diff < 0)
        self.CF = (a < b) # 32-bit unsigned varsayımı
        # Signed 32-bit taşma denetimi
        self.OF = False
        if (a > 0 and b < 0 and diff < 0) or (a < 0 and b > 0 and diff > 0):
            self.OF = True


# =====================================================================
# MODÜL 2: Dallanmalı (Branched) vs Dallanmasız (Branchless) Motor
# =====================================================================

def branched_conditional_sum(data: List[int], threshold: int = 128) -> Tuple[int, int]:
    """Klasik if dallanması (Branch). Misprediction durumunda ceza yer."""
    total = 0
    branch_count = 0
    for v in data:
        branch_count += 1
        if v >= threshold:
            total += v
    return total, branch_count


def branchless_conditional_sum(data: List[int], threshold: int = 128) -> Tuple[int, int]:
    """
    Dallanmasız (Branchless) Programlama:
    (v >= threshold) ifadesi 1 veya 0 üretir (CMOV veya bitmask).
    İşlemci boru hattı (pipeline) asla boşaltılmaz; sıfır jitter!
    """
    total = 0
    ops = 0
    for v in data:
        ops += 1
        # C++'ta: total += v * (v >= threshold); veya CMOV komutu
        mask = int(v >= threshold)
        total += v * mask
    return total, ops


# =====================================================================
# MODÜL 3 & 4: Sabotaj & Kısa Devre (Short-Circuit) Yan Etki Tuzağı
# =====================================================================

class RadarTargetTracker:
    def __init__(self):
        self.hardware_fire_count = 0

    def check_threat_level(self, threat: int) -> bool:
        return threat > 80

    def trigger_interceptor_fire(self) -> bool:
        """Kritik yan etki (Side-effect): Füze ateşleme donanımına darbe gönderir."""
        self.hardware_fire_count += 1
        return True

    def evaluate_insecure(self, threat: int, is_armed: bool) -> bool:
        """
        KUSURLU KOD: Yan etkili fonksiyon kısa devreye güvenilerek yazılmış.
        Eğer is_armed False olsa bile yanlış sıra yüzünden füze ateşlenebilir!
        """
        # Yanlış sıra: Önce ateşleme tetiği çekiliyor, sonra silah hazır mı bakılıyor!
        return self.trigger_interceptor_fire() and is_armed and self.check_threat_level(threat)

    def evaluate_secure(self, threat: int, is_armed: bool) -> bool:
        """
        GÜVENLİ MİMARİ: Saf sorgular önce çalışır, donanımsal yan etki en son çağrılır.
        """
        if not is_armed:
            return False
        if not self.check_threat_level(threat):
            return False
        return self.trigger_interceptor_fire()


# =====================================================================
# MODÜL 5 & 6: Ampirik Kıyaslama ve 4-Panelli Dashboard
# =====================================================================

def run_benchmarks_and_generate_dashboard():
    # 1. Sıralı vs Rastgele Veride Dallanma Kıyaslaması
    n_elements = 50000
    np.random.seed(42)
    random_data = np.random.randint(0, 256, size=n_elements).tolist()
    sorted_data = sorted(random_data)

    # Sıralı veri (Branch predictor mükemmel çalışır)
    t0 = time.perf_counter_ns()
    s1, _ = branched_conditional_sum(sorted_data, 128)
    t1 = time.perf_counter_ns()
    time_sorted_ns = (t1 - t0) / n_elements

    # Rastgele veri (Branch predictor %50 çuvallar - Pipeline Flush!)
    t0 = time.perf_counter_ns()
    s2, _ = branched_conditional_sum(random_data, 128)
    t1 = time.perf_counter_ns()
    time_random_ns = (t1 - t0) / n_elements

    # Dallanmasız kod (Rastgele veride bile sabit ve hızlı)
    t0 = time.perf_counter_ns()
    s3, _ = branchless_conditional_sum(random_data, 128)
    t1 = time.perf_counter_ns()
    time_branchless_ns = (t1 - t0) / n_elements

    # 2. Donanımsal Bayraklar (Flags Matrix) Simülasyonu
    flags = CPUFlags()
    test_pairs = [
        ("A == B (10 == 10)", 10, 10),
        ("A > B  (25 > 10)", 25, 10),
        ("A < B  (5 < 20)", 5, 20)
    ]
    flag_matrix = []
    for desc, a, b in test_pairs:
        flags.cmp(a, b)
        flag_matrix.append([int(flags.ZF), int(flags.SF), int(flags.CF), int(flags.OF)])

    # 3. Kısa Devre Sabotaj Testi
    tracker_bad = RadarTargetTracker()
    tracker_good = RadarTargetTracker()
    
    # Silah hazır değil (is_armed = False), ama acemi kod yan etkiyi tetikliyor!
    for _ in range(50):
        tracker_bad.evaluate_insecure(threat=95, is_armed=False)
        tracker_good.evaluate_secure(threat=95, is_armed=False)

    # ==================== GRAFİK ÇİZİMİ ====================
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0d1117')

    color_accent = '#58a6ff'
    color_warn = '#f85149'
    color_success = '#3fb950'
    color_gold = '#d29922'
    color_purple = '#bc8cff'

    # Panel 1: Dallanma Tahmini Cezası (Sorted vs Random)
    ax1 = axes[0, 0]
    ax1.set_facecolor('#161b22')
    categories = ['Sıralı Veri\n(Branch Predictor %99 Başarılı)', 'Rastgele Veri\n(Branch Mispredict Cezası)']
    times_ns = [time_sorted_ns, time_random_ns]
    bars1 = ax1.bar(categories, times_ns, color=[color_success, color_warn], width=0.45, alpha=0.85)
    ax1.set_title('Panel 1: İşlemci Dallanma Tahmin Cezası (Branch Misprediction)', fontsize=12, fontweight='bold', color='white', pad=10)
    ax1.set_ylabel('İşlem Başına Süre (ns)', fontsize=10, color='#8b949e')
    ax1.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars1:
        h = b.get_height()
        ax1.text(b.get_x() + b.get_width()/2.0, h + 0.5, f'{h:.2f} ns', ha='center', color='white', fontweight='bold')

    # Panel 2: Branched vs Branchless Performansı
    ax2 = axes[0, 1]
    ax2.set_facecolor('#161b22')
    b_types = ['Klasik if Dallanması\n(Rastgele Veri)', 'Dallanmasız (Branchless)\n(CMOV / Maskeleme)']
    b_times = [time_random_ns, time_branchless_ns]
    bars2 = ax2.bar(b_types, b_times, color=[color_warn, color_accent], width=0.45, alpha=0.85)
    ax2.set_title('Panel 2: Determinizm Kıyaslaması: Branched if vs Branchless', fontsize=12, fontweight='bold', color='white', pad=10)
    ax2.set_ylabel('Gecikme (ns - Düşük = İyi)', fontsize=10, color='#8b949e')
    ax2.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars2:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2.0, h + 0.5, f'{h:.2f} ns', ha='center', color='white', fontweight='bold')

    # Panel 3: CPU Flags Register Isı Haritası
    ax3 = axes[1, 0]
    ax3.set_facecolor('#161b22')
    im = ax3.imshow(flag_matrix, cmap='Blues', aspect='auto')
    ax3.set_title('Panel 3: Donanımsal CPU Flags Register Matrisi (CMP a, b)', fontsize=12, fontweight='bold', color='white', pad=10)
    ax3.set_xticks([0, 1, 2, 3])
    ax3.set_xticklabels(['ZF (Zero)', 'SF (Sign)', 'CF (Carry)', 'OF (Overflow)'], fontsize=9)
    ax3.set_yticks([0, 1, 2])
    ax3.set_yticklabels([t[0] for t in test_pairs], fontsize=9)
    for i in range(3):
        for j in range(4):
            val = flag_matrix[i][j]
            ax3.text(j, i, str(val), ha='center', va='center', color='white' if val else '#8b949e', fontweight='bold', fontsize=12)

    # Panel 4: Sabotaj: Yan Etkili Kısa Devre Değerlendirme
    ax4 = axes[1, 1]
    ax4.set_facecolor('#161b22')
    eval_types = ['Kusurlu Kısa Devre\n(Yetkisiz Ateşleme Tetiklendi!)', 'Güvenli Sıralama\n(Sıfır Hatalı Ateşleme)']
    counts = [tracker_bad.hardware_fire_count, tracker_good.hardware_fire_count]
    bars4 = ax4.bar(eval_types, counts, color=[color_warn, color_success], width=0.45, alpha=0.85)
    ax4.set_title('Panel 4: Sabotaj Testi: Kısa Devre Değerlendirme (Short-Circuit) Tuzağı', fontsize=12, fontweight='bold', color='white', pad=10)
    ax4.set_ylabel('İstenmeyen Donanım Tetikleme Sayısı', fontsize=10, color='#8b949e')
    ax4.set_ylim(0, 65)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars4:
        h = b.get_height()
        ax4.text(b.get_x() + b.get_width()/2.0, h + 2, f'{h} Kez', ha='center', color='white', fontweight='bold')

    plt.tight_layout()
    output_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_011_kosul_ve_karar_mantigi.png")
    plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 011 Dashboard başarıyla üretildi: {output_png}")


# =====================================================================
# DOĞRULAMA VE ASSERT TESTLERİ
# =====================================================================

def verify_all():
    print("--- GÜN 011 SİSTEM VE MİMARİ DOĞRULAMA TESTLERİ BAŞLIYOR ---")
    
    # Test 1: CPU Flags CMP Doğrulama
    flags = CPUFlags()
    flags.cmp(100, 100)
    assert flags.ZF == True and flags.SF == False
    flags.cmp(50, 80)
    assert flags.ZF == False and flags.SF == True and flags.CF == True
    print("[PASS] Test 1: Donanımsal CPU Flags Register (ZF, SF, CF) doğrulaması başarılı.")

    # Test 2: Branched vs Branchless Eşdeğerlik
    sample_data = [50, 150, 200, 10, 80, 250]
    res1, _ = branched_conditional_sum(sample_data, 100)
    res2, _ = branchless_conditional_sum(sample_data, 100)
    assert res1 == (150 + 200 + 250)
    assert res1 == res2
    print("[PASS] Test 2: Branched vs Branchless algoritmalarının matematiksel eşdeğerliği doğrulandı.")

    # Test 3: Kısa Devre Yan Etki Koruması
    tracker = RadarTargetTracker()
    # is_armed = False olduğunda güvenli kod asla trigger_interceptor_fire() çağırmamalıdır
    res = tracker.evaluate_secure(threat=99, is_armed=False)
    assert res == False
    assert tracker.hardware_fire_count == 0
    print("[PASS] Test 3: Kısa devre mantığında yan etki (Side-effect) izolasyonu doğrulandı.")

    # Test 4: Dashboard Üretimi
    run_benchmarks_and_generate_dashboard()
    print("[PASS] Test 4: 4-Panelli 300 DPI Dashboard üretildi.")
    print("[PASS] Gün 011: Tüm koşul, karar, bayrak ve dallanma kuralları doğrulandı.")


if __name__ == "__main__":
    verify_all()
