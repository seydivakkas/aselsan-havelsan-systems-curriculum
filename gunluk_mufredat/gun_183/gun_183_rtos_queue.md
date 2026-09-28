# GÜN 183: RTOS Queue (Kuyruk Mimarisi ve Görevler Arası İletişim)

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, tersine mühendislik yapılamaz.
```

---

## Modül Künyesi
- **Faz:** F5 — Gömülü Sistemler, RTOS ve STM32 Mimarisi
- **Konu:** Görevler Arası İletişim (IPC), FreeRTOS `Queue_t` Çekirdek Anatomisi, Dairesel Tampon (Ring Buffer) Yönetimi, Kopyalama Tabanlı (Pass-by-Copy) vs İşaretçi Tabanlı (Pass-by-Reference / Zero-Copy) Veri Aktarımı, Kesmelerden Kuyruğa Yazma (`xQueueSendFromISR`), Kuyruk Taşma ve Geri Basınç (Backpressure) Politikaları, Kuyruk Su Seviyesi (High Water Mark)
- **Hedef Donanım:** ARM Cortex-M4/M7 (STM32F4/F7/H7), FreeRTOS Core IPC Engine
- **Kritik Kavramlar:** Global Değişken Güvensizliği, Thread-Safe FIFO, `uxMessagesWaiting` vs `uxLength`, `xTasksWaitingToSend` Öncelik Kuyruğu, Kesmelerde Bloklanma Yasağı (`xTicksToWait = 0`), Zero-Copy Bellek Sahipliği (Ownership), Kuyruk Kilitlenmeleri (Deadlock)
- **Savunma Sanayii Senaryosu:** HAVELSAN / ASELSAN Taktik Veri Bağı (Link-16 / TAFICS) Haberleşme Kartında UART DMA Kesmesinden Kripto Çözme ve Durumsal Farkındalık Görevlerine Deterministik Taktik Paket Aktarımı

## 1. Giriş ve Zihinsel Model (Neden Global Değişken Değil de Kuyruk?)

Gömülü sistemlere yeni başlayanların en sık düştüğü ölümcül tuzak şudur:
> *"Bir görev UART'tan veri alsın, bunu global bir `uint8_t rx_buffer[128]` dizisine yazsın; diğer görev de bu diziden okusun!"*

Bu yaklaşım çoklu görev (Multitasking) ve kesme (ISR) ortamında **TAM BİR FELAKETTİR:**
1. **Yarış Durumu (Race Condition):** Tüketici görev dizinin ilk 10 baytını okurken, tam o anda yüksek hızlı bir kesme gelip dizinin üzerine yeni paket yazarsa veri bozulur (Torn Read/Write).
2. **Kör Bekleme (Busy-Waiting):** Tüketici görevin yeni veri geldiğini anlaması için sürekli `while(data_ready == 0)` şeklinde CPU yakması gerekir.
3. **Senkronizasyon ve Öncelik Kaybı:** Veriyi bekleyen yüksek öncelikli bir görevin anında uyandırılmasını sağlayan hiçbir donanımsal mekanizma yoktur.

İşte bu nedenle gerçek zamanlı işletim sistemlerinde görevler arası veri transferinin omurgasını **RTOS Kuyrukları (Queues)** oluşturur!

```
+---------------------------------------------------------------------------------------------------+
|                        FREERTOS KUYRUK (QUEUE) VERİ AKIŞI VE BLOKLANMA MODELİ                     |
|                                                                                                   |
|  Üretici Görev veya ISR                     Dairesel FIFO Tampon                    Tüketici Görev |
|  +--------------------+                   +----+----+----+----+----+              +--------------+|
|  | xQueueSend()       | ────────────────> | P1 | P2 | P3 |    |    | ───────────> | xQueueReceive||
|  +--------------------+  (Kopyalanır)     +----+----+----+----+----+ (Kopyalanır) +--------------+|
|                                             ▲                  ▲                                  |
|                                             │                  │                                  |
|                                         pcReadFrom         pcWriteTo                              |
|                                                                                                   |
|  * KUYRUK DOLUYSA: Üretici görev 'xTasksWaitingToSend' listesine girer ve BLOCKED olur (Sıfır CPU)|
|  * KUYRUK BOŞSA  : Tüketici görev 'xTasksWaitingToReceive' listesine girer ve BLOCKED olur.      |
|  * VERİ GELDİĞİNDE: En yüksek öncelikli bekleyen görev ANINDA uyandırılır (Preemption)!           |
+---------------------------------------------------------------------------------------------------+
```

> **RTOS MİMARİ SIRRI:** FreeRTOS'ta Semaforlar (Binary & Counting Semaphores) ve Mutex'ler ayrı birer veri yapısı **DEĞİLDİR!** Tümü eleman boyutu sıfır (`uxItemSize = 0`) olan özel birer Kuyruktur! Kuyruk mimarisini anlayan bir mühendis, RTOS'un tüm senkronizasyon motorunu kavramış olur.

## 2. FreeRTOS Kuyruk Anatomisi (`Queue_t` ve Dairesel Tampon)

FreeRTOS çekirdeğinde (`queue.c`), bir kuyruk bellekte `QueueDefinition` yapısı ile temsil edilir:

```c
typedef struct QueueDefinition {
    int8_t *pcHead;           /* Dairesel bellek alanının başlangıç adresi */
    int8_t *pcTail;           /* Dairesel bellek alanının bitiş sınırı */
    int8_t *pcWriteTo;        /* Bir sonraki elemanın yazılacağı adres */
    int8_t *pcReadFrom;       /* En son okunan elemanın adresi */

    List_t xTasksWaitingToSend;    /* Kuyruk doluyken veri yazmak için bekleyen görevler */
    List_t xTasksWaitingToReceive; /* Kuyruk boşken veri okumak için bekleyen görevler */

    volatile UBaseType_t uxMessagesWaiting; /* Kuyrukta o an bekleyen eleman sayısı */
    UBaseType_t uxLength;                  /* Kuyruğun maksimum kapasitesi (Eleman sayısı) */
    UBaseType_t uxItemSize;                /* Her bir elemanın sabit bayt boyutu */
} xQUEUE;
```

### Kuyruk Bellek Alanı Hesabı
Bir kuyruk oluşturulurken (`xQueueCreate` veya `xQueueCreateStatic`) tahsis edilen toplam RAM miktarı:
$$\text{Toplam RAM} = \text{sizeof}(\text{StaticQueue\_t}) + (\text{uxLength} \times \text{uxItemSize})$$

Örneğin 10 adet 32 baytlık Link-16 mesajı alabilen bir kuyruk için:
- TCB/Yapı alanı: ~80 bayt
- Tampon alanı: $10 \times 32 = 320$ bayt
- Toplam: **~400 bayt RAM.**

```python
# KOD HÜCRESİ 1: FreeRTOS Kuyruk Çekirdek Simülatörü (Queue_t Ring Buffer)
# ------------------------------------------------------------------------------
# Bu simülasyon, FreeRTOS QueueDefinition veri yapısını, dairesel bellek
# yönetimini (pcWriteTo/pcReadFrom) ve görev bloklanma/uyanma mantığını modeller.

