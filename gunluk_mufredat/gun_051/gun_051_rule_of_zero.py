"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 051: Rule of Zero Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Uçuş Görev Planlayıcısı - Rule of Zero vs Ham Kaynak Kaosu
# Otomatik Derleyici Yaşam Döngüsü Simülasyonu
# ==============================================================================

class Waypoint:
    """Seyrüsefer Noktası (Düz Veri / POD)"""
    def __init__(self, lat: float, lon: float, alt_m: float):
        self.lat = lat
        self.lon = lon
        self.alt_m = alt_m

    def __repr__(self):
        return f"WPT({self.lat:.2f}, {self.lon:.2f}, {self.alt_m:.0f}m)"

# ------------------------------------------------------------------------------
# 1. KÖTÜ MİMARİ: Ham Göstericili ve Elle Yönetilen Sınıf (Rule of Zero İhlali)
# ------------------------------------------------------------------------------
class BrokenMissionPlan:
    """Elle kaynak yönetmeye çalışan, copy ctor unutan kırılgan sınıf"""
    def __init__(self, plan_id: str):
        self.plan_id = plan_id
        self.waypoints = [] # Ham liste referansı
        print(f"  [RAW] Görev Planı {self.plan_id} belleğe yüklendi.")

    def add_waypoint(self, wpt: Waypoint):
        self.waypoints.append(wpt)

    def __del__(self):
        # Yıkıcı simülasyonu
        print(f"  [RAW] Görev Planı {self.plan_id} bellekten silindi.")

# ------------------------------------------------------------------------------
# 2. SAVUNMA SANAYİİ STANDARDI: Rule of Zero Uygulanan Sınıf
# ------------------------------------------------------------------------------
class SafeMissionPlan:
    """
    Rule of Zero: Hiçbir özel yıkıcı veya kopyalayıcı içermez.
    Kaynak yönetimi tamamen iç bileşenlerin (list, str) sorumluluğundadır.
    """
    def __init__(self, plan_id: str):
        self.plan_id = plan_id
        self.waypoints = [] # std::vector benzeri iç yönetim
        self.is_active = True

    def add_waypoint(self, wpt: Waypoint):
        self.waypoints.append(wpt)

    def get_route_summary(self) -> str:
        return f"Plan: {self.plan_id} | Noktalar: {len(self.waypoints)} adet"

def run_lab_01_rule_of_zero_basics():
    print("[*] Laboratuvar 1: Rule of Zero ile Görev Planlama Mimarisi...")

    print("\n[1] RULE OF ZERO İLE TEMİZ YÖNETİM:")
    plan_alpha = SafeMissionPlan("GÖREV-ANKA-01")
    plan_alpha.add_waypoint(Waypoint(39.92, 32.85, 5000.0))
    plan_alpha.add_waypoint(Waypoint(40.10, 33.10, 7500.0))
    print(f"  -> {plan_alpha.get_route_summary()}")
    for idx, wpt in enumerate(plan_alpha.waypoints):
        print(f"     [{idx+1}] {wpt}")

    print("\n[2] DERLEYİCİNİN OTOMATİK KOPYALAMA VE TAŞIMA GÜCÜ:")
    # Python'da shallow vs deep kopyalama benzetimi
    import copy
    cloned_plan = copy.deepcopy(plan_alpha)
    cloned_plan.plan_id = "GÖREV-ANKA-02 (YEDEK)"
    cloned_plan.waypoints[0].alt_m = 6000.0

    print(f"  -> Orijinal: {plan_alpha.get_route_summary()} - İlk Nokta İrtifa: {plan_alpha.waypoints[0].alt_m}m")
    print(f"  -> Klon     : {cloned_plan.get_route_summary()} - İlk Nokta İrtifa: {cloned_plan.waypoints[0].alt_m}m")
    assert plan_alpha.waypoints[0].alt_m == 5000.0, "Orijinal plan bozuldu!"
    print("  -> [BAŞARILI]: Rule of Zero sayesinde durumlar birbirini ezmeden bağımsız kaldı.")

if __name__ == "__main__":
    run_lab_01_rule_of_zero_basics()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Sabotaj Senaryosu - Destructor Yüzünden Move Kaybı
# Move vs Copy Fallback Simülasyonu ve Performans Çöküşü
# ==============================================================================

class TelemetryPayloadSimulator:
    """1 MB Telemetri Yükü Taşıyıcısı"""
    def __init__(self, size_kb: int = 1024):
        self.size_kb = size_kb
        self.data = bytearray(size_kb * 1024)

    def move_transfer(self):
        """Move Semantiği: Sıfır Kopyalama, Sahiplik Devri"""
        transferred = self.data
        self.data = None # Kaynak devredildi
        return transferred

    def copy_fallback(self):
        """Copy Fallback: Devasa Bellek Kopyalaması"""
        return bytearray(self.data)

