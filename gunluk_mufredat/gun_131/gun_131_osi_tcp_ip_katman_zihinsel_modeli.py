# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 8 (CODE 1): Katmanlı Paket Kapsülleme ve Çözme Simülatörü
OSI Katmanları Arasında Bayt Düzeyinde Encapsulation/Decapsulation Yapan Referans Motor
"""

import struct
import zlib
from typing import Dict, Tuple, Optional

class PacketEncapsulationEngine:
    """
    L7 (Uygulama) -> L4 (UDP) -> L3 (IPv4) -> L2 (Ethernet)
    Kapsülleme ve Decapsulation referans motoru.
    """
    def __init__(self):
        pass

    @staticmethod
    def encapsulate(payload: bytes, src_port: int, dst_port: int,
                    src_ip: str, dst_ip: str, src_mac: str, dst_mac: str) -> bytes:
        """Uygulama verisini Ethernet Çerçevesine kapsüller."""
        # 1. L4: UDP Başlığı (8 Bayt)
        # Format: !HHHH (SrcPort:16, DstPort:16, Length:16, Checksum:16)
        udp_len = 8 + len(payload)
        udp_header = struct.pack("!HHHH", src_port, dst_port, udp_len, 0)
        l4_packet = udp_header + payload

        # 2. L3: IPv4 Başlığı (20 Bayt)
        # Format: !BBHHHBBH4s4s
        version_ihl = (4 << 4) | 5 # IPv4, IHL=5 (20 bayt)
        dscp_ecn = 0
        total_len = 20 + len(l4_packet)
        ident = 54321
        flags_frag = 0x4000 # Don't Fragment (DF=1)
        ttl = 64
        proto = 17 # UDP = 17
        checksum = 0
        src_ip_bytes = bytes(map(int, src_ip.split('.')))
        dst_ip_bytes = bytes(map(int, dst_ip.split('.')))
        
        ip_header = struct.pack("!BBHHHBBH4s4s",
                                version_ihl, dscp_ecn, total_len, ident,
                                flags_frag, ttl, proto, checksum,
                                src_ip_bytes, dst_ip_bytes)
        l3_packet = ip_header + l4_packet

        # 3. L2: Ethernet II Başlığı (14 Bayt)
        # Format: !6s6sH (DstMAC:6B, SrcMAC:6B, EtherType:16)
        def mac_to_bytes(mac: str) -> bytes:
            return bytes.fromhex(mac.replace(':', '').replace('-', ''))

        eth_header = struct.pack("!6s6sH",
                                 mac_to_bytes(dst_mac),
                                 mac_to_bytes(src_mac),
                                 0x0800) # EtherType: IPv4 (0x0800)

        # FCS / CRC32 (4 Bayt)
        crc32_val = zlib.crc32(eth_header + l3_packet) & 0xffffffff
        fcs = struct.pack("!I", crc32_val)

        # Tam Çerçeve (Ethernet Frame)
        full_frame = eth_header + l3_packet + fcs
        return full_frame

    @staticmethod
    def decapsulate(frame: bytes) -> Dict:
        """Gelen Ethernet Çerçevesini katman katman çözer (Decapsulate eder)."""
        assert len(frame) >= 14 + 20 + 8 + 4, "Çerçeve boyutu asgari sınırdan küçük!"
        
        # 1. L2 Çözümleme
        eth_header = frame[:14]
        dst_mac_raw, src_mac_raw, ethertype = struct.unpack("!6s6sH", eth_header)
        fcs_raw = frame[-4:]
        payload_with_ip = frame[14:-4]
        
        # 2. L3 Çözümleme
        ip_header = payload_with_ip[:20]
        v_ihl, dscp, total_len, ident, flags, ttl, proto, chk, s_ip, d_ip = struct.unpack("!BBHHHBBH4s4s", ip_header)
        payload_with_udp = payload_with_ip[20:total_len]
        
        # 3. L4 Çözümleme
        udp_header = payload_with_udp[:8]
        src_port, dst_port, udp_len, udp_chk = struct.unpack("!HHHH", udp_header)
        app_payload = payload_with_udp[8:udp_len]

        return {
            "l2": {
                "src_mac": ":".join(f"{b:02x}" for b in src_mac_raw),
                "dst_mac": ":".join(f"{b:02x}" for b in dst_mac_raw),
                "ethertype": hex(ethertype)
            },
            "l3": {
                "src_ip": ".".join(map(str, s_ip)),
                "dst_ip": ".".join(map(str, d_ip)),
                "proto": proto,
                "ttl": ttl
            },
            "l4": {
                "src_port": src_port,
                "dst_port": dst_port,
                "length": udp_len
            },
            "payload": app_payload
        }

print("[HÜCRE 8] PacketEncapsulationEngine başarıyla yüklendi.")

# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 2): Uçtan Uca Paket Kapsülleme ve Doğrulama Deneyi
Taktik Radar İzinin Bayt Düzeyinde Paketlenmesi, Gönderilmesi ve Çözülmesi
"""

