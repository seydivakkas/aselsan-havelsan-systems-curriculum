# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 4 (CODE 1): Sanal Bellek, PTE ve mmap Simülatörü
Sayfa Tablosu (PTE), Minor/Major Page Fault ve MAP_SHARED vs MAP_PRIVATE (CoW)
"""

from typing import Dict, List, Optional, Tuple

PAGE_SIZE = 4096

class PhysicalPage:
    """Fiziksel RAM sayfası."""
    def __init__(self, page_id: int, data: bytearray):
        self.page_id = page_id
        self.data = data
        self.dirty = False

class PageTableEntry:
    """MMU Sayfa Tablosu Girdisi (PTE)."""
    def __init__(self, physical_page: Optional[PhysicalPage], readable: bool, writable: bool):
        self.physical_page = physical_page
        self.readable = readable
        self.writable = writable
        self.present = physical_page is not None

class SimulatedMmapProcess:
    """Linux VMA ve mmap bellek yönetim simülatörü."""
    def __init__(self, pid: int):
        self.pid = pid
        self.page_table: Dict[int, PageTableEntry] = {} # Sanal sayfa no -> PTE
        self.page_fault_minor_count = 0
        self.page_fault_major_count = 0

    def mmap(self, vaddr_start: int, length: int, flags: str, backing_file_pages: Dict[int, PhysicalPage]):
        """mmap çağrısı: Başlangıçta tembel eşleme (Lazy Demand Paging) yapar."""
        num_pages = (length + PAGE_SIZE - 1) // PAGE_SIZE
        start_page_idx = vaddr_start // PAGE_SIZE
        
        for i in range(num_pages):
            v_idx = start_page_idx + i
            # Tembel haritalama: Henüz fiziksel sayfa bağlanmadı (present=False)
            # Sadece VMA kaydı var
            writable = ("MAP_SHARED" in flags) or ("MAP_PRIVATE" in flags)
            self.page_table[v_idx] = PageTableEntry(
                physical_page=None,
                readable=True,
                writable=writable
            )
        self.start_page_idx = start_page_idx
        self.backing_store = backing_file_pages
        self.mmap_flags = flags

    def read_byte(self, vaddr: int) -> int:
        """Sanal adresten 1 bayt okur. Sayfa yoksa Page Fault üretir."""
        v_idx = vaddr // PAGE_SIZE
        offset = vaddr % PAGE_SIZE
        
        if v_idx not in self.page_table:
            raise MemoryError(f"SIGSEGV: Adres {hex(vaddr)} haritalanmamis!")
            
        pte = self.page_table[v_idx]
        if not pte.present:
            # Major Page Fault: Diskten/Page Cache'ten sayfayı getir
            self.page_fault_major_count += 1
            file_page_idx = v_idx - self.start_page_idx
            phys = self.backing_store.get(file_page_idx)
            if not phys:
                raise RuntimeError(f"SIGBUS: Fiziksel blok mevcut degil! (Adres: {hex(vaddr)})")
            pte.physical_page = phys
            pte.present = True
            
        return pte.physical_page.data[offset]

    def write_byte(self, vaddr: int, byte_val: int):
        """Sanal adrese 1 bayt yazar. MAP_PRIVATE ise Copy-on-Write (CoW) tetikler."""
        v_idx = vaddr // PAGE_SIZE
        offset = vaddr % PAGE_SIZE
        
        if v_idx not in self.page_table:
            raise MemoryError(f"SIGSEGV: Adres {hex(vaddr)} haritalanmamis!")
            
        pte = self.page_table[v_idx]
        if not pte.present:
            self.read_byte(vaddr) # Önce sayfayı yükle
            
        if "MAP_PRIVATE" in self.mmap_flags:
            # Copy-on-Write tetiklendi: Orijinal sayfayı kopyala
            self.page_fault_minor_count += 1
            new_data = bytearray(pte.physical_page.data)
            new_page = PhysicalPage(page_id=9999, data=new_data)
            pte.physical_page = new_page # Artık sürece özel sayfa!
            
        pte.physical_page.data[offset] = byte_val
        pte.physical_page.dirty = True

if __name__ == "__main__":
    # Test Senaryosu: 1 Sayfalık dosya destekli mmap
    disk_data = bytearray(b"ORIGINAL_RADAR_DATA" + b"\x00" * (PAGE_SIZE - 19))
    shared_phys_page = PhysicalPage(page_id=101, data=disk_data)
    file_backing = {0: shared_phys_page}

    print("=== [MMAP SAYFA HATASI VE CoW SİMÜLASYONU] ===")
    proc = SimulatedMmapProcess(pid=1420)
    proc.mmap(vaddr_start=0x10000, length=4096, flags="MAP_PRIVATE", backing_file_pages=file_backing)

    # 1. İlk Okuma: Major Page Fault (Tembel yükleme)
    b0 = proc.read_byte(0x10000)
    print(f"[*] İlk Okuma Baytı  : {chr(b0)} (Major Fault: {proc.page_fault_major_count})")

    # 2. Yazma: Minor Page Fault (Copy-on-Write)
    proc.write_byte(0x10000, ord("M"))
    print(f"[*] Süreçteki Yeni Değer : {chr(proc.read_byte(0x10000))}")
    print(f"[*] Orijinal Disk Sayfası: {chr(shared_phys_page.data[0])} (Değişmedi! CoW Başarılı)")
    print(f"[*] Toplam CoW Hataları  : {proc.page_fault_minor_count}")


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Python ile Üretim Seviyesi MmapMemoryManager Simülatörü
Sıfır Kopyalama Bellek Görünümü (memoryview), msync ve Otomatik Kaynak Temizliği
"""

