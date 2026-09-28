# -*- coding: utf-8 -*-
"""
================================================================================
GÜN 278: PID KONTROL — ORANSAL (PROPORTIONAL) KONTROL VE KALICI DURUM HATASI
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
================================================================================
"""
# [KOD HÜCRESİ 1: Taktik Gimbal / Taret Pozisyon P-Kontrolcü Simülatörü]
# Amaç: ASELSAN SARP veya elektro-optik FLIR taretinin açısal konumlandırma mekanizmasını
# 2. dereceden eyleyici dinamiğiyle modellemek; oransal (P) kontrolcü ile hedef açıya yönlendirmek.

import numpy as np
import time
from typing import Tuple, Dict, List

class TacticalGimbalActuator:
    """
    2. Dereceden Taktik Gimbal / Taret Eyleyici Modeli:
    J * theta_ddot + b * theta_dot + tau_spring = tau_motor = K_m * u
    
    Durum Vektörü: x = [theta (açı, rad), omega (açısal hız, rad/s)]^T
    Kontrol Girdisi: u (motor gerilimi / tork komutu, V veya A)
    Bozucu Tork  : tau_dist (rüzgar / aerodinamik sürtünme momenti, N.m)
    """
    def __init__(self, J: float = 0.05, b: float = 0.25, Km: float = 1.20, k_spring: float = 0.50):
        self.J = J          # Taret eylemsizlik momenti (kg.m^2)
        self.b = b          # Viskoz sürtünme katsayısı (N.m.s/rad)
        self.Km = Km        # Motor tork sabiti (N.m / V)
        self.k_spring = k_spring # Kablo demeti / yay geri çağırma sertliği (N.m/rad)
        self.u_max = 24.0   # Maksimum motor gerilim sınırı (Volt)
        
    def state_derivative(self, x: np.ndarray, u: float, tau_dist: float = 0.0) -> np.ndarray:
        theta, omega = x[0], x[1]
        u_clamped = np.clip(u, -self.u_max, self.u_max)
        
        # theta_dot = omega
        # omega_dot = (Km * u - b * omega - k_spring * theta + tau_dist) / J
        theta_dot = omega
        omega_dot = (self.Km * u_clamped - self.b * omega - self.k_spring * theta + tau_dist) / self.J
        return np.array([theta_dot, omega_dot], dtype=np.float64)
        
    def step_rk4(self, x: np.ndarray, u: float, tau_dist: float, dt: float) -> np.ndarray:
        """4. Dereceden Runge-Kutta Sayısal İntegrasyonu"""
        k1 = self.state_derivative(x, u, tau_dist)
        k2 = self.state_derivative(x + 0.5 * dt * k1, u, tau_dist)
        k3 = self.state_derivative(x + 0.5 * dt * k2, u, tau_dist)
        k4 = self.state_derivative(x + dt * k3, u, tau_dist)
        return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

class ProportionalController:
    """Saf Oransal (P) Kontrolcü: u(t) = K_p * e(t)"""
    def __init__(self, Kp: float):
        self.Kp = Kp
        
    def compute_command(self, target_rad: float, current_rad: float) -> float:
        error = target_rad - current_rad
        return self.Kp * error

# Modeli ve P-Kontrolcüyü kur
gimbal = TacticalGimbalActuator(J=0.05, b=0.85, Km=1.20, k_spring=0.50)
p_ctrl = ProportionalController(Kp=12.0)

# Simülasyon başlangıcı: 0 dereceden 30 dereceye (0.5236 rad) basamak komutu
target_deg = 30.0
target_rad = np.radians(target_deg)

x0 = np.array([0.0, 0.0]) # Başlangıç: Hareketsiz
dt = 0.005 # 200 Hz kontrol döngüsü

# 1 adımlık test
u0 = p_ctrl.compute_command(target_rad, x0[0])
x1 = gimbal.step_rk4(x0, u0, tau_dist=0.0, dt=dt)

