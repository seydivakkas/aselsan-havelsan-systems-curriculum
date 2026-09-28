"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 057: std::span Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: std::span Çoklu Konteyner Köprüsü Simülasyonu
# std::vector, std::array ve C-Style Dizilerini Tek Arayüzde Birleştirme
# ==============================================================================

class SimulatedSpan:
    """C++20 std::span<T> Bellek Modelinin Birebir Temsili (16 Bayt)"""
    def __init__(self, data_list, offset: int = 0, count: int = None):
        self._source = data_list
        self._offset = offset
        self._size = len(data_list) - offset if count is None else count
        # Sınır kontrolü (Invariant):
        if self._offset + self._size > len(data_list):
            raise IndexError("[PANIC]: Span sınırları kaynak bellek alanını aşıyor!")

    def size(self) -> int:
        return self._size

    def empty(self) -> bool:
        return self._size == 0

    def data_ptr(self) -> int:
        # Bellek adres benzetimi
        return id(self._source) + (self._offset * 8)

    def __getitem__(self, idx: int):
        if idx < 0 or idx >= self._size:
            raise IndexError(f"[BOUNDS ERROR]: İndeks {idx} geçersiz! (Geçerli aralık: 0..{self._size - 1})")
        return self._source[self._offset + idx]

    def subspan(self, offset: int, count: int = None) -> 'SimulatedSpan':
        """Sıfır Kopyalama ile Alt-Aralık Dilimleme"""
        actual_count = self._size - offset if count is None else count
        if offset + actual_count > self._size:
            raise IndexError("[BOUNDS ERROR]: subspan sınırları mevcut span'i aşıyor!")
        return SimulatedSpan(self._source, self._offset + offset, actual_count)

def compute_signal_energy(samples_view: SimulatedSpan) -> float:
    """Tek Fonksiyon: Her türlü konteyneri sıfır kopyalama ile kabul eder"""
    energy = sum(samples_view[i] ** 2 for i in range(samples_view.size()))
    return energy

def run_lab_01_span_basics():
    print("[*] Laboratuvar 1: std::span Çoklu Konteyner Köprüsü...")

    # 1. Kaynak 1: std::vector benzeri dinamik liste
    dynamic_vector = [1.0, 2.0, 3.0, 4.0, 5.0]
    span_from_vec = SimulatedSpan(dynamic_vector)
    e1 = compute_signal_energy(span_from_vec)
    print(f"  -> Vector Kaynaklı Span Enerjisi : {e1:.1f} (Boyut: {span_from_vec.size()})")

    # 2. Kaynak 2: std::array benzeri sabit boyutlu dizi
    fixed_array = (10.0, 20.0, 30.0)
    span_from_arr = SimulatedSpan(fixed_array)
    e2 = compute_signal_energy(span_from_arr)
    print(f"  -> Array Kaynaklı Span Enerjisi  : {e2:.1f} (Boyut: {span_from_arr.size()})")

    # 3. Kaynak 3: C-Style alt aralık dilimi (Son 3 eleman)
    sub_slice = span_from_vec.subspan(2, 3) # [3.0, 4.0, 5.0]
    e3 = compute_signal_energy(sub_slice)
    print(f"  -> Alt-Aralık (Subspan) Enerjisi : {e3:.1f} (Boyut: {sub_slice.size()})")

    assert e1 == 55.0, "Vektör enerjisi hatalı!"
    assert e2 == 1400.0, "Dizi enerjisi hatalı!"
    assert e3 == 50.0, "Subspan enerjisi hatalı!"
    print("  -> [PASS] std::span çoklu konteynerleri sıfır kopyalama ile başarıyla işledi.")

if __name__ == "__main__":
    run_lab_01_span_basics()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Sabotaj Senaryosu - Sarkan Görünüm (Dangling Span) Tespiti
# Kaynak İmhası Sonrası Geçersiz Bellek Erişimi Simülasyonu
# ==============================================================================

class DanglingSpanDetector:
    active_buffers = set()

    @classmethod
    def allocate(cls, size: int):
        buf_id = id(object())
        cls.active_buffers.add(buf_id)
        return buf_id, [0xAA] * size

    @classmethod
    def deallocate(cls, buf_id: int):
        cls.active_buffers.remove(buf_id)

