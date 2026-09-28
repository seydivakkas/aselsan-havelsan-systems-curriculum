"""
===============================================================================
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.
===============================================================================
GÜN 003: CPU, Instruction Set ve Saat (Clock) Döngüsü Fiziği
24-Hücreli Master Mimari Planı Kapsamında Çalıştırılabilir Simülasyon ve Benchmark Motoru
===============================================================================
"""

import time
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# =============================================================================
# CODE 1: Modül 1 - 4-Aşamalı CPU Döngüsü Emülatörü (Fetch-Decode-Execute-WB)
# =============================================================================
@dataclass
class Instruction:
    opcode: str      # 'ADD', 'SUB', 'LOAD', 'STORE', 'JMP', 'NOP'
    dest: int        # R0..R7
    src1: int        # R0..R7 veya imm
    src2: int = 0    # R0..R7 veya imm
    is_imm: bool = False

class SimpleCPU:
    """
    Klasik RISC benzeri 4 aşamalı komut çevrimi simülatörü.
    """
    def __init__(self, mem_size: int = 256):
        self.registers = [0] * 8
        self.memory = [0] * mem_size
        self.pc = 0
        self.clock_cycles = 0
        self.instructions_retired = 0

    def step(self, program: List[Instruction]) -> Optional[str]:
        if self.pc >= len(program):
            return None
        
        # 1. FETCH (Komut Getir)
        inst = program[self.pc]
        self.pc += 1
        self.clock_cycles += 1
        
        # 2. DECODE & 3. EXECUTE (Çöz ve Çalıştır)
        val1 = inst.src1 if inst.is_imm else self.registers[inst.src1]
        val2 = inst.src2 if inst.is_imm else self.registers[inst.src2]
        
        res = 0
        if inst.opcode == 'ADD':
            res = val1 + val2
        elif inst.opcode == 'SUB':
            res = val1 - val2
        elif inst.opcode == 'LOAD':
            res = self.memory[val1 % len(self.memory)]
        elif inst.opcode == 'STORE':
            self.memory[val1 % len(self.memory)] = self.registers[inst.dest]
            res = None
        elif inst.opcode == 'NOP':
            res = None
            
        # 4. WRITEBACK (Geri Yaz)
        if res is not None and inst.opcode not in ('STORE', 'NOP'):
            self.registers[inst.dest] = res & 0xFFFFFFFF
            
        self.instructions_retired += 1
        return f"Cycle {self.clock_cycles}: {inst.opcode} -> R{inst.dest}={self.registers[inst.dest]}"

# =============================================================================
# CODE 2: Modül 2 - Pipeline Tehlikeleri (Data Hazard) ve Stall Simülatörü
# =============================================================================
class PipelinedCPUSimulator:
    """
    4 aşamalı Pipeline (Fetch, Decode, Execute, Writeback) simülasyonu.
    Read-After-Write (RAW) Data Hazard tespit eder ve Stall döngüleri enjekte eder.
    """
    def __init__(self):
        self.total_cycles = 0
        self.stalls = 0
        self.instructions_executed = 0

    def run_pipeline(self, program: List[Instruction], enable_forwarding: bool = False) -> Dict[str, float]:
        self.total_cycles = 0
        self.stalls = 0
        self.instructions_executed = len(program)
        
        # Her yazmaç için en son ne zaman güncelleneceği bilgisini tutar
        reg_ready_at = [0] * 8
        current_cycle = 0

        for inst in program:
            current_cycle += 1 # Her komut en az 1 döngüde Fetch edilir
            
            # Veri bağımlılığı kontrolü (RAW Hazard)
            hazard_stall = 0
            if not inst.is_imm and inst.opcode in ('ADD', 'SUB', 'STORE'):
                needed_cycle = max(reg_ready_at[inst.src1], reg_ready_at[inst.src2])
                if needed_cycle > current_cycle:
                    # Stall gerekiyor
                    penalty = needed_cycle - current_cycle
                    if enable_forwarding:
                        penalty = max(0, penalty - 1) # Forwarding 1 döngü kazandırır
                    hazard_stall = penalty
                    
            current_cycle += hazard_stall
            self.stalls += hazard_stall
            
            # Bu komutun sonucu Writeback aşamasında (2 döngü sonra) hazır olacak
            if inst.opcode in ('ADD', 'SUB', 'LOAD'):
                reg_ready_at[inst.dest] = current_cycle + (1 if enable_forwarding else 2)

        self.total_cycles = current_cycle + 3 # Pipeline drenajı (drain)
        cpi = self.total_cycles / max(1, self.instructions_executed)
        return {
            "total_cycles": self.total_cycles,
            "stalls": self.stalls,
            "cpi": cpi,
            "forwarding": enable_forwarding
        }

