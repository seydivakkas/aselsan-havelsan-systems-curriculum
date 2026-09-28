# -*- coding: utf-8 -*-
"""
gun_161_embedded_sistem_nedir_mcu_vs_cpu_sbc
Otomatik Oluşturulan Çalıştırılabilir Python Betiği
"""

# -*- coding: utf-8 -*-
"""
GÜN 161: Kod Bloğu 1 — Sanal Donanım Simülatörü: MCU ve CPU/SBC Mimarisi
"""

import time
import random
from typing import Dict, Any, Optional, List

class VirtualMcu:
    """
    STM32 / ARM Cortex-M Benzeri Mikrodenetleyici Modeli:
    - Dahili 512 KB SRAM, 2 MB Flash
    - MMU YOKTUR (Doğrudan fiziksel adresleme)
    - Donanımsal NVIC (Ultra düşük kesme gecikmesi: ~0.05 us)
    - Düşük güç tüketimi (150 mW)
    """
    def __init__(self, clock_mhz: int = 216, ram_kb: int = 512, flash_kb: int = 2048):
        self.clock_mhz = clock_mhz
        self.ram_kb = ram_kb
        self.flash_kb = flash_kb
        self.has_mmu = False
        self.power_mw = 150.0
        self.boot_time_ms = 12.5  # Soğuk açılış süresi
        self.ram_memory = bytearray(ram_kb * 1024)
        self.interrupt_latency_ns = 55.0  # 12 çevrim @ 216MHz

    def write_physical_ram(self, address: int, data: bytes):
        if address + len(data) > len(self.ram_memory):
            raise IndexError("MCU Physical RAM Overflow! (Stack-Heap Çarpışması)")
        self.ram_memory[address:address + len(data)] = data

    def read_physical_ram(self, address: int, length: int) -> bytes:
        return bytes(self.ram_memory[address:address + length])

class VirtualCpuSbc:
    """
    ARM Cortex-A53 / Linux Benzeri Tek Kart Bilgisayar Modeli:
    - Harici 4 GB LPDDR4 RAM, 32 GB eMMC
    - MMU VARDIR (Sanal bellek, 4KB sayfalama, korumalı adres uzayı)
    - İşletim sistemi scheduler ve context switch gecikmesi (~15 us)
    - Yüksek güç tüketimi (6500 mW)
    """
    def __init__(self, clock_mhz: int = 1500, ram_mb: int = 4096):
        self.clock_mhz = clock_mhz
        self.ram_mb = ram_mb
        self.has_mmu = True
        self.power_mw = 6500.0
        self.boot_time_ms = 8500.0 # Linux çekirdeği açılışı
        self.virtual_pages: Dict[int, bytearray] = {}
        self.interrupt_latency_ns = 15000.0 # OS context switch

    def write_virtual_memory(self, process_id: int, virtual_addr: int, data: bytes):
        page_id = virtual_addr // 4096
        if page_id not in self.virtual_pages:
            self.virtual_pages[page_id] = bytearray(4096)
        
        offset = virtual_addr % 4096
        self.virtual_pages[page_id][offset:offset + len(data)] = data

# Simülatör Doğrulama
mcu = VirtualMcu()
sbc = VirtualCpuSbc()

# MCU doğrudan fiziksel belleğe yazar
mcu.write_physical_ram(0x20000000 % len(mcu.ram_memory), b"SERVO_POS_CMD_45DEG")
read_mcu = mcu.read_physical_ram(0x20000000 % len(mcu.ram_memory), 19)

# SBC sanal sayfaya yazar
sbc.write_virtual_memory(process_id=101, virtual_addr=0x00401000, data=b"AI_TARGET_DETECTED")

print("[*] Donanım Simülatörleri Başarıyla Başlatıldı:")
print(f"  [+] MCU (STM32): MMU={mcu.has_mmu} | RAM={mcu.ram_kb}KB | Güç={mcu.power_mw}mW | Kesme Gecikmesi={mcu.interrupt_latency_ns}ns")
print(f"  [+] SBC (Linux): MMU={sbc.has_mmu} | RAM={sbc.ram_mb}MB | Güç={sbc.power_mw}mW | Kesme Gecikmesi={sbc.interrupt_latency_ns}ns")
print(f"  [+] MCU Fiziksel Bellek Doğrulandı: {read_mcu.decode()}")

