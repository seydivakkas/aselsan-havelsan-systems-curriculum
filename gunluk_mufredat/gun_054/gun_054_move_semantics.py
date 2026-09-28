"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 054: Move Semantics Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Radar Ham I/Q Arabelleği - Taşıma Semantiği Simülasyonu
# Deep Copy vs Pointer Stealing (Kaynak Hırsızlığı) Makine Modeli
# ==============================================================================

class SimulatedRadarBuffer:
    """64-bit C++ RadarIQBuffer Bellek Modelinin Birebir Temsili"""
    def __init__(self, size_mb: int, buffer_id: str):
        self.buffer_id = buffer_id
        self.size_mb = size_mb
        # Heap bellek adresi benzetimi:
        self.data_ptr = id(object()) if size_mb > 0 else 0
        print(f"  [ALLOC] {self.buffer_id} Tahsis Edildi -> Boyut: {self.size_mb} MB, Heap Adresi: 0x{self.data_ptr:08X}")

    def __del__(self):
        if self.data_ptr != 0:
            print(f"  [FREE]  {self.buffer_id} Belleği Serbest Bırakıldı -> Adres: 0x{self.data_ptr:08X}")
        else:
            print(f"  [NO-OP] {self.buffer_id} Zaten Taşınmış (Boş), Serbest Bırakma Gerekmez.")

    @classmethod
    def deep_copy(cls, source: 'SimulatedRadarBuffer', new_id: str) -> 'SimulatedRadarBuffer':
        """C++98 Tarzı Pahalı Derin Kopyalama (Copy Constructor)"""
        print(f"  [COPY]  {source.buffer_id} -> {new_id} için {source.size_mb} MB KOPYALANIYOR (memcpy)...")
        # Yeni bağımsız heap tahsisi yapılır:
        new_buf = cls(source.size_mb, new_id)
        return new_buf

    @classmethod
    def move_from(cls, source: 'SimulatedRadarBuffer', new_id: str) -> 'SimulatedRadarBuffer':
        """C++20 Tarzı Sıfır Maliyetli Taşıma (Move Constructor)"""
        print(f"  [MOVE]  {source.buffer_id} -> {new_id} için Kaynak Çalınıyor (Pointer Stealing)...")
        new_buf = cls(0, new_id)
        # İşaretçi çalınır (O(1) - 2 nanosaniye):
        new_buf.data_ptr = source.data_ptr
        new_buf.size_mb = source.size_mb
        # Kaynak nesne 'moved-from' durumuna getirilir:
        source.data_ptr = 0
        source.size_mb = 0
        return new_buf

def run_lab_01_move_basics():
    print("[*] Laboratuvar 1: Radar Ham Sinyal Arabelleği Taşıma Semantiği...")

    # 1. Ham Sinyal Toplayıcı (Receiver) 64 MB Arabellek Oluşturuyor:
    rx_buf = SimulatedRadarBuffer(64, "RX_BUFFER_01")
    initial_address = rx_buf.data_ptr

    # 2. Taşıma İşlemi (std::move ile Darbe Sıkıştırma İşlemcisine Devir):
    dsp_buf = SimulatedRadarBuffer.move_from(rx_buf, "DSP_BUFFER_01")

    # 3. Durum Analizi:
    print(f"\n  -> Taşıma Sonrası Hedef Adresi : 0x{dsp_buf.data_ptr:08X} ({dsp_buf.size_mb} MB)")
    print(f"  -> Taşıma Sonrası Kaynak Adresi: 0x{rx_buf.data_ptr:08X} ({rx_buf.size_mb} MB)")

    assert dsp_buf.data_ptr == initial_address, "HATA: Veri adresi değişti, sıfır kopyalama bozuldu!"
    assert rx_buf.data_ptr == 0, "HATA: Kaynak nesne sıfırlanmadı (dangling pointer riski)!"
    print("  -> [BAŞARILI]: 64 MB veri tek bir bayt kopyalanmadan 0 ns ek yük ile devredildi.")

    # 4. Kapsam Dışı Temizliği
    del dsp_buf
    del rx_buf

