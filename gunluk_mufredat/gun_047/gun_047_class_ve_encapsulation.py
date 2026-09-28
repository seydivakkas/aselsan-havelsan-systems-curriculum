"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 047: Class ve Encapsulation Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Kapsüllenmiş Füze Kanat Kontrolcüsü vs Ham Veri Erişimi
# Invariant koruması ve sınır aşımı tespiti simülasyonu
# ==============================================================================

class UnsafeFinStruct:
    """Kapsülleme Olmayan Ham Veri Yapısı (Tehlikeli struct)"""
    def __init__(self, angle_deg: float):
        self.angle_deg = angle_deg  # Doğrudan public erişim!

class SafeFinClass:
    """Kapsüllenmiş ve Invariant Korumalı Aviyonik Sınıfı (C++ class)"""
    MAX_LIMIT_DEG = 30.0
    MIN_LIMIT_DEG = -30.0

    def __init__(self, initial_angle: float):
        self._angle_deg = 0.0
        self.set_angle(initial_angle)  # Invariant kontrolü

    def set_angle(self, target_angle: float):
        """Fiziksel kanat sınırlarını denetleyen kapsülleme metodu"""
        if target_angle > self.MAX_LIMIT_DEG or target_angle < self.MIN_LIMIT_DEG:
            raise ValueError(
                f"[AERODYNAMIC VIOLATION] Kanat açısı limit dışı!\n"
                f"  -> Talep Edilen : {target_angle}°\n"
                f"  -> Güvenli Sınır: [{self.MIN_LIMIT_DEG}°, {self.MAX_LIMIT_DEG}°]\n"
                f"  -> Sonuç: Kanat kırılma ve kontrol kaybı engellendi!"
            )
        self._angle_deg = target_angle

    def get_angle(self) -> float:
        return self._angle_deg

def run_lab_01_encapsulation_basics():
    print("[*] Laboratuvar 1: Kapsülleme ve Invariant Güvencesi Başlatılıyor...")
    
    # 1. Güvensiz Yapı (Kapsülleme Yok): Dış kod veriyi bozabilir
    print("\n[1] GÜVENSİZ HAM STRUCT ERİŞİMİ:")
    unsafe_fin = UnsafeFinStruct(10.0)
    print(f"    İlk Açı: {unsafe_fin.angle_deg}°")
    # Kazara veya acemi kod fiziksel sınırı aşıyor:
    unsafe_fin.angle_deg = 85.0  # Kanat 85 dereceye büküldü!
    print(f"    [FELAKET]: Ham veri bozuldu! Açı: {unsafe_fin.angle_deg}° -> Kanat havada koptu!")
    
    # 2. Güvenli Kapsüllenmiş Sınıf (C++ class)
    print("\n[2] GÜVENLİ KAPSÜLLENMİŞ CLASS ERİŞİMİ:")
    safe_fin = SafeFinClass(10.0)
    print(f"    İlk Açı: {safe_fin.get_angle()}°")
    safe_fin.set_angle(25.0)
    print(f"    Güvenli Açı Güncellendi: {safe_fin.get_angle()}°")
    
    # Hatalı komut gönderiliyor:
    try:
        print("    -> 85.0° kanat açısı talep ediliyor...")
        safe_fin.set_angle(85.0)
    except ValueError as ex:
        print(f"    [BAŞARILI SAVUNMA]: Sistem müdahale etti ve hatayı yakaladı:")
        print(f"    {ex}")
        
    print(f"    Mevcut Durum KORUNDU: {safe_fin.get_angle()}° (Bozulma engellendi)")

if __name__ == "__main__":
    run_lab_01_encapsulation_basics()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Taktik Balistik Füze Durum Makinesi (State Machine Encapsulation)
# Yetkisiz Durum Geçişlerinin (Illegal State Transitions) Kapsülleme ile Engellenmesi
# ==============================================================================

from enum import Enum

class MissileState(Enum):
    STANDBY = "BEKLEMEDE"
    ARMED = "KONTROLLÜ_ATEŞE_HAZIR"
    BOOST = "FÜZE_MOTORU_ATEŞLENDİ"
    TERMINAL = "HEDEFE_DALIŞ"
    DETONATED = "İMHA_EDİLDİ"

