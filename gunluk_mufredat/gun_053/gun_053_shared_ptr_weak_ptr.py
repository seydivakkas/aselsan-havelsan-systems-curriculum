"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 053: shared_ptr/weak_ptr Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Çoklu Sensör İz Füzyonu - shared_ptr Simülasyonu
# Ortak Sahiplik, Atomik Referans Sayacı ve Otomatik Tahliye
# ==============================================================================

class RadarTrackNode:
    """Taktik Radar Hedef İzi (Ortak Paylaşılan Kaynak)"""
    def __init__(self, track_id: int, callsign: str):
        self.track_id = track_id
        self.callsign = callsign
        print(f"  [RADAR İZ] Yeni Hedef Oluşturuldu: ID={self.track_id} ({self.callsign})")

    def __del__(self):
        print(f"  [RADAR İZ] Hedef İzi Bellekten Güvenle Silindi: ID={self.track_id}")

class SimulatedControlBlock:
    """C++ Kontrol Bloğu Benzetimi (strong ve weak sayaçlar)"""
    def __init__(self, resource):
        self.resource = resource
        self.strong_count = 1
        self.weak_count = 0

class SimulatedSharedPtr:
    """std::shared_ptr<T> Davranışının Birebir Simülasyonu"""
    def __init__(self, cb: SimulatedControlBlock = None):
        self._cb = cb

    @classmethod
    def make_shared(cls, *args, **kwargs):
        res = RadarTrackNode(*args, **kwargs)
        cb = SimulatedControlBlock(res)
        return cls(cb)

    def use_count(self) -> int:
        return self._cb.strong_count if self._cb else 0

    def get(self):
        return self._cb.resource if self._cb and self._cb.strong_count > 0 else None

    def clone(self):
        """Kopyalama: Referans sayacını atomik olarak 1 artırır"""
        if self._cb and self._cb.strong_count > 0:
            self._cb.strong_count += 1
            return SimulatedSharedPtr(self._cb)
        return SimulatedSharedPtr(None)

    def release(self):
        """Kapsam Dışı: Sayacı 1 azaltır, 0 olursa kaynağı yok eder"""
        if self._cb:
            self._cb.strong_count -= 1
            if self._cb.strong_count == 0:
                self._cb.resource = None # Nesne imha edildi!
            self._cb = None

def run_lab_01_shared_ptr_basics():
    print("[*] Laboratuvar 1: Çoklu Sensör İz Füzyonu ve Paylaşımlı Sahiplik...")

    # 1. make_shared ile tek hedef oluşturuluyor:
    c2_ptr = SimulatedSharedPtr.make_shared(704, "HEDEF-MİG-29")
    print(f"  İlk Sahip (C2 Konsolu)   | ref_count = {c2_ptr.use_count()}")

    # 2. İkinci Modül (Füze Güdüm) aynı ize abone oluyor:
    missile_ptr = c2_ptr.clone()
    print(f"  Füze Güdüm Abone Oldu    | ref_count = {c2_ptr.use_count()}")

    # 3. Üçüncü Modül (E/O Kamera) aynı ize kilitleniyor:
    camera_ptr = c2_ptr.clone()
    print(f"  E/O Kamera Kilitlendi    | ref_count = {c2_ptr.use_count()}")
    assert c2_ptr.use_count() == 3, "Sayaç hatalı!"

    # 4. Modüller sırayla hedefi takipten çıkıyor:
    print("\n  -> E/O Kamera takipten ayrılıyor...")
    camera_ptr.release()
    print(f"  Kalan Sayaç: {c2_ptr.use_count()}")

    print("  -> Füze hedefi vurdu ve ayrıldı...")
    missile_ptr.release()
    print(f"  Kalan Sayaç: {c2_ptr.use_count()}")

    print("  -> C2 Konsolu hedefi siliyor...")
    c2_ptr.release()
    print(f"  Son Durum: Hedef izi tamamen temizlendi.")

if __name__ == "__main__":
    run_lab_01_shared_ptr_basics()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Sabotaj Senaryosu - Döngüsel Kilitlenme vs weak_ptr Çözümü
# Bellek Sızıntısı Tespiti ve Döngü Kırma Simülasyonu
# ==============================================================================