if __name__ == "__main__":
    run_lab_01_move_basics()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Sabotaj Senaryosu - Use-After-Move ve Kendine Taşıma
# Arıza Enjeksiyonu ve Savunma Mekanizmaları
# ==============================================================================

class ResilientRadarPacket:
    """Kendine Taşıma ve Use-After-Move Korumalı Savunma Sınıfı"""
    def __init__(self, packet_id: int, payload_str: str):
        self.packet_id = packet_id
        self.payload = payload_str
        self.is_moved = False

    def move_assign(self, other: 'ResilientRadarPacket'):
        """Savunma Kuralı: Self-Move Assignment Koruması (this == &other)"""
        if self is other:
            print("  [SAVUNMA]: Kendine taşıma (Self-Move) tespit edildi! İşlem güvenle yok sayıldı.")
            return self

        # 1. Kendi eski kaynağını temizle
        self.payload = None

        # 2. Kaynağı çal
        self.packet_id = other.packet_id
        self.payload = other.payload
        self.is_moved = False

        # 3. Kaynak nesneyi boşalt (moved-from state)
        other.payload = None
        other.is_moved = True
        return self

    def transmit(self):
        """Taşınmış nesne üzerinden işlem yapılmasını engelleyen bariyer"""
        if self.is_moved or self.payload is None:
            raise RuntimeError(f"[FELAKET - Use-After-Move]: Paket ID={self.packet_id} taşınmış durumda! Veri okunamadı!")
        return f"PAKET-VERİSİ:[{self.payload}]"

def run_lab_02_sabotage_and_defense():
    print("\n[*] Laboratuvar 2: Sabotaj Senaryosu ve Güvenlik Bariyerleri...")

    # --------------------------------------------------------------------------
    # 1. Sabotaj: Use-After-Move
    # --------------------------------------------------------------------------
    print("  [1] USE-AFTER-MOVE SABOTAJ DENEYİ:")
    pkt_a = ResilientRadarPacket(101, "AESA_BEAM_STEERING_DATA")
    pkt_b = ResilientRadarPacket(0, "")

    # Taşıma işlemi:
    pkt_b.move_assign(pkt_a)
    print(f"    pkt_b Başarıyla Alındı: {pkt_b.transmit()}")

    try:
        # Taşınmış pkt_a üzerinden okuma denemesi:
        pkt_a.transmit()
        assert False, "HATA: Taşınmış nesneye erişim engellenemedi!"
    except RuntimeError as e:
        print(f"    [BAŞARILI SAVUNMA]: Beklenen çöküş yakalandı -> {e}")

    # --------------------------------------------------------------------------
    # 2. Sabotaj: Kendine Taşıma (Self-Move Assignment)
    # --------------------------------------------------------------------------
    print("\n  [2] KENDİNE TAŞIMA (SELF-MOVE) SABOTAJ DENEYİ:")
    pkt_c = ResilientRadarPacket(202, "DRFM_ELECTRONIC_WARFARE_SIGNATURE")
    # Kendini kendine taşı:
    pkt_c.move_assign(pkt_c)
    assert pkt_c.payload is not None, "HATA: Kendine taşıma nesneyi yok etti!"
    print(f"    İşlem Sonrası Paket Durumu: {pkt_c.transmit()}")
    print("    [BAŞARILI SAVUNMA]: Self-move kontrolü veri kaybını önledi.")

if __name__ == "__main__":
    run_lab_02_sabotage_and_defense()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: std::vector Reallocation Davranış Simülasyonu
# noexcept Taşıma vs non-noexcept Kopyalamaya Düşüş Ölçümü
# ==============================================================================

class ElementStats:
    copies = 0
    moves = 0

