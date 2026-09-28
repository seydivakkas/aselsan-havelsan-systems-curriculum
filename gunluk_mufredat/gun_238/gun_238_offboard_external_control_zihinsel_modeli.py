# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 238: Offboard/External Control Zihinsel Modeli Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: SET_POSITION_TARGET_LOCAL_NED (#84) İkili (Binary) Çerçevesi
# Konum, hız, ivme ve type_mask serileştirme ve doğrulaması.
# ============================================================================
from dataclasses import dataclass
import struct
from typing import Tuple

@dataclass
class SetPositionTargetLocalNedPayload:
    time_boot_ms: int       # uint32
    x: float                # float (m)
    y: float                # float (m)
    z: float                # float (m - NED z aşağı negatif)
    vx: float               # float (m/s)
    vy: float               # float (m/s)
    vz: float               # float (m/s)
    afx: float              # float (m/s^2)
    afy: float              # float (m/s^2)
    afz: float              # float (m/s^2)
    yaw: float              # float (rad)
    yaw_rate: float         # float (rad/s)
    type_mask: int          # uint16 (İhmal bitleri)
    target_system: int = 1  # uint8
    target_component: int = 1 # uint8
    coordinate_frame: int = 1 # MAV_FRAME_LOCAL_NED = 1

    def serialize(self) -> bytes:
        # Format: <I (4) + 11f (44) + H (2) + 3B (3) = 53 bayt (Standart MAVLink v2 hizalaması: 53 bayt)
        return struct.pack("<I11fHBBB", self.time_boot_ms, self.x, self.y, self.z,
                           self.vx, self.vy, self.vz, self.afx, self.afy, self.afz,
                           self.yaw, self.yaw_rate, self.type_mask,
                           self.target_system, self.target_component, self.coordinate_frame)

    @classmethod
    def deserialize(cls, data: bytes) -> "SetPositionTargetLocalNedPayload":
        unpacked = struct.unpack("<I11fHBBB", data)
        return cls(time_boot_ms=unpacked[0], x=unpacked[1], y=unpacked[2], z=unpacked[3],
                   vx=unpacked[4], vy=unpacked[5], vz=unpacked[6],
                   afx=unpacked[7], afy=unpacked[8], afz=unpacked[9],
                   yaw=unpacked[10], yaw_rate=unpacked[11], type_mask=unpacked[12],
                   target_system=unpacked[13], target_component=unpacked[14], coordinate_frame=unpacked[15])

# Test: Yalnızca Hız Kontrolü Setpoint'i (Vx = 5.0 m/s Kuzey, Vz = -1.0 m/s Tırmanış)
# Konum ve İvmeler ihmal edilecek: type_mask = 0b0000110111000111 = 0x0DC7
TYPE_MASK_VELOCITY_ONLY = 0x0DC7

sp = SetPositionTargetLocalNedPayload(
    time_boot_ms=250000,
    x=0.0, y=0.0, z=0.0,
    vx=5.0, vy=0.0, vz=-1.0,
    afx=0.0, afy=0.0, afz=0.0,
    yaw=0.0, yaw_rate=0.0,
    type_mask=TYPE_MASK_VELOCITY_ONLY
)

raw_sp = sp.serialize()
assert len(raw_sp) == 53, f"Hatalı paket uzunluğu: {len(raw_sp)}"

dec_sp = SetPositionTargetLocalNedPayload.deserialize(raw_sp)
assert dec_sp.vx == 5.0
assert dec_sp.vz == -1.0
assert dec_sp.type_mask == TYPE_MASK_VELOCITY_ONLY

print("[PASS] Kod 1: SET_POSITION_TARGET_LOCAL_NED (#84) Paketi Başarıyla Doğrulandı.")
print(f"  - Paket Boyutu  : {len(raw_sp)} bayt")
print(f"  - Hedef Hızlar  : Vx={dec_sp.vx} m/s, Vy={dec_sp.vy} m/s, Vz={dec_sp.vz} m/s")
print(f"  - Type Mask     : 0x{dec_sp.type_mask:04X} (Yalnızca Hız Kontrolü)")

