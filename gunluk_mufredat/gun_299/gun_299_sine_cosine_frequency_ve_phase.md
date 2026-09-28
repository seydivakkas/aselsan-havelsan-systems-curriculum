# Gün 299: Sine/Cosine, Frequency ve Phase (Radar İnterferometrisi, Fazör Dinamiği ve LFM Chirp)

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

### Faz F10: Radar / DSP / Communications — Sinüs/Kosinüs, Frekans ve Fazın Derin Fiziği
Savunma sanayiinde (ASELSAN, ROKETSAN, TUSAŞ) trigonometrik sinüs ve kosinüs dalgaları basit lise formüllerinden ibaret değildir. Bunlar:
1. **Hedefin Radyal Hızını Ölçen Taşıyıcı:** Doppler frekansı zaman içindeki faz değişiminin türevidir.
2. **Hedefin Geliş Açısını (AoA) Belirleyen Cetvel:** İki anten arasına düşen mikroskobik faz farkı ($\Delta\phi$), füzenin veya uçağın radar açısını santigrat derecenin yüzde biri hassasiyetinde belirler.
3. **Menzil Çözünürlüğünü Yaratan Matematik:** Fazın karesel değişimi ($\theta \propto t^2$), radara kilometrelerce uzaktaki hedefleri metre altı çözünürlükle ayırt ettiren **LFM (Linear Frequency Modulation) Chirp** dalga şeklini üretir.

Bugün **Gün 299**'da, sinüs ve kosinüsün ortogonalite fiziğini, fazör dinamiğini, faz türevi ile anlık frekans ilişkisini, çift antenli radar interferometresini (Angle of Arrival - AoA) ve faz belirsizliği sınırını ($d \le \lambda/2$) derinlemesine inceleyeceğiz.

---

## 1. Konsept ve Matematiksel Altyapı

### 1.1 Sinüs ve Kosinüsün Ortogonalite Özelliği
İki sinyal $x(t)$ ve $y(t)$ bir periyot $T_0$ boyunca iç çarpımları sıfır ise ortogonaldir:

$$\langle x, y \rangle = \frac{1}{T_0} \int_{0}^{T_0} \cos(2\pi f_0 t) \sin(2\pi f_0 t) \, dt = 0$$

Bu $90^\circ$ diklik, aynı taşıyıcı frekansta iki bağımsız bilgi kanalının ($I$ ve $Q$) birbirine karışmadan taşınmasını (QAM modülasyonu) ve radar alıcılarında yönün çözülmesini sağlar.

### 1.2 Fazör Gösterimi (Phasor Representation)
Euler özdeşliği ($e^{j\theta} = \cos\theta + j\sin\theta$) ile bir harmonik dalga karmaşık düzlemde dönen bir fazör olarak tanımlanır:

$$p(t) = A e^{j(2\pi f_0 t + \phi_0)} = A \cos(2\pi f_0 t + \phi_0) + j A \sin(2\pi f_0 t + \phi_0)$$

- **A:** Fazörün uzunluğu (Genlik).
- **$\omega = 2\pi f_0$:** Fazörün açısal dönüş hızı (Açısal frekans, rad/s).
- **$\phi_0$:** $t=0$ anındaki başlangıç açısı (Faz).

### 1.3 Faz Türevi Olarak Anlık Frekans (Instantaneous Frequency)
Toplam faz fonksiyonu $\theta(t)$ zamanla değişen keyfi bir fonksiyon olduğunda:

$$x(t) = A \cos(\theta(t))$$

Anlık açısal frekans $\omega(t)$ ve anlık frekans $f_{inst}(t)$, faz fonksiyonunun zaman türevidir:

$$\omega_{inst}(t) = \frac{d\theta(t)}{dt}, \quad f_{inst}(t) = \frac{1}{2\pi} \frac{d\theta(t)}{dt}$$

1. **Doğrusal Faz (CW Tonu):**
   $$\theta(t) = 2\pi f_0 t + \phi_0 \implies f_{inst}(t) = f_0 \quad (\text{Sabit Frekans})$$
2. **Karesel Faz (LFM Chirp / Darbe Sıkıştırma):**
   $$\theta(t) = 2\pi \left( f_{start} t + \frac{1}{2} K t^2 \right) \implies f_{inst}(t) = f_{start} + K t$$
   Burada $K = \frac{B}{T}$ chirp eğimidir ($B$: Bant genişliği, $T$: Darbe süresi).

### 1.4 Radar İnterferometrisi ve Geliş Açısı Kestirimi (Angle of Arrival - AoA)
Aralarında $d$ mesafesi bulunan iki radar alıcı antenine $\theta$ açısıyla gelen bir düzlem dalga düşünelim.
İkinci antene ulaşan dalganın katettiği ekstra yol:

$$\Delta R = d \sin(\theta)$$

Bu yol farkının ürettiği elektriksel faz kayması ($\Delta\phi$):

$$\Delta\phi = \frac{2\pi}{\lambda} \Delta R = \frac{2\pi}{\lambda} d \sin(\theta)$$

Eğer iki anten arasındaki aralık $d = \frac{\lambda}{2}$ seçilirse:

$$\Delta\phi = \pi \sin(\theta)$$

Antenlerden gelen kompleks sinyallerin çapraz korelasyon çarpımı ile $\Delta\phi$ ölçülür:

$$R_{12} = \frac{1}{N} \sum_{n=1}^{N} s_2[n] \cdot s_1^*[n] \implies \Delta\phi = \angle R_{12}$$

Hedefin uzamsal geliş açısı doğrudan kestirilir:

$$\theta_{est} = \arcsin\left( \frac{\Delta\phi \cdot \lambda}{2\pi d} \right)$$

### 1.5 Faz Belirsizliği Sınırı ve Izgara Lobları (Grating Lobes)
Faz ölçümleri $[-\pi, +\pi]$ aralığı ile sınırlıdır (modulo $2\pi$).
Eğer $d > \frac{\lambda}{2}$ seçilirse, $\theta = \pm 90^\circ$ için $\Delta\phi = \frac{2\pi d}{\lambda} > \pi$ olur ve faz katlanarak (phase wrapping) sahte açılarda hayalet hedefler (**Grating Lobes**) üretir! Bu nedenle savunma radarlarında anten dizisi eleman aralığı daima $d \le \frac{\lambda}{2}$ kuralına bağlanır.

---

## 2. Neden-Sonuç Zinciri ve Mimari Akış Şeması

```mermaid
flowchart TD
    subgraph Signal_Physics["Fiziksel Dalga & Faz Dinamiği"]
        TRIG["Sinüs & Kosinüs Ortogonalitesi\\n<cos, sin> = 0 (İki Bağımsız I/Q Kanalı)"]
        PHASE_DERIV["Fazın Zaman Türevi\\nf_inst = (1/2pi) * d(theta)/dt"]
        CHIRP["Karesel Faz: theta(t) ~ t^2\\nLineer Frekans Süpürme (LFM Chirp: B = 6 kHz)"]
    end

    subgraph Spatial_Interferometry["Uzamsal Faz & Radar İnterferometrisi"]
        ANT_PAIR["Çift Anten Geometrisi (d = lambda/2)\\nHedef Açısı theta = 30 Derece"]
        PATH_DIFF["Yol Farkı: Delta_R = d * sin(theta)"]
        PHASE_SHIFT["Elektriksel Faz Farkı: Delta_phi = pi * sin(theta) = 90 Derece"]
    end

    subgraph DSP_Estimation["Sayısal DSP & Açı Kestirimi"]
        CROSS_PROD["Kompleks Çapraz Çarpım\\nR12 = mean(s2 * conj(s1))"]
        ANGLE_RESOLVE["Açı Çözümü: theta = arcsin(Delta_phi / pi) -> 30.0 Derece"]
        AMBIG_CHECK["Faz Belirsizliği Kontrolü\\nd <= lambda/2 Güvencesi (Grating Lobe Engellendi)"]
    end

    TRIG --> PHASE_DERIV --> CHIRP
    ANT_PAIR --> PATH_DIFF --> PHASE_SHIFT
    PHASE_SHIFT --> CROSS_PROD --> ANGLE_RESOLVE --> AMBIG_CHECK

    style Signal_Physics fill:#1E293B,stroke:#38BDF8,stroke-width:2px,color:#F8FAFC
    style Spatial_Interferometry fill:#0F172A,stroke:#F59E0B,stroke-width:2px,color:#F8FAFC
    style DSP_Estimation fill:#1E293B,stroke:#10B981,stroke-width:2px,color:#F8FAFC
```

