"""
===============================================================================
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.
===============================================================================
GÜN 001: Bilgisayar Sistemi: Giriş-İşlem-Çıkış-Depolama
24-Hücreli Master Mimari Planı Kapsamında Çalıştırılabilir Simülasyon ve Benchmark Motoru
===============================================================================
"""

import time
import random
import os
import sys
from collections import deque
from dataclasses import dataclass, field
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# =============================================================================
# CODE 1: Modül 1 - Temel Von Neumann Bilgisayar Simülatörü (Minimal Computer Engine)
# =============================================================================
@dataclass
class CPU:
    accumulator: int = 0
    program_counter: int = 0
    instruction_register: str = ""
    cycles: int = 0

    def execute(self, opcode: str, operand: int, memory: list) -> str:
        self.cycles += 1
        self.instruction_register = f"{opcode} {operand}"
        if opcode == "LOAD":
            self.accumulator = memory[operand]
            return f"LOAD from RAM[{operand}] -> ACC={self.accumulator}"
        elif opcode == "ADD":
            self.accumulator += memory[operand]
            return f"ADD RAM[{operand}] -> ACC={self.accumulator}"
        elif opcode == "STORE":
            memory[operand] = self.accumulator
            return f"STORE ACC to RAM[{operand}]"
        elif opcode == "OUT":
            return f"OUTPUT BUS <= {self.accumulator}"
        else:
            return "NOP"

class BasicComputer:
    def __init__(self, mem_size: int = 16):
        self.memory = [0] * mem_size
        self.cpu = CPU()
        self.input_bus = deque()
        self.output_bus = []

    def load_input(self, data: int, target_mem_addr: int):
        # Giriş biriminden belleğe yükleme (I/O -> Storage)
        self.input_bus.append((data, target_mem_addr))
        self.memory[target_mem_addr] = data

    def run_cycle(self, opcode: str, operand: int) -> str:
        # CPU İşlem döngüsü (Process)
        result = self.cpu.execute(opcode, operand, self.memory)
        if opcode == "OUT":
            self.output_bus.append(self.cpu.accumulator)
        return result

# =============================================================================
# CODE 2: Modül 2 - Bellek Eşlemeli G/Ç (Memory-Mapped I/O) ve DMA Simülasyonu
# =============================================================================
class MemoryMappedIOComputer:
    """
    Savunma elektroniğinde (ör. radar/aviyonik sensör entegrasyonu) kullanılan
    Memory-Mapped I/O (MMIO) ve Direct Memory Access (DMA) simülasyonu.
    """
    IO_SENSOR_ADDR = 0xFE  # Sensör giriş portu adresi
    IO_ACTUATOR_ADDR = 0xFF # Eyleyici çıkış portu adresi

    def __init__(self, ram_size: int = 256):
        self.ram = bytearray(ram_size)
        self.dma_transfers = 0

    def dma_transfer(self, peripheral_data: bytes, dest_addr: int):
        """CPU'yu araya sokmadan doğrudan belleğe blok aktarımı (DMA)."""
        length = len(peripheral_data)
        self.ram[dest_addr : dest_addr + length] = peripheral_data
        self.dma_transfers += length

    def write_reg(self, addr: int, val: int):
        self.ram[addr % len(self.ram)] = val & 0xFF

    def read_reg(self, addr: int) -> int:
        return self.ram[addr % len(self.ram)]

# =============================================================================
# CODE 3: Modül 3 - Sınırlı Kuyruk (Bounded Queue) ve Geri Basınç (Backpressure)
# =============================================================================
@dataclass
class TelemetryFrame:
    sensor_id: int
    payload: float
    timestamp: float

