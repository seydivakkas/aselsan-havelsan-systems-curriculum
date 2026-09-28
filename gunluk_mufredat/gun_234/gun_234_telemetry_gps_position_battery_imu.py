# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 234: Telemetry Mesajları Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: MAVLink Telemetri Mesaj Yapıları Serileştirme & Deserialization
# GLOBAL_POSITION_INT, GPS_RAW_INT, BATTERY_STATUS ve HIGHRES_IMU ikili modelleri.
# ============================================================================
from dataclasses import dataclass
import struct
from typing import List, Tuple

# 1. GLOBAL_POSITION_INT (#33) - 28 Bayt
@dataclass
class GlobalPositionIntPayload:
    time_boot_ms: int   # uint32
    lat: int            # int32 (degE7)
    lon: int            # int32 (degE7)
    alt: int            # int32 (mm MSL)
    relative_alt: int   # int32 (mm AGL)
    vx: int             # int16 (cm/s NED north)
    vy: int             # int16 (cm/s NED east)
    vz: int             # int16 (cm/s NED down)
    hdg: int            # uint16 (cdeg 0..35999)

    def serialize(self) -> bytes:
        # Format: < (little-endian), I (4), i (4), i (4), i (4), i (4), h (2), h (2), h (2), H (2) = 28 bayt
        return struct.pack("<IiiiihhhH", self.time_boot_ms, self.lat, self.lon, 
                           self.alt, self.relative_alt, self.vx, self.vy, self.vz, self.hdg)

    @classmethod
    def deserialize(cls, data: bytes) -> "GlobalPositionIntPayload":
        vals = struct.unpack("<IiiiihhhH", data)
        return cls(*vals)

# 2. BATTERY_STATUS (#147) - 36 Bayt
@dataclass
class BatteryStatusPayload:
    current_consumed_mah: int # int32
    energy_consumed_hj: int   # int32
    temperature_cdeg: int     # int16 (0.01 C)
    voltages_mv: List[int]    # 10 adet uint16 (hücre gerilimleri)
    current_battery_ca: int   # int16 (10 mA)
    battery_id: int           # uint8
    battery_function: int     # uint8
    battery_type: int         # uint8
    battery_remaining: int    # int8 (%)

    def serialize(self) -> bytes:
        # Format: < (little-endian), i (4), i (4), h (2), 10H (20), h (2), B (1), B (1), B (1), b (1) = 36 bayt
        v = self.voltages_mv + [0] * (10 - len(self.voltages_mv))
        return struct.pack("<iih10HhBBBb", self.current_consumed_mah, self.energy_consumed_hj,
                           self.temperature_cdeg, *v, self.current_battery_ca,
                           self.battery_id, self.battery_function, self.battery_type, self.battery_remaining)

    @classmethod
    def deserialize(cls, data: bytes) -> "BatteryStatusPayload":
        unpacked = struct.unpack("<iih10HhBBBb", data)
        c_mah, e_hj, temp = unpacked[0], unpacked[1], unpacked[2]
        volts = list(unpacked[3:13])
        c_ca, b_id, b_func, b_type, b_rem = unpacked[13], unpacked[14], unpacked[15], unpacked[16], unpacked[17]
        return cls(c_mah, e_hj, temp, volts, c_ca, b_id, b_func, b_type, b_rem)

# 3. HIGHRES_IMU (#105) - 62 Bayt
@dataclass
class HighresImuPayload:
    time_usec: int      # uint64
    xacc: float         # float (m/s^2)
    yacc: float         # float
    zacc: float         # float
    xgyro: float        # float (rad/s)
    ygyro: float        # float
    zgyro: float        # float
    xmag: float         # float (gauss)
    ymag: float         # float
    zmag: float         # float
    abs_pressure: float # float (mbar)
    diff_pressure: float# float (mbar)
    pressure_alt: float # float (m)
    temperature: float  # float (deg C)
    fields_updated: int # uint16
    imu_id: int         # uint8

    def serialize(self) -> bytes:
        # Format: <Q (8) + 13f (52) + H (2) = 62 bayt
        return struct.pack("<Q13fH", self.time_usec, self.xacc, self.yacc, self.zacc,
                           self.xgyro, self.ygyro, self.zgyro, self.xmag, self.ymag, self.zmag,
                           self.abs_pressure, self.diff_pressure, self.pressure_alt, self.temperature,
                           self.fields_updated)

    @classmethod
    def deserialize(cls, data: bytes) -> "HighresImuPayload":
        unpacked = struct.unpack("<Q13fH", data)
        return cls(unpacked[0], *unpacked[1:14], unpacked[14], 0)