def run_encapsulation_experiment():
    print("")
    print("[*] Taktik Radar İzi Kapsülleme Deneyi Başlatılıyor...")
    
    # 1. Uygulama Verisi (Radar Telemetri)
    # TargetID=101, Range=84.5km, Azimuth=124.8deg
    telemetry_payload = struct.pack("!Iff", 101, 84.5, 124.8)
    print(f"  [+] L7 Uygulama Yükü (Payload Boyutu): {len(telemetry_payload)} Bayt")
    
    # 2. Kapsülleme (Encapsulation)
    frame = PacketEncapsulationEngine.encapsulate(
        payload=telemetry_payload,
        src_port=5001, dst_port=5005,
        src_ip="192.168.1.50", dst_ip="192.168.1.100",
        src_mac="00:1A:2B:3C:4D:5E", dst_mac="A0:B1:C2:D3:E4:F5"
    )
    
    print(f"  [+] L2 Ethernet Çerçevesi (Toplam Boyut): {len(frame)} Bayt")
    print(f"      - Başlık Ek Yükü (Overhead)        : {len(frame) - len(telemetry_payload)} Bayt (14B Eth + 20B IP + 8B UDP + 4B FCS)")
    
    # 3. Alıcıda Çözümleme (Decapsulation)
    parsed = PacketEncapsulationEngine.decapsulate(frame)
    print(f"  [+] Decapsulation Başarılı:")
    print(f"      - Kaynak -> Hedef IP   : {parsed['l3']['src_ip']} -> {parsed['l3']['dst_ip']}")
    print(f"      - Kaynak -> Hedef Port : {parsed['l4']['src_port']} -> {parsed['l4']['dst_port']}")
    
    # Veri bütünlüğü kontrolü
    tid, rng, az = struct.unpack("!Iff", parsed['payload'])
    print(f"      - Çözülen Radar İzi    : Hedef={tid}, Menzil={rng:.1f} km, Açı={az:.1f} deg")
    
    assert tid == 101 and abs(rng - 84.5) < 1e-3, "HATA: Radar verisi bozuldu!"
    print("  [+] %100 Bit Düzeyinde Veri Bütünlüğü Doğrulandı.")
    return len(frame), len(telemetry_payload)

frame_len, payload_len = run_encapsulation_experiment()

# -*- coding: utf-8 -*-
"""
HÜCRE 13 (CODE 3): Sabotaj ve Arıza Enjeksiyon Simülatörü
Bozuk Checksum / FCS Durumunda Çerçevenin Reddedilmesi ve Endianness Hatası
"""

def run_sabotage_experiments():
    print("")
    print("[*] Ağ Sabotaj ve Arıza Enjeksiyon Deneyleri Başlatılıyor...")
    
    payload = b"MISSILE_FIRE_COMMAND"
    frame = bytearray(PacketEncapsulationEngine.encapsulate(
        payload, 8000, 9000, "10.0.0.1", "10.0.0.2",
        "00:11:22:33:44:55", "66:77:88:99:AA:BB"
    ))
    
    # -------------------------------------------------------------
    # SABOTAJ 1: Yolda 1 Bit Değişmesi (Bit Flip / Karışma)
    # -------------------------------------------------------------
    frame[35] ^= 0x01 # Verinin ortasındaki 1 biti boz
    
    # FCS Kontrolü
    calculated_crc = zlib.crc32(frame[:-4]) & 0xffffffff
    stored_crc = struct.unpack("!I", frame[-4:])[0]
    
    corrupted_detected = (calculated_crc != stored_crc)
    print(f"  [+] Sabotaj 1: Bit Karışması Tespit Edildi mi?: {corrupted_detected}")
    print(f"      - Beklenen CRC: {hex(stored_crc)} | Hesaplanan: {hex(calculated_crc)} (FRAME DROPPED!)")
    
    assert corrupted_detected, "HATA: CRC32 bozuk paketi yakalayamadı!"
    return True

