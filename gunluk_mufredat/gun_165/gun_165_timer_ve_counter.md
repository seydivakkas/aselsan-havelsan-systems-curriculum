# GÜN 165: STM32 Donanımsal Zamanlayıcılar (Timers) ve Sayaçlar (Counters), PWM, Dead-Time ve BKIN Mimarisi

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz.
```

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
![C++20](https://img.shields.io/badge/Standard-C%2B%2B20-blue.svg?style=flat-square)
![ARM Cortex-M](https://img.shields.io/badge/Architecture-ARM%20Cortex--M4%2FM7-orange.svg?style=flat-square)
![STM32 Timers](https://img.shields.io/badge/Hardware-TIM1%2FTIM8%2FTIM2-purple.svg?style=flat-square)
![Defense Grade](https://img.shields.io/badge/Domain-Avionics%20%2F%20Motor%20Control-red.svg?style=flat-square)

---

## 1. Zihinsel Model ve Mimari Büyük Resim (Timer Silikon Anatomisi)

Gömülü sistemlerde zamanı yazılımsal döngülerle (`for(int i=0; i<1000; i++)` veya `delay_ms()`) yönetmek en büyük acemiliktir. Yazılımsal gecikmeler:
1. CPU çekirdeğini meşgul ederek sistemi kilitler (yüzde 100 CPU israfı),
2. Araya giren bir kesme (`ISR`) nedeniyle zamanlamayı bozar (non-deterministik),
3. Güç tüketimini fırlatır.

**Zamanlayıcılar (Timers & Counters)**, CPU çekirdeğinden tamamen bağımsız olarak silikon üzerinde kendi başına koşan, nanosaniyelik hassasiyete sahip **donanımsal saat motorlarıdır**. CPU derin uykuda (`WFI - Wait For Interrupt`) olsa dahi donanımsal timer arka planda saymaya devam eder, tam zamanı geldiğinde PWM darbeleri üretir, motor kontrol eder veya ADC'ye donanımsal örnekleme emri verir.

STM32 mimarisinde bir Timer donanımı 3 ana temel bloktan oluşur:
1. **Zaman Tabanı Üreteci (Time Base Generator):** Giriş saatini bölen **PSC (Prescaler)**, yukarı/aşağı sayan **CNT (Counter)** ve periyodu belirleyen **ARR (Auto-Reload Register)**.
2. **Kanal Karşılaştırma / Yakalama Birimi (Capture/Compare Channels):** Her timer'da 1 ile 4 adet bağımsız kanal bulunur. `CCR` (Capture/Compare Register) yazmacı ile pinlerden darbe genişliği ölçülür (Input Capture) veya dış dünyaya milimetrik PWM üretilir (Output Compare).
3. **Gelişmiş Koruma ve Tetikleme Mantığı (Break & Dead-Time):** Motor sürücülerinde transistörlerin yanmasını önleyen **Dead-Time** jeneratörü ve acil durumlarda donanımı nanosaniyede durduran **BKIN (Break Input)** devresi.

```
    +-------------------------------------------------------------------------+
    |               STM32 DONANSIMSAL ZAMANLAYICI İÇ BLOK ŞEMASI               |
    +-------------------------------------------------------------------------+
    
    Dahili Saat (TIMxCLK) [84 MHz / 168 MHz]
             |
             v
    +-------------------+       +-------------------+       +-------------------+
    |  PRESCALER (PSC)  | ----> |   COUNTER (CNT)   | <---> | AUTO-RELOAD (ARR) |
    |  (Saat Bölücü)    |       |   (16/32-bit Say) |       |   (Periyot Eşiği) |
    +-------------------+       +-------------------+       +-------------------+
                                          |                           |
                                          |                           v
                                          |                  [ UPDATE EVENT (UEV) ]
                                          |                  (Taşma / Kesme / DMA)
                                          v
                               +---------------------+
                               | CAPTURE / COMPARE   | <--- CCR1, CCR2, CCR3, CCR4
                               | Lojik Karşılaştırıcı|
                               +---------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
             [ OUTPUT COMPARE / PWM ]              [ INPUT CAPTURE ]
             (Motor Sürücü, LED, Sinyal)           (Frekans, Darbe Ölçümü)
                        |
                        v
             +-----------------------+
             | DEAD-TIME GENERATOR   | <--- TIM1 / TIM8 Gelişmiş Timer
             | ve BREAK (BKIN) GİRİŞİ|      (Aşırı Akım Emniyet Kalkanı)
             +-----------------------+
                        |
                        +---> CH1 / CH1N (Tamamlayıcı H-Köprüsü Çıkışları)
