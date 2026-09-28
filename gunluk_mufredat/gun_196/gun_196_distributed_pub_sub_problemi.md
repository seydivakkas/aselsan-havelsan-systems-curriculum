# GÜN 196: Dağıtık Sistemlerde Yayıncı/Abone (Pub/Sub) Paradigması ve Ayrışma (Decoupling) Problemi

**Faz 6:** DDS / ROS2 / Gazebo (Dağıtık Robotik Sistemler, Eşler Arası Ağlar ve Simülasyon)  
**Ön Koşul:** Faz 3 (Modern C++ Bellek ve IPC) + Faz 4 (Linux Kernel & Ağ) + Faz 5 (RTOS & Sensör Ağ Geçidi)  
**Sonraki Adım:** Gün 197 — DDS Nedir? Veri Odaklı (Data-Centric) Yaklaşım ve RTPS Protokolü  
**Hedef Sektör:** HAVELSAN (ADVENT Savaş Yönetim Sistemi, C4ISR), ASELSAN (Hava Savunma Radar Ağı), BAYKAR & TUSAŞ (Sürü İHA Görev Sistemleri)

---

### Müfredat Bilgileri ve Tasarım Kararı
Önceki modüllerde (Faz 5), tek bir mikrodenetleyici üzerindeki görevlerin (tasks) kuyruklar ve semaforlar aracılığıyla nasıl haberleştiğini inceledik. Ancak gerçek bir insansız hava aracında, otonom zırhlı araçta veya denizaltı savaş yönetim sisteminde **onlarca bağımsız bilgisayar, sensör ve işlemci** ağ üzerinden birbirine bağlıdır.

Geleneksel istemci-sunucu (Client-Server / RPC) ve noktadan noktaya (Point-to-Point TCP) soket mimarileri dağıtık robotik sistemlerde felaketle sonuçlanır:
1. **Bağlantı Patlaması (Connection Explosion):** $N$ düğümlü bir sistemde her düğüm birbiriyle konuşmak istediğinde $\frac{N(N-1)}{2} = O(N^2)$ adet doğrudan TCP bağlantısı açılmalıdır.
2. **Sıkı Bağlılık (Tight Coupling):** Bir sensör düğümü veriyi kime göndereceğini (IP adresini, port numarasını) önceden bilmek zorundadır. Ağa yeni bir ekran veya yapay zeka modülü eklendiğinde tüm sensör kodlarının baştan derlenmesi gerekir.
3. **Tek Nokta Hata Riski (Single Point of Failure - SPoF):** Merkezi bir aracı (MQTT/Kafka Broker veya ROS1 `roscore`) kullanıldığında, o sunucu kaza yaparsa savaş alanındaki tüm filo kör ve sağır kalır.

**Dağıtık Yayıncı/Abone (Distributed Publish/Subscribe) Paradigması**, düğümleri **Zaman, Mekan ve Senkronizasyon** boyutlarında birbirinden tamamen ayırarak (Decoupling) savunma ve robotik sistemlerine sınırsız ölçeklenebilirlik ve yüksek hata toleransı kazandırır.

```
+----------------------------------------------------------------------------------------------------+
|                         DAĞITIK HABERLEŞME TOPOLOJİLERİNİN KARŞILAŞTIRILMASI                       |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [ 1. NOKTADAN NOKTAYA TCP ]          [ 2. MERKEZİ BROKER (MQTT/ROS1) ]    [ 3. DAĞITIK P2P PUB/SUB (DDS) ]|
|                                                                                                    |
|     (O(N^2) Bağlantı Kaosu)               (Tek Nokta Arıza - SPoF)            (Eşler Arası Ayrışma)        |
|                                                                                                    |
|      (A) <--------> (B)                       (A)      (B)                        (A)        (B)           |
|       ^ \        /  ^                           \    /                            ^          ^           |
|       |  \      /   |                            v  v                              |          |           |
|       |   \    /    |                      +--------------+                =======================      |
|       |    \  /     |                      | MERKEZİ      |                   KÜRESEL VERİ ALANI        |
|       v     \/      v                      | BROKER /     |                    (GLOBAL DATA SPACE)      |
|      (C) <--------> (D)                     | ROSCORE      |                =======================      |
|                                             +--------------+                        |          |           |
|  * 4 Düğüm: 6 Bağlantı                             ^                                v          v           |
|  * 32 Düğüm: 496 Bağlantı!                         | (Broker Çökerse               (C)        (D)          |
|  * IP ve Portlar Sabit (Kırılgan)           Tüm Sistem Ölür!)             * Sıfır Broker (No SPoF)         |
|                                                                           * Dinamik Keşif (Discovery)      |
|                                                                           * Çok Noktaya Yayın (Multicast)  |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

> **Tasarım Kararı:** Savaş sahasında bir İHA'nın veya zırhlı aracın telsiz bağlantısı koptuğunda merkezi bir sunucuya bağımlı olamaz. Bu nedenle kritik savunma sistemleri (DO-178C ve NATO STANAG 4586) merkezi broker mimarilerini yasaklar; doğrudan donanımsal UDP Multicast üzerinde koşan **Eşler Arası (Peer-to-Peer) Dağıtık Pub/Sub (DDS RTPS)** protokolünü şart koşar.

## 1.1 Noktadan Noktaya İletişimin Çöküşü ve Üç Boyutlu Ayrışma

Klasik yazılım mühendisliğinde kullanılan REST API veya gRPC/RPC sistemleri dağıtık robotik dünyasında üç kritik boyutta tıkanır (Eugster et al., 2003):

### 1. Mekan Ayrışması (Space Decoupling)
- **Problem:** Bir düğüm mesaj göndermek için alıcının ağ adresini (`IP:Port`) bilmek zorundadır.
- **Pub/Sub Çözümü:** Yayıncı (Publisher) ve Abone (Subscriber) birbirlerinin IP adreslerinden, işlemci kimliklerinden veya fiziksel konumlarından habersizdir. Yalnızca **Konu (Topic)** adı verilen mantıksal bir veri kanalını bilirler (Örn: `/uav/nav/imu_raw`).

### 2. Zaman Ayrışması (Time Decoupling)
- **Problem:** İstemci-sunucu modelinde her iki tarafın da aynı anda ayakta ve hatta bağlı olması şarttır.
- **Pub/Sub Çözümü:** Yayıncı veriyi bastığı anda abone henüz başlatılmamış veya geçici olarak bağlantısı kopmuş olabilir. Kalıcılık politikaları (Durability / Transient Local QoS) sayesinde abone hatta katıldığı anda geçmişteki en kritik son durum mesajını (Latching) otomatik olarak teslim alır.

### 3. Senkronizasyon Ayrışması (Synchronization Decoupling)
- **Problem:** RPC çağrısı yapan bir iş parçacığı (thread), karşı taraf yanıt verene kadar bloke olur (Blocking I/O).
- **Pub/Sub Çözümü:** Yayıncı `publish()` çağrısını yapar yapmaz kontrolü geri alır ($O(1)$ yürütme süresi). Verinin iletimi ve abonelerin geri çağırım (callback) fonksiyonlarının tetiklenmesi tamamen asenkron olarak arka planda yürütülür.

```python
# Kod Hücresi 1: O(N^2) Noktadan Noktaya Bağlantı Patlaması vs Dağıtık Pub/Sub Topoloji Simülatörü
import numpy as np

