# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 4 (CODE 1): Süreç Çevre Değişkeni ve Yığın (Stack) Bellek Simülatörü
char **environ Düzeni, getenv/setenv/putenv Davranışı ve execve Kalıtımı
"""

from typing import Dict, List, Optional, Tuple

class SimulatedProcessEnvironment:
    """Linux süreç bellek yığını ve char **environ mekanizmasının simülatörü."""
    
    def __init__(self, initial_env: Optional[Dict[str, str]] = None):
        # Yığın tepesindeki ham string depolaması: Adres -> "KEY=VALUE\0"
        self.memory_store: Dict[int, str] = {}
        # char **environ: Bellek adreslerinin sıralı listesi (Son eleman 0 / NULL)
        self.environ_ptrs: List[int] = []
        self.next_address = 0x7FFF0010
        self.stack_active_frames: List[int] = [] # Geçici stack adresleri
        
        if initial_env:
            for k, v in initial_env.items():
                self.setenv(k, v, overwrite=1)

    def getenv(self, name: str) -> Optional[str]:
        """getenv(name): environ dizisini baştan sona doğrusal arar O(N)."""
        prefix = f"{name}="
        for ptr in self.environ_ptrs:
            if ptr == 0:  # NULL sonlandırıcı
                break
            entry = self.memory_store.get(ptr, "")
            if entry.startswith(prefix):
                return entry[len(prefix):]
        return None

    def setenv(self, name: str, value: str, overwrite: int = 1) -> int:
        """setenv: Güvenli heap tahsisi ile kopyalama yapar."""
        if not name or "=" in name:
            return -1
        existing_val = self.getenv(name)
        if existing_val is not None and not overwrite:
            return 0
            
        # Eğer zaten varsa eski adresi güncelle
        prefix = f"{name}="
        entry_str = f"{name}={value}"
        for i, ptr in enumerate(self.environ_ptrs):
            if ptr != 0 and self.memory_store.get(ptr, "").startswith(prefix):
                # Mevcut kaydı güncelle (yeni bellek tahsis et)
                addr = self.next_address
                self.next_address += len(entry_str) + 1
                self.memory_store[addr] = entry_str
                self.environ_ptrs[i] = addr
                return 0
                
        # Yeni değişken: Yeni adres al ve environ'a ekle
        addr = self.next_address
        self.next_address += len(entry_str) + 1
        self.memory_store[addr] = entry_str
        self.environ_ptrs.append(addr)
        return 0

    def putenv_vulnerable(self, raw_string: str, is_on_stack: bool = True) -> int:
        """putenv: Kopyalamadan doğrudan verilen adresi bağlar (Tuzak simülasyonu)."""
        addr = self.next_address
        self.next_address += len(raw_string) + 1
        self.memory_store[addr] = raw_string
        if is_on_stack:
            self.stack_active_frames.append(addr)
        self.environ_ptrs.append(addr)
        return 0

    def unwind_stack_frame(self):
        """Fonksiyon sonlandığında yerel yığın değişkenlerini bozar/temizler."""
        for addr in self.stack_active_frames:
            # Bellek çöp değerle (garbage) ezildi!
            self.memory_store[addr] = "GARBAGE_CORRUPTED_STACK_DATA_0xDEADBEEF"
        self.stack_active_frames.clear()

    def generate_proc_environ_bytes(self) -> bytes:
        """Linux /proc/PID/environ NUL-ayraçlı ham bayt akışı üretir."""
        raw_bytes = bytearray()
        for ptr in self.environ_ptrs:
            if ptr != 0 and ptr in self.memory_store:
                raw_bytes.extend(self.memory_store[ptr].encode("utf-8"))
                raw_bytes.append(0) # '\0' ayracı
        return bytes(raw_bytes)

if __name__ == "__main__":
    proc_env = SimulatedProcessEnvironment({
        "PATH": "/usr/bin:/bin",
        "USER": "mission_operator",
        "RADAR_MODE": "SEARCH"
    })
    
    print("=== [/proc/PID/environ SIMÜLASYONU] ===")
    raw_env = proc_env.generate_proc_environ_bytes()
    print(f"Ham Çıktı (NUL ayrılmış): {raw_env.replace(b'\\x00', b' [NUL] ')}")
    print(f"getenv('RADAR_MODE')     : {proc_env.getenv('RADAR_MODE')}")


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Python ile Üretim Seviyesi CascadingConfigManager Simülatörü
CLI > ENV > FILE > DEFAULTS Kaskat Öncelik Birleştirici ve Tip Güvenli Erişim
"""

