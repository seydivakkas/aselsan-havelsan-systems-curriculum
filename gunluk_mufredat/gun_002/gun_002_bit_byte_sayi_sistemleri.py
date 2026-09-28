"""
===============================================================================
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.
===============================================================================
GÜN 002: Bit, Byte, İkilik ve Hexadecimal Sayı Sistemleri
24-Hücreli Master Mimari Planı Kapsamında Çalıştırılabilir Simülasyon ve Benchmark Motoru
===============================================================================
"""

import time
import struct
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# =============================================================================
# CODE 1: Modül 1 - Donanım Register & Bitwise Manipülasyon Motoru (BitwiseEngine)
# =============================================================================
class HardwareRegister:
    """
    32-bit mikrodenetleyici donanım register'ı (ör. STM32 Control/Status Register).
    Bit maskeleme, kurma (set), temizleme (clear) ve tersleme (toggle) işlemleri.
    """
    def __init__(self, initial_value: int = 0x00000000):
        self.value = initial_value & 0xFFFFFFFF

    def set_bit(self, bit_pos: int):
        """Belirtilen biti 1 yapar: REG |= (1 << bit_pos)"""
        self.value |= (1 << bit_pos)
        self.value &= 0xFFFFFFFF

    def clear_bit(self, bit_pos: int):
        """Belirtilen biti 0 yapar: REG &= ~(1 << bit_pos)"""
        self.value &= ~(1 << bit_pos)
        self.value &= 0xFFFFFFFF

    def toggle_bit(self, bit_pos: int):
        """Belirtilen biti tersler: REG ^= (1 << bit_pos)"""
        self.value ^= (1 << bit_pos)
        self.value &= 0xFFFFFFFF

    def read_bit(self, bit_pos: int) -> int:
        """Belirtilen bitin değerini okur (0 veya 1)."""
        return (self.value >> bit_pos) & 0x01

    def to_binary_str(self) -> str:
        return f"{self.value:032b}"

    def to_hex_str(self) -> str:
        return f"0x{self.value:08X}"

# =============================================================================
# CODE 2: Modül 2 - Savunma Sanayii Telemetri Paketi Ayrıştırma (Bitfield Packing)
# =============================================================================
class AvionicsTelemetryPacket:
    """
    Askeri bir füzeye ait 32-bit sıkıştırılmış telemetri paket formatı:
    [Bit 0..7]   : Sensör ID (8 bit, 0-255)
    [Bit 8..19]  : Yükseklik (Altitude in tens of meters - 12 bit, 0-4095)
    [Bit 20..27] : Hız (Velocity in m/s - 8 bit, 0-255)
    [Bit 28]     : Güdüm Kilidi (Lock Status - 1 bit, 0 veya 1)
    [Bit 29]     : Harbe Hazır (Armed Status - 1 bit, 0 veya 1)
    [Bit 30..31] : Hata Kodu / Status (2 bit, 0-3)
    """
    @staticmethod
    def pack(sensor_id: int, altitude: int, velocity: int, is_locked: bool, is_armed: bool, status: int) -> int:
        word = 0
        word |= (sensor_id & 0xFF)
        word |= ((altitude & 0xFFF) << 8)
        word |= ((velocity & 0xFF) << 20)
        word |= ((1 if is_locked else 0) << 28)
        word |= ((1 if is_armed else 0) << 29)
        word |= ((status & 0x03) << 30)
        return word & 0xFFFFFFFF

    @staticmethod
    def unpack(packed_word: int) -> dict:
        return {
            "sensor_id": packed_word & 0xFF,
            "altitude_m": ((packed_word >> 8) & 0xFFF) * 10,
            "velocity_mps": (packed_word >> 20) & 0xFF,
            "is_locked": bool((packed_word >> 28) & 0x01),
            "is_armed": bool((packed_word >> 29) & 0x01),
            "status": (packed_word >> 30) & 0x03
        }