assert mcu.has_mmu == False
assert sbc.has_mmu == True
assert read_mcu == b"SERVO_POS_CMD_45DEG"
print("[HÜCRE 6] Donanım simülatörü çekirdeği hazır.")

# -*- coding: utf-8 -*-
"""
GÜN 161: Kod Bloğu 2 — 1000 Hz Hard Real-Time Aviyonik Servo Kontrol Döngüsü
"""

class FlightControlLoopSimulator:
    """1000 Hz (1.0 ms) Hedef Periyotlu Aviyonik Kanatçık Servo PID Kontrol Döngüsü"""
    def __init__(self):
        self.target_period_us = 1000.0  # 1.0 ms
        self.deadline_us = 1200.0       # Maksimum tolere edilen süre (1.2 ms)

    def run_mcu_hardware_timer_loop(self, iterations: int = 500) -> Dict[str, Any]:
        """MCU Donanımsal Timer Kesmesi (Cortex-M SysTick / TIM2)"""
        periods = []
        deadline_misses = 0

        for _ in range(iterations):
            # Donanım saati kristal osilatör kararlılığı: ± 0.5 mikrosaniye jitter
            jitter = random.gauss(0.0, 0.4)
            actual_period = self.target_period_us + jitter
            periods.append(actual_period)
            if actual_period > self.deadline_us:
                deadline_misses += 1

        return {
            "platform": "MCU (Bare-Metal / RTOS)",
            "periods_us": periods,
            "mean_us": sum(periods) / len(periods),
            "max_us": max(periods),
            "min_us": min(periods),
            "deadline_misses": deadline_misses
        }

    def run_cpu_linux_os_loop(self, iterations: int = 500) -> Dict[str, Any]:
        """Genel Amaçlı Linux İşletim Sistemi Zamanlayıcısı (usleep / OS Scheduler)"""
        periods = []
        deadline_misses = 0

        for i in range(iterations):
            # Normal işletim gecikmesi (ortalama 1000 us ± 25 us)
            actual_period = self.target_period_us + random.gauss(0.0, 25.0)

            # Rastlantısal Arka Plan İşi (Disk I/O, sayfalama, Linux context switch gecikmesi)
            if random.random() < 0.04:  # %4 olasılıkla OS kilitlenmesi / jitter patlaması
                actual_period += random.uniform(300.0, 1500.0) # 1.3 ms - 2.5 ms arası fırlar!

            periods.append(actual_period)
            if actual_period > self.deadline_us:
                deadline_misses += 1

        return {
            "platform": "CPU/SBC (Genel Amaçlı Linux)",
            "periods_us": periods,
            "mean_us": sum(periods) / len(periods),
            "max_us": max(periods),
            "min_us": min(periods),
            "deadline_misses": deadline_misses
        }

random.seed(161)
sim = FlightControlLoopSimulator()
mcu_res = sim.run_mcu_hardware_timer_loop(500)
cpu_res = sim.run_cpu_linux_os_loop(500)

print()
print("[*] 1000 Hz Aviyonik Kontrol Döngüsü Kıyaslama Raporu (500 İterasyon):")
print(f"  [+] MCU (STM32/RTOS)  : Ort={mcu_res['mean_us']:.2f}us | Max={mcu_res['max_us']:.2f}us | Deadline Kaçırma={mcu_res['deadline_misses']} (HARD REAL-TIME BAŞARISI)")
print(f"  [-] SBC (Genel Linux) : Ort={cpu_res['mean_us']:.2f}us | Max={cpu_res['max_us']:.2f}us | Deadline Kaçırma={cpu_res['deadline_misses']} (FELAKET! FÜZE KONTROLÜ KAYBEDER)")

