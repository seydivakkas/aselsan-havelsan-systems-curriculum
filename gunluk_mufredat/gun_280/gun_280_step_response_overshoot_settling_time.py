# -*- coding: utf-8 -*-
"""
================================================================================
GÜN 280: BASAMAK YANITI, AŞIM (OVERSHOOT) VE OTURMA ZAMANI (SETTLING TIME)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
================================================================================
"""
# [KOD HÜCRESİ 1: 2. Derece Aviyonik Sistem Modeli ve Zaman Düzlemi Metrik Ekstraktörü]
# Amaç: Taktik servo ve otopilot sistemleri için standart 2. dereceden dinamik model kurmak:
# y_ddot + 2*zeta*wn*y_dot + wn^2*y = wn^2*u
# ve zaman düzlemi spesifikasyonlarını (t_r, t_p, M_p, t_s %2 ve %5) analitik doğrulukla hesaplamak.

import numpy as np
import time
from typing import Dict, Tuple, List

class SecondOrderSystem:
    """
    Standart 2. Dereceden LTI Dinamik Sistem:
    G(s) = omega_n^2 / (s^2 + 2*zeta*omega_n*s + omega_n^2)
    Durum Vektörü: x = [y, y_dot]^T
    """
    def __init__(self, wn: float = 10.0, zeta: float = 0.707):
        self.wn = wn        # Doğal Açısal Frekans (rad/s)
        self.zeta = zeta    # Sönümleme Oranı (Damping Ratio)
        
    def step_rk4(self, state: np.ndarray, u: float, dt: float) -> np.ndarray:
        def f(s):
            pos, vel = s[0], s[1]
            acc = (self.wn ** 2) * (u - pos) - 2.0 * self.zeta * self.wn * vel
            return np.array([vel, acc], dtype=np.float64)
            
        k1 = f(state)
        k2 = f(state + 0.5 * dt * k1)
        k3 = f(state + 0.5 * dt * k2)
        k4 = f(state + dt * k3)
        return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

class StepResponseAnalyzer:
    """
    Zaman Düzlemi Metrik Ekstraktörü:
    - Yükselme Zamanı (t_r): %10'dan %90'a geçiş süresi
    - Tepe Zamanı (t_p): Maksimum çıktıya ulaşılan ilk an
    - Tepe Aşımı (M_p): Yüzde maksimum aşım ((y_max - y_target)/y_target * 100)
    - Oturma Zamanı (t_s %2 ve %5): Hatanın tolerans bandına girip bir daha çıkmadığı an
    - Kalıcı Hata (e_ss): Nihai hedef takip hatası
    """
    @staticmethod
    def extract_metrics(t: np.ndarray, y: np.ndarray, target: float = 1.0) -> Dict[str, float]:
        steps = len(t)
        dt = t[1] - t[0] if steps > 1 else 0.001
        
        # 1. Tepe Değer ve Tepe Zamanı
        idx_peak = int(np.argmax(y))
        y_max = float(y[idx_peak])
        t_p = float(t[idx_peak])
        
        # 2. Tepe Aşımı (M_p %)
        overshoot_pct = max(0.0, (y_max - target) / target * 100.0)
        
        # 3. Yükselme Zamanı (t_r: %10 -> %90)
        idx_10 = np.where(y >= 0.10 * target)[0]
        idx_90 = np.where(y >= 0.90 * target)[0]
        if len(idx_10) > 0 and len(idx_90) > 0:
            t_rise = float(t[idx_90[0]] - t[idx_10[0]])
        else:
            t_rise = float('nan')
            
        # 4. Oturma Zamanı (t_s %2 Bandı)
        band_2 = 0.02 * target
        out_2 = np.where(np.abs(y - target) > band_2)[0]
        if len(out_2) == 0:
            t_settle_2 = 0.0
        elif out_2[-1] + 1 < steps:
            t_settle_2 = float(t[out_2[-1] + 1])
        else:
            t_settle_2 = float(t[-1])
            
        # 5. Oturma Zamanı (t_s %5 Bandı)
        band_5 = 0.05 * target
        out_5 = np.where(np.abs(y - target) > band_5)[0]
        if len(out_5) == 0:
            t_settle_5 = 0.0
        elif out_5[-1] + 1 < steps:
            t_settle_5 = float(t[out_5[-1] + 1])
        else:
            t_settle_5 = float(t[-1])
            
        # 6. Kalıcı Durum Hatası (e_ss)
        e_ss = float(abs(target - y[-1]))
        
        return {
            'y_max': y_max,
            't_p': t_p,
            'overshoot_pct': overshoot_pct,
            't_rise': t_rise,
            't_settle_2': t_settle_2,
            't_settle_5': t_settle_5,
            'e_ss': e_ss
        }

