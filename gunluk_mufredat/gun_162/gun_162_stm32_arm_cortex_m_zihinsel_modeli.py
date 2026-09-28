# -*- coding: utf-8 -*-
"""
gun_162_stm32_arm_cortex_m_zihinsel_modeli
Otomatik Oluşturulan Çalıştırılabilir Python Betiği
"""

# -*- coding: utf-8 -*-
"""
GÜN 162: Kod Bloğu 1 — ARM Cortex-M Çekirdek, Yazmaçlar ve Donanımsal Stacking Simülatörü
"""

from typing import Dict, Any, List, Optional

class CortexMCpu:
    """
    ARM Cortex-M4/M7 Çekirdek Modeli:
    - R0 - R12: Genel Yazmaçlar
    - SP (R13): MSP ve PSP Çift Yığın İşaretçileri
    - LR (R14): Link Register
    - PC (R15): Program Counter
    - CONTROL: SPSEL ve nPRIV Bitleri
    - Modlar: Thread ve Handler Modu
    """
    EXC_RETURN_THREAD_MSP = 0xFFFFFFF9
    EXC_RETURN_THREAD_PSP = 0xFFFFFFFD
    EXC_RETURN_HANDLER    = 0xFFFFFFF1

    def __init__(self, sram_size_bytes: int = 128 * 1024):
        self.regs = [0] * 16  # R0 - R15
        self.msp = 0x20000000 + sram_size_bytes # En üst adres (Stack aşağı doğru büyür)
        self.psp = 0x20000000 + (sram_size_bytes // 2)
        self.xpsr = 0x01000000 # Thumb bit = 1
        self.control_spsel = 0 # 0 = MSP, 1 = PSP
        self.is_handler_mode = False

        # Bellek Deposu (Adres -> 32-bit Değer)
        self.memory: Dict[int, int] = {}

    @property
    def sp(self) -> int:
        return self.psp if (self.control_spsel == 1 and not self.is_handler_mode) else self.msp

    @sp.setter
    def sp(self, value: int):
        if self.control_spsel == 1 and not self.is_handler_mode:
            self.psp = value
        else:
            self.msp = value

    def push_stack(self, val: int):
        current_sp = self.sp - 4
        self.sp = current_sp
        self.memory[current_sp] = val & 0xFFFFFFFF

    def pop_stack(self) -> int:
        val = self.memory.get(self.sp, 0)
        self.sp = self.sp + 4
        return val

    def hardware_interrupt_entry(self, isr_address: int):
        """NVIC Donanımsal Otomatik Stacking (Tam 12 Saat Çevrimi)"""
        # 1. Yazmaçları stack'e donanımsal bas (xPSR, PC, LR, R12, R3, R2, R1, R0)
        stack_frame = [self.xpsr, self.regs[15], self.regs[14], self.regs[12],
                       self.regs[3], self.regs[2], self.regs[1], self.regs[0]]
        
        # O anki mod ve SP tipini kaydet
        was_using_psp = (self.control_spsel == 1 and not self.is_handler_mode)

        for val in stack_frame:
            self.push_stack(val)

        # 2. LR'ye EXC_RETURN Sihirli Değerini Yükle
        self.regs[14] = self.EXC_RETURN_THREAD_PSP if was_using_psp else self.EXC_RETURN_THREAD_MSP

        # 3. Handler Moduna Geç ve PC'yi ISR Adresine Yönlendir
        self.is_handler_mode = True
        self.regs[15] = isr_address & 0xFFFFFFFE # PC = ISR

    def hardware_interrupt_exit(self):
        """BX LR Komutu ile EXC_RETURN Yakalama ve Donanımsal Unstacking"""
        exc_return = self.regs[14]
        if exc_return not in (self.EXC_RETURN_THREAD_MSP, self.EXC_RETURN_THREAD_PSP, self.EXC_RETURN_HANDLER):
            raise ValueError(f"Geçersiz EXC_RETURN Değeri: 0x{exc_return:08X}")

        # EXC_RETURN değerine göre hangi stack'ten unstack yapılacağını belirle:
        # Bit 2: 0 = Return with MSP, 1 = Return with PSP
        unstack_from_psp = (exc_return == self.EXC_RETURN_THREAD_PSP) or bool(exc_return & 0x04)
        is_return_to_thread = (exc_return in (self.EXC_RETURN_THREAD_MSP, self.EXC_RETURN_THREAD_PSP)) or bool(exc_return & 0x08)

        # Unstacking sırası (Hardware stacking tersi: R0 en son atılmıştı, ilk çekilir)
        # Entry'de push sırası: xPSR, PC, LR, R12, R3, R2, R1, R0
        # SP aşağı büyüdüğünden R0 en tepededir; pop sırası: R0, R1, R2, R3, R12, LR, PC, xPSR
        def pop_target_stack() -> int:
            if unstack_from_psp:
                val = self.memory.get(self.psp, 0)
                self.psp += 4
                return val
            else:
                val = self.memory.get(self.msp, 0)
                self.msp += 4
                return val

        self.regs[0] = pop_target_stack()
        self.regs[1] = pop_target_stack()
        self.regs[2] = pop_target_stack()
        self.regs[3] = pop_target_stack()
        self.regs[12] = pop_target_stack()
        self.regs[14] = pop_target_stack()
        self.regs[15] = pop_target_stack()
        self.xpsr = pop_target_stack()

        # Modu güncelle
        self.is_handler_mode = not is_return_to_thread

# Simülatör Doğrulama: Görev Sırasında Kesme Gelmesi ve Geri Dönüş
cpu = CortexMCpu()
cpu.control_spsel = 1  # RTOS görevi PSP kullanıyor
cpu.regs[0] = 0xAA55AA55
cpu.regs[15] = 0x08001020 # Kullanıcı Görevi PC adresi

print("[*] Cortex-M Çekirdeği Başlatıldı:")
print(f"  [+] Başlangıç: Mod=Thread | SP={hex(cpu.sp)} | PC={hex(cpu.regs[15])}")

# Donanım Kesmesi Tetikleniyor! (Adres: 0x08002000)
ISR_ADDR = 0x08002000
cpu.hardware_interrupt_entry(ISR_ADDR)

print(f"  [+] Kesme Girişi (Hardware Stacking):")
print(f"      - Mod       : {'Handler (Kesme)' if cpu.is_handler_mode else 'Thread'}")
print(f"      - PC        : {hex(cpu.regs[15])} (ISR Adresi)")
print(f"      - LR (Link) : 0x{cpu.regs[14]:08X} (EXC_RETURN Sihirli Kodu)")

assert cpu.is_handler_mode == True
assert cpu.regs[15] == ISR_ADDR
assert cpu.regs[14] == CortexMCpu.EXC_RETURN_THREAD_PSP

# Kesme Bitiyor (BX LR)
cpu.hardware_interrupt_exit()
print(f"  [+] Kesme Çıkışı (Hardware Unstacking):")
print(f"      - Mod       : {'Handler' if cpu.is_handler_mode else 'Thread (Kullanıcı Görevi)'}")
print(f"      - PC        : {hex(cpu.regs[15])} (Orijinal Göreve Geri Dönüldü)")
print(f"      - R0        : 0x{cpu.regs[0]:08X} (Kusursuz Korundu)")

assert cpu.is_handler_mode == False
assert cpu.regs[15] == 0x08001020
assert cpu.regs[0] == 0xAA55AA55
print("[HÜCRE 6] ARM Cortex-M donanımsal stacking ve EXC_RETURN simülatörü başarıyla test edildi.")

# -*- coding: utf-8 -*-
"""
GÜN 162: Kod Bloğu 2 — STM32 Bus Matrix, Bellek Haritası ve RCC Clock Gating Motoru
"""

class Stm32BusMatrix:
    """
    STM32F4 / F7 Çok Katmanlı Bus Matrix ve Çevresel Birim Haritası:
    - Flash: 0x08000000 (2 MB)
    - SRAM:  0x20000000 (128 KB - 512 KB)
    - APB1:  0x40000000 (CAN1, TIM2, USART2)
    - APB2:  0x40010000 (TIM1, USART1, SPI1)
    - AHB1:  0x40020000 (GPIOA..GPIOK, RCC, DMA1, DMA2)
    """
    FLASH_BASE = 0x08000000
    SRAM_BASE  = 0x20000000
    PERIPH_BASE= 0x40000000
    
    RCC_BASE   = 0x40023800
    GPIOA_BASE = 0x40020000
    TIM1_BASE  = 0x40010000

    def __init__(self):
        # RCC Saat Yazmaçları (Reset durumunda hepsi 0 = KAPALI)
        self.rcc_ahb1enr = 0x00000000
        self.rcc_apb2enr = 0x00000000

        # Çevresel Birim Bellekleri (Adres -> 32-bit Veri)
        self.periph_registers: Dict[int, int] = {}
        self.flash_memory: Dict[int, int] = {}
        self.sram_memory: Dict[int, int] = {}

    def write_register(self, address: int, value: int):
        # 1. RCC Yazmaçlarına Erişim
        if address == self.RCC_BASE:
            self.rcc_ahb1enr = value
            return
        elif address == self.RCC_BASE + 0x04:
            self.rcc_apb2enr = value
            return

        # 2. GPIOA Yazmaçlarına Erişim (AHB1 Saat Denetimi)
        if self.GPIOA_BASE <= address < self.GPIOA_BASE + 0x400:
            if not (self.rcc_ahb1enr & 0x01): # Bit 0: GPIOA Clock Enable
                raise PermissionError("HARDFAULT / BUSFAULT: GPIOA erişimi başarısız! RCC AHB1ENR saat kapısı KAPALI!")
            self.periph_registers[address] = value
            return

        # 3. TIM1 Yazmaçlarına Erişim (APB2 Saat Denetimi)
        if self.TIM1_BASE <= address < self.TIM1_BASE + 0x400:
            if not (self.rcc_apb2enr & 0x01): # Bit 0: TIM1 Clock Enable
                raise PermissionError("HARDFAULT / BUSFAULT: TIM1 erişimi başarısız! RCC APB2ENR saat kapısı KAPALI!")
            self.periph_registers[address] = value
            return

        # Genel Yazmaç
        self.periph_registers[address] = value

    def read_register(self, address: int) -> int:
        if self.GPIOA_BASE <= address < self.GPIOA_BASE + 0x400:
            if not (self.rcc_ahb1enr & 0x01):
                raise PermissionError("HARDFAULT / BUSFAULT: GPIOA okunamadı! RCC saati kapalı!")
        return self.periph_registers.get(address, 0)

print("[*] STM32 Bus Matrix ve RCC Saat Denetim Motoru Tanımlandı.")
print("[HÜCRE 8] Bus matrix ve RCC motoru hazır.")

# -*- coding: utf-8 -*-
"""
GÜN 162: Kod Bloğu 3 — Sabotaj ve Hata Enjeksiyonu: BusFault ve HardFault İhlalleri
"""

bus = Stm32BusMatrix()

print()
print("[*] SABOTAJ SENARYOSU 1: RCC Saati Açılmadan GPIO Portuna Yazma (BusFault)")
bus_fault_caught = False
try:
    # Henüz RCC->AHB1ENR açılmadı! GPIOA MODER yazmacına yazmaya çalışıyoruz:
    bus.write_register(Stm32BusMatrix.GPIOA_BASE, 0x00000001)
except PermissionError as e:
    bus_fault_caught = True
    print(f"  [+] Savunma Başarılı: Beklenen Donanım Hatası Yakalandı! ({e})")

assert bus_fault_caught == True, "Saat verilmeyen birime erişim BusFault üretmelidir!"

print()
print("[*] DÜZELTME: RCC Saati Açılıyor ve GPIO Yapılandırılıyor")
# 1. RCC AHB1ENR'da GPIOA bitini (Bit 0) aç
bus.write_register(Stm32BusMatrix.RCC_BASE, 0x00000001)
# 2. Şimdi GPIOA'ya yaz
bus.write_register(Stm32BusMatrix.GPIOA_BASE, 0x00000001)
val = bus.read_register(Stm32BusMatrix.GPIOA_BASE)
print(f"  [+] GPIOA MODER Yazmacı Başarıyla Yazıldı: 0x{val:08X}")
assert val == 0x00000001

print()
print("[*] SABOTAJ SENARYOSU 2: Thumb-2 Kural İhlali (Reset Vektöründe Çift Sayılı Adres)")
# ARM Cortex-M sadece Thumb komut setini destekler. Vektör tablosundaki tüm fonksiyon adreslerinin
# Bit 0'ı (Thumb bit) mutlaka 1 (Tek sayı) olmalıdır! Eğer çift sayı (örn: 0x08001000) verilirse CPU HardFault verir.

def validate_arm_cortex_vector(address: int) -> bool:
    if (address & 0x01) == 0:
        raise ValueError(f"HARDFAULT: Geçersiz Vektör Adresi 0x{address:08X}! Bit 0 (Thumb Bit) 1 olmalıdır!")
    return True

thumb_fault_caught = False
try:
    # Hatalı çift sayılı reset adresi
    validate_arm_cortex_vector(0x08002040)
except ValueError as e:
    thumb_fault_caught = True
    print(f"  [+] Savunma Başarılı: Thumb Kural İhlali Yakalandı! ({e})")

assert thumb_fault_caught == True
# Yasal adres: 0x08002041 (Bit 0 = 1)
assert validate_arm_cortex_vector(0x08002041) == True
print("[HÜCRE 10] Sabotaj ve kural doğrulama testleri başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 162: Kod Bloğu 4 — NVIC Kesme Önceliklendirme (Preemption) ve Tail-Chaining Simülatörü
"""

class NvicInterruptController:
    """
    ARM Cortex-M NVIC Donanım Motoru:
    - Preemption Priority (Öncelik Seviyesi: Düşük sayı = Yüksek öncelik)
    - Yuvalanmış Kesmeler (Nested Interrupts)
    - Tail-Chaining Sıfır Maliyetli Kesme Geçişi
    """
    def __init__(self):
        # Kesme Numarası -> Öncelik Seviyesi (0 en yüksek öncelik)
        self.priorities: Dict[str, int] = {
            "HARDFAULT": -1, # Negatif = Donanımsal Sabit Öncelik
            "EMERGENCY_EXTI": 0, # En Yüksek Kullanıcı Kesmesi
            "TIM1_MOTOR_PID": 1,
            "UART_TELEMETRY": 2
        }
        self.active_interrupt_stack: List[str] = []
        self.tail_chaining_events = 0
        self.execution_log = []

    def trigger_interrupt(self, name: str):
        prio = self.priorities[name]
        
        # Eğer çalışan bir kesme varsa
        if self.active_interrupt_stack:
            current_active = self.active_interrupt_stack[-1]
            curr_prio = self.priorities[current_active]
            
            # Gelen kesmenin önceliği daha mı yüksek? (Daha küçük sayı)
            if prio < curr_prio:
                # PREEMPTION (Araya Girme): Çalışan kesmeyi böl ve öne geç!
                self.execution_log.append(f"[PREEMPTION] {name} (Prio {prio}), {current_active} (Prio {curr_prio}) kesmesini BÖLDÜ!")
                self.active_interrupt_stack.append(name)
            else:
                # Bekleme kuyruğuna al veya Tail-Chaining yap
                self.tail_chaining_events += 1
                self.execution_log.append(f"[TAIL-CHAINING] {name} (Prio {prio}) beklemeye alındı, {current_active} bittiğinde 6 çevrimde girecek.")
        else:
            self.active_interrupt_stack.append(name)
            self.execution_log.append(f"[ENTRY] {name} Kesmesi Başlatıldı.")

    def finish_current_interrupt(self):
        if self.active_interrupt_stack:
            finished = self.active_interrupt_stack.pop()
            self.execution_log.append(f"[EXIT] {finished} Kesmesi Tamamlandı.")

# Deney: Motor Kontrolü Sırasında Acil Durum Kesmesi Gelmesi
nvic = NvicInterruptController()

# 1. 1000 Hz Motor Kontrol Kesmesi Başlıyor (Prio 1)
nvic.trigger_interrupt("TIM1_MOTOR_PID")

# 2. Motor dönerken ACİL NAMLU LİMİT KESMESİ Geliyor! (Prio 0 - Daha Yüksek!)
nvic.trigger_interrupt("EMERGENCY_EXTI")

# 3. Aynı anda arka planda UART telemetrisi tetikleniyor (Prio 2 - Daha Düşük!)
nvic.trigger_interrupt("UART_TELEMETRY")

# Kesmeler Tamamlanıyor
nvic.finish_current_interrupt() # EMERGENCY_EXTI biter
nvic.finish_current_interrupt() # TIM1_MOTOR_PID biter

print()
print("[*] NVIC Donanım Kesme ve Tail-Chaining Yürütme Günlüğü:")
for log in nvic.execution_log:
    print(f"  {log}")

assert nvic.tail_chaining_events == 1
assert "[PREEMPTION]" in nvic.execution_log[1]
print("[HÜCRE 12] NVIC kesme önceliklendirme ve tail-chaining testi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 162: Kod Bloğu 5 — ASELSAN KORKUT 35mm Namlu Stabilizasyon Kontrol Çekirdeği
"""

class KorkutBarrelStabilizer:
    """
    ASELSAN KORKUT Uçaksavar Sistemi STM32H7 Aviyonik Modeli:
    - SysTick / Thread Modu (PSP): 1000 Hz Gyro Okuma ve Kalman/PID Stabilizasyonu
    - EXTI (Handler / MSP): Namlu Açı Sınırı Limit Sensörü (Acil Donanım Kesmesi)
    """
    def __init__(self):
        self.cpu = CortexMCpu()
        self.barrel_elevation_deg = 45.0
        self.target_elevation_deg = 45.0
        self.emergency_stop_triggered = False
        self.pid_cycles_completed = 0

    def systick_pid_control_loop(self):
        """Thread Modunda (PSP) Çalışan 1000 Hz Stabilizasyon Döngüsü"""
        if self.emergency_stop_triggered:
            return  # Acil durdurma devrede!

        # Basit PID Hata Düzeltme
        error = self.target_elevation_deg - self.barrel_elevation_deg
        self.barrel_elevation_deg += error * 0.2
        self.pid_cycles_completed += 1

    def exti_limit_switch_isr(self):
        """Handler Modunda (MSP) Çalışan Donanımsal Acil Kesme"""
        # Namlu fiziksel sınırları aştı! (Örn: 85 dereceyi geçti)
        self.emergency_stop_triggered = True

# Görev Simülasyonu: KORKUT Namlusu Hedefe Yöneliyor
korkut = KorkutBarrelStabilizer()
korkut.target_elevation_deg = 65.0

# 5 Döngü Normal Stabilizasyon
for _ in range(5):
    korkut.systick_pid_control_loop()

print()
print(f"[*] KORKUT Namlu Stabilizasyonu Başlatıldı (Elevasyon: {korkut.barrel_elevation_deg:.2f}°)")

# Simüle Edilen Arıza: Namlu sensörü arızalandı ve açı 88 dereceye fırladı!
# Donanımsal EXTI Kesmesi Tetikleniyor:
korkut.cpu.hardware_interrupt_entry(isr_address=0x08003000)
korkut.exti_limit_switch_isr()
korkut.cpu.hardware_interrupt_exit()

# Sonraki döngülerde acil durum nedeniyle motorlar durdurulmalıdır
for _ in range(5):
    korkut.systick_pid_control_loop()

print(f"  [+] EXTI Acil Güvenlik Kesmesi Tetiklendi!")
print(f"  [+] Acil Durdurma Durumu : {korkut.emergency_stop_triggered}")
print(f"  [+] Tamamlanan PID Döngüsü: {korkut.pid_cycles_completed} (Döngü donduruldu)")

assert korkut.emergency_stop_triggered == True
assert korkut.pid_cycles_completed == 5, "Acil durum sonrası PID döngüsü derhal kilitlenmelidir!"
print("[HÜCRE 14] Taktik KORKUT stabilizasyon senaryosu başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 162: Kod Bloğu 6 — 4 Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_162_stm32_arm_cortex_m_zihinsel_modeli.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_162\gun_162_stm32_arm_cortex_m_zihinsel_modeli.png"

# Matplotlib Karanlık Tema Ayarları
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.0

fig = plt.figure(figsize=(18, 12), dpi=300, facecolor='#0F172A')
fig.suptitle("GÜN 162: STM32 ve ARM Cortex-M Zihinsel Modeli ve Donanım Mimarisi Panosu",
             fontsize=15, fontweight='bold', color='#38BDF8', y=0.98)

# -----------------------------------------------------------------------------
# PANEL 1: ARM Cortex-M Çekirdek Modları ve Çift Yığın (MSP vs PSP)
# -----------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1)
ax1.set_facecolor('#1E293B')
ax1.set_title("Panel 1: ARM Cortex-M Çalışma Modları ve Çift Yığın (Dual Stack)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax1.axis('off')

# Thread Mode Kutusu
tm_box = patches.FancyBboxPatch((0.05, 0.45), 0.42, 0.45, boxstyle="round,pad=0.02", facecolor='#064E3B', edgecolor='#10B981', lw=2)
ax1.add_patch(tm_box)
ax1.text(0.26, 0.82, "THREAD MODE", ha='center', va='center', color='#34D399', fontweight='bold', fontsize=11)
ax1.text(0.26, 0.74, "Kullanıcı Görevleri (Tasks)", ha='center', va='center', color='#CBD5E1', fontsize=8.5)
ax1.text(0.26, 0.65, "Yığın: PSP (Process Stack)", ha='center', va='center', color='#FBBF24', fontweight='bold', fontsize=9)
ax1.text(0.26, 0.54, "Ayrıcalık: Unprivileged / Privileged\n(Görev çökmesi çekirdeği etkilemez)", ha='center', va='center', color='#94A3B8', fontsize=7.5)

# Handler Mode Kutusu
hm_box = patches.FancyBboxPatch((0.53, 0.45), 0.42, 0.45, boxstyle="round,pad=0.02", facecolor='#7F1D1D', edgecolor='#EF4444', lw=2)
ax1.add_patch(hm_box)
ax1.text(0.74, 0.82, "HANDLER MODE", ha='center', va='center', color='#F87171', fontweight='bold', fontsize=11)
ax1.text(0.74, 0.74, "Kesmeler & İstisnalar (ISR)", ha='center', va='center', color='#CBD5E1', fontsize=8.5)
ax1.text(0.74, 0.65, "Yığın: MSP (Main Stack)", ha='center', va='center', color='#FBBF24', fontweight='bold', fontsize=9)
ax1.text(0.74, 0.54, "Ayrıcalık: DAİMA PRIVILEGED\n(Tam donanım erişim yetkisi)", ha='center', va='center', color='#94A3B8', fontsize=7.5)

# Geçiş Okları
ax1.annotate("", xy=(0.53, 0.65), xytext=(0.47, 0.65), arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2.5))
ax1.text(0.50, 0.69, "Kesme Tetiklendi\n(HW Stacking)", ha='center', va='bottom', color='#38BDF8', fontsize=7.5, fontweight='bold')

ax1.annotate("", xy=(0.47, 0.52), xytext=(0.53, 0.52), arrowprops=dict(arrowstyle="->", color='#A78BFA', lw=2.5))
ax1.text(0.50, 0.47, "BX LR (EXC_RETURN)\n(HW Unstacking)", ha='center', va='top', color='#A78BFA', fontsize=7.5, fontweight='bold')

# CONTROL Register Gösterimi
ctrl_box = patches.Rectangle((0.15, 0.12), 0.70, 0.22, facecolor='#0F172A', edgecolor='#38BDF8', lw=1.5)
ax1.add_patch(ctrl_box)
ax1.text(0.5, 0.27, "CONTROL REGISTER (SPSEL Biti)", ha='center', va='center', color='#38BDF8', fontweight='bold', fontsize=9)
ax1.text(0.5, 0.18, "SPSEL = 0 -> MSP Seçili (Kernel / Boot) | SPSEL = 1 -> PSP Seçili (RTOS Görevleri)", ha='center', va='center', color='#CBD5E1', fontsize=8)

ax1.set_xlim(0.0, 1.0)
ax1.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 2: STM32 Bus Matrix ve Bellek Haritası
# -----------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2)
ax2.set_facecolor('#1E293B')
ax2.set_title("Panel 2: STM32 Multi-Layer Bus Matrix ve Adres Haritası", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax2.axis('off')

regions = [
    ("Sistem Belleği / Çevre Birimleri (System)", "0xE0000000 - 0xFFFFFFFF (NVIC, SysTick, Core Debug)", "#64748B", 0.80),
    ("Çevresel Birimler (Peripherals - APB1/APB2/AHB)", "0x40000000 - 0x5FFFFFFF (GPIO, TIM, CAN, USART, RCC)", "#D97706", 0.60),
    ("Dahili SRAM (SRAM1 + SRAM2 + DTCM)", "0x20000000 - 0x3FFFFFFF (Yığın, Heap, Global Değişkenler)", "#059669", 0.40),
    ("Dahili Flash Bellek (Flash / Code Space)", "0x08000000 - 0x081FFFFF (Vektör Tablosu, C++20 Kod)", "#0284C7", 0.20)
]

for title, desc, col, ypos in regions:
    ax2.add_patch(patches.Rectangle((0.05, ypos), 0.90, 0.15, facecolor=col, alpha=0.3, edgecolor=col, lw=2))
    ax2.text(0.08, ypos + 0.09, title, color='#F8FAFC', fontweight='bold', fontsize=8.5)
    ax2.text(0.08, ypos + 0.035, desc, color='#CBD5E1', fontsize=7.5)

ax2.set_xlim(0.0, 1.0)
ax2.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 3: Donanımsal Kesme Stacking ve Unstacking (12 Çevrim)
# -----------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3)
ax3.set_facecolor('#1E293B')
ax3.set_title("Panel 3: NVIC Donanımsal Context Stacking Çerçevesi (32 Bayt)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax3.axis('off')

stack_elements = [
    ("xPSR (Program Durum Yazmacı)", "#8B5CF6", 0.82),
    ("PC (Program Counter / Dönüş Adresi)", "#EC4899", 0.72),
    ("LR (Link Register / R14)", "#3B82F6", 0.62),
    ("R12 (Scratch Register)", "#0284C7", 0.52),
    ("R3 (Fonksiyon Argümanı 4)", "#10B981", 0.42),
    ("R2 (Fonksiyon Argümanı 3)", "#10B981", 0.32),
    ("R1 (Fonksiyon Argümanı 2)", "#10B981", 0.22),
    ("R0 (Fonksiyon Argümanı 1)", "#10B981", 0.12)
]

ax3.text(0.05, 0.94, "SP -> [Aşağı Doğru Büyüyen Yığın Bellek (Stack Frame)]:", color='#CBD5E1', fontsize=8.5, fontweight='bold')

for name, col, ypos in stack_elements:
    ax3.add_patch(patches.Rectangle((0.15, ypos), 0.70, 0.08, facecolor=col, edgecolor='#FFFFFF', lw=1.2))
    ax3.text(0.50, ypos + 0.04, name, ha='center', va='center', color='#FFFFFF', fontweight='bold', fontsize=8)

ax3.set_xlim(0.0, 1.0)
ax3.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 4: NVIC Tail-Chaining Sıfır Maliyetli Geçiş Zamanlaması
# -----------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4)
ax4.set_facecolor('#1E293B')
ax4.set_title("Panel 4: Klasik Kesme vs ARM Cortex-M Tail-Chaining", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax4.axis('off')

# Klasik İşlemci
ax4.text(0.05, 0.85, "1. KLASİK İŞLEMCİ: Tam Unstacking + Tekrar Stacking (24-32 Çevrim İsraf)", color='#EF4444', fontweight='bold', fontsize=8.5)
ax4.add_patch(patches.Rectangle((0.05, 0.70), 0.30, 0.10, facecolor='#10B981', edgecolor='#FFFFFF', lw=1))
ax4.text(0.20, 0.75, "ISR 1 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

ax4.add_patch(patches.Rectangle((0.37, 0.70), 0.22, 0.10, facecolor='#EF4444', edgecolor='#FFFFFF', lw=1))
ax4.text(0.48, 0.75, "POP + PUSH\n(24 Çevrim İsraf!)", ha='center', va='center', color='#FFFFFF', fontsize=7)

ax4.add_patch(patches.Rectangle((0.61, 0.70), 0.30, 0.10, facecolor='#38BDF8', edgecolor='#FFFFFF', lw=1))
ax4.text(0.76, 0.75, "ISR 2 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

# ARM Cortex-M Tail-Chaining
ax4.text(0.05, 0.45, "2. ARM CORTEX-M: Tail-Chaining ile Sıfır Stack İşlemi (Sadece 6 Çevrim)", color='#10B981', fontweight='bold', fontsize=8.5)
ax4.add_patch(patches.Rectangle((0.05, 0.30), 0.38, 0.10, facecolor='#10B981', edgecolor='#FFFFFF', lw=1))
ax4.text(0.24, 0.35, "ISR 1 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

ax4.add_patch(patches.Rectangle((0.45, 0.30), 0.10, 0.10, facecolor='#F59E0B', edgecolor='#FFFFFF', lw=1))
ax4.text(0.50, 0.35, "TC\n(6ç)", ha='center', va='center', color='#FFFFFF', fontsize=7.5, fontweight='bold')

ax4.add_patch(patches.Rectangle((0.57, 0.30), 0.38, 0.10, facecolor='#38BDF8', edgecolor='#FFFFFF', lw=1))
ax4.text(0.76, 0.35, "ISR 2 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

# Alt Açıklama
ax4.text(0.50, 0.12, "* Tail-Chaining sayesinde ardışık kesmelerde bellek erişimi yapılmaz; yazmaçlar korunarak direkt sıradaki vektöre atlanır.",
         ha='center', va='center', color='#CBD5E1', fontsize=8, fontstyle='italic')

ax4.set_xlim(0.0, 1.0)
ax4.set_ylim(0.0, 1.0)

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 162 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert bus_fault_caught == True
assert thumb_fault_caught == True
assert nvic.tail_chaining_events == 1
assert korkut.emergency_stop_triggered == True
assert korkut.pid_cycles_completed == 5

print()
print("[PASS] Gün 162: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")