from typing import Dict, Any, Optional, Tuple

class CascadingConfigManager:
    """4-Kademeli Öncelik Hiyerarşisini işleten savunma konfigürasyon motoru."""
    
    SOURCE_PRIORITY = {
        "CLI": 4,      # En yüksek
        "ENV": 3,
        "FILE": 2,
        "DEFAULT": 1   # En düşük
    }
    
    def __init__(self):
        # key -> (value, source_name)
        self.entries: Dict[str, Tuple[Any, str]] = {}

    def set(self, key: str, value: Any, source: str) -> bool:
        """Yeni değeri ancak önceliği mevcut kaynaktan yüksek veya eşitse kaydeder."""
        if source not in self.SOURCE_PRIORITY:
            raise ValueError(f"Geçersiz kaynak: {source}")
            
        if key in self.entries:
            curr_val, curr_src = self.entries[key]
            curr_prio = self.SOURCE_PRIORITY[curr_src]
            new_prio = self.SOURCE_PRIORITY[source]
            
            # Eğer yeni kaynak önceliği düşükse reddet
            if new_prio < curr_prio:
                return False
                
        self.entries[key] = (value, source)
        return True

    def get_string(self, key: str, fallback: str = "") -> str:
        if key in self.entries:
            return str(self.entries[key][0])
        return fallback

    def get_int(self, key: str, fallback: int = 0) -> int:
        val = self.get_string(key)
        try:
            return int(val)
        except (ValueError, TypeError):
            return fallback

    def get_source(self, key: str) -> Optional[str]:
        if key in self.entries:
            return self.entries[key][1]
        return None

if __name__ == "__main__":
    cfg = CascadingConfigManager()
    
    # 1. Kod İçi Varsayılanlar
    cfg.set("radar_port", 8080, "DEFAULT")
    cfg.set("radar_mode", "STANDBY", "DEFAULT")
    cfg.set("frequency_mhz", 9400, "DEFAULT")
    
    # 2. Dosyadan Yükleme
    cfg.set("radar_mode", "SEARCH", "FILE")
    cfg.set("frequency_mhz", 9600, "FILE")
    
    # 3. Ortam Değişkeni ile Ezme (ENV)
    cfg.set("radar_mode", "TRACK_TACTICAL", "ENV")
    
    # 4. CLI ile Ezme (En yüksek öncelik)
    cfg.set("radar_port", 9090, "CLI")
    
    # 5. Düşük öncelikli kaynağın ezmeye çalışması (Reddedilmeli!)
    rejected = cfg.set("radar_port", 5000, "FILE")
    
    print("=== [KASKAT KONFİGÜRASYON BİRLEŞTİRME SONUÇLARI] ===")
    for k in ["radar_port", "radar_mode", "frequency_mhz"]:
        val = cfg.get_string(k)
        src = cfg.get_source(k)
        print(f"Key: {k:14s} -> Değer: {val:16s} [Kazanan Kaynak: {src}]")
    print(f"[*] FILE ile CLI ezme denemesi: {'Engellendi (Güvenli)' if not rejected else 'HATA'}")


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Sabotaj Laboratuvarı: putenv Dangling Pointer
Yığın Bellek Bozulması ve setenv/getenv Multi-Thread Yarış Koşulu Simülatörü
"""

from typing import Dict, List, Tuple

class EnvironmentSabotageLab:
    """putenv yerel bellek bozmasını ve thread-safety zaafiyetini test eden laboratuvar."""
    
    @staticmethod
    def run_putenv_sabotage() -> Tuple[str, str]:
        """Fonksiyon sonlandığında yerel stack değişkeni ezilmesini simüle eder."""
        proc = SimulatedProcessEnvironment()
        
        # Fonksiyon içi: Yerel stack değişkeni oluşturup putenv çağrılıyor
        local_var_string = "TARGET_COORDINATES=39.9208,32.8541"
        proc.putenv_vulnerable(local_var_string, is_on_stack=True)
        
        val_before = proc.getenv("TARGET_COORDINATES")
        held_addr = proc.environ_ptrs[-1]
        
        # Fonksiyon bitti: Stack unwound edildi ve bellek çöp veriyle ezildi!
        proc.unwind_stack_frame()
        
        # İşaretçiyi dereference eden süreç çöp veri okur
        val_after = proc.memory_store.get(held_addr, "")
        return str(val_before), str(val_after)

    @staticmethod
    def simulate_thread_race() -> Tuple[bool, str]:
        """Bir thread okurken diğerinin realloc yapması sonucu çöküşü simüle eder."""
        # Thread A getenv("PATH") çağırıp işaretçiyi tutuyor
        # Thread B o anda 100 tane yeni değişken ekleyerek environ tablosunu realloc ediyor
        old_buffer_address = 0x1000
        new_buffer_address = 0x5000 # realloc taşındı
        
        thread_a_held_ptr = old_buffer_address
        # Thread B eski belleği serbest bıraktı (free)
        freed_address = old_buffer_address
        
        # Thread A işaretçiyi dereference etmeye çalıştığında
        use_after_free = (thread_a_held_ptr == freed_address)
        return use_after_free, "SIGSEGV: Use-After-Free! Thread B environ tablosunu taşırken Thread A eski adrese erişti."

if __name__ == "__main__":
    print("=== [SABOTAJ VE ARIZA LABORATUVARI] ===")
    v_before, v_after = EnvironmentSabotageLab.run_putenv_sabotage()
    print(f"[*] putenv Çağrıldığında Değer     : {v_before}")
    print(f"[*] Stack Unwind Sonrası Okunan     : {v_after} (BOZULMA TEYİT EDİLDİ!)")
    
    is_race, race_msg = EnvironmentSabotageLab.simulate_thread_race()
    print(f"[*] Multi-Thread Yarış Durumu Testi : {race_msg}")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Gizlilik ve Güvenlik Laboratuvarı: /proc Sızıntısı
/proc/PID/environ Üzerinden Parola İfşası ve Güvenli Sıfırlama (Secure Erase)
"""

