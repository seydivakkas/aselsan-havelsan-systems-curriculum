# -*- coding: utf-8 -*-
"""
GÜN 154: Kod Bloğu 1 — Protobuf Tel Formatı (Wire Engine): Varint, ZigZag ve Tag Motoru
"""

import struct
from typing import Tuple, List, Dict, Any

class ProtobufWire:
    """
    Google Protocol Buffers tel formatı (Wire Format) kodlama ve çözme motoru.
    """
    WIRE_VARINT = 0
    WIRE_FIXED64 = 1
    WIRE_LENGTH_DELIMITED = 2
    WIRE_FIXED32 = 5

    # 1. Varint Kodlama ve Çözme
    @staticmethod
    def encode_varint(value: int) -> bytes:
        if value < 0:
            # 64-bit two's complement
            value = (1 << 64) + value
        out = bytearray()
        while value > 0x7F:
            out.append((value & 0x7F) | 0x80)
            value >>= 7
        out.append(value & 0x7F)
        return bytes(out)

    @staticmethod
    def decode_varint(data: bytes, offset: int = 0) -> Tuple[int, int]:
        res = 0
        shift = 0
        while offset < len(data):
            b = data[offset]
            offset += 1
            res |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        return res, offset

    # 2. ZigZag Kodlama (sint32 için)
    @staticmethod
    def encode_zigzag32(n: int) -> int:
        return (n << 1) ^ (n >> 31)

    @staticmethod
    def decode_zigzag32(n: int) -> int:
        return (n >> 1) ^ (-(n & 1))

    # 3. Tag (Key) Oluşturma ve Çözme
    @classmethod
    def make_tag(cls, field_number: int, wire_type: int) -> bytes:
        key = (field_number << 3) | (wire_type & 0x07)
        return cls.encode_varint(key)

    @classmethod
    def parse_tag(cls, data: bytes, offset: int = 0) -> Tuple[int, int, int]:
        key, new_offset = cls.decode_varint(data, offset)
        field_number = key >> 3
        wire_type = key & 0x07
        return field_number, wire_type, new_offset

print("[HÜCRE 7] Protobuf Tel Formatı Motoru Başarıyla Yüklendi.")

# Temel Varint ve ZigZag Doğrulamaları
v_test = 300
v_enc = ProtobufWire.encode_varint(v_test)
v_dec, _ = ProtobufWire.decode_varint(v_enc)

z_test = -42
z_enc = ProtobufWire.encode_zigzag32(z_test)
z_dec = ProtobufWire.decode_zigzag32(z_enc)

print(f"  [+] Sayı 300 Varint Baytları : {[hex(b) for b in v_enc]} ({len(v_enc)} Bayt)")
print(f"  [+] Varint Geri Çözme        : {v_dec} (Doğrulandı: {v_dec == v_test})")
print(f"  [+] Sayı -42 ZigZag Değeri   : {z_enc} (Pozitife eşlendi)")
print(f"  [+] ZigZag Geri Çözme        : {z_dec} (Doğrulandı: {z_dec == z_test})")

tag_id = ProtobufWire.make_tag(field_number=1, wire_type=ProtobufWire.WIRE_VARINT)
tag_az = ProtobufWire.make_tag(field_number=2, wire_type=ProtobufWire.WIRE_FIXED32)
print(f"  [+] Field 1 Varint Tag Hex  : 0x{tag_id.hex().upper()} (Beklenen: 0x08)")
print(f"  [+] Field 2 Fixed32 Tag Hex : 0x{tag_az.hex().upper()} (Beklenen: 0x15)")

# -*- coding: utf-8 -*-
"""
GÜN 154: Kod Bloğu 2 — Taktik Radar İzi Protobuf Mesaj Serileştirici ve Ayrıştırıcı
"""

