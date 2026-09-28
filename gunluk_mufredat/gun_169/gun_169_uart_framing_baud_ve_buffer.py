

# ==============================================================================# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 1 — UART Çerçeveleme (Framing) Kodlayıcı ve Parity Hesaplayıcı
8N1, 8E1, 8O1, 8N2 Formatlarında Bit Dizilimi ve Eşlik Doğrulama
"""

from typing import List, Dict, Tuple

class UARTFrameEncoder:
    """UART Çerçeve Oluşturucu ve Parity Motoru"""
    
    @staticmethod
    def calculate_parity(data_byte: int, parity_type: str) -> int:
        """Even veya Odd parity bitini hesaplar"""
        # 1'lerin sayısını hesapla (popcount)
        ones_count = bin(data_byte).count('1')
        if parity_type.upper() == 'E': # Even (Çift)
            return 1 if (ones_count % 2 != 0) else 0
        elif parity_type.upper() == 'O': # Odd (Tek)
            return 0 if (ones_count % 2 != 0) else 1
        return 0 # No parity

    @classmethod
    def encode_byte(cls, data_byte: int, data_bits: int = 8, parity: str = 'N', stop_bits: int = 1) -> List[int]:
        """
        Bir baytı UART bit akışına dönüştürür.
        Format: START(0) + DATA (LSB First) + [PARITY] + STOP(1...1)
        """
        frame = [0] # 1. Start Biti (Daima 0)

        # 2. Veri Bitleri (LSB first)
        for i in range(data_bits):
            frame.append((data_byte >> i) & 1)

        # 3. Eşlik Biti (Varsa)
        if parity.upper() in ['E', 'O']:
            p_bit = cls.calculate_parity(data_byte, parity)
            frame.append(p_bit)

        # 4. Durdurma Bitleri (1 veya 2 adet lojik 1)
        for _ in range(stop_bits):
            frame.append(1)

        return frame

    @classmethod
    def decode_frame(cls, frame: List[int], data_bits: int = 8, parity: str = 'N', stop_bits: int = 1) -> Dict[str, any]:
        """Gelen bit çerçevesini çözer, Parity ve Framing Error denetimi yapar"""
        expected_len = 1 + data_bits + (1 if parity.upper() in ['E', 'O'] else 0) + stop_bits
        if len(frame) != expected_len:
            return {"valid": False, "error": "FRAME_LENGTH_MISMATCH", "data": None}

        # 1. Start Bit Kontrolü
        if frame[0] != 0:
            return {"valid": False, "error": "START_BIT_ERROR", "data": None}

        # 2. Veri Bitlerini Topla (LSB first)
        data_byte = 0
        for i in range(data_bits):
            data_byte |= (frame[1 + i] << i)

        # 3. Parity Kontrolü
        cursor = 1 + data_bits
        if parity.upper() in ['E', 'O']:
            rx_parity = frame[cursor]
            calc_p = cls.calculate_parity(data_byte, parity)
            if rx_parity != calc_p:
                return {"valid": False, "error": "PARITY_ERROR", "data": data_byte}
            cursor += 1

        # 4. Stop Bit Kontrolü (Framing Error Check)
        for s in range(stop_bits):
            if frame[cursor + s] != 1:
                return {"valid": False, "error": "FRAMING_ERROR", "data": data_byte}

        return {"valid": True, "error": None, "data": data_byte, "char": chr(data_byte) if 32 <= data_byte <= 126 else None}

# Test ve Doğrulama: 'M' Harfi (ASCII 77 = 0x4D = 0b01001101)
# 1'lerin sayısı = 4 (Çift)
test_val = 0x4D # 'M'

# 8N1 Çerçevesi
frame_8n1 = UARTFrameEncoder.encode_byte(test_val, 8, 'N', 1)
# 8E1 Çerçevesi: 4 adet 1 var -> Even parity için P=0 olmalı
frame_8e1 = UARTFrameEncoder.encode_byte(test_val, 8, 'E', 1)
# 8O1 Çerçevesi: 4 adet 1 var -> Odd parity için P=1 olmalı
frame_8o1 = UARTFrameEncoder.encode_byte(test_val, 8, 'O', 1)
# 8N2 Çerçevesi: 2 Stop biti
frame_8n2 = UARTFrameEncoder.encode_byte(test_val, 8, 'N', 2)

dec_8n1 = UARTFrameEncoder.decode_frame(frame_8n1, 8, 'N', 1)
dec_8e1 = UARTFrameEncoder.decode_frame(frame_8e1, 8, 'E', 1)

print("[*] UART Çerçeveleme (Framing) Doğrulama Testi:")
print(f"  [+] 'M' (0x4D) 8N1 Frame ({len(frame_8n1)} bit): {frame_8n1}")
print(f"  [+] 'M' (0x4D) 8E1 Frame ({len(frame_8e1)} bit): {frame_8e1}")
print(f"  [+] 'M' (0x4D) 8O1 Frame ({len(frame_8o1)} bit): {frame_8o1}")
print(f"  [+] 'M' (0x4D) 8N2 Frame ({len(frame_8n2)} bit): {frame_8n2}")
print(f"  [+] 8N1 Çözümleme : {dec_8n1['char']} (Hata: {dec_8n1['error']})")
print(f"  [+] 8E1 Çözümleme : {dec_8e1['char']} (Hata: {dec_8e1['error']})")

# Kasıtlı Parity Bozulması Testi
corrupted_8e1 = list(frame_8e1)
corrupted_8e1[9] ^= 1 # Parity bitini ters çevir
dec_corrupt = UARTFrameEncoder.decode_frame(corrupted_8e1, 8, 'E', 1)
print(f"  [!] Bozuk Parity Testi: {dec_corrupt['error']}")

assert dec_8n1["valid"] is True and dec_8n1["data"] == 0x4D, "8N1 çözülemedi!"
assert dec_8e1["valid"] is True and dec_8e1["data"] == 0x4D, "8E1 çözülemedi!"
assert dec_corrupt["error"] == "PARITY_ERROR", "Parity hatası yakalanamadı!"
assert frame_8o1[9] == 1, "Odd parity biti 1 olmalıydı!"
print("\n[HÜCRE 6] UART framing ve parity doğrulama motoru başarıyla onaylandı.")

# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 2 — Baud Hızı Saat Kayması (Clock Drift) ve Framing Error (FE) Simülatörü
Frekans Sapmasının Kümülatif Zamanlama Hatası ve STOP Biti Üzerindeki Yıkıcı Etkisi
"""

