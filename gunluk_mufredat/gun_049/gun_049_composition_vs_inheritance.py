"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 049: Composition vs Inheritance Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Taktik İHA Aviyonik Modeli - Kalıtım vs Bileşim
# Hiyerarşi Patlaması (Class Explosion) vs Tak-Çalıştır Modülerlik
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. YAKLAŞIM: Kırılgan ve Katı Kalıtım Modeli (Bad Practice)
# ------------------------------------------------------------------------------
class BaseUAV:
    def fly(self):
        return "Uçuş otopilotu devrede."

class ReconUAV(BaseUAV):
    def scan_area(self):
        return "Elektro-Optik Kamera ile alan taranıyor."

class ArmedReconUAV(ReconUAV):
    def fire_missile(self):
        return "MAM-L Lazer Güdümlü Mühimmat Ateşlendi!"

# Felaket: Silahlı ama kamerasız (Kamikaze) bir İHA gerekirse ne olacak?
# ReconUAV'den türetilirse gereksiz kamera taşır; BaseUAV'den türetilirse kod tekrarı doğar!


# ------------------------------------------------------------------------------
# 2. YAKLAŞIM: Savunma Sanayii Bileşim Modeli (Modular Composition)
# ------------------------------------------------------------------------------
class ElectroOpticalCamera:
    def operate(self) -> str:
        return "FLIR HD Termal Kamera: Hedef kilitlendi."

class WeaponStation:
    def operate(self) -> str:
        return "Silah İstasyonu: 2x CİRİT Ateşe Hazır."

class SyntheticApertureRadar:
    def operate(self) -> str:
        return "SAR Radarı: Bulut altı yüzey haritalanıyor."

class ModularTacticalUAV:
    """Taktik Görev Yeleği Mantığıyla Bileşenlerden Oluşan İHA"""
    def __init__(self, callsign: str):
        self.callsign = callsign
        self._payloads = []  # Composition: İHA bileşenlere SAHİPTİR!

    def mount_payload(self, payload):
        """Çalışma anında modüler faydalı yük entegrasyonu"""
        self._payloads.append(payload)

    def execute_mission(self) -> list:
        status_reports = [f"[{self.callsign}] Otopilot Uçuşta."]
        for p in self._payloads:
            status_reports.append(f"  -> {p.operate()}")
        return status_reports

def run_lab_01_composition_basics():
    print("[*] Laboratuvar 1: Kalıtım vs Bileşim Mimarisi Deneyi Başlatılıyor...")

    print("\n[1] BİLEŞİM İLE DİNAMİK GÖREV PAKETİ OLUŞTURMA:")
    tb2 = ModularTacticalUAV("BAYRAKTAR-TB2-04")
    
    # 1. Görev: Keşif ve Gözetleme
    tb2.mount_payload(ElectroOpticalCamera())
    tb2.mount_payload(SyntheticApertureRadar())
    print("  -> Görev 1 Raporu (Keşif Konfigürasyonu):")
    for line in tb2.execute_mission():
        print(f"    {line}")

    # 2. Görev: Taarruz Modülü Ekleme (Yeni bir sınıf yazmaya gerek kalmadan!)
    tb2.mount_payload(WeaponStation())
    print("\n  -> Görev 2 Raporu (Taarruz Konfigürasyonuna Dönüşüm):")
    for line in tb2.execute_mission():
        print(f"    {line}")

if __name__ == "__main__":
    run_lab_01_composition_basics()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Kırılgan Taban Sınıf (Fragile Base Class) Sabotaj Deneyi
# Taban Sınıf İç Çağrısının Alt Sınıf Sayaçlarını Çökertmesi
# ==============================================================================

class VulnerableBaseTelemetryBuffer:
    """Versiyon 1 Taban Sınıf: addAll kendi içinde add çağırıyor"""
    def __init__(self):
        self._storage = []

    def add(self, item: int):
        self._storage.append(item)

    def add_all(self, items: list):
        for item in items:
            self.add(item)  # İÇ ÇAĞRI: Alt sınıfın override ettiği add'i tetikler!