from typing import Dict, List, Tuple

class SecretLeakageLab:
    """Ortam değişkenlerinde parola saklamanın getirdiği güvenlik riskini analiz eder."""
    
    @staticmethod
    def simulate_secret_leak() -> Tuple[bool, str, str]:
        # Süreç başlatılırken parolayı ortam değişkeni olarak almış
        env = SimulatedProcessEnvironment({
            "USER": "radar_admin",
            "ENCRYPTION_KEY": "ASELSAN_SECRET_KEY_9921",
            "DB_PASS": "SuperSecretPass123"
        })
        
        # Saldırgan /proc/PID/environ okuyor
        proc_environ = env.generate_proc_environ_bytes().decode("utf-8", errors="ignore")
        leaked = "ASELSAN_SECRET_KEY_9921" in proc_environ
        
        # GÜVENLİ SAVUNMA: Süreç anahtarı okuduktan hemen sonra belleği sıfırlamalı
        # ve ortam değişkenini unsetenv ile tablodan düşürmelidir!
        return leaked, proc_environ, "GÜVENLİ ÇÖZÜM: Hassas sırlar ENV yerine RAM disk veya Keyring (TPM) üzerinden aktarılmalıdır."

if __name__ == "__main__":
    leaked, dump, fix = SecretLeakageLab.simulate_secret_leak()
    print("=== [/proc/PID/environ SIZINTI ANALİZİ] ===")
    print(f"[*] Parola Dışarıdan Okunabildi mi?: {leaked}")
    print(f"[*] Saldırganın Gördüğü Veri Dökümü:\n    {dump.replace(chr(0), ' | ')}")
    print(f"[*] Savunma Yönergesi: {fix}")


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Performans ve Benchmark Laboratuvarı: getenv vs Cache
Doğrusal Arama O(N) ile Hash Tablosu Önbelleği O(1) Mikro-Kıyaslaması
"""

import time
from typing import Dict

def run_getenv_vs_cache_benchmark(iterations: int = 50000) -> Dict[str, float]:
    """getenv'in O(N) string taraması ile O(1) önbellek erişimini kıyaslar."""
    
    # 50 elemanlı simüle edilmiş bir environ tablosu
    env_list = [f"DUMMY_VARIABLE_KEY_{i}=VALUE_{i}" for i in range(50)]
    target_key = "RADAR_PULSE_WIDTH"
    env_list.append(f"{target_key}=250_MICROSECONDS") # Hedef sonda (En kötü senaryo O(N))
    
    # 1. Klasik getenv Simülasyonu: Her çağrıda diziyi baştan sona tarar
    t0 = time.perf_counter()
    dummy_acc = 0
    prefix = f"{target_key}="
    for _ in range(iterations):
        for entry in env_list:
            if entry.startswith(prefix):
                dummy_acc += len(entry)
                break
    t_getenv = time.perf_counter() - t0

    # 2. Önbellekli (Cached Config) Simülasyonu: Hash tablosu O(1)
    cache_dict = {k.split("=")[0]: k.split("=")[1] for k in env_list}
    t1 = time.perf_counter()
    for _ in range(iterations):
        val = cache_dict.get(target_key)
        if val:
            dummy_acc += len(val)
    t_cache = time.perf_counter() - t1

    speedup = t_getenv / max(t_cache, 1e-9)
    return {
        "iterations": iterations,
        "t_getenv_sec": t_getenv,
        "t_cache_sec": t_cache,
        "speedup_factor": speedup
    }

