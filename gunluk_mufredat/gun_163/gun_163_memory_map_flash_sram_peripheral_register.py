# -*- coding: utf-8 -*-
"""
GÜN 163: STM32 Bellek Haritası (Memory Map), Flash, SRAM ve Çevresel Yazmaç (Peripheral Register) Mimarisi
Otomatik Oluşturulan Çalıştırılabilir Python Betiği
"""

# -*- coding: utf-8 -*-
"""
GÜN 163: Kod Bloğu 1 — STM32 4 GB Düzlemsel Bellek Haritası ve MMIO Register Motoru
"""

from typing import Dict, Any, Tuple
import struct

class Stm32MemoryMapEngine:
    """
    STM32 4 GB Adres Uzayı Simülatörü:
    - FLASH      : 0x08000000 - 0x081FFFFF (2 MB)
    - SRAM       : 0x20000000 - 0x2001FFFF (128 KB)
    - PERIPHERALS: 0x40000000 - 0x5FFFFFFF
    - SYSTEM     : 0xE0000000 - 0xE000EDEF (NVIC, SCB, SysTick)
    """
    FLASH_BASE  = 0x08000000
    FLASH_SIZE  = 2 * 1024 * 1024       # 2 MB Flash
    SRAM_BASE   = 0x20000000
    SRAM_SIZE   = 128 * 1024            # 128 KB SRAM
    PERIPH_BASE = 0x40000000
    PERIPH_SIZE = 512 * 1024 * 1024     # 512 MB Periph Uzayı
    SYSTEM_BASE = 0xE0000000
    SYSTEM_SIZE = 1 * 1024 * 1024       # 1 MB Dahili Cortex

    def __init__(self):
        # Bellek Havuzları
        self.flash_memory = bytearray(self.FLASH_SIZE)
        self.sram_memory = bytearray(self.SRAM_SIZE)
        self.periph_registers: Dict[int, int] = {} # 32-bit MMIO Yazmaçları
        self.system_registers: Dict[int, int] = {}

        # Reset Durumu
        self._init_default_vectors()

    def _init_default_vectors(self):
        """Vektör Tablosunun İlk İki 32-bit Değeri: İlk SP ve Reset Handler"""
        initial_sp = self.SRAM_BASE + self.SRAM_SIZE # 0x20020000 (RAM Sonu)
        reset_handler = 0x08000101                   # Thumb Bit = 1

        # Flash'ın başlangıcına (0x08000000) yaz
        struct.pack_into("<I", self.flash_memory, 0, initial_sp)
        struct.pack_into("<I", self.flash_memory, 4, reset_handler)

    def write32(self, address: int, value: int):
        """32-bit Değer Yazma (Fiziksel Bus Hatlarını Taklit Eder)"""
        # 4 baytlık hizalama denetimi (Alignment Check)
        if address % 4 != 0:
            raise ValueError(f"UNALIGNED ACCESS FAULT: 0x{address:08X} adresi 4 bayta hizalı değil!")

        value &= 0xFFFFFFFF

        # 1. SRAM Erişimi
        if self.SRAM_BASE <= address < self.SRAM_BASE + self.SRAM_SIZE:
            offset = address - self.SRAM_BASE
            struct.pack_into("<I", self.sram_memory, offset, value)
            return

        # 2. Flash Erişimi (Normal RAM gibi yazılamaz!)
        if self.FLASH_BASE <= address < self.FLASH_BASE + self.FLASH_SIZE:
            raise PermissionError(f"FLASH WRITE FAULT: 0x{address:08X} Flash salt okunurdur! Sektör silinmeden yazılamaz!")

        # 3. Çevresel Birimler (MMIO)
        if self.PERIPH_BASE <= address < self.PERIPH_BASE + self.PERIPH_SIZE:
            self.periph_registers[address] = value
            return

        # 4. Sistem Birimleri (NVIC, SCB)
        if self.SYSTEM_BASE <= address < self.SYSTEM_BASE + self.SYSTEM_SIZE:
            self.system_registers[address] = value
            return

        raise MemoryError(f"BUS FAULT: 0x{address:08X} tanımlanmamış / rezerve bellek alanına erişim!")

    def read32(self, address: int) -> int:
        """32-bit Değer Okuma"""
        if address % 4 != 0:
            raise ValueError(f"UNALIGNED ACCESS FAULT: 0x{address:08X} adresi 4 bayta hizalı değil!")

        # 1. Boot Alias (0x00000000 -> Flash'a Mirror Edilir)
        if 0x00000000 <= address < 0x00000000 + self.FLASH_SIZE:
            offset = address
            return struct.unpack_from("<I", self.flash_memory, offset)[0]

        # 2. Flash Bellek (0x08000000)
        if self.FLASH_BASE <= address < self.FLASH_BASE + self.FLASH_SIZE:
            offset = address - self.FLASH_BASE
            return struct.unpack_from("<I", self.flash_memory, offset)[0]

        # 3. SRAM Bellek (0x20000000)
        if self.SRAM_BASE <= address < self.SRAM_BASE + self.SRAM_SIZE:
            offset = address - self.SRAM_BASE
            return struct.unpack_from("<I", self.sram_memory, offset)[0]

        # 4. Çevresel Birimler (MMIO)
        if self.PERIPH_BASE <= address < self.PERIPH_BASE + self.PERIPH_SIZE:
            return self.periph_registers.get(address, 0x00000000)

        # 5. Sistem Birimleri
        if self.SYSTEM_BASE <= address < self.SYSTEM_BASE + self.SYSTEM_SIZE:
            return self.system_registers.get(address, 0x00000000)

        raise MemoryError(f"BUS FAULT: 0x{address:08X} tanımsız adresten okuma!")

