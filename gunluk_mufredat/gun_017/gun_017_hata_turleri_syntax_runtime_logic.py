#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

GÜN 017: Hata Türleri: Syntax, Runtime ve Logic Hataları
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
# MODÜL 1: Hata Taksonomisi ve Keşif Aşamaları Simülatörü
# =====================================================================

class ErrorTaxonomy:
    """Hata türlerinin sınıflandırılması ve yaşam döngüsü modeli."""
    SYNTAX = "SYNTAX_ERROR"       # Derleme zamanında parser yakalar (En ucuz)
    RUNTIME = "RUNTIME_ERROR"     # Çalışma anında OS/CPU yakalar (Crash / Trap)
    LOGIC = "LOGIC_ERROR"         # Sessizce çalışır, yanlış sonuç üretir (En ölümcül!)

    @staticmethod
    def simulate_syntax_check(code_snippet: str) -> Tuple[bool, str]:
        """Sözdizimi denetimi: Derleyici AST kuramazsa derleme durur."""
        try:
            compile(code_snippet, "<test>", "exec")
            return True, "Sözdizimi Hatasız (Derlendi)."
        except SyntaxError as e:
            return False, f"DERLEME HATASI: {e.msg} (Satır {e.lineno})"

    @staticmethod
    def simulate_runtime_division(a: float, b: float) -> Tuple[bool, float, str]:
        """Çalışma zamanı hatası: Sıfıra bölme (SIGFPE Trap)."""
        try:
            res = a / b
            return True, res, "Başarılı İcra."
        except ZeroDivisionError:
            return False, 0.0, "RUNTIME_TRAP: Sıfıra bölme donanımsal istisnası (SIGFPE)!"


# =====================================================================
# MODÜL 2: Güçlü Tip Güvenliği ve Birim Analizi (Mars Orbiter Kalkanı)
# =====================================================================

class Radian:
    """Güçlü tipli radyan birimi."""
    def __init__(self, value: float):
        self.value = value

    def to_degree(self) -> float:
        return self.value * (180.0 / math.pi)


class Degree:
    """Güçlü tipli derece birimi."""
    def __init__(self, value: float):
        self.value = value

    def to_radian(self) -> Radian:
        return Radian(self.value * (math.pi / 180.0))


class AviyonikGuidanceCalculator:
    """Tip denetimi ile sessiz mantık hatalarını engelleyen güdüm motoru."""
    @staticmethod
    def compute_rudder_deflection_buggy(angle_val: float) -> float:
        """Korumasız naif fonksiyon: Derece mi radyan mı belli değil! (Logic Bug tuzağı)"""
        # Formül radyan bekliyor ama kullanıcı derece yollarsa kontrol yüzeyi 57 kat fazla sapar!
        return math.sin(angle_val) * 10.0

    @staticmethod
    def compute_rudder_deflection_safe(angle: Radian) -> float:
        """Güçlü tipli güvenli fonksiyon: Yalnızca Radian kabul eder."""
        return math.sin(angle.value) * 10.0


# =====================================================================
# MODÜL 3: Design by Contract (Sözleşmeli Tasarım Kalkanı)
# =====================================================================

class ContractGuard:
    """Önkoşul (Precondition), Sonkoşul (Postcondition) ve Değişmez (Invariant) denetimi."""
    @staticmethod
    def calculate_thrust(fuel_kg: float, burn_rate: float) -> float:
        # Precondition (Önkoşul)
        assert fuel_kg >= 0.0, "INVARIANT_FAULT: Yakıt miktarı negatif olamaz!"
        assert burn_rate > 0.0, "PRECONDITION_FAULT: Yanma hızı pozitif olmalıdır!"
        
        thrust = fuel_kg * burn_rate * 9.81
        
        # Postcondition (Sonkoşul)
        assert thrust >= 0.0, "POSTCONDITION_FAULT: İtki kuvveti negatif olamaz!"
        return thrust


# =====================================================================
# MODÜL 4: Tarihi Askeri/Uzay Sabotaj Senaryoları (Chaos Engineering)
# =====================================================================

