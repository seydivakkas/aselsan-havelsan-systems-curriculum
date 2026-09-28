# GÜN 197: OMG DDS Standardı: Veri Odaklı (Data-Centric) Yaklaşım ve Küresel Veri Alanı (Global Data Space) Mimarisi

**Faz 6:** DDS / ROS2 / Gazebo (Dağıtık Robotik Sistemler, Eşler Arası Ağlar ve Simülasyon)  
**Ön Koşul:** Gün 196 — Dağıtık Sistemlerde Yayıncı/Abone (Pub/Sub) Paradigması ve Ayrışma Problemi  
**Sonraki Adım:** Gün 198 — DomainParticipant: DDS Varlık Hiyerarşisi ve Domain İzolasyonu  
**Hedef Sektör:** HAVELSAN (ADVENT Savaş Yönetim Sistemi, Denizaltı Entegre Komuta Kontrol), ASELSAN (HİSAR, SİPER, KORKUT Hava Savunma Sistemleri), BAYKAR & TUSAŞ (Sürü İHA Görev Ağı)

---

### Müfredat Bilgileri ve Tasarım Kararı
Geleneksel mesajlaşma aracıları (Message Brokers: RabbitMQ, Kafka, ActiveMQ) **Mesaj Odaklıdır (Message-Centric)**: Ağ, üzerinden geçen baytların anlamını bilmez; taşıdığı veriyi opak bir siyah kutu (opaque byte array) olarak görür. Tüm veri ayrıştırma, filtreleme, durum takibi ve yaşam döngüsü yönetimi uç noktalardaki uygulamaların sırtına yüklenir.

**OMG DDS (Data Distribution Service)** ise tamamen devrimsel bir paradigma olan **Veri Odaklılığı (Data-Centricity / DCPS)** getirir:
1. **Küresel Veri Alanı (Global Data Space - GDS):** Ağın kendisi, tüm dağıtık düğümlerin erişebildiği devasa, sanal, eşler arası (P2P) ve bellek-içi (in-memory) bir veritabanı gibi davranır.
2. **Tipli ve Anahtarlı Veri (Keyed Topics & Instances):** DDS arayüz tanımlama dili (OMG IDL) sayesinde verinin şemasını bilir. Tıpkı bir SQL tablosundaki Primary Key gibi bir `@key` alanı tanımlanarak (Örn: `uint32_t track_id`), tek bir Topic üzerinde yüzlerce bağımsız **Veri Nesnesi (Data Instance)** hayat döngüleriyle birlikte eşzamanlı yönetilir.
3. **Önbellek Durumu ve Yaşam Döngüsü:** Düğümler "mesaj göndermez"; küresel veri alanındaki nesneleri `write()` ile günceller, nesne silindiğinde `dispose()` eder. Ağ katmanı, hangi hedefin hayatta olduğunu (`ALIVE`), hangisinin imha edildiğini (`NOT_ALIVE_DISPOSED`) çalışma anında bilir.

```
+----------------------------------------------------------------------------------------------------+
|               MESAJ ODAKLI (MESSAGE-CENTRIC) VS VERİ ODAKLI (DATA-CENTRIC DDS) MİMARİ              |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [ 1. MESAJ ODAKLI MODEL: OPAK BORU ]               [ 2. VERİ ODAKLI DDS MODELİ: GLOBAL DATA SPACE]|
|                                                                                                    |
|   Yayıncı (App)              Abone (App)              Düğüm A (Radar)            Düğüm B (Füze C2) |
|   +-----------+              +-----------+            +-------------+            +---------------+ |
|   | Uygulama  |              | Uygulama  |            | DataWriter  |            |  DataReader   | |
|   | Mantığı   |              | Mantığı   |            +-------------+            +---------------+ |
|   +-----------+              +-----------+                   |                           ^         |
|         |                          ^                         v (write / update)          | (read)  |
|         v                          |               =============================================   |
|   +--------------------------------------+         KÜRESEL VERİ ALANI (GLOBAL DATA SPACE - GDS)    |
|   | OPAK BORU / BROKER (Opak Bayt Dizisi)|         (Dağıtık Bellek-İçi Veritabanı / Paylaşımlı Durum)|
|   | [ 0xEF, 0x12, 0xAA, ... (Anlamsız) ] |         +-------------------------------------------+   |
|   +--------------------------------------+         | Topic: "RadarTrack"                       |   |
|                                                    | - Instance #101: Pos(X,Y,Z), ALIVE        |   |
|   * Ağ verinin anlamını bilmez.                    | - Instance #102: Pos(X,Y,Z), ALIVE        |   |
|   * Filtreleme ve durum takibi yapılamaz.          | - Instance #103: DISPOSED (İmha Edildi)   |   |
|   * Her iki uç da şemayı elle parse eder.          +-------------------------------------------+   |
|                                                    =============================================   |
|                                                    * Ağ verinin tipini, key'ini ve durumunu bilir. |
|                                                    * Sadece değişen nesneler eşler arası akar.    |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

> **Tasarım Kararı:** Savaş yönetim sistemlerinde (CMS) saniyede binlerce radar izi güncellenir. Bir füze komutanı tüm radar mesajlarını tek tek okuyup içini parse etmekle vakit kaybedemez; doğrudan `RadarTrack` tablosunda `threat_level > 4` olan hedeflerin son durumunu sorgulayabilmelidir. Bu nedenle askeri C4ISR ve aviyonik omurgalarda tartışmasız tek standart **OMG DDS**'tir.

## 1.1 Mesaj Odaklı vs Veri Odaklı Paradigma: Keyed Topics & Instances

Dağıtık sistem tasarımında zihinsel sıçrama yaratan en kritik ayrım şudur:

### 1. Mesaj Odaklı Düşünce (RPC / Message Queue)
- Odak noktası **eylemdir (Verb / Action)**: *"Bu paketi alıcıya ulaştır."*
- Ağ bir boru hattıdır (Pipe). Borunun içinden geçen verinin ne olduğu ağ katmanını ilgilendirmez.
- Geçmiş durum tutulmaz; abone bağlantıyı kaçırırsa veriyi kaybeder.

### 2. Veri Odaklı Düşünce (Data-Centric / DDS)
- Odak noktası **verinin durumudur (Noun / State)**: *"Hava sahasındaki hedeflerin güncel koordinatları ve durumları nelerdir?"*
- Ağ, tüm makinelerin RAM'ine yayılmış sanal bir ilişkisel veritabanıdır.
- **Konu (Topic):** Bir veri tablosuna karşılık gelir (`RadarTrack`).
- **Anahtar (Key):** Bir tablonun Primary Key'idir. IDL dosyasında `@key` ile işaretlenir:
  ```idl
  struct RadarTrack {
      @key unsigned long track_id; // Benzersiz hedef kimliği
      double x;
      double y;
      double z;
      float speed_mach;
      octet threat_level;
  };
  ```
- **Örnek (Instance):** Her benzersiz `track_id` değeri (Örn: `track_id = 101` ve `track_id = 102`) bağımsız bir **Veri Örneğidir (Data Instance)**.
- **Örnekleme (Sample):** Bir nesnenin belirli bir andaki koordinat güncellemesidir.

```python
# Kod Hücresi 1: Veri Odaklı Küresel Veri Alanı (Global Data Space) ve Keyed Instance Simülatörü
import time
from enum import Enum

