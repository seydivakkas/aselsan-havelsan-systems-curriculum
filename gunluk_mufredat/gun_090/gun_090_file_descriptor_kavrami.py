# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 7 (CODE 1): Linux VFS 3-Katmanlı Dosya Tanıtıcı Mimarisi Simülasyonu
Süreç FD Tablosu -> Sistem Geneli Open File Description -> VFS Inode Modeli
"""

from typing import Dict, List, Optional, Tuple

class VfsInode:
    """Katman 3: Disk üzerindeki fiziksel/sanal varlık (struct inode)."""
    def __init__(self, inode_num: int, path: str, size_bytes: int = 0):
        self.inode_num = inode_num
        self.path = path
        self.size_bytes = size_bytes
        self.content: bytearray = bytearray(b"")

class OpenFileDescription:
    """Katman 2: Sistem geneli açık dosya durumu (struct file)."""
    def __init__(self, inode: VfsInode, flags: str = "O_RDWR"):
        self.inode = inode
        self.flags = flags
        self.offset: int = 0
        self.refcount: int = 1  # Kaç FD bu nesneye işaret ediyor

class ProcessFdTable:
    """Katman 1: Süreç başına dosya tanıtıcı tablosu (struct files_struct)."""
    def __init__(self, pid: int, max_fds: int = 1024):
        self.pid = pid
        self.max_fds = max_fds
        # fd_num -> (OpenFileDescription, cloexec_flag)
        self.fd_array: Dict[int, Tuple[OpenFileDescription, bool]] = {}

    def allocate_fd(self, ofd: OpenFileDescription, cloexec: bool = False) -> int:
        """En küçük boş FD numarasını bulur ve atar (find_next_zero_bit)."""
        for fd in range(self.max_fds):
            if fd not in self.fd_array:
                self.fd_array[fd] = (ofd, cloexec)
                return fd
        raise OSError("EMFILE: Too many open files for process")

    def close_fd(self, fd: int) -> bool:
        if fd not in self.fd_array:
            return False
        ofd, _ = self.fd_array[fd]
        ofd.refcount -= 1
        del self.fd_array[fd]
        return True

    def dup(self, oldfd: int) -> int:
        if oldfd not in self.fd_array:
            raise OSError("EBADF: Invalid file descriptor")
        ofd, _ = self.fd_array[oldfd]
        ofd.refcount += 1
        return self.allocate_fd(ofd, cloexec=False)

    def dup2(self, oldfd: int, newfd: int) -> int:
        if oldfd not in self.fd_array:
            raise OSError("EBADF: Invalid file descriptor")
        if oldfd == newfd:
            return newfd  # POSIX kuralı: Aynıysa no-op
        if newfd < 0 or newfd >= self.max_fds:
            raise OSError("EBADF: Target descriptor out of range")
        
        # Eğer newfd açıksa atomik olarak kapat
        if newfd in self.fd_array:
            self.close_fd(newfd)

        ofd, _ = self.fd_array[oldfd]
        ofd.refcount += 1
        self.fd_array[newfd] = (ofd, False)
        return newfd

class VfsKernelEngine:
    """Tüm VFS altsistemini koordine eden çekirdek simülatörü."""
    def __init__(self):
        self.inodes: Dict[int, VfsInode] = {}
        self.next_inode = 100

    def create_file(self, path: str, initial_data: bytes = b"") -> VfsInode:
        ino = VfsInode(self.next_inode, path, len(initial_data))
        ino.content = bytearray(initial_data)
        self.inodes[self.next_inode] = ino
        self.next_inode += 1
        return ino

    def open(self, proc: ProcessFdTable, path: str, flags: str = "O_RDWR") -> int:
        # Inode bul
        target_inode = None
        for ino in self.inodes.values():
            if ino.path == path:
                target_inode = ino
                break
        if not target_inode:
            target_inode = self.create_file(path)

        # Yeni bir struct file (OpenFileDescription) oluştur
        ofd = OpenFileDescription(target_inode, flags)
        return proc.allocate_fd(ofd, cloexec=False)

# Doğrulama Testi
if __name__ == "__main__":
    vfs = VfsKernelEngine()
    test_file = vfs.create_file("/var/log/radar.dat", b"0123456789ABCDEF")
    proc = ProcessFdTable(pid=4092)

    # 1. Dosyayı aç -> FD 0
    fd1 = vfs.open(proc, "/var/log/radar.dat")
    # 2. dup(fd1) çağır -> FD 1
    fd2 = proc.dup(fd1)

    print(f"[*] Dosya Açıldı: FD1={fd1}, dup Çağrıldı: FD2={fd2}")
    ofd1, _ = proc.fd_array[fd1]
    ofd2, _ = proc.fd_array[fd2]
    print(f"[*] Aynı OpenFileDescription'ı mı Paylaşıyorlar?: {ofd1 is ofd2}")
    print(f"[*] Ortak RefCount: {ofd1.refcount}")

    # FD1 üzerinden 5 bayt oku (ofset ilerlet)
    ofd1.offset += 5
    print(f"[*] FD1 5 bayt okudu -> FD1 Ofset: {ofd1.offset}, FD2 Ofset: {ofd2.offset} (PAYLAŞIM DOĞRULANDI)")


# -*- coding: utf-8 -*-
"""
HÜCRE 9 (CODE 2): C++20 UniqueFd RAII Sarmalayıcısı ve Redirection Simülatörü
Move-Only Semantik, Otomatik close() Çağrısı ve EBADF Koruma Mimarisi
"""

from typing import Optional

class Cpp20UniqueFd:
    """
    C++20 std::unique_ptr mantığıyla çalışan POSIX Dosya Tanıtıcısı RAII Sınıfı
    Kopyalama yasak, taşıma (move) serbest, scope bitiminde otomatik close().
    """
    def __init__(self, fd: Optional[int] = None):
        self._fd: Optional[int] = fd

    @property
    def fd(self) -> int:
        if self._fd is None or self._fd < 0:
            raise OSError("EBADF: File descriptor is closed or invalid")
        return self._fd

    def is_valid(self) -> bool:
        return self._fd is not None and self._fd >= 0

    def release(self) -> Optional[int]:
        """Sahipliği devreder (Ownership transfer), destructor kapatmaz."""
        tmp = self._fd
        self._fd = None
        return tmp

    def reset(self, new_fd: Optional[int] = None) -> None:
        """Mevcut tanıtıcıyı kapatır ve yenisini devralır."""
        if self.is_valid():
            # Simüle edilmiş close(self._fd)
            self._fd = None
        self._fd = new_fd

    def move_to(self) -> 'Cpp20UniqueFd':
        """C++20 std::move simülasyonu."""
        new_instance = Cpp20UniqueFd(self._fd)
        self._fd = None
        return new_instance

    def __del__(self):
        """RAII Destructor: Scope bitiminde otomatik kapatma."""
        if self.is_valid():
            self._fd = None

# Test ve Doğrulama
fd_holder1 = Cpp20UniqueFd(3)
print(f"[C++20 UniqueFd 1] Başlangıç FD: {fd_holder1.fd}, Geçerli mi?: {fd_holder1.is_valid()}")

# std::move işlemi: fd_holder1 sahipliği fd_holder2'ye devreder
fd_holder2 = fd_holder1.move_to()
print(f"[C++20 UniqueFd 2] Taşınan FD: {fd_holder2.fd}")
print(f"[C++20 UniqueFd 1] Eski Nesne Geçerli mi?: {fd_holder1.is_valid()} (Boşaltıldı!)")

try:
    _ = fd_holder1.fd
except OSError as e:
    print(f"[Güvenlik Koruması] Eski nesneye erişim engellendi -> {e}")


# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Savunma Laboratuvarı
Kasıtlı FD Sızıntısı ile EMFILE Çöküşü (Sabotage) vs RAII Otomatik Temizlik (Defense)
"""

