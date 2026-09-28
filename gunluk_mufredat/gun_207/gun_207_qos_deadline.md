# GÜN 207: DDS QoS Temelleri — Deadline Politikası, Periyodik Veri Sözleşmeleri ve Kaçırılan Teslim Süreleri (Missed Deadline)

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

YASAKLAR:
  1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
  2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
  3. Alt lisanslanamaz, satılamaz veya devredilemez.
  4. Tersine mühendislik yapılamaz.

İZİN VERİLEN KULLANIM:
  - GitHub üzerinde görüntüleme ve okuma.
  - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).

YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
İzin talepleri için: GitHub @seydivakkas
```

---

## Yönetici Özeti ve Junior Geliştirici Mental Modeli

Gerçek zamanlı aviyonik ve robotik sistemlerde (ör. TUSAŞ GÖKBEY helikopter uçuş kontrol bilgisayarı, ASELSAN HİSAR hava savunma füzesi güdüm döngüsü), bir verinin sadece "doğru" olması yetmez; **"zamanında"** gelmesi gerekir. 100 Hz frekansla (her 10 milisaniyede bir) çalışan bir uçuş kontrol bilgisayarı için 25 milisaniye sonra gelen irtifa verisi işe yaramaz; hatta bu gecikme kontrol yüzeylerinin titremesine ve uçağın aerodinamik kararsızlığa girmesine neden olabilir.

DDS mimarisindeki `DeadlineQosPolicy`, üretici (DataWriter) ile tüketici (DataReader) arasında **zamansal bir sözleşme** (Temporal Contract) imzalar:
- **Yazar:** "Ben her bir nesne (`instance`) için en geç $T_{\text{offered}}$ sürede bir yeni örnek üreteceğim."
- **Okuyucu:** "Bana her bir nesne için en geç $T_{\text{requested}}$ sürede bir yeni örnek gelmelidir; gelmezse acil durum alarmı ver!"

### Junior Mental Modeli: "Yoğun Bakım Kalp Monitörü ve Tren Seferi"
- **Kalp Monitörü (Watchdog / Deadline):** Kalp monitörü her 1 saniyede bir kalp atışı ("bip" sesi) bekler. Eğer 1.5 saniye geçer ve ses gelmezse monitör hemen kırmızı ışık yakıp acil durum alarmı çalar (`RequestedDeadlineMissed`). Doktorun "acaba hasta iyi mi?" diye her saniye gidip nabız kontrol etmesine gerek yoktur; monitör (DDS) zaman aşımını otomatik denetler.
- **Tren Seferleri (RxO Sözleşmesi):** Bir yolcu (Okuyucu) "Ben en fazla 15 dakikada bir tren gelsin istiyorum" (`Requested = 15 dk`) derse; Tren İşletmesi (Yazar) "Biz her 10 dakikada bir tren kaldırıyoruz" (`Offered = 10 dk`) diyorsa yolcu memnun kalır (**EŞLEŞİR**). Ancak işletme "Biz 20 dakikada bir tren kaldırıyoruz" derse yolcu trene binmez (**UYUŞMAZLIK!**).

## Deadline QoS Politikası, Matematiksel Model ve Durum Geri Çağrımları

OMG DDS standardında `DeadlineQosPolicy` tek bir süre (`Duration_t period`) parametresi alır:

$$\text{DeadlineQosPolicy} = \{ \text{period}: \Delta t \}$$

### 1. RxO (Requested vs Offered) Uyumluluk Kuralı
Zaman politikalarında kural güvenilirlik ve kalıcılık politikalarının **tersidir**! Bir yayıncının bir okuyucuyu besleyebilmesi için, yazarın veri üretim periyodu okuyucunun azami bekleme süresine **eşit ya da ondan daha kısa (daha hızlı)** olmak zorundadır:

$$\text{Offered.period} \le \text{Requested.period}$$

- Yazar $10\text{ ms}$ sunarken okuyucu $20\text{ ms}$ beklerse: **EŞLEŞİR** ($10 \le 20$, yazar daha hızlı besliyor).
- Yazar $50\text{ ms}$ sunarken okuyucu $20\text{ ms}$ beklerse: **UYUŞMAZLIK!** DDS `INCONSISTENT_QOS` / `REQUESTED_INCOMPATIBLE_QOS` hatası verir ve bağlantı kurulmaz!

### 2. İki Taraflı Zaman Aşımı Gözlemi (Dual-Sided Missed Deadlines)
Deadline mekanizması hem yazar hem de okuyucu tarafında bağımsız sayaçlar işletir:

| Olay / Durum Yapısı | Tetiklenme Yeri | Anlamı ve Kök Neden |
|---|---|---|
| **`OfferedDeadlineMissedStatus`** | DataWriter (Yayıncı) | Yazar taahhüt ettiği $T_{\text{offered}}$ süresi içinde `write()` fonksiyonunu çağırmadı (Sensör dondu, thread takıldı, kilitlenme). |
| **`RequestedDeadlineMissedStatus`** | DataReader (Abone) | Okuyucuya $T_{\text{requested}}$ süresi içinde yeni örnek gelmedi (Ağ koptu, paketler düştü veya yazar çöktü). |

### 3. Çok Anahtarlı (Per-Instance) Deadline İzleme
Eğer Topic bir `@key` alanına sahipse (ör. `track_id` ile radar izleri), DDS her bir hedef için **bağımsız bir zamanlayıcı** çalıştırır:
$$\Delta t_k = t_{\text{now}} - t_{\text{last\_update}}(k) > T_{\text{deadline}} \implies \text{DeadlineMissed}(k)$$
Bir hedefin sinyal kaybetmesi, diğer aktif hedeflerin zamanlayıcılarını asla etkilemez!

## Kod 1 Mimarisi: Minimal Deadline Doğrulama ve Missed Callback Simülasyonu

Bu minimal senaryoda:
1. 100 Hz ile veri üreten bir uçuş sensörü ($T_{\text{offered}} = 10\text{ ms}$) ve bunu tüketen uçuş bilgisayarı ($T_{\text{requested}} = 12\text{ ms}$) modellenir.
2. Sensör ilk 3 örneği 10 ms arayla düzenli üretir.
3. 4. örnekte yapay bir sensör gecikmesi ($25\text{ ms}$) enjekte edilir.
4. Okuyucunun `on_requested_deadline_missed` geri çağrımı çalışarak zaman aşımını ve etkilenen örneği tespit eder.

```python
# ==============================================================================
# KOD 1: Minimal Deadline Sözleşmesi ve Zaman Aşımı Simülatörü
# Amaç: Belirlenen periyodun (12 ms) aşılması durumunda
# on_requested_deadline_missed durumunun tetiklendiğini doğrulamak.
# ==============================================================================

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DeadlineStatus:
    total_count: int = 0
    total_count_change: int = 0
    last_instance_handle: Optional[str] = None

