# -*- coding: utf-8 -*-
"""
GÜN 166: STM32 Kesmeler (Interrupts), NVIC Mimarisi, Preemption, EXTI ve ISR Tasarım İlkeleri
Otomatik Oluşturulan Çalıştırılabilir Python Betiği
"""

# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 1 — STM32 NVIC Çok Seviyeli Kesme ve Vektör Tablosu Simülatörü
(Preemption, Sub-Priority, Vektör Tablosu ve Donanımsal Yuvalanma)
"""

from typing import Dict, List, Any, Optional
import time

class NvicInterruptEngine:
    """
    ARM Cortex-M NVIC Donanım Motoru Modeli:
    - Preemption Priority (Öncelik: 0 en yüksek, 15 en düşük)
    - Sub-Priority (Aynı anda tetiklenenlerde sıra belirleme)
    - ISER / ICER (Etkinleştirme / Devre Dışı Bırakma)
    - ISPR / ICPR (Bekleme / Pending Yönetimi)
    - IABR (O anda aktif çalışan kesmeler)
    """
    def __init__(self, prigroup: int = 4):
        self.prigroup = prigroup # 4: 4-bit Preemption (0..15 seviye)
        self.vector_table: Dict[int, str] = {
            0: "RESET_HANDLER",
            1: "NMI_HANDLER",
            2: "HARDFAULT_HANDLER",
            16: "EXTI0_LASER_DETECT", # Harici Kesme 0
            17: "TIM1_UP_MOTOR_PID",  # Motor PID
            18: "USART1_TELEMETRY",   # Seri Telemetri
            19: "EXTI15_10_SAFETY"    # Emniyet Kilidi
        }
        
        # Kesme Nitelikleri: irq_num -> (Preemption, SubPriority, Enabled, Pending)
        self.irq_config: Dict[int, Dict[str, Any]] = {}
        self.active_stack: List[int] = [] # Çalışan kesmeler yığını (Nesting)
        self.execution_trace: List[str] = []

    def register_irq(self, irq_num: int, preemption: int, sub_prio: int = 0):
        self.irq_config[irq_num] = {
            "preemption": preemption,
            "sub_prio": sub_prio,
            "enabled": True,
            "pending": False
        }

    def trigger_interrupt(self, irq_num: int) -> bool:
        """Donanımsal veya Yazılımsal Kesme Tetikleme"""
        if irq_num not in self.irq_config or not self.irq_config[irq_num]["enabled"]:
            return False

        name = self.vector_table.get(irq_num, f"IRQ_{irq_num}")
        incoming_prio = self.irq_config[irq_num]["preemption"]

        # Eğer şu anda çalışan bir kesme varsa
        if self.active_stack:
            current_active = self.active_stack[-1]
            current_prio = self.irq_config[current_active]["preemption"]

            # PREEMPTION KONTROLÜ: Gelen kesmenin önceliği daha mı yüksek? (Daha küçük sayı)
            if incoming_prio < current_prio:
                self.execution_trace.append(f"[PREEMPTION] {name} (Prio {incoming_prio}) -> {self.vector_table[current_active]} (Prio {current_prio}) kesmesini BÖLDÜ!")
                self.active_stack.append(irq_num)
                return True
            else:
                # Kesme beklemeye alınıyor (Pending)
                self.irq_config[irq_num]["pending"] = True
                self.execution_trace.append(f"[PENDING] {name} (Prio {incoming_prio}) beklemeye alındı (Çalışan Prio {current_prio})")
                return False
        else:
            # İşlemci Thread modundaydı, doğrudan kesmeye girilir
            self.execution_trace.append(f"[ENTER] {name} (Prio {incoming_prio}) kesmesine girildi.")
            self.active_stack.append(irq_num)
            return True

    def finish_current_isr(self):
        """BX LR (EXC_RETURN) ile Kesmeden Çıkış"""
        if self.active_stack:
            finished = self.active_stack.pop()
            finished_name = self.vector_table.get(finished, f"IRQ_{finished}")
            self.execution_trace.append(f"[EXIT] {finished_name} tamamlandı.")

            # Sırada bekleyen (Pending) kesme var mı? (Tail-Chaining)
            pending_irqs = [irq for irq, cfg in self.irq_config.items() if cfg["pending"]]
            if pending_irqs:
                # En yüksek öncelikli olanı seç (En küçük preemption)
                pending_irqs.sort(key=lambda x: (self.irq_config[x]["preemption"], self.irq_config[x]["sub_prio"]))
                next_irq = pending_irqs[0]
                self.irq_config[next_irq]["pending"] = False
                next_name = self.vector_table[next_irq]
                self.execution_trace.append(f"[TAIL-CHAINING] 6 Çevrimde doğrudan {next_name} kesmesine geçildi (Sıfır Stack Masrafı).")
                self.active_stack.append(next_irq)

# Doğrulama Testi
nvic = NvicInterruptEngine()
# Kesme Öncelikleri: EXTI0 (0 - En yüksek), TIM1 (1 - Orta), USART1 (2 - Düşük)
nvic.register_irq(18, preemption=2) # USART1
nvic.register_irq(17, preemption=1) # TIM1
nvic.register_irq(16, preemption=0) # EXTI0

# Senaryo 1: USART telemetri paketi alınıyor (Prio 2)
nvic.trigger_interrupt(18)

# Senaryo 2: USART çalışırken 2000 Hz TIM1 Motor PID kesmesi geliyor (Prio 1 < 2 -> BÖLER!)
nvic.trigger_interrupt(17)

# Senaryo 3: Motor PID çalışırken ACİL LAZER DARBESİ EXTI0 Geliyor! (Prio 0 < 1 -> BÖLER!)
nvic.trigger_interrupt(16)

# Kesmeler sırayla biter
nvic.finish_current_isr() # EXTI0 biter, TIM1'e döner
nvic.finish_current_isr() # TIM1 biter, USART'a döner
nvic.finish_current_isr() # USART biter, ana göreve döner

print("[*] NVIC Çok Seviyeli Yuvalanmış Kesme Yürütme İzi:")
for trace in nvic.execution_trace:
    print(f"  {trace}")

assert "[PREEMPTION]" in nvic.execution_trace[1]
assert "[PREEMPTION]" in nvic.execution_trace[2]
assert len(nvic.active_stack) == 0, "Tüm kesmeler başarıyla tamamlanmış olmalıdır!"
print("[HÜCRE 6] NVIC çok seviyeli kesme ve preemption motoru başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 2 — EXTI (External Interrupt) Hat Eşlemesi ve Write-1-to-Clear Mekanizması
"""

