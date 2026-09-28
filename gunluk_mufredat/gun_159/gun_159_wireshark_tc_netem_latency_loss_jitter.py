# -*- coding: utf-8 -*-
"""
gun_159_wireshark_tc_netem_latency_loss_jitter
Otomatik Oluşturulan Çalıştırılabilir Python Betiği
"""

# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 1 — Linux tc/netem Mantığını Birebir Taklit Eden Ağ Kanal Motoru
"""

import random
import time
from typing import List, Tuple, Optional, Dict, Any

class NetemPacket:
    """Simüle Edilen Ağ Paketi"""
    def __init__(self, seq: int, send_time: float, payload: bytes):
        self.seq = seq
        self.send_time = send_time
        self.delivery_time = send_time
        self.payload = payload
        self.is_duplicate = False

class NetemChannel:
    """
    Linux tc/netem Çekirdek Kuyruğunun Python Uygulaması.
    Gecikme (Gauss), Jitter, Kayıp, Çoğaltma ve Sıra Bozulmasını modeller.
    """
    def __init__(self, mean_delay_ms: float = 50.0, jitter_ms: float = 10.0,
                 loss_rate: float = 0.10, duplicate_rate: float = 0.02,
                 reorder_rate: float = 0.05):
        self.mean_delay = mean_delay_ms / 1000.0
        self.jitter = jitter_ms / 1000.0
        self.loss_rate = loss_rate
        self.duplicate_rate = duplicate_rate
        self.reorder_rate = reorder_rate

        self.stats = {
            "sent": 0,
            "delivered": 0,
            "dropped": 0,
            "duplicated": 0,
            "reordered": 0
        }

    def transmit(self, packets: List[NetemPacket]) -> List[NetemPacket]:
        in_flight: List[NetemPacket] = []

        for pkt in packets:
            self.stats["sent"] += 1

            # 1. Paket Kaybı (Loss) Enjeksiyonu
            if random.random() < self.loss_rate:
                self.stats["dropped"] += 1
                continue

            # 2. Gecikme ve Jitter (Gauss / Normal Dağılım)
            delay = max(0.001, random.gauss(self.mean_delay, self.jitter))
            
            # 3. Sıra Bozulması (Reordering) Enjeksiyonu
            if random.random() < self.reorder_rate:
                # Sırasız pakete daha az gecikme vererek öne fırlat
                delay *= 0.3
                self.stats["reordered"] += 1

            pkt.delivery_time = pkt.send_time + delay
            in_flight.append(pkt)

            # 4. Paket Çoğaltma (Duplication) Enjeksiyonu
            if random.random() < self.duplicate_rate:
                dup_pkt = NetemPacket(pkt.seq, pkt.send_time, pkt.payload)
                dup_pkt.delivery_time = pkt.delivery_time + 0.005 # 5 ms sonra ikinci kopya
                dup_pkt.is_duplicate = True
                in_flight.append(dup_pkt)
                self.stats["duplicated"] += 1

        # Alıcıya varış zamanına göre fiziksel ortamda sırala
        in_flight.sort(key=lambda p: p.delivery_time)
        self.stats["delivered"] = len(in_flight)
        return in_flight

print("[*] Linux tc/netem Kanal Simülatörü Motoru Tanımlandı.")
print("[HÜCRE 6] Netem simülatörü hazır.")

# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 2 — Wireshark Uyumlu Libpcap (.pcap) İkili Dosya Yazıcı Motoru
"""

import os
import struct

try:
    target_dir = os.path.dirname(os.path.abspath(__file__))
except Exception:
    target_dir = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_159"

class PcapWriter:
    """
    RFC Standartlarında Libpcap (.pcap) İkili Dosya Üreticisi.
    Harici kütüphane gerektirmeden Wireshark'ın açabileceği dosyalar üretir.
    """
    GLOBAL_HEADER_MAGIC = 0xA1B2C3D4  # Standard PCAP Magic
    VERSION_MAJOR = 2
    VERSION_MINOR = 4
    SNAPLEN = 65535
    NETWORK_RAW_IP = 101  # Link-Layer Header Type: Raw IPv4

    def __init__(self, filename: str):
        self.filename = filename
        self.file = open(filename, "wb")
        self._write_global_header()

    def _write_global_header(self):
        # 24 Bayt Libpcap Genel Başlığı
        hdr = struct.pack(
            "=I H H i I I I",
            self.GLOBAL_HEADER_MAGIC,
            self.VERSION_MAJOR,
            self.VERSION_MINOR,
            0,          # GMT to local correction
            0,          # Accuracy of timestamps
            self.SNAPLEN,
            self.NETWORK_RAW_IP
        )
        self.file.write(hdr)

    def write_packet(self, timestamp_sec: float, payload: bytes):
        sec = int(timestamp_sec)
        usec = int((timestamp_sec - sec) * 1_000_000)
        pkt_len = len(payload)

        # 16 Bayt Paket Başlığı
        pkt_hdr = struct.pack("=I I I I", sec, usec, pkt_len, pkt_len)
        self.file.write(pkt_hdr)
        self.file.write(payload)

    def close(self):
        if self.file and not self.file.closed:
            self.file.close()