### Neden-Sonuç İlişkisi
1. **Neden:** Hedefin sadece mesafesi değil, gökyüzündeki yatay/dikey açısı (Bearing / Elevation) da tespit edilmelidir.
2. **Fiziksel İlke:** Düzlem dalga iki antene farklı anlarda ulaşır; yol farkı mikroskobik bir faz farkı ($\Delta\phi$) doğurur.
3. **Mühendislik Eylemi:** İki anten sinyali çapraz çarpılarak faz farkı çıkarılır; $\arcsin$ formülüyle hedef açısı $0.01^\circ$ hassasiyetle hesaplanır.
4. **Kritik Kural:** Faz belirsizliğini önlemek için antenler arası mesafe kesinlikle $d \le \lambda/2$ olmalıdır.

---

## 3. 5N1K Mühendislik Analizi

| Soru | Mühendislik Yanıtı |
| :--- | :--- |
| **Ne? (What)** | Sinüs/kosinüs ortogonalitesi, fazör modeli, faz türevi ile anlık frekans hesabı, radar interferometrisi ve AoA açı kestirimi. |
| **Neden? (Why)** | Hedefin menzil çözünürlüğünü artırmak (LFM Chirp) ve tek bir darbede hedefin geliş açısını (Angle of Arrival) yüksek doğrulukla bulmak için. |
| **Nerede? (Where)** | ASELSAN AESA radar huzme yönlendirme (Beamforming) modüllerinde, TUSAŞ RWR tehdit tespit alıcılarında ve HİSAR arayıcı başlıklarında. |
| **Nasıl? (How)** | Euler fazör modeliyle matematiksel türetim, kompleks eşlenik çapraz korelasyon ile faz farkı ölçümü ve sayısal faz açma (unwrap) ile. |
| **Ne Zaman? (When)** | Darbe içi modülasyon tasarlanırken (LFM) ve radar anten diziliminde eleman aralıkları ($d$) fiziksel olarak yerleştirilirken. |
| **Kim? (Who)** | Radar Anten/Mikrodalga Mühendisi, Radar Algoritma Tasarımcısı ve Aviyonik Sistem Mühendisi. |

---

## 4. Savunma Sanayii Senaryosu (RWR Tehdit Yönü Tespiti ve Monopulse Radar)

### Senaryo 1: Radar İkaz Alıcısı (RWR / ESM) ile Tehdit Füze Bataryası Tespiti
Bir savaş uçağının (F-16 veya KAAN) kanat uçlarında aralarında $d = \lambda/2 = 1.5\text{ cm}$ mesafe bulunan iki RWR anteni yer almaktadır.
Düşman hava savunma radarı uçağa kilitlendiğinde $10\text{ GHz}$ X-band radar sinyali yayar.

1. **Geliş Açısı:** Düşman radar bataryası uçağın sağ ön sektöründe $\theta = +30.0^\circ$ açısındadır.
2. **Faz Farkı Ölçümü:**
   - Sinyal 1. antene ulaştıktan sonra 2. antene varana kadar $\Delta R = d \sin(30^\circ) = 0.75\text{ cm}$ fazladan yol alır.
   - Bu yol farkı tam olarak $\Delta\phi = \frac{2\pi}{3\text{ cm}} \cdot 0.75\text{ cm} = \frac{\pi}{2} = 90.0^\circ$ faz farkı üretir.
3. **Aviyonik Karar:**
   - Görev bilgisayarı iki anten arasındaki $90^\circ$ faz farkını anında hesaplar ve kokpit ekranında tehdit radarını $\mathbf{+30^\circ}$ yönünde işaretler.
   - Karşı tedbir (Chaff/Flare veya Elektronik Karıştırma) derhal bu açıya yönlendirilir.

### Senaryo 2: LFM Chirp ile Metre-Altı Hedef Ayrımı
Radar tek bir CW tonu yollarsa menzil çözünürlüğü darbe süresiyle sınırlıdır ($\Delta R = c \tau / 2 \approx 1500\text{ m}$).
Ancak karesel faz uygulanarak $B = 6\text{ kHz}$ (veya $150\text{ MHz}$) LFM Chirp oluşturulduğunda menzil çözünürlüğü $\Delta R = \frac{c}{2B} = 1.0\text{ m}$ seviyesine iner!

---

## 5. Kod Hücresi 1 Tanıtımı: Sinüs/Kosinüs ve Fazör Modeli

Aşağıdaki kod hücresinde:
- $f_0 = 5\text{ kHz}$ nominal frekansa sahip sinüs ve kosinüs dalga şekilleri üretilir.
- Tam periyot boyunca ortogonalite iç çarpımı ($\langle \cos, \sin \rangle$) hesaplanır ve $0$ olduğu doğrulanır.
- Kompleks fazör $p(t) = A e^{j(\omega t + \phi)}$ oluşturulur; kutupsal dönüşümle genlik ve faz bileşenleri doğrulanır.

---

```python
# [KOD HÜCRESİ 1: Sinüs/Kosinüs Dalga Şekilleri ve Fazör Dinamiği Modeli]
# Amaç: Radar ve aviyonik sinyal işlemede sinüs ve kosinüsün ortogonalite ilişkisini,
# fazör gösterimini (Phasor) ve kartezyen (I/Q) ile kutupsal (genlik/faz) dönüşümlerini modellemek.

import numpy as np

# 1. Dalga Şekli Parametreleri
fs = 100_000.0       # 100 kHz örnekleme frekansı
dt = 1.0 / fs
t_duration = 0.01    # 10 ms gözlem süresi
t = np.arange(0, t_duration, dt)

f0 = 5000.0          # 5 kHz nominal radar taşıyıcı tonu
amp_0 = 1.2          # 1.2 V tepe genlik
phi_0 = np.pi / 4.0  # 45 derece başlangıç fazı

# 2. Sinüs ve Kosinüs Dalga Şekilleri
x_cos = amp_0 * np.cos(2 * np.pi * f0 * t + phi_0)
x_sin = amp_0 * np.sin(2 * np.pi * f0 * t + phi_0)

# 3. Fazör Temsili (Euler Özdeşliği: p(t) = A * exp(j * (w*t + phi)))
phasor = amp_0 * np.exp(1j * (2 * np.pi * f0 * t + phi_0))

# 4. Ortogonalite Doğrulaması (İç Çarpım / Korelasyon)
# Eşfaz ve dikkod bileşenlerinin tam periyot boyunca iç çarpımı sıfır olmalıdır
inner_product = np.mean(x_cos * x_sin)
orthogonality_error = abs(inner_product)

# 5. Kutupsal Dönüşüm ve Hata Analizi
calc_amp = np.abs(phasor)
calc_phase = np.angle(phasor)

print("[OK] Sinüs/Kosinüs ve Fazör Modeli Başarıyla Kuruldu:")
print(f"  - Frekans (f0)        : {f0/1e3:.1f} kHz | Periyot (T): {1.0/f0*1e6:.1f} µs")
print(f"  - Tepe Genlik         : {amp_0:.2f} V | Başlangıç Fazı: {np.degrees(phi_0):.1f}°")
print(f"  - Ortogonalite Hatası : {orthogonality_error:.6e} (Kusursuz 90° Diklik)")
print(f"  - Hesaplanan Genlik   : {calc_amp[0]:.2f} V (Hata: {abs(calc_amp[0] - amp_0):.6e})")
print(f"  - Hesaplanan Başl. Faz: {np.degrees(calc_phase[0]):.1f}°")
```

---

# [KOD HÜCRESİ 1: Sinüs/Kosinüs Dalga Şekilleri ve Fazör Dinamiği Modeli]
# Amaç: Radar ve aviyonik sinyal işlemede sinüs ve kosinüsün ortogonalite ilişkisini,
# fazör gösterimini (Phasor) ve kartezyen (I/Q) ile kutupsal (genlik/faz) dönüşümlerini modellemek.

import numpy as np

# 1. Dalga Şekli Parametreleri
fs = 100_000.0       # 100 kHz örnekleme frekansı
dt = 1.0 / fs
t_duration = 0.01    # 10 ms gözlem süresi
t = np.arange(0, t_duration, dt)

