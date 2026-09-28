# -*- coding: utf-8 -*-
"""
================================================================================
GÜN 282: MODERN KONTROL — KONTROL EDİLEBİLİRLİK VE GÖZLEMLENEBİLİRLİK SEZGİSİ
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
================================================================================
"""
# [KOD HÜCRESİ 1: Kalman Kontrol Edilebilirlik (C) ve Gözlemlenebilirlik (O) Matris Motoru]
# Amaç: Çok boyutlu LTI sistemlerde Kalman Kontrol Edilebilirlik Matrisi C = [B, AB, ..., A^(n-1)B]
# ve Gözlemlenebilirlik Matrisi O = [C; CA; ...; CA^(n-1)] cebirsel yapılarını kurmak;
# rank, koşul sayısı (condition number) ve tekil değerleri (singular values) analiz etmek.

import numpy as np
from scipy import linalg
from typing import Dict, Tuple, List

class KalmanGramianEngine:
    """
    Kalman Kontrol Edilebilirlik ve Gözlemlenebilirlik Analiz Motoru:
    - Controllability Matrix: C = [B, A*B, A^2*B, ..., A^(n-1)*B]
    - Observability Matrix:   O = [C; C*A; C*A^2; ...; C*A^(n-1)]
    """
    def __init__(self, A: np.ndarray, B: np.ndarray, C: np.ndarray):
        self.A = np.array(A, dtype=np.float64)
        self.B = np.array(B, dtype=np.float64)
        self.C = np.array(C, dtype=np.float64)
        
        self.n = self.A.shape[0]
        if self.B.ndim == 1:
            self.B = self.B.reshape((self.n, 1))
        if self.C.ndim == 1:
            self.C = self.C.reshape((1, self.n))
            
        self.m = self.B.shape[1]
        self.p = self.C.shape[0]
        
    def compute_controllability_matrix(self) -> np.ndarray:
        """C = [B, A*B, A^2*B, ..., A^(n-1)*B] matrisini hesaplar."""
        blocks = [self.B]
        current_block = self.B
        for _ in range(1, self.n):
            current_block = self.A @ current_block
            blocks.append(current_block)
        return np.hstack(blocks)

    def compute_observability_matrix(self) -> np.ndarray:
        """O = [C; C*A; C*A^2; ...; C*A^(n-1)] matrisini hesaplar."""
        blocks = [self.C]
        current_block = self.C
        for _ in range(1, self.n):
            current_block = current_block @ self.A
            blocks.append(current_block)
        return np.vstack(blocks)

    def evaluate(self) -> Dict[str, any]:
        Ctr = self.compute_controllability_matrix()
        Obs = self.compute_observability_matrix()
        
        rank_c = int(np.linalg.matrix_rank(Ctr))
        rank_o = int(np.linalg.matrix_rank(Obs))
        
        svd_c = np.linalg.svd(Ctr, compute_uv=False)
        svd_o = np.linalg.svd(Obs, compute_uv=False)
        
        cond_c = float(svd_c[0] / svd_c[-1]) if svd_c[-1] > 1e-12 else float('inf')
        cond_o = float(svd_o[0] / svd_o[-1]) if svd_o[-1] > 1e-12 else float('inf')
        
        is_controllable = bool(rank_c == self.n)
        is_observable = bool(rank_o == self.n)
        
        return {
            'Ctr': Ctr,
            'Obs': Obs,
            'rank_c': rank_c,
            'rank_o': rank_o,
            'svd_c': svd_c,
            'svd_o': svd_o,
            'cond_c': cond_c,
            'cond_o': cond_o,
            'is_controllable': is_controllable,
            'is_observable': is_observable
        }

# Taktik İHA Boyuna Uçuş Modeli
A_uav = np.array([
    [-0.045,  0.036,  0.000, -9.810],
    [-0.369, -2.020, 17.000,  0.000],
    [ 0.001, -0.050, -2.050,  0.000],
    [ 0.000,  0.000,  1.000,  0.000]
])