class MinimalDeadlineMonitor:
    def __init__(self, requested_deadline_ms: float):
        self.requested_deadline_ms = requested_deadline_ms
        self.last_arrival_time_ms: Optional[float] = None
        self.status = DeadlineStatus()
        self.received_samples: List[str] = []

    def on_data_arrived(self, current_time_ms: float, payload: str, instance_id: str = "DEFAULT"):
        if self.last_arrival_time_ms is not None:
            delta_t = current_time_ms - self.last_arrival_time_ms
            # Deadline Kontrolü
            if delta_t > self.requested_deadline_ms:
                self.status.total_count += 1
                self.status.total_count_change = 1
                self.status.last_instance_handle = instance_id
                print(f"[ALARM] DEADLINE MISSED! Gecikme: {delta_t:.1f}ms (Tavan: {self.requested_deadline_ms}ms) Hedef: {instance_id}")
            else:
                self.status.total_count_change = 0

        self.last_arrival_time_ms = current_time_ms
        self.received_samples.append(payload)

# Simülasyon: 100 Hz Beklenti (Requested Deadline = 12.0 ms)
monitor = MinimalDeadlineMonitor(requested_deadline_ms=12.0)

# Zaman çizelgesi simülasyonu (ms): t=0, t=10, t=20 (Normal), t=45 (25ms gecikme -> Missed!)
timeline = [
    (0.0, "ALT_1000m"),
    (10.0, "ALT_1002m"),
    (20.0, "ALT_1005m"),
    (45.0, "ALT_1010m") # 25 ms aralık! (Deadline 12 ms idi)
]

for t, data in timeline:
    monitor.on_data_arrived(current_time_ms=t, payload=data)

print(f"\n[KOD 1] Simülasyon Sonuçları:")
print(f"  - Toplam Alınan Örnek      : {len(monitor.received_samples)} (Beklenen: 4)")
print(f"  - Kaçırılan Deadline Sayısı: {monitor.status.total_count} (Beklenen: 1)")

assert len(monitor.received_samples) == 4
assert monitor.status.total_count == 1, "Tam olarak 1 adet deadline ihlali tespit edilmelidir!"

print("\n[PASS] Kod 1 Minimal Deadline Takip Mekanizması Başarıyla Doğrulandı.")
```

### Kod 1 Çıktı Analizi ve Temel Bulgular

1. **Normal Periyot:** $t = 0\text{ ms}$, $t = 10\text{ ms}$ ve $t = 20\text{ ms}$ anlarında örnekler $10\text{ ms}$ aralıklarla gelmiş; $10\text{ ms} \le 12\text{ ms}$ şartı sağlandığı için hiçbir ihlal oluşmamıştır.
2. **İhlal Anı:** $t = 20\text{ ms}$ ile $t = 45\text{ ms}$ arasında $\Delta t = 25\text{ ms}$ fark oluşmuştur. İzin verilen azami sınır $12\text{ ms}$ olduğundan monitör derhal `total_count = 1` değerine yükselmiş ve alarm üretmiştir.
3. **Mühendislik Önemi:** Tüketici kodun içerisinde `sleep()` veya karmaşık zaman ölçüm döngüleri kurmaya gerek kalmamış; DDS altyapısı zaman aşımını otomatik olarak bildirmiştir.

## Kod 2 Mimarisi: Çok Anahtarlı (Multi-Instance) Bağımsız Deadline Motoru

Radar ve hava savunma sistemlerinde onlarca hava hedefi (`Track`) eşzamanlı izlenir:
- Dost savaş uçağı (`TRK_F16`) saniyede 50 defa konum bildirirken,
- Düşman seyir füzesi (`TRK_CRUISE`) elektronik harp (jamming) nedeniyle sinyal kaybedebilir.

### Mimari Özellikler:
- DDS `DeadlineQosPolicy`, topic genelinde tek bir kronometre tutmaz; **her bir `@key` (instance) için bağımsız bir zaman damgası** tutar.
- Kod 2, 3 farklı radar hedefini bağımsız zamanlayıcılarla koşturur; yalnızca sinyali kesilen hedefin deadline sayacını artırır.

```python
# ==============================================================================
# KOD 2: Çok Anahtarlı (Multi-Instance) Bağımsız Deadline Takip Motoru
# Amaç: Farklı anahtarlara (@key) sahip hedeflerin bağımsız süreölçerlerle
# denetlenmesini ve sinyali kesilen hedefin izole olarak yakalanmasını doğrulamak.
# ==============================================================================

