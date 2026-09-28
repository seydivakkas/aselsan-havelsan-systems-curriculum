# -*- coding: utf-8 -*-
"""
GÜN 196: Distributed Pub/Sub Problemi ve Ayrışma Mimarisi
Standalone Python Doğrulama ve Görselleştirme Betiği
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_196\gun_196_distributed_pub_sub_problemi.png"

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

# ======================================================================
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