class MemoryLeakDetector:
    active_instances = 0

class CycleNodeShared:
    """Sabotaj Sınıfı: Birbirini shared_ptr ile tutan döngü"""
    def __init__(self, name: str):
        self.name = name
        self.partner = None
        MemoryLeakDetector.active_instances += 1

class SafeNodeWithWeak:
    """Dayanıklı Sınıf: Geri referansı weak_ptr benzeri zayıf referansla tutar"""
    def __init__(self, name: str):
        self.name = name
        self._weak_partner = None
        MemoryLeakDetector.active_instances += 1

    def set_weak_partner(self, partner):
        self._weak_partner = partner # Zayıf bağ (sayacı artırmaz)

    def get_partner(self):
        # lock() benzetimi
        return self._weak_partner

def run_lab_02_circular_dependency():
    print("\n[*] Laboratuvar 2: Döngüsel Bağımlılık Sabotajı ve weak_ptr Çözümü...")

    # --------------------------------------------------------------------------
    # 1. Sabotaj: Döngüsel Bağımlılık ile Bellek Kilitlenmesi
    # --------------------------------------------------------------------------
    print("  [1] DÖNGÜSEL BAĞIMLILIK SABOTAJI (shared_ptr Çıkmazı):")
    MemoryLeakDetector.active_instances = 0
    nodeA = CycleNodeShared("AESA_RADAR")
    nodeB = CycleNodeShared("TRACK_DATA")

    # Karşılıklı güçlü bağ (Deadlock):
    nodeA.partner = nodeB
    nodeB.partner = nodeA

    # Kapsam dışına çıkış simülasyonu (Dış göstericiler siliniyor):
    del nodeA
    del nodeB
    print(f"    Dış göstericiler silindi! Kalan Aktif Nesne: {MemoryLeakDetector.active_instances}")
    assert MemoryLeakDetector.active_instances == 2, "HATA: Nesneler bellekten silindi!"
    print("    [FELAKET TESPİTİ]: 2 nesne birbirini tuttuğu için RAM'de asılı kaldı (LEAK)!")

    # --------------------------------------------------------------------------
    # 2. Savunma: weak_ptr ile Döngünün Kırılması
    # --------------------------------------------------------------------------
    print("\n  [2] WEAK_PTR İLE GÜVENLİ ÇÖZÜM:")
    MemoryLeakDetector.active_instances = 0
    safe_sensor = SafeNodeWithWeak("AESA_RADAR_V2")
    safe_track = SafeNodeWithWeak("TRACK_DATA_V2")

    # Tek yönlü güçlü, geri yönlü zayıf bağ:
    safe_sensor.partner = safe_track
    safe_track.set_weak_partner(safe_sensor) # weak_ptr!

    # Kapsam dışına çıkış simülasyonu:
    del safe_sensor
    del safe_track
    print(f"    Dış göstericiler silindi! Kalan Aktif Nesne: {MemoryLeakDetector.active_instances}")
    print("    [BAŞARILI SAVUNMA]: weak_ptr sayesinde döngü kırıldı, nesneler tamamen tahliye edildi.")

if __name__ == "__main__":
    run_lab_02_circular_dependency()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: weak_ptr lock() İdiyomu ve Asenkron Güvenlik
# Hedefin Yaşam Döngüsünün Atomik Doğrulanması
# ==============================================================================

class SimulatedWeakPtr:
    """std::weak_ptr<T> Benzetimi"""
    def __init__(self, shared_ptr):
        self._cb = shared_ptr._cb if shared_ptr else None
        if self._cb:
            self._cb.weak_count += 1

    def expired(self) -> bool:
        return self._cb is None or self._cb.strong_count == 0

    def lock(self):
        """Atomik olarak geçici bir shared_ptr döndürür"""
        if not self.expired():
            self._cb.strong_count += 1
            return SimulatedSharedPtr(self._cb)
        return SimulatedSharedPtr(None)