# Test: Örnek PCAP Dosyası Oluşturma
sample_pcap_path = os.path.join(target_dir, "tactical_sample.pcap")
writer = PcapWriter(sample_pcap_path)

base_time = 1716380000.0
for i in range(10):
    dummy_payload = f"TACTICAL_TELEMETRY_PKT_SEQ_{i}".encode('utf-8')
    writer.write_packet(base_time + (i * 0.05), dummy_payload)
writer.close()

pcap_size = os.path.getsize(sample_pcap_path)
print("[*] Wireshark PCAP İkili Dosyası Başarıyla Oluşturuldu:")
print(f"  [+] Dosya Yolu : {sample_pcap_path}")
print(f"  [+] Dosya Boyu : {pcap_size} Bayt (24B Global Header + 10x(16B Hdr + Payload))")

assert os.path.exists(sample_pcap_path)
assert pcap_size > 24 + (10 * 16)
print("[HÜCRE 8] PCAP formatlayıcı motoru başarıyla test edildi.")

# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 3 — Sabotaj ve Başarım İspatı: Standart vs Dayanıklı Telemetri Alıcısı
"""

class StandardTelemetryReceiver:
    """Saf UDP Gibi Çalışan Savunmasız Alıcı (Sıra / Duplication Koruması Yok)"""
    def __init__(self):
        self.received = []

    def receive(self, pkt: NetemPacket):
        self.received.append(pkt.seq)

class ResilientTelemetryReceiver:
    """
    Savunma Standartlarında Dayanıklı Alıcı (Resilient Receiver):
    - Duplicate Paketleri Düşürür (Anti-Replay / Dedup)
    - Sıra Bozulmasını Tespit Eder ve Yeniden Sıralar
    """
    def __init__(self):
        self.seen_seqs = set()
        self.delivered = []
        self.expected_seq = 0
        self.buffer = {}

    def receive(self, pkt: NetemPacket):
        # 1. Çoğaltılmış Paket (Duplication) Tespiti ve İmhayı Sağla
        if pkt.seq in self.seen_seqs:
            return  # Kopyayı sessizce düşür!
        self.seen_seqs.add(pkt.seq)

        # 2. Tampona Ekle
        self.buffer[pkt.seq] = pkt.payload

        # 3. Sırayla Teslim Et
        while self.expected_seq in self.buffer:
            self.delivered.append(self.expected_seq)
            del self.buffer[self.expected_seq]
            self.expected_seq += 1

# Deney Kurulumu: 50 Paket Gönder, Ağda Agresif Elektronik Harp (EH) Uygula
random.seed(159)
netem = NetemChannel(
    mean_delay_ms=80.0,
    jitter_ms=25.0,
    loss_rate=0.15,      # %15 Paket Kaybı
    duplicate_rate=0.10, # %10 Çoğaltma
    reorder_rate=0.15    # %15 Sıra Bozulması
)

packets = [NetemPacket(seq=i, send_time=i * 0.02, payload=f"DATA_{i}".encode()) for i in range(50)]
delivered_packets = netem.transmit(packets)

std_rx = StandardTelemetryReceiver()
res_rx = ResilientTelemetryReceiver()

for p in delivered_packets:
    std_rx.receive(p)
    res_rx.receive(p)

print()
print("[*] Elektronik Harp (EH) Simülasyon Sonuçları (50 Paket Gönderildi):")
print(f"  [+] Ağda Düşürülen Paket Sayısı : {netem.stats['dropped']} (%{netem.stats['dropped']/50*100:.1f})")
print(f"  [+] Çoğaltılan Paket Sayısı     : {netem.stats['duplicated']}")
print(f"  [+] Sırası Değişen Paket Sayısı : {netem.stats['reordered']}")
print()
print(f"  [-] Standart Alıcı Teslimat Sayısı : {len(std_rx.received)} (Kopya paketleri ayırt edemedi!)")
print(f"  [+] Dayanıklı Alıcı Teslimat Sayısı: {len(res_rx.delivered)} (Kopyalar %100 elendi, sıralı teslim edildi)")

# Kural İspatı: Standart alıcıda kopya paketler bulunurken, dayanıklı alıcıda asla bulunmaz
assert len(std_rx.received) > len(set(std_rx.received)), "Standart alıcı kopyaları filtreleyememelidir!"
assert len(res_rx.delivered) == len(set(res_rx.delivered)), "Dayanıklı alıcıda kopya paket olamaz!"
print("[HÜCRE 10] Sabotaj ve dayanıklılık testi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 4 — Wireshark Metrik Analizörü (RTT, RFC 3550 Jitter ve Gecikme Dağılımı)
"""

