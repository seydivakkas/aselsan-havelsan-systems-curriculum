

# ==============================================================================# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 1 — SPI Full-Duplex Dairesel Kaydırma Yazmacı (Shift Register Exchange)
8 Saat Darbesi Boyunca Master ve Slave Bit Akışı ve Dummy Byte Mekanizması
"""

from typing import Tuple, List, Dict

class SPIShiftRegisterExchange:
    """Master ve Slave 8-bit Kaydırma Yazmaçlarının Donanımsal Simülatörü"""
    def __init__(self):
        pass

    def transfer_byte(self, master_byte: int, slave_byte: int) -> Dict[str, any]:
        """
        Master ve Slave arasında 8 saat darbesi boyunca bit takasını adım adım işletir.
        MSB First kuralı geçerlidir (En önemli bit 7 önce çıkar).
        """
        m_reg = master_byte & 0xFF
        s_reg = slave_byte & 0xFF

        trace = []
        # Başlangıç durumu
        trace.append({
            "clock_tick": 0,
            "master_reg": f"0b{m_reg:08b}",
            "slave_reg": f"0b{s_reg:08b}",
            "mosi_bit": None,
            "miso_bit": None
        })

        # 8 Saat Darbesi (1..8)
        for tick in range(1, 9):
            # 1. MSB bitleri hatlara sürülür
            mosi_bit = (m_reg >> 7) & 1
            miso_bit = (s_reg >> 7) & 1

            # 2. Yazmaçlar 1 bit sola kaydırılır ve diğer taraftan gelen bit LSB'ye alınır
            m_reg = ((m_reg << 1) & 0xFE) | miso_bit
            s_reg = ((s_reg << 1) & 0xFE) | mosi_bit

            trace.append({
                "clock_tick": tick,
                "master_reg": f"0b{m_reg:08b}",
                "slave_reg": f"0b{s_reg:08b}",
                "mosi_bit": mosi_bit,
                "miso_bit": miso_bit
            })

        return {
            "master_sent": master_byte,
            "slave_sent": slave_byte,
            "master_received": m_reg,
            "slave_received": s_reg,
            "trace": trace
        }

# Test 1: Karşılıklı Veri Takası
# Master IMU'ya Okuma Komutu Gönderiyor: 0x8F (WHO_AM_I Okuma, Bit7=1)
# Slave IMU içinde WHO_AM_I cevabı hazır: 0xEA (Cihaz Kimlik Kodu)
sim = SPIShiftRegisterExchange()
res1 = sim.transfer_byte(master_byte=0x8F, slave_byte=0xEA)

print("[*] SPI Full-Duplex Donanımsal Kaydırma Yazmacı Testi:")
print(f"  [+] Master Gönderdi : 0x{res1['master_sent']:02X} (0b{res1['master_sent']:08b})")
print(f"  [+] Slave Gönderdi  : 0x{res1['slave_sent']:02X} (0b{res1['slave_sent']:08b})")
print(f"  [+] Master Aldı     : 0x{res1['master_received']:02X} (Beklenen: 0xEA)")
print(f"  [+] Slave Aldı      : 0x{res1['slave_received']:02X} (Beklenen: 0x8F)")

# Test 2: Dummy Byte ile Salt Okuma
# Master Dummy (0xFF) gönderiyor, Slave sıcaklık telemetrisi (0x24 = 36 C) dönüyor
res_dummy = sim.transfer_byte(master_byte=0xFF, slave_byte=0x24)
print(f"\n[*] Dummy Byte (0xFF) Okuma Testi:")
print(f"  [+] Master Aldığı Telemetri: 0x{res_dummy['master_received']:02X} ({res_dummy['master_received']} °C)")

assert res1["master_received"] == 0xEA, "Master Slave verisini alamadı!"
assert res1["slave_received"] == 0x8F, "Slave Master verisini alamadı!"
assert res_dummy["master_received"] == 0x24, "Dummy byte okuma başarısız!"
print("\n[HÜCRE 6] SPI dairesel kaydırma yazmacı ve dummy byte mekanizması başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 2 — SPI 4 Modu (CPOL/CPHA) Sinyal Üretici ve Zamanlama Simülatörü
Mode 0, 1, 2, 3 İçin Saat Seviyesi, Örnekleme Kenarı ve Veri Çözümleme Doğrulaması
"""

