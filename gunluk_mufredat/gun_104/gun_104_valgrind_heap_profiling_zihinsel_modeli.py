# -*- coding: utf-8 -*-
# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
# amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz.


# -*- coding: utf-8 -*-
"""
HÜCRE 04 (CODE 1): Python ile Valgrind Gölge Bellek (Shadow Memory) ve Sızıntı Motoru
A-bitleri (Adreslenebilirlik), V-bitleri (İlklendirme) ve Sızıntı Taksonomisi Simülasyonu
"""

from typing import Dict, List, Any, Optional, Set

class ShadowByte:
    """Gölge Bellek hücresi: Gerçek 1 baytın A ve V durumunu tutar."""
    def __init__(self):
        self.addressable: bool = False # A-biti: True ise geçerli tahsis
        self.initialized: bool = False # V-biti: True ise değer atanmış
        self.payload: int = 0

class SimulatedShadowMemory:
    """Valgrind DBI sanal makinesi bellek denetleyicisi."""
    def __init__(self):
        self.memory: Dict[int, ShadowByte] = {}
        self.allocations: Dict[int, int] = {} # ptr -> size
        self.root_pointers: Set[int] = set() # Global / Stack işaretçileri
        self.errors: List[str] = []

    def malloc(self, address: int, size: int) -> int:
        """malloc(): Bellek adreslenebilir olur (A=1) ama ilklendirilmemiştir (V=0)."""
        self.allocations[address] = size
        for addr in range(address, address + size):
            b = ShadowByte()
            b.addressable = True
            b.initialized = False
            self.memory[addr] = b
        return address

    def free(self, address: int):
        """free(): Bellek artık adreslenemez (A=0). UAF takibi başlar."""
        if address not in self.allocations:
            self.errors.append(f"Invalid free(): {hex(address)} geçerli bir tahsis değil veya Double Free!")
            return
            
        size = self.allocations.pop(address)
        for addr in range(address, address + size):
            if addr in self.memory:
                self.memory[addr].addressable = False # A-biti sıfırlandı!

    def write_byte(self, address: int, val: int):
        """Belleğe yazma: A-biti kontrol edilir, V-biti 1 yapılır."""
        if address not in self.memory or not self.memory[address].addressable:
            self.errors.append(f"Invalid write of size 1 at address {hex(address)} (Use-After-Free veya Heap Overflow)!")
            return
        self.memory[address].payload = val
        self.memory[address].initialized = True # Artık başlatıldı

    def read_byte(self, address: int) -> int:
        """Bellekten okuma: A-biti ve V-biti doğrulanır."""
        if address not in self.memory or not self.memory[address].addressable:
            self.errors.append(f"Invalid read of size 1 at address {hex(address)} (Use-After-Free veya Out-of-Bounds)!")
            return 0
        if not self.memory[address].initialized:
            self.errors.append(f"Uninitialised value read at address {hex(address)} (V-bit is False)!")
        return self.memory[address].payload

    def classify_leaks(self) -> Dict[str, int]:
        """Program sonlandığında sızıntı taksonomisini hesaplar."""
        definitely_lost = 0
        still_reachable = 0

        for ptr, size in self.allocations.items():
            if ptr in self.root_pointers:
                still_reachable += size
            else:
                definitely_lost += size

        return {
            "definitely_lost_bytes": definitely_lost,
            "still_reachable_bytes": still_reachable,
            "total_open_allocations": len(self.allocations)
        }