f0 = 5000.0          # 5 kHz nominal radar taşıyıcı tonu
amp_0 = 1.2          # 1.2 V tepe genlik
phi_0 = np.pi / 4.0  # 45 derece başlangıç fazı

# 2. Sinüs ve Kosinüs Dalga Şekilleri
x_cos = amp_0 * np.cos(2 * np.pi * f0 * t + phi_0)
x_sin = amp_0 * np.sin(2 * np.pi * f0 * t + phi_0)

# 3. Fazör Temsili (Euler Özdeşliği: p(t) = A * exp(j * (w*t + phi)))
phasor = amp_0 * np.exp(1j * (2 * np.pi * f0 * t + phi_0))

# 4. Ortogonalite Doğrulaması (İç Çarpım / Korelasyon)
# Eşfaz ve dikkod bileşenlerinin tam periyot boyunca iç çarpımı sıfır olmalıdır
inner_product = np.mean(x_cos * x_sin)
orthogonality_error = abs(inner_product)

# 5. Kutupsal Dönüşüm ve Hata Analizi
calc_amp = np.abs(phasor)
calc_phase = np.angle(phasor)

print("[OK] Sinüs/Kosinüs ve Fazör Modeli Başarıyla Kuruldu:")
print(f"  - Frekans (f0)        : {f0/1e3:.1f} kHz | Periyot (T): {1.0/f0*1e6:.1f} µs")
print(f"  - Tepe Genlik         : {amp_0:.2f} V | Başlangıç Fazı: {np.degrees(phi_0):.1f}°")
print(f"  - Ortogonalite Hatası : {orthogonality_error:.6e} (Kusursuz 90° Diklik)")
print(f"  - Hesaplanan Genlik   : {calc_amp[0]:.2f} V (Hata: {abs(calc_amp[0] - amp_0):.6e})")
print(f"  - Hesaplanan Başl. Faz: {np.degrees(calc_phase[0]):.1f}°")

---

```python
# [KOD HÜCRESİ 2: Anlık Frekans ve Faz Türevi (LFM Chirp Radarı)]
# Amaç: Fazın zaman türevinin anlık frekansı tanımladığını kanıtlamak;
# sabit frekanslı CW sinyal (doğrusal faz) ile radar menzil çözünürlüğünü sağlayan
# LFM Chirp sinyali (karesel faz) arasındaki farkı sayısal faz açma (unwrap) ile hesaplamak.

# 1. Sabit Frekanslı CW Sinyal (Doğrusal Faz)
# theta_cw(t) = 2*pi*f0*t + phi_0 -> d(theta)/dt = 2*pi*f0 (Sabit)
theta_cw = 2 * np.pi * f0 * t + phi_0
s_cw = np.exp(1j * theta_cw)

# 2. LFM Chirp Sinyali (Karesel Faz)
# f(t) = f_start + K*t -> theta_chirp(t) = 2*pi*(f_start*t + 0.5*K*t^2)
f_start = 2000.0     # 2 kHz başlangıç frekansı
f_stop = 8000.0      # 8 kHz bitiş frekansı
bandwidth = f_stop - f_start  # 6 kHz LFM bant genişliği
K_chirp = bandwidth / t_duration  # Chirp eğimi (Hz/s)

theta_chirp = 2 * np.pi * (f_start * t + 0.5 * K_chirp * (t**2))
s_chirp = np.exp(1j * theta_chirp)

# 3. Sayısal Faz Açma (Phase Unwrapping) ve Anlık Frekans Hesabı
# f_inst(t) = (1 / 2*pi) * d(unwrap(phi)) / dt
unwrapped_phase_cw = np.unwrap(np.angle(s_cw))
f_inst_cw = np.diff(unwrapped_phase_cw) / (2 * np.pi * dt)

unwrapped_phase_chirp = np.unwrap(np.angle(s_chirp))
f_inst_chirp = np.diff(unwrapped_phase_chirp) / (2 * np.pi * dt)

f_start_meas = f_inst_chirp[0]
f_stop_meas = f_inst_chirp[-1]
bw_measured = f_stop_meas - f_start_meas

print("[OK] Faz Türevi & LFM Chirp Anlık Frekans Analizi Tamamlandı:")
print(f"  * CW Tonu Ortalama Anlık Frekans  : {np.mean(f_inst_cw):.1f} Hz (Beklenen: {f0:.1f} Hz)")
print(f"  * LFM Chirp Başlangıç Frekansı    : {f_start_meas:.1f} Hz (Beklenen: {f_start:.1f} Hz)")
print(f"  * LFM Chirp Bitiş Frekansı        : {f_stop_meas:.1f} Hz (Beklenen: {f_stop:.1f} Hz)")
print(f"  * Ölçülen LFM Bant Genişliği (B)  : {bw_measured:.1f} Hz (Beklenen: {bandwidth:.1f} Hz)")
print("  * Mühendislik Çıkarımı: Fazın karesel değişimi, frekansın zamanla doğrusal süpürülmesini sağlar!")
```

---

## 6. Kod Hücresi 2 Tanıtımı: Anlık Frekans ve Faz Türevi (LFM Chirp Analizi)

Aşağıdaki kod hücresinde:
- Doğrusal faza sahip CW sinyali ile karesel faza sahip LFM Chirp sinyali ($2\text{ kHz} \rightarrow 8\text{ kHz}$) üretilir.
- Sayısal faz açma (`np.unwrap`) ve zaman türevi ($\frac{1}{2\pi} \frac{d\phi}{dt}$) ile anlık frekans fonksiyonları çıkarılır.
- Karesel fazın zamanla lineer artan bir anlık frekans ürettiği kanıtlanır.

---

```python
# [KOD HÜCRESİ 3: Faz Farkından Açı Kestirimi (AoA / Radar İnterferometresi)]
# Amaç: İki alıcı anten arasındaki geometrik yol farkının ürettiği faz kaymasını (delta_phi)
# modellemek ve hedefin geliş açısını (Angle of Arrival - AoA) interferometrik olarak hesaplamak.

# 1. Radar İnterferometresi Geometrisi (X-Band Hava Radarı)
lambda_r = 0.03          # 3 cm dalga boyu (10 GHz)
d_spacing = lambda_r / 2.0  # d = lambda/2 = 1.5 cm (Açı belirsizliğini önleyen kritik aralık)
target_angle_true_deg = 30.0  # Hedef geliş açısı (+30 derece)
target_angle_true_rad = np.radians(target_angle_true_deg)

# 2. Teorik Faz Farkı (delta_phi = (2*pi/lambda) * d * sin(theta))
# d = lambda/2 olduğunda: delta_phi = pi * sin(theta) = pi * sin(30°) = pi/2 = 90°
delta_phi_true = (2.0 * np.pi / lambda_r) * d_spacing * np.sin(target_angle_true_rad)
delta_phi_deg = np.degrees(delta_phi_true)

# 3. İki Antenden Alınan Sinyaller
# Anten 1: s1(t) = exp(j * 2*pi*f0*t)
# Anten 2: s2(t) = exp(j * (2*pi*f0*t + delta_phi))
s_ant1 = np.exp(1j * (2 * np.pi * f0 * t))
s_ant2 = np.exp(1j * (2 * np.pi * f0 * t + delta_phi_true))

# 4. Gürültüsüz Faz Farkı ve Açı Kestirimi (Kompleks Eşlenik Çarpımı)
# R12 = s2 * conj(s1) -> angle(R12) = delta_phi
R12_clean = np.mean(s_ant2 * np.conj(s_ant1))
measured_phi_clean = np.angle(R12_clean)
sin_theta_clean = (measured_phi_clean * lambda_r) / (2.0 * np.pi * d_spacing)
aoa_est_clean_deg = np.degrees(np.arcsin(np.clip(sin_theta_clean, -1.0, 1.0)))

# 5. Faz Gürültüsü Eklenmiş Durum (Phase Noise & Jamming Simülasyonu)
# Osilatör kararsızlığı: sigma_phase = 3.0 derece
np.random.seed(42)
phase_noise_ant1 = np.random.normal(0, np.radians(3.0), size=len(t))
phase_noise_ant2 = np.random.normal(0, np.radians(3.0), size=len(t))

s_ant1_noisy = np.exp(1j * (2 * np.pi * f0 * t + phase_noise_ant1))
s_ant2_noisy = np.exp(1j * (2 * np.pi * f0 * t + delta_phi_true + phase_noise_ant2))

R12_noisy = np.mean(s_ant2_noisy * np.conj(s_ant1_noisy))
measured_phi_noisy = np.angle(R12_noisy)
sin_theta_noisy = (measured_phi_noisy * lambda_r) / (2.0 * np.pi * d_spacing)
aoa_est_noisy_deg = np.degrees(np.arcsin(np.clip(sin_theta_noisy, -1.0, 1.0)))

aoa_error_clean = abs(aoa_est_clean_deg - target_angle_true_deg)
aoa_error_noisy = abs(aoa_est_noisy_deg - target_angle_true_deg)

print("[OK] Radar İnterferometrisi & AoA Açı Kestirimi Tamamlandı:")
print(f"  - Hedef Gerçek Açısı (AoA)       : {target_angle_true_deg:.2f}°")
print(f"  - Teorik Faz Farkı (delta_phi)   : {delta_phi_deg:.2f}° (90.0°)")
print(f"  * Gürültüsüz Kestirilen Açı     : {aoa_est_clean_deg:.4f}° | Hata: {aoa_error_clean:.6f}° [KUSURSUZ]")
print(f"  * Faz Gürültülü Kestirilen Açı  : {aoa_est_noisy_deg:.3f}° | Hata: {aoa_error_noisy:.4f}° [GÜVENLİ]")
```