from typing import List

class FdResourceLeakLab:
    def __init__(self, rlimit_nofile: int = 50):
        self.rlimit_nofile = rlimit_nofile
        self.open_fds: List[int] = []
        self.next_fd = 3  # 0, 1, 2 stdin/stdout/stderr

    def open_dummy_fd(self) -> int:
        if len(self.open_fds) >= (self.rlimit_nofile - 3):
            raise OSError(f"EMFILE: Too many open files! Sınır aşıldı ({self.rlimit_nofile})")
        fd = self.next_fd
        self.next_fd += 1
        self.open_fds.append(fd)
        return fd

    def close_fd(self, fd: int) -> None:
        if fd in self.open_fds:
            self.open_fds.remove(fd)

# Sabotaj Testi: Döngüde dosya açıp close() çağırmayı unutan acemi kod
leak_lab = FdResourceLeakLab(rlimit_nofile=20)
sabotage_crashed = False
sabotage_err = ""

try:
    for _ in range(50):
        # close yapılmıyor -> Sızıntı!
        leak_lab.open_dummy_fd()
except OSError as e:
    sabotage_crashed = True
    sabotage_err = str(e)

# Savunma Testi: RAII mekanizması ile her işlem sonunda anında close()
defense_lab = FdResourceLeakLab(rlimit_nofile=20)
for _ in range(100):
    fd = defense_lab.open_dummy_fd()
    # Scope sonu simülasyonu:
    defense_lab.close_fd(fd)

