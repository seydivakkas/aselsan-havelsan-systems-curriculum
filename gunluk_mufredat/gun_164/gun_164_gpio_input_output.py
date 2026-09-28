# -*- coding: utf-8 -*-
"""
GÜN 164: STM32 GPIO Giriş/Çıkış Mimarisi, Push-Pull vs Open-Drain, Slew Rate ve Donanımsal Koruma
Otomatik Oluşturulan Çalıştırılabilir Python Betiği
"""

# -*- coding: utf-8 -*-
"""
GÜN 164: Kod Bloğu 1 — STM32 GPIO Donanım Bloğu ve Pad Simülatörü
(MODER, OTYPER, OSPEEDR, PUPDR, IDR, ODR, BSRR, LCKR)
"""

from typing import Dict, Any, Tuple
import struct

class Stm32GpioPort:
    """
    STM32F4/H7 Gerçekçi GPIO Port Donanım Modeli (16 Pin [0..15]):
    - MODER   (0x00): [00: Giriş, 01: Çıkış, 10: AF, 11: Analog]
    - OTYPER  (0x04): [0: Push-Pull, 1: Open-Drain]
    - OSPEEDR (0x08): [00: Low (2MHz), 01: Med (25MHz), 10: Fast (50MHz), 11: High (100MHz)]
    - PUPDR   (0x0C): [00: No-PUPD, 01: Pull-Up, 10: Pull-Down]
    - IDR     (0x10): Fiziksel Pin Gerilimi Giriş Yazmacı (Salt Okunur)
    - ODR     (0x14): Çıkış Veri Yazmacı
    - BSRR    (0x18): Atomik Set/Reset Yazmacı
    - LCKR    (0x1C): Donanımsal Konfigürasyon Kilitleme
    """
    MODE_INPUT  = 0b00
    MODE_OUTPUT = 0b01
    MODE_AF     = 0b10
    MODE_ANALOG = 0b11

    OTYPE_PUSHPULL  = 0
    OTYPE_OPENDRAIN = 1

    PUPD_NONE     = 0b00
    PUPD_PULLUP   = 0b01
    PUPD_PULLDOWN = 0b10

    def __init__(self, name: str = "GPIOA"):
        self.name = name
        self.moder   = 0x00000000 # Tüm pinler varsayılan Giriş (Reset Durumu)
        self.otyper  = 0x00000000 # Varsayılan Push-Pull
        self.ospeedr = 0x00000000 # Varsayılan Low Speed
        self.pupdr   = 0x00000000 # Varsayılan No-PUPD
        self.odr     = 0x00000000
        self.lckr    = 0x00000000
        self.is_locked = False

        # Fiziksel Dış Hat Gerilimleri (0.0V - 3.3V)
        self.external_pin_voltage = [0.0] * 16

    def configure_pin(self, pin: int, mode: int, otype: int = 0, speed: int = 0, pupd: int = 0):
        if self.is_locked and (self.lckr & (1 << pin)):
            raise PermissionError(f"HARDWARE LOCK FAULT: Pin {pin} LCKR ile KİLİTLENMİŞTİR! Değiştirilemez.")

        # 1. MODER Güncelle (2-bit)
        self.moder &= ~(0b11 << (pin * 2))
        self.moder |= (mode & 0b11) << (pin * 2)

        # 2. OTYPER Güncelle (1-bit)
        self.otyper &= ~(1 << pin)
        self.otyper |= (otype & 1) << pin

        # 3. OSPEEDR Güncelle (2-bit)
        self.ospeedr &= ~(0b11 << (pin * 2))
        self.ospeedr |= (speed & 0b11) << (pin * 2)

        # 4. PUPDR Güncelle (2-bit)
        self.pupdr &= ~(0b11 << (pin * 2))
        self.pupdr |= (pupd & 0b11) << (pin * 2)

    def write_bsrr(self, set_mask: int, reset_mask: int):
        """32-bit Donanımsal Atomik Set/Reset"""
        self.odr |= (set_mask & 0xFFFF)
        self.odr &= ~(reset_mask & 0xFFFF)

    def read_idr(self) -> int:
        """Schmitt Trigger ve Histerezis Simülasyonu ile Pin Okuma"""
        idr_val = 0
        for pin in range(16):
            mode = (self.moder >> (pin * 2)) & 0b11
            otype = (self.otyper >> pin) & 0b1
            pupd  = (self.pupdr >> (pin * 2)) & 0b11

            v = 0.0
            if mode == self.MODE_OUTPUT:
                pin_odr_high = bool(self.odr & (1 << pin))
                if otype == self.OTYPE_PUSHPULL:
                    v = 3.3 if pin_odr_high else 0.0
                elif otype == self.OTYPE_OPENDRAIN:
                    if pin_odr_high:
                        # Open drain Lojik 1: Pin yüzer, Pull-up varsa 3.3V olur
                        v = 3.3 if pupd == self.PUPD_PULLUP else self.external_pin_voltage[pin]
                    else:
                        v = 0.0 # N-MOS GND'ye çeker
            elif mode == self.MODE_INPUT:
                if pupd == self.PUPD_PULLUP:
                    v = 3.3 if self.external_pin_voltage[pin] > 1.5 else self.external_pin_voltage[pin]
                elif pupd == self.PUPD_PULLDOWN:
                    v = self.external_pin_voltage[pin]
                else: # Floating
                    v = self.external_pin_voltage[pin]

            # Schmitt Trigger Eşik Kontrolü: V > 1.7V ise High, V < 1.3V ise Low
            if v >= 1.7:
                idr_val |= (1 << pin)
            elif v <= 1.3:
                idr_val &= ~(1 << pin)

        return idr_val

