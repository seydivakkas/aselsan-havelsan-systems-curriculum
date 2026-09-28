#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

GÜN 014: Array/List ve Ardışık Veri Mimarisi
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
# MODÜL 1: Bitişik Dizi (Contiguous Array) ve Pointer Aritmetiği Motoru
# =====================================================================

class ContiguousArraySimulator:
    """Donanımsal RAM yerleşimi, önbellek satırları ve pointer aritmetiği modeli."""
    def __init__(self, base_address: int, element_count: int, element_size: int = 4):
        self.base_address = base_address
        self.element_count = element_count
        self.element_size = element_size # 4 bayt = int32_t
        self.memory = [0] * element_count
        self.cache_line_size = 64 # 64 Bayt L1 Cache Line

    def get_address_of_index(self, index: int) -> int:
        """Pointer Aritmetiği: Address = Base + Index * Sizeof(T) (LEA komutu)."""
        if index < 0 or index >= self.element_count:
            raise IndexError(f"BUFFER_OVERRUN: Dizi sınırları aşıldı! İndeks: {index}, Boyut: {self.element_count}")
        return self.base_address + (index * self.element_size)

    def calculate_cache_lines_needed(self) -> int:
        """Dizinin toplam kapladığı 64-baytlık L1 önbellek satırı sayısı."""
        total_bytes = self.element_count * self.element_size
        return (total_bytes + self.cache_line_size - 1) // self.cache_line_size


# =====================================================================
# MODÜL 2: Dinamik Dizi (std::vector) Büyüme ve Kopyalama Simülatörü
# =====================================================================

class DynamicVectorSimulator:
    """Geometrik (1.5x, 2.0x) vs Lineer (+1) büyüme stratejisi analizi."""
    def __init__(self, growth_factor: float = 2.0, initial_capacity: int = 1):
        self.growth_factor = growth_factor
        self.capacity = initial_capacity
        self.size = 0
        self.reallocation_count = 0
        self.total_elements_copied = 0

    def push_back(self, value: int):
        if self.size >= self.capacity:
            # Yeniden tahsis (Reallocation) ve taşıma (Move/Copy)
            new_capacity = int(self.capacity * self.growth_factor) if self.growth_factor > 1.0 else self.capacity + 1
            if new_capacity <= self.capacity:
                new_capacity = self.capacity + 1
            self.total_elements_copied += self.size
            self.capacity = new_capacity
            self.reallocation_count += 1
        self.size += 1


# =====================================================================
# MODÜL 3: Deterministik Aviyonik Dairesel Tampon (Ring Buffer)
# =====================================================================

class CircularRingBuffer:
    """Sıfır çalışma zamanı tahsisli, sabit boyutlu ardışık aviyonik kuyruk."""
    def __init__(self, capacity: int = 256):
        self.capacity = capacity
        self.buffer = [0] * capacity
        self.head = 0
        self.tail = 0
        self.count = 0

    def push(self, data: int) -> bool:
        if self.count >= self.capacity:
            return False # Geri basınç: Tampon dolu!
        self.buffer[self.head] = data
        self.head = (self.head + 1) % self.capacity
        self.count += 1
        return True

    def pop(self) -> Optional[int]:
        if self.count == 0:
            return None # Tampon boş
        val = self.buffer[self.tail]
        self.tail = (self.tail + 1) % self.capacity
        self.count -= 1
        return val


# =====================================================================
# MODÜL 4: Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering)
# =====================================================================

class ArraySabotage:
    @staticmethod
    def simulate_buffer_overflow(arr_sim: ContiguousArraySimulator, target_index: int) -> Tuple[bool, str]:
        """Sınır kontrolsüz bellek okuma/yazma sabotajı."""
        try:
            addr = arr_sim.get_address_of_index(target_index)
            return True, f"KORUMASIZ ERİŞİM: Adres hesaplandı {hex(addr)} (Bellek Sızıntısı/Bozulması!)"
        except IndexError as e:
            return False, f"ENGELENDİ: {str(e)}"

    @staticmethod
    def simulate_linear_growth_catastrophe(n_elements: int) -> Tuple[int, int]:
        """Lineer (+1) büyüme sabotajı: O(N^2) kopyalama felaketi."""
        vec = DynamicVectorSimulator(growth_factor=1.0)
        for i in range(n_elements):
            vec.push_back(i)
        return vec.reallocation_count, vec.total_elements_copied


# =====================================================================
# MODÜL 5 & 6: Ampirik Kıyaslama ve 4-Panelli Dashboard
# =====================================================================

