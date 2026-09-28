# -*- coding: utf-8 -*-
# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
# amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz.


# -*- coding: utf-8 -*-
"""
HÜCRE 04 (CODE 1): Python ile ptrace ve strace Çekirdek Olay Yakalama Simülasyonu
Syscall-Enter ve Syscall-Exit Trap Mekanizması, Context Switch ve Gecikme Modeli
"""

import time
from typing import Dict, List, Any, Tuple

class SimulatedSyscallContext:
    """Linux çekirdeği CPU register ve syscall durumu simülatörü."""
    def __init__(self, name: str, args: List[Any], return_val: int, duration_us: float):
        self.name = name
        self.args = args
        self.return_val = return_val
        self.duration_us = duration_us
        self.errno: str = "" if return_val >= 0 else "ENOENT"

class SimulatedKernelSyscallTracer:
    """Linux ptrace(2) ve strace altyapısının çekirdek seviyesi simülasyonu."""
    
    # Baz sistem çağrısı çekirdek süresi: ~0.25 µs (250 ns)
    BASE_SYSCALL_LATENCY_US = 0.25
    # ptrace trap + 2 x Context Switch süresi: ~12.5 µs (12,500 ns)
    PTRACE_TRAP_OVERHEAD_US = 12.5

    def __init__(self, trace_filter: Optional[List[str]] = None, measure_time: bool = True):
        self.trace_filter = trace_filter
        self.measure_time = measure_time
        self.output_log: List[str] = []
        self.stats: Dict[str, Dict[str, Any]] = {}
        self.total_overhead_us: float = 0.0

    def trace_syscall(self, call: SimulatedSyscallContext, is_attached: bool = True) -> float:
        """Bir sistem çağrısını yürütür ve ptrace takılıysa izler."""
        # 1. Filtre kontrolü
        if self.trace_filter and call.name not in self.trace_filter:
            return call.duration_us

        # 2. İstatistik başlat
        if call.name not in self.stats:
            self.stats[call.name] = {"calls": 0, "errors": 0, "total_time_us": 0.0}
        
        self.stats[call.name]["calls"] += 1
        if call.return_val < 0:
            self.stats[call.name]["errors"] += 1

        # 3. ptrace devrede mi?
        actual_latency_us = call.duration_us
        if is_attached:
            # Syscall-Enter Trap (Context Switch 1 & 2) + Syscall-Exit Trap (Context Switch 3 & 4)
            overhead = self.PTRACE_TRAP_OVERHEAD_US
            actual_latency_us += overhead
            self.total_overhead_us += overhead

            # Biçimlendirilmiş strace çıktısı
            args_str = ", ".join(str(a) for a in call.args)
            ret_str = str(call.return_val) if call.return_val >= 0 else f"-1 {call.errno} (No such file or directory)"
            
            time_suffix = f" <{actual_latency_us / 1e6:.6f}>" if self.measure_time else ""
            log_line = f"{call.name}({args_str}) = {ret_str}{time_suffix}"
            self.output_log.append(log_line)

        self.stats[call.name]["total_time_us"] += actual_latency_us
        return actual_latency_us


if __name__ == "__main__":
    print("=== STRACE / PTRACE ÇEKİRDEK İZLEME SİMÜLASYONU ===")
    tracer = SimulatedKernelSyscallTracer(measure_time=True)

    # Simüle edilmiş bir C++ servisinin başlarken yaptığı syscall'lar
    sample_calls = [
        SimulatedSyscallContext("openat", ["AT_FDCWD", "\"/etc/radar.conf\"", "O_RDONLY"], return_val=3, duration_us=1.2),
        SimulatedSyscallContext("read", [3, "\"RADAR_CONFIG_BLOCK\"", 1024], return_val=1024, duration_us=2.5),
        SimulatedSyscallContext("close", [3], return_val=0, duration_us=0.8),
        SimulatedSyscallContext("openat", ["AT_FDCWD", "\"/opt/aselsan/calibration.dat\"", "O_RDONLY"], return_val=-1, duration_us=0.9),
        SimulatedSyscallContext("epoll_create1", ["EPOLL_CLOEXEC"], return_val=4, duration_us=1.5),
        SimulatedSyscallContext("epoll_wait", [4, "...", 64, -1], return_val=1, duration_us=45.0)
    ]

    for c in sample_calls:
        tracer.trace_syscall(c, is_attached=True)

    print("\n--- [STRACE ÇIKTISI] ---")
    for line in tracer.output_log:
        print(f"  {line}")

    print(f"\n[*] Toplam ptrace Ek Yükü (Overhead): {tracer.total_overhead_us:.2f} µs")


