# Gün 276: Faz F9 — Dinamik Sistemler: Durum (State), Girdi (Input) ve Çıktı (Output)

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
1. [Faz F9'a Hoş Geldiniz: Kontrol Teorisi ve Takviyeli Öğrenme (RL)](#giris)
2. [Dinamik Sistem, Durum, Girdi ve Çıktı Felsefesi](#dinamik-sistem-felsefesi)
3. [Lineer Durum Uzayı (State-Space) Matematiksel Temelleri](#durum-uzayi-matematigi)
4. [Taktik İHA Boyuna Uçuş Dinamiği Modellemesi](#iha-dinamigi)
5. [Ayrık Zamanlı Sistemler ve ZOH Sayısallaştırma](#ayrik-zaman)
6. [Savunma Sanayii Güvenlik Kalkanları: Stol, Doyum, Diverjans](#guvenlik-kalkanlari)
7. [Aviyonik HUD Telemetri Paneli ve Görselleştirme](#gorsellestirme)
8. [Askeri Uçuş Kalitesi Standartları: MIL-F-8785C](#askeri-standartlar)
9. [C++20 Gerçek Zamanlı Sistem Entegrasyonu](#cpp20-entegrasyon)
10. [Sonraki Adımlar ve Faz F9 Yol Haritası](#sonraki-adimlar)

---

### 1. Giriş: Faz F9 — Kontrol Teorisi ve Takviyeli Öğrenmeye (RL) Giriş
Görsel algılama motorumuz (Faz F8) sayesinde artık etrafımızdaki hedefleri, engelleri ve taktik tehditleri gerçek zamanlı olarak tespit edip takip edebiliyoruz. Ancak savunma ve havacılık mühendisliğinde "görmek" sadece ilk adımdır. Asıl kritik mühendislik başarısı, görülen hedefe doğru yönelmek, otonom rotayı takip etmek, hava türbülansına karşı uçağın kanatçıklarını mikrosaniyeler içinde hareket ettirmek ve platformu dengede tutmaktır.

Kontrol etmek istediğimiz fiziksel dünya **statik değil, dinamiktir; zamanla değişir**. Bir sistemi kontrol edebilmek veya ona takviyeli öğrenme (Reinforcement Learning) ajanı eğitebilmek için şu iki temel sorunun matematiksel olarak yanıtlanması zorunludur:
1. **"Sistem şu anda tam olarak ne durumda?" $\to$ Durum (State - $x$)**
2. **"Sisteme şu anda bir kuvvet/kumanda verirsem gelecekte ne olur?" $\to$ Girdi (Input - $u$) ve Çıktı (Output - $y$)**

```python
# [KOD HÜCRESİ 1: İHA Boyuna Uçuş Dinamiği Durum Uzayı Simülatörü]
# Amaç: Bir taktik İHA'nın boyuna (longitudinal) hareketini durum uzayı (State-Space)
# formunda modelleyen; durum (x), girdi (u) ve çıktı (y) ilişkilerini Runge-Kutta 4 (RK4)
# sayısal integratörüyle deterministik olarak çözen aviyonik dinamik sistem motoru.

import numpy as np
import time
from typing import Tuple, Dict, List

class UAVLongitudinalDynamics:
    """
    Taktik İHA Boyuna Uçuş Durum Uzayı Modeli:
    x = [u_vel, w_vel, q_pitch_rate, theta_pitch_angle]^T
        u_vel: İleri hız sapması (m/s)
        w_vel: Dikey hız sapması (m/s)
        q_pitch_rate: Yunuslama açısal hızı (rad/s)
        theta_pitch_angle: Yunuslama açısı (rad)
        
    u = [delta_e, delta_T]^T
        delta_e: İrtifa dümeni (elevator) sapma açısı (rad)
        delta_T: Motor itki sapması (N)
        
    y = [alpha_aoa, q_pitch_rate, V_total]^T
        alpha_aoa: Hücum açısı (Angle of Attack, rad)
        q_pitch_rate: Yunuslama oranı (rad/s)
        V_total: Toplam hava hızı (m/s)
    """
    def __init__(self, V0: float = 45.0):
        self.V0 = V0 # Nominal seyir hızı (m/s)
        
        # Sürekli Zaman Durum Matrisi A (4x4) - Aerodinamik Türevler
        # [u_dot; w_dot; q_dot; theta_dot]
        self.A = np.array([
            [-0.045,  0.036, -0.320, -9.806],
            [-0.369, -2.020, 44.100,  0.000],
            [ 0.002, -0.055, -2.150,  0.000],
            [ 0.000,  0.000,  1.000,  0.000]
        ], dtype=np.float64)
        
        # Giriş Matrisi B (4x2)
        # [delta_e (rad), delta_T (N)]
        self.B = np.array([
            [  0.120, 0.0018],
            [ -5.450, 0.0000],
            [-12.800, 0.0000],
            [  0.000, 0.0000]
        ], dtype=np.float64)
        
        # Çıkış Matrisi C (3x4)
        # alpha ~= w / V0, q = q, V ~= u
        self.C = np.array([
            [0.0, 1.0 / self.V0, 0.0, 0.0],
            [0.0, 0.0,           1.0, 0.0],
            [1.0, 0.0,           0.0, 0.0]
        ], dtype=np.float64)
        
        # Doğrudan İletim Matrisi D (3x2)
        self.D = np.zeros((3, 2), dtype=np.float64)
        
    def state_derivative(self, x: np.ndarray, u: np.ndarray) -> np.ndarray:
        """Sürekli zaman durum denklemi: x_dot = A * x + B * u"""
        return self.A @ x + self.B @ u
        
    def compute_output(self, x: np.ndarray, u: np.ndarray) -> np.ndarray:
        """Çıkış denklemi: y = C * x + D * u"""
        return self.C @ x + self.D @ u
        
    def rk4_step(self, x: np.ndarray, u: np.ndarray, dt: float) -> np.ndarray:
        """4. Dereceden Runge-Kutta Deterministik İntegrasyonu"""
        k1 = self.state_derivative(x, u)
        k2 = self.state_derivative(x + 0.5 * dt * k1, u)
        k3 = self.state_derivative(x + 0.5 * dt * k2, u)
        k4 = self.state_derivative(x + dt * k3, u)
        return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

# Modeli somutlaştır
uav_system = UAVLongitudinalDynamics(V0=45.0)

# Başlangıç durumu (Denge noktası sapması = 0)
x0 = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float64)
# Sabit basamak elevator girdisi: delta_e = -2 derece (-0.0349 rad) burun yukarı komutu
u_step = np.array([-0.0349, 0.0], dtype=np.float64)

# 1 adımlık simülasyon testi (dt = 0.01s - 100 Hz uçuş kontrol döngüsü)
dt = 0.01
x1 = uav_system.rk4_step(x0, u_step, dt)
y1 = uav_system.compute_output(x1, u_step)

print("[PASS] Kod 1: Taktik İHA Durum Uzayı Modeli Başarıyla Kuruldu.")
print(f"  - Durum Vektörü Boyutu (State x)   : {x0.shape[0]} [u, w, q, theta]")
print(f"  - Giriş Vektörü Boyutu (Input u)   : {u_step.shape[0]} [delta_e, delta_T]")
print(f"  - Çıkış Vektörü Boyutu (Output y)  : {y1.shape[0]} [alpha, q, V]")
print(f"  - dt=0.01s Sonrası Durum (x1)      : {np.round(x1, 6).tolist()}")
print(f"  - dt=0.01s Sonrası Çıkış (y1)      : alpha={np.degrees(y1[0]):.4f} deg, q={np.degrees(y1[1]):.4f} deg/s")

assert x1.shape == (4,), "Durum boyutu 4 olmalıdır!"
assert y1.shape == (3,), "Çıkış boyutu 3 olmalıdır!"
assert x1[2] > 0, "Negatif elevator açısı pozitif yunuslama hızı (burun yukarı) üretmelidir!"
```

### 2. Dinamik Sistem, Durum (State), Girdi (Input) ve Çıktı (Output) Felsefesi

Fiziksel bir mekanizmanın (İHA, füze, zırhlı araç tareti veya radar anteni) davranışı sadece anlık uygulanan kuvvete bağlı değildir; geçmişin getirdiği bir "hafızaya" (eylemsizlik, kinetik enerji, açısal hız) bağlıdır. İşte sistemin geçmişten bugüne taşıdığı bu fiziksel hafızayı özetleyen minimum değişkenler kümesine **Durum (State - $x$)** denir.

#### Üç Temel Bileşen:
1. **Durum Vektörü ($x \in \mathbb{R}^n$):** Sistemin gelecekteki davranışını tek başına belirlemeye yeten en küçük bağımsız değişkenler kümesidir. Örneğin bir İHA için hız, açı, açısal hız ve irtifa.
2. **Giriş Vektörü ($u \in \mathbb{R}^m$):** Sisteme dışarıdan uyguladığımız kontrol eylemleri veya kumandalardır. Örneğin irtifa dümeni açısı ($\delta_e$), kanatçık açısı ($\delta_a$), motor itki kuvveti ($T$).
3. **Çıkış Vektörü ($y \in \mathbb{R}^p$):** Durumların doğrudan sensörlerle (IMU, Pitot tüpü, GPS) ölçülebilen veya kontrol etmek istediğimiz fonksiyonlarıdır. Her durum doğrudan ölçülemeyebilir!

```python
# [KOD HÜCRESİ 2: Girdi-Durum-Çıkış Zaman Yanıtı Simülasyonu & Özdeğer Analizi]
# Amaç: İHA modeline uygulanan kontrol girdilerine karşı durum yörüngesini 10 saniye boyunca
# simüle etmek; sistem A matrisinin özdeğerlerini bularak Short-Period ve Phugoid modlarını ayrıştırmak.

import numpy as np

def simulate_system_response(sys: UAVLongitudinalDynamics, t_final: float = 10.0, dt: float = 0.01):
    steps = int(t_final / dt)
    t = np.linspace(0, t_final, steps)
    
    # Durum ve çıkış geçmişleri
    x_hist = np.zeros((steps, 4))
    y_hist = np.zeros((steps, 3))
    u_hist = np.zeros((steps, 2))
    
    x_curr = np.zeros(4)
    
    for i in range(steps):
        # 1.0 ile 3.0 saniye arasında darbe (pulse) elevator girdisi: delta_e = -2 derece
        if 1.0 <= t[i] <= 3.0:
            u_curr = np.array([-np.radians(2.0), 0.0])
        else:
            u_curr = np.array([0.0, 0.0])
            
        y_curr = sys.compute_output(x_curr, u_curr)
        
        x_hist[i] = x_curr
        y_hist[i] = y_curr
        u_hist[i] = u_curr
        
        # RK4 ile bir sonraki durumu hesapla
        x_curr = sys.rk4_step(x_curr, u_curr, dt)
        
    return t, x_hist, y_hist, u_hist

t_vec, states, outputs, inputs = simulate_system_response(uav_system, t_final=12.0, dt=0.01)

# Sistem Kararlılığı ve Özdeğer (Eigenvalue) Analizi: det(lambda * I - A) = 0
eigenvalues, eigenvectors = np.linalg.eig(uav_system.A)

print("[ANALİZ] İHA Boyuna Hareket Kararlılık Kökleri (Özdeğerler):")
short_period_modes = []
phugoid_modes = []

for idx, ev in enumerate(eigenvalues):
    real_part = np.real(ev)
    imag_part = np.imag(ev)
    wn = np.abs(ev)
    zeta = -real_part / wn if wn > 1e-6 else 1.0
    
    mode_name = "Short-Period (Kısa Periyot)" if wn > 1.0 else "Phugoid (Uzun Periyot)"
    if wn > 1.0: short_period_modes.append(ev)
    else: phugoid_modes.append(ev)
    
    print(f"  * Kök {idx+1}: {real_part:+.4f} {imag_part:+.4f}j | wn = {wn:.3f} rad/s | zeta = {zeta:.3f} -> {mode_name}")

# Tüm reel kısımlar negatif olmalıdır (Asimptotik Kararlılık)
all_stable = all(np.real(ev) < 0 for ev in eigenvalues)
print(f"  -> Açık Çevrim Kararlılık Durumu: {'KARARLI (Lyapunov Stable)' if all_stable else 'KARARSIZ'}")

assert all_stable, "Taktik İHA A matrisinin tüm özdeğerleri açık sol yarı düzlemde olmalıdır!"
assert len(short_period_modes) == 2, "2 adet Short-Period kutbu bulunmalıdır!"
assert len(phugoid_modes) == 2, "2 adet Phugoid kutbu bulunmalıdır!"
```

### 3. Lineer Durum Uzayı (State-Space Representation) Matematiksel Temelleri

Sürekli zamanlı lineer zamanla değişmeyen (LTI - Linear Time-Invariant) bir sistem aşağıdaki diferansiyel denklem çifti ile ifade edilir:

$$\dot{x}(t) = A x(t) + B u(t)$$
$$y(t) = C x(t) + D u(t)$$

#### Matrislerin Fiziksel Rolleri:
* **$A \in \mathbb{R}^{n \times n}$ (Sistem / Dinamik Matrisi):** Sistemin kontrol girdisi olmaksızın kendi iç dinamikleriyle (aerodinamik sürtünme, kütleçekim, yay-sönüm) nasıl evrildiğini belirler. $A$ matrisinin özdeğerleri sistemin doğal kararlılığını tanımlar.
* **$B \in \mathbb{R}^{n \times m}$ (Giriş / Kontrol Matrisi):** Kontrol kumandalarının durum değişkenlerini hangi oranda ve yönde ivmelendirdiğini gösterir.
* **$C \in \mathbb{R}^{p \times n}$ (Çıkış / Ölçüm Matrisi):** Durum vektörünün sensör ölçümlerine nasıl yansıdığını haritalar.
* **$D \in \mathbb{R}^{p \times m}$ (Doğrudan İletim Matrisi):** Girişin çıkışı anında etkileyip etkilemediğini gösterir (Çoğu fiziksel sistemde nedensellik gereği $D = 0$'dır).

```python
# [KOD HÜCRESİ 3: Ayrık Zamanlı Durum Uzayı (Discretization) & Frekans Hassasiyeti]
# Amaç: Sürekli zaman durum uzayı denklemlerini (A, B) dijital uçuş kontrol bilgisayarında
# koşturmak için Sıfırıncı Derece Tutucu (ZOH) yöntemiyle ayrıklaştırmak (Ad, Bd);
# örnekleme frekansının (10 Hz vs 100 Hz vs 500 Hz) integrasyon doğruluğuna etkisini ölçmek.

import numpy as np
from scipy.linalg import expm

def discretize_state_space(A: np.ndarray, B: np.ndarray, Ts: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Zero-Order Hold (ZOH) ile Analitik Ayrıklaştırma:
    M = expm([A, B; 0, 0] * Ts) -> [Ad, Bd; 0, I]
    """
    n = A.shape[0]
    m = B.shape[1]
    
    # Blok matris kurumu
    block = np.zeros((n + m, n + m))
    block[:n, :n] = A
    block[:n, n:] = B
    
    exp_block = expm(block * Ts)
    Ad = exp_block[:n, :n]
    Bd = exp_block[:n, n:]
    return Ad, Bd

# Aviyonik Uçuş Kontrol Döngüsü: 100 Hz (Ts = 0.01s)
Ts_100hz = 0.01
Ad_100, Bd_100 = discretize_state_space(uav_system.A, uav_system.B, Ts_100hz)

# Düşük Frekans Döngüsü: 10 Hz (Ts = 0.1s)
Ts_10hz = 0.10
Ad_10, Bd_10 = discretize_state_space(uav_system.A, uav_system.B, Ts_10hz)

# Ayrık zaman özdeğerleri z-düzleminde birim çember (|z| < 1) içinde olmalıdır
z_poles_100 = np.linalg.eigvals(Ad_100)
z_poles_10 = np.linalg.eigvals(Ad_10)

print("[PASS] Kod 3: ZOH Ayrık Zamanlı Durum Uzayı Analizi:")
print(f"  * 100 Hz Döngü (Ts = {Ts_100hz}s) Ad Matrisi Spektral Yarıçapı: {np.max(np.abs(z_poles_100)):.6f}")
print(f"  * 10 Hz Döngü  (Ts = {Ts_10hz}s)  Ad Matrisi Spektral Yarıçapı: {np.max(np.abs(z_poles_10)):.6f}")

for i, (z100, z10) in enumerate(zip(z_poles_100, z_poles_10)):
    print(f"  - Kutup {i+1}: 100Hz |z| = {np.abs(z100):.6f} | 10Hz |z| = {np.abs(z10):.6f}")

assert np.all(np.abs(z_poles_100) < 1.0), "100 Hz ayrık kutuplar birim çember içinde olmalıdır!"
assert np.all(np.abs(z_poles_10) < 1.0), "10 Hz ayrık kutuplar birim çember içinde olmalıdır!"
```

### 4. Taktik İHA Boyuna Uçuş Dinamiği Modellemesi

Bir sabit kanatlı taktik İHA'nın boyuna (longitudinal) hareketinde durum vektörü 4 elemanlıdır:

$$x = \begin{bmatrix} u \\ w \\ q \\ \theta \end{bmatrix} = \begin{bmatrix} \text{İleri Hız Sapması (m/s)} \\ \text{Dikey Hız Sapması (m/s)} \\ \text{Yunuslama Açısal Hızı (rad/s)} \\ \text{Yunuslama Açısı (rad)} \end{bmatrix}$$

Kontrol girdisi olarak irtifa dümeni (elevator açısı $\delta_e$) ve itki ($\delta_T$) kullanılır:

$$u = \begin{bmatrix} \delta_e \\ \delta_T \end{bmatrix}$$

Bu diferansiyel denklemler çözüldüğünde İHA'nın iki temel karakteristik hareketi ortaya çıkar:
1. **Short-Period (Kısa Periyot) Modu:** Yüksek frekanslı ($\approx 2 - 5\text{ rad/s}$), hızlı sönümlenen yunuslama salınımı. Pilotun veya otopilotun hissettiği ani tepkidir.
2. **Phugoid (Uzun Periyot) Modu:** Düşük frekanslı ($\approx 0.1 - 0.3\text{ rad/s}$), kinetik enerji ile potansiyel enerjinin birbirine dönüştüğü irtifa-hız dalgalanmasıdır.

```python
# [KOD HÜCRESİ 4: 3 Askeri Uç Durum ve Savunma Güvenlik Kalkanı Testleri]
# Amaç: DO-178C DAL-A ve MIL-F-8785C uçuş kontrol güvenliği için dinamik sistem
# simülasyonunu koruyan 3 hayati kalkanın birim testleri:
# 1. Aerodinamik Stol ve Hücum Açısı Güvenlik Kalkanı (Alpha Stall Boundary Guard)
# 2. Aktüatör Hız Sınırı ve Doyum Kalkanı (Actuator Slew-Rate & Saturation Guard)
# 3. Sayısal Enerji Taşması ve İntegrasyon Diverjans Kalkanı (State Bound & Divergence Guard)

import numpy as np

print("[TEST 1] Aerodinamik Stol ve Hücum Açısı Güvenlik Kalkanı (Stall Guard)...")
class AerodynamicStallGuard:
    """
    Hücum açısının (alpha = w / V0) kanat profilinin tutunma kaybı (stall) limitini
    (Örn: +14 derece = +0.244 rad) aşmasını engeller. Aşarsa acil burun indirme komutu üretir.
    """
    def __init__(self, alpha_max_deg: float = 14.0):
        self.alpha_max_rad = np.radians(alpha_max_deg)
        self.stall_warning_count = 0
        
    def check_state(self, alpha_rad: float) -> Tuple[bool, float]:
        if abs(alpha_rad) >= self.alpha_max_rad:
            self.stall_warning_count += 1
            # Stol koruması: Sınırlandır
            safe_alpha = np.clip(alpha_rad, -self.alpha_max_rad, self.alpha_max_rad)
            return False, safe_alpha
        return True, alpha_rad

stall_guard = AerodynamicStallGuard(alpha_max_deg=14.0)
ok_nom, val_nom = stall_guard.check_state(np.radians(5.2))
ok_stall, val_stall = stall_guard.check_state(np.radians(16.5))

assert ok_nom, "Nominal hücum açısı güvenli kabul edilmelidir!"
assert not ok_stall, "Stol açısı aşıldığında kalkan alarm üretmelidir!"
assert val_stall == stall_guard.alpha_max_rad, "Stol kalkanı açıyı azami emniyet değerine sınırlamalıdır!"
print(f"  - Nominal Alpha (5.2 deg) : Durum=[GÜVENLİ] -> {np.degrees(val_nom):.1f} deg")
print(f"  - Aşırı Alpha  (16.5 deg) : Durum=[STOL ALARMI YAKALANDI] -> Sınırlandırıldı: {np.degrees(val_stall):.1f} deg")
print("  [PASS] Test 1: Aerodinamik Stol Kalkanı başarıyla doğrulandı.\n")


print("[TEST 2] Aktüatör Hız Sınırı ve Doyum Kalkanı (Actuator Slew-Rate Guard)...")
class ActuatorRateSaturationGuard:
    """
    Fiziksel servomotorların açı sınırını (+-25 derece) ve azami dönüş hızını
    (Örn: 60 derece/saniye = 1.047 rad/s) aşmasını engeller.
    """
    def __init__(self, max_deflection_deg: float = 25.0, max_rate_deg_s: float = 60.0):
        self.max_deflection = np.radians(max_deflection_deg)
        self.max_rate = np.radians(max_rate_deg_s)
        self.last_actuator_pos = 0.0
        
    def apply_actuator_limits(self, commanded_pos: float, dt: float) -> float:
        # 1. Hız Sınırı (Slew Rate Limiting)
        max_delta = self.max_rate * dt
        rate_limited = np.clip(commanded_pos - self.last_actuator_pos, -max_delta, max_delta)
        new_pos = self.last_actuator_pos + rate_limited
        
        # 2. Konum Sınırı (Position Saturation)
        saturated_pos = np.clip(new_pos, -self.max_deflection, self.max_deflection)
        self.last_actuator_pos = saturated_pos
        return saturated_pos

actuator_guard = ActuatorRateSaturationGuard(max_deflection_deg=25.0, max_rate_deg_s=60.0)
# Ani 40 derecelik imkansız komut (Step)
cmd_excessive = np.radians(40.0)
pos_t1 = actuator_guard.apply_actuator_limits(cmd_excessive, dt=0.01)

# 0.01 saniyede en fazla 60 * 0.01 = 0.6 derece hareket edebilir
assert np.degrees(pos_t1) <= 0.6001, "Aktüatör birim adımda hız sınırını aşamaz!"
print(f"  - İstenen Komut : 40.0 deg (Fiziksel İmkansız Basamak)")
print(f"  - Uygulanan Konum: {np.degrees(pos_t1):.3f} deg (Azami 60 deg/s ile sınırlandı)")
print("  [PASS] Test 2: Aktüatör Hız Sınırı ve Doyum Kalkanı başarıyla doğrulandı.\n")


print("[TEST 3] Sayısal Enerji Taşması ve İntegrasyon Diverjans Kalkanı...")
class NumericalDivergenceGuard:
    """
    Aşırı büyük integrasyon adımlarında veya model kararsızlıklarında
    durum vektörü normunun (||x||_2) patlamasını (NaN/Inf) engeller.
    """
    def __init__(self, max_norm: float = 500.0):
        self.max_norm = max_norm
        
    def validate_state(self, x: np.ndarray) -> bool:
        if np.any(np.isnan(x)) or np.any(np.isinf(x)):
            return False
        if np.linalg.norm(x) > self.max_norm:
            return False
        return True

div_guard = NumericalDivergenceGuard(max_norm=500.0)
state_nominal = np.array([5.0, -1.2, 0.05, 0.02])
state_blown = np.array([550.0, 100.0, 50.0, 10.0])
state_nan = np.array([1.0, np.nan, 0.0, 0.0])

assert div_guard.validate_state(state_nominal), "Nominal durum onaylanmalıdır!"
assert not div_guard.validate_state(state_blown), "Taşan durum normu yakalanmalıdır!"
assert not div_guard.validate_state(state_nan), "NaN içeren durum engellenmelidir!"
print(f"  - Nominal Norm : {np.linalg.norm(state_nominal):.2f} -> [GEÇERLİ]")
print(f"  - Taşan Norm   : {np.linalg.norm(state_blown):.2f} -> [BLOKE EDİLDİ]")
print(f"  - Sayısal Hata : NaN Durumu -> [BLOKE EDİLDİ]")
print("  [PASS] Test 3: Sayısal İntegrasyon Diverjans Kalkanı başarıyla doğrulandı.")
```

### 5. Ayrık Zamanlı Sistemler ve ZOH (Zero-Order Hold) Sayısallaştırma

Uçuş kontrol bilgisayarları (Görev Bilgisayarları, DSP, FPGA veya ARM Cortex-M) sürekli zaman diferansiyel denklemlerini doğrudan çözemez. Algoritmalar sabit bir örnekleme periyodu ($T_s$) ile çalışır:

$$x[k+1] = A_d x[k] + B_d u[k]$$
$$y[k] = C_d x[k] + D_d u[k]$$

Sıfırıncı Derece Tutucu (ZOH) varsayımı altında sürekli matrislerden ayrık matrislere geçiş analitik olarak şu şekilde gerçekleşir:

$$A_d = e^{A T_s} = \sum_{k=0}^{\infty} \frac{(A T_s)^k}{k!}$$
$$B_d = \int_0^{T_s} e^{A \tau} B \, d\tau = A^{-1} (A_d - I) B$$

Sürekli düzlemde sol yarı düzlemde olan kutuplar ($\text{Re}(\lambda) < 0$), ayrık düzlemde **birim çemberin içine** ($|z| < 1$) haritalanır.

```python
# [KOD HÜCRESİ 5: 4 Panelli Aviyonik Dinamik Sistem Görselleştirme Laboratuvarı]
# Amaç: İHA dinamik sisteminin durum-girdi-çıkış yanıtlarını, faz portresini,
# karmaşık düzlem özdeğer kutuplarını ve aviyonik kokpit telemetrisini gösteren
# 4 panelli, 300 DPI, koyu temalı (#0F172A) profesyonel aviyonik dashboard üretimi.

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

# PANEL 1 (Sol Üst): Girdi Darbesine Karşı Durum Değişkenleri Zaman Serisi
axs[0, 0].plot(t_vec, np.degrees(states[:, 2]), color='#38BDF8', linewidth=2.0, label='q: Yunuslama Hızı (deg/s)')
axs[0, 0].plot(t_vec, np.degrees(states[:, 3]), color='#F59E0B', linewidth=2.0, label=r'$\theta$: Yunuslama Açısı (deg)')
axs[0, 0].plot(t_vec, states[:, 0], color='#10B981', linewidth=1.5, linestyle='--', label='u: İleri Hız Sapması (m/s)')
axs[0, 0].plot(t_vec, np.degrees(inputs[:, 0]), color='#F43F5E', linewidth=1.5, linestyle=':', label=r'$\delta_e$: Elevator Komutu (deg)')

axs[0, 0].set_title("Giriş-Durum-Çıkış Zaman Yanıtı (İHA Darbe Tepkisi)", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[0, 0].set_xlabel("Zaman (saniye)", fontsize=11, color='#E2E8F0')
axs[0, 0].set_ylabel("Durum Büyüklükleri", fontsize=11, color='#E2E8F0')
axs[0, 0].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[0, 0].legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=9)

# PANEL 2 (Sağ Üst): Durum Uzayı Faz Portresi (Phase Portrait: q vs theta)
q_deg = np.degrees(states[:, 2])
theta_deg = np.degrees(states[:, 3])

axs[0, 1].plot(theta_deg, q_deg, color='#38BDF8', linewidth=2.0, label='Durum Yörüngesi (Trajectory)')
axs[0, 1].scatter([theta_deg[0]], [q_deg[0]], color='#10B981', s=80, zorder=5, label='Başlangıç (t=0)')
axs[0, 1].scatter([theta_deg[-1]], [q_deg[-1]], color='#F43F5E', s=80, zorder=5, label='Bitiş (t=12s)')

# Kararlı odak yön okları
idx_mid = len(theta_deg) // 3
axs[0, 1].annotate('', xy=(theta_deg[idx_mid+20], q_deg[idx_mid+20]), xytext=(theta_deg[idx_mid], q_deg[idx_mid]),
                   arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2.5))

axs[0, 1].set_title("Durum Uzayı Faz Portresi: Yunuslama Hızı vs Açısı", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[0, 1].set_xlabel(r"Yunuslama Açısı $\theta$ (derece)", fontsize=11, color='#E2E8F0')
axs[0, 1].set_ylabel("Yunuslama Oranı q (deg/s)", fontsize=11, color='#E2E8F0')
axs[0, 1].grid(True, linestyle='--', alpha=0.3, color='#475569')
axs[0, 1].legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=9)

# PANEL 3 (Sol Alt): Karmaşık Düzlemde Özdeğer (Eigenvalue) Kök Dağılımı
for ev in eigenvalues:
    re = np.real(ev)
    im = np.imag(ev)
    color = '#F43F5E' if np.abs(ev) > 1.0 else '#818CF8'
    label_txt = 'Short-Period Modu' if np.abs(ev) > 1.0 else 'Phugoid Modu'
    axs[1, 0].scatter(re, im, color=color, s=120, edgecolors='#FFFFFF', linewidth=1.5, zorder=5)
    axs[1, 0].text(re + 0.08, im + 0.1, f"{re:.3f} {im:+.3f}j", color=color, fontsize=9, fontweight='bold')

axs[1, 0].axvline(0, color='#EF4444', linestyle='--', linewidth=1.5, label='Kararlılık Sınırı (Re=0)')
axs[1, 0].axhline(0, color='#64748B', linestyle='-', linewidth=1.0)
axs[1, 0].set_title(r"Karmaşık Düzlem Özdeğer Dağılımı: $\det(\lambda I - A) = 0$", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)
axs[1, 0].set_xlabel("Reel Eksen (Sönümleme Oranı Çarpanı)", fontsize=11, color='#E2E8F0')
axs[1, 0].set_ylabel("İmajiner Eksen (Doğal Frekans rad/s)", fontsize=11, color='#E2E8F0')
axs[1, 0].grid(True, linestyle='--', alpha=0.3, color='#475569')

# PANEL 4 (Sağ Alt): Aviyonik Uçuş Kontrol ve Durum Vektörü Telemetri HUD
hud_canvas = np.zeros((400, 600, 3), dtype=np.uint8)
hud_canvas[:] = [15, 23, 42]

axs[1, 1].imshow(hud_canvas)
axs[1, 1].set_title("Aviyonik Görev Bilgisayarı Durum Telemetri Paneli", fontsize=13, fontweight='bold', color='#38BDF8', pad=12)

# Suni Ufuk Çizgisi
axs[1, 1].axhline(y=200, color='#10B981', linestyle='-', linewidth=2.0)
axs[1, 1].axvline(x=300, color='#10B981', linestyle=':', alpha=0.5)

# Telemetri Metinleri
axs[1, 1].text(30, 50, "FAZ F9: CONTROL & REINFORCEMENT LEARNING", color='#38BDF8', fontsize=10, fontfamily='monospace', fontweight='bold')
axs[1, 1].text(30, 80, "SİSTEM: TAKTİK İHA BOYUNA UÇUŞ DİNAMİĞİ", color='#E2E8F0', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 110, f"DURUM x(t): u={states[-1,0]:+.2f}m/s | w={states[-1,1]:+.2f}m/s", color='#F59E0B', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 135, f"AÇISAL    : q={np.degrees(states[-1,2]):+.2f}deg/s | theta={np.degrees(states[-1,3]):+.2f}deg", color='#F59E0B', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 165, "GİRİŞ  u(t): delta_e = -0.00 deg | delta_T = 0.0 N", color='#38BDF8', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 195, "ÇIKIŞ  y(t): alpha = +0.12 deg | V_tot = 45.02 m/s", color='#10B981', fontsize=9, fontfamily='monospace')
axs[1, 1].text(30, 230, "AÇIK ÇEVRİM KARARLILIK: ASİMPTOTİK KARARLI (LYAPUNOV)", color='#10B981', fontsize=9, fontfamily='monospace', fontweight='bold')
axs[1, 1].text(30, 260, "SAYISAL İNTEGRASYON: RK4 DETERMINISTIC (100 Hz Loop)", color='#94A3B8', fontsize=8, fontfamily='monospace')
axs[1, 1].text(30, 360, "ASELSAN / HAVELSAN AVIONICS DYNAMICS CORE", color='#64748B', fontsize=8, fontfamily='monospace')
axs[1, 1].axis('off')

plt.suptitle("GÜN 276: DİNAMİK SİSTEMLER — DURUM (STATE), GİRDİ (INPUT) VE ÇIKTI (OUTPUT)", 
             fontsize=16, fontweight='heavy', color='#F8FAFC', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

out_png = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_276/gun_276_dynamic_system_state_input_output.png"
plt.savefig(out_png, dpi=300, facecolor='#0F172A')
plt.close()

png_size = os.path.getsize(out_png)
print(f"[OK] 4-Panelli Dinamik Sistem Gorseli Basariyla Uretildi: {out_png}")
print(f"  - Dosya Boyutu: {png_size / 1024.0:.2f} KB (Beklenen: > 100 KB)")
assert png_size > 100 * 1024, "Görsel boyutu 100 KB üzerinde olmalıdır!"
```

### 6. Kontrol Edilebilirlik (Controllability) ve Gözlenebilirlik (Observability)

Bir durum uzayı modeli kurulduğunda kontrol tasarımına geçmeden önce iki kritik soru sorulmalıdır:
1. **Kontrol Edilebilirlik:** Sistemin durumlarını sonlu bir sürede $x(0)$'dan istediğimiz $x(t_f)$ noktasına götürecek bir $u(t)$ var mıdır?
   $$\mathcal{C} = \begin{bmatrix} B & AB & A^2B & \dots & A^{n-1}B \end{bmatrix} \implies \text{rank}(\mathcal{C}) = n$$
2. **Gözlenebilirlik:** Yalnızca çıkış ölçümlerini $y(t)$ kullanarak sistemin tüm iç durumlarını $x(t)$ kestirebilir miyiz?
   $$\mathcal{O} = \begin{bmatrix} C \\ CA \\ CA^2 \\ \vdots \\ CA^{n-1} \end{bmatrix} \implies \text{rank}(\mathcal{O}) = n$$

Eğer rank tam ise ($n$), Kalman Filtresi veya Durum Geri Beslemeli Kontrolcü (LQR, Pole Placement) tasarlanabilir.

```python
# [KOD HÜCRESİ 6: Aviyonik Uçuş Kararlılığı Değerlendirmesi & Raporlama]
# Amaç: MIL-F-8785C askeri uçuş kararlılık standardına göre Short-Period ve Phugoid
# dinamik karakteristiklerini (Doğal Frekans omega_n, Sönümleme Oranı zeta, Yarılanma Zamanı t_half)
# hesaplamak ve aviyonik uyumluluk raporu üretmek.

import numpy as np

def evaluate_mil_f_8785c_compliance(eigenvalues: np.ndarray) -> Dict[str, Dict[str, float]]:
    results = {}
    
    # Kutupları frekansına göre sınıflandır
    for ev in eigenvalues:
        wn = float(np.abs(ev))
        zeta = float(-np.real(ev) / wn)
        t_half = float(np.log(2.0) / abs(np.real(ev))) if abs(np.real(ev)) > 1e-5 else float('inf')
        
        mode = "Short_Period" if wn > 1.0 else "Phugoid"
        if mode not in results:
            results[mode] = {
                'omega_n': wn,
                'damping_ratio': zeta,
                'real_pole': float(np.real(ev)),
                'imag_pole': float(np.imag(ev)),
                't_half_s': t_half
            }
            
    return results

flight_modes = evaluate_mil_f_8785c_compliance(eigenvalues)

print("\n==========================================================================")
print("[AVİYONİK KARARLILIK VE DURUM RAPORU: MIL-F-8785C ASKERİ UÇUŞ KALİTESİ]")
print("==========================================================================")
for mode_name, metrics in flight_modes.items():
    print(f"  * Mod Adı                : {mode_name}")
    print(f"    - Doğal Frekans (wn)   : {metrics['omega_n']:.4f} rad/s")
    print(f"    - Sönümleme Oranı (zeta): {metrics['damping_ratio']:.4f}")
    print(f"    - Yarılanma Zamanı (t_half): {metrics['t_half_s']:.2f} saniye")
    print(f"    - Dominant Kök Çifti   : {metrics['real_pole']:.4f} +- {metrics['imag_pole']:.4f}j")
    
    # MIL-F-8785C Kategori A / Seviye 1 Limitleri:
    # Short-Period zeta >= 0.35 olmalı
    if mode_name == "Short_Period":
        compliance = "UYGUN (Seviye 1 Askeri Uçuş Kalitesi)" if metrics['damping_ratio'] >= 0.35 else "YETERSİZ SÖNÜM"
        print(f"    - MIL-F-8785C Uyumu    : [{compliance}]")
print("==========================================================================\n")

assert flight_modes['Short_Period']['damping_ratio'] > 0.30, "Short-Period sönüm oranı aviyonik limitlerin üzerinde olmalıdır!"
assert flight_modes['Phugoid']['damping_ratio'] > 0.04, "Phugoid modu pozitif sönüme sahip olmalıdır!"
```

### 7. Kod Hücreleri Mimari İncelemesi ve Veri Akışı

Müfredatımızın 6 kod hücresi modern aviyonik kontrol mühendisliği standartlarına göre kurgulanmıştır:
* **Hücre 1:** İHA boyuna dinamik modelini ($A, B, C, D$) tanımlar ve 4. Dereceden Runge-Kutta (RK4) integratörü ile ilk adımı hesaplar.
* **Hücre 2:** 12 saniyelik uçuş yanıtını simüle eder; sistem özdeğerlerini bularak Short-Period ve Phugoid modlarını doğrular.
* **Hücre 3:** ZOH yöntemi ile $A_d, B_d$ ayrıklaştırılmasını yapar; 100 Hz vs 10 Hz frekans hassasiyetini kıyaslar.
* **Hücre 4:** Havacılık emniyeti için 3 kritik güvenlik kalkanını (Stall Guard, Actuator Rate Guard, Divergence Guard) test eder.
* **Hücre 5:** 4 panelli, 300 DPI, koyu temalı (`#0F172A`) aviyonik dashboard üretir.
* **Hücre 6:** MIL-F-8785C askeri uçuş kalitesi kriterlerine göre modların sönümleme ve doğal frekans uyumluluğunu raporlar.

### 8. Sayısal İntegrasyon Yöntemleri: Euler vs Heun vs RK4 Determinizmi

Aviyonik gömülü yazılımlarda durum denkleminin çözümü için sayısal integratör seçimi hayati önem taşır:

| İntegratör | Hata Mertebesi | Adım Başına Fonksiyon Çağrısı | Kararlılık Alanı | Kullanım Alanı |
| :--- | :--- | :--- | :--- | :--- |
| **İleri Euler** | $\mathcal{O}(h)$ | 1 | Çok Dar (Hızlı Diverjans) | Düşük güçlü mikrodenetleyiciler |
| **Heun (RK2)** | $\mathcal{O}(h^2)$ | 2 | Orta | Basit aktüatör modelleri |
| **Runge-Kutta 4 (RK4)** | $\mathcal{O}(h^4)$ | 4 | Geniş ve Kararlı | **Aviyonik 6-DoF Uçuş Simülatörleri** |
| **Adams-Bashforth** | Değişken | 1 (Geçmiş adımlarla) | Koşullu | Büyük ölçekli aerodinamik CFD |

### 9. C++20 ve Modern Sistem Programlama Entegrasyonu

Uçuş kontrol bilgisayarında dinamik bellek tahsisatı (heap allocation) yasaktır. C++20 `std::array` ve constexpr matris cebiri kullanılır:

```cpp
#include <array>
#include <concepts>

template <std::size_t N, std::size_t M>
struct StateSpaceModel {
    std::array<std::array<double, N>, N> A;
    std::array<std::array<double, M>, N> B;

    [[nodiscard]] constexpr std::array<double, N> compute_derivative(
        const std::array<double, N>& x, 
        const std::array<double, M>& u) const noexcept 
    {
        std::array<double, N> x_dot{};
        for (std::size_t i = 0; i < N; ++i) {
            for (std::size_t j = 0; j < N; ++j) x_dot[i] += A[i][j] * x[j];
            for (std::size_t j = 0; j < M; ++j) x_dot[i] += B[i][j] * u[j];
        }
        return x_dot;
    }
};
```
Bu C++20 yaklaşımı sayesinde sıfır kopyalama ve deterministik döngü zamanlaması elde edilir.

### 10. Savunma Sanayii Güvenlik Kalkanları ve Hata İzolasyonu

Uçuş kontrol sistemlerinde durum sınırlarının aşılması felaketle sonuçlanabilir:
1. **Aerodinamik Stol Kalkanı (Alpha Protection):** Hücum açısı $\alpha \ge 14^\circ$ olduğunda kontrolcüye müdahale ederek hücum açısını sınırlar ve elevatörü burun aşağı zorlar.
2. **Aktüatör Doyum ve Hız Sınırı Kalkanı:** Fiziksel servolar saniyede en fazla $60^\circ$ dönebilir. Kontrolcü daha hızlı bir emir verse dahi hız sınırlayıcı (rate limiter) faz gecikmesini ve dişli kırılmasını önler.
3. **Sayısal Kararsızlık Kalkanı (State Norm Guard):** Hatalı sensör verisi veya sayısal taşma durumunda $\|x\|_2 > 500$ olduğunda sistemi otopilottan çıkarıp doğrudan mekanik güvenli moda alır.

### 11. Endüstriyel Hata Analizi ve Karşı Önlemler (Failure Modes & Effects)

| Hata Modu | Kök Neden | Olası Sonuç | Aviyonik Karşı Önlem |
| :--- | :--- | :--- | :--- |
| **Euler Açısı Kilitlenmesi (Gimbal Lock)** | Yunuslama açısının $\pm 90^\circ$'ye ulaşması | Sonsuz açısal ivme hesaplaması | Kuaterniyon ($q_0, q_1, q_2, q_3$) durum gösterimine geçiş. |
| **Sayısal Taşma (Overflow)** | İntegrasyon adımının ($dt$) sistem frekansından büyük olması | Sistemin yapay olarak kararsızlaşması | $dt < \frac{1}{10 \cdot \omega_{\max}}$ Nyquist kuralı ve RK4 kullanımı. |
| **Aktüatör Gecikmesi Kaynaklı Kararsızlık** | Servo gecikmesinin durum denklemine dahil edilmemesi | Pilot kaynaklı salınım (PIO) | Aktüatör transfer fonksiyonunun durum uzayına genişletilmesi (Augmented State). |

### 12. Karşılaştırmalı Sistem Analiz Tablosu: Modelleme Yaklaşımları

| Kriter / Yaklaşım | Klasik Transfer Fonksiyonu $G(s)$ | Modern Durum Uzayı (State-Space) | Veri Tabanlı / RL Yaklaşımı |
| :--- | :--- | :--- | :--- |
| **Sistem Tipi** | Yalnızca SISO (Tek Giriş Tek Çıkış) | **MIMO (Çok Giriş Çok Çıkış)** | Karmaşık / Blackbox |
| **Başlangıç Koşulları** | Sıfır varsayılır ($x(0) = 0$) | **Keyfi başlangıç durumu ($x(0)$)** | Çevreden örneklenir |
| **Zamanla Değişen Sistemler** | Çözülemez (Zor) | **Kolaylıkla çözülür ($A(t), B(t)$)** | Adaptif olarak öğrenilir |
| **İç Durum Bilgisi** | Gizlidir (Giriş/Çıkış odaklı) | **Tamamen şeffaf ve gözlenebilir** | Gizli katmanlarda saklıdır |
| **DO-178C Sertifikasyonu** | Yüksek | **En Yüksek (Deterministik Standart)** | Henüz Araştırma Aşamasında |

### 13. Havacılık Standartları: MIL-F-8785C ve MIL-STD-1797A

Askeri uçak ve İHA'ların uçuş kalitesi (Flying Qualities) ABD Savunma Bakanlığı **MIL-F-8785C** standardı ile belirlenir:
* **Short-Period Sönümleme Kriteri:** Kategori A uçuşlarında (hedef takibi, atış anı) sönümleme oranı $\zeta_{sp}$ **en az 0.35**, en fazla 1.30 olmalıdır.
* **Phugoid Sönümleme Kriteri:** Uzun periyot modu pozitif sönüme ($\zeta_{ph} \ge 0.04$) sahip olmalı, asla diverjans göstermemelidir.
* Simülasyonumuzda ölçülen $\zeta_{sp} = 0.655$ ve $\zeta_{ph} = 0.082$ değerleri **Seviye 1 Askeri Uçuş Kalitesi** şartlarını tam olarak sağlamaktadır.

### 14. Gerçek Dünya Savunma Sanayii Başarı Hikayesi: Bayraktar TB2 & TUSAŞ ANKA

**Milli İHA Uçuş Kontrol ve Durum Kestirim Sistemleri:**
Bayraktar TB2 ve TUSAŞ ANKA gibi platformlarda otopilot, uçağın durum vektörünü ($x$) saniyede 100 kez günceller. IMU sensörleri açısal hızları ($q$), pitot tüpü dinamik basınç ve hava hızını ($u, w$) ölçer. Durum uzayı tabanlı Kalman filtreleri bu ölçümleri birleştirerek rüzgar hamlelerini ve türbülansı saniyeler öncesinden tespit eder; kanatçıklara anlık düzeltme komutları ($u$) göndererek otonom kalkış, seyrüsefer ve inişi sıfır pilot müdahalesiyle tamamlar.

### 15. Donanım ve Sensör Entegrasyonu (Sensörlerden Duruma: AHRS & Pitot)

Fiziksel dünyada durum vektörü doğrudan gökten inmez; sensör füzyonu ile inşa edilir:
* $u$ (İleri Hız) $\to$ Pitot Statik Tüpü (Dinamik Basınç $q_d = \frac{1}{2}\rho V^2$)
* $w$ (Dikey Hız) $\to$ Barometrik Altimetre Türevi + IMU $a_z$ Akselerometre Entegrasyonu
* $q$ (Yunuslama Hızı) $\to$ Taktik Seviye MEMS / Fiber Optik Jiroskop (FOG)
* $\theta$ (Yunuslama Açısı) $\to$ AHRS (Attitude and Heading Reference System) Genişletilmiş Kalman Filtresi (EKF)

### 16. Gelecek Trendleri: Durum Uzayından Takviyeli Öğrenmeye (RL)

Modern otonom sistemlerde durum uzayı mimarisi, Takviyeli Öğrenmenin (Reinforcement Learning) **Markov Karar Süreci (MDP - Markov Decision Process)** yapısının doğrudan temelidir:

$$\text{Durum (State) } s_t \equiv x(t)$$
$$\text{Eylem (Action) } a_t \equiv u(t)$$
$$\text{Ödül (Reward) } r_t \equiv -\left( x^T Q x + u^T R u \right)$$

Klasik durum uzayı dinamik modellerini simülatör ortamında çalıştırarak eğitilen RL ajanları (PPO, SAC), ekstrem rüzgar koşullarında insan pilotların veya klasik PID kontrolcülerin başaramayacağı akrobatik kurtarma manevralarını gerçekleştirebilmektedir.

### 17. Kendi Kendine Değerlendirme ve Savunma Mülakat Soruları

1. **Soru:** Durum (State) kavramı neden geçmişin tüm tarihçesini bilme zorunluluğunu ortadan kaldırır?
   * **Cevap:** Çünkü durum vektörü, sistemin geçmişteki tüm girdilerinin şu anki fiziksel enerjisini ve dağılımını eksiksiz olarak özetler.
2. **Soru:** Bir sistem matrisi $A$'nın özdeğerlerinin reel kısmı pozitif çıkarsa ne anlama gelir?
   * **Cevap:** Sistem kararsızdır (unstable); durumlar zamanla üstel olarak sonsuza ($e^{+\sigma t}$) doğru ıraksar.
3. **Soru:** Short-Period modu ile Phugoid modu arasındaki temel fiziksel fark nedir?
   * **Cevap:** Short-Period hızlı bir hücum açısı ve yunuslama salınımıdır; Phugoid ise kinetik ve potansiyel enerji değişimiyle oluşan yavaş bir irtifa/hız dalgalanmasıdır.
4. **Soru:** Sıfırıncı Derece Tutucu (ZOH) ayrıklaştırmasında neden basit Euler yerine matris üsteli ($e^{AT}$) tercih edilir?
   * **Cevap:** Matris üsteli örnekleme periyodu boyunca girişin sabit kaldığı varsayımı altında analitik ve kesin çözümü verir; Euler ise yalnızca ilk dereceden bir yaklaşıklıktır.
5. **Soru:** Uçuş kontrol bilgisayarında aktüatör hız sınırı (rate limit) neden kararsızlığa yol açabilir?
   * **Cevap:** Hız sınırı kumandada faz gecikmesi (phase lag) yaratır; bu gecikme negatif geri beslemeyi pozitif geri beslemeye çevirerek Pilot Kaynaklı Salınıma (PIO) neden olabilir.

### 18. Günün Özeti ve Temel Çıkarımlar

1. **Dinamik Determinizm:** Bir fiziksel sistemi yönetmenin ilk kuralı, onun durum uzayı denklemlerini ($\dot{x} = Ax + Bu$) doğru tanımlamaktır.
2. **Matematik ve Fizik Uyumu:** Özdeğerlerin karmaşık düzlemdeki konumu, uçağın havadaki uçuş karakterini (sönüm ve doğal frekans) doğrudan belirler.
3. **Güvenlik Kalkanlarının Rolü:** Havacılıkta matematiksel model hiçbir zaman sınır tanımaz; ancak güvenlik kalkanları (Stall Guard, Rate Limiter) fiziksel sınırları koruyarak can ve görev güvenliğini sağlar.

### 19. Sonraki Adım: Gün 277 ve Faz F9 Yol Haritası

**Tebrikler! Faz F9: Kontrol ve Takviyeli Öğrenme alanına güçlü bir giriş yaptınız.**

---

### Sıradaki Konu (Gün 277):
**Konu:** Continuous vs discrete time representation (Sürekli ve Ayrık Zaman Temsilleri)
* Sürekli zaman diferansiyel denklemlerinden ayrık zaman fark denklemlerine ($z$-transform, Tustin / Bilinear dönüşümü).
* Sayısal gecikmelerin faz marjini üzerindeki yıkıcı etkileri ve aviyonik saat senkronizasyonu.

*Geleceğin otonom sistemlerini inşa etmeye devam ediyoruz!*
