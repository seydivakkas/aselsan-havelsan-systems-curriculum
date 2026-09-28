# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 243: ULog ve Uçuş Günlüğü Analizi Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: ULog İkili Format Kodlayıcı ve Ayrıştırıcı Kütüphanesi
# Dosya başlığı, format tanımı, abonelik ve ikili veri paketleme doğrulaması.
# ============================================================================
import struct
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

# ULog Sabitleri
ULOG_MAGIC = b"\x55\x4c\x6f\x67\x01\x12\x35"
ULOG_VERSION = 1
MSG_TYPE_FORMAT = ord("F")
MSG_TYPE_SUBSCRIBE = ord("A")
MSG_TYPE_DATA = ord("D")
MSG_TYPE_DROPOUT = ord("O")
MSG_TYPE_LOG = ord("L")

@dataclass
class AttitudeSample:
    timestamp_us: int
    roll_deg: float
    pitch_deg: float
    yaw_deg: float

class ULogCodec:
    # 16 Bayt Dosya Başlığı: 7B magic + 1B version + 8B timestamp_us
    FILE_HDR_FMT = "<7sBQ"
    # 3 Bayt Paket Başlığı: 2B msg_size + 1B msg_type
    MSG_HDR_FMT = "<HB"

    @classmethod
    def create_file_header(cls, start_time_us: int) -> bytes:
        return struct.pack(cls.FILE_HDR_FMT, ULOG_MAGIC, ULOG_VERSION, start_time_us)

    @classmethod
    def verify_file_header(cls, raw: bytes) -> Tuple[bool, int]:
        if len(raw) < 16:
            return False, 0
        magic, ver, t_start = struct.unpack_from(cls.FILE_HDR_FMT, raw, 0)
        is_valid = (magic == ULOG_MAGIC) and (ver == ULOG_VERSION)
        return is_valid, t_start

    @classmethod
    def encode_format_msg(cls, format_str: str) -> bytes:
        payload = format_str.encode("utf-8")
        hdr = struct.pack(cls.MSG_HDR_FMT, len(payload), MSG_TYPE_FORMAT)
        return hdr + payload

    @classmethod
    def encode_subscribe_msg(cls, msg_id: int, topic_name: str) -> bytes:
        name_bytes = topic_name.encode("utf-8")
        payload = struct.pack("<H", msg_id) + name_bytes
        hdr = struct.pack(cls.MSG_HDR_FMT, len(payload), MSG_TYPE_SUBSCRIBE)
        return hdr + payload

    @classmethod
    def encode_attitude_data(cls, msg_id: int, sample: AttitudeSample) -> bytes:
        # Payload: msg_id (uint16) + timestamp (uint64) + 3x float32 (roll, pitch, yaw)
        payload = struct.pack("<HQfff", msg_id, sample.timestamp_us, sample.roll_deg, sample.pitch_deg, sample.yaw_deg)
        hdr = struct.pack(cls.MSG_HDR_FMT, len(payload), MSG_TYPE_DATA)
        return hdr + payload

    @classmethod
    def decode_stream(cls, buffer: bytes) -> List[AttitudeSample]:
        samples = []
        offset = 16 # Dosya başlığını atla
        total_len = len(buffer)
        
        while offset + 3 <= total_len:
            msg_size, msg_type = struct.unpack_from(cls.MSG_HDR_FMT, buffer, offset)
            offset += 3
            payload = buffer[offset : offset + msg_size]
            offset += msg_size
            
            if msg_type == MSG_TYPE_DATA:
                msg_id, t_us, r, p, y = struct.unpack("<HQfff", payload)
                samples.append(AttitudeSample(timestamp_us=t_us, roll_deg=r, pitch_deg=p, yaw_deg=y))
                
        return samples

# Test: ULog İkili Akışı Oluşturma ve Doğrulama
t_boot = 1727095000000000
raw_ulog = bytearray()

# 1. Başlık Ekle
raw_ulog.extend(ULogCodec.create_file_header(t_boot))
is_ok, dec_t = ULogCodec.verify_file_header(raw_ulog[:16])
assert is_ok and dec_t == t_boot

# 2. Format ve Abone Mesajı Ekle
raw_ulog.extend(ULogCodec.encode_format_msg("vehicle_attitude:uint64_t timestamp;float roll;float pitch;float yaw;"))
raw_ulog.extend(ULogCodec.encode_subscribe_msg(msg_id=1, topic_name="vehicle_attitude"))

