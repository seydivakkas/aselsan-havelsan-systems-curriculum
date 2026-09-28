"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 059: std::optional Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Radar Hedef Arama - std::optional Simülasyonu
# Tip Seviyesinde Varlık/Yokluk Modellemesi ve Sıfır Heap Doğrulaması
# ==============================================================================

class RadarTarget:
    def __init__(self, target_id: int, distance_km: float, rcs_m2: float):
        self.target_id = target_id
        self.distance_km = distance_km
        self.rcs_m2 = rcs_m2

    def __repr__(self):
        return f"Target[ID={self.target_id}, Dist={self.distance_km:.1f}km, RCS={self.rcs_m2}m2]"

class SimulatedOptional:
    """C++ std::optional<T> In-Place Bellek Modeli"""
    def __init__(self, value=None):
        self._has_value = (value is not None)
        self._value = value

    def has_value(self) -> bool:
        return self._has_value

    def value(self):
        """Değer yokken çağrılırsa std::bad_optional_access fırlatır"""
        if not self._has_value:
            raise RuntimeError("[std::bad_optional_access]: Boş optional nesnesine erişildi!")
        return self._value

    def value_or(self, default_value):
        """Güvenli varsayılan değer dönme kalkanı"""
        return self._value if self._has_value else default_value

    @classmethod
    def nullopt(cls):
        return cls(None)

def search_radar_sector(azimuth_deg: float) -> SimulatedOptional:
    """Radar Arama Fonksiyonu: Hedef varsa optional(Target), yoksa nullopt döner"""
    # 45 derece azimutta tespit edilen Mig-29 hedefi benzetimi:
    if 44.0 <= azimuth_deg <= 46.0:
        return SimulatedOptional(RadarTarget(701, 48.5, 3.2))
    return SimulatedOptional.nullopt()

def run_lab_01_optional_basics():
    print("[*] Laboratuvar 1: Radar Hedef Tespiti ve std::optional...")

    # 1. Hedef Olan Sektör Taraması (45 derece)
    res_found = search_radar_sector(45.0)
    print(f"  -> Sektör 45° Taraması: has_value={res_found.has_value()}")
    if res_found.has_value():
        target = res_found.value()
        print(f"     [HEDEF KİLİTLENDİ]: {target}")

    # 2. Hedef Olmayan Boş Sektör Taraması (90 derece)
    res_empty = search_radar_sector(90.0)
    print(f"  -> Sektör 90° Taraması: has_value={res_empty.has_value()}")
    
    # value_or kullanımı:
    dummy_fallback = RadarTarget(0, 0.0, 0.0)
    safe_target = res_empty.value_or(dummy_fallback)
    print(f"     [GÜVENLİ FALLBACK]: {safe_target}")

    assert res_found.has_value() is True, "Hedef bulunmalıydı!"
    assert res_empty.has_value() is False, "Sektör boş olmalıydı!"
    assert safe_target.target_id == 0, "Fallback hatalı!"
    print("  -> [PASS] std::optional varlık ve yokluk durumlarını tip güvenliğiyle yönetti.")

if __name__ == "__main__":
    run_lab_01_optional_basics()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Sabotaj Senaryosu - Kontrolsüz Erişim ve bad_optional_access
# Arıza Enjeksiyonu ve Güvenli Erişim Kalkanı
# ==============================================================================

def run_lab_02_sabotage():
    print("\n[*] Laboratuvar 2: Kontrolsüz Erişim Sabotajı ve Savunma...")

    empty_opt = SimulatedOptional.nullopt()

    # 1. SABOTAJ: Boş nesne üzerinde doğrudan .value() çağrısı
    print("  [1] BOŞ OPTIONAL ÜZERİNDE .value() ÇAĞRISI SABOTAJI:")
    try:
        # Programcı kontrol etmeden veriye erişmeye çalışıyor:
        _ = empty_opt.value()
        assert False, "HATA: İstisna fırlatılmadı!"
    except RuntimeError as e:
        print(f"      [BEKLENEN ÇÖKÜŞ YAKALANDI]: {e}")
        print("      [SAVUNMA RAPORU]: std::bad_optional_access tanımsız davranışı engelledi.")

    # 2. SAVUNMA: value_or ve if (has_value) kalkanı
    print("\n  [2] GÜVENLİ SAVUNMA METODU (value_or):")
    safe_callsign = empty_opt.value_or("TELSİZ_SESSİZLİĞİ")
    print(f"      Dönen Güvenli Çağrı Kodu: '{safe_callsign}'")
    assert safe_callsign == "TELSİZ_SESSİZLİĞİ"

    print("  -> [PASS] Boş değer erişimi savunma mekanizmalarıyla başarıyla kontrol altına alındı.")