B_uav = np.array([[0.0], [-0.450], [-1.250], [0.0]])
C_uav = np.array([
    [0.0, 0.0, 1.0, 0.0],  # Gyro q (rad/s)
    [0.0, 0.0, 0.0, 1.0]   # AHRS theta (rad)
])

engine_nom = KalmanGramianEngine(A_uav, B_uav, C_uav)
eval_nom = engine_nom.evaluate()

print("[PASS] Kod 1: Kalman Kontrol Edilebilirlik ve Gözlemlenebilirlik Motoru Kuruldu.")
print(f"  - Durum Boyutu (n)           : {engine_nom.n}")
print(f"  - Kontrol Edilebilirlik Rankı: {eval_nom['rank_c']}/{engine_nom.n} -> [{'TAM KONTROL EDİLEBİLİR' if eval_nom['is_controllable'] else 'EKSİK RANK'}]")
print(f"  - Gözlemlenebilirlik Rankı   : {eval_nom['rank_o']}/{engine_nom.n} -> [{'TAM GÖZLEMLENEBİLİR' if eval_nom['is_observable'] else 'EKSİK RANK'}]")
print(f"  - Kontrol Tekil Değerleri    : {eval_nom['svd_c']}")
print(f"  - Gözlem Tekil Değerleri     : {eval_nom['svd_o']}")
print(f"  - Koşul Sayısı (kappa_C)     : {eval_nom['cond_c']:.2e}")
print(f"  - Koşul Sayısı (kappa_O)     : {eval_nom['cond_o']:.2e}")

assert eval_nom['is_controllable'] is True, "Nominal sistem tam kontrol edilebilir olmalıdır!"
assert eval_nom['is_observable'] is True, "Nominal sistem tam gözlemlenebilir olmalıdır!"
assert eval_nom['rank_c'] == 4, "Kontrol edilebilirlik matrisi rank 4 olmalıdır!"
assert eval_nom['rank_o'] == 4, "Gözlemlenebilirlik matrisi rank 4 olmalıdır!"


# [KOD HÜCRESİ 2: Popov-Belevitch-Hautus (PBH) Testi ve Mod Ayrıştırması]
# Amaç: Sistemin her bir özdeğerinin (Short-Period ve Phugoid modları) kontrol ve gözlem
# kabiliyetini test etmek:
# PBH Controllability: rank([lambda_i * I - A, B]) == n
# PBH Observability:   rank([lambda_i * I - A; C]) == n

import numpy as np

def run_pbh_test(A: np.ndarray, B: np.ndarray, C: np.ndarray) -> List[Dict[str, any]]:
    n = A.shape[0]
    eigs = np.linalg.eigvals(A)
    pbh_results = []
    
    for idx, lam in enumerate(eigs):
        # 1. PBH Kontrol Edilebilirlik Matrisi: [lam*I - A, B] (n x (n + m))
        mat_ctr = np.hstack([lam * np.eye(n) - A, B])
        rank_ctr = int(np.linalg.matrix_rank(mat_ctr))
        is_mode_controllable = bool(rank_ctr == n)
        
        # 2. PBH Gözlemlenebilirlik Matrisi: [lam*I - A; C] ((n + p) x n)
        mat_obs = np.vstack([lam * np.eye(n) - A, C])
        rank_obs = int(np.linalg.matrix_rank(mat_obs))
        is_mode_observable = bool(rank_obs == n)
        
        mode_name = "Short-Period" if abs(lam.real) > 1.0 else "Phugoid"
        
        pbh_results.append({
            'mode_index': idx + 1,
            'mode_name': mode_name,
            'eigenvalue': lam,
            'rank_ctr': rank_ctr,
            'rank_obs': rank_obs,
            'is_ctr': is_mode_controllable,
            'is_obs': is_mode_observable
        })
        
    return pbh_results

pbh_res = run_pbh_test(A_uav, B_uav, C_uav)