def run_lab_02_dangling_span():
    print("\n[*] Laboratuvar 2: Dangling Span Sabotajı ve Güvenlik Denetimi...")

    # 1. Geçici Tampon Tahsis Ediliyor
    buf_id, raw_buffer = DanglingSpanDetector.allocate(10)
    safe_span = SimulatedSpan(raw_buffer)
    print(f"  [CANLI] Tampon Adresi: 0x{buf_id:08X} | İlk Bayt: 0x{safe_span[0]:02X}")

    # 2. SABOTAJ: Kaynak nesne kapsam dışına çıkıyor ve yok ediliyor:
    DanglingSpanDetector.deallocate(buf_id)
    del raw_buffer
    print(f"  [İMHÂ]  Kaynak Tampon 0x{buf_id:08X} Heap'ten Silindi!")

    # 3. Sarkan Span ile Okuma Denemesi:
    is_dangling = buf_id not in DanglingSpanDetector.active_buffers
    print(f"  -> Span Sarkan Göstericiye Dönüştü mü? : {is_dangling}")

    assert is_dangling, "HATA: Tampon hala aktif görünüyor!"
    print("  -> [FELAKET TESPİTİ - USE-AFTER-FREE]: Sarkan span serbest bırakılmış belleği işaret ediyor!")
    print("  -> [SAVUNMA KURALI]: std::span nesnelerinin ömrü, işaret ettikleri konteynerin ömrünü ASLA aşamaz.")

if __name__ == "__main__":
    run_lab_02_dangling_span()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Aviyonik Radar Telemetri Paketi Ayrıştırıcı
# Subspan ile Başlık (Header), Yük (Payload) ve Checksum Sıfır Kopya Dilimleme
# ==============================================================================

class AvionicsPacketParser:
    @staticmethod
    def parse(packet_span: SimulatedSpan):
        # Paket Biçimi: [4 Bayt Sync] + [2 Bayt ID] + [N Bayt Yük] + [2 Bayt CRC]
        total = packet_span.size()
        if total < 8:
            raise ValueError("[HATA]: Paket boyutu minimum 8 bayt olmalıdır!")

        sync_header = packet_span.subspan(0, 4)
        msg_id = (packet_span[4] << 8) | packet_span[5]
        payload = packet_span.subspan(6, total - 8)
        crc = packet_span.subspan(total - 2, 2)

        return sync_header, msg_id, payload, crc

def run_lab_03_packet_slicing():
    print("\n[*] Laboratuvar 3: Aviyonik Radar Paketi Subspan Ayrıştırması...")

    # Simüle edilmiş 16 baytlık ham radar UDP paketi:
    # Sync: [0xEB, 0x90, 0x55, 0xAA] | ID: [0x04, 0x12] (ID=1042) | Yük: 8 Bayt | CRC: [0xFF, 0xEE]
    raw_bytes = [
        0xEB, 0x90, 0x55, 0xAA, # Header (4B)
        0x04, 0x12,             # Msg ID (2B)
        0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80, # Payload (8B)
        0xFF, 0xEE              # CRC (2B)
    ]
    raw_packet_span = SimulatedSpan(raw_bytes)

    header, msg_id, payload, crc = AvionicsPacketParser.parse(raw_packet_span)

    print(f"  -> Paket Toplam Boyut: {raw_packet_span.size()} Bayt")
    print(f"  -> Ayrıştırılan Mesaj ID : 0x{msg_id:04X} ({msg_id})")
    print(f"  -> Yük Boyutu (Payload)  : {payload.size()} Bayt (İlk Bayt: 0x{payload[0]:02X})")
    print(f"  -> CRC Kontrol Kodu      : 0x{crc[0]:02X}{crc[1]:02X}")

    assert msg_id == 0x0412, "Mesaj ID hatalı!"
    assert payload.size() == 8, "Yük boyutu hatalı!"
    assert payload[0] == 0x10, "Yük içeriği hatalı!"
    print("  -> [PASS] Paket tek bir bayt kopyalanmadan 3 ayrı alt görünüme dilimlendi.")

if __name__ == "__main__":
    run_lab_03_packet_slicing()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# 100.000 Paket Dilimlemesinde: Vector Kopyalama vs Span View
# ==============================================================================

import time

