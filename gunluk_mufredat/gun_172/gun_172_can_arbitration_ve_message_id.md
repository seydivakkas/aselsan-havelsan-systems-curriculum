# GÜN 172: CAN Bus — Diferansiyel İletim, Kayıpsız Tahkim (Arbitration) ve Message ID Hiyerarşisi

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır. Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz.
```

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
![C++20](https://img.shields.io/badge/Standard-C%2B%2B20-blue.svg?style=flat-square)
![STM32](https://img.shields.io/badge/Hardware-STM32%20bxCAN%20Peripheral-orange.svg?style=flat-square)
![Protocol](https://img.shields.io/badge/Protocol-CAN%202.0A%2FB%20ISO%2011898-green.svg?style=flat-square)
![Defense Grade](https://img.shields.io/badge/Domain-Armored%20Vehicle%20%2F%20Missile%20Actuator-red.svg?style=flat-square)

---

## 1. Zihinsel Model ve Mimari Büyük Resim (CAN Bus Nedir?)

Modern savunma sanayii sistemlerinde (ASELSAN KORKUT hava savunma tareti, ROKETSAN füze kanatçık tahrik sistemleri, FNSS zırhlı muharebe araçları) onlarca bağımsız elektronik kontrol ünitesi (ECU) aşırı gürültülü ve titreşimli bir ortamda haberleşmek zorundadır.

Bu ortamda UART (noktadan noktaya kısıtı), SPI (kısa mesafe ve pin çokluğu) veya I2C (zayıf gürültü bağışıklığı) kullanılamaz. Bosch tarafından 1986'da geliştirilen ve ISO 11898 standardı haline gelen **CAN (Controller Area Network)**, dünyanın en sağlam ve güvenilir endüstriyel/askeri veri yoludur.

### CAN Bus'ın 4 Temel Mimari Sütunu:
1. **Çoklu Master (Multi-Master):** Ağda merkezi bir master yoktur; her düğüm hat boş olduğu anda mesaj gönderebilir.
2. **Kayıpsız Bit Düzeyinde Tahkim (Non-Destructive Bitwise Arbitration):** İki düğüm aynı anda iletime başlarsa, önceliği yüksek olan düğüm tek bir bit bile kaybetmeden aktarıma devam eder; düşük öncelikli düğüm sessizce çekilir.
3. **Mesaj Tabanlı Adresleme (Content-Based Addressing):** Mesajlar belirli bir cihaza gönderilmez; her mesajın bir **Message ID**'si vardır (örneğin ID `0x010` = Acil Durdurma). İlgilenen tüm düğümler bu mesajı dinler.
4. **Donanımsal Hata Hapsedilmesi (Fault Confinement):** Kendi kendine arızalanan veya sürekli hatta saçmalayan bir düğüm, donanım tarafından otomatik olarak hattan koparılır (**Bus-Off**), böylece diğer sistemlerin çökmesi engellenir!

## 2. Fiziksel Katman: Diferansiyel Sinyalleşme ve Dominant/Recessive

CAN veri yolu iki bükümlü kablo (Twisted Pair) üzerinden diferansiyel voltaj farkıyla çalışır: **CAN_H (CAN High)** ve **CAN_L (CAN Low)**.

### Sonlandırma Dirençleri ($120\ \Omega$):
Hattın en uçtaki iki noktasına $120\ \Omega$ direnç takılır. Bu dirençler hattın empedansını dengeler (toplam paralel empedans $60\ \Omega$) ve yüksek hızlı sinyal yansımalarını (Signal Reflection) tamamen yok eder.

### Lojik Seviyeler: Baskın (Dominant) vs Çekinik (Recessive)
CAN bus'ta "1" ve "0" yerine özel iki durum kullanılır:

```
+-----------------------------------------------------------------------------------+
|               CAN DİFERANSİYEL SİNYAL SEVİYELERİ (ISO 11898 STANDARD)             |
+-----------------------------------------------------------------------------------+

   Voltaj (V)
     3.5V  +---------------- CAN_H = 3.5V ---------------+
           |                                             |
     2.5V  +====== CAN_H = CAN_L = 2.5V (ÇEKİNİK) ======+===== CAN_H = CAN_L = 2.5V
           |                                             |
     1.5V  +---------------- CAN_L = 1.5V ---------------+
           |                                             |
      0V   +---------------------------------------------+------------------------
           <----------- BASKIN (DOMINANT = 0) -----------> <--- ÇEKİNİK (1) ----->
           Vdiff = 3.5V - 1.5V = 2.0V                     Vdiff = 2.5V - 2.5V = 0.0V
```

1. **Baskın Durum (Dominant = Lojik 0):**
   - Transceiver transistörleri aktif olarak açılır: $\text{CAN\_H} \approx 3.5\ \text{V}$, $\text{CAN\_L} \approx 1.5\ \text{V}$.
   - Diferansiyel voltaj farkı: $V_{\text{diff}} = 3.5\ \text{V} - 1.5\ \text{V} = \mathbf{2.0\ \text{V}}$.
2. **Çekinik Durum (Recessive = Lojik 1):**
   - Transceiver transistörleri kapanır (High-Z). Sonlandırma dirençleri hattı dengeler: $\text{CAN\_H} \approx \text{CAN\_L} \approx \mathbf{2.5\ \text{V}}$.
   - Diferansiyel voltaj farkı: $V_{\text{diff}} = 2.5\ \text{V} - 2.5\ \text{V} = \mathbf{0.0\ \text{V}}$.

### Kablolu-VE (Wired-AND) Çarpışma Mekanizması:
- Eğer Düğüm A hatta **Çekinik (1)** basarken, Düğüm B aynı anda **Baskın (0)** basarsa; hat fiziksel olarak **Baskın ($V_{\text{diff}} = 2.0\ \text{V}$)** seviyesine geçer!
- **Baskın bit (0), çekinik biti (1) daima ezer!** Bu kural tahkim algoritmasının temel taşıdır.

## 3. Kayıpsız Bit Düzeyinde Tahkim (Non-Destructive Bitwise Arbitration)

Ethernet gibi ağlarda iki cihaz aynı anda iletime başladığında çarpışma (Collision) oluşur; her iki cihaz da iletimi durdurup rastgele bir süre bekler (Backoff). Bu durum aviyonik sistemlerde asla kabul edilemez (Determinizm yok olur)!

CAN bus ise **Kayıpsız Hakemlik (Non-Destructive Bitwise Arbitration)** mekanizması kullanır.

### Tahkim Algoritması Nasıl Çalışır?:
1. İletime başlamak isteyen tüm düğümler hattın boşta (IDLE = Çekinik) olmasını bekler.
2. Hat boşaldığı anda düğümler senkronize olarak bir **SOF (Start of Frame = 0)** biti basar ve ardından **Message ID**'lerini en önemli bitten (MSB) başlayarak bit bit hatta sürmeye başlar.
3. **Kritik Kural:** Her düğüm bir bit basarken, aynı anda hattın fiziksel seviyesini geri okur (Loopback / Listen).
4. Eğer bir düğüm hatta **Çekinik (1)** basmışsa, fakat hattan **Baskın (0)** okumuşsa:
   - Düğüm der ki: *"Hatta benden daha yüksek öncelikli bir düğüm var!"*
   - O düğüm bir sonraki saat darbesinde **derhal verici modundan çıkar ve dinleyici (Receiver) moduna geçer!**
5. Kazanan yüksek öncelikli düğüm ise hattan kendi bastığı biti (0) okumaya devam ettiği için yarışın farkında bile olmadan iletimini kesintisiz tamamlar!

```
+-----------------------------------------------------------------------------------+
|                     CAN TAHKİM YARIŞI (ARBITRATION RACE) ÖRNEĞİ                    |
+-----------------------------------------------------------------------------------+

   Bit Adımı :   Bit 10    Bit 9     Bit 8     Bit 7     Bit 6     Sonuç
   -------------------------------------------------------------------------
   Düğüm 1   :     0         1         0         0         1       (ID: 0x240 - Öncelikli)
   Düğüm 2   :     0         1         0         1 (1 bastı, 0 gördü -> ÇEKİLDİ!)
   
   HAT (Bus) :     0         1         0         0 (Düğüm 1 kazandı, devam ediyor!)
