# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 7 (CODE 1): POSIX Sinyal Altsistemi ve Çekirdek Simülasyon Motoru
Signal Generation, Pending Mask, Signal Delivery ve Coalescing Mekanizması
"""

from enum import IntEnum
from typing import Dict, List, Set, Optional, Callable

class StandardSignal(IntEnum):
    SIGHUP = 1
    SIGINT = 2
    SIGQUIT = 3
    SIGKILL = 9
    SIGUSR1 = 10
    SIGSEGV = 11
    SIGUSR2 = 12
    SIGPIPE = 13
    SIGALRM = 14
    SIGTERM = 15
    SIGSTOP = 19

class SignalDisposition(IntEnum):
    DEFAULT = 0
    IGNORE = 1
    CUSTOM = 2

class SimulatedProcessSignalTable:
    def __init__(self, pid: int):
        self.pid = pid
        self.pending_signals: Set[StandardSignal] = set() # Pending bitmask
        self.blocked_signals: Set[StandardSignal] = set() # sigprocmask
        self.signal_handlers: Dict[StandardSignal, Tuple[SignalDisposition, Optional[str]]] = {}
        
        # Varsayılan Aksiyonlar Kurulumu
        for sig in StandardSignal:
            self.signal_handlers[sig] = (SignalDisposition.DEFAULT, None)

    def sigaction(self, sig: StandardSignal, disposition: SignalDisposition, handler_name: Optional[str] = None) -> bool:
        """POSIX sigaction() sistem çağrısı simülasyonu."""
        if sig in (StandardSignal.SIGKILL, StandardSignal.SIGSTOP):
            # Çekirdek Koruması: SIGKILL ve SIGSTOP asla değiştirilemez!
            return False
        self.signal_handlers[sig] = (disposition, handler_name)
        return True

    def sigprocmask_block(self, sig: StandardSignal) -> bool:
        """POSIX sigprocmask(SIG_BLOCK) simülasyonu."""
        if sig in (StandardSignal.SIGKILL, StandardSignal.SIGSTOP):
            # Çekirdek Koruması: SIGKILL ve SIGSTOP asla bloke edilemez!
            return False
        self.blocked_signals.add(sig)
        return True

    def sigprocmask_unblock(self, sig: StandardSignal) -> None:
        self.blocked_signals.discard(sig)

    def send_signal(self, sig: StandardSignal) -> str:
        """kill(pid, sig) sistem çağrısı simülasyonu."""
        # 1. SIGKILL özel durumu: Bloke veya yoksayma dinlemez!
        if sig == StandardSignal.SIGKILL:
            return "PROCESS_TERMINATED_IMMEDIATELY_BY_SIGKILL"

        # 2. Sinyal Maskeleme Denetimi
        if sig in self.blocked_signals:
            # Sinyal pending kümesine eklenir (Coalescing: Zaten varsa küme boyutu değişmez)
            self.pending_signals.add(sig)
            return "SIGNAL_BLOCKED_AND_PENDING"

        # 3. Yoksayma Denetimi
        disp, handler = self.signal_handlers.get(sig, (SignalDisposition.DEFAULT, None))
        if disp == SignalDisposition.IGNORE:
            return "SIGNAL_IGNORED"

        # 4. Teslimat (Delivery)
        if disp == SignalDisposition.CUSTOM:
            return f"EXECUTED_CUSTOM_HANDLER:{handler}"
        else:
            return f"EXECUTED_DEFAULT_ACTION_FOR_{sig.name}"

# Doğrulama Testi
if __name__ == "__main__":
    proc = SimulatedProcessSignalTable(pid=8080)
    
    # 1. SIGINT'e özel işleyici bağla
    proc.sigaction(StandardSignal.SIGINT, SignalDisposition.CUSTOM, "safe_shutdown_handler")
    # 2. SIGKILL'e bağlamayı dene (Başarısız olmalı!)
    kill_hook_ok = proc.sigaction(StandardSignal.SIGKILL, SignalDisposition.CUSTOM, "evil_handler")
    print(f"[*] SIGKILL Handler Kayıt Başarısı: {kill_hook_ok} (Beklenen: False)")

    # 3. SIGTERM'i bloke et
    proc.sigprocmask_block(StandardSignal.SIGTERM)
    res_term1 = proc.send_signal(StandardSignal.SIGTERM)
    res_term2 = proc.send_signal(StandardSignal.SIGTERM) # 2. defa gönder (Coalescing)
    print(f"[*] SIGTERM Gönderildi (Blokeli): {res_term1}")
    print(f"[*] Bekleyen (Pending) Sinyal Sayısı: {len(proc.pending_signals)} (Coalescing Doğrulandı: Tek bit)")

    # 4. SIGKILL gönder
    res_kill = proc.send_signal(StandardSignal.SIGKILL)
    print(f"[*] SIGKILL Gönderildi: {res_kill}")


# -*- coding: utf-8 -*-
"""
HÜCRE 9 (CODE 2): C++20 GracefulShutdownCoordinator Simülatörü
Lock-Free std::atomic<bool> Bayrağı, SA_RESTART Yönetimi ve signalfd Entegrasyonu
"""

import time
from typing import Dict, List, Tuple

class Cpp20GracefulShutdownCoordinator:
    """
    Modern C++20 std::atomic<bool> ve SA_RESTART Tabanlı Kapanış Koordinatörü
    Async-Signal-Safe mimarisini simüle eder.
    """
    def __init__(self):
        # C++20 std::atomic<bool> karşılığı
        self._shutdown_requested: bool = False
        self._sa_restart_enabled: bool = True
        self._interrupted_syscall_count: int = 0
        self._completed_tasks_count: int = 0

    @property
    def is_shutdown_requested(self) -> bool:
        return self._shutdown_requested

    def signal_handler_mock(self, signum: int) -> None:
        """
        KUSURSUZ ASYNC-SIGNAL-SAFE İŞLEYİCİ:
        Yalnızca tek bir atomik bayrak yazar. Sıfır I/O, sıfır bellek tahsisi!
        """
        self._shutdown_requested = True

    def execute_event_loop_step(self, simulate_incoming_signal: bool = False) -> str:
        """Ana döngü adımı (Sensör veri okuma, paket işleme)."""
        if simulate_incoming_signal:
            self.signal_handler_mock(15) # SIGTERM geldi!

        if self._shutdown_requested:
            # Zarif Kapanış Protokolü Devrede
            return "DRAINING_AND_EXITING (Safe flush, close hardware sockets, return 0)"

        # Normal Görev İcrası
        self._completed_tasks_count += 1
        return "TASK_PROCESSED_SUCCESSFULLY"

    def simulate_syscall_interruption(self, has_sa_restart: bool) -> Tuple[int, str]:
        """
        SA_RESTART bayrağının EINTR üzerindeki etkisini test eder.
        """
        if has_sa_restart:
            # Çekirdek syscall'u otomatik yeniden başlatır
            return 0, "SUCCESS (Syscall automatically restarted by kernel via SA_RESTART)"
        else:
            # Syscall -1 döner ve errno = EINTR olur
            self._interrupted_syscall_count += 1
            return -1, "EINTR (4: Interrupted system call - User space retry required)"

# Test ve Doğrulama
coordinator = Cpp20GracefulShutdownCoordinator()

# Adım 1: Normal çalışma
status1 = coordinator.execute_event_loop_step(simulate_incoming_signal=False)
# Adım 2: SIGTERM geliyor
status2 = coordinator.execute_event_loop_step(simulate_incoming_signal=True)

print(f"[C++20 Coordinator] Adım 1: {status1}")
print(f"[C++20 Coordinator] Adım 2: {status2}")

# SA_RESTART Farkı
_, msg_restart = coordinator.simulate_syscall_interruption(has_sa_restart=True)
_, msg_no_restart = coordinator.simulate_syscall_interruption(has_sa_restart=False)
print(f"[SA_RESTART Aktif]   -> {msg_restart}")
print(f"[SA_RESTART Pasif]   -> {msg_no_restart}")


# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Savunma Laboratuvarı
Sinyal İşleyicisinde Reentrancy Deadlock (Sabotage) vs Lock-Free Atomic Savunması (Defense)
"""

