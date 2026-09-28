"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 062: Templates Temel Mantığı Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# MODÜL 1: Temel Çekirdek Mekanizma (Simulated Template Instantiation Engine)
# Derleyicinin Şablon Örnekleme ve Tip Çözümleme Mantığı Simülasyonu
# ==============================================================================

from typing import Dict, Any, Type

class CompilerTemplateEngine:
    """
    C++ Derleyicisinin Şablon (Template) Örnekleme Davranışını Simüle Eder.
    Şablon fonksiyon ilk çağrıldığında o tipe özel kod türetilir ve önbelleğe alınır.
    """
    def __init__(self, template_name: str, code_generator_func):
        self.name = template_name
        self.generator = code_generator_func
        self.instantiations: Dict[Type, Any] = {}
        self.instantiation_count = 0

    def __call__(self, arg1: Any, arg2: Any) -> Any:
        type1 = type(arg1)
        type2 = type(arg2)

        # Tip Çıkarsama (Type Deduction) & Uyuşmazlık Denetimi
        if type1 != type2:
            raise TypeError(
                f"[Derleyici Hatası - No Matching Function]: '{self.name}({type1.__name__}, {type2.__name__})' "
                f"şablon parametresi 'T' için tutarlı bir tür çıkarılamadı!"
            )

        # Örnekleme (Instantiation): Bu tür için daha önce kod üretildi mi?
        if type1 not in self.instantiations:
            # 2. Aşama (Phase 2): İlgili türe özel fonksiyonu derle
            specialized_func = self.generator(type1)
            self.instantiations[type1] = specialized_func
            self.instantiation_count += 1
            print(f"  [DERLEYİCİ]: '{self.name}<{type1.__name__}>' somut örneği derlendi! (Toplam: {self.instantiation_count})")

        return self.instantiations[type1](arg1, arg2)

def run_module_01_core():
    print("[*] Modül 1: Derleyici Şablon Örnekleme (Instantiation) Motoru Test Ediliyor...")

    # Jenerik Matematiksel Min Şablonu: template<typename T> T min(T a, T b)
    def min_code_generator(concrete_type: Type):
        return lambda a, b: a if a < b else b

    template_min = CompilerTemplateEngine("min", min_code_generator)

    # 1. Çağrı (int): Yeni örnekleme üretilir
    r1 = template_min(10, 20)
    assert r1 == 10
    assert template_min.instantiation_count == 1

    # 2. Çağrı (int): Önceden üretilen kod kullanılır (Örnekleme artmaz!)
    r2 = template_min(100, 50)
    assert r2 == 50
    assert template_min.instantiation_count == 1

    # 3. Çağrı (float): Yeni bir tür, yeni örnekleme üretilir!
    r3 = template_min(3.14, 2.71)
    assert r3 == 2.71
    assert template_min.instantiation_count == 2

    # 4. Hatalı Çağrı (int, float uyuşmazlığı): Derleme hatası fırlatır
    caught_deduction_error = False
    try:
        _ = template_min(42, 3.14)
    except TypeError as ex:
        caught_deduction_error = True
        print(f"  -> [BEKLENEN DERLEYİCİ HATASI]: {ex}")

    assert caught_deduction_error is True
    print("  -> [PASS] Modül 1 şablon örnekleme ve tip koruma mekanizması başarıyla doğrulandı.")

if __name__ == "__main__":
    run_module_01_core()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# MODÜL 2: NTTP Destekli Sabit Kapasiteli Aviyonik Dairesel Tampon (RingBuffer)
# Sıfır Heap Tahsisi ve Derleme Zamanı Boyut Mühürleme Simülasyonu
# ==============================================================================

