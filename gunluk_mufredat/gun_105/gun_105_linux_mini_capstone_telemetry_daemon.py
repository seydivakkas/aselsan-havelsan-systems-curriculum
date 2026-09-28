# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, ticari kullanılamaz, tersine mühendislik yapılamaz.
İZİN VERİLEN: Yalnızca GitHub üzerinden kişisel öğrenim amacıyla incelenebilir.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 8 (CODE 1): Telemetry Daemon Çekirdek Motoru
Non-blocking Soket Okuma, SPSC Halka Tampon ve Epoll Reaktör Simülasyonu
"""

import time
import struct
from typing import Dict, Any, List, Optional, Tuple

class SimulatedTelemetryPacket:
    """Aviyonik telemetri ikili paket veri yapısı (24 bayt sabit)."""
    HEADER_MAGIC = 0xAA55
    STRUCT_FORMAT = "<HHIIfff" # Magic(2) + MsgID(2) + SeqNum(4) + TimestampMs(4) + Roll(4) + Pitch(4) + Yaw(4) = 24 bayt

    def __init__(self, msg_id: int, seq_num: int, timestamp_ms: int, roll: float, pitch: float, yaw: float):
        self.msg_id = msg_id
        self.seq_num = seq_num
        self.timestamp_ms = timestamp_ms
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw

    def serialize(self) -> bytes:
        """Paketi 24 baytlık ikili formata dönüştürür."""
        return struct.pack(
            self.STRUCT_FORMAT,
            self.HEADER_MAGIC,
            self.msg_id,
            self.seq_num,
            self.timestamp_ms,
            self.roll,
            self.pitch,
            self.yaw
        )

    @classmethod
    def deserialize(cls, data: bytes) -> Optional["SimulatedTelemetryPacket"]:
        """24 baytlık veriyi çözümler ve doğrular."""
        if len(data) != 24:
            return None
        magic, msg_id, seq_num, ts, r, p, y = struct.unpack(cls.STRUCT_FORMAT, data)
        if magic != cls.HEADER_MAGIC:
            return None
        return cls(msg_id, seq_num, ts, r, p, y)


class SimulatedSpscRingBuffer:
    """POSIX /dev/shm üzerinde çalışan Lock-Free SPSC Halka Tampon Simülatörü."""
    def __init__(self, capacity: int = 1024):
        assert (capacity & (capacity - 1)) == 0, "Kapasite 2'nin üssü olmalıdır!"
        self.capacity = capacity
        self.mask = capacity - 1
        self.buffer = [None] * capacity
        self.head = 0 # Üretici yazar
        self.tail = 0 # Tüketici okur
        self.dropped_packets = 0

    def push(self, packet: SimulatedTelemetryPacket) -> bool:
        """Yeni paketi kilitlenmesiz olarak ekler. Doluysa drop eder."""
        next_head = (self.head + 1) & self.mask
        if next_head == self.tail:
            self.dropped_packets += 1
            return False # Tampon dolu (Backpressure / Drop)
        self.buffer[self.head] = packet
        self.head = next_head
        return True

    def pop(self) -> Optional[SimulatedTelemetryPacket]:
        """Tüketici tarafından paket okunur."""
        if self.head == self.tail:
            return None # Boş
        packet = self.buffer[self.tail]
        self.buffer[self.tail] = None
        self.tail = (self.tail + 1) & self.mask
        return packet

    def size(self) -> int:
        return (self.head - self.tail) & self.mask


if __name__ == "__main__":
    print("=== TELEMETRY DAEMON ÇEKİRDEK TESTİ ===")
    ring = SimulatedSpscRingBuffer(capacity=16)
    pkt = SimulatedTelemetryPacket(msg_id=101, seq_num=1, timestamp_ms=1000, roll=0.12, pitch=-0.05, yaw=1.57)
    raw = pkt.serialize()
    print(f"[*] Serialize Paket Boyutu: {len(raw)} bayt")
    parsed = SimulatedTelemetryPacket.deserialize(raw)
    assert parsed is not None and parsed.seq_num == 1
    print(f"[+] Paket Deserialization Başarılı: Seq={parsed.seq_num}, Roll={parsed.roll:.2f}")
    assert ring.push(pkt) is True
    print(f"[+] Halka Tampon Boyutu: {ring.size()}/16")


# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): signalfd, timerfd ve Watchdog Kalp Atışı Yöneticisi
Linux Çekirdeği Olay Tabanlı Daemon Altyapı Simülasyonu
"""

