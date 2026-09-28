# -*- coding: utf-8 -*-
# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
# amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz.


# -*- coding: utf-8 -*-
"""
HÜCRE 04 (CODE 1): Python ile I/O Multiplexing Çekirdek Simülasyonu
select (Bitmask O(N)), poll (Array O(N)) ve epoll (RB-Tree + ReadyList O(1)) Motorları
"""

from typing import List, Dict, Set, Tuple
import time

class SimulatedSelectKernel:
    """select(2) mimarisi: Bitmask tabanlı, 1024 FD limitli ve O(N) doğrusal tarama."""
    FD_SETSIZE = 1024

    def __init__(self):
        self.registered_fds: Set[int] = set()

    def register(self, fd: int):
        if fd >= self.FD_SETSIZE:
            raise OverflowError(f"HATA: FD ({fd}) >= FD_SETSIZE (1024) sınırını aştı! Stack taşması!")
        self.registered_fds.add(fd)

    def select(self, active_fds: Set[int]) -> Tuple[List[int], int]:
        """Kullanıcıdan gelen bitmask'i tarar. Döngü sayısı en büyük FD'ye bağlıdır."""
        if not self.registered_fds:
            return [], 0
            
        max_fd = max(self.registered_fds)
        iterations_count = 0
        ready_fds = []
        
        # O(N) Döngüsü: 0'dan max_fd'ye kadar TÜM bitleri tek tek kontrol eder!
        for fd in range(max_fd + 1):
            iterations_count += 1
            if fd in self.registered_fds and fd in active_fds:
                ready_fds.append(fd)
                
        return ready_fds, iterations_count


class SimulatedPollKernel:
    """poll(2) mimarisi: Dinamik dizi tabanlı ancak her çağrıda O(N) dizi kopyalama ve tarama."""
    def __init__(self):
        self.pollfds: List[int] = []

    def register(self, fd: int):
        self.pollfds.append(fd)

    def poll(self, active_fds: Set[int]) -> Tuple[List[int], int, int]:
        """Tüm struct pollfd dizisini çekirdeğe kopyalar ve tamamını döngüyle tarar."""
        bytes_copied = len(self.pollfds) * 8 # Her struct pollfd = 8 bayt
        iterations_count = 0
        ready_fds = []

        for fd in self.pollfds:
            iterations_count += 1
            if fd in active_fds:
                ready_fds.append(fd)

        return ready_fds, iterations_count, bytes_copied


class SimulatedEpollKernel:
    """epoll(7) mimarisi: Kırmızı-Siyah Ağaç izleme kümesi ve O(1) Hazır Listesi (Ready List)."""
    def __init__(self):
        self.monitored_rb_tree: Set[int] = set() # Çekirdekte kalıcı izleme kümesi
        self.ready_list: List[int] = []          # NIC kesmesiyle dolan hazır listesi

    def epoll_ctl_add(self, fd: int):
        """O(log N) Kırmızı-Siyah ağaca ekleme (Sadece bir kez çağrılır!)."""
        self.monitored_rb_tree.add(fd)

    def on_hardware_interrupt(self, active_fds: Set[int]):
        """Ağ kartı kesmesi: Sadece veri gelen soketleri hazır listesine ekler."""
        self.ready_list = [fd for fd in self.monitored_rb_tree if fd in active_fds]

    def epoll_wait(self, maxevents: int) -> Tuple[List[int], int, int]:
        """O(1) Karmaşıklık: Yalnızca hazır listesindeki ilk maxevents elemanı döndürür."""
        events_to_return = self.ready_list[:maxevents]
        # Döngü sayısı SADECE dönen aktif olay kadardır! Asla toplam FD sayısına bağlı değildir!
        iterations_count = len(events_to_return)
        bytes_copied = len(events_to_return) * 12 # epoll_event = 12 bayt
        return events_to_return, iterations_count, bytes_copied