# =============================================================================
# CODE 3: Modül 3 - Donanımsal Saat Frekansı & Watchdog Timer Simülatörü
# =============================================================================
class WatchdogTimer:
    """
    Aviyonik görev bilgisayarlarında CPU kilitlenmelerini ve
    saat frekansı yavaşlamalarını algılayan donanımsal zamanlayıcı.
    """
    def __init__(self, timeout_ms: float = 10.0):
        self.timeout_ms = timeout_ms
        self.last_kick_time = time.perf_counter()
        self.reset_triggered = False

    def kick(self):
        """Watchdog besleme (Refresh/Petting)."""
        self.last_kick_time = time.perf_counter()

    def check(self) -> bool:
        elapsed = (time.perf_counter() - self.last_kick_time) * 1000.0
        if elapsed > self.timeout_ms:
            self.reset_triggered = True
            return False # TIMEOUT!
        return True

# =============================================================================
# CODE 4: Sabotaj Senaryosu: Pipeline Stall Patlaması ve Watchdog Reset Faciası
# =============================================================================
def run_sabotage_simulation():
    # Senaryo A: Bağımsız komutlar (Pürüzsüz Pipeline akışı)
    clean_program = [
        Instruction('ADD', dest=0, src1=1, src2=2, is_imm=True),
        Instruction('ADD', dest=3, src1=4, src2=5, is_imm=True),
        Instruction('ADD', dest=6, src1=7, src2=1, is_imm=True),
        Instruction('ADD', dest=1, src1=2, src2=3, is_imm=True),
    ] * 200

    # Senaryo B (Sabotaj): Ağır RAW Bağımlılığı (Her komut bir öncekinin sonucunu bekliyor)
    # R1 = R0 + 1; R2 = R1 + 1; R3 = R2 + 1 ... -> Pipeline tamamen kilitlenir!
    dependent_program = []
    for i in range(200):
        dependent_program.append(Instruction('ADD', dest=1, src1=1, src2=1, is_imm=False))
        dependent_program.append(Instruction('ADD', dest=2, src1=1, src2=1, is_imm=False))
        dependent_program.append(Instruction('ADD', dest=3, src1=2, src2=1, is_imm=False))

    sim = PipelinedCPUSimulator()
    res_clean = sim.run_pipeline(clean_program, enable_forwarding=False)
    res_clean_fwd = sim.run_pipeline(clean_program, enable_forwarding=True)
    res_dep = sim.run_pipeline(dependent_program, enable_forwarding=False)
    res_dep_fwd = sim.run_pipeline(dependent_program, enable_forwarding=True)

    # Watchdog Arıza Enjeksiyonu
    wdt = WatchdogTimer(timeout_ms=1.0) # 1 ms deadline
    time.sleep(0.002) # Saat frekansı çöktü / stall yaşandı
    wdt_status = wdt.check() # False dönmeli (Reset tetiklendi)

    return res_clean, res_clean_fwd, res_dep, res_dep_fwd, wdt_status

# =============================================================================
# CODE 5: Modül 4 - Ampirik Kıyaslama ve CPI Analizi (Benchmark Motoru)
# =============================================================================
def run_empirical_benchmark(iterations: int = 5000):
    cpu = SimpleCPU()
    prog = [
        Instruction('ADD', 0, 10, 20, is_imm=True),
        Instruction('ADD', 1, 0, 5, is_imm=False),
        Instruction('SUB', 2, 1, 3, is_imm=False),
    ]

    latencies = []
    for _ in range(iterations):
        cpu.pc = 0
        t0 = time.perf_counter()
        while cpu.pc < len(prog):
            cpu.step(prog)
        dt = (time.perf_counter() - t0) * 1e6
        latencies.append(dt)

    return latencies