# 3. 3 Adet Örnek Veri Yaz
s1 = AttitudeSample(timestamp_us=t_boot + 10000, roll_deg=2.5, pitch_deg=-1.2, yaw_deg=45.0)
s2 = AttitudeSample(timestamp_us=t_boot + 20000, roll_deg=5.1, pitch_deg=-0.8, yaw_deg=46.5)
s3 = AttitudeSample(timestamp_us=t_boot + 30000, roll_deg=1.2, pitch_deg=0.5, yaw_deg=48.0)

raw_ulog.extend(ULogCodec.encode_attitude_data(msg_id=1, sample=s1))
raw_ulog.extend(ULogCodec.encode_attitude_data(msg_id=1, sample=s2))
raw_ulog.extend(ULogCodec.encode_attitude_data(msg_id=1, sample=s3))

# 4. Geri Çöz ve Doğrula
recovered = ULogCodec.decode_stream(raw_ulog)
assert len(recovered) == 3
assert abs(recovered[0].roll_deg - 2.5) < 1e-4
assert abs(recovered[1].pitch_deg - (-0.8)) < 1e-4
assert abs(recovered[2].yaw_deg - 48.0) < 1e-4

print("[PASS] Kod 1: ULog İkili Format Kodlayıcı ve Ayrıştırıcı Doğrulandı.")
print(f"  - Üretilen ULog Dosya Boyutu : {len(raw_ulog)} bayt (Başlık, Format, Abone ve 3 Veri Paketi)")
print(f"  - Çözülen Örnek 1            : t=+10ms, Roll={recovered[0].roll_deg:.1f}°, Pitch={recovered[0].pitch_deg:.1f}°, Yaw={recovered[0].yaw_deg:.1f}°")
print(f"  - Çözülen Örnek 3            : t=+30ms, Roll={recovered[2].roll_deg:.1f}°, Pitch={recovered[2].pitch_deg:.1f}°, Yaw={recovered[2].yaw_deg:.1f}°")

# ============================================================================
# KOD HÜCRESİ 2: Kontrolcü Tutum Takip Hatası ve RMSE Metrik Motoru
# Setpoint vs Actual karşılaştırması, RMSE, tepe hatası ve kabul kriteri.
# ============================================================================
import numpy as np

class AttitudeTrackingAnalyzer:
    @staticmethod
    def calculate_tracking_metrics(sp_series: np.ndarray, actual_series: np.ndarray) -> Dict[str, float]:
        assert len(sp_series) == len(actual_series), "Dizi uzunlukları eşit olmalıdır"
        error = actual_series - sp_series
        
        rmse = float(np.sqrt(np.mean(error ** 2)))
        mean_err = float(np.mean(error))
        max_err = float(np.max(np.abs(error)))
        std_err = float(np.std(error))
        
        return {
            "rmse_deg": rmse,
            "mean_error_deg": mean_err,
            "max_error_deg": max_err,
            "std_error_deg": std_err
        }

# Simülasyon: 10 saniyelik basamak ve sinüsoidal Roll manevrası (100 Hz = 1000 örnek)
t_flight = np.linspace(0, 10.0, 1000)
# Pilot komutu (Setpoint): 15 derecelik yatış ve sinüs dönüşü
roll_sp = 15.0 * np.sin(2 * np.pi * 0.3 * t_flight)

# Gerçek Uçak Tepkisi: 60 ms faz gecikmesi ve hafif aşma (damping ratio zeta=0.7)
# Gecikme simülasyonu: 6 örnek kaydırma (6 * 10ms = 60ms)
delay_samples = 6
roll_actual = np.zeros_like(roll_sp)
roll_actual[delay_samples:] = roll_sp[:-delay_samples] * 0.98 + np.random.normal(0, 0.2, 1000 - delay_samples)
roll_actual[:delay_samples] = roll_sp[:delay_samples]

metrics = AttitudeTrackingAnalyzer.calculate_tracking_metrics(roll_sp, roll_actual)

# Havacılık Doğrulamaları:
# İHA normal manevrada RMSE <= 1.5 derece olmalıdır
assert metrics["rmse_deg"] < 1.5, f"RMSE çok yüksek: {metrics['rmse_deg']:.2f}°"
assert metrics["max_error_deg"] < 3.5, f"Tepe hatası çok yüksek: {metrics['max_error_deg']:.2f}°"