if __name__ == "__main__":
    print("=== I/O MULTIPLEXING ÇEKİRDEK DAVRANIŞ SİMÜLASYONU ===")
    TOTAL_CLIENTS = 1000
    ACTIVE_COUNT = 3 # 1000 istemciden sadece 3 tanesi paket gönderdi!
    active_set = {10, 250, 980}

    # 1. select Testi
    sel = SimulatedSelectKernel()
    for fd in range(TOTAL_CLIENTS):
        sel.register(fd)
    sel_ready, sel_iter = sel.select(active_set)
    print(f"[select] Aktif FD'ler: {sel_ready} | İncelenen FD Sayısı (İterasyon): {sel_iter}")

    # 2. poll Testi
    pol = SimulatedPollKernel()
    for fd in range(TOTAL_CLIENTS):
        pol.register(fd)
    pol_ready, pol_iter, pol_bytes = pol.poll(active_set)
    print(f"[poll]   Aktif FD'ler: {pol_ready} | İncelenen FD Sayısı: {pol_iter} | Kopyalanan Bellek: {pol_bytes} bayt")

    # 3. epoll Testi
    ep = SimulatedEpollKernel()
    for fd in range(TOTAL_CLIENTS):
        ep.epoll_ctl_add(fd)
    ep.on_hardware_interrupt(active_set)
    ep_ready, ep_iter, ep_bytes = ep.epoll_wait(maxevents=64)
    print(f"[epoll]  Aktif FD'ler: {ep_ready} | İncelenen FD Sayısı: {ep_iter} | Kopyalanan Bellek: {ep_bytes} bayt")


# -*- coding: utf-8 -*-
"""
HÜCRE 08 (CODE 2): Python ile Edge-Triggered (ET) vs Level-Triggered (LT) Simülasyonu
Tampon Tüketimi, Kısmi Okuma (Partial Read) ve Soket Kilitlenme (Starvation) Analizi
"""

from typing import Dict, List, Tuple

class SimulatedSocket:
    """Ağ soketi ve çekirdek tampon simülatörü."""
    def __init__(self, fd: int):
        self.fd = fd
        self.rx_buffer = bytearray()
        self.state_changed = False

    def incoming_network_data(self, data: bytes):
        """Ağdan yeni paket geldi (Donanım kesmesi)."""
        was_empty = (len(self.rx_buffer) == 0)
        self.rx_buffer.extend(data)
        if was_empty and len(self.rx_buffer) > 0:
            self.state_changed = True # Durum Boş -> Dolu olarak değişti

    def read_chunk(self, max_bytes: int) -> bytes:
        """Kullanıcının read() çağrısı."""
        chunk = bytes(self.rx_buffer[:max_bytes])
        self.rx_buffer = self.rx_buffer[max_bytes:]
        self.state_changed = False
        return chunk


class TriggerModeSimulator:
    """LT ve ET bildirim mekanizmalarının davranışsal karşılaştırıcısı."""
    
    @staticmethod
    def simulate_level_triggered(sock: SimulatedSocket, read_size: int, loop_count: int) -> List[int]:
        """Level-Triggered: Tamponda veri kaldığı sürece her döngüde uyandırır."""
        wakeups = []
        for loop in range(loop_count):
            if len(sock.rx_buffer) > 0:
                wakeups.append(loop)
                # Kısmi okuma yapılıyor (tampon boşaltılmıyor)
                sock.read_chunk(read_size)
        return wakeups

    @staticmethod
    def simulate_edge_triggered(sock: SimulatedSocket, read_size: int, loop_count: int) -> Tuple[List[int], int]:
        """Edge-Triggered: Yalnızca durum değiştiğinde uyandırır. EAGAIN döngüsü yoksa veri kilitlenir!"""
        wakeups = []
        for loop in range(loop_count):
            if sock.state_changed:
                wakeups.append(loop)
                # Kısmi okuma yapılıyor ve EAGAIN'e kadar tüketilmiyor (Anti-pattern!)
                sock.read_chunk(read_size)
            # Yeni ağ verisi gelmedikçe sock.state_changed False kalır!
        
        stranded_bytes = len(sock.rx_buffer)
        return wakeups, stranded_bytes