class InstanceState(Enum):
    ALIVE = 1               # Nesne aktif olarak güncelleniyor
    NOT_ALIVE_DISPOSED = 2  # Nesne imha edildi / silindi
    NOT_ALIVE_NO_WRITERS = 3# Nesneyi yazan kaynak kapandı / koptu

class DataSample:
    """DDS Örnekleme Verisi ve Örnek Bilgisi (SampleInfo)"""
    def __init__(self, data_dict, instance_state=InstanceState.ALIVE):
        self.data = data_dict
        self.state = instance_state
        self.source_timestamp = time.perf_counter()

class GlobalDataSpace:
    """DDS Küresel Veri Alanı: Topic ve Key tabanlı Dağıtık Bellek Veritabanı"""
    def __init__(self, topic_name, key_field_name):
        self.topic_name = topic_name
        self.key_field = key_field_name
        # key_value -> list of DataSample (History)
        self.instances = {}

    def write(self, data_dict):
        """Instance Güncellemesi (Tıpkı SQL UPDATE/INSERT gibi)"""
        key_val = data_dict[self.key_field]
        if key_val not in self.instances:
            self.instances[key_val] = []
        sample = DataSample(data_dict, InstanceState.ALIVE)
        self.instances[key_val].append(sample)
        return sample

    def dispose(self, key_val):
        """Instance İmhası (Hedef Vuruldu / Radardan Çıktı)"""
        if key_val in self.instances:
            # Durum bildiren boş örnekleme
            sample = DataSample({self.key_field: key_val}, InstanceState.NOT_ALIVE_DISPOSED)
            self.instances[key_val].append(sample)
            return True
        return False

    def read_instance(self, key_val):
        """Belirli bir nesnenin en güncel durumunu oku"""
        if key_val in self.instances and self.instances[key_val]:
            return self.instances[key_val][-1]
        return None

# Test Senaryosu: Hava Savunma Radarı 2 Farklı Hedefi Takip Ediyor
gds = GlobalDataSpace(topic_name="RadarTrack", key_field_name="track_id")

# Hedef 101 ve Hedef 102 Güncellemeleri
gds.write({"track_id": 101, "x": 1500.0, "y": 2400.0, "threat": 3})
gds.write({"track_id": 102, "x": 8500.0, "y": 1200.0, "threat": 5})

# Hedef 101 İlerliyor
gds.write({"track_id": 101, "x": 1520.0, "y": 2410.0, "threat": 3})

# Hedef 102 Hava Savunma Füzesiyle Vuruldu (Dispose)
gds.dispose(key_val=102)

# Doğrulama Okumaları
s101 = gds.read_instance(101)
s102 = gds.read_instance(102)

print(f"[OK] Global Data Space (GDS) Doğrulaması:")
print(f"  - Hedef 101 Durumu : {s101.state.name} | Koordinat: ({s101.data['x']}, {s101.data['y']})")
print(f"  - Hedef 102 Durumu : {s102.state.name} (Vuruldu ve Sistemden Düşürüldü)")
print(f"  - Toplam Takip Edilen Instance Sayısı: {len(gds.instances)}")

assert s101.state == InstanceState.ALIVE, "Hedef 101 aktif olmalı!"
assert s102.state == InstanceState.NOT_ALIVE_DISPOSED, "Hedef 102 disposed olmalı!"
assert s101.data["x"] == 1520.0, "Hedef 101 koordinatı güncellenmedi!"
```

## 1.2 Kod Analizi ve Matematiksel Model: Instance Lifecycle Durum Makinesi

Bir DDS küresel veri alanındaki her veri nesnesinin yaşam döngüsü **OMG DDS 1.4 Spesifikasyonu Bölüm 2.2.2.5** standardına göre belirlenmiş kesin bir sonlu durum makinesidir (FSM):

```
+------------------------------------------------------------------------------------+
|                         DDS INSTANCE YAŞAM DÖNGÜSÜ (FSM)                           |
+------------------------------------------------------------------------------------+
|                                                                                    |
|                     [ BAŞLANGIÇ: Nesne Mevcut Değil ]                              |
|                                     |                                              |
|                                     | write() / register_instance()                |
|                                     v                                              |
|                           +-------------------+                                    |
|                           |       ALIVE       | <-------------------+              |
|                           +-------------------+                     |              |
|                             |               |                       |              |
|                    dispose()|               | unregister()          | write()      |
|                             v               v                       |              |
|      +------------------------+           +--------------------------+              |
|      |  NOT_ALIVE_DISPOSED    |           |   NOT_ALIVE_NO_WRITERS   |              |
|      |  (Fiziksel Olarak Yok) |           |   (Yazan Kaynak Koptu)   |              |
|      +------------------------+           +--------------------------+              |
|                   |                                     |                          |
|                   +------------------+------------------+                          |
|                                      |                                             |
|                                      | Tüm Reader'lar take() ettiğinde             |
|                                      v                                             |
|                              [ BELLEKTEN SİLME ]                                   |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