```

> **Altın Kural:** Sayısal değeri daha KÜÇÜK olan Message ID, ikili sistemde daha solda '0' (Baskın) bitine sahip olduğu için **DAİMA DAHA YÜKSEK ÖNCELİĞE SAHİPTİR!**
> Örn: ID `0x010` (Acil Durdurma) > ID `0x150` (Aktüatör Pozisyonu) > ID `0x380` (Sıcaklık).

## 4. CAN 2.0A ve 2.0B Çerçeve Anatomisi: 11-bit vs 29-bit ID

CAN protokolünde iki standart çerçeve tipi bulunur:
1. **Standart Format (CAN 2.0A):** 11-bit Identifier ($2^{11} = 2048$ farklı mesaj tipi).
2. **Genişletilmiş Format (CAN 2.0B):** 29-bit Identifier ($2^{29} \approx 536\ \text{milyon}$ farklı mesaj, askeri MIL-CAN ve J1939 standartlarında kullanılır).

```
+-----------------------------------------------------------------------------------+
|                      STANDART CAN 2.0A VERİ ÇERÇEVESİ (DATA FRAME)                |
+-----------------------------------------------------------------------------------+

  [SOF] [IDENTIFIER] [RTR] [IDE] [r0] [DLC]   [DATA FIELD]   [CRC] [CRCD] [ACK] [ACKD] [EOF] [IFS]
  1-bit    11-bit    1-bit 1-bit 1-bit 4-bit   0..8 Bayt     15-bit 1-bit 1-bit 1-bit  7-bit 3-bit
  (0)    (Mesaj ID)   (0)   (0)   (0)  (0..8) (Veri Alanı)  (Denetim)(1)  (0/1) (1)    (1..1)(1..1)
```

### Alanların Görevleri:
- **SOF (Start of Frame):** 1 bit baskın (0). Tüm düğümleri senkronize eder.
- **Identifier (11-bit):** Mesajın kimliği ve önceliği.
- **RTR (Remote Transmission Request):** $0 \implies \text{Data Frame}$ (Veri taşıyor), $1 \implies \text{Remote Frame}$ (Başka bir düğümden veri talep ediyor).
- **IDE (Identifier Extension):** $0 \implies \text{Standart 11-bit}$, $1 \implies \text{Genişletilmiş 29-bit}$.
- **DLC (Data Length Code):** 4 bit. Veri alanında kaç bayt olduğunu belirtir ($0 - 8\ \text{bayt}$).
- **DATA:** $0$ ila $8$ baytlık asıl yük (Payload). CAN FD'de 64 bayta kadar çıkabilir.
- **CRC (15-bit):** Donanımsal hata denetim kodu.
- **ACK Slot (1-bit):** Verici bu biti çekinik (1) basar. Paketi hatasız alan tüm dinleyici düğümler bu anda hatta **Baskın (0)** basarak vericiye *"Paketi aldık!"* der.
- **EOF (End of Frame):** 7 adet çekinik (1) bit ile çerçevenin sonu belirtilir.

```python
# -*- coding: utf-8 -*-
"""
GÜN 172: Kod Bloğu 1 — CAN Bit Düzeyinde Kayıpsız Tahkim (Arbitration) Simülatörü
Aynı Anda İletime Başlayan 3 Düğümün Yarışı ve Öncelikli Düğümün Kesintisiz Kazanması
"""

from typing import List, Dict, Tuple

class CANNode:
    """CAN Bus Düğüm Simülasyonu"""
    def __init__(self, name: str, message_id_11bit: int, data_bytes: List[int]):
        assert 0 <= message_id_11bit <= 0x7FF, "ID 11-bit olmalıdır!"
        self.name = name
        self.message_id = message_id_11bit
        self.data_bytes = data_bytes
        self.is_transmitting = True
        self.lost_arbitration_at_bit = None

        # 11-bit ID ikili listesi (MSB first)
        self.id_bits = [(message_id_11bit >> (10 - i)) & 1 for i in range(11)]

    def get_id_bit(self, bit_index: int) -> int:
        return self.id_bits[bit_index]

class CANBusArbitrationEngine:
    """CAN Bus Hakemlik ve Hat Seviyesi Simülatörü"""
    def __init__(self, nodes: List[CANNode]):
        self.nodes = nodes

    def run_arbitration(self) -> Dict[str, any]:
        arbitration_log = []
        active_nodes = list(self.nodes)

        # 11-bit ID boyunca yarış
        for bit_idx in range(11):
            # 1. Aktif tüm düğümler bitlerini basar
            driven_bits = {node.name: node.get_id_bit(bit_idx) for node in active_nodes}

            # 2. Hat seviyesi belirlenir: Herhangi biri '0' (Dominant) basarsa hat '0' olur!
            bus_level = 0 if any(b == 0 for b in driven_bits.values()) else 1

            # 3. Her düğüm hattı geri okur. Çekinik (1) basıp hatta Baskın (0) gören elenir!
            survivors = []
            eliminated_this_round = []

            for node in active_nodes:
                my_bit = driven_bits[node.name]
                if my_bit == 1 and bus_level == 0:
                    # Tahkim kaybedildi!
                    node.is_transmitting = False
                    node.lost_arbitration_at_bit = bit_idx
                    eliminated_this_round.append(node.name)
                else:
                    survivors.append(node)

            arbitration_log.append({
                "bit_step": bit_idx,
                "driven_bits": driven_bits,
                "bus_level": bus_level,
                "eliminated": eliminated_this_round,
                "active_count": len(survivors)
            })

            active_nodes = survivors
            if len(active_nodes) == 1:
                # Kazanan kesinleşti
                pass

        winner = active_nodes[0] if len(active_nodes) == 1 else None
        return {
            "winner_node": winner.name if winner else None,
            "winner_id": hex(winner.message_id) if winner else None,
            "log": arbitration_log
        }

# Simülasyon: 3 Taktik Düğüm Aynı Anda Hatta Giriyor
# Düğüm 1: Acil Görev İptal (ID: 0x010 = 0b00000010000) -> En Yüksek Öncelik
# Düğüm 2: Kanatçık Motoru   (ID: 0x150 = 0b00101010000) -> Orta Öncelik
# Düğüm 3: Batarya Telemetri (ID: 0x380 = 0b01110000000) -> Düşük Öncelik
node1 = CANNode("E_STOP_ABORT", 0x010, [0xFF])
node2 = CANNode("FIN_ACTUATOR", 0x150, [0x12, 0x34])
node3 = CANNode("BATTERY_TELEMETRY", 0x380, [0x0B, 0x50])

engine = CANBusArbitrationEngine([node1, node2, node3])
result = engine.run_arbitration()

print("[*] CAN Bus Kayıpsız Tahkim (Arbitration) Simülasyonu:")
print(f"  [+] Yarışan Düğümler: E_STOP (0x010), FIN_ACT (0x150), BATT (0x380)")
print(f"  [+] Tahkimi Kazanan : {result['winner_node']} (ID: {result['winner_id']})")