import numpy as np
from typing import Dict, List, Tuple

class ClockDriftSimulator:
    """Verici ve Alıcı Arasındaki Saat Frekansı Sapmasını Simüle Eden Motor"""
    def __init__(self, nominal_baud: int = 115200):
        self.nominal_baud = nominal_baud
        self.t_bit_ideal = 1.0 / nominal_baud

    def simulate_transmission(self, drift_percent: float, bits: List[int]) -> Dict[str, any]:
        """
        drift_percent: +3.0 -> Alıcı %3 daha hızlı, -3.0 -> Alıcı %3 daha yavaş
        bits: [START(0), D0..D7, STOP(1)] (10 bit)
        """
        drift_ratio = 1.0 + (drift_percent / 100.0)
        rx_baud = self.nominal_baud * drift_ratio
        t_bit_rx = 1.0 / rx_baud

        # Alıcının her bit için örnekleme anları (Start bit düşen kenarı t=0 kabul edilir)
        sample_times = [(i + 0.5) * t_bit_rx for i in range(len(bits))]
        
        sampled_values = []
        timing_errors_fraction = []
        framing_error = False

        for i, t_sample in enumerate(sample_times):
            # İdeal verici dalga formunda t_sample anındaki gerçek bit hangisi?
            tx_bit_index = int(t_sample / self.t_bit_ideal)
            
            # Kümülatif sapmanın bit periyoduna oranı
            ideal_center = (i + 0.5) * self.t_bit_ideal
            error_fraction = (t_sample - ideal_center) / self.t_bit_ideal
            timing_errors_fraction.append(error_fraction)

            if tx_bit_index < len(bits):
                read_val = bits[tx_bit_index]
            else:
                read_val = 1 # Hat stop sonrası idle (1)

            sampled_values.append(read_val)

            # Stop biti kontrolü (Son bit)
            if i == len(bits) - 1:
                # Stop biti lojik 1 olmalıdır
                if read_val != 1 or tx_bit_index != (len(bits) - 1):
                    framing_error = True

        return {
            "drift_percent": drift_percent,
            "framing_error": framing_error,
            "timing_errors_fraction": timing_errors_fraction,
            "sampled_values": sampled_values,
            "max_drift_fraction": max(abs(e) for e in timing_errors_fraction)
        }