class IngestionEngine:
    """
    Yüksek frekanslı giriş akışını işlemciye taşıyan ve depolayan dayanıklı boru hattı.
    """
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.queue = deque(maxlen=capacity)
        self.dropped_packets = 0
        self.processed_packets = 0

    def push(self, frame: TelemetryFrame) -> bool:
        if len(self.queue) >= self.capacity:
            self.dropped_packets += 1
            return False  # Fast-fail / Drop tail
        self.queue.append(frame)
        return True

    def process_one(self) -> float:
        if not self.queue:
            return 0.0
        frame = self.queue.popleft()
        # Simüle edilen CPU işleme maliyeti
        t_start = time.perf_counter()
        _ = (frame.payload ** 2) % 1000.0
        self.processed_packets += 1
        return (time.perf_counter() - t_start) * 1e6  # mikrosaniye

# =============================================================================
# CODE 4: Sabotaj Senaryosu: Sınırsız Kuyruk (OOM) vs Sınırlı Kuyruk (Robust)
# =============================================================================
def run_sabotage_simulation(burst_size: int = 2000):
    # Senaryo A: Korumasız Sistem (Sınırsız bellek tahsisi - Bellek Yamyamlığı)
    unbounded_queue = []
    unbounded_memory_growth = []

    # Senaryo B: Dayanıklı Savunma Sistemi (Sınırlı Kuyruk + Drop İlkesi)
    bounded_engine = IngestionEngine(capacity=200)
    bounded_memory_footprint = []
    bounded_drops = []

    for i in range(burst_size):
        frame = TelemetryFrame(sensor_id=1, payload=random.random(), timestamp=time.time())
        # Unbounded
        unbounded_queue.append(frame)
        unbounded_memory_growth.append(len(unbounded_queue))

        # Bounded
        bounded_engine.push(frame)
        bounded_memory_footprint.append(len(bounded_engine.queue))
        bounded_drops.append(bounded_engine.dropped_packets)

    return unbounded_memory_growth, bounded_memory_footprint, bounded_drops

# =============================================================================
# CODE 5: Modül 4 - Ampirik Kıyaslama ve Gecikme Dağılımı (Benchmark Engine)
# =============================================================================
def run_empirical_benchmark(iterations: int = 1000):
    computer = BasicComputer()
    computer.memory[1] = 42
    computer.memory[2] = 58

    normal_latencies = []
    burst_latencies = []

    # Normal yük altında işlem
    for _ in range(iterations):
        t0 = time.perf_counter()
        computer.run_cycle("LOAD", 1)
        computer.run_cycle("ADD", 2)
        computer.run_cycle("STORE", 3)
        computer.run_cycle("OUT", 3)
        dt = (time.perf_counter() - t0) * 1e6
        normal_latencies.append(dt)

    # Ağır I/O yükü altında işlem (Disk/RAM gecikmesi simülasyonu)
    for _ in range(iterations):
        t0 = time.perf_counter()
        # Simüle bellek beklemesi (memory stall)
        _ = sum([i * i for i in range(50)])
        computer.run_cycle("LOAD", 1)
        computer.run_cycle("ADD", 2)
        computer.run_cycle("STORE", 3)
        computer.run_cycle("OUT", 3)
        dt = (time.perf_counter() - t0) * 1e6
        burst_latencies.append(dt)

    return normal_latencies, burst_latencies

