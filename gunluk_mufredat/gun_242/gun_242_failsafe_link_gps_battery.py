# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 242: Failsafe (Link / GPS / Battery) Standalone İcra Dosyası
"""

# ============================================================================
# KOD HÜCRESİ 1: Sağlık Durum Monitörü ve Failsafe Koşul Değerlendirici
# Veri bağı, GPS sıhhati ve 4S LiPo batarya voltaj ölçüm doğrulayıcısı.
# ============================================================================
from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple

class FailsafeAction(Enum):
    NONE             = auto()
    WARN_GCS         = auto()
    HOLD_LOITER      = auto()
    RETURN_TO_LAUNCH = auto()
    AUTO_LAND        = auto()
    TERMINATE_FLIGHT = auto()

@dataclass
class LinkState:
    last_rc_heartbeat_ms: int
    last_gcs_heartbeat_ms: int

@dataclass
class GpsState:
    fix_type: int        # 0: No Fix, 3: 3D Fix, 4: DGPS/RTK
    eph: float           # Yatay konum belirsizliği (m)
    last_fix_time_ms: int

@dataclass
class BatteryState:
    voltage: float       # Toplam paket voltajı (V)
    cell_voltages: Tuple[float, float, float, float] # 4S hücre voltajları
    remaining_pct: float # 0 - 100

class HealthEvaluator:
    RC_TIMEOUT_MS = 1000      # 1.0 saniye
    GCS_TIMEOUT_MS = 10000    # 10.0 saniye
    GPS_TIMEOUT_MS = 2000     # 2.0 saniye
    GPS_EPH_THRESHOLD = 5.0   # 5.0 metre üzeri konum geçersiz

    @classmethod
    def is_link_active(cls, link: LinkState, current_time_ms: int) -> Tuple[bool, bool]:
        rc_ok = (current_time_ms - link.last_rc_heartbeat_ms) <= cls.RC_TIMEOUT_MS
        gcs_ok = (current_time_ms - link.last_gcs_heartbeat_ms) <= cls.GCS_TIMEOUT_MS
        return rc_ok, gcs_ok

    @classmethod
    def is_gps_valid(cls, gps: GpsState, current_time_ms: int) -> bool:
        time_ok = (current_time_ms - gps.last_fix_time_ms) <= cls.GPS_TIMEOUT_MS
        fix_ok = gps.fix_type >= 3
        accuracy_ok = gps.eph <= cls.GPS_EPH_THRESHOLD
        return time_ok and fix_ok and accuracy_ok

    @classmethod
    def evaluate_battery_tier(cls, bat: BatteryState) -> str:
        min_cell = min(bat.cell_voltages)
        # Acil Seviye: Hücre <= 3.3V veya Kalan <= %5
        if bat.remaining_pct <= 5.0 or min_cell <= 3.30 or bat.voltage <= 13.20:
            return "EMERGENCY"
        # Kritik Seviye: Hücre <= 3.5V veya Kalan <= %10
        elif bat.remaining_pct <= 10.0 or min_cell <= 3.50 or bat.voltage <= 14.00:
            return "CRITICAL"
        # Düşük İkaz Seviyesi: Hücre <= 3.7V veya Kalan <= %20
        elif bat.remaining_pct <= 20.0 or min_cell <= 3.70 or bat.voltage <= 14.80:
            return "LOW"
        return "NORMAL"

# Doğrulama Testi: Sağlıklı Telemetri Girdisi
t_now = 50000 # 50. saniye
link = LinkState(last_rc_heartbeat_ms=49500, last_gcs_heartbeat_ms=48000)
gps = GpsState(fix_type=3, eph=1.2, last_fix_time_ms=49900)
bat = BatteryState(voltage=15.6, cell_voltages=(3.90, 3.91, 3.89, 3.90), remaining_pct=65.0)

rc_ok, gcs_ok = HealthEvaluator.is_link_active(link, t_now)
gps_ok = HealthEvaluator.is_gps_valid(gps, t_now)
bat_tier = HealthEvaluator.evaluate_battery_tier(bat)

assert rc_ok and gcs_ok, "Linkler aktif olmalı"
assert gps_ok, "GPS 3D Fix geçerli olmalı"
assert bat_tier == "NORMAL", "Batarya normal seviyede olmalı"

print("[PASS] Kod 1: Sağlık Monitörü ve Koşul Değerlendirici Doğrulandı.")
print(f"  - Veri Bağı Durumu   : RC={'AKTİF' if rc_ok else 'KOPUK'}, GCS={'AKTİF' if gcs_ok else 'KOPUK'}")
print(f"  - GPS Durumu         : 3D Fix={gps.fix_type}, EPH={gps.eph}m -> {'GEÇERLİ' if gps_ok else 'GEÇERSİZ'}")
print(f"  - Batarya Sağlığı    : {bat.voltage:.2f}V (%{bat.remaining_pct:.0f}) -> Durum: {bat_tier} [OK]")

# ============================================================================
# KOD HÜCRESİ 2: Çoklu Tehdit Hakemlik Motoru ve Eylem Seçici
# Link, GPS ve Batarya durumlarının öncelik sırasına göre çözümlenmesi.
# ============================================================================
class FailsafeArbitrator:
    @staticmethod
    def resolve_action(link_ok: bool, gps_ok: bool, bat_tier: str) -> Tuple[FailsafeAction, str]:
        # KURAL 1: Batarya Acil Seviyede ise (Emergency) -> GPS ve Link ne olursa olsun derhal İNİŞ
        if bat_tier == "EMERGENCY":
            return FailsafeAction.AUTO_LAND, "BATTERY_EMERGENCY_OVERRIDE"

        # KURAL 2: GPS Kaybı Varsa -> RTL yapılamaz!
        if not gps_ok:
            if not link_ok or bat_tier == "CRITICAL":
                return FailsafeAction.AUTO_LAND, "GPS_LOST_CANNOT_RTL_LANDING"
            else:
                return FailsafeAction.HOLD_LOITER, "GPS_LOST_FALLBACK_ALTCTL"

        # KURAL 3: Batarya Kritik Seviyede ise -> GPS var, derhal Eve Dönüş (RTL)
        if bat_tier == "CRITICAL":
            return FailsafeAction.RETURN_TO_LAUNCH, "BATTERY_CRITICAL_RTL"

        # KURAL 4: Veri Bağı Kesilmişse -> GPS var, Eve Dönüş (RTL)
        if not link_ok:
            return FailsafeAction.RETURN_TO_LAUNCH, "DATALINK_LOST_RTL"

        # KURAL 5: Batarya Düşük Seviyede ise -> İkaz Ver
        if bat_tier == "LOW":
            return FailsafeAction.WARN_GCS, "BATTERY_LOW_WARNING"

        return FailsafeAction.NONE, "ALL_SYSTEMS_NOMINAL"

# Test Matrisi: 5 Kritik Senaryonun Denetlenmesi
scenarios = [
    # (link_ok, gps_ok, bat_tier, expected_action, expected_reason)
    (False, True, "NORMAL", FailsafeAction.RETURN_TO_LAUNCH, "DATALINK_LOST_RTL"),
    (False, False, "NORMAL", FailsafeAction.AUTO_LAND, "GPS_LOST_CANNOT_RTL_LANDING"),
    (True, True, "CRITICAL", FailsafeAction.RETURN_TO_LAUNCH, "BATTERY_CRITICAL_RTL"),
    (True, True, "EMERGENCY", FailsafeAction.AUTO_LAND, "BATTERY_EMERGENCY_OVERRIDE"),
    (False, False, "EMERGENCY", FailsafeAction.AUTO_LAND, "BATTERY_EMERGENCY_OVERRIDE"),
]

for idx, (l_ok, g_ok, b_tr, exp_act, exp_rsn) in enumerate(scenarios, 1):
    action, reason = FailsafeArbitrator.resolve_action(l_ok, g_ok, b_tr)
    assert action == exp_act, f"Senaryo {idx} hatalı: {action} != {exp_act}"
    assert reason == exp_rsn, f"Senaryo {idx} sebep hatalı: {reason} != {exp_rsn}"

print("[PASS] Kod 2: Çoklu Tehdit Hakemlik Motoru ve Karar Seçici Doğrulandı.")
print("  - Senaryo 1: Link Kopuk + GPS Var           -> RETURN_TO_LAUNCH [OK]")
print("  - Senaryo 2: Link Kopuk + GPS Yok (Kör Uçuş) -> AUTO_LAND (RTL Yasaklandı) [OK]")
print("  - Senaryo 3: Batarya Kritik (%10)           -> RETURN_TO_LAUNCH [OK]")
print("  - Senaryo 4: Batarya Acil (%5)              -> AUTO_LAND (Dikey Acil İniş) [OK]")
print("  - Senaryo 5: Link Yok + GPS Yok + Batarya %5 -> AUTO_LAND (Üçlü Felaket İzolasyonu) [OK]")

# ============================================================================
# KOD HÜCRESİ 3: 30 Saniyelik Çoklu Arıza (Link -> GPS -> Batarya) Uçuş Simülasyonu
# Görev uçuşu, veri bağı kaybı, GPS karartması ve acil dikey iniş dinamikleri.
# ============================================================================
class MissionFlightSimulator:
    def __init__(self):
        self.t_history = []
        self.alt_history = []
        self.mode_history = []
        self.action_history = []

    def run_simulation(self):
        # 0'dan 30 saniyeye 0.1 saniye adımlarla simülasyon (300 adım)
        dt = 0.1
        current_time = 0.0
        altitude = 50.0
        
        while current_time <= 30.0:
            # 1. Çevresel Durumları Belirle (Arıza Enjeksiyonları)
            # t >= 10s: Link Kopar
            link_ok = current_time < 10.0
            
            # t >= 15s: GPS Kararır (Jamming)
            gps_ok = current_time < 15.0
            
            # Batarya Profili: t=20s'de acil seviyeye çöker
            if current_time < 20.0:
                bat_tier = "NORMAL"
            else:
                bat_tier = "EMERGENCY"
                
            # 2. Failsafe Kararını Çözümle
            action, reason = FailsafeArbitrator.resolve_action(link_ok, gps_ok, bat_tier)
            
            # 3. İrtifa Fiziği
            if action == FailsafeAction.AUTO_LAND:
                # İniş Hızı: 4.0 m/s
                altitude = max(0.0, altitude - 4.0 * dt)
            elif action == FailsafeAction.RETURN_TO_LAUNCH:
                # RTL İrtifası Sabit 50m
                altitude = 50.0
            elif action == FailsafeAction.HOLD_LOITER:
                altitude = 50.0
                
            # Kaydet
            self.t_history.append(current_time)
            self.alt_history.append(altitude)
            self.action_history.append(action)
            
            current_time += dt

sim = MissionFlightSimulator()
sim.run_simulation()

# Doğrulamalar:
# 5. saniyede: NONE (Görevde)
idx_5s = int(5.0 / 0.1)
assert sim.action_history[idx_5s] == FailsafeAction.NONE

# 12. saniyede: RETURN_TO_LAUNCH (Link koptu, GPS var)
idx_12s = int(12.0 / 0.1)
assert sim.action_history[idx_12s] == FailsafeAction.RETURN_TO_LAUNCH

# 17. saniyede: AUTO_LAND veya HOLD (Link yok + GPS yok -> AUTO_LAND)
idx_17s = int(17.0 / 0.1)
assert sim.action_history[idx_17s] == FailsafeAction.AUTO_LAND

# 22. saniyede: AUTO_LAND (Batarya acil)
idx_22s = int(22.0 / 0.1)
assert sim.action_history[idx_22s] == FailsafeAction.AUTO_LAND

# 30. saniyede: İrtifa tam 0 metre olmalı (Yere teker kondu)
assert sim.alt_history[-1] == 0.0

print("[PASS] Kod 3: 30 Saniyelik Çoklu Arıza Uçuş Simülasyonu Başarıyla Tamamlandı.")
print(f"  - t=5.0s  : Durum = {sim.action_history[idx_5s].name:<18} (Normal Görev Uçuşu)")
print(f"  - t=12.0s : Durum = {sim.action_history[idx_12s].name:<18} (Link Kaybı -> RTL Başlatıldı)")
print(f"  - t=17.0s : Durum = {sim.action_history[idx_17s].name:<18} (GPS Kaybı -> RTL İptal Edildi, İniş)")
print(f"  - t=22.0s : Durum = {sim.action_history[idx_22s].name:<18} (Batarya Acil -> Zorunlu İniş Devam)")
print(f"  - t=30.0s : Son İrtifa = {sim.alt_history[-1]:.1f}m (Yerde Güvenli)")

# ============================================================================
# KOD HÜCRESİ 4: 3 Kritik Failsafe Sınır ve Dayanıklılık Testi
# Voltaj debouncing filtresi, RTL link geri kazanımı ve GPS histerezis kalkanı.
# ============================================================================

# --- TEST 1: Geçici Voltaj Çökmesi (Voltage Sag) Debouncing Filtresi ---
print("[TEST 1] Geçici Voltaj Çökmesi (Transient Sag) Debouncing Testi...")
class BatteryDebounceFilter:
    DEBOUNCE_TIME_MS = 1000 # 1.0 saniye sürekli çöküş şartı

    def __init__(self):
        self.sag_start_time_ms: Optional[int] = None
        self.emergency_triggered = False

    def update(self, voltage: float, current_time_ms: int) -> bool:
        if voltage <= 13.20: # 4S için 3.3V/hücre çöküş sınırı
            if self.sag_start_time_ms is None:
                self.sag_start_time_ms = current_time_ms
            elif (current_time_ms - self.sag_start_time_ms) >= self.DEBOUNCE_TIME_MS:
                self.emergency_triggered = True
        else:
            # Voltaj normale döndü, debouncing sıfırla
            self.sag_start_time_ms = None
            self.emergency_triggered = False
            
        return self.emergency_triggered

filter_bat = BatteryDebounceFilter()

# 0 - 300 ms: Ani gaz verme sebebiyle voltaj 13.0V'a çöktü (Sag)
assert filter_bat.update(13.0, 0) == False
assert filter_bat.update(13.0, 300) == False # 300ms < 1000ms, henüz tetiklenmemeli

# 400 ms: Gaz kesildi, voltaj 15.0V'a geri sıçradı
assert filter_bat.update(15.0, 400) == False
assert filter_bat.sag_start_time_ms is None, "Debounce zamanı sıfırlanmadı!"

# 1000 - 2100 ms: Gerçek hücre tükenmesi (1100 ms boyunca 13.0V)
assert filter_bat.update(13.0, 1000) == False
assert filter_bat.update(13.0, 1500) == False
assert filter_bat.update(13.0, 2050) == True, "1050 ms sonra acil durum tetiklenmeliydi!"

print("  - 300ms Geçici Voltaj Çökmesi (13.0V) : FİLTRELENDİ (Sahte İniş Engellendi)")
print("  - 1050ms Sürekli Voltaj Çökmesi      : TETİKLENDİ (Gerçek Batarya Arızası)")
print("  [PASS] Test 1: Voltaj debouncing filtresi başarıyla doğrulandı.\n")

# --- TEST 2: RTL Esnasında Veri Bağının Geri Gelmesi ---
print("[TEST 2] RTL Esnasında Veri Bağının Geri Gelmesi (Link Re-acquisition)...")
def handle_link_recovery(current_mode: str, link_recovered: bool, pilot_takeover: bool) -> str:
    # Kural: Link geri gelse dahi pilot açıkça manuel müdahale (takeover) yapana kadar RTL devam eder
    if current_mode == "RTL":
        if link_recovered and not pilot_takeover:
            return "CONTINUE_RTL"
        elif link_recovered and pilot_takeover:
            return "MANUAL_POSCTL"
    return current_mode

assert handle_link_recovery("RTL", link_recovered=True, pilot_takeover=False) == "CONTINUE_RTL"
assert handle_link_recovery("RTL", link_recovered=True, pilot_takeover=True) == "MANUAL_POSCTL"
print("  - Link Geri Geldi (Müdahale Yok) : CONTINUE_RTL (Üsse Uçuş Güvenle Sürüyor)")
print("  - Link Geri Geldi + Pilot Müdahale: MANUAL_POSCTL (Kontrol Pilota Devredildi)")
print("  [PASS] Test 2: RTL link geri kazanım kararlılığı doğrulandı.\n")

# --- TEST 3: Dalgalı GPS (Intermittent Glitch) Histerezis Kalkanı ---
print("[TEST 3] Dalgalı GPS (Intermittent Glitch) Histerezis Testi...")
class GpsHysteresisFilter:
    REQUIRED_HEALTHY_SAMPLES = 5

    def __init__(self):
        self.healthy_count = 0
        self.is_trusted = True

    def update(self, gps_valid_now: bool) -> bool:
        if not gps_valid_now:
            self.healthy_count = 0
            self.is_trusted = False
        else:
            self.healthy_count += 1
            if self.healthy_count >= self.REQUIRED_HEALTHY_SAMPLES:
                self.is_trusted = True
        return self.is_trusted

hyst = GpsHysteresisFilter()
# GPS aniden koptu
assert hyst.update(False) == False
# 1 örnek iyi geldi (hemen güvenilmemeli!)
assert hyst.update(True) == False
assert hyst.update(True) == False
assert hyst.update(True) == False
assert hyst.update(True) == False
# 5. ardışık sağlıklı örnek: Artık güvenilebilir
assert hyst.update(True) == True

print("  - 1 Başarılı GPS Paketi : GÜVENİLMİYOR (Histerezis Kalkanı)")
print("  - 5 Ardışık Sağlıklı GPS: GÜVENİLİR KABUL EDİLDİ (Kararlılık Sağlandı)")
print("  [PASS] Test 3: GPS histerezis kalkanı başarıyla doğrulandı.\n")

print("[PASS] Kod 4: 3 Kritik Failsafe Sınır Testi Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 5: 100.000 Döngülük Failsafe Hakemlik Benchmark'ı
# Nanosaniye düzeyinde çoklu tehdit çözümü, eylem seçimi ve persentil analizi.
# ============================================================================
import time
import numpy as np

NUM_CYCLES = 100_000
latencies_us = np.empty(NUM_CYCLES, dtype=np.float64)

# Rastgele sağlık durumları
rand_link = np.random.rand(NUM_CYCLES) > 0.05   # %5 link kaybı
rand_gps = np.random.rand(NUM_CYCLES) > 0.03    # %3 GPS kaybı
rand_bats = np.random.choice(["NORMAL", "LOW", "CRITICAL", "EMERGENCY"], size=NUM_CYCLES, p=[0.85, 0.10, 0.04, 0.01])

print(f"[BENCHMARK] {NUM_CYCLES:,} Failsafe Hakemlik Değerlendirmesi Başlatılıyor...")
t_start = time.perf_counter()

for i in range(NUM_CYCLES):
    t0 = time.perf_counter_ns()
    
    # Hakemlik kararı
    action, reason = FailsafeArbitrator.resolve_action(rand_link[i], rand_gps[i], rand_bats[i])
    
    t_end = time.perf_counter_ns()
    latencies_us[i] = (t_end - t0) / 1000.0 # ns -> us

t_total = time.perf_counter() - t_start

throughput_evals_sec = NUM_CYCLES / t_total
avg_lat = np.mean(latencies_us)
p50 = np.percentile(latencies_us, 50)
p90 = np.percentile(latencies_us, 90)
p99 = np.percentile(latencies_us, 99)

print(f"\n[FAILSAFE HAKEMLİK BENCHMARK SONUÇLARI]")
print(f"  - Toplam Süre         : {t_total:.4f} saniye")
print(f"  - İşlem Verimi        : {throughput_evals_sec:,.1f} değerlendirme/s (Hedef: > 150,000)")
print(f"  - Ortalama Gecikme    : {avg_lat:.2f} µs")
print(f"  - p50 (Medyan)        : {p50:.2f} µs")
print(f"  - p90 Gecikme         : {p90:.2f} µs")
print(f"  - p99 Kuyruk Gecikmesi: {p99:.2f} µs (Hedef: < 15.0 µs)")

# Doğrulamalar
assert throughput_evals_sec > 150_000, f"Değerlendirme verimi yetersiz: {throughput_evals_sec}"
assert p99 < 15.0, f"p99 gecikmesi çok yüksek: {p99} µs"

print("\n[PASS] Kod 5: 100.000 Döngülük Failsafe Benchmark'ı Başarıyla Tamamlandı.")

# ============================================================================
# KOD HÜCRESİ 6: 4-Panelli 300 DPI Koyu Tema Failsafe Dashboard'u
# gun_242_failsafe_link_gps_battery.png dosyasını üretir.
# ============================================================================
import matplotlib.pyplot as plt
import numpy as np
import os

# Koyu Tema Savunma Renk Paleti
COLOR_BG = "#0F172A"       # Slate 900
COLOR_PANEL = "#1E293B"    # Slate 800
COLOR_TEXT = "#F8FAFC"     # Slate 50
COLOR_MUTED = "#94A3B8"    # Slate 400
COLOR_RTL = "#38BDF8"      # Cyan (RTL)
COLOR_LAND = "#F87171"     # Kırmızı (Auto Land)
COLOR_WARN = "#FBBF24"     # Sarı (Warning / AltHold)
COLOR_SAFE = "#34D399"     # Yeşil (Nominal)
COLOR_ACCENT = "#818CF8"   # İndigo

fig, axs = plt.subplots(2, 2, figsize=(18, 12), facecolor=COLOR_BG)
plt.subplots_adjust(wspace=0.25, hspace=0.32)

# --- PANEL 1: Failsafe Hakemlik Öncelik Karar Matrisi ---
ax1 = axs[0, 0]
ax1.set_facecolor(COLOR_PANEL)

threat_levels = [
    "Batarya Acil (<= 5%)\n[Dikey İniş Şart]",
    "GPS Kaybı\n[RTL Yasak - İniş Yap]",
    "Batarya Kritik (<= 10%)\n[GPS Varsa RTL]",
    "Link Kaybı (RC/GCS)\n[GPS Varsa RTL]",
    "Batarya Düşük (<= 20%)\n[GCS İkazı Ver]"
]
priorities = [5, 4, 3, 2, 1]
colors_p1 = [COLOR_LAND, COLOR_LAND, COLOR_RTL, COLOR_RTL, COLOR_WARN]

bars = ax1.barh(threat_levels, priorities, color=colors_p1, edgecolor=COLOR_TEXT, height=0.6)
for bar, p in zip(bars, priorities):
    ax1.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height()/2.0, 
             f"Öncelik Seviyesi {p}", color=COLOR_TEXT, va="center", fontsize=9, fontweight="bold")

ax1.set_title("Panel 1: Failsafe Hakemlik Öncelik Hiyerarşisi (1: Düşük, 5: En Yüksek)", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax1.set_xlabel("Öncelik Derecesi", color=COLOR_MUTED, fontsize=10)
ax1.set_xlim(0, 6.5)
ax1.tick_params(colors=COLOR_MUTED)
ax1.grid(True, color="#334155", linestyle=":", alpha=0.6, axis="x")

# --- PANEL 2: 4S LiPo Batarya Deşarj Eğrisi ve Emniyet Eşikleri ---
ax2 = axs[0, 1]
ax2.set_facecolor(COLOR_PANEL)

discharge_pct = np.linspace(100, 0, 100)
# Tipik LiPo deşarj voltaj eğrisi formülasyonu
v_curve = 13.0 + 3.8 * (discharge_pct / 100.0)**0.45

ax2.plot(discharge_pct, v_curve, color=COLOR_SAFE, linewidth=2.5, label="Paket Voltajı (4S)")
ax2.axhline(14.8, color=COLOR_WARN, linestyle="--", linewidth=1.8, label="Düşük İkaz Eşiği (%20 - 14.8V)")
ax2.axhline(14.0, color=COLOR_RTL, linestyle="--", linewidth=1.8, label="Kritik RTL Eşiği (%10 - 14.0V)")
ax2.axhline(13.2, color=COLOR_LAND, linestyle="--", linewidth=2.2, label="Acil İniş Eşiği (%5 - 13.2V)")

# Eşik bölgeleri
ax2.axvspan(10, 20, color=COLOR_WARN, alpha=0.15)
ax2.axvspan(5, 10, color=COLOR_RTL, alpha=0.2)
ax2.axvspan(0, 5, color=COLOR_LAND, alpha=0.25)

ax2.set_title("Panel 2: 4S LiPo Batarya Voltaj Deşarjı ve Kademeli Emniyet Eşikleri", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax2.set_xlabel("Kalan Kapasite [%]", color=COLOR_MUTED, fontsize=10)
ax2.set_ylabel("Paket Voltajı [V]", color=COLOR_MUTED, fontsize=10)
ax2.set_xlim(100, 0) # Geriye doğru deşarj
ax2.tick_params(colors=COLOR_MUTED)
ax2.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax2.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 3: 100.000 Failsafe Değerlendirme Gecikme Dağılımı ---
ax3 = axs[1, 0]
ax3.set_facecolor(COLOR_PANEL)

ax3.hist(latencies_us, bins=50, color=COLOR_ACCENT, alpha=0.75, edgecolor="#4F46E5")
ax3.axvline(p50, color=COLOR_SAFE, linestyle="-", linewidth=2.2, label=f"p50 (Medyan): {p50:.2f} µs")
ax3.axvline(p90, color=COLOR_WARN, linestyle="--", linewidth=2.2, label=f"p90: {p90:.2f} µs")
ax3.axvline(p99, color=COLOR_LAND, linestyle="-.", linewidth=2.2, label=f"p99: {p99:.2f} µs")

ax3.set_title("Panel 3: 100k Failsafe Hakemlik Değerlendirme Yürütme Gecikmesi Dağılımı", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax3.set_xlabel("İşlem Süresi [µs]", color=COLOR_MUTED, fontsize=10)
ax3.set_ylabel("Örnek Sayısı", color=COLOR_MUTED, fontsize=10)
ax3.tick_params(colors=COLOR_MUTED)
ax3.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax3.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)

# --- PANEL 4: 30 Saniyelik Çoklu Arıza Simülasyon Uçuş Profili ---
ax4 = axs[1, 1]
ax4.set_facecolor(COLOR_PANEL)

ax4.plot(sim.t_history, sim.alt_history, color=COLOR_TEXT, linewidth=2.8, label="İHA İrtifası [m]")
ax4.axvspan(0, 10, color=COLOR_SAFE, alpha=0.15, label="MISSION (Nominal)")
ax4.axvspan(10, 15, color=COLOR_RTL, alpha=0.2, label="RTL (Link Koptu)")
ax4.axvspan(15, 20, color=COLOR_WARN, alpha=0.25, label="RTL İptal (GPS Kesildi)")
ax4.axvspan(20, 30, color=COLOR_LAND, alpha=0.25, label="AUTO_LAND (Batarya Acil)")

ax4.annotate("Link Koptu -> RTL", xy=(10, 50), xytext=(6, 40),
             arrowprops=dict(arrowstyle="->", color=COLOR_RTL, lw=1.8),
             color=COLOR_RTL, fontsize=8, fontweight="bold")
ax4.annotate("GPS Koptu -> RTL İptal!", xy=(15, 50), xytext=(12, 30),
             arrowprops=dict(arrowstyle="->", color=COLOR_WARN, lw=1.8),
             color=COLOR_WARN, fontsize=8, fontweight="bold")
ax4.annotate("Batarya %5 -> Dikey İniş", xy=(20, 50), xytext=(18, 15),
             arrowprops=dict(arrowstyle="->", color=COLOR_LAND, lw=1.8),
             color=COLOR_LAND, fontsize=8, fontweight="bold")

ax4.set_title("Panel 4: 30s Uçuşta Çoklu Arıza Tetikleme ve İrtifa Tepki Profili", color=COLOR_TEXT, fontsize=12, fontweight="bold", pad=10)
ax4.set_xlabel("Zaman [s]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylabel("İrtifa [m]", color=COLOR_MUTED, fontsize=10)
ax4.set_ylim(-2, 60)
ax4.tick_params(colors=COLOR_MUTED)
ax4.grid(True, color="#334155", linestyle=":", alpha=0.6)
ax4.legend(facecolor=COLOR_BG, edgecolor=COLOR_MUTED, labelcolor=COLOR_TEXT, loc="lower left", fontsize=8)

# Üst Başlık
plt.suptitle("PX4 AUTOPILOT — ÇOKLU TEHDİT FAILSAFE (LINK / GPS / BATTERY) HAKEMLİK DASHBOARD'U", 
             color=COLOR_TEXT, fontsize=15, fontweight="bold", y=0.98)

TARGET_PNG = r"c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_242/gun_242_failsafe_link_gps_battery.png"
plt.savefig(TARGET_PNG, dpi=300, facecolor=COLOR_BG, bbox_inches="tight")
plt.close()

file_size_kb = os.path.getsize(TARGET_PNG) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {TARGET_PNG}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'ın altında!"