# Simülasyon: Farklı Baud Sapmalarında 8N1 Çerçevesi
test_bits = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1] # Alternatif bitler + Stop(1)
drift_tests = [-6.0, -3.5, -1.0, 0.0, +1.0, +3.5, +6.0]

sim_engine = ClockDriftSimulator(nominal_baud=115200)

print(f"[*] Baud Hızı Saat Sapması (Baud Drift) Dayanıklılık Analizi:")
print(f"{'Drift (%)':>10} | {'Maks Kayma (Bit)':>18} | {'Stop Biti Hata?':>16} | {'Sonuç'}")
print("-" * 60)

for d in drift_tests:
    res = sim_engine.simulate_transmission(d, test_bits)
    status_str = "[FAIL] Framing Error" if res["framing_error"] else "[PASS] Kararlı"
    print(f"{d:>9.1f}% | {res['max_drift_fraction']:>17.3f}x | {str(res['framing_error']):>16} | {status_str}")

# Katı Doğrulama Testi
res_safe = sim_engine.simulate_transmission(1.5, test_bits)
res_fatal = sim_engine.simulate_transmission(6.0, test_bits)

assert res_safe["framing_error"] is False, "%1.5 sapmada framing error olmamalı!"
assert res_fatal["framing_error"] is True, "%6.0 sapmada STOP biti kaymalı ve FE oluşmalı!"
print("\n[HÜCRE 8] Baud drift ve kümülatif framing error simülatörü başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 3 — C++20 Uyumlu Lock-Free SPSC Ring Buffer Simülasyonu
Power-of-Two Maskeleme, Taşma (Overflow) Koruması ve Kilit-Siz İndeks Yönetimi
"""

from typing import Optional, List

class LockFreeSPSCRingBuffer:
    """
    Tek Üretici (ISR) - Tek Tüketici (Thread) Dairesel Tampon.
    Tampon boyutu kesinlikle 2'nin kuvveti olmalıdır (Örn: 16, 64, 256).
    """
    def __init__(self, capacity_power_of_two: int = 16):
        # 2'nin kuvveti kontrolü: (N & (N - 1)) == 0
        assert (capacity_power_of_two & (capacity_power_of_two - 1)) == 0, "Kapasite 2'nin kuvveti olmalıdır!"
        self.capacity = capacity_power_of_two
        self.mask = capacity_power_of_two - 1
        self.buffer = [0] * self.capacity
        self.head = 0 # Üretici yazar
        self.tail = 0 # Tüketici okur
        self.overflow_drops = 0

    def push_from_isr(self, byte_val: int) -> bool:
        """Üretici (ISR) Metodu: Kilit yok, atomik indeks ilerletme"""
        next_head = (self.head + 1) & self.mask
        if next_head == self.tail:
            # Tampon tamamen dolu! Taşma politikası: Yeni gelen baytı at (Drop)
            self.overflow_drops += 1
            return False

        self.buffer[self.head] = byte_val & 0xFF
        self.head = next_head
        return True

    def pop_to_consumer(self) -> Optional[int]:
        """Tüketici (Ana Görev) Metodu: Kilit yok"""
        if self.head == self.tail:
            return None # Tampon boş

        byte_val = self.buffer[self.tail]
        self.tail = (self.tail + 1) & self.mask
        return byte_val

    def available(self) -> int:
        """Tampondaki okunmaya hazır bayt sayısı"""
        return (self.head - self.tail) & self.mask

    def is_full(self) -> bool:
        return ((self.head + 1) & self.mask) == self.tail

# Test ve Doğrulama
ring = LockFreeSPSCRingBuffer(capacity_power_of_two=8) # Kapasite 8 (Maks 7 bayt saklar)

# 1. 5 Bayt Yaz
test_data = [0x10, 0x20, 0x30, 0x40, 0x50]
for b in test_data:
    assert ring.push_from_isr(b) is True

print("[*] Lock-Free SPSC Ring Buffer Doğrulama Testi:")
print(f"  [+] 5 bayt yazıldı. Hazır bayt sayısı : {ring.available()}")
assert ring.available() == 5

# 2. 2 Bayt Oku
read_b1 = ring.pop_to_consumer()
read_b2 = ring.pop_to_consumer()
print(f"  [+] 2 bayt okundu: 0x{read_b1:02X}, 0x{read_b2:02X}. Kalan: {ring.available()}")
assert read_b1 == 0x10 and read_b2 == 0x20
assert ring.available() == 3

# 3. Tamponu Doldur (Maks 7 bayt saklayabilir, 4 bayt daha yazalım)
for b in [0x60, 0x70, 0x80, 0x90]:
    ring.push_from_isr(b)

print(f"  [+] Tampon dolduruldu. Hazır bayt: {ring.available()}, Dolu mu: {ring.is_full()}")
assert ring.is_full() is True

# 4. Taşma (Overflow) Testi: Doluyken 1 bayt daha zorla
overflow_result = ring.push_from_isr(0xFF)
print(f"  [!] Taşma denemesi kabul edildi mi: {overflow_result} (Düşen paketler: {ring.overflow_drops})")
assert overflow_result is False
assert ring.overflow_drops == 1

# 5. Kalan tüm baytları oku (Wrap-around testi)
drained = []
while True:
    b = ring.pop_to_consumer()
    if b is None:
        break
    drained.append(b)

print(f"  [+] Boşaltılan baytlar: {[hex(x) for x in drained]}")
assert drained == [0x30, 0x40, 0x50, 0x60, 0x70, 0x80, 0x90]
assert ring.available() == 0
print("\n[HÜCRE 10] Lock-free ring buffer ve power-of-two maskeleme başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 4 — Kesme Tabanlı Sanal STM32 USART RXNE ve Ring Buffer Sürücüsü
Sanal Donanım Kesmesi, Top-Half Tamponlama ve CPU Yükü Karşılaştırması
"""

from typing import List

class VirtualSTM32InterruptUART:
    """Sanal Donanım ve Kesme Motoru Modeli"""
    def __init__(self, rx_buffer_size: int = 64):
        self.ring_buffer = LockFreeSPSCRingBuffer(rx_buffer_size)
        self.rxne_interrupt_count = 0
        self.error_interrupt_count = 0
        self.cpu_cycles_spent_in_isr = 0

    def hardware_incoming_byte(self, byte_val: int, has_framing_error: bool = False):
        """Donanımın RX pininden bir bayt tamamlandığında NVIC kesmesi fırlatması"""
        # 1. Donanım Kesme Hizmet Rutini (USART1_IRQHandler Simülasyonu)
        self.rxne_interrupt_count += 1
        self.cpu_cycles_spent_in_isr += 15 # Top-half ortalama 15 çevrim sürer

        if has_framing_error:
            self.error_interrupt_count += 1
        else:
            # Ring buffer'a ekle
            self.ring_buffer.push_from_isr(byte_val)

    def read_available_data(self) -> List[int]:
        """Tüketici katmanının tamponu boşaltması"""
        collected = []
        while True:
            b = self.ring_buffer.pop_to_consumer()
            if b is None:
                break
            collected.append(b)
        return collected

# Simülasyon: 20 Baytlık Sensör Telemetri Verisi Akışı
sensor_stream = list(b"ASELSAN_RADAR_ALT_99")
uart_system = VirtualSTM32InterruptUART(rx_buffer_size=32)

# Donanımdan peş peşe baytlar akıyor
for b in sensor_stream:
    uart_system.hardware_incoming_byte(b)

# 1 bayt Framing Error enjekte et
uart_system.hardware_incoming_byte(0x00, has_framing_error=True)

# Tüketici veriyi okur
received_bytes = uart_system.read_available_data()
received_text = bytes(received_bytes).decode('ascii')

# CPU Yükü Karşılaştırması (Polling vs Interrupt)
# 20 Bayt @ 115200 baud -> ~1.73 ms sürer. 168 MHz'de toplam çevrim: 290,000 çevrim
total_mcu_cycles = 290_000
isr_cycles = uart_system.cpu_cycles_spent_in_isr
interrupt_cpu_overhead_pct = (isr_cycles / total_mcu_cycles) * 100.0

print("[*] Kesme Tabanlı UART RX ve CPU Yükü Analizi:")
print(f"  [+] Alınan Telemetri     : {received_text}")
print(f"  [+] Tetiklenen RXNE ISR  : {uart_system.rxne_interrupt_count} adet")
print(f"  [+] Yakalanan Hata       : {uart_system.error_interrupt_count} adet FE")
print(f"  [+] ISR Toplam Çevrim    : {isr_cycles} çevrim")
print(f"  [+] Kesme Tabanlı CPU Yükü: %{interrupt_cpu_overhead_pct:.3f} (Polling: %100.0)")

assert received_text == "ASELSAN_RADAR_ALT_99", "Gelen telemetri verisi eşleşmiyor!"
assert uart_system.error_interrupt_count == 1, "Framing error yakalanmalıydı!"
assert interrupt_cpu_overhead_pct < 0.5, "Kesme yükü %0.5'in altında olmalı!"
print("\n[HÜCRE 12] Kesme tabanlı sanal USART ve ring buffer sürücüsü başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 5 — Aviyonik Radar Altimetre WCET Tampon Boyutlandırma Testi
921600 Baud Hızında Görev Gecikmesi (Task Jitter) ve Tampon Taşma Analizi
"""

def test_buffer_sizing(buffer_capacity: int, burst_bytes: int) -> Dict[str, any]:
    ring = LockFreeSPSCRingBuffer(capacity_power_of_two=buffer_capacity)
    # Patlama anında gelen verileri it
    for i in range(burst_bytes):
        ring.push_from_isr(i & 0xFF)

    return {
        "capacity": buffer_capacity,
        "burst_bytes": burst_bytes,
        "saved_bytes": ring.available(),
        "dropped_bytes": ring.overflow_drops,
        "is_safe": ring.overflow_drops == 0
    }

# Senaryo: 5 ms görev bloklanmasında biriken 80 baytlık veri patlaması
burst_size = 80

res_64 = test_buffer_sizing(buffer_capacity=64, burst_bytes=burst_size)
res_128 = test_buffer_sizing(buffer_capacity=128, burst_bytes=burst_size)
res_256 = test_buffer_sizing(buffer_capacity=256, burst_bytes=burst_size)

print("[*] Aviyonik Radar Altimetre Tampon Boyutlandırma Raporu (80 Bayt Patlama):")
print(f"  [!] 64-Bayt Tampon  : Kaydedilen = {res_64['saved_bytes']}, Düşen = {res_64['dropped_bytes']} bayt -> [FAIL] TEHLİKELİ")
print(f"  [+] 128-Bayt Tampon : Kaydedilen = {res_128['saved_bytes']}, Düşen = {res_128['dropped_bytes']} bayt -> [PASS] GÜVENLİ")
print(f"  [+] 256-Bayt Tampon : Kaydedilen = {res_256['saved_bytes']}, Düşen = {res_256['dropped_bytes']} bayt -> [PASS] ASKERİ MARJ")

assert res_64["is_safe"] is False and res_64["dropped_bytes"] > 0, "64 bayt taşmalıydı!"
assert res_128["is_safe"] is True and res_128["dropped_bytes"] == 0, "128 bayt sıfır kayıp sağlamalı!"
assert res_256["is_safe"] is True and res_256["dropped_bytes"] == 0, "256 bayt sıfır kayıp sağlamalı!"
print("\n[HÜCRE 14] Aviyonik WCET tampon boyutlandırma analizi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 169: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. UART Framing Formatları Karşılaştırması (8N1 vs 8E1 vs 8N2)
2. Baud Hızı Saat Kayması (Clock Drift) ve Kümülatif Örnekleme Sapması (FE Bölgesi)
3. Lock-Free Ring Buffer Dairesel Bellek Modeli (Head, Tail, Boş, Dolu, Wrap-Around)
4. Aviyonik WCET Görev Gecikmesine Karşı Minimum Tampon Boyutu Eğrisi
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
# PANEL 1: UART Framing Formatları (8N1 vs 8E1 vs 8N2)
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

formats = ['8N1 (10 Bit)', '8E1 (11 Bit)', '8N2 (11 Bit)']
y_positions = [2.5, 1.5, 0.5]

# 8N1: START(0), D0..D7(8), STOP(1)
# 8E1: START(0), D0..D7(8), PARITY(1), STOP(1)
# 8N2: START(0), D0..D7(8), STOP1(1), STOP2(1)

def plot_frame_bar(ax, y, labels, colors, widths):
    x_curr = 0
    for l, c, w in zip(labels, colors, widths):
        ax.barh(y, w, left=x_curr, height=0.5, color=c, edgecolor='#0F172A', alpha=0.9)
        ax.text(x_curr + w/2, y, l, ha='center', va='center', color='#0F172A', fontweight='bold', fontsize=8)
        x_curr += w

# 8N1
plot_frame_bar(ax1, 2.5, ['START', '8 DATA BITS', 'STOP'], [C_YELLOW, C_CYAN, C_GREEN], [1, 8, 1])
# 8E1
plot_frame_bar(ax1, 1.5, ['START', '8 DATA BITS', 'PARITY', 'STOP'], [C_YELLOW, C_CYAN, C_PURPLE, C_GREEN], [1, 8, 1, 1])
# 8N2
plot_frame_bar(ax1, 0.5, ['START', '8 DATA BITS', 'STOP 1', 'STOP 2'], [C_YELLOW, C_CYAN, C_GREEN, '#10B981'], [1, 8, 1, 1])

ax1.set_yticks(y_positions)
ax1.set_yticklabels(formats, fontsize=10, color=C_WHITE, fontweight='bold')
ax1.set_xlabel("Bit Süresi (Tbit Cinsinden)", color=C_WHITE, fontsize=10)
ax1.set_title("Panel 1: UART Çerçeveleme (Framing) Formatları Anatomisi", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.set_xlim(0, 12)
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')

# ------------------------------------------------------------------------------
# PANEL 2: Baud Hızı Saat Kayması (Clock Drift) ve Kümülatif Örnekleme Sapması
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

bits_seq = np.arange(0, 10, 1) # Start, D0..D7, Stop
drifts = [0.0, 2.0, 3.75, 5.0, 6.5]
colors_drift = [C_GREEN, C_CYAN, C_YELLOW, C_RED, '#EF4444']

for d, c in zip(drifts, colors_drift):
    # Kümülatif kayma: Delta T = i * (d / 100)
    cumulative_drift = bits_seq * (d / 100.0)
    label_str = f"Saat Sapması %{d:.2f}"
    if d == 0.0:
        label_str += " (İdeal)"
    elif d == 3.75:
        label_str += " (Aviyonik Limit)"
    elif d >= 5.0:
        label_str += " (Framing Error!)"
    ax2.plot(bits_seq, cumulative_drift, marker='o', color=c, linewidth=2, label=label_str)

# Hata Bölgesi (+0.5 Tbit sınırı)
ax2.axhline(0.5, color=C_RED, linestyle='--', linewidth=1.5, label='Kritik Eşik (+0.5 Tbit FE Sınırı)')
ax2.axhspan(0.5, 0.7, color=C_RED, alpha=0.2)
ax2.text(1, 0.53, "FRAMING ERROR (FE) BÖLGESİ", color=C_RED, fontweight='bold', fontsize=9)

ax2.set_xticks(bits_seq)
ax2.set_xticklabels(['START', 'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'STOP'], fontsize=8, color=C_WHITE)
ax2.set_ylabel("Kümülatif Kayma (Tbit Kesri)", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: Kümülatif Saat Kayması ve STOP Biti Sapması", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='upper left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: Lock-Free Ring Buffer Dairesel Bellek Modeli
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

# 16 Elemanlı Dairesel Tampon Çizimi
n_slots = 16
angles = np.linspace(0, 2*np.pi, n_slots, endpoint=False)
radii = np.ones(n_slots) * 5

# Temsili Dolu Yuvalar (Tail: 3, Head: 10 -> Yuvalar 3..9 dolu)
slot_colors = []
for i in range(n_slots):
    if 3 <= i <= 9:
        slot_colors.append(C_CYAN) # Dolu
    else:
        slot_colors.append('#334155') # Boş

x_coords = radii * np.cos(angles)
y_coords = radii * np.sin(angles)

ax3.scatter(x_coords, y_coords, s=550, c=slot_colors, edgecolors=C_WHITE, linewidth=1.5, zorder=3)

for i in range(n_slots):
    label = f"{i}"
    if i == 3:
        label += "\nTAIL"
    elif i == 10:
        label += "\nHEAD"
    ax3.text(x_coords[i], y_coords[i], label, ha='center', va='center', color=C_WHITE, fontsize=8, fontweight='bold')

# Merkez Bilgi Notu
ax3.text(0, 0.5, "Lock-Free SPSC\nPower-of-Two (16)", ha='center', va='center', color=C_WHITE, fontsize=11, fontweight='bold')
ax3.text(0, -1.5, "Dolu: 7 Bayt\nBoş: 8 Bayt\nMask: 0x0F", ha='center', va='center', color=C_YELLOW, fontsize=9)

ax3.set_xlim(-7, 7)
ax3.set_ylim(-7, 7)
ax3.set_aspect('equal')
ax3.axis('off')
ax3.set_title("Panel 3: Lock-Free Dairesel Tampon (Head/Tail ve Power-of-Two)", color=C_WHITE, fontsize=12, fontweight='bold')

# ------------------------------------------------------------------------------
# PANEL 4: Aviyonik WCET Görev Gecikmesine Karşı Minimum Tampon Boyutu
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

latency_ms = np.linspace(1, 20, 100) # 1 ms ila 20 ms WCET görev gecikmesi
# 921600 baud -> ~92160 byte/s (Teorik maks), tipik aviyonik telemetri: 20000 byte/s
data_rate_bytes_sec = 20_000

min_buffer_bytes = data_rate_bytes_sec * (latency_ms / 1000.0)

ax4.plot(latency_ms, min_buffer_bytes, color=C_CYAN, linewidth=2.5, label='Gereken Tampon (20 KB/s Veri Akışı)')

# Standart 2'nin kuvveti tampon eşikleri
ax4.axhline(64, color='#94A3B8', linestyle=':', label='64-Bayt Eşiği')
ax4.axhline(128, color=C_YELLOW, linestyle='--', label='128-Bayt Eşiği')
ax4.axhline(256, color=C_GREEN, linestyle='-.', label='256-Bayt Eşiği (Aviyonik Önerilen)')

# 5 ms kritik nokta (Güdüm WCET)
ax4.scatter([5.0], [100.0], color=C_RED, s=80, zorder=5)
ax4.annotate("5 ms Güdüm Gecikmesi\n(100 Bayt Birikir)", xy=(5, 100), xytext=(8, 150),
             color=C_RED, fontweight='bold', fontsize=9,
             arrowprops=dict(facecolor=C_RED, arrowstyle="->"))

ax4.set_xlabel("WCET Görev Bloklanma Süresi (ms)", color=C_WHITE, fontsize=10)
ax4.set_ylabel("Gereken Minimum Tampon (Bayt)", color=C_WHITE, fontsize=10)
ax4.set_title("Panel 4: Görev Gecikmesine Göre Tampon Boyutlandırma Eğrisi", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax4.legend(loc='upper left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.suptitle("GÜN 169: UART Framing, Baud Toleransı ve Lock-Free Dairesel Tampon Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_169_uart_framing_baud_ve_buffer.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_169\gun_169_uart_framing_baud_ve_buffer.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 169 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. Framing ve Parity Assertions
enc = UARTFrameEncoder()
f_test = enc.encode_byte(0x55, 8, 'E', 1)
d_test = enc.decode_frame(f_test, 8, 'E', 1)
assert d_test["valid"] is True and d_test["data"] == 0x55, "Framing decode hatası!"

# 3. Baud Drift Assertions
drift_sim = ClockDriftSimulator(115200)
res_drift_ok = drift_sim.simulate_transmission(2.0, [0, 1, 0, 1, 0, 1, 0, 1, 0, 1])
res_drift_fail = drift_sim.simulate_transmission(6.0, [0, 1, 0, 1, 0, 1, 0, 1, 0, 1])
assert res_drift_ok["framing_error"] is False, "2% drift tolere edilmeliydi!"
assert res_drift_fail["framing_error"] is True, "6% drift FE oluşturmalıydı!"

# 4. Lock-Free SPSC Ring Buffer Assertions
rb = LockFreeSPSCRingBuffer(32)
for i in range(10):
    rb.push_from_isr(i)
assert rb.available() == 10, "Ring buffer available hatalı!"
popped = [rb.pop_to_consumer() for _ in range(5)]
assert popped == list(range(5)), "Okunan bayt sırası hatalı!"
assert rb.available() == 5, "Kalan bayt sayısı hatalı!"

# 5. WCET Buffer Sizing Assertions
r_sz = test_buffer_sizing(buffer_capacity=128, burst_bytes=80)
assert r_sz["is_safe"] is True and r_sz["dropped_bytes"] == 0, "128 bayt sıfır kayıp sağlamalı!"

print("\n[PASS] Gün 169: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
