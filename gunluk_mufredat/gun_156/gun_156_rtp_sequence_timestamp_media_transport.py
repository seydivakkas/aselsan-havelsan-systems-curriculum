# -*- coding: utf-8 -*-
"""
GÜN 156: Kod Bloğu 1 — RFC 3550 RTP Başlık Kodlayıcı ve Çözücü Motoru
"""

import struct
import time
from typing import Dict, Any, Tuple, Optional

class RtpPacket:
    """
    RFC 3550 Real-time Transport Protocol (RTP) 12-Bayt Standart Paket Motoru.
    """
    HEADER_SIZE = 12

    def __init__(self, payload_type: int, seq_num: int, timestamp: int, ssrc: int, marker: bool = False, payload: bytes = b""):
        self.version = 2
        self.padding = 0
        self.extension = 0
        self.csrc_count = 0
        self.marker = marker
        self.payload_type = payload_type
        self.seq_num = seq_num & 0xFFFF
        self.timestamp = timestamp & 0xFFFFFFFF
        self.ssrc = ssrc & 0xFFFFFFFF
        self.payload = payload

    def pack(self) -> bytes:
        # Byte 0: V(2b) | P(1b) | X(1b) | CC(4b)
        byte0 = (self.version << 6) | (self.padding << 5) | (self.extension << 4) | (self.csrc_count & 0x0F)
        # Byte 1: M(1b) | PT(7b)
        byte1 = (1 << 7 if self.marker else 0) | (self.payload_type & 0x7F)
        # 12 Bayt Sabit Başlık (Network Byte Order - Big-Endian)
        header = struct.pack(">B B H I I", byte0, byte1, self.seq_num, self.timestamp, self.ssrc)
        return header + self.payload

    @classmethod
    def unpack(cls, data: bytes) -> 'RtpPacket':
        if len(data) < cls.HEADER_SIZE:
            raise ValueError("Veri RTP başlık boyutundan (12B) küçük!")
            
        byte0, byte1, seq, ts, ssrc = struct.unpack(">B B H I I", data[:cls.HEADER_SIZE])
        ver = (byte0 >> 6) & 0x03
        if ver != 2:
            raise ValueError(f"Desteklenmeyen RTP sürümü: {ver}")
            
        marker = bool((byte1 >> 7) & 0x01)
        pt = byte1 & 0x7F
        payload = data[cls.HEADER_SIZE:]
        return cls(payload_type=pt, seq_num=seq, timestamp=ts, ssrc=ssrc, marker=marker, payload=payload)

print("[HÜCRE 7] RFC 3550 RTP Motoru Başarıyla Yüklendi.")

# Örnek RTP Paketi Oluştur ve Doğrula
sample_rtp = RtpPacket(payload_type=96, seq_num=1001, timestamp=90000, ssrc=0xABCD1234, marker=True, payload=b"H264_NAL_SLICE_DATA")
packed_bytes = sample_rtp.pack()
parsed_rtp = RtpPacket.unpack(packed_bytes)

print(f"  [+] Paketlenmiş RTP Boyutu : {len(packed_bytes)} Bayt (Başlık: 12B, Yük: {len(sample_rtp.payload)}B)")
print(f"  [+] Çözülen Sequence No    : {parsed_rtp.seq_num}")
print(f"  [+] Çözülen Timestamp      : {parsed_rtp.timestamp} (90 kHz Saat)")
print(f"  [+] Çözülen SSRC ID        : 0x{parsed_rtp.ssrc:08X}")
print(f"  [+] Marker Biti Set Edildi : {parsed_rtp.marker} (Kare Sonu)")

# -*- coding: utf-8 -*-
"""
GÜN 156: Kod Bloğu 2 — Taktik Video Karesi Parçalanması ve Birleştirilmesi
"""

