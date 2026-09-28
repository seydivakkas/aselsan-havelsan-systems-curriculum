

# ==============================================================================# -*- coding: utf-8 -*-
"""
GÜN 175: Kod Bloğu 1 — Tek Tampon Veri Yarışı (Data Race) vs Double Buffering Karşılaştırması
Tek Tamponda DMA'nın CPU'yu Ezme Simülasyonu ve Çift Tamponda Tam İzolasyon
"""

from typing import List, Dict, Tuple

class BufferRaceConditionSimulator:
    """Tek Tampon Ezilmesi vs Çift Tampon İzolasyon Simülatörü"""
    def __init__(self, buffer_size: int = 16):
        self.size = buffer_size

    def simulate_single_buffer_race(self, dma_speed: int = 2, cpu_speed: int = 1) -> Dict[str, any]:
        """
        Tek Tampon Senaryosu:
        DMA hattan gelen yeni veriyi (100+) tampona basar.
        CPU ise eski veriyi (0..15) okumaya çalışır.
        DMA CPU'dan daha hızlıysa CPU'yu ezer (Torn Read)!
        """
        # Başlangıçta tamponda 0. paketin verileri var
        buffer = [i for i in range(self.size)]
        
        cpu_read_values = []
        corrupted_reads = 0
        
        # CPU okuma indisi ve DMA yazma indisi
        cpu_idx = 0
        dma_idx = 0
        
        while cpu_idx < self.size:
            # 1. DMA dma_speed kadar bayt yazar (Yeni Paket: 100+)
            for _ in range(dma_speed):
                if dma_idx < self.size:
                    buffer[dma_idx] = 100 + dma_idx
                    dma_idx += 1
                    
            # 2. CPU cpu_speed kadar bayt okur
            for _ in range(cpu_speed):
                if cpu_idx < self.size:
                    val = buffer[cpu_idx]
                    cpu_read_values.append(val)
                    # Eğer okunan değer 100'den büyükse, CPU daha okuyamadan DMA üstüne yazmıştır!
                    if val >= 100:
                        corrupted_reads += 1
                    cpu_idx += 1

        return {
            "buffer_type": "SINGLE_BUFFER",
            "read_values": cpu_read_values,
            "corrupted_count": corrupted_reads,
            "corruption_ratio": corrupted_reads / self.size,
            "status": "DATA_CORRUPTED" if corrupted_reads > 0 else "OK"
        }

    def simulate_double_buffer(self) -> Dict[str, any]:
        """
        Çift Tampon Senaryosu:
        DMA Tampon A'yı (100+) doldururken CPU Tampon B'yi (0..15) okur.
        Tamamen izole bellek alanları!
        """
        buf_a = [100 + i for i in range(self.size)] # DMA'nın doldurduğu
        buf_b = [i for i in range(self.size)]       # CPU'nun okuduğu
        
        # CPU sadece buf_b'den okur
        cpu_reads = list(buf_b)
        corrupted = sum(1 for x in cpu_reads if x >= 100)
        
        return {
            "buffer_type": "DOUBLE_BUFFER",
            "read_values": cpu_reads,
            "corrupted_count": corrupted,
            "corruption_ratio": 0.0,
            "status": "PERFECT_ISOLATION"
        }

# Test ve Doğrulama
sim = BufferRaceConditionSimulator(buffer_size=16)
res_single = sim.simulate_single_buffer_race(dma_speed=2, cpu_speed=1)
res_double = sim.simulate_double_buffer()

print("[*] Tek Tampon vs Çift Tampon Veri Yarışı Analizi:")
print(f"  [!] Tek Tampon Okunan Veriler    : {res_single['read_values']}")
print(f"  [!] Tek Tampon Ezilen Bayt Sayısı: {res_single['corrupted_count']} / 16 (Bozulma: %{res_single['corruption_ratio']*100:.1f})")
print(f"  [+] Çift Tampon Okunan Veriler   : {res_double['read_values']}")
print(f"  [+] Çift Tampon Ezilme Sayısı    : {res_double['corrupted_count']} / 16 (Bozulma: %0.0 - MÜKEMMEL İZOLASYON)")