print("[PASS] Kod 2: Kontrolcü Tutum Takip Hatası ve RMSE Analiz Motoru Doğrulandı.")
print(f"  - Kök Ortalama Karekök Hatası (RMSE) : {metrics['rmse_deg']:.3f}° (Kabul Kriteri: < 1.5°)")
print(f"  - Azami Tepe Hatası (Max Error)     : {metrics['max_error_deg']:.3f}° (Kabul Kriteri: < 3.5°)")
print(f"  - Ortalama Sapma (Mean Bias)         : {metrics['mean_error_deg']:.3f}°")
print(f"  - Hata Standart Sapması              : {metrics['std_error_deg']:.3f}° [MÜKEMMEL]")

# ============================================================================
# KOD HÜCRESİ 3: İvmeölçer Titreşim Analizi ve FFT Spektral Tepe Tespiti
# Hanning pencereleme, Güç Spektral Yoğunluğu (PSD) ve motor RPM frekansı tespiti.
# ============================================================================
class ImuVibrationSpectralAnalyzer:
    @staticmethod
    def compute_psd(signal: np.ndarray, fs: float) -> Tuple[np.ndarray, np.ndarray, float]:
        n = len(signal)
        # Hanning Penceresi ile spektral sızıntıyı (spectral leakage) önle
        window = np.hanning(n)
        windowed_sig = (signal - np.mean(signal)) * window
        
        # FFT Hesaplama
        fft_vals = np.fft.rfft(windowed_sig)
        freqs = np.fft.rfftfreq(n, d=1.0/fs)
        
        # PSD (Tek taraflı)
        psd = (np.abs(fft_vals) ** 2) / (n * fs)
        psd[1:-1] *= 2.0 # Enerji koruma faktörü
        
        rms_val = float(np.sqrt(np.mean((signal - np.mean(signal)) ** 2)))
        return freqs, psd, rms_val

# Simülasyon: 200 Hz örnekleme ile 4 saniyelik İvmeölçer Z ekseni verisi (800 örnek)
fs_imu = 200.0
n_samples = 800
t_vib = np.arange(n_samples) / fs_imu

# Sinyal Bileşenleri:
# 1. 1g Yerçekimi (9.81 m/s^2)
# 2. 75 Hz Motor Titreşimi (4500 RPM / 60 = 75 Hz), Genlik: 1.2 m/s^2
# 3. 25 Hz Gövde Rezonansı, Genlik: 0.5 m/s^2
# 4. Beyaz Gürültü
vib_signal = (
    9.81 +
    1.2 * np.sin(2 * np.pi * 75.0 * t_vib) +
    0.5 * np.sin(2 * np.pi * 25.0 * t_vib) +
    np.random.normal(0, 0.3, n_samples)
)

freqs, psd, rms_vib = ImuVibrationSpectralAnalyzer.compute_psd(vib_signal, fs_imu)

# En yüksek tepe frekansını bul (0 Hz DC bileşeni hariç)
peak_idx = np.argmax(psd[freqs > 5.0]) + np.sum(freqs <= 5.0)
peak_freq = freqs[peak_idx]

# Doğrulamalar:
# Tepe frekansı 75 Hz civarında olmalıdır (+- 2 Hz tolerans)
assert abs(peak_freq - 75.0) < 2.0, f"Beklenen 75 Hz, bulunan: {peak_freq:.1f} Hz"
# RMS titreşimi askeri sınır olan 3.0 m/s^2 altında kalmalıdır
assert rms_vib < 3.0, f"Titreşim çok yüksek: {rms_vib:.2f} m/s^2"

print("[PASS] Kod 3: İvmeölçer FFT Spektral Analizi ve Tepe Tespiti Doğrulandı.")
print(f"  - Örnekleme Frekansı       : {fs_imu:.0f} Hz (Nyquist Sınırı: {fs_imu/2:.0f} Hz)")
print(f"  - Tespit Edilen Tepe Frekans: {peak_freq:.1f} Hz (4500 RPM Motor Harmonisi [DOĞRULANDI])")
print(f"  - Titreşim RMS Değeri      : {rms_vib:.3f} m/s² (Askeri Eşik: < 3.0 m/s² [GÜVENLİ])")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik Uçuş Günlüğü Adli Teşhis Testi
# SD kart dropout tespiti, motor PWM doygunluğu ve zaman damgası jitter teşhisi.
# ============================================================================

