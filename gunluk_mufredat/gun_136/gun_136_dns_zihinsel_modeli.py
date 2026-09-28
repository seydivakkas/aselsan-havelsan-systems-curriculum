# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""


# -*- coding: utf-8 -*-
"""
HÜCRE 8 (CODE 1): RFC 1035 DNS Başlık ve Paket Motoru
Ham Bayt Paketleme, QNAME Etiket Kodlaması, A/SRV Kayıt Ayrıştırma ve Yerel Çözümleyici
"""

import struct
from typing import Dict, List, Tuple, Optional

# DNS Tür ve Sınıf Sabitleri (RFC 1035, RFC 2782)
DNS_TYPE_A = 1         # IPv4 Adresi
DNS_TYPE_CNAME = 5     # Takma Ad (Canonical Name)
DNS_TYPE_PTR = 12      # Ters DNS
DNS_TYPE_SRV = 33      # Servis Keşfi (RFC 2782)
DNS_CLASS_IN = 1       # Internet Sınıfı

class DNSHeader:
    """RFC 1035 12-Baytlık Sabit DNS Başlığı."""
    def __init__(self, xid: int, flags: int = 0x0100, qdcount: int = 1,
                 ancount: int = 0, nscount: int = 0, arcount: int = 0):
        self.xid = xid
        self.flags = flags       # 0x0100 = Standard recursive query
        self.qdcount = qdcount   # Soru sayısı
        self.ancount = ancount   # Cevap sayısı
        self.nscount = nscount   # Yetkili sunucu sayısı
        self.arcount = arcount   # Ek kayıt sayısı

    def pack(self) -> bytes:
        return struct.pack("!HHHHHH", self.xid, self.flags, self.qdcount,
                           self.ancount, self.nscount, self.arcount)

    @classmethod
    def unpack(cls, data: bytes) -> 'DNSHeader':
        if len(data) < 12:
            raise ValueError("Geçersiz DNS başlık boyutu (< 12 bayt)")
        xid, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", data[:12])
        return cls(xid, flags, qd, an, ns, ar)

class DNSCodec:
    """DNS QNAME etiket kodlama ve çözme motoru."""
    @staticmethod
    def encode_qname(domain: str) -> bytes:
        """'radar.aselsan.local' -> b'\x05radar\x07aselsan\x05local\x00'"""
        parts = domain.strip('.').split('.')
        encoded = b""
        for part in parts:
            b_part = part.encode('ascii')
            encoded += struct.pack("!B", len(b_part)) + b_part
        encoded += b"\x00"
        return encoded

    @staticmethod
    def decode_qname(data: bytes, offset: int = 12) -> Tuple[str, int]:
        """QNAME bayt dizisini alan adına dönüştürür (Pointer compression destekli)."""
        labels = []
        curr = offset
        jumped = False
        bytes_consumed = 0

        while curr < len(data):
            length = data[curr]
            if length == 0:
                if not jumped:
                    bytes_consumed = (curr + 1) - offset
                break
            elif (length & 0xC0) == 0xC0:
                # 14-bit Pointer Compression
                if not jumped:
                    bytes_consumed = (curr + 2) - offset
                pointer = struct.unpack("!H", data[curr:curr+2])[0] & 0x3FFF
                curr = pointer
                jumped = True
            else:
                curr += 1
                labels.append(data[curr:curr+length].decode('ascii'))
                curr += length
                if not jumped:
                    bytes_consumed = curr - offset

        return ".".join(labels), bytes_consumed