print("\n[*] Adım Adım Tahkim Günlüğü:")
print(f"{'Bit':>4} | {'E_STOP (0x010)':>15} | {'FIN (0x150)':>12} | {'BATT (0x380)':>12} | {'Bus Hat':>8} | {'Elenen'}")
print("-" * 75)
for step in result["log"]:
    bits = step["driven_bits"]
    elim_str = ", ".join(step["eliminated"]) if step["eliminated"] else "-"
    print(f"{step['bit_step']:>4} | {bits.get('E_STOP_ABORT', '-'):>15} | {bits.get('FIN_ACTUATOR', '-'):>12} | {bits.get('BATTERY_TELEMETRY', '-'):>12} | {step['bus_level']:>8} | {elim_str}")

# Doğrulama Assertions
assert result["winner_node"] == "E_STOP_ABORT", "En düşük sayısal ID (0x010) kazanmalıydı!"
assert node3.lost_arbitration_at_bit == 1, "0x380 1. bitte (0b011..) elenmeliydi!"
assert node2.lost_arbitration_at_bit == 2, "0x150 2. bitte (0b001..) elenmeliydi!"
print("\n[HÜCRE 6] CAN kayıpsız tahkim ve öncelik çözümleme motoru başarıyla doğrulandı.")
```

## 5. Bit Doldurma (Bit Stuffing) Kuralı ve Saat Senkronizasyonu

CAN bus asenkron bir hiyerarşi gibi harici clock hattı taşımaz. Alıcılar saatlerini hattaki sinyal kenarlarından (0'dan 1'e veya 1'den 0'a geçişlerden) senkronize tutar (Resynchronization).

### Uzun Süre Değişmeyen Bitler Sorunu:
Eğer gönderilen veride ardışık olarak onlarca adet `0` veya `1` varsa, hatta hiç voltaj geçişi olmaz. Alıcıların saat osilatörleri zamanla kayar ve senkronizasyon kopar.

### Bit Doldurma (Bit Stuffing) Çözümü:
CAN protokol standardı (ISO 11898) donanımsal bir kural koyar:
- Verici, SOF'tan CRC alanının sonuna kadar olan bölgede **ardışık 5 adet aynı seviyede bit (00000 veya 11111)** gönderirse:
- Donanım hemen araya otomatik olarak **1 adet ters seviyede bit (Stuff Bit)** ekler!
  - 5 adet `0` geldiyse araya zorla `1` eklenir: `00000` $\to$ `00000`**1**
  - 5 adet `1` geldiyse araya zorla `0` eklenir: `11111` $\to$ `11111`**0**
- Alıcı donanım bu kuralı bilir; 5 ardışık aynı bitten sonra gelen 6. zıt biti otomatik olarak hattan siler (**Destuffing**) ve veriyi orijinal haline getirir.

### Stuff Error (Doldurma Hatası):
Eğer alıcı hatta ardışık **6 adet aynı seviyede bit** görürse, protokol kuralı ihlal edilmiş demektir!
- Alıcı bunu bir fiziksel hat veya parazit kabul eder ve derhal bir **Aktif Hata Çerçevesi (Active Error Frame - 6 dominant bit)** basarak tüm ağı uyarır ve paketi imha eder!

```python
# -*- coding: utf-8 -*-
"""
GÜN 172: Kod Bloğu 2 — CAN Bit Stuffing (Doldurma) Kodlayıcı, Çözücü ve Hata Sezici
5 Ardışık Aynı Bitten Sonra Ters Bit Enjeksiyonu, Destuffing ve Stuff Error Tespiti
"""

from typing import List, Dict, Tuple

class CANBitStuffer:
    """CAN Donanımsal Bit Stuffing ve Destuffing Motoru"""

    @staticmethod
    def apply_bit_stuffing(raw_bits: List[int]) -> Tuple[List[int], List[int]]:
        """
        Ham bit akışına 5 ardışık kuralını uygular.
        Dönüş: (stuffed_stream, stuffed_indices)
        """
        stuffed = []
        stuffed_indices = []
        consecutive = 0
        last_bit = None

        for bit in raw_bits:
            if bit == last_bit:
                consecutive += 1
            else:
                consecutive = 1
                last_bit = bit

            stuffed.append(bit)

            # 5 ardışık aynı bit olduysa ters bit ekle!
            if consecutive == 5:
                stuff_bit = 1 if bit == 0 else 0
                stuffed_indices.append(len(stuffed))
                stuffed.append(stuff_bit)
                # Yeni eklenen bit için sayacı sıfırla
                last_bit = stuff_bit
                consecutive = 1

        return stuffed, stuffed_indices

    @staticmethod
    def remove_bit_stuffing(stuffed_bits: List[int]) -> Dict[str, any]:
        """Doldurulmuş bit akışından ters bitleri temizler ve 6 ardışık hata denetimi yapar"""
        destuffed = []
        consecutive = 0
        last_bit = None
        idx = 0
        n = len(stuffed_bits)

        while idx < n:
            bit = stuffed_bits[idx]

            if bit == last_bit:
                consecutive += 1
            else:
                consecutive = 1
                last_bit = bit

            destuffed.append(bit)

            # 6 ardışık kontrolü (Stuff Error!)
            if consecutive >= 6:
                return {
                    "valid": False,
                    "error": "STUFF_ERROR",
                    "failed_at_index": idx,
                    "destuffed_bits": destuffed
                }

            # 5 ardışık olduysa bir sonraki bit doldurma bitidir, atla!
            if consecutive == 5:
                idx += 1
                if idx < n:
                    # Bir sonraki bit ters olmalıdır
                    expected_stuff = 1 if bit == 0 else 0
                    actual_stuff = stuffed_bits[idx]
                    if actual_stuff != expected_stuff:
                        return {"valid": False, "error": "STUFF_ERROR", "failed_at_index": idx}
                    # Stuff bit atlandı, sayaç sıfırlandı
                    last_bit = None
                    consecutive = 0

            idx += 1

        return {"valid": True, "error": None, "destuffed_bits": destuffed}

# Test 1: Normal Bit Stuffing Testi
# 7 adet ardışık '0' içeren veri akışı: [0, 0, 0, 0, 0, 0, 0, 1]
test_payload = [0, 0, 0, 0, 0, 0, 0, 1]
stuffed_stream, stuff_pts = CANBitStuffer.apply_bit_stuffing(test_payload)
destuff_res = CANBitStuffer.remove_bit_stuffing(stuffed_stream)

print("[*] CAN Bit Stuffing (Doldurma) Doğrulama Testi:")
print(f"  [+] Orijinal Bitler ({len(test_payload)} bit) : {test_payload}")
print(f"  [+] Doldurulmuş Akış ({len(stuffed_stream)} bit) : {stuffed_stream}")
print(f"  [+] Enjekte Edilen Noktalar     : {stuff_pts} (5 sıfırdan sonra '1' girdi)")
print(f"  [+] Geri Çözülen Bitler         : {destuff_res['destuffed_bits']}")

# Test 2: Kasıtlı Stuff Error (Hatta 6 adet ardışık '1' enjeksiyonu)
corrupted_stream = [1, 1, 1, 1, 1, 1, 0, 0]
err_res = CANBitStuffer.remove_bit_stuffing(corrupted_stream)
print(f"  [!] Kasıtlı 6-Ardışık Hata Testi : {err_res['error']} (İndeks: {err_res['failed_at_index']})")

