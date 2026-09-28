# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""

# GÜN 086: fork zihinsel modeli Master Script

# Modül 1: Temel Çekirdek Mekanizma / fork() Simülatörü ve Donanımsal Yazmaç Klonlama Motoru
from typing import Dict, List, Optional, Tuple, Any

class CpuRegisters:
    """İşlemci donanımsal yazmaç yedeği (struct pt_regs simülasyonu)."""
    def __init__(self, rip: int = 0x400000, rsp: int = 0x7ffffff0, rax: int = 0):
        self.rip = rip  # Instruction Pointer (Program Sayacı)
        self.rsp = rsp  # Stack Pointer (Yığın Göstergesi)
        self.rax = rax  # Return Value Register (Dönüş Değeri Yazmacı)

    def clone(self) -> 'CpuRegisters':
        return CpuRegisters(rip=self.rip, rsp=self.rsp, rax=self.rax)

class SimulatedProcess:
    """Linux çekirdeğindeki struct task_struct bağlamı."""
    def __init__(self, pid: int, ppid: int, name: str, registers: CpuRegisters):
        self.pid = pid
        self.ppid = ppid
        self.name = name
        self.regs = registers
        self.open_files: Dict[int, int] = {0: 0, 1: 0, 2: 0} # fd -> shared_file_description_id
        self.virtual_pages: Dict[int, int] = {} # virtual_page_num -> physical_frame_id

class KernelForkEngine:
    """Linux copy_process() ve sys_fork() mekanizmasını simüle eden çekirdek motoru."""
    def __init__(self):
        self.process_table: Dict[int, SimulatedProcess] = {}
        self.next_pid = 100
        # Başlangıç ebeveyn süreci
        init_regs = CpuRegisters(rip=0x401050, rsp=0x7fffff00, rax=0)
        parent = SimulatedProcess(pid=self.next_pid, ppid=1, name="parent_radar", registers=init_regs)
        self.process_table[self.next_pid] = parent
        self.next_pid += 1

    def do_fork(self, parent_pid: int) -> Tuple[int, int]:
        """
        fork() sistem çağrısını simüle eder.
        Döner: (ebeveynin_gördüğü_dönüş, çocuğun_gördüğü_dönüş)
        """
        if parent_pid not in self.process_table:
            raise ValueError(f"ESRCH: Ebeveyn PID {parent_pid} bulunamadı!")

        parent = self.process_table[parent_pid]
        child_pid = self.next_pid
        self.next_pid += 1

        # 1. İşlemci Yazmaçlarını Klonla
        child_regs = parent.regs.clone()

        # 2. SİHİRLİ ÇEKİRDEK KURALI: Çocuğun RAX yazmacı SIFIRLANIR!
        child_regs.rax = 0

        # 3. Ebeveynin RAX yazmacına ÇOCUK PID yazılır!
        parent.regs.rax = child_pid

        # 4. Çocuk Süreç Nesnesini Oluştur
        child = SimulatedProcess(
            pid=child_pid,
            ppid=parent_pid,
            name=f"{parent.name}_child",
            registers=child_regs
        )

        # 5. Dosya Tanıtıcılarını Kopyala (Aynı struct file tablosunu paylaşırlar)
        child.open_files = dict(parent.open_files)

        self.process_table[child_pid] = child

        # Ebeveyn ve çocuğun fork() dönüş değerleri
        parent_return = parent.regs.rax
        child_return = child.regs.rax

        return parent_return, child_return

# Modül 1 Doğrulama
_fork_engine = KernelForkEngine()
_p_ret, _c_ret = _fork_engine.do_fork(parent_pid=100)

assert _p_ret == 101, f"Ebeveyn çocuk PID'sini (101) görmeli, alınan: {_p_ret}"
assert _c_ret == 0, f"Çocuk 0 değerini görmeli, alınan: {_c_ret}"
assert _fork_engine.process_table[101].ppid == 100, "Çocuğun ebeveyni 100 olmalı"
print(f"[Modül 1] fork() Başarılı: Ebeveyne Dönen={_p_ret}, Çocuğa Dönen={_c_ret}")


# Modül 2: Copy-on-Write (CoW) ve Donanımsal Page Fault (do_wp_page) Simülatörü