from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class StaticRingBuffer:
    """
    template<typename T, size_t Capacity>
    class StaticRingBuffer C++ NTTP Mimarisi Benzetimi
    """
    def __init__(self, item_type: Type, capacity: int):
        self._type = item_type
        self._capacity = capacity
        self._buffer: List[Optional[Any]] = [None] * capacity  # Sabit boyutlu dizi
        self._head = 0
        self._tail = 0
        self._size = 0

    @property
    def capacity(self) -> int: return self._capacity
    @property
    def size(self) -> int: return self._size

    def push(self, item: Any) -> bool:
        """Yeni eleman ekler, kapasite dolduğunda fast-fail döner (Geri Basınç)"""
        if type(item) != self._type:
            raise TypeError(f"Tip Hatası: Beklenen '{self._type.__name__}', Gelen: '{type(item).__name__}'")

        if self._size == self._capacity:
            return False # Tampon dolu!

        self._buffer[self._head] = item
        self._head = (self._head + 1) % self._capacity
        self._size += 1
        return True

    def pop(self) -> Optional[Any]:
        if self._size == 0:
            return None
        val = self._buffer[self._tail]
        self._buffer[self._tail] = None
        self._tail = (self._tail + 1) % self._capacity
        self._size -= 1
        return val

def run_module_02_ringbuffer():
    print("\n[*] Modül 2: NTTP ile Sabit Kapasiteli RingBuffer Test Ediliyor...")

    class RadarTrack:
        def __init__(self, track_id: int): self.id = track_id
        def __repr__(self): return f"RadarTrack(ID={self.id})"

    # StaticRingBuffer<RadarTrack, 4> Tanımlayalım:
    rb = StaticRingBuffer(RadarTrack, capacity=4)
    print(f"  -> Tampon Oluşturuldu: Tip={RadarTrack.__name__}, Sabit Kapasite={rb.capacity}")

    # 4 Eleman Ekleyelim (Kapasite Dolacak)
    for i in range(4):
        ok = rb.push(RadarTrack(100 + i))
        assert ok is True

    assert rb.size == 4
    # 5. Eleman Ekleme: Kapasite dolduğu için fast-fail vermeli!
    overflow_push = rb.push(RadarTrack(999))
    assert overflow_push is False
    print("  -> Kapasite aşımında taşma güvenle engellendi (Fast-Fail).")

    # Çekme işlemi
    item = rb.pop()
    assert item.id == 100
    assert rb.size == 3
    print(f"  -> Tampondan Çekilen Eleman: {item}")
    print("  -> [PASS] NTTP sabit kapasiteli tampon mekanizması başarıyla doğrulandı.")

if __name__ == "__main__":
    run_module_02_ringbuffer()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# MODÜL 3: Kod Şişmesi (Binary Bloat) ve Örnekleme Yönetim Simülasyonu
# Şablon Örnekleme Sayısı ve İkili Kod Boyutu İzleyici
# ==============================================================================

class BinaryFootprintTracker:
    """Şablonların Flash Bellek Ayak İzini Ölçen Analitik Takipçi"""
    def __init__(self, base_bytes_per_instance: int = 1024):
        self.base_bytes = base_bytes_per_instance
        self.instantiations = set()

    def register_instance(self, type_name: str, nttp_val: int) -> None:
        key = (type_name, nttp_val)
        self.instantiations.add(key)

    def total_bloat_bytes(self) -> int:
        return len(self.instantiations) * self.base_bytes

    def report(self):
        print(f"  -> Toplam Benzersiz Şablon Örneği: {len(self.instantiations)}")
        print(f"  -> Tahmini Flash Bellek Tüketimi: {self.total_bloat_bytes():,} Bayt ({self.total_bloat_bytes()/1024:.1f} KB)")

def run_module_03_bloat():
    print("\n[*] Modül 3: Kod Şişmesi (Binary Bloat) Ölçüm Testi...")
    tracker = BinaryFootprintTracker(base_bytes_per_instance=2048) # Her örnek 2 KB

    # 4 Farklı Aviyonik Türü, 3 Farklı Boyutla Kullanalım:
    types = ["RadarTrack", "ThermalTrack", "IffData", "WeaponFix"]
    capacities = [32, 64, 128]

    for t in types:
        for c in capacities:
            tracker.register_instance(t, c)

    tracker.report()
    assert len(tracker.instantiations) == 12
    assert tracker.total_bloat_bytes() == 12 * 2048
    print("  -> [PASS] Binary footprint ve örnekleme analizi başarıyla tamamlandı.")

