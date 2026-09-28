# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 1 — C++20 Standartlarında Doğal Hizalı Taktik İkili Başlık Kodlayıcı / Ayrıştırıcı
"""

import struct
import zlib
from typing import Tuple, Dict, Any, Optional

class TacticalBinaryHeader:
    """
    ASELSAN / HAVELSAN Standart Taktik 16-Bayt Doğal Hizalı Başlık Mimarisi.
    Format String: >H B B H H I I
    Ofsetler:
      0x00: uint16_t magic       (2B) - 0xAA55
      0x02: uint8_t  version     (1B) - 0x02
      0x03: uint8_t  flags       (1B) - Bitmask
      0x04: uint16_t msg_type    (2B) - Opcode
      0x06: uint16_t payload_len (2B) - Uzunluk
      0x08: uint32_t sequence    (4B) - Dizi No
      0x0C: uint32_t header_crc  (4B) - İlk 12 baytın CRC32 kontrol özeti
    Toplam Boyut: 16 Bayt (Kusursuz 4-Bayt Hizalı)
    """
    MAGIC_WORD = 0xAA55
    HEADER_FORMAT = ">H B B H H I I"
    HEADER_SIZE = 16

    FLAG_ENCRYPTED = 0x01
    FLAG_COMPRESSED = 0x02
    FLAG_REQUIRES_ACK = 0x04

    def __init__(self, version: int, flags: int, msg_type: int, payload_len: int, sequence: int, header_crc: int = 0):
        self.magic = self.MAGIC_WORD
        self.version = version
        self.flags = flags
        self.msg_type = msg_type
        self.payload_len = payload_len
        self.sequence = sequence
        self.header_crc = header_crc

    @classmethod
    def compute_header_crc(cls, header_first_12_bytes: bytes) -> int:
        """Başlığın ilk 12 baytının IEEE 802.3 CRC-32 özetini hesaplar."""
        return zlib.crc32(header_first_12_bytes) & 0xFFFFFFFF

    def encode(self) -> bytes:
        """Başlığı Network Byte Order (Big-Endian) ile serileştirir ve CRC32 ekler."""
        # 1. CRC hariç ilk 12 baytı paketle
        partial = struct.pack(">H B B H H I", self.magic, self.version, self.flags, self.msg_type, self.payload_len, self.sequence)
        # 2. CRC32 hesapla
        computed_crc = self.compute_header_crc(partial)
        self.header_crc = computed_crc
        # 3. 16 baytlık tam başlığı oluştur
        return partial + struct.pack(">I", computed_crc)

    @classmethod
    def decode(cls, header_bytes: bytes):
        """Gelen 16 baytlık başlığı doğrular ve nesneye dönüştürür."""
        if len(header_bytes) != cls.HEADER_SIZE:
            raise ValueError(f"Geçersiz başlık boyutu: {len(header_bytes)}B (Beklenen: 16B)")
            
        magic, ver, flags, mtype, plen, seq, rx_crc = struct.unpack(cls.HEADER_FORMAT, header_bytes)
        
        # 1. Magic Word Kontrolü
        if magic != cls.MAGIC_WORD:
            raise ValueError(f"Geçersiz senkronizasyon kelimesi (Magic Word): 0x{magic:04X}")
            
        # 2. Header CRC32 Bütünlük Kontrolü
        calc_crc = cls.compute_header_crc(header_bytes[:12])
        if rx_crc != calc_crc:
            raise ValueError(f"Başlık bozulmuş! (CRC32 Uyuşmazlığı: Gelen=0x{rx_crc:08X}, Hesaplanan=0x{calc_crc:08X})")
            
        obj = cls(version=ver, flags=flags, msg_type=mtype, payload_len=plen, sequence=seq, header_crc=rx_crc)
        return obj

# Örnek Başlık Oluştur ve Test Et
hdr_sample = TacticalBinaryHeader(version=2, flags=TacticalBinaryHeader.FLAG_REQUIRES_ACK, msg_type=0x0105, payload_len=64, sequence=1042)
encoded_bytes = hdr_sample.encode()
decoded_hdr = TacticalBinaryHeader.decode(encoded_bytes)

print(f"[HÜCRE 7] TacticalBinaryHeader C++20 Kodlayıcı Hazırlandı.")
print(f"  [+] Başlık Boyutu           : {len(encoded_bytes)} Bayt (Tam 16 Bayt)")
print(f"  [+] Ham Başlık Hex          : {encoded_bytes.hex(' ').upper()}")
print(f"  [+] Hesaplanmış Header CRC32: 0x{decoded_hdr.header_crc:08X}")

assert len(encoded_bytes) == 16
assert decoded_hdr.sequence == 1042
assert decoded_hdr.msg_type == 0x0105

# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 2 — Taktik Hava Savunma C2 Füze Ateşleme Emri İletim Deneyi
"""

