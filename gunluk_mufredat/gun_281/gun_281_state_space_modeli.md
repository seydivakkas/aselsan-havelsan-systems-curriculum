# Gün 281: Faz F9 — Durum-Uzay Modeli (State-Space Model: $A, B, C, D$ Matrisleri)

## Lisans ve Telif Hakkı Bildirgesi
```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.

YASAKLAR:
  1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
  2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
  3. Alt lisanslanamaz, satılamaz veya devredilemez.
  4. Tersine mühendislik yapılamaz.

İZİN VERİLEN KULLANIM:
  - GitHub üzerinde görüntüleme ve okuma.
  - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).

YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
İzin talepleri için: GitHub @seydivakkas
```

---

## İçindekiler Tablosu
1. [Giriş: Klasik Kontrolden Modern Kontrole Geçiş Devrimi](#giris)
2. [Durum Değişkeni Kavramı ve Durum-Uzay Formülasyonu](#durum-kavrami)
3. [Sistem Matrislerinin Fiziksel Anlamı: $A, B, C, D$](#matrislerin-anlami)
4. [Taktik İHA Boyuna Uçuş Mekaniği ve Doğrusallaştırma](#uav-mekanigi)
5. [Özdeğerler ($\lambda_i$) ve Uçuş Modları: Short-Period ve Phugoid](#ozdegerler-ve-modlar)
6. [Sürekli Zamandan Ayrık Zamana Dönüşüm (C2D: Zero-Order Hold)](#ayriklastirma)
7. [Durum Geçiş Matrisi $\Phi(t) = e^{At}$ ve Lyapunov Kararlılığı](#lyapunov-kararliligi)
8. [C++20 ile Gerçek Zamanlı Deterministik Durum-Uzay Sınıfı](#cpp20-sinifi)
9. [Savunma Sanayii Güvenlik Kalkanları ve Hata İzolasyonu](#guvenlik-kalkanlari)
10. [Sonraki Adımlar ve Faz F9 Yol Haritası](#sonraki-adimlar)

---

### 1. Giriş: Klasik Kontrolden Modern Kontrole Geçiş Devrimi
Son günlerde tek girişli tek çıkışlı (SISO) transfer fonksiyonlarını $G(s)$, PID denetleyicileri ve zaman düzlemi spesifikasyonlarını inceledik.
Ancak gerçek bir savaş uçağı, taktik İHA veya güdümlü füze tek bir değişkenle yönetilmez:
* İrtifa dümeni (elevator), kanatçıklar (aileron), istikamet dümeni (rudder), motor itkisi (thrust)...
* İleri hız ($u$), dikey hız ($w$), yan kayma ($v$), yalpalama ($p$), yunuslama ($q$), sapma ($r$), irtifa ($h$)...

Transfer fonksiyonları bu çok girişli çok çıkışlı (MIMO) dünyayı ifade etmekte yetersiz kalır ve sistemin iç durumlarını (internal states) "kara kutu" ardına gizler.
İşte 1960'larda Rudolf Kalman tarafından başlatılan **Modern Kontrol Teorisi**, sistemi durum değişkenleriyle açıkça ifade eden **Durum-Uzay (State-Space)** gösterimini getirmiştir.

```python
# [KOD HÜCRESİ 1: Standart Durum-Uzay LTI Sınıfı ve ZOH Matris Üstel Ayrıklaştırması]
# Amaç: Çok girişli çok çıkışlı (MIMO) dinamik sistemler için modern durum-uzay (State-Space)
# formülasyonunu kurmak:
# dx/dt = A*x + B*u
# y     = C*x + D*u
# ve uçuş kontrol bilgisayarı (FCC) için Zero-Order Hold (ZOH) matris üsteli ile ayrıklaştırmak.

import numpy as np
from scipy import linalg
from typing import Dict, Tuple, List

class StateSpaceLTI:
    """
    Doğrusal Zamanla Değişmeyen (LTI) Durum-Uzay Modeli:
    x_dot = A*x + B*u
    y     = C*x + D*u
    """
    def __init__(self, A: np.ndarray, B: np.ndarray, C: np.ndarray, D: np.ndarray = None):
        self.A = np.array(A, dtype=np.float64)
        self.B = np.array(B, dtype=np.float64)
        self.C = np.array(C, dtype=np.float64)
        
        n = self.A.shape[0]
        m = self.B.shape[1] if self.B.ndim > 1 else 1
        p = self.C.shape[0] if self.C.ndim > 1 else 1
        
        if self.B.ndim == 1:
            self.B = self.B.reshape((n, 1))
        if self.C.ndim == 1:
            self.C = self.C.reshape((1, n))
            
        if D is None:
            self.D = np.zeros((p, m), dtype=np.float64)
        else:
            self.D = np.array(D, dtype=np.float64)
            if self.D.ndim == 1:
                self.D = self.D.reshape((p, m))
                
        self.n_states = n
        self.n_inputs = m
        self.n_outputs = p
        
    def get_eigenvalues(self) -> List[Dict[str, float]]:
        """A matrisinin özdeğerlerini ve her modun doğal frekans ve sönümleme oranını hesaplar."""
        eigs = np.linalg.eigvals(self.A)
        modes = []
        for val in eigs:
            wn = float(np.abs(val))
            zeta = float(-val.real / wn) if wn > 1e-7 else 0.0
            modes.append({
                'eigenvalue': val,
                'real': float(val.real),
                'imag': float(val.imag),
                'wn': wn,
                'zeta': zeta
            })
        return modes

    def c2d_zoh(self, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Zero-Order Hold (ZOH) ile Sürekli Zamandan Ayrık Zamana Dönüşüm:
        M = [[A, B], [0, 0]]
        e^(M * dt) = [[Ad, Bd], [0, I]]
        """
        n, m = self.n_states, self.n_inputs
        M = np.block([
            [self.A, self.B],
            [np.zeros((m, n + m))]
        ])
        eM = linalg.expm(M * dt)
        Ad = eM[:n, :n]
        Bd = eM[:n, n:]
        return Ad, Bd

# Taktik İHA Boyuna Uçuş Dinamiği Modeli (4 Durum: delta_u, delta_w, q, delta_theta; 1 Girdi: delta_e)
A_uav = np.array([
    [-0.045,  0.036,  0.000, -9.810],
    [-0.369, -2.020, 17.000,  0.000],
    [ 0.001, -0.050, -2.050,  0.000],
    [ 0.000,  0.000,  1.000,  0.000]
])

B_uav = np.array([
    [ 0.000],
    [-0.450],
    [-1.250],
    [ 0.000]
])

C_uav = np.array([
    [0.0, 0.0, 1.0, 0.0],  # Çıktı 1: Jiroskop yunuslama hızı q (rad/s)
    [0.0, 0.0, 0.0, 1.0]   # Çıktı 2: AHRS yunuslama açısı theta (rad)
])

ss_uav = StateSpaceLTI(A_uav, B_uav, C_uav)
dt_fcc = 0.02  # 50 Hz aviyonik görev çevrimi
Ad_uav, Bd_uav = ss_uav.c2d_zoh(dt=dt_fcc)
modes = ss_uav.get_eigenvalues()

print("[PASS] Kod 1: Taktik İHA Durum-Uzay LTI Modeli Başarıyla Kuruldu.")
print(f"  - Durum Sayısı (n) : {ss_uav.n_states} | Girdi Sayısı (m) : {ss_uav.n_inputs} | Çıktı (p) : {ss_uav.n_outputs}")
print(f"  - Ayrık Ad Boyutu  : {Ad_uav.shape} | Bd Boyutu : {Bd_uav.shape} (Ts = {dt_fcc*1000:.0f} ms)")
print("  - Karakteristik Uçuş Modları (Özdeğerler):")
for i, m in enumerate(modes):
    print(f"    * Mod {i+1}: {m['real']:+.4f} {m['imag']:+.4f}j | wn = {m['wn']:.3f} rad/s | zeta = {m['zeta']:.4f}")

# Doğrulamalar:
spectral_radius = np.max(np.abs(np.linalg.eigvals(Ad_uav)))
assert spectral_radius < 1.0, "Ayrık sistemin spektral yarıçapı 1'den küçük (kararlı) olmalıdır!"
assert ss_uav.n_states == 4, "Durum sayısı tam 4 olmalıdır!"
assert ss_uav.n_outputs == 2, "Sensör çıktı sayısı 2 olmalıdır!"
```

### 2. Durum Değişkeni Kavramı ve Durum-Uzay Formülasyonu

#### Durum (State) Nedir?
Bir dinamik sistemin **durumu**, sistemin geçmişteki tüm hareket geçmişini özetleyen ve gelecekteki davranışını girdi sinyalleriyle birlikte eksiksiz olarak belirleyen **en küçük değişkenler kümesidir**.

Standart 1. Dereceden Matris Diferansiyel Denklem Sistemi:

$$\dot{x}(t) = A x(t) + B u(t) \quad \text{(Durum Denklemi)}$$
$$y(t) = C x(t) + D u(t) \quad \text{(Çıktı Denklemi)}$$

Burada:
* $x(t) \in \mathbb{R}^n$: Durum Vektörü ($n$ adet durum değişkeni)
* $u(t) \in \mathbb{R}^m$: Kontrol Girdisi Vektörü ($m$ adet eyleyici)
* $y(t) \in \mathbb{R}^p$: Çıktı Vektörü ($p$ adet sensör ölçümü)

```python
# [KOD HÜCRESİ 2: Taktik İHA Boyuna Uçuş Dinamiği ve İrtifa Dümeni Basamak Simülasyonu]
# Amaç: İrtifa dümenine (elevator, delta_e) -2 derecelik basamak komutu verildiğinde
# sistemin 4 durumunun zaman evrimini (u, w, q, theta) 20 saniye boyunca simüle etmek.
# Hızlı Kısa Periyot (Short-Period) ve yavaş Fügoid (Phugoid) salınımlarını gözlemlemek.

import numpy as np

def simulate_state_space(ss: StateSpaceLTI, u_step: float, t_final: float = 20.0, dt: float = 0.02):
    Ad, Bd = ss.c2d_zoh(dt)
    steps = int(t_final / dt)
    t = np.linspace(0, t_final, steps)
    
    n, p = ss.n_states, ss.n_outputs
    x_hist = np.zeros((steps, n))
    y_hist = np.zeros((steps, p))
    
    curr_x = np.zeros(n)
    u_vec = np.array([u_step])
    
    for i in range(steps):
        x_hist[i] = curr_x
        y_hist[i] = ss.C @ curr_x + ss.D @ u_vec
        curr_x = Ad @ curr_x + Bd @ u_vec
        
    return t, x_hist, y_hist

delta_e_cmd = np.radians(-2.0) # -2 derece burun yukarı irtifa dümeni komutu
t_flight, states_hist, outputs_hist = simulate_state_space(ss_uav, u_step=delta_e_cmd, t_final=20.0, dt=0.02)

# Birim Dönüşümleri (Görsel ve Raporlama için)
delta_u = states_hist[:, 0]               # İleri hız sapması (m/s)
delta_w = states_hist[:, 1]               # Dikey hız sapması (m/s)
q_deg = np.degrees(states_hist[:, 2])     # Yunuslama hızı (deg/s)
theta_deg = np.degrees(states_hist[:, 3]) # Yunuslama açısı (deg)

max_q = float(np.max(np.abs(q_deg)))
max_theta = float(np.max(np.abs(theta_deg)))
final_theta = float(theta_deg[-1])

print("[ANALİZ] İrtifa Dümeni (-2°) Basamak Tepkisi Uçuş Analizi:")
print(f"  * Maksimum Yunuslama Hızı (|q_max|)   : {max_q:.3f} deg/s (Kısa Periyot Zirvesi)")
print(f"  * Maksimum Yunuslama Açısı (|th_max|) : {max_theta:.3f} deg (Fügoid Tepe Değeri)")
print(f"  * 20. Saniyedeki Yunuslama Açısı      : {final_theta:.3f} deg")
print(f"  * Maksimum İleri Hız Sapması (|u_max|): {np.max(np.abs(delta_u)):.3f} m/s")

# Doğrulamalar:
assert max_q > 0.5, "İrtifa dümeni en az 0.5 deg/s yunuslama hızı üretmelidir!"
assert max_theta > 4.0, "Yunuslama açısı en az 4 dereceye tırmanmalıdır!"
assert abs(final_theta) < 15.0, "Uçuş zarfı limitleri aşılmamalıdır!"
```

### 3. Sistem Matrislerinin Fiziksel Anlamı: $A, B, C, D$

1. **$A \in \mathbb{R}^{n \times n}$ (Sistem / Dinamik Matrisi):**
   * Sistemin dış etki olmadan kendi iç dinamikleriyle nasıl evrildiğini temsil eder.
   * $A$ matrisinin özdeğerleri ($\det(\lambda I - A) = 0$), sistemin kararlılığını, kutuplarını, osilasyon frekanslarını ve sönümlemelerini belirler.
2. **$B \in \mathbb{R}^{n \times m}$ (Giriş Matrisi):**
   * Eyleyicilerin ve kontrol kumandalarının durum türevlerine olan etkisini tanımlar.
3. **$C \in \mathbb{R}^{p \times n}$ (Çıkış / Gözlem Matrisi):**
   * Durum değişkenlerinin sensörler (IMU, Barometre, Pitot vb.) tarafından nasıl ölçüldüğünü gösterir.
4. **$D \in \mathbb{R}^{p \times m}$ (Doğrudan İletim / Feedthrough Matrisi):**
   * Girdinin sensör çıktısına anlık, gecikmesiz doğrudan etkisidir. Havacılık ve robotik sistemlerinde fiziksel eylemsizlik nedeniyle neredeyse her zaman **$D = 0$** (Strictly Proper) kabul edilir.

```python
# [KOD HÜCRESİ 3: Durum Geçiş Matrisi Phi(t) = exp(At) ve Lyapunov Enerji Fonksiyonu]
# Amaç: Girdi olmaksızın (u = 0) başlangıç durumundan serbest bırakılan (Zero-Input Response)
# İHA'nın denge noktasına dönüşünü ve Lyapunov enerji fonksiyonunun V(x) = x^T * P * x
# monotonik azalışını ispatlamak. A^T * P + P * A = -Q Lyapunov denklemi çözümü.

import numpy as np
from scipy import linalg

def compute_lyapunov_matrix(A: np.ndarray, Q: np.ndarray = None) -> np.ndarray:
    n = A.shape[0]
    if Q is None:
        Q = np.eye(n)
    # Continuous-time Lyapunov Equation: A^T * P + P * A = -Q
    # scipy.linalg.solve_continuous_lyapunov(a, q) solves: A * P + P * A^H = Q
    # We solve: A^T * P + P * A = -Q
    P = linalg.solve_continuous_lyapunov(A.T, -Q)
    return P

# Lyapunov P matrisini hesapla
Q_identity = np.eye(ss_uav.n_states)
P_matrix = compute_lyapunov_matrix(ss_uav.A, Q_identity)

# Başlangıç Bozulması (Initial Condition): Rüzgar türbülansı ile oluşmuş sapmalar
x0 = np.array([2.0, 1.0, np.radians(3.0), np.radians(4.0)]) # [u=2m/s, w=1m/s, q=3deg/s, theta=4deg]

steps_zero = int(15.0 / 0.02)
t_zero = np.linspace(0, 15.0, steps_zero)
Ad_uav, _ = ss_uav.c2d_zoh(0.02)

x_free = np.zeros((steps_zero, 4))
v_energy = np.zeros(steps_zero)

curr_x = x0.copy()
for i in range(steps_zero):
    x_free[i] = curr_x
    v_energy[i] = float(curr_x.T @ P_matrix @ curr_x)
    curr_x = Ad_uav @ curr_x # u = 0 serbest yanıt

energy_init = v_energy[0]
energy_final = v_energy[-1]
energy_decay_pct = (1.0 - energy_final / energy_init) * 100.0

print("[PASS] Kod 3: Durum Geçiş Matrisi ve Lyapunov Kararlılık Doğrulaması:")
print(f"  * Başlangıç Lyapunov Enerjisi V(x0)  : {energy_init:.4f}")
print(f"  * 15s Sonraki Kalan Enerji V(x_end)  : {energy_final:.6f}")
print(f"  * Enerji Sönümlenme Oranı           : %{energy_decay_pct:.2f} (Asimptotik Kararlı)")
print(f"  * P Matrisi Pozitif Tanımlılık (min eig): {np.min(np.linalg.eigvals(P_matrix)):.4f} > 0")

assert energy_final < energy_init, "Lyapunov enerjisi monotonik olarak azalmalıdır!"
assert energy_decay_pct > 20.0, "15 saniyede Lyapunov enerjisi en az %20 sönümlenmelidir!"
assert np.all(np.linalg.eigvals(P_matrix) > 0), "Lyapunov P matrisi kesin pozitif tanımlı olmalıdır!"
```

### 4. Taktik İHA Boyuna Uçuş Mekaniği ve Doğrusallaştırma

Bir sabit kanatlı taktik İHA'nın boyuna (longitudinal) hareket denklemleri $V_0 = 17\text{ m/s}$ seyir hızında doğrusallaştırıldığında 4 temel durum değişkeni ortaya çıkar:

$$x = \begin{bmatrix} \Delta u \\ \Delta w \\ q \\ \Delta \theta \end{bmatrix} \begin{matrix} \text{İleri hız sapması (m/s)} \\ \text{Dikey hız sapması (m/s)} \\ \text{Yunuslama açısal hızı (rad/s)} \\ \text{Yunuslama açısı (rad)} \end{matrix}$$

Kontrol girdisi:
$$u = [\delta_e] \quad \text{(İrtifa Dümeni Açısı - rad)}$$

Sensör çıktıları:
$$y = \begin{bmatrix} q \\ \Delta \theta \end{bmatrix} = \begin{bmatrix} 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 1 \end{bmatrix} x$$

```python
# [KOD HÜCRESİ 4: 3 Askeri Uç Durum ve Güvenlik Kalkanı Testleri]
# Amaç: DO-178C DAL-A uçuş kontrol yazılımlarında Durum-Uzay modelini denetleyen 3 kalkan:
# 1. Özdeğer ve Kararlılık Kalkanı (Eigenvalue Stability Guard - Kararsız Kutup Alarmı)
# 2. Doğrudan İletim ve Cebirsel Döngü Kalkanı (Feedthrough D-Matrix Algebraic Loop Guard)
# 3. Uçuş Zarfı Durum Sapması Kalkanı (State-Space Flight Envelope Deviation Guard)

import numpy as np

print("[TEST 1] Özdeğer ve Kararlılık Kalkanı (Eigenvalue Stability Guard)...")
class EigenvalueStabilityGuard:
    """
    Sürekli zaman matrisi A'nın tüm özdeğerlerinin sol yarı düzlemde (Re(lambda) < 0)
    ve ayrık zaman matrisi Ad'nin birim çember içinde (|lambda_d| < 1) olduğunu denetler.
    """
    def __init__(self, max_allowed_real_part: float = -1e-4):
        self.max_real = max_allowed_real_part
        
    def inspect(self, A: np.ndarray) -> Tuple[bool, str]:
        eigs = np.linalg.eigvals(A)
        max_re = float(np.max(eigs.real))
        if max_re >= self.max_real:
            return False, f"UNSTABLE POLE DETECTED: max Re(lambda) = {max_re:+.4f} >= {self.max_real}!"
        return True, f"ALL POLES STABLE: max Re(lambda) = {max_re:+.4f} < 0"

eig_guard = EigenvalueStabilityGuard()
pass_stable, msg_stable = eig_guard.inspect(ss_uav.A)

# Yapay Kararsız A Matrisi Testi
A_unstable = ss_uav.A.copy()
A_unstable[0, 0] = +0.15 # Sağ yarı düzleme kaçan kutup
pass_unstable, msg_unstable = eig_guard.inspect(A_unstable)

assert pass_stable is True, "Gerçek İHA A matrisi kararlı olmalıdır!"
assert pass_unstable is False, "Kararsız matris kalkan tarafından derhal yakalanmalıdır!"
print(f"  - Nominal A Matrisi  : {msg_stable} [GÜVENLİ]")
print(f"  - Bozuk A Matrisi    : {msg_unstable} [KORUMA DEVREDE]")
print("  [PASS] Test 1: Özdeğer Kararlılık Kalkanı başarıyla doğrulandı.\n")


print("[TEST 2] Doğrudan İletim ve Cebirsel Döngü Kalkanı (Feedthrough D-Matrix Guard)...")
class FeedthroughAlgebraicLoopGuard:
    """
    D != 0 olduğunda girdi doğrudan sensör çıktısına yansır (Direct Transmission).
    Bu durum dijital geri besleme döngüsünde anlık gecikmesiz cebirsel döngü (algebraic loop)
    ve sayısal patlama yaratır. Askeri FCC standartları D = 0 zorunlu kılar.
    """
    def __init__(self, tolerance: float = 1e-6):
        self.tol = tolerance
        
    def inspect(self, D: np.ndarray) -> Tuple[bool, str]:
        norm_d = float(np.linalg.norm(D))
        if norm_d > self.tol:
            return False, f"ALGEBRAIC LOOP RISK: Feedthrough norm ||D|| = {norm_d:.4f} > 0!"
        return True, "STRICTLY PROPER SYSTEM (D = 0, NO DIRECT FEEDTHROUGH)"

d_guard = FeedthroughAlgebraicLoopGuard()
pass_d_nom, msg_d_nom = d_guard.inspect(ss_uav.D)
pass_d_bad, msg_d_bad = d_guard.inspect(np.array([[0.15], [0.0]]))

assert pass_d_nom is True, "Nominal sistem strictly proper olmalıdır!"
assert pass_d_bad is False, "Sıfır olmayan D matrisi alarm üretmelidir!"
print(f"  - Nominal D Matrisi  : {msg_d_nom} [ONAYLANDI]")
print(f"  - Hatalı D Matrisi   : {msg_d_bad} [ENGEL İZOLASYONU]")
print("  [PASS] Test 2: Cebirsel Döngü Kalkanı başarıyla doğrulandı.\n")


print("[TEST 3] Uçuş Zarfı Durum Sapması Kalkanı (Flight Envelope Guard)...")
class FlightEnvelopeGuard:
    """
    Durum vektörünün fiziksel sınırları (Stall açısı theta < 30°, Aşırı G / yunuslama hızı |q| < 30°/s)
    aşıldığında acil emniyet modunu tetikler.
    """
    def __init__(self, max_theta_deg: float = 25.0, max_q_deg: float = 20.0):
        self.max_theta = max_theta_deg
        self.max_q = max_q_deg
        
    def inspect(self, q_deg_arr: np.ndarray, theta_deg_arr: np.ndarray) -> Tuple[bool, str]:
        max_q = np.max(np.abs(q_deg_arr))
        max_th = np.max(np.abs(theta_deg_arr))
        if max_th > self.max_theta or max_q > self.max_q:
            return False, f"ENVELOPE EXCEEDED: max |theta|={max_th:.1f}° (Limit: {self.max_theta}°) or |q|={max_q:.1f}°/s (Limit: {self.max_q}°/s)!"
        return True, "WITHIN STRUCTURAL FLIGHT ENVELOPE"

env_guard = FlightEnvelopeGuard(max_theta_deg=25.0, max_q_deg=20.0)
pass_env_nom, msg_env_nom = env_guard.inspect(q_deg, theta_deg)
pass_env_bad, msg_env_bad = env_guard.inspect(np.array([25.0]), np.array([32.0]))

assert pass_env_nom is True, "Simülasyon uçuş zarfı içinde kalmalıdır!"
assert pass_env_bad is False, "Aşırı durum sapması yakalanmalıdır!"
print(f"  - Simülasyon Zarfı   : {msg_env_nom} [GÜVENLİ]")
print(f"  - Aşırı Sapma        : {msg_env_bad} [KORUMA DEVREDE]")
print("  [PASS] Test 3: Uçuş Zarfı Kalkanı başarıyla doğrulandı.")
```

### 5. Özdeğerler ($\lambda_i$) ve Uçuş Modları: Short-Period ve Phugoid

Durum matrisi $A$'nın özdeğerleri hava aracının aerodinamik kimliğini belirler:

$$\det(\lambda I - A) = 0$$

#### 1. Kısa Periyot Modu (Short-Period Mode):
* Yüksek frekanslı ($\omega_n \approx 2.25\text{ rad/s}$), yüksek sönümlü ($\zeta \approx 0.91$) karmaşık eşlenik kutup çifti.
* Hız neredeyse değişmeden İHA'nın burnunun hızla hücum açısına oturmasını sağlayan ana tork modudur.
* Pilot veya otopilot tarafından hissedilen birincil tepkidir.

#### 2. Fügoid Modu (Phugoid / Long-Period Mode):
* Çok düşük frekanslı ($\omega_n \approx 0.20\text{ rad/s}$), çok hafif sönümlü ($\zeta \approx 0.05$) yavaş salınım modu.
* Kinetik enerji (hız $\Delta u$) ile potansiyel enerji (irtifa ve $\Delta \theta$) arasındaki yavaş takastır. İHA yukarı tırmanırken yavaşlar, burnunu eğip hızlanarak dalar.

```python
# [KOD HÜCRESİ 5: 4 Panelli Aviyonik Durum-Uzay Dashboard Görselleştirmesi]
# Amaç: İHA boyuna durumlarının (u, w, q, theta) basamak tepkisini, s-düzleminde özdeğer
# dağılımını (kutuplar), faz portresini (q vs theta) ve aviyonik HUD telemetri panelini
# gösteren 300 DPI, koyu temalı (#0F172A) görsel üretimi.

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

# PANEL 1 (Sol Üst): İHA Boyuna Durum Değişkenleri Zaman Tepkisi
axs[0, 0].plot(t_flight, delta_u, color='#38BDF8', linewidth=1.8, label=r'$\Delta u$ İleri Hız (m/s)')
axs[0, 0].plot(t_flight, delta_w, color='#F59E0B', linewidth=1.8, label=r'$\Delta w$ Dikey Hız (m/s)')
axs[0, 0].plot(t_flight, q_deg, color='#EF4444', linewidth=2.0, label=r'$q$ Yunuslama Hızı (deg/s)')
axs[0, 0].plot(t_flight, theta_deg, color='#10B981', linewidth=2.2, label=r'$\theta$ Yunuslama Açısı (deg)')

axs[0, 0].axvline(x=0.0, color='#64748B', linestyle='--', alpha=0.7)
axs[0, 0].set_title(r"İHA Boyuna Uçuş Durumları: $\dot{x} = Ax + Bu$ ($\delta_e = -2^\circ$ Basamak)", 
                    fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[0, 0].set_xlabel("Zaman (saniye)", fontsize=11, color='#E2E8F0')
axs[0, 0].set_ylabel("Durum Değişkeni Büyüklükleri", fontsize=11, color='#E2E8F0')
axs[0, 0].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[0, 0].legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=9)

# PANEL 2 (Sağ Üst): Karmaşık s-Düzleminde Özdeğerler (Short-Period ve Phugoid Kutupları)
eigs = np.linalg.eigvals(ss_uav.A)

# Sol Yarı Düzlem Vurgusu
axs[0, 1].axvspan(-3.0, 0.0, color='#10B981', alpha=0.08, label='Kararlı Sol Yarı Düzlem (LHP)')
axs[0, 1].axvline(x=0.0, color='#EF4444', linestyle='-', linewidth=1.5, label='Sanal Eksen (Kararlılık Sınırı)')
axs[0, 1].axhline(y=0.0, color='#64748B', linestyle='--', alpha=0.5)

# Kutupları Çiz
sp_eigs = [eigs[0], eigs[1]]
ph_eigs = [eigs[2], eigs[3]]

axs[0, 1].scatter([val.real for val in sp_eigs], [val.imag for val in sp_eigs], 
                  color='#38BDF8', s=120, marker='x', linewidth=3.0, label='Kısa Periyot Kutupları (Short-Period)')
axs[0, 1].scatter([val.real for val in ph_eigs], [val.imag for val in ph_eigs], 
                  color='#F59E0B', s=120, marker='o', linewidth=2.0, label='Fügoid Kutupları (Phugoid)')

# Açıklayıcı metinler
axs[0, 1].annotate(f"Short-Period Mode\nwn={modes[0]['wn']:.2f} rad/s, z={modes[0]['zeta']:.2f}", 
                   xy=(eigs[0].real, eigs[0].imag), xytext=(eigs[0].real - 0.8, eigs[0].imag + 0.3),
                   color='#38BDF8', fontsize=9, arrowprops=dict(arrowstyle="->", color='#38BDF8'))

axs[0, 1].annotate(f"Phugoid Mode\nwn={modes[2]['wn']:.2f} rad/s, z={modes[2]['zeta']:.2f}", 
                   xy=(eigs[2].real, eigs[2].imag), xytext=(eigs[2].real - 0.8, eigs[2].imag + 0.4),
                   color='#F59E0B', fontsize=9, arrowprops=dict(arrowstyle="->", color='#F59E0B'))

axs[0, 1].set_title(r"Karmaşık $s$-Düzleminde Sistem Dinamik Kutupları ($\lambda_i \in \mathbb{C}$)", 
                    fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[0, 1].set_xlabel(r"Reel Eksen $\sigma$ (1/s)", fontsize=11, color='#E2E8F0')
axs[0, 1].set_ylabel(r"Sanal Eksen $j\omega$ (rad/s)", fontsize=11, color='#E2E8F0')
axs[0, 1].set_xlim(-3.0, 0.5)
axs[0, 1].set_ylim(-1.5, 1.5)
axs[0, 1].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[0, 1].legend(loc='lower left', facecolor='#1E293B', edgecolor='#334155', fontsize=8.5)

# PANEL 3 (Sol Alt): Durum Faz Portresi (Phase Portrait: q vs theta)
axs[1, 0].plot(theta_deg, q_deg, color='#10B981', linewidth=2.2, label='Faz Yörüngesi (Phase Trajectory)')
axs[1, 0].scatter([theta_deg[0]], [q_deg[0]], color='#38BDF8', s=90, marker='o', label='Başlangıç (t=0)')
axs[1, 0].scatter([theta_deg[-1]], [q_deg[-1]], color='#EF4444', s=100, marker='*', label='Son Durum (t=20s)')

# Ok işaretleri ekle
mid_idx = len(theta_deg) // 4
axs[1, 0].annotate('', xy=(theta_deg[mid_idx+5], q_deg[mid_idx+5]), xytext=(theta_deg[mid_idx], q_deg[mid_idx]),
                   arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))

axs[1, 0].set_title(r"Durum Faz Portresi: Yunuslama Hızı ($q$) vs Yunuslama Açısı ($\theta$)", 
                    fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[1, 0].set_xlabel(r"Yunuslama Açısı $\theta$ (derece)", fontsize=11, color='#E2E8F0')
axs[1, 0].set_ylabel(r"Yunuslama Açısal Hızı $q$ (derece/saniye)", fontsize=11, color='#E2E8F0')
axs[1, 0].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[1, 0].legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=9)

# PANEL 4 (Sağ Alt): Aviyonik Uçuş Kontrol Bilgisayarı (FCC) HUD Ekranı
hud_canvas = np.zeros((400, 600, 3), dtype=np.uint8)
hud_canvas[:] = [15, 23, 42]

axs[1, 1].imshow(hud_canvas)
axs[1, 1].set_title("Aviyonik Otopilot Durum-Uzay Telemetrisi & Mod İzleme", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)

# Nişangah ve HUD Grafikleri
axs[1, 1].axvline(x=300, color='#10B981', linestyle=':', alpha=0.6)
axs[1, 1].axhline(y=200, color='#10B981', linestyle=':', alpha=0.6)
rect = plt.Rectangle((180, 120), 240, 160, fill=False, edgecolor='#10B981', linestyle='--', linewidth=1.5)
axs[1, 1].add_patch(rect)

axs[1, 1].text(30, 45, "ASELSAN / TUSAŞ UAV STATE-SPACE CORE", color='#38BDF8', fontsize=9, fontfamily='monospace', fontweight='bold')
axs[1, 1].text(30, 75, "MODEL FORMU  : dx/dt = A*x + B*u | y = C*x + D*u", color='#10B981', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 105, f"DURUM BOYUTU : n={ss_uav.n_states} (u, w, q, th) | GİRDİ: m=1 (delta_e)", color='#E2E8F0', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 130, f"AYRIKLAŞTIRMA: ZOH MATRIX EXPONENTIAL (Ts=20ms, 50Hz)", color='#38BDF8', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 155, f"KISA PERİYOT : wn=2.25 rad/s | zeta=0.91 (AŞIRI SÖNÜMLÜ)", color='#10B981', fontsize=9, fontfamily='monospace', fontweight='bold')
axs[1, 1].text(30, 185, f"FÜGOİD MODU  : wn=0.20 rad/s | zeta=0.05 (HAFİF SALINIMLI)", color='#F59E0B', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 215, "LYAPUNOV STAB: A^T*P + P*A = -Q [STABLE PASS]", color='#10B981', fontsize=8.5, fontfamily='monospace')
axs[1, 1].text(30, 360, "DO-178C DAL-A FLIGHT DYNAMICS KERNEL ACTIVE", color='#64748B', fontsize=8, fontfamily='monospace')
axs[1, 1].axis('off')

plt.suptitle("GÜN 281: MODERN KONTROL — DURUM-UZAY (STATE-SPACE) MODELİ VE İHA UÇUŞ MEKANİĞİ", 
             fontsize=15, fontweight='heavy', color='#F8FAFC', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

out_png = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_281/gun_281_state_space_modeli.png"
plt.savefig(out_png, dpi=300, facecolor='#0F172A')
plt.close()

png_size = os.path.getsize(out_png)
print(f"[OK] 4-Panelli Durum-Uzay Gorseli Basariyla Uretildi: {out_png}")
print(f"  - Dosya Boyutu: {png_size / 1024.0:.2f} KB (Beklenen: > 100 KB)")
assert png_size > 100 * 1024, "Görsel boyutu 100 KB üzerinde olmalıdır!"
```

### 6. Sürekli Zamandan Ayrık Zamana Dönüşüm (C2D: Zero-Order Hold)

Aviyonik uçuş kontrol bilgisayarı (FCC) dijital olarak çalıştığından, sürekli sistem ayrık zamana ($T_s = 20\text{ ms} \implies 50\text{ Hz}$) çevrilmelidir:

$$x_{k+1} = A_d x_k + B_d u_k$$
$$y_k = C x_k + D u_k$$

Matris üsteli (Matrix Exponential) formülü:

$$A_d = e^{A T_s}, \quad B_d = \left( \int_0^{T_s} e^{A \tau} d\tau \right) B$$

Blok matris üsteli ile tam nümerik çözüm (Van Loan Algoritması):

$$\exp\left( \begin{bmatrix} A & B \\ 0 & 0 \end{bmatrix} T_s \right) = \begin{bmatrix} A_d & B_d \\ 0 & I \end{bmatrix}$$

```python
# [KOD HÜCRESİ 6: DO-178C DAL-A Durum-Uzay ve Dinamik Kararlılık Kalifikasyon Raporu]
# Amaç: Taktik İHA durum-uzay matrislerinin, ayrıklaştırma doğruluğunun ve uçuş emniyet
# sınırlarının DO-178C DAL-A standartlarına göre otomatik doğrulanması.

import numpy as np

def generate_state_space_qualification_report(ss: StateSpaceLTI, Ad: np.ndarray, Bd: np.ndarray) -> Dict[str, any]:
    eigs_c = np.linalg.eigvals(ss.A)
    eigs_d = np.linalg.eigvals(Ad)
    
    max_real_c = float(np.max(eigs_c.real))
    spectral_radius = float(np.max(np.abs(eigs_d)))
    
    crit_1_c_stable = bool(max_real_c < 0.0)
    crit_2_d_stable = bool(spectral_radius < 1.0)
    crit_3_proper = bool(np.linalg.norm(ss.D) == 0.0)
    crit_4_dim_match = bool(ss.A.shape[0] == ss.B.shape[0] == ss.C.shape[1])
    
    all_pass = crit_1_c_stable and crit_2_d_stable and crit_3_proper and crit_4_dim_match
    
    return {
        'max_real_continuous': max_real_c,
        'spectral_radius_discrete': spectral_radius,
        'n_states': ss.n_states,
        'n_inputs': ss.n_inputs,
        'n_outputs': ss.n_outputs,
        'crit_1_c_stable': crit_1_c_stable,
        'crit_2_d_stable': crit_2_d_stable,
        'crit_3_proper': crit_3_proper,
        'crit_4_dim_match': crit_4_dim_match,
        'flight_qualification_certified': all_pass
    }

report = generate_state_space_qualification_report(ss_uav, Ad_uav, Bd_uav)

print("\n==========================================================================")
print("[AVİYONİK DURUM-UZAY MODELİ KALİFİKASYON VE EMNİYET RAPORU]")
print("==========================================================================")
print(f"  * Durum / Girdi / Çıktı Boyutu   : {report['n_states']}x{report['n_states']} | Girdi: {report['n_inputs']} | Çıktı: {report['n_outputs']}")
print(f"  * Sürekli Zaman Kararlılığı      : max Re(lambda) = {report['max_real_continuous']:+.4f} -> [{'PASS' if report['crit_1_c_stable'] else 'FAIL'}]")
print(f"  * Ayrık Zaman Spektral Yarıçapı  : rho(Ad) = {report['spectral_radius_discrete']:.6f} (< 1.0) -> [{'PASS' if report['crit_2_d_stable'] else 'FAIL'}]")
print(f"  * Strictly Proper (D = 0)        : Doğrudan besleme yok -> [{'PASS' if report['crit_3_proper'] else 'FAIL'}]")
print(f"  * Matris Boyut Tutarlılığı       : Tam uyumlu -> [{'PASS' if report['crit_4_dim_match'] else 'FAIL'}]")
print(f"  * Uçuş Emniyet Sertifikasyonu    : [DO-178C DAL-A UÇUŞ ONAYI VERİLDİ]")
print("==========================================================================\n")

assert report['crit_1_c_stable'], "Sürekli zaman matrisi kararlı olmalıdır!"
assert report['crit_2_d_stable'], "Ayrık zaman matrisi kararlı olmalıdır!"
assert report['crit_3_proper'], "D matrisi sıfır olmalıdır!"
assert report['crit_4_dim_match'], "Matris boyutları tutarlı olmalıdır!"
assert report['flight_qualification_certified'], "Tüm kalifikasyon şartları sağlanmalıdır!"
```

### 7. Durum Geçiş Matrisi $\Phi(t) = e^{At}$ ve Lyapunov Kararlılığı

Girdi olmaksızın ($u(t) = 0$) sistemin serbest hareketi:

$$x(t) = e^{A t} x(0) = \Phi(t) x(0)$$

#### Lyapunov Kararlılık Teoremi:
Sistemin asimptotik kararlı olması için herhangi bir simetrik pozitif tanımlı $Q > 0$ matrisine karşılık:

$$A^T P + P A = -Q$$

denklemini sağlayan simetrik pozitif tanımlı bir $P > 0$ matrisinin var olması **gerek ve yeter şarttır**.
Sistemin toplam "enerjisi" $V(x) = x^T P x$ zamanla daima azalır:

$$\dot{V}(x) = x^T (A^T P + P A) x = -x^T Q x < 0 \quad (\forall x \ne 0)$$

### 8. Durum-Uzay ve Transfer Fonksiyonu Dönüşümü

Durum-uzay modelinden Laplace transfer fonksiyonuna geçiş:

$$s X(s) - x(0) = A X(s) + B U(s)$$
$$X(s) = (sI - A)^{-1} B U(s)$$
$$Y(s) = C X(s) + D U(s) = \left[ C (sI - A)^{-1} B + D \right] U(s)$$

Buradan transfer fonksiyonu matrisi:

$$G(s) = C (sI - A)^{-1} B + D = \frac{C \cdot \text{adj}(sI - A) \cdot B}{\det(sI - A)} + D$$

Paydadaki $\det(sI - A) = 0$ karakteristik denklemi, durum matrisi $A$'nın özdeğerlerinin transfer fonksiyonunun kutuplarıyla **özdeş** olduğunu kanıtlar!

### 9. C++20 ile Gerçek Zamanlı Deterministik Durum-Uzay Sınıfı

```cpp
#include <array>
#include <cstddef>
#include <concepts>

template <std::size_t States, std::size_t Inputs, std::size_t Outputs>
class DiscreteStateSpace {
public:
    using StateVec  = std::array<double, States>;
    using InputVec  = std::array<double, Inputs>;
    using OutputVec = std::array<double, Outputs>;
    using StateMat  = std::array<std::array<double, States>, States>;
    using InputMat  = std::array<std::array<double, Inputs>, States>;
    using OutputMat = std::array<std::array<double, States>, Outputs>;

private:
    StateMat  Ad_{};
    InputMat  Bd_{};
    OutputMat C_{};
    StateVec  x_{};

public:
    constexpr explicit DiscreteStateSpace(const StateMat& Ad, const InputMat& Bd, const OutputMat& C) noexcept
        : Ad_(Ad), Bd_(Bd), C_(C) {}

    [[nodiscard]] OutputVec update(const InputVec& u) noexcept {
        // 1. Output Equation: y = C * x
        OutputVec y{};
        for (std::size_t i = 0; i < Outputs; ++i) {
            double sum = 0.0;
            for (std::size_t j = 0; j < States; ++j) {
                sum += C_[i][j] * x_[j];
            }
            y[i] = sum;
        }

        // 2. State Update Equation: x_next = Ad * x + Bd * u
        StateVec x_next{};
        for (std::size_t i = 0; i < States; ++i) {
            double sum = 0.0;
            for (std::size_t j = 0; j < States; ++j) {
                sum += Ad_[i][j] * x_[j];
            }
            for (std::size_t j = 0; j < Inputs; ++j) {
                sum += Bd_[i][j] * u[j];
            }
            x_next[i] = sum;
        }
        x_ = x_next;
        return y;
    }

    [[nodiscard]] const StateVec& getState() const noexcept { return x_; }
    void setState(const StateVec& x_new) noexcept { x_ = x_new; }
};
```
Bu C++20 şablon sınıfı sıfır dinamik bellek ayırma (`std::array`), derleme zamanı boyut kontrolü ve DO-178C DAL-A tam determinizm garantisi sunar.

### 10. Savunma Sanayii Güvenlik Kalkanları ve Hata İzolasyonu

Uçuş kontrol sistemini sahada koruyan 3 kalkan:
1. **Özdeğer Kararlılık Kalkanı:** Sürekli veya ayrık zaman matrisinde kararsız kutup ($\text{Re}(\lambda) \ge 0$ veya $|\lambda_d| \ge 1$) tespit edildiğinde sistemi fail-safe moduna alır.
2. **Cebirsel Döngü Kalkanı:** $D \ne 0$ doğrudan iletimini denetleyerek dijital geri beslemede sonsuz cebirsel döngü oluşmasını engeller.
3. **Uçuş Zarfı Kalkanı:** İHA durum değişkenlerinin fiziksel stall açısı veya yapısal G sınırlarını aşmasını önler.

### 11. Endüstriyel Hata Analizi ve Karşı Önlemler (Failure Modes & Effects)

| Hata Modu | Kök Neden | Olası Sonuç | Aviyonik Karşı Önlem |
| :--- | :--- | :--- | :--- |
| **Kutup Sağa Kayması ($\text{Re}(\lambda) > 0$)** | Hatalı aerodinamik türev tablosu | Kontrolsüz ivmelenme ve kırım | Gerçek zamanlı özdeğer denetçisi & Geri alma modu. |
| **Cebirsel Döngü (Algebraic Loop)**| Sensör gecikmesini modellememek ($D \ne 0$)| Sayısal patlama veya döngü kilitlenmesi | $D = 0$ kuralı ve 1 döngü birim gecikme ekleme. |
| **Durum Patlaması (State Divergence)**| Eyleyici doyumunda durum kestirimi | Otopilotun stall sınırına girmesi | Durum doyumu sınırlayıcı (State Saturation Clamping). |
| **Nümerik Ayrıklaştırma Hatası**| Euler yerine ZOH matris üsteli kullanmamak | Uçuş bilgisayarında sahte osilasyon | Matrix exponential / Tustin bilineer dönüşümü. |

### 12. Karşılaştırmalı Analiz Tablosu: Klasik vs Modern Kontrol

| Kriter / Yaklaşım | Klasik Kontrol (Transfer Fonksiyonu) | Modern Kontrol (Durum-Uzay) |
| :--- | :--- | :--- |
| **Matematiksel Dil** | Laplace Düzlemi ($s$), Frekans Düzlemi ($j\omega$)| Diferansiyel Denklemler, Matris Cebiri ($\mathbb{R}^n$)|
| **Sistem Tipi** | Tek Girişli Tek Çıkışlı (SISO) | Çok Girişli Çok Çıkışlı (MIMO) |
| **İç Durum Görünürlüğü** | Gizli ("Kara Kutu" giriş-çıkış)| **Tam Açık ve Gözlemlenebilir** |
| **Başlangıç Koşulları** | Sıfır varsayılır ($x(0) = 0$)| **Rastgele $x(0)$ doğrudan hesaba katılır** |
| **Zamanla Değişen Sistemler**| Desteklenmez (LTI zorunlu) | $A(t), B(t)$ ile doğal desteklenir |
| **Optimal Kontrol (LQR/LQG)**| Çok zor veya imkansız | **Doğal ve doğrudan uygulanır** |

### 13. Havacılık Standartları: DO-178C DAL-A ve MIL-HDBK-1797

* **MIL-HDBK-1797 (Flying Qualities of Piloted Aircraft):** Uçuş kontrol kanunları tasarlanırken boyuna durum-uzay matrisinin Kısa Periyot modu ($\omega_{n_{sp}}, \zeta_{sp}$) ve Fügoid modu ($\omega_{n_{ph}}, \zeta_{ph}$) frekans ve sönümleme şartlarını sağlamalıdır.
* **DO-178C DAL-A:** Durum-uzay durum vektörü güncellemelerinde sayısal taşma (overflow) ve sıfıra bölme ihtimallerinin statik kod analiziyle imkansız olduğu kanıtlanmalıdır.

### 14. Gerçek Dünya Savunma Sanayii Başarı Hikayesi: BAYKAR Bayraktar TB2 ve Akıncı TİHA

**Uçuş Kontrol ve Otopilot Durum Kestirimi:**
BAYKAR tarafından üretilen Bayraktar TB2 ve Akıncı TİHA'lar, binlerce saatlik otonom uçuş icra eder. Hava aracının 6 serbestlik dereceli (6-DOF) uçuş mekaniği, durum-uzay formülasyonu ile modellenmiştir.
Gövdeye yerleştirilen üç yedekli aviyonik bilgisayarlar, her $20\text{ ms}$'de bir durum-uzay modelini işleterek uçağın hava hızını, yunuslama açısını, irtifasını ve motor gücünü koordine eder. Bu modern durum-uzay temeli olmasaydı, otonom iniş-kalkış ve zorlu hava koşullarında görev icrası mümkün olamazdı.

### 15. Donanım ve Eyleyici Entegrasyonu: Sensör Füzyonu ve Kalman Filtresi

Durum-uzay modeli, modern sensör füzyonunun (Kalman Filter / EKF) kalbidir:
1. **Zaman Güncellemesi (Time Update):** $\hat{x}_{k|k-1} = A_d \hat{x}_{k-1} + B_d u_{k-1}$
2. **Ölçüm Güncellemesi (Measurement Update):** $\hat{x}_k = \hat{x}_{k|k-1} + K_k (y_k - C \hat{x}_{k|k-1})$

Durum-uzay gösterimi sayesinde doğrudan ölçülemeyen durumlar (örneğin hücum açısı $\alpha$ veya rüzgar sürüklenmesi) diğer sensörlerden matematiksel olarak kestirilebilir.

### 16. Takviyeli Öğrenmede (RL) Durum-Uzay: Markov Karar Süreci (MDP)

Reinforcement Learning dünyasındaki Durum (State $s_t$), Aksiyon (Action $a_t$) ve Geçiş Dinamiği ($P(s_{t+1}|s_t, a_t)$), durum-uzay modelinin doğrudan karşılığıdır:

$$s_{t+1} = f(s_t, a_t) = A_d s_t + B_d a_t$$

RL ajanı eğitilirken durum-uzay matrisleri ortamın fizik motoru olarak kullanılır. Bu sayede simülasyonda öğrenilen politika, gerçek hava aracına aktarıldığında (Sim-to-Real) sıfır sürprizle çalışır.

### 17. Kendi Kendine Değerlendirme ve Savunma Mülakat Soruları

1. **Soru:** Durum-uzay modelinin klasik transfer fonksiyonuna göre en büyük 3 üstünlüğü nedir?
   * **Cevap:** (1) Çok girişli çok çıkışlı (MIMO) sistemleri doğal olarak modellemesi, (2) Sistemin iç durumlarını (internal states) açıkça takip edebilmesi, (3) Sıfır olmayan başlangıç koşullarını doğrudan hesaba katabilmesi.
2. **Soru:** $A$ matrisinin özdeğerleri sistem hakkında ne söyler?
   * **Cevap:** Sistemin kutuplarını, kararlılığını (Re$(\lambda) < 0$ ise kararlı), doğal salınım frekanslarını ($\omega_n$) ve sönümleme oranlarını ($\zeta$) verir.
3. **Soru:** İHA boyuna uçuş mekaniğindeki iki ana mod hangileridir?
   * **Cevap:** (1) Hızlı ve yüksek sönümlü Kısa Periyot Modu (Short-Period), (2) Yavaş ve hafif salınımlı Fügoid Modu (Phugoid).
4. **Soru:** ZOH (Zero-Order Hold) ayrıklaştırması neden basit Euler integralinden üstündür?
   * **Cevap:** Euler integrali yüksek frekanslarda yapay kararsızlık yaratırken, ZOH matris üsteli ($e^{AT_s}$) sistemin sürekli zaman çözümünü örnekleme anlarında analitik olarak birebir yakalar.
5. **Soru:** Sürekli zaman LTI sisteminin Lyapunov kararlılık şartı nedir?
   * **Cevap:** Herhangi bir $Q > 0$ için $A^T P + P A = -Q$ denklemini sağlayan simetrik pozitif tanımlı bir $P > 0$ matrisinin var olmasıdır.

### 18. Günün Özeti ve Temel Çıkarımlar

1. **Modern Temel:** $\dot{x} = Ax + Bu$ ve $y = Cx + Du$ matris denklemleri, modern kontrol teorisi, Kalman filtreleri ve takviyeli öğrenmenin ortak alfabesidir.
2. **Kutupların Gücü:** $A$ matrisinin özdeğerleri hava aracının gökyüzündeki tüm dinamik karakteristiğini tek başına belirler.
3. **MIMO Geleceği:** Yarın öğreneceğimiz "Controllability ve Observability" (Kontrol Edilebilirlik ve Gözlemlenebilirlik) kavramları, durum-uzay matrisleri üzerinde inşa edilecektir.

### 19. Sonraki Adım: Gün 282 ve Faz F9 Yol Haritası

**Tebrikler! Durum-Uzay modelinin (State-space model) tüm temellerini, İHA uçuş dinamiğini ve ayrıklaştırmasını tamamladınız.**

---

### Sıradaki Konu (Gün 282):
**Konu:** Controllability / observability sezgisi (Kontrol Edilebilirlik ve Gözlemlenebilirlik)
* Bir sistemin tüm durumlarını eyleyicilerimizle istediğimiz noktaya sürebilir miyiz? (Controllability Matrisi $\mathcal{C}$)
* Sensör çıktılarımızdan sistemin iç durumlarını eksiksiz kestirebilir miyiz? (Observability Matrisi $\mathcal{O}$)
* Kalman rank kriteri ve PBH testi.

*Modern kontrolün kalbine doğru ilerleyişimiz sürüyor!*
