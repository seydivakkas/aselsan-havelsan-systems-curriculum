# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 4 (CODE 1): ELF Bağımlılık Ağacı ve ldd Simülatörü
Özyinelemeli DT_NEEDED Tarayıcısı, Eksik Kütüphane Tespiti ve Diamond Dependency
"""

from typing import Dict, List, Set, Tuple, Optional

class SimulatedElfBinary:
    """ELF çalıştırılabilir dosya veya paylaşılan kütüphane simülasyonu."""
    def __init__(self, name: str, needed: List[str], provides_symbols: List[str]):
        self.name = name
        self.needed = needed # DT_NEEDED listesi
        self.provides_symbols = provides_symbols

class DependencyTreeResolver:
    """Linux ld.so bağımlılık çözümleme motorunun simülatörü."""
    
    def __init__(self, system_libraries: Dict[str, SimulatedElfBinary]):
        self.system_libraries = system_libraries

    def simulate_ldd(self, target_binary: SimulatedElfBinary) -> List[Tuple[str, str, Optional[int]]]:
        """ldd çıktısını özyinelemeli olarak üretir: (lib_name, path_or_status, base_addr)."""
        results = []
        visited: Set[str] = set()
        base_address = 0x7FFF0000
        
        queue = list(target_binary.needed)
        while queue:
            lib_name = queue.pop(0)
            if lib_name in visited:
                continue
            visited.add(lib_name)
            
            if lib_name in self.system_libraries:
                lib_obj = self.system_libraries[lib_name]
                results.append((lib_name, f"/lib64/{lib_name}", base_address))
                base_address += 0x10000
                # Geçişli (Transitive) bağımlılıkları kuyruğa ekle
                for child in lib_obj.needed:
                    if child not in visited:
                        queue.append(child)
            else:
                # Eksik kütüphane! (not found)
                results.append((lib_name, "not found", None))
                
        return results

if __name__ == "__main__":
    # Sistem Kütüphaneleri Havuzu
    repo = {
        "libdsp.so.1": SimulatedElfBinary("libdsp.so.1", ["libm.so.6", "libc.so.6"], ["fft"]),
        "libm.so.6": SimulatedElfBinary("libm.so.6", ["libc.so.6"], ["sin", "cos"]),
        "libc.so.6": SimulatedElfBinary("libc.so.6", [], ["printf", "malloc"])
    }
    
    # 1. Başarılı İkili Dosya
    app_ok = SimulatedElfBinary("radar_app", ["libdsp.so.1"], ["main"])
    resolver = DependencyTreeResolver(repo)
    
    print("=== [ldd ./radar_app SİMÜLASYONU (BAŞARILI)] ===")
    for name, path, addr in resolver.simulate_ldd(app_ok):
        addr_str = f"({hex(addr)})" if addr else ""
        print(f"    {name:15s} => {path:25s} {addr_str}")

    # 2. Eksik Kütüphaneli İkili Dosya
    app_broken = SimulatedElfBinary("broken_app", ["libdsp.so.1", "libcuda_aselsan.so.5"], ["main"])
    print("\n=== [ldd ./broken_app SİMÜLASYONU (EKSİK KÜTÜPHANE)] ===")
    for name, path, addr in resolver.simulate_ldd(app_broken):
        addr_str = f"({hex(addr)})" if addr else ""
        print(f"    {name:25s} => {path:25s} {addr_str}")


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Python ile Güvenli Statik ELF Analizörü
İkili Dosyayı Çalıştırmadan DT_NEEDED ve .interp Başlıklarını Ayrıştırma
"""

from typing import Dict, List, Any

class SafeStaticElfParser:
    """ELF başlıklarını çalıştırmadan statik olarak denetleyen güvenlik motoru."""
    
    @staticmethod
    def inspect_binary_metadata(simulated_elf_header: Dict[str, Any]) -> Dict[str, Any]:
        """Güvensiz ldd çalıştırmak yerine ELF başlıklarını statik inceler."""
        interpreter = simulated_elf_header.get("interp", "")
        needed = simulated_elf_header.get("needed", [])
        rpath = simulated_elf_header.get("rpath", "")
        runpath = simulated_elf_header.get("runpath", "")
        
        # Güvenlik Tehdit Değerlendirmesi:
        # Eğer interpreter şüpheli bir dizindeyse (örn: /tmp veya yerel dizin) alarm ver!
        is_suspicious_interp = interpreter.startswith("/tmp") or "./" in interpreter
        
        return {
            "interpreter": interpreter,
            "is_suspicious_interp": is_suspicious_interp,
            "needed_libraries": needed,
            "rpath": rpath,
            "runpath": runpath,
            "uses_origin": "$ORIGIN" in (rpath + runpath)
        }