def calculate_topologies(node_counts):
    """
    Farklı Düğüm Sayılarında Ağ Bağlantı ve Soket Sayısı Karşılaştırması:
    - P2P Mesh (Noktadan Noktaya TCP) : N * (N - 1) / 2
    - Broker-Based (MQTT / ROS1)     : N (Tek merkeze N bağlantı)
    - Peer-to-Peer Pub/Sub (Multicast): N (Her düğümde 1 yayıncı/dinleyici soketi)
    """
    p2p_connections = [int(n * (n - 1) / 2) for n in node_counts]
    broker_connections = [n for n in node_counts]
    pubsub_p2p_sockets = [n for n in node_counts] # Her düğüm 1 multicast soketi açar
    
    return p2p_connections, broker_connections, pubsub_p2p_sockets

nodes = np.array([2, 4, 8, 16, 32, 64, 128])
p2p_conn, broker_conn, pubsub_sock = calculate_topologies(nodes)

print(f"[OK] Dağıtık Ağ Topoloji Karmaşıklığı Analizi:")
print(f"{'Düğüm (N)':<10} | {'P2P Mesh TCP (O(N^2))':<24} | {'Merkezi Broker':<16} | {'P2P Pub/Sub Multicast':<22}")
print("-" * 80)
for i in range(len(nodes)):
    print(f"{nodes[i]:<10} | {p2p_conn[i]:<24} | {broker_conn[i]:<16} | {pubsub_sock[i]:<22}")

# Doğrulamalar
assert p2p_conn[1] == 6, "4 düğümlü mesh 6 bağlantı olmalı!"
assert p2p_conn[4] == 496, "32 düğümlü mesh 496 bağlantı olmalı!"
assert p2p_conn[6] == 8128, "128 düğümlü mesh 8128 bağlantı olmalı!"

print(f"\n[SONUÇ] 128 Düğümlü bir İHA/Savaş filosunda P2P TCP Mesh tam 8,128 soket gerektirirken,")
print(f"Pub/Sub Multicast yaklaşımı sistemi yalnızca 128 bağımsız soketle ölçekler (63.5x Bağlantı Tasarrufu)!")
```

## 1.2 Kod Analizi ve Matematiksel Model: Fan-Out ve Multicast Dağıtım

Dağıtık sistemlerde performans darboğazı yalnızca bağlantı sayısı değil, **Ağ Çıkış Bant Genişliği (Egress Bandwidth / Fan-Out)** problemidir.

### 1. Unicast Fan-Out Modeli (İstemci-Sunucu / TCP P2P)
Bir yayıncının $M$ aboneye $S_{bytes}$ boyutundaki bir paketi $f$ frekansıyla göndermesi durumunda CPU'nun sokete basması gereken toplam veri debisi:
$$\text{Throughput}_{unicast} = M \times S_{bytes} \times f$$
Örnek: $S_{bytes} = 100\,\text{KB}$ (Lidar nokta bulutu), $f = 30\,\text{Hz}$, $M = 10$ abone:
$$\text{Throughput}_{unicast} = 10 \times 100\,\text{KB} \times 30 = 30.000\,\text{KB/s} = 30\,\text{MB/s} \approx 240\,\text{Mbps}$$
Yayıncı düğüm tek bir lidar paketini 10 kez RAM'den sokete kopyalamak zorunda kalır (CPU ve bus darboğazı).

### 2. Donanımsal Multicast Modeli (DDS / IGMP Snooping)
Donanımsal çok noktaya yayında (IP Multicast: `239.255.0.1`), yayıncı paketi ağ kartına **yalnızca 1 kez** basar:
$$\text{Throughput}_{multicast} = 1 \times S_{bytes} \times f = 100\,\text{KB} \times 30 = 3\,\text{MB/s} \approx 24\,\text{Mbps}$$
Paketin 10 aboneye çoğaltılması işlemi, işlemciyi yormadan **fiziksel ağ anahtarı (Ethernet Switch)** seviyesinde donanımsal olarak gerçekleştirilir (**%90 CPU ve Bant Genişliği Tasarrufu!**).

## 1.3 Gömülü Sistemlerdeki Yeri ve Donanım Sınırlamaları

Robotik dünyasında ROS1'den ROS2'ye geçişin tek ve en büyük sebebi bu mimari zorunluluktur:
- **ROS1 Dönemi (2007-2020):** Merkezi bir `roscore` (XML-RPC Master) kullanılıyordu. Savaş alanında haberleşmenin koptuğu veya IP adresinin değiştiği otonom askeri araçlarda `roscore` bağlantıyı kaybediyor ve tüm robot donuyordu.
- **ROS2 Dönemi (2020+):** `roscore` tamamen çöpe atıldı! İletişim omurgası olarak OMG (Object Management Group) tarafından standardize edilen **DDS (Data Distribution Service)** entegre edildi. Artık her ROS2 düğümü ağdaki diğer düğümleri UDP Multicast (RTPS Discovery) ile sıfır konfigürasyonla (Zero-Conf) bulur ve doğrudan eşler arası haberleşir.

## 2.1 Konu Tabanlı (Topic-Based) vs İçerik Tabanlı (Content-Based) Filtreleme

Dağıtık Pub/Sub sistemlerinde iki temel filtreleme paradigması kullanılır:

1. **Konu Tabanlı Filtreleme (Topic-Based):**
   - Hiyerarşik metin dizgileri kullanılır: `/filo_1/iha_3/seyrusefer/gps`
   - Abone belirli bir konuya üye olur; yayınlanan tüm mesajlar aboneye akar.
   - **Avantajı:** Çok hızlıdır, hash tablosu ile $O(1)$ sürede eşleşir.

2. **İçerik Tabanlı Filtreleme (Content-Based Filtering - CBF):**
   - Abone yalnızca konuya değil, mesajın **içeriğindeki değer şartına (SQL-like predicate)** abone olur:
     `SELECT * FROM "RadarTrack" WHERE distance_km < 15.0 AND threat_level > 3`
   - **Savunma Sanayii Avantajı:** Filtreleme işlemi yayıncı tarafında (Writer-side) yapılarak gereksiz yüzlerce radar izi telsiz hattına hiç basılmaz; telsiz bant genişliği korunur.

```python
# Kod Hücresi 2: C++20 Tarzı Tip-Güvenli Konu Tabanlı Dağıtık Pub/Sub Dağıtım Motoru
import time
from collections import defaultdict