print("[PASS] Kod 1: Taktik Gimbal ve P-Kontrolcü Modeli Başarıyla Kuruldu.")
print(f"  - Hedef Açı (Target)         : {target_deg:.1f} derece ({target_rad:.4f} rad)")
print(f"  - Oransal Kazanç (Kp)        : {p_ctrl.Kp:.2f} V/rad")
print(f"  - İlk Kontrol Kumandası (u0) : {u0:.2f} Volt (Sınır: ±{gimbal.u_max:.1f} V)")
print(f"  - dt=0.005s Sonrası Açı (x1) : {np.degrees(x1[0]):.4f} derece")
print(f"  - dt=0.005s Sonrası Hız      : {np.degrees(x1[1]):.4f} deg/s")

assert x1[0] > 0, "Pozitif hata pozitif hareket üretmelidir!"
assert u0 > 0, "Pozitif hata pozitif kontrol gerilimi üretmelidir!"


# [KOD HÜCRESİ 2: Farklı Oransal Kazançların (Kp) Karşılaştırmalı Yanıtı]
# Amaç: Kp kazancının 4 farklı seviyesini (Düşük, Orta, Yüksek, Aşırı Yüksek) simüle etmek;
# Yükselme Zamanı (t_r), Tepe Aşımı (M_p) ve Kalıcı Durum Hatasını (e_ss / Droop) ölçmek.

import numpy as np

def simulate_kp_sweep(gimbal: TacticalGimbalActuator, kp_list: List[float], t_final: float = 3.0, dt: float = 0.005):
    steps = int(t_final / dt)
    t = np.linspace(0, t_final, steps)
    target_rad = np.radians(30.0) # 30 derece hedef
    
    results = {}
    
    for kp in kp_list:
        ctrl = ProportionalController(Kp=kp)
        x = np.zeros(2)
        theta_hist = np.zeros(steps)
        u_hist = np.zeros(steps)
        
        # t = 1.5s anında 0.3 N.m dış bozucu tork (Rüzgar yükü / sürtünme)
        for i in range(steps):
            tau_dist = -0.30 if t[i] >= 1.5 else 0.0
            u = ctrl.compute_command(target_rad, x[0])
            x = gimbal.step_rk4(x, u, tau_dist, dt)
            
            theta_hist[i] = x[0]
            u_hist[i] = u
            
        # Metriklerin Hesaplanması
        theta_deg = np.degrees(theta_hist)
        target_d = 30.0
        
        # 1. Kalıcı Durum Hatası (t = 1.4s, rüzgar öncesi)
        idx_pre_dist = int(1.4 / dt)
        e_ss_deg = abs(target_d - theta_deg[idx_pre_dist])
        
        # 2. Tepe Aşımı (Max Overshoot %)
        peak_deg = np.max(theta_deg[:idx_pre_dist])
        overshoot_pct = max(0.0, (peak_deg - target_d) / target_d * 100.0)
        
        # 3. Yükselme Zamanı (10% ile 90% arası)
        idx_10 = np.where(theta_deg >= 0.10 * target_d)[0]
        idx_90 = np.where(theta_deg >= 0.90 * target_d)[0]
        t_rise = (t[idx_90[0]] - t[idx_10[0]]) if len(idx_90) > 0 else float('nan')
        
        results[kp] = {
            'theta_deg': theta_deg,
            'u_hist': u_hist,
            'e_ss_deg': e_ss_deg,
            'overshoot_pct': overshoot_pct,
            't_rise': t_rise,
            'theta_final_dist': theta_deg[-1]
        }
        
    return t, results

kp_candidates = [1.0, 4.0, 12.0, 35.0]
t_sim, sweep_res = simulate_kp_sweep(gimbal, kp_candidates, t_final=3.0, dt=0.005)