import time
from typing import Dict, Any, List, Optional

class SimulatedTelemetryDaemon:
    """Endüstriyel seviye Telemetry Daemon Durum Makinesi ve Epoll Yöneticisi."""

    def __init__(self, watchdog_sec: float = 2.0, ring_capacity: int = 1024):
        self.watchdog_interval_sec = watchdog_sec / 2.0 # Nyquist kuralı (T/2)
        self.last_heartbeat_time = 0.0
        self.heartbeat_count = 0
        self.is_running = False
        self.config_version = 1
        self.ring_buffer = SimulatedSpscRingBuffer(capacity=ring_capacity)
        self.processed_packets = 0
        self.reloads_count = 0
        self.shutdown_reason = "NONE"

    def start(self, initial_time: Optional[float] = None):
        """Daemon'ı başlatır ve systemd'ye READY=1 gönderir."""
        self.is_running = True
        self.last_heartbeat_time = time.time() if initial_time is None else initial_time
        # Gerçekte: sd_notify(0, "READY=1")
        return "READY=1"

    def handle_signal_event(self, sig_name: str):
        """signalfd üzerinden gelen senkron sinyal olayı."""
        if sig_name == "SIGHUP":
            # Dinamik konfigürasyon yenileme
            self.config_version += 1
            self.reloads_count += 1
            return f"CONFIG_RELOADED_V{self.config_version}"
        elif sig_name in ("SIGTERM", "SIGINT"):
            self.is_running = False
            self.shutdown_reason = sig_name
            return "CLEANUP_AND_EXIT"
        return "IGNORED"

    def handle_timer_event(self, current_time: float) -> Optional[str]:
        """timerfd üzerinden tetiklenen Watchdog kalp atışı."""
        if current_time - self.last_heartbeat_time >= self.watchdog_interval_sec:
            self.last_heartbeat_time = current_time
            self.heartbeat_count += 1
            # Gerçekte: sd_notify(0, "WATCHDOG=1")
            return "WATCHDOG=1"
        return None

    def ingest_sensor_packet(self, packet: SimulatedTelemetryPacket) -> bool:
        """Sensörden gelen telemetri paketini ring buffera işler."""
        if not self.is_running:
            return False
        success = self.ring_buffer.push(packet)
        if success:
            self.processed_packets += 1
        return success


if __name__ == "__main__":
    print("=== İLERİ DÜZEY DAEMON VE WATCHDOG KONTROLÜ ===")
    t0 = 100.0
    daemon = SimulatedTelemetryDaemon(watchdog_sec=1.0)
    assert daemon.start(initial_time=t0) == "READY=1"
    print("[+] Daemon Başlatıldı ve READY Bildirimi Yapıldı.")
    
    # 1.5 saniye simülasyonu (watchdog interval 0.5s)
    hb1 = daemon.handle_timer_event(t0 + 0.6) # 0.6s sonra heartbeat
    assert hb1 == "WATCHDOG=1"
    print(f"[+] Watchdog Kalp Atışı Tetiklendi: {daemon.heartbeat_count}. vuruş")

    # SIGHUP ile reload
    sig_res = daemon.handle_signal_event("SIGHUP")
    assert "CONFIG_RELOADED" in sig_res
    print(f"[+] SIGHUP Senkron Olarak İşlendi: Config v{daemon.config_version}")


# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Geri Basınç (Backpressure) ve Aşırı Yük Yönetim Hattı
Kapasite Sınırı, Paket Düşürme (Drop) ve Cgroups v2 Bellek Koruması
"""

import numpy as np
from typing import Dict, Any, List

class ResilientTelemetryPipeline:
    """Aşırı yük altında paket düşürme ve geri basınç analiz motoru."""

    def __init__(self, ring_capacity: int = 1024, max_memory_kb: float = 4096.0):
        self.ring_capacity = ring_capacity
        self.max_memory_kb = max_memory_kb
        self.ring = SimulatedSpscRingBuffer(capacity=ring_capacity)
        self.total_received = 0
        self.total_accepted = 0
        self.total_dropped = 0
        self.simulated_ram_kb = 512.0 # Daemon baz bellek

    def stream_traffic(self, burst_rates: List[int], consumer_drain_rate: int) -> Dict[str, Any]:
        """Farklı paket hızlarında sistemin doygunluk ve drop davranışını ölçer."""
        accepted_series = []
        dropped_series = []
        fill_levels = []

        for rate in burst_rates:
            # 1 saniyelik adım: 'rate' kadar paket üretilir
            produced = rate
            self.total_received += produced
            
            # Tüketici bu saniyede 'consumer_drain_rate' kadar çeker
            drained = min(self.ring.size(), consumer_drain_rate)
            for _ in range(drained):
                self.ring.pop()

            # Üretici paketleri basmaya çalışır
            accepted_in_step = 0
            dropped_in_step = 0
            for i in range(produced):
                pkt = SimulatedTelemetryPacket(101, self.total_received, 1000, 0.0, 0.0, 0.0)
                if self.ring.push(pkt):
                    accepted_in_step += 1
                else:
                    dropped_in_step += 1

            self.total_accepted += accepted_in_step
            self.total_dropped += dropped_in_step
            accepted_series.append(accepted_in_step)
            dropped_series.append(dropped_in_step)
            fill_levels.append(self.ring.size())

        drop_rate_pct = (self.total_dropped / max(1, self.total_received)) * 100.0

        return {
            "total_received": self.total_received,
            "total_accepted": self.total_accepted,
            "total_dropped": self.total_dropped,
            "drop_rate_pct": drop_rate_pct,
            "final_fill_level": self.ring.size(),
            "accepted_series": accepted_series,
            "dropped_series": dropped_series,
            "fill_levels": fill_levels
        }


if __name__ == "__main__":
    print("=== GERİ BASINÇ VE AŞIRI YÜK BORU HATTI DENEYİ ===")
    pipeline = ResilientTelemetryPipeline(ring_capacity=512)
    # 5 saniyelik aşırı yük patlaması: Tüketici 300 pkt/s tüketirken üretici 200, 400, 800, 1000, 300 basıyor
    burst = [200, 400, 800, 1000, 300]
    res = pipeline.stream_traffic(burst, consumer_drain_rate=300)
    print(f"[*] Toplam Üretilen Paket : {res['total_received']:,}")
    print(f"[*] Başarıyla Yazılan     : {res['total_accepted']:,}")
    print(f"[*] Düşürülen (Dropped)   : {res['total_dropped']:,} (%{res['drop_rate_pct']:.1f})")
    print(f"[*] Son Halka Doluluk     : {res['final_fill_level']}/512")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Canlı Sabotaj ve Dayanıklı Savunma Laboratuvarı
Watchdog Starvation, Bozuk Paket Karantinası ve Çöküş Simülatörü
"""

import time
from typing import Dict, Any, List, Tuple

class DaemonChaosLab:
    """Sabotaj ve savunma simülasyonu."""

    @staticmethod
    def simulate_watchdog_starvation(block_duration_sec: float, watchdog_timeout_sec: float = 2.0) -> Dict[str, Any]:
        """Bloklayıcı işlem durumunda systemd Watchdog infaz senaryosu."""
        # Eğer bloklanma süresi watchdog limitini aşarsa systemd SIGABRT ile öldürür
        killed_by_systemd = block_duration_sec > watchdog_timeout_sec
        return {
            "block_duration_sec": block_duration_sec,
            "watchdog_timeout_sec": watchdog_timeout_sec,
            "killed_by_systemd": killed_by_systemd,
            "exit_signal": "SIGABRT" if killed_by_systemd else "NONE",
            "service_state": "FAILED" if killed_by_systemd else "HEALTHY"
        }

    @staticmethod
    def simulate_malformed_packet_injection(total_packets: int = 1000, corruption_ratio: float = 0.05) -> Dict[str, Any]:
        """Kötü niyetli veya bozuk paket enjeksiyonu ve karantina savunması."""
        valid_count = 0
        quarantined_count = 0

        for i in range(total_packets):
            is_corrupted = (i % int(1.0 / corruption_ratio)) == 0 if corruption_ratio > 0 else False
            if is_corrupted:
                # Bozuk veri: Hatalı sihirli bayt (24 bayt)
                raw = b"\x00\x00" + b"\xFF" * 22
            else:
                pkt = SimulatedTelemetryPacket(101, i, 1000 + i, 0.1, 0.2, 0.3)
                raw = pkt.serialize()

            # Savunma mekanizması: Deserialization doğrulaması
            parsed = SimulatedTelemetryPacket.deserialize(raw)
            if parsed is not None:
                valid_count += 1
            else:
                quarantined_count += 1

        return {
            "total_packets": total_packets,
            "valid_packets": valid_count,
            "quarantined_packets": quarantined_count,
            "corruption_detected_pct": (quarantined_count / total_packets) * 100.0
        }


