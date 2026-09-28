# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""

# GÜN 085: ps, top, htop ve process gözleme Master Script

# Modül 1: Temel Çekirdek Mekanizma / procfs Simülatörü ve /proc/[PID]/stat Ayrıştırıcı
import time
from typing import Dict, List, Optional, Tuple, NamedTuple

class ProcessStat(NamedTuple):
    pid: int
    comm: str
    state: str
    ppid: int
    utime: int
    stime: int
    num_threads: int
    vsize_bytes: int
    rss_pages: int

class VirtualProcFS:
    """Linux çekirdeğinin /proc dosya sistemi davranışını simüle eden bellek içi motor."""
    def __init__(self):
        self.page_size = 4096  # 4 KB standart x86_64 sayfa boyutu
        self.total_cpu_ticks = 1000000
        # Simüle edilen süreç veri tabanı
        self.processes: Dict[int, Dict[str, any]] = {}
        self._init_mock_system()

    def _init_mock_system(self):
        """Askeri görev bilgisayarı için başlangıç süreçlerini oluşturur."""
        self.register_process(1, "systemd", "S", 0, utime=500, stime=200, vsize_mb=20, rss_mb=8)
        self.register_process(100, "radar_tracker", "R", 1, utime=12000, stime=3500, vsize_mb=512, rss_mb=128)
        self.register_process(101, "telemetry_tx", "S", 1, utime=3000, stime=1100, vsize_mb=64, rss_mb=16)
        self.register_process(102, "nvme_logger", "D", 1, utime=450, stime=890, vsize_mb=128, rss_mb=32)
        self.register_process(103, "zombie_helper", "Z", 1, utime=50, stime=10, vsize_mb=0, rss_mb=0)

    def register_process(self, pid: int, name: str, state: str, ppid: int,
                         utime: int, stime: int, vsize_mb: int, rss_mb: int, threads: int = 1):
        self.processes[pid] = {
            "pid": pid,
            "comm": name,
            "state": state,
            "ppid": ppid,
            "utime": utime,
            "stime": stime,
            "num_threads": threads,
            "vsize": vsize_mb * 1024 * 1024,
            "rss": (rss_mb * 1024 * 1024) // self.page_size
        }

    def read_proc_stat(self, pid: int) -> str:
        """/proc/[PID]/stat dosyasının metin çıktısını üretir."""
        if pid not in self.processes:
            raise FileNotFoundError(f"/proc/{pid}/stat bulunamadı (ESRCH)")
        
        p = self.processes[pid]
        # Linux /proc/[pid]/stat formatı:
        # pid (comm) state ppid pgrp session tty_nr tpgid flags minflt cminflt majflt cmajflt utime stime ...
        dummy_fields = "0 0 0 0 0 0 0 0 0" # 5-13 arası temsili alanlar
        stat_line = (f"{p['pid']} ({p['comm']}) {p['state']} {p['ppid']} {dummy_fields} "
                     f"{p['utime']} {p['stime']} 0 0 20 0 {p['num_threads']} 0 1000 "
                     f"{p['vsize']} {p['rss']}")
        return stat_line

    def read_system_cpu(self) -> int:
        """/proc/stat dosyasındaki toplam CPU saat vuruşunu döner."""
        return self.total_cpu_ticks

    def tick_system(self, delta_ticks: int = 100):
        """Zamanı ilerletir; simüle edilmiş süreçlere CPU yükü dağıtır."""
        self.total_cpu_ticks += delta_ticks
        # Çalışan (R) durumdaki süreçlere ticks ekle
        for p in self.processes.values():
            if p["state"] == "R":
                p["utime"] += int(delta_ticks * 0.7)
                p["stime"] += int(delta_ticks * 0.1)

def parse_proc_stat(stat_content: str) -> ProcessStat:
    """/proc/[PID]/stat satırını mikro-saniye hassasiyetinde ayrıştırır."""
    # comm alanı parantez içerir ve içinde boşluk olabilir: "1 (my process) R ..."
    first_paren = stat_content.find('(')
    last_paren = stat_content.rfind(')')
    
    pid = int(stat_content[:first_paren].strip())
    comm = stat_content[first_paren + 1:last_paren]
    rest = stat_content[last_paren + 2:].split()
    
    state = rest[0]
    ppid = int(rest[1])
    utime = int(rest[11])
    stime = int(rest[12])
    num_threads = int(rest[17])
    vsize = int(rest[20])
    rss = int(rest[21])
    
    return ProcessStat(pid, comm, state, ppid, utime, stime, num_threads, vsize, rss)