if __name__ == "__main__":
    res = run_getenv_vs_cache_benchmark(iterations=50000)
    print("=== [GETENV DOĞRUSAL ARAMA VS HASH CACHE BENCHMARK] ===")
    print(f"Toplam Döngü       : {res['iterations']:,}")
    print(f"getenv O(N) Süresi : {res['t_getenv_sec']*1000:.3f} ms")
    print(f"Cache O(1) Süresi  : {res['t_cache_sec']*1000:.3f} ms")
    print(f"[*] Önbellekleme Hızlanma Çarpanı: {res['speedup_factor']:.2f}x Kat Daha Hızlı!")


# -*- coding: utf-8 -*-
"""
HÜCRE 22 (CODE 6): 4-Panelli Görselleştirme Paneli ve Katı Doğrulama Testleri
Bellek Yığın Mimarisi, Kaskat Hiyerarşisi, getenv vs Cache ve Güvenlik Seviyeleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_095_environment_variables_ve_config.png"

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

    # PANEL 1: Süreç Bellek Yığını (Stack Top) Mimarisi
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("Süreç Adres Uzayı: Top of Stack & environ[] Yerleşimi", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    layers = [
        ("0x7FFFFFFFFFFF: Çevre Değişkeni Stringleri (\"PATH=...\", \"USER=...\")", 0.5, 0.85, accent_blue),
        ("Argüman Stringleri (\"./radar\", \"--config\")", 0.5, 0.68, accent_amber),
        ("char **environ -> [ptr0, ptr1, ptr2, ..., NULL]", 0.5, 0.51, accent_green),
        ("char **argv    -> [arg0, arg1, ..., NULL]", 0.5, 0.34, '#94A3B8'),
        ("argc (Argüman Sayısı)", 0.5, 0.18, '#CBD5E1')
    ]
    for text, x, y, col in layers:
        ax1.text(x, y, text, ha='center', va='center', color=text_color, fontsize=8, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor=col, linewidth=2))

    ax1.set_xlim(0, 1.0)
    ax1.set_ylim(0, 1.0)
    ax1.axis('off')

    # PANEL 2: Kaskat Konfigürasyon Öncelik Piramidi
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("Kaskat Öncelik Hiyerarşisi: Kim Kimi Ezer?", fontsize=12, fontweight='bold', color=accent_amber, pad=12)
    
    levels = ["CLI Argümanları\n(Öncelik: 4 - En Yüksek)", "Ortam Değişkenleri (ENV)\n(Öncelik: 3)", "Konfigürasyon Dosyası\n(Öncelik: 2)", "Derleme Varsayılanları\n(Öncelik: 1 - En Düşük)"]
    weights = [4, 3, 2, 1]
    colors = [accent_red, accent_amber, accent_blue, accent_green]
    
    bars = ax2.barh(levels, weights, color=colors, height=0.55)
    ax2.set_xlabel("Öncelik Ağırlığı", fontsize=10, color=text_color)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars:
        ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, f"Seviye {int(bar.get_width())}",
                 va='center', ha='left', color=text_color, fontsize=9, fontweight='bold')

    # PANEL 3: getenv O(N) vs Cache O(1) Performans Kıyaslaması
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("Erişim Süresi: getenv Doğrusal Arama vs Önbellek (Cache)", fontsize=12, fontweight='bold', color=accent_green, pad=12)
    
    bench = run_getenv_vs_cache_benchmark(iterations=50000)
    cats = ["getenv() [O(N) Doğrusal Tarama]", "Config Cache [O(1) Hash Haritası]"]
    times = [bench['t_getenv_sec'] * 1000, bench['t_cache_sec'] * 1000]
    
    bars3 = ax3.bar(cats, times, color=[accent_amber, accent_green], width=0.45)
    ax3.set_ylabel("50,000 Çağrı Süresi (ms)", fontsize=10, color=text_color)
    ax3.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars3:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f"{bar.get_height():.2f} ms",
                 ha='center', va='bottom', color=text_color, fontsize=9, fontweight='bold')

    # PANEL 4: Güvenlik ve Tehdit Risk Matrisi
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("Ortam Değişkeni Güvenlik Açıkları ve Savunma", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    scenarios = ["putenv Stack Leak", "Multi-Thread Race", "/proc Plain Secret", "SUID LD_PRELOAD"]
    risk_levels = [95, 90, 85, 99] # Risk Skoru
    
    bars4 = ax4.bar(scenarios, risk_levels, color=[accent_red, accent_amber, accent_blue, accent_red], width=0.5)
    ax4.set_ylabel("Risk & Kritiklik Skoru (%)", fontsize=10, color=text_color)
    ax4.set_ylim(0, 115)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars4:
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"%{int(bar.get_height())}",
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

    # 2. Kaskat Öncelik Doğrulaması (CLI > ENV > FILE > DEFAULT)
    cfg = CascadingConfigManager()
    cfg.set("freq", 100, "DEFAULT")
    cfg.set("freq", 200, "FILE")
    cfg.set("freq", 300, "ENV")
    cfg.set("freq", 400, "CLI")
    assert cfg.get_int("freq") == 400, "HATA: CLI değeri tüm kaynakları ezmelidir!"
    assert cfg.get_source("freq") == "CLI", "HATA: Kaynak CLI olmalıdır!"
    
    # Düşük öncelikli kaynağın ezmeye çalışması
    rej = cfg.set("freq", 50, "FILE")
    assert rej is False, "HATA: Düşük öncelikli kaynak yüksek olanı ezememelidir!"
    assert cfg.get_int("freq") == 400, "HATA: Değer değişmemelidir!"
    print("  [+] 4-Kademeli Kaskat Öncelik Hiyerarşisi Doğrulandı.")

    # 3. putenv Yığın Bozma (Dangling Pointer) Doğrulaması
    v_bef, v_aft = EnvironmentSabotageLab.run_putenv_sabotage()
    assert "TARGET_COORDINATES" in v_bef or "39.9208" in v_bef, "HATA: Başlangıçta değer okunabilmelidir!"
    assert "GARBAGE" in v_aft or "DEADBEEF" in v_aft, "HATA: Stack unwound sonrası bellek bozulmalıdır!"
    print("  [+] putenv Dangling Pointer Bellek Bozulması Doğrulandı.")

    # 4. /proc/PID/environ NUL Sınırları ve Sızıntı Doğrulaması
    leaked, dump, _ = SecretLeakageLab.simulate_secret_leak()
    assert leaked is True, "HATA: Sırların /proc üzerinden sızdığı doğrulanmalıdır!"
    print("  [+] /proc/PID/environ NUL Ayrıştırma ve Güvenlik Zaafiyeti Doğrulandı.")

    # 5. Benchmark Hızlanma Doğrulaması
    b_res = run_getenv_vs_cache_benchmark(iterations=10000)
    assert b_res["speedup_factor"] > 1.2, "HATA: Cache mekanizması getenv'e göre daha hızlı olmalıdır!"
    print(f"  [+] Önbellek Hızlanması Doğrulandı ({b_res['speedup_factor']:.2f}x Hızlanma).")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