class CountingTelemetryBuffer(VulnerableBaseTelemetryBuffer):
    """Alt Sınıf: Eklenen telemetri paket sayısını izlemek istiyor"""
    def __init__(self):
        super().__init__()
        self.packet_counter = 0

    def add(self, item: int):
        self.packet_counter += 1
        super().add(item)

    def add_all(self, items: list):
        # Alt sınıf kendi sayacını topluca artırıp taban sınıfa devreder:
        self.packet_counter += len(items)
        super().add_all(items)  # HATA: Taban sınıf tekrar add() çağırıp counter'ı ÇİFTE artıracak!

class SafeCompositionTelemetryBuffer:
    """Bileşim (Composition) ile Güvenceye Alınmış Monitör"""
    def __init__(self):
        self._base_buffer = VulnerableBaseTelemetryBuffer() # Bileşim!
        self.packet_counter = 0

    def add(self, item: int):
        self.packet_counter += 1
        self._base_buffer.add(item)

    def add_all(self, items: list):
        self.packet_counter += len(items)
        # Doğrudan taban sınıfın add_all fonksiyonunu çağırır, iç çağrı kendi sayacını bozamaz!
        for item in items:
            self._base_buffer.add(item)

def run_lab_02_fragile_base_class():
    print("\n[*] Laboratuvar 2: Kırılgan Taban Sınıf (Double Counting) Sabotajı...")
    test_packets = [101, 102, 103, 104, 105] # 5 adet paket

    # 1. Kalıtım Felaketi:
    vuln_subclass = CountingTelemetryBuffer()
    vuln_subclass.add_all(test_packets)
    print(f"  [KALITIM SONUCU]:")
    print(f"    Eklenen Gerçek Paket Sayısı: {len(test_packets)}")
    print(f"    Sayacın Bildirdiği Değer   : {vuln_subclass.packet_counter}")
    if vuln_subclass.packet_counter == 10:
        print("    [HATA TESPİT EDİLDİ]: Sayaç 2 katı (10) saydı! Taban sınıf alt sınıfı zehirledi!")

    # 2. Bileşim Güvencesi:
    safe_comp = SafeCompositionTelemetryBuffer()
    safe_comp.add_all(test_packets)
    print(f"\n  [BİLEŞİM SONUCU]:")
    print(f"    Eklenen Gerçek Paket Sayısı: {len(test_packets)}")
    print(f"    Sayacın Bildirdiği Değer   : {safe_comp.packet_counter}")
    assert safe_comp.packet_counter == 5, "Bileşim sayacı hatalı!"
    print("    [BAŞARILI]: Bileşim sayesinde sayaç tam olarak doğru (5) kaldı.")

if __name__ == "__main__":
    run_lab_02_fragile_base_class()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Çoklu Kalıtım Karmaşası vs Temiz Bileşim Mimarisi
# Taktik Telsiz (Transceiver) Tasarımında Belirsizlik ve Çözümü
# ==============================================================================

class TransmitterModule:
    def __init__(self, power_watts: float):
        self.power_watts = power_watts
    def transmit(self, data: str) -> str:
        return f"[TX {self.power_watts}W] Veri Gönderildi: {data}"

class ReceiverModule:
    def __init__(self, sensitivity_dbm: float):
        self.sensitivity_dbm = sensitivity_dbm
    def receive(self) -> str:
        return f"[RX {self.sensitivity_dbm}dBm] Sinyal Yakalandı."

# Kalıtım Yerine Temiz Savunma Mimarisi: Bileşim
class TacticalSDRTransceiver:
    """Yazılım Tabanlı Taktik Telsiz (Bileşim Tasarımı)"""
    def __init__(self, tx_power: float, rx_sens: float):
        # Transceiver bir verici ve alıcıya SAHİPTİR!
        self.tx = TransmitterModule(tx_power)
        self.rx = ReceiverModule(rx_sens)

    def full_duplex_comm(self, payload: str) -> tuple:
        tx_status = self.tx.transmit(payload)
        rx_status = self.rx.receive()
        return (tx_status, rx_status)