# --- TEST 1: SD Kart Darboğazı ve Dropout Tespiti ---
print("[TEST 1] SD Kart Darboğazı ve Dropout ('O') Mesajı Tespiti...")
class ULogDropoutDetector:
    @staticmethod
    def parse_dropouts(log_events: List[Dict[str, Any]]) -> Tuple[int, int, float]:
        total_drops = 0
        total_lost_ms = 0
        for ev in log_events:
            if ev.get("type") == "DROPOUT":
                total_drops += 1
                total_lost_ms += ev.get("duration_ms", 0)
        loss_pct = (total_lost_ms / 60000.0) * 100.0 # 60 saniyelik uçuş varsayımı
        return total_drops, total_lost_ms, loss_pct

events = [
    {"type": "DATA", "time": 1000},
    {"type": "DROPOUT", "duration_ms": 150}, # 150 ms tampon taşması
    {"type": "DATA", "time": 1150},
    {"type": "DROPOUT", "duration_ms": 80},  # 80 ms tampon taşması
]

drops, lost_ms, pct = ULogDropoutDetector.parse_dropouts(events)
assert drops == 2, "Dropout adedi hatalı"
assert lost_ms == 230, "Kayıp süre toplamı hatalı"
print(f"  - Tespit Edilen Dropout Sayısı : {drops} adet")
print(f"  - Toplam Kaybedilen Süre       : {lost_ms} ms (Yavaş SD Kart Teşhisi)")
print("  [PASS] Test 1: ULog Dropout tespiti başarıyla doğrulandı.\n")

# --- TEST 2: Aktüatör Doygunluğu (PWM Clipping) Teşhisi ---
print("[TEST 2] Aktüatör Doygunluğu (Actuator Saturation Clipping) Teşhisi...")
def detect_actuator_clipping(motor_outputs: np.ndarray) -> Tuple[bool, float]:
    # motor_outputs: 0.0 ile 1.0 arasında normalize PWM
    clipped_samples = np.sum(motor_outputs >= 0.99)
    clip_ratio = clipped_samples / len(motor_outputs)
    is_saturated = clip_ratio > 0.05 # %5'ten fazla tavanda kalırsa tehlike
    return is_saturated, clip_ratio

# Senaryo: Rüzgara karşı zorlanan motor %8 süreyle 1.0 (doygunluk) seviyesinde kalıyor
pwm_stream = np.random.uniform(0.5, 0.9, 1000)
pwm_stream[:80] = 1.0 # 80 örnek doygunluk (%8)

is_sat, ratio = detect_actuator_clipping(pwm_stream)
assert is_sat == True, "Doygunluk tespit edilemedi!"
assert abs(ratio - 0.08) < 1e-3
print(f"  - Motor Doygunluk Oranı : %{ratio*100:.1f} (Tavan: 1.0 PWM)")
print("  - Teşhis Kararı          : AKTÜATÖR DOYGUNLUĞU ALARMI (Kontrol Yetersizliği Riski)")
print("  [PASS] Test 2: Aktüatör doygunluk teşhisi başarıyla doğrulandı.\n")

# --- TEST 3: Zaman Damgası Jitter Dalgalanması Teşhisi ---
print("[TEST 3] Sensör Zaman Damgası Dalgalanması (Timestamp Jitter) Teşhisi...")
def analyze_timestamp_jitter(timestamps_us: np.ndarray, nominal_dt_us: float) -> Tuple[bool, float]:
    dts = np.diff(timestamps_us)
    max_dt = np.max(dts)
    # Nominal sürenin 2 katından büyük aralık varsa jitter hatası ver
    has_jitter = max_dt > (2.0 * nominal_dt_us)
    return has_jitter, float(max_dt)

# Nominal 10 ms (10,000 us) döngüde bir kesinti sonucu 25,000 us gecikme oluşur
ts = np.arange(0, 100000, 10000) # 10 adet 10ms örnek
ts[5:] += 15000 # 5. örnekte 25ms sıçrama

has_j, peak_gap = analyze_timestamp_jitter(ts, nominal_dt_us=10000)
assert has_j == True, "Jitter atlaması tespit edilemedi!"
assert peak_gap == 25000.0
print(f"  - Nominal Örnekleme Aralığı : 10,000 µs (10 ms)")
print(f"  - Tespit Edilen Azami Boşluk: {peak_gap:.0f} µs (2.5x Gecikme Sıçraması)")
print("  - Teşhis Kararı             : KESME GECİKMESİ / THREAD JITTER TESPİT EDİLDİ")
print("  [PASS] Test 3: Zaman damgası dalgalanma teşhisi başarıyla doğrulandı.\n")