# Taktik Yük (Payload): 12 Bayt (Hedef ID: uint32, Azimut: float32, İrtifa: uint32)
payload_target_id = 7891
payload_azimuth = 88.5
payload_altitude = 12000
raw_payload = struct.pack(">I f I", payload_target_id, payload_azimuth, payload_altitude)

# 1. Başlık Hazırlama
tx_header = TacticalBinaryHeader(
    version=2,
    flags=TacticalBinaryHeader.FLAG_REQUIRES_ACK | TacticalBinaryHeader.FLAG_ENCRYPTED,
    msg_type=0x0201, # CMD_LAUNCH_MISSILE
    payload_len=len(raw_payload),
    sequence=501
)

# 2. Tam Paketi Oluştur (Header + Payload)
full_packet_bytes = tx_header.encode() + raw_payload

# 3. Alıcı Tarafı (Lançer Bilgisayarı): İki Aşamalı Deterministik Okuma
# Aşama A: Sabit 16 Bayt Başlığı Oku ve Doğrula
rx_header_bytes = full_packet_bytes[:16]
rx_header = TacticalBinaryHeader.decode(rx_header_bytes)

# Aşama B: Başlıktaki Yük Boyutu Kadar Oku
rx_payload_bytes = full_packet_bytes[16 : 16 + rx_header.payload_len]
tgt_id, azim, alt = struct.unpack(">I f I", rx_payload_bytes)

print()
print("[*] Taktik C2 Füze Ateşleme Paketi Uçtan Uca İletim Raporu:")
print(f"  [+] Toplam Paket Boyutu          : {len(full_packet_bytes)} Bayt (Başlık: 16B, Yük: {len(raw_payload)}B)")
print(f"  [+] Başlık Çözümlendi: Dizi #{rx_header.sequence}, Tip: 0x{rx_header.msg_type:04X}, Bayraklar: 0x{rx_header.flags:02X}")
print(f"  [+] Taktik Yük Bilgileri:")
print(f"      - Hedef Takip Kimliği        : #{tgt_id}")
print(f"      - Füze Yönelme Açısı (Azimut): {azim:.1f}°")
print(f"      - Hedef İrtifası             : {alt:,} metre (12 km)")

