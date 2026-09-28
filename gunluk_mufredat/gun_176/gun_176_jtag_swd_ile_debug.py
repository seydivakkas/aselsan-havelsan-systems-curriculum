

# ==============================================================================# -*- coding: utf-8 -*-
"""
GÜN 176: Kod Bloğu 1 — JTAG TAP State Machine vs SWD Paket Protokolü
Fiziksel Pin Sayısı, Saat Başına Verim, Paket Başlık Analizi ve Çift Yönlü İletişim
"""

from typing import List, Dict

class DebugProtocolComparator:
    """JTAG ve SWD Fiziksel Katman ve Protokol Verimlilik Karşılaştırıcısı"""
    def __init__(self):
        # Pin Sayıları
        self.jtag_pins = {"TCK", "TMS", "TDI", "TDO", "nTRST"} # 4-5 pin
        self.swd_pins = {"SWCLK", "SWDIO"} # 2 pin (+1 SWO opsiyonel)

    def simulate_swd_write_packet(self, ap_ndp: int, address: int, data_val: int) -> Dict[str, any]:
        """
        SWD Yazma Paketi (ARM Debug Interface v5):
        1. Request Header (8-bit): Start(1), APnDP(1), RnW(0=Write), A[2:3], Parity, Stop(0), Park(1)
        2. Turnaround (Trn): 1 çevrim yön değişimi
        3. Acknowledge (3-bit): OK (0b001)
        4. Turnaround (Trn): 1 çevrim yön değişimi
        5. Data (32-bit): LSB-first veri
        6. Parity (1-bit): Veri paritesi
        """
        header_bits = 8
        trn_1_bits = 1
        ack_bits = 3
        trn_2_bits = 1
        data_bits = 32
        parity_bits = 1
        
        total_clock_cycles = header_bits + trn_1_bits + ack_bits + trn_2_bits + data_bits + parity_bits
        effective_payload_ratio = data_bits / total_clock_cycles

        return {
            "protocol": "SWD",
            "pin_count": 2,
            "total_cycles": total_clock_cycles, # 46 çevrim
            "payload_bits": data_bits,
            "efficiency_ratio": round(effective_payload_ratio, 3),
            "ack_status": "OK (0b001)"
        }

    def simulate_jtag_write_packet(self, data_val: int) -> Dict[str, any]:
        """
        JTAG Yazma İşlemi (TAP State Machine Geçişleri):
        Test-Logic-Reset -> Run-Test/Idle -> Select-DR-Scan -> Capture-DR -> Shift-DR -> Update-DR
        TMS hareketleri + 35 bit Shift-DR (32-bit veri + 3-bit komut)
        """
        tap_transition_cycles = 6
        shift_dr_cycles = 35
        update_cycles = 2
        total_cycles = tap_transition_cycles + shift_dr_cycles + update_cycles
        effective_payload_ratio = 32 / total_cycles

        return {
            "protocol": "JTAG",
            "pin_count": 5,
            "total_cycles": total_cycles,
            "payload_bits": 32,
            "efficiency_ratio": round(effective_payload_ratio, 3),
            "state": "UPDATE_DR_COMPLETE"
        }

# Simülasyon ve Karşılaştırma
comp = DebugProtocolComparator()
swd_res = comp.simulate_swd_write_packet(ap_ndp=1, address=0x20000000, data_val=0xDEADBEEF)
jtag_res = comp.simulate_jtag_write_packet(data_val=0xDEADBEEF)

print("[*] JTAG vs SWD Protokol ve Donanım Karşılaştırması:")
print(f"  [+] JTAG: {jtag_res['pin_count']} Pin Kullanımı | Toplam Çevrim: {jtag_res['total_cycles']} | Verimlilik: %{jtag_res['efficiency_ratio']*100:.1f}")
print(f"  [+] SWD : {swd_res['pin_count']} Pin Kullanımı | Toplam Çevrim: {swd_res['total_cycles']} | Verimlilik: %{swd_res['efficiency_ratio']*100:.1f}")
print(f"  [+] Pin Tasarrufu: %{(1 - swd_res['pin_count'] / jtag_res['pin_count']) * 100:.0f} daha az pin!")