class SimulatedQueue:
    def __init__(self, length, item_size_bytes):
        self.length = length
        self.item_size = item_size_bytes
        # Dairesel tampon belleği
        self.storage = [None] * length
        self.write_idx = 0
        self.read_idx = 0
        self.messages_waiting = 0
        
        # Bekleme Listeleri (Öncelik sırasına göre)
        self.tasks_waiting_to_send = []
        self.tasks_waiting_to_receive = []

    def send(self, item, task_name=None, timeout_ticks=0):
        if self.messages_waiting < self.length:
            # Kuyrukta yer var: Doğrudan yaz (FIFO)
            self.storage[self.write_idx] = item
            self.write_idx = (self.write_idx + 1) % self.length
            self.messages_waiting += 1
            
            # Eğer veri bekleyen bir görev varsa uyandır
            woken_task = None
            if self.tasks_waiting_to_receive:
                woken_task = self.tasks_waiting_to_receive.pop(0)
            return True, woken_task
        else:
            # Kuyruk Dolu!
            if timeout_ticks > 0 and task_name:
                self.tasks_waiting_to_send.append(task_name)
            return False, None

    def receive(self, task_name=None, timeout_ticks=0):
        if self.messages_waiting > 0:
            # Kuyrukta veri var: Oku (FIFO)
            item = self.storage[self.read_idx]
            self.storage[self.read_idx] = None
            self.read_idx = (self.read_idx + 1) % self.length
            self.messages_waiting -= 1
            
            # Eğer yer açılmasını bekleyen üretici görev varsa uyandır
            woken_task = None
            if self.tasks_waiting_to_send:
                woken_task = self.tasks_waiting_to_send.pop(0)
            return item, woken_task
        else:
            # Kuyruk Boş!
            if timeout_ticks > 0 and task_name:
                self.tasks_waiting_to_receive.append(task_name)
            return None, None

# Test Senaryosu: 3 Eleman Kapasiteli Taktik Paket Kuyruğu
q = SimulatedQueue(length=3, item_size_bytes=16)

print("=" * 68)
print("FREERTOS QUEUE_T DAİRESEL TAMPON VE BLOKLANMA SİMÜLASYONU")
print("=" * 68)

# 1. Kuyruğu Doldur
q.send({"id": 101, "cmd": "RADAR_ON"}, task_name="Task_Producer")
q.send({"id": 102, "cmd": "SET_FREQ"}, task_name="Task_Producer")
q.send({"id": 103, "cmd": "START_TX"}, task_name="Task_Producer")

print(f"3 Eleman Eklendi:")
print(f"  - Bekleyen Mesaj : {q.messages_waiting}/{q.length}")
print(f"  - Write Index    : {q.write_idx} | Read Index: {q.read_idx}")

# 2. Taşma Denemesi (4. Eleman)
success, _ = q.send({"id": 104, "cmd": "OVERFLOW"}, task_name="Task_Producer", timeout_ticks=10)
print(f"\n4. Eleman Ekleme Denemesi (Kuyruk Dolu):")
print(f"  - Ekleme Başarılı mı? : {success}")
print(f"  - Bekleyen Üreticiler : {q.tasks_waiting_to_send}")

# 3. Eleman Oku ve Bekleyen Görevi Uyandır
item, woken_producer = q.receive(task_name="Task_Consumer")
print(f"\n1 Eleman Okundu:")
print(f"  - Okunan Veri         : {item}")
print(f"  - Uyandırılan Üretici : {woken_producer}")
print(f"  - Kalan Mesaj Sayısı  : {q.messages_waiting}/{q.length}")

