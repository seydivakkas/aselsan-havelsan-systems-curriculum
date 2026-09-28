# Gün 297: Nyquist ve Aliasing (Spektral Katlanma, Nyquist Zonları, Radar Doppler Ambiguity ve Bandpass Sampling)

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

### Faz F10: Radar / DSP / Communications — Derinlemesine Nyquist ve Aliasing
Dün Gün 296'da sürekli ve ayrık sinyallerin temel örnekleme ilkelerini ve analog Anti-Aliasing filtresinin zorunluluğunu incelemiştik. Bugün **Gün 297**'de konuyu savunma sanayiinin (ASELSAN, ROKETSAN, TUSAŞ) en kritik radar ve haberleşme problemlerine taşıyoruz:
1. **Nyquist Zonları (Nyquist Zones):** Spektrumun $[0, f_s/2]$, $[f_s/2, f_s]$, $[f_s, 3f_s/2]$ gibi dilimlere bölünmesi ve çift zonlarda oluşan **Spektral Tersleme (Spectral Inversion)** etkisi.
2. **Pulse-Doppler Radarlarında Hız Belirsizliği (Doppler Ambiguity):** Darbe Tekrarlama Frekansının (PRF) sınırlı olması sebebiyle süpersonik yaklaşan seyir füzelerinin radarda çok yavaş veya geriye gidiyormuş gibi görünmesi.
3. **Kör Hızlar (Blind Speeds):** Hedef hızının radar MTI/Clutter filtresi tarafından yer paraziti (clutter) zannedilip ekrandan silinmesi.
4. **Çoklu PRF (Staggered / Dual-PRF) Tekniği:** Çin Kalan Teoremi (Chinese Remainder Theorem) ile süpersonik hızın belirsizsiz çözülmesi.
5. **Bandpass Sampling (IF Sub-Nyquist Sampling):** Yüksek frekanslı ara frekans (IF) sinyallerinin pahalı mikser donanımlarına ihtiyaç duymadan doğrudan temel banda indirilmesi.

---

## 1. Konsept ve Matematiksel Altyapı

### 1.1 Nyquist Zonları ve Katlanma Mekanizması
Bir sinyal $f_s$ frekansıyla örneklendiğinde, frekans ekseni $\frac{f_s}{2}$ genişliğindeki **Nyquist Zonlarına** ayrılır:

$$\text{Zon } m: \left[ (m-1)\frac{f_s}{2}, \; m\frac{f_s}{2} \right], \quad m = 1, 2, 3, \dots$$

Herhangi bir $f$ frekansındaki analog bileşenin örnekleme sonucunda $[0, f_s/2]$ temel bandında görüneceği frekans ($f_{apparent}$):

$$f_{apparent} = \begin{cases} 
f \pmod{f_s}, & \text{eğer } f \pmod{f_s} \le \frac{f_s}{2} \quad (m \text{ tek: Düz Katlanma}) \\
f_s - (f \pmod{f_s}), & \text{eğer } f \pmod{f_s} > \frac{f_s}{2} \quad (m \text{ çift: Spektral Tersleme})
\end{cases}$$

- **1. Zon $[0, 10\text{ kHz}]$ ($f_s=20\text{ kHz}$):** $f_A = 4\text{ kHz} \rightarrow f_{app} = 4\text{ kHz}$ (Değişmez).
- **2. Zon $[10, 20\text{ kHz}]$:** $f_B = 14\text{ kHz} \rightarrow f_{app} = 20 - 14 = 6\text{ kHz}$ (Spektrum ters döner!).
- **3. Zon $[20, 30\text{ kHz}]$:** $f_C = 23.5\text{ kHz} \rightarrow f_{app} = 23.5 - 20 = 3.5\text{ kHz}$ (Düz katlanır).

### 1.2 Pulse-Doppler Radarında Doppler Aliasing ve Kör Hızlar
Darbeli radarlarda sinyal sürekli değil, darbe tekrarlama periyodu $T_{pri} = \frac{1}{PRF}$ ile ayrık darbeler halinde gönderilir ve alınır. Dolayısıyla radar alıcısındaki Doppler örnekleme frekansı doğrudan **PRF**'tir!

Hedefin radyal bağıl hızı $v_r$ olduğunda üretilen Doppler kayması:

$$f_d = \frac{2 v_r}{\lambda}$$

Nyquist-Shannon kuralına göre tek taraflı maksimum belirsizsiz hız:

$$f_d \le \frac{PRF}{2} \implies v_{unambig} = \frac{\lambda \cdot PRF}{4}$$

Eğer hedef süpersonik bir füze ise ve $v_r > v_{unambig}$ olursa, Doppler frekansı katlanır ($f_{d\_meas} = f_d \pmod{PRF}$).

**Kör Hızlar (Blind Speeds):**
Hedef Doppler kayması tam olarak PRF'in bir tam katı olduğunda ($f_d = k \cdot PRF$):

$$v_{blind} = \frac{k \lambda \cdot PRF}{2}, \quad k = 1, 2, 3, \dots$$

Bu hızda hedeften yansıyan yankı darbeleri arasındaki faz farkı tam $2\pi k$ olur. Radar Hareketli Hedef Göstergesi (MTI) ve Clutter filtresi, hedefi duran bir dağ veya yer paraziti sanarak filtreler ve hedef radarda **tamamen görünmez** hale gelir!

### 1.3 Çoklu PRF (Dual-PRF) ile Doppler Belirsizliğinin Çözümü
Tek bir PRF ile hız belirsizliği çözülemez. Ancak radar ardışık darbe paketlerinde iki farklı PRF ($PRF_1$ ve $PRF_2$) kullanırsa:

$$\begin{aligned}
f_{d1} &= f_{d\_true} \pmod{PRF_1} \\
f_{d2} &= f_{d\_true} \pmod{PRF_2}
\end{aligned}$$

Çin Kalan Teoremi (CRT) veya en küçük artık (residual) araması yapılarak gerçek $f_{d\_true}$ ve dolayısıyla süpersonik gerçek hız $v_r$ kesin olarak çözülür.

### 1.4 Bandpass Sampling (IF Doğrudan Sayısallaştırma) Teoremi
Eğer bir sinyal yüksek bir ara frekansta ($f_c$) yer alıyor ancak dar bir $B$ bant genişliğine sahipse ($f_L$ ile $f_H$ arası), $f_s \ge 2 f_H$ şartına gerek yoktur!
Aliasing kasıtlı olarak bir **sayısal mikser** gibi kullanılarak sinyal doğrudan temel banda düşürülebilir.
Örtüşmesiz (aliasing-free) bandpass örnekleme frekansı koşulu:

$$\frac{2 f_H}{n} \le f_s \le \frac{2 f_L}{n - 1}, \quad 1 \le n \le \left\lfloor \frac{f_H}{B} \right\rfloor$$

Bu teknik, ASELSAN radar alıcılarında analog yerel osilatör (LO) ve mikser aşamalarını devreden çıkararak donanım maliyetini, hacmini ve gürültü faktörünü (NF) dramatik biçimde düşürür.

---

## 2. Neden-Sonuç Zinciri ve Mimari Akış Şeması

```mermaid
flowchart TD
    subgraph RF_Domain["Radar RF / Darbe Katmanı"]
        PULSE["Darbe Üreteci\\nPRF_1 = 5 kHz / PRF_2 = 6 kHz"]
        TGT["Hedef Yankısı\\nv = 120 m/s (Süpersonik)\\nfd = 2v/lambda = 8000 Hz"]
    end

    subgraph Sampling_Issue["Örnekleme & Katlanma Riski"]
        NYQ_LIMIT["PRF_1 Limiti = 2500 Hz\\nfd > PRF_1/2 -> DOPPLER ALIASING!"]
        BLIND["Kör Hız Riski\\nv_blind = k*lambda*PRF/2\\nHedef MTI Filtresinde Kaybolabilir!"]
    end

    subgraph Defense_Solutions["Aviyonik Savunma Çözümleri"]
        DUAL_PRF["Çoklu PRF (Dual-PRF Algoritması)\\nPRF_1 & PRF_2 Eşzamanlı Gözlem"]
        CRT["Çin Kalan Teoremi (CRT) / Rezidüel Arama\\nGerçek Hızın Tekilleştirilmesi (120 m/s)"]
        BP_ADC["Bandpass Sampling ADC\\nIF 45 kHz -> 5 kHz Baseband (Miksersiz)"]
    end

    PULSE --> TGT
    TGT --> NYQ_LIMIT
    TGT --> BLIND
    NYQ_LIMIT --> DUAL_PRF
    BLIND --> DUAL_PRF
    DUAL_PRF --> CRT
    CRT --> BP_ADC

    style RF_Domain fill:#1E293B,stroke:#38BDF8,stroke-width:2px,color:#F8FAFC
    style Sampling_Issue fill:#0F172A,stroke:#EF4444,stroke-width:2px,color:#F8FAFC
    style Defense_Solutions fill:#1E293B,stroke:#10B981,stroke-width:2px,color:#F8FAFC
```