from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class InstanceDeadlineState:
    last_update_ms: float
    missed_count: int = 0
    is_alive: bool = True

class MultiInstanceDeadlineEngine:
    def __init__(self, deadline_period_ms: float):
        self.deadline_period_ms = deadline_period_ms
        self.instances: Dict[str, InstanceDeadlineState] = {}

    def update_sample(self, track_id: str, current_time_ms: float):
        if track_id not in self.instances:
            self.instances[track_id] = InstanceDeadlineState(last_update_ms=current_time_ms)
        else:
            state = self.instances[track_id]
            delta_t = current_time_ms - state.last_update_ms
            if delta_t > self.deadline_period_ms:
                state.missed_count += 1
                state.is_alive = False
            else:
                state.is_alive = True
            state.last_update_ms = current_time_ms

    def check_deadlines_at(self, current_time_ms: float) -> List[str]:
        # Watchdog periyodik kontrolü (Veri gelmese bile süre doldu mu?)
        timed_out_tracks = []
        for tid, state in self.instances.items():
            if state.is_alive and (current_time_ms - state.last_update_ms > self.deadline_period_ms):
                state.missed_count += 1
                state.is_alive = False
                timed_out_tracks.append(tid)
        return timed_out_tracks

# 3 Hedefli Radar Simülasyonu (Deadline = 20.0 ms)
engine = MultiInstanceDeadlineEngine(deadline_period_ms=20.0)

# t = 0ms: 3 hedef de sisteme kaydolur
engine.update_sample("TRK_ALPHA", current_time_ms=0.0)
engine.update_sample("TRK_BRAVO", current_time_ms=0.0)
engine.update_sample("TRK_CHARLIE", current_time_ms=0.0)

# t = 15ms: TRK_ALPHA ve TRK_BRAVO güncellenir (Normal)
engine.update_sample("TRK_ALPHA", current_time_ms=15.0)
engine.update_sample("TRK_BRAVO", current_time_ms=15.0)

# t = 30ms: TRK_ALPHA güncellenir, TRK_CHARLIE hiç gelmez!
engine.update_sample("TRK_ALPHA", current_time_ms=30.0)

# t = 25ms anında Watchdog kontrolü: TRK_CHARLIE 25 ms'dir veri üretmedi (Deadline 20 ms)!
timed_out = engine.check_deadlines_at(current_time_ms=25.0)

print("[KOD 2] Çok Anahtarlı Deadline İzleme Durumu (t = 25 ms):")
print(f"  - Zaman Aşımına Uğrayan Hedefler: {timed_out} (Beklenen: ['TRK_CHARLIE'])")
for tid, state in engine.instances.items():
    print(f"  - {tid:<12} -> Son Görülme: {state.last_update_ms:4.1f}ms, Missed Count: {state.missed_count}, Canlı Mı: {state.is_alive}")

assert timed_out == ["TRK_CHARLIE"], "Yalnızca TRK_CHARLIE zaman aşımına uğramalıdır!"
assert engine.instances["TRK_ALPHA"].missed_count == 0
assert engine.instances["TRK_BRAVO"].missed_count == 0
assert engine.instances["TRK_CHARLIE"].missed_count == 1

print("\n[PASS] Çok Anahtarlı Deadline Takip Motoru %100 Başarıyla Doğrulandı.")
```

### Kod 2 Derinlemesine Analiz: Per-Instance İzolasyon ve Watchdog Mekanizması

1. **Watchdog ve Proaktif Denetim:** DDS'te okuyucunun deadline kaçırmasını fark etmesi için yeni bir paketin gelmesi **şart değildir**! Arka planda çalışan bir DDS zamanlayıcı iş parçacığı (Timer Thread / Watchdog), son güncellemeden bu yana $T_{\text{requested}}$ süresi geçtiğinde reaktif olarak `on_requested_deadline_missed` olayını fırlatır.
2. **Kritik İzolasyon:** `TRK_ALPHA`'nın yüksek frekansta veri göndermeye devam etmesi, sinyali kesilen `TRK_CHARLIE`'nin gizlenmesine neden olmamıştır. Radar komuta kontrol ekranı, `TRK_CHARLIE` hedefini anında "KAYIP / İZ SİLİNDİ" durumuna çekebilir.

## Kod 3 Mimarisi: RxO Deadline Matrisi Simülatörü

Deadline politikası bir **RxO (Offered vs Requested)** politikasıdır.
- **Kural:** $\text{Offered.period} \le \text{Requested.period}$.
- Üretici tüketiciye "en az tüketicinin istediği kadar sık" veri sağlamak zorundadır.
- Kod 3, 5 farklı yaygın süre kombinasyonunu test ederek DDS keşif eşleşme matrisini üretir.

```python
# ==============================================================================
# KOD 3: RxO Deadline Eşleşme Matrisi Simülatörü
# Amaç: Offered.period <= Requested.period kuralının tüm kombinasyonlarda
# doğru çalıştığını ve uyumsuz periyotların reddedildiğini doğrulamak.
# ==============================================================================

periods = [5, 10, 20, 50, 100] # milisaniye cinsinden periyotlar
rxo_deadline_matrix = {}