class PhysicalMemoryFrame:
    """Fiziksel RAM üzerindeki 4 KB'lık sayfa çerçevesi."""
    def __init__(self, frame_id: int, initial_data: bytes):
        self.frame_id = frame_id
        self.data = bytearray(initial_data)
        self.refcount = 1  # Kaç sürecin sayfa tablosunda bağlı?

class PageTableEntry:
    """MMU Sayfa Tablosu Girdisi (PTE)."""
    def __init__(self, frame_id: int, writeable: bool):
        self.frame_id = frame_id
        self.writeable = writeable  # R/W biti

class VirtualMemoryMMU:
    """MMU ve Çekirdek CoW Bellek Yöneticisi."""
    def __init__(self):
        self.frames: Dict[int, PhysicalMemoryFrame] = {}
        self.next_frame_id = 1
        self.page_fault_count = 0
        self.cow_copies_count = 0

    def allocate_page(self, data: bytes) -> int:
        """Yeni bir fiziksel sayfa tahsis eder."""
        fid = self.next_frame_id
        self.next_frame_id += 1
        self.frames[fid] = PhysicalMemoryFrame(fid, data)
        return fid

    def fork_page_table(self, parent_ptes: Dict[int, PageTableEntry]) -> Tuple[Dict[int, PageTableEntry], Dict[int, PageTableEntry]]:
        """
        fork() anında sayfa tablolarını kopyalar ve tüm sayfaları Salt-Okunur (CoW) yapar.
        """
        child_ptes: Dict[int, PageTableEntry] = {}
        for vpn, pte in parent_ptes.items():
            # Fiziksel sayfanın referansını artır
            self.frames[pte.frame_id].refcount += 1
            # EBEVEYNİ DE ÇOCUĞU DA SALT-OKUNUR YAP!
            pte.writeable = False
            child_ptes[vpn] = PageTableEntry(frame_id=pte.frame_id, writeable=False)

        return parent_ptes, child_ptes

    def write_memory(self, ptes: Dict[int, PageTableEntry], vpn: int, offset: int, byte_val: int) -> None:
        """
        Süreç belleğe yazmaya çalışır. Eğer writeable == False ise PAGE FAULT tetiklenir!
        """
        if vpn not in ptes:
            raise MemoryError("SIGSEGV: Geçersiz bellek adresi!")

        pte = ptes[vpn]

        if not pte.writeable:
            # DONANIMSAL SAYFA HATASI (PAGE FAULT) TETİKLENDİ!
            self.page_fault_count += 1
            old_frame = self.frames[pte.frame_id]

            if old_frame.refcount > 1:
                # Gerçek CoW Kopyalama: Yeni çerçeve oluştur ve veriyi kopyala
                self.cow_copies_count += 1
                new_fid = self.allocate_page(bytes(old_frame.data))
                old_frame.refcount -= 1
                
                # Bu sürecin PTE'sini yeni çerçeveye bağla ve yazılabilir yap
                pte.frame_id = new_fid
                pte.writeable = True
            else:
                # refcount == 1 ise tek kalan süreçtir; doğrudan yazılabilir yap
                pte.writeable = True

        # Belleğe yazma işlemini icra et
        target_frame = self.frames[pte.frame_id]
        target_frame.data[offset] = byte_val

# Modül 2 Test
_mmu = VirtualMemoryMMU()
_fid = _mmu.allocate_page(b"RADAR_COORDINATES_V1")
_parent_ptes = {0: PageTableEntry(_fid, writeable=True)}

# fork() yapılıyor: İki süreç aynı sayfayı salt-okunur paylaşır
_parent_ptes, _child_ptes = _mmu.fork_page_table(_parent_ptes)
assert _mmu.frames[_fid].refcount == 2, "Sayfa refcount 2 olmalı"
assert _parent_ptes[0].writeable == False, "Ebeveyn sayfası salt-okunur olmalı"
assert _child_ptes[0].writeable == False, "Çocuk sayfası salt-okunur olmalı"

# Çocuk sayfayı değiştiriyor -> CoW tetiklenmeli!
_mmu.write_memory(_child_ptes, vpn=0, offset=0, byte_val=ord('X'))