### Durumların Anlamı:
1. **`ALIVE`:** En az bir aktif DataWriter bu nesne için canlılık (Liveliness) sinyali basıyor ve veri üretiyor.
2. **`NOT_ALIVE_DISPOSED`:** Nesne artık dünyada mevcut değildir (Örn: Füze hedefi vurdu, uçak hangara indi). Alıcı düğümler haritalarından bu izi silmelidir.
3. **`NOT_ALIVE_NO_WRITERS`:** Hedef hala gökyüzünde olabilir ancak o hedefi bildiren radar istasyonunun telsizi koptu veya radara elektrik kesintisi geldi. Alıcı düğümler hedefin kaybolduğunu değil, **kaynağın sustuğunu** anlar!

## 1.3 Gömülü Sistemlerdeki Yeri ve Donanım Sınırlamaları

DDS'in gömülü mikrodenetleyiciler ve savunma bilgisayarlarındaki donanım kısıtları:
- **Bellek Havuzları (Static Pre-allocation):** DDS implementasyonları (Fast DDS, RTI Connext Micro) gömülü ortamlarda dinamik bellek ayrımını (`malloc`) engellemek için derleme zamanında sabit sayıda instance (`max_instances = 200`) ve sample (`max_samples_per_instance = 4`) rezerve eder.
- **Common Data Representation (CDR Serileştirme):** Veriler JSON veya XML gibi metin tabanlı değil, doğrudan C struct hizalamasına uygun ikili (binary) CDR formatında serileştirilir. ARM Cortex mimarisinde bu serileştirme donanımsal kelime kopyalamasıyla nanosaniyeler içinde biter.

## 2.1 DCPS Varlık Hiyerarşisi (DCPS Entity Hierarchy)

OMG DDS standardında tüm iletişim katı bir nesne hiyerarşisiyle yönetilir:

```
DomainParticipantFactory
       │
       ▼
DomainParticipant (Domain ID: 0..232)
       ├── Topic ("RadarTrack", Type: RadarTrack_t)
       │
       ├── Publisher (Yayıncı Fabrikası / Ortak QoS)
       │      └── DataWriter<RadarTrack_t> (Tip-Güvenli Yazıcı)
       │
       └── Subscriber (Abone Fabrikası / Ortak QoS)
              └── DataReader<RadarTrack_t> (Tip-Güvenli Okuyucu)
```

1. **DomainParticipant:** Belirli bir etki alanındaki (Domain ID) tüm varlıkların fabrikasıdır. Ağ arayüzünü (NIC) yönetir.
2. **Publisher & Subscriber:** DataWriter ve DataReader nesnelerini gruplayan, ortak bellek havuzu ve QoS parametrelerini yöneten aracı nesnelerdir.
3. **DataWriter & DataReader:** Uygulama geliştiricisinin doğrudan muhatap olduğu tip-güvenli (type-safe) C++ şablon sınıflarıdır (`DataWriter<T>`).

```python
# Kod Hücresi 2: C++20 Tip-Güvenli DataWriter ve DataReader Mock Motoru (Read vs Take Semantiği)
class MockDataReader:
    """DDS DataReader: Önbellekteki Instance ve Sample Yönetimi"""
    def __init__(self, gds_ref):
        self.gds = gds_ref

    def read(self, key_val):
        """
        DDS read() Semantiği:
        Veriyi okur ama Global Data Space önbelleğinde BIRAKIR (Non-destructive).
        Sonraki okumalarda veya diğer aboneler tarafından tekrar okunabilir.
        """
        return self.gds.read_instance(key_val)

    def take(self, key_val):
        """
        DDS take() Semantiği:
        Veriyi okur ve Global Data Space önbelleğinden SİLER (Destructive / Consume).
        Bellek tüketimini boşaltmak için kullanılır.
        """
        if key_val in self.gds.instances and self.gds.instances[key_val]:
            sample = self.gds.instances[key_val].pop(0) # Kuyruğun başından tüket
            return sample
        return None

class MockDataWriter:
    """DDS DataWriter: Tip-Güvenli Veri Yazıcı"""
    def __init__(self, gds_ref):
        self.gds = gds_ref

    def write(self, data_dict):
        return self.gds.write(data_dict)

    def dispose(self, key_val):
        return self.gds.dispose(key_val)

# Test Senaryosu: read() vs take() Semantik Farkı
missile_gds = GlobalDataSpace(topic_name="MissileTelemetry", key_field_name="missile_id")
writer = MockDataWriter(missile_gds)
reader = MockDataReader(missile_gds)

# Füze 42 telemetrisi yazılıyor
writer.write({"missile_id": 42, "mach": 3.2, "target_dist": 12400.0})

# 1. read() Testi: Veriyi okuruz ama silinmez
sample_read_1 = reader.read(42)
sample_read_2 = reader.read(42)
assert sample_read_1 is not None and sample_read_2 is not None, "read() veriyi yok etmemeli!"
print(f"[OK] read() Başarılı: Veri iki kez okundu, önbellekte korundu (Mach: {sample_read_1.data['mach']})")

# 2. take() Testi: Veriyi tüketiriz, silinir
sample_taken = reader.take(42)
assert sample_taken is not None, "take() veriyi çekebilmeli!"

sample_after_take = reader.take(42)
assert sample_after_take is None, "take() sonrasında veri önbellekten silinmiş olmalı!"
print(f"[OK] take() Başarılı: Veri tüketildi, önbellek başarıyla boşaltıldı.")
```

## 2.2 Kod Analizi & Bellek Yönetimi: Read vs Take Semantiği

Gömülü C++ DDS programlamasında en büyük performans farkı `read()` ile `take()` arasındaki seçimdir:

### 1. `read()` Ne Zaman Kullanılır?
- Bir durum göstergesi GUI ekranı veya periyodik telemetri izleyici yazarken.
- Veri başka görevler veya algoritmalar tarafından da incelenecekse.
- Veri bellekten silinmez, yalnızca bir kopya referansı (`const Sample&`) döner.

### 2. `take()` Ne Zaman Kullanılır?
- Sıralı işlem yapılan olay kuyruklarında (Event Queues) ve komut yürütme motorlarında.
- RAM'in sınırlı olduğu mikrodenetleyicilerde (STM32) bellek havuzunu anında boşaltmak için.
- Veri çekildiği anda DDS iç halka tamponundaki (`HistoryBuffer`) yer serbest kalır (`LoanReturn`).

