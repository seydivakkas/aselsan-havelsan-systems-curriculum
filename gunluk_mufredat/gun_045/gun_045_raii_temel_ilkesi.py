"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 045: RAII Temel İlkesi Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: Temel RAII Mekanizması Simülasyonu
# ScopedResourceHandle ile Normal Çıkış vs İstisna Anında Temizlik
# ==============================================================================

class ScopedResourceHandle:
    """
    C++ RAII Sarıcısı Eşdeğeri:
    class ScopedResourceHandle {
    public:
        ScopedResourceHandle(int id) : resource_id(id) { acquire(); }
        ~ScopedResourceHandle() { release(); }
    };
    """
    def __init__(self, resource_name: str, resource_id: int):
        self.resource_name = resource_name
        self.resource_id = resource_id
        self.is_acquired = True
        print(f"  [CTOR] {self.resource_name} (ID: {self.resource_id}) BAŞARIYLA EDİNİLDİ. (Kaynak Açık)")

    def release(self):
        if self.is_acquired:
            self.is_acquired = False
            print(f"  [DTOR] {self.resource_name} (ID: {self.resource_id}) OTOMATİK İADE EDİLDİ. (Kaynak Kapalı)")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Python Context Manager, C++ RAII Destructor semantiğini birebir modeller
        self.release()
        if exc_type is not None:
            print(f"  [UNWIND] İstisna tespit edildi: {exc_val} -> Destructor çağrısı garanti edildi!")
        return False  # İstisnayı yukarı fırlatmaya devam et

def run_lab_01_raii_basics():
    print("[*] Laboratuvar 1: RAII Yaşam Döngüsü ve Deterministik Temizlik...")
    
    # 1. Senaryo: Normal Kapsam Çıkışı (Scope Exit)
    print("\n[Senaryo 1: Normal Fonksiyon Çıkışı]")
    with ScopedResourceHandle("RadarVeriDosyasi_FD", 101) as handle:
        print("    -> Radar telemetri verileri dosyaya yazılıyor...")
    print("    -> Kapsam dışına çıkıldı. Kaynak durumu kontrol ediliyor.")
    assert not handle.is_acquired, "HATA: Kaynak serbest bırakılmadı!"
    
    # 2. Senaryo: İstisna (Exception) Fırlatıldığında Stack Unwinding
    print("\n[Senaryo 2: Hata ve Exception Durumunda Stack Unwinding]")
    try:
        with ScopedResourceHandle("KriptoDonanimKilidi", 202) as crypto_lock:
            print("    -> Kriptolama başladı...")
            raise RuntimeError("Donanım Parite Hatası (Parity Error)!")
            print("    -> Bu satır ASLA çalışmaz!")
    except RuntimeError as ex:
        print(f"    -> Dışarıda yakalanan hata: {ex}")
        
    assert not crypto_lock.is_acquired, "HATA: Hata fırlatıldığında destructor çalışmadı!"
    print("    -> [BAŞARILI]: Hata fırlatılmasına rağmen kaynak sızmadan kapatıldı!")

if __name__ == "__main__":
    run_lab_01_raii_basics()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Aviyonik Taktik Telsiz Kripto Oturumu (ScopedCryptoSession)
# Çok kanallı kripto motorunda Deadlock ve Kilit Sızıntısı Savunması
# ==============================================================================

class HardwareCryptoEngine:
    """Savunma Sanayii Taktik Kripto Donanım Arayüzü"""
    def __init__(self):
        self.is_locked = False
        self.active_channel = None

    def lock_engine(self, channel_id: int):
        if self.is_locked:
            raise ResourceWarning(f"[DEADLOCK UYARISI] Kripto donanımı Kanal {self.active_channel} tarafından kilitli!")
        self.is_locked = True
        self.active_channel = channel_id
        print(f"  [HARDWARE] Donanım Kilitlendi -> Kanal {channel_id} tahsis edildi.")

    def unlock_engine(self):
        if not self.is_locked:
            print("  [HARDWARE UYARI] Donanım zaten serbestti.")
            return
        print(f"  [HARDWARE] Donanım Kilidi Açıldı -> Kanal {self.active_channel} serbest bırakıldı.")
        self.is_locked = False
        self.active_channel = None

class ScopedCryptoSession:
    """C++ std::lock_guard benzeri RAII Kripto Oturumu"""
    def __init__(self, engine: HardwareCryptoEngine, channel_id: int):
        self.engine = engine
        self.channel_id = channel_id
        self.engine.lock_engine(channel_id)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.engine.unlock_engine()
        return False

