

# ==============================================================================# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 1 — STM32 Baud Rate Generator (BRR) Hesaplayıcı
Farklı PCLK Frekanslarında Mantissa, Fraction ve Hata Yüzdesi Analizi
"""

from typing import Dict, List, Tuple

class STM32BaudRateCalculator:
    """
    STM32 USART Baud Rate Register (BRR) Hesaplama Motoru.
    Standart 16x oversampling (OVER8=0) ve yüksek hızlı 8x oversampling (OVER8=1) destekler.
    """
    def __init__(self, pclk_hz: int):
        self.pclk_hz = pclk_hz

    def calculate_brr(self, target_baud: int, over8: int = 0) -> Dict[str, float]:
        oversampling = 8 if over8 == 1 else 16
        usart_div = self.pclk_hz / (oversampling * target_baud)
        
        mantissa = int(usart_div)
        fraction_float = (usart_div - mantissa) * oversampling
        fraction = round(fraction_float)

        # Fraction taşma kontrolü (Örn: 16x'te fraction 16 olursa mantissa 1 artar)
        if fraction >= oversampling:
            mantissa += 1
            fraction = 0

        # Donanımsal BRR yazmaç değeri
        if over8 == 0:
            brr_reg = (mantissa << 4) | (fraction & 0x0F)
            actual_div = mantissa + (fraction / 16.0)
        else:
            # OVER8=1 iken fraction 3-bit'tir (Bit [2:0]), Bit 3 sıfır olmalıdır
            brr_reg = (mantissa << 4) | (fraction & 0x07)
            actual_div = mantissa + (fraction / 8.0)

        actual_baud = self.pclk_hz / (oversampling * actual_div) if actual_div > 0 else 0
        error_pct = ((actual_baud - target_baud) / target_baud) * 100.0

        return {
            "pclk_mhz": self.pclk_hz / 1e6,
            "target_baud": target_baud,
            "over8": over8,
            "usart_div": round(usart_div, 4),
            "mantissa": mantissa,
            "fraction": fraction,
            "brr_hex": f"0x{brr_reg:04X}",
            "actual_baud": round(actual_baud, 2),
            "error_pct": round(error_pct, 4),
            "is_avionics_safe": abs(error_pct) < 2.5
        }

# Simülasyon ve Doğrulama
pclk_apb1 = 42_000_000 # 42 MHz (STM32F4 APB1 Bus)
pclk_apb2 = 84_000_000 # 84 MHz (STM32F4 APB2 Bus)
standard_bauds = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

calc_apb1 = STM32BaudRateCalculator(pclk_apb1)
results_apb1 = [calc_apb1.calculate_brr(b, over8=0) for b in standard_bauds]

print(f"[*] STM32 USART BRR Analizi (PCLK = {pclk_apb1/1e6} MHz, OVER8=0):")
print(f"{'Target Baud':>12} | {'BRR Hex':>8} | {'Mantissa':>8} | {'Fraction':>8} | {'Actual Baud':>12} | {'Error (%)':>10} | {'Safety'}")
print("-" * 75)
for r in results_apb1:
    safe_str = "[PASS] Safe" if r["is_avionics_safe"] else "[FAIL] Risky"
    print(f"{r['target_baud']:>12} | {r['brr_hex']:>8} | {r['mantissa']:>8} | {r['fraction']:>8} | {r['actual_baud']:>12.2f} | {r['error_pct']:>9.3f}% | {safe_str}")

# Katı Doğrulama Testi
res_115200 = calc_apb1.calculate_brr(115200, over8=0)
assert res_115200["mantissa"] == 22, f"Beklenen mantissa 22, bulunan: {res_115200['mantissa']}"
assert res_115200["fraction"] == 13, f"Beklenen fraction 13, bulunan: {res_115200['fraction']}"
assert res_115200["brr_hex"] == "0x016D", f"Beklenen BRR 0x016D, bulunan: {res_115200['brr_hex']}"
assert abs(res_115200["error_pct"]) < 0.2, "Baud hatası %0.2'den küçük olmalı!"
print("\n[HÜCRE 6] STM32 Baud Rate Generator hesaplama motoru başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 2 — UART RX 16x Oversampling ve Majority Voting Simülatörü
Gürültülü Sayısal Sinyalin Örneklenmesi, Çoğunluk Oylaması ve NF (Noise Flag) Tespiti
"""