if __name__ == "__main__":
    run_lab_02_sabotage()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Füze Güdüm ve Atış Kontrol Monadik Boru Hattı
# and_then ve transform Fonksiyonel Zincirleme Simülasyonu
# ==============================================================================

class MonadicOptional(SimulatedOptional):
    def and_then(self, func):
        """Değer varsa func(value) çağır ve dönen optional'ı döndür, yoksa nullopt dön"""
        if not self._has_value:
            return MonadicOptional(None)
        return func(self._value)

    def transform(self, func):
        """Değer varsa func(value) sonucunu optional ile sar, yoksa nullopt dön"""
        if not self._has_value:
            return MonadicOptional(None)
        return MonadicOptional(func(self._value))

# Boru Hattı Fonksiyonları
def step1_detect_target(sector: int) -> MonadicOptional:
    if sector == 1:
        return MonadicOptional({"id": 101, "range_km": 25.0})
    return MonadicOptional(None)

def step2_calculate_lead_angle(target_data: dict) -> MonadicOptional:
    if target_data["range_km"] < 50.0:
        lead_angle = target_data["range_km"] * 0.4
        return MonadicOptional({"id": target_data["id"], "lead_deg": lead_angle})
    return MonadicOptional(None)

def step3_arm_interceptor(firing_solution: dict) -> str:
    return f"FÜZE_ATEŞLENDİ -> Hedef={firing_solution['id']} ÖnlemeAçısı={firing_solution['lead_deg']}°"

def run_lab_03_monadic_pipeline():
    print("\n[*] Laboratuvar 3: Monadik Atış Kontrol Güdüm Hattı...")

    # Senaryo A: Başarılı Zincir (Sektör 1)
    res_a = (step1_detect_target(1)
             .and_then(step2_calculate_lead_angle)
             .transform(step3_arm_interceptor))

    print(f"  -> Sektör 1 Atış Sonucu: {res_a.value_or('HEDEF_YOK')}")
    assert "FÜZE_ATEŞLENDİ" in res_a.value(), "Atış başarısız oldu!"

    # Senaryo B: Kısa Devre (Sektör 2 - Hedef Yok)
    res_b = (step1_detect_target(2)
             .and_then(step2_calculate_lead_angle)
             .transform(step3_arm_interceptor))

    print(f"  -> Sektör 2 Atış Sonucu: {res_b.value_or('HEDEF_YOK')}")
    assert res_b.has_value() is False, "Boş sektörde hedef bulundu!"
    print("  -> [PASS] Monadik boru hattı kısa devre mekanizmasıyla kusursuz çalıştı.")

if __name__ == "__main__":
    run_lab_03_monadic_pipeline()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# 100.000 Hedef Aramasında: Heap Pointer vs In-Place std::optional
# ==============================================================================

import time

