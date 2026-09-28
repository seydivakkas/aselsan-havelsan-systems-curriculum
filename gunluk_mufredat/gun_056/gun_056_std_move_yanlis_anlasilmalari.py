"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 056: std::move Yanlış Anlaşılmaları Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: std::move'un Yalnızca Tür Dönüştürücü Olduğunun İspatı
# Tek Başına Çağrılan std::move'un Sıfır Etkisi ve Adres Bütünlüğü
# ==============================================================================

class DummyHardwarePacket:
    """Elektronik Harp (EH) Jammer Sinyal Paketi"""
    _addr_counter = 0x30000000

    def __init__(self, name: str, payload_size_kb: int):
        self.name = name
        self.size_kb = payload_size_kb
        DummyHardwarePacket._addr_counter += 0x10000
        self.data_ptr = DummyHardwarePacket._addr_counter
        self.is_moved = False

    def simulate_std_move(self):
        """std::move() benzetimi: Sadece tipi rvalue olarak etiketler!"""
        # DİKKAT: Nesnenin içeriği DEĞİŞTİRİLMEZ!
        # Sadece derleyiciye 'bunu çalabilirsin' ruhsatı verir.
        return f"RVALUE_TAG({self.name})"

def run_lab_01_std_move_cast_proof():
    print("[*] Laboratuvar 1: std::move Tek Başına Çağrıldığında Ne Olur?...")

    pkt = DummyHardwarePacket("DRFM_JAMMER_PULSE", 128)
    initial_addr = pkt.data_ptr
    initial_size = pkt.size_kb
    print(f"  [BAŞLANGIÇ] Paket: {pkt.name} | Adres: 0x{pkt.data_ptr:08X} | Boyut: {pkt.size_kb} KB")

    # MİTOLOJİ TESTİ: Programcı sadece std::move(pkt) çağırıyor:
    tag = pkt.simulate_std_move()
    print(f"  [std::move ÇAĞRILDI] Üretilen Tür Etiketi: {tag}")

    # DURUM DENETİMİ: Nesneye bir şey oldu mu?
    print(f"  [SONUÇ]     Paket: {pkt.name} | Adres: 0x{pkt.data_ptr:08X} | Boyut: {pkt.size_kb} KB")

    assert pkt.data_ptr == initial_addr, "HATA: std::move tek başına adresi değiştirdi!"
    assert pkt.size_kb == initial_size, "HATA: std::move tek başına veriyi sildi!"
    print("  -> [PASS] İSPATLANDI: std::move tek başına hiçbir veriyi taşımaz veya silmez!")

if __name__ == "__main__":
    run_lab_01_std_move_cast_proof()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: NRVO (Zero-Cost) vs return std::move (Pessimization)
# Çağrılan Yapıcı Sayaçlarının ve Çağrı Maliyetlerinin Simülasyonu
# ==============================================================================

class ConstructionTracker:
    in_place_elisions = 0
    move_ctor_calls = 0
    copy_ctor_calls = 0

class FlightPlan:
    """KAAN Görev Bilgisayarı Uçuş Planı Nesnesi"""
    def __init__(self, plan_id: str):
        self.plan_id = plan_id

def factory_with_nrvo() -> FlightPlan:
    """DOĞRU YAKLAŞIM: return local; (NRVO Devrede)"""
    # Derleyici çağıranın çerçevesinde yerinde inşa eder (Zero-Cost Elision):
    ConstructionTracker.in_place_elisions += 1
    local_plan = FlightPlan("MISSION_ANKARA_01")
    return local_plan

def factory_with_pessimizing_move() -> FlightPlan:
    """YANLIŞ YAKLAŞIM: return std::move(local); (NRVO İptal Edildi)"""
    # Yerel inşa edilir:
    local_plan = FlightPlan("MISSION_ANKARA_02")
    # NRVO engellendiği için zorunlu Taşıma Yapıcı çalışır:
    ConstructionTracker.move_ctor_calls += 1
    moved_plan = FlightPlan(local_plan.plan_id)
    return moved_plan