assert _mmu.page_fault_count == 1, "1 Page Fault oluşmalı"
assert _mmu.cow_copies_count == 1, "1 CoW kopyalama gerçekleşmeli"
assert _child_ptes[0].frame_id != _parent_ptes[0].frame_id, "Çocuk artık farklı fiziksel sayfaya sahip olmalı"
assert bytes(_mmu.frames[_child_ptes[0].frame_id].data).startswith(b"XADAR"), "Çocuk verisi güncellenmeli"
assert bytes(_mmu.frames[_parent_ptes[0].frame_id].data).startswith(b"RADAR"), "Ebeveyn verisi bozulmamalı!"
print(f"[Modül 2] CoW Başarılı! Ebeveyn ve Çocuk Fiziksel Belleği Ayrıştı.")


# Modül 3: Paylaşılan Dosya Ofseti ve pthread_atfork Kilit Güvenliği Motoru

class SharedFileDescription:
    """Linux çekirdeğindeki struct file yapısının simülasyonu."""
    def __init__(self, filename: str):
        self.filename = filename
        self.cursor_pos = 0  # Paylaşılan dosya ofseti (f_pos)
        self.buffer = bytearray()

    def write(self, data: bytes) -> int:
        self.buffer.extend(data)
        bytes_written = len(data)
        self.cursor_pos += bytes_written
        return bytes_written

class ThreadMutex:
    """Basit kilit simülasyonu."""
    def __init__(self, name: str):
        self.name = name
        self.locked = False
        self.owner_thread: Optional[int] = None

    def acquire(self, thread_id: int):
        if self.locked and self.owner_thread != thread_id:
            raise RuntimeError(f"DEADLOCK: Mutex {self.name} başka thread ({self.owner_thread}) tarafından kilitli!")
        self.locked = True
        self.owner_thread = thread_id

    def release(self):
        self.locked = False
        self.owner_thread = None

class AtForkManager:
    """pthread_atfork kilit senkronizasyon motoru."""
    def __init__(self, mutex: ThreadMutex):
        self.mutex = mutex

    def prepare(self):
        """fork öncesi: Kilidi garantiye al."""
        self.mutex.acquire(thread_id=0)

    def parent(self):
        """Ebeveyn bittiğinde: Kilidi serbest bırak."""
        self.mutex.release()

    def child(self):
        """Çocuk süreçte: Kilidi sıfırla."""
        self.mutex.release()

# Modül 3 Test: Dosya Ofseti Paylaşımı İspatı
_shared_file = SharedFileDescription("telemetry.log")
# Ebeveyn 10 bayt yazar
_shared_file.write(b"PARENT_10_")
assert _shared_file.cursor_pos == 10, "Ebeveyn imleci 10 yapmalı"

# Çocuk aynı dosya nesnesine yazar
_shared_file.write(b"CHILD_10__")
assert _shared_file.cursor_pos == 20, "Çocuk imleci 20'ye ilerletmeli (Ofset ortaktır!)"
assert bytes(_shared_file.buffer) == b"PARENT_10_CHILD_10__", "Veriler sıralı eklenmeli"
print(f"[Modül 3] Paylaşılan Dosya Ofseti Doğrulandı: Cursor={_shared_file.cursor_pos}")


# Modül 4: Sabotaj Senaryosu — Korumasız Fork Deadlock vs pthread_atfork Kalkanı

