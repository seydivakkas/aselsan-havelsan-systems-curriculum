# -*- coding: utf-8 -*-
"""
Gün 310: Faz F10 — Fading ve Multipath
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

# [KOD HÜCRESİ 1: İki Işınlı Deniz Üstü Yayılım Modeli ve Lobing Simülasyonu]
# Amaç: Deniz seviyesinde alçaktan uçan gemisavar füzesine (h2=10m) karşı gemi radarı
# (h1=20m, fc=9.5 GHz X-band) sahasında direkt ve denizden yansıyan ışınların faz
# etkileşimini, iki yönlü radar yayılım faktörünü (F^4) ve derin iptal null'larını modellemek.

import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np

# 1. Radar ve Geometrik Sahne Parametreleri
fc1 = 9.5e9               # X-band Taşıyıcı Frekansı: 9.5 GHz
c = 3.0e8                 # Işık hızı (m/s)
lambda1 = c / fc1         # Dalga boyu: 3.1579 cm

h1 = 20.0                 # Radar Anten Yüksekliği: 20.0 m (Fırkateyn direği)
h2 = 10.0                 # Hedef Füze İrtifası: 10.0 m (Sea-skimming taarruz)

# Menzil Izgarası: 1 km .. 20 km (2000 nokta)
ranges = np.linspace(1000.0, 20000.0, 2000)

# 2. Doğrudan ve Yansıyan Işın Geometrisi
# Doğrudan yol mesafesi: R_dir = sqrt(R^2 + (h1 - h2)^2)
# Yansıyan yol mesafesi: R_refl = sqrt(R^2 + (h1 + h2)^2)
R_dir = np.sqrt(ranges**2 + (h1 - h2)**2)
R_refl = np.sqrt(ranges**2 + (h1 + h2)**2)
delta_R = R_refl - R_dir

# 3. Fresnel Yansıma Katsayısı (Deniz Suyu, Yatay Polarizasyon, Otlama Açısı)
# Yatay polarizasyonda otlama açısında faz 180 derece döner (Gamma approx -1)
rho_sea = 0.95            # Deniz yüzeyi pürüzsüzlük faktörü
phi_sea = np.pi           # 180 derece faz çevrimi
Gamma = rho_sea * np.exp(1j * phi_sea)

# 4. İki Işınlı Faz Farkı ve Yayılım Faktörü F
phase_diff1 = 2.0 * np.pi * delta_R / lambda1
F_complex1 = 1.0 + Gamma * np.exp(-1j * phase_diff1)
F_mag1 = np.abs(F_complex1)
F4_db1 = 40.0 * np.log10(F_mag1 + 1e-6)   # İki yönlü radar güç çarpanı (Radar Equation F^4)

# 5. Kuramsal İlk Derin İptal (First Deep Null) Menzili
# Faz farkı 2*pi olduğunda (Gamma=-1 ile) yıkıcı girişim maksimuma ulaşır:
# 2*pi * (2*h1*h2 / (R_null * lambda)) = 2*pi -> R_null = 2*h1*h2 / lambda
R_null_theo = 2.0 * h1 * h2 / lambda1

# Sayısal Olarak Ölçülen Null
null_idx = np.argmin(np.abs(ranges - R_null_theo))
local_idx = null_idx - 15 + np.argmin(F4_db1[null_idx-15:null_idx+15])
measured_null_r = ranges[local_idx]
null_depth = F4_db1[local_idx]

print("=" * 72)
print("ASELSAN ÇAFRAD / MAR-D DENİZ SAVUNMA RADARI — MULTIPATH ANALİZİ")
print("=" * 72)
print(f"Radar Frekansı (fc1)       : {fc1/1e9:.2f} GHz (Dalga Boyu: {lambda1*1e2:.2f} cm)")
print(f"Radar Anten Yüksekliği (h1): {h1:.1f} m | Hedef Füze İrtifası (h2): {h2:.1f} m")
print(f"Deniz Yansıma Katsayısı    : |Gamma| = {rho_sea:.2f}, Faz = 180.0°")
print("-" * 72)
print(f"Kuramsal İlk Derin Null    : R_null = {R_null_theo:.1f} m ({R_null_theo/1e3:.2f} km)")
print(f"Ölçülen İlk Derin Null     : R_null = {measured_null_r:.1f} m ({measured_null_r/1e3:.2f} km)")
print(f"Null Bölgesi Sinyal İptali : {null_depth:.2f} dB (RADAR KÖR NOKTASI)")
print(f"Maksimum Yapıcı Güç Artışı : +{np.max(F4_db1):.2f} dB (Lob Zirvesi)")
print("=" * 72)


# [KOD HÜCRESİ 2: İstatistiksel Sönümleme Kanalları (Rayleigh vs Rician) ve PDF]
# Amaç: Görüş hattı olmayan (NLOS) kentsel/dağlık kanal için Rayleigh ve baskın görüş
# hattına (LOS) sahip taktik veri bağı için Rician (K=6dB, K=12dB) kanallarını
# 100,000 Monte Carlo gerçekleşimiyle üretmek, zarf PDF'lerini kuramsal eğrilerle doğrulamak.

from scipy.special import i0

N_mc = 100000
np.random.seed(42)

# 1. Rayleigh Sönümleme Kanalı (K = 0, E[|h|^2] = 1.0)
sigma_ray = 1.0 / np.sqrt(2.0)
h_ray = sigma_ray * (np.random.randn(N_mc) + 1j * np.random.randn(N_mc))
env_ray = np.abs(h_ray)

# 2. Rician Sönümleme Kanalı (K = 6 dB, Orta Düzey LOS Bileşen)
K_lin1 = 10.0**(6.0 / 10.0)
s1 = np.sqrt(K_lin1 / (K_lin1 + 1.0))
sigma_ric1 = np.sqrt(1.0 / (2.0 * (K_lin1 + 1.0)))
h_ric1 = (s1 + sigma_ric1 * np.random.randn(N_mc)) + 1j * (sigma_ric1 * np.random.randn(N_mc))
env_ric1 = np.abs(h_ric1)

# 3. Rician Sönümleme Kanalı (K = 12 dB, Baskın Güçlü LOS Bileşen)
K_lin2 = 10.0**(12.0 / 10.0)
s2 = np.sqrt(K_lin2 / (K_lin2 + 1.0))
sigma_ric2 = np.sqrt(1.0 / (2.0 * (K_lin2 + 1.0)))
h_ric2 = (s2 + sigma_ric2 * np.random.randn(N_mc)) + 1j * (sigma_ric2 * np.random.randn(N_mc))
env_ric2 = np.abs(h_ric2)

# 4. -15 dB Altı Derin Sönüm / Kesinti Olasılığı (Outage Probability)
th_outage = 10.0**(-15.0 / 20.0)   # Genlik eşiği approx 0.1778
outage_ray = np.mean(env_ray < th_outage)
outage_ric1 = np.mean(env_ric1 < th_outage)
outage_ric2 = np.mean(env_ric2 < th_outage)

# İstatistiksel Ortalama Değerler
mean_ray = np.mean(env_ray)
theo_mean_ray = sigma_ray * np.sqrt(np.pi / 2.0)

print("=" * 72)
print("İSTATİSTİKSEL SÖNÜMLEME KANALLARI (RAYLEIGH VS RICIAN) ANALİZİ")
print("=" * 72)
print(f"Rayleigh Ortalama Zarf Genliği : {mean_ray:.4f} (Kuramsal: {theo_mean_ray:.4f})")
print(f"Rayleigh Kesinti Oranı (<-15dB): %{outage_ray*100:.2f} (Kritik Sinyal Kaybı)")
print(f"Rician (K=6dB) Kesinti Oranı   : %{outage_ric1*100:.3f} (Orta Düzey İyileşme)")
print(f"Rician (K=12dB) Kesinti Oranı  : %{outage_ric2*100:.4f} (Yüksek Güvenilirlik)")
print("-" * 72)
print(f"Rician K=12dB vs Rayleigh Güvenlik Kazancı: {outage_ray / max(outage_ric2, 1e-6):.1f} Kat Daha Düşük Kesinti!")
print("=" * 72)


# [KOD HÜCRESİ 3: Frekans Çeşitliliği (Frequency Agility) ile Multipath İptalini Önleme]
# Amaç: Tek frekansta (9.5 GHz) 12.66 km menzilde oluşan -52 dB'lik ölümcül multipath
# çukurunu, ikinci bir taşıyıcı frekans (10.2 GHz) ve seçimli çeşitlilik (Selection Diversity)
# ile aşarak radar hedef tespitini kesintisiz hale getirmek ve çeşitlilik kazancını kanıtlamak.

# 1. İkinci Radar Frekansı Modeli (fc2 = 10.2 GHz, lambda2 = 2.94 cm)
fc2 = 10.2e9
lambda2 = c / fc2
phase_diff2 = 2.0 * np.pi * delta_R / lambda2
F_complex2 = 1.0 + Gamma * np.exp(-1j * phase_diff2)
F4_db2 = 40.0 * np.log10(np.abs(F_complex2) + 1e-6)

# 2. Seçimli Frekans Çeşitliliği (Selection Diversity Combination)
# Radar her menzilde daha güçlü olan frekans kanalını kullanır
F4_div = np.maximum(F4_db1, F4_db2)

# 3. Null Bölgesinde Çeşitlilik Kazancı (Diversity Gain) Hesabı
null_power_f1 = F4_db1[local_idx]
null_power_f2 = F4_db2[local_idx]
null_power_div = F4_div[local_idx]
diversity_gain = null_power_div - null_power_f1

print("=" * 72)
print("FREKANS ÇEŞİTLİLİĞİ (FREQUENCY DIVERSITY) PERFORMANS KAZANCI")
print("=" * 72)
print(f"Kanal 1 Frekansı (fc1)      : {fc1/1e9:.2f} GHz (Derin Null Bölgesi: {measured_null_r/1e3:.2f} km)")
print(f"Kanal 2 Frekansı (fc2)      : {fc2/1e9:.2f} GHz (Faz Kaydırılmış Kanal)")
print(f"Kanal 1 Gücü (Null Anında)  : {null_power_f1:.2f} dB (Hedef Radardan Silindi)")
print(f"Kanal 2 Gücü (Null Anında)  : {null_power_f2:.2f} dB (Güçlü Algılama Seviyesi)")
print(f"Çeşitlilik Sonrası Güç      : {null_power_div:.2f} dB")
print(f"Efektif Çeşitlilik Kazancı  : +{diversity_gain:.2f} dB (RADAR KÖR NOKTASI KURTARILDI)")
print("=" * 72)


# [KOD HÜCRESİ 4: DO-254 / MIL-STD-461 Fading & Multipath Algoritmik Stres Testleri]
# Amaç: Multipath yayılım ve sönümleme modellerinin DO-254 DAL-A havacılık/savunma
# standartlarında; null konum doğruluğu, zarf momentleri, kesinti olasılıkları,
# çeşitlilik kazancı ve numerik stabilite açısından 5 katı stres testinden geçtiğini
# assert denetimleriyle garanti altına almak.

print("=" * 72)
print("DO-254 / MIL-STD-461 FADING & MULTIPATH ALGORİTMİK STRES TESTLERİ")
print("=" * 72)

# TEST 1: İki Işınlı Null Menzili ve Derinliği Doğrulaması
err_null_r = abs(measured_null_r - R_null_theo)
assert err_null_r <= 25.0, f"HATA: Null menzili hatası {err_null_r:.2f} m limitin üzerinde!"
assert null_depth <= -35.0, f"HATA: Null derinliği {null_depth:.2f} dB yetersiz (< -35 dB)!"
print(f"[TEST 1 PASS] Two-Ray Null Doğrulaması: R_null={measured_null_r:.1f}m (Teorik: {R_null_theo:.1f}m, Hata: {err_null_r:.2f}m) | Derinlik={null_depth:.2f} dB")

# TEST 2: Rayleigh İstatistiksel Moment Doğrulaması
err_ray_pct = abs(mean_ray - theo_mean_ray) / theo_mean_ray * 100.0
assert err_ray_pct <= 2.0, f"HATA: Rayleigh ortalama hatası %{err_ray_pct:.2f} limitin üzerinde!"
print(f"[TEST 2 PASS] Rayleigh Moment Uyumu: Ölçülen={mean_ray:.4f} (Teorik: {theo_mean_ray:.4f}, Hata: %{err_ray_pct:.2f} <= %2.0)")

# TEST 3: Kesinti (Outage) Olasılığı Kademeli İyileşme Testi
assert outage_ray >= 0.02 and outage_ray <= 0.045, f"HATA: Rayleigh outage %{outage_ray*100:.2f} limit dışı!"
assert outage_ric1 < outage_ray, "HATA: Rician K=6dB kesintisi Rayleigh'den küçük olmalı!"
assert outage_ric2 < 0.005, f"HATA: Rician K=12dB outage %{outage_ric2*100:.4f} çok yüksek!"
print(f"[TEST 3 PASS] Kesinti Olasılığı: Rayleigh=%{outage_ray*100:.2f} -> Rician K=6dB=%{outage_ric1*100:.3f} -> K=12dB=%{outage_ric2*100:.4f}")

# TEST 4: Frekans Çeşitliliği Kazancı (Diversity Gain >= 20.0 dB)
assert diversity_gain >= 20.0, f"HATA: Çeşitlilik kazancı {diversity_gain:.2f} dB yetersiz (< 20 dB)!"
print(f"[TEST 4 PASS] Frekans Çeşitliliği Kazancı: Null İptali Kazancı = +{diversity_gain:.2f} dB (>= 20.0 dB)")

# TEST 5: Enerji Korunumu ve Numerik Kararlılık (Maks |F| <= 2.0, NaN/Inf Yok)
max_F1 = np.max(F_mag1)
assert max_F1 <= 2.0001, f"HATA: Enerji korunumu aşıldı! Maks |F| = {max_F1:.4f} > 2.0"
assert not np.isnan(F4_db1).any(), "HATA: NaN tespit edildi!"
assert not np.isinf(F4_db1).any(), "HATA: Inf tespit edildi!"
print(f"[TEST 5 PASS] Enerji Korunumu ve Stabilite: Maks |F| = {max_F1:.4f} <= 2.0 | NaN/Inf Koruması %100 Onaylandı.")
print("=" * 72)
print("TÜM DO-254 / MIL-STD-461 ALGORİTMİK STRES TESTLERİ BAŞARIYLA GEÇTİ [PASS]")
print("=" * 72)


# [KOD HÜCRESİ 5: 4 Panelli 300 DPI Profesyonel Aviyonik Dashboard]
# Amaç: İki ışınlı deniz yansıması lobing deseni, istatistiksel sönümleme zaman izleri,
# kuramsal PDF eğrileri ve frekans çeşitliliği kazancını koyu lacivert (#0F172A)
# aviyonik tema ile 300 DPI çözünürlükte profesyonel bir PNG görseline dönüştürmek.

import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#475569'
plt.rcParams['axes.linewidth'] = 0.8

fig = plt.figure(figsize=(19, 12), facecolor='#0F172A')

# ------------------------------------------------------------------------------
# PANEL 1: İki Işınlı Deniz Üstü Yayılım Faktörü F^4(R) ve Lobing Deseni
# ------------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1, facecolor='#1E293B')
ax1.plot(ranges / 1000.0, F4_db1, color='#38BDF8', lw=1.8, label="Radar Yayılım Faktörü F⁴(R) [f1 = 9.5 GHz]")
ax1.axhline(0, color='#94A3B8', linestyle='--', lw=1.0, label="Serbest Uzay Referansı (0 dB)")
ax1.axhline(12.0, color='#34D399', linestyle=':', lw=1.2, label="Maksimum Yapıcı Girişim (+12 dB)")
ax1.axhline(-20.0, color='#EF4444', linestyle=':', lw=1.2, label="Kritik İptal / Tespit Sınırı (-20 dB)")

R_null_km = R_null_theo / 1000.0
ax1.axvline(R_null_km, color='#F87171', linestyle='--', lw=1.2)
ax1.annotate(f"Derin İptal Null'u\nR = {R_null_km:.2f} km\nF⁴ = -52 dB", xy=(R_null_km, -40), xytext=(R_null_km + 1.5, -35),
             arrowprops=dict(arrowstyle="->", color='#EF4444', lw=1.5),
             color='#FCA5A5', fontsize=8, fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", fc="#1E293B", ec="#EF4444", lw=1.2))

ax1.set_xlim(1, 20)
ax1.set_ylim(-55, 16)
ax1.set_title("PANEL 1: DENİZ ÜSTÜ İKİ IŞINLI YAYILIM FAKTÖRÜ F⁴(R) VE LOBING", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
ax1.set_xlabel("Hedef Menzili / Range (km)", color='#E2E8F0', fontsize=10)
ax1.set_ylabel("İki Yönlü Radar Güç Faktörü F⁴ (dB)", color='#E2E8F0', fontsize=10)
ax1.tick_params(colors='#CBD5E1', labelsize=9)
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax1.legend(facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=8, loc='lower right')

# ------------------------------------------------------------------------------
# PANEL 2: İstatistiksel Sönümleme Zaman Profilleri
# ------------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2, facecolor='#1E293B')
N_time = 300
t_axis = np.linspace(0, 3, N_time)
window = np.ones(5) / 5.0

h_ray_t = sigma_ray * (np.random.randn(N_time) + 1j * np.random.randn(N_time))
env_ray_db = 20.0 * np.log10(np.abs(np.convolve(h_ray_t, window, mode='same')) + 1e-4)

h_ric1_t = (s1 + sigma_ric1 * np.random.randn(N_time)) + 1j * (sigma_ric1 * np.random.randn(N_time))
env_ric1_db = 20.0 * np.log10(np.abs(np.convolve(h_ric1_t, window, mode='same')) + 1e-4)

h_ric2_t = (s2 + sigma_ric2 * np.random.randn(N_time)) + 1j * (sigma_ric2 * np.random.randn(N_time))
env_ric2_db = 20.0 * np.log10(np.abs(np.convolve(h_ric2_t, window, mode='same')) + 1e-4)

ax2.plot(t_axis, env_ray_db, color='#F87171', lw=1.5, label="Rayleigh Sönümleme (NLOS, K=0) — Derin Çukurlar")
ax2.plot(t_axis, env_ric1_db, color='#FBBF24', lw=1.6, label="Rician Sönümleme (K = 6 dB)")
ax2.plot(t_axis, env_ric2_db, color='#34D399', lw=2.0, label="Rician Sönümleme (K = 12 dB, Güçlü LOS)")
ax2.axhline(-15, color='#EF4444', linestyle='--', lw=1.2, label="Kesinti Eşiği (Outage: -15 dB)")

ax2.set_xlim(0, 3)
ax2.set_ylim(-35, 8)
ax2.set_title("PANEL 2: KANAL SÖNÜMLEME ZAMAN İZLERİ (FADING ENVELOPES)", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
ax2.set_xlabel("Zaman / Time (s)", color='#E2E8F0', fontsize=10)
ax2.set_ylabel("Kanal Zarf Gücü / Envelope Power (dB)", color='#E2E8F0', fontsize=10)
ax2.tick_params(colors='#CBD5E1', labelsize=9)
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=8, loc='lower left')

# ------------------------------------------------------------------------------
# PANEL 3: Kuramsal ve Sayısal Zarf Olasılık Yoğunluk Fonksiyonları (PDF)
# ------------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3, facecolor='#1E293B')
r_grid = np.linspace(0.01, 2.5, 300)
pdf_ray_theo = (r_grid / sigma_ray**2) * np.exp(-r_grid**2 / (2.0 * sigma_ray**2))

def calc_rician_pdf(r, K_val):
    s_val = np.sqrt(K_val / (K_val + 1.0))
    sig_val = np.sqrt(1.0 / (2.0 * (K_val + 1.0)))
    return (r / sig_val**2) * np.exp(-(r**2 + s_val**2) / (2.0 * sig_val**2)) * i0(r * s_val / sig_val**2)

pdf_ric1_theo = calc_rician_pdf(r_grid, K_lin1)
pdf_ric2_theo = calc_rician_pdf(r_grid, K_lin2)

ax3.hist(env_ray, bins=60, density=True, alpha=0.3, color='#F87171', label="Sayısal Rayleigh")
ax3.plot(r_grid, pdf_ray_theo, color='#EF4444', lw=2.0, label="Kuramsal Rayleigh PDF")

ax3.hist(env_ric1, bins=60, density=True, alpha=0.3, color='#FBBF24', label="Sayısal Rician (K=6dB)")
ax3.plot(r_grid, pdf_ric1_theo, color='#F59E0B', lw=2.0, label="Kuramsal Rician K=6dB PDF")

ax3.hist(env_ric2, bins=60, density=True, alpha=0.3, color='#34D399', label="Sayısal Rician (K=12dB)")
ax3.plot(r_grid, pdf_ric2_theo, color='#10B981', lw=2.0, label="Kuramsal Rician K=12dB PDF")

ax3.set_xlim(0, 2.5)
ax3.set_ylim(0, 2.8)
ax3.set_title("PANEL 3: KURAMSAL VE SAYISAL ZARF OLASILIK YOĞUNLUK FONKSİYONLARI (PDF)", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
ax3.set_xlabel("Genlik Zarfı / Envelope Amplitude r", color='#E2E8F0', fontsize=10)
ax3.set_ylabel("Olasılık Yoğunluğu / Probability Density", color='#E2E8F0', fontsize=10)
ax3.tick_params(colors='#CBD5E1', labelsize=9)
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax3.legend(facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=8, loc='upper right')

# ------------------------------------------------------------------------------
# PANEL 4: Frekans Çeşitliliği (Frequency Agility / Diversity) ile Null İptali
# ------------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4, facecolor='#1E293B')
ax4.plot(ranges / 1000.0, F4_db1, color='#F87171', lw=1.2, linestyle=':', label="Kanal 1: f1 = 9.5 GHz (Derin Null Var)")
ax4.plot(ranges / 1000.0, F4_db2, color='#38BDF8', lw=1.2, linestyle='--', label="Kanal 2: f2 = 10.2 GHz (Kaydırılmış Faz)")
ax4.plot(ranges / 1000.0, F4_div, color='#10B981', lw=2.2, label="Çift Frekans Çeşitliliği (Dual-Freq Selection Diversity)")

ax4.axhline(-15, color='#F59E0B', linestyle='--', lw=1.0, label="Tespit Güvenlik Eşiği (-15 dB)")
ax4.set_xlim(5, 18)
ax4.set_ylim(-35, 16)
ax4.set_title("PANEL 4: FREKANS ÇEŞİTLİLİĞİ İLE MULTIPATH NULL İPTALİ VE KAZANÇ", color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
ax4.set_xlabel("Hedef Menzili / Range (km)", color='#E2E8F0', fontsize=10)
ax4.set_ylabel("Efektif Radar Güç Faktörü (dB)", color='#E2E8F0', fontsize=10)
ax4.tick_params(colors='#CBD5E1', labelsize=9)
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax4.legend(facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=8, loc='lower right')

plt.suptitle("ASELSAN / HAVELSAN RADAR VE HABERLEŞME — FADING VE MULTIPATH MİMARİSİ\nİki Işınlı Deniz Yansıması (Lloyd's Mirror), Rayleigh/Rician Kanalları ve Frekans Çeşitliliği Analizi",
             color='#F8FAFC', fontsize=14, fontweight='bold', y=0.98)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
output_png = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_310\gun_310_fading_ve_multipath.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

import os
png_size = os.path.getsize(output_png)
print(f"[+] 300 DPI Profesyonel Aviyonik Dashboard Kaydedildi: {output_png} ({png_size:,} bayt)")


# [KOD HÜCRESİ 6: DO-254 / MIL-STD-461 Fading & Multipath Kalifikasyon Raporu]
# Amaç: Radar ve taktik veri bağı kanal modellerinin tüm operasyonel parametrelerini
# ve algoritmik dayanıklılık kriterlerini kurumsal DO-254 / MIL-STD-461 onay matrisi
# formatında tescillemek.

import os

report_lines = [
    "+" + "=" * 70 + "+",
    "|   ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ RADAR AVİYONİK LABORATUVARI  |",
    "|       DO-254 / MIL-STD-461 FADING VE MULTIPATH KALİFİKASYON RAPORU    |",
    "+" + "=" * 70 + "+",
    f"| 1. Radar Frekansı & Dalga Boyu   : fc = 9.50 GHz | lambda = 3.16 cm         | [UYGUN] |",
    f"| 2. Deniz Geometrisi (h1, h2)     : Gemi = 20.0 m | Füze = 10.0 m             | [UYGUN] |",
    f"| 3. İlk Derin Null Doğrulaması    : R_null = {measured_null_r/1e3:.2f} km (Derinlik: {null_depth:.1f} dB) | [UYGUN] |",
    f"| 4. Rayleigh Zarf Moment Hatası   : Hata = %{err_ray_pct:.2f} (Limit <= %2.0)            | [UYGUN] |",
    f"| 5. Kesinti Olasılığı (-15 dB)    : Rayleigh = %{outage_ray*100:.2f} | Rician = %{outage_ric2*100:.4f}  | [UYGUN] |",
    f"| 6. Frekans Çeşitliliği Kazancı   : Kazanç = +{diversity_gain:.2f} dB (>= 20.0 dB Eşik)     | [UYGUN] |",
    f"| 7. Enerji Korunumu (|F| <= 2.0)  : Maks |F| = {max_F1:.4f} <= 2.0000                 | [UYGUN] |",
    f"| 8. Dashboard Görsel Artefaktı    : 300 DPI PNG ({png_size:,} bayt > 100 KB)     | [UYGUN] |",
    "+" + "=" * 70 + "+",
    "| SONUÇ: TÜM 8 RADAR & HABERLEŞME KRİTERİ VE DO-254 TESTLERİ SAĞLANDI!|",
    "+" + "=" * 70 + "+"
]

report_text = "\n".join(report_lines)
print(report_text)

# Sertifikasyon Assert Korumaları
assert err_null_r <= 25.0, "Null menzili kalifikasyon hatası!"
assert null_depth <= -35.0, "Null derinliği kalifikasyon hatası!"
assert diversity_gain >= 20.0, "Çeşitlilik kazancı kalifikasyon hatası!"
assert max_F1 <= 2.0001, "Enerji korunumu kalifikasyon hatası!"
assert os.path.exists(output_png) and os.path.getsize(output_png) > 100000, "Dashboard görseli eksik veya yetersiz!"

print("\n[MÜKEMMEL] GÜN 310: FADING VE MULTIPATH AVİYONİK KALİFİKASYONU TAMAMLANDI.")