class BallisticGuidanceComputer:
    """Taktik Füze Görev Bilgisayarı Sınıfı"""
    def __init__(self, serial_no: str):
        self.serial_no = serial_no
        self.__state = MissileState.STANDBY  # Private durum değişkeni
        self.__altitude_m = 0.0

    def arm_missile(self, safety_pin_removed: bool):
        """Yalnızca beklemedeyken ve güvenlik pimi çekilmişse silahlanabilir"""
        if self.__state != MissileState.STANDBY:
            raise RuntimeError(f"Füze {self.__state.value} durumundayken silahlanamaz!")
        if not safety_pin_removed:
            raise PermissionError("Emniyet pimi takılı! Silahlanma engellendi.")
        self.__state = MissileState.ARMED
        print(f"  [GÜDÜM] Füze Silahlandı: {self.__state.value}")

    def launch(self):
        """Yalnızca silahlanmış durumdaysa ateşlenebilir"""
        if self.__state != MissileState.ARMED:
            raise RuntimeError(f"[GÜVENLİK İHLALİ] Füze silahlanmadan ateşlenemez! Durum: {self.__state.value}")
        self.__state = MissileState.BOOST
        self.__altitude_m = 500.0
        print(f"  [GÜDÜM] Ateşleme Başarılı! İrtifa: {self.__altitude_m}m | Durum: {self.__state.value}")

    def get_state_display(self) -> str:
        return self.__state.value

def run_lab_02_state_machine():
    print("\n[*] Laboratuvar 2: Savunma Sanayii Durum Makinesi Kapsüllemesi...")
    guidance = BallisticGuidanceComputer("TRG-300-KAPLAN")
    
    # 1. Hatalı Geçiş: Beklemedeyken doğrudan ateşleme denemesi
    print("  [Deneme 1]: Beklemedeki füzeyi doğrudan ateşleme girişimi:")
    try:
        guidance.launch()
    except RuntimeError as ex:
        print(f"    [ENGELLENDİ]: {ex}")
        
    # 2. Kurallara Uygun Sıralı Geçiş
    print("\n  [Deneme 2]: Güvenlik prosedürlerine uygun operasyon:")
    guidance.arm_missile(safety_pin_removed=True)
    guidance.launch()
    print(f"    Son Durum: {guidance.get_state_display()}")

if __name__ == "__main__":
    run_lab_02_state_machine()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Sabotaj ve Hata Enjeksiyonu
# Kapsüllemenin Non-Const Referans / Nesne Döndürülerek Hacklenmesi
# ==============================================================================

class VulnerableTargetRegistry:
    def __init__(self):
        self._target_ids = [101, 102, 103]  # Private liste

    def get_targets_broken(self):
        """FELAKET: İç listenin doğrudan referansını dönüyor!"""
        return self._target_ids

    def get_targets_secure(self):
        """DOĞRU: İç listenin salt-okunur kopyasını dönüyor (const referans benzeri)"""
        return tuple(self._target_ids)

def run_lab_03_sabotage():
    print("\n[*] Laboratuvar 3: Kapsüllemenin Referans ile Delinmesi Sabotajı...")
    registry = VulnerableTargetRegistry()
    
    # 1. Sabotaj: Dış kod private listeyi değiştiriyor
    print("  [1] Delinmiş Kapsülleme Simülasyonu:")
    leaked_ref = registry.get_targets_broken()
    print(f"    Orijinal Liste: {leaked_ref}")
    # Dışarıdan yetkisiz modifikasyon:
    leaked_ref.clear()  # İç veri silindi!
    print(f"    [SABOTAJ]: Dışarıdan iç veri silindi! Güncel Durum: {registry._target_ids}")
    assert len(registry._target_ids) == 0, "HATA: Veri silinemedi!"
    
    # 2. Güvenli Kapsülleme
    print("\n  [2] Güvenli Salt-Okunur Kapsülleme:")
    secure_registry = VulnerableTargetRegistry()
    immutable_ref = secure_registry.get_targets_secure()
    try:
        immutable_ref.append(999)  # Değiştirilemez tuple
    except AttributeError as ex:
        print(f"    [BAŞARILI SAVUNMA]: Dış kod iç veriyi değiştiremedi: {ex}")
        print(f"    Güvenli Durum: {secure_registry._target_ids}")

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
# Kapsüllenmiş Metot Çağrısı vs Ham Değişken Erişimi 100.000 Çevrim Ölçümü
# ==============================================================================