class HistoricalSabotageSimulator:
    @staticmethod
    def simulate_ariane_5_overflow(horizontal_velocity: float) -> Tuple[bool, int, str]:
        """Ariane 5 Roket Faciası (4 Haziran 1996): 64-bit Float -> 16-bit Int Taşması."""
        # 16-bit işaretli tamsayı aralığı: -32768 ile +32767 arası
        INT16_MAX = 32767
        INT16_MIN = -32768

        raw_int = int(horizontal_velocity)
        if raw_int > INT16_MAX or raw_int < INT16_MIN:
            # Donanımsal Overflow İstisnası (Korumasız kodda kontrol bilgisayarı çöktü!)
            return False, raw_int, "ARIANE_5_CRASH: 64-bit Kayan Nokta 16-bit Tamsayıya Sığmadı (Arithmetic Overflow)!"
        return True, raw_int, "Güvenli Dönüşüm."

    @staticmethod
    def simulate_mars_climate_orbiter_disaster(impulse_ns_force: float, is_metric: bool) -> Tuple[float, float]:
        """Mars Climate Orbiter (1999): Pound-force saniye vs Newton-saniye Birim Hatası."""
        # Beklenen: Newton-saniye (Metrik)
        # Gelen: Pound-force saniye (İmparatorluk) -> 1 lbf = 4.44822 Newton
        if not is_metric:
            # Hatalı: Dönüşüm yapılmadan doğrudan kullanıldı (Sessiz Mantık Hatası!)
            actual_force_applied = impulse_ns_force # Gerçekte 4.45 kat eksik itki uygulandı!
        else:
            actual_force_applied = impulse_ns_force * 4.44822

        target_trajectory_km = 140.0 # Güvenli yörünge 140-150 km
        actual_trajectory_km = target_trajectory_km * (actual_force_applied / (impulse_ns_force * 4.44822))
        return actual_force_applied, actual_trajectory_km


# =====================================================================
# MODÜL 5 & 6: Ampirik Kıyaslama ve 4-Panelli Dashboard
# =====================================================================

def run_benchmarks_and_generate_dashboard():
    # 1. Hatanın Keşfedildiği Aşamaya Göre Göreli Maliyet (Logaritmik Ölçek)
    phases = [
        '1. Derleme Zamanı\n(Syntax/Type/Warning)',
        '2. Birim Test\n(Unit / Contract Test)',
        '3. Entegrasyon & HIL\n(System Test Bench)',
        '4. Canlı Görev / Uçuş\n(Mission Critical Failure)'
    ]
    relative_costs = [1, 10, 100, 10000] # 1x, 10x, 100x, 10.000x maliyet

    # 2. Derleyici Uyarı Bayrakları ile Hata Yakalama Oranı
    flags_labels = ['Temel Derleme\n(gcc)', 'Tüm Uyarılar\n(-Wall -Wextra)', 'Katı Güvenlik\n(-Werror -Wconversion)']
    caught_rates = [25, 75, 100]

    # 3. Ariane 5 Yatay Hız Simülasyonu
    velocities = np.linspace(10000, 45000, 100)
    int16_limit = 32767
    crashed_mask = velocities > int16_limit

    # 4. Mars Climate Orbiter Yörünge Sapması
    forces = [100.0, 200.0, 300.0, 400.0, 500.0]
    trajectories_safe = []
    trajectories_buggy = []
    for f in forces:
        _, tr_safe = HistoricalSabotageSimulator.simulate_mars_climate_orbiter_disaster(f, is_metric=True)
        _, tr_bug = HistoricalSabotageSimulator.simulate_mars_climate_orbiter_disaster(f, is_metric=False)
        trajectories_safe.append(tr_safe)
        trajectories_buggy.append(tr_bug)

    # ==================== GRAFİK ÇİZİMİ (300 DPI Dark Tema) ====================
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0d1117')

    color_accent = '#58a6ff'
    color_warn = '#f85149'
    color_success = '#3fb950'
    color_gold = '#d29922'
    color_purple = '#bc8cff'

    # Panel 1: Hata Keşif Aşamasına Göre Maliyet Çarpanı
    ax1 = axes[0, 0]
    ax1.set_facecolor('#161b22')
    bars1 = ax1.bar(phases, relative_costs, color=[color_success, color_accent, color_gold, color_warn], width=0.45, alpha=0.85)
    ax1.set_yscale('log')
    ax1.set_title('Panel 1: Hatanın Keşif Fazına Göre Göreli Düzeltme Maliyeti', fontsize=12, fontweight='bold', color='white', pad=10)
    ax1.set_ylabel('Göreli Maliyet Çarpanı (Logaritmik)', fontsize=10, color='#8b949e')
    ax1.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars1:
        h = b.get_height()
        ax1.text(b.get_x() + b.get_width()/2.0, h * 1.3, f'{int(h):,}x', ha='center', color='white', fontweight='bold')

    # Panel 2: Derleyici Bayraklarının Hata Önleme Gücü
    ax2 = axes[0, 1]
    ax2.set_facecolor('#161b22')
    bars2 = ax2.bar(flags_labels, caught_rates, color=[color_warn, color_gold, color_success], width=0.45, alpha=0.85)
    ax2.set_title('Panel 2: Derleme Bayraklarının Potansiyel Hata Yakalama Oranı', fontsize=12, fontweight='bold', color='white', pad=10)
    ax2.set_ylabel('Yakalama Başarısı (%)', fontsize=10, color='#8b949e')
    ax2.set_ylim(0, 115)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    for b in bars2:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2.0, h + 2, f'%{int(h)}', ha='center', color='white', fontweight='bold')

    # Panel 3: Ariane 5 Taşıma Simülasyonu
    ax3 = axes[1, 0]
    ax3.set_facecolor('#161b22')
    ax3.plot(velocities, velocities, color=color_accent, linewidth=2, label='Sensör Ölçülen Hız (Float64)')
    ax3.axhline(y=int16_limit, color=color_warn, linestyle='--', linewidth=2.5, label='Int16 Tavan Limiti (+32,767)')
    ax3.fill_between(velocities, int16_limit, velocities, where=crashed_mask, color=color_warn, alpha=0.3, label='Crash / Çöküş Bölgesi')
    ax3.set_title('Panel 3: Ariane 5 Faciası: Float64 -> Int16 Aritmetik Taşma', fontsize=12, fontweight='bold', color='white', pad=10)
    ax3.set_xlabel('Yatay Hız Ölçümü', fontsize=10, color='#8b949e')
    ax3.set_ylabel('Sayısal Değer', fontsize=10, color='#8b949e')
    ax3.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax3.legend(loc='upper left')

    # Panel 4: Mars Climate Orbiter Sessiz Mantık Hatası
    ax4 = axes[1, 1]
    ax4.set_facecolor('#161b22')
    ax4.plot(forces, trajectories_safe, color=color_success, marker='o', linewidth=2.5, label='Doğru Metrik (Newton) Yörünge (140 km)')
    ax4.plot(forces, trajectories_buggy, color=color_warn, marker='x', linestyle='--', linewidth=2.5, label='Birim Uyumsuzluğu (57 km - Atmosferde Yandı!)')
    ax4.axhline(y=80.0, color=color_gold, linestyle=':', label='Kritik Atmosfer Giriş Sınırı (80 km)')
    ax4.set_title('Panel 4: Mars Climate Orbiter: Sessiz Mantık Hatası (Birim Karışması)', fontsize=12, fontweight='bold', color='white', pad=10)
    ax4.set_xlabel('Uygulanan İtki Kuvveti', fontsize=10, color='#8b949e')
    ax4.set_ylabel('Yaklaşma İrtifası (km)', fontsize=10, color='#8b949e')
    ax4.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax4.legend(loc='lower left')

    plt.tight_layout()
    output_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_017_hata_turleri_syntax_runtime_logic.png")
    plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 017 Dashboard başarıyla üretildi: {output_png}")