# Doğrulama Testleri
# 1. Konum Testi: Ankara TUSAŞ Semaları (Enlem: 39.9250180, Boylam: 32.8369560, İrtifa: 950m MSL, 150m AGL)
pos = GlobalPositionIntPayload(
    time_boot_ms=125400,
    lat=int(39.9250180 * 1e7),
    lon=int(32.8369560 * 1e7),
    alt=950000,
    relative_alt=150000,
    vx=2500, # 25 m/s Kuzey
    vy=0,
    vz=-100, # 1 m/s Tırmanış (-Z)
    hdg=18000 # 180 derece (Güney)
)
raw_pos = pos.serialize()
assert len(raw_pos) == 28, f"Hatalı Konum boyutu: {len(raw_pos)}"
dec_pos = GlobalPositionIntPayload.deserialize(raw_pos)
assert dec_pos.lat == pos.lat
assert dec_pos.relative_alt == 150000

# 2. Batarya Testi: 6S LiPo Batarya (22.2V nominal, %85 kalan kapasite)
batt = BatteryStatusPayload(
    current_consumed_mah=4500,
    energy_consumed_hj=36000,
    temperature_cdeg=2850, # 28.5 C
    voltages_mv=[3850, 3845, 3852, 3848, 3850, 3846, 0, 0, 0, 0],
    current_battery_ca=1850, # 18.5 A
    battery_id=0,
    battery_function=1,
    battery_type=2,
    battery_remaining=85
)
raw_batt = batt.serialize()
assert len(raw_batt) == 36, f"Hatalı Batarya boyutu: {len(raw_batt)}"
dec_batt = BatteryStatusPayload.deserialize(raw_batt)
assert dec_batt.battery_remaining == 85
assert dec_batt.voltages_mv[0] == 3850

print("[PASS] Kod 1: MAVLink Telemetri İkili (Binary) Çerçeveleri Başarıyla Doğrulandı.")
print(f"  - GLOBAL_POSITION_INT : {len(raw_pos)} bayt (Lat: {dec_pos.lat/1e7:.6f}, RelAlt: {dec_pos.relative_alt/1000.0}m)")
print(f"  - BATTERY_STATUS      : {len(raw_batt)} bayt (Kalan: %{dec_batt.battery_remaining}, Akım: {dec_batt.current_battery_ca/100.0}A)")

# ============================================================================
# KOD HÜCRESİ 2: Çok Kanallı Telemetri Akış Zamanlayıcısı (Stream Scheduler)
# Periyodik mesaj tetikleme, bant genişliği bütçelemesi ve zamanlama simülasyonu.
# ============================================================================
from typing import Dict, List, NamedTuple

class StreamDefinition(NamedTuple):
    name: str
    msg_id: int
    payload_size: int
    target_hz: float

class TelemetryStreamScheduler:
    def __init__(self):
        self.streams: Dict[int, StreamDefinition] = {}
        self.last_run_time: Dict[int, float] = {}
        self.packet_counts: Dict[int, int] = {}
        self.total_bytes_sent = 0

    def register_stream(self, stream: StreamDefinition):
        self.streams[stream.msg_id] = stream
        self.last_run_time[stream.msg_id] = -1.0
        self.packet_counts[stream.msg_id] = 0

    def update(self, current_time: float) -> List[Tuple[str, int]]:
        ready_packets = []
        for msg_id, stream in self.streams.items():
            interval = 1.0 / stream.target_hz
            last_t = self.last_run_time[msg_id]

            if last_t < 0 or (current_time - last_t) >= (interval - 1e-6):
                self.last_run_time[msg_id] = current_time
                self.packet_counts[msg_id] += 1
                pkt_total_size = stream.payload_size + 12 # MAVLink v2 header + CRC
                self.total_bytes_sent += pkt_total_size
                ready_packets.append((stream.name, pkt_total_size))

        return ready_packets

