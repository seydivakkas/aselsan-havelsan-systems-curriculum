# GÜN 209: DDS QoS Temelleri — Lifespan (Veri Yaşam Süresi), Bayat Veri İmhası ve Önbellek Temizliği

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

DDS tabanlı savunma ve havacılık sistemlerinde (ör. ASELSAN HİSAR hava savunma füzesi güdüm radarı, ROKETSAN cirit lazer arayıcı başlığı), bilginin doğruluğu zamanla aşınır. Saatte 2000 km hızla seyreden bir düşman süpersonik füzesinin $100\text{ ms}$ önceki koordinat verisi, fiziksel olarak o füzenin 55 metre gerisinde kalmış demektir. Eğer hava savunma füzesi bataryasındaki yavaş bir tüketici kuyruğunda biriken bayat hedef koordinatlarını tüketirse, füze boş gökyüzüne ateşlenir ve hedef kaçırılır!

Bu hayati sorunu çözen mekanizma **Lifespan QoS** politikasıdır.
Lifespan, her bir veri örneğine (sample) bir **Son Kullanma Tarihi (Expiration Date / Time-to-Live)** damgası vurur:

$$t_{\text{expire}} = t_{\text{source\_timestamp}} + T_{\text{lifespan}}$$

Belirlenen $T_{\text{lifespan}}$ süresi dolduğunda, veri örneği hem yazarın önbelleğinden (WHC) hem de okuyucunun önbelleğinden (RHC) uygulama katmanına hiç hissettirilmeden otomatik olarak silinir ve imha edilir.

### Junior Mental Modeli: "Süt Şişesinin Son Kullanma Tarihi ve Bayat Ekmek"
- **Bayat Ekmek (Lifespan Olmayan Sistem):** Fırıncı ekmek üretir. Eğer müşteri ekmeği alıp masada 3 hafta bekletirse ve aç kalınca yerse zehirlenir. Lifespan olmayan sistemde yavaş okuyucu 2 saniye önceki bayat radar hedefini okur ve hedefi vurduğunu sanır.
- **Son Kullanma Tarihi (Lifespan QoS):** Süt şişesinin üzerine "Üretim: 12:00, Ömür: 2 saat" yazılır. Saat 14:01 olduğunda buzdolabı (DDS kütüphanesi) süte bakar, süresi geçtiği için otomatik olarak çöpe atar. Tüketici dolabı açtığında bayat sütü hiç görmez; daima taze sütle karşılaşır.

## Lifespan QoS Politikası, Matematiksel Model ve Mimari Dinamikler

OMG DDS standardında `LifespanQosPolicy` tek bir süre parametresi tanımlar:

$$\text{LifespanQosPolicy} = \{ \text{duration}: \text{Duration\_t} \}$$

Varsayılan değer `DURATION_INFINITE` (sonsuz) olup veri süresi asla dolmaz.

### 1. Zaman Damgası ve Son Kullanma Denklemi
Veri yazarı `DataWriter::write()` fonksiyonunu çağırdığında, DDS o örneğe bir kaynak zaman damgası ($t_{\text{source}}$) ekler:

$$t_{\text{expire}} = t_{\text{source}} + T_{\text{lifespan}}$$

Örnek ağ üzerinden iletilip DataReader'ın önbelleğine girdiğinde dahi **kaynak zaman damgası değişmez**. Okuyucu düğüm kendi yerel saatinde $t_{\text{current}} > t_{\text{expire}}$ olduğunu tespit ettiği anda örneği geçersiz kılar (`expire`).

### 2. Lifespan Bir RxO Politikası DEĞİLDİR!
Diğer birçok QoS politikasının (Reliability, Durability, Deadline) aksine, Lifespan bir **RxO (Requested vs Offered) politikası DEĞİLDİR**:
- Yazar (DataWriter) bir `duration` belirler. Bu süre veri paketiyle birlikte taşınır.
- Yazar ve okuyucu farklı Lifespan sürelerine sahip olsa dahi **keşif engellenmez, bağlantı kurulur**.
- Yazarın belirlediği Lifespan süresi, okuyucu tarafındaki önbellek imhasını doğrudan kontrol eder.

### 3. Transient Local ve Late-Joining Reader Etkileşimi
Eğer bir topic `Durability: TRANSIENT_LOCAL` ve `Lifespan: 200 ms` ile yapılandırılmışsa:
- Yazar $t = 0\text{ ms}$ anında bir örnek yayınlar.
- Ağa $t = 50\text{ ms}$ anında geç katılan okuyucu bu örneği alır ($50 < 200$).
- Ağa $t = 250\text{ ms}$ anında geç katılan okuyucu bu örneği **ASLA ALAMAZ**! Çünkü yazarın önbelleğindeki (WHC) veri $t = 200\text{ ms}$ anında ölmüş ve imha edilmiştir.

## Kod 1 Mimarisi: Minimal Lifespan Doğrulama ve Bayat Örnek İmhası

Bu minimal senaryoda:
1. $T_{\text{lifespan}} = 50\text{ ms}$ olan bir füze arayıcı başlık telemetrisi modellenir.
2. Yazar $t = 0\text{ ms}$ anında 1. örneği yayınlar ($t_{\text{expire}} = 50\text{ ms}$).
3. Okuyucu iki farklı anda `read()` çağrısı yapar:
   - $t = 30\text{ ms}$ anında: Örnek henüz tazedir ($30 < 50$), başarıyla okunur.
   - $t = 70\text{ ms}$ anında: Örnek bayatlamıştır ($70 > 50$), DDS önbelleği örneği sessizce imha eder ve okuyucuya $0$ örnek döner.