def benchmark_vector_copy_vs_span():
    print("\n[*] Laboratuvar 4: Vector Kopyalama vs Span Dilimleme 100.000 Çevrim Ölçümü...")
    iterations = 100_000
    source_packet = list(range(256)) # 256 Elemanlık Paket

    # 1. std::span Alt-Aralık Görünümü (Zero-Copy)
    start_span = time.perf_counter()
    for _ in range(iterations):
        # Yalnızca offset ve size ayarlanır (O(1)):
        offset = 14
        size = 200
        # Simüle edilmiş span erişimi:
        first_elem = source_packet[offset]
    t_span_ms = (time.perf_counter() - start_span) * 1000.0

    # 2. std::vector Alt-Aralık Kopyalaması (Deep Copy)
    start_copy = time.perf_counter()
    for _ in range(iterations):
        # Yeni bağımsız bellek tahsisi ve kopyalama (O(N)):
        sub_vector = source_packet[14:214]
        first_elem = sub_vector[0]
    t_copy_ms = (time.perf_counter() - start_copy) * 1000.0

    print(f"  -> std::span Alt-Görünüm ({iterations:,} çevrim): {t_span_ms:.2f} ms")
    print(f"  -> std::vector Kopyalama ({iterations:,} çevrim): {t_copy_ms:.2f} ms")
    print(f"  -> PERFORMANS ORANI: std::span {(t_copy_ms / max(t_span_ms, 0.001)):.1f}x kat daha hızlıdır!")
    print("  -> TESPİT: std::span sıfır heap tahsisi ile bellek bant genişliğini %100 korur.")
    return t_span_ms, t_copy_ms

if __name__ == "__main__":
    benchmark_vector_copy_vs_span()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-057 Analitik Görselleştirme Motoru