```

## 2. Frekans Hesaplama Matematiği: Prescaler (PSC), Auto-Reload (ARR) ve CNT

Bir STM32 timer'ını yapılandırırken mühendisin elindeki matematiksel araçlar şunlardır:

### 1. Sayaç Saati Frekansı ($f_{CNT}$):
Timer'a APB bus üzerinden gelen ana saat frekansı $f_{TIMCLK}$ (örneğin $84\ \text{MHz}$), $16\ \text{bit}$'lik Prescaler yazmacı ile bölünür:
$$f_{CNT} = \frac{f_{TIMCLK}}{\text{PSC} + 1}$$
*Not: STM32 donanımında yazmaç değerine $1$ eklenir. `PSC = 0` girilirse saat bölünmez ($/1$); `PSC = 83` girilirse $84\ \text{MHz} / 84 = 1\ \text{MHz}$ ($1\ \mu\text{s}$ sayma periyodu) elde edilir.*

### 2. Zaman Aşımı / Taşma Frekansı ($f_{UEV}$ - Update Event):
Sayaç (`CNT`), $0$'dan başlayarak `ARR` (Auto-Reload Register) değerine kadar sayar. `CNT == ARR` olduğunda bir **Update Event (UEV)** tetiklenir, `CNT` sıfırlanır ve isteğe bağlı olarak donanımsal kesme (Interrupt) veya DMA talebi üretilir:
$$f_{UEV} = \frac{f_{TIMCLK}}{(\text{PSC} + 1) \times (\text{ARR} + 1)}$$
Periyot süresi ($T_{period}$):
$$T_{period} = \frac{1}{f_{UEV}} = \frac{(\text{PSC} + 1) \times (\text{ARR} + 1)}{f_{TIMCLK}}$$

### 3. PWM Görev Oranı (Duty Cycle) Formülü:
PWM modunda sinyalin yüksekte kalma süresi `CCR` (Capture/Compare Register) tarafından belirlenir:
$$\text{Duty Cycle (\%)} = \frac{\text{CCR}}{\text{ARR} + 1} \times 100$$
- `CCR = 0` $\implies$ Sürekli Lojik 0 (\%0 PWM)
- `CCR = (ARR + 1) / 2` $\implies$ Tam Kare Dalga (\%50 PWM)
- `CCR = ARR + 1` $\implies$ Sürekli Lojik 1 (\%100 PWM)

## 3. Output Compare, PWM Üretimi (Edge vs Center-Aligned) ve Dead-Time

### 1. Kenara Dayalı (Edge-Aligned) vs Merkeze Dayalı (Center-Aligned) PWM:
- **Edge-Aligned PWM:** Sayaç sadece yukarı doğru sayar ($0 \to \text{ARR}$). Her periyot başında sinyal $1$ olur, `CNT == CCR` olduğunda $0$'a düşer. Testere dişi dalga formudur.
  - Dezavantajı: Yüksek frekanslı harmonikler ve elektromanyetik ışıma (EMI) üretir.
- **Center-Aligned PWM:** Sayaç önce yukarı, sonra aşağı sayar ($0 \to \text{ARR} \to 0$). Simetrik üçgen dalga oluşturur.
  - **Savunma Standardı:** FOC (Field Oriented Control) motor sürücülerinde akım dalgalanmasını ve motor akustik gürültüsünü minimuma indirmek için **merkeze dayalı PWM zorunludur**.

### 2. Dead-Time (Ölü Zaman) Fiziği ve Shoot-Through Felaketi:
Güç elektroniğinde bir H-Köprüsünün veya 3-fazlı motor inverterinin bir kolunda iki transistör (üst MOSFET/IGBT ve alt MOSFET/IGBT) bulunur.
- Transistörlerin açılma süresi ($t_{on}$) ile kapanma süresi ($t_{off}$) eşit değildir. Kapanma süresi parazitik kapasitanslar nedeniyle her zaman daha uzundur!
- Eğer üst transistörü açma komutu ile alt transistörü kapama komutu aynı anda verilirse, kısa bir an ($200 - 500\ \text{ns}$) **İKİ TRANSİSTÖR BİRDEN İLETİMDE KALIR**.
- Besleme hattından ($48\ \text{V} - 600\ \text{V}$) doğrudan şasiye ($\text{GND}$) yüzlerce amperlik kısa devre akımı akar (**Shoot-Through / Cross-Conduction**). Transistörler milisaniyeler içinde patlar!
- **STM32 Çözümü:** `TIM1` ve `TIM8` içindeki donanımsal **Dead-Time Generator**, tamamlayıcı çıkışlar arasına ayarlanabilir ölü zaman ekleyerek bir transistör tamamen kapanmadan diğerinin açılmasını imkansız kılar.

## 4. Input Capture, Encoder Modu ve Donanımsal Break (BKIN) Emniyeti

### 1. Input Capture (Giriş Yakalama):
Dış dünyadan gelen bir kare dalganın (örneğin radar darbesi, ultrasonik yankı veya devir sensörü) frekansını ve darbe genişliğini sıfır CPU yüküyle ölçer:
- Pinde yükselen kenar görüldüğünde donanım o anki `CNT` değerini anında `CCR1` yazmacına kopyalar.
- Düşen kenar görüldüğünde `CNT` değeri `CCR2` yazmacına kopyalanır.
- Darbe Genişliği: $\Delta t = (\text{CCR2} - \text{CCR1}) \times T_{CNT}$. Yazılım hiçbir kesme kaçırmadan tek formülle süreyi bulur.

### 2. Donanımsal Quadrature Encoder Modu:
Optik veya manyetik döner enkoderler $90^\circ$ faz farkı olan iki sinyal (Kanal A ve Kanal B) üretir.
- STM32 General Purpose timer'ları bu iki kanalı doğrudan donanımsal olarak sayar.
- A fazı B'den öndeyse `CNT` yukarı sayar; gerideyse aşağı sayar.
- Çift kenar tetikleme ile çözünürlük $4$ katına çıkar ($4\times$ Decoding). CPU tek bir satır kod koşturmadan sadece `TIMx->CNT` değerini okuyarak füze kanatçığının açısını öğrenir!

### 3. Donanımsal Break Girişi (BKIN / Break Input):
Askeri motor kontrol sistemlerinde yazılım çökse, CPU HardFault'a düşse veya saat hatası olsa dahi donanım kendini korumalıdır:
- `BKIN` pini harici bir aşırı akım komparatörüne bağlanır.
- Motor aşırı akım çektiği anda `BKIN` pini Lojik-0/1 olur.
- Timer donanımı **CPU'YA HİÇBİR ŞEY SORMADAN, YAZILIMSIZ OLARAK NANOSANİYELER İÇİNDE** tüm PWM çıkışlarını anında keser (Hi-Z veya pasif durum). Füze motoru ve sürücü donanımı yanmaktan kurtulur!

```python
# -*- coding: utf-8 -*-
"""
GÜN 165: Kod Bloğu 1 — STM32 Donanımsal Zamanlayıcı (Timer) Çekirdek Simülatörü
(PSC, ARR, CNT, CCR, UEV, Edge/Center-Aligned PWM)
"""

from typing import Dict, Any, Tuple, List

class Stm32HardwareTimer:
    """
    STM32F4/H7 Timer Silikon Modeli (TIM1 / TIM2):
    - PSC : 16-bit Prescaler (0..65535)
    - ARR : Auto-Reload Register (16 veya 32 bit)
    - CNT : Anlık Sayaç Değeri
    - CCR : 4 Bağımsız Capture/Compare Kanalı
    - Mod : UP_COUNTER, DOWN_COUNTER, CENTER_ALIGNED
    """
    MODE_UP             = 0
    MODE_DOWN           = 1
    MODE_CENTER_ALIGNED = 2

    def __init__(self, name: str = "TIM1", clock_hz: int = 84_000_000):
        self.name = name
        self.input_clock_hz = clock_hz

        # Donanım Yazmaçları
        self.psc: int = 0
        self.arr: int = 65535
        self.cnt: int = 0
        self.ccr: List[int] = [0, 0, 0, 0] # 4 Kanal (CCR1..CCR4)
        
        self.counting_mode = self.MODE_UP
        self.counting_direction = 1 # 1: Yukarı, -1: Aşağı (Center-aligned için)

        # Olay Sayaçları
        self.update_events_count = 0
        self.prescaler_counter = 0

    def configure_timebase(self, psc: int, arr: int, mode: int = MODE_UP):
        self.psc = psc & 0xFFFF
        self.arr = arr & 0xFFFFFFFF
        self.counting_mode = mode
        self.cnt = 0
        self.prescaler_counter = 0

    def get_timer_frequencies(self) -> Tuple[float, float]:
        """(Sayaç Frekansı Hz, Update/Taşma Frekansı Hz)"""
        f_cnt = self.input_clock_hz / (self.psc + 1)
        if self.counting_mode == self.MODE_CENTER_ALIGNED:
            # Merkeze dayalı modda periyot iki katına çıkar (0 -> ARR -> 0)
            f_uev = f_cnt / (2 * self.arr)
        else:
            f_uev = f_cnt / (self.arr + 1)
        return f_cnt, f_uev

    def step_clock_tick(self) -> Tuple[bool, List[int]]:
        """
        Giriş saatinden 1 darbe geldiğinde çalışan donanım adımı.
        Dönüş: (Update_Event_Oldu_mu, [PWM1, PWM2, PWM3, PWM4])
        """
        uev_triggered = False

        # 1. Prescaler Sayımı
        self.prescaler_counter += 1
        if self.prescaler_counter <= self.psc:
            return False, self._compute_pwm_outputs()

        self.prescaler_counter = 0

        # 2. CNT Sayacı Güncellemesi
        if self.counting_mode == self.MODE_UP:
            self.cnt += 1
            if self.cnt > self.arr:
                self.cnt = 0
                self.update_events_count += 1
                uev_triggered = True
        elif self.counting_mode == self.MODE_DOWN:
            self.cnt -= 1
            if self.cnt < 0:
                self.cnt = self.arr
                self.update_events_count += 1
                uev_triggered = True
        elif self.counting_mode == self.MODE_CENTER_ALIGNED:
            self.cnt += self.counting_direction
            if self.cnt >= self.arr:
                self.counting_direction = -1
                self.update_events_count += 1
                uev_triggered = True
            elif self.cnt <= 0:
                self.counting_direction = 1
                self.update_events_count += 1
                uev_triggered = True

        return uev_triggered, self._compute_pwm_outputs()

    def _compute_pwm_outputs(self) -> List[int]:
        """Output Compare PWM Çıkışları: CNT < CCR ise 1, aksi halde 0"""
        outputs = []
        for ch in range(4):
            outputs.append(1 if self.cnt < self.ccr[ch] else 0)
        return outputs