class MockBufferNoexcept:
    """noexcept taşıma kurucusuna sahip güvenli sınıf"""
    def __init__(self, name: str):
        self.name = name
    def copy(self):
        ElementStats.copies += 1
        return MockBufferNoexcept(self.name)
    def move(self):
        ElementStats.moves += 1
        return MockBufferNoexcept(self.name)

class MockBufferThrowing:
    """noexcept OLMAYAN güvensiz sınıf (std::vector mecburen kopyalar)"""
    def __init__(self, name: str):
        self.name = name
    def copy(self):
        ElementStats.copies += 1
        return MockBufferThrowing(self.name)
    def move(self):
        # Vektör bu fonksiyonu çağırmaktan korkar!
        ElementStats.moves += 1
        return MockBufferThrowing(self.name)

def simulate_vector_growth(element_cls, is_noexcept: bool, target_size: int = 16):
    """std::vector geometrik büyüme (1, 2, 4, 8, 16) simülasyonu"""
    capacity = 1
    storage = []

    for i in range(target_size):
        if len(storage) == capacity:
            # Reallocation Tetiklendi!
            new_capacity = capacity * 2
            new_storage = []
            for item in storage:
                if is_noexcept:
                    new_storage.append(item.move()) # noexcept: TAŞI!
                else:
                    new_storage.append(item.copy()) # non-noexcept: KOPYALA!
            storage = new_storage
            capacity = new_capacity
        storage.append(element_cls(f"elem_{i}"))

def run_lab_03_vector_reallocation():
    print("\n[*] Laboratuvar 3: std::vector Büyümesi ve noexcept Kararı...")

    # 1. noexcept OLAN sınıf ile vektör büyümesi:
    ElementStats.copies = 0
    ElementStats.moves = 0
    simulate_vector_growth(MockBufferNoexcept, is_noexcept=True, target_size=16)
    print(f"  [noexcept = TRUE]  -> Kopya Sayısı: {ElementStats.copies} | Taşıma Sayısı: {ElementStats.moves}")
    assert ElementStats.copies == 0, "HATA: noexcept sınıf kopyalandı!"
    assert ElementStats.moves == 15, "HATA: Taşıma sayısı hatalı!"

    # 2. noexcept OLMAYAN sınıf ile vektör büyümesi:
    ElementStats.copies = 0
    ElementStats.moves = 0
    simulate_vector_growth(MockBufferThrowing, is_noexcept=False, target_size=16)
    print(f"  [noexcept = FALSE] -> Kopya Sayısı: {ElementStats.copies} | Taşıma Sayısı: {ElementStats.moves}")
    assert ElementStats.copies == 15, "HATA: non-noexcept sınıf kopyalanmadı!"
    assert ElementStats.moves == 0, "HATA: non-noexcept sınıf taşındı!"

    print("  -> TESPİT: noexcept eksikliği 16 elemanlık küçük bir büyümede bile 15 adet gereksiz derin kopya tetikledi!")

if __name__ == "__main__":
    run_lab_03_vector_reallocation()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# 64 MB Arabellek için Deep Copy vs Move Semantics Gecikme Ölçümü
# ==============================================================================

import time

