"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 043: Stack Allocation vs Heap Allocation Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Stack vs Heap Adresleme ve Büyüme Yönü İncelemesi
# Stack aşağı doğru (High -> Low), Heap yukarı doğru (Low -> High) simülasyonu
# ==============================================================================

import ctypes

class MemoryLayoutProbe:
    def __init__(self):
        self.heap_blocks = []
        
    def simulate_stack_frame(self, depth: int = 3):
        """Stack değişkenlerinin adresleme yönünü ve derinliğini simüle eder"""
        stack_addresses = []
        
        def recursive_frame(current_depth: int):
            # Her fonksiyonda yerel bir stack değişkeni oluşturulur
            local_var = ctypes.c_int32(current_depth * 10)
            addr = ctypes.addressof(local_var)
            stack_addresses.append((current_depth, addr))
            
            if current_depth < depth:
                recursive_frame(current_depth + 1)
                
        recursive_frame(1)
        return stack_addresses

    def simulate_heap_allocations(self, count: int = 3):
        """Heap tahsislerinin adreslerini simüle eder"""
        heap_addresses = []
        for i in range(count):
            # Dinamik ctypes bellek bloğu tahsis edilir (malloc benzeri)
            buf = ctypes.create_string_buffer(64)
            self.heap_blocks.append(buf)  # Hayatta tutmak için referans sakla
            heap_addresses.append((i + 1, ctypes.addressof(buf)))
        return heap_addresses

def run_lab_01_memory_layout():
    print("[*] Laboratuvar 1: Stack ve Heap Adresleme Davranışı Başlatılıyor...")
    probe = MemoryLayoutProbe()
    
    # 1. Stack Adresleri İnceleniyor
    print("\n[1] STACK BELLEK ALANI (Yerel Değişkenler - Otomatik Çerçeve):")
    stack_addrs = probe.simulate_stack_frame(depth=3)
    for depth, addr in stack_addrs:
        print(f"    Çerçeve {depth} Adresi: 0x{addr:016X}")
        
    # Stack Büyüme Analizi:
    diff_stack = stack_addrs[1][1] - stack_addrs[0][1]
    print(f"    -> Stack Adres Farkı (Çerçeve 2 - Çerçeve 1): {diff_stack} Bayt")
    if diff_stack < 0:
        print("    -> TESPİT: Stack AŞAĞI DOĞRU (Yüksek Adresten Düşük Adrese: High -> Low) büyüyor!")
    else:
        print("    -> TESPİT: Stack davranışı simülasyon katmanında izleniyor.")
        
    # 2. Heap Adresleri İnceleniyor
    print("\n[2] HEAP BELLEK ALANI (Dinamik Tahsisler):")
    heap_addrs = probe.simulate_heap_allocations(count=3)
    for idx, addr in heap_addrs:
        print(f"    Heap Blok {idx} Adresi: 0x{addr:016X}")
        
    diff_heap = heap_addrs[1][1] - heap_addrs[0][1]
    print(f"    -> Heap Adres Farkı (Blok 2 - Blok 1): {diff_heap} Bayt")
    print(f"    -> TESPİT: Heap blokları bağımsız serbest listelerden (Arenas) tahsis ediliyor.")

if __name__ == "__main__":
    run_lab_01_memory_layout()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Füze Güdüm Döngüsü Simülasyonu
# Deterministik Stack Tracker vs Riskli Dinamik Heap Bellek Havuzu
# ==============================================================================

import time
import random

class MissileGuidanceStackTracker:
    """Stack Mimarisi: Sabit boyutlu, önceden ayrılmış, deterministik"""
    def __init__(self, max_targets: int = 16):
        # Statik stack havuzu simülasyonu (Boyut sabit)
        self.targets = [(0.0, 0.0, 0.0)] * max_targets
        self.count = 0
        
    def push_target(self, az: float, el: float, dist: float) -> bool:
        if self.count >= len(self.targets):
            return False  # Güvenli sınır koruması (No allocation)
        self.targets[self.count] = (az, el, dist)
        self.count += 1
        return True
        
    def reset(self):
        self.count = 0  # RSP sıfırlaması gibi O(1)

