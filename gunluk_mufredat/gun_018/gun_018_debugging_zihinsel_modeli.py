#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

GÜN 018: Debugging Zihinsel Modeli
Çalıştırılabilir Simülasyon, Sabotaj, Benchmark & 4-Panelli Doğrulama Dashboard'u
"""

import os
import sys
import time
import math
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
# MODÜL 1: Bilimsel Hata Ayıklama (Scientific Debugging) Durum Makinesi
# =====================================================================

class ScientificDebugState:
    OBSERVE = "1. GÖZLEM (Semptom Tespiti)"
    HYPOTHESIS = "2. HİPOTEZ (Kök Neden Varsayımı)"
    EXPERIMENT = "3. DENEY (Minimal Reproducer - MRE)"
    VERIFY = "4. KANITLAMA (Breakpoint / Watchpoint)"
    FIX_REGRESSION = "5. ÇÖZÜM & REGRESYON TESTİ"


class ScientificDebugger:
    """Bilimsel hata ayıklama döngüsü yöneticisi."""
    def __init__(self):
        self.history: List[str] = []

    def transition(self, state: str, detail: str):
        log_entry = f"[{state}] -> {detail}"
        self.history.append(log_entry)
        return log_entry

    @staticmethod
    def binary_search_fault_isolation(code_lines: int, bug_line: int) -> int:
        """Git Bisect mantığıyla hatayı ikili arama ile izole etme (O(log N))."""
        low = 1
        high = code_lines
        steps = 0
        while low <= high:
            steps += 1
            mid = (low + high) // 2
            if mid == bug_line:
                return steps
            elif mid < bug_line:
                low = mid + 1
            else:
                high = mid - 1
        return steps


# =====================================================================
# MODÜL 2: Donanımsal Breakpoint ve Watchpoint Simülatörü (DR0-DR7)
# =====================================================================

class HardwareDebugRegisters:
    """x86_64 mimarisindeki donanımsal hata ayıklama yazmaçları (DR0-DR7) modeli."""
    def __init__(self):
        # 4 Adet Donanımsal Adres Yazmacı (DR0, DR1, DR2, DR3)
        self.dr_address: List[Optional[int]] = [None, None, None, None]
        # DR7: Kontrol Yazmacı (Bitler: Hangi adres, Hangi koşulda tetiklenecek: 0=İcra, 1=Yazma, 3=Okuma/Yazma)
        self.dr7_conditions: List[str] = ["EXEC", "EXEC", "EXEC", "EXEC"]
        self.trapped: bool = False
        self.trapped_address: Optional[int] = None

    def set_hardware_watchpoint(self, register_idx: int, address: int, condition: str = "WRITE"):
        assert 0 <= register_idx <= 3, "DR0-DR3 arası sadece 4 donanımsal gözetleme noktası desteklenir!"
        self.dr_address[register_idx] = address
        self.dr7_conditions[register_idx] = condition

    def on_memory_write(self, target_address: int, value: any) -> bool:
        """Belleğe yazma yapıldığında CPU donanımının adresi kontrol etmesi."""
        for idx in range(4):
            if self.dr_address[idx] == target_address and self.dr7_conditions[idx] in ["WRITE", "RW"]:
                self.trapped = True
                self.trapped_address = target_address
                return True # Donanımsal Kesme (#DB Trap) tetiklendi!
        return False


# =====================================================================
# MODÜL 3: Post-Mortem Core Dump ve Stack Trace Çözümleyici
# =====================================================================

class CoreDumpUnwinder:
    """Çöküş anındaki yığın çerçevelerini (Stack Frames) geriye doğru çözen motor."""
    @staticmethod
    def unwind_stack(raw_frames: List[Dict[str, any]]) -> List[str]:
        trace = []
        for i, f in enumerate(reversed(raw_frames)):
            func = f.get("func", "unknown")
            file_name = f.get("file", "unknown.cpp")
            line = f.get("line", 0)
            trace.append(f"#{i}  0x{f.get('rip', 0):08x} in {func}() at {file_name}:{line}")
        return trace


# =====================================================================
# MODÜL 4: Sabotaj Senaryoları (Heisenbug ve Bellek Bozulması)
# =====================================================================

class DebugSabotage:
    @staticmethod
    def simulate_heisenbug_probe_effect(add_printf: bool) -> Tuple[bool, float, str]:
        """Heisenbug: 'printf' eklendiğinde zamanlama değişir ve yarış durumu hatası kaybolur!"""
        # Eşzamanlı iki iş parçacığı zamanlama aralığı
        critical_window_ns = 500 # 500 ns içinde çakışma riski
        
        t0 = time.perf_counter_ns()
        if add_printf:
            # Gözlemci Etkisi (Probe Effect): Printf konsola yazarken 10.000 ns gecikme yaratır!
            dummy = f"DEBUG: Degisken durumu kontrol ediliyor... {time.time()}"
            delay_ns = 15000
        else:
            delay_ns = 200 # Normal saf kod
            
        t1 = time.perf_counter_ns()
        
        # Eğer gecikme kritik pencereyi aşarsa yarış durumu maskelenir
        if delay_ns > critical_window_ns:
            # Hata ortadan kayboldu! (Heisenbug)
            return False, delay_ns, "HEISENBUG: Printf eklendiği için zamanlama bozuldu, hata GİZLENDİ!"
        else:
            # Hata tetiklendi! (Crash)
            return True, delay_ns, "GERÇEK ÇÖKÜŞ: Yarış durumu yakalandı!"

    @staticmethod
    def simulate_wild_pointer_overwrite(hw_debug: HardwareDebugRegisters, target_addr: int) -> Tuple[bool, str]:
        """Vahşi işaretçi (Wild Pointer) ile belleği sessizce ezme sabotajı."""
        trap_fired = hw_debug.on_memory_write(target_addr, 0xDEADBEEF)
        if trap_fired:
            return True, f"DONANIMSAL YAKALAMA (#DB): Adres {hex(target_addr)} üzerine yazıldığı anda CPU durduruldu!"
        return False, f"SESSİZ BOZULMA: Adres {hex(target_addr)} ezildi ama yakalanamadı!"


# =====================================================================
# MODÜL 5 & 6: Ampirik Kıyaslama ve 4-Panelli Dashboard
# =====================================================================

def run_benchmarks_and_generate_dashboard():
    # 1. Hata Arama Yöntemleri: Rastgele (Linear) vs Bilimsel İkili Arama (Git Bisect)
    n_commits = [10, 50, 100, 500, 1000, 5000, 10000]
    steps_linear = [c / 2 for c in n_commits] # Ortalama arama adımı N/2
    steps_bisect = [math.ceil(math.log2(c)) for c in n_commits] # log2(N)

    # 2. Breakpoint Türleri: Software (INT 3) vs Hardware (DR0-DR7)
    # Software breakpoint kod sayfasına yazma (Copy-on-Write) gerektirir; Hardware breakpoint 0 bayt modifikasyon yapar.
    bp_types = ['Yazılımsal (INT 3 / 0xCC)\n(I-Cache Flush + CoW)', 'Donanımsal (DR0-DR7)\n(Sıfır Bellek Değişimi)']
    bp_intrusiveness = [85, 5] # Göreli intruzyon ve gecikme skoru

    # 3. Heisenbug Gecikme Ölçümü
    _, d_pure, _ = DebugSabotage.simulate_heisenbug_probe_effect(add_printf=False)
    _, d_print, _ = DebugSabotage.simulate_heisenbug_probe_effect(add_printf=True)

    # 4. Hardware Watchpoint Yakalama Başarısı
    hw_sim = HardwareDebugRegisters()
    hw_sim.set_hardware_watchpoint(0, 0x00405000, "WRITE")
    caught_hw, _ = DebugSabotage.simulate_wild_pointer_overwrite(hw_sim, 0x00405000)

    # ==================== GRAFİK ÇİZİMİ (300 DPI Dark Tema) ====================
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0d1117')

    color_accent = '#58a6ff'
    color_warn = '#f85149'
    color_success = '#3fb950'
    color_gold = '#d29922'
    color_purple = '#bc8cff'

    # Panel 1: Rastgele Arama vs Bilimsel İkili Arama (Git Bisect)
    ax1 = axes[0, 0]
    ax1.set_facecolor('#161b22')
    ax1.plot(n_commits, steps_linear, color=color_warn, linewidth=2.5, label='Rastgele/Lineer Arama O(N)')
    ax1.plot(n_commits, steps_bisect, color=color_success, linewidth=2.5, marker='o', label='Bilimsel İkili Arama (Git Bisect) O(log N)')
    ax1.set_title('Panel 1: Hata İzolasyon Hızı: Lineer vs Bilimsel İkili Arama', fontsize=12, fontweight='bold', color='white', pad=10)
    ax1.set_xlabel('Kod Satırı / Commit Sayısı (N)', fontsize=10, color='#8b949e')
    ax1.set_ylabel('Gereken Test Adımı Sayısı', fontsize=10, color='#8b949e')
    ax1.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax1.legend(loc='upper left')

    # Panel 2: Breakpoint İntruzyon Karşılaştırması
    ax2 = axes[0, 1]
    ax2.set_facecolor('#161b22')
    bars2 = ax2.bar(bp_types, bp_intrusiveness, color=[color_warn, color_accent], width=0.45, alpha=0.85)
    ax2.set_title('Panel 2: Breakpoint Türleri: Kod Değiştirme ve Gecikme Skoru', fontsize=12, fontweight='bold', color='white', pad=10)
    ax2.set_ylabel('Sisteme Müdahale (İntruzyon) Seviyesi', fontsize=10, color='#8b949e')
    ax2.set_ylim(0, 100)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars2:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2.0, h + 2, f'{h} Puan', ha='center', color='white', fontweight='bold')

    # Panel 3: Heisenbug ve Gözlemci Etkisi (Probe Effect)
    ax3 = axes[1, 0]
    ax3.set_facecolor('#161b22')
    hb_labels = ['Saf Üretim Kodu\n(Yarış Durumu Aktif)', 'Printf Eklenmiş Kod\n(Zamanlama Bozuldu / Hata Gizlendi)']
    delays = [d_pure / 1000.0, d_print / 1000.0]
    bars3 = ax3.bar(hb_labels, delays, color=[color_warn, color_gold], width=0.45, alpha=0.85)
    ax3.axhline(y=0.5, color=color_purple, linestyle='--', linewidth=2, label='Kritik Eşzamanlılık Penceresi (0.5 µs)')
    ax3.set_title('Panel 3: Heisenbug: Printf Eklenince Zamanlama Sapması', fontsize=12, fontweight='bold', color='white', pad=10)
    ax3.set_ylabel('Gecikme Süresi (µs - Logik Değişimi)', fontsize=10, color='#8b949e')
    ax3.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax3.legend(loc='upper left')

    # Panel 4: Sabotaj Testi: Bellek Ezilmesini Yakalama
    ax4 = axes[1, 1]
    ax4.set_facecolor('#161b22')
    sab_labels = ['Klasik Loglama (Printf)\n(Ezilme Sonrası Çöküş)', 'Hardware Watchpoint (DR0-DR7)\n(Ezilme Anında Donanımsal Trap)']
    success_rates = [0, 100]
    ax4.bar(sab_labels, success_rates, color=[color_warn, color_success], width=0.45, alpha=0.85)
    ax4.set_title('Panel 4: Sabotaj Testi: Bellek Bozulmasını Kaynağında Yakalama', fontsize=12, fontweight='bold', color='white', pad=10)
    ax4.set_ylabel('Hatanın Kök Nedenini Yakalama Başarısı (%)', fontsize=10, color='#8b949e')
    ax4.set_ylim(0, 115)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#30363d')

    plt.tight_layout()
    output_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_018_debugging_zihinsel_modeli.png")
    plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 018 Dashboard başarıyla üretildi: {output_png}")


# =====================================================================
# DOĞRULAMA VE ASSERT TESTLERİ
# =====================================================================

def verify_all():
    print("--- GÜN 018 SİSTEM VE MİMARİ DOĞRULAMA TESTLERİ BAŞLIYOR ---")
    
    # Test 1: Bilimsel Hata Ayıklama İkili Arama Doğrulaması
    steps_1000 = ScientificDebugger.binary_search_fault_isolation(code_lines=1000, bug_line=450)
    assert steps_1000 <= 10 # log2(1000) ~ 10 adımda izole edilmelidir
    print(f"[PASS] Test 1: Git Bisect ikili arama mantığı {steps_1000} adımda hatayı izole etti.")

    # Test 2: Hardware Debug Register (DR0-DR7) Doğrulaması
    hw = HardwareDebugRegisters()
    hw.set_hardware_watchpoint(0, 0x00501000, "WRITE")
    assert hw.on_memory_write(0x00501000, 123) is True # Tetiklendi
    assert hw.trapped is True
    assert hw.on_memory_write(0x00502000, 456) is False # Farklı adres, tetiklenmedi
    print("[PASS] Test 2: Donanımsal Watchpoint (#DB Trap) bellek yazma denetimi doğrulandı.")

    # Test 3: Core Dump Unwinder Doğrulaması
    raw_stack = [
        {"func": "main", "file": "main.cpp", "line": 42, "rip": 0x401000},
        {"func": "radar_filter", "file": "radar.cpp", "line": 128, "rip": 0x402500},
        {"func": "fft_core", "file": "fft.cpp", "line": 88, "rip": 0x403100}
    ]
    unwound = CoreDumpUnwinder.unwind_stack(raw_stack)
    assert len(unwound) == 3
    assert "fft_core" in unwound[0] # En üstteki çöküş çerçevesi en başta olmalı (#0)
    print("[PASS] Test 3: Post-Mortem Core Dump yığın çözümü (Stack Unwinding) doğrulandı.")

    # Test 4: Sabotaj Testleri (Heisenbug ve Wild Pointer)
    crashed_pure, _, _ = DebugSabotage.simulate_heisenbug_probe_effect(add_printf=False)
    assert crashed_pure is True
    crashed_print, _, msg_hb = DebugSabotage.simulate_heisenbug_probe_effect(add_printf=True)
    assert crashed_print is False # Printf hatayı gizledi!
    assert "HEISENBUG" in msg_hb
    print("[PASS] Test 4: Heisenbug gözlemci etkisi (Probe Effect) sabotajı doğrulandı.")

    # Test 5: Dashboard Üretimi
    run_benchmarks_and_generate_dashboard()
    print("[PASS] Test 5: 4-Panelli 300 DPI Dashboard üretildi.")
    print("[PASS] Gün 018: Tüm Debugging Zihinsel Modeli, DR0-DR7, Core Dump ve Heisenbug kuralları doğrulandı.")


if __name__ == "__main__":
    verify_all()