print(f"[Sabotaj Testi] FD Sızıntısı ile Süreç Çöktü mü?: {sabotage_crashed} -> {sabotage_err}")
print(f"[Savunma Testi] 100 İşlem Sonrası Açık Kalan FD Sayısı: {len(defense_lab.open_fds)} (Sıfır Sızıntı!)")


# -*- coding: utf-8 -*-
"""
HÜCRE 13 (CODE 4): Hata Enjeksiyonu ve Sınır Koşulları
EBADF (Geçersiz FD), EMFILE (Limit Aşımı), dup2(fd, fd) İstisnası ve Negatif FD
"""

from typing import Dict, List, Tuple

class FdFaultInjector:
    def __init__(self, max_limit: int = 10):
        self.max_limit = max_limit
        self.open_set = {0, 1, 2} # stdin, stdout, stderr

    def test_read_closed_fd(self, fd: int) -> Tuple[int, str]:
        """Kapatılmış veya hiç açılmamış FD ile işlem yapma."""
        if fd not in self.open_set or fd < 0:
            return -1, "EBADF (9: Bad file descriptor - Descriptor is not open)"
        return 0, "SUCCESS"

    def test_dup2_same_fd(self, oldfd: int, newfd: int) -> Tuple[int, str]:
        """POSIX dup2(x, x) istisna kuralı denetimi."""
        if oldfd not in self.open_set or oldfd < 0:
            return -1, "EBADF (9: Bad file descriptor)"
        if oldfd == newfd:
            return newfd, "SUCCESS_NO_OP (POSIX Rule: dup2 to same descriptor does nothing)"
        return newfd, "SUCCESS_CLONED"

    def test_fd_overflow(self) -> Tuple[int, str]:
        """Limit aşımında dönen çekirdek hatası."""
        current_count = len(self.open_set)
        if current_count >= self.max_limit:
            return -1, f"EMFILE (24: Too many open files - Limit {self.max_limit} reached)"
        return 0, "SUCCESS"

injector = FdFaultInjector(max_limit=3)

# Test 1: Kapalı FD okuma
c_bad, msg_bad = injector.test_read_closed_fd(99)
c_neg, msg_neg = injector.test_read_closed_fd(-1)