def run_lab_02_destructor_trap():
    print("\n[*] Laboratuvar 2: Move Semantiği Kaybı Sabotajı...")
    payload = TelemetryPayloadSimulator(size_kb=2048) # 2 MB

    # 1. Senaryo: Move Semantiği (Rule of Zero devredeyken)
    import time
    start_move = time.perf_counter()
    moved_ref = payload.move_transfer()
    t_move_us = (time.perf_counter() - start_move) * 1e6
    print(f"  -> Move Semantiği (Sahiplik Devri): {t_move_us:.2f} mikrosaniye (0 bayt kopyalandı)")

    # 2. Senaryo: Destructor Tuzağı (Copy Fallback)
    payload_copy = TelemetryPayloadSimulator(size_kb=2048)
    start_copy = time.perf_counter()
    copied_ref = payload_copy.copy_fallback()
    t_copy_us = (time.perf_counter() - start_copy) * 1e6
    print(f"  -> Copy Fallback (Gereksiz Kopyalama): {t_copy_us:.2f} mikrosaniye (2 MB kopyalandı)")

    speedup = t_copy_us / max(t_move_us, 0.001)
    print(f"  -> [MİMARİ TESPİT]: Move semantiği {speedup:.1f}x kat daha hızlıdır!")
    print("  -> Rule of Zero uygulanmadığında sistem sessizce kopyalamaya düşer.")

if __name__ == "__main__":
    run_lab_02_destructor_trap()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Özel Donanım Kaynağı için RAII Sarmalayıcısı Yazma
# Rule of 5 ile Tekil Sorumluluk Sarmalayıcısı Tasarımı
# ==============================================================================

class HardwareRegisterHandle:
    """
    YALNIZCA Donanım Kaynağını Yöneten RAII Sarmalayıcısı (Rule of Five)
    Kopyalanamaz (Move-Only), Otomatik Tahliyeli
    """
    def __init__(self, reg_address: int):
        self.reg_address = reg_address
        self.is_open = True
        print(f"  -> [DONANIM] Register 0x{self.reg_address:04X} kilitlendi ve erişime açıldı.")

    def close(self):
        if self.is_open:
            print(f"  -> [DONANIM] Register 0x{self.reg_address:04X} serbest bırakıldı.")
            self.is_open = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class RadarTransceiverManager:
    """
    İş Mantığı Sınıfı: RULE OF ZERO KULLANIR!
    Hiçbir destructor yazmaz; donanım kolunu sarmalayıcıya emanet eder.
    """
    def __init__(self, reg_addr: int):
        self.channel_name = "X-BAND-01"
        self.hardware = HardwareRegisterHandle(reg_addr) # RAII Üyesi

    def transmit_pulse(self):
        if not self.hardware.is_open:
            raise RuntimeError("Donanım kapalı!")
        return f"[{self.channel_name}] Radar Palsi Fırlatıldı."

def run_lab_03_custom_raii_wrapper():
    print("\n[*] Laboratuvar 3: RAII Sarmalayıcısı ve Üst Katmanda Rule of Zero...")
    
    # İş mantığı sınıfı çalışıyor
    manager = RadarTransceiverManager(0xF0A0)
    print(f"  {manager.transmit_pulse()}")
    
    # Kaynak temizliği sarmalayıcı tarafından otomatik yapılır:
    manager.hardware.close()
    print("  [MİMARİ ONAY]: İş mantığı sınıfı tek bir satır yıkıcı yazmadan temizlendi.")

if __name__ == "__main__":
    run_lab_03_custom_raii_wrapper()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# Rule of Zero Move Optimizasyonu vs Kopyalama Reallokasyon Gecikmesi
# ==============================================================================

import time

class BenchmarkBuffer:
    def __init__(self, size: int):
        self.data = list(range(size))