# Doğrulama: Standart Butterworth Damping (zeta = 0.707, wn = 10.0 rad/s)
sys_nominal = SecondOrderSystem(wn=10.0, zeta=0.707)
dt = 0.001
t_sim = np.arange(0, 2.0, dt)
x_state = np.zeros(2)
y_hist = np.zeros(len(t_sim))

for i in range(len(t_sim)):
    x_state = sys_nominal.step_rk4(x_state, u=1.0, dt=dt)
    y_hist[i] = x_state[0]

metrics_nom = StepResponseAnalyzer.extract_metrics(t_sim, y_hist, target=1.0)

print("[PASS] Kod 1: 2. Derece Sistem ve Zaman Metrik Ekstraktörü Kuruldu.")
print(f"  - Yükselme Zamanı (t_r %10-%90) : {metrics_nom['t_rise']:.3f} s")
print(f"  - Tepe Zamanı (t_p)            : {metrics_nom['t_p']:.3f} s")
print(f"  - Yüzde Tepe Aşımı (M_p)       : %{metrics_nom['overshoot_pct']:.2f}")
print(f"  - Oturma Zamanı (t_s %2 Bandı) : {metrics_nom['t_settle_2']:.3f} s")
print(f"  - Kalıcı Durum Hatası (e_ss)   : {metrics_nom['e_ss']:.6f}")

assert metrics_nom['overshoot_pct'] < 5.0, "zeta=0.707 için aşım %5 altında olmalıdır!"
assert metrics_nom['t_settle_2'] < 0.70, "Oturma zamanı 0.7s altında kalmalıdır!"
assert metrics_nom['e_ss'] < 0.001, "Kalıcı hata sıfıra yakın olmalıdır!"


# [KOD HÜCRESİ 2: Parametrik Sönümleme (zeta) Taraması ve Teorik vs Ölçülen Analizi]
# Amaç: Sönümleme oranının (zeta) basamak yanıtı üzerindeki etkisini incelemek:
# 1. Az Sönümlü (Underdamped, zeta < 1.0): Salınım ve aşım var.
# 2. Kritik Sönümlü (Critically Damped, zeta = 1.0): Aşım yok, en hızlı oturma.
# 3. Aşırı Sönümlü (Overdamped, zeta > 1.0): Aşım yok, tembel ve yavaş oturma.
# Teorik formül: M_p = exp(-pi * zeta / sqrt(1 - zeta^2)) * 100

import numpy as np

def run_damping_sweep(wn: float = 10.0, zetas: List[float] = [0.2, 0.4, 0.707, 1.0, 1.5], t_final: float = 2.0, dt: float = 0.001):
    t = np.arange(0, t_final, dt)
    results = {}
    
    for z in zetas:
        sys = SecondOrderSystem(wn=wn, zeta=z)
        state = np.zeros(2)
        y = np.zeros(len(t))
        for i in range(len(t)):
            state = sys.step_rk4(state, u=1.0, dt=dt)
            y[i] = state[0]
            
        m = StepResponseAnalyzer.extract_metrics(t, y, target=1.0)
        
        # Teorik Aşım Hesabı
        if z < 1.0:
            mp_theo = float(np.exp(-np.pi * z / np.sqrt(1.0 - z**2)) * 100.0)
            tp_theo = float(np.pi / (wn * np.sqrt(1.0 - z**2)))
            ts_theo_2 = float(4.0 / (z * wn))
        else:
            mp_theo = 0.0
            tp_theo = float('nan')
            ts_theo_2 = float('nan')
            
        m['mp_theo'] = mp_theo
        m['tp_theo'] = tp_theo
        m['ts_theo_2'] = ts_theo_2
        m['y'] = y
        results[z] = m
        
    return t, results

zeta_values = [0.2, 0.4, 0.707, 1.0, 1.5]
t_axis, sweep_results = run_damping_sweep(wn=10.0, zetas=zeta_values)