import threading
import time

class DeadlockSabotageLab:
    def __init__(self):
        self.mutex = threading.Lock()
        self.shared_log: List[str] = []
        self.deadlock_occurred = False

    def unsafe_signal_handler(self) -> None:
        """
        SABOTAJ: Sinyal işleyicisi ana thread'in tuttuğu mutex'i almaya çalışıyor!
        """
        # Bloklamasız dene; eğer kilitliyse gerçek sistemde sonsuza dek asılı kalırdı (Deadlock)
        acquired = self.mutex.acquire(blocking=False)
        if not acquired:
            self.deadlock_occurred = True
            self.shared_log.append("CRITICAL: DEADLOCK_DETECTED (Reentrancy lock violation in signal handler!)")
        else:
            self.shared_log.append("MUTEX_ACQUIRED_UNEXPECTEDLY")
            self.mutex.release()

    def run_sabotage_simulation(self) -> bool:
        # Ana thread mutex'i kilitliyor (Örn: printf veya malloc içinde)
        self.mutex.acquire()
        try:
            # Tam bu anda asenkron sinyal geldi ve handler çalıştı!
            self.unsafe_signal_handler()
        finally:
            self.mutex.release()
        return self.deadlock_occurred

class DefenseSignalLab:
    def __init__(self):
        self.atomic_flag = False

    def safe_signal_handler(self) -> None:
        """
        SAVUNMA: Sıfır lock, sıfır I/O. Yalnızca atomik bayrak.
        """
        self.atomic_flag = True

    def run_defense_simulation(self) -> bool:
        # Ana thread ne kadar meşgul veya kilitli olursa olsun:
        self.safe_signal_handler()
        return self.atomic_flag

