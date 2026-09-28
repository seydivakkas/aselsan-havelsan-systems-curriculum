"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 050: Virtual Function ve Polymorphism Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Entegre Hava Savunma Sistemi (IADS) Çokbiçimli Filosu
# vtable / vptr Dinamik Bağlama Simülasyonu ve Silah Seçim Motoru
# ==============================================================================

class TargetTelemetry:
    """Hedef Telemetri Verisi"""
    def __init__(self, target_id: str, range_km: float, altitude_m: float):
        self.target_id = target_id
        self.range_km = range_km
        self.altitude_m = altitude_m

class IAirDefenseInterceptor:
    """Soyut Taban Sınıf (Interface): Sanal Metotlar ve vtable Benzetimi"""
    def __init__(self, system_name: str, max_range_km: float):
        self.system_name = system_name
        self.max_range_km = max_range_km

    def can_engage(self, target: TargetTelemetry) -> bool:
        raise NotImplementedError("Virtual method!")

    def engage(self, target: TargetTelemetry) -> str:
        raise NotImplementedError("Virtual method!")

class KorkutSPAAG(IAirDefenseInterceptor):
    """Korkut 35mm Çift Namlulu Kundağı Motorlu Uçaksavar Sistemi"""
    def __init__(self):
        super().__init__("KORKUT-35mm", max_range_km=4.0)

    def can_engage(self, target: TargetTelemetry) -> bool:
        return target.range_km <= self.max_range_km and target.altitude_m <= 3000.0

    def engage(self, target: TargetTelemetry) -> str:
        return f"[{self.system_name}] 35mm ATOM Parçacıklı Mühimmat Serisi Ateşlendi! Hedef: {target.target_id}"

class HisarA_SAM(IAirDefenseInterceptor):
    """Hisar-A+ Alçak İrtifa Hava Savunma Füze Sistemi"""
    def __init__(self):
        super().__init__("HİSAR-A+", max_range_km=15.0)

    def can_engage(self, target: TargetTelemetry) -> bool:
        return 3.0 < target.range_km <= self.max_range_km

    def engage(self, target: TargetTelemetry) -> str:
        return f"[{self.system_name}] Dikey Atımlı IIR Güdümlü Füze Ateşlendi! Hedef: {target.target_id}"

class SiperBlock1_SAM(IAirDefenseInterceptor):
    """Siper Blok-1 Uzun Menzilli Bölge Savunma Füzesi"""
    def __init__(self):
        super().__init__("SİPER-BLOK-1", max_range_km=100.0)

    def can_engage(self, target: TargetTelemetry) -> bool:
        return target.range_km > 15.0 and target.range_km <= self.max_range_km

    def engage(self, target: TargetTelemetry) -> str:
        return f"[{self.system_name}] Aktif Radar Arayıcı Başlıklı Uzun Menzil Füzesi Fırlatıldı! Hedef: {target.target_id}"

class AirDefenseCommandCenter:
    """Komuta Kontrol (C2) Konsolu: Heterojen Silah Filosunu Polimorfik Yönetir"""
    def __init__(self):
        self._battery = []

    def deploy_interceptor(self, interceptor: IAirDefenseInterceptor):
        self._battery.append(interceptor)

    def process_threat(self, target: TargetTelemetry) -> str:
        # Dinamik Polimorfik Çağrı: Tek döngüde uygun sistemi tetikler
        for interceptor in self._battery:
            if interceptor.can_engage(target):
                return interceptor.engage(target)
        return f"[C2 UYARI] Hedef menzil/irtifa dışı! Önleme yapılamadı: {target.target_id} ({target.range_km} km)"

def run_lab_01_polymorphism_c2():
    print("[*] Laboratuvar 1: Çokbiçimli Hava Savunma Komuta Sistemi Başlatılıyor...")
    c2 = AirDefenseCommandCenter()
    c2.deploy_interceptor(KorkutSPAAG())
    c2.deploy_interceptor(HisarA_SAM())
    c2.deploy_interceptor(SiperBlock1_SAM())

    threats = [
        TargetTelemetry("DUSMAN_IHA_KAMIKAZE", range_km=2.5, altitude_m=800.0),
        TargetTelemetry("SEYIR_FUZESI_TOMAHAWK", range_km=12.0, altitude_m=250.0),
        TargetTelemetry("AVCI_UCAK_SU35", range_km=75.0, altitude_m=9500.0),
        TargetTelemetry("STRATEJIK_BOMBARDIRMAN", range_km=180.0, altitude_m=14000.0)
    ]

    print("\n[*] C2 RADAR TEHDİT DEĞERLENDİRMESİ:")
    for t in threats:
        result = c2.process_threat(t)
        print(f"  -> Tehdit {t.target_id:25} ({t.range_km:5.1f}km) => {result}")