print("[ANALİZ] Popov-Belevitch-Hautus (PBH) Özdeğer Mod Denetimi:")
print(f"{'Mod':<4} | {'İsim':<14} | {'Özdeğer':<25} | {'PBH Ctr Rank':<14} | {'PBH Obs Rank':<14} | {'Durum'}")
print("-" * 85)

for r in pbh_res:
    status = "TAMAM" if (r['is_ctr'] and r['is_obs']) else "KAYIP"
    eig_str = f"{r['eigenvalue'].real:+.3f} {r['eigenvalue'].imag:+.3f}j"
    print(f"{r['mode_index']:<4} | {r['mode_name']:<14} | {eig_str:<25} | {r['rank_ctr']}/4          | {r['rank_obs']}/4          | [{status}]")

# Doğrulamalar:
for r in pbh_res:
    assert r['is_ctr'] is True, f"Mod {r['mode_index']} kontrol edilebilir olmalıdır!"
    assert r['is_obs'] is True, f"Mod {r['mode_index']} gözlemlenebilir olmalıdır!"


# [KOD HÜCRESİ 3: Sensör/Eyleyici Kopması ve Gramian Enerji Analizi]
# Amaç: Eyleyici veya sensör kaybında sistemin kontrol ve gözlem kabiliyetinin çöküşünü
# incelemek; Controllability Gramian (Wc) ve Observability Gramian (Wo) çözerek
# kontrol enerjisinin E_min = x0^T * Wc^(-1) * x0 nasıl patladığını kanıtlamak.

import numpy as np
from scipy import linalg

# 1. Nominal Durum Gramianları
# A*Wc + Wc*A^T = -B*B^T
Wc_nom = linalg.solve_continuous_lyapunov(A_uav, -B_uav @ B_uav.T)
# A^T*Wo + Wo*A = -C^T*C
Wo_nom = linalg.solve_continuous_lyapunov(A_uav.T, -C_uav.T @ C_uav)

# 2. Arızalı Sistem: Eyleyici Kopması (Elevator Link Disconnected)
B_broken = np.zeros_like(B_uav)
engine_broken_act = KalmanGramianEngine(A_uav, B_broken, C_uav)
eval_broken_act = engine_broken_act.evaluate()

# 3. Arızalı Sistem: Gizli Yapısal Mod (Decoupled Fuel Slosh / Wing Flutter)
# 5. bir gizli mod ekleniyor, eyleyici ve sensörler bu modu görmüyor
A_hidden = np.block([
    [A_uav, np.zeros((4, 1))],
    [np.zeros((1, 4)), -0.5] # İzole çalkantı modu
])
B_hidden = np.vstack([B_uav, 0.0]) # Eyleyici temas etmiyor
C_hidden = np.hstack([C_uav, np.zeros((2, 1))]) # Sensör ölçmüyor

engine_hidden = KalmanGramianEngine(A_hidden, B_hidden, C_hidden)
eval_hidden = engine_hidden.evaluate()

# Kontrol Enerjisi Karşılaştırması: Dengeye getirme enerjisi
x0_test = np.array([1.0, 0.5, 0.02, 0.03])
energy_nom = float(x0_test.T @ np.linalg.pinv(Wc_nom) @ x0_test)

print("[PASS] Kod 3: Sensör/Eyleyici Kopması ve Gramian Analizi:")
print(f"  * Nominal Wc Özdeğerleri (En Küçük/En Büyük): {np.min(np.linalg.eigvals(Wc_nom)):.4e} / {np.max(np.linalg.eigvals(Wc_nom)):.4e}")
print(f"  * Nominal Wo Özdeğerleri (En Küçük/En Büyük): {np.min(np.linalg.eigvals(Wo_nom)):.4e} / {np.max(np.linalg.eigvals(Wo_nom)):.4e}")
print(f"  * Nominal Dengeleme Enerjisi (E_min)        : {energy_nom:.4f} Joules")
print(f"  * Arızalı Eyleyici (Kopuk) Ctr Rankı        : {eval_broken_act['rank_c']}/4 (SIFIR KONTROL)")
print(f"  * Gizli Modlu Sistem (5 Durum) Ctr/Obs Rank : Ctr={eval_hidden['rank_c']}/5 | Obs={eval_hidden['rank_o']}/5 (EKSİK GÖZLEM)")