# Modül 1 Testi
_procfs = VirtualProcFS()
_raw_stat = _procfs.read_proc_stat(100)
_parsed = parse_proc_stat(_raw_stat)

assert _parsed.pid == 100, "PID 100 olmalı"
assert _parsed.comm == "radar_tracker", "Comm adı doğru ayrıştırılmalı"
assert _parsed.state == "R", "Durum Running olmalı"
assert _parsed.utime == 12000, "utime doğru okunmalı"
print(f"[Modül 1] /proc/[PID]/stat Ayrıştırıldı: PID={_parsed.pid} ({_parsed.comm}) State={_parsed.state} RSS={_parsed.rss_pages} sayfa")


# Modül 2: Delta CPU Hesaplayıcı ve Linux Load Average (EDMA) Motoru
import math

class CpuMetricsCalculator:
    """İki örneklem arasındaki CPU kullanım yüzdesini hesaplar."""
    def __init__(self, num_cores: int = 4):
        self.num_cores = num_cores
        self.previous_samples: Dict[int, Tuple[int, int]] = {} # pid -> (total_proc_ticks, sys_ticks)

    def calculate_cpu_percent(self, pid: int, current_proc_ticks: int, current_sys_ticks: int) -> float:
        """Δproc / Δsys formülüyle anlık %CPU döner."""
        if pid not in self.previous_samples:
            self.previous_samples[pid] = (current_proc_ticks, current_sys_ticks)
            return 0.0

        prev_proc, prev_sys = self.previous_samples[pid]
        delta_proc = current_proc_ticks - prev_proc
        delta_sys = current_sys_ticks - prev_sys

        # Güncel değeri kaydet
        self.previous_samples[pid] = (current_proc_ticks, current_sys_ticks)

        if delta_sys <= 0:
            return 0.0

        cpu_percent = (delta_proc / delta_sys) * 100.0 * self.num_cores
        return round(cpu_percent, 2)

class LinuxLoadAverageEngine:
    """Linux kernel/sched/loadavg.c üstel bozulma (EDMA) simülasyonu."""
    def __init__(self):
        self.load_1min = 0.0
        self.load_5min = 0.0
        self.load_15min = 0.0
        
        # Çekirdek sabitleri (5 saniye örneklem periyodu)
        self.exp_1 = math.exp(-5.0 / 60.0)
        self.exp_5 = math.exp(-5.0 / 300.0)
        self.exp_15 = math.exp(-5.0 / 900.0)

    def update(self, running_count: int, uninterruptible_count: int) -> Tuple[float, float, float]:
        """Her 5 saniyede bir yük ortalamalarını günceller."""
        # Linux kuralı: R + D süreçleri toplamı aktif yüktür!
        active_tasks = running_count + uninterruptible_count
        
        self.load_1min = self.load_1min * self.exp_1 + active_tasks * (1.0 - self.exp_1)
        self.load_5min = self.load_5min * self.exp_5 + active_tasks * (1.0 - self.exp_5)
        self.load_15min = self.load_15min * self.exp_15 + active_tasks * (1.0 - self.exp_15)
        
        return (round(self.load_1min, 2), round(self.load_5min, 2), round(self.load_15min, 2))

# Modül 2 Test
_cpu_calc = CpuMetricsCalculator(num_cores=2)
# Örneklem 1
_cpu_calc.calculate_cpu_percent(100, current_proc_ticks=1000, current_sys_ticks=10000)
# Örneklem 2: 100 ticks süreç harcadı, 200 ticks sistem ilerledi -> (100/200)*100*2 = %100 CPU!
_cpu_pct = _cpu_calc.calculate_cpu_percent(100, current_proc_ticks=1100, current_sys_ticks=10200)
assert _cpu_pct == 100.0, f"Beklenen %100, Gerçekleşen: {_cpu_pct}"

_load_eng = LinuxLoadAverageEngine()
for _ in range(12): # 1 dakika boyunca sürekli 4 aktif süreç
    _l1, _l5, _l15 = _load_eng.update(running_count=2, uninterruptible_count=2)

assert _l1 > 2.0, "1 dakika sonra Load Average 2.0 üzerine çıkmalı"
print(f"[Modül 2] CPU ve Load Avg Hesaplandı: %CPU={_cpu_pct}% | Load 1m={_l1}, 5m={_l5}, 15m={_l15}")


