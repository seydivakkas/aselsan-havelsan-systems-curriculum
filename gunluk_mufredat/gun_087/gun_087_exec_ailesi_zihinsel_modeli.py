# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 7 (CODE 1): POSIX Sanal Makinesi ve execve() Çekirdek Simülasyonu
Sanal Adres Uzayı (VMA), Dosya Tanıtıcı Tablosu ve ELF Yükleme Mekanizması
"""

import sys
import os
import copy
from typing import List, Dict, Tuple, Optional

class FileDescriptor:
    def __init__(self, fd_num: int, target_name: str, offset: int = 0, cloexec: bool = False):
        self.fd_num = fd_num
        self.target_name = target_name
        self.offset = offset
        self.cloexec = cloexec

    def __repr__(self):
        return f"FD({self.fd_num}, '{self.target_name}', off={self.offset}, cloexec={self.cloexec})"

class VirtualAddressSpace:
    def __init__(self, binary_name: str, text_size_kb: int, data_size_kb: int, heap_size_kb: int, stack_size_kb: int):
        self.binary_name = binary_name
        self.text_size_kb = text_size_kb
        self.data_size_kb = data_size_kb
        self.heap_size_kb = heap_size_kb
        self.stack_size_kb = stack_size_kb
        self.threads_count = 1
        self.signal_handlers: Dict[str, str] = {}

    @property
    def total_size_kb(self) -> int:
        return self.text_size_kb + self.data_size_kb + self.heap_size_kb + self.stack_size_kb

class ElfBinary:
    def __init__(self, path: str, text_kb: int, data_kb: int, is_valid_elf: bool = True, is_executable: bool = True):
        self.path = path
        self.text_kb = text_kb
        self.data_kb = data_kb
        self.is_valid_elf = is_valid_elf
        self.is_executable = is_executable

class PosixProcessSimulator:
    def __init__(self, pid: int, ppid: int, initial_binary: str):
        self.pid = pid
        self.ppid = ppid
        self.real_uid = 1000
        self.real_gid = 1000
        self.umask = 0o022
        self.cwd = "/home/defense/mission"
        self.rlimit_nofile = 1024
        self.arg_max_bytes = 128 * 1024  # 128 KB limit
        
        # Sanal Adres Uzayı (VMA)
        self.vma = VirtualAddressSpace(initial_binary, text_size_kb=512, data_size_kb=128, heap_size_kb=4096, stack_size_kb=256)
        self.vma.threads_count = 4  # Başlangıçta çok thread'li
        self.vma.signal_handlers = {"SIGINT": "0x4012A0", "SIGTERM": "0x401340", "SIGCHLD": "SIG_IGN"}

        # Dosya Tanıtıcı Tablosu (files_struct)
        self.fd_table: Dict[int, FileDescriptor] = {
            0: FileDescriptor(0, "/dev/pts/0", 0, cloexec=False),
            1: FileDescriptor(1, "/dev/pts/0", 0, cloexec=False),
            2: FileDescriptor(2, "/dev/pts/0", 0, cloexec=False),
        }

    def open_file(self, fd_num: int, name: str, cloexec: bool = False) -> int:
        self.fd_table[fd_num] = FileDescriptor(fd_num, name, offset=0, cloexec=cloexec)
        return fd_num

    def execve(self, binary: ElfBinary, argv: List[str], envp: List[str]) -> Tuple[bool, str]:
        """
        Linux sys_execve Sistem Çağrısı Simülasyonu
        Başarılı olursa ASLA geri dönmez (True, 'MUTATED').
        Başarısız olursa -1 döner ve errno üretir.
        """
        # 1. Dosya Varlık ve Yetki Kontrolü
        if not binary.is_valid_elf:
            return False, "ENOEXEC (Exec format error: Invalid ELF magic)"
        if not binary.is_executable:
            return False, "EACCES (Permission denied: Binary not executable)"

        # 2. ARG_MAX Sınır Kontrolü
        total_arg_bytes = sum(len(a.encode('utf-8')) + 1 + 8 for a in argv)
        total_env_bytes = sum(len(e.encode('utf-8')) + 1 + 8 for e in envp)
        if (total_arg_bytes + total_env_bytes) > self.arg_max_bytes:
            return False, f"E2BIG (Argument list too long: {total_arg_bytes + total_env_bytes} > {self.arg_max_bytes})"

        # 3. FD_CLOEXEC Temizliği (Close-on-Exec)
        closed_fds = []
        for fd_num in list(self.fd_table.keys()):
            if self.fd_table[fd_num].cloexec:
                closed_fds.append(fd_num)
                del self.fd_table[fd_num]

        # 4. Eski Sanal Belleği Yok Et (munmap) ve Yeni ELF'i Haritala
        new_vma = VirtualAddressSpace(
            binary_name=binary.path,
            text_size_kb=binary.text_kb,
            data_size_kb=binary.data_kb,
            heap_size_kb=64,   # Temiz sıfırlanmış heap
            stack_size_kb=128  # Yeni temiz stack
        )
        new_vma.threads_count = 1

        # 5. Sinyal Sıfırlama Kuralları:
        for sig, handler in list(self.vma.signal_handlers.items()):
            if handler == "SIG_IGN":
                new_vma.signal_handlers[sig] = "SIG_IGN"
            else:
                new_vma.signal_handlers[sig] = "SIG_DFL"

        self.vma = new_vma
        return True, f"SUCCESS (Process {self.pid} mutated to {binary.path}, Closed FDs: {closed_fds})"

# Doğrulama Testi
_proc = PosixProcessSimulator(pid=4092, ppid=1001, initial_binary="/opt/defense/radar_daemon")
_proc.open_file(3, "/etc/crypto/radar_key.bin", cloexec=False)
_proc.open_file(4, "/dev/hw_telemetry_sock", cloexec=True)

_target_elf = ElfBinary("/usr/bin/target_tracker", text_kb=1024, data_kb=256, is_valid_elf=True, is_executable=True)
_ok, _msg = _proc.execve(_target_elf, argv=["target_tracker", "--scan-rate=60"], envp=["PATH=/usr/bin", "LC_ALL=C"])
print(f"[Modül 1] execve Simülasyonu: {_msg}")


# -*- coding: utf-8 -*-
"""
HÜCRE 9 (CODE 2): C++20 SecureProcessLauncher Simülasyon Modeli
Sıfır Kopyalı Argüman Yönetimi, Ortam Değişkeni Beyaz Listesi (Whitelist) ve _exit(127) Semantiği
"""

from typing import List, Dict, Tuple, Optional

class Cpp20SecureLauncher:
    """
    Modern C++20 std::span ve RAII tabanlı Güvenli Süreç Başlatıcı Simülatörü
    """
    DANGEROUS_ENV_VARS = {"LD_PRELOAD", "LD_LIBRARY_PATH", "IFS", "PYTHONPATH"}
    POSIX_ERR_ENOENT = 127
    POSIX_ERR_EACCES = 126

    def __init__(self, binary_path: str):
        self.binary_path = binary_path
        self.enforce_o_cloexec: bool = True
        self.env_whitelist: Dict[str, str] = {}

    def set_environment_whitelist(self, raw_env: Dict[str, str]) -> Dict[str, str]:
        """Güvenlik Denetimi: Zararlı ortam değişkenlerini (LD_PRELOAD vb.) temizler."""
        sanitized = {}
        for k, v in raw_env.items():
            if k not in self.DANGEROUS_ENV_VARS:
                sanitized[k] = v
        self.env_whitelist = sanitized
        return sanitized

    def spawn(self, args: List[str], raw_env: Dict[str, str], binary_exists: bool = True, is_executable: bool = True) -> Tuple[int, str]:
        """
        fork() + execve() döngüsünü taklit eder.
        Döner: (çıkış_kodu, durum_mesajı)
        """
        # 1. Ortam Güvenliği
        clean_env = self.set_environment_whitelist(raw_env)
        
        # 2. İkili Dosya Varlık Denetimi
        if not binary_exists:
            # POSIX kuralı: Dosya yoksa _exit(127)
            return self.POSIX_ERR_ENOENT, "ERR: Command not found (ENOENT -> _exit(127))"

        # 3. Çalıştırma İzni Denetimi
        if not is_executable:
            # POSIX kuralı: Yetki yoksa _exit(126)
            return self.POSIX_ERR_EACCES, "ERR: Permission denied (EACCES -> _exit(126))"

        # 4. Başarılı Yürütme: execve asla geri dönmez!
        return 0, f"SUCCESS: Process successfully executed {self.binary_path} with {len(args)} args"

# Doğrulama Testi
launcher = Cpp20SecureLauncher("/usr/bin/radar_signal_proc")
tainted_env = {"LD_PRELOAD": "/tmp/rootkit.so", "MISSION_ID": "ASELSAN_99", "PATH": "/usr/bin"}
clean_env = launcher.set_environment_whitelist(tainted_env)

assert "LD_PRELOAD" not in clean_env, "Güvenlik açığı: LD_PRELOAD elenmeliydi!"
assert clean_env["MISSION_ID"] == "ASELSAN_99", "Geçerli değişken korunmalıydı"

exit_code, status_msg = launcher.spawn(["--mode=ACTIVE"], clean_env, binary_exists=True, is_executable=True)
print(f"[Modül 2] SecureProcessLauncher: Code={exit_code}, Durum={status_msg}")


# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Savunma Laboratuvarı
Kasıtlı FD Sızıntısı (Sabotage) vs fcntl(F_SETFD, FD_CLOEXEC) Savunması (Defense)
"""