class DistributedTopicBus:
    """DDS / ROS2 Mantığıyla Çalışan Bellek-İçi Dağıtık Konu Dağıtım Motoru"""
    def __init__(self):
        # topic_name -> list of subscriber callbacks
        self.subscribers = defaultdict(list)
        self.message_counters = defaultdict(int)
        self.published_history = []

    def subscribe(self, topic_name, callback_fn):
        """Bir konuya geri çağırım fonksiyonu (callback) bağla"""
        self.subscribers[topic_name].append(callback_fn)

    def publish(self, topic_name, message_data):
        """Asenkron/Eşzamanlı Mesaj Yayını (Zero-Copy Referans Aktarımı)"""
        self.message_counters[topic_name] += 1
        callbacks = self.subscribers.get(topic_name, [])
        
        # Tüm abonelere dağıt (Fan-out)
        for cb in callbacks:
            cb(topic_name, message_data)
            
        self.published_history.append((topic_name, message_data))
        return len(callbacks)

# Test Senaryosu: Aviyonik Sensör ve Güdüm Düğümleri
bus = DistributedTopicBus()

# Abone 1: Uçuş Kontrolcüsü (Yalnızca IMU dinler)
flight_controller_received = []
def on_imu_received(topic, data):
    flight_controller_received.append(data)

# Abone 2: Kara Kutusu (BlackBox Logger - Hem IMU hem GPS dinler)
blackbox_received = []
def on_blackbox_received(topic, data):
    blackbox_received.append((topic, data))

# Aboneliklerin Başlatılması (Mekan ve Zaman Ayrışması)
bus.subscribe("/uav/sensors/imu", on_imu_received)
bus.subscribe("/uav/sensors/imu", on_blackbox_received)
bus.subscribe("/uav/sensors/gps", on_blackbox_received)

# Yayıncılar Veri Basıyor
bus.publish("/uav/sensors/imu", {"accel_z": 9.81, "gyro_x": 0.02})
bus.publish("/uav/sensors/gps", {"lat": 39.9207, "lon": 32.8541})
bus.publish("/uav/sensors/imu", {"accel_z": 9.82, "gyro_x": -0.01})
bus.publish("/uav/unregistered_topic", {"dummy": 123}) # Abonesi olmayan konu

print(f"[OK] Tip-Güvenli Pub/Sub Dağıtım Testi Tamamlandı:")
print(f"  - Uçuş Kontrolcüsü Alınan IMU Sayısı : {len(flight_controller_received)} paket (Hedef: 2)")
print(f"  - Kara Kutu Alınan Toplam Paket      : {len(blackbox_received)} paket (Hedef: 3)")
print(f"  - IMU Kanalı Toplam İleti Sayısı     : {bus.message_counters['/uav/sensors/imu']}")

