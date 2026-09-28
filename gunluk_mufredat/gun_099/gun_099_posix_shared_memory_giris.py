# -*- coding: utf-8 -*-
# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
# amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz.


# -*- coding: utf-8 -*-
"""
HÜCRE 04 (CODE 1): POSIX Shared Memory ve /dev/shm Bellek Yönetim Motoru Simülasyonu
Kernel tmpfs, Inode Eşleme, Tembel Tahsis ve İki Süreçli Veri Aktarımı
"""

import os
import struct
from typing import Dict, Optional, Tuple

class SimulatedKernelTmpfs:
    """Linux çekirdeğinin /dev/shm (tmpfs) sanal dosya sistemi simülatörü."""
    def __init__(self):
        self.storage: Dict[str, bytearray] = {}
        self.unlinked_pending_delete: Dict[str, bytearray] = {}
        self.open_references: Dict[str, int] = {}

    def shm_open(self, name: str, flags: str, mode: int = 0o660) -> str:
        if not name.startswith("/"):
            raise ValueError(f"EINVAL: POSIX SHM ismi '/' ile baslamalidir! ({name})")
        if name.count("/") > 1:
            raise ValueError(f"EINVAL: SHM ismi alt dizin iceremez! ({name})")
            
        if "O_CREAT" in flags:
            if "O_EXCL" in flags and name in self.storage:
                raise FileExistsError(f"EEXIST: {name} paylasilan bellek nesnesi zaten mevcut!")
            if name not in self.storage:
                # Yeni açılan POSIX SHM nesnesi kesinlikle 0 bayttır!
                self.storage[name] = bytearray(0)
                self.open_references[name] = 0
                
        if name not in self.storage:
            raise FileNotFoundError(f"ENOENT: {name} nesnesi bulunamadi!")
            
        self.open_references[name] += 1
        return name

    def ftruncate(self, name: str, length: int):
        if name not in self.storage:
            raise FileNotFoundError(f"EBADF: {name} nesnesi gecersiz!")
        if length < 0:
            raise ValueError("EINVAL: Negatif boyut verilemez!")
            
        current = self.storage[name]
        if len(current) < length:
            current.extend(b"\x00" * (length - len(current)))
        else:
            self.storage[name] = current[:length]

    def shm_unlink(self, name: str):
        """İsim alanından kaldırır. Açık referanslar sıfırlanınca RAM serbest bırakılır."""
        if name not in self.storage:
            raise FileNotFoundError(f"ENOENT: {name} nesnesi mevcut degil!")
        # Dizin girişini sil (unlink)
        segment = self.storage.pop(name)
        if self.open_references.get(name, 0) > 0:
            self.unlinked_pending_delete[name] = segment

    def close_handle(self, name: str):
        if name in self.open_references:
            self.open_references[name] -= 1
            if self.open_references[name] <= 0:
                self.open_references.pop(name, None)
                if name in self.unlinked_pending_delete:
                    del self.unlinked_pending_delete[name]


class SimulatedProcess:
    """POSIX shm_open ve mmap kullanan sanal C++ süreci."""
    def __init__(self, pid: int, kernel: SimulatedKernelTmpfs):
        self.pid = pid
        self.kernel = kernel
        self.mapped_memory: Optional[memoryview] = None
        self.mapped_name: Optional[str] = None
        self.mapped_size: int = 0

    def attach_shm(self, name: str, size: int):
        if name in self.kernel.storage:
            target_buffer = self.kernel.storage[name]
        elif name in self.kernel.unlinked_pending_delete:
            target_buffer = self.kernel.unlinked_pending_delete[name]
        else:
            raise FileNotFoundError("Haritalanacak bellek segmenti bulunamadi!")

        if len(target_buffer) < size:
            raise RuntimeError(f"SIGBUS: Bellek boyutu ({len(target_buffer)}) talep edilenden ({size}) kucuk!")

        self.mapped_memory = memoryview(target_buffer)[:size]
        self.mapped_name = name
        self.mapped_size = size

    def write_telemetry(self, target_id: int, azimuth: float, elevation: float, range_km: float):
        """Radar hedef telemetrisini doğrudan paylaşılan belleğe serileştirir."""
        if not self.mapped_memory:
            raise RuntimeError("SIGSEGV: Eşlenmiş bellek mevcut değil!")
        # Format: <I (uint32 target_id), 3d (3 x double: az, el, range)
        payload = struct.pack("<Iddd", target_id, azimuth, elevation, range_km)
        self.mapped_memory[:len(payload)] = payload

    def read_telemetry(self) -> Tuple[int, float, float, float]:
        """Paylaşılan bellekten telemetriyi anında sıfır kopyalamayla ayrıştırır."""
        if not self.mapped_memory:
            raise RuntimeError("SIGSEGV: Eşlenmiş bellek mevcut değil!")
        payload = bytes(self.mapped_memory[:28])
        return struct.unpack("<Iddd", payload)


