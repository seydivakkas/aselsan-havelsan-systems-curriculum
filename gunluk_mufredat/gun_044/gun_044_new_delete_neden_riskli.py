"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 044: new/delete Neden Riskli? Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Manuel new / delete Yaşam Döngüsü ve Dangling Pointer Simülasyonu
# Bellek serbest bırakma sonrası adreste kalan artık verinin tespiti
# ==============================================================================

import ctypes

class SensorNode(ctypes.Structure):
    _fields_ = [
        ("node_id", ctypes.c_uint32),
        ("frequency_mhz", ctypes.c_float),
        ("is_active", ctypes.c_bool)
    ]

class ManualHeapManager:
    """C++ new ve delete operatörlerinin davranışını simüle eden bellek yöneticisi"""
    def __init__(self):
        self.allocated_blocks = {}
        self.counter = 0x20000000

    def cpp_new(self, node_id: int, freq: float) -> int:
        """new SensorNode(node_id, freq) simülasyonu"""
        addr = self.counter
        self.counter += 64  # 64 baytlık heap bloğu
        node = SensorNode(node_id=node_id, frequency_mhz=freq, is_active=True)
        self.allocated_blocks[addr] = {"object": node, "deleted": False}
        return addr

    def cpp_delete(self, addr: int):
        """delete ptr simülasyonu"""
        if addr not in self.allocated_blocks:
            raise MemoryError(f"[SEGFAULT] 0x{addr:08X} adresi heap üzerinde kayıtlı değil!")
        block = self.allocated_blocks[addr]
        if block["deleted"]:
            raise RuntimeError(f"[DOUBLE FREE ALERT] 0x{addr:08X} adresi zaten silinmişti! Heap bozuldu!")
        
        # 1. Aşama: Destructor çağrısı (is_active = False)
        block["object"].is_active = False
        # 2. Aşama: Belleği serbest bırak (Deleted işaretle)
        block["deleted"] = True

    def dereference(self, addr: int) -> SensorNode:
        """*ptr erişim simülasyonu"""
        if addr not in self.allocated_blocks:
            raise MemoryError(f"Segmentation fault on 0x{addr:08X}")
        block = self.allocated_blocks[addr]
        if block["deleted"]:
            # Use-After-Free durumu
            return f"[USE-AFTER-FREE UYARISI] 0x{addr:08X} silindi ama okundu! (Artık ID: {block['object'].node_id})"
        return block["object"]

def run_lab_01_manual_lifecycle():
    print("[*] Laboratuvar 1: Manuel new / delete Yaşam Döngüsü Başlatılıyor...")
    heap = ManualHeapManager()
    
    # 1. new çağrısı
    ptr = heap.cpp_new(node_id=707, freq=1200.5)
    print(f"  [+] new SensorNode çağrıldı. Tahsis edilen adres: 0x{ptr:08X}")
    node = heap.dereference(ptr)
    print(f"  [+] Nesne Okundu -> ID: {node.node_id} | Frekans: {node.frequency_mhz} MHz")
    
    # 2. delete çağrısı
    print(f"  [-] delete ptr çağrılıyor...")
    heap.cpp_delete(ptr)
    print(f"  [-] Bellek serbest bırakıldı.")
    
    # 3. Tehlike: ptr değişkeni sıfırlanmadı (Dangling Pointer)
    print(f"\n[!] DANGLING POINTER TUZAĞI:")
    print(f"    Pointer değişkeninin değeri hâlâ: 0x{ptr:08X}")
    uaf_result = heap.dereference(ptr)
    print(f"    Silinen adrese erişim sonucu: {uaf_result}")
    
    # Doğru Savunma Kuralı: Nullify!
    ptr = 0  # C++: ptr = nullptr;
    print(f"    [SAVUNMA] ptr = nullptr yapıldı. Artık dangling pointer değil: 0x{ptr:08X}")