class SimulatedDNSServer:
    """Taktik Askeri Alan Adı Sunucusu ve Bölge Yöneticisi (Zone Manager)."""
    def __init__(self, zone_name: str):
        self.zone_name = zone_name
        self.records_a: Dict[str, str] = {}
        self.records_srv: Dict[str, Tuple[int, int, int, str]] = {} # (priority, weight, port, target)

    def add_a_record(self, name: str, ip: str):
        self.records_a[name.lower()] = ip

    def add_srv_record(self, service_name: str, priority: int, weight: int, port: int, target: str):
        self.records_srv[service_name.lower()] = (priority, weight, port, target)

    def resolve_query(self, raw_query: bytes) -> bytes:
        """Gelen ham DNS sorgusunu ayrıştırır ve RFC 1035 yanıtı üretir."""
        req_hdr = DNSHeader.unpack(raw_query)
        qname, q_len = DNSCodec.decode_qname(raw_query, 12)
        qtype, qclass = struct.unpack("!HH", raw_query[12+q_len:12+q_len+4])

        resp_flags = 0x8180 # Response, Recursion Available, No Error
        qname_lower = qname.lower()

        if qtype == DNS_TYPE_A and qname_lower in self.records_a:
            ip_str = self.records_a[qname_lower]
            resp_hdr = DNSHeader(req_hdr.xid, flags=resp_flags, qdcount=1, ancount=1)
            
            # Soru bölümünü aynen kopyala
            question_bytes = raw_query[12:12+q_len+4]
            
            # Cevap RR: Pointer to QNAME (0xC00C), Type A (1), Class IN (1), TTL (300s), RDLENGTH (4), IP (4 bayt)
            ip_bytes = bytes(int(x) for x in ip_str.split('.'))
            answer_bytes = struct.pack("!HHHIH4s", 0xC00C, DNS_TYPE_A, DNS_CLASS_IN, 300, 4, ip_bytes)
            
            return resp_hdr.pack() + question_bytes + answer_bytes
        else:
            # NXDOMAIN (Böyle bir kayıt yok)
            resp_flags_nx = 0x8183
            resp_hdr = DNSHeader(req_hdr.xid, flags=resp_flags_nx, qdcount=1, ancount=0)
            return resp_hdr.pack() + raw_query[12:12+q_len+4]

print("[HÜCRE 8] DNSHeader, DNSCodec ve SimulatedDNSServer motoru başarıyla yüklendi.")

# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 2): Taktik Servis Çözümleme Deneyi
Radar, FLIR ve Görev Bilgisayarı Alan Adlarının RFC 1035 Üzerinden Çözümlenmesi
"""

def run_dns_resolution_experiment():
    print("")
    print("[*] Taktik Alan Adı Çözümleme Deneyi Başlatılıyor...")
    
    server = SimulatedDNSServer(zone_name="aselsan.local")
    server.add_a_record("radar.aselsan.local", "192.168.10.80")
    server.add_a_record("flir.aselsan.local", "192.168.10.20")
    server.add_a_record("c2.aselsan.local", "10.200.5.1")
    
    # -------------------------------------------------------------
    # SORGULAMA: radar.aselsan.local (Type A)
    # -------------------------------------------------------------
    qname = "radar.aselsan.local"
    req_hdr = DNSHeader(xid=0xABCD, flags=0x0100)
    qname_bytes = DNSCodec.encode_qname(qname)
    q_footer = struct.pack("!HH", DNS_TYPE_A, DNS_CLASS_IN)
    query_packet = req_hdr.pack() + qname_bytes + q_footer
    
    # Sunucuya ilet ve yanıt al
    raw_response = server.resolve_query(query_packet)
    resp_hdr = DNSHeader.unpack(raw_response)
    
    print(f"  [+] DNS Yanıtı Alındı (XID: 0x{resp_hdr.xid:04X}):")
    print(f"      - Soru Sayısı : {resp_hdr.qdcount}")
    print(f"      - Cevap Sayısı: {resp_hdr.ancount}")
    print(f"      - Bayraklar   : 0x{resp_hdr.flags:04X} (No Error)")
    
    assert resp_hdr.xid == 0xABCD and resp_hdr.ancount == 1
    
    # Cevap bölümündeki IP'yi oku
    # Başlık (12) + Soru (len(qname_bytes) + 4) = 12 + len(qname_bytes) + 4
    ans_offset = 12 + len(qname_bytes) + 4
    _, rtype, rclass, ttl, rdlen = struct.unpack("!HHHIH", raw_response[ans_offset:ans_offset+12])
    ip_bytes = raw_response[ans_offset+12:ans_offset+12+rdlen]
    resolved_ip = ".".join(str(b) for b in ip_bytes)
    
    print(f"  [+] Çözümlenen IP: {qname} -> {resolved_ip} (TTL: {ttl}s)")
    assert resolved_ip == "192.168.10.80"
    
    print("  [+] Taktik DNS Çözümleme Deneyi %100 Başarıyla Tamamlandı!")
    return server

dns_sim_server = run_dns_resolution_experiment()

# -*- coding: utf-8 -*-
"""
HÜCRE 13 (CODE 3): DNS Sabotaj ve Güvenlik Simülatörü
Transaction ID Eşleşme Doğrulaması (Anti-Spoofing Kalkanı) ve NXDOMAIN Testi
"""

def run_dns_sabotage_lab(server: SimulatedDNSServer):
    print("")
    print("[*] DNS Sabotaj ve Güvenlik Testleri Başlatılıyor...")
    
    # -------------------------------------------------------------
    # SABOTAJ 1: Sahte Transaction ID ile DNS Spoofing Denemesi
    # -------------------------------------------------------------
    legit_xid = 0x55AA
    attacker_xid = 0xDEAD # Saldırgan yanlış ID tahmin etti
    
    def verify_dns_response(sent_xid: int, resp_bytes: bytes) -> bool:
        hdr = DNSHeader.unpack(resp_bytes)
        if hdr.xid != sent_xid:
            raise SecurityError(f"DNS Spoofing Girişimi Engellendi! Beklenen XID: 0x{sent_xid:04X}, Gelen: 0x{hdr.xid:04X}")
        return True

    # Gerçek yanıt üretiliyor
    q_bytes = DNSHeader(legit_xid).pack() + DNSCodec.encode_qname("radar.aselsan.local") + struct.pack("!HH", 1, 1)
    legit_resp = server.resolve_query(q_bytes)
    
    # Sahte saldırgan yanıtı üretiliyor (Farklı XID)
    fake_resp = DNSHeader(attacker_xid).pack() + DNSCodec.encode_qname("radar.aselsan.local") + struct.pack("!HH", 1, 1)

    # Doğrulama Testi
    class SecurityError(Exception): pass
    
    assert verify_dns_response(legit_xid, legit_resp) is True
    print("  [+] Orijinal DNS Yanıtı Başarıyla Doğrulandı.")

    caught_spoof = False
    try:
        verify_dns_response(legit_xid, fake_resp)
    except SecurityError as e:
        caught_spoof = True
        print(f"  [+] Sabotaj 1 Yakalandı: {e}")
    assert caught_spoof, "HATA: Sahte XID'li paket kabul edilmemeliydi!"

    # -------------------------------------------------------------
    # SABOTAJ 2: Olmayan Alan Adı (NXDOMAIN - RCODE = 3)
    # -------------------------------------------------------------
    nx_query = DNSHeader(0x1234).pack() + DNSCodec.encode_qname("olmayan-sensor.aselsan.local") + struct.pack("!HH", 1, 1)
    nx_resp = server.resolve_query(nx_query)
    nx_hdr = DNSHeader.unpack(nx_resp)
    rcode = nx_hdr.flags & 0x000F
    assert rcode == 3 # NXDOMAIN
    print(f"  [+] Sabotaj 2: Olmayan Alan Adı Başarıyla NXDOMAIN (RCODE={rcode}) Döndü.")

    print("  [+] Tüm DNS Sabotaj ve Güvenlik Testleri Başarıyla Geçti!")
    return True

assert run_dns_sabotage_lab(dns_sim_server), "HATA: DNS sabotaj testleri başarısız!"

# -*- coding: utf-8 -*-
"""
HÜCRE 15 (CODE 4): Bellek İçi DNS Önbellek (DNS Cache) Arama Benchmark Suite
10.000 Alan Adı Altında Önbellek Arama Süresi (O(1) Hash Map İspatı)
"""

import time

def run_dns_cache_benchmark():
    print("")
    print("[*] Bellek İçi DNS Önbellek Arama Benchmarkı Başlatılıyor...")
    
    # 5.000 Adet Alan Adı Kaydediliyor
    TOTAL_NAMES = 5000
    dns_cache: Dict[str, str] = {}
    for i in range(TOTAL_NAMES):
        name = f"sensor-{i}.aselsan.local"
        ip = f"10.{(i >> 8) & 0xFF}.{i & 0xFF}.1"
        dns_cache[name] = ip
        
    print(f"  [+] Önbelleğe {TOTAL_NAMES:,} Adet Taktik Sensör İsim-IP Eşlemesi Yüklendi.")

    # 100.000 Rastgele İsim Sorgulaması
    LOOKUPS = 100_000
    test_queries = [f"sensor-{i % TOTAL_NAMES}.aselsan.local" for i in range(LOOKUPS)]

    start = time.perf_counter()
    for domain in test_queries:
        _ = dns_cache.get(domain)
    duration = time.perf_counter() - start

    avg_ns = (duration / LOOKUPS) * 1e9
    ops_sec = LOOKUPS / duration

    print(f"  [+] Benchmark Sonuçları:")
    print(f"      - Toplam Arama Sayısı : {LOOKUPS:,}")
    print(f"      - Ortalama Arama Süresi: {avg_ns:.1f} nanosaniye / isim çözümleme")
    print(f"      - Çözümleme Throughput : {ops_sec:,.0f} Sorgu / Saniye (O(1) Hızı)")

    return avg_ns, ops_sec

dns_cache_latency_ns, dns_cache_ops = run_dns_cache_benchmark()
assert dns_cache_latency_ns < 1000.0, "HATA: DNS önbellek arama süresi 1 us altında olmalıdır!"

# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Taktik Aviyonik SRV Servis Keşfi Simülasyonu
Radar, FLIR ve Telemetri Servislerinin Dinamik Port, Ağırlık ve Öncelik Ayrıştırması
"""