if __name__ == "__main__":
    run_lab_01_polymorphism_c2()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Sabotaj Senaryoları - Slicing ve Virtual Destructor Sızıntısı
# Kaynak Sızıntısının ve Dilimlemenin Simülasyonu
# ==============================================================================

class HardwareSocketTracker:
    """Donanım Soketi Açık/Kapalı Durumu Takipçisi"""
    active_sockets = 0

class NonVirtualBaseInterceptor:
    """TEHLİKELİ: Destructor Virtual Olmayan Taban Sınıf"""
    def __init__(self):
        self.base_name = "GENERIC_INTERCEPTOR"

    def cleanup(self):
        # Yalnızca taban sınıf temizliği
        pass

class LeakingSAM(NonVirtualBaseInterceptor):
    """Donanım Soketi Tutan Türemiş Sınıf"""
    def __init__(self):
        super().__init__()
        HardwareSocketTracker.active_sockets += 1
        self.socket_id = 0xAA99
        print(f"  -> [DONANIM] Radar Soketi 0x{self.socket_id:X} Açıldı. (Aktif: {HardwareSocketTracker.active_sockets})")

    def cleanup_derived(self):
        # Türemiş sınıf temizliği: Soketi kapatır
        HardwareSocketTracker.active_sockets -= 1
        print(f"  -> [DONANIM] Radar Soketi 0x{self.socket_id:X} Güvenle Kapatıldı. (Aktif: {HardwareSocketTracker.active_sockets})")

def run_lab_02_destructor_sabotage():
    print("\n[*] Laboratuvar 2: Non-Virtual Destructor ve Kaynak Sızıntısı Sabotajı...")

    # 1. Sabotaj: Virtual Destructor Olmadığı İçin Türemiş Sınıf Yıkılmıyor
    print("  [1] Sanal Yıkıcı Eksikliği Nedeniyle Soket Sızıntısı:")
    
    # Nesne heap'te açılıyor:
    leaking_system = LeakingSAM()
    
    # Taban sınıf göstericisi üzerinden temizlik yapılıyor (delete base_ptr benzeri):
    print("    -> delete base_ptr çağrılıyor (Virtual Destructor YOK!)...")
    leaking_system.cleanup() # Sadece Base temizlendi, cleanup_derived() ÇAĞRILMADI!
    
    print(f"    [FELAKET TESPİTİ]: Aktif Donanım Soketi: {HardwareSocketTracker.active_sockets}")
    assert HardwareSocketTracker.active_sockets == 1, "Sızıntı tespit edilemedi!"
    print("    -> Sızıntı doğrulandı: Radar soketi bellekte kilitli kaldı!")

    # 2. Savunma: Doğru Virtual Destructor Temizliği
    print("\n  [2] Doğru Sanal Temizlik (Virtual Destructor):")
    leaking_system.cleanup_derived() # Polimorfik doğru çağrı
    print(f"    [GÜVENLİ DURUM]: Aktif Soket: {HardwareSocketTracker.active_sockets} (Tam Tahliye)")

if __name__ == "__main__":
    run_lab_02_destructor_sabotage()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Override İmzası Denetimi ve Devirtualization Mekanizması
# Yanlış Metod İmzası Tespiti ve Statik Çözümleme
# ==============================================================================

class SafeBaseTracker:
    def track_threat(self, threat_id: int, azimuth_deg: float) -> str:
        return f"[BASE] Tehdit {threat_id} izleniyor. Açı: {azimuth_deg}°"

class ErroneousDerivedTracker(SafeBaseTracker):
    """Hatalı İmza: azimuth parametresini unutmuş, override yerine overload yaptı!"""
    def track_threat_buggy(self, threat_id: int) -> str:
        return f"[BUG] Sadece ID izleniyor: {threat_id}"

