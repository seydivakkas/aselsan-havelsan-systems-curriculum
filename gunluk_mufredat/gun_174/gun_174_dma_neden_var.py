

# ==============================================================================# -*- coding: utf-8 -*-
"""
GÜN 174: Kod Bloğu 1 — Polling vs Interrupt vs DMA Çevrim Maliyeti Simülasyonu
Farklı Veri Hızlarında CPU Tüketimi, Çevrim Harcaması ve İşlemci Yükü Karşılaştırması
"""

from typing import Dict, List

class CpuDataTransferProfiler:
    """Veri İletim Yöntemlerinin CPU Yükü ve Çevrim Maliyet Analizörü"""
    def __init__(self, mcu_clock_hz: int = 168_000_000): # STM32F407: 168 MHz
        self.clock_hz = mcu_clock_hz
        
        # ARM Cortex-M4 Donanımsal Zaman Parametreleri (Çevrim Cinsinden)
        self.isr_stacking_cycles = 12   # Donanım r0-r3, r12, lr, pc, xpsr stack eder
        self.isr_execution_cycles = 14  # Baytı DR'den oku, diziye yaz, indisi artır
        self.isr_unstacking_cycles = 12 # Kesmeden çıkış (bx lr / exc_return)
        self.total_isr_per_byte = self.isr_stacking_cycles + self.isr_execution_cycles + self.isr_unstacking_cycles

    def profile_transfer(self, bytes_per_sec: int, buffer_size: int = 1024) -> Dict[str, any]:
        """Verilen veri debisinde Polling, Interrupt ve DMA CPU tüketimini hesaplar"""
        
        # 1. Polling: CPU veriyi beklerken %100 kilitlidir
        polling_cpu_pct = 100.0
        
        # 2. Interrupt (Her bayt için ayrı ISR):
        cycles_for_interrupt = bytes_per_sec * self.total_isr_per_byte
        interrupt_cpu_pct = min(100.0, (cycles_for_interrupt / self.clock_hz) * 100.0)
        
        # 3. DMA (Sadece tampon dolduğunda 1 adet ISR):
        num_buffers_per_sec = bytes_per_sec / buffer_size
        dma_irq_cycles = num_buffers_per_sec * self.total_isr_per_byte
        dma_cpu_pct = (dma_irq_cycles / self.clock_hz) * 100.0
        
        return {
            "bytes_per_sec": bytes_per_sec,
            "polling_cpu_pct": polling_cpu_pct,
            "interrupt_cpu_pct": round(interrupt_cpu_pct, 3),
            "dma_cpu_pct": round(dma_cpu_pct, 5),
            "dma_efficiency_factor": round(interrupt_cpu_pct / max(dma_cpu_pct, 1e-9), 1)
        }

# Simülasyon: Düşük Hızdan (9600 baud) Taktik Radar Hızına (2 MB/s)
profiler = CpuDataTransferProfiler(mcu_clock_hz=168_000_000)

test_rates = [
    1_152,        # 9600 baud UART (~1 KB/s)
    11_520,       # 115200 baud UART (~11.5 KB/s)
    100_000,      # Orta Hız CAN/Sensör (~100 KB/s)
    500_000,      # Hızlı SPI Sensörü (~500 KB/s)
    1_000_000,    # Yüksek Hızlı ADC (~1 MB/s)
    2_000_000     # Taktik Radar IQ Akışı (~2 MB/s)
]

print(f"{'Hız (Bayt/s)':<14} | {'Polling CPU':<12} | {'Interrupt CPU':<14} | {'DMA CPU':<12} | {'DMA Kazancı':<10}")
print("-" * 72)

results = []
for rate in test_rates:
    res = profiler.profile_transfer(rate, buffer_size=1024)
    results.append(res)
    print(f"{res['bytes_per_sec']:<14,d} | %{res['polling_cpu_pct']:<11.1f} | %{res['interrupt_cpu_pct']:<13.3f} | %{res['dma_cpu_pct']:<11.5f} | {res['dma_efficiency_factor']:<10.0f}x")