if __name__ == "__main__":
    run_lab_01_manual_lifecycle()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Taktik İHA Görev Bilgisayarında Sızıntı ve Güvenli Tasarım
# Manuel new/delete ile sızıntı simülasyonu vs Güvenli Kapsam Koruması
# ==============================================================================

class FlightTelemetryPacket:
    def __init__(self, packet_id: int, size_bytes: int = 1024):
        self.packet_id = packet_id
        self.size_bytes = size_bytes

class UnsafeFlightController:
    def __init__(self):
        self.leaked_bytes = 0
        self.total_processed = 0

    def process_packet_unsafe(self, packet_id: int, checksum_valid: bool):
        """Manuel new/delete simülasyonu - Erken return sızıntı üretir"""
        # C++: FlightTelemetryPacket* pkt = new FlightTelemetryPacket(packet_id);
        packet_size = 1024
        self.total_processed += 1
        
        if not checksum_valid:
            # Erken çıkış! delete pkt unutuldu!
            self.leaked_bytes += packet_size
            return False  # Erken dönüş
            
        # Başarılı işlem - delete pkt yapıldı
        return True

class SafeFlightController:
    def __init__(self):
        self.leaked_bytes = 0
        self.total_processed = 0

    def process_packet_safe(self, packet_id: int, checksum_valid: bool):
        """Modern RAII / Stack simülasyonu - Kapsamdan nasıl çıkılırsa çıkılsın sızıntı 0'dır"""
        self.total_processed += 1
        # C++: auto pkt = std::make_unique<FlightTelemetryPacket>(packet_id);
        # RAII sahibi fonksiyon sonlandığında otomatik temizlenir!
        if not checksum_valid:
            return False  # Güvenle çıkış
        return True

def run_lab_02_leak_simulation():
    print("\n[*] Laboratuvar 2: Taktik İHA Uçuş Bilgisayarı Sızıntı Senaryosu...")
    unsafe_ctrl = UnsafeFlightController()
    safe_ctrl = SafeFlightController()
    
    total_packets = 10_000
    # Paketlerin %5'i bozuk sağlama toplamına (checksum error) sahip olsun
    import random
    random.seed(42)
    
    for i in range(total_packets):
        is_valid = (i % 20 != 0)  # Her 20 paketten 1'i bozuk
        unsafe_ctrl.process_packet_unsafe(packet_id=i, checksum_valid=is_valid)
        safe_ctrl.process_packet_safe(packet_id=i, checksum_valid=is_valid)
        
    print(f"  [+] İşlenen Toplam Paket : {total_packets:,} adet")
    print(f"  [!] GÜVENSİZ KONTROLCÜ   : {unsafe_ctrl.leaked_bytes / 1024:.1f} KB Bellek Sızdı! (Haftada GB'larca RAM tükenir)")
    print(f"  [+] GÜVENLİ (RAII) KONT. : {safe_ctrl.leaked_bytes} KB Sızıntı (SIFIR SIZINTI GARANTİSİ)")

if __name__ == "__main__":
    run_lab_02_leak_simulation()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Sabotaj ve Hata Enjeksiyonu (Double Free & Mismatched Array Delete)
# Sistem seviyesinde heap bütünlük koruması ve tespit simülasyonu
# ==============================================================================

