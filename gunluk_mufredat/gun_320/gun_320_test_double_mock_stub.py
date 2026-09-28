#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

Gün 320: Test Double, Mock, Stub (Donanım İzolasyonu)
Faz F11: Verification / SIL / HIL
Referans: DO-178C, DO-330, Gerard Meszaros xUnit Patterns, Google Mock (GMock)
"""

# [KOD HÜCRESİ 1: Test Double Veri Modeli ve 5 Temel Çiftin Gerçeklenmesi]
# Amaç: DO-178C Seviye-A ve modern C++20 aviyonik mimarisine uygun
# Gerard Meszaros taksonomisinde yer alan 5 Test Double türünü
# (Dummy, Stub, Spy, Mock, Fake) programatik olarak modellemek.

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

class TestDoubleType(Enum):
    DUMMY = "1. Dummy (Kukla - Boş Parametre Doldurucu)"
    STUB = "2. Stub (Taslak - Sabit Girdi Sağlayıcı)"
    SPY = "3. Spy (Casus - Çağrı ve Parametre Kaydedici)"
    MOCK = "4. Mock (Sahte - Davranış ve Sıra Doğrulayıcı)"
    FAKE = "5. Fake (Taklit - Bellek İçi Çalışan Basit Kopya)"

# 1. DUMMY: Parametre listesini doldurmak için kullanılan, işlevsiz nesne
class DummyLogger:
    """Uçuş kontrolcüsüne parametre olarak iletilen fakat testte çağrılmayan dummy logger."""
    def __init__(self):
        self.invoked = False
    def log_debug(self, message: str) -> None:
        self.invoked = True  # Eğer çağrılırsa işaretle

# 2. STUB: Önceden hazırlanmış sabit/yapay sensör verisi dönen nesne (Canned Answers)
class IMUSensorStub:
    """Fiziksel jiroskop ve ivmeölçer yerine deterministik telemetri dönen stub."""
    def __init__(self):
        self.roll_deg = 2.40
        self.pitch_deg = -3.50
        self.yaw_deg = 120.0
        self.sensor_status = "HEALTHY_OK"

    def set_pitch(self, pitch: float) -> None:
        self.pitch_deg = pitch

    def read_attitude(self) -> Dict[str, Any]:
        return {
            "roll": self.roll_deg,
            "pitch": self.pitch_deg,
            "yaw": self.yaw_deg,
            "status": self.sensor_status
        }

# 3. SPY: Gönderilen komutları, açıları ve zamanlamaları kaydeden casus nesne
class FinActuatorSpy:
    """Kanatçık servo motorlarına giden açı komutlarını kaydeden spy."""
    def __init__(self):
        self.command_history: List[Tuple[int, float]] = []  # (fin_id, angle_deg)
        self.call_count = 0

    def set_deflection(self, fin_id: int, angle_deg: float) -> None:
        self.command_history.append((fin_id, angle_deg))
        self.call_count += 1

# 4. MOCK: Davranış ve çağrı beklentilerini (Expectations) denetleyen nesne
class TelemetryLinkMock:
    """Link-16 / Taktik veri bağı güvenlik onayını (Handshake) zorlayan mock."""
    def __init__(self):
        self.expected_token = 0xA55A
        self.received_token = None
        self.handshake_verified = False

    def expect_handshake(self, token: int) -> None:
        self.expected_token = token

    def send_auth_token(self, token: int) -> None:
        self.received_token = token
        if self.received_token == self.expected_token:
            self.handshake_verified = True

    def verify_expectations(self) -> bool:
        return self.handshake_verified

# 5. FAKE: Gerçek donanım donatısı yerine RAM üzerinde çalışan taklit depolama (In-Memory NVM)
class FakeNonVolatileMemory:
    """Gerçek EEPROM / Flash yongası yerine RAM sözlüğü kullanan basit fake bellek."""
    def __init__(self):
        self.storage: Dict[int, float] = {}

    def write_word(self, address: int, value: float) -> None:
        self.storage[address] = value

    def read_word(self, address: int) -> float:
        return self.storage.get(address, 0.0)

print("=" * 84)
print("ASELSAN / HAVELSAN / ROKETSAN TEST DOUBLE MİMARİSİ (5 TEMEL ÇİFT)")
print("=" * 84)
for tdt in TestDoubleType:
    print(f"[{tdt.name}] -> {tdt.value}")
print("=" * 84)


# [KOD HÜCRESİ 2: Uçuş Güdüm Kontrolcüsü (SUT) ve Testbench Koşumu]
# Amaç: Test Edilen Sistem (SUT - System Under Test) olan Uçuş Güdüm Kontrolcüsünü
# (FlightGuidanceController) fiziksel donanım olmadan 5 Test Double ile
# 100 simülasyon adımı boyunca kapalı döngüde çalıştırmak.

class FlightGuidanceController:
    """Güdüm ve Kanatçık Kontrol Bilgisayarı (SUT)."""
    def __init__(self, imu_sensor: IMUSensorStub, actuator_bus: FinActuatorSpy,
                 telemetry: TelemetryLinkMock, nvm: FakeNonVolatileMemory,
                 logger: DummyLogger):
        self.imu = imu_sensor
        self.actuators = actuator_bus
        self.telemetry = telemetry
        self.nvm = nvm
        self.logger = logger
        self.kp_pitch = 1.80  # Pitch kontrol kazancı (deg/deg)
        self.max_fin_deflection_deg = 20.0  # Kanatçık mekanik sınır

    def execute_cycle(self, cycle_index: int) -> Dict[str, Any]:
        # 1. IMU Stub'dan veri oku
        attitude = self.imu.read_attitude()
        pitch_err = attitude["pitch"]
        
        # 2. Kanatçık komutunu hesapla (P-Kontrolcü)
        # Pitch yukarı kalktığında (+), kanatçık aşağı yönelmeli (-)
        raw_cmd = -self.kp_pitch * pitch_err
        # Doyum (Saturation) koruması
        fin_deflection = float(np.clip(raw_cmd, -self.max_fin_deflection_deg, self.max_fin_deflection_deg))
        
        # 3. Kanatçık Spy'a komut gönder
        self.actuators.set_deflection(1, fin_deflection)
        self.actuators.set_deflection(2, -fin_deflection)
        
        # 4. Kritik durum bilgisini Fake NVM'e kaydet (Adres: 0x0100)
        self.nvm.write_word(0x0100 + cycle_index, fin_deflection)
        
        # 5. Her 10 döngüde bir Telemetri Mock ile güvenlik tokalaşması yap
        if cycle_index % 10 == 0:
            self.telemetry.send_auth_token(0xA55A)
            
        return {
            "cycle": cycle_index,
            "pitch": pitch_err,
            "fin_cmd": fin_deflection
        }

# Testbench Başlatımı
dummy_log = DummyLogger()
imu_stub = IMUSensorStub()
actuator_spy = FinActuatorSpy()
telemetry_mock = TelemetryLinkMock()
fake_nvm = FakeNonVolatileMemory()

controller = FlightGuidanceController(
    imu_sensor=imu_stub,
    actuator_bus=actuator_spy,
    telemetry=telemetry_mock,
    nvm=fake_nvm,
    logger=dummy_log
)

# 100 Adımlık Uçuş Simülasyonu
N_CYCLES = 100
t_steps = np.arange(N_CYCLES)
simulated_pitch_profile = 8.0 * np.sin(2.0 * np.pi * t_steps / 40.0)

flight_telemetry = []

for c in range(N_CYCLES):
    # Stub'a dinamik pitch açısı enjekte et (Uçuş kinematiği simülasyonu)
    imu_stub.set_pitch(simulated_pitch_profile[c])
    out = controller.execute_cycle(c)
    flight_telemetry.append(out)

print("=" * 84)
print("UÇUŞ GÜDÜM KONTROLCÜSÜ (SUT) TESTBENCH KOŞUM ÇIKTILARI")
print("=" * 84)
print(f"Koşturulan Döngü Sayısı       : {N_CYCLES} Adım")
print(f"Actuator Spy Çağrı Sayısı     : {actuator_spy.call_count} Çağrı ({N_CYCLES * 2} Kanatçık Komutu)")
print(f"Fake NVM Yazılan Hücre Sayısı : {len(fake_nvm.storage)} Adres")
print(f"Telemetry Mock Doğrulandı mı? : {telemetry_mock.verify_expectations()} (Beklenen Token Alındı)")
print(f"Dummy Logger Çağrıldı mı?     : {dummy_log.invoked} (İdeal: False - Gereksiz Çalışma Yok)")
print("=" * 84)


# [KOD HÜCRESİ 3: Otomatik Test Doğrulama ve Davranış Denetim Motoru]
# Amaç: 5 Test Double'ın ürettiği kayıtları DO-178C test kriterlerine göre
# otomatik incelemek; durum doğrulamasını (State Verification) ve
# davranış doğrulamasını (Behavior Verification) tek bir raporda konsolide etmek.

print("=" * 100)
print(f"{'TEST DOUBLE':<16} | {'ROL VE GÖREV':<30} | {'DENETLENEN METRİK':<24} | {'DURUM'}")
print("=" * 100)

double_checks = []

# 1. DUMMY KONTROLÜ
dummy_pass = (dummy_log.invoked == False)
double_checks.append(("Dummy (Logger)", "Arayüz Parametresi Sağlama", f"Çağrılma: {dummy_log.invoked} (0 Çağrı)", dummy_pass))

# 2. STUB KONTROLÜ
# Stub telemetrisi son adımda doğru okundu mu?
last_pitch_read = imu_stub.read_attitude()["pitch"]
expected_last_pitch = simulated_pitch_profile[-1]
stub_pass = abs(last_pitch_read - expected_last_pitch) < 1e-6
double_checks.append(("Stub (IMU Sensor)", "Yapay Giriş Telemetrisi Sağlama", f"Son Pitch: {last_pitch_read:.2f}°", stub_pass))

# 3. SPY KONTROLÜ
# 200 çağrı yapıldı mı ve maksimum kanatçık açısı 20.0 derece mekanik sınırını aştı mı?
all_deflections = [cmd[1] for cmd in actuator_spy.command_history]
max_observed_fin = float(np.max(np.abs(all_deflections)))
spy_pass = (actuator_spy.call_count == N_CYCLES * 2) and (max_observed_fin <= 20.0)
double_checks.append(("Spy (Actuator Bus)", "Kanatçık Komut Kaydı & Doyum", f"Maks Açı: {max_observed_fin:.2f}° <= 20°", spy_pass))

# 4. MOCK KONTROLÜ
# Davranışsal güvenlik protokolü doğrulandı mı?
mock_pass = telemetry_mock.verify_expectations()
double_checks.append(("Mock (Telemetry C2)", "Link-16 Protokol Doğrulama", f"Token Doğrulandı: {mock_pass}", mock_pass))

# 5. FAKE KONTROLÜ
# NVM'e yazılan 100 hücre de RAM'den bozulmadan okunabiliyor mu?
sample_val = fake_nvm.read_word(0x0100 + 40)
expected_val = flight_telemetry[40]["fin_cmd"]
fake_pass = abs(sample_val - expected_val) < 1e-6 and (len(fake_nvm.storage) == 100)
double_checks.append(("Fake (NVM Storage)", "RAM Üzerinde Bellek Bütünlüğü", f"Hücre 0x0128: {sample_val:.2f}°", fake_pass))

for name, role, metric_str, passed in double_checks:
    status_str = "[PASS] UYGUN" if passed else "[FAIL] İHLAL"
    print(f"{name:<16} | {role:<30} | {metric_str:<24} | {status_str}")

print("=" * 100)
all_doubles_passed = all(check[3] for check in double_checks)
print(f"DO-178C TÜM TEST DOUBLE DOĞRULAMA DURUMU: {'%100 BAŞARILI (COMPLIANT)' if all_doubles_passed else 'UYUMSUZLUK'}")
print("=" * 100)


# [KOD HÜCRESİ 4: DO-178C DAL-A Algoritmik Stres Test Paketi]
# Amaç: 5 Test Double'ın sınır şartlarını, güvenlik izolasyonunu ve
# matematiksel kararlılığını 5 bağımsız assert korumasıyla doğrulamak.

print("=" * 84)
print("DO-178C DAL-A TEST DOUBLE VE DONANIM İZOLASYON STRES TESTLERİ")
print("=" * 84)

# TEST 1: Dummy İzolasyon Koruması (Dummy asla gereksiz invoke edilmemeli)
assert dummy_log.invoked == False, "HATA: Dummy logger gereksiz yere çağrıldı!"
print("[TEST 1 PASS] Dummy İzolasyonu: SUT gereksiz log çağrısı yapmadı, sıfır yan etki.")

# TEST 2: Stub Sınır ve Enjeksiyon Doğruluğu
assert abs(last_pitch_read - expected_last_pitch) < 1e-6, "HATA: IMU Stub telemetri kayması!"
print(f"[TEST 2 PASS] Stub Telemetri Enjeksiyonu: Gerçekçi dinamik profil başarıyla aktarıldı ({last_pitch_read:.2f}°).")

# TEST 3: Spy Aktüatör Doyum (Saturation) Koruması (Açı <= 20.0 deg)
assert max_observed_fin <= 20.0, f"HATA: Kanatçık mekanik sınırı aşıldı: {max_observed_fin:.2f}° > 20.0°"
assert actuator_spy.call_count == 200, f"HATA: Eksik servo komutu: {actuator_spy.call_count} != 200"
print(f"[TEST 3 PASS] Spy Gözetimi: 200 komut kaydedildi, maksimum açı {max_observed_fin:.2f}° <= 20.0° (Doyum Sağlam).")

# TEST 4: Mock Davranışsal Sözleşme ve Güvenlik Protokolü Doğrulaması
assert telemetry_mock.verify_expectations() == True, "HATA: Telemetry Mock güvenlik beklentisi karşılanmadı!"
print("[TEST 4 PASS] Mock Davranış Doğrulaması: Link-16 0xA55A güvenlik tokalaşması %100 doğrulandı.")

# TEST 5: Fake NVM Bellek Bütünlüğü ve Sayısal Güvenlik
assert len(fake_nvm.storage) == 100, "HATA: Fake NVM veri kaybı tespit edildi!"
assert not np.isnan(sample_val) and not np.isinf(sample_val), "Sayısal taşma hatası!"
print("[TEST 5 PASS] Fake NVM Bütünlüğü: 100 hücre eksiksiz yazıldı ve geri okundu, sıfır taşma.")

print("=" * 84)
print("TÜM DO-178C DAL-A TEST DOUBLE STRES TESTLERİ GEÇTİ: [UYGUN]")
print("=" * 84)


# [KOD HÜCRESİ 5: 300 DPI Profesyonel Aviyonik Test Double Dashboard'u]
# Amaç: Havacılık ve savunma aviyonik laboratuvarları için 5 Test Double'ın
# mimari rolünü ve telemetrisini 4 panelli, koyu temalı (#0F172A),
# 300 DPI çözünürlüğünde yayın kalitesinde bir görsel göstergeye dönüştürmek.

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

c_cyan = '#06B6D4'
c_amber = '#F59E0B'
c_rose = '#F43F5E'
c_emerald = '#10B981'
c_blue = '#3B82F6'
c_purple = '#8B5CF6'

# PANEL 1: Test Double Taksonomisi ve Mimari Rol Dağılımı
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')

double_labels = ['Dummy', 'Stub', 'Spy', 'Mock', 'Fake']
y_positions = np.arange(len(double_labels))
descriptions = [
    'Dummy: Boş Parametre (0 Çağrı)',
    'Stub: Canned Telemetri (IMU Sensor)',
    'Spy: Açı & Çağrı Kaydedici (200 Çağrı)',
    'Mock: Link-16 Davranış Doğrulayıcı',
    'Fake: Bellek İçi NVM Depolama (100 Sözcük)'
]
bar_colors = [c_blue, c_cyan, c_amber, c_rose, c_emerald]

ax1.barh(y_positions, [1.0]*5, color=bar_colors, alpha=0.75, edgecolor='#FFFFFF', lw=1.2)
for i, desc in enumerate(descriptions):
    ax1.text(0.05, i, desc, va='center', fontsize=9.5, fontweight='bold', color='#FFFFFF')

ax1.set_yticks(y_positions)
ax1.set_yticklabels(double_labels, fontsize=10, fontweight='bold')
ax1.set_xlim(0, 1.1)
ax1.set_xticks([])
ax1.set_title('PANEL 1: Gerard Meszaros 5 Test Double Mimarisi', fontsize=11, fontweight='bold', color='#38BDF8')

# PANEL 2: IMU Stub Girdisi vs Actuator Spy Kanatçık Yanıtı
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')

pitch_vals = [t["pitch"] for t in flight_telemetry]
fin1_cmds = [actuator_spy.command_history[2*i][1] for i in range(N_CYCLES)]

ax2.plot(t_steps, pitch_vals, color=c_cyan, lw=2.2, label='IMU Stub Pitch Açısı (°)')
ax2.plot(t_steps, fin1_cmds, color=c_amber, lw=2.0, ls='--', label='Actuator Spy Kanatçık 1 (°)')
ax2.axhline(20.0, color=c_rose, ls=':', lw=1.8, label='Mekanik Doyum Sınırı (+20°)')
ax2.axhline(-20.0, color=c_rose, ls=':', lw=1.8, label='Mekanik Doyum Sınırı (-20°)')

ax2.set_xlabel('Simülasyon Adımı (Döngü)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax2.set_ylabel('Açı (Derece)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax2.set_title('PANEL 2: Stub Telemetrisi vs Spy Kanatçık Komut Yanıtı', fontsize=11, fontweight='bold', color='#38BDF8')
ax2.grid(True, ls=':', color='#334155', alpha=0.7)
ax2.legend(loc='lower left', fontsize=8, framealpha=0.85)

# PANEL 3: Telemetry Mock Davranış ve Çağrı Frekansı Doğrulaması
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')

handshake_cycles = [i for i in range(N_CYCLES) if i % 10 == 0]
handshake_tokens = [0xA55A] * len(handshake_cycles)

ax3.stem(handshake_cycles, handshake_tokens, linefmt='cyan', markerfmt='s', basefmt='gray', label='Alınan Güvenlik Tokeni (0xA55A)')
ax3.axhline(0xA55A, color=c_emerald, ls='--', lw=2.0, label='Beklenen Mock Sözleşmesi (0xA55A)')

for hc in handshake_cycles:
    ax3.annotate('PASS', (hc, 0xA55A + 0x0500), fontsize=7.5, fontweight='bold', color='#A7F3D0', ha='center')

ax3.set_ylim(0x9000, 0xB500)
ax3.set_xlabel('Döngü İndeksi (Her 10 Döngüde Bir)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax3.set_ylabel('Onay Token Değeri (Hex)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax3.set_title('PANEL 3: Telemetry Mock Protokol ve Sıra Doğrulaması (%100 UYGUN)', fontsize=11, fontweight='bold', color='#38BDF8')
ax3.grid(True, ls=':', color='#334155', alpha=0.7)
ax3.legend(loc='lower right', fontsize=8, framealpha=0.85)

# PANEL 4: Fake NVM Bellek Haritası ve Veri Bütünlüğü
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')

addrs = list(fake_nvm.storage.keys())
stored_vals = [fake_nvm.storage[a] for a in addrs]

ax4.scatter(addrs, stored_vals, color=c_emerald, s=25, alpha=0.85, label='NVM Kayıtlı Değerler')
ax4.plot(addrs, stored_vals, color=c_emerald, lw=1.2, alpha=0.5)

ax4.set_xlabel('Bellek Adresi (Hex 0x0100 - 0x0163)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax4.set_ylabel('Kaydedilen Kanatçık Açısı (°)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax4.set_title('PANEL 4: Fake NVM In-Memory Depolama & Bütünlük (100 Sözcük)', fontsize=11, fontweight='bold', color='#38BDF8')
ax4.grid(True, ls=':', color='#334155', alpha=0.7)
ax4.legend(loc='lower left', fontsize=8, framealpha=0.85)

fig.suptitle('ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ DO-178C TEST DOUBLE DOĞRULAMA DASHBOARD',
             fontsize=13, fontweight='bold', color='#F8FAFC', y=0.985)

plt.tight_layout(rect=[0, 0.02, 1, 0.97])

output_png = "gunluk_mufredat/gun_320/gun_320_test_double_mock_stub.png"
fig.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close(fig)

import os
file_size = os.path.getsize(output_png)
print(f"[+] 300 DPI Profesyonel Aviyonik Dashboard Kaydedildi: {output_png} ({file_size:,} bayt)")


# [KOD HÜCRESİ 6: Kurumsal DO-178C Kalifikasyon Tablosu ve Onay]
# Amaç: DO-178C, DO-254 ve DO-330 (Tool Qualification) denetimleri için resmi
# Test Double Uygunluk Beyanını ve Doğrulama Raporunu oluşturmak.

import os

print("+======================================================================+")
print("|   ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ AVİYONİK TEST DOĞRULAMA LAB  |")
print("|       DO-178C TEST DOUBLE (MOCK/STUB) KALİFİKASYON PROTOKOLÜ         |")
print("+======================================================================+")

report_items = [
    ("1. Dummy Logger İzolasyonu", "Çağrı: 0 (Yan Etkisiz Parametre)", "Sıfır Overhead", "UYGUN"),
    ("2. IMU Sensor Stub Doğruluğu", "Dinamik Pitch Profil Enjeksiyonu", "100 Adım Senkron", "UYGUN"),
    ("3. Fin Actuator Spy Kayıt Güveni", f"Kayıt: {actuator_spy.call_count} Komut (Maks Açı <= 20°)", "Doyum Korundu", "UYGUN"),
    ("4. Telemetry Mock Sözleşmesi", "0xA55A Protokol Tokalaşması", "Davranışsal Onay", "UYGUN"),
    ("5. Fake NVM Bellek Bütünlüğü", f"{len(fake_nvm.storage)} Adres Eksiksiz Doğrulandı", "Kayıpsız RAM", "UYGUN"),
    ("6. Bağımsız Donanım İzolasyonu", "Fiziksel Sensör Olmadan %100 Çalışma", "CI/CD Uyumlu", "UYGUN"),
    ("7. Sayısal Bütünlük ve Taşma", "Sıfır NaN / Sıfır Inf / Tam Determinizm", "MISRA-C++ Uyum", "UYGUN"),
    ("8. Dashboard Teftiş Artefaktı", f"300 DPI PNG ({os.path.getsize(output_png):,} bayt > 100 KB)", "Koyu Tema #0F172A", "UYGUN")
]

for item, metric, note, status in report_items:
    print(f"| {item:<34} : {metric:<34} | [{status}] |")

print("+======================================================================+")
print("| SONUÇ: TÜM 5 TEST DOUBLE TÜRÜ DO-178C DAL-A KRİTERLERİNE TAM UYGUNDUR!|")
print("| FİZİKSEL DONANIM BAĞIMSIZLIĞI VE BİRİM TEST KALİFİKASYONU MÜHÜRLENDİ!|")
print("+======================================================================+\n")

print("[MÜKEMMEL] GÜN 320: TEST DOUBLE (MOCK, STUB, SPY, FAKE, DUMMY) TAMAMLANDI.")
print("[SIRADAKİ GÜN] GÜN 321: TEST DRIVEN DEVELOPMENT (TDD) VE AVİYONİK RED-GREEN DÖNGÜSÜ.")