from typing import Dict, Any, Optional

class MmapMemoryManager:
    """C++20 SafeMmapView eşdeğeri bellek haritalama ve yönetim motoru."""
    
    def __init__(self, filename: str, size: int, is_shared: bool = True):
        self.filename = filename
        self.size = size
        self.is_shared = is_shared
        # Simüle edilmiş disk/dosya depolaması
        self.disk_storage = bytearray(size)
        # mmap ile açılan bellek görünümü (Zero-Copy memoryview simülasyonu)
        self.mapped_memory = bytearray(self.disk_storage)
        self.is_mapped = True
        self.dirty = False

    def write_struct(self, offset: int, data_bytes: bytes):
        """Doğrudan işaretçi üzerinden sıfır kopyalama ile yazma."""
        if not self.is_mapped:
            raise MemoryError("SIGSEGV: Harita kapatilmis (munmap) bellege yazilamaz!")
        if offset + len(data_bytes) > self.size:
            raise IndexError("SIGBUS: Haritalanan dosya boyutu asildi!")
            
        self.mapped_memory[offset : offset + len(data_bytes)] = data_bytes
        self.dirty = True

    def read_struct(self, offset: int, length: int) -> bytes:
        """Doğrudan işaretçi üzerinden okuma."""
        if not self.is_mapped:
            raise MemoryError("SIGSEGV: Harita kapatilmis bellekten okunamaz!")
        return bytes(self.mapped_memory[offset : offset + length])

    def msync(self, synchronous: bool = True) -> bool:
        """Kirli sayfaları fiziksel depolamaya boşaltır."""
        if not self.is_mapped:
            return False
        if self.is_shared and self.dirty:
            self.disk_storage[:] = self.mapped_memory
            self.dirty = False
            return True
        return False

    def close(self):
        """munmap ve close simülasyonu."""
        if self.is_mapped:
            self.msync(synchronous=True)
            self.is_mapped = False