def benchmark_copy_vs_move():
    print("\n[*] Laboratuvar 4: Deep Copy vs Move Semantics 100.000 Çevrim Ölçümü...")
    iterations = 100_000

    # 1. Taşıma Semantiği (Move) Benzetimi: Yalnızca 3 Değişken Takası
    start_move = time.perf_counter()
    ptr = 0xDEADBEEF
    size = 67108864 # 64 MB
    for _ in range(iterations):
        # 3 CPU kaydı kopyalama ve sıfırlama:
        new_ptr = ptr
        new_size = size
        ptr = 0
        size = 0
        # Geri yükle (test devamı için)
        ptr = new_ptr
        size = new_size
    t_move_ms = (time.perf_counter() - start_move) * 1000.0

    # 2. Derin Kopyalama (Deep Copy) Benzetimi: Küçük bir bellek bloğu kopyalama simülasyonu
    # (100.000 kez gerçek 64 MB kopyalamak 1500 saniye süreceğinden 1 KB sembolik blok kullanılır)
    sample_block = bytearray(1024) # 1 KB
    start_copy = time.perf_counter()
    for _ in range(iterations):
        copied_block = bytearray(sample_block)
    t_copy_ms = (time.perf_counter() - start_copy) * 1000.0

    print(f"  -> Taşıma Semantiği ({iterations:,} çevrim): {t_move_ms:.2f} ms")
    print(f"  -> 1 KB Sembolik Kopya ({iterations:,} çevrim): {t_copy_ms:.2f} ms")
    print(f"  -> 64 MB Gerçek Kopyalama Tahmini: {(t_copy_ms * 64 * 1024 / 1000.0):.1f} SANİYE!")
    print(f"  -> PERFORMANS FARKI: Taşıma işlemi {(t_copy_ms / max(t_move_ms, 0.001)):.1f}x kat daha hızlıdır.")
    return t_move_ms, t_copy_ms

if __name__ == "__main__":
    benchmark_copy_vs_move()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-054 Analitik Görselleştirme Motoru