print("[PASS] Kod 4: 3 Kritik Uçuş Günlüğü Teşhis Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 100.000 ULog İkili Veri Paketi Ayrıştırma Benchmark'ı
# Nanosaniye düzeyinde paket çözme, struct unpack ve persentil analizi.
# ============================================================================
import time
import numpy as np

NUM_RECORDS = 100_000
latencies_us = np.empty(NUM_RECORDS, dtype=np.float64)

# 100.000 adet ULog veri paketi oluştur (Bellekte hazır bayt dizisi)
# Her paket: 3B msg_hdr + 2B msg_id + 8B timestamp + 12B roll/pitch/yaw = 25 Bayt
sample_packet = struct.pack("<HBHQfff", 22, MSG_TYPE_DATA, 1, 1000000, 1.5, -0.8, 90.0)
stream_buffer = sample_packet * NUM_RECORDS

print(f"[BENCHMARK] {NUM_RECORDS:,} ULog İkili Veri Paketi Ayrıştırılıyor...")
t_start = time.perf_counter()

offset = 0
for i in range(NUM_RECORDS):
    t0 = time.perf_counter_ns()
    
    # 1. Paket Başlığını Çöz (3 Bayt)
    msg_size, msg_type = struct.unpack_from("<HB", stream_buffer, offset)
    
    # 2. Veri Yükünü Çöz (22 Bayt)
    msg_id, t_us, r, p, y = struct.unpack_from("<HQfff", stream_buffer, offset + 3)
    
    offset += (3 + msg_size)
    t_end = time.perf_counter_ns()
    latencies_us[i] = (t_end - t0) / 1000.0 # ns -> us

t_total = time.perf_counter() - t_start

throughput_records_sec = NUM_RECORDS / t_total
avg_lat = np.mean(latencies_us)
p50 = np.percentile(latencies_us, 50)
p90 = np.percentile(latencies_us, 90)
p99 = np.percentile(latencies_us, 99)

print(f"\n[ULOG AYRIŞTIRMA BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - İşlem Verimi        : {throughput_records_sec:,.1f} kayıt/s (Hedef: > 150,000)")
print(f"  - Ortalama Gecikme    : {avg_lat:.2f} µs")
print(f"  - p50 (Medyan)        : {p50:.2f} µs")
print(f"  - p90 Gecikme         : {p90:.2f} µs")
print(f"  - p99 Kuyruk Gecikmesi: {p99:.2f} µs (Hedef: < 15.0 µs)")

# Doğrulamalar
assert throughput_records_sec > 150_000, f"Ayrıştırma verimi yetersiz: {throughput_records_sec}"
assert p99 < 15.0, f"p99 gecikmesi çok yüksek: {p99} µs"

print("\n[PASS] Kod 5: 100.000 ULog Paketi Ayrıştırma Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli 300 DPI Koyu Tema ULog ve Uçuş Analiz Dashboard'u
# gun_243_ulog_ve_flight_log_analizi.png dosyasını üretir.
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
import os

# Savunma Koyu Tema Renk Paleti
COLOR_BG = "#0F172A"       # Slate 900
COLOR_PANEL = "#1E293B"    # Slate 800
COLOR_TEXT = "#F8FAFC"     # Slate 50
COLOR_MUTED = "#94A3B8"    # Slate 400
COLOR_SP = "#38BDF8"       # Cyan (Setpoint)
COLOR_ACT = "#34D399"      # Yeşil (Actual)
COLOR_ERR = "#F87171"      # Kırmızı (Error / Dropout)
COLOR_WARN = "#FBBF24"     # Sarı (Vibration Peak)
COLOR_ACCENT = "#818CF8"   # İndigo

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: Roll Tutum Takip Hatası (Setpoint vs Actual) ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

ax1.plot(t_flight, roll_sp, color=COLOR_SP, linestyle="--", linewidth=2.0, label="Roll Setpoint [Hedef]")
ax1.plot(t_flight, roll_actual, color=COLOR_ACT, linewidth=2.0, label="Roll Actual [Gerçek]")
# Hata artıklarını altta göster
roll_err = roll_actual - roll_sp
ax1.plot(t_flight, roll_err, color=COLOR_ERR, linewidth=1.2, alpha=0.7, label=f"Hata (RMSE: {metrics['rmse_deg']:.2f}°)")

ax1.set_title("Panel 1: Roll Tutum Takip Performansı ve Hata Artıkları (Setpoint vs Actual)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xlabel("Zaman [s]", color=COLOR_MUTED, fontsize=10)
ax1.set_ylabel("Açı [Derece]", color=COLOR_MUTED, fontsize=10)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax1.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 2: İvmeölçer FFT Spektral Titreşim Analizi (PSD) ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

# 0 - 100 Hz aralığını çiz
valid_freq_mask = (freqs >= 0) & (freqs <= 100)
ax2.plot(freqs[valid_freq_mask], psd[valid_freq_mask], color=COLOR_WARN, linewidth=2.0, label="İvmeölçer Z Spektrumu (PSD)")
ax2.axvline(75.0, color=COLOR_ERR, linestyle="--", linewidth=1.8, label="Motor Harmonisi (75 Hz = 4500 RPM)")
ax2.axvline(25.0, color=COLOR_ACCENT, linestyle=":", linewidth=1.8, label="Gövde Rezonansı (25 Hz)")

ax2.annotate("Motor Tepe Noktası\n(Pervane Balansı)", xy=(75, np.max(psd)), xytext=(55, np.max(psd)*0.85),
             arrowprops=dict(arrowstyle="->", color=COLOR_ERR, lw=1.8),
             color=COLOR_ERR, fontsize=8, fontweight="bold")

ax2.set_title("Panel 2: IMU FFT Titreşim Spektrumu ve Motor RPM Tepe Analizi", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_xlabel("Frekans [Hz]", color=COLOR_MUTED, fontsize=10)
ax2.set_ylabel("Güç Spektral Yoğunluğu [m²/s⁴/Hz]", color=COLOR_MUTED, fontsize=10)
ax2.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax2.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 3: 100.000 ULog Kayıt Ayrıştırma Gecikme Histogramı ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

ax3.hist(latencies_us, bins=50, color=COLOR_SP, alpha=0.75, edgecolor="#0284C7")
ax3.axvline(p50, color=COLOR_ACT, linestyle="-", linewidth=2.2, label=f"p50 (Medyan): {p50:.2f} µs")
ax3.axvline(p90, color=COLOR_WARN, linestyle="--", linewidth=2.2, label=f"p90: {p90:.2f} µs")
ax3.axvline(p99, color=COLOR_ERR, linestyle="-.", linewidth=2.2, label=f"p99: {p99:.2f} µs")

ax3.set_title("Panel 3: 100k ULog İkili Paket Ayrıştırma Yürütme Gecikmesi Dağılımı", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("İşlem Süresi [µs]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("Örnek Sayısı", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 4: SD Kart Yazma Darboğazı ve Dropout ('O') Zaman Çizelgesi ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

t_sim_log = np.linspace(0, 60, 600)
# Simüle edilmiş SD kart yazma tampon doluluğu (%)
buf_fill = 20.0 + 10.0 * np.sin(t_sim_log * 0.2) + np.random.normal(0, 3, 600)
# 25. ve 45. saniyelerde SD kart blok yazma gecikmesi nedeniyle taşma
buf_fill[245:255] = 100.0
buf_fill[445:452] = 100.0

ax4.plot(t_sim_log, buf_fill, color=COLOR_SP, linewidth=2.0, label="Logger Ring Buffer Doluluk [%]")
ax4.axhline(100.0, color=COLOR_ERR, linestyle="--", linewidth=2.0, label="Tampon Taşma Sınırı (100%)")

# Dropout bölgelerini işaretle
ax4.scatter([25.0, 45.0], [100.0, 100.0], color=COLOR_ERR, s=150, zorder=5, label="Dropout Olayı ('O' Mesajı)")
ax4.annotate("150ms Veri Kaybı!\n(SD Kart Darboğazı)", xy=(25, 100), xytext=(28, 80),
             arrowprops=dict(arrowstyle="->", color=COLOR_ERR, lw=1.8),
             color=COLOR_ERR, fontsize=8, fontweight="bold")

ax4.set_title("Panel 4: SD Kart Tampon Sağlığı ve Dropout ('O') Kayıp Zaman Çizelgesi", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_xlabel("Uçuş Süresi [s]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylabel("Tampon Doluluk Oranı [%]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylim(0, 115)
ax4.tick_params(colors=COLOR_MUTED)
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax4.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="lower right", fontsize=8)

# Süper Başlık
plt.suptitle("PX4 AUTOPILOT — ULOG MİMARİSİ VE UÇUŞ GÜNLÜĞÜ (FLIGHT LOG) ANALİZ DASHBOARD'U", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_243/gun_243_ulog_ve_flight_log_analizi.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