assert len(flight_controller_received) == 2, "Uçuş kontrolcüsü eksik/fazla paket aldı!"
assert len(blackbox_received) == 3, "Kara kutu tüm kanalları dinleyemedi!"
assert bus.message_counters['/uav/unregistered_topic'] == 1, "Kayıtsız konu sayacı hatalı!"
```

## 2.2 Kod Analizi & Bellek Yönetimi: Callback Deadlock ve Reentrancy

Dağıtık Pub/Sub mimarisinde en sık düşülen tuzak **Geri Çağırım Kilitlenmesidir (Callback Deadlock)**:
1. Bir abone geri çağırım (callback) fonksiyonu içinde uzun süren bir matematiksel hesaplama (Örn: Kalman matris tersi alma) veya bloklayan bir I/O işlemi (dosya yazma) yaparsa, **yayıncı iş parçacığını (publisher thread) rehin alır**.
2. Eğer callback fonksiyonu içinden tekrar aynı konuya bir `publish()` çağrısı yapılırsa (**Reentrancy**), iç içe kilitlenme veya yığın taşması (Stack Overflow) meydana gelir.

### Çözüm: Asenkron Yürütme Kuyrukları (Executor Thread Pool)
ROS2 ve modern DDS kütüphaneleri (Fast DDS / Cyclone DDS), callback fonksiyonlarını yayıncının bağlamında değil, bağımsız bir **İşçi İş Parçacığı Havuzunda (Executor Worker Pool)** kuyruğa atarak yürütür. Yayıncı veriyi kuyruğa bıraktığı anda yoluna devam eder.

## 2.3 Edge Case'ler ve Kritik Hatalar: Dağıtık Sistem Tuzakları

| Kritik Hata | Belirti / Sonuç | Kök Neden (Root Cause) | Çözüm / Savunma |
| :--- | :--- | :--- | :--- |
| **Yavaş Abone (Slow Consumer)** | Yayıncının RAM'i şişer ve sistem OOM (Out Of Memory) ile çöker | Abonenin tüketim hızının yayıncının üretim hızından yavaş kalması | `KEEP_LAST` sınırlı kuyruk (depth=N) ve `Drop Oldest` politikası. |
| **Geç Katılan Düğüm (Late Joiner)** | Yeni açılan düğüm ilk veriyi alamayıp kilitlenir | Yayıncının sadece yeni veri geldiğinde basması | `TRANSIENT_LOCAL` Durability QoS (Son durum hafızada tutulup yeni gelene verilir). |
| **Tip Uyuşmazlığı (Type Incompatibility)** | Abone anlamsız çöp veri okur veya çöker | Yayıncı ve abonenin aynı isimli topic için farklı struct tanımları derlemesi | OMG IDL (Interface Definition Language) ile derleme zamanı tip garantisi. |
| **Ağ Ayrışması (Network Split-Brain)** | Filo ikiye bölünür, iki farklı lider seçilir | Telsiz bağlantısının geçici olarak kopması | Lease Duration ve Liveliness QoS kalp atışı (Heartbeat) denetimi. |

## 3.1 Merkezi Broker (MQTT/ROS1) vs Dağıtık Eşler Arası (P2P DDS)

| Kriter | Merkezi Broker (MQTT / ROS1 roscore) | Dağıtık P2P (DDS / ROS2) | Savunma Sanayii Gerekçesi |
| :--- | :--- | :--- | :--- |
| **Arıza Noktası** | **Tek Nokta Arızası (SPoF):** Broker çökerse sistem biter | **Sıfır SPoF:** Her düğüm bağımsız eş (Peer) olarak yaşar | **DDS Tercih Edilir:** Füze saldırısında hiçbir sunucu tek başına kritik olamaz. |
| **Gecikme (Latency)** | Çift Atlamalı: `Düğüm A -> Broker -> Düğüm B` (~2-10 ms) | Doğrudan: `Düğüm A -> Düğüm B` (**< 100 µs**) | **DDS Tercih Edilir:** Uçuş kontrol döngüsünde 1 ms bile gecikme tolere edilemez. |
| **Bant Genişliği** | Broker ağ kartında tüm filo trafiği toplanır (Darboğaz) | Trafik ağdaki anahtarlar üzerinden paralel dağılır | **DDS Tercih Edilir:** Yüksek çözünürlüklü radar/FLIR akışı taşınabilir. |
| **Keşif (Discovery)** | Düğümler statik olarak Broker IP'sine yönlendirilir | Dinamik UDP Multicast ile birbirini otomatik bulur | **DDS Tercih Edilir:** Savaş alanına yeni katılan İHA anında ağa dahil olur. |

```python
# Kod Hücresi 3: Merkezi Broker Çökmesi (SPoF) vs Dağıtık P2P Ağ Dayanıklılık Karşılaştırması
class CentralBrokerNetwork:
    """Merkezi Sunucuya Bağımlı Ağ Modeli (MQTT / ROS1 roscore)"""
    def __init__(self):
        self.broker_alive = True
        self.delivered_count = 0

    def crash_broker(self):
        self.broker_alive = False

    def send_message(self, sender, data):
        if not self.broker_alive:
            return False, "ERR_BROKER_DOWN_SPOF"
        self.delivered_count += 1
        return True, "DELIVERED"

class DistributedP2PNetwork:
    """Eşler Arası Dağıtık Ağ Modeli (DDS / ROS2 RTPS)"""
    def __init__(self, node_list):
        self.nodes = {name: True for name in node_list} # Düğüm sağlık tablosu
        self.delivered_count = 0

    def kill_node(self, node_name):
        if node_name in self.nodes:
            self.nodes[node_name] = False

    def send_p2p(self, sender, receiver, data):
        # İletişim için sadece gönderici ve alıcının ayakta olması yeterlidir!
        if self.nodes.get(sender, False) and self.nodes.get(receiver, False):
            self.delivered_count += 1
            return True, "DELIVERED"
        return False, "ERR_PEER_UNREACHABLE"

# Test Senaryosu: t=50 ms Anında Merkezi Sunucu / Lider Düğüm Çöküyor
broker_net = CentralBrokerNetwork()
p2p_net = DistributedP2PNetwork(["UAV_Leader", "UAV_Wingman_1", "UAV_Wingman_2", "Radar_Node"])

# 1. Aşama: İlk 10 mesaj normal iletiliyor
for i in range(10):
    broker_net.send_message("UAV_Wingman_1", "DATA")
    p2p_net.send_p2p("UAV_Wingman_1", "UAV_Wingman_2", "DATA")

# 2. Aşama: KRİZ! Merkezi sunucu çöküyor, P2P ağda ise sadece Lider vuruluyor!
broker_net.crash_broker()
p2p_net.kill_node("UAV_Leader")

# Kriz sonrası 10 mesaj iletim denemesi (Wingman-1 ile Wingman-2 arasında)
broker_fails = 0
p2p_success = 0

for i in range(10):
    ok_b, _ = broker_net.send_message("UAV_Wingman_1", "DATA")
    if not ok_b: broker_fails += 1
    
    ok_p, _ = p2p_net.send_p2p("UAV_Wingman_1", "UAV_Wingman_2", "DATA")
    if ok_p: p2p_success += 1

print(f"[OK] SPoF Dayanıklılık Testi Tamamlandı:")
print(f"  - Merkezi Broker Başarısızlık Oranı : %{(broker_fails / 10) * 100:.1f} (Tüm Filo Kilitlendi)")
print(f"  - Dağıtık P2P Başarı Oranı          : %{(p2p_success / 10) * 100:.1f} (Lider Çökse de Kalanlar Çalışıyor)")

assert broker_fails == 10, "Broker çöküşü iletişimi durduramadı!"
assert p2p_success == 10, "P2P ağ diğer eşler arasında çalışmayı sürdüremedi!"
```

## 3.2 Hata Enjeksiyonu: Yavaş Abone (Slow Consumer) ve Bellek Tüketim Patlaması

Dağıtık sistemlerin en ölümcül hatası, hızlı bir yayıncının (Örn: 1000 Hz Radar DSP) yavaş bir aboneye (Örn: 20 Hz disk kaydedici) veri basmasıdır:
- Eğer yayıncı abonenin almasını beklemek için kuyruk sınırını kaldırmışsa (`Unbounded Queue`), dakikalar içinde yüz binlerce mesaj RAM'de birikir ve işletim sistemi **OOM-Killer (Out of Memory)** ile süreci öldürür.
- **DDS Çözümü:** `History QoS: KEEP_LAST (depth = N)`. Kuyrukta yalnızca en son $N$ adet mesaj tutulur; yeni gelen her mesaj en eskisini ezer.

```python
# Kod Hücresi 4: Kırılma Senaryosu: Sınırsız Kuyruk Bellek Sızıntısı vs History QoS (KEEP_LAST)
class UnboundedConsumerQueue:
    """TEHLİKELİ (Anti-Pattern): Sınırsız Kuyruk (OOM Riski)"""
    def __init__(self):
        self.buffer = []

    def push(self, data):
        self.buffer.append(data) # Asla silmez, sonsuz büyür!

    def get_memory_usage_elements(self):
        return len(self.buffer)