if __name__ == "__main__":
    print("=== LEVEL-TRIGGERED vs EDGE-TRIGGERED KARŞILAŞTIRMASI ===")
    
    # Senaryo: Sokete 4096 bayt radar telemetrisi geldi
    # İstemci her döngüde sadece 1024 bayt okuyor
    
    # 1. Level-Triggered Davranışı
    sock_lt = SimulatedSocket(fd=10)
    sock_lt.incoming_network_data(b"X" * 4096)
    lt_wakeups = TriggerModeSimulator.simulate_level_triggered(sock_lt, read_size=1024, loop_count=5)
    print(f"[Level-Triggered] 4096 bayt veri için tetiklenen döngüler: {lt_wakeups} (Tampon bitene kadar 4 kez uyandırdı!)")

    # 2. Edge-Triggered Davranışı (Hatalı Kullanım - EAGAIN döngüsü unutuldu)
    sock_et = SimulatedSocket(fd=20)
    sock_et.incoming_network_data(b"X" * 4096)
    et_wakeups, stranded = TriggerModeSimulator.simulate_edge_triggered(sock_et, read_size=1024, loop_count=5)
    print(f"[Edge-Triggered]  4096 bayt veri için tetiklenen döngüler: {et_wakeups} (SADECE 1 KEZ UYANDIRDI!)")
    print(f"[Edge-Triggered]  KİLİTLENEN VE OKUNAMAYAN VERİ: {stranded} bayt! (Veri sokette rehin kaldı!)")


# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Arıza Simülatörü
select FD_SETSIZE (1024) Bellek Ezilmesi ve Thundering Herd Simülasyonu
"""

from typing import List, Dict, Any, Tuple

class MultiplexingSabotageLab:
    """I/O çoklama sistemlerinde sabotaj ve sınır ihlali simülatörü."""

    @staticmethod
    def simulate_select_overflow_crash(target_fd: int = 1025) -> Tuple[bool, str]:
        """select FD_SETSIZE sınırının aşıldığında sistem çöküşünü modeller."""
        kernel_sel = SimulatedSelectKernel()
        try:
            # 1024 veya üstü bir FD register edilmeye çalışılıyor
            kernel_sel.register(target_fd)
            return False, "HATA: select 1024 sınırını kontrolsüzce kabul etti!"
        except OverflowError as e:
            return True, f"BEKLENEN ÇÖKÜŞ ÖNLENDİ / YAKALANDI: {str(e)}"

    @staticmethod
    def simulate_thundering_herd(num_workers: int = 8, use_exclusive: bool = False) -> Dict[str, Any]:
        """Bir olay geldiğinde kaç worker'ın boş yere uyandırıldığını analiz eder."""
        if use_exclusive:
            # EPOLLEXCLUSIVE aktif: Çekirdek sadece 1 worker uyandırır
            woken_workers = 1
            wasted_wakeups = 0
        else:
            # Geleneksel epoll: TÜM worker'lar uyanır, sadece 1'i accept yapabilir
            woken_workers = num_workers
            wasted_wakeups = num_workers - 1

        cpu_overhead_arbitrary_units = woken_workers * 150 # Context switch maliyeti

        return {
            "num_workers": num_workers,
            "woken_workers": woken_workers,
            "wasted_wakeups": wasted_wakeups,
            "cpu_overhead": cpu_overhead_arbitrary_units,
            "exclusive_active": use_exclusive
        }


if __name__ == "__main__":
    print("=== I/O MULTIPLEXING SABOTAJ VE ARIZA LABORATUVARI ===")
    
    # Test 1: select 1024 Sınır Aşımı
    crash_handled, msg = MultiplexingSabotageLab.simulate_select_overflow_crash(target_fd=1042)
    print(f"[*] select() FD_SETSIZE Taşma Testi: {'BAŞARILI' if crash_handled else 'BAŞARISIZ'}")
    print(f"    Sonuç: {msg}")

    # Test 2: Thundering Herd Analizi
    th_legacy = MultiplexingSabotageLab.simulate_thundering_herd(num_workers=8, use_exclusive=False)
    th_fixed = MultiplexingSabotageLab.simulate_thundering_herd(num_workers=8, use_exclusive=True)
    
    print(f"\n[*] Thundering Herd (Gürleyen Sürü) Karşılaştırması:")
    print(f"    [Geleneksel Epoll]   Uyandırılan: {th_legacy['woken_workers']} | Boşa Çıkan: {th_legacy['wasted_wakeups']} worker | CPU Maliyeti: {th_legacy['cpu_overhead']}")
    print(f"    [EPOLLEXCLUSIVE]     Uyandırılan: {th_fixed['woken_workers']} | Boşa Çıkan: {th_fixed['wasted_wakeups']} worker | CPU Maliyeti: {th_fixed['cpu_overhead']}")


# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): 10,000 Düğümlü Taktik Sensör Ağı (C10K) Event Loop Simülasyonu
Büyük Ölçekli Eşzamanlılıkta CPU Döngü Sayısı ve Gecikme Ölçümü
"""

import time
import numpy as np
from typing import Dict, Any

def simulate_tactical_c10k_event_loop(num_total_nodes: int = 10000, num_active_nodes: int = 50) -> Dict[str, Any]:
    """10,000 düğümlü taktik ağda select, poll ve epoll başarımını simüle eder."""
    
    # Rastgele aktif 50 düğüm belirle
    np.random.seed(42)
    active_fds = set(np.random.choice(num_total_nodes, size=num_active_nodes, replace=False))

    # 1. poll() Simülasyonu (select 1024 sınırından dolayı 10,000 düğümde çalışamaz!)
    t0 = time.perf_counter()
    poll_inspected = 0
    poll_ready = []
    # Çekirdek içi O(N) döngüsü
    for fd in range(num_total_nodes):
        poll_inspected += 1
        if fd in active_fds:
            poll_ready.append(fd)
    t_poll_us = (time.perf_counter() - t0) * 1e6

    # 2. epoll() Simülasyonu (RB-Tree + Ready List O(1))
    t0 = time.perf_counter()
    # Donanım kesmesi doğrudan hazır listesini verir
    epoll_ready = list(active_fds)
    epoll_inspected = len(epoll_ready) # YALNIZCA AKTİF OLANLAR İNCELENİR
    t_epoll_us = (time.perf_counter() - t0) * 1e6

    # Minimum nanosaniye tabanı düzeltmesi
    t_epoll_us = max(t_epoll_us, 0.45)

    return {
        "total_nodes": num_total_nodes,
        "active_nodes": num_active_nodes,
        "poll_inspected_fds": poll_inspected,
        "epoll_inspected_fds": epoll_inspected,
        "poll_time_us": t_poll_us,
        "epoll_time_us": t_epoll_us,
        "speedup_factor": t_poll_us / t_epoll_us
    }


if __name__ == "__main__":
    print("=== TAKTİK AĞ C10K SENSÖR EVENT LOOP DENEYİ ===")
    res = simulate_tactical_c10k_event_loop(num_total_nodes=10000, num_active_nodes=50)
    print(f"[*] Toplam Taktik Düğüm Sayısı : {res['total_nodes']:,}")
    print(f"[*] Aktif Paket Gönderen Düğüm : {res['active_nodes']}")
    print(f"[*] poll()  İncelenen FD Sayısı: {res['poll_inspected_fds']:,} | Süre: {res['poll_time_us']:.2f} µs")
    print(f"[*] epoll() İncelenen FD Sayısı: {res['epoll_inspected_fds']:,} | Süre: {res['epoll_time_us']:.2f} µs")
    print(f"[*] epoll Hızlanma Çarpanı     : {res['speedup_factor']:.1f}x Kat Daha Hızlı!")


# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Kapsamlı I/O Çoklama Benchmark Laboratuvarı
Bağlantı Sayısına Göre Gecikme (Latency) ve CPU İş Yükü (select vs poll vs epoll)
"""

import numpy as np
from typing import Dict, Any