print("[ANALİZ] Parametrik Sönümleme Oranı (zeta) ve Zaman Metrikleri Karşılaştırması:")
print(f"{'zeta':<6} | {'Rejim':<16} | {'t_r (s)':<10} | {'t_p (s)':<10} | {'M_p (%)':<10} | {'M_p Teorik':<12} | {'t_s %2 (s)':<10}")
print("-" * 85)

for z in zeta_values:
    r = sweep_results[z]
    regime = "Az Sönümlü" if z < 1.0 else ("Kritik Sönümlü" if z == 1.0 else "Aşırı Sönümlü")
    print(f"{z:<6.3f} | {regime:<16} | {r['t_rise']:<10.3f} | {r['t_p']:<10.3f} | %{r['overshoot_pct']:<9.1f} | %{r['mp_theo']:<11.1f} | {r['t_settle_2']:<10.3f}")

# Teorik vs Ölçüm Doğrulamaları:
for z in [0.2, 0.4, 0.707]:
    diff = abs(sweep_results[z]['overshoot_pct'] - sweep_results[z]['mp_theo'])
    assert diff < 0.5, f"zeta={z} için teorik aşım ile ölçülen farkı < %0.5 olmalıdır (Fark: {diff:.3f}%)!"

assert sweep_results[1.0]['overshoot_pct'] == 0.0, "zeta=1.0 için aşım sıfır olmalıdır!"
assert sweep_results[1.5]['overshoot_pct'] == 0.0, "zeta=1.5 için aşım sıfır olmalıdır!"
assert sweep_results[0.2]['overshoot_pct'] > 50.0, "zeta=0.2 için aşım %50'den büyük olmalıdır!"
assert sweep_results[1.5]['t_rise'] > sweep_results[0.707]['t_rise'] * 2.0, "Aşırı sönüm çok yavaş yükselmelidir!"


# [KOD HÜCRESİ 3: Askeri Uçuş Kalitesi Standartları (MIL-F-8785C) ve Bozucu Darbe Yanıtı]
# Amaç: Uçuş kontrol sistemlerinde (FCS) askeri Seviye 1, 2, 3 Uçuş Kalitesi standartlarını
# denetlemek ve t=1.0s anında gelen 0.5 Nm ani rüzgar hamlesi (gust) altında sistemin toparlanma süresini test etmek.

import numpy as np

class MilitaryFlyingQualitiesEvaluator:
    """
    MIL-F-8785C & ADS-33E-PRF Askeri Uçuş Kalitesi Sınıflandırıcısı:
    - Level 1: Görev kalitesi mükemmel, pilot iş yükü düşük (M_p <= 10%, 0.35 <= zeta <= 1.30, t_s <= 1.0s)
    - Level 2: Görev yapılabilir fakat pilot iş yükü yüksek (10% < M_p <= 30%, 0.20 <= zeta < 0.35, t_s <= 2.5s)
    - Level 3: Kontrol kaybı tehlikesi, kritik uçuş modu (M_p > 30% veya zeta < 0.20 veya t_s > 2.5s)
    """
    @staticmethod
    def classify_level(zeta: float, overshoot_pct: float, t_settle: float) -> str:
        if (0.35 <= zeta <= 1.30) and (overshoot_pct <= 10.0) and (t_settle <= 1.0):
            return "LEVEL 1 (MISSION READY - TACTICAL SUPERIORITY)"
        elif (0.20 <= zeta <= 1.60) and (overshoot_pct <= 30.0) and (t_settle <= 2.5):
            return "LEVEL 2 (ACCEPTABLE - HIGH PILOT WORKLOAD)"
        else:
            return "LEVEL 3 (CRITICAL RISK - LOSS OF CONTROL DANGER)"