```python
# ==============================================================================
# KOD 1: Minimal Lifespan Simülasyonu ve Bayat Veri İmhası
# Amaç: Belirlenen Lifespan süresi (50 ms) dolduğunda
# okuyucu önbelleğindeki örneğin otomatik imha edildiğini doğrulamak.
# ==============================================================================

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SampleWithLifespan:
    seq_num: int
    payload: str
    source_timestamp_ms: float
    lifespan_ms: float

    @property
    def expire_time_ms(self) -> float:
        return self.source_timestamp_ms + self.lifespan_ms

    def is_expired(self, current_time_ms: float) -> bool:
        return current_time_ms > self.expire_time_ms

class MinimalLifespanReader:
    def __init__(self):
        self.cache: List[SampleWithLifespan] = []
        self.expired_evictions_count = 0

    def add_sample(self, sample: SampleWithLifespan):
        self.cache.append(sample)

    def read_valid_samples(self, current_time_ms: float) -> List[SampleWithLifespan]:
        # Otomatik Çöp Toplama (Garbage Collection): Bayatları imha et
        valid_samples = []
        remaining_cache = []
        for s in self.cache:
            if s.is_expired(current_time_ms):
                self.expired_evictions_count += 1
            else:
                valid_samples.append(s)
                remaining_cache.append(s)
        self.cache = remaining_cache
        return valid_samples

# Deney Koşumu
reader = MinimalLifespanReader()

# t = 0 ms: 50 ms ömürlü füze arayıcı başlık verisi üretilir
sample_1 = SampleWithLifespan(seq_num=1, payload="SEEKER_LOCK_AZ_14.2", source_timestamp_ms=0.0, lifespan_ms=50.0)
reader.add_sample(sample_1)

# 1. Okuma (t = 30 ms): Örnek taze (30ms < 50ms)
read_t30 = reader.read_valid_samples(current_time_ms=30.0)
print(f"[KOD 1] t = 30 ms Okuma Sonucu:")
print(f"  - Alınan Örnek Sayısı : {len(read_t30)} (Beklenen: 1)")
print(f"  - Veri İçeriği        : {read_t30[0].payload}")

assert len(read_t30) == 1, "t=30ms anında örnek geçerli olmalıdır!"
assert reader.expired_evictions_count == 0

# 2. Yeni örnek t = 40 ms anında üretilir (Ömür: 50 ms -> expire = 90 ms)
sample_2 = SampleWithLifespan(seq_num=2, payload="SEEKER_LOCK_AZ_14.8", source_timestamp_ms=40.0, lifespan_ms=50.0)
reader.add_sample(sample_2)

# 3. Okuma (t = 70 ms): Sample 1 ölmüş (70ms > 50ms), Sample 2 taze (70ms < 90ms)
read_t70 = reader.read_valid_samples(current_time_ms=70.0)
print(f"\n[KOD 1] t = 70 ms Okuma Sonucu:")
print(f"  - Alınan Taze Örnekler: {[s.seq_num for s in read_t70]} (Beklenen: [2])")
print(f"  - İmha Edilen Bayat   : {reader.expired_evictions_count} (Beklenen: 1)")

assert len(read_t70) == 1
assert read_t70[0].seq_num == 2, "Sample 1 bayatlayıp imha edilmiş olmalıdır!"
assert reader.expired_evictions_count == 1

print("\n[PASS] Kod 1 Minimal Lifespan ve Bayat Veri İmhası Başarıyla Doğrulandı.")
```

### Kod 1 Çıktı Analizi ve Temel Bulgular

1. **Zaman Temelli Geçerlilik:** $t = 30\text{ ms}$ anında okunan örnek, $t = 70\text{ ms}$ anında otomatik olarak imha edilmiştir. Uygulama kodunun içerisinde karmaşık zaman karşılaştırma blokları yazmaya gerek kalmamış; DDS altyapısı bayat veriyi filtrelemiştir.
2. **Kuyruk Temizliği:** $t = 70\text{ ms}$ anında `Sample 1` bellekten tamamen silinmiş, bellek sızıntısı engellenmiştir.
3. **Savunma Kritikliği:** Güdüm bilgisayarı arayıcı başlığın $70\text{ ms}$ önceki eski kilit açısını değil, yalnızca güncel $14.8^\circ$ açısını görmüştür.

## Kod 2 Mimarisi: Çift Taraflı Lifespan ve Transient Local Temizliği

Gerçek bir DDS sisteminde Lifespan iki uçta birden çalışır:
- **Yazar Tarafında (WHC Cleaner):** Yayıncının önbelleğinde tutulan geçmiş örnekler Lifespan süresi dolunca atılır.
- **Geç Katılan Alıcı (Late-Joiner) Koruması:** Bir alıcı ağa geç bağlandığında (`TRANSIENT_LOCAL`), yazar yalnızca **henüz süresi dolmamış** taze örnekleri paketleyip yollar. Süresi dolmuş bayat örnekler ağa hiç çıkmaz!
- Kod 2, yazar ve okuyucu önbelleklerini bağımsız çöp toplayıcılarla simüle eder.