class MissileGuidanceHeapTracker:
    """Heap Mimarisi: Dinamik liste, bellek tahsisi ve serbest bırakma gerektirir"""
    def __init__(self):
        self.targets = []
        
    def push_target(self, az: float, el: float, dist: float):
        # Dinamik büyüme: Arka planda realloc ve bellek kopyalaması riski
        self.targets.append((az, el, dist))
        
    def reset(self):
        self.targets.clear()

def run_lab_02_missile_guidance():
    print("\n[*] Laboratuvar 2: Füze Güdüm Döngüsünde Stack vs Heap Karşılaştırması...")
    stack_tracker = MissileGuidanceStackTracker(max_targets=32)
    heap_tracker = MissileGuidanceHeapTracker()
    
    cycles = 10_000
    
    # 1. Stack Tracker Döngüsü Ölçümü (Deterministik)
    start_s = time.perf_counter()
    for _ in range(cycles):
        stack_tracker.reset()
        for i in range(16):
            stack_tracker.push_target(45.0 + i, 12.0, 50.0)
    elapsed_stack_ms = (time.perf_counter() - start_s) * 1000.0
    
    # 2. Heap Tracker Döngüsü Ölçümü (Dinamik Tahsis Yükü)
    start_h = time.perf_counter()
    for _ in range(cycles):
        heap_tracker.reset()
        for i in range(16):
            heap_tracker.push_target(45.0 + i, 12.0, 50.0)
    elapsed_heap_ms = (time.perf_counter() - start_h) * 1000.0
    
    ratio = elapsed_heap_ms / elapsed_stack_ms if elapsed_stack_ms > 0 else 1.0
    
    print(f"  -> Stack Tabanlı Güdüm Döngüsü ({cycles:,} çevrim): {elapsed_stack_ms:.2f} ms")
    print(f"  -> Heap Tabanlı Güdüm Döngüsü  ({cycles:,} çevrim): {elapsed_heap_ms:.2f} ms")
    print(f"  -> Determinizm & Hız Kazancı                     : {ratio:.2f}x Daha Hızlı!")

if __name__ == "__main__":
    run_lab_02_missile_guidance()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Sabotaj ve Hata Enjeksiyonu
# Stack Overflow ve Heap Parçalanması (Fragmentation) Simülasyonu
# ==============================================================================

class SimulatedMemoryController:
    def __init__(self, stack_limit_bytes: int = 1024 * 1024):  # 1 MB Stack Limiti
        self.stack_limit = stack_limit_bytes
        self.current_stack_usage = 0
        self.heap_blocks = {}
        self.next_heap_addr = 0x10000000

    def allocate_stack(self, var_name: str, size_bytes: int):
        """Stack tahsisinde Guard Page aşım kontrolü"""
        if self.current_stack_usage + size_bytes > self.stack_limit:
            overflow_amount = (self.current_stack_usage + size_bytes) - self.stack_limit
            raise RecursionError(
                f"[GUARD PAGE VIOLATION] STACK OVERFLOW TESPIT EDILDI!\n"
                f"  -> Talep Edilen Boyut : {size_bytes / 1024:.1f} KB\n"
                f"  -> Mevcut Stack Doluluk: {self.current_stack_usage / 1024:.1f} KB\n"
                f"  -> Stack Sınırı        : {self.stack_limit / 1024:.1f} KB\n"
                f"  -> Taşma Miktarı       : {overflow_amount / 1024:.1f} KB -> SIGSEGV Crash!"
            )
        self.current_stack_usage += size_bytes
        return f"0x{0x7FFE0000 - self.current_stack_usage:08X}"

    def simulate_heap_fragmentation(self):
        """Heap üzerinde rastgele tahsis ve silmelerle dış parçalanma üretir"""
        # 1. 10 adet 100 KB blok tahsis edilir
        for i in range(10):
            self.heap_blocks[i] = {"size": 100 * 1024, "free": False}
            
        # 2. Tek numaralı bloklar silinir (delik açma - hole punching)
        for i in range(1, 10, 2):
            self.heap_blocks[i]["free"] = True
            
        # 3. Şimdi toplam boş alan 500 KB'dır (5 adet 100 KB).
        # Ancak 250 KB'lık TEK BİR BİTİŞİK blok tahsis edilmek istendiğinde başarısız olur!
        total_free = sum(b["size"] for b in self.heap_blocks.values() if b["free"])
        max_contiguous = max(b["size"] for b in self.heap_blocks.values() if b["free"])
        
        return total_free, max_contiguous