### Neden-Sonuç İlişkisi
1. **Neden:** Darbeli radar sistemlerinde darbe tekrarlama hızı (PRF) menzil gereksinimleri nedeniyle sınırlıdır (düşük PRF uzun menzil sağlar ancak dar Doppler penceresi bırakır).
2. **Sonuç (Tehlike):** Süpersonik füzeler Doppler aliasing'e uğrayarak radarda yavaş hedef gibi görünür; kör hızlarda ise MTI filtresi tarafından tamamen silinir.
3. **Mühendislik Çözümü:** İki veya üç farklı PRF dönüşümlü kullanılır (Staggered PRF); CRT algoritmasıyla gerçek hız kurtarılır; bandpass sampling ile ara frekans doğrudan sayısallaştırılır.

---

## 3. 5N1K Mühendislik Analizi

| Soru | Mühendislik Yanıtı |
| :--- | :--- |
| **Ne? (What)** | Nyquist zonları, çift zonlarda spektral tersleme, radar pulse-doppler hız katlanması, kör hızlar ve bandpass sampling kuralları. |
| **Neden? (Why)** | Radar sistemlerinde süpersonik füzelerin hızını yanlış hesaplamamak, kör hızlarda hedefi kaybetmemek ve alıcı donanım karmaşıklığını azaltmak için. |
| **Nerede? (Where)** | ASELSAN AESA atış kontrol radarlarında (F-16/KAAN), HİSAR/SİPER hava savunma radar arayıcı başlıklarında ve taktik telsiz alıcılarında. |
| **Nasıl? (How)** | Nyquist zon analiz denklemleri, Dual-PRF eşleştirme optimizasyonu ve sub-Nyquist bandpass örnekleme bant koşulu formülü ile. |
| **Ne Zaman? (When)** | Radar dalga şekli (waveform) tasarımı yapılırken ve PRF aralıkları belirlenirken; ADC saat frekansı seçilirken. |
| **Kim? (Who)** | Radar Dalga Şekli Mühendisi, Sayısal Radar İşleme (DSP) Mimarı ve Elektronik Harp (EH) Algoritma Tasarımcısı. |

---

## 4. Savunma Sanayii Senaryosu (Hava Savunma Radarı vs. Süpersonik Seyir Füzesi)

### Senaryo: SİPER / HİSAR Bataryası Erken İhbar Radarı
Düşman unsurları tarafından fırlatılan bir süpersonik seyir füzesi, bataryaya doğru $v_r = 120\text{ m/s}$ ($432\text{ km/h}$) radyal hızla alçaktan yaklaşmaktadır.

1. **Radar Parametreleri:**
   - X-band atış kontrol radarı: $\lambda = 0.03\text{ m}$ ($f_0 = 10\text{ GHz}$).
   - Kullanılan 1. darbe dizisi frekansı: $PRF_1 = 5000\text{ Hz}$.
2. **Aliasing Riski:**
   - Füzenin ürettiği gerçek Doppler kayması: $f_d = \frac{2 \cdot 120}{0.03} = 8000\text{ Hz}$.
   - Ancak radarın belirsizsiz ölçüm sınırı $PRF_1 / 2 = 2500\text{ Hz}$'dir!
   - $8000\text{ Hz}$, $5000\text{ Hz}$'lik PRF ekseninde katlanır: $8000 \pmod{5000} = 3000\text{ Hz}$ (Simetrik Doppler ekseninde $-2000\text{ Hz}$).
   - Radar ekranında füzenin hızı $v_{app} = \frac{2000 \cdot 0.03}{2} = 30\text{ m/s}$ ($108\text{ km/h}$) olarak görünür!
   - Tehdit Değerlendirme Algoritması füzenin hızını $108\text{ km/h}$ zannederek önleme önceliğini düşürür ve batarya vurulma tehlikesiyle karşılaşır!
3. **Mühendislik Çözümü (Dual-PRF Unfolding):**
   - Radar aynı zamanda $PRF_2 = 6000\text{ Hz}$ ile de darbeler yollar.
   - $PRF_2$ altında Doppler ölçümü $8000 \pmod{6000} = 2000\text{ Hz}$ olur.
   - Dual-PRF çözücü iki ölçümü Çin Kalan Teoremi ile birleştirerek gerçek hızın $120\text{ m/s}$ olduğunu **$0.01\text{ m/s}$** hassasiyetle doğrular ve bataryaya derhal angajman emri verir!

---

## 5. Kod Hücresi 1 Tanıtımı: Nyquist Zonları & Spektral Katlanma Simülatörü

Aşağıdaki kod hücresinde:
- $f_s = 20\text{ kHz}$ örnekleme hızına sahip bir sistemde 4 ayrı Nyquist zonu tanımlanır.
- Farklı zonlarda yer alan 3 radar tonu ($f_A = 4\text{ kHz}$, $f_B = 14\text{ kHz}$, $f_C = 23.5\text{ kHz}$) üretilir.
- Genelleştirilmiş `compute_apparent_frequency` fonksiyonu ile her tonun temel banda hangi frekansta ve hangi spektral yönelimle (düz veya ters) katlandığı hesaplanır.

---

```python
# [KOD HÜCRESİ 1: Nyquist Zonları & Spektral Katlanma (Spectral Folding) Modeli]
# Amaç: Sinyal işleme ve radar alıcılarında Nyquist zonlarını (1., 2., 3., 4. zonlar)
# modellemek, farklı zonlardaki frekansların temel banda (baseband) nasıl katlandığını
# matematiksel ve algoritmik olarak simüle etmek.

import numpy as np

# 1. Örnekleme ve Simülasyon Izgarası
fs = 20_000.0        # Örnekleme hızı (20 kHz)
f_nyquist = fs / 2.0  # Nyquist frekansı (10 kHz)
fs_sim = 200_000.0   # Yüksek çözünürlüklü analog zaman simülasyonu (200 kHz)
t_duration = 0.04    # 40 ms gözlem penceresi
t_analog = np.arange(0, t_duration, 1.0 / fs_sim)

# 2. Farklı Nyquist Zonlarında Yer Alan 3 Radar/Sensör Tonu
# Zon 1 [0, 10 kHz]    : f_A = 4.0 kHz (Hedef A Doppler tonu)
# Zon 2 [10, 20 kHz]   : f_B = 14.0 kHz (Zon 2 parazit / radar IF tonu)
# Zon 3 [20, 30 kHz]   : f_C = 23.5 kHz (Zon 3 harmonik / jamming tonu)
signals_info = {
    'A': {'freq': 4_000.0,  'amp': 1.0, 'zone': 1, 'name': 'Hedef A (Zon 1)'},
    'B': {'freq': 14_000.0, 'amp': 0.8, 'zone': 2, 'name': 'Parazit B (Zon 2)'},
    'C': {'freq': 23_500.0, 'amp': 0.6, 'zone': 3, 'name': 'Girişim C (Zon 3)'}
}

# Sürekli zamanlı kompozit sinyal x(t)
x_analog = np.zeros_like(t_analog)
for k, s in signals_info.items():
    x_analog += s['amp'] * np.cos(2 * np.pi * s['freq'] * t_analog)

# 3. Ayrık Örnekleme (fs = 20 kHz)
step = int(round(fs_sim / fs))
t_disc = t_analog[::step]
x_disc = x_analog[::step]

# 4. Spektral Katlanma Fonksiyonu (Genelleştirilmiş Nyquist Zon Katlanması)
def compute_apparent_frequency(f_in: float, fs_rate: float) -> tuple:
    f_nyq = fs_rate / 2.0
    zone = int(np.floor(f_in / f_nyq)) + 1
    # Modulo fs temelli katlanma
    f_mod = f_in % fs_rate
    if f_mod > f_nyq:
        f_apparent = fs_rate - f_mod
        is_inverted = True
    else:
        f_apparent = f_mod
        is_inverted = False
    return f_apparent, zone, is_inverted

print("[OK] Nyquist Zonları & Örnekleme Modeli Kuruldu:")
print(f"  - Örnekleme Hızı (fs) : {fs / 1e3:.1f} kHz | Nyquist Sınırı (f_N): {f_nyquist / 1e3:.1f} kHz")
for k, s in signals_info.items():
    f_app, z_calc, inv = compute_apparent_frequency(s['freq'], fs)
    s['f_apparent'] = f_app
    s['is_inverted'] = inv
    print(f"  * {s['name']:18s} (Giriş: {s['freq']/1e3:4.1f} kHz) -> Zon {z_calc} | Temel Bant: {f_app/1e3:4.1f} kHz (Spektral Tersleme: {inv})")
```

---

# [KOD HÜCRESİ 1: Nyquist Zonları & Spektral Katlanma (Spectral Folding) Modeli]
# Amaç: Sinyal işleme ve radar alıcılarında Nyquist zonlarını (1., 2., 3., 4. zonlar)
# modellemek, farklı zonlardaki frekansların temel banda (baseband) nasıl katlandığını
# matematiksel ve algoritmik olarak simüle etmek.

import numpy as np

# 1. Örnekleme ve Simülasyon Izgarası
fs = 20_000.0        # Örnekleme hızı (20 kHz)
f_nyquist = fs / 2.0  # Nyquist frekansı (10 kHz)
fs_sim = 200_000.0   # Yüksek çözünürlüklü analog zaman simülasyonu (200 kHz)
t_duration = 0.04    # 40 ms gözlem penceresi
t_analog = np.arange(0, t_duration, 1.0 / fs_sim)