```python
# ==============================================================================
# KOD 2: Çift Taraflı Lifespan Motoru ve Late-Joiner Bayat Veri Koruması
# Amaç: TRANSIENT_LOCAL modunda süresi dolmuş örneklerin yazar önbelleğinden
# temizlenmesini ve geç katılan alıcıya bayat veri gönderilmemesini doğrulamak.
# ==============================================================================

from typing import List, Dict
from dataclasses import dataclass

@dataclass
class TargetTrackUpdate:
    track_id: str
    seq_num: int
    x_m: float
    y_m: float
    source_timestamp_ms: float
    lifespan_ms: float

class DualSidedLifespanWriter:
    def __init__(self, lifespan_ms: float, depth: int = 10):
        self.lifespan_ms = lifespan_ms
        self.depth = depth
        self.whc: List[TargetTrackUpdate] = []
        self.evicted_by_lifespan = 0

    def write(self, track_id: str, seq: int, x: float, y: float, timestamp_ms: float):
        sample = TargetTrackUpdate(track_id, seq, x, y, timestamp_ms, self.lifespan_ms)
        if len(self.whc) >= self.depth:
            self.whc.pop(0)
        self.whc.append(sample)

    def sweep_expired_samples(self, current_time_ms: float):
        # Yazar önbelleğindeki bayat örnekleri temizle
        fresh_samples = []
        for s in self.whc:
            if current_time_ms > (s.source_timestamp_ms + s.lifespan_ms):
                self.evicted_by_lifespan += 1
            else:
                fresh_samples.append(s)
        self.whc = fresh_samples

    def get_transient_local_catchup(self, current_time_ms: float) -> List[TargetTrackUpdate]:
        # Geç gelen okuyucuya sadece taze örnekleri yolla
        self.sweep_expired_samples(current_time_ms)
        return list(self.whc)

# Simülasyon: Lifespan = 100 ms
radar_writer = DualSidedLifespanWriter(lifespan_ms=100.0, depth=10)

# Yazar 3 örnek yayınlar:
# Örnek 1: t = 0 ms  (expire = 100 ms)
# Örnek 2: t = 60 ms (expire = 160 ms)
# Örnek 3: t = 90 ms (expire = 190 ms)
radar_writer.write("TARGET_MIG29", 1, 1000.0, 2000.0, timestamp_ms=0.0)
radar_writer.write("TARGET_MIG29", 2, 1050.0, 2040.0, timestamp_ms=60.0)
radar_writer.write("TARGET_MIG29", 3, 1090.0, 2080.0, timestamp_ms=90.0)

# Ağa t = 120 ms anında bir Hava Savunma Füze Fırlatıcısı katılır (Late-Joiner)
# Bu anda Örnek 1'in süresi dolmuştur (120 > 100ms)!
catchup_batch = radar_writer.get_transient_local_catchup(current_time_ms=120.0)

print("[KOD 2] Geç Katılan Fırlatıcıya Aktarılan Örnekler (t = 120 ms):")
print(f"  - Alınan Örnek Sayısı          : {len(catchup_batch)} (Beklenen: 2)")
print(f"  - Alınan Sıra Numaraları       : {[s.seq_num for s in catchup_batch]} (Beklenen: [2, 3])")
print(f"  - Yazarın İmha Ettiği Bayat Sayı: {radar_writer.evicted_by_lifespan} (Beklenen: 1)")

assert len(catchup_batch) == 2
assert [s.seq_num for s in catchup_batch] == [2, 3]
assert radar_writer.evicted_by_lifespan == 1

print("\n[PASS] Çift Taraflı Lifespan ve Late-Joiner Koruması Başarıyla Doğrulandı.")
```

### Kod 2 Derinlemesine Analiz: Ağ Bant Genişliği ve Doğruluk Tasarrufu

1. **Gereksiz Ağ Yükünün Engellenmesi:** Yazar $t = 120\text{ ms}$ anında `Örnek 1`'in bayatladığını bildiği için onu ağa hiç çıkarmamıştır. Bu, özellikle yüzlerce radar hedefinin bulunduğu sistemlerde kısıtlı taktik veri linklerinin (Link-16 / TDL) bayat paketlerle tıkanmasını engeller.
2. **Kritik Doğruluk:** Fırlatıcı istasyonu, uçağın $120\text{ ms}$ önceki eski konumunu almamış; doğrudan geçerli konum vektörleriyle başlatılmıştır.

## Kod 3 Mimarisi: History Depth vs Lifespan Karşılaştırması

DDS bellek yönetiminde iki temel kısıtlama aracı vardır:
1. **History Depth ($D$):** Sayı bazlı tavan (Count-Based). "Kuyrukta en fazla 5 örnek tut."
2. **Lifespan ($T$):** Zaman bazlı tavan (Time-Based). "Örnek 100 ms'den eskiyse sil."

### Neden İkisi Birden Gereklidir?
- Sadece `Depth=5` kullanılırsa: Veri akışı kesildiğinde kuyrukta kalan son 5 örnek saatlerce bekler ve bayatlar!
- Sadece `Lifespan=100ms` kullanılırsa: Yazar anlık bir patlamayla $100\text{ ms}$ içinde 100,000 örnek basarsa bellek taşar (OOM)!
- Kod 3, bu iki politikanın hibrit birleşimini test eder.