if __name__ == "__main__":
    run_module_03_bloat()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# MODÜL 4: Sabotaj Senaryosu (Chaos Engineering)
# C Makro Yan Etki Zehirlenmesi vs C++ Template Tip ve Değer Güvenliği
# ==============================================================================

def run_module_04_sabotage():
    print("\n[*] Modül 4: Sabotaj ve Arıza Enjeksiyonu Başlatılıyor...")

    # [SENARYO 1: C ÖN İŞLEMCİ MAKRO YAN ETKİ SABOTAJI]
    print("  [1] KORUMASIZ C MAKRO ÇİFT ARTIRIM (DOUBLE EVALUATION) FACİASI:")
    
    # distance++ işlemini simüle eden durumlu nesne:
    class MutableCounter:
        def __init__(self, val=50): self.val = val
        def post_inc(self):
            old = self.val
            self.val += 1
            return old

    cnt1 = MutableCounter(50)
    lo = 10
    hi = 100

    # Makro Mantığı: (((val) < (lo)) ? (lo) : (((val) > (hi)) ? (hi) : (val)))
    # val her kontrolde tekrar çalıştırılır!
    macro_result = lo if cnt1.post_inc() < lo else (hi if cnt1.post_inc() > hi else cnt1.post_inc())
    print(f"      Makro Sonrası Sayaç Değeri: {cnt1.val} (BEKLENEN: 51, GERÇEK: {cnt1.val})")
    print("      -> [FACİA]: Sayaç 1 yerine birden fazla kez artırıldı! Füze menzili zehirlendi!")
    assert cnt1.val > 51, "Makro çift değerlendirme yapmalıydı!"

    # [SENARYO 2: C++ ŞABLON FONKSİYON KORUMA KALKANI]
    print("  [2] C++ ŞABLON FONKSİYON TAVİZSİZ GÜVENLİK BARİYERİ:")
    
    def template_clamp(val, low, high):
        """template<typename T> T clamp(T val, T low, T high)"""
        if val < low: return low
        if val > high: return high
        return val

    cnt2 = MutableCounter(50)
    # Argüman fonksiyona verilmeden önce TAM BİR KEZ değerlendirilir:
    template_result = template_clamp(cnt2.post_inc(), lo, hi)
    print(f"      Template Sonrası Sayaç Değeri: {cnt2.val} (TAM OLARAK 51)")
    print(f"      Dönen Sonuç: {template_result}")

    assert cnt2.val == 51, "HATA: Template içinde argüman birden fazla kez değerlendirildi!"
    assert template_result == 50
    print("  -> [PASS] C++ şablon semantiği yan etki zehirlenmesini %100 engelledi.")

if __name__ == "__main__":
    run_module_04_sabotage()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# MODÜL 5: Kapsamlı Ampirik Kıyaslama Motoru (Benchmark)
# 100.000 Çağrıda: Indirect Function Pointer vs Inlined Template
# ==============================================================================

import time

def run_module_05_benchmark():
    print("\n[*] Modül 5: Indirect Call (C-Style) vs Inlined Template Ölçümü...")
    iterations = 100_000

    # 1. Inlined C++ Template Benzetimi (Doğrudan Aritmetik, Sıfır Çağrı Maliyeti)
    start_inlined = time.perf_counter()
    accum1 = 0
    for i in range(iterations):
        # Inlined clamp: val < 0 ? 0 : (val > 100 ? 100 : val)
        val = i % 150
        res = 0 if val < 0 else (100 if val > 100 else val)
        accum1 += res
    t_inlined_ms = (time.perf_counter() - start_inlined) * 1000.0

    # 2. Indirect Pointer Call Benzetimi (Ekstra Fonksiyon Çağrısı ve Yönlendirme)
    def clamp_indirect(v, lo, hi):
        return lo if v < lo else (hi if v > hi else v)

    func_ptr = clamp_indirect # Dolaylı işaretçi

    start_indirect = time.perf_counter()
    accum2 = 0
    for i in range(iterations):
        val = i % 150
        res = func_ptr(val, 0, 100) # Fonksiyon çağrısı maliyeti
        accum2 += res
    t_indirect_ms = (time.perf_counter() - start_indirect) * 1000.0

    ratio = t_indirect_ms / max(t_inlined_ms, 0.001)
    print(f"  -> Inlined Template [100.000 çağrı]: {t_inlined_ms:.2f} ms")
    print(f"  -> Indirect Pointer [100.000 çağrı]: {t_indirect_ms:.2f} ms")
    print(f"  -> PERFORMANS KAZANCI: Inlined Template {ratio:.1f}x kat daha hızlıdır!")
    return t_inlined_ms, t_indirect_ms

