# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
GÜN 180: task_thread_ve_scheduler - Bağımsız Çalıştırılabilir Kod Laboratuvarı
"""

# ==============================================================================
# KOD BLOĞU: 4
# ==============================================================================
# KOD HÜCRESİ 1: FreeRTOS Task State Machine & O(1) Bitmask Scheduler Simülatörü
# ------------------------------------------------------------------------------
# Bu simülasyon, FreeRTOS görev durum makinesini (State Machine) ve ARM Cortex-M
# donanımında tek saat çevriminde en yüksek önceliği bulan O(1) Bitmask (CLZ)
# çizelgeleme algoritmasını modeller.

class TaskState:
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"

class SimulatedTask:
    def __init__(self, task_id, name, priority, period_ticks, compute_ticks):
        self.task_id = task_id
        self.name = name
        self.priority = priority # 0 (En düşük / Idle) .. 31 (En yüksek)
        self.period_ticks = period_ticks
        self.compute_ticks = compute_ticks
        self.rem_compute = compute_ticks
        self.block_timeout = 0
        self.state = TaskState.READY
        self.total_run_ticks = 0

class FreeRTOSSchedulerO1:
    def __init__(self, max_priorities=32):
        self.max_priorities = max_priorities
        # Her öncelik seviyesi için Ready List (Çift yönlü bağlı liste simülasyonu)
        self.ready_lists = [[] for _ in range(max_priorities)]
        self.blocked_list = []
        # Donanımsal 32-bit Bitmask: Hangi öncelikte hazır görev var?
        self.ready_priority_bitmask = 0
        self.current_running_task = None
        self.tick_count = 0
        
    def add_task(self, task):
        self._add_to_ready(task)
        
    def _add_to_ready(self, task):
        task.state = TaskState.READY
        self.ready_lists[task.priority].append(task)
        # Bitmask'te ilgili önceliğin bitini 1 yap (O(1))
        self.ready_priority_bitmask |= (1 << task.priority)
        
    def _remove_from_ready(self, task):
        if task in self.ready_lists[task.priority]:
            self.ready_lists[task.priority].remove(task)
            if len(self.ready_lists[task.priority]) == 0:
                # O öncelikte hiç görev kalmadıysa biti 0 yap (O(1))
                self.ready_priority_bitmask &= ~(1 << task.priority)

    def find_highest_priority_clz(self):
        """ARM Cortex-M __CLZ (Count Leading Zeros) donanımsal O(1) emülasyonu"""
        if self.ready_priority_bitmask == 0:
            return 0 # Sadece Idle Task kalmış
        # Python'da 32-bit integer CLZ eşdeğeri: bit_length
        highest_prio = self.ready_priority_bitmask.bit_length() - 1
        return highest_prio

    def step_tick(self):
        self.tick_count += 1
        
        # 1. Blokeli görevlerin zaman aşımını kontrol et
        unblocked = []
        for task in self.blocked_list:
            task.block_timeout -= 1
            if task.block_timeout <= 0:
                unblocked.append(task)
                
        for task in unblocked:
            self.blocked_list.remove(task)
            task.rem_compute = task.compute_ticks
            self._add_to_ready(task)
            
        # 2. Çalışan görevin durumunu güncelle
        if self.current_running_task is not None:
            self.current_running_task.rem_compute -= 1
            self.current_running_task.total_run_ticks += 1
            
            if self.current_running_task.rem_compute <= 0:
                # Görev işini bitirdi -> Bir sonraki periyoda kadar BLOCKED durumuna geç
                self.current_running_task.state = TaskState.BLOCKED
                self.current_running_task.block_timeout = max(1, self.current_running_task.period_ticks - self.current_running_task.compute_ticks)
                self.blocked_list.append(self.current_running_task)
                self.current_running_task = None
            else:
                # İş henüz bitmedi, hazır listesine geri bırak (Time-Slicing için arkaya ekle)
                self._add_to_ready(self.current_running_task)
                self.current_running_task = None
                
        # 3. O(1) CLZ ile en yüksek öncelikli görevi seç
        top_prio = self.find_highest_priority_clz()
        if len(self.ready_lists[top_prio]) > 0:
            next_task = self.ready_lists[top_prio].pop(0)
            if len(self.ready_lists[top_prio]) == 0:
                self.ready_priority_bitmask &= ~(1 << top_prio)
            next_task.state = TaskState.RUNNING
            self.current_running_task = next_task
            return next_task.name, next_task.priority
            
        return "IDLE_TASK", 0

# Test Senaryosu Oluştur
sched = FreeRTOSSchedulerO1()
t_ins = SimulatedTask(1, "INS_EKF", priority=4, period_ticks=5, compute_ticks=1)
t_pwm = SimulatedTask(2, "Fin_PWM", priority=4, period_ticks=5, compute_ticks=1)
t_telem = SimulatedTask(3, "Telemetry", priority=1, period_ticks=10, compute_ticks=3)
t_idle = SimulatedTask(0, "IdleTask", priority=0, period_ticks=1, compute_ticks=1)

for t in [t_ins, t_pwm, t_telem, t_idle]:
    sched.add_task(t)

print("=" * 68)
print("FREERTOS O(1) BITMASK SCHEDULER VE TASK STATE MACHINE SİMÜLASYONU")
print("=" * 68)

execution_log = []
for tick in range(1, 21):
    running_name, running_prio = sched.step_tick()
    execution_log.append((tick, running_name, running_prio, sched.ready_priority_bitmask))
    if tick <= 10 or tick >= 18:
        print(f"Tick {tick:02d}: Koşan Görev = {running_name:<10} (Öncelik {running_prio}) | Bitmask: 0x{sched.ready_priority_bitmask:08X} ({bin(sched.ready_priority_bitmask)})")

# Matematiksel doğrulama
assert t_ins.total_run_ticks > 0, "HATA: INS_EKF çalışmalıydı!"
assert t_pwm.total_run_ticks > 0, "HATA: Fin_PWM çalışmalıydı!"
assert sched.ready_priority_bitmask & (1 << 0) != 0 or sched.current_running_task.name == "IdleTask", "Idle task her zaman hazır olmalı!"
print("\n[BAŞARILI]: Donanımsal O(1) Bitmask CLZ algoritması ve Task State Machine doğrulandı.")

# ==============================================================================
# KOD BLOĞU: 6
# ==============================================================================
# KOD HÜCRESİ 2: Round-Robin Time-Slicing vs Non-Time-Slicing
# ------------------------------------------------------------------------------
# Aynı önceliğe sahip birden fazla görev hazır olduğunda:
# 1. configUSE_TIME_SLICING = 1: Her SysTick kesmesinde adil Round-Robin geçişi
# 2. configUSE_TIME_SLICING = 0: Bir görev bitene veya cooperatively yield edene kadar CPU'yu tutar.

import numpy as np

def simulate_round_robin(time_slicing_enabled=True, total_ticks=24):
    # 3 Adet Eşit Öncelikli Görev (Öncelik 2)
    # Her birinin 6 tick iş yükü var
    tasks = {
        "Fin_Actuator_Left":  {"rem": 6, "runs": []},
        "Fin_Actuator_Right": {"rem": 6, "runs": []},
        "Fin_Actuator_Rudder": {"rem": 6, "runs": []},
    }
    
    ready_queue = list(tasks.keys())
    timeline = []
    context_switch_count = 0
    last_task = None
    
    for tick in range(total_ticks):
        if not ready_queue:
            timeline.append("IDLE")
            continue
            
        current = ready_queue[0]
        
        if last_task is not None and last_task != current:
            context_switch_count += 1
        last_task = current
        
        tasks[current]["rem"] -= 1
        tasks[current]["runs"].append(tick)
        timeline.append(current)
        
        if tasks[current]["rem"] <= 0:
            # Görev tamamlandı -> Kuyruktan çıkar
            ready_queue.pop(0)
        else:
            if time_slicing_enabled:
                # Time-slicing aktif: Görevi kuyruğun en arkasına at (Round-Robin)
                ready_queue.pop(0)
                ready_queue.append(current)
            else:
                # Time-slicing kapalı: Görev işi bitene kadar kuyruğun başında kalır!
                pass
                
    return {
        "timeline": timeline,
        "context_switch_count": context_switch_count,
        "tasks": tasks
    }

res_ts_on = simulate_round_robin(time_slicing_enabled=True)
res_ts_off = simulate_round_robin(time_slicing_enabled=False)

print("=" * 68)
print("ROUND-ROBIN TIME-SLICING ETKİSİ (EŞİT ÖNCELİKLİ GÖREVLER)")
print("=" * 68)
print(f"Zaman Dilimleme AÇIK  (configUSE_TIME_SLICING = 1):")
print(f"  - Context Switch Sayısı : {res_ts_on['context_switch_count']} adet")
print(f"  - İlk 9 Tick Sıralaması: {res_ts_on['timeline'][:9]}")

print(f"\nZaman Dilimleme KAPALI (configUSE_TIME_SLICING = 0):")
print(f"  - Context Switch Sayısı : {res_ts_off['context_switch_count']} adet")
print(f"  - İlk 9 Tick Sıralaması: {res_ts_off['timeline'][:9]}")

# Doğrulama: Time slicing açıkken görevler 1'er tick sırayla koşmalı
assert res_ts_on["timeline"][0] != res_ts_on["timeline"][1], "Time-slicing açıkken ardışık tickler farklı görev olmalı!"
assert res_ts_off["timeline"][0] == res_ts_off["timeline"][1], "Time-slicing kapalıyken görev bitene kadar koşmalı!"
print("\n[BAŞARILI]: Round-Robin Time-Slicing adaleti ve context switch farkı doğrulandı.")

# ==============================================================================
# KOD BLOĞU: 8
# ==============================================================================
# KOD HÜCRESİ 3: TCB Bellek Haritası ve Stack High Water Mark Analizörü
# ------------------------------------------------------------------------------
# FreeRTOS, görev yığınını 0xA5 deseniyle başlatır.
# Bu kod, bellek haritasını, yığının aşağı doğru büyümesini (Full Descending Stack)
# ve uxTaskGetStackHighWaterMark() fonksiyonunun çalışma prensibini modeller.

class SimulatedTCB:
    def __init__(self, name, priority, stack_size_words=256):
        self.name = name
        self.priority = priority
        self.stack_size_words = stack_size_words
        self.stack_size_bytes = stack_size_words * 4
        
        # 1. Yığını FreeRTOS standardı olan 0xA5 deseniyle doldur
        self.stack_memory = bytearray([0xA5] * self.stack_size_bytes)
        
        # ARM Cortex-M Full-Descending Stack: Yığın en yüksek adresten başlar, aşağı büyür
        self.stack_base_offset = 0 # En alt adres (Taşma sınırı)
        self.stack_top_offset = self.stack_size_bytes # Başlangıç SP adresi (Full-descending stack)
        self.current_sp = self.stack_top_offset
        
    def simulate_push(self, num_bytes):
        """Fonksiyon çağrısı veya yerel değişken tahsisi (Yığın aşağı büyür)"""
        new_sp = self.current_sp - num_bytes
        if new_sp < self.stack_base_offset:
            raise MemoryError(f"CRITICAL STACK OVERFLOW! Task '{self.name}' yığın sınırını {abs(new_sp)} bayt aştı!")
            
        # Belleği rastgele çalışma verisiyle ez (0xA5 desenini boz)
        for offset in range(new_sp, self.current_sp):
            self.stack_memory[offset] = 0x55 # Çalışma verisi
        self.current_sp = new_sp
        
    def simulate_pop(self, num_bytes):
        """Fonksiyon dönüşü (SP yukarı çıkar, ancak eski veri bellekte kalır)"""
        self.current_sp = min(self.stack_top_offset, self.current_sp + num_bytes)

    def get_stack_high_water_mark(self):
        """uxTaskGetStackHighWaterMark(): Taban adresinden itibaren bozulmamış 0xA5 sayısını say"""
        unused_bytes = 0
        for byte_val in self.stack_memory:
            if byte_val == 0xA5:
                unused_bytes += 1
            else:
                break
        # FreeRTOS bu değeri KELİME (Word = 4 bayt) cinsinden döndürür
        return unused_bytes // 4

# Test Senaryosu: 1024 Baytlık (256 Word) Aviyonik Telemetri Görevi
tcb = SimulatedTCB("TelemTask", priority=2, stack_size_words=256)

print("=" * 68)
print("TCB BELLEK HARİTASI VE STACK HIGH WATER MARK ANALİZİ")
print("=" * 68)
init_hwm = tcb.get_stack_high_water_mark()
print(f"Görev Başlatıldı (Toplam Yığın: {tcb.stack_size_bytes} bayt / {tcb.stack_size_words} kelime):")
print(f"  - Başlangıç Stack High Water Mark: {init_hwm} kelime (%{init_hwm/tcb.stack_size_words*100:.1f} boş alan)")

# 1. Normal Çalışma: 32 baytlık interrupt frame + 64 baytlık yerel değişken
tcb.simulate_push(96)
tcb.simulate_pop(64) # Fonksiyon döndü
hwm_step1 = tcb.get_stack_high_water_mark()
print(f"\nAdım 1: Normal Fonksiyon Çağrısı (96 bayt tepe tüketimi):")
print(f"  - Kalan High Water Mark: {hwm_step1} kelime ({hwm_step1*4} bayt hiç dokunulmadı)")

# 2. Ağır Yük: İç içe derin fonksiyon çağrıları (600 bayt tüketim)
tcb.simulate_push(600)
hwm_step2 = tcb.get_stack_high_water_mark()
print(f"\nAdım 2: Derin İç İçe Çağrılar (Toplam 696 bayt tepe tüketimi):")
print(f"  - Kalan High Water Mark: {hwm_step2} kelime ({hwm_step2*4} bayt kaldı!)")

# 3. Yığın Taşması Eşiği Testi
overflow_detected = False
try:
    # 400 bayt daha tahsis etmeye çalış (Toplam 1096 bayt > 1024 bayt!)
    tcb.simulate_push(400)
except MemoryError as e:
    overflow_detected = True
    print(f"\n[GÜVENLİK YAKALANDI]: {e}")

assert hwm_step1 == 256 - (96 // 4), "Adım 1 HWM hesabı doğru olmalı!"
assert overflow_detected == True, "HATA: Yığın taşması yakalanamadı!"
print("\n[BAŞARILI]: 0xA5 yığın deseni ve High Water Mark tespit mekanizması doğrulandı.")

# ==============================================================================
# KOD BLOĞU: 10
# ==============================================================================
# KOD HÜCRESİ 4: Tickless Idle ve Güç Tüketimi Matematiksel Modeli
# ------------------------------------------------------------------------------
# Klasik RTOS: Her 1 ms'de bir SysTick kesmesi CPU'yu uyandırır (1000 uyandırma/sn).
# Tickless Idle: Gelecekteki ilk göreve kadar (örn. 50 ms) SysTick durdurulur,
# Low-Power Timer kurulur ve MCU STOP/STANDBY modunda derin uykuya dalar.

class LowPowerModel:
    def __init__(self, v_supply=3.3, i_run_ma=40.0, i_sleep_ma=0.015, battery_mah=2500):
        self.v_supply = v_supply
        self.i_run_ma = i_run_ma       # Aktif Mod Akımı (STM32 @ 168 MHz)
        self.i_sleep_ma = i_sleep_ma   # Düşük Güç Stop Modu Akımı (15 µA)
        self.battery_mah = battery_mah # 2500 mAh Li-Ion Pil
        
    def calculate_consumption(self, active_duty_cycle_percent=5.0, tickless_enabled=False):
        # active_duty_cycle_percent: Görevlerin gerçek CPU kullanma yüzdesi (örn. %5)
        # Geriye kalan %95 zamanda sistem boştadır (Idle)
        
        t_active_ratio = active_duty_cycle_percent / 100.0
        t_idle_ratio = 1.0 - t_active_ratio
        
        if not tickless_enabled:
            # Standart RTOS: Idle durumunda her 1 ms'de bir SysTick uyanır.
            # SysTick ISR süresi: ~20 µs = %2 ek çalışma yükü!
            # Ayrıca derin uykuya (STOP) geçilemez, sadece hafif uyku (WFI) kullanılır (i_idle = 8 mA)
            i_idle_mode_ma = 8.0
            avg_current_ma = (t_active_ratio * self.i_run_ma) + (t_idle_ratio * i_idle_mode_ma)
        else:
            # Tickless Idle: SysTick durdurulur, STOP modunda 15 µA tüketilir
            avg_current_ma = (t_active_ratio * self.i_run_ma) + (t_idle_ratio * self.i_sleep_ma)
            
        battery_hours = self.battery_mah / avg_current_ma
        battery_days = battery_hours / 24.0
        
        return {
            "avg_current_ma": avg_current_ma,
            "battery_hours": battery_hours,
            "battery_days": battery_days
        }

lp = LowPowerModel(v_supply=3.3, i_run_ma=45.0, i_sleep_ma=0.02, battery_mah=3000)

res_standard = lp.calculate_consumption(active_duty_cycle_percent=4.0, tickless_enabled=False)
res_tickless = lp.calculate_consumption(active_duty_cycle_percent=4.0, tickless_enabled=True)

energy_saving_percent = (1.0 - res_tickless["avg_current_ma"] / res_standard["avg_current_ma"]) * 100.0

print("=" * 68)
print("TICKLESS IDLE GÜÇ TÜKETİMİ VE PİL ÖMRÜ MATEMATİKSEL ANALİZİ")
print("=" * 68)
print(f"Standart Periyodik SysTick Modu (configUSE_TICKLESS_IDLE = 0):")
print(f"  - Ortalama Akım Tüketimi: {res_standard['avg_current_ma']:.2f} mA")
print(f"  - Pil Ömrü               : {res_standard['battery_days']:.1f} gün ({res_standard['battery_hours']:.0f} saat)")

print(f"\nTickless Idle Düşük Güç Modu (configUSE_TICKLESS_IDLE = 1):")
print(f"  - Ortalama Akım Tüketimi: {res_tickless['avg_current_ma']:.2f} mA")
print(f"  - Pil Ömrü               : {res_tickless['battery_days']:.1f} gün ({res_tickless['battery_hours']:.0f} saat)")
print(f"\nEnerji Tasarrufu Oranı   : %{energy_saving_percent:.2f}")

assert res_tickless["avg_current_ma"] < res_standard["avg_current_ma"], "Tickless idle daha az akım çekmeli!"
assert energy_saving_percent > 70.0, "Enerji tasarrufu %70'ten büyük olmalı!"
print("\n[BAŞARILI]: Tickless Idle mimarisinin batarya ömrünü katlama etkisi matematiksel olarak kanıtlandı.")

# ==============================================================================
# KOD BLOĞU: 12
# ==============================================================================
# KOD HÜCRESİ 5: Savunma Sanayii Aviyonik Senaryosu: Füze Uçuş Bilgisayarı
# ------------------------------------------------------------------------------
# ROKETSAN Füze Güdüm Bilgisayarı Görev Seti Simülasyonu:
# - Task 1: INS Navigation EKF (Prio 4, 10 ms periyot, 2 ms WCET)
# - Task 2: Fin Control PWM    (Prio 4, 10 ms periyot, 2 ms WCET - Time-Sliced!)
# - Task 3: Mission FSM        (Prio 2, 20 ms periyot, 3 ms WCET)
# - Task 4: Telemetry Link     (Prio 1, 50 ms periyot, 5 ms WCET)
# - Task 0: Idle Task          (Prio 0, Arka plan sistem sağlığı)
# Simülasyon 100 ms boyunca görev durumlarını ve CPU kullanımını kaydeder.

import numpy as np

def simulate_missile_flight_computer(sim_duration_ms=100, tick_ms=1):
    ticks = int(sim_duration_ms / tick_ms)
    time_axis = np.arange(0, sim_duration_ms, tick_ms)
    
    tasks = {
        "INS_EKF":     {"prio": 4, "period": 10, "wcet": 2, "rem": 0, "next_wake": 0, "state_history": []},
        "Fin_Actuator":{"prio": 4, "period": 10, "wcet": 2, "rem": 0, "next_wake": 0, "state_history": []},
        "Mission_FSM": {"prio": 2, "period": 20, "wcet": 3, "rem": 0, "next_wake": 0, "state_history": []},
        "Telemetry":   {"prio": 1, "period": 50, "wcet": 5, "rem": 0, "next_wake": 0, "state_history": []},
    }
    
    cpu_running_history = []
    
    # Eşit öncelikli görevler için Round-Robin kuyruğu
    prio4_rr_turn = 0
    
    for t in time_axis:
        # 1. Periyodu gelen görevleri READY yap
        for name, tinfo in tasks.items():
            if t >= tinfo["next_wake"]:
                tinfo["rem"] = tinfo["wcet"]
                tinfo["next_wake"] += tinfo["period"]

        # 2. Hazır görevleri filtrele
        ready_tasks = [name for name, tinfo in tasks.items() if tinfo["rem"] > 0]
        
        # 3. En yüksek önceliği bul
        if not ready_tasks:
            current_task = "Idle_Task"
        else:
            max_prio = max(tasks[name]["prio"] for name in ready_tasks)
            candidates = [name for name in ready_tasks if tasks[name]["prio"] == max_prio]
            
            if len(candidates) > 1:
                # Eşit öncelikli görevlerde Time-Slicing Round-Robin
                current_task = candidates[prio4_rr_turn % len(candidates)]
                prio4_rr_turn += 1
            else:
                current_task = candidates[0]
                
        cpu_running_history.append(current_task)
        
        # 4. Çalışan görevin süresini azalt ve durumları kaydet
        if current_task != "Idle_Task":
            tasks[current_task]["rem"] -= tick_ms
            
        for name, tinfo in tasks.items():
            if current_task == name:
                st = "RUNNING"
            elif tinfo["rem"] > 0:
                st = "READY"
            else:
                st = "BLOCKED"
            tinfo["state_history"].append(st)

    return {
        "time_axis": time_axis,
        "cpu_running_history": cpu_running_history,
        "tasks": tasks
    }

missile_sim = simulate_missile_flight_computer()

print("=" * 68)
print("ROKETSAN FÜZE GÜDÜM BİLGİSAYARI ÇOKLU GÖREV ÇALIŞMA RAPORU (100 ms)")
print("=" * 68)
cpu_counts = {}
for t_name in missile_sim["cpu_running_history"]:
    cpu_counts[t_name] = cpu_counts.get(t_name, 0) + 1

for t_name, count in sorted(cpu_counts.items(), key=lambda x: -x[1]):
    print(f"  - {t_name:<15}: %{count/100*100:5.1f} CPU Zamanı ({count} ms)")

# Doğrulama: Tüm görevler başarıyla çalışmış olmalı
assert cpu_counts["INS_EKF"] == 20, "INS_EKF 10 periyot x 2 ms = 20 ms koşmalı!"
assert cpu_counts["Fin_Actuator"] == 20, "Fin_Actuator 10 periyot x 2 ms = 20 ms koşmalı!"
assert cpu_counts["Mission_FSM"] == 15, "Mission_FSM 5 periyot x 3 ms = 15 ms koşmalı!"
assert cpu_counts["Telemetry"] == 10, "Telemetry 2 periyot x 5 ms = 10 ms koşmalı!"
assert cpu_counts["Idle_Task"] == 35, "Idle Task kalan 35 ms'yi doldurmalı!"
print("\n[BAŞARILI]: Füze uçuş bilgisayarı görev seti %100 deterministik zamanlamayla tamamlandı.")

# ==============================================================================
# KOD BLOĞU: 14
# ==============================================================================
# KOD HÜCRESİ 6: Endüstriyel Dashboard Görselleştirme ve Kapsamlı Assertions
# ------------------------------------------------------------------------------
# 300 DPI, Dark Theme (#0F172A), 4 Panelli Endüstriyel Aviyonik Dashboard:
# Panel 1: Görev Durum Makinesi Yaşam Döngüsü (Running, Ready, Blocked)
# Panel 2: Eşit Öncelikli Görevlerde Round-Robin Time-Slicing Dağılımı
# Panel 3: TCB Bellek Haritası ve Stack High Water Mark (0xA5 Deseni)
# Panel 4: Klasik Tick vs Tickless Idle Güç Tüketimi Karşılaştırması

import os
import matplotlib.pyplot as plt
import numpy as np

# PNG Dosya Yolu
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_180_task_thread_ve_scheduler.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_180\gun_180_task_thread_ve_scheduler.png"

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
# PANEL 1: Görev Durum Makinesi Yaşam Döngüsü (Gantt Chart)
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. Görev Durum Makinesi Yaşam Döngüsü (İlk 30 ms)", fontsize=11, fontweight='bold', pad=10)

t_limit = 30
task_colors = {"INS_EKF": "#38BDF8", "Fin_Actuator": "#10B981", "Mission_FSM": "#F59E0B", "Telemetry": "#EC4899", "Idle_Task": "#64748B"}
y_levels = {"INS_EKF": 4, "Fin_Actuator": 3, "Mission_FSM": 2, "Telemetry": 1, "Idle_Task": 0}

for idx, t_name in enumerate(missile_sim["cpu_running_history"][:t_limit]):
    ax1.barh(y_levels[t_name], 1, left=idx, color=task_colors[t_name], height=0.7, edgecolor='none')

ax1.set_yticks(list(y_levels.values()))
ax1.set_yticklabels(list(y_levels.keys()), fontweight='bold')
ax1.set_xlabel("Zaman (ms)", fontsize=10)
ax1.set_xlim(0, t_limit)

# ------------------------------------------------------------------------------
# PANEL 2: Round-Robin Time-Slicing Karşılaştırması
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. Eşit Öncelikli Görevlerde Round-Robin Time-Slicing (1 ms Dilimler)", fontsize=11, fontweight='bold', pad=10)

ts_tasks = ["Fin_Left", "Fin_Right", "Fin_Rudder"]
c_map = {"Fin_Actuator_Left": "#38BDF8", "Fin_Actuator_Right": "#10B981", "Fin_Actuator_Rudder": "#F59E0B"}

# Time Slicing AÇIK (Üst)
for i, t_act in enumerate(res_ts_on["timeline"][:18]):
    ax2.barh(1.8, 1, left=i, color=c_map[t_act], height=0.5, edgecolor='#0F172A')

# Time Slicing KAPALI (Alt)
for i, t_act in enumerate(res_ts_off["timeline"][:18]):
    ax2.barh(0.8, 1, left=i, color=c_map[t_act], height=0.5, edgecolor='#0F172A')

ax2.set_yticks([0.8, 1.8])
ax2.set_yticklabels(["Time-Slicing KAPALI", "Time-Slicing AÇIK"], fontweight='bold')
ax2.set_xlabel("Zaman Dilimi (Ticks)", fontsize=10)
ax2.set_xlim(0, 18)
ax2.text(2, 2.15, "Adil Dağılım: Sırayla 1'er Tick", color='#38BDF8', fontsize=9, fontweight='bold')
ax2.text(2, 1.15, "Bloklayıcı Dağılım: Biri Bitmeden Diğeri Başlamaz", color='#EF4444', fontsize=9, fontweight='bold')

# ------------------------------------------------------------------------------
# PANEL 3: TCB Bellek Haritası ve Stack High Water Mark
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. TCB Yığın Bellek Haritası ve High Water Mark (0xA5 Deseni)", fontsize=11, fontweight='bold', pad=10)

stack_depth = np.arange(0, 256) # 256 kelime
# 0..74 kelime: Kullanılmamış 0xA5 deseni
# 75..255 kelime: Kullanılmış çalışma alanı
memory_profile = np.array([1 if i < hwm_step2 else 2 for i in stack_depth])

ax3.bar(stack_depth[:hwm_step2], np.ones(hwm_step2), color='#10B981', width=1.0, label=f'Dokunulmamış Alan (0xA5): {hwm_step2} Kelime')
ax3.bar(stack_depth[hwm_step2:], np.ones(256 - hwm_step2), color='#EF4444', width=1.0, label=f'Tepe Yığın Tüketimi: {256-hwm_step2} Kelime')

ax3.axvline(hwm_step2, color='#F59E0B', linestyle='--', linewidth=2, label=f'High Water Mark Sınırı ({hwm_step2*4} Bayt)')
ax3.set_xlabel("Yığın Ofseti (Kelimeler - 4 Bayt)", fontsize=10)
ax3.set_ylabel("Doluluk Durumu", fontsize=10)
ax3.set_xlim(0, 256)
ax3.set_ylim(0, 1.5)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 4: Klasik Tick vs Tickless Idle Güç Tüketimi
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. Düşük Güç Analizi: Klasik SysTick vs Tickless Idle", fontsize=11, fontweight='bold', pad=10)

modes = ["Klasik SysTick (1000 Hz)", "Tickless Idle (LPTIM)"]
currents = [res_standard["avg_current_ma"], res_tickless["avg_current_ma"]]
battery_days = [res_standard["battery_days"], res_tickless["battery_days"]]

x_pos = np.arange(len(modes))
ax4_bar = ax4.bar(x_pos, currents, width=0.45, color=['#EF4444', '#10B981'], edgecolor='#475569')

ax4.set_xticks(x_pos)
ax4.set_xticklabels(modes, fontweight='bold')
ax4.set_ylabel("Ortalama Akım Tüketimi (mA)", fontsize=10)
ax4.set_ylim(0, 15)

for i, bar in enumerate(ax4_bar):
    h = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2, h + 0.4, f"{h:.2f} mA\n({battery_days[i]:.1f} Gün Pil)", 
             ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=9)

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
assert cpu_counts["INS_EKF"] == 20, "HATA: INS_EKF çalışma süresi tutarsız!"
assert cpu_counts["Idle_Task"] == 35, "HATA: Idle task çalışma süresi tutarsız!"
assert res_ts_on["context_switch_count"] > res_ts_off["context_switch_count"], "HATA: Time-slicing daha çok context switch üretmeli!"
assert energy_saving_percent > 70.0, "HATA: Tickless tasarrufu hesaplama hatası!"

print("[PASS] GÜN 180: TÜM MATEMATİKSEL VE GÖRSEL DOĞRULAMALAR BAŞARIYLA TAMAMLANDI!")