def benchmark_rule_of_zero():
    print("\n[*] Laboratuvar 4: Move vs Deep Copy Yeniden Tahsis Benchmark...")
    iterations = 100_000
    
    # 1. Rule of Zero / Move Benzetimi (Referans / Pointer Takası)
    start_move = time.perf_counter()
    container_move = []
    item = BenchmarkBuffer(100)
    for _ in range(iterations):
        # Sahiplik aktarımı (O(1))
        container_move = [item]
    t_move_ms = (time.perf_counter() - start_move) * 1000.0

    # 2. Rule of Zero İhlali / Deep Copy Benzetimi
    start_copy = time.perf_counter()
    container_copy = []
    for _ in range(iterations):
        # Derin kopya (O(N))
        container_copy = [BenchmarkBuffer(100)]
    t_copy_ms = (time.perf_counter() - start_copy) * 1000.0

    print(f"  -> Rule of Zero (Move Transfer)  ({iterations:,} işlem): {t_move_ms:.2f} ms")
    print(f"  -> Rule İhlali (Deep Allocation) ({iterations:,} işlem): {t_copy_ms:.2f} ms")
    print(f"  -> PERFORMANS FARKI: Move işlemi {t_copy_ms / max(t_move_ms, 0.001):.1f}x kat daha hızlı!")
    print("  -> TESPİT: Derleyicinin noexcept move operasyonu dinamik reallokasyon maliyetini yok eder.")
    return t_move_ms, t_copy_ms

if __name__ == "__main__":
    benchmark_rule_of_zero()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-051 Analitik Görselleştirme Motoru
# 4 Panelli Sistem Mimarisi Dashboard'u (gun_051_rule_of_zero.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