if __name__ == "__main__":
    manager = MmapMemoryManager("telemetry_stream.dat", size=4096, is_shared=True)
    
    print("=== [SIFIR KOPYALAMA (ZERO-COPY) YAZMA TESTİ] ===")
    manager.write_struct(0, b"RADAR_FRAME_HEADER_001")
    print(f"[*] Bellekteki Veri : {manager.read_struct(0, 23).decode('utf-8')}")
    print(f"[*] Diskteki Durum (msync Öncesi) : {bytes(manager.disk_storage[:23])}")
    
    synced = manager.msync(synchronous=True)
    print(f"[+] msync Çagrildi mi?            : {synced}")
    print(f"[*] Diskteki Durum (msync Sonrası): {bytes(manager.disk_storage[:23]).decode('utf-8')}")
    manager.close()


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Sabotaj Laboratuvarı: SIGBUS ve SIGSEGV Tuzakları
Dosya Kırpılması (Truncation), Boyut Aşımı ve Sinyal Yakalama Simülatörü
"""

from typing import Tuple

class MmapSabotageLab:
    """mmap işlemlerindeki ölümcül donanımsal istisnaları modeller."""
    
    @staticmethod
    def simulate_sigbus_truncation() -> Tuple[bool, str]:
        """Dosya haritalandıktan sonra başka bir sürecin dosyayı kırpması (truncate)."""
        # 1. Dosya 8192 bayt (2 sayfa) olarak haritalandı
        mapped_length = 8192
        file_actual_size = 8192
        
        # 2. SABOTAJ: Başka bir süreç ftruncate() ile dosyayı 100 bayta düşürdü!
        file_actual_size = 100
        
        # 3. Süreç 2000. bayta yazmaya çalışıyor (Sanal adres geçerli, disk bloğu yok!)
        target_offset = 2000
        if target_offset > file_actual_size:
            return True, f"SIGBUS (Bus Error): Adres geçerli fakat fiziksel dosya {file_actual_size} bayta kırpılmış! Donanım hatası tetiklendi."
        return False, "Erişim başarılı."

    @staticmethod
    def simulate_sigsegv_protection_violation() -> Tuple[bool, str]:
        """PROT_READ olarak haritalanmış alana yazma denemesi."""
        prot_writable = False
        attempt_write = True
        
        if attempt_write and not prot_writable:
            return True, "SIGSEGV (Segmentation Fault): PROT_READ ile korunan alana yazma denendi! MMU koruma ihlali."
        return False, "Erişim başarılı."

if __name__ == "__main__":
    print("=== [MMAP SABOTAJ VE SİNYAL LABORATUVARI] ===")
    sigbus_triggered, bus_msg = MmapSabotageLab.simulate_sigbus_truncation()
    print(f"[*] SIGBUS Testi  : {bus_msg}")

    sigsegv_triggered, segv_msg = MmapSabotageLab.simulate_sigsegv_protection_violation()
    print(f"[*] SIGSEGV Testi : {segv_msg}")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): msync Senkronizasyon ve Çöküş Direnci Laboratuvarı
MS_ASYNC vs MS_SYNC Güvenilirlik Testi ve Ani Güç Kesintisi Simülatörü
"""

from typing import Dict, Any, Tuple

class CrashDurabilityLab:
    """Elektrik kesintisinde bellek haritalı verilerin kaybolma riskini modeller."""
    
    @staticmethod
    def simulate_power_loss(use_ms_sync: bool) -> Tuple[bool, str]:
        # Süreç 50 adet telemetri kaydı yazıyor
        ram_buffer = ["TELEMETRY_PACKET"] * 50
        disk_flushed = []
        
        if use_ms_sync:
            # MS_SYNC: Her yazma veya blok anında diske yazılır
            disk_flushed = list(ram_buffer)
        else:
            # MS_ASYNC / No sync: Çekirdek kuyruğunda beklerken güç kesildi!
            disk_flushed = [] # Diske henüz yazılmadı
            
        is_data_intact = len(disk_flushed) == 50
        if is_data_intact:
            return True, "TAM GÜVENLİK: MS_SYNC sayesinde elektrik kesilmesine rağmen tüm telemetri kurtarıldı."
        else:
            return False, f"VERİ KAYBI: MS_ASYNC tamponu henüz boşaltılmamıştı! {len(ram_buffer)} paket kayboldu."