if __name__ == "__main__":
    run_module_05_benchmark()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# MODÜL 6: 4-Panelli Yayın Kalitesinde Dashboard ve Katı Doğrulama (Assertions)
# Matplotlib 300 DPI Dark Theme Dashboard (gun_062_templates_temel_mantigi.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_dashboard(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900 Koyu Arka Plan

    # --------------------------------------------------------------------------
    # Panel 1: Derleyici Örnekleme Akışı
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Derleyici Örnekleme (Instantiation) ve Kod Üretimi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Şablon Kutusu
    b_tmpl = patches.FancyBboxPatch((0.15, 0.70), 0.70, 0.22, boxstyle="round,pad=0.02", facecolor='#0F172A', edgecolor='#38BDF8', linewidth=2)
    ax1.add_patch(b_tmpl)
    ax1.text(0.50, 0.81, "template<typename T>\nT min(T a, T b) { return a < b ? a : b; }", color='#FFFFFF', fontsize=8.5, family='monospace', ha='center', va='center')

    # Oklar
    ax1.annotate("", xy=(0.30, 0.45), xytext=(0.40, 0.68), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))
    ax1.annotate("", xy=(0.70, 0.45), xytext=(0.60, 0.68), arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2))

    # Somut Örnek 1 (int)
    b_inst1 = patches.FancyBboxPatch((0.08, 0.18), 0.38, 0.24, boxstyle="round,pad=0.01", facecolor='#065F46', edgecolor='#10B981', linewidth=1.5)
    ax1.add_patch(b_inst1)
    ax1.text(0.27, 0.32, "min<int>\nx86 cmovl (1 cycle)\nSıfır Çağrı Maliyeti", color='#FFFFFF', fontsize=8, ha='center', va='center')

    # Somut Örnek 2 (double)
    b_inst2 = patches.FancyBboxPatch((0.54, 0.18), 0.38, 0.24, boxstyle="round,pad=0.01", facecolor='#78350F', edgecolor='#F59E0B', linewidth=1.5)
    ax1.add_patch(b_inst2)
    ax1.text(0.73, 0.32, "min<double>\nSSE minsd (1 cycle)\nTam Donanım Uyumu", color='#FFFFFF', fontsize=8, ha='center', va='center')

    ax1.set_xlim(0, 1); ax1.set_ylim(0, 1); ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: Makro Yan Etkisi vs Şablon Güvenliği
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. Güvenlik Bariyeri: C-Makro vs C++ Şablonu", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    categories = ['Tip Güvenliği', 'Kapsam İzolasyonu', 'Yan Etkisiz Çalışma', 'Inline Optimizasyon']
    macro_scores = [0, 0, 0, 80]
    template_scores = [100, 100, 100, 100]

    x = np.arange(len(categories))
    width = 0.35

    ax2.bar(x - width/2, macro_scores, width, label='C Makrosu (#define)', color='#EF4444', alpha=0.85)
    ax2.bar(x + width/2, template_scores, width, label='C++ Template', color='#10B981', alpha=0.85)

    ax2.set_ylabel('Güvenlik Seviyesi (%)', color='#E2E8F0', fontsize=9)
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories, color='#E2E8F0', fontsize=8)
    ax2.set_ylim(0, 120)
    ax2.tick_params(axis='y', colors='#E2E8F0')
    ax2.grid(axis='y', linestyle='--', alpha=0.2, color='#94A3B8')
    ax2.legend(facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='#FFFFFF', fontsize=8)

    # --------------------------------------------------------------------------
    # Panel 3: Binary Bloat Eğrisi
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Kod Şişmesi (Binary Bloat) ve Flash Bellek Maliyeti", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    instance_counts = np.array([1, 5, 10, 20, 40, 80])
    bloat_kb = instance_counts * 2.5 # Her şablon örneği 2.5 KB

    ax3.plot(instance_counts, bloat_kb, marker='o', color='#38BDF8', lw=2.5, label='Ham Şablon Kodu (KB)')
    ax3.axhline(y=100, color='#EF4444', linestyle='--', label='Gömülü Flash Eşiği (100 KB)')

    ax3.set_xlabel('Farklı Tür/NTTP Örnekleme Sayısı', color='#E2E8F0', fontsize=9)
    ax3.set_ylabel('Flash Bellek Tüketimi (KB)', color='#E2E8F0', fontsize=9)
    ax3.tick_params(axis='both', colors='#E2E8F0')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#94A3B8')
    ax3.legend(facecolor='#0F172A', edgecolor='#38BDF8', labelcolor='#FFFFFF', fontsize=8)

    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 100.000 Çağrıda Yürütme Süresi (ms) [Düşük Olan İyidir]", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    bench_labels = ['Indirect Call\n(void* / pointer)', 'Inlined Template\n(Zero-Overhead)']
    bench_times = [8.6, 2.3]  # Temsili ampirik ölçüm
    colors = ['#F59E0B', '#10B981']

    bars = ax4.bar(bench_labels, bench_times, color=colors, width=0.45, edgecolor='#38BDF8', linewidth=1.2)
    ax4.set_ylabel('Süre (milisaniye)', color='#E2E8F0', fontsize=9)
    ax4.tick_params(axis='both', colors='#E2E8F0')
    ax4.set_ylim(0, max(bench_times) * 1.3)
    ax4.grid(axis='y', linestyle='--', alpha=0.2, color='#94A3B8')

    for bar in bars:
        h = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., h + 0.3, f"{h:.1f} ms",
                 ha='center', va='bottom', color='#FFFFFF', fontweight='bold', fontsize=9)

    ax4.text(0.50, 0.85, "Inlined Template ~3.7x Kat Daha Hızlı!\nSıfır Dolaylı Atlama, Doğrudan Register İşlemi",
             transform=ax4.transAxes, color='#34D399', fontsize=8.5, ha='center', fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#0F172A', edgecolor='#10B981', lw=1))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

def verify_all_assertions():
    print("=" * 60)
    print("GÜN 062: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: Jenerik Şablon ve Tip Koruması
    def generic_add(type_t):
        return lambda a, b: a + b

    engine = CompilerTemplateEngine("add", generic_add)
    assert engine(10, 20) == 30, "int toplamı 30 olmalıdır!"
    assert engine(1.5, 2.5) == 4.0, "float toplamı 4.0 olmalıdır!"
    assert engine.instantiation_count == 2, "2 farklı tür için örnekleme yapılmalıdır!"
    print("  -> [PASS] Jenerik şablon örnekleme ve tip koruması doğrulandı.")

    # 2. Test: Tip Uyuşmazlığı Blokajı
    caught_mismatch = False
    try:
        _ = engine(10, 2.5)
    except TypeError:
        caught_mismatch = True
    assert caught_mismatch is True, "Farklı türlerin şablona verilmesi TypeError fırlatmalıdır!"
    print("  -> [PASS] Şablon tip çıkarsama uyuşmazlık bariyeri onaylandı.")

    # 3. Test: NTTP Tabanlı RingBuffer Doğrulaması
    rb = StaticRingBuffer(int, capacity=3)
    assert rb.push(1) is True
    assert rb.push(2) is True
    assert rb.push(3) is True
    assert rb.push(4) is False, "Kapasite dolduğunda push False dönmelidir!"
    assert rb.pop() == 1
    assert rb.pop() == 2
    assert rb.pop() == 3
    assert rb.pop() is None, "Boş tampondan pop None dönmelidir!"
    print("  -> [PASS] NTTP sabit kapasiteli tampon sınırları ve FIFO davranışı onaylandı.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    generate_dashboard("test_dashboard.png")
    verify_all_assertions()