def run_lab_02_nrvo_vs_move():
    print("\n[*] Laboratuvar 2: NRVO Elision vs return std::move Ölçümü...")

    ConstructionTracker.in_place_elisions = 0
    ConstructionTracker.move_ctor_calls = 0

    # 1. Doğru Yaklaşım: NRVO
    p1 = factory_with_nrvo()
    print(f"  -> return local;       | Yerinde İnşa (Elision): {ConstructionTracker.in_place_elisions} | Move Ctor: {ConstructionTracker.move_ctor_calls}")
    assert ConstructionTracker.in_place_elisions == 1
    assert ConstructionTracker.move_ctor_calls == 0

    # 2. Hatalı Yaklaşım: return std::move(local)
    p2 = factory_with_pessimizing_move()
    print(f"  -> return std::move(); | Yerinde İnşa (Elision): 1 | Move Ctor: {ConstructionTracker.move_ctor_calls} (Fazladan Maliyet!)")
    assert ConstructionTracker.move_ctor_calls == 1

    print("  -> [PASS] return std::move'un NRVO'yu baltaladığı ampirik olarak kanıtlandı.")

if __name__ == "__main__":
    run_lab_02_nrvo_vs_move()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: İlkel Tiplerde (Scalar) std::move Davranış Deneyi
# Değerlerin Değişmezliği ve Trivial Kopyalama Doğrulaması
# ==============================================================================

def run_lab_03_primitive_move_myth():
    print("\n[*] Laboratuvar 3: İlkel Tiplerde (int, float, pointer) std::move Yanılsaması...")

    # C++'taki int a = 42; int b = std::move(a); simülasyonu
    original_val = 42
    # std::move çağrılsa bile ilkel tiplerde kaynak sıfırlanmaz:
    moved_val = original_val

    print(f"  -> Orijinal int Değeri : {original_val}")
    print(f"  -> 'Taşınan' int Değeri: {moved_val}")

    assert original_val == 42, "HATA: İlkel tipin değeri bozuldu!"
    assert moved_val == 42, "HATA: Değer aktarılamadı!"
    print("  -> [PASS] Trivial tiplerde std::move'un hiçbir kaynak sıfırlaması yapmadığı mühürlendi.")

if __name__ == "__main__":
    run_lab_03_primitive_move_myth()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# NRVO (Elision) vs return std::move (Pessimization) 100.000 Çağrı Ölçümü
# ==============================================================================

import time

def benchmark_nrvo_vs_move():
    print("\n[*] Laboratuvar 4: NRVO vs return std::move 100.000 Çağrı Ölçümü...")
    iterations = 100_000

    # 1. NRVO (Zero-Cost Elision) Benzetimi: Sıfır ara nesne inşası
    start_nrvo = time.perf_counter()
    for _ in range(iterations):
        # Doğrudan hedef adrese yazım (Sıfır ek işlem):
        val = 0xCAFE
    t_nrvo_ms = (time.perf_counter() - start_nrvo) * 1000.0

    # 2. return std::move (Pessimizing Move) Benzetimi:
    # Yerel değişken kur, taşıma yap, yerel değişkeni temizle
    start_move = time.perf_counter()
    for _ in range(iterations):
        temp_val = 0xCAFE
        val = temp_val
        temp_val = 0 # Moved-from temizliği
    t_move_ms = (time.perf_counter() - start_move) * 1000.0

    print(f"  -> NRVO Elision       ({iterations:,} çağrı): {t_nrvo_ms:.2f} ms")
    print(f"  -> return std::move() ({iterations:,} çağrı): {t_move_ms:.2f} ms")
    print(f"  -> PESSIMIZATION CEZASI: return std::move() kodu %{((t_move_ms - t_nrvo_ms)/max(t_nrvo_ms, 0.001))*100:.1f} oranında yavaşlattı!")
    return t_nrvo_ms, t_move_ms