class BoundedHistoryQoSQueue:
    """DDS / ROS2 Standardı: History QoS = KEEP_LAST, depth = 5"""
    def __init__(self, depth=5):
        self.depth = depth
        self.buffer = []
        self.dropped_count = 0

    def push(self, data):
        if len(self.buffer) >= self.depth:
            self.buffer.pop(0) # En eskiyi sil (Drop Oldest)
            self.dropped_count += 1
        self.buffer.append(data)

    def get_memory_usage_elements(self):
        return len(self.buffer)

# Simülasyon: Hızlı Yayıncı 1000 Paket Üretiyor, Yavaş Abone Hiç Tüketemiyor
unbounded = UnboundedConsumerQueue()
bounded = BoundedHistoryQoSQueue(depth=5)

for i in range(1000):
    unbounded.push(f"RADAR_DATA_{i}")
    bounded.push(f"RADAR_DATA_{i}")

print(f"[OK] Yavaş Abone Bellek Yönetimi Testi:")
print(f"  - Üretilen Toplam Mesaj       : 1000 paket")
print(f"  - Sınırsız Kuyruk RAM Elemanı : {unbounded.get_memory_usage_elements()} paket (Bellek Şişmesi!)")
print(f"  - Bounded QoS RAM Elemanı     : {bounded.get_memory_usage_elements()} paket (Sabit Sınır)")
print(f"  - Bounded Atılan Paket Sayısı : {bounded.dropped_count} paket")

