# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 1 — C++20 Endianness Dönüştürücü, Bit-Cast ve Bellek Dizilim Simülatörü
"""

import struct
import sys
from typing import Tuple, List, Dict, Any

class EndiannessEngine:
    """
    POSIX ve C++20 std::endian donanım bellek dönüşümlerini simüle eden sınıf.
    """
    HOST_IS_LITTLE = (sys.byteorder == 'little')

    @staticmethod
    def inspect_system_endian() -> str:
        return "Little-Endian (LSB first)" if EndiannessEngine.HOST_IS_LITTLE else "Big-Endian (MSB first)"

    @staticmethod
    def uint16_to_bytes(val: int, is_big_endian: bool) -> bytes:
        fmt = ">H" if is_big_endian else "<H"
        return struct.pack(fmt, val)

    @staticmethod
    def uint32_to_bytes(val: int, is_big_endian: bool) -> bytes:
        fmt = ">I" if is_big_endian else "<I"
        return struct.pack(fmt, val)

    @staticmethod
    def uint64_to_bytes(val: int, is_big_endian: bool) -> bytes:
        fmt = ">Q" if is_big_endian else "<Q"
        return struct.pack(fmt, val)

    @staticmethod
    def float32_to_bytes(val: float, is_big_endian: bool) -> bytes:
        fmt = ">f" if is_big_endian else "<f"
        return struct.pack(fmt, val)

    @staticmethod
    def bytes_to_uint32(b: bytes, is_big_endian: bool) -> int:
        fmt = ">I" if is_big_endian else "<I"
        return struct.unpack(fmt, b)[0]

    @staticmethod
    def bytes_to_float32(b: bytes, is_big_endian: bool) -> float:
        fmt = ">f" if is_big_endian else "<f"
        return struct.unpack(fmt, b)[0]

    @staticmethod
    def bswap32(val: int) -> int:
        """x86 BSWAP / ARM REV donanım talimatı simülasyonu."""
        return (
            ((val & 0x000000FF) << 24) |
            ((val & 0x0000FF00) << 8)  |
            ((val & 0x00FF0000) >> 8)  |
            ((val & 0xFF000000) >> 24)
        )

# Test Değeri: 0x12345678 (Ondalık: 305419896)
sample_val = 0x12345678
bytes_be = EndiannessEngine.uint32_to_bytes(sample_val, is_big_endian=True)
bytes_le = EndiannessEngine.uint32_to_bytes(sample_val, is_big_endian=False)

print(f"[HÜCRE 7] EndiannessEngine Yüklendi.")
print(f"  [+] Yerel Sistem Mimarisi : {EndiannessEngine.inspect_system_endian()}")
print(f"  [+] 0x12345678 Big-Endian (Network Order)  : {[hex(b) for b in bytes_be]}")
print(f"  [+] 0x12345678 Little-Endian (Host Order)  : {[hex(b) for b in bytes_le]}")

assert bytes_be == bytes([0x12, 0x34, 0x56, 0x78])
assert bytes_le == bytes([0x78, 0x56, 0x34, 0x12])

# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 2 — Heterojen Taktik Füze Telemetrisi: Serialization & Endian Safe İletim
"""

class TacticalTelemetryPacket:
    def __init__(self, msg_id: int, range_m: int, speed_mps: int, heading: float):
        self.msg_id = msg_id
        self.range_m = range_m
        self.speed_mps = speed_mps
        self.heading = heading

    def serialize_network_order(self) -> bytes:
        """Host -> Network Byte Order (Big-Endian) dönüşümü (htons, htonl, bit_cast)."""
        # >H: uint16 big-endian, >I: uint32 big-endian, >f: float32 big-endian
        return struct.pack(">H I I f", self.msg_id, self.range_m, self.speed_mps, self.heading)

    @classmethod
    def deserialize_network_order(cls, data: bytes):
        """Network Byte Order -> Host dönüşümü (ntohs, ntohl, bit_cast)."""
        msg_id, range_m, speed_mps, heading = struct.unpack(">H I I f", data)
        return cls(msg_id, range_m, speed_mps, heading)