def run_benchmarks_and_generate_dashboard():
    # 1. Contiguous Array vs Linked List (Pointer Chasing) Benchmark
    n_items = 100000
    contiguous_data = list(range(n_items))
    
    # Linked List simülasyonu: Belleğin rastgele yerlerine dağıtılmış düğümler (Pointer Chasing)
    random_indices = list(range(n_items))
    random.seed(42)
    random.shuffle(random_indices)
    
    # Sıralı ardışık erişim (L1/L2 Hardware Prefetcher dostu)
    t0 = time.perf_counter_ns()
    s1 = 0
    for val in contiguous_data:
        s1 += val
    t1 = time.perf_counter_ns()
    time_contiguous_ns = (t1 - t0) / n_items

    # Dağınık işaretçi takibi (Cache Miss cezası)
    t0 = time.perf_counter_ns()
    s2 = 0
    for idx in random_indices:
        s2 += contiguous_data[idx]
    t1 = time.perf_counter_ns()
    time_pointer_chasing_ns = (t1 - t0) / n_items

    # 2. Vektör Büyüme Stratejileri Kıyaslaması (N = 5.000 eleman)
    n_vec = 5000
    vec_2x = DynamicVectorSimulator(growth_factor=2.0)
    vec_15x = DynamicVectorSimulator(growth_factor=1.5)
    vec_linear = DynamicVectorSimulator(growth_factor=1.0)

    copies_2x, copies_15x, copies_linear = [], [], []
    steps = list(range(100, n_vec + 1, 100))

    for s in steps:
        v2 = DynamicVectorSimulator(2.0)
        v15 = DynamicVectorSimulator(1.5)
        vlin = DynamicVectorSimulator(1.0)
        for i in range(s):
            v2.push_back(i)
            v15.push_back(i)
            vlin.push_back(i)
        copies_2x.append(v2.total_elements_copied)
        copies_15x.append(v15.total_elements_copied)
        copies_linear.append(vlin.total_elements_copied)

    # 3. Capacity Reserve vs Dynamic Push Benchmark
    n_reserve_test = 200000
    t0 = time.perf_counter_ns()
    v_dyn = []
    for i in range(n_reserve_test):
        v_dyn.append(i)
    t1 = time.perf_counter_ns()
    time_dynamic_ms = (t1 - t0) / 1e6

    t0 = time.perf_counter_ns()
    v_res = [0] * n_reserve_test # std::vector::reserve benzeri ön tahsis
    for i in range(n_reserve_test):
        v_res[i] = i
    t1 = time.perf_counter_ns()
    time_reserve_ms = (t1 - t0) / 1e6

    # ==================== GRAFİK ÇİZİMİ (300 DPI Dark Tema) ====================
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0d1117')

    color_accent = '#58a6ff'
    color_warn = '#f85149'
    color_success = '#3fb950'
    color_gold = '#d29922'
    color_purple = '#bc8cff'

    # Panel 1: Contiguous Array vs Pointer Chasing (Cache Latency)
    ax1 = axes[0, 0]
    ax1.set_facecolor('#161b22')
    labels1 = ['Ardışık Dizi Erişimi\n(L1 Cache Prefetcher)', 'Dağınık Pointer Chasing\n(Linked List / Cache Miss)']
    latencies = [time_contiguous_ns, time_pointer_chasing_ns]
    bars1 = ax1.bar(labels1, latencies, color=[color_success, color_warn], width=0.45, alpha=0.85)
    ax1.set_title('Panel 1: Bitişik Dizi vs Dağınık Liste Bellek Erişim Gecikmesi', fontsize=12, fontweight='bold', color='white', pad=10)
    ax1.set_ylabel('Eleman Başına Süre (ns - Düşük = Hızlı)', fontsize=10, color='#8b949e')
    ax1.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars1:
        h = b.get_height()
        ax1.text(b.get_x() + b.get_width()/2.0, h + 0.5, f'{h:.1f} ns', ha='center', color='white', fontweight='bold')

    # Panel 2: Vector Büyüme Kopyalama Maliyetleri
    ax2 = axes[0, 1]
    ax2.set_facecolor('#161b22')
    ax2.plot(steps, copies_linear, color=color_warn, linewidth=2.5, label='Lineer (+1 Büyüme - O(N^2) Felaket)')
    ax2.plot(steps, copies_15x, color=color_gold, linewidth=2.5, label='1.5x Geometrik Büyüme (MSVC Stratejisi)')
    ax2.plot(steps, copies_2x, color=color_success, linewidth=2.5, label='2.0x Geometrik Büyüme (GCC Stratejisi)')
    ax2.set_title('Panel 2: Dinamik Dizi Büyüme Stratejileri Kümülatif Kopyalama', fontsize=12, fontweight='bold', color='white', pad=10)
    ax2.set_xlabel('Eklenen Eleman Sayısı (N)', fontsize=10, color='#8b949e')
    ax2.set_ylabel('Toplam Kopyalanan Eleman Sayısı', fontsize=10, color='#8b949e')
    ax2.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax2.legend(loc='upper left')

    # Panel 3: Kapasite Rezervasyonu Etkisi (Reserve vs Dinamik)
    ax3 = axes[1, 0]
    ax3.set_facecolor('#161b22')
    labels3 = ['Dinamik Büyüyen Vektör\n(Yeniden Tahsisler + Kopyalama)', 'Önceden Rezerv Edilmiş (Reserve)\n(Sıfır Yeniden Tahsis)']
    times3 = [time_dynamic_ms, time_reserve_ms]
    bars3 = ax3.bar(labels3, times3, color=[color_gold, color_accent], width=0.45, alpha=0.85)
    ax3.set_title('Panel 3: std::vector::reserve Ön-Tahsis Performans Kazanımı', fontsize=12, fontweight='bold', color='white', pad=10)
    ax3.set_ylabel('Toplam İcra Süresi (ms - Düşük = İyi)', fontsize=10, color='#8b949e')
    ax3.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars3:
        h = b.get_height()
        ax3.text(b.get_x() + b.get_width()/2.0, h + 0.5, f'{h:.2f} ms', ha='center', color='white', fontweight='bold')

    # Panel 4: Sabotaj Testi: Sınır Kontrolü ve Güvenlik
    ax4 = axes[1, 1]
    ax4.set_facecolor('#161b22')
    sabotage_labels = ['Korumasız Operatör[]\n(Out-of-Bounds Bellek Sızıntısı)', 'Sınır Korumalı at() / Span\n(Out-of-Bounds Engelleme)']
    defense_rates = [0, 100]
    ax4.bar(sabotage_labels, defense_rates, color=[color_warn, color_success], width=0.45, alpha=0.85)
    ax4.set_title('Panel 4: Sabotaj Testi: Dizi Sınır İhlali (OOB) ve Savunma Kalkanı', fontsize=12, fontweight='bold', color='white', pad=10)
    ax4.set_ylabel('Sistemin Taşmayı Engelleme Başarısı (%)', fontsize=10, color='#8b949e')
    ax4.set_ylim(0, 115)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#30363d')

    plt.tight_layout()
    output_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_014_array_list_ardisik_veri.png")
    plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 014 Dashboard başarıyla üretildi: {output_png}")