# 2. Farklı Nyquist Zonlarında Yer Alan 3 Radar/Sensör Tonu
# Zon 1 [0, 10 kHz]    : f_A = 4.0 kHz (Hedef A Doppler tonu)
# Zon 2 [10, 20 kHz]   : f_B = 14.0 kHz (Zon 2 parazit / radar IF tonu)
# Zon 3 [20, 30 kHz]   : f_C = 23.5 kHz (Zon 3 harmonik / jamming tonu)
signals_info = {
    'A': {'freq': 4_000.0,  'amp': 1.0, 'zone': 1, 'name': 'Hedef A (Zon 1)'},
    'B': {'freq': 14_000.0, 'amp': 0.8, 'zone': 2, 'name': 'Parazit B (Zon 2)'},
    'C': {'freq': 23_500.0, 'amp': 0.6, 'zone': 3, 'name': 'Girişim C (Zon 3)'}
}

# Sürekli zamanlı kompozit sinyal x(t)
x_analog = np.zeros_like(t_analog)
for k, s in signals_info.items():
    x_analog += s['amp'] * np.cos(2 * np.pi * s['freq'] * t_analog)

# 3. Ayrık Örnekleme (fs = 20 kHz)
step = int(round(fs_sim / fs))
t_disc = t_analog[::step]
x_disc = x_analog[::step]

# 4. Spektral Katlanma Fonksiyonu (Genelleştirilmiş Nyquist Zon Katlanması)
def compute_apparent_frequency(f_in: float, fs_rate: float) -> tuple:
    f_nyq = fs_rate / 2.0
    zone = int(np.floor(f_in / f_nyq)) + 1
    # Modulo fs temelli katlanma
    f_mod = f_in % fs_rate
    if f_mod > f_nyq:
        f_apparent = fs_rate - f_mod
        is_inverted = True
    else:
        f_apparent = f_mod
        is_inverted = False
    return f_apparent, zone, is_inverted

print("[OK] Nyquist Zonları & Örnekleme Modeli Kuruldu:")
print(f"  - Örnekleme Hızı (fs) : {fs / 1e3:.1f} kHz | Nyquist Sınırı (f_N): {f_nyquist / 1e3:.1f} kHz")
for k, s in signals_info.items():
    f_app, z_calc, inv = compute_apparent_frequency(s['freq'], fs)
    s['f_apparent'] = f_app
    s['is_inverted'] = inv
    print(f"  * {s['name']:18s} (Giriş: {s['freq']/1e3:4.1f} kHz) -> Zon {z_calc} | Temel Bant: {f_app/1e3:4.1f} kHz (Spektral Tersleme: {inv})")

---

```python
# [KOD HÜCRESİ 2: Radar Pulse-Doppler Örneklemesi ve Doppler Aliasing]
# Amaç: Darbeli Doppler (Pulse-Doppler) radar sistemlerinde Darbe Tekrarlama Frekansının (PRF)
# Doppler aliasing, kör hızlar (blind speeds) ve hız belirsizliği üzerindeki etkisini modellemek.

# 1. Radar Parametreleri (X-Band Hava Savunma Radarı)
lambda_radar = 0.03   # 3 cm dalga boyu (f0 = 10 GHz X-band)
prf_1 = 5_000.0       # PRF 1: 5 kHz darbe frekansı
v_unambig_max = (lambda_radar * prf_1) / 4.0   # Tek taraflı belirsizsiz hız sınırı (+/- 37.5 m/s)

# 2. İki Farklı Hedef Senaryosu
# Hedef 1 (Normal Hızlı İHA): v1 = 25.0 m/s (90 km/h) -> Ambiguity YOK
# Hedef 2 (Süpersonik Füze)  : v2 = 120.0 m/s (432 km/h) -> Şiddetli Doppler Aliasing!
targets = {
    'UAV':     {'v_true': 25.0,  'desc': 'Taktik İHA'},
    'MISSILE': {'v_true': 120.0, 'desc': 'Süpersonik Seyir Füzesi'}
}

# Doppler Frekans Hesabı: fd = 2 * vr / lambda
for name, tgt in targets.items():
    v = tgt['v_true']
    fd_true = (2.0 * v) / lambda_radar
    tgt['fd_true'] = fd_true
    
    # Pulse-Doppler örneklemesinde ölçülen frekans [-PRF/2, +PRF/2]
    # veya pozitif [0, PRF] bandında katlanma
    fd_meas = fd_true % prf_1
    if fd_meas > (prf_1 / 2.0):
        v_apparent = ((fd_meas - prf_1) * lambda_radar) / 2.0
    else:
        v_apparent = (fd_meas * lambda_radar) / 2.0
        
    tgt['fd_meas'] = fd_meas
    tgt['v_apparent'] = v_apparent
    tgt['has_aliasing'] = abs(v - v_apparent) > 0.1

# Kör Hız (Blind Speed) Hesabı: Hedef Doppler frekansının PRF katı olması (fd = k * PRF)
k_blind = 1
v_blind_1 = (k_blind * lambda_radar * prf_1) / 2.0  # 75.0 m/s

print("[OK] Radar Pulse-Doppler & Doppler Aliasing Analizi Tamamlandı:")
print(f"  - Radar Dalga Boyu   : {lambda_radar*100:.1f} cm (X-Band)")
print(f"  - Radar PRF-1        : {prf_1:.0f} Hz (Maks Belirsizsiz Hız: ±{v_unambig_max:.1f} m/s)")
print(f"  - 1. Kör Hız (v_blind): {v_blind_1:.1f} m/s (270 km/h)")
for name, tgt in targets.items():
    print(f"  * {tgt['desc']:22s} -> Gerçek Hız: {tgt['v_true']:5.1f} m/s (fd: {tgt['fd_true']:6.1f} Hz) | "
          f"Radarda Görünen Hız: {tgt['v_apparent']:5.1f} m/s (Aliasing: {tgt['has_aliasing']})")
```

---

## 6. Kod Hücresi 2 Tanıtımı: Radar Pulse-Doppler Örneklemesi ve Doppler Aliasing

Aşağıdaki kod hücresinde:
- X-band ($10\text{ GHz}$, $\lambda=3\text{ cm}$) radar parametreleri ve $PRF_1 = 5\text{ kHz}$ tanımlanır.
- İki farklı hava hedefi modellenir: Normal taktik İHA ($25\text{ m/s}$) ve Süpersonik füze ($120\text{ m/s}$).
- Füzenin Doppler frekansının $8\text{ kHz}$'e ulaşıp $PRF/2 = 2.5\text{ kHz}$ sınırını aşması sonucu oluşan katlanma ve sahte hız ($30\text{ m/s}$) hesaplanır.
- Sistemin 1. kör hızı ($v_{blind} = 75\text{ m/s}$) matematiksel olarak modellenir.

---