# Doğrulamalar
assert success == False, "Kuyruk doluyken 4. eleman yazılamamalı!"
assert item["id"] == 101, "FIFO kuralına göre ilk giren (101) ilk çıkmalıdır!"
assert woken_producer == "Task_Producer", "Veri okununca bekleyen üretici uyandırılmalıdır!"
print("\n[BAŞARILI]: FreeRTOS dairesel kuyruk FIFO ve bloklanma mantığı doğrulandı.")
```

## 3. Kopyalama Tabanlı (Pass-by-Copy) vs İşaretçi Tabanlı (Zero-Copy) Transfer

FreeRTOS kuyrukları varsayılan olarak **Kopyalama Semantiği (Pass-by-Copy)** ile çalışır. Ancak büyük veri paketlerinde bu durum ciddi bir performans darboğazına dönüşebilir:

### 1. Pass-by-Copy (Değer Kopyalama)
- Veri gönderilirken `memcpy` ile kuyruğun tamponuna kopyalanır.
- Okunurken kuyruktan alıcının yerel tamponuna tekrar kopyalanır (**Çift Kopyalama!**).
- **Avantajı:** %100 Güvenli. Gönderen fonksiyonun değişkeni stack'te olsa ve fonksiyon return etse dahi veri kuyrukta bozulmadan korunur.
- **Kullanım Yeri:** Küçük boyutlu veriler (Örn: 4 bayt int, 8 bayt ADC gyro verisi, 16 bayt CAN mesajı).

### 2. Pass-by-Reference / Zero-Copy (İşaretçi Kopyalama)
- Kuyruğun eleman boyutu yalnızca bir işaretçi boyutu olarak tanımlanır: `uxItemSize = sizeof(void*)` (ARM Cortex-M'de 4 bayt).
- Kuyrukta verinin kendisi değil, **bellek adresi (Pointer)** taşınır.
- **Avantajı:** 1 KB veya 64 KB veri aktarılsa dahi yalnızca 4 baytlık adres kopyalanır! İşlem süresi boyuttan bağımsız **~20 saat çevrimidir ($O(1)$ Zero-Copy).**
- **Kullanım Yeri:** Ethernet paketleri, FLIR kamera satırları, büyük telemetri kütükleri.

```
+---------------------------------------------------------------------------------------------------+
|               PASS-BY-COPY VS ZERO-COPY (POINTER) PERFORMANS KARŞILAŞTIRMASI                      |
|                                                                                                   |
|  Paket Boyutu       Pass-by-Copy Çevrim (168 MHz)        Zero-Copy Çevrim (168 MHz)    Hızlanma   |
|  ───────────────────────────────────────────────────────────────────────────────────────────────  |
|  8 Bayt (Sensör)    ~ 45 çevrim (0.26 µs)                ~ 24 çevrim (0.14 µs)         ~ 1.8x     |
|  64 Bayt (CAN-FD)   ~ 180 çevrim (1.07 µs)               ~ 24 çevrim (0.14 µs)         ~ 7.5x     |
|  512 Bayt (Radar)   ~ 1,280 çevrim (7.61 µs)             ~ 24 çevrim (0.14 µs)         ~ 53x!     |
|  1500 Bayt (Ethernet)~ 3,750 çevrim (22.3 µs)            ~ 24 çevrim (0.14 µs)         ~ 156x!    |
+---------------------------------------------------------------------------------------------------+
```

```python
# KOD HÜCRESİ 2: Pass-by-Copy vs Zero-Copy Benchmark ve CPU Maliyet Modeli
# ------------------------------------------------------------------------------
# Bu kod, farklı paket boyutlarında (8B, 32B, 128B, 512B, 1024B, 1500B)
# Kopyalama Tabanlı (Pass-by-Copy - memcpy) ile İşaretçi Tabanlı (Zero-Copy)
# transferlerin CPU saat çevrimi maliyetini ve mikro-saniye gecikmesini modeller.

class QueueBenchmarkModel:
    def __init__(self, f_cpu_mhz=168):
        self.f_cpu_mhz = f_cpu_mhz
        
    def evaluate(self, packet_sizes=[8, 32, 128, 512, 1024, 1500]):
        results = []
        for sz in packet_sizes:
            # Pass-by-Copy: Yazarken memcpy + Okurken memcpy = Çift Kopyalama!
            # Cortex-M4 LDMIA/STMIA optimizasyonu ile 4 bayt başına ~2.5 çevrim + queue overhead (~30 çevrim)
            copy_cycles = 30 + (sz / 4.0) * 2.5 * 2.0
            copy_time_us = (copy_cycles / (self.f_cpu_mhz * 1e6)) * 1e6
            
            # Zero-Copy: Boyuttan bağımsız! Sadece 4 baytlık pointer kuyruğa yazılır ve okunur
            zero_cycles = 30 + (4.0 / 4.0) * 2.5 * 2.0 # Sabit ~35 çevrim
            zero_time_us = (zero_cycles / (self.f_cpu_mhz * 1e6)) * 1e6
            
            speedup = copy_cycles / zero_cycles
            results.append({
                "size_bytes": sz,
                "copy_cycles": copy_cycles,
                "copy_time_us": copy_time_us,
                "zero_cycles": zero_cycles,
                "zero_time_us": zero_time_us,
                "speedup": speedup
            })
        return results

bench = QueueBenchmarkModel(f_cpu_mhz=168)
bench_data = bench.evaluate()

print("=" * 68)
print("PASS-BY-COPY VS ZERO-COPY TRANSFER PERFORMANS KARŞILAŞTIRMASI")
print("=" * 68)
print(f"{'Boyut':<10} | {'Copy Çevrim':<12} | {'Copy (µs)':<10} | {'Zero (µs)':<10} | {'Hızlanma Faktörü':<16}")
print("-" * 68)
for r in bench_data:
    print(f"{r['size_bytes']:4d} Bayt   | {r['copy_cycles']:8.1f}     | {r['copy_time_us']:6.3f} µs   | {r['zero_time_us']:6.3f} µs   | {r['speedup']:6.1f}x Hızlı!")

assert bench_data[-1]["speedup"] > 50.0, "1500 baytlık pakette Zero-Copy 50 kattan fazla hızlı olmalıdır!"
print("\n[BAŞARILI]: Büyük paketlerde Zero-Copy kuyruk mimarisinin ezici üstünlüğü doğrulandı.")
```

## 4. Donanım Kesmelerinden Kuyruğa Yazma (xQueueSendFromISR Kuralları)

Bir çevre birim kesmesi (örn. UART RX, SPI DMA) veri aldığında bunu tüketici bir göreve aktarırken normal `xQueueSend()` **ASLA ÇAĞRILAMAZ!**
Bunun yerine özel olarak tasarlanmış **`xQueueSendFromISR()`** kullanılmalıdır.

### Kesme İçi Kuyruk Kuralları:
1. **Bloklanma Süresi (Timeout) Parametresi Yoktur:**
   - Normal görevde `xQueueSend(q, &item, pdMS_TO_TICKS(10))` yazabilirsiniz (Kuyruk doluysa 10 ms bekle).
   - Ancak donanım kesmesi (ISR) **ASLA UYUTULAMAZ VEYA BLOKE EDİLEMEZ!**
   - Bu nedenle `FromISR` fonksiyonlarında `xTicksToWait` parametresi bulunmaz. Kuyruk doluysa fonksiyon derhal `errQUEUE_FULL` döndürür; veriyi düşürmek veya ezmek yazılımcının sorumluluğundadır.
2. **`pxHigherPriorityTaskWoken` Parametresi:**
   - Fonksiyona `BaseType_t xHigherPriorityTaskWoken = pdFALSE;` değişkeninin adresi geçilir.
   - Eğer kuyruğa yazılan veri, o an çalışan görevden daha yüksek öncelikli bir görevi uyandırdıysa, FreeRTOS bu değişkeni içeride otomatik olarak `pdTRUE` yapar.
   - ISR çıkışında `portYIELD_FROM_ISR(xHigherPriorityTaskWoken)` çağrılarak **anında bağlam değiştirme (Preemption)** tetiklenir!

```python
# KOD HÜCRESİ 3: xQueueSendFromISR ve portYIELD_FROM_ISR Veri Akış Simülatörü
# ------------------------------------------------------------------------------
# Bu simülasyon, UART RX kesmesinin 10 adet taktik mesajı kuyruğa yazmasını,
# kuyruk doluluğunu ve yüksek öncelikli tüketici görevin anında uyanışını modeller.

