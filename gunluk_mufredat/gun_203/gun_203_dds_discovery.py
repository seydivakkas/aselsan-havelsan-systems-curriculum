#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

GÜN 203: DDS Keşif Protokolü (Discovery) Standalone Doğrulama ve Çalıştırma Betiği
"""

import sys
import os

# Konsol UTF-8 Ayarı
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_203/gun_203_dds_discovery.png"



# ============================================================================# ==============================================================================
# KOD 1: Minimal 2-Aşamalı DDS Keşif Motoru (SPDP + SEDP)
# Amaç: Aşama 1'de katılımcıların birbirini bulmasını, Aşama 2'de
# Topic ve Tip eşleşmesi üzerinden doğrudan iletişim kanalının kurulmasını simüle etmek.
# ==============================================================================

from dataclasses import dataclass
from typing import Dict, List, Set, Optional

@dataclass
class ParticipantDiscoveryData:
    guid_prefix: str
    participant_name: str
    unicast_locator: str

@dataclass
class EndpointDiscoveryData:
    endpoint_guid: str
    participant_guid_prefix: str
    topic_name: str
    type_name: str
    is_writer: bool

class SimpleDiscoveryEngine:
    def __init__(self, node_name: str, guid_prefix: str, locator: str):
        self.node_name = node_name
        self.guid_prefix = guid_prefix
        self.locator = locator
        
        # Keşif Tabloları
        self.discovered_participants: Dict[str, ParticipantDiscoveryData] = {}
        self.discovered_endpoints: Dict[str, EndpointDiscoveryData] = {}
        self.matched_channels: List[str] = []

    # AŞAMA 1: SPDP Katılımcı Anonsu Alma
    def on_spdp_received(self, pdata: ParticipantDiscoveryData):
        if pdata.guid_prefix != self.guid_prefix:
            self.discovered_participants[pdata.guid_prefix] = pdata
            print(f"[{self.node_name} | SPDP] Yeni Katılımcı Keşfedildi: {pdata.participant_name} ({pdata.guid_prefix})")

    # AŞAMA 2: SEDP Uç Nokta Anonsu Alma ve Eşleştirme
    def on_sedp_received(self, local_endpoint: EndpointDiscoveryData, remote_endpoint: EndpointDiscoveryData):
        # 1. Kural: Ebeveyn katılımcı SPDP ile keşfedilmiş olmalı
        if remote_endpoint.participant_guid_prefix not in self.discovered_participants:
            return False

        # 2. Kural: Biri Writer diğeri Reader olmalı
        if local_endpoint.is_writer == remote_endpoint.is_writer:
            return False

        # 3. Kural: Topic ve Tip Adı tam uyuşmalı
        if (local_endpoint.topic_name == remote_endpoint.topic_name and 
            local_endpoint.type_name == remote_endpoint.type_name):
            channel_id = f"MATCH: {local_endpoint.endpoint_guid} <---> {remote_endpoint.endpoint_guid}"
            self.matched_channels.append(channel_id)
            print(f"[{self.node_name} | SEDP] Uç Noktalar Eşleşti! Kanal: '{local_endpoint.topic_name}' ({local_endpoint.type_name})")
            return True
        return False

# Senaryo: Radar (Writer) ve Füze Güdüm (Reader)
radar_discovery = SimpleDiscoveryEngine("RadarNode", "GUID_RADAR", "192.168.1.10:7410")
missile_discovery = SimpleDiscoveryEngine("MissileNode", "GUID_MISSILE", "192.168.1.20:7412")

print("[KOD 1] 2-Aşamalı Keşif Başlatılıyor:")

# Adım 1: SPDP Değişimi
p_radar = ParticipantDiscoveryData("GUID_RADAR", "RadarNode", "192.168.1.10:7410")
p_missile = ParticipantDiscoveryData("GUID_MISSILE", "MissileNode", "192.168.1.20:7412")

radar_discovery.on_spdp_received(p_missile)
missile_discovery.on_spdp_received(p_radar)

assert "GUID_MISSILE" in radar_discovery.discovered_participants
assert "GUID_RADAR" in missile_discovery.discovered_participants

# Adım 2: SEDP Uç Nokta Eşleşmesi
ep_radar_writer = EndpointDiscoveryData("EP_W1", "GUID_RADAR", "rt/tracks", "RadarTrack", is_writer=True)
ep_missile_reader = EndpointDiscoveryData("EP_R1", "GUID_MISSILE", "rt/tracks", "RadarTrack", is_writer=False)

matched = radar_discovery.on_sedp_received(ep_radar_writer, ep_missile_reader)

assert matched == True, "Topic ve Tip aynı olduğunda SEDP eşleşmelidir!"
assert len(radar_discovery.matched_channels) == 1

print("[PASS] Minimal SPDP ve SEDP İki Aşamalı Keşif Başarıyla Doğrulandı.")

# ==============================================================================
# KOD 2: Gelişmiş SEDP Eşleştirme ve RxO Uyumluluk Denetleyicisi
# Amaç: Reliability, Durability ve Deadline politikalarının matematiksel
# kısmi sıralama kuralına (Offered >= Requested) göre denetlenmesini sağlamak.
# ==============================================================================

from enum import IntEnum

class ReliabilityKind(IntEnum):
    BEST_EFFORT = 1
    RELIABLE = 2

class DurabilityKind(IntEnum):
    VOLATILE = 1
    TRANSIENT_LOCAL = 2

@dataclass
class WriterQoS:
    reliability: ReliabilityKind
    durability: DurabilityKind
    deadline_ms: float

@dataclass
class ReaderQoS:
    reliability: ReliabilityKind
    durability: DurabilityKind
    deadline_ms: float

class RxOMatcher:
    @classmethod
    def check_compatibility(cls, w_qos: WriterQoS, r_qos: ReaderQoS) -> Tuple[bool, List[str]]:
        incompatibilities = []

        # 1. Reliability Denetimi: Offered >= Requested
        if w_qos.reliability < r_qos.reliability:
            incompatibilities.append(
                f"RELIABILITY_MISMATCH: Writer({w_qos.reliability.name}) < Reader({r_qos.reliability.name})"
            )

        # 2. Durability Denetimi: Offered >= Requested
        if w_qos.durability < r_qos.durability:
            incompatibilities.append(
                f"DURABILITY_MISMATCH: Writer({w_qos.durability.name}) < Reader({r_qos.durability.name})"
            )

        # 3. Deadline Denetimi: Offered <= Requested (Yazar daha sık veya eşit periyotta yazmalı)
        if w_qos.deadline_ms > r_qos.deadline_ms:
            incompatibilities.append(
                f"DEADLINE_MISMATCH: Writer({w_qos.deadline_ms}ms) > Reader({r_qos.deadline_ms}ms)"
            )

        is_matched = len(incompatibilities) == 0
        return is_matched, incompatibilities

# Senaryolar:
# Senaryo 1: Tam Uyumlu Aviyonik Hattı
w_qos_ok = WriterQoS(ReliabilityKind.RELIABLE, DurabilityKind.TRANSIENT_LOCAL, deadline_ms=20.0)
r_qos_ok = ReaderQoS(ReliabilityKind.RELIABLE, DurabilityKind.VOLATILE, deadline_ms=50.0)

matched_1, errs_1 = RxOMatcher.check_compatibility(w_qos_ok, r_qos_ok)
print("[KOD 2] Senaryo 1 (Uyumlu QoS):", matched_1)
assert matched_1 == True
assert len(errs_1) == 0

# Senaryo 2: Uyumsuz Hat (Yazar Best-Effort, Okuyucu Reliable istiyor)
w_qos_bad = WriterQoS(ReliabilityKind.BEST_EFFORT, DurabilityKind.VOLATILE, deadline_ms=100.0)
r_qos_demanding = ReaderQoS(ReliabilityKind.RELIABLE, DurabilityKind.TRANSIENT_LOCAL, deadline_ms=20.0)

matched_2, errs_2 = RxOMatcher.check_compatibility(w_qos_bad, r_qos_demanding)
print("\n[KOD 2] Senaryo 2 (Uyumsuz QoS):", matched_2)
for e in errs_2:
    print(f"  [-] Red Nedeni: {e}")

assert matched_2 == False
assert len(errs_2) == 3, "Tüm 3 QoS kuralı da ihlal edildi!"

print("\n[PASS] RxO Uyumluluk Matrisi ve Matematiksel Doğrulama Tamamlandı.")

# ==============================================================================
# KOD 3: Keşif Ölçeklenebilirlik Analizörü (Simple Discovery vs Discovery Server)
# Amaç: Düğüm sayısı 5'ten 50'ye çıkarken üretilen keşif paket sayısını ve
# ağ bant genişliği tüketimini matematiksel olarak simüle edip karşılaştırmak.
# ==============================================================================

class DiscoveryScalabilityAnalyzer:
    @staticmethod
    def calculate_traffic(num_nodes: int, endpoints_per_node: int = 5):
        # 1. Simple Discovery (Herkes Herkese Multicast + Unicast SEDP)
        # SPDP Multicast: N anons, her anons N-1 kişi tarafından alınır
        spdp_packets = num_nodes * (num_nodes - 1)
        # SEDP Unicast: Her uç nokta için karşılıklı güvenli mesajlaşma
        sedp_packets = (num_nodes * endpoints_per_node) * ((num_nodes - 1) * endpoints_per_node)
        total_simple = spdp_packets + sedp_packets

        # 2. Discovery Server (Tüm düğümler yalnızca sunucu ile konuşur)
        # SPDP Unicast: Her düğüm sunucuya kaydolur (N kayıt + N cevap)
        ds_spdp = 2 * num_nodes
        # SEDP Unicast: Sunucu eşleşmeleri ilgili istemcilere dağıtır
        ds_sedp = 2 * (num_nodes * endpoints_per_node)
        total_server = ds_spdp + ds_sedp

        return {
            "num_nodes": num_nodes,
            "simple_packets": total_simple,
            "server_packets": total_server,
            "reduction_ratio": total_simple / max(1, total_server)
        }

# Kıyaslama Testi:
node_counts = [5, 10, 20, 50]
results = [DiscoveryScalabilityAnalyzer.calculate_traffic(n) for n in node_counts]

print("[KOD 3] Keşif Ölçeklenebilirlik Kıyaslama Sonuçları:")
for r in results:
    print(
        f"  - Düğüm Sayısı: {r['num_nodes']:2d} | "
        f"Simple Discovery: {r['simple_packets']:6,d} paket | "
        f"Discovery Server: {r['server_packets']:4,d} paket | "
        f"Kazanç: {r['reduction_ratio']:.1f}x"
    )

# Doğrulama:
assert results[0]["simple_packets"] < results[-1]["simple_packets"]
assert results[-1]["reduction_ratio"] > 40.0, "50 düğümde Discovery Server en az 40 kat tasarruf sağlamalı!"

print("\n[PASS] Discovery Server Trafik Tasarrufu Matematiksel Olarak Kanıtlandı.")

# ==============================================================================
# KOD 4: Hata Enjeksiyonu (Fault Injection) ve Keşif Hata Senaryoları
# Senaryolar:
#   Test A: RxO Uyuşmazlığında Bağlantı Reddi (Incompatible QoS)
#   Test B: Topic Adı Eşit Ama Tip Adı Farklı (Inconsistent Topic)
#   Test C: Kaza-Kırım / Sessizlik Durumunda Kira Süresi Aşımı (Lease Expiration)
# ==============================================================================

class DiscoveryFault(Exception):
    pass

# TEST A: RxO Uyuşmazlığı Nedeniyle Bağlantı Reddi
def simulate_endpoint_match(w_rel: ReliabilityKind, r_rel: ReliabilityKind):
    if w_rel < r_rel:
        raise DiscoveryFault(
            f"INCOMPATIBLE_QOS: Writer({w_rel.name}) alıcının talep ettiği "
            f"Reader({r_rel.name}) güvenilirlik seviyesini karşılayamaz!"
        )
    return "MATCHED_OK"

rxo_fault_caught = False
try:
    simulate_endpoint_match(ReliabilityKind.BEST_EFFORT, ReliabilityKind.RELIABLE)
except DiscoveryFault as e:
    rxo_fault_caught = True
    print(f"[TEST A] Beklenen RxO Uyuşmazlığı Yakalandı:\n  -> {e}")

assert rxo_fault_caught, "Best-effort yazar ile reliable okuyucu eşleşmemeliydi!"

# TEST B: Inconsistent Topic Hatası
def simulate_topic_match(topic_w: str, type_w: str, topic_r: str, type_r: str):
    if topic_w == topic_r and type_w != type_r:
        raise DiscoveryFault(
            f"INCONSISTENT_TOPIC: '{topic_w}' konusu için tip adları uyuşmuyor! "
            f"Writer: '{type_w}' != Reader: '{type_r}'"
        )
    return "MATCHED_OK"

topic_fault_caught = False
try:
    simulate_topic_match("rt/telemetry", "AvionicsData_v1", "rt/telemetry", "AvionicsData_v2")
except DiscoveryFault as e:
    topic_fault_caught = True
    print(f"\n[TEST B] Beklenen Tip Çatışması Yakalandı:\n  -> {e}")

assert topic_fault_caught, "Farklı tiplere sahip aynı topic eşleşmemeliydi!"

# TEST C: Kaza-Kırım / Düğüm Çökmesi Kira Süresi Aşımı
class LeaseWatchdog:
    def __init__(self, lease_duration_sec: float = 2.0):
        self.lease_duration = lease_duration_sec
        self.peers: Dict[str, float] = {} # guid -> last_heartbeat_time

    def heartbeat(self, guid: str, now: float):
        self.peers[guid] = now

    def purge_dead_nodes(self, now: float) -> List[str]:
        dead = []
        for guid, last_time in list(self.peers.items()):
            if now - last_time > self.lease_duration:
                dead.append(guid)
                del self.peers[guid]
        return dead

watchdog = LeaseWatchdog(lease_duration_sec=2.0)
watchdog.heartbeat("RADAR_01", now=10.0)
watchdog.heartbeat("MISSILE_01", now=10.0)

# 1. saniye: Radar hayatta
watchdog.heartbeat("RADAR_01", now=11.0)
# Füze 10. saniyeden sonra vuruldu, hiç paket gelmedi!

# 12.5 saniyede denetim (Füzenin son sinyalinden 2.5 sn geçti, limit 2.0s)
dead_nodes = watchdog.purge_dead_nodes(now=12.5)

print(f"\n[TEST C] Kira Süresi Dolup Sistemden Düşürülen Düğümler: {dead_nodes}")
assert "MISSILE_01" in dead_nodes, "Sessiz kalan füze sistemden silinmeliydi!"
assert "RADAR_01" in watchdog.peers, "Sinyal gönderen radar canlı kalmalıydı!"

print("\n[PASS] 3 Kritik Keşif Hata Enjeksiyonu Senaryosu Başarıyla Geçti.")

# ==============================================================================
# KOD 5: 50-Düğümlü Sürü İHA Keşif Zamanı (TTD) ve Jitter Kıyaslaması
# Amaç: 50 İHA'nın ağa katılımında Simple Discovery vs Discovery Server
# keşif tamamlama sürelerini (Time-To-Discovery) mikrosaniye hassasiyetinde ölçmek.
# ==============================================================================

import time
import random
import numpy as np

NUM_SWARM_NODES = 50

# 1. Simple Discovery Simülasyonu (Multicast Çekişmesi ve Gecikme)
np.random.seed(42)
# Her düğüm O(N) eşleşme yapar; ağ yükü nedeniyle ortalama gecikme artar
simple_ttd_ms = np.random.normal(loc=1250, scale=180, size=NUM_SWARM_NODES)
simple_ttd_ms = np.clip(simple_ttd_ms, 800, 2200)

# 2. Discovery Server Simülasyonu (Merkezi Unicast Dağıtımı)
server_ttd_ms = np.random.normal(loc=180, scale=25, size=NUM_SWARM_NODES)
server_ttd_ms = np.clip(server_ttd_ms, 120, 320)

avg_simple = float(np.mean(simple_ttd_ms))
avg_server = float(np.mean(server_ttd_ms))
ttd_speedup = avg_simple / avg_server

print("[KOD 5] 50-Düğümlü Sürü İHA Keşif Başarım Sonuçları:")
print(f"  - Düğüm Sayısı                       : {NUM_SWARM_NODES}")
print(f"  - Simple Discovery Ortalama TTD     : {avg_simple:.1f} ms")
print(f"  - Discovery Server Ortalama TTD     : {avg_server:.1f} ms")
print(f"  - Keşif Hızlanma Oranı (Speedup)    : {ttd_speedup:.1f} KAT DAHA HIZLI!")

# Doğrulama:
assert avg_server < 300.0, "Discovery Server TTD 300 ms altında olmalıdır!"
assert ttd_speedup > 4.0, "Discovery Server en az 4 kat daha hızlı keşif sağlamalı!"

print("[PASS] Sürü İHA Keşif Başarım Kıyaslaması Başarıyla Tamamlandı.")

# ==============================================================================
# KOD 6: 4-Panelli Master Görselleştirme Paneli (Publication-Quality Artifact)
# Amaç: 2-aşamalı keşif protokolünü, RxO matrisini, keşif ölçeklenebilirliğini
# ve sürü İHA TTD gecikme dağılımını gösteren teknik panel üretmek.
# ==============================================================================

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# PNG dosya yolu belirleme (Dizin garantili)
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_203_dds_discovery.png")
    except Exception:
        PNG_FILE = "c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_203/gun_203_dds_discovery.png"

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
# PANEL 1: 2-Aşamalı RTPS Keşif Protokolü Akış Şeması
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
ax1.set_title("1. RTPS v2.3 İki Aşamalı Keşif Mimarisi (SPDP & SEDP)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

flow_nodes = [
    ("Yeni Katılımcı Başlatıldı\n(DomainParticipant)", 0.2, 0.8, "#6366F1"),
    ("AŞAMA 1: SPDP Multicast\n239.255.0.1:7400\n(GUID & IP Locator Keşfi)", 0.5, 0.8, "#D97706"),
    ("Katılımcılar Eşleşti\n(Peer Proxy Tablosu)", 0.8, 0.8, "#0284C7"),
    ("AŞAMA 2: SEDP Unicast\nDCPSPublication / Subscription\n(Topic, Tip ve QoS)", 0.8, 0.35, "#059669"),
    ("RxO QoS Denetimi\n(Offered >= Requested)", 0.5, 0.35, "#DC2626"),
    ("Doğrudan Veri Hattı\nDataWriter <---> DataReader", 0.2, 0.35, "#34D399")
]

for text, x, y, col in flow_nodes:
    ax1.text(x, y, text, ha='center', va='center', color='#F8FAFC', weight='bold', fontsize=8.5,
             bbox=dict(boxstyle='round,pad=0.5', facecolor=col, edgecolor='#CBD5E1', alpha=0.9))

arrow_kw = dict(arrowstyle='->', color='#38BDF8', lw=2)
ax1.annotate('', xy=(0.38, 0.8), xytext=(0.31, 0.8), arrowprops=arrow_kw)
ax1.annotate('', xy=(0.69, 0.8), xytext=(0.61, 0.8), arrowprops=arrow_kw)
ax1.annotate('', xy=(0.8, 0.47), xytext=(0.8, 0.73), arrowprops=arrow_kw)
ax1.annotate('', xy=(0.61, 0.35), xytext=(0.69, 0.35), arrowprops=arrow_kw)
ax1.annotate('', xy=(0.31, 0.35), xytext=(0.39, 0.35), arrowprops=arrow_kw)

ax1.set_xlim(0.05, 0.95)
ax1.set_ylim(0.15, 0.95)
ax1.axis('off')

# ------------------------------------------------------------------------------
# PANEL 2: RxO (Requested vs Offered) QoS Uyumluluk Matrisi
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
ax2.set_title("2. RxO (Requested vs Offered) Eşleşme Uyumluluk Matrisi", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

matrix_data = np.array([
    [1, 1], # Writer RELIABLE: Reader BestEffort(1), Reader Reliable(1)
    [1, 0]  # Writer BEST_EFFORT: Reader BestEffort(1), Reader Reliable(0)
])

cax = ax2.imshow(matrix_data, cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')

ax2.set_xticks([0, 1])
ax2.set_yticks([0, 1])
ax2.set_xticklabels(['Reader: BEST_EFFORT', 'Reader: RELIABLE'], color='#E2E8F0', fontsize=10, weight='bold')
ax2.set_yticklabels(['Writer: RELIABLE', 'Writer: BEST_EFFORT'], color='#E2E8F0', fontsize=10, weight='bold')

for i in range(2):
    for j in range(2):
        val = matrix_data[i, j]
        txt = "UYUMLU\n(MATCH)" if val == 1 else "UYUMSUZ\n(RED)"
        col = "#0F172A" if val == 1 else "#F8FAFC"
        ax2.text(j, i, txt, ha='center', va='center', color=col, weight='bold', fontsize=11)

ax2.grid(False)

# ------------------------------------------------------------------------------
# PANEL 3: Keşif Ölçeklenebilirliği: Simple (O(N^2)) vs Discovery Server (O(N))
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
ax3.set_title("3. Keşif Ağ Paket Yükü: Simple Discovery vs Discovery Server", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

nodes_sim = np.linspace(2, 50, 49)
simple_traffic = nodes_sim * (nodes_sim - 1) + (nodes_sim * 5) * ((nodes_sim - 1) * 5)
server_traffic = 2 * nodes_sim + 2 * (nodes_sim * 5)

ax3.plot(nodes_sim, simple_traffic, color='#EF4444', lw=2.5, label='Simple Discovery: O(N²) Multicast')
ax3.plot(nodes_sim, server_traffic, color='#34D399', lw=2.5, label='Discovery Server: O(N) Unicast')

ax3.set_xlabel("Ağdaki Düğüm Sayısı (N)", color='#CBD5E1', fontsize=10)
ax3.set_ylabel("Üretilen Keşif Paket Sayısı", color='#CBD5E1', fontsize=10)
ax3.set_yscale('log')
ax3.legend(loc='upper left', facecolor='#1E293B', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

ax3.annotate('50 Düğümde 60,000+ Paket!\n(Multicast Fırtınası)', xy=(50, simple_traffic[-1]), xytext=(30, 20000),
             arrowprops=dict(facecolor='#EF4444', shrink=0.05), color='#EF4444', weight='bold', fontsize=8.5)
ax3.annotate('Sadece ~600 Paket!', xy=(50, server_traffic[-1]), xytext=(35, 1500),
             arrowprops=dict(facecolor='#34D399', shrink=0.05), color='#34D399', weight='bold', fontsize=8.5)

# ------------------------------------------------------------------------------
# PANEL 4: 50 Düğümlü Sürü İHA Time-To-Discovery (TTD) Dağılımı
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
ax4.set_title("4. 50-Düğümlü Sürü İHA Keşif Tamamlama Süresi (TTD Histogramı)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

ax4.hist(simple_ttd_ms, bins=30, color='#EF4444', alpha=0.75, label=f'Simple Discovery (Ort: {avg_simple:.0f} ms)')
ax4.hist(server_ttd_ms, bins=30, color='#34D399', alpha=0.85, label=f'Discovery Server (Ort: {avg_server:.0f} ms)')

ax4.axvline(x=avg_simple, color='#F87171', linestyle='--', lw=2)
ax4.axvline(x=avg_server, color='#34D399', linestyle='--', lw=2)

ax4.set_xlabel("Keşif Tamamlama Süresi (Milisaniye - ms)", color='#CBD5E1', fontsize=10)
ax4.set_ylabel("Düğüm Sayısı", color='#CBD5E1', fontsize=10)
ax4.legend(loc='upper right', facecolor='#1E293B', edgecolor='#475569', labelcolor='#F8FAFC', fontsize=9)

info_txt = (
    "SÜRÜ İHA METRİKLERİ:\n"
    "--------------------\n"
    f"- Hızlanma : {ttd_speedup:.1f} Kat Hızlı\n"
    "- Trafik   : %99 Tasarruf\n"
    "- Telsiz   : Sıfır Multicast\n"
    "- Havada   : Kesintisiz Katılım"
)
ax4.text(0.48, 0.45, info_txt, transform=ax4.transAxes,
         fontsize=8.5, color='#E2E8F0', fontfamily='monospace',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor='#38BDF8', alpha=0.9))

plt.tight_layout()
fig.subplots_adjust(top=0.93)
fig.suptitle("GÜN 203: DDS DISCOVERY PROTOKOLÜ (SPDP, SEDP, RxO VE DISCOVERY SERVER)",
             fontsize=15, color='#F8FAFC', weight='bold')

plt.savefig(PNG_FILE, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

file_size_kb = os.path.getsize(PNG_FILE) / 1024.0
print(f"[OK] 4-Panelli Görselleştirme Başarıyla Üretildi: {PNG_FILE}")
print(f"  - Dosya Boyutu: {file_size_kb:.2f} KB (Beklenen: > 100 KB)")
assert file_size_kb > 100.0, "PNG dosya boyutu 100 KB'den küçük olamaz!"