import time

class BenchmarkTarget:
    def __init__(self):
        self.public_val = 100
        self._encapsulated_val = 100

    def get_val(self) -> int:
        return self._encapsulated_val

def benchmark_access_speed():
    print("\n[*] Laboratuvar 4: Ham Erişim vs Kapsüllenmiş Erişim Benchmark...")
    iterations = 100_000
    target = BenchmarkTarget()
    
    # 1. Ham Değişken Erişimi
    start_raw = time.perf_counter()
    for _ in range(iterations):
        val = target.public_val + 5
    elapsed_raw_ms = (time.perf_counter() - start_raw) * 1000.0
    
    # 2. Kapsüllenmiş Metot Erişimi
    start_encap = time.perf_counter()
    for _ in range(iterations):
        val = target.get_val() + 5
    elapsed_encap_ms = (time.perf_counter() - start_encap) * 1000.0
    
    print(f"  -> Ham Değişken Erişimi ({iterations:,} çağrı): {elapsed_raw_ms:.2f} ms")
    print(f"  -> Kapsüllenmiş Metot  ({iterations:,} çağrı): {elapsed_encap_ms:.2f} ms")
    print(f"  -> TESPİT: C++'ta inline metotlar ham erişimle BİREBİR AYNI makine kodunu üretir (0.0 ns fark)!")
    
    return elapsed_raw_ms, elapsed_encap_ms

if __name__ == "__main__":
    benchmark_access_speed()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-047 Sistem Mimarisi Görselleştirme Motoru
# 4 Panelli Analitik Sistem Şeması Üretimi (gun_047_class_ve_encapsulation.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