# Deney: 84 MHz Giriş Saati ile 20 kHz Motor PWM Sinyali Üretimi
timer = Stm32HardwareTimer("TIM1", clock_hz=84_000_000)

# Hedef: 20 kHz PWM (ARR = 4199, PSC = 0)
# f_uev = 84,000,000 / ((0 + 1) * (4199 + 1)) = 84,000,000 / 4200 = 20,000 Hz (20 kHz)!
timer.configure_timebase(psc=0, arr=4199, mode=Stm32HardwareTimer.MODE_UP)
timer.ccr[0] = 2100 # Kanal 1: %50 Duty Cycle (2100 / 4200)
timer.ccr[1] = 1050 # Kanal 2: %25 Duty Cycle (1050 / 4200)

f_cnt, f_uev = timer.get_timer_frequencies()

print("[*] STM32 Zamanlayıcı Donanım Simülatörü Başlatıldı:")
print(f"  [+] Giriş Saati          : {timer.input_clock_hz / 1e6:.1f} MHz")
print(f"  [+] Prescaler (PSC)     : {timer.psc}")
print(f"  [+] Auto-Reload (ARR)   : {timer.arr}")
print(f"  [+] Sayaç Hızı (f_CNT)  : {f_cnt / 1e6:.2f} MHz")
print(f"  [+] PWM Frekansı (f_UEV): {f_uev:.1f} Hz ({f_uev / 1e3:.2f} kHz)")

assert f_cnt == 84_000_000.0
assert f_uev == 20_000.0

# 1 Tam PWM Periyodu Koşturuluyor (4200 saat çevrimi)
duty1_high_cycles = 0
for _ in range(4200):
    _, pwms = timer.step_clock_tick()
    if pwms[0] == 1:
        duty1_high_cycles += 1

measured_duty = (duty1_high_cycles / 4200.0) * 100.0
print(f"  [+] Ölçülen Kanal 1 Duty: %{measured_duty:.1f} (Beklenen: %50.0)")
assert abs(measured_duty - 50.0) < 0.1
print("[HÜCRE 6] STM32 zaman tabanı ve PWM donanım simülatörü başarıyla doğrulandı.")
```

## 5. Kod Açıklaması: Zaman Tabanı Üretimi ve PWM Fiziği

Yukarıdaki simülatör $84\ \text{MHz}$ giriş saatinden tam $20\ \text{kHz}$ motor kontrol PWM sinyali üretmiştir:
1. `configure_timebase(psc=0, arr=4199)` formülü uygulanarak $f_{UEV} = \frac{84\ \text{MHz}}{(0+1) \times (4199+1)} = 20\ \text{kHz}$ elde edilmiştir.
2. `CCR1 = 2100` atanarak $4200$ adımlık periyodun tam yarısında ($2100$ adım) sinyal Lojik-1, kalan yarısında Lojik-0 üretilmiş ve kusursuz bir \%50 görev oranı (Duty Cycle) doğrulanmıştır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 165: Kod Bloğu 2 — Donanımsal Input Capture ile Frekans ve Darbe Genişliği Ölçümü
"""

class InputCaptureModule:
    """
    STM32 Giriş Yakalama (Input Capture) Mantığı:
    - Kanal 1 (Yükselen Kenar): CNT değerini CCR1'e kilitler (Periyot Başlangıcı).
    - Kanal 2 (Düşen Kenar)   : CNT değerini CCR2'ye kilitler (Darbe Sonu).
    """
    def __init__(self, timer_clock_hz: int = 84_000_000):
        self.timer_clock_hz = timer_clock_hz
        self.ccr1_rising = 0
        self.ccr2_falling = 0
        self.measured_period_ticks = 0
        self.measured_high_ticks = 0

    def capture_edge(self, edge_type: str, current_cnt: int):
        if edge_type == "RISING":
            # İki yükselen kenar arasındaki fark periyottur
            if current_cnt >= self.ccr1_rising:
                self.measured_period_ticks = current_cnt - self.ccr1_rising
            else: # Sayaç taşması durumu (Wrap-around)
                self.measured_period_ticks = (65536 - self.ccr1_rising) + current_cnt
            self.ccr1_rising = current_cnt
        elif edge_type == "FALLING":
            self.ccr2_falling = current_cnt
            if self.ccr2_falling >= self.ccr1_rising:
                self.measured_high_ticks = self.ccr2_falling - self.ccr1_rising
            else:
                self.measured_high_ticks = (65536 - self.ccr1_rising) + self.ccr2_falling

    def get_signal_parameters(self) -> Tuple[float, float]:
        """(Frekans Hz, Duty Cycle %)"""
        if self.measured_period_ticks == 0:
            return 0.0, 0.0
        freq = self.timer_clock_hz / self.measured_period_ticks
        duty = (self.measured_high_ticks / self.measured_period_ticks) * 100.0
        return freq, duty

# Radar Telemetri Darbesi Simülasyonu:
# Gönderilen Sinyal: Frekans = 10 kHz (Periyot = 8400 tick @ 84MHz), Duty = %30 (High = 2520 tick)
ic = InputCaptureModule(timer_clock_hz=84_000_000)

# 1. Periyot Başı (t = 1000 tick, Yükselen Kenar)
ic.capture_edge("RISING", current_cnt=1000)

# 2. Darbe Sonu (t = 1000 + 2520 = 3520 tick, Düşen Kenar)
ic.capture_edge("FALLING", current_cnt=3520)

# 3. İkinci Periyot Başı (t = 1000 + 8400 = 9400 tick, Yükselen Kenar)
ic.capture_edge("RISING", current_cnt=9400)

calc_freq, calc_duty = ic.get_signal_parameters()

print()
print("[*] Donanımsal Input Capture Ölçüm Sonuçları:")
print(f"  [+] Ölçülen Periyot Tick : {ic.measured_period_ticks} (Beklenen: 8400)")
print(f"  [+] Ölçülen High Tick    : {ic.measured_high_ticks} (Beklenen: 2520)")
print(f"  [+] Hesaplanan Frekans   : {calc_freq / 1e3:.2f} kHz (Beklenen: 10.00 kHz)")
print(f"  [+] Hesaplanan Duty      : %{calc_duty:.1f} (Beklenen: %30.0)")

assert ic.measured_period_ticks == 8400
assert ic.measured_high_ticks == 2520
assert abs(calc_freq - 10_000.0) < 1.0
assert abs(calc_duty - 30.0) < 0.1
print("[HÜCRE 8] Donanımsal Input Capture frekans ve darbe ölçümü başarıyla doğrulandı.")
```