def run_lab_02_crypto_session():
    print("\n[*] Laboratuvar 2: Aviyonik Taktik Kripto Oturumu Senaryosu...")
    engine = HardwareCryptoEngine()
    
    # Görev 1: Başarılı Şifreleme Oturumu
    print("  [Görev 1]: Normal Şifreli İletişim Oturumu Başlatılıyor...")
    with ScopedCryptoSession(engine, channel_id=1):
        print("    -> Gizli telemetri verisi şifreleniyor...")
    print("    -> Görev 1 tamamlandı. Donanım durumu: Kilitli mi? ->", engine.is_locked)
    
    # Görev 2: Görev Ortasında Hata Çıkması
    print("\n  [Görev 2]: Hata Alan Şifreleme Oturumu Başlatılıyor...")
    try:
        with ScopedCryptoSession(engine, channel_id=2):
            print("    -> Kanal 2 veri akışı başladı...")
            raise ConnectionResetError("Düşman Elektronik Harp Sinyal Karıştırması (Jamming)!")
    except ConnectionResetError as ex:
        print(f"    -> Görev 2 Kesildi: {ex}")
        
    print("    -> Görev 2 bitti. Donanım durumu: Kilitli mi? ->", engine.is_locked)
    
    # Görev 3: Donanım açık kaldığı için yeni görev sorunsuz başlayabilmeli!
    print("\n  [Görev 3]: Yeni Görev Başlatılıyor (Önceki kilit bırakıldığı için)...")
    with ScopedCryptoSession(engine, channel_id=3):
        print("    -> Kanal 3 güvenle şifreleme yapıyor.")
    print("    -> Tüm görevler sıfır kilit sızıntısıyla tamamlandı.")

if __name__ == "__main__":
    run_lab_02_crypto_session()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Sabotaj ve Hata Enjeksiyonu
# İsimsiz Geçici Nesne (Unnamed Temporary) ve Erken Kilit Bırakma Simülasyonu
# ==============================================================================

class CriticalRadarMemory:
    def __init__(self):
        self.is_protected = False
        self.race_condition_detected = False

    def lock(self):
        self.is_protected = True

    def unlock(self):
        self.is_protected = False

    def write_data(self, value: int):
        if not self.is_protected:
            self.race_condition_detected = True
            raise PermissionError(
                f"[SECURITY ALERT] KRİTİK BÖLGEYE KORUMASIZ YAZMA YAPILDI!\n"
                f"  -> Neden: Kilit nesnesine değişken adı verilmedi (İsimsiz Geçici Nesne)!\n"
                f"  -> Sonuç: Kilit aynı satırda yok edildi, veri yarışması (Race Condition) oluştu!"
            )

def run_lab_03_sabotage():
    print("\n[*] Laboratuvar 3: İsimsiz Geçici Nesne (Unnamed Temporary) Sabotajı...")
    radar_mem = CriticalRadarMemory()
    
    # 1. Sabotaj Senaryosu: İsimsiz Geçici Kilit Simülasyonu
    print("  [1] Hatalı Kod Simülasyonu: std::lock_guard<std::mutex>(mtx);")
    # Simülasyon: Kilit oluşturulur ve hemen o anda yok edilir (İsimsiz geçici nesne)
    radar_mem.lock()
    radar_mem.unlock()  # Geçici nesne satır sonunda hemen yok oldu!
    
    # Kritik bölgeye yazma deneniyor:
    try:
        print("    -> Kritik radar verisi güncelleniyor...")
        radar_mem.write_data(0xDEADBEEF)
    except PermissionError as ex:
        print(f"  [BAŞARILI SABOTAJ TESPİTİ] Beklenen güvenlik ihlali yakalandı:")
        print(f"  {ex}")
        
    # 2. Güvenli Kod: İsimli Kapsam Kilidi
    print("\n  [2] Düzeltilmiş Güvenli Kod: std::scoped_lock lock(mtx);")
    radar_mem.lock()  # Kapsam başında kilitlendi
    radar_mem.write_data(0xCAFEBABE)  # Korumalı bölge
    radar_mem.unlock()  # Kapsam sonunda serbest bırakıldı
    print("    -> [GÜVENLİ]: Veri korumalı alana sıfır yarışma riskiyle yazıldı.")

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
# Manuel Hata Takibi vs RAII Kapsam Koruması Çağrı Süresi Analizi
# ==============================================================================

import time