# Doğrulama Testleri
assert results[-1]["interrupt_cpu_pct"] > 40.0, "2 MB/s'de kesme CPU'nun en az %40'ını yemelidir!"
assert results[-1]["dma_cpu_pct"] < 0.1, "DMA CPU yükü %0.1'in altında kalmalıdır!"
print("\n[HÜCRE 6] Polling vs Interrupt vs DMA çevrim tüketim modeli başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 174: Kod Bloğu 2 — ISR Context Switch Yükü ve CPU Thrashing Simülasyonu
Kesme Boğulması Eşiği, Overrun Hata Üretimi ve Ana Döngü Donma Analizi
"""

from typing import Dict, List

class InterruptThrashingSimulator:
    """Yüksek Hızlı Veri Akışında Kesme Boğulması ve Overrun Simülatörü"""
    def __init__(self, mcu_clock_hz: int = 168_000_000):
        self.clock_hz = mcu_clock_hz
        self.isr_cycles = 38 # Stacking (12) + Read & Store (14) + Unstacking (12)
        self.isr_duration_sec = self.isr_cycles / self.clock_hz

    def evaluate_system_stability(self, byte_rate: int) -> Dict[str, any]:
        inter_arrival_time = 1.0 / byte_rate
        cpu_load_ratio = self.isr_duration_sec / inter_arrival_time
        
        # Eğer CPU yükü %100'ü aşarsa sistem boğulur (Thrashing)
        is_thrashing = cpu_load_ratio >= 1.0
        
        # Ana döngüye kalan zaman (İşlemcinin algoritmaları koşturabileceği süre)
        main_loop_available_pct = max(0.0, (1.0 - cpu_load_ratio) * 100.0)
        
        # ORE (Overrun Error) oluşma riski
        overrun_risk = "CRITICAL_COLLAPSE" if cpu_load_ratio >= 1.0 else (
            "HIGH_RISK" if cpu_load_ratio > 0.6 else "SAFE"
        )

        return {
            "byte_rate": byte_rate,
            "inter_arrival_us": round(inter_arrival_time * 1e6, 3),
            "isr_duration_us": round(self.isr_duration_sec * 1e6, 3),
            "cpu_load_pct": round(min(100.0, cpu_load_ratio * 100.0), 2),
            "main_loop_available_pct": round(main_loop_available_pct, 2),
            "is_thrashing": is_thrashing,
            "overrun_risk": overrun_risk
        }

# Test: 100 kByte/s'den 5 MByte/s'ye kadar kesme yükü
sim = InterruptThrashingSimulator(mcu_clock_hz=168_000_000)
rates = [500_000, 1_500_000, 3_000_000, 4_421_000, 5_000_000]

print("[*] Kesme Boğulması (Interrupt Thrashing) ve Sistem Kararlılık Testi:")
print(f"{'Debi (B/s)':<12} | {'Geliş Süresi':<14} | {'ISR Süresi':<12} | {'CPU Yükü':<10} | {'Ana Döngü':<10} | {'Durum':<15}")
print("-" * 82)

res_thrash = []
for r in rates:
    st = sim.evaluate_system_stability(r)
    res_thrash.append(st)
    print(f"{st['byte_rate']:<12,d} | {st['inter_arrival_us']:<11.3f} us | {st['isr_duration_us']:<9.3f} us | %{st['cpu_load_pct']:<8.1f} | %{st['main_loop_available_pct']:<8.1f} | {st['overrun_risk']:<15}")

# Doğrulama: 4.42 MHz üzerinde CPU %100 kilitlenmelidir (168M / 38 = 4.421.052 B/s)
crit_rate = int(168_000_000 / 38)
collapse_check = sim.evaluate_system_stability(crit_rate + 1000)
assert collapse_check["is_thrashing"] is True, "Kritik frekans aşıldığında sistem boğulmalıdır!"
assert collapse_check["main_loop_available_pct"] == 0.0, "Boğulmada ana döngüye sıfır süre kalmalıdır!"
print("\n[HÜCRE 8] Kesme boğulması ve kritik çöküş frekansı başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 174: Kod Bloğu 3 — C++20 STM32 DMA Controller Kayıt Seviyesi Simülatörü
Stream Konfigürasyonu, NDTR Geri Sayımı, Circular Wrap-around ve TCIF Bayrak Yönetimi
"""

from typing import List, Dict, Optional

class VirtualSTM32DMAStream:
    """STM32 DMA Stream Kayıt Seviyesi Emülatörü"""
    def __init__(self, stream_id: int):
        self.stream_id = stream_id
        
        # Yazmaçlar (Registers)
        self.CR = 0       # Control Register (DIR, CIRC, MINC, PINC, TCIE, HTIE, EN)
        self.NDTR = 0     # Number of Data Items to Transfer
        self.PAR = 0      # Peripheral Address Register
        self.M0AR = 0     # Memory 0 Address Register
        self.initial_ndtr = 0
        
        # Durum Bayrakları (Status Flags - LISR / HISR)
        self.TCIF = False # Transfer Complete Interrupt Flag
        self.HTIF = False # Half Transfer Interrupt Flag
        self.TEIF = False # Transfer Error Interrupt Flag
        
        # Bellek alanı simülasyonu
        self.memory_buffer = []

    def configure(self, periph_addr: int, mem_size: int, circular: bool = True, minc: bool = True):
        self.PAR = periph_addr
        self.NDTR = mem_size
        self.initial_ndtr = mem_size
        self.memory_buffer = [0] * mem_size
        
        # CR Bitleri: EN=1, CIRC=(1 if circular else 0), MINC=(1 if minc else 0)
        self.CR = (1 << 0) # EN
        if circular:
            self.CR |= (1 << 8) # CIRC
        if minc:
            self.CR |= (1 << 10) # MINC (Memory Increment)
            
        self.TCIF = False
        self.HTIF = False

    def trigger_peripheral_transfer(self, incoming_data: int) -> Dict[str, any]:
        """Çevre biriminden 1 bayt veri geldiğinde (DMAReq) DMA aktarımı"""
        if not (self.CR & (1 << 0)): # EN biti sıfırsa transfer yapılamaz
            return {"status": "DISABLED"}

        write_index = self.initial_ndtr - self.NDTR
        self.memory_buffer[write_index] = incoming_data
        self.NDTR -= 1
        
        half_point = self.initial_ndtr // 2
        is_half = (self.NDTR == half_point)
        if is_half:
            self.HTIF = True
            
        is_complete = (self.NDTR == 0)
        if is_complete:
            self.TCIF = True
            if self.CR & (1 << 8): # CIRC Modu aktifse başa dön
                self.NDTR = self.initial_ndtr # Auto-reload
            else:
                self.CR &= ~(1 << 0) # Normal modda EN sıfırlanır

        return {
            "status": "TRANSFER_OK",
            "written_index": write_index,
            "remaining_ndtr": self.NDTR,
            "htif_triggered": is_half,
            "tcif_triggered": is_complete
        }

# Test: 4 Baytlık Tampon ile Circular DMA Simülasyonu
dma = VirtualSTM32DMAStream(stream_id=0)
dma.configure(periph_addr=0x40011004, mem_size=4, circular=True, minc=True)

test_stream = [0x11, 0x22, 0x33, 0x44, 0x55] # 5 bayt veri
events = []
for b in test_stream:
    ev = dma.trigger_peripheral_transfer(b)
    events.append(ev)

print("[*] STM32 DMA Stream Circular Mod ve Bayrak Simülasyonu:")
for i, ev in enumerate(events):
    print(f"  [+] Bayt {i+1} (0x{test_stream[i]:02X}) -> İndis: {ev['written_index']} | Kalan NDTR: {ev['remaining_ndtr']} | HTIF: {ev['htif_triggered']} | TCIF: {ev['tcif_triggered']}")

# Doğrulamalar:
assert events[1]["htif_triggered"] is True, "2. baytta Half Transfer (HTIF) kalkmalıydı!"
assert events[3]["tcif_triggered"] is True, "4. baytta Transfer Complete (TCIF) kalkmalıydı!"
assert events[4]["written_index"] == 0, "Circular mod 5. baytta başa sarmalıydı (İndis 0)!"
assert dma.memory_buffer[0] == 0x55, "Başa yazılan veri 0x55 olmalıydı!"
print("\n[HÜCRE 10] C++20 STM32 DMA controller simülatörü başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 174: Kod Bloğu 4 — Bus Arbiter ve Çoklu Master Çekişme Modeli (CPU vs DMA)
Bus Matrix Çakışma Yönetimi, Round-Robin Önceliklendirme ve Çevrim Kaybı Analizi
"""

from typing import Dict, List

class BusMatrixCrossbarSimulator:
    """Multi-AHB Bus Matrix Çakışma ve Eşzamanlılık Simülatörü"""
    def __init__(self):
        # Master'lar: CPU_I, CPU_D, DMA1, DMA2
        # Slave'ler : FLASH, SRAM1, SRAM2, APB1, APB2
        pass

    def simulate_bus_cycle(self, cpu_target: str, dma_target: str) -> Dict[str, any]:
        """
        CPU ve DMA aynı anda farklı veya aynı slave'e erişmeye çalışır.
        Eğer hedefler farklıysa: Çakışma YOK (Concurrent - 0 wait state).
        Eğer hedefler aynıysa  : Çakışma VAR (Arbiter devreye girer, biri bekler).
        """
        is_contention = (cpu_target == dma_target)
        
        if not is_contention:
            return {
                "cpu_target": cpu_target,
                "dma_target": dma_target,
                "contention": False,
                "cpu_stolen_cycles": 0,
                "throughput_efficiency": 1.0,
                "mode": "CONCURRENT_PARALLEL_ACCESS"
            }
        else:
            # Arbiter Round-Robin kuralı ile 1 çevrimlik gecikme sokar
            return {
                "cpu_target": cpu_target,
                "dma_target": dma_target,
                "contention": True,
                "cpu_stolen_cycles": 1,
                "throughput_efficiency": 0.5,
                "mode": "ARBITER_WAIT_STATE"
            }

# Simülasyon: Farklı Sistem Senaryoları
matrix = BusMatrixCrossbarSimulator()

scenarios = [
    # Senaryo 1: Optimum Tasarım — CPU Flash'tan kod çekiyor, DMA SRAM1'e yazıyor
    ("FLASH", "SRAM1"),
    # Senaryo 2: Mükemmel Paralellik — CPU SRAM1'de yığın çalıştırıyor, DMA SRAM2'ye yazıyor
    ("SRAM1", "SRAM2"),
    # Senaryo 3: Çekişme Durumu — Hem CPU hem DMA aynı SRAM1 alanına erişmeye çalışıyor!
    ("SRAM1", "SRAM1"),
    # Senaryo 4: APB Çekişmesi — Hem CPU hem DMA çevre birimine yazıyor
    ("APB1", "APB1")
]

print("[*] Multi-AHB Bus Matrix Eşzamanlılık ve Çakışma Denetimi:")
for c_tgt, d_tgt in scenarios:
    res = matrix.simulate_bus_cycle(c_tgt, d_tgt)
    status = "PARALEL (Sıfır Kayıp)" if not res["contention"] else "ÇAKIŞMA (1 Çevrim Bekleme)"
    print(f"  CPU -> {res['cpu_target']:<6} | DMA -> {res['dma_target']:<6} | Mod: {status}")

# Doğrulama
opt = matrix.simulate_bus_cycle("SRAM1", "SRAM2")
assert opt["contention"] is False and opt["cpu_stolen_cycles"] == 0, "Farklı SRAM bloklarında çakışma olmamalıdır!"

con = matrix.simulate_bus_cycle("SRAM1", "SRAM1")
assert con["contention"] is True and con["cpu_stolen_cycles"] == 1, "Aynı blokta arbiter 1 çevrim durdurmalıdır!"
print("\n[HÜCRE 12] Bus Matrix çakışma ve eşzamanlılık modeli başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 174: Kod Bloğu 5 — Radar IQ Akışında Sıfır-CPU DMA Alımı ve Paralel FFT Yürütümü
Ping-Pong (Half/Full Transfer) Mimarisi ve Eşzamanlı DSP İşleme Simülasyonu
"""

import math
from typing import List, Dict

class RadarPulseProcessorDMA:
    """Taktik Radar IQ Akışı ve Donanımsal DMA Tampon Yöneticisi"""
    def __init__(self, buffer_size: int = 1024):
        self.buffer_size = buffer_size
        self.half_size = buffer_size // 2
        
        # Tamponlar (Ping-Pong)
        self.dma_raw_buffer = [0.0] * buffer_size
        self.processed_buffers_count = 0
        self.detected_targets = []

    def simulate_radar_stream(self, samples: List[float]) -> Dict[str, any]:
        """ADC'den gelen radar sinyallerini DMA ile toplar ve HT/TC anında FFT simüle eder"""
        ht_events = 0
        tc_events = 0
        
        for idx, sample in enumerate(samples):
            buf_pos = idx % self.buffer_size
            self.dma_raw_buffer[buf_pos] = sample
            
            # Half-Transfer Kesmesi (İlk yarı doldu: Ping Tamponu İşle)
            if buf_pos == self.half_size - 1:
                ht_events += 1
                self._execute_fft_on_half_buffer(buffer_id="PING_HALF_A", start_idx=0)
                
            # Transfer-Complete Kesmesi (İkinci yarı doldu: Pong Tamponu İşle)
            elif buf_pos == self.buffer_size - 1:
                tc_events += 1
                self._execute_fft_on_half_buffer(buffer_id="PONG_HALF_B", start_idx=self.half_size)
                
        return {
            "total_samples_ingested": len(samples),
            "ht_interrupts": ht_events,
            "tc_interrupts": tc_events,
            "total_interrupts": ht_events + tc_events,
            "cpu_overhead_reduction_factor": len(samples) / (ht_events + tc_events)
        }

    def _execute_fft_on_half_buffer(self, buffer_id: str, start_idx: int):
        """CPU'nun arka planda koşturduğu 512 noktalı sinyal işleme görevi"""
        half_data = self.dma_raw_buffer[start_idx : start_idx + self.half_size]
        # Basit güç spektrumu hesabı
        power = sum(x * x for x in half_data) / len(half_data)
        if power > 50.0: # Eşik üzeri hedef
            self.detected_targets.append((buffer_id, power))
        self.processed_buffers_count += 1

# Simülasyon: 4096 Örnekli Radar Yankı Dizisi (Hedef Sinyali Eklenmiş)
samples = [math.sin(0.1 * i) * 5.0 for i in range(4096)]
# 1500..1600 arasına güçlü bir hedef darbesi yerleştir
for k in range(1500, 1600):
    samples[k] += 30.0

radar_dma = RadarPulseProcessorDMA(buffer_size=1024)
res_radar = radar_dma.simulate_radar_stream(samples)

print("[*] Taktik Radar DMA Çift Tamponlama ve Paralel İşleme Raporu:")
print(f"  [+] Alınan Toplam Örnek Sayısı : {res_radar['total_samples_ingested']:,}")
print(f"  [+] Half-Transfer (HT) Kesmesi : {res_radar['ht_interrupts']}")
print(f"  [+] Transfer-Complete (TC)     : {res_radar['tc_interrupts']}")
print(f"  [+] Toplam CPU Kesme Sayısı    : {res_radar['total_interrupts']} (Kesme Başına 512 Örnek!)")
print(f"  [+] Kesme Yükü Azaltma Faktörü : {res_radar['cpu_overhead_reduction_factor']:.0f}x Daha Az Kesme!")
print(f"  [+] Tespit Edilen Radar Hedefi : {len(radar_dma.detected_targets)} adet")

# Doğrulama: 4096 örnekte tam olarak 4 HT ve 4 TC (toplam 8 kesme) oluşmalıdır!
assert res_radar["total_interrupts"] == 8, "4096 örnek 1024'lük tamponda 8 kesme üretmelidir!"
assert res_radar["cpu_overhead_reduction_factor"] == 512.0, "Her kesme 512 örneği kapsamalıdır!"
assert len(radar_dma.detected_targets) > 0, "Hedef darbesi tespit edilmeliydi!"
print("\n[HÜCRE 14] Taktik radar DMA alım ve çift tamponlama motoru başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 174: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. CPU Yükü vs Veri Hızı (Polling %100, Interrupt Üstel Yükseliş, DMA <%0.1)
2. ARM Cortex-M Bus Matrix Çevrim Eşzamanlılığı (CPU ALU vs DMA AHB Transferi)
3. Kesme Maliyeti Dağılımı (Stacking + Execution + Unstacking vs Tek TC Kesmesi)
4. Taktik Radar Alıcısında Ping-Pong Tamponlama ve Paralel FFT Yürütme Zamanlaması
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

C_BG = '#1E293B'
C_CYAN = '#38BDF8'
C_GREEN = '#34D399'
C_RED = '#F87171'
C_YELLOW = '#FBBF24'
C_PURPLE = '#A855F7'
C_WHITE = '#F8FAFC'

# ------------------------------------------------------------------------------
# PANEL 1: CPU Yükü vs Veri Hızı (Throughput vs CPU Utilization)
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

# 1 kB/s'den 5 MB/s'ye kadar logaritmik hız
rates = np.logspace(3, 6.7, 200) # 1,000 B/s to ~5,000,000 B/s
mcu_clock = 168_000_000 # 168 MHz
isr_cycles_per_byte = 38

# Polling: Daima %100
polling_load = np.full_like(rates, 100.0)

# Interrupt: (Rate * 38 / 168M) * 100
interrupt_load = np.clip((rates * isr_cycles_per_byte / mcu_clock) * 100.0, 0.0, 100.0)

# DMA (1024'lük blok başına 38 çevrim):
dma_load = ((rates / 1024.0) * isr_cycles_per_byte / mcu_clock) * 100.0

ax1.plot(rates, polling_load, color=C_RED, linestyle='--', linewidth=2.0, label='Yoklama (Polling) - %100 Kilitli')
ax1.plot(rates, interrupt_load, color=C_YELLOW, linewidth=2.5, label='Kesme (Interrupt / ISR) - Üstel Yük')
ax1.plot(rates, dma_load, color=C_GREEN, linewidth=3.0, label='DMA (Direct Memory Access) - <%0.1 Yük!')

# Çöküş çizgisi
crit_collapse_rate = mcu_clock / isr_cycles_per_byte
ax1.axvline(crit_collapse_rate, color=C_RED, linestyle=':', linewidth=1.8, label=f'Kesme Çöküş Sınırı ({crit_collapse_rate/1e6:.2f} MB/s)')

ax1.set_xscale('log')
ax1.set_xlabel("Veri Hızı (Bayt / Saniye, Log Ölçek)", color=C_WHITE, fontsize=10)
ax1.set_ylabel("İşlemci (CPU) Yükü (%)", color=C_WHITE, fontsize=10)
ax1.set_title("Panel 1: Veri Akış Hızına Karşı İşlemci (CPU) Tüketim Analizi", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax1.legend(loc='center left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 2: Bus Matrix Eşzamanlılığı (Zero-Wait Concurrency)
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

cycles = np.arange(0, 16)
# Senaryo: CPU Flash'tan komut okur ve FPU'da FFT hesabı yapar (Sürekli aktif)
cpu_active = np.ones(16)
# DMA aynı anda her saat çevriminde ADC'den SRAM2'ye veri transfer eder
dma_active = np.ones(16)

bar_width = 0.35
ax2.bar(cycles - bar_width/2, cpu_active, width=bar_width, color=C_CYAN, label='ARM Cortex-M CPU (FPU FFT / Algoritma)')
ax2.bar(cycles + bar_width/2, dma_active, width=bar_width, color=C_GREEN, label='DMA Controller (AHB Matrix Otoban Transferi)')

ax2.set_xticks(cycles)
ax2.set_xlabel("Sistem Saat Çevrimi (Clock Cycles)", color=C_WHITE, fontsize=10)
ax2.set_ylabel("Donanımsal Aktivite Seviyesi", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: Multi-AHB Bus Matrix Çapraz Eşzamanlı Çalışma (Zero Stolen Cycle)", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')
ax2.set_ylim(0, 1.4)
ax2.text(2, 1.15, "TAM PARALEL: CPU Çevrim Kaybetmez!", color=C_GREEN, fontweight='bold', fontsize=9,
         bbox=dict(boxstyle='round,pad=0.3', facecolor='#064E3B', edgecolor=C_GREEN))

# ------------------------------------------------------------------------------
# PANEL 3: Kesme Maliyeti Dağılımı (ISR Overhead Breakdown)
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

categories = ['Donanım Stacking\n(R0-R3, LR, PC)', 'ISR Gövdesi\n(DR Oku & Yaz)', 'Donanım Unstacking\n(Geri Yükleme)', 'DMA Blok Transferi\n(1024 Bayt İçin)']
cycle_costs = [12, 14, 12, 38 / 1024.0] # DMA'da bayt başına 0.037 çevrim!
colors = [C_YELLOW, C_RED, C_PURPLE, C_GREEN]

bars = ax3.bar(categories, cycle_costs, color=colors, width=0.55)
ax3.set_ylabel("Bayt Başına Harcanan CPU Çevrimi", color=C_WHITE, fontsize=10)
ax3.set_title("Panel 3: Bayt Başına Kesme Yükü (ISR Overhead) vs DMA Verimi", color=C_WHITE, fontsize=12, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B', axis='y')

for bar, cost in zip(bars, cycle_costs):
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f"{cost:.2f} Çevrim", 
             ha='center', va='bottom', color=C_WHITE, fontweight='bold', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 4: Radar Ping-Pong Çift Tamponlama Zaman Çizelgesi
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

time_axis = np.linspace(0, 10, 500)
# Tampon A dolum ve CPU işleme
# 0..5 aralığında DMA Tampon A'yı doldurur, CPU Tampon B'yi işler
# 5..10 aralığında DMA Tampon B'yi doldurur, CPU Tampon A'yı işler

ax4.fill_between([0, 5], [1, 1], [0, 0], color=C_GREEN, alpha=0.35, label='DMA: Tampon A Doluyor (Ping)')
ax4.fill_between([0, 5], [2, 2], [1, 1], color=C_CYAN, alpha=0.45, label='CPU: Tampon B FFT İşleniyor (Pong)')

ax4.fill_between([5, 10], [1, 1], [0, 0], color=C_YELLOW, alpha=0.35, label='DMA: Tampon B Doluyor (Pong)')
ax4.fill_between([5, 10], [2, 2], [1, 1], color=C_PURPLE, alpha=0.45, label='CPU: Tampon A FFT İşleniyor (Ping)')

# Kesme Noktaları
ax4.axvline(5.0, color=C_WHITE, linestyle='--', linewidth=2.0)
ax4.text(5.05, 1.5, "HTIF (Half Transfer)\nTamponlar Takas Edildi!", color=C_WHITE, fontweight='bold', fontsize=8)

ax4.set_yticks([0.5, 1.5])
ax4.set_yticklabels(['DMA Controller', 'Cortex-M CPU (FFT)'], color=C_WHITE, fontweight='bold', fontsize=9)
ax4.set_xlabel("Zaman Akışı (Zaman Dilimleri)", color=C_WHITE, fontsize=10)
ax4.set_title("Panel 4: Taktik Radar Ping-Pong Çift Tamponlama Kesintisiz İşleme Akışı", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax4.legend(loc='lower left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.suptitle("GÜN 174: DMA Neden Var? — Direct Memory Access ve Bus Matrix Mimarisi Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_174_dma_neden_var.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_174\gun_174_dma_neden_var.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 174 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. CPU Çevrim Maliyeti Assertions
prof = CpuDataTransferProfiler(mcu_clock_hz=168_000_000)
p_res = prof.profile_transfer(2_000_000, buffer_size=1024)
assert p_res["interrupt_cpu_pct"] > 40.0, "2 MB/s hızda kesme yükü %40'ı geçmelidir!"
assert p_res["dma_cpu_pct"] < 0.1, "DMA CPU yükü %0.1'in altında olmalıdır!"

# 3. Kesme Boğulması (Thrashing) Assertions
thrash_sim = InterruptThrashingSimulator(mcu_clock_hz=168_000_000)
crit_st = thrash_sim.evaluate_system_stability(5_000_000)
assert crit_st["is_thrashing"] is True, "5 MB/s hızda sistem kesinlikle boğulmalıdır!"
assert crit_st["main_loop_available_pct"] == 0.0, "Ana döngüye sıfır süre kalmalıdır!"

# 4. DMA Stream ve Donanım Kayıt Assertions
stream_sim = VirtualSTM32DMAStream(stream_id=1)
stream_sim.configure(periph_addr=0x40011004, mem_size=4, circular=True, minc=True)
_ = stream_sim.trigger_peripheral_transfer(0xAA)
_ = stream_sim.trigger_peripheral_transfer(0xBB)
assert stream_sim.HTIF is True, "2. baytta Half Transfer kalkmalıydı!"
_ = stream_sim.trigger_peripheral_transfer(0xCC)
_ = stream_sim.trigger_peripheral_transfer(0xDD)
assert stream_sim.TCIF is True, "4. baytta Transfer Complete kalkmalıydı!"
assert stream_sim.NDTR == 4, "Circular modda NDTR auto-reload olmalıydı!"

# 5. Radar Ping-Pong DMA İşleme Assertions
test_sig = [1.0] * 2048
r_proc = RadarPulseProcessorDMA(buffer_size=1024)
r_eval = r_proc.simulate_radar_stream(test_sig)
assert r_eval["total_interrupts"] == 4, "2048 örnek 1024'lük tamponda 4 kesme üretmelidir!"
assert r_eval["cpu_overhead_reduction_factor"] == 512.0, "İyileştirme faktörü 512 olmalıdır!"

print("\n[PASS] Gün 174: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
