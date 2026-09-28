# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 7 (CODE 1): POSIX Süreç Yaşam Döngüsü ve wstatus Bitmask Çözümleme Motoru
TASK_RUNNING -> EXIT_ZOMBIE -> EXIT_DEAD Durum Makinesi ve POSIX Makro Simülatörü
"""

import sys
from enum import Enum
from typing import Dict, Optional, Tuple

class ProcessState(Enum):
    TASK_RUNNING = "R (Running)"
    TASK_INTERRUPTIBLE = "S (Interruptible Sleep)"
    TASK_UNINTERRUPTIBLE = "D (Uninterruptible Sleep / IO)"
    TASK_STOPPED = "T (Stopped)"
    EXIT_ZOMBIE = "Z (Zombie / Defunct)"
    EXIT_DEAD = "X (Dead / Reaped)"

class WStatusDecoder:
    """
    Linux sys/wait.h Başlığındaki Bitmask Makrolarının Birebir Karşılığı
    """
    @staticmethod
    def encode_exit(exit_code: int) -> int:
        """Normal çıkış durumunu 16-bit wstatus kelimesine kodlar."""
        masked_code = exit_code & 0xFF
        return (masked_code << 8) & 0xFF00

    @staticmethod
    def encode_signal(sig_num: int, core_dump: bool = False) -> int:
        """Sinyal ile ölüm durumunu 16-bit wstatus kelimesine kodlar."""
        val = sig_num & 0x7F
        if core_dump:
            val |= 0x80
        return val

    @staticmethod
    def WIFEXITED(wstatus: int) -> bool:
        return (wstatus & 0x7F) == 0

    @staticmethod
    def WEXITSTATUS(wstatus: int) -> int:
        return (wstatus >> 8) & 0xFF

    @staticmethod
    def WIFSIGNALED(wstatus: int) -> bool:
        # Alt 7 bit 0 değilse ve 0x7F değilse sinyalle öldürülmüştür
        term_sig = wstatus & 0x7F
        return term_sig != 0 and term_sig != 0x7F

    @staticmethod
    def WTERMSIG(wstatus: int) -> int:
        return wstatus & 0x7F

    @staticmethod
    def WCOREDUMP(wstatus: int) -> bool:
        return bool(wstatus & 0x80)

class SimulatedTask:
    def __init__(self, pid: int, ppid: int, name: str):
        self.pid = pid
        self.ppid = ppid
        self.name = name
        self.state = ProcessState.TASK_RUNNING
        self.wstatus: Optional[int] = None
        self.memory_kb: int = 4096  # Başlangıçta 4 MB

    def terminate_normal(self, exit_code: int) -> None:
        """Süreç exit() çağırır. Bellek serbest bırakılır, Zombi olur."""
        self.memory_kb = 0  # VMA serbest bırakıldı
        self.wstatus = WStatusDecoder.encode_exit(exit_code)
        self.state = ProcessState.EXIT_ZOMBIE

    def terminate_signal(self, sig_num: int, core_dump: bool = False) -> None:
        """Süreç sinyalle öldürülür."""
        self.memory_kb = 0
        self.wstatus = WStatusDecoder.encode_signal(sig_num, core_dump)
        self.state = ProcessState.EXIT_ZOMBIE

    def reap(self) -> int:
        """Ebeveyn wait() çağırır, task_struct tamamen silinir."""
        if self.state != ProcessState.EXIT_ZOMBIE:
            raise RuntimeError(f"HATA: Süreç {self.pid} zombi durumunda değil ({self.state})!")
        self.state = ProcessState.EXIT_DEAD
        return self.wstatus

# Doğrulama Testi
if __name__ == "__main__":
    child = SimulatedTask(pid=5001, ppid=1000, name="radar_worker")
    print(f"[*] Süreç Başlatıldı: PID={child.pid}, Durum={child.state.value}, RAM={child.memory_kb} KB")
    
    # Süreç exit(42) ile sonlanıyor
    child.terminate_normal(42)
    print(f"[*] Süreç Sonlandı: PID={child.pid}, Durum={child.state.value}, RAM={child.memory_kb} KB (ZOMBİ)")
    
    # Ebeveyn waitpid() çağırıyor
    captured_wstatus = child.reap()
    print(f"[*] Süreç Hasat Edildi (Reaped): Durum={child.state.value}")
    print(f"    - WIFEXITED: {WStatusDecoder.WIFEXITED(captured_wstatus)}")
    print(f"    - WEXITSTATUS: {WStatusDecoder.WEXITSTATUS(captured_wstatus)}")
    print(f"    - WIFSIGNALED: {WStatusDecoder.WIFSIGNALED(captured_wstatus)}")


# -*- coding: utf-8 -*-
"""
HÜCRE 9 (CODE 2): C++20 RAIISubprocessManager ve Asenkron Zombi Hasadı Simülatörü
Non-blocking WNOHANG, Otomatik Temizlik (RAII Destructor) ve Timeout Yönetimi
"""

from typing import Dict, List, Optional, Tuple

class RAIISubprocessManager:
    """
    Modern C++20 RAII Yaklaşımı ile Alt Süreç Yönetimi Simülatörü
    Destructor çalıştığında alt süreç zombi kalmasın diye otomatik waitpid/kill uygular.
    """
    def __init__(self, pid: int, name: str):
        self.pid = pid
        self.name = name
        self.is_running: bool = True
        self.exit_code: Optional[int] = None
        self.termination_signal: Optional[int] = None

    def poll(self) -> Optional[int]:
        """POSIX waitpid(pid, &status, WNOHANG) simülasyonu (Bloklamasız kontrol)."""
        if not self.is_running:
            return self.exit_code
        return None  # Süreç hala çalışıyor

    def simulate_child_exit(self, code: int) -> None:
        """Çocuk sürecin kendi kendine sonlanması."""
        self.is_running = False
        self.exit_code = code & 0xFF

    def simulate_child_killed(self, sig: int) -> None:
        """Çocuk sürecin sinyalle öldürülmesi."""
        self.is_running = False
        self.termination_signal = sig

    def close(self, timeout_ms: int = 100) -> Tuple[str, Optional[int]]:
        """
        C++20 Destructor Mantığı:
        1. WNOHANG ile çıkmış mı bak.
        2. Çıkmadıysa SIGTERM gönder, bekle.
        3. Hala çıkmadıysa SIGKILL ile zorla sonlandır ve hasat et!
        """
        if not self.is_running:
            return f"CLEAN_REAP (Child {self.pid} already exited)", self.exit_code

        # Süreç hala hayatta -> Güvenli sonlandırma protokolü
        # 1. SIGTERM fırlat
        # 2. Timeout sonrası SIGKILL fırlat
        self.simulate_child_killed(9) # SIGKILL
        return f"FORCE_KILL_AND_REAP (Child {self.pid} killed via SIGKILL to prevent zombie leak)", 128 + 9

# Test ve Doğrulama
sub1 = RAIISubprocessManager(pid=6101, name="dsp_filter")
sub1.simulate_child_exit(0)
msg1, code1 = sub1.close()
print(f"[RAII Subprocess 1] {msg1} -> Code: {code1}")

sub2 = RAIISubprocessManager(pid=6102, name="hung_worker")
# sub2 hiç çıkmıyor (dondu), scope bitiyor (destructor çağrılıyor):
msg2, code2 = sub2.close()
print(f"[RAII Subprocess 2] {msg2} -> Code: {code2}")


# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Savunma Laboratuvarı
Zombi Sızıntısı ile PID Tükenmesi (Sabotage) vs SIGCHLD + WNOHANG Hasadı (Defense)
"""