if __name__ == "__main__":
    print("=== VALGRIND GÖLGE BELLEK (SHADOW MEMORY) SİMÜLASYONU ===")
    vm = SimulatedShadowMemory()

    # 1. malloc 4 bayt
    ptr1 = vm.malloc(0x1000, 4)
    print(f"[*] 0x1000 adresinde 4 bayt tahsis edildi (A=True, V=False).")

    # 2. Hata: İlklendirilmemiş okuma
    val = vm.read_byte(0x1000)
    print(f"[*] İlklendirilmemiş Okuma Testi -> Değer: {val}")

    # 3. Yazma ve Temiz Okuma
    vm.write_byte(0x1000, 0x42)
    val2 = vm.read_byte(0x1000)
    print(f"[*] Başarılı Yazma Sonrası Okuma -> Değer: {hex(val2)}")

    # 4. free ve Use-After-Free (UAF) Hatası
    vm.free(ptr1)
    print(f"[*] 0x1000 serbest bırakıldı (free).")
    vm.read_byte(0x1000) # UAF!

    # 5. Sızıntı Senaryosu: ptr2 tahsis edildi ama serbest bırakılmadı
    ptr2 = vm.malloc(0x2000, 64)
    # ptr2 kök işaretçilerde kayıtlı değil -> definitely lost!

    leak_report = vm.classify_leaks()
    print("\n=== VALGRIND MEMCHECK RAPORU ===")
    for err in vm.errors:
        print(f"  [ERROR] {err}")
    print(f"\nSızıntı Özeti:")
    print(f"  definitely lost: {leak_report['definitely_lost_bytes']} bayt")
    print(f"  still reachable: {leak_report['still_reachable_bytes']} bayt")


# -*- coding: utf-8 -*-
"""
HÜCRE 08 (CODE 2): Python ile Monotonic Arena Allocator ve Parçalanma Simülasyonu
Geleneksel malloc/free Parçalanması (Fragmentation) vs PMR Monotonic Reset Mimarisi
"""

from typing import Dict, Any, List

class MonotonicArenaSimulator:
    """C++20 std::pmr::monotonic_buffer_resource simülatörü."""
    
    def __init__(self, capacity_bytes: int):
        self.capacity = capacity_bytes
        self.offset = 0
        self.allocation_count = 0
        self.reset_count = 0

    def allocate(self, size_bytes: int, alignment: int = 8) -> Optional[int]:
        """İşaretçiyi ileri sararak anında bellek tahsis eder (O(1))."""
        # Hizalama düzeltmesi
        aligned_offset = (self.offset + alignment - 1) & ~(alignment - 1)
        if aligned_offset + size_bytes > self.capacity:
            return None # Arena doldu (OutOfMemory)
            
        alloc_addr = aligned_offset
        self.offset = aligned_offset + size_bytes
        self.allocation_count += 1
        return alloc_addr

    def release_all(self):
        """Tüm arenayı tek hamlede sıfırlar (O(1)). Bellek sızıntısı matematiksel olarak imkansızdır!"""
        self.offset = 0
        self.reset_count += 1

    def get_stats(self) -> Dict[str, Any]:
        return {
            "capacity_kb": self.capacity / 1024.0,
            "used_kb": self.offset / 1024.0,
            "free_kb": (self.capacity - self.offset) / 1024.0,
            "utilization_pct": (self.offset / self.capacity) * 100.0,
            "alloc_count": self.allocation_count,
            "reset_count": self.reset_count
        }


if __name__ == "__main__":
    print("=== C++20 PMR ARENA ALLOCATOR SİMÜLASYONU ===")
    arena = MonotonicArenaSimulator(capacity_bytes=1024 * 1024) # 1 MB Arena

    # 10 Çerçevelik radar döngüsü
    for frame in range(10):
        # Her çerçevede 1,000 hedef için 64 bayt tahsis et
        for target in range(1000):
            addr = arena.allocate(size_bytes=64, alignment=16)
        
        # Çerçeve bitti: Tüm tahsisleri tek seferde sıfırla!
        arena.release_all()

    stats = arena.get_stats()
    print(f"[*] Toplam Yapılan Tahsis Sayısı : {stats['alloc_count']:,}")
    print(f"[*] Gerçekleşen Arena Reset Sayısı: {stats['reset_count']}")
    print(f"[*] Çerçeve Sonu Kalan Sızıntı    : {stats['used_kb']} KB (SIFIR SIZINTI GARANTİSİ)")


# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Arıza Simülatörü
72 Saatlik Görevde Yavaş Bellek Sızıntısı (Memory Creep) ve OOM Çöküş Modeli
"""

import numpy as np
from typing import Dict, Any, List

class MemoryCreepSabotageLab:
    """Yavaş bellek sızıntısının sistem ömrü üzerindeki tahribat simülatörü."""

    @staticmethod
    def simulate_long_running_creep(
        total_hours: int = 72,
        packets_per_sec: int = 500,
        leak_bytes_per_packet: int = 16,
        system_ram_limit_mb: float = 2048.0
    ) -> Dict[str, Any]:
        """72 saat boyunca çalışan bir aviyonik serviste sızıntı büyümesini modeller."""
        hours = np.arange(1, total_hours + 1)
        bytes_per_sec = packets_per_sec * leak_bytes_per_packet
        bytes_per_hour = bytes_per_sec * 3600
        
        cumulative_leak_mb = (hours * bytes_per_hour) / (1024.0 * 1024.0)
        
        # OOM çöküş anı kontrolü
        oom_hour = None
        for h, mb in zip(hours, cumulative_leak_mb):
            if mb >= system_ram_limit_mb:
                oom_hour = int(h)
                break

        return {
            "total_hours": total_hours,
            "leak_rate_mb_per_hour": bytes_per_hour / (1024.0 * 1024.0),
            "final_leak_mb": float(cumulative_leak_mb[-1]),
            "oom_limit_mb": system_ram_limit_mb,
            "oom_triggered": oom_hour is not None,
            "oom_hour": oom_hour,
            "hourly_mb": cumulative_leak_mb
        }


if __name__ == "__main__":
    print("=== YAVAŞ BELLEK SIZINTISI (MEMORY CREEP) SABOTAJ TESTİ ===")
    report = MemoryCreepSabotageLab.simulate_long_running_creep(
        total_hours=72, packets_per_sec=500, leak_bytes_per_packet=16, system_ram_limit_mb=2048.0
    )
    print(f"[*] Saatlik Sızıntı Hızı : {report['leak_rate_mb_per_hour']:.2f} MB / saat")
    print(f"[*] 72. Saat Sonu Sızıntı : {report['final_leak_mb']:.1f} MB")
    print(f"[*] OOM Killer Tetiklendi mi?: {report['oom_triggered']}")
    if report['oom_triggered']:
        print(f"[!] SİSTEM {report['oom_hour']}. SAATTE OOM İLE ÇÖKTÜ!")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): 72 Saatlik Görev Simülasyonu Massif Snapshot Analizcisi
Zaman Serisi Heap Büyümesi, Zirve (High-Water Mark) Tespiti ve Sızıntı Eğimi Hesabı
"""

import numpy as np
from typing import Dict, Any, List

def analyze_massif_profile(hours: int = 72, has_leak: bool = True) -> Dict[str, Any]:
    """Massif yığın profili simülasyonu: Sızıntılı vs Optimize Edilmiş Profil Karşılaştırması."""
    time_pts = np.linspace(0, hours, 100)
    
    if has_leak:
        # Sızıntılı profil: Sürekli artan eğri (Creep) + dalgalanma
        heap_mb = 120.0 + (time_pts * 24.5) + np.random.normal(0, 5.0, size=len(time_pts))
    else:
        # Optimize profil: Sabit tavanlı yığın tamponu (High-Water Mark ~250 MB, sıfır sızıntı eğimi)
        heap_mb = 250.0 + np.random.normal(0, 2.0, size=len(time_pts))

    peak_mb = float(np.max(heap_mb))
    slope = float(np.polyfit(time_pts, heap_mb, 1)[0]) # MB / saat eğimi

    is_leaking = slope > 1.0 # Saatte 1 MB'den fazla artıyorsa sızıntı var

    return {
        "time_hours": time_pts,
        "heap_mb": heap_mb,
        "peak_mb": peak_mb,
        "leak_slope_mb_per_hour": slope,
        "is_leaking": is_leaking
    }


if __name__ == "__main__":
    print("=== MASSIF YIĞIN PROFİLİ VE SIZINTI TREND ANALİZİ ===")
    leak_data = analyze_massif_profile(hours=72, has_leak=True)
    fixed_data = analyze_massif_profile(hours=72, has_leak=False)

    print(f"[*] [Sızıntılı Tasarım] Zirve Bellek: {leak_data['peak_mb']:.1f} MB | Büyüme Eğimi: {leak_data['leak_slope_mb_per_hour']:.2f} MB/saat | Sızıntı Var mı?: {leak_data['is_leaking']}")
    print(f"[*] [Optimize Tasarım]  Zirve Bellek: {fixed_data['peak_mb']:.1f} MB | Büyüme Eğimi: {fixed_data['leak_slope_mb_per_hour']:.2f} MB/saat | Sızıntı Var mı?: {fixed_data['is_leaking']}")


# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Kapsamlı Bellek Teşhis Araçları Benchmark Laboratuvarı
Doğrudan Yürütme vs AddressSanitizer (ASan) vs Valgrind Memcheck Karşılaştırması
"""

import numpy as np
from typing import Dict, Any

def run_sanitizer_benchmark() -> Dict[str, Any]:
    """100,000 bellek tahsisi ve serbest bırakma işleminde araçların başarımını modeller."""
    operations = 100000
    
    # 1. Doğrudan C++ (Optimizasyonlu)
    native_time_ms = 45.0
    native_ram_mb = 32.0

    # 2. AddressSanitizer (ASan) -> ~2x süre, ~2.8x RAM
    asan_time_ms = native_time_ms * 2.1
    asan_ram_mb = native_ram_mb * 2.7

    # 3. Valgrind Memcheck -> ~35x süre, ~2.2x RAM
    valgrind_time_ms = native_time_ms * 34.5
    valgrind_ram_mb = native_ram_mb * 2.2

    return {
        "operations": operations,
        "tools": ["Doğrudan C++ (-O3)", "AddressSanitizer (ASan)", "Valgrind Memcheck"],
        "times_ms": [native_time_ms, asan_time_ms, valgrind_time_ms],
        "rams_mb": [native_ram_mb, asan_ram_mb, valgrind_ram_mb],
        "slowdown_ratios": [1.0, asan_time_ms / native_time_ms, valgrind_time_ms / native_time_ms]
    }


if __name__ == "__main__":
    print("=== BELLEK TEŞHİS ARAÇLARI PERFORMANS BENCHMARK'I ===")
    b = run_sanitizer_benchmark()
    print(f"{'Araç':>25} | {'Süre (ms)':>10} | {'Yavaşlama':>10} | {'RAM (MB)':>10}")
    print("-" * 62)
    for i, tool in enumerate(b["tools"]):
        print(f"{tool:>25} | {b['times_ms'][i]:>10.1f} | {b['slowdown_ratios'][i]:>9.1f}x | {b['rams_mb'][i]:>10.1f}")


# -*- coding: utf-8 -*-
"""
HÜCRE 20 (CODE 6): 4 Panelli 300 DPI Mühendislik Dashboard'u ve Katı Doğrulama Testleri
Valgrind Gölge Bellek, Massif Zaman Serisi, Sızıntı Taksonomisi ve ASan Karşılaştırması
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_104\gun_104_valgrind_heap_profiling_zihinsel_modeli.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı Valgrind heap profiling dashboard'u üretir."""
    fig, axes = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor("#0F172A")

    # Renk Paleti
    accent_blue = "#38BDF8"
    accent_green = "#4ADE80"
    accent_amber = "#FBBF24"
    accent_red = "#F87171"
    accent_purple = "#C084FC"
    text_color = "#F8FAFC"
    grid_color = "#334155"

    for ax_row in axes:
        for ax in ax_row:
            ax.set_facecolor("#1E293B")
            ax.tick_params(colors=text_color, labelsize=9)
            ax.grid(True, linestyle="--", alpha=0.3, color=grid_color)
            for spine in ax.spines.values():
                spine.set_color(grid_color)

    # -------------------------------------------------------------------------
    # Panel 1: 72 Saatlik Massif Yığın Profili (Zaman Serisi)
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    time_hrs = np.linspace(0, 72, 100)
    leak_mb = 100 + (time_hrs * 26.5) # Sızıntılı profil
    fixed_mb = 120 + (130 * (1.0 - np.exp(-time_hrs / 6.0))) # Düzleşen profil

    ax1.plot(time_hrs, leak_mb, color=accent_red, linewidth=2.5, label="Sızıntılı Servis (Monotonic Creep)")
    ax1.plot(time_hrs, fixed_mb, color=accent_green, linewidth=2.5, label="C++20 PMR / Sabit Tavan (250 MB)")
    ax1.axhline(2048, color=accent_amber, linestyle="--", linewidth=1.8, label="Cgroup / Sistem RAM Sınırı (2 GB)")

    ax1.scatter(72, leak_mb[-1], color=accent_red, s=120, zorder=5)
    ax1.text(70, leak_mb[-1] - 150, "OOM İnfazı Riski!\n(~2,008 MB)", color=accent_red, fontsize=8.5, ha="right", fontweight="bold")

    ax1.set_title("Panel 1: 72 Saatlik Massif Yığın Profili ve Sızıntı Eğimi", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.set_xlabel("Zaman (Saat)", color=text_color, fontsize=10)
    ax1.set_ylabel("Yığın Bellek (Heap MB)", color=text_color, fontsize=10)
    ax1.set_ylim(0, 2300)
    ax1.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 2: Valgrind Memcheck Sızıntı Taksonomisi (Bar Grafiği)
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    categories = ["Definitely Lost\n(Kesin Kayıp)", "Indirectly Lost\n(Dolaylı Kayıp)", "Possibly Lost\n(Şüpheli)", "Still Reachable\n(Ulaşılabilir)"]
    bytes_lost = [524288, 262144, 65536, 1048576] # Bayt cinsinden
    kb_lost = [b / 1024.0 for b in bytes_lost]
    colors = [accent_red, accent_amber, accent_purple, accent_green]

    bars = ax2.bar(categories, kb_lost, color=colors, width=0.55, edgecolor="#0F172A", linewidth=1.5)
    ax2.set_title("Panel 2: Valgrind Memcheck Sızıntı Taksonomisi Dağılımı", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_ylabel("Kayıp Bellek (KB)", color=text_color, fontsize=10)

    for bar, val in zip(bars, kb_lost):
        ax2.text(bar.get_x() + bar.get_width()/2.0, val + 25, f"{val:.1f} KB", ha="center", va="bottom", color=text_color, fontsize=9.5, fontweight="bold")
    ax2.set_ylim(0, 1300)

    # -------------------------------------------------------------------------
    # Panel 3: Valgrind Gölge Bellek (Shadow Memory) Mimari Şeması
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)
    ax3.axis("off")
    ax3.set_title("Panel 3: Valgrind Gölge Bellek (Shadow Memory) Eşlemesi", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # Gerçek Bellek Kutusu
    rect_real = plt.Rectangle((0.5, 6.0), 4.0, 3.0, facecolor="#0369A1", edgecolor=accent_blue, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_real)
    ax3.text(2.5, 8.2, "GERÇEK BELLEK (1 Bayt)", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(2.5, 7.2, "Adres: 0x7ffd_1000\nVeri: 0x42 (01000010b)", ha="center", color="#BAE6FD", fontsize=8.5)

    # A-Biti Kutusu
    rect_abit = plt.Rectangle((5.5, 6.5), 4.0, 2.5, facecolor="#047857", edgecolor=accent_green, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_abit)
    ax3.text(7.5, 8.2, "A-BİTİ (Addressable)", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(7.5, 7.2, "1 Bit: [ 1 ] (Geçerli Adres)\nmalloc=1, free=0", ha="center", color="#A7F3D0", fontsize=8.5)

    # V-Bitleri Kutusu
    rect_vbit = plt.Rectangle((5.5, 2.5), 4.0, 3.0, facecolor="#B45309", edgecolor=accent_amber, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_vbit)
    ax3.text(7.5, 4.7, "V-BİTLERİ (Valid-Value)", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(7.5, 3.5, "8 Bit: [ 11111111b ]\nHer bit ilklendirildi mi?\n0 ise uninitialized warning!", ha="center", color="#FDE68A", fontsize=8)

    # Oklar
    ax3.annotate("", xy=(5.5, 7.7), xytext=(4.5, 7.7), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))
    ax3.annotate("", xy=(5.5, 4.0), xytext=(4.5, 6.5), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))

    # Alt Açıklama
    rect_desc = plt.Rectangle((0.5, 1.0), 9.0, 1.2, facecolor="#334155", edgecolor=grid_color, linewidth=1.5, transform=ax3.transData)
    ax3.add_patch(rect_desc)
    ax3.text(5.0, 1.6, "Her bellek erişimi 2 aşamalı kontrol edilir: A-bit (Erişim Yetkisi) + V-bit (Değer Başlatıldı mı?)", ha="center", va="center", color=text_color, fontsize=8.5, fontweight="bold")

    # -------------------------------------------------------------------------
    # Panel 4: Doğrudan C++ vs ASan vs Valgrind Performans Kıyaslaması
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    tools = ["Doğrudan C++\n(-O3)", "AddressSanitizer\n(ASan)", "Valgrind\nMemcheck"]
    slowdown = [1.0, 2.1, 34.5]
    ram_multiplier = [1.0, 2.7, 2.2]

    x = np.arange(len(tools))
    width = 0.35

    ax4.bar(x - width/2, slowdown, width, color=accent_red, label="Yürütme Süresi Çarpanı (1x - 35x)")
    ax4.bar(x + width/2, ram_multiplier, width, color=accent_blue, label="RAM Tüketim Çarpanı (1x - 3x)")

    ax4.set_xticks(x)
    ax4.set_xticklabels(tools, color=text_color, fontsize=9.5, fontweight="bold")
    ax4.set_ylabel("Maliyet Çarpanı (Kat)", color=text_color, fontsize=10)
    ax4.set_title("Panel 4: Teşhis Araçları Başarım ve Yavaşlama Maliyeti", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax4.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_path}")


def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Gün 104 için tüm mimari ve matematiksel kabulleri katı testlerle doğrular."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dashboard Görsel Doğrulaması
    assert os.path.exists(png_path), f"HATA: Dashboard görseli mevcut değil: {png_path}"
    file_size = os.path.getsize(png_path)
    assert file_size > 100_000, f"HATA: Dashboard boyutu şüpheli ({file_size} bayt)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {file_size:,} bayt.")

    # 2. Gölge Bellek Simülatörü ve UAF Doğrulaması
    vm = SimulatedShadowMemory()
    p = vm.malloc(0x1000, 8)
    vm.write_byte(0x1000, 100)
    assert vm.read_byte(0x1000) == 100, "HATA: Başarılı bellek yazma okunamadı!"
    vm.free(p)
    vm.read_byte(0x1000) # UAF üretmeli
    assert any("Use-After-Free" in e for e in vm.errors), "HATA: UAF hatası tespit edilemedi!"
    print("  [+] Gölge Bellek A-bit/V-bit ve Use-After-Free (UAF) Davranışı Doğrulandı.")

    # 3. Sızıntı Taksonomisi Doğrulaması
    vm.malloc(0x2000, 128) # Serbest bırakılmadı
    leaks = vm.classify_leaks()
    assert leaks["definitely_lost_bytes"] == 128, "HATA: definitely lost sızıntı miktarı hatalı!"
    print("  [+] Memcheck definitely lost Sızıntı Taksonomisi Doğrulandı.")

    # 4. PMR Monotonic Arena Doğrulaması
    arena = MonotonicArenaSimulator(capacity_bytes=1024)
    addr1 = arena.allocate(128)
    assert addr1 is not None, "HATA: Arena tahsis yapamadı!"
    arena.release_all()
    stats = arena.get_stats()
    assert stats["used_kb"] == 0.0, "HATA: Arena release_all() sonrası bellek sıfırlanmalıdır!"
    print("  [+] C++20 PMR Monotonic Arena Sıfır Sızıntı Garantisi Doğrulandı.")

    # 5. Massif Profil Analizcisi Doğrulaması
    prof_leak = analyze_massif_profile(hours=24, has_leak=True)
    prof_fixed = analyze_massif_profile(hours=24, has_leak=False)
    assert prof_leak["is_leaking"] is True, "HATA: Sızıntılı profil tespit edilemedi!"
    assert prof_fixed["is_leaking"] is False, "HATA: Sabit tavanlı profil sızıntı olarak işaretlenmemelidir!"
    print("  [+] Massif Yığın Profili Regresyon Eğimi ve Sızıntı Tespiti Doğrulandı.")

    print("\n[PASS] Gün 104: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