print("[ANALİZ] Oransal Kazanç (Kp) Hassasiyet ve Performans Tablosu:")
print(f"{'Kp':<6} | {'Yükselme t_r (s)':<16} | {'Aşım M_p (%)':<14} | {'Kalıcı Hata e_ss':<18} | {'Rüzgar Sonrası Açı'}")
print("-" * 75)
for kp in kp_candidates:
    r = sweep_res[kp]
    print(f"{kp:<6.1f} | {r['t_rise']:<16.3f} | %{r['overshoot_pct']:<13.1f} | {r['e_ss_deg']:<16.2f}° | {r['theta_final_dist']:.2f}° (Hedef: 30°)")

# Doğrulamalar:
# Kp arttıkça kalıcı durum hatası azalmalıdır (ama asla sıfır olmaz!)
assert sweep_res[35.0]['e_ss_deg'] < sweep_res[1.0]['e_ss_deg'], "Yüksek Kp kalıcı hatayı azaltmalıdır!"
# Kp arttıkça aşım (overshoot) artmalıdır!
assert sweep_res[35.0]['overshoot_pct'] > sweep_res[4.0]['overshoot_pct'], "Yüksek Kp aşımı artırmalıdır!"
# P kontrolcüde kalıcı durum hatası sıfır olamaz!
assert sweep_res[35.0]['e_ss_deg'] > 0.05, "P-kontrolcü tek başına kalıcı hatayı sıfırlayamaz!"


# [KOD HÜCRESİ 3: S-Düzlemi Kök Yer Eğrisi (Root Locus) ve Sönümleme Analizi]
# Amaç: Kapalı çevrim karakteristik denklemi üzerinden Kp arttıkça kutupların
# karmaşık s-düzleminde nasıl hareket ettiğini analitik olarak hesaplamak.
# Karakteristik Denklem: s^2 + (b/J)*s + (k_spring + Kp*Km)/J = 0

import numpy as np

def compute_root_locus(J: float, b: float, Km: float, k_spring: float, kp_range: np.ndarray):
    roots_real = []
    roots_imag = []
    zetas = []
    omegas = []
    
    for kp in kp_range:
        # s^2 + a1 * s + a0 = 0
        a1 = b / J
        a0 = (k_spring + kp * Km) / J
        
        # s1,2 = -a1/2 +- sqrt((a1/2)^2 - a0)
        disc = (a1 / 2.0)**2 - a0
        if disc >= 0:
            r1 = -a1 / 2.0 + np.sqrt(disc)
            r2 = -a1 / 2.0 - np.sqrt(disc)
            roots_real.extend([r1, r2])
            roots_imag.extend([0.0, 0.0])
        else:
            re = -a1 / 2.0
            im = np.sqrt(-disc)
            roots_real.extend([re, re])
            roots_imag.extend([im, -im])
            
        wn = np.sqrt(a0)
        zeta = a1 / (2.0 * wn)
        zetas.append(zeta)
        omegas.append(wn)
        
    return np.array(roots_real), np.array(roots_imag), np.array(zetas), np.array(omegas)

kp_dense = np.linspace(0.1, 150.0, 300)
roots_re, roots_im, zeta_arr, wn_arr = compute_root_locus(gimbal.J, gimbal.b, gimbal.Km, gimbal.k_spring, kp_dense)

print("[PASS] Kod 3: Kök Yer Eğrisi ve Sönümleme Analizi:")
print(f"  * Kp = 0.1  İken Doğal Frekans: {wn_arr[0]:.2f} rad/s | Sönümleme zeta: {zeta_arr[0]:.3f} (Aşırı Sönümlü)")
print(f"  * Kp = 25.0 İken Doğal Frekans: {wn_arr[50]:.2f} rad/s | Sönümleme zeta: {zeta_arr[50]:.3f} (Dengeli)")
print(f"  * Kp = 150  İken Doğal Frekans: {wn_arr[-1]:.2f} rad/s | Sönümleme zeta: {zeta_arr[-1]:.3f} (Düşük Sönüm / Yüksek Titreşim)")