# Doğrulamalar
assert swd_res["pin_count"] == 2, "SWD 2 pin kullanmalıdır!"
assert jtag_res["pin_count"] == 5, "JTAG 5 pin gerektirmelidir!"
assert swd_res["total_cycles"] == 46, "Standart SWD 32-bit yazma işlemi 46 saat çevrimi sürmelidir!"
print("\n[HÜCRE 6] JTAG vs SWD protokol ve pin verimlilik analizi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 176: Kod Bloğu 2 — CoreSight MEM-AP Bellek ve Yazmaç Canlı Erişim Simülatörü
CPU Durdurulmadan SRAM Okuma/Yazma, TAR/DRW Yazmaçları ve Canlı Değişken İzleme
"""

from typing import Dict, List

class CoreSightMemApSimulator:
    """CoreSight Memory Access Port (MEM-AP) Donanımsal Model"""
    def __init__(self):
        # MEM-AP Yazmaçları
        self.CSW = 0x23000052 # Control/Status Word (32-bit erişim, otomatik artırım)
        self.TAR = 0x00000000 # Transfer Address Register
        self.DRW = 0x00000000 # Data Read/Write Register
        
        # Simüle Edilen Mikrodenetleyici SRAM Belleği (0x20000000 tabanlı)
        self.sram = {
            0x20000000: 0x12345678, # Telemetri Sayacı
            0x20000004: 0x00000042, # Hedef Tehdit Seviyesi
            0x20000008: 0xDEADBEEF  # Kritik Sistem Bayrağı
        }

    def write_memory_word(self, address: int, value: int):
        """Debug probu TAR'a adresi, DRW'ye veriyi yazar; MEM-AP veriyi SRAM'e basar"""
        self.TAR = address
        self.DRW = value
        self.sram[address] = value

    def read_memory_word(self, address: int) -> int:
        """CPU çalışırken arka planda SRAM'den kelime okuma (Non-intrusive Live Read)"""
        self.TAR = address
        val = self.sram.get(address, 0x00000000)
        self.DRW = val
        return val

# Test: Uçuş Bilgisayarı Çalışırken Canlı Telemetri Okuma ve Parametre Enjeksiyonu
mem_ap = CoreSightMemApSimulator()

# 1. Canlı Değişken Okuma (CPU durdurulmadan)
val_counter = mem_ap.read_memory_word(0x20000000)
val_threat = mem_ap.read_memory_word(0x20000004)

print("[*] CoreSight MEM-AP Canlı Bellek (Live Watch) İnceleme Raporu:")
print(f"  [+] Adres 0x20000000 (Telemetri) : 0x{val_counter:08X}")
print(f"  [+] Adres 0x20000004 (Tehdit)    : 0x{val_threat:08X} (Seviye 42)")

# 2. Canlı Parametre Enjeksiyonu (Savaş anında hedef koordinatı güncelleme)
mem_ap.write_memory_word(0x20000004, 0x00000099) # Tehdit seviyesini 99 yap
updated_threat = mem_ap.read_memory_word(0x20000004)
print(f"  [!] Canlı Enjeksiyon Sonrası     : 0x{updated_threat:08X} (Yeni Seviye 99)")

# Doğrulamalar:
assert val_counter == 0x12345678, "İlk okunan telemetri doğru olmalıdır!"
assert updated_threat == 0x00000099, "Enjekte edilen değer başarıyla güncellenmelidir!"
assert mem_ap.TAR == 0x20000004, "TAR son erişilen adresi tutmalıdır!"
print("\n[HÜCRE 8] CoreSight MEM-AP canlı bellek erişim modeli başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 176: Kod Bloğu 3 — Donanımsal FPB Breakpoint ve DWT Watchpoint Tetikleme Motoru
FPB Karşılaştırıcı Sayısı (Max 6), DWT Adres Tetikleme ve CPU Halt Simülasyonu
"""

from typing import List, Dict, Optional

class HardwareBreakpointWatchpointEngine:
    """ARM Cortex-M FPB (Breakpoint) ve DWT (Watchpoint) Donanım Motoru"""
    def __init__(self, max_hw_breakpoints: int = 6, max_watchpoints: int = 4):
        self.max_bp = max_hw_breakpoints
        self.max_wp = max_watchpoints
        
        # Donanım Yuvaları (Slots)
        self.active_breakpoints = {} # slot_id -> pc_address
        self.active_watchpoints = {}  # slot_id -> (data_address, access_type)

    def set_hardware_breakpoint(self, address: int) -> Dict[str, any]:
        if len(self.active_breakpoints) >= self.max_bp:
            return {"success": False, "error": "EXCEEDED_MAX_HARDWARE_BREAKPOINTS (Max 6!)"}
        
        slot_id = len(self.active_breakpoints)
        self.active_breakpoints[slot_id] = address
        return {"success": True, "slot": slot_id, "address": hex(address)}

    def set_data_watchpoint(self, address: int, access_type: str = "WRITE") -> Dict[str, any]:
        if len(self.active_watchpoints) >= self.max_wp:
            return {"success": False, "error": "EXCEEDED_MAX_WATCHPOINTS"}
        
        slot_id = len(self.active_watchpoints)
        self.active_watchpoints[slot_id] = (address, access_type)
        return {"success": True, "slot": slot_id, "address": hex(address), "type": access_type}

    def check_instruction_fetch(self, current_pc: int) -> bool:
        """CPU her komut çektiğinde FPB karşılaştırıcı kontrolü"""
        return current_pc in self.active_breakpoints.values()

    def check_memory_access(self, mem_addr: int, access_type: str) -> bool:
        """CPU belleğe okuma/yazma yaptığında DWT karşılaştırıcı kontrolü"""
        for slot, (addr, a_type) in self.active_watchpoints.items():
            if addr == mem_addr and (a_type == access_type or a_type == "READ_WRITE"):
                return True
        return False

# Test: 6 Breakpoint Limiti ve DWT Bellek Tetikleme
engine = HardwareBreakpointWatchpointEngine()

# 1. Breakpoint Atamaları (İlk 6'sı başarılı, 7.'si başarısız olmalı!)
bp_results = []
for i in range(7):
    res = engine.set_hardware_breakpoint(0x08001000 + i * 4)
    bp_results.append(res)

print("[*] ARM Cortex-M FPB Donanımsal Breakpoint Kapasite Testi:")
print(f"  [+] 1..6. Breakpoint Atamaları : Başarılı ({len(engine.active_breakpoints)} adet aktif)")
print(f"  [!] 7. Breakpoint Ataması      : {bp_results[-1]['error']}")

# 2. DWT Watchpoint ile Bozuk Bellek Yakalama
engine.set_data_watchpoint(0x20000050, access_type="WRITE")

# Normal bellek yazımı (tetiklenmemeli)
hit_normal = engine.check_memory_access(0x20000010, "WRITE")
# Kritik değişken yazımı (DWT tetiklemeli!)
hit_critical = engine.check_memory_access(0x20000050, "WRITE")

print("[*] DWT Bellek Nöbetçisi (Watchpoint) Testi:")
print(f"  [+] Adres 0x20000010 Yazımı : Tetikleme: {hit_normal} (Güvenli)")
print(f"  [!] Adres 0x20000050 Yazımı : Tetikleme: {hit_critical} (YAKALANDI! CPU HALT)")

# Doğrulamalar:
assert bp_results[5]["success"] is True, "6. breakpoint kabul edilmelidir!"
assert bp_results[6]["success"] is False, "7. breakpoint donanım sınırı yüzünden reddedilmelidir!"
assert hit_normal is False, "Farklı adreste tetikleme olmamalıdır!"
assert hit_critical is True, "İzlenen adrese yazıldığında CPU durdurulmalıdır!"
print("\n[HÜCRE 10] FPB breakpoint limitleri ve DWT nöbetçi motoru başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 176: Kod Bloğu 4 — Heisenbug Simülasyonu: Intrusive printf vs Non-Intrusive Trace
Zaman Aşımı Bozulması, Debug Açıkken Hatanın Kaybolması (Heisenbug) ve Trace Verimi
"""

from typing import Dict, List

class HeisenbugRaceConditionSimulator:
    """Debug Yükünün Gerçek Zamanlı Yarış Durumlarını Maskeleme (Heisenbug) Simülatörü"""
    def __init__(self):
        # 100 kHz Sensör Veri Bütçesi: Her 10 mikrosaniyede 1 örnek
        self.deadline_us = 10.0

    def simulate_production_run(self) -> Dict[str, any]:
        """Üretim Modu (Debug Yok): İki thread arasındaki gerçek yarış durumu"""
        sensor_arrival_us = 8.0 # Veri 8. mikrosaniyede hazır
        deadline_us = self.deadline_us
        
        # Algoritma 9. mikrosaniyede bitiyor (Zamanında yetişti)
        success = sensor_arrival_us < deadline_us
        return {
            "mode": "PRODUCTION_NO_DEBUG",
            "execution_us": sensor_arrival_us,
            "deadline_us": deadline_us,
            "missed_deadline": not success,
            "bug_manifested": False
        }

    def simulate_printf_debug_run(self, message_len: int = 20) -> Dict[str, any]:
        """Hatalı Yaklaşım: Araya UART printf() eklenmiş debug modu (Intrusive)"""
        # 115200 baud UART: 1 bayt ~86.8 us!
        printf_delay_us = message_len * 86.8 # 20 bayt = 1736 us!
        total_time_us = 8.0 + printf_delay_us
        
        # printf yüzünden deadline feci şekilde patladı!
        missed = total_time_us > self.deadline_us
        return {
            "mode": "PRINTF_DEBUG",
            "execution_us": round(total_time_us, 1),
            "deadline_us": self.deadline_us,
            "missed_deadline": missed,
            "delay_penalty_factor": round(total_time_us / 8.0, 1),
            "bug_manifested": True # printf yüzünden sistem çöktü!
        }

    def simulate_swd_rtt_debug_run(self) -> Dict[str, any]:
        """Doğru Yaklaşım: SEGGER RTT / ITM Trace ile Non-Intrusive İzleme"""
        # RAM'e memcpy: 20 bayt ~0.15 us
        rtt_delay_us = 0.15
        total_time_us = 8.0 + rtt_delay_us
        missed = total_time_us > self.deadline_us
        
        return {
            "mode": "SWD_RTT_NON_INTRUSIVE",
            "execution_us": round(total_time_us, 2),
            "deadline_us": self.deadline_us,
            "missed_deadline": missed,
            "delay_penalty_factor": round(total_time_us / 8.0, 3),
            "bug_manifested": False # Sistem deterministik çalışmaya devam etti!
        }

# Simülasyon ve Heisenbug Tespiti
hb = HeisenbugRaceConditionSimulator()
res_prod = hb.simulate_production_run()
res_printf = hb.simulate_printf_debug_run(message_len=20)
res_rtt = hb.simulate_swd_rtt_debug_run()

print("[*] Heisenbug ve Debug İntrusiveness Analizi:")
print(f"  [+] Üretim Modu (Logsuz)   : Süre: {res_prod['execution_us']} us | Deadline: {res_prod['deadline_us']} us | Çöküş: {res_prod['bug_manifested']}")
print(f"  [!] UART printf() Modu    : Süre: {res_printf['execution_us']} us | Ceza: {res_printf['delay_penalty_factor']}x YAVAŞ | Çöküş: {res_printf['bug_manifested']} (HEISENBUG!)")
print(f"  [+] SWD RTT Non-Intrusive : Süre: {res_rtt['execution_us']} us | Ceza: {res_rtt['delay_penalty_factor']}x | Çöküş: {res_rtt['bug_manifested']} (GÜVENLİ)")

# Doğrulamalar:
assert res_printf["missed_deadline"] is True, "printf deadline'ı patlatmalıdır!"
assert res_rtt["missed_deadline"] is False, "RTT deadline içinde kalmalıdır!"
assert res_printf["execution_us"] > 1000.0, "20 bayt printf 1 milisaniyeden fazla sürmelidir!"
print("\n[HÜCRE 12] Heisenbug ve non-intrusive trace zamanlama modeli başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 176: Kod Bloğu 5 — HardFault Kayıt Çözümleyici ve Stack Frame Unwinder
SCB->CFSR, HFSR, BFAR/MMFAR Analizi ve Donanımsal Stack Çözümleme (Root-Cause Extraction)
"""

from typing import Dict, List

class CortexMHardFaultAnalyzer:
    """ARM Cortex-M HardFault SCB ve Stack Frame Adli Tıp (Forensic) Analizörü"""
    def __init__(self):
        pass

    def decode_cfsr(self, cfsr_val: int) -> Dict[str, any]:
        """
        CFSR (0xE000ED28) Bit Analizi:
        - MMSR (Bits 7:0)   : MemManage Faults (IACCVIOL, DACCVIOL, MUNSTKERR, MSTKERR, MMARVALID)
        - BFSR (Bits 15:8)  : Bus Faults (IBUSERR, PRECISERR, IMPRECISERR, BFARVALID)
        - UFSR (Bits 31:16) : Usage Faults (UNDEFINSTR, INVSTATE, INVPC, NOCP, UNALIGNED, DIVBYZERO)
        """
        mmsr = cfsr_val & 0xFF
        bfsr = (cfsr_val >> 8) & 0xFF
        ufsr = (cfsr_val >> 16) & 0xFFFF

        causes = []
        if ufsr & (1 << 9):
            causes.append("DIVBYZERO (Sıfıra Bölme Hatası!)")
        if ufsr & (1 << 8):
            causes.append("UNALIGNED (Hizasız Bellek Erişimi)")
        if ufsr & (1 << 0):
            causes.append("UNDEFINSTR (Tanımsız Makine Kodu / Bozuk Flash)")
        if bfsr & (1 << 1):
            causes.append("PRECISERR (Kesin Bus Hatası - Geçersiz Adres Erişimi)")
        if mmsr & (1 << 1):
            causes.append("DACCVIOL (MPU Veri Erişim İhlali)")

        return {
            "cfsr_raw": hex(cfsr_val),
            "mmsr": hex(mmsr),
            "bfsr": hex(bfsr),
            "ufsr": hex(ufsr),
            "detected_causes": causes
        }

    def unwind_hardware_stack_frame(self, stack_bytes: List[int]) -> Dict[str, any]:
        """
        Cortex-M Donanımsal Auto-Stacking Sırası (8 Kelime = 32 Bayt):
        SP+0 : R0
        SP+4 : R1
        SP+8 : R2
        SP+12: R3
        SP+16: R12
        SP+20: LR  (Link Register - Fonksiyon dönüş adresi)
        SP+24: PC  (Program Counter - ÇÖKEN KOMUTUN ADRESİ!)
        SP+28: xPSR
        """
        if len(stack_bytes) < 8:
            return {"error": "INSUFFICIENT_STACK_WORDS"}

        return {
            "R0": hex(stack_bytes[0]),
            "R1": hex(stack_bytes[1]),
            "R2": hex(stack_bytes[2]),
            "R3": hex(stack_bytes[3]),
            "R12": hex(stack_bytes[4]),
            "LR": hex(stack_bytes[5]),
            "PC_FAULT_ADDR": hex(stack_bytes[6]), # Kritik: Çöken satır!
            "xPSR": hex(stack_bytes[7])
        }

# Test: Uçuş Bilgisayarında Sıfıra Bölme ve Bus Hatası Olayı
analyzer = CortexMHardFaultAnalyzer()

# CFSR: DIVBYZERO (Bit 25 = 1 << 9 in UFSR) + PRECISERR (Bit 9 = 1 << 1 in BFSR)
# UFSR = 0x0200, BFSR = 0x02 -> CFSR = 0x02000200
test_cfsr = 0x02000200
decoded_fault = analyzer.decode_cfsr(test_cfsr)

# Donanımın stack'e kaydettiği register değerleri
simulated_stack = [
    0x00000000, # R0: Bölen sayı (0!)
    0x00000064, # R1: Bölünen (100)
    0x20001000, # R2
    0x00000000, # R3
    0x00000001, # R12
    0x08002151, # LR: Çağıran fonksiyon adresi
    0x080034AC, # PC: ÇÖKEN KOMUTUN ADRESİ (calculate_flight_trajectory + 0x14)
    0x61000000  # xPSR
]

unwound_frame = analyzer.unwind_hardware_stack_frame(simulated_stack)

print("[*] Aviyonik Uçuş Kontrolcüsü HardFault Kök Neden Analiz Raporu:")
print(f"  [!] CFSR Çözümleme      : {decoded_fault['detected_causes']}")
print(f"  [+] Çöken Fonksiyon (PC): {unwound_frame['PC_FAULT_ADDR']} (calculate_flight_trajectory)")
print(f"  [+] Çağıran Adres (LR)  : {unwound_frame['LR']}")
print(f"  [!] Hatalı Parametre R0 : {unwound_frame['R0']} (Sıfır Değeri Tespiti!)")

# Doğrulamalar:
assert "DIVBYZERO (Sıfıra Bölme Hatası!)" in decoded_fault["detected_causes"]
assert "PRECISERR (Kesin Bus Hatası - Geçersiz Adres Erişimi)" in decoded_fault["detected_causes"]
assert unwound_frame["PC_FAULT_ADDR"] == "0x80034ac"
assert unwound_frame["R0"] == "0x0"
print("\n[HÜCRE 14] HardFault CFSR çözücü ve Stack Unwinder adli tıp motoru başarıyla onaylandı.")

# -*- coding: utf-8 -*-
"""
GÜN 176: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. JTAG (5 Pin) vs SWD (2 Pin) Protokol ve Donanım Pin Verimliliği
2. ARM CoreSight FPB Donanımsal Breakpoint ve DWT Watchpoint Mimarisi
3. Heisenbug Etkisi: Intrusive UART printf Gecikmesi vs Non-Intrusive RTT Zamanlaması
4. Uçuş Kontrolcüsü HardFault Adli Bilişim (Forensics) ve Yığın Çözümleme
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
# PANEL 1: JTAG vs SWD Pin Sayısı ve Verim Karşılaştırması
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

categories = ['Pin Sayısı (Adet)', 'Veri Yolu Hatları', 'Saat Başına Verim (%)', 'Kullanılan Alan (%)']
jtag_metrics = [5, 4, 32/43*100, 100]
swd_metrics  = [2, 1, 32/46*100, 40]

x = np.arange(len(categories))
bar_width = 0.35

ax1.bar(x - bar_width/2, jtag_metrics, width=bar_width, color=C_RED, label='JTAG (IEEE 1149.1)')
ax1.bar(x + bar_width/2, swd_metrics, width=bar_width, color=C_GREEN, label='SWD (Serial Wire Debug)')

ax1.set_xticks(x)
ax1.set_xticklabels(categories, color=C_WHITE, fontsize=9, fontweight='bold')
ax1.set_ylabel("Değer / Yüzde Oranı", color=C_WHITE, fontsize=10)
ax1.set_title("Panel 1: JTAG vs SWD Donanım Pin Sayısı ve Protokol Verimliliği", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B', axis='y')
ax1.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

ax1.text(0.5, 80, "SWD: %60 Pin Tasarrufu!\n(Yalnızca SWDIO ve SWCLK)", color=C_GREEN, fontweight='bold', fontsize=9,
         bbox=dict(boxstyle='round,pad=0.3', facecolor='#064E3B', edgecolor=C_GREEN))

# ------------------------------------------------------------------------------
# PANEL 2: FPB Breakpoint ve DWT Watchpoint Dağılımı
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

slots = [f"FPB_COMP{i}" for i in range(6)] + ['7. Breakpoint\n(REDDEDİLDİ!)', 'DWT_COMP0\n(Watchpoint)']
status = [1, 1, 1, 1, 1, 1, 0, 1] # 1: Aktif, 0: Donanım Sınırı
colors = [C_CYAN]*6 + [C_RED] + [C_YELLOW]

bars = ax2.bar(slots, [1]*8, color=colors, width=0.55)
ax2.set_yticks([0, 1])
ax2.set_yticklabels(['Boş / Red', 'Donanımsal Aktif'], color=C_WHITE, fontweight='bold', fontsize=9)
ax2.set_title("Panel 2: Cortex-M4 FPB Karşılaştırıcı Limitleri (Maksimum 6 Breakpoint)", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B', axis='y')

# Vurgular
ax2.annotate("Donanımsal Limit!\nFlash'ta 7. Breakpoint Konamaz", xy=(6, 0.5), xytext=(4.5, 0.75),
             color=C_RED, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_RED, arrowstyle="->"))

# ------------------------------------------------------------------------------
# PANEL 3: Heisenbug: UART printf vs SWD RTT Gecikme Analizi
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

msg_sizes = np.array([5, 10, 20, 50, 100]) # Bayt cinsinden log uzunluğu
# 115200 baud UART: Bayt başına 86.8 us
uart_times_us = msg_sizes * 86.8
# SEGGER RTT: RAM kopyalama ~0.01 us/bayt + 0.1 us sabit
rtt_times_us = msg_sizes * 0.01 + 0.1

ax3.plot(msg_sizes, uart_times_us, color=C_RED, marker='o', linewidth=2.5, label='UART printf() - Aşırı Yavaş (Heisenbug Riski)')
ax3.plot(msg_sizes, rtt_times_us, color=C_GREEN, marker='s', linewidth=2.5, label='SEGGER RTT / ITM - Non-Intrusive (<1 µs)')

ax3.axhline(50.0, color=C_YELLOW, linestyle=':', label='Kritik Gerçek Zamanlı Deadline Eşiği (50 µs)')

ax3.set_yscale('log')
ax3.set_xlabel("Log Mesajı Boyutu (Bayt)", color=C_WHITE, fontsize=10)
ax3.set_ylabel("CPU Kilitlenme Süresi (µs, Log Ölçek)", color=C_WHITE, fontsize=10)
ax3.set_title("Panel 3: Heisenbug Riski: UART printf() Gecikmesi vs Non-Intrusive RTT", color=C_WHITE, fontsize=12, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax3.legend(loc='center left', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 4: HardFault Adli Bilişim (Forensics) Stack Frame
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

registers = ['xPSR', 'PC (Çöken Satır)', 'LR (Dönüş)', 'R12', 'R3', 'R2', 'R1', 'R0 (Parametre)']
reg_values = ['0x61000000', '0x080034AC', '0x08002151', '0x00000001', '0x00000000', '0x20001000', '0x00000064', '0x00000000']
bar_colors = [C_PURPLE, C_RED, C_YELLOW, C_CYAN, C_CYAN, C_CYAN, C_CYAN, C_RED]

y_pos = np.arange(len(registers))
ax4.barh(y_pos, [1]*8, color=bar_colors, height=0.6)

for idx, (reg, val) in enumerate(zip(registers, reg_values)):
    ax4.text(0.05, idx, f"{reg:<18} : {val}", va='center', color=C_WHITE, fontweight='bold', fontsize=9)

ax4.set_yticks([])
ax4.set_xticks([])
ax4.set_title("Panel 4: Aviyonik HardFault Stack Unwinding (Kök Neden: PC & R0=0)", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.grid(False)

plt.suptitle("GÜN 176: JTAG/SWD ile Hata Ayıklama (Debug) ve ARM CoreSight Mimarisi Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_176_jtag_swd_ile_debug.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_176\gun_176_jtag_swd_ile_debug.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 176 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. JTAG vs SWD Protokol Assertions
comp_test = DebugProtocolComparator()
sw_t = comp_test.simulate_swd_write_packet(1, 0x20000000, 0x1234)
assert sw_t["pin_count"] == 2, "SWD 2 pinli olmalıdır!"
assert sw_t["total_cycles"] == 46, "SWD 32-bit transfer 46 çevrim sürmelidir!"

# 3. CoreSight MEM-AP Assertions
mem_sim = CoreSightMemApSimulator()
mem_sim.write_memory_word(0x20000000, 0xCAFEBABE)
assert mem_sim.read_memory_word(0x20000000) == 0xCAFEBABE, "MEM-AP okuma/yazma tutarlı olmalıdır!"

# 4. FPB Breakpoint ve DWT Watchpoint Assertions
eng_test = HardwareBreakpointWatchpointEngine()
for i in range(6):
    assert eng_test.set_hardware_breakpoint(0x08000000 + i*4)["success"] is True
assert eng_test.set_hardware_breakpoint(0x08000020)["success"] is False, "7. breakpoint reddedilmelidir!"

eng_test.set_data_watchpoint(0x20000080, "WRITE")
assert eng_test.check_memory_access(0x20000080, "WRITE") is True, "Watchpoint tetiklenmelidir!"
assert eng_test.check_memory_access(0x20000080, "READ") is False, "Sadece WRITE izlenmelidir!"

# 5. Heisenbug Zamanlama Assertions
hb_test = HeisenbugRaceConditionSimulator()
p_run = hb_test.simulate_printf_debug_run(20)
r_run = hb_test.simulate_swd_rtt_debug_run()
assert p_run["missed_deadline"] is True, "printf deadline'ı bozmalıdır!"
assert r_run["missed_deadline"] is False, "RTT deadline içinde kalmalıdır!"

# 6. HardFault Çözümleme Assertions
hf_test = CortexMHardFaultAnalyzer()
dec = hf_test.decode_cfsr(0x02000200)
assert "DIVBYZERO (Sıfıra Bölme Hatası!)" in dec["detected_causes"]
unwound = hf_test.unwind_hardware_stack_frame([0, 10, 0, 0, 0, 0x08001000, 0x08002000, 0x01000000])
assert unwound["PC_FAULT_ADDR"] == "0x8002000", "PC adresi doğru çıkarılmalıdır!"

print("\n[PASS] Gün 176: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