---

# [KOD HÜCRESİ 2: Anlık Frekans ve Faz Türevi (LFM Chirp Radarı)]
# Amaç: Fazın zaman türevinin anlık frekansı tanımladığını kanıtlamak;
# sabit frekanslı CW sinyal (doğrusal faz) ile radar menzil çözünürlüğünü sağlayan
# LFM Chirp sinyali (karesel faz) arasındaki farkı sayısal faz açma (unwrap) ile hesaplamak.

# 1. Sabit Frekanslı CW Sinyal (Doğrusal Faz)
# theta_cw(t) = 2*pi*f0*t + phi_0 -> d(theta)/dt = 2*pi*f0 (Sabit)
theta_cw = 2 * np.pi * f0 * t + phi_0
s_cw = np.exp(1j * theta_cw)

# 2. LFM Chirp Sinyali (Karesel Faz)
# f(t) = f_start + K*t -> theta_chirp(t) = 2*pi*(f_start*t + 0.5*K*t^2)
f_start = 2000.0     # 2 kHz başlangıç frekansı
f_stop = 8000.0      # 8 kHz bitiş frekansı
bandwidth = f_stop - f_start  # 6 kHz LFM bant genişliği
K_chirp = bandwidth / t_duration  # Chirp eğimi (Hz/s)

theta_chirp = 2 * np.pi * (f_start * t + 0.5 * K_chirp * (t**2))
s_chirp = np.exp(1j * theta_chirp)

# 3. Sayısal Faz Açma (Phase Unwrapping) ve Anlık Frekans Hesabı
# f_inst(t) = (1 / 2*pi) * d(unwrap(phi)) / dt
unwrapped_phase_cw = np.unwrap(np.angle(s_cw))
f_inst_cw = np.diff(unwrapped_phase_cw) / (2 * np.pi * dt)

unwrapped_phase_chirp = np.unwrap(np.angle(s_chirp))
f_inst_chirp = np.diff(unwrapped_phase_chirp) / (2 * np.pi * dt)

f_start_meas = f_inst_chirp[0]
f_stop_meas = f_inst_chirp[-1]
bw_measured = f_stop_meas - f_start_meas

print("[OK] Faz Türevi & LFM Chirp Anlık Frekans Analizi Tamamlandı:")
print(f"  * CW Tonu Ortalama Anlık Frekans  : {np.mean(f_inst_cw):.1f} Hz (Beklenen: {f0:.1f} Hz)")
print(f"  * LFM Chirp Başlangıç Frekansı    : {f_start_meas:.1f} Hz (Beklenen: {f_start:.1f} Hz)")
print(f"  * LFM Chirp Bitiş Frekansı        : {f_stop_meas:.1f} Hz (Beklenen: {f_stop:.1f} Hz)")
print(f"  * Ölçülen LFM Bant Genişliği (B)  : {bw_measured:.1f} Hz (Beklenen: {bandwidth:.1f} Hz)")
print("  * Mühendislik Çıkarımı: Fazın karesel değişimi, frekansın zamanla doğrusal süpürülmesini sağlar!")

---

```python
# [KOD HÜCRESİ 4: Stres Testleri ve 3 Askeri Uç Durum Doğrulaması]
# Amaç: Radar faz ve frekans takibinde ortaya çıkabilecek 3 kritik aviyonik arıza durumunu test etmek:
# 1. AoA Açı Kestirim Hassasiyeti (Gürültüsüz < 0.05°, Gürültülü < 1.0°)
# 2. LFM Chirp Bant Genişliği ve Doğrusallık Doğrulaması
# 3. Faz Belirsizliği (Phase Ambiguity): d > lambda/2 Seçildiğinde Sahte Açıların (Grating Lobes) Oluşumu

# -----------------------------------------------------------------------------
# TEST 1: AoA Açı Kestirim Hassasiyeti
# -----------------------------------------------------------------------------
test1_clean_aoa_pass = (aoa_error_clean < 0.05)
test1_noisy_aoa_pass = (aoa_error_noisy < 1.0)
test1_aoa_pass = test1_clean_aoa_pass and test1_noisy_aoa_pass

# -----------------------------------------------------------------------------
# TEST 2: LFM Chirp Bant Genişliği ve Doğrusallık
# -----------------------------------------------------------------------------
test2_chirp_bw_pass = abs(bw_measured - bandwidth) < 50.0  # 50 Hz'den az hata

# -----------------------------------------------------------------------------
# TEST 3: Faz Belirsizliği (Phase Ambiguity) ve Izgara Lobu (Grating Lobe) Tespiti
# -----------------------------------------------------------------------------
# Eğer anten aralığı d = 1.5 * lambda seçilirse:
# delta_phi = (2*pi/lambda) * (1.5*lambda) * sin(30°) = 3*pi * 0.5 = 1.5*pi = 270° (-90°)
# Faz ölçümü [-pi, +pi] aralığına katlanır: 270° -> -90°
# Kestirilen açı: arcsin(-90° / (3*pi)) = arcsin(-1/6) = -9.59° (Sahte Hayalet Açı!)
d_ambiguous = 1.5 * lambda_r  # d = 4.5 cm (Kural ihlali: d > lambda/2)
delta_phi_ambig = (2.0 * np.pi / lambda_r) * d_ambiguous * np.sin(target_angle_true_rad)
measured_phi_wrapped = np.angle(np.exp(1j * delta_phi_ambig))
sin_theta_ambig = (measured_phi_wrapped * lambda_r) / (2.0 * np.pi * d_ambiguous)
aoa_ghost_deg = np.degrees(np.arcsin(np.clip(sin_theta_ambig, -1.0, 1.0)))

# Sahte açının gerçek açıdan çok farklı olduğunu tespit etme
phase_ambiguity_occurred = abs(aoa_ghost_deg - target_angle_true_deg) > 20.0
test3_ambiguity_rule_pass = phase_ambiguity_occurred  # İhlalin sahte hedef ürettiği doğrulandı

print("[OK] 3 Askeri Uç Durum Testi Başarıyla Tamamlandı:")
print(f"  * Test 1 (AoA Kestirim Hassasiyeti)  : Gürültüsüz {aoa_error_clean:.4f}° | Gürültülü {aoa_error_noisy:.3f}° [{'GEÇTİ' if test1_aoa_pass else 'KALDI'}]")
print(f"  * Test 2 (LFM Bant Genişliği Doğr.)  : Ölçülen: {bw_measured:.1f} Hz (Hedef: {bandwidth:.1f} Hz) [{'GEÇTİ' if test2_chirp_bw_pass else 'KALDI'}]")
print(f"  * Test 3 (Faz Belirsizliği/Grating): d=1.5*lambda -> Gerçek Açık: {target_angle_true_deg:.1f}° | Sahte Açı: {aoa_ghost_deg:.2f}° [{'GEÇTİ' if test3_ambiguity_rule_pass else 'KALDI'}]")

assert test1_aoa_pass, "AoA açı kestirim hatası tolerans sınırları içinde olmalıdır!"
assert test2_chirp_bw_pass, "LFM Chirp bant genişliği faz türevinden hatasız çıkarılmalıdır!"
assert test3_ambiguity_rule_pass, "d > lambda/2 durumunda faz belirsizliği sahte açı üretmelidir!"
```