# Zamanlayıcı Yapılandırması
scheduler = TelemetryStreamScheduler()
scheduler.register_stream(StreamDefinition("HIGHRES_IMU", 105, 62, target_hz=20.0))
scheduler.register_stream(StreamDefinition("GLOBAL_POSITION_INT", 33, 28, target_hz=10.0))
scheduler.register_stream(StreamDefinition("GPS_RAW_INT", 24, 30, target_hz=5.0))
scheduler.register_stream(StreamDefinition("BATTERY_STATUS", 147, 36, target_hz=1.0))
scheduler.register_stream(StreamDefinition("HEARTBEAT", 0, 9, target_hz=1.0))

# 10 Saniyelik Uçuş Simülasyonu (0.005s = 5ms adımlarla 200 Hz ana döngü)
dt = 0.005
sim_duration = 10.0
steps = int(sim_duration / dt)

for s in range(steps):
    t = s * dt
    scheduler.update(t)

# Doğrulamalar: 10 saniyede beklenen paket adetleri
assert scheduler.packet_counts[105] == 200, f"IMU paket sayısı hatalı: {scheduler.packet_counts[105]} (200 bekleniyor)"
assert scheduler.packet_counts[33] == 100, f"Konum paket sayısı hatalı: {scheduler.packet_counts[33]} (100 bekleniyor)"
assert scheduler.packet_counts[24] == 50, f"GPS paket sayısı hatalı: {scheduler.packet_counts[24]} (50 bekleniyor)"
assert scheduler.packet_counts[147] == 10, f"Batarya paket sayısı hatalı: {scheduler.packet_counts[147]} (10 bekleniyor)"
assert scheduler.packet_counts[0] == 10, f"Heartbeat paket sayısı hatalı: {scheduler.packet_counts[0]} (10 bekleniyor)"

avg_bandwidth_bps = (scheduler.total_bytes_sent / sim_duration)
print("[PASS] Kod 2: Çok Kanallı Telemetri Akış Zamanlayıcısı Doğrulandı.")
print(f"  - Üretilen IMU Paketi (20 Hz)   : {scheduler.packet_counts[105]} adet")
print(f"  - Üretilen Konum Paketi (10 Hz) : {scheduler.packet_counts[33]} adet")
print(f"  - Üretilen GPS Paketi (5 Hz)    : {scheduler.packet_counts[24]} adet")
print(f"  - Üretilen Pil Paketi (1 Hz)    : {scheduler.packet_counts[147]} adet")
print(f"  - Toplam İletilen Veri          : {scheduler.total_bytes_sent:,} bayt")
print(f"  - Ortalama Veri Hızı            : {avg_bandwidth_bps:.1f} Bayt/s (115200 baud hattın %{avg_bandwidth_bps/115.2:.1f}'i)")

# ============================================================================
# KOD HÜCRESİ 3: Aviyonik Telemetri Sağlık ve Kritik Güvenlik İzleme Motoru
# Batarya hücre dengesizliği, GPS fix bozulması ve IMU aşırı titreşim alarmları.
# ============================================================================
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TelemetryHealthStatus:
    is_gps_valid: bool
    is_battery_safe: bool
    is_imu_healthy: bool
    active_alarms: List[str]