from typing import Dict, List, Tuple

class SecurityAuditSystem:
    def __init__(self):
        self.audit_log: List[str] = []

    def simulate_attack_scenario(self, use_cloexec: bool) -> Dict[str, any]:
        """
        Radar Yer İstasyonu Tehdit Senaryosu:
        Ana süreç gizli kripto anahtarını (FD: 3) açar.
        Ardından üçüncü parti eklentiyi execve() ile çalıştırır.
        """
        # Ebeveyn Süreç Kaynakları
        open_fds = {
            0: {"desc": "STDIN", "secure": True},
            1: {"desc": "STDOUT", "secure": True},
            2: {"desc": "STDERR", "secure": True},
            3: {"desc": "RADAR_AES256_PRIVATE_KEY", "secure": False, "cloexec": use_cloexec}
        }

        # execve Simülasyonu: Sadece cloexec=True olanlar kapanır
        inherited_after_exec = {}
        for fd, meta in open_fds.items():
            if not meta.get("cloexec", False):
                inherited_after_exec[fd] = meta["desc"]

        # Saldırı Analizi
        breached = (3 in inherited_after_exec)
        result = {
            "use_cloexec": use_cloexec,
            "breached": breached,
            "exposed_fds": inherited_after_exec,
            "security_status": "CRITICAL_VULNERABILITY" if breached else "HARDENED_ISOLATED"
        }
        return result