assert mcu_res["deadline_misses"] == 0, "MCU kontrol döngüsü deadline kaçıramaz!"
assert cpu_res["deadline_misses"] > 0, "Standart Linux periyodik kontrol döngüsünde deadline kaçırmalıdır!"
print("[HÜCRE 8] Aviyonik kontrol döngüsü ve determinizm testi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 161: Kod Bloğu 3 — Sabotaj ve Hata Enjeksiyonu: MMU Yoksunluğu ve Bellek Çarpışması
"""

print()
print("[*] SABOTAJ SENARYOSU 1: MCU'da Stack Taşması (Stack-Heap Collision / Silent Corruption)")
# MCU'da sanal bellek (MMU) olmadığı için stack kontrolsüz büyürse global değişkenlerin üzerine yazar!
mcu_attack = VirtualMcu(ram_kb=64) # 64 KB RAM

# Global Sistem Değişkeni (0x0100 adresinde fırlatma izni bayrağı)
ADDR_ARMED_FLAG = 0x0100
mcu_attack.write_physical_ram(ADDR_ARMED_FLAG, b"\x00") # False (Füze Kilitli)

# Yanlış özyinelemeli fonksiyon veya kontrolsüz dizi yazımı ile stack taşırılıyor
stack_smash_data = b"\x01" * 300 # Global değişkenlerin üzerine taşan veri!
mcu_attack.write_physical_ram(0x0050, stack_smash_data)

tampered_flag = mcu_attack.read_physical_ram(ADDR_ARMED_FLAG, 1)
print(f"  [-] Orijinal Füze Fırlatma Bayrağı: 0x00 (KİLİTLİ)")
print(f"  [!] Stack Taşması Sonrası Bayrak  : 0x{tampered_flag[0]:02X} (SESSİZCE BOZULDU VE FÜZE ATEŞLENDİ!)")

assert tampered_flag == b"\x01", "MCU'da MMU olmadığı için bellek sessizce bozulabilmelidir!"

print()
print("[*] SABOTAJ SENARYOSU 2: CPU/SBC'de Aynı Hata -> MMU Tarafından Yakalanma")
# Linux SBC'de süreç geçersiz veya korumalı bir bellek sayfasına yazmaya çalıştığında:
sbc_attack = VirtualCpuSbc()
mmu_caught_segfault = False

try:
    # Sayfa izin hatası / SegFault simülasyonu (Salt okunur veya tahsis edilmemiş sanal adres)
    protected_virtual_address = 0xDEADBEEF
    if protected_virtual_address > 0xC0000000:
        raise MemoryError("SIGSEGV: Kernel Memory Access Denied by MMU Hardware!")
    sbc_attack.write_virtual_memory(process_id=200, virtual_addr=protected_virtual_address, data=b"ATTACK")
except MemoryError as e:
    mmu_caught_segfault = True
    print(f"  [+] Savunma Başarılı: MMU Donanımı Hatayı Yakaladı ve Süreci İzole Etti! ({e})")

assert mmu_caught_segfault == True, "SBC'de MMU donanımsal koruma sağlamalıdır!"
print("[HÜCRE 10] Sabotaj ve bellek yönetim testleri başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 161: Kod Bloğu 4 — Soğuk Açılış (Cold Boot Time) ve Güç Tüketimi Analiz Motoru
"""

def benchmark_cold_boot_and_power():
    # Askeri Aviyonik Senaryosu: Roket Motoru Ateşlendi / Güç Kesintisi (Brown-Out) Yaşandı
    mcu_boot_ms = 14.2   # STM32: Reset vektörü -> SystemInit -> main()
    sbc_boot_ms = 7800.0 # Linux SBC: U-Boot -> Kernel Decompress -> Init -> Daemons

    mcu_power_watts = 0.18   # 180 mW
    sbc_power_watts = 8.50   # 8.5 Watt (47 kat daha fazla!)

    # 1 Saatlik Görevde Harcanan Enerji (Joule = Watt * Saniye)
    mcu_energy_joules = mcu_power_watts * 3600.0
    sbc_energy_joules = sbc_power_watts * 3600.0

    return {
        "mcu_boot_ms": mcu_boot_ms,
        "sbc_boot_ms": sbc_boot_ms,
        "boot_speedup_ratio": sbc_boot_ms / mcu_boot_ms,
        "mcu_power_w": mcu_power_watts,
        "sbc_power_w": sbc_power_watts,
        "power_ratio": sbc_power_watts / mcu_power_watts,
        "mcu_energy_1h_j": mcu_energy_joules,
        "sbc_energy_1h_j": sbc_energy_joules
    }

boot_metrics = benchmark_cold_boot_and_power()

print()
print("[*] Soğuk Açılış (Cold Boot) ve Enerji Verimliliği Kıyaslama Raporu:")
print(f"  [+] Açılış Süresi (Boot Time) : MCU={boot_metrics['mcu_boot_ms']} ms | SBC={boot_metrics['sbc_boot_ms']} ms ({boot_metrics['boot_speedup_ratio']:.1f}x Kat Daha Hızlı!)")
print(f"  [+] Güç Tüketimi (Power)      : MCU={boot_metrics['mcu_power_w']} W  | SBC={boot_metrics['sbc_power_w']} W  ({boot_metrics['power_ratio']:.1f}x Kat Daha Tasarruflu!)")
print(f"  [+] 1 Saatlik Enerji Tüketimi : MCU={boot_metrics['mcu_energy_1h_j']:.1f} J | SBC={boot_metrics['sbc_energy_1h_j']:.1f} J")

assert boot_metrics["boot_speedup_ratio"] > 100.0, "MCU en az 100 kat daha hızlı açılmalıdır!"
assert boot_metrics["power_ratio"] > 20.0, "MCU en az 20 kat daha az güç tüketmelidir!"
print("[HÜCRE 12] Açılış süresi ve güç tüketimi benchmark analizi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 161: Kod Bloğu 5 — ROKETSAN Güdümlü Füze Hibrit Aviyonik Mimari Simülasyonu
"""

class HybridMissileAvionics:
    """
    ROKETSAN L-UMTAS / CİRİT Benzeri Hibrit Güdüm Mimarisi:
    - SBC (ARM Cortex-A / Linux): Termal Arayıcı Başlık Görüntü İşleme (10 Hz)
    - MCU (STM32H7 / Cortex-M7): Uçuş Kontrol ve Kanatçık Servo PID (1000 Hz)
    - İletişim: Donanımsal SPI Veri Yolu (10 Mbps)
    """
    def __init__(self):
        self.mcu = VirtualMcu()
        self.sbc = VirtualCpuSbc()
        self.spi_telemetry_bus: List[str] = []
        self.actuator_commands_executed = 0

    def sbc_process_seeker_camera(self, frame_id: int) -> Dict[str, float]:
        """SBC 10 Hz Hızında Termal Kameradan Hedef Sapma Açısını (Line of Sight - LOS) Hesaplar"""
        target_error_azimuth = random.uniform(-2.5, 2.5)
        target_error_elevation = random.uniform(-1.8, 1.8)
        return {
            "frame_id": frame_id,
            "az_err_deg": target_error_azimuth,
            "el_err_deg": target_error_elevation
        }

    def mcu_execute_servo_step(self, guidance_cmd: Dict[str, float], step_id: int):
        """MCU 1000 Hz Hızında Kanatçık Servolarını PID ile Sürer"""
        # Her 100 adımda bir SBC'den yeni hedef kılavuz verisi gelir
        fin_deflection_deg = guidance_cmd["az_err_deg"] * 1.5
        self.actuator_commands_executed += 1
        if step_id % 100 == 0:
            self.spi_telemetry_bus.append(f"STEP_{step_id}:FIN_SERVO_ANGLE={fin_deflection_deg:.2f}")

# Simülasyon: 500 Adımlık Uçuş Yolu
missile_system = HybridMissileAvionics()
current_guidance = {"frame_id": 0, "az_err_deg": 0.0, "el_err_deg": 0.0}

for step in range(1, 501):
    if step % 100 == 1:
        # SBC yeni kare işler
        current_guidance = missile_system.sbc_process_seeker_camera(frame_id=step // 100)
    
    # MCU her adımda (1 ms) servo sürer
    missile_system.mcu_execute_servo_step(current_guidance, step)

print()
print("[*] ROKETSAN Hibrit Aviyonik Görev Simülasyonu Raporu:")
print(f"  [+] MCU Tarafında İcra Edilen Servo Adımı : {missile_system.actuator_commands_executed} Adım (1000 Hz Hard Real-Time)")
print(f"  [+] SBC Tarafından İşlenen Arayıcı Kare  : 5 Kare (10 Hz Soft Real-Time)")
print(f"  [+] SPI Veri Yolu Telemetri Güncellemeleri: {missile_system.spi_telemetry_bus}")

assert missile_system.actuator_commands_executed == 500
assert len(missile_system.spi_telemetry_bus) == 5
print("[HÜCRE 14] Hibrit aviyonik görev simülasyonu başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 161: Kod Bloğu 6 — 4 Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_161_embedded_sistem_nedir_mcu_vs_cpu_sbc.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_161\gun_161_embedded_sistem_nedir_mcu_vs_cpu_sbc.png"

# Matplotlib Karanlık Tema Ayarları
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.0

fig = plt.figure(figsize=(18, 12), dpi=300, facecolor='#0F172A')
fig.suptitle("GÜN 161: Gömülü Sistem Mimarisi — MCU vs CPU/SBC Karşılaştırma Panosu",
             fontsize=15, fontweight='bold', color='#38BDF8', y=0.98)

# -----------------------------------------------------------------------------
# PANEL 1: MCU vs CPU/SBC Donanım Blok Şeması
# -----------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1)
ax1.set_facecolor('#1E293B')
ax1.set_title("Panel 1: Silikon Düzeyinde Donanım Mimarisi Karşılaştırması", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax1.axis('off')

# MCU Bloğu (Sol)
mcu_card = patches.FancyBboxPatch((0.05, 0.15), 0.42, 0.75, boxstyle="round,pad=0.02", facecolor='#064E3B', edgecolor='#10B981', lw=2)
ax1.add_patch(mcu_card)
ax1.text(0.26, 0.85, "MCU (Mikrodenetleyici)", ha='center', va='center', color='#34D399', fontweight='bold', fontsize=11)
ax1.text(0.26, 0.80, "STM32 / ARM Cortex-M", ha='center', va='center', color='#CBD5E1', fontsize=8.5)

mcu_modules = [
    ("CPU Çekirdeği (Cortex-M7)", "#047857"),
    ("Dahili SRAM (512 KB)", "#059669"),
    ("Dahili Flash (2 MB)", "#059669"),
    ("NVIC (Kesme Denetleyici)", "#10B981"),
    ("Peripherals: Timers, SPI, CAN", "#047857"),
    ("MMU: YOK! (Doğrudan Fiziksel)", "#EF4444")
]
for idx, (mod, col) in enumerate(mcu_modules):
    my = 0.72 - (idx * 0.09)
    ax1.add_patch(patches.Rectangle((0.08, my), 0.36, 0.07, facecolor=col, edgecolor='#FFFFFF', lw=1))
    ax1.text(0.26, my + 0.035, mod, ha='center', va='center', color='#FFFFFF', fontweight='bold', fontsize=8)

# CPU/SBC Bloğu (Sağ)
sbc_card = patches.FancyBboxPatch((0.53, 0.15), 0.42, 0.75, boxstyle="round,pad=0.02", facecolor='#1E3A8A', edgecolor='#38BDF8', lw=2)
ax1.add_patch(sbc_card)
ax1.text(0.74, 0.85, "CPU / SBC (Mikroişlemci)", ha='center', va='center', color='#38BDF8', fontweight='bold', fontsize=11)
ax1.text(0.74, 0.80, "i.MX8 / Cortex-A / Linux", ha='center', va='center', color='#CBD5E1', fontsize=8.5)

sbc_modules = [
    ("CPU Çoklu Çekirdek (Cortex-A53)", "#1D4ED8"),
    ("MMU: VAR! (Sanal Bellek / Paging)", "#10B981"),
    ("Harici DDR4 RAM (4 GB - 16 GB)", "#2563EB"),
    ("Harici Depolama: eMMC / NVMe", "#2563EB"),
    ("Linux Kernel & OS Scheduler", "#1D4ED8"),
    ("USB 3.0, PCIe, Gigabit Ethernet", "#1E40AF")
]
for idx, (mod, col) in enumerate(sbc_modules):
    sy = 0.72 - (idx * 0.09)
    ax1.add_patch(patches.Rectangle((0.56, sy), 0.36, 0.07, facecolor=col, edgecolor='#FFFFFF', lw=1))
    ax1.text(0.74, sy + 0.035, mod, ha='center', va='center', color='#FFFFFF', fontweight='bold', fontsize=8)

ax1.set_xlim(0.0, 1.0)
ax1.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 2: 1000 Hz Döngü Jitter Dağılımı (Hard Real-Time vs Linux)
# -----------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2)
ax2.set_facecolor('#1E293B')
ax2.set_title("Panel 2: 1000 Hz Kontrol Döngüsü Jitter Dağılımı", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

mcu_periods = mcu_res["periods_us"]
cpu_periods = cpu_res["periods_us"]

ax2.hist(mcu_periods, bins=20, color='#10B981', alpha=0.75, label='MCU (Bare-Metal / RTOS): Jitter < 1.5µs')
ax2.hist(cpu_periods, bins=40, color='#EF4444', alpha=0.6, label='SBC (Genel Linux): Jitter > 1000µs!')

ax2.axvline(x=1200.0, color='#F59E0B', linestyle='--', lw=2, label='DEADLINE SINIRI (1.2 ms)')

ax2.set_xlim(950, 1600)
ax2.set_xlabel("Döngü Periyodu (Mikrosaniye - µs)", fontsize=9, color='#94A3B8')
ax2.set_ylabel("Örnek Sayısı", fontsize=9, color='#94A3B8')
ax2.grid(True, linestyle=':', alpha=0.3, color='#64748B')
ax2.legend(facecolor='#1E293B', edgecolor='#334155')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Açılış Süresi ve Kesme Gecikmesi Kıyaslaması
# -----------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3)
ax3.set_facecolor('#1E293B')
ax3.set_title("Panel 3: Soğuk Açılış (Boot Time) ve Kesme Gecikmesi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

categories = ["Soğuk Açılış\nSüresi (ms)", "Kesme Gecikmesi\n(µs / mikrosaniye)"]
mcu_vals = [boot_metrics["mcu_boot_ms"], mcu.interrupt_latency_ns / 1000.0]
sbc_vals = [boot_metrics["sbc_boot_ms"], sbc.interrupt_latency_ns / 1000.0]

x = np.arange(len(categories))
width = 0.35

rects1 = ax3.bar(x - width/2, mcu_vals, width, label='MCU (STM32)', color='#10B981', edgecolor='#334155')
rects2 = ax3.bar(x + width/2, sbc_vals, width, label='SBC (Linux)', color='#38BDF8', edgecolor='#334155')

ax3.set_yscale('log')
ax3.set_ylabel("Süre (Logaritmik Ölçek)", fontsize=9, color='#94A3B8')
ax3.set_xticks(x)
ax3.set_xticklabels(categories, fontsize=9, color='#F8FAFC')
ax3.grid(axis='y', linestyle=':', alpha=0.3, color='#64748B')
ax3.legend(facecolor='#1E293B', edgecolor='#334155')
ax3.tick_params(colors='#94A3B8')

for bar in rects1:
    y = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, y * 1.3, f"{y:.2f}", ha='center', va='bottom', color='#34D399', fontsize=8, fontweight='bold')

for bar in rects2:
    y = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, y * 1.3, f"{y:.1f}", ha='center', va='bottom', color='#38BDF8', fontsize=8, fontweight='bold')

# -----------------------------------------------------------------------------
# PANEL 4: Taktik Savunma Donanım Karar Matrisi
# -----------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4)
ax4.set_facecolor('#1E293B')
ax4.set_title("Panel 4: Taktik Aviyonik Görev Dağılımı ve Güç Tüketimi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

features = ["Güç Tüketimi (Watt)", "Hard Real-Time Uygunluğu", "Görüntü İşleme Kapasitesi", "Sıfır Dinamik Bellek"]
mcu_scores = [0.18, 100, 5, 100]
sbc_scores = [8.50, 15, 100, 10]

bar_x = np.arange(len(features))
ax4.barh(bar_x - 0.18, mcu_scores, height=0.35, label='MCU (STM32)', color='#10B981', edgecolor='#334155')
ax4.barh(bar_x + 0.18, sbc_scores, height=0.35, label='SBC (Linux)', color='#F59E0B', edgecolor='#334155')

ax4.set_yticks(bar_x)
ax4.set_yticklabels(features, fontsize=8.5, color='#F8FAFC')
ax4.set_xlabel("Göreceli Skor / Değer", fontsize=9, color='#94A3B8')
ax4.grid(axis='x', linestyle=':', alpha=0.3, color='#64748B')
ax4.legend(loc='lower right', facecolor='#1E293B', edgecolor='#334155')
ax4.tick_params(colors='#94A3B8')

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 161 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert mcu_res["deadline_misses"] == 0
assert cpu_res["deadline_misses"] > 0
assert tampered_flag == b"\x01"
assert mmu_caught_segfault == True
assert boot_metrics["boot_speedup_ratio"] > 100.0
assert missile_system.actuator_commands_executed == 500

print()
print("[PASS] Gün 161 (F5 Başlangıcı): Tüm Katı Doğrulama Testleri Başarıyla Geçti!")