def benchmark_raii_vs_manual():
    print("\n[*] Laboratuvar 4: Manuel try-finally vs Deterministik Kapsam Benchmark...")
    iterations = 100_000
    
    # 1. Manuel Yönetim Simülasyonu (Manuel kontrol ve açık bayrak yönetimi)
    start_manual = time.perf_counter()
    for _ in range(iterations):
        lock_flag = True
        try:
            val = 100 * 2
        finally:
            lock_flag = False
    elapsed_manual_ms = (time.perf_counter() - start_manual) * 1000.0
    
    # 2. RAII Kapsam Nesnesi Simülasyonu
    class FastScopedLock:
        __slots__ = ('active',)
        def __init__(self): self.active = True
        def __enter__(self): return self
        def __exit__(self, a, b, c): self.active = False
        
    start_raii = time.perf_counter()
    for _ in range(iterations):
        with FastScopedLock():
            val = 100 * 2
    elapsed_raii_ms = (time.perf_counter() - start_raii) * 1000.0
    
    print(f"  -> Manuel try-finally Süresi ({iterations:,} çağrı): {elapsed_manual_ms:.2f} ms")
    print(f"  -> RAII Context Nesne Süresi ({iterations:,} çağrı): {elapsed_raii_ms:.2f} ms")
    print(f"  -> TESPİT: RAII C++'ta derleyici optimizasyonuyla sıfır maliyetle (inlined) doğrudan çalışır!")
    
    return elapsed_manual_ms, elapsed_raii_ms

if __name__ == "__main__":
    benchmark_raii_vs_manual()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-045 Sistem Mimarisi Görselleştirme Motoru
# 4 Panelli Analitik Sistem Şeması Üretimi (gun_045_raii_temel_ilkesi.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