class ForkSabotageSimulation:
    """Multi-threaded fork deadlock sabotajı ve atfork kalkanını simüle eder."""
    def __init__(self):
        self.mutex = ThreadMutex("radar_telemetry_lock")
        self.atfork_mgr = AtForkManager(self.mutex)

    def run_unprotected_sabotage(self) -> Dict[str, any]:
        """Korumasız sistem: Başka bir iş parçacığı kilidi tutarken fork yapılıyor."""
        # Arka plan iş parçacığı (Thread 99) kilidi alıyor
        self.mutex.acquire(thread_id=99)
        
        # Ana thread (Thread 1) fork yapıyor...
        # Çocuk süreçte Thread 99 YOKTUR! Kilit kilitli kaldı!
        child_deadlocked = False
        try:
            # Çocuk süreç kilidi almaya çalışıyor
            self.mutex.acquire(thread_id=1)
        except RuntimeError as e:
            child_deadlocked = True

        # Temizlik
        self.mutex.release()

        return {
            "deadlocked": child_deadlocked,
            "reason": "Kilit sahibi iş parçacığı çocuk süreçte kopyalanmadığı için kilit sahipsiz kaldı!"
        }

    def run_hardened_defense(self) -> Dict[str, any]:
        """Sertleştirilmiş sistem: pthread_atfork ile kilit senkronizasyonu."""
        # 1. prepare(): fork öncesi ana thread kilidi alır
        self.atfork_mgr.prepare()
        
        # 2. fork gerçekleşti...
        
        # 3. child(): Çocuk süreçte kilit temizlenir
        self.atfork_mgr.child()
        
        # 4. Çocuk süreç artık kilidi sorunsuz alabilir!
        child_acquired_successfully = False
        try:
            self.mutex.acquire(thread_id=1)
            child_acquired_successfully = True
            self.mutex.release()
        except RuntimeError:
            child_acquired_successfully = False

        return {
            "deadlocked": not child_acquired_successfully,
            "success": child_acquired_successfully,
            "protection": "pthread_atfork kalkanı kilidi çocukta güvenle sıfırladı."
        }

_sim = ForkSabotageSimulation()
_res_unprotected = _sim.run_unprotected_sabotage()
_res_hardened = _sim.run_hardened_defense()

assert _res_unprotected["deadlocked"] == True, "Korumasız sistem deadlock olmalı!"
assert _res_hardened["deadlocked"] == False, "Sertleştirilmiş sistem kilitlenmemeli!"
print(f"[Sabotaj Testi] Korumasız Deadlock: {_res_unprotected['deadlocked']}")
print(f"[Savunma Testi] AtFork Koruması Başarılı: {_res_hardened['success']}")


# Modül 5: Ampirik Kıyaslama ve Yüksek Çözünürlüklü fork / CoW Benchmark Motoru
import time
import numpy as np