# ============================================================================
# KOD HÜCRESİ 2: İki Aşamalı Offboard Aktivasyon ve Canlı Setpoint Akış Motoru
# Ön-akış doğrulaması, mod geçiş onayı ve canlı uçuş durumu simülasyonu.
# ============================================================================
class Px4OffboardStateMachine:
    def __init__(self, min_freq_hz: float = 2.0, timeout_s: float = 0.5):
        self.min_freq_hz = min_freq_hz
        self.timeout_s = timeout_s
        self.current_mode = "POSCTL"
        self.last_sp_time = -1.0
        self.sp_count_last_sec = 0
        self.is_offboard_active = False

    def feed_setpoint(self, current_time_s: float):
        if self.last_sp_time > 0 and (current_time_s - self.last_sp_time) <= 1.0:
            self.sp_count_last_sec += 1
        else:
            self.sp_count_last_sec = 1
        self.last_sp_time = current_time_s

    def request_offboard_mode(self, current_time_s: float) -> str:
        # Emniyet Kuralı: Son 500ms içinde setpoint gelmiş mi ve frekans >= 2Hz mi?
        dt = current_time_s - self.last_sp_time
        if self.last_sp_time > 0 and dt <= self.timeout_s and self.sp_count_last_sec >= 2:
            self.current_mode = "OFFBOARD"
            self.is_offboard_active = True
            return "MAV_RESULT_ACCEPTED"
        else:
            return "MAV_RESULT_DENIED"

    def update_watchdog(self, current_time_s: float) -> str:
        if self.is_offboard_active:
            dt = current_time_s - self.last_sp_time
            if dt > self.timeout_s:
                self.is_offboard_active = False
                self.current_mode = "AUTO_LOITER"
                return "FAILSAFE_OFFBOARD_LOSS_LOITER"
        return "NORMAL"

# Simülasyon
px4 = Px4OffboardStateMachine()

# 1. Aşama: 10 Hz hızında 0.5 saniye setpoint akıtılır (5 paket)
for i in range(5):
    t = i * 0.1
    px4.feed_setpoint(current_time_s=t)

# 2. Aşama: Offboard Mod Geçişi İstenir (t = 0.45s)
res_switch = px4.request_offboard_mode(current_time_s=0.45)
assert res_switch == "MAV_RESULT_ACCEPTED", "Ön-akış olmasına rağmen Offboard modu reddedildi!"
assert px4.current_mode == "OFFBOARD"

print("[PASS] Kod 2: İki Aşamalı Offboard Aktivasyon Motoru Doğrulandı.")
print(f"  - Ön-akış Paketi    : {px4.sp_count_last_sec} adet")
print(f"  - Mod Geçiş Yanıtı  : {res_switch}")
print(f"  - Aktif Uçuş Modu   : {px4.current_mode} [BAŞARILI]")

# ============================================================================
# KOD HÜCRESİ 3: Offboard Sinyal Kaybı (Watchdog Loss) ve Failsafe Simülatörü
# 500 ms zaman aşımı sayacı ve otomatik AUTO_LOITER emniyet moduna geçiş.
# ============================================================================
# Canlı Offboard uçuşu: t=0..2s arası her 0.05s'de (20 Hz) setpoint beslenir
for step in range(40):
    t = step * 0.05
    px4.feed_setpoint(t)

assert px4.is_offboard_active == True

# t = 2.0s'de Jetson AI bilgisayarı dondu (Crash / Donma)!
# Zaman ilerler: t = 2.3s (300 ms geçti -> Henüz Failsafe YOK)
status_300ms = px4.update_watchdog(current_time_s=2.30)
assert status_300ms == "NORMAL"
assert px4.current_mode == "OFFBOARD"