pass_count = 0
fail_count = 0

for off in periods:
    for req in periods:
        # Kural: Offered <= Requested
        compatible = (off <= req)
        rxo_deadline_matrix[(off, req)] = compatible
        if compatible:
            pass_count += 1
        else:
            fail_count += 1

print("[KOD 3] DDS Deadline RxO Uyumluluk Matrisi (Offered <= Requested):")
header_cols = " | ".join([f"{p}ms".ljust(6) for p in periods])
print(f"{'Offered \\ Requested':<20} | {header_cols}")
print("-" * 65)

for off in periods:
    row_str = f"{off}ms{'':<16} | "
    for req in periods:
        res = "PASS" if rxo_deadline_matrix[(off, req)] else "FAIL"
        row_str += f"{res:<6} | "
    print(row_str)

print(f"\nToplam Test Edilen İkili : {len(rxo_deadline_matrix)}")
print(f"Uyumlu (PASS)            : {pass_count} (Beklenen: 15)")
print(f"Uyumsuz (FAIL)           : {fail_count} (Beklenen: 10)")

assert pass_count == 15
assert fail_count == 10
assert rxo_deadline_matrix[(10, 20)] is True  # 10ms sunan, 20ms isteyeni doyurur
assert rxo_deadline_matrix[(50, 10)] is False # 50ms sunan, 10ms isteyene yetemez!

print("\n[PASS] Deadline RxO Eşleşme Matrisi %100 Başarıyla Doğrulandı.")
```

### Kod 3 Çıktı Analizi ve Boyutlandırma Kuralı

1. **Alt Üçgen Kuralı:** Toplam 25 durumdan 15 tanesi uyumludur. Eşitlik durumunda ($10\text{ ms} \le 10\text{ ms}$) eşleşme sağlanır.
2. **Tersine Hiyerarşi:** Durability ve Reliability'de "daha büyük değer" (RELIABLE > BEST_EFFORT) güçlüyken, Deadline'da **"daha küçük süre"** daha güçlü ve zorlayıcıdır!
3. **Mühendislik Tavsiyesi:** Sahada jitter (zamanlama dalgalanması) nedeniyle gereksiz alarmlar almamak için okuyucu deadline süresi daima yazar periyodundan %20 - %30 daha gevşek tutulmalıdır:

$$T_{\text{requested}} \ge 1.3 \times T_{\text{offered}}$$

## Kod 4 Mimarisi: Hata Enjeksiyonu ve Savunma Dayanıklılık Testleri

Savunma sistemlerinde Deadline ihlalleri ölümcül kazalara yol açabilir. Bu senaryoda 3 kritik hata enjekte edilir:
- **Test A (Zamanlama Jitter'ı):** Ağ gecikmesi ve işletim sistemi zamanlayıcı dalgalanması ($10\text{ ms} \pm 5\text{ ms}$) nedeniyle anlık deadline ihlallerinin tespiti.
- **Test B (Sensör Donması ve Fail-Safe / Dead Reckoning Modu):** Sensör tamamen sustuğunda uçuş bilgisayarının kaçırılan deadline uyarısıyla otomatik olarak ataletsel kestirim (Dead Reckoning) moduna geçmesi.
- **Test C (RxO Uyumsuzluğu Reddi):** $50\text{ ms}$ ile yayınlayan kameranın $20\text{ ms}$ bekleyen görüntü işleme düğümü tarafından reddedilmesi.

```python
# ==============================================================================
# KOD 4: Hata Enjeksiyonu (Fault Injection) ve Savunma Dayanıklılık Testleri
# Senaryolar:
#   Test A: Ağ Jitter'ı Nedeniyle Deadline İhlali
#   Test B: Donan Sensör Karşısında Otomatik Fail-Safe (Dead Reckoning) Tetikleme
#   Test C: RxO Uyumsuzluğunun Reddedilmesi
# ==============================================================================

class DefenseFlightControlNode:
    def __init__(self, requested_deadline_ms: float):
        self.requested_deadline_ms = requested_deadline_ms
        self.control_mode = "NORMAL_SENSOR_FEED"
        self.missed_deadlines = 0
        self.last_packet_time_ms = 0.0

    def receive_telemetry(self, current_time_ms: float, is_valid: bool):
        delta = current_time_ms - self.last_packet_time_ms
        if delta > self.requested_deadline_ms:
            self.missed_deadlines += 1
            # FAIL-SAFE KORUMASI: 2 ardışık deadline kaçarsa otopilot kestirime geçer
            if self.missed_deadlines >= 2:
                self.control_mode = "FAILSAFE_DEAD_RECKONING"
                print(f"[FAILSAFE AKTİF] Otopilot DEAD RECKONING moduna geçti! (Delta: {delta:.1f}ms)")
        else:
            self.missed_deadlines = 0 # Sıfırla
            self.control_mode = "NORMAL_SENSOR_FEED"

        self.last_packet_time_ms = current_time_ms

# TEST A & B: Sensör Donması ve Fail-Safe Doğrulama
node = DefenseFlightControlNode(requested_deadline_ms=15.0)

# Normal akış: t=0, 10, 20
node.receive_telemetry(0.0, True)
node.receive_telemetry(10.0, True)
node.receive_telemetry(20.0, True)
assert node.control_mode == "NORMAL_SENSOR_FEED"

# Sensör donar: t=40 (20 ms aralık -> 1. ihlal), t=65 (25 ms aralık -> 2. ihlal)
node.receive_telemetry(40.0, True)
assert node.missed_deadlines == 1
assert node.control_mode == "NORMAL_SENSOR_FEED"

