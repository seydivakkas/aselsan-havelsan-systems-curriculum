# GÜN 166: STM32 Kesmeler (Interrupts), NVIC Mimarisi, Preemption, EXTI ve ISR Tasarım İlkeleri

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz.
```

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
![C++20](https://img.shields.io/badge/Standard-C%2B%2B20-blue.svg?style=flat-square)
![ARM Cortex-M](https://img.shields.io/badge/Architecture-ARM%20Cortex--M4%2FM7-orange.svg?style=flat-square)
![STM32 NVIC](https://img.shields.io/badge/Hardware-NVIC%20%2F%20EXTI-red.svg?style=flat-square)
![Defense Grade](https://img.shields.io/badge/Domain-Avionics%20%2F%20Hard%20Real--Time-red.svg?style=flat-square)

---

## 1. Zihinsel Model ve Mimari Büyük Resim (NVIC ve Donanımsal Kesme Otoyolu)

Gömülü sistem mühendisliğinde iki temel çalışma felsefesi vardır:
1. **Yoklama (Polling):** İşlemci sürekli bir döngüde `while(button == 0)` veya `while(uart_ready == 0)` diyerek dış dünyayı kontrol eder. Bu yöntem CPU zamanını tamamen israf eder, reaksiyon gecikmesini (Latency) ve güç tüketimini tavan yaptırır.
2. **Kesme Tabanlı (Interrupt-Driven):** İşlemci kendi işini (veya uykusunu) sürdürür. Dış dünyada bir olay olduğunda (radar yankısı geldi, UART baytı indi, füze açısı sınır değerini aştı), donanım doğrudan CPU çekirdeğinin omzuna dokunur: *"Dur, şu anki işini askıya al ve benim bu acil fonksiyonumu koştur!"*

ARM Cortex-M mimarisinin kalbinde yer alan **NVIC (Nested Vectored Interrupt Controller - Yuvalanmış Vektörlü Kesme Denetleyicisi)**, dünyadaki en gelişmiş deterministik kesme motorlarından biridir:
- **Nested (Yuvalanmış):** Yüksek öncelikli bir kesme, o an çalışmakta olan düşük öncelikli bir kesmeyi **BÖLEBİLİR (Preemption)**.
- **Vectored (Vektörlü):** Kesme geldiğinde yazılımsal bir sorgulama döngüsüne gerek kalmaz. Donanım, Flash bellekteki **Vektör Tablosu (Vector Table)** üzerinden doğrudan ilgili fonksiyonun (ISR - Interrupt Service Routine) adresine atlar.
- **Sıfır Yazılım Overhead'i:** Klasik mikrodenetleyicilerde yazılımla yapılan yazmaç saklama (Stacking) işlemi, Cortex-M'de tam $12$ saat çevriminde doğrudan silikon donanım tarafından yürütülür.

```
    +-------------------------------------------------------------------------+
    |           ARM CORTEX-M NVIC DONANSIMSAL KESME VE ÖNCELİK MİMARİSİ       |
    +-------------------------------------------------------------------------+
    
    [ ÇEVRESEL BİRİMLER ]              [ NVIC DONANIMI ]                  [ CORTEX-M ÇEKİRDEK ]
    
    EXTI0 (Lazer Dedektör) ----> [ Öncelik Karşılaştırıcı ]            +-------------------+
    TIM1 (Motor PWM)        ----> |   (Priority Engine)    |            |   THREAD MODE     |
    USART1 (Telemetri RX)   ----> |                        | ---------> | (Normal Görevler) |
    SysTick (RTOS Zamanı)   ----> [ En Yüksek Önceliği Seç ]            +-------------------+
                                                                                  |
                                                                        [ 12-Cycle HW Stacking ]
                                                                                  v
                                                                        +-------------------+
                                                                        |   HANDLER MODE    |
                                                                        | (Acil Kesme - ISR)|
                                                                        +-------------------+
                                                                                  |
                                                                        [ EXC_RETURN / Unstack ]
                                                                                  v
                                                                        [ Göreve Geri Dönüş ]