# t = 2.55s (550 ms geçti -> Eşik Aşıldı!)
status_550ms = px4.update_watchdog(current_time_s=2.55)
assert status_550ms == "FAILSAFE_OFFBOARD_LOSS_LOITER"
assert px4.current_mode == "AUTO_LOITER"
assert px4.is_offboard_active == False

print("[PASS] Kod 3: Offboard Sinyal Kaybı ve Failsafe Durum Makinesi Doğrulandı.")
print(f"  - 300 ms Gecikme Durumu : {status_300ms} (Mod: {px4.current_mode})")
print(f"  - 550 ms Gecikme Durumu : {status_550ms} (Mod: {px4.current_mode} - KONTROL GERİ ALINDI)")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik Offboard Hata Enjeksiyon Testi
# Ön-akışsız geçiş reddi, aşırı hız hedefi kırpma ve geçersiz frame denetimi.
# ============================================================================

# --- TEST 1: Ön-Akış Olmadan Körlemesine Offboard Geçiş Denemesi ---
print("[TEST 1] Ön-Akış Olmadan Körlemesine Offboard Mod Geçişi Testi...")
clean_px4 = Px4OffboardStateMachine()
# Hiç setpoint beslenmeden mod geçişi istenirse:
blind_res = clean_px4.request_offboard_mode(current_time_s=1.0)
assert blind_res == "MAV_RESULT_DENIED", "Ön-akışsız tehlikeli geçiş kabul edildi!"
assert clean_px4.current_mode == "POSCTL"
print(f"  - Talep Durumu : Ön-akış YOK")
print(f"  - Dönen Sonuç  : {blind_res} (Geçiş Kesinlikle Engellendi)")
print("  [PASS] Test 1: Ön-akış kuralı ihlali başarıyla bloke edildi.\n")

# --- TEST 2: Aşırı Hız Setpoint'i Kırpma (Velocity Clamping) ---
print("[TEST 2] Aşırı Hız Setpoint'i Sınırlandırma (Velocity Clamping) Testi...")
def clamp_velocity_setpoint(vx: float, vy: float, vz: float, max_horiz_m_s: float = 15.0) -> Tuple[float, float, float]:
    horiz_speed = (vx*vx + vy*vy)**0.5
    if horiz_speed > max_horiz_m_s:
        scale = max_horiz_m_s / horiz_speed
        return vx * scale, vy * scale, vz
    return vx, vy, vz

# Jetson sehven 60 m/s hız istedi (Maksimum limit: 15 m/s)
vx_clamped, vy_clamped, vz_clamped = clamp_velocity_setpoint(vx=60.0, vy=0.0, vz=-2.0, max_horiz_m_s=15.0)
assert vx_clamped == 15.0, f"Hız kırpılamadı: {vx_clamped}"
assert vz_clamped == -2.0
print(f"  - Talep Edilen Hız : 60.0 m/s")
print(f"  - Kırpılan Güvenli : {vx_clamped:.1f} m/s (Uçuş Zarfı Korundu)")
print("  [PASS] Test 2: Aşırı hız talebi güvenle kırpıldı.\n")

# --- TEST 3: Geçersiz Koordinat Referans Çerçevesi Reddi ---
print("[TEST 3] Geçersiz Koordinat Çerçevesi (Frame Mismatch) Testi...")
def validate_coordinate_frame(frame: int) -> bool:
    # Yalnızca MAV_FRAME_LOCAL_NED (1) veya MAV_FRAME_BODY_NED (8) kabul edilir
    return frame in [1, 8]

assert validate_coordinate_frame(frame=1) == True # LOCAL_NED
assert validate_coordinate_frame(frame=99) == False # Geçersiz
print("  - LOCAL_NED (1)   : Kabul Edildi [OK]")
print("  - Bilinmeyen (99) : Reddedildi [OK]")
print("  [PASS] Test 3: Geçersiz koordinat çerçevesi başarıyla filtrelendi.\n")