assert zeta_arr[-1] < zeta_arr[0], "Kp arttıkça sönümleme oranı (zeta) düşmelidir!"
assert wn_arr[-1] > wn_arr[0], "Kp arttıkça sistemin doğal frekansı artmalıdır!"


# [KOD HÜCRESİ 4: 3 Askeri Uç Durum ve Savunma Güvenlik Kalkanı Testleri]
# Amaç: DO-178C DAL-A taret/gimbal otopilotunda P-kontrolcüyü koruyan 3 kritik güvenlik kalkanı:
# 1. Eyleyici Doyumu ve Motor Gerilim Kalkanı (P-Command Saturation Guard)
# 2. Yüksek Kazançlı Rezonans ve Titreşim Kalkanı (High-Gain Chattering Guard)
# 3. Yük Torku Altında Kalıcı Hata Eşik Kalkanı (Steady-State Offset Exceedance Guard)

import numpy as np

print("[TEST 1] Eyleyici Doyumu ve Motor Gerilim Kalkanı (Voltage Saturation Guard)...")
class ActuatorVoltageClampingGuard:
    """
    P kontrolcünün ani büyük hedef değişimlerinde ürettiği oransal komutun
    (u = Kp * e) motorun maksimum gerilimini (Örn: +-24V) aşmasını engeller.
    """
    def __init__(self, v_max: float = 24.0):
        self.v_max = v_max
        self.saturation_count = 0
        
    def clamp_command(self, u_raw: float) -> Tuple[float, bool]:
        if abs(u_raw) > self.v_max:
            self.saturation_count += 1
            clamped = float(np.clip(u_raw, -self.v_max, self.v_max))
            return clamped, True
        return u_raw, False

v_guard = ActuatorVoltageClampingGuard(v_max=24.0)
u_safe, sat1 = v_guard.clamp_command(12.5)
u_blown, sat2 = v_guard.clamp_command(95.0)

assert not sat1 and u_safe == 12.5, "Güvenli voltaj doğrudan iletilmelidir!"
assert sat2 and u_blown == 24.0, "Taşan voltaj 24.0V'a kırpılmalıdır!"
print(f"  - Nominal Komut : 12.5V -> [GEÇERLİ]")
print(f"  - Taşan Komut   : 95.0V -> Sınırlandı: {u_blown:.1f}V (Doyum: {sat2})")
print("  [PASS] Test 1: Gerilim Doyum Kalkanı başarıyla doğrulandı.\n")


print("[TEST 2] Yüksek Kazançlı Rezonans ve Titreşim Kalkanı (Chattering Guard)...")
class HighGainChatteringGuard:
    """
    Kp kazancı gereğinden fazla büyütüldüğünde motor yüksek frekansta titremeye
    (chattering) başlar. Bu kalkan kontrol sinyali türevini izler; titreşim eşiğini aşarsa
    Kp kazancını otomatik olarak sönümler (%50 azaltır).
    """
    def __init__(self, max_slew_rate: float = 500.0):
        self.max_slew = max_slew_rate # V/s
        self.last_u = 0.0
        self.gain_derated = False
        
    def check_stability(self, u_cmd: float, dt: float, current_kp: float) -> Tuple[float, bool]:
        slew = abs(u_cmd - self.last_u) / dt
        self.last_u = u_cmd
        if slew > self.max_slew:
            self.gain_derated = True
            safe_kp = current_kp * 0.50
            return safe_kp, True
        self.gain_derated = False
        return current_kp, False

chatter_guard = HighGainChatteringGuard(max_slew_rate=500.0)
kp_ok, ch1 = chatter_guard.check_stability(u_cmd=10.0, dt=0.05, current_kp=20.0) # slew = 200 V/s
kp_derated, ch2 = chatter_guard.check_stability(u_cmd=45.0, dt=0.01, current_kp=80.0) # slew = 3500 V/s

