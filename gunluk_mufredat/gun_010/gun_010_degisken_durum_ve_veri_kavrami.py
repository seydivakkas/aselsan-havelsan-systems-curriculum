#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

GÜN 010: Değişken, Durum ve Veri Kavramı
Çalıştırılabilir Simülasyon, Sabotaj, Benchmark & 4-Panelli Doğrulama Dashboard'u
"""

import os
import sys
import time
import struct
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
# MODÜL 1: Bellek Düzeni, Alignment & Padding Simülasyonu
# =====================================================================

class MemoryLayoutSimulator:
    """
    struct InefficientTelemetry {
        char sensor_id;    // 1 bayt (+ 3 bayt padding)
        int  timestamp;    // 4 bayt
        short voltage_mv;  // 2 bayt (+ 2 bayt padding)
    }; // Toplam: 12 bayt! (5 bayt israf)
    
    struct OptimizedTelemetry {
        int   timestamp;   // 4 bayt
        short voltage_mv;  // 2 bayt
        char  sensor_id;   // 1 bayt (+ 1 bayt tail padding)
    }; // Toplam: 8 bayt! (Sadece 1 bayt padding)
    """
    @staticmethod
    def calculate_memory_footprint(packet_count: int) -> Tuple[int, int, int]:
        # C struct layout'u struct modülü ile tam olarak simüle edilir
        inefficient_fmt = "c x x x i h x x" # 12 bayt
        optimized_fmt   = "i h c x"         # 8 bayt
        packed_fmt      = "<c i h"          # 7 bayt (Pragma pack(1))
        
        sz_inefficient = struct.calcsize(inefficient_fmt) * packet_count
        sz_optimized   = struct.calcsize(optimized_fmt) * packet_count
        sz_packed      = struct.calcsize(packed_fmt) * packet_count
        
        return sz_inefficient, sz_optimized, sz_packed


# =====================================================================
# MODÜL 2: Deterministik Durum Vektörü (State Vector Engine)
# =====================================================================

class FlightTelemetryState:
    """Uçuş kontrol bilgisayarının durum vektörü S(t) = (alt, vel, fuel, status)."""
    def __init__(self, altitude: float = 0.0, velocity: float = 0.0, fuel: float = 100.0, status_flags: int = 0x01):
        self.altitude = altitude       # float64 (8 bayt)
        self.velocity = velocity       # float64 (8 bayt)
        self.fuel = fuel               # float32 (4 bayt)
        self.status_flags = status_flags # uint16 (2 bayt)

    def step_simulation(self, dt: float, throttle: float):
        """Deterministik durum güncellemesi."""
        thrust = throttle * 25.0
        drag = 0.5 * 0.05 * (self.velocity ** 2)
        acceleration = thrust - 9.81 - drag
        
        self.velocity += acceleration * dt
        self.altitude = max(0.0, self.altitude + self.velocity * dt)
        self.fuel = max(0.0, self.fuel - (throttle * 0.5 * dt))
        
        # Durum bayrağı güncelleme
        if self.fuel <= 5.0:
            self.status_flags |= 0x04 # Düşük yakıt uyarısı biti


# =====================================================================
# MODÜL 3 & 4: Sabotaj & Taşma Kalkanı (Integer Overflow / Ariane 5)
# =====================================================================

class IntegerOverflowSabotage:
    """16-bit işaretsiz tamsayı taşması (65535 + 1 -> 0) ve Doygunluk Kalkanı."""
    MAX_UINT16 = 65535

    @staticmethod
    def unsafe_increment(val: int, delta: int) -> int:
        """Korumasız: 16-bit wraparound (Ariane 5 tipi felaket)."""
        raw = val + delta
        return raw & 0xFFFF # 16-bit maske

    @staticmethod
    def saturating_increment(val: int, delta: int) -> int:
        """Korumalı / Doygunluk Aritmetiği (Saturating Arithmetic): Tavanda sabitlenir."""
        raw = val + delta
        return min(IntegerOverflowSabotage.MAX_UINT16, raw)


# =====================================================================
# MODÜL 5 & 6: Ampirik Kıyaslama ve 4-Panelli Dashboard
# =====================================================================

def run_benchmarks_and_generate_dashboard():
    # 1. Bellek İsrafı Analizi (1.000 .. 100.000 Paket)
    packet_counts = [1000, 5000, 20000, 50000, 100000]
    ineff_kb = []
    opt_kb = []
    pack_kb = []
    
    for count in packet_counts:
        s_in, s_op, s_pk = MemoryLayoutSimulator.calculate_memory_footprint(count)
        ineff_kb.append(s_in / 1024)
        opt_kb.append(s_op / 1024)
        pack_kb.append(s_pk / 1024)

    # 2. 64-Baytlık Cache Line Başına Nesne Sığma Oranı
    # Inefficient: 64 / 12 = 5 nesne (4 bayt cache boşluğu)
    # Optimized:   64 / 8  = 8 nesne (0 bayt cache boşluğu - Mükemmel hizalama)
    # Packed:      64 / 7  = 9 nesne (1 bayt unaligned erişim cezası)
    cache_densities = [5, 8, 9]
    cache_types = ['Dağınık Struct\n(12 Bayt - %41 İsraf)', 'Optimize Struct\n(8 Bayt - Hizalı)', 'Packed Struct\n(7 Bayt - Hizalanmamış)']

    # 3. Durum Vektörü Simülasyonu (0 .. 20 Saniye)
    sim_state = FlightTelemetryState(altitude=100.0, velocity=50.0, fuel=100.0)
    time_series = []
    altitudes = []
    velocities = []
    fuels = []
    
    dt = 0.1
    for step in range(200):
        t_curr = step * dt
        sim_state.step_simulation(dt, throttle=0.8)
        time_series.append(t_curr)
        altitudes.append(sim_state.altitude)
        velocities.append(sim_state.velocity)
        fuels.append(sim_state.fuel)

    # 4. Tamsayı Taşması Sabotajı (60.000'den 70.000'e artış)
    steps_count = 100
    unsafe_vals = []
    safe_vals = []
    curr_unsafe = 60000
    curr_safe = 60000
    
    for _ in range(steps_count):
        curr_unsafe = IntegerOverflowSabotage.unsafe_increment(curr_unsafe, 100)
        curr_safe = IntegerOverflowSabotage.saturating_increment(curr_safe, 100)
        unsafe_vals.append(curr_unsafe)
        safe_vals.append(curr_safe)

    # ==================== GRAFİK ÇİZİMİ ====================
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0d1117')

    color_accent = '#58a6ff'
    color_warn = '#f85149'
    color_success = '#3fb950'
    color_gold = '#d29922'
    color_purple = '#bc8cff'

    # Panel 1: Bellek Padding İsrafı (KB)
    ax1 = axes[0, 0]
    ax1.set_facecolor('#161b22')
    ax1.plot(packet_counts, ineff_kb, marker='o', color=color_warn, linewidth=2.5, label='Dağınık Struct (12 Bayt)')
    ax1.plot(packet_counts, opt_kb, marker='s', color=color_success, linewidth=2.5, label='Optimize Struct (8 Bayt)')
    ax1.plot(packet_counts, pack_kb, marker='^', color=color_accent, linewidth=2.5, linestyle='--', label='Packed Struct (7 Bayt)')
    ax1.set_title('Panel 1: Bellek Hizalama (Padding) İsrafı: Paket Sayısı vs RAM', fontsize=12, fontweight='bold', color='white', pad=10)
    ax1.set_xlabel('Telemetri Paketi Sayısı', fontsize=10, color='#8b949e')
    ax1.set_ylabel('RAM Tüketimi (KB)', fontsize=10, color='#8b949e')
    ax1.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax1.legend(loc='upper left')

    # Panel 2: Cache Line Yoğunluğu
    ax2 = axes[0, 1]
    ax2.set_facecolor('#161b22')
    bars = ax2.bar(cache_types, cache_densities, color=[color_warn, color_success, color_gold], width=0.45, alpha=0.85)
    ax2.set_title('Panel 2: 64-Baytlık Cache Line Başına Sığan Nesne Sayısı', fontsize=12, fontweight='bold', color='white', pad=10)
    ax2.set_ylabel('Sığan Nesne Adedi (Daha Yüksek = Hızlı)', fontsize=10, color='#8b949e')
    ax2.set_ylim(0, 12)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for bar in bars:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, h + 0.3, f'{h} Nesne', ha='center', color='white', fontweight='bold')

    # Panel 3: Uçuş Durum Vektörü Zaman Çizelgesi
    ax3 = axes[1, 0]
    ax3.set_facecolor('#161b22')
    ax3.plot(time_series, altitudes, color=color_accent, linewidth=2, label='İrtifa (m)')
    ax3.plot(time_series, velocities, color=color_gold, linewidth=2, label='Hız (m/s)')
    ax3.plot(time_series, fuels, color=color_purple, linewidth=2, linestyle=':', label='Kalan Yakıt (%)')
    ax3.set_title('Panel 3: Aviyonik Durum Vektörü S(t) = (İrtifa, Hız, Yakıt) Zaman Çizgesi', fontsize=12, fontweight='bold', color='white', pad=10)
    ax3.set_xlabel('Uçuş Zamanı (s)', fontsize=10, color='#8b949e')
    ax3.set_ylabel('Fiziksel Değerler', fontsize=10, color='#8b949e')
    ax3.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax3.legend(loc='upper left')

    # Panel 4: Tamsayı Taşması ve Doygunluk Kalkanı
    ax4 = axes[1, 1]
    ax4.set_facecolor('#161b22')
    ax4.plot(range(steps_count), unsafe_vals, color=color_warn, linewidth=2.5, label='Korumasız Wraparound (Ariane-5 Tipi Çöküş)')
    ax4.plot(range(steps_count), safe_vals, color=color_success, linewidth=2.5, linestyle='--', label='Doygunluk Kalkanı (Saturating Arithmetic)')
    ax4.axhline(y=65535, color=color_gold, linestyle=':', linewidth=1.5, label='16-bit UINT Tavan Sınırı (65535)')
    ax4.set_title('Panel 4: Sabotaj Testi: uint16 Tamsayı Taşması ve Doygunluk Kalkanı', fontsize=12, fontweight='bold', color='white', pad=10)
    ax4.set_xlabel('Döngü Adımı', fontsize=10, color='#8b949e')
    ax4.set_ylabel('Değişken Değeri', fontsize=10, color='#8b949e')
    ax4.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax4.legend(loc='center left')

    plt.tight_layout()
    output_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_010_degisken_durum_ve_veri_kavrami.png")
    plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 010 Dashboard başarıyla üretildi: {output_png}")


# =====================================================================
# DOĞRULAMA VE ASSERT TESTLERİ
# =====================================================================

def verify_all():
    print("--- GÜN 010 SİSTEM VE MİMARİ DOĞRULAMA TESTLERİ BAŞLIYOR ---")
    
    # Test 1: Struct Layout ve Padding Doğrulama
    s_in, s_op, s_pk = MemoryLayoutSimulator.calculate_memory_footprint(1)
    assert s_in == 12 # 1 + 3(pad) + 4 + 2 + 2(pad) = 12
    assert s_op == 8  # 4 + 2 + 1 + 1(pad) = 8
    assert s_pk == 7  # 1 + 4 + 2 = 7 (Packed)
    print(f"[PASS] Test 1: Bellek hizalama (Padding) boyutları doğrulandı (12B vs 8B vs 7B).")

    # Test 2: Durum Vektörü Simülasyonu
    state = FlightTelemetryState(altitude=0.0, velocity=10.0, fuel=100.0)
    state.step_simulation(dt=1.0, throttle=1.0)
    assert state.altitude > 0.0
    assert state.fuel < 100.0
    print("[PASS] Test 2: Aviyonik Durum Vektörü deterministik güncellemesi doğrulandı.")

    # Test 3: Tamsayı Taşması ve Doygunluk Kalkanı
    val_wrapped = IntegerOverflowSabotage.unsafe_increment(65535, 1)
    val_saturated = IntegerOverflowSabotage.saturating_increment(65535, 1)
    assert val_wrapped == 0     # 65535 + 1 = 0 (Tehlikeli wraparound!)
    assert val_saturated == 65535 # Tavanda sabitlendi (Güvenli!)
    print("[PASS] Test 3: Tamsayı taşması (Ariane 5 felaketi) ve Doygunluk Kalkanı doğrulandı.")

    # Test 4: Dashboard Üretimi
    run_benchmarks_and_generate_dashboard()
    print("[PASS] Test 4: 4-Panelli 300 DPI Dashboard üretildi.")
    print("[PASS] Gün 010: Tüm değişken, durum, bellek hizalama ve veri kuralları doğrulandı.")


if __name__ == "__main__":
    verify_all()