assert res_single["corrupted_count"] > 0, "Tek tamponda DMA CPU'yu ezmelidir!"
assert res_double["corrupted_count"] == 0, "Çift tamponda ezilme sıfır olmalıdır!"
print("\n[HÜCRE 6] Tek tampon veri yarışı ve çift tampon izolasyon modeli başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 175: Kod Bloğu 2 — C++20 STM32 DBM Donanımsal Çift Tampon Kontrolcü Simülasyonu
DMA_SxCR_DBM, Current Target (CT) Bayrak Otomasyonu ve M0AR/M1AR Geçiş Modeli
"""

from typing import List, Dict

class VirtualSTM32HardwareDBM:
    """STM32 Donanımsal Çift Tampon (DBM) Denetleyici Modeli"""
    def __init__(self, buffer_capacity: int = 4):
        self.capacity = buffer_capacity
        
        # Donanım Yazmaçları
        self.CR_EN = False
        self.CR_DBM = True
        self.CR_CT = 0  # 0: M0AR hedefleniyor, 1: M1AR hedefleniyor
        self.NDTR = buffer_capacity
        
        # Fiziksel Bellek Tamponları (M0AR ve M1AR)
        self.buffer_m0 = [0] * buffer_capacity
        self.buffer_m1 = [0] * buffer_capacity
        
        # Kesme Takibi
        self.tcif_count = 0
        self.history_log = []

    def start_dma(self):
        self.CR_EN = True
        self.CR_CT = 0
        self.NDTR = self.capacity

    def push_sample_from_peripheral(self, data_val: int) -> Dict[str, any]:
        """Çevre biriminden donanıma 1 veri darbesi geldiğinde çalışan silisyum mantığı"""
        if not self.CR_EN:
            return {"status": "DMA_OFF"}

        target_buf = self.buffer_m0 if self.CR_CT == 0 else self.buffer_m1
        write_idx = self.capacity - self.NDTR
        target_buf[write_idx] = data_val
        self.NDTR -= 1

        switched = False
        completed_buffer_id = None

        # Tampon bittiğinde donanımsal otomatik takas
        if self.NDTR == 0:
            self.tcif_count += 1
            completed_buffer_id = self.CR_CT # Dolan tampon
            
            # Donanım CT bitini tersler (0 -> 1 veya 1 -> 0)
            self.CR_CT = 1 if self.CR_CT == 0 else 0
            # Donanım NDTR'yi otomatik reload eder
            self.NDTR = self.capacity
            switched = True

        log_entry = {
            "val": hex(data_val),
            "written_to_m": completed_buffer_id if switched else self.CR_CT,
            "write_idx": write_idx,
            "new_ct": self.CR_CT,
            "switched": switched
        }
        self.history_log.append(log_entry)
        return log_entry

# Test: 8 Baytlık Veri Akışı ile DBM Testi (Kapasite = 4)
dbm = VirtualSTM32HardwareDBM(buffer_capacity=4)
dbm.start_dma()

input_stream = [0x10, 0x20, 0x30, 0x40, 0xA1, 0xA2, 0xA3, 0xA4]
for byte_in in input_stream:
    dbm.push_sample_from_peripheral(byte_in)

print("[*] STM32 Donanımsal Double Buffer Mode (DBM) Simülasyonu:")
print(f"  [+] Tampon 0 (M0AR) Verileri : {[hex(x) for x in dbm.buffer_m0]}")
print(f"  [+] Tampon 1 (M1AR) Verileri : {[hex(x) for x in dbm.buffer_m1]}")
print(f"  [+] Üretilen TC Kesmesi Sayısı: {dbm.tcif_count}")
print(f"  [+] Son Durumda Aktif CT Pini : {dbm.CR_CT} (DMA Şu An M{dbm.CR_CT}AR'a Yazıyor)")

# Doğrulamalar:
# İlk 4 bayt (0x10..0x40) Tampon 0'a gitmeli
assert dbm.buffer_m0 == [0x10, 0x20, 0x30, 0x40], "Tampon 0 ilk 4 baytı almalıydı!"
# İkinci 4 bayt (0xA1..0xA4) Tampon 1'e gitmeli
assert dbm.buffer_m1 == [0xA1, 0xA2, 0xA3, 0xA4], "Tampon 1 ikinci 4 baytı almalıydı!"
# 8 bayt bittiğinde 2 kez takas olmalı (tcif_count == 2)
assert dbm.tcif_count == 2, "2 tam tampon aktarımında 2 TC kesmesi oluşmalıydı!"

# 3. Tur Başlangıcı: 9. bayt M0'ın ilk indisine yazılmalı
dbm.push_sample_from_peripheral(0xEE)
assert dbm.buffer_m0[0] == 0xEE, "3. turda ilk bayt M0'a yazılmalıydı!"
print("\n[HÜCRE 8] STM32 donanımsal DBM kontrolcüsü ve CT bayrak geçişi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 175: Kod Bloğu 3 — Ping-Pong (HT/TC) Tampon Kesme ve Durum Makinesi Modeli
Circular DMA Üzerinde HT/TC Tetikleme, CPU Görev Kuyruğu ve Tampon Paylaşımı
"""

from typing import List, Dict

class PingPongCircularDmaManager:
    """Tek Büyük Tampon Üzerinde HT/TC Ping-Pong Yöneticisi"""
    def __init__(self, half_size: int = 8):
        self.half_size = half_size
        self.total_size = half_size * 2
        
        # 2N boyutlu tek bellek havuzu
        self.circular_buffer = [0] * self.total_size
        self.write_ptr = 0
        
        # CPU'ya gönderilen işleme emirleri
        self.cpu_work_orders = []

    def push_byte_stream(self, data_bytes: List[int]):
        for b in data_bytes:
            self.circular_buffer[self.write_ptr] = b
            self.write_ptr += 1
            
            # 1. Yarı Doldu: HTIF Tetiklenir
            if self.write_ptr == self.half_size:
                ping_slice = list(self.circular_buffer[0 : self.half_size])
                self.cpu_work_orders.append({
                    "event": "HTIF_HALF_TRANSFER",
                    "buffer_target": "PING_HALF_A",
                    "data": ping_slice,
                    "indices": (0, self.half_size - 1)
                })
                
            # 2. Yarı Doldu: TCIF Tetiklenir ve Başa Sarar
            elif self.write_ptr == self.total_size:
                pong_slice = list(self.circular_buffer[self.half_size : self.total_size])
                self.cpu_work_orders.append({
                    "event": "TCIF_TRANSFER_COMPLETE",
                    "buffer_target": "PONG_HALF_B",
                    "data": pong_slice,
                    "indices": (self.half_size, self.total_size - 1)
                })
                self.write_ptr = 0 # Circular wrap-around

# Test: 32 Baytlık Veri Akışı (Half Size = 8, Toplam = 16)
pp_mgr = PingPongCircularDmaManager(half_size=8)
test_stream = [i for i in range(32)]
pp_mgr.push_byte_stream(test_stream)

print("[*] Ping-Pong Circular DMA HT/TC Durum Makinesi Raporu:")
for idx, order in enumerate(pp_mgr.cpu_work_orders):
    print(f"  [+] İş Emri {idx+1}: {order['event']:<22} | Hedef: {order['buffer_target']} | Aralık: {order['indices']} | Veri: {order['data'][:4]}...")

# Doğrulamalar: 32 bayt akışta tam 2 tam tur atılmalı -> 2 HT, 2 TC (toplam 4 iş emri)
assert len(pp_mgr.cpu_work_orders) == 4, "32 bayt 4 adet yarı tampon iş emri üretmelidir!"
assert pp_mgr.cpu_work_orders[0]["buffer_target"] == "PING_HALF_A", "İlk iş emri PING olmalıdır!"
assert pp_mgr.cpu_work_orders[1]["buffer_target"] == "PONG_HALF_B", "İkinci iş emri PONG olmalıdır!"
assert pp_mgr.cpu_work_orders[0]["data"] == list(range(0, 8)), "İlk 8 bayt doğru iletilmelidir!"
assert pp_mgr.cpu_work_orders[1]["data"] == list(range(8, 16)), "İkinci 8 bayt doğru iletilmelidir!"
print("\n[HÜCRE 10] Ping-Pong HT/TC durum makinesi ve veri doğruluğu başarıyla onaylandı.")

# -*- coding: utf-8 -*-
"""
GÜN 175: Kod Bloğu 4 — WCET ve Deadline Aşımı Simülatörü (İşlem Süresi > Dolum Süresi Felaketi)
Tampon Dolum Hızı vs Algoritma Yürütme Süresi Analizi ve Overrun Tespiti
"""

from typing import Dict, List

class DoubleBufferTimingAnalyzer:
    """Çift Tampon Gerçek Zamanlı Zamanlama ve WCET Güvenlik Analizörü"""
    def __init__(self, mcu_clock_hz: int = 168_000_000):
        self.clock_hz = mcu_clock_hz

    def analyze_margin(self, sample_rate_hz: int, buffer_size: int, algorithm_cycles: int) -> Dict[str, any]:
        """
        sample_rate_hz   : Saniyede gelen örnek sayısı (ADC / Sensör hızı)
        buffer_size      : Bir tamponun örnek kapasitesi
        algorithm_cycles : CPU'nun tampon başına harcadığı saat çevrimi (WCET)
        """
        # 1. Tamponun dolma süresi (DMA fill time)
        t_fill_sec = buffer_size / sample_rate_hz
        
        # 2. CPU'nun algoritmayı tamamlama süresi
        t_process_sec = algorithm_cycles / self.clock_hz
        
        # 3. Yük oranı ve güvenlik marjı
        duty_ratio = t_process_sec / t_fill_sec
        safety_margin_sec = t_fill_sec - t_process_sec
        safety_margin_pct = (1.0 - duty_ratio) * 100.0
        
        is_deadline_missed = t_process_sec >= t_fill_sec

        status = "CRITICAL_OVERRUN" if is_deadline_missed else (
            "WARNING_LOW_MARGIN" if duty_ratio > 0.70 else "SAFE_REALTIME"
        )

        return {
            "sample_rate_hz": sample_rate_hz,
            "buffer_size": buffer_size,
            "t_fill_ms": round(t_fill_sec * 1000.0, 3),
            "t_process_ms": round(t_process_sec * 1000.0, 3),
            "duty_ratio": round(duty_ratio, 3),
            "safety_margin_pct": round(safety_margin_pct, 1),
            "is_overrun": is_deadline_missed,
            "status": status
        }

# Test: Farklı Algoritma Yüklerinde 100 kSPS Sensör Akışı
analyzer = DoubleBufferTimingAnalyzer(mcu_clock_hz=168_000_000)

scenarios = [
    ("Hafif Filtre (FIR)", 100_000, 1024, 200_000),      # 200k çevrim
    ("Orta Algoritma (FFT)", 100_000, 1024, 1_000_000),   # 1M çevrim
    ("Ağır Takip (Kalman)", 100_000, 1024, 1_400_000),   # 1.4M çevrim
    ("Aşırı Yük (ÇÖKÜŞ!)", 100_000, 1024, 2_000_000)     # 2M çevrim
]

print("[*] Double Buffering WCET ve Zaman Aşımı (Deadline) Güvenlik Matrisi:")
print(f"{'Algoritma Türü':<20} | {'Dolum (ms)':<11} | {'İşlem (ms)':<11} | {'Yük Oranı':<10} | {'Güvenlik Marjı':<15} | {'Durum':<15}")
print("-" * 92)

results = []
for name, s_rate, b_size, cyc in scenarios:
    res = analyzer.analyze_margin(s_rate, b_size, cyc)
    results.append(res)
    print(f"{name:<20} | {res['t_fill_ms']:<9.2f} ms | {res['t_process_ms']:<9.2f} ms | %{res['duty_ratio']*100:<8.1f} | %{res['safety_margin_pct']:<13.1f} | {res['status']:<15}")

# Doğrulamalar:
assert results[0]["status"] == "SAFE_REALTIME", "FIR filtre emniyetli olmalıdır!"
assert results[-1]["is_overrun"] is True, "2M çevrimlik aşırı yükte tampon taşması (overrun) olmalıdır!"
print("\n[HÜCRE 12] Double buffering WCET güvenlik analizi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 175: Kod Bloğu 5 — Aviyonik Termal Görüntüleme Akışında Kesintisiz DBM ve Hedef Takip Motoru
16 KB Kare Boyutlu FLIR Akışı, Donanımsal Tampon Takası ve Sıcak Nokta (Hotspot) Algılama
"""

from typing import List, Dict, Tuple

class FlirThermalCameraPipeline:
    """FLIR Termal Kamera DBM Alım ve Hedef Algılama Hattı"""
    def __init__(self, frame_size: int = 64): # Simülasyon için 64 piksellik küçük kareler
        self.frame_size = frame_size
        
        # Donanımsal İki Tampon (M0 ve M1)
        self.buffer_m0 = [0] * frame_size
        self.buffer_m1 = [0] * frame_size
        self.current_target = 0 # 0: M0, 1: M1
        
        self.processed_frames = []
        self.detected_hotspots = []

    def ingest_frame_via_dma(self, pixel_stream: List[int]) -> Dict[str, any]:
        """DMA gelen kareyi aktif tampona yazar ve bittiğinde CPU'ya işlettirir"""
        active_buf = self.buffer_m0 if self.current_target == 0 else self.buffer_m1
        
        for i in range(self.frame_size):
            active_buf[i] = pixel_stream[i]

        # Donanım takası gerçekleşti
        ready_buffer_id = self.current_target
        self.current_target = 1 if self.current_target == 0 else 0 # CT terslenir

        # CPU arka planda hazır olan izole tamponu işler (Hotspot Tespiti)
        buf_to_process = self.buffer_m0 if ready_buffer_id == 0 else self.buffer_m1
        hotspot = self._process_thermal_frame(buf_to_process, ready_buffer_id)

        return {
            "ingested_to_buffer": f"M{ready_buffer_id}AR",
            "next_dma_target": f"M{self.current_target}AR",
            "hotspot_found": hotspot is not None,
            "hotspot_coords": hotspot
        }

    def _process_thermal_frame(self, frame_data: List[int], buf_id: int) -> Tuple[int, int]:
        """Termal piksel değerlerinde 200'ün üzerindeki sıcak noktayı (hedefi) bulur"""
        self.processed_frames.append(buf_id)
        max_val = -1
        max_idx = -1
        for idx, p in enumerate(frame_data):
            if p > max_val:
                max_val = p
                max_idx = idx

        if max_val >= 200: # Hedef eşiği
            self.detected_hotspots.append((len(self.processed_frames), max_idx, max_val))
            return (max_idx, max_val)
        return None

# Test: 3 Ardışık Termal Kare (Kare 2'de Düşman Uçak Sıcak Motor İzi: Değer 255)
pipeline = FlirThermalCameraPipeline(frame_size=16)

frame_1 = [50 + i for i in range(16)] # Arka plan orman
frame_2 = [50] * 16; frame_2[7] = 255 # 7. pikselde jet motoru sıcaklığı!
frame_3 = [55 + i for i in range(16)] # Normal gökyüzü

r1 = pipeline.ingest_frame_via_dma(frame_1)
r2 = pipeline.ingest_frame_via_dma(frame_2)
r3 = pipeline.ingest_frame_via_dma(frame_3)

print("[*] FLIR Termal Görüntüleme DBM Kesintisiz Akış Raporu:")
print(f"  [+] Kare 1: Yazılan: {r1['ingested_to_buffer']} | Sonraki Hedef: {r1['next_dma_target']} | Hedef: {r1['hotspot_coords']}")
print(f"  [!] Kare 2: Yazılan: {r2['ingested_to_buffer']} | Sonraki Hedef: {r2['next_dma_target']} | Hedef: {r2['hotspot_coords']}")
print(f"  [+] Kare 3: Yazılan: {r3['ingested_to_buffer']} | Sonraki Hedef: {r3['next_dma_target']} | Hedef: {r3['hotspot_coords']}")

# Doğrulamalar:
assert r1["ingested_to_buffer"] == "M0AR" and r1["next_dma_target"] == "M1AR"
assert r2["ingested_to_buffer"] == "M1AR" and r2["next_dma_target"] == "M0AR"
assert r3["ingested_to_buffer"] == "M0AR" and r3["next_dma_target"] == "M1AR"
assert len(pipeline.detected_hotspots) == 1, "Kare 2'deki sıcak hedef tespit edilmelidir!"
assert pipeline.detected_hotspots[0][1] == 7, "Sıcak nokta 7. pikselde olmalıdır!"
print("\n[HÜCRE 14] Aviyonik FLIR DBM termal hedef takip motoru başarıyla onaylandı.")

# -*- coding: utf-8 -*-
"""
GÜN 175: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. Tek Tampon Veri Ezilmesi (Race Condition) vs Çift Tampon İzolasyonu
2. STM32 DBM Donanımsal Hedef Değişimi (CT: 0 -> 1 -> 0) ve CPU İcra Çizelgesi
3. İşlem Süresi (T_process) vs Dolum Süresi (T_fill) WCET Güvenlik Marjı
4. FLIR Termal Sensör Akışında Kesintisiz Kare Hızı (FPS) ve Hedef Tespit Başarımı
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
# PANEL 1: Tek Tampon Ezilme vs Çift Tampon İzolasyon Haritası
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

time_pts = np.linspace(0, 10, 200)

# Tek Tampon: CPU okurken DMA üstüne yazar
# 0..10 zamanında CPU indisi 0..100 ilerlerken DMA indisi 0..200 ilerler
cpu_idx_single = np.linspace(0, 100, 200)
dma_idx_single = np.linspace(0, 200, 200) % 100 # Başa sarar

ax1.plot(time_pts, cpu_idx_single, color=C_YELLOW, linewidth=2.0, label='Tek Tampon: CPU Okuma İndisi')
ax1.plot(time_pts, dma_idx_single, color=C_RED, linewidth=2.5, linestyle='--', label='Tek Tampon: DMA Yazma İndisi (Ezme!)')

# Çift Tampon: M0 ve M1 ayrımı
ax1.axhline(50, color='#64748B', linestyle=':', alpha=0.5)
ax1.text(0.5, 80, "TEK TAMPON FELAKETİ:\nDMA CPU'yu 2 kez ezdi (Torn Read!)", color=C_RED, fontweight='bold', fontsize=9,
         bbox=dict(boxstyle='round,pad=0.3', facecolor='#450A0A', edgecolor=C_RED))

ax1.set_xlabel("Zaman (ms)", color=C_WHITE, fontsize=10)
ax1.set_ylabel("Tampon İndis Konumu (Örnekler)", color=C_WHITE, fontsize=10)
ax1.set_title("Panel 1: Tek Tamponda Veri Yarışı (Race Condition) ve Bozulma", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax1.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 2: STM32 DBM Donanımsal Hedef Değişimi ve CPU İcrası
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

# 4 Zaman Aralığı (0..4 ms)
t_steps = np.arange(0, 5)
ct_values = [0, 1, 0, 1, 0] # Current Target

ax2.step(t_steps, ct_values, color=C_CYAN, where='post', linewidth=2.8, label='Donanımsal CT (Current Target: 0=M0, 1=M1)')

# Bölgelerin etiketlenmesi
ax2.fill_between([0, 1], [0, 0], [1, 1], color=C_GREEN, alpha=0.2, label='CPU M1 Okuyor | DMA M0 Yazıyor')
ax2.fill_between([1, 2], [0, 0], [1, 1], color=C_PURPLE, alpha=0.2, label='CPU M0 Okuyor | DMA M1 Yazıyor')
ax2.fill_between([2, 3], [0, 0], [1, 1], color=C_GREEN, alpha=0.2)
ax2.fill_between([3, 4], [0, 0], [1, 1], color=C_PURPLE, alpha=0.2)

ax2.set_yticks([0, 1])
ax2.set_yticklabels(['Hedef: M0AR', 'Hedef: M1AR'], color=C_WHITE, fontweight='bold', fontsize=9)
ax2.set_xlabel("Transfer Tamamlanma Fazları (TC Kesme Anları)", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: STM32 DBM Donanımsal CT Bayrağı ve Tampon Takas Döngüsü", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='center right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: WCET Güvenlik Marjı Analizi (T_process vs T_fill)
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

algorithms = ['Basit Ölçekleme', 'Sobel Kenar', '512-FFT', 'Kalman Filtresi', 'Ağır DNN (ÇÖKÜŞ)']
t_fill_const = 10.0 # 10 ms dolum süresi
t_process_vals = [2.1, 4.5, 6.8, 8.9, 13.5] # İşlem süreleri

x_pos = np.arange(len(algorithms))
bar_width = 0.45

colors = [C_GREEN, C_GREEN, C_YELLOW, C_YELLOW, C_RED]
bars = ax3.bar(x_pos, t_process_vals, width=bar_width, color=colors, label='İşlem Süresi T_process (ms)')

ax3.axhline(t_fill_const, color=C_RED, linestyle='--', linewidth=2.0, label='Maksimum Dolum Süresi T_fill (10.0 ms)')
ax3.axhspan(0, 7.0, color=C_GREEN, alpha=0.1, label='Güvenli Bölge (<%70 Marj)')
ax3.axhspan(7.0, 10.0, color=C_YELLOW, alpha=0.1, label='Kritik Bölge (%70 - %100)')
ax3.axhspan(10.0, 16.0, color=C_RED, alpha=0.15, label='OVERRUN (Taşma / Çöküş!)')

ax3.set_xticks(x_pos)
ax3.set_xticklabels(algorithms, color=C_WHITE, fontsize=9, fontweight='bold')
ax3.set_ylabel("Süre (Milisaniye - ms)", color=C_WHITE, fontsize=10)
ax3.set_title("Panel 3: Çift Tampon Algoritma WCET ve Taşma (Overrun) Sınırı", color=C_WHITE, fontsize=12, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B', axis='y')
ax3.legend(loc='upper left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

for bar, val in zip(bars, t_process_vals):
    ax3.text(bar.get_x() + bar.get_width()/2.0, val + 0.3, f"{val:.1f} ms",
             ha='center', va='bottom', color=C_WHITE, fontweight='bold', fontsize=8)

# ------------------------------------------------------------------------------
# PANEL 4: FLIR Termal Sensör Akışında Kesintisiz Kare Hızı (FPS)
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

frames = np.arange(1, 11)
# Çift Tampon: FPS sabit 60 FPS
fps_double = np.full(10, 60.0)
# Tek Tampon: Çakışma ve bekleme yüzünden FPS dalgalı ve düşük
fps_single = [60, 35, 20, 60, 25, 15, 60, 30, 20, 40]

ax4.plot(frames, fps_double, color=C_GREEN, marker='o', linewidth=2.5, label='Çift Tampon (DBM) - Sabit 60 FPS')
ax4.plot(frames, fps_single, color=C_RED, marker='x', linestyle=':', linewidth=2.0, label='Tek Tampon - Düşük / Dalgalı FPS (Kayıplı)')

ax4.set_xticks(frames)
ax4.set_xlabel("Termal Kare İndeksi", color=C_WHITE, fontsize=10)
ax4.set_ylabel("Kare Hızı (FPS)", color=C_WHITE, fontsize=10)
ax4.set_title("Panel 4: FLIR Termal Kamera Akışında Kare Hızı Kararlılığı", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax4.legend(loc='center right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')
ax4.set_ylim(0, 75)

plt.suptitle("GÜN 175: DMA Buffer ve Double Buffering Mimarisi Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_175_dma_buffer_ve_double_buffering.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_175\gun_175_dma_buffer_ve_double_buffering.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 175 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. Veri Yarışı Assertions
race_sim = BufferRaceConditionSimulator(buffer_size=16)
s_res = race_sim.simulate_single_buffer_race(dma_speed=2, cpu_speed=1)
d_res = race_sim.simulate_double_buffer()
assert s_res["corrupted_count"] > 0, "Tek tamponda veri yarışı gerçekleşmelidir!"
assert d_res["corrupted_count"] == 0, "Çift tamponda ezilme sıfır olmalıdır!"

# 3. STM32 Donanımsal DBM Assertions
hw_dbm = VirtualSTM32HardwareDBM(buffer_capacity=4)
hw_dbm.start_dma()
for val in [1, 2, 3, 4, 5, 6, 7, 8]:
    hw_dbm.push_sample_from_peripheral(val)
assert hw_dbm.buffer_m0 == [1, 2, 3, 4], "Tampon 0 ilk 4 baytı almalıdır!"
assert hw_dbm.buffer_m1 == [5, 6, 7, 8], "Tampon 1 ikinci 4 baytı almalıdır!"
assert hw_dbm.tcif_count == 2, "2 kez transfer tamamlandı kesmesi üretilmelidir!"

# 4. Ping-Pong HT/TC Assertions
pp_test = PingPongCircularDmaManager(half_size=8)
pp_test.push_byte_stream(list(range(16)))
assert len(pp_test.cpu_work_orders) == 2, "16 bayt 1 HT ve 1 TC üretmelidir!"
assert pp_test.cpu_work_orders[0]["event"] == "HTIF_HALF_TRANSFER"
assert pp_test.cpu_work_orders[1]["event"] == "TCIF_TRANSFER_COMPLETE"

# 5. WCET ve Deadline Assertions
timing = DoubleBufferTimingAnalyzer(mcu_clock_hz=168_000_000)
safe_run = timing.analyze_margin(100_000, 1024, 200_000)
overrun_run = timing.analyze_margin(100_000, 1024, 2_000_000)
assert safe_run["is_overrun"] is False, "200k çevrim güvenli marjda olmalıdır!"
assert overrun_run["is_overrun"] is True, "2M çevrim overrun hatası üretmelidir!"

# 6. FLIR Termal Pipeline Assertions
flir = FlirThermalCameraPipeline(frame_size=16)
f_hot = [10] * 16; f_hot[5] = 240
rep = flir.ingest_frame_via_dma(f_hot)
assert rep["hotspot_found"] is True, "Sıcak nokta tespit edilmelidir!"
assert rep["hotspot_coords"][0] == 5, "Sıcak nokta indisi 5 olmalıdır!"

print("\n[PASS] Gün 175: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