# =============================================================================
# CODE 3: Modül 3 - Endianness (Bayt Sırası) Tespiti ve Dönüştürme Boru Hattı
# =============================================================================
class EndiannessManager:
    @staticmethod
    def is_system_little_endian() -> bool:
        return sys.byteorder == 'little'

    @staticmethod
    def swap_uint32(val: int) -> int:
        """32-bit Little-Endian <-> Big-Endian manuel bayt değişimi."""
        b0 = (val >> 0) & 0xFF
        b1 = (val >> 8) & 0xFF
        b2 = (val >> 16) & 0xFF
        b3 = (val >> 24) & 0xFF
        return (b0 << 24) | (b1 << 16) | (b2 << 8) | b3

    @staticmethod
    def to_network_bytes(val: int) -> bytes:
        """Big-Endian (Ağ Sırası) olarak paketler."""
        return struct.pack('>I', val)

    @staticmethod
    def from_network_bytes(data: bytes) -> int:
        return struct.unpack('>I', data)[0]

# =============================================================================
# CODE 4: Sabotaj Senaryosu: Endian Uyumsuzluğu ve İşaretli Taşma (Integer Overflow)
# =============================================================================
def run_sabotage_simulation():
    # Senaryo 1: Endianness Uyuşmazlığı
    # Radardan 0x00000001 (1 metre) gönderiliyor.
    # Karşı taraf Big-Endian varsayımıyla Little-Endian okursa:
    original_target_id = 0x12345678
    network_packet = EndiannessManager.to_network_bytes(original_target_id)
    
    # Kasıtlı Hata (Sabotaj): Ağ baytını Little-Endian olarak çözmek
    corrupted_id = struct.unpack('<I', network_packet)[0]

    # Senaryo 2: İşaretli 8-bit Sayı Taşması (Two's Complement Failure)
    # Füze motor itki gücü kontrolü: 127'ye 1 eklenirse -128 olur!
    int8_values = []
    overflow_occurred_at = -1
    val = 120
    for i in range(16):
        # 8-bit signed overflow simulation
        sim_int8 = ((val + 128) % 256) - 128
        int8_values.append(sim_int8)
        if sim_int8 < 0 and overflow_occurred_at == -1:
            overflow_occurred_at = i
        val += 1

    return original_target_id, corrupted_id, int8_values, overflow_occurred_at

# =============================================================================
# CODE 5: Modül 4 - Ampirik Kıyaslama (Bitwise Shifts vs Aritmetik Operatörler)
# =============================================================================
def run_empirical_benchmark(iterations: int = 50000):
    # Çarpma / Bölme vs Bit Kaydırma (x * 8 vs x << 3)
    t0 = time.perf_counter()
    res_arith = 0
    for i in range(iterations):
        res_arith += (i * 8) // 4
    arithmetic_time = (time.perf_counter() - t0) * 1e6

    t0 = time.perf_counter()
    res_bit = 0
    for i in range(iterations):
        res_bit += (i << 3) >> 2
    bitwise_time = (time.perf_counter() - t0) * 1e6

    # Paket Ayrıştırma Gecikmesi (Unpack döngüleri)
    latencies = []
    packet = AvionicsTelemetryPacket.pack(0xAA, 1500, 240, True, True, 0)
    for _ in range(1000):
        t_sub = time.perf_counter()
        _ = AvionicsTelemetryPacket.unpack(packet)
        latencies.append((time.perf_counter() - t_sub) * 1e6)

    return arithmetic_time, bitwise_time, latencies