assert unbounded.get_memory_usage_elements() == 1000, "Sınırsız kuyruk boyutu hatalı!"
assert bounded.get_memory_usage_elements() == 5, "Bounded kuyruk sınırı aştı!"
assert bounded.dropped_count == 995, "Atılan paket sayısı uyuşmuyor!"
```

## 3.3 Hata Analizi ve Düzeltme Stratejisi: QoS Kontratı (Request vs Offered)

Dağıtık Pub/Sub mimarisinde bir abonenin bir yayıncıya bağlanabilmesi için yalnızca konu adlarının uyuşması yetmez; **QoS Politikalarının Uyuşması (QoS Compatibility Contract)** gerekir:

- **Offered QoS (Yayıncının Vaat Ettiği):** "Ben bu veriyi `BEST_EFFORT` (Kayıp olabilir) gönderiyorum."
- **Requested QoS (Abonenin Talep Ettiği):** "Ben bu veriyi kesinlikle `RELIABLE` (Sıfır kayıp) almak zorundayım!"
- **Sonuç:** QoS Uyuşmazlığı (`QoS Incompatible`)! DDS altyapısı bu bağlantıyı bilerek kurmaz ve hata üretir. Çünkü güvenilirlik garantisi verilemeyecek bir hatta kritik kontrol kodunun çalıştırılması güvenlik ihlalidir.

## 4.1 Savunma Sanayiinde Dağıtık Pub/Sub: HAVELSAN ADVENT & Sürü İHA Sistemleri

Türkiye'nin milli fırkateynlerinde (MİLGEM) ve TCG ANADOLU gemisinde kullanılan **HAVELSAN ADVENT Savaş Yönetim Sistemi**:
- Dünyanın en gelişmiş veri odaklı (data-centric) ağlarından biridir.
- Gemideki radarlar, sonar, elektronik harp ve füze fırlatma sistemleri tek bir merkezi sunucuya değil, **DDS tabanlı küresel bir veri alanına (Global Data Space)** bağlıdır.
- Bir fırkateyndeki radarın tespit ettiği hedef, DDS üzerinden saniyeler içinde yüzlerce kilometre ötedeki diğer gemilerin ve İHA'ların ekranına tek bir `publish()` ile akar.

```python
# Kod Hücresi 5: Üretim Seviyesi 5-Düğümlü Sürü İHA Görev Ağı Simülasyonu (Leader + 3 Followers + GCS)
class SwarmUavNode:
    """Sürü İHA Ağ Düğümü (Hem Yayıncı Hem Abone)"""
    def __init__(self, uav_id, role, bus_ref):
        self.uav_id = uav_id
        self.role = role
        self.bus = bus_ref
        self.current_pos = [0.0, 0.0, 100.0]
        self.received_formation_cmds = []
        self.received_peer_telemetries = []
        
        # Abonelikler
        if self.role == "FOLLOWER":
            self.bus.subscribe("/swarm/cmd/formation", self.on_formation_cmd)
        self.bus.subscribe("/swarm/telemetry/broadcast", self.on_peer_telemetry)

    def on_formation_cmd(self, topic, cmd):
        self.received_formation_cmds.append(cmd)

    def on_peer_telemetry(self, topic, telem):
        if telem["id"] != self.uav_id:
            self.received_peer_telemetries.append(telem)

    def step(self, t_ms):
        # Her İHA periyodik olarak kendi telemetrisini yayar
        telem = {
            "id": self.uav_id,
            "timestamp": t_ms,
            "pos": list(self.current_pos),
            "status": "ENGAGED"
        }
        self.bus.publish("/swarm/telemetry/broadcast", telem)
        
        # Eğer liderse formasyon komutu basar
        if self.role == "LEADER" and t_ms % 100 == 0:
            cmd = {"cmd_seq": t_ms // 100, "formation": "V_SHAPE", "target_speed": 120.0}
            self.bus.publish("/swarm/cmd/formation", cmd)

# 5 Düğümlü Ağın Kurulması
swarm_bus = DistributedTopicBus()
leader = SwarmUavNode("UAV_Leader", "LEADER", swarm_bus)
follower_1 = SwarmUavNode("UAV_Follower_1", "FOLLOWER", swarm_bus)
follower_2 = SwarmUavNode("UAV_Follower_2", "FOLLOWER", swarm_bus)
follower_3 = SwarmUavNode("UAV_Follower_3", "FOLLOWER", swarm_bus)
gcs = SwarmUavNode("GCS_GroundStation", "MONITOR", swarm_bus) # Yer Kontrol İstasyonu

# 500 ms'lik Sürü Görevi Simülasyonu (50 ms adımlarla)
for t in range(0, 500, 50):
    for uav in [leader, follower_1, follower_2, follower_3, gcs]:
        uav.step(t)

print(f"[OK] 5-Düğümlü Sürü İHA Dağıtık Görev Simülasyonu Tamamlandı:")
print(f"  - Takipçi 1 Alınan Formasyon Komutu : {len(follower_1.received_formation_cmds)} komut")
print(f"  - Takipçi 1 Alınan Akran Telemetrisi: {len(follower_1.received_peer_telemetries)} paket")
print(f"  - Yer İstasyonu Alınan Telemetri   : {len(gcs.received_peer_telemetries)} paket")

# 500 ms içinde 0, 100, 200, 300, 400. ms'lerde olmak üzere 5 formasyon komutu basılır
assert len(follower_1.received_formation_cmds) == 5, "Formasyon komutu sayısı hatalı!"
assert len(follower_2.received_formation_cmds) == 5, "Follower 2 komut alamadı!"
assert len(follower_3.received_formation_cmds) == 5, "Follower 3 komut alamadı!"
assert len(gcs.received_peer_telemetries) > 0, "Yer istasyonu telemetri alamadı!"
```

## 4.2 Benchmark ve Performans Çıkarımları: İletişim Mimarileri Karşılaştırması

| Mimari Türü | Bağlantı Modeli | Gecikme (Latency) | SPoF Riski | Throughput | En Uygun Senaryo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REST / HTTP JSON** | İstemci-Sunucu TCP | $15 - 50\,\text{ms}$ | Yüksek (Sunucu) | Düşük (<5 MB/s) | Web arayüzleri, bulut raporlama |
| **gRPC / Protobuf** | İstemci-Sunucu TCP | $2 - 5\,\text{ms}$ | Yüksek (Sunucu) | Orta (~20 MB/s) | Mikroservis arka uç sistemleri |
| **MQTT Broker** | Merkezi Broker TCP | $1 - 3\,\text{ms}$ | **Kritik (Broker)** | Orta (~15 MB/s) | IoT telemetrisi, akıllı ev sistemleri |
| **DDS RTPS (P2P)** | **Eşler Arası Multicast**| **$30 - 150\,\mu\text{s}$**| **SIFIR (No SPoF)**| **Çok Yüksek (>250 MB/s)**| **Aviyonik, Sürü İHA, Radar, Robotik** |

```python
# Kod Hücresi 6: Profesyonel 4-Panelli Dağıtık Pub/Sub Performans Dashboard'u (Dark Theme)
import os
import matplotlib.pyplot as plt
import numpy as np

# Robust Fallback for PNG_FILE
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_196_distributed_pub_sub_problemi.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_196\gun_196_distributed_pub_sub_problemi.png"

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
# PANEL 1: Bağlantı Karmaşıklığı: P2P TCP Mesh O(N^2) vs Broker vs P2P Pub/Sub
# ------------------------------------------------------------------------------
node_range = np.array([2, 4, 8, 16, 32, 48, 64])
p2p_mesh = node_range * (node_range - 1) / 2
broker_linear = node_range
pubsub_const = np.ones_like(node_range) * 1 # Düğüm başına 1 multicast kanalı

axs[0, 0].plot(node_range, p2p_mesh, color='#EF4444', linewidth=2.5, marker='o', label='P2P TCP Mesh: O(N²)')
axs[0, 0].plot(node_range, broker_linear, color='#F59E0B', linewidth=2.0, linestyle='--', marker='s', label='Merkezi Broker: O(N)')
axs[0, 0].plot(node_range, pubsub_const * node_range, color='#10B981', linewidth=2.0, linestyle='-', marker='^', label='DDS P2P Multicast')

axs[0, 0].set_title("Panel 1: Düğüm Sayısına Göre Ağ Bağlantı Sayısı Patlaması", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[0, 0].set_xlabel("Sistemdeki Düğüm Sayısı (N)", fontsize=9, color='#CBD5E1')
axs[0, 0].set_ylabel("Gereken Fiziksel Bağlantı Sayısı", fontsize=9, color='#CBD5E1')
axs[0, 0].set_yscale('log')
axs[0, 0].legend(loc='upper left', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

# ------------------------------------------------------------------------------
# PANEL 2: SPoF Dayanıklılığı: Merkezi Broker Çöküşü vs P2P İletim Akışı
# ------------------------------------------------------------------------------
timeline_ms = np.linspace(0, 100, 100)
broker_flow = np.ones_like(timeline_ms) * 50
broker_flow[timeline_ms >= 50] = 0 # 50. ms'de broker çöktü! Sıfıra indi!

p2p_flow = np.ones_like(timeline_ms) * 50
# 50. ms'de lider vuruldu ama eşler arası iletişim %80 devam ediyor
p2p_flow[timeline_ms >= 50] = 40

axs[0, 1].plot(timeline_ms, broker_flow, color='#EF4444', linewidth=2.5, label='Merkezi Broker (Broker Çökünce %0)')
axs[0, 1].plot(timeline_ms, p2p_flow, color='#10B981', linewidth=2.5, label='DDS P2P (Lider Vurulsada Akranlar Devam)')
axs[0, 1].axvline(50, color='#F59E0B', linestyle=':', linewidth=2, label='Arıza Enjeksiyonu (t=50 ms)')

axs[0, 1].set_title("Panel 2: SPoF Dayanıklılığı: Broker Çöküşü vs Eşler Arası P2P", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[0, 1].set_xlabel("Zaman (Milisaniye - ms)", fontsize=9, color='#CBD5E1')
axs[0, 1].set_ylabel("Saniyedeki Başarılı Paket", fontsize=9, color='#CBD5E1')
axs[0, 1].legend(loc='lower left', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

# ------------------------------------------------------------------------------
# PANEL 3: Yavaş Abone (Slow Consumer) Bellek Tüketim Farkı
# ------------------------------------------------------------------------------
msgs_produced = np.linspace(0, 500, 100)
unbounded_mem = msgs_produced # Sınırsız büyüyor
bounded_mem = np.minimum(msgs_produced, 10) # Depth = 10 ile sabitlenmiş

axs[1, 0].plot(msgs_produced, unbounded_mem, color='#EF4444', linewidth=2.5, label='Sınırsız Kuyruk (OOM Crash Riski)')
axs[1, 0].plot(msgs_produced, bounded_mem, color='#38BDF8', linewidth=2.5, label='DDS History QoS (KEEP_LAST, depth=10)')
axs[1, 0].fill_between(msgs_produced, unbounded_mem, color='#EF4444', alpha=0.15)

axs[1, 0].set_title("Panel 3: Yavaş Abone: Sınırsız Kuyruk vs History QoS Bellek Tüketimi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[1, 0].set_xlabel("Yayınlanan Mesaj Sayısı", fontsize=9, color='#CBD5E1')
axs[1, 0].set_ylabel("Kuyruktaki Paket Sayısı", fontsize=9, color='#CBD5E1')
axs[1, 0].legend(loc='upper left', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

# ------------------------------------------------------------------------------
# PANEL 4: Sürü İHA Dağıtık P2P Gecikme (Latency) Dağılımı (µs)
# ------------------------------------------------------------------------------
np.random.seed(42)
dds_latencies_us = np.random.normal(loc=75.4, scale=12.2, size=500)
dds_latencies_us = np.clip(dds_latencies_us, 40, 150)

n, bins, patches = axs[1, 1].hist(dds_latencies_us, bins=25, color='#10B981', alpha=0.8, edgecolor='#0F172A')
axs[1, 1].axvline(np.mean(dds_latencies_us), color='#F59E0B', linestyle='--', linewidth=2, label=f"Ortalama: {np.mean(dds_latencies_us):.1f} µs")
axs[1, 1].axvline(np.mean(dds_latencies_us) + 3*np.std(dds_latencies_us), color='#38BDF8', linestyle=':', linewidth=1.5, label=f"3-Sigma: {np.mean(dds_latencies_us)+3*np.std(dds_latencies_us):.1f} µs")

axs[1, 1].set_title("Panel 4: DDS P2P Uçtan Uca Gecikme Dağılımı (Mikrosaniye - µs)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
axs[1, 1].set_xlabel("Gecikme Süresi (µs)", fontsize=9, color='#CBD5E1')
axs[1, 1].set_ylabel("Örnek Sayısı", fontsize=9, color='#CBD5E1')
axs[1, 1].legend(loc='upper right', framealpha=0.8, facecolor='#0F172A', edgecolor='#475569', fontsize=8)

plt.tight_layout()
fig.subplots_adjust(top=0.92)
fig.suptitle("ASELSAN / HAVELSAN DAĞITIK SİSTEMLER — GÜN 196: DISTRIBUTED PUB/SUB PARADIGM & DECOUPLING", 
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
1. **Ad Alanı (Namespace) Standartlaşması:** Konu isimlerini rastgele seçmeyin; kurumsal bir aviyonik şeması tanımlayın: `/<sistem>/<düğüm_id>/<alt_sistem>/<veri_adı>`.
2. **Kuyruk Derinliklerini Sınırlandırın (Bounded Queues):** Asla varsayılan sınırsız kuyruk kullanmayın; telemetri için `depth=1..5`, kritik komutlar için `depth=20..50` verin.
3. **IDL ile Şema Doğrulama:** Mesaj tiplerini elle yazmak yerine OMG IDL dosyaları tanımlayarak C++/Python kodlarını otomatik derleyicilerle (`fastddsgen`) üretin.

### Kaçınılması Gereken Hatalar (DON'Ts - Anti-Patterns)
1. **Callback İçinde Ağır İşlem Yapmak:** Abone fonksiyonu içinde disk I/O veya karmaşık matris hesaplaması yapmayın; veriyi bir iç kuyruğa atıp callback'ten hemen çıkın.
2. **Kritik Kontrolde MQTT Kullanmak:** Savaş sahasında merkezi broker mimarileri kullanmayın; broker çöküşü tüm filoyu öldürür.
3. **Polymorphic / Dynamic Typing Kullanmak:** Güvenlik kritik sistemlerde JSON veya Python pickle gibi çalışma anı tipleri kullanmayın; statik tipli ikili serileştirme (CDR - Common Data Representation) kullanın.

## 4.4 Mülakat Soruları ve Yanıtları

### Soru 1: Dağıtık Pub/Sub mimarisinde "Üç Boyutlu Ayrışma (Three Dimensions of Decoupling)" nedir?
**Cevap:** Eugster et al. (2003) tarafından tanımlanan bu üç boyut:
1. **Mekan Ayrışması (Space Decoupling):** Yayıncı ve abone birbirinin IP adresi veya portunu bilmez; yalnızca konu (topic) ismini bilir. Düğümler ağda serbestçe yer değiştirebilir.
2. **Zaman Ayrışması (Time Decoupling):** Tarafların aynı anda çalışır durumda olması gerekmez. Kalıcılık politikaları (Durability) sayesinde bir düğüm kapalıyken yayınlanan kritik veri, düğüm açıldığında teslim edilir.
3. **Senkronizasyon Ayrışması (Synchronization Decoupling):** Yayıncı mesajı gönderirken abonenin işlemi bitirmesini beklemez; asenkron olarak hemen döner ($O(1)$).

### Soru 2: ROS1'deki `roscore` mimarisi neden ROS2'de terk edilmiş ve DDS tercih edilmiştir?
**Cevap:** ROS1'deki `roscore`, XML-RPC tabanlı merkezi bir aracıydı. Tüm düğümler birbirini bulmak için `roscore`'a kayıt olmak zorundaydı. Bu durum iki büyük felaket yaratıyordu: (1) `roscore` çöktüğünde tüm robot kör oluyordu (Tek Nokta Arızası - SPoF), (2) Gerçek zamanlı değildi ve haberleşmenin koptuğu askeri/telsiz ortamlarında yeniden bağlanamıyordu. ROS2 ise merkezi olmayan, donanımsal UDP Multicast ile çalışan ve endüstri standardı QoS politikaları sunan eşler arası (P2P) DDS mimarisine geçmiştir.

### Soru 3: "Slow Consumer" (Yavaş Abone) problemi dağıtık bir sistemde nasıl yönetilir?
**Cevap:** Yavaş çalışan bir abone, yayıncının bellek tüketimini patlatabilir. Çözüm: (1) `History QoS = KEEP_LAST` ve küçük bir kuyruk derinliği (`depth = 1..10`) belirlenerek eski mesajlar otomatik atılır. (2) `Reliability QoS = BEST_EFFORT` seçilerek yayıncının onay (ACK) beklemesi engellenir. (3) Abone tarafında callback'ler çok iş parçacıklı bir çalıştırıcı havuzuna (Multi-threaded Executor Pool) devredilerek ana dinleyici soketi rahatlatılır.

## 4.5 Bilgi Kontrolü (Self-Check Test)

### 1. N düğümlü tam bağlı (Full Mesh) bir noktadan noktaya TCP ağında kaç adet bağlantı açılmalıdır?
- A) N
- B) N * (N - 1) / 2
- C) 2 * N
- D) N^3
*Cevap: B. Her düğüm çifti arasında 1 hat olacağından N*(N-1)/2 bağlantı gerekir.*

### 2. Yayıncı ve abonenin birbirlerinin IP adresini bilmeden sadece "Topic" adı üzerinden haberleşmesi hangi ayrışma boyutudur?
- A) Zaman Ayrışması (Time Decoupling)
- B) Mekan Ayrışması (Space Decoupling)
- C) Senkronizasyon Ayrışması
- D) Veri Tabanı Ayrışması
*Cevap: B. IP/port bağımlılığının kalkması Mekan (Space) ayrışmasıdır.*

### 3. Savunma sanayiinde merkezi broker mimarileri yerine P2P DDS kullanılmasının en kritik sebebi nedir?
- A) P2P mimarisinin daha renkli loglar üretmesi
- B) Merkezi broker'ın Tek Nokta Arıza Noktası (SPoF) olması ve çöküşünde tüm filoyu felç etmesi
- C) P2P mimaride şifrelemenin imkansız olması
- D) DDS'in sadece Java desteklemesi
*Cevap: B. Askeri sistemlerde tek bir sunucunun çöküşü kabul edilemez bir risktir.*