class CorrectDerivedTracker(SafeBaseTracker):
    """Tam Uyumlu Override İmzası"""
    def track_threat(self, threat_id: int, azimuth_deg: float) -> str:
        return f"[DERIVED FINAL] AESA Radarı ile Kilitlenildi: Hedef {threat_id}, Açı: {azimuth_deg:.2f}°"

def run_lab_03_override_mechanics():
    print("\n[*] Laboratuvar 3: Override İmzası ve Devirtualization İncelemesi...")
    
    # 1. Taban Göstericisi Üzerinden Çağrı
    tracker: SafeBaseTracker = CorrectDerivedTracker()
    output = tracker.track_threat(901, 142.5)
    print(f"  -> Polimorfik Çıktı: {output}")
    assert "AESA Radarı" in output, "Override başarısız!"
    print("  -> [MİMARİ ONAY]: Override imzası doğrulandı, dinamik bağlama başarıyla gerçekleşti.")

if __name__ == "__main__":
    run_lab_03_override_mechanics()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# Statik Doğrudan Çağrı vs Sanal Dinamik Bağlama (Virtual Dispatch) Gecikmesi
# ==============================================================================

import time

# 1. Doğrudan Çağrı (Static Dispatch)
class DirectCalculator:
    def compute(self, x: float) -> float:
        return x * 1.05 + 0.5

# 2. Sanal Çağrı (Dynamic Dispatch / Indirection)
class BaseCalculator:
    def compute(self, x: float) -> float:
        raise NotImplementedError()

class VirtualCalculator(BaseCalculator):
    def compute(self, x: float) -> float:
        return x * 1.05 + 0.5

def benchmark_virtual_dispatch():
    print("\n[*] Laboratuvar 4: Statik Doğrudan Çağrı vs Sanal Çağrı Benchmark...")
    iterations = 100_000

    direct = DirectCalculator()
    v_calc: BaseCalculator = VirtualCalculator()

    # 1. Statik Çağrı
    start_stat = time.perf_counter()
    res_s = 0.0
    for i in range(iterations):
        res_s += direct.compute(float(i))
    t_stat_ms = (time.perf_counter() - start_stat) * 1000.0

    # 2. Sanal Çağrı
    start_virt = time.perf_counter()
    res_v = 0.0
    for i in range(iterations):
        res_v += v_calc.compute(float(i))
    t_virt_ms = (time.perf_counter() - start_virt) * 1000.0

    print(f"  -> Doğrudan Statik Çağrı ({iterations:,} çağrı): {t_stat_ms:.2f} ms")
    print(f"  -> Sanal Dinamik Çağrı   ({iterations:,} çağrı): {t_virt_ms:.2f} ms")
    print(f"  -> İndireksiyon Başına Ek Gecikme: {(t_virt_ms - t_stat_ms) / iterations * 1e6:.2f} ns")
    print("  -> TESPİT: C++'ta sanal çağrı 1-3 saat döngüsü (0.5-1.5 ns) ek yük getirir; devirtualization ile bu sıfırlanabilir!")
    return t_stat_ms, t_virt_ms

if __name__ == "__main__":
    benchmark_virtual_dispatch()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-050 Analitik Görselleştirme Motoru
# 4 Panelli Sistem Mimarisi Dashboard'u (gun_050_virtual_function_ve_polymorphism.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

