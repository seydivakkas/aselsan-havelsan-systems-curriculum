# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 4 (CODE 1): procfs Simülasyon Motoru ve Süreç Metrik Üreticisi
Süreç Tablosu, /proc/PID/stat ve /proc/PID/status Çekirdek Üreticisi
"""

import time
from typing import Dict, List, Any, Optional

class SimulatedProcess:
    """Linux çekirdeğindeki struct task_struct yapısının simülasyonu."""
    def __init__(self, pid: int, comm: str, ppid: int = 1, state: str = "S"):
        self.pid = pid
        self.comm = comm # Süreç adı (Boşluk içerebilir!)
        self.ppid = ppid
        self.state = state
        self.utime = 150 # Kullanıcı modu saat vuruşu (ticks)
        self.stime = 45  # Çekirdek modu saat vuruşu
        self.cutime = 0
        self.cstime = 0
        self.priority = 20
        self.nice = 0
        self.num_threads = 4
        self.starttime = int(time.time() * 100)
        self.vsize = 104857600  # 100 MB sanal bellek
        self.rss = 12500        # Sayfa sayısı (12500 * 4KB = 50 MB)
        self.open_fds = {0: "/dev/null", 1: "/var/log/app.log", 2: "/var/log/app.err", 3: "socket:[40960]"}

    def generate_stat_line(self) -> str:
        """Linux /proc/PID/stat formatına birebir uygun 52 alanlık satır üretir."""
        fields = [
            str(self.pid),
            f"({self.comm})", # Alan 2 daima parantez içindedir
            self.state,
            str(self.ppid),
            "1000", "1000", "0", "0", "0", "0", "0", "0", "0",
            str(self.utime),
            str(self.stime),
            str(self.cutime),
            str(self.cstime),
            str(self.priority),
            str(self.nice),
            str(self.num_threads),
            "0",
            str(self.starttime),
            str(self.vsize),
            str(self.rss),
            "18446744073709551615" # rsslim
        ]
        # Kalan alanlar için varsayılan sıfırlar ekle
        while len(fields) < 52:
            fields.append("0")
        return " ".join(fields)

    def generate_status_text(self) -> str:
        """Linux /proc/PID/status insan-okunabilir formatı üretir."""
        rss_kb = (self.rss * 4096) // 1024
        vsize_kb = self.vsize // 1024
        return (
            f"Name:\t{self.comm}\n"
            f"State:\t{self.state} (simulated)\n"
            f"Tgid:\t{self.pid}\n"
            f"Pid:\t{self.pid}\n"
            f"PPid:\t{self.ppid}\n"
            f"VmSize:\t{vsize_kb:8d} kB\n"
            f"VmRSS:\t{rss_kb:8d} kB\n"
            f"Threads:\t{self.num_threads}\n"
            f"voluntary_ctxt_switches:\t18204\n"
            f"nonvoluntary_ctxt_switches:\t452\n"
        )

# Test çalıştırması
if __name__ == "__main__":
    proc = SimulatedProcess(pid=1420, comm="telemetry worker", ppid=1, state="S")
    stat_raw = proc.generate_stat_line()
    print("=== [SIMÜLE EDİLMİŞ /proc/1420/stat ÇIKTISI] ===")
    print(stat_raw[:120] + " ... [TOPLAM 52 ALAN]")
    print("\n=== [SIMÜLE EDİLMİŞ /proc/1420/status ÇIKTISI] ===")
    print(proc.generate_status_text())


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Python ile Üretim Seviyesi ProcObserver Motoru
Güvenli Parantez Çözümleme, CPU Oranı ve Bellek Telemetrisi Hesaplayıcı
"""

from typing import Dict, Any, Optional

