# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 7 (CODE 1): İki Kademeli I/O Simülasyon Motoru
Kullanıcı Alanı FILE* Tamponu (setvbuf modları: _IOFBF, _IOLBF, _IONBF) vs Çekirdek Syscall Akışı
"""

from enum import Enum
from typing import List, Tuple, Optional

class BufferMode(Enum):
    IOFBF = 0  # Tam Tamponlu (Full Buffering)
    IOLBF = 1  # Satır Tamponlu (Line Buffering)
    IONBF = 2  # Tamponsuz (No Buffering)

class MockKernelStorage:
    def __init__(self):
        self.raw_disk_data = bytearray()
        self.syscall_write_count = 0
        self.bytes_written_to_kernel = 0

    def sys_write(self, data: bytes) -> int:
        self.syscall_write_count += 1
        self.bytes_written_to_kernel += len(data)
        self.raw_disk_data.extend(data)
        return len(data)

class StdioStreamSimulator:
    def __init__(self, kernel: MockKernelStorage, mode: BufferMode = BufferMode.IOFBF, buffer_size: int = 4096):
        self.kernel = kernel
        self.mode = mode
        self.buffer_size = buffer_size
        self.user_buffer = bytearray()

    def setvbuf(self, mode: BufferMode, size: int) -> None:
        if len(self.user_buffer) > 0:
            raise RuntimeError("EINVAL: setvbuf() cannot be called after I/O has started!")
        self.mode = mode
        self.buffer_size = size

    def fputc(self, char_byte: bytes) -> None:
        self.fwrite(char_byte)

    def fwrite(self, data: bytes) -> int:
        """Kullanıcı alanı tamponlu yazma simülasyonu."""
        if self.mode == BufferMode.IONBF:
            # Tamponsuz: Doğrudan çekirdeğe yaz
            return self.kernel.sys_write(data)

        total_fed = 0
        for b in data:
            byte_val = bytes([b])
            self.user_buffer.append(b)
            total_fed += 1

            # Flush koşulları
            should_flush = False
            if self.mode == BufferMode.IOLBF and byte_val == b"\n":
                should_flush = True
            elif len(self.user_buffer) >= self.buffer_size:
                should_flush = True

            if should_flush:
                self.fflush()

        return total_fed

    def fflush(self) -> None:
        """Kullanıcı tamponunu çekirdeğe boşaltır."""
        if len(self.user_buffer) > 0:
            self.kernel.sys_write(bytes(self.user_buffer))
            self.user_buffer.clear()

# Doğrulama Testi
if __name__ == "__main__":
    kernel_sink = MockKernelStorage()
    stream = StdioStreamSimulator(kernel_sink, mode=BufferMode.IOLBF, buffer_size=64)

    # 1. Satır sonu (\n) olmadan yaz:
    stream.fwrite(b"RADAR_DATA_PART1_NO_NEWLINE")
    print(f"[*] Satır Sonu Yokken -> Çekirdeğe Ulaşan Bayt: {kernel_sink.bytes_written_to_kernel} (Tamponda Bekliyor: {len(stream.user_buffer)}B)")

    # 2. Satır sonu (\n) ekle:
    stream.fwrite(b"_FINISHED\n")
    print(f"[*] Satır Sonu Gelince -> Çekirdeğe Ulaşan Bayt: {kernel_sink.bytes_written_to_kernel} (Syscall Sayısı: {kernel_sink.syscall_write_count})")
    print(f"[*] Diskteki İçerik: {kernel_sink.raw_disk_data.decode('utf-8').strip()}")


# -*- coding: utf-8 -*-
"""
HÜCRE 9 (CODE 2): C++20 SmartStreamWriter ve Deterministik Flush Simülatörü
RAII Akış Yönetimi, Telemetri Moduna Göre Tampon Seçimi ve std::format Uyumu
"""

from typing import Dict, List, Optional

class Cpp20SmartStreamWriter:
    """
    Modern C++20 Hibrit I/O Yöneticisi Simülasyonu
    Metin logları için Tamponlu (Buffered), Yüksek hızlı binary telemetri için Tamponsuz (Unbuffered) mod
    """
    def __init__(self, name: str, is_realtime_telemetry: bool = False):
        self.name = name
        self.is_realtime_telemetry = is_realtime_telemetry
        self.kernel_storage = MockKernelStorage()
        
        # Aviyonik Kuralı: Gerçek zamanlı telemetriyse IONBF, normal log ise IOFBF
        mode = BufferMode.IONBF if is_realtime_telemetry else BufferMode.IOFBF
        self.stream = StdioStreamSimulator(self.kernel_storage, mode=mode, buffer_size=4096)

    def log_message(self, msg: str) -> None:
        """C++20 std::format formatlı metin loglama."""
        encoded = (msg + "\n").encode('utf-8')
        self.stream.fwrite(encoded)

    def write_raw_telemetry_packet(self, packet_bytes: bytes) -> None:
        """Kritik ham paket aktarımı."""
        self.stream.fwrite(packet_bytes)

    def flush_explicit(self) -> None:
        """Belirli aralıklarla zorunlu senkronizasyon."""
        self.stream.fflush()

    def close(self) -> Tuple[int, int]:
        """Scope sonu temizliği (Destructor)."""
        self.stream.fflush()
        return self.kernel_storage.bytes_written_to_kernel, self.kernel_storage.syscall_write_count

# Test ve Doğrulama
# Senaryo 1: Normal Loglayıcı (Tamponlu)
logger = Cpp20SmartStreamWriter("flight_logger", is_realtime_telemetry=False)
for i in range(10):
    logger.log_message(f"STATUS_HEALTH_CHECK_NODE_{i}")
print(f"[SmartStreamWriter: Loglayıcı] 10 Log Yazıldı -> Çekirdeğe İnen Syscall: {logger.kernel_storage.syscall_write_count} (Tamponda Bekliyor)")
bytes_log, calls_log = logger.close()
print(f"[SmartStreamWriter: Loglayıcı] Destructor Sonrası Toplam Syscall: {calls_log}, Yazılan: {bytes_log}B")

# Senaryo 2: Gerçek Zamanlı Telemetri (Tamponsuz)
telemetry = Cpp20SmartStreamWriter("flir_telemetry", is_realtime_telemetry=True)
for i in range(5):
    telemetry.write_raw_telemetry_packet(b"FLIR_PACKET")
print(f"[SmartStreamWriter: Telemetri] 5 Paket Yazıldı -> Anında Çekirdeğe İnen Syscall: {telemetry.kernel_storage.syscall_write_count} (Sıfır Gecikme)")


# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Savunma Laboratuvarı
fork() Öncesi fflush() Unutulması ile Mükerrer Yazma (Sabotage) vs fflush(NULL) Savunması (Defense)
"""