```

## 2. NVIC Öncelik Mimarisi: Preemption vs Sub-Priority ve PRIGROUP

ARM Cortex-M NVIC mimarisinde her kesme için bir öncelik değeri tanımlanır. Ancak STM32 çiplerinde bu öncelik alanı $4\ \text{bit}$ ($0 - 15$) genişliğindedir. Bu $4\ \text{bit}$, `SCB->AIRCR` yazmacındaki `PRIGROUP` konfigürasyonu ile ikiye bölünür:

1. **Preemption Priority (Araya Girme Önceliği):**
   - Çalışmakta olan bir kesmeyi **bölebilme** yeteneğidir.
   - Sayısal olarak daha küçük değere sahip olan kesme (örneğin Öncelik 0), daha büyük değere sahip olan kesmeyi (örneğin Öncelik 2) ortasından böler.
2. **Sub-Priority (Alt Öncelik / Sıralama Önceliği):**
   - Eğer iki kesme **AYNI ANDA** beklemeye (Pending) düşerse, hangisinin önce çalıştırılacağını belirler.
   - Alt öncelik **ASLA ÇALIŞMAKTA OLAN BİR KESMEYİ BÖLEMEZ**! Sadece kuyrukta kimin öne geçeceğine karar verir.

### PRIGROUP Ayarları Tablosu (STM32 4-Bit Uygulaması):

| PRIGROUP Seviyesi | Preemption Bitleri | Sub-Priority Bitleri | Preemption Seviyeleri | Sub-Priority Seviyeleri | Savunma / RTOS Tercihi |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `NVIC_PRIORITYGROUP_4` | **4 Bit [3:0]** | 0 Bit | **16 Seviye (0..15)** | Yok | **En Çok Tercih Edilen (Tam Hiyerarşi)** |
| `NVIC_PRIORITYGROUP_3` | 3 Bit [3:1] | 1 Bit [0] | 8 Seviye (0..7) | 2 Seviye (0..1) | Karma Sistemler |
| `NVIC_PRIORITYGROUP_2` | 2 Bit [3:2] | 2 Bit [1:0] | 4 Seviye (0..3) | 4 Seviye (0..3) | **FreeRTOS Varsayılanı** |
| `NVIC_PRIORITYGROUP_0` | 0 Bit | 4 Bit [3:0] | Yok (Yuvalanma Yok) | 16 Seviye | Deterministik FIFO Kuyruğu |

> [!IMPORTANT]
> **Altın Kural:** Cortex-M NVIC'de sayı küçüldükçe öncelik **ARTAR**! Öncelik `0` en yüksek ve en acil kesmedir; Öncelik `15` en düşük önceliktir.

## 3. Donanım Optimizasyonları: Tail-Chaining, Late-Arrival ve Pop-Preemption

Geleneksel mikrodenetleyicilerde kesme giriş ve çıkışları yazılımsal stack işlemleri nedeniyle çok yavaştır. ARM Cortex-M silikonu bu sorunu 3 patentli donanım mekanizmasıyla çözer:

### 1. Tail-Chaining (Kuyruk Bağlama):
Bir kesme servisi (ISR 1) bittiğinde sırada bekleyen başka bir kesme (ISR 2) varsa:
- Klasik işlemci 12 çevrimde stack'i boşaltır (unstacking), hemen ardından ikinci kesme için aynı yazmaçları tekrar stack'e basar (stacking) $\implies 24 - 32\ \text{çevrim}$ israf!
- Cortex-M NVIC ise yazmaçları stack'te hiç ellemeden bırakır; sadece **$6$ saat çevrimi** içinde doğrudan ISR 2 vektörüne dalar. Bellek veri yolu trafiği \%80 azalır!

### 2. Late-Arrival (Geç Varış Optimizasyonu):
İşlemci düşük öncelikli bir kesme (ISR 2) için donanımsal stacking yaparken (12 çevrimlik süreçte), aniden çok yüksek öncelikli bir acil durum kesmesi (ISR 1) gelirse:
- Donanım devam eden stacking işlemini iptal etmez; stacking tamamlandığı anda düşük öncelikli kesmeyi değil, doğrudan yüksek öncelikli ISR 1'i çalıştırır!

### 3. Pop-Preemption:
Bir ISR tamamlanıp işlemci stack'ten yazmaçları geri yüklerken (Unstacking) yeni bir yüksek öncelikli kesme gelirse, unstacking derhal durdurulur ve yeni ISR'a geçilir.

## 4. Altın Kural: Top-Half vs Bottom-Half (Deferred Interrupt Processing)

Gömülü yazılım geliştirmede karşılaşılan en büyük mimari hata, kesme fonksiyonunun (ISR) içine uzun kodlar yazmaktır. Bir ISR içinde kesinlikle **YAPILMAMASI GEREKENLER**:
1. `printf()`, `std::cout`, UART üzerinden uzun metin basma (Bloklayıcı I/O),
2. `HAL_Delay()` veya `sleep()` döngüleri (SysTick engellendiği için sistem kilitlenir),
3. `malloc()`, `free()`, C++ `new` (Reentrant değildir, heap bozulur),
4. Ağır matematiksel filtreler (FFT, matris tersi, karmaşık algoritmalar).

### Doğru Mimari: İki Aşamalı Kesme Yönetimi (Top-Half & Bottom-Half):
- **Top-Half (Birincil Kesme - ISR):**
  - Süre: $< 1 - 5\ \mu\text{s}$.
  - Görev: Donanımsal bayrağı temizle, veriyi donanım yazmacından (`DR` veya FIFO) oku, kesme-güvenli dairesel arabelleğe (`Ring Buffer`) at, bir bayrak veya RTOS semaforunu (`xSemaphoreGiveFromISR`) tetikle ve derhal çık!
- **Bottom-Half (Ertelenmiş İşlem - Task / Main Loop):**
  - Süre: Gerektiği kadar (milisaniyeler).
  - Görev: Thread modunda veya bir RTOS görevi içinde çalışır. Ring Buffer'daki veriyi alır, CRC kontrolünü yapar, şifresini çözer, Kalman filtresini koşturur. Sistemdeki diğer acil kesmeler hiçbir zaman engellenmez!

```python
# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 1 — STM32 NVIC Çok Seviyeli Kesme ve Vektör Tablosu Simülatörü
(Preemption, Sub-Priority, Vektör Tablosu ve Donanımsal Yuvalanma)
"""

from typing import Dict, List, Any, Optional
import time

class NvicInterruptEngine:
    """
    ARM Cortex-M NVIC Donanım Motoru Modeli:
    - Preemption Priority (Öncelik: 0 en yüksek, 15 en düşük)
    - Sub-Priority (Aynı anda tetiklenenlerde sıra belirleme)
    - ISER / ICER (Etkinleştirme / Devre Dışı Bırakma)
    - ISPR / ICPR (Bekleme / Pending Yönetimi)
    - IABR (O anda aktif çalışan kesmeler)
    """
    def __init__(self, prigroup: int = 4):
        self.prigroup = prigroup # 4: 4-bit Preemption (0..15 seviye)
        self.vector_table: Dict[int, str] = {
            0: "RESET_HANDLER",
            1: "NMI_HANDLER",
            2: "HARDFAULT_HANDLER",
            16: "EXTI0_LASER_DETECT", # Harici Kesme 0
            17: "TIM1_UP_MOTOR_PID",  # Motor PID
            18: "USART1_TELEMETRY",   # Seri Telemetri
            19: "EXTI15_10_SAFETY"    # Emniyet Kilidi
        }
        
        # Kesme Nitelikleri: irq_num -> (Preemption, SubPriority, Enabled, Pending)
        self.irq_config: Dict[int, Dict[str, Any]] = {}
        self.active_stack: List[int] = [] # Çalışan kesmeler yığını (Nesting)
        self.execution_trace: List[str] = []

    def register_irq(self, irq_num: int, preemption: int, sub_prio: int = 0):
        self.irq_config[irq_num] = {
            "preemption": preemption,
            "sub_prio": sub_prio,
            "enabled": True,
            "pending": False
        }

    def trigger_interrupt(self, irq_num: int) -> bool:
        """Donanımsal veya Yazılımsal Kesme Tetikleme"""
        if irq_num not in self.irq_config or not self.irq_config[irq_num]["enabled"]:
            return False

        name = self.vector_table.get(irq_num, f"IRQ_{irq_num}")
        incoming_prio = self.irq_config[irq_num]["preemption"]

        # Eğer şu anda çalışan bir kesme varsa
        if self.active_stack:
            current_active = self.active_stack[-1]
            current_prio = self.irq_config[current_active]["preemption"]

            # PREEMPTION KONTROLÜ: Gelen kesmenin önceliği daha mı yüksek? (Daha küçük sayı)
            if incoming_prio < current_prio:
                self.execution_trace.append(f"[PREEMPTION] {name} (Prio {incoming_prio}) -> {self.vector_table[current_active]} (Prio {current_prio}) kesmesini BÖLDÜ!")
                self.active_stack.append(irq_num)
                return True
            else:
                # Kesme beklemeye alınıyor (Pending)
                self.irq_config[irq_num]["pending"] = True
                self.execution_trace.append(f"[PENDING] {name} (Prio {incoming_prio}) beklemeye alındı (Çalışan Prio {current_prio})")
                return False
        else:
            # İşlemci Thread modundaydı, doğrudan kesmeye girilir
            self.execution_trace.append(f"[ENTER] {name} (Prio {incoming_prio}) kesmesine girildi.")
            self.active_stack.append(irq_num)
            return True

    def finish_current_isr(self):
        """BX LR (EXC_RETURN) ile Kesmeden Çıkış"""
        if self.active_stack:
            finished = self.active_stack.pop()
            finished_name = self.vector_table.get(finished, f"IRQ_{finished}")
            self.execution_trace.append(f"[EXIT] {finished_name} tamamlandı.")

            # Sırada bekleyen (Pending) kesme var mı? (Tail-Chaining)
            pending_irqs = [irq for irq, cfg in self.irq_config.items() if cfg["pending"]]
            if pending_irqs:
                # En yüksek öncelikli olanı seç (En küçük preemption)
                pending_irqs.sort(key=lambda x: (self.irq_config[x]["preemption"], self.irq_config[x]["sub_prio"]))
                next_irq = pending_irqs[0]
                self.irq_config[next_irq]["pending"] = False
                next_name = self.vector_table[next_irq]
                self.execution_trace.append(f"[TAIL-CHAINING] 6 Çevrimde doğrudan {next_name} kesmesine geçildi (Sıfır Stack Masrafı).")
                self.active_stack.append(next_irq)

# Doğrulama Testi
nvic = NvicInterruptEngine()
# Kesme Öncelikleri: EXTI0 (0 - En yüksek), TIM1 (1 - Orta), USART1 (2 - Düşük)
nvic.register_irq(18, preemption=2) # USART1
nvic.register_irq(17, preemption=1) # TIM1
nvic.register_irq(16, preemption=0) # EXTI0

# Senaryo 1: USART telemetri paketi alınıyor (Prio 2)
nvic.trigger_interrupt(18)

# Senaryo 2: USART çalışırken 2000 Hz TIM1 Motor PID kesmesi geliyor (Prio 1 < 2 -> BÖLER!)
nvic.trigger_interrupt(17)

# Senaryo 3: Motor PID çalışırken ACİL LAZER DARBESİ EXTI0 Geliyor! (Prio 0 < 1 -> BÖLER!)
nvic.trigger_interrupt(16)

# Kesmeler sırayla biter
nvic.finish_current_isr() # EXTI0 biter, TIM1'e döner
nvic.finish_current_isr() # TIM1 biter, USART'a döner
nvic.finish_current_isr() # USART biter, ana göreve döner

print("[*] NVIC Çok Seviyeli Yuvalanmış Kesme Yürütme İzi:")
for trace in nvic.execution_trace:
    print(f"  {trace}")

assert "[PREEMPTION]" in nvic.execution_trace[1]
assert "[PREEMPTION]" in nvic.execution_trace[2]
assert len(nvic.active_stack) == 0, "Tüm kesmeler başarıyla tamamlanmış olmalıdır!"
print("[HÜCRE 6] NVIC çok seviyeli kesme ve preemption motoru başarıyla doğrulandı.")
```

## 5. Kod Açıklaması: NVIC Öncelik Sıralaması ve Preemption Yürütmesi

Yukarıdaki simülatör, ARM Cortex-M donanımının en kritik yeteneğini doğrulamıştır:
1. `USART1` (`Prio 2`) çalışırken daha yüksek öncelikli `TIM1` (`Prio 1`) geldiğinde işlemci hiç duraksamadan USART kodunu askıya almış ve motor PID döngüsüne geçmiştir.
2. Motor PID döngüsü çalışırken acil hedef lazer darbesi `EXTI0` (`Prio 0`) geldiğinde, donanım motor kodunu da askıya almış ve $12$ çevrimlik stacking ile lazer kesmesini çalıştırmıştır.
3. Kesmeler $0 \to 1 \to 2$ hiyerarşik sırasında tamamlanarak hiçbir veri kaybı yaşanmadan ana göreve güvenle dönülmüştür.

```python
# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 2 — EXTI (External Interrupt) Hat Eşlemesi ve Write-1-to-Clear Mekanizması
"""