node.receive_telemetry(65.0, True)
print(f"[TEST B] Fail-Safe Durumu: {node.control_mode} (Kaçırılan: {node.missed_deadlines})")
assert node.missed_deadlines == 2
assert node.control_mode == "FAILSAFE_DEAD_RECKONING", "2. ihlalde fail-safe aktifleşmelidir!"

# TEST C: RxO Uyumsuzluğu
class EndpointMatcher:
    @staticmethod
    def match(offered_deadline: float, requested_deadline: float) -> bool:
        if offered_deadline > requested_deadline:
            raise ValueError(f"INCOMPATIBLE_QOS: Offered ({offered_deadline}ms) > Requested ({requested_deadline}ms)")
        return True

rxo_failed = False
try:
    EndpointMatcher.match(offered_deadline=50.0, requested_deadline=20.0)
except ValueError as ex:
    rxo_failed = True
    print(f"\n[TEST C] RxO Hatası Başarıyla Yakalandı: {ex}")

assert rxo_failed, "Yavaş yazar hızlı okuyucu ile eşleşemez!"

print("\n[PASS] 3 Kritik Savunma Güvenliği Testi Başarıyla Geçti.")
```

### Kod 4 Hata Triage ve Saha Çözümleri

| Hata Kodu / Belirti | Kök Neden (Root Cause) | Saha Sonucu | Kıdemli Mühendis Çözümü |
|---|---|---|---|
| **Yanlış Alarm (`Spurious Deadline Missed`)** | `Requested.period` değerinin yazar periyoduna çok yakın ($10.0\text{ ms} \to 10.1\text{ ms}$) ayarlanması | Ağdaki mikro-jitter nedeniyle sistem sürekli alarm üretir. | Okuyucu toleransını en az %20 - %30 güvenlik payıyla ayarlamak ($13 - 15\text{ ms}$). |
| **`INCOMPATIBLE_QOS`** | Yazar süresi okuyucu süresinden büyük ($T_O > T_R$) | Düğümler eşleşmez, telemetri hiç akmaz. | Sistem QoS konfigürasyon şemasında veri kaynağı frekansını teyit etmek. |
| **Sessiz Sensör Arızası** | Deadline tanımlanmaması | Sensör sustuğunda uçuş bilgisayarı son açıyı sabit sanarak çakılır. | Her kritik sensör konusuna mutlaka `DeadlineQosPolicy` tanımlamak. |

## Kod 5 Mimarisi: 50,000 Paketlik Uçuş Kontrol Jitter ve Deadline Kıyaslaması (Benchmark)

Bu yüksek hacimli kıyaslamada:
- 100 Hz ($10\text{ ms}$) nominal frekansta çalışan bir Uçuş Kontrol Bilgisayarı (FCC) modellenir.
- Gerçekçi Linux RT-Preempt ve Ethernet gecikmelerini modellemek için paketler arasına Gauss dağılımlı jitter eklenir:

$$\Delta t \sim \mathcal{N}(\mu = 10.0\text{ ms}, \sigma = 2.0\text{ ms})$$

- 50,000 paketlik ardışık akışta 3 farklı okuyucu deadline toleransı test edilir:
  1. **Sıkı Tolerans:** $T_R = 11.0\text{ ms}$ ($\mu + 0.5\sigma$)
  2. **Dengeli Tolerans:** $T_R = 13.0\text{ ms}$ ($\mu + 1.5\sigma$)
  3. **Gevşek / Savunma Standardı Tolerans:** $T_R = 16.0\text{ ms}$ ($\mu + 3.0\sigma$)
- Her profil için kaçırılan deadline oranı ve yanlış alarm sayısı ölçülür.

```python
# ==============================================================================
# KOD 5: 50,000 Paketlik Uçuş Kontrol Jitter ve Deadline Kıyaslaması
# Amaç: Farklı Requested Deadline toleranslarında (11ms, 13ms, 16ms)
# kaçırılan deadline sayısını ve yanlış alarm oranını ölçmek.
# ==============================================================================

import numpy as np

NUM_SAMPLES = 50000
MEAN_PERIOD_MS = 10.0
STD_DEV_MS = 1.8 # Gerçekçi ağ ve scheduling jitter'ı

np.random.seed(42)
intervals = np.random.normal(MEAN_PERIOD_MS, STD_DEV_MS, NUM_SAMPLES)
# Fiziksel kısıt: zaman farkı negatif olamaz
intervals = np.maximum(intervals, 1.0)

test_deadlines = [11.0, 13.0, 16.0]
benchmark_results = {}

for dl in test_deadlines:
    missed_count = int(np.sum(intervals > dl))
    miss_rate_pct = (missed_count / NUM_SAMPLES) * 100.0
    benchmark_results[dl] = {
        "missed": missed_count,
        "rate_pct": miss_rate_pct
    }

print("[KOD 5] 50,000 Örnekli Uçuş Kontrol Jitter ve Deadline İstatistikleri:")
for dl, res in benchmark_results.items():
    print(f"\n--- Requested Deadline = {dl:.1f} ms ---")
    print(f"  - Kaçırılan Paket Sayısı : {res['missed']:,} / {NUM_SAMPLES:,}")
    print(f"  - Deadline İhlal Oranı   : %{res['rate_pct']:.2f}")

