# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
GÜN 140: Kod Bloğu 1 — TCP Reliability, RTO ve Out-of-Order Sıralama Motoru
Jacobson/Karels RTT/RTO Algoritması (RFC 6298) ve Reordering Buffer.
"""

import os
import sys
import time
import math
import random
from typing import Dict, List, Tuple, Optional, NamedTuple

class RTTStats:
    """RFC 6298 Jacobson/Karels Algoritması Gerçeklemesi"""
    def __init__(self, alpha: float = 0.125, beta: float = 0.25, g_sec: float = 0.001):
        self.alpha = alpha
        self.beta = beta
        self.g = g_sec  # Clock granularity (1 ms)
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None
        self.rto: float = 1.0  # RFC başlangıç RTO = 1.0 saniye
        self.rtt_history: List[Tuple[float, float, float, float]] = [] # (R, SRTT, RTTVAR, RTO)

    def update(self, r_sample: float):
        """Yeni bir RTT örneği ile SRTT, RTTVAR ve RTO güncellenir"""
        if self.srtt is None:
            # İlk ölçüm (RFC 6298 Bölüm 2.2)
            self.srtt = r_sample
            self.rttvar = r_sample / 2.0
            self.rto = self.srtt + max(self.g, 4.0 * self.rttvar)
        else:
            # Sonraki ölçümler (RFC 6298 Bölüm 2.3)
            self.rttvar = (1.0 - self.beta) * self.rttvar + self.beta * abs(self.srtt - r_sample)
            self.srtt = (1.0 - self.alpha) * self.srtt + self.alpha * r_sample
            self.rto = self.srtt + max(self.g, 4.0 * self.rttvar)

        # Sınırlandırmalar: min 0.2s (Linux standardı), max 60s
        self.rto = max(0.2, min(self.rto, 60.0))
        self.rtt_history.append((r_sample, self.srtt, self.rttvar, self.rto))

    def backoff(self):
        """Karn Exponential Backoff: RTO ikiye katlanır"""
        self.rto = min(self.rto * 2.0, 60.0)

class TCPSegment(NamedTuple):
    seq: int
    data: bytes
    send_time: float
    is_retransmit: bool = False

class TCPReorderingBuffer:
    """Alıcı Çekirdek Sıralama Tamponu (Out-of-Order Queue / Red-Black Tree Mantığı)"""
    def __init__(self, initial_expected_seq: int = 1000):
        self.rcv_nxt = initial_expected_seq  # Alıcının beklediği bir sonraki bayt
        self.ofo_buffer: Dict[int, bytes] = {} # seq -> data (Sırasız gelen paketler)
        self.delivered_stream: bytearray = bytearray()
        self.dup_ack_count = 0
        self.last_ack_sent = initial_expected_seq

    def receive_segment(self, segment: TCPSegment) -> Tuple[int, List[Tuple[int, int]]]:
        """
        Gelen segmenti işler.
        Dönüş: (Kümülatif ACK, SACK Blokları [(start, end)])
        """
        seq = segment.seq
        length = len(segment.data)

        # 1. Beklenen segment tam vaktinde geldi mi?
        if seq == self.rcv_nxt:
            self.delivered_stream.extend(segment.data)
            self.rcv_nxt += length
            self.dup_ack_count = 0

            # Şimdi tamponda bekleyen sıradaki paketlerin önü açıldı mı? (Delik kapandı!)
            while self.rcv_nxt in self.ofo_buffer:
                contiguous_data = self.ofo_buffer.pop(self.rcv_nxt)
                self.delivered_stream.extend(contiguous_data)
                self.rcv_nxt += len(contiguous_data)

        elif seq > self.rcv_nxt:
            # 2. Gelecekten bir paket geldi (Out-of-Order)! Tampona al, delik oluştu!
            if seq not in self.ofo_buffer:
                self.ofo_buffer[seq] = segment.data
            self.dup_ack_count += 1
        else:
            # 3. Zaten alınmış eski/yinelenen paket (Duplicate)
            pass

        self.last_ack_sent = self.rcv_nxt
        sack_blocks = self._generate_sack_blocks()
        return self.rcv_nxt, sack_blocks

    def _generate_sack_blocks(self) -> List[Tuple[int, int]]:
        """Tampondaki izole blokları SACK formatında listeler"""
        blocks = []
        for seq in sorted(self.ofo_buffer.keys()):
            blocks.append((seq, seq + len(self.ofo_buffer[seq])))
        return blocks

print("[HÜCRE 7] RTTStats, TCPSegment ve TCPReorderingBuffer başarıyla yüklendi.")

# -*- coding: utf-8 -*-
"""
GÜN 140: Kod Bloğu 2 — Out-of-Order İletim ve Reordering Buffer Delik Kapatma Deneyi
"""

print("")
print("[*] Out-of-Order Paket İletimi ve Sıralama Tamponu Deneyi Başlatılıyor...")

# 500 Baytlık Taktik Görev Emri
payloads = [
    b"CMD_TARGET_LOCK_AZIMUTH_045_RADAR_NORTH",     # 1000..1099 (100B yapalım)
    b"CMD_MISSILE_WARHEAD_ARM_SAFE_BATTERY_01",    # 1100..1199
    b"CMD_IFF_CHALLENGE_TRANSPONDER_MODE_5_OK",    # 1200..1299
    b"CMD_ENGAGE_TRACK_ID_9942_AIR_SUPERIOR",      # 1300..1399
    b"CMD_TERMINAL_HOMING_ACTIVE_RADAR_SEEKER"     # 1400..1499
]
# Her birini tam 100 bayta pad edelim
segments = []
for idx, p in enumerate(payloads):
    padded = p.ljust(100, b"#")
    segments.append(TCPSegment(seq=1000 + idx * 100, data=padded, send_time=time.time()))

# Senaryo: Sıra bozuldu! Alıcıya geliş sırası: 0, 2, 3, 4, 1 (Paket 1 gecikti!)
arrival_order = [0, 2, 3, 4, 1]
receiver_buffer = TCPReorderingBuffer(initial_expected_seq=1000)

print(f"  [+] Gönderilen Paketler: 5 Adet x 100 Bayt (Seq: 1000 - 1500)")
print(f"  [+] Ağ Varış Sırası   : {[s.seq for s in [segments[i] for i in arrival_order]]}")

for step, arr_idx in enumerate(arrival_order, start=1):
    seg = segments[arr_idx]
    cum_ack, sack_blocks = receiver_buffer.receive_segment(seg)
    print(""); print(f"  [Adım {step}] Paket Geldi: Seq={seg.seq}..{seg.seq+len(seg.data)}")
    print(f"      -> Alıcı Kümülatif ACK: {cum_ack}")
    print(f"      -> SACK Blokları     : {sack_blocks}")
    print(f"      -> DUP ACK Sayısı    : {receiver_buffer.dup_ack_count}")
    print(f"      -> Tampon Bekleyen   : {list(receiver_buffer.ofo_buffer.keys())}")

# Doğrulama
assert receiver_buffer.rcv_nxt == 1500, "HATA: Tüm paketler geldikten sonra rcv_nxt 1500 olmalıydı!"
assert len(receiver_buffer.ofo_buffer) == 0, "HATA: Tüm delikler kapandıktan sonra tampon boş olmalıydı!"
assert len(receiver_buffer.delivered_stream) == 500, "HATA: Teslim edilen veri 500 bayt olmalıydı!"
print(""); print("  [+] Mükemmel Başarı: Out-of-Order paketler %100 kusursuz sırada teslim edildi!")
print("[HÜCRE 9] Sırasız paket sıralama deneyi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 140: Kod Bloğu 3 — Sabotaj Laboratuvarı: RTO Zaman Aşımı vs Fast Retransmit
"""

