# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 8 (CODE 1): TCP Byte-Stream ve Length-Prefixed Framing Motoru
Mesaj Sınırlarının Kaybolmasını Önleyen 4-Bayt Uzunluk Başlıklı Çerçeveleyici
"""

import struct
from typing import List, Tuple, Optional

class LengthPrefixedFramingCodec:
    """
    TCP bayt akışında mesaj sınırlarını koruyan çerçeveleme motoru.
    Format: [ 4-Bayt Big-Endian Payload Uzunluğu ] + [ N-Bayt Ham Veri ]
    """
    @staticmethod
    def encode_message(payload: bytes) -> bytes:
        """Mesajın başına 4 baytlık uzunluk ön-eki ekler."""
        length_header = struct.pack("!I", len(payload))
        return length_header + payload

class StreamReceiverBuffer:
    """
    Alıcı tarafta gelen parçalı (chunked) ve yapışık (coalesced) baytları
    biriktirip eksiksiz mesajları ayrıştıran akış tamponu.
    """
    def __init__(self):
        self.buffer = bytearray()

    def feed_bytes(self, chunk: bytes):
        """Ağdan gelen ham baytları tamponun sonuna ekler."""
        self.buffer.extend(chunk)

    def extract_messages(self) -> List[bytes]:
        """
        Tamponu inceler; eksiksiz tamamlanmış tüm mesajları ayrıştırıp döner.
        Eksik kalan baytları bir sonraki recv() için tamponda tutar.
        """
        messages = []
        while True:
            # 1. Aşama: En az 4 baytlık uzunluk başlığı var mı?
            if len(self.buffer) < 4:
                break # Başlık henüz tamamlanmadı
                
            payload_len = struct.unpack("!I", self.buffer[:4])[0]
            total_frame_len = 4 + payload_len
            
            # 2. Aşama: Mesajın tamamı tamponda birikti mi?
            if len(self.buffer) < total_frame_len:
                break # Gövde henüz tamamen gelmedi (Partial read)
                
            # 3. Aşama: Mesaj tamamlandı! Çıkar ve teslim et
            msg_payload = bytes(self.buffer[4:total_frame_len])
            messages.append(msg_payload)
            
            # Tampondan çıkarılan mesajı temizle
            del self.buffer[:total_frame_len]
            
        return messages

print("[HÜCRE 8] LengthPrefixedFramingCodec ve StreamReceiverBuffer motoru başarıyla yüklendi.")

# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 2): Taktik Görev Emri Akış Deneyi
Aynı Akışta Hem Yapışan (Coalesced) Hem de Parçalanan (Chunked) Emirlerin Hatasız Ayrıştırılması
"""

def run_tcp_stream_framing_experiment():
    print("")
    print("[*] Taktik TCP Akış ve Çerçeve Ayrıştırma Deneyi Başlatılıyor...")
    
    # 3 Adet Kritik Taktik Görev Emri
    orders = [
        b"TARGET_LOCK_AZIMUTH_120.4_RADAR_ALPHA",
        b"ENGAGE_MISSILE_BATTERY_3_FIRE",
        b"IFF_MODE_5_CRYPTOGRAPHIC_CHALLENGE_VERIFIED"
    ]
    
    # Gönderici taraf emirleri paketliyor
    stream_wire = bytearray()
    for o in orders:
        frame = LengthPrefixedFramingCodec.encode_message(o)
        stream_wire.extend(frame)
        
    print(f"  [+] Gönderici Tarafından {len(orders)} Emir Çerçevelendi.")
    print(f"  [+] Ağ Hattındaki Toplam Bayt: {len(stream_wire)} Bayt.")

    # -------------------------------------------------------------
    # SİMÜLASYON: Ağ Bu Baytları Kasıtlı Olarak Saçma Sapan Parçalara Bölüyor!
    # Parça 1: İlk mesajın yarısı (15 bayt)
    # Parça 2: İlk mesajın kalanı + 2. mesajın tamamı + 3. mesajın başı (Yapışma + Parçalanma)
    # Parça 3: 3. mesajın kalanı
    # -------------------------------------------------------------
    chunk1 = bytes(stream_wire[:15])
    chunk2 = bytes(stream_wire[15:85])
    chunk3 = bytes(stream_wire[85:])
    
    receiver_buf = StreamReceiverBuffer()
    decoded_orders = []

    print("\n  [>] 1. Ağ Parçası Geldi (15 Bayt)...")
    receiver_buf.feed_bytes(chunk1)
    msgs = receiver_buf.extract_messages()
    print(f"      Ayrışan Mesaj Sayısı: {len(msgs)} (Beklenen: 0, henüz başlık/gövde yetersiz)")
    assert len(msgs) == 0

    print("\n  [>] 2. Ağ Parçası Geldi (70 Bayt - Yapışık Segment)...")
    receiver_buf.feed_bytes(chunk2)
    msgs = receiver_buf.extract_messages()
    print(f"      Ayrışan Mesaj Sayısı: {len(msgs)} (1. ve 2. mesajlar eksiksiz çıktı!)")
    decoded_orders.extend(msgs)
    assert len(msgs) == 2

    print("\n  [>] 3. Ağ Parçası Geldi (Kalan Baytlar)...")
    receiver_buf.feed_bytes(chunk3)
    msgs = receiver_buf.extract_messages()
    print(f"      Ayrışan Mesaj Sayısı: {len(msgs)} (3. mesaj tamamlandı!)")
    decoded_orders.extend(msgs)
    assert len(msgs) == 1

    # Birebir Doğrulama
    print("\n  [+] Çözümlenen Emirler:")
    for idx, d in enumerate(decoded_orders):
        assert d == orders[idx]
        print(f"      - Emir {idx+1}: {d.decode('ascii')} -> [TAM VE DOĞRU]")

    print("\n  [+] TCP Akış Çerçeveleme Deneyi %100 Başarıyla Tamamlandı!")
    return True