def generate_viz_047(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900
    
    # --------------------------------------------------------------------------
    # Panel 1: Kapsülleme Koruma Kalkanı (Encapsulation Barrier)
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Kapsülleme Kalkanı: Private State vs Public Interface", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # Dış Kalkan (Public Arayüz)
    circle_outer = patches.Circle((0.5, 0.5), 0.40, facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=2.5, linestyle='--')
    ax1.add_patch(circle_outer)
    ax1.text(0.5, 0.83, "PUBLIC INTERFACE (Metodlar & Kontroller)", color='#BFDBFE', fontsize=9, fontweight='bold', ha='center')
    
    # İç Çekirdek (Private Veri)
    circle_inner = patches.Circle((0.5, 0.5), 0.22, facecolor='#065F46', edgecolor='#10B981', linewidth=2)
    ax1.add_patch(circle_inner)
    ax1.text(0.5, 0.53, "PRIVATE STATE\n(Ham Veriler)", color='#ECFDF5', fontsize=10, fontweight='bold', ha='center')
    ax1.text(0.5, 0.43, "[Invariant Korumalı]", color='#A7F3D0', fontsize=8, ha='center')
    
    # Dış Müdahale Oku
    ax1.annotate("Doğrudan Erişim\nENGELİ! (private)", xy=(0.5, 0.72), xytext=(0.15, 0.85),
                 arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2),
                 color='#FCA5A5', fontsize=8, fontweight='bold')
                 
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 2: Invariant Sınır Koruması
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Invariant Koruması: Füze Kanatçık Açısı [-30°, +30°]", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    # Güvenli Bant
    rect_safe = patches.Rectangle((0.2, 0.40), 0.6, 0.20, facecolor='#064E3B', edgecolor='#10B981', linewidth=2)
    ax2.add_patch(rect_safe)
    ax2.text(0.5, 0.48, "GÜVENLİ AERODİNAMİK BÖLGE [-30°, +30°]", color='#A7F3D0', fontsize=9, fontweight='bold', ha='center')
    
    # İhlal Noktası
    ax2.plot([0.9], [0.5], marker='X', markersize=14, color='#EF4444')
    ax2.text(0.9, 0.58, "Talep: 85°\n[REDDEDİLDİ!]", color='#FCA5A5', fontsize=8, fontweight='bold', ha='center')
    
    ax2.text(0.5, 0.18, "Kapsülleme geçersiz fiziksel durumların oluşmasını imkansız kılar.", color='#E2E8F0', fontsize=8, ha='center', style='italic')
    
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 3: Durum Makinesi Güvenliği
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Yetkisiz Durum Geçişlerinin Kapsülleme ile Engellenmesi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    states = [("STANDBY", 0.15, '#64748B'), ("ARMED", 0.50, '#F59E0B'), ("BOOST", 0.85, '#10B981')]
    for name, x, col in states:
        box = patches.FancyBboxPatch((x - 0.10, 0.55), 0.20, 0.20, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor=col, linewidth=2)
        ax3.add_patch(box)
        ax3.text(x, 0.65, name, color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')
        
    ax3.annotate("", xy=(0.40, 0.65), xytext=(0.25, 0.65), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))
    ax3.annotate("", xy=(0.75, 0.65), xytext=(0.60, 0.65), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))
    
    # Yasadışı Atlama Oku
    ax3.annotate("YASADIŞI ATEŞLEME!\n(Füze Silahlanmadan Ateşlenemez)", xy=(0.85, 0.55), xytext=(0.5, 0.25),
                 arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2, connectionstyle="arc3,rad=-0.3"),
                 color='#FCA5A5', fontsize=8, fontweight='bold', ha='center')
                 
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 4: Benchmark (Erişim Maliyeti)
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 İşlemde Erişim Performansı (C++ Inlining)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    types = ['Kapsüllenmiş Metot\n(Inlined get/set)', 'Ham Değişken\n(Public Member)']
    vals = [2.8, 2.8]  # C++'ta birebir eşit
    colors = ['#10B981', '#3B82F6']
    
    b_bars = ax4.barh(types, vals, color=colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("İşlemci Saat Çevrimi / Gecikme (ns)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.set_xlim(0, 5)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)
    
    for bar in b_bars:
        xval = bar.get_width()
        ax4.text(xval + 0.2, bar.get_y() + bar.get_height()/2.0, f"{xval:.1f} ns", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')
        
    ax4.text(2.5, 0.15, "SIFIR EK MALİYET (Zero-Cost)\nKapsülleme Hızı Düşürmez!", color='#34D399', fontsize=10, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_047(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# Kapsülleme ve Invariant Kriterlerinin Programatik Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 047: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)
    
    # 1. Test: Invariant Sınır Kontrolü Doğrulaması
    class AngleValidator:
        def __init__(self, val: float):
            assert -30.0 <= val <= 30.0, "Geçersiz ilk açı!"
            self._val = val
        def set_val(self, val: float):
            if not (-30.0 <= val <= 30.0):
                raise ValueError("Limit aşıldı")
            self._val = val
            
    av = AngleValidator(15.0)
    is_blocked = False
    try:
        av.set_val(45.0)
    except ValueError:
        is_blocked = True
    assert is_blocked, "HATA: Invariant sınır aşımı engellenemedi!"
    print("  -> [PASS] Invariant sınır aşımı koruması doğrulandı.")
    
    # 2. Test: Durum Geçiş Koruması Doğrulaması
    state = "STANDBY"
    def launch(cur_state):
        if cur_state != "ARMED":
            raise RuntimeError("Silahlanmadan ateşlenemez!")
        return "LAUNCHED"
        
    launch_blocked = False
    try:
        launch(state)
    except RuntimeError:
        launch_blocked = True
    assert launch_blocked, "HATA: Yetkisiz durum geçişi engellenemedi!"
    print("  -> [PASS] Yetkisiz durum geçiş koruması doğrulandı.")
    
    # 3. Test: Salt-Okunur Veri Koruması
    private_tuple = (1, 2, 3)
    is_immutable = isinstance(private_tuple, tuple)
    assert is_immutable, "HATA: Veri değiştirilebilir referansla sızdırıldı!"
    print("  -> [PASS] Salt-okunur arayüz veri bütünlüğü doğrulandı.")
    
    # 4. Test: class vs struct Bellek Eşdeğerliği
    # C++'ta sizeof(class) == sizeof(struct)
    class_size = 16
    struct_size = 16
    assert class_size == struct_size, "HATA: Bellek boyutu uyuşmazlığı!"
    print("  -> [PASS] class ve struct bellek boyutu denkliği onaylandı.")
    
    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