class ForkBufferBugLab:
    def __init__(self):
        pass

    def simulate_fork_with_unflushed_buffer(self, call_fflush_before_fork: bool) -> List[str]:
        """
        fork() öncesi açık tamponun ebeveyn ve çocuk tarafından iki kez yazılması simülasyonu
        """
        # Kullanıcı alanı tamponu
        parent_buffer = ["TELEMETRY_HEADER: "]
        
        # Savunma: fork öncesi fflush yapıldı mı?
        flushed_output = []
        if call_fflush_before_fork:
            flushed_output.extend(parent_buffer)
            parent_buffer.clear()

        # fork() icra ediliyor: Çocuk bellek alanını birebir kopyalar!
        child_buffer = list(parent_buffer)

        # Ebeveyn ve çocuk kendi loglarını ekliyor
        parent_buffer.append("PARENT_FINISH\n")
        child_buffer.append("CHILD_FINISH\n")

        # Her iki süreç exit() yaparken kendi tamponlarını boşaltıyor (flush)
        flushed_output.append("".join(parent_buffer))
        flushed_output.append("".join(child_buffer))

        return flushed_output

lab = ForkBufferBugLab()

# 1. Sabotaj: fflush unutuldu
sabotage_log = lab.simulate_fork_with_unflushed_buffer(call_fflush_before_fork=False)
# 2. Savunma: fflush(NULL) çağrıldı
defense_log = lab.simulate_fork_with_unflushed_buffer(call_fflush_before_fork=True)

print("=== [SABOTAJ TESTİ: fork() ÖNCESİ fflush() UNUTULDU] ===")
for entry in sabotage_log:
    print(f"Diske Yazılan Satır: {entry.strip()}")

print("\n=== [SAVUNMA TESTİ: fork() ÖNCESİ fflush() ÇAĞRILDI] ===")
for entry in defense_log:
    print(f"Diske Yazılan Satır: {entry.strip()}")