class ExtiHardwareController:
    """
    STM32 EXTI Donanım Kontrolcüsü:
    - IMR  (Interrupt Mask Register): Kesme maskesi (1: Açık, 0: Kapalı)
    - RTSR (Rising Trigger Selection Register): Yükselen kenar tetikleme
    - FTSR (Falling Trigger Selection Register): Düşen kenar tetikleme
    - PR   (Pending Register): Bayrak yazmacı (WRITE-1-TO-CLEAR!)
    - SYSCFG EXTI Multiplexer: Pin 0 sadece PA0, PB0 veya PC0'dan birine bağlanabilir!
    """
    def __init__(self):
        self.imr = 0x0000
        self.rtsr = 0x0000
        self.ftsr = 0x0000
        self.pr = 0x0000
        self.syscfg_exti0_port = "PA" # PA0 seçili

    def configure_exti_line(self, line: int, port: str, rising: bool = True, falling: bool = False):
        if line == 0:
            self.syscfg_exti0_port = port

        # Maskeyi aç
        self.imr |= (1 << line)
        if rising:
            self.rtsr |= (1 << line)
        if falling:
            self.ftsr |= (1 << line)

    def trigger_pin_event(self, line: int, port: str, edge: str) -> bool:
        """Dış Fiziksel Pinden Kenar Gelmesi"""
        # 1. SYSCFG port doğrulaması: Doğru port mu bağlı?
        if line == 0 and port != self.syscfg_exti0_port:
            return False # Yanlış port, multiplexer sinyali geçirmez!

        # 2. Kenar kontrolü
        is_valid_edge = False
        if edge == "RISING" and (self.rtsr & (1 << line)):
            is_valid_edge = True
        elif edge == "FALLING" and (self.ftsr & (1 << line)):
            is_valid_edge = True

        # 3. Maske kontrolü
        if is_valid_edge and (self.imr & (1 << line)):
            # Donanım PR bayrağını Lojik-1 yapar!
            self.pr |= (1 << line)
            return True
        return False

    def clear_pending_flag(self, line: int, write_value: int):
        """WRITE-1-TO-CLEAR Mekanizması: Sadece 1 yazıldığında temizlenir!"""
        if write_value & (1 << line):
            self.pr &= ~(1 << line) # Bayrak sıfırlanır

# EXTI Yapılandırma ve Test
exti = ExtiHardwareController()
# EXTI Hat 0 PA0 pinine bağlanıyor, Yükselen Kenar aktif
exti.configure_exti_line(line=0, port="PA", rising=True, falling=False)

# PA0 pini Lojik 0 -> 1 geçişi yapıyor (Lazer darbesi!)
event_generated = exti.trigger_pin_event(line=0, port="PA", edge="RISING")

print()
print("[*] EXTI Donanımsal Hat Eşleme ve Tetikleme Testi:")
print(f"  [+] EXTI0 PA0 Tetiklendi mi? : {event_generated}")
print(f"  [+] Pending Register (PR)   : 0x{exti.pr:04X} (Hat 0 Bayrağı Set)")

assert event_generated == True
assert (exti.pr & (1 << 0)) != 0

# WRITE-1-TO-CLEAR TESTİ:
# Eğer yazılımcı sıfır yazarsa bayrak TEMİZLENMEZ!
exti.clear_pending_flag(line=0, write_value=0x0000)
assert (exti.pr & (1 << 0)) != 0, "Sıfır yazmak bayrağı temizleyemez!"