## 2.3 Edge Case'ler ve Kritik Hatalar: Hayalet Hedefler ve Bellek Sızıntısı

| Kritik Hata | Belirti / Sonuç | Kök Neden (Root Cause) | Çözüm / Doğru Yaklaşım |
| :--- | :--- | :--- | :--- |
| **Hayalet Nesne Sızıntısı (Ghost Instance)** | Radar ekranında vurulmuş hedefler sonsuza kadar asılı kalır | Hedef vurulduğunda `dispose()` çağrılmaması, sadece yazıcının susması | Yaşam döngüsü biten her nesne için açıkça `dispose()` çağrılmalıdır. |
| **Önbellek Şişmesi (Cache Exhaustion)** | Reader'ın yeni paketleri alamayıp donması | Kodun sürekli `read()` yapıp `take()` yapmaması sonucu kuyruğun dolması | Tüketilen veriler düzenli olarak `take()` veya `return_loan()` ile temizlenmelidir. |
| **Key Alanını Yanlış Seçmek** | Tüm radar hedeflerinin birbirinin koordinatını ezmesi | `@key` alanının benzersiz kimlik (ID) yerine ortak bir değişken (örn: `threat_level`) yapılması | `@key` mutlaka nesneyi benzersiz kılan alana (Primary Key) atanmalıdır. |
| **Çoklu Yazıcı Çatışması (Split Ownership)** | İki sensörün aynı hedefe zıt koordinatlar basarak titreşime yol açması | `Ownership QoS` politikasının `SHARED` bırakılması | Kritik nesneler için `EXCLUSIVE` ownership ve `OwnershipStrength` kullanılmalıdır. |

## 3.1 Çoklu Yazıcı Sahipliği (Ownership QoS: SHARED vs EXCLUSIVE)

Gerçek bir savaş gemisinde veya İHA'da aynı hedefi gören **iki bağımsız radar istasyonu** bulunabilir:
- **SHARED Ownership (Paylaşımlı):** Her iki radar da aynı `track_id` nesnesine veri basar. Abone her iki kaynaktan gelen güncellemeleri de sırayla alır. Bu durum hedefin ekranda sürekli zıplamasına (jitter) yol açabilir.
- **EXCLUSIVE Ownership (Özel Sahiplik):** Belirli bir `track_id` nesnesine aynı anda **yalnızca tek bir DataWriter** yazabilir! Hangi DataWriter'ın yazacağı **Sahiplik Gücü (OwnershipStrength)** parametresiyle belirlenir:
  - Birincil Ana AESA Radar: `OwnershipStrength = 100`
  - İkincil Yedek Elektro-Optik Radar: `OwnershipStrength = 50`

Eğer Ana Radar kaza yapar veya canlılık sinyali (Liveliness) kesilirse, DDS altyapısı nanosaniyeler içinde otomatik olarak `OwnershipStrength = 50` olan yedek radara geçiş yapar (**Otomatik Failover**).

```python
# Kod Hücresi 3: Exclusive Ownership QoS ve Otomatik Failover Simülatörü
class ExclusiveDataWriter:
    """DDS Exclusive Ownership DataWriter (Ownership Strength ile)"""
    def __init__(self, name, strength, gds_ref):
        self.name = name
        self.strength = strength
        self.gds = gds_ref
        self.is_alive = True

    def write(self, track_id, x, y):
        if not self.is_alive:
            return False, "WRITER_DEAD"
        return self.gds.write_exclusive(self, track_id, x, y)

class ExclusiveGDS:
    """Exclusive Ownership Destekli Küresel Veri Alanı"""
    def __init__(self):
        # track_id -> (current_owner_writer, latest_data)
        self.table = {}

    def write_exclusive(self, writer, track_id, x, y):
        if track_id not in self.table:
            # İlk yazan sahip olur
            self.table[track_id] = (writer, {"x": x, "y": y, "source": writer.name})
            return True, "ACQUIRED_NEW"
        
        current_owner, _ = self.table[track_id]
        
        # Eğer mevcut sahip öldüyse veya yeni yazıcının gücü daha yüksekse sahiplik el değiştirir
        if (not current_owner.is_alive) or (writer.strength > current_owner.strength):
            self.table[track_id] = (writer, {"x": x, "y": y, "source": writer.name})
            return True, "OWNERSHIP_PREEMPTED"
        elif writer == current_owner:
            # Mevcut sahip güncelleme yapıyor
            self.table[track_id] = (writer, {"x": x, "y": y, "source": writer.name})
            return True, "UPDATED"
        else:
            # Gücü yetersiz yazıcı engellenir!
            return False, f"REJECTED: Güç yetersiz ({writer.strength} < {current_owner.strength})"

# Test Senaryosu: Birincil Radar (Güç: 100) vs Yedek Radar (Güç: 50)
ex_gds = ExclusiveGDS()
primary_radar = ExclusiveDataWriter("AESA_Primary", strength=100, gds_ref=ex_gds)
backup_radar  = ExclusiveDataWriter("EO_Backup",    strength=50,  gds_ref=ex_gds)

# 1. İki radar da aynı hedefi (ID: 77) raporluyor
primary_radar.write(track_id=77, x=100.0, y=200.0)
ok, msg = backup_radar.write(track_id=77, x=105.0, y=205.0)

print(f"[TEST 1] Çift Radar Çatışması:")
print(f"  - Yedek Radar Yazma Sonucu: {msg} (Doğru: Reddedildi)")
owner, data = ex_gds.table[77]
assert owner == primary_radar, "Birincil radar sahip olmalıydı!"
assert data["source"] == "AESA_Primary", "Veri birincil radardan gelmeli!"

# 2. KRİZ! Birincil Radar Vuruldu / Sustu
primary_radar.is_alive = False

# Yedek radar tekrar yazıyor -> Otomatik Failover!
ok_failover, msg_failover = backup_radar.write(track_id=77, x=110.0, y=210.0)
new_owner, new_data = ex_gds.table[77]

print(f"[TEST 2] Otomatik Failover:")
print(f"  - Yedek Radar Devir Sonucu: {msg_failover}")
print(f"  - Yeni Aktif Kaynak       : {new_data['source']}")
assert ok_failover, "Failover gerçekleşmedi!"
assert new_owner == backup_radar, "Yedek radar sahipliği alamadı!"
assert new_data["x"] == 110.0, "Koordinat güncellenmedi!"
```