assert destuff_res["valid"] is True and destuff_res["destuffed_bits"] == test_payload
assert stuff_pts == [5], "5. indekse stuff biti eklenmeliydi!"
assert err_res["error"] == "STUFF_ERROR", "6 ardışık bit STUFF_ERROR üretmeliydi!"
print("\n[HÜCRE 8] CAN bit stuffing ve destuffing motoru başarıyla onaylandı.")
```

## 6. Hata Durum Makinesi ve İzolasyon: TEC, REC ve Bus-Off

CAN protokolünü savunma sanayiinde vazgeçilmez kılan en büyük özellik **Hata Hapsedilmesidir (Fault Confinement)**. Her CAN kontrolcüsü içinde iki bağımsız donanımsal hata sayacı çalışır:
- **TEC (Transmit Error Counter):** Verici iken karşılaşılan hataların sayacı.
- **REC (Receive Error Counter):** Alıcı iken karşılaşılan hataların sayacı.

### Sayaç Kuralları (Asimetrik Cezalandırma):
- Hata olduğunda: Sayaç sert bir şekilde **$+8$ artırılır**.
- Başarılı aktarımda: Sayaç yavaşça **$-1$ azaltılır**.
Bu asimetri, sürekli hata üreten arızalı düğümün hızla tespit edilmesini sağlar.

```
+-----------------------------------------------------------------------------------+
|                     CAN HATA DURUM MAKİNESİ (FAULT CONFINEMENT)                   |
+-----------------------------------------------------------------------------------+

   +-------------------------------------------------------------+
   |  ERROR ACTIVE (Normal Durum)                                |
   |  (TEC <= 127 ve REC <= 127)                                 |
   |  Hata sezdiğinde 6 DOMINANT bit ile tüm ağı uyarır!        |
   +-------------------------------------------------------------+
                               |
                   (TEC > 127 veya REC > 127)
                               v
   +-------------------------------------------------------------+
   |  ERROR PASSIVE (Kısıtlı Durum)                              |
   |  (128 <= TEC <= 255 veya 128 <= REC <= 255)                 |
   |  Hata sezdiğinde 6 RECESSIVE bit basar (Ağı kilitleyemez).  |
   |  İletimden önce ek 8 bit bekleme cezası (Suspend Transmit). |
   +-------------------------------------------------------------+
                               |
                          (TEC > 255)
                               v
   +-------------------------------------------------------------+
   |  BUS-OFF (Ağdan Tam İzolasyon)                              |
   |  Düğümün çıkış transistörleri tamamen kapatılır!            |
   |  Hatta tek bir sinyal dahi basamaz. Ağ kurtarılır!          |
   +-------------------------------------------------------------+
```

### Bus-Off'un Kritik Önemi:
Eğer bir kanatçık motorunun mikrodenetleyicisi şaseye kısa devre yapmışsa veya kristali bozulup sürekli hatta gürültü basıyorsa; TEC sayacı 32 hatalı denemede $32 \times 8 = 256$'yı aşar ve donanım düğümü **BUS-OFF** durumuna alarak hattan elektriksel olarak söker. Diğer füzeler veya alt sistemler sorunsuz haberleşmeye devam eder!

```python
# -*- coding: utf-8 -*-
"""
GÜN 172: Kod Bloğu 3 — CAN Hata Sayacı (TEC/REC) ve Bus-Off İzolasyon Simülatörü
Hata Cezalandırma (+8), Başarılı Ödül (-1), Error Passive ve Bus-Off Geçişleri
"""

from typing import Dict, List

class CANFaultConfinementSimulator:
    """CAN Hata Durum Makinesi Modeli"""
    STATE_ERROR_ACTIVE  = "ERROR_ACTIVE"
    STATE_ERROR_PASSIVE = "ERROR_PASSIVE"
    STATE_BUS_OFF       = "BUS_OFF"

    def __init__(self, node_name: str):
        self.node_name = node_name
        self.tec = 0 # Transmit Error Counter
        self.rec = 0 # Receive Error Counter
        self.state = self.STATE_ERROR_ACTIVE
        self.history = []

    def log_state(self, event: str):
        self.history.append({
            "event": event,
            "tec": self.tec,
            "rec": self.rec,
            "state": self.state
        })

    def update_state(self):
        if self.tec > 255:
            self.state = self.STATE_BUS_OFF
        elif self.tec > 127 or self.rec > 127:
            self.state = self.STATE_ERROR_PASSIVE
        else:
            self.state = self.STATE_ERROR_ACTIVE

    def on_transmit_error(self):
        """Verim hatası: TEC + 8"""
        if self.state != self.STATE_BUS_OFF:
            self.tec += 8
            self.update_state()
            self.log_state("TX_ERROR (+8)")

    def on_transmit_success(self):
        """Başarılı aktarım: TEC - 1 (Sıfırın altına inemez)"""
        if self.state != self.STATE_BUS_OFF:
            if self.tec > 0:
                self.tec -= 1
            self.update_state()
            self.log_state("TX_SUCCESS (-1)")

# Simülasyon: Arızalanan Bir Aviyonik Sensörün Bus-Off'a Sürüklenmesi
sim_node = CANFaultConfinementSimulator("MISSILE_FIN_SENSOR")

# Başlangıç durumu
sim_node.log_state("INIT")

# 1. 16 Peş Peşe TX Hatası (16 * 8 = 128 -> Error Passive)
for _ in range(16):
    sim_node.on_transmit_error()

state_after_16 = sim_node.state
tec_after_16 = sim_node.tec

# 2. 16 TX Hatası Daha (128 + 128 = 256 -> Bus Off)
for _ in range(16):
    sim_node.on_transmit_error()

state_after_32 = sim_node.state
tec_after_32 = sim_node.tec

print("[*] CAN Hata Hapsedilmesi (Fault Confinement) Simülasyonu:")
print(f"  [+] 16 Hata Sonrası TEC: {tec_after_16}, Durum: {state_after_16} (Error Passive)")
print(f"  [!] 32 Hata Sonrası TEC: {tec_after_32}, Durum: {state_after_32} (BUS-OFF: Düğüm Hattan İzolasyon!)")

assert state_after_16 == CANFaultConfinementSimulator.STATE_ERROR_PASSIVE, "128 TEC ile Error Passive olunmalıydı!"
assert state_after_32 == CANFaultConfinementSimulator.STATE_BUS_OFF, "256 TEC ile Bus-Off olunmalıydı!"
print("\n[HÜCRE 10] CAN TEC/REC sayaçları ve Bus-Off izolasyon modeli başarıyla doğrulandı.")
```

## 7. STM32 bxCAN Donanım Mimarisi: Posta Kutuları ve Filtre Bankaları

STM32 serisindeki **bxCAN (Basic Extended CAN)** denetleyicisi, CPU'yu gereksiz mesaj kesmelerinden korumak için donanımsal posta kutuları ve filtreleme bankaları sunar:

### 1. İletim Posta Kutuları (Tx Mailboxes):
STM32'de 3 adet donanımsal iletim posta kutusu bulunur (`Mailbox 0, 1, 2`).
- İletim önceliği iki şekilde ayarlanabilir (`CAN_MCR_TXFP` biti):
  - **Kronolojik Sıra (FIFO):** Önce yüklenen mesaj önce hatta çıkar.
  - **Identifier Önceliği (ID Priority):** Posta kutularındaki mesajlardan Message ID'si en küçük (en öncelikli) olan donanım tarafından otomatik olarak ilk sıraya alınır!

### 2. Donanımsal Filtre Bankaları (Filter Banks):
Ağda saniyede $5000$ mesaj akabilir. Ancak bir kanatçık motoru sadece kendisini ilgilendiren `0x150` ve `0x010` mesajlarını dinlemek ister.
STM32, işlemciye tek bir kesme bile üretmeden mesajları donanımsal olarak süzen **14 (veya 28) adet Filtre Bankası** içerir:
1. **Identifier List Modu (Tam Eşleşme):** Filtreye yazılan ID'ler ile birebir eşleşen mesajlar kabul edilir, diğerleri donanımsal olarak çöpe atılır.
2. **Identifier Mask Modu (Aralık / Maske Eşleşmesi):**
   - `Filter ID`: Beklenen referans değer.
   - `Filter Mask`: Hangi bitlerin kontrol edileceği (`1` olan bitler eşleşmek zorundadır, `0` olan bitler önemsizdir - "Don't Care").
   - *Örnek:* ID = `0x200`, Mask = `0x7F0` $\implies$ `0x200` ila `0x20F` arasındaki tüm mesajlar tek bir filtreyle kabul edilir!

```python
# -*- coding: utf-8 -*-
"""
GÜN 172: Kod Bloğu 4 — C++20 STM32 bxCAN Donanımsal Filtre Bankası Simülatörü
Identifier List Modu, Identifier Mask Modu ve İlgisiz Mesajların Donanımsal Engellenmesi
"""