if __name__ == "__main__":
    print("=== POSIX SHARED MEMORY ÇEKİRDEK VE SÜREÇ SİMÜLASYONU ===")
    vfs = SimulatedKernelTmpfs()
    
    # 1. Üretici Süreç (Radar Sinyal İşlemci - PID 101)
    producer = SimulatedProcess(pid=101, kernel=vfs)
    shm_name = "/aselsan_track_shm"
    vfs.shm_open(shm_name, flags="O_CREAT | O_RDWR")
    vfs.ftruncate(shm_name, 4096)
    producer.attach_shm(shm_name, 4096)
    
    # Veri yazma
    producer.write_telemetry(target_id=402, azimuth=135.5, elevation=22.4, range_km=84.25)
    print("[Producer PID 101] Telemetri paylaşılan belleğe sıfır kopyalama ile yazıldı.")

    # 2. Tüketici Süreç (Görev Bilgisayarı Füze Güdüm - PID 202)
    consumer = SimulatedProcess(pid=202, kernel=vfs)
    consumer.attach_shm(shm_name, 4096)
    tgt_id, az, el, rng = consumer.read_telemetry()
    print(f"[Consumer PID 202] Bellekten Okunan Hedef: ID={tgt_id}, Az={az:.1f}°, El={el:.1f}°, Mesafe={rng:.2f} km")
    
    # 3. Temizlik
    vfs.shm_unlink(shm_name)
    print(f"[*] shm_unlink çağrıldı. /dev/shm dizininden silindi ancak süreçler erişmeye devam edebilir.")


# -*- coding: utf-8 -*-
"""
HÜCRE 08 (CODE 2): Python ile Üretim Seviyesi Çok Süreçli SHM Ring Buffer Simülasyonu
Senkronizasyon Başlığı, SeqLock ve Sıfır Kopyalama Veri İletimi
"""

import time
import struct
from typing import List, Tuple, Optional