# =============================================================================
# CODE 6: Modül 5 - 4-Panelli Yayın Kalitesinde Dashboard ve Katı Doğrulama
# =============================================================================
def generate_dashboard(output_path: str):
    res_clean, res_clean_fwd, res_dep, res_dep_fwd, wdt_tripped = run_sabotage_simulation()
    latencies = run_empirical_benchmark(iterations=5000)

    p50_lat, p95_lat, p99_lat = np.percentile(latencies, [50, 95, 99])

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor('#0f172a')

    for ax_row in axs:
        for ax in ax_row:
            ax.set_facecolor('#1e293b')
            ax.tick_params(colors='#94a3b8')
            ax.xaxis.label.set_color('#cbd5e1')
            ax.yaxis.label.set_color('#cbd5e1')
            ax.title.set_color('#f8fafc')
            ax.grid(True, linestyle='--', alpha=0.2, color='#64748b')

    # Panel 1: CPI (Cycles Per Instruction) Karşılaştırması
    configs = ['Temiz', 'Temiz+Fwd', 'Bağımlı (Hazard)', 'Bağımlı+Fwd']
    cpis = [res_clean['cpi'], res_clean_fwd['cpi'], res_dep['cpi'], res_dep_fwd['cpi']]
    colors = ['#10b981', '#38bdf8', '#ef4444', '#f59e0b']
    axs[0, 0].bar(configs, cpis, color=colors, width=0.45)
    axs[0, 0].set_title('Panel 1: CPI Karşılaştırması (İdeal = 1.0)', fontsize=12, fontweight='bold')
    axs[0, 0].set_ylabel('CPI (Döngü / Komut)')
    for i, v in enumerate(cpis):
        axs[0, 0].text(i, v / 2, f"{v:.2f}", ha='center', color='white', fontweight='bold', fontsize=11)

    # Panel 2: Pipeline Stall Döngü Sayısı Analizi
    stalls = [res_clean['stalls'], res_clean_fwd['stalls'], res_dep['stalls'], res_dep_fwd['stalls']]
    axs[0, 1].bar(configs, stalls, color=colors, width=0.45)
    axs[0, 1].set_title('Panel 2: Data Hazard Kaynaklı Boşa Geçen Stall Döngüleri', fontsize=12, fontweight='bold')
    axs[0, 1].set_ylabel('Stall Döngü Adedi')
    for i, v in enumerate(stalls):
        axs[0, 1].text(i, max(10, v / 2), f"{v}", ha='center', color='white', fontweight='bold', fontsize=11)

    # Panel 3: CPU Döngü Yürütme Gecikmesi Dağılımı (Histogram)
    axs[1, 0].hist(latencies, bins=40, color='#38bdf8', alpha=0.75, density=True)
    axs[1, 0].axvline(p95_lat, color='#f59e0b', linestyle='--', label=f'p95: {p95_lat:.2f} µs')
    axs[1, 0].axvline(p99_lat, color='#ef4444', linestyle='--', label=f'p99: {p99_lat:.2f} µs')
    axs[1, 0].set_title('Panel 3: 3-Komutluk Döngü Yürütme Gecikmesi (µs)', fontsize=12, fontweight='bold')
    axs[1, 0].set_xlabel('Gecikme (µs)')
    axs[1, 0].set_ylabel('Yoğunluk (Density)')
    axs[1, 0].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    # Panel 4: Saat Periyodu ve Frekans Bağıntısı (Fiziksel Model)
    freqs = np.linspace(10, 1000, 100) # 10 MHz to 1000 MHz (1 GHz)
    periods = 1000.0 / freqs # ns cinsinden saat periyodu (T = 1/f)
    axs[1, 1].plot(freqs, periods, color='#ec4899', lw=2.5, label=r'Saat Periyodu: $T_{clk} = 1/f$')
    axs[1, 1].axhline(1.0, color='#64748b', linestyle=':', label='1 GHz = 1.0 ns Sınırı')
    axs[1, 1].set_title('Panel 4: Frekans vs Saat Periyodu (Fiziksel Zaman Sınırı)', fontsize=12, fontweight='bold')
    axs[1, 1].set_xlabel('Saat Frekansı (MHz)')
    axs[1, 1].set_ylabel('Saat Periyodu (ns)')
    axs[1, 1].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 003 Dashboard başarıyla üretildi: {output_path}")

    # ==========================================
    # KATI MİMARİ DOĞRULAMA (STRICT ASSERTIONS)
    # ==========================================
    # 1. Pipeline CPI Invariantı: Bağımlı kodun CPI değeri temiz koddan büyük olmalı
    assert res_dep['cpi'] > res_clean['cpi'], "HATA: Pipeline stall CPI değerini artırmadı!"
    # 2. Forwarding Optimizasyonu: Forwarding açıkken stall sayısı azalmalı
    assert res_dep_fwd['stalls'] < res_dep['stalls'], "HATA: Forwarding stall sayısını düşüremedi!"
    # 3. Watchdog Reset Doğrulaması: Zaman aşımında reset bayrağı düşmeli
    assert wdt_tripped is False, "HATA: Gecikme anında Watchdog reset tetiklenmedi!"
    print("[PASS] Gün 003: Tüm mimari, pipeline ve saat fizik kuralları doğrulandı.")

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    img_target = os.path.join(out_dir, "gun_003_cpu_instruction_clock.png")
    generate_dashboard(img_target)