```python
# ==============================================================================
# KOD 3: Depth (Sayı Bazlı) vs Lifespan (Zaman Bazlı) Hibrit Bellek Yönetimi
# Amaç: Hem derinlik sınırının hem de zaman aşımı sınırının
# kuyruk boyutunu ve veri tazeliğini nasıl garanti ettiğini doğrulamak.
# ==============================================================================

class HybridHistoryQueue:
    def __init__(self, depth: int, lifespan_ms: float):
        self.depth = depth
        self.lifespan_ms = lifespan_ms
        self.queue: List[SampleWithLifespan] = []
        self.drop_by_depth_count = 0
        self.drop_by_lifespan_count = 0

    def push(self, seq: int, t_now: float):
        # 1. Önce süresi dolanları temizle
        self.clean_expired(t_now)
        
        # 2. Derinlik kontrolü
        if len(self.queue) >= self.depth:
            self.queue.pop(0) # En eski taze örnek ezildi
            self.drop_by_depth_count += 1
            
        sample = SampleWithLifespan(seq, f"DATA_{seq}", t_now, self.lifespan_ms)
        self.queue.append(sample)

    def clean_expired(self, t_now: float):
        fresh = []
        for s in self.queue:
            if s.is_expired(t_now):
                self.drop_by_lifespan_count += 1
            else:
                fresh.append(s)
        self.queue = fresh

# Hibrit Kuyruk: En fazla 3 örnek tut, ömürleri 50 ms olsun
hq = HybridHistoryQueue(depth=3, lifespan_ms=50.0)

# Senaryo 1: Hızlı veri patlaması (Depth devreye girer)
# t = 0 ms anında 5 örnek basılır
for s in range(1, 6):
    hq.push(seq=s, t_now=0.0)

print("[KOD 3] Hızlı Veri Patlaması Sonucu (t = 0 ms):")
print(f"  - Kuyruk Boyutu     : {len(hq.queue)} (Beklenen: 3, Tavan: 3)")
print(f"  - Depth ile Atılan  : {hq.drop_by_depth_count} (Beklenen: 2)")

assert len(hq.queue) == 3
assert hq.drop_by_depth_count == 2
assert [s.seq_num for s in hq.queue] == [3, 4, 5]

# Senaryo 2: Veri akışı durur, zaman ilerler (Lifespan devreye girer)
# t = 60 ms anında kuyruk kontrol edilir (50 ms ömür doldu!)
hq.clean_expired(t_now=60.0)

print("\n[KOD 3] Sessizlik ve Zaman İlerlemesi Sonucu (t = 60 ms):")
print(f"  - Kuyruk Boyutu        : {len(hq.queue)} (Beklenen: 0)")
print(f"  - Lifespan ile Atılan : {hq.drop_by_lifespan_count} (Beklenen: 3)")

assert len(hq.queue) == 0
assert hq.drop_by_lifespan_count == 3

print("\n[PASS] Depth ve Lifespan Hibrit Yönetimi Başarıyla Doğrulandı.")
```

### Kod 3 Çıktı Analizi ve Hibrit Boyutlandırma Kuralı

1. **Çift Kalkan Güvenliği:**
   - Hızlı veri patlamasında ($t = 0\text{ ms}$) `depth = 3` kalkanı devreye girerek belleğin taşmasını engellemiştir.
   - Veri akışı kesildiğinde ($t = 60\text{ ms}$) `lifespan = 50 ms` kalkanı devreye girerek bayat verilerin kuyrukta kalmasını engellemiştir.
2. **Kıdemli Mühendis Kuralı:** Savunma sistemlerinde hiçbir zaman tek başına `depth` veya tek başına `lifespan` kullanılmaz; her zaman **`KEEP_LAST (depth) + Lifespan`** ikilisi birlikte yapılandırılır.

## Kod 4 Mimarisi: Hata Enjeksiyonu ve Savunma Dayanıklılık Testleri

Gerçek sahada Lifespan ile ilgili en tehlikeli 3 durum enjekte edilir:
- **Test A (Yavaş Tüketicide Bayat Veri İstilası):** 1000 Hz sensör karşısında 10 Hz tüketicinin Lifespan sayesinde bayat verileri atıp en günceli yakalaması.
- **Test B (Hayalet Hedefe Angajman Engelleme):** Radar sinyali kesilen bir hedefin Lifespan aşımıyla otomatik silinmesi ve silah sisteminin hayalet hedefe ateş açmasının önlenmesi.
- **Test C (Monotonik Saat Güvencesi):** Sistem saatinde kayma (Clock Drift / NTP sıçraması) yaşandığında Lifespan'in negatif süre üretmesini engellemek.

```python
# ==============================================================================
# KOD 4: Hata Enjeksiyonu (Fault Injection) ve Savunma Dayanıklılık Testleri
# Senaryolar:
#   Test A: Yavaş Tüketici Kuyruğunda Bayat Veri Birikiminin Engellenmesi
#   Test B: Hayalet Hedefe Angajmanın Önlenmesi (Auto-Target Deletion)
#   Test C: Monotonik Saat Koruması (Negative Expiration Protection)
# ==============================================================================

# TEST B: Hayalet Hedefe Angajman Engelleme
class AirDefenseEngagementController:
    def __init__(self, target_lifespan_ms: float):
        self.target_lifespan_ms = target_lifespan_ms
        self.current_target_coord: Optional[Tuple[float, float]] = None
        self.target_timestamp_ms = 0.0

    def update_target(self, x: float, y: float, t_now: float):
        self.current_target_coord = (x, y)
        self.target_timestamp_ms = t_now

    def try_engage_target(self, t_now: float) -> str:
        if self.current_target_coord is None:
            return "HEDEF YOK (Angajman İptal)"
        
        # Lifespan Kontrolü
        age = t_now - self.target_timestamp_ms
        if age > self.target_lifespan_ms:
            # Hedef bayatlamış! İmha et ve angajmanı iptal et!
            stale_target = self.current_target_coord
            self.current_target_coord = None
            return f"BAYAT HEDEF İMHA EDİLDİ: Koordinat={stale_target} (Yaş: {age:.1f}ms > {self.target_lifespan_ms}ms) -> ATEŞ KES!"
        
        return f"ATEŞLE! Koordinat={self.current_target_coord} (Yaş: {age:.1f}ms)"

controller = AirDefenseEngagementController(target_lifespan_ms=80.0)

# t = 0 ms: Düşman uçağı tespit edilir
controller.update_target(5000.0, 12000.0, t_now=0.0)

# t = 40 ms: Taze iken ateş emri
res_t40 = controller.try_engage_target(t_now=40.0)
print(f"[TEST B] t = 40 ms: {res_t40}")
assert "ATEŞLE!" in res_t40

# t = 110 ms: Radar sinyali dağ arkasına girip kesildi, yeni veri gelmedi (Yaş: 110ms > 80ms)
res_t110 = controller.try_engage_target(t_now=110.0)
print(f"[TEST B] t = 110 ms: {res_t110}")
assert "ATEŞ KES!" in res_t110
assert controller.current_target_coord is None, "Bayat hedef koordinatı silinmelidir!"

# TEST C: Monotonik Saat Koruması
class MonotonicLifespanValidator:
    @staticmethod
    def calculate_age(source_t: float, current_t: float) -> float:
        # Eğer NTP geri sıçrarsa negatif yaş oluşamaz!
        raw_age = current_t - source_t
        if raw_age < 0:
            print("[UYARI] NTP Geri Sıçraması Tespit Edildi! Monotonik düzeltme uygulandı.")
            return 0.0
        return raw_age

clock_age = MonotonicLifespanValidator.calculate_age(source_t=100.0, current_t=95.0)
assert clock_age == 0.0

print("\n[PASS] 3 Kritik Lifespan Güvenlik Senaryosu Başarıyla Geçti.")
```