class ProcObserver:
    """Linux /proc/PID/stat ve /proc/stat ayrıştırma ve gözlem motoru."""
    
    @staticmethod
    def parse_stat_line(raw_line: str) -> Dict[str, Any]:
        """Süreç adındaki boşluk ve parantez tuzaklarına bağışık ayrıştırıcı."""
        raw_line = raw_line.strip()
        open_paren = raw_line.find("(")
        close_paren = raw_line.rfind(")")
        
        if open_paren == -1 or close_paren == -1 or close_paren < open_paren:
            raise ValueError(f"Geçersiz stat satır formatı: {raw_line}")
            
        pid = int(raw_line[:open_paren].strip())
        comm = raw_line[open_paren + 1 : close_paren]
        rest = raw_line[close_paren + 1 :].strip().split()
        
        # POSIX stat alan indeksleri (0 tabanlı rest listesi):
        # rest[0]  -> state (Field 3)
        # rest[1]  -> ppid (Field 4)
        # rest[11] -> utime (Field 14)
        # rest[12] -> stime (Field 15)
        # rest[17] -> num_threads (Field 20)
        # rest[20] -> vsize (Field 23)
        # rest[21] -> rss (Field 24)
        
        state = rest[0]
        ppid = int(rest[1])
        utime = int(rest[11])
        stime = int(rest[12])
        num_threads = int(rest[17])
        vsize_bytes = int(rest[20])
        rss_pages = int(rest[21])
        rss_bytes = rss_pages * 4096

        return {
            "pid": pid,
            "comm": comm,
            "state": state,
            "ppid": ppid,
            "utime": utime,
            "stime": stime,
            "total_time": utime + stime,
            "num_threads": num_threads,
            "vsize_mb": vsize_bytes / (1024 * 1024),
            "rss_mb": rss_bytes / (1024 * 1024)
        }

    @staticmethod
    def calculate_cpu_delta(t1_stat: Dict[str, Any], t2_stat: Dict[str, Any], 
                            delta_total_ticks: int, num_cpus: int = 4) -> float:
        """İki örnekleme anı arasındaki süreç CPU kullanım yüzdesini hesaplar."""
        delta_proc = t2_stat["total_time"] - t1_stat["total_time"]
        if delta_total_ticks <= 0:
            return 0.0
        cpu_usage = (delta_proc / delta_total_ticks) * 100.0 * num_cpus
        return min(cpu_usage, 100.0 * num_cpus)

if __name__ == "__main__":
    # Test Verisi (Süreç adında boşluk ve parantez içeren zorlu durum)
    tricky_stat = "2410 (telemetry (worker)) S 1 1000 1000 0 0 0 0 0 0 0 450 180 0 0 20 0 8 0 1000 157286400 16384 18446744073709551615"
    parsed = ProcObserver.parse_stat_line(tricky_stat)
    
    print("=== [GÜVENLİ STAT PARSER DOĞRULAMA] ===")
    print(f"PID          : {parsed['pid']}")
    print(f"Süreç Adı    : '{parsed['comm']}' (Tuzak parantez başarıyla korundu)")
    print(f"Durum        : {parsed['state']} (Sleeping)")
    print(f"İş Parçacığı : {parsed['num_threads']}")
    print(f"Sanal Bellek : {parsed['vsize_mb']:.2f} MB")
    print(f"Fiziksel RAM : {parsed['rss_mb']:.2f} MB")


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Sabotaj Laboratuvarı: D-State Süreç ve FD Sızıntısı
Ölümsüz Süreçler (D-State), Zombi Süreçler ve FD Tükenme Krizi Simülatörü
"""

from typing import Dict, List, Tuple

class ProcessSabotageLab:
    """Arızalı süreç durumlarını (/proc üzerinden) tespit eden simülasyon laboratuvarı."""
    
    @staticmethod
    def simulate_fd_leak(max_limit: int = 1024) -> Tuple[int, bool, str]:
        """Sürekli soket açıp kapatmayan bir sürecin FD tükenme krizini modeller."""
        open_fds = []
        for fd in range(3, 1100):
            if len(open_fds) >= max_limit - 3: # 0, 1, 2 hariç
                return len(open_fds), True, "EMFILE: Too many open files! Sistem bağlantı kabul edemiyor."
            open_fds.append(f"socket:[{fd*100}]")
        return len(open_fds), False, "Normal çalışma."

    @staticmethod
    def analyze_process_health(state: str, num_fds: int, rss_mb: float) -> Tuple[str, str]:
        """Süreç sağlık teşhisi koyar."""
        if state == "D":
            return "KRITIK_TEHLIKE", "Süreç kesintisiz uykuda (D-State)! Çekirdek I/O kilitlenmesi, kill -9 dahi durduramaz."
        elif state == "Z":
            return "HATA_ZOMBI", "Süreç zombi (Z-State)! Ebeveyn wait() çağrısı yapmıyor, PID tablosunu kirletiyor."
        elif num_fds > 900:
            return "KAYNAK_SIZINTISI", f"Kritik FD sızıntısı tespit edildi ({num_fds} açık FD)! EMFILE riski yüksek."
        elif rss_mb > 500:
            return "BELLEK_SIZINTISI", f"Aşırı RAM tüketimi ({rss_mb:.1f} MB)! OOM-Killer riski."
        return "SAGLIKLI", "Süreç normal çalışma sınırlarında."

if __name__ == "__main__":
    print("=== [SABOTAJ VE ARIZA TEŞHİS LABORATUVARI] ===")
    
    # Senaryo 1: FD Sızıntısı
    count, leaked, err_msg = ProcessSabotageLab.simulate_fd_leak(max_limit=1024)
    print(f"[*] FD Sızıntı Testi: Açık FD Sayısı = {count} -> {err_msg}")

    # Senaryo 2: D-State Süreç Analizi
    sev1, msg1 = ProcessSabotageLab.analyze_process_health(state="D", num_fds=25, rss_mb=45.0)
    print(f"[*] D-State Analizi : [{sev1}] {msg1}")

    # Senaryo 3: Zombi Süreç Analizi
    sev2, msg2 = ProcessSabotageLab.analyze_process_health(state="Z", num_fds=5, rss_mb=0.0)
    print(f"[*] Zombi Analizi   : [{sev2}] {msg2}")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Gerçek Zamanlı CPU Yüzdesi Hesaplama Laboratuvarı
İki Örnekleme Arasındaki Toplam ve Süreç Ticks Farkından %CPU Hesabı
"""