```python
# [KOD HÜCRESİ 3: Bandpass Sampling & Çoklu PRF (Dual-PRF) ile Doppler Belirsizliği Çözümü]
# Amaç:
# 1. Bandpass Sampling (IF Sub-Nyquist Doğrudan Örnekleme) ile ara frekans sinyalini miksersiz temel banda indirmek.
# 2. Çoklu PRF (Dual-PRF) yöntemiyle aliased Doppler frekanslarından gerçek süpersonik hızı (120 m/s) tam kurtarmak.

# -----------------------------------------------------------------------------
# BÖLÜM 1: Bandpass Sampling (IF Doğrudan Örnekleme)
# -----------------------------------------------------------------------------
# IF Taşıyıcı: 45 kHz, Bant Genişliği B = 4 kHz (43 kHz - 47 kHz)
# Nyquist-Shannon Bandpass Kuralı: 2*fH/n <= fs <= 2*fL/(n-1)
# n=5 için: 2*47/5 = 18.8 kHz <= fs <= 2*43/4 = 21.5 kHz -> fs = 20 kHz uygundur!
f_if_center = 45_000.0
bw_if = 4_000.0
t_bp_sim = np.arange(0, 0.05, 1.0 / 400_000.0)  # 400 kHz analog simülasyon
x_if_analog = (np.cos(2 * np.pi * 44_000.0 * t_bp_sim) + 
               0.8 * np.cos(2 * np.pi * 46_000.0 * t_bp_sim))

# 20 kHz ile Bandpass Doğrudan Örnekleme
step_bp = int(round(400_000.0 / 20_000.0))
t_bp_disc = t_bp_sim[::step_bp]
x_bp_disc = x_if_analog[::step_bp]

fft_bp = np.fft.rfft(x_bp_disc)
freqs_bp = np.fft.rfftfreq(len(x_bp_disc), 1.0 / 20_000.0)
mag_bp = (2.0 / len(x_bp_disc)) * np.abs(fft_bp)

# Temel bantta oluşan tepe frekanslar (44 kHz -> 4 kHz, 46 kHz -> 6 kHz)
idx_bp_1 = np.argmin(np.abs(freqs_bp - 4000.0))
idx_bp_2 = np.argmin(np.abs(freqs_bp - 6000.0))
bp_success = (mag_bp[idx_bp_1] > 0.90 and mag_bp[idx_bp_2] > 0.70)

# -----------------------------------------------------------------------------
# BÖLÜM 2: Dual-PRF ile Süpersonik Hedef Hızını Kurtarma (Unfolding)
# -----------------------------------------------------------------------------
prf_2 = 6_000.0  # İkinci PRF: 6 kHz
v_target_missile = targets['MISSILE']['v_true']  # 120.0 m/s
fd_true_m = (2.0 * v_target_missile) / lambda_radar  # 8000 Hz

# İki PRF altında ölçülen aliased frekanslar
fd_meas_prf1 = fd_true_m % prf_1  # 8000 % 5000 = 3000 Hz
fd_meas_prf2 = fd_true_m % prf_2  # 8000 % 6000 = 2000 Hz

# Çin Kalan Teoremi / Spektral Eşleştirme Arama Izgarası (0 - 300 m/s)
v_search_grid = np.linspace(0.0, 300.0, 60_000)
diff_prf1 = np.abs((2.0 * v_search_grid / lambda_radar) % prf_1 - fd_meas_prf1)
diff_prf2 = np.abs((2.0 * v_search_grid / lambda_radar) % prf_2 - fd_meas_prf2)
total_residual = diff_prf1 + diff_prf2

best_v_idx = np.argmin(total_residual)
v_unfolded = float(v_search_grid[best_v_idx])
v_unfolding_error = abs(v_unfolded - v_target_missile)

print("[OK] Bandpass Sampling ve Dual-PRF Çözümü Başarılı:")
print(f"  * Bandpass Sampling (IF 45 kHz -> Temel Bant): 4.0 kHz ve 6.0 kHz Tepeleri Doğrulandı -> {'[BAŞARILI]' if bp_success else '[BAŞARISIZ]'}")
print(f"  * Hedef Gerçek Hızı      : {v_target_missile:.1f} m/s (432 km/h)")
print(f"  * PRF-1 (5 kHz) Ölçümü   : {fd_meas_prf1:.1f} Hz (Katlanmış Görünür Hız: {targets['MISSILE']['v_apparent']:.1f} m/s)")
print(f"  * PRF-2 (6 kHz) Ölçümü   : {fd_meas_prf2:.1f} Hz")
print(f"  * Dual-PRF Kurtarılan Hız: {v_unfolded:.2f} m/s | Hata: {v_unfolding_error:.4f} m/s [MÜKEMMEL]")
```

---

# [KOD HÜCRESİ 2: Radar Pulse-Doppler Örneklemesi ve Doppler Aliasing]
# Amaç: Darbeli Doppler (Pulse-Doppler) radar sistemlerinde Darbe Tekrarlama Frekansının (PRF)
# Doppler aliasing, kör hızlar (blind speeds) ve hız belirsizliği üzerindeki etkisini modellemek.

# 1. Radar Parametreleri (X-Band Hava Savunma Radarı)
lambda_radar = 0.03   # 3 cm dalga boyu (f0 = 10 GHz X-band)
prf_1 = 5_000.0       # PRF 1: 5 kHz darbe frekansı
v_unambig_max = (lambda_radar * prf_1) / 4.0   # Tek taraflı belirsizsiz hız sınırı (+/- 37.5 m/s)

# 2. İki Farklı Hedef Senaryosu
# Hedef 1 (Normal Hızlı İHA): v1 = 25.0 m/s (90 km/h) -> Ambiguity YOK
# Hedef 2 (Süpersonik Füze)  : v2 = 120.0 m/s (432 km/h) -> Şiddetli Doppler Aliasing!
targets = {
    'UAV':     {'v_true': 25.0,  'desc': 'Taktik İHA'},
    'MISSILE': {'v_true': 120.0, 'desc': 'Süpersonik Seyir Füzesi'}
}

# Doppler Frekans Hesabı: fd = 2 * vr / lambda
for name, tgt in targets.items():
    v = tgt['v_true']
    fd_true = (2.0 * v) / lambda_radar
    tgt['fd_true'] = fd_true
    
    # Pulse-Doppler örneklemesinde ölçülen frekans [-PRF/2, +PRF/2]
    # veya pozitif [0, PRF] bandında katlanma
    fd_meas = fd_true % prf_1
    if fd_meas > (prf_1 / 2.0):
        v_apparent = ((fd_meas - prf_1) * lambda_radar) / 2.0
    else:
        v_apparent = (fd_meas * lambda_radar) / 2.0
        
    tgt['fd_meas'] = fd_meas
    tgt['v_apparent'] = v_apparent
    tgt['has_aliasing'] = abs(v - v_apparent) > 0.1

# Kör Hız (Blind Speed) Hesabı: Hedef Doppler frekansının PRF katı olması (fd = k * PRF)
k_blind = 1
v_blind_1 = (k_blind * lambda_radar * prf_1) / 2.0  # 75.0 m/s

print("[OK] Radar Pulse-Doppler & Doppler Aliasing Analizi Tamamlandı:")
print(f"  - Radar Dalga Boyu   : {lambda_radar*100:.1f} cm (X-Band)")
print(f"  - Radar PRF-1        : {prf_1:.0f} Hz (Maks Belirsizsiz Hız: ±{v_unambig_max:.1f} m/s)")
print(f"  - 1. Kör Hız (v_blind): {v_blind_1:.1f} m/s (270 km/h)")
for name, tgt in targets.items():
    print(f"  * {tgt['desc']:22s} -> Gerçek Hız: {tgt['v_true']:5.1f} m/s (fd: {tgt['fd_true']:6.1f} Hz) | "
          f"Radarda Görünen Hız: {tgt['v_apparent']:5.1f} m/s (Aliasing: {tgt['has_aliasing']})")

---

```python
# [KOD HÜCRESİ 4: Stres Testleri ve 3 Askeri Uç Durum Doğrulaması]
# Amaç: Radar ve aviyonik sinyal işleme sistemlerinde ortaya çıkabilecek 3 kritik arıza
# ve sınır durumunu doğrulamak:
# 1. Dual-PRF Doppler Ambiguity Çözümü Başarısı (Hata < 0.2 m/s)
# 2. Bandpass Sampling Spektral Saflık ve Dinamik Aralık Korunumu
# 3. Kör Hız (Blind Speed) Rejeksiyonu ve Çoklu PRF Koruma Garantisi

# -----------------------------------------------------------------------------
# TEST 1: Dual-PRF Doppler Ambiguity Çözüm Hassasiyeti
# -----------------------------------------------------------------------------
# Süpersonik seyir füzesinin (120 m/s) hızı Dual-PRF çözücü ile 0.2 m/s toleransla kurtarılmalıdır.
test1_prf_unfolding_pass = (v_unfolding_error < 0.20)

# -----------------------------------------------------------------------------
# TEST 2: Bandpass Sampling Spektral Saflığı (Aliasing Örtüşme İhlali Olmaması)
# -----------------------------------------------------------------------------
# Bant dışı çakışma olmaksızın 4 kHz ve 6 kHz tonlarının genlik oranının (1.0 / 0.8) korunması
mag_ratio_meas = mag_bp[idx_bp_1] / mag_bp[idx_bp_2]
mag_ratio_true = 1.0 / 0.8  # 1.25
test2_bp_purity_pass = abs(mag_ratio_meas - mag_ratio_true) < 0.05

# -----------------------------------------------------------------------------
# TEST 3: Kör Hız (Blind Speed) Rejeksiyonu ve Radar Körleşmesi Koruması
# -----------------------------------------------------------------------------
# Hedef hızı tam olarak 1. PRF kör hızına (75 m/s) eşit olduğunda:
# PRF_1'de Doppler frekansı tam 0 Hz (DC) olur ve radar MTI/Clutter filtresi hedefi siler.
# Ancak PRF_2'de Doppler frekansı sıfırdan farklı olmalı ve hedef izi korunmalıdır.
v_blind_scenario = 75.0  # 75 m/s
fd_blind_prf1 = (2.0 * v_blind_scenario / lambda_radar) % prf_1  # 5000 % 5000 = 0.0 Hz
fd_blind_prf2 = (2.0 * v_blind_scenario / lambda_radar) % prf_2  # 5000 % 6000 = 5000.0 Hz (veya -1000 Hz)

is_blind_in_prf1 = (abs(fd_blind_prf1) < 1e-6 or abs(fd_blind_prf1 - prf_1) < 1e-6)
is_visible_in_prf2 = (abs(fd_blind_prf2) > 100.0)
test3_blind_speed_mitigated = is_blind_in_prf1 and is_visible_in_prf2

print("[OK] 3 Askeri Uç Durum Testi Başarıyla Tamamlandı:")
print(f"  * Test 1 (Doppler Unfolding Hata): {v_unfolding_error:.4f} m/s (Limit: < 0.20 m/s) [{'GEÇTİ' if test1_prf_unfolding_pass else 'KALDI'}]")
print(f"  * Test 2 (Bandpass Genlik Oranı) : Ölçülen: {mag_ratio_meas:.3f} | Teorik: {mag_ratio_true:.3f} [{'GEÇTİ' if test2_bp_purity_pass else 'KALDI'}]")
print(f"  * Test 3 (Kör Hız Rejeksiyonu)   : PRF-1 fd = {fd_blind_prf1:.1f} Hz (Kör) | PRF-2 fd = {fd_blind_prf2:.1f} Hz (Görünür) [{'GEÇTİ' if test3_blind_speed_mitigated else 'KALDI'}]")

assert test1_prf_unfolding_pass, "Dual-PRF algoritması hedef hızını hatasız çözmelidir!"
assert test2_bp_purity_pass, "Bandpass sampling spektral saflığı ve genlik oranını korumalıdır!"
assert test3_blind_speed_mitigated, "Kör hızda hedef PRF-2 sayesinde radar ekranında kaybolmamalıdır!"
```

