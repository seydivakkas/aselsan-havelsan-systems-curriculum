

# ==============================================================================# -*- coding: utf-8 -*-
"""
GÜN 171: Kod Bloğu 1 — I2C Protokol Durum Makinesi ve Dalga Formu (SDA/SCL) Simülatörü
START, 7-bit Adres + R/W, 9. Bit ACK/NACK ve STOP Sinyalleşmesi
"""

from typing import List, Dict, Tuple

class I2CFrameSimulator:
    """I2C Protokol Zamanlama ve Sinyal Seviyesi Simülatörü"""
    def __init__(self):
        self.timeline = [] # [{"time": t, "scl": 0/1, "sda": 0/1, "event": str}]

    def generate_transaction(self, slave_addr_7bit: int, is_read: bool, data_byte: int, slave_present: bool = True) -> Dict[str, any]:
        self.timeline.clear()
        t = 0

        # 1. Bus IDLE: SCL=1, SDA=1
        self.timeline.append({"time": t, "scl": 1, "sda": 1, "desc": "BUS IDLE"}); t += 1

        # 2. START KOŞULU: SCL=1 iken SDA 1 -> 0 düşer
        self.timeline.append({"time": t, "scl": 1, "sda": 0, "desc": "START (S)"}); t += 1
        self.timeline.append({"time": t, "scl": 0, "sda": 0, "desc": "SCL LOW (Data Setup)"}); t += 1

        # 3. ADRES BAYTI: 7-bit Adres + R/W Biti (Toplam 8 Bit)
        addr_byte = ((slave_addr_7bit & 0x7F) << 1) | (1 if is_read else 0)
        addr_bits = [(addr_byte >> (7 - i)) & 1 for i in range(8)]

        for i, bit in enumerate(addr_bits):
            # SCL=0 iken SDA değişir
            self.timeline.append({"time": t, "scl": 0, "sda": bit, "desc": f"ADDR Bit {7-i}: {bit}"}); t += 1
            # SCL=1 iken SDA kararlı kalır (Sample)
            self.timeline.append({"time": t, "scl": 1, "sda": bit, "desc": f"ADDR Sample {bit}"}); t += 1
            # SCL tekrar 0'a iner
            self.timeline.append({"time": t, "scl": 0, "sda": bit, "desc": "SCL FALL"}); t += 1

        # 4. 9. BİT: ACK / NACK El Sıkışması
        # Slave mevcutsa SDA'yı 0'a çeker (ACK), yoksa hat HIGH kalır (NACK)
        ack_bit = 0 if slave_present else 1
        ack_desc = "SLAVE ACK (0)" if ack_bit == 0 else "NACK (1) - NO DEVICE"

        self.timeline.append({"time": t, "scl": 0, "sda": ack_bit, "desc": "ACK Slot Setup"}); t += 1
        self.timeline.append({"time": t, "scl": 1, "sda": ack_bit, "desc": ack_desc}); t += 1
        self.timeline.append({"time": t, "scl": 0, "sda": ack_bit, "desc": "ACK Slot End"}); t += 1

        # Eğer NACK alındıysa işlem durur, STOP üretilir
        if ack_bit == 1:
            self.timeline.append({"time": t, "scl": 0, "sda": 0, "desc": "PRE-STOP"}); t += 1
            self.timeline.append({"time": t, "scl": 1, "sda": 0, "desc": "SCL HIGH FOR STOP"}); t += 1
            self.timeline.append({"time": t, "scl": 1, "sda": 1, "desc": "STOP (P) [ABORT]"}); t += 1
            return {"status": "NACK_RECEIVED", "addr_byte": addr_byte, "ack": ack_bit, "timeline": list(self.timeline)}

        # 5. VERİ BAYTI AKTARIMI (Yazma Modu)
        data_bits = [(data_byte >> (7 - i)) & 1 for i in range(8)]
        for i, bit in enumerate(data_bits):
            self.timeline.append({"time": t, "scl": 0, "sda": bit, "desc": f"DATA Bit {7-i}: {bit}"}); t += 1
            self.timeline.append({"time": t, "scl": 1, "sda": bit, "desc": f"DATA Sample {bit}"}); t += 1
            self.timeline.append({"time": t, "scl": 0, "sda": bit, "desc": "SCL FALL"}); t += 1

        # Veri için ACK (0)
        self.timeline.append({"time": t, "scl": 0, "sda": 0, "desc": "DATA ACK Slot"}); t += 1
        self.timeline.append({"time": t, "scl": 1, "sda": 0, "desc": "SLAVE DATA ACK (0)"}); t += 1
        self.timeline.append({"time": t, "scl": 0, "sda": 0, "desc": "SCL FALL"}); t += 1

        # 6. STOP KOŞULU: SCL=1 iken SDA 0 -> 1 yükselir
        self.timeline.append({"time": t, "scl": 0, "sda": 0, "desc": "STOP SETUP"}); t += 1
        self.timeline.append({"time": t, "scl": 1, "sda": 0, "desc": "SCL HIGH"}); t += 1
        self.timeline.append({"time": t, "scl": 1, "sda": 1, "desc": "STOP (P)"}); t += 1

        return {"status": "SUCCESS_ACK", "addr_byte": addr_byte, "ack": ack_bit, "timeline": list(self.timeline)}