assert benchmark_results[11.0]["missed"] > benchmark_results[13.0]["missed"]
assert benchmark_results[13.0]["missed"] > benchmark_results[16.0]["missed"]
assert benchmark_results[16.0]["rate_pct"] < 1.0, "3-Sigma toleransında ihlal %1'in altında olmalıdır!"

print("\n[PASS] 50,000 Paketlik Uçuş Kontrol Benchmark Testi Başarıyla Tamamlandı.")
```

### Kod 5 Bulguları ve 3-Sigma Boyutlandırma Kuralı

1. **Sıkı Tolerans Felaketi ($11\text{ ms}$):** Ortalaması $10\text{ ms}$ olan bir sistemde okuyucu deadline değeri $11\text{ ms}$ seçildiğinde, sistem normal çalışmasına rağmen paketlerin **%28.9'u** deadline kaçırmış gibi algılanır. Bu durum kontrol odasını sahte alarmlarla boğar.
2. **3-Sigma Savunma Standardı ($16\text{ ms}$):** 

$$T_{\text{deadline}} = \mu + 3\sigma = 10.0 + 3(1.8) = 15.4\text{ ms} \implies 16.0\text{ ms}$$

Tolerans $16\text{ ms}$ seçildiğinde yanlış alarm oranı **%0.05** seviyesine düşmüştür. Gerçek bir sensör kopması yaşandığında sistem en geç $16\text{ ms}$ içinde bunu %100 doğrulukla yakalar.

## Gerçek Dünya Savunma ve Havacılık Uygulamaları

| Sistem / Alt Bileşen | Nominal Frekans | Deadline Ayarı | İhlal Durumundaki Eylem |
|---|---|---|---|
| **Füze Ataletsel Navigasyon (IMU)** | $1000\text{ Hz}$ ($1\text{ ms}$) | $1.5\text{ ms}$ | Güdüm bilgisayarı ikincil (yedek) IMU sensörüne geçer. |
| **İHA Uçuş Kontrol Yüzeyleri** | $100\text{ Hz}$ ($10\text{ ms}$) | $15.0\text{ ms}$ | Otopilot otomatik seviyeleme ve acil süzülüş modunu açar. |
| **Hava Savunma Radar Takip** | $20\text{ Hz}$ ($50\text{ ms}$) | $75.0\text{ ms}$ | Hedef ekranında iz "Kayıp / Manevra Tahmini" rengine döner. |
| **Kokpit Heartbeat / Watchdog** | $2\text{ Hz}$ ($500\text{ ms}$) | $800.0\text{ ms}$ | Ana ekran "MISSION COMPUTER OFFLINE" kırmızı uyarısı basar. |

## Kod 6 Mimarisi: 4-Panelli Master Görselleştirme Paneli

Bu görselleştirme paneli, DDS Deadline politikasını 4 temel mühendislik perspektifinden modeller:
- **Panel 1 (Zaman Dalga Formu):** Normal Örnekler vs Deadline İhlali ve Watchdog Alarm Tetiklenmesi.
- **Panel 2 (Çok Anahtarlı Radar Takip):** TRK_ALPHA (Aktif), TRK_BRAVO (Aktif) ve TRK_CHARLIE (Zaman Aşımı) Durumu.
- **Panel 3 (RxO Eşleşme Isı Haritası):** 5x5 Offered vs Requested Deadline Eşleşme Matrisi.
- **Panel 4 (Jitter Dağılımı ve 3-Sigma):** Gauss Jitter Eğrisi ve Deadline Eşiklerinin Karşılaştırması.

```python
# ==============================================================================
# KOD 6: 4-Panelli Master Görselleştirme Paneli (Publication-Quality Artifact)
# Amaç: Deadline mekanizmasını, per-instance takibini,
# RxO matrisini ve 50,000 örnekli jitter istatistiklerini belgelemek.
# ==============================================================================

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# PNG dosya yolu belirleme (Dizin garantili)
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_207_qos_deadline.png")
    except Exception:
        PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_207/gun_207_qos_deadline.png"

# Koyu Tema ve Tipografi Ayarları
plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.grid(True, linestyle='--', alpha=0.3, color='#64748B')
    ax.tick_params(colors='#E2E8F0', labelsize=10)
    for spine in ax.spines.values():
        spine.set_color('#475569')

# ------------------------------------------------------------------------------
# PANEL 1: Deadline Zaman Dalga Formu ve Alarm Tetiklenmesi
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. DDS Deadline İzleme Dalga Formu ve Watchdog Alarmı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

t_points = [0, 10, 20, 45, 55]
y_vals = [1, 1, 1, 1, 1]

ax1.plot([0, 60], [1, 1], color='#475569', linestyle='--', linewidth=1.5)
ax1.scatter([0, 10, 20, 55], [1, 1, 1, 1], color='#10B981', s=250, label='Zamanında Gelen Örnek', zorder=5)
ax1.scatter([45], [1], color='#EF4444', s=350, marker='X', label='Deadline İhlali Sonrası Örnek', zorder=6)

# Deadline Eşik Çizgisi
ax1.axvline(x=32, color='#F59E0B', linestyle=':', linewidth=2, label='Deadline Eşiği (t = 20 + 12 = 32ms)')
ax1.annotate("Requested Deadline Missed!\n(Delta = 25ms > 12ms)", xy=(32, 1), xytext=(22, 1.4),
             arrowprops=dict(facecolor='#EF4444', shrink=0.08, width=2, headwidth=7),
             color='#FCA5A5', fontweight='bold', fontsize=9)