# =============================================================================
# CODE 6: Modül 5 - 4-Panelli Yayın Kalitesinde Dashboard ve Katı Doğrulama
# =============================================================================
def generate_dashboard(output_path: str):
    unbounded_mem, bounded_mem, bounded_drops = run_sabotage_simulation(burst_size=1500)
    normal_lat, burst_lat = run_empirical_benchmark(iterations=1000)

    # İstatistiksel metrikler
    p50_norm, p95_norm, p99_norm = np.percentile(normal_lat, [50, 95, 99])
    p50_burst, p95_burst, p99_burst = np.percentile(burst_lat, [50, 95, 99])

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor('#0f172a')  # Modern koyu tema

    for ax_row in axs:
        for ax in ax_row:
            ax.set_facecolor('#1e293b')
            ax.tick_params(colors='#94a3b8')
            ax.xaxis.label.set_color('#cbd5e1')
            ax.yaxis.label.set_color('#cbd5e1')
            ax.title.set_color('#f8fafc')
            ax.grid(True, linestyle='--', alpha=0.2, color='#64748b')

    # Panel 1: Bellek Büyümesi: Sınırsız vs Sınırlı
    axs[0, 0].plot(unbounded_mem, label='Korumasız (Sınırsız Kuyruk - OOM Riski)', color='#ef4444', lw=2)
    axs[0, 0].plot(bounded_mem, label='Korumalı (Sınırlı Kapasite=200)', color='#10b981', lw=2)
    axs[0, 0].set_title('Panel 1: Giriş Yığılması Altında Bellek Tüketimi', fontsize=12, fontweight='bold')
    axs[0, 0].set_xlabel('Gelen Giriş Paket Sayısı')
    axs[0, 0].set_ylabel('Bellekte Tutulan Öğe Sayısı')
    axs[0, 0].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    # Panel 2: Drop Oranı ve Arıza İzolasyonu
    axs[0, 1].plot(bounded_drops, label='Fast-Drop Edilen Paketler (Sistem Ayakta)', color='#f59e0b', lw=2)
    axs[0, 1].set_title('Panel 2: Sistem Çökmesini Önleyen Geri Basınç / Drop Grafiği', fontsize=12, fontweight='bold')
    axs[0, 1].set_xlabel('Gelen Giriş Paket Sayısı')
    axs[0, 1].set_ylabel('Düşürülen Paket Adedi')
    axs[0, 1].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    # Panel 3: Gecikme Dağılımı (Histogram & KDE)
    axs[1, 0].hist(normal_lat, bins=40, alpha=0.7, label='Normal Döngü Gecikmesi', color='#38bdf8', density=True)
    axs[1, 0].hist(burst_lat, bins=40, alpha=0.7, label='Bellek Stall Gecikmesi', color='#f43f5e', density=True)
    axs[1, 0].set_title('Panel 3: İşlemci Döngü Gecikmesi Dağılımı (µs)', fontsize=12, fontweight='bold')
    axs[1, 0].set_xlabel('Gecikme (mikrosaniye - µs)')
    axs[1, 0].set_ylabel('Yoğunluk (Density)')
    axs[1, 0].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    # Panel 4: SLA & Yüzdelik (Percentile) Metrikleri Karşılaştırması
    categories = ['p50 (Medyan)', 'p95', 'p99 (Kritik)']
    x = np.arange(len(categories))
    width = 0.35
    axs[1, 1].bar(x - width/2, [p50_norm, p95_norm, p99_norm], width, label='Normal Yük', color='#38bdf8')
    axs[1, 1].bar(x + width/2, [p50_burst, p95_burst, p99_burst], width, label='Stall/Yük Altında', color='#f43f5e')
    axs[1, 1].set_title('Panel 4: SLA Metrikleri (p50, p95, p99 Gecikme Analizi)', fontsize=12, fontweight='bold')
    axs[1, 1].set_xticks(x)
    axs[1, 1].set_xticklabels(categories)
    axs[1, 1].set_ylabel('Gecikme (µs)')
    axs[1, 1].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Dashboard başarıyla üretildi: {output_path}")

    # ==========================================
    # KATI MİMARİ DOĞRULAMA (STRICT ASSERTIONS)
    # ==========================================
    assert max(bounded_mem) <= 200, "HATA: Sınırlı kuyruk kapasitesi aşıldı!"
    assert bounded_drops[-1] > 0, "HATA: Aşırı yükte drop mekanizması tetiklenmedi!"
    assert p99_burst > p50_norm, "HATA: İstatistiksel anomali tespit edilemedi!"
    print("[PASS] Tüm mimari doğrulamalar ve güvenlik sınırları (invariants) geçerli.")

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    img_target = os.path.join(out_dir, "gun001_computer_architecture_benchmark.png")
    generate_dashboard(img_target)