assert run_tcp_stream_framing_experiment(), "HATA: Akış deneyi başarısız!"

# -*- coding: utf-8 -*-
"""
HÜCRE 13 (CODE 3): Nagle Algoritması Gecikme Simülatörü ve Çerçevesiz Çöküş Testi
TCP_NODELAY Kapalıyken 40 ms Gecikme Spike'ı ve Çerçevesiz Ayrıştırma Hatası
"""

def run_tcp_sabotage_lab():
    print("")
    print("[*] TCP Sabotaj ve Gecikme Arıza Enjeksiyon Testleri Başlatılıyor...")
    
    # -------------------------------------------------------------
    # SABOTAJ 1: Çerçevesiz İletişimde Paket Yapışması Hatası
    # -------------------------------------------------------------
    raw_stream_without_framing = b"CMD_FIRE_MISSILE_1CMD_FIRE_MISSILE_2" # İki emir yapıştı!
    
    def naive_parser(data: bytes) -> str:
        # Acemi geliştirici tek bir emir bekliyor
        if not data.startswith(b"CMD_FIRE_MISSILE_"):
            raise ValueError("Bozuk Paket!")
        # Emir numarasını almaya çalışıyor
        return data.decode('ascii')

    parsed = naive_parser(raw_stream_without_framing)
    # Beklenti tek emir idi ancak yapışık veri geldi
    is_corrupted = (parsed != "CMD_FIRE_MISSILE_1")
    assert is_corrupted is True
    print(f"  [+] Sabotaj 1 İspatlandı: Çerçevesiz Akışta Yapışan Paketler Ayrıştırılamadı ({parsed}).")

    # -------------------------------------------------------------
    # SABOTAJ 2: Nagle + Delayed ACK Çakışma Simülasyonu
    # -------------------------------------------------------------
    def simulate_tcp_transfer(packet_size: int, nodelay: bool) -> float:
        """Gecikmeyi milisaniye cinsinden simüle eder."""
        base_network_latency = 0.8 # ms
        if nodelay:
            return base_network_latency # Anında iletim
        else:
            if packet_size < 1460: # MSS'ten küçükse Nagle devreye girer
                # Delayed ACK bekleme süresi eklenir (40 ms)
                return base_network_latency + 40.0
            return base_network_latency

    lat_nagle_on = simulate_tcp_transfer(packet_size=64, nodelay=False)
    lat_nagle_off = simulate_tcp_transfer(packet_size=64, nodelay=True)

    print(f"  [+] Sabotaj 2 Sonuçları:")
    print(f"      - Nagle Açık (TCP_NODELAY=0)  : {lat_nagle_on:.1f} ms (40 ms Gecikme Tuzağı!)")
    print(f"      - Nagle Kapalı (TCP_NODELAY=1): {lat_nagle_off:.1f} ms (Yüksek Hızlı Taktik İletim)")
    
    assert lat_nagle_on >= 40.0
    assert lat_nagle_off < 2.0
    print("  [+] Tüm TCP Sabotaj Testleri Başarıyla Geçti!")
    return True

assert run_tcp_sabotage_lab(), "HATA: TCP sabotaj testleri başarısız!"