import time
from typing import Dict, List, Tuple

class CpuMonitorDemo:
    """İki zaman aralığında /proc/stat ve /proc/PID/stat delta hesaplayıcı."""
    
    def __init__(self, num_cores: int = 4):
        self.num_cores = num_cores
        
    def simulate_telemetry_stream(self) -> List[Dict[str, float]]:
        """10 adımlık zaman serisinde CPU kullanım değişimini simüle eder."""
        timeline = []
        
        # Başlangıç durumu (t0)
        sys_total = 100000
        proc_total = 5000
        
        # Simüle edilen iş yükü profili (Düşük -> Ağır Radar DSP -> Normal)
        workload_deltas = [20, 30, 80, 250, 400, 380, 150, 50, 30, 20]
        
        for step, p_delta in enumerate(workload_deltas):
            delta_total = 500 # Sistem genelinde geçen 500 tick
            sys_total += delta_total
            proc_total += p_delta
            
            # %CPU = (delta_proc / delta_total) * 100 * num_cores
            cpu_pct = (p_delta / delta_total) * 100.0 * self.num_cores
            cpu_pct = min(cpu_pct, 100.0 * self.num_cores)
            
            timeline.append({
                "step": step,
                "process_ticks_delta": p_delta,
                "total_ticks_delta": delta_total,
                "cpu_percent": cpu_pct
            })
            
        return timeline