class RadarTrackMessage:
    def __init__(self, track_id: int, azimuth: float, elevation: float, range_m: float, radial_vel: int, classification: str):
        self.track_id = track_id
        self.azimuth = azimuth
        self.elevation = elevation
        self.range_m = range_m
        self.radial_vel = radial_vel # Yaklaşma/Uzaklaşma hızı (m/s, negatif olabilir)
        self.classification = classification

    def serialize_to_wire(self) -> bytes:
        out = bytearray()
        
        # Field 1: track_id (uint32 -> Varint)
        if self.track_id != 0:
            out.extend(ProtobufWire.make_tag(1, ProtobufWire.WIRE_VARINT))
            out.extend(ProtobufWire.encode_varint(self.track_id))

        # Field 2: azimuth (float -> Fixed32)
        if self.azimuth != 0.0:
            out.extend(ProtobufWire.make_tag(2, ProtobufWire.WIRE_FIXED32))
            out.extend(struct.pack("<f", self.azimuth)) # Protobuf fixed types are Little-Endian

        # Field 3: elevation (float -> Fixed32)
        if self.elevation != 0.0:
            out.extend(ProtobufWire.make_tag(3, ProtobufWire.WIRE_FIXED32))
            out.extend(struct.pack("<f", self.elevation))

        # Field 4: range_m (float -> Fixed32)
        if self.range_m != 0.0:
            out.extend(ProtobufWire.make_tag(4, ProtobufWire.WIRE_FIXED32))
            out.extend(struct.pack("<f", self.range_m))

        # Field 5: radial_vel (sint32 -> ZigZag Varint)
        if self.radial_vel != 0:
            out.extend(ProtobufWire.make_tag(5, ProtobufWire.WIRE_VARINT))
            zz = ProtobufWire.encode_zigzag32(self.radial_vel)
            out.extend(ProtobufWire.encode_varint(zz))

        # Field 6: classification (string -> Length-delimited)
        if self.classification:
            str_bytes = self.classification.encode('utf-8')
            out.extend(ProtobufWire.make_tag(6, ProtobufWire.WIRE_LENGTH_DELIMITED))
            out.extend(ProtobufWire.encode_varint(len(str_bytes)))
            out.extend(str_bytes)

        return bytes(out)

    @classmethod
    def parse_from_wire(cls, wire_bytes: bytes) -> Tuple['RadarTrackMessage', Dict[int, Any]]:
        offset = 0
        track_id = 0
        azimuth = 0.0
        elevation = 0.0
        range_m = 0.0
        radial_vel = 0
        classification = ""
        unknown_fields = {}

        while offset < len(wire_bytes):
            field_num, wire_type, offset = ProtobufWire.parse_tag(wire_bytes, offset)
            
            if field_num == 1 and wire_type == ProtobufWire.WIRE_VARINT:
                track_id, offset = ProtobufWire.decode_varint(wire_bytes, offset)
            elif field_num == 2 and wire_type == ProtobufWire.WIRE_FIXED32:
                azimuth = struct.unpack("<f", wire_bytes[offset:offset+4])[0]
                offset += 4
            elif field_num == 3 and wire_type == ProtobufWire.WIRE_FIXED32:
                elevation = struct.unpack("<f", wire_bytes[offset:offset+4])[0]
                offset += 4
            elif field_num == 4 and wire_type == ProtobufWire.WIRE_FIXED32:
                range_m = struct.unpack("<f", wire_bytes[offset:offset+4])[0]
                offset += 4
            elif field_num == 5 and wire_type == ProtobufWire.WIRE_VARINT:
                zz, offset = ProtobufWire.decode_varint(wire_bytes, offset)
                radial_vel = ProtobufWire.decode_zigzag32(zz)
            elif field_num == 6 and wire_type == ProtobufWire.WIRE_LENGTH_DELIMITED:
                length, offset = ProtobufWire.decode_varint(wire_bytes, offset)
                classification = wire_bytes[offset:offset+length].decode('utf-8')
                offset += length
            else:
                # BİLİNMEYEN ALAN (FORWARD COMPATIBILITY / POSTEL ATLATMA)
                if wire_type == ProtobufWire.WIRE_VARINT:
                    val, offset = ProtobufWire.decode_varint(wire_bytes, offset)
                    unknown_fields[field_num] = val
                elif wire_type == ProtobufWire.WIRE_FIXED32:
                    unknown_fields[field_num] = wire_bytes[offset:offset+4]
                    offset += 4
                elif wire_type == ProtobufWire.WIRE_FIXED64:
                    unknown_fields[field_num] = wire_bytes[offset:offset+8]
                    offset += 8
                elif wire_type == ProtobufWire.WIRE_LENGTH_DELIMITED:
                    length, offset = ProtobufWire.decode_varint(wire_bytes, offset)
                    unknown_fields[field_num] = wire_bytes[offset:offset+length]
                    offset += length

        msg = cls(track_id, azimuth, elevation, range_m, radial_vel, classification)
        return msg, unknown_fields