from typing import List, Dict

class STM32CANFilterBank:
    """STM32 bxCAN Donanımsal Filtre Modeli"""
    MODE_ID_LIST = "ID_LIST"
    MODE_ID_MASK = "ID_MASK"

    def __init__(self, filter_id: int, filter_mask_or_id2: int, mode: str):
        self.mode = mode
        self.filter_id = filter_id & 0x7FF
        self.filter_param2 = filter_mask_or_id2 & 0x7FF

    def matches(self, incoming_id: int) -> bool:
        incoming_id &= 0x7FF
        if self.mode == self.MODE_ID_LIST:
            # İki ID'den biriyle birebir eşleşmeli
            return (incoming_id == self.filter_id) or (incoming_id == self.filter_param2)
        elif self.mode == self.MODE_ID_MASK:
            # (incoming_id & Mask) == (Filter_ID & Mask)
            mask = self.filter_param2
            return (incoming_id & mask) == (self.filter_id & mask)
        return False

# Test ve Doğrulama
# Filtre 1: ID List Modu -> Sadece 0x010 (Acil Stop) ve 0x150 (Motor) geçebilir
filter_list = STM32CANFilterBank(filter_id=0x010, filter_mask_or_id2=0x150, mode=STM32CANFilterBank.MODE_ID_LIST)

# Filtre 2: ID Mask Modu -> 0x200 bazlı, Mask: 0x7F0 (0x200..0x20F telemetri bloğu geçer)
filter_mask = STM32CANFilterBank(filter_id=0x200, filter_mask_or_id2=0x7F0, mode=STM32CANFilterBank.MODE_ID_MASK)

# Gelen Mesajlar
test_messages = [0x010, 0x150, 0x155, 0x203, 0x209, 0x300, 0x7FF]

accepted_by_list = [msg for msg in test_messages if filter_list.matches(msg)]
accepted_by_mask = [msg for msg in test_messages if filter_mask.matches(msg)]

print("[*] STM32 bxCAN Donanımsal Filtre Bankası Testi:")
print(f"  [+] Gelen Tüm Mesajlar       : {[hex(x) for x in test_messages]}")
print(f"  [+] ID List Filtresi Kabulü  : {[hex(x) for x in accepted_by_list]} (Beklenen: 0x10, 0x150)")
print(f"  [+] ID Mask (0x20X) Kabulü   : {[hex(x) for x in accepted_by_mask]} (Beklenen: 0x203, 0x209)")

assert accepted_by_list == [0x010, 0x150], "List filtre eşleşmesi hatalı!"
assert accepted_by_mask == [0x203, 0x209], "Mask filtre eşleşmesi hatalı!"
print("\n[HÜCRE 12] STM32 bxCAN donanımsal filtreleme algoritmaları başarıyla doğrulandı.")
```

## 8. Savunma Sanayii Aviyonik Senaryosu: Füze Kanatçık Kontrolü

Hassas güdümlü bir tanksavar veya hava savunma füzesinde (örneğin ROKETSAN CİRİT / HİSAR):
- Füze gövdesinde $4$ adet aerodinamik kontrol kanatçığı bulunur (Fin Actuator 1..4).
- Ana Görev Bilgisayarı (Guidance Computer) kanatçık motorlarına her $1\ \text{ms}$'de bir hedef açı komutu gönderir.

### Taktik CAN Mesaj Kimliği (ID) Hiyerarşisi:
Savunma sanayiinde CAN Message ID'leri rastgele verilmez; gecikme toleransına (Deadline) göre en katı öncelik sırasıyla atanır:

| Mesaj ID | Mesaj Tanımı | Gönderici | Periyot / Tetik | Öncelik Seviyesi |
| :---: | :--- | :--- | :---: | :--- |
| **`0x001`** | **Acil Uçuş Sonlandırma (FTS / Abort)** | Güvenlik Sistemi | Asenkron (Acil) | **Kritik 1 (En Yüksek)** |
| **`0x050`** | **Ateşleme / Harp Başlığı Hazırlık** | Görev Bilgisayarı | $10\ \text{ms}$ | **Kritik 2** |
| **`0x100`** | **Kanatçık Açı Komutu (Fin Actuators)**| Güdüm Bilgisayarı | $1\ \text{ms}$ ($1\ \text{kHz}$) | **Yüksek (Gerçek Zamanlı)** |
| **`0x250`** | **Kanatçık Pozisyon Geri Bildirimi** | Aktüatör Düğümleri | $2\ \text{ms}$ | Orta |
| **`0x600`** | **Batarya Voltajı ve Motor Sıcaklığı**| Güç Birimi | $50\ \text{ms}$ | Düşük |
| **`0x7E0`** | **Saha Hata Teşhis (Diagnostic / UDS)**| Bakım Terminali | İstek üzerine | **En Düşük** |

Ağda tam bir trafik patlaması (Bus Congestion) yaşansa dahi, `0x001` Abort mesajı sıfır mikrosaniye gecikmeyle tüm diğer mesajları tahkimde ezer ve kanatçıkları anında emniyet moduna çeker!

```python
# -*- coding: utf-8 -*-
"""
GÜN 172: Kod Bloğu 5 — Taktik Füze CAN Bus Ağ Trafiği ve Öncelik Tahkim Yarışı
Trafik Tıkanıklığı Anında Deterministik Öncelik Tahkimi ve Gecikme (Latency) Ölçümü
"""

class TacticalCANMessage:
    def __init__(self, msg_id: int, name: str, payload: List[int]):
        self.msg_id = msg_id
        self.name = name
        self.payload = payload

class TacticalBusScheduler:
    """Taktik Ağ Tahkim Zamanlayıcısı"""
    def __init__(self):
        self.tx_queue = []

    def queue_message(self, msg: TacticalCANMessage):
        self.tx_queue.append(msg)

    def resolve_arbitration_order(self) -> List[TacticalCANMessage]:
        """Tüm düğümler aynı anda hatta girmeye çalıştığında çıkış sırasını çözer"""
        # CAN donanımı gereği en düşük ID ilk çıkar (Deterministik sıralama)
        sorted_order = sorted(self.tx_queue, key=lambda m: m.msg_id)
        self.tx_queue.clear()
        return sorted_order

# Simülasyon: Tam Patlama Anı (Tüm Sistemler Aynı Mikrosaniyede Hatta Girdi)
scheduler = TacticalBusScheduler()
scheduler.queue_message(TacticalCANMessage(0x600, "BATTERY_TEMP", [0x28]))
scheduler.queue_message(TacticalCANMessage(0x100, "FIN_ANGLE_CMD", [0x05, 0x10]))
scheduler.queue_message(TacticalCANMessage(0x001, "EMERGENCY_ABORT", [0xAA]))
scheduler.queue_message(TacticalCANMessage(0x250, "FIN_FEEDBACK", [0x05, 0x0F]))
scheduler.queue_message(TacticalCANMessage(0x050, "WARHEAD_ARM", [0x01]))

resolved_stream = scheduler.resolve_arbitration_order()

print("[*] Taktik Füze CAN Bus Tahkim Çözümleme Sırası:")
for rank, msg in enumerate(resolved_stream, start=1):
    print(f"  {rank}. Sıra -> ID: 0x{msg.msg_id:03X} | Mesaj: {msg.name:<18} | Yük: {[hex(b) for b in msg.payload]}")