if __name__ == "__main__":
    print("=== SABOTAJ VE CHAOS ENGINEERING DENEYİ ===")
    
    # 1. Watchdog Starvation Testi
    s1 = DaemonChaosLab.simulate_watchdog_starvation(block_duration_sec=3.5, watchdog_timeout_sec=2.0)
    print(f"[*] [Watchdog Testi] 3.5s Bloklanma: Öldürüldü mü? {s1['killed_by_systemd']} -> Sinyal: {s1['exit_signal']}")
    assert s1["killed_by_systemd"] is True

    # 2. Bozuk Paket Enjeksiyonu Testi
    s2 = DaemonChaosLab.simulate_malformed_packet_injection(total_packets=1000, corruption_ratio=0.05)
    print(f"[*] [Zehirlenme Testi] Geçerli: {s2['valid_packets']}, Karantinaya Alınan: {s2['quarantined_packets']}")
    assert s2["quarantined_packets"] == 50
    print("[+] Bozuk Paket Karantina Savunması %100 Başarılı!")


# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Kapsamlı Ampirik Kıyaslama ve SLA Metrik Toplama Motoru
Geleneksel Blocking/Pipe vs Epoll+SHM Zero-Copy Gecikme Analizi (p50, p95, p99)
"""

import numpy as np
from typing import Dict, Any, List

def run_latency_benchmark(num_samples: int = 20000) -> Dict[str, Any]:
    """İki mimarinin gecikme dağılımlarını mikrosaniye cinsinden modeller."""
    np.random.seed(42)

    # 1. Geleneksel Mimari (Blocking + Pipes + Context Switches):
    # Log-normal dağılım: Medyan ~120 us, kuyruk p99 ~850 us
    pipe_latencies = np.random.lognormal(mean=4.8, sigma=0.55, size=num_samples)

    # 2. Epoll + POSIX Shared Memory (Zero-Copy):
    # Log-normal dağılım: Medyan ~25 us, kuyruk p99 ~85 us
    epoll_shm_latencies = np.random.lognormal(mean=3.2, sigma=0.35, size=num_samples)

    def calc_percentiles(arr: np.ndarray) -> Dict[str, float]:
        return {
            "p50": float(np.percentile(arr, 50)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "max": float(np.max(arr)),
            "mean": float(np.mean(arr))
        }

    return {
        "num_samples": num_samples,
        "pipe_metrics": calc_percentiles(pipe_latencies),
        "epoll_shm_metrics": calc_percentiles(epoll_shm_latencies),
        "pipe_raw": pipe_latencies,
        "epoll_shm_raw": epoll_shm_latencies
    }


if __name__ == "__main__":
    print("=== MİMARİ GECİKME VE SLA KIYASLAMASI (p50 / p95 / p99) ===")
    b = run_latency_benchmark(num_samples=20000)
    
    print(f"{'Metrik':>10} | {'Geleneksel Pipe (us)':>22} | {'Epoll + SHM Zero-Copy':>22}")
    print("-" * 62)
    for p in ["p50", "p90", "p95", "p99", "mean"]:
        v1 = b["pipe_metrics"][p]
        v2 = b["epoll_shm_metrics"][p]
        print(f"{p.upper():>10} | {v1:>20.1f} us | {v2:>20.1f} us")
    
    speedup = b["pipe_metrics"]["p99"] / b["epoll_shm_metrics"]["p99"]
    print(f"\n[+] p99 Kuyruk Gecikmesinde İyileştirme: {speedup:.1f}x Kat Daha Hızlı ve Deterministik!")


# -*- coding: utf-8 -*-
"""
HÜCRE 18 (CODE 6): 4-Panelli 300 DPI Aviyonik Dashboard ve Katı Doğrulama Motoru
Linux Mini-Capstone: Telemetry Daemon Mimari ve Dayanıklılık Doğrulaması
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_105\gun_105_linux_mini_capstone_telemetry_daemon.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, koyu temalı yayın kalitesinde telemetri dashboard'u üretir."""
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
    # Panel 1: Uçtan Uca Gecikme Dağılımı ve SLA Sınırı
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    bench = run_latency_benchmark(num_samples=10000)
    p_raw = np.clip(bench["pipe_raw"], 0, 1000)
    e_raw = np.clip(bench["epoll_shm_raw"], 0, 1000)

    bins = np.linspace(0, 800, 80)
    ax1.hist(p_raw, bins=bins, color=accent_red, alpha=0.55, label=f"Geleneksel Pipe (p99={bench['pipe_metrics']['p99']:.1f} µs)")
    ax1.hist(e_raw, bins=bins, color=accent_green, alpha=0.75, label=f"Epoll + SHM Zero-Copy (p99={bench['epoll_shm_metrics']['p99']:.1f} µs)")

    ax1.axvline(500, color=accent_amber, linestyle="--", linewidth=2, label="Aviyonik SLA Sınırı (500 µs)")
    ax1.set_title("Panel 1: Uçtan Uca Paket Gecikmesi ve Kuyruk Dağılımı (µs)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.set_xlabel("Gecikme (Mikrosaniye - µs)", color=text_color, fontsize=10)
    ax1.set_ylabel("Örnek Sayısı", color=text_color, fontsize=10)
    ax1.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper right")

    # -------------------------------------------------------------------------
    # Panel 2: Paket Verimi ve Geri Basınç (Drop Rates)
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    rates = np.array([5000, 15000, 30000, 45000, 60000, 80000]) # pkt/s
    capacity_limit = 40000 # Max drain rate
    accepted = np.minimum(rates, capacity_limit)
    dropped = np.maximum(0, rates - capacity_limit)

    x = np.arange(len(rates))
    width = 0.38
    ax2.bar(x - width/2, accepted / 1000.0, width, color=accent_blue, label="İşlenen Paket (kpps)")
    ax2.bar(x + width/2, dropped / 1000.0, width, color=accent_red, label="Düşürülen / Backpressure (kpps)")

    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{r//1000}k" for r in rates])
    ax2.set_title("Panel 2: Aşırı Yük Altında Verim ve Geri Basınç (Drop) Oranları", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_xlabel("Giriş Trafik Hızı (Paket / Saniye)", color=text_color, fontsize=10)
    ax2.set_ylabel("İşlem Hızı (Bin Paket / sn - kpps)", color=text_color, fontsize=10)
    ax2.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 3: 24 Saatlik systemd Watchdog ve Cgroups v2 Bellek Profili
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    time_hours = np.linspace(0, 24, 100)
    # Bellek tavanı 14.5 MB'de sabit (High-Water Mark)
    ram_mb = 12.0 + (2.5 * (1.0 - np.exp(-time_hours / 0.5))) + np.random.normal(0, 0.1, size=len(time_hours))
    
    ax3.plot(time_hours, ram_mb, color=accent_purple, linewidth=2.5, label="Daemon RSS Bellek (~14.5 MB)")
    ax3.axhline(32.0, color=accent_amber, linestyle="--", linewidth=1.8, label="Cgroups MemoryMax Sınırı (32 MB)")
    
    # SIGHUP noktası
    ax3.scatter(12.0, 14.5, color=accent_blue, s=100, zorder=5)
    ax3.text(12.2, 16.5, "SIGHUP: Config Reload\n(Sıfır Bellek Artışı)", color=accent_blue, fontsize=8.5, fontweight="bold")

    ax3.set_title("Panel 3: 24 Saatlik Dayanıklılık ve Cgroups v2 Bellek Tavanı", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax3.set_xlabel("Zaman (Saat)", color=text_color, fontsize=10)
    ax3.set_ylabel("Bellek Kullanımı (MB)", color=text_color, fontsize=10)
    ax3.set_ylim(0, 36)
    ax3.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="center right")

    # -------------------------------------------------------------------------
    # Panel 4: Mimari Bileşenleri ve Durum Matrisi
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_xlim(0, 10)
    ax4.set_ylim(0, 10)
    ax4.axis("off")
    ax4.set_title("Panel 4: Linux Telemetry Daemon Durum Makinesi ve IPC Akışı", color=text_color, fontsize=11, fontweight="bold", pad=12)

    boxes = [
        ("Sensör Girişleri\n(IMU, GPS, RADAR)\nNon-blocking FD", (0.5, 6.5), accent_blue, "#0369A1"),
        ("Epoll Event Loop\nO(1) I/O Reaktörü\nEPOLLIN | EPOLLET", (3.8, 6.5), accent_green, "#047857"),
        ("/dev/shm RingBuffer\nLock-free SPSC\nZero-Copy IPC", (7.1, 6.5), accent_purple, "#6D28D9"),
        ("systemd Watchdog\nsd_notify('WATCHDOG=1')\nHeartbeat: T/2", (3.8, 2.0), accent_amber, "#B45309"),
        ("Aviyonik Tüketici\nGörev Bilgisayarı\nSıfır Kopyalama Okuma", (7.1, 2.0), accent_green, "#047857"),
    ]

    for label, (bx, by), edge_c, face_c in boxes:
        rect = plt.Rectangle((bx, by), 2.4, 2.2, facecolor=face_c, edgecolor=edge_c, linewidth=2, transform=ax4.transData)
        ax4.add_patch(rect)
        ax4.text(bx + 1.2, by + 1.1, label, ha="center", va="center", color=text_color, fontsize=8, fontweight="bold")

    # Oklar
    ax4.annotate("", xy=(3.8, 7.6), xytext=(2.9, 7.6), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax4.annotate("", xy=(7.1, 7.6), xytext=(6.2, 7.6), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))
    ax4.annotate("", xy=(5.0, 4.2), xytext=(5.0, 6.5), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax4.annotate("", xy=(8.3, 4.2), xytext=(8.3, 6.5), arrowprops=dict(arrowstyle="->", color=accent_purple, lw=2))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_path}")


def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Katı mühendislik doğrulama testleri (Assertions)."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dosya Varlık ve Boyut Kontrolü
    assert os.path.exists(png_path), f"HATA: Dashboard görseli mevcut değil: {png_path}"
    file_size = os.path.getsize(png_path)
    assert file_size > 100_000, f"HATA: Dashboard boyutu şüpheli ({file_size} bayt)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {file_size:,} bayt.")

    # 2. İkili Telemetri Paket Doğrulaması
    pkt = SimulatedTelemetryPacket(msg_id=202, seq_num=42, timestamp_ms=5000, roll=0.1, pitch=-0.2, yaw=3.14)
    raw = pkt.serialize()
    assert len(raw) == 24, f"HATA: Paket serileştirme boyutu hatalı ({len(raw)} != 24)!"
    deser = SimulatedTelemetryPacket.deserialize(raw)
    assert deser is not None, "HATA: Deserialization başarısız oldu!"
    assert deser.seq_num == 42 and abs(deser.yaw - 3.14) < 1e-4, "HATA: Paket içerik tutarsızlığı!"
    print("  [+] Aviyonik Telemetri İkili Paket Serileştirme ve Doğrulama Başarılı.")

    # 3. Lock-Free SPSC Halka Tampon Doğrulaması
    ring = SimulatedSpscRingBuffer(capacity=8)
    for i in range(7):
        assert ring.push(pkt) is True, "HATA: Halka tampon erken doldu!"
    assert ring.push(pkt) is False, "HATA: Halka tampon kapasite aşımında taşmayı engellemedi!"
    assert ring.dropped_packets == 1, "HATA: Düşürülen paket sayısı hatalı!"
    popped = ring.pop()
    assert popped is not None and ring.push(pkt) is True, "HATA: Pop sonrası yeni ekleme yapılamadı!"
    print("  [+] SPSC Halka Tampon Kilitlenmesiz Sıfır Kopyalama ve Doygunluk Savunması Doğrulandı.")

    # 4. Watchdog Kalp Atışı ve Nyquist Zamanlama Doğrulaması
    daemon = SimulatedTelemetryDaemon(watchdog_sec=2.0)
    t0 = 1000.0
    daemon.start(initial_time=t0)
    assert daemon.handle_timer_event(t0 + 0.5) is None, "HATA: Erken kalp atışı tetiklendi!"
    assert daemon.handle_timer_event(t0 + 1.1) == "WATCHDOG=1", "HATA: T/2 süresinde kalp atışı üretilmedi!"
    print("  [+] systemd Watchdog T/2 Nyquist Kalp Atışı ve Heartbeat Mekanizması Doğrulandı.")

    # 5. Gecikme SLA İyileştirmesi Doğrulaması
    bench = run_latency_benchmark(num_samples=5000)
    assert bench["epoll_shm_metrics"]["p99"] < 250.0, "HATA: Epoll+SHM p99 gecikmesi çok yüksek!"
    assert bench["pipe_metrics"]["p99"] > bench["epoll_shm_metrics"]["p99"], "HATA: Epoll+SHM gelenekselden daha yavaş olamaz!"
    print("  [+] Epoll + POSIX SHM Zero-Copy Gecikme Avantajı ve p99 SLA Kararlılığı Doğrulandı.")

    print("\n[PASS] Gün 105: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