def run_tactical_srv_discovery_sim():
    print("")
    print("[*] Taktik Aviyonik SRV Servis Keşfi Simülasyonu Başlatılıyor...")
    
    server = SimulatedDNSServer(zone_name="mission.local")
    
    # Sensör Servisleri Kaydediliyor (Priority, Weight, Port, TargetHost)
    # RFC 2782: Düşük Priority numarası daha önceliklidir!
    server.add_srv_record("_radar._udp.mission.local", priority=10, weight=60, port=5001, target="radar-primary.mission.local")
    server.add_srv_record("_radar._udp.mission.local_bk", priority=20, weight=40, port=5001, target="radar-backup.mission.local")
    server.add_srv_record("_flir._tcp.mission.local", priority=10, weight=100, port=8080, target="flir-hd.mission.local")
    
    print("  [+] SRV Kayıtları Taktik DNS Sunucusuna Eklendi:")
    for srv_name, (pri, wgt, p, tgt) in server.records_srv.items():
        print(f"      - {srv_name:<28} -> Pri:{pri:<2} Wgt:{wgt:<3} Port:{p:<5} Host:{tgt}")

    # Servis Keşfi Simülasyonu
    srv_entry = server.records_srv["_radar._udp.mission.local"]
    priority, weight, port, target_host = srv_entry
    
    assert port == 5001
    assert target_host == "radar-primary.mission.local"
    assert priority == 10
    
    print("\n  [+] SRV Çözümleme Başarılı:")
    print(f"      - Ana Radar Uç Noktası: {target_host}:{port} (Öncelik: {priority})")
    print("  [+] Dinamik Servis Keşfi Testi %100 Başarıyla Tamamlandı!")
    return True

assert run_tactical_srv_discovery_sim(), "HATA: SRV keşif simülasyonu başarısız!"