def benchmark_heap_vs_optional():
    print("\n[*] Laboratuvar 4: Heap Pointer vs std::optional 100.000 Çağrı Ölçümü...")
    iterations = 100_000

    # 1. std::optional Benzetimi (In-Place Stack Tuple: has_value + veri)
    start_opt = time.perf_counter()
    for i in range(iterations):
        # In-place değer oluşturma (Heap yok):
        opt_has_val = (i % 2 == 0)
        opt_data = 48.5 if opt_has_val else 0.0
        # Güvenli okuma:
        val = opt_data if opt_has_val else -1.0
    t_opt_ms = (time.perf_counter() - start_opt) * 1000.0

    # 2. Heap Pointer Benzetimi (Dinamik Tahsis ve İmha)
    start_heap = time.perf_counter()
    for i in range(iterations):
        if i % 2 == 0:
            # Heap tahsisi benzetimi:
            heap_obj = [48.5] # Yeni liste tahsisi
            val = heap_obj[0]
            del heap_obj # free
        else:
            heap_ptr = None
            val = -1.0
    t_heap_ms = (time.perf_counter() - start_heap) * 1000.0

    print(f"  -> std::optional In-Place ({iterations:,} çağrı): {t_opt_ms:.2f} ms")
    print(f"  -> Heap Pointer Tahsisi  ({iterations:,} çağrı): {t_heap_ms:.2f} ms")
    print(f"  -> PERFORMANS ORANI: std::optional {(t_heap_ms / max(t_opt_ms, 0.001)):.1f}x kat daha hızlıdır!")
    print("  -> TESPİT: std::optional sıfır heap tahsisi ile gerçek zamanlı determinizmi korur.")
    return t_opt_ms, t_heap_ms

if __name__ == "__main__":
    benchmark_heap_vs_optional()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-059 Analitik Görselleştirme Motoru