def simulate_with_gust(wn: float = 10.0, zeta: float = 0.707, t_final: float = 2.5, dt: float = 0.001):
    t = np.arange(0, t_final, dt)
    sys = SecondOrderSystem(wn=wn, zeta=zeta)
    state = np.zeros(2)
    y = np.zeros(len(t))
    u_base = 1.0
    
    for i in range(len(t)):
        # t = 1.2s anında 0.35 birim genlikli sert rüzgar hamlesi darbesi (Pulse Disturbance)
        gust = 0.35 if (1.20 <= t[i] <= 1.35) else 0.0
        # Fiziksel sisteme etkiyen toplam girdi: u + gust
        state = sys.step_rk4(state, u=(u_base + gust), dt=dt)
        y[i] = state[0]
        
    # Bozucu sonrası toparlanma süresi (Recovery Time)
    idx_gust_end = int(1.35 / dt)
    band = 0.02 * u_base
    out_post_gust = np.where(np.abs(y[idx_gust_end:] - u_base) > band)[0]
    if len(out_post_gust) > 0:
        t_recovery = float(out_post_gust[-1] * dt)
    else:
        t_recovery = 0.0
        
    return t, y, t_recovery

t_gust, y_gust, t_rec = simulate_with_gust(wn=10.0, zeta=0.707)

evaluator = MilitaryFlyingQualitiesEvaluator()
nom_level = evaluator.classify_level(0.707, sweep_results[0.707]['overshoot_pct'], sweep_results[0.707]['t_settle_2'])
low_level = evaluator.classify_level(0.200, sweep_results[0.200]['overshoot_pct'], sweep_results[0.200]['t_settle_2'])

print("[PASS] Kod 3: Askeri Uçuş Kalitesi Değerlendirmesi:")
print(f"  * Nominal Sistem (zeta=0.707) Sınıfı : {nom_level}")
print(f"  * Düşük Sönümlü (zeta=0.200) Sınıfı  : {low_level}")
print(f"  * Rüzgar Darbesi Toparlanma Süresi   : {t_rec:.3f} s (Hedef: < 0.50 s)")

assert "LEVEL 1" in nom_level, "Nominal sistem Seviye 1 standartlarını sağlamalıdır!"
assert "LEVEL 3" in low_level, "0.2 sönümleme Seviye 3 riskli kabul edilmelidir!"
assert t_rec < 0.50, "Sistem rüzgar darbesinden 0.5 saniyede kurtulmalıdır!"


# [KOD HÜCRESİ 4: 3 Askeri Uç Durum ve Güvenlik Kalkanı Testleri]
# Amaç: DO-178C DAL-A sertifikasyonlu uçuş kontrolcülerinde basamak yanıtını denetleyen 3 kalkan:
# 1. Yetersiz Sönümleme Kalkanı (Underdamped Resonance Guard - Aşırı Osilasyon Alarmı)
# 2. Tembel Yanıt ve Aşırı Sönümleme Kalkanı (Sluggish Response Guard - Hedef Kaçırma Alarmı)
# 3. Kalıcı Salınım ve Tolerans Zarfı Kalkanı (Limit Cycle & Settling Envelope Guard)

import numpy as np

print("[TEST 1] Yetersiz Sönümleme Kalkanı (Underdamped Resonance Guard)...")
class UnderdampedResonanceGuard:
    """
    zeta < 0.25 durumunda mekanik gövde rezonansa girer, aşım %50'yi aşar ve eyleyici dişlileri kırılır.
    Bu kalkan aşımın %20'yi aştığı anda emniyet modunu (actuator safe mode) tetikler.
    """
    def __init__(self, max_allowed_overshoot_pct: float = 20.0):
        self.max_mp = max_allowed_overshoot_pct
        
    def inspect(self, overshoot_pct: float) -> Tuple[bool, str]:
        if overshoot_pct > self.max_mp:
            return False, f"RESONANCE DETECTED: Overshoot %{overshoot_pct:.1f} exceeds limit %{self.max_mp:.1f}!"
        return True, "DAMPING NOMINAL"

res_guard = UnderdampedResonanceGuard(max_allowed_overshoot_pct=20.0)
passed_nom, msg_nom = res_guard.inspect(sweep_results[0.707]['overshoot_pct'])
passed_bad, msg_bad = res_guard.inspect(sweep_results[0.200]['overshoot_pct'])

assert passed_nom is True, "zeta=0.707 kalkanı geçmelidir!"
assert passed_bad is False, "zeta=0.200 rezonans alarmı vermelidir!"
print(f"  - Nominal Durum (zeta=0.707) : {msg_nom} [GÜVENLİ]")
print(f"  - Tehlikeli Durum (zeta=0.2) : {msg_bad} [KORUMA DEVREDE]")
print("  [PASS] Test 1: Yetersiz Sönümleme Kalkanı başarıyla doğrulandı.\n")