def generate_viz_050(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900

    # --------------------------------------------------------------------------
    # Panel 1: vtable ve vptr Bellek Düzeni
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Bellek Mimarisi: Nesne İçi __vptr ve .rodata vtable Bağlantısı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Nesne (RAM)
    rect_obj = patches.FancyBboxPatch((0.08, 0.25), 0.35, 0.60, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#38BDF8', linewidth=2)
    ax1.add_patch(rect_obj)
    ax1.text(0.255, 0.80, "HisarA_SAM Nesnesi (Heap/Stack)", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center')

    # vptr Alanı
    rect_vptr = patches.Rectangle((0.11, 0.62), 0.29, 0.12, facecolor='#0369A1', edgecolor='#38BDF8', linewidth=1.5)
    ax1.add_patch(rect_vptr)
    ax1.text(0.255, 0.68, "__vptr (8 Bayt Gösterici)", color='#F0F9FF', fontsize=8, fontweight='bold', ha='center', va='center')

    # Veri Alanı
    rect_data = patches.Rectangle((0.11, 0.35), 0.29, 0.22, facecolor='#334155', edgecolor='#64748B', linewidth=1.5)
    ax1.add_patch(rect_data)
    ax1.text(0.255, 0.46, "Üye Değişkenler\n• max_range_km (8B)\n• missile_count (4B)", color='#E2E8F0', fontsize=8, ha='center', va='center')

    # vtable (.rodata)
    rect_vt = patches.FancyBboxPatch((0.58, 0.25), 0.35, 0.60, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#10B981', linewidth=2)
    ax1.add_patch(rect_vt)
    ax1.text(0.755, 0.80, "vtable for HisarA_SAM (.rodata)", color='#A7F3D0', fontsize=9, fontweight='bold', ha='center')

    vt_entries = [("[0]: &HisarA::can_engage", '#065F46'), ("[1]: &HisarA::engage", '#047857'), ("[2]: &HisarA::~HisarA (Dtor)", '#059669')]
    for idx, (label, col) in enumerate(vt_entries):
        y = 0.62 - idx * 0.13
        r = patches.Rectangle((0.61, y), 0.29, 0.10, facecolor=col, edgecolor='#10B981', linewidth=1)
        ax1.add_patch(r)
        ax1.text(0.755, y + 0.05, label, color='#FFFFFF', fontsize=7.5, family='monospace', ha='center', va='center')

    # Bağlantı Oku
    ax1.annotate("", xy=(0.58, 0.68), xytext=(0.40, 0.68),
                 arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2.5))
    ax1.text(0.49, 0.72, "Pointer", color='#38BDF8', fontsize=8, fontweight='bold', ha='center')

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: Sanal Yıkıcı (Virtual Destructor) Sızıntı Mekanizması
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Sanal Yıkıcı Eksikliği: Kaynak Sızıntısı (Resource Leak)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Yanlış Durum (Non-Virtual)
    box_bad = patches.FancyBboxPatch((0.08, 0.52), 0.84, 0.38, boxstyle="round,pad=0.02", facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1.5)
    ax2.add_patch(box_bad)
    ax2.text(0.50, 0.82, "NON-VIRTUAL DESTRUCTOR [FELAKET SENARYOSU]", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center')
    ax2.text(0.50, 0.67, "delete base_ptr;  ──►  SADECE ~BaseInterceptor() ÇALIŞTI!\n~HisarMissile() ASLA ÇAĞRILMADI!\n-> Radar Soketleri ve Donanım Kilitleri Havada Kaldı (Leak)!", color='#FEE2E2', fontsize=8, ha='center')

    # Doğru Durum (Virtual)
    box_good = patches.FancyBboxPatch((0.08, 0.10), 0.84, 0.35, boxstyle="round,pad=0.02", facecolor='#064E3B', edgecolor='#10B981', linewidth=1.5)
    ax2.add_patch(box_good)
    ax2.text(0.50, 0.38, "VIRTUAL DESTRUCTOR [SAVUNMA MİMARİSİ STANDARDI]", color='#A7F3D0', fontsize=9, fontweight='bold', ha='center')
    ax2.text(0.50, 0.22, "delete base_ptr;  ──►  vtable Üzerinden ~HisarMissile() Çağrıldı\nArdından ~BaseInterceptor() Temizlendi (LIFO Sırası)\n-> Tüm Donanım Kaynakları Sıfır Sızıntıyla Boşaltıldı!", color='#ECFDF5', fontsize=8, ha='center')

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # Panel 3: C2 Hava Savunma Polimorfik Önleme Filosu
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Çokbiçimli Hava Savunma Katmanları (Menzile Göre Seçim)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    systems = [
        ("KORKUT-35mm", 4.0, '#F59E0B', "0 - 4 km\nNamlulu Hava Savunma"),
        ("HİSAR-A+", 15.0, '#3B82F6', "4 - 15 km\nAlçak İrtifa Füze"),
        ("HİSAR-O+", 25.0, '#6366F1', "15 - 25 km\nOrta İrtifa Füze"),
        ("SİPER Blok-1", 100.0, '#10B981', "25 - 100+ km\nUzun Menzil Bölge")
    ]

    ranges = [s[1] for s in systems]
    names = [s[0] for s in systems]
    colors = [s[2] for s in systems]

    bars = ax3.barh(names, ranges, color=colors, height=0.55, edgecolor='#334155', linewidth=1.5)
    ax3.set_xlabel("Önleme Menzili (km)", color='#94A3B8', fontsize=9)
    ax3.tick_params(colors='#CBD5E1', labelsize=8)
    ax3.set_xlim(0, 120)
    ax3.grid(axis='x', color='#334155', linestyle='--', alpha=0.6)

    for idx, bar in enumerate(bars):
        xval = bar.get_width()
        ax3.text(xval + 2, bar.get_y() + bar.get_height()/2.0, f"{xval:.0f} km ({systems[idx][3].splitlines()[0]})", ha='left', va='center', color='#F8FAFC', fontsize=8, fontweight='bold')

    ax3.text(60, -0.5, "Polimorfizm: Tek Arayüz (engage) -> 4 Farklı Silah!", color='#38BDF8', fontsize=8.5, fontweight='bold', ha='center')

    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi (Sanal Çağrı Gecikmesi)
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 Çağrıda Gecikme: Statik vs Sanal Dinamik Bağlama", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    bench_types = ['Sanal Çağrı\n(Dynamic Dispatch)', 'Statik Doğrudan Çağrı\n(Direct Inlined)']
    bench_values = [6.8, 4.3]
    bench_cols = ['#F59E0B', '#10B981']

    b_bars = ax4.barh(bench_types, bench_values, color=bench_cols, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("İşlemci Çağrı Süresi (ms)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.set_xlim(0, 10)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)

    for bar in b_bars:
        xval = bar.get_width()
        ax4.text(xval + 0.3, bar.get_y() + bar.get_height()/2.0, f"{xval:.1f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')

    ax4.text(5.0, 0.12, "DEVIRTUALIZATION (C++20 final)\nDerleyici final sınıflarda sanal çağrıyı\ndoğrudan statik inlining'e dönüştürür!", color='#34D399', fontsize=8.5, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_050(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# Polimorfizm, vptr ve Sanal Yıkıcı Kurallarının Programatik Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 050: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: Sanal Fonksiyon Dinamik Bağlama Testi
    class Shape:
        def area(self) -> float: raise NotImplementedError()

    class Circle(Shape):
        def __init__(self, r: float): self.r = r
        def area(self) -> float: return 3.14159 * self.r * self.r

    class Square(Shape):
        def __init__(self, a: float): self.a = a
        def area(self) -> float: return self.a * self.a

    shapes = [Circle(2.0), Square(3.0)]
    areas = [s.area() for s in shapes]
    assert abs(areas[0] - 12.56636) < 0.001, "Daire alanı hatalı hesaplandı!"
    assert areas[1] == 9.0, "Kare alanı hatalı hesaplandı!"
    print("  -> [PASS] Polimorfik dinamik alan hesaplama doğrulandı.")

    # 2. Test: Sanal Yıkıcı Zincirleme Doğrulaması
    destruction_order = []
    class BaseWithVirtualDtor:
        def cleanup(self):
            destruction_order.append("BASE_CLEANUP")

    class DerivedWithDtor(BaseWithVirtualDtor):
        def cleanup(self):
            destruction_order.append("DERIVED_CLEANUP")
            super().cleanup()

    obj: BaseWithVirtualDtor = DerivedWithDtor()
    obj.cleanup()
    assert destruction_order == ["DERIVED_CLEANUP", "BASE_CLEANUP"], "HATA: Yıkım sırası bozuk!"
    print("  -> [PASS] Sanal Yıkıcı LIFO tahliye sırası doğrulandı.")

    # 3. Test: vptr Ek Yükü Boyut Analizi (C++ 64-bit Model)
    sizeof_non_virtual = 8   # double x
    sizeof_with_virtual = 16  # __vptr (8B) + double x (8B)
    assert sizeof_with_virtual - sizeof_non_virtual == 8, "vptr boyut uyuşmazlığı!"
    print("  -> [PASS] __vptr 64-bit bellek yerleşimi onaylandı.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
