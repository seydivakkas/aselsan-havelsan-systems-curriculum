# -*- coding: utf-8 -*-
"""
GÜN 167: C/C++ 'volatile' Anahtar Kelimesi: Ne Zaman Gerekir, Ne Zaman Yetmez? Atomiklik, Torn Reads ve Bellek Bariyerleri
Otomatik Oluşturulan Çalıştırılabilir Python Betiği
"""

# -*- coding: utf-8 -*-
"""
GÜN 167: Kod Bloğu 1 — Derleyici Optimizasyonu ve volatile Simülatörü
(Register Caching vs Bellek Senkronizasyonu)
"""

class CompilerOptimizationSimulator:
    """
    Derleyici Optimizasyon Motoru Simülasyonu:
    - -O0 Modu: Her zaman doğrudan RAM'den okur/yazar.
    - -O3 Modu (Non-volatile): Değişkeni ilk okumada CPU Register'ına önbelleğe alır.
    - -O3 Modu (Volatile): Register caching yasaktır, daima RAM'den LDR/STR üretir.
    """
    def __init__(self):
        self.ram_memory = {"packet_flag": 0}
        self.cpu_register_r4 = None # CPU Önbellek Yazmacı

    def simulate_polling_loop_non_volatile_O3(self, isr_trigger_step: int, max_steps: int = 20) -> Tuple[bool, int]:
        """Non-volatile bayrak: Derleyici R4 yazmacında döner, RAM'deki değişimi GÖREMEZ!"""
        steps = 0
        loop_exited = False

        # Derleyici optimizasyonu: İlk adımda RAM'den R4'e al
        self.cpu_register_r4 = self.ram_memory["packet_flag"]

        for step in range(max_steps):
            steps += 1
            # Simüle edilen Kesme (ISR): Belirli adımda RAM'i günceller
            if step == isr_trigger_step:
                self.ram_memory["packet_flag"] = 1 # RAM güncellendi!

            # CPU Döngüsü: R4 yazmacına bakar (RAM'e BAKMAZ!)
            if self.cpu_register_r4 != 0:
                loop_exited = True
                break

        return loop_exited, steps

    def simulate_polling_loop_volatile_O3(self, isr_trigger_step: int, max_steps: int = 20) -> Tuple[bool, int]:
        """Volatile bayrak: Derleyici R4 önbelleklemesini devre dışı bırakır, her adımda LDR üretir!"""
        steps = 0
        loop_exited = False

        for step in range(max_steps):
            steps += 1
            if step == isr_trigger_step:
                self.ram_memory["packet_flag"] = 1 # RAM güncellendi!

            # VOLATILE EMRİ: Her adımda RAM'den doğrudan oku (LDR komutu)
            fresh_value_from_ram = self.ram_memory["packet_flag"]
            if fresh_value_from_ram != 0:
                loop_exited = True
                break

        return loop_exited, steps

# Deney: 5. Adımda Kesme Geliyor
sim = CompilerOptimizationSimulator()

# 1. Non-Volatile Testi (-O3 Optimizasyonunda Kilitlenme)
exited_non_vol, steps_non_vol = sim.simulate_polling_loop_non_volatile_O3(isr_trigger_step=5, max_steps=20)

print("[*] Derleyici Optimizasyonu ve Register Caching Simülasyonu:")
print(f"  [!] Non-Volatile (-O3): Döngüden Çıkabildi mi? : {exited_non_vol} (Adım: {steps_non_vol})")
print(f"  [!] RAM Değeri: {sim.ram_memory['packet_flag']}, CPU R4 Yazmacı: {sim.cpu_register_r4}")
assert exited_non_vol == False, "Non-volatile değişken register caching nedeniyle kilitlenmelidir!"

# 2. Volatile Testi (Her Adımda Fiziksel LDR Okuması)
sim.ram_memory["packet_flag"] = 0 # Sıfırla
exited_vol, steps_vol = sim.simulate_polling_loop_volatile_O3(isr_trigger_step=5, max_steps=20)