# Doğru temizleme: İlgili bite 1 yazılır!
exti.clear_pending_flag(line=0, write_value=(1 << 0))
assert exti.pr == 0x0000, "1 yazıldığında PR bayrağı sıfırlanmalıdır!"
print("  [+] Write-1-to-Clear kuralı başarıyla doğrulandı: Bayrak temizlendi.")
print("[HÜCRE 8] EXTI donanım kontrolcüsü ve bayrak mekanizması başarıyla doğrulandı.")
```

## 6. Kod Açıklaması: SYSCFG Pin Eşlemesi ve Write-1-to-Clear Kuralı

Yukarıdaki kod bloğu sahada en çok kafa karıştıran iki donanım kuralını ispatlamıştır:
1. **SYSCFG Multiplexer Kısıtı:** Bir mikrokontrolcüde $16$ adet harici kesme hattı (`EXTI0`..`EXTI15`) vardır. Hat 0'a ya `PA0`, ya `PB0`, ya da `PC0` bağlanabilir. İki farklı portun 0 numaralı pini aynı anda bağımsız kesme üretemez!
2. **Write-1-to-Clear Mantığı:** Donanım seviyesinde `EXTI->PR` yazmacı bayrağı set ettiğinde, yazılımcı `EXTI->PR = 0;` yazarsa bayrak **TEMİZLENMEZ**. Bayrağı temizlemek için o bit pozisyonuna Lojik-1 (`EXTI->PR = (1 << pin)`) yazılması zorunludur.

```python
# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 3 — Sabotaj ve Hata Enjeksiyonu: Bayrak Temizleme İhmali ve Sonsuz Döngü
"""

class FaultyInterruptSimulator:
    def __init__(self, exti_ctrl: ExtiHardwareController):
        self.exti = exti_ctrl
        self.isr_invocation_counter = 0

    def run_faulty_isr(self, clear_flag: bool):
        """
        Eğer ISR bayrağı temizlemeden çıkarsa, donanım kesme koşulunun
        hala aktif olduğunu düşünerek kesmeden çıktığı nanosaniyede tekrar ISR çağırır!
        """
        self.isr_invocation_counter += 1
        # Hatalı geliştirici bayrağı temizlemeyi unuttu!
        if clear_flag:
            self.exti.clear_pending_flag(line=0, write_value=(1 << 0))

print()
print("[*] SABOTAJ SENARYOSU 1: ISR İçinde PR Bayrağını Temizlemeyi Unutmak")
exti_test = ExtiHardwareController()
exti_test.configure_exti_line(line=0, port="PA", rising=True)
exti_test.trigger_pin_event(line=0, port="PA", edge="RISING")

simulator = FaultyInterruptSimulator(exti_test)

# Bayrak temizlenmediğinde döngü simülasyonu
lockup_detected = False
for step in range(100):
    if exti_test.pr & (1 << 0):
        simulator.run_faulty_isr(clear_flag=False)
        if simulator.isr_invocation_counter >= 50:
            lockup_detected = True
            break

print(f"  [!] Sonsuz Döngü / Lockup Algılandı: ISR tam {simulator.isr_invocation_counter} kez peş peşe çağrıldı!")
print(f"  [!] CPU Ana Göreve Dönemiyor (Thread Starvation)!")
assert lockup_detected == True

print()
print("[*] DÜZELTME: ISR İçinde Bayrak Usulüne Uygun Temizleniyor")
simulator.isr_invocation_counter = 0
simulator.run_faulty_isr(clear_flag=True)
print(f"  [+] Bayrak Temizlendi: PR = 0x{exti_test.pr:04X}, Toplam Çağrı = {simulator.isr_invocation_counter}")
assert exti_test.pr == 0x0000
assert simulator.isr_invocation_counter == 1

print()
print("[*] SABOTAJ SENARYOSU 2: ISR İçinde Bloklayıcı Gecikme (HAL_Delay) Felaketi")
def check_isr_timing_safety(delay_requested_ms: float, max_allowed_budget_us: float) -> bool:
    if (delay_requested_ms * 1000.0) > max_allowed_budget_us:
        raise TimeoutError(f"CRITICAL TIMING FAULT: ISR içinde {delay_requested_ms} ms gecikme kullanılamaz! Bütçe: {max_allowed_budget_us} us")
    return True

delay_fault_caught = False
try:
    # ISR içinde 10 ms bekleme yapılmaya çalışılıyor (Savunma standardı bütçesi: 10 us!)
    check_isr_timing_safety(delay_requested_ms=10.0, max_allowed_budget_us=10.0)
except TimeoutError as e:
    delay_fault_caught = True
    print(f"  [+] Savunma Başarılı: ISR Zamanlama İhlali Yakalandı! ({e})")

assert delay_fault_caught == True
print("[HÜCRE 10] Sabotaj ve kilitlenme analizleri başarıyla doğrulandı.")
```

## 7. Kod Açıklaması: Sabotaj Analizi ve Sonsuz Kesme Döngüsü Kök Nedenleri

Yukarıdaki sabotaj deneylerinde sahada sistemlerin çökmesine neden olan iki ana hata canlandırılmıştır:
1. **ISR Starvation Lockup (Sonsuz Kesme Kilitlenmesi):** Geliştirici `EXTI0_IRQHandler` içine bayrak temizleme komutu (`EXTI->PR = 1`) koymadığında, işlemci `BX LR` ile ana göreve döner dönmez donanım bayrağın hala $1$ olduğunu görür ve tek bir satır kullanıcı kodu dahi çalıştırmadan anında tekrar ISR'a dalar. Sistem tamamen donar.
2. **ISR Blocking Delay (Gecikme Felaketi):** Kesme içinde beklemek sistemin tüm zamanlama determinizmini yok eder; diğer tüm alt sistemler açlıktan ölür (**Starvation**).

```python
# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 4 — Top-Half / Bottom-Half Ayrımı ve Kesme-Güvenli Lock-Free Dairesel Bellek
"""

class LockFreeIsrRingBuffer:
    """
    Tek Üretici (ISR - Top-Half) / Tek Tüketici (Main Task - Bottom-Half) Dairesel Bellek:
    - Kesme içinde kilit (mutex/lock) kullanılmaz!
    - Head sadece ISR tarafından yazılır.
    - Tail sadece Ana Görev tarafından yazılır.
    - Sıfır yarış durumu (Race Condition), atomik operasyon.
    """
    def __init__(self, capacity: int = 16):
        self.capacity = capacity
        self.buffer = [0] * capacity
        self.head = 0
        self.tail = 0
        self.dropped_events = 0

    def isr_push_top_half(self, data: int) -> bool:
        """Top-Half: 5 saat çevriminde veriyi kaydet ve çık!"""
        next_head = (self.head + 1) % self.capacity
        if next_head == self.tail:
            # Arabellek dolu! Veri düştü (Buffer Overflow)
            self.dropped_events += 1
            return False
        self.buffer[self.head] = data
        self.head = next_head
        return True

    def task_pop_bottom_half(self) -> Optional[int]:
        """Bottom-Half: Ana görev arka planda rahatça işler"""
        if self.head == self.tail:
            return None # Boş
        data = self.buffer[self.tail]
        self.tail = (self.tail + 1) % self.capacity
        return data