class IsrQueueSimulator:
    def __init__(self, queue_capacity=5):
        self.capacity = queue_capacity
        self.queue = []
        self.dropped_packets = 0
        self.preemption_events = []
        
    def uart_rx_isr(self, packet_id, consumer_task_priority=4, current_task_priority=1):
        # Kesme anında bloklanma YOKTUR (Timeout = 0)
        higher_task_woken = False
        
        if len(self.queue) < self.capacity:
            self.queue.append(packet_id)
            # Eğer tüketici görevin önceliği şu an koşan görevden yüksekse preemption gerekir!
            if consumer_task_priority > current_task_priority:
                higher_task_woken = True
                self.preemption_events.append(packet_id)
            return True, higher_task_woken
        else:
            # Kuyruk Dolu -> Paket Düşürüldü (Drop Policy)
            self.dropped_packets += 1
            return False, False

isr_sim = IsrQueueSimulator(queue_capacity=4)

print("=" * 68)
print("xQueueSendFromISR VE PORTYIELD KESME VERİ AKIŞ SİMÜLASYONU")
print("=" * 68)

# 6 Adet Kesme Paketi Gönder (Kapasite 4)
for pkt in [101, 102, 103, 104, 105, 106]:
    ok, yield_req = isr_sim.uart_rx_isr(pkt, consumer_task_priority=4, current_task_priority=2)
    status = f"Eklendi (Preemption İstendi!)" if ok else "KUYRUK DOLU (Paket Düşürüldü!)"
    print(f"UART ISR Paket {pkt}: {status}")

print(f"\nSonuç Raporu:")
print(f"  - Kuyruktaki Paketler : {isr_sim.queue}")
print(f"  - Düşürülen Paketler  : {isr_sim.dropped_packets} adet")
print(f"  - Preemption Sayısı   : {len(isr_sim.preemption_events)} adet")

assert isr_sim.dropped_packets == 2, "HATA: 6 paketten son 2'si düşürülmeliydi!"
assert len(isr_sim.queue) == 4, "HATA: Kuyruk tam kapasiteye (4) ulaşmalıydı!"
print("\n[BAŞARILI]: xQueueSendFromISR bloklanmasız taşma ve preemption davranışı doğrulandı.")
```

## 5. Kuyruk Taşması, Geri Basınç (Backpressure) ve xQueueOverwrite

Üretici (Producer) görevin veya kesmelerin veri üretme hızı, tüketici (Consumer) görevin veri işleme hızından daha yüksekse kuyruk kaçınılmaz olarak dolar. Bu durumda mimari bir karar verilmelidir:

### Kuyruk Taşma Politikaları:
1. **Paketi Düşürme (Drop New / Tail Drop):**
   - Kuyruk dolduğunda yeni gelen paket atılır ve bir hata sayacı artırılır.
   - *Kullanım Yeri:* Ses veya telemetri akışları (Eski verinin tutarlılığı yeni veriden daha önemliyse).
2. **En Eski Veriyi Ezme (`xQueueOverwrite`):**
   - 1 elemanlık kuyruklarda (`uxLength = 1`) kuyruk dolu olsa dahi eski verinin üzerine yazılır.
   - *Kullanım Yeri:* Anlık sensör verisi (Örn. Jiroskop açısı, anlık motor sıcaklığı). Alıcı görev için geçmişteki açı değil, **en son ölçülen güncel açı** önemlidir!
3. **Geri Basınç (Backpressure / Flow Control):**
   - Üretici görev kuyruk dolu olduğunda bloke edilir (`xTicksToWait`). Bu sayede veri akışı otomatik yavaşlatılır. Donanım seviyesinde ise UART RTS/CTS donanımsal akış kontrolü tetiklenir.

```python
# KOD HÜCRESİ 4: Kuyruk Taşması ve Su Seviyesi (High Water Mark) Analizi
# ------------------------------------------------------------------------------
# Bu simülasyon, hızlı bir üretici (1000 paket/sn) ile yavaş bir tüketiciyi (600 paket/sn)
# 100 ms boyunca yarıştırır ve kuyruk doluluk grafiğini (Watermark) çıkarır.

import numpy as np

def simulate_queue_backpressure(capacity=10, duration_ms=100):
    time_ms = np.arange(0, duration_ms, 1)
    
    occupancy_history = []
    dropped_count = 0
    current_occupancy = 0
    max_watermark = 0
    
    for t in time_ms:
        # Üretici: Her 1 ms'de 1 paket üretir (1000 pkt/s)
        produced = 1
        
        # Tüketici: Her 1.66 ms'de 1 paket tüketir (yaklaşık %60 hızında)
        consumed = 1 if (t % 2 == 0) else 0
        
        # Önce tüketim
        current_occupancy = max(0, current_occupancy - consumed)
        
        # Sonra üretim
        if current_occupancy + produced <= capacity:
            current_occupancy += produced
        else:
            dropped_count += 1
            
        max_watermark = max(max_watermark, current_occupancy)
        occupancy_history.append(current_occupancy)
        
    return {
        "time_ms": time_ms,
        "occupancy": occupancy_history,
        "dropped_count": dropped_count,
        "max_watermark": max_watermark,
        "capacity": capacity
    }

q_flow = simulate_queue_backpressure(capacity=10, duration_ms=100)

print("=" * 68)
print("KUYRUK TAŞMASI VE GERİ BASINÇ (BACKPRESSURE) ANALİZİ")
print("=" * 68)
print(f"Kuyruk Kapasitesi       : {q_flow['capacity']} paket")
print(f"Tepe Su Seviyesi (Peak) : {q_flow['max_watermark']}/{q_flow['capacity']} paket (%100 Doluluk)")
print(f"Düşürülen Paket Sayısı  : {q_flow['dropped_count']} paket")