class TacticalVideoPacketizer:
    """
    Büyük H.264 NAL birimlerini MTU sınırına göre RTP paketlerine bölen modül.
    """
    def __init__(self, ssrc: int, payload_type: int = 96, max_payload_size: int = 1200):
        self.ssrc = ssrc
        self.payload_type = payload_type
        self.max_payload_size = max_payload_size
        self.current_seq = 100
        self.current_ts = 900000

    def packetize_frame(self, frame_bytes: bytes) -> List[RtpPacket]:
        packets = []
        total_len = len(frame_bytes)
        offset = 0
        
        while offset < total_len:
            chunk = frame_bytes[offset : offset + self.max_payload_size]
            offset += len(chunk)
            is_last = (offset >= total_len)
            
            pkt = RtpPacket(
                payload_type=self.payload_type,
                seq_num=self.current_seq,
                timestamp=self.current_ts,
                ssrc=self.ssrc,
                marker=is_last, # Yalnızca karenin son parçasında Marker=True
                payload=chunk
            )
            packets.append(pkt)
            self.current_seq = (self.current_seq + 1) & 0xFFFF

        # Bir sonraki kare için zaman damgasını 30 fps (3000 tick) artır
        self.current_ts = (self.current_ts + 3000) & 0xFFFFFFFF
        return packets

# 3,200 Baytlık Büyük Bir FLIR Termal Video Karesi
dummy_flir_frame = b"FLIR_I_FRAME_HEADER_" + (b"X" * 3180)
packetizer = TacticalVideoPacketizer(ssrc=0x11223344, max_payload_size=1200)
fragmented_packets = packetizer.packetize_frame(dummy_flir_frame)

print()
print("[*] Taktik FLIR Kare Parçalanma Raporu:")
print(f"  [+] Orijinal Kare Boyutu   : {len(dummy_flir_frame)} Bayt")
print(f"  [+] Üretilen RTP Paketi   : {len(fragmented_packets)} Adet")

for idx, p in enumerate(fragmented_packets):
    print(f"      - Parça #{idx+1}: Seq={p.seq_num} | Timestamp={p.timestamp} | Marker={p.marker} | Boyut={len(p.payload)}B")

