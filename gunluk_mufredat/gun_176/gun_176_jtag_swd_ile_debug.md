# GÜN 176: JTAG/SWD ile Debug (ARM CoreSight ve Canlı Donanım İncelemesi)

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, tersine mühendislik yapılamaz.
```

---

## Modül Künyesi
- **Faz:** F5 — Gömülü Sistemler, RTOS ve STM32 Mimarisi
- **Konu:** JTAG/SWD ile Donanımsal Hata Ayıklama (Debug), ARM CoreSight Mimarisi, DAP (Debug Access Port), MEM-AP, Breakpoint/Watchpoint Mekanizmaları
- **Hedef Donanım:** ARM Cortex-M4/M7 (STM32F4/F7/H7 Serisi)
- **Kritik Kavramlar:** JTAG (IEEE 1149.1 - 4/5 Pin) vs SWD (2 Pin: SWDIO, SWCLK), CoreSight DAP, MEM-AP Bellek Otobanı, Donanımsal Breakpoint (FPB - Flash Patch and Breakpoint), DWT (Data Watchpoint and Trace), SWO/ITM Non-Intrusive Trace, Heisenbug Olgusu, HardFault Stack Frame Unwinding
- **Savunma Sanayii Senaryosu:** Kilitlenen Aviyonik Uçuş Kontrol Bilgisayarında CPU'yu Durdurmadan SWD MEM-AP Üzerinden Canlı Bellek Dökümü ve HardFault Kök Neden Analizi

## 1. Giriş ve Zihinsel Model (İğne ile Silisyuma Dokunmak)

Masaüstü yazılım geliştirmede hata ayıklamak lükstür: İşletim sistemi çöken programın yığınını saklar, `gdb` çekirdek dökümünü (`core dump`) diske yazar ve ekran çıktısıyla geliştiriciyi yönlendirir.

Gömülü sistemlerde ise bir mikrodenetleyici çöktüğünde ekran yoktur, işletim sistemi yoktur, disk yoktur. İşlemci sonsuz bir `HardFault_Handler` döngüsüne girer ve dış dünyaya hiçbir ses vermez.

İşte bu noktada devreye **JTAG ve SWD** girer. Bunlar yazılımsal bir kütüphane değil, mikrodenetleyicinin silisyumuna entegre edilmiş **donanımsal bir arka kapıdır (Hardware Backdoor)**!

```
+-----------------------------------------------------------------------------------+
|                        GELENEKSEL HATA AYIKLAMA (PRINTF ÇIKMAZI)                  |
|                                                                                   |
|  [Kod] ---> printf("Adim 1"); ---> [UART Tx FIFO] ---> (115200 Baud: ~86 us/bayt) |
|               |                                                                   |
|               v                                                                   |
|  * FELAKET: printf CPU'yu milisaniyelerce kilitler! Gerçek zamanlı motor/radar   |
|    zamanlamasını bozar! Hata debug açıkken kaybolur, sahada ortaya çıkar          |
|    (HEISENBUG FELAKETİ)!                                                          |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                        DONANIMSAL SWD / CORESIGHT HATA AYIKLAMA                   |
|                                                                                   |
|  [GDB / IDE] <== (ST-Link / J-Link) ==> [SWDIO + SWCLK]                           |
|                                                |                                  |
|                                                v                                  |
|                                  [ARM CoreSight DAP / MEM-AP]                     |
|                                                |                                  |
|                                                +---> CPU'yu Durdur (Halt)         |
|                                                +---> Register'ları Oku (R0-R15)   |
|                                                +---> SRAM'i Canlı Oku/Yaz         |
|                                                └---> FPB ile Breakpoint Yakala    |
|  * SONUÇ: Sıfır kod değişikliği, sıfır çevrim kaybı, doğrudan silisyum denetimi! |
+-----------------------------------------------------------------------------------+
```

### Zihinsel Analoji: "Arabanın Gösterge Paneli vs OBD-II Teşhis Soketi"
- **`printf` ile Debug:** Arabanın hızını ve motor arızasını anlamak için torpido gözüne cep telefonu kamerası koyup kadranın videosunu çekmeye benzer. Görüş kısıtlıdır, araba sarsıldıkça telefon kayar, tam arıza anını kaçırır.
- **JTAG / SWD:** Arabanın doğrudan motor beynine (ECU) takılan profesyonel **OBD-II teşhis cihazıdır**. Motorun silindir basıncını, enjektör püskürtme mikro-saniyesini ve arıza kodunu motor çalışırken doğrudan sensör veri yollarından okur.

## 2. Neden-Sonuç Zinciri ve Mimari Konumlandırma

Gömülü sistem mühendisliğinde JTAG/SWD'nin mimari konumlandırması ve gereklilik zinciri:

```
[Mikrodenetleyici Kilitlendi / HardFault Aldı]
         │
         ▼