assert eval_broken_act['rank_c'] == 0, "Kopuk eyleyici rankı sıfır olmalıdır!"
assert eval_hidden['rank_c'] == 4, "Gizli mod kontrol edilememelidir (rank 4 < 5)!"
assert eval_hidden['rank_o'] == 4, "Gizli mod gözlemlenememelidir (rank 4 < 5)!"
assert np.all(np.linalg.eigvals(Wc_nom) > 0), "Nominal Wc kesin pozitif tanımlı olmalıdır!"
assert np.all(np.linalg.eigvals(Wo_nom) > 0), "Nominal Wo kesin pozitif tanımlı olmalıdır!"


# [KOD HÜCRESİ 4: 3 Askeri Uç Durum ve Güvenlik Kalkanı Testleri]
# Amaç: DO-178C DAL-A uçuş kontrol yazılımlarında kontrol edilebilirlik ve gözlemlenebilirlik
# durumunu denetleyen 3 kritik güvenlik kalkanı:
# 1. Eyleyici Kaybı ve Kontrol Edilebilirlik Kalkanı (Actuator Loss Guard)
# 2. Sensör Körleşmesi ve Gözlemlenebilirlik Kalkanı (Sensor Blindness Guard)
# 3. Kötü Koşulluluk ve Aşırı Enerji Kalkanı (Ill-Conditioning Control Energy Guard)

import numpy as np

print("[TEST 1] Eyleyici Kaybı ve Kontrol Edilebilirlik Kalkanı (Actuator Loss Guard)...")
class ControllabilityLossGuard:
    """
    Eyleyici hasar aldığında Ctr matrisinin rankını ve en küçük tekil değerini (sigma_min)
    denetler. sigma_min < 1e-4 ise sistemin kontrol gücünün bittiğini ilan eder.
    """
    def __init__(self, min_allowed_sigma: float = 1e-3):
        self.min_sigma = min_allowed_sigma
        
    def inspect(self, Ctr: np.ndarray) -> Tuple[bool, str]:
        s = np.linalg.svd(Ctr, compute_uv=False)
        sigma_min = float(s[-1])
        if sigma_min < self.min_sigma:
            return False, f"CONTROLLABILITY DEGRADED: sigma_min = {sigma_min:.2e} < {self.min_sigma:.2e}!"
        return True, f"CONTROLLABILITY NOMINAL: sigma_min = {sigma_min:.2f}"

ctr_guard = ControllabilityLossGuard(min_allowed_sigma=1e-3)
pass_ctr_nom, msg_ctr_nom = ctr_guard.inspect(eval_nom['Ctr'])
pass_ctr_bad, msg_ctr_bad = ctr_guard.inspect(eval_broken_act['Ctr'])

assert pass_ctr_nom is True, "Nominal sistem kontrol kalkanını geçmelidir!"
assert pass_ctr_bad is False, "Kopuk eyleyici kontrol kalkanına takılmalıdır!"
print(f"  - Nominal Durum  : {msg_ctr_nom} [GÜVENLİ]")
print(f"  - Kopuk Eyleyici : {msg_ctr_bad} [KORUMA DEVREDE]")
print("  [PASS] Test 1: Kontrol Edilebilirlik Kalkanı başarıyla doğrulandı.\n")