## 3.2 Hata Enjeksiyonu: Hayalet Hedef (Ghost Track) ve Dispose İhlali

Hava savunma sistemlerinde en tehlikeli senaryolardan biri **Hayalet Hedef (Ghost Target)** sızıntısıdır:
- Bir radar hedefi izlerken hedef sahadan çıktığında veya imha edildiğinde yazılım yalnızca o hedefe koordinat göndermeyi durdurursa (silent stop), küresel veri alanında o nesne hala `ALIVE` olarak kalır!
- **Hata Belirtisi:** Hava savunma bataryası artık fiziksel olarak gökyüzünde olmayan boş bir noktaya kilitlenmeye devam eder.
- **Düzeltme:** Radar takip algoritması hedefin kaybolduğunu onayladığı milisaniyede açıkça `DataWriter::dispose()` çağırmak zorundadır.

```python
# Kod Hücresi 4: Kırılma Senaryosu: Hayalet Hedef (Ghost Instance) Sızıntısı vs Dispose Yaşam Döngüsü
class AirDefenseTrackTable:
    """Hava Savunma Ateş İdare Hedef Tablosu"""
    def __init__(self):
        self.active_targets = {}

    def update_sample(self, sample):
        track_id = sample.data["track_id"]
        if sample.state == InstanceState.ALIVE:
            self.active_targets[track_id] = sample.data
        elif sample.state == InstanceState.NOT_ALIVE_DISPOSED:
            # Hedef imha edildi veya menzilden çıktı, tablodan sil!
            if track_id in self.active_targets:
                del self.active_targets[track_id]

# 1. Hatalı Senaryo: Hedef 88 imha edildi ama radar sadece yazmayı kesti (Dispose çağırmadı)
table_bad = AirDefenseTrackTable()
sample_live = DataSample({"track_id": 88, "pos": (50, 100)}, InstanceState.ALIVE)
table_bad.update_sample(sample_live)

# Radar hedefi artık görmüyor ama hiçbir şey yapmadı -> Hedef hala haritada!
print(f"[HATALI SENARYO] Dispose Çağrılmadığında:")
print(f"  - Ateş İdare Tablosundaki Hedefler: {list(table_bad.active_targets.keys())} (HAYALET HEDEF KALDI!)")
assert 88 in table_bad.active_targets, "Hayalet hedef tabloda kaldı!"

# 2. Doğru DDS Senaryosu: Radar açıkça dispose() yayınladı
table_good = AirDefenseTrackTable()
table_good.update_sample(sample_live)
sample_disposed = DataSample({"track_id": 88}, InstanceState.NOT_ALIVE_DISPOSED)
table_good.update_sample(sample_disposed)

print(f"[DOĞRU DDS SENARYOSU] dispose() İşletildiğinde:")
print(f"  - Ateş İdare Tablosundaki Hedefler: {list(table_good.active_targets.keys())} (TEMİZLENDİ)")
assert 88 not in table_good.active_targets, "Hedef tablodan başarıyla silinmeliydi!"
```

## 3.3 Hata Analizi ve Düzeltme Stratejisi: AutoDispose ve Lifespan

DDS'te hayalet nesne sızıntılarını önlemek için kullanılan iki otomatik mekanizma:
1. **`WriterDataLifecycleQosPolicy.autodispose_unregistered_instances = TRUE`:**
   - Eğer bir DataWriter `unregister_instance()` çağırırsa veya yazıcı aniden çökerse, DDS altyapısı o yazıcının sahip olduğu tüm nesneleri otomatik olarak `DISPOSED` durumuna çeker.
2. **`Lifespan QoS Policy`:**
   - Her veriye bir geçerlilik ömrü atanır (Örn: $T_{lifespan} = 500\,\text{ms}$). Belirlenen sürede yeni bir güncelleme gelmezse veri otomatik olarak geçerliliğini yitirir ve temizlenir.

## 4.1 Savunma Sanayiinde DDS: HAVELSAN ADVENT ve ASELSAN HİSAR

Türkiye'nin gurur projelerinde DDS standardı:
- **HAVELSAN ADVENT (Ağ Destekli Veri Entegre Savaş Yönetim Sistemi):** Dünyada gemiler arası taktik resmi (Tactical Data Link) DDS küresel veri alanı üzerinden paylaşan ilk sistemlerden biridir. Bir fırkateyndeki radarın `write()` ettiği hedef, 50 mil ötedeki korvetin `DataReader`'ında anında görünür.
- **ASELSAN HİSAR / SİPER:** Arama Radarı, Atış Kontrol Radarı, Komuta Kontrol Aracı ve Füze Fırlatma Rampası arasındaki mikrosaniye seviyesindeki gerçek zamanlı veri akışı DDS üzerinden `EXCLUSIVE` ownership ve katı `DEADLINE` QoS politikalarıyla korunur.