class ExtiHardwareController:
    """
    STM32 EXTI Donanım Kontrolcüsü:
    - IMR  (Interrupt Mask Register): Kesme maskesi (1: Açık, 0: Kapalı)
    - RTSR (Rising Trigger Selection Register): Yükselen kenar tetikleme
    - FTSR (Falling Trigger Selection Register): Düşen kenar tetikleme
    - PR   (Pending Register): Bayrak yazmacı (WRITE-1-TO-CLEAR!)
    - SYSCFG EXTI Multiplexer: Pin 0 sadece PA0, PB0 veya PC0'dan birine bağlanabilir!
    """
    def __init__(self):
        self.imr = 0x0000
        self.rtsr = 0x0000
        self.ftsr = 0x0000
        self.pr = 0x0000
        self.syscfg_exti0_port = "PA" # PA0 seçili

    def configure_exti_line(self, line: int, port: str, rising: bool = True, falling: bool = False):
        if line == 0:
            self.syscfg_exti0_port = port

        # Maskeyi aç
        self.imr |= (1 << line)
        if rising:
            self.rtsr |= (1 << line)
        if falling:
            self.ftsr |= (1 << line)

    def trigger_pin_event(self, line: int, port: str, edge: str) -> bool:
        """Dış Fiziksel Pinden Kenar Gelmesi"""
        # 1. SYSCFG port doğrulaması: Doğru port mu bağlı?
        if line == 0 and port != self.syscfg_exti0_port:
            return False # Yanlış port, multiplexer sinyali geçirmez!

        # 2. Kenar kontrolü
        is_valid_edge = False
        if edge == "RISING" and (self.rtsr & (1 << line)):
            is_valid_edge = True
        elif edge == "FALLING" and (self.ftsr & (1 << line)):
            is_valid_edge = True

        # 3. Maske kontrolü
        if is_valid_edge and (self.imr & (1 << line)):
            # Donanım PR bayrağını Lojik-1 yapar!
            self.pr |= (1 << line)
            return True
        return False

    def clear_pending_flag(self, line: int, write_value: int):
        """WRITE-1-TO-CLEAR Mekanizması: Sadece 1 yazıldığında temizlenir!"""
        if write_value & (1 << line):
            self.pr &= ~(1 << line) # Bayrak sıfırlanır