# -*- coding: utf-8 -*-
"""
HÜCRE 15 (CODE 4): TCP_NODELAY Etkin vs Kapalı İletim Gecikmesi Benchmark Suite
Küçük Taktik Paketlerde 40 ms Gecikme Spike'ı ve Throughput Analizi
"""

import time

def run_nodelay_benchmark():
    print("")
    print("[*] TCP_NODELAY Performans ve Gecikme Benchmarkı Başlatılıyor...")
    
    NUM_COMMANDS = 1000
    
    # 1. Senaryo: Nagle Açık (TCP_NODELAY = 0)
    # Her küçük pakette 40 ms Delayed ACK beklemesi simülasyonu
    # (Matematiksel modelleme: 1000 emir x 40 ms = 40.000 ms)
    simulated_nagle_time_s = NUM_COMMANDS * 0.0408 # 40.8 ms per cmd
    rate_nagle = NUM_COMMANDS / simulated_nagle_time_s
    
    # 2. Senaryo: TCP_NODELAY = 1 (Nagle Kapalı)
    # Nominal ağ gecikmesi: ~0.8 ms per cmd
    simulated_nodelay_time_s = NUM_COMMANDS * 0.0008 # 0.8 ms per cmd
    rate_nodelay = NUM_COMMANDS / simulated_nodelay_time_s
    
    print(f"  [+] {NUM_COMMANDS:,} Taktik Emir İletim Kıyaslaması:")
    print(f"      - Nagle Devrede (Default)   : {simulated_nagle_time_s:.2f} saniye ({rate_nagle:.1f} Emir/s)")
    print(f"      - TCP_NODELAY = 1 (Taktik) : {simulated_nodelay_time_s:.2f} saniye ({rate_nodelay:,.0f} Emir/s)")
    print(f"      - Hızlanma Katsayısı        : {rate_nodelay / rate_nagle:.1f}x KAT DAHA HIZLI!")

    assert rate_nodelay > (rate_nagle * 20.0), "HATA: TCP_NODELAY en az 20 kat daha hızlı olmalıdır!"
    return rate_nagle, rate_nodelay

rate_nagle, rate_nodelay = run_nodelay_benchmark()

# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Çok Mesajlı Taktik Füze Ateşleme Akış Stres Testi
1.000 Bağımsız Füze Emrinin Rastgele Parçalanmış Akıştan %100 Kusursuz Ayrıştırılması
"""

import random

def run_missile_stream_stress_suite():
    print("")
    print("[*] 1.000 Mesajlık Taktik Füze Akış Stres Testi Başlatılıyor...")
    
    NUM_MESSAGES = 1000
    original_messages = [f"MISSILE_FIRE_CMD_ID_{i:04d}_TARGET_COORD_39.9_32.8".encode('ascii') for i in range(NUM_MESSAGES)]
    
    # Tüm mesajlar uzunluk ön-eki ile tek bir akışa paketleniyor
    stream_pipeline = bytearray()
    for m in original_messages:
        stream_pipeline.extend(LengthPrefixedFramingCodec.encode_message(m))
        
    print(f"  [+] Toplam Akış Boyutu: {len(stream_pipeline):,} Bayt.")

    # Akış rastgele parçalara (chunk) bölünüyor (10 bayt ile 250 bayt arası rastgele)
    receiver = StreamReceiverBuffer()
    extracted_all = []
    
    offset = 0
    while offset < len(stream_pipeline):
        chunk_size = random.randint(10, 250)
        chunk = bytes(stream_pipeline[offset:offset+chunk_size])
        offset += chunk_size
        
        receiver.feed_bytes(chunk)
        msgs = receiver.extract_messages()
        extracted_all.extend(msgs)

    print(f"  [+] Stres Testi Tamamlandı:")
    print(f"      - Gönderilen Toplam Mesaj: {NUM_MESSAGES:,}")
    print(f"      - Ayrıştırılan Mesaj Sayısı: {len(extracted_all):,}")
    print(f"      - Kalan Tampon Boyutu    : {len(receiver.buffer)} Bayt")
    
    assert len(extracted_all) == NUM_MESSAGES
    assert len(receiver.buffer) == 0
    for idx, m in enumerate(original_messages):
        assert extracted_all[idx] == m

    print("  [+] 1.000 Mesajın Tamamı Sıralı ve Sıfır Bozulmayla (%100 Başarıyla) Ayrıştırıldı!")
    return True

assert run_missile_stream_stress_suite(), "HATA: Stres testi başarısız!"

# -*- coding: utf-8 -*-
"""
HÜCRE 19 (CODE 6): 4-Panelli TCP Dashboard Üretici ve Katı Assertions
300 DPI, #0F172A Koyu Tema ile Savunma Sanayii TCP Mimarisi Görselleştirme Panosu
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_tcp_dashboard(output_path: str):
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')
    
    DARK_BG = '#1E293B'
    TEXT_COLOR = '#F8FAFC'
    ACCENT_RED = '#EF4444'
    ACCENT_GREEN = '#10B981'
    ACCENT_BLUE = '#38BDF8'
    ACCENT_AMBER = '#F59E0B'
    ACCENT_PURPLE = '#A855F7'

    # -------------------------------------------------------------
    # PANEL 1: TCP Byte-Stream vs UDP Datagram
    # -------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor(DARK_BG)
    ax1.set_title("1. İletim Modeli: TCP Byte-Stream vs UDP Datagram", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)

    # TCP Gösterimi
    rect_tcp = patches.Rectangle((0.5, 3.2), 9.0, 1.8, facecolor=ACCENT_BLUE, edgecolor='#FFFFFF', alpha=0.7, lw=1.5)
    ax1.add_patch(rect_tcp)
    ax1.text(5.0, 4.1, "TCP Byte-Stream: Kesintisiz Bayt Akışı (Sınır Yok!)\n[Byte 0] [Byte 1] [Byte 2] ... [Byte N] (Yapışır / Parçalanır)", color=TEXT_COLOR, ha='center', va='center', fontsize=9, fontweight='bold')

    # UDP Gösterimi
    ax1.text(0.5, 2.2, "UDP Datagram: Kesin Mesaj Sınırları (1 Send = 1 Receive)", color=ACCENT_GREEN, fontsize=10, fontweight='bold')
    udp_boxes = [("Datagram #1", 0.5), ("Datagram #2", 3.8), ("Datagram #3", 7.1)]
    for text, x in udp_boxes:
        rect = patches.Rectangle((x, 0.6), 2.5, 1.4, facecolor=ACCENT_GREEN, edgecolor='#FFFFFF', alpha=0.75, lw=1.5)
        ax1.add_patch(rect)
        ax1.text(x + 1.25, 1.3, text, color=TEXT_COLOR, ha='center', va='center', fontsize=8, fontweight='bold')

    ax1.set_xlim(0, 10.0)
    ax1.set_ylim(0, 6.0)
    ax1.axis('off')

    # -------------------------------------------------------------
    # PANEL 2: Length-Prefixed Framing Mimarisi
    # -------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor(DARK_BG)
    ax2.set_title("2. Uzunluk Ön-Ekli Çerçeveleme (Length-Prefixed Framing)", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)

    frames = [
        ("4B Len\n[0x0028]", "Mesaj A Yükü (40 Bayt - Füze Emri)", 0.5, 3.5, ACCENT_AMBER, ACCENT_BLUE),
        ("4B Len\n[0x003C]", "Mesaj B Yükü (60 Bayt - Radar Kilidi)", 0.5, 1.2, ACCENT_AMBER, ACCENT_PURPLE)
    ]

    for len_text, payload_text, x, y, col_hdr, col_pay in frames:
        r_hdr = patches.Rectangle((x, y), 2.0, 1.5, facecolor=col_hdr, edgecolor='#FFFFFF', alpha=0.8, lw=1.5)
        r_pay = patches.Rectangle((x + 2.0, y), 7.0, 1.5, facecolor=col_pay, edgecolor='#FFFFFF', alpha=0.7, lw=1.5)
        ax2.add_patch(r_hdr)
        ax2.add_patch(r_pay)
        ax2.text(x + 1.0, y + 0.75, len_text, color=TEXT_COLOR, ha='center', va='center', fontsize=8, fontweight='bold')
        ax2.text(x + 5.5, y + 0.75, payload_text, color=TEXT_COLOR, ha='center', va='center', fontsize=9, fontweight='bold')

    ax2.set_xlim(0, 10.0)
    ax2.set_ylim(0, 6.0)
    ax2.axis('off')

    # -------------------------------------------------------------
    # PANEL 3: Nagle Algoritması Gecikme Spikeları (40 ms)
    # -------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor(DARK_BG)
    ax3.set_title("3. Nagle Algoritması + Delayed ACK Gecikme Tuzağı", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)

    categories = ['Nagle Açık (TCP_NODELAY=0)\n[40 ms Kilitlenme]', 'TCP_NODELAY=1 (Taktik)\n[Anında İletim]']
    latencies = [40.8, 0.8]
    colors_nagle = [ACCENT_RED, ACCENT_GREEN]

    bars = ax3.bar(categories, latencies, color=colors_nagle, width=0.45, edgecolor='#FFFFFF')
    for bar in bars:
        yval = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2.0, yval + 1.0, f"{yval:.1f} ms", ha='center', va='bottom', color=TEXT_COLOR, fontweight='bold')

    ax3.set_ylabel("Paket İletim Gecikmesi (Milisaniye - ms)", color=TEXT_COLOR)
    ax3.set_ylim(0, 48)
    ax3.grid(True, linestyle=':', alpha=0.3, color='#475569')
    ax3.tick_params(colors=TEXT_COLOR)

    # -------------------------------------------------------------
    # PANEL 4: Kayan Pencere (Sliding Window) ve Akış Kontrolü
    # -------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor(DARK_BG)
    ax4.set_title("4. TCP Kayan Pencere (Sliding Window) ve Akış Kontrolü", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)

    steps = np.arange(1, 21)
    # Tampon doldukça Advertised Window azalır
    window_sizes = [64, 60, 55, 48, 40, 30, 20, 10, 5, 0, 0, 15, 30, 45, 55, 64, 64, 64, 64, 64]

    ax4.plot(steps, window_sizes, color=ACCENT_PURPLE, lw=2.5, marker='s', markersize=6, label="Advertised Window (KB)")
    ax4.axhline(0, color=ACCENT_RED, linestyle='--', label="Zero Window (Akış Durduruldu)")
    
    ax4.set_xlabel("İletim Aşaması (Transmission Steps)", color=TEXT_COLOR)
    ax4.set_ylabel("Bildirilen Pencere Boyutu (KB)", color=TEXT_COLOR)
    ax4.set_ylim(-5, 75)
    ax4.legend(loc='lower right', facecolor='#0F172A', edgecolor='#475569')
    ax4.grid(True, linestyle=':', alpha=0.3, color='#475569')
    ax4.tick_params(colors=TEXT_COLOR)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='#0F172A')
    plt.close()
    print(f"[Dashboard] Görselleştirme panosu başarıyla oluşturuldu: {output_path}")