# Çalıştırma ve Karşılaştırma
audit = SecurityAuditSystem()
sabotage_result = audit.simulate_attack_scenario(use_cloexec=False)
defense_result = audit.simulate_attack_scenario(use_cloexec=True)

print(f"[Sabotaj Testi] FD_CLOEXEC Unutuldu: Breached={sabotage_result['breached']}, Durum={sabotage_result['security_status']}")
print(f"[Savunma Testi] O_CLOEXEC Uygulandı: Breached={defense_result['breached']}, Durum={defense_result['security_status']}")


# -*- coding: utf-8 -*-
"""
HÜCRE 13 (CODE 4): Hata Enjeksiyonu ve Sınır Koşulları
ENOENT, EACCES, E2BIG (ARG_MAX Aşımı), ENOEXEC, ETXTBSY Hata Simülasyonu
"""

from typing import Dict, List, Tuple

class ExecveFaultInjector:
    def __init__(self, arg_max_bytes: int = 131072):
        self.arg_max_bytes = arg_max_bytes

    def test_fault(self, scenario_name: str, path_exists: bool, is_exec: bool, valid_magic: bool, total_bytes: int, is_busy_writing: bool = False) -> Tuple[int, str]:
        """
        Linux sys_execve Hata Kontrol Matrisi
        """
        # 1. Dosya Yolu Kontrolü
        if not path_exists:
            return -1, "ENOENT (2: No such file or directory)"
        
        # 2. Yetki Kontrolü
        if not is_exec:
            return -1, "EACCES (13: Permission denied)"
        
        # 3. Argüman Boyutu Kontrolü
        if total_bytes > self.arg_max_bytes:
            return -1, f"E2BIG (7: Argument list too long [{total_bytes} > {self.arg_max_bytes}])"
        
        # 4. İkili Dosya Biçim Kontrolü (ELF Magic \x7fELF)
        if not valid_magic:
            return -1, "ENOEXEC (8: Exec format error)"

        # 5. Dosya Yazma Kilidi Kontrolü (ETXTBSY)
        if is_busy_writing:
            return -1, "ETXTBSY (26: Text file busy)"

        return 0, "SUCCESS (Executable mapped without error)"

injector = ExecveFaultInjector(arg_max_bytes=1024 * 64) # 64 KB limit