# Katı Doğrulamalar
assert resolved_stream[0].name == "EMERGENCY_ABORT", "0x001 ilk sırada çıkmalıydı!"
assert resolved_stream[1].name == "WARHEAD_ARM", "0x050 ikinci sırada çıkmalıydı!"
assert resolved_stream[2].name == "FIN_ANGLE_CMD", "0x100 üçüncü sırada çıkmalıydı!"
assert resolved_stream[-1].name == "BATTERY_TEMP", "0x600 en son çıkmalıydı!"
print("\n[HÜCRE 14] Taktik aviyonik CAN öncelik tahkimi ve determinizm testi başarıyla doğrulandı.")
```

## 9. Üretim Seviyesi C++20 Type-Safe CAN Frame Yapısı

Modern C++20 standardında CAN mesaj çerçeveleri tip güvenli (type-safe) ve sıfır ek maliyetli yapılar olarak modellenir:

```cpp
// ============================================================================
// C++20 Modern CAN Frame & Filter Mimarisi
// ============================================================================
#include <cstdint>
#include <span>
#include <array>
#include <concepts>

namespace defense::can {

enum class IdType : uint8_t { Standard11Bit, Extended29Bit };
enum class FrameType : uint8_t { DataFrame, RemoteFrame };

struct CanMessage {
    uint32_t id{0};
    IdType id_type{IdType::Standard11Bit};
    FrameType frame_type{FrameType::DataFrame};
    uint8_t dlc{0};
    std::array<uint8_t, 8> data{};

    [[nodiscard]] constexpr bool is_high_priority() const noexcept {
        return id < 0x100; // 0x100 altı kritik görev mesajları
    }
};

template <uint32_t FilterId, uint32_t FilterMask>
class HardwareFilter {
public:
    [[nodiscard]] static constexpr bool accept(uint32_t incoming_id) noexcept {
        return (incoming_id & FilterMask) == (FilterId & FilterMask);
    }
};

// Aviyonik Aktüatör Filtresi: 0x150 .. 0x15F arasını kabul eder
using FinActuatorFilter = HardwareFilter<0x150, 0x7F0>;

static_assert(FinActuatorFilter::accept(0x153) == true);
static_assert(FinActuatorFilter::accept(0x200) == false);

} // namespace defense::can
```

## 10. Bilerek Bozduğumuz Şey (Sabotaj ve Arıza Analizi)

### Sabotaj 1: Kopuk veya Eksik 120 Ohm Sonlandırma Direnci
CAN veri yolunun iki ucundaki $120\ \Omega$ dirençlerden birinin veya ikisinin takılmaması:
- **Ne Olur?:** Yüksek hızlı kare dalga sinyalleri hattın sonuna ulaştığında geri yansır (Standing Wave / Signal Reflection).
- **Sonuç:** $1\ \text{Mbps}$ hızında yansıyan dalgalar asıl sinyalin üzerine biner; diferansiyel alıcılar bitleri yanlış okur, sürekli `CRC Error` ve `Stuff Error` oluşur. Düğümler birkaç saniye içinde `Bus-Off` olup ağı kilitler.

### Sabotaj 2: İki Farklı Düğüme Aynı Message ID Verilmesi
İki farklı sensörün (örn. Sol Kanatçık ve Sağ Kanatçık) donanım ID'sinin yanlışlıkla ikisine de `0x150` olarak kodlanması:
- **Ne Olur?:** İki düğüm aynı anda iletime başlarsa, ID bitleri boyunca tahkim çözülemez (ikisi de aynı bitleri basar).
- **Sonuç:** Veri alanına (Payload) gelindiğinde farklı baytlar basıldığı an her iki düğüm de hattan kendi bastığı bitten farklı bir bit okur (Bit Error). İkisi de aynı anda hatta `Error Frame` fırlatır! Ağ tamamen felç olur.

## 11. Karşılaştırma Matrisi: CAN vs CAN FD vs RS-485

| Karşılaştırma Kriteri | Klasik CAN 2.0B | CAN FD (Flexible Datarate) | RS-485 (UART / Modbus) |
| :--- | :--- | :--- | :--- |
| **Maksimum Veri Hızı** | $1\ \text{Mbps}$ ($40\ \text{m}$) | **$5 - 8\ \text{Mbps}$** | **$10\ \text{Mbps}$** |
| **Maksimum Veri Yükü** | $8\ \text{Bayt}$ | **$64\ \text{Bayt}$** | Sınırsız (Paket yapısına bağlı) |
| **Tahkim (Arbitration)** | **Kayıpsız Bit Düzeyinde** | **Kayıpsız Bit Düzeyinde** | Yok (Master-Slave sorgulama) |
| **Donanımsal Hata Ayıklama**| **Var (TEC/REC/Bus-Off)** | **Var (Gelişmiş CRC)** | Yok (Yazılıma bağlı) |
| **Gürültü Bağışıklığı** | **Aşırı Yüksek (Diferansiyel)** | **Aşırı Yüksek** | Yüksek (Diferansiyel) |
| **Kullanım Alanı** | Aviyonik, Motor, Taret | Yeni Nesil Radar/Kamera | Uzun Mesafe Güç Panoları |

## 12. Donanım ve Yazmaç Haritası (STM32 CAN1/CAN2 bxCAN)

STM32F4 serisinde CAN modüllerinin bellek adresleri:

```
  [ APB1 Veri Yolu (42 MHz) ]
    |---> CAN1 : 0x40006400 (Master bxCAN - 14/28 Filtre Bankasını Yönetir)
    |---> CAN2 : 0x40006800 (Slave bxCAN - CAN1 saati açık olmadan çalışamaz!)

  Kritik Yazmaçlar:
  - CAN_MCR : Master Control Register (INRQ: Başlatma Modu, TXFP: İletim Önceliği)
  - CAN_MSR : Master Status Register (INAK: Başlatma Onayı, SLAK: Uyku Modu)
  - CAN_TSR : Transmit Status Register (TME0..2: Mailbox Boş Bayrakları)
  - CAN_RF0R: Receive FIFO 0 Register (FMP0: Gelen Mesaj Sayısı)
  - CAN_ESR : Error Status Register (LEC: Hata Kodu, TEC: Sayaç, REC: Sayaç)