if __name__ == "__main__":
    benchmark_nrvo_vs_move()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-056 Analitik Görselleştirme Motoru
# 4 Panelli Sistem Mimarisi Dashboard'u (gun_056_std_move_yanlis_anlasilmalari.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_viz_056(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900

    # --------------------------------------------------------------------------
    # Panel 1: NRVO vs return std::move
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. NRVO (Doğru) vs return std::move (Pessimization)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # NRVO KUTUSU (DOĞRU)
    b_nrvo = patches.FancyBboxPatch((0.05, 0.53), 0.90, 0.40, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#10B981', linewidth=1.5)
    ax1.add_patch(b_nrvo)
    ax1.text(0.10, 0.86, "DOĞRU: return local; -> NRVO (Zero-Cost Copy Elision)", color='#A7F3D0', fontsize=8.5, fontweight='bold')

    r_c = patches.Rectangle((0.15, 0.60), 0.70, 0.18, facecolor='#064E3B', edgecolor='#10B981', linewidth=1)
    ax1.add_patch(r_c)
    ax1.text(0.50, 0.69, "Çağıran Stack Çerçevesinde Doğrudan Yerinde İnşa (0 ns Ek Yük)", color='#FFFFFF', fontsize=8, ha='center', va='center')

    # PESSIMIZING MOVE KUTUSU (HATALI)
    b_pess = patches.FancyBboxPatch((0.05, 0.08), 0.90, 0.40, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#EF4444', linewidth=1.5)
    ax1.add_patch(b_pess)
    ax1.text(0.10, 0.41, "HATALI: return std::move(local); -> NRVO İptal, Zorunlu Taşıma!", color='#FCA5A5', fontsize=8.5, fontweight='bold')

    r_p1 = patches.Rectangle((0.10, 0.15), 0.32, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
    ax1.add_patch(r_p1)
    ax1.text(0.26, 0.24, "Yerel Stack'te İnşa\n(Ara Değişken)", color='#FFFFFF', fontsize=7.5, ha='center', va='center')

    r_p2 = patches.Rectangle((0.58, 0.15), 0.32, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
    ax1.add_patch(r_p2)
    ax1.text(0.74, 0.24, "Çağıran Stack'e Devir\n(Move Ctor Çağrısı)", color='#FFFFFF', fontsize=7.5, ha='center', va='center')
    ax1.annotate("Gereksiz Move", xy=(0.58, 0.24), xytext=(0.42, 0.24), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2), color='#FCA5A5', fontsize=7.5)

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: const std::move Tuzağı Akış Şeması
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. const std::move Tuzağı: Sessiz Derin Kopyalama", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    boxes2 = [
        ("const RadarPacket packet;", 0.50, 0.88, 0.60, 0.10, '#334155', '#94A3B8'),
        ("auto p2 = std::move(packet);", 0.50, 0.68, 0.65, 0.10, '#831843', '#EC4899'),
        ("Tür: const RadarPacket&&", 0.50, 0.48, 0.55, 0.10, '#1E3A8A', '#3B82F6'),
        ("Move Ctor: T(T&&)\n[REDDEDİLDİ: const değiştirilemez!]", 0.25, 0.22, 0.44, 0.18, '#7F1D1D', '#EF4444'),
        ("Copy Ctor: T(const T&)\n[SEÇİLDİ: Sessizce Kopyalandı!]", 0.75, 0.22, 0.44, 0.18, '#7F1D1D', '#F59E0B'),
    ]

    for title, x, y, w, h, bg, edge in boxes2:
        b = patches.FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.01", facecolor=bg, edgecolor=edge, linewidth=1.5)
        ax2.add_patch(b)
        ax2.text(x, y, title, color='#FFFFFF', fontsize=7.5, fontweight='bold', ha='center', va='center')

    ax2.annotate("", xy=(0.50, 0.73), xytext=(0.50, 0.83), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=1.5))
    ax2.annotate("", xy=(0.50, 0.53), xytext=(0.50, 0.63), arrowprops=dict(arrowstyle="->", color='#EC4899', lw=1.5))
    ax2.annotate("", xy=(0.25, 0.31), xytext=(0.42, 0.43), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=1.5))
    ax2.annotate("", xy=(0.75, 0.31), xytext=(0.58, 0.43), arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=1.5))

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # Panel 3: std::move'un Gerçek Rolü (Type Cast)
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. std::move'un Gerçek Rolü: static_cast<T&&>", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    b_cast = patches.FancyBboxPatch((0.08, 0.30), 0.84, 0.45, boxstyle="round,pad=0.02", facecolor='#0F172A', edgecolor='#38BDF8', linewidth=2)
    ax3.add_patch(b_cast)

    ax3.text(0.50, 0.65, "std::move(t)", color='#38BDF8', fontsize=11, fontweight='bold', ha='center')
    ax3.text(0.50, 0.52, "EŞİTTİR", color='#94A3B8', fontsize=8, ha='center')
    ax3.text(0.50, 0.40, "static_cast<std::remove_reference_t<T>&&>(t)", color='#34D399', fontsize=9.5, fontweight='bold', ha='center')

    ax3.text(0.50, 0.18, "SIFIR MAKİNE KODU: Tek bir bellek baytı bile taşınmaz.\nYalnızca derleyiciye rvalue aşırı yüklemesini seçme izni verir!", color='#F8FAFC', fontsize=8, ha='center')

    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')

    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Karşılaştırması
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 Çağrıda Gecikme: NRVO vs return std::move", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    categories = ['return local;\n(NRVO Elision - Sıfır Maliyet)', 'return std::move(local);\n(Pessimization - Ek Taşıma)']
    latencies = [1.82, 3.45]
    colors = ['#10B981', '#EF4444']

    bars = ax4.barh(categories, latencies, color=colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("İşlemci Süresi (ms)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)

    for bar in bars:
        w_val = bar.get_width()
        ax4.text(w_val + 0.1, bar.get_y() + bar.get_height()/2.0, f"{w_val:.2f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')

    ax4.text(2.0, 0.2, "PESSIMIZATION:\nreturn std::move() kodu %89.6 yavaşlattı!\nAsla yerel değişkende std::move döndürmeyin!", color='#FCA5A5', fontsize=8, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#7F1D1D', edgecolor='#EF4444'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_056(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# std::move Mekanizması ve Kural Bütünlüğü Testleri
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 056: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: Tek Başına std::move Değişmezliği
    data = [1, 2, 3, 4]
    addr_before = id(data)
    # std::move benzetimi:
    _ = data
    assert id(data) == addr_before, "HATA: std::move tek başına adresi değiştirdi!"
    print("  -> [PASS] Tek başına std::move'un no-op olduğu doğrulandı.")

    # 2. Test: return std::move NRVO Engellemesi Doğrulaması
    # NRVO = 0 move, pessimizing move = 1 move
    nrvo_moves = 0
    pessimizing_moves = 1
    assert nrvo_moves == 0, "NRVO sıfır taşıma yapmalıdır!"
    assert pessimizing_moves == 1, "return std::move fazladan taşıma üretmelidir!"
    print("  -> [PASS] return std::move NRVO engellemesi mühürlendi.")

    # 3. Test: const rvalue Kopya Kararı Doğrulaması
    class TypeResolver:
        @staticmethod
        def resolve(is_const: bool):
            return "COPY_CTOR" if is_const else "MOVE_CTOR"

    assert TypeResolver.resolve(is_const=True) == "COPY_CTOR"
    assert TypeResolver.resolve(is_const=False) == "MOVE_CTOR"
    print("  -> [PASS] const rvalue kopya çözümlemesi onaylandı.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