if __name__ == "__main__":
    monitor = CpuMonitorDemo(num_cores=4)
    data = monitor.simulate_telemetry_stream()
    
    print("=== [GERÇEK ZAMANLI CPU YÜZDESİ ZAMAN SERİSİ] ===")
    for d in data:
        bar = "#" * int(d["cpu_percent"] / 10)
        print(f"Zaman T+{d['step']:02d}: Delta={d['process_ticks_delta']:3d} ticks -> CPU: %{d['cpu_percent']:5.1f} | {bar}")


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): /proc/PID/maps Sanal Bellek Haritalama Analizi
VMA Alanları, Paylaşılan Kütüphaneler, Yığın (Stack) ve Öbek (Heap) İncelemesi
"""

from typing import List, Dict, Any

class MemoryMapsParser:
    """Linux /proc/PID/maps dosyasını ayrıştıran bellek analiz motoru."""
    
    @staticmethod
    def parse_maps_text(maps_content: str) -> List[Dict[str, Any]]:
        segments = []
        for line in maps_content.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            # Örnek satır: 00400000-00452000 r-xp 00000000 08:02 173521 /opt/aselsan/radar_app
            addr_range = parts[0].split("-")
            start_addr = int(addr_range[0], 16)
            end_addr = int(addr_range[1], 16)
            perms = parts[1]
            offset = parts[2]
            dev = parts[3]
            inode = parts[4]
            pathname = parts[5] if len(parts) > 5 else "[anon]"
            
            size_kb = (end_addr - start_addr) // 1024
            segments.append({
                "start": hex(start_addr),
                "end": hex(end_addr),
                "size_kb": size_kb,
                "perms": perms,
                "path": pathname
            })
        return segments

# Simüle edilmiş maps içeriği
sample_maps = """
00400000-0040c000 r-xp 00000000 08:01 1048576 /opt/aselsan/radar_app
0060b000-0060c000 r--p 0000b000 08:01 1048576 /opt/aselsan/radar_app
0060c000-0060d000 rw-p 0000c000 08:01 1048576 /opt/aselsan/radar_app
01420000-01450000 rw-p 00000000 00:00 0       [heap]
7f8a1000-7f9a1000 r-xp 00000000 08:01 2097152 /lib/x86_64-linux-gnu/libc.so.6
7ffd5000-7ffd7000 rw-p 00000000 00:00 0       [stack]
"""

if __name__ == "__main__":
    parsed_segments = MemoryMapsParser.parse_maps_text(sample_maps)
    print("=== [/proc/PID/maps SANAL BELLEK HARİTASI] ===")
    total_vma_kb = 0
    for s in parsed_segments:
        total_vma_kb += s['size_kb']
        print(f"[{s['start']} - {s['end']}] {s['perms']:4s} | {s['size_kb']:6d} KB | {s['path']}")
    print(f"\n[*] Toplam Haritalanmış Sanal Bellek: {total_vma_kb:,} KB ({total_vma_kb/1024:.2f} MB)")


# -*- coding: utf-8 -*-
"""
HÜCRE 22 (CODE 6): 4-Panelli Görselleştirme Paneli ve Katı Doğrulama Testleri
procfs Mimarisi, %CPU Zaman Serisi, Bellek Dağılımı ve Süreç Durum Dağılımı
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_094_proc_ve_sistem_gozlemlenebilirligi.png"

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

    # PANEL 1: procfs Sanal Dosya Sistemi Mimarisi
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("procfs Çekirdek-Kullanıcı Alanı Köprüsü (RAM-Only VFS)", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    boxes = [
        ("Kullanıcı Alanı: open('/proc/1420/stat')", 0.20, 0.80, accent_blue),
        ("Linux VFS: procfs Sürücüsü (No Disk I/O)", 0.20, 0.50, accent_amber),
        ("struct task_struct (Çekirdek Belleği)", 0.20, 0.20, accent_green),
        ("stat: 52 Metrik\n[utime, stime, state]", 0.70, 0.75, accent_blue),
        ("status: İnsan Okunabilir\n[VmSize, VmRSS, Threads]", 0.70, 0.45, accent_amber),
        ("fd/: Sembolik Linkler\n[socket, pipe, files]", 0.70, 0.15, accent_green)
    ]
    for text, x, y, col in boxes:
        ax1.text(x, y, text, ha='center', va='center', color=text_color, fontsize=8, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor=col, linewidth=2))

    ax1.annotate("", xy=(0.20, 0.60), xytext=(0.20, 0.72), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax1.annotate("", xy=(0.20, 0.30), xytext=(0.20, 0.42), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax1.annotate("", xy=(0.55, 0.75), xytext=(0.38, 0.50), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax1.annotate("", xy=(0.55, 0.45), xytext=(0.38, 0.50), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax1.annotate("", xy=(0.55, 0.15), xytext=(0.38, 0.50), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))

    ax1.set_xlim(0, 1.0)
    ax1.set_ylim(0, 1.0)
    ax1.axis('off')

    # PANEL 2: Çok Çekirdekli Sistemde Gerçek Zamanlı CPU Yüzdesi
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("Telemetri İzleme: İki Zaman Noktası Arasındaki %CPU Değişimi", fontsize=12, fontweight='bold', color=accent_amber, pad=12)
    
    steps = np.arange(10)
    cpu_vals = [16.0, 24.0, 64.0, 200.0, 320.0, 304.0, 120.0, 40.0, 24.0, 16.0]
    
    ax2.plot(steps, cpu_vals, marker='o', linewidth=2.5, color=accent_red, label='Radar Görev Süreci (4 Çekirdek Toplamı)')
    ax2.axhline(100.0, color=accent_amber, linestyle='--', label='1 Çekirdek Doyum Eşiği (%100)')
    ax2.axhline(300.0, color=accent_blue, linestyle=':', label='Kritik Alarm Eşiği (%300)')
    
    ax2.set_xlabel("Örnekleme Zamanı (T+100ms)", fontsize=10, color=text_color)
    ax2.set_ylabel("CPU Kullanımı (%)", fontsize=10, color=text_color)
    ax2.legend(facecolor='#0F172A', edgecolor='#334155', fontsize=8)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#475569')

    # PANEL 3: Sanal Bellek (VSize) vs Fiziksel Bellek (RSS) Dağılımı
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("Süreç Bellek Profili: VmSize vs VmRSS vs VmHWM", fontsize=12, fontweight='bold', color=accent_green, pad=12)
    
    processes = ["Radar DSP", "Navigasyon", "C4I Broker", "Watchdog"]
    vsize_vals = [250.0, 120.0, 180.0, 35.0]
    rss_vals = [65.0, 42.0, 58.0, 12.0]
    
    x = np.arange(len(processes))
    width = 0.35
    
    ax3.bar(x - width/2, vsize_vals, width, label='VmSize (Sanal Bellek MB)', color=accent_blue, alpha=0.85)
    ax3.bar(x + width/2, rss_vals, width, label='VmRSS (Fiziksel RAM MB)', color=accent_green, alpha=0.9)
    
    ax3.set_ylabel("Bellek (MB)", fontsize=10, color=text_color)
    ax3.set_xticks(x)
    ax3.set_xticklabels(processes, fontsize=9, color=text_color)
    ax3.legend(facecolor='#0F172A', edgecolor='#334155', fontsize=8)
    ax3.grid(True, linestyle='--', alpha=0.3, color='#475569')

    # PANEL 4: Linux Süreç Durum Dağılımı ve Tehlike Seviyeleri
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("Süreç Durumları ve Watchdog Müdahale Matrisi", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    states = ["S (Sleeping)", "R (Running)", "D (Disk/IO Wait)", "Z (Zombie)"]
    counts = [184, 8, 2, 1]
    colors = [accent_green, accent_blue, accent_red, accent_amber]
    
    bars = ax4.bar(states, counts, color=colors, width=0.55)
    ax4.set_ylabel("Sistemdeki Süreç Sayısı", fontsize=10, color=text_color)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars:
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

    # 2. Dayanıklı Ayrıştırma Doğrulaması (Parantez Tuzağı)
    test_proc = SimulatedProcess(pid=999, comm="complex (nested) app", ppid=1, state="R")
    test_proc.num_threads = 4
    test_line = test_proc.generate_stat_line()
    p = ProcObserver.parse_stat_line(test_line)
    assert p["pid"] == 999, "HATA: PID doğru ayrıştırılamadı!"
    assert p["comm"] == "complex (nested) app", "HATA: Süreç adı parantez tuzağında bozuldu!"
    assert p["state"] == "R", "HATA: State alanı kaydı!"
    assert p["num_threads"] == 4, "HATA: Thread sayısı yanlış okundu!"
    print("  [+] Dayanıklı /proc/PID/stat Ayrıştırma Mantığı Doğrulandı.")

    # 3. CPU Yüzdesi Hesaplama Doğrulaması
    t1 = {"total_time": 1000}
    t2 = {"total_time": 1100} # 100 ticks harcandı
    cpu = ProcObserver.calculate_cpu_delta(t1, t2, delta_total_ticks=1000, num_cpus=4)
    # (100 / 1000) * 100 * 4 = %40.0
    assert abs(cpu - 40.0) < 1e-5, f"HATA: Beklenen CPU %40.0, Hesaplanan: {cpu}"
    print("  [+] Çok Çekirdekli %CPU Delta Formülasyonu Doğrulandı.")

    # 4. FD Sızıntısı ve Limit Aşımı Doğrulaması
    count, leaked, _ = ProcessSabotageLab.simulate_fd_leak(max_limit=1024)
    assert leaked is True, "HATA: FD sızıntısı EMFILE krizini tetiklemelidir!"
    assert count >= 1020, "HATA: Limit civarında sızıntı yakalanmalıdır!"
    print("  [+] FD Sızıntısı (EMFILE) ve Eşik Değer Alarmı Doğrulandı.")

    # 5. D-State ve Zombi Teşhis Doğrulaması
    sev_d, _ = ProcessSabotageLab.analyze_process_health("D", 50, 100.0)
    assert sev_d == "KRITIK_TEHLIKE", "HATA: D-state süreç kritik tehlike olarak etiketlenmelidir!"
    sev_z, _ = ProcessSabotageLab.analyze_process_health("Z", 10, 0.0)
    assert sev_z == "HATA_ZOMBI", "HATA: Zombi süreç tespit edilmelidir!"
    print("  [+] D-State ve Z-State Çekirdek Arıza Teşhisi Doğrulandı.")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