ax1.set_xlim(-5, 65)
ax1.set_ylim(0.5, 1.8)
ax1.set_xlabel("Zaman (Milisaniye)", color='#E2E8F0', fontsize=10)
ax1.set_yticks([])
ax1.legend(loc='lower left', facecolor='#1E293B', edgecolor='#475569', labelcolor='#E2E8F0')

# ------------------------------------------------------------------------------
# PANEL 2: Çok Anahtarlı (Per-Instance) Radar Takip Durumu
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. Çok Anahtarlı Radar Takip Deadline İzolasyonu (Per-Instance)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

tracks = ['TRK_ALPHA (F-16)', 'TRK_BRAVO (İHA)', 'TRK_CHARLIE (Füze)']
last_seen = [30.0, 15.0, 0.0]
status_cols = ['#10B981', '#10B981', '#EF4444']
labels = ['CANLI (0 ihlal)', 'CANLI (0 ihlal)', 'ZAMAN AŞIMI (1 ihlal)']

y_idx = np.arange(len(tracks))
bars = ax2.barh(y_idx, [30, 25, 25], color=['#0284C7', '#0284C7', '#7F1D1D'], alpha=0.6, edgecolor='white')

for i, (trk, col, lbl) in enumerate(zip(tracks, status_cols, labels)):
    ax2.text(1, i, f"{trk} -> {lbl}", color=col, fontweight='bold', va='center', fontsize=10)

ax2.axvline(x=20, color='#F59E0B', linestyle='--', linewidth=2, label='Deadline Limiti (20 ms)')
ax2.set_yticks(y_idx)
ax2.set_yticklabels(['', '', ''])
ax2.set_xlabel("Geçen Süre (ms)", color='#E2E8F0', fontsize=10)
ax2.legend(loc='lower right', facecolor='#1E293B', edgecolor='#475569', labelcolor='#E2E8F0')

# ------------------------------------------------------------------------------
# PANEL 3: 5x5 RxO Deadline Matrisi Isı Haritası
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. DDS Deadline RxO Matrisi (Offered <= Requested)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

periods_ticks = ["5ms", "10ms", "20ms", "50ms", "100ms"]
matrix_m = np.zeros((5, 5))
for i, off in enumerate([5, 10, 20, 50, 100]):
    for j, req in enumerate([5, 10, 20, 50, 100]):
        matrix_m[i, j] = 1 if off <= req else 0

ax3.imshow(matrix_m, cmap='RdYlGn', vmin=0, vmax=1.2, aspect='auto')
ax3.set_xticks(range(5))
ax3.set_yticks(range(5))
ax3.set_xticklabels(periods_ticks, color='#E2E8F0', fontsize=9)
ax3.set_yticklabels(periods_ticks, color='#E2E8F0', fontsize=9)
ax3.set_xlabel("Requested Deadline (DataReader)", color='#E2E8F0', fontsize=10)
ax3.set_ylabel("Offered Deadline (DataWriter)", color='#E2E8F0', fontsize=10)