import numpy as np
from typing import List, Tuple, Dict

class UARTOversamplingReceiver:
    """
    16x Oversampling Alıcı Donanım Simülatörü.
    Start bit düşen kenar tespiti ve 8-9-10 dilimlerinde majority voting uygular.
    """
    def __init__(self, samples_per_bit: int = 16):
        self.samples_per_bit = samples_per_bit

    def decode_stream(self, raw_samples: List[int]) -> Dict[str, any]:
        idx = 0
        n_samples = len(raw_samples)
        decoded_bits = []
        noise_flags = []
        sample_points = []

        # 1. Start Bit Arama (1 -> 0 düşen kenar)
        while idx < n_samples and raw_samples[idx] == 1:
            idx += 1

        if idx >= n_samples:
            return {"status": "NO_START_BIT", "bits": [], "noise": []}

        # Start bit düşen kenar bulundu. Örnekleme sayacını başlat
        start_edge = idx
        
        # 1 Start Biti + 8 Veri Biti + 1 Stop Biti = 10 Bit Toplam
        for bit_idx in range(10):
            bit_start = start_edge + bit_idx * self.samples_per_bit
            if bit_start + 10 >= n_samples:
                break # Akış erken bitti

            # 8, 9, 10 numaralı örnekleme dilimleri
            s8 = raw_samples[bit_start + 8]
            s9 = raw_samples[bit_start + 9]
            s10 = raw_samples[bit_start + 10]
            sample_points.append(bit_start + 9) # Orta nokta

            vote_sum = s8 + s9 + s10
            bit_val = 1 if vote_sum >= 2 else 0
            has_noise = (vote_sum == 1 or vote_sum == 2) # Tam mutabakat yoksa gürültü vardır

            decoded_bits.append(bit_val)
            noise_flags.append(has_noise)

        # Doğrulama: Bit 0 Start bit (0 olmalı), Bit 9 Stop bit (1 olmalı)
        is_valid_frame = (len(decoded_bits) == 10 and decoded_bits[0] == 0 and decoded_bits[-1] == 1)
        
        # 8-bit veri (LSB first)
        data_byte = 0
        if is_valid_frame:
            data_bits = decoded_bits[1:9]
            for i, b in enumerate(data_bits):
                data_byte |= (b << i)

        return {
            "status": "SUCCESS" if is_valid_frame else "FRAMING_ERROR",
            "decoded_bits": decoded_bits,
            "data_byte_hex": f"0x{data_byte:02X}" if is_valid_frame else None,
            "data_char": chr(data_byte) if is_valid_frame and 32 <= data_byte <= 126 else None,
            "noise_detected": any(noise_flags),
            "noise_flags": noise_flags,
            "sample_points": sample_points
        }

# Test: 'A' Harfi (ASCII 65 = 0x41 = 0b01000001)
# LSB first: D0=1, D1=0, D2=0, D3=0, D4=0, D5=0, D6=1, D7=0
# Tam UART Çerçevesi: [START=0, 1, 0, 0, 0, 0, 0, 1, 0, STOP=1]
tx_bits = [0, 1, 0, 0, 0, 0, 0, 1, 0, 1]

# 16x oversampling ile ideal sinyal üret
sim_samples = []
# Başlangıçta 8 örnek IDLE (1)
sim_samples.extend([1] * 8)
for b in tx_bits:
    sim_samples.extend([b] * 16)
# Sonda 8 örnek IDLE (1)
sim_samples.extend([1] * 8)

# Hatta Gürültü Enjekte Et: 
# D0 bitinin 8. dilimine yapay gürültü darbesi koy (Normalde 1, gürültüyle 0 yap)
# Sinyal indeksi: 8 (idle) + 16 (start) + 8 (D0'ın 8. örneği) = 32
sim_samples[32] = 0 # Anlık glitch

rx_sim = UARTOversamplingReceiver()
rx_result = rx_sim.decode_stream(sim_samples)

print("[*] UART 16x Oversampling ve Majority Voting Testi:")
print(f"  [+] Durum            : {rx_result['status']}")
print(f"  [+] Çözülen Bayt (Hex): {rx_result['data_byte_hex']} ({rx_result['data_char']})")
print(f"  [+] Gürültü Sezildi mi: {rx_result['noise_detected']} (NF Bayrağı Set Edildi)")
print(f"  [+] Çözülen Bitler   : {rx_result['decoded_bits']}")