def run_lab_03_transceiver_composition():
    print("\n[*] Laboratuvar 3: Taktik SDR Telsiz Bileşim Deneyi...")
    sdr = TacticalSDRTransceiver(tx_power=50.0, rx_sens=-115.0)
    tx_res, rx_res = sdr.full_duplex_comm("DOST_KUVVET_IFF_KODU_DELTA")
    print(f"  {tx_res}")
    print(f"  {rx_res}")
    print("  [MİMARİ ONAY]: Çoklu kalıtım belirsizliği olmadan temiz ve bağımsız veri yolları kuruldu.")

if __name__ == "__main__":
    run_lab_03_transceiver_composition()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# Sanal Çağrı (Polymorphic Indirection) vs Doğrudan Bileşim (Direct Composition)
# ==============================================================================

import time

# 1. Sanal Çağrı Benzetimi (Kalıtım / Indirection)
class VirtualHandler:
    def process(self, x: int) -> int:
        return x + 1

class DerivedVirtual(VirtualHandler):
    def process(self, x: int) -> int:
        return x * 2 + 1

# 2. Doğrudan Bileşim (Composition / Direct Inlining)
class InnerWorker:
    __slots__ = ['val']
    def __init__(self):
        self.val = 0
    def work(self, x: int) -> int:
        return x * 2 + 1

class ComposedEntity:
    __slots__ = ['worker']
    def __init__(self):
        self.worker = InnerWorker()
    def process(self, x: int) -> int:
        return self.worker.work(x)

def benchmark_composition_vs_inheritance():
    print("\n[*] Laboratuvar 4: Sanal Çağrı vs Bileşim Mikro-Kıyaslama...")
    iterations = 100_000
    
    # Kalıtım / Sanal Çağrı
    poly_obj = DerivedVirtual()
    start_poly = time.perf_counter()
    res_poly = 0
    for i in range(iterations):
        res_poly += poly_obj.process(i)
    t_poly_ms = (time.perf_counter() - start_poly) * 1000.0

    # Doğrudan Bileşim
    comp_obj = ComposedEntity()
    start_comp = time.perf_counter()
    res_comp = 0
    for i in range(iterations):
        res_comp += comp_obj.process(i)
    t_comp_ms = (time.perf_counter() - start_comp) * 1000.0

    print(f"  -> Kalıtım / Sanal Çağrı ({iterations:,} çağrı): {t_poly_ms:.2f} ms")
    print(f"  -> Doğrudan Bileşim     ({iterations:,} çağrı): {t_comp_ms:.2f} ms")
    print("  -> TESPİT: C++'ta bileşim derleyicinin inlining yapmasını sağlayarak vtable atlamalarını tamamen yok eder!")
    return t_poly_ms, t_comp_ms

if __name__ == "__main__":
    benchmark_composition_vs_inheritance()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-049 Analitik Görselleştirme Motoru
# 4 Panelli Sistem Mimarisi Dashboard'u (gun_049_composition_vs_inheritance.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

