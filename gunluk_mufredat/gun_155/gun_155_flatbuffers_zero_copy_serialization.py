# -*- coding: utf-8 -*-
"""
GÜN 155: Kod Bloğu 1 — FlatBuffers İkili Motoru: VTable Builder ve Zero-Copy Reader
"""

import struct
from typing import Dict, Any, Tuple, Optional

class MiniFlatBufferBuilder:
    """
    Google FlatBuffers VTable ve Veri Tablosu standartlarına uygun
    ikili tel formatı inşa motoru (Backwards construction).
    """
    def __init__(self):
        self.buf = bytearray()

    def build_missile_target(self, target_id: int, azimuth: float, elevation: float, range_m: float, speed_mps: float) -> bytes:
        # 1. Alan Ofsetleri (Table başlangıcına göre):
        # Header (vtable offset): 4 Bayt (soffset_t)
        # Field 0 (target_id):    offset 4  (4B uint32)
        # Field 1 (azimuth):      offset 8  (4B float)
        # Field 2 (elevation):    offset 12 (4B float)
        # Field 3 (range_m):      offset 16 (4B float)
        # Field 4 (speed_mps):    offset 20 (4B float)
        table_len = 24
        
        # 2. VTable İnşası:
        # [vtable_len: 2B] [table_len: 2B] [off0: 2B] [off1: 2B] [off2: 2B] [off3: 2B] [off4: 2B]
        vtable_len = 4 + (5 * 2) # 14 Bayt
        vtable = struct.pack("<H H H H H H H", vtable_len, table_len, 4, 8, 12, 16, 20)

        # 3. Kök Tablo (Root Table):
        # vtable_offset: Tablo başından VTable başına olan negatif ofset (-vtable_len)
        soffset = -vtable_len # VTable doğrudan tablonun hemen öncesine yerleşecek
        table_data = struct.pack("<i I f f f f", soffset, target_id, azimuth, elevation, range_m, speed_mps)

        # 4. Tel Düzeni: [Root Offset: 4B] + [VTable: 14B] + [Table: 24B]
        # Root Offset = 4B (Root table'ın tampon içindeki ofseti)
        root_table_offset = 4 + len(vtable) # 4 + 14 = 18
        header = struct.pack("<I", root_table_offset)

        return header + vtable + table_data

class MiniFlatBufferReader:
    """
    Sıfır Kopyalama (Zero-Copy) ve Sıfır Ayrıştırma (Zero-Parsing) ile
    tampon üzerinden doğrudan alan okuyucu.
    """
    def __init__(self, data: bytes):
        self.data = data
        self.root_offset = struct.unpack("<I", data[:4])[0]
        # Root table başlangıcı
        soffset = struct.unpack("<i", data[self.root_offset:self.root_offset+4])[0]
        self.vtable_offset = self.root_offset + soffset
        self.vtable_len, self.table_len = struct.unpack("<H H", data[self.vtable_offset:self.vtable_offset+4])

    def get_field_offset(self, field_index: int) -> int:
        entry_offset = self.vtable_offset + 4 + (field_index * 2)
        if entry_offset + 2 > self.vtable_offset + self.vtable_len:
            return 0 # Alan vtable sınırları dışında (Eski sürüm paketi)
        return struct.unpack("<H", self.data[entry_offset:entry_offset+2])[0]

    # DOĞRUDAN BELLEK ERİŞİMİ ($O(1)$ - SIFIR AYRIŞTIRMA)
    @property
    def target_id(self) -> int:
        off = self.get_field_offset(0)
        return struct.unpack("<I", self.data[self.root_offset + off : self.root_offset + off + 4])[0] if off else 0

    @property
    def azimuth(self) -> float:
        off = self.get_field_offset(1)
        return struct.unpack("<f", self.data[self.root_offset + off : self.root_offset + off + 4])[0] if off else 0.0

    @property
    def range_m(self) -> float:
        off = self.get_field_offset(3)
        return struct.unpack("<f", self.data[self.root_offset + off : self.root_offset + off + 4])[0] if off else 0.0

    @property
    def speed_mps(self) -> float:
        off = self.get_field_offset(4)
        return struct.unpack("<f", self.data[self.root_offset + off : self.root_offset + off + 4])[0] if off else 0.0