scenarios = [
    ("Normal Çalıştırma", True, True, True, 2048, False),
    ("Hata 1: Olmayan Dosya", False, True, True, 1024, False),
    ("Hata 2: Yetkisiz Dosya", True, False, True, 1024, False),
    ("Hata 3: ARG_MAX Aşımı", True, True, True, 90000, False),
    ("Hata 4: Bozuk ELF Başlığı", True, True, False, 2048, False),
    ("Hata 5: Text File Busy", True, True, True, 1024, True)
]

print("=== [EXECVE HATA ENJEKSİYONU VE SINIR KOŞULLARI] ===")
fault_results = {}
for name, p_ex, is_ex, v_mag, bytes_cnt, is_busy in scenarios:
    code, desc = injector.test_fault(name, p_ex, is_ex, v_mag, bytes_cnt, is_busy)
    fault_results[name] = (code, desc)
    status_tag = "[PASS]" if code == 0 else f"[ERR: {desc.split(' ')[0]}]"
    print(f"{status_tag:<12} {name:<26} -> {desc}")


# -*- coding: utf-8 -*-
"""
HÜCRE 15 (CODE 5): Kapsamlı Benchmark ve Performans Ölçümü
fork()+execve() vs posix_spawn() Latency, P95, Throughput Monte Carlo Simülasyonu
"""

import numpy as np
from typing import Dict, Tuple

def run_exec_benchmark(iterations: int = 2000) -> Dict[str, np.ndarray]:
    """
    fork()+execve() vs posix_spawn() Gecikme Ölçüm Simülasyonu
    Farklı süreç bellek boyutlarına (VIRT) göre sayfa tablosu yükü
    """
    np.random.seed(42)

    # 1. Küçük Süreç (10 MB RSS) - fork()+execve()
    fork_exec_small = np.random.lognormal(mean=6.5, sigma=0.25, size=iterations) # ~700 us

    # 2. Büyük Süreç (8 GB RSS) - fork()+execve()
    fork_exec_large = np.random.lognormal(mean=9.2, sigma=0.35, size=iterations) # ~11,000 us (11 ms)

    # 3. posix_spawn() (CLONE_VM + CLONE_VFORK - Bellek boyutundan bağımsız sabit yük)
    posix_spawn_lat = np.random.lognormal(mean=5.2, sigma=0.20, size=iterations) # ~200 us

    return {
        "fork_exec_small": fork_exec_small,
        "fork_exec_large": fork_exec_large,
        "posix_spawn": posix_spawn_lat
    }

bench_data = run_exec_benchmark(iterations=2000)

metrics = {}
for key, data in bench_data.items():
    metrics[key] = {
        "mean_us": float(np.mean(data)),
        "std_us": float(np.std(data)),
        "p50_us": float(np.percentile(data, 50)),
        "p95_us": float(np.percentile(data, 95)),
        "p99_us": float(np.percentile(data, 99)),
        "min_us": float(np.min(data)),
        "max_us": float(np.max(data))
    }

print("=== [BENCHMARK VE PERFORMANS KARŞILAŞTIRMASI] ===")
for name, m in metrics.items():
    print(f"[{name:<16}] Mean: {m['mean_us']:>9.2f} us | P95: {m['p95_us']:>9.2f} us | P99: {m['p99_us']:>9.2f} us")

speedup_ratio = metrics["fork_exec_large"]["mean_us"] / metrics["posix_spawn"]["mean_us"]
print(f"\n[*] Büyük Bellekli Sistemde posix_spawn Hızlanma Oranı: {speedup_ratio:.2f}x Kat!")


# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 6): Görselleştirme Dashboard'u ve Katı Doğrulama (Assertions)
4 Panelli Koyu Tema Dashboard (Adres Uzayı, Taksonomi, FD Sızıntısı, Benchmark)
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_087_exec_ailesi_zihinsel_modeli.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    # Koyu Tema ve Tipografi Ayarları
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    # -------------------------------------------------------------
    # PANEL 1: Sanal Adres Uzayı Dönüşümü (Before vs After execve)
    # -------------------------------------------------------------
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    
    stages = ['.text (Kod)', '.data (Veri)', 'Heap', 'Stack', 'PIDs & Creds']
    before_sizes = [512, 128, 4096, 256, 100]
    after_sizes = [1024, 256, 64, 128, 100]
    
    x = np.arange(len(stages))
    width = 0.35
    
    rects1 = ax1.bar(x - width/2, before_sizes, width, label='execve Öncesi (Radar Daemon)', color='#38BDF8', alpha=0.9)
    rects2 = ax1.bar(x + width/2, after_sizes, width, label='execve Sonrası (Target Tracker)', color='#F43F5E', alpha=0.9)
    
    ax1.set_title("1. Sanal Adres Uzayı Dönüşümü (VMA Mutation)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax1.set_ylabel("Bellek Boyutu (KB) / Log Ölçek", fontsize=11, color='#CBD5E1')
    ax1.set_yscale('log')
    ax1.set_xticks(x)
    ax1.set_xticklabels(stages, fontsize=10, color='#E2E8F0')
    ax1.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax1.legend(loc='upper right', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 2: POSIX exec Ailesi Taksonomisi ve Özellik Matrisi
    # -------------------------------------------------------------
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    
    functions = ['execl', 'execlp', 'execle', 'execv', 'execvp', 'execvpe', 'execve']
    has_path = [0, 1, 0, 0, 1, 1, 0]
    has_custom_env = [0, 0, 1, 0, 0, 1, 1]
    is_vector = [0, 0, 0, 1, 1, 1, 1]
    
    y = np.arange(len(functions))
    h = 0.25
    
    ax2.barh(y - h, has_path, h, label='PATH Araması (p)', color='#10B981', alpha=0.85)
    ax2.barh(y, has_custom_env, h, label='Özel Ortam / envp (e)', color='#F59E0B', alpha=0.85)
    ax2.barh(y + h, is_vector, h, label='Vektör / argv[] (v)', color='#8B5CF6', alpha=0.85)
    
    ax2.set_title("2. POSIX exec Ailesi Fonksiyon Yetenekleri Matrisi", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax2.set_yticks(y)
    ax2.set_yticklabels(functions, fontsize=11, color='#E2E8F0', fontweight='bold')
    ax2.set_xlabel("Destek Durumu (0: Yok, 1: Var)", fontsize=11, color='#CBD5E1')
    ax2.set_xticks([0, 1])
    ax2.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax2.legend(loc='lower right', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 3: FD Sızıntısı vs O_CLOEXEC Güvenlik Analizi
    # -------------------------------------------------------------
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    
    fd_labels = ['FD 0\nstdin', 'FD 1\nstdout', 'FD 2\nstderr', 'FD 3\nCRYPTO KEY\n(No CLOEXEC)', 'FD 4\nTELEMETRY\n(O_CLOEXEC)']
    leak_status = [1, 1, 1, 1, 0]
    colors = ['#38BDF8', '#38BDF8', '#38BDF8', '#EF4444', '#10B981']
    
    bars = ax3.bar(range(len(fd_labels)), leak_status, color=colors, width=0.5, edgecolor='#0F172A', linewidth=2)
    ax3.set_title("3. Dosya Tanıtıcısı Sızıntı Tehdidi (FD Leaks vs O_CLOEXEC)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax3.set_ylabel("Miras Kalma Durumu (1: Açık, 0: Kapalı)", fontsize=11, color='#CBD5E1')
    ax3.set_xticks(range(len(fd_labels)))
    ax3.set_xticklabels(fd_labels, fontsize=9, color='#E2E8F0')
    ax3.set_yticks([0, 1])
    ax3.set_yticklabels(['KAPATILDI (Güvenli)', 'MİRAS KALDI (Açık)'], fontsize=10, color='#CBD5E1')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#64748B')

    for bar in bars:
        height = bar.get_height()
        status_text = "SIZINTI TEHLİKESİ!" if height == 1 and bar.get_x() > 2.5 else ("GÜVENLİ İZOLASYON" if height == 0 else "STANDART")
        ax3.annotate(status_text,
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold',
                    color='#F8FAFC')

    # -------------------------------------------------------------
    # PANEL 4: Benchmark: fork()+execve() vs posix_spawn() Latency
    # -------------------------------------------------------------
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    
    np.random.seed(42)
    d_small = np.random.lognormal(mean=6.5, sigma=0.25, size=2000)
    d_large = np.random.lognormal(mean=9.2, sigma=0.35, size=2000)
    d_spawn = np.random.lognormal(mean=5.2, sigma=0.20, size=2000)
    
    ax4.hist(d_small, bins=50, density=True, alpha=0.6, color='#38BDF8', label='fork+exec (Küçük Süreç ~0.7ms)')
    ax4.hist(d_spawn, bins=50, density=True, alpha=0.8, color='#10B981', label='posix_spawn (CLONE_VM ~0.2ms)')
    ax4.hist(d_large, bins=50, density=True, alpha=0.5, color='#F43F5E', label='fork+exec (8GB Süreç ~11ms)')
    
    ax4.set_title("4. Süreç Başlatma Gecikmesi Dağılımı (Monte Carlo Sim.)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax4.set_xlabel("Gecikme (Mikrosaniye - us) / Log Ölçek", fontsize=11, color='#CBD5E1')
    ax4.set_xscale('log')
    ax4.set_ylabel("Olasılık Yoğunluğu (KDE)", fontsize=11, color='#CBD5E1')
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

    # 2. Simülatör ve Adres Uzayı Doğrulaması
    sim = PosixProcessSimulator(pid=4092, ppid=1001, initial_binary="/bin/init_proc")
    sim.open_file(3, "/keys/crypto.key", cloexec=False)
    sim.open_file(4, "/sockets/telemetry.sock", cloexec=True)
    
    target = ElfBinary("/bin/mission_proc", text_kb=2048, data_kb=512, is_valid_elf=True, is_executable=True)
    ok, status = sim.execve(target, argv=["mission", "--safe"], envp=["PORT=9000"])
    
    assert ok is True, "HATA: execve simülasyonu başarısız oldu!"
    assert sim.pid == 4092, "HATA: execve sonrasında PID değişmemelidir!"
    assert sim.ppid == 1001, "HATA: execve sonrasında PPID değişmemelidir!"
    assert 3 in sim.fd_table, "HATA: FD 3 cloexec=False olduğu için açık kalmalıydı!"
    assert 4 not in sim.fd_table, "HATA: FD 4 cloexec=True olduğu için kapatılmalıydı!"
    assert sim.vma.threads_count == 1, "HATA: execve sonrasında tek thread kalmalıdır!"
    print("  [+] POSIX Sanal Makinesi ve Çekirdek Kuralları Doğrulandı.")

    # 3. Cpp20 Launcher Doğrulaması
    cl = Cpp20SecureLauncher("/bin/app")
    c_env = cl.set_environment_whitelist({"LD_PRELOAD": "bad.so", "OK": "1"})
    assert "LD_PRELOAD" not in c_env, "HATA: LD_PRELOAD elenmeliydi!"
    c_code, _ = cl.spawn([], c_env, binary_exists=False)
    assert c_code == 127, "HATA: Olmayan ikili dosya 127 kodu dönmeliydi!"
    c_code2, _ = cl.spawn([], c_env, binary_exists=True, is_executable=False)
    assert c_code2 == 126, "HATA: Yetkisiz dosya 126 kodu dönmeliydi!"
    print("  [+] C++20 SecureLauncher ve POSIX Çıkış Kodları Doğrulandı.")

    # 4. Hata Enjeksiyonu Doğrulaması
    inj = ExecveFaultInjector(arg_max_bytes=1024)
    c1, _ = inj.test_fault("Missing", path_exists=False, is_exec=True, valid_magic=True, total_bytes=100)
    c2, _ = inj.test_fault("Perm", path_exists=True, is_exec=False, valid_magic=True, total_bytes=100)
    c3, _ = inj.test_fault("E2BIG", path_exists=True, is_exec=True, valid_magic=True, total_bytes=2000)
    c4, _ = inj.test_fault("Format", path_exists=True, is_exec=True, valid_magic=False, total_bytes=100)
    c5, _ = inj.test_fault("Busy", path_exists=True, is_exec=True, valid_magic=True, total_bytes=100, is_busy_writing=True)
    
    assert c1 == -1 and c2 == -1 and c3 == -1 and c4 == -1 and c5 == -1, "HATA: Hata enjeksiyon kontrolleri başarısız!"
    print("  [+] Hata Enjeksiyonu (ENOENT, EACCES, E2BIG, ENOEXEC, ETXTBSY) Doğrulandı.")

    # 5. Benchmark İstatistik Doğrulaması
    data = run_exec_benchmark(iterations=500)
    mean_spawn = np.mean(data["posix_spawn"])
    mean_large = np.mean(data["fork_exec_large"])
    assert mean_spawn < mean_large, "HATA: posix_spawn büyük süreçte fork+exec'ten hızlı olmalıdır!"
    print(f"  [+] Benchmark Metrikleri Doğrulandı (Speedup: {mean_large/mean_spawn:.1f}x).")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