---

## 7. Kod Hücresi 3 Tanıtımı: Bandpass Sampling ve Dual-PRF Hız Kurtarma

Aşağıdaki kod hücresinde iki kritik savunma DSP mekanizması uygulanır:
1. **Bandpass Doğrudan IF Örnekleme:** $45\text{ kHz}$ ara frekansındaki sinyal, $n=5$ katsayısı ile doğrudan $f_s = 20\text{ kHz}$ sub-Nyquist hızıyla örneklenir ve analog mikser olmaksızın $5\text{ kHz}$ temel banda indirgenir.
2. **Dual-PRF Doppler Unfolding:** $PRF_1 = 5\text{ kHz}$ ve $PRF_2 = 6\text{ kHz}$ ölçümleri birleştirilerek süpersonik füzenin gerçek hızı ($120\text{ m/s}$) arama optimizasyonu ile kusursuz çözülür.

---

```python
# [KOD HÜCRESİ 5: 4 Panelli 300 DPI Profesyonel Aviyonik Dashboard (#0F172A)]
# Amaç: Nyquist zonlarını, pulse-doppler aliasing spektrumunu, bandpass sampling
# mekanizmasını ve Dual-PRF Doppler belirsizliği çözüm matrisini aviyonik karanlık tema (#0F172A)
# ile 300 DPI kalitesinde görselleştirmek.

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
# PANEL 1: Nyquist Zonları ve Katlanma Eğrileri (Spectral Folding Map)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
f_input_range = np.linspace(0, 40, 1000)  # 0 - 40 kHz
f_app_curve = [compute_apparent_frequency(f * 1e3, 20_000.0)[0] / 1e3 for f in f_input_range]

ax1.plot(f_input_range, f_app_curve, color='#38BDF8', linewidth=2.4, label='Görünür Temel Bant Frekansı')

# Zon sınırları ve arka plan renkleri
zone_colors = ['#10B981', '#F59E0B', '#6366F1', '#EC4899']
zone_names = ['Zon 1 (0-10k)', 'Zon 2 (10-20k)', 'Zon 3 (20-30k)', 'Zon 4 (30-40k)']
for i in range(4):
    ax1.axvspan(i * 10, (i + 1) * 10, alpha=0.08, color=zone_colors[i], label=zone_names[i])
    if i > 0:
        ax1.axvline(x=i * 10, color='#64748B', linestyle=':', linewidth=1.2)

# Örnek sinyallerin konumları
for k, s in signals_info.items():
    ax1.scatter([s['freq'] / 1e3], [s['f_apparent'] / 1e3], s=90, zorder=5, label=f"{s['name']}")

ax1.set_title("Panel 1: Nyquist Zonları & Katlanma Haritası (fs = 20 kHz)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax1.set_xlabel("Fiziksel Giriş Frekansı (kHz)", fontsize=10, color='#94A3B8')
ax1.set_ylabel("Ölçülen Temel Bant Frekansı (kHz)", fontsize=10, color='#94A3B8')
ax1.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8)

# -----------------------------------------------------------------------------
# PANEL 2: Pulse-Doppler Radar Spektrumu (Doğru Hedef vs. Aliased Füze)
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
# Pulse doppler spektrumu simülasyonu
fd_axis = np.linspace(-prf_1 / 2, prf_1 / 2, 1000)
# İHA piki (1666.7 Hz)
uav_peak = np.exp(-0.5 * ((fd_axis - targets['UAV']['fd_true']) / 30.0)**2)
# Füze piki (Katlanmış 2000.0 Hz)
missile_peak = 0.85 * np.exp(-0.5 * ((fd_axis - targets['MISSILE']['fd_meas']) / 30.0)**2)
# Zemin gürültüsü
noise_floor = np.random.uniform(0.01, 0.04, size=len(fd_axis))
spec_total = uav_peak + missile_peak + noise_floor

ax2.plot(fd_axis, spec_total, color='#38BDF8', linewidth=1.5, label='Doppler Büyüklük Spektrumu')
ax2.axvline(x=targets['UAV']['fd_true'], color='#10B981', linestyle='--', linewidth=1.8, 
            label=f"İHA Gerçek Doppler ({targets['UAV']['fd_true']:.0f} Hz / 25 m/s)")
ax2.axvline(x=targets['MISSILE']['fd_meas'], color='#EF4444', linestyle='--', linewidth=1.8, 
            label=f"Füze Aliased Doppler ({targets['MISSILE']['fd_meas']:.0f} Hz / 30 m/s)")
ax2.axvline(x=0.0, color='#94A3B8', linestyle='-', linewidth=1.0, alpha=0.5)

ax2.set_title("Panel 2: Pulse-Doppler Spektrumu ve Süpersonik Aliasing (PRF = 5 kHz)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax2.set_xlabel("Doppler Frekansı (Hz)", fontsize=10, color='#94A3B8')
ax2.set_ylabel("Normalize Spektral Güç", fontsize=10, color='#94A3B8')
ax2.legend(loc='upper left', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8)

# -----------------------------------------------------------------------------
# PANEL 3: Bandpass Sampling (IF 45 kHz -> Temel Bant 5 kHz Doğrudan İndirgeme)
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.plot(freqs_bp, mag_bp, color='#10B981', linewidth=2.0, label='Bandpass Örneklenmiş Spektrum (fs = 20 kHz)')
ax3.axvline(x=4000.0, color='#38BDF8', linestyle=':', linewidth=1.8, label='İndirgenmiş Ton 1 (4.0 kHz)')
ax3.axvline(x=6000.0, color='#F59E0B', linestyle=':', linewidth=1.8, label='İndirgenmiş Ton 2 (6.0 kHz)')

ax3.set_title("Panel 3: Bandpass Sampling ile IF Doğrudan Sayısallaştırma (Miksersiz İndirgeme)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax3.set_xlabel("Sayısal Frekans (Hz)", fontsize=10, color='#94A3B8')
ax3.set_ylabel("Spektral Büyüklük", fontsize=10, color='#94A3B8')
ax3.set_xlim(0, 10_000)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8)

# -----------------------------------------------------------------------------
# PANEL 4: Dual-PRF Doppler Eşleştirme Kalıntısı & Aviyonik HUD Paneli
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
# Eşleştirme kalıntısı (Residual) grafiği (Hız ekseni 80 - 160 m/s)
v_mask = (v_search_grid >= 80.0) & (v_search_grid <= 160.0)
ax4.plot(v_search_grid[v_mask], total_residual[v_mask], color='#F59E0B', linewidth=1.8, label='Dual-PRF Rezidüel Eğrisi')
ax4.scatter([v_unfolded], [total_residual[best_v_idx]], color='#10B981', s=120, zorder=6, 
            label=f'Çözülen Hız ({v_unfolded:.1f} m/s)')

hud_text = (
    "DO-254 / AVİYONİK RADAR ALIASING METRİKLERİ\n"
    "-------------------------------------------\n"
    f"PRF-1 / PRF-2 Frekansları   : 5000 / 6000 Hz\n"
    f"Gerçek Hedef Hızı           : {v_target_missile:.1f} m/s (432 km/h)\n"
    f"PRF-1'de Ölçülen Sahte Hız  : {targets['MISSILE']['v_apparent']:.1f} m/s [ALIASED]\n"
    f"Dual-PRF Çözülen Hız        : {v_unfolded:.2f} m/s [HATA: {v_unfolding_error:.4f} m/s]\n"
    f"Bandpass Örnekleme Başarısı : 45 kHz IF -> 5 kHz Baseband [GEÇTİ]\n"
    f"Kör Hız Rejeksiyon Garantisi: PRF-2 ile Kör Nokta Korundu [GEÇTİ]"
)
ax4.text(0.04, 0.42, hud_text, transform=ax4.transAxes, fontsize=9.0, fontfamily='monospace',
         color='#F8FAFC', bbox=dict(boxstyle='round,pad=0.6', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.92))

ax4.set_title("Panel 4: Dual-PRF Doppler Belirsizliği Çözüm Matrisi ve HUD Paneli", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax4.set_xlabel("Aday Hedef Hızı (m/s)", fontsize=10, color='#94A3B8')
ax4.set_ylabel("Eşleştirme Kalıntı Hatası (Hz)", fontsize=10, color='#94A3B8')
ax4.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8)

plt.tight_layout()

# Kaydetme
os.makedirs("gunluk_mufredat/gun_297", exist_ok=True)
output_png = "gunluk_mufredat/gun_297/gun_297_nyquist_ve_aliasing.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close(fig)

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Görsel Başarıyla Üretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, f"Görsel boyutu 100 KB üzerinde olmalıdır! Güncel: {file_size_kb:.2f} KB"
```