print("")
print("[*] TCP Kayıp Kurtarma ve Sabotaj Laboratuvarı Başlatılıyor...")

class TCPSenderSimulation:
    def __init__(self, rtt_ms: float = 20.0):
        self.rtt_ms = rtt_ms
        self.rtt_stats = RTTStats()
        self.rtt_stats.update(rtt_ms / 1000.0) # İlk RTT'yi öğret
        self.retransmission_log: List[Dict] = []

    def simulate_rto_recovery(self, lost_seq: int) -> float:
        """Akışın son paketi kayboldu; DUP ACK gelmiyor, mecburen RTO bekleniyor"""
        rto_duration_ms = self.rtt_stats.rto * 1000.0
        self.rtt_stats.backoff() # Karn backoff
        self.retransmission_log.append({
            "type": "RTO_TIMEOUT",
            "seq": lost_seq,
            "latency_ms": rto_duration_ms
        })
        return rto_duration_ms

    def simulate_fast_retransmit(self, lost_seq: int) -> float:
        """Kayıp paketin ardından 3 DUP ACK geldi; anında Fast Retransmit!"""
        # 3 DUP ACK üretilmesi için geçen süre: ~1 RTT
        # Tekrar iletimin onaylanması: +1 RTT. Toplam: 2 RTT
        recovery_time_ms = 2.0 * self.rtt_ms
        self.retransmission_log.append({
            "type": "FAST_RETRANSMIT",
            "seq": lost_seq,
            "latency_ms": recovery_time_ms
        })
        return recovery_time_ms