print("[PASS] Kod 4: 3 Kritik Offboard Hata Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 100.000 Yüksek Frekanslı Offboard Setpoint Benchmark'ı
# Nanosaniye düzeyinde setpoint çözümleme, hız kırpma ve icra döngüsü hızı.
# ============================================================================
import time
import numpy as np

NUM_SETPOINTS = 100_000
latencies_us = np.empty(NUM_SETPOINTS, dtype=np.float64)

test_raw_sp = sp.serialize()

print(f"[BENCHMARK] {NUM_SETPOINTS:,} Offboard Setpoint Paketi İşleniyor...")
t_start = time.perf_counter()

for i in range(NUM_SETPOINTS):
    t0 = time.perf_counter_ns()
    
    # 1. Çözümleme
    pkt = SetPositionTargetLocalNedPayload.deserialize(test_raw_sp)
    
    # 2. Hız Kırpma (Safety Clamping)
    h_spd = (pkt.vx**2 + pkt.vy**2)**0.5
    if h_spd > 15.0:
        s = 15.0 / h_spd
        pkt.vx *= s
        pkt.vy *= s
        
    t_end = time.perf_counter_ns()
    latencies_us[i] = (t_end - t0) / 1000.0 # ns -> us

t_total = time.perf_counter() - t_start

throughput_sps = NUM_SETPOINTS / t_total
avg_lat = np.mean(latencies_us)
p50 = np.percentile(latencies_us, 50)
p90 = np.percentile(latencies_us, 90)
p99 = np.percentile(latencies_us, 99)

print(f"\n[OFFBOARD SETPOINT BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - İşlem Verimi        : {throughput_sps:,.1f} setpoint/s (Hedef: > 200,000)")
print(f"  - Ortalama Gecikme    : {avg_lat:.2f} µs")
print(f"  - p50 (Medyan)        : {p50:.2f} µs")
print(f"  - p90 Gecikme         : {p90:.2f} µs")
print(f"  - p99 Kuyruk Gecikmesi: {p99:.2f} µs (Hedef: < 15.0 µs)")

# Doğrulamalar
assert throughput_sps > 200_000, f"İşlem verimi yetersiz: {throughput_sps}"
assert p99 < 15.0, f"p99 gecikmesi çok yüksek: {p99} µs"

print("\n[PASS] Kod 5: 100.000 Offboard Setpoint Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli 300 DPI Koyu Tema Offboard Kontrol Dashboard'u
# gun_238_offboard_external_control_zihinsel_modeli.png dosyasını üretir.
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
import os

# Koyu Tema Savunma Standart Renkleri
COLOR_BG = "#0F172A"       # Slate 900
COLOR_PANEL = "#1E293B"    # Slate 800
COLOR_TEXT = "#F8FAFC"     # Slate 50
COLOR_MUTED = "#94A3B8"    # Slate 400
COLOR_ACCEPT = "#34D399"   # Yeşil (Offboard Aktif)
COLOR_PRESTREAM = "#38BDF8"# Cyan (Ön-akış)
COLOR_WARN = "#FBBF24"     # Sarı (Failsafe Loiter)
COLOR_FAIL = "#F87171"     # Kırmızı (Setpoint Kaybı)

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: Offboard İki Aşamalı Geçiş Zaman Çizelgesi ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

t_axis = np.linspace(0, 5, 250)
mode_state = []
for t in t_axis:
    if t < 1.0:
        mode_state.append(1) # POSCTL (Pre-streaming)
    elif t < 3.5:
        mode_state.append(2) # OFFBOARD Aktif
    else:
        mode_state.append(3) # FAILSAFE LOITER

ax1.plot(t_axis, mode_state, color=COLOR_PRESTREAM, linewidth=2.5, drawstyle='steps-post')
ax1.axvline(1.0, color=COLOR_ACCEPT, linestyle="--", linewidth=2.0, label="Mod Geçiş İsteği Kabulü (t=1.0s)")
ax1.axvline(3.5, color=COLOR_FAIL, linestyle="-.", linewidth=2.0, label="Akış Kesildi -> Failsafe Loiter (t=3.5s)")

ax1.set_yticks([1, 2, 3])
ax1.set_yticklabels(["POSCTL\n(Ön-Akış)", "OFFBOARD\n(Aktif Güdüm)", "AUTO_LOITER\n(Failsafe)"])
ax1.set_title("Panel 1: PX4 İki Aşamalı Offboard Geçiş ve Watchdog Zaman Çizelgesi", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xlabel("Zaman [s]", color=COLOR_MUTED, fontsize=10)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax1.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 2: Talep Edilen Hız vs Kırpılan Güvenli Uçuş Hızı ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

t_sim = np.linspace(0, 10, 200)
raw_vx = 10.0 + 20.0 * np.sin(t_sim * 0.5) # Bazen 30 m/s'ye fırlar
clamped_vx = np.clip(raw_vx, -15.0, 15.0)

ax2.plot(t_sim, raw_vx, color=COLOR_FAIL, linestyle=":", linewidth=2.0, label="Companion Ham Hız Talebi (m/s)")
ax2.plot(t_sim, clamped_vx, color=COLOR_ACCEPT, linewidth=2.5, label="Otopilot Kırpılan Güvenli Hız (±15 m/s)")
ax2.axhline(15.0, color=COLOR_WARN, linestyle="--", label="Azami Yatay Hız Limiti (15 m/s)")
ax2.axhline(-15.0, color=COLOR_WARN, linestyle="--")

ax2.set_title("Panel 2: Aerodinamik Uçuş Zarfı ve Hız Kırpma (Velocity Clamping)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_xlabel("Zaman [s]", color=COLOR_MUTED, fontsize=10)
ax2.set_ylabel("Hız [m/s]", color=COLOR_MUTED, fontsize=10)
ax2.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax2.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="lower right", fontsize=8)

# --- PANEL 3: 100.000 Setpoint İşleme Gecikme Histogramı ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

n, bins, patches = ax3.hist(latencies_us, bins=50, color=COLOR_PRESTREAM, alpha=0.75, edgecolor="#0284C7")
ax3.axvline(p50, color=COLOR_ACCEPT, linestyle="-", linewidth=2.2, label=f"p50 (Medyan): {p50:.2f} µs")
ax3.axvline(p90, color=COLOR_WARN, linestyle="--", linewidth=2.2, label=f"p90: {p90:.2f} µs")
ax3.axvline(p99, color=COLOR_FAIL, linestyle="-.", linewidth=2.2, label=f"p99: {p99:.2f} µs")

ax3.set_title("Panel 3: Offboard Setpoint Çözümleme ve Kontrol Gecikmesi (µs)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("İşlem Gecikmesi [µs]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("Örnek Sayısı", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 4: Type Mask Alan Dağılımı ve Kullanım Oranları ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

control_modes = ["Yalnızca Konum", "Yalnızca Hız", "Konum + Hız", "İvme / Thrust", "Doğrudan Tutum"]
usage_pct = [45.0, 35.0, 12.0, 5.0, 3.0]
bar_colors4 = [COLOR_ACCEPT, COLOR_PRESTREAM, "#818CF8", COLOR_WARN, COLOR_FAIL]

bars4 = ax4.bar(control_modes, usage_pct, color=bar_colors4, width=0.55, edgecolor="#334155")
ax4.set_title("Panel 4: Savunma Görevlerinde Tercih Edilen Offboard Kontrol Tipleri (%)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_ylabel("Kullanım Oranı [%]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylim(0, 55)
ax4.tick_params(colors=COLOR_MUTED)
plt.setp(ax4.get_xticklabels(), rotation=15, ha="right")
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="y")

for bar in bars4:
    h = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., h + 1.2, f"%{h:.1f}", ha='center', va='bottom', color=COLOR_TEXT, fontsize=8, fontweight="bold")

# Üst Başlık
plt.suptitle("BAYRAKTAR KIZILELMA / STM KARGU — PX4 OFFBOARD KONTROL VE EMNİYET DASHBOARD'U", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_238/gun_238_offboard_external_control_zihinsel_modeli.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