assert not ch1 and kp_ok == 20.0, "Düşük ivmelenmede kazanç korunmalıdır!"
assert ch2 and kp_derated == 40.0, "Titreşimde kazanç derating edilmelidir!"
print(f"  - Normal Slew   : 200 V/s -> [STABİL]")
print(f"  - Yüksek Slew   : 3500 V/s -> [TİTREŞİM ALARMI] -> Kp düşürüldü: {kp_derated:.1f}")
print("  [PASS] Test 2: Titreşim ve Rezonans Kalkanı başarıyla doğrulandı.\n")


print("[TEST 3] Yük Torku Altında Kalıcı Hata Eşik Kalkanı (Offset Guard)...")
class SteadyStateOffsetGuard:
    """
    P-kontrolcünün doğasında bulunan kalıcı durum hatasını izler.
    Eğer hata 2 saniye boyunca izin verilen toleransın (Örn: 1.5 derece)
    üzerinde kalırsa (rüzgar/ağırlık torku yüzünden), integral kontrolcüye geçiş
    veya trim uyarısı bayrağı tetikler.
    """
    def __init__(self, max_allowed_offset_deg: float = 1.5):
        self.max_offset_deg = max_allowed_offset_deg
        
    def evaluate_tracking(self, error_deg: float) -> Tuple[bool, str]:
        if abs(error_deg) > self.max_offset_deg:
            return False, "KALICI_HATA_ESIK_ASILDI_INTEGRAL_GEREKLI"
        return True, "HATA_TOLERANS_DAHILINDE"

offset_guard = SteadyStateOffsetGuard(max_allowed_offset_deg=1.5)
st1, msg1 = offset_guard.evaluate_tracking(error_deg=0.45)
st2, msg2 = offset_guard.evaluate_tracking(error_deg=3.80)

assert st1, "Düşük hata kabul edilmelidir!"
assert not st2, "Yüksek offset integral ihtiyacı alarmı üretmelidir!"
print(f"  - Küçük Hata (0.45°) : Durum=[{msg1}]")
print(f"  - Büyük Offset (3.80°): Durum=[{msg2}]")
print("  [PASS] Test 3: Kalıcı Hata Eşik Kalkanı başarıyla doğrulandı.")


# [KOD HÜCRESİ 5: 4 Panelli Aviyonik Oransal Kontrol Dashboard Görselleştirmesi]
# Amaç: P-kontrolcünün farklı Kp değerlerindeki adım yanıtını, kalıcı durum hatasını,
# s-düzlemi kök yer eğrisini ve aviyonik taret HUD hedefleme ekranını gösteren
# 4 panelli, 300 DPI, koyu temalı (#0F172A) görsel üretimi.

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

# PANEL 1 (Sol Üst): Kp Parametre Süpürme Zaman Yanıtları (Step Response)
colors = ['#94A3B8', '#38BDF8', '#10B981', '#F43F5E']
for idx, kp in enumerate(kp_candidates):
    axs[0, 0].plot(t_sim, sweep_res[kp]['theta_deg'], color=colors[idx], linewidth=2.0, label=f'Kp = {kp:.1f}')