class AvionicsTelemetryMonitor:
    def __init__(self):
        self.min_cell_voltage_mv = 3300 # 3.3V kritik sınır
        self.max_cell_delta_mv = 300     # 300mV hücreler arası fark sınırı
        self.min_satellites = 6
        self.max_vibration_acc = 30.0    # 30 m/s^2 (~3g) titreşim sınırı

    def evaluate_health(self, pos: GlobalPositionIntPayload, batt: BatteryStatusPayload, imu: HighresImuPayload) -> TelemetryHealthStatus:
        alarms = []
        gps_valid = True
        battery_safe = True
        imu_healthy = True

        # 1. Batarya Hücre Denetimi
        active_cells = [v for v in batt.voltages_mv if v > 0]
        if active_cells:
            min_v = min(active_cells)
            max_v = max(active_cells)
            if min_v < self.min_cell_voltage_mv:
                battery_safe = False
                alarms.append(f"ALARM_BATTERY_LOW_CELL ({min_v} mV < {self.min_cell_voltage_mv} mV)")
            if (max_v - min_v) > self.max_cell_delta_mv:
                battery_safe = False
                alarms.append(f"ALARM_BATTERY_CELL_IMBALANCE (Delta: {max_v - min_v} mV)")

        # 2. İrtifa ve Konum Denetimi
        if pos.relative_alt < -5000: # -5 metre altı (Yer altına girme anomalisi)
            gps_valid = False
            alarms.append("ALARM_NEGATIVE_RELATIVE_ALTITUDE_ANOMALY")

        # 3. IMU Titreşim ve Doyum Denetimi
        acc_magnitude = (imu.xacc**2 + imu.yacc**2 + imu.zacc**2)**0.5
        if acc_magnitude > self.max_vibration_acc:
            imu_healthy = False
            alarms.append(f"ALARM_HIGH_IMU_VIBRATION ({acc_magnitude:.1f} m/s^2 > {self.max_vibration_acc} m/s^2)")

        return TelemetryHealthStatus(
            is_gps_valid=gps_valid,
            is_battery_safe=battery_safe,
            is_imu_healthy=imu_healthy,
            active_alarms=alarms
        )

# Normal Uçuş Durumu Doğrulaması
monitor = AvionicsTelemetryMonitor()
normal_status = monitor.evaluate_health(pos, batt, HighresImuPayload(
    time_usec=1000000, xacc=0.1, yacc=0.2, zacc=-9.81,
    xgyro=0.01, ygyro=0.01, zgyro=0.0, xmag=0.2, ymag=0.1, zmag=0.4,
    abs_pressure=1013.25, diff_pressure=12.5, pressure_alt=950.0, temperature=25.0,
    fields_updated=0xFFFF, imu_id=0
))

assert normal_status.is_gps_valid == True
assert normal_status.is_battery_safe == True
assert normal_status.is_imu_healthy == True
assert len(normal_status.active_alarms) == 0

print("[PASS] Kod 3: Aviyonik Telemetri Sağlık İzleme Motoru Doğrulandı.")
print("  - Normal Durum Değerlendirmesi: TÜM ALT SİSTEMLER SAĞLIKLI [OK]")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik Aviyonik Telemetri Hata Enjeksiyon Testi
# Hücre gerilim çökmesi, GNSS irtifa tutarsızlığı ve IMU rezonans doyumu.
# ============================================================================

# --- HATA TESTİ 1: Kritik Batarya Hücre Çökmesi ---
print("[TEST 1] Batarya Tek Hücre Çökmesi (Low Cell Voltage Anomaly)...")
faulty_batt = BatteryStatusPayload(
    current_consumed_mah=5200, energy_consumed_hj=41000, temperature_cdeg=3200,
    voltages_mv=[3820, 3815, 3822, 3150, 3818, 3820, 0, 0, 0, 0], # 4. hücre 3150 mV!
    current_battery_ca=2200, battery_id=0, battery_function=1, battery_type=2, battery_remaining=42
)
res_batt = monitor.evaluate_health(pos, faulty_batt, HighresImuPayload(
    time_usec=1000000, xacc=0, yacc=0, zacc=-9.81, xgyro=0, ygyro=0, zgyro=0,
    xmag=0, ymag=0, zmag=0, abs_pressure=1013, diff_pressure=10, pressure_alt=950,
    temperature=25, fields_updated=0xFFFF, imu_id=0
))
assert res_batt.is_battery_safe == False, "Düşük hücre gerilimi yakalanamadı!"
assert any("ALARM_BATTERY_LOW_CELL" in a for a in res_batt.active_alarms)
print(f"  - 4. Hücre Gerilimi : {faulty_batt.voltages_mv[3]} mV (Eşik: 3300 mV)")
print(f"  - Üretilen Alarm    : {res_batt.active_alarms[0]}")
print("  [PASS] Test 1: Batarya hücre çökmesi başarıyla tespit edildi.\n")