def run_benchmarks(iterations: int = 3000) -> Dict[str, any]:
    """fork() çağrısı ve CoW Page Fault gecikmelerini ampirik olarak ölçer."""
    fork_engine = KernelForkEngine()
    mmu = VirtualMemoryMMU()
    
    # 50 sayfalık temsili bir bellek alanı oluştur
    ptes = {}
    for vpn in range(50):
        fid = mmu.allocate_page(b"A" * 4096)
        ptes[vpn] = PageTableEntry(fid, writeable=True)

    latencies_fork = []
    latencies_cow_fault = []

    for _ in range(iterations):
        # 1. fork() sistem çağrısı süresi
        t0 = time.perf_counter_ns()
        p_ret, c_ret = fork_engine.do_fork(parent_pid=100)
        t1 = time.perf_counter_ns()
        latencies_fork.append(t1 - t0)

        # 2. Sayfa tablosunu CoW yap
        parent_p, child_p = mmu.fork_page_table(ptes)

        # 3. CoW Page Fault (İlk Yazma) süresi
        t0 = time.perf_counter_ns()
        mmu.write_memory(child_p, vpn=0, offset=10, byte_val=ord('Z'))
        t1 = time.perf_counter_ns()
        latencies_cow_fault.append(t1 - t0)

    def calc_stats(lat_list):
        arr = np.array(lat_list, dtype=np.float64)
        return {
            "mean": float(np.mean(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "raw": arr
        }

    return {
        "fork": calc_stats(latencies_fork),
        "cow_fault": calc_stats(latencies_cow_fault),
        "iterations": iterations
    }

_bench_res = run_benchmarks(iterations=2000)
print(f"[Benchmark] {_bench_res['iterations']} İterasyon Ölçüldü.")
print(f"  fork() Mean:     {_bench_res['fork']['mean']:.2f} ns (p95: {_bench_res['fork']['p95']:.2f} ns)")
print(f"  CoW Fault Mean:  {_bench_res['cow_fault']['mean']:.2f} ns (p95: {_bench_res['cow_fault']['p95']:.2f} ns)")


# Modül 6: 4-Panelli Yayın Kalitesinde Dashboard Üretimi ve Katı Assert Doğrulaması
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DEFAULT_PNG = "gun_086_fork_zihinsel_modeli.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    """Yayın kalitesinde 4-panelli görselleştirme paneli üretir."""
    fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    bench_data = run_benchmarks(iterations=2000)

    # Ortak Stil Fonksiyonu
    def style_ax(ax, title, xlabel, ylabel):
        ax.set_facecolor('#1E293B')
        ax.set_title(title, fontsize=12, fontweight='bold', color='#38BDF8', pad=10)
        ax.set_xlabel(xlabel, fontsize=10, fontweight='bold', color='#94A3B8')
        ax.set_ylabel(ylabel, fontsize=10, fontweight='bold', color='#94A3B8')
        ax.tick_params(colors='#CBD5E1', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#334155')
            spine.set_linewidth(1.2)
        ax.grid(True, linestyle='--', alpha=0.25, color='#64748B')

    # -------------------------------------------------------------
    # PANEL 1: CoW Bellek Ayrışması (Paylaşılan vs Ayrık Sayfalar)
    # -------------------------------------------------------------
    ax1 = axs[0, 0]
    style_ax(ax1, "Panel 1: CoW Öncesi ve Sonrası Bellek Dağılımı", 
             "Bellek Durumu", "Fiziksel Sayfa Sayısı (Pages)")
    
    states = ['fork() Anı\n(0 Yazma)', 'Kısmi Yazma\n(10 Sayfa)', 'Tam Ayrışma\n(50 Sayfa)']
    shared_pages = [50, 40, 0]
    copied_pages = [0, 10, 50]
    
    x = np.arange(len(states))
    w = 0.4
    
    b1 = ax1.bar(x, shared_pages, width=w, label='Ortak Sayfalar (ref=2)', color='#0EA5E9', edgecolor='#334155')
    b2 = ax1.bar(x, copied_pages, width=w, bottom=shared_pages, label='Klonlanan Sayfalar (ref=1)', color='#EF4444', edgecolor='#334155')
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(states, fontweight='bold')
    ax1.set_ylim(0, 65)
    ax1.legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=8)

    # -------------------------------------------------------------
    # PANEL 2: fork() ve CoW Page Fault Gecikmeleri (Boxplot)
    # -------------------------------------------------------------
    ax2 = axs[0, 1]
    style_ax(ax2, "Panel 2: fork() Klonlama vs CoW Page Fault Gecikmesi", 
             "İşlem Türü", "Gecikme (Nanosaniye - ns)")
    
    ops = ['fork() Klonlama', 'CoW Page Fault']
    data_plot = [
        bench_data['fork']['raw'][:1000],
        bench_data['cow_fault']['raw'][:1000]
    ]
    
    bp = ax2.boxplot(data_plot, patch_artist=True, showmeans=True,
                     boxprops=dict(facecolor='#0284C7', color='#38BDF8'),
                     capprops=dict(color='#94A3B8'),
                     whiskerprops=dict(color='#64748B'),
                     flierprops=dict(marker='o', markerfacecolor='#F43F5E', markersize=3, alpha=0.4),
                     medianprops=dict(color='#F59E0B', linewidth=2),
                     meanprops=dict(marker='^', markerfacecolor='#10B981', markeredgecolor='#10B981'))
    
    ax2.set_xticks([1, 2])
    ax2.set_xticklabels(ops, fontweight='bold')
    ax2.set_yscale('log')
    
    means = [bench_data['fork']['mean'], bench_data['cow_fault']['mean']]
    for i, m in enumerate(means, 1):
        ax2.text(i, m * 1.25, f"Ort: {m:.0f}ns", ha='center', color='#38BDF8', fontsize=8, fontweight='bold')

    # -------------------------------------------------------------
    # PANEL 3: Sabotaj Senaryosu (Deadlock vs atfork Koruması)
    # -------------------------------------------------------------
    ax3 = axs[1, 0]
    style_ax(ax3, "Panel 3: Multi-Thread Fork Kilitlenme Oranı", 
             "Koruma Stratejisi", "Kilitlenme (Deadlock) Oranı (%)")
    
    strats = ['Korumasız Fork\n(Mutex Sahipsiz)', 'pthread_atfork\n(Kilit Temizleme)']
    d_rates = [100.0, 0.0]
    bar_colors = ['#EF4444', '#10B981']
    
    bars3 = ax3.bar(strats, d_rates, color=bar_colors, edgecolor='#334155', width=0.45)
    ax3.set_ylim(0, 115)
    
    ax3.text(0, 103, "%100 KİLİTLENME!", ha='center', color='#EF4444', fontweight='bold', fontsize=9)
    ax3.text(1, 5, "%0 GÜVENLİ (PASS)", ha='center', color='#10B981', fontweight='bold', fontsize=9)

    # -------------------------------------------------------------
    # PANEL 4: Paylaşılan Dosya Ofseti İlerlemesi
    # -------------------------------------------------------------
    ax4 = axs[1, 1]
    style_ax(ax4, "Panel 4: Ebeveyn ve Çocuk Ortak Dosya İmleci İlerlemesi", 
             "Yazma Sırası (İşlem No)", "Dosya İmleci Konumu (Bayt)")
    
    ops_seq = list(range(1, 9))
    # Ebeveyn ve çocuğun ardışık yazmaları
    cursor_progression = [10, 20, 30, 40, 50, 60, 70, 80]
    
    ax4.plot(ops_seq, cursor_progression, marker='s', color='#F59E0B', linewidth=2.5, label='Paylaşılan f_pos')
    ax4.scatter([1, 3, 5, 7], [10, 30, 50, 70], color='#38BDF8', s=80, zorder=5, label='Ebeveyn Yazdı')
    ax4.scatter([2, 4, 6, 8], [20, 40, 60, 80], color='#10B981', s=80, zorder=5, label='Çocuk Yazdı')
    
    ax4.set_xticks(ops_seq)
    ax4.legend(loc='upper left', facecolor='#1E293B', edgecolor='#334155', fontsize=8)

    plt.suptitle("ASELSAN / HAVELSAN Görev Sistemleri: fork() Zihinsel Modeli ve CoW Mimarisi", 
                 fontsize=15, fontweight='bold', color='#F8FAFC', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_png_path}")

def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Tüm fork() ve CoW mekanizmalarını katı assert koşullarıyla denetler."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. fork() Çift Dönüş Doğrulaması
    engine = KernelForkEngine()
    p_val, c_val = engine.do_fork(parent_pid=100)
    assert p_val == 101, "Ebeveyn dönüş değeri çocuk PID olmalı"
    assert c_val == 0, "Çocuk dönüş değeri 0 olmalı"

    # 2. CoW Page Fault Doğrulaması
    mmu = VirtualMemoryMMU()
    fid = mmu.allocate_page(b"ORIGINAL_DATA")
    p_ptes = {0: PageTableEntry(fid, writeable=True)}
    p_ptes, c_ptes = mmu.fork_page_table(p_ptes)
    
    assert mmu.frames[fid].refcount == 2, "fork sonrası refcount 2 olmalı"
    assert p_ptes[0].writeable == False, "Sayfalar salt-okunur kilitlenmeli"
    
    # Yazma tetikle
    mmu.write_memory(c_ptes, vpn=0, offset=0, byte_val=ord('N'))
    assert mmu.page_fault_count == 1, "Page fault tetiklenmeli"
    assert c_ptes[0].frame_id != p_ptes[0].frame_id, "Çocuk yeni çerçeveye ayrışmalı"

    # 3. Paylaşılan Ofset Doğrulaması
    sfile = SharedFileDescription("test.bin")
    sfile.write(b"ABC")
    sfile.write(b"DEF")
    assert sfile.cursor_pos == 6, "Ofset ortak ilerlemeli"

    # 4. atfork Deadlock Kalkanı Doğrulaması
    sim = ForkSabotageSimulation()
    res_sab = sim.run_unprotected_sabotage()
    res_def = sim.run_hardened_defense()
    assert res_sab["deadlocked"] == True, "Korumasız multi-threaded fork deadlock olmalı"
    assert res_def["deadlocked"] == False, "atfork ile kilitlenme engellenmeli"

    # 5. PNG Görsel Dosya Kontrolü
    if os.path.exists(png_path):
        size = os.path.getsize(png_path)
        assert size > 50000, f"PNG dosyası çok küçük veya bozuk ({size} bayt)"

    print("[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")

if __name__ == "__main__":
    out_png = "gun_086_fork_zihinsel_modeli.png"
    generate_dashboard(out_png)
    verify_all_assertions(out_png)