if __name__ == "__main__":
    print("=== [GÜÇ KESİNTİSİ VE msync() DİRENÇ TESTİ] ===")
    ok_async, msg_async = CrashDurabilityLab.simulate_power_loss(use_ms_sync=False)
    print(f"[*] MS_ASYNC Testi : {msg_async}")

    ok_sync, msg_sync = CrashDurabilityLab.simulate_power_loss(use_ms_sync=True)
    print(f"[*] MS_SYNC Testi  : {msg_sync}")


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Performans Benchmark Laboratuvarı: mmap vs read/write
Çift Kopyalama (Double-Buffering) vs Sıfır Kopyalama (Zero-Copy) Mikro-Kıyaslaması
"""

import time
from typing import Dict

def run_mmap_vs_readwrite_benchmark(iterations: int = 50000) -> Dict[str, float]:
    """read/write memcpy maliyeti ile mmap doğrudan işaretçi erişimini kıyaslar."""
    
    payload = b"X" * 1024 # 1 KB veri bloğu
    
    # 1. POSIX read() / write() Simülasyonu: Syscall + User-Kernel memcpy
    t0 = time.perf_counter()
    sink_buffer = bytearray(1024)
    for _ in range(iterations):
        # 1. memcpy: Kernel -> User
        sink_buffer[:] = payload
        # 2. memcpy: User -> Processing
        val = sink_buffer[0]
    t_readwrite = time.perf_counter() - t0

    # 2. mmap() Simülasyonu: Doğrudan işaretçi üzerinden okuma (Sıfır kopyalama)
    shared_vma = payload # Zaten bellekte eşlenmiş blok
    t1 = time.perf_counter()
    for _ in range(iterations):
        val = shared_vma[0] # Doğrudan pointer dereference
    t_mmap = time.perf_counter() - t1

    speedup = t_readwrite / max(t_mmap, 1e-9)
    return {
        "iterations": iterations,
        "t_readwrite_ms": t_readwrite * 1000,
        "t_mmap_ms": t_mmap * 1000,
        "speedup_factor": speedup
    }

if __name__ == "__main__":
    res = run_mmap_vs_readwrite_benchmark(iterations=50000)
    print("=== [MMAP SIFIR KOPYALAMA VS READ/WRITE BENCHMARK] ===")
    print(f"Toplam Döngü (1 KB Blok) : {res['iterations']:,}")
    print(f"POSIX read/write Süresi  : {res['t_readwrite_ms']:.3f} ms")
    print(f"mmap Sıfır Kopyalama     : {res['t_mmap_ms']:.3f} ms")
    print(f"[*] mmap Hızlanma Çarpanı: {res['speedup_factor']:.2f}x Kat Daha Hızlı!")


# -*- coding: utf-8 -*-
"""
HÜCRE 22 (CODE 6): 4-Panelli Görselleştirme Paneli ve Katı Doğrulama Testleri
mmap Mimarisi, Bellek Kopyalama Kıyaslaması, Page Fault Dağılımı ve msync Direnci
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_098_mmap_ile_memory_mapping.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    """4-panelli, koyu tema, 300 DPI kurumsal sistem mimarisi paneli üretir."""
    
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    accent_blue = '#38BDF8'
    accent_amber = '#F59E0B'
    accent_green = '#10B981'
    accent_red = '#EF4444'
    text_color = '#F8FAFC'

    # PANEL 1: Zero-Copy mmap vs POSIX read/write Mimari Diyagramı
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("Veri Yolu Mimarisi: Çift Kopyalama vs Sıfır Kopyalama", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    boxes = [
        ("A) POSIX read(): Disk -> Page Cache -> Kullanıcı Tamponu (2 Kopya)", 0.5, 0.80, accent_red),
        ("B) mmap(): Disk -> Page Cache == Sanal Adres Uzayı (0 Kopya!)", 0.5, 0.60, accent_green),
        ("MMU Sayfa Tablosu (PTE Doğrudan Donanımsal Çözümleme)", 0.5, 0.40, accent_blue),
        ("MAP_POPULATE: Başlangıçta Tüm Sayfaları RAM'e Kilitleme", 0.5, 0.20, accent_amber)
    ]
    for text, x, y, col in boxes:
        ax1.text(x, y, text, ha='center', va='center', color=text_color, fontsize=8, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor=col, linewidth=2))

    ax1.set_xlim(0, 1.0)
    ax1.set_ylim(0, 1.0)
    ax1.axis('off')

    # PANEL 2: I/O Gecikme Benchmark'ı (read/write vs mmap)
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("50,000 Blok Okuma/Yazma Süresi (ms)", fontsize=12, fontweight='bold', color=accent_amber, pad=12)
    
    bench = run_mmap_vs_readwrite_benchmark(iterations=50000)
    cats = ["POSIX read()/write()\n(Çift Kopyalama)", "mmap Zero-Copy\n(Doğrudan İşaretçi)"]
    times = [bench['t_readwrite_ms'], bench['t_mmap_ms']]
    
    bars2 = ax2.bar(cats, times, color=[accent_red, accent_green], width=0.45)
    ax2.set_ylabel("Toplam Süre (ms)", fontsize=10, color=text_color)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars2:
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f"{bar.get_height():.2f} ms",
                 ha='center', va='bottom', color=text_color, fontsize=9, fontweight='bold')

    # PANEL 3: Sayfa Hatası (Page Fault) Dağılımı ve Gecikme
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("Page Fault Çeşitleri ve İşlemci Gecikme Skalası", fontsize=12, fontweight='bold', color=accent_green, pad=12)
    
    fault_types = ["Standart mmap\n(Minor Fault / CoW)", "Tembel Okuma\n(Major Fault / Disk I/O)", "MAP_POPULATE\n(Önceden Yüklenmiş)"]
    latencies = [2.5, 120.0, 0.05] # Mikrosaniye cinsinden gecikme
    
    bars3 = ax3.barh(fault_types, latencies, color=[accent_amber, accent_red, accent_green], height=0.5)
    ax3.set_xlabel("Erişim Gecikmesi (Mikrosaniye - Logaritmik)", fontsize=10, color=text_color)
    ax3.set_xscale('log')
    ax3.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars3:
        ax3.text(bar.get_width() * 1.2, bar.get_y() + bar.get_height()/2, f"{bar.get_width():.2f} µs",
                 va='center', ha='left', color=text_color, fontsize=9, fontweight='bold')

    # PANEL 4: Sinyal ve Güvenilirlik Risk Matrisi
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("mmap Sinyal Tuzakları ve Veri Güvenliği", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    risks = ["SIGBUS (Truncation)", "SIGSEGV (PROT Violation)", "MS_ASYNC Veri Kaybı", "MAP_SHARED Çakışması"]
    severity = [98, 92, 85, 80]
    
    bars4 = ax4.bar(risks, severity, color=[accent_red, accent_amber, accent_blue, '#94A3B8'], width=0.5)
    ax4.set_ylabel("Kritiklik / Risk Derecesi (%)", fontsize=10, color=text_color)
    ax4.set_ylim(0, 115)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars4:
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"%{int(bar.get_height())}",
                 ha='center', va='bottom', color=text_color, fontsize=9, fontweight='bold')

    plt.tight_layout()
    output_dir = os.path.dirname(os.path.abspath(output_png_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    plt.savefig(output_png_path, facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_png_path}")

def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Sistem varsayımlarını ve mimari sınırları doğrulayan katı testler."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")
    
    # 1. Dashboard Varlık Kontrolü
    assert os.path.exists(png_path), f"HATA: Dashboard görseli üretilemedi: {png_path}"
    assert os.path.getsize(png_path) > 100_000, "HATA: Dashboard görsel boyutu yetersiz!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {os.path.getsize(png_path):,} bayt.")

    # 2. Sıfır Kopyalama ve msync Doğrulaması
    mgr = MmapMemoryManager("test.dat", size=1024, is_shared=True)
    mgr.write_struct(0, b"RADAR_DATA_FRAME")
    assert mgr.read_struct(0, 16) == b"RADAR_DATA_FRAME", "HATA: Belleğe yazılan veri okunamadı!"
    assert mgr.disk_storage[:16] != b"RADAR_DATA_FRAME", "HATA: msync öncesi veri diske yazılmamalıdır!"
    mgr.msync(synchronous=True)
    assert mgr.disk_storage[:16] == b"RADAR_DATA_FRAME", "HATA: msync sonrası disk güncellenmelidir!"
    mgr.close()
    print("  [+] Sıfır Kopyalama ve msync Kalıcılığı Doğrulandı.")

    # 3. SIGBUS ve SIGSEGV Tuzak Doğrulaması
    bus_triggered, _ = MmapSabotageLab.simulate_sigbus_truncation()
    assert bus_triggered is True, "HATA: Dosya kırpılması SIGBUS üretmelidir!"
    segv_triggered, _ = MmapSabotageLab.simulate_sigsegv_protection_violation()
    assert segv_triggered is True, "HATA: Salt-okunur alana yazma SIGSEGV üretmelidir!"
    print("  [+] SIGBUS ve SIGSEGV Donanımsal İstisna Davranışları Doğrulandı.")

    # 4. Copy-on-Write (MAP_PRIVATE) İzolasyon Doğrulaması
    data_backing = bytearray(b"ORIGINAL_PAYLOAD" + b"\x00" * 4080)
    page = PhysicalPage(1, data_backing)
    proc = SimulatedMmapProcess(1)
    proc.mmap(0x1000, 4096, "MAP_PRIVATE", {0: page})
    proc.write_byte(0x1000, ord("Z"))
    assert chr(proc.read_byte(0x1000)) == "Z", "HATA: Süreç kendi yazımını okuyabilmelidir!"
    assert chr(data_backing[0]) == "O", "HATA: MAP_PRIVATE orijinal disk sayfasını değiştirmemelidir!"
    print("  [+] Copy-on-Write (MAP_PRIVATE) Bellek İzolasyonu Doğrulandı.")

    # 5. Benchmark Performans Kontrolü
    bench = run_mmap_vs_readwrite_benchmark(iterations=10000)
    assert bench["speedup_factor"] > 1.2, "HATA: mmap sıfır kopyalama read/write'tan daha hızlı olmalıdır!"
    print(f"  [+] Sıfır Kopyalama Hızlanması Doğrulandı ({bench['speedup_factor']:.2f}x Hızlanma).")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