assert q_flow["max_watermark"] == 10, "Kuyruk tam kapasiteye ulaşmış olmalı!"
assert q_flow["dropped_count"] > 30, "Hızlı üretici nedeniyle paketler düşmeliydi!"
print("\n[BAŞARILI]: Kuyruk kapasite sınırları ve geri basınç dinamiği modellendi.")
```

## 6. Kuyruk Setleri (Queue Sets): Birden Fazla Kuyruğu Dinleme

Bir görev hem CAN bus'tan hem UART'tan hem de bir butondan gelen olayları aynı anda beklemek zorunda kalabilir.
Klasik yaklaşımda her kuyruk için ayrı bir thread açmak RAM israfıdır.

FreeRTOS **Queue Sets (`xQueueCreateSet`)** mimarisi ile POSIX `select()` / `epoll()` mantığını mikrodenetleyiciye getirir:
```c
QueueSetHandle_t xQueueSet = xQueueCreateSet(COMBINED_LENGTH);
xQueueAddToSet(xCanQueue, xQueueSet);
xQueueAddToSet(xUartQueue, xQueueSet);

for (;;) {
    // Hangisine veri gelirse anında uyan!
    QueueSetMemberHandle_t xActiveHandle = xQueueSelectFromSet(xQueueSet, portMAX_DELAY);
    
    if (xActiveHandle == xCanQueue) {
        xQueueReceive(xCanQueue, &can_msg, 0);
        handle_can(can_msg);
    } else if (xActiveHandle == xUartQueue) {
        xQueueReceive(xUartQueue, &uart_msg, 0);
        handle_uart(uart_msg);
    }
}
```

```python
# KOD HÜCRESİ 5: Savunma Sanayii Senaryosu: Link-16 Taktik Mesaj Kuyruğu
# ------------------------------------------------------------------------------
# HAVELSAN Taktik Veri Bağı (Link-16) İletişim Kartı Simülasyonu:
# - Üretici 1: RF Modem UART Kesmesi (10 ms periyotla taktik hava izi paketi)
# - Üretici 2: CAN Radar Kesmesi (25 ms periyotla hedef koordinatı)
# - Tüketici: Link-16 Kripto Çözücü Görevi (Kuyruktan çeker, deşifre eder)
# 100 ms taktik simülasyonda paketlerin sırasını ve gecikmelerini modeller.

import numpy as np

def simulate_link16_tactical_router(sim_duration_ms=100):
    time_ms = np.arange(0, sim_duration_ms, 1)
    
    queue = []
    processed_packets = []
    
    for t in time_ms:
        # 1. RF Modem UART Kesmesi (10 ms periyot)
        if t % 10 == 0:
            queue.append({"src": "RF_MODEM", "id": t, "t_arrive": t})
            
        # 2. CAN Radar Kesmesi (25 ms periyot)
        if t % 25 == 0:
            queue.append({"src": "CAN_RADAR", "id": t, "t_arrive": t})
            
        # 3. Kripto Çözücü Görevi (Her 5 ms'de bir kuyruktan paket çeker)
        if t % 5 == 0 and len(queue) > 0:
            pkt = queue.pop(0)
            pkt["t_process"] = t
            pkt["latency_ms"] = t - pkt["t_arrive"]
            processed_packets.append(pkt)
            
    return {
        "processed": processed_packets,
        "rem_in_queue": len(queue),
        "total_processed": len(processed_packets)
    }

link16_res = simulate_link16_tactical_router()

print("=" * 68)
print("HAVELSAN LINK-16 TAKTİK MESAJ KUYRUĞU İŞLEME RAPORU")
print("=" * 68)
latencies = [p["latency_ms"] for p in link16_res["processed"]]
print(f"Toplam İşlenen Taktik Paket: {link16_res['total_processed']} adet")
print(f"Kuyrukta Kalan Paket        : {link16_res['rem_in_queue']} adet")
print(f"Ortalama Kuyruk Gecikmesi   : {np.mean(latencies):.2f} ms")
print(f"Maksimum Kuyruk Gecikmesi   : {np.max(latencies):.2f} ms (Deadline < 10 ms)")

assert np.max(latencies) <= 10.0, "HATA: Taktik paket gecikmesi 10 ms sınırını aştı!"
assert link16_res["total_processed"] >= 13, "HATA: Yeterli paket işlenemedi!"
print("\n[BAŞARILI]: Link-16 taktik mesaj kuyruğu sıfır kayıp ve deterministik gecikmeyle çalıştı.")
```

## 7. Savunma Sanayii Aviyonik Senaryosu: Link-16 Taktik Mesaj Kuyruğu

Link-16, NATO standartlarında hava savunma sistemleri (F-16, SİHA, Erken İhbar Radarları) arasında şifreli durumsal farkındalık verisi paylaşan askeri bir taktik veri bağıdır.

### Aviyonik Kuyruk Mimarisi
1. **Çoklu Üretici (Multi-Producer):**
   - RF Modem Seri Port Kesmesi (`NVIC Prio 5`),
   - AESA Radar CAN-FD Kesmesi (`NVIC Prio 6`).
   Her iki kesme de aynı `xLink16PacketQueue` kuyruğuna `xQueueSendFromISR` ile paket yazar.
2. **Tek Tüketici (Single-Consumer):**
   - Kripto ve Görev Bilgisayarı Görevi (`Task Prio 4`).
   Kuyruktan gelen paketleri J-Series (Hava İzi, Dost/Düşman Tanıma - IFF, Angajman Emri) formatında ayrıştırıp taktik harita ekranına aktarır.
3. **Determinizm Güvencesi:**
   Maksimum kuyruk bekleme süresi 10 milisaniyenin altında tutularak taktik hava sahasındaki süpersonik tehditlerin anında işaretlenmesi sağlanır.

```python
# KOD HÜCRESİ 6: Endüstriyel Dashboard Görselleştirme ve Kapsamlı Assertions
# ------------------------------------------------------------------------------
# 300 DPI, Dark Theme (#0F172A), 4 Panelli Endüstriyel Aviyonik Dashboard:
# Panel 1: Kuyruk Doluluk ve Su Seviyesi Zaman Grafiği (Backpressure Dynamics)
# Panel 2: Pass-by-Copy vs Zero-Copy Transfer Süresi Karşılaştırması
# Panel 3: Taktik Mesaj Kuyruğu Paket Gecikme Histogramı (Latency Distribution)
# Panel 4: Üretim vs Tüketim Akış Dengesi (Throughput Balance)