class PcapAnalyzer:
    """Yakalanan Paketlerden Wireshark Tipi İstatistik Çıkaran Motor"""
    @staticmethod
    def analyze_stream(delivered: List[NetemPacket]) -> Dict[str, Any]:
        if not delivered:
            return {}

        delays_ms = [(p.delivery_time - p.send_time) * 1000.0 for p in delivered]
        mean_delay = sum(delays_ms) / len(delays_ms)

        # RFC 3550 Jitter Hesabı
        jitter = 0.0
        jitter_history = []
        for i in range(1, len(delivered)):
            prev = delivered[i-1]
            curr = delivered[i]
            d = abs((curr.delivery_time - prev.delivery_time) - (curr.send_time - prev.send_time)) * 1000.0
            jitter = jitter + (d - jitter) / 16.0
            jitter_history.append(jitter)

        return {
            "packet_count": len(delivered),
            "delays_ms": delays_ms,
            "mean_delay_ms": mean_delay,
            "min_delay_ms": min(delays_ms),
            "max_delay_ms": max(delays_ms),
            "final_jitter_ms": jitter,
            "jitter_history": jitter_history
        }

metrics = PcapAnalyzer.analyze_stream(delivered_packets)

print()
print("[*] Wireshark Tipi Ağ Sağlık ve Metrik Raporu:")
print(f"  [+] Analiz Edilen Paket  : {metrics['packet_count']}")
print(f"  [+] Ortalama Gecikme     : {metrics['mean_delay_ms']:.2f} ms")
print(f"  [+] Min / Max Gecikme    : {metrics['min_delay_ms']:.2f} ms / {metrics['max_delay_ms']:.2f} ms")
print(f"  [+] Nihai RFC 3550 Jitter: {metrics['final_jitter_ms']:.2f} ms")

assert metrics['mean_delay_ms'] > 40.0, "Ortalama gecikme emüle edilen aralıkta olmalıdır!"
assert metrics['final_jitter_ms'] > 0.0, "Jitter sıfırdan büyük olmalıdır!"
print("[HÜCRE 12] Wireshark metrik analizörü başarıyla çalıştırıldı.")

# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 5 — Bayraktar TB2 Taktik Görev Simülasyonu ve Telsiz Bozulma Testi
"""

class TacticalTelemetryUav:
    """İHA Tarafında Telemetri Üreten Modül"""
    def __init__(self):
        self.seq = 0

    def generate_packet(self, timestamp: float) -> NetemPacket:
        # GPS, İrtifa, Hız ve Batarya Paketi
        payload = f"TB2_TLM:SEQ={self.seq},LAT=39.925,LON=32.866,ALT=5200M,SPD=120KTS,BAT=%98".encode()
        pkt = NetemPacket(self.seq, timestamp, payload)
        self.seq += 1
        return pkt

# 100 Paketlik Taktik Uçuş Görevi
uav = TacticalTelemetryUav()
raw_telemetry = [uav.generate_packet(timestamp=i * 0.05) for i in range(100)]

# Görev Sırasında Düşman Jammer'ı Devreye Giriyor!
tactical_channel = NetemChannel(
    mean_delay_ms=120.0, # 120 ms uydu/telsiz gecikmesi
    jitter_ms=30.0,
    loss_rate=0.20,      # %20 Yüksek Karıştırma Kaybı
    duplicate_rate=0.04,
    reorder_rate=0.08
)

transmitted_tlm = tactical_channel.transmit(raw_telemetry)
gcs_receiver = ResilientTelemetryReceiver()

for p in transmitted_tlm:
    gcs_receiver.receive(p)

print()
print("[*] Bayraktar TB2 Görev Sonu Telemetri Raporu (100 Paket Üretildi):")
print(f"  [+] Jammer Tarafından Düşürülen: {tactical_channel.stats['dropped']} Paket")
print(f"  [+] Yer İstasyonuna Ulaşan      : {len(transmitted_tlm)} Paket")
print(f"  [+] Kusursuz İşlenen Telemetri : {len(gcs_receiver.delivered)} Adet")

assert len(gcs_receiver.delivered) == len(set(gcs_receiver.delivered))
assert tactical_channel.stats['dropped'] > 0
print("[HÜCRE 14] Taktik telemetri dayanıklılık senaryosu başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 159: Kod Bloğu 6 — 4 Panelli 300 DPI Görselleştirme Panosu ve Katı Doğrulama Testleri
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_159_wireshark_tc_netem_latency_loss_jitter.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_159\gun_159_wireshark_tc_netem_latency_loss_jitter.png"

# Matplotlib Karanlık Tema Ayarları
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.0

fig = plt.figure(figsize=(18, 12), dpi=300, facecolor='#0F172A')
fig.suptitle("GÜN 159: Linux tc/netem Ağ Emülasyonu ve Wireshark Analiz Panosu",
             fontsize=15, fontweight='bold', color='#38BDF8', y=0.98)

# -----------------------------------------------------------------------------
# PANEL 1: Linux tc/netem Çekirdek Kuyruk Mimarisi (Qdisc Pipeline)
# -----------------------------------------------------------------------------
ax1 = fig.add_subplot(2, 2, 1)
ax1.set_facecolor('#1E293B')
ax1.set_title("Panel 1: Linux Çekirdeği Trafik Kontrolü (tc/netem Qdisc) Mimarisi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)
ax1.axis('off')

# Blok Şeması
blocks = [
    ("Uygulama Katmanı (Socket)", "sendto() / write() Veri Üretimi", 0.05, 0.75, 0.38, "#0284C7"),
    ("IP Yığını (Routing & Output)", "sk_buff Çekirdek Bellek Tahsisi", 0.55, 0.75, 0.40, "#0284C7"),
    ("Linux Qdisc: netem (Kuyruk Disiplini)", "Gecikme (Gauss), Jitter, Loss (%15), Duplication, Reordering", 0.05, 0.42, 0.90, "#D97706"),
    ("Ağ Kartı Sürücüsü (NIC Driver)", "Ring Buffer (DMA Transfer)", 0.05, 0.12, 0.42, "#10B981"),
    ("Fiziksel Telsiz / RF Arayüzü", "Harp Sahası Anteni & Taktik Hat", 0.53, 0.12, 0.42, "#10B981")
]

for title, sub, bx, by, bw, col in blocks:
    rect = patches.FancyBboxPatch((bx, by), bw, 0.18, boxstyle="round,pad=0.02", facecolor=col, alpha=0.25, edgecolor=col, lw=2)
    ax1.add_patch(rect)
    ax1.text(bx + 0.02, by + 0.11, title, color='#F8FAFC', fontweight='bold', fontsize=9.5)
    ax1.text(bx + 0.02, by + 0.04, sub, color='#CBD5E1', fontsize=8)

# Oklar
ax1.annotate("", xy=(0.54, 0.84), xytext=(0.44, 0.84), arrowprops=dict(arrowstyle="->", color='#38BDF8', lw=2))
ax1.annotate("", xy=(0.5, 0.61), xytext=(0.5, 0.74), arrowprops=dict(arrowstyle="->", color='#F59E0B', lw=2.5))
ax1.annotate("", xy=(0.26, 0.31), xytext=(0.26, 0.41), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))
ax1.annotate("", xy=(0.74, 0.31), xytext=(0.74, 0.41), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2))

ax1.set_xlim(0.0, 1.0)
ax1.set_ylim(0.0, 1.0)

# -----------------------------------------------------------------------------
# PANEL 2: Gecikme Dağılımı ve Jitter Gauss Eğrisi
# -----------------------------------------------------------------------------
ax2 = fig.add_subplot(2, 2, 2)
ax2.set_facecolor('#1E293B')
ax2.set_title("Panel 2: Emüle Edilen Paket Gecikme Dağılımı (Gauss / Normal Eğri)", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

delays = metrics['delays_ms']
count, bins, ignored = ax2.hist(delays, bins=15, density=True, color='#38BDF8', alpha=0.6, edgecolor='#1E293B')

# Teorik Gauss Eğrisi Çizimi
mu = metrics['mean_delay_ms']
sigma = np.std(delays)
x_vals = np.linspace(min(delays) - 10, max(delays) + 10, 100)
p_vals = 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(- (x_vals - mu)**2 / (2 * sigma**2))
ax2.plot(x_vals, p_vals, linewidth=2.5, color='#F43F5E', label=f'Gauss Fit (μ={mu:.1f}ms, σ={sigma:.1f}ms)')

ax2.set_xlabel("Paket Gecikmesi (Milisaniye)", fontsize=9, color='#94A3B8')
ax2.set_ylabel("Olasılık Yoğunluğu", fontsize=9, color='#94A3B8')
ax2.grid(True, linestyle=':', alpha=0.3, color='#64748B')
ax2.legend(facecolor='#1E293B', edgecolor='#334155')
ax2.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 3: Taktik Telsiz Paket Teslim Durum Dağılımı
# -----------------------------------------------------------------------------
ax3 = fig.add_subplot(2, 2, 3)
ax3.set_facecolor('#1E293B')
ax3.set_title("Panel 3: Elektronik Harp Altında Paket İletim Durumları", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

categories = ["Başarılı Teslim", "Jammer Kaybı\n(Dropped)", "Çoğaltılan\n(Duplicated)", "Sırası Değişen\n(Reordered)"]
values = [
    netem.stats['delivered'] - netem.stats['duplicated'],
    netem.stats['dropped'],
    netem.stats['duplicated'],
    netem.stats['reordered']
]
colors_cat = ['#10B981', '#EF4444', '#F59E0B', '#8B5CF6']

bars3 = ax3.bar(categories, values, color=colors_cat, width=0.45, edgecolor='#334155', lw=1.5)
for bar, val in zip(bars3, values):
    yval = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 0.8, f"{val} Pkt",
             ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=9)

ax3.set_ylim(0, max(values) + 8)
ax3.set_ylabel("Paket Sayısı", fontsize=9, color='#94A3B8')
ax3.grid(axis='y', linestyle=':', alpha=0.3, color='#64748B')
ax3.tick_params(colors='#94A3B8')

# -----------------------------------------------------------------------------
# PANEL 4: RFC 3550 Jitter Zaman Serisi
# -----------------------------------------------------------------------------
ax4 = fig.add_subplot(2, 2, 4)
ax4.set_facecolor('#1E293B')
ax4.set_title("Panel 4: RFC 3550 Inter-Arrival Jitter Zaman Serisi Eğrisi", fontsize=11, fontweight='bold', color='#F8FAFC', pad=10)

jitter_hist = metrics['jitter_history']
pkt_indices = list(range(1, len(jitter_hist) + 1))

ax4.plot(pkt_indices, jitter_hist, color='#F59E0B', lw=2.0, marker='o', markersize=3, label='RFC 3550 Jitter (EMA)')
ax4.axhline(y=metrics['final_jitter_ms'], color='#10B981', linestyle='--', label=f"Nihai Jitter: {metrics['final_jitter_ms']:.2f} ms")

ax4.set_xlabel("İletilen Paket Sırası (Index)", fontsize=9, color='#94A3B8')
ax4.set_ylabel("Jitter Değeri (Milisaniye)", fontsize=9, color='#94A3B8')
ax4.grid(True, linestyle=':', alpha=0.3, color='#64748B')
ax4.legend(facecolor='#1E293B', edgecolor='#334155')
ax4.tick_params(colors='#94A3B8')

plt.tight_layout()
fig.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', edgecolor='none')
plt.close(fig)

print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {PNG_FILE}")

# -----------------------------------------------------------------------------
# KATI DOĞRULAMA TESTLERİ (ASSERTIONS)
# -----------------------------------------------------------------------------
print()
print("[*] GÜN 159 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

assert os.path.exists(PNG_FILE), "PNG görsel artefaktı bulunamadı!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100_000, f"PNG boyutu 100 KB üzerinde olmalı, bulunan: {png_size} bayt"

assert metrics['packet_count'] > 0
assert metrics['mean_delay_ms'] > 0
assert netem.stats['dropped'] > 0
assert len(gcs_receiver.delivered) > 0

print()
print("[PASS] Gün 159: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")