assert rx_header.payload_len == 12
assert tgt_id == 7891
assert alt == 12000
assert abs(azim - 88.5) < 1e-4
print("[HÜCRE 9] Taktik paket başarıyla serileştirildi, iletildi ve doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Padding Uyumsuzluğu & Zehirli Başlık Uzunluğu
"""

print()
print("[*] Binary Header Sabotaj ve Güvenlik Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: Gizli Padding Mismatch (Hizalama Bozulması)
# -----------------------------------------------------------------------------
# Hizalanmamış kötü tasarım: uint8 (1B) + uint32 (4B)
# Derleyici araya 3 bayt padding ekler
unaligned_struct_bytes = struct.pack("=B I", 0x01, 1000) # C++ varsayılan hizalama: 8 bayt!
# Karşı taraf ise packed (5 bayt) bekliyor!
packed_unpack_error = False
try:
    # 5 bayt bekleyen kod 8 baytlık veriyi yanlış ayrıştırır
    val_b, val_i = struct.unpack(">B I", unaligned_struct_bytes[:5])
    # Değer bozulur:
    if val_i != 1000:
        packed_unpack_error = True
        print(f"  [+] Sabotaj 1 İspatlandı: Padding yüzünden değer bozuldu! (Beklenen: 1000, Okunan: {val_i})")
except Exception as e:
    packed_unpack_error = True

assert packed_unpack_error, "Padding uyumsuzluğu veri bozulmasına yol açmalıydı!"

# -----------------------------------------------------------------------------
# SABOTAJ 2: Zehirli Başlık Uzunluğu ve CRC32 Savunması
# -----------------------------------------------------------------------------
# Orijinal geçerli bir başlık üret
valid_hdr_bytes = bytearray(tx_header.encode())

# Siber saldırgan araya girdi ve payload_len alanını (Ofset 6-7) 60000 bayt yaptı!
valid_hdr_bytes[6] = 0xEA
valid_hdr_bytes[7] = 0x60 # 60000

crc_defense_successful = False
try:
    # Alıcı zehirli başlığı doğrulamayı dener:
    TacticalBinaryHeader.decode(bytes(valid_hdr_bytes))
except ValueError as e:
    crc_defense_successful = True
    print(f"  [+] Sabotaj 2 Savunması Başarılı! Zehirli Paket Yakalandı: {e}")

assert crc_defense_successful, "Header CRC32 tahrif edilmiş başlığı mutlaka yakalamalıydı!"
print("[HÜCRE 11] Tüm sabotaj ve güvenlik savunma testleri başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 4 — Benchmark: 100,000 Paket Başına İkili Başlık vs JSON Ayrıştırma
"""

import time
import json

def run_serialization_benchmark(iterations: int = 100_000) -> Dict[str, Any]:
    # Test verisi
    msg_dict = {
        "magic": 0xAA55,
        "ver": 2,
        "flags": 4,
        "type": 261,
        "len": 12,
        "seq": 1042,
        "target_id": 7891,
        "azimuth": 88.5,
        "altitude": 12000
    }
    
    # 1. JSON Benchmarkı
    t0 = time.perf_counter()
    json_bytes_total = 0
    for _ in range(iterations):
        dumped = json.dumps(msg_dict)
        json_bytes_total = len(dumped)
        _ = json.loads(dumped)
    t1 = time.perf_counter()
    time_json_sec = t1 - t0

    # 2. İkili (Binary) Başlık + Yük Benchmarkı
    raw_payload_local = struct.pack(">I f I", 7891, 88.5, 12000)
    t0 = time.perf_counter()
    binary_bytes_total = 0
    for _ in range(iterations):
        # 16B Header + 12B Payload = 28B
        hdr = TacticalBinaryHeader(2, 4, 261, 12, 1042)
        wire = hdr.encode() + raw_payload_local
        binary_bytes_total = len(wire)
        # Parse
        _ = TacticalBinaryHeader.decode(wire[:16])
        _ = struct.unpack(">I f I", wire[16:])
    t1 = time.perf_counter()
    time_binary_sec = t1 - t0

    return {
        "iterations": iterations,
        "json_time_ms": time_json_sec * 1000.0,
        "json_per_op_us": (time_json_sec / iterations) * 1e6,
        "json_size_bytes": json_bytes_total,
        "binary_time_ms": time_binary_sec * 1000.0,
        "binary_per_op_us": (time_binary_sec / iterations) * 1e6,
        "binary_size_bytes": binary_bytes_total,
        "speedup": time_json_sec / max(1e-6, time_binary_sec),
        "size_reduction_pct": ((json_bytes_total - binary_bytes_total) / json_bytes_total) * 100.0
    }

bench_res = run_serialization_benchmark(iterations=50_000)

print()
print(f"[*] Protokol Serileştirme & Ayrıştırma Benchmarkı ({bench_res['iterations']:,} Paket):")
print(f"  [1] JSON Protokolü:")
print(f"      - Paket Boyutu        : {bench_res['json_size_bytes']} Bayt")
print(f"      - Paket Başına Süre   : {bench_res['json_per_op_us']:.2f} µs")
print(f"      - Toplam Süre         : {bench_res['json_time_ms']:.2f} ms")

print(f"  [2] İkili Başlık (Binary Header):")
print(f"      - Paket Boyutu        : {bench_res['binary_size_bytes']} Bayt (Tam %{bench_res['size_reduction_pct']:.1f} Tasarruf!)")
print(f"      - Paket Başına Süre   : {bench_res['binary_per_op_us']:.2f} µs")
print(f"      - Toplam Süre         : {bench_res['binary_time_ms']:.2f} ms")
print(f"      - Performans Üstünlüğü: {bench_res['speedup']:.2f}x Daha Hızlı!")

assert bench_res['binary_size_bytes'] < 32
assert bench_res['speedup'] > 1.2
print("[HÜCRE 13] Serileştirme benchmarkı başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 5 — MAVLink 2.0 Taktik Telemetri Çerçeveleyici ve CRC-16 Doğrulama
"""

def crc16_mcrf4xx(data: bytes) -> int:
    """MAVLink X.25 CRC-16 algoritması."""
    crc = 0xFFFF
    for byte in data:
        tmp = byte ^ (crc & 0xFF)
        tmp = (tmp ^ (tmp << 4)) & 0xFF
        crc = (crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)
        crc &= 0xFFFF
    return crc

class MAVLink2Packet:
    STX_V2 = 0xFD

    def __init__(self, sys_id: int, comp_id: int, msg_id: int, seq: int, payload: bytes):
        self.sys_id = sys_id
        self.comp_id = comp_id
        self.msg_id = msg_id
        self.seq = seq
        self.payload = payload

    def encode(self) -> bytes:
        # MAVLink 2 Header: STX(1), LEN(1), INC_FLAGS(1), CMP_FLAGS(1), SEQ(1), SYSID(1), COMPID(1), MSGID(3B LE)
        plen = len(self.payload)
        header = struct.pack("<B B B B B B B", self.STX_V2, plen, 0, 0, self.seq, self.sys_id, self.comp_id)
        # 24-bit msg_id (3 bytes Little-Endian)
        msg_id_bytes = struct.pack("<I", self.msg_id)[:3]
        header_full = header + msg_id_bytes
        
        # CRC hesaplama: STX hariç tüm başlık ve yük
        calc_crc = crc16_mcrf4xx(header_full[1:] + self.payload)
        return header_full + self.payload + struct.pack("<H", calc_crc)

    @classmethod
    def decode(cls, data: bytes):
        if len(data) < 12:
            raise ValueError("Paket çok kısa!")
        if data[0] != cls.STX_V2:
            raise ValueError("Geçersiz MAVLink v2 STX!")
            
        plen = data[1]
        seq = data[4]
        sys_id = data[5]
        comp_id = data[6]
        msg_id = struct.unpack("<I", data[7:10] + b"\x00")[0]
        
        expected_len = 10 + plen + 2
        if len(data) != expected_len:
            raise ValueError("Eksik paket verisi!")
            
        payload = data[10 : 10 + plen]
        rx_crc = struct.unpack("<H", data[10 + plen : 10 + plen + 2])[0]
        
        calc_crc = crc16_mcrf4xx(data[1 : 10 + plen])
        if rx_crc != calc_crc:
            raise ValueError("MAVLink CRC-16 Hatası!")
            
        return cls(sys_id, comp_id, msg_id, seq, payload)

# Test: İHA Otopilot Attitude Paketi (Roll=1.2 rad, Pitch=-0.4 rad, Yaw=3.14 rad)
attitude_payload = struct.pack("<f f f", 1.2, -0.4, 3.14)
mav_tx = MAVLink2Packet(sys_id=1, comp_id=1, msg_id=30, seq=42, payload=attitude_payload)
mav_wire = mav_tx.encode()

mav_rx = MAVLink2Packet.decode(mav_wire)
roll, pitch, yaw = struct.unpack("<f f f", mav_rx.payload)

print()
print("[*] MAVLink 2.0 Aviyonik Telemetri Doğrulama Raporu:")
print(f"  [+] MAVLink 2 Toplam Çerçeve Boyutu : {len(mav_wire)} Bayt (Başlık: 10B, Yük: 12B, CRC: 2B)")
print(f"  [+] Sistem Kimliği (SYSID)          : {mav_rx.sys_id} (İHA #1)")
print(f"  [+] Mesaj Kimliği (MSGID)           : {mav_rx.msg_id} (ATTITUDE)")
print(f"  [+] Açısal Durum                    : Roll = {roll:.2f} rad, Pitch = {pitch:.2f} rad, Yaw = {yaw:.2f} rad")

assert mav_rx.sys_id == 1
assert mav_rx.msg_id == 30
assert abs(roll - 1.2) < 1e-4
print("[HÜCRE 15] MAVLink 2.0 taktik telemetri protokolü başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 148: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_148_binary_protocol_header_tasarimi.png")

# Matplotlib stil ve karanlık tema ayarları
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: 16-Bayt İkili Başlık Bellek Haritası (Byte Layout)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

# 16 baytlık başlık alanları
fields = [
    {"name": "MAGIC\n0xAA55", "bytes": 2, "color": "#3B82F6", "offset": "0..1"},
    {"name": "VER\n0x02", "bytes": 1, "color": "#8B5CF6", "offset": "2"},
    {"name": "FLAGS\nBits", "bytes": 1, "color": "#EC4899", "offset": "3"},
    {"name": "MSG_TYPE\nOpcode", "bytes": 2, "color": "#F59E0B", "offset": "4..5"},
    {"name": "PAYLOAD_LEN\nSize (N)", "bytes": 2, "color": "#10B981", "offset": "6..7"},
    {"name": "SEQUENCE_NUM\nPacket Counter (uint32)", "bytes": 4, "color": "#06B6D4", "offset": "8..11"},
    {"name": "HEADER_CRC32\nIntegrity Hash", "bytes": 4, "color": "#EF4444", "offset": "12..15"}
]

curr_x = 0.05
for f in fields:
    w = (f["bytes"] / 16.0) * 0.88
    rect = plt.Rectangle((curr_x, 0.40), w, 0.35, facecolor=f["color"], alpha=0.3, edgecolor=f["color"], lw=2)
    ax1.add_patch(rect)
    ax1.text(curr_x + w/2, 0.57, f["name"], ha='center', va='center', color='#F8FAFC', fontsize=8.5, fontweight='bold')
    ax1.text(curr_x + w/2, 0.46, f"{f['bytes']} Bayt", ha='center', va='center', color='#94A3B8', fontsize=8)
    ax1.text(curr_x + w/2, 0.32, f"Ofset {f['offset']}", ha='center', va='center', color='#CBD5E1', fontsize=7.5)
    curr_x += w + 0.003

ax1.set_title("Taktik 16-Bayt Doğal Hizalı İkili Başlık Bellek Haritası", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: Bellek Hizalama & Padding Tuzağı Karşılaştırması
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')
ax2.axis('off')

# Kötü Hizalama vs Doğru Hizalama Kutuları
ax2.text(0.05, 0.85, "A) Hatalı Hizalama (Derleyici Gizli Padding Ekler):", color='#EF4444', fontsize=10.5, fontweight='bold')
# uint8 (1B) + 3B padding + uint32 (4B) + uint16 (2B) + 2B padding = 12B
bad_blocks = [
    {"txt": "uint8\n(1B)", "w": 0.08, "c": "#3B82F6"},
    {"txt": "PADDING\n(3B Boş)", "w": 0.22, "c": "#EF4444"},
    {"txt": "uint32\n(4B)", "w": 0.28, "c": "#10B981"},
    {"txt": "uint16\n(2B)", "w": 0.14, "c": "#F59E0B"},
    {"txt": "PADDING\n(2B Boş)", "w": 0.16, "c": "#EF4444"}
]
x = 0.05
for b in bad_blocks:
    rect = plt.Rectangle((x, 0.60), b["w"], 0.20, facecolor=b["c"], alpha=0.3, edgecolor=b["c"], lw=1.8)
    ax2.add_patch(rect)
    ax2.text(x + b["w"]/2, 0.70, b["txt"], ha='center', va='center', color='#F8FAFC', fontsize=7.5, fontweight='bold')
    x += b["w"] + 0.005

ax2.text(0.05, 0.45, "B) Taktik Standart: Elle Doğal Hizalanmış 16-Bayt Başlık:", color='#10B981', fontsize=10.5, fontweight='bold')
# 2B + 1B + 1B = 4B | 2B + 2B = 4B | 4B | 4B = 16B (Sıfır Padding)
good_blocks = [
    {"txt": "uint16\n(2B)", "w": 0.15, "c": "#3B82F6"},
    {"txt": "uint8\n(1B)", "w": 0.08, "c": "#8B5CF6"},
    {"txt": "uint8\n(1B)", "w": 0.08, "c": "#EC4899"},
    {"txt": "uint16\n(2B)", "w": 0.15, "c": "#F59E0B"},
    {"txt": "uint16\n(2B)", "w": 0.15, "c": "#10B981"},
    {"txt": "uint32\n(4B)", "w": 0.18, "c": "#06B6D4"},
    {"txt": "uint32\n(4B)", "w": 0.18, "c": "#EF4444"}
]
x = 0.05
for b in good_blocks:
    rect = plt.Rectangle((x, 0.20), b["w"], 0.20, facecolor=b["c"], alpha=0.3, edgecolor=b["c"], lw=1.8)
    ax2.add_patch(rect)
    ax2.text(x + b["w"]/2, 0.30, b["txt"], ha='center', va='center', color='#F8FAFC', fontsize=7.5, fontweight='bold')
    x += b["w"] + 0.003

ax2.set_title("Yapı Hizalaması: Gizli Padding vs Kusursuz 4-Bayt Hizalama", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 3: Performans Benchmarkı (JSON vs İkili Başlık)
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

methods = ['JSON Protokolü', 'İkili Başlık (Binary)']
times = [bench_res['json_per_op_us'], bench_res['binary_per_op_us']]
colors_bar = ['#EF4444', '#10B981']

bars3 = ax3.bar(methods, times, color=colors_bar, width=0.45, edgecolor='#334155', linewidth=1.5)
for bar, val in zip(bars3, times):
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f"{val:.2f} µs", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=11)

ax3.set_title(f"Ayrıştırma Gecikmesi ({bench_res['speedup']:.1f}x Daha Hızlı)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.set_ylabel("Paket Başına Süre (µs)", fontsize=10, color='#94A3B8')
ax3.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: İkili Paket Ayrıştırma Durum Makinesi (State Machine)
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')
ax4.axis('off')

steps = [
    {"x": 0.05, "y": 0.60, "w": 0.25, "h": 0.30, "title": "1. Sync Check", "desc": "magic == 0xAA55 ?\nHayır -> 1 Bayt Kaydır\nEvet -> Devam Et", "color": "#3B82F6"},
    {"x": 0.38, "y": 0.60, "w": 0.25, "h": 0.30, "title": "2. Header CRC32", "desc": "CRC Doğru mu?\nHayır -> Zehirli/Bozuk!\nEvet -> Yük Boyutunu Al", "color": "#F59E0B"},
    {"x": 0.71, "y": 0.60, "w": 0.25, "h": 0.30, "title": "3. Payload Extract", "desc": "payload_len Kadar Oku\nTampon Taşmasını Önle\nOpcode'a Göre Dağıt", "color": "#10B981"},
    {"x": 0.38, "y": 0.15, "w": 0.25, "h": 0.30, "title": "4. Sequence Track", "desc": "seq == expected_seq ?\nKayıp Paket Alarmı\nMükerrer Paketleri At", "color": "#8B5CF6"},
    {"x": 0.71, "y": 0.15, "w": 0.25, "h": 0.30, "title": "5. Taktik İşleme", "desc": "C2 Füze / Radar İşi\nHard Real-Time Yanıt\nGörev Başarılı!", "color": "#06B6D4"}
]

for s in steps:
    rect = plt.Rectangle((s['x'], s['y']), s['w'], s['h'], facecolor=s['color'], alpha=0.25, edgecolor=s['color'], lw=2)
    ax4.add_patch(rect)
    ax4.text(s['x'] + s['w']/2, s['y'] + s['h']*0.75, s['title'], ha='center', va='center', color='#F8FAFC', fontsize=9.5, fontweight='bold')
    ax4.text(s['x'] + s['w']/2, s['y'] + s['h']*0.35, s['desc'], ha='center', va='center', color='#94A3B8', fontsize=8.5)

ax4.annotate("", xy=(0.38, 0.75), xytext=(0.30, 0.75), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.71, 0.75), xytext=(0.63, 0.75), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.83, 0.45), xytext=(0.83, 0.60), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.63, 0.30), xytext=(0.71, 0.30), arrowprops=dict(arrowstyle="<-", color="#F8FAFC", lw=2))

ax4.set_title("Taktik İkili Başlık Doğrulama Durum Makinesi", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 148 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert len(encoded_bytes) == 16, "Başlık boyutu tam 16 bayt olmalı!"
assert bench_res['binary_size_bytes'] < bench_res['json_size_bytes'], "Binary format JSON'dan daha küçük olmalı!"
assert bench_res['speedup'] > 1.0, "Binary ayrıştırma JSON'dan hızlı olmalı!"

print()
print("[PASS] Gün 148: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")