[printf Çalışamaz] (Interruptlar kapalı, UART sürücüsü donmuş)
         │
         ▼
[Donanımsal Arka Kapı İhtiyacı: JTAG / SWD]
         │
         ├─► CPU'yu Tek Komutta Durdurur (Core Halt)
         ├─► Bus Matrix üzerinden SRAM ve Çevre Birimlerini Okur (MEM-AP)
         ├─► Flash Bellekte Donanımsal Karşılaştırıcı Eşleşmesi Yapar (FPB)
         └─► Bellek Adresi Değiştiğinde Kesme Noktası Tetikler (DWT Watchpoint)
         │
         ▼
[Kök Neden Tespiti: Hangi Kod Satırı, Hangi Bellek İhlali, Hangi Register?]
         │
         ▼
[Askeri Standartta Sıfır-Riskli Deterministik Hata Çözümü!]
```

## 3. JTAG (IEEE 1149.1) vs SWD (Serial Wire Debug) Fiziksel Katman Farkı

Mikrodenetleyicilerde hata ayıklama için iki temel fiziksel standart kullanılır:

### 1. JTAG (Joint Test Action Group — IEEE 1149.1):
Tarihsel olarak PCB üretim bantlarında lehim hatalarını ve açık/kısa devreleri test etmek (Boundary Scan) için tasarlanmıştır. Sonradan işlemci çekirdeklerine bağlanarak debug standardı olmuştur.
- **Pinler (4 veya 5 Pin):**
  - `TCK` (Test Clock): Saat sinyali.
  - `TMS` (Test Mode Select): TAP durum makinesini (State Machine) yönlendiren kontrol hattı.
  - `TDI` (Test Data In): Çipe seri veri girişi.
  - `TDO` (Test Data Out): Çipten seri veri çıkışı.
  - `nTRST` (Test Reset - Opsiyonel): TAP kontrolcüsünü resetler.
- **Dezavantajı:** Çok fazla pin tüketir! Küçük kılıflı mikrodenetleyicilerde (QFP32, QFN48) 5 pin harcamak GPIO kaynaklarını felç eder.

### 2. SWD (Serial Wire Debug — ARM Özgül Standardı):
ARM tarafından JTAG'in pin israfını ortadan kaldırmak için Cortex-M serisi ile tanıtılmış 2-telli seri protokoldür.
- **Pinler (Yalnızca 2 Pin!):**
  - `SWCLK` (Serial Wire Clock): Debug probundan işlemciye saat sinyali.
  - `SWDIO` (Serial Wire Data Input/Output): Çift yönlü (Bi-directional) tek telli seri veri hattı.
  - *(Opsiyonel 3. Pin)* `SWO` (Serial Wire Output): İşlemciden tek yönlü yüksek hızlı trace/log akışı (ITM).
- **Avantajı:** JTAG ile birebir aynı debug yeteneklerini **sadece 2 pin** ile sunar! Geri kalan tüm pinler aviyonik sensörlere ve bus hatlarına ayrılabilir.

## 4. ARM CoreSight Mimarisi: DAP, DP ve MEM-AP Otobanı

ARM Cortex-M işlemcilerinde debug altyapısı **CoreSight** olarak adlandırılır. CoreSight, CPU çekirdeğinden bağımsız yaşayan donanımsal bir çevre birimidir.

```
  +---------------------------------------------------------------------------------+
  |                          ARM CORESIGHT DAP MİMARİSİ                             |
  +---------------------------------------------------------------------------------+
  
  [ Debug Probe: ST-Link / J-Link ]
         │
         │ (SWDIO + SWCLK)
         ▼
  +---------------------------------------------------------------------------------+
  | Debug Access Port (DAP)                                                         |
  |                                                                                 |
  |   +--------------------------+                                                  |
  |   | Debug Port (DP)          | ---> SWD paketlerini çözer, ACK/NACK üretir.     |
  |   +--------------------------+                                                  |
  |                │                                                                |
  |                ▼                                                                |
  |   +--------------------------+                                                  |
  |   | Access Port (AP: MEM-AP) | ---> Veri Yolu Efendisi (Bus Master)!            |
  |   +--------------------------+                                                  |
  +---------------------------------------------------------------------------------+
                   │
                   ▼ (Doğrudan Multi-AHB Bus Matrix'e Bağlanır!)
  +---------------------------------------------------------------------------------+
  | Multi-AHB Bus Matrix                                                            |
  |   ├──> CPU Çekirdeği Durdurulabilir / İncelenebilir (Core Halt / Registers)    |
  |   ├──> Flash Bellek Doğrudan Okunabilir (Program Doğrulama)                    |
  |   ├──> SRAM1 / SRAM2 CANLI Okunabilir / Yazılabilir (CANLI DEĞİŞKEN İZLEME)    |
  |   └──> Çevre Birimleri (USART, SPI, TIM) Kontrol Edilebilir                     |
  +---------------------------------------------------------------------------------+
```

### Canlı Bellek İnceleme (Non-Intrusive Live Watch):
CoreSight `MEM-AP`, Bus Matrix üzerinde bağımsız bir Master'dır!
- Bu sayede CPU tam hızda uçuş kontrol algoritmasını koştururken, debug probu `MEM-AP` üzerinden CPU'yu **HİÇ DURDURMADAN (0 Çevrim Gecikmeyle)** SRAM'deki değişkenleri okuyup ekranda grafik olarak çizebilir!

```python
# -*- coding: utf-8 -*-
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
```

## 5. Kesme Noktaları: Hardware Breakpoint (FPB) vs Software `BKPT`

Gömülü yazılımda bir kod satırında durmak (Breakpoint) iki tamamen farklı mekanizmayla gerçekleştirilir:

### 1. Donanımsal Kesme Noktası (Hardware Breakpoint — FPB):
ARM Cortex-M çekirdeklerinde **Flash Patch and Breakpoint (FPB)** birimi bulunur.
- **Nasıl Çalışır?:** Flash bellekteki kod değiştirilmez! FPB içinde özel donanımsal adres karşılaştırıcılar (**Comparators**) vardır.
- Program Counter (`PC`), belirlenen Flash adresine (`0x08001234`) ulaştığı anda FPB donanımı işlemciye `BKPT` sinyali üretir ve çekirdeği durdurur (`Halt`).
- **Kısıtlama:** ARM Cortex-M4'te donanımsal olarak **sadece 6 adet (FPB_COMP0..5)** karşılaştırıcı bulunur! GDB'de 7. breakpoint'i koymaya çalışırsanız IDE *"No hardware breakpoints available"* hatası verir.

### 2. Yazılımsal Kesme Noktası (Software Breakpoint — `BKPT` Komutu):
- **Nasıl Çalışır?:** Debug probu hedef satırdaki makine kodunu okur, yerine `0xBE00` (ARM `BKPT 0` opcode'u) yazar!
- CPU bu adrese geldiğinde `BKPT` komutunu işler ve durur.
- **Ölümcül Kısıt:** `BKPT` komutunun belleğe yazılabilmesi için o bellek alanının **yazılabilir (RAM)** olması gerekir!
- Standart Flash belleğe doğrudan tek bir bayt yazılamaz (önce tüm Flash sektörünün silinmesi gerekir). Bu yüzden **Flash üzerindeki kodlarda yazılımsal breakpoint KULLANILAMAZ! Yalnızca FPB donanımsal breakpoint kullanılır!**

```python
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
```

## 6. DWT (Data Watchpoint and Trace) ve Bellek Nöbetçisi

Gömülü sistemlerin en zor bulunan hatası:
> *"Bir değişken durduk yere bozuluyor ama hangi kod satırının o değişkeni bozduğunu bulamıyorum!"*

İşte bu sorunu çözen donanım **DWT (Data Watchpoint and Trace)** birimidir.

```
  +---------------------------------------------------------------------------------+
  |                       DWT VERİ İZLEME VE NÖBETÇİ MEKANİZMASI                    |
  +---------------------------------------------------------------------------------+
  
  [ DWT_COMP0 (Adres Karşılaştırıcı) ] = 0x20000040 (Hedef Değişken Adresi)
  [ DWT_FUNCTION0 ]                    = DATAV_WRITE (Yalnızca Yazma Anında Tetikle)
  
  Senaryo:
  1. Kod satırları normal akışta çalışır.
  2. Bir fonksiyon (veya yığın taşması) 0x20000040 adresine yazmaya çalıştığı ANDA:
     - DWT donanımı Bus Matrix üzerinde bu adresi anında yakalar!
     - CPU'yu tam o yazma komutunda (STR) dondurur (Halt)!
     - GDB ekranında imleç doğrudan değişkeni bozan satırın üzerinde durur!
```

### DWT'nin Sunduğu Ek Özellikler:
- **`DWT_CYCCNT` (Cycle Counter):** 32-bit donanımsal saat çevrim sayacıdır. Bir fonksiyonun tam olarak kaç mikro-saniye sürdüğünü ölçmek için kullanılır (`DWT->CYCCNT`).
- **Veri Değeri Karşılaştırması:** Sadece adrese erişildiğinde değil, örneğin o adrese `0` yazıldığında durması da sağlanabilir.

```python
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
```

## 7. Gerçek Zamanlı İzleme (Trace): ITM, ETM, SWO ve SEGGER RTT

Klasik `printf` UART üzerinden veri basarken işlemciyi yüzlerce mikrosaniye kilitler. Gerçek zamanlı savunma sistemlerinde bu gecikmeyi sıfırlamak için 3 modern teknoloji kullanılır:

```
+-------------------+--------------------+------------------------+-------------------+
| Teknoloji         | Fiziksel Donanım   | CPU Gecikmesi (Overhead)| Kullanım Amacı    |
+-------------------+--------------------+------------------------+-------------------+
| UART printf       | TX Pini            | Aşırı Yüksek (~1 ms)   | Basit Terminal    |
| ITM / SWO         | SWO Pini (1 Tel)   | Çok Düşük (~1-2 Çevrim)| Donanımsal Trace  |
| ETM               | 4-Pin Trace Port   | SIFIR Çevrim (0 ns)    | Komut Düzeyi Trace|
| SEGGER RTT        | SWD (Mevcut 2 Tel) | İhmal Edilebilir (1 µs)| Yüksek Hızlı RAM  |
+-------------------+--------------------+------------------------+-------------------+
```

### 1. ITM (Instrumentation Trace Macrocell) & SWO:
- CPU `ITM->PORT[0].u8 = byte;` yazar. Bu işlem tek bir donanım çevrimidir!
- ITM donanımı veriyi arkadaki FIFO'ya atar ve tek telli `SWO` pininden paketler halinde basar. CPU hiçbir şekilde beklemez.

### 2. SEGGER RTT (Real-Time Transfer):
- En popüler endüstri standardıdır. Hiçbir ek pin (SWO dahil) gerektirmez!
- SRAM içinde dairesel bir tampon (`SEGGER_RTT_CB`) açılır.
- İşlemci log metnini doğrudan bu RAM tamponuna kopyalar (birkaç mikrosaniye).
- J-Link / ST-Link probu `MEM-AP` üzerinden CPU'dan habersiz bu RAM tamponunu sürekli okur ve ekrana basar. Sıfır donanım kısıtlaması, maksimum hız!

```python
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
```

## 8. Savunma Sanayii Aviyonik Senaryosu: HardFault Canlı Analizi

ASELSAN / ROKETSAN aviyonik uçuş kontrol bilgisayarında test uçuşu sırasında sistem aniden kilitlendi ve `HardFault_Handler` fonksiyonuna düştü.

```
                   TAKTIK UÇUŞ BİLGİSAYARI HARDFAULT ÇÖZÜMLEME
  +---------------------------------------------------------------------------------+
  | [Uçuş Kontrolcüsü (STM32H7 / Cortex-M7)]                                        |
  |   └──> Sonsuz Döngüde Kilitli: while(1) {}                                      |
  |                                                                                 |
  | [SWD Debug Probu (J-Link / ST-Link)]                                            |
  |   └──> Uçak Kapatılmadan SWD Portuna Takılır ve GDB Bağlanır                    |
  |                                                                                 |
  | 1. ADIM: Donanımsal Hata Yazmaçları Okunur (SCB Registers):                     |
  |   - CFSR  (Configurable Fault Status Register) -> Hatanın Sebebi (Bölme/İhlal) |
  |   - HFSR  (HardFault Status Register)          -> Zorlanmış Hata Durumu         |
  |   - MMFAR (MemManage Fault Address Register)   -> İhlal Edilen Bellek Adresi    |
  |                                                                                 |
  | 2. ADIM: Stack Frame (Yığın Çerçevesi) Çözümlenir (Hardware Auto-Stacking):     |
  |   - SP (Stack Pointer) bulunur (MSP mi PSP mi?).                                |
  |   - Donanımın stack'e ittiği 8 kayıt okunur:                                   |
  |     [R0, R1, R2, R3, R12, LR, PC, xPSR]                                        |
  |                                                                                 |
  | 3. ADIM: KÖK NEDEN TESPİTİ:                                                     |
  |   - PC (Program Counter) = 0x08004520 -> Hatanın koptuğu C++ kod satırı!        |
  |   - Hata Türü: PRECISERR (Veri Yolu Hatası) / DACCVIOL (Yetkisiz Bellek)        |
  +---------------------------------------------------------------------------------+
```

```python
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
```

## 9. Üretim Seviyesi C++20 SEGGER RTT / ITM Debug Log Şablonu

Savunma standartlarında gerçek zamanlı sistemlerde `printf` yerine kullanılan sıfır-maliyetli C++20 ITM / RTT sarmalayıcısı:

```cpp
// ============================================================================
// C++20 Non-Intrusive ITM / SWO Gerçek Zamanlı Log Mekanizması
// ============================================================================
#include <cstdint>
#include <string_view>
#include <concepts>

namespace defense::debug {

struct ItmPortRegs {
    volatile uint32_t PORT0;
};

class RealTimeLogger {
public:
    static constexpr uintptr_t ITM_BASE = 0xE0000000;
    static constexpr uint32_t ITM_TCR_ENABLE = (1U << 0);

    // ITM Port 0 üzerinden tek çevrimlik kartsız log iletimi
    static void log_char(char c) noexcept {
        // ITM ve Port 0 donanımsal olarak aktif mi kontrol et
        volatile uint32_t* itm_tcr = reinterpret_cast<volatile uint32_t*>(0xE0000E80);
        volatile uint32_t* itm_ter = reinterpret_cast<volatile uint32_t*>(0xE0000E00);

        if ((*itm_tcr & ITM_TCR_ENABLE) && (*itm_ter & 1U)) {
            volatile uint8_t* port0_u8 = reinterpret_cast<volatile uint8_t*>(ITM_BASE);
            // FIFO dolu değilse hemen yaz ve çık (Maksimum 1-2 saat çevrimi!)
            while (*reinterpret_cast<volatile uint32_t*>(ITM_BASE) == 0);
            *port0_u8 = static_cast<uint8_t>(c);
        }
    }

    static void log_string(std::string_view msg) noexcept {
        for (char ch : msg) {
            log_char(ch);
        }
    }
};

} // namespace defense::debug
```

## 10. Bilerek Bozduğumuz Şey (SWD Pinlerini Yanlışlıkla GPIO Yapma)

### Sabotaj: `PA13` ve `PA14` Pinlerini Yanlışlıkla Genel GPIO Olarak Yapılandırmak
Mikrodenetleyici dünyasının en meşhur "Çipi Tuğlaya Dönüştürme" (Bricking the MCU) hatasıdır!

- **Hata:**
  STM32'de `PA13` pini **`SWDIO`**, `PA14` pini ise **`SWCLK`**'tır.
  Yazılımcı GPIO başlatma kodunda şu hatayı yapar:
  ```c
  // FELAKET KOD: Port A'nın tüm pinlerini çıkış yap!
  GPIOA->MODER |= 0x55555555; // PA13 ve PA14 de genel çıkış (General Output) oldu!
  ```
- **Ne Olur?:**
  İşlemci açılır açılmaz bu kod çalışır. `PA13` ve `PA14` donanımsal SWD işlevinden çıkar, sıradan birer GPIO LED pinine dönüşür!
- **Sonuç:**
  Debug probu (ST-Link / J-Link) artık işlemciye bağlanamaz! IDE *"Cannot connect to target"* hatası verir. Çip kilitlenmiştir.
- **Saha Çözümü (Under-Reset Connect):**
  1. Donanımsal `NRST` (Reset) butonuna basılı tutulur.
  2. GDB / OpenOCD başlatılır (`connect under reset` modu seçilir).
  3. Çip resetten çıkmadan önce prob donanımı durdurur (`Halt`) ve Flash belleği tamamen siler (`Mass Erase`).

## 11. Karşılaştırma Matrisi: Hata Ayıklama (Debug) Teknolojileri

| Kriter | UART printf() | JTAG (IEEE 1149.1) | SWD (Serial Wire Debug) | SEGGER RTT |
| :--- | :--- | :--- | :--- | :--- |
| **Gerekli Pin Sayısı** | 1 Pin (Tx) | **4 - 5 Pin** | **2 Pin (SWDIO, SWCLK)** | **2 Pin (Mevcut SWD)** |
| **CPU İntrusiveness** | Aşırı Yüksek (~1 ms) | Sıfır (CoreSight) | **Sıfır (CoreSight)** | **İhmal Edilebilir (~1 µs)**|
| **Canlı Bellek Okuma** | İmkansız | Var (MEM-AP) | **Var (MEM-AP)** | **Var (Çift Yönlü RAM)** |
| **Donanımsal Breakpoint**| Yok | Var (FPB) | **Var (FPB)** | N/A (Loglama) |
| **Heisenbug Riski** | %100 Yüksek Risk | Sıfır | **Sıfır** | **Çok Düşük** |
| **Aviyonik Uygunluğu** | Yasak (Uçuşta) | Standart | **Modern Standart** | **Altın Standart** |

## 12. Donanım Araçları: ST-Link vs J-Link vs Black Magic Probe

Savunma laboratuvarlarında kullanılan debug donanımları:

```
  +-------------------------------------------------------------------------------+
  |                 SAVUNMA SANAYİİ DONANIMSAL DEBUG PROBLARI                     |
  +-------------------------------------------------------------------------------+
  
  [ ST-Link V2 / V3 ] (STMicroelectronics)
    ├── Avantajı : Çok ucuz, Discovery ve Nucleo kartlarına gömülü gelir.
    ├── Hızı     : 4 MHz - 10 MHz SWCLK hızı.
    └── Kısıtı   : Sadece STM32 mikrodenetleyicilerini tam destekler.
  
  [ SEGGER J-Link BASE / ULTRA+ / PRO ] (Endüstri Altın Standardı)
    ├── Avantajı : Tüm ARM çekirdeklerini destekler, 50 MHz SWCLK hızı, RTT desteği.
    ├── Özelliği : Sonsuz yazılımsal breakpoint (FlashDL), ultra hızlı Flash yazma.
    └── Tercih   : Askeri aviyonik laboratuvarlarının vazgeçilmez donanımıdır.
  
  [ Black Magic Probe (BMP) ]
    ├── Avantajı : Açık kaynak, içinde gömülü GDB Server barındırır (OpenOCD gereksiz!).
    └── Tercih   : Bağımsız test ve CI/CD otomatik test tezgâhlarında kullanılır.
```

## 13. Mülakat ve Saha Tuzakları (Top 5 Gotchas)

1. **"Flash üzerinde neden sınırsız breakpoint koyamıyoruz?" Mülakat Sorusu:**
   - **Doğru Cevap:** *"Çünkü Flash bellek salt okunurdur; kodun içine dinamik `BKPT` opcode'u yazılamaz. Cortex-M4'te sadece 6 adet donanımsal karşılaştırıcıya sahip FPB (Flash Patch and Breakpoint) birimi vardır; bu yüzden en fazla 6 donanımsal kesme noktası konabilir."*
2. **PA13/PA14 Pinlerini GPIO Olarak Kullanıp Çipi Kilitlemek:**
   - SWD pinleri asla sıradan GPIO yapılmamalıdır.
3. **Debug Sırasında Watchdog'un İşlemciyi Resetlemesi:**
   - İşlemci breakpoint'te durduğunda Watchdog sayacı saymaya devam ederse çip resetlenir. `DBGMCU_APB1_FZ` yazmacından `DBG_IWDG_STOP` biti aktif edilerek CPU durduğunda Watchdog'un da dondurulması sağlanmalıdır!
4. **Heisenbug (printf ile arızayı yok etmek):**
   - Zamanlama yarışlarını debug etmek için asla `printf` kullanılmamalı, DWT ve RTT tercih edilmelidir.
5. **DWT Watchpoint'in Stack Taşmasında Hayat Kurtarması:**
   - Stack alanının en sonundaki 4 bayta DWT write watchpoint koyarak yığın taşması (Stack Overflow) anında CPU'yu durdurabilirsiniz.

## 14. 5N1K Özeti

- **Ne?:** JTAG (4/5 telli endüstri standardı) ve SWD (2 telli ARM standardı), mikrodenetleyici donanımına doğrudan müdahale eden hata ayıklama ve bellek izleme arayüzleridir.
- **Neden?:** Ekranı ve işletim sistemi olmayan gömülü sistemlerde CPU'yu durdurmak, kayıtları incelemek ve çöken sistemlerin kök nedenini belirlemek için.
- **Nasıl?:** ARM CoreSight DAP (Debug Access Port) ve MEM-AP üzerinden Bus Matrix'e bağlanarak işlemci çevrimini çalmadan belleği okuyarak.
- **Nerede?:** Taktik füze kontrol kartlarında, radar sinyal işleme işlemcilerinde, aviyonik uçuş bilgisayarlarında.
- **Ne Zaman?:** Donanım geliştirme, kart ayağa kaldırma (bring-up) ve HardFault arıza analizlerinde.
- **Kim?:** Aviyonik gömülü yazılım mühendisleri, sistem doğrulama ekipleri.

## 15. Gün Sonu Özeti ve Yetkinlik Kontrolü

### 3 Cümlelik Özet:
1. **JTAG/SWD Nedir?:** İşlemci silisyumuna entegre CoreSight DAP donanımı üzerinden bellek ve yazmaçlara sıfır kod yüküyle doğrudan erişen hata ayıklama standardıdır.
2. **Hangi Problemi Çözer?:** `printf` gibi gerçek zamanlı zamanlamayı bozan (Heisenbug) hantal metotlar yerine, CPU'yu durdurmadan canlı bellek izleme ve anlık breakpoint imkanı sunar.
3. **Getirdiği Risk / Trade-off:** SWD pinlerinin kazara GPIO yapılması çipi erişilemez kılar ve donanımsal breakpoint sayısı (Cortex-M'de 6 adet) ile sınırlıdır.

### Yetkinlik Kontrol Listesi:
- [x] JTAG ile SWD arasındaki pin farkını ve paket protokolünü biliyorum.
- [x] ARM CoreSight DAP, DP ve MEM-AP mimarisini açıklayabiliyorum.
- [x] Hardware Breakpoint (FPB) ile Software Breakpoint farkını ve Flash kısıtını anladım.
- [x] DWT Data Watchpoint ile hafıza bozan fonksiyonu nasıl yakalayacağımı biliyorum.
- [x] Heisenbug olgusunu ve RTT / ITM trace yöntemlerini kavradım.
- [x] Kilitlenen bir uçuş bilgisayarında CFSR ve Stack Frame üzerinden HardFault analizi yapabiliyorum.

## 16. İleri Okuma ve Kaynaklar

1. **ARM CoreSight Architecture Specification (v3.0):** *DAP, MEM-AP and Debug Port Protocol Manual.*
2. **Joseph Yiu:** *The Definitive Guide to ARM Cortex-M3 and Cortex-M4 Processors (Chapter 15: Debugging Architecture).*
3. **SEGGER Microcontroller:** *Real Time Transfer (RTT) Technical Description and Benchmark Whitepaper.*
4. **STMicroelectronics Application Note (AN3155):** *USART protocol used in the STM32 bootloader and SWD activation.*

## 17. 24-Hücreli Master Mimari Onay Beyanı

Bu eğitim modülü, ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ standartlarında C++20 ve STM32 Gömülü Sistemler Müfredatı kapsamında hazırlanmıştır.

```
+-----------------------------------------------------------------------------------+
|               GÜN 176 MASTER MİMARİ MÜHENDİSLİK DOĞRULAMA RAPORU                  |
+-----------------------------------------------------------------------------------+
| 1. Toplam Hücre Sayısı        : 24 Hücre (18 Markdown, 6 Python Kodu)             |
| 2. Fiziksel Katman Modelleri  : JTAG (5 Pin TAP) vs SWD (2 Pin SWDIO/SWCLK)       |
| 3. CoreSight Donanım Simülasyonu: MEM-AP Live Watch & Canlı Değişken Enjeksiyonu  |
| 4. Kesme Noktası Mimarisi     : FPB (Max 6 Donanımsal) vs DWT Watchpoint          |
| 5. Aviyonik Senaryosu         : Uçuş Bilgisayarı HardFault Unwinder & CFSR Analiz  |
| 6. Görsel Artefact            : 300 DPI 4-Panelli Koyu Tema Dashboard (.PNG)      |
| 7. Özel Lisans                : Telif Hakkı (c) 2026 Seydi Eryılmaz               |
+-----------------------------------------------------------------------------------+
```

```python
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
```