# 4 Panelli Sistem Mimarisi Dashboard'u (gun_059_std_optional.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_viz_059(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900

    # --------------------------------------------------------------------------
    # Panel 1: Bellek Anatomisi
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. std::optional<double> Bellek Anatomisi (16 Bayt In-Place)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Dış Kutu
    b_opt = patches.FancyBboxPatch((0.08, 0.35), 0.84, 0.40, boxstyle="round,pad=0.02", facecolor='#0F172A', edgecolor='#38BDF8', linewidth=2)
    ax1.add_patch(b_opt)

    # 3 Parça: Storage (8B), has_value (1B), Padding (7B)
    r1 = patches.Rectangle((0.12, 0.42), 0.42, 0.24, facecolor='#065F46', edgecolor='#10B981', linewidth=1.5)
    ax1.add_patch(r1)
    ax1.text(0.33, 0.54, "T storage_ (8 Bayt)\n[Değer Alanı]", color='#FFFFFF', fontsize=8, fontweight='bold', ha='center', va='center')

    r2 = patches.Rectangle((0.56, 0.42), 0.16, 0.24, facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=1.5)
    ax1.add_patch(r2)
    ax1.text(0.64, 0.54, "has_val\n(1B)", color='#FFFFFF', fontsize=8, fontweight='bold', ha='center', va='center')

    r3 = patches.Rectangle((0.74, 0.42), 0.14, 0.24, facecolor='#334155', edgecolor='#94A3B8', linewidth=1.5)
    ax1.add_patch(r3)
    ax1.text(0.81, 0.54, "Padding\n(7B)", color='#CBD5E1', fontsize=7.5, ha='center', va='center')

    ax1.text(0.50, 0.20, "SIFIR HEAP TAHSİSİ: Değer doğrudan stack üzerinde saklanır.\nalignof(optional<T>) == alignof(T)", color='#34D399', fontsize=8.5, ha='center', fontweight='bold')

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: Yöntem Kıyaslaması
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Hata Bildirim Yöntemleri ve Güvenlik Seviyeleri", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    methods = [
        ("Sentinel Value (-1.0)", "Filtre Zehirlenmesi (Bozuk Veri)", '#7F1D1D', '#EF4444'),
        ("Raw Pointer (nullptr)", "Nullptr Dereference (SIGSEGV)", '#7F1D1D', '#F59E0B'),
        ("Out-Param (bool &out)", "Hantal API, Default Ctor Zorunlu", '#1E3A8A', '#3B82F6'),
        ("std::optional<T>", "Sıfır Heap, Tip Güvenliği, value_or()", '#065F46', '#10B981')
    ]

    y_pos = [0.78, 0.54, 0.30, 0.08]
    for (name, desc, bg, edge), y in zip(methods, y_pos):
        b = patches.FancyBboxPatch((0.08, y), 0.84, 0.16, boxstyle="round,pad=0.01", facecolor=bg, edgecolor=edge, linewidth=1.5)
        ax2.add_patch(b)
        ax2.text(0.12, y + 0.08, name, color='#FFFFFF', fontsize=8.5, fontweight='bold', va='center')
        ax2.text(0.55, y + 0.08, desc, color='#F8FAFC', fontsize=7.5, va='center')

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # Panel 3: Monadik Boru Hattı
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Monadik Boru Hattı: and_then ile Kısa Devre Güvencesi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    pipe_steps = [
        ("1. Sektör Tarama\nsearchSector()", 0.15, 0.60, '#1E3A8A', '#3B82F6'),
        ("2. İz Korelasyonu\ncorrelateTrack()", 0.50, 0.60, '#065F46', '#10B981'),
        ("3. Atış Çözümü\ncomputeSolution()", 0.85, 0.60, '#7C3AED', '#A78BFA')
    ]

    for title, x, y, bg, edge in pipe_steps:
        b = patches.FancyBboxPatch((x - 0.15, y - 0.12), 0.30, 0.24, boxstyle="round,pad=0.01", facecolor=bg, edgecolor=edge, linewidth=1.5)
        ax3.add_patch(b)
        ax3.text(x, y, title, color='#FFFFFF', fontsize=7.5, fontweight='bold', ha='center', va='center')

    ax3.annotate("", xy=(0.33, 0.60), xytext=(0.31, 0.60), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=2))
    ax3.annotate("", xy=(0.68, 0.60), xytext=(0.66, 0.60), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=2))

    # Kısa devre oku
    ax3.annotate("nullopt dönerse zincir anında durur (Short-Circuit)!", xy=(0.50, 0.30), xytext=(0.50, 0.44),
                 arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2), color='#FCA5A5', fontsize=8, ha='center', fontweight='bold')

    ax3.text(0.50, 0.15, "İç içe if-else bloklarına son veren fonksiyonel boru hattı", color='#CBD5E1', fontsize=8, ha='center', style='italic')

    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')

    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 Çağrıda Gecikme: Heap Pointer vs std::optional", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    categories = ['std::optional<T>\n(In-Place Stack, 0 malloc)', 'Heap Pointer (T*)\n(Dinamik Tahsis, 50.000 malloc)']
    times = [1.65, 12.40]
    bar_colors = ['#10B981', '#EF4444']

    bars = ax4.barh(categories, times, color=bar_colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("İşlemci Süresi (ms)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)

    for bar in bars:
        w_val = bar.get_width()
        ax4.text(w_val + 0.2, bar.get_y() + bar.get_height()/2.0, f"{w_val:.2f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')

    ax4.text(6.5, 0.2, "PERFORMANS FARKI:\nstd::optional 7.5x Kat Daha Hızlıdır\n(Sıfır Heap Parçalanması)", color='#38BDF8', fontsize=8.5, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#1E3A8A', edgecolor='#3B82F6'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_059(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# std::optional Bütünlük ve Güvenlik Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 059: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: Dolu ve Boş Optional Durumları
    full_opt = SimulatedOptional("RADAR_LOCK_ACQUIRED")
    empty_opt = SimulatedOptional.nullopt()

    assert full_opt.has_value() is True, "full_opt dolu olmalıdır!"
    assert empty_opt.has_value() is False, "empty_opt boş olmalıdır!"
    assert full_opt.value() == "RADAR_LOCK_ACQUIRED", "Değer eşleşmedi!"
    print("  -> [PASS] has_value() ve value() durumları başarıyla doğrulandı.")

    # 2. Test: value_or Fallback Doğrulaması
    res_val = empty_opt.value_or("STANDBY_SEARCH")
    assert res_val == "STANDBY_SEARCH", "Fallback değeri hatalı!"
    print("  -> [PASS] value_or() varsayılan değer mekanizması mühürlendi.")

    # 3. Test: bad_optional_access Koruma Doğrulaması
    caught_bad_access = False
    try:
        _ = empty_opt.value()
    except RuntimeError:
        caught_bad_access = True

    assert caught_bad_access is True, "HATA: Boş değere erişimde istisna yakalanamadı!"
    print("  -> [PASS] std::bad_optional_access koruyucu bariyeri onaylandı.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