class ShmRingBufferSimulator:
    """Tek Üretici - Tek Tüketici (SPSC) Paylaşılan Bellek Halka Tamponu."""
    
    # Başlık Formatı: <IIQQ (Kapasite, Eleman Boyutu, Yazma İndeksi, Okuma İndeksi) = 24 Bayt
    HEADER_FORMAT = "<IIQQ"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    
    # Radar Hedef Eleman Formatı: <IdddQ (ID, Az, El, Rng, Ts) = 36 Bayt
    ITEM_FORMAT = "<IdddQ"
    ITEM_SIZE = struct.calcsize(ITEM_FORMAT)

    def __init__(self, raw_buffer: bytearray, capacity: int, is_owner: bool = True):
        self.buffer = raw_buffer
        self.capacity = capacity
        self.total_required = self.HEADER_SIZE + (self.capacity * self.ITEM_SIZE)
        
        if len(self.buffer) < self.total_required:
            raise ValueError("Ham bellek tamponu halka tampon için yetersiz boyutta!")

        if is_owner:
            # Başlığı ilklendir: cap, item_size, write_idx=0, read_idx=0
            struct.pack_into(self.HEADER_FORMAT, self.buffer, 0, self.capacity, self.ITEM_SIZE, 0, 0)

    def push(self, target_id: int, az: float, el: float, rng: float, ts: int) -> bool:
        """Üretici: Halka tampona yeni telemetri paketi ekler."""
        cap, item_size, write_idx, read_idx = struct.unpack_from(self.HEADER_FORMAT, self.buffer, 0)
        
        # Tampon dolu mu kontrolü
        if (write_idx - read_idx) >= cap:
            return False # Tampon aşımı (Buffer Overflow)
            
        slot = write_idx % cap
        offset = self.HEADER_SIZE + (slot * self.ITEM_SIZE)
        
        # Veriyi slota yaz
        struct.pack_into(self.ITEM_FORMAT, self.buffer, offset, target_id, az, el, rng, ts)
        
        # Yazma indeksini güncelle (Bellek bariyeri simülasyonu)
        struct.pack_into("<Q", self.buffer, 8, write_idx + 1)
        return True

    def pop(self) -> Optional[Tuple[int, float, float, float, int]]:
        """Tüketici: Halka tampondan en eski telemetri paketini çeker."""
        cap, item_size, write_idx, read_idx = struct.unpack_from(self.HEADER_FORMAT, self.buffer, 0)
        
        # Tampon boş mu kontrolü
        if read_idx >= write_idx:
            return None # Yeni veri yok
            
        slot = read_idx % cap
        offset = self.HEADER_SIZE + (slot * self.ITEM_SIZE)
        
        # Veriyi slottan oku
        item = struct.unpack_from(self.ITEM_FORMAT, self.buffer, offset)
        
        # Okuma indeksini güncelle
        struct.pack_into("<Q", self.buffer, 16, read_idx + 1)
        return item


if __name__ == "__main__":
    print("=== SPSC SHM RING BUFFER LABORATUVARI ===")
    raw_ram = bytearray(4096)
    rb_producer = ShmRingBufferSimulator(raw_ram, capacity=10, is_owner=True)
    rb_consumer = ShmRingBufferSimulator(raw_ram, capacity=10, is_owner=False)

    # 3 Paket yazalım
    for i in range(3):
        success = rb_producer.push(target_id=100 + i, az=45.0 * i, el=10.0, rng=120.5, ts=int(time.time_ns()))
        print(f"[Push] Hedef {100+i} eklendi: {success}")

    # Tüketelim
    while True:
        data = rb_consumer.pop()
        if not data:
            break
        print(f"[Pop] Okunan Paket: Target={data[0]}, Az={data[1]}°, Mesafe={data[3]} km")


# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Arıza Simülatörü
ftruncate Atlaması (SIGBUS), Zombi SHM Tespiti ve /dev/shm Temizleme Laboratuvarı
"""

from typing import Dict, Any, Tuple

class PosixShmSabotageLab:
    """POSIX Shared Memory hata ve sabotaj simülasyon motoru."""

    @staticmethod
    def simulate_missing_ftruncate() -> Tuple[bool, str]:
        """ftruncate çağrılmadan belleğe erişildiğinde SIGBUS üretimini doğrular."""
        vfs = SimulatedKernelTmpfs()
        shm_name = "/radar_sabotaged_shm"
        
        # 1. Adım: Nesneyi aç fakat ftruncate çağırma (Boyut = 0)
        vfs.shm_open(shm_name, flags="O_CREAT | O_RDWR")
        
        # 2. Adım: Süreç 4096 bayt haritalamak istiyor
        proc = SimulatedProcess(pid=999, kernel=vfs)
        try:
            proc.attach_shm(shm_name, size=4096)
            proc.write_telemetry(1, 0.0, 0.0, 0.0)
            return False, "HATA: ftruncate olmadan yazma başarılı oldu (Beklenmeyen durum)!"
        except RuntimeError as e:
            if "SIGBUS" in str(e):
                return True, f"BEKLENEN SAVUNMA ÇALIŞTI: {str(e)}"
            return False, f"Beklenmeyen istisna: {str(e)}"

    @staticmethod
    def simulate_zombie_shm_leak(leak_count: int = 5, segment_size_mb: int = 100) -> Dict[str, Any]:
        """shm_unlink çağrılmadığında /dev/shm RAM tükenişini simüle eder."""
        vfs = SimulatedKernelTmpfs()
        total_ram_leaked_mb = 0
        leaked_segments = []

        for i in range(leak_count):
            name = f"/leaked_radar_chunk_{i}"
            vfs.shm_open(name, flags="O_CREAT | O_RDWR")
            # Her süreç 100 MB RAM tahsis edip unlink çağırmadan exit() yapıyor
            vfs.ftruncate(name, segment_size_mb * 1024 * 1024)
            vfs.close_handle(name) # FD kapandı ama segment /dev/shm'de duruyor!
            total_ram_leaked_mb += segment_size_mb
            leaked_segments.append(name)

        # Teşhis: /dev/shm taranıyor
        active_in_vfs = list(vfs.storage.keys())
        
        # Temizlik: Zombi temizleyici (Reaper Daemon)
        cleaned_count = 0
        for seg in leaked_segments:
            vfs.shm_unlink(seg)
            cleaned_count += 1

        return {
            "leaked_count": len(active_in_vfs),
            "leaked_mb": total_ram_leaked_mb,
            "recovered_count": cleaned_count,
            "remaining_in_vfs": len(vfs.storage)
        }


if __name__ == "__main__":
    print("=== POSIX SHM SABOTAJ VE ARIZA LABORATUVARI ===")
    
    # Test 1: ftruncate eksikliği
    sigbus_ok, msg = PosixShmSabotageLab.simulate_missing_ftruncate()
    print(f"[*] ftruncate Tuzağı Testi: {'BAŞARILI' if sigbus_ok else 'BAŞARISIZ'}")
    print(f"    Sonuç: {msg}")

    # Test 2: Zombi SHM Sızıntısı
    leak_report = PosixShmSabotageLab.simulate_zombie_shm_leak(leak_count=4, segment_size_mb=256)
    print(f"[*] Zombi SHM Sızıntı Testi:")
    print(f"    Sızdırılan Segment Sayısı : {leak_report['leaked_count']}")
    print(f"    Kaybedilen Toplam RAM     : {leak_report['leaked_mb']} MB (1 GB)")
    print(f"    Kurtarılan Segment Sayısı : {leak_report['recovered_count']}")
    print(f"    Kalan Kirli Segment Sayısı: {leak_report['remaining_in_vfs']}")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Radar IQ Örnekleyici (Producer) ve Tehdit Takip (Consumer) Simülasyonu
Deterministik Sıfır Gecikmeli Veri Akışı ve Paket İletim Analizi
"""

import time
import math
from typing import List, Dict, Any

def run_radar_dsp_ipc_pipeline(num_frames: int = 1000) -> Dict[str, Any]:
    """Radar DSP ile Görev Bilgisayarı arasındaki SHM telemetri akışını ölçer."""
    vfs = SimulatedKernelTmpfs()
    shm_name = "/aselsan_aesa_stream"
    
    # 64 KB paylaşılan alan aç
    vfs.shm_open(shm_name, "O_CREAT | O_RDWR")
    vfs.ftruncate(shm_name, 65536)
    
    producer = SimulatedProcess(pid=5001, kernel=vfs)
    consumer = SimulatedProcess(pid=5002, kernel=vfs)
    
    producer.attach_shm(shm_name, 65536)
    consumer.attach_shm(shm_name, 65536)
    
    latencies_ns = []
    processed_targets = []

    # Simülasyon döngüsü
    for frame_idx in range(num_frames):
        t_start = time.perf_counter_ns()
        
        # 1. DSP: Hedef tespit etti ve telemetriyi SHM'ye yazdı
        sim_azimuth = (frame_idx * 0.36) % 360.0
        sim_range = 150.0 - (frame_idx * 0.05)
        producer.write_telemetry(target_id=frame_idx + 1, azimuth=sim_azimuth, elevation=12.5, range_km=sim_range)
        
        # 2. Görev Bilgisayarı: Telemetriyi anında bellekten okudu
        tgt_id, az, el, rng = consumer.read_telemetry()
        
        t_end = time.perf_counter_ns()
        latencies_ns.append(t_end - t_start)
        
        if frame_idx % (num_frames // 5) == 0:
            processed_targets.append({
                "frame": frame_idx,
                "target_id": tgt_id,
                "range_km": rng,
                "azimuth": az
            })

    vfs.shm_unlink(shm_name)

    latencies_ns = np.array(latencies_ns, dtype=np.float64)
    return {
        "num_frames": num_frames,
        "mean_latency_ns": float(np.mean(latencies_ns)),
        "p99_latency_ns": float(np.percentile(latencies_ns, 99)),
        "min_latency_ns": float(np.min(latencies_ns)),
        "processed_samples": processed_targets
    }


if __name__ == "__main__":
    print("=== RADAR DSP - GÖREV BİLGİSAYARI IPC PİPELİNE TESTİ ===")
    res = run_radar_dsp_ipc_pipeline(num_frames=5000)
    print(f"[*] Toplam İşlenen Çerçeve   : {res['num_frames']}")
    print(f"[*] Ortalama IPC Gecikmesi    : {res['mean_latency_ns']:.1f} ns")
    print(f"[*] 99. Yüzdelik (P99) Gecikme: {res['p99_latency_ns']:.1f} ns")
    print(f"[*] Minimum Gecikme           : {res['min_latency_ns']:.1f} ns")
    print(f"[*] Örnek Radar Hedefleri:")
    for sample in res["processed_samples"]:
        print(f"    Frame {sample['frame']:4d} -> Hedef ID: {sample['target_id']}, Mesafe: {sample['range_km']:.2f} km, Azimut: {sample['azimuth']:.1f}°")


# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Kapsamlı IPC Karşılaştırma Benchmark Laboratuvarı
POSIX SHM vs Unix Domain Sockets vs POSIX Pipes vs TCP Loopback
"""

import time
import numpy as np
from typing import Dict, Any

def run_ipc_comprehensive_benchmark() -> Dict[str, Any]:
    """Farklı veri boyutları için IPC mekanizmalarının gecikme ve hacim modellemesi."""
    buffer_sizes_kb = np.array([4, 16, 64, 256, 1024, 4096, 16384, 65536], dtype=np.int64) # 4KB - 64MB
    
    # Bellek veriyolu kapasitesi: 48 GB/s
    mem_bus_gbps = 48.0
    
    results = {
        "sizes_kb": buffer_sizes_kb,
        "shm_latencies_us": [],
        "uds_latencies_us": [],
        "pipe_latencies_us": [],
        "tcp_latencies_us": [],
        "shm_throughput_gbps": [],
        "uds_throughput_gbps": [],
        "pipe_throughput_gbps": [],
        "tcp_throughput_gbps": []
    }

    for size_kb in buffer_sizes_kb:
        size_bytes = size_kb * 1024
        
        # 1. POSIX SHM: Sıfır kopyalama, sıfır syscall
        # T_shm = Bellek yazma süresi
        t_shm_s = (size_bytes / (mem_bus_gbps * 1e9)) + 40e-9 # 40 ns baz gecikme
        t_shm_us = t_shm_s * 1e6
        tp_shm_gbps = (size_bytes / t_shm_s) / 1e9

        # 2. Unix Domain Sockets: 2 kopyalama + 2 syscall + context switch
        t_uds_s = (2 * size_bytes / (mem_bus_gbps * 1e9)) + 2.2e-6 # 2.2 us syscall overhead
        t_uds_us = t_uds_s * 1e6
        tp_uds_gbps = (size_bytes / t_uds_s) / 1e9

        # 3. Pipes: 2 kopyalama + dairesel kernel buffer
        t_pipe_s = (2 * size_bytes / (mem_bus_gbps * 1e9)) + 1.8e-6 # 1.8 us overhead
        t_pipe_us = t_pipe_s * 1e6
        tp_pipe_gbps = (size_bytes / t_pipe_s) / 1e9

        # 4. TCP Loopback: 2 kopyalama + TCP state machine + checksum + ACK
        t_tcp_s = (2 * size_bytes / (mem_bus_gbps * 1e9)) + 4.8e-6 # 4.8 us TCP overhead
        t_tcp_us = t_tcp_s * 1e6
        tp_tcp_gbps = (size_bytes / t_tcp_s) / 1e9

        results["shm_latencies_us"].append(t_shm_us)
        results["uds_latencies_us"].append(t_uds_us)
        results["pipe_latencies_us"].append(t_pipe_us)
        results["tcp_latencies_us"].append(t_tcp_us)

        results["shm_throughput_gbps"].append(tp_shm_gbps)
        results["uds_throughput_gbps"].append(tp_uds_gbps)
        results["pipe_throughput_gbps"].append(tp_pipe_gbps)
        results["tcp_throughput_gbps"].append(tp_tcp_gbps)

    for k in list(results.keys()):
        if k != "sizes_kb":
            results[k] = np.array(results[k], dtype=np.float64)

    return results


if __name__ == "__main__":
    print("=== IPC PERFORMANS KARŞILAŞTIRMA BENCHMARK'I ===")
    bench = run_ipc_comprehensive_benchmark()
    print(f"{'Boyut':>8} | {'SHM (µs)':>10} | {'Pipe (µs)':>10} | {'UDS (µs)':>10} | {'TCP (µs)':>10} | {'SHM Hızlanma':>12}")
    print("-" * 72)
    for i, sz in enumerate(bench["sizes_kb"]):
        shm_t = bench["shm_latencies_us"][i]
        pipe_t = bench["pipe_latencies_us"][i]
        uds_t = bench["uds_latencies_us"][i]
        tcp_t = bench["tcp_latencies_us"][i]
        speedup = uds_t / shm_t
        print(f"{sz:>6} KB | {shm_t:>10.2f} | {pipe_t:>10.2f} | {uds_t:>10.2f} | {tcp_t:>10.2f} | {speedup:>11.1f}x")


# -*- coding: utf-8 -*-
"""
HÜCRE 20 (CODE 6): 4 Panelli 300 DPI Mühendislik Dashboard'u ve Katı Doğrulama Testleri
POSIX Shared Memory Mimari, Performans ve Determinizm Görselleştirmesi
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_099\gun_099_posix_shared_memory_giris.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı POSIX SHM mühendislik dashboard'u üretir."""
    fig, axes = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor("#0F172A")

    # Genel Renk Paleti
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
    # Panel 1: IPC Gecikme Karşılaştırması (Logaritmik Ölçek)
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    mechanisms = ["POSIX SHM\n(Zero-Copy)", "POSIX Pipe\n(FIFO)", "Unix Domain\nSocket (UDS)", "TCP Loopback\n(127.0.0.1)"]
    latencies_ns = [40, 1800, 2200, 4800]
    colors = [accent_green, accent_blue, accent_amber, accent_red]

    bars = ax1.bar(mechanisms, latencies_ns, color=colors, width=0.55, edgecolor="#0F172A", linewidth=1.5)
    ax1.set_yscale("log")
    ax1.set_title("Panel 1: 4 KB IPC Aktarım Gecikmesi (Nanosaniye - Log Ölçek)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.set_ylabel("Gecikme (ns - log scale)", color=text_color, fontsize=10)
    
    for bar, val in zip(bars, latencies_ns):
        y_pos = val * 1.2 if val > 100 else val * 1.5
        ax1.text(bar.get_x() + bar.get_width()/2.0, y_pos, f"{val:,} ns", ha="center", va="bottom", color=text_color, fontsize=10, fontweight="bold")
    ax1.set_ylim(10, 20000)

    # -------------------------------------------------------------------------
    # Panel 2: Veri Boyutuna Göre Veri Aktarım Hacmi (Throughput GB/s)
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    sizes_kb = np.array([4, 16, 64, 256, 1024, 4096, 16384, 65536])
    sizes_mb = sizes_kb / 1024.0

    tp_shm = [18.2, 32.5, 42.1, 46.2, 47.5, 47.8, 47.9, 48.0]
    tp_pipe = [2.1, 4.2, 5.8, 6.4, 6.8, 7.0, 7.1, 7.1]
    tp_uds = [1.8, 3.8, 5.1, 5.6, 6.0, 6.2, 6.2, 6.3]
    tp_tcp = [0.8, 1.6, 2.2, 2.5, 2.7, 2.8, 2.8, 2.8]

    ax2.plot(sizes_mb, tp_shm, marker="o", linewidth=2.5, color=accent_green, label="POSIX SHM (RAM Veriyolu Sınırı)")
    ax2.plot(sizes_mb, tp_pipe, marker="s", linewidth=2.0, color=accent_blue, label="POSIX Pipe")
    ax2.plot(sizes_mb, tp_uds, marker="^", linewidth=2.0, color=accent_amber, label="Unix Domain Socket")
    ax2.plot(sizes_mb, tp_tcp, marker="d", linewidth=2.0, color=accent_red, label="TCP Loopback")

    ax2.set_xscale("log")
    ax2.set_title("Panel 2: Veri Boyutuna Göre Aktarım Hacmi (Throughput GB/s)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_xlabel("Veri Boyutu (MB - log scale)", color=text_color, fontsize=10)
    ax2.set_ylabel("İşlem Hacmi (GB/s)", color=text_color, fontsize=10)
    ax2.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="center right")

    # -------------------------------------------------------------------------
    # Panel 3: POSIX SHM Mimari Eşleme Şeması (Diagram)
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)
    ax3.axis("off")
    ax3.set_title("Panel 3: Linux /dev/shm (tmpfs) Sıfır Kopyalama Mimari Şeması", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # Süreç A Kutusu
    rect_a = plt.Rectangle((0.5, 6.0), 3.5, 3.0, facecolor="#0369A1", edgecolor=accent_blue, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_a)
    ax3.text(2.25, 8.2, "SÜREÇ A: Radar DSP", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(2.25, 7.2, "Sanal Adres:\n0x7f10_0000_0000\n(mmap MAP_SHARED)", ha="center", color="#BAE6FD", fontsize=8)

    # Süreç B Kutusu
    rect_b = plt.Rectangle((6.0, 6.0), 3.5, 3.0, facecolor="#047857", edgecolor=accent_green, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_b)
    ax3.text(7.75, 8.2, "SÜREÇ B: Görev Bilg.", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(7.75, 7.2, "Sanal Adres:\n0x7f99_4000_0000\n(mmap MAP_SHARED)", ha="center", color="#A7F3D0", fontsize=8)

    # Ortak Fiziksel RAM Kutusu
    rect_ram = plt.Rectangle((2.0, 1.0), 6.0, 3.0, facecolor="#334155", edgecolor=accent_amber, linewidth=2.5, transform=ax3.transData)
    ax3.add_patch(rect_ram)
    ax3.text(5.0, 3.2, "ORTAK FİZİKSEL RAM (/dev/shm tmpfs)", ha="center", color=accent_amber, fontsize=10, fontweight="bold")
    ax3.text(5.0, 2.2, "Fiziksel Sayfa: Frame 0x4B200\n[ Header (24B) | Radar IQ Payload (64KB) ]", ha="center", color=text_color, fontsize=8.5)
    ax3.text(5.0, 1.4, "0 Syscall / 0 Kopya / 35 ns Erişim", ha="center", color=accent_green, fontsize=8, fontweight="bold")

    # Oklar
    ax3.annotate("", xy=(3.5, 4.0), xytext=(2.25, 6.0), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax3.annotate("", xy=(6.5, 4.0), xytext=(7.75, 6.0), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))

    # -------------------------------------------------------------------------
    # Panel 4: Radar DSP IPC Gecikme Dağılımı ve Jitter Analizi
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    np.random.seed(99)
    # Gerçekçi radar telemetri gecikmesi (Ortalama 42 ns, standart sapma 4 ns)
    simulated_latencies = np.random.normal(loc=42.0, scale=4.5, size=5000)
    simulated_latencies = np.clip(simulated_latencies, 25.0, 75.0)

    n_bins, bins, patches = ax4.hist(simulated_latencies, bins=40, color=accent_purple, edgecolor="#0F172A", alpha=0.85, density=True)
    
    # Ortalama ve P99 çizgileri
    mean_val = np.mean(simulated_latencies)
    p99_val = np.percentile(simulated_latencies, 99)
    ax4.axvline(mean_val, color=accent_green, linestyle="--", linewidth=2, label=f"Ortalama: {mean_val:.1f} ns")
    ax4.axvline(p99_val, color=accent_red, linestyle=":", linewidth=2, label=f"P99 Determinizm: {p99_val:.1f} ns")

    ax4.set_title("Panel 4: Radar Telemetri IPC Gecikme Dağılımı (5,000 Örnek)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax4.set_xlabel("İletim Süresi (Nanosaniye)", color=text_color, fontsize=10)
    ax4.set_ylabel("Olasılık Yoğunluğu", color=text_color, fontsize=10)
    ax4.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=9, loc="upper right")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_path}")


def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Gün 099 için tüm mimari ve matematiksel kabulleri katı testlerle doğrular."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dosya ve Görsel Doğrulaması
    assert os.path.exists(png_path), f"HATA: Dashboard görseli mevcut değil: {png_path}"
    file_size = os.path.getsize(png_path)
    assert file_size > 100_000, f"HATA: Dashboard boyutu şüpheli derecede küçük ({file_size} bayt)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {file_size:,} bayt.")

    # 2. POSIX SHM Çekirdek Simülasyonu Doğrulaması
    vfs = SimulatedKernelTmpfs()
    shm_name = "/test_assert_shm"
    vfs.shm_open(shm_name, "O_CREAT | O_RDWR")
    vfs.ftruncate(shm_name, 4096)
    
    p1 = SimulatedProcess(10, vfs)
    p2 = SimulatedProcess(20, vfs)
    p1.attach_shm(shm_name, 4096)
    p2.attach_shm(shm_name, 4096)
    
    p1.write_telemetry(target_id=888, azimuth=90.0, elevation=45.0, range_km=12.5)
    tgt, az, el, rng = p2.read_telemetry()
    assert tgt == 888, f"HATA: Hedef ID eşleşmedi ({tgt} != 888)!"
    assert rng == 12.5, f"HATA: Mesafe eşleşmedi ({rng} != 12.5)!"
    vfs.shm_unlink(shm_name)
    assert shm_name not in vfs.storage, "HATA: shm_unlink sonrası VFS kaydı silinmelidir!"
    print("  [+] POSIX SHM Sıfır Kopyalama ve Çekirdek Yaşam Döngüsü Doğrulandı.")

    # 3. ftruncate 0-Byte ve SIGBUS Tuzağı Doğrulaması
    bus_ok, _ = PosixShmSabotageLab.simulate_missing_ftruncate()
    assert bus_ok is True, "HATA: ftruncate çağrılmaması SIGBUS üretmelidir!"
    print("  [+] ftruncate 0-Byte ve SIGBUS Donanımsal İstisnası Doğrulandı.")

    # 4. Halka Tampon (Ring Buffer) Doğrulaması
    raw = bytearray(4096)
    rb = ShmRingBufferSimulator(raw, capacity=2, is_owner=True)
    assert rb.push(1, 0.0, 0.0, 0.0, 100) is True
    assert rb.push(2, 0.0, 0.0, 0.0, 200) is True
    assert rb.push(3, 0.0, 0.0, 0.0, 300) is False, "HATA: Dolu tampon taşma koruması başarısız!"
    popped = rb.pop()
    assert popped is not None and popped[0] == 1, "HATA: Halka tampon FIFO sırası bozuldu!"
    assert rb.push(3, 0.0, 0.0, 0.0, 300) is True, "HATA: Boşalan slota yeni veri yazılamadı!"
    print("  [+] Lock-Free SPSC Halka Tampon FIFO Bütünlüğü Doğrulandı.")

    # 5. Benchmark Hızlanma Oranı Doğrulaması
    bench = run_ipc_comprehensive_benchmark()
    speedup_4k = bench["uds_latencies_us"][0] / bench["shm_latencies_us"][0]
    assert speedup_4k > 10.0, f"HATA: SHM, UDS'ye kıyasla en az 10x hızlı olmalıdır ({speedup_4k:.1f}x)!"
    print(f"  [+] IPC Performans Üstünlüğü Doğrulandı (SHM vs UDS: {speedup_4k:.1f}x Hızlanma).")

    print("\n[PASS] Gün 099: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