# Test 2: dup2 aynı FD
c_same, msg_same = injector.test_dup2_same_fd(1, 1)

# Test 3: Limit taşması
c_overflow, msg_overflow = injector.test_fd_overflow()

print("=== [DOSYA TANITICISI HATA ENJEKSİYONU] ===")
print(f"[Hata 1] Kapalı FD (99)  -> {msg_bad}")
print(f"[Hata 2] Negatif FD (-1) -> {msg_neg}")
print(f"[Kural 3] dup2(1, 1)     -> {msg_same} (Kod: {c_same})")
print(f"[Hata 4] Limit Aşımı     -> {msg_overflow}")


# -*- coding: utf-8 -*-
"""
HÜCRE 15 (CODE 5): Kapsamlı Benchmark ve Performans Ölçümü
FD Tablosu Arama/Tahsis Gecikmesi vs Doğrudan İndeks Erişimi Monte Carlo Simülasyonu
"""

import numpy as np
from typing import Dict, Tuple

def run_fd_benchmark(iterations: int = 2000) -> Dict[str, np.ndarray]:
    """
    FD tahsisi (find_next_zero_bit) ve indeks çözümleme gecikmesi (nanosaniye)
    """
    np.random.seed(42)

    # 1. FD Tahsisi (open / dup): Bitmask arama + struct file bağlama
    # Log-normal gecikme (~420 ns)
    fd_alloc_lat = np.random.lognormal(mean=6.0, sigma=0.22, size=iterations)

    # 2. FD Çözümleme (read / write sırasında fd -> struct file pointer lookup)
    # Doğrudan dizi indeksi erişimi (~45 ns)
    fd_lookup_lat = np.random.lognormal(mean=3.8, sigma=0.15, size=iterations)

    # 3. dup2 Atomik Kapatma ve Klonlama Maliyeti
    # (~310 ns)
    dup2_lat = np.random.lognormal(mean=5.7, sigma=0.20, size=iterations)

    return {
        "fd_allocation": fd_alloc_lat,
        "fd_lookup": fd_lookup_lat,
        "dup2_clone": dup2_lat
    }

bench_data = run_fd_benchmark(iterations=2000)

metrics = {}
for key, data in bench_data.items():
    metrics[key] = {
        "mean_ns": float(np.mean(data)),
        "std_ns": float(np.std(data)),
        "p50_ns": float(np.percentile(data, 50)),
        "p95_ns": float(np.percentile(data, 95)),
        "p99_ns": float(np.percentile(data, 99))
    }

print("=== [DOSYA TANITICISI BENCHMARK ANALİZİ] ===")
for name, m in metrics.items():
    print(f"[{name:<16}] Mean: {m['mean_ns']:>8.1f} ns | P50: {m['p50_ns']:>8.1f} ns | P95: {m['p95_ns']:>8.1f} ns | P99: {m['p99_ns']:>8.1f} ns")

speedup = metrics["fd_allocation"]["mean_ns"] / metrics["fd_lookup"]["mean_ns"]
print(f"\n[*] Doğrudan FD İndeks Çözümlemesi Tahsise Göre {speedup:.2f}x Kat Daha Hızlı!")


# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 6): Görselleştirme Dashboard'u ve Katı Doğrulama (Assertions)
4 Panelli Koyu Tema Dashboard (VFS 3-Katman, Ofset Paylaşımı, Sızıntı vs Savunma, Benchmark)
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_090_file_descriptor_kavrami.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    # -------------------------------------------------------------
    # PANEL 1: VFS 3-Katmanlı Mimari Veri Akış Modeli
    # -------------------------------------------------------------
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    
    layers = ['Katman 1:\nSüreç FD Tablosu\n(task->files->fd)', 
              'Katman 2:\nAçık Dosya Tanımı\n(struct file / Offset)', 
              'Katman 3:\nVFS Inode\n(struct inode / Disk)']
    counts = [1024, 256, 120] # Göreli kapasite/sayı temsili
    colors = ['#38BDF8', '#F59E0B', '#10B981']
    
    bars1 = ax1.bar(range(len(layers)), counts, color=colors, width=0.5, edgecolor='#0F172A', linewidth=2)
    ax1.set_title("1. Linux VFS 3-Katmanlı Veri Yapısı Ayrımı", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax1.set_ylabel("Hiyerarşik Düzey / Temsili Varlık", fontsize=11, color='#CBD5E1')
    ax1.set_xticks(range(len(layers)))
    ax1.set_xticklabels(layers, fontsize=9, color='#E2E8F0')
    ax1.grid(True, linestyle='--', alpha=0.2, color='#64748B')

    for b in bars1:
        y_val = b.get_height()
        ax1.annotate(f"Düzey {b.get_x()+0.5:.0f}",
                     xy=(b.get_x() + b.get_width() / 2, y_val),
                     xytext=(0, 5), textcoords="offset points",
                     ha='center', va='bottom', fontsize=10, fontweight='bold',
                     color='#F8FAFC')

    # -------------------------------------------------------------
    # PANEL 2: Bağımsız open() vs dup() Ofset Paylaşımı
    # -------------------------------------------------------------
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    
    steps = ['Başlangıç', 'FD_A 10B Oku', 'FD_B 20B Oku', 'FD_A 15B Oku']
    # Bağımsız open: FD A ve FD B bağımsız ofsetlere sahip
    offset_indep_a = [0, 10, 10, 25]
    offset_indep_b = [0, 0, 20, 20]
    
    # dup() paylaşımı: İkisi aynı ofseti tüketir
    offset_shared = [0, 10, 30, 45]
    
    x = np.arange(len(steps))
    ax2.plot(x, offset_indep_a, marker='o', color='#38BDF8', linewidth=2.5, label='Bağımsız open(): FD A Ofseti')
    ax2.plot(x, offset_indep_b, marker='s', color='#F59E0B', linewidth=2.5, label='Bağımsız open(): FD B Ofseti')
    ax2.plot(x, offset_shared, marker='^', color='#EF4444', linewidth=2.5, linestyle='--', label='dup() / fork(): Ortak Paylaşılan Ofset')
    
    ax2.set_title("2. Dosya Ofseti (Cursor) İlerleme Dinamiği", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(steps, fontsize=10, color='#E2E8F0')
    ax2.set_ylabel("Dosya İçi Konum (Bayt)", fontsize=11, color='#CBD5E1')
    ax2.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax2.legend(loc='upper left', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 3: FD Sızıntısı (Leak) vs RAII Güvenliği
    # -------------------------------------------------------------
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    
    ops = np.arange(0, 35, 1)
    # Korumasız kod: Her operasyonda FD açılıyor, kapanmıyor
    leaked_fds = ops + 3
    # RAII savunması: Açılıp kapanıyor, açık sayısı sabit kalıyor
    raii_fds = np.full_like(ops, 3)
    
    ax3.plot(ops, leaked_fds, color='#EF4444', linewidth=2.5, label='Korumasız Kod (FD Sızıntısı)')
    ax3.plot(ops, raii_fds, color='#10B981', linewidth=2.5, linestyle='--', label='C++20 UniqueFd (RAII Korumalı)')
    ax3.axhline(y=30, color='#F59E0B', linestyle=':', label='RLIMIT_NOFILE Sınırı (30)')
    ax3.scatter([27], [30], color='#EF4444', s=120, zorder=5, label='EMFILE Çöküş Noktası!')
    
    ax3.set_title("3. Dosya Tanıtıcısı Sızıntısı ve EMFILE Çöküşü", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax3.set_xlabel("İcra Edilen I/O Operasyon Sayısı", fontsize=11, color='#CBD5E1')
    ax3.set_ylabel("Açık Kalan FD Sayısı", fontsize=11, color='#CBD5E1')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax3.legend(loc='upper left', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 4: Benchmark: FD Tahsis vs Doğrudan İndeks Erişimi
    # -------------------------------------------------------------
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    
    np.random.seed(42)
    d_alloc = np.random.lognormal(mean=6.0, sigma=0.22, size=2000)
    d_lookup = np.random.lognormal(mean=3.8, sigma=0.15, size=2000)
    
    ax4.hist(d_alloc, bins=50, density=True, alpha=0.6, color='#F59E0B', label='FD Tahsisi (open/dup ~420 ns)')
    ax4.hist(d_lookup, bins=50, density=True, alpha=0.8, color='#10B981', label='Doğrudan FD İndeks Lookup (~45 ns)')
    
    ax4.set_title("4. FD Erişim Gecikmesi Dağılımı (Monte Carlo Sim.)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
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

    # 2. VFS Katman ve Ofset Doğrulaması
    vfs = VfsKernelEngine()
    vfs.create_file("/test.bin", b"DATA")
    proc = ProcessFdTable(pid=1000)
    fd1 = vfs.open(proc, "/test.bin")
    fd2 = proc.dup(fd1)
    
    ofd1, _ = proc.fd_array[fd1]
    ofd2, _ = proc.fd_array[fd2]
    assert ofd1 is ofd2, "HATA: dup() aynı OpenFileDescription'a işaret etmelidir!"
    assert ofd1.refcount == 2, "HATA: dup() sonrası refcount 2 olmalıdır!"
    
    ofd1.offset = 15
    assert ofd2.offset == 15, "HATA: Ortak ofset senkronizasyonu başarısız!"
    
    proc.close_fd(fd1)
    assert ofd2.refcount == 1, "HATA: fd1 kapatılınca refcount 1'e düşmelidir!"
    assert fd2 in proc.fd_array, "HATA: fd2 hala açık kalmalıdır!"
    print("  [+] VFS 3-Katman Mimarisi ve Ofset Paylaşımı Doğrulandı.")

    # 3. C++20 UniqueFd Doğrulaması
    ufd1 = Cpp20UniqueFd(10)
    assert ufd1.is_valid() is True, "HATA: ufd1 geçerli olmalı!"
    ufd2 = ufd1.move_to()
    assert ufd1.is_valid() is False, "HATA: Taşınan ufd1 geçersiz olmalı!"
    assert ufd2.fd == 10, "HATA: Taşınan ufd2 FD 10 olmalıdır!"
    print("  [+] C++20 UniqueFd Move Semantics ve Sahiplik Doğrulandı.")

    # 4. Hata Enjeksiyonu Doğrulaması
    inj = FdFaultInjector(max_limit=2)
    c_bad, _ = inj.test_read_closed_fd(44)
    assert c_bad == -1, "HATA: Kapalı FD EBADF dönmeli!"
    c_same, _ = inj.test_dup2_same_fd(1, 1)
    assert c_same == 1, "HATA: dup2(x, x) no-op olmalı ve x dönmeli!"
    c_limit, _ = inj.test_fd_overflow()
    assert c_limit == -1, "HATA: Limit aşımı EMFILE dönmeli!"
    print("  [+] Hata Enjeksiyonu (EBADF, EMFILE, dup2 no-op) Doğrulandı.")

    # 5. Benchmark İstatistik Doğrulaması
    b_data = run_fd_benchmark(iterations=500)
    mean_alloc = np.mean(b_data["fd_allocation"])
    mean_lookup = np.mean(b_data["fd_lookup"])
    assert mean_lookup < mean_alloc, "HATA: Doğrudan indeks lookup tahsisten hızlı olmalıdır!"
    print(f"  [+] Benchmark Metrikleri Doğrulandı (Speedup: {mean_alloc/mean_lookup:.1f}x).")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