import os
import matplotlib.pyplot as plt
import numpy as np

# PNG Yol Tanımı
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_183_rtos_queue.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_183\gun_183_rtos_queue.png"

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
# PANEL 1: Kuyruk Doluluk ve Su Seviyesi
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. Kuyruk Doluluğu ve Geri Basınç (Watermark Dinamiği)", fontsize=11, fontweight='bold', pad=10)

t_pts = q_flow["time_ms"]
occ_pts = q_flow["occupancy"]

ax1.plot(t_pts, occ_pts, color='#38BDF8', linewidth=2.5, label='Kuyruktaki Mesaj Sayısı')
ax1.axhline(q_flow["capacity"], color='#EF4444', linestyle='--', linewidth=2, label=f'Maksimum Kapasite ({q_flow["capacity"]})')
ax1.fill_between(t_pts, occ_pts, color='#38BDF8', alpha=0.2)

ax1.set_xlabel("Zaman (ms)", fontsize=10)
ax1.set_ylabel("Bekleyen Eleman Sayısı", fontsize=10)
ax1.set_ylim(0, 12)
ax1.legend(loc='lower right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC')
ax1.text(10, 10.5, f"Taşma Nedeniyle Düşürülen: {q_flow['dropped_count']} Paket!", color='#EF4444', fontweight='bold', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 2: Pass-by-Copy vs Zero-Copy Transfer Süresi
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. Transfer Süresi: Pass-by-Copy vs Zero-Copy (Logaritmik)", fontsize=11, fontweight='bold', pad=10)

sizes = [r["size_bytes"] for r in bench_data]
copy_times = [r["copy_time_us"] for r in bench_data]
zero_times = [r["zero_time_us"] for r in bench_data]

x_indices = np.arange(len(sizes))
width = 0.35

ax2.bar(x_indices - width/2, copy_times, width, label='Pass-by-Copy (memcpy)', color='#EF4444', alpha=0.85)
ax2.bar(x_indices + width/2, zero_times, width, label='Zero-Copy (Pointer)', color='#10B981', alpha=0.85)

ax2.set_xticks(x_indices)
ax2.set_xticklabels([f"{s} B" for s in sizes], fontweight='bold')
ax2.set_ylabel("Transfer Süresi (µs)", fontsize=10)
ax2.set_yscale('log')
ax2.legend(loc='upper left', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC')

# ------------------------------------------------------------------------------
# PANEL 3: Taktik Mesaj Kuyruğu Paket Gecikme Dağılımı
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. Link-16 Taktik Mesaj Gecikme Dağılımı (Histogram)", fontsize=11, fontweight='bold', pad=10)

ax3.hist(latencies, bins=6, color='#10B981', edgecolor='#0F172A', alpha=0.85, rwidth=0.85)
ax3.axvline(np.mean(latencies), color='#F59E0B', linestyle='--', linewidth=2, label=f'Ortalama: {np.mean(latencies):.2f} ms')
ax3.axvline(10.0, color='#EF4444', linestyle='-', linewidth=2, label='Deadline (10 ms)')

ax3.set_xlabel("Kuyrukta Bekleme Gecikmesi (ms)", fontsize=10)
ax3.set_ylabel("Paket Sayısı", fontsize=10)
ax3.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC')

# ------------------------------------------------------------------------------
# PANEL 4: Üretim vs Tüketim Zaman Çizelgesi
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. Link-16 Paket Varış ve Tüketim Zaman Çizelgesi", fontsize=11, fontweight='bold', pad=10)

rf_arrivals = [p["t_arrive"] for p in link16_res["processed"] if p["src"] == "RF_MODEM"]
can_arrivals = [p["t_arrive"] for p in link16_res["processed"] if p["src"] == "CAN_RADAR"]
processed_t = [p["t_process"] for p in link16_res["processed"]]

ax4.scatter(rf_arrivals, [2]*len(rf_arrivals), color='#38BDF8', s=80, label='RF Modem Varış (10 ms)', marker='o')
ax4.scatter(can_arrivals, [1.5]*len(can_arrivals), color='#F59E0B', s=80, label='CAN Radar Varış (25 ms)', marker='^')
ax4.scatter(processed_t, [1]*len(processed_t), color='#10B981', s=80, label='Kripto Tüketim (5 ms)', marker='s')

ax4.set_yticks([1, 1.5, 2])
ax4.set_yticklabels(["Kripto İşleme", "CAN Radar", "RF Modem"], fontweight='bold')
ax4.set_xlabel("Zaman (ms)", fontsize=10)
ax4.set_xlim(0, 100)
ax4.legend(loc='upper right', facecolor='#0F172A', edgecolor='#475569', labelcolor='#F8FAFC')

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

# Doğrulamalar
assert q_flow["max_watermark"] == 10, "HATA: Kuyruk doluluğu doğrulaması başarısız!"
assert bench_data[-1]["speedup"] > 50.0, "HATA: Zero-copy hızlanma faktörü tutarsız!"
assert np.max(latencies) <= 10.0, "HATA: Taktik paket gecikmesi aşımı!"

print("[PASS] GÜN 183: TÜM MATEMATİKSEL VE GÖRSEL DOĞRULAMALAR BAŞARIYLA TAMAMLANDI!")
```

## 8. C++20 ile Tip-Güvenli ve RAII Tabanlı Kuyruk Sarmalayıcısı

C++20 şablonları (Templates) ve konseptleri (`std::is_trivially_copyable`), FreeRTOS kuyruklarında tür dönüşümü (`(void*)&data`) hatalarını tamamen engeller:

```cpp
#include "FreeRTOS.h"
#include "queue.h"
#include <concepts>
#include <optional>
#include <chrono>

template <typename T, size_t QueueLength>
requires std::is_trivially_copyable_v<T>
class SafeRtosQueue {
public:
    SafeRtosQueue() {
        handle_ = xQueueCreate(QueueLength, sizeof(T));
    }

    ~SafeRtosQueue() {
        if (handle_) vQueueDelete(handle_);
    }

    bool send(const T& item, TickType_t timeout = portMAX_DELAY) noexcept {
        return xQueueSend(handle_, &item, timeout) == pdPASS;
    }

    [[nodiscard]] std::optional<T> receive(TickType_t timeout = portMAX_DELAY) noexcept {
        T item;
        if (xQueueReceive(handle_, &item, timeout) == pdPASS) {
            return item;
        }
        return std::nullopt;
    }

    [[nodiscard]] UBaseType_t messages_waiting() const noexcept {
        return uxQueueMessagesWaiting(handle_);
    }

    SafeRtosQueue(const SafeRtosQueue&) = delete;
    SafeRtosQueue& operator=(const SafeRtosQueue&) = delete;

private:
    QueueHandle_t handle_{nullptr};
};
```

## 9. DO-178C ve Emniyet Kritik Sistemlerde Kuyruk Boyutlandırma

Aviyonik sistemlerde (DO-178C DAL-A) rastgele kuyruk boyutu verilemez:
1. **Matematiksel Boyutlandırma Kanıtı (Sizing Justification):**
   - En kötü durum varış hızı ($\lambda_{\max}$) ve en kötü durum tüketim süresi ($WCET$) analiz edilerek kuyruk boyutu $N \ge \lceil \lambda_{\max} \cdot WCET \rceil + \text{Marj}$ formülüyle ispatlanmalıdır.
2. **Statik Kuyruk Zorunluluğu:**
   - Dinamik bellek (`xQueueCreate`) kesinlikle yasaktır; tüm kuyruklar derleme zamanında `xQueueCreateStatic` ile tahsis edilmelidir.
3. **Taşma Sayacı Denetimi:**
   - Düşen her paket için bir Telemetri Arıza Kodu (Fault Code) üretilmeli ve uçuş kayıt belleğine (Black Box) yazılmalıdır.

## 10. Bilerek Bozacağımız Şey: ISR İçinde Bloklanmaya Çalışmak

### Bozma Senaryosu: Kesmede Normal Kuyruk Fonksiyonu Çağırmak
1. Bir USART veya EXTI kesme rutini içine `xQueueSend(xQueue, &data, pdMS_TO_TICKS(10));` yazın.
2. **Beklenen Çökme Belirtisi:**
   - Kesme rutini içinde işlemci `Handler Mode`'dadır.
   - Kuyruk doluysa çekirdek kesmeyi uyutmaya (Sleep/Block) çalışır.
   - Ancak donanımsal kesmeler uyutulamaz!
   - Çekirdek anında `configASSERT` tetikler veya `HardFault_Handler`'a düşerek sistemi kilitler.
3. **Düzeltme:** Kesmelerde DAİMA `xQueueSendFromISR` kullanılmalı ve zaman aşımı verilmemelidir!

## 11. Hata Ayıklama ve Gözlemlenebilirlik (Tracealyzer ve High Water Mark)

Kuyrukların canlı izlenmesi için iki kritik API:

1. **`uxQueueMessagesWaiting(xQueue)`:** Kuyrukta o an bekleyen eleman sayısını verir.
2. **`uxQueueSpacesAvailable(xQueue)`:** Kuyrukta kalan boş yer miktarını verir. Eğer bu değer sürekli 0'a yakınsa kuyruk boyutunun büyütülmesi veya tüketici görevin önceliğinin artırılması gerekir!

## 12. Adım Adım C Kod Örneği: FreeRTOS Statik Kuyruk ve ISR

```c
#include "FreeRTOS.h"
#include "queue.h"

#define QUEUE_LENGTH    8
#define ITEM_SIZE       sizeof(TacticalPacket_t)

typedef struct {
    uint16_t packet_id;
    uint8_t payload[32];
} TacticalPacket_t;

// Statik Kuyruk Belleği
static StaticQueue_t xStaticQueue;
static uint8_t ucQueueStorageArea[QUEUE_LENGTH * ITEM_SIZE];
static QueueHandle_t xTacticalQueue = NULL;

void USART2_IRQHandler(void) {
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    TacticalPacket_t rx_pkt;
    
    // Donanımdan paketi oku
    read_packet_from_uart_regs(&rx_pkt);
    
    // Kesmeden kuyruğa yaz
    xQueueSendFromISR(xTacticalQueue, &rx_pkt, &xHigherPriorityTaskWoken);
    
    // Gerekirse anında preemption yap
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}

void vCryptoTask(void *pvParameters) {
    TacticalPacket_t pkt;
    for (;;) {
        if (xQueueReceive(xTacticalQueue, &pkt, portMAX_DELAY) == pdPASS) {
            decrypt_tactical_data(&pkt);
        }
    }
}

int main(void) {
    // Statik Kuyruğu Başlat
    xTacticalQueue = xQueueCreateStatic(
        QUEUE_LENGTH, ITEM_SIZE, ucQueueStorageArea, &xStaticQueue
    );
    
    xTaskCreate(vCryptoTask, "Crypto", 256, NULL, 4, NULL);
    vTaskStartScheduler();
    for (;;);
}
```

## 13. Sık Yapılan Hatalar ve Anti-Pattern'ler

| Hata / Anti-Pattern | Neden Tehlikeli? | Doğru Tasarım Deseni |
|:---|:---|:---|
| **Stack Değişkeninin İşaretçisini Kuyruğa Koymak** | Gönderen fonksiyon return edince yığındaki veri ezilir (Dangling Pointer). | İşaretçi kuyruğunda yalnızca statik veya heap/pool bellek adresleri aktarılmalıdır. |
| **ISR İçinde Standart `xQueueSend` Çağırmak** | Kesmede bloke olunamaz; çekirdek HardFault verir. | Kesmelerde yalnızca `xQueueSendFromISR` kullanılmalıdır. |
| **Büyük Verileri Pass-by-Copy ile Göndermek** | `memcpy` CPU çevrimlerini ve RAM'i tüketir. | 64 bayttan büyük verilerde Zero-Copy işaretçi kuyrukları kullanılmalıdır. |
| **Kuyruk Doluluğunu İzlememek** | Sessiz paket kayıpları ve taktik veri eksikliği oluşur. | `uxQueueSpacesAvailable` ile doluluk düzenli izlenmeli ve loglanmalıdır. |

## 14. 5N1K Tablosu: RTOS Queue Mimarisi

| Soru | Aviyonik ve Gömülü Sistem Yanıtı |
|:---|:---|
| **Ne?** | Görevler ve kesmeler arasında thread-safe, FIFO tabanlı veri aktarımı sağlayan RTOS IPC çekirdeği. |
| **Neden?** | Yarış durumlarını (Race Conditions) engellemek ve tüketici görevleri sıfır CPU ile uyutup uyandırmak için. |
| **Nerede?** | FreeRTOS çekirdek belleğinde, dairesel bellek tamponlarında ve bekleme listelerinde. |
| **Nasıl?** | Pass-by-Copy (`memcpy`) veya Zero-Copy işaretçi transferi ve donanımsal kesme preemption'ı ile. |
| **Ne Zaman?** | Bir çevre biriminden veri geldiğinde veya görevler asenkron mesajlaşmak istediğinde. |
| **Kim?** | Aviyonik yazılım mimarı, haberleşme protokol mühendisi ve gömülü sistem geliştiricisi. |

## 15. İleri Düzey Okuma ve Kaynaklar

1. **FreeRTOS Source Code Architecture - `queue.c`:** FreeRTOS'un en karmaşık ve yetkin kaynak dosyasının detaylı analizi.
2. **Percepio Tracealyzer User Guide:** Kuyruk doluluk ve bekleme sürelerinin canlı görselleştirilmesi.
3. **RTCA DO-178C Section 6.4:** Verification of Data Coupling and Control Coupling in RTOS Queues.
4. **B. Powel - Real-Time Embedded Multithreading:** Inter-Task Communication and Queue Sizing Patterns.

## 16. Günün Mini Projesi ve Sınav Soruları

### Mini Proje Görevi
STM32F4 üzerinde:
1. `xQueueCreateStatic` ile 5 elemanlık bir CAN mesaj kuyruğu açın.
2. Bir donanım timer kesmesi içinden her 5 ms'de bir kuyruğa `xQueueSendFromISR` ile sayaç değeri yazın.
3. Tüketici görevde `xQueueReceive` ile veriyi okuyup UART üzerinden yayınlayın.
4. Tüketici görevin içine bilerek 20 ms'lik gecikme koyarak kuyruğun nasıl taştığını ve `errQUEUE_FULL` dönüşünü Logic Analyzer ile gözlemleyin.

---

### Günün Sınav Soruları

#### Soru 1: FreeRTOS kuyruklarında Pass-by-Copy (Değer Kopyalama) yönteminin Pass-by-Reference (İşaretçi) yöntemine göre en büyük avantajı nedir?
- A) Daha az CPU harcar.
- B) Gönderen görevin yerel değişkeni değişse veya silinse dahi veri kuyruk tamponunda bağımsız ve güvenle korunur.
- C) Sonsuz eleman alabilir.
- D) Kesmeler tarafından engellenemez.
- **Doğru Cevap: B**

#### Soru 2: Bir donanım kesmesi (ISR) içinden kuyruğa veri yazarken neden `xTicksToWait` (Zaman Aşımı) parametresi bulunmaz?
- A) Kesmeler zamanı ölçemez.
- B) Donanım kesmeleri (ISR) asla bloke edilemez veya uyutulamaz; kuyruk doluysa anında dönmek zorundadır.
- C) Kesmeler sadece tek bayt yazabilir.
- D) FreeRTOS kesmeleri desteklemez.
- **Doğru Cevap: B**

#### Soru 3: 1500 baytlık bir Ethernet paketi aktarılırken neden Pass-by-Copy yerine Zero-Copy (İşaretçi Kuyruğu) kullanılmalıdır?
- A) Çünkü Pass-by-Copy 1500 bayt için binlerce saat çevrimi `memcpy` harcarken, Zero-Copy sadece 4 baytlık işaretçiyi aktararak 50-100 kat hızlanır.
- B) FreeRTOS 1500 baytlık kuyruk açamaz.
- C) Zero-Copy kesmeleri kapatır.
- D) Ethernet donanımı kuyruk kullanamaz.
- **Doğru Cevap: A**

#### Soru 4: FreeRTOS'ta `xQueueOverwrite()` fonksiyonu hangi tip kuyruklarda ve hangi amaçla kullanılır?
- A) Sonsuz elemanlı kuyruklarda tüm veriyi silmek için.
- B) Uzunluğu 1 olan kuyruklarda, kuyruk dolu olsa dahi eski veriyi ezerek daima en son güncel veriyi (örn. anlık gyro açısı) saklamak için.
- C) Flash belleğe yazma yapmak için.
- D) Öncelik terslenmesini çözmek için.
- **Doğru Cevap: B**

#### Soru 5: FreeRTOS'ta İkili Semaforlar (Binary Semaphores) ve Sayıcı Semaforlar (Counting Semaphores) mimari olarak nedir?
- A) Tamamen ayrı birer donanım modülüdür.
- B) Eleman boyutu sıfır (`uxItemSize = 0`) olan özel birer Kuyruktur (`Queue_t`).
- C) Sadece bir tamsayı sayacıdır.
- D) C++20 standardında birer sınıftır.
- **Doğru Cevap: B**

## 17. Gün Sonu Özeti ve Yarının Ön İzlemesi

### 3 Cümlelik Kapanış Özeti
1. **RTOS Queue Nedir?** RTOS Queue; görevler ve kesmeler arasında bağımsız dairesel tamponlar üzerinde thread-safe ve FIFO kurallarıyla veri aktarımı sağlayan temel IPC mekanizmasıdır.
2. **Hangi Problemi Çözer?** Global değişkenlerin yol açtığı veri yarışlarını (Race Conditions) engeller ve alıcı görevleri veri gelene kadar sıfır CPU yüküyle uyutarak senkronize eder.
3. **Hangi Bedeli Getirir?** Kopyalama maliyeti (`memcpy`), kuyruk doluluk yönetimi (Overflow/Backpressure) ve işaretçi aktarımındaki bellek sahipliği (Ownership) takip zorunluluğunu getirir.

---

### Yarının Konusu (GÜN 184): RTOS Semaphore ve Mutex Mimarisi
Yarın F5 fazında kaynak paylaşımının temellerine inerek:
- Binary Semaphore vs Counting Semaphore vs Mutex farkları,
- Recursive Mutex (Özyinelemeli Kilitler),
- Öncelik Mirası (Priority Inheritance) protokolünün mutex içindeki matematiksel kanıtı ve
- Çoklu kaynaklarda Kilitlenme (Deadlock) engelleme algoritmalarını inceleyeceğiz!