# 1. Füze Tarafı (x86_64 Little-Endian) Paketi Hazırlar
telemetry_tx = TacticalTelemetryPacket(
    msg_id=0x0101,
    range_m=1000,      # 1000 metre
    speed_mps=850,     # 850 m/s
    heading=85.5       # 85.5 derece
)

wire_bytes = telemetry_tx.serialize_network_order()

# 2. Radar İstasyonu (DSP / Big-Endian veya ARM Little-Endian) Paketi Çözer
telemetry_rx = TacticalTelemetryPacket.deserialize_network_order(wire_bytes)

print()
print("[*] Taktik Füze Telemetri Güvenli İletim Deneyi:")
print(f"  [+] Kabloya Basılan Ham Paket (Hex) : {wire_bytes.hex(' ').upper()}")
print(f"  [+] Çözümlenen Mesaj Kimliği (ID)   : 0x{telemetry_rx.msg_id:04X} ({telemetry_rx.msg_id})")
print(f"  [+] Çözümlenen Hedef Menzili        : {telemetry_rx.range_m} metre (Beklenen: 1000 m)")
print(f"  [+] Çözümlenen Füze Sürati          : {telemetry_rx.speed_mps} m/s (Beklenen: 850 m/s)")
print(f"  [+] Çözümlenen Baş Açısı            : {telemetry_rx.heading:.1f} derece (Beklenen: 85.5°)")