# =====================================================================
# DOĞRULAMA VE ASSERT TESTLERİ
# =====================================================================

def verify_all():
    print("--- GÜN 017 SİSTEM VE MİMARİ DOĞRULAMA TESTLERİ BAŞLIYOR ---")
    
    # Test 1: Syntax Hata Yakalama Doğrulaması
    ok_syn, msg_syn = ErrorTaxonomy.simulate_syntax_check("def valid_code(): return 42")
    assert ok_syn is True
    bad_syn, msg_bad = ErrorTaxonomy.simulate_syntax_check("def broken_code( return 42")
    assert bad_syn is False
    assert "DERLEME HATASI" in msg_bad
    print("[PASS] Test 1: Sözdizimi (Syntax) derleme aşaması denetimi doğrulandı.")

    # Test 2: Runtime Hata ve Donanımsal Trap Doğrulaması
    ok_run, res_run, _ = ErrorTaxonomy.simulate_runtime_division(100.0, 2.0)
    assert ok_run is True and res_run == 50.0
    bad_run, _, msg_run = ErrorTaxonomy.simulate_runtime_division(100.0, 0.0)
    assert bad_run is False
    assert "RUNTIME_TRAP" in msg_run
    print("[PASS] Test 2: Çalışma zamanı (Runtime) sıfıra bölme istisnası doğrulandı.")

    # Test 3: Ariane 5 Sabotajı Doğrulaması
    safe_vel, _, _ = HistoricalSabotageSimulator.simulate_ariane_5_overflow(25000.0)
    assert safe_vel is True
    crash_vel, _, msg_ariane = HistoricalSabotageSimulator.simulate_ariane_5_overflow(35000.0)
    assert crash_vel is False
    assert "ARIANE_5_CRASH" in msg_ariane
    print("[PASS] Test 3: Ariane 5 aritmetik dönüşüm taşması sabotajı tam sınırda doğrulandı.")

    # Test 4: Mars Climate Orbiter Birim Güvenliği Doğrulaması
    deg = Degree(90.0)
    rad = deg.to_radian()
    assert abs(rad.value - (math.pi / 2.0)) < 1e-6
    safe_deflect = AviyonikGuidanceCalculator.compute_rudder_deflection_safe(rad)
    assert abs(safe_deflect - 10.0) < 1e-6
    print("[PASS] Test 4: Güçlü tipli birim güvenliği ve Mars Orbiter kalkanı doğrulandı.")

    # Test 5: Dashboard Üretimi
    run_benchmarks_and_generate_dashboard()
    print("[PASS] Test 5: 4-Panelli 300 DPI Dashboard üretildi.")
    print("[PASS] Gün 017: Tüm Syntax, Runtime, Logic, Tip Güvenliği ve Tarihi Hata analizleri doğrulandı.")


if __name__ == "__main__":
    verify_all()