if __name__ == "__main__":
    # Test 1: Güvenli Standart Aviyonik İkili Dosya
    clean_elf = {
        "interp": "/lib64/ld-linux-x86-64.so.2",
        "needed": ["libdsp.so.1", "libc.so.6"],
        "rpath": "$ORIGIN/../lib",
        "runpath": ""
    }
    res1 = SafeStaticElfParser.inspect_binary_metadata(clean_elf)
    print("=== [STATİK GÜVENLİ ELF ANALİZİ: TEMİZ DOSYA] ===")
    print(f"Interpreter : {res1['interpreter']}")
    print(f"Şüpheli mi? : {res1['is_suspicious_interp']}")
    print(f"Bağımlılık  : {res1['needed_libraries']}")
    print(f"$ORIGIN var : {res1['uses_origin']}")

    # Test 2: Saldırgan Tarafından Manipüle Edilmiş Zararlı ELF
    malicious_elf = {
        "interp": "/tmp/evil_loader.so",
        "needed": ["libc.so.6"],
        "rpath": "",
        "runpath": ""
    }
    res2 = SafeStaticElfParser.inspect_binary_metadata(malicious_elf)
    print("\n=== [STATİK GÜVENLİ ELF ANALİZİ: ZARARLI TUZAK DOSYA] ===")
    print(f"Interpreter : {res2['interpreter']}")
    print(f"Şüpheli mi? : {res2['is_suspicious_interp']} (ldd ÇALIŞTIRILSAYDI ZARARLI ÇALIŞACAKTI!)")


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Sabotaj Laboratuvarı: glibc Sürüm Çatışması
GLIBC_X.XX not found Hatası ve Statik Bağlama ile Savunma Simülatörü
"""

from typing import Dict, List, Tuple

class GlibcVersionSabotageLab:
    """Eski hedef sistemde yeni glibc ikilisi çalıştırma krizini modeller."""
    
    @staticmethod
    def simulate_version_mismatch() -> Tuple[bool, str]:
        # Geliştirme makinesi glibc 2.38 kullanıyor, hedef radar donanımı glibc 2.28
        target_system_glibc_versions = {"GLIBC_2.17", "GLIBC_2.25", "GLIBC_2.28"}
        binary_required_symbols = {
            "printf": "GLIBC_2.17",
            "pthread_create": "GLIBC_2.34" # Yeni sürüm gerektiriyor!
        }
        
        missing_versions = []
        for sym, req_ver in binary_required_symbols.items():
            if req_ver not in target_system_glibc_versions:
                missing_versions.append(f"{sym}@@{req_ver}")
                
        if missing_versions:
            return True, f"FATAL ERROR: /lib64/libc.so.6: version `GLIBC_2.34' not found (Eksik: {missing_versions})"
        return False, "Program başarıyla yüklendi."

    @staticmethod
    def simulate_static_binary_solution() -> Tuple[bool, str]:
        """-static bayrağı ile tüm glibc kodunun binary içine gömülmesi."""
        # Statik bağlamada DT_NEEDED boştur! Kütüphane aranmaz.
        dt_needed = []
        is_hermetic = len(dt_needed) == 0
        return is_hermetic, "BAŞARILI: Statik ikili dosya (Hermetic Binary)! Sistem glibc sürümünden %100 bağımsız."

if __name__ == "__main__":
    print("=== [GLIBC SÜRÜM ÇATIŞMASI VE ÇÖZÜM LABORATUVARI] ===")
    mismatch, err = GlibcVersionSabotageLab.simulate_version_mismatch()
    print(f"[*] Dinamik İkili Sonucu : {err}")
    
    hermetic, fix = GlibcVersionSabotageLab.simulate_static_binary_solution()
    print(f"[*] Statik Çözüm Sonucu   : {fix}")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Diamond Dependency Simülatörü
Sürüm Çakışması, İlk Yüklenen Kazanır (First-Wins) Kuralı ve Çöküş Tespiti
"""