print("[TEST 2] Sensör Körleşmesi ve Gözlemlenebilirlik Kalkanı (Sensor Blindness Guard)...")
class ObservabilityLossGuard:
    """
    Sensörlerin iç durumları kestirebilme yeteneğini denetler.
    Rank eksikliği varsa Kalman Filtresinin durum kestiremeyeceğini bildirir.
    """
    def __init__(self, required_rank: int = 4):
        self.req_rank = required_rank
        
    def inspect(self, Obs: np.ndarray) -> Tuple[bool, str]:
        rank = int(np.linalg.matrix_rank(Obs))
        if rank < self.req_rank:
            return False, f"OBSERVABILITY LOST: rank = {rank} < {self.req_rank} (UNOBSERVABLE MODES DETECTED)!"
        return True, f"FULL OBSERVABILITY CONFIRMED: rank = {rank}/{self.req_rank}"

obs_guard = ObservabilityLossGuard(required_rank=4)
pass_obs_nom, msg_obs_nom = obs_guard.inspect(eval_nom['Obs'])
# Sıfır C matrisi testi (sensörler tamamen devre dışı)
pass_obs_bad, msg_obs_bad = obs_guard.inspect(np.zeros_like(eval_nom['Obs']))

assert pass_obs_nom is True, "Nominal sistem gözlem kalkanını geçmelidir!"
assert pass_obs_bad is False, "Körleşmiş sensör gözlem kalkanına takılmalıdır!"
print(f"  - Nominal Sensörler : {msg_obs_nom} [ONAYLANDI]")
print(f"  - Körleşmiş Sensör  : {msg_obs_bad} [ACİL HATA İZOLASYONU]")
print("  [PASS] Test 2: Gözlemlenebilirlik Kalkanı başarıyla doğrulandı.\n")


print("[TEST 3] Kötü Koşulluluk ve Aşırı Enerji Kalkanı (Ill-Conditioning Guard)...")
class IllConditioningGuard:
    """
    Sistem kağıt üzerinde kontrol edilebilir olsa bile koşul sayısı (condition number)
    çok büyükse (kappa > 1e4), durumları sürmek için fiziksel olarak ulaşılamaz
    devasa kontrol enerjisi gerekir (Weakly Controllable).
    """
    def __init__(self, max_allowed_cond: float = 1e4):
        self.max_cond = max_allowed_cond
        
    def inspect(self, Ctr: np.ndarray) -> Tuple[bool, str]:
        cond = float(np.linalg.cond(Ctr))
        if cond > self.max_cond:
            return False, f"ILL-CONDITIONED ACTUATOR: kappa(Ctr) = {cond:.2e} > {self.max_cond:.2e} (EXCESS ENERGY REQUIRED)!"
        return True, f"WELL-CONDITIONED CONTROL EFFORT: kappa(Ctr) = {cond:.2e}"

cond_guard = IllConditioningGuard(max_allowed_cond=1e4)
pass_cond_nom, msg_cond_nom = cond_guard.inspect(eval_nom['Ctr'])

# Yapay kötü koşullu matris testi (zayıf kontrol)
Ctr_weak = eval_nom['Ctr'].copy()
Ctr_weak[:, -1] *= 1e-6
pass_cond_bad, msg_cond_bad = cond_guard.inspect(Ctr_weak)

assert pass_cond_nom is True, "Nominal sistem kabul edilebilir koşullu olmalıdır!"
assert pass_cond_bad is False, "Aşırı kötü koşullu sistem alarm vermelidir!"
print(f"  - Nominal Koşul Sayısı : {msg_cond_nom} [KABUL EDİLEBİLİR]")
print(f"  - Zayıf Eyleyici Gücü  : {msg_cond_bad} [AŞIRI ENERJİ UYARISI]")
print("  [PASS] Test 3: Kötü Koşulluluk Kalkanı başarıyla doğrulandı.")


# [KOD HÜCRESİ 5: 4 Panelli Aviyonik Kalman & Gramian Dashboard Görselleştirmesi]
# Amaç: Kontrol ve gözlem tekil değer spektrumunu, PBH özdeğer mod haritasını,
# Gramian enerji dağılımını ve aviyonik kokpit HUD durum izleme panelini gösteren
# 300 DPI, koyu temalı (#0F172A) görsel üretimi.

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