# -*- coding: utf-8 -*-
"""
HÜCRE 08 (CODE 2): Python ile strace Log Ayrıştırıcı ve İstatistik Motoru
Ham strace Metin Çıktısını Ayrıştırma, Hata Frekansı ve P99 Gecikme Hesaplayıcısı
"""

import re
from typing import Dict, List, Any

class StraceLogParser:
    """strace çıktılarını ayrıştırıp metrik üreten analitik motor."""
    
    # Regex formatı: openat(AT_FDCWD, "/path", O_RDONLY) = 3 <0.000120>
    LOG_PATTERN = re.compile(r"^(\w+)\((.*)\)\s+=\s+(-?\w+)(?:\s+([A-Z]+))?(?:.*<([\d\.]+)>)?")

    def __init__(self):
        self.parsed_records: List[Dict[str, Any]] = []

    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        line = line.strip()
        if not line or line.startswith("---") or line.startswith("+++"):
            return None # Sinyal veya exit satırları

        match = self.LOG_PATTERN.match(line)
        if not match:
            return None

        syscall_name = match.group(1)
        raw_args = match.group(2)
        raw_return = match.group(3)
        errno_str = match.group(4) or ""
        duration_s = float(match.group(5)) if match.group(5) else 0.0

        record = {
            "syscall": syscall_name,
            "args": raw_args,
            "return_code": raw_return,
            "errno": errno_str,
            "is_error": raw_return.startswith("-") or (errno_str != ""),
            "duration_us": duration_s * 1e6
        }
        self.parsed_records.append(record)
        return record

    def compute_summary_statistics(self) -> Dict[str, Any]:
        stats: Dict[str, Dict[str, Any]] = {}
        for rec in self.parsed_records:
            name = rec["syscall"]
            if name not in stats:
                stats[name] = {"count": 0, "errors": 0, "durations_us": []}
            stats[name]["count"] += 1
            if rec["is_error"]:
                stats[name]["errors"] += 1
            stats[name]["durations_us"].append(rec["duration_us"])

        summary = {}
        for name, data in stats.items():
            durations = np.array(data["durations_us"])
            summary[name] = {
                "calls": data["count"],
                "errors": data["errors"],
                "total_time_us": float(np.sum(durations)),
                "mean_us": float(np.mean(durations)),
                "p99_us": float(np.percentile(durations, 99)) if len(durations) > 0 else 0.0
            }
        return summary


if __name__ == "__main__":
    print("=== STRACE LOG AYRIŞTIRICI DENEYİ ===")
    parser = StraceLogParser()

    sample_strace_output = """
    openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3 <0.000015>
    read(3, "\\177ELF\\2\\1\\1", 832) = 832 <0.000008>
    close(3) = 0 <0.000005>
    openat(AT_FDCWD, "/missing/radar_calib.bin", O_RDONLY) = -1 ENOENT <0.000018>
    epoll_wait(4, [{events=EPOLLIN, data={u32=5, u64=5}}], 64, 1000) = 1 <0.004250>
    write(1, "Target Detected: ID 402\\n", 25) = 25 <0.000022>
    """

    for l in sample_strace_output.strip().split("\n"):
        parser.parse_line(l)

    stats = parser.compute_summary_statistics()
    print(f"{'Syscall':>12} | {'Çağrı':>6} | {'Hata':>6} | {'Toplam (µs)':>12} | {'P99 (µs)':>10}")
    print("-" * 56)
    for sc, data in stats.items():
        print(f"{sc:>12} | {data['calls']:>6d} | {data['errors']:>6d} | {data['total_time_us']:>12.2f} | {data['p99_us']:>10.2f}")


# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Arıza Simülatörü
strace Ek Yükünün Neden Olduğu Aviyonik Watchdog Zaman Aşımı ve Heisenbug Modeli
"""

from typing import Dict, Any, Tuple

class StraceOverheadSabotageLab:
    """strace ptrace gecikmesinin gerçek zamanlı sistemler üzerindeki tahribat simülatörü."""

    @staticmethod
    def simulate_watchdog_timeout_induced_by_strace(
        num_syscalls_per_cycle: int = 80000, 
        watchdog_limit_sec: float = 1.0,
        enable_strace: bool = False
    ) -> Dict[str, Any]:
        """strace takıldığında bir radar döngüsünün Watchdog süresini aşıp aşmadığını test eder."""
        # Normal syscall süresi: 200 ns
        normal_syscall_time_s = 200e-9
        # ptrace ek yükü: 15 µs
        ptrace_overhead_s = 15e-6 if enable_strace else 0.0

        effective_syscall_time_s = normal_syscall_time_s + ptrace_overhead_s
        total_cycle_time_s = num_syscalls_per_cycle * effective_syscall_time_s

        watchdog_violated = total_cycle_time_s > watchdog_limit_sec

        return {
            "strace_enabled": enable_strace,
            "num_syscalls": num_syscalls_per_cycle,
            "total_cycle_time_s": total_cycle_time_s,
            "watchdog_limit_sec": watchdog_limit_sec,
            "watchdog_violated": watchdog_violated,
            "status": "WATCHDOG_KILL_SIGABRT" if watchdog_violated else "CYCLE_SUCCESS"
        }


if __name__ == "__main__":
    print("=== STRACE HEISENBUG VE WATCHDOG SABOTAJ TESTİ ===")
    
    # 1. Normal Çalışma (strace kapalı)
    normal = StraceOverheadSabotageLab.simulate_watchdog_timeout_induced_by_strace(enable_strace=False)
    print(f"[*] [Normal Çalışma] Döngü Süresi: {normal['total_cycle_time_s']*1000:.2f} ms | Durum: {normal['status']}")

    # 2. strace Takıldı (Canlı üretimde kontrolsüz teşhis)
    traced = StraceOverheadSabotageLab.simulate_watchdog_timeout_induced_by_strace(enable_strace=True)
    print(f"[*] [strace Altında] Döngü Süresi: {traced['total_cycle_time_s']*1000:.2f} ms | Durum: {traced['status']}")
    print(f"    -> SONUÇ: Servis {traced['total_cycle_time_s']:.2f}s sürdü ve {traced['watchdog_limit_sec']}s Watchdog limitini aşarak ÇÖKTÜ!")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Radar Telemetri Servisi strace Günlüğü Anomali Tespit Motoru
Otomatik Hata Sınıflandırma, Yavaş Syscall Tespiti ve Kök Neden Teşhisi
"""

from typing import List, Dict, Any

def analyze_strace_dump_for_anomalies(raw_lines: List[str], slow_threshold_us: float = 1000.0) -> Dict[str, Any]:
    """strace günlüğünü tarayarak sistem anomalilerini ve donma noktalarını tespit eder."""
    parser = StraceLogParser()
    anomalies = []
    
    for line in raw_lines:
        rec = parser.parse_line(line)
        if not rec:
            continue
            
        # Anomali 1: Hata üreten kritik syscall'lar
        if rec["is_error"] and rec["errno"] in ["ENOENT", "EACCES", "ECONNREFUSED", "EADDRINUSE"]:
            anomalies.append({
                "type": "CRITICAL_ERROR",
                "syscall": rec["syscall"],
                "reason": f"{rec['errno']} hatası alındı (Argümanlar: {rec['args']})",
                "duration_us": rec["duration_us"]
            })
            
        # Anomali 2: Eşik değerini aşan aşırı yavaş çağrılar (Blokaj tespiti)
        elif rec["duration_us"] > slow_threshold_us:
            anomalies.append({
                "type": "SLOW_SYSCALL_BLOCK",
                "syscall": rec["syscall"],
                "reason": f"Sistem çağrısı beklenmedik şekilde uzun sürdü ({rec['duration_us']:.1f} µs)",
                "duration_us": rec["duration_us"]
            })

    stats = parser.compute_summary_statistics()

    return {
        "total_parsed": len(parser.parsed_records),
        "total_anomalies": len(anomalies),
        "anomalies": anomalies,
        "summary": stats
    }