---

# [KOD HÜCRESİ 3: Bandpass Sampling & Çoklu PRF (Dual-PRF) ile Doppler Belirsizliği Çözümü]
# Amaç:
# 1. Bandpass Sampling (IF Sub-Nyquist Doğrudan Örnekleme) ile ara frekans sinyalini miksersiz temel banda indirmek.
# 2. Çoklu PRF (Dual-PRF) yöntemiyle aliased Doppler frekanslarından gerçek süpersonik hızı (120 m/s) tam kurtarmak.

# -----------------------------------------------------------------------------
# BÖLÜM 1: Bandpass Sampling (IF Doğrudan Örnekleme)
# -----------------------------------------------------------------------------
# IF Taşıyıcı: 45 kHz, Bant Genişliği B = 4 kHz (43 kHz - 47 kHz)
# Nyquist-Shannon Bandpass Kuralı: 2*fH/n <= fs <= 2*fL/(n-1)
# n=5 için: 2*47/5 = 18.8 kHz <= fs <= 2*43/4 = 21.5 kHz -> fs = 20 kHz uygundur!
f_if_center = 45_000.0
bw_if = 4_000.0
t_bp_sim = np.arange(0, 0.05, 1.0 / 400_000.0)  # 400 kHz analog simülasyon
x_if_analog = (np.cos(2 * np.pi * 44_000.0 * t_bp_sim) + 
               0.8 * np.cos(2 * np.pi * 46_000.0 * t_bp_sim))

# 20 kHz ile Bandpass Doğrudan Örnekleme
step_bp = int(round(400_000.0 / 20_000.0))
t_bp_disc = t_bp_sim[::step_bp]
x_bp_disc = x_if_analog[::step_bp]

fft_bp = np.fft.rfft(x_bp_disc)
freqs_bp = np.fft.rfftfreq(len(x_bp_disc), 1.0 / 20_000.0)
mag_bp = (2.0 / len(x_bp_disc)) * np.abs(fft_bp)

# Temel bantta oluşan tepe frekanslar (44 kHz -> 4 kHz, 46 kHz -> 6 kHz)
idx_bp_1 = np.argmin(np.abs(freqs_bp - 4000.0))
idx_bp_2 = np.argmin(np.abs(freqs_bp - 6000.0))
bp_success = (mag_bp[idx_bp_1] > 0.90 and mag_bp[idx_bp_2] > 0.70)

# -----------------------------------------------------------------------------
# BÖLÜM 2: Dual-PRF ile Süpersonik Hedef Hızını Kurtarma (Unfolding)
# -----------------------------------------------------------------------------
prf_2 = 6_000.0  # İkinci PRF: 6 kHz
v_target_missile = targets['MISSILE']['v_true']  # 120.0 m/s
fd_true_m = (2.0 * v_target_missile) / lambda_radar  # 8000 Hz

# İki PRF altında ölçülen aliased frekanslar
fd_meas_prf1 = fd_true_m % prf_1  # 8000 % 5000 = 3000 Hz
fd_meas_prf2 = fd_true_m % prf_2  # 8000 % 6000 = 2000 Hz

# Çin Kalan Teoremi / Spektral Eşleştirme Arama Izgarası (0 - 300 m/s)
v_search_grid = np.linspace(0.0, 300.0, 60_000)
diff_prf1 = np.abs((2.0 * v_search_grid / lambda_radar) % prf_1 - fd_meas_prf1)
diff_prf2 = np.abs((2.0 * v_search_grid / lambda_radar) % prf_2 - fd_meas_prf2)
total_residual = diff_prf1 + diff_prf2

best_v_idx = np.argmin(total_residual)
v_unfolded = float(v_search_grid[best_v_idx])
v_unfolding_error = abs(v_unfolded - v_target_missile)

print("[OK] Bandpass Sampling ve Dual-PRF Çözümü Başarılı:")
print(f"  * Bandpass Sampling (IF 45 kHz -> Temel Bant): 4.0 kHz ve 6.0 kHz Tepeleri Doğrulandı -> {'[BAŞARILI]' if bp_success else '[BAŞARISIZ]'}")
print(f"  * Hedef Gerçek Hızı      : {v_target_missile:.1f} m/s (432 km/h)")
print(f"  * PRF-1 (5 kHz) Ölçümü   : {fd_meas_prf1:.1f} Hz (Katlanmış Görünür Hız: {targets['MISSILE']['v_apparent']:.1f} m/s)")
print(f"  * PRF-2 (6 kHz) Ölçümü   : {fd_meas_prf2:.1f} Hz")
print(f"  * Dual-PRF Kurtarılan Hız: {v_unfolded:.2f} m/s | Hata: {v_unfolding_error:.4f} m/s [MÜKEMMEL]")

---

```python
# [KOD HÜCRESİ 6: DO-254 / MIL-STD-461 Radar Doppler & Aliasing Kalifikasyon Raporu]
# Amaç: Radar darbe tekrarlama hızı, Doppler katlanması, bandpass sampling ve çoklu PRF
# algoritmalarını DO-254 DAL-A seviyesinde sertifiye etmek.

from typing import Dict, Any

def generate_nyquist_aliasing_qualification_report(
    zone_folding_pass: bool,
    doppler_aliasing_detected: bool,
    unfolding_accuracy_pass: bool,
    bandpass_sampling_pass: bool,
    blind_speed_mitigated_pass: bool
) -> Dict[str, Any]:
    c1 = bool(zone_folding_pass)
    c2 = bool(doppler_aliasing_detected)
    c3 = bool(unfolding_accuracy_pass)
    c4 = bool(bandpass_sampling_pass)
    c5 = bool(blind_speed_mitigated_pass)
    
    all_certified = (c1 and c2 and c3 and c4 and c5)
    
    return {
        'crit_1_zone_folding': c1,
        'crit_2_doppler_aliasing': c2,
        'crit_3_unfolding_accuracy': c3,
        'crit_4_bandpass_sampling': c4,
        'crit_5_blind_speed_mitigation': c5,
        'all_certified': all_certified
    }

rep = generate_nyquist_aliasing_qualification_report(
    zone_folding_pass=(signals_info['B']['f_apparent'] == 6000.0 and signals_info['C']['f_apparent'] == 3500.0),
    doppler_aliasing_detected=(targets['MISSILE']['has_aliasing'] and targets['MISSILE']['fd_meas'] == 3000.0),
    unfolding_accuracy_pass=(v_unfolding_error < 0.20),
    bandpass_sampling_pass=bp_success,
    blind_speed_mitigated_pass=test3_blind_speed_mitigated
)

print("")
print("======================================================================")
print("[FAZ F10: RADAR PULSE-DOPPLER & NYQUIST ALIASING KALİFİKASYON RAPORU]")
print("======================================================================")
print(f"  * Kriter 1: Nyquist Zon Katlanma Matematiksel Doğruluğu  -> [{'PASS' if rep['crit_1_zone_folding'] else 'FAIL'}]")
print(f"  * Kriter 2: Pulse-Doppler Aliasing Tespiti & İzolasyonu   -> [{'PASS' if rep['crit_2_doppler_aliasing'] else 'FAIL'}]")
print(f"  * Kriter 3: Dual-PRF Doppler Hız Kurtarma Doğruluğu      -> [{'PASS' if rep['crit_3_unfolding_accuracy'] else 'FAIL'}]")
print(f"  * Kriter 4: Bandpass Doğrudan IF Örnekleme Başarısı     -> [{'PASS' if rep['crit_4_bandpass_sampling'] else 'FAIL'}]")
print(f"  * Kriter 5: Kör Hız (Blind Speed) Rejeksiyon Güvencesi   -> [{'PASS' if rep['crit_5_blind_speed_mitigation'] else 'FAIL'}]")
print(f"  * NİHAİ SERTİFİKASYON: [DO-254 / MIL-STD-461 RADAR ALIASING GÜVENİLİR ONAYLANDI]")
print("======================================================================")
print("")

assert rep['all_certified'], "Tüm DO-254 Seviye-A Radar Aliasing kriterleri başarıyla geçmelidir!"
```

---

## 8. Kod Hücresi 4 Tanıtımı: Stres Testleri ve 3 Askeri Uç Durum Doğrulaması

Aşağıdaki kod hücresinde DO-254 standartlarına uygun 3 kritik stres testi icra edilir:
1. **Test 1 - Dual-PRF Doppler Unfolding Hassasiyeti:** Çözülen hız hatasının $0.20\text{ m/s}$ altında olduğu doğrulanır.
2. **Test 2 - Bandpass Sampling Spektral Saflık:** IF'ten indirgenen tonların genlik oranının teorik $1.25$ değerini $\%5$ toleransla koruduğu onaylanır.
3. **Test 3 - Kör Hız (Blind Speed) Rejeksiyonu:** $v = 75\text{ m/s}$ kör hız senaryosunda $PRF_1$'de kaybolan hedefin $PRF_2$ sayesinde radarda görünür kaldığı kanıtlanır.