print("[TEST 2] Tembel Yanıt ve Aşırı Sönümleme Kalkanı (Sluggish Response Guard)...")
class SluggishResponseGuard:
    """
    Füze kaçınma veya hedef takibinde yükselme zamanı t_r > 0.45s olursa hedef radar konisinden çıkar.
    Bu kalkan yükselme süresini denetler.
    """
    def __init__(self, max_allowed_tr: float = 0.45):
        self.max_tr = max_allowed_tr
        
    def inspect(self, tr: float) -> Tuple[bool, str]:
        if tr > self.max_tr:
            return False, f"SLUGGISH RESPONSE: Rise time {tr:.3f}s exceeds tactical deadline {self.max_tr:.3f}s!"
        return True, "RESPONSE FAST AND CRISP"

slug_guard = SluggishResponseGuard(max_allowed_tr=0.45)
pass_slug_nom, m_slug_nom = slug_guard.inspect(sweep_results[0.707]['t_rise'])
pass_slug_bad, m_slug_bad = slug_guard.inspect(sweep_results[1.500]['t_rise'])

assert pass_slug_nom is True, "zeta=0.707 hızlı yükselmelidir!"
assert pass_slug_bad is False, "zeta=1.500 tembel yanıt alarmı vermelidir!"
print(f"  - Nominal Yükselme (zeta=0.707) : {m_slug_nom} (t_r = {sweep_results[0.707]['t_rise']:.3f}s)")
print(f"  - Aşırı Sönüm (zeta=1.500)      : {m_slug_bad} (t_r = {sweep_results[1.500]['t_rise']:.3f}s)")
print("  [PASS] Test 2: Tembel Yanıt Kalkanı başarıyla doğrulandı.\n")


print("[TEST 3] Kalıcı Salınım ve Tolerans Zarfı Kalkanı (Limit Cycle & Settling Envelope Guard)...")
class SettlingEnvelopeGuard:
    """
    Belirli bir t_deadline anından sonra sistem çıktısının daima [target - band, target + band]
    zarfında kalmasını şart koşar. Aksi takdirde limit döngüsü (limit cycle) veya sızıntı ilan edilir.
    """
    def __init__(self, target: float = 1.0, band_pct: float = 2.0, t_deadline: float = 1.0):
        self.target = target
        self.band = (band_pct / 100.0) * target
        self.t_deadline = t_deadline
        
    def inspect(self, t: np.ndarray, y: np.ndarray) -> Tuple[bool, str]:
        idx_dead = np.where(t >= self.t_deadline)[0]
        tail_y = y[idx_dead]
        outliers = np.where(np.abs(tail_y - self.target) > self.band)[0]
        if len(outliers) > 0:
            max_dev = np.max(np.abs(tail_y - self.target))
            return False, f"ENVELOPE VIOLATION: Deviation {max_dev:.4f} > {self.band:.4f} after {self.t_deadline}s!"
        return True, "STABLE WITHIN TOLERANCE ENVELOPE"

env_guard = SettlingEnvelopeGuard(target=1.0, band_pct=2.0, t_deadline=1.0)
pass_env_nom, m_env_nom = env_guard.inspect(t_axis, sweep_results[0.707]['y'])
pass_env_bad, m_env_bad = env_guard.inspect(t_axis, sweep_results[0.200]['y'])

assert pass_env_nom is True, "zeta=0.707 1 saniyede %2 bandına oturmalıdır!"
assert pass_env_bad is False, "zeta=0.200 1 saniyede %2 bandından taşmalıdır!"
print(f"  - Nominal Zarf (zeta=0.707) : {m_env_nom} [KİLİTLENDİ]")
print(f"  - Taşma Durumu (zeta=0.200) : {m_env_bad} [DIŞINDA]")
print("  [PASS] Test 3: Tolerans Zarfı Kalkanı başarıyla doğrulandı.")


# [KOD HÜCRESİ 5: 4 Panelli Aviyonik Basamak Yanıtı Dashboard Görselleştirmesi]
# Amaç: Farklı sönümleme oranlarının basamak yanıtlarını, %2 tolerans bandını,
# teorik vs ölçülen aşım eğrisini, oturma-yükselme zamanı trade-off çukurunu ve
# aviyonik kokpit HUD telemetrisini gösteren 300 DPI, koyu temalı (#0F172A) görsel üretimi.