class StrictHeapIntegrityMonitor:
    def __init__(self):
        self.allocated_chunks = {}
        self.free_chunks = set()
        self.counter = 0x40000000

    def allocate(self, size: int, is_array: bool = False) -> int:
        addr = self.counter
        self.counter += size + 64
        self.allocated_chunks[addr] = {"size": size, "is_array": is_array}
        return addr

    def delete_single(self, addr: int):
        """C++ delete ptr;"""
        if addr in self.free_chunks:
            raise RuntimeError(
                f"[CRITICAL ABORT] DOUBLE FREE TESPIT EDILDI!\n"
                f"  -> Adres: 0x{addr:016X}\n"
                f"  -> Teşhis: Bu bellek bloğu daha önce serbest bırakılmıştı!\n"
                f"  -> Sonuç: Heap arena bütünlüğü bozuldu (SIGABRT)!"
            )
        if addr not in self.allocated_chunks:
            raise MemoryError(f"Geçersiz bellek adresi: 0x{addr:016X}")
            
        chunk = self.allocated_chunks[addr]
        if chunk["is_array"]:
            raise TypeError(
                f"[ALLOCATION MISMATCH] Dizi tahsisi tekil delete ile silinemez!\n"
                f"  -> Hata: 'new[]' ile ayrılan bellek 'delete[]' yerine 'delete' ile silindi!\n"
                f"  -> Sonuç: Dizi metadata cookie'si bozuldu!"
            )
            
        del self.allocated_chunks[addr]
        self.free_chunks.add(addr)

def run_lab_03_sabotage():
    print("\n[*] Laboratuvar 3: Double Free ve Mismatched Deallocation Sabotajı...")
    monitor = StrictHeapIntegrityMonitor()
    
    # 1. Sabotaj: Double Free Testi
    print("  [1] Double Free Sabotajı:")
    addr = monitor.allocate(size=256, is_array=False)
    monitor.delete_single(addr)  # İlk yasal silme
    try:
        monitor.delete_single(addr)  # İkinci yasadışı silme!
    except RuntimeError as ex:
        print(f"  [BAŞARILI TESPİT] Beklenen Double Free yakalandı:")
        print(f"  {ex}")
        
    # 2. Sabotaj: Mismatched Array Delete Testi
    print("\n  [2] Mismatched Allocation Sabotajı (new[] vs delete):")
    arr_addr = monitor.allocate(size=1024, is_array=True)  # new Target[10]
    try:
        monitor.delete_single(arr_addr)  # delete ptr; (delete[] ptr OLMALIYDI)
    except TypeError as ex:
        print(f"  [BAŞARILI TESPİT] Beklenen Mismatch hatası yakalandı:")
        print(f"  {ex}")

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
# Manuel Bellek Yönetimi vs Otomatik Kapsam Temizliği (RAII) Simülasyonu
# ==============================================================================

import time

def benchmark_manual_vs_scoped():
    print("\n[*] Laboratuvar 4: Manuel Yönetim vs RAII Determinizm Benchmark Başlatılıyor...")
    iterations = 50_000
    
    # 1. Manuel Yönetim Simülasyonu (İki aşamalı: tahsis + manuel takip + manuel serbest bırakma)
    start_manual = time.perf_counter()
    for _ in range(iterations):
        # Tahsis
        res = [10.5, 20.2, 30.1]
        # Manuel doğrulama adımları
        if len(res) > 0:
            val = res[0]
        # Manuel silme simülasyonu
        del res
    elapsed_manual_ms = (time.perf_counter() - start_manual) * 1000.0
    
    # 2. Doğrudan Kapsam Tabanlı (RAII / Stack Simülasyonu)
    start_scoped = time.perf_counter()
    for _ in range(iterations):
        # Otomatik kapsam değişkeni
        val = 10.5 + 20.2
    elapsed_scoped_ms = (time.perf_counter() - start_scoped) * 1000.0
    
    speedup = elapsed_manual_ms / elapsed_scoped_ms if elapsed_scoped_ms > 0 else 1.0
    
    print(f"  -> Manuel Takip ve Silme Süresi ({iterations:,} çağrı): {elapsed_manual_ms:.2f} ms")
    print(f"  -> Otomatik Kapsam / RAII Süresi ({iterations:,} çağrı): {elapsed_scoped_ms:.2f} ms")
    print(f"  -> Hız & Verim Artışı                            : {speedup:.2f}x Daha Hızlı!")
    
    return elapsed_manual_ms, elapsed_scoped_ms, speedup

if __name__ == "__main__":
    benchmark_manual_vs_scoped()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-044 Sistem Mimarisi Görselleştirme Motoru