## 6. Kod Açıklaması: Donanımsal Input Capture ve Çift Kanal Ölçüm

Yukarıdaki kod bloğu STM32'nin **PWM Input Mode** donanım yeteneğini modeller:
1. Gelen sinyal Timer'ın iki kanalına birden bağlanır (Kanal 1 yükselen kenara, Kanal 2 düşen kenara).
2. Yükselen kenarda `CCR1` yakalanır, düşen kenarda `CCR2` yakalanır.
3. CPU hiçbir karmaşık zamanlama döngüsü veya harici interrupt çalıştırmadan; doğrudan $\text{Frekans} = \frac{f_{TIMCLK}}{\Delta \text{CCR1}}$ ve $\text{Duty} = \frac{\Delta \text{CCR2}}{\Delta \text{CCR1}}$ oranını nanosaniyeler içinde hesaplar.

```python
# -*- coding: utf-8 -*-
"""
GÜN 165: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Dead-Time Eksikliği ve Shoot-Through
"""

class InverterBridgeSafetyMonitor:
    """
    H-Köprüsü Güç Katı Simülasyonu:
    - High-Side Transistör (CH1)
    - Low-Side Transistör (CH1N)
    - Dead-Time süresi (ns)
    """
    def __init__(self, dead_time_ns: float = 0.0):
        self.dead_time_ns = dead_time_ns
        self.mosfet_turn_off_delay_ns = 250.0 # Transistörün kapanma ataleti (250 ns)
        self.shoot_through_detected = False

    def simulate_switching(self, high_side_command: int, low_side_command: int) -> str:
        # Her iki sürücüye de aynı anda 1 komutu gelirse doğrudan kaza!
        if high_side_command == 1 and low_side_command == 1:
            self.shoot_through_detected = True
            raise RuntimeError("CATASTROPHIC FAILURE: Donanımsal Kısa Devre! Üst ve alt MOSFET aynı anda açıldı!")

        # Kapanma gecikmesi simülasyonu: Eğer dead-time transistörün kapanma süresinden kısaysa
        if self.dead_time_ns < self.mosfet_turn_off_delay_ns:
            self.shoot_through_detected = True
            raise RuntimeError(f"POWER STAGE DESTROYED: Shoot-Through! Dead-Time ({self.dead_time_ns} ns) < Kapanma Süresi ({self.mosfet_turn_off_delay_ns} ns)!")

        return "SAFE_SWITCHING"

print()
print("[*] SABOTAJ SENARYOSU 1: Dead-Time Tanımlanmadan Tamamlayıcı Çıkış Sürülmesi")
unsafe_bridge = InverterBridgeSafetyMonitor(dead_time_ns=0.0) # Sıfır Dead-Time!

shoot_through_caught = False
try:
    # Üst transistör kapanıp alt transistör açılıyor (Geçiş anı):
    unsafe_bridge.simulate_switching(high_side_command=0, low_side_command=1)
except RuntimeError as e:
    shoot_through_caught = True
    print(f"  [+] Savunma Başarılı: Beklenen Donanım Arızası Yakalandı! ({e})")

assert shoot_through_caught == True, "Dead-time olmadan güç katı patlamalıdır!"

print()
print("[*] DÜZELTME: STM32 TIM1 Donanımsal Dead-Time Generator Devreye Alınıyor")
# 500 ns Dead-time ekleniyor (250 ns kapanma gecikmesinden büyük):
safe_bridge = InverterBridgeSafetyMonitor(dead_time_ns=500.0)
status = safe_bridge.simulate_switching(high_side_command=0, low_side_command=1)
print(f"  [+] Donanımsal Dead-Time Devrede: {status} (Transistörler güvende).")

assert status == "SAFE_SWITCHING"
assert safe_bridge.shoot_through_detected == False
print("[HÜCRE 10] Dead-time emniyet ve sabotaj testleri başarıyla doğrulandı.")
```

## 7. Kod Açıklaması: Sabotaj Analizi ve Donanımsal Koruma