# Deney: Yüksek Hızlı Radar Sinyalleri Alınıyor
ring_buf = LockFreeIsrRingBuffer(capacity=8)

# Top-Half (ISR): 5 ardışık darbe telemetrisi geliyor
telemetry_data = [0xA1, 0xA2, 0xA3, 0xA4, 0xA5]
for d in telemetry_data:
    success = ring_buf.isr_push_top_half(d)
    assert success == True

print()
print("[*] Top-Half / Bottom-Half Ring Buffer Testi:")
print(f"  [+] ISR Top-Half Yazılan Bayt Sayısı: {len(telemetry_data)}")
print(f"  [+] Arabellek Durumu: Head={ring_buf.head}, Tail={ring_buf.tail}")

# Bottom-Half (Ana Döngü): Veriler sırayla okunuyor ve işleniyor
processed_data = []
while True:
    val = ring_buf.task_pop_bottom_half()
    if val is None:
        break
    processed_data.append(val)

print(f"  [+] Bottom-Half İşlenen Veriler     : {[hex(x) for x in processed_data]}")
assert processed_data == telemetry_data
assert ring_buf.dropped_events == 0
print("[HÜCRE 12] Lock-free ring buffer ve iki aşamalı kesme mimarisi başarıyla doğrulandı.")
```

## 8. Kod Açıklaması: Minimum ISR Süresi ve Jitter Eliminasyonu

Yukarıdaki `LockFreeIsrRingBuffer` uygulaması aviyonik ve gerçek zamanlı sistemlerin temel veri otoyoludur:
1. **Kilit-Siz (Lock-Free) Güvenlik:** `head` işaretçisini sadece ISR artırır, `tail` işaretçisini sadece ana görev artırır. Mutex veya kritik bölge kilitlerine (`disable_irq`) ihtiyaç duyulmaz.
2. **Determinizm:** ISR sadece $3$ makine komutu koşturup çıkar ($t_{ISR} < 50\ \text{ns}$); böylece diğer yüksek öncelikli kesmelerin gecikme oynaması (**Jitter**) sıfıra indirilir.

```python
# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 5 — ROKETSAN Taktik Füze Lazer Arayıcı Başlık (Seeker) Kesme Mimarisi
"""

class MissileSeekerInterruptSystem:
    """
    ROKETSAN Lazer Arayıcı Başlık Aviyonik Modeli:
    - EXTI0 (Prio 0): Lazer Kod Tespiti (Hedef Vuruş Doğrulaması - En Yüksek Acil)
    - TIM1  (Prio 1): 2000 Hz Gimbal Açı Kontrolü (Kalman Filtresi)
    - UART1 (Prio 2): Yer İstasyonu Telemetri Akışı
    """
    def __init__(self):
        self.nvic = NvicInterruptEngine(prigroup=4)
        self.ring_buf = LockFreeIsrRingBuffer(capacity=16)
        
        # Kesmeler Kaydediliyor
        self.nvic.register_irq(16, preemption=0) # EXTI0 Lazer
        self.nvic.register_irq(17, preemption=1) # TIM1 Gimbal
        self.nvic.register_irq(18, preemption=2) # UART1 Telemetri

        self.laser_target_locked = False
        self.gimbal_cycles = 0

    def simulate_combat_scenario(self):
        # 1. Telemetri gönderimi başlar (Prio 2)
        self.nvic.trigger_interrupt(18)

        # 2. Gimbal açı kontrolü tetiklenir (Prio 1 -> Telemetriyi böler!)
        self.nvic.trigger_interrupt(17)
        self.gimbal_cycles += 1

        # 3. TAM O ANDA HEDEF LAZER DARBESİ YAKALANDI! (Prio 0 -> Gimbal'ı da böler!)
        self.nvic.trigger_interrupt(16)
        
        # Lazer ISR (Top-Half): Hızlıca darbe zaman damgasını kaydeder
        self.ring_buf.isr_push_top_half(0xDEAD)
        self.laser_target_locked = True

        # Kesmeler Hiyerarşik Olarak Kapanır
        self.nvic.finish_current_isr() # Lazer biter
        self.nvic.finish_current_isr() # Gimbal biter
        self.nvic.finish_current_isr() # Telemetri biter

# Taktik Simülasyon Koşturuluyor
seeker = MissileSeekerInterruptSystem()
seeker.simulate_combat_scenario()

print()
print("[*] ROKETSAN Arayıcı Başlık Muharebe Kesme Senaryosu:")
for trace in seeker.nvic.execution_trace:
    print(f"  {trace}")

assert seeker.laser_target_locked == True
assert seeker.gimbal_cycles == 1
assert seeker.ring_buf.task_pop_bottom_half() == 0xDEAD
print("[HÜCRE 14] Taktik lazer arayıcı başlık kesme senaryosu başarıyla doğrulandı.")
```

## 9. Kod Açıklaması: Lazer Darbe Önceliği ve Çoklu Yuvalanma (Nesting)

Yukarıdaki taktik muharebe senaryosunda $3$ katmanlı yuvalanma doğrulanmıştır:
1. Füze yer istasyonuna telemetri yollarken (`Prio 2`), $2000\ \text{Hz}$ kanatçık gimbal döngüsü (`Prio 1`) araya girmiştir.
2. Tam o esnada hedeften yansıyan $1064\ \text{nm}$ lazer darbesi (`EXTI0 - Prio 0`) dedektöre çarpmış ve donanım anında iki görevi birden askıya alarak hedef koordinatını yakalamıştır.
3. Bu donanımsal öncelik hiyerarşisi sayesinde telemetri paketi ne kadar yoğun olursa olsun, füze hedefini asla ıskalamaz.

```python
# -*- coding: utf-8 -*-
"""
GÜN 166: Kod Bloğu 6 — 4 Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_166_interrupt_ve_isr.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_166\gun_166_interrupt_ve_isr.png"

# Matplotlib Karanlık Tema Ayarları
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.0

fig = plt.figure(figsize=(18, 12), dpi=300, facecolor='#0F172A')
fig.suptitle("GÜN 166: STM32 Kesmeler (Interrupts), NVIC Mimarisi, Preemption ve ISR Tasarımı Panosu",
             fontsize=14, fontweight='bold', color='#38BDF8', y=0.98)