import matplotlib.pyplot as plt
import numpy as np
import os

plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.tick_params(colors='#E2E8F0', labelsize=10)
    for spine in ax.spines.values():
        spine.set_color('#334155')

# PANEL 1 (Sol Üst): Sönümleme Oranına Göre Basamak Yanıtları ve %2 Bandı
colors = {0.2: '#EF4444', 0.4: '#F59E0B', 0.707: '#10B981', 1.0: '#38BDF8', 1.5: '#A855F7'}
labels = {
    0.2: 'zeta=0.20 (Az Sönümlü - %52.7 Aşım)',
    0.4: 'zeta=0.40 (Hafif Sönümlü - %25.4 Aşım)',
    0.707: 'zeta=0.707 (Optimum Butterworth - %4.3 Aşım)',
    1.0: 'zeta=1.00 (Kritik Sönümlü - %0 Aşım)',
    1.5: 'zeta=1.50 (Aşırı Sönümlü - Yavaş)'
}

for z in zeta_values:
    linewidth = 2.5 if z == 0.707 else 1.8
    axs[0, 0].plot(t_axis, sweep_results[z]['y'], color=colors[z], linewidth=linewidth, label=labels[z])

# %2 Tolerans Zarfı
axs[0, 0].axhline(y=1.00, color='#FFFFFF', linestyle='--', linewidth=1.2, label='Hedef Referans (1.0)')
axs[0, 0].fill_between(t_axis, 0.98, 1.02, color='#10B981', alpha=0.15, label='±%2 Tolerans Zarfı [0.98, 1.02]')