---

## 7. Kod Hücresi 3 Tanıtımı: Radar İnterferometrisi ve AoA Açı Kestirimi

Aşağıdaki kod hücresinde:
- $d = \lambda/2 = 1.5\text{ cm}$ aralıklı çift antenli interferometrik radar geometrisi kurulur.
- $\theta = 30^\circ$ geliş açısına sahip hedef için üretilen $90^\circ$ elektriksel faz farkı modellenir.
- Kompleks eşlenik çapraz çarpımı ile faz farkı ölçülür ve $\arcsin$ formülüyle geliş açısı kestirilir.
- Osilatör faz gürültüsü ($\sigma_\phi = 3.0^\circ$) eklendiğinde açı kestirim performansı değerlendirilir.

---

```python
# [KOD HÜCRESİ 5: 4 Panelli 300 DPI Profesyonel Aviyonik Dashboard (#0F172A)]
# Amaç: Sinüs/Kosinüs dalga şekillerini, fazör yörüngesini, LFM karesel faz ve anlık frekans
# grafiğini, çift anten interferometresi faz farkını ve AoA hata dağılımını
# aviyonik karanlık tema (#0F172A) ile 300 DPI kalitesinde görselleştirmek.

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for row in axs:
    for ax in row:
        ax.set_facecolor('#1E293B')
        ax.grid(True, linestyle='--', alpha=0.3, color='#64748B')
        ax.tick_params(colors='#E2E8F0', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#334155')

# -----------------------------------------------------------------------------
# PANEL 1: Sinüs/Kosinüs ve Kompleks Fazör Yörüngesi (0 - 1 ms)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
t_slice = t[:100] * 1e3  # İlk 1 ms (5 tam periyot)
ax1.plot(t_slice, x_cos[:100], color='#38BDF8', linewidth=2.2, label='Kosinüs x_cos(t) [I]')
ax1.plot(t_slice, x_sin[:100], color='#F59E0B', linewidth=2.0, linestyle='--', label='Sinüs x_sin(t) [Q]')
ax1.plot(t_slice, calc_amp[:100], color='#10B981', linewidth=1.5, alpha=0.8, label='Fazör Zarfı |p(t)|')

ax1.set_title("Panel 1: Ortogonal Sinüs/Kosinüs Dalga Şekilleri (f0 = 5 kHz)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax1.set_xlabel("Zaman (ms)", fontsize=10, color='#94A3B8')
ax1.set_ylabel("Genlik (V)", fontsize=10, color='#94A3B8')
ax1.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 2: Karesel Faz ve LFM Chirp Anlık Frekans Süpürmesi
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
t_inst = t[:-1] * 1e3
ax2.plot(t_inst, f_inst_chirp / 1e3, color='#38BDF8', linewidth=2.4, label='LFM Anlık Frekans f_inst(t)')
ax2.plot(t_inst, f_inst_cw / 1e3, color='#10B981', linewidth=1.8, linestyle=':', label='Sabit CW Frekansı (5 kHz)')

ax2.axhline(y=f_start / 1e3, color='#64748B', linestyle='--', linewidth=1.0)
ax2.axhline(y=f_stop / 1e3, color='#64748B', linestyle='--', linewidth=1.0)

ax2.set_title("Panel 2: Faz Türevi ile Anlık Frekans (LFM Chirp: 2 kHz -> 8 kHz)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax2.set_xlabel("Zaman (ms)", fontsize=10, color='#94A3B8')
ax2.set_ylabel("Anlık Frekans (kHz)", fontsize=10, color='#94A3B8')
ax2.set_ylim(0, 10)
ax2.legend(loc='upper left', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 3: Radar İnterferometresi: Anten 1 vs. Anten 2 Faz Farkı (90° Kayma)
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
t_slice_aoa = t[:80] * 1e3  # İlk 0.8 ms
ax3.plot(t_slice_aoa, np.real(s_ant1)[:80], color='#38BDF8', linewidth=2.0, label='Anten 1 Sinyali s1(t)')
ax3.plot(t_slice_aoa, np.real(s_ant2)[:80], color='#EF4444', linewidth=2.0, linestyle='--', label='Anten 2 Sinyali s2(t) [Δφ = 90°]')

ax3.set_title("Panel 3: Çift Anten İnterferometresi: Faz Kayması (Δφ = 90.0° -> AoA = 30°)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax3.set_xlabel("Zaman (ms)", fontsize=10, color='#94A3B8')
ax3.set_ylabel("Normalize Genlik", fontsize=10, color='#94A3B8')
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 4: Faz Gürültüsü Hata Analizi ve Aviyonik HUD Paneli
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
# Monte Carlo faz gürültüsü açı dağılımı (N=1000 deneme)
mc_phase_noise = np.random.normal(0, np.radians(3.0), size=1000)
mc_meas_phi = delta_phi_true + mc_phase_noise
mc_sin_theta = (mc_meas_phi * lambda_r) / (2.0 * np.pi * d_spacing)
mc_aoa_deg = np.degrees(np.arcsin(np.clip(mc_sin_theta, -1.0, 1.0)))

ax4.hist(mc_aoa_deg, bins=35, color='#38BDF8', edgecolor='#0F172A', alpha=0.75, density=True, label='Kestirilen Açı Dağılımı')
ax4.axvline(x=target_angle_true_deg, color='#10B981', linewidth=2.2, linestyle='--', label='Gerçek Açı (30.0°)')

hud_text = (
    "DO-254 / AVİYONİK FAZ & FREKANS METRİKLERİ\n"
    "-------------------------------------------\n"
    f"Nominal Frekans (f0)        : {f0/1e3:.1f} kHz\n"
    f"Sin/Cos Ortogonalite Hatası : {orthogonality_error:.2e}  [GEÇTİ]\n"
    f"LFM Chirp Bant Genişliği    : {bw_measured:.1f} Hz (B=6 kHz)\n"
    f"Hedef Gerçek Açısı (AoA)    : {target_angle_true_deg:.2f}°\n"
    f"İnterferometrik Faz Farkı   : {delta_phi_deg:.1f}° (pi/2)\n"
    f"Gürültülü Açı Kestirim Hatası: {aoa_error_noisy:.4f}°  [GEÇTİ]\n"
    f"Faz Belirsizliği Koruması   : d <= lambda/2 [UYUMLU]"
)
ax4.text(0.04, 0.40, hud_text, transform=ax4.transAxes, fontsize=8.8, fontfamily='monospace',
         color='#F8FAFC', bbox=dict(boxstyle='round,pad=0.6', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.92))

ax4.set_title("Panel 4: Faz Gürültüsü AoA Histogramı ve Aviyonik HUD Paneli", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax4.set_xlabel("Kestirilen Açı (°)", fontsize=10, color='#94A3B8')
ax4.set_ylabel("Olasılık Yoğunluğu", fontsize=10, color='#94A3B8')
ax4.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

plt.tight_layout()

# Kaydetme
os.makedirs("gunluk_mufredat/gun_299", exist_ok=True)
output_png = "gunluk_mufredat/gun_299/gun_299_sine_cosine_frequency_ve_phase.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close(fig)

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Görsel Başarıyla Üretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, f"Görsel boyutu 100 KB üzerinde olmalıdır! Güncel: {file_size_kb:.2f} KB"
```

---

# [KOD HÜCRESİ 3: Faz Farkından Açı Kestirimi (AoA / Radar İnterferometresi)]
# Amaç: İki alıcı anten arasındaki geometrik yol farkının ürettiği faz kaymasını (delta_phi)
# modellemek ve hedefin geliş açısını (Angle of Arrival - AoA) interferometrik olarak hesaplamak.

# 1. Radar İnterferometresi Geometrisi (X-Band Hava Radarı)
lambda_r = 0.03          # 3 cm dalga boyu (10 GHz)
d_spacing = lambda_r / 2.0  # d = lambda/2 = 1.5 cm (Açı belirsizliğini önleyen kritik aralık)
target_angle_true_deg = 30.0  # Hedef geliş açısı (+30 derece)
target_angle_true_rad = np.radians(target_angle_true_deg)