Yukarıdaki sabotaj deneyinde motor sürücülerinin en büyük kabusu modellenmiştir:
1. Transistörler ideal anahtarlar değildir; iletimden kesime geçerken fiziksel yük boşalması nedeniyle $250\ \text{ns}$ gecikme yaşarlar.
2. Eğer Timer donanımında `DTG` (Dead-Time Generator) yazmacı sıfır bırakılırsa, geçiş anında her iki transistör $250\ \text{ns}$ boyunca aynı anda iletimde kalır.
3. Simülatörümüz $500\ \text{ns}$ donanımsal Dead-Time ekleyerek üst transistör tamamen kapanmadan alt transistörün açılmasını engellemiş ve güç katını kurtarmıştır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 165: Kod Bloğu 4 — Donanımsal Quadrature Encoder Arayüzü (Motor Pozisyon / Hız Takibi)
"""

class QuadratureEncoderHardwareInterface:
    """
    STM32 Timer Donanımsal Encoder Modu (TIM2 / TIM3):
    - TI1 (Kanal A) ve TI2 (Kanal B) girişlerini dinler.
    - 4x Encoding Modu: Her iki kanalın hem yükselen hem düşen kenarında sayar.
    """
    def __init__(self, ppr: int = 1024):
        self.ppr = ppr                      # Pulses Per Revolution (Tur Başına Darbe)
        self.cpr = ppr * 4                  # 4x Çözünürlük: Counts Per Revolution (4096)
        self.cnt: int = 0
        self.last_a: int = 0
        self.last_b: int = 0

    def update_encoder_pins(self, a: int, b: int):
        """Donanımsal Durum Geçiş Tablosu (Quadrature Decoding Table)"""
        if a != self.last_a or b != self.last_b:
            # Dönüş Yönü Belirleme:
            # İleri dönüş (Saat yönü - CW): (A ^ last_B) == 1
            # Geri dönüş (Saat yönünün tersi - CCW): (B ^ last_A) == 1
            if (a ^ self.last_b):
                self.cnt = (self.cnt + 1) % self.cpr
            else:
                self.cnt = (self.cnt - 1 + self.cpr) % self.cpr

            self.last_a = a
            self.last_b = b

    def get_mechanical_angle_degrees(self) -> float:
        """Mekanik Şaft Açısı: 0.0 - 360.0 Derece"""
        return (self.cnt / float(self.cpr)) * 360.0

# Simülasyon: Motor İleri Yönde 1/4 Tur (90 Derece) Dönüyor
encoder = QuadratureEncoderHardwareInterface(ppr=1024) # 4096 CPR

# Saat yönünde (CW) standart Gray-Code döngüsü: (0,0) -> (1,0) -> (1,1) -> (0,1) -> (0,0)
cw_steps = [(1, 0), (1, 1), (0, 1), (0, 0)]

# 90 derece için 1024 count gerekir (1024 / 4 = 256 tam Gray cycle)
for _ in range(256):
    for a, b in cw_steps:
        encoder.update_encoder_pins(a, b)

angle = encoder.get_mechanical_angle_degrees()

print()
print("[*] Donanımsal Quadrature Encoder Simülasyonu:")
print(f"  [+] Toplam Sayılan Darbe (CNT) : {encoder.cnt} / {encoder.cpr}")
print(f"  [+] Hesaplanan Mekanik Açı    : {angle:.2f}° (Beklenen: 90.00°)")

assert encoder.cnt == 1024
assert abs(angle - 90.0) < 0.01
print("[HÜCRE 12] Quadrature encoder donanım arayüzü başarıyla doğrulandı.")
```

## 8. Kod Açıklaması: Donanımsal 4x Enkoder Sayacı

Yukarıdaki simülasyonda STM32'nin **Encoder Interface Mode** yeteneği modellenmiştir:
1. $1024\ \text{PPR}$ optik enkoder $4\times$ sayma moduna alınarak çözünürlük $4096\ \text{CPR}$'a çıkarılmıştır.
2. 256 Gray kodu döngüsü ($1024$ kenar) sonucunda `CNT` tam $1024$'e ulaşmış ve mekanik açı tam $90.00^\circ$ olarak sıfır CPU müdahalesiyle hesaplanmıştır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 165: Kod Bloğu 5 — ASELSAN HİSAR Hava Savunma Füzesi Kanatçık BLDC Motoru ve BKIN Emniyeti
"""

class HisarMissileActuatorController:
    """
    ASELSAN HİSAR Füzesi Kanatçık Eyleyici (Fin Actuator) Kontrol Ünitesi:
    - TIM1 Advanced Timer: 3-Fazlı Tamamlayıcı PWM (CH1/CH1N, CH2/CH2N, CH3/CH3N)
    - Dead-Time: 500 ns
    - BKIN (Break Input): Donanımsal Aşırı Akım / Kanatçık Sıkışma Kilidi
    """
    def __init__(self):
        self.timer = Stm32HardwareTimer("TIM1", clock_hz=168_000_000) # STM32F405 168 MHz
        # 20 kHz Center-Aligned PWM (ARR = 4200, PSC = 0)
        self.timer.configure_timebase(psc=0, arr=4200, mode=Stm32HardwareTimer.MODE_CENTER_ALIGNED)
        
        # 3 Faz PWM Görev Oranları (Sinüs FOC Başlangıcı)
        self.timer.ccr[0] = 2100 # Faz U: %50
        self.timer.ccr[1] = 1050 # Faz V: %25
        self.timer.ccr[2] = 3150 # Faz W: %75

        self.bkin_tripped = False
        self.pwm_outputs_enabled = True

    def trigger_hardware_break_fault(self, fault_reason: str):
        """Donanımsal BKIN Pini Tetiklendiğinde (Nanosaniyelik Kapanma)"""
        # CPU'DAN VE YAZILIMDAN BAĞIMSIZ DOĞRUDAN SİLİKON SEVİYESİNDE KİLİTLEME:
        self.pwm_outputs_enabled = False
        self.bkin_tripped = True
        # Donanım tüm CCR çıkışlarını derhal 0 yapar (Hi-Z Modu)
        self.timer.ccr = [0, 0, 0, 0]
        print(f"  [BKIN ACİL DURUM] Donanımsal Break Girişi Tetiklendi! Sebep: {fault_reason}")
        print("  [GÜVENLİK] Tüm 3-Faz PWM Çıkışları 10 ns İçinde Donanımsal Olarak KESİLDİ!")

# Uçuş Simülasyonu: Kanatçık Hedef Yönlenmesinde Aşırı Tork / Akım Algılandı
hisar_actuator = HisarMissileActuatorController()

print()
print("[*] ASELSAN HİSAR Kanatçık Sürücü Testi Başlatıldı:")
print(f"  [+] PWM Sürücü Durumu: {'AKTİF' if hisar_actuator.pwm_outputs_enabled else 'KAPALI'}")
assert hisar_actuator.pwm_outputs_enabled == True

# Kanatçık mekanik bir engele çarptı ve şönt dirençte aşırı akım gerilimi 3.3V'u aştı:
hisar_actuator.trigger_hardware_break_fault("AŞIRI AKIM (KANATÇIK MEKANİK SIKIŞMASI - I_peak > 45A)")