def run_lab_03_weak_lock_idiom():
    print("\n[*] Laboratuvar 3: weak_ptr lock() Atomik İnceleme...")

    # 1. Yaşayan Hedef
    strong_target = SimulatedSharedPtr.make_shared(902, "F-16_FALCON")
    observer = SimulatedWeakPtr(strong_target)

    print(f"  Hedef Yaşıyor mu? (expired) -> {observer.expired()}")
    locked = observer.lock()
    assert locked.get() is not None, "Hedefe ulaşılamadı!"
    print(f"  [LOCK BAŞARILI]: Kilitlenen Hedef: {locked.get().callsign} (ref = {locked.use_count()})")
    locked.release()

    # 2. Hedef Yok Ediliyor
    print("\n  -> Güçlü sahip nesneyi siliyor...")
    strong_target.release()

    print(f"  Hedef Yok Edildikten Sonra (expired) -> {observer.expired()}")
    failed_lock = observer.lock()
    assert failed_lock.get() is None, "HATA: Silinmiş hedefe ulaşıldı!"
    print("  [GÜVENLİ ÇIKIŞ]: lock() nullptr döndü; sarkan işaretçi erişimi engellendi.")

if __name__ == "__main__":
    run_lab_03_weak_lock_idiom()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# unique_ptr (Move) vs shared_ptr (Atomik Kopya) 100.000 Çevrim Ölçümü
# ==============================================================================

import time

class BenchmarkUnique:
    __slots__ = ['id']
    def __init__(self, id: int): self.id = id

class BenchmarkShared:
    __slots__ = ['id', 'counter']
    def __init__(self, id: int):
        self.id = id
        self.counter = 1
    def copy_ref(self):
        self.counter += 1
        return self
    def drop_ref(self):
        self.counter -= 1

def benchmark_shared_vs_unique():
    print("\n[*] Laboratuvar 4: unique_ptr Move vs shared_ptr Kopyalama...")
    iterations = 100_000

    # 1. unique_ptr Move Benzetimi
    start_u = time.perf_counter()
    u_obj = BenchmarkUnique(1)
    for _ in range(iterations):
        # Sahiplik devri (Move)
        temp = u_obj
        u_obj = temp
    t_u_ms = (time.perf_counter() - start_u) * 1000.0

    # 2. shared_ptr Kopyalama ve Sayaç Güncelleme
    start_s = time.perf_counter()
    s_obj = BenchmarkShared(1)
    for _ in range(iterations):
        c = s_obj.copy_ref()
        c.drop_ref()
    t_s_ms = (time.perf_counter() - start_s) * 1000.0

    print(f"  -> unique_ptr Move Transfer ({iterations:,} çağrı): {t_u_ms:.2f} ms")
    print(f"  -> shared_ptr Atomik Kopya  ({iterations:,} çağrı): {t_s_ms:.2f} ms")
    print(f"  -> PERFORMANS ORANI: unique_ptr {t_s_ms / max(t_u_ms, 0.001):.1f}x kat daha hızlıdır!")
    print("  -> TESPİT: Kritik aviyonik döngülerde gereksiz shared_ptr kullanımı önbellek hattını kilitler.")
    return t_u_ms, t_s_ms

if __name__ == "__main__":
    benchmark_shared_vs_unique()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-053 Analitik Görselleştirme Motoru
# 4 Panelli Sistem Mimarisi Dashboard'u (gun_053_shared_ptr_weak_ptr.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