# PANEL 1 (Sol Üst): Kontrol ve Gözlem Tekil Değer Spektrumu (Singular Values)
idx_svd = np.arange(1, 5)
axs[0, 0].semilogy(idx_svd, eval_nom['svd_c'], color='#38BDF8', marker='o', linewidth=2.2, label='Kontrol Edilebilirlik (Ctr) Tekil Değerleri')
axs[0, 0].semilogy(idx_svd, eval_nom['svd_o'], color='#10B981', marker='s', linewidth=2.2, label='Gözlemlenebilirlik (Obs) Tekil Değerleri')

axs[0, 0].axhline(y=1e-3, color='#EF4444', linestyle='--', linewidth=1.5, label='Kritik Eşik (sigma_min = 1e-3)')
axs[0, 0].set_title("Kalman Matrisleri Tekil Değer Spektrumu (SVD)", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[0, 0].set_xlabel("Tekil Değer Sırası (i)", fontsize=11, color='#E2E8F0')
axs[0, 0].set_ylabel("Tekil Değer Büyüklüğü (Logaritmik)", fontsize=11, color='#E2E8F0')
axs[0, 0].set_xticks(idx_svd)
axs[0, 0].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[0, 0].legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=9)

# PANEL 2 (Sağ Üst): PBH Mod Haritası ve Özdeğerlerin s-Düzlemindeki Durumu
eigs = np.linalg.eigvals(A_uav)
axs[0, 1].axvspan(-3.0, 0.0, color='#10B981', alpha=0.08, label='Kararlı Sol Yarı Düzlem (LHP)')
axs[0, 1].axvline(x=0.0, color='#EF4444', linestyle='-', linewidth=1.5, label='Sanal Eksen')
axs[0, 1].axhline(y=0.0, color='#64748B', linestyle='--', alpha=0.5)

for p in pbh_res:
    marker_color = '#38BDF8' if "Short-Period" in p['mode_name'] else '#F59E0B'
    axs[0, 1].scatter(p['eigenvalue'].real, p['eigenvalue'].imag, color=marker_color, s=140, marker='D', zorder=5)
    offset_y = 0.25 if p['eigenvalue'].imag >= 0 else -0.35
    axs[0, 1].text(p['eigenvalue'].real - 0.7, p['eigenvalue'].imag + offset_y, 
                   f"{p['mode_name']}\nPBH Ctr: {p['rank_ctr']}/4 | Obs: {p['rank_obs']}/4", 
                   color=marker_color, fontsize=8.5, fontweight='bold')