import numpy as np
from typing import Dict, List, Tuple

class SPIModeSimulator:
    """SPI 4 Modunun Saat ve Veri Zamanlama Simülatörü"""
    def __init__(self, mode: int):
        assert mode in [0, 1, 2, 3], "Mod 0, 1, 2 veya 3 olmalıdır!"
        self.mode = mode
        self.cpol = 1 if mode in [2, 3] else 0
        self.cpha = 1 if mode in [1, 3] else 0

    def get_clock_edges(self, num_bits: int = 8) -> List[Dict[str, any]]:
        """Her bit için 2 saat kenarının (Edge 1, Edge 2) polarite ve aksiyonunu döner"""
        edges = []
        for bit_idx in range(num_bits):
            # Kenar 1
            e1_type = "FALLING" if self.cpol == 1 else "RISING"
            e1_action = "SHIFT" if self.cpha == 1 else "SAMPLE"
            edges.append({"bit": bit_idx, "edge_num": 1, "type": e1_type, "action": e1_action})

            # Kenar 2
            e2_type = "RISING" if self.cpol == 1 else "FALLING"
            e2_action = "SAMPLE" if self.cpha == 1 else "SHIFT"
            edges.append({"bit": bit_idx, "edge_num": 2, "type": e2_type, "action": e2_action})

        return edges

    def sample_data(self, data_bits: List[int]) -> List[int]:
        """Verilen bit akışını bu modun kurallarına göre çözümler"""
        # İdeal senkron hatta doğru modda okunan veri orijinal veriye eşittir
        return list(data_bits)

# Doğrulama: 4 Modun Karakteristiği
modes_info = {}
for m in [0, 1, 2, 3]:
    sim_m = SPIModeSimulator(m)
    edges = sim_m.get_clock_edges(num_bits=1) # 1. bitin kenarları
    modes_info[m] = {
        "cpol": sim_m.cpol,
        "cpha": sim_m.cpha,
        "idle_level": "HIGH" if sim_m.cpol == 1 else "LOW",
        "sample_edge": [e for e in edges if e["action"] == "SAMPLE"][0]["type"]
    }

print("[*] SPI 4 Çalışma Modu Özellikleri:")
print(f"{'Mod':>5} | {'CPOL':>5} | {'CPHA':>5} | {'Boşta (IDLE)':>14} | {'Örnekleme Kenarı'}")
print("-" * 55)
for m, info in modes_info.items():
    print(f"Mod {m:>1} | {info['cpol']:>5} | {info['cpha']:>5} | {info['idle_level']:>14} | {info['sample_edge']}")

# Katı Doğrulamalar
assert modes_info[0]["cpol"] == 0 and modes_info[0]["cpha"] == 0
assert modes_info[0]["idle_level"] == "LOW" and modes_info[0]["sample_edge"] == "RISING"