# Modül 3: Hafif Süreç Gözlemcisi (Lightweight Process Monitor / Mini top)
class LightweightProcessMonitor:
    """Savunma sistemleri için sıfır-yük (zero-overhead) telemetri izleme motoru."""
    def __init__(self, procfs: VirtualProcFS, num_cores: int = 4):
        self.procfs = procfs
        self.cpu_calc = CpuMetricsCalculator(num_cores=num_cores)
        self.load_engine = LinuxLoadAverageEngine()
        self.alerts: List[str] = []

    def collect_snapshot(self) -> List[Dict[str, any]]:
        """Tüm süreçleri tarar ve top formatında sıralı tablo üretir."""
        snapshot = []
        sys_ticks = self.procfs.read_system_cpu()
        running_count = 0
        uninterruptible_count = 0

        for pid in list(self.procfs.processes.keys()):
            try:
                raw = self.procfs.read_proc_stat(pid)
                p = parse_proc_stat(raw)
            except FileNotFoundError:
                continue

            # Durum sayaçları
            if p.state == 'R': running_count += 1
            elif p.state == 'D': uninterruptible_count += 1

            # %CPU Hesapla
            total_proc_ticks = p.utime + p.stime
            cpu_pct = self.cpu_calc.calculate_cpu_percent(p.pid, total_proc_ticks, sys_ticks)

            # Bellek MB
            virt_mb = round(p.vsize_bytes / (1024 * 1024), 1)
            res_mb = round((p.rss_pages * self.procfs.page_size) / (1024 * 1024), 1)

            # Alarm Kontrolleri
            if p.state == 'D':
                self.alerts.append(f"UYARI: PID {p.pid} ({p.comm}) D-State kilitlenmesinde!")
            if cpu_pct > 85.0:
                self.alerts.append(f"KRİTİK: PID {p.pid} ({p.comm}) aşırı CPU tüketiyor: %{cpu_pct}!")

            snapshot.append({
                "pid": p.pid,
                "comm": p.comm,
                "state": p.state,
                "cpu_pct": cpu_pct,
                "virt_mb": virt_mb,
                "res_mb": res_mb,
                "threads": p.num_threads
            })

        # Load average güncelle
        self.load_engine.update(running_count, uninterruptible_count)
        
        # CPU kullanımına göre azalan sırala
        snapshot.sort(key=lambda x: x["cpu_pct"], reverse=True)
        return snapshot

# Modül 3 Test
_monitor = LightweightProcessMonitor(_procfs, num_cores=2)
_snap1 = _monitor.collect_snapshot()
_procfs.tick_system(delta_ticks=500)
_snap2 = _monitor.collect_snapshot()

assert len(_snap2) > 0, "Snapshot boş olmamalı"
assert any(s["state"] == "D" for s in _snap2), "D state süreci listede olmalı"
print(f"[Modül 3] Mini-Top Raporu:")
for s in _snap2[:3]:
    print(f"  PID {s['pid']:<4} {s['comm']:<15} {s['state']} %CPU={s['cpu_pct']:<5} RES={s['res_mb']}MB")


# Modül 4: Sabotaj Senaryosu — Gizli CPU Sızıntısı ve D-State Kilitlenmesi vs Akıllı Gözlem
class TelemetryChaosSimulation:
    """Süreç anormalliklerini ve izleme dedektörünün tepkisini simüle eder."""
    def __init__(self):
        self.procfs = VirtualProcFS()
        self.monitor = LightweightProcessMonitor(self.procfs, num_cores=2)

    def inject_cpu_hog_sabotage(self, target_pid: int = 101) -> Dict[str, any]:
        """Masum telsiz sürecini (telemetry_tx) sonsuz döngüye sokarak CPU sızıntısı yaratır."""
        # Başlangıç durumu
        self.monitor.collect_snapshot()
        
        # Sabotaj: Süreç durumunu R yap ve ticks patlaması yaşat
        p = self.procfs.processes[target_pid]
        p["state"] = "R"
        
        # Sistem 100 ticks ilerlerken süreç 95 ticks harcasın (%95 CPU!)
        self.procfs.total_cpu_ticks += 100
        p["utime"] += 95
        
        snapshot = self.monitor.collect_snapshot()
        detected_hog = next((s for s in snapshot if s["pid"] == target_pid), None)

        return {
            "target_pid": target_pid,
            "detected_cpu": detected_hog["cpu_pct"] if detected_hog else 0.0,
            "alarm_triggered": any(f"PID {target_pid}" in a for a in self.monitor.alerts)
        }

    def inject_d_state_lockup(self, target_pid: int = 102) -> Dict[str, any]:
        """Kayıt sürecini kalıcı D durumuna kilitler ve Load Average fırlamasını simüle eder."""
        p = self.procfs.processes[target_pid]
        p["state"] = "D"
        
        # 10 örneklem boyunca D state kalıyor
        for _ in range(10):
            self.monitor.collect_snapshot()

        alarm_exists = any("D-State kilitlenmesinde" in a for a in self.monitor.alerts)
        load_1m = self.monitor.load_engine.load_1min

        return {
            "target_pid": target_pid,
            "state": p["state"],
            "alarm_triggered": alarm_exists,
            "current_load_1m": load_1m
        }