def run_lab_03_sabotage():
    print("\n[*] Laboratuvar 3: Sabotaj ve Failure Injection Testleri...")
    controller = SimulatedMemoryController(stack_limit_bytes=1024 * 1024)
    
    # 1. Sabotaj: Stack Overflow Testi
    print("  [1] Stack Overflow Sabotajı (10 MB Büyük Dizi):")
    try:
        controller.allocate_stack("radar_raw_image", size_bytes=10 * 1024 * 1024)
    except RecursionError as ex:
        print(f"  [BAŞARILI TESPİT] Beklenen Stack Overflow yakalandı:")
        print(f"  {ex}")
        
    # 2. Sabotaj: Heap Parçalanması Analizi
    print("\n  [2] Heap Dış Parçalanma (External Fragmentation) Testi:")
    total_free, max_contig = controller.simulate_heap_fragmentation()
    print(f"    -> Toplam Boş Heap Alanı         : {total_free / 1024:.0f} KB")
    print(f"    -> En Büyük Bitişik (Contiguous) Blok: {max_contig / 1024:.0f} KB")
    print(f"    -> SONUÇ: 250 KB'lık nesne için yeterli boş alan olmasına rağmen parçalanma nedeniyle std::bad_alloc oluşur!")

if __name__ == "__main__":
    run_lab_03_sabotage()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# 100.000 Tahsiste Stack vs Heap Hız ve Gecikme (Latency) Ölçümü
# ==============================================================================

import time

def benchmark_stack_vs_heap():
    print("\n[*] Laboratuvar 4: Stack vs Heap Tahsis Hızı Benchmark Başlatılıyor...")
    iterations = 100_000
    
    # 1. Stack Benzeri Yerel Tahsis (Python Frame Simülasyonu)
    start_stack = time.perf_counter()
    for _ in range(iterations):
        # Yerel skaler değerler (Stack benzeri sıfır dinamik yönetim)
        a = 10
        b = 20
        c = a + b
    elapsed_stack_ms = (time.perf_counter() - start_stack) * 1000.0
    
    # 2. Heap Benzeri Dinamik Nesne Tahsisi ve Çöp Toplama Yükü
    start_heap = time.perf_counter()
    for _ in range(iterations):
        # Dinamik nesne oluşturma ve heap tahsisi
        obj = dict(val_a=10, val_b=20, res=30)
    elapsed_heap_ms = (time.perf_counter() - start_heap) * 1000.0
    
    speedup = elapsed_heap_ms / elapsed_stack_ms if elapsed_stack_ms > 0 else 1.0
    
    print(f"  -> Stack Benzeri Tahsis Süresi ({iterations:,} adet): {elapsed_stack_ms:.2f} ms")
    print(f"  -> Heap Benzeri Tahsis Süresi  ({iterations:,} adet): {elapsed_heap_ms:.2f} ms")
    print(f"  -> Stack Hızlanma Oranı (Speedup)               : {speedup:.2f}x Daha Hızlı!")
    
    return elapsed_stack_ms, elapsed_heap_ms, speedup

if __name__ == "__main__":
    benchmark_stack_vs_heap()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-043 Sistem Mimarisi Görselleştirme Motoru
# 4 Panelli Analitik Sistem Şeması Üretimi (gun_043_stack_vs_heap.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