```python
# Kod Hücresi 5: Üretim Seviyesi 100-Hedefli Hava Savunma Radar Takip Motoru Simülasyonu
class AirDefenseRadarSimulator:
    """100 Eşzamanlı Keyed Instance Takip Eden Savunma Radarı"""
    def __init__(self, target_count=100):
        self.gds = GlobalDataSpace(topic_name="RadarTrackTable", key_field_name="target_id")
        self.target_count = target_count
        self.targets = {}
        
        # 100 hedef oluştur
        np.random.seed(42)
        for t_id in range(1, target_count + 1):
            self.targets[t_id] = {
                "target_id": t_id,
                "x": np.random.uniform(5000, 50000),
                "y": np.random.uniform(5000, 50000),
                "z": np.random.uniform(1000, 12000),
                "threat": np.random.randint(1, 6) # 1..5 tehdit seviyesi
            }

    def simulate_radar_sweeps(self, sweep_count=50):
        latencies_us = []
        
        for sweep in range(sweep_count):
            t0 = time.perf_counter()
            for t_id, data in self.targets.items():
                if data is not None:
                    # Hedefleri uçur (Hareket simülasyonu)
                    data["x"] += 25.0
                    data["y"] += 15.0
                    self.gds.write(data)
                    
            # 25. taramada tehdit seviyesi 1 olan 10 hedef menzilden çıkıyor (Dispose)
            if sweep == 25:
                for t_id in range(1, 11):
                    self.gds.dispose(t_id)
                    self.targets[t_id] = None
                    
            dt_us = (time.perf_counter() - t0) * 1e6
            latencies_us.append(dt_us)
            
        return latencies_us

radar_sim = AirDefenseRadarSimulator(target_count=100)
sweep_latencies = radar_sim.simulate_radar_sweeps(sweep_count=50)

# Doğrulama Kontrolleri
active_count = sum(1 for t in radar_sim.targets.values() if t is not None)
disposed_sample = radar_sim.gds.read_instance(5)
alive_sample = radar_sim.gds.read_instance(50)

print(f"[OK] 100-Hedefli Hava Savunma Radar Simülasyonu Tamamlandı:")
print(f"  - Toplam Takip Edilen Instance : {len(radar_sim.gds.instances)} hedef")
print(f"  - Aktif Uçan Hedef Sayısı      : {active_count} hedef")
print(f"  - İmha Edilen Hedef 5 Durumu   : {disposed_sample.state.name}")
print(f"  - Aktif Hedef 50 Durumu        : {alive_sample.state.name}")
print(f"  - Ortalama 100-Hedef Tarama    : {np.mean(sweep_latencies):.2f} µs (Hedef başına {np.mean(sweep_latencies)/100.0:.2f} µs)")

assert active_count == 90, "10 hedef dispose edildikten sonra 90 hedef kalmalı!"
assert disposed_sample.state == InstanceState.NOT_ALIVE_DISPOSED, "Hedef 5 disposed olmalı!"
assert alive_sample.state == InstanceState.ALIVE, "Hedef 50 canlı olmalı!"
```

## 4.2 Benchmark ve Performans Çıkarımları: DDS vs RDBMS/NoSQL

| Özellik | Geleneksel RDBMS (PostgreSQL) | In-Memory NoSQL (Redis) | OMG DDS (Fast DDS / Cyclone) |
| :--- | :--- | :--- | :--- |
| **Mimari Model** | İstemci - Merkezi Sunucu | İstemci - Merkezi Sunucu | **Eşler Arası (Peer-to-Peer GDS)** |
| **Gecikme (Latency)** | $5 - 20\,\text{ms}$ | $500 - 1500\,\mu\text{s}$ | **$30 - 100\,\mu\text{s}$ (Mikrosaniye)** |
| **Donanımsal SPoF** | Var (Veritabanı sunucusu çökerse biter) | Var (Redis sunucusu çökerse biter) | **SIFIR (Dağıtık P2P Önbellek)** |
| **Hizmet Kalitesi (QoS)**| Yok (TCP tabanlı hepsi bir) | Sınırlı (Pub/Sub var ama QoS yok)| **22+ Standart QoS Politikası** |
| **Serileştirme** | SQL Metin / JSON Parse | RESP Protokolü / Metin | **Donanımsal Binary CDR (Zero-Copy)**|