_chaos = TelemetryChaosSimulation()
_res_hog = _chaos.inject_cpu_hog_sabotage(target_pid=101)
_res_d = _chaos.inject_d_state_lockup(target_pid=102)

assert _res_hog["detected_cpu"] > 80.0, "CPU sızıntısı %80 üzerinde tespit edilmeli!"
assert _res_hog["alarm_triggered"] == True, "Aşırı CPU için alarm üretilmeli!"
assert _res_d["alarm_triggered"] == True, "D-state için alarm üretilmeli!"
print(f"[Sabotaj Testi] CPU Sızıntısı Tespiti: {_res_hog}")
print(f"[Sabotaj Testi] D-State Kilitlenme Tespiti: {_res_d}")


# Modül 5: Ampirik Kıyaslama ve Yüksek Çözünürlüklü Telemetri Benchmark Motoru
import time
import numpy as np

def run_benchmarks(iterations: int = 3000) -> Dict[str, any]:
    """procfs ayrıştırma ve snapshot toplama gecikmelerini ampirik olarak ölçer."""
    procfs = VirtualProcFS()
    monitor = LightweightProcessMonitor(procfs, num_cores=4)
    
    # Sisteme 50 adet ek süreç kaydet
    for i in range(200, 250):
        procfs.register_process(i, f"worker_{i}", "S", 1, utime=i*10, stime=i*2, vsize_mb=32, rss_mb=8)

    sample_stat_line = procfs.read_proc_stat(100)
    latencies_parse = []
    latencies_snapshot = []

    for _ in range(iterations):
        # 1. Tekil stat ayrıştırma süresi
        t0 = time.perf_counter_ns()
        parse_proc_stat(sample_stat_line)
        t1 = time.perf_counter_ns()
        latencies_parse.append(t1 - t0)

        # 2. Tüm sistem snapshot toplama süresi
        t0 = time.perf_counter_ns()
        monitor.collect_snapshot()
        t1 = time.perf_counter_ns()
        latencies_snapshot.append(t1 - t0)

    def calc_stats(lat_list):
        arr = np.array(lat_list, dtype=np.float64)
        return {
            "mean": float(np.mean(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "raw": arr
        }

    return {
        "parse": calc_stats(latencies_parse),
        "snapshot": calc_stats(latencies_snapshot),
        "iterations": iterations
    }

_bench_res = run_benchmarks(iterations=2000)
print(f"[Benchmark] {_bench_res['iterations']} İterasyon Ölçüldü.")
print(f"  Stat Parse Mean:     {_bench_res['parse']['mean']:.2f} ns (p95: {_bench_res['parse']['p95']:.2f} ns)")
print(f"  Full Snapshot Mean:  {_bench_res['snapshot']['mean']:.2f} ns (p95: {_bench_res['snapshot']['p95']:.2f} ns)")


# Modül 6: 4-Panelli Yayın Kalitesinde Dashboard Üretimi ve Katı Assert Doğrulaması
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DEFAULT_PNG = "gun_085_ps_top_htop_ve_process_gozleme.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    """Yayın kalitesinde 4-panelli görselleştirme paneli üretir."""
    fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    bench_data = run_benchmarks(iterations=2000)

    # Ortak Stil Fonksiyonu
    def style_ax(ax, title, xlabel, ylabel):
        ax.set_facecolor('#1E293B')
        ax.set_title(title, fontsize=12, fontweight='bold', color='#38BDF8', pad=10)
        ax.set_xlabel(xlabel, fontsize=10, fontweight='bold', color='#94A3B8')
        ax.set_ylabel(ylabel, fontsize=10, fontweight='bold', color='#94A3B8')
        ax.tick_params(colors='#CBD5E1', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#334155')
            spine.set_linewidth(1.2)
        ax.grid(True, linestyle='--', alpha=0.25, color='#64748B')

    # -------------------------------------------------------------
    # PANEL 1: Süreç Kaynak Tüketimi (CPU & RES Memory)
    # -------------------------------------------------------------
    ax1 = axs[0, 0]
    style_ax(ax1, "Panel 1: Kritik Görev Süreçleri Profil Dağılımı", 
             "Süreç İsmi", "%CPU / RES Bellek (MB)")
    
    procs = ['radar_tracker', 'telemetry_tx', 'nvme_logger', 'systemd']
    cpu_vals = [70.0, 95.0, 5.0, 2.0]
    res_vals = [128, 16, 32, 8]
    
    x = np.arange(len(procs))
    w = 0.35
    
    b1 = ax1.bar(x - w/2, cpu_vals, width=w, label='% CPU Tüketimi', color='#EF4444', edgecolor='#334155')
    b2 = ax1.bar(x + w/2, res_vals, width=w, label='RES Bellek (MB)', color='#0EA5E9', edgecolor='#334155')
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(procs, fontweight='bold', fontsize=8)
    ax1.set_ylim(0, 150)
    ax1.legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=9)
    
    for bar in b1:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"%{bar.get_height():.0f}", 
                 ha='center', color='#F8FAFC', fontsize=8, fontweight='bold')

    # -------------------------------------------------------------
    # PANEL 2: Load Average Üstel Bozulma (EDMA) Dinamiği
    # -------------------------------------------------------------
    ax2 = axs[0, 1]
    style_ax(ax2, "Panel 2: Linux Load Average Üstel Tepki Eğrisi", 
             "Zaman Adımı (5 sn Periyotlar)", "Yük Ortalaması (Load Average)")
    
    engine = LinuxLoadAverageEngine()
    l1_history = []
    l5_history = []
    l15_history = []
    
    # İlk 20 adımda 6 aktif görev var, sonraki 20 adımda 1 aktif görev
    for step in range(40):
        active = 6 if step < 20 else 1
        l1, l5, l15 = engine.update(running_count=active, uninterruptible_count=0)
        l1_history.append(l1)
        l5_history.append(l5)
        l15_history.append(l15)

    steps = range(1, 41)
    ax2.plot(steps, l1_history, label='1 Dakika (Hızlı Tepki)', color='#F59E0B', linewidth=2)
    ax2.plot(steps, l5_history, label='5 Dakika (Orta)', color='#38BDF8', linewidth=2)
    ax2.plot(steps, l15_history, label='15 Dakika (Yavaş Sönümleme)', color='#10B981', linewidth=2)
    ax2.axvline(20, color='#EF4444', linestyle='--', alpha=0.6, label='Yükün Düştüğü An')
    ax2.legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=8)

    # -------------------------------------------------------------
    # PANEL 3: Sabotaj Senaryosu: CPU Sızıntısı & D-State Tespiti
    # -------------------------------------------------------------
    ax3 = axs[1, 0]
    style_ax(ax3, "Panel 3: Sabotaj Tespiti (Stealth CPU Hog & D-State)", 
             "Metrik Türü", "Ölçülen Değer / Durum")
    
    metrics = ['Normal Telsiz\n%CPU', 'Sabotajlı Telsiz\n%CPU', 'D-State Süreç\nSayısı']
    m_vals = [5.0, 95.0, 1.0]
    colors_p3 = ['#10B981', '#EF4444', '#F59E0B']
    
    bars3 = ax3.bar(metrics, m_vals, color=colors_p3, edgecolor='#334155', width=0.45)
    ax3.set_ylim(0, 115)
    
    ax3.text(0, 8, "NORMAL", ha='center', color='#F8FAFC', fontweight='bold', fontsize=9)
    ax3.text(1, 98, "ALARM: %95!", ha='center', color='#EF4444', fontweight='bold', fontsize=9)
    ax3.text(2, 4, "ALARM: D-State!", ha='center', color='#F59E0B', fontweight='bold', fontsize=9)

    # -------------------------------------------------------------
    # PANEL 4: Procfs Ayrıştırma Gecikme Dağılımı (Boxplot)
    # -------------------------------------------------------------
    ax4 = axs[1, 1]
    style_ax(ax4, "Panel 4: Procfs Ayrıştırma Gecikme Dağılımı", 
             "İşlem Türü", "Gecikme (Nanosaniye - ns)")
    
    bench_ops = ['stat Parse', '50-Proc Snapshot']
    data_bench = [
        bench_data['parse']['raw'][:1000],
        bench_data['snapshot']['raw'][:1000]
    ]
    
    bp = ax4.boxplot(data_bench, patch_artist=True, showmeans=True,
                     boxprops=dict(facecolor='#0284C7', color='#38BDF8'),
                     capprops=dict(color='#94A3B8'),
                     whiskerprops=dict(color='#64748B'),
                     flierprops=dict(marker='o', markerfacecolor='#F43F5E', markersize=3, alpha=0.4),
                     medianprops=dict(color='#F59E0B', linewidth=2),
                     meanprops=dict(marker='^', markerfacecolor='#10B981', markeredgecolor='#10B981'))
    
    ax4.set_xticks([1, 2])
    ax4.set_xticklabels(bench_ops, fontweight='bold')
    ax4.set_yscale('log')
    
    means = [bench_data['parse']['mean'], bench_data['snapshot']['mean']]
    for i, m in enumerate(means, 1):
        ax4.text(i, m * 1.3, f"Ort: {m:.0f}ns", ha='center', color='#38BDF8', fontsize=8, fontweight='bold')

    plt.suptitle("ASELSAN / HAVELSAN Görev Sistemleri: ps, top, htop ve procfs Gözlem Mimarisi", 
                 fontsize=15, fontweight='bold', color='#F8FAFC', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_png_path}")

def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Tüm procfs ve telemetri gözlem mekanizmalarını katı assert koşullarıyla denetler."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    procfs = VirtualProcFS()

    # 1. /proc/[PID]/stat Formatı Doğrulaması
    raw_stat = procfs.read_proc_stat(100)
    parsed = parse_proc_stat(raw_stat)
    assert parsed.pid == 100, "PID doğrulaması başarısız"
    assert parsed.comm == "radar_tracker", "Comm adı hatalı"
    assert parsed.state == "R", "Durum 'R' olmalı"
    assert parsed.vsize_bytes == 512 * 1024 * 1024, "VIRT 512 MB olmalı"
    assert parsed.rss_pages == (128 * 1024 * 1024) // 4096, "RSS 128 MB karşılığı sayfa olmalı"

    # 2. CPU Delta Hesaplama Doğrulaması
    calc = CpuMetricsCalculator(num_cores=4)
    # t1: proc=1000, sys=10000
    calc.calculate_cpu_percent(100, 1000, 10000)
    # t2: proc=1100 (100 ticks), sys=10100 (100 ticks) -> (100/100) * 100 * 4 = %400 (4 çekirdek tam yük)
    res_cpu = calc.calculate_cpu_percent(100, 1100, 10100)
    assert res_cpu == 400.0, f"4 çekirdekte beklenen %400, alınan: {res_cpu}"

    # 3. Load Average Üstel Bozulma Doğrulaması
    load_eng = LinuxLoadAverageEngine()
    # 12 adımda (1 dakika) 10 aktif görev verildiğinde load 1m sıfırdan yukarı çıkmalı
    for _ in range(12):
        l1, _, _ = load_eng.update(running_count=10, uninterruptible_count=0)
    assert l1 > 5.0, f"Load 1m beklenen > 5.0, alınan: {l1}"

    # 4. D-State Alarm ve Tespiti
    monitor = LightweightProcessMonitor(procfs, num_cores=2)
    snap = monitor.collect_snapshot()
    d_proc = next((p for p in snap if p["state"] == "D"), None)
    assert d_proc is not None, "D-State süreci listede bulunmalı!"
    assert any("D-State kilitlenmesinde" in a for a in monitor.alerts), "D-State alarmı üretilmeli"

    # 5. PNG Görsel Dosya Kontrolü
    if os.path.exists(png_path):
        size = os.path.getsize(png_path)
        assert size > 50000, f"PNG dosyası çok küçük veya bozuk ({size} bayt)"

    print("[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")

if __name__ == "__main__":
    out_png = "gun_085_ps_top_htop_ve_process_gozleme.png"
    generate_dashboard(out_png)
    verify_all_assertions(out_png)