# Doğrulama: Sabotajda HEADER kelimesi 2 kez mi geçti?
sabotage_raw = "".join(sabotage_log)
header_count_sabotage = sabotage_raw.count("TELEMETRY_HEADER")
defense_raw = "".join(defense_log)
header_count_defense = defense_raw.count("TELEMETRY_HEADER")

print(f"\n[*] Sabotaj Çıktısındaki Başlık Sayısı: {header_count_sabotage} (MÜKERRER BUG ONAYLANDI!)")
print(f"[*] Savunma Çıktısındaki Başlık Sayısı: {header_count_defense} (TEMİZ VE DOĞRU)")


# -*- coding: utf-8 -*-
"""
HÜCRE 13 (CODE 4): Hata Enjeksiyonu ve Sınır Koşulları
_exit() ile Ani Kapanmada Tampon Kaybı vs exit() ile Tampon Kurtarma
"""

from typing import Tuple

class BufferFaultInjectionLab:
    @staticmethod
    def simulate_termination_data_loss(use_raw_exit: bool) -> Tuple[int, str]:
        """
        exit() vs _exit() çağrısında tamponlanan verinin akıbeti.
        """
        # Kullanıcı alanında bekleyen 120 baytlık veri
        buffered_bytes = 120
        
        if use_raw_exit:
            # _exit(1) / _Exit(1) çağrısı: CRT temizliği YOK, tamponlar ÇÖPE GİDER!
            disked_bytes = 0
            return disked_bytes, "DATA_LOST (Process terminated via _exit: User buffer discarded!)"
        else:
            # exit(0) çağrısı: CRT atexit ve fflush çalıştırır, veri kurtarılır!
            disked_bytes = buffered_bytes
            return disked_bytes, "DATA_SAVED (Process terminated via exit: Buffers automatically flushed)"

lab_fault = BufferFaultInjectionLab()

saved_bytes, msg_normal = lab_fault.simulate_termination_data_loss(use_raw_exit=False)
lost_bytes, msg_raw = lab_fault.simulate_termination_data_loss(use_raw_exit=True)

print("=== [TAMPON BOŞALTMA VE ÇIKIŞ HATALARI LABORATUVARI] ===")
print(f"[Normal exit()] -> {msg_normal} (Kaydedilen: {saved_bytes}B)")
print(f"[Ham _exit()]   -> {msg_raw} (Kaydedilen: {lost_bytes}B)")


# -*- coding: utf-8 -*-
"""
HÜCRE 15 (CODE 5): Kapsamlı Benchmark ve Performans Ölçümü
1 Baytlık vs 4 KB'lık Yazmalarda Tamponlu (fwrite) vs Tamponsuz (write) Hız Karşılaştırması
"""

import numpy as np
from typing import Dict

def run_buffering_benchmark(iterations: int = 50000) -> Dict[str, any]:
    """
    50,000 adet 1-baytlık yazma operasyonunun simülasyonu
    """
    # Süreler nanosaniye cinsinden
    t_syscall = 500.0   # 500 ns syscall bağlam değişimi
    t_user_copy = 2.0   # 2 ns L1 cache bellek kopyalaması
    t_kernel_copy = 1.0 # 1 ns sayfa önbelleği kopyalaması
    buffer_capacity = 4096

    # 1. Tamponsuz POSIX write (Her bayt için 1 syscall!)
    # Toplam süre = 50000 * (t_syscall + t_kernel_copy)
    unbuf_total_ns = iterations * (t_syscall + t_kernel_copy)
    
    # 2. Tamponlu fwrite (4 KB tamponda biriktirip tek syscall!)
    num_flushes = int(np.ceil(iterations / buffer_capacity))
    buf_total_ns = (iterations * t_user_copy) + (num_flushes * t_syscall) + (iterations * t_kernel_copy)

    speedup = unbuf_total_ns / buf_total_ns

    return {
        "iterations": iterations,
        "unbuf_total_ms": unbuf_total_ns / 1e6,
        "buf_total_ms": buf_total_ns / 1e6,
        "num_syscalls_unbuf": iterations,
        "num_syscalls_buf": num_flushes,
        "speedup": speedup
    }

b_res = run_buffering_benchmark(iterations=50000)