from typing import Dict, List, Tuple

class DiamondDependencyLab:
    """Aynı isimli kütüphanenin iki farklı sürümünün yüklenmeye çalışılmasını modeller."""
    
    @staticmethod
    def simulate_diamond_conflict() -> Tuple[str, bool, str]:
        # Süreç adres uzayındaki yüklü kütüphaneler tablosu
        loaded_libs = {}
        
        # 1. libradar.so yüklenir -> libmath.so (v1.0) talep eder
        loaded_libs["libmath.so"] = "v1.0_OLD_ABI"
        
        # 2. libsensor.so yüklenir -> libmath.so (v2.0) talep eder
        # Linux dinamik bağlayıcı kuralı: Aynı dosya adı zaten bellekteyse ikinciyi yüklemez!
        active_version = loaded_libs["libmath.so"]
        
        # libsensor v2.0 içindeki 'fast_inv_sqrt' fonksiyonunu bekliyor
        v1_symbols = {"sin", "cos", "sqrt"}
        v2_symbols = {"sin", "cos", "sqrt", "fast_inv_sqrt"}
        
        # libsensor çağrı yapıyor:
        required_sym = "fast_inv_sqrt"
        has_symbol = required_sym in v1_symbols
        
        if not has_symbol:
            return active_version, False, f"SIGSEGV: undefined symbol '{required_sym}'! libsensor v2.0 beklerken v1.0 yüklendi."
        return active_version, True, "Çağrı başarılı."