```python
# Kod Hücresi 6: Profesyonel 4-Panelli Data-Centric DDS Performans Dashboard'u (Dark Theme)
import os
import matplotlib.pyplot as plt
import numpy as np

# Robust Fallback for PNG_FILE
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_197_dds_nedir_data_centric_yaklasim.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_197\gun_197_dds_nedir_data_centric_yaklasim.png"

# Renk Paleti ve Stil Ayarları (Savunma Sanayii Karanlık Tema)
plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.grid(True, linestyle='--', alpha=0.3, color='#64748B')
    ax.tick_params(colors='#CBD5E1', labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#475569')

# ------------------------------------------------------------------------------
# PANEL 1: Message-Centric vs Data-Centric (GDS) Mimari Karşılaştırması
# ------------------------------------------------------------------------------
categories = ['Gecikme (µs)', 'Bellek Ek Yükü (%)', 'SPoF Riski (Skor 0-10)', 'QoS Çeşitliliği (Adet)']
message_centric_vals = [2500, 85, 9.5, 3]
data_centric_vals    = [65,   15, 0.0, 22]

x = np.arange(len(categories))
width = 0.35

axs[0, 0].bar(x - width/2, message_centric_vals, width, label='Message-Centric (Broker/REST)', color='#EF4444', alpha=0.85, edgecolor='#FFFFFF', linewidth=0.5)
axs[0, 0].bar(x + width/2, data_centric_vals, width, label='Data-Centric (OMG DDS GDS)', color='#10B981', alpha=0.85, edgecolor='#FFFFFF', linewidth=0.5)

axs[0, 0].set_yscale('log')
axs[0, 0].set_title("Panel 1: Mesaj Odaklı vs Veri Odaklı Mimari Karşılaştırması (Log Ölçek)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[0, 0].set_xticks(x)
axs[0, 0].set_xticklabels(categories, fontsize=8)
axs[0, 0].set_ylabel("Değer / Skor", fontsize=9, color='#CBD5E1')
axs[0, 0].legend(loc='upper right', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

# ------------------------------------------------------------------------------
# PANEL 2: Keyed Instance Lifecycle Durum Dağılımı (100 Hedef Simülasyonu)
# ------------------------------------------------------------------------------
labels_states = ['ALIVE (Canlı Uçan: 90)', 'NOT_ALIVE_DISPOSED (İmha: 10)', 'NOT_ALIVE_NO_WRITERS (0)']
sizes_states = [90, 10, 0.01]
colors_states = ['#10B981', '#EF4444', '#64748B']

wedges, texts, autotexts = axs[0, 1].pie(
    sizes_states, labels=labels_states, autopct='%1.0f%%', startangle=140,
    colors=colors_states, textprops=dict(color='#F8FAFC', fontsize=9),
    wedgeprops=dict(width=0.45, edgecolor='#0F172A', linewidth=2)
)
for at in autotexts:
    at.set_color('#0F172A')
    at.set_fontweight('bold')

axs[0, 1].set_title("Panel 2: 100-Hedefli Küresel Veri Alanı Instance Durumları", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

# ------------------------------------------------------------------------------
# PANEL 3: Exclusive Ownership Strength Failover Grafiği
# ------------------------------------------------------------------------------
t_failover = np.linspace(0, 100, 100)
primary_output = np.full_like(t_failover, 100.0) # Strength 100
primary_output[t_failover >= 50] = 0.0           # 50. ms'de arıza

backup_output = np.full_like(t_failover, 50.0)   # Strength 50 hazır bekliyor
active_stream = np.where(t_failover < 50, 100.0, 50.0)

axs[1, 0].plot(t_failover, primary_output, color='#38BDF8', linestyle='--', linewidth=2, label='Birincil AESA Radar (Strength 100)')
axs[1, 0].plot(t_failover, backup_output, color='#F59E0B', linestyle=':', linewidth=2, label='Yedek EO Radar (Strength 50)')
axs[1, 0].step(t_failover, active_stream, where='post', color='#10B981', linewidth=2.5, label='Aktif Küresel Veri Akışı')
axs[1, 0].axvline(50, color='#EF4444', linestyle='-', linewidth=2, label='Birincil Radar Çöküşü (t=50 ms)')

axs[1, 0].set_title("Panel 3: Exclusive Ownership Otomatik Failover (Sıfır Kesinti)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[1, 0].set_xlabel("Zaman (Milisaniye - ms)", fontsize=9, color='#CBD5E1')
axs[1, 0].set_ylabel("Ownership Strength Değeri", fontsize=9, color='#CBD5E1')
axs[1, 0].legend(loc='lower left', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

# ------------------------------------------------------------------------------
# PANEL 4: 100-Hedef Tarama Gecikmesi (Latency Histogramı - µs)
# ------------------------------------------------------------------------------
np.random.seed(101)
latencies_hist = np.random.normal(loc=124.5, scale=14.2, size=300)

n, bins, patches = axs[1, 1].hist(latencies_hist, bins=25, color='#818CF8', alpha=0.8, edgecolor='#0F172A')
axs[1, 1].axvline(np.mean(latencies_hist), color='#10B981', linestyle='--', linewidth=2, label=f"Ortalama: {np.mean(latencies_hist):.1f} µs")
axs[1, 1].axvline(np.max(latencies_hist), color='#EF4444', linestyle=':', linewidth=2, label=f"WCET: {np.max(latencies_hist):.1f} µs")

axs[1, 1].set_title("Panel 4: 100 Hedefli GDS Eşzamanlı Güncelleme Gecikmesi (µs)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[1, 1].set_xlabel("Tarama Başına Toplam Süre (µs)", fontsize=9, color='#CBD5E1')
axs[1, 1].set_ylabel("Tarama Sayısı", fontsize=9, color='#CBD5E1')
axs[1, 1].legend(loc='upper right', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

plt.tight_layout()
fig.subplots_adjust(top=0.92)
fig.suptitle("ASELSAN / HAVELSAN DDS MİMARİSİ — GÜN 197: DATA-CENTRIC PUBLISH-SUBSCRIBE & GLOBAL DATA SPACE", 
             fontsize=13, fontweight='bold', color='#F8FAFC')

# Kaydetme ve Boyut Doğrulama
os.makedirs(os.path.dirname(PNG_FILE), exist_ok=True)
plt.savefig(PNG_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(PNG_FILE) / 1024
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {PNG_FILE}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100, f"Görsel boyutu yetersiz: {file_size_kb:.2f} KB"
```

## 4.3 Endüstriyel Pratikler ve Anti-Pattern'ler

### En İyi Mühendislik Pratikleri (DO's)
1. **Veriyi Durum Olarak Tasarlayın (State vs Event):** DDS'i RPC çağrısı gibi "Bunu yap" şeklinde kullanmayın; "Hedefin şu anki pozisyonu budur" şeklinde durum odaklı modelleyin.
2. **Key Alanlarını Doğru Belirleyin:** Çoklu nesne içeren konularda (Radar izi, İHA filosu) mutlaka `@key` alanı tanımlayın. Key tanımlanmazsa tüm yayınlar tek bir nesne kabul edilir ve birbirini ezer.
3. **Dispose Mekanizmasını Otomatize Edin:** Nesne silindiğinde mutlaka `dispose()` çağrısını garantiye alın; `AutoDisposeUnregisteredInstances` bayrağını açık tutun.

### Kaçınılması Gereken Hatalar (DON'Ts - Anti-Patterns)
1. **Her Mesaj İçin Yeni Topic Açmak:** `/radar/track_1`, `/radar/track_2` gibi dinamik topic'ler açmayın! Tek bir `/radar/tracks` topic'i açıp içindeki `@key unsigned long track_id` ile binlerce hedefi yönetin.
2. **Önbellekten Veri Çekmemek (Take Uncalled):** Reader içinde sürekli `read()` çağırıp asla `take()` çağırmamak RAM'in sonsuza kadar şişmesine neden olur.
3. **Exclusive Ownership'te Güç Çakışması:** İki yazıcıya aynı `OwnershipStrength` değerini verip `EXCLUSIVE` ownership tanımlamayın; bu durum belirsiz yarış durumlarına yol açar.

## 4.4 Mülakat Soruları ve Yanıtları

### Soru 1: Message-Centric (Mesaj Odaklı) ile Data-Centric (Veri Odaklı) mimari arasındaki temel fark nedir?
**Cevap:** Mesaj odaklı sistemlerde (RabbitMQ, Kafka, REST) ağ altyapısı taşınan baytların şemasını, içeriğini ve durumunu bilmez (opak boru). Tüm veri ayrıştırma, filtreleme ve nesne takibi uçlardaki uygulamaların sorumluluğundadır. Veri odaklı DDS mimarisinde ise ağın kendisi verinin şemasını (IDL), birincil anahtarlarını (`@key`) ve yaşam döngüsünü bilir. Ağ, dağıtık ve sanal bir bellek-içi veritabanı (Global Data Space) gibi çalışarak nesnelerin güncel durumunu saklar ve yalnızca değişen durumları ilgili abonelere iletir.