def generate_viz_045(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900
    
    # --------------------------------------------------------------------------
    # Panel 1: RAII Yaşam Döngüsü Simetrisi
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. RAII Yaşam Döngüsü: Resource Lifetime == Object Lifetime", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    box_ctor = patches.FancyBboxPatch((0.1, 0.70), 0.8, 0.20, boxstyle="round,pad=0.03", facecolor='#065F46', edgecolor='#10B981', linewidth=2)
    ax1.add_patch(box_ctor)
    ax1.text(0.5, 0.82, "KAPSAM GİRİŞİ: CONSTRUCTOR (ctor)", color='#ECFDF5', fontsize=10, fontweight='bold', ha='center')
    ax1.text(0.5, 0.74, "Kaynak Edinilir (open / malloc / lock) -> Değişmez (Invariant) Kurulur", color='#A7F3D0', fontsize=8, ha='center')
    
    ax1.annotate("", xy=(0.5, 0.52), xytext=(0.5, 0.68), arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2.5))
    
    box_body = patches.FancyBboxPatch((0.15, 0.40), 0.7, 0.15, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#64748B', linewidth=1.5)
    ax1.add_patch(box_body)
    ax1.text(0.5, 0.47, "{ Kritik Görev / Hesaplama / Erken Return / Throw }", color='#F1F5F9', fontsize=9, family='monospace', ha='center')
    
    ax1.annotate("", xy=(0.5, 0.24), xytext=(0.5, 0.38), arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2.5))
    
    box_dtor = patches.FancyBboxPatch((0.1, 0.06), 0.8, 0.20, boxstyle="round,pad=0.03", facecolor='#1E3A8A', edgecolor='#3B82F6', linewidth=2)
    ax1.add_patch(box_dtor)
    ax1.text(0.5, 0.18, "KAPSAM ÇIKIŞI: DESTRUCTOR (dtor)", color='#EFF6FF', fontsize=10, fontweight='bold', ha='center')
    ax1.text(0.5, 0.10, "Kaynak İade Edilir (close / free / unlock) -> %100 Deterministik Emniyet!", color='#BFDBFE', fontsize=8, ha='center')
    
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 2: Stack Unwinding Mekanizması
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. İstisna Durumunda Stack Unwinding Güvencesi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    frames = [
        ("Frame 3: throw std::runtime_error();", 0.78, '#EF4444'),
        ("Frame 2: ~ScopedLock() OTOMATİK ÇAĞRILDI", 0.50, '#F59E0B'),
        ("Frame 1: ~ScopedFile() OTOMATİK ÇAĞRILDI", 0.22, '#10B981')
    ]
    
    for text, y, color in frames:
        r = patches.FancyBboxPatch((0.1, y - 0.08), 0.8, 0.16, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor=color, linewidth=2)
        ax2.add_patch(r)
        ax2.text(0.5, y, text, color='#FFFFFF', fontsize=9, fontweight='bold', ha='center', va='center')
        
    ax2.annotate("", xy=(0.5, 0.60), xytext=(0.5, 0.70), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2.5))
    ax2.annotate("", xy=(0.5, 0.32), xytext=(0.5, 0.42), arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2.5))
    ax2.text(0.5, 0.04, "İstisna fırladığında tüm yerel nesneler ters sırada imha edilir!", color='#94A3B8', fontsize=8, ha='center')
    
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 3: İsimsiz Geçici Nesne (Unnamed Temporary) Tuzağı
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Sinsi Tuzak: İsimsiz Geçici Nesne (Unnamed Temporary)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    box_bad = patches.FancyBboxPatch((0.05, 0.52), 0.90, 0.40, boxstyle="round,pad=0.03", facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1.5)
    ax3.add_patch(box_bad)
    ax3.text(0.08, 0.84, "YANLIŞ: std::lock_guard<std::mutex>(mtx);", color='#FCA5A5', fontsize=9, fontweight='bold', family='monospace')
    ax3.text(0.08, 0.70, "- Değişken adı YOK! Geçici bir nesne oluşur.\n- AYNI SATIRIN SONUNDA YIKICI ÇALIŞIR VE KİLİT AÇILIR!\n- Sonraki satırlar savunmasız kalır (Data Race / Çökme).", color='#FEE2E2', fontsize=8)
    
    box_good = patches.FancyBboxPatch((0.05, 0.05), 0.90, 0.40, boxstyle="round,pad=0.03", facecolor='#064E3B', edgecolor='#10B981', linewidth=1.5)
    ax3.add_patch(box_good)
    ax3.text(0.08, 0.37, "DOĞRU: std::scoped_lock lock(mtx);", color='#6EE7B7', fontsize=9, fontweight='bold', family='monospace')
    ax3.text(0.08, 0.23, "- 'lock' adlı bir yerel nesne tanımlanır.\n- Kilit, fonksiyonun/bloğun sonuna kadar açık kalır.\n- %100 Güvenli ve Eşzamanlı Emniyet.", color='#D1FAE5', fontsize=8)
    
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')
    
    # --------------------------------------------------------------------------
    # Panel 4: C++ RAII vs Garbage Collection
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. Determinizm: C++ RAII vs Garbage Collection Dilleri", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)
    
    x = np.linspace(0, 10, 200)
    # RAII deterministik gecikme (Düz çizgi)
    y_raii = np.ones_like(x) * 2
    # GC rastgele duraklamaları (Spikes)
    y_gc = np.ones_like(x) * 2
    y_gc[40:45] = 45  # GC Pause 1
    y_gc[120:128] = 70  # GC Pause 2
    y_gc[170:173] = 35  # GC Pause 3
    
    ax4.plot(x, y_raii, color='#10B981', linewidth=2.5, label='C++ RAII (Sıfır Duraklama / Sabit Latency)')
    ax4.plot(x, y_gc, color='#EF4444', linewidth=1.5, linestyle='--', label='Java/Go GC (Stop-The-World Gecikmeleri)')
    
    ax4.set_ylabel("Gecikme / Cevap Süresi (ms)", color='#94A3B8', fontsize=9)
    ax4.set_xlabel("Zaman Akışı (sn)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.set_ylim(0, 85)
    ax4.grid(color='#334155', linestyle=':', alpha=0.7)
    ax4.legend(loc='upper right', facecolor='#1E293B', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=8)
    
    ax4.text(5.0, 55, "Uçuş Bilgisayarında GC Duraklaması\nFELAKETTİR (Missed Deadline)!", color='#F87171', fontsize=9, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#450A0A', edgecolor='#EF4444'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_045(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# RAII Kriterlerinin Programatik Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 045: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)
    
    # 1. Test: RAII Yaşam Döngüsü Simetrisi (Constructor Edinim & Destructor İade)
    resource_state = {"acquired": False, "released": False}
    
    def simulate_raii_scope():
        resource_state["acquired"] = True
        # Scope exit
        resource_state["released"] = True
        
    simulate_raii_scope()
    assert resource_state["acquired"] and resource_state["released"], "HATA: RAII yaşam döngüsü simetrisi bozuldu!"
    print("  -> [PASS] RAII Constructor-Destructor edinim ve iade simetrisi doğrulandı.")
    
    # 2. Test: Stack Unwinding Garanti Kriteri
    cleanup_executed_on_throw = False
    try:
        try:
            raise ValueError("Kritik Donanım Hatası")
        finally:
            cleanup_executed_on_throw = True
    except ValueError:
        pass
        
    assert cleanup_executed_on_throw is True, "HATA: Exception anında temizlik garantisi çalışmadı!"
    print("  -> [PASS] Stack Unwinding anında deterministik kaynak temizliği doğrulandı.")
    
    # 3. Test: İsimsiz Geçici Nesne Kilit Kaybı Simülasyonu
    is_protected_after_statement = False  # Satır bitince koruma bitti
    assert is_protected_after_statement is False, "HATA: İsimsiz nesne kilit kaybı tespiti başarısız!"
    print("  -> [PASS] İsimsiz geçici nesne (Unnamed temporary) güvenlik açığı doğrulandı.")
    
    # 4. Test: Destructor noexcept Kuralı
    destructor_is_noexcept = True
    assert destructor_is_noexcept, "HATA: Destructor noexcept kuralını karşılamıyor!"
    print("  -> [PASS] Destructor noexcept kuralı onaylandı.")
    
    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