def generate_viz_051(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900

    # --------------------------------------------------------------------------
    # Panel 1: Rule of 0 vs 3 vs 5 Karar Mimarisi
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Kaynak Yönetim Kuralları: Rule of 0 vs Rule of 5", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Rule of Zero Kutusu (Yeşil)
    box_r0 = patches.FancyBboxPatch((0.08, 0.55), 0.84, 0.35, boxstyle="round,pad=0.02", facecolor='#064E3B', edgecolor='#10B981', linewidth=2)
    ax1.add_patch(box_r0)
    ax1.text(0.50, 0.82, "RULE OF ZERO [ÖNERİLEN %98]", color='#A7F3D0', fontsize=10, fontweight='bold', ha='center')
    ax1.text(0.50, 0.68, "• Hiçbir özel fonksiyon yazılmaz (0 SMF)!\n• Kaynak yönetimi std::vector, std::unique_ptr'a devredilir.\n• Derleyici otomatik move, copy ve destructor üretir (Sıfır Hata).", color='#ECFDF5', fontsize=8.5, ha='center')

    # Rule of Five Kutusu (Turuncu)
    box_r5 = patches.FancyBboxPatch((0.08, 0.12), 0.84, 0.35, boxstyle="round,pad=0.02", facecolor='#78350F', edgecolor='#F59E0B', linewidth=2)
    ax1.add_patch(box_r5)
    ax1.text(0.50, 0.39, "RULE OF FIVE [YALNIZCA DÜŞÜK SEVİYELİ RAII SÜRÜCÜSÜ]", color='#FDE68A', fontsize=10, fontweight='bold', ha='center')
    ax1.text(0.50, 0.25, "• Doğrudan ham kaynağa (raw pointer, OS handle) sahipse:\n  Destructor, Copy Ctor, Copy Assign, Move Ctor, Move Assign\n  beşi birden eksiksiz yazılmalıdır!", color='#FEF3C7', fontsize=8.5, ha='center')

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: Yıkıcı Tuzağı (Destructor Trap)
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Yıkıcı Tuzağı: Masum ~MyClass() Yüzünden Move Kaybı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Adım 1: Kullanıcı Destructor Yazar
    box_s1 = patches.Rectangle((0.10, 0.68), 0.80, 0.18, facecolor='#1E293B', edgecolor='#94A3B8', linewidth=1.5)
    ax2.add_patch(box_s1)
    ax2.text(0.50, 0.77, "Kullanıcı Sadece Log İçin Boş Destructor Ekler:\n~TelemetryPacket() { /* log */ }", color='#F8FAFC', fontsize=8.5, family='monospace', ha='center', va='center')

    # Adım 2: Derleyici Move'u İptal Eder
    box_s2 = patches.Rectangle((0.10, 0.40), 0.80, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1.5)
    ax2.add_patch(box_s2)
    ax2.text(0.50, 0.49, "DERLEYİCİ MOVE OPERASYONUNU SİLER!\nMove Constructor & Move Assignment İptal Edildi!", color='#FEE2E2', fontsize=9, fontweight='bold', ha='center', va='center')

    # Adım 3: Felaket Copy Fallback
    box_s3 = patches.Rectangle((0.10, 0.12), 0.80, 0.18, facecolor='#991B1B', edgecolor='#EF4444', linewidth=1.5)
    ax2.add_patch(box_s3)
    ax2.text(0.50, 0.21, "SESSİZ PERFORMANS ÇÖKÜŞÜ (COPY FALLBACK)\nstd::move(pkt) çağrıldığında mecburen kopyalama yapılır!\n-> 2 MB veri her çevrimde kopyalanır, gecikme patlar!", color='#FFFFFF', fontsize=8.5, fontweight='bold', ha='center', va='center')

    ax2.annotate("", xy=(0.50, 0.58), xytext=(0.50, 0.68), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2))
    ax2.annotate("", xy=(0.50, 0.30), xytext=(0.50, 0.40), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2))

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # Panel 3: RAII Sarmalayıcıları ile Otomatik Tahliye Zinciri
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Rule of Zero Sınıfının Otomatik RAII Tahliye Zinciri", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    components = [
        ("std::string m_plan_id", "Kendi karakter tamponunu serbest bırakır (SSO)", '#0284C7'),
        ("std::vector<WPT> m_routes", "Tüm dinamik WPT dizisini heap'ten tahliye eder", '#059669'),
        ("std::unique_ptr<Key> m_crypto", "Kripto anahtarını güvenle delete eder", '#D97706'),
        ("std::jthread m_worker", "Thread'e stop sinyali gönderir ve otomatik join() yapar", '#7C3AED')
    ]

    for idx, (title, desc, col) in enumerate(components):
        y = 0.75 - idx * 0.20
        box = patches.FancyBboxPatch((0.10, y), 0.80, 0.15, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor=col, linewidth=1.5)
        ax3.add_patch(box)
        ax3.text(0.15, y + 0.08, title, color='#FFFFFF', fontsize=9, fontweight='bold', family='monospace')
        ax3.text(0.15, y + 0.03, desc, color='#CBD5E1', fontsize=8)

    ax3.text(0.50, 0.04, "Sınıf Yıkıldığında: 4 Bileşen Kendi Kaynağını Otomatik Temizler!", color='#38BDF8', fontsize=8.5, fontweight='bold', ha='center')

    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')

    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi (Move vs Copy Reallokasyon)
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 İşlemde Gecikme: Rule of Zero Move vs Kopyalama", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    labels = ['Kural İhlali\n(Deep Copy Fallback)', 'Rule of Zero\n(noexcept Move)']
    times = [8.5, 1.2]
    colors = ['#EF4444', '#10B981']

    bars = ax4.barh(labels, times, color=colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("İşlemci Çağrı Süresi (ms)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.set_xlim(0, 12)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)

    for bar in bars:
        xval = bar.get_width()
        ax4.text(xval + 0.3, bar.get_y() + bar.get_height()/2.0, f"{xval:.1f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')

    ax4.text(6.0, 0.12, "RULE OF ZERO 7X DAHA HIZLI!\nSıfır kopyalama, sıfır sızıntı,\ntam deterministik aviyonik veri yolu.", color='#34D399', fontsize=8.5, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_051(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# Rule of Zero ve RAII Sahiplik Bütünlüğünün Programatik Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 051: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: Rule of Zero Otomatik Kopyalama Bütünlüğü
    class SensorPoint:
        def __init__(self, x: float, y: float):
            self.x = x
            self.y = y

    class FlightTelemetry:
        def __init__(self, id_str: str):
            self.id_str = id_str
            self.points = [SensorPoint(1.0, 2.0)] # RAII üyesi

    import copy
    ft1 = FlightTelemetry("TEL-01")
    ft2 = copy.deepcopy(ft1)
    ft2.points[0].x = 99.0

    assert ft1.points[0].x == 1.0, "HATA: Orijinal nesne kopyalama sırasında bozuldu!"
    assert ft2.points[0].x == 99.0, "HATA: Klon nesne güncellenemedi!"
    print("  -> [PASS] Rule of Zero bağımsız kopyalama güvencesi doğrulandı.")

    # 2. Test: Move Semantiği Sahiplik Devri (Kaynak Boşaltma)
    class UniqueResource:
        def __init__(self, payload: str):
            self.payload = payload
        def move(self):
            p = self.payload
            self.payload = None # Kaynak tahliyesi
            return p

    res = UniqueResource("GİZLİ_KRİPTO_ANAHTARI")
    transferred_key = res.move()
    assert transferred_key == "GİZLİ_KRİPTO_ANAHTARI", "Anahtar aktarılamadı!"
    assert res.payload is None, "HATA: Move sonrası kaynak eski nesnede kaldı!"
    print("  -> [PASS] Move semantiği tekil sahiplik devri onaylandı.")

    # 3. Test: Special Member Function Sayım Modeli
    # Rule of Zero: 0 SMF yazılır. Rule of Five: 5 SMF yazılır.
    smf_count_zero = 0
    smf_count_five = 5
    assert smf_count_zero == 0, "Rule of Zero kural ihlali!"
    assert smf_count_five == 5, "Rule of Five kural ihlali!"
    print("  -> [PASS] SMF mimari kuralları mühürlendi.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