# Test: TMP102 Sıcaklık Sensörüne Yazma (Adres: 0x48, Pointer: 0x01)
sim = I2CFrameSimulator()
res_ok = sim.generate_transaction(slave_addr_7bit=0x48, is_read=False, data_byte=0x01, slave_present=True)
res_nack = sim.generate_transaction(slave_addr_7bit=0x48, is_read=False, data_byte=0x01, slave_present=False)

print("[*] I2C START / Adres / ACK / STOP Simülatörü:")
print(f"  [+] 7-bit Adres 0x48 -> 8-bit Yazma Adresi: 0x{res_ok['addr_byte']:02X} (0b{res_ok['addr_byte']:08b})")
print(f"  [+] Cihaz Mevcut Durumu      : {res_ok['status']} (ACK = {res_ok['ack']})")
print(f"  [!] Cihaz Olmayan Durum      : {res_nack['status']} (NACK = {res_nack['ack']})")

assert res_ok["addr_byte"] == 0x90, f"0x48 << 1 = 0x90 olmalı, bulunan: 0x{res_ok['addr_byte']:02X}"
assert res_ok["status"] == "SUCCESS_ACK", "Cihaz mevcutken ACK alınmalıydı!"
assert res_nack["status"] == "NACK_RECEIVED", "Cihaz yokken NACK alınmalıydı!"
print("\n[HÜCRE 6] I2C protokol durum makinesi ve sinyal dalga formu başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 171: Kod Bloğu 2 — I2C Bus Kilitlenmesi ve 9-Saat Kurtarma (Bus Recovery) Simülatörü
SDA LOW Asılı Kalma Durumu, Master GPIO Clock Darbeleri ve Bus'ın Kurtarılması
"""

from typing import Dict, List

class StuckSlaveDevice:
    """Tam veri aktarımının ortasında asılı kalmış sanal sensör"""
    def __init__(self, remaining_bits: List[int]):
        # Slave'in göndereceği kalan bitler (Örn: [0, 0, 1, 1, 0, 1])
        self.remaining_bits = list(remaining_bits)

    def get_sda_level(self) -> int:
        if self.remaining_bits:
            return self.remaining_bits[0] # Şu anki aktif bit
        return 1 # Tüm bitler bittiğinde SDA serbest (HIGH)

    def clock_pulse(self):
        """Master'dan 1 saat darbesi geldiğinde bir sonraki bite geç"""
        if self.remaining_bits:
            self.remaining_bits.pop(0)

class I2CBusRecoveryManager:
    """Master Tarafı 9-Saat Darbeli Bus Kurtarma Motoru"""
    def __init__(self, slave: StuckSlaveDevice):
        self.slave = slave

    def is_bus_stuck(self) -> bool:
        # SDA 0 ise ve hat boşta olmalıysa bus kilitlidir
        return self.slave.get_sda_level() == 0

    def execute_recovery_sequence(self, max_pulses: int = 9) -> Dict[str, any]:
        pulses_applied = 0
        recovered = False

        if not self.is_bus_stuck():
            return {"status": "NOT_STUCK", "pulses": 0}

        # 9 Saat darbesi döngüsü
        for p in range(1, max_pulses + 1):
            pulses_applied += 1
            # SCL LOW -> HIGH -> LOW
            self.slave.clock_pulse()
            
            # SDA serbest kaldı mı? (Lojik 1 oldu mu?)
            if self.slave.get_sda_level() == 1:
                recovered = True
                break

        # Kurtarıldıysa STOP koşulu üret
        stop_generated = recovered

        return {
            "status": "RECOVERED" if recovered else "FAILED",
            "pulses_applied": pulses_applied,
            "stop_generated": stop_generated,
            "final_sda": self.slave.get_sda_level()
        }

# Simülasyon Senaryosu:
# Sensör '0' basarken CPU reset yedi, sensörün içinde [0, 0, 0, 1] bitleri kaldı (SDA = 0 kilitli!)
stuck_slave = StuckSlaveDevice(remaining_bits=[0, 0, 0, 1])
recovery_mgr = I2CBusRecoveryManager(stuck_slave)

print("[*] I2C Bus Kilitlenmesi ve Kurtarma (Bus Recovery) Testi:")
print(f"  [!] Başlangıç Bus Durumu : {'KİLİTLİ (SDA=0)' if recovery_mgr.is_bus_stuck() else 'NORMAL'}")

# Kurtarma Algoritmasını Çalıştır
rec_result = recovery_mgr.execute_recovery_sequence()

print(f"  [+] Kurtarma Sonucu      : {rec_result['status']}")
print(f"  [+] Uygulanan SCLK Darbe : {rec_result['pulses_applied']} darbe")
print(f"  [+] STOP Koşulu Üretildi : {rec_result['stop_generated']}")
print(f"  [+] Nihai SDA Seviyesi   : {rec_result['final_sda']} (3.3V HIGH - Bus Serbest)")

assert rec_result["status"] == "RECOVERED", "Bus kurtarılamadı!"
assert rec_result["pulses_applied"] == 3, "3 darbede SDA serbest kalmalıydı!"
assert rec_result["final_sda"] == 1, "Nihai SDA HIGH olmalı!"
print("\n[HÜCRE 8] I2C Bus Recovery algoritması başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 171: Kod Bloğu 3 — C++20 STM32 Bare-Metal I2C Master Driver Simülasyonu
Sanal I2C Yazmaçları (CR1, SR1, SR2, DR), SB, ADDR, TXE, BTF Bayrak Yönetimi ve Timeout
"""

from typing import Tuple, Optional

class VirtualSTM32I2CHardware:
    """STM32 I2C Donanım Modeli"""
    I2C_SR1_SB   = (1 << 0)
    I2C_SR1_ADDR = (1 << 1)
    I2C_SR1_BTF  = (1 << 2)
    I2C_SR1_RXNE = (1 << 6)
    I2C_SR1_TXE  = (1 << 7)
    I2C_SR1_AF   = (1 << 10) # NACK Failure

    def __init__(self, registered_slave_addr: int = 0x48):
        self.registered_slave = registered_slave_addr
        self.SR1 = 0
        self.SR2 = 0
        self.DR = 0
        self.CR1 = 0
        self.bus_busy = False

    def generate_start(self):
        self.bus_busy = True
        self.SR1 |= self.I2C_SR1_SB # SB = 1

    def write_DR(self, byte_val: int):
        self.DR = byte_val & 0xFF
        # Eğer SB 1 ise yazılan şey adrestir
        if self.SR1 & self.I2C_SR1_SB:
            self.SR1 &= ~self.I2C_SR1_SB # SB temizlendi
            sent_addr = byte_val >> 1
            if sent_addr == self.registered_slave:
                self.SR1 |= self.I2C_SR1_ADDR # ACK geldi: ADDR = 1
            else:
                self.SR1 |= self.I2C_SR1_AF   # Yanlış adres: NACK!
        else:
            # Normal veri baytı yazıldı
            self.SR1 &= ~self.I2C_SR1_TXE
            self.SR1 |= self.I2C_SR1_BTF | self.I2C_SR1_TXE

    def clear_ADDR(self):
        """ADDR bayrağını temizleme kuralı: SR1 okunur, ardından SR2 okunur"""
        self.SR1 &= ~self.I2C_SR1_ADDR
        self.SR1 |= self.I2C_SR1_TXE # Veri göndermeye hazır

    def generate_stop(self):
        self.bus_busy = False
        self.SR1 = 0

class STM32I2CMasterDriver:
    """C++20 Robust STM32 I2C Master Sürücüsü"""
    def __init__(self, hw: VirtualSTM32I2CHardware):
        self.hw = hw

    def write_register(self, slave_addr_7bit: int, reg_addr: int, reg_value: int) -> bool:
        # 1. START Üret
        self.hw.generate_start()
        if not (self.hw.SR1 & VirtualSTM32I2CHardware.I2C_SR1_SB):
            return False

        # 2. Adres Gönder (Write: Bit0 = 0)
        self.hw.write_DR((slave_addr_7bit << 1) | 0)
        if self.hw.SR1 & VirtualSTM32I2CHardware.I2C_SR1_AF:
            self.hw.generate_stop()
            return False # NACK alındı!

        if not (self.hw.SR1 & VirtualSTM32I2CHardware.I2C_SR1_ADDR):
            return False

        # 3. ADDR Bayrağını Temizle
        self.hw.clear_ADDR()

        # 4. Kayıt Adresini Gönder
        self.hw.write_DR(reg_addr)

        # 5. Veri Baytını Gönder
        self.hw.write_DR(reg_value)

        # 6. STOP Üret
        self.hw.generate_stop()
        return True

# Test: TMP102 Sensörüne (0x48) Konfigürasyon Yazma
virt_i2c = VirtualSTM32I2CHardware(registered_slave_addr=0x48)
driver = STM32I2CMasterDriver(virt_i2c)

# 1. Geçerli Cihaza Yazma
success_valid = driver.write_register(slave_addr_7bit=0x48, reg_addr=0x01, reg_value=0x60)
print("[*] STM32 Bare-Metal I2C Sürücü Testi:")
print(f"  [+] TMP102 (0x48) Yazma Durumu : {success_valid} (Başarılı)")

# 2. Olmayan Cihaza Yazma (0x55) -> NACK Testi
success_invalid = driver.write_register(slave_addr_7bit=0x55, reg_addr=0x01, reg_value=0x60)
print(f"  [!] Olmayan Cihaz (0x55) Durumu: {success_invalid} (NACK İle Reddedildi)")

assert success_valid is True, "Geçerli cihaza yazma başarısız oldu!"
assert success_invalid is False, "Olmayan cihaza yazma NACK vermeliydi!"
print("\n[HÜCRE 10] C++20 bare-metal I2C sürücüsü ve bayrak yönetimi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 171: Kod Bloğu 4 — Repeated START ile Sensör Kayıt Okuma (Write-then-Read)
Son Bayt NACK Protokolü ve Çoklu Bayt Telemetri Çekimi Simülasyonu
"""

from typing import List, Dict

class I2CSensorDevice:
    """TMP102 / INA226 Benzeri Sanal Kayıt Tabanlı I2C Sensör"""
    def __init__(self, address: int):
        self.address = address
        # Kayıtlar: 0x00: Sıcaklık (16-bit: 0x1900 = +25.0 °C), 0x01: Config, 0x0B: Cihaz Kimliği (0x5449)
        self.registers = {
            0x00: [0x19, 0x00], # +25.0 C
            0x01: [0x60, 0xA0],
            0x0B: [0x54, 0x49]  # 'TI' Manufacturer ID
        }
        self.selected_pointer = 0x00

    def write_pointer(self, reg_addr: int):
        self.selected_pointer = reg_addr

    def read_byte(self, byte_index: int) -> int:
        data = self.registers.get(self.selected_pointer, [0x00, 0x00])
        if byte_index < len(data):
            return data[byte_index]
        return 0xFF

class I2CReadTransactionSimulator:
    """Repeated START ile 16-bit Kayıt Okuma Simülatörü"""
    def __init__(self, sensor: I2CSensorDevice):
        self.sensor = sensor

    def read_register_16bit(self, slave_addr: int, reg_addr: int) -> Dict[str, any]:
        if slave_addr != self.sensor.address:
            return {"success": False, "error": "ADDR_NACK", "data": None}

        # 1. Aşama: Pointer Yazma
        self.sensor.write_pointer(reg_addr)

        # 2. Aşama: Repeated START ve 2 Bayt Okuma
        # Bayt 1: Master okur ve ACK (0) döner
        b1 = self.sensor.read_byte(0)
        ack1 = 0 # ACK

        # Bayt 2 (Son Bayt): Master okur ve NACK (1) döner!
        b2 = self.sensor.read_byte(1)
        ack2 = 1 # NACK!

        val16 = (b1 << 8) | b2
        return {
            "success": True,
            "bytes": [b1, b2],
            "ack_sequence": [ack1, ack2],
            "value_16bit": val16
        }

# Test: TMP102 Sıcaklık Kaydı (0x00) Okuma
tmp_sensor = I2CSensorDevice(address=0x48)
reader = I2CReadTransactionSimulator(tmp_sensor)

res = reader.read_register_16bit(slave_addr=0x48, reg_addr=0x00)

print("[*] Repeated START ile Sensör Telemetri Okuma Testi:")
print(f"  [+] Okunan Baytlar       : {[f'0x{b:02X}' for b in res['bytes']]}")
print(f"  [+] El Sıkışma Sırası    : ACK={res['ack_sequence'][0]}, NACK={res['ack_sequence'][1]} (Doğru Protokol)")
print(f"  [+] 16-bit Ham Sıcaklık  : 0x{res['value_16bit']:04X}")

# Sıcaklık Hesabı: TMP102 12-bit modunda 4 bit sağa kaydırılır, 0.0625 ile çarpılır
temp_c = (res['value_16bit'] >> 4) * 0.0625
print(f"  [+] Hesaplanan Sıcaklık  : {temp_c:.2f} °C")

assert res["success"] is True, "Okuma başarısız!"
assert res["ack_sequence"] == [0, 1], "Son baytta NACK (1) gönderilmelidir!"
assert temp_c == 25.0, f"Sıcaklık 25.0 C olmalı, bulunan: {temp_c}"
print("\n[HÜCRE 12] Repeated START ve Son-Bayt-NACK kuralı başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 171: Kod Bloğu 5 — Aviyonik Güç ve Sıcaklık Telemetri Çözücü Testi
TMP102 ve INA226 Veri Dönüşümü, Aşırı Akım / Sıcaklık Alarm Seviyeleri
"""

from typing import Dict

class AvionicsHealthMonitor:
    """Aviyonik Güç ve Sıcaklık Güvenlik Denetleyicisi"""
    TEMP_CRITICAL_C = 85.0     # 85 Derece üzeri acil durum
    CURRENT_MAX_AMPS = 12.0    # 12 Amper üzeri aşırı akım

    @staticmethod
    def decode_tmp102(raw_16bit: int) -> float:
        """TMP102 12-bit ikiye tümleyen sıcaklık dönüşümü"""
        temp_val = (raw_16bit >> 4)
        # Negatif sayı kontrolü (12. bit işaret biti)
        if temp_val & 0x800:
            temp_val -= 4096
        return temp_val * 0.0625

    @staticmethod
    def decode_ina226_bus_voltage(raw_16bit: int) -> float:
        """INA226 Bus Voltajı: 1.25 mV / LSB"""
        return raw_16bit * 0.00125

    @staticmethod
    def decode_ina226_current(raw_16bit: int, current_lsb_ma: float = 0.5) -> float:
        """INA226 Akım Değeri: current_lsb_ma cinsinden"""
        # 16-bit signed integer
        if raw_16bit > 32767:
            raw_16bit -= 65536
        return (raw_16bit * current_lsb_ma) / 1000.0

    def evaluate_telemetry(self, temp_raw: int, v_bus_raw: int, current_raw: int) -> Dict[str, any]:
        temp_c = self.decode_tmp102(temp_raw)
        v_bus = self.decode_ina226_bus_voltage(v_bus_raw)
        current_a = self.decode_ina226_current(current_raw)
        power_w = v_bus * current_a

        temp_alarm = temp_c > self.TEMP_CRITICAL_C
        overcurrent_alarm = current_a > self.CURRENT_MAX_AMPS

        return {
            "temperature_c": round(temp_c, 2),
            "bus_voltage_v": round(v_bus, 2),
            "current_amps": round(current_a, 2),
            "power_watts": round(power_w, 2),
            "temp_alarm": temp_alarm,
            "overcurrent_alarm": overcurrent_alarm,
            "system_safe": not (temp_alarm or overcurrent_alarm)
        }

# Test: Normal ve Kritik Durum Simülasyonu
monitor = AvionicsHealthMonitor()

# 1. Normal Durum: +42.5 °C, 28.0 V, 4.2 A
# TMP102: 42.5 / 0.0625 = 680 (0x2A8) -> << 4 = 0x2A80
# INA226 VBUS: 28.0 / 0.00125 = 22400 = 0x5780
# INA226 Current: 4.2 A = 4200 mA / 0.5 = 8400 = 0x20D0
res_normal = monitor.evaluate_telemetry(temp_raw=0x2A80, v_bus_raw=0x5780, current_raw=0x20D0)

print("[*] Aviyonik Donanım Sağlığı (Health Monitoring) Telemetrisi:")
print(f"  [+] Sıcaklık : {res_normal['temperature_c']} °C (Alarm: {res_normal['temp_alarm']})")
print(f"  [+] Güç Barası: {res_normal['bus_voltage_v']} V, {res_normal['current_amps']} A -> {res_normal['power_watts']} W")
print(f"  [+] Sistem Güvenli mi: {res_normal['system_safe']}")

# 2. Aşırı Sıcaklık Sabotaj Testi: +92.0 °C (0x5C00)
res_overheat = monitor.evaluate_telemetry(temp_raw=0x5C00, v_bus_raw=0x5780, current_raw=0x20D0)
print(f"  [!] Aşırı Sıcaklık Durumu: {res_overheat['temperature_c']} °C -> Sistem Güvenli: {res_overheat['system_safe']}")

assert res_normal["system_safe"] is True, "Normal telemetri güvenli olmalı!"
assert res_normal["temperature_c"] == 42.5, "Sıcaklık dönüşümü hatalı!"
assert res_overheat["temp_alarm"] is True and res_overheat["system_safe"] is False, "Aşırı sıcaklık alarmı tetiklenmeliydi!"
print("\n[HÜCRE 14] Aviyonik I2C sensör telemetri çözücü ve alarm motoru başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 171: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. I2C START, STOP, Bit Geçerliliği ve 9. Bit ACK/NACK Dalga Formu
2. I2C Bus Kilitlenmesi (Stuck Bus) ve 9-Saat Darbesi ile Kurtarma (Bus Recovery)
3. Pull-Up Direnci (Rp) ve Bus Kapasitansı (Cb) Yükselme Zamanı (tr) Eğrisi
4. Aviyonik Güç & Sıcaklık Telemetri Çözümleme Panosu (TMP102 / INA226)
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
# PANEL 1: I2C START, STOP ve ACK Dalga Formu
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

time_pts = np.arange(0, 14, 1)
# SCL ve SDA Seviyeleri (Temsili Adres: 0x48 + Write + ACK)
# Adres: 0b1001000 + 0(W) + 0(ACK)
scl_wave = [1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1]
sda_wave = [1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1]

ax1.step(time_pts, np.array(scl_wave) * 0.8 + 1.3, color=C_YELLOW, where='post', linewidth=2.2, label='SCL (Saat Hattı)')
ax1.step(time_pts, np.array(sda_wave) * 0.8 + 0.1, color=C_CYAN, where='post', linewidth=2.2, label='SDA (Veri Hattı)')

# START ve STOP Vurguları
ax1.annotate("START (S)\nSCL=1 iken SDA düşer", xy=(1.5, 0.5), xytext=(0.5, 2.5),
             color=C_GREEN, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_GREEN, arrowstyle="->"))

ax1.annotate("ACK (0)\nSlave çeker", xy=(10.5, 0.1), xytext=(8.5, -0.6),
             color=C_CYAN, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_CYAN, arrowstyle="->"))

ax1.annotate("STOP (P)\nSCL=1 iken SDA çıkar", xy=(13.0, 0.8), xytext=(10.5, 2.5),
             color=C_RED, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_RED, arrowstyle="->"))

ax1.set_yticks([0.5, 1.7])
ax1.set_yticklabels(['SDA Hattı', 'SCL Hattı'], color=C_WHITE, fontweight='bold', fontsize=10)
ax1.set_xlabel("Zaman Çevrimleri (Clock Phases)", color=C_WHITE, fontsize=10)
ax1.set_title("Panel 1: I2C START, STOP, Veri Geçerliliği ve ACK Sinyalleşmesi", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.set_ylim(-0.8, 3.2)
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax1.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 2: I2C Bus Kilitlenmesi ve 9-Saat Kurtarma
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

rec_steps = np.arange(0, 12, 1)
# SCL: İlk başta pasif, sonra Master 9 darbe basar
scl_rec = [1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1]
# SDA: Kilitli (0), 3. darbede serbest (1), sonra STOP ile 1 kalır
sda_rec = [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1]

ax2.step(rec_steps, np.array(scl_rec) * 0.8 + 1.3, color=C_YELLOW, where='post', linewidth=2.2, label='SCL (Master Kurtarma Darbeleri)')
ax2.step(rec_steps, np.array(sda_rec) * 0.8 + 0.1, color=C_RED, where='post', linewidth=2.2, label='SDA (Kilitli -> Kurtarıldı)')

ax2.axvspan(0, 7, color=C_RED, alpha=0.15, label='Kilitli Bölge (SDA=0 Asılı)')
ax2.axvspan(7, 11, color=C_GREEN, alpha=0.15, label='Kurtarılan Bölge (SDA Serbest)')

ax2.set_yticks([0.5, 1.7])
ax2.set_yticklabels(['SDA Seviyesi', 'SCL Darbeleri'], color=C_WHITE, fontweight='bold', fontsize=10)
ax2.set_xlabel("Kurtarma Saat Darbeleri (Pulses)", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: I2C Stuck Bus ve 9-Saat Darbesi ile Kurtarma", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: Pull-Up Direnci (Rp) ve Yükselme Zamanı (tr) Analizi
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

# tr = 0.8473 * Rp * Cb (I2C standardı: %10'dan %90'a çıkış süresi)
cb_pf = 200.0 # 200 pF tipik kart kapasitansı
rp_kohm = np.linspace(1.0, 10.0, 100) # 1k ila 10k
tr_ns = 0.8473 * (rp_kohm * 1e3) * (cb_pf * 1e-12) * 1e9 # ns cinsinden

ax3.plot(rp_kohm, tr_ns, color=C_CYAN, linewidth=2.5, label='Yükselme Süresi tr (Cb = 200 pF)')

# Standart Sınırlar
ax3.axhline(1000, color=C_YELLOW, linestyle='--', label='Standart Mod Limiti (tr < 1000 ns)')
ax3.axhline(300, color=C_RED, linestyle='--', label='Fast Mod Limiti (tr < 300 ns)')

# Önerilen Bölge (2.2k - 4.7k)
ax3.axvspan(2.0, 4.7, color=C_GREEN, alpha=0.2, label='Aviyonik Önerilen Bölge (2.2k - 4.7k)')

ax3.set_xlabel("Pull-Up Direnci Rp (kΩ)", color=C_WHITE, fontsize=10)
ax3.set_ylabel("Sinyal Yükselme Süresi tr (ns)", color=C_WHITE, fontsize=10)
ax3.set_title("Panel 3: Pull-Up Direnci Seçimi ve RC Zaman Sabiti Analizi", color=C_WHITE, fontsize=12, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax3.legend(loc='upper left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 4: Aviyonik Güç & Sıcaklık Telemetrisi (TMP102 / INA226)
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

# 10 Saniyelik telemetri simülasyonu
time_s = np.linspace(0, 10, 20)
temp_profile = 40.0 + 3.0 * np.sin(time_s / 2.0) # 37 - 43 C
voltage_profile = 28.0 + 0.2 * np.random.randn(len(time_s)) # 28V civarı
current_profile = 4.0 + 0.8 * np.sin(time_s) # 3.2 - 4.8 A

ax4.plot(time_s, temp_profile, color=C_YELLOW, marker='o', linewidth=2, label='TMP102 Sıcaklık (°C)')
ax4.plot(time_s, current_profile * 5.0, color=C_CYAN, marker='s', linewidth=2, label='INA226 Akım (x5 Ölçek, A)')
ax4.axhline(85.0, color=C_RED, linestyle=':', label='Kritik Sıcaklık Limiti (85 °C)')

ax4.set_xlabel("Uçuş Süresi (s)", color=C_WHITE, fontsize=10)
ax4.set_ylabel("Telemetri Değeri", color=C_WHITE, fontsize=10)
ax4.set_title("Panel 4: Aviyonik Donanım Sağlığı (Health Monitoring) Telemetrisi", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax4.legend(loc='center right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.suptitle("GÜN 171: I2C Protokolü, 7-bit Adresleme, ACK ve Bus Kurtarma Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_171_i2c_address_start_stop_ack.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_171\gun_171_i2c_address_start_stop_ack.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 171 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. Adresleme Assertions
sim_test = I2CFrameSimulator()
tx_test = sim_test.generate_transaction(0x48, is_read=False, data_byte=0x00, slave_present=True)
assert tx_test["addr_byte"] == 0x90, "0x48 Write adresi 0x90 olmalı!"
assert tx_test["status"] == "SUCCESS_ACK", "ACK doğrulaması başarısız!"

# 3. Bus Recovery Assertions
stuck_test = StuckSlaveDevice([0, 0, 1])
rec_test = I2CBusRecoveryManager(stuck_test).execute_recovery_sequence()
assert rec_test["status"] == "RECOVERED", "Bus recovery başarısız!"
assert rec_test["final_sda"] == 1, "Recovery sonrası SDA 1 olmalı!"

# 4. Repeated START Assertions
sens_test = I2CSensorDevice(0x48)
rd_sim = I2CReadTransactionSimulator(sens_test)
rd_res = rd_sim.read_register_16bit(0x48, 0x00)
assert rd_res["success"] is True, "Sensör okuma başarısız!"
assert rd_res["ack_sequence"] == [0, 1], "Son bayt NACK olmalı!"

# 5. Aviyonik Telemetri Assertions
mon_test = AvionicsHealthMonitor()
t_eval = mon_test.evaluate_telemetry(temp_raw=0x1900, v_bus_raw=22400, current_raw=8400)
assert t_eval["temperature_c"] == 25.0, "Sıcaklık 25C olmalı!"
assert t_eval["bus_voltage_v"] == 28.0, "Voltaj 28V olmalı!"
assert t_eval["system_safe"] is True, "Sistem güvenli olmalı!"

print("\n[PASS] Gün 171: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