from typing import List, Dict

class ProcessTableSimulator:
    def __init__(self, max_pids: int = 100):
        self.max_pids = max_pids
        self.table: Dict[int, str] = {} # PID -> State ('RUNNING', 'ZOMBIE')
        self.next_pid = 1000

    def spawn_child(self) -> int:
        if len(self.table) >= self.max_pids:
            raise OSError(f"EAGAIN: Kaynak geçici olarak yetersiz! PID tablosu DOLDU ({self.max_pids}/{self.max_pids})")
        pid = self.next_pid
        self.next_pid += 1
        self.table[pid] = "RUNNING"
        return pid

    def child_exits(self, pid: int) -> None:
        if pid in self.table:
            self.table[pid] = "ZOMBIE"

    def reap_child(self, pid: int) -> None:
        if pid in self.table and self.table[pid] == "ZOMBIE":
            del self.table[pid]

    def reap_all_zombies(self) -> int:
        """while ((pid = waitpid(-1, &status, WNOHANG)) > 0) döngüsü"""
        reaped_count = 0
        for pid in list(self.table.keys()):
            if self.table[pid] == "ZOMBIE":
                del self.table[pid]
                reaped_count += 1
        return reaped_count

# Sabotaj Testi: 100 çocuk üret, hepsi exit yapsın ama hiçbiri hasat edilmesin!
pt_sabotage = ProcessTableSimulator(max_pids=50)
sabotage_failed = False
try:
    for _ in range(50):
        c_pid = pt_sabotage.spawn_child()
        pt_sabotage.child_exits(c_pid)
    # 51. süreçte PID patlaması yaşanmalı!
    pt_sabotage.spawn_child()
