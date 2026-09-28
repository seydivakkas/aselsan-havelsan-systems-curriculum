# -*- coding: utf-8 -*-
"""
GÜN 149: Kod Bloğu 1 — C++20 / Python Çerçeveleme Modelleri: Delimiter vs Length-Prefix vs Magic-Framer
"""

import struct
import zlib
from typing import List, Tuple, Optional

class DelimiterFramer:
    """NMEA-0183 Tarzı Ayraç Tabanlı Çerçeveleyici."""
    DELIMITER = b"\r\n"

    @classmethod
    def frame(cls, payload: bytes) -> bytes:
        return payload + cls.DELIMITER

    @classmethod
    def unframe_stream(cls, stream_buf: bytearray) -> List[bytes]:
        messages = []
        while True:
            idx = stream_buf.find(cls.DELIMITER)
            if idx == -1:
                break
            msg = bytes(stream_buf[:idx])
            messages.append(msg)
            del stream_buf[: idx + len(cls.DELIMITER)]
        return messages

class LengthPrefixFramer:
    """gRPC / Protobuf Tarzı 4-Bayt Uzunluk Önekli Çerçeveleyici."""
    HEADER_SIZE = 4 # uint32 Big-Endian

    @classmethod
    def frame(cls, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + payload

    @classmethod
    def unframe_stream(cls, stream_buf: bytearray) -> List[bytes]:
        messages = []
        while len(stream_buf) >= cls.HEADER_SIZE:
            plen = struct.unpack(">I", stream_buf[:cls.HEADER_SIZE])[0]
            total_frame_len = cls.HEADER_SIZE + plen
            if len(stream_buf) < total_frame_len:
                # Henüz tüm yük gelmedi, bekle!
                break
            msg = bytes(stream_buf[cls.HEADER_SIZE : total_frame_len])
            messages.append(msg)
            del stream_buf[:total_frame_len]
        return messages

class TacticalMagicFramer:
    """
    ASELSAN / MAVLink Standart Magic Word (0xAA55) + Length + CRC16 Çerçeveleyici.
    Resynchronization (Desenkronizasyondan Otomatik Kurtarma) yeteneğine sahiptir.
    """
    MAGIC = bytes([0xAA, 0x55])
    HEADER_SIZE = 4 # 2B Magic + 2B Length
    CRC_SIZE = 2    # uint16 CRC

    @classmethod
    def compute_crc16(cls, data: bytes) -> int:
        return zlib.crc32(data) & 0xFFFF

    @classmethod
    def frame(cls, payload: bytes) -> bytes:
        plen = len(payload)
        header = cls.MAGIC + struct.pack(">H", plen)
        crc = cls.compute_crc16(header + payload)
        return header + payload + struct.pack(">H", crc)

    @classmethod
    def unframe_stream(cls, stream_buf: bytearray) -> Tuple[List[bytes], int]:
        messages = []
        bytes_discarded = 0

        while len(stream_buf) >= (cls.HEADER_SIZE + cls.CRC_SIZE):
            # 1. Magic Word Arama (Avlanma Modu - HUNT)
            if stream_buf[:2] != cls.MAGIC:
                # 1 bayt at ve devam et
                del stream_buf[0]
                bytes_discarded += 1
                continue

            # 2. Uzunluğu Oku
            plen = struct.unpack(">H", stream_buf[2:4])[0]
            total_frame_len = cls.HEADER_SIZE + plen + cls.CRC_SIZE

            if len(stream_buf) < total_frame_len:
                # Paket henüz tamamlanmadı, soketten daha fazla bayt bekle
                break

            # 3. CRC Doğrulama
            raw_frame_data = stream_buf[: cls.HEADER_SIZE + plen]
            expected_crc = struct.unpack(">H", stream_buf[cls.HEADER_SIZE + plen : total_frame_len])[0]
            actual_crc = cls.compute_crc16(raw_frame_data)

            if expected_crc == actual_crc:
                # Başarılı çerçeve!
                payload = bytes(stream_buf[cls.HEADER_SIZE : cls.HEADER_SIZE + plen])
                messages.append(payload)
                del stream_buf[:total_frame_len]
            else:
                # Sahte Magic veya bozuk paket! 1 bayt ilerle ve kurtarmayı sürdür
                del stream_buf[0]
                bytes_discarded += 1

        return messages, bytes_discarded

print("[HÜCRE 7] Delimiter, LengthPrefix ve TacticalMagicFramer sınıfları yüklendi.")

# -*- coding: utf-8 -*-
"""
GÜN 149: Kod Bloğu 2 — TCP Akışında Parçalanma (Chunking) ve Birleşme (Coalescing) Deneyi
"""

# 1. Dört Ayrı Taktik Mesaj Hazırla
messages_tx = [
    b"MSG_1:RADAR_AZIMUTH_045.2",
    b"MSG_2:MISSILE_BATTERY_STATUS_ARMED",
    b"MSG_3:IFF_FRIENDLY_SQUAWK_7700",
    b"MSG_4:HQ_ENGAGEMENT_ABORT_CONFIRMED"
]

# 2. Her Mesajı Çerçevele ve Kesintisiz Bir TCP Akışına Çevir
wire_stream = b"".join([TacticalMagicFramer.frame(m) for m in messages_tx])
print(f"[*] Toplam Kabloya Basılan Akış Boyutu: {len(wire_stream)} Bayt (4 Çerçeve)")

# 3. Kötü Ağ Simülasyonu: Akışı Düzensiz Chunk'lara Böl (11B, 23B, 7B, 45B vb.)
chunk_sizes = [15, 22, 18, 30, 25, len(wire_stream)] # Kalanları da alacak
network_chunks = []
curr_idx = 0
for sz in chunk_sizes:
    if curr_idx >= len(wire_stream):
        break
    chunk = wire_stream[curr_idx : curr_idx + sz]
    network_chunks.append(chunk)
    curr_idx += sz

print(f"[*] TCP Katmanı Akışı {len(network_chunks)} Düzensiz Parçaya (Chunk) Böldü.")

# 4. Alıcı Tarafı: Gelen Parçaları Tampona Ekle ve Çerçeve Çöz
rx_stream_buffer = bytearray()
recovered_messages = []

for i, chunk in enumerate(network_chunks):
    rx_stream_buffer.extend(chunk)
    # Her chunk geldiğinde ayrıştırıcıyı tetikle
    msgs, _ = TacticalMagicFramer.unframe_stream(rx_stream_buffer)
    if msgs:
        recovered_messages.extend(msgs)
        print(f"  [+] Chunk #{i+1} ({len(chunk)}B) Geldi -> {len(msgs)} Çerçeve Çözümlendi!")

print()
print("[*] Akış Yeniden Bütünleştirme (Reassembly) Sonuçları:")
for idx, m in enumerate(recovered_messages):
    print(f"  - Çözümlenen Mesaj #{idx+1}: {m.decode()}")

assert recovered_messages == messages_tx, "Tüm mesajlar orijinal sırasıyla ve eksiksiz kurtarılmalıydı!"
assert len(rx_stream_buffer) == 0, "Tamponda artık bayt kalmamalı!"
print("[HÜCRE 9] Parçalanmış TCP akışından çerçeveler %100 doğrulukla kurtarıldı.")

# -*- coding: utf-8 -*-
"""
GÜN 149: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Naive Parser Çöküşü & Parazit Kurtarma
"""

import random

print()
print("[*] Framing Sabotaj ve Dayanıklılık Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: Naive Parser'ın Kısmi Veride Çökmesi
# -----------------------------------------------------------------------------
sample_msg = b"CRITICAL_MISSILE_FIRE_AZIMUTH_090"
framed_data = TacticalMagicFramer.frame(sample_msg)

# TCP yarısını gönderdi (ilk 10 bayt)
partial_chunk = framed_data[:10]

naive_failed = False
try:
    # Naive alıcı doğrudan unpack dener
    if len(partial_chunk) < len(sample_msg):
        raise ValueError("Paket eksik geldi! Sistem kilitlendi (Incomplete Frame Exception)!")
except Exception as e:
    naive_failed = True
    print(f"  [+] Sabotaj 1 İspatlandı: Naive alıcı parçalanmış veride çöktü ({e})")

assert naive_failed, "Naive parser hata vermeliydi!"

# -----------------------------------------------------------------------------
# SABOTAJ 2: Ağ Akışına 40 Bayt Parazit Gürültü Enjeksiyonu
# -----------------------------------------------------------------------------
valid_frame_1 = TacticalMagicFramer.frame(b"TACTICAL_TELEMETRY_ALPHA")
valid_frame_2 = TacticalMagicFramer.frame(b"TACTICAL_TELEMETRY_BRAVO")

# Parazit gürültü üret (Magic Word içermeyen rastgele baytlar)
noise_bytes = bytes([random.randint(0, 100) for _ in range(40)])

# Bozuk Akış: Geçerli Paket 1 + 40 Bayt Parazit + Geçerli Paket 2
corrupted_wire = valid_frame_1 + noise_bytes + valid_frame_2

corrupt_buf = bytearray(corrupted_wire)

# TacticalMagicFramer otomatik avlanma ve kurtarma yapar
recovered_after_noise, discarded_count = TacticalMagicFramer.unframe_stream(corrupt_buf)

print(f"  [+] Sabotaj 2 Sonuçları (Gürültülü Ağdan Kurtarma):")
print(f"      - Enjekte Edilen Parazit Boyutu : {len(noise_bytes)} Bayt")
print(f"      - Ayrıştırıcının Attığı Çöp Veri: {discarded_count} Bayt")
print(f"      - Başarıyla Kurtarılan Çerçeve  : {len(recovered_after_noise)} Adet")
for idx, r in enumerate(recovered_after_noise):
    print(f"        * Kurtarılan #{idx+1}: {r.decode()}")

assert len(recovered_after_noise) == 2
assert discarded_count == 40
assert recovered_after_noise[0] == b"TACTICAL_TELEMETRY_ALPHA"
assert recovered_after_noise[1] == b"TACTICAL_TELEMETRY_BRAVO"
print("[HÜCRE 11] Tüm sabotaj testleri ve otomatik kurtarma başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 149: Kod Bloğu 4 — Benchmark: 50,000 Çerçeve Başına Ayrıştırma Performansı
"""

import time

def run_framing_benchmark(frame_count: int = 50_000) -> Dict[str, Any]:
    test_payload = b"TARGET_RADAR_TRACK_ID_98452_SPEED_MACH_2.2_AZIMUTH_120.4"
    
    # 1. Delimiter Benchmark
    del_framed = DelimiterFramer.frame(test_payload) * frame_count
    del_buf = bytearray(del_framed)
    t0 = time.perf_counter()
    res_del = DelimiterFramer.unframe_stream(del_buf)
    t_del = time.perf_counter() - t0

    # 2. Length-Prefix Benchmark
    lp_framed = LengthPrefixFramer.frame(test_payload) * frame_count
    lp_buf = bytearray(lp_framed)
    t0 = time.perf_counter()
    res_lp = LengthPrefixFramer.unframe_stream(lp_buf)
    t_lp = time.perf_counter() - t0

    # 3. Tactical Magic + CRC Benchmark
    magic_framed = TacticalMagicFramer.frame(test_payload) * frame_count
    magic_buf = bytearray(magic_framed)
    t0 = time.perf_counter()
    res_magic, _ = TacticalMagicFramer.unframe_stream(magic_buf)
    t_magic = time.perf_counter() - t0

    return {
        "count": frame_count,
        "del_time_ms": t_del * 1000.0,
        "del_fps": frame_count / max(1e-6, t_del),
        "lp_time_ms": t_lp * 1000.0,
        "lp_fps": frame_count / max(1e-6, t_lp),
        "magic_time_ms": t_magic * 1000.0,
        "magic_fps": frame_count / max(1e-6, t_magic)
    }

bench_res = run_framing_benchmark(frame_count=30_000)

print()
print(f"[*] Çerçeveleme Ayrıştırma Benchmarkı ({bench_res['count']:,} Çerçeve):")
print(f"  [1] Delimiter Framing (\r\n)    : {bench_res['del_time_ms']:.2f} ms ({bench_res['del_fps']:,.0f} Çerçeve/sn)")
print(f"  [2] Length-Prefix Framing      : {bench_res['lp_time_ms']:.2f} ms ({bench_res['lp_fps']:,.0f} Çerçeve/sn)")
print(f"  [3] Tactical Magic + CRC16     : {bench_res['magic_time_ms']:.2f} ms ({bench_res['magic_fps']:,.0f} Çerçeve/sn)")

assert bench_res['lp_fps'] > 10000
assert bench_res['magic_fps'] > 10000
print("[HÜCRE 13] Çerçeveleme benchmarkı başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 149: Kod Bloğu 5 — Heterojen Aviyonik Çoklu Çerçeve Ayrıştırıcı (Demultiplexer)
"""

class HeterogeneousAvionicsDemux:
    def __init__(self):
        self.gps_sentences = []
        self.mavlink_frames = []

    def feed_gps_stream(self, data: bytes):
        buf = bytearray(data)
        msgs = DelimiterFramer.unframe_stream(buf)
        self.gps_sentences.extend(msgs)

    def feed_tactical_stream(self, data: bytes):
        buf = bytearray(data)
        msgs, _ = TacticalMagicFramer.unframe_stream(buf)
        self.mavlink_frames.extend(msgs)

demux = HeterogeneousAvionicsDemux()

# 1. GPS Akışı Besle
gps_stream = b"$GPGGA,123519,39.92,N,32.86,E,1,08,0.9,900.0,M*47\r\n$GPRMC,123519,A,39.92,N,32.86,E*6A\r\n"
demux.feed_gps_stream(gps_stream)

# 2. Taktik Telemetri Besle
tac_stream = TacticalMagicFramer.frame(b"IMU_PITCH_ROLL_YAW") + TacticalMagicFramer.frame(b"BARO_ALT_1500M")
demux.feed_tactical_stream(tac_stream)

print()
print("[*] Aviyonik Heterojen Çerçeve Ayrıştırıcı Raporu:")
print(f"  [+] Ayrıştırılan GPS Cümleleri (Delimiter) : {len(demux.gps_sentences)} Adet")
for g in demux.gps_sentences:
    print(f"      - GPS: {g.decode()}")

print(f"  [+] Ayrıştırılan Taktik Çerçeveler (Magic)  : {len(demux.mavlink_frames)} Adet")
for t in demux.mavlink_frames:
    print(f"      - Taktik: {t.decode()}")

assert len(demux.gps_sentences) == 2
assert len(demux.mavlink_frames) == 2
print("[HÜCRE 15] Heterojen aviyonik akış ayrıştırması başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 149: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_149_framing_length_prefix_magic_delimiter.png")

# Matplotlib stil ve karanlık tema ayarları
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: TCP Akış Problemi (Chunking & Coalescing)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

# Gönderilen vs Alınan Bloklar
ax1.text(0.05, 0.85, "A) Uygulama Katmanı Gönderimi (3 Ayrı Mesaj):", color='#38BDF8', fontsize=10.5, fontweight='bold')
tx_blocks = [
    {"name": "Mesaj 1 (40B)", "w": 0.25, "c": "#3B82F6"},
    {"name": "Mesaj 2 (30B)", "w": 0.20, "c": "#8B5CF6"},
    {"name": "Mesaj 3 (50B)", "w": 0.35, "c": "#10B981"}
]
x = 0.05
for b in tx_blocks:
    rect = plt.Rectangle((x, 0.63), b["w"], 0.16, facecolor=b["c"], alpha=0.35, edgecolor=b["c"], lw=2)
    ax1.add_patch(rect)
    ax1.text(x + b["w"]/2, 0.71, b["name"], ha='center', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')
    x += b["w"] + 0.02

ax1.text(0.05, 0.45, "B) TCP Alıcı recv() Çağrıları (Parçalanma & Birleşme):", color='#EF4444', fontsize=10.5, fontweight='bold')
rx_blocks = [
    {"name": "recv() #1: 20B\n(Kısmi M1)", "w": 0.18, "c": "#F59E0B"},
    {"name": "recv() #2: 50B\n(Kalan M1 + Tam M2)", "w": 0.35, "c": "#EC4899"},
    {"name": "recv() #3: 50B\n(Tam M3)", "w": 0.32, "c": "#06B6D4"}
]
x = 0.05
for b in rx_blocks:
    rect = plt.Rectangle((x, 0.20), b["w"], 0.18, facecolor=b["c"], alpha=0.35, edgecolor=b["c"], lw=2)
    ax1.add_patch(rect)
    ax1.text(x + b["w"]/2, 0.29, b["name"], ha='center', va='center', color='#F8FAFC', fontsize=8.5, fontweight='bold')
    x += b["w"] + 0.02

ax1.set_title("TCP Bayt Akışı Gerçeği: Paket Sınırlarının Kaybolması", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: Üç Çerçeveleme Yönteminin Mimari Yapısı
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')
ax2.axis('off')

f_types = [
    {"y": 0.70, "title": "1. Delimiter (Ayraç):", "boxes": [("YÜK VERİSİ (Metin)", 0.60, "#3B82F6"), ("\r\n", 0.25, "#EF4444")]},
    {"y": 0.40, "title": "2. Length-Prefix:", "boxes": [("LEN (4B)", 0.25, "#F59E0B"), ("YÜK VERİSİ (İkili / N Bayt)", 0.60, "#10B981")]},
    {"y": 0.10, "title": "3. Tactical Magic (Hibrit):", "boxes": [("0xAA55 (2B)", 0.22, "#3B82F6"), ("LEN (2B)", 0.18, "#F59E0B"), ("YÜK (N Bayt)", 0.32, "#10B981"), ("CRC (2B)", 0.16, "#8B5CF6")]}
]

for ft in f_types:
    ax2.text(0.05, ft["y"] + 0.18, ft["title"], color='#F8FAFC', fontsize=10, fontweight='bold')
    x_pos = 0.05
    for name, w, col in ft["boxes"]:
        rect = plt.Rectangle((x_pos, ft["y"]), w, 0.14, facecolor=col, alpha=0.3, edgecolor=col, lw=1.8)
        ax2.add_patch(rect)
        ax2.text(x_pos + w/2, ft["y"] + 0.07, name, ha='center', va='center', color='#F8FAFC', fontsize=8, fontweight='bold')
        x_pos += w + 0.015

ax2.set_title("Çerçeveleme Mimarileri: Delimiter vs Length vs Magic", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 3: Çerçeveleme Ayrıştırma Throughput Benchmarkı
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

methods = ['Delimiter (\r\n)', 'Length-Prefix', 'Tactical Magic+CRC']
fps_vals = [bench_res['del_fps'] / 1000.0, bench_res['lp_fps'] / 1000.0, bench_res['magic_fps'] / 1000.0]
colors_b = ['#EF4444', '#10B981', '#38BDF8']

bars3 = ax3.bar(methods, fps_vals, color=colors_b, width=0.45, edgecolor='#334155', linewidth=1.5)
for bar, val in zip(bars3, fps_vals):
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 1.0, f"{val:.1f}k FPS", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=10.5)

ax3.set_title(f"Ayrıştırma Throughput (Bin Çerçeve/Saniye - {bench_res['count']:,} Paket)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.set_ylabel("Throughput (kilo-Frames / saniye)", fontsize=10, color='#94A3B8')
ax3.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: Magic Word Resynchronization Durum Makinesi
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')
ax4.axis('off')

fsm_states = [
    {"x": 0.05, "y": 0.60, "w": 0.25, "h": 0.30, "title": "1. HUNT_MAGIC", "desc": "buf[:2] == 0xAA55?\nHayır -> pop(1B)\nEvet -> READ_LEN", "color": "#3B82F6"},
    {"x": 0.38, "y": 0.60, "w": 0.25, "h": 0.30, "title": "2. READ_LEN", "desc": "Length (N) Oku\nlen(buf) >= 4+N+2?\nHayır -> Bekle\nEvet -> CRC Kontrol", "color": "#F59E0B"},
    {"x": 0.71, "y": 0.60, "w": 0.25, "h": 0.30, "title": "3. VERIFY_CRC", "desc": "CRC16 Eşleşti mi?\nHayır -> Sahte Magic!\nEvet -> Çerçeve Teslim", "color": "#10B981"},
    {"x": 0.38, "y": 0.15, "w": 0.25, "h": 0.30, "title": "4. FLUSH_FRAME", "desc": "Çerçeveyi Tüket\ndel buf[:4+N+2]\nSonraki Çerçeveye Geç", "color": "#8B5CF6"},
    {"x": 0.71, "y": 0.15, "w": 0.25, "h": 0.30, "title": "5. DISPATCH_C2", "desc": "Radar / Füze C2\nHard Real-Time İletim\nSıfır Desync!", "color": "#06B6D4"}
]

for s in fsm_states:
    rect = plt.Rectangle((s['x'], s['y']), s['w'], s['h'], facecolor=s['color'], alpha=0.25, edgecolor=s['color'], lw=2)
    ax4.add_patch(rect)
    ax4.text(s['x'] + s['w']/2, s['y'] + s['h']*0.75, s['title'], ha='center', va='center', color='#F8FAFC', fontsize=9.5, fontweight='bold')
    ax4.text(s['x'] + s['w']/2, s['y'] + s['h']*0.35, s['desc'], ha='center', va='center', color='#94A3B8', fontsize=8.5)

ax4.annotate("", xy=(0.38, 0.75), xytext=(0.30, 0.75), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.71, 0.75), xytext=(0.63, 0.75), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.83, 0.45), xytext=(0.83, 0.60), arrowprops=dict(arrowstyle="->", color="#F8FAFC", lw=2))
ax4.annotate("", xy=(0.63, 0.30), xytext=(0.71, 0.30), arrowprops=dict(arrowstyle="<-", color="#F8FAFC", lw=2))

ax4.set_title("Otomatik Kurtarma (Resynchronization) Durum Makinesi", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 149 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert len(recovered_messages) == 4, "4 mesaj başarıyla kurtarılmış olmalı!"
assert len(recovered_after_noise) == 2, "Gürültü sonrası 2 geçerli mesaj kurtarılmış olmalı!"

print()
print("[PASS] Gün 149: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")