### 4. Çok hızlı veri üreten bir sensörün yavaş bir aboneyi boğmasını engellemek için hangi History QoS politikası kullanılır?
- A) KEEP_ALL (Sonsuz kuyruk)
- B) KEEP_LAST (Derinlik = N, en eskiyi at)
- C) DELETE_ALL
- D) BLOCK_PUBLISHER
*Cevap: B. KEEP_LAST kuyruk taşmasında eski paketleri düşürerek belleği korur.*

### 5. Donanımsal IP Multicast kullanımının Unicast'e göre en büyük avantajı nedir?
- A) Yayıncının tek bir paketi ağ kartına basması ve çoğaltmanın ağ anahtarı (Switch) tarafından yapılması
- B) Multicast'in internette her yere şifresiz yayılması
- C) CPU saat frekansını artırması
- D) Kablo gerektirmemesi
*Cevap: A. Donanımsal çoğaltma yayıncı CPU'sunun fan-out yükünü sıfıra indirir.*

## 4.6 Günün Sözü ve Düşünce Sorusu

> *"Bir orkestrada her müzisyenin diğer tüm müzisyenlere tek tek bakarak çalması imkansızdır; müzisyenler partisyona (Topic) odaklanır ve orkestra eşzamanlı bir armoniyle akar."*

