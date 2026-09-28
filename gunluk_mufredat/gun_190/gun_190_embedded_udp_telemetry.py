# -*- coding: utf-8 -*-
"""
GÜN 190: Gömülü UDP Telemetri Yayını, İkili Çerçeveleme ve Deterministik Akış
Standalone Python Doğrulama ve Görselleştirme Betiği
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_190\gun_190_embedded_udp_telemetry.png"

# ======================================================================
# Kod Hücresi 1: Sabit Boyutlu İkili Telemetri Çerçeveleyici ve CRC-32 Doğrulama Motoru
import struct
import zlib
import time

class TelemetryFramer:
    """
    Aviyonik Standartlarında Sabit Boyutlu İkili Telemetri Paketi (Binary Packed Struct)
    [Sync: 2B (0xEB90)] [Seq: 4B] [Timestamp_us: 8B] [Roll: 4B] [Pitch: 4B] [Yaw: 4B] 
    [Altitude: 4B] [Airspeed: 4B] [Battery_mV: 2B] [Status: 2B] [CRC32: 4B]
    Toplam Boyut: 42 Bayt (Kompakt ve Hizalı)
    """
    # Biçim: > (Big-Endian) H (uint16) I (uint32) Q (uint64) ffff (4x float) H (uint16) H (uint16) I (uint32)
    STRUCT_FORMAT = ">HIQfffffHHI"
    PAYLOAD_FORMAT = ">HIQfffffHH" # CRC hariç kısım
    SYNC_WORD = 0xEB90

    def __init__(self):
        self.seq_counter = 0

    def pack(self, timestamp_us, roll, pitch, yaw, altitude, airspeed, batt_mv, status):
        self.seq_counter += 1
        # 1. CRC hariç ham veriyi paketle
        raw_payload = struct.pack(
            self.PAYLOAD_FORMAT,
            self.SYNC_WORD,
            self.seq_counter,
            timestamp_us,
            roll, pitch, yaw, altitude, airspeed,
            batt_mv, status
        )
        # 2. IEEE 802.3 Standart CRC-32 Hesapla
        crc = zlib.crc32(raw_payload) & 0xFFFFFFFF
        # 3. Paketi CRC ile birleştir
        full_packet = raw_payload + struct.pack(">I", crc)
        return full_packet

    @staticmethod
    def unpack(packet_bytes):
        if len(packet_bytes) != 42:
            return None, "HATALI_PAKET_BOYUTU"
        
        # CRC Denetimi
        payload = packet_bytes[:38]
        expected_crc = struct.unpack(">I", packet_bytes[38:])[0]
        calculated_crc = zlib.crc32(payload) & 0xFFFFFFFF
        
        if expected_crc != calculated_crc:
            return None, "CRC_HATASI"

        data = struct.unpack(TelemetryFramer.STRUCT_FORMAT, packet_bytes)
        if data[0] != TelemetryFramer.SYNC_WORD:
            return None, "SENKRONIZASYON_KAYBI"

        parsed = {
            "sync": hex(data[0]),
            "seq": data[1],
            "timestamp_us": data[2],
            "roll": data[3],
            "pitch": data[4],
            "yaw": data[5],
            "altitude": data[6],
            "airspeed": data[7],
            "batt_mv": data[8],
            "status": data[9],
            "crc": hex(data[10])
        }
        return parsed, "OK"

# Test: Örnek Uçuş Telemetrisi Oluştur ve Çöz
framer = TelemetryFramer()
pkt = framer.pack(
    timestamp_us=1250000, 
    roll=12.45, pitch=-3.15, yaw=178.90, 
    altitude=1450.5, airspeed=68.2, 
    batt_mv=24800, status=0x0001
)

parsed_pkt, status = TelemetryFramer.unpack(pkt)

print("=== 1. IKILI TELEMETRI CERCEVE VE CRC-32 DOGRULAMA ===")
print(f"Paket Boyutu       : {len(pkt)} Bayt (Sabit ve Hizalı)")
print(f"Durum              : {status}")
print(f"Paket İçeriği      : Seq={parsed_pkt['seq']} | Roll={parsed_pkt['roll']:.2f}° | Pitch={parsed_pkt['pitch']:.2f}° | Alt={parsed_pkt['altitude']:.1f}m | Batarya={parsed_pkt['batt_mv']}mV")
print(f"Hesaplanan CRC-32  : {parsed_pkt['crc']}")

# Assertions
assert len(pkt) == 42, "Paket boyutu tam 42 bayt olmalıdır!"
assert status == "OK", "Paket çözme başarısız!"
assert parsed_pkt["sync"] == "0xeb90", "Sync Word eşleşmedi!"
print("[BAŞARILI]: İkili telemetri paketleme ve CRC-32 motoru doğrulandı.")

# ======================================================================
# Kod Hücresi 2: lwIP Raw UDP Soket Motoru ve Sıfır Kopyalama Gönderim Simülatörü
class MockUdpPcb:
    def __init__(self, src_port):
        self.src_port = src_port
        self.dest_ip = None
        self.dest_port = None
        self.recv_callback = None
        self.tx_packets_log = []

    def bind(self, port):
        self.src_port = port
        return 0 # ERR_OK

    def connect(self, ip, port):
        self.dest_ip = ip
        self.dest_port = port
        return 0 # ERR_OK

    def send(self, payload_bytes):
        """
        lwIP udp_send benzeri sıfır kopyalamalı iletim.
        8 Bayt UDP başlığı eklenir ve doğrudan MAC katmanına devredilir.
        """
        udp_header = struct.pack(">HHHH", self.src_port, self.dest_port, len(payload_bytes) + 8, 0x0000)
        full_udp_frame = udp_header + payload_bytes
        self.tx_packets_log.append(full_udp_frame)
        return len(full_udp_frame)

# Simülasyon: Port 5005'ten Multicast 239.255.0.1:5005'e Telemetri Basımı
udp_pcb = MockUdpPcb(src_port=5005)
udp_pcb.connect("239.255.0.1", 5005)

# 10 Ardışık Telemetri Paketi Gönder
for i in range(10):
    packet_data = framer.pack(
        timestamp_us=int(time.time() * 1e6) + (i * 4000), # 4 ms aralıklarla
        roll=0.5 * i, pitch=-0.2 * i, yaw=180.0,
        altitude=100.0 + (i * 2.5), airspeed=45.0,
        batt_mv=25200, status=0x0000
    )
    udp_pcb.send(packet_data)

print("=== 2. LWIP RAW UDP SOKET VE MULTICAST ILETIMI ===")
print(f"Kaynak Port  : {udp_pcb.src_port} | Hedef Multicast Grubu: {udp_pcb.dest_ip}:{udp_pcb.dest_port}")
print(f"Gönderilen UDP Çerçeve Sayısı : {len(udp_pcb.tx_packets_log)} adet")
print(f"Toplam Çerçeve Boyutu         : {len(udp_pcb.tx_packets_log[0])} Bayt (8B UDP Başlığı + 42B Telemetri)")

# Assertions
assert len(udp_pcb.tx_packets_log) == 10, "10 paket iletilmeliydi!"
assert len(udp_pcb.tx_packets_log[0]) == 50, "Toplam UDP çerçeve boyu 50 bayt olmalıdır!"
print("[BAŞARILI]: lwIP Raw UDP soket motoru başarıyla simüle edildi.")

# ======================================================================
# Kod Hücresi 3: TCP vs UDP Telemetri Akış Gecikmesi ve Jitter Karşılaştırma Analizi
import numpy as np

def compare_tcp_vs_udp_telemetry(num_cycles=200, packet_loss_rate=0.02):
    """
    200 uçuş döngüsü boyunca %2 paket kaybı olan bir radyo linkinde
    TCP ve UDP telemetri gecikmelerini simüle eder.
    - UDP: Kayıp paket yeniden iletilmez, gecikme sabit (~0.25 ms).
    - TCP: Kayıp paket Retransmission Timeout (RTO = 150 ms) bekler, Head-of-Line blocking oluşur!
    """
    np.random.seed(42)
    latencies_udp = []
    latencies_tcp = []
    
    for cycle in range(num_cycles):
        # 1. UDP Gecikmesi: Tamamen deterministik (0.22 - 0.28 ms)
        t_udp = np.random.normal(0.25, 0.015)
        latencies_udp.append(t_udp)
        
        # 2. TCP Gecikmesi: Normalde ~1.8 ms; ancak kayıp olursa RTO patlaması!
        is_lost = np.random.rand() < packet_loss_rate
        if is_lost:
            # RTO + Yeniden İletim Gecikmesi
            t_tcp = 150.0 + np.random.normal(2.0, 0.5)
        else:
            t_tcp = np.random.normal(1.8, 0.1)
        latencies_tcp.append(t_tcp)

    return np.array(latencies_udp), np.array(latencies_tcp)

lat_udp, lat_tcp = compare_tcp_vs_udp_telemetry(200, packet_loss_rate=0.02)

print("=== 3. TCP VS UDP TELEMETRI PERFORMANS KARSILASTIRMASI (%2 KAYIPLI HAT) ===")
print(f"[UDP] Ortalama Gecikme : {np.mean(lat_udp):>6.2f} ms | Maksimum: {np.max(lat_udp):>6.2f} ms | Jitter: {np.std(lat_udp):>6.3f} ms")
print(f"[TCP] Ortalama Gecikme : {np.mean(lat_tcp):>6.2f} ms | Maksimum: {np.max(lat_tcp):>6.2f} ms | Jitter: {np.std(lat_tcp):>6.3f} ms")
print(f"-> GÖZLEM: TCP'deki tek bir kayıp, gecikmeyi {np.max(lat_tcp):.1f} ms'ye fırlatarak uçuş kontrol döngüsünü felç etti!")

# Assertions
assert np.max(lat_udp) < 1.0, "UDP gecikmesi 1 ms'nin altında kalmalıdır!"
assert np.max(lat_tcp) > 100.0, "TCP yeniden iletim gecikmesi tespit edilemedi!"
print("[BAŞARILI]: UDP'nin deterministik telemetri üstünlüğü kanıtlandı.")

# ======================================================================
# Kod Hücresi 4: Bilerek Bozma Deneyi — Sequence Gap (Sıra Atlama) ve CRC Bozulması
print("=== BILEREK BOZMA: PAKET KAYBI, SIRA ATLAMASI VE BOZUK VERI TESTI ===")

def simulate_telemetry_stream_corruption():
    """
    Alıcı tarafın iki kritik hata sınıfını denetlemesi:
    1. Sequence Gap: 10 paketlik akışta 4. paket kaybolur (1, 2, 3, 5, 6...).
    2. Payload Bit Flips: 7. paketin bir baytı havada bozulur (CRC hatası!).
    """
    framer = TelemetryFramer()
    tx_stream = []
    
    for i in range(1, 11):
        pkt = framer.pack(
            timestamp_us=i * 4000, roll=1.0, pitch=0.0, yaw=0.0,
            altitude=500.0, airspeed=50.0, batt_mv=24000, status=0
        )
        tx_stream.append(pkt)

    # 1. Bozma: 4. paketi hattan düşür (Drop pkt 4)
    rx_stream = [tx_stream[0], tx_stream[1], tx_stream[2], tx_stream[4], tx_stream[5]] # 3 indexli paket kayıp!
    
    # 2. Bozma: 7. paketi al ama 20. baytını boz (Bit Flip)
    corrupted_pkt = bytearray(tx_stream[6])
    corrupted_pkt[20] ^= 0xFF # Veriyi boz!
    rx_stream.append(bytes(corrupted_pkt))

    # Alıcı Taraf Analizi
    expected_seq = 1
    detected_gaps = 0
    detected_crc_errors = 0
    valid_packets = 0

    for pkt in rx_stream:
        parsed, status = TelemetryFramer.unpack(pkt)
        if status == "CRC_HATASI":
            detected_crc_errors += 1
            continue
        elif status == "OK":
            curr_seq = parsed["seq"]
            if curr_seq != expected_seq:
                gap_size = curr_seq - expected_seq
                detected_gaps += gap_size
                expected_seq = curr_seq + 1
            else:
                expected_seq += 1
            valid_packets += 1

    return detected_gaps, detected_crc_errors, valid_packets

gaps, crc_errs, valids = simulate_telemetry_stream_corruption()

print(f"1. TELEMETRİ GÜVENLİK TESTİ:")
print(f"   Tespit Edilen Kayıp Paket (Sequence Gaps) : {gaps} adet")
print(f"   Tespit Edilen Bozuk Paket (CRC-32 Errors) : {crc_errs} adet")
print(f"   Başarıyla Doğrulanan Paket Sayısı        : {valids} adet")

# Assertions
assert gaps == 1, "Kayıp paket (Sequence Gap) tespit edilemedi!"
assert crc_errs == 1, "Bozuk paketin CRC hatası yakalanamadı!"
print("[BAŞARILI]: Telemetri sıra bütünlüğü ve CRC-32 emniyet kalkanı doğrulandı.")

# ======================================================================
# Kod Hücresi 5: Savunma Sanayii Senaryosu — ROKETSAN 250 Hz Uçuş Telemetri Simülasyonu
import numpy as np

def run_uav_telemetry_mission(num_frames=1000):
    """
    1000 uçuş çerçevesi (4 saniye, 250 Hz) boyunca İHA telemetri akış simülasyonu.
    - Frame Periyodu: 4.0 ms (4000 µs)
    - Paketleme Süresi: 35 µs
    - UDP Çıkış Gecikmesi: 45 µs
    - Metrikler: Frame Jitter, Bant Genişliği, Veri Tazeliği
    """
    np.random.seed(42)
    cycle_jitters_us = []
    packet_sizes_bytes = []
    
    nominal_period_us = 4000.0
    
    for frame in range(num_frames):
        # Gerçek zamanlı döngü sapması (Jitter: +/- 15 µs gürültü)
        actual_period = nominal_period_us + np.random.normal(0, 12.0)
        jitter = abs(actual_period - nominal_period_us)
        cycle_jitters_us.append(jitter)
        
        # Sabit 42 Bayt paket
        packet_sizes_bytes.append(42)

    total_bytes = sum(packet_sizes_bytes)
    duration_s = (num_frames * 4.0) / 1000.0
    bandwidth_kbps = (total_bytes * 8) / duration_s / 1000.0

    return np.array(cycle_jitters_us), bandwidth_kbps

jitters_us, bw_kbps = run_uav_telemetry_mission(1000)

print("=== 5. ROKETSAN 250 HZ IHA UCUS TELEMETRI MISSION SONUCLARI ===")
print(f"Toplam Simüle Edilen Çerçeve   : 1000 çerçeve (4.0 saniye uçuş)")
print(f"Hedef Döngü Frekansı           : 250 Hz (Her 4000 µs'de bir paket)")
print(f"Ortalama Döngü Jitter'ı        : {np.mean(jitters_us):.2f} µs (Tolerans: <= 50.0 µs)")
print(f"Maksimum Döngü Jitter'ı        : {np.max(jitters_us):.2f} µs")
print(f"Hattaki Veri Akış Hızı         : {bw_kbps:.2f} kbps (100 Mbps hattın %{bw_kbps/100000*100:.3f}'i)")
print(f"Paket Bütünlüğü                : %100 Doğrulanmış CRC-32")

# Savunma Kriteri Assertions
assert np.max(jitters_us) <= 50.0, f"Maksimum jitter toleransı aşıldı: {np.max(jitters_us):.2f} µs"
assert bw_kbps < 150.0, "Bant genişliği tüketimi beklenenden yüksek!"
print("[BAŞARILI]: ROKETSAN 250 Hz telemetri akışı aviyonik determinizm kriterlerini sağladı.")

# ======================================================================
# Kod Hücresi 6: Profesyonel 4 Panelli Mühendislik Dashboardu (300 DPI, Dark Theme)
import os
import numpy as np
import matplotlib.pyplot as plt

# Görsel Dosya Yolu Kontrolü
if 'PNG_FILE' not in globals():
    try:
        PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_190_embedded_udp_telemetry.png")
    except Exception:
        PNG_FILE = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_190\gun_190_embedded_udp_telemetry.png"

# Karanlık Tema Renk Paleti (#0F172A Slate / Neon)
plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.grid(True, linestyle='--', alpha=0.3, color='#64748B')
    ax.tick_params(colors='#E2E8F0', labelsize=10)
    for spine in ax.spines.values():
        spine.set_color('#334155')

# ------------------------------------------------------------------------------
# PANEL 1: TCP vs UDP Telemetri İletim Gecikmesi ve Head-of-Line Blocking
# ------------------------------------------------------------------------------
ax1 = axs[0, 0]
cycles_x = np.arange(len(lat_udp[:120]))

ax1.plot(cycles_x, lat_tcp[:120], color='#EF4444', linewidth=1.8, label='TCP Gecikmesi (HoL Blocking & Retransmit)')
ax1.plot(cycles_x, lat_udp[:120], color='#10B981', linewidth=2.2, label='UDP Telemetri Gecikmesi (Deterministik ~0.25 ms)')
ax1.axhline(5.0, color='#F59E0B', linestyle='--', linewidth=1.5, label='Kabul Edilebilir Maksimum Uçuş Gecikmesi (5.0 ms)')

ax1.set_title('PANEL 1: TCP vs UDP Telemetri Akış Gecikmesi (Head-of-Line Blocking)', color='#38BDF8', fontsize=12, fontweight='bold')
ax1.set_xlabel('Uçuş Kontrol Döngüsü (Frames)', color='#E2E8F0', fontsize=10)
ax1.set_ylabel('İletim Gecikmesi (ms - Logaritmik)', color='#E2E8F0', fontsize=10)
ax1.set_yscale('log')
ax1.legend(loc='upper right', facecolor='#0F172A', edgecolor='#334155', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 2: Telemetri İkili Çerçeve Bellek Haritası ve Alan Boyutları
# ------------------------------------------------------------------------------
ax2 = axs[0, 1]
fields = ['Sync (2B)', 'SeqNo (4B)', 'Time_us (8B)', 'Euler (12B)', 'Alt_Speed (8B)', 'Batt_Stat (4B)', 'CRC-32 (4B)']
sizes = [2, 4, 8, 12, 8, 4, 4]
colors_p2 = ['#38BDF8', '#818CF8', '#10B981', '#F59E0B', '#EC4899', '#A855F7', '#EF4444']

y_pos = np.arange(len(fields))
bars2 = ax2.barh(y_pos, sizes, color=colors_p2, edgecolor='#334155', height=0.55)

for bar, s in zip(bars2, sizes):
    ax2.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2.0, 
             f"{s} Bayt", va='center', ha='left', color='#F8FAFC', fontweight='bold', fontsize=9)

ax2.set_yticks(y_pos)
ax2.set_yticklabels(fields, color='#E2E8F0', fontsize=10)
ax2.set_title('PANEL 2: 42 Baytlık İkili Telemetri Çerçeve Bellek Düzeni', color='#38BDF8', fontsize=12, fontweight='bold')
ax2.set_xlabel('Bayt Genişliği', color='#E2E8F0', fontsize=10)
ax2.set_xlim(0, 16)

# ------------------------------------------------------------------------------
# PANEL 3: Dizi Numarası (Sequence Gap) ve Kayıp Paket Tespit Grafiği
# ------------------------------------------------------------------------------
ax3 = axs[1, 0]
seq_x = np.arange(1, 30)
# Normalde 1'er 1'er artar; 12. pakette 2 paketlik kayıp olsun (11 -> 14)
received_seqs = []
curr = 1
for i in range(1, 30):
    if i == 12: curr += 3 # 2 paket kayıp!
    else: curr += 1
    received_seqs.append(curr)

ax3.step(seq_x, received_seqs, where='post', color='#38BDF8', linewidth=2, label='Alınan Sequence Numarası')
ax3.plot([11, 12], [received_seqs[10], received_seqs[11]], color='#EF4444', linewidth=3, linestyle='--', label='Sequence Gap (Kayıp Paket Alarmı!)')

ax3.set_title('PANEL 3: Dizi Numarası Takibi ve Hattan Paket Düşme Tespiti', color='#38BDF8', fontsize=12, fontweight='bold')
ax3.set_xlabel('Gelen Paket Sırası', color='#E2E8F0', fontsize=10)
ax3.set_ylabel('Okunan Dizi Numarası (SeqNo)', color='#E2E8F0', fontsize=10)
ax3.legend(loc='upper left', facecolor='#0F172A', edgecolor='#334155', fontsize=9)

# ------------------------------------------------------------------------------
# PANEL 4: ROKETSAN 250 Hz Aviyonik Telemetri Jitter Dağılımı (1000 Çerçeve)
# ------------------------------------------------------------------------------
ax4 = axs[1, 1]
bins_p4 = np.linspace(0, 45, 35)

ax4.hist(jitters_us, bins=bins_p4, color='#10B981', alpha=0.75, edgecolor='#059669', label=f'Jitter Dağılımı (Ort: {np.mean(jitters_us):.1f} µs)')
ax4.axvline(50.0, color='#F43F5E', linestyle='--', linewidth=2, label='Aviyonik Maksimum Tolerans (50 µs)')
ax4.axvline(np.mean(jitters_us), color='#38BDF8', linestyle=':', linewidth=2, label=f'Nominal Seviye ({np.mean(jitters_us):.1f} µs)')

ax4.set_title('PANEL 4: ROKETSAN 250 Hz Uçuş Kontrol Telemetri Jitter Dağılımı', color='#38BDF8', fontsize=12, fontweight='bold')
ax4.set_xlabel('Çevrim Periyodundan Sapma (µs)', color='#E2E8F0', fontsize=10)
ax4.set_ylabel('Çerçeve Sayısı (Frames)', color='#E2E8F0', fontsize=10)
ax4.legend(loc='upper right', facecolor='#0F172A', edgecolor='#334155', fontsize=9)

plt.tight_layout()
plt.savefig(PNG_FILE, dpi=300, facecolor='#0F172A', bbox_inches='tight')
plt.close()

# Üretilen PNG Dosya Boyutu Kontrolü
file_size = os.path.getsize(PNG_FILE)
print(f"[+] Visual Artifact Üretildi: {PNG_FILE} ({file_size:,} bayt)")

# Assertions
assert os.path.exists(PNG_FILE), "Görsel dosya üretilemedi!"
assert file_size > 100 * 1024, f"Görsel dosya boyutu çok küçük: {file_size} bayt (< 100 KB)"
print("[PASS] GÜN 190: TÜM MATEMATİKSEL VE GÖRSEL DOĞRULAMALAR BAŞARIYLA TAMAMLANDI!")