# =====================================================================
# DOĞRULAMA VE ASSERT TESTLERİ
# =====================================================================

def verify_all():
    print("--- GÜN 014 SİSTEM VE MİMARİ DOĞRULAMA TESTLERİ BAŞLIYOR ---")
    
    # Test 1: Pointer Aritmetiği ve LEA Adres Doğrulaması
    arr_sim = ContiguousArraySimulator(base_address=0x1000, element_count=100, element_size=4)
    assert arr_sim.get_address_of_index(0) == 0x1000
    assert arr_sim.get_address_of_index(5) == 0x1000 + (5 * 4)
    assert arr_sim.calculate_cache_lines_needed() == (400 + 63) // 64
    print("[PASS] Test 1: Pointer aritmetiği ve 64-bayt Cache Line hesabı doğrulandı.")

    # Test 2: Dynamic Vector Geometrik Büyüme Doğrulaması
    vec = DynamicVectorSimulator(growth_factor=2.0, initial_capacity=2)
    for i in range(10):
        vec.push_back(i)
    assert vec.size == 10
    assert vec.capacity >= 10
    assert vec.reallocation_count > 0
    print(f"[PASS] Test 2: std::vector 2.0x geometrik büyüme ve yeniden tahsisler doğrulandı (Kapasite: {vec.capacity}).")

    # Test 3: Circular Ring Buffer Aviyonik Determinizm Doğrulaması
    rb = CircularRingBuffer(capacity=4)
    assert rb.push(10) is True
    assert rb.push(20) is True
    assert rb.push(30) is True
    assert rb.push(40) is True
    assert rb.push(50) is False # Geri basınç: Dolu
    assert rb.pop() == 10
    assert rb.push(50) is True # Şimdi yer açıldı
    print("[PASS] Test 3: Deterministik Dairesel Tampon (Ring Buffer) geri basıncı doğrulandı.")

    # Test 4: Sabotaj Testleri (Out-of-Bounds & Lineer Felaket)
    allowed, msg = ArraySabotage.simulate_buffer_overflow(arr_sim, target_index=150)
    assert allowed is False
    assert "BUFFER_OVERRUN" in msg
    reallocs, copies = ArraySabotage.simulate_linear_growth_catastrophe(100)
    assert reallocs == 99
    assert copies == (99 * 100) // 2 # Toplam N*(N-1)/2 kopyalama (O(N^2))
    print(f"[PASS] Test 4: Out-of-bounds sınır ihlali ve O(N^2) lineer kopyalama sabotajı doğrulandı.")

    # Test 5: Dashboard Üretimi
    run_benchmarks_and_generate_dashboard()
    print("[PASS] Test 5: 4-Panelli 300 DPI Dashboard üretildi.")
    print("[PASS] Gün 014: Tüm bitişik dizi, önbellek dostu veri, pointer aritmetiği ve büyüme kuralları doğrulandı.")


if __name__ == "__main__":
    verify_all()