for i in range(5):
    for j in range(5):
        txt = "PASS" if matrix_m[i, j] == 1 else "FAIL"
        col = "black" if matrix_m[i, j] == 1 else "white"
        ax3.text(j, i, txt, ha='center', va='center', color=col, fontweight='bold', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 4: 50,000 Paketlik Jitter Dağılımı ve Eşik Analizi
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. 50,000 Paketlik Uçuş Kontrol Jitter Dağılımı ve 3-Sigma Eşiği", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

counts, bins, _ = ax4.hist(intervals, bins=60, color='#6366F1', alpha=0.75, edgecolor='#4338CA', density=True)

ax4.axvline(x=10.0, color='#38BDF8', linestyle='-', linewidth=2, label='Nominal (10ms)')
ax4.axvline(x=11.0, color='#EF4444', linestyle='--', linewidth=2, label='Sıkı Eşik: 11ms (%28 İhlal)')
ax4.axvline(x=13.0, color='#F59E0B', linestyle='--', linewidth=2, label='Dengeli Eşik: 13ms (%4 İhlal)')
ax4.axvline(x=16.0, color='#10B981', linestyle='-', linewidth=2.5, label='3-Sigma Eşik: 16ms (%0.05 İhlal)')

ax4.set_xlabel("İki Paket Arasındaki Süre (ms)", color='#E2E8F0', fontsize=10)
ax4.set_ylabel("Olasılık Yoğunluğu", color='#E2E8F0', fontsize=10)
ax4.legend(loc='upper right', facecolor='#1E293B', edgecolor='#475569', labelcolor='#E2E8F0', fontsize=9)

plt.tight_layout()
plt.savefig(PNG_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

# Üretilen PNG Dosya Boyutu Kontrolü
file_size_bytes = os.path.getsize(PNG_FILE)
file_size_kb = file_size_bytes / 1024.0

print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {PNG_FILE}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'nin üzerinde olmalıdır!"
```

### Görselleştirme Paneli Derinlemesine Analizi

- **Panel 1 (Zaman Dalga Formu):** $t = 20\text{ ms}$'den sonra beklenen $12\text{ ms}$ sınırında ($t = 32\text{ ms}$) paket gelmeyince Watchdog anında tetiklenmiş; $t = 45\text{ ms}$ anında gecikmeli gelen paket kırmızı ile işaretlenmiştir.
- **Panel 2 (Çok Anahtarlı İzolasyon):** `TRK_ALPHA` ve `TRK_BRAVO` sağlıklı seyrine devam ederken, $20\text{ ms}$ boyunca sinyal üretmeyen `TRK_CHARLIE` izole edilerek kırmızı hata durumuna düşürülmüştür.
- **Panel 3 (RxO Matrisi):** 15 yeşil ve 10 kırmızı hücre, Offered süresinin Requested süresinden daima küçük veya eşit olması gerektiğini belgeler.
- **Panel 4 (Jitter ve Eşik):** Gauss eğrisinde $11\text{ ms}$ eşiğinin alanın büyük kısmını kestiği (%28 yanlış alarm), buna karşın $16\text{ ms}$ ($3\sigma$) eşiğinin yalnızca gerçek anomalileri filtrelediği net biçimde görülmektedir.

## Öz Değerlendirme ve Mülakat Soruları

### Soru 1 (Junior Seviye): DataReader'ın Deadline süresi DataWriter'ın Deadline süresinden küçük olabilir mi?
**Cevap:** Hayır, olamaz! DDS RxO kuralına göre $\text{Offered} \le \text{Requested}$ olmalıdır. Eğer yazar $20\text{ ms}$ sözü verirken okuyucu $10\text{ ms}$ beklerse, okuyucu daha ilk andan itibaren sürekli deadline kaçıracaktır. DDS bu uyumsuzluğu keşif anında tespit eder ve eşleşmeyi reddeder (`REQUESTED_INCOMPATIBLE_QOS`).

### Soru 2 (Senior Seviye): `on_offered_deadline_missed` ile `on_requested_deadline_missed` arasındaki fark nedir?
**Cevap:** 
- `on_offered_deadline_missed`: Yayıncı düğümün kendi CPU'su, thread havuzu veya sensör sürücüsü kilitlendiği için söz verdiği periyotta `write()` çağıramadığında yayıncı tarafında tetiklenir.
- `on_requested_deadline_missed`: Yayıncı veriyi zamanında gönderse bile ağda paket kaybolursa veya yayıncı çökerse abone tarafında tetiklenir.

### Soru 3 (Staff/Principal Seviye): Aviyonik bir sistemde Deadline süresi belirlenirken ağ gecikmesi ve işletim sistemi jitter'ı nasıl hesaba katılmalıdır?
**Cevap:** Nominal periyot $\mu$ ve toplam zamanlama standart sapması $\sigma$ (Linux scheduling jitter + network jitter) ölçülmelidir. Okuyucu deadline süresi en az $T_{\text{requested}} = \mu + 3\sigma$ (tercihen $\mu + 4\sigma$ veya nominal sürenin %130 - %150'si) olarak seçilmelidir. Bu formül, yanlış alarmları (false positives) matematiksel olarak %0.13'ün altına düşürürken, gerçek bir donma durumunda en kötü senaryoda $T_{\text{requested}}$ içinde fail-safe mekanizmasının devreye girmesini garanti eder.

## Sık Yapılan Hatalar ve Savunma Sanayii Pratikleri

### ❌ Anti-Pattern 1: Deadline'ı Nominal Periyoda Birebir Eşit Ayarlamak
100 Hz ($10.0\text{ ms}$) çalışan bir sensör için hem yazar hem okuyucu deadline'ını tam $10.0\text{ ms}$ yapmak. Tek bir mikrosaniyelik işletim sistemi gecikmesinde bile okuyucu sahte alarm üretir.
- **Doğru Yaklaşım:** Okuyucu deadline değerine her zaman bir güvenlik marjı eklenmelidir ($13.0 - 15.0\text{ ms}$).

### ❌ Anti-Pattern 2: Deadline Alarmını Yalnızca Loglamak (Eylemsizlik)
`on_requested_deadline_missed` tetiklendiğinde ekrana yalnızca uyarı basıp uçuş kontrol döngüsünü eski bayat veriyle çalıştırmaya devam etmek.
- **Doğru Yaklaşım:** Deadline kaçtığında sistem derhal durum makinesini (FSM) güncellemeli; sensörü "Geçersiz" işaretleyerek yedek sensöre veya Dead Reckoning moduna geçmelidir.

### ❌ Anti-Pattern 3: Liveliness ile Deadline'ı Karıştırmak
Deadline her bir veri örneğinin geliş sıklığını ölçer. Liveliness ise düğümün genel olarak "yaşayıp yaşamadığını" (heartbeat) denetler. Bir düğüm yaşıyor olabilir ama sensör thread'i kilitlendiği için veri üretemiyor olabilir; bunu yalnızca **Deadline** yakalar.

## Gün Sonu Özeti ve Gelecek Konu Önizlemesi

Bugün, gerçek zamanlı dağıtık sistemlerde verinin zamanında teslimini garanti altına alan **Deadline QoS** politikasını inceledik:
1. $\text{Offered.period} \le \text{Requested.period}$ RxO kuralını ve 5x5 uyumluluk matrisini doğruladık.
2. Çok anahtarlı (Multi-Instance) radar hedef takip motorunda sinyali kesilen hedefin diğer hedeflerden bağımsız olarak izole edildiğini test ettik.
3. 50,000 örnekli Gauss jitter deneyinde $3\sigma$ kuralıyla sahte alarmları sıfıra indirdik ve fail-safe durum geçişini doğruladık.

### Yarın (GÜN 208): `QoS: liveliness`
Yarın, ağdaki düğümlerin ve yazarların hayatta olup olmadığını (canlılık durumunu) denetleyen **Liveliness** QoS politikasını; `AUTOMATIC` ve `MANUAL_BY_TOPIC` modellerini, kiralama sürelerini (`lease_duration`) ve ölü düğüm tespit mekanizmalarını inceleyeceğiz.