# -----------------------------------------------------------------------------
# PANEL 1: NVIC Preemption Hiyerarşisi ve Çok Katmanlı Yuvalanma (Nesting)
# -----------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1)
ax1.set_facecolor('#1E293B')
ax1.set_title("Panel 1: NVIC Donanımsal Kesme Yuvalanması (Preemption Nesting)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax1.axis('off')

# Katman 1: Main Thread
ax1.add_patch(patches.Rectangle((0.05, 0.10), 0.90, 0.16, facecolor='#064E3B', edgecolor='#10B981', lw=1.5))
ax1.text(0.50, 0.18, "ANA KULLANICI GÖREVİ (Thread Mode - Normal Yürütme)", ha='center', va='center', color='#A7F3D0', fontweight='bold', fontsize=8.5)

# Katman 2: USART ISR
ax1.add_patch(patches.Rectangle((0.15, 0.34), 0.75, 0.16, facecolor='#1E3A8A', edgecolor='#3B82F6', lw=1.5))
ax1.text(0.52, 0.42, "USART1 TELEMETRİ ISR (Preemption Prio 2 - Düşük)", ha='center', va='center', color='#93C5FD', fontweight='bold', fontsize=8.5)

# Katman 3: TIM1 Motor PID
ax1.add_patch(patches.Rectangle((0.30, 0.58), 0.55, 0.16, facecolor='#78350F', edgecolor='#F59E0B', lw=1.5))
ax1.text(0.57, 0.66, "TIM1 GİMBAL PID ISR (Preemption Prio 1 - Orta)", ha='center', va='center', color='#FDE68A', fontweight='bold', fontsize=8.5)

# Katman 4: EXTI0 Lazer Dedektör
ax1.add_patch(patches.Rectangle((0.48, 0.80), 0.32, 0.16, facecolor='#7F1D1D', edgecolor='#EF4444', lw=2))
ax1.text(0.64, 0.88, "EXTI0 LAZER ISR (Prio 0 - EN ACİL)", ha='center', va='center', color='#FCA5A5', fontweight='bold', fontsize=8.5)

# Olay Akış Okları
ax1.annotate("", xy=(0.15, 0.34), xytext=(0.15, 0.26), arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2))
ax1.annotate("", xy=(0.30, 0.58), xytext=(0.30, 0.50), arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2))
ax1.annotate("", xy=(0.48, 0.80), xytext=(0.48, 0.74), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2))