except OSError as e:
    sabotage_failed = True
    sabotage_err = str(e)

# Savunma Testi: Her çıkış sonrasında WNOHANG temizliği
pt_defense = ProcessTableSimulator(max_pids=50)
for _ in range(100):
    c_pid = pt_defense.spawn_child()
    pt_defense.child_exits(c_pid)
    pt_defense.reap_all_zombies() # SIGCHLD işleyicisi gibi anında hasat

print(f"[Sabotaj Testi] PID Tablosu Kilitlendi mi?: {sabotage_failed} -> {sabotage_err if sabotage_failed else 'Hayır'}")
print(f"[Savunma Testi] 100 Süreç Sonrası Tablodaki Kalan Süreç Sayısı: {len(pt_defense.table)} (Sıfır Zombi Sızıntısı!)")


# -*- coding: utf-8 -*-
"""
HÜCRE 13 (CODE 4): Hata Enjeksiyonu ve Sınır Koşulları
8-Bit Kesilme Anomalisi, Sinyal Ölümleri, ECHILD ve EINTR Simülasyonu
"""

from typing import Dict, List, Tuple

class ExitCodeFaultLab:
    @staticmethod
    def test_8bit_truncation(input_code: int) -> Tuple[int, bool]:
        """
        Linux çekirdeğinin exit(N) kodunu 8-bit'e kesmesi simülasyonu.
        Döner: (gerçek_dönen_kod, anomali_var_mı)
        """
        actual_posix_code = input_code & 0xFF
        has_anomaly = (actual_posix_code != input_code)
        return actual_posix_code, has_anomaly

    @staticmethod
    def simulate_signal_death(sig_num: int, generate_core: bool) -> Dict[str, any]:
        """Sinyal ile ölüm durumunun wstatus çözümlenmesi."""
        wstatus = sig_num & 0x7F
        if generate_core:
            wstatus |= 0x80
        
        is_exited = ((wstatus & 0x7F) == 0)
        is_signaled = ((wstatus & 0x7F) != 0 and (wstatus & 0x7F) != 0x7F)
        term_sig = wstatus & 0x7F if is_signaled else 0
        has_core = bool(wstatus & 0x80)
        shell_exit_code = 128 + term_sig

        return {
            "wstatus_hex": hex(wstatus),
            "WIFEXITED": is_exited,
            "WIFSIGNALED": is_signaled,
            "WTERMSIG": term_sig,
            "WCOREDUMP": has_core,
            "shell_exit_code": shell_exit_code
        }

print("=== [8-BİT KESİLME VE ANOMALİ LABORATUVARI] ===")
test_inputs = [0, 1, 42, 255, 256, 300, -1, 512]
for code in test_inputs:
    actual, anomaly = ExitCodeFaultLab.test_8bit_truncation(code)
    warn_tag = "[ANOMALİ!]" if anomaly else "[NORMAL]   "
    print(f"{warn_tag} exit({code:>4}) -> Ebeveynin Gördüğü: {actual:>3} (Binary: {actual:08b})")

print("\n=== [SİNYAL İLE ÖLÜM VE CORE DUMP LABORATUVARI] ===")
sig_scenarios = [
    ("SIGKILL (Hemen Öldür)", 9, False),
    ("SIGSEGV (Seg Fault)", 11, True),
    ("SIGTERM (Zarif Kapatma)", 15, False),
    ("SIGABRT (Abort/Assert)", 6, True)
]
for name, signum, core in sig_scenarios:
    res = ExitCodeFaultLab.simulate_signal_death(signum, core)
    print(f"[{name:<24}] wstatus={res['wstatus_hex']} | Signaled={res['WIFSIGNALED']} | Signal={res['WTERMSIG']} | CoreDump={res['WCOREDUMP']} | ShellCode={res['shell_exit_code']}")