if __name__ == "__main__":
    print("=== STRACE ANOMALİ VE KÖK NEDEN TESPİT MOTORU ===")
    
    mock_dump = [
        'openat(AT_FDCWD, "/etc/radar/keys.pem", O_RDONLY) = -1 EACCES (Permission denied) <0.000025>',
        'epoll_wait(3, [], 64, 5000) = 0 <5.002100>',
        'connect(4, {sa_family=AF_INET, sin_port=htons(9001), sin_addr=inet_addr("192.168.1.50")}, 16) = -1 ECONNREFUSED <0.000350>',
        'write(1, "Radar Heartbeat OK\\n", 19) = 19 <0.000018>',
        'read(5, "", 4096) = 0 <0.000012>'
    ]

    report = analyze_strace_dump_for_anomalies(mock_dump, slow_threshold_us=2000.0)
    print(f"[*] Toplam Ayrıştırılan Syscall: {report['total_parsed']}")
    print(f"[*] Tespit Edilen Anomali Sayısı : {report['total_anomalies']}")
    print("\nAnomali Detayları:")
    for a in report["anomalies"]:
        print(f"  -> [{a['type']}] {a['syscall']}: {a['reason']}")


# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Kapsamlı Syscall Benchmark Laboratuvarı
Doğrudan Syscall vs ptrace İzlemeli Syscall Gecikmesi ve Çağrı Hacmi Karşılaştırması
"""

import numpy as np
from typing import Dict, Any

def run_syscall_tracing_benchmark() -> Dict[str, Any]:
    """Farklı syscall hacimleri için doğrudan yürütme ile strace izleme maliyetini karşılaştırır."""
    syscall_counts = np.array([1000, 5000, 10000, 25000, 50000, 100000], dtype=np.int64)
    
    native_latency_ns = 250.0   # 0.25 µs
    ptrace_latency_ns = 14500.0 # 14.5 µs (58x yavaşlama)

    native_times_ms = (syscall_counts * native_latency_ns) / 1e6
    traced_times_ms = (syscall_counts * ptrace_latency_ns) / 1e6

    speedup_ratio = traced_times_ms / native_times_ms

    return {
        "counts": syscall_counts,
        "native_times_ms": native_times_ms,
        "traced_times_ms": traced_times_ms,
        "slowdown_factor": speedup_ratio[0]
    }


if __name__ == "__main__":
    print("=== SYSCALL TRACING PERFORMANS BENCHMARK'I ===")
    bench = run_syscall_tracing_benchmark()
    print(f"{'Syscall Sayısı':>14} | {'Normal Süre (ms)':>18} | {'strace Süresi (ms)':>20} | {'Yavaşlama':>12}")
    print("-" * 72)
    for i, count in enumerate(bench["counts"]):
        n_t = bench["native_times_ms"][i]
        t_t = bench["traced_times_ms"][i]
        print(f"{count:>14,d} | {n_t:>18.2f} | {t_t:>20.2f} | {bench['slowdown_factor']:>11.1f}x")


# -*- coding: utf-8 -*-
"""
HÜCRE 20 (CODE 6): 4 Panelli 300 DPI Mühendislik Dashboard'u ve Katı Doğrulama Testleri
strace / ptrace Mekanizması, Gecikme Maliyeti ve Kök Neden Analizi Görselleştirmesi
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_102\gun_102_strace_ile_syscall_gozleme.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı strace mühendislik dashboard'u üretir."""
    fig, axes = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor("#0F172A")

    # Renk Paleti
    accent_blue = "#38BDF8"
    accent_green = "#4ADE80"
    accent_amber = "#FBBF24"
    accent_red = "#F87171"
    accent_purple = "#C084FC"
    text_color = "#F8FAFC"
    grid_color = "#334155"

    for ax_row in axes:
        for ax in ax_row:
            ax.set_facecolor("#1E293B")
            ax.tick_params(colors=text_color, labelsize=9)
            ax.grid(True, linestyle="--", alpha=0.3, color=grid_color)
            for spine in ax.spines.values():
                spine.set_color(grid_color)

    # -------------------------------------------------------------------------
    # Panel 1: Normal vs strace Syscall Gecikmesi (Logaritmik Bar Grafiği)
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    syscalls = ["read()", "write()", "openat()", "mmap()", "epoll_wait()"]
    t_native_ns = [220, 240, 1200, 1800, 450]
    t_traced_ns = [14200, 14800, 18500, 21000, 16500]

    x = np.arange(len(syscalls))
    width = 0.35

    ax1.bar(x - width/2, t_native_ns, width, color=accent_green, label="Doğrudan Syscall (~250 ns)")
    ax1.bar(x + width/2, t_traced_ns, width, color=accent_red, label="strace Altında (~16,000 ns - 60x Yavaş)")

    ax1.set_yscale("log")
    ax1.set_xticks(x)
    ax1.set_xticklabels(syscalls, color=text_color, fontsize=9.5, fontweight="bold")
    ax1.set_ylabel("Gecikme (ns - log scale)", color=text_color, fontsize=10)
    ax1.set_title("Panel 1: Doğrudan Syscall vs strace Ek Yükü (50x - 60x Darboğaz)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 2: strace -c Kümülatif Syscall Süre Dağılımı (Donut Grafiği)
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor("#0F172A")
    labels = ["epoll_wait\n(%62.4)", "read\n(%18.2)", "futex\n(%11.5)", "write\n(%5.8)", "openat / stat\n(%2.1)"]
    sizes = [62.4, 18.2, 11.5, 5.8, 2.1]
    pie_colors = [accent_blue, accent_green, accent_purple, accent_amber, accent_red]

    wedges, texts = ax2.pie(sizes, labels=labels, colors=pie_colors, startangle=140, 
                            wedgeprops=dict(width=0.45, edgecolor="#0F172A", linewidth=2),
                            textprops=dict(color=text_color, fontsize=9, fontweight="bold"))
    ax2.set_title("Panel 2: strace -c Kümülatif Çekirdek Zamanı Dağılımı", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # -------------------------------------------------------------------------
    # Panel 3: Linux ptrace Syscall Trap Şeması (Diagram)
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)
    ax3.axis("off")
    ax3.set_title("Panel 3: Linux ptrace(2) İki Aşamalı Syscall Yakalama Akışı", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # Kullanıcı Süreci Kutusu
    rect_u = plt.Rectangle((0.5, 5.5), 4.0, 3.5, facecolor="#0369A1", edgecolor=accent_blue, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_u)
    ax3.text(2.5, 8.2, "İZLENEN SÜREÇ (Tracee)", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(2.5, 7.0, "1. syscall openat()\n2. Çekirdek Tarafından Durdurulur\n3. Devam Eder -> Dönüş Alır", ha="center", color="#BAE6FD", fontsize=8)

    # strace Süreci Kutusu
    rect_s = plt.Rectangle((5.5, 5.5), 4.0, 3.5, facecolor="#047857", edgecolor=accent_green, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_s)
    ax3.text(7.5, 8.2, "GÖZLEMCİ (strace)", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(7.5, 7.0, "1. SIGTRAP ile Uyanır\n2. Register'ları İnceler (rax, rdi)\n3. PTRACE_SYSCALL Gönderir", ha="center", color="#A7F3D0", fontsize=8)

    # Çekirdek Alanı Kutusu
    rect_k = plt.Rectangle((1.5, 1.0), 7.0, 3.0, facecolor="#334155", edgecolor=accent_amber, linewidth=2.2, transform=ax3.transData)
    ax3.add_patch(rect_k)
    ax3.text(5.0, 3.2, "LINUX ÇEKİRDEĞİ (KERNEL SPACE)", ha="center", color=accent_amber, fontsize=10, fontweight="bold")
    ax3.text(5.0, 2.2, "[Syscall-Enter-Stop] -> 2 x Context Switch\n[Syscall-Exit-Stop]  -> 2 x Context Switch", ha="center", color=text_color, fontsize=8.5)
    ax3.text(5.0, 1.4, "Toplam: 4 Context Switch / Syscall!", ha="center", color=accent_red, fontsize=8.5, fontweight="bold")

    # Oklar
    ax3.annotate("", xy=(3.0, 4.0), xytext=(2.5, 5.5), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax3.annotate("", xy=(7.0, 5.5), xytext=(6.5, 4.0), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))

    # -------------------------------------------------------------------------
    # Panel 4: strace Kaynaklı Heisenbug ve Watchdog İhlali
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    cycle_indices = np.arange(1, 11)
    
    # 1'den 5'e kadar normal çalışma (20 ms)
    # 6'dan itibaren strace takıldı -> 1,250 ms'ye fırladı
    cycle_durations = np.array([22, 19, 25, 20, 21, 1250, 1280, 1240, 1290, 1260])

    colors_bar = [accent_green if d < 1000 else accent_red for d in cycle_durations]
    ax4.bar(cycle_indices, cycle_durations, color=colors_bar, width=0.6, edgecolor="#0F172A", linewidth=1.5)

    ax4.axhline(1000, color=accent_amber, linestyle="--", linewidth=2.0, label="WatchdogSec=1.0s Limiti (1000 ms)")
    
    ax4.text(3, 100, "Normal Çalışma\n(~20 ms)", ha="center", color=accent_green, fontsize=9, fontweight="bold")
    ax4.text(8, 1400, "strace Takıldı!\n(Watchdog Aşımı: SIGABRT)", ha="center", color=accent_red, fontsize=9, fontweight="bold")

    ax4.set_title("Panel 4: strace Ek Yükü Kaynaklı Aviyonik Watchdog İhlali", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax4.set_xlabel("Radar Döngü Numarası", color=text_color, fontsize=10)
    ax4.set_ylabel("Döngü Süresi (Milisaniye)", color=text_color, fontsize=10)
    ax4.set_ylim(0, 1600)
    ax4.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_path}")


def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Gün 102 için tüm mimari ve matematiksel kabulleri katı testlerle doğrular."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dashboard Görsel Doğrulaması
    assert os.path.exists(png_path), f"HATA: Dashboard görseli mevcut değil: {png_path}"
    file_size = os.path.getsize(png_path)
    assert file_size > 100_000, f"HATA: Dashboard boyutu şüpheli ({file_size} bayt)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {file_size:,} bayt.")

    # 2. strace Ayrıştırıcı Doğrulaması
    parser = StraceLogParser()
    rec = parser.parse_line('openat(AT_FDCWD, "/etc/radar.conf", O_RDONLY) = -1 ENOENT <0.000045>')
    assert rec is not None, "HATA: openat satırı ayrıştırılamadı!"
    assert rec["syscall"] == "openat", "HATA: Syscall ismi hatalı!"
    assert rec["is_error"] is True, "HATA: ENOENT hatası tespit edilemedi!"
    assert rec["duration_us"] == 45.0, "HATA: Süre mikrosaniyeye dönüştürülemedi!"
    print("  [+] strace Log Regex Ayrıştırma ve Hata Tespiti Doğrulandı.")

    # 3. ptrace Gecikme Ek Yükü Doğrulaması
    bench = run_syscall_tracing_benchmark()
    assert bench["slowdown_factor"] > 30.0, f"HATA: strace ek yükü en az 30x olmalıdır ({bench['slowdown_factor']:.1f}x)!"
    print(f"  [+] ptrace 4 Context Switch Yavaşlama Çarpanı Doğrulandı ({bench['slowdown_factor']:.1f}x).")

    # 4. Watchdog Aşımı Simülasyonu Doğrulaması
    res = StraceOverheadSabotageLab.simulate_watchdog_timeout_induced_by_strace(enable_strace=True)
    assert res["watchdog_violated"] is True, "HATA: strace altında Watchdog aşımı gerçekleşmelidir!"
    assert res["status"] == "WATCHDOG_KILL_SIGABRT", "HATA: Watchdog aşımı SIGABRT üretmelidir!"
    print("  [+] strace Kaynaklı Heisenbug ve Watchdog İnfazı Doğrulandı.")

    # 5. Kök Neden Anomali Motoru Doğrulaması
    anom_res = analyze_strace_dump_for_anomalies([
        'connect(4, {sa_family=AF_INET, sin_port=htons(8080)}, 16) = -1 ECONNREFUSED <0.000200>',
        'read(3, "DATA", 4) = 4 <0.000010>'
    ])
    assert anom_res["total_anomalies"] == 1, "HATA: ECONNREFUSED anomalisi yakalanamadı!"
    assert anom_res["anomalies"][0]["syscall"] == "connect"
    print("  [+] Otomatik Kök Neden Anomali Sınıflandırıcısı Doğrulandı.")

    print("\n[PASS] Gün 102: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