ax1.set_xlim(0.0, 1.0)
ax1.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 2: Klasik Kesme vs ARM Cortex-M Tail-Chaining & Late-Arrival
# -----------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2)
ax2.set_facecolor('#1E293B')
ax2.set_title("Panel 2: Tail-Chaining Sıfır Maliyetli Kesme Geçişi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax2.axis('off')

# Geleneksel İşlemci
ax2.text(0.05, 0.86, "1. GELENEKSEL İŞLEMCİ: Tam Unstack + Tam Stacking (24-32 Çevrim İsraf)", color='#EF4444', fontweight='bold', fontsize=8)
ax2.add_patch(patches.Rectangle((0.05, 0.70), 0.28, 0.12, facecolor='#059669', edgecolor='#FFFFFF', lw=1))
ax2.text(0.19, 0.76, "ISR 1 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

ax2.add_patch(patches.Rectangle((0.35, 0.70), 0.25, 0.12, facecolor='#EF4444', edgecolor='#FFFFFF', lw=1))
ax2.text(0.47, 0.76, "POP + PUSH\n(24 Çevrim İsraf!)", ha='center', va='center', color='#FFFFFF', fontsize=7)

ax2.add_patch(patches.Rectangle((0.62, 0.70), 0.28, 0.12, facecolor='#0284C7', edgecolor='#FFFFFF', lw=1))
ax2.text(0.76, 0.76, "ISR 2 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

# ARM Cortex-M Tail-Chaining
ax2.text(0.05, 0.48, "2. ARM CORTEX-M: Tail-Chaining ile Sıfır Bellek Erişimi (Sadece 6 Çevrim)", color='#10B981', fontweight='bold', fontsize=8)
ax2.add_patch(patches.Rectangle((0.05, 0.32), 0.38, 0.12, facecolor='#059669', edgecolor='#FFFFFF', lw=1))
ax2.text(0.24, 0.38, "ISR 1 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

ax2.add_patch(patches.Rectangle((0.45, 0.32), 0.10, 0.12, facecolor='#F59E0B', edgecolor='#FFFFFF', lw=1))
ax2.text(0.50, 0.38, "TC\n(6ç)", ha='center', va='center', color='#FFFFFF', fontsize=7.5, fontweight='bold')

ax2.add_patch(patches.Rectangle((0.57, 0.32), 0.38, 0.12, facecolor='#0284C7', edgecolor='#FFFFFF', lw=1))
ax2.text(0.76, 0.38, "ISR 2 Çalışıyor", ha='center', va='center', color='#FFFFFF', fontsize=7.5)

# Açıklama
ax2.text(0.50, 0.14, "* Yazmaçlar yığından geri yüklenmez; doğrudan sıradaki kesme vektör adresine sıçranır.",
         ha='center', va='center', color='#CBD5E1', fontsize=8, fontstyle='italic')

ax2.set_xlim(0.0, 1.0)
ax2.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 3: Top-Half vs Bottom-Half Mimarisi ve Ring Buffer
# -----------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3)
ax3.set_facecolor('#1E293B')
ax3.set_title("Panel 3: İki Aşamalı Kesme Mimarisi (Top-Half vs Bottom-Half)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax3.axis('off')

# Top Half Kutusu
ax3.add_patch(patches.FancyBboxPatch((0.05, 0.45), 0.42, 0.45, boxstyle="round,pad=0.02", facecolor='#7F1D1D', edgecolor='#EF4444', lw=2))
ax3.text(0.26, 0.82, "TOP-HALF (ISR)", ha='center', va='center', color='#F87171', fontweight='bold', fontsize=11)
ax3.text(0.26, 0.73, "Süre: < 2 us (Ultra Hızlı)", ha='center', va='center', color='#FDE68A', fontsize=8.5)
ax3.text(0.26, 0.64, "1. Donanım Bayrağını Sil (PR=1)\n2. Veriyi Donanımdan Oku\n3. Ring Buffer'a İt (Push)\n4. Derhal Çık!", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

# Bottom Half Kutusu
ax3.add_patch(patches.FancyBboxPatch((0.53, 0.45), 0.42, 0.45, boxstyle="round,pad=0.02", facecolor='#064E3B', edgecolor='#10B981', lw=2))
ax3.text(0.74, 0.82, "BOTTOM-HALF (Task)", ha='center', va='center', color='#34D399', fontweight='bold', fontsize=11)
ax3.text(0.74, 0.73, "Süre: Esnek (Thread Modu)", ha='center', va='center', color='#FDE68A', fontsize=8.5)
ax3.text(0.74, 0.64, "1. Ring Buffer'dan Veri Çek\n2. Ağır Matematik / Kalman\n3. Paket Çözümleme / CRC\n4. Kesmeleri Asla Engellemez!", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

# Ortadaki Köprü: Ring Buffer
ax3.add_patch(patches.Rectangle((0.20, 0.12), 0.60, 0.22, facecolor='#0F172A', edgecolor='#38BDF8', lw=1.5))
ax3.text(0.50, 0.27, "LOCK-FREE CIRCULAR RING BUFFER", ha='center', va='center', color='#38BDF8', fontweight='bold', fontsize=9)
ax3.text(0.50, 0.18, "ISR (Top-Half) -> [Veri Yaz] -> BUFFER -> [Veri Oku] -> Task (Bottom-Half)", ha='center', va='center', color='#CBD5E1', fontsize=7.5)

ax3.set_xlim(0.0, 1.0)
ax3.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 4: EXTI Write-1-to-Clear ve Starvation Lockup Analizi
# -----------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4)
ax4.set_facecolor('#1E293B')
ax4.set_title("Panel 4: EXTI->PR Write-1-to-Clear ve Kilitlenme (Starvation) Riski", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

t_axis = np.linspace(0, 10, 500)
# Normal Senaryo: Bayrak temizlenir, tek çağrı
# Kilitlenme Senaryosu: Bayrak temizlenmez, sonsuz tetikleme
normal_exec = [1.0 if (1.0 <= t <= 1.2) else 0.0 for t in t_axis]
lockup_exec = [1.0 if t >= 4.0 else 0.0 for t in t_axis]

ax4.plot(t_axis, [v + 1.4 for v in normal_exec], color='#34D399', lw=2.2, label="Doğru Kullanım: PR=1 ile Silindi (Tek Temiz ISR)")
ax4.plot(t_axis, lockup_exec, color='#EF4444', lw=2.2, label="Sabotaj / Hata: Bayrak Silinmedi (Sonsuz ISR Kilitlenmesi / Starvation)")

ax4.axvline(4.0, color='#F59E0B', linestyle='--', lw=1.5)
ax4.text(4.2, 0.5, "Bayrak Temizlenmedi!\nİşlemci sonsuz kesme döngüsüne kilitlendi!", color='#FCA5A5', fontsize=8, fontweight='bold')

ax4.set_xlabel("Zaman (ms)", color='#94A3B8')
ax4.set_ylabel("CPU Yürütme Durumu", color='#94A3B8')
ax4.set_yticks([0, 1, 1.4, 2.4])
ax4.set_yticklabels(["Boş", "ISR (Kilitli)", "Thread", "ISR (Temiz)"])
ax4.set_ylim(-0.2, 2.8)
ax4.grid(True, color='#334155', alpha=0.5, linestyle='--')
ax4.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 166 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert len(nvic.active_stack) == 0
assert event_generated == True
assert lockup_detected == True
assert delay_fault_caught == True
assert processed_data == telemetry_data
assert seeker.laser_target_locked == True

print()
print("[PASS] Gün 166: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
```

## 10. Görselleştirme Açıklaması ve Mimari Yorumlar

Üretilen 4 panelli yüksek çözünürlüklü (300 DPI) mimari pano, NVIC kesme kontrolünün tüm katmanlarını sergiler:
1. **Panel 1: NVIC Donanımsal Kesme Yuvalanması (Preemption Nesting):**
   Thread modundan başlayan akışta `USART1 (Prio 2)`, `TIM1 (Prio 1)` ve `EXTI0 (Prio 0)` hiyerarşik kesme katmanları ve donanımsal stacking adımları gösterilmiştir.
2. **Panel 2: Tail-Chaining Sıfır Maliyetli Kesme Geçişi:**
   Klasik işlemcilerin 24-32 çevrimlik çifte stack külfeti ile Cortex-M'in 6 çevrimlik sıfır bellek erişimli donanım optimizasyonu kıyaslanmıştır.
3. **Panel 3: İki Aşamalı Kesme Mimarisi (Top-Half vs Bottom-Half):**
   Top-Half'ın $2\ \mu\text{s}$'lik hızlı donanım etkileşimi ve Lock-Free Ring Buffer üzerinden Bottom-Half arka plan görevine veri aktarımı şematize edilmiştir.
4. **Panel 4: EXTI->PR Write-1-to-Clear ve Kilitlenme Riski:**
   Bayrağın doğru silindiği tek darbelik temiz yürütme ile bayrağın silinmeyip CPU'yu kilitlediği sonsuz kesme fırtınası zaman ekseninde görselleştirilmiştir.

## 11. Karşılaştırmalı Analiz: Polling vs Interrupt vs DMA

| Mimari Özellik | Yoklama (Polling) | Kesme Tabanlı (Interrupt - ISR) | Doğrudan Bellek Erişimi (DMA) |
| :--- | :--- | :--- | :--- |
| **CPU Müdahalesi** | **\%100 CPU Kullanımı (Sürekli Döngü)** | Olay Anında Minimum CPU ($12$ çevrim) | **SIFIR CPU Kullanımı (Sadece Transfer Sonu)** |
| **Reaksiyon Gecikmesi** | Çok Değişken (Döngü uzunluğuna bağlı) | **Deterministik ve Çok Hızlı ($< 1\ \mu\text{s}$)** | Donanımsal Bus Arbiter Gecikmesi |
| **Veri Aktarım Hızı** | Çok Düşük (Bayt bayt CPU okur) | Orta ($100\ \text{kHz} - 1\ \text{MHz}$ arası) | **Ultra Yüksek ($50 - 100\ \text{MB/s}$)** |
| **Kod Karmaşıklığı** | Çok Basit (`while` döngüsü) | Orta (Öncelik, Stack, Reentrancy) | Yüksek (Descriptor, Ring Buffer, Cache) |
| **Savunma Kullanımı** | Düşük hızlı kullanıcı paneli | **Acil durum alarmları, Limit anahtarları** | **Radar I/Q, Video akışı, Yüksek hızlı ADC** |

## 12. Donanım ve Çip Seviyesi Ayrıntılar (VTOR Relocation, Fault Handlers)

### 1. VTOR (Vector Table Offset Register - `0xE000 ED08`):
Normalde Vektör Tablosu Flash belleğin başında (`0x0800 0000`) yer alır.
- Aviyonik sistemlerde Bootloader'dan Ana Uçuş Yazılımına geçerken veya çalışma anında dinamik ISR değiştirmek için Vektör Tablosu RAM'e taşınabilir:
  ```c
  SCB->VTOR = 0x20000000; // Artık kesme vektörleri SRAM'den okunur!
  ```
- RAM'e taşınan vektör tablosu, kesme adreslerinin çalışma anında sıfır Flash bekleme süresiyle ($0\ \text{WS}$) okunmasını sağlar.

### 2. Sabit Donanımsal İstisnalar (Fixed Negative Priorities):
Cortex-M mimarisinde yazılımla değiştirilemeyen 3 sabit donanım önceliği vardır:
- **Reset:** Öncelik `-3` (Dünyanın en yüksek önceliği)
- **NMI (Non-Maskable Interrupt):** Öncelik `-2` (Saat arızası, ECC bellek çökmesi)
- **HardFault:** Öncelik `-1` (Bilinmeyen komut, veri yolu hatası)
Bu 3 istisna hiçbir yazılım komutu (`cpsid i`, `__disable_irq`) ile maskelenemez!

## 13. Güvenlik, Hata Ayıklama ve Taktik İpuçları (Cortex-M Memory Barrier: DSB / ISB)

### 1. ISR Çıkışında Gizli Tekrar Tetiklenme Tuzağı (Bus Latency):
Cortex-M4 ve Cortex-M7 işlemcilerde yazma tamponu (**Write Buffer**) bulunur.
- Bir ISR'ın sonunda `EXTI->PR = (1 << pin);` yazdığınızda bu veri hemen donanım yazmacına ulaşmayabilir, Write Buffer'da birkaç saat çevrimi bekleyebilir.
- İşlemci hemen ardından `BX LR` komutu ile kesmeden çıkarsa, donanım henüz silme işlemini tamamlamadığı için **AYNI KESMEYE TEKRAR GİRER**!
- **Askeri Standart Çözüm:** Bayrak silindikten hemen sonra bir `DSB` (Data Synchronization Barrier) komutu konulmalıdır:
  ```c
  void EXTI0_IRQHandler(void) {
      EXTI->PR = EXTI_PR_PR0; // Bayrağı sil
      __DSB(); // Bellek yazma tamponunun boşalmasını zorla bekle!
  }
  ```

### 2. Kritik Bölge Yönetimi (`PRIMASK` vs `BASEPRI`):
- `__disable_irq()` (`cpsid i`): Tüm kesmeleri kapatır. Ancak bu kaba yöntem gerçek zamanlı işletim sistemlerinde motor PID döngüsünü de durdurarak felakete yol açabilir.
- **`BASEPRI` Kullanımı:** Sadece belirli bir seviyenin altındaki kesmeleri kapatır. Örneğin `__set_BASEPRI(0x50)` derseniz, Öncelik 0, 1, 2 ve 3 çalışmaya devam eder; sadece önemsiz arka plan kesmeleri maskelenir!

## 14. Günün Mini Uygulaması: STM32 Çok Seviyeli Kesme ve Arayıcı Başlık Simülatörü

Günün mini uygulamasında:
1. ARM Cortex-M NVIC öncelik ve yuvalanma motoru kodlanmış; `EXTI0 (0)`, `TIM1 (1)` ve `USART1 (2)` arasındaki çok seviyeli preemption hiyerarşisi doğrulanmıştır.
2. STM32 `EXTI` donanımı ve Write-1-to-Clear kuralı modellenmiştir.
3. ISR içinde bayrak silmeyi unutma (Starvation Lockup) ve bloklayıcı gecikme çalıştırma sabotaj testleri yapılmıştır.
4. Sıfır kilitli, yarış durumundan muaf **Lock-Free Dairesel Bellek (Ring Buffer)** ile Top-Half / Bottom-Half ayrımı gerçekleştirilmiştir.
5. ROKETSAN lazer güdümlü füze optik arayıcı başlığında telemetri ve kanatçık motoru çalışırken lazer darbesinin sisteme araya girme (preemption) senaryosu test edilmiştir.

## 15. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **`EXTI->PR` Bayrağına 0 Yazarak Silmeye Çalışmak:** Donanımın Write-1-to-Clear olduğunu unutup bayrağı silemeyerek sistemi sonsuz kesme döngüsüne sokmak.
2. **ISR İçinde `HAL_Delay` Kullanmak:** SysTick kesmesini bloke ederek sistemi kalıcı olarak dondurmak.
3. **Paylaşılan Değişkenlerde `volatile` Unutmak:** Derleyicinin değişkeni CPU yazmacında önbelleğe alıp ana döngünün kesme tarafından güncellenen veriyi görmesini engellemesi.
4. **Kritik Bölgelerde `__disable_irq()` ile Sistemi Saatlerce Kör Bırakmak:** Tüm kesmeleri kapatmak yerine yalnızca çakışan seviyeleri maskelemek için `BASEPRI` kullanılmalıdır.

## 16. Mülakat ve Saha Deneyimi Soruları (ASELSAN / ROKETSAN / TUSAŞ)

### Soru 1: ARM Cortex-M NVIC mimarisinde 'Preemption Priority' ile 'Sub-Priority' arasındaki hayati fark nedir?
**Cevap:** Preemption Priority (Araya Girme Önceliği), çalışan bir kesmeyi bölüp araya girebilme yeteneğidir. Eğer gelen kesmenin preemption önceliği o an çalışan kesmeden daha yüksekse (sayısal olarak daha küçükse), işlemci çalışan kesmeyi durdurur, yazmaçları stack'e basar ve yeni kesmeye dalar. Sub-Priority (Alt Öncelik) ise sadece iki kesme aynı anda tetiklendiğinde hangisinin önce çalışacağını belirler; çalışan bir kesmeyi asla bölemez. FreeRTOS gibi gerçek zamanlı sistemlerde öncelik hiyerarşisinin bozulmaması için genellikle tüm 4 bit Preemption'a atanır (`NVIC_PRIORITYGROUP_4`).

### Soru 2: Bir ISR (Kesme Servis Rutini) içinde neden dinamik bellek tahsisi (`malloc` / `free`) veya `printf` gibi fonksiyonlar kullanılmamalıdır?
**Cevap:** Bu fonksiyonlar 'Reentrant' (yeniden girilebilir) değildir ve arkalarında dahili mutex/kilit yapıları barındırırlar. Eğer ana görev `malloc` çağırıp heap kilidini aldığı sırada bir kesme girer ve o da `malloc` çağırmaya kalkarsa, kesme zaten kilitli olan kaynağı beklemeye başlar; ancak kesme bitmeden ana görev kilidi serbest bırakamayacağı için sistem anında sonsuz kilitlenmeye (**Deadlock**) düşer. Ayrıca `printf` bloklayıcı I/O kullandığından kesme süresini milisaniyelere uzatarak sistemin tüm determinizmini yok eder.

### Soru 3: STM32'de bir EXTI kesmesinden çıkarken neden bazen `__DSB()` (Data Synchronization Barrier) komutu kullanılır?
**Cevap:** Cortex-M4/M7 işlemcilerde bellek yazma işlemlerini hızlandıran asenkron bir 'Write Buffer' (Yazma Tamponu) bulunur. ISR içinde `EXTI->PR = 1;` yazıldığında bu emir hemen donanım yazmacına ulaşmayıp Write Buffer'da birkaç saat çevrimi bekleyebilir. Eğer işlemci hemen ardından kesmeden çıkarsa (`BX LR`), EXTI donanımı bayrağın hala silinmediğini sanarak işlemciyi aynı kesmeye ikinci kez sokar (sahte kesme). Araya konulan `__DSB()` komutu yazma tamponunun boşaltılmasını ve bayrağın silindiğinin onaylanmasını zorunlu kılar.

## 17. Gün Sonu Özeti ve 3-Cümle Çıkarımı

1. **Interrupt ve NVIC Nedir?:** Dış dünyadaki acil olayları yoklama döngüleri yerine donanımsal vektör tablosu ve 12 çevrimlik stacking ile nanosaniyeler içinde karşılayan mimaridir.
2. **Hangi Problemi Çözer?:** CPU'nun boş döngülerde kilitlenmesini önler; Preemption ile hayati füze ve radar alarmlarının düşük öncelikli telemetri görevlerini anında bölmesini sağlar.
3. **Hangi Trade-off/Hata Sınıfını Getirir?:** `EXTI->PR` bayrağının silinmemesi sonsuz kilitlenmeye (Starvation Lockup), ISR içinde uzun kod koşturulması ise diğer tüm sistemin gecikme oynamasına (Jitter) yol açar.