```

## 13. Mülakat ve Saha Tuzakları (Top 5 Gotchas)

1. **"Daha büyük ID daha önceliklidir" Yanılgısı:**
   - Hayır! Tam tersine ikili sistemde '0' baskın olduğu için **en küçük sayısal ID en yüksek önceliğe sahiptir**.
2. **STM32'de CAN2'yi Başlatırken CAN1 Saatini Açmamak:**
   - CAN2 donanımı SRAM ve filtre bankalarını CAN1 ile paylaşır. `RCC->APB1ENR` üzerinde `CAN1EN` açılmazsa `CAN2` asla başlamaz!
3. **Tek Bir Düğümle CAN Bus'ı Test Etmeye Çalışmak:**
   - Hatta en az bir alıcı olmalıdır! Verici paketi gönderdiğinde ACK slotunda hiçbir alıcı '0' basmazsa `ACK Error` alır ve paketi sonsuza kadar tekrar gönderir.
4. **Sonlandırma Direncini Rastgele Takmak:**
   - $120\ \Omega$ dirençler hattın ortasına değil, mutlaka hattın fiziksel olarak **en uçtaki iki ucuna** takılmalıdır.
5. **Bus-Off Durumuna Düşen Düğümü Otomatik Resetlemek:**
   - Bus-Off donanımın kendini koruma refleksidir. Donanımsal arıza çözülmeden yazılımla zorla resetlenirse diğer tüm ağ çöker.

## 14. 5N1K Özeti

- **Ne?:** CAN Bus, diferansiyel sinyalleşme, kayıpsız bit düzeyinde tahkim (CSMA/NBA) ve hata hapsedilmesine sahip çoklu master endüstriyel/askeri veri yoludur.
- **Neden?:** Yüksek elektromanyetik gürültü altında sıfır veri kaybı ve deterministik öncelik yönetimi sağlamak için.
- **Nasıl?:** Baskın (0) bitlerin çekinik (1) bitleri ezmesi ve çekilen düğümlerin dinleme moduna geçmesiyle.
- **Nerede?:** Zırhlı araç taret kontrolü, taktik füze aktüatörleri, İHA uçuş kontrol ağlarında.
- **Ne Zaman?:** Birden fazla bağımsız kontrolcünün aynı fiziksel kablo üzerinden çarpışmasız veri paylaşması gerektiğinde.
- **Kim?:** Aviyonik gömülü yazılım mühendisleri, savunma sanayii kontrol mimarları.

## 15. Gün Sonu Özeti ve Yetkinlik Kontrolü

### 3 Cümlelik Özet:
1. **CAN Bus Nedir?:** CAN bus, $120\ \Omega$ sonlandırmalı diferansiyel hatlar üzerinden kayıpsız bit düzeyinde tahkimle çalışan çoklu-master bir ağ protokolüdür.
2. **Hangi Problemi Çözer?:** Veri çarpışmalarında paket kaybını önler ve küçük sayısal ID'li kritik mesajların sıfır gecikmeyle hatta çıkmasını garanti eder.
3. **Getirdiği Risk / Trade-off:** Hata sayaçları (TEC) 255'i aştığında düğümün ağdan tamamen kopması (Bus-Off) ve maksimum $1\ \text{Mbps}$ hız sınırıdır.

### Yetkinlik Kontrol Listesi:
- [x] CAN diferansiyel sinyalleşmesini ve dominant/recessive voltaj seviyelerini biliyorum.
- [x] Kayıpsız tahkim (Arbitration) yarışını ve küçük ID'nin neden kazandığını simüle edebiliyorum.
- [x] 5 ardışık bitten sonra uygulanan Bit Stuffing mantığını ve Stuff Error'ü anladım.
- [x] TEC/REC sayaçlarının düğümü nasıl Bus-Off durumuna getirdiğini açıklayabiliyorum.
- [x] STM32 bxCAN donanımsal filtreleme (ID List ve ID Mask) yapısını uygulayabiliyorum.
- [x] Aviyonik acil durum (Abort) mesajının deterministik önceliğini tasarlayabiliyorum.

## 16. İleri Okuma ve Kaynaklar

1. **ISO 11898-1 / 11898-2 Standard:** *Road vehicles — Controller area network (CAN) — Data link layer and physical signalling.*
2. **Bosch CAN Specification Version 2.0:** *Robert Bosch GmbH Official Reference.*
3. **STMicroelectronics Reference Manual (RM0090):** *bxCAN Controller, Mailboxes and Acceptance Filters.*
4. **Vector Informatik GmbH Knowledge Base:** *CAN Arbitration and Bit Timing Principles.*

## 17. 24-Hücreli Master Mimari Onay Beyanı

Bu eğitim modülü, ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ standartlarında C++20 ve STM32 Gömülü Sistemler Müfredatı kapsamında hazırlanmıştır.

```
+-----------------------------------------------------------------------------------+
|               GÜN 172 MASTER MİMARİ MÜHENDİSLİK DOĞRULAMA RAPORU                  |
+-----------------------------------------------------------------------------------+
| 1. Toplam Hücre Sayısı        : 24 Hücre (18 Markdown, 6 Python Kodu)             |
| 2. Fiziksel Katman Modelleri  : Diferansiyel CAN_H/CAN_L, 120 Ohm, Vdiff          |
| 3. Protokol Dinamikleri       : Non-Destructive Bitwise Arbitration, Bit Stuffing |
| 4. Güvenilirlik Mimarisi      : TEC/REC Sayaçları, Error Passive, Bus-Off İzole   |
| 5. Aviyonik Senaryosu         : Füze Kanatçık Kontrolü & E-Stop Determinizmi      |
| 6. Görsel Artefact            : 300 DPI 4-Panelli Koyu Tema Dashboard (.PNG)      |
| 7. Özel Lisans                : Telif Hakkı (c) 2026 Seydi Eryılmaz               |
+-----------------------------------------------------------------------------------+
```

```python
# -*- coding: utf-8 -*-
"""
GÜN 172: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Doğrulama Testleri
Paneller:
1. CAN Diferansiyel Sinyalleşmesi (CAN_H, CAN_L, Vdiff, Dominant vs Recessive)
2. Bit Düzeyinde Tahkim (Arbitration) Yarışı ve Çekilen Düğümlerin Dalga Formu
3. CAN Bit Stuffing (5 Aynı Bitten Sonra Ters Bit Enjeksiyonu) Zaman Çizelgesi
4. CAN Hata Durum Makinesi (Error Active -> Error Passive -> Bus-Off) ve TEC Eğrisi
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
# PANEL 1: CAN Diferansiyel Sinyalleşmesi (CAN_H, CAN_L, Vdiff)
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_facecolor(C_BG)

time_pts = np.linspace(0, 8, 800)
# Temsili Bit Dizisi: 1 (Recessive), 0 (Dominant), 0 (Dominant), 1, 0, 1, 1, 0
bits = [1, 0, 0, 1, 0, 1, 1, 0]

can_h = []
can_l = []
v_diff = []

for t in time_pts:
    bit_idx = int(t) % len(bits)
    b = bits[bit_idx]
    if b == 0: # Dominant
        can_h.append(3.5)
        can_l.append(1.5)
        v_diff.append(2.0)
    else: # Recessive
        can_h.append(2.5)
        can_l.append(2.5)
        v_diff.append(0.0)

ax1.plot(time_pts, can_h, color=C_RED, linewidth=2, label='CAN_H (High: 3.5V / 2.5V)')
ax1.plot(time_pts, can_l, color=C_CYAN, linewidth=2, label='CAN_L (Low: 1.5V / 2.5V)')
ax1.plot(time_pts, v_diff, color=C_GREEN, linewidth=2.5, linestyle='--', label='Vdiff = CAN_H - CAN_L (2.0V / 0V)')

ax1.set_yticks([0.0, 1.5, 2.0, 2.5, 3.5])
ax1.set_yticklabels(['0V', '1.5V', '2.0V', '2.5V', '3.5V'], color=C_WHITE, fontsize=9)
ax1.set_xlabel("Zaman (Bit Periyotları)", color=C_WHITE, fontsize=10)
ax1.set_ylabel("Voltaj (V)", color=C_WHITE, fontsize=10)
ax1.set_title("Panel 1: CAN Diferansiyel Sinyalleşmesi ve Dominant/Recessive Seviyeleri", color=C_WHITE, fontsize=12, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax1.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 2: Bit Düzeyinde Tahkim (Arbitration) Yarışı
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_facecolor(C_BG)

steps = np.arange(0, 11, 1)
# Node 1 (0x010): 0 0 0 0 0 0 1 0 0 0 0 -> Kazanan
# Node 2 (0x150): 0 0 1 0 1 0 1 0 0 0 0 -> 2. bitte elenir
# Node 3 (0x380): 0 1 1 1 0 0 0 0 0 0 0 -> 1. bitte elenir

n1_bits = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]
n2_bits = [0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0]
n3_bits = [0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
bus_bits = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]

ax2.step(steps, np.array(n3_bits) * 0.7 + 2.4, color='#94A3B8', where='post', linewidth=2, label="Düğüm 3 (0x380 - 1. Bitte Çekildi)")
ax2.step(steps, np.array(n2_bits) * 0.7 + 1.3, color=C_YELLOW, where='post', linewidth=2, label="Düğüm 2 (0x150 - 2. Bitte Çekildi)")
ax2.step(steps, np.array(n1_bits) * 0.7 + 0.2, color=C_GREEN, where='post', linewidth=2.5, label="Düğüm 1 (0x010 - KAZANAN)")

# Elenme İşaretleri
ax2.scatter([1], [2.4 + 0.7], color=C_RED, s=100, zorder=5)
ax2.annotate("0x380 Elendi!", xy=(1, 3.1), xytext=(1.5, 3.3), color=C_RED, fontweight='bold', fontsize=8, arrowprops=dict(facecolor=C_RED, arrowstyle="->"))

ax2.scatter([2], [1.3 + 0.7], color=C_RED, s=100, zorder=5)
ax2.annotate("0x150 Elendi!", xy=(2, 2.0), xytext=(2.5, 2.2), color=C_RED, fontweight='bold', fontsize=8, arrowprops=dict(facecolor=C_RED, arrowstyle="->"))

ax2.set_yticks([0.5, 1.6, 2.7])
ax2.set_yticklabels(['0x010 (E-Stop)', '0x150 (Fin)', '0x380 (Batt)'], color=C_WHITE, fontsize=9, fontweight='bold')
ax2.set_xlabel("Message ID Bit İndeksi (MSB -> LSB)", color=C_WHITE, fontsize=10)
ax2.set_title("Panel 2: Kayıpsız Bit Düzeyinde Tahkim (Arbitration) Yarışı", color=C_WHITE, fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax2.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 3: CAN Bit Stuffing (5 Aynı Bitten Sonra Ters Bit)
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_facecolor(C_BG)

# Orijinal: 0 0 0 0 0 0 0 1
# Stuffed : 0 0 0 0 0 [1] 0 0 1
raw_seq = [0, 0, 0, 0, 0, 0, 0, 1]
stuffed_seq = [0, 0, 0, 0, 0, 1, 0, 0, 1]

t_raw = np.arange(len(raw_seq))
t_stuffed = np.arange(len(stuffed_seq))

ax3.step(t_raw, np.array(raw_seq) * 0.8 + 1.3, color=C_CYAN, where='post', linewidth=2.2, label='Ham Veri (7 Adet Ardışık 0)')
ax3.step(t_stuffed, np.array(stuffed_seq) * 0.8 + 0.1, color=C_PURPLE, where='post', linewidth=2.2, label='Doldurulmuş Akış (Stuff Bit: 1)')

ax3.scatter([5.5], [0.9], color=C_YELLOW, s=120, zorder=5)
ax3.annotate("STUFF BİTİ (1)\nSenkronizasyon Korundu", xy=(5.5, 0.9), xytext=(5.0, 2.5),
             color=C_YELLOW, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_YELLOW, arrowstyle="->"))

ax3.set_yticks([0.5, 1.7])
ax3.set_yticklabels(['Stuffed Akış', 'Ham Veri'], color=C_WHITE, fontsize=9, fontweight='bold')
ax3.set_xlabel("Bit Sırası", color=C_WHITE, fontsize=10)
ax3.set_title("Panel 3: CAN Donanımsal Bit Stuffing (Doldurma) Mekanizması", color=C_WHITE, fontsize=12, fontweight='bold')
ax3.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax3.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

# ------------------------------------------------------------------------------
# PANEL 4: CAN Hata Durum Makinesi ve TEC Eğrisi
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_facecolor(C_BG)

# 35 Hata simülasyonu
tx_attempts = np.arange(0, 36, 1)
tec_values = [min(i * 8, 260) for i in tx_attempts]

ax4.plot(tx_attempts, tec_values, color=C_RED, linewidth=2.5, label='TEC (Transmit Error Counter)')

# Bölgeler
ax4.axhspan(0, 127, color=C_GREEN, alpha=0.15, label='Error Active (0 - 127)')
ax4.axhspan(128, 255, color=C_YELLOW, alpha=0.15, label='Error Passive (128 - 255)')
ax4.axhspan(256, 270, color=C_RED, alpha=0.25, label='BUS-OFF (> 255 İzolasyon!)')

ax4.axhline(128, color=C_YELLOW, linestyle='--')
ax4.axhline(256, color=C_RED, linestyle='--')

ax4.scatter([16], [128], color=C_YELLOW, s=80, zorder=5)
ax4.scatter([32], [256], color=C_RED, s=100, zorder=5)

ax4.annotate("Error Passive Geçişi\n(TEC = 128)", xy=(16, 128), xytext=(5, 170),
             color=C_YELLOW, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_YELLOW, arrowstyle="->"))

ax4.annotate("BUS-OFF KİLİTLEME!\n(Hattan İzolasyon)", xy=(32, 256), xytext=(18, 240),
             color=C_RED, fontweight='bold', fontsize=8,
             arrowprops=dict(facecolor=C_RED, arrowstyle="->"))

ax4.set_xlabel("Ardışık Verim Hatası Sayısı", color=C_WHITE, fontsize=10)
ax4.set_ylabel("Hata Sayacı Değeri (TEC)", color=C_WHITE, fontsize=10)
ax4.set_title("Panel 4: CAN Hata Hapsedilmesi (Fault Confinement) Durum Geçişleri", color=C_WHITE, fontsize=12, fontweight='bold')
ax4.set_ylim(0, 275)
ax4.grid(True, linestyle='--', alpha=0.3, color='#64748B')
ax4.legend(loc='lower right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.suptitle("GÜN 172: CAN Bus — Diferansiyel İletim, Tahkim ve Hata Hapsedilme Panosu\nTelif Hakkı (c) 2026 Seydi Eryılmaz — Tüm Hakları Saklıdır", 
             color=C_WHITE, fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# PNG Kaydetme Fallback Mekanizması
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_172_can_arbitration_ve_message_id.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_172\gun_172_can_arbitration_ve_message_id.png"

plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close()
print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# ==============================================================================
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# ==============================================================================
print("\n[*] GÜN 172 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

# 1. Dosya Varlık ve Boyut Doğrulaması
assert os.path.exists(PNG_FILE), f"PNG dosyası bulunamadı: {PNG_FILE}"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB'dan küçük: {png_size} bayt!"

# 2. Tahkim Assertions
n_a = CANNode("A", 0x100, [1])
n_b = CANNode("B", 0x050, [2])
arb_test = CANBusArbitrationEngine([n_a, n_b]).run_arbitration()
assert arb_test["winner_node"] == "B", "0x050 öncelikli olmalı!"

# 3. Bit Stuffing Assertions
st_res, st_pts = CANBitStuffer.apply_bit_stuffing([1, 1, 1, 1, 1, 1])
assert len(st_pts) == 1, "1 adet stuff bit eklenmeliydi!"
assert st_res[5] == 0, "5 ardışık '1'den sonra '0' eklenmeliydi!"

# 4. Hata Sayacı ve Bus-Off Assertions
fc = CANFaultConfinementSimulator("TEST")
for _ in range(33):
    fc.on_transmit_error()
assert fc.state == CANFaultConfinementSimulator.STATE_BUS_OFF, "33 hatada Bus-off olunmalı!"

# 5. Filtre Bankası Assertions
fb = STM32CANFilterBank(0x100, 0x7F0, STM32CANFilterBank.MODE_ID_MASK)
assert fb.matches(0x105) is True, "0x105 maskeye uymalı!"
assert fb.matches(0x200) is False, "0x200 maskeye uymamalı!"

print("\n[PASS] Gün 172: Tüm Katı Doğrulama Testleri Başarıyla Geçti!")
```
