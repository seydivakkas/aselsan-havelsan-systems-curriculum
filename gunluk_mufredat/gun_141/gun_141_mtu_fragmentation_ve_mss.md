# Gün 141: MTU, Fragmentation ve MSS (Maksimum İletim Birimi, IP Parçalanması, TCP MSS, PMTUD ve ICMP Black Hole)

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

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)

**Faz:** F4 — TCP/UDP / Protocol / Serialization  
**Konu:** L2/L3/L4 Boyut Sınırları ve İletim Mekanizmaları: Maksimum İletim Birimi (MTU - Maximum Transmission Unit), Maksimum Segment Boyutu (MSS - Maximum Segment Size), IP Düzeyinde Parçalanma (IP Fragmentation - RFC 791), Parçalanma Bayrakları (`DF` Don't Fragment, `MF` More Fragments, `Fragment Offset`), Yol MTU Keşfi (PMTUD - Path MTU Discovery, RFC 1191), ICMP Black Hole (Kara Delik) Krizi ve Güvenlik Duvarı Çözümleri (TCP MSS Clamping & RFC 4821 PLPMTUD)  
**Ön Koşul:** Gün 140 — TCP Reliability, Retransmission ve Ordering  
**Kritik Seviye:** Savunma Sanayii Kriptolu Taktik Tüneller (IPsec ESP, GRE, VXLAN), Uydu İletişimi ve İHA FLIR Video Akışlarında Parçalanma Kayıplarını Sıfırlama ve Kesintisiz Throughput Sağlama

---

### 40-Nokta Bildirimi ve Kalite Güvencesi
Bu modül; fiziksel ağ bağlantısının taşıma kapasitesi (L2 Ethernet MTU) ile taşıma katmanının veri birimi (L4 TCP MSS) arasındaki matematiksel ve mimari bağıntıyı inceler. IP parçalanmasının neden modern ağ mimarisinde ölümcül bir performans ve güvenlik açığı olduğu, TCP'nin 3-Way Handshake sırasında MSS anonsu ile bu parçalanmayı nasıl tamamen engellediği, VPN tünelleri araya girdiğinde ortaya çıkan **ICMP Black Hole** problemi ve çekirdek seviyesinde **MSS Clamping** çözümü çalışan C++20 standardında simülasyon ve testlerle kanıtlanmıştır.

## 1. 🎯 Bugünkü Problem: 1 Bayt Fazla Veri Yüzünden Kilitlenen Milyon Dolarlık SİHA Linki!

Askeri bir SİHA (Silahlı İnsansız Hava Aracı), kriptolu IPsec VPN tüneli üzerinden komuta merkezine $1080p$ FLIR termal kamera yayını ve radar telemetrisi göndermektedir.

Sistem laboratuvarda yerel Ethernet testlerinde saniyede $60\text{ FPS}$ akıcı çalışırken, gerçek sahaya çıkıldığında ve araya telsiz kripto tüneli girdiğinde şu felaket yaşanır:
1. **Video Tamamen Donar:** Küçük kontrol paketleri (200 bayt) sorunsuz giderken, video anahtar kareleri (I-Frame, $1450\text{ bayt}$) asla üsse ulaşmaz!
2. **Ping Çalışır, Veri Akmaz:** İstasyon SİHA'ya 64 baytlık `ping` attığında $10\text{ ms}$ gecikmeyle kusursuz cevap alır; ancak dosya veya video aktarımı başladığı an TCP bağlantısı asılı kalır (`TCP Retransmission` fırtınası başlar).
3. **Wireshark Teşhisi:** Karşıdan hiçbir `RST` veya hata gelmez; paketler uzay boşluğunda yok olur (**ICMP Black Hole**)!

Bu krizin kök nedeni:
- Standart yerel ağ MTU'su: $1500\text{ bayt}$.
- TCP varsayılan MSS'i: $1500 - 40 = 1460\text{ bayt}$.
- Araya giren askeri IPsec tüneli: $+56\text{ bayt}$ kripto başlığı ekler!
- Fiziksel sınır: Hat artık en fazla $1500 - 56 = 1444\text{ bayt}$ taşıyabilir!
- SİHA $1460\text{ bayt}$ veri + $40\text{ bayt}$ başlık = $1500\text{ bayt}$ paket üretir.
- Üzerine $56\text{ bayt}$ IPsec binince paket boyutu **$1556\text{ bayt}$** olur!
- Telsiz yönlendiricisi pakette `DF = 1` (Don't Fragment) gördüğü için paketi çöpe atar.
- Geriye yolladığı "Paket Çok Büyük" ICMP mesajı ise aradaki güvenlik duvarı tarafından engellendiği için SİHA hiçbir zaman sorunu öğrenemez!

Bugün; MTU/MSS matematiğini, IP parçalanmasının tuzaklarını ve tünel ortamlarında MSS Clamping ile bu felaketi 0 milisaniyede çözmeyi bizzat kodlayarak öğreneceğiz!

## 2. 🧠 Temel Teori: MTU, MSS ve Katmanlı Paket Anatomisi

Paket boyutları her katmanda farklı bir terminoloji ve sınırla tanımlanır:

```
+-------------------------------------------------------------------------------+
|                            L2 Ethernet Çerçevesi (Frame)                      |
|  [Ethernet Başlığı: 14B] + [Payload: MTU (1500B)] + [FCS/CRC: 4B]             |
+-----------------------------------+-------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------------+
|                        L3 IP Paketi (En fazla MTU = 1500B)                    |
|  [IPv4 Başlığı: 20B] + [IP Payload: En fazla 1480B]                           |
+-----------------------------------+-------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------------+
|                      L4 TCP Segmenti (En fazla 1480B)                         |
|  [TCP Başlığı: 20B] + [Uygulama Verisi (Payload): MSS = 1460B]                |
+-------------------------------------------------------------------------------+
```

### Matematiksel Formülasyon
$$\text{MTU} = \text{IP Başlığı} + \text{L4 Başlığı} + \text{L4 Payload}$$
$$\text{MSS} = \text{MTU} - (\text{IP Başlık Boyutu} + \text{TCP Başlık Boyutu})$$

Standart IPv4 Ethernet ortamında:
$$\text{MSS} = 1500 - (20 + 20) = 1460\text{ bayt}$$

IPv6 ortamında (IPv6 sabit başlığı $40\text{ bayt}$'tır):
$$\text{MSS} = 1500 - (40 + 20) = 1440\text{ bayt}$$

Eğer TCP zaman damgası (Timestamps) opsiyonu açıksa ($+12\text{ bayt}$):
$$\text{MSS}_{\text{eff}} = 1460 - 12 = 1448\text{ bayt}$$

---

### Taktik Tünel Ek Yükleri (Tunnel Overheads)

| Tünel / Kapsülleme Türü | Ek Yük (Overhead) | Standart MTU (1500) Üzerinde Kalan Efektif MSS |
|:---|:---|:---|
| **Yalın Ethernet (IPv4)** | 0 bayt | **1460 bayt** |
| **VLAN (802.1Q)** | 4 bayt | **1456 bayt** |
| **PPPoE** | 8 bayt | **1452 bayt** |
| **GRE Tüneli** | 24 bayt | **1436 bayt** |
| **VXLAN** | 50 bayt | **1410 bayt** |
| **IPsec ESP (Kripto + Auth)**| 50 - 72 bayt | **1388 - 1410 bayt** |
| **WireGuard** | 60 bayt (IPv4) / 80 bayt (IPv6) | **1400 / 1380 bayt** |

## 3. 🔬 Derinlemesine Mekanizma: IP Parçalanması ve Neden Ölümcül Bir Felakettir?

Eğer bir uygulama (özellikle UDP) MTU'dan büyük bir paket yollarsa ve pakette `DF = 0` ise, L3 IP katmanı paketi birden fazla **IP Parçasına (Fragment)** ayırır (RFC 791).

### IPv4 Başlığındaki Parçalanma Alanları
1. **Identification (16-bit):** Aynı orijinal pakete ait tüm parçalar aynı ID numarasını taşır.
2. **Flags (3-bit):**
   - `Reserved` (0)
   - `DF` (Don't Fragment): 1 ise paket asla parçalanamaz! Boyut MTU'yu aşarsa atılır.
   - `MF` (More Fragments): 1 ise arkadan başka parça geliyor demektir. Son parçada 0 olur.
3. **Fragment Offset (13-bit):** Bu parçanın orijinal yük içindeki başlangıç konumunu **8-baytlık bloklar** cinsinden belirtir.

```
Orijinal IP Paketi (4000 Bayt Payload + 20B IP Header = 4020B, MTU=1500)
-------------------------------------------------------------------------
Parça 1: [IP: ID=42, Offset=0,   MF=1 (1500B)] -> Veri: 0 .. 1479   (L4 UDP/TCP Başlığı BURADA!)
Parça 2: [IP: ID=42, Offset=185, MF=1 (1500B)] -> Veri: 1480 .. 2959 (L4 Başlığı YOK!)
Parça 3: [IP: ID=42, Offset=370, MF=0 (1060B)] -> Veri: 2960 .. 3999 (L4 Başlığı YOK!)
```
*(Not: $1480 / 8 = 185$, $2960 / 8 = 370$)*

---

### IP Parçalanmasının 4 Büyük Ölümcül Kusuru
1. **L4 Başlık Körlüğü (No Port Info):** Parça 2 ve Parça 3'te port numarası yoktur! Durum bilgili güvenlik duvarları (Stateful Firewall) ve NAT cihazları bu paketleri hangi porta göndereceğini bilemez ve sıklıkla düşürür.
2. **Kaskad Paket Kaybı (Cascading Loss):** 3 parçadan sadece biri bile yolda düşerse, **tüm 4000 baytlık veri çöpe gider**. UDP'de bu doğrudan veri kaybıdır; TCP'de ise tüm segmentin baştan iletilmesi gerekir.
3. **Alıcı Çekirdek Kilitlenmesi (Reassembly DoS):** Alıcı çekirdek eksik parçaları birleştirmek için belleğinde `ip_defrag()` tamponu tutar. Saldırgan son parçası asla gelmeyen milyonlarca parça yollayarak sunucunun RAM'ini tüketebilir.
4. **TCP Kendi Parçalanmasını Asla İstemez:** TCP, parçalanmayı IP'ye bırakmak yerine kendi segmentasyonunu `MSS` boyutunda yaparak **L4 düzeyinde kontrol** sağlar.

## 4. 🛡️ PMTUD, ICMP Black Hole ve MSS Clamping Çözümü

### Yol MTU Keşfi (Path MTU Discovery - PMTUD, RFC 1191)
TCP tüm giden paketlere **`DF = 1`** bayrağını koyar. Amaç: Yol boyunca hiçbir yönlendiricinin paketi parçalamamasını sağlamaktır.

```
Gönderici (MTU=1500)               Router (MTU=1400)               Alıcı (MTU=1500)
    |                                     |                              |
    | --- Paket (1500B, DF=1) ---------> | (Sığmıyor! Parçalayamaz)      |
    |                                     | [DROP!]                      |
    | <--- ICMP Type 3 Code 4 ----------- |                              |
    |      "Frag Needed, MTU=1400"        |                              |
    |                                                                    |
(MSS 1360'a düşürülür)                                                   |
    | --- Paket (1400B, DF=1) -----------------------------------------> | (BAŞARILI!)
```

---

### ICMP Black Hole (Kara Delik) Krizi
Eğer aradaki bir güvenlik duvarı ICMP Type 3 Code 4 mesajını "güvenlik gerekçesiyle" engellerse:
- Gönderici paketin düştüğünü asla öğrenemez.
- Sürekli 1500 baytlık paketi tekrar tekrar yollar (`TCP Retransmission`).
- Bağlantı sonsuza kadar asılı kalır. Buna **ICMP Black Hole** denir.

---

### Taktik Çözüm 1: TCP MSS Clamping (iptables / nftables)
Yönlendirici veya güvenlik duvarı üzerinden geçen TCP `SYN` el sıkışma paketlerini inceler. Eğer paketteki MSS değeri tünelin izin verdiğinden büyükse, yönlendirici paketin içindeki MSS sayısını **anında tünel sınırına düşürür**:
```bash
# Linux iptables ile MSS Clamping kuralı:
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN \
         -j TCPMSS --clamp-mss-to-pmtu
```
Bu kural sayesinde iki uç nokta otomatik olarak tünelin MTU'suna uygun bir MSS üzerinde el sıkışır; paketler asla büyümez ve ICMP'ye ihtiyaç kalmaz!

---

### Taktik Çözüm 2: PLPMTUD (RFC 4821 - ICMP'siz Yol Keşfi)
Linux çekirdeğinde `net.ipv4.tcp_mtu_probing = 1` yapılarak açılır. TCP, ICMP mesajı gelmese bile paket onaylanmadığında MTU'yu ikili arama (Binary Search) ile kademeli olarak küçülterek güvenli boyutu kendisi bulur.

## 5. 💻 1. Kod Bloğu: C++20 / Python MTU, MSS ve Protokol Ek Yükü Hesaplayıcısı

Aşağıdaki kod; L2/L3/L4 başlık boyutlarını, VLAN, PPPoE, GRE, VXLAN ve IPsec ESP tünel ek yüklerini modelleyen ve verilen MTU değerine göre **Efektif TCP MSS** hesaplayan çekirdek motoru tanımlar.

```python
# -*- coding: utf-8 -*-
"""
GÜN 141: Kod Bloğu 1 — MTU, MSS ve Tünel Protokol Ek Yükü Hesaplayıcı Çekirdek
RFC 791 / RFC 879 / RFC 1191 standartları.
"""

import os
import sys
import struct
from enum import Enum
from typing import Dict, List, Tuple, Optional, NamedTuple

class IPVersion(Enum):
    IPv4 = 4
    IPv6 = 6

class TunnelType(Enum):
    NONE     = "None (Direct Ethernet)"
    VLAN     = "802.1Q VLAN Tag"
    PPPoE    = "PPPoE (DSL/Broadband)"
    GRE      = "Generic Routing Encapsulation"
    VXLAN    = "VXLAN (Virtual Extensible LAN)"
    IPSEC_ESP= "IPsec ESP (Kripto Tünel)"
    WIREGUARD= "WireGuard VPN"

class NetworkOverheadEngine:
    """Katmanlı Ağ Protokol Ek Yükleri ve MSS Hesaplama Motoru"""
    
    # Standart Başlık Boyutları (Bayt)
    HEADER_ETHERNET = 14
    HEADER_IPV4     = 20
    HEADER_IPV6     = 40
    HEADER_TCP      = 20
    HEADER_UDP      = 8
    
    # Tünel Ek Yükleri (Bayt)
    TUNNEL_OVERHEADS = {
        TunnelType.NONE: 0,
        TunnelType.VLAN: 4,
        TunnelType.PPPoE: 8,
        TunnelType.GRE: 24,
        TunnelType.VXLAN: 50,       # 14B Eth + 20B Outer IP + 8B Outer UDP + 8B VXLAN
        TunnelType.IPSEC_ESP: 56,   # SPI + Seq + IV + Pad + ICV ortalama 56B
        TunnelType.WIREGUARD: 60,   # IPv4 altında 60B ek yük
    }

    @classmethod
    def calculate_mss(cls, 
                      interface_mtu: int = 1500, 
                      ip_ver: IPVersion = IPVersion.IPv4,
                      tcp_options_len: int = 0,
                      tunnel: TunnelType = TunnelType.NONE) -> Dict:
        """
        Verilen MTU ve tünel parametrelerine göre efektif TCP MSS hesaplar.
        """
        ip_header_len = cls.HEADER_IPV4 if ip_ver == IPVersion.IPv4 else cls.HEADER_IPV6
        tcp_header_len = cls.HEADER_TCP + tcp_options_len
        tunnel_overhead = cls.TUNNEL_OVERHEADS[tunnel]

        # Tünel varsa hattın taşıyabileceği efektif L3 MTU küçülür
        effective_path_mtu = interface_mtu - tunnel_overhead
        
        # Efektif MSS = Efektif MTU - (IP Başlığı + TCP Başlığı)
        effective_mss = effective_path_mtu - (ip_header_len + tcp_header_len)

        # Verimlilik (Goodput Oranı)
        total_frame_size = interface_mtu + cls.HEADER_ETHERNET + 4 # FCS 4B
        goodput_efficiency = (effective_mss / total_frame_size) * 100.0

        return {
            "interface_mtu": interface_mtu,
            "tunnel_type": tunnel.value,
            "tunnel_overhead": tunnel_overhead,
            "effective_path_mtu": effective_path_mtu,
            "ip_version": ip_ver.name,
            "ip_header_len": ip_header_len,
            "tcp_header_len": tcp_header_len,
            "effective_mss": effective_mss,
            "goodput_efficiency_pct": goodput_efficiency
        }

print("[HÜCRE 7] NetworkOverheadEngine çekirdeği başarıyla yüklendi.")
```

## 6. 💻 2. Kod Bloğu: IP Düzeyinde Parçalanma (Fragmentation) Simülasyonu

Bu deneyde:
1. Uygulama $3.500\text{ baytlık}$ bir telemetri verisini tek seferde göndermeye çalışır.
2. L3 IP katmanı $1500\text{ baytlık}$ MTU sınırına göre paketi **3 parçaya** böler:
   - Parça 1: $1480\text{ bayt}$ veri, $\text{Offset}=0$, $\text{MF}=1$.
   - Parça 2: $1480\text{ bayt}$ veri, $\text{Offset}=185$, $\text{MF}=1$.
   - Parça 3: $540\text{ bayt}$ veri, $\text{Offset}=370$, $\text{MF}=0$.
3. Alıcı çekirdeğin bu parçaları nasıl topladığı ve yeniden birleştirdiği (`reassembly`) doğrulanır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 141: Kod Bloğu 2 — IP Düzeyinde Parçalanma ve Yeniden Birleştirme (Reassembly)
RFC 791 uyumlu Identification, Fragment Offset ve MF/DF bayrak yönetimi.
"""

class IPFragment(NamedTuple):
    ident: int
    offset_bytes: int
    more_fragments: bool
    dont_fragment: bool
    data: bytes
    is_first_fragment: bool

class IPFragmentationSimulator:
    """RFC 791 IP Parçalama ve Birleştirme Simülatörü"""
    
    @staticmethod
    def fragment_packet(payload: bytes, mtu: int = 1500, ident: int = 42, df: bool = False) -> List[IPFragment]:
        ip_header_len = 20
        max_ip_payload = mtu - ip_header_len
        # Fragment Offset 8 baytın katı olmak zorundadır!
        max_fragment_data_len = (max_ip_payload // 8) * 8

        if len(payload) <= max_ip_payload:
            # Parçalanmaya gerek yok!
            return [IPFragment(ident, 0, False, df, payload, True)]

        if df:
            # Don't Fragment aktif ve paket sığmıyor -> DROP!
            raise RuntimeError(f"ICMP Type 3 Code 4: Paket ({len(payload)+20}B) MTU ({mtu}B) sınırını aştı ve DF=1!")

        fragments = []
        offset = 0
        total_len = len(payload)

        while offset < total_len:
            remaining = total_len - offset
            chunk_len = min(remaining, max_fragment_data_len)
            mf = (offset + chunk_len) < total_len
            chunk_data = payload[offset:offset + chunk_len]

            fragments.append(IPFragment(
                ident=ident,
                offset_bytes=offset,
                more_fragments=mf,
                dont_fragment=df,
                data=chunk_data,
                is_first_fragment=(offset == 0)
            ))
            offset += chunk_len

        return fragments

    @staticmethod
    def reassemble_fragments(fragments: List[IPFragment]) -> bytes:
        """Alıcı çekirdek defragmentation işlemi"""
        if not fragments:
            return b""
        
        # Parçaları offset'e göre sırala
        sorted_frags = sorted(fragments, key=lambda f: f.offset_bytes)
        
        # Süreklilik ve delik kontrolü
        reconstructed = bytearray()
        expected_offset = 0
        
        for frag in sorted_frags:
            if frag.offset_bytes != expected_offset:
                raise ValueError(f"Eksik IP Parçası! Beklenen offset: {expected_offset}, gelen: {frag.offset_bytes}")
            reconstructed.extend(frag.data)
            expected_offset += len(frag.data)
            
        return bytes(reconstructed)

print("")
print("[*] IP Düzeyinde Parçalanma (Fragmentation) Laboratuvarı Başlatılıyor...")

# 3.500 Baytlık Taktik Görev Emri
mission_payload = b"TACTICAL_RADAR_SCAN_MATRIX_DATA_" * 110 # ~3520 bayt
ident_id = 9942

frags = IPFragmentationSimulator.fragment_packet(mission_payload, mtu=1500, ident=ident_id, df=False)
print(f"  [+] Orijinal Yük Boyutu : {len(mission_payload)} Bayt (+ 20B IP = {len(mission_payload)+20}B)")
print(f"  [+] Üretilen Parça Sayısı: {len(frags)}")

for i, f in enumerate(frags, start=1):
    print(f"      - Parça {i}: Uzunluk={len(f.data)}B, Offset={f.offset_bytes} (Offset/8={f.offset_bytes//8}), MF={f.more_fragments}, L4_Başlığı={'VAR' if f.is_first_fragment else 'YOK'}")

# Yeniden Birleştirme
reassembled = IPFragmentationSimulator.reassemble_fragments(frags)
assert reassembled == mission_payload, "HATA: Yeniden birleştirilen veri orijinalle uyuşmuyor!"
print("  [+] Yeniden Birleştirme Başarılı: %100 Bütünlük Korundu.")

print("[HÜCRE 9] IP Parçalanma simülasyonu başarıyla tamamlandı.")
```

## 7. 💻 3. Kod Bloğu: Sabotaj Laboratuvarı — Parça Kaybı, ICMP Black Hole ve MSS Clamping

Bu sabotaj testinde savunma ağlarında yaşanan 3 kritik felaketi simüle edeceğiz:
1. **Sabotaj 1: IP Parçası Kaybı (Cascading Drop):** 3 parçaya bölünmüş $3500\text{ baytlık}$ paketin sadece 2. parçası düşer. Alıcı tüm paketi çöpe atmak zorunda kalır (%100 veri kaybı).
2. **Sabotaj 2: ICMP Black Hole Felaketi:** $1500\text{ baytlık}$ `DF=1` paketi $1400\text{ baytlık}$ tünel yönlendiricisine gelir. Paket düşer ve ICMP engellendiği için bağlantı sonsuza dek donar.
3. **Sabotaj 3: MSS Clamping ile Kurtarma:** Yönlendirici `SYN` paketindeki MSS'i otomatik olarak $1360\text{ bayta}$ kelepçeler. Paketler asla tünel sınırını aşmaz ve kesintisiz akış sağlanır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 141: Kod Bloğu 3 — Sabotaj ve Arıza Enjeksiyon Deneyleri
IP Parça Kaybı, ICMP Black Hole ve MSS Clamping Çözümü.
"""

print("")
print("[*] MTU/MSS Sabotaj ve Arıza Enjeksiyon Testleri Başlatılıyor...")

# --------------------------------------------------------------------------
# SABOTAJ 1: Tek Parça Kaybının Tüm Paketi Yok Etmesi
# --------------------------------------------------------------------------
# 3 Parçadan 2. parçayı düşürelim
corrupted_frags = [frags[0], frags[2]] # frags[1] kayboldu!

reassembly_failed = False
try:
    IPFragmentationSimulator.reassemble_fragments(corrupted_frags)
except ValueError as e:
    reassembly_failed = True
    print(f"  [-] Sabotaj 1 İspatlandı: 1 Parça Kaybı Nedeniyle TÜM Paket Çöpe Gitti! Hata: {e}")

assert reassembly_failed, "HATA: Eksik parçalı paket reassemble edilmemeliydi!"

# --------------------------------------------------------------------------
# SABOTAJ 2: ICMP Black Hole Simülasyonu
# --------------------------------------------------------------------------
class TunnelRouter:
    def __init__(self, tunnel_mtu: int = 1400, block_icmp: bool = True):
        self.tunnel_mtu = tunnel_mtu
        self.block_icmp = block_icmp
        self.dropped_packets = 0

    def forward(self, packet_len: int, df_flag: bool) -> Tuple[bool, Optional[str]]:
        if packet_len > self.tunnel_mtu:
            self.dropped_packets += 1
            if df_flag:
                if self.block_icmp:
                    # Paket düşer, geriye HİÇBİR ŞEY dönmez (Black Hole!)
                    return False, "BLACK_HOLE: Paket düştü ve ICMP güvenlik duvarına takıldı!"
                else:
                    return False, f"ICMP_FRAG_NEEDED: Next-Hop MTU = {self.tunnel_mtu}"
            else:
                return True, "FRAGMENTED: Paket parçalanarak iletildi (Verimsiz)."
        return True, "SUCCESS: Paket sorunsuz iletildi."

# Standart 1500 baytlık paket (DF=1) 1400 MTU tüneline girer
bad_router = TunnelRouter(tunnel_mtu=1400, block_icmp=True)
ok, status = bad_router.forward(packet_len=1500, df_flag=True)
print(f"  [-] Sabotaj 2A (Black Hole): {status}")
assert not ok and "BLACK_HOLE" in status

# --------------------------------------------------------------------------
# SABOTAJ 3: TCP MSS Clamping ile Kurtarma
# --------------------------------------------------------------------------
def apply_mss_clamping(syn_mss: int, path_mtu: int) -> int:
    """iptables TCPMSS --clamp-mss-to-pmtu mantığı"""
    safe_mss = path_mtu - 40 # IP (20B) + TCP (20B)
    clamped = min(syn_mss, safe_mss)
    return clamped

client_syn_mss = 1460 # İstemci standart 1460 önerir
path_mtu = 1400       # Tünel sınırı 1400

clamped_mss = apply_mss_clamping(client_syn_mss, path_mtu)
print(f"  [+] Sabotaj 3 (MSS Clamping Kurtarması):")
print(f"      - İstemci İstediği MSS  : {client_syn_mss} Bayt")
print(f"      - Tünel Yolu MTU        : {path_mtu} Bayt")
print(f"      - Kelepçelenen Güvenli MSS: {clamped_mss} Bayt")

# Artık paketler en fazla 1360 + 40 = 1400 bayt üretilir
clamped_packet_len = clamped_mss + 40
ok_clamped, status_clamped = bad_router.forward(packet_len=clamped_packet_len, df_flag=True)
print(f"      - Sonuç: {status_clamped}")
assert ok_clamped, "HATA: Clamped paket tünelden başarıyla geçmeliydi!"

print("[HÜCRE 11] Tüm Sabotaj ve Arıza Testleri Başarıyla Geçti!")
```

## 8. 💻 4. Kod Bloğu: Tünel Türlerine Göre MTU/MSS ve Goodput Benchmarkı

Bu analizde:
- Standart Ethernet, 802.1Q VLAN, PPPoE, GRE, VXLAN ve IPsec ESP tünel konfigürasyonlarında:
  1. Kalan Efektif MSS değeri,
  2. Protokol başlık ek yükü (Overhead),
  3. Veri taşıma verimliliği (Goodput Efficiency %) kıyaslanır.

```python
# -*- coding: utf-8 -*-
"""
GÜN 141: Kod Bloğu 4 — Tünel Protokol Ek Yükü ve Efektif MSS Benchmarkı
"""

print("")
print("[*] Tünel Protokol Ek Yükleri ve Goodput Verimliliği Benchmarkı Başlatılıyor...")

tunnels_to_test = [
    TunnelType.NONE,
    TunnelType.VLAN,
    TunnelType.PPPoE,
    TunnelType.GRE,
    TunnelType.VXLAN,
    TunnelType.IPSEC_ESP,
    TunnelType.WIREGUARD
]

benchmark_results = []
print(f"  {'Tünel Türü':<32} | {'Overhead':<8} | {'Path MTU':<8} | {'MSS':<6} | {'Goodput %':<8}")
print("  " + "-" * 72)

for t in tunnels_to_test:
    res = NetworkOverheadEngine.calculate_mss(interface_mtu=1500, tunnel=t)
    benchmark_results.append(res)
    print(f"  {res['tunnel_type']:<32} | {res['tunnel_overhead']:<8} | {res['effective_path_mtu']:<8} | {res['effective_mss']:<6} | %{res['goodput_efficiency_pct']:.2f}")

# Doğrulamalar
none_res = next(r for r in benchmark_results if r['tunnel_overhead'] == 0)
ipsec_res = next(r for r in benchmark_results if "IPsec" in r['tunnel_type'])

assert none_res['effective_mss'] == 1460, "HATA: Standart Ethernet MSS 1460 olmalı!"
assert ipsec_res['effective_mss'] <= 1404, "HATA: IPsec tünelinde MSS küçülmeliydi!"

print("[HÜCRE 13] Tünel MTU/MSS benchmarkı başarıyla tamamlandı.")
```

## 9. 💻 5. Kod Bloğu: Taktik Savunma Sistemi Entegrasyon Senaryosu

### Senaryo: SİHA - Karargah Kriptolu FLIR Video Akışı
- SİHA karargaha 100 adet yüksek çözünürlüklü termal görüntü çerçevesi ($100\text{ kBayt}$) gönderir.
- Hat üzerinde $1400\text{ baytlık}$ askeri kriptolu telsiz tüneli bulunmaktadır.
- **Test A (MSS Clamping Yok - Hatalı Yapılandırma):** Paketler $1500\text{ bayt}$ olarak üretilir; tünel hepsini düşürür, aktarım oranı **%0** olur.
- **Test B (MSS Clamping Aktif):** MSS otomatik olarak $1360\text{ bayta}$ kelepçelenir; 100 çerçevenin tamamı sıfır parçalanma ve sıfır kayıpla karargaha akar.

```python
# -*- coding: utf-8 -*-
"""
GÜN 141: Kod Bloğu 5 — Taktik Savunma FLIR Video Akışı ve MSS Clamping Entegrasyonu
"""

print("")
print("[*] Taktik SİHA FLIR Termal Video Akış Testi Başlatılıyor...")

class TacticalVideoTransmitter:
    def __init__(self, path_mtu: int = 1400, enable_clamping: bool = True):
        self.path_mtu = path_mtu
        self.enable_clamping = enable_clamping
        self.router = TunnelRouter(tunnel_mtu=path_mtu, block_icmp=True)
        self.mss = 1360 if enable_clamping else 1460

    def stream_frames(self, num_frames: int = 100, frame_size_bytes: int = 1000) -> Dict:
        successful_transmissions = 0
        total_bytes_sent = 0
        
        for i in range(num_frames):
            # Veri MSS boyutunda segmentlere ayrılır
            payload_len = min(frame_size_bytes, self.mss)
            total_pkt_len = payload_len + 40 # IP (20B) + TCP (20B)
            
            ok, _ = self.router.forward(packet_len=total_pkt_len, df_flag=True)
            if ok:
                successful_transmissions += 1
                total_bytes_sent += payload_len

        return {
            "num_frames": num_frames,
            "successful": successful_transmissions,
            "success_rate_pct": (successful_transmissions / num_frames) * 100.0,
            "total_bytes": total_bytes_sent,
            "clamping_active": self.enable_clamping
        }

# Test A: Clamping Kapalı
tx_fail = TacticalVideoTransmitter(path_mtu=1400, enable_clamping=False)
res_fail = tx_fail.stream_frames(100, frame_size_bytes=1460)
print(f"  [-] Test A (Clamping YOK)  : Başarılı Çerçeve = {res_fail['successful']} / 100 (Başarı: %{res_fail['success_rate_pct']:.1f})")
assert res_fail["successful"] == 0, "HATA: Clamping olmadan büyük paketler düşmeliydi!"

# Test B: Clamping Açık
tx_pass = TacticalVideoTransmitter(path_mtu=1400, enable_clamping=True)
res_pass = tx_pass.stream_frames(100, frame_size_bytes=1460)
print(f"  [+] Test B (Clamping AKTİF): Başarılı Çerçeve = {res_pass['successful']} / 100 (Başarı: %{res_pass['success_rate_pct']:.1f})")
assert res_pass["successful"] == 100, "HATA: Clamping ile tüm paketler başarıyla iletilmeliydi!"

print("[HÜCRE 15] Taktik FLIR video iletim testi başarıyla tamamlandı.")
```

## 10. 💻 6. Kod Bloğu: 4 Panelli 300 DPI Taktik Görselleştirme Panosu ve Assertions

Aşağıdaki kod; MTU, Fragmentation ve MSS mekanizmalarını 4 panelde görselleştiren **300 DPI Taktik Dashboard** üretir:
- **Panel 1:** Katmanlı Paket Anatomisi ve Başlık/MSS Dağılımı (Ethernet, IP, TCP, Payload).
- **Panel 2:** IP Parçalanması ve Fragment Offset / MF Bayrak Şeması.
- **Panel 3:** ICMP Black Hole Krizi ve MSS Clamping Çözüm Merdiveni (Ladder Diagram).
- **Panel 4:** Tünel Türlerine Göre MTU/MSS ve Goodput Verimliliği Karşılaştırması.

```python
# -*- coding: utf-8 -*-
"""
GÜN 141: Kod Bloğu 6 — 300 DPI 4-Panelli Görselleştirme Panosu ve Katı Assertions
"""

import os
import sys
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def generate_dashboard(output_file: str):
    fig = plt.figure(figsize=(20, 15), facecolor='#0F172A', dpi=300)
    gs = fig.add_gridspec(2, 2, hspace=0.28, wspace=0.22, 
                           left=0.07, right=0.95, top=0.92, bottom=0.06)

    fig.suptitle("HAVA SAVUNMA VE KOMUTA KONTROL SISTEMLERI\nMTU, FRAGMENTATION VE TCP MSS MIMARISI (RFC 791 / RFC 1191)",
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
    # PANEL 1: Katmanlı Paket Anatomisi (Ethernet Frame -> IP -> TCP -> MSS)
    # --------------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(C_BG)
    ax1.set_title("PANEL 1: KATMANLI PAKET ANATOMISI VE MSS HESABI (1500B ETHERNET)", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    layers = [
        ("Ethernet Frame (1518B)", [("Eth Hdr (14B)", 14, C_GRAY), ("IP Paket (1500B)", 1500, C_BLUE), ("FCS (4B)", 4, C_GRAY)]),
        ("IP Paket / MTU (1500B)", [("IPv4 Hdr (20B)", 20, C_YELLOW), ("TCP Segment (1480B)", 1480, C_GREEN)]),
        ("TCP Segment (1480B)",    [("TCP Hdr (20B)", 20, C_PURPLE), ("TCP Payload / MSS (1460B)", 1460, '#10B981')]),
        ("IPsec Tünel (1500B)",    [("ESP Hdr (56B)", 56, C_RED), ("IP (20B)", 20, C_YELLOW), ("TCP (20B)", 20, C_PURPLE), ("MSS (1404B)", 1404, '#059669')])
    ]

    y_positions = [0.75, 0.52, 0.29, 0.08]
    for (layer_title, segments), y in zip(layers, y_positions):
        ax1.text(0.02, y + 0.12, layer_title, color='#F8FAFC', fontweight='bold', fontsize=10)
        curr_x = 0.02
        for seg_name, length, col in segments:
            # Genişlik logaritmik veya ölçekli
            norm_w = 0.94 * (math.log10(length + 1) / math.log10(1550))
            rect = plt.Rectangle((curr_x, y), norm_w, 0.09, facecolor=col, edgecolor='#FFFFFF', lw=1.2, alpha=0.9)
            ax1.add_patch(rect)
            if norm_w > 0.12:
                ax1.text(curr_x + norm_w/2., y + 0.045, f"{seg_name}", ha='center', va='center',
                         color='#0F172A', fontweight='bold', fontsize=8.5)
            curr_x += norm_w

    ax1.set_xlim(0.0, 1.0)
    ax1.set_ylim(0.0, 0.95)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # PANEL 2: IP Parçalanması ve Fragment Offset Şeması
    # --------------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(C_BG)
    ax2.set_title("PANEL 2: IP FRAGMENTATION VE FRAGMENT OFFSET (RFC 791)", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # 3 Parçanın Kutuları
    frag_data = [
        ("Orijinal Paket (4020B, MTU=1500)", 0.82, C_GRAY, "Payload: 4000B + 20B IPv4 Header (Sığmıyor -> Parçalanacak)"),
        ("Parça 1: Len=1500B", 0.60, C_GREEN, "Offset = 0 (0B) | MF = 1 | L4 TCP/UDP Başlığı Mevcut"),
        ("Parça 2: Len=1500B", 0.40, C_YELLOW, "Offset = 185 (1480B) | MF = 1 | L4 Başlığı YOK (Port Görünmez)"),
        ("Parça 3: Len=1060B", 0.20, C_PURPLE, "Offset = 370 (2960B) | MF = 0 (Son Parça) | L4 Başlığı YOK")
    ]

    for title, y, col, desc in frag_data:
        bbox_t = dict(boxstyle="square,pad=0.3", fc='#0F172A', ec=col, lw=1.5)
        bbox_d = dict(boxstyle="round,pad=0.3", fc=col, ec='#FFFFFF', lw=1.0)
        ax2.text(0.05, y, title, color='#F8FAFC', fontweight='bold', fontsize=9.5, bbox=bbox_t, va='center')
        ax2.text(0.50, y, desc, color='#0F172A', fontweight='bold', fontsize=8.5, bbox=bbox_d, va='center')

    # Oklar
    ax2.annotate("", xy=(0.25, 0.67), xytext=(0.25, 0.76), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=2))
    ax2.annotate("", xy=(0.25, 0.47), xytext=(0.25, 0.56), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=2))
    ax2.annotate("", xy=(0.25, 0.27), xytext=(0.25, 0.36), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=2))

    ax2.set_xlim(0.0, 1.0)
    ax2.set_ylim(0.1, 0.95)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # PANEL 3: ICMP Black Hole Krizi vs MSS Clamping Çözümü
    # --------------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor(C_BG)
    ax3.set_title("PANEL 3: ICMP BLACK HOLE KRIZI VS TCP MSS CLAMPING", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    scenarios = [
        "Normal Trafik\n(MTU=1500)",
        "Tünel + DF=1\n(ICMP Açık)",
        "ICMP Black Hole\n(Firewall Engeli)",
        "MSS Clamping\n(iptables Kalkanı)"
    ]
    throughput = [100.0, 92.0, 0.0, 91.5] # Başarı / Throughput %
    cols = [C_GREEN, C_YELLOW, C_RED, C_BLUE]

    bars = ax3.bar(scenarios, throughput, color=cols, width=0.45, alpha=0.9)
    ax3.set_ylabel('Veri İletim Başarısı (%)', color='#F8FAFC', fontweight='bold')
    ax3.tick_params(colors='#94A3B8')
    ax3.grid(color='#334155', linestyle='--', alpha=0.5, axis='y')

    for bar, val, col in zip(bars, throughput, cols):
        h = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., h + 3, f"%{val:.1f}", 
                 ha='center', color=col, fontweight='bold', fontsize=10)

    ax3.text(2, 45, "BAGLANTI\nDONDU! (%0)", color=C_RED, fontweight='bold', fontsize=11, ha='center',
             bbox=dict(boxstyle="round,pad=0.3", fc='#0F172A', ec=C_RED, lw=1.5))
    ax3.set_ylim(0, 120)

    # --------------------------------------------------------------------------
    # PANEL 4: Tünel Protokol Ek Yükü ve Efektif MSS
    # --------------------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor(C_BG)
    ax4.set_title("PANEL 4: TUNEL TURUNE GORE EFEKTIF MSS VE OVERHEAD (BAYT)", 
                  color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    tun_names = ["Ethernet", "VLAN", "PPPoE", "GRE", "VXLAN", "IPsec", "WireGuard"]
    mss_vals = [1460, 1456, 1452, 1436, 1410, 1404, 1400]
    overheads = [0, 4, 8, 24, 50, 56, 60]

    x = np.arange(len(tun_names))
    width = 0.35

    rects1 = ax4.bar(x - width/2, mss_vals, width, label='Efektif MSS (Bayt)', color=C_BLUE, alpha=0.85)
    ax4_sub = ax4.twinx()
    rects2 = ax4_sub.bar(x + width/2, overheads, width, label='Tünel Ek Yükü (Bayt)', color=C_RED, alpha=0.85)

    ax4.set_ylabel('Efektif MSS (Bayt)', color=C_BLUE, fontweight='bold')
    ax4_sub.set_ylabel('Tünel Ek Yükü (Bayt)', color=C_RED, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(tun_names, color='#F8FAFC', fontweight='bold', fontsize=9)
    ax4.tick_params(colors='#94A3B8')
    ax4_sub.tick_params(colors='#94A3B8')
    ax4.grid(color='#334155', linestyle='--', alpha=0.5, axis='x')

    ax4.set_ylim(1300, 1500)
    ax4_sub.set_ylim(0, 80)

    plt.savefig(output_file, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Dashboard] 300 DPI Görselleştirme panosu başarıyla oluşturuldu: {output_file}")

# Doğrulama ve Çalıştırma
if 'PNG_FILE' not in globals():
    PNG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_141_mtu_fragmentation_ve_mss.png")

generate_dashboard(PNG_FILE)

print("")
print("[*] GÜN 141 Katı Doğrulama Testleri (Assertions) Başlatılıyor...")
assert os.path.exists(PNG_FILE), "HATA: PNG dosyası üretilemedi!"
png_size = os.path.getsize(PNG_FILE)
print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size:,} bayt.")
assert png_size > 100000, f"HATA: PNG dosya boyutu çok küçük ({png_size} bayt)!"

# Temel Mantık Doğrulamaları
assert NetworkOverheadEngine.calculate_mss(interface_mtu=1500, tunnel=TunnelType.NONE)['effective_mss'] == 1460
assert NetworkOverheadEngine.calculate_mss(interface_mtu=1500, tunnel=TunnelType.IPSEC_ESP)['effective_mss'] <= 1404
assert len(frags) == 3
assert apply_mss_clamping(1460, 1400) == 1360

print("")
print("[PASS] Gün 141: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")
```

## 11. 🔍 Kod İnceleme ve Çıktı Analizi

### Simülasyon Çıktılarının Kritik Değerlendirmesi:
1. **IP Parçalanması ve Başlık Dağılımı:**
   $3.500\text{ baytlık}$ veri $1500\text{ baytlık}$ MTU hattında 3 parçaya ayrılmıştır. Parça 1'in $1480\text{ bayt}$ veri ve L4 başlığını taşıdığı, Parça 2'nin $\text{Offset}=185$ ($1480/8$) ile L4 başlığı olmaksızın iletildiği, Parça 3'ün ise $\text{MF}=0$ ile akışı sonlandırdığı doğrulanmıştır.
2. **Kaskad Parça Kaybı Riski:**
   Parçalardan sadece birinin düşmesi durumunda tüm $3.500\text{ baytlık}$ verinin alıcı çekirdeğince imha edildiği kanıtlanmıştır.
3. **ICMP Black Hole ve MSS Clamping Başarımı:**
   $1400\text{ baytlık}$ tünelde `DF=1` paketleri ICMP engeli yüzünden %0 başarıyla düşerken, `MSS Clamping` kuralı ile MSS $1360\text{ bayta}$ kelepçelendiğinde FLIR video akışının **%100 başarıyla** ulaştığı doğrulanmıştır.

## 12. ⚠️ Sık Yapılan Hatalar ve Anti-Pattern'ler

### 1. Güvenlik Duvarında Tüm ICMP Trafiğini Kapatmak
- **Anti-Pattern:** Güvenlik ekiplerinin ağdaki tüm ICMP paketlerini (Echo Request ile birlikte Type 3 Code 4 Destination Unreachable'ı da) körlemesine yasaklaması.
- **Sonuç:** PMTUD çöker; VPN ve tünel kullanan istemcilerin büyük paketli bağlantıları donar (ICMP Black Hole).
- **Doğru Yaklaşım:** `ICMP Type 3, Code 4 (Fragmentation Needed)` mesajlarına kesinlikle izin verilmelidir.

### 2. UDP Soketlerinde MTU'dan Büyük Datagram Basmak
- **Anti-Pattern:** Geliştiricinin UDP soketinde tek bir `sendto()` ile $8192\text{ bayt}$ telemetri göndermesi.
- **Sonuç:** Paket IP düzeyinde 6 parçaya bölünür. Telsiz hattında tek bir parça düşerse tüm datagram yok olur (Kayıp olasılığı 6 katına çıkar).
- **Doğru Yaklaşım:** UDP paketleri her zaman $1400\text{ baytın}$ altında tutulmalıdır.

### 3. Tünel Yönlendiricilerinde MSS Clamping Yapmamak
- **Anti-Pattern:** IPsec veya WireGuard tüneli kurup uç sistemlerin MSS değerine müdahale etmemek.
- **Sonuç:** Kullanıcılar web sitelerine veya komuta kontrol sunucularına bağlanabilir (küçük HTML yüklenir) ancak dosya indirme veya video akışı anında donar.

## 13. 🎯 Mülakat Soruları ve Savunma Sanayii Senaryoları

### Soru 1: TCP Neden IP Parçalanmasından Kaçar ve MSS Boyutunda Kendi Segmentasyonunu Yapar?
**Cevap:**  
Eğer parçalanma IP katmanında yapılırsa, IP'nin kayıp kurtarma mekanizması olmadığı için tek bir parça düştüğünde tüm segment çöpe gider ve TCP tüm paketi baştan yollar. Ayrıca 2. ve sonraki parçalarda TCP başlığı (port numaraları) bulunmadığı için NAT ve güvenlik duvarları paketleri düşürebilir. TCP, veriyi en baştan `MSS` sınırında segmentlere bölerek hem IP parçalanmasını sıfıra indirir hem de kayıpların sadece o segment özelinde telafi edilmesini sağlar.

### Soru 2: ICMP Black Hole Nedir ve Nasıl Teşhis Edilir?
**Cevap:**  
Göndericinin `DF=1` ile MTU'dan büyük bir paket yollaması, ara yönlendiricinin paketi düşürüp `ICMP Type 3 Code 4` üretmesi ancak bu ICMP mesajının bir güvenlik duvarınca engellenmesi sonucu göndericinin paketin düştüğünü anlayamaması ve bağlantının asılı kalmasıdır. Teşhisi: Küçük paketler (ping, HTTP GET) sorunsuz çalışırken, büyük veri aktarımlarında (I-Frame video, POST isteği) TCP bağlantısının `Retransmission` fırtınasına girip kilitlenmesidir. Çözümü `MSS Clamping` veya `PLPMTUD`'dur.

## 14. 🏗️ Projeye Entegrasyon ve Mimari Karar Matrisi

### MTU ve MSS Tasarım Karar Tablosu

```
                         [Taktik Ağ Bağlantısı]
                                   |
         +-------------------------+-------------------------+
         |                                                   |
   [Yalın Ethernet]                                   [Tünelli / VPN Hattı]
         |                                                   |
   MTU = 1500B                                        1. Path MTU Keşfi (PMTUD)
   MSS = 1460B                                        2. iptables TCPMSS Clamping
   DF = 1                                             3. net.ipv4.tcp_mtu_probing = 1
                                                      4. UDP Payload <= 1400B
```

| Parametre | Standart Değer | Taktik / Tünelli Ağ Önerisi | Mimari Gerekçe |
|:---|:---|:---|:---|
| `tcp_mtu_probing` | 0 (Kapalı) | **1 (PLPMTUD Açık)** | ICMP engellense bile TCP kendi MTU'sunu dinamik keşfeder. |
| iptables Kuralı | Yok | `--clamp-mss-to-pmtu` | SYN aşamasında MSS'i zorla küçülterek parçalanmayı önler. |
| UDP Güvenli Sınır| 65,507B | **<= 1400B (İdeal 1200B)** | IP parçalanmasını ve kaskad kayıpları sıfırlar. |

## 15. 📝 Gün Sonu Özeti ve 3 Temel Çıkarım

1. **MTU Hat Sınırıdır, MSS İse TCP Veri Sınırıdır:** $\text{MSS} = \text{MTU} - (\text{IP} + \text{TCP})$ bağıntısı asla ihlal edilemez. Standart sınır $1460\text{ bayttır}$.
2. **IP Parçalanması Performans Katilidir:** Tek parça kaybı tüm paketi yok eder ve portsuz parçalar güvenlik duvarlarına takılır.
3. **MSS Clamping Tünellerin Can Simididir:** Kripto tünellerinde ortaya çıkan ICMP Black Hole felaketi, `SYN` el sıkışmasında MSS'in güvenli sınıra kelepçelenmesiyle çözülür.

## 16. 🚀 Gelecek Perspektifi: Yarının Konusu

Yarın **Gün 142'de: "TCP Head-of-Line Blocking ve Nagle" (Kuyruk Başı Tıkanması ve Nagle Algoritması)** konusuna geçeceğiz:
- Tek bir kayıp paketin arkasındaki tüm bağımsız telemetri akışlarını dondurması (**Head-of-Line Blocking - HoL**),
- HTTP/2'nin TCP üzerindeki HoL zaafı ve HTTP/3 (QUIC/UDP) devriminin ortaya çıkış nedeni,
- Nagle algoritması ile Delayed ACK çakışmasının gerçek zamanlı robotik/aviyonik sistemlerdeki gecikme anatomisi.

## 17. 📜 Özel Lisans Bildirimi

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

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