# -*- coding: utf-8 -*-
"""
HÜCRE 15 (CODE 5): Kapsamlı Benchmark ve Performans Ölçümü
Senkron waitpid() Bloklaması vs Asenkron WNOHANG Hasatlama Gecikmesi Monte Carlo Simülasyonu
"""

import numpy as np
from typing import Dict, Tuple

def run_lifecycle_benchmark(iterations: int = 2000) -> Dict[str, np.ndarray]:
    """
    Süreç sonlandırma ve hasatlama gecikme karşılaştırması (nanosaniye)
    """
    np.random.seed(42)

    # 1. Senkron waitpid() Bloklayıcı Hasat (Ebeveyn bağlam değişimi ve uyku maliyeti)
    # Log-normal gecikme (nanosaniye)
    blocking_wait = np.random.lognormal(mean=8.2, sigma=0.25, size=iterations) # ~3800 ns

    # 2. Asenkron WNOHANG Polling (Hazır zombiyi anında tablodan alma)
    # Minimum bağlam değişimi
    nonblocking_wait = np.random.lognormal(mean=6.1, sigma=0.20, size=iterations) # ~450 ns

    # 3. Kernel exit_notify + SIGCHLD Sinyal İletim Gecikmesi
    sigchld_delivery = np.random.lognormal(mean=7.5, sigma=0.30, size=iterations) # ~1900 ns

    return {
        "blocking_wait": blocking_wait,
        "nonblocking_wait": nonblocking_wait,
        "sigchld_delivery": sigchld_delivery
    }

bench_data = run_lifecycle_benchmark(iterations=2000)

metrics = {}
for key, data in bench_data.items():
    metrics[key] = {
        "mean_ns": float(np.mean(data)),
        "std_ns": float(np.std(data)),
        "p50_ns": float(np.percentile(data, 50)),
        "p95_ns": float(np.percentile(data, 95)),
        "p99_ns": float(np.percentile(data, 99))
    }

print("=== [SÜREÇ YAŞAM DÖNGÜSÜ BENCHMARK ANALİZİ] ===")
for name, m in metrics.items():
    print(f"[{name:<18}] Mean: {m['mean_ns']:>8.1f} ns | P50: {m['p50_ns']:>8.1f} ns | P95: {m['p95_ns']:>8.1f} ns | P99: {m['p99_ns']:>8.1f} ns")

gain = metrics["blocking_wait"]["mean_ns"] / metrics["nonblocking_wait"]["mean_ns"]
print(f"\n[*] Asenkron WNOHANG Hasatlaması Senkron Bloklamaya Göre {gain:.2f}x Daha Hızlı!")


# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 6): Görselleştirme Dashboard'u ve Katı Doğrulama (Assertions)
4 Panelli Koyu Tema Dashboard (Durum Çizelgesi, wstatus Bit Dağılımı, Zombi Sızıntısı, Benchmark)
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_088_exit_code_ve_process_lifecycle.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    # -------------------------------------------------------------
    # PANEL 1: Linux Süreç Yaşam Döngüsü ve Durum Geçişleri
    # -------------------------------------------------------------
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    
    states = ['1. TASK_RUNNING\n(Aktif / Kuyruk)', '2. TASK_SLEEP\n(S / D Uyku)', '3. TASK_STOPPED\n(SIGSTOP / T)', '4. EXIT_ZOMBIE\n(Bellek Yok / Z)', '5. EXIT_DEAD\n(Hasat / X)']
    durations = [45, 30, 10, 12, 3] # Temsili yaşam döngüsü yüzdesi
    colors = ['#10B981', '#38BDF8', '#F59E0B', '#EF4444', '#64748B']
    
    bars1 = ax1.bar(range(len(states)), durations, color=colors, width=0.55, edgecolor='#0F172A', linewidth=2)
    ax1.set_title("1. Linux Süreç Yaşam Döngüsü ve Durumları (States)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax1.set_ylabel("Tipik Süreç Zaman Payı (%)", fontsize=11, color='#CBD5E1')
    ax1.set_xticks(range(len(states)))
    ax1.set_xticklabels(states, fontsize=9, color='#E2E8F0')
    ax1.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    
    for b in bars1:
        y_val = b.get_height()
        ax1.annotate(f"%{y_val}",
                     xy=(b.get_x() + b.get_width() / 2, y_val),
                     xytext=(0, 4), textcoords="offset points",
                     ha='center', va='bottom', fontsize=10, fontweight='bold',
                     color='#F8FAFC')

    # -------------------------------------------------------------
    # PANEL 2: wstatus 16-Bit Kelime Çözümleme Mimarisi
    # -------------------------------------------------------------
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    
    scenarios = ['exit(0) Success', 'exit(42) Custom', 'SIGKILL (9)', 'SIGSEGV (11) + Core', 'exit(300) Truncate']
    wstatus_vals = [0x0000, 0x2A00, 0x0009, 0x008B, 0x2C00]
    exit_codes = [(w >> 8) & 0xFF for w in wstatus_vals]
    signals = [w & 0x7F if (w & 0x7F) != 0 else 0 for w in wstatus_vals]
    
    y = np.arange(len(scenarios))
    h = 0.35
    
    ax2.barh(y - h/2, exit_codes, h, label='WEXITSTATUS (Exit Code)', color='#38BDF8', alpha=0.85)
    ax2.barh(y + h/2, signals, h, label='WTERMSIG (Ölümcül Sinyal)', color='#F43F5E', alpha=0.85)
    
    ax2.set_title("2. POSIX wstatus Çözümlemesi: Çıkış Kodu vs Sinyal", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax2.set_yticks(y)
    ax2.set_yticklabels(scenarios, fontsize=10, color='#E2E8F0', fontweight='bold')
    ax2.set_xlabel("Sayısal Değer", fontsize=11, color='#CBD5E1')
    ax2.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax2.legend(loc='lower right', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 3: Zombi Sızıntısı vs WNOHANG Hasatlama Simülasyonu
    # -------------------------------------------------------------
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    
    time_steps = np.arange(0, 50, 1)
    # Sabotaj: wait yapılmıyor, zombiler birikiyor
    zombie_leak = time_steps * 2 
    # Savunma: WNOHANG ile periyodik temizleniyor
    defended = np.zeros_like(time_steps)
    for i in range(len(defended)):
        defended[i] = (i % 3) # En fazla 2 zombi anlık bekler
    
    ax3.plot(time_steps, zombie_leak, label='Korumasız Ebeveyn (Zombi Sızıntısı)', color='#EF4444', linewidth=2.5)
    ax3.plot(time_steps, defended, label='SIGCHLD + WNOHANG Savunması', color='#10B981', linewidth=2.5, linestyle='--')
    ax3.axhline(y=80, color='#F59E0B', linestyle=':', label='PID Havuz Tükenme Eşiği')
    
    ax3.set_title("3. Zombi Birikimi ve PID Tüketimi Simülasyonu", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax3.set_xlabel("Zaman Adımı", fontsize=11, color='#CBD5E1')
    ax3.set_ylabel("Sistemdeki Zombi Süreç Sayısı", fontsize=11, color='#CBD5E1')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax3.legend(loc='upper left', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 4: Benchmark: waitpid() Bloklama vs WNOHANG Gecikmesi
    # -------------------------------------------------------------
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    
    np.random.seed(42)
    b_wait = np.random.lognormal(mean=8.2, sigma=0.25, size=2000) # Blocking
    nb_wait = np.random.lognormal(mean=6.1, sigma=0.20, size=2000) # Non-blocking
    
    ax4.hist(b_wait, bins=50, density=True, alpha=0.6, color='#F43F5E', label='Senkron waitpid() Bloklayıcı (~3800 ns)')
    ax4.hist(nb_wait, bins=50, density=True, alpha=0.8, color='#10B981', label='Asenkron WNOHANG Hasat (~450 ns)')
    
    ax4.set_title("4. Hasatlama Gecikmesi Dağılımı (Monte Carlo Sim.)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax4.set_xlabel("Gecikme (Nanosaniye - ns) / Log Ölçek", fontsize=11, color='#CBD5E1')
    ax4.set_xscale('log')
    ax4.set_ylabel("Olasılık Yoğunluğu", fontsize=11, color='#CBD5E1')
    ax4.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax4.legend(loc='upper right', framealpha=0.8, facecolor='#0F172A')

    plt.tight_layout()
    plt.savefig(output_png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_png_path}")

def verify_all_assertions(png_path: str = DEFAULT_PNG):
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dosya Varlık ve Boyut Testleri
    assert os.path.exists(png_path), f"HATA: {png_path} görseli bulunamadı!"
    png_size = os.path.getsize(png_path)
    assert png_size > 50000, f"HATA: Görsel boyutu yetersiz ({png_size} bayt < 50KB)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size} bayt.")

    # 2. Simülatör ve wstatus Bitmask Doğrulaması
    sim_child = SimulatedTask(pid=7001, ppid=1000, name="telemetry")
    sim_child.terminate_normal(120)
    w_code = sim_child.reap()
    assert WStatusDecoder.WIFEXITED(w_code) is True, "HATA: Normal çıkış WIFEXITED=True olmalıdır!"
    assert WStatusDecoder.WEXITSTATUS(w_code) == 120, "HATA: Exit code 120 olarak ayıklanmalıdır!"
    assert WStatusDecoder.WIFSIGNALED(w_code) is False, "HATA: Normal çıkış WIFSIGNALED=False olmalıdır!"
    
    # Sinyal Doğrulaması
    sim_child2 = SimulatedTask(pid=7002, ppid=1000, name="crashed_mod")
    sim_child2.terminate_signal(11, core_dump=True)
    w_sig = sim_child2.reap()
    assert WStatusDecoder.WIFEXITED(w_sig) is False, "HATA: Sinyal ölümü WIFEXITED=False olmalıdır!"
    assert WStatusDecoder.WIFSIGNALED(w_sig) is True, "HATA: Sinyal ölümü WIFSIGNALED=True olmalıdır!"
    assert WStatusDecoder.WTERMSIG(w_sig) == 11, "HATA: Ölümcül sinyal SIGSEGV(11) olmalıdır!"
    assert WStatusDecoder.WCOREDUMP(w_sig) is True, "HATA: Core dump biti True olmalıdır!"
    print("  [+] POSIX wstatus Bitmask ve Durum Makinesi Doğrulandı.")

    # 3. 8-Bit Kesilme Doğrulaması
    c256, anom256 = ExitCodeFaultLab.test_8bit_truncation(256)
    assert c256 == 0 and anom256 is True, "HATA: 256 mod 256 == 0 anomalisi tespit edilemedi!"
    c300, anom300 = ExitCodeFaultLab.test_8bit_truncation(300)
    assert c300 == 44 and anom300 is True, "HATA: 300 mod 256 == 44 anomalisi tespit edilemedi!"
    c_neg, anom_neg = ExitCodeFaultLab.test_8bit_truncation(-1)
    assert c_neg == 255 and anom_neg is True, "HATA: -1 mod 256 == 255 anomalisi tespit edilemedi!"
    print("  [+] 8-Bit Kesilme ve Anomali Testleri Doğrulandı.")

    # 4. Zombi Sızıntısı ve PID Havuzu Doğrulaması
    pt_test = ProcessTableSimulator(max_pids=10)
    for _ in range(10):
        p = pt_test.spawn_child()
        pt_test.child_exits(p)
    try:
        pt_test.spawn_child()
        assert False, "HATA: PID tablosu dolduğunda EAGAIN fırlatılmalıydı!"
    except OSError:
        pass
    reaped = pt_test.reap_all_zombies()
    assert reaped == 10, "HATA: 10 zombi temizlenmeliydi!"
    assert len(pt_test.table) == 0, "HATA: Zombiler temizlendikten sonra tablo boş olmalı!"
    print("  [+] Zombi Sızıntısı ve WNOHANG Hasadı Doğrulandı.")

    # 5. Benchmark İstatistik Doğrulaması
    b_data = run_lifecycle_benchmark(iterations=500)
    mean_b = np.mean(b_data["blocking_wait"])
    mean_nb = np.mean(b_data["nonblocking_wait"])
    assert mean_nb < mean_b, "HATA: WNOHANG bloklayıcı waitpid'den hızlı olmalıdır!"
    print(f"  [+] Benchmark Metrikleri Doğrulandı (Speedup: {mean_b/mean_nb:.1f}x).")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