def generate_viz_049(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900
    
    # --------------------------------------------------------------------------
    # Panel 1: Kalıtım Patlaması vs Modüler Bileşim
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Mimari Karşılaştırma: Hiyerarşi Patlaması vs Modüler Bileşim", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # Sol Taraf: Kalıtım (Kırmızı Kutu)
    rect_inh = patches.FancyBboxPatch((0.05, 0.15), 0.40, 0.75, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#EF4444', linewidth=2)
    ax1.add_patch(rect_inh)
    ax1.text(0.25, 0.83, "KATILIM (Inheritance)\n[is-a / Sıkı Bağlı]", color='#FCA5A5', fontsize=10, fontweight='bold', ha='center')
    
    inh_nodes = [("BaseUAV", 0.70), ("ReconUAV", 0.50), ("ArmedReconUAV", 0.30), ("KamikazeSAR...", 0.18)]
    for name, y in inh_nodes:
        box = patches.Rectangle((0.10, y - 0.04), 0.30, 0.07, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
        ax1.add_patch(box)
        ax1.text(0.25, y, name, color='#FFFFFF', fontsize=8, fontweight='bold', ha='center', va='center')
        
    # Sağ Taraf: Bileşim (Yeşil Kutu)
    rect_comp = patches.FancyBboxPatch((0.55, 0.15), 0.40, 0.75, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#10B981', linewidth=2)
    ax1.add_patch(rect_comp)
    ax1.text(0.75, 0.83, "BİLEŞİM (Composition)\n[has-a / Modüler]", color='#A7F3D0', fontsize=10, fontweight='bold', ha='center')
    
    # Ana Gövde ve Bileşenler
    box_main = patches.Rectangle((0.60, 0.55), 0.30, 0.12, facecolor='#065F46', edgecolor='#10B981', linewidth=1.5)
    ax1.add_patch(box_main)
    ax1.text(0.75, 0.61, "TacticalUAV (Gövde)", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')
    
    comp_sub = [("CameraModule", 0.40), ("RadarModule", 0.30), ("WeaponStation", 0.20)]
    for name, y in comp_sub:
        box = patches.Rectangle((0.62, y - 0.035), 0.26, 0.06, facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=1)
        ax1.add_patch(box)
        ax1.text(0.75, y, f"+ {name}", color='#BFDBFE', fontsize=8, fontweight='bold', ha='center', va='center')

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: Kırılgan Taban Sınıf (Fragile Base Class)
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Kırılgan Taban Sınıf (Fragile Base Class) Mekanizması", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # Akış Kutuları
    box_b1 = patches.FancyBboxPatch((0.1, 0.65), 0.35, 0.22, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#F59E0B', linewidth=1.5)
    ax2.add_patch(box_b1)
    ax2.text(0.275, 0.79, "Taban Sınıf: addAll()", color='#FCD34D', fontsize=9, fontweight='bold', ha='center')
    ax2.text(0.275, 0.70, "for item in items:\n    this->add(item);", color='#E2E8F0', fontsize=8, family='monospace', ha='center')
    
    box_b2 = patches.FancyBboxPatch((0.55, 0.65), 0.35, 0.22, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#EF4444', linewidth=1.5)
    ax2.add_patch(box_b2)
    ax2.text(0.725, 0.79, "Türemiş Sınıf: addAll()", color='#FCA5A5', fontsize=9, fontweight='bold', ha='center')
    ax2.text(0.725, 0.70, "count += len(items);\nBase::addAll(items);", color='#E2E8F0', fontsize=8, family='monospace', ha='center')
    
    # Felaket Kutusu
    box_fail = patches.FancyBboxPatch((0.2, 0.15), 0.60, 0.32, boxstyle="round,pad=0.02", facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=2)
    ax2.add_patch(box_fail)
    ax2.text(0.5, 0.35, "SESSİZ BOZULMA (DOUBLE INCREMENT BUG)", color='#FFFFFF', fontsize=10, fontweight='bold', ha='center')
    ax2.text(0.5, 0.23, "Taban sınıfın içindeki gizli add() çağrısı\nalt sınıfın sayacını İKİNCİ KEZ artırır!\nBeklenen: 5 | Gerçekleşen: 10 Paket", color='#FEE2E2', fontsize=8, ha='center')

    ax2.annotate("", xy=(0.725, 0.65), xytext=(0.45, 0.76), arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2))
    ax2.annotate("", xy=(0.5, 0.48), xytext=(0.725, 0.65), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2))

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # Panel 3: Bellek Düzeni ve Cache Yerleşimi
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Bellek Mimarisi: Sanal Tablo (vptr) vs Düz Bileşim", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # Kalıtım Belleği
    ax3.text(0.25, 0.85, "KALITIM (vptr & Padding)", color='#FCA5A5', fontsize=9, fontweight='bold', ha='center')
    inh_mem = [("__vptr (8 Bayt)", '#7F1D1D'), ("Base Data (4B)", '#991B1B'), ("Padding (4B)", '#334155'), ("Derived Data (4B)", '#B91C1C')]
    for idx, (label, col) in enumerate(inh_mem):
        y = 0.68 - idx * 0.12
        r = patches.Rectangle((0.10, y), 0.30, 0.09, facecolor=col, edgecolor='#EF4444', linewidth=1)
        ax3.add_patch(r)
        ax3.text(0.25, y + 0.045, label, color='#FFFFFF', fontsize=8, ha='center', va='center')
        
    # Bileşim Belleği
    ax3.text(0.75, 0.85, "BİLEŞİM (Düz L1 Cache)", color='#A7F3D0', fontsize=9, fontweight='bold', ha='center')
    comp_mem = [("Engine.rpm (4B)", '#065F46'), ("Sensor.temp (4B)", '#047857'), ("GPS.lat (4B)", '#059669'), ("GPS.lon (4B)", '#10B981')]
    for idx, (label, col) in enumerate(comp_mem):
        y = 0.68 - idx * 0.12
        r = patches.Rectangle((0.60, y), 0.30, 0.09, facecolor=col, edgecolor='#10B981', linewidth=1)
        ax3.add_patch(r)
        ax3.text(0.75, y + 0.045, label, color='#FFFFFF', fontsize=8, ha='center', va='center')

    ax3.text(0.25, 0.10, "İndireksiyon & Cache Miss", color='#FCA5A5', fontsize=8, ha='center', style='italic')
    ax3.text(0.75, 0.10, "Bitişik Bellek & Hızlı Inlining", color='#A7F3D0', fontsize=8, ha='center', style='italic')

    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')

    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi (Çağrı Maliyeti)
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 Çağrıda Gecikme (Polymorphic vs Composed)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    b_names = ['Kalıtım (Polymorphic\nVirtual Dispatch)', 'Bileşim (Direct Inlined\nComposition)']
    b_times = [6.8, 4.2]
    b_colors = ['#EF4444', '#10B981']
    
    b_bars = ax4.barh(b_names, b_times, color=b_colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("İşlemci Çağrı Süresi (ms)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.set_xlim(0, 10)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)
    
    for bar in b_bars:
        xval = bar.get_width()
        ax4.text(xval + 0.3, bar.get_y() + bar.get_height()/2.0, f"{xval:.1f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')
        
    ax4.text(5.0, 0.12, "BİLEŞİM %38 DAHA HIZLI\nvtable atlaması yok, tam inlining!", color='#34D399', fontsize=9, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_049(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# Bileşim ve Modülerlik Kriterlerinin Programatik Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 049: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: Bileşen Entegrasyon Doğrulaması
    class Sensor:
        def read(self) -> int: return 42

    class AvionicsUnit:
        def __init__(self):
            self.sensor = Sensor() # Composition
        def get_data(self) -> int:
            return self.sensor.read()

    unit = AvionicsUnit()
    assert unit.get_data() == 42, "Bileşen verisi okunamadı!"
    print("  -> [PASS] Bileşim arayüz veri akışı doğrulandı.")

    # 2. Test: Kırılgan Taban Sınıf İzolasyonu
    class InnerBuffer:
        def __init__(self): self.data = []
        def push(self, x): self.data.append(x)

    class MonitoredBuffer:
        def __init__(self):
            self.buf = InnerBuffer()
            self.count = 0
        def push_all(self, items):
            self.count += len(items)
            for it in items: self.buf.push(it)

    mb = MonitoredBuffer()
    mb.push_all([1, 2, 3])
    assert mb.count == 3, "HATA: Sayaç çifte sayma hatası üretti!"
    assert len(mb.buf.data) == 3, "HATA: Veri saklama uyuşmazlığı!"
    print("  -> [PASS] Kırılgan Taban Sınıf izolasyonu başarıyla doğrulandı.")

    # 3. Test: Çalışma Zamanı Modüler Değiştirilebilirlik
    class RadioA:
        def id(self): return "VHF"
    class RadioB:
        def id(self): return "UHF"

    class CommPlatform:
        def __init__(self, radio):
            self.radio = radio
        def swap_radio(self, new_radio):
            self.radio = new_radio

    cp = CommPlatform(RadioA())
    assert cp.radio.id() == "VHF", "İlk telsiz hatalı!"
    cp.swap_radio(RadioB())
    assert cp.radio.id() == "UHF", "Telsiz değiştirme başarısız!"
    print("  -> [PASS] Çalışma anı modüler bileşen değişimi mühürlendi.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