def run_multiplexing_benchmark() -> Dict[str, Any]:
    """100'den 50,000 bağlantıya kadar olan ölçekte mekanizmaların performansını modeller."""
    connection_counts = np.array([100, 500, 1000, 2500, 5000, 10000, 25000, 50000], dtype=np.int64)
    active_ratio = 0.01 # Bağlantıların %1'i aktif (Tipik ağ yükü)

    results = {
        "connections": connection_counts,
        "select_latency_us": [],
        "poll_latency_us": [],
        "epoll_latency_us": [],
        "poll_copy_kb": [],
        "epoll_copy_kb": []
    }

    for n in connection_counts:
        k = max(1, int(n * active_ratio))
        
        # 1. select: 1024'e kadar çalışır, sonrasında tanımsız/taşma
        if n <= 1024:
            t_sel = 0.8 + (n * 0.015) # Mikrosaniye
        else:
            t_sel = np.nan # 1024 üstü geçersiz
        results["select_latency_us"].append(t_sel)

        # 2. poll: O(N) bellek kopyalama ve tarama
        t_pol = 1.2 + (n * 0.028)
        results["poll_latency_us"].append(t_pol)
        results["poll_copy_kb"].append((n * 8) / 1024.0)

        # 3. epoll: O(1) sabit gecikme + sadece K kadar aktif olay
        t_ep = 0.65 + (k * 0.002)
        results["epoll_latency_us"].append(t_ep)
        results["epoll_copy_kb"].append((k * 12) / 1024.0)

    for key in list(results.keys()):
        if key != "connections":
            results[key] = np.array(results[key], dtype=np.float64)

    return results


if __name__ == "__main__":
    print("=== I/O MULTIPLEXING PERFORMANS BENCHMARK'I ===")
    bench = run_multiplexing_benchmark()
    print(f"{'Bağlantı':>8} | {'select (µs)':>12} | {'poll (µs)':>10} | {'epoll (µs)':>10} | {'epoll Hızlanma':>14}")
    print("-" * 64)
    for i, n in enumerate(bench["connections"]):
        s_val = f"{bench['select_latency_us'][i]:.2f}" if not np.isnan(bench["select_latency_us"][i]) else "LIMIT AŞILDI"
        p_val = bench["poll_latency_us"][i]
        e_val = bench["epoll_latency_us"][i]
        speedup = p_val / e_val
        print(f"{n:>8,d} | {s_val:>12} | {p_val:>10.2f} | {e_val:>10.2f} | {speedup:>13.1f}x")