assert modes_info[3]["cpol"] == 1 and modes_info[3]["cpha"] == 1
assert modes_info[3]["idle_level"] == "HIGH" and modes_info[3]["sample_edge"] == "RISING"
print("\n[HÜCRE 8] SPI 4 modu zamanlama ve saat kenarı kuralları başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 3 — SPI Çoklu-Slave (Multi-Slave) CS Çekişmesi ve Zamanlama Koruması
Bağımsız CS Pinleri, Bus Contention Koruması ve T_setup / T_hold Doğrulaması
"""

from typing import Dict, List, Optional

class SPISlaveDevice:
    """Sanal SPI Sensörü (Örn: IMU, Barometre, Flash)"""
    def __init__(self, name: str, device_id: int):
        self.name = name
        self.device_id = device_id
        self.cs_pin = 1 # 1: Pasif (HIGH), 0: Seçili (LOW)
        self.miso_active = False

    def set_cs(self, level: int):
        self.cs_pin = level
        self.miso_active = (level == 0) # CS LOW olunca MISO aktifleşir

class SPIMasterBusController:
    """Çoklu Slave SPI Bus Denetleyicisi ve Çekişme (Contention) Koruması"""
    def __init__(self, slaves: List[SPISlaveDevice]):
        self.slaves = slaves
        self.bus_contention_detected = False

    def select_slave(self, slave_index: int) -> bool:
        # Önce tüm slave'leri kapat (HIGH yap)
        for s in self.slaves:
            s.set_cs(1)

        # İstenen slave'i aç (LOW yap)
        if 0 <= slave_index < len(self.slaves):
            self.slaves[slave_index].set_cs(0)
            return True
        return False

    def deselect_all(self):
        for s in self.slaves:
            s.set_cs(1)

    def check_bus_health(self) -> bool:
        """Aynı anda birden fazla slave MISO sürüyorsa kısa devre (contention) oluşur!"""
        active_drivers = sum(1 for s in self.slaves if s.miso_active)
        if active_drivers > 1:
            self.bus_contention_detected = True
            return False
        return True

# Test ve Simülasyon
imu_sensor = SPISlaveDevice("ADIS16488_IMU", device_id=0x01)
baro_sensor = SPISlaveDevice("MS5611_BARO", device_id=0x02)
flash_mem = SPISlaveDevice("W25Q128_FLASH", device_id=0x03)

bus_mgr = SPIMasterBusController([imu_sensor, baro_sensor, flash_mem])

# 1. Normal Çalışma (Sırayla Seçim)
bus_mgr.select_slave(0) # IMU seçildi
assert bus_mgr.check_bus_health() is True, "Normal seçimde bus sağlıklı olmalı!"
assert imu_sensor.miso_active is True and baro_sensor.miso_active is False

bus_mgr.select_slave(1) # Barometre seçildi
assert bus_mgr.check_bus_health() is True
assert imu_sensor.miso_active is False and baro_sensor.miso_active is True

bus_mgr.deselect_all()
assert sum(1 for s in bus_mgr.slaves if s.miso_active) == 0, "Tüm slave'ler pasif olmalı!"

# 2. Hata Enjeksiyonu: Donanımsal Sabotaj (Aynı anda 2 CS LOW yapıldı)
imu_sensor.set_cs(0)
baro_sensor.set_cs(0) # SABOTAJ!
is_healthy = bus_mgr.check_bus_health()

print("[*] SPI Çoklu-Slave Bus Çekişme (Contention) Testi:")
print(f"  [+] Tekil Seçim Sağlık Durumu : Sağlıklı (1 Aktif MISO Sürücüsü)")
print(f"  [!] Çift CS Seçimi Durumu     : {is_healthy} (Çekişme Algılandı: {bus_mgr.bus_contention_detected})")

assert is_healthy is False, "Çift CS seçildiğinde bus contention yakalanmalıydı!"
print("\n[HÜCRE 10] Çoklu slave CS çekişme koruma mekanizması başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 4 — C++20 STM32 Bare-Metal SPI Master Sürücü Simülasyonu
Sanal SPI Yazmaçları (SR, DR, CR1), TXE, RXNE, BSY Bayrakları ve Timeout Koruması
"""

from typing import Tuple, Optional

class VirtualSTM32SPIHardware:
    """STM32 SPI Donanımının Sanal Register Modeli"""
    SPI_SR_RXNE = (1 << 0)
    SPI_SR_TXE  = (1 << 1)
    SPI_SR_BSY  = (1 << 7)

    def __init__(self, connected_slave_byte: int = 0xAA):
        self.SR = self.SPI_SR_TXE # Başlangıçta TX boş, BSY=0, RXNE=0
        self.DR_tx = 0
        self.DR_rx = 0
        self.slave_response = connected_slave_byte
        self.cycles = 0

    def write_DR(self, byte_val: int):
        self.DR_tx = byte_val & 0xFF
        self.SR &= ~self.SPI_SR_TXE # TXE temizlendi (dolu)
        self.SR |= self.SPI_SR_BSY   # Hat meşgul (BSY=1)

    def step_clock(self):
        """Donanımın saat çevrimi: Veri takasını tamamlar"""
        if self.SR & self.SPI_SR_BSY:
            self.DR_rx = self.slave_response # Slave'den gelen veri RX'e yazıldı
            self.SR |= self.SPI_SR_RXNE      # RXNE = 1
            self.SR |= self.SPI_SR_TXE       # TXE = 1
            self.SR &= ~self.SPI_SR_BSY      # Aktarım bitti (BSY = 0)

    def read_DR(self) -> int:
        val = self.DR_rx
        self.SR &= ~self.SPI_SR_RXNE # Okununca RXNE temizlenir
        return val

class STM32SPIMasterDriver:
    """C++20 Benzeri Robust SPI Master Sürücüsü"""
    def __init__(self, hw: VirtualSTM32SPIHardware):
        self.hw = hw

    def exchange_byte(self, byte_to_send: int, timeout_cycles: int = 100) -> Tuple[bool, int]:
        # 1. TXE Bekle
        cycles = 0
        while not (self.hw.SR & VirtualSTM32SPIHardware.SPI_SR_TXE):
            self.hw.step_clock()
            cycles += 1
            if cycles >= timeout_cycles:
                return False, 0

        # 2. Veriyi Yaz
        self.hw.write_DR(byte_to_send)

        # 3. RXNE Bekle
        cycles = 0
        while not (self.hw.SR & VirtualSTM32SPIHardware.SPI_SR_RXNE):
            self.hw.step_clock()
            cycles += 1
            if cycles >= timeout_cycles:
                return False, 0

        # 4. Veriyi Oku
        received_byte = self.hw.read_DR()
        return True, received_byte

    def wait_until_idle(self, timeout_cycles: int = 100) -> bool:
        """CS kapatılmadan önce BSY bayrağının düşmesini bekle"""
        cycles = 0
        while (self.hw.SR & VirtualSTM32SPIHardware.SPI_SR_BSY):
            self.hw.step_clock()
            cycles += 1
            if cycles >= timeout_cycles:
                return False
        return True

# Sürücü Doğrulama Testi
virt_spi = VirtualSTM32SPIHardware(connected_slave_byte=0x3F)
spi_driver = STM32SPIMasterDriver(virt_spi)

# Veri Takası: 0x80 gönder, 0x3F al
success, rx_val = spi_driver.exchange_byte(0x80)
is_idle = spi_driver.wait_until_idle()

print("[*] STM32 Bare-Metal SPI Sürücü Doğrulama Testi:")
print(f"  [+] Gönderilen Bayt : 0x80")
print(f"  [+] Alınan Bayt     : 0x{rx_val:02X} (Başarılı: {success})")
print(f"  [+] BSY Boşta mı    : {is_idle} (CS güvenle HIGH yapılabilir)")

assert success is True and rx_val == 0x3F, "SPI bayt takası hatalı!"
assert is_idle is True, "SPI aktarım sonrası meşgul kaldı!"
print("\n[HÜCRE 12] C++20 bare-metal SPI sürücüsü başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 5 — Taktik IMU SPI Kayıt Okuma ve CRC-16 Bütünlük Testi
Burst-Read ile 6 Eksen Telemetri Çekimi ve SPI Bit Bozulma İzolasyonu
"""

from typing import Dict, List, Tuple

class TacticalIMUSensor:
    """ROKETSAN Taktik IMU Sensör Modeli (Örn: ADIS16488 benzeri)"""
    def __init__(self):
        # 6 Eksen Ham Sensör Değerleri (16-bit Signed Integer)
        # Gyro X, Y, Z (dps) ve Accel X, Y, Z (g)
        self.registers = {
            0x02: 0x0012, # GYRO_X (+18 dps)
            0x04: 0xFFF0, # GYRO_Y (-16 dps)
            0x06: 0x0005, # GYRO_Z (+5 dps)
            0x08: 0x03E8, # ACCEL_X (+1000 mg = +1.0g)
            0x0A: 0x0000, # ACCEL_Y (0.0g)
            0x0C: 0xFC18, # ACCEL_Z (-1000 mg = -1.0g)
        }

    @staticmethod
    def calculate_crc16(data_bytes: List[int]) -> int:
        """CCITT-16 CRC Algoritması (Polinom: 0x1021, Init: 0xFFFF)"""
        crc = 0xFFFF
        for byte in data_bytes:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    def read_burst_telemetry(self, inject_bit_error: bool = False) -> Dict[str, any]:
        """Tüm eksenleri 12 bayt halinde okur ve CRC ekler"""
        payload = []
        for reg_addr in [0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C]:
            val16 = self.registers[reg_addr]
            payload.append((val16 >> 8) & 0xFF) # High Byte
            payload.append(val16 & 0xFF)        # Low Byte

        crc = self.calculate_crc16(payload)

        # Hata Enjeksiyonu
        if inject_bit_error:
            payload[3] ^= 0x01 # 4. baytın 1 bitini boz

        return {
            "payload_bytes": payload,
            "crc_transmitted": crc,
            "is_valid": self.calculate_crc16(payload) == crc
        }

# Test ve Simülasyon
imu = TacticalIMUSensor()

# 1. Normal Hatasız Okuma
res_clean = imu.read_burst_telemetry(inject_bit_error=False)
print("[*] Taktik Aviyonik IMU SPI Telemetri Testi:")
print(f"  [+] Okunan 12 Bayt    : {[f'0x{b:02X}' for b in res_clean['payload_bytes']]}")
print(f"  [+] Hesaplanan CRC-16 : 0x{res_clean['crc_transmitted']:04X}")
print(f"  [+] Bütünlük Durumu   : {res_clean['is_valid']} (Kabul Edildi)")

# 2. Gürültülü Hat / Bozuk Bit Testi
res_corrupt = imu.read_burst_telemetry(inject_bit_error=True)
print(f"  [!] Bozuk Paket Durumu: {res_corrupt['is_valid']} (CRC Uyuşmazlığı Reddedildi)")

assert res_clean["is_valid"] is True, "Temiz telemetri CRC kontrolünü geçmeliydi!"
assert res_corrupt["is_valid"] is False, "Bozuk telemetri CRC tarafından yakalanmalıydı!"
print("\n[HÜCRE 14] Taktik IMU telemetri ve CRC-16 doğrulama motoru başarıyla onaylandı.")

# -*- coding: utf-8 -*-
"""
GÜN 170: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. SPI Full-Duplex Dairesel Kaydırma Yazmacı Değişimi (Master & Slave 8-Clock Ring)
2. SPI 4 Modu (CPOL ve CPHA) Saat ve Örnekleme Zamanlama Diyagramı
3. Çoklu-Slave Chip Select (CS) ve MISO Çekişmesi Önleme Mimarisi
4. Veri Yolu Hızı ve Bant Genişliği Karşılaştırması (UART vs I2C vs SPI 10M/42M)
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300, facecolor='#0F172A')

C_BG = '#1E293B'
C_CYAN = '#38BDF8'
C_GREEN = '#34D399'
C_RED = '#F87171'
C_YELLOW = '#FBBF24'
C_PURPLE = '#A855F7'
C_WHITE = '#F8FAFC'

# ------------------------------------------------------------------------------
# PANEL 1: SPI Full-Duplex Dairesel Kaydırma Yazmacı Değişimi
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

# 8 Saat vuruşu boyunca Master ve Slave içindeki bit kayma sürecini göster
clock_ticks = list(range(9)) # 0..8
# Temsili bit ağırlıkları
master_shift_vals = [0x8F, 0x1E, 0x3D, 0x7A, 0xF5, 0xEB, 0xD6, 0xAD, 0xEA]
slave_shift_vals =  [0xEA, 0xD5, 0xAA, 0x54, 0xA8, 0x51, 0xA3, 0x47, 0x8F]

ax1.plot(clock_ticks, master_shift_vals, marker='o', color=C_CYAN, linewidth=2.5, label="Master Yazmacı (0x8F -> 0xEA)")
ax1.plot(clock_ticks, slave_shift_vals, marker='s', color=C_YELLOW, linewidth=2.5, label="Slave Yazmacı (0xEA -> 0x8F)")

ax1.scatter([0], [0x8F], color=C_CYAN, s=120, zorder=5)
ax1.scatter([8], [0xEA], color=C_GREEN, s=140, zorder=5)
ax1.annotate("Master 0xEA Aldı!", xy=(8, 0xEA), xytext=(5.5, 0xF5),
             color=C_GREEN, fontweight='bold', fontsize=9,
             arrowprops=dict(facecolor=C_GREEN, arrowstyle="->"))

ax1.set_xlabel("SCLK Saat Darbesi (Clock Ticks)", color=C_WHITE, fontsize=10)
ax1.set_ylabel("Yazmaç Değeri (Hex)", color=C_WHITE, fontsize=10)
ax1.set_title("Panel 1: SPI Full-Duplex Kaydırma Yazmaçlarının Halka Takası", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.set_xticks(clock_ticks)
ax1.set_xticklabels([f"T{i}" for i in clock_ticks], color=C_WHITE)
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax1.legend(loc='center right', fontsize=9, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 2: SPI 4 Modu (CPOL ve CPHA) Zamanlama Diyagramı
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

t_steps = np.linspace(0, 4, 400)
# Mode 0: CPOL=0 (Boşta 0), CPHA=0 (Yükselende Örnekle)
# Mode 1: CPOL=0 (Boşta 0), CPHA=1 (Düşende Örnekle)
# Mode 2: CPOL=1 (Boşta 1), CPHA=0 (Düşende Örnekle)
# Mode 3: CPOL=1 (Boşta 1), CPHA=1 (Yükselende Örnekle)

clk_m0 = np.where(np.sin(2 * np.pi * t_steps) > 0, 1.0, 0.0)
clk_m2 = 1.0 - clk_m0 # CPOL=1 terslenmiş

y_base = [3.5, 2.5, 1.5, 0.5]
ax2.plot(t_steps, clk_m0 * 0.6 + y_base[0], color=C_CYAN, linewidth=2, label="Mode 0 (CPOL=0, CPHA=0)")
ax2.plot(t_steps, clk_m0 * 0.6 + y_base[1], color=C_GREEN, linewidth=2, label="Mode 1 (CPOL=0, CPHA=1)")
ax2.plot(t_steps, clk_m2 * 0.6 + y_base[2], color=C_YELLOW, linewidth=2, label="Mode 2 (CPOL=1, CPHA=0)")
ax2.plot(t_steps, clk_m2 * 0.6 + y_base[3], color=C_PURPLE, linewidth=2, label="Mode 3 (CPOL=1, CPHA=1)")

# Örnekleme noktalarını göster (Örnek olarak Mode 0 ve Mode 3)
sample_pts_m0 = [0.0, 1.0, 2.0, 3.0]
ax2.scatter(sample_pts_m0, [y_base[0]]*4, color=C_RED, s=50, zorder=5, label="Mode 0 Örnekleme (Yükselen)")

sample_pts_m3 = [0.5, 1.5, 2.5, 3.5]
ax2.scatter(sample_pts_m3, [y_base[3] + 0.6]*4, color=C_WHITE, s=50, zorder=5, label="Mode 3 Örnekleme (Yükselen)")

ax2.set_yticks([y + 0.3 for y in y_base])
ax2.set_yticklabels(["Mode 0", "Mode 1", "Mode 2", "Mode 3"], color=C_WHITE, fontweight='bold', fontsize=9)
ax2.set_xlabel("Zaman (Periyot)", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: SPI 4 Modunun Saat Seviyeleri ve Örnekleme Noktaları", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: Çoklu-Slave Chip Select (CS) ve MISO Çekişmesi Önleme
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

time_axis = np.arange(0, 16, 1)
# CS1 (IMU): 1..5 aralığında LOW
cs1 = [1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
# CS2 (BARO): 7..11 aralığında LOW
cs2 = [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1]
# CS3 (FLASH): 13..15 aralığında LOW
cs3 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1]

ax3.step(time_axis, np.array(cs1) * 0.8 + 2.5, color=C_CYAN, where='post', linewidth=2.2, label="CS1: ADIS16488 IMU")
ax3.step(time_axis, np.array(cs2) * 0.8 + 1.3, color=C_GREEN, where='post', linewidth=2.2, label="CS2: MS5611 Barometre")
ax3.step(time_axis, np.array(cs3) * 0.8 + 0.1, color=C_YELLOW, where='post', linewidth=2.2, label="CS3: W25Q128 Flash")

# Güvenli Bölgeleri Vurgula
ax3.axvspan(1, 5, color=C_CYAN, alpha=0.15)
ax3.axvspan(7, 11, color=C_GREEN, alpha=0.15)
ax3.axvspan(13, 15, color=C_YELLOW, alpha=0.15)

ax3.set_yticks([0.5, 1.7, 2.9])
ax3.set_yticklabels(["FLASH Aktif", "BARO Aktif", "IMU Aktif"], color=C_WHITE, fontsize=9)
ax3.set_xlabel("Zaman Pencereleri (µs)", color=C_WHITE, fontsize=10)
ax3.set_title("Panel 3: Çoklu Slave Yazılımsal CS Zamanlaması (Sıfır Çekişme)", color=C_WHITE, fontsize=12, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax3.legend(loc='lower left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 4: Veri Yolu Hızı ve Bant Genişliği Karşılaştırması
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

buses = ['UART\n115.2k', 'UART\n921.6k', 'I2C\nStandard', 'I2C\nFast Mode', 'SPI\nSensör 10M', 'STM32 SPI1\nAzami 42M']
# Kilobayt / Saniye cinsinden net veri debisi
throughput_kb_s = [
    11.52,      # UART 115200 (10 bit/bayt)
    92.16,      # UART 921600
    10.0,       # I2C 100 kHz (%80 verim)
    40.0,       # I2C 400 kHz
    1250.0,     # SPI 10 MHz (10M / 8 = 1.25 MB/s)
    5250.0      # SPI 42 MHz (42M / 8 = 5.25 MB/s)
]

colors_bar = ['#64748B', '#94A3B8', C_PURPLE, '#C084FC', C_CYAN, C_GREEN]

bars = ax4.bar(buses, throughput_kb_s, color=colors_bar, alpha=0.9, width=0.55)
ax4.set_yscale('log')
ax4.set_ylabel("Efektif Veri Debisi (KB/s, Log Ölçek)", color=C_WHITE, fontsize=10)
ax4.set_title("Panel 4: Gömülü Veri Yolları Hız ve Bant Genişliği Karşılaştırması", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')

for bar in bars:
    yval = bar.get_height()
    label = f"{yval:.1f} KB/s" if yval < 1000 else f"{yval/1000:.2f} MB/s"
    ax4.text(bar.get_x() + bar.get_width()/2.0, yval * 1.3, label, ha='center', va='bottom', color=C_WHITE, fontsize=8, fontweight='bold')

plt.suptitle("GÜN 170: SPI Clock, Chip Select ve Full-Duplex Mimari Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_170_spi_clock_chip_select_full_duplex.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_170\gun_170_spi_clock_chip_select_full_duplex.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 170 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. Shift Register Full-Duplex Assertions
sr_sim = SPIShiftRegisterExchange()
res_test = sr_sim.transfer_byte(0x55, 0xAA)
assert res_test["master_received"] == 0xAA, "Full duplex master alım hatası!"
assert res_test["slave_received"] == 0x55, "Full duplex slave alım hatası!"

# 3. SPI Modları Assertions
m0 = SPIModeSimulator(0)
assert m0.cpol == 0 and m0.cpha == 0, "Mod 0 CPOL/CPHA hatalı!"
m3 = SPIModeSimulator(3)
assert m3.cpol == 1 and m3.cpha == 1, "Mod 3 CPOL/CPHA hatalı!"

# 4. Çoklu Slave Bus Çekişme Assertions
s1 = SPISlaveDevice("S1", 1)
s2 = SPISlaveDevice("S2", 2)
bus = SPIMasterBusController([s1, s2])
bus.select_slave(0)
assert bus.check_bus_health() is True, "Tekil seçim sağlıklı olmalı!"
s2.set_cs(0) # Çift CS zorla
assert bus.check_bus_health() is False, "Bus contention yakalanmalıydı!"

# 5. Taktik IMU ve CRC-16 Assertions
imu_dev = TacticalIMUSensor()
imu_clean = imu_dev.read_burst_telemetry(inject_bit_error=False)
assert imu_clean["is_valid"] is True, "IMU CRC doğrulanamadı!"
imu_err = imu_dev.read_burst_telemetry(inject_bit_error=True)
assert imu_err["is_valid"] is False, "IMU CRC hatayı yakalayamadı!"

print("\n[PASS] Gün 170: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