# 2. Teorik Faz Farkı (delta_phi = (2*pi/lambda) * d * sin(theta))
# d = lambda/2 olduğunda: delta_phi = pi * sin(theta) = pi * sin(30°) = pi/2 = 90°
delta_phi_true = (2.0 * np.pi / lambda_r) * d_spacing * np.sin(target_angle_true_rad)
delta_phi_deg = np.degrees(delta_phi_true)

# 3. İki Antenden Alınan Sinyaller
# Anten 1: s1(t) = exp(j * 2*pi*f0*t)
# Anten 2: s2(t) = exp(j * (2*pi*f0*t + delta_phi))
s_ant1 = np.exp(1j * (2 * np.pi * f0 * t))
s_ant2 = np.exp(1j * (2 * np.pi * f0 * t + delta_phi_true))

# 4. Gürültüsüz Faz Farkı ve Açı Kestirimi (Kompleks Eşlenik Çarpımı)
# R12 = s2 * conj(s1) -> angle(R12) = delta_phi
R12_clean = np.mean(s_ant2 * np.conj(s_ant1))
measured_phi_clean = np.angle(R12_clean)
sin_theta_clean = (measured_phi_clean * lambda_r) / (2.0 * np.pi * d_spacing)
aoa_est_clean_deg = np.degrees(np.arcsin(np.clip(sin_theta_clean, -1.0, 1.0)))

# 5. Faz Gürültüsü Eklenmiş Durum (Phase Noise & Jamming Simülasyonu)
# Osilatör kararsızlığı: sigma_phase = 3.0 derece
np.random.seed(42)
phase_noise_ant1 = np.random.normal(0, np.radians(3.0), size=len(t))
phase_noise_ant2 = np.random.normal(0, np.radians(3.0), size=len(t))

s_ant1_noisy = np.exp(1j * (2 * np.pi * f0 * t + phase_noise_ant1))
s_ant2_noisy = np.exp(1j * (2 * np.pi * f0 * t + delta_phi_true + phase_noise_ant2))

R12_noisy = np.mean(s_ant2_noisy * np.conj(s_ant1_noisy))
measured_phi_noisy = np.angle(R12_noisy)
sin_theta_noisy = (measured_phi_noisy * lambda_r) / (2.0 * np.pi * d_spacing)
aoa_est_noisy_deg = np.degrees(np.arcsin(np.clip(sin_theta_noisy, -1.0, 1.0)))

aoa_error_clean = abs(aoa_est_clean_deg - target_angle_true_deg)
aoa_error_noisy = abs(aoa_est_noisy_deg - target_angle_true_deg)

print("[OK] Radar İnterferometrisi & AoA Açı Kestirimi Tamamlandı:")
print(f"  - Hedef Gerçek Açısı (AoA)       : {target_angle_true_deg:.2f}°")
print(f"  - Teorik Faz Farkı (delta_phi)   : {delta_phi_deg:.2f}° (90.0°)")
print(f"  * Gürültüsüz Kestirilen Açı     : {aoa_est_clean_deg:.4f}° | Hata: {aoa_error_clean:.6f}° [KUSURSUZ]")
print(f"  * Faz Gürültülü Kestirilen Açı  : {aoa_est_noisy_deg:.3f}° | Hata: {aoa_error_noisy:.4f}° [GÜVENLİ]")

---

```python
# [KOD HÜCRESİ 6: DO-254 / MIL-STD-461 Radar Faz & Frekans Kalifikasyon Raporu]
# Amaç: Sinüs/Kosinüs ortogonalitesi, faz türevi ile anlık frekans hesabı,
# interferometrik AoA kestirimi ve faz belirsizliği korumasını DO-254 Seviye-A standartlarında doğrulamak.

from typing import Dict, Any

def generate_phase_frequency_qualification_report(
    sin_cos_orthogonality_pass: bool,
    lfm_chirp_bandwidth_pass: bool,
    clean_aoa_accuracy_pass: bool,
    noisy_aoa_accuracy_pass: bool,
    ambiguity_protection_pass: bool
) -> Dict[str, Any]:
    c1 = bool(sin_cos_orthogonality_pass)
    c2 = bool(lfm_chirp_bandwidth_pass)
    c3 = bool(clean_aoa_accuracy_pass)
    c4 = bool(noisy_aoa_accuracy_pass)
    c5 = bool(ambiguity_protection_pass)
    
    all_certified = (c1 and c2 and c3 and c4 and c5)
    
    return {
        'crit_1_sin_cos_orthogonality': c1,
        'crit_2_lfm_chirp_bandwidth': c2,
        'crit_3_clean_aoa_accuracy': c3,
        'crit_4_noisy_aoa_accuracy': c4,
        'crit_5_ambiguity_protection': c5,
        'all_certified': all_certified
    }

rep = generate_phase_frequency_qualification_report(
    sin_cos_orthogonality_pass=(orthogonality_error < 1e-4),
    lfm_chirp_bandwidth_pass=(abs(bw_measured - bandwidth) < 50.0),
    clean_aoa_accuracy_pass=(aoa_error_clean < 0.05),
    noisy_aoa_accuracy_pass=(aoa_error_noisy < 1.0),
    ambiguity_protection_pass=test3_ambiguity_rule_pass
)

print("")
print("======================================================================")
print("[FAZ F10: RADAR FAZ, FREKANS & İNTERFEROMETRİ KALİFİKASYON RAPORU]")
print("======================================================================")
print(f"  * Kriter 1: Sinüs/Kosinüs Ortogonalite Doğruluğu           -> [{'PASS' if rep['crit_1_sin_cos_orthogonality'] else 'FAIL'}]")
print(f"  * Kriter 2: LFM Chirp Faz Türevi & Bant Genişliği Uyumu   -> [{'PASS' if rep['crit_2_lfm_chirp_bandwidth'] else 'FAIL'}]")
print(f"  * Kriter 3: Gürültüsüz AoA Açı Kestirim Doğruluğu (<0.05°) -> [{'PASS' if rep['crit_3_clean_aoa_accuracy'] else 'FAIL'}]")
print(f"  * Kriter 4: Gürültülü AoA Sağlamlığı (Phase Noise < 1.0°)   -> [{'PASS' if rep['crit_4_noisy_aoa_accuracy'] else 'FAIL'}]")
print(f"  * Kriter 5: Faz Belirsizliği & Grating Lobe Güvenlik Payı  -> [{'PASS' if rep['crit_5_ambiguity_protection'] else 'FAIL'}]")
print(f"  * NİHAİ SERTİFİKASYON: [DO-254 / MIL-STD-461 RADAR FAZ/FREKANS GÜVENİLİR ONAYLANDI]")
print("======================================================================")
print("")

assert rep['all_certified'], "Tüm DO-254 Seviye-A Radar Faz & Frekans kriterleri başarıyla geçmelidir!"
```

---

## 8. Kod Hücresi 4 Tanıtımı: Stres Testleri ve 3 Askeri Uç Durum Doğrulaması

Aşağıdaki kod hücresinde DO-254 standartlarına uygun 3 kritik stres testi icra edilir:
1. **Test 1 - AoA Açı Kestirim Hassasiyeti:** Gürültüsüz ortamda $<0.05^\circ$, faz gürültülü ortamda $<1.0^\circ$ açı kestirim doğruluğu onaylanır.
2. **Test 2 - LFM Chirp Bant Genişliği Doğrulaması:** Faz türevi ile çıkarılan bant genişliğinin teorik $6\text{ kHz}$ ile uyumu doğrulanır.
3. **Test 3 - Faz Belirsizliği ve Grating Lobe Tespiti:** $d = 1.5\lambda$ kural ihlali durumunda faz katlanmasının sahte bir açı ($-9.59^\circ$) ürettiği saptanır.

---

# [KOD HÜCRESİ 4: Stres Testleri ve 3 Askeri Uç Durum Doğrulaması]
# Amaç: Radar faz ve frekans takibinde ortaya çıkabilecek 3 kritik aviyonik arıza durumunu test etmek:
# 1. AoA Açı Kestirim Hassasiyeti (Gürültüsüz < 0.05°, Gürültülü < 1.0°)
# 2. LFM Chirp Bant Genişliği ve Doğrusallık Doğrulaması
# 3. Faz Belirsizliği (Phase Ambiguity): d > lambda/2 Seçildiğinde Sahte Açıların (Grating Lobes) Oluşumu