# =============================================================================
# CODE 6: Modül 5 - 4-Panelli Yayın Kalitesinde Dashboard ve Katı Doğrulama
# =============================================================================
def generate_dashboard(output_path: str):
    orig_id, corrupted_id, int8_vals, overflow_step = run_sabotage_simulation()
    arith_time, bit_time, latencies = run_empirical_benchmark(iterations=100000)

    p50_lat, p95_lat, p99_lat = np.percentile(latencies, [50, 95, 99])

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor('#0f172a')

    for ax_row in axs:
        for ax in ax_row:
            ax.set_facecolor('#1e293b')
            ax.tick_params(colors='#94a3b8')
            ax.xaxis.label.set_color('#cbd5e1')
            ax.yaxis.label.set_color('#cbd5e1')
            ax.title.set_color('#f8fafc')
            ax.grid(True, linestyle='--', alpha=0.2, color='#64748b')

    # Panel 1: Endianness Uyuşmazlığı Sabotaj Etkisi
    categories = ['Orijinal Veri (Big-Endian)', 'Bozuk Okuma (Little-Endian)']
    vals = [orig_id, corrupted_id]
    axs[0, 0].bar(categories, vals, color=['#10b981', '#ef4444'], width=0.4)
    axs[0, 0].set_title('Panel 1: Endianness Arıza Enjeksiyonu (Hedef ID Bozulması)', fontsize=12, fontweight='bold')
    axs[0, 0].set_ylabel('Sayısal Değer (Decimal)')
    for i, v in enumerate(vals):
        axs[0, 0].text(i, v / 2, f"0x{v:08X}", ha='center', color='white', fontweight='bold', fontsize=11)

    # Panel 2: 8-Bit İki'nin Tümleyeni İşaretli Taşma (Integer Overflow)
    x_steps = list(range(len(int8_vals)))
    axs[0, 1].plot(x_steps, int8_vals, marker='o', color='#38bdf8', lw=2, label='8-bit Değişken Değeri')
    axs[0, 1].axhline(0, color='#64748b', linestyle=':')
    axs[0, 1].axvline(overflow_step, color='#ef4444', linestyle='--', label=f'Taşma Noktası (127 -> -128)')
    axs[0, 1].set_title('Panel 2: İki\'nin Tümleyeni İşaretli Taşma Faciası', fontsize=12, fontweight='bold')
    axs[0, 1].set_xlabel('Adım')
    axs[0, 1].set_ylabel('Değer (-128 ile +127)')
    axs[0, 1].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    # Panel 3: Paket Ayrıştırma (Bitfield Unpacking) Gecikme Dağılımı
    axs[1, 0].hist(latencies, bins=35, color='#a855f7', alpha=0.75, density=True)
    axs[1, 0].axvline(p95_lat, color='#f59e0b', linestyle='--', label=f'p95: {p95_lat:.2f} µs')
    axs[1, 0].axvline(p99_lat, color='#ef4444', linestyle='--', label=f'p99: {p99_lat:.2f} µs')
    axs[1, 0].set_title('Panel 3: Aviyonik Telemetri Paket Unpack Gecikmesi (µs)', fontsize=12, fontweight='bold')
    axs[1, 0].set_xlabel('Gecikme (µs)')
    axs[1, 0].set_ylabel('Yoğunluk (Density)')
    axs[1, 0].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    # Panel 4: Bitwise vs Standart Aritmetik İşlem Süresi Kıyaslaması
    ops = ['Aritmetik (* ve //)', 'Bitwise (<< ve >>)']
    times = [arith_time, bit_time]
    axs[1, 1].bar(ops, times, color=['#f43f5e', '#10b981'], width=0.45)
    axs[1, 1].set_title('Panel 4: Bitwise vs Aritmetik 100K İşlem Süresi (µs)', fontsize=12, fontweight='bold')
    axs[1, 1].set_ylabel('Toplam Süre (µs)')
    for i, t in enumerate(times):
        axs[1, 1].text(i, t * 0.5, f"{t:.1f} µs", ha='center', color='white', fontweight='bold', fontsize=11)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 002 Dashboard başarıyla üretildi: {output_path}")

    # ==========================================
    # KATI MİMARİ DOĞRULAMA (STRICT ASSERTIONS)
    # ==========================================
    # 1. Endianness swap doğrulaması
    swapped = EndiannessManager.swap_uint32(orig_id)
    assert EndiannessManager.swap_uint32(swapped) == orig_id, "Endian swap simetrisi bozuldu!"
    # 2. Telemetri bitfield doğrulaması
    test_word = AvionicsTelemetryPacket.pack(0x55, 320, 180, True, False, 2)
    unpacked = AvionicsTelemetryPacket.unpack(test_word)
    assert unpacked["sensor_id"] == 0x55, "Sensör ID bit ayrıştırma hatası!"
    assert unpacked["altitude_m"] == 3200, "Altitude ölçekleme hatası!"
    assert unpacked["is_locked"] is True and unpacked["is_armed"] is False, "Boolean bayrak ayrıştırma hatası!"
    # 3. İki'nin tümleyeni taşma doğrulaması
    assert int8_vals[overflow_step] == -128, "Taşma anında -128 değeri üretilemedi!"
    print("[PASS] Gün 002: Tüm mimari ve matematiksel invariantlar doğrulandı.")

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    img_target = os.path.join(out_dir, "gun_002_bit_byte_sayi_sistemleri.png")
    generate_dashboard(img_target)