# --- HATA TESTİ 2: GNSS İrtifa Sahtekarlığı / Bozulması ---
print("[TEST 2] GNSS Bağıl İrtifa Tutarsızlığı (Spoofing / Baro Uyuşmazlığı)...")
faulty_pos = GlobalPositionIntPayload(
    time_boot_ms=130000, lat=pos.lat, lon=pos.lon, alt=800000,
    relative_alt=-15000, # -15 metre (Yerin altı!)
    vx=2000, vy=0, vz=0, hdg=18000
)
res_gps = monitor.evaluate_health(faulty_pos, batt, HighresImuPayload(
    time_usec=1000000, xacc=0, yacc=0, zacc=-9.81, xgyro=0, ygyro=0, zgyro=0,
    xmag=0, ymag=0, zmag=0, abs_pressure=1013, diff_pressure=10, pressure_alt=950,
    temperature=25, fields_updated=0xFFFF, imu_id=0
))
assert res_gps.is_gps_valid == False, "Yerin altına inen irtifa anomalisi yakalanamadı!"
assert any("ALARM_NEGATIVE_RELATIVE_ALTITUDE" in a for a in res_gps.active_alarms)
print(f"  - Hatalı Bağıl İrtifa: {faulty_pos.relative_alt/1000.0} m")
print(f"  - Üretilen Alarm     : {res_gps.active_alarms[0]}")
print("  [PASS] Test 2: GNSS irtifa tutarsızlığı başarıyla yakalandı.\n")

# --- HATA TESTİ 3: Aşırı IMU Rezonans Titreşimi ---
print("[TEST 3] Motor Titreşimi ve IMU Doyumu (Resonance Clipping)...")
faulty_imu = HighresImuPayload(
    time_usec=1000000, xacc=5.0, yacc=8.0, zacc=35.0, # sqrt(25 + 64 + 1225) = ~36.3 m/s^2
    xgyro=0.1, ygyro=0.1, zgyro=0.2, xmag=0, ymag=0, zmag=0,
    abs_pressure=1013, diff_pressure=10, pressure_alt=950, temperature=25,
    fields_updated=0xFFFF, imu_id=0
)
res_imu = monitor.evaluate_health(pos, batt, faulty_imu)
assert res_imu.is_imu_healthy == False, "Aşırı IMU titreşimi yakalanamadı!"
assert any("ALARM_HIGH_IMU_VIBRATION" in a for a in res_imu.active_alarms)
print(f"  - Toplam İvme Bileşkesi: {(faulty_imu.xacc**2 + faulty_imu.yacc**2 + faulty_imu.zacc**2)**0.5:.2f} m/s^2")
print(f"  - Üretilen Alarm        : {res_imu.active_alarms[0]}")
print("  [PASS] Test 3: IMU titreşim anomalisi başarıyla engellendi.\n")