print(f"  [+] Volatile (-O3)    : Döngüden Çıkabildi mi? : {exited_vol} (Adım: {steps_vol})")
assert exited_vol == True, "Volatile değişken kesme güncellemesini anında yakalamalıdır!"
assert steps_vol == 6 # 5. adımda yazıldı, 6. adımda anında çıktı
print("[HÜCRE 6] volatile ve register caching simülatörü başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 167: Kod Bloğu 2 — 64-bit Değişkenlerde Torn Read (Yırtık Okuma) Simülatörü
(32-bit Cortex-M Veri Yolu Kısıtı)
"""

class TornReadSimulator:
    """
    32-bit ARM Cortex-M Bus Kısıtı:
    - 64-bit (uint64_t) değerler 2 bağımsız 32-bit STR komutuyla yazılır.
    - Düşük 32-bit (Low Word) yazıldıktan hemen sonra araya kesme girerse,
      kesme eski High Word ile yeni Low Word'ün birleşimini okur (TORN READ)!
    """
    def __init__(self):
        self.memory_low32 = 0x00000000
        self.memory_high32 = 0x00000000

    def write_64bit_non_atomic(self, val64: int, interrupt_trigger_callback=None):
        low = val64 & 0xFFFFFFFF
        high = (val64 >> 32) & 0xFFFFFFFF

        # ADIM 1: Düşük 32-bit yazılır
        self.memory_low32 = low

        # [ARAYA KESME GİRİYOR!]
        if interrupt_trigger_callback:
            interrupt_trigger_callback()

        # ADIM 2: Yüksek 32-bit yazılır
        self.memory_high32 = high

    def read_64bit(self) -> int:
        return (self.memory_high32 << 32) | self.memory_low32

# Deney: Füze Zaman Damgası 0x00000000_FFFFFFFF'den 0x00000001_00000000'a geçiyor!
torn_sim = TornReadSimulator()
# Başlangıç değeri: 0x00000000_FFFFFFFF (Düşük: 0xFFFFFFFF, Yüksek: 0x00000000)
torn_sim.write_64bit_non_atomic(0x00000000_FFFFFFFF)

corrupted_read_value = None

def isr_read_probe():
    global corrupted_read_value
    # Kesme tam iki 32-bit yazma işlemi arasında değişkeni okuyor:
    corrupted_read_value = torn_sim.read_64bit()

# Yeni değer yazılıyor: 0x00000001_00000000 (Low=0x00000000, High=0x00000001)
# Yazma anında araya kesme giriyor:
torn_sim.write_64bit_non_atomic(0x00000001_00000000, interrupt_trigger_callback=isr_read_probe)

print()
print("[*] 64-bit Torn Read (Yırtık Okuma) Analizi:")
print(f"  [+] Eski Değer : 0x00000000_FFFFFFFF ({0x00000000_FFFFFFFF})")
print(f"  [+] Yeni Değer : 0x00000001_00000000 ({0x00000001_00000000})")
print(f"  [!] KESMENİN OKUDUĞU YIRTIK DEĞER: 0x{corrupted_read_value:016X} ({corrupted_read_value})")

# Kesme ne eski değeri okudu ne yeni değeri; 0x0 okudu!
assert corrupted_read_value == 0x00000000_00000000, "Torn Read ile verinin 0'a çöktüğü kanıtlandı!"
print("  [!] volatile olmasına rağmen 64-bit veri donanımsal olarak YIRTILDI!")
print("[HÜCRE 8] Torn read simülasyonu başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 167: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyonu: volatile Sayaç Yarış Durumu (Race Condition)
"""

class VolatileRaceConditionSimulator:
    """
    volatile int counter = 0;
    counter++ işlemi atomik değildir!
    LDR -> ADD -> STR adımları arasına kesme girdiğinde sayaç kayıpları simülasyonu.
    """
    def __init__(self):
        self.shared_counter = 0
        self.lost_updates = 0

    def non_atomic_increment_task(self, isr_intervene: bool = False):
        # 1. Adım: Oku (LDR)
        local_reg = self.shared_counter

        # [SABOTAJ: ARAYA KESME GİRİYOR VE SAYAÇ ARTIRIYOR!]
        if isr_intervene:
            # Kesme kendi içinde counter++ yapıyor
            self.shared_counter += 1

        # 2. Adım: Artır (ADD)
        local_reg += 1

        # 3. Adım: Yaz (STR) - Kesmenin artırdığı değeri ezer!
        self.shared_counter = local_reg

# Simülasyon: 100 Kez Artırma Yapılıyor, 30 Tanesinde Araya Kesme Giriyor
race_sim = VolatileRaceConditionSimulator()

for i in range(100):
    # Her 3 işlemde bir kesme araya girsin
    should_interrupt = (i % 3 == 0)
    race_sim.non_atomic_increment_task(isr_intervene=should_interrupt)

# Beklenen Değer: 100 (Ana Görev) + 34 (Araya giren kesmeler) = 134 olmalıydı
# Ancak araya giren kesmeler ezildiği için değer sadece 100 kalır!
print()
print("[*] volatile++ Yarış Durumu (Race Condition) Sabotaj Testi:")
print(f"  [+] Beklenen Toplam Artış: 134")
print(f"  [!] Gerçekleşen Sayaç     : {race_sim.shared_counter}")
lost = 134 - race_sim.shared_counter
print(f"  [!] Kaybolan / Ezilen Veri : {lost} adet artırma kayboldu!")

assert race_sim.shared_counter == 100, "Kesmelerin yaptığı artırmalar ezilmelidir!"
assert lost == 34, "34 adet kesme artırması kaybolmuştur!"
print("[HÜCRE 10] volatile sayaç yarış durumu (race condition) başarıyla kanıtlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 167: Kod Bloğu 4 — C++20 Bellek Modeli: std::atomic, acquire/release ve Donanımsal DMB Bariyeri
"""

class Cpp20AtomicMemoryModel:
    """
    C++20 std::atomic ve Donanımsal Bellek Bariyeri (DMB) Modeli:
    - atomic_store_release: Tampon verisinin belleğe yazılmasını zorlar, sonra bayrağı yakar.
    - atomic_load_acquire  : Bayrağı kontrol eder; bayrak 1 ise tamponun hazır olduğunu garanti eder.
    - atomic_fetch_add     : ARM LDREX/STREX veya kritik bölge ile bölünemez artırma sağlar.
    """
    def __init__(self):
        self.atomic_counter = 0
        self.telemetry_buffer = [0] * 4
        self.data_ready_flag = 0
        self.dmb_barrier_executed = False

    def atomic_fetch_add(self, val: int = 1) -> int:
        """ARM Cortex-M LDREX / STREX Donanımsal Bölünemez Artırma"""
        # Tek çevrimlik atomik işlem: Kesme araya girse dahi donanım çakışmayı yakalar ve tekrarlar
        old = self.atomic_counter
        self.atomic_counter += val
        return old

    def producer_atomic_release(self, payload: List[int]):
        """C++20 memory_order_release Simülasyonu"""
        # 1. Önce veriyi yaz
        for i, b in enumerate(payload):
            self.telemetry_buffer[i] = b

        # 2. Donanımsal Bellek Bariyeri (DMB - Data Memory Barrier)
        # Derleyicinin veya CPU'nun flag yazmasını buffer yazmasının önüne geçirmesini engeller!
        self.dmb_barrier_executed = True

        # 3. Bayrağı atomik set et
        self.data_ready_flag = 1

    def consumer_atomic_acquire(self) -> Optional[List[int]]:
        """C++20 memory_order_acquire Simülasyonu"""
        if self.data_ready_flag == 1:
            # DMB sayesinde buffer'ın tam yazıldığı garantidir
            return list(self.telemetry_buffer)
        return None

# Deney: C++20 Atomik Model Doğrulaması
atomic_model = Cpp20AtomicMemoryModel()

# 1. Atomik Sayaç Testi
for _ in range(134):
    atomic_model.atomic_fetch_add(1)

print()
print("[*] C++20 std::atomic ve Bellek Bariyeri (DMB) Testi:")
print(f"  [+] Atomik Sayaç Değeri: {atomic_model.atomic_counter} (Beklenen: 134)")
assert atomic_model.atomic_counter == 134

# 2. Acquire-Release Veri Transferi
test_payload = [0x55, 0xAA, 0x12, 0x34]
atomic_model.producer_atomic_release(test_payload)
assert atomic_model.dmb_barrier_executed == True

consumed_payload = atomic_model.consumer_atomic_acquire()
print(f"  [+] Acquire İle Okunan Tampon: {[hex(x) for x in consumed_payload]}")
assert consumed_payload == test_payload
print("  [+] Mükemmel: Bellek bariyeri ile sıfır veri yırtılması ve sıfır yeniden sıralama.")
print("[HÜCRE 12] C++20 atomik model ve donanımsal DMB mekanizması başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 167: Kod Bloğu 5 — ROKETSAN Füze Seyrüsefer ve Güdüm Bilgisayarı Paylaşımlı Bellek Mimarisi
"""

class RocketNavTelemetrySharedMemory:
    """
    ROKETSAN Füze Aviyonik Çekirdeği:
    - 2000 Hz Seyrüsefer Görevi (Thread): 64-bit Yüksek Hassasiyetli Koordinat Üretir
    - 500 Hz Telemetri DMA/ISR (Handler): Koordinatları Telsiz Modülüne Basar
    - Çözüm: Çift Tamponlama (Double Buffering) + Atomik Değişim (Atomic Ping-Pong Pointer)
    """
    def __init__(self):
        # Ping-Pong Tamponları
        self.buffer_ping = {"target_x": 0.0, "target_y": 0.0, "timestamp_us": 0}
        self.buffer_pong = {"target_x": 0.0, "target_y": 0.0, "timestamp_us": 0}
        self.active_write_buffer_idx = 0 # 0: Ping, 1: Pong
        self.atomic_commit_sequence = 0

    def guidance_task_update_coordinates(self, x: float, y: float, timestamp: int):
        """2000 Hz Güdüm Görevi: Pasif Tampona Yazar (Torn Read İmkansızdır!)"""
        target_buf = self.buffer_pong if self.active_write_buffer_idx == 0 else self.buffer_ping
        target_buf["target_x"] = x
        target_buf["target_y"] = y
        target_buf["timestamp_us"] = timestamp

        # Atomik Pointer Değişimi (C++20 atomic_exchange)
        self.active_write_buffer_idx = 1 - self.active_write_buffer_idx
        self.atomic_commit_sequence += 1

    def telemetry_isr_read_latest(self) -> Dict[str, Any]:
        """500 Hz Telemetri ISR: Daima En Son Tamamlanmış Tamponu Okur"""
        # Aktif yazılanın zıttı olan tampon daima tutarlıdır
        read_buf = self.buffer_ping if self.active_write_buffer_idx == 0 else self.buffer_pong
        return dict(read_buf)

# Aviyonik Uçuş Simülasyonu
nav_sys = RocketNavTelemetrySharedMemory()

# 1. Adım: İlk Koordinatlar Yazılıyor (Hedef: X=12500.5m, Y=4500.2m, Zaman=10000us)
nav_sys.guidance_task_update_coordinates(12500.5, 4500.2, 10000)

# 2. Adım: Telemetri ISR anında okuyor
telemetry_packet = nav_sys.telemetry_isr_read_latest()

print()
print("[*] ROKETSAN Seyrüsefer Çift Tamponlu (Double-Buffering) Telemetri Testi:")
print(f"  [+] Okunan Hedef X       : {telemetry_packet['target_x']} m")
print(f"  [+] Okunan Hedef Y       : {telemetry_packet['target_y']} m")
print(f"  [+] Zaman Damgası        : {telemetry_packet['timestamp_us']} us")
print(f"  [+] Atomik Taahhüt Sırası: {nav_sys.atomic_commit_sequence}")

assert telemetry_packet["target_x"] == 12500.5
assert telemetry_packet["target_y"] == 4500.2
assert telemetry_packet["timestamp_us"] == 10000
assert nav_sys.atomic_commit_sequence == 1
print("[HÜCRE 14] Taktik aviyonik seyrüsefer paylaşımlı bellek mimarisi başarıyla doğrulandı.")

# -*- coding: utf-8 -*-
"""
GÜN 167: Kod Bloğu 6 — 4 Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_167_volatile_ne_zaman_gerekir_ne_zaman_yetmez.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_167\gun_167_volatile_ne_zaman_gerekir_ne_zaman_yetmez.png"

# Matplotlib Karanlık Tema Ayarları
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.0

fig = plt.figure(figsize=(18, 12), dpi=300, facecolor='#0F172A')
fig.suptitle("GÜN 167: C/C++ 'volatile' Semantiği, Atomiklik, Torn Reads ve Bellek Bariyerleri Panosu",
             fontsize=14, fontweight='bold', color='#38BDF8', y=0.98)

# -----------------------------------------------------------------------------
# PANEL 1: Register Caching vs Volatile Bellek Erişimi (-O3)
# -----------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1)
ax1.set_facecolor('#1E293B')
ax1.set_title("Panel 1: Register Caching (-O3) vs 'volatile' Bellek Erişimi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax1.axis('off')

# Non-volatile Kutusu
ax1.add_patch(patches.FancyBboxPatch((0.05, 0.48), 0.42, 0.45, boxstyle="round,pad=0.02", facecolor='#7F1D1D', edgecolor='#EF4444', lw=2))
ax1.text(0.26, 0.85, "NON-VOLATILE (-O3)", ha='center', va='center', color='#F87171', fontweight='bold', fontsize=10)
ax1.text(0.26, 0.75, "CPU Yazmacına Önbellekleme\n(Register Caching)", ha='center', va='center', color='#FDE68A', fontsize=8.5)
ax1.text(0.26, 0.60, "RAM'e sadece İLK ADIMDA bakar.\nISR RAM'deki bayrağı 1 yapsa dahi,\nCPU R4 yazmacında 0'da döner!\nSONUÇ: SONSUZ KİLİTLENME!", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

# Volatile Kutusu
ax1.add_patch(patches.FancyBboxPatch((0.53, 0.48), 0.42, 0.45, boxstyle="round,pad=0.02", facecolor='#064E3B', edgecolor='#10B981', lw=2))
ax1.text(0.74, 0.85, "VOLATILE (-O3)", ha='center', va='center', color='#34D399', fontweight='bold', fontsize=10)
ax1.text(0.74, 0.75, "Her Adımda LDR Komutu\n(Zorunlu Bellek Okuma)", ha='center', va='center', color='#FDE68A', fontsize=8.5)
ax1.text(0.74, 0.60, "Derleyici önbelleklemeyi iptal eder.\nHer döngüde RAM'den güncel değer okunur.\nKesme değişikliği anında algılanır.\nSONUÇ: BAŞARILI ÇIKIŞ!", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

# Alt Açıklama
ax1.add_patch(patches.Rectangle((0.10, 0.12), 0.80, 0.25, facecolor='#0F172A', edgecolor='#38BDF8', lw=1.5))
ax1.text(0.50, 0.28, "DERLEYİCİ KURALI: 'volatile' SADECE DERLEYİCİ OPTİMİZASYONUNU ENGELLER", ha='center', va='center', color='#38BDF8', fontweight='bold', fontsize=8.5)
ax1.text(0.50, 0.18, "* 'volatile', donanımsal atomiklik veya thread senkronizasyonu SAĞLAMAZ!\n* Sadece derleyicinin değişkeni CPU yazmacında saklamasını yasaklar.", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

ax1.set_xlim(0.0, 1.0)
ax1.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 2: 64-bit Torn Read (Yırtık Okuma) Mekanizması
# -----------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2)
ax2.set_facecolor('#1E293B')
ax2.set_title("Panel 2: 32-bit Mimaride 64-bit 'Torn Read' (Yırtık Okuma) Fiziği", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax2.axis('off')

# 64-bit Yazma Aşamaları
ax2.text(0.05, 0.88, "1. ADIM: Düşük 32-bit Yazıldı (STR R0, [Addr+0]):", color='#38BDF8', fontweight='bold', fontsize=8.5)
ax2.add_patch(patches.Rectangle((0.05, 0.74), 0.42, 0.10, facecolor='#0284C7', edgecolor='#FFFFFF', lw=1))
ax2.text(0.26, 0.79, "LOW: 0x00000000 (YENİ)", ha='center', va='center', color='#FFFFFF', fontsize=8, fontweight='bold')
ax2.add_patch(patches.Rectangle((0.50, 0.74), 0.42, 0.10, facecolor='#64748B', edgecolor='#FFFFFF', lw=1))
ax2.text(0.71, 0.79, "HIGH: 0x00000000 (ESKİ)", ha='center', va='center', color='#FFFFFF', fontsize=8)

# Araya Kesme Girişi
ax2.add_patch(patches.Rectangle((0.05, 0.46), 0.87, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', lw=1.5, linestyle='--'))
ax2.text(0.485, 0.58, "TAM BURADA KESME (ISR) GİRİYOR VE OKUMA YAPIYOR!", ha='center', va='center', color='#FCA5A5', fontweight='bold', fontsize=9)
ax2.text(0.485, 0.50, "Okunan = (ESKİ HIGH << 32) | YENİ LOW = 0x00000000_00000000 (ÇÖP VERİ!)", ha='center', va='center', color='#FDE68A', fontsize=8)

# 2. Adım: Yüksek 32-bit Yazılıyor
ax2.text(0.05, 0.34, "2. ADIM: Yüksek 32-bit Yazıldı (STR R1, [Addr+4]) [ARTIK ÇOK GEÇ!]:", color='#A78BFA', fontweight='bold', fontsize=8.5)
ax2.add_patch(patches.Rectangle((0.05, 0.18), 0.42, 0.10, facecolor='#0284C7', edgecolor='#FFFFFF', lw=1))
ax2.text(0.26, 0.23, "LOW: 0x00000000 (YENİ)", ha='center', va='center', color='#FFFFFF', fontsize=8)
ax2.add_patch(patches.Rectangle((0.50, 0.18), 0.42, 0.10, facecolor='#059669', edgecolor='#FFFFFF', lw=1))
ax2.text(0.71, 0.23, "HIGH: 0x00000001 (YENİ)", ha='center', va='center', color='#FFFFFF', fontsize=8, fontweight='bold')

ax2.set_xlim(0.0, 1.0)
ax2.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 3: volatile++ Yarış Durumu (LDR -> ADD -> STR)
# -----------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3)
ax3.set_facecolor('#1E293B')
ax3.set_title("Panel 3: volatile++ Neden Atomik Değildir? (Race Condition)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax3.axis('off')

steps_data = [
    ("1. Ana Görev: LDR R0, [counter]", "counter = 0 değerini CPU yazmacına (R0=0) okur", "#38BDF8", 0.80),
    ("2. [KESME GİRİYOR!]", "ISR çalışır: counter'ı okur, artırır ve RAM'e 1 yazar!", "#EF4444", 0.60),
    ("3. Ana Görev Devam Eder: ADD R0, #1", "Ana görev kendi R0'ını (0+1=1) artırır", "#F59E0B", 0.40),
    ("4. Ana Görev: STR R0, [counter]", "RAM'e 1 yazar -> KESMENİN YAPTIĞI ARTIŞ EZİLDİ!", "#DC2626", 0.20)
]

for title, desc, col, ypos in steps_data:
    ax3.add_patch(patches.Rectangle((0.05, ypos), 0.90, 0.14, facecolor='#0F172A', edgecolor=col, lw=1.5))
    ax3.text(0.08, ypos + 0.085, title, color=col, fontweight='bold', fontsize=8.5)
    ax3.text(0.08, ypos + 0.035, desc, color='#CBD5E1', fontsize=7.5)

ax3.set_xlim(0.0, 1.0)
ax3.set_ylim(0.05, 1.0)

# -----------------------------------------------------------------------------
# PANEL 4: Çözüm: C++20 std::atomic ve Donanımsal Bellek Bariyeri (DMB)
# -----------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4)
ax4.set_facecolor('#1E293B')
ax4.set_title("Panel 4: Savunma Çözümü: C++20 Bellek Modeli ve DMB Bariyeri", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax4.axis('off')

# Üretici Akışı
ax4.add_patch(patches.Rectangle((0.05, 0.55), 0.42, 0.38, facecolor='#0F172A', edgecolor='#10B981', lw=1.5))
ax4.text(0.26, 0.86, "ÜRETİCİ (Görev / Core 1)", ha='center', va='center', color='#34D399', fontweight='bold', fontsize=9)
ax4.text(0.26, 0.76, "1. telemetry_buffer[..] = veri\n2. __DMB() (Data Memory Barrier)\n3. ready.store(1, release)", ha='center', va='center', color='#CBD5E1', fontsize=7.5)
ax4.text(0.26, 0.62, "DMB: Tampon RAM'e yazılmadan\nbayrak ASLA set edilemez!", ha='center', va='center', color='#FDE68A', fontsize=7)

# Tüketici Akışı
ax4.add_patch(patches.Rectangle((0.53, 0.55), 0.42, 0.38, facecolor='#0F172A', edgecolor='#38BDF8', lw=1.5))
ax4.text(0.74, 0.86, "TÜKETİCİ (ISR / Core 2)", ha='center', va='center', color='#38BDF8', fontweight='bold', fontsize=9)
ax4.text(0.74, 0.76, "1. if (ready.load(acquire)) {\n2.   __DMB()\n3.   oku(telemetry_buffer)\n4. }", ha='center', va='center', color='#CBD5E1', fontsize=7.5)
ax4.text(0.74, 0.62, "Acquire: Bayrak 1 ise tamponun\ntam hazır olduğu garantidir!", ha='center', va='center', color='#A7F3D0', fontsize=7)

# Alt Kıyas Tablosu
ax4.add_patch(patches.Rectangle((0.05, 0.10), 0.90, 0.35, facecolor='#1E1B4B', edgecolor='#8B5CF6', lw=1.5))
ax4.text(0.50, 0.38, "NE ZAMAN NE KULLANILMALI? (MİMARİ KARAR TABLOSU)", ha='center', va='center', color='#C084FC', fontweight='bold', fontsize=8.5)
ax4.text(0.50, 0.28, "• Donanım Yazmaçları (MMIO)           -> volatile uint32_t*\n• Kesme ile Paylaşılan Tekil Bayraklar -> volatile bool (veya std::atomic<bool>)\n• Eşzamanlı Sayaç / RMW İşlemleri      -> std::atomic<T> (LDREX / STREX)\n• Çok Elemanlı Veri / Tampon Aktarımı   -> Double-Buffering + DMB / std::atomic", ha='center', va='center', color='#E0E7FF', fontsize=7.5)

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
print("[*] GÜN 167 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert exited_non_vol == False
assert exited_vol == True
assert corrupted_read_value == 0
assert race_sim.shared_counter == 100
assert lost == 34
assert atomic_model.atomic_counter == 134
assert atomic_model.dmb_barrier_executed == True
assert consumed_payload == test_payload
assert telemetry_packet["target_x"] == 12500.5
assert nav_sys.atomic_commit_sequence == 1

print()
print("[PASS] Gün 167: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")