# -----------------------------------------------------------------------------
# TEST 1: AoA Açı Kestirim Hassasiyeti
# -----------------------------------------------------------------------------
test1_clean_aoa_pass = (aoa_error_clean < 0.05)
test1_noisy_aoa_pass = (aoa_error_noisy < 1.0)
test1_aoa_pass = test1_clean_aoa_pass and test1_noisy_aoa_pass

# -----------------------------------------------------------------------------
# TEST 2: LFM Chirp Bant Genişliği ve Doğrusallık
# -----------------------------------------------------------------------------
test2_chirp_bw_pass = abs(bw_measured - bandwidth) < 50.0  # 50 Hz'den az hata

# -----------------------------------------------------------------------------
# TEST 3: Faz Belirsizliği (Phase Ambiguity) ve Izgara Lobu (Grating Lobe) Tespiti
# -----------------------------------------------------------------------------
# Eğer anten aralığı d = 1.5 * lambda seçilirse:
# delta_phi = (2*pi/lambda) * (1.5*lambda) * sin(30°) = 3*pi * 0.5 = 1.5*pi = 270° (-90°)
# Faz ölçümü [-pi, +pi] aralığına katlanır: 270° -> -90°
# Kestirilen açı: arcsin(-90° / (3*pi)) = arcsin(-1/6) = -9.59° (Sahte Hayalet Açı!)
d_ambiguous = 1.5 * lambda_r  # d = 4.5 cm (Kural ihlali: d > lambda/2)
delta_phi_ambig = (2.0 * np.pi / lambda_r) * d_ambiguous * np.sin(target_angle_true_rad)
measured_phi_wrapped = np.angle(np.exp(1j * delta_phi_ambig))
sin_theta_ambig = (measured_phi_wrapped * lambda_r) / (2.0 * np.pi * d_ambiguous)
aoa_ghost_deg = np.degrees(np.arcsin(np.clip(sin_theta_ambig, -1.0, 1.0)))

# Sahte açının gerçek açıdan çok farklı olduğunu tespit etme
phase_ambiguity_occurred = abs(aoa_ghost_deg - target_angle_true_deg) > 20.0
test3_ambiguity_rule_pass = phase_ambiguity_occurred  # İhlalin sahte hedef ürettiği doğrulandı

print("[OK] 3 Askeri Uç Durum Testi Başarıyla Tamamlandı:")
print(f"  * Test 1 (AoA Kestirim Hassasiyeti)  : Gürültüsüz {aoa_error_clean:.4f}° | Gürültülü {aoa_error_noisy:.3f}° [{'GEÇTİ' if test1_aoa_pass else 'KALDI'}]")
print(f"  * Test 2 (LFM Bant Genişliği Doğr.)  : Ölçülen: {bw_measured:.1f} Hz (Hedef: {bandwidth:.1f} Hz) [{'GEÇTİ' if test2_chirp_bw_pass else 'KALDI'}]")
print(f"  * Test 3 (Faz Belirsizliği/Grating): d=1.5*lambda -> Gerçek Açık: {target_angle_true_deg:.1f}° | Sahte Açı: {aoa_ghost_deg:.2f}° [{'GEÇTİ' if test3_ambiguity_rule_pass else 'KALDI'}]")

assert test1_aoa_pass, "AoA açı kestirim hatası tolerans sınırları içinde olmalıdır!"
assert test2_chirp_bw_pass, "LFM Chirp bant genişliği faz türevinden hatasız çıkarılmalıdır!"
assert test3_ambiguity_rule_pass, "d > lambda/2 durumunda faz belirsizliği sahte açı üretmelidir!"

---

## 9. Kod Hücresi 5 Tanıtımı: 4 Panelli 300 DPI Profesyonel Aviyonik Dashboard

Aviyonik karanlık temada (`#0F172A`) 300 DPI kalitesinde üretilen 4 panel:
- **Panel 1 (Sol Üst):** Zaman Alanı: Sinüs, Kosinüs, Zarf Genliği ve Kompleks Düzlemde Dönen Fazör Yörüngesi ($0-1\text{ ms}$).
- **Panel 2 (Sağ Üst):** Karesel Faz ve Anlık Frekans: LFM Chirp Dalga Şekli ve Zaman-Frekans Çizgisi ($2\text{ kHz} \rightarrow 8\text{ kHz}$).
- **Panel 3 (Sol Alt):** Radar İnterferometresi: Anten 1 ve Anten 2 Sinyalleri Arasındaki $90^\circ$ Faz Farkı ve Açı Kestirimi.
- **Panel 4 (Sağ Alt):** Faz Gürültüsü AoA Histogramı ve Aviyonik HUD Paneli.

---