sabotage = DeadlockSabotageLab()
sabotage_deadlock = sabotage.run_sabotage_simulation()

defense = DefenseSignalLab()
defense_ok = defense.run_defense_simulation()

print(f"[Sabotaj Testi] Unsafe Handler Deadlock Üretti mi?: {sabotage_deadlock}")
print(f"[Savunma Testi] Atomic Safe Handler Başarılı mı?: {defense_ok}")


# -*- coding: utf-8 -*-
"""
HÜCRE 13 (CODE 4): Hata Enjeksiyonu ve Sınır Koşulları
SIGKILL/SIGSTOP Dokunulmazlığı (EINVAL), SIGPIPE Görmezden Gelme ve EINTR Kurtarma
"""

from typing import Dict, List, Tuple

class SignalFaultInjector:
    @staticmethod
    def test_modify_immutable_signals(signum: int) -> Tuple[int, str]:
        """
        Linux çekirdeğinin SIGKILL (9) ve SIGSTOP (19) üzerindeki koruması.
        """
        if signum in (9, 19):
            return -1, "EINVAL (22: Invalid argument - Cannot catch or ignore SIGKILL/SIGSTOP)"
        return 0, "SUCCESS (Signal disposition updated successfully)"

    @staticmethod
    def test_broken_pipe_behavior(ignore_sigpipe: bool) -> Tuple[int, str]:
        """
        Kırık sokete (closed pipe) veri yazıldığında SIGPIPE davranışı.
        """
        if not ignore_sigpipe:
            # Varsayılan aksiyon: Süreç anında çöker! (Terminated by SIGPIPE)
            return 128 + 13, "TERMINATED_BY_SIGPIPE (Process abruptly terminated due to unhandled broken pipe)"
        else:
            # SIG_IGN yapılmışsa: write() çağrısı -1 döner ve errno = EPIPE olur
            return -1, "EPIPE (32: Broken pipe - Handled gracefully via normal error return)"

    @staticmethod
    def test_eintr_recovery(has_restart_flag: bool) -> Tuple[bool, str]:
        """EINTR kesilmesi ve kurtarma simülasyonu."""
        if has_restart_flag:
            return True, "AUTO_RESTARTED (Kernel handled the interruption)"
        else:
            return False, "EINTR_RAISED (Application code must check errno and retry)"

injector = SignalFaultInjector()

# Test 1: SIGKILL koruması
code_kill, msg_kill = injector.test_modify_immutable_signals(9)
code_usr, msg_usr = injector.test_modify_immutable_signals(10)