print("=== [TAMPONLU (fwrite) VS TAMPONSUZ (write) BENCHMARK] ===")
print(f"İşlem Sayısı (1-Baytlık Yazma): {b_res['iterations']}")
print(f"Tamponsuz POSIX write() Toplam Süre: {b_res['unbuf_total_ms']:.2f} ms (Syscall Sayısı: {b_res['num_syscalls_unbuf']})")
print(f"Tamponlu stdio fwrite()   Toplam Süre: {b_res['buf_total_ms']:.2f} ms (Syscall Sayısı: {b_res['num_syscalls_buf']})")
print(f"\n[*] Küçük Verilerde Tamponlu I/O Hızlanma Oranı: {b_res['speedup']:.2f}x Kat Daha Hızlı!")


# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 6): Görselleştirme Dashboard'u ve Katı Doğrulama (Assertions)
4 Panelli Koyu Tema Dashboard (Tampon Hiyerarşisi, fork Bug'ı, Benchmark Süresi, Mod Karşılaştırması)
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_092_buffered_vs_unbuffered_io.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    # -------------------------------------------------------------
    # PANEL 1: Tamponlu vs Tamponsuz I/O Süre Karşılaştırması (Log Ölçek)
    # -------------------------------------------------------------
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    
    categories = ['1B Yazma (50K Adet)', '64B Yazma (10K Adet)', '4KB Yazma (1K Adet)', '64KB Yazma (100 Adet)']
    unbuf_times_ms = [25.05, 5.20, 0.65, 0.15]
    buf_times_ms = [0.16, 0.25, 0.72, 0.22] # Büyük blokta çift kopyalama yüzünden buf biraz yavaşlar!
    
    x = np.arange(len(categories))
    w = 0.35
    
    rects1 = ax1.bar(x - w/2, unbuf_times_ms, w, label='Tamponsuz POSIX (write)', color='#EF4444', alpha=0.9)
    rects2 = ax1.bar(x + w/2, buf_times_ms, w, label='Tamponlu CRT (fwrite)', color='#10B981', alpha=0.9)
    
    ax1.set_title("1. Yazma Boyutuna Göre İcra Süresi (ms / Log Ölçek)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax1.set_ylabel("Toplam Süre (Milisaniye - ms)", fontsize=11, color='#CBD5E1')
    ax1.set_yscale('log')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, fontsize=9, color='#E2E8F0')
    ax1.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax1.legend(loc='upper right', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 2: setvbuf Üç Modunun Flush Tetikleme Karşılaştırması
    # -------------------------------------------------------------
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    
    modes = ['_IOFBF\n(Tam Tamponlu)', '_IOLBF\n(Satır Tamponlu)', '_IONBF\n(Tamponsuz)']
    flush_speed = [20, 65, 100]  # Flush sıklığı/anındalık puanı
    throughput_eff = [98, 75, 15] # Verim/throughput verimlilik puanı
    
    y = np.arange(len(modes))
    h = 0.3
    
    ax2.barh(y - h/2, flush_speed, h, label='Anlık İletim Skoru (Düşük Gecikme)', color='#38BDF8', alpha=0.85)
    ax2.barh(y + h/2, throughput_eff, h, label='Bant Genişliği Verimi (Throughput)', color='#F59E0B', alpha=0.85)
    
    ax2.set_title("2. setvbuf Tampon Modları Karakteristikleri", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax2.set_yticks(y)
    ax2.set_yticklabels(modes, fontsize=10, color='#E2E8F0', fontweight='bold')
    ax2.set_xlabel("Puan (100 Üzerinden)", fontsize=11, color='#CBD5E1')
    ax2.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax2.legend(loc='lower right', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 3: fork() Öncesi fflush Yapılmazsa Mükerrer Yazma
    # -------------------------------------------------------------
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    
    scenarios = ['Korumasız fork()\n(fflush UNUTULDU)', 'Güvenli fork()\n(fflush ÇAĞRILDI)']
    header_counts = [2, 1] # Mükerrer vs Tekil
    colors3 = ['#EF4444', '#10B981']
    
    bars3 = ax3.bar(scenarios, header_counts, color=colors3, width=0.45, edgecolor='#0F172A', linewidth=2)
    ax3.set_title("3. fork() Çift Yazma (Double Flush) Anomali Analizi", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax3.set_ylabel("Diske Yazılan Başlık Sayısı", fontsize=11, color='#CBD5E1')
    ax3.set_yticks([0, 1, 2, 3])
    ax3.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    
    for b in bars3:
        h_val = b.get_height()
        status_str = "MÜKERRER BUG! (Çift Log)" if h_val == 2 else "KUSURSUZ (Tekil)"
        ax3.annotate(status_str,
                     xy=(b.get_x() + b.get_width() / 2, h_val),
                     xytext=(0, 5), textcoords="offset points",
                     ha='center', va='bottom', fontsize=10, fontweight='bold',
                     color='#F8FAFC')

    # -------------------------------------------------------------
    # PANEL 4: Blok Boyutu Büyüdükçe Çift Kopyalama Cezası
    # -------------------------------------------------------------
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    
    block_sizes_kb = np.array([0.5, 1, 2, 4, 8, 16, 32, 64])
    # Syscall tasarrufu küçük blokta çok yüksek, blok büyüdükçe çift kopyalama yükü artar
    rel_speed_ratio = 50.0 / (1.0 + block_sizes_kb * 0.8) # Normalize edilmiş hız oranı
    
    ax4.plot(block_sizes_kb, rel_speed_ratio, marker='s', color='#38BDF8', linewidth=2.5, label='fwrite / write Hız Oranı (Log Ölçek)')
    ax4.axhline(y=1.0, color='#EF4444', linestyle='--', label='Başabaş Eşiği (1.0x - POSIX Üstünlüğü Başlar)')
    
    ax4.set_title("4. Blok Boyutuna Göre Tamponlama Avantajı Eğrisi", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax4.set_xlabel("Tekil Yazma Blok Boyutu (KB)", fontsize=11, color='#CBD5E1')
    ax4.set_ylabel("Bağıl Hız Oranı (Tamponlu / Tamponsuz)", fontsize=11, color='#CBD5E1')
    ax4.set_xscale('log')
    ax4.set_xticks(block_sizes_kb)
    ax4.set_xticklabels([f"{v:g}K" for v in block_sizes_kb], fontsize=9, color='#E2E8F0')
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

    # 2. Tamponlama Simülatörü Doğrulaması
    k = MockKernelStorage()
    s = StdioStreamSimulator(k, mode=BufferMode.IOFBF, buffer_size=10)
    s.fwrite(b"12345")
    assert k.syscall_write_count == 0, "HATA: IOFBF tampon dolmadan syscall yapmamalı!"
    s.fwrite(b"67890") # Tampon doldu (10 bayt)
    assert k.syscall_write_count == 1, "HATA: Tampon dolunca otomatik flush olmalıydı!"
    assert k.raw_disk_data == b"1234567890", "HATA: Diske yazılan veri bozuk!"
    print("  [+] IOFBF Otomatik Flush Mekanizması Doğrulandı.")

    # 3. Satır Tamponlu (IOLBF) Doğrulaması
    k2 = MockKernelStorage()
    s2 = StdioStreamSimulator(k2, mode=BufferMode.IOLBF, buffer_size=100)
    s2.fwrite(b"NO_NEWLINE")
    assert k2.syscall_write_count == 0, "HATA: IOLBF satır sonu olmadan flush yapmamalı!"
    s2.fwrite(b"\n")
    assert k2.syscall_write_count == 1, "HATA: Satır sonu anında flush tetiklemeliydi!"
    print("  [+] IOLBF Satır Sonu Flush Mekanizması Doğrulandı.")

    # 4. fork() Çift Yazma Bug'ı Doğrulaması
    f_lab = ForkBufferBugLab()
    bad_out = f_lab.simulate_fork_with_unflushed_buffer(call_fflush_before_fork=False)
    good_out = f_lab.simulate_fork_with_unflushed_buffer(call_fflush_before_fork=True)
    assert "".join(bad_out).count("TELEMETRY_HEADER") == 2, "HATA: Sabotaj testinde mükerrer başlık oluşmalıydı!"
    assert "".join(good_out).count("TELEMETRY_HEADER") == 1, "HATA: Savunma testinde tekil başlık korunmalıydı!"
    print("  [+] fork() Çift Yazma Bug'ı ve fflush Savunması Doğrulandı.")

    # 5. Benchmark İstatistik Doğrulaması
    b_data = run_buffering_benchmark(iterations=10000)
    assert b_data["speedup"] > 10.0, "HATA: 1 baytlık yazmalarda tamponlu mod en az 10x hızlı olmalı!"
    print(f"  [+] Benchmark Metrikleri Doğrulandı (Küçük veride Hızlanma: {b_data['speedup']:.1f}x).")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)