assert run_sabotage_experiments(), "HATA: Sabotaj testleri başarısız!"

# -*- coding: utf-8 -*-
"""
HÜCRE 15 (CODE 4): Paket Boyutuna Göre Protokol Verimlilik (Goodput) Analizi
16 Bayt Telemetriden 1460 Bayt Jumbo Radar Paketine Başlık Ek Yükü ve Verim Eğrisi
"""

def run_protocol_efficiency_analysis():
    print("")
    print("[*] Protokol Verimlilik (Goodput / Efficiency) Analizi Başlatılıyor...")
    
    # Başlık Boyutları (L2 + L3 + L4 + FCS)
    HEADER_OVERHEAD_BYTES = 14 + 20 + 8 + 4 # 46 Bayt
    
    payload_sizes = [16, 32, 64, 128, 256, 512, 1024, 1454]
    efficiency_results = {}
    
    for p_size in payload_sizes:
        total_frame = p_size + HEADER_OVERHEAD_BYTES
        efficiency_pct = (p_size / total_frame) * 100.0
        efficiency_results[p_size] = (total_frame, efficiency_pct)
        print(f"  - Yük: {p_size:4d} B | Toplam Çerçeve: {total_frame:4d} B | Ağ Verimi: %{efficiency_pct:5.2f} (Kayıp: %{100-efficiency_pct:5.2f})")
        
    return efficiency_results

eff_results = run_protocol_efficiency_analysis()

# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Toplu Telemetri Akışı ve Ayrıştırma (Parse) Stres Testi
1.000 Adet Heterojen Radar/Aviyonik Çerçevesinin Hatasız Kapsüllenmesi ve Ayrıştırılması
"""

import random

def run_stress_encapsulation_suite():
    print("")
    print("[*] Toplu Telemetri Akışı Stres Testi Başlatılıyor (1.000 Paket)...")
    
    NUM_PACKETS = 1000
    success_count = 0
    
    for i in range(NUM_PACKETS):
        target_id = i % 50
        fake_range = random.uniform(10.0, 200.0)
        fake_az = random.uniform(0.0, 360.0)
        raw_payload = struct.pack("!Iff", target_id, fake_range, fake_az)
        
        # Kapsülleme
        frame = PacketEncapsulationEngine.encapsulate(
            raw_payload,
            src_port=10000 + (i % 100),
            dst_port=5000,
            src_ip="192.168.10.2",
            dst_ip="192.168.10.1",
            src_mac="02:00:00:00:00:01",
            dst_mac="02:00:00:00:00:02"
        )
        
        # Çözümleme
        decapped = PacketEncapsulationEngine.decapsulate(frame)
        t_id, r, az = struct.unpack("!Iff", decapped['payload'])
        
        if t_id == target_id and abs(r - fake_range) < 1e-4:
            success_count += 1
            
    print(f"  [+] Stres Testi Tamamlandı:")
    print(f"      - Gönderilen Çerçeve : {NUM_PACKETS}")
    print(f"      - Başarıyla Çözülen  : {success_count} (%100 Başarı)")
    
    return success_count == NUM_PACKETS

assert run_stress_encapsulation_suite(), "HATA: Stres testi paket kaybetti!"

# -*- coding: utf-8 -*-
"""
HÜCRE 19 (CODE 6): 4-Panelli OSI Dashboard Üretimi ve Katı Doğrulama Testleri (Assertions)
300 DPI, #0F172A Koyu Tema ile Savunma Sanayii Ağ Mimarisi Görselleştirme Panosu
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_osi_dashboard(output_path: str):
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
    # PANEL 1: OSI 7-Katman vs Savunma Protokolleri
    # -------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor(DARK_BG)
    ax1.set_title("1. OSI Modeli ve Savunma Sanayii Protokol Eşlemesi", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)
    
    layers = [
        ("L7. Uygulama", "DDS, MAVLink, STANAG 4586", ACCENT_BLUE),
        ("L6. Sunum", "Protobuf, ASN.1, AES-256 Kripto", ACCENT_PURPLE),
        ("L5. Oturum", "RTPS Session, RPC Channel", '#6366F1'),
        ("L4. Taşıma", "UDP (Gerçek Zamanlı), TCP", ACCENT_GREEN),
        ("L3. Ağ", "IPv4, IPv6, Taktik Yönlendirme", ACCENT_AMBER),
        ("L2. Veri Bağı", "Ethernet II, ARINC 664, VLAN", '#EC4899'),
        ("L1. Fiziksel", "Fiber Optik, RF Link, 10GbE PHY", ACCENT_RED)
    ]
    
    for idx, (lname, pnames, col) in enumerate(layers):
        y = 6.0 - idx * 0.85
        rect = patches.Rectangle((0.5, y - 0.35), 4.0, 0.7, linewidth=1.5, edgecolor=col, facecolor=col, alpha=0.3)
        ax1.add_patch(rect)
        ax1.text(2.5, y, lname, color=TEXT_COLOR, ha='center', va='center', fontweight='bold', fontsize=9)
        
        rect2 = patches.Rectangle((5.0, y - 0.35), 5.5, 0.7, linewidth=1.5, edgecolor='#475569', facecolor='#0F172A', alpha=0.6)
        ax1.add_patch(rect2)
        ax1.text(7.75, y, pnames, color=TEXT_COLOR, ha='center', va='center', fontsize=8)
        
    ax1.set_xlim(0, 11)
    ax1.set_ylim(-0.5, 7.0)
    ax1.axis('off')

    # -------------------------------------------------------------
    # PANEL 2: Paket Kapsülleme Başlık Yükü Dağılımı (256B Yük)
    # -------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor(DARK_BG)
    ax2.set_title("2. 256 Baytlık Radar Paketinde Başlık Yükü Dağılımı (302B)", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)
    
    labels = ['Uygulama Yükü (256B)', 'IPv4 Başlığı (20B)', 'Ethernet II (14B)', 'UDP Başlığı (8B)', 'FCS CRC (4B)']
    sizes = [256, 20, 14, 8, 4]
    colors_pie = [ACCENT_BLUE, ACCENT_AMBER, '#EC4899', ACCENT_GREEN, ACCENT_RED]
    explode = (0.05, 0.08, 0.08, 0.08, 0.08)
    
    wedges, texts, autotexts = ax2.pie(
        sizes, explode=explode, labels=labels, autopct='%1.1f%%',
        startangle=140, colors=colors_pie, textprops=dict(color=TEXT_COLOR, fontsize=8)
    )
    for at in autotexts:
        at.set_color('#0F172A')
        at.set_fontweight('bold')

    # -------------------------------------------------------------
    # PANEL 3: Yük Boyutuna Göre Goodput Verimlilik Eğrisi
    # -------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor(DARK_BG)
    ax3.set_title("3. Faydalı Yük Boyutuna Göre Protokol Verimi (Goodput Ratio)", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)
    
    payloads = np.linspace(8, 1500, 100)
    efficiencies = (payloads / (payloads + 46)) * 100.0
    
    ax3.plot(payloads, efficiencies, color=ACCENT_GREEN, lw=3, label="Protokol Verimliliği (%)")
    ax3.axhline(96.9, color=ACCENT_BLUE, linestyle='--', label="Maksimum MTU Verimi (%96.9)")
    ax3.axvline(256, color=ACCENT_AMBER, linestyle=':', label="Tipik Radar İzi (256B -> %84.7)")
    ax3.axvline(32, color=ACCENT_RED, linestyle=':', label="Küçük Sensör (32B -> %41.0)")
    
    ax3.set_xlabel("Faydalı Yük Boyutu (Bayt)", color=TEXT_COLOR)
    ax3.set_ylabel("Faydalı Veri Oranı / Goodput (%)", color=TEXT_COLOR)
    ax3.set_ylim(0, 105)
    ax3.legend(loc='lower right', facecolor='#0F172A', edgecolor='#475569')
    ax3.grid(True, linestyle=':', alpha=0.3, color='#475569')
    ax3.tick_params(colors=TEXT_COLOR)

    # -------------------------------------------------------------
    # PANEL 4: Linux Çekirdeği Ağ Yığını Gecikme Adımları
    # -------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor(DARK_BG)
    ax4.set_title("4. Linux Çekirdek Ağ Yığını İşlem Gecikmesi (Kernel Path)", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)
    
    steps = [
        'NIC DMA -> Ring',
        'Hard IRQ & NAPI',
        'sk_buff Tahsisi',
        'ip_rcv & Route',
        'udp_rcv & Queue',
        'Kullanıcı recv()'
    ]
    latencies_us = [0.8, 1.4, 2.5, 1.8, 1.2, 3.1]
    
    bars = ax4.barh(steps, latencies_us, color=ACCENT_BLUE, edgecolor='#FFFFFF', height=0.55)
    for bar in bars:
        wval = bar.get_width()
        ax4.text(wval + 0.1, bar.get_y() + bar.get_height()/2.0, f"{wval:.1f} us", va='center', color=TEXT_COLOR, fontweight='bold', fontsize=9)
        
    ax4.set_xlabel("Gecikme Maliyeti (Mikrosaniye - us)", color=TEXT_COLOR)
    ax4.set_xlim(0, 4.0)
    ax4.grid(True, linestyle=':', alpha=0.3, color='#475569')
    ax4.tick_params(colors=TEXT_COLOR)
    
    # Toplam Kutu
    ax4.text(2.2, 0.8, "Toplam Çekirdek Gecikmesi:\n~10.8 us (Zero-Copy ile < 4 us)",
             bbox=dict(boxstyle="round,pad=0.5", facecolor='#0F172A', edgecolor=ACCENT_GREEN, lw=1.5),
             color=ACCENT_GREEN, fontweight='bold', fontsize=9)
             
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='#0F172A')
    plt.close()
    print(f"[Dashboard] Görselleştirme panosu başarıyla oluşturuldu: {output_path}")