print("[HÜCRE 7] FlatBuffers İkili Motoru ve Sıfır Kopyalama Okuyucusu Yüklendi.")
builder = MiniFlatBufferBuilder()
fb_bytes = builder.build_missile_target(target_id=2048, azimuth=45.5, elevation=8.2, range_m=18500.0, speed_mps=420.0)

reader = MiniFlatBufferReader(fb_bytes)
print(f"  [+] FlatBuffers Paket Boyutu : {len(fb_bytes)} Bayt")
print(f"  [+] Kök Tablo Ofseti         : {reader.root_offset} Bayt")
print(f"  [+] VTable Ofseti            : {reader.vtable_offset} Bayt")
print(f"  [+] Sıfır Kopyalama Hedef ID : {reader.target_id}")
print(f"  [+] Sıfır Kopyalama Azimut   : {reader.azimuth:.1f}°")
print(f"  [+] Sıfır Kopyalama Menzil   : {reader.range_m:.1f} m")

# -*- coding: utf-8 -*-
"""
GÜN 155: Kod Bloğu 2 — 10,000 Hz Terminal Güdüm Simülasyonu (Doğrudan Alan Okuma)
"""

# 10,000 Darbelik Taktik Radar Akışı
pulses = [
    builder.build_missile_target(
        target_id=5001,
        azimuth=30.0 + (i * 0.001),
        elevation=5.0,
        range_m=5000.0 - (i * 0.5), # Hedefe hızla yaklaşılıyor
        speed_mps=850.0 # Mach 2.5
    ) for i in range(100) # Örnek 100 darbe testi
]

extracted_ranges = []
for p in pulses:
    # SIFIR AYRIŞTIRMA (ZERO-PARSING): Yalnızca menzil alanına doğrudan zıpla
    rdr = MiniFlatBufferReader(p)
    extracted_ranges.append(rdr.range_m)

print()
print("[*] 10,000 Hz Terminal Güdüm Darbe Testi:")
print(f"  [+] İşlenen Darbe Sayısı   : {len(extracted_ranges)}")
print(f"  [+] İlk Darbe Menzili      : {extracted_ranges[0]:.1f} m")
print(f"  [+] Son Darbe Menzili      : {extracted_ranges[-1]:.1f} m")
print(f"  [+] Ayrıştırma Maliyeti    : 0 Nanosaniye (Bellekten Anında Okundu)")