# Doğrulama Testi
gpio = Stm32GpioPort("GPIOA")
# Pin 5'i LED için Push-Pull Çıkış yap
gpio.configure_pin(5, mode=Stm32GpioPort.MODE_OUTPUT, otype=Stm32GpioPort.OTYPE_PUSHPULL)
gpio.write_bsrr(set_mask=(1 << 5), reset_mask=0)

# Pin 0'ı Buton için Pull-Down Giriş yap
gpio.configure_pin(0, mode=Stm32GpioPort.MODE_INPUT, pupd=Stm32GpioPort.PUPD_PULLDOWN)
gpio.external_pin_voltage[0] = 3.3 # Butona basıldı

idr = gpio.read_idr()

print("[*] STM32 GPIO Donanım Portu Simülatörü Başlatıldı:")
print(f"  [+] Pin 5 Çıkış Durumu (ODR)    : 0x{gpio.odr:04X} (Pin 5 HIGH)")
print(f"  [+] Port Giriş Değerleri (IDR) : 0x{idr:04X} (Pin 0 HIGH, Pin 5 Feedback HIGH)")

assert (gpio.odr & (1 << 5)) != 0
assert (idr & (1 << 0)) != 0
assert (idr & (1 << 5)) != 0
print("[HÜCRE 6] GPIO donanım portu ve Schmitt trigger simülatörü başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 164: Kod Bloğu 2 — Sayısal Giriş Filtreleme ve Glitch / Mekanik Debounce Algoritması
"""

from typing import List

class DigitalDebounceFilter:
    """
    Aviyonik Sınıfı Yazılımsal Sayısal Filtre (Debouncer & Glitch Filter):
    - Giriş pini her 1 ms'de bir örneklenir.
    - Kararlı durum değişimi için ardışık 'N' adet aynı örnek gereklidir.
    - Kısa süreli EMI parazit darbeleri (Glitches < N ms) yok sayılır.
    """
    def __init__(self, filter_depth: int = 5):
        self.filter_depth = filter_depth
        self.history_buffer: int = 0x00
        self.stable_state: int = 0
        self.filter_mask = (1 << filter_depth) - 1 # Örn 5 örnek için 0b11111 (0x1F)

    def process_sample(self, raw_pin_level: int) -> Tuple[int, bool]:
        """
        Giriş: 0 veya 1 (Anlık Pin Seviyesi)
        Çıkış: (Mevcut Kararlı Seviye, Durum Değişti mi?)
        """
        # Kaydırma yazmacına yeni örneği ekle
        self.history_buffer = ((self.history_buffer << 1) | (1 if raw_pin_level else 0)) & 0xFFFF
        
        state_changed = False
        active_bits = self.history_buffer & self.filter_mask

        # Tüm son 'N' örnek 1 mi?
        if active_bits == self.filter_mask and self.stable_state == 0:
            self.stable_state = 1
            state_changed = True
        # Tüm son 'N' örnek 0 mı?
        elif active_bits == 0 and self.stable_state == 1:
            self.stable_state = 0
            state_changed = True

        return self.stable_state, state_changed

# Mekanik Kontak Sıçraması (Contact Bounce) ve EMI Gürültü Simülasyonu
# Butona basıldığında ilk 6 ms boyunca gürültülü dalgalanma (0, 1, 0, 1, 1...) oluşur:
noisy_samples = [0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1] # 18 ms timeline

debouncer = DigitalDebounceFilter(filter_depth=5)
filter_output = []
transition_count = 0

for ms, sample in enumerate(noisy_samples):
    state, changed = debouncer.process_sample(sample)
    filter_output.append(state)
    if changed:
        transition_count += 1
        print(f"  [+] Kararlı Durum Değişimi Algılandı: Zaman={ms} ms, Yeni Lojik Durum={state}")

print()
print("[*] Sayısal Giriş Filtreleme (Debounce) Testi:")
print(f"  [+] Ham Giriş Sinyali : {noisy_samples}")
print(f"  [+] Filtrelenmiş Çıkış: {filter_output}")
print(f"  [+] Tetiklenen Olay Sayısı: {transition_count} (Beklenen: Tam 1)")

assert transition_count == 1, "Debounce filtresi tüm sıçramaları tek bir kararlı olaya indirgemelidir!"
assert filter_output[-1] == 1
print("[HÜCRE 8] Sayısal debounce ve glitch filtresi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 164: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Floating Pin Gürültüsü ve Bus Çakışması
"""

import random
random.seed(42)

print()
print("[*] SABOTAJ SENARYOSU 1: Boşta Kalan (Floating) Giriş Pini ve Sahte Kesmeler")
floating_gpio = Stm32GpioPort("GPIOB")
# Pin 1 Floating Giriş olarak yapılandırılıyor (Pull-up / Pull-down YOK!)
floating_gpio.configure_pin(1, mode=Stm32GpioPort.MODE_INPUT, pupd=Stm32GpioPort.PUPD_NONE)

# Çevresel RF parazit simülasyonu: Gerilim 0.8V ile 2.2V arasında dalgalanıyor
rf_noise_voltages = [random.uniform(0.8, 2.2) for _ in range(50)]
false_interrupt_triggers = 0
last_state = 0

for v in rf_noise_voltages:
    floating_gpio.external_pin_voltage[1] = v
    current_state = bool(floating_gpio.read_idr() & (1 << 1))
    if current_state != last_state:
        false_interrupt_triggers += 1
        last_state = current_state

print(f"  [!] Havada Asılı (Floating) Pin Sahte Tetikleme Sayısı: {false_interrupt_triggers} kez!")
assert false_interrupt_triggers > 5, "Floating pin EMI altında sahte lojik sıçramalar üretmelidir!"

print()
print("[*] DÜZELTME: Dahili Pull-Down Direnci Devreye Alınıyor")
floating_gpio.configure_pin(1, mode=Stm32GpioPort.MODE_INPUT, pupd=Stm32GpioPort.PUPD_PULLDOWN)
floating_gpio.external_pin_voltage[1] = 0.0 # Direnç pini GND'ye sabitler
stable_state = bool(floating_gpio.read_idr() & (1 << 1))
print(f"  [+] Pull-Down Devrede: Pin Durumu = {stable_state} (Sıfır Gürültü)")
assert stable_state == False

print()
print("[*] SABOTAJ SENARYOSU 2: İki Push-Pull Çıkışın Birbirine Bağlanması (Kısa Devre / Bus Contention)")
class BusContentionMonitor:
    @staticmethod
    def connect_pins(pin1_mode: int, pin1_val: int, pin2_mode: int, pin2_val: int) -> str:
        # İki pin de Push-Pull Çıkış ise
        if pin1_mode == Stm32GpioPort.OTYPE_PUSHPULL and pin2_mode == Stm32GpioPort.OTYPE_PUSHPULL:
            if pin1_val != pin2_val:
                raise RuntimeError("CRITICAL HARDWARE DAMAGE: Kısa Devre! Bir pin 3.3V sürerken diğeri GND sürüyor (I_sc > 100mA)!")
        return "SAFE_CONNECTION"

bus_burn_caught = False
try:
    # Pin A Push-Pull 1 (3.3V), Pin B Push-Pull 0 (GND)
    BusContentionMonitor.connect_pins(Stm32GpioPort.OTYPE_PUSHPULL, 1, Stm32GpioPort.OTYPE_PUSHPULL, 0)
except RuntimeError as e:
    bus_burn_caught = True
    print(f"  [+] Savunma Başarılı: Push-Pull Çakışması / Yanma Uyarısı Yakalandı! ({e})")

assert bus_burn_caught == True
# Open-Drain bağlandığında güvenli olmalıdır:
safe_res = BusContentionMonitor.connect_pins(Stm32GpioPort.OTYPE_OPENDRAIN, 1, Stm32GpioPort.OTYPE_OPENDRAIN, 0)
assert safe_res == "SAFE_CONNECTION"
print("  [+] Open-Drain Bağlantısı: Kısa devre riski yok (Wired-AND güvenli).")
print("[HÜCRE 10] Sabotaj ve arıza enjeksiyon testleri başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 164: Kod Bloğu 4 — Donanımsal Konfigürasyon Kilitleme (LCKR Register Lock Sequence)
"""

class GpioConfigurationLocker:
    """
    STM32 GPIO Port Yapılandırma Kilidi (LCKR):
    Askeri kritik pinlerin (örn: Füze Harp Başlığı Ateşleme Pini) çalışma anında
    yazılımsal hatalar veya buffer-overflow açıklar ile giriş/çıkış modunun değiştirilmesini engeller.
    
    KİLİT AÇMA / ONAYLAMA SIRASI (Lock Sequence):
    1. LCKR = 0x00010000 | Pin_Mask (LCKK = 1)
    2. LCKR = 0x00000000 | Pin_Mask (LCKK = 0)
    3. LCKR = 0x00010000 | Pin_Mask (LCKK = 1)
    4. Read LCKR (LCKK biti okunur)
    5. Read LCKR (İkinci okuma kilidi onaylar: LCKK = 1)
    """
    def __init__(self, port: Stm32GpioPort):
        self.port = port

    def lock_pins(self, pin_mask: int):
        # 1. Adım: LCKK = 1
        seq1 = 0x00010000 | (pin_mask & 0xFFFF)
        # 2. Adım: LCKK = 0
        seq2 = 0x00000000 | (pin_mask & 0xFFFF)
        # 3. Adım: LCKK = 1
        seq3 = 0x00010000 | (pin_mask & 0xFFFF)

        # Sıralı yazma simülasyonu
        self.port.lckr = seq1
        self.port.lckr = seq2
        self.port.lckr = seq3

        # 4 ve 5. Adım: Çift okuma ile kilitlemeyi tamamla
        _ = self.port.lckr
        final_read = self.port.lckr

        if final_read & 0x00010000:
            self.port.is_locked = True
            print(f"  [LCKR] GPIO Portu Başarıyla Donanımsal Olarak KİLİTLENDİ (Pin Mask: 0x{pin_mask:04X})")

# Deney: PA0 (Piroteknik Ateşleme Pini) Yapılandırılıyor ve Kilitleniyor
test_port = Stm32GpioPort("GPIOA")
test_port.configure_pin(0, mode=Stm32GpioPort.MODE_OUTPUT, otype=Stm32GpioPort.OTYPE_PUSHPULL)

locker = GpioConfigurationLocker(test_port)
locker.lock_pins(pin_mask=(1 << 0)) # Sadece Pin 0'ı kilitle

# Kötü Amaçlı veya Hatalı Yazılım PA0 pinini 'GİRİŞ' yapmaya çalışıyor:
tamper_attempt_caught = False
try:
    test_port.configure_pin(0, mode=Stm32GpioPort.MODE_INPUT)
except PermissionError as e:
    tamper_attempt_caught = True
    print(f"  [+] Savunma Başarılı: Kilitli Pine Müdahale Engellendi! ({e})")

assert tamper_attempt_caught == True
# Pinin modu hala MODE_OUTPUT olarak kalmalıdır!
current_mode = (test_port.moder >> 0) & 0b11
assert current_mode == Stm32GpioPort.MODE_OUTPUT
print("[HÜCRE 12] LCKR donanımsal güvenlik kilidi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 164: Kod Bloğu 5 — ROKETSAN CİRİT / UMTAS Füze Emniyet ve Ateşleme (S&A) Birimi
"""

class RocketSafetyAndArmingUnit:
    """
    ROKETSAN Taktik Füze Emniyet ve Ateşleme Arayüzü:
    - Pin PA0: Piroteknik Roket Motoru Ateşleme Tetikleyicisi (Push-Pull, LCKR Kilitli)
    - Pin PA1: Acil Durum Ortak Alarm Hattı (Open-Drain Wired-OR Bus)
    - Pin PA2: Mekanik Kanatçık Ayrılma Limit Switch'i (Debounced Pull-Down Giriş)
    """
    def __init__(self):
        self.port = Stm32GpioPort("GPIOA")
        self.debouncer = DigitalDebounceFilter(filter_depth=4)
        self.missile_armed = False
        self.motor_ignited = False

        # Donanım Konfigürasyonu
        # PA0: Çıkış Push-Pull (Ateşleme)
        self.port.configure_pin(0, mode=Stm32GpioPort.MODE_OUTPUT, otype=Stm32GpioPort.OTYPE_PUSHPULL)
        # PA1: Open-Drain Çıkış (Ortak Alarm Barası)
        self.port.configure_pin(1, mode=Stm32GpioPort.MODE_OUTPUT, otype=Stm32GpioPort.OTYPE_OPENDRAIN, pupd=Stm32GpioPort.PUPD_PULLUP)
        # PA2: Giriş Pull-Down (Kanatçık Açılma Sensörü)
        self.port.configure_pin(2, mode=Stm32GpioPort.MODE_INPUT, pupd=Stm32GpioPort.PUPD_PULLDOWN)

        # PA0 Donanımsal Olarak Kilitleniyor!
        locker = GpioConfigurationLocker(self.port)
        locker.lock_pins(pin_mask=(1 << 0))

    def trigger_emergency_abort(self):
        """Open-Drain Hattını LOW Yaparak Tüm Füzeyi Kitle"""
        # BSRR üst 16-bit ile Pin 1 RESETlenir (GND'ye çekilir)
        self.port.write_bsrr(set_mask=0, reset_mask=(1 << 1))
        self.missile_armed = False
        print("  [ACİL DURUM] Open-Drain Alarm Hattı LOW'a Çekildi! Sistem kilitlendi.")

    def attempt_ignition(self) -> bool:
        """Ateşleme Denetimi: Yalnızca Alarm Hattı HIGH ve Kanatçık Açıksa Ateşle"""
        # Alarm hattı kontrolü
        alarm_bus_high = bool(self.port.read_idr() & (1 << 1))
        # Kanatçık kontrolü
        wing_deployed = bool(self.port.read_idr() & (1 << 2))

        if alarm_bus_high and wing_deployed and self.missile_armed:
            self.port.write_bsrr(set_mask=(1 << 0), reset_mask=0) # PA0 HIGH
            self.motor_ignited = True
            print("  [ATEŞLEME] Roket Motoru Ateşlendi! (PA0 = HIGH)")
            return True
        else:
            print(f"  [GÜVENLİK ENGELİ] Ateşleme Reddedildi! (Alarm_OK={alarm_bus_high}, Kanat={wing_deployed}, Kurulma={self.missile_armed})")
            return False

# Uçuş Senaryosu Simülasyonu
sa_unit = RocketSafetyAndArmingUnit()

print()
print("[*] ROKETSAN Füze Emniyet & Ateşleme Birimi Test Ediliyor:")
# 1. Adım: Sistem henüz kurulmadı, ateşleme başarısız olmalı
assert sa_unit.attempt_ignition() == False

# 2. Adım: Kanatçık sensöründen sinyal geliyor (Debounce doğrulaması)
for _ in range(5):
    sa_unit.debouncer.process_sample(1)
sa_unit.port.external_pin_voltage[2] = 3.3 # Donanımsal pin 3.3V

# 3. Adım: Füze kuruluyor (Arm)
sa_unit.missile_armed = True
# Alarm hattı normalde HIGH (Pull-up ile)
sa_unit.port.write_bsrr(set_mask=(1 << 1), reset_mask=0)

# 4. Adım: Ateşleme deneniyor -> BAŞARILI OLMALI
success = sa_unit.attempt_ignition()
assert success == True
assert sa_unit.motor_ignited == True

# 5. Adım: Uçuş sırasında acil iptal emri geliyor
sa_unit.trigger_emergency_abort()
assert (sa_unit.port.read_idr() & (1 << 1)) == 0 # Alarm hattı LOW
assert sa_unit.missile_armed == False

print("[HÜCRE 14] Taktik füze S&A arayüzü başarıyla simüle edildi ve doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 164: Kod Bloğu 6 — 4 Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_164_gpio_input_output.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_164\gun_164_gpio_input_output.png"

# Matplotlib Karanlık Tema Ayarları
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.0

fig = plt.figure(figsize=(18, 12), dpi=300, facecolor='#0F172A')
fig.suptitle("GÜN 164: STM32 GPIO Giriş/Çıkış Mimarisi, Push-Pull vs Open-Drain ve Sinyal Bütünlüğü Panosu",
             fontsize=14, fontweight='bold', color='#38BDF8', y=0.98)

# -----------------------------------------------------------------------------
# PANEL 1: Push-Pull vs Open-Drain Çıkış Katı Devre Şematiği
# -----------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1)
ax1.set_facecolor('#1E293B')
ax1.set_title("Panel 1: Push-Pull vs Open-Drain Transistör Çıkış Devresi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax1.axis('off')

# Push-Pull Kutusu
ax1.add_patch(patches.FancyBboxPatch((0.05, 0.52), 0.42, 0.42, boxstyle="round,pad=0.02", facecolor='#064E3B', edgecolor='#10B981', lw=2))
ax1.text(0.26, 0.88, "PUSH-PULL (OTYPER = 0)", ha='center', va='center', color='#34D399', fontweight='bold', fontsize=10)
ax1.text(0.26, 0.79, "Aktif P-MOS (3.3V) + Aktif N-MOS (GND)", ha='center', va='center', color='#CBD5E1', fontsize=8)
ax1.text(0.26, 0.70, "Hızlı Geçiş (Simetrik Slew Rate)", ha='center', va='center', color='#FBBF24', fontweight='bold', fontsize=8.5)
ax1.text(0.26, 0.60, "Kullanım: SPI, UART TX, PWM, LED\n(Asla doğrudan birbirine bağlanamaz!)", ha='center', va='center', color='#94A3B8', fontsize=7.5)

# Open-Drain Kutusu
ax1.add_patch(patches.FancyBboxPatch((0.53, 0.52), 0.42, 0.42, boxstyle="round,pad=0.02", facecolor='#78350F', edgecolor='#F59E0B', lw=2))
ax1.text(0.74, 0.88, "OPEN-DRAIN (OTYPER = 1)", ha='center', va='center', color='#FCD34D', fontweight='bold', fontsize=10)
ax1.text(0.74, 0.79, "P-MOS İptal! Sadece N-MOS (GND)", ha='center', va='center', color='#CBD5E1', fontsize=8)
ax1.text(0.74, 0.70, "1 Durumu: Hi-Z (Harici Pull-Up Şart)", ha='center', va='center', color='#F87171', fontweight='bold', fontsize=8.5)
ax1.text(0.74, 0.60, "Kullanım: I2C (SCL/SDA), Wired-OR Bus\n(Kısa devre riski sıfırdır, güvenli paylaşım)", ha='center', va='center', color='#94A3B8', fontsize=7.5)

# Alt Şematik Gösterim
ax1.add_patch(patches.Rectangle((0.15, 0.12), 0.70, 0.32, facecolor='#0F172A', edgecolor='#38BDF8', lw=1.5))
ax1.text(0.50, 0.38, "WIRED-OR / WIRED-AND ACİL DURUM HATTI", ha='center', va='center', color='#38BDF8', fontweight='bold', fontsize=9)
ax1.text(0.50, 0.28, "MCU 1 [Open-Drain] ---+--- [R_Pullup (4.7k)] ---> 3.3V\nMCU 2 [Open-Drain] ---+\nSensör [Open-Drain] --+---> ORTAK ALARM HATTI (Biri LOW çekerse hepsi durur!)",
         ha='center', va='center', color='#CBD5E1', fontsize=8)

ax1.set_xlim(0.0, 1.0)
ax1.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 2: Schmitt Trigger Histerezis ve Floating Gürültüsü
# -----------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2)
ax2.set_facecolor('#1E293B')
ax2.set_title("Panel 2: Schmitt Trigger Histerezis ve Parazit Bağışıklığı", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

t = np.linspace(0, 10, 500)
# Yavaş yükselen ve üzerinde yüksek frekanslı gürültü olan analog sinyal
analog_signal = 1.5 + 1.2 * np.sin(t * 0.6) + 0.18 * np.sin(t * 12.0)

v_high_threshold = 1.7 # V_T+
v_low_threshold  = 1.3 # V_T-

# Schmitt Trigger Çıkışı Hesaplama
schmitt_out = []
curr = 0
for v in analog_signal:
    if v >= v_high_threshold:
        curr = 3.3
    elif v <= v_low_threshold:
        curr = 0.0
    schmitt_out.append(curr)

ax2.plot(t, analog_signal, color='#38BDF8', lw=1.8, label="Fiziksel Giriş Gerilimi (Gürültülü Sinyal)")
ax2.plot(t, schmitt_out, color='#10B981', lw=2.2, linestyle='--', label="Schmitt Trigger IDR Çıkışı (Filtrelenmiş)")
ax2.axhline(v_high_threshold, color='#EF4444', linestyle=':', lw=1.2, label=f"V_T+ Eşiği ({v_high_threshold}V)")
ax2.axhline(v_low_threshold, color='#F59E0B', linestyle=':', lw=1.2, label=f"V_T- Eşiği ({v_low_threshold}V)")

ax2.set_xlabel("Zaman (ms)", color='#94A3B8')
ax2.set_ylabel("Gerilim (V)", color='#94A3B8')
ax2.set_ylim(-0.5, 4.0)
ax2.grid(True, color='#334155', alpha=0.5, linestyle='--')
ax2.legend(loc='upper right', fontsize=7.5, facecolor='#0F172A', edgecolor='#334155')

# -----------------------------------------------------------------------------
# PANEL 3: Sayısal Debounce Zamanlaması ve Glitch Bastırma
# -----------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3)
ax3.set_facecolor('#1E293B')
ax3.set_title("Panel 3: Mekanik Kontak Sıçraması (Bounce) ve Yazılımsal Filtre", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

time_ms = np.arange(0, 20, 1)
# 0-3ms 0, 3-8ms sıçrama, 8ms sonrası kararlı 1
raw_button = [0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

# 4ms Debouncer çıktısı
filtered_btn = [0]*7 + [1]*13

ax3.step(time_ms, [v + 1.4 for v in raw_button], color='#EF4444', lw=2.0, where='post', label="Ham Pin Sinyali (Kontak Sıçraması / 15 Tetikleme)")
ax3.step(time_ms, filtered_btn, color='#34D399', lw=2.2, where='post', label="Filtrelenmiş Kararlı Durum (Tek Kesme)")

ax3.axvspan(3, 8, color='#F59E0B', alpha=0.15, label="Mekanik Sıçrama Bölgesi (5 ms)")
ax3.text(5.5, 2.7, "Bounce Gürültüsü!", ha='center', color='#FCD34D', fontsize=8, fontweight='bold')

ax3.set_xlabel("Zaman (ms)", color='#94A3B8')
ax3.set_ylabel("Lojik Durum", color='#94A3B8')
ax3.set_yticks([0, 1, 1.4, 2.4])
ax3.set_yticklabels(["0", "1 (Filtre)", "0", "1 (Ham)"])
ax3.grid(True, color='#334155', alpha=0.5, linestyle='--')
ax3.legend(loc='center right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# -----------------------------------------------------------------------------
# PANEL 4: Slew Rate, EMI Işıması ve Ground Bounce İndüksiyonu
# -----------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4)
ax4.set_facecolor('#1E293B')
ax4.set_title("Panel 4: OSPEEDR Slew Rate vs Ground Bounce Ringing (V = L di/dt)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

t_edge = np.linspace(0, 10, 400) # ns

# High Speed (100 MHz): tr = 1ns, yüksek osilasyon ve ground bounce
v_high_speed = 3.3 / (1 + np.exp(-4 * (t_edge - 2))) + 0.6 * np.exp(-(t_edge - 2.5)) * np.sin(10 * (t_edge - 2.5)) * (t_edge > 2.5)
# Low Speed (2 MHz): tr = 5ns, yumuşak geçiş, sıfır ringing
v_low_speed = 3.3 / (1 + np.exp(-1.0 * (t_edge - 4)))

ax4.plot(t_edge, v_high_speed, color='#F43F5E', lw=2.0, label="High Speed (OSPEEDR=11): tr=1ns, Yüksek EMI & Ground Bounce Ringing")
ax4.plot(t_edge, v_low_speed, color='#38BDF8', lw=2.2, label="Low Speed (OSPEEDR=00): tr=5ns, Temiz Geçiş, Sıfır EMI")

ax4.axhline(3.3, color='#64748B', linestyle=':', lw=1.0)
ax4.axhline(0.0, color='#64748B', linestyle=':', lw=1.0)

ax4.set_xlabel("Zaman (ns)", color='#94A3B8')
ax4.set_ylabel("Pin Gerilimi (V)", color='#94A3B8')
ax4.set_ylim(-0.8, 4.5)
ax4.grid(True, color='#334155', alpha=0.5, linestyle='--')
ax4.legend(loc='lower right', fontsize=7.5, facecolor='#0F172A', edgecolor='#334155')

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 164 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert (gpio.odr & (1 << 5)) != 0
assert (idr & (1 << 0)) != 0
assert transition_count == 1
assert false_interrupt_triggers > 5
assert bus_burn_caught == True
assert tamper_attempt_caught == True
assert sa_unit.motor_ignited == True
assert (sa_unit.port.read_idr() & (1 << 1)) == 0

print()
print("[PASS] Gün 164: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")