# Simülatör Doğrulama
mmap = Stm32MemoryMapEngine()
initial_msp = mmap.read32(0x00000000) # Boot alias üzerinden oku
reset_vector = mmap.read32(0x00000004)

print("[*] STM32 Bellek Haritası Motoru Başlatıldı:")
print(f"  [+] Donanım Başlangıç MSP Adresi : 0x{initial_msp:08X}")
print(f"  [+] Donanım Reset Handler Adresi: 0x{reset_vector:08X} (Thumb Bit: {reset_vector & 1})")

assert initial_msp == 0x20020000, "İlk Yığın İşaretçisi SRAM tepesini göstermelidir!"
assert reset_vector == 0x08000101, "Reset Vektörü Flash kodunu ve Thumb modunu göstermelidir!"
print("[HÜCRE 6] STM32 bellek haritası ve vektör tablosu başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 163: Kod Bloğu 2 — Linker Script (.ld) ve Reset_Handler Veri Kopyalama Motoru
"""

class LinkerScriptSimulator:
    """
    Linker Script Sembolleri ve Reset_Handler Başlangıç Mantığı:
    - _sidata: .data bölümünün Flash'taki başlangıç adresi (LMA - Load Memory Address)
    - _sdata : .data bölümünün SRAM'deki başlangıç adresi (VMA - Virtual Memory Address)
    - _edata : .data bölümünün SRAM'deki bitiş adresi
    - _sbss  : .bss bölümünün SRAM'deki başlangıç adresi
    - _ebss  : .bss bölümünün SRAM'deki bitiş adresi
    """
    def __init__(self, mmap_engine: Stm32MemoryMapEngine):
        self.mmap = mmap_engine

        # Linker Sembolleri Adresleri
        self.FLASH_DATA_LMA = 0x08005000 # Flash'taki kopya
        self.SRAM_DATA_VMA  = 0x20000000 # SRAM başlangıcı
        self.DATA_SIZE      = 64         # 16 adet 32-bit değişken (64 bayt)

        self.SRAM_BSS_START = self.SRAM_DATA_VMA + self.DATA_SIZE # 0x20000040
        self.BSS_SIZE       = 128        # 32 adet 32-bit değişken (128 bayt)
        self.SRAM_BSS_END   = self.SRAM_BSS_START + self.BSS_SIZE

        # Flash'a başlangıç verilerini yükle (Örn: Global PID katsayıları)
        self._burn_initial_data_to_flash()

    def _burn_initial_data_to_flash(self):
        """Derleyici tarafından üretilen Flash ikili görüntüsü"""
        offset = self.FLASH_DATA_LMA - self.mmap.FLASH_BASE
        for i in range(0, self.DATA_SIZE, 4):
            val = 0x1000 + (i // 4) # Test katsayıları: 0x1000, 0x1001, ...
            struct.pack_into("<I", self.mmap.flash_memory, offset + i, val)

    def execute_reset_handler(self) -> Tuple[int, int]:
        """
        Cortex-M Startup Kodu (Assembly / C):
        1. Flash'taki .data bölümünü SRAM'e kopyala
        2. SRAM'deki .bss bölümünü sıfırla (Zero out)
        """
        copied_words = 0
        zeroed_words = 0

        # ADIM 1: .data Bölümünü Kopyala
        src_offset = self.FLASH_DATA_LMA - self.mmap.FLASH_BASE
        dst_addr = self.SRAM_DATA_VMA
        for i in range(0, self.DATA_SIZE, 4):
            val = struct.unpack_from("<I", self.mmap.flash_memory, src_offset + i)[0]
            self.mmap.write32(dst_addr + i, val)
            copied_words += 1

        # ADIM 2: .bss Bölümünü Sıfırla
        for addr in range(self.SRAM_BSS_START, self.SRAM_BSS_END, 4):
            self.mmap.write32(addr, 0x00000000)
            zeroed_words += 1

        return copied_words, zeroed_words

# Deney: Reset Handler Çalıştırılması
linker = LinkerScriptSimulator(mmap)
copied, zeroed = linker.execute_reset_handler()

print("[*] Reset_Handler Yürütüldü:")
print(f"  [+] Flash -> SRAM Kopyalanan .data Sözcüğü: {copied} (Toplam {copied * 4} bayt)")
print(f"  [+] SRAM Sıfırlanan .bss Sözcüğü         : {zeroed} (Toplam {zeroed * 4} bayt)")

# Doğrulama: SRAM ilk adreste Flash'taki veri olmalı
val_first_data = mmap.read32(linker.SRAM_DATA_VMA)
val_first_bss  = mmap.read32(linker.SRAM_BSS_START)

print(f"  [+] SRAM 0x{linker.SRAM_DATA_VMA:08X} (.data ilk değişken): 0x{val_first_data:08X}")
print(f"  [+] SRAM 0x{linker.SRAM_BSS_START:08X} (.bss ilk değişken) : 0x{val_first_bss:08X}")

assert val_first_data == 0x1000
assert val_first_bss == 0x00000000
print("[HÜCRE 8] Linker relocation ve Reset_Handler sıfırlama simülasyonu başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 163: Kod Bloğu 3 — Sabotaj ve Hata Enjeksiyonu: Flash İhlali ve Stack-Heap Çarpışması
"""

print()
print("[*] SABOTAJ SENARYOSU 1: Flash Belleğe Sıradan Pointer İle Yazma Girişimi")
flash_write_fault_caught = False
try:
    # 0x08001000 Flash adresine STR komutu çalıştırmaya çalışıyoruz:
    mmap.write32(0x08001000, 0xDEADBEEF)
except PermissionError as e:
    flash_write_fault_caught = True
    print(f"  [+] Savunma Başarılı: Beklenen Donanım Hatası Yakalandı! ({e})")

assert flash_write_fault_caught == True, "Flash belleğe sıradan yazma engellenmelidir!"

print()
print("[*] SABOTAJ SENARYOSU 2: Hizalanmamış (Unaligned) Bellek Erişimi")
unaligned_fault_caught = False
try:
    # 4 baytlık okuma 0x20000002 adresinden yapılmaya çalışılıyor (Hizalama ihlali!)
    mmap.read32(0x20000002)
except ValueError as e:
    unaligned_fault_caught = True
    print(f"  [+] Savunma Başarılı: Unaligned Access Yakalandı! ({e})")

assert unaligned_fault_caught == True, "Hizalanmamış adres UsageFault üretmelidir!"

print()
print("[*] SABOTAJ SENARYOSU 3: Stack-Heap Bellek Çarpışması (Memory Collision)")
class MemoryCollisionMonitor:
    def __init__(self, sram_base: int, sram_size: int):
        self.sram_base = sram_base
        self.sram_top  = sram_base + sram_size
        self.heap_limit = sram_base + 32 * 1024 # Heap 32 KB'a kadar büyüyebilir
        self.current_heap = self.sram_base + 1024
        self.current_stack = self.sram_top      # Stack en tepeden başlar

    def allocate_heap(self, bytes_count: int) -> int:
        new_heap = self.current_heap + bytes_count
        if new_heap >= self.current_stack:
            raise MemoryError(f"CRITICAL: Stack-Heap Çarpışması! Heap (0x{new_heap:08X}) Stack'i (0x{self.current_stack:08X}) EZDİ!")
        self.current_heap = new_heap
        return self.current_heap

    def push_stack_frame(self, frame_size_bytes: int):
        new_stack = self.current_stack - frame_size_bytes
        if new_stack <= self.current_heap:
            raise MemoryError(f"CRITICAL: STACK OVERFLOW! Stack (0x{new_stack:08X}) Heap alanına (0x{self.current_heap:08X}) ÇARPTI!")
        self.current_stack = new_stack

mem_mon = MemoryCollisionMonitor(mmap.SRAM_BASE, mmap.SRAM_SIZE)
# Derin özyineleme simülasyonu: Stack her adımda 4 KB büyüyor
stack_collision_caught = False
try:
    for recursion_depth in range(40): # 40 * 4 KB = 160 KB > 128 KB SRAM!
        mem_mon.push_stack_frame(4 * 1024)
except MemoryError as e:
    stack_collision_caught = True
    print(f"  [+] Savunma Başarılı: Stack Taşması / Çarpışma Tespit Edildi! ({e})")

assert stack_collision_caught == True
print("[HÜCRE 10] Tüm sabotaj ve sınır aşım testleri başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 163: Kod Bloğu 4 — Atomik Register Manipülasyonu: GPIO BSRR vs ODR Read-Modify-Write Yarışı
"""

class GpioPortSimulator:
    """
    STM32 GPIO Port Donanımı (GPIOA):
    - ODR  (Output Data Register - 0x14): 16-bit Çıkış Durumu
    - BSRR (Bit Set/Reset Register - 0x18): 32-bit Atomik Yazmaç
           - Düşük 16 bit [0..15] : 1 yazılırsa ilgili pin SET (HIGH) olur.
           - Yüksek 16 bit [16..31]: 1 yazılırsa ilgili pin RESET (LOW) olur.
           - 0 yazmanın hiçbir etkisi yoktur!
    """
    def __init__(self):
        self.odr = 0x00000000

    def non_atomic_odr_set(self, pin: int):
        """Klasik C Read-Modify-Write: ODR |= (1 << pin)"""
        # Adım 1: Oku
        temp = self.odr
        # [BURADA KESME GELDİĞİNİ VARSAYALIM!]
        # Adım 2: Değiştir ve Yaz
        temp |= (1 << pin)
        self.odr = temp

    def atomic_bsrr_write(self, set_mask: int, reset_mask: int):
        """Donanımsal Tek Çevrim Atomik Erişim"""
        # Tek bir STR komutu ile donanım bitleri anında günceller
        self.odr = (self.odr | (set_mask & 0xFFFF)) & ~(reset_mask & 0xFFFF)

# YARIŞ DURUMU (RACE CONDITION) DENEYİ:
# Ana program Pin 5'i HIGH yapmak istiyor.
# Tam okuma yaptıktan sonra araya acil bir kesme (ISR) girip Pin 6'yı HIGH yapıyor!

gpio = GpioPortSimulator()

print()
print("[*] 1. YARIŞ DURUMU DENEYİ: Güvensiz ODR Read-Modify-Write İşlemi")
# Adım 1: Ana görev ODR'yi okur (Değer: 0x0000)
main_task_temp = gpio.odr 

# Adım 2: ARAYA KESME GİRİYOR! Kesme Pin 6'yı yakar:
gpio.odr |= (1 << 6)
print(f"  [ISR] Kesme Çalıştı: Pin 6 HIGH Yapıldı (Mevcut ODR: 0x{gpio.odr:04X})")

# Adım 3: Ana görev kaldığı yerden devam eder ve elindeki eski 'main_task_temp' ile Pin 5'i yazar:
main_task_temp |= (1 << 5)
gpio.odr = main_task_temp # FELAKET: Kesmenin yaktığı Pin 6 SİLİNDİ!

print(f"  [ANA GÖREV] Ana Görev Yazdı (Son ODR: 0x{gpio.odr:04X})")
print(f"  [HATA] Pin 6 Durumu: {'AKTİF' if (gpio.odr & (1 << 6)) else 'KAYIP / BOZULDU!'}")
assert not (gpio.odr & (1 << 6)), "ODR yarışında Pin 6'nın ezildiği kanıtlandı!"

print()
print("[*] 2. ÇÖZÜM: Donanımsal Atomik BSRR Yazmacı")
gpio.odr = 0x0000 # Sıfırla

# Kesme Pin 6'yı BSRR ile yakar (Bit 6 = 1):
gpio.atomic_bsrr_write(set_mask=(1 << 6), reset_mask=0)

# Ana görev Pin 5'i BSRR ile yakar (Bit 5 = 1):
gpio.atomic_bsrr_write(set_mask=(1 << 5), reset_mask=0)

print(f"  [BSRR] Her İki İşlem Sonrası ODR: 0x{gpio.odr:04X}")
assert (gpio.odr & (1 << 6)) and (gpio.odr & (1 << 5)), "BSRR ile iki pin de kusursuz korundu!"
print("  [+] Mükemmel: BSRR sayesinde hiçbir okuma-yazma yarışı oluşmadı.")
print("[HÜCRE 12] BSRR atomik register manipülasyonu başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 163: Kod Bloğu 5 — ASELSAN Aviyonik Görev Bilgisayarı Dual-Bank & DTCM Bellek Yöneticisi
"""

class AvionicsMissionMemoryManager:
    """
    ASELSAN Taktik Füze Görev Bilgisayarı Bellek Mimarisi:
    - Dual-Bank Flash: Bank 1 (Aktif Yazılım), Bank 2 (Yedek OTA İmajı)
    - DTCM / CCM RAM : 2000 Hz Hard Real-Time Güdüm Döngüsü (Sıfır Bekleme)
    - SRAM1          : Telemetri Arabellekleri ve FreeRTOS Kuyrukları
    """
    FLASH_BANK1_START = 0x08000000
    FLASH_BANK1_END   = 0x080FFFFF # 1 MB
    FLASH_BANK2_START = 0x08100000
    FLASH_BANK2_END   = 0x081FFFFF # 1 MB
    DTCM_BASE         = 0x20000000 # 64 KB DTCM
    DTCM_SIZE         = 64 * 1024

    def __init__(self):
        self.active_bank = 1 # Bank 1 aktif
        self.dtcm_allocated_bytes = 0
        self.guidance_loop_frequency_hz = 2000
        self.firmware_signature_verified = True

    def switch_active_bank(self, target_bank: int):
        """Görev Sırasında Canlı / Güvenli Firmware Değişimi (Live Bank Swapping)"""
        if target_bank not in (1, 2):
            raise ValueError("Geçersiz Flash Bankı!")
        self.active_bank = target_bank
        print(f"  [BOOT] Flash Bank Değiştirildi -> Aktif Bank: {self.active_bank}")

    def allocate_dtcm_critical_buffer(self, name: str, size_bytes: int) -> int:
        """Kritik Seyrüsefer / Kalman Değişkenlerini DTCM'e Tahsis Et"""
        if self.dtcm_allocated_bytes + size_bytes > self.DTCM_SIZE:
            raise MemoryError("DTCM Bellek Yetersiz! Kritik görev tahsis edilemedi.")
        
        addr = self.DTCM_BASE + self.dtcm_allocated_bytes
        self.dtcm_allocated_bytes += size_bytes
        return addr

# Aviyonik Görev Başlatma Simülasyonu
avionics_mem = AvionicsMissionMemoryManager()

print()
print("[*] ASELSAN Aviyonik Görev Bilgisayarı Bellek Haritası Konfigürasyonu:")
print(f"  [+] Aktif Uçuş Yazılımı: Flash Bank {avionics_mem.active_bank} (0x{avionics_mem.FLASH_BANK1_START:08X})")

# DTCM'e 2000 Hz Güdüm Matrisi Yerleştiriliyor
kalman_matrix_addr = avionics_mem.allocate_dtcm_critical_buffer("Kalman_Covariance", 512)
ins_state_addr     = avionics_mem.allocate_dtcm_critical_buffer("INS_Navigation_State", 256)

print(f"  [+] DTCM Tahsis: Kalman Kovaryans Matrisi -> 0x{kalman_matrix_addr:08X} (Boyut: 512 Bayt)")
print(f"  [+] DTCM Tahsis: INS Seyrüsefer Durumu    -> 0x{ins_state_addr:08X} (Boyut: 256 Bayt)")
print(f"  [+] DTCM Toplam Kullanım: {avionics_mem.dtcm_allocated_bytes} / {avionics_mem.DTCM_SIZE} Bayt")

# Canlı Görevde Bank 2'ye Geçiş (Fail-Safe OTA Güncellemesi)
avionics_mem.switch_active_bank(2)
assert avionics_mem.active_bank == 2
assert kalman_matrix_addr == 0x20000000
assert ins_state_addr == 0x20000200

print("[HÜCRE 14] Taktik aviyonik Dual-Bank ve DTCM bellek senaryosu başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 163: Kod Bloğu 6 — 4 Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_163_memory_map_flash_sram_peripheral_register.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_163\gun_163_memory_map_flash_sram_peripheral_register.png"

# Matplotlib Karanlık Tema Ayarları
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.0

fig = plt.figure(figsize=(18, 12), dpi=300, facecolor='#0F172A')
fig.suptitle("GÜN 163: STM32 Bellek Haritası, SRAM İç Düzeni ve MMIO Mimarisi Panosu",
             fontsize=15, fontweight='bold', color='#38BDF8', y=0.98)

# -----------------------------------------------------------------------------
# PANEL 1: STM32 4 GB Düzlemsel Adres Haritası (Memory Map)
# -----------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1)
ax1.set_facecolor('#1E293B')
ax1.set_title("Panel 1: STM32 4 GB Global Adres Uzayı (Flat Address Space)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax1.axis('off')

memory_blocks = [
    ("Sistem & Çekirdek (Cortex System)", "0xE000_0000 - 0xFFFF_FFFF", "NVIC, SysTick, MPU, SCB", "#8B5CF6", 0.78),
    ("Harici Bellek / Cihaz (FMC / FSMC)", "0x6000_0000 - 0xDFFF_FFFF", "Harici SDRAM, NOR/NAND Flash", "#64748B", 0.58),
    ("Çevresel Birimler (MMIO Peripherals)", "0x4000_0000 - 0x5FFF_FFFF", "GPIO, TIM, USART, SPI, CAN, RCC", "#D97706", 0.38),
    ("Dahili SRAM (SRAM1 + SRAM2 + DTCM)", "0x2000_0000 - 0x3FFF_FFFF", "Stack, Heap, .bss, .data", "#059669", 0.18),
    ("Kod / Flash (Code Space & Flash)", "0x0000_0000 - 0x1FFF_FFFF", "Flash (0x0800_0000), Vector Table", "#0284C7", -0.02)
]

for title, addr, desc, col, ypos in memory_blocks:
    ax1.add_patch(patches.Rectangle((0.05, ypos + 0.05), 0.90, 0.16, facecolor=col, alpha=0.35, edgecolor=col, lw=2))
    ax1.text(0.08, ypos + 0.16, f"{title} [{addr}]", color='#F8FAFC', fontweight='bold', fontsize=8.5)
    ax1.text(0.08, ypos + 0.09, desc, color='#CBD5E1', fontsize=7.5)

ax1.set_xlim(0.0, 1.0)
ax1.set_ylim(-0.05, 1.0)

# -----------------------------------------------------------------------------
# PANEL 2: SRAM Bellek Organizasyonu ve Stack vs Heap Çatışması
# -----------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2)
ax2.set_facecolor('#1E293B')
ax2.set_title("Panel 2: SRAM İçi Yerleşim ve Stack-Heap Çatışma Tehlikesi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax2.axis('off')

# Stack
ax2.add_patch(patches.Rectangle((0.15, 0.72), 0.70, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', lw=2))
ax2.text(0.50, 0.83, "STACK (Yığın) [0x2002_0000 -> _estack]", ha='center', va='center', color='#FCA5A5', fontweight='bold', fontsize=9)
ax2.text(0.50, 0.76, "Yerel Değişkenler, Dönüş Adresleri (Aşağı Doğru Büyür v)", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

# Çatışma Alanı (Collision Zone)
ax2.add_patch(patches.Rectangle((0.15, 0.52), 0.70, 0.18, facecolor='#451A03', edgecolor='#F59E0B', lw=1.5, linestyle='--'))
ax2.text(0.50, 0.63, "TEHLİKELİ ÇATIŞMA ALANI (Guard Zone)", ha='center', va='center', color='#FCD34D', fontweight='bold', fontsize=8.5)
ax2.text(0.50, 0.56, "Stack Overflow & Heap Overlap (MPU Korumasız Çöküş)", ha='center', va='center', color='#FDE68A', fontsize=7.5)

# Heap
ax2.add_patch(patches.Rectangle((0.15, 0.32), 0.70, 0.18, facecolor='#064E3B', edgecolor='#10B981', lw=2))
ax2.text(0.50, 0.43, "HEAP (Dinamik Bellek) [Yukarı Doğru Büyür ^]", ha='center', va='center', color='#6EE7B7', fontweight='bold', fontsize=9)
ax2.text(0.50, 0.36, "malloc() / C++ new / FreeRTOS Task Stacks", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

# .bss ve .data
ax2.add_patch(patches.Rectangle((0.15, 0.17), 0.70, 0.12, facecolor='#1E3A8A', edgecolor='#3B82F6', lw=1.5))
ax2.text(0.50, 0.23, ".bss BÖLÜMÜ (Sıfırlanan Global Veriler)", ha='center', va='center', color='#93C5FD', fontweight='bold', fontsize=8)

ax2.add_patch(patches.Rectangle((0.15, 0.03), 0.70, 0.12, facecolor='#1E293B', edgecolor='#0284C7', lw=1.5))
ax2.text(0.50, 0.09, ".data BÖLÜMÜ [0x2000_0000] (Flash'tan Kopyalanan Globals)", ha='center', va='center', color='#38BDF8', fontweight='bold', fontsize=8)

ax2.set_xlim(0.0, 1.0)
ax2.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 3: MMIO Struct Mapping ve BSRR Atomik Mekanizması
# -----------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3)
ax3.set_facecolor('#1E293B')
ax3.set_title("Panel 3: GPIO Struct Offset Haritası ve Atomik BSRR Donanımı", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax3.axis('off')

struct_offsets = [
    ("Offset 0x00", "MODER", "Pin Modu (Giriş/Çıkış/Analog/AF)"),
    ("Offset 0x04", "OTYPER", "Çıkış Tipi (Push-Pull / Open-Drain)"),
    ("Offset 0x10", "IDR", "Giriş Veri Yazmacı (Salt Okunur)"),
    ("Offset 0x14", "ODR", "Çıkış Veri Yazmacı (Non-Atomic RMW Tehlikesi!)"),
    ("Offset 0x18", "BSRR", "Bit Set/Reset (32-bit Donanımsal Atomik Yazma!)")
]

y = 0.85
for off, reg, desc in struct_offsets:
    col = '#EF4444' if reg == 'ODR' else ('#10B981' if reg == 'BSRR' else '#38BDF8')
    ax3.add_patch(patches.Rectangle((0.08, y - 0.05), 0.84, 0.12, facecolor='#0F172A', edgecolor=col, lw=1.5))
    ax3.text(0.12, y + 0.01, f"{off}: {reg}", color=col, fontweight='bold', fontsize=8.5)
    ax3.text(0.38, y + 0.01, desc, color='#CBD5E1', fontsize=7.5)
    y -= 0.17

ax3.set_xlim(0.0, 1.0)
ax3.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 4: Reset_Handler Başlangıç İşlemleri ve Dual-Bank Flash
# -----------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4)
ax4.set_facecolor('#1E293B')
ax4.set_title("Panel 4: Reset_Handler Relocation Akışı ve Dual-Bank Flash", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax4.axis('off')

# Adım 1: Flash'tan SRAM'e Kopyalama
ax4.text(0.05, 0.88, "1. ADIM: .data Bölümü Kopyalama (LMA -> VMA)", color='#38BDF8', fontweight='bold', fontsize=8.5)
ax4.add_patch(patches.Rectangle((0.05, 0.72), 0.40, 0.12, facecolor='#0284C7', alpha=0.4, edgecolor='#38BDF8', lw=1.5))
ax4.text(0.25, 0.78, "Flash (_sidata)\n0x0800_5000", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

ax4.annotate("", xy=(0.55, 0.78), xytext=(0.46, 0.78), arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2))

ax4.add_patch(patches.Rectangle((0.56, 0.72), 0.39, 0.12, facecolor='#059669', alpha=0.4, edgecolor='#10B981', lw=1.5))
ax4.text(0.75, 0.78, "SRAM (_sdata)\n0x2000_0000", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

# Adım 2: BSS Sıfırlama
ax4.text(0.05, 0.58, "2. ADIM: .bss Bölümü Sıfırlama (Zero-fill)", color='#A78BFA', fontweight='bold', fontsize=8.5)
ax4.add_patch(patches.Rectangle((0.05, 0.42), 0.90, 0.12, facecolor='#1E1B4B', edgecolor='#8B5CF6', lw=1.5))
ax4.text(0.50, 0.48, "memset(&_sbss, 0x00, &_ebss - &_sbss) -> 0x2000_0040 ... 0x2000_00C0", ha='center', va='center', color='#E0E7FF', fontsize=7.5)

# Adım 3: Dual Bank Gösterimi
ax4.text(0.05, 0.28, "3. ADIM: Taktik Dual-Bank Flash Bölümleme", color='#34D399', fontweight='bold', fontsize=8.5)
ax4.add_patch(patches.Rectangle((0.05, 0.10), 0.42, 0.14, facecolor='#064E3B', edgecolor='#10B981', lw=1.5))
ax4.text(0.26, 0.17, "BANK 1 (Aktif Uçuş Kodu)\n0x0800_0000 (1 MB)", ha='center', va='center', color='#A7F3D0', fontsize=7.5, fontweight='bold')

ax4.add_patch(patches.Rectangle((0.53, 0.10), 0.42, 0.14, facecolor='#78350F', edgecolor='#F59E0B', lw=1.5))
ax4.text(0.74, 0.17, "BANK 2 (Yedek / Canlı OTA)\n0x0810_0000 (1 MB)", ha='center', va='center', color='#FDE68A', fontsize=7.5, fontweight='bold')

ax4.set_xlim(0.0, 1.0)
ax4.set_ylim(0.0, 1.0)

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 163 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert initial_msp == 0x20020000
assert reset_vector == 0x08000101
assert val_first_data == 0x1000
assert val_first_bss == 0x00000000
assert flash_write_fault_caught == True
assert unaligned_fault_caught == True
assert stack_collision_caught == True
assert avionics_mem.active_bank == 2
assert kalman_matrix_addr == 0x20000000

print()
print("[PASS] Gün 163: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")