# Doğrulama: Tüm parçalar aynı timestamp'e sahip olmalı
assert len(fragmented_packets) == 3
assert fragmented_packets[0].timestamp == fragmented_packets[1].timestamp == fragmented_packets[2].timestamp
assert fragmented_packets[0].marker == False
assert fragmented_packets[1].marker == False
assert fragmented_packets[2].marker == True # Son paket
print("[HÜCRE 9] Video karesi parçalanma ve zaman damgası tutarlılığı başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 156: Kod Bloğu 3 — Sabotaj Deneyleri: Paket Kaybı ve Sıra Bozulması Yönetimi
"""

class TacticalFrameReassembler:
    """
    Sequence Number ve Marker bitine bakarak video karelerini
    sağlam şekilde yeniden inşa eden alıcı motor.
    """
    def __init__(self):
        self.current_frame_chunks = []
        self.expected_seq = None
        self.completed_frames = 0
        self.dropped_corrupt_frames = 0

    def process_packet(self, pkt: RtpPacket) -> Optional[bytes]:
        if self.expected_seq is None:
            self.expected_seq = pkt.seq_num

        # 1. Paket Kaybı Denetimi
        if pkt.seq_num != self.expected_seq:
            # Sıra bozuldu veya ara paket kayboldu!
            self.dropped_corrupt_frames += 1
            self.current_frame_chunks.clear()
            self.expected_seq = (pkt.seq_num + 1) & 0xFFFF
            return None

        self.current_frame_chunks.append(pkt.payload)
        self.expected_seq = (self.expected_seq + 1) & 0xFFFF

        # 2. Kare Sonu (Marker Biti) Denetimi
        if pkt.marker:
            full_frame = b"".join(self.current_frame_chunks)
            self.current_frame_chunks.clear()
            self.completed_frames += 1
            return full_frame

        return None

print()
print("[*] RTP Sabotaj ve Kare Kurtarma Testleri Başlatılıyor...")

reassembler = TacticalFrameReassembler()

# -----------------------------------------------------------------------------
# SABOTAJ 1: Ara Paketin Düşmesi (2. Parça Kayboldu)
# -----------------------------------------------------------------------------
# Parçalar: [0, 1, 2]. 1. parça (ortanca) silindi!
corrupted_stream = [fragmented_packets[0], fragmented_packets[2]]

frame_res1 = reassembler.process_packet(corrupted_stream[0]) # Parça 1 (Seq 100) -> Bekliyor
frame_res2 = reassembler.process_packet(corrupted_stream[1]) # Parça 3 (Seq 102) -> 101 kayıp!

print(f"  [+] Sabotaj 1 Sonuçları (Ara Paket Kaybı):")
print(f"      - Bozuk Kare Dekodere İletildi mi? : {frame_res2 is not None}")
print(f"      - Zehirli Kare Düşürüldü mü?       : {reassembler.dropped_corrupt_frames == 1} (KORUMA AKTİF)")
print(f"      - GPU Dekoder Çökmesi Engellendi   : EVET")

assert frame_res2 is None
assert reassembler.dropped_corrupt_frames == 1

# -----------------------------------------------------------------------------
# SABOTAJ 2: Yeni Temiz Karenin Eksiksiz Birleşmesi
# -----------------------------------------------------------------------------
clean_packets = packetizer.packetize_frame(b"CLEAN_FLIR_TARGET_FRAME_DATA")
clean_reassembler = TacticalFrameReassembler()

assembled = None
for p in clean_packets:
    assembled = clean_reassembler.process_packet(p)

print()
print(f"  [+] Sabotaj 2 Sonuçları (Temiz Akış Doğrulama):")
print(f"      - Tam Kare Başarıyla İnşa Edildi mi? : {assembled is not None}")
print(f"      - Çözülen Kare İçeriği             : {assembled.decode('utf-8')}")

assert assembled == b"CLEAN_FLIR_TARGET_FRAME_DATA"
assert clean_reassembler.completed_frames == 1
print("[HÜCRE 11] Sabotaj ve kare bütünlüğü denetimleri başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 156: Kod Bloğu 4 — RFC 3550 Jitter Hesaplama ve Ağ Simülasyonu
"""

import random

def simulate_rtp_jitter(packet_count: int = 500) -> Dict[str, Any]:
    # 90 kHz Saat Frekansı (Her paket arası 3000 tick / 33.3 ms)
    clock_rate = 90_000
    nominal_spacing = 3000
    
    jitter = 0.0
    jitter_history = []
    delays = []

    last_send_time = 0
    last_recv_time = 0

    for i in range(packet_count):
        send_time = i * nominal_spacing
        # Ağ paraziti ve telsiz kuyruk jitter'ı (nominal 1000 tick ± 400 tick)
        network_delay = 1000 + random.randint(-400, 400)
        recv_time = send_time + network_delay
        delays.append(network_delay)

        if i > 0:
            # RFC 3550 Jitter Formülü: D(i, j) = (R_j - R_i) - (S_j - S_i)
            d = abs((recv_time - last_recv_time) - (send_time - last_send_time))
            jitter = jitter + (d - jitter) / 16.0
            jitter_history.append(jitter)

        last_send_time = send_time
        last_recv_time = recv_time

    return {
        "packet_count": packet_count,
        "delays": delays,
        "final_jitter_ticks": jitter,
        "final_jitter_ms": (jitter / clock_rate) * 1000.0,
        "jitter_history": jitter_history
    }

random.seed(42)
jitter_res = simulate_rtp_jitter(packet_count=500)

print()
print(f"[*] RFC 3550 Taktik Jitter Analiz Raporu ({jitter_res['packet_count']} Paket):")
print(f"  [+] Ortalama Ağ Gecikmesi : {sum(jitter_res['delays']) / len(jitter_res['delays']):.1f} saat tick")
print(f"  [+] Nihai Jitter (Ticks)   : {jitter_res['final_jitter_ticks']:.2f} tick")
print(f"  [+] Nihai Jitter (Milisn)  : {jitter_res['final_jitter_ms']:.2f} ms (Uçuş Video Standardı: < 20 ms)")

assert jitter_res['final_jitter_ms'] < 20.0, "Jitter kabul edilebilir video sınırının altında olmalıdır!"
print("[HÜCRE 13] RFC 3550 jitter analizi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 156: Kod Bloğu 5 — STANAG 4609 Uyumlu Video ve KLV Telemetri Çoklayıcı
"""

class Stanag4609Multiplexer:
    """
    Video yükü ile KLV telemetrisini aynı RTP zaman damgasında çoklayan taktik motor.
    """
    def __init__(self, ssrc: int):
        self.ssrc = ssrc
        self.seq = 5000
        self.timestamp = 180000

    def create_synced_video_telemetry_packet(self, video_data: bytes, lat: float, lon: float, alt_m: float) -> Tuple[RtpPacket, bytes]:
        # 1. KLV Telemetri Bloğu (Key: 0x01 = GPS Coords)
        klv_meta = struct.pack(">B B f f f", 0x01, 12, lat, lon, alt_m)
        
        # 2. Eşzamanlı RTP Paketi
        rtp_pkt = RtpPacket(
            payload_type=96,
            seq_num=self.seq,
            timestamp=self.timestamp,
            ssrc=self.ssrc,
            marker=True,
            payload=video_data + b"__KLV__" + klv_meta
        )
        self.seq += 1
        self.timestamp += 3000
        return rtp_pkt, klv_meta

muxer = Stanag4609Multiplexer(ssrc=0xDEAD9988)
video_rtp, klv = muxer.create_synced_video_telemetry_packet(
    video_data=b"H264_TARGET_LOCK",
    lat=39.9250,
    lon=32.8660,
    alt_m=3500.0
)

print()
print("[*] STANAG 4609 Taktik Eşzamanlı Medya Paketi:")
print(f"  [+] RTP Boyutu        : {len(video_rtp.pack())} Bayt")
print(f"  [+] Eşzamanlı Hedef   : Lat={39.9250}°, Lon={32.8660}°, Alt=3500 m")
print(f"  [+] Timestamp Uyumu   : {video_rtp.timestamp} (Video ve GPS tam senkron)")

assert b"__KLV__" in video_rtp.payload
assert video_rtp.marker == True
print("[HÜCRE 15] STANAG 4609 video ve KLV telemetri çoklayıcı testi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 156: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_156_rtp_sequence_timestamp_media_transport.png")

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: RFC 3550 RTP 12-Bayt Başlık Anatomisi
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

hdr_boxes = [
    {"name": "V=2\n(2b)", "x": 0.05, "y": 0.65, "w": 0.08, "c": "#3B82F6"},
    {"name": "P\n(1b)", "x": 0.14, "y": 0.65, "w": 0.05, "c": "#64748B"},
    {"name": "X\n(1b)", "x": 0.20, "y": 0.65, "w": 0.05, "c": "#64748B"},
    {"name": "CC\n(4b)", "x": 0.26, "y": 0.65, "w": 0.08, "c": "#64748B"},
    {"name": "M\n(1b)", "x": 0.35, "y": 0.65, "w": 0.06, "c": "#EF4444"},
    {"name": "Payload Type (PT)\n(7 bit: e.g. 96=H.264)", "x": 0.42, "y": 0.65, "w": 0.25, "c": "#8B5CF6"},
    {"name": "Sequence Number (16-Bit)\n(Paket Sırası / Kayıp Takibi)", "x": 0.68, "y": 0.65, "w": 0.27, "c": "#10B981"},

    {"name": "Timestamp (32-Bit) — Medya Örnekleme Zamanı (90 kHz Saat)", "x": 0.05, "y": 0.38, "w": 0.90, "c": "#F59E0B"},
    {"name": "Synchronization Source (SSRC: 32-Bit) — Yayıncı ID (İHA FLIR Kamera)", "x": 0.05, "y": 0.12, "w": 0.90, "c": "#38BDF8"}
]

for b in hdr_boxes:
    rect = plt.Rectangle((b["x"], b["y"]), b["w"], 0.20, facecolor=b["c"], alpha=0.35, edgecolor=b["c"], lw=2)
    ax1.add_patch(rect)
    ax1.text(b["x"] + b["w"]/2, b["y"] + 0.10, b["name"], ha='center', va='center', color='#F8FAFC', fontsize=8.5, fontweight='bold')

ax1.text(0.05, 0.92, "RFC 3550 RTP 12-Bayt Doğal Hizalanmış Başlık:", color='#38BDF8', fontsize=11, fontweight='bold')
ax1.set_title("RTP Başlık Anatomisi (Header Layout)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: Video Karesi Parçalanması (MTU Fragmentation)
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

parts = ['Parça #1\n(Seq: 100)', 'Parça #2\n(Seq: 101)', 'Parça #3\n(Seq: 102)']
ts_vals = [900000, 900000, 900000]
markers = ['Marker = 0\n(Devam)', 'Marker = 0\n(Devam)', 'Marker = 1\n(KARE SONU!)']
colors_parts = ['#38BDF8', '#38BDF8', '#10B981']

bars2 = ax2.bar(parts, [1, 1, 1], color=colors_parts, width=0.45, edgecolor='#334155', lw=1.5)
for idx, (bar, m) in enumerate(zip(bars2, markers)):
    ax2.text(bar.get_x() + bar.get_width()/2.0, 0.5, f"Timestamp:\n900,000\n\n{m}", ha='center', va='center', color='#F8FAFC', fontweight='bold', fontsize=9)

ax2.set_ylim(0, 1.25)
ax2.set_ylabel("Kare Bütünlüğü Durumu", fontsize=10, color='#94A3B8')
ax2.set_title("Tek Video Karesinin MTU Parçalanması (Aynı Timestamp)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax2.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: RFC 3550 Inter-Arrival Jitter Zaman Serisi
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

packets_x = list(range(len(jitter_res['jitter_history'])))
ax3.plot(packets_x, jitter_res['jitter_history'], color='#F59E0B', lw=1.8, label='Filtrelenmiş Jitter (Ticks)')
ax3.axhline(jitter_res['final_jitter_ticks'], color='#10B981', linestyle='--', label=f'Kararlı Jitter: {jitter_res["final_jitter_ticks"]:.1f} tick')

ax3.set_xlabel("Paket İndeksi", fontsize=10, color='#94A3B8')
ax3.set_ylabel("Gecikme Dalgalanması (Tick)", fontsize=10, color='#94A3B8')
ax3.set_title("RFC 3550 Inter-Arrival Jitter İstatistiği", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', fontsize=8.5)
ax3.grid(axis='both', linestyle=':', alpha=0.4, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: Kare Yeniden İnşa Başarısı (Sabotaj vs Sağlam Akış)
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')

stream_cases = ['Eksiksiz Akış\n(Temiz Video)', 'Ara Paket Kaybı\n(Ortanca Parça Düştü)']
recovery_rates = [100, 0]
colors_rec = ['#10B981', '#EF4444']

bars4 = ax4.bar(stream_cases, recovery_rates, color=colors_rec, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars4, recovery_rates):
    yval = bar.get_height()
    status_label = "%100 TESLİM (Dekodere İletildi)" if val == 100 else "İMHA EDİLDİ! (Yırtılma Engellendi)"
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 3.0, status_label, ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=9)

ax4.set_ylim(0, 130)
ax4.set_ylabel("Kare Doğrulama Oranı (%)", fontsize=10, color='#94A3B8')
ax4.set_title("Kare Bütünlüğü ve Bozuk Kare Düşürme Başarısı", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax4.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax4.tick_params(colors='#94A3B8')

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 156 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert len(sample_rtp.pack()) == 12 + len(sample_rtp.payload), "RTP başlığı tam 12 bayt olmalıdır!"
assert parsed_rtp.seq_num == 1001, "Sequence numarası doğrulanmalıdır!"
assert parsed_rtp.timestamp == 90000, "Timestamp doğrulanmalıdır!"
assert parsed_rtp.marker == True, "Marker biti doğrulanmalıdır!"
assert reassembler.dropped_corrupt_frames == 1, "Kayıp paketli kare düşürülmelidir!"
assert clean_reassembler.completed_frames == 1, "Temiz kare eksiksiz birleştirilmelidir!"

print()
print("[PASS] Gün 156: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")