if __name__ == "__main__":
    ver, ok, msg = DiamondDependencyLab.simulate_diamond_conflict()
    print("=== [DIAMOND DEPENDENCY SÜRÜM ÇAKIŞMASI TESTİ] ===")
    print(f"[*] Bellekteki Aktif Sürüm : {ver}")
    print(f"[*] Çağrı Sonucu           : {msg}")


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Statik vs Dinamik İkili Dosya Boyut ve Yükleme Benchmark'ı
Disk Ayak İzi, RAM Tüketimi ve Başlatma Süresi Mikro-Kıyaslaması
"""

import time
from typing import Dict

def run_binary_footprint_benchmark() -> Dict[str, Any]:
    """Statik vs Dinamik ikili dosyaların temel sistem metriklerini kıyaslar."""
    
    # 1. Disk Boyutu (KB)
    dynamic_disk_kb = 85.0   # Sadece kullanıcı kodu
    static_disk_kb = 2400.0  # glibc + libstdc++ + pthread gömülü
    
    # 2. 10 Adet Süreç Çalıştırıldığında Fiziksel RAM Tüketimi (KB)
    # Dinamik: Kütüphane kodu (2000 KB) bellekte 1 kopyadır, süreçler sadece özel veri (100 KB) tutar.
    dynamic_total_ram_kb = 2000.0 + (10 * 100.0) # 3000 KB
    # Statik: Her süreç 2400 KB kodun tamamını kendi belleğine alır!
    static_total_ram_kb = 10 * (2400.0 + 100.0)  # 25000 KB
    
    # 3. Yükleme ve Başlatma Süresi Simülasyonu (Dinamik bağlayıcı çözme maliyeti)
    t0 = time.perf_counter()
    for _ in range(20000):
        # Statik: Doğrudan entry_point'e atlama
        pass
    t_static_start = time.perf_counter() - t0

    t1 = time.perf_counter()
    for _ in range(20000):
        # Dinamik: 10 kütüphane için string karşılaştırma ve GOT doldurma
        for _ in range(10):
            hash("libc.so.6")
    t_dynamic_start = time.perf_counter() - t1

    return {
        "dynamic_disk_kb": dynamic_disk_kb,
        "static_disk_kb": static_disk_kb,
        "dynamic_ram_10_procs_kb": dynamic_total_ram_kb,
        "static_ram_10_procs_kb": static_total_ram_kb,
        "t_static_start_ms": t_static_start * 1000,
        "t_dynamic_start_ms": t_dynamic_start * 1000,
        "ram_savings_ratio": static_total_ram_kb / dynamic_total_ram_kb
    }

if __name__ == "__main__":
    res = run_binary_footprint_benchmark()
    print("=== [STATİK VS DİNAMİK İKİLİ DOSYA METRİKLERİ] ===")
    print(f"Disk Boyutu     -> Dinamik: {res['dynamic_disk_kb']} KB | Statik: {res['static_disk_kb']} KB")
    print(f"10 Süreç RAM'i  -> Dinamik: {res['dynamic_ram_10_procs_kb']:,} KB | Statik: {res['static_ram_10_procs_kb']:,} KB")
    print(f"[*] Dinamik Bellek Tasarrufu: {res['ram_savings_ratio']:.2f}x Kat Daha Az RAM!")
    print(f"Başlatma Süresi -> Dinamik: {res['t_dynamic_start_ms']:.3f} ms | Statik: {res['t_static_start_ms']:.3f} ms")


# -*- coding: utf-8 -*-
"""
HÜCRE 22 (CODE 6): 4-Panelli Görselleştirme Paneli ve Katı Doğrulama Testleri
Bağımlılık Ağacı, RAM/Disk Takası, Arama Önceliği ve Güvenlik Matrisi
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_097_ldd_ve_runtime_dependency.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    """4-panelli, koyu tema, 300 DPI kurumsal sistem mimarisi paneli üretir."""
    
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    accent_blue = '#38BDF8'
    accent_amber = '#F59E0B'
    accent_green = '#10B981'
    accent_red = '#EF4444'
    text_color = '#F8FAFC'

    # PANEL 1: Geçişli (Transitive) Bağımlılık Ağacı
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("ELF Bağımlılık Ağacı: Doğrudan vs Geçişli Kütüphaneler", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    nodes = [
        ("radar_app (İkili Dosya)", 0.5, 0.85, accent_blue),
        ("libdsp.so.1 (Doğrudan)", 0.3, 0.55, accent_amber),
        ("libnetwork.so (Doğrudan)", 0.7, 0.55, accent_amber),
        ("libm.so.6 (Geçişli)", 0.2, 0.20, accent_green),
        ("libc.so.6 (Temel)", 0.5, 0.20, '#94A3B8'),
        ("libcrypto.so (Geçişli)", 0.8, 0.20, accent_green)
    ]
    for text, x, y, col in nodes:
        ax1.text(x, y, text, ha='center', va='center', color=text_color, fontsize=8, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor=col, linewidth=2))

    ax1.annotate("", xy=(0.35, 0.62), xytext=(0.45, 0.80), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax1.annotate("", xy=(0.65, 0.62), xytext=(0.55, 0.80), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax1.annotate("", xy=(0.25, 0.28), xytext=(0.30, 0.48), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))
    ax1.annotate("", xy=(0.45, 0.28), xytext=(0.35, 0.48), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=2))
    ax1.annotate("", xy=(0.75, 0.28), xytext=(0.70, 0.48), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))

    ax1.set_xlim(0, 1.0)
    ax1.set_ylim(0, 1.0)
    ax1.axis('off')

    # PANEL 2: Statik vs Dinamik RAM ve Disk Tüketimi
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("Mimari Takas: Disk Boyutu vs 10 Süreç RAM Tüketimi (MB)", fontsize=12, fontweight='bold', color=accent_amber, pad=12)
    
    cats = ["Disk Boyutu (Tek Dosya)", "10 Süreç Toplam RAM"]
    dyn_vals = [0.085, 3.0]
    stat_vals = [2.4, 25.0]
    
    x = np.arange(len(cats))
    width = 0.35
    
    ax2.bar(x - width/2, dyn_vals, width, label='Dinamik (.so)', color=accent_blue, alpha=0.9)
    ax2.bar(x + width/2, stat_vals, width, label='Statik (-static)', color=accent_red, alpha=0.9)
    
    ax2.set_ylabel("Boyut (MB)", fontsize=10, color=text_color)
    ax2.set_xticks(x)
    ax2.set_xticklabels(cats, fontsize=9, color=text_color)
    ax2.legend(facecolor='#0F172A', edgecolor='#334155', fontsize=8)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#475569')

    # PANEL 3: glibc ve Diamond Bağımlılık Hata Oranları
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("Dağıtım Hataları Dağılımı ve Risk Dereceleri", fontsize=12, fontweight='bold', color=accent_green, pad=12)
    
    errors = ["GLIBC Version Mismatch", "Library Not Found", "Diamond ABI Crash", "ldd Interpreter Exploit"]
    impact = [92, 88, 85, 99]
    
    bars3 = ax3.barh(errors, impact, color=[accent_red, accent_amber, accent_blue, accent_red], height=0.55)
    ax3.set_xlabel("Kritiklik Skoru (%)", fontsize=10, color=text_color)
    ax3.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars3:
        ax3.text(bar.get_width() + 1.0, bar.get_y() + bar.get_height()/2, f"%{int(bar.get_width())}",
                 va='center', ha='left', color=text_color, fontsize=9, fontweight='bold')

    # PANEL 4: Güvenli Dağıtım Yöntemleri Karşılaştırması
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("Dağıtım İzolasyon Seviyeleri ($ORIGIN vs Statik)", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    methods = ["Sistem /lib64 (Kırılgan)", "LD_LIBRARY_PATH (Geçici)", "$ORIGIN RPATH (Hermetik)", "Full Static (İzole)"]
    portability_scores = [30, 50, 90, 100]
    
    bars4 = ax4.bar(methods, portability_scores, color=['#94A3B8', accent_amber, accent_blue, accent_green], width=0.5)
    ax4.set_ylabel("Taşınabilirlik / Güvenlik Skoru", fontsize=10, color=text_color)
    ax4.set_ylim(0, 115)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars4:
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"{int(bar.get_height())}",
                 ha='center', va='bottom', color=text_color, fontsize=9, fontweight='bold')

    plt.tight_layout()
    output_dir = os.path.dirname(os.path.abspath(output_png_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    plt.savefig(output_png_path, facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_png_path}")

def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Sistem varsayımlarını ve mimari sınırları doğrulayan katı testler."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")
    
    # 1. Dashboard Varlık Kontrolü
    assert os.path.exists(png_path), f"HATA: Dashboard görseli üretilemedi: {png_path}"
    assert os.path.getsize(png_path) > 100_000, "HATA: Dashboard görsel boyutu yetersiz!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {os.path.getsize(png_path):,} bayt.")

    # 2. ldd Bağımlılık Ağacı Çözümleme Doğrulaması
    repo_test = {
        "liba.so": SimulatedElfBinary("liba.so", ["libb.so"], []),
        "libb.so": SimulatedElfBinary("libb.so", [], [])
    }
    app = SimulatedElfBinary("app", ["liba.so"], [])
    resolver = DependencyTreeResolver(repo_test)
    resolved = resolver.simulate_ldd(app)
    lib_names = [r[0] for r in resolved]
    assert "liba.so" in lib_names, "HATA: Doğrudan bağımlılık çözümlenmelidir!"
    assert "libb.so" in lib_names, "HATA: Geçişli bağımlılık çözümlenmelidir!"
    print("  [+] Geçişli (Transitive) Bağımlılık Ağacı Doğrulandı.")

    # 3. Şüpheli Interpreter Tespiti
    bad_elf = {"interp": "/tmp/hack.so", "needed": []}
    res_bad = SafeStaticElfParser.inspect_binary_metadata(bad_elf)
    assert res_bad["is_suspicious_interp"] is True, "HATA: /tmp içindeki interpreter şüpheli bulunmalıdır!"
    print("  [+] Statik ELF Şüpheli Interpreter Güvenlik Kontrolü Doğrulandı.")

    # 4. glibc Sürüm Çakışması Doğrulaması
    mismatch, _ = GlibcVersionSabotageLab.simulate_version_mismatch()
    assert mismatch is True, "HATA: Hedef sistemde olmayan GLIBC sürümü hata vermelidir!"
    print("  [+] glibc Sürüm Çakışması (GLIBC_X.XX not found) Doğrulandı.")

    # 5. Diamond Dependency Çöküş Doğrulaması
    _, ok, _ = DiamondDependencyLab.simulate_diamond_conflict()
    assert ok is False, "HATA: Diamond bağımlılık ABI uyuşmazlığında çöküş yakalanmalıdır!"
    print("  [+] Diamond Dependency ve Sembol Uyuşmazlığı Doğrulandı.")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