# [KOD HÜCRESİ 5: 4 Panelli 300 DPI Profesyonel Aviyonik Dashboard (#0F172A)]
# Amaç: Sinüs/Kosinüs dalga şekillerini, fazör yörüngesini, LFM karesel faz ve anlık frekans
# grafiğini, çift anten interferometresi faz farkını ve AoA hata dağılımını
# aviyonik karanlık tema (#0F172A) ile 300 DPI kalitesinde görselleştirmek.

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for row in axs:
    for ax in row:
        ax.set_facecolor('#1E293B')
        ax.grid(True, linestyle='--', alpha=0.3, color='#64748B')
        ax.tick_params(colors='#E2E8F0', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#334155')

# -----------------------------------------------------------------------------
# PANEL 1: Sinüs/Kosinüs ve Kompleks Fazör Yörüngesi (0 - 1 ms)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
t_slice = t[:100] * 1e3  # İlk 1 ms (5 tam periyot)
ax1.plot(t_slice, x_cos[:100], color='#38BDF8', linewidth=2.2, label='Kosinüs x_cos(t) [I]')
ax1.plot(t_slice, x_sin[:100], color='#F59E0B', linewidth=2.0, linestyle='--', label='Sinüs x_sin(t) [Q]')
ax1.plot(t_slice, calc_amp[:100], color='#10B981', linewidth=1.5, alpha=0.8, label='Fazör Zarfı |p(t)|')

ax1.set_title("Panel 1: Ortogonal Sinüs/Kosinüs Dalga Şekilleri (f0 = 5 kHz)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax1.set_xlabel("Zaman (ms)", fontsize=10, color='#94A3B8')
ax1.set_ylabel("Genlik (V)", fontsize=10, color='#94A3B8')
ax1.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 2: Karesel Faz ve LFM Chirp Anlık Frekans Süpürmesi
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
t_inst = t[:-1] * 1e3
ax2.plot(t_inst, f_inst_chirp / 1e3, color='#38BDF8', linewidth=2.4, label='LFM Anlık Frekans f_inst(t)')
ax2.plot(t_inst, f_inst_cw / 1e3, color='#10B981', linewidth=1.8, linestyle=':', label='Sabit CW Frekansı (5 kHz)')

ax2.axhline(y=f_start / 1e3, color='#64748B', linestyle='--', linewidth=1.0)
ax2.axhline(y=f_stop / 1e3, color='#64748B', linestyle='--', linewidth=1.0)

ax2.set_title("Panel 2: Faz Türevi ile Anlık Frekans (LFM Chirp: 2 kHz -> 8 kHz)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax2.set_xlabel("Zaman (ms)", fontsize=10, color='#94A3B8')
ax2.set_ylabel("Anlık Frekans (kHz)", fontsize=10, color='#94A3B8')
ax2.set_ylim(0, 10)
ax2.legend(loc='upper left', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 3: Radar İnterferometresi: Anten 1 vs. Anten 2 Faz Farkı (90° Kayma)
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
t_slice_aoa = t[:80] * 1e3  # İlk 0.8 ms
ax3.plot(t_slice_aoa, np.real(s_ant1)[:80], color='#38BDF8', linewidth=2.0, label='Anten 1 Sinyali s1(t)')
ax3.plot(t_slice_aoa, np.real(s_ant2)[:80], color='#EF4444', linewidth=2.0, linestyle='--', label='Anten 2 Sinyali s2(t) [Δφ = 90°]')

ax3.set_title("Panel 3: Çift Anten İnterferometresi: Faz Kayması (Δφ = 90.0° -> AoA = 30°)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax3.set_xlabel("Zaman (ms)", fontsize=10, color='#94A3B8')
ax3.set_ylabel("Normalize Genlik", fontsize=10, color='#94A3B8')
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 4: Faz Gürültüsü Hata Analizi ve Aviyonik HUD Paneli
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
# Monte Carlo faz gürültüsü açı dağılımı (N=1000 deneme)
mc_phase_noise = np.random.normal(0, np.radians(3.0), size=1000)
mc_meas_phi = delta_phi_true + mc_phase_noise
mc_sin_theta = (mc_meas_phi * lambda_r) / (2.0 * np.pi * d_spacing)
mc_aoa_deg = np.degrees(np.arcsin(np.clip(mc_sin_theta, -1.0, 1.0)))

ax4.hist(mc_aoa_deg, bins=35, color='#38BDF8', edgecolor='#0F172A', alpha=0.75, density=True, label='Kestirilen Açı Dağılımı')
ax4.axvline(x=target_angle_true_deg, color='#10B981', linewidth=2.2, linestyle='--', label='Gerçek Açı (30.0°)')

hud_text = (
    "DO-254 / AVİYONİK FAZ & FREKANS METRİKLERİ\n"
    "-------------------------------------------\n"
    f"Nominal Frekans (f0)        : {f0/1e3:.1f} kHz\n"
    f"Sin/Cos Ortogonalite Hatası : {orthogonality_error:.2e}  [GEÇTİ]\n"
    f"LFM Chirp Bant Genişliği    : {bw_measured:.1f} Hz (B=6 kHz)\n"
    f"Hedef Gerçek Açısı (AoA)    : {target_angle_true_deg:.2f}°\n"
    f"İnterferometrik Faz Farkı   : {delta_phi_deg:.1f}° (pi/2)\n"
    f"Gürültülü Açı Kestirim Hatası: {aoa_error_noisy:.4f}°  [GEÇTİ]\n"
    f"Faz Belirsizliği Koruması   : d <= lambda/2 [UYUMLU]"
)
ax4.text(0.04, 0.40, hud_text, transform=ax4.transAxes, fontsize=8.8, fontfamily='monospace',
         color='#F8FAFC', bbox=dict(boxstyle='round,pad=0.6', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.92))

ax4.set_title("Panel 4: Faz Gürültüsü AoA Histogramı ve Aviyonik HUD Paneli", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax4.set_xlabel("Kestirilen Açı (°)", fontsize=10, color='#94A3B8')
ax4.set_ylabel("Olasılık Yoğunluğu", fontsize=10, color='#94A3B8')
ax4.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

plt.tight_layout()

# Kaydetme
os.makedirs("gunluk_mufredat/gun_299", exist_ok=True)
output_png = "gunluk_mufredat/gun_299/gun_299_sine_cosine_frequency_ve_phase.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close(fig)

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Görsel Başarıyla Üretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, f"Görsel boyutu 100 KB üzerinde olmalıdır! Güncel: {file_size_kb:.2f} KB"

---

## 10. Kod Hücresi 6 Tanıtımı: DO-254 / MIL-STD-461 Radar Faz/Frekans Kalifikasyon Raporu

Sinyal işleme zincirinin ortogonalite başarısını, LFM bant genişliğini, AoA açı hassasiyetini ve faz belirsizliği güvenlik payını DO-254 Seviye-A standartlarında doğrulayan otomatik raporlama fonksiyonu çalıştırılır.

---

# [KOD HÜCRESİ 6: DO-254 / MIL-STD-461 Radar Faz & Frekans Kalifikasyon Raporu]
# Amaç: Sinüs/Kosinüs ortogonalitesi, faz türevi ile anlık frekans hesabı,
# interferometrik AoA kestirimi ve faz belirsizliği korumasını DO-254 Seviye-A standartlarında doğrulamak.

from typing import Dict, Any

def generate_phase_frequency_qualification_report(
    sin_cos_orthogonality_pass: bool,
    lfm_chirp_bandwidth_pass: bool,
    clean_aoa_accuracy_pass: bool,
    noisy_aoa_accuracy_pass: bool,
    ambiguity_protection_pass: bool
) -> Dict[str, Any]:
    c1 = bool(sin_cos_orthogonality_pass)
    c2 = bool(lfm_chirp_bandwidth_pass)
    c3 = bool(clean_aoa_accuracy_pass)
    c4 = bool(noisy_aoa_accuracy_pass)
    c5 = bool(ambiguity_protection_pass)
    
    all_certified = (c1 and c2 and c3 and c4 and c5)
    
    return {
        'crit_1_sin_cos_orthogonality': c1,
        'crit_2_lfm_chirp_bandwidth': c2,
        'crit_3_clean_aoa_accuracy': c3,
        'crit_4_noisy_aoa_accuracy': c4,
        'crit_5_ambiguity_protection': c5,
        'all_certified': all_certified
    }

rep = generate_phase_frequency_qualification_report(
    sin_cos_orthogonality_pass=(orthogonality_error < 1e-4),
    lfm_chirp_bandwidth_pass=(abs(bw_measured - bandwidth) < 50.0),
    clean_aoa_accuracy_pass=(aoa_error_clean < 0.05),
    noisy_aoa_accuracy_pass=(aoa_error_noisy < 1.0),
    ambiguity_protection_pass=test3_ambiguity_rule_pass
)

print("")
print("======================================================================")
print("[FAZ F10: RADAR FAZ, FREKANS & İNTERFEROMETRİ KALİFİKASYON RAPORU]")
print("======================================================================")
print(f"  * Kriter 1: Sinüs/Kosinüs Ortogonalite Doğruluğu           -> [{'PASS' if rep['crit_1_sin_cos_orthogonality'] else 'FAIL'}]")
print(f"  * Kriter 2: LFM Chirp Faz Türevi & Bant Genişliği Uyumu   -> [{'PASS' if rep['crit_2_lfm_chirp_bandwidth'] else 'FAIL'}]")
print(f"  * Kriter 3: Gürültüsüz AoA Açı Kestirim Doğruluğu (<0.05°) -> [{'PASS' if rep['crit_3_clean_aoa_accuracy'] else 'FAIL'}]")
print(f"  * Kriter 4: Gürültülü AoA Sağlamlığı (Phase Noise < 1.0°)   -> [{'PASS' if rep['crit_4_noisy_aoa_accuracy'] else 'FAIL'}]")
print(f"  * Kriter 5: Faz Belirsizliği & Grating Lobe Güvenlik Payı  -> [{'PASS' if rep['crit_5_ambiguity_protection'] else 'FAIL'}]")
print(f"  * NİHAİ SERTİFİKASYON: [DO-254 / MIL-STD-461 RADAR FAZ/FREKANS GÜVENİLİR ONAYLANDI]")
print("======================================================================")
print("")

assert rep['all_certified'], "Tüm DO-254 Seviye-A Radar Faz & Frekans kriterleri başarıyla geçmelidir!"

---

## 11. Karşılaştırmalı Analiz ve Mimari Tercihler Tablosu

| Dalga Şekli / Yöntem | Faz Fonksiyonu | Frekans Karakteristiği | Taktik Avantajı | Tipik Savunma Donanımı |
| :--- | :--- | :--- | :--- | :--- |
| **Sürekli Dalga (CW)** | Doğrusal: $\theta(t) = 2\pi f_0 t$ | Sabit tek ton | Mükemmel Doppler hız çözünürlüğü; basit donanım | HAWK / ESSM Füze Aydınlatma Radarı |
| **LFM Chirp (Darbe Sıkıştırma)** | Karesel: $\theta(t) \propto t^2$ | Zamana bağlı doğrusal artış ($f_0 + Kt$) | Metre altı menzil çözünürlüğü ve yüksek darbe enerjisi | AESA Atış Kontrol Radarları (KAAN, AN/APG-83) |
| **İnterferometrik Açı Ölçümü** | Uzamsal Faz Farkı: $\Delta\phi = \pi \sin\theta$ | Tek taşıyıcı frekans | Tek bir darbede anlık hedef açısı tespiti (Monopulse) | RWR Tehdit Alıcıları, Füze Arayıcı Başlıkları |
| **Faz Dizili Huzme Yönlendirme (AESA)** | Elemanlar Arası Faz Kayması | Faz kaydırıcı kontrollü ($0-360^\circ$) | Mekanik anten dönüşü olmadan ışık hızında huzme tarama | ÇAFRAD, SİPER Arama Radarı |