assert rx_result["status"] == "SUCCESS", "Frame başarılı çözülmeliydi!"
assert rx_result["data_byte_hex"] == "0x41", f"Beklenen 0x41 ('A'), okunan: {rx_result['data_byte_hex']}"
assert rx_result["noise_detected"] is True, "D0 bitindeki glitch sezilmeliydi!"
print("\n[HÜCRE 8] 16x Oversampling ve Majority Voting simülatörü başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 3 — Donanım Akış Kontrolü (RTS/CTS) vs Overrun Error (ORE) Simülasyonu
Akış Kontrolsüz Veri Kaybı ile RTS/CTS Güvenli Aktarımının Karşılaştırmalı Modeli
"""

from typing import List, Dict

class UARTSinkDevice:
    """Yavaş alıcı cihaz simülasyonu (Küçük FIFO tamponu ve sınırlı CPU tüketim hızı)"""
    def __init__(self, fifo_capacity: int = 4, use_hardware_flow_control: bool = False):
        self.fifo_capacity = fifo_capacity
        self.use_hw_flow = use_hardware_flow_control
        self.fifo = []
        self.rts_pin = 0 # 0: Ready to Receive (LOW), 1: FIFO Dolu / Meşgul (HIGH)
        self.overrun_errors = 0
        self.received_bytes = []

    def can_accept_byte(self) -> bool:
        if self.use_hw_flow:
            return self.rts_pin == 0
        return True # Akış kontrolü yoksa daima hat açık varsayılır

    def receive_byte(self, byte_val: int):
        if len(self.fifo) >= self.fifo_capacity:
            # Overrun Error! Eski veri okunmadan yeni veri geldi, yeni veri ezildi
            self.overrun_errors += 1
        else:
            self.fifo.append(byte_val)
            self.received_bytes.append(byte_val)
            # Eğer tampon dolduysa ve HW flow açıksa RTS'yi 1 (HIGH) yap
            if self.use_hw_flow and len(self.fifo) >= self.fifo_capacity:
                self.rts_pin = 1

    def process_one_byte_from_fifo(self):
        """Alıcı CPU bir baytı işleyip tamponu boşaltır"""
        if self.fifo:
            self.fifo.pop(0)
            if self.use_hw_flow and len(self.fifo) < self.fifo_capacity:
                self.rts_pin = 0 # Yer açıldı, RTS tekrar LOW (Gönderime hazır)

# Test Senaryosu: 12 Baytlık Hızlı Telemetri Verisi
telemetry_data = list(b"ROKETSAN_NAV") # 12 bayt

# Senaryo A: Donanım Akış Kontrolü YOK (Akış Kontrolsüz Patlama)
sink_no_flow = UARTSinkDevice(fifo_capacity=4, use_hardware_flow_control=False)
for b in telemetry_data:
    sink_no_flow.receive_byte(b) # CPU hiç okuma fırsatı bulamadan peş peşe 12 bayt geldi

# Senaryo B: Donanım Akış Kontrolü AKTİF (RTS/CTS ile Vericiyi Frenleme)
sink_with_flow = UARTSinkDevice(fifo_capacity=4, use_hardware_flow_control=True)
bytes_to_send = list(telemetry_data)
tx_cycles = 0

while bytes_to_send or sink_with_flow.fifo:
    tx_cycles += 1
    # Verici CTS (Alıcının RTS'si) pinini dinler
    if bytes_to_send and sink_with_flow.can_accept_byte():
        next_byte = bytes_to_send.pop(0)
        sink_with_flow.receive_byte(next_byte)
    
    # Her 2 döngüde bir alıcı CPU bir bayt tüketebilsin
    if tx_cycles % 2 == 0:
        sink_with_flow.process_one_byte_from_fifo()

print("[*] Donanım Akış Kontrolü (RTS/CTS) Dayanıklılık Raporu:")
print(f"  [!] Akış Kontrolsüz Alınan Bayt : {len(sink_no_flow.received_bytes)} / {len(telemetry_data)}")
print(f"  [!] Akış Kontrolsüz ORE Hataları: {sink_no_flow.overrun_errors} bayt kayboldu!")
print(f"  [+] RTS/CTS ile Alınan Bayt     : {len(sink_with_flow.received_bytes)} / {len(telemetry_data)}")
print(f"  [+] RTS/CTS ile ORE Hataları    : {sink_with_flow.overrun_errors} (SIFIR Veri Kaybı)")

assert sink_no_flow.overrun_errors == 8, f"Beklenen ORE 8, bulunan: {sink_no_flow.overrun_errors}"
assert sink_with_flow.overrun_errors == 0, "RTS/CTS ile ORE kesinlikle 0 olmalı!"
assert len(sink_with_flow.received_bytes) == 12, "Tüm veri eksiksiz alınmalıydı!"
print("\n[HÜCRE 10] Donanım akış kontrolü ve ORE koruma modeli başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 4 — C++20 STM32 Bare-Metal USART Driver Simülatörü
MMIO Yazmaçları, TXE, TC, RXNE Yoklaması ve Timeout Korumalı Bloklayıcı Sürücü
"""

from typing import Optional, Tuple

class VirtualSTM32USART:
    """
    STM32 USART Donanımının Sanal Yazmaç Modeli (MMIO):
    SR  : Status Register (TXE, TC, RXNE, ORE, FE, PE)
    DR  : Data Register (TDR yazma / RDR okuma)
    CR1 : Control Register 1 (UE, TE, RE)
    """
    USART_SR_PE   = (1 << 0)
    USART_SR_FE   = (1 << 1)
    USART_SR_NF   = (1 << 2)
    USART_SR_ORE  = (1 << 3)
    USART_SR_RXNE = (1 << 5)
    USART_SR_TC   = (1 << 6)
    USART_SR_TXE  = (1 << 7)

    def __init__(self):
        self.SR = self.USART_SR_TXE | self.USART_SR_TC # Başlangıçta hat boşta
        self.TDR = 0
        self.RDR = 0
        self.tx_shift_reg = None
        self.rx_shift_reg = None
        self.tx_wire = [] # Hatta çıkan baytlar

    def write_DR(self, value: int):
        self.TDR = value & 0xFF
        self.SR &= ~self.USART_SR_TXE # TDR doldu, TXE = 0
        self.SR &= ~self.USART_SR_TC  # İletim başladı, TC = 0

    def read_DR(self) -> int:
        val = self.RDR
        self.SR &= ~self.USART_SR_RXNE # RDR okundu, RXNE temizlendi
        return val

    def step_hardware_cycle(self):
        """Donanımın arka plan saat çevrimi"""
        # TDR'dan Shift Register'a aktarım
        if not (self.SR & self.USART_SR_TXE) and self.tx_shift_reg is None:
            self.tx_shift_reg = self.TDR
            self.SR |= self.USART_SR_TXE # TDR boşaldı, yeni bayt kabul edebilir

        # Shift Register'dan kabloya aktarım
        elif self.tx_shift_reg is not None:
            self.tx_wire.append(self.tx_shift_reg)
            self.tx_shift_reg = None
            if self.SR & self.USART_SR_TXE:
                self.SR |= self.USART_SR_TC # Hem TDR hem Shift boşaldı -> TC = 1

    def inject_rx_byte(self, byte_val: int):
        """Dış dünyadan RX pinine bayt gelmesi"""
        if self.SR & self.USART_SR_RXNE:
            self.SR |= self.USART_SR_ORE # Önceki okunmadan geldi: Overrun!
        else:
            self.RDR = byte_val & 0xFF
            self.SR |= self.USART_SR_RXNE # Yeni veri hazır

class STM32PollingUARTDriver:
    """Üretim standardında C++20 benzeri Timeout korumalı Polling sürücüsü"""
    def __init__(self, hardware: VirtualSTM32USART):
        self.hw = hardware

    def transmit_byte(self, byte_val: int, timeout_cycles: int = 100) -> bool:
        cycles = 0
        # 1. TXE bekle
        while not (self.hw.SR & VirtualSTM32USART.USART_SR_TXE):
            self.hw.step_hardware_cycle()
            cycles += 1
            if cycles >= timeout_cycles:
                return False # Zaman aşımı!

        # 2. Veriyi yaz
        self.hw.write_DR(byte_val)
        self.hw.step_hardware_cycle()
        return True

    def flush_tx(self, timeout_cycles: int = 100) -> bool:
        """Tüm bitlerin hattan çıktığını garantile (TC bekle)"""
        cycles = 0
        while not (self.hw.SR & VirtualSTM32USART.USART_SR_TC):
            self.hw.step_hardware_cycle()
            cycles += 1
            if cycles >= timeout_cycles:
                return False
        return True

    def receive_byte(self, timeout_cycles: int = 100) -> Tuple[bool, Optional[int]]:
        cycles = 0
        while not (self.hw.SR & VirtualSTM32USART.USART_SR_RXNE):
            self.hw.step_hardware_cycle()
            cycles += 1
            if cycles >= timeout_cycles:
                return False, None
        return True, self.hw.read_DR()

# Sürücü Doğrulama Testi
virt_hw = VirtualSTM32USART()
driver = STM32PollingUARTDriver(virt_hw)

# 1. İletim Testi
test_payload = b"ASELSAN"
for b in test_payload:
    assert driver.transmit_byte(b) is True, "Bayt iletimi başarısız!"
assert driver.flush_tx() is True, "TC bekleme zaman aşımına uğradı!"

transmitted_str = bytes(virt_hw.tx_wire).decode('ascii')
print("[*] Polling Tabanlı UART İletim Testi:")
print(f"  [+] Gönderilen String : {transmitted_str}")
assert transmitted_str == "ASELSAN", "Gönderilen veri eşleşmiyor!"

# 2. Alım Testi
virt_hw.inject_rx_byte(0x5A) # Dışarıdan 0x5A geldi
success, rx_byte = driver.receive_byte()
print(f"  [+] Alınan Bayt       : 0x{rx_byte:02X} (Başarılı: {success})")
assert success is True and rx_byte == 0x5A, "Alınan bayt hatalı!"
print("\n[HÜCRE 12] C++20 bare-metal polling UART sürücüsü başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 5 — Aviyonik GPS Telemetri Çözücü ve Hata Enjeksiyon Testi
NMEA Checksum Doğrulaması, Framing Error (FE) ve Baud Drift İzolasyonu
"""

from typing import Optional, Dict

class AvionicsGPSTelemetryParser:
    """NMEA-0183 Aviyonik Telemetri Çözücü ve Hata İzleme Modülü"""
    def __init__(self):
        self.valid_packets = 0
        self.checksum_errors = 0
        self.framing_errors = 0

    @staticmethod
    def calculate_nmea_checksum(sentence_content: str) -> str:
        """NMEA-0183 standardı: '$' ile '*' arasındaki tüm karakterlerin XOR toplamı"""
        csum = 0
        for char in sentence_content:
            csum ^= ord(char)
        return f"{csum:02X}"

    def parse_sentence(self, raw_sentence: str, has_framing_error: bool = False) -> Dict[str, any]:
        if has_framing_error:
            self.framing_errors += 1
            return {"valid": False, "error": "FRAMING_ERROR", "data": None}

        # Format kontrolü: $ ile başlamalı, * içermeli
        if not raw_sentence.startswith("$") or "*" not in raw_sentence:
            self.checksum_errors += 1
            return {"valid": False, "error": "MALFORMED_FORMAT", "data": None}

        parts = raw_sentence[1:].split("*")
        content = parts[0]
        received_csum = parts[1].strip()

        expected_csum = self.calculate_nmea_checksum(content)
        if received_csum.upper() != expected_csum.upper():
            self.checksum_errors += 1
            return {"valid": False, "error": "CHECKSUM_MISMATCH", "expected": expected_csum, "received": received_csum}

        # Başarılı paket ayrıştırma
        self.valid_packets += 1
        fields = content.split(",")
        packet_type = fields[0]

        parsed_data = {"type": packet_type}
        if packet_type in ["GNGGA", "GPGGA"] and len(fields) >= 10:
            parsed_data["utc_time"] = fields[1]
            parsed_data["latitude"] = f"{fields[2]} {fields[3]}"
            parsed_data["longitude"] = f"{fields[4]} {fields[5]}"
            parsed_data["fix_quality"] = int(fields[6]) if fields[6].isdigit() else 0
            parsed_data["altitude_m"] = float(fields[9]) if fields[9] else 0.0

        return {"valid": True, "error": None, "data": parsed_data}

# Test ve Simülasyon
parser = AvionicsGPSTelemetryParser()

# 1. Geçerli Aviyonik GPS Paketi ($GNGGA)
# Koordinatlar: 39°55'48" N (ASELSAN Macunköy), 32°45'12" E, Rakım: 875.4m
valid_content = "GNGGA,123519.00,3955.80,N,03245.20,E,1,08,0.9,875.4,M,36.0,M,,"
valid_csum = AvionicsGPSTelemetryParser.calculate_nmea_checksum(valid_content)
valid_sentence = f"${valid_content}*{valid_csum}"

res_valid = parser.parse_sentence(valid_sentence)
print("[*] Aviyonik GPS/INS Telemetri Doğrulama Testi:")
print(f"  [+] Geçerli NMEA Paketi  : {valid_sentence}")
print(f"  [+] Ayrıştırılan Veri    : {res_valid['data']}")

# 2. Checksum Hata Enjeksiyonu (Hatta 1 bit ters döndü)
corrupted_sentence = valid_sentence.replace("875.4", "975.4") # Rakım bozuldu ama checksum eski kaldı
res_corrupt = parser.parse_sentence(corrupted_sentence)
print(f"  [!] Bozuk Paket Durumu   : {res_corrupt['error']} (Beklenen: {res_corrupt.get('expected')}, Gelen: {res_corrupt.get('received')})")

# 3. Framing Error Enjeksiyonu (Baud rate drift sebebiyle STOP biti kaçırıldı)
res_fe = parser.parse_sentence(valid_sentence, has_framing_error=True)
print(f"  [!] Framing Error Durumu : {res_fe['error']}")

assert res_valid["valid"] is True, "Geçerli paket reddedildi!"
assert res_valid["data"]["altitude_m"] == 875.4, "Rakım hatalı çözüldü!"
assert res_corrupt["valid"] is False and res_corrupt["error"] == "CHECKSUM_MISMATCH", "Bozuk checksum yakalanmalıydı!"
assert res_fe["valid"] is False and res_fe["error"] == "FRAMING_ERROR", "Framing error yakalanmalıydı!"
print("\n[HÜCRE 14] Aviyonik telemetri hata enjeksiyonu ve çözümleme motoru başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 168: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. UART Sinyal Zamanlaması ve 16x Oversampling Majority Voting (Start, Data, Stop)
2. STM32 Baud Rate Hata Oranı Eğrisi (Farklı PCLK ve Baud Değerlerinde % Sapma)
3. Donanım Akış Kontrolü (RTS/CTS) ve Alıcı Tamponu Seviyesi (ORE Önleme)
4. UART İletim Süresi ve CPU Bloklanma Karşılaştırması (Baud Hızlarına Göre Gecikme)
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# Matplotlib dark mode ve font ayarları
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
# PANEL 1: UART Sinyal Zamanlaması ve 16x Oversampling (Dilim 8, 9, 10)
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

# 'A' Harfi (0x41 = 0b01000001) -> Frame: START(0), 1, 0, 0, 0, 0, 0, 1, 0, STOP(1)
bits = [0, 1, 0, 0, 0, 0, 0, 1, 0, 1]
bit_labels = ['START\n(0)', 'D0\n(1)', 'D1\n(0)', 'D2\n(0)', 'D3\n(0)', 'D4\n(0)', 'D5\n(0)', 'D6\n(1)', 'D7\n(0)', 'STOP\n(1)']

t_step = []
signal_val = []
for i, b in enumerate(bits):
    t_step.extend([i, i + 0.999])
    signal_val.extend([b, b])

ax1.plot(t_step, signal_val, color=C_CYAN, linewidth=2.5, label='UART TX/RX Sinyali (TTL 3.3V)')

# 16x oversampling noktalarını göster (Özellikle D0 bitinde dilim 8, 9, 10)
d0_center = 1.5 # 1. bitin ortası
ax1.axvspan(1.45, 1.65, color=C_YELLOW, alpha=0.3, label='Majority Voting Penceresi (Örnek 8, 9, 10)')
ax1.scatter([1.48, 1.53, 1.58], [1, 1, 1], color=C_GREEN, s=60, zorder=5, label='Temiz Örnekleme (NF=0)')

# D1 bitinde temsili glitch ve gürültü bayrağı
ax1.scatter([2.48, 2.53, 2.58], [0, 1, 0], color=C_RED, s=60, zorder=5, label='Gürültülü Örnekleme (NF=1)')

ax1.set_xticks(range(10))
ax1.set_xticklabels(bit_labels, fontsize=9, color=C_WHITE)
ax1.set_yticks([0, 1])
ax1.set_yticklabels(['0V (LOW)', '3.3V (HIGH)'], fontsize=10, color=C_WHITE)
ax1.set_title("Panel 1: UART Çerçevesi ve 16x Oversampling (Majority Voting)", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.set_xlabel("Bit Çerçeve İndeksi", color=C_WHITE, fontsize=10)
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax1.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 2: STM32 Baud Rate Hata Oranı Eğrisi (% Sapma)
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

bauds = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
pclk_42 = 42_000_000 # 42 MHz APB1
pclk_84 = 84_000_000 # 84 MHz APB2

def calc_errors(pclk, baud_list):
    errs = []
    for b in baud_list:
        div = pclk / (16.0 * b)
        mant = int(div)
        frac = round((div - mant) * 16)
        if frac >= 16:
            mant += 1
            frac = 0
        act_div = mant + frac / 16.0
        act_b = pclk / (16.0 * act_div)
        err = ((act_b - b) / b) * 100.0
        errs.append(err)
    return errs

errs_42 = calc_errors(pclk_42, bauds)
errs_84 = calc_errors(pclk_84, bauds)

x_pos = np.arange(len(bauds))
width = 0.35

ax2.bar(x_pos - width/2, errs_42, width, label='APB1 (42 MHz PCLK)', color=C_PURPLE, alpha=0.85)
ax2.bar(x_pos + width/2, errs_84, width, label='APB2 (84 MHz PCLK)', color=C_GREEN, alpha=0.85)

# Aviyonik ±2.5% tolerans çizgisi
ax2.axhline(2.5, color=C_RED, linestyle='--', linewidth=1.5, label='Aviyonik Limit (+2.5%)')
ax2.axhline(-2.5, color=C_RED, linestyle='--', linewidth=1.5, label='Aviyonik Limit (-2.5%)')

ax2.set_xticks(x_pos)
ax2.set_xticklabels([str(b) for b in bauds], fontsize=9, color=C_WHITE, rotation=30)
ax2.set_ylabel("Baud Hatası (%)", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: STM32 Baud Rate Hata Oranı (% Sapma Analizi)", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='lower left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: Donanım Akış Kontrolü (RTS/CTS) ve Alıcı Tamponu Seviyesi
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

time_ticks = np.arange(0, 20, 1)
# Tampon doluluk simülasyonu
fifo_no_flow = [0, 1, 2, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]
ore_events =   [0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 8, 8, 8, 8, 8, 8, 8]
fifo_with_flow = [0, 1, 2, 3, 4, 3, 4, 3, 4, 3, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0]
rts_pin_level =  [0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]

ax3.plot(time_ticks, fifo_no_flow, color=C_RED, linestyle=':', linewidth=2, label='Akış Kontrolsüz FIFO (Kilitlenme)')
ax3.plot(time_ticks, ore_events, color='#EF4444', linewidth=2.5, label='Biriken ORE Hataları (Veri Kaybı)')
ax3.plot(time_ticks, fifo_with_flow, color=C_CYAN, linewidth=2.5, label='RTS/CTS ile Güvenli FIFO (Maks: 4)')
ax3.step(time_ticks, np.array(rts_pin_level) * 3.8, color=C_YELLOW, where='post', linewidth=1.8, label='RTS Pini Durumu (HIGH = Dur)')

ax3.axhline(4, color=C_WHITE, linestyle='--', alpha=0.5, label='FIFO Kapasitesi (4 Bayt)')
ax3.set_xlabel("Zaman Çevrimleri (Ticks)", color=C_WHITE, fontsize=10)
ax3.set_ylabel("Tampon / Hata Sayısı", color=C_WHITE, fontsize=10)
ax3.set_title("Panel 3: Donanım Akış Kontrolü (RTS/CTS) ile ORE İzolasyonu", color=C_WHITE, fontsize=12, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax3.legend(loc='upper left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 4: UART İletim Süresi ve CPU Bloklanma Karşılaştırması
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

# 1 Bayt = 10 Bit (1 Start + 8 Data + 1 Stop)
byte_times_us = [(10.0 / b) * 1e6 for b in bauds]
cpu_cycles_168mhz = [t * 168.0 for t in byte_times_us] # 168 MHz MCU'da boşa harcanan komut çevrimi

ax4.plot(bauds, byte_times_us, marker='o', color=C_CYAN, linewidth=2.5, label='1 Bayt İletim Süresi (µs)')
ax4.set_xscale('log')
ax4.set_yscale('log')
ax4.set_xlabel("Baud Hızı (Log Ölçek, bps)", color=C_WHITE, fontsize=10)
ax4.set_ylabel("İletim Süresi (µs)", color=C_CYAN, fontsize=10)
ax4.tick_params(axis='y', labelcolor=C_CYAN)

ax4_twin = ax4.twinx()
ax4_twin.plot(bauds, cpu_cycles_168mhz, marker='s', color=C_YELLOW, linewidth=2, linestyle='--', label='Polling CPU İsrafı (Çevrim)')
ax4_twin.set_yscale('log')
ax4_twin.set_ylabel("168 MHz CPU Çevrim İsrafı", color=C_YELLOW, fontsize=10)
ax4_twin.tick_params(axis='y', labelcolor=C_YELLOW)

ax4.set_title("Panel 4: Baud Hızına Göre İletim Gecikmesi ve CPU Yükü", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')

plt.suptitle("GÜN 168: STM32 UART/USART Temelleri ve Aviyonik Entegrasyon Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_168_uart_temelleri.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_168\gun_168_uart_temelleri.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 168 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. Baud Rate Hesaplama Motoru Assertions
calc_test = STM32BaudRateCalculator(42_000_000)
brr_115200 = calc_test.calculate_brr(115200, over8=0)
assert brr_115200["mantissa"] == 22, "Mantissa değeri hatalı!"
assert brr_115200["fraction"] == 13, "Fraction değeri hatalı!"
assert brr_115200["brr_hex"] == "0x016D", "BRR Hex değeri hatalı!"
assert abs(brr_115200["error_pct"]) < 0.2, "Baud hatası %0.2'den küçük olmalı!"

# 3. 16x Oversampling Decoder Assertions
rx_test = UARTOversamplingReceiver()
# ASCII 'B' = 66 = 0x42 = 0b01000010 -> LSB first: D0=0, D1=1, D2=0, D3=0, D4=0, D5=0, D6=1, D7=0
raw_b_bits = [0, 0, 1, 0, 0, 0, 0, 1, 0, 1] # Start + Data + Stop
stream_samples = []
for b in raw_b_bits:
    stream_samples.extend([b] * 16)
dec_res = rx_test.decode_stream(stream_samples)
assert dec_res["status"] == "SUCCESS", "Frame çözülemedi!"
assert dec_res["data_byte_hex"] == "0x42", f"Beklenen 0x42 ('B'), okunan: {dec_res['data_byte_hex']}"

# 4. Donanım Akış Kontrolü Assertions
sink_test = UARTSinkDevice(fifo_capacity=2, use_hardware_flow_control=True)
sink_test.receive_byte(1)
assert sink_test.rts_pin == 0, "Tampon 1 baytta henüz dolmadı, RTS 0 olmalı!"
sink_test.receive_byte(2)
assert sink_test.rts_pin == 1, "Tampon 2 baytla doldu, RTS 1 olmalı!"
assert sink_test.can_accept_byte() is False, "Tampon doluyken yeni bayt kabul edilmemeli!"
sink_test.process_one_byte_from_fifo()
assert sink_test.rts_pin == 0, "Tampon boşaltılınca RTS 0 olmalı!"

# 5. Aviyonik NMEA Telemetri Çözücü Assertions
gps_parser = AvionicsGPSTelemetryParser()
csum = gps_parser.calculate_nmea_checksum("GPGGA,120000.00,3900.00,N,03200.00,E,1,08,1.0,1000.0,M,0.0,M,,")
nmea_str = f"$GPGGA,120000.00,3900.00,N,03200.00,E,1,08,1.0,1000.0,M,0.0,M,,*{csum}"
parsed = gps_parser.parse_sentence(nmea_str)
assert parsed["valid"] is True, "Geçerli NMEA cümlesi çözülemedi!"
assert parsed["data"]["altitude_m"] == 1000.0, "Rakım hatalı!"

print("\n[PASS] Gün 168: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