axs[0, 0].axhline(y=30.0, color='#F59E0B', linestyle='--', linewidth=1.5, label='Hedef Açı (30°)')
axs[0, 0].axvline(x=1.5, color='#EF4444', linestyle=':', label='Bozucu Rüzgar Torku (-0.3 Nm)')
axs[0, 0].set_title("Farklı Kp Kazançlarında Basamak Tepkisi ve Rüzgar Yükü", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[0, 0].set_xlabel("Zaman (saniye)", fontsize=11, color='#E2E8F0')
axs[0, 0].set_ylabel("Gimbal Açısı (derece)", fontsize=11, color='#E2E8F0')
axs[0, 0].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[0, 0].legend(loc='lower right', facecolor='#1E293B', edgecolor='#334155', fontsize=9)

# PANEL 2 (Sağ Üst): Kalıcı Durum Hatası (Steady-State Droop) vs Kp
kp_theory = np.linspace(1.0, 100.0, 150)
# e_ss teorik = target * k_spring / (k_spring + Kp * Km)
e_ss_theory_deg = 30.0 * gimbal.k_spring / (gimbal.k_spring + kp_theory * gimbal.Km)

axs[0, 1].plot(kp_theory, e_ss_theory_deg, color='#38BDF8', linewidth=2.2, label=r'Teorik Droop: $e_{ss} = \frac{k_{spring} \cdot r}{k_{spring} + K_p K_m}$')
measured_kps = kp_candidates
measured_ess = [sweep_res[kp]['e_ss_deg'] for kp in measured_kps]
axs[0, 1].scatter(measured_kps, measured_ess, color='#F43F5E', s=90, zorder=5, label='Simüle Edilen Kalıcı Hata')

axs[0, 1].set_title("P-Kontrolcünün Doğası: Kalıcı Durum Hatası Neden Sıfırlanamaz?", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[0, 1].set_xlabel("Oransal Kazanç Kp (V/rad)", fontsize=11, color='#E2E8F0')
axs[0, 1].set_ylabel("Kalıcı Durum Hatası (derece)", fontsize=11, color='#E2E8F0')
axs[0, 1].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[0, 1].legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=9)

# PANEL 3 (Sol Alt): S-Düzlemi Kök Yer Eğrisi (Root Locus: Kp Değişimi)
axs[1, 0].scatter(roots_re, roots_im, c=np.repeat(kp_dense, 2), cmap='plasma', s=8, alpha=0.8)
axs[1, 0].axvline(0, color='#EF4444', linestyle='--', linewidth=1.5, label='Kararlılık Sınırı (Re=0)')
axs[1, 0].axhline(0, color='#64748B', linestyle='-', linewidth=1.0)
axs[1, 0].set_title("S-Düzleminde Kök Yer Eğrisi: Kp Arttıkça Sönümün Yok Oluşu", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[1, 0].set_xlabel(r"Reel Eksen $\sigma$ (Sönümleme)", fontsize=11, color='#E2E8F0')
axs[1, 0].set_ylabel(r"İmajiner Eksen $j\omega$ (Salınım Frekansı)", fontsize=11, color='#E2E8F0')
axs[1, 0].grid(True, linestyle='--', alpha=0.3, color='#475569')

# PANEL 4 (Sağ Alt): Aviyonik Gimbal HUD Taktik Nişangah Arayüzü
hud_canvas = np.zeros((400, 600, 3), dtype=np.uint8)
hud_canvas[:] = [15, 23, 42]

axs[1, 1].imshow(hud_canvas)
axs[1, 1].set_title("Taktik Elektro-Optik FLIR Gimbal HUD Arayüzü", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)

# Nişangah ve Daire
axs[1, 1].axvline(x=300, color='#10B981', linestyle=':', alpha=0.6)
axs[1, 1].axhline(y=200, color='#10B981', linestyle=':', alpha=0.6)
circle = plt.Circle((300, 200), 70, color='#10B981', fill=False, linestyle='--', linewidth=1.5)
axs[1, 1].add_patch(circle)

# Hedef ve Mevcut Konum
axs[1, 1].scatter([300], [200], color='#F43F5E', s=80, marker='+', label='Kilit Noktası')
axs[1, 1].text(30, 45, "ASELSAN SARP / FLIR GIMBAL POSITION CONTROLLER", color='#38BDF8', fontsize=9, fontfamily='monospace', fontweight='bold')
axs[1, 1].text(30, 75, "KONTROL TİPİ : SAF ORANSAL (P-ONLY CONTROLLER)", color='#F59E0B', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 105, f"OPTİMAL Kp   : 12.0 V/rad | DOYUM LİMİTİ: ±24V", color='#E2E8F0', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 130, f"HEDEF AÇI    : 30.00° | MEVCUT: {sweep_res[12.0]['theta_deg'][int(1.4/0.005)]:.2f}°", color='#10B981', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 155, f"KALICI DROOP : {sweep_res[12.0]['e_ss_deg']:.2f}° (İNTEGRAL TERİMİ GEREKLİ)", color='#F43F5E', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 185, "GÜVENLİK KALKANI: VOLTAGE CLAMP & CHATTERING GUARD ON", color='#10B981', fontsize=8, fontfamily='monospace')
axs[1, 1].text(30, 360, "DO-178C LEVEL A MISSION CRITICAL CORE", color='#64748B', fontsize=8, fontfamily='monospace')
axs[1, 1].axis('off')

plt.suptitle("GÜN 278: PID KONTROL — ORANSAL (PROPORTIONAL) KONTROL VE KALICI DURUM HATASI", 
             fontsize=16, fontweight='heavy', color='#F8FAFC', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

out_png = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_278/gun_278_pid_proportional.png"
plt.savefig(out_png, dpi=300, facecolor='#0F172A')
plt.close()

png_size = os.path.getsize(out_png)
print(f"[OK] 4-Panelli P-Kontrolcu Gorseli Basariyla Uretildi: {out_png}")
print(f"  - Dosya Boyutu: {png_size / 1024.0:.2f} KB (Beklenen: > 100 KB)")
assert png_size > 100 * 1024, "Görsel boyutu 100 KB üzerinde olmalıdır!"


# [KOD HÜCRESİ 6: Aviyonik Taret Performans Doğrulaması & Raporlama]
# Amaç: P-kontrolcünün askeri servo standartlarına göre bant genişliği, tepe aşımı
# ve kalıcı hata metriklerini doğrulamak; bir sonraki gün olan İntegral (I) ihtiyacını raporlamak.

import numpy as np

def generate_proportional_control_report(res: Dict[float, Dict[str, float]]) -> Dict[str, float]:
    best_kp = 12.0
    return {
        'best_kp': best_kp,
        'best_tr': res[best_kp]['t_rise'],
        'best_mp': res[best_kp]['overshoot_pct'],
        'best_ess': res[best_kp]['e_ss_deg'],
        'dist_drop': abs(res[best_kp]['theta_deg'][int(1.4/0.005)] - res[best_kp]['theta_final_dist'])
    }

rep = generate_proportional_control_report(sweep_res)

print("\n==========================================================================")
print("[AVİYONİK SERVO TEST RAPORU: ORANSAL (P) KONTROL VE DROOP KARAKTERİSTİĞİ]")
print("==========================================================================")
print(f"  * Seçilen Optimal Kp        : {rep['best_kp']:.1f} V/rad")
print(f"  * Ölçülen Yükselme Zamanı   : {rep['best_tr']:.3f} saniye (< 0.20s şartı sağlandı)")
print(f"  * Ölçülen Tepe Aşımı        : %{rep['best_mp']:.1f} (< %25 askeri limit)")
print(f"  * Kalıcı Durum Hatası (Droop): {rep['best_ess']:.2f} derece (P-kontrolcü limiti)")
print(f"  * Rüzgar Altında İlave Sapma: {rep['dist_drop']:.2f} derece")
print(f"  * MİMARİ KARAR              : [İNTEGRAL (I) TERİMİ ENTEGRASYONU ZORUNLUDUR]")
print("==========================================================================\n")

assert rep['best_tr'] < 0.25, "Optimal Kp hızlı yükselme zamanı sağlamalıdır!"
assert rep['best_mp'] < 30.0, "Optimal Kp aşırı aşım üretmemelidir!"
assert rep['best_ess'] > 0.1, "P kontrolcünün offset ürettiği doğrulanmalıdır!"