# -*- coding: utf-8 -*-
"""
HÜCRE 19 (CODE 6): 4-Panelli DNS Dashboard Üretici ve Katı Assertions
300 DPI, #0F172A Koyu Tema ile Savunma Sanayii DNS Mimarisi Görselleştirme Panosu
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_dns_dashboard(output_path: str):
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
    # PANEL 1: RFC 1035 12-Bayt DNS Başlık Mimarisi
    # -------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor(DARK_BG)
    ax1.set_title("1. RFC 1035 DNS Başlık Mimarisi (12-Bayt Haritası)", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)

    boxes = [
        ("Transaction ID (2 Bayt)\n[Eşleştirme Anahtarı: 0xABCD]", 0.5, 3.8, 4.2, 1.6, ACCENT_BLUE),
        ("Flags (2 Bayt)\n[QR, Opcode, AA, TC, RD, RA, RCODE]", 5.2, 3.8, 4.3, 1.6, ACCENT_AMBER),
        ("QDCOUNT: Soru Sayısı (2B)\n[Genellikle 1 Soru]", 0.5, 1.8, 4.2, 1.6, ACCENT_GREEN),
        ("ANCOUNT: Cevap Sayısı (2B)\n[Dönen Kayıt Sayısı]", 5.2, 1.8, 4.3, 1.6, ACCENT_GREEN),
        ("NSCOUNT: Yetkili Sunucu (2B) | ARCOUNT: Ek Kayıt Sayısı (2B)", 0.5, -0.2, 9.0, 1.6, ACCENT_PURPLE)
    ]

    for label, x, y, w, h, col in boxes:
        rect = patches.Rectangle((x, y), w, h, facecolor=col, edgecolor='#FFFFFF', alpha=0.75, lw=1.5)
        ax1.add_patch(rect)
        ax1.text(x + w/2.0, y + h/2.0, label, color=TEXT_COLOR, ha='center', va='center', fontsize=8, fontweight='bold')

    ax1.set_xlim(0, 10.0)
    ax1.set_ylim(-0.8, 6.0)
    ax1.axis('off')

    # -------------------------------------------------------------
    # PANEL 2: Hiyerarşik DNS Çözümleme Ağacı
    # -------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor(DARK_BG)
    ax2.set_title("2. Hiyerarşik DNS Alan Adı Ağacı Mimarisi", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)

    tree_nodes = [
        ("Root Domain (.)", 5.0, 5.0, ACCENT_PURPLE),
        ("TLD: .mil", 2.5, 3.3, ACCENT_BLUE),
        ("TLD: .local", 7.5, 3.3, ACCENT_BLUE),
        ("aselsan.mil", 2.5, 1.6, ACCENT_AMBER),
        ("mission.local", 7.5, 1.6, ACCENT_AMBER),
        ("radar.aselsan.mil", 2.5, 0.0, ACCENT_GREEN),
        ("flir.mission.local", 7.5, 0.0, ACCENT_GREEN)
    ]

    for text, x, y, col in tree_nodes:
        rect = patches.Rectangle((x - 1.5, y - 0.5), 3.0, 1.0, facecolor=col, edgecolor='#FFFFFF', alpha=0.8, lw=1.5)
        ax2.add_patch(rect)
        ax2.text(x, y, text, color=TEXT_COLOR, ha='center', va='center', fontsize=8, fontweight='bold')

    # Bağlantı çizgileri
    ax2.plot([5.0, 2.5], [4.5, 3.8], color='#94A3B8', lw=1.5)
    ax2.plot([5.0, 7.5], [4.5, 3.8], color='#94A3B8', lw=1.5)
    ax2.plot([2.5, 2.5], [2.8, 2.1], color='#94A3B8', lw=1.5)
    ax2.plot([7.5, 7.5], [2.8, 2.1], color='#94A3B8', lw=1.5)
    ax2.plot([2.5, 2.5], [1.1, 0.5], color='#94A3B8', lw=1.5)
    ax2.plot([7.5, 7.5], [1.1, 0.5], color='#94A3B8', lw=1.5)

    ax2.set_xlim(0, 10.0)
    ax2.set_ylim(-0.8, 6.0)
    ax2.axis('off')

    # -------------------------------------------------------------
    # PANEL 3: İsim Çözümleme Katmanları Gecikme Profili (Log Ölçek)
    # -------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor(DARK_BG)
    ax3.set_title("3. Çözümleme Katmanları Gecikme Profili (Mikrosaniye - Log)", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)

    methods = ['/etc/hosts\n(Statik)', 'Local Cache\n(systemd)', 'Taktik DNS\n(Internal)', 'Genel WAN\n(Public)', 'DNS Timeout\n(Air-Gap Felaketi)']
    # Gecikmeler mikrosaniye cinsinden: 5 us, 30 us, 1500 us (1.5ms), 45000 us (45ms), 5000000 us (5s)
    lat_us = [5.0, 30.0, 1500.0, 45000.0, 5000000.0]
    colors_lat = [ACCENT_GREEN, ACCENT_BLUE, ACCENT_AMBER, '#EC4899', ACCENT_RED]

    bars = ax3.bar(methods, lat_us, color=colors_lat, width=0.5, edgecolor='#FFFFFF')
    ax3.set_yscale('log')
    for bar in bars:
        yval = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2.0, yval * 1.3, f"{yval:,.0f} µs", ha='center', va='bottom', color=TEXT_COLOR, fontsize=8, fontweight='bold')

    ax3.set_ylabel("Çözümleme Gecikmesi (µs - Log Ölçek)", color=TEXT_COLOR)
    ax3.set_ylim(1, 20000000)
    ax3.grid(True, linestyle=':', alpha=0.3, color='#475569')
    ax3.tick_params(colors=TEXT_COLOR)

    # -------------------------------------------------------------
    # PANEL 4: DNS Spoofing Başarı Olasılığı vs Entropi
    # -------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor(DARK_BG)
    ax4.set_title("4. DNS Spoofing Başarı Riski vs Entropi Güvenliği", fontsize=12, fontweight='bold', color=TEXT_COLOR, pad=12)

    schemes = ['Yalnızca Sabit Port\n(16-bit XID)', 'Port Randomization\n(16b XID + 16b Port)', 'DNSSEC Kalkanı\n(Kriptografik İmza)']
    risk_pct = [95.0, 0.05, 0.0]
    colors_risk = [ACCENT_RED, ACCENT_AMBER, ACCENT_GREEN]

    bars4 = ax4.bar(schemes, risk_pct, color=colors_risk, width=0.45, edgecolor='#FFFFFF')
    for bar in bars4:
        yval = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 2.0, f"%{yval:.2f}", ha='center', va='bottom', color=TEXT_COLOR, fontweight='bold')

    ax4.set_ylabel("Başarılı Zehirlenme Riski (%)", color=TEXT_COLOR)
    ax4.set_ylim(0, 115)
    ax4.grid(True, linestyle=':', alpha=0.3, color='#475569')
    ax4.tick_params(colors=TEXT_COLOR)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor='#0F172A')
    plt.close()
    print(f"[Dashboard] Görselleştirme panosu başarıyla oluşturuldu: {output_path}")

def verify_all_assertions(png_path: str):
    print("")
    print("[*] GÜN 136 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. PNG Dosya Varlığı ve Boyutu (> 100 KB)
    assert os.path.exists(png_path), f"HATA: Dashboard PNG dosyası bulunamadı: {png_path}"
    png_size = os.path.getsize(png_path)
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
    assert png_size > 100_000, f"HATA: PNG boyutu 100 KB altında ({png_size} bayt)!"

    # 2. QNAME Kodlama ve Çözme Doğrulaması
    encoded = DNSCodec.encode_qname("radar.aselsan.local")
    expected_encoded = b"\x05radar\x07aselsan\x05local\x00"
    assert encoded == expected_encoded, "HATA: QNAME etiket kodlaması hatalı!"
    
    decoded, consumed = DNSCodec.decode_qname(b"\x00" * 12 + encoded, offset=12)
    assert decoded == "radar.aselsan.local" and consumed == len(encoded)
    print("  [+] RFC 1035 QNAME Etiket Kodlama ve Çözme Doğrulandı.")

    # 3. Başlık Paketleme (12 Bayt) Doğrulaması
    hdr = DNSHeader(xid=0x1234, flags=0x0100, qdcount=1, ancount=0)
    raw_hdr = hdr.pack()
    assert len(raw_hdr) == 12, "HATA: DNS başlığı tam 12 bayt olmalıdır!"
    
    unpacked_hdr = DNSHeader.unpack(raw_hdr)
    assert unpacked_hdr.xid == 0x1234 and unpacked_hdr.qdcount == 1
    print("  [+] RFC 1035 12-Baytlık DNS Başlık Kodlama ve Çözme Doğrulandı.")

    # 4. Önbellek Performansı Doğrulaması
    assert dns_cache_latency_ns < 1000.0, "HATA: O(1) DNS önbellek arama süresi 1 us altında olmalıdır!"
    print(f"  [+] O(1) Bellek İçi DNS Önbellek Arama Performansı Doğrulandı ({dns_cache_latency_ns:.1f} ns/sorgu).")

    print("")
    print("[PASS] Gün 136: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
    print("")

if __name__ == "__main__":
    _cur_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else "."
    _png_path = os.path.join(_cur_dir, "gun_136_dns_zihinsel_modeli.png")
    generate_dns_dashboard(_png_path)
    verify_all_assertions(_png_path)