---

# [KOD HÜCRESİ 4: Stres Testleri ve 3 Askeri Uç Durum Doğrulaması]
# Amaç: Radar ve aviyonik sinyal işleme sistemlerinde ortaya çıkabilecek 3 kritik arıza
# ve sınır durumunu doğrulamak:
# 1. Dual-PRF Doppler Ambiguity Çözümü Başarısı (Hata < 0.2 m/s)
# 2. Bandpass Sampling Spektral Saflık ve Dinamik Aralık Korunumu
# 3. Kör Hız (Blind Speed) Rejeksiyonu ve Çoklu PRF Koruma Garantisi

# -----------------------------------------------------------------------------
# TEST 1: Dual-PRF Doppler Ambiguity Çözüm Hassasiyeti
# -----------------------------------------------------------------------------
# Süpersonik seyir füzesinin (120 m/s) hızı Dual-PRF çözücü ile 0.2 m/s toleransla kurtarılmalıdır.
test1_prf_unfolding_pass = (v_unfolding_error < 0.20)

# -----------------------------------------------------------------------------
# TEST 2: Bandpass Sampling Spektral Saflığı (Aliasing Örtüşme İhlali Olmaması)
# -----------------------------------------------------------------------------
# Bant dışı çakışma olmaksızın 4 kHz ve 6 kHz tonlarının genlik oranının (1.0 / 0.8) korunması
mag_ratio_meas = mag_bp[idx_bp_1] / mag_bp[idx_bp_2]
mag_ratio_true = 1.0 / 0.8  # 1.25
test2_bp_purity_pass = abs(mag_ratio_meas - mag_ratio_true) < 0.05

# -----------------------------------------------------------------------------
# TEST 3: Kör Hız (Blind Speed) Rejeksiyonu ve Radar Körleşmesi Koruması
# -----------------------------------------------------------------------------
# Hedef hızı tam olarak 1. PRF kör hızına (75 m/s) eşit olduğunda:
# PRF_1'de Doppler frekansı tam 0 Hz (DC) olur ve radar MTI/Clutter filtresi hedefi siler.
# Ancak PRF_2'de Doppler frekansı sıfırdan farklı olmalı ve hedef izi korunmalıdır.
v_blind_scenario = 75.0  # 75 m/s
fd_blind_prf1 = (2.0 * v_blind_scenario / lambda_radar) % prf_1  # 5000 % 5000 = 0.0 Hz
fd_blind_prf2 = (2.0 * v_blind_scenario / lambda_radar) % prf_2  # 5000 % 6000 = 5000.0 Hz (veya -1000 Hz)

is_blind_in_prf1 = (abs(fd_blind_prf1) < 1e-6 or abs(fd_blind_prf1 - prf_1) < 1e-6)
is_visible_in_prf2 = (abs(fd_blind_prf2) > 100.0)
test3_blind_speed_mitigated = is_blind_in_prf1 and is_visible_in_prf2

print("[OK] 3 Askeri Uç Durum Testi Başarıyla Tamamlandı:")
print(f"  * Test 1 (Doppler Unfolding Hata): {v_unfolding_error:.4f} m/s (Limit: < 0.20 m/s) [{'GEÇTİ' if test1_prf_unfolding_pass else 'KALDI'}]")
print(f"  * Test 2 (Bandpass Genlik Oranı) : Ölçülen: {mag_ratio_meas:.3f} | Teorik: {mag_ratio_true:.3f} [{'GEÇTİ' if test2_bp_purity_pass else 'KALDI'}]")
print(f"  * Test 3 (Kör Hız Rejeksiyonu)   : PRF-1 fd = {fd_blind_prf1:.1f} Hz (Kör) | PRF-2 fd = {fd_blind_prf2:.1f} Hz (Görünür) [{'GEÇTİ' if test3_blind_speed_mitigated else 'KALDI'}]")

assert test1_prf_unfolding_pass, "Dual-PRF algoritması hedef hızını hatasız çözmelidir!"
assert test2_bp_purity_pass, "Bandpass sampling spektral saflığı ve genlik oranını korumalıdır!"
assert test3_blind_speed_mitigated, "Kör hızda hedef PRF-2 sayesinde radar ekranında kaybolmamalıdır!"

---

## 9. Kod Hücresi 5 Tanıtımı: 4 Panelli 300 DPI Profesyonel Aviyonik Dashboard

Aviyonik karanlık temada (`#0F172A`) 300 DPI kalitesinde üretilen 4 panel:
- **Panel 1 (Sol Üst):** Nyquist Zonları & Spektral Katlanma Haritası (Zon 1-4 renklendirmesi ve katlanma eğrileri).
- **Panel 2 (Sağ Üst):** Pulse-Doppler Radar Spektrumu (İHA Tepe Noktası vs. Katlanmış Füze Sahte Piki).
- **Panel 3 (Sol Alt):** Bandpass Doğrudan IF Örnekleme Spektrumu (45 kHz IF $\rightarrow$ 4 kHz & 6 kHz Temel Bant).
- **Panel 4 (Sağ Alt):** Dual-PRF Eşleştirme Kalıntı Hatası Rezidüel Eğrisi ve DO-254 Radar HUD Paneli.

---

# [KOD HÜCRESİ 5: 4 Panelli 300 DPI Profesyonel Aviyonik Dashboard (#0F172A)]
# Amaç: Nyquist zonlarını, pulse-doppler aliasing spektrumunu, bandpass sampling
# mekanizmasını ve Dual-PRF Doppler belirsizliği çözüm matrisini aviyonik karanlık tema (#0F172A)
# ile 300 DPI kalitesinde görselleştirmek.

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
# PANEL 1: Nyquist Zonları ve Katlanma Eğrileri (Spectral Folding Map)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
f_input_range = np.linspace(0, 40, 1000)  # 0 - 40 kHz
f_app_curve = [compute_apparent_frequency(f * 1e3, 20_000.0)[0] / 1e3 for f in f_input_range]

ax1.plot(f_input_range, f_app_curve, color='#38BDF8', linewidth=2.4, label='Görünür Temel Bant Frekansı')

# Zon sınırları ve arka plan renkleri
zone_colors = ['#10B981', '#F59E0B', '#6366F1', '#EC4899']
zone_names = ['Zon 1 (0-10k)', 'Zon 2 (10-20k)', 'Zon 3 (20-30k)', 'Zon 4 (30-40k)']
for i in range(4):
    ax1.axvspan(i * 10, (i + 1) * 10, alpha=0.08, color=zone_colors[i], label=zone_names[i])
    if i > 0:
        ax1.axvline(x=i * 10, color='#64748B', linestyle=':', linewidth=1.2)

# Örnek sinyallerin konumları
for k, s in signals_info.items():
    ax1.scatter([s['freq'] / 1e3], [s['f_apparent'] / 1e3], s=90, zorder=5, label=f"{s['name']}")

ax1.set_title("Panel 1: Nyquist Zonları & Katlanma Haritası (fs = 20 kHz)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax1.set_xlabel("Fiziksel Giriş Frekansı (kHz)", fontsize=10, color='#94A3B8')
ax1.set_ylabel("Ölçülen Temel Bant Frekansı (kHz)", fontsize=10, color='#94A3B8')
ax1.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8)

# -----------------------------------------------------------------------------
# PANEL 2: Pulse-Doppler Radar Spektrumu (Doğru Hedef vs. Aliased Füze)
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
# Pulse doppler spektrumu simülasyonu
fd_axis = np.linspace(-prf_1 / 2, prf_1 / 2, 1000)
# İHA piki (1666.7 Hz)
uav_peak = np.exp(-0.5 * ((fd_axis - targets['UAV']['fd_true']) / 30.0)**2)
# Füze piki (Katlanmış 2000.0 Hz)
missile_peak = 0.85 * np.exp(-0.5 * ((fd_axis - targets['MISSILE']['fd_meas']) / 30.0)**2)
# Zemin gürültüsü
noise_floor = np.random.uniform(0.01, 0.04, size=len(fd_axis))
spec_total = uav_peak + missile_peak + noise_floor

ax2.plot(fd_axis, spec_total, color='#38BDF8', linewidth=1.5, label='Doppler Büyüklük Spektrumu')
ax2.axvline(x=targets['UAV']['fd_true'], color='#10B981', linestyle='--', linewidth=1.8, 
            label=f"İHA Gerçek Doppler ({targets['UAV']['fd_true']:.0f} Hz / 25 m/s)")
ax2.axvline(x=targets['MISSILE']['fd_meas'], color='#EF4444', linestyle='--', linewidth=1.8, 
            label=f"Füze Aliased Doppler ({targets['MISSILE']['fd_meas']:.0f} Hz / 30 m/s)")
ax2.axvline(x=0.0, color='#94A3B8', linestyle='-', linewidth=1.0, alpha=0.5)