def verify_all_assertions(png_path: str):
    print("")
    print("[*] GÜN 138 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. PNG Dosya Varlığı ve Boyutu (> 100 KB)
    assert os.path.exists(png_path), f"HATA: Dashboard PNG dosyası bulunamadı: {png_path}"
    png_size = os.path.getsize(png_path)
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
    assert png_size > 100_000, f"HATA: PNG boyutu 100 KB altında ({png_size} bayt)!"

    # 2. Length-Prefixed Kodlama Doğrulaması
    raw_frame = LengthPrefixedFramingCodec.encode_message(b"RADAR_COMMAND")
    assert len(raw_frame) == 4 + len(b"RADAR_COMMAND")
    len_field = struct.unpack("!I", raw_frame[:4])[0]
    assert len_field == len(b"RADAR_COMMAND")
    print("  [+] Uzunluk Ön-Ekli Çerçeve Kodlaması Doğrulandı.")

    # 3. Kısmi Okuma (Partial Read) ve Yapışma (Coalescing) Doğrulaması
    buf = StreamReceiverBuffer()
    f1 = LengthPrefixedFramingCodec.encode_message(b"MSG_ONE")
    f2 = LengthPrefixedFramingCodec.encode_message(b"MSG_TWO")
    combined = f1 + f2
    
    # 2 bayt ver (Eksik başlık)
    buf.feed_bytes(combined[:2])
    assert len(buf.extract_messages()) == 0
    
    # Kalan tümünü ver (Hem 1 hem 2 aynı anda ayrışmalı)
    buf.feed_bytes(combined[2:])
    res = buf.extract_messages()
    assert len(res) == 2
    assert res[0] == b"MSG_ONE" and res[1] == b"MSG_TWO"
    print("  [+] Kısmi Okuma ve Yapışma Ayrıştırma Mantığı Doğrulandı.")

    # 4. Nagle vs NODELAY Benchmark Doğrulaması
    assert rate_nodelay > rate_nagle * 20.0, "HATA: TCP_NODELAY en az 20x hızlı olmalıdır!"
    print(f"  [+] TCP_NODELAY Hızlanma Başarımı Doğrulandı ({rate_nodelay/rate_nagle:.1f}x).")

    print("")
    print("[PASS] Gün 138: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
    print("")

if __name__ == "__main__":
    _cur_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else "."
    _png_path = os.path.join(_cur_dir, "gun_138_tcp_byte_stream_modeli.png")
    generate_tcp_dashboard(_png_path)
    verify_all_assertions(_png_path)
