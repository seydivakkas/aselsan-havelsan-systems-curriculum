# -*- coding: utf-8 -*-
"""
GÜN 165: STM32 Donanımsal Zamanlayıcılar (Timers) ve Sayaçlar (Counters), PWM, Dead-Time ve BKIN Mimarisi
Otomatik Oluşturulan Çalıştırılabilir Python Betiği
"""

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

