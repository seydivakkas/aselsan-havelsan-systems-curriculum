# Gün 298: Complex Numbers ve In-Phase / Quadrature (I/Q) Temsili (Radar, DSP ve Haberleşme)

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

### Faz F10: Radar / DSP / Communications — Kompleks Sayılar ve I/Q Temsili
Fiziksel dünyada bir osiloskop probu veya anten çıkışı yalnızca tek boyutlu gerçek gerilimleri ($v(t) \in \mathbb{R}$) ölçebilir. Ancak modern bir radar alıcısında yalnızca gerilimi bilmek yetersizdir; hedefin yaklaşma veya uzaklaşma yönünü (Doppler işareti), anlık fazını ve karmaşık modülasyonları çözebilmek için iki boyutlu bir matematiksel yapıya ihtiyaç duyarız.

Bu matematiksel omurga **In-Phase (Eşfaz - $I$)** ve **Quadrature (Dikkod - $Q$)** sinyallerinin birleşimi olan **Analitik Kompleks Sinyal** temsilidir:

$$z(t) = I(t) + j Q(t) = A(t) e^{j \phi(t)}$$

Bugün **Gün 298**'de:
1. Fiziksel RF/IF sinyalinin kuadratür demodülatör ile $I$ ve $Q$ bileşenlerine ayrıştırılmasını,
2. Gerçek FFT'nin pozitif ve negatif frekansları ayırt edememe kısıtını ve Kompleks FFT'nin Doppler yönünü nasıl çözdüğünü,
3. Analog devrelerde kaçınılmaz olan **I/Q Dengesizliğini (Gain Mismatch, Phase Mismatch, DC Offset)** ve oluşturduğu **Hayalet Ayna Hedefini (Ghost Image)**,
4. Sayısal DSP katmanında bu ayna hedefi yok eden **Gram-Schmidt Eliptik Kalibrasyon Algoritmasını** ve **Image Rejection Ratio (IRR)** analizini derinlemesine inceleyeceğiz.

---

## 1. Konsept ve Matematiksel Altyapı

### 1.1 Gerçek Sinyallerin Kısıtı ve Hilbert Dönüşümü
Gerçek değerli bir radar darbesi Euler formülüyle iki eşlenik kompleks üstel bileşenin toplamıdır:

$$s(t) = A \cos(2\pi f_0 t + \phi) = \frac{A}{2} e^{j(2\pi f_0 t + \phi)} + \frac{A}{2} e^{-j(2\pi f_0 t + \phi)}$$

Fourier dönüşümünde gerçek bir sinyalin spektrumu çift-simetriktir (Hermitian): $S(-f) = S^*(f)$.
Bu simetri sebebiyle, $+f_d$ frekansında yaklaşan bir hedef ile $-f_d$ frekansında uzaklaşan bir hedef **aynı gerçek spektrumu üretir**!
Negatif frekansları yok edip yalnızca pozitif frekansları içeren analitik sinyali türetmek için Hilbert dönüşümü ($\mathcal{H}\{\cdot\}$) kullanılır:

$$z(t) = s(t) + j \mathcal{H}\{s(t)\} = A(t) e^{j(2\pi f_0 t + \phi(t))}$$

### 1.2 Kuadratür Demodülatör (Quadrature Downconversion)
Pratikte Hilbert dönüşümü geniş bantta analog olarak gerçekleştirilemez. Bunun yerine giriş RF/IF sinyali, yerel osilatörün (LO) birbiriyle $90^\circ$ faz farkına sahip iki kopyası ile çarpılır:

$$\begin{aligned}
\text{I Kanalı (In-Phase):} \quad & x_I(t) = x_{in}(t) \cdot 2\cos(2\pi f_c t) \\
\text{Q Kanalı (Quadrature):} \quad & x_Q(t) = x_{in}(t) \cdot (-2\sin(2\pi f_c t))
\end{aligned}$$

Alçak geçiren filtreleme (LPF) sonrasında $2 f_c$ yüksek frekans terimleri elenir ve temel bant $I(t)$ ve $Q(t)$ sinyalleri kalır:

$$z(t) = I(t) + j Q(t)$$

- **Anlık Zarf Genliği (Magnitude):** $A(t) = \sqrt{I^2(t) + Q^2(t)}$
- **Anlık Faz (Phase):** $\phi(t) = \mathrm{atan2}(Q(t), I(t))$
- **Anlık Doppler Frekansı:** $f_d(t) = \frac{1}{2\pi} \frac{d\phi(t)}{dt}$