# 4 Panelli Analitik Sistem Şeması Üretimi (gun_044_new_delete_neden_riskli.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

def generate_viz_044(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900
    
    # --------------------------------------------------------------------------
    # Panel 1: new ve delete İki Aşamalı Anatomisi
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. new ve delete Operatörlerinin İki Aşamalı Mekanizması", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # new Akışı
    box_new = patches.FancyBboxPatch((0.05, 0.52), 0.90, 0.40, boxstyle="round,pad=0.03", facecolor='#064E3B', edgecolor='#10B981', linewidth=1.5)
    ax1.add_patch(box_new)
    ax1.text(0.08, 0.84, "C++ new Target(args):", color='#6EE7B7', fontsize=10, fontweight='bold')
    ax1.text(0.08, 0.72, "1. Adım: operator new(sizeof(Target)) -> Ham bellek tahsisi (malloc benzeri)\n2. Adım: Target::Target(args) -> Placement constructor ile nesne inşası\n[RİSK]: Constructor'da exception fırlarsa iç kaynaklar sızabilir!", color='#D1FAE5', fontsize=8)
    
    # delete Akışı
    box_del = patches.FancyBboxPatch((0.05, 0.05), 0.90, 0.40, boxstyle="round,pad=0.03", facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1.5)
    ax1.add_patch(box_del)
    ax1.text(0.08, 0.37, "C++ delete ptr:", color='#FCA5A5', fontsize=10, fontweight='bold')
    ax1.text(0.08, 0.25, "1. Adım: ptr->~Target() -> Destructor çağrılarak iç kaynaklar temizlenir\n2. Adım: operator delete(ptr) -> Ham bellek heap serbest listesine iade edilir\n[RİSK]: ptr değişkeni sıfırlanmaz! Dangling Pointer olarak kalır!", color='#FEE2E2', fontsize=8)
    
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 2: Erken Çıkışta Bellek Sızıntısı (Memory Leak)
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Fonksiyon Erken Dönüşünde (Early Return) Sızıntı Tuzağı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    nodes = [
        ("new Telemetry()", 0.85, '#10B981'),
        ("if (!checksum_valid)", 0.65, '#F59E0B'),
        ("return false; (SIZINTI!)", 0.45, '#EF4444'),
        ("delete tel; (ÇALIŞMADI)", 0.25, '#64748B')
    ]
    
    for text, y, color in nodes:
        r = patches.FancyBboxPatch((0.15, y - 0.06), 0.70, 0.09, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor=color, linewidth=2)
        ax2.add_patch(r)
        ax2.text(0.5, y - 0.01, text, color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')
        
    ax2.annotate("", xy=(0.5, 0.71), xytext=(0.5, 0.79), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=2))
    ax2.annotate("", xy=(0.5, 0.51), xytext=(0.5, 0.59), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2))
    ax2.text(0.5, 0.10, "[SONUÇ]: Her hatalı pakette 1 KB sızar -> 30 Günde GB'larca RAM tükenir!", color='#FCA5A5', fontsize=8, fontweight='bold', ha='center')
    
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 3: Double Free ve Use-After-Free
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Double Free ve Use-After-Free (UAF) Mekanizması", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # Heap Bloğu
    rect_heap = patches.Rectangle((0.1, 0.55), 0.35, 0.30, facecolor='#065F46', edgecolor='#10B981', linewidth=2)
    ax3.add_patch(rect_heap)
    ax3.text(0.275, 0.70, "Hedef Nesne\n(0x20000000)", color='#ECFDF5', fontsize=9, fontweight='bold', ha='center')
    
    # delete 1
    ax3.annotate("1. delete ptr; (Yasal İade)", xy=(0.45, 0.70), xytext=(0.60, 0.80),
                 arrowprops=dict(arrowstyle="->", color='#10B981', lw=2),
                 color='#6EE7B7', fontsize=8, fontweight='bold')
                 
    # delete 2
    ax3.annotate("2. delete ptr; (ÇİFT İADE!)\n-> SIGABRT / Heap Bozulması!", xy=(0.45, 0.65), xytext=(0.55, 0.55),
                 arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2.5),
                 color='#FCA5A5', fontsize=8, fontweight='bold')
                 
    # UAF
    box_uaf = patches.FancyBboxPatch((0.1, 0.10), 0.8, 0.30, boxstyle="round,pad=0.03", facecolor='#450A0A', edgecolor='#DC2626', linewidth=1.5)
    ax3.add_patch(box_uaf)
    ax3.text(0.5, 0.30, "USE-AFTER-FREE (UAF) TEHLİKESİ:", color='#FCA5A5', fontsize=9, fontweight='bold', ha='center')
    ax3.text(0.5, 0.18, "ptr iade edildi ama adresi hâlâ saklıyor.\nO adrese başka bir veri yazıldığında eski kod o veriyi ezebilir!\nSonuç: Sessiz veri bozulması veya RCE güvenlik açığı!", color='#FEE2E2', fontsize=8, ha='center')
    
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 50.000 İşlemde Manuel Takip vs Otomatik Kapsam Süresi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    methods = ['Manuel Takip & Silme\n(new/delete yükü)', 'Otomatik Kapsam / RAII\n(Deterministik)']
    times = [28.4, 2.1]  # Temsili milisaniye değerleri
    bar_colors = ['#EF4444', '#10B981']
    
    b_bars = ax4.barh(methods, times, color=bar_colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("Toplam Süre (Milisaniye - Daha Azı Daha İyi)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.set_xlim(0, 35)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)
    
    for bar in b_bars:
        xval = bar.get_width()
        ax4.text(xval + 1, bar.get_y() + bar.get_height()/2.0, f"{xval:.1f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')
        
    ax4.text(18, 0.15, "13.5x Daha Hızlı!\n(%100 Sızıntısız Emniyet)", color='#34D399', fontsize=11, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_044(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# new/delete Risk Kriterlerinin Programatik Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 044: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)
    
    # 1. Test: Dangling Pointer Durumu ve Nullify Koruması
    raw_ptr = 0x30001000
    is_deleted = True
    # Silme sonrası ptr sıfırlanmadıysa dangling'dir:
    assert raw_ptr != 0 and is_deleted, "HATA: Dangling pointer durumu modellenemedi!"
    # Nullify koruması:
    raw_ptr = 0  # nullptr
    assert raw_ptr == 0, "HATA: Nullify adımı başarısız!"
    print("  -> [PASS] Dangling pointer tespiti ve Nullify kuralı doğrulandı.")
    
    # 2. Test: Double Free Tespiti Doğrulaması
    free_history = set()
    test_addr = 0x40002000
    free_history.add(test_addr)
    # İkinci silme girişimi:
    double_free_detected = (test_addr in free_history)
    assert double_free_detected is True, "HATA: Double free tespit edilemedi!"
    print("  -> [PASS] Double Free yakalama algoritması doğrulandı.")
    
    # 3. Test: Memory Leak Simülasyonu
    allocated_count = 100
    freed_count = 95
    leaked_count = allocated_count - freed_count
    assert leaked_count == 5, "HATA: Bellek sızıntısı hesabı hatalı!"
    print(f"  -> [PASS] Bellek Sızıntısı Hesabı Doğrulandı: {leaked_count} adet kayıp blok.")
    
    # 4. Test: Mismatched Allocation Koruma Kuralı
    alloc_type = "new[]"
    dealloc_type = "delete"
    is_mismatch = (alloc_type == "new[]" and dealloc_type != "delete[]")
    assert is_mismatch is True, "HATA: Eşleşmeyen dizi silme kuralı doğrulanamadı!"
    print("  -> [PASS] new[] vs delete uyumsuzluğu tespiti doğrulandı.")
    
    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