# Test 2: SIGPIPE kırık boru
code_pipe_unsafe, msg_pipe_unsafe = injector.test_broken_pipe_behavior(ignore_sigpipe=False)
code_pipe_safe, msg_pipe_safe = injector.test_broken_pipe_behavior(ignore_sigpipe=True)

# Test 3: EINTR
ok_restart, msg_restart = injector.test_eintr_recovery(has_restart_flag=True)
ok_no_restart, msg_no_restart = injector.test_eintr_recovery(has_restart_flag=False)

print("=== [SİNYAL ALTSİSTEMİ HATA ENJEKSİYONU] ===")
print(f"[Korumalı Sinyal] SIGKILL Değiştirme -> {msg_kill}")
print(f"[Normal Sinyal]   SIGUSR1 Değiştirme -> {msg_usr}")
print(f"[Kırık Boru Tehdit] SIGPIPE Korumasız -> {msg_pipe_unsafe} (Exit: {code_pipe_unsafe})")
print(f"[Kırık Boru Savunma] SIGPIPE Yoksayma -> {msg_pipe_safe}")
print(f"[Syscall Kesilmesi] SA_RESTART Aktif  -> {msg_restart}")
print(f"[Syscall Kesilmesi] SA_RESTART Yok    -> {msg_no_restart}")


# -*- coding: utf-8 -*-
"""
HÜCRE 15 (CODE 5): Kapsamlı Benchmark ve Performans Ölçümü
Asenkron sigaction Kesmesi vs Senkron signalfd Okuma Gecikmesi Monte Carlo Simülasyonu
"""

import numpy as np
from typing import Dict, Tuple

def run_signal_benchmark(iterations: int = 2000) -> Dict[str, np.ndarray]:
    """
    Sinyal teslimatı ve işleme gecikme simülasyonu (nanosaniye)
    """
    np.random.seed(42)

    # 1. Klasik sigaction Kesmesi (Context switch, sigframe oluşturma, sigreturn)
    # Log-normal dağılım (~1850 ns)
    sigaction_lat = np.random.lognormal(mean=7.5, sigma=0.28, size=iterations)

    # 2. Modern signalfd ile Senkron Okuma (Zero-context switch interrupt, düz read)
    # Log-normal dağılım (~380 ns)
    signalfd_lat = np.random.lognormal(mean=5.9, sigma=0.18, size=iterations)

    # 3. Sinyal Jitter (Dalgalanma - Gerçek zamanlı sistemler için gecikme sapması)
    rt_jitter = np.abs(np.random.normal(loc=50, scale=15, size=iterations))

    return {
        "sigaction_interrupt": sigaction_lat,
        "signalfd_read": signalfd_lat,
        "rt_jitter": rt_jitter
    }

bench_data = run_signal_benchmark(iterations=2000)

metrics = {}
for key, data in bench_data.items():
    metrics[key] = {
        "mean_ns": float(np.mean(data)),
        "std_ns": float(np.std(data)),
        "p50_ns": float(np.percentile(data, 50)),
        "p95_ns": float(np.percentile(data, 95)),
        "p99_ns": float(np.percentile(data, 99))
    }

print("=== [SİNYAL ALTSİSTEMİ BENCHMARK ANALİZİ] ===")
for name, m in metrics.items():
    print(f"[{name:<20}] Mean: {m['mean_ns']:>8.1f} ns | P50: {m['p50_ns']:>8.1f} ns | P95: {m['p95_ns']:>8.1f} ns | P99: {m['p99_ns']:>8.1f} ns")

gain = metrics["sigaction_interrupt"]["mean_ns"] / metrics["signalfd_read"]["mean_ns"]
print(f"\n[*] Modern signalfd Mimarisi Klasik sigaction Kesmesine Göre {gain:.2f}x Daha Hızlı ve Deterministik!")


# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 6): Görselleştirme Dashboard'u ve Katı Doğrulama (Assertions)
4 Panelli Koyu Tema Dashboard (Sinyal Karşılaştırması, Yaşam Döngüsü, Deadlock Tehdidi, Benchmark)
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_089_signal_sigint_sigterm_sigkill.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    # -------------------------------------------------------------
    # PANEL 1: Üç Büyük Sinyalin Karşılaştırma Matrisi
    # -------------------------------------------------------------
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    
    signals = ['SIGINT (2)', 'SIGTERM (15)', 'SIGKILL (9)', 'SIGSTOP (19)', 'SIGPIPE (13)']
    catchable = [1, 1, 0, 0, 1]
    blockable = [1, 1, 0, 0, 1]
    can_cleanup = [1, 1, 0, 0, 1]
    
    y = np.arange(len(signals))
    h = 0.25
    
    ax1.barh(y - h, catchable, h, label='Yakalanabilir mi? (Catchable)', color='#10B981', alpha=0.85)
    ax1.barh(y, blockable, h, label='Bloke Edilebilir mi? (Blockable)', color='#38BDF8', alpha=0.85)
    ax1.barh(y + h, can_cleanup, h, label='Zarif Temizlik İzni (Cleanup)', color='#F59E0B', alpha=0.85)
    
    ax1.set_title("1. Sinyal Yetenekleri ve Çekirdek Dokunulmazlık Matrisi", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax1.set_yticks(y)
    ax1.set_yticklabels(signals, fontsize=10, color='#E2E8F0', fontweight='bold')
    ax1.set_xlabel("İzin Durumu (0: Yasak / İmkansız, 1: İzinli)", fontsize=11, color='#CBD5E1')
    ax1.set_xticks([0, 1])
    ax1.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax1.legend(loc='lower right', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 2: Sinyal Teslimatı ve sigframe Yığın Mekanizması
    # -------------------------------------------------------------
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    
    phases = ['1. Syscall / Int', '2. Pending Mask', '3. sigframe Build', '4. Handler Exec', '5. sigreturn']
    overhead_us = [0.25, 0.15, 0.65, 0.40, 0.40]
    colors2 = ['#38BDF8', '#64748B', '#EF4444', '#F59E0B', '#10B981']
    
    bars2 = ax2.bar(range(len(phases)), overhead_us, color=colors2, width=0.5, edgecolor='#0F172A', linewidth=2)
    ax2.set_title("2. Sinyal Teslimat Aşamaları ve Yığın Ek Maliyeti (us)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax2.set_ylabel("Gecikme (Mikrosaniye - us)", fontsize=11, color='#CBD5E1')
    ax2.set_xticks(range(len(phases)))
    ax2.set_xticklabels(phases, fontsize=9, color='#E2E8F0', rotation=10)
    ax2.grid(True, linestyle='--', alpha=0.2, color='#64748B')

    for b in bars2:
        y_val = b.get_height()
        ax2.annotate(f"{y_val:.2f} us",
                     xy=(b.get_x() + b.get_width() / 2, y_val),
                     xytext=(0, 4), textcoords="offset points",
                     ha='center', va='bottom', fontsize=9, fontweight='bold',
                     color='#F8FAFC')

    # -------------------------------------------------------------
    # PANEL 3: Zarif Kapanış Süresi (Graceful Timeout) vs SIGKILL
    # -------------------------------------------------------------
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    
    t = np.linspace(0, 5, 200) # Saniye cinsinden
    # Senaryo A: Normal zarif kapanış (1.5 saniyede tamam)
    cleanup_progress_a = np.clip(t / 1.5 * 100, 0, 100)
    # Senaryo B: Kilitlenmiş görev (Takıldı, timeout aşıldı)
    cleanup_progress_b = np.clip(t / 8.0 * 100, 0, 40)
    
    ax3.plot(t, cleanup_progress_a, label='Başarılı Kapanış (SIGTERM -> Exit 0)', color='#10B981', linewidth=2.5)
    ax3.plot(t, cleanup_progress_b, label='Kilitlenmiş Süreç (Takıldı)', color='#EF4444', linewidth=2.5)
    ax3.axvline(x=3.0, color='#F59E0B', linestyle='--', label='Zaman Aşımı Sınırı (Timeout = 3.0s)')
    ax3.scatter([3.0], [40], color='#EF4444', s=120, zorder=5, label='SIGKILL İcra Noktası!')
    
    ax3.set_title("3. Zarif Kapanma Süreci ve SIGKILL Tetikleme Eşiği", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax3.set_xlabel("Geçen Zaman (Saniye)", fontsize=11, color='#CBD5E1')
    ax3.set_ylabel("Temizlik Tamamlanma Yüzdesi (%)", fontsize=11, color='#CBD5E1')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax3.legend(loc='center right', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 4: Benchmark: sigaction Kesmesi vs signalfd Gecikmesi
    # -------------------------------------------------------------
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    
    np.random.seed(42)
    sig_act = np.random.lognormal(mean=7.5, sigma=0.28, size=2000)
    sig_fd = np.random.lognormal(mean=5.9, sigma=0.18, size=2000)
    
    ax4.hist(sig_act, bins=50, density=True, alpha=0.6, color='#EF4444', label='sigaction Kesmesi (~1850 ns)')
    ax4.hist(sig_fd, bins=50, density=True, alpha=0.8, color='#10B981', label='signalfd Senkron Olay (~380 ns)')
    
    ax4.set_title("4. Sinyal Teslimat Gecikmesi Dağılımı (Monte Carlo Sim.)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
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

    # 2. Sinyal Altsistem Simülatör Doğrulaması
    sim = SimulatedProcessSignalTable(pid=9999)
    # SIGKILL değiştirilemez
    assert sim.sigaction(StandardSignal.SIGKILL, SignalDisposition.CUSTOM, "fn") is False, "HATA: SIGKILL değiştirilememeli!"
    assert sim.sigprocmask_block(StandardSignal.SIGKILL) is False, "HATA: SIGKILL bloke edilememeli!"
    # Normal sinyal maskeleme
    sim.sigprocmask_block(StandardSignal.SIGTERM)
    assert StandardSignal.SIGTERM in sim.blocked_signals, "HATA: SIGTERM bloke edilmiş olmalı!"
    sim.send_signal(StandardSignal.SIGTERM)
    sim.send_signal(StandardSignal.SIGTERM)
    assert len(sim.pending_signals) == 1, "HATA: Sinyal birleşmesi (coalescing) başarısız!"
    print("  [+] Sinyal Altsistemi ve Çekirdek Dokunulmazlık Kuralları Doğrulandı.")

    # 3. C++20 Coordinator ve SA_RESTART Doğrulaması
    coord = Cpp20GracefulShutdownCoordinator()
    msg_step1 = coord.execute_event_loop_step(simulate_incoming_signal=False)
    assert "SUCCESSFULLY" in msg_step1, "HATA: Normal döngü adımı başarısız!"
    msg_step2 = coord.execute_event_loop_step(simulate_incoming_signal=True)
    assert coord.is_shutdown_requested is True, "HATA: Atomik bayrak True olmalıydı!"
    assert "DRAINING" in msg_step2, "HATA: Kapanış protokolü devreye girmeliydi!"
    
    c_res, _ = coord.simulate_syscall_interruption(has_sa_restart=True)
    assert c_res == 0, "HATA: SA_RESTART otomatik yeniden başlatmalıydı!"
    c_res2, _ = coord.simulate_syscall_interruption(has_sa_restart=False)
    assert c_res2 == -1, "HATA: SA_RESTART yokken EINTR dönmeliydi!"
    print("  [+] C++20 Coordinator ve SA_RESTART Semantiği Doğrulandı.")

    # 4. Hata Enjeksiyonu Doğrulaması
    inj = SignalFaultInjector()
    c_kill, _ = inj.test_modify_immutable_signals(9)
    assert c_kill == -1, "HATA: SIGKILL modifikasyonu EINVAL vermelidir!"
    c_pipe, _ = inj.test_broken_pipe_behavior(ignore_sigpipe=False)
    assert c_pipe == 141, "HATA: Korumasız SIGPIPE 141 kodu ile sonlanmalıdır (128+13)!"
    print("  [+] Hata Enjeksiyonu ve SIGPIPE Koruma Kuralları Doğrulandı.")

    # 5. Benchmark İstatistik Doğrulaması
    b_data = run_signal_benchmark(iterations=500)
    mean_act = np.mean(b_data["sigaction_interrupt"])
    mean_fd = np.mean(b_data["signalfd_read"])
    assert mean_fd < mean_act, "HATA: signalfd klasik sigaction kesmesinden hızlı olmalıdır!"
    print(f"  [+] Benchmark Metrikleri Doğrulandı (Speedup: {mean_act/mean_fd:.1f}x).")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