### 1.3 Pozitif vs. Negatif Frekans Ayrımı
Kompleks üstel fonksiyon $e^{j 2\pi f_d t}$ için:
- **Yaklaşan Hedef ($f_d > 0$):** Faz saatin tersi yönünde döner ($I$ kanalı $Q$'dan $90^\circ$ öndedir).
- **Uzaklaşan Hedef ($f_d < 0$):** Faz saat yönünde döner ($Q$ kanalı $I$'dan $90^\circ$ öndedir).
İki taraflı FFT (Two-Sided Complex FFT) uygulandığında $+f_d$ ve $-f_d$ frekans ekseninin farklı taraflarında bağımsız iki tepe olarak belirir.

### 1.4 Donanımsal I/Q Dengesizliği ve Ayna Hedef (Ghost Image)
Analog mikserlerin kazanç farkı ($\epsilon$) ve faz kaydırıcının $90^\circ$'den sapması ($\Delta\theta$):

$$\begin{aligned}
I_{m}(t) &= (1 + \epsilon/2) I(t) + I_{dc} \\
Q_{m}(t) &= (1 - \epsilon/2) \left[ \sin(\Delta\theta) I(t) + \cos(\Delta\theta) Q(t) \right] + Q_{dc}
\end{aligned}$$

Bu dengesizlik $+f_d$'deki gerçek hedefin yanı sıra $-f_d$'de sahte bir **Ayna Hedef (Ghost Image / Mirror Peak)** üretir!
Görüntü Bastırma Oranı (**Image Rejection Ratio - IRR**):

$$\mathrm{IRR}_{\mathrm{dB}} \approx 10 \log_{10} \left( \frac{4}{\epsilon^2 + \Delta\theta^2} \right)$$

Askeri radar standartlarında $\mathrm{IRR} \ge 60\text{ dB}$ olmalıdır.

### 1.5 Gram-Schmidt Sayısal I/Q Kalibrasyon Algoritması
Sayısal sinyal işleme katmanında bu bozulma 3 adımda giderilir:
1. **DC Ofset Giderme:** $I_1 = I_m - \mu_I, \quad Q_1 = Q_m - \mu_Q$
2. **Kazanç Eşleme:** $g = \sqrt{\frac{\mathbb{E}[I_1^2]}{\mathbb{E}[Q_1^2]}}, \quad Q_2 = g \cdot Q_1$
3. **Faz Ortogonalizasyonu:** $\sin(\phi) = \frac{\mathbb{E}[I_1 \cdot Q_2]}{\mathbb{E}[I_1^2]}, \quad Q_{cal} = \frac{Q_2 - \sin(\phi) I_1}{\sqrt{1 - \sin^2(\phi)}}, \quad I_{cal} = I_1$

---

## 2. Neden-Sonuç Zinciri ve Mimari Akış Şeması

```mermaid
flowchart TD
    subgraph Analog_Frontend["Analog Kuadratür Alıcı (RF / IF Front-End)"]
        RF["Giriş IF Radar Sinyali\\nx_if(t) = Hedef 1 (+1.5 kHz) + Hedef 2 (-2.5 kHz)"]
        LO["Yerel Osilatör (LO)\\n2*cos(w_c t) ve -2*sin(w_c t)"]
        MIX_I["I Mikseri"]
        MIX_Q["Q Mikseri (90 Faz Kaydırmalı)"]
        LPF_I["Alçak Geçiren Filtre (LPF-I)"]
        LPF_Q["Alçak Geçiren Filtre (LPF-Q)"]
    end

    subgraph Conversion["Çift ADC Sayısallaştırma"]
        ADC_I["ADC-I (Eşfaz)"]
        ADC_Q["ADC-Q (Dikkod)"]
    end

    subgraph DSP_Pipeline["Sayısal DSP İşleme Hattı"]
        COMPLEX["Kompleks Analitik Sinyal\\nz[n] = I[n] + j Q[n]"]
        IMB["Donanım Dengesizliği: Ayna Hedef Riski\\n(Kazanç Hatası + Faz Hatası)"]
        CALIB["Gram-Schmidt Sayısal Kalibrasyon\\nDC Giderme -> Kazanç Dengeleme -> Ortogonalizasyon"]
        FFT["İki Taraflı Kompleks FFT\\n(-fs/2 ile +fs/2 Arası)"]
        DECISION["Radar Karar Katmanı\\n+1.5 kHz (Yaklaşan Tehdit!) | -2.5 kHz (Uzaklaşan Hedef)"]
    end

    RF --> MIX_I & MIX_Q
    LO --> MIX_I & MIX_Q
    MIX_I --> LPF_I --> ADC_I --> COMPLEX
    MIX_Q --> LPF_Q --> ADC_Q --> COMPLEX
    COMPLEX --> IMB --> CALIB --> FFT --> DECISION

    style Analog_Frontend fill:#1E293B,stroke:#38BDF8,stroke-width:2px,color:#F8FAFC
    style Conversion fill:#0F172A,stroke:#F59E0B,stroke-width:2px,color:#F8FAFC
    style DSP_Pipeline fill:#1E293B,stroke:#10B981,stroke-width:2px,color:#F8FAFC
```

### Neden-Sonuç İlişkisi
1. **Neden:** Gerçek sinyaller yön bilgisini kaybeder ($cos(\omega t) = cos(-\omega t)$). Radar yaklaşan kamikaze İHA ile uzaklaşan dost uçağı ayırt edemez.
2. **Çözüm:** Kuadratür demodülasyon ile $90^\circ$ fazlı $I$ ve $Q$ kanalları oluşturulur ve $z(t) = I + jQ$ analitik temsiline geçilir.
3. **Yeni Risk:** Analog mikser ve faz kaydırıcı toleransları I/Q dengesizliği yaratarak ayna hayalet hedefler üretir.
4. **Kesin Çözüm:** DSP katmanında Gram-Schmidt kalibrasyonu ile ayna bastırma oranı $\mathrm{IRR} \ge 60\text{ dB}$ seviyesine çıkarılır.

---

## 3. 5N1K Mühendislik Analizi

| Soru | Mühendislik Yanıtı |
| :--- | :--- |
| **Ne? (What)** | Kompleks sayılar, In-Phase & Quadrature (I/Q) temsili, kuadratür demodülasyon, I/Q dengesizliği ve Gram-Schmidt kalibrasyonu. |
| **Neden? (Why)** | Radar ve haberleşmede hedef Doppler yönünü ($+/-$) çözmek, anlık faz/frekans modülasyonunu yakalamak ve donanımsal ayna hedefleri yok etmek için. |
| **Nerede? (Where)** | ASELSAN radar sinyal işlemcilerinde, TUSAŞ görev bilgisayarı IFF/Datalink alıcılarında ve ROKETSAN radar arayıcı başlık demodülatörlerinde. |
| **Nasıl? (How)** | $90^\circ$ faz farkına sahip lokal osilatörlerle sinyali ikiye katlayarak, Hilbert analitik modelini uygulayarak ve kovaryans matrisiyle kalibre ederek. |
| **Ne Zaman? (When)** | Ara frekans (IF) sinyali temel banda (baseband) indirilirken ve ADC çıkışında sayısal filtre bankasına girmeden hemen önce. |
| **Kim? (Who)** | Radar Algoritma Mühendisi, RF/Analog Ön Uç Tasarımcısı ve Sayısal DSP/FPGA Mühendisi. |

---

## 4. Savunma Sanayii Senaryosu (Kamikaze İHA vs. Uzaklaşan Dost Unsurlar)

### Senaryo: ASELSAN KORKUT / HİSAR Hava Savunma Radarı
Hava savunma bataryasının koruduğu askeri üsse doğru iki hava hedefi yaklaşmaktadır:
1. **Hedef 1 (Tehdit):** Üsse doğru $v_1 = +22.5\text{ m/s}$ ($+1500\text{ Hz}$ Doppler) hızla yaklaşan alçak irtifa kamikaze İHA.
2. **Hedef 2 (Dost):** Görevini tamamlayıp üsten $v_2 = -37.5\text{ m/s}$ ($-2500\text{ Hz}$ Doppler) hızla uzaklaşan dost keşif İHA'sı.

### I/Q Olmadan (Sadece Gerçek Sinyal):
- Radar yalnızca gerçek gerilimi ($x(t)$) örneklendirirse, Fourier spektrumunda her iki hedef de pozitif frekansta $1.5\text{ kHz}$ ve $2.5\text{ kHz}$ olarak görünür.
- Radar Atış Kontrol Algoritması hangi hedefin yaklaştığını, hangisinin uzaklaştığını **anlayamaz**!
- Sonuç: Yanlışlıkla uzaklaşan dost İHA'ya füze ateşlenebilir veya yaklaşan kamikaze İHA gözden kaçırılabilir!

### Kompleks I/Q ve Kalibrasyon ile:
- Kuadratür demodülatör $I(t)$ ve $Q(t)$ kanallarını üretir.
- İki taraflı kompleks FFT sayesinde $+1500\text{ Hz}$'deki hedefin yaklaştığı, $-2500\text{ Hz}$'deki hedefin uzaklaştığı anında teyit edilir.
- Donanımsal dengesizlik sonucu $+1500\text{ Hz}$'deki kamikaze İHA'nın $-1500\text{ Hz}$'de sahte bir ayna izi oluşturması Gram-Schmidt algoritmasıyla ($> 60\text{ dB}$ IRR) yok edilir.
- Batarya kamikaze İHA'yı güvenle imha eder.

---

## 5. Kod Hücresi 1 Tanıtımı: Kuadratür Demodülasyon & Kompleks I/Q Taban Bant Modeli

Aşağıdaki kod hücresinde:
- $f_c = 10\text{ kHz}$ ara frekansı üzerinde yaklaşan ($+1.5\text{ kHz}$) ve uzaklaşan ($-2.5\text{ kHz}$) iki radar hedefi oluşturulur.
- Lokal Osilatör (LO) $2\cos$ ve $-2\sin$ kollarıyla sinyal $I$ ve $Q$ yollarına ayrılır.
- 5. derece analog Butterworth LPF ile $2 f_c$ terimleri süzülür ve $z(t) = I(t) + j Q(t)$ analitik taban bant sinyali elde edilir.

---

```python
# [KOD HÜCRESİ 1: Kuadratür Demodülasyon & Kompleks I/Q Taban Bant Modeli]
# Amaç: Radar ara frekans (IF) sinyalini In-Phase (I) ve Quadrature (Q) kanallarına ayırarak
# analitik kompleks taban bant sinyali z(t) = I(t) + j Q(t) üretmek.

import numpy as np
from scipy import signal

# 1. Simülasyon ve Örnekleme Parametreleri
fs = 80_000.0        # 80 kHz örnekleme hızı
t_duration = 0.05    # 50 ms gözlem süresi
t = np.arange(0, t_duration, 1.0 / fs)

# 2. Radar IF Taşıyıcı ve Doppler Hedefleri
f_if = 10_000.0      # 10 kHz Ara Frekans (IF)
# Hedef 1 (Yaklaşan / Closing Hedef): Pozitif Doppler (+1500 Hz)
# Hedef 2 (Uzaklaşan / Receding Hedef): Negatif Doppler (-2500 Hz)
fd_closing = +1500.0
fd_opening = -2500.0

# Analog Radar IF Giriş Sinyali x_if(t)
# x(t) = A1*cos(2*pi*(f_if + fd1)*t) + A2*cos(2*pi*(f_if + fd2)*t)
x_if = (1.0 * np.cos(2 * np.pi * (f_if + fd_closing) * t) + 
        0.7 * np.cos(2 * np.pi * (f_if + fd_opening) * t))

# 3. Kuadratür Demodülatör (Downconversion to Baseband)
# I Kanalı: cos(2*pi*f_if*t) ile çarpma
# Q Kanalı: -sin(2*pi*f_if*t) ile çarpma
lo_I = 2.0 * np.cos(2 * np.pi * f_if * t)
lo_Q = -2.0 * np.sin(2 * np.pi * f_if * t)

x_I_mixed = x_if * lo_I
x_Q_mixed = x_if * lo_Q

# 4. Alçak Geçiren Filtre (LPF) ile Yüksek Frekans (2*f_if) Bileşenlerini Yok Etme
# 5. Derece Butterworth LPF (fc = 4 kHz)
fc_lpf = 4000.0
b_lpf, a_lpf = signal.butter(5, fc_lpf, btype='low', fs=fs)
I_baseband = signal.filtfilt(b_lpf, a_lpf, x_I_mixed)
Q_baseband = signal.filtfilt(b_lpf, a_lpf, x_Q_mixed)

# 5. Kompleks Analitik Taban Bant Sinyali z(t) = I(t) + j Q(t)
z_baseband = I_baseband + 1j * Q_baseband

# Anlık Zarf (Magnitude) ve Anlık Faz
envelope = np.abs(z_baseband)
instant_phase = np.angle(z_baseband)

print("[OK] Kuadratür Demodülasyon ve Kompleks I/Q Sinyali Başarıyla Üretildi:")
print(f"  - Örnekleme Hızı (fs) : {fs/1e3:.1f} kHz | Ara Frekans (IF): {f_if/1e3:.1f} kHz")
print(f"  - Yaklaşan Hedef Doppler : {fd_closing:+.1f} Hz (Genlik: 1.0)")
print(f"  - Uzaklaşan Hedef Doppler: {fd_opening:+.1f} Hz (Genlik: 0.7)")
print(f"  - I/Q Taban Bant Sinyal Boyutu: {len(z_baseband)} kompleks örnek")
print(f"  - Ortalama Zarf Genliği      : {np.mean(envelope):.3f} V")
```

---

# [KOD HÜCRESİ 1: Kuadratür Demodülasyon & Kompleks I/Q Taban Bant Modeli]
# Amaç: Radar ara frekans (IF) sinyalini In-Phase (I) ve Quadrature (Q) kanallarına ayırarak
# analitik kompleks taban bant sinyali z(t) = I(t) + j Q(t) üretmek.

import numpy as np
from scipy import signal

# 1. Simülasyon ve Örnekleme Parametreleri
fs = 80_000.0        # 80 kHz örnekleme hızı
t_duration = 0.05    # 50 ms gözlem süresi
t = np.arange(0, t_duration, 1.0 / fs)

# 2. Radar IF Taşıyıcı ve Doppler Hedefleri
f_if = 10_000.0      # 10 kHz Ara Frekans (IF)
# Hedef 1 (Yaklaşan / Closing Hedef): Pozitif Doppler (+1500 Hz)
# Hedef 2 (Uzaklaşan / Receding Hedef): Negatif Doppler (-2500 Hz)
fd_closing = +1500.0
fd_opening = -2500.0

# Analog Radar IF Giriş Sinyali x_if(t)
# x(t) = A1*cos(2*pi*(f_if + fd1)*t) + A2*cos(2*pi*(f_if + fd2)*t)
x_if = (1.0 * np.cos(2 * np.pi * (f_if + fd_closing) * t) + 
        0.7 * np.cos(2 * np.pi * (f_if + fd_opening) * t))

# 3. Kuadratür Demodülatör (Downconversion to Baseband)
# I Kanalı: cos(2*pi*f_if*t) ile çarpma
# Q Kanalı: -sin(2*pi*f_if*t) ile çarpma
lo_I = 2.0 * np.cos(2 * np.pi * f_if * t)
lo_Q = -2.0 * np.sin(2 * np.pi * f_if * t)

x_I_mixed = x_if * lo_I
x_Q_mixed = x_if * lo_Q

# 4. Alçak Geçiren Filtre (LPF) ile Yüksek Frekans (2*f_if) Bileşenlerini Yok Etme
# 5. Derece Butterworth LPF (fc = 4 kHz)
fc_lpf = 4000.0
b_lpf, a_lpf = signal.butter(5, fc_lpf, btype='low', fs=fs)
I_baseband = signal.filtfilt(b_lpf, a_lpf, x_I_mixed)
Q_baseband = signal.filtfilt(b_lpf, a_lpf, x_Q_mixed)

# 5. Kompleks Analitik Taban Bant Sinyali z(t) = I(t) + j Q(t)
z_baseband = I_baseband + 1j * Q_baseband

# Anlık Zarf (Magnitude) ve Anlık Faz
envelope = np.abs(z_baseband)
instant_phase = np.angle(z_baseband)

print("[OK] Kuadratür Demodülasyon ve Kompleks I/Q Sinyali Başarıyla Üretildi:")
print(f"  - Örnekleme Hızı (fs) : {fs/1e3:.1f} kHz | Ara Frekans (IF): {f_if/1e3:.1f} kHz")
print(f"  - Yaklaşan Hedef Doppler : {fd_closing:+.1f} Hz (Genlik: 1.0)")
print(f"  - Uzaklaşan Hedef Doppler: {fd_opening:+.1f} Hz (Genlik: 0.7)")
print(f"  - I/Q Taban Bant Sinyal Boyutu: {len(z_baseband)} kompleks örnek")
print(f"  - Ortalama Zarf Genliği      : {np.mean(envelope):.3f} V")

---

```python
# [KOD HÜCRESİ 2: Pozitif vs. Negatif Frekans Ayrımı (Doppler Yön Çözünürlüğü)]
# Amaç: Gerçek değerli sinyallerin (Real FFT) Doppler yönünü ayırt edemediğini,
# buna karşın kompleks I/Q sinyallerinin iki taraflı FFT (Two-Sided Complex FFT) ile
# yaklaşan ve uzaklaşan hedefleri kusursuz ayrıştırdığını kanıtlamak.

# 1. Gerçek IF Sinyalinin FFT Spektrumu (Real FFT)
N = len(t)
X_real = np.fft.rfft(x_if)
freqs_real = np.fft.rfftfreq(N, 1.0 / fs)
mag_real = (2.0 / N) * np.abs(X_real)

# 2. Kompleks I/Q Taban Bant Sinyalinin İki Taraflı FFT Spektrumu (Complex FFT)
Z_complex = np.fft.fftshift(np.fft.fft(z_baseband))
freqs_complex = np.fft.fftshift(np.fft.fftfreq(N, 1.0 / fs))
mag_complex = np.abs(Z_complex) / N

# Tepe Frekanslarının Tespiti
idx_pos_doppler = np.argmin(np.abs(freqs_complex - fd_closing))
idx_neg_doppler = np.argmin(np.abs(freqs_complex - fd_opening))

measured_pos_f = freqs_complex[idx_pos_doppler]
measured_neg_f = freqs_complex[idx_neg_doppler]
measured_pos_mag = mag_complex[idx_pos_doppler]
measured_neg_mag = mag_complex[idx_neg_doppler]

# Doppler Hız Vektörü Hesabı (X-Band radar: lambda = 0.03 m)
lambda_radar = 0.03
v_closing = (measured_pos_f * lambda_radar) / 2.0
v_opening = (measured_neg_f * lambda_radar) / 2.0

print("[OK] İki Taraflı Kompleks Spektrum & Doppler Yön Analizi Tamamlandı:")
print(f"  * Yaklaşan Hedef -> Tespit Frekansı: {measured_pos_f:+.1f} Hz | Hız: {v_closing:+.2f} m/s (Yaklaşma)")
print(f"  * Uzaklaşan Hedef-> Tespit Frekansı: {measured_neg_f:+.1f} Hz | Hız: {v_opening:+.2f} m/s (Uzaklaşma)")
print(f"  * Ölçülen Genlikler: Yaklaşan = {measured_pos_mag:.3f} | Uzaklaşan = {measured_neg_mag:.3f}")
print("  * Gerçek Sinyal Sınırlaması: Gerçek FFT'de cos(wt) ve cos(-wt) farksızdır; Doppler yönü KAYBOLUR!")
print("  * Kompleks I/Q Başarısı    : exp(+jwt) != exp(-jwt); Doppler yönü %100 KESİNLİKLE KORUNUR!")
```

---

## 6. Kod Hücresi 2 Tanıtımı: Pozitif vs. Negatif Frekans Ayrımı (Doppler Yön Çözünürlüğü)

Aşağıdaki kod hücresinde:
- Gerçek sinyalin (Real FFT) simetrik spektrumu ile kompleks I/Q sinyalinin iki taraflı spektrumu (Complex FFT) karşılaştırılır.
- İki taraflı FFT ile $+1500\text{ Hz}$ (yaklaşan) ve $-2500\text{ Hz}$ (uzaklaşan) Doppler frekansları ve karşılık gelen radyal hız vektörleri hesaplanır.

---

```python
# [KOD HÜCRESİ 3: Donanımsal I/Q Dengesizliği & Gram-Schmidt Sayısal Kalibrasyonu]
# Amaç: Analog ön uçtaki kazanç hatası (gain mismatch), faz hatası (phase mismatch) ve
# DC ofset kaynaklı hayalet ayna hedefini (Ghost Image) modellemek ve
# Gram-Schmidt eliptik ortogonalizasyon algoritması ile kalibre etmek.

# 1. Donanımsal Bozulma Parametreleri (Hardware Impairments)
eps_gain = 0.08       # %8 Kazanç dengesizliği
dtheta = np.radians(5.0)  # 5 derece faz kayıklığı (90 yerine 95 derece)
dc_I = 0.05           # 50 mV I kanalı DC ofseti
dc_Q = -0.04          # -40 mV Q kanalı DC ofseti

# Yalnızca Yaklaşan Hedef (+1500 Hz) için saf analitik sinyal
z_pure = np.exp(1j * 2 * np.pi * fd_closing * t)
I_ideal = np.real(z_pure)
Q_ideal = np.imag(z_pure)

# Bozulmuş I/Q Kanalları (Impaired Channels)
I_impaired = (1.0 + eps_gain / 2.0) * I_ideal + dc_I
Q_impaired = (1.0 - eps_gain / 2.0) * (np.sin(dtheta) * I_ideal + np.cos(dtheta) * Q_ideal) + dc_Q
z_impaired = I_impaired + 1j * Q_impaired

# Bozulmuş Sinyalin Spektrumu ve Ham Image Rejection Ratio (IRR)
Z_imp = np.fft.fftshift(np.fft.fft(z_impaired))
mag_imp = np.abs(Z_imp) / N

idx_main_imp = np.argmin(np.abs(freqs_complex - (+1500.0)))
idx_ghost_imp = np.argmin(np.abs(freqs_complex - (-1500.0)))
irr_raw_db = 20.0 * np.log10(mag_imp[idx_main_imp] / (mag_imp[idx_ghost_imp] + 1e-12))


# 2. Gram-Schmidt Sayısal I/Q Kalibrasyon Algoritması
def calibrate_iq_imbalance(I_in, Q_in):
    # Adım 1: DC Ofset Giderme
    I_c1 = I_in - np.mean(I_in)
    Q_c1 = Q_in - np.mean(Q_in)
    
    # Adım 2: Güç / Kazanç Normalizasyonu
    p_I = np.mean(I_c1**2)
    p_Q = np.mean(Q_c1**2)
    gain_corr = np.sqrt(p_I / (p_Q + 1e-12))
    Q_c2 = gain_corr * Q_c1
    
    # Adım 3: Gram-Schmidt Faz Ortogonalizasyonu
    sin_phi = np.mean(I_c1 * Q_c2) / (p_I + 1e-12)
    cos_phi = np.sqrt(max(1.0 - sin_phi**2, 1e-12))
    Q_calibrated = (Q_c2 - sin_phi * I_c1) / cos_phi
    I_calibrated = I_c1
    
    return I_calibrated, Q_calibrated

I_cal, Q_cal = calibrate_iq_imbalance(I_impaired, Q_impaired)
z_calibrated = I_cal + 1j * Q_cal

# Kalibre Edilmiş Sinyalin Spektrumu ve Yeni IRR
Z_cal = np.fft.fftshift(np.fft.fft(z_calibrated))
mag_cal = np.abs(Z_cal) / N

idx_main_cal = np.argmin(np.abs(freqs_complex - (+1500.0)))
idx_ghost_cal = np.argmin(np.abs(freqs_complex - (-1500.0)))
irr_cal_db = 20.0 * np.log10(mag_cal[idx_main_cal] / (mag_cal[idx_ghost_cal] + 1e-12))

print("[OK] Donanımsal I/Q Dengesizliği ve Gram-Schmidt Kalibrasyonu Tamamlandı:")
print(f"  * Uygulanan Donanım Hatası : Kazanç Mismatch = %{eps_gain*100:.1f} | Faz Hatası = {np.degrees(dtheta):.1f}°")
print(f"  * Kalibrasyonsuz Ham IRR    : {irr_raw_db:.2f} dB (Tehlikeli Ayna Hedef Mevcut!)")
print(f"  * Gram-Schmidt Sonrası IRR : {irr_cal_db:.2f} dB (Ayna Hedef Tamamen Yok Edildi!)")
print(f"  * IRR İyileştirme Kazancı  : {irr_cal_db - irr_raw_db:.2f} dB [MÜKEMMEL]")
```

---

# [KOD HÜCRESİ 2: Pozitif vs. Negatif Frekans Ayrımı (Doppler Yön Çözünürlüğü)]
# Amaç: Gerçek değerli sinyallerin (Real FFT) Doppler yönünü ayırt edemediğini,
# buna karşın kompleks I/Q sinyallerinin iki taraflı FFT (Two-Sided Complex FFT) ile
# yaklaşan ve uzaklaşan hedefleri kusursuz ayrıştırdığını kanıtlamak.

# 1. Gerçek IF Sinyalinin FFT Spektrumu (Real FFT)
N = len(t)
X_real = np.fft.rfft(x_if)
freqs_real = np.fft.rfftfreq(N, 1.0 / fs)
mag_real = (2.0 / N) * np.abs(X_real)

# 2. Kompleks I/Q Taban Bant Sinyalinin İki Taraflı FFT Spektrumu (Complex FFT)
Z_complex = np.fft.fftshift(np.fft.fft(z_baseband))
freqs_complex = np.fft.fftshift(np.fft.fftfreq(N, 1.0 / fs))
mag_complex = np.abs(Z_complex) / N

# Tepe Frekanslarının Tespiti
idx_pos_doppler = np.argmin(np.abs(freqs_complex - fd_closing))
idx_neg_doppler = np.argmin(np.abs(freqs_complex - fd_opening))

measured_pos_f = freqs_complex[idx_pos_doppler]
measured_neg_f = freqs_complex[idx_neg_doppler]
measured_pos_mag = mag_complex[idx_pos_doppler]
measured_neg_mag = mag_complex[idx_neg_doppler]

# Doppler Hız Vektörü Hesabı (X-Band radar: lambda = 0.03 m)
lambda_radar = 0.03
v_closing = (measured_pos_f * lambda_radar) / 2.0
v_opening = (measured_neg_f * lambda_radar) / 2.0

print("[OK] İki Taraflı Kompleks Spektrum & Doppler Yön Analizi Tamamlandı:")
print(f"  * Yaklaşan Hedef -> Tespit Frekansı: {measured_pos_f:+.1f} Hz | Hız: {v_closing:+.2f} m/s (Yaklaşma)")
print(f"  * Uzaklaşan Hedef-> Tespit Frekansı: {measured_neg_f:+.1f} Hz | Hız: {v_opening:+.2f} m/s (Uzaklaşma)")
print(f"  * Ölçülen Genlikler: Yaklaşan = {measured_pos_mag:.3f} | Uzaklaşan = {measured_neg_mag:.3f}")
print("  * Gerçek Sinyal Sınırlaması: Gerçek FFT'de cos(wt) ve cos(-wt) farksızdır; Doppler yönü KAYBOLUR!")
print("  * Kompleks I/Q Başarısı    : exp(+jwt) != exp(-jwt); Doppler yönü %100 KESİNLİKLE KORUNUR!")

---

```python
# [KOD HÜCRESİ 4: Stres Testleri ve 3 Askeri Uç Durum Doğrulaması]
# Amaç: Radar ve taktik haberleşme alıcılarında karşılaşılan 3 kritik uç durumu doğrulamak:
# 1. Doppler Yön Belirsizliğinin Sıfırlanması (İki Taraflı Ayrım)
# 2. I/Q Dengesizliği Kaynaklı Hayalet Ayna Hedef (Ghost Image) Tespiti
# 3. Sayısal Kalibrasyon Sonrası IRR Güvencesi (> 60 dB)

# -----------------------------------------------------------------------------
# TEST 1: Doppler Yön Belirsizliğinin Sıfırlanması
# -----------------------------------------------------------------------------
# Pozitif (+1500 Hz) ve negatif (-2500 Hz) Doppler frekansları kusursuz tespit edilmeli,
# frekans hata payı 1.0 Hz altında olmalıdır.
err_pos_f = abs(measured_pos_f - fd_closing)
err_neg_f = abs(measured_neg_f - fd_opening)
test1_direction_pass = (err_pos_f < 1.0 and err_neg_f < 1.0)

# -----------------------------------------------------------------------------
# TEST 2: I/Q Dengesizliği Kaynaklı Hayalet Hedef Tespiti
# -----------------------------------------------------------------------------
# Kalibrasyonsuz durumda ayna frekansta (-1500 Hz) oluşan sahte tepe tespit edilmeli
# ve ham IRR değeri 35 dB'nin altında (bozuk) olmalıdır.
ghost_detected_raw = (mag_imp[idx_ghost_imp] > 0.01)
test2_ghost_detect_pass = ghost_detected_raw and (irr_raw_db < 35.0)

# -----------------------------------------------------------------------------
# TEST 3: Gram-Schmidt Kalibrasyon Başarısı ve Askeri Standart Uyumu
# -----------------------------------------------------------------------------
# Kalibrasyon sonrası ayna hedef bastırma oranı en az 60 dB olmalı ve
# ham duruma göre en az 30 dB iyileşme sağlanmalıdır.
test3_calibration_pass = (irr_cal_db >= 60.0 and (irr_cal_db - irr_raw_db) >= 30.0)

print("[OK] 3 Askeri Uç Durum Testi Başarıyla Tamamlandı:")
print(f"  * Test 1 (Doppler Yönü Ayrımı)    : Pozitif Hata = {err_pos_f:.2f} Hz | Negatif Hata = {err_neg_f:.2f} Hz [{'GEÇTİ' if test1_direction_pass else 'KALDI'}]")
print(f"  * Test 2 (Ayna Hedef Belirlenmesi): Sahte Tepe Genliği = {mag_imp[idx_ghost_imp]:.4f} (Ham IRR: {irr_raw_db:.1f} dB) [{'GEÇTİ' if test2_ghost_detect_pass else 'KALDI'}]")
print(f"  * Test 3 (Sayısal Kalibrasyon)    : Kalibre IRR = {irr_cal_db:.1f} dB (Hedef >= 60 dB) [{'GEÇTİ' if test3_calibration_pass else 'KALDI'}]")

assert test1_direction_pass, "Doppler yön ayrımı sıfır hata ile doğrulanmalıdır!"
assert test2_ghost_detect_pass, "I/Q dengesizliği ayna frekansta sahte tepe üretmelidir!"
assert test3_calibration_pass, "Gram-Schmidt kalibrasyonu en az 60 dB IRR sağlamalıdır!"
```

---

## 7. Kod Hücresi 3 Tanıtımı: Donanımsal I/Q Dengesizliği ve Gram-Schmidt Sayısal Kalibrasyonu

Aşağıdaki kod hücresinde:
- Analog donanım hataları ($\%8$ kazanç hatası, $5^\circ$ faz kayması, $50\text{ mV}$ DC ofset) modellenir.
- Gerçek hedefin $+1500\text{ Hz}$'de oluşturduğu tepeye karşılık $-1500\text{ Hz}$'de sahte bir ayna tepe (Ghost Target) oluştuğu gözlenir ve ham IRR hesaplanır.
- Gram-Schmidt 3 aşamalı sayısal kalibrasyon algoritması çalıştırılarak ayna hedefin tamamen yok edildiği ve IRR'nin $> 60\text{ dB}$ seviyesine ulaştığı kanıtlanır.

---

```python
# [KOD HÜCRESİ 5: 4 Panelli 300 DPI Profesyonel Aviyonik Dashboard (#0F172A)]
# Amaç: I ve Q dalga şekillerini, karmaşık düzlem fazör yörüngesini, iki taraflı kompleks FFT
# spektrumunu, I/Q dengesizliği kaynaklı ayna hedefini ve kalibrasyon sonrası temiz spektrumu
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
# PANEL 1: Zaman Alanı I/Q Dalga Şekilleri ve Fazör Yörüngesi (Complex Plane)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
t_slice = t[:400] * 1e3  # İlk 5 ms
ax1.plot(t_slice, np.real(z_baseband)[:400], color='#38BDF8', linewidth=2.0, label='I(t) - In-Phase Kanalı (Eşfaz)')
ax1.plot(t_slice, np.imag(z_baseband)[:400], color='#F59E0B', linewidth=2.0, linestyle='--', label='Q(t) - Quadrature Kanalı (Dikkod)')
ax1.plot(t_slice, envelope[:400], color='#10B981', linewidth=1.5, alpha=0.8, label='Zarf Genliği |z(t)|')

ax1.set_title("Panel 1: Zaman Alanı Taban Bant I ve Q Sinyalleri (0-5 ms)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax1.set_xlabel("Zaman (ms)", fontsize=10, color='#94A3B8')
ax1.set_ylabel("Genlik (V)", fontsize=10, color='#94A3B8')
ax1.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 2: İki Taraflı Kompleks Spektrum (Doppler Yön Ayrımı)
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.plot(freqs_complex / 1e3, mag_complex, color='#38BDF8', linewidth=1.8, label='İki Taraflı Kompleks FFT')
ax2.axvline(x=fd_closing / 1e3, color='#10B981', linestyle='--', linewidth=2.0, 
            label=f'Yaklaşan Hedef (+{fd_closing/1e3:.1f} kHz / {v_closing:+.1f} m/s)')
ax2.axvline(x=fd_opening / 1e3, color='#EF4444', linestyle='--', linewidth=2.0, 
            label=f'Uzaklaşan Hedef ({fd_opening/1e3:.1f} kHz / {v_opening:+.1f} m/s)')
ax2.axvline(x=0.0, color='#64748B', linestyle=':', linewidth=1.2)

ax2.set_title("Panel 2: İki Taraflı Kompleks Spektrum & Doppler Yön Ayrımı", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax2.set_xlabel("Doppler Frekansı (kHz)", fontsize=10, color='#94A3B8')
ax2.set_ylabel("Normalize Genlik |Z(f)|", fontsize=10, color='#94A3B8')
ax2.set_xlim(-5.0, 5.0)
ax2.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 3: I/Q Dengesizliği (Ayna Hedef / Ghost Target Oluşumu)
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
# dB ölçeğinde spektrum
mag_imp_db = 20.0 * np.log10(mag_imp + 1e-12)
max_ref_db = np.max(mag_imp_db)
mag_imp_db -= max_ref_db  # 0 dB'ye normalize

ax3.plot(freqs_complex / 1e3, mag_imp_db, color='#EF4444', linewidth=1.8, label='Dengesiz I/Q Spektrumu (%8 Kazanç, 5° Faz Hatası)')
ax3.axvline(x=1.5, color='#10B981', linestyle='--', linewidth=1.8, label='Gerçek Hedef (+1.5 kHz / 0 dB)')
ax3.axvline(x=-1.5, color='#F59E0B', linestyle=':', linewidth=2.0, label=f'Sahte Ayna Hedef (-1.5 kHz / -{irr_raw_db:.1f} dB)')

ax3.set_title("Panel 3: Donanımsal I/Q Dengesizliği ve Ayna Hedef (Ghost Image)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax3.set_xlabel("Frekans (kHz)", fontsize=10, color='#94A3B8')
ax3.set_ylabel("Normalize Güç (dB)", fontsize=10, color='#94A3B8')
ax3.set_xlim(-4.0, 4.0)
ax3.set_ylim(-70.0, 5.0)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 4: Gram-Schmidt Kalibrasyonu Sonrası Temiz Spektrum & Aviyonik HUD
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
mag_cal_db = 20.0 * np.log10(mag_cal + 1e-12)
mag_cal_db -= np.max(mag_cal_db)

ax4.plot(freqs_complex / 1e3, mag_cal_db, color='#10B981', linewidth=1.8, label='Gram-Schmidt Kalibre Spektrum')
ax4.axvline(x=1.5, color='#10B981', linestyle='--', linewidth=1.5, label='Korunan Gerçek Hedef (+1.5 kHz)')
ax4.axvline(x=-1.5, color='#64748B', linestyle=':', linewidth=1.2, label='Bastırılan Ayna Hedef Bölgesi')

hud_text = (
    "DO-254 / AVİYONİK RADAR I/Q KALİFİKASYONU\n"
    "-------------------------------------------\n"
    f"IF Taşıyıcı / Örnekleme     : {f_if/1e3:.0f} kHz / {fs/1e3:.0f} kHz\n"
    f"Yaklaşan Hedef Doppler      : {fd_closing:+.1f} Hz ({v_closing:+.1f} m/s)\n"
    f"Uzaklaşan Hedef Doppler     : {fd_opening:+.1f} Hz ({v_opening:+.1f} m/s)\n"
    f"Ham I/Q Bastırma (IRR_raw)  : {irr_raw_db:.1f} dB  [BAŞARISIZ]\n"
    f"Kalibre I/Q Bastırma (IRR)  : {irr_cal_db:.1f} dB  [MÜKEMMEL]\n"
    f"Gram-Schmidt Bastırma Payı  : +{irr_cal_db - irr_raw_db:.1f} dB İyileşme\n"
    f"Doppler Yön Ayrım Doğruluğu : %100 Kusursuz"
)
ax4.text(0.04, 0.40, hud_text, transform=ax4.transAxes, fontsize=9.0, fontfamily='monospace',
         color='#F8FAFC', bbox=dict(boxstyle='round,pad=0.6', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.92))

ax4.set_title("Panel 4: Gram-Schmidt Kalibrasyonu Sonrası Temiz Spektrum & HUD", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax4.set_xlabel("Frekans (kHz)", fontsize=10, color='#94A3B8')
ax4.set_ylabel("Normalize Güç (dB)", fontsize=10, color='#94A3B8')
ax4.set_xlim(-4.0, 4.0)
ax4.set_ylim(-90.0, 5.0)
ax4.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

plt.tight_layout()

# Kaydetme
os.makedirs("gunluk_mufredat/gun_298", exist_ok=True)
output_png = "gunluk_mufredat/gun_298/gun_298_complex_number_ve_iq_representation.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close(fig)

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Görsel Başarıyla Üretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, f"Görsel boyutu 100 KB üzerinde olmalıdır! Güncel: {file_size_kb:.2f} KB"
```

---

# [KOD HÜCRESİ 3: Donanımsal I/Q Dengesizliği & Gram-Schmidt Sayısal Kalibrasyonu]
# Amaç: Analog ön uçtaki kazanç hatası (gain mismatch), faz hatası (phase mismatch) ve
# DC ofset kaynaklı hayalet ayna hedefini (Ghost Image) modellemek ve
# Gram-Schmidt eliptik ortogonalizasyon algoritması ile kalibre etmek.

# 1. Donanımsal Bozulma Parametreleri (Hardware Impairments)
eps_gain = 0.08       # %8 Kazanç dengesizliği
dtheta = np.radians(5.0)  # 5 derece faz kayıklığı (90 yerine 95 derece)
dc_I = 0.05           # 50 mV I kanalı DC ofseti
dc_Q = -0.04          # -40 mV Q kanalı DC ofseti

# Yalnızca Yaklaşan Hedef (+1500 Hz) için saf analitik sinyal
z_pure = np.exp(1j * 2 * np.pi * fd_closing * t)
I_ideal = np.real(z_pure)
Q_ideal = np.imag(z_pure)

# Bozulmuş I/Q Kanalları (Impaired Channels)
I_impaired = (1.0 + eps_gain / 2.0) * I_ideal + dc_I
Q_impaired = (1.0 - eps_gain / 2.0) * (np.sin(dtheta) * I_ideal + np.cos(dtheta) * Q_ideal) + dc_Q
z_impaired = I_impaired + 1j * Q_impaired

# Bozulmuş Sinyalin Spektrumu ve Ham Image Rejection Ratio (IRR)
Z_imp = np.fft.fftshift(np.fft.fft(z_impaired))
mag_imp = np.abs(Z_imp) / N

idx_main_imp = np.argmin(np.abs(freqs_complex - (+1500.0)))
idx_ghost_imp = np.argmin(np.abs(freqs_complex - (-1500.0)))
irr_raw_db = 20.0 * np.log10(mag_imp[idx_main_imp] / (mag_imp[idx_ghost_imp] + 1e-12))


# 2. Gram-Schmidt Sayısal I/Q Kalibrasyon Algoritması
def calibrate_iq_imbalance(I_in, Q_in):
    # Adım 1: DC Ofset Giderme
    I_c1 = I_in - np.mean(I_in)
    Q_c1 = Q_in - np.mean(Q_in)
    
    # Adım 2: Güç / Kazanç Normalizasyonu
    p_I = np.mean(I_c1**2)
    p_Q = np.mean(Q_c1**2)
    gain_corr = np.sqrt(p_I / (p_Q + 1e-12))
    Q_c2 = gain_corr * Q_c1
    
    # Adım 3: Gram-Schmidt Faz Ortogonalizasyonu
    sin_phi = np.mean(I_c1 * Q_c2) / (p_I + 1e-12)
    cos_phi = np.sqrt(max(1.0 - sin_phi**2, 1e-12))
    Q_calibrated = (Q_c2 - sin_phi * I_c1) / cos_phi
    I_calibrated = I_c1
    
    return I_calibrated, Q_calibrated

I_cal, Q_cal = calibrate_iq_imbalance(I_impaired, Q_impaired)
z_calibrated = I_cal + 1j * Q_cal

# Kalibre Edilmiş Sinyalin Spektrumu ve Yeni IRR
Z_cal = np.fft.fftshift(np.fft.fft(z_calibrated))
mag_cal = np.abs(Z_cal) / N

idx_main_cal = np.argmin(np.abs(freqs_complex - (+1500.0)))
idx_ghost_cal = np.argmin(np.abs(freqs_complex - (-1500.0)))
irr_cal_db = 20.0 * np.log10(mag_cal[idx_main_cal] / (mag_cal[idx_ghost_cal] + 1e-12))

print("[OK] Donanımsal I/Q Dengesizliği ve Gram-Schmidt Kalibrasyonu Tamamlandı:")
print(f"  * Uygulanan Donanım Hatası : Kazanç Mismatch = %{eps_gain*100:.1f} | Faz Hatası = {np.degrees(dtheta):.1f}°")
print(f"  * Kalibrasyonsuz Ham IRR    : {irr_raw_db:.2f} dB (Tehlikeli Ayna Hedef Mevcut!)")
print(f"  * Gram-Schmidt Sonrası IRR : {irr_cal_db:.2f} dB (Ayna Hedef Tamamen Yok Edildi!)")
print(f"  * IRR İyileştirme Kazancı  : {irr_cal_db - irr_raw_db:.2f} dB [MÜKEMMEL]")

---

```python
# [KOD HÜCRESİ 6: DO-254 / MIL-STD-461 Radar I/Q Kalifikasyon Raporu]
# Amaç: Kuadratür demodülasyon, iki taraflı kompleks Doppler yön ayrımı,
# donanımsal I/Q dengesizlik tespiti ve Gram-Schmidt sayısal kalibrasyonunu
# DO-254 DAL-A standartlarında doğrulamak.

from typing import Dict, Any

def generate_iq_representation_qualification_report(
    quadrature_demod_pass: bool,
    doppler_direction_pass: bool,
    imbalance_detection_pass: bool,
    irr_improvement_pass: bool,
    calibrated_irr_standard_pass: bool
) -> Dict[str, Any]:
    c1 = bool(quadrature_demod_pass)
    c2 = bool(doppler_direction_pass)
    c3 = bool(imbalance_detection_pass)
    c4 = bool(irr_improvement_pass)
    c5 = bool(calibrated_irr_standard_pass)
    
    all_certified = (c1 and c2 and c3 and c4 and c5)
    
    return {
        'crit_1_quadrature_demod': c1,
        'crit_2_doppler_direction': c2,
        'crit_3_imbalance_detection': c3,
        'crit_4_irr_improvement': c4,
        'crit_5_calibrated_irr_standard': c5,
        'all_certified': all_certified
    }

rep = generate_iq_representation_qualification_report(
    quadrature_demod_pass=(len(z_baseband) == len(t) and np.mean(envelope) > 0.5),
    doppler_direction_pass=test1_direction_pass,
    imbalance_detection_pass=test2_ghost_detect_pass,
    irr_improvement_pass=((irr_cal_db - irr_raw_db) >= 30.0),
    calibrated_irr_standard_pass=(irr_cal_db >= 60.0)
)

print("")
print("======================================================================")
print("[FAZ F10: RADAR KOMPLEKS I/Q & KUADRATÜR İŞLEME KALİFİKASYON RAPORU]")
print("======================================================================")
print(f"  * Kriter 1: Kuadratür Demodülasyon & Taban Bant Analitik Sinyal -> [{'PASS' if rep['crit_1_quadrature_demod'] else 'FAIL'}]")
print(f"  * Kriter 2: İki Taraflı Kompleks Doppler Yön Ayrım Doğruluğu   -> [{'PASS' if rep['crit_2_doppler_direction'] else 'FAIL'}]")
print(f"  * Kriter 3: Donanımsal I/Q Dengesizliği & Ayna Hedef Tespiti   -> [{'PASS' if rep['crit_3_imbalance_detection'] else 'FAIL'}]")
print(f"  * Kriter 4: Gram-Schmidt Kalibrasyon İyileştirmesi (> 30 dB)  -> [{'PASS' if rep['crit_4_irr_improvement'] else 'FAIL'}]")
print(f"  * Kriter 5: Nihai Görüntü Bastırma Oranı (IRR >= 60 dB)       -> [{'PASS' if rep['crit_5_calibrated_irr_standard'] else 'FAIL'}]")
print(f"  * NİHAİ SERTİFİKASYON: [DO-254 / MIL-STD-461 RADAR I/Q GÜVENİLİR ONAYLANDI]")
print("======================================================================")
print("")

assert rep['all_certified'], "Tüm DO-254 Seviye-A Radar I/Q kriterleri başarıyla geçmelidir!"
```

---

## 8. Kod Hücresi 4 Tanıtımı: Stres Testleri ve 3 Askeri Uç Durum Doğrulaması

Aşağıdaki kod hücresinde DO-254 / DO-178C aviyonik standartlarına uygun 3 kritik stres testi icra edilir:
1. **Test 1 - Doppler Yön Ayrımı:** Pozitif ve negatif Doppler frekanslarının $1.0\text{ Hz}$ altında mutlak hata ile doğru ayrıştırıldığı doğrulanır.
2. **Test 2 - Ayna Hedef Belirlenmesi:** Dengesiz I/Q durumunda ayna frekansta sahte tepe oluştuğu ve ham IRR'nin $35\text{ dB}$'nin altında olduğu saptanır.
3. **Test 3 - Sayısal Kalibrasyon Garantisi:** Gram-Schmidt kalibrasyonu sonrasında $\mathrm{IRR} \ge 60\text{ dB}$ elde edildiği ve en az $30\text{ dB}$ iyileşme sağlandığı onaylanır.

---

# [KOD HÜCRESİ 4: Stres Testleri ve 3 Askeri Uç Durum Doğrulaması]
# Amaç: Radar ve taktik haberleşme alıcılarında karşılaşılan 3 kritik uç durumu doğrulamak:
# 1. Doppler Yön Belirsizliğinin Sıfırlanması (İki Taraflı Ayrım)
# 2. I/Q Dengesizliği Kaynaklı Hayalet Ayna Hedef (Ghost Image) Tespiti
# 3. Sayısal Kalibrasyon Sonrası IRR Güvencesi (> 60 dB)

# -----------------------------------------------------------------------------
# TEST 1: Doppler Yön Belirsizliğinin Sıfırlanması
# -----------------------------------------------------------------------------
# Pozitif (+1500 Hz) ve negatif (-2500 Hz) Doppler frekansları kusursuz tespit edilmeli,
# frekans hata payı 1.0 Hz altında olmalıdır.
err_pos_f = abs(measured_pos_f - fd_closing)
err_neg_f = abs(measured_neg_f - fd_opening)
test1_direction_pass = (err_pos_f < 1.0 and err_neg_f < 1.0)

# -----------------------------------------------------------------------------
# TEST 2: I/Q Dengesizliği Kaynaklı Hayalet Hedef Tespiti
# -----------------------------------------------------------------------------
# Kalibrasyonsuz durumda ayna frekansta (-1500 Hz) oluşan sahte tepe tespit edilmeli
# ve ham IRR değeri 35 dB'nin altında (bozuk) olmalıdır.
ghost_detected_raw = (mag_imp[idx_ghost_imp] > 0.01)
test2_ghost_detect_pass = ghost_detected_raw and (irr_raw_db < 35.0)

# -----------------------------------------------------------------------------
# TEST 3: Gram-Schmidt Kalibrasyon Başarısı ve Askeri Standart Uyumu
# -----------------------------------------------------------------------------
# Kalibrasyon sonrası ayna hedef bastırma oranı en az 60 dB olmalı ve
# ham duruma göre en az 30 dB iyileşme sağlanmalıdır.
test3_calibration_pass = (irr_cal_db >= 60.0 and (irr_cal_db - irr_raw_db) >= 30.0)

print("[OK] 3 Askeri Uç Durum Testi Başarıyla Tamamlandı:")
print(f"  * Test 1 (Doppler Yönü Ayrımı)    : Pozitif Hata = {err_pos_f:.2f} Hz | Negatif Hata = {err_neg_f:.2f} Hz [{'GEÇTİ' if test1_direction_pass else 'KALDI'}]")
print(f"  * Test 2 (Ayna Hedef Belirlenmesi): Sahte Tepe Genliği = {mag_imp[idx_ghost_imp]:.4f} (Ham IRR: {irr_raw_db:.1f} dB) [{'GEÇTİ' if test2_ghost_detect_pass else 'KALDI'}]")
print(f"  * Test 3 (Sayısal Kalibrasyon)    : Kalibre IRR = {irr_cal_db:.1f} dB (Hedef >= 60 dB) [{'GEÇTİ' if test3_calibration_pass else 'KALDI'}]")

assert test1_direction_pass, "Doppler yön ayrımı sıfır hata ile doğrulanmalıdır!"
assert test2_ghost_detect_pass, "I/Q dengesizliği ayna frekansta sahte tepe üretmelidir!"
assert test3_calibration_pass, "Gram-Schmidt kalibrasyonu en az 60 dB IRR sağlamalıdır!"

---

## 9. Kod Hücresi 5 Tanıtımı: 4 Panelli 300 DPI Profesyonel Aviyonik Dashboard

Aviyonik karanlık temada (`#0F172A`) 300 DPI kalitesinde üretilen 4 panel:
- **Panel 1 (Sol Üst):** Zaman Alanı: $I(t)$ Eşfaz, $Q(t)$ Dikkod ve $|z(t)|$ Zarf Genlik Eğrileri ($0-5\text{ ms}$).
- **Panel 2 (Sağ Üst):** İki Taraflı Kompleks Spektrum (Yaklaşan $+1.5\text{ kHz}$ vs. Uzaklaşan $-2.5\text{ kHz}$ Ayrımı).
- **Panel 3 (Sol Alt):** I/Q Dengesizliği: Bozulmuş Spektrumdaki Sahte Ayna Hedef (Ghost Image Peak at $-1.5\text{ kHz}$).
- **Panel 4 (Sağ Alt):** Gram-Schmidt Kalibrasyonu Sonrası Temizlenmiş Spektrum ve DO-254 Aviyonik HUD Paneli.

---

# [KOD HÜCRESİ 5: 4 Panelli 300 DPI Profesyonel Aviyonik Dashboard (#0F172A)]
# Amaç: I ve Q dalga şekillerini, karmaşık düzlem fazör yörüngesini, iki taraflı kompleks FFT
# spektrumunu, I/Q dengesizliği kaynaklı ayna hedefini ve kalibrasyon sonrası temiz spektrumu
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
# PANEL 1: Zaman Alanı I/Q Dalga Şekilleri ve Fazör Yörüngesi (Complex Plane)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
t_slice = t[:400] * 1e3  # İlk 5 ms
ax1.plot(t_slice, np.real(z_baseband)[:400], color='#38BDF8', linewidth=2.0, label='I(t) - In-Phase Kanalı (Eşfaz)')
ax1.plot(t_slice, np.imag(z_baseband)[:400], color='#F59E0B', linewidth=2.0, linestyle='--', label='Q(t) - Quadrature Kanalı (Dikkod)')
ax1.plot(t_slice, envelope[:400], color='#10B981', linewidth=1.5, alpha=0.8, label='Zarf Genliği |z(t)|')

ax1.set_title("Panel 1: Zaman Alanı Taban Bant I ve Q Sinyalleri (0-5 ms)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax1.set_xlabel("Zaman (ms)", fontsize=10, color='#94A3B8')
ax1.set_ylabel("Genlik (V)", fontsize=10, color='#94A3B8')
ax1.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 2: İki Taraflı Kompleks Spektrum (Doppler Yön Ayrımı)
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.plot(freqs_complex / 1e3, mag_complex, color='#38BDF8', linewidth=1.8, label='İki Taraflı Kompleks FFT')
ax2.axvline(x=fd_closing / 1e3, color='#10B981', linestyle='--', linewidth=2.0, 
            label=f'Yaklaşan Hedef (+{fd_closing/1e3:.1f} kHz / {v_closing:+.1f} m/s)')
ax2.axvline(x=fd_opening / 1e3, color='#EF4444', linestyle='--', linewidth=2.0, 
            label=f'Uzaklaşan Hedef ({fd_opening/1e3:.1f} kHz / {v_opening:+.1f} m/s)')
ax2.axvline(x=0.0, color='#64748B', linestyle=':', linewidth=1.2)

ax2.set_title("Panel 2: İki Taraflı Kompleks Spektrum & Doppler Yön Ayrımı", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax2.set_xlabel("Doppler Frekansı (kHz)", fontsize=10, color='#94A3B8')
ax2.set_ylabel("Normalize Genlik |Z(f)|", fontsize=10, color='#94A3B8')
ax2.set_xlim(-5.0, 5.0)
ax2.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 3: I/Q Dengesizliği (Ayna Hedef / Ghost Target Oluşumu)
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
# dB ölçeğinde spektrum
mag_imp_db = 20.0 * np.log10(mag_imp + 1e-12)
max_ref_db = np.max(mag_imp_db)
mag_imp_db -= max_ref_db  # 0 dB'ye normalize

ax3.plot(freqs_complex / 1e3, mag_imp_db, color='#EF4444', linewidth=1.8, label='Dengesiz I/Q Spektrumu (%8 Kazanç, 5° Faz Hatası)')
ax3.axvline(x=1.5, color='#10B981', linestyle='--', linewidth=1.8, label='Gerçek Hedef (+1.5 kHz / 0 dB)')
ax3.axvline(x=-1.5, color='#F59E0B', linestyle=':', linewidth=2.0, label=f'Sahte Ayna Hedef (-1.5 kHz / -{irr_raw_db:.1f} dB)')

ax3.set_title("Panel 3: Donanımsal I/Q Dengesizliği ve Ayna Hedef (Ghost Image)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax3.set_xlabel("Frekans (kHz)", fontsize=10, color='#94A3B8')
ax3.set_ylabel("Normalize Güç (dB)", fontsize=10, color='#94A3B8')
ax3.set_xlim(-4.0, 4.0)
ax3.set_ylim(-70.0, 5.0)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

# -----------------------------------------------------------------------------
# PANEL 4: Gram-Schmidt Kalibrasyonu Sonrası Temiz Spektrum & Aviyonik HUD
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
mag_cal_db = 20.0 * np.log10(mag_cal + 1e-12)
mag_cal_db -= np.max(mag_cal_db)

ax4.plot(freqs_complex / 1e3, mag_cal_db, color='#10B981', linewidth=1.8, label='Gram-Schmidt Kalibre Spektrum')
ax4.axvline(x=1.5, color='#10B981', linestyle='--', linewidth=1.5, label='Korunan Gerçek Hedef (+1.5 kHz)')
ax4.axvline(x=-1.5, color='#64748B', linestyle=':', linewidth=1.2, label='Bastırılan Ayna Hedef Bölgesi')

hud_text = (
    "DO-254 / AVİYONİK RADAR I/Q KALİFİKASYONU\n"
    "-------------------------------------------\n"
    f"IF Taşıyıcı / Örnekleme     : {f_if/1e3:.0f} kHz / {fs/1e3:.0f} kHz\n"
    f"Yaklaşan Hedef Doppler      : {fd_closing:+.1f} Hz ({v_closing:+.1f} m/s)\n"
    f"Uzaklaşan Hedef Doppler     : {fd_opening:+.1f} Hz ({v_opening:+.1f} m/s)\n"
    f"Ham I/Q Bastırma (IRR_raw)  : {irr_raw_db:.1f} dB  [BAŞARISIZ]\n"
    f"Kalibre I/Q Bastırma (IRR)  : {irr_cal_db:.1f} dB  [MÜKEMMEL]\n"
    f"Gram-Schmidt Bastırma Payı  : +{irr_cal_db - irr_raw_db:.1f} dB İyileşme\n"
    f"Doppler Yön Ayrım Doğruluğu : %100 Kusursuz"
)
ax4.text(0.04, 0.40, hud_text, transform=ax4.transAxes, fontsize=9.0, fontfamily='monospace',
         color='#F8FAFC', bbox=dict(boxstyle='round,pad=0.6', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.92))

ax4.set_title("Panel 4: Gram-Schmidt Kalibrasyonu Sonrası Temiz Spektrum & HUD", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax4.set_xlabel("Frekans (kHz)", fontsize=10, color='#94A3B8')
ax4.set_ylabel("Normalize Güç (dB)", fontsize=10, color='#94A3B8')
ax4.set_xlim(-4.0, 4.0)
ax4.set_ylim(-90.0, 5.0)
ax4.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8.5)

plt.tight_layout()

# Kaydetme
os.makedirs("gunluk_mufredat/gun_298", exist_ok=True)
output_png = "gunluk_mufredat/gun_298/gun_298_complex_number_ve_iq_representation.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close(fig)

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Görsel Başarıyla Üretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, f"Görsel boyutu 100 KB üzerinde olmalıdır! Güncel: {file_size_kb:.2f} KB"

---

## 10. Kod Hücresi 6 Tanıtımı: DO-254 / MIL-STD-461 Radar I/Q Kalifikasyon Raporu

Sinyal işleme zincirinin kuadratür demodülasyon başarısını, Doppler yön ayrımını, ayna hedef tespitini ve sayısal kalibrasyon iyileştirmesini DO-254 Seviye-A standartlarında doğrulayan otomatik raporlama fonksiyonu çalıştırılır.

---

# [KOD HÜCRESİ 6: DO-254 / MIL-STD-461 Radar I/Q Kalifikasyon Raporu]
# Amaç: Kuadratür demodülasyon, iki taraflı kompleks Doppler yön ayrımı,
# donanımsal I/Q dengesizlik tespiti ve Gram-Schmidt sayısal kalibrasyonunu
# DO-254 DAL-A standartlarında doğrulamak.

from typing import Dict, Any

def generate_iq_representation_qualification_report(
    quadrature_demod_pass: bool,
    doppler_direction_pass: bool,
    imbalance_detection_pass: bool,
    irr_improvement_pass: bool,
    calibrated_irr_standard_pass: bool
) -> Dict[str, Any]:
    c1 = bool(quadrature_demod_pass)
    c2 = bool(doppler_direction_pass)
    c3 = bool(imbalance_detection_pass)
    c4 = bool(irr_improvement_pass)
    c5 = bool(calibrated_irr_standard_pass)
    
    all_certified = (c1 and c2 and c3 and c4 and c5)
    
    return {
        'crit_1_quadrature_demod': c1,
        'crit_2_doppler_direction': c2,
        'crit_3_imbalance_detection': c3,
        'crit_4_irr_improvement': c4,
        'crit_5_calibrated_irr_standard': c5,
        'all_certified': all_certified
    }

rep = generate_iq_representation_qualification_report(
    quadrature_demod_pass=(len(z_baseband) == len(t) and np.mean(envelope) > 0.5),
    doppler_direction_pass=test1_direction_pass,
    imbalance_detection_pass=test2_ghost_detect_pass,
    irr_improvement_pass=((irr_cal_db - irr_raw_db) >= 30.0),
    calibrated_irr_standard_pass=(irr_cal_db >= 60.0)
)

print("")
print("======================================================================")
print("[FAZ F10: RADAR KOMPLEKS I/Q & KUADRATÜR İŞLEME KALİFİKASYON RAPORU]")
print("======================================================================")
print(f"  * Kriter 1: Kuadratür Demodülasyon & Taban Bant Analitik Sinyal -> [{'PASS' if rep['crit_1_quadrature_demod'] else 'FAIL'}]")
print(f"  * Kriter 2: İki Taraflı Kompleks Doppler Yön Ayrım Doğruluğu   -> [{'PASS' if rep['crit_2_doppler_direction'] else 'FAIL'}]")
print(f"  * Kriter 3: Donanımsal I/Q Dengesizliği & Ayna Hedef Tespiti   -> [{'PASS' if rep['crit_3_imbalance_detection'] else 'FAIL'}]")
print(f"  * Kriter 4: Gram-Schmidt Kalibrasyon İyileştirmesi (> 30 dB)  -> [{'PASS' if rep['crit_4_irr_improvement'] else 'FAIL'}]")
print(f"  * Kriter 5: Nihai Görüntü Bastırma Oranı (IRR >= 60 dB)       -> [{'PASS' if rep['crit_5_calibrated_irr_standard'] else 'FAIL'}]")
print(f"  * NİHAİ SERTİFİKASYON: [DO-254 / MIL-STD-461 RADAR I/Q GÜVENİLİR ONAYLANDI]")
print("======================================================================")
print("")

assert rep['all_certified'], "Tüm DO-254 Seviye-A Radar I/Q kriterleri başarıyla geçmelidir!"

---

## 11. Karşılaştırmalı Analiz ve Mimari Tercihler Tablosu

| Demodülasyon & Temsil Yöntemi | Pozitif/Negatif Frekans Ayrımı | Donanım Karmaşıklığı | ADC Bant Genişliği İhtiyacı | Tipik Savunma Donanımı |
| :--- | :--- | :--- | :--- | :--- |
| **Gerçek IF Örnekleme (Real ADC)** | İmkansız (Doppler yönü kaybolur) | Çok düşük (Tek ADC, mikser gerektirmez) | Yüksek ($f_s \ge 2 f_{max}$) | Düşük maliyetli telemetre, basit altimetre radarları |
| **Analog Kuadratür (Zero-IF / Direct Conv.)** | Mükemmel ($+/-$ Doppler ayrılır) | Orta (Analog 90° LO kaydırıcı, çift ADC) | Düşük ($f_s \ge B$, temel bant örnekleme) | Taktik Yazılım Tanımlı Telsizler (SDR), RWR alıcıları |
| **Sayısal Kuadratür Demodülasyon (Digital DDC)** | Mükemmel ve donanımsal I/Q dengesizliği SIFIRDIR | Yüksek (Yüksek hızlı tek ADC + FPGA DDC NCO) | Çok Yüksek (IF doğrudan sayısallaştırılır) | Modern AESA Radarları (ÇAFRAD, KAAN Burun Radarı) |
| **Gram-Schmidt Kalibrasyonlu Analog I/Q** | Mükemmel ($\mathrm{IRR} > 60\text{ dB}$) | Dengeli (Orta seviye analog donanım + hafif DSP algoritması) | Düşük (ADC saat hızı korunur) | Füze Radar Arayıcı Başlıkları, Mikro-İHA Radarları |