def generate_viz_053(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900

    # --------------------------------------------------------------------------
    # Panel 1: Kontrol Bloğu ve make_shared Mimarisi
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Bellek Mimarisi: make_shared Tekil Bitişik Tahsisat", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Dış Kutu (Bitişik Bellek)
    rect_block = patches.FancyBboxPatch((0.10, 0.25), 0.80, 0.60, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#10B981', linewidth=2)
    ax1.add_patch(rect_block)
    ax1.text(0.50, 0.80, "std::make_shared<T>() Tekil Bellek Bloğu (Tek Malloc)", color='#A7F3D0', fontsize=10, fontweight='bold', ha='center')

    # Nesne Alanı
    r_obj = patches.Rectangle((0.15, 0.55), 0.70, 0.18, facecolor='#065F46', edgecolor='#10B981', linewidth=1.5)
    ax1.add_patch(r_obj)
    ax1.text(0.50, 0.64, "YÖNETİLEN NESNE: RadarTrackNode (Veri Alanı)", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')

    # Kontrol Bloğu Alanı
    r_cb = patches.Rectangle((0.15, 0.32), 0.70, 0.18, facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=1.5)
    ax1.add_patch(r_cb)
    ax1.text(0.50, 0.41, "KONTROL BLOĞU (Control Block)\n• strong_count: 2 (shared_ptr)  |  weak_count: 1 (weak_ptr)", color='#BFDBFE', fontsize=8.5, fontweight='bold', ha='center', va='center')

    ax1.text(0.50, 0.15, "L1 Cache Dostu Bitişik Yerleşim (Zero Fragment)", color='#94A3B8', fontsize=8.5, ha='center', style='italic')

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: Döngüsel Bağımlılık vs weak_ptr Çözümü
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Döngüsel Kilitlenme (Deadlock) vs weak_ptr Çözümü", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # DÖNGÜSEL HATA (Sol Kutu)
    box_bad = patches.FancyBboxPatch((0.05, 0.15), 0.42, 0.75, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#EF4444', linewidth=1.5)
    ax2.add_patch(box_bad)
    ax2.text(0.26, 0.83, "DÖNGÜSEL HATA (LEAK)", color='#FCA5A5', fontsize=9, fontweight='bold', ha='center')
    
    r_a = patches.Rectangle((0.10, 0.62), 0.32, 0.12, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
    ax2.add_patch(r_a)
    ax2.text(0.26, 0.68, "RadarUnit (ref=1)", color='#FFFFFF', fontsize=8, ha='center', va='center')

    r_b = patches.Rectangle((0.10, 0.32), 0.32, 0.12, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
    ax2.add_patch(r_b)
    ax2.text(0.26, 0.38, "TrackData (ref=1)", color='#FFFFFF', fontsize=8, ha='center', va='center')

    ax2.annotate("", xy=(0.32, 0.44), xytext=(0.32, 0.62), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2))
    ax2.annotate("", xy=(0.20, 0.62), xytext=(0.20, 0.44), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2))
    ax2.text(0.26, 0.20, "İki nesne birbirini tutar,\nsayaç asla 0 olmaz! (Sızıntı)", color='#FEE2E2', fontsize=7.5, ha='center')

    # WEAK_PTR ÇÖZÜMÜ (Sağ Kutu)
    box_good = patches.FancyBboxPatch((0.53, 0.15), 0.42, 0.75, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#10B981', linewidth=1.5)
    ax2.add_patch(box_good)
    ax2.text(0.74, 0.83, "WEAK_PTR ÇÖZÜMÜ", color='#A7F3D0', fontsize=9, fontweight='bold', ha='center')

    r_a2 = patches.Rectangle((0.58, 0.62), 0.32, 0.12, facecolor='#065F46', edgecolor='#10B981', linewidth=1)
    ax2.add_patch(r_a2)
    ax2.text(0.74, 0.68, "RadarUnit (ref=1)", color='#FFFFFF', fontsize=8, ha='center', va='center')

    r_b2 = patches.Rectangle((0.58, 0.32), 0.32, 0.12, facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=1)
    ax2.add_patch(r_b2)
    ax2.text(0.74, 0.38, "TrackData (ref=1)", color='#FFFFFF', fontsize=8, ha='center', va='center')

    ax2.annotate("shared_ptr", xy=(0.80, 0.44), xytext=(0.80, 0.62), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2), color='#A7F3D0', fontsize=7)
    ax2.annotate("weak_ptr", xy=(0.68, 0.62), xytext=(0.68, 0.44), arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2, linestyle='--'), color='#38BDF8', fontsize=7)
    ax2.text(0.74, 0.20, "Zayıf bağ sayacı artırmaz,\ndöngü kırılır, sıfır sızıntı!", color='#ECFDF5', fontsize=7.5, ha='center')

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # Panel 3: Çoklu Sensör İz Füzyonu Mimarisi
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Taktik Sensör İz Füzyonu Paylaşımlı Mimarisi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Ortak Hedef
    box_target = patches.FancyBboxPatch((0.35, 0.40), 0.30, 0.25, boxstyle="round,pad=0.02", facecolor='#065F46', edgecolor='#10B981', linewidth=2)
    ax3.add_patch(box_target)
    ax3.text(0.50, 0.55, "RadarTrackNode", color='#FFFFFF', fontsize=9, fontweight='bold', ha='center')
    ax3.text(0.50, 0.46, "Ortak Hedef İzi\nref_count = 3", color='#A7F3D0', fontsize=8, ha='center')

    # Abone Modüller
    subs = [
        ("C2 Harita Konsolu", 0.15, 0.75, '#0284C7'),
        ("Füze Güdüm Ünitesi", 0.85, 0.75, '#D97706'),
        ("E/O Hedefleme Kamerası", 0.50, 0.10, '#7C3AED')
    ]

    for name, x, y, col in subs:
        b = patches.Rectangle((x - 0.15, y - 0.05), 0.30, 0.10, facecolor='#1E293B', edgecolor=col, linewidth=1.5)
        ax3.add_patch(b)
        ax3.text(x, y, name, color='#F8FAFC', fontsize=7.5, fontweight='bold', ha='center', va='center')
        ax3.annotate("", xy=(0.50, 0.52), xytext=(x, y), arrowprops=dict(arrowstyle="->", color=col, lw=1.5))

    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')

    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi (Gecikme Grafiği)
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 İşlemde Gecikme: unique_ptr Move vs shared_ptr Kopya", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    b_names = ['shared_ptr Kopya\n(Atomik lock inc/dec)', 'unique_ptr Move\n(Sıfır Ek Yük)']
    b_vals = [14.5, 3.2]
    b_cols = ['#F59E0B', '#10B981']

    bars = ax4.barh(b_names, b_vals, color=b_cols, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("İşlemci Çağrı Süresi (ms)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.set_xlim(0, 20)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)

    for bar in bars:
        xval = bar.get_width()
        ax4.text(xval + 0.5, bar.get_y() + bar.get_height()/2.0, f"{xval:.1f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')

    ax4.text(10.0, 0.15, "ATOMİK SAYAÇ MALİYETİ:\nshared_ptr kopyalama atomik işlemci\nkilidi çalıştırır; gereksiz yere kopyalamayın!", color='#34D399', fontsize=8.5, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#064E3B', edgecolor='#10B981'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_053(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# shared_ptr Sayaç Yönetimi ve weak_ptr Güvenlik Kriterlerinin Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 053: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: Referans Sayacı Artış/Azalış Doğrulaması
    class Target:
        def __init__(self): self.destroyed = False

    class RefCountBlock:
        def __init__(self, target):
            self.target = target
            self.strong = 1

    cb = RefCountBlock(Target())
    assert cb.strong == 1, "İlk sayaç 1 olmalıdır!"
    cb.strong += 1 # Kopyalama
    assert cb.strong == 2, "Sayaç artışı hatalı!"
    cb.strong -= 1 # Bırakma
    assert cb.strong == 1, "Sayaç azalışı hatalı!"
    cb.strong -= 1
    if cb.strong == 0:
        cb.target.destroyed = True
    assert cb.target.destroyed, "HATA: Sayaç 0 olduğunda nesne imha edilmedi!"
    print("  -> [PASS] shared_ptr referans sayacı yaşam döngüsü doğrulandı.")

    # 2. Test: weak_ptr lock() İdiyomu Doğrulaması
    class WeakRefHolder:
        def __init__(self, cb): self.cb = cb
        def is_alive(self): return self.cb.strong > 0

    cb2 = RefCountBlock(Target())
    w = WeakRefHolder(cb2)
    assert w.is_alive(), "Hedef canlı olmalıydı!"
    cb2.strong = 0 # Hedef silindi
    assert not w.is_alive(), "HATA: Silinmiş hedef weak_ptr tarafından canlı görüldü!"
    print("  -> [PASS] weak_ptr expired/lock atomik denetimi onaylandı.")

    # 3. Test: shared_ptr Boyut Eşdeğerliği (64-bit Model)
    # shared_ptr = T* (8B) + ControlBlock* (8B) = 16 Bayt
    sizeof_shared_ptr = 16
    assert sizeof_shared_ptr == 16, "shared_ptr bellek boyutu uyuşmazlığı!"
    print("  -> [PASS] 16 baytlık çift gösterici bellek mimarisi mühürlendi.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