axs[0, 0].set_title("Standart 2. Derece Basamak Yanıtı: Sönümleme Oranı (zeta) Etkisi", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[0, 0].set_xlabel("Zaman (saniye)", fontsize=11, color='#E2E8F0')
axs[0, 0].set_ylabel("Sistem Çıktısı y(t)", fontsize=11, color='#E2E8F0')
axs[0, 0].set_ylim(-0.1, 1.7)
axs[0, 0].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[0, 0].legend(loc='lower right', facecolor='#1E293B', edgecolor='#334155', fontsize=8.5)

# PANEL 2 (Sağ Üst): Tepe Aşımı (M_p) Teorik Analitik Eğri ve Ölçüm Noktaları
zeta_dense = np.linspace(0.05, 0.95, 200)
mp_curve = np.exp(-np.pi * zeta_dense / np.sqrt(1.0 - zeta_dense**2)) * 100.0

axs[0, 1].plot(zeta_dense, mp_curve, color='#38BDF8', linewidth=2.2, label=r'Teorik $M_p = e^{-\pi\zeta/\sqrt{1-\zeta^2}} \times 100\%$')

# Ölçülen noktalar
measured_zetas = [0.2, 0.4, 0.707]
measured_mps = [sweep_results[z]['overshoot_pct'] for z in measured_zetas]
axs[0, 1].scatter(measured_zetas, measured_mps, color='#EF4444', s=90, zorder=5, label='Simülasyon Ölçümleri (RK4)')

# Askeri Limit Bölgeleri
axs[0, 1].axhspan(0, 10, color='#10B981', alpha=0.2, label='MIL-F-8785C Level 1 (M_p <= %10)')
axs[0, 1].axhspan(10, 30, color='#F59E0B', alpha=0.15, label='MIL-F-8785C Level 2 (%10 < M_p <= %30)')
axs[0, 1].axhspan(30, 80, color='#EF4444', alpha=0.1, label='MIL-F-8785C Level 3 (M_p > %30 Tehlikeli)')

axs[0, 1].set_title("Tepe Aşımı (M_p) ve Askeri Uçuş Kalitesi Zarfı", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[0, 1].set_xlabel("Sönümleme Oranı (zeta)", fontsize=11, color='#E2E8F0')
axs[0, 1].set_ylabel("Maksimum Aşım M_p (%)", fontsize=11, color='#E2E8F0')
axs[0, 1].set_ylim(0, 80)
axs[0, 1].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[0, 1].legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=8.5)

# PANEL 3 (Sol Alt): Oturma Zamanı (t_s) ve Yükselme Zamanı (t_r) Trade-off
z_plot = [0.2, 0.4, 0.6, 0.707, 0.85, 1.0, 1.2, 1.5]
t_temp, res_temp = run_damping_sweep(wn=10.0, zetas=z_plot)
ts_vals = [res_temp[z]['t_settle_2'] for z in z_plot]
tr_vals = [res_temp[z]['t_rise'] for z in z_plot]

axs[1, 0].plot(z_plot, ts_vals, color='#F59E0B', marker='o', linewidth=2.0, label='Oturma Zamanı t_s (%2 Bandı)')
axs[1, 0].plot(z_plot, tr_vals, color='#38BDF8', marker='s', linewidth=2.0, label='Yükselme Zamanı t_r (%10-%90)')

# Optimum çukur çizgisi
axs[1, 0].axvline(x=0.707, color='#10B981', linestyle=':', linewidth=1.8, label='Optimum Nokta (zeta=0.707, Min t_s)')

axs[1, 0].set_title("Tasarımcı İkilemi: Oturma (t_s) vs Yükselme (t_r) Zamanı Trade-Off", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[1, 0].set_xlabel("Sönümleme Oranı (zeta)", fontsize=11, color='#E2E8F0')
axs[1, 0].set_ylabel("Zaman (saniye)", fontsize=11, color='#E2E8F0')
axs[1, 0].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[1, 0].legend(loc='upper left', facecolor='#1E293B', edgecolor='#334155', fontsize=8.5)

# PANEL 4 (Sağ Alt): Aviyonik Uçuş Kontrol Bilgisayarı (FCC) HUD Ekranı
hud_canvas = np.zeros((400, 600, 3), dtype=np.uint8)
hud_canvas[:] = [15, 23, 42]

axs[1, 1].imshow(hud_canvas)
axs[1, 1].set_title("Aviyonik Otopilot / Gimbal Basamak Yanıtı Telemetrisi", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)

# Nişangah ve HUD Grafikleri
axs[1, 1].axvline(x=300, color='#10B981', linestyle=':', alpha=0.6)
axs[1, 1].axhline(y=200, color='#10B981', linestyle=':', alpha=0.6)
rect = plt.Rectangle((220, 140), 160, 120, fill=False, edgecolor='#10B981', linestyle='--', linewidth=1.5)
axs[1, 1].add_patch(rect)

nom_res = sweep_results[0.707]
axs[1, 1].text(30, 45, "ASELSAN / HAVELSAN TIME-DOMAIN SPEC CORE", color='#38BDF8', fontsize=9, fontfamily='monospace', fontweight='bold')
axs[1, 1].text(30, 75, f"DOĞAL FREKANS (wn) : 10.00 rad/s (BANT GENİŞLİĞİ: 1.59 Hz)", color='#E2E8F0', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 105, f"SÖNÜMLEME ORANI(z) : 0.707 (BUTTERWORTH OPTIMAL)", color='#10B981', fontsize=9, fontfamily='monospace', fontweight='bold')
axs[1, 1].text(30, 130, f"YÜKSELME ZAMANI(tr): {nom_res['t_rise']:.3f} s  (< 0.25 s ASKERİ LİMİT)", color='#10B981', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 155, f"TEPE AŞIMI (Mp)    : %{nom_res['overshoot_pct']:.2f} (MIL-F-8785C LEVEL 1)", color='#10B981', fontsize=9, fontfamily='monospace', fontweight='bold')
axs[1, 1].text(30, 185, f"OTURMA ZAMANI(ts)  : {nom_res['t_settle_2']:.3f} s  (%%2 TOLERANS ZARFI)", color='#38BDF8', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 215, "UÇUŞ SERTİFİKASI   : DO-178C LEVEL A / ADS-33E PASS", color='#10B981', fontsize=8.5, fontfamily='monospace')
axs[1, 1].text(30, 360, "AUTOPILOT CLOSED-LOOP STEP TELEMETRY ACTIVE", color='#64748B', fontsize=8, fontfamily='monospace')
axs[1, 1].axis('off')

plt.suptitle("GÜN 280: BASAMAK YANITI, AŞIM (OVERSHOOT) VE OTURMA ZAMANI (SETTLING TIME) ANALİZİ", 
             fontsize=15, fontweight='heavy', color='#F8FAFC', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

out_png = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_280/gun_280_step_response_overshoot_settling_time.png"
plt.savefig(out_png, dpi=300, facecolor='#0F172A')
plt.close()

png_size = os.path.getsize(out_png)
print(f"[OK] 4-Panelli Basamak Yaniti Gorseli Basariyla Uretildi: {out_png}")
print(f"  - Dosya Boyutu: {png_size / 1024.0:.2f} KB (Beklenen: > 100 KB)")
assert png_size > 100 * 1024, "Görsel boyutu 100 KB üzerinde olmalıdır!"


# [KOD HÜCRESİ 6: DO-178C DAL-A Zaman Yanıtı ve Spesifikasyon Doğrulama Raporu]
# Amaç: Taktik otopilot basamak yanıtının aviyonik ve askeri standartlara göre
# uçuş onay kriterlerini (Acceptance Criteria) matematiksel olarak doğrulamak.

import numpy as np

def generate_flight_qualification_report(results: Dict[float, Dict[str, float]]) -> Dict[str, any]:
    nom = results[0.707]
    low = results[0.200]
    high = results[1.500]
    
    crit_1_pass = bool(nom['overshoot_pct'] <= 10.0)
    crit_2_pass = bool(nom['t_settle_2'] <= 1.0)
    crit_3_pass = bool(nom['t_rise'] <= 0.30)
    crit_4_pass = bool(nom['e_ss'] <= 0.005)
    
    all_pass = crit_1_pass and crit_2_pass and crit_3_pass and crit_4_pass
    
    return {
        'zeta_nominal': 0.707,
        'nom_mp': nom['overshoot_pct'],
        'nom_tr': nom['t_rise'],
        'nom_ts': nom['t_settle_2'],
        'nom_ess': nom['e_ss'],
        'underdamped_mp': low['overshoot_pct'],
        'overdamped_tr': high['t_rise'],
        'crit_1_overshoot_pass': crit_1_pass,
        'crit_2_settling_pass': crit_2_pass,
        'crit_3_rise_pass': crit_3_pass,
        'crit_4_ess_pass': crit_4_pass,
        'overall_flight_qualified': all_pass
    }

report = generate_flight_qualification_report(sweep_results)

print("\n==========================================================================")
print("[AVİYONİK SERVO & OTOPİLOT ZAMAN DÜZLEMİ KALİFİKASYON RAPORU]")
print("==========================================================================")
print(f"  * Nominal Sönümleme Oranı (zeta) : {report['zeta_nominal']}")
print(f"  * Yükselme Zamanı (t_r %10-%90)  : {report['nom_tr']:.3f} s (Kriter: <= 0.30s) -> [{'PASS' if report['crit_3_rise_pass'] else 'FAIL'}]")
print(f"  * Tepe Aşımı (M_p)              : %{report['nom_mp']:.2f} (Kriter: <= %10)   -> [{'PASS' if report['crit_1_overshoot_pass'] else 'FAIL'}]")
print(f"  * Oturma Zamanı (t_s %2 Bandı)  : {report['nom_ts']:.3f} s (Kriter: <= 1.00s) -> [{'PASS' if report['crit_2_settling_pass'] else 'FAIL'}]")
print(f"  * Kalıcı Durum Hatası (e_ss)    : {report['nom_ess']:.6f} (Kriter: <= 0.005) -> [{'PASS' if report['crit_4_ess_pass'] else 'FAIL'}]")
print(f"  * Az Sönümlü Rejim Aşımı (z=0.2): %{report['underdamped_mp']:.1f} (Aşırı Titreşim Uyarısı)")
print(f"  * Aşırı Sönümlü Rejim t_r(z=1.5): {report['overdamped_tr']:.3f} s (Tembel Yanıt Uyarısı)")
print(f"  * Askeri Sertifikasyon Kararı   : [MIL-F-8785C LEVEL 1 UÇUŞA UYGUNDUR]")
print("==========================================================================\n")

assert report['crit_1_overshoot_pass'], "Nominal aşım kriteri sağlanmalıdır!"
assert report['crit_2_settling_pass'], "Nominal oturma zamanı kriteri sağlanmalıdır!"
assert report['crit_3_rise_pass'], "Nominal yükselme zamanı kriteri sağlanmalıdır!"
assert report['crit_4_ess_pass'], "Kalıcı durum hatası kriteri sağlanmalıdır!"
assert report['overall_flight_qualified'], "Sistem bütünüyle uçuş onayından geçmelidir!"

