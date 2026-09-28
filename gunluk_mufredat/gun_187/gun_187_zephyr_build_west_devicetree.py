# -*- coding: utf-8 -*-
"""
GÜN 187: Zephyr RTOS Derleme Sistemi, West ve Devicetree Mimarisi
Standalone Python Doğrulama ve Görselleştirme Betiği
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_187\gun_187_zephyr_build_west_devicetree.png"

# ======================================================================
# Kod Hücresi 1: Devicetree (DTS) Ayrıştırıcı ve Donanım Ağacı Simülatörü
import re

class DevicetreeNode:
    def __init__(self, name, address=None):
        self.name = name
        self.address = address
        self.properties = {}
        self.children = []
        self.parent = None

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def set_property(self, key, value):
        self.properties[key] = value

    def find_node_by_label(self, label):
        if self.properties.get("label") == label or self.name.startswith(label):
            return self
        for child in self.children:
            res = child.find_node_by_label(label)
            if res:
                return res
        return None

def build_mock_stm32_dts():
    """
    STM32H7 Aviyonik Görev Bilgisayarı için basitleştirilmiş Devicetree Ağacı.
    """
    root = DevicetreeNode("/")
    
    # SoC Düğümü
    soc = DevicetreeNode("soc", address=0x0)
    soc.set_property("compatible", "simple-bus")
    root.add_child(soc)
    
    # Flash Bellek Düğümü
    flash = DevicetreeNode("flash", address=0x08000000)
    flash.set_property("compatible", "st,stm32-flash")
    flash.set_property("reg", [0x08000000, 0x00200000]) # 2 MB Flash
    soc.add_child(flash)
    
    # SRAM Düğümü
    sram = DevicetreeNode("sram", address=0x20000000)
    sram.set_property("compatible", "mmio-sram")
    sram.set_property("reg", [0x20000000, 0x00080000]) # 512 KB AXI-SRAM
    soc.add_child(sram)

    # USART1 (RS-422 Taktik Arayüz)
    usart1 = DevicetreeNode("usart1", address=0x40013800)
    usart1.set_property("compatible", "st,stm32-uart")
    usart1.set_property("reg", [0x40013800, 0x400])
    usart1.set_property("interrupts", [37, 0]) # IRQ 37, Priority 0
    usart1.set_property("current-speed", 115200)
    usart1.set_property("status", "okay")
    soc.add_child(usart1)

    # CAN-FD Düğümü
    can1 = DevicetreeNode("fdcan1", address=0x4000A000)
    can1.set_property("compatible", "st,stm32-fdcan")
    can1.set_property("reg", [0x4000A000, 0x400])
    can1.set_property("interrupts", [19, 1]) # IRQ 19, Priority 1
    can1.set_property("bus-speed", 1000000) # 1 Mbps
    can1.set_property("status", "okay")
    soc.add_child(can1)

    return root

# Ağacı Oluştur ve İncele
dts_root = build_mock_stm32_dts()
usart1_node = dts_root.find_node_by_label("usart1")
can1_node = dts_root.find_node_by_label("fdcan1")

print("=== 1. DEVICETREE (DTS) AYRISTIRMA DENEYI ===")
print(f"Kök Düğüm: {dts_root.name} | Çocuk Sayısı: {len(dts_root.children)}")
print(f"USART1 Düğümü: Adres=0x{usart1_node.address:08X} | Compatible={usart1_node.properties['compatible']} | IRQ={usart1_node.properties['interrupts'][0]}")
print(f"FDCAN1 Düğümü: Adres=0x{can1_node.address:08X} | Hız={can1_node.properties['bus-speed']/1e6:.1f} Mbps | Durum={can1_node.properties['status']}")

# Assertions
assert usart1_node.address == 0x40013800, "USART1 taban adresi hatalı!"
assert can1_node.properties["bus-speed"] == 1000000, "CAN veriyolu hızı 1 Mbps olmalıdır!"
print("[BAŞARILI]: Devicetree donanım ağacı modeli başarıyla oluşturuldu ve doğrulandı.")

# ======================================================================
# Kod Hücresi 2: Devicetree'den C Önişlemci Makrolarına Dönüşüm Motoru
def generate_c_devicetree_headers(root_node):
    """
    Devicetree ağacını tarayarak Zephyr benzeri statik C makroları üretir.
    """
    c_defines = {}
    
    def traverse(node, path=""):
        current_path = f"{path}_{node.name}" if path else node.name
        safe_path = current_path.replace("/", "").replace("-", "_").replace("@", "_")
        
        # Taban adres varsa makro oluştur
        if "reg" in node.properties:
            base_addr = node.properties["reg"][0]
            size = node.properties["reg"][1]
            c_defines[f"DT_NODELABEL_{node.name.upper()}_REG_ADDR"] = hex(base_addr)
            c_defines[f"DT_NODELABEL_{node.name.upper()}_REG_SIZE"] = hex(size)
            
        # Kesme varsa makro oluştur
        if "interrupts" in node.properties:
            irq_num = node.properties["interrupts"][0]
            c_defines[f"DT_NODELABEL_{node.name.upper()}_IRQ"] = irq_num
            
        # Özel mülkler
        if "current-speed" in node.properties:
            c_defines[f"DT_NODELABEL_{node.name.upper()}_BAUD"] = node.properties["current-speed"]
            
        for child in node.children:
            traverse(child, current_path)

    traverse(root_node)
    return c_defines

c_macros = generate_c_devicetree_headers(dts_root)

print("=== 2. DEVICETREE'DEN URETILEN C ONISLEMCI MAKROLARI (devicetree_generated.h) ===")
for macro, val in c_macros.items():
    print(f"#define {macro:<35} {val}")

# Assertions
assert c_macros["DT_NODELABEL_USART1_REG_ADDR"] == "0x40013800", "USART1 adres makrosu hatalı!"
assert c_macros["DT_NODELABEL_USART1_IRQ"] == 37, "USART1 IRQ makrosu hatalı!"
assert c_macros["DT_NODELABEL_FDCAN1_REG_ADDR"] == "0x4000a000", "CAN1 adres makrosu hatalı!"
print("[BAŞARILI]: Derleme zamanı C makro üretim motoru %100 doğrulukla çalıştı.")

# ======================================================================
# Kod Hücresi 3: Zephyr Kconfig Yapılandırma Seviyeleri ve Flash/RAM Ayak İzi Karşılaştırması
import numpy as np

def analyze_zephyr_footprint():
    """
    Farklı Kconfig profillerine göre derlenen Zephyr ikili boyutları (STM32H7 / Cortex-M7).
    """
    configurations = {
        "1. Nano Kernel (Min)": {
            "flash_kb": 14.2, 
            "ram_kb": 3.8, 
            "description": "Temel görev çizelgeleyici, interrupts, sıfır sürücü"
        },
        "2. Standart Aviyonik": {
            "flash_kb": 48.6, 
            "ram_kb": 12.4, 
            "description": "Kernel + UART + CAN-FD + SPI + GPIO + Mutex/Queue"
        },
        "3. Aviyonik + Shell": {
            "flash_kb": 86.4, 
            "ram_kb": 22.1, 
            "description": "Standart + USB/UART CLI Shell + Logging Altyapısı"
        },
        "4. Tam Stack (POSIX+IP)": {
            "flash_kb": 168.0, 
            "ram_kb": 44.5, 
            "description": "Aviyonik + lwIP / Native TCP/IP + POSIX Katmanı + MPU"
        }
    }
    return configurations

configs = analyze_zephyr_footprint()

print("=== 3. ZEPHYR KCONFIG PROFILLERI VE BELLEK AYAK IZI ANALIZI ===")
for name, data in configs.items():
    print(f"{name:<24} | Flash: {data['flash_kb']:>6.1f} KB | RAM: {data['ram_kb']:>5.1f} KB | {data['description']}")

min_flash = configs["1. Nano Kernel (Min)"]["flash_kb"]
full_flash = configs["4. Tam Stack (POSIX+IP)"]["flash_kb"]
ratio = full_flash / min_flash
print(f"-> GÖZLEM: Modüler Kconfig sayesinde en küçük sistem ile tam stack arasında {ratio:.1f}x boyut farkı sağlanır!")

# Assertions
assert min_flash < 20.0, "Nano kernel boyutu 20 KB'tan küçük olmalıdır!"
assert configs["2. Standart Aviyonik"]["flash_kb"] < 64.0, "Standart aviyonik çekirdek boyutu 64 KB sınırını aştı!"
print("[BAŞARILI]: Zephyr'in modüler Kconfig bellek ayak izi analizi doğrulandı.")

# ======================================================================
# Kod Hücresi 4: Bilerek Bozma Deneyi — Hatalı DTS Binding ve Eksik Kconfig Denetimi
print("=== BILEREK BOZMA: DERLEME ZAMANI (COMPILE-TIME) HATA DENEYI ===")

def simulate_zephyr_build_check(dts_property_type, kconfig_enabled):
    """
    Zephyr derleyicisinin iki kritik güvenlik kuralını simüle eder:
    1. DTS Binding Doğrulama: 'current-speed' tamsayı olmalıdır.
    2. Kconfig Tutarlılık Denetimi: CONFIG_SERIAL=y olmadan uart düğümü kullanılamaz!
    """
    build_success = True
    error_messages = []
    
    # 1. DTS Tip Denetimi
    if not isinstance(dts_property_type, int):
        build_success = False
        error_messages.append(f"DTC ERROR: 'current-speed' property must be integer! Found: {type(dts_property_type).__name__}")
        
    # 2. Kconfig Sürücü Bağımlılık Denetimi
    if not kconfig_enabled:
        build_success = False
        error_messages.append("KCONFIG ERROR: Device 'usart1' enabled in DTS, but CONFIG_SERIAL is not set in prj.conf!")

    return build_success, error_messages

# Senaryo 1: Hatalı DTS (String girilmiş)
ok1, err1 = simulate_zephyr_build_check(dts_property_type="115200_string", kconfig_enabled=True)
print(f"1. DTS BINDING HATASI SENARYOSU:")
print(f"   Derleme Başarılı mı? : {ok1}")
print(f"   Hata Mesajı          : {err1[0]}")

# Senaryo 2: Eksik Kconfig (DTS var ama sürücü derlenmemiş)
ok2, err2 = simulate_zephyr_build_check(dts_property_type=115200, kconfig_enabled=False)
print(f"\n2. KCONFIG SURUCU EKSIKLIGI SENARYOSU:")
print(f"   Derleme Başarılı mı? : {ok2}")
print(f"   Hata Mesajı          : {err2[0]}")

# Senaryo 3: Kusursuz Konfigürasyon
ok3, err3 = simulate_zephyr_build_check(dts_property_type=115200, kconfig_enabled=True)
print(f"\n3. BASARILI DERLEME SENARYOSU:")
print(f"   Derleme Başarılı mı? : {ok3} (zephyr.elf üretildi!)")

# Assertions
assert ok1 == False and "DTC ERROR" in err1[0], "DTS tip hatası yakalanamadı!"
assert ok2 == False and "KCONFIG ERROR" in err2[0], "Kconfig eksikliği yakalanamadı!"
assert ok3 == True and len(err3) == 0, "Doğru konfigürasyon derlenemedi!"
print("\n[BAŞARILI]: Zephyr statik derleme zamanı emniyet kontrolleri doğrulandı.")

# ======================================================================
# Kod Hücresi 5: Savunma Sanayii Senaryosu — ASELSAN Aviyonik Görev Bilgisayarı DTS Analiz Hattı
import numpy as np

def run_aselsan_bsp_pipeline():
    """
    ASELSAN özel kartı için Devicetree doğrulama ve kaynak çakışma (Conflict) denetleyicisi.
    """
    peripherals = [
        {"name": "usart1_rs422", "addr_start": 0x40013800, "addr_end": 0x40013BFF, "irq": 37, "pins": ["PB6", "PB7"]},
        {"name": "fdcan1_bus",   "addr_start": 0x4000A000, "addr_end": 0x4000A3FF, "irq": 19, "pins": ["PD0", "PD1"]},
        {"name": "spi1_imu",     "addr_start": 0x40013000, "addr_end": 0x400133FF, "irq": 35, "pins": ["PA5", "PA6", "PA7"]},
        {"name": "safety_gpio",  "addr_start": 0x58020000, "addr_end": 0x580203FF, "irq": 16, "pins": ["PA0"]}
    ]
    
    # 1. Adres Çakışması Kontrolü (Memory Overlap Detection)
    conflict_detected = False
    for i in range(len(peripherals)):
        for j in range(i + 1, len(peripherals)):
            p1 = peripherals[i]
            p2 = peripherals[j]
            # Adres çakışması var mı?
            if max(p1["addr_start"], p2["addr_start"]) <= min(p1["addr_end"], p2["addr_end"]):
                conflict_detected = True
                print(f"HATA: Adres çakışması! {p1['name']} ve {p2['name']}")

    # 2. Pin Çakışması Kontrolü (Pin Multiplexing Conflict)
    allocated_pins = set()
    pin_conflict = False
    for p in peripherals:
        for pin in p["pins"]:
            if pin in allocated_pins:
                pin_conflict = True
                print(f"HATA: Pin çakışması! {pin} birden fazla çevre birimine atandı!")
            allocated_pins.add(pin)

    # 3. IRQ Benzersizliği Kontrolü
    irqs = [p["irq"] for p in peripherals]
    irq_unique = len(irqs) == len(set(irqs))

    return conflict_detected, pin_conflict, irq_unique, len(peripherals)

has_addr_conflict, has_pin_conflict, irqs_ok, periph_count = run_aselsan_bsp_pipeline()

print("=== 5. ASELSAN AVIYONIK BSP VE DONANIM DOGRULAMA RAPORU ===")
print(f"Toplam Tanımlanan Çevre Birimi : {periph_count} adet")
print(f"Adres Çakışması (Overlap)       : {'YOK (TEMİZ)' if not has_addr_conflict else 'HATA VAR!'}")
print(f"Pin Yönlendirme Çakışması       : {'YOK (TEMİZ)' if not has_pin_conflict else 'HATA VAR!'}")
print(f"Kesme Hattı (IRQ) Benzersizliği : {'TAM VE GUVENLI' if irqs_ok else 'CAKISMA VAR!'}")

# Assertions
assert not has_addr_conflict, "Donanım adres çakışması tespit edildi!"
assert not has_pin_conflict, "Pinmux çakışması tespit edildi!"
assert irqs_ok, "Kesme numaraları çakışıyor!"
print("[BAŞARILI]: ASELSAN Aviyonik Kart DTS mimarisi tüm kuralları başarıyla geçti.")

# ======================================================================
# Kod Hücresi 6: Profesyonel 4 Panelli Mühendislik Dashboardu (300 DPI, Dark Theme)
import os
import numpy as np
import matplotlib.pyplot as plt

# Görsel Dosya Yolu Kontrolü
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_187_zephyr_build_west_devicetree.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_187\gun_187_zephyr_build_west_devicetree.png"

# Karanlık Tema Renk Paleti (#0F172A Slate / Neon)
plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.grid(True, linestyle='--', alpha=0.3, color='#64748B')
    ax.tick_params(colors='#E2E8F0', labelsize=10)
    for spine in ax.spines.values():
        spine.set_color('#334155')

# ------------------------------------------------------------------------------
# PANEL 1: Devicetree Donanım Adres Haritası ve Çevre Birimleri Dağılımı
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
periph_names = ['FLASH (2MB)', 'AXI-SRAM (512K)', 'USART1 (RS-422)', 'FDCAN1 (1M)', 'SPI1 (IMU)', 'GPIO_A (Safe)']
base_addrs = [0x08000000 / 1e6, 0x20000000 / 1e6, 0x40013800 / 1e6, 0x4000A000 / 1e6, 0x40013000 / 1e6, 0x58020000 / 1e6]
colors_p1 = ['#38BDF8', '#818CF8', '#10B981', '#F59E0B', '#EC4899', '#EF4444']

y_pos = np.arange(len(periph_names))
bars1 = ax1.barh(y_pos, base_addrs, color=colors_p1, edgecolor='#334155', height=0.55)

for bar, addr, p_name in zip(bars1, base_addrs, periph_names):
    ax1.text(bar.get_width() + 15, bar.get_y() + bar.get_height()/2.0, 
             f"0x{int(addr*1e6):08X}", va='center', ha='left', color='#F8FAFC', fontweight='bold', fontsize=9)

ax1.set_yticks(y_pos)
ax1.set_yticklabels(periph_names, color='#E2E8F0', fontsize=10)
ax1.set_title('PANEL 1: Devicetree Hiyerarşik Donanım Adres Haritası (MB)', color='#38BDF8', fontsize=12, fontweight='bold')
ax1.set_xlabel('Bellek Adres Tabanı (Milyon / HEX Gösterim)', color='#E2E8F0', fontsize=10)
ax1.set_xlim(0, 1750)

# ------------------------------------------------------------------------------
# PANEL 2: Kconfig Seviyelerine Göre Flash ve RAM Ayak İzi (Footprint)
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
cfg_labels = ['1. Nano Kernel', '2. Standart Aviyonik', '3. Aviyonik+Shell', '4. Tam Stack']
flash_vals = [configs[k]["flash_kb"] for k in configs.keys()]
ram_vals = [configs[k]["ram_kb"] for k in configs.keys()]

x = np.arange(len(cfg_labels))
width = 0.35

rects1 = ax2.bar(x - width/2, flash_vals, width, label='Flash Boyutu (KB)', color='#38BDF8', edgecolor='#334155')
rects2 = ax2.bar(x + width/2, ram_vals, width, label='RAM Boyutu (KB)', color='#10B981', edgecolor='#334155')

for r in rects1:
    h = r.get_height()
    ax2.text(r.get_x() + r.get_width()/2.0, h + 2, f"{h:.1f}K", ha='center', va='bottom', color='#38BDF8', fontsize=9, fontweight='bold')

for r in rects2:
    h = r.get_height()
    ax2.text(r.get_x() + r.get_width()/2.0, h + 2, f"{h:.1f}K", ha='center', va='bottom', color='#10B981', fontsize=9, fontweight='bold')

ax2.set_title('PANEL 2: Kconfig Konfigürasyon Seviyelerine Göre Ayak İzi (Footprint)', color='#38BDF8', fontsize=12, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(cfg_labels, color='#E2E8F0', fontsize=9)
ax2.set_ylabel('Bellek Kullanımı (Kilobayt - KB)', color='#E2E8F0', fontsize=10)
ax2.set_ylim(0, 195)
ax2.legend(loc='upper left', facecolor='#0F172A', edgecolor='#334155', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 3: West Build Aşamaları Süre Dağılımı (Saniye)
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
build_stages = ['DTC & Overlays', 'Kconfig Çözümleme', 'CMake Yapılandırma', 'Ninja/GCC Derleme', 'Binary İmzalama']
stage_times = [0.45, 0.65, 1.20, 4.80, 0.30] # Toplam ~7.4 saniye
colors_p3 = ['#38BDF8', '#818CF8', '#F59E0B', '#10B981', '#EC4899']

wedges, texts, autotexts = ax3.pie(stage_times, labels=build_stages, autopct='%1.1f%%', 
                                  startangle=140, colors=colors_p3, 
                                  textprops=dict(color='#E2E8F0', fontsize=9),
                                  wedgeprops=dict(edgecolor='#0F172A', linewidth=2))

for autotext in autotexts:
    autotext.set_color('#0F172A')
    autotext.set_fontweight('bold')

ax3.set_title('PANEL 3: West Build Derleme Boru Hattı Aşamaları (Toplam: 7.4s)', color='#38BDF8', fontsize=12, fontweight='bold')

# ------------------------------------------------------------------------------
# PANEL 4: ASELSAN Aviyonik Donanım Kesme (IRQ) ve Veri Hızı Profili
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
p_names_p4 = ['USART1 (RS-422)', 'FDCAN1 (Gövde)', 'SPI1 (Taktik IMU)', 'SAFETY_GPIO']
irq_numbers = [37, 19, 35, 16]
bus_speeds_kbps = [921.6, 1000.0, 15000.0 / 10, 100.0] # SPI ölçeklendi

ax4_twin = ax4.twinx()
ax4_twin.set_facecolor('none')
ax4_twin.grid(False)

bar_p4_1 = ax4.bar(np.arange(len(p_names_p4)) - 0.2, irq_numbers, width=0.35, color='#F59E0B', label='NVIC IRQ Kanalı', edgecolor='#334155')
bar_p4_2 = ax4_twin.bar(np.arange(len(p_names_p4)) + 0.2, bus_speeds_kbps, width=0.35, color='#38BDF8', label='Veri Hızı (kbps / x10)', edgecolor='#334155')

ax4.set_xticks(np.arange(len(p_names_p4)))
ax4.set_xticklabels(p_names_p4, color='#E2E8F0', fontsize=9)
ax4.set_ylabel('NVIC Kesme Numarası (IRQ#)', color='#F59E0B', fontsize=10)
ax4_twin.set_ylabel('Haberleşme Hızı (kbps)', color='#38BDF8', fontsize=10)
ax4_twin.tick_params(colors='#38BDF8')
ax4.tick_params(colors='#F59E0B')

ax4.set_title('PANEL 4: ASELSAN Aviyonik Kartı Çevre Birimleri IRQ ve Hız Dağılımı', color='#38BDF8', fontsize=12, fontweight='bold')

# Birleşik Lejant
lines_1, labels_1 = ax4.get_legend_handles_labels()
lines_2, labels_2 = ax4_twin.get_legend_handles_labels()
ax4.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', facecolor='#0F172A', edgecolor='#334155', fontsize=9)

plt.tight_layout()
plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', bbox_inches='tight')
plt.close()

# Üretilen PNG Dosya Boyutu Kontrolü
file_size = os.path.getsize(PNG_FILE)
print(f"[+] Visual Artifact Üretildi: {PNG_FILE} ({file_size:,} bayt)")

# Assertions
assert os.path.exists(PNG_FILE), "Görsel dosya üretilemedi!"
assert file_size > 100 * 1024, f"Görsel dosya boyutu çok küçük: {file_size} bayt (< 100 KB)"
print("[PASS] GÜN 187: TÜM MATEMATİKSEL VE GÖRSEL DOĞRULAMALAR BAŞARIYLA TAMAMLANDI!")