print("[PASS] Kod 4: 3 Kritik Aviyonik Telemetri Hata Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 100.000 Telemetri Paketi Ayrıştırma ve Doğrulama Benchmark'ı
# Nanosaniye düzeyinde serileştirme/deserialization verimi ve p99 kuyruk analizi.
# ============================================================================
import time
import numpy as np

NUM_PACKETS = 100_000
latencies_us = np.empty(NUM_PACKETS, dtype=np.float64)

# Önceden serileştirilmiş ikili test paketleri
raw_pos_packet = pos.serialize()
raw_batt_packet = batt.serialize()

print(f"[BENCHMARK] {NUM_PACKETS:,} Telemetri Paketi Ayrıştırılıyor (Deserialization)...")
t_start = time.perf_counter()

for i in range(NUM_PACKETS):
    t0 = time.perf_counter_ns()
    
    # 50-50 Konum ve Batarya Paketi Ayrıştırma
    if i % 2 == 0:
        p = GlobalPositionIntPayload.deserialize(raw_pos_packet)
    else:
        b = BatteryStatusPayload.deserialize(raw_batt_packet)
        
    t_end = time.perf_counter_ns()
    latencies_us[i] = (t_end - t0) / 1000.0 # ns -> us

t_total = time.perf_counter() - t_start

throughput_pkts = NUM_PACKETS / t_total
avg_lat = np.mean(latencies_us)
p50 = np.percentile(latencies_us, 50)
p90 = np.percentile(latencies_us, 90)
p99 = np.percentile(latencies_us, 99)

print(f"\n[TELEMETRİ AYRIŞTIRMA BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - Ayrıştırma Hızı     : {throughput_pkts:,.1f} paket/s (Hedef: > 200,000)")
print(f"  - Ortalama Gecikme    : {avg_lat:.2f} µs")
print(f"  - p50 (Medyan)        : {p50:.2f} µs")
print(f"  - p90 Gecikme         : {p90:.2f} µs")
print(f"  - p99 Kuyruk Gecikmesi: {p99:.2f} µs (Hedef: < 15.0 µs)")

# Doğrulamalar
assert throughput_pkts > 200_000, f"Ayrıştırma hızı yetersiz: {throughput_pkts}"
assert p99 < 15.0, f"p99 gecikmesi çok yüksek: {p99} µs"

print("\n[PASS] Kod 5: 100.000 Telemetri Paketi Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli 300 DPI Koyu Tema Aviyonik Telemetri Dashboard'u
# gun_234_telemetry_gps_position_battery_imu.png dosyasını üretir.
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
import os

# Koyu Tema Savunma Standart Renkleri
COLOR_BG = "#0F172A"       # Slate 900
COLOR_PANEL = "#1E293B"    # Slate 800
COLOR_TEXT = "#F8FAFC"     # Slate 50
COLOR_MUTED = "#94A3B8"    # Slate 400
COLOR_ACCENT1 = "#38BDF8"  # Cyan (Konum ve İrtifa)
COLOR_ACCENT2 = "#34D399"  # Yeşil (Normal Batarya)
COLOR_ACCENT3 = "#F87171"  # Kırmızı (Çöken Hücre / Titreşim Alarmı)
COLOR_ACCENT4 = "#FBBF24"  # Sarı (IMU Dinamiği)

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: Taktik Uçuş Yörüngesi ve Bağıl İrtifa Profili ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

t_pts = np.linspace(0, 100, 200)
alt_m = 150.0 + 25.0 * np.sin(t_pts * 0.08) # 150m +/- 25m dalgalanma
vel_ms = 22.0 + 3.0 * np.cos(t_pts * 0.08)

ax1.plot(t_pts, alt_m, color=COLOR_ACCENT1, linewidth=2.5, label="Bağıl İrtifa (relative_alt) [m]")
ax1.set_title("Panel 1: Taktik Uçuş Seyrüsefer ve İrtifa Profili (GLOBAL_POSITION_INT)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xlabel("Uçuş Süresi [s]", color=COLOR_MUTED, fontsize=10)
ax1.set_ylabel("İrtifa [m AGL]", color=COLOR_ACCENT1, fontsize=10)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6)

# İkinci Y-Ekseni (Hız)
ax1_twin = ax1.twinx()
ax1_twin.plot(t_pts, vel_ms, color=COLOR_ACCENT4, linestyle="--", linewidth=1.8, label="Yer Hızı (Groundspeed) [m/s]")
ax1_twin.set_ylabel("Hız [m/s]", color=COLOR_ACCENT4, fontsize=10)
ax1_twin.tick_params(colors=COLOR_MUTED)

# Birleşik Lejant
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax1_twin.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 2: 6S Batarya Hücre Gerilimleri ve Çöken Hücre Tespiti ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

cells_idx = [f"Hücre {i}" for i in range(1, 7)]
healthy_voltages = [3.85, 3.84, 3.85, 3.85, 3.84, 3.85]
faulty_voltages = [3.82, 3.81, 3.82, 3.15, 3.82, 3.81] # 4. hücre kritik

x = np.arange(len(cells_idx))
width = 0.35

rects1 = ax2.bar(x - width/2, healthy_voltages, width, label='Normal Durum', color=COLOR_ACCENT2, edgecolor="#334155")
rects2 = ax2.bar(x + width/2, faulty_voltages, width, label='Hücre Çökmesi (Arıza)', color=[COLOR_ACCENT2, COLOR_ACCENT2, COLOR_ACCENT2, COLOR_ACCENT3, COLOR_ACCENT2, COLOR_ACCENT2], edgecolor="#334155")

ax2.axhline(3.30, color=COLOR_ACCENT3, linestyle=":", linewidth=2.0, label="Kritik Hücre Sınırı (3.30 V)")
ax2.set_title("Panel 2: LiPo Batarya 6S Hücre Gerilim Analizi ve Anomali (BATTERY_STATUS)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_ylabel("Hücre Gerilimi [V]", color=COLOR_MUTED, fontsize=10)
ax2.set_xticks(x)
ax2.set_xticklabels(cells_idx)
ax2.set_ylim(2.8, 4.2)
ax2.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")
ax2.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="lower right", fontsize=8)

for bar in rects2:
    h = bar.get_height()
    if h < 3.3:
        ax2.text(bar.get_x() + bar.get_width()/2., h + 0.05, f"ARIZA!\n{h:.2f}V", ha='center', va='bottom', color=COLOR_ACCENT3, fontsize=8, fontweight="bold")

# --- PANEL 3: 3 Eksen IMU İvmeölçer Dinamiği ve Titreşim Doyumu ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

t_imu = np.linspace(0, 10, 300)
# Normal uçuş + 6. saniyede pervane hasarı kaynaklı titreşim patlaması
vib_burst = np.where(t_imu > 6.0, 12.0 * np.sin(t_imu * 45.0), 1.0 * np.sin(t_imu * 10.0))
acc_z = -9.81 + vib_burst

ax3.plot(t_imu, acc_z, color=COLOR_ACCENT4, linewidth=1.5, label="Z-Eksen İvme (zacc) [m/s²]")
ax3.axhline(-9.81, color=COLOR_MUTED, linestyle="--", label="1g Yerçekimi Referansı (-9.81 m/s²)")
ax3.axhspan(-25.0, -9.81, color=COLOR_ACCENT3, alpha=0.15, label="Kritik Titreşim / Doyum Eşiği (> 20 m/s²)")

ax3.set_title("Panel 3: Yüksek Çözünürlüklü IMU Dinamiği ve Rezonans Titreşimi (HIGHRES_IMU)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("Zaman [s]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("İvme [m/s²]", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="lower left", fontsize=8)

# --- PANEL 4: 100.000 Paket Ayrıştırma Gecikme Dağılımı ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

n, bins, patches = ax4.hist(latencies_us, bins=50, color=COLOR_ACCENT1, alpha=0.75, edgecolor="#0284C7")
ax4.axvline(p50, color=COLOR_ACCENT2, linestyle="-", linewidth=2.2, label=f"p50 (Medyan): {p50:.2f} µs")
ax4.axvline(p90, color=COLOR_ACCENT4, linestyle="--", linewidth=2.2, label=f"p90: {p90:.2f} µs")
ax4.axvline(p99, color=COLOR_ACCENT3, linestyle="-.", linewidth=2.2, label=f"p99: {p99:.2f} µs")

ax4.set_title("Panel 4: 100.000 Telemetri Paketi Ayrıştırma Gecikmesi (µs)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_xlabel("Ayrıştırma Süresi [µs]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylabel("Paket Sayısı", color=COLOR_MUTED, fontsize=10)
ax4.tick_params(colors=COLOR_MUTED)
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax4.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# Üst Başlık
plt.suptitle("BAYRAKTAR TB2 / ANKA — MAVLINK TELEMETRİ VE AVİYONİK SAĞLIK DASHBOARD'U", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_234/gun_234_telemetry_gps_position_battery_imu.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