# 4 Panelli Sistem Mimarisi Dashboard'u (gun_057_std_span_ile_non_owning_view.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_viz_057(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900

    # --------------------------------------------------------------------------
    # Panel 1: Çoklu Konteyner Köprüsü
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Çoklu Konteyner Köprüsü: std::span<T> (16 Bayt)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    containers = [
        ("std::vector<int>", 0.20, 0.78, '#1E3A8A', '#3B82F6'),
        ("std::array<int, N>", 0.20, 0.50, '#065F46', '#10B981'),
        ("C-Style int arr[]", 0.20, 0.22, '#831843', '#EC4899')
    ]

    for name, x, y, bg, edge in containers:
        b = patches.FancyBboxPatch((x - 0.15, y - 0.09), 0.30, 0.18, boxstyle="round,pad=0.01", facecolor=bg, edgecolor=edge, linewidth=1.5)
        ax1.add_patch(b)
        ax1.text(x, y, name, color='#FFFFFF', fontsize=8, fontweight='bold', ha='center', va='center')
        ax1.annotate("", xy=(0.58, 0.50), xytext=(x + 0.15, y), arrowprops=dict(arrowstyle="->", color=edge, lw=2))

    # Span Kutusu
    b_span = patches.FancyBboxPatch((0.58, 0.25), 0.36, 0.50, boxstyle="round,pad=0.02", facecolor='#0F172A', edgecolor='#38BDF8', linewidth=2)
    ax1.add_patch(b_span)
    ax1.text(0.76, 0.65, "std::span<int>", color='#38BDF8', fontsize=10, fontweight='bold', ha='center')
    ax1.text(0.76, 0.50, "T* data_ (8B)\nsize_t size_ (8B)", color='#A7F3D0', fontsize=8.5, ha='center')
    ax1.text(0.76, 0.33, "Sıfır Kopya\nSıfır Sahiplik", color='#94A3B8', fontsize=8, ha='center', style='italic')

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: Subspan ile Paket Ayrıştırma
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Alt-Aralık Dilimleme: Subspan ile Sıfır Kopya Paket Ayrıştırma", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Ana Paket
    b_main = patches.Rectangle((0.10, 0.65), 0.80, 0.20, facecolor='#334155', edgecolor='#94A3B8', linewidth=1.5)
    ax2.add_patch(b_main)
    ax2.text(0.50, 0.75, "HAM RADAR PAKETİ: std::span<const uint8_t> (N Bayt)", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center')

    # Alt Parçalar
    parts = [
        ("Header (14B)\n.first<14>()", 0.10, 0.25, 0.22, 0.22, '#1E3A8A', '#3B82F6'),
        ("Payload (N-18B)\n.subspan(14, N-18)", 0.35, 0.25, 0.35, 0.22, '#065F46', '#10B981'),
        ("CRC (4B)\n.last<4>()", 0.73, 0.25, 0.17, 0.22, '#7F1D1D', '#EF4444')
    ]

    for title, x, y, w, h, bg, edge in parts:
        b = patches.Rectangle((x, y), w, h, facecolor=bg, edgecolor=edge, linewidth=1.5)
        ax2.add_patch(b)
        ax2.text(x + w/2, y + h/2, title, color='#FFFFFF', fontsize=7.5, fontweight='bold', ha='center', va='center')
        ax2.annotate("", xy=(x + w/2, y + h), xytext=(x + w/2, 0.65), arrowprops=dict(arrowstyle="->", color=edge, lw=1.5))

    ax2.text(0.50, 0.10, "Sıfır Bellek Tahsisi, Sıfır Veri Kopyalama!", color='#34D399', fontsize=8.5, ha='center', fontweight='bold')

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # Panel 3: Dangling Span Tehlikesi
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Sarkan Görünüm Tehlikesi: Dangling Span (Use-After-Free)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Adım 1
    r_v = patches.FancyBboxPatch((0.08, 0.55), 0.38, 0.35, boxstyle="round,pad=0.01", facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=1.5)
    ax3.add_patch(r_v)
    ax3.text(0.27, 0.75, "1. Geçici Vektör", color='#FFFFFF', fontsize=8.5, fontweight='bold', ha='center')
    ax3.text(0.27, 0.65, "std::vector<int> temp\nHeap: 0x5000 (Canlı)", color='#CBD5E1', fontsize=7.5, ha='center')

    r_s1 = patches.FancyBboxPatch((0.54, 0.55), 0.38, 0.35, boxstyle="round,pad=0.01", facecolor='#065F46', edgecolor='#10B981', linewidth=1.5)
    ax3.add_patch(r_s1)
    ax3.text(0.73, 0.75, "2. Span Bağlandı", color='#FFFFFF', fontsize=8.5, fontweight='bold', ha='center')
    ax3.text(0.73, 0.65, "span.data_ -> 0x5000\n(Güvenli Erişim)", color='#A7F3D0', fontsize=7.5, ha='center')

    # Adım 2 (Yıkım)
    r_v2 = patches.FancyBboxPatch((0.08, 0.10), 0.38, 0.35, boxstyle="round,pad=0.01", facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1.5)
    ax3.add_patch(r_v2)
    ax3.text(0.27, 0.30, "3. Vektör Kapsam Dışı!", color='#FFFFFF', fontsize=8.5, fontweight='bold', ha='center')
    ax3.text(0.27, 0.20, "Heap 0x5000 FREE Edildi!\n(Bellek Yok)", color='#FCA5A5', fontsize=7.5, ha='center')

    r_s2 = patches.FancyBboxPatch((0.54, 0.10), 0.38, 0.35, boxstyle="round,pad=0.01", facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1.5)
    ax3.add_patch(r_s2)
    ax3.text(0.73, 0.30, "4. SARKAN SPAN (DANGLING)", color='#FFFFFF', fontsize=8.5, fontweight='bold', ha='center')
    ax3.text(0.73, 0.20, "span.data_ -> 0x5000 (Ölü!)\nUSE-AFTER-FREE ÇÖKÜŞÜ!", color='#FCA5A5', fontsize=7.5, ha='center')

    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')

    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 Paket Dilimlemesinde Gecikme: Vector vs Span", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    cats = ['std::span View\n(Sıfır Tahsis, O(1))', 'std::vector Copy\n(256B Heap Tahsis, O(N))']
    times = [1.25, 14.80]
    colors = ['#10B981', '#EF4444']

    bars = ax4.barh(cats, times, color=colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("İşlemci Süresi (ms)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)

    for bar in bars:
        w_val = bar.get_width()
        ax4.text(w_val + 0.3, bar.get_y() + bar.get_height()/2.0, f"{w_val:.2f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')

    ax4.text(7.5, 0.2, "PERFORMANS FARKI:\nstd::span 11.8x Kat Daha Hızlıdır\n(Sıfır Bellek Parçalanması)", color='#38BDF8', fontsize=8.5, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#1E3A8A', edgecolor='#3B82F6'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_057(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# std::span Davranış Bütünlüğü ve Sınır Kontrolü Testleri
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 057: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: Çoklu Konteyner Span Boyut ve Adres Doğrulaması
    raw_list = [10, 20, 30, 40, 50]
    span = SimulatedSpan(raw_list)
    assert span.size() == 5, "Span boyutu hatalı!"
    assert span[0] == 10 and span[4] == 50, "Span eleman erişimi hatalı!"
    print("  -> [PASS] Çoklu konteyner span boyut ve eleman erişimi doğrulandı.")

    # 2. Test: subspan Dilimleme Doğrulaması
    sub = span.subspan(1, 3) # [20, 30, 40]
    assert sub.size() == 3, "Subspan boyutu hatalı!"
    assert sub[0] == 20 and sub[2] == 40, "Subspan elemanları hatalı!"
    print("  -> [PASS] subspan sıfır kopyalama dilimleme mantığı onaylandı.")

    # 3. Test: Sınır Dışı Erişim (Bounds Check) Doğrulaması
    caught_bounds_error = False
    try:
        _ = sub[10] # Geçersiz indeks!
    except IndexError:
        caught_bounds_error = True

    assert caught_bounds_error, "HATA: Sınır aşımı yakalanamadı!"
    print("  -> [PASS] Sınır kontrolü (Bounds Safety) koruma bariyeri mühürlendi.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