### Düşünce Sorusu
Bir insansız savaş uçağında füze fırlatma komutu gibi **asla kaybolmaması gereken** bir mesaj ile 500 Hz jiroskop telemetrisi gibi **kaybolsa da yenisi anında gelen** bir mesaj aynı dağıtık veriyolunda nasıl farklı muamele görmelidir?
**Cevap:** QoS (Hizmet Kalitesi) profilleriyle ayrılır. Füze komutu `RELIABLE` (onaylı ve tekrar iletimli) ve `TRANSIENT_LOCAL` (geçici kalıcı) QoS ile gönderilirken; jiroskop telemetrisi `BEST_EFFORT` (en iyi gayret, onaysız) ve `VOLATILE` QoS ile basılır. Böylece yüksek hızlı telemetri hatta gecikme yaratmazken, kritik komut %100 güvence altına alınır.

## 5.1 İleri Düzey Okuma ve Kaynakça

1. **Eugster, P. T., Felber, P. A., Guerraoui, R., & Kermarrec, A. M. (2003):** *The many faces of publish/subscribe.* ACM Computing Surveys (CSUR), 35(2), 114-131.
2. **Object Management Group (OMG):** *Data Distribution Service (DDS) Specification, v1.4.*
3. **ROS2 Design Documentation:** *Why ROS 2 uses DDS - Changes between ROS 1 and ROS 2.* https://design.ros2.org/articles/ros_on_dds.html
4. **eProsima:** *Fast DDS User Manual - Real-Time Publish Subscribe (RTPS) Protocol Architecture.*

## 5.2 Gün Sonu Özeti ve Özel Lisans

### Günün Özeti (3 Cümlelik Kural)
1. **Dağıtık Pub/Sub Paradigması Nedir?:** Yayıncılar ile aboneleri Mekan (IP bağımsız), Zaman (asenkron) ve Senkronizasyon boyutlarında ayıran, konu tabanlı eşler arası dağıtık iletişim mimarisidir.
2. **Hangi Problemi Çözer?:** Noktadan noktaya ağların $O(N^2)$ bağlantı patlamasını, merkezi aracıların (Broker) Tek Nokta Arızası (SPoF) riskini ve sıkı bağımlılıkları ortadan kaldırır.
3. **Hangi Trade-off / Hata Sınıfını Getirir?:** Ağ trafiğinin yönetimi için karmaşık QoS (Hizmet Kalitesi) politikaları gerektirir; yanlış yapılandırılmış kuyruklar Yavaş Abone (Slow Consumer) bellek sızıntısına yol açar.

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

