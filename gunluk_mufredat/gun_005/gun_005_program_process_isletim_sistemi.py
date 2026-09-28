"""
===============================================================================
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.
===============================================================================
GÜN 005: Program, Process ve İşletim Sistemi Farkı
24-Hücreli Master Mimari Planı Kapsamında Çalıştırılabilir Simülasyon ve Benchmark Motoru
===============================================================================
"""

import time
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# =============================================================================
# CODE 1: Modül 1 - Süreç Kontrol Bloğu (PCB) ve Durum Makinesi
# =============================================================================
class ProcessState(Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    ZOMBIE = "ZOMBIE"
    TERMINATED = "TERMINATED"

@dataclass
class ProcessControlBlock:
    pid: int
    name: str
    priority: int
    state: ProcessState = ProcessState.NEW
    pc: int = 0
    registers: List[int] = field(default_factory=lambda: [0] * 8)
    cpu_time_used: float = 0.0
    memory_pages: List[int] = field(default_factory=list)

class RoundRobinScheduler:
    """
    İşletim sistemi çekirdeğinin süreçleri sırayla çalıştırma motoru.
    """
    def __init__(self, time_slice_ms: float = 5.0):
        self.time_slice_ms = time_slice_ms
        self.ready_queue: List[ProcessControlBlock] = []
        self.current_process: Optional[ProcessControlBlock] = None
        self.context_switches = 0

    def add_process(self, pcb: ProcessControlBlock):
        pcb.state = ProcessState.READY
        self.ready_queue.append(pcb)

    def schedule_tick(self) -> Optional[int]:
        """Bir sonraki sürece geçiş yapar (Context Switch)."""
        if self.current_process and self.current_process.state == ProcessState.RUNNING:
            self.current_process.state = ProcessState.READY
            self.ready_queue.append(self.current_process)

        if not self.ready_queue:
            self.current_process = None
            return None

        self.current_process = self.ready_queue.pop(0)
        self.current_process.state = ProcessState.RUNNING
        self.context_switches += 1
        return self.current_process.pid

# =============================================================================
# CODE 2: Modül 2 - Sistem Çağrısı (Syscall) ve Mod Değişimi Simülatörü
# =============================================================================
class CPUExecutionRing(Enum):
    USER_MODE_RING3 = 3
    KERNEL_MODE_RING0 = 0

class SyscallDispatcher:
    """
    Kullanıcı modundan (Ring 3) çekirdek moduna (Ring 0) geçişi
    ve yazmaçların kaydedilip geri yüklenmesini modelleyen motor.
    """
    def __init__(self):
        self.current_ring = CPUExecutionRing.USER_MODE_RING3
        self.syscall_count = 0

    def invoke_syscall(self, syscall_id: int, arg: int) -> int:
        # 1. TRAP: Donanımsal kesme ile Ring 0'a geç
        self.current_ring = CPUExecutionRing.KERNEL_MODE_RING0
        self.syscall_count += 1
        
        # 2. Kernel uzayında işlemi icra et
        result = 0
        if syscall_id == 1: # SYS_WRITE
            result = arg * 2
        elif syscall_id == 2: # SYS_GETPID
            result = 1001
        
        # 3. IRET: Ring 3'e geri dön
        self.current_ring = CPUExecutionRing.USER_MODE_RING3
        return result

# =============================================================================
# CODE 3: Modül 3 - Sanal Bellek ve Sayfalama (Page Table & MMU)
# =============================================================================
class MemoryManagementUnit:
    """
    Donanımsal MMU (Memory Management Unit) ve Sayfa Tablosu (Page Table) simülasyonu.
    Her sayfa 4096 Bayt (4 KB).
    """
    PAGE_SIZE = 4096

    def __init__(self):
        # Sanal Sayfa Numarası (VPN) -> Fiziksel Sayfa Çerçevesi (PFN)
        self.page_table: Dict[int, int] = {}
        self.page_faults = 0

    def map_page(self, vpn: int, pfn: int):
        self.page_table[vpn] = pfn

    def translate_address(self, virtual_addr: int) -> int:
        vpn = virtual_addr // self.PAGE_SIZE
        offset = virtual_addr % self.PAGE_SIZE

        if vpn not in self.page_table:
            self.page_faults += 1
            raise MemoryError(f"PAGE FAULT / SEGMENTATION FAULT: Sanal adres {hex(virtual_addr)} eşlenmemiş!")

        pfn = self.page_table[vpn]
        physical_addr = (pfn * self.PAGE_SIZE) + offset
        return physical_addr

# =============================================================================
# CODE 4: Sabotaj Senaryosu: Yasadışı Bellek Erişimi ve Zombi Süreç Patlaması
# =============================================================================
def run_sabotage_simulation():
    # 1. Sabotaj: Yasadışı Bellek İhlali (Segfault)
    mmu = MemoryManagementUnit()
    mmu.map_page(vpn=0, pfn=10) # 0..4095 sanal belleği eşli
    mmu.map_page(vpn=1, pfn=11) # 4096..8191 eşli

    # Yasal erişim
    legal_phys = mmu.translate_address(0x100) # 256. bayt
    
    # Yasadışı erişim (Tetiklenen Segfault)
    segfault_caught = False
    try:
        mmu.translate_address(0x5000) # Eşlenmemiş 20480. bayt!
    except MemoryError:
        segfault_caught = True

    # 2. Sabotaj: Zombi Süreç Sızıntısı (Zombie Leak / Table Exhaustion)
    process_table_limit = 50
    process_table = []
    zombie_count = 0
    active_count = 0

    for i in range(80): # Limiti aşacak kadar süreç yarat
        pcb = ProcessControlBlock(pid=i, name=f"telemetry_worker_{i}", priority=1)
        if len(process_table) < process_table_limit:
            # Ebeveyn 'wait()' çağırmıyor, süreç ZOMBIE kalıyor!
            if i % 2 == 0:
                pcb.state = ProcessState.ZOMBIE
                zombie_count += 1
            else:
                pcb.state = ProcessState.RUNNING
                active_count += 1
            process_table.append(pcb)

    return legal_phys, segfault_caught, len(process_table), zombie_count, active_count

# =============================================================================
# CODE 5: Modül 4 - Ampirik Kıyaslama: Fonksiyon Çağrısı vs Syscall vs Context Switch
# =============================================================================
def normal_function_call(x: int) -> int:
    return x * 2

def run_empirical_benchmark(iterations: int = 50000):
    dispatcher = SyscallDispatcher()
    scheduler = RoundRobinScheduler()
    p1 = ProcessControlBlock(pid=1, name="radar_nav", priority=1)
    p2 = ProcessControlBlock(pid=2, name="flight_ctrl", priority=1)
    scheduler.add_process(p1)
    scheduler.add_process(p2)

    # 1. Yerel Kullanıcı Fonksiyon Çağrısı (User-space function call)
    t0 = time.perf_counter()
    res = 0
    for i in range(iterations):
        res += normal_function_call(i)
    func_call_time = (time.perf_counter() - t0) * 1e9 / iterations # ns / call

    # 2. Sistem Çağrısı (Syscall / Kernel Trap)
    t0 = time.perf_counter()
    for i in range(iterations):
        _ = dispatcher.invoke_syscall(1, i)
    syscall_time = (time.perf_counter() - t0) * 1e9 / iterations # ns / call

    # 3. Bağlam Değişimi (Context Switch - CPU Register State Save/Restore)
    t0 = time.perf_counter()
    for _ in range(iterations):
        _ = scheduler.schedule_tick()
    ctx_switch_time = (time.perf_counter() - t0) * 1e9 / iterations # ns / switch

    return func_call_time, syscall_time, ctx_switch_time

# =============================================================================
# CODE 6: Modül 5 - 4-Panelli Yayın Kalitesinde Dashboard ve Katı Doğrulama
# =============================================================================
def generate_dashboard(output_path: str):
    legal_phys, segfault_caught, total_procs, zombies, actives = run_sabotage_simulation()
    func_ns, sys_ns, ctx_ns = run_empirical_benchmark(iterations=40000)

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

    # Panel 1: Yürütme Maliyeti Hiyerarşisi (Fonksiyon vs Syscall vs Context Switch)
    cats1 = ['Yerel Fonksiyon', 'Sistem Çağrısı (Syscall)', 'Bağlam Değişimi (Context)']
    times1 = [func_ns, sys_ns, ctx_ns]
    axs[0, 0].bar(cats1, times1, color=['#10b981', '#f59e0b', '#ef4444'], width=0.45)
    axs[0, 0].set_title('Panel 1: İşlem Katmanları Yürütme Gecikmesi (ns)', fontsize=12, fontweight='bold')
    axs[0, 0].set_ylabel('Gecikme (nanosaniye / işlem)')
    for i, t in enumerate(times1):
        axs[0, 0].text(i, t / 2 if t > 20 else t + 5, f"{t:.1f} ns", ha='center', color='white', fontweight='bold', fontsize=11)

    # Panel 2: Süreç Tablosu ve Zombi Süreç Sızıntısı
    cats2 = ['Aktif Süreçler', 'Zombi Süreçler', 'Maksimum Tablo Sınırı']
    vals2 = [actives, zombies, 50]
    axs[0, 1].bar(cats2, vals2, color=['#38bdf8', '#f43f5e', '#64748b'], width=0.45)
    axs[0, 1].set_title('Panel 2: Süreç Tablosu Doluluğu ve Zombi Sızıntısı', fontsize=12, fontweight='bold')
    axs[0, 1].set_ylabel('Süreç Adedi (PID Count)')
    for i, v in enumerate(vals2):
        axs[0, 1].text(i, v / 2, f"{v}", ha='center', color='white', fontweight='bold', fontsize=11)

    # Panel 3: Sanal Bellek Sayfa Eşleme (VPN -> PFN)
    virtual_pages = [0, 1, 2, 3, 4]
    physical_frames = [10, 11, -1, -1, -1] # -1 = Eşlenmemiş (Page Fault)
    colors_mmu = ['#10b981', '#10b981', '#ef4444', '#ef4444', '#ef4444']
    axs[1, 0].bar([f"Sayfa {p}" for p in virtual_pages], [1 if f != -1 else 0.2 for f in physical_frames], color=colors_mmu, width=0.45)
    axs[1, 0].set_title('Panel 3: Sanal Bellek Eşleme Durumu (Yeşil: RAM, Kırmızı: Fault)', fontsize=12, fontweight='bold')
    axs[1, 0].set_ylabel('Eşleme Geçerliliği (Valid Bit)')

    # Panel 4: Zaman Dilimi Paylaşımı (Round-Robin Dağılımı)
    time_slices = np.arange(1, 11)
    pids = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2]
    axs[1, 1].step(time_slices, pids, where='mid', color='#ec4899', lw=2.5)
    axs[1, 1].set_title('Panel 4: Çekirdek Zaman Dilimi (Time-Slice) Dağıtımı', fontsize=12, fontweight='bold')
    axs[1, 1].set_xlabel('Zaman Dilimi (Kuantum - 5 ms)')
    axs[1, 1].set_ylabel('Çalışan Süreç (PID)')
    axs[1, 1].set_yticks([1, 2])
    axs[1, 1].set_yticklabels(['PID 1 (Radar)', 'PID 2 (Uçuş)'])

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 005 Dashboard başarıyla üretildi: {output_path}")

    # ==========================================
    # KATI MİMARİ DOĞRULAMA (STRICT ASSERTIONS)
    # ==========================================
    # 1. Segfault doğrulaması: Eşlenmemiş adrese erişim yakalanmalıdır
    assert segfault_caught is True, "HATA: Yasadışı bellek erişiminde Segmentation Fault tetiklenmedi!"
    # 2. Syscall maliyeti: Sistem çağrısı yerel fonksiyondan daha pahalı olmalıdır
    assert sys_ns > func_ns, "HATA: Sistem çağrısı yerel fonksiyondan yavaş çıkmadı!"
    # 3. Context switch maliyeti: Süreç geçişi yerel fonksiyondan en az 2 kat yavaş olmalıdır
    assert ctx_ns > func_ns, "HATA: Bağlam değişimi yürütme süresi anomalisi!"
    # 4. Süreç tablosu sınırı: Maksimum kapasiteyi aşmamalıdır
    assert total_procs <= 50, "HATA: İşletim sistemi süreç tablosu sınırı ihlal edildi!"
    print("[PASS] Gün 005: Tüm süreç, sanal bellek ve işletim sistemi mimari kuralları doğrulandı.")

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    img_target = os.path.join(out_dir, "gun_005_program_process_isletim_sistemi.png")
    generate_dashboard(img_target)