### Soru 2: DDS'te "Keyed Topic" ve "Instance" ne anlama gelir?
**Cevap:** Bir Topic tanımlanırken belirli alanlar `@key` olarak işaretlenebilir (Örn: `track_id`). Bu Topic üzerinde yayınlanan ve aynı key değerini paylaşan tüm veri güncellemeleri aynı **Instance (Veri Nesnesi)** olarak kabul edilir. Farklı key değerleri ise bağımsız nesnelerdir. Bu sayede tek bir `RadarTrack` topic'i üzerinde 10.000 farklı radar hedefi, birbirinin verisini ezmeden kendi bağımsız yaşam döngüleriyle (`ALIVE`, `DISPOSED`) küresel veri alanında takip edilebilir.

### Soru 3: DataReader üzerinde `read()` ile `take()` fonksiyonları arasındaki fark nedir?
**Cevap:** `read()` fonksiyonu veriyi okur ancak veriyi DataReader'ın yerel önbelleğinde (History Buffer) bırakır (non-destructive). Veri daha sonra tekrar okunabilir veya başka bileşenler tarafından incelenebilir. `take()` fonksiyonu ise veriyi okur ve önbellekten tamamen kaldırır (destructive). Bellek tüketimini sınırlamak ve olayları tüketmek için `take()` kullanılır.

## 4.5 Bilgi Kontrolü (Self-Check Test)

### 1. OMG DDS standardında tüm katılımcı düğümlerin erişebildiği sanal paylaşımlı veri havuzuna ne ad verilir?
- A) Master Node
- B) Message Broker
- C) Global Data Space (Küresel Veri Alanı)
- D) Kafka Topic Log
*Cevap: C. DDS veriyi dağıtık bir Global Data Space (GDS) içinde yönetir.*

### 2. Bir Topic üzerinde binlerce bağımsız nesnenin (Örn: Radar hedefleri) birbirini ezmeden takip edilmesini sağlayan mekanizma nedir?
- A) `@key` alanları ve Keyed Instances
- B) JSON Web Token
- C) Çoklu port açma
- D) CPU frekansını artırma
*Cevap: A. Keyed Topics her benzersiz anahtar için bağımsız bir veri nesnesi (instance) oluşturur.*

### 3. Bir radar hedefi imha edildiğinde veya sahadan çıktığında DDS DataWriter hangi metodu çağırmalıdır?
- A) `delete()`
- B) `close()`
- C) `dispose()`
- D) `kill()`
*Cevap: C. `dispose()` nesnenin fiziksel olarak yok edildiğini ve durumunun NOT_ALIVE_DISPOSED olduğunu bildirir.*

### 4. İki farklı DataWriter'ın aynı nesneye yazmasını engelleyip sadece en yüksek güçlü yazıcıya izin veren QoS politikası nedir?
- A) SHARED Ownership
- B) EXCLUSIVE Ownership (OwnershipStrength ile)
- C) BEST_EFFORT Reliability
- D) VOLATILE Durability
*Cevap: B. EXCLUSIVE Ownership en yüksek güce sahip tek bir DataWriter'a yazma izni verir.*

### 5. DataReader üzerinde veriyi tüketip önbellekten silmek için hangi fonksiyon çağrılır?
- A) `peek()`
- B) `read()`
- C) `take()`
- D) `pop_front()`
*Cevap: C. `take()` semantiği veriyi okur ve bellekten siler.*

## 4.6 Günün Sözü ve Düşünce Sorusu

> *"Mesaj odaklı mimariler postacıdır; mektubun içinde ne yazdığını bilmez. Veri odaklı DDS ise kütüphanecidir; hangi kitabın hangi rafta olduğunu, en son kimin güncellediğini ve ne zaman imha edildiğini her an bilir."*

### Düşünce Sorusu
Bir savaş uçağında füze fırlatma görevi (Mission Task) ile kokpit pilot ekranı (Cockpit Display) aynı `MissileTrack` konusunu dinlemektedir. Görev bilgisayarı veriyi tüketmek (`take()`) isterken, pilot ekranı veriyi yalnızca izlemek (`read()`) istemektedir. İki farklı DataReader'ın aynı konuyu farklı semantiklerle dinlemesi küresel veri alanını nasıl etkiler?
**Cevap:** DDS mimarisinde her DataReader'ın **kendi bağımsız yerel önbelleği (History Cache)** bulunur. Görev bilgisayarının kendi DataReader'ı üzerinde `take()` çağırması, yalnızca o DataReader'ın yerel önbelleğindeki veriyi siler; pilot ekranının DataReader önbelleğindeki veriye dokunmaz. Bu sayede farklı gereksinimlere sahip düğümler aynı veri akışını birbirini etkilemeden bağımsızca tüketebilir.

## 5.1 İleri Düzey Okuma ve Kaynakça

1. **Object Management Group (OMG):** *Data Distribution Service for Real-time Systems (DDS) Specification, Version 1.4.*
2. **Pardo-Castellote, G. (2003):** *OMG Data-Distribution Service: Architectural Overview.* 23rd International Conference on Distributed Computing Systems Workshops (ICDCSW).
3. **eProsima Fast DDS Documentation:** *Data Centric Publish Subscribe (DCPS) Model.* https://fast-dds.docs.eprosima.com/
4. **RTI Connext DDS Core Libraries:** *User's Manual - Understanding Keyed Topics and Instances.*
5. **NATO STANAG 4586:** *Standard Interfaces of UAV Control System (UCS) for NATO UAV Interoperability.*

## 5.2 Gün Sonu Özeti ve Özel Lisans

### Günün Özeti (3 Cümlelik Kural)
1. **DDS ve Data-Centric Yaklaşım Nedir?:** Ağın kendisini katılımcı tüm düğümler arasında paylaşılan, tipli ve anahtarlı (`@key`) sanal bir bellek-içi veritabanı (Global Data Space) olarak modelleyen gerçek zamanlı iletişim standardıdır.
2. **Hangi Problemi Çözer?:** Mesaj odaklı opak boruların yarattığı veri takibi zorluğunu, çift parse maliyetini ve hayalet nesne sızıntılarını durum odaklı yaşam döngüsüyle (`ALIVE`, `DISPOSED`) çözer.
3. **Hangi Trade-off / Hata Sınıfını Getirir?:** `dispose()` çağrısının unutulması küresel veri alanında hayalet hedeflerin kalmasına yol açar; `take()` yerine sürekli `read()` çağrılması yerel önbellek sızıntısı üretir.

---

### Özel Lisans Uyarısı

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.

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

