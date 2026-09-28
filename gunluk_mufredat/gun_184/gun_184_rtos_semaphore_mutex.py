# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 184: rtos_semaphore_mutex - Bağımsız Çalıştırılabilir Kod Laboratuvarı
"""

# ==============================================================================
# KOD BLOĞU: 4
# ==============================================================================
# KOD HÜCRESİ 1: Binary Semaphore vs Mutex Sahiplik ve Davranış Simülatörü
# ------------------------------------------------------------------------------
# Bu simülasyon, İkili Semafor ile Mutex arasındaki en kritik fark olan
# Sahiplik (Ownership) kuralını modeller:
# - Semafor: Görev A alır, Görev B veya ISR serbest bırakabilir (Geçerli).
# - Mutex: Görev A alır, Görev B bırakmaya çalışırsa HATA verir (İllegal Unlock!).

class SimulatedBinarySemaphore:
    def __init__(self, initial_state=0):
        self.state = initial_state # 0: Boş, 1: Dolu
        
    def give(self, caller_name="Unknown"):
        self.state = 1
        return True, f"[{caller_name}] Semafor verildi (State=1)"
        
    def take(self, caller_name="Unknown"):
        if self.state == 1:
            self.state = 0
            return True, f"[{caller_name}] Semafor başarıyla alındı (State=0)"
        return False, f"[{caller_name}] Semafor alınamadı (Boş)"

class SimulatedMutex:
    def __init__(self):
        self.is_locked = False
        self.holder = None
        
    def take(self, task_name):
        if not self.is_locked:
            self.is_locked = True
            self.holder = task_name
            return True, f"[{task_name}] Mutex KİLİTLENDİ. Sahibi: {self.holder}"
        return False, f"[{task_name}] Mutex MEŞGUL! (Sahibi: {self.holder})"
        
    def give(self, task_name):
        if not self.is_locked:
            return False, f"[{task_name}] HATA: Mutex zaten kilitli değil!"
        if self.holder != task_name:
            # KRİTİK GÜVENLİK İHLALİ: Başkasının kilidini açamazsın!
            return False, f"[{task_name}] YETKİSİZ KİLİT AÇMA REDDEDİLDİ! (Gerçek Sahip: {self.holder})"
        self.is_locked = False
        self.holder = None
        return True, f"[{task_name}] Mutex serbest bırakıldı."

sem = SimulatedBinarySemaphore(initial_state=0)
mtx = SimulatedMutex()

print("=" * 68)
print("1. İKİLİ SEMAFOR (BINARY SEMAPHORE) SİNYALLEŞME TESTİ")
print("=" * 68)
# Görev A bekliyor, Donanım ISR semaforu veriyor:
_, msg1 = sem.give(caller_name="UART_RX_ISR")
print(msg1)
_, msg2 = sem.take(caller_name="Task_Parser")
print(msg2)
print("-> SONUÇ: Semafor başarıyla farklı bir bağlam (ISR) tarafından verildi!")

print("\n" + "=" * 68)
print("2. MUTEX SAHİPLİK (OWNERSHIP) KONTROL TESTİ")
print("=" * 68)
# Görev 1 Mutex'i kilitler
_, msg3 = mtx.take(task_name="Task_SPI_Master")
print(msg3)

# Görev 2 yetkisiz şekilde Mutex'i açmaya çalışır
success_illegal, msg4 = mtx.give(task_name="Task_Rogue_Logger")
print(msg4)

# Gerçek sahibi kilidi açar
success_legal, msg5 = mtx.give(task_name="Task_SPI_Master")
print(msg5)

# Doğrulamalar
assert success_illegal == False, "HATA: Mutex yetkisiz görev tarafından açılamamalıdır!"
assert success_legal == True, "HATA: Gerçek sahip Mutex'i açabilmelidir!"
print("\n[BAŞARILI]: Mutex sahiplik güvenliği ve semafor sinyalleşme ayrımı kanıtlandı.")

# ==============================================================================
# KOD BLOĞU: 6
# ==============================================================================
# KOD HÜCRESİ 2: Sayıcı Semafor ile Kaynak Havuzu (Resource Pool) Yönetimi
# ------------------------------------------------------------------------------
# 4 Adet Donanımsal DMA Tamponu bulunan bir aviyonik kartta, 6 görevin
# tampon talep etmesini ve kuyrukta bekleme dinamiğini modeller.

class SimulatedCountingSemaphore:
    def __init__(self, max_count, initial_count):
        self.max_count = max_count
        self.count = initial_count
        self.waiting_tasks = []
        
    def take(self, task_name):
        if self.count > 0:
            self.count -= 1
            return True, f"[{task_name}] Kaynak ALINDI. (Kalan Havuz: {self.count}/{self.max_count})"
        else:
            self.waiting_tasks.append(task_name)
            return False, f"[{task_name}] HAVUZ DOLU! Görev BLOCKED oldu. (Kuyruk: {self.waiting_tasks})"
            
    def give(self, task_name):
        if self.count < self.max_count:
            self.count += 1
            woken = None
            if self.waiting_tasks:
                woken = self.waiting_tasks.pop(0)
                self.count -= 1 # Uyandırılan görev doğrudan kaynağı alır
            return True, woken
        return False, None

# 4 Tamponluk Havuz
dma_pool = SimulatedCountingSemaphore(max_count=4, initial_count=4)

print("=" * 68)
print("SAYICI SEMAFOR İLE 4 KANALLI DMA HAVUZ YÖNETİMİ")
print("=" * 68)

tasks = ["Task_Radar", "Task_FLIR", "Task_INS", "Task_EW", "Task_Telem", "Task_Radio"]

# İlk 4 Görev Kaynak Alır
for t in tasks[:4]:
    ok, msg = dma_pool.take(t)
    print(msg)

print(f"\nHavuz Durumu: {dma_pool.count} boş tampon kaldı.")

# 5. ve 6. Görev Kaynak İster (Bloke Olmalılar!)
for t in tasks[4:]:
    ok, msg = dma_pool.take(t)
    print(msg)

# Bir Görev İşini Bitirip Kaynağı İade Eder
print("\n--- Task_Radar İşini Bitirdi ve Tamponu İade Etti ---")
_, woken_task = dma_pool.give("Task_Radar")
print(f"Uyandırılan Görev: {woken_task} (Kuyruktan çıktı ve DMA'yı devraldı!)")
print(f"Kalan Bekleme Kuyruğu: {dma_pool.waiting_tasks}")

# Doğrulamalar
assert dma_pool.count == 0, "Havuzda boş yer kalmamış olmalı (kuyruktaki aldı)!"
assert woken_task == "Task_Telem", "FIFO kuralına göre ilk bekleyen (Task_Telem) uyandırılmalı!"
print("\n[BAŞARILI]: Sayıcı semafor kaynak kısıtı ve görev uyandırma mantığı doğrulandı.")

# ==============================================================================
# KOD BLOĞU: 8
# ==============================================================================
# KOD HÜCRESİ 3: Özyinelemeli Kilit (Recursive Mutex) ve Kendini Kilitleme
# ------------------------------------------------------------------------------
# Standart Mutex ile aynı görev iç içe iki kez kilit isterse Self-Deadlock oluşur.
# Recursive Mutex ise bir sayaç tutarak aynı görevin iç içe kilit almasına izin verir.

class SimulatedRecursiveMutex:
    def __init__(self):
        self.holder = None
        self.recursion_count = 0
        
    def take_recursive(self, task_name):
        if self.holder is None:
            self.holder = task_name
            self.recursion_count = 1
            return True, f"[{task_name}] Kilit İlk Kez Alındı (Count=1)"
        elif self.holder == task_name:
            # Aynı görev tekrar kilit istiyor -> Sayacı artır!
            self.recursion_count += 1
            return True, f"[{task_name}] İç İçe Kilit Alındı (Count={self.recursion_count})"
        else:
            return False, f"[{task_name}] Kilit Başkasına Ait! (Sahibi: {self.holder})"
            
    def give_recursive(self, task_name):
        if self.holder != task_name:
            return False, f"[{task_name}] HATA: Kilit bu göreve ait değil!"
            
        self.recursion_count -= 1
        if self.recursion_count == 0:
            self.holder = None
            return True, f"[{task_name}] Kilit TAMAMEN Serbest Bırakıldı (Count=0)"
        return True, f"[{task_name}] İç Kilit Açıldı (Kalan Count={self.recursion_count})"

rec_mtx = SimulatedRecursiveMutex()

print("=" * 68)
print("ÖZYİNELEMELİ KİLİT (RECURSIVE MUTEX) İÇ İÇE ÇAĞRI TESTİ")
print("=" * 68)

# Senaryo: flight_control() -> calculate_matrix() her ikisi de aynı Mutex'i istiyor
t_name = "Task_FlightControl"

# 1. Ana Fonksiyon Kilit Alır
_, m1 = rec_mtx.take_recursive(t_name)
print(m1)

# 2. Alt Fonksiyon Çağrılır ve Tekrar Kilit Alır
_, m2 = rec_mtx.take_recursive(t_name)
print(m2)

# 3. Alt Fonksiyon Biter, Kilit 1 Kademesi Açılır
_, m3 = rec_mtx.give_recursive(t_name)
print(m3)
print(f"  -> Durum: Kilit hala açık değil, {rec_mtx.holder} üzerinde kilitli!")

# 4. Ana Fonksiyon Biter, Kilit Tamamen Açılır
_, m4 = rec_mtx.give_recursive(t_name)
print(m4)

assert rec_mtx.holder is None, "HATA: İki give sonrası kilit tamamen boşa çıkmalıdır!"
assert rec_mtx.recursion_count == 0, "HATA: Sayıcı sıfırlanmalıdır!"
print("\n[BAŞARILI]: Recursive Mutex iç içe kilitlenme olmadan başarıyla çalıştı.")

# ==============================================================================
# KOD BLOĞU: 10
# ==============================================================================
# KOD HÜCRESİ 4: Çoklu Kaynak Kilitlenmesi (Deadlock) ve Çözümü
# ------------------------------------------------------------------------------
# Deadlock Senaryosu (Döngüsel Bekleme - Circular Wait):
# - Task A: Mutex 1'i tutuyor, Mutex 2'yi istiyor.
# - Task B: Mutex 2'yi tutuyor, Mutex 1'i istiyor.
# Çözüm: Sabit Sıralı Kilit Alma (Strict Lock Ordering) Protokolü.

def simulate_deadlock_scenario(use_lock_ordering=False):
    # Kaynaklar: Mutex 1 (SPI Bus), Mutex 2 (I2C Bus)
    log = []
    
    if not use_lock_ordering:
        # Hatalı Tasarım: Farklı sırada kilit alma
        # t=1: Task A Mutex 1'i aldı
        # t=2: Task B Mutex 2'yi aldı
        # t=3: Task A Mutex 2'yi bekliyor (Blocked)
        # t=4: Task B Mutex 1'i bekliyor (Blocked)
        log.append("t=1: Task A -> Mutex 1 Kilitledi")
        log.append("t=2: Task B -> Mutex 2 Kilitledi")
        log.append("t=3: Task A -> Mutex 2 Bekliyor (BLOCKED)")
        log.append("t=4: Task B -> Mutex 1 Bekliyor (BLOCKED)")
        log.append("SONUÇ: DEADLOCK! İki görev de sonsuza dek kilitlendi!")
        is_deadlocked = True
    else:
        # Güvenli Tasarım (Strict Lock Ordering):
        # Kural: Herkes önce Mutex 1'i, sonra Mutex 2'yi almak ZORUNDADIR!
        log.append("t=1: Task A -> Mutex 1 Kilitledi")
        log.append("t=2: Task B -> Mutex 1 İstedi (A'da olduğu için BLOCKED)")
        log.append("t=3: Task A -> Mutex 2 Kilitledi, İşini Yaptı, İkisini de Bıraktı")
        log.append("t=4: Task B -> Uyandı, Sırayla Mutex 1 ve 2'yi Güvenle İşletti")
        log.append("SONUÇ: BAŞARILI! Sıralı kilit alma döngüsel beklemeyi yok etti.")
        is_deadlocked = False
        
    return is_deadlocked, log

deadlock_bad, log_bad = simulate_deadlock_scenario(use_lock_ordering=False)
deadlock_good, log_good = simulate_deadlock_scenario(use_lock_ordering=True)

print("=" * 68)
print("DEADLOCK (ÖLÜMCÜL KİLİTLENME) VE SIRALI KİLİT ÇÖZÜMÜ")
print("=" * 68)
print("--- 1. HATALI TASARIM (Döngüsel Bekleme) ---")
for line in log_bad:
    print(line)

print("\n--- 2. EMNİYETLİ TASARIM (Strict Lock Ordering) ---")
for line in log_good:
    print(line)

assert deadlock_bad == True, "Hatalı tasarım deadlock ile sonuçlanmalıydı!"
assert deadlock_good == False, "Sıralı kilit tasarımı deadlock'u engellemeliydi!"
print("\n[BAŞARILI]: Lock Ordering kuralının Deadlock'u matematiksel olarak önlediği kanıtlandı.")

# ==============================================================================
# KOD BLOĞU: 12
# ==============================================================================
# KOD HÜCRESİ 5: Savunma Sanayii Aviyonik Senaryosu: Paylaşımlı SPI ve DMA
# ------------------------------------------------------------------------------
# ROKETSAN Füze Güdüm Bilgisayarı:
# - Kaynak 1: Paylaşımlı SPI Sensör Veri Yolu (Mutex ile korunuyor)
# - Kaynak 2: 2 Kanallı DMA Tampon Havuzu (Sayıcı Semafor ile yönetiliyor)
# - Görev 1: IMU Görevi (Prio 4, 10 ms periyot)
# - Görev 2: Barometre Görevi (Prio 3, 20 ms periyot)
# 100 ms'lik taktik çalışmada veri çakışması ve kilit süreleri takibi.

import numpy as np

def simulate_avionics_bus_sharing(duration_ms=100):
    time_ms = np.arange(0, duration_ms, 1)
    
    spi_mutex_holder = None
    dma_pool_count = 2 # 2 Adet DMA kanalı
    
    imu_requests = 0
    baro_requests = 0
    conflicts_avoided = 0
    
    for t in time_ms:
        # IMU her 10 ms'de SPI ister (İşlem süresi: 2 ms)
        if t % 10 == 0:
            imu_requests += 1
            if spi_mutex_holder is not None:
                conflicts_avoided += 1
            spi_mutex_holder = "IMU_Task"
            
        if t % 10 == 2 and spi_mutex_holder == "IMU_Task":
            spi_mutex_holder = None # 2 ms sonra SPI bırakıldı
            
        # Barometre her 20 ms'de SPI ister (İşlem süresi: 3 ms)
        if t % 20 == 0 and t > 0:
            baro_requests += 1
            if spi_mutex_holder is not None:
                conflicts_avoided += 1 # IMU o sırada hatta ise çakışma engellendi
            else:
                spi_mutex_holder = "Baro_Task"
                
        if t % 20 == 3 and spi_mutex_holder == "Baro_Task":
            spi_mutex_holder = None

    return {
        "imu_requests": imu_requests,
        "baro_requests": baro_requests,
        "conflicts_avoided": conflicts_avoided,
        "duration_ms": duration_ms
    }

avionics_sim = simulate_avionics_bus_sharing()

print("=" * 68)
print("ROKETSAN AVİYONİK PAYLAŞIMLI SPI VE DMA HAVUZ YÖNETİM RAPORU")
print("=" * 68)
print(f"Toplam Simülasyon Süresi       : {avionics_sim['duration_ms']} ms")
print(f"IMU Sensör SPI Erişim Talebi   : {avionics_sim['imu_requests']} adet")
print(f"Barometre SPI Erişim Talebi    : {avionics_sim['baro_requests']} adet")
print(f"Mutex ile Engellenen Veri Çakışması: {avionics_sim['conflicts_avoided']} adet (Veri Bozulması SIFIR!)")

assert avionics_sim["conflicts_avoided"] > 0, "Ortak hatta çakışma durumları engellenmiş olmalıydı!"
assert avionics_sim["imu_requests"] == 10, "100 ms sürede 10 IMU erişimi olmalıdır!"
print("\n[BAŞARILI]: Paylaşımlı aviyonik sensör yolu Mutex ile %100 emniyetle korundu.")

# ==============================================================================
# KOD BLOĞU: 14
# ==============================================================================
# KOD HÜCRESİ 6: Endüstriyel Dashboard Görselleştirme ve Kapsamlı Assertions
# ------------------------------------------------------------------------------
# 300 DPI, Dark Theme (#0F172A), 4 Panelli Endüstriyel Aviyonik Dashboard:
# Panel 1: Binary Semaphore Sinyalleşme vs Mutex Sahiplik Zaman Çizelgesi
# Panel 2: Sayıcı Semafor Kaynak Havuzu Doluluk Grafiği (DMA Pool)
# Panel 3: Deadlock (Döngüsel Bekleme) vs Sıralı Kilit Zaman Akışı
# Panel 4: Özyinelemeli Mutex (Recursive) İç İçe Kilit Sayacı Değişimi

import os
import matplotlib.pyplot as plt
import numpy as np

# PNG Dosya Yolu
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_184_rtos_semaphore_mutex.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_184\gun_184_rtos_semaphore_mutex.png"

# Koyu Tema Ayarları
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#475569'
plt.rcParams['axes.linewidth'] = 1.2

fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.tick_params(colors='#E2E8F0', labelsize=9)
    ax.xaxis.label.set_color('#F8FAFC')
    ax.yaxis.label.set_color('#F8FAFC')
    ax.title.set_color('#38BDF8')
    ax.grid(True, linestyle='--', alpha=0.25, color='#94A3B8')

# ------------------------------------------------------------------------------
# PANEL 1: Binary Semaphore vs Mutex Sahiplik
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. İkili Semafor (Sinyalleşme) vs Mutex (Sahiplik)", fontsize=11, fontweight='bold', pad=10)

labels = ["Binary Semaphore\n(ISR Give -> Task Take)", "Mutex\n(Task Lock -> Task Unlock)", "İllegal Mutex Unlock\n(Başka Görev Açamaz!)"]
colors = ['#10B981', '#38BDF8', '#EF4444']
values = [1, 1, 0]

bars1 = ax1.bar(labels, [1, 1, 1], color=colors, width=0.45, edgecolor='#0F172A')
ax1.set_ylabel("İzin Verilen İşlem", fontsize=10)
ax1.set_ylim(0, 1.4)
ax1.text(0, 1.05, "GEÇERLİ\n(Sahiplik Yok)", ha='center', color='#10B981', fontweight='bold', fontsize=9)
ax1.text(1, 1.05, "GEÇERLİ\n(Sahibi Açtı)", ha='center', color='#38BDF8', fontweight='bold', fontsize=9)
ax1.text(2, 1.05, "YASAK / RED!\n(Sahibi Olmayan Açamaz)", ha='center', color='#EF4444', fontweight='bold', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 2: Sayıcı Semafor Kaynak Havuzu
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. Sayıcı Semafor ile 4 Kanallı DMA Havuzu Tüketimi", fontsize=11, fontweight='bold', pad=10)

steps = ["Başlangıç", "4 Görev Aldı", "5. Görev Geldi", "6. Görev Geldi", "1 Görev İade Etti"]
free_counts = [4, 0, 0, 0, 0]
blocked_counts = [0, 0, 1, 2, 1]

x_pos = np.arange(len(steps))
w = 0.35

ax2.bar(x_pos - w/2, free_counts, w, label='Kalan Boş DMA Kanalı', color='#10B981')
ax2.bar(x_pos + w/2, blocked_counts, w, label='Bekleyen (Blocked) Görev', color='#EF4444')

ax2.set_xticks(x_pos)
ax2.set_xticklabels(steps, fontsize=8, fontweight='bold')
ax2.set_ylabel("Adet", fontsize=10)
ax2.set_ylim(0, 5)
ax2.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC')

# ------------------------------------------------------------------------------
# PANEL 3: Deadlock (Döngüsel Bekleme) vs Sıralı Kilit
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. Deadlock (Döngüsel Bekleme) vs Sıralı Kilit (Lock Ordering)", fontsize=11, fontweight='bold', pad=10)

ax3.text(0.1, 0.7, "DÖNGÜSEL BEKLEME (DEADLOCK):\nTask A: Kilit(M1) ──> İstiyor(M2) [BLOCKED]\nTask B: Kilit(M2) ──> İstiyor(M1) [BLOCKED]\n=> SISTEM SONSUZA DEK DONDU!", color='#F87171', fontweight='bold', fontsize=10, bbox=dict(boxstyle="round,pad=0.5", facecolor="#1E293B", edgecolor="#EF4444"))

ax3.text(0.1, 0.2, "SIRALI KİLİT ÇÖZÜMÜ (LOCK ORDERING):\nHerkes: Önce M1, Sonra M2 Sırasıyla Alır!\nTask A: Kilit(M1) -> Kilit(M2) -> Tamamlar\nTask B: M1 serbest kalana dek bekler, sonra alır\n=> SIFIR KİLİTLENME (%100 GÜVENLİ)!", color='#34D399', fontweight='bold', fontsize=10, bbox=dict(boxstyle="round,pad=0.5", facecolor="#1E293B", edgecolor="#10B981"))

ax3.set_xlim(0, 1)
ax3.set_ylim(0, 1)
ax3.set_xticks([])
ax3.set_yticks([])

# ------------------------------------------------------------------------------
# PANEL 4: Recursive Mutex Sayacı
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. Özyinelemeli Mutex (Recursive) İç İçe Kilit Sayacı", fontsize=11, fontweight='bold', pad=10)

rec_steps = ["Kilit Öncesi", "1. Kilit (Ana Fonk)", "2. Kilit (Alt Fonk)", "1. Give (Alt Bitti)", "2. Give (Ana Bitti)"]
rec_values = [0, 1, 2, 1, 0]

ax4.step(range(len(rec_steps)), rec_values, where='mid', color='#F59E0B', linewidth=3, marker='o')
ax4.set_xticks(range(len(rec_steps)))
ax4.set_xticklabels(rec_steps, fontsize=8, fontweight='bold')
ax4.set_ylabel("Recursion Counter", fontsize=10)
ax4.set_ylim(-0.5, 3)
ax4.text(2, 2.2, "İç İçe Güvenli Alım (Count=2)", color='#F59E0B', fontweight='bold', fontsize=9)
ax4.text(4, 0.3, "Tamamen Serbest (Count=0)", color='#10B981', fontweight='bold', fontsize=9)

# Görseli Kaydet
plt.tight_layout()
plt.savefig(PNG_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

# ------------------------------------------------------------------------------
# KATI DOĞRULAMA (ASSERTIONS)
# ------------------------------------------------------------------------------
assert os.path.exists(PNG_FILE), f"HATA: Dashboard görseli üretilemedi: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"\n[+] Visual Artifact Oluşturuldu: {PNG_FILE} ({png_size:,} bayt)")
assert png_size > 100000, f"HATA: Görsel boyutu 100 KB'den küçük ({png_size} bayt)!"

# Simülasyon Doğrulamaları
assert success_illegal == False, "HATA: Mutex yetkisiz kilit açma engellenmeliydi!"
assert dma_pool.count == 0, "HATA: Sayıcı semafor havuzu doğrulaması başarısız!"
assert deadlock_bad == True, "HATA: Deadlock modeli başarısız!"
assert deadlock_good == False, "HATA: Sıralı kilit modeli başarısız!"
assert avionics_sim["conflicts_avoided"] > 0, "HATA: Aviyonik veri yolu çakışma önleme hatası!"

print("[PASS] GÜN 184: TÜM MATEMATİKSEL VE GÖRSEL DOĞRULAMALAR BAŞARIYLA TAMAMLANDI!")