# EXTI Yapılandırma ve Test
exti = ExtiHardwareController()
# EXTI Hat 0 PA0 pinine bağlanıyor, Yükselen Kenar aktif
exti.configure_exti_line(line=0, port="PA", rising=True, falling=False)

# PA0 pini Lojik 0 -> 1 geçişi yapıyor (Lazer darbesi!)
event_generated = exti.trigger_pin_event(line=0, port="PA", edge="RISING")

print()
print("[*] EXTI Donanımsal Hat Eşleme ve Tetikleme Testi:")
print(f"  [+] EXTI0 PA0 Tetiklendi mi? : {event_generated}")
print(f"  [+] Pending Register (PR)   : 0x{exti.pr:04X} (Hat 0 Bayrağı Set)")

assert event_generated == True
assert (exti.pr & (1 << 0)) != 0

# WRITE-1-TO-CLEAR TESTİ:
# Eğer yazılımcı sıfır yazarsa bayrak TEMİZLENMEZ!
exti.clear_pending_flag(line=0, write_value=0x0000)
assert (exti.pr & (1 << 0)) != 0, "Sıfır yazmak bayrağı temizleyemez!"

# Doğru temizleme: İlgili bite 1 yazılır!
exti.clear_pending_flag(line=0, write_value=(1 << 0))
assert exti.pr == 0x0000, "1 yazıldığında PR bayrağı sıfırlanmalıdır!"
print("  [+] Write-1-to-Clear kuralı başarıyla doğrulandı: Bayrak temizlendi.")
print("[HÜCRE 8] EXTI donanım kontrolcüsü ve bayrak mekanizması başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 3 — Sabotaj ve Hata Enjeksiyonu: Bayrak Temizleme İhmali ve Sonsuz Döngü
"""

class FaultyInterruptSimulator:
    def __init__(self, exti_ctrl: ExtiHardwareController):
        self.exti = exti_ctrl
        self.isr_invocation_counter = 0

    def run_faulty_isr(self, clear_flag: bool):
        """
        Eğer ISR bayrağı temizlemeden çıkarsa, donanım kesme koşulunun
        hala aktif olduğunu düşünerek kesmeden çıktığı nanosaniyede tekrar ISR çağırır!
        """
        self.isr_invocation_counter += 1
        # Hatalı geliştirici bayrağı temizlemeyi unuttu!
        if clear_flag:
            self.exti.clear_pending_flag(line=0, write_value=(1 << 0))

print()
print("[*] SABOTAJ SENARYOSU 1: ISR İçinde PR Bayrağını Temizlemeyi Unutmak")
exti_test = ExtiHardwareController()
exti_test.configure_exti_line(line=0, port="PA", rising=True)
exti_test.trigger_pin_event(line=0, port="PA", edge="RISING")

simulator = FaultyInterruptSimulator(exti_test)

# Bayrak temizlenmediğinde döngü simülasyonu
lockup_detected = False
for step in range(100):
    if exti_test.pr & (1 << 0):
        simulator.run_faulty_isr(clear_flag=False)
        if simulator.isr_invocation_counter >= 50:
            lockup_detected = True
            break

print(f"  [!] Sonsuz Döngü / Lockup Algılandı: ISR tam {simulator.isr_invocation_counter} kez peş peşe çağrıldı!")
print(f"  [!] CPU Ana Göreve Dönemiyor (Thread Starvation)!")
assert lockup_detected == True

print()
print("[*] DÜZELTME: ISR İçinde Bayrak Usulüne Uygun Temizleniyor")
simulator.isr_invocation_counter = 0
simulator.run_faulty_isr(clear_flag=True)
print(f"  [+] Bayrak Temizlendi: PR = 0x{exti_test.pr:04X}, Toplam Çağrı = {simulator.isr_invocation_counter}")
assert exti_test.pr == 0x0000
assert simulator.isr_invocation_counter == 1

print()
print("[*] SABOTAJ SENARYOSU 2: ISR İçinde Bloklayıcı Gecikme (HAL_Delay) Felaketi")
def check_isr_timing_safety(delay_requested_ms: float, max_allowed_budget_us: float) -> bool:
    if (delay_requested_ms * 1000.0) > max_allowed_budget_us:
        raise TimeoutError(f"CRITICAL TIMING FAULT: ISR içinde {delay_requested_ms} ms gecikme kullanılamaz! Bütçe: {max_allowed_budget_us} us")
    return True

delay_fault_caught = False
try:
    # ISR içinde 10 ms bekleme yapılmaya çalışılıyor (Savunma standardı bütçesi: 10 us!)
    check_isr_timing_safety(delay_requested_ms=10.0, max_allowed_budget_us=10.0)
except TimeoutError as e:
    delay_fault_caught = True
    print(f"  [+] Savunma Başarılı: ISR Zamanlama İhlali Yakalandı! ({e})")

assert delay_fault_caught == True
print("[HÜCRE 10] Sabotaj ve kilitlenme analizleri başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 4 — Top-Half / Bottom-Half Ayrımı ve Kesme-Güvenli Lock-Free Dairesel Bellek
"""

class LockFreeIsrRingBuffer:
    """
    Tek Üretici (ISR - Top-Half) / Tek Tüketici (Main Task - Bottom-Half) Dairesel Bellek:
    - Kesme içinde kilit (mutex/lock) kullanılmaz!
    - Head sadece ISR tarafından yazılır.
    - Tail sadece Ana Görev tarafından yazılır.
    - Sıfır yarış durumu (Race Condition), atomik operasyon.
    """
    def __init__(self, capacity: int = 16):
        self.capacity = capacity
        self.buffer = [0] * capacity
        self.head = 0
        self.tail = 0
        self.dropped_events = 0

    def isr_push_top_half(self, data: int) -> bool:
        """Top-Half: 5 saat çevriminde veriyi kaydet ve çık!"""
        next_head = (self.head + 1) % self.capacity
        if next_head == self.tail:
            # Arabellek dolu! Veri düştü (Buffer Overflow)
            self.dropped_events += 1
            return False
        self.buffer[self.head] = data
        self.head = next_head
        return True

    def task_pop_bottom_half(self) -> Optional[int]:
        """Bottom-Half: Ana görev arka planda rahatça işler"""
        if self.head == self.tail:
            return None # Boş
        data = self.buffer[self.tail]
        self.tail = (self.tail + 1) % self.capacity
        return data

# Deney: Yüksek Hızlı Radar Sinyalleri Alınıyor
ring_buf = LockFreeIsrRingBuffer(capacity=8)

# Top-Half (ISR): 5 ardışık darbe telemetrisi geliyor
telemetry_data = [0xA1, 0xA2, 0xA3, 0xA4, 0xA5]
for d in telemetry_data:
    success = ring_buf.isr_push_top_half(d)
    assert success == True

print()
print("[*] Top-Half / Bottom-Half Ring Buffer Testi:")
print(f"  [+] ISR Top-Half Yazılan Bayt Sayısı: {len(telemetry_data)}")
print(f"  [+] Arabellek Durumu: Head={ring_buf.head}, Tail={ring_buf.tail}")

# Bottom-Half (Ana Döngü): Veriler sırayla okunuyor ve işleniyor
processed_data = []
while True:
    val = ring_buf.task_pop_bottom_half()
    if val is None:
        break
    processed_data.append(val)

print(f"  [+] Bottom-Half İşlenen Veriler     : {[hex(x) for x in processed_data]}")
assert processed_data == telemetry_data
assert ring_buf.dropped_events == 0
print("[HÜCRE 12] Lock-free ring buffer ve iki aşamalı kesme mimarisi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 5 — ROKETSAN Taktik Füze Lazer Arayıcı Başlık (Seeker) Kesme Mimarisi
"""

class MissileSeekerInterruptSystem:
    """
    ROKETSAN Lazer Arayıcı Başlık Aviyonik Modeli:
    - EXTI0 (Prio 0): Lazer Kod Tespiti (Hedef Vuruş Doğrulaması - En Yüksek Acil)
    - TIM1  (Prio 1): 2000 Hz Gimbal Açı Kontrolü (Kalman Filtresi)
    - UART1 (Prio 2): Yer İstasyonu Telemetri Akışı
    """
    def __init__(self):
        self.nvic = NvicInterruptEngine(prigroup=4)
        self.ring_buf = LockFreeIsrRingBuffer(capacity=16)
        
        # Kesmeler Kaydediliyor
        self.nvic.register_irq(16, preemption=0) # EXTI0 Lazer
        self.nvic.register_irq(17, preemption=1) # TIM1 Gimbal
        self.nvic.register_irq(18, preemption=2) # UART1 Telemetri

        self.laser_target_locked = False
        self.gimbal_cycles = 0

    def simulate_combat_scenario(self):
        # 1. Telemetri gönderimi başlar (Prio 2)
        self.nvic.trigger_interrupt(18)

        # 2. Gimbal açı kontrolü tetiklenir (Prio 1 -> Telemetriyi böler!)
        self.nvic.trigger_interrupt(17)
        self.gimbal_cycles += 1

        # 3. TAM O ANDA HEDEF LAZER DARBESİ YAKALANDI! (Prio 0 -> Gimbal'ı da böler!)
        self.nvic.trigger_interrupt(16)
        
        # Lazer ISR (Top-Half): Hızlıca darbe zaman damgasını kaydeder
        self.ring_buf.isr_push_top_half(0xDEAD)
        self.laser_target_locked = True

        # Kesmeler Hiyerarşik Olarak Kapanır
        self.nvic.finish_current_isr() # Lazer biter
        self.nvic.finish_current_isr() # Gimbal biter
        self.nvic.finish_current_isr() # Telemetri biter

# Taktik Simülasyon Koşturuluyor
seeker = MissileSeekerInterruptSystem()
seeker.simulate_combat_scenario()

print()
print("[*] ROKETSAN Arayıcı Başlık Muharebe Kesme Senaryosu:")
for trace in seeker.nvic.execution_trace:
    print(f"  {trace}")

assert seeker.laser_target_locked == True
assert seeker.gimbal_cycles == 1
assert seeker.ring_buf.task_pop_bottom_half() == 0xDEAD
print("[HÜCRE 14] Taktik lazer arayıcı başlık kesme senaryosu başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 6 — 4 Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_166_interrupt_ve_isr.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_166\gun_166_interrupt_ve_isr.png"

# Matplotlib Karanlık Tema Ayarları
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.0

fig = plt.figure(figsize=(18, 12), dpi=300, facecolor='#0F172A')
fig.suptitle("GÜN 166: STM32 Kesmeler (Interrupts), NVIC Mimarisi, Preemption ve ISR Tasarımı Panosu",
             fontsize=14, fontweight='bold', color='#38BDF8', y=0.98)

# -----------------------------------------------------------------------------
# PANEL 1: NVIC Preemption Hiyerarşisi ve Çok Katmanlı Yuvalanma (Nesting)
# -----------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1)
ax1.set_facecolor('#1E293B')
ax1.set_title("Panel 1: NVIC Donanımsal Kesme Yuvalanması (Preemption Nesting)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax1.axis('off')

# Katman 1: Main Thread
ax1.add_patch(patches.Rectangle((0.05, 0.10), 0.90, 0.16, facecolor='#064E3B', edgecolor='#10B981', lw=1.5))
ax1.text(0.50, 0.18, "ANA KULLANICI GÖREVİ (Thread Mode - Normal Yürütme)", ha='center', va='center', color='#A7F3D0', fontweight='bold', fontsize=8.5)

# Katman 2: USART ISR
ax1.add_patch(patches.Rectangle((0.15, 0.34), 0.75, 0.16, facecolor='#1E3A8A', edgecolor='#3B82F6', lw=1.5))
ax1.text(0.52, 0.42, "USART1 TELEMETRİ ISR (Preemption Prio 2 - Düşük)", ha='center', va='center', color='#93C5FD', fontweight='bold', fontsize=8.5)

# Katman 3: TIM1 Motor PID
ax1.add_patch(patches.Rectangle((0.30, 0.58), 0.55, 0.16, facecolor='#78350F', edgecolor='#F59E0B', lw=1.5))
ax1.text(0.57, 0.66, "TIM1 GİMBAL PID ISR (Preemption Prio 1 - Orta)", ha='center', va='center', color='#FDE68A', fontweight='bold', fontsize=8.5)

# Katman 4: EXTI0 Lazer Dedektör
ax1.add_patch(patches.Rectangle((0.48, 0.80), 0.32, 0.16, facecolor='#7F1D1D', edgecolor='#EF4444', lw=2))
ax1.text(0.64, 0.88, "EXTI0 LAZER ISR (Prio 0 - EN ACİL)", ha='center', va='center', color='#FCA5A5', fontweight='bold', fontsize=8.5)

# Olay Akış Okları
ax1.annotate("", xy=(0.15, 0.34), xytext=(0.15, 0.26), arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2))
ax1.annotate("", xy=(0.30, 0.58), xytext=(0.30, 0.50), arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2))
ax1.annotate("", xy=(0.48, 0.80), xytext=(0.48, 0.74), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2))

ax1.set_xlim(0.0, 1.0)
ax1.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 2: Klasik Kesme vs ARM Cortex-M Tail-Chaining & Late-Arrival
# -----------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2)
ax2.set_facecolor('#1E293B')
ax2.set_title("Panel 2: Tail-Chaining Sıfır Maliyetli Kesme Geçişi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax2.axis('off')

# Geleneksel İşlemci
ax2.text(0.05, 0.86, "1. GELENEKSEL İŞLEMCİ: Tam Unstack + Tam Stacking (24-32 Çevrim İsraf)", color='#EF4444', fontweight='bold', fontsize=8)
ax2.add_patch(patches.Rectangle((0.05, 0.70), 0.28, 0.12, facecolor='#059669', edgecolor='#FFFFFF', lw=1))
ax2.text(0.19, 0.76, "ISR 1 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

ax2.add_patch(patches.Rectangle((0.35, 0.70), 0.25, 0.12, facecolor='#EF4444', edgecolor='#FFFFFF', lw=1))
ax2.text(0.47, 0.76, "POP + PUSH\n(24 Çevrim İsraf!)", ha='center', va='center', color='#FFFFFF', fontsize=7)

ax2.add_patch(patches.Rectangle((0.62, 0.70), 0.28, 0.12, facecolor='#0284C7', edgecolor='#FFFFFF', lw=1))
ax2.text(0.76, 0.76, "ISR 2 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

# ARM Cortex-M Tail-Chaining
ax2.text(0.05, 0.48, "2. ARM CORTEX-M: Tail-Chaining ile Sıfır Bellek Erişimi (Sadece 6 Çevrim)", color='#10B981', fontweight='bold', fontsize=8)
ax2.add_patch(patches.Rectangle((0.05, 0.32), 0.38, 0.12, facecolor='#059669', edgecolor='#FFFFFF', lw=1))
ax2.text(0.24, 0.38, "ISR 1 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

ax2.add_patch(patches.Rectangle((0.45, 0.32), 0.10, 0.12, facecolor='#F59E0B', edgecolor='#FFFFFF', lw=1))
ax2.text(0.50, 0.38, "TC\n(6ç)", ha='center', va='center', color='#FFFFFF', fontsize=7.5, fontweight='bold')

ax2.add_patch(patches.Rectangle((0.57, 0.32), 0.38, 0.12, facecolor='#0284C7', edgecolor='#FFFFFF', lw=1))
ax2.text(0.76, 0.38, "ISR 2 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

# Açıklama
ax2.text(0.50, 0.14, "* Yazmaçlar yığından geri yüklenmez; doğrudan sıradaki kesme vektör adresine sıçranır.",
         ha='center', va='center', color='#CBD5E1', fontsize=8, fontstyle='italic')

ax2.set_xlim(0.0, 1.0)
ax2.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 3: Top-Half vs Bottom-Half Mimarisi ve Ring Buffer
# -----------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3)
ax3.set_facecolor('#1E293B')
ax3.set_title("Panel 3: İki Aşamalı Kesme Mimarisi (Top-Half vs Bottom-Half)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax3.axis('off')

# Top Half Kutusu
ax3.add_patch(patches.FancyBboxPatch((0.05, 0.45), 0.42, 0.45, boxstyle="round,pad=0.02", facecolor='#7F1D1D', edgecolor='#EF4444', lw=2))
ax3.text(0.26, 0.82, "TOP-HALF (ISR)", ha='center', va='center', color='#F87171', fontweight='bold', fontsize=11)
ax3.text(0.26, 0.73, "Süre: < 2 us (Ultra Hızlı)", ha='center', va='center', color='#FDE68A', fontsize=8.5)
ax3.text(0.26, 0.64, "1. Donanım Bayrağını Sil (PR=1)\n2. Veriyi Donanımdan Oku\n3. Ring Buffer'a İt (Push)\n4. Derhal Çık!", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

# Bottom Half Kutusu
ax3.add_patch(patches.FancyBboxPatch((0.53, 0.45), 0.42, 0.45, boxstyle="round,pad=0.02", facecolor='#064E3B', edgecolor='#10B981', lw=2))
ax3.text(0.74, 0.82, "BOTTOM-HALF (Task)", ha='center', va='center', color='#34D399', fontweight='bold', fontsize=11)
ax3.text(0.74, 0.73, "Süre: Esnek (Thread Modu)", ha='center', va='center', color='#FDE68A', fontsize=8.5)
ax3.text(0.74, 0.64, "1. Ring Buffer'dan Veri Çek\n2. Ağır Matematik / Kalman\n3. Paket Çözümleme / CRC\n4. Kesmeleri Asla Engellemez!", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

# Ortadaki Köprü: Ring Buffer
ax3.add_patch(patches.Rectangle((0.20, 0.12), 0.60, 0.22, facecolor='#0F172A', edgecolor='#38BDF8', lw=1.5))
ax3.text(0.50, 0.27, "LOCK-FREE CIRCULAR RING BUFFER", ha='center', va='center', color='#38BDF8', fontweight='bold', fontsize=9)
ax3.text(0.50, 0.18, "ISR (Top-Half) -> [Veri Yaz] -> BUFFER -> [Veri Oku] -> Task (Bottom-Half)", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

ax3.set_xlim(0.0, 1.0)
ax3.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 4: EXTI Write-1-to-Clear ve Starvation Lockup Analizi
# -----------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4)
ax4.set_facecolor('#1E293B')
ax4.set_title("Panel 4: EXTI->PR Write-1-to-Clear ve Kilitlenme (Starvation) Riski", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

t_axis = np.linspace(0, 10, 500)
# Normal Senaryo: Bayrak temizlenir, tek çağrı
# Kilitlenme Senaryosu: Bayrak temizlenmez, sonsuz tetikleme
normal_exec = [1.0 if (1.0 <= t <= 1.2) else 0.0 for t in t_axis]
lockup_exec = [1.0 if t >= 4.0 else 0.0 for t in t_axis]

ax4.plot(t_axis, [v + 1.4 for v in normal_exec], color='#34D399', lw=2.2, label="Doğru Kullanım: PR=1 ile Silindi (Tek Temiz ISR)")
ax4.plot(t_axis, lockup_exec, color='#EF4444', lw=2.2, label="Sabotaj / Hata: Bayrak Silinmedi (Sonsuz ISR Kilitlenmesi / Starvation)")

ax4.axvline(4.0, color='#F59E0B', linestyle='--', lw=1.5)
ax4.text(4.2, 0.5, "Bayrak Temizlenmedi!\nİşlemci sonsuz kesme döngüsüne kilitlendi!", color='#FCA5A5', fontsize=8, fontweight='bold')

ax4.set_xlabel("Zaman (ms)", color='#94A3B8')
ax4.set_ylabel("CPU Yürütme Durumu", color='#94A3B8')
ax4.set_yticks([0, 1, 1.4, 2.4])
ax4.set_yticklabels(["Boş", "ISR (Kilitli)", "Thread", "ISR (Temiz)"])
ax4.set_ylim(-0.2, 2.8)
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
print("[*] GÜN 166 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert len(nvic.active_stack) == 0
assert event_generated == True
assert lockup_detected == True
assert delay_fault_caught == True
assert processed_data == telemetry_data
assert seeker.laser_target_locked == True

print()
print("[PASS] Gün 166: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")