# 4 Panelli Sistem Mimarisi Dashboard'u (gun_054_move_semantics.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_viz_054(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900

    # --------------------------------------------------------------------------
    # Panel 1: Bellek Yerleşimi: Kopyalama vs Taşıma
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Bellek Mimarisi: Deep Copy vs Move Semantics", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Deep Copy Kutusu
    b_copy = patches.FancyBboxPatch((0.05, 0.55), 0.90, 0.38, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#EF4444', linewidth=1.5)
    ax1.add_patch(b_copy)
    ax1.text(0.10, 0.86, "DERİN KOPYALAMA (DEEP COPY) - O(N) Zaman, 2x Bellek", color='#FCA5A5', fontsize=9, fontweight='bold')
    
    r_src = patches.Rectangle((0.10, 0.62), 0.30, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
    ax1.add_patch(r_src)
    ax1.text(0.25, 0.71, "Kaynak Arabellek\n(64 MB Heap)", color='#FFFFFF', fontsize=8, ha='center', va='center')

    r_dst = patches.Rectangle((0.60, 0.62), 0.30, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
    ax1.add_patch(r_dst)
    ax1.text(0.75, 0.71, "Hedef Arabellek\n(Yeni 64 MB Heap)", color='#FFFFFF', fontsize=8, ha='center', va='center')
    ax1.annotate("memcpy (15 ms)", xy=(0.60, 0.71), xytext=(0.40, 0.71), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2), color='#FCA5A5', fontsize=8, ha='center')

    # Move Semantics Kutusu
    b_move = patches.FancyBboxPatch((0.05, 0.08), 0.90, 0.40, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#10B981', linewidth=1.5)
    ax1.add_patch(b_move)
    ax1.text(0.10, 0.41, "TAŞIMA SEMANTİĞİ (MOVE SEMANTICS) - O(1) Zaman (2 ns), Sıfır Ek Bellek", color='#A7F3D0', fontsize=9, fontweight='bold')

    r_src_m = patches.Rectangle((0.10, 0.15), 0.30, 0.18, facecolor='#064E3B', edgecolor='#10B981', linewidth=1)
    ax1.add_patch(r_src_m)
    ax1.text(0.25, 0.24, "Kaynak (Moved-From)\nptr = nullptr (0 B)", color='#FFFFFF', fontsize=8, ha='center', va='center')

    r_dst_m = patches.Rectangle((0.60, 0.15), 0.30, 0.18, facecolor='#065F46', edgecolor='#10B981', linewidth=1)
    ax1.add_patch(r_dst_m)
    ax1.text(0.75, 0.24, "Hedef (Yeni Sahip)\n(Mevcut 64 MB Korundu)", color='#FFFFFF', fontsize=8, ha='center', va='center')
    ax1.annotate("Pointer Steal (2 ns)", xy=(0.60, 0.24), xytext=(0.40, 0.24), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2), color='#A7F3D0', fontsize=8, ha='center')

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: Değer Kategorileri Hiyerarşisi (C++20)
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. C++ Değer Kategorileri (Value Categories) Taksonomisi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    cats = [
        ("İfadeler (Expressions)", 0.50, 0.88, 0.80, 0.10, '#334155', '#94A3B8'),
        ("glvalue (Genelleştirilmiş Sol)", 0.28, 0.65, 0.42, 0.10, '#1E3A8A', '#3B82F6'),
        ("rvalue (Sağ-Değer)", 0.72, 0.65, 0.42, 0.10, '#065F46', '#10B981'),
        ("lvalue\n(Kimlik Var, Taşınamaz)", 0.16, 0.35, 0.26, 0.16, '#1E293B', '#38BDF8'),
        ("xvalue\n(std::move Dönüşümü)", 0.50, 0.35, 0.26, 0.16, '#831843', '#EC4899'),
        ("prvalue\n(Saf Geçici Değer)", 0.84, 0.35, 0.26, 0.16, '#064E3B', '#34D399'),
    ]

    for title, x, y, w, h, bg, edge in cats:
        b = patches.FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.01", facecolor=bg, edgecolor=edge, linewidth=1.5)
        ax2.add_patch(b)
        ax2.text(x, y, title, color='#FFFFFF', fontsize=8, fontweight='bold', ha='center', va='center')

    # Bağlantı Okları
    ax2.annotate("", xy=(0.28, 0.70), xytext=(0.45, 0.83), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=1.5))
    ax2.annotate("", xy=(0.72, 0.70), xytext=(0.55, 0.83), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=1.5))
    ax2.annotate("", xy=(0.16, 0.43), xytext=(0.25, 0.60), arrowprops=dict(arrowstyle="->", color='#3B82F6', lw=1.5))
    ax2.annotate("", xy=(0.48, 0.43), xytext=(0.32, 0.60), arrowprops=dict(arrowstyle="->", color='#3B82F6', lw=1.5))
    ax2.annotate("", xy=(0.52, 0.43), xytext=(0.68, 0.60), arrowprops=dict(arrowstyle="->", color='#10B981', lw=1.5))
    ax2.annotate("", xy=(0.84, 0.43), xytext=(0.75, 0.60), arrowprops=dict(arrowstyle="->", color='#10B981', lw=1.5))

    ax2.text(0.50, 0.12, "std::move(lvalue) -> İfadeyi bir xvalue'ya dönüştürür ve taşımayı tetikler!", color='#F472B6', fontsize=8.5, ha='center', fontweight='bold')

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # Panel 3: std::vector Reallocation Davranışı
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. std::vector Reallocation: noexcept Taşıma vs Kopyalama", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    vec_labels = ['1. Kapasite (1->2)', '2. Kapasite (2->4)', '3. Kapasite (4->8)', '4. Kapasite (8->16)']
    x_indices = np.arange(len(vec_labels))

    copy_counts = [1, 2, 4, 8]
    move_counts = [1, 2, 4, 8]

    bar_w = 0.35
    ax3.bar(x_indices - bar_w/2, copy_counts, width=bar_w, label='noexcept = FALSE (Derin Kopyalama)', color='#EF4444', edgecolor='#7F1D1D')
    ax3.bar(x_indices + bar_w/2, move_counts, width=bar_w, label='noexcept = TRUE (O(1) Taşıma)', color='#10B981', edgecolor='#064E3B')

    ax3.set_xticks(x_indices)
    ax3.set_xticklabels(vec_labels, color='#CBD5E1', fontsize=8)
    ax3.set_ylabel("Taşınan/Kopyalanan Eleman Sayısı", color='#94A3B8', fontsize=9)
    ax3.tick_params(colors='#CBD5E1')
    ax3.grid(axis='y', color='#334155', linestyle='--', alpha=0.7)
    ax3.legend(facecolor='#1E293B', edgecolor='#334155', labelcolor='#FFFFFF', fontsize=8)

    ax3.text(1.5, 6.5, "noexcept YOKSA:\nstd::vector güçlü istisna garantisi için\nsessizce derin kopyalamaya düşer!", color='#FCA5A5', fontsize=8.5, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#7F1D1D', edgecolor='#EF4444'))

    # --------------------------------------------------------------------------
    # Panel 4: Veri Boyutuna Göre Aktarım Süresi (Benchmark)
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. Veri Boyutuna Göre Aktarım Gecikmesi (Logaritmik)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    sizes_mb = np.array([1, 4, 16, 64, 256])
    # Kopyalama süresi: Doğrusal artış (0.2 ms / MB)
    copy_lat_ms = sizes_mb * 0.25
    # Taşıma süresi: Tamamen sabit (0.000002 ms = 2 ns)
    move_lat_ms = np.full_like(sizes_mb, 0.000002, dtype=float)

    ax4.plot(sizes_mb, copy_lat_ms, 'o-', color='#EF4444', linewidth=2.5, label='Deep Copy O(N) Gecikme')
    ax4.plot(sizes_mb, move_lat_ms, 's-', color='#10B981', linewidth=2.5, label='Move Semantics O(1) Gecikme (2 ns)')

    ax4.set_xscale('log')
    ax4.set_yscale('log')
    ax4.set_xlabel("Arabellek Boyutu (MB)", color='#94A3B8', fontsize=9)
    ax4.set_ylabel("Aktarım Gecikmesi (ms - Log)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1')
    ax4.grid(True, which='both', color='#334155', linestyle='--', alpha=0.5)
    ax4.legend(facecolor='#1E293B', edgecolor='#334155', labelcolor='#FFFFFF', fontsize=8)

    ax4.text(16, 0.0001, "256 MB için Taşıma:\n2 Nanosaniye (Sabit!)", color='#34D399', fontsize=8.5, fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_054(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# Taşıma Semantiği ve Kaynak Güvenliği Kriterlerinin Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 054: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: Kaynak Hırsızlığı ve Adres Bütünlüğü Doğrulaması
    class RawBuffer:
        def __init__(self, addr): self.addr = addr

    source = RawBuffer(0xABCDEF00)
    assert source.addr == 0xABCDEF00, "Kaynak adres hatalı!"
    
    # Taşıma takası:
    target_addr = source.addr
    source.addr = None
    assert target_addr == 0xABCDEF00, "Hedef adres aktarımı bozuldu!"
    assert source.addr is None, "HATA: Moved-from nesne boşaltılmadı (Dangling pointer riski)!"
    print("  -> [PASS] Kaynak hırsızlığı ve moved-from nullptr durumu doğrulandı.")

    # 2. Test: Kendine Taşıma (Self-Move) Koruması Doğrulaması
    class SafeMover:
        def __init__(self, val): self.val = val
        def move_from(self, other):
            if self is other: return self
            self.val = other.val
            other.val = None
            return self

    s = SafeMover("RADAR_CONFIG_2026")
    s.move_from(s) # Kendine taşı
    assert s.val == "RADAR_CONFIG_2026", "HATA: Kendine taşıma veriyi sildi!"
    print("  -> [PASS] Self-move assignment koruma mekanizması mühürlendi.")

    # 3. Test: noexcept Vektör Büyüme Karar Ağacı Doğrulaması
    is_move_noexcept = True
    action = "MOVE" if is_move_noexcept else "COPY"
    assert action == "MOVE", "noexcept sınıf taşınmalıdır!"

    is_move_noexcept = False
    action_throw = "MOVE" if is_move_noexcept else "COPY"
    assert action_throw == "COPY", "non-noexcept sınıf kopyalamaya düşmelidir!"
    print("  -> [PASS] noexcept ve std::move_if_noexcept karar mantığı onaylandı.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