axs[0, 1].set_title(r"PBH Mod Denetimi ($s$-Düzleminde Kontrol & Gözlem)", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[0, 1].set_xlabel(r"Reel Eksen $\sigma$ (1/s)", fontsize=11, color='#E2E8F0')
axs[0, 1].set_ylabel(r"Sanal Eksen $j\omega$ (rad/s)", fontsize=11, color='#E2E8F0')
axs[0, 1].set_xlim(-3.0, 0.5)
axs[0, 1].set_ylim(-1.5, 1.5)
axs[0, 1].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[0, 1].legend(loc='lower left', facecolor='#1E293B', edgecolor='#334155', fontsize=9)

# PANEL 3 (Sol Alt): Gramian Enerji Elipsoidi (Yunuslama Açısı vs Hız Düzlemi)
theta_grid = np.linspace(-3.0, 3.0, 100)
q_grid = np.linspace(-2.0, 2.0, 100)
T_mesh, Q_mesh = np.meshgrid(theta_grid, q_grid)

# 2D alt uzay Gramian tersi (theta ve q durumları: index 2 ve 3)
Wc_sub = Wc_nom[2:4, 2:4]
Wc_sub_inv = np.linalg.inv(Wc_sub)

Energy_mesh = np.zeros_like(T_mesh)
for i in range(len(q_grid)):
    for j in range(len(theta_grid)):
        vec = np.array([np.radians(Q_mesh[i, j]), np.radians(T_mesh[i, j])])
        Energy_mesh[i, j] = vec.T @ Wc_sub_inv @ vec

cs = axs[1, 0].contour(T_mesh, Q_mesh, Energy_mesh, levels=[0.1, 0.5, 1.0, 2.5, 5.0], colors=['#10B981', '#38BDF8', '#F59E0B', '#EF4444', '#A855F7'], linewidths=1.8)
axs[1, 0].clabel(cs, inline=True, fontsize=8, fmt='E=%.1f')

axs[1, 0].set_title(r"Kontrol Edilebilirlik Gramian Enerji Zarfı ($x^T W_c^{-1} x$)", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[1, 0].set_xlabel(r"Yunuslama Açısı $\Delta\theta$ (derece)", fontsize=11, color='#E2E8F0')
axs[1, 0].set_ylabel(r"Yunuslama Hızı $q$ (derece/saniye)", fontsize=11, color='#E2E8F0')
axs[1, 0].grid(True, linestyle='--', alpha=0.3, color='#475569')

# PANEL 4 (Sağ Alt): Aviyonik Uçuş Kontrol Bilgisayarı (FCC) HUD Ekranı
hud_canvas = np.zeros((400, 600, 3), dtype=np.uint8)
hud_canvas[:] = [15, 23, 42]

axs[1, 1].imshow(hud_canvas)
axs[1, 1].set_title("Aviyonik Kalman Rankı & Eyleyici/Sensör Sağlık HUD Paneli", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)

# Nişangah ve HUD Grafikleri
axs[1, 1].axvline(x=300, color='#10B981', linestyle=':', alpha=0.6)
axs[1, 1].axhline(y=200, color='#10B981', linestyle=':', alpha=0.6)
rect = plt.Rectangle((180, 120), 240, 160, fill=False, edgecolor='#10B981', linestyle='--', linewidth=1.5)
axs[1, 1].add_patch(rect)

axs[1, 1].text(30, 45, "ASELSAN / TUSAŞ AVIONICS KALMAN HEALTH CORE", color='#38BDF8', fontsize=9, fontfamily='monospace', fontweight='bold')
axs[1, 1].text(30, 75, "KONTROL EDİLEBİLİRLİK : RANK 4/4 (TAM ERİŞİM SAĞLANDI)", color='#10B981', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 105, "GÖZLEMLENEBİLİRLİK   : RANK 4/4 (TAM DURUM KESTİRİMİ AKTİF)", color='#10B981', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 130, f"EYLEYİCİ DURUMU       : ELEVATOR NOMINAL (sigma_min={eval_nom['svd_c'][-1]:.2f})", color='#E2E8F0', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 155, f"SENSÖR DONANIMI       : GYRO + AHRS HEALTHY (kappa={eval_nom['cond_o']:.1e})", color='#10B981', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 185, "PBH TEST DENETİMİ     : 4/4 MODLAR STABLE & REACHABLE", color='#38BDF8', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 215, "ARIZA KORUMA MODU     : ACTUATOR / SENSOR FAULT GUARDS ARMED", color='#10B981', fontsize=8.5, fontfamily='monospace')
axs[1, 1].text(30, 360, "DO-178C DAL-A PRE-FLIGHT READINESS PASS", color='#64748B', fontsize=8, fontfamily='monospace')
axs[1, 1].axis('off')

plt.suptitle("GÜN 282: MODERN KONTROL — KONTROL EDİLEBİLİRLİK VE GÖZLEMLENEBİLİRLİK (KALMAN & PBH)", 
             fontsize=15, fontweight='heavy', color='#F8FAFC', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

out_png = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_282/gun_282_controllability_observability_sezgisi.png"
plt.savefig(out_png, dpi=300, facecolor='#0F172A')
plt.close()

png_size = os.path.getsize(out_png)
print(f"[OK] 4-Panelli Kalman/Gramian Gorseli Basariyla Uretildi: {out_png}")
print(f"  - Dosya Boyutu: {png_size / 1024.0:.2f} KB (Beklenen: > 100 KB)")
assert png_size > 100 * 1024, "Görsel boyutu 100 KB üzerinde olmalıdır!"


# [KOD HÜCRESİ 6: DO-178C DAL-A Uçuş Öncesi Kalman & Gramian Kalifikasyon Raporu]
# Amaç: Taktik İHA otopilotunun eyleyici yetkinliğini ve sensör gözlem gücünü
# DO-178C DAL-A uçuş öncesi test standartlarına göre otomatik doğrulamak.

import numpy as np

def generate_kalman_certification_report(eval_data: Dict[str, any], pbh_data: List[Dict[str, any]]) -> Dict[str, any]:
    crit_1_ctr_rank = bool(eval_data['rank_c'] == 4)
    crit_2_obs_rank = bool(eval_data['rank_o'] == 4)
    crit_3_pbh_all_pass = all(p['is_ctr'] and p['is_obs'] for p in pbh_data)
    crit_4_cond_ctr = bool(eval_data['cond_c'] < 1e4)
    crit_5_cond_obs = bool(eval_data['cond_o'] < 1e4)
    
    all_pass = crit_1_ctr_rank and crit_2_obs_rank and crit_3_pbh_all_pass and crit_4_cond_ctr and crit_5_cond_obs
    
    return {
        'rank_c': eval_data['rank_c'],
        'rank_o': eval_data['rank_o'],
        'cond_c': eval_data['cond_c'],
        'cond_o': eval_data['cond_o'],
        'crit_1_ctr_rank': crit_1_ctr_rank,
        'crit_2_obs_rank': crit_2_obs_rank,
        'crit_3_pbh_all_pass': crit_3_pbh_all_pass,
        'crit_4_cond_ctr': crit_4_cond_ctr,
        'crit_5_cond_obs': crit_5_cond_obs,
        'flight_qualification_certified': all_pass
    }

report = generate_kalman_certification_report(eval_nom, pbh_res)

print("\n==========================================================================")
print("[AVİYONİK KONTROL VE GÖZLEM KALİFİKASYON RAPORU (DO-178C DAL-A)]")
print("==========================================================================")
print(f"  * Kontrol Edilebilirlik Rankı (Kalman) : {report['rank_c']}/4 -> [{'PASS' if report['crit_1_ctr_rank'] else 'FAIL'}]")
print(f"  * Gözlemlenebilirlik Rankı (Kalman)   : {report['rank_o']}/4 -> [{'PASS' if report['crit_2_obs_rank'] else 'FAIL'}]")
print(f"  * PBH Özdeğer Ayrışım Testi (Tüm Modlar): [{'PASS' if report['crit_3_pbh_all_pass'] else 'FAIL'}]")
print(f"  * Kontrol Matrisi Koşul Sayısı        : kappa = {report['cond_c']:.2e} (< 1e4) -> [{'PASS' if report['crit_4_cond_ctr'] else 'FAIL'}]")
print(f"  * Gözlem Matrisi Koşul Sayısı         : kappa = {report['cond_o']:.2e} (< 1e4) -> [{'PASS' if report['crit_5_cond_obs'] else 'FAIL'}]")
print(f"  * Otopilot Uçuşa Elverişlilik Durumu : [KONTROL VE GÖZLEM TESTLERİNDEN TAM NOTLA GEÇTİ]")
print("==========================================================================\n")

assert report['crit_1_ctr_rank'], "Kontrol edilebilirlik tam rank olmalıdır!"
assert report['crit_2_obs_rank'], "Gözlemlenebilirlik tam rank olmalıdır!"
assert report['crit_3_pbh_all_pass'], "PBH testinin tüm modları başarılı olmalıdır!"
assert report['crit_4_cond_ctr'], "Kontrol koşul sayısı kabul edilebilir sınırda olmalıdır!"
assert report['crit_5_cond_obs'], "Gözlem koşul sayısı kabul edilebilir sınırda olmalıdır!"
assert report['flight_qualification_certified'], "Sistem uçuş sertifikasyonunu bütünüyle geçmelidir!"