assert telemetry_rx.range_m == 1000
assert telemetry_rx.speed_mps == 850
assert abs(telemetry_rx.heading - 85.5) < 1e-4
print("[HÜCRE 9] Heterojen telemetri iletimi %100 doğrulukla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Endianness İhmali ile Hedef Kaçırma & Double-Swap
"""

print()
print("[*] Endianness Sabotaj ve Arıza Enjeksiyon Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: Endianness Dönüşümü Yapılmadan Ham Bellek İletimi
# -----------------------------------------------------------------------------
true_range_m = 1000 # 0x000003E8

# Hatalı Kod: Little-Endian x86 ham bellek sırasıyla gönderildi
raw_le_bytes = EndiannessEngine.uint32_to_bytes(true_range_m, is_big_endian=False)
# raw_le_bytes: [0xe8, 0x03, 0x00, 0x00]

# Radar İstasyonu Network Order (Big-Endian) sanarak okudu:
corrupted_range_m = EndiannessEngine.bytes_to_uint32(raw_le_bytes, is_big_endian=True)

print(f"  [+] Sabotaj 1 Sonuçları (Endian Dönüşüm İhmali):")
print(f"      - Gerçek Hedef Menzili      : {true_range_m} metre (1.00 km)")
print(f"      - Ağdan Okunan Bozuk Menzil : {corrupted_range_m:,} metre ({corrupted_range_m/1e6:.2f} milyon km!)")
print(f"      - Hata Oranı                : %{((corrupted_range_m - true_range_m)/true_range_m)*100:,.1f}")

assert corrupted_range_m == 3892510720, "Beklenen bozuk menzil değeri 3,892,510,720 olmalıdır!"

# -----------------------------------------------------------------------------
# SABOTAJ 2: Çift htons() Tuzağı (Double-Swap)
# -----------------------------------------------------------------------------
original_port = 8080 # 0x1F90

# 1. Dönüşüm (Host -> Network)
swap_once = struct.unpack(">H", struct.pack("<H", original_port))[0] # 0x901F = 36895
# 2. Hatalı İkinci Dönüşüm (Tekrar swap!)
swap_twice = struct.unpack(">H", struct.pack("<H", swap_once))[0] # 0x1F90 = 8080

print(f"  [+] Sabotaj 2 Sonuçları (Double-Swap Port Hatası):")
print(f"      - Hedef Port                : {original_port} (0x{original_port:04X})")
print(f"      - Doğru Network Portu       : {swap_once} (0x{swap_once:04X})")
print(f"      - Çift Swap Sonrası Değer   : {swap_twice} (Hatalı Şekilde Geri Döndü!)")

assert swap_twice == original_port, "Çift swap sayıyı aslına geri döndürmüş olmalıdır."
print("[HÜCRE 11] Tüm sabotaj deneyleri başarıyla tamamlandı ve doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 4 — Benchmark: 1,000,000 Paket Başına Endian Dönüşüm Performansı
"""

import time
import struct

def run_endianness_benchmark(iterations: int = 1_000_000) -> Dict[str, Any]:
    sample_val = 0xA1B2C3D4
    
    # 1. Yöntem: struct.pack / unpack (C kütüphanesi simülasyonu)
    t0 = time.perf_counter_ns()
    for _ in range(iterations):
        _ = struct.pack(">I", sample_val)
    t1 = time.perf_counter_ns()
    time_struct_ns = t1 - t0
    
    # 2. Yöntem: Saf Bit Manipülasyonu (bswap32 donanım optimizasyonu)
    t0 = time.perf_counter_ns()
    for _ in range(iterations):
        _ = (
            ((sample_val & 0x000000FF) << 24) |
            ((sample_val & 0x0000FF00) << 8)  |
            ((sample_val & 0x00FF0000) >> 8)  |
            ((sample_val & 0xFF000000) >> 24)
        )
    t1 = time.perf_counter_ns()
    time_bswap_ns = t1 - t0

    return {
        "iterations": iterations,
        "struct_duration_ms": time_struct_ns / 1e6,
        "struct_per_op_ns": time_struct_ns / iterations,
        "bswap_duration_ms": time_bswap_ns / 1e6,
        "bswap_per_op_ns": time_bswap_ns / iterations,
        "speedup": time_struct_ns / max(1, time_bswap_ns)
    }

bench_res = run_endianness_benchmark(iterations=500_000)

print()
print(f"[*] Endianness Dönüşüm Benchmarkı ({bench_res['iterations']:,} İşlem):")
print(f"  [+] struct.pack (>I) Toplam Süre   : {bench_res['struct_duration_ms']:.2f} ms ({bench_res['struct_per_op_ns']:.2f} ns/op)")
print(f"  [+] bswap Bit Operasyonu Süresi    : {bench_res['bswap_duration_ms']:.2f} ms ({bench_res['bswap_per_op_ns']:.2f} ns/op)")
print(f"  [+] Donanım Bitwise Hızlanma Oranı : {bench_res['speedup']:.2f}x Daha Hızlı")

assert bench_res['bswap_per_op_ns'] < 500.0, "Dönüşüm operasyonu nanosaniye seviyesinde olmalıdır!"
print("[HÜCRE 13] Benchmark testleri başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 5 — ASELSAN Radar Taktik İz Ayrıştırıcı: Endian-Aware Güvenli Çerçeve İletimi
"""

class RadarTrackFrame:
    SYNC_WORD = 0xAA55

    def __init__(self, track_id: int, x_cm: int, y_cm: int, vel_mps: int):
        self.track_id = track_id
        self.x_cm = x_cm
        self.y_cm = y_cm
        self.vel_mps = vel_mps

    def encode(self) -> bytes:
        """Tüm alanları Network Byte Order (Big-Endian) ile paketler."""
        payload_len = 16 # 2B sync + 2B len + 4B trk + 4B x + 4B y + 2B vel = 18B
        # >H: sync, >H: len, >I: track_id, >i: x_cm, >i: y_cm, >H: vel_mps
        return struct.pack(">H H I i i H", self.SYNC_WORD, 18, self.track_id, self.x_cm, self.y_cm, self.vel_mps)

    @classmethod
    def decode(cls, frame_bytes: bytes):
        if len(frame_bytes) != 18:
            raise ValueError("Geçersiz paket boyutu!")
        sync, plen, trk, x, y, vel = struct.unpack(">H H I i i H", frame_bytes)
        if sync != cls.SYNC_WORD:
            raise ValueError(f"Senkronizasyon hatası! Geçersiz sync word: 0x{sync:04X}")
        return cls(track_id=trk, x_cm=x, y_cm=y, vel_mps=vel)

# Radar Örneği Oluştur (Menzil: X=45km, Y=12km, Hız=340m/s - Ses Hızı)
frame_tx = RadarTrackFrame(track_id=1042, x_cm=4_500_000, y_cm=1_200_000, vel_mps=340)
wire_data = frame_tx.encode()

# Görev Bilgisayarı Paketi Çözer
frame_rx = RadarTrackFrame.decode(wire_data)

print()
print("[*] ASELSAN Radar Taktik Çerçeve Kodlama ve Doğrulama Raporu:")
print(f"  [+] Çerçeve Boyutu               : {len(wire_data)} bayt")
print(f"  [+] Senkronizasyon Kelimesi      : 0x{RadarTrackFrame.SYNC_WORD:04X}")
print(f"  [+] Çözümlenen Hedef İz Kimliği  : #{frame_rx.track_id}")
print(f"  [+] Hedef Konumu (X, Y)          : X = {frame_rx.x_cm/1e5:.2f} km, Y = {frame_rx.y_cm/1e5:.2f} km")
print(f"  [+] Hedef Hızı                   : {frame_rx.vel_mps} m/s (Mach {frame_rx.vel_mps/340:.1f})")

assert frame_rx.track_id == 1042
assert frame_rx.x_cm == 4_500_000
assert frame_rx.y_cm == 1_200_000
assert frame_rx.vel_mps == 340
print("[HÜCRE 15] Taktik radar çerçevesi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 147: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_147_network_byte_order_ve_endianness.png")

# Matplotlib stil ve karanlık tema ayarları
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: Bellek Bayt Dizilimi (Big-Endian vs Little-Endian)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

# Kutu Çizimleri
be_bytes = ["0x12\n(MSB)", "0x34", "0x56", "0x78\n(LSB)"]
le_bytes = ["0x78\n(LSB)", "0x56", "0x34", "0x12\n(MSB)"]

# Big-Endian Çizim
ax1.text(0.05, 0.85, "A) BIG-ENDIAN (Network Byte Order):", color='#38BDF8', fontsize=11, fontweight='bold')
for i, b in enumerate(be_bytes):
    rect = plt.Rectangle((0.05 + i*0.22, 0.58), 0.18, 0.22, facecolor='#3B82F6', alpha=0.3, edgecolor='#38BDF8', lw=2)
    ax1.add_patch(rect)
    ax1.text(0.05 + i*0.22 + 0.09, 0.69, b, ha='center', va='center', color='#F8FAFC', fontsize=10, fontweight='bold')
    ax1.text(0.05 + i*0.22 + 0.09, 0.52, f"Adres {i}", ha='center', color='#94A3B8', fontsize=9)

# Little-Endian Çizim
ax1.text(0.05, 0.40, "B) LITTLE-ENDIAN (Host Order - x86_64 / ARM):", color='#10B981', fontsize=11, fontweight='bold')
for i, b in enumerate(le_bytes):
    rect = plt.Rectangle((0.05 + i*0.22, 0.13), 0.18, 0.22, facecolor='#10B981', alpha=0.3, edgecolor='#34D399', lw=2)
    ax1.add_patch(rect)
    ax1.text(0.05 + i*0.22 + 0.09, 0.24, b, ha='center', va='center', color='#F8FAFC', fontsize=10, fontweight='bold')
    ax1.text(0.05 + i*0.22 + 0.09, 0.07, f"Adres {i}", ha='center', color='#94A3B8', fontsize=9)

ax1.set_title("0x12345678 Değerinin Fiziksel Bellek Adresi Dizilimi", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: Taktik Füze Hedef Menzil Sapması (Logaritmik Ölçek)
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

ranges = [true_range_m, corrupted_range_m]
labels = ['Doğru Okuma\n(Big-Endian)', 'Hatalı Okuma\n(Endian İhmali)']
colors_r = ['#10B981', '#EF4444']

bars2 = ax2.bar(labels, ranges, color=colors_r, width=0.45, edgecolor='#334155', linewidth=1.5)
ax2.set_yscale('log')

ax2.text(0, true_range_m * 2.5, f"{true_range_m:,} m\n(1 km)", ha='center', color='#F8FAFC', fontweight='bold', fontsize=11)
ax2.text(1, corrupted_range_m * 0.2, f"{corrupted_range_m:,} m\n(3.89 Milyon km!)", ha='center', color='#F8FAFC', fontweight='bold', fontsize=11)

ax2.set_title("Füze Hedef Menzil Sapması (Logaritmik Ölçek)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax2.set_ylabel("Menzil Mesafesi (Metre - Log)", fontsize=10, color='#94A3B8')
ax2.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Endian Dönüşüm Benchmark Performansı
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

bench_methods = ['struct.pack (>I)', 'bswap Bitwise']
bench_durations = [bench_res['struct_duration_ms'], bench_res['bswap_duration_ms']]
colors_b = ['#F59E0B', '#38BDF8']

bars3 = ax3.bar(bench_methods, bench_durations, color=colors_b, width=0.45, edgecolor='#334155', linewidth=1.5)
for bar, val in zip(bars3, bench_durations):
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 1.0, f"{val:.1f} ms", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=11)

ax3.set_title(f"500,000 Dönüşüm İşlemi Süresi ({bench_res['speedup']:.1f}x Hızlanma)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.set_ylabel("Toplam Süre (Milisaniye - ms)", fontsize=10, color='#94A3B8')
ax3.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: Uçtan Uca Ağ İletim Akış Şeması
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')
ax4.axis('off')

flow_steps = [
    {"x": 0.05, "y": 0.60, "w": 0.25, "h": 0.30, "title": "1. Verici (Host LE)", "desc": "Değer: 1000 m\nBellek: E8 03 00 00\nx86_64 Register", "color": "#3B82F6"},
    {"x": 0.38, "y": 0.60, "w": 0.25, "h": 0.30, "title": "2. htonl() / htobe32", "desc": "Byte-Swap (bswap)\nMSB <-> LSB\n00 00 03 E8", "color": "#F59E0B"},
    {"x": 0.71, "y": 0.60, "w": 0.25, "h": 0.30, "title": "3. Kablo (Network BE)", "desc": "RFC 791 Standardı\nBig-Endian Akış\n00 00 03 E8", "color": "#10B981"},
    {"x": 0.38, "y": 0.15, "w": 0.25, "h": 0.30, "title": "4. ntohl() / be32toh", "desc": "Alıcı Byte-Swap\nHost Formatına Çevir\nE8 03 00 00", "color": "#8B5CF6"},
    {"x": 0.71, "y": 0.15, "w": 0.25, "h": 0.30, "title": "5. Alıcı (Host LE)", "desc": "Değer: 1000 m\nKusursuz Okuma!\nRadar Kilitlendi", "color": "#06B6D4"}
]

for s in flow_steps:
    rect = plt.Rectangle((s['x'], s['y']), s['w'], s['h'], facecolor=s['color'], alpha=0.25, edgecolor=s['color'], lw=2)
    ax4.add_patch(rect)
    ax4.text(s['x'] + s['w']/2, s['y'] + s['h']*0.75, s['title'], ha='center', va='center', color='#F8FAFC', fontsize=9.5, fontweight='bold')
    ax4.text(s['x'] + s['w']/2, s['y'] + s['h']*0.35, s['desc'], ha='center', va='center', color='#94A3B8', fontsize=8.5)

ax4.annotate("", xy=(0.38, 0.75), xytext=(0.30, 0.75), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.71, 0.75), xytext=(0.63, 0.75), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.83, 0.45), xytext=(0.83, 0.60), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.63, 0.30), xytext=(0.71, 0.30), arrowprops=dict(arrowstyle="<-", color="#F8FAFC", lw=2))

ax4.set_title("Uçtan Uca Ağ İletim ve Dönüşüm Döngüsü", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 147 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert corrupted_range_m == 3892510720
assert telemetry_rx.range_m == 1000
assert frame_rx.track_id == 1042

print()
print("[PASS] Gün 147: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")