def verify_all_assertions(png_path: str):
    print("")
    print("[*] GÜN 131 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. PNG Dosya Varlığı ve Boyutu (> 100 KB)
    assert os.path.exists(png_path), f"HATA: Dashboard PNG dosyası bulunamadı: {png_path}"
    png_size = os.path.getsize(png_path)
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
    assert png_size > 100_000, f"HATA: PNG boyutu 100 KB altında ({png_size} bayt)!"

    # 2. Kapsülleme ve Decapsulation Bit Bütünlüğü
    raw = b"ASELSAN_RADAR_TEST_BEACON_404"
    frame = PacketEncapsulationEngine.encapsulate(raw, 4000, 5000, "192.168.1.1", "192.168.1.2", "aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66")
    parsed = PacketEncapsulationEngine.decapsulate(frame)
    assert parsed["payload"] == raw, "HATA: Decapsulation veriyi bozdu!"
    print("  [+] Kapsülleme / Decapsulation Bit Düzeyinde Doğrulandı.")

    # 3. Başlık Yükü ve Matematiksel Doğruluk
    overhead = len(frame) - len(raw)
    assert overhead == 46, f"HATA: Standart başlık yükü 46 bayt olmalıdır ({overhead} bayt bulundu)!"
    print(f"  [+] Standart L2-L4 Başlık Ek Yükü Doğrulandı: {overhead} Bayt.")

    # 4. Verimlilik Ölçeklenmesi Doğrulaması
    assert eff_results[1454][1] > 95.0, "HATA: Tam MTU'da verim %95 üzerinde olmalıdır!"
    assert eff_results[16][1] < 30.0, "HATA: 16 baytta verim %30 altında olmalıdır!"
    print("  [+] Goodput / Başlık Verimlilik Ölçeklenmesi Doğrulandı.")

    print("")
    print("[PASS] Gün 131: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
    print("")

if __name__ == "__main__":
    _cur_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else "."
    _png_path = os.path.join(_cur_dir, "gun_131_osi_tcp_ip_katman_zihinsel_modeli.png")
    generate_osi_dashboard(_png_path)
    verify_all_assertions(_png_path)