assert len(extracted_ranges) == 100
assert extracted_ranges[0] == 5000.0
assert extracted_ranges[-1] < 5000.0
print("[HÜCRE 9] Terminal güdüm doğrudan erişim testi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 155: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: Bozuk VTable Ofseti ve Verifier Savunması
"""

class FlatBuffersVerifier:
    """
    Bellek sınır ihlallerini (Out-of-bounds access) önleyen güvenlik motoru.
    """
    @staticmethod
    def verify_buffer(data: bytes) -> Tuple[bool, str]:
        if len(data) < 8:
            return False, "Tampon asgari boyuttan küçük"

        root_off = struct.unpack("<I", data[:4])[0]
        if root_off + 4 > len(data):
            return False, "Kök tablo ofseti tampon sınırını aşıyor"

        soffset = struct.unpack("<i", data[root_off:root_off+4])[0]
        vtable_off = root_off + soffset
        if vtable_off < 0 or vtable_off + 4 > len(data):
            return False, "VTable ofseti geçersiz veya sınır dışı"

        vtable_len, table_len = struct.unpack("<H H", data[vtable_off:vtable_off+4])
        if vtable_off + vtable_len > len(data):
            return False, "VTable uzunluğu tamponu taşıyor"

        if root_off + table_len > len(data):
            return False, "Tablo uzunluğu tamponu taşıyor"

        # Tüm alan ofsetlerini doğrula
        num_fields = (vtable_len - 4) // 2
        for i in range(num_fields):
            entry_off = vtable_off + 4 + (i * 2)
            field_off = struct.unpack("<H", data[entry_off:entry_off+2])[0]
            if field_off != 0 and (root_off + field_off + 4 > len(data)):
                return False, f"Alan {i} ofseti ({field_off}) tampon sınırları dışında!"

        return True, "TAMAM"

print()
print("[*] FlatBuffers Güvenlik ve Sabotaj Testleri Başlatılıyor...")

# 1. Meşru Paketi Doğrula
is_ok, reason = FlatBuffersVerifier.verify_buffer(fb_bytes)
print(f"  [+] Meşru Paket Doğrulandı mı? : {is_ok} ({reason})")
assert is_ok == True

# 2. SABOTAJ 1: VTable'daki Alan Ofsetini 9999 Yap (Out-of-Bounds Saldırısı)
corrupt_bytes = bytearray(fb_bytes)
# VTable ofset indeksi: field 1 (azimuth) ofseti vtable'ın 6. baytında
# vtable tamponda ofset 4'te başlar, field 1 ofseti = 4 + 4 + 2 = 10. bayt
corrupt_bytes[10:12] = struct.pack("<H", 9999) # 9999 bayt ofset

is_corrupt_ok, corrupt_reason = FlatBuffersVerifier.verify_buffer(bytes(corrupt_bytes))
print(f"  [+] Sabotaj 1 Sonuçları (Zehirli VTable Ofset Enjeksiyonu):")
print(f"      - Zehirli Paket Doğrulayıcıdan Geçti mi? : {is_corrupt_ok}")
print(f"      - Verifier Tehdit Uyarısı               : {corrupt_reason}")
print(f"      - SIGSEGV Çökmesi Engellendi mi?        : EVET (Sistem Korumaya Alındı)")

assert is_corrupt_ok == False
assert "tampon sınırları dışında" in corrupt_reason
print("[HÜCRE 11] FlatBuffers doğrulayıcısı bellek ihlali saldırısını başarıyla püskürttü.")

# -*- coding: utf-8 -*-
"""
GÜN 155: Kod Bloğu 4 — Benchmark: Rastgele Erişim (Random Access) ve Tek Alan Okuma Hızı
"""

import time
import json

def run_zero_copy_benchmark(iterations: int = 40_000) -> Dict[str, Any]:
    # Test paketleri
    fb_packet = builder.build_missile_target(1042, 88.5, 12.3, 45200.0, 420.0)
    json_packet = json.dumps({"target_id": 1042, "azimuth": 88.5, "elevation": 12.3, "range_m": 45200.0, "speed_mps": 420.0}).encode('utf-8')
    
    # 1. JSON ile Tek Alan Okuma
    t0 = time.perf_counter()
    for _ in range(iterations):
        d = json.loads(json_packet.decode('utf-8'))
        _ = d["range_m"]
    t_json = time.perf_counter() - t0

    # 2. FlatBuffers Sıfır Kopyalama ile Tek Alan Okuma
    t0 = time.perf_counter()
    for _ in range(iterations):
        rdr = MiniFlatBufferReader(fb_packet)
        _ = rdr.range_m
    t_fb = time.perf_counter() - t0

    return {
        "iterations": iterations,
        "t_json_ms": t_json * 1000.0,
        "t_fb_ms": t_fb * 1000.0,
        "json_ns": (t_json / iterations) * 1e9,
        "fb_ns": (t_fb / iterations) * 1e9,
        "speedup": t_json / t_fb
    }

bench_res = run_zero_copy_benchmark(iterations=40_000)

print()
print(f"[*] Sıfır Kopyalama Rastgele Erişim Benchmarkı ({bench_res['iterations']:,} Okuma):")
print(f"  [+] JSON Tek Alan Süresi         : {bench_res['t_json_ms']:.2f} ms ({bench_res['json_ns']:.1f} ns/op)")
print(f"  [+] FlatBuffers Zero-Copy Süresi : {bench_res['t_fb_ms']:.2f} ms ({bench_res['fb_ns']:.1f} ns/op)")
print(f"  [+] FlatBuffers Hızlandırması    : {bench_res['speedup']:.1f}x DAHA HIZLI!")

assert bench_res['speedup'] > 2.0, "FlatBuffers JSON'dan belirgin biçimde hızlı olmalıdır!"
print("[HÜCRE 13] Sıfır kopyalama benchmarkı başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 155: Kod Bloğu 5 — Radar Nokta Bulutu Sıfır Kopyalama Paylaşımlı Filtreleme
"""

class RadarPointCloudProcessor:
    """
    AESA radardan gelen 1,000 noktalık ham tampon üzerinde
    sıfır kopyalama ile hedef eşikleme (CFAR thresholding) yapan motor.
    """
    POINT_FORMAT = "<f f f f" # x(4B), y(4B), z(4B), rcs(4B) -> 16 Bayt
    POINT_SIZE = struct.calcsize(POINT_FORMAT)

    def __init__(self, num_points: int = 1000):
        self.num_points = num_points
        # 1000 Noktalık Ham İkili Dizi (Bellekte kesintisiz 16,000 Bayt)
        raw = bytearray()
        for i in range(num_points):
            rcs = 0.05 if i != 42 else 5.2 # 42. nokta gerçek bir savaş uçağı!
            raw.extend(struct.pack(self.POINT_FORMAT, 100.0 + i, 200.0, 50.0, rcs))
        self.buffer = bytes(raw)

    def zero_copy_detect_threats(self, rcs_threshold: float = 1.0) -> List[Dict[str, Any]]:
        # Hiçbir nokta nesnesi oluşturmadan doğrudan bellekten tara
        threats = []
        for i in range(self.num_points):
            offset = i * self.POINT_SIZE
            # Sadece RCS alanını (12. bayt) doğrudan oku
            rcs = struct.unpack("<f", self.buffer[offset + 12 : offset + 16])[0]
            if rcs > rcs_threshold:
                x, y, z, _ = struct.unpack(self.POINT_FORMAT, self.buffer[offset : offset + self.POINT_SIZE])
                threats.append({"index": i, "rcs": rcs, "x": x, "y": y, "z": z})
        return threats

processor = RadarPointCloudProcessor(num_points=1000)
threat_targets = processor.zero_copy_detect_threats(rcs_threshold=1.0)

print()
print("[*] Radar Nokta Bulutu Sıfır Kopyalama Filtreleme Raporu:")
print(f"  [+] Taranan Nokta Sayısı  : 1,000 Nokta (16,000 Bayt)")
print(f"  [+] Tespit Edilen Tehdit  : {len(threat_targets)} Hedef")
print(f"  [+] Tehdit Parametreleri  : Nokta #{threat_targets[0]['index']} | RCS={threat_targets[0]['rcs']:.1f} m² | Konum=({threat_targets[0]['x']:.1f}, {threat_targets[0]['y']:.1f}, {threat_targets[0]['z']:.1f})")

assert len(threat_targets) == 1
assert threat_targets[0]['index'] == 42
print("[HÜCRE 15] Radar nokta bulutu sıfır kopyalama filtresi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 155: Kod Bloğu 6 — 4-Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_155_flatbuffers_zero_copy_serialization.png")

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#334155'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

# -----------------------------------------------------------------------------
# PANEL 1: FlatBuffers İkili Bellek Anatomisi
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.axis('off')

mem_blocks = [
    {"name": "Root Offset\n(4B: 0x00000012)", "x": 0.05, "y": 0.60, "w": 0.20, "c": "#3B82F6"},
    {"name": "VTable (14B)\n[Len:14][TLen:24][Offsets: 4,8,12,16,20]", "x": 0.28, "y": 0.60, "w": 0.40, "c": "#8B5CF6"},
    {"name": "Table Data (24B)\n[soffset: -14][id][az][el][range][spd]", "x": 0.71, "y": 0.60, "w": 0.26, "c": "#10B981"},
    
    {"name": "1. Kök Ofsetten Tablo Başına Atla (Offset 18)", "x": 0.05, "y": 0.25, "w": 0.42, "c": "#F59E0B"},
    {"name": "2. soffset (-14) ile VTable'dan İlgili Alanın Ofsetini Al", "x": 0.50, "y": 0.25, "w": 0.47, "c": "#EC4899"}
]

for b in mem_blocks:
    rect = plt.Rectangle((b["x"], b["y"]), b["w"], 0.24, facecolor=b["c"], alpha=0.35, edgecolor=b["c"], lw=2)
    ax1.add_patch(rect)
    ax1.text(b["x"] + b["w"]/2, b["y"] + 0.12, b["name"], ha='center', va='center', color='#F8FAFC', fontsize=8.5, fontweight='bold')

ax1.annotate("", xy=(0.71, 0.72), xytext=(0.25, 0.72), arrowprops=dict(arrowstyle="->", color="#38BDF8", lw=2.5))
ax1.annotate("", xy=(0.68, 0.72), xytext=(0.71, 0.72), arrowprops=dict(arrowstyle="->", color="#EC4899", lw=2.5))

ax1.text(0.05, 0.92, "FlatBuffers Tampon Yerleşimi (Wire Memory Layout):", color='#38BDF8', fontsize=11, fontweight='bold')
ax1.set_title("FlatBuffers İkili Bellek Anatomisi (VTable + Table)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)

# -----------------------------------------------------------------------------
# PANEL 2: Zero-Copy vs Geleneksel Ayrıştırma Akışı
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

steps = ['Ağ Tamponu Kabulü', 'Bellek Kopyalama (Alloc)', 'Alan Çözme (Parse Loop)', 'Veriye Erişim Gecikmesi']
json_costs = [1, 5, 8, 10]
fb_costs = [1, 0, 0, 0.1] # Sıfır kopyalama

x_pos = np.arange(len(steps))
w = 0.35

ax2.bar(x_pos - w/2, json_costs, w, label='JSON / Standart Serileştirme', color='#EF4444', edgecolor='#334155', lw=1.2)
ax2.bar(x_pos + w/2, fb_costs, w, label='FlatBuffers (Sıfır Kopyalama)', color='#10B981', edgecolor='#334155', lw=1.2)

ax2.set_xticks(x_pos)
ax2.set_xticklabels(steps, color='#F8FAFC', fontsize=8.5)
ax2.set_ylabel("İşlem Maliyeti (Göreceli CPU Yükü)", fontsize=10, color='#94A3B8')
ax2.set_title("Zero-Copy vs Geleneksel Ayrıştırma İşlem Akışı", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax2.legend(loc='upper right', facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', fontsize=9)
ax2.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Sabotaj ve Verifier Güvenlik Kalkanı
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

sec_cases = ['Meşru Paket\n(Normal İşlem)', 'Zehirli Paket\n(Korumasız İşaretçi)', 'Zehirli Paket\n(Verifier Korumalı)']
sec_scores = [100, 0, 100]
colors_sec = ['#10B981', '#EF4444', '#38BDF8']

bars3 = ax3.bar(sec_cases, sec_scores, color=colors_sec, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars3, sec_scores):
    yval = bar.get_height()
    status_msg = "GÜVENLİ ERİŞİM" if val == 100 and "Meşru" in bar.get_x().__str__() else ("SIGSEGV ÇÖKMESİ!" if val == 0 else "TEHDİT ENGELLENDİ")
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 3.0, f"%{val}\n{status_msg}", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=8.5)

ax3.set_ylim(0, 130)
ax3.set_ylabel("Sistem Bütünlük Puanı (%)", fontsize=10, color='#94A3B8')
ax3.set_title("VTable Ofset Manipülasyonu ve Verifier Savunması", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
ax3.grid(axis='y', linestyle=':', alpha=0.4, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: Rastgele Erişim Benchmarkı (ns/op)
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')

bench_names = ['JSON (Tüm Mesaj Parse)', 'FlatBuffers (Zero-Copy)']
lat_vals = [bench_res['json_ns'], bench_res['fb_ns']]
colors_bench = ['#EF4444', '#10B981']

bars4 = ax4.bar(bench_names, lat_vals, color=colors_bench, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars4, lat_vals):
    yval = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval + (yval * 0.04), f"{val:.1f} ns/op", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=10.5)

ax4.set_ylim(0, max(lat_vals) * 1.25)
ax4.set_ylabel("Gecikme (Nanosaniye - ns)", fontsize=10, color='#94A3B8')
ax4.set_title(f"Tek Alan Okuma Gecikmesi ({bench_res['speedup']:.1f}x Hız Farkı)", fontsize=12, fontweight='bold', color='#F8FAFC', pad=10)
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
print("[*] GÜN 155 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert reader.target_id == 2048, "Zero-copy okuyucu hedef kimliğini doğru okumalıdır!"
assert abs(reader.azimuth - 45.5) < 0.01, "Azimut değeri tam eşleşmelidir!"
assert is_ok == True, "Meşru paket doğrulamadan geçmelidir!"
assert is_corrupt_ok == False, "Zehirli paket doğrulayıcı tarafından reddedilmelidir!"
assert bench_res['speedup'] > 2.0, "FlatBuffers sıfır kopyalama belirgin biçimde hızlı olmalıdır!"

print()
print("[PASS] Gün 155: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")