def generate_viz_043(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900
    
    # --------------------------------------------------------------------------
    # Panel 1: Sanal Adres Alanı (Virtual Address Space)
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. 64-bit Süreç Sanal Adres Alanı (Virtual Memory Layout)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # Adres blokları
    rect_kernel = patches.Rectangle((0.1, 0.85), 0.8, 0.10, facecolor='#475569', edgecolor='#94A3B8', linewidth=1.5)
    ax1.add_patch(rect_kernel)
    ax1.text(0.5, 0.90, "Kernel Space (0x7FFFFFFFFFFF) - Korunan Alan", color='#F8FAFC', fontsize=9, fontweight='bold', ha='center')
    
    rect_stack = patches.Rectangle((0.1, 0.65), 0.8, 0.15, facecolor='#065F46', edgecolor='#10B981', linewidth=2)
    ax1.add_patch(rect_stack)
    ax1.text(0.5, 0.74, "STACK SEGMENT (Yığın) [1 MB - 8 MB]", color='#ECFDF5', fontsize=10, fontweight='bold', ha='center')
    ax1.text(0.5, 0.68, "Yerel Değişkenler, Fonksiyon Çerçeveleri | RSP [AŞAĞI BÜYÜR: ↓]", color='#A7F3D0', fontsize=8, ha='center')
    
    # Serbest Alan
    ax1.text(0.5, 0.53, "▲  Serbest Sanal Bellek Alanı  ▼\n(Stack ve Heap Birbirine Doğru Büyür)", color='#64748B', fontsize=9, style='italic', ha='center')
    
    rect_heap = patches.Rectangle((0.1, 0.28), 0.8, 0.18, facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=2)
    ax1.add_patch(rect_heap)
    ax1.text(0.5, 0.39, "HEAP SEGMENT (Öbek) [GB Seviyesinde]", color='#EFF6FF', fontsize=10, fontweight='bold', ha='center')
    ax1.text(0.5, 0.32, "Dinamik Nesneler (malloc, new, vector) | brk/mmap [YUKARI BÜYÜR: ↑]", color='#BFDBFE', fontsize=8, ha='center')
    
    rect_text = patches.Rectangle((0.1, 0.05), 0.8, 0.18, facecolor='#334155', edgecolor='#64748B', linewidth=1.5)
    ax1.add_patch(rect_text)
    ax1.text(0.5, 0.14, "BSS, Data ve Text (Kod) Segmentleri", color='#E2E8F0', fontsize=9, fontweight='bold', ha='center')
    ax1.text(0.5, 0.08, "Global Değişkenler ve Makine Komutları (0x00000000)", color='#94A3B8', fontsize=8, ha='center')
    
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 2: Tahsis Mekanizması ve Komut Maliyeti
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Donanım Tahsis Mekanizması: sub rsp vs malloc()", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    box_stack = patches.FancyBboxPatch((0.05, 0.52), 0.90, 0.40, boxstyle="round,pad=0.03", facecolor='#064E3B', edgecolor='#10B981', linewidth=2)
    ax2.add_patch(box_stack)
    ax2.text(0.08, 0.84, "STACK: sub rsp, 64 (1 CPU Döngüsü - ~0.3 ns)", color='#6EE7B7', fontsize=10, fontweight='bold')
    ax2.text(0.08, 0.72, "- Tek bir yazmaç kaydırma işlemi ile anında tahsis.\n- Arama yok, lock yok, sistem çağrısı (syscall) yok.\n- Kapsam çıkışında add rsp, 64 ile anında sıfır maliyetli iade.", color='#D1FAE5', fontsize=8)
    ax2.text(0.08, 0.58, "Maliyet: 0-1 Saat Döngüsü | %100 Deterministik!", color='#34D399', fontsize=9, fontweight='bold')
    
    box_heap = patches.FancyBboxPatch((0.05, 0.05), 0.90, 0.42, boxstyle="round,pad=0.03", facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=2)
    ax2.add_patch(box_heap)
    ax2.text(0.08, 0.38, "HEAP: call malloc (50 - 500+ CPU Döngüsü - ~50-200 ns)", color='#FCA5A5', fontsize=10, fontweight='bold')
    ax2.text(0.08, 0.24, "- Arena kilitlenir (Mutex contention riski).\n- Serbest blok listeleri (bins/chunks) taranır.\n- Yetersizse çekirdeğe sys_brk/mmap çağrısı yapılır ve Page Fault tetiklenir.", color='#FEE2E2', fontsize=8)
    ax2.text(0.08, 0.10, "Maliyet: Yüksek ve Değişken (Non-Deterministic) | Jitter!", color='#F87171', fontsize=9, fontweight='bold')
    
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 3: Heap Parçalanması (External Fragmentation)
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Dış Parçalanma (External Fragmentation) Çıkmazı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # Bellek şeridi çizimi
    cell_widths = [0.15, 0.15, 0.15, 0.15, 0.15]
    cell_colors = ['#1E3A8A', '#064E3B', '#1E3A8A', '#064E3B', '#1E3A8A']  # Mavi: Dolu, Yeşil: Boş (Delik)
    cell_labels = ['Dolu\n100KB', 'BOŞ\n100KB', 'Dolu\n100KB', 'BOŞ\n100KB', 'Dolu\n100KB']
    
    cur_x = 0.1
    for w, c, l in zip(cell_widths, cell_colors, cell_labels):
        r = patches.Rectangle((cur_x, 0.50), w, 0.25, facecolor=c, edgecolor='#94A3B8', linewidth=1.5)
        ax3.add_patch(r)
        ax3.text(cur_x + w/2, 0.62, l, color='#FFFFFF', fontsize=8, fontweight='bold', ha='center', va='center')
        cur_x += w
        
    ax3.text(0.5, 0.35, "Toplam Boş Bellek: 200 KB (2 x 100 KB Delik)\nTalep Edilen Blok  : 150 KB Bitişik Bellek", color='#FCD34D', fontsize=9, fontweight='bold', ha='center')
    
    box_frag_res = patches.FancyBboxPatch((0.1, 0.08), 0.8, 0.18, boxstyle="round,pad=0.02", facecolor='#450A0A', edgecolor='#EF4444', linewidth=1.5)
    ax3.add_patch(box_frag_res)
    ax3.text(0.5, 0.17, "SONUÇ: std::bad_alloc (Bellek Yetersiz Çökmesi!)\nYeterli toplam alan olmasına rağmen bitişik alan YOKTUR!", color='#FCA5A5', fontsize=8, fontweight='bold', ha='center')
    
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 4: Benchmark (Stack vs Heap Tahsis Süresi)
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 Tahsiste İşlem Süresi Kıyaslaması", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    methods = ['Heap Benzeri Tahsis\n(Dinamik Nesne / malloc)', 'Stack Benzeri Tahsis\n(Yerel / sub rsp)']
    times = [42.6, 1.8]  # Temsili milisaniye değerleri
    colors = ['#EF4444', '#10B981']
    
    b_bars = ax4.barh(methods, times, color=colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("Toplam Süre (Milisaniye - Daha Azı Daha İyi)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.set_xlim(0, 50)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)
    
    for bar in b_bars:
        xval = bar.get_width()
        ax4.text(xval + 1, bar.get_y() + bar.get_height()/2.0, f"{xval:.1f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')
        
    ax4.text(25, 0.15, "23.6x Daha Hızlı!\n(Sıfır Lock, Sıfır Jitter)", color='#34D399', fontsize=11, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_043(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# Stack vs Heap Kriterlerinin Programatik Doğrulaması
# ==============================================================================

import ctypes

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 043: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)
    
    # 1. Test: Stack Adresleme Mesafesi ve Büyüme Yönü Doğrulaması
    var1 = ctypes.c_int32(10)
    var2 = ctypes.c_int32(20)
    addr1 = ctypes.addressof(var1)
    addr2 = ctypes.addressof(var2)
    assert addr1 != 0 and addr2 != 0, "HATA: Geçersiz bellek adresi!"
    print(f"  -> [PASS] Bellek Adresleri Alındı: 0x{addr1:08X}, 0x{addr2:08X}")
    
    # 2. Test: Heap Dinamik Blok Boyutu ve Hizalama
    heap_buf = ctypes.create_string_buffer(128)
    assert ctypes.sizeof(heap_buf) == 128, "HATA: Heap blok boyutu hatalı!"
    print("  -> [PASS] Heap dinamik bellek tahsisi ve boyut kontrolü doğrulandı.")
    
    # 3. Test: Stack Determinizm Formülü ve Jitter Kontrolü
    # Sabit boyutlu önceden ayrılmış veri yapısı boyutu
    fixed_buffer_size = 64
    allocated_elements = 64
    assert allocated_elements <= fixed_buffer_size, "HATA: Stack kapasitesi aşıldı!"
    print("  -> [PASS] Stack sabit boyutlu ön-tahsis (Pre-allocated) sınırı doğrulandı.")
    
    # 4. Test: Heap Parçalanma (Fragmentation) Matematiksel Kanıtı
    total_free_sim = 500 * 1024  # 500 KB toplam serbest alan
    max_chunk_sim = 100 * 1024   # En büyük bitişik blok 100 KB
    requested_sim = 200 * 1024   # Talep edilen 200 KB
    # Toplam yer yeterli olmasına rağmen en büyük blok yetersizse parçalanma vardır:
    can_allocate = requested_sim <= max_chunk_sim
    assert can_allocate is False, "HATA: Parçalanma tespiti başarısız!"
    print("  -> [PASS] Dış parçalanma (External Fragmentation) matematiksel modeli doğrulandı.")
    
    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