print(f"  [+] BKIN Sonrası PWM Durumu: {'AKTİF' if hisar_actuator.pwm_outputs_enabled else 'KAPALI (GÜVENLİ Hi-Z)'}")
assert hisar_actuator.bkin_tripped == True
assert hisar_actuator.pwm_outputs_enabled == False
assert all(ccr == 0 for ccr in hisar_actuator.timer.ccr)
print("[HÜCRE 14] Taktik BKIN donanımsal acil durdurma senaryosu başarıyla tamamlandı.")
```

## 9. Kod Açıklaması: Taktik 3-Fazlı PWM ve Acil Durdurma

Yukarıdaki taktik savunma uygulamasında ASELSAN HİSAR füzesinin kanatçık motor kontrol mimarisi test edilmiştir:
1. `TIM1` Advanced Timer, $168\ \text{MHz}$ çekirdek saati ile $20\ \text{kHz}$ merkeze dayalı (Center-Aligned) 3-fazlı sinüzoidal PWM üretmiştir.
2. Kanatçık mekanik sıkışması durumunda harici analog komparatör `BKIN` pinini düşürmüş ve donanım yazılımsız olarak PWM çıkışlarını derhal sıfırlayarak motor sürücüsünün yanmasını önlemiştir.

```python
# -*- coding: utf-8 -*-
"""
GÜN 165: Kod Bloğu 6 — 4 Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_165_timer_ve_counter.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_165\gun_165_timer_ve_counter.png"

# Matplotlib Karanlık Tema Ayarları
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.0

fig = plt.figure(figsize=(18, 12), dpi=300, facecolor='#0F172A')
fig.suptitle("GÜN 165: STM32 Donanımsal Zamanlayıcılar, PWM, Dead-Time ve BKIN Mimarisi Panosu",
             fontsize=14, fontweight='bold', color='#38BDF8', y=0.98)

# -----------------------------------------------------------------------------
# PANEL 1: Edge-Aligned vs Center-Aligned PWM Sayaç Dalga Formu
# -----------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1)
ax1.set_facecolor('#1E293B')
ax1.set_title("Panel 1: Edge-Aligned (Testere) vs Center-Aligned (Üçgen) PWM", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

t_edge = np.linspace(0, 4, 400)
# Edge-aligned: 0 -> ARR (Testere)
sawtooth_cnt = (t_edge % 1.0) * 100
ccr_val = 60

ax1.plot(t_edge, sawtooth_cnt, color='#38BDF8', lw=1.8, label="Edge-Aligned CNT (0 -> ARR)")
ax1.axhline(ccr_val, color='#F59E0B', linestyle='--', lw=1.5, label=f"CCR Eşiği ({ccr_val})")

# PWM Çıkışı
pwm_edge = [15 if c < ccr_val else -15 for c in sawtooth_cnt]
ax1.plot(t_edge, pwm_edge, color='#10B981', lw=2.0, label="Çıkış PWM (Edge: %60 Duty)")

ax1.set_xlabel("Zaman (Periyot)", color='#94A3B8')
ax1.set_ylabel("Sayaç Değeri (CNT)", color='#94A3B8')
ax1.set_ylim(-25, 115)
ax1.grid(True, color='#334155', alpha=0.5, linestyle='--')
ax1.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# -----------------------------------------------------------------------------
# PANEL 2: Dead-Time Fiziği ve H-Köprüsü Shoot-Through Koruması
# -----------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2)
ax2.set_facecolor('#1E293B')
ax2.set_title("Panel 2: Tamamlayıcı PWM ve Donanımsal Dead-Time (Ölü Zaman)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

time_ns = np.linspace(0, 1000, 500)
# Üst Transistör (CH1)
high_side = [1.0 if (t < 400 or t > 900) else 0.0 for t in time_ns]
# Alt Transistör (CH1N) - 500ns Dead-Time ile ötelenmiş
low_side  = [1.0 if (480 < t < 820) else 0.0 for t in time_ns]

ax2.step(time_ns, [v + 1.4 for v in high_side], color='#38BDF8', lw=2.2, where='post', label="Üst Transistör (CH1 High-Side)")
ax2.step(time_ns, low_side, color='#A78BFA', lw=2.2, where='post', label="Alt Transistör (CH1N Low-Side)")

# Dead-Time Bölgeleri
ax2.axvspan(400, 480, color='#F43F5E', alpha=0.25, label="Dead-Time 1 (80 ns)")
ax2.axvspan(820, 900, color='#F43F5E', alpha=0.25, label="Dead-Time 2 (80 ns)")

ax2.text(440, 1.2, "Dead-Time\n(İkisi de KAPALI)", ha='center', color='#FCA5A5', fontsize=7.5, fontweight='bold')
ax2.text(860, 1.2, "Dead-Time\n(İkisi de KAPALI)", ha='center', color='#FCA5A5', fontsize=7.5, fontweight='bold')

ax2.set_xlabel("Zaman (ns)", color='#94A3B8')
ax2.set_ylabel("Lojik Sürücü Sinyali", color='#94A3B8')
ax2.set_yticks([0, 1, 1.4, 2.4])
ax2.set_yticklabels(["0", "1 (CH1N)", "0", "1 (CH1)"])
ax2.set_ylim(-0.2, 2.8)
ax2.grid(True, color='#334155', alpha=0.5, linestyle='--')
ax2.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# -----------------------------------------------------------------------------
# PANEL 3: Donanımsal Quadrature Encoder 4x Decoding Sinyalleri
# -----------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3)
ax3.set_facecolor('#1E293B')
ax3.set_title("Panel 3: Donanımsal Quadrature Encoder (4x Decoding Gray Code)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

enc_t = np.linspace(0, 8, 800)
ch_a = np.sign(np.sin(2 * np.pi * 0.5 * enc_t))
ch_b = np.sign(np.cos(2 * np.pi * 0.5 * enc_t))

ch_a = np.where(ch_a > 0, 1.0, 0.0)
ch_b = np.where(ch_b > 0, 1.0, 0.0)

ax3.step(enc_t, [v + 1.4 for v in ch_a], color='#34D399', lw=2.0, where='post', label="Kanal A (TI1 Girişi)")
ax3.step(enc_t, ch_b, color='#FBBF24', lw=2.0, where='post', label="Kanal B (TI2 Girişi - 90° Faz Farkı)")

# Sayma Kenarları
for edge in np.arange(0.5, 8.0, 0.5):
    ax3.axvline(edge, color='#64748B', linestyle=':', alpha=0.6)

ax3.text(4.0, 2.7, "Her iki kanalın hem yükselen hem düşen kenarında sayım (4x Çözünürlük)",
         ha='center', color='#CBD5E1', fontsize=8, fontstyle='italic')

ax3.set_xlabel("Zaman / Açı", color='#94A3B8')
ax3.set_yticks([0, 1, 1.4, 2.4])
ax3.set_yticklabels(["0", "1 (CH B)", "0", "1 (CH A)"])
ax3.set_ylim(-0.2, 3.0)
ax3.grid(True, color='#334155', alpha=0.5, linestyle='--')
ax3.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# -----------------------------------------------------------------------------
# PANEL 4: BKIN (Break Input) Acil Durdurma Zaman Çizgisi
# -----------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4)
ax4.set_facecolor('#1E293B')
ax4.set_title("Panel 4: BKIN (Break Input) Donanımsal Acil Durdurma Zamanlaması", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

t_bkin = np.linspace(0, 10, 500)
# 0-5 ms normal PWM, 5 ms'de BKIN tetikleniyor ve çıkış anında sıfır!
pwm_actuator = [1.0 if (t < 5.0 and (t % 1.0 < 0.6)) else 0.0 for t in t_bkin]
bkin_signal  = [0.0 if t < 5.0 else 3.3 for t in t_bkin]

ax4.plot(t_bkin, [v * 3.3 for v in pwm_actuator], color='#38BDF8', lw=2.0, label="TIM1 PWM Çıkışları (Kanatçık Motor Sinyali)")
ax4.plot(t_bkin, bkin_signal, color='#EF4444', lw=2.2, linestyle='--', label="BKIN Pini (Aşırı Akım Alarmı)")

ax4.axvline(5.0, color='#F43F5E', linestyle='-', lw=1.8)
ax4.text(5.2, 2.2, "ARIZA TESPİT EDİLDİ!\nBKIN Donanımsal Kilitleme\n(10 ns gecikmeyle PWM=0)",
         color='#FCA5A5', fontsize=8, fontweight='bold')

ax4.set_xlabel("Zaman (ms)", color='#94A3B8')
ax4.set_ylabel("Gerilim (V)", color='#94A3B8')
ax4.set_ylim(-0.5, 4.2)
ax4.grid(True, color='#334155', alpha=0.5, linestyle='--')
ax4.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 165 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert f_cnt == 84_000_000.0
assert f_uev == 20_000.0
assert abs(measured_duty - 50.0) < 0.1
assert ic.measured_period_ticks == 8400
assert ic.measured_high_ticks == 2520
assert shoot_through_caught == True
assert status == "SAFE_SWITCHING"
assert encoder.cnt == 1024
assert hisar_actuator.bkin_tripped == True
assert hisar_actuator.pwm_outputs_enabled == False

print()
print("[PASS] Gün 165: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
```

## 10. Görselleştirme Açıklaması ve Mimari Yorumlar

Üretilen 4 panelli yüksek çözünürlüklü (300 DPI) mimari pano, STM32 Timer iç mekanizmalarını görselleştirir:
1. **Panel 1: Edge-Aligned vs Center-Aligned PWM:**
   Testere dişi sayım modu ve eşik karşılaştırmasıyla üretilen \%60 görev oranlı PWM darbesi resmedilmiştir.
2. **Panel 2: Tamamlayıcı PWM ve Donanımsal Dead-Time:**
   H-Köprüsü transistörlerinin kapanma ataletine karşı araya eklenen $80\ \text{ns}$'lik güvenlik ölü zamanı (Dead-Time) ve Shoot-Through koruması gösterilmiştir.
3. **Panel 3: Donanımsal Quadrature Encoder (4x Decoding):**
   Kanal A ve Kanal B sinyallerinin $90^\circ$ faz farkı ve $4\times$ çözünürlük artışı zaman çizgisinde haritalanmıştır.
4. **Panel 4: BKIN (Break Input) Donanımsal Acil Durdurma:**
   Aşırı akım anında CPU ve yazılımdan bağımsız olarak PWM darbelerinin $10\ \text{ns}$ içinde sıfıra kilitlenmesi kanıtlanmıştır.

## 11. Karşılaştırmalı Analiz: Basic vs General Purpose vs Advanced Timer

| Donanım Özelliği | Basic Timers (TIM6, TIM7) | General-Purpose (TIM2-TIM5) | Advanced-Control (TIM1, TIM8) |
| :--- | :--- | :--- | :--- |
| **Sayaç Çözünürlüğü** | 16-bit | 16-bit veya **32-bit (TIM2/5)** | 16-bit |
| **Sayma Yönü** | Sadece Yukarı (Up) | Yukarı, Aşağı, Merkeze Dayalı | Yukarı, Aşağı, Merkeze Dayalı |
| **Kanal Sayısı** | Sıfır (Dış Pin Yok) | 4 Bağımsız Kanal | 4 Kanal + **Tamamlayıcı Çıkışlar** |
| **PWM Üretimi** | Yok | Var (Edge / Center) | Var (Gelişmiş FOC Motor PWM) |
| **Dead-Time Generator** | Yok | Yok | **VAR (Programlanabilir ns Hassasiyeti)** |
| **Break (BKIN) Girişi** | Yok | Yok | **VAR (Donanımsal Acil Durdurma)** |
| **Kullanım Alanı** | DAC Tetikleme, RTOS Tick | Sensör Ölçümü, Enkoder, Servo | **BLDC/PMSM Motor Sürücü, SMPS** |

## 12. Donanım ve Çip Seviyesi Ayrıntılar (Shadow Registers, Preload ARR/CCR, UEV)

### 1. Preload ve Gölge Yazmaçlar (Shadow Registers):
Timer yazmaçları (`ARR` ve `CCR`) çift katmanlıdır:
- **Preload Register (Ön Yükleme Yazmacı):** Yazılımın doğrudan okuyup yazdığı yazmaçtır.
- **Shadow Register (Gölge Yazmaç):** Timer donanımının o an sayarken kullandığı fiziksel yazmaçtır.
- `ARPE` (Auto-Reload Preload Enable) biti açıkken yazılım `ARR = 1000` yazarsa, bu değer hemen gölge yazmaca aktarılmaz; mevcut periyodun bitmesi (**Update Event - UEV**) beklenir!
- Eğer `ARPE` kapalı olsaydı ve sayaç $800$'deyken yazılım `ARR = 500` yazsaydı, sayaç $800$'den $65535$'e kadar saymak zorunda kalır ve motor anlık hız patlaması yaşardı (**Glitch**).

### 2. Repetition Counter (RCR):
`TIM1` ve `TIM8`'de bulunan `RCR` yazmacı, kesmenin her periyotta değil, her $N+1$ periyotta bir üretilmesini sağlar. Özellikle $40\ \text{kHz}$ PWM çalışırken CPU'yu her periyotta kesmeyle boğmamak, akım okumasını her 2 periyotta bir ($20\ \text{kHz}$) yapmak için kullanılır.

## 13. Güvenlik, Hata Ayıklama ve Taktik İpuçları (Timer Clock APB Multiplier Tuzakları)

### 1. APB Timer Clock Multiplier Gizli Tuzağı:
STM32 saat ağacında (Clock Tree) en sık yapılan hesaplama hatası:
- Eğer APB1 prescaler'ı $/1$ ise, Timer saati APB1 saatiyle aynıdır ($42\ \text{MHz}$).
- Ancak eğer APB1 prescaler'ı $/2$, $/4$ veya $/8$ gibi $1$'den farklıysa, donanım Timer saatini otomatik olarak **$2$ İLE ÇARPAR**!
- Sonuç: APB1 bus'ı $42\ \text{MHz}$ iken `TIM2` saati $84\ \text{MHz}$ olur! Bu kuralı bilmeyen mühendisler PWM frekansını yarı yarıya hatalı hesaplarlar.

### 2. GDB Debug Sırasında Timer'ın Durdurulması (`DBGMCU_APB1_FZ`):
Kodda bir breakpoint koyup durduğunuzda CPU çekirdeği durur ancak donanımsal timer saymaya devam ederse:
- Breakpoint'ten devam ettiğiniz anda devasa bir zaman aşımı (timeout) hatası oluşur veya motor kontrol döngüsü patlar.
- **Çözüm:** `DBGMCU->APB1FZ |= DBGMCU_APB1_FZ_DBG_TIM2_STOP;` komutu ile işlemci debug modunda durdurulduğunda Timer sayaçlarının da dondurulması sağlanmalıdır.

## 14. Günün Mini Uygulaması: STM32 Donanımsal Zamanlayıcı ve Motor Sürücüsü

Günün mini uygulamasında:
1. $84\ \text{MHz}$ giriş saatinden $20\ \text{kHz}$ motor kontrol PWM sinyali üreten STM32 Timer zaman tabanı simülatörü kodlanmıştır.
2. Çift kanallı donanımsal **Input Capture** modülü ile harici darbenin frekansı ve görev oranı sıfır CPU yüküyle ölçülmüştür.
3. H-Köprüsü güç transistörlerinde **Shoot-Through** kısa devresi simüle edilmiş; $500\ \text{ns}$ donanımsal **Dead-Time** ile sistem emniyete alınmıştır.
4. $1024\ \text{PPR}$ ($4096\ \text{CPR}$) **Quadrature Encoder** arayüzü ile $90^\circ$ şaft açısı donanımsal olarak takip edilmiştir.
5. ASELSAN HİSAR füzesi kanatçık eyleyicisinde aşırı akım anında nanosaniyeler içinde tüm PWM çıkışlarını kapatan **BKIN (Break Input)** devresi doğrulanmıştır.

## 15. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **Preload (ARPE) Açmayı Unutmak:** Çalışma anında PWM frekansı veya periyodu değiştirilirken `ARPE` açılmadığı için sayaç taşması ve motor titremesi üretmek.
2. **Dead-Time Koymadan Tamamlayıcı Çıkışları Açmak:** Güç katında anlık kısa devre yaratarak MOSFET'leri yakmak.
3. **Timer Giriş Saatini Yanlış Varsaymak:** APB saat çarpanı kuralını unutup timer frekansını $2$ kat hatalı hesaplamak.
4. **Input Capture'da Sayaç Taşmasını (Overflow/Wrap-around) Dikkate Almamak:** Sayaç $65535$'ten $0$'a dönerken zaman farkını negatif hesaplayıp telemetriyi bozmak.

## 16. Mülakat ve Saha Deneyimi Soruları (ASELSAN / ROKETSAN / TUSAŞ)

### Soru 1: FOC (Field Oriented Control) motor sürücülerinde ve füze kanatçık eyleyicilerinde neden Edge-Aligned yerine Center-Aligned PWM tercih edilir?
**Cevap:** Edge-Aligned PWM modunda sayaç testere dişi ($0 \to \text{ARR}$) şeklinde sayar ve tüm fazların yükselen kenarları aynı anda tetiklenir. Bu durum DC bara üzerinde çok yüksek akım dalgalanmalarına ($di/dt$), parazitik rezonansa ve şiddetli elektromanyetik ışıma (EMI) gürültüsüne yol açar. Center-Aligned PWM modunda ise sayaç üçgen dalga ($0 \to \text{ARR} \to 0$) şeklinde yukarı ve aşağı sayar. PWM darbeleri periyodun merkezine göre simetrik olarak açılıp kapanır. Bu simetri motor faz akımlarındaki harmonik bozulmayı minimuma indirir, motor tork dalgalanmasını (torque ripple) ve akustik gürültüyü yok eder; ayrıca ADC akım örneklemesinin tam tepe veya dip noktasında gürültüsüzce yapılmasına olanak tanır.

### Soru 2: STM32 Timer donanımında 'Dead-Time' nedir ve yazılımsal gecikmeler yerine neden özel bir donanım bloğu tarafından üretilir?
**Cevap:** Dead-Time (Ölü Zaman), bir H-Köprüsünün aynı kolundaki üst ve alt güç transistörlerinin anahtarlama anlarında ikisinin de aynı anda iletimde kalmasını önlemek amacıyla araya eklenen nanosaniyelik (örn: $200 - 800\ \text{ns}$) güvenlik bekleme süresidir. Transistörlerin kapanma süreleri parazitik kapasitelerden dolayı açılma sürelerinden daha uzundur. Eğer üst transistör kapatılırken alt transistör anında açılırsa, besleme ile toprak arasında doğrudan kısa devre (**Shoot-Through**) oluşur ve güç katı patlar. Yazılımsal gecikmeler mikrodenetleyici kesmeleri veya işletim sistemi gecikmeleri nedeniyle değişkenlik gösterir ve deterministik değildir. Timer içindeki `Dead-Time Generator` donanımı ise doğrudan saat çevrimleriyle nanosaniye hassasiyetinde ve yüzde yüz güvenilirlikle bu gecikmeyi donanımsal lojik kapılarla sağlar.

### Soru 3: Advanced Control Timer (TIM1/TIM8) üzerindeki 'BKIN' (Break Input) pini sahada hangi kritik korumayı sağlar?
**Cevap:** BKIN pini, donanımsal bir acil durum frenleme mekanizmasıdır. Motor sürücüsündeki harici şönt direnç veya sıcaklık sensörüne bağlı bir analog komparatör ile sürülür. Motorda mekanik sıkışma, aşırı akım veya kısa devre tespit edildiğinde BKIN pini lojik seviye değiştirir. Bu sinyal ulaştığı anda Timer silikonu **CPU'dan bağımsız olarak, hiçbir yazılım veya kesme gecikmesi beklemeksizin nanosaniyeler içinde** tüm PWM çıkışlarını anında devre dışı bırakır (Hi-Z veya güvenli lojik seviye). İşlemci o sırada kilitlenmiş veya bir sonsuz döngüde olsa dahi donanım kendini kalıcı hasardan korur.

## 17. Gün Sonu Özeti ve 3-Cümle Çıkarımı

1. **Timer ve Counter Nedir?:** CPU'dan bağımsız çalışan, `PSC`, `ARR`, `CNT` ve `CCR` yazmaçları ile nanosaniyelik zaman tabanı, PWM ve sinyal yakalama üreten donanımsal motorlardır.
2. **Hangi Problemi Çözer?:** Yazılımsal döngülerin deterministik olmayan gecikmelerini ve CPU israfını sıfırlayarak motor kontrolü, enkoder takibi ve radar darbe ölçümlerini donanımsal hızda gerçekleştirir.
3. **Hangi Trade-off/Hata Sınıfını Getirir?:** H-Köprüsü sürücülerinde yetersiz Dead-Time seçimi ölümcül Shoot-Through patlamalarına, Preload (`ARPE`) kullanılmaması ise motorlarda anlık glitch sıçramalarına yol açar.