# Test Radar İzi Oluştur
track_obj = RadarTrackMessage(
    track_id=1042,
    azimuth=88.5,
    elevation=12.3,
    range_m=45200.0,
    radial_vel=-350, # Bize doğru 350 m/s hızla yaklaşan düşman hedefi
    classification="SU-57"
)

wire_data = track_obj.serialize_to_wire()
parsed_track, unknowns = RadarTrackMessage.parse_from_wire(wire_data)

print()
print("[*] Protobuf RadarTrack Serileştirme Raporu:")
print(f"  [+] Teldeki Toplam Boyut  : {len(wire_data)} Bayt")
print(f"  [+] Teldeki Hex Akışı     : {wire_data.hex().upper()}")
print(f"  [+] Çözülen Hedef ID      : {parsed_track.track_id}")
print(f"  [+] Çözülen Azimut Açısı  : {parsed_track.azimuth:.1f}°")
print(f"  [+] Çözülen Radyal Hız    : {parsed_track.radial_vel} m/s (Negatif değer korundu)")
print(f"  [+] Çözülen Sınıflandırma : {parsed_track.classification}")

assert parsed_track.track_id == 1042
assert parsed_track.radial_vel == -350
assert parsed_track.classification == "SU-57"
assert len(unknowns) == 0
print("[HÜCRE 9] RadarTrack Protobuf tel formatı testi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 154: Kod Bloğu 3 — Sabotaj Deneyleri: Negatif int32 Şişmesi ve Bilinmeyen Alan
"""

print()
print("[*] Protobuf Sabotaj ve İleriye Uyumluluk Testleri Başlatılıyor...")

# -----------------------------------------------------------------------------
# SABOTAJ 1: int32 (-350) vs sint32 (-350) Tel Boyutu Karşılaştırması
# -----------------------------------------------------------------------------
neg_val = -350

# A) Hatalı Yaklaşım: Standart int32 Two's Complement Varint
raw_int32_varint = ProtobufWire.encode_varint(neg_val)

# B) Doğru Yaklaşım: sint32 ZigZag Varint
zz_val = ProtobufWire.encode_zigzag32(neg_val)
zigzag_varint = ProtobufWire.encode_varint(zz_val)

print(f"  [+] Sabotaj 1 Sonuçları (Negatif Sayı Tel Şişmesi):")
print(f"      - int32 (-350) Varint Boyutu : {len(raw_int32_varint)} Bayt (ŞİŞME! Tam 10 Bayt!)")
print(f"      - sint32 (-350) ZigZag Boyut : {len(zigzag_varint)} Bayt (MÜKEMMEL! 2 Bayt!)")
print(f"      - İsraf Oranı               : {len(raw_int32_varint) / len(zigzag_varint):.1f}x Daha Fazla Bayt!")

assert len(raw_int32_varint) == 10, "int32 negatif sayı 10 bayta genişlemelidir!"
assert len(zigzag_varint) == 2, "sint32 negatif sayı 2 bayt tutmalıdır!"

# -----------------------------------------------------------------------------
# SABOTAJ 2: Bilinmeyen Alan (Tag 9 / Fixed64) İle İleriye Uyumluluk Testi
# -----------------------------------------------------------------------------
# Yeni Nesil Radar, eski RadarTrack mesajının sonuna Tag 9 (Fixed64) Elektronik Harp verisi ekledi:
future_wire = bytearray(wire_data)
tag_future = ProtobufWire.make_tag(field_number=9, wire_type=ProtobufWire.WIRE_FIXED64)
future_data = struct.pack("<Q", 0xDEADBEEFCAFEBABE)

future_wire.extend(tag_future)
future_wire.extend(future_data)

# Eski alıcı bu geleceğin paketini çözebilecek mi?
parsed_legacy, legacy_unknowns = RadarTrackMessage.parse_from_wire(bytes(future_wire))

print()
print(f"  [+] Sabotaj 2 Sonuçları (Bilinmeyen Alan İle Karşılaşma):")
print(f"      - Eski Alıcı Çöktü mü?        : HAYIR (Güvenle Çalıştı)")
print(f"      - Bilinen Alanlar Okundu mu?  : EVET (Hedef: {parsed_legacy.classification})")
print(f"      - Bilinmeyen Tag 9 Yakalandı mı: {9 in legacy_unknowns} (Boyut: {len(legacy_unknowns[9])} Bayt)")

assert 9 in legacy_unknowns
assert legacy_unknowns[9] == future_data
print("[HÜCRE 11] Tüm Protobuf sabotaj deneyleri başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 154: Kod Bloğu 4 — Benchmark: JSON vs Protobuf vs Raw Struct Hız ve Boyut Ölçümü
"""

import time
import json

def run_protobuf_benchmark(iterations: int = 25_000) -> Dict[str, Any]:
    track = RadarTrackMessage(1042, 88.5, 12.3, 45200.0, -350, "SU-57")
    
    # Boyutlar
    proto_bytes = track.serialize_to_wire()
    json_bytes = json.dumps({
        "track_id": track.track_id, "azimuth": track.azimuth,
        "elevation": track.elevation, "range_m": track.range_m,
        "radial_vel": track.radial_vel, "classification": track.classification
    }).encode('utf-8')
    raw_struct_bytes = struct.pack(">I f f f i 8s", track.track_id, track.azimuth, track.elevation, track.range_m, track.radial_vel, track.classification.encode('utf-8'))

    # 1. JSON Süresi
    t0 = time.perf_counter()
    for _ in range(iterations):
        jb = json.dumps({
            "track_id": track.track_id, "azimuth": track.azimuth,
            "elevation": track.elevation, "range_m": track.range_m,
            "radial_vel": track.radial_vel, "classification": track.classification
        }).encode('utf-8')
        _ = json.loads(jb.decode('utf-8'))
    t_json = time.perf_counter() - t0

    # 2. Protobuf Süresi
    t0 = time.perf_counter()
    for _ in range(iterations):
        pb = track.serialize_to_wire()
        _, _ = RadarTrackMessage.parse_from_wire(pb)
    t_proto = time.perf_counter() - t0

    # 3. Raw Struct Süresi
    t0 = time.perf_counter()
    for _ in range(iterations):
        sb = struct.pack(">I f f f i 8s", track.track_id, track.azimuth, track.elevation, track.range_m, track.radial_vel, b"SU-57\x00\x00\x00")
        _ = struct.unpack(">I f f f i 8s", sb)
    t_struct = time.perf_counter() - t0

    return {
        "iterations": iterations,
        "size_json": len(json_bytes),
        "size_proto": len(proto_bytes),
        "size_struct": len(raw_struct_bytes),
        "t_json_ms": t_json * 1000.0,
        "t_proto_ms": t_proto * 1000.0,
        "t_struct_ms": t_struct * 1000.0,
        "json_ns": (t_json / iterations) * 1e9,
        "proto_ns": (t_proto / iterations) * 1e9,
        "struct_ns": (t_struct / iterations) * 1e9,
        "proto_vs_json_speedup": t_json / t_proto
    }

bench_res = run_protobuf_benchmark(iterations=25_000)

print()
print(f"[*] Format Kıyaslama Benchmarkı ({bench_res['iterations']:,} İşlem):")
print(f"  [+] Paket Boyutları     : JSON={bench_res['size_json']}B | Struct={bench_res['size_struct']}B | Protobuf={bench_res['size_proto']}B")
print(f"  [+] JSON Süresi         : {bench_res['t_json_ms']:.2f} ms ({bench_res['json_ns']:.1f} ns/op)")
print(f"  [+] Protobuf Süresi     : {bench_res['t_proto_ms']:.2f} ms ({bench_res['proto_ns']:.1f} ns/op)")
print(f"  [+] Raw Struct Süresi   : {bench_res['t_struct_ms']:.2f} ms ({bench_res['struct_ns']:.1f} ns/op)")
print(f"  [+] Protobuf Kazancı    : JSON'dan {bench_res['size_json'] / bench_res['size_proto']:.1f}x Daha Kompakt!")

assert bench_res['size_proto'] < bench_res['size_json']
print("[HÜCRE 13] Format karşılaştırma benchmarkı başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 154: Kod Bloğu 5 — Taktik Protobuf Dağıtıcı (Tactical Pub-Sub Broker)
"""

class TacticalProtobufBroker:
    """
    Protobuf ile serileştirilmiş radar izlerini abonelere dağıtan servis.
    """
    def __init__(self):
        self.published_messages = 0
        self.delivered_tracks = 0
        self.total_wire_bytes = 0

    def publish_radar_track(self, track_msg: RadarTrackMessage) -> bytes:
        wire_data = track_msg.serialize_to_wire()
        self.published_messages += 1
        self.total_wire_bytes += len(wire_data)
        return wire_data

    def deliver_to_subscriber(self, wire_data: bytes) -> RadarTrackMessage:
        parsed, _ = RadarTrackMessage.parse_from_wire(wire_data)
        self.delivered_tracks += 1
        return parsed

broker = TacticalProtobufBroker()

# 5 Hedeflik Radar Taramasını Yayınla ve Dağıt
fleet_tracks = [
    RadarTrackMessage(101, 45.0, 10.0, 15000.0, -280, "UAV"),
    RadarTrackMessage(102, 90.0, 15.0, 32000.0, -650, "MISSILE"),
    RadarTrackMessage(103, 135.0, 5.0, 48000.0, 120, "AIRLINER")
]

delivered_list = []
for t in fleet_tracks:
    w = broker.publish_radar_track(t)
    rcv = broker.deliver_to_subscriber(w)
    delivered_list.append(rcv)

print()
print("[*] Taktik Protobuf Dağıtıcı (Broker) Raporu:")
print(f"  [+] Yayınlanan Mesaj Sayısı : {broker.published_messages}")
print(f"  [+] Teslim Edilen İzler     : {broker.delivered_tracks}")
print(f"  [+] Toplam Taşınan Bayt     : {broker.total_wire_bytes} Bayt")
print(f"  [+] Tehdit Sınıfı           : {[t.classification for t in delivered_list]}")

assert broker.delivered_tracks == 3
assert delivered_list[1].classification == "MISSILE"
assert delivered_list[1].radial_vel == -650
print("[HÜCRE 15] Taktik Protobuf dağıtıcı testi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 154: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_154_protocol_buffers_zihinsel_modeli.png")

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: Protobuf Tel Formatı (Wire Format Anatomisi)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

wire_boxes = [
    {"name": "Tag 1 (0x08)\nField:1 | Type:0 (Varint)", "x": 0.05, "y": 0.60, "w": 0.22, "c": "#3B82F6"},
    {"name": "track_id (1042)\nVarint: 0x92 0x08", "x": 0.30, "y": 0.60, "w": 0.22, "c": "#10B981"},
    {"name": "Tag 2 (0x15)\nField:2 | Type:5 (Fixed32)", "x": 0.55, "y": 0.60, "w": 0.22, "c": "#3B82F6"},
    {"name": "azimuth (88.5°)\nFixed32: 4 Bayt Little-Endian", "x": 0.80, "y": 0.60, "w": 0.17, "c": "#F59E0B"},
    
    {"name": "Tag 5 (0x28)\nField:5 | Type:0 (Varint)", "x": 0.05, "y": 0.20, "w": 0.22, "c": "#3B82F6"},
    {"name": "radial_vel (-350)\nZigZag: 0xBB 0x05", "x": 0.30, "y": 0.20, "w": 0.22, "c": "#EC4899"},
    {"name": "Tag 6 (0x32)\nField:6 | Type:2 (Delimited)", "x": 0.55, "y": 0.20, "w": 0.22, "c": "#3B82F6"},
    {"name": "classification\nLen: 5 | Value: 'SU-57'", "x": 0.80, "y": 0.20, "w": 0.17, "c": "#8B5CF6"}
]

for b in wire_boxes:
    rect = plt.Rectangle((b["x"], b["y"]), b["w"], 0.26, facecolor=b["c"], alpha=0.35, edgecolor=b["c"], lw=2)
    ax1.add_patch(rect)
    ax1.text(b["x"] + b["w"]/2, b["y"] + 0.13, b["name"], ha='center', va='center', color='#F8FAFC', fontsize=8.5, fontweight='bold')

ax1.text(0.05, 0.92, "Protobuf Tel Akışı (Wire Format Byte Stream):", color='#38BDF8', fontsize=11, fontweight='bold')
ax1.set_title("Protobuf Tel Formatı (Tag + Value / Varint Anatomisi)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: Varint vs ZigZag Kodlama Bayt Boyutu
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

cases = ['Pozitif Sayı (42)\nVarint', 'Büyük Pozitif (1042)\nVarint', 'Negatif (-350)\nStandart int32 (ŞİŞME!)', 'Negatif (-350)\nsint32 ZigZag (OPTİMUM)']
byte_sizes = [1, 2, 10, 2]
colors_zz = ['#10B981', '#38BDF8', '#EF4444', '#10B981']

bars2 = ax2.bar(cases, byte_sizes, color=colors_zz, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars2, byte_sizes):
    yval = bar.get_height()
    status_txt = f"{val} Bayt"
    if val == 10:
        status_txt += "\n(Two's Complement Tuzağı)"
    elif val == 2 and "ZigZag" in bar.get_x().__str__():
        status_txt += "\n(%80 Kazanç)"
    ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.25, status_txt, ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=8.5)

ax2.set_ylim(0, 12.5)
ax2.set_ylabel("Teldeki Bayt Sayısı", fontsize=10, color='#94A3B8')
ax2.set_title("Varint ve ZigZag Kodlama Verimliliği (int32 vs sint32)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax2.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Şema Evrimi ve Bilinmeyen Alan Atlatma
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

compat_scenarios = ['V1 Alıcı <- V1 Mesaj\n(Temel Paket)', 'V1 Alıcı <- V2 Mesaj\n(Ekstra Tag 9 / Fixed64)', 'Kırıcı Değişiklik\n(Field No Çakışması)']
surv_scores = [100, 100, 0]
colors_compat = ['#10B981', '#38BDF8', '#EF4444']

bars3 = ax3.bar(compat_scenarios, surv_scores, color=colors_compat, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars3, surv_scores):
    yval = bar.get_height()
    lbl = "KUSURSUZ AYRIŞTIRMA" if val == 100 and "V1 Alıcı <- V1" in bar.get_x().__str__() else ("GÜVENLE ATLANDI (UnknownField)" if val == 100 else "BOZULMA / ÇÖKME")
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 2.5, f"%{val} Başarı\n{lbl}", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=8.5)

ax3.set_ylim(0, 130)
ax3.set_ylabel("Ayrıştırma Başarısı (%)", fontsize=10, color='#94A3B8')
ax3.set_title("Şema Evrimi ve Bilinmeyen Alanları (Unknown Fields) Koruma", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: Tel Boyutu Karşılaştırması
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')

proto_formats = ['JSON (Metin)', 'Raw Struct (C++)', 'Protobuf (Binary)']
proto_sizes = [bench_res['size_json'], bench_res['size_struct'], bench_res['size_proto']]
colors_proto = ['#EF4444', '#F59E0B', '#10B981']

bars4 = ax4.bar(proto_formats, proto_sizes, color=colors_proto, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars4, proto_sizes):
    yval = bar.get_height()
    ratio = val / bench_res['size_proto']
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f"{val} Bayt\n({ratio:.1f}x)", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=9.5)

ax4.set_ylim(0, max(proto_sizes) * 1.3)
ax4.set_ylabel("Paket Boyutu (Bayt)", fontsize=10, color='#94A3B8')
ax4.set_title("Tel Boyutu Karşılaştırması (Wire Size)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
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
print("[*] GÜN 154 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert len(raw_int32_varint) == 10, "int32 negatif sayı 10 bayta genişlemelidir!"
assert len(zigzag_varint) == 2, "sint32 negatif sayı 2 bayt tutmalıdır!"
assert 9 in legacy_unknowns, "Bilinmeyen Tag 9 güvenle yakalanmalıdır!"
assert bench_res['size_proto'] < bench_res['size_json'], "Protobuf JSON'dan daha küçük olmalıdır!"

print()
print("[PASS] Gün 154: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")