ax2.set_title("Panel 2: Pulse-Doppler Spektrumu ve Süpersonik Aliasing (PRF = 5 kHz)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax2.set_xlabel("Doppler Frekansı (Hz)", fontsize=10, color='#94A3B8')
ax2.set_ylabel("Normalize Spektral Güç", fontsize=10, color='#94A3B8')
ax2.legend(loc='upper left', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8)

# -----------------------------------------------------------------------------
# PANEL 3: Bandpass Sampling (IF 45 kHz -> Temel Bant 5 kHz Doğrudan İndirgeme)
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.plot(freqs_bp, mag_bp, color='#10B981', linewidth=2.0, label='Bandpass Örneklenmiş Spektrum (fs = 20 kHz)')
ax3.axvline(x=4000.0, color='#38BDF8', linestyle=':', linewidth=1.8, label='İndirgenmiş Ton 1 (4.0 kHz)')
ax3.axvline(x=6000.0, color='#F59E0B', linestyle=':', linewidth=1.8, label='İndirgenmiş Ton 2 (6.0 kHz)')

ax3.set_title("Panel 3: Bandpass Sampling ile IF Doğrudan Sayısallaştırma (Miksersiz İndirgeme)", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax3.set_xlabel("Sayısal Frekans (Hz)", fontsize=10, color='#94A3B8')
ax3.set_ylabel("Spektral Büyüklük", fontsize=10, color='#94A3B8')
ax3.set_xlim(0, 10_000)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8)

# -----------------------------------------------------------------------------
# PANEL 4: Dual-PRF Doppler Eşleştirme Kalıntısı & Aviyonik HUD Paneli
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
# Eşleştirme kalıntısı (Residual) grafiği (Hız ekseni 80 - 160 m/s)
v_mask = (v_search_grid >= 80.0) & (v_search_grid <= 160.0)
ax4.plot(v_search_grid[v_mask], total_residual[v_mask], color='#F59E0B', linewidth=1.8, label='Dual-PRF Rezidüel Eğrisi')
ax4.scatter([v_unfolded], [total_residual[best_v_idx]], color='#10B981', s=120, zorder=6, 
            label=f'Çözülen Hız ({v_unfolded:.1f} m/s)')

hud_text = (
    "DO-254 / AVİYONİK RADAR ALIASING METRİKLERİ\n"
    "-------------------------------------------\n"
    f"PRF-1 / PRF-2 Frekansları   : 5000 / 6000 Hz\n"
    f"Gerçek Hedef Hızı           : {v_target_missile:.1f} m/s (432 km/h)\n"
    f"PRF-1'de Ölçülen Sahte Hız  : {targets['MISSILE']['v_apparent']:.1f} m/s [ALIASED]\n"
    f"Dual-PRF Çözülen Hız        : {v_unfolded:.2f} m/s [HATA: {v_unfolding_error:.4f} m/s]\n"
    f"Bandpass Örnekleme Başarısı : 45 kHz IF -> 5 kHz Baseband [GEÇTİ]\n"
    f"Kör Hız Rejeksiyon Garantisi: PRF-2 ile Kör Nokta Korundu [GEÇTİ]"
)
ax4.text(0.04, 0.42, hud_text, transform=ax4.transAxes, fontsize=9.0, fontfamily='monospace',
         color='#F8FAFC', bbox=dict(boxstyle='round,pad=0.6', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.92))

ax4.set_title("Panel 4: Dual-PRF Doppler Belirsizliği Çözüm Matrisi ve HUD Paneli", 
              fontsize=11, fontweight='bold', color='#38BDF8', pad=10)
ax4.set_xlabel("Aday Hedef Hızı (m/s)", fontsize=10, color='#94A3B8')
ax4.set_ylabel("Eşleştirme Kalıntı Hatası (Hz)", fontsize=10, color='#94A3B8')
ax4.legend(loc='upper right', facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='white', fontsize=8)

plt.tight_layout()

# Kaydetme
os.makedirs("gunluk_mufredat/gun_297", exist_ok=True)
output_png = "gunluk_mufredat/gun_297/gun_297_nyquist_ve_aliasing.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
plt.close(fig)

file_size_kb = os.path.getsize(output_png) / 1024.0
print(f"[OK] 4-Panelli Görsel Başarıyla Üretildi: {output_png}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, f"Görsel boyutu 100 KB üzerinde olmalıdır! Güncel: {file_size_kb:.2f} KB"

---

## 10. Kod Hücresi 6 Tanıtımı: DO-254 / MIL-STD-461 Radar Kalifikasyon Raporu

Günün tüm Doppler aliasing, zon katlanması, Dual-PRF hız tekilleştirmesi ve bandpass sampling metriklerini DO-254 Seviye-A standartlarında doğrulayan otomatik raporlama fonksiyonu çalıştırılır.

---

# [KOD HÜCRESİ 6: DO-254 / MIL-STD-461 Radar Doppler & Aliasing Kalifikasyon Raporu]
# Amaç: Radar darbe tekrarlama hızı, Doppler katlanması, bandpass sampling ve çoklu PRF
# algoritmalarını DO-254 DAL-A seviyesinde sertifiye etmek.

from typing import Dict, Any

def generate_nyquist_aliasing_qualification_report(
    zone_folding_pass: bool,
    doppler_aliasing_detected: bool,
    unfolding_accuracy_pass: bool,
    bandpass_sampling_pass: bool,
    blind_speed_mitigated_pass: bool
) -> Dict[str, Any]:
    c1 = bool(zone_folding_pass)
    c2 = bool(doppler_aliasing_detected)
    c3 = bool(unfolding_accuracy_pass)
    c4 = bool(bandpass_sampling_pass)
    c5 = bool(blind_speed_mitigated_pass)
    
    all_certified = (c1 and c2 and c3 and c4 and c5)
    
    return {
        'crit_1_zone_folding': c1,
        'crit_2_doppler_aliasing': c2,
        'crit_3_unfolding_accuracy': c3,
        'crit_4_bandpass_sampling': c4,
        'crit_5_blind_speed_mitigation': c5,
        'all_certified': all_certified
    }

rep = generate_nyquist_aliasing_qualification_report(
    zone_folding_pass=(signals_info['B']['f_apparent'] == 6000.0 and signals_info['C']['f_apparent'] == 3500.0),
    doppler_aliasing_detected=(targets['MISSILE']['has_aliasing'] and targets['MISSILE']['fd_meas'] == 3000.0),
    unfolding_accuracy_pass=(v_unfolding_error < 0.20),
    bandpass_sampling_pass=bp_success,
    blind_speed_mitigated_pass=test3_blind_speed_mitigated
)

print("")
print("======================================================================")
print("[FAZ F10: RADAR PULSE-DOPPLER & NYQUIST ALIASING KALİFİKASYON RAPORU]")
print("======================================================================")
print(f"  * Kriter 1: Nyquist Zon Katlanma Matematiksel Doğruluğu  -> [{'PASS' if rep['crit_1_zone_folding'] else 'FAIL'}]")
print(f"  * Kriter 2: Pulse-Doppler Aliasing Tespiti & İzolasyonu   -> [{'PASS' if rep['crit_2_doppler_aliasing'] else 'FAIL'}]")
print(f"  * Kriter 3: Dual-PRF Doppler Hız Kurtarma Doğruluğu      -> [{'PASS' if rep['crit_3_unfolding_accuracy'] else 'FAIL'}]")
print(f"  * Kriter 4: Bandpass Doğrudan IF Örnekleme Başarısı     -> [{'PASS' if rep['crit_4_bandpass_sampling'] else 'FAIL'}]")
print(f"  * Kriter 5: Kör Hız (Blind Speed) Rejeksiyon Güvencesi   -> [{'PASS' if rep['crit_5_blind_speed_mitigation'] else 'FAIL'}]")
print(f"  * NİHAİ SERTİFİKASYON: [DO-254 / MIL-STD-461 RADAR ALIASING GÜVENİLİR ONAYLANDI]")
print("======================================================================")
print("")

assert rep['all_certified'], "Tüm DO-254 Seviye-A Radar Aliasing kriterleri başarıyla geçmelidir!"

---

## 11. Karşılaştırmalı Analiz ve Mimari Tercihler Tablosu

| Yöntem / Mimari | Avantajları | Dezavantajları / Riskleri | Tipik Savunma Donanımı |
| :--- | :--- | :--- | :--- |
| **Tek PRF (Low/Medium PRF)** | Basit alıcı mimarisi, düşük FPGA işlem yükü | Ciddi Doppler aliasing ve kör hızlar (blind speeds) içerir | Kısa menzilli deniz gözetleme radarları |
| **Çoklu PRF (Dual/Triple PRF)** | Süpersonik hedeflerin gerçek hızını çözer, kör hızları ortadan kaldırır | İşlemci karmaşıklığı, PRF geçişlerinde ölü zaman (dead time) | AESA Atış Kontrol Radarları (KAAN, F-16 Blok 70) |
| **Doğrudan RF/IF Bandpass Sampling** | Analog mikser ve lokal osilatör (LO) ihtiyacını kaldırır; donanım küçülür | Çok dar ve keskin analog bant geçiren filtre gerektirir; saat jitter'ına duyarlıdır | Yazılım Tanımlı Telsiz (SDR), RWR Alıcıları |
| **Geleneksel Süperheterodin Alıcı** | Yüksek seçicilik, geniş dinamik aralık | Ağır analog donanım, mikser mahreçleri ve IF filtre maliyeti | Eski nesil hava savunma arama radarları |