# -*- coding: utf-8 -*-
"""
HÜCRE 20 (CODE 6): 4 Panelli 300 DPI Mühendislik Dashboard'u ve Katı Doğrulama Testleri
select, poll, epoll Evrimi, Karmaşıklık Analizi ve Çekirdek Mimarisi Görselleştirmesi
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_100\gun_100_select_poll_epoll_neden_var.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı I/O Multiplexing dashboard'u üretir."""
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
    # Panel 1: Bağlantı Sayısına Göre Gecikme (Log-Log Eğrisi)
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    conns = np.array([100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000])
    
    # select: 1024'e kadar
    sel_conns = conns[conns <= 1000]
    lat_sel = 0.8 + (sel_conns * 0.015)
    
    lat_poll = 1.2 + (conns * 0.028)
    lat_epoll = 0.65 + (conns * 0.01 * 0.002)

    ax1.plot(sel_conns, lat_sel, marker="o", linewidth=2.2, color=accent_amber, label="select(2) [1024 FD Sınırı]")
    ax1.plot(conns, lat_poll, marker="s", linewidth=2.5, color=accent_red, label="poll(2) [O(N) Doğrusal Tırmanış]")
    ax1.plot(conns, lat_epoll, marker="^", linewidth=3.0, color=accent_green, label="epoll(7) [O(1) Asimptotik Sabit]")

    # 1024 Sınır Çizgisi
    ax1.axvline(1024, color=accent_amber, linestyle=":", alpha=0.7, label="FD_SETSIZE (1024) Limiti")
    
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_title("Panel 1: Bağlantı Sayısına Göre Event Loop Gecikmesi (Log-Log)", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax1.set_xlabel("İzlenen Bağlantı Sayısı (N)", color=text_color, fontsize=10)
    ax1.set_ylabel("Döngü Gecikmesi (µs)", color=text_color, fontsize=10)
    ax1.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 2: Çekirdek-Kullanıcı Bellek Kopyalama Hacmi (KB)
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    copy_poll_kb = (conns * 8) / 1024.0 # pollfd = 8 bayt
    copy_epoll_kb = (conns * 0.01 * 12) / 1024.0 # epoll_event = 12 bayt (aktif %1)

    ax2.plot(conns, copy_poll_kb, marker="s", linewidth=2.5, color=accent_red, label="poll(2): Tüm pollfd Dizisi Kopyalanır")
    ax2.plot(conns, copy_epoll_kb, marker="^", linewidth=2.5, color=accent_green, label="epoll(7): Yalnızca Aktif Olaylar Kopyalanır")

    ax2.set_title("Panel 2: Döngü Başına Kullanıcı-Çekirdek Bellek Kopyalama Hacmi", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax2.set_xlabel("İzlenen Bağlantı Sayısı (N)", color=text_color, fontsize=10)
    ax2.set_ylabel("Kopyalanan Veri (KB / Döngü)", color=text_color, fontsize=10)
    ax2.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=9, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 3: Linux epoll İç Mimari Şeması (Diagram)
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)
    ax3.axis("off")
    ax3.set_title("Panel 3: Linux Çekirdeği epoll İç Mimari Veri Yapıları", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # Kırmızı-Siyah Ağaç Kutusu
    rect_rbtree = plt.Rectangle((0.5, 5.2), 4.2, 3.8, facecolor="#0369A1", edgecolor=accent_blue, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_rbtree)
    ax3.text(2.6, 8.3, "İzleme Kümesi (Kırmızı-Siyah Ağaç)", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(2.6, 7.3, "struct rb_root (O(log N))\n100,000 Soket Burada Kayıtlıdır", ha="center", color="#BAE6FD", fontsize=8)
    ax3.text(2.6, 6.0, "epoll_ctl(ADD/DEL/MOD)", ha="center", color=accent_amber, fontsize=8.5, fontweight="bold")

    # Hazır Listesi Kutusu
    rect_ready = plt.Rectangle((5.3, 5.2), 4.2, 3.8, facecolor="#047857", edgecolor=accent_green, linewidth=2, transform=ax3.transData)
    ax3.add_patch(rect_ready)
    ax3.text(7.4, 8.3, "Hazır Listesi (Ready List - DLL)", ha="center", color=text_color, fontsize=9.5, fontweight="bold")
    ax3.text(7.4, 7.3, "struct list_head (O(1))\nSADECE Aktif 3 Soket Bulunur", ha="center", color="#A7F3D0", fontsize=8)
    ax3.text(7.4, 6.0, "epoll_wait() Anında Döndürür", ha="center", color=accent_blue, fontsize=8.5, fontweight="bold")

    # Donanım Kesmesi Kutusu
    rect_hw = plt.Rectangle((2.0, 1.0), 6.0, 2.8, facecolor="#334155", edgecolor=accent_amber, linewidth=2.2, transform=ax3.transData)
    ax3.add_patch(rect_hw)
    ax3.text(5.0, 3.0, "AĞ KARTI (NIC) DONANIM KESMESİ", ha="center", color=accent_amber, fontsize=10, fontweight="bold")
    ax3.text(5.0, 2.0, "Paket Geldi -> Çekirdek Callback Çalışır\nSoketi O(1) ile Hazır Listesine Ekler", ha="center", color=text_color, fontsize=8.5)

    # Oklar
    ax3.annotate("", xy=(7.4, 5.2), xytext=(6.5, 3.8), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2.5))
    ax3.annotate("", xy=(2.6, 5.2), xytext=(3.5, 3.8), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))

    # -------------------------------------------------------------------------
    # Panel 4: Edge-Triggered (ET) vs Level-Triggered (LT) Dinamiği
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    time_pts = np.linspace(0, 10, 500)
    
    # Tampon Veri Seviyesi (Dalga: Veri geliyor ve kısmi okunuyor)
    buffer_level = np.zeros_like(time_pts)
    buffer_level[(time_pts >= 2.0) & (time_pts < 4.0)] = 4.0
    buffer_level[(time_pts >= 4.0) & (time_pts < 7.0)] = 2.5 # Kısmi okundu
    buffer_level[(time_pts >= 7.0)] = 0.0 # Tamamen bitti

    # Tetiklemeler
    lt_signal = np.zeros_like(time_pts)
    lt_signal[(time_pts >= 2.0) & (time_pts < 7.0)] = 1.0 # LT: Veri varken sürekli aktif!

    et_signal = np.zeros_like(time_pts)
    et_signal[(time_pts >= 2.0) & (time_pts < 2.3)] = 1.0 # ET: Sadece kenar değişiminde tek darbe!

    ax4.plot(time_pts, buffer_level, color=accent_blue, linewidth=2.0, label="Soket Rx Tampon Seviyesi (KB)")
    ax4.step(time_pts, lt_signal * 3.5, color=accent_amber, linestyle="--", linewidth=1.8, label="Level-Triggered Bildirimi (Sürekli)")
    ax4.step(time_pts, et_signal * 3.8, color=accent_red, linewidth=2.2, label="Edge-Triggered Bildirimi (Tek Darbe)")

    ax4.set_title("Panel 4: Edge-Triggered (ET) vs Level-Triggered (LT) Bildirim Dinamiği", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax4.set_xlabel("Zaman (Temsili Akış)", color=text_color, fontsize=10)
    ax4.set_ylabel("Sinyal / Boyut", color=text_color, fontsize=10)
    ax4.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper right")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_path}")


def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Gün 100 için tüm mimari ve matematiksel kabulleri katı testlerle doğrular."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dashboard Görsel Kontrolü
    assert os.path.exists(png_path), f"HATA: Dashboard görseli mevcut değil: {png_path}"
    file_size = os.path.getsize(png_path)
    assert file_size > 100_000, f"HATA: Dashboard boyutu şüpheli ({file_size} bayt)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {file_size:,} bayt.")

    # 2. select() 1024 FD Taşma Doğrulaması
    overflow_ok, _ = MultiplexingSabotageLab.simulate_select_overflow_crash(1025)
    assert overflow_ok is True, "HATA: select 1024 sınır aşımını engellemelidir!"
    print("  [+] select() FD_SETSIZE (1024) Donanımsal/Yazılımsal Taşma Sınırı Doğrulandı.")

    # 3. Edge-Triggered Kısmi Okuma Tuzağı Doğrulaması
    sock_test = SimulatedSocket(fd=88)
    sock_test.incoming_network_data(b"RADAR_FRAME_DATA")
    wakeups, stranded = TriggerModeSimulator.simulate_edge_triggered(sock_test, read_size=5, loop_count=4)
    assert len(wakeups) == 1, "HATA: Edge-triggered yalnızca durum değişiminde 1 kez uyanmalıdır!"
    assert stranded > 0, "HATA: EAGAIN döngüsü olmadan okunan ET sokette veri kilitlenmelidir!"
    print("  [+] Edge-Triggered Bildirim Dinamiği ve Veri Kilitlenme Tuzağı Doğrulandı.")

    # 4. C10K Taktik Ağ Hızlanma Doğrulaması
    c10k = simulate_tactical_c10k_event_loop(num_total_nodes=5000, num_active_nodes=20)
    assert c10k["speedup_factor"] > 5.0, f"HATA: epoll, poll'e kıyasla en az 5x hızlı olmalıdır ({c10k['speedup_factor']:.1f}x)!"
    assert c10k["epoll_inspected_fds"] == 20, "HATA: epoll yalnızca aktif FD'leri incelemelidir!"
    print(f"  [+] C10K Taktik Ağ epoll O(1) Üstünlüğü Doğrulandı ({c10k['speedup_factor']:.1f}x Hızlanma).")

    # 5. Thundering Herd Analiz Doğrulaması
    th = MultiplexingSabotageLab.simulate_thundering_herd(num_workers=16, use_exclusive=True)
    assert th["woken_workers"] == 1, "HATA: EPOLLEXCLUSIVE yalnızca 1 worker uyandırmalıdır!"
    print("  [+] EPOLLEXCLUSIVE ile Thundering Herd Eliminasyonu Doğrulandı.")

    print("\n[PASS] Gün 100: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