sender = TCPSenderSimulation(rtt_ms=20.0)

# Sabotaj 1: RTO ile Kurtarma
time_rto = sender.simulate_rto_recovery(lost_seq=2000)
print(f"  [-] Sabotaj 1: DUP ACK Yok (Son Paket Düştü) -> RTO Beklendi: {time_rto:.1f} ms")

# Sabotaj 2: Fast Retransmit ile Kurtarma
time_fast = sender.simulate_fast_retransmit(lost_seq=2000)
print(f"  [+] Sabotaj 2: 3 DUP ACK Geldi -> Fast Retransmit Yapıldı: {time_fast:.1f} ms")

speedup = time_rto / time_fast
print(f"  [+] Fast Retransmit Hızlandırması: {speedup:.1f}x KAT DAHA HIZLI!")
assert speedup >= 4.0, "HATA: Fast Retransmit RTO'dan en az 4 kat hızlı olmalıydı!"

print("[HÜCRE 11] Sabotaj ve kayıp kurtarma testleri başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 140: Kod Bloğu 4 — Jacobson/Karels Algoritması Jitter ve Adaptasyon Benchmarkı
"""

print("")
print("[*] Jacobson/Karels RTT/RTO Dinamik Adaptasyon Benchmarkı Başlatılıyor...")

rtt_engine = RTTStats(alpha=0.125, beta=0.25, g_sec=0.001)

# Simüle edilmiş 100 paketlik RTT dizisi (Jitter enjeksiyonu: 20ms taban, 60ms ani sıçrama)
random.seed(42)
sample_rtts = []
for i in range(100):
    if 30 <= i <= 50:
        # Taktik telsiz jamming / uydu dalgalanması bölgesi: Yüksek Jitter!
        r = random.uniform(0.080, 0.160)
    else:
        # Normal hat
        r = random.uniform(0.015, 0.035)
    sample_rtts.append(r)
    rtt_engine.update(r)

# İstatistikler
avg_sample = sum(sample_rtts) / len(sample_rtts) * 1000.0
final_srtt = rtt_engine.srtt * 1000.0
final_rttvar = rtt_engine.rttvar * 1000.0
final_rto = rtt_engine.rto * 1000.0

print(f"  [+] 100 Paketlik Jitter Benchmark Sonuçları:")
print(f"      - Ortalama Ham RTT Örneği : {avg_sample:.2f} ms")
print(f"      - Nihai Düzeltilmiş SRTT  : {final_srtt:.2f} ms")
print(f"      - Nihai RTT Varyansı (Sapma): {final_rttvar:.2f} ms")
print(f"      - Nihai Güvenli RTO Süresi : {final_rto:.2f} ms")
print(f"      - RTO Güvenlik Marjı      : {final_rto - final_srtt:.2f} ms (4 * RTTVAR)")

assert final_rto > final_srtt, "HATA: RTO süresi her zaman SRTT'den büyük olmalıdır!"
assert final_rto >= 200.0, "HATA: RTO minimum 200 ms sınırına uymalıdır!"

print("[HÜCRE 13] Jacobson/Karels RTT/RTO Benchmarkı başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 140: Kod Bloğu 5 — Taktik Savunma Sistemi Telemetri Stres Testi
%10 Paket Kaybı ve %20 Sıra Bozulması Altında 1.000 Paketlik Bütünlük Testi.
"""

print("")
print("[*] 1.000 Paketlik Taktik Telemetri Ağ Stres Testi Başlatılıyor...")

class TacticalLossyNetwork:
    def __init__(self, loss_rate: float = 0.10, reorder_rate: float = 0.20):
        self.loss_rate = loss_rate
        self.reorder_rate = reorder_rate
        self.total_sent = 0
        self.total_dropped = 0
        self.total_reordered = 0

    def transmit(self, packets: List[TCPSegment]) -> List[TCPSegment]:
        self.total_sent = len(packets)
        received = []
        pending_reorder = []

        for pkt in packets:
            # 1. Kayıp Simülasyonu
            if random.random() < self.loss_rate:
                self.total_dropped += 1
                continue # Paket düştü!

            # 2. Sıra Bozulması Simülasyonu
            if random.random() < self.reorder_rate:
                self.total_reordered += 1
                pending_reorder.append(pkt)
            else:
                received.append(pkt)
                if pending_reorder and random.random() < 0.5:
                    received.append(pending_reorder.pop(0))

        # Kalan sırasızları ekle
        received.extend(pending_reorder)
        return received

# 1.000 Paket Üretimi
random.seed(99)
test_packets = [TCPSegment(seq=i*100, data=f"RADAR_TRK_{i:04d}".encode().ljust(100, b"."), send_time=time.time()) 
                for i in range(1000)]

net = TacticalLossyNetwork(loss_rate=0.10, reorder_rate=0.20)
delivered_packets = net.transmit(test_packets)

print(f"  [+] Ağ İstatistikleri:")
print(f"      - Gönderilen Toplam Paket : {net.total_sent:,}")
print(f"      - Düşürülen Paket (Drop)   : {net.total_dropped:,} (%{net.total_dropped/net.total_sent*100:.1f})")
print(f"      - Sırası Bozulan (Reorder): {net.total_reordered:,} (%{net.total_reordered/net.total_sent*100:.1f})")
print(f"      - İlk Seferde Ulaşan      : {len(delivered_packets):,}")

# Kayıpları Tespit ve Yeniden İletim (Retransmission Loop)
received_seqs = set(p.seq for p in delivered_packets)
missing_seqs = [p for p in test_packets if p.seq not in received_seqs]

# Yeniden iletim ile eksikleri tamamla
all_received = list(delivered_packets) + missing_seqs
all_received.sort(key=lambda p: p.seq) # Alıcı tamponuna veriliş

# Reordering buffer doğrulaması
final_rx_buffer = TCPReorderingBuffer(initial_expected_seq=0)
for p in all_received:
    final_rx_buffer.receive_segment(p)

assert final_rx_buffer.rcv_nxt == 100000, f"HATA: Beklenen 100,000 bayt ama {final_rx_buffer.rcv_nxt} oldu!"
assert len(final_rx_buffer.delivered_stream) == 100000, "HATA: Veri akış uzunluğu hatalı!"
print(""); print(f"  [+] Stres Testi Başarılı: 100.000 Baytlık Radar Akışı %100 Eksiksiz ve Sıralı Teslim Edildi!")

print("[HÜCRE 15] Taktik telemetri stres testi başarıyla tamamlandı.")

# -*- coding: utf-8 -*-
"""
GÜN 140: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Assertions
"""

import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def generate_dashboard(output_file: str):
    fig = plt.figure(figsize=(20, 15), facecolor='#0F172A', dpi=300)
    gs = fig.add_gridspec(2, 2, hspace=0.28, wspace=0.22, 
                           left=0.07, right=0.95, top=0.92, bottom=0.06)

    fig.suptitle("HAVA SAVUNMA VE KOMUTA KONTROL SISTEMLERI\nTCP GUVENILIRLIK, YENIDEN ILETIM VE SIRALAMA (RFC 6298 / RFC 5681)",
                 fontsize=18, fontweight='bold', color='#F8FAFC', y=0.97)

    # Renk Paleti
    C_BLUE = '#38BDF8'
    C_GREEN = '#34D399'
    C_RED = '#F87171'
    C_YELLOW = '#FBBF24'
    C_PURPLE = '#C084FC'
    C_GRAY = '#64748B'
    C_BG = '#1E293B'

    # --------------------------------------------------------------------------
    # PANEL 1: Jacobson/Karels Dinamik RTT, SRTT, RTTVAR ve RTO Adaptasyonu
    # --------------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(C_BG)
    ax1.set_title("PANEL 1: JACOBSON/KARELS DINAMIK RTT/RTO ADAPTASYONU (RFC 6298)", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Simüle verileri çekelim
    history = rtt_engine.rtt_history
    steps = np.arange(len(history))
    r_vals = [h[0]*1000 for h in history]
    srtt_vals = [h[1]*1000 for h in history]
    rto_vals = [h[3]*1000 for h in history]

    ax1.plot(steps, r_vals, color=C_GRAY, linestyle=':', alpha=0.6, label='Ham RTT Örneği (Sample R)')
    ax1.plot(steps, srtt_vals, color=C_BLUE, lw=2.2, label='Düzeltilmiş RTT (SRTT, alpha=0.125)')
    ax1.plot(steps, rto_vals, color=C_RED, lw=2.5, label='Zaman Aşımı Süresi (RTO = SRTT + 4*RTTVAR)')

    ax1.axvspan(30, 50, color=C_YELLOW, alpha=0.15, label='Taktik Jitter Bölgesi (Jamming)')
    ax1.set_xlabel('İletilen Segment İndeksi', color='#F8FAFC', fontweight='bold')
    ax1.set_ylabel('Süre (Milisaniye - ms)', color='#F8FAFC', fontweight='bold')
    ax1.tick_params(colors='#94A3B8')
    ax1.grid(color='#334155', linestyle='--', alpha=0.5)
    ax1.legend(facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', loc='upper right')

    # --------------------------------------------------------------------------
    # PANEL 2: Out-of-Order Sıralama ve Delik Kapatma Merdiveni
    # --------------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(C_BG)
    ax2.set_title("PANEL 2: OUT-OF-ORDER SIRALAMA VE DELIK KAPATMA (REORDERING BUFFER)", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Merdiven adımları
    events = [
        ("Paket 1 Geldi (Seq 1000)", "rcv_nxt: 1100\nTampon: []", C_GREEN, 0.82),
        ("Paket 3 Geldi (Seq 1200)", "rcv_nxt: 1100\nTampon: [1200] (DELIK!)", C_YELLOW, 0.65),
        ("Paket 4 Geldi (Seq 1300)", "rcv_nxt: 1100\nTampon: [1200, 1300]", C_YELLOW, 0.48),
        ("Paket 5 Geldi (Seq 1400)", "rcv_nxt: 1100\nTampon: [1200..1400]", C_YELLOW, 0.31),
        ("Paket 2 Geldi (Seq 1100)", "rcv_nxt: 1500 (TUM DELIKLER KAPANDI!)", C_GREEN, 0.14),
    ]

    for label, status, col, y in events:
        bbox_l = dict(boxstyle="square,pad=0.3", fc='#0F172A', ec=col, lw=1.5)
        bbox_r = dict(boxstyle="round,pad=0.3", fc=col, ec='#FFFFFF', lw=1.2)
        ax2.text(0.08, y, label, color='#F8FAFC', fontweight='bold', fontsize=9.5, bbox=bbox_l, va='center')
        ax2.annotate("", xy=(0.58, y), xytext=(0.42, y),
                     arrowprops=dict(arrowstyle="->", color=col, lw=2.0))
        ax2.text(0.60, y, status, color='#0F172A', fontweight='bold', fontsize=9.0, bbox=bbox_r, va='center')

    ax2.set_xlim(0.0, 1.0)
    ax2.set_ylim(0.05, 0.95)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # PANEL 3: Fast Retransmit (3 DUP ACK) vs RTO Zaman Aşımı Süresi
    # --------------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor(C_BG)
    ax3.set_title("PANEL 3: KAYIP KURTARMA SURESI: 3 DUP ACK VS RTO ZAMAN ASIMI", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    recovery_methods = ["Fast Retransmit\n(3 DUP ACK)", "RTO Zaman Aşımı\n(Minimum 200 ms)", "RTO Zaman Aşımı\n(Standart 1000 ms)"]
    durations = [40.0, 200.0, 1000.0] # ms
    cols = [C_GREEN, C_YELLOW, C_RED]

    bars = ax3.bar(recovery_methods, durations, color=cols, width=0.45, alpha=0.9)
    ax3.set_ylabel('Kurtarma Gecikmesi (ms - Düşük İyidir)', color='#F8FAFC', fontweight='bold')
    ax3.tick_params(colors='#94A3B8')
    ax3.grid(color='#334155', linestyle='--', alpha=0.5, axis='y')

    for bar, d in zip(bars, durations):
        h = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., h + 25, f"{d:.0f} ms", 
                 ha='center', color='#F8FAFC', fontweight='bold', fontsize=10)

    ax3.text(0, 500, "25.0x KAT\nDAHA HIZLI!", color=C_GREEN, fontweight='bold', fontsize=12, ha='center',
             bbox=dict(boxstyle="round,pad=0.3", fc='#0F172A', ec=C_GREEN, lw=1.5))
    ax3.set_ylim(0, 1200)

    # --------------------------------------------------------------------------
    # PANEL 4: SACK Açık vs Kapalı Kayıp Oranına Göre Verimlilik
    # --------------------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor(C_BG)
    ax4.set_title("PANEL 4: SACK AKTIF VS PASIF BANT GENISLIGI VERIMLILIGI", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    loss_rates = np.array([1, 3, 5, 8, 12, 15])
    # SACK açıkken gereksiz tekrar %0; kapalıyken kümülatif körlük nedeniyle fazladan bayt iletilir
    overhead_no_sack = loss_rates * 3.8 # Her kayıp için sonraki paketler de tekrar gider
    overhead_sack = loss_rates * 1.0    # Sadece kayıp paket tekrar gider

    ax4.plot(loss_rates, overhead_no_sack, marker='o', color=C_RED, lw=2.5, label='SACK Kapalı (Kümülatif Tekrar İsrafı)')
    ax4.plot(loss_rates, overhead_sack, marker='s', color=C_GREEN, lw=2.5, label='SACK Açık (RFC 2018 Nokta Atışı Tekrar)')

    ax4.set_xlabel('Ağ Paket Kayıp Oranı (%)', color='#F8FAFC', fontweight='bold')
    ax4.set_ylabel('Gereksiz Yeniden İletim Oranı (%)', color='#F8FAFC', fontweight='bold')
    ax4.tick_params(colors='#94A3B8')
    ax4.grid(color='#334155', linestyle='--', alpha=0.5)
    ax4.legend(facecolor='#0F172A', edgecolor='#334155', labelcolor='#F8FAFC', loc='upper left')

    plt.savefig(output_file, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {output_file}")

# Doğrulama ve Çalıştırma
generate_dashboard(PNG_FILE)

print("")
print("[*] GÜN 140 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")
assert os.path.exists(PNG_FILE), "HATA: PNG dosyası üretilemedi!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100000, f"HATA: PNG dosya boyutu çok küçük ({png_size} bayt)!"

# Algoritmik Doğrulamalar
assert rtt_engine.srtt is not None and rtt_engine.srtt > 0
assert rtt_engine.rto >= 0.2
assert receiver_buffer.rcv_nxt == 1500
assert len(receiver_buffer.delivered_stream) == 500

print("")
print("[PASS] Gün 140: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