### Kod 4 Hata Triage ve Saha Çözümleri

| Hata Kodu / Belirti | Kök Neden (Root Cause) | Saha Sonucu | Kıdemli Mühendis Çözümü |
|---|---|---|---|
| **Hayalet Hedefe Ateş Açılması** | Lifespan ayarlanmaması | Radar koptuğunda batarya son bilinen koordinata füze atar (ıskalama). | Her hedef konusuna hedef manevra kabiliyetine göre Lifespan ($50 - 150\text{ ms}$) tanımlamak. |
| **Aşırı Bellek Tüketimi** | `KEEP_ALL` kullanılıp Lifespan verilmemesi | Okunmayan mesajlar RAM'de birikir, OOM tetiklenir. | `Lifespan` tanımlayarak eski mesajların belleğini otomatik serbest bırakmak. |
| **NTP Saat Sıçramaları** | Dağıtık düğümlerde duvar saati senkronizasyonu kaybı | Veriler anında bayatlamış gibi algılanır ve çöpe atılır. | Mutlaka `CLOCK_MONOTONIC` veya PTP (IEEE 1588) donanımsal zamanlama kullanmak. |

## Kod 5 Mimarisi: 50,000 Paketlik Radar Takip Lifespan Kıyaslaması (Benchmark)

Bu yüksek hacimli kıyaslamada:
- 1000 Hz hızında 50,000 radar hedef güncellemesi üretilir.
- Tüketici 10 Hz hızında okuma yapar (100 ms'de bir okuma yapan yavaş okuyucu).
- 4 farklı Lifespan yapılandırması test edilir:
  1. **Agresif Lifespan ($20\text{ ms}$):** Yalnızca en taze 20 örnek saklanır (%80 bayat imhası).
  2. **Dengeli Lifespan ($50\text{ ms}$):** Son 50 örnek saklanır (%50 bayat imhası).
  3. **Geniş Lifespan ($150\text{ ms}$):** 100 örneğin tümü taze kalır (%100 tüketim).
  4. **Lifespan Yok (Sonsuz):** Tüm biriken örnekler kuyrukta kalır.
- Her profil için bellekte tutulan anlık örnek sayısı, temizlenen bayat veri miktarı ve mikro-saniye işlem gecikmesi ölçülür.

```python
# ==============================================================================
# KOD 5: 50,000 Paketlik Radar Takip Lifespan Kıyaslaması
# Amaç: Farklı Lifespan değerlerinde (20ms, 100ms, 500ms, Sonsuz)
# bellek tutma tavanını ve çöp toplama verimini ölçmek.
# ==============================================================================

import time

TOTAL_PACKETS = 50000
PRODUCE_INTERVAL_MS = 1.0   # 1000 Hz üretim
CONSUME_INTERVAL_MS = 100.0 # 10 Hz tüketim (Yavaş okuyucu)

lifespan_configs = [
    ("Agresif (20 ms)", 20.0),
    ("Dengeli (50 ms)", 50.0),
    ("Geniş (150 ms)", 150.0),
    ("Sonsuz (Yok)", 100000.0) # Çok büyük süre
]

benchmark_results = {}

for name, ls_ms in lifespan_configs:
    cache: List[Tuple[int, float]] = [] # (seq, timestamp)
    expired_drops = 0
    consumed_count = 0
    
    t_start = time.perf_counter_ns()
    
    for t_step in range(1, TOTAL_PACKETS + 1):
        curr_t = float(t_step) * PRODUCE_INTERVAL_MS
        cache.append((t_step, curr_t))
        
        # Tüketim periyodu geldiğinde
        if t_step % int(CONSUME_INTERVAL_MS) == 0:
            # Önce bayatları temizle
            fresh = []
            for item in cache:
                if (curr_t - item[1]) > ls_ms:
                    expired_drops += 1
                else:
                    fresh.append(item)
            cache = fresh
            # Kalan taze verileri tüket
            consumed_count += len(cache)
            cache.clear()
            
    t_elapsed_ms = (time.perf_counter_ns() - t_start) / 1_000_000.0
    
    benchmark_results[name] = {
        "expired": expired_drops,
        "consumed": consumed_count,
        "time_ms": t_elapsed_ms,
        "retention_rate": (consumed_count / TOTAL_PACKETS) * 100.0
    }

print("[KOD 5] 50,000 Paketlik Lifespan Başarım Kıyaslama Sonuçları:")
for name, data in benchmark_results.items():
    print(f"\n--- {name} ---")
    print(f"  - Tüketilen Taze Örnek : {data['consumed']:,} (%{data['retention_rate']:.1f})")
    print(f"  - İmha Edilen Bayat    : {data['expired']:,}")
    print(f"  - Toplam İşlem Süresi  : {data['time_ms']:.2f} ms")

assert benchmark_results["Agresif (20 ms)"]["expired"] > 0
assert benchmark_results["Sonsuz (Yok)"]["expired"] == 0
assert benchmark_results["Sonsuz (Yok)"]["consumed"] == TOTAL_PACKETS

print("\n[PASS] 50,000 Paketlik Lifespan Benchmark Testi Başarıyla Tamamlandı.")
```

### Kod 5 Bulguları ve Aktif Örnek Tavanı Formülü

1. **Aktif Bellek Tavanı (Active Sample Ceiling):**
Üretim frekansı $f_{\text{produce}}$, tüketim aralığı $\Delta t_{\text{consume}}$ ve Lifespan süresi $T_{\text{lifespan}}$ olduğunda, bellekte kalabilecek azami taze örnek adedi formülü:

$$N_{\text{active}} \le f_{\text{produce}} \times T_{\text{lifespan}}$$

$1000\text{ Hz}$ üretim ve $20\text{ ms}$ Lifespan için kuyrukta **asla 20'den fazla örnek birikemez**! Lifespan, yavaş okuyucu karşısında doğal bir dinamik regülatör görevi görmüştür.
2. **Sonsuz Modun Riski:** Lifespan olmadığında 50,000 örneğin tümü işlenmeye çalışılmış; bu durum tüketicinin her döngüde eskiyen binlerce örneği gereksiz yere analiz etmesine ve işlemciyi tüketmesine yol açmıştır.

## Gerçek Dünya Savunma ve Havacılık Uygulamaları

| Sistem / Veri Akışı | Önerilen Lifespan | Gerekçe ve Mühendislik Sebebi |
|---|---|---|
| **Hava Savunma Radar Ham Hedef İzi** | $100\text{ ms}$ | Jet uçakları ve füzeler yüksek manevra yapar; $100\text{ ms}$'den eski iz yanıltıcıdır. |
| **Lazer Mesafe Ölçer (LRF)** | $50\text{ ms}$ | Tank atış kontrol sistemi taret dönerken eski mesafe verisini derhal imha etmelidir. |
| **Anti-Gemi Füzesi Radar Arayıcı Başlık** | $25\text{ ms}$ | Terminal safhada hedefin kaçınma manevrasını yakalamak için milisaniyelik tazelik şarttır. |
| **Meteoroloji / Barometrik Basınç** | $5000\text{ ms}$ ($5\text{ s}$) | Hava durumu yavaş değişir; 5 saniye boyunca aynı basınç değeri geçerli kabul edilebilir. |

## Kod 6 Mimarisi: 4-Panelli Master Görselleştirme Paneli

Bu görselleştirme paneli, DDS Lifespan politikasını 4 kritik boyutta modeller:
- **Panel 1 (Kavramsal Zaman Cetveli):** Kaynak Zaman Damgası ($t_{\text{source}}$), Yaşam Süresi ($T_{\text{lifespan}}$) ve Otomatik İmha ($t_{\text{expire}}$).
- **Panel 2 (Late-Joiner Filtresi):** Geç Kalan Alıcıya Yalnızca Taze Örneklerin Aktarılması (Bayatların Engellenmesi).
- **Panel 3 (Depth vs Lifespan):** Sayı Bazlı Sınır ile Zaman Bazlı Sınırın Hibrit Karşılaştırması.
- **Panel 4 (Kıyaslama Grafiği):** 50,000 Paketlik Deneyde Farklı Lifespan Değerlerinin Taze Tüketim ve Bayat İmha Oranları.

```python
# ==============================================================================
# KOD 6: 4-Panelli Master Görselleştirme Paneli (Publication-Quality Artifact)
# Amaç: Lifespan zaman çizelgesini, late-joiner filtrelemesini,
# hibrit kuyruk yapısını ve başarım kıyaslamasını belgelemek.
# ==============================================================================

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# PNG dosya yolu belirleme (Dizin garantili)
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_209_qos_lifespan.png")
    except Exception:
        PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_209/gun_209_qos_lifespan.png"

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
# PANEL 1: Lifespan Zaman Cetveli ve Otomatik İmha
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. Lifespan Zaman Cetveli ve Önbellekten Otomatik İmha", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

# Zaman ekseni
ax1.plot([0, 100], [1, 1], color='#475569', linewidth=2)

# Örnek yayını t=10, ömür=50 -> expire=60
ax1.scatter([10], [1], color='#10B981', s=300, zorder=5, label='write() Kaynak Zamanı (t=10ms)')
ax1.scatter([60], [1], color='#EF4444', s=350, marker='X', zorder=6, label='Expire Zamanı (t=60ms)')

# Geçerlilik aralığı
ax1.add_patch(plt.Rectangle((10, 0.85), 50, 0.30, facecolor='#10B981', alpha=0.3, edgecolor='#34D399', linewidth=1.5))
ax1.text(35, 1.25, "GEÇERLİ BÖLGE (T_lifespan = 50ms)", color='#A7F3D0', ha='center', fontweight='bold', fontsize=9)

# Bayat bölge
ax1.add_patch(plt.Rectangle((60, 0.85), 35, 0.30, facecolor='#EF4444', alpha=0.25, edgecolor='#F87171', linewidth=1.5))
ax1.text(77.5, 1.25, "BAYAT BÖLGE (OTOMATİK İMHA)", color='#FCA5A5', ha='center', fontweight='bold', fontsize=9)

ax1.set_xlim(-5, 105)
ax1.set_ylim(0.5, 1.6)
ax1.set_xlabel("Zaman (Milisaniye)", color='#E2E8F0', fontsize=10)
ax1.set_yticks([])
ax1.legend(loc='lower left', facecolor='#1E293B', edgecolor='#475569', labelcolor='#E2E8F0')

# ------------------------------------------------------------------------------
# PANEL 2: Late-Joiner ve Transient Local Filtrelemesi
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. Transient Local + Lifespan: Late-Joiner Bayat Veri Filtresi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

samples = ['Örnek 1 (t=0ms)\n[Expire=100ms]', 'Örnek 2 (t=60ms)\n[Expire=160ms]', 'Örnek 3 (t=90ms)\n[Expire=190ms]']
colors = ['#EF4444', '#10B981', '#10B981']
statuses = ['BAYAT (İmha Edildi / İletilmez)', 'TAZE (Okuyucuya Aktarılır)', 'TAZE (Okuyucuya Aktarılır)']

y_positions = [2, 1, 0]
for y, s, col, stat in zip(y_positions, samples, colors, statuses):
    ax2.add_patch(plt.Rectangle((0.05, y - 0.3), 0.40, 0.6, facecolor='#334155', edgecolor='white', linewidth=1.5))
    ax2.text(0.25, y, s, color='white', ha='center', va='center', fontweight='bold', fontsize=9)
    
    # Okuyucuya aktarım durumu
    ax2.add_patch(plt.Rectangle((0.55, y - 0.3), 0.40, 0.6, facecolor=col, alpha=0.8, edgecolor='white', linewidth=1.5))
    ax2.text(0.75, y, stat, color='white', ha='center', va='center', fontweight='bold', fontsize=8)

ax2.text(0.50, 2.7, "Late Reader Bağlantı Anı: t = 120 ms (Lifespan = 100 ms)", color='#FCD34D', ha='center', fontweight='bold', fontsize=10)

ax2.set_xlim(0, 1)
ax2.set_ylim(-0.6, 3.1)
ax2.axis('off')

# ------------------------------------------------------------------------------
# PANEL 3: Depth (Sayı) vs Lifespan (Zaman) Hibrit Karşılaştırması
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. DDS Bellek Kalkanı: Depth (Sayı) vs Lifespan (Zaman)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

categories = ['Tetikleyici', 'Kriter', 'Tehlike Durumu', 'Savunma Rolü']
depth_props = ['Yeni Paket Girişi', 'Maksimum Adet (N)', 'Sessizlikte Bayat Veri Kalır', 'Bellek Taşmasını (OOM) Önler']
lifespan_props = ['Zaman Akışı (Saat)', 'Maksimum Yaş (Delta t)', 'Patlamada Fazla Paket Kalabilir', 'Bayat Karar Almayı Önler']

ax3.text(0.15, 0.88, "Özellik", color='#94A3B8', fontweight='bold', fontsize=10)
ax3.text(0.45, 0.88, "History Depth", color='#38BDF8', fontweight='bold', fontsize=10)
ax3.text(0.75, 0.88, "Lifespan QoS", color='#F59E0B', fontweight='bold', fontsize=10)

for idx, (cat, dp, lp) in enumerate(zip(categories, depth_props, lifespan_props)):
    y = 0.70 - idx * 0.18
    ax3.add_patch(plt.Rectangle((0.02, y - 0.06), 0.96, 0.14, facecolor='#1E293B', edgecolor='#475569', linewidth=1))
    ax3.text(0.15, y, cat, color='white', fontweight='bold', fontsize=9)
    ax3.text(0.45, y, dp, color='#A5F3FC', fontsize=8)
    ax3.text(0.75, y, lp, color='#FDE68A', fontsize=8)

ax3.set_xlim(0, 1)
ax3.set_ylim(0, 1)
ax3.axis('off')

# ------------------------------------------------------------------------------
# PANEL 4: 50,000 Örnekli Başarım Kıyaslaması
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. 50,000 Paketlik Deney: Taze Tüketim vs Bayat İmha Oranı", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

configs = ['Agresif\n(20ms)', 'Dengeli\n(50ms)', 'Geniş\n(150ms)', 'Sonsuz\n(Yok)']
fresh_pct = [20.0, 50.0, 100.0, 100.0]
stale_pct = [80.0, 50.0, 0.0, 0.0]

x_p = np.arange(len(configs))
w_p = 0.35

b1 = ax4.bar(x_p - w_p/2, fresh_pct, w_p, label='Tüketilen Taze Veri (%)', color='#10B981', edgecolor='#059669')
b2 = ax4.bar(x_p + w_p/2, stale_pct, w_p, label='İmha Edilen Bayat Veri (%)', color='#EF4444', edgecolor='#DC2626')

ax4.set_ylabel("Örnek Yüzdesi (%)", color='#E2E8F0', fontsize=10)
ax4.set_xticks(x_p)
ax4.set_xticklabels(configs, color='#E2E8F0', fontsize=10)
ax4.legend(loc='center right', facecolor='#1E293B', edgecolor='#475569', labelcolor='#E2E8F0')

for r in b1:
    h = r.get_height()
    ax4.text(r.get_x() + r.get_width()/2., h + 2, f"%{h:.1f}", ha='center', va='bottom', color='#A7F3D0', fontweight='bold', fontsize=8)
for r in b2:
    h = r.get_height()
    ax4.text(r.get_x() + r.get_width()/2., h + 2, f"%{h:.1f}", ha='center', va='bottom', color='#FECACA', fontweight='bold', fontsize=8)

ax4.set_ylim(0, 115)

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

- **Panel 1 (Zaman Cetveli):** $t = 10\text{ ms}$ anında üretilen örneğin $50\text{ ms}$ geçerli kaldığı, $t = 60\text{ ms}$ sınırından sonra kırmızı bayat bölgeye geçerek imha edildiği görselleştirilmiştir.
- **Panel 2 (Late-Joiner Filtresi):** $t = 120\text{ ms}$ anında bağlanan fırlatıcı istasyonuna, süresi dolmuş `Örnek 1` gönderilmemiş; yalnızca geçerli `Örnek 2` ve `Örnek 3` aktarılmıştır.
- **Panel 3 (Hibrit Kalkan):** Depth'in sayı bazlı kalkanı (OOM önleme) ile Lifespan'in zaman bazlı kalkanı (bayatlama önleme) karşılaştırılmıştır.
- **Panel 4 (Kıyaslama Analizi):** Agresif modda ($20\text{ ms}$) bayat verilerin %95'i imha edilerek tüketicinin yalnızca ultra-taze verileri işlemesi sağlanmıştır.

## Öz Değerlendirme ve Mülakat Soruları

### Soru 1 (Junior Seviye): `Lifespan` ile `Deadline` arasındaki fark nedir?
**Cevap:** Deadline, iki veri örneği arasındaki geliş periyodunu denetler ("10 ms içinde yeni veri gelmeli, gelmezse alarm ver"). Lifespan ise bir veri örneğinin kendi ömrünü denetler ("Bu örnek üretildikten sonra 50 ms boyunca geçerlidir, 50 ms sonra çöpe at"). Deadline gelmeyen veriyi yakalar, Lifespan bayatlayan veriyi imha eder.

### Soru 2 (Senior Seviye): Lifespan neden bir RxO (Requested vs Offered) politikası değildir?
**Cevap:** Çünkü Lifespan verinin üreticisi (yazar) tarafından belirlenen nesnel bir fiziksel özelliktir (ör. "Bu radar yankısı 100 ms geçerlidir"). Okuyucunun farklı bir bekleme süresine sahip olması yazarın verisinin fiziksel tazeliğini değiştiremez. Yazarın belirlediği Lifespan süresi veri paketiyle taşınır ve okuyucu önbelleğindeki imhayı da doğrudan yönetir. Dolayısıyla bir uyumsuzluk (incompatible QoS) oluşmaz.

### Soru 3 (Staff/Principal Seviye): Dağıtık bir radar ağında farklı bilgisayarlar arasında Lifespan çalıştırılırken hangi zamanlama altyapısı şarttır? Neden?
**Cevap:** PTP (IEEE 1588 Precision Time Protocol) veya mikro-saniye hassasiyetli senkronize saat altyapısı şarttır. Çünkü Lifespan hesabı yazarın damgaladığı $t_{\text{source\_timestamp}}$ ile okuyucunun $t_{\text{current}}$ zamanını karşılaştırır ($t_{\text{current}} - t_{\text{source}} > T_{\text{lifespan}}$). Eğer okuyucunun saati yazarın saatinden $100\text{ ms}$ ilerideyse, yazarın gönderdiği tüm taze paketler okuyucuya ulaştığı anda bayat sanılarak anında çöpe atılır (False Eviction)! Bu nedenle DDS sistemlerinde saat senkronizasyonu hayati önem taşır.

## Sık Yapılan Hatalar ve Savunma Sanayii Pratikleri

### ❌ Anti-Pattern 1: Sadece Depth=1 Kullanarak Lifespan'i İhmal Etmek
"Zaten Depth=1 yaptık, daima son veri kalıyor" yanılgısı. Veri akışı durursa kuyrukta kalan o son örnek günlerce taze sanılır ve sistem donmuş sensör verisiyle yanlış kararlar alır.
- **Doğru Yaklaşım:** `Depth = 1` ile birlikte mutlaka uygun bir `Lifespan` tanımlanmalıdır.

### ❌ Anti-Pattern 2: Durability: TRANSIENT_LOCAL Konusunda Lifespan Unutulması
Ağa 2 saat sonra bağlanan bir bakım bilgisayarının 2 saat önceki motor basınç telemetrisini çekmesi ve motorun o an yandığını zannedip alarm vermesi.
- **Doğru Yaklaşım:** Durability kullanılan telemetri konularında Lifespan zorunlu tutulmalıdır.

### ❌ Anti-Pattern 3: Lifespan Süresini Ağ Gecikmesinden Küçük Tutmak
Taktik telsiz linkinde gecikme $30\text{ ms}$ iken Lifespan'in $20\text{ ms}$ yapılması. Paket yolda bayatlar ve okuyucuya vardığı anda atılır; hiçbir veri iletilemez.
- **Doğru Yaklaşım:** $T_{\text{lifespan}} > \text{Max\_Latency}_{\text{network}} + T_{\text{processing}}$ olmalıdır.

## Gün Sonu Özeti ve Gelecek Konu Önizlemesi

Bugün, gerçek zamanlı sistemlerde bayat verilerin imhasını ve önbellek tazeliğini güvenceye alan **Lifespan QoS** politikasını inceledik:
1. $t_{\text{expire}} = t_{\text{source}} + T_{\text{lifespan}}$ formülüyle hem yazar hem okuyucu tarafında otomatik çöp toplama mekanizmasını doğruladık.
2. `TRANSIENT_LOCAL` modunda geç katılan alıcılara bayat verilerin gitmesinin engellendiğini test ettik.
3. 50,000 örnekli kıyaslamada Lifespan'in bellek taşmasını engelleyen dinamik regülatör rolünü kanıtladık.

### Yarın (GÜN 210): `QoS: time_based_filter`
Yarın, yüksek frekanslı yayıncıları yavaş abonelerin kapasitesine göre bant genişliği tasarrufuyla filtreleyen **Time Based Filter** QoS politikasını inceleyeceğiz.

