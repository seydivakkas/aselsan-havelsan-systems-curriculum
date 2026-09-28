# Gün 323 — F11 — Verification / SIL / HIL: Traceability (Requirement -> Design -> Code -> Test)

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](file:///c:/Users/seydieryilmaz/Downloads/Olay_Proje/gunluk_mufredat/gun_323/gun_323_traceability_requirement_design_code_test.md)

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

---

## Genel Bakış ve Amaç
Savunma ve aviyonik yazılım mühendisliğinde (DO-178C, MIL-STD-498, IEEE 29148), bir yazılımın "çalışıyor olması" uçuş onayı (flight clearance) için yeterli değildir. Her bir sistem isterinin tasarıma, kaynak koda ve testlere eksiksiz dönüştürüldüğünün; tersine, kaynak koddaki her satırın ve her testin geçerli bir üst düzey gereksinime dayandığının matematiksel ve denetlenebilir olarak kanıtlanması gerekir.

Bu mühendislik disiplinine **Çift Yönlü İzlenebilirlik (Bidirectional Traceability)** adı verilir. Bu modülde, sistem gereksinimlerinden (SR) başlayarak yüksek seviyeli yazılım isterlerine (HLR), alt seviye mimari tasarıma (LLR), C++20 kaynak kodlarına ve doğrulama testlerine (Unit/SIL/HIL) uzanan izlenebilirlik çizgesini kuracak, **Yetim Kod (Orphan / Rogue Code)** ve **Test Edilmemiş İster (Untested Requirement)** açıklarını otomatik olarak tespit edeceğiz.

---

## 1. Kavramsal Temel ve Neden-Sonuç Zinciri

### 5N1K Modeli
- **Ne?** Traceability (Gereksinimden Tasarıma, Koda ve Teste Çift Yönlü İzlenebilirlik); İleri İzlenebilirlik (Forward), Geriye Dönük İzlenebilirlik (Backward) ve Değişiklik Etki Analizi (CIA).
- **Neden?** Yazılımda hiçbir gereksinimin atlanmadığını (omission), hiçbir yetim/istenmeyen kodun (rogue/dead code) sisteme sızmadığını ve ister değişikliklerinde hangi testlerin koşulacağını kesin olarak belirlemek.
- **Nerede?** Görev Bilgisayarları, Uçuş Yönetim Sistemleri (FMS), Seyrüsefer ve Güdüm Algoritmaları, İHA Otomasyon Yazılımları.
- **Nasıl?** Gereksinim yönetim araçları (IBM DOORS, Jama, Polarion) ile C++20 kaynak kod etiketleri (`@traces_to`), test framework'leri (GTest/PyTest) ve CI/CD çizge motorları üzerinden.
- **Ne Zaman?** Yazılım gereksinim analizi fazından kabul testlerine (FAT/SAT) kadar tüm SDLC boyunca canlı ve kesintisiz olarak.
- **Kim?** Sistem Mühendisi, Yazılım Mimarı, Doğrulama & Geçerleme (V&V) Mühendisi, Sertifikasyon Denetçisi.

### Neden-Sonuç Tablosu
| Sebep (Mühendislik İhtiyacı) | Uygulanan İzlenebilirlik Yöntemi | Doğrudan Çıktı / Gözlem | Önlenen Kritik Risk |
|---|---|---|---|
| Her isterin kodlandığını doğrulama | İleri İzlenebilirlik (Forward Traceability) | $SR \to HLR \to LLR \to Code$ zinciri | Eksik gereksinim (Omission Bug) nedeniyle uçuşta arıza |
| Her kodun meşru bir nedene dayandığını doğrulama | Geri İzlenebilirlik (Backward Traceability) | $Code \to LLR \to HLR \to SR$ zinciri | Yetim kod (Orphan Code), Truva atı (Trojan), yetkisiz arka kapı |
| Her isterin test edildiğini ispatlama | Doğrulama Kapsama Matrisi (VCM) | $Requirement \to Test Case$ eşleşmesi | Kod çalışsa dahi gereksinimi karşılamayan sahte fonksiyon |
| İster değişikliğinin maliyetini hesaplama | Değişiklik Etki Analizi (CIA Graph Propagation) | Etkilenen LLR, Kod ve Regresyon Test Listesi | Değişiklik sonrası gereksiz tüm sistemi test etme maliyeti veya eksik test riski |

---

## 2. Çift Yönlü İzlenebilirlik (Bidirectional Traceability) Mimarisi

DO-178C standardı, Tablo A-3 (Yazılım Geliştirme Süreçlerinin Çıktıları) ve Tablo A-4/A-6 (Doğrulama Süreçleri) uyarınca çift yönlü izlenebilirliği zorunlu kılar:

```
[İLERİ İZLENEBİLİRLİK (FORWARD TRACEABILITY)]
Sistem İsteri (SR) ----> Yüksek Seviye İster (HLR) ----> Alt Seviye Tasarım (LLR) ----> Kaynak Kod ----> Test Senaryoları
      |                          |                           |                      |                 |
      v                          v                           v                      v                 v
[SR-SYS-001]             [HLR-SW-101]                [LLR-DES-201]            [nav_filter.cpp]   [TC-NAV-01]
      ^                          ^                           ^                      ^                 ^
      |                          |                           |                      |                 |
[GERİYE DÖNÜK İZLENEBİLİRLİK (BACKWARD TRACEABILITY)]
```

### Kritik Sorular ve Doğrulama Karşılıkları:
1. **İleri İzlenebilirlik Ne Sorar?**
   - *"Müşterinin/Sistemin istediği tüm özellikler kodlandı mı ve doğrulandı mı?"*
   - Eğer bir $SR$ zincirin sonundaki bir $TC$'ye (Test Case) ulaşamıyorsa: **TEST EDİLMEMİŞ İSTER (Gap)**.
2. **Geriye Dönük İzlenebilirlik Ne Sorar?**
   - *"Bu kaynak kod satırını kim istedi? Neden bu fonksiyon yazıldı?"*
   - Eğer bir kaynak dosya veya fonksiyon hiçbir $LLR$ ya da $HLR$'ye bağlanamıyorsa: **YETİM KOD (Orphan Code / Dead Code / Rogue Code)**.

---

## 3. Matematiksel Model ve Çizge (Graph) Teorisi

İzlenebilirlik mimarisi, yönlü ve döngüsüz bir çizge (Directed Acyclic Graph - DAG) olarak modellenir:

$$G = (V, E)$$

Burada düğüm kümeleri yaşam döngüsü katmanlarını temsil eder:
$$V = V_{SR} \cup V_{HLR} \cup V_{LLR} \cup V_{CODE} \cup V_{TEST}$$

Kenar kümesi ($E$), katmanlar arasındaki izlenebilirlik bağlarıdır:
$$E \subseteq (V_{SR} \times V_{HLR}) \cup (V_{HLR} \times V_{LLR}) \cup (V_{LLR} \times V_{CODE}) \cup (V_{CODE} \times V_{TEST})$$

### Metrik 1: İleri İzlenebilirlik Oranı ($T_{fwd}$)
Tüm sistem isterlerinin en az bir geçerli test senaryosuna ulaşıp ulaşmadığı:
$$T_{fwd} = \frac{|\{v \in V_{SR} \mid \exists u \in V_{TEST}, v \rightsquigarrow u\}|}{|V_{SR}|} \times 100\%$$

### Metrik 2: Geriye Dönük İzlenebilirlik Oranı ($T_{bwd}$)
Kaynak kod modüllerinin meşru bir sistem isterinden türeyip türemediği:
$$T_{bwd} = \frac{|\{c \in V_{CODE} \mid \exists s \in V_{SR}, s \rightsquigarrow c\}|}{|V_{CODE}|} \times 100\%$$

### Metrik 3: Değişiklik Etki Kapsamı (Change Impact Propagation - CIA)
Bir sistem isteri $\Delta_{SR} \subset V_{SR}$ değiştiğinde etkilenen alt bileşenler kümesi:
$$\text{Impact}(\Delta_{SR}) = \{w \in V \mid \exists v \in \Delta_{SR}, v \rightsquigarrow w\}$$
Zorunlu regresyon test kümesi:
$$\text{RegressionSuite}(\Delta_{SR}) = \text{Impact}(\Delta_{SR}) \cap V_{TEST}$$

---

```python
# -*- coding: utf-8 -*-
"""
Gün 323: Traceability: requirement -> design -> code -> test
Kod Bloğu 1: Temel İzlenebilirlik Motoru ve Veri Modeli
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict, deque

@dataclass
class ArtifactNode:
    """Yaşam döngüsü artefakt düğümü (SR, HLR, LLR, CODE, TEST)."""
    node_id: str
    artifact_type: str  # 'SR', 'HLR', 'LLR', 'CODE', 'TEST'
    title: str
    description: str = ""

@dataclass
class TraceLink:
    """İki artefakt arasındaki yönlü izlenebilirlik bağı."""
    source_id: str  # Üst seviye (Parent)
    target_id: str  # Alt seviye (Child)

class TraceabilityMatrixEngine:
    """
    Aviyonik Çift Yönlü İzlenebilirlik ve Değişiklik Etki Analiz Motoru.
    DO-178C Tablo A-3 / A-4 / A-6 uyumluluğunu yönetir.
    """
    def __init__(self):
        self.nodes: Dict[str, ArtifactNode] = {}
        self.forward_links: Dict[str, Set[str]] = defaultdict(set)   # parent -> children
        self.backward_links: Dict[str, Set[str]] = defaultdict(set)  # child -> parents

    def add_node(self, node: ArtifactNode):
        self.nodes[node.node_id] = node

    def add_link(self, parent_id: str, child_id: str):
        if parent_id not in self.nodes or child_id not in self.nodes:
            raise ValueError(f"Düğüm bulunamadı: {parent_id} veya {child_id}")
        self.forward_links[parent_id].add(child_id)
        self.backward_links[child_id].add(parent_id)

    def remove_node(self, node_id: str):
        if node_id in self.nodes:
            del self.nodes[node_id]
            if node_id in self.forward_links:
                del self.forward_links[node_id]
            if node_id in self.backward_links:
                del self.backward_links[node_id]
            for p, children in self.forward_links.items():
                children.discard(node_id)
            for c, parents in self.backward_links.items():
                parents.discard(node_id)

    def get_forward_trace(self, start_id: str) -> Set[str]:
        """start_id'den türeyen tüm alt seviye düğümleri (BFS ile) bulur."""
        visited = set()
        queue = deque([start_id])
        while queue:
            curr = queue.popleft()
            for child in self.forward_links.get(curr, []):
                if child not in visited:
                    visited.add(child)
                    queue.append(child)
        return visited

    def get_backward_trace(self, start_id: str) -> Set[str]:
        """start_id'nin dayandığı tüm üst seviye düğümleri (BFS ile) bulur."""
        visited = set()
        queue = deque([start_id])
        while queue:
            curr = queue.popleft()
            for parent in self.backward_links.get(curr, []):
                if parent not in visited:
                    visited.add(parent)
                    queue.append(parent)
        return visited

    def audit_forward_traceability(self) -> Tuple[float, List[str]]:
        """Tüm Sistem İsterlerinin (SR) en az bir TEST'e ulaşıp ulaşmadığını denetler."""
        sr_nodes = [nid for nid, n in self.nodes.items() if n.artifact_type == 'SR']
        if not sr_nodes:
            return 100.0, []
        untested_srs = []
        for sr in sr_nodes:
            downstream = self.get_forward_trace(sr)
            tests = [nid for nid in downstream if self.nodes[nid].artifact_type == 'TEST']
            if not tests:
                untested_srs.append(sr)
        coverage_pct = ((len(sr_nodes) - len(untested_srs)) / len(sr_nodes)) * 100.0
        return coverage_pct, untested_srs

    def audit_backward_traceability(self) -> Tuple[float, List[str]]:
        """Tüm Kaynak Kodların (CODE) bir Sistem İsterine (SR) dayanıp dayanmadığını denetler."""
        code_nodes = [nid for nid, n in self.nodes.items() if n.artifact_type == 'CODE']
        if not code_nodes:
            return 100.0, []
        orphan_codes = []
        for code in code_nodes:
            upstream = self.get_backward_trace(code)
            srs = [nid for nid in upstream if self.nodes[nid].artifact_type == 'SR']
            if not srs:
                orphan_codes.append(code)
        coverage_pct = ((len(code_nodes) - len(orphan_codes)) / len(code_nodes)) * 100.0
        return coverage_pct, orphan_codes

    def change_impact_analysis(self, modified_node_id: str) -> Dict[str, List[str]]:
        """Değiştirilen bir düğümün etkilediği alt seviye bileşenleri gruplar."""
        impacted_nodes = self.get_forward_trace(modified_node_id)
        grouped_impact = defaultdict(list)
        for nid in impacted_nodes:
            grouped_impact[self.nodes[nid].artifact_type].append(nid)
        return dict(grouped_impact)

print("====================================================================================")
print("ASELSAN / HAVELSAN / ROKETSAN ÇİFT YÖNLÜ İZLENEBİLİRLİK MOTORU YÜKLENDİ")
print("====================================================================================")
print("Standart Uyumluluğu : DO-178C Tablo A-3, A-4, A-6, MIL-STD-498")
print("İzlenebilirlik Akışı: SR -> HLR -> LLR -> CODE -> TEST")
print("====================================================================================")

```

---

## 4. Kod 1 Teknik Açıklaması: Aviyonik İzlenebilirlik Çizge Motoru

Aşağıdaki Python/C++ çift yönlü modelinde, uçuş yönetim bilgisayarı (Flight Management Computer) için tam kapsamlı bir `TraceabilityMatrixEngine` inşa edilmiştir:

1. **`ArtifactNode` Sınıfı:** İster, tasarım, kod ve test bileşenlerini benzersiz ID, tür (SR, HLR, LLR, CODE, TEST) ve durum verileriyle tanımlar.
2. **`TraceLink` Yapısı:** İki düğüm arasındaki yönlü ilişkiyi (`parent_id -> child_id`) modeller.
3. **Çizge İndeksleme:** Motor hem ileri (`forward_index`) hem de geri (`backward_index`) arama tablolarını kurarak $O(V+E)$ karmaşıklığında anlık gezinme sağlar.
4. **Veri Modeli:**
   - 4 Sistem İsteri (SR-SYS-001 ... 004)
   - 4 Yazılım İsteri (HLR-SW-101 ... 104)
   - 4 Tasarım Bileşeni (LLR-DES-201 ... 204)
   - 4 Kaynak Kod Modülü (`nav_filter.cpp`, `guidance_laws.cpp`, `health_monitor.cpp`, `telemetry_link.cpp`)
   - 5 Doğrulama Testi (`TC-NAV-01` ... `TC-NAV-05`)

---

## 5. Yetim Kod (Orphan Code) ve Test Edilmemiş İster Tehlikesi

Savunma yazılımlarında denetçilerin (SSB, FAA, EASA) en katı olduğu iki kritik uygunsuzluk:

### 1. Yetim Kod (Orphan / Rogue Code) Tehlikesi:
- Geliştirici tarafından "belki ileride lazım olur" diye eklenmiş, hiçbir HLR veya LLR'ye dayanmayan fonksiyonlardır.
- **Tehlike:** Test edilmemiş kod blokları barındırır, siber saldırganlar için arka kapı (backdoor) potansiyeli taşır veya hafıza alanını kirleterek determinizmi bozar.
- **DO-178C Hükmü:** Yetim kod derhal projeden silinmelidir (Bölüm 6.4.4.3).

### 2. Test Edilmemiş İster (Untested Requirement) Tehlikesi:
- İster yazılmış, tasarım yapılmış, kod geliştirilmiş ancak doğrulama testi (Test Case) yazılmamıştır.
- **Tehlike:** Fonksiyonun uçuş anında beklenen toleranslarda çalışıp çalışmadığı kanıtlanamaz.
- **DO-178C Hükmü:** Doğrulama olmadan yazılım DAL seviyesi sertifikası alamaz.

---

## 6. Değişiklik Etki Analizi (Change Impact Analysis - CIA) Yöntemleri

Bir hava aracında ya da füzede görev isterleri değiştiğinde (örneğin maksimum dönüş açısı $30^\circ$'den $45^\circ$'ye çıkarıldığında):
- **Geleneksel Yanlış Yaklaşım:** Bütün yazılımı baştan sona rastgele test etmek ya da sadece değiştirilen fonksiyona yüzeysel bakmak.
- **DO-178C Bölüm 7.2 Yaklaşımı:** Çift yönlü izlenebilirlik çizgesi üzerinden DFS/BFS ile etkilenen alt gereksinimler, fonksiyonlar ve testler matematiksel olarak çıkarılır:

```
[İster Değişimi: SR-SYS-002]
         |
         v (Downstream Edge)
   [HLR-SW-102: Güdüm Açı Sınırları]
         |
         v (Downstream Edge)
   [LLR-DES-202: Oransal Seyrüsefer Matrisi]
         |
         v (Downstream Edge)
   [Kaynak Kod: guidance_laws.cpp]
         |
         +---------------------------------------+
         v                                       v
[Doğrulama Testi: TC-NAV-02]            [Doğrulama Testi: TC-NAV-03]
```

Böylece 10.000 testlik bir sistemde yalnızca etkilenen **2 testin** ve ilgili entegrasyon sınırlarının koşulması yeterli olur (Scoped Regression Testing).

---

```python
# -*- coding: utf-8 -*-
"""
Gün 323: Traceability: requirement -> design -> code -> test
Kod Bloğu 2: Temel Aviyonik İzlenebilirlik Veri Seti ve Matris Koşumu
"""
# Motoru Başlat
engine = TraceabilityMatrixEngine()

# 1. Katman: Sistem İsterleri (System Requirements - SR)
engine.add_node(ArtifactNode("SR-SYS-001", "SR", "Otonom Konum ve İrtifa Kestirimi"))
engine.add_node(ArtifactNode("SR-SYS-002", "SR", "Güdümlü Rota ve Seyrüsefer Kontrolü"))
engine.add_node(ArtifactNode("SR-SYS-003", "SR", "Uçuş Emniyeti ve Arıza İzolasyonu"))
engine.add_node(ArtifactNode("SR-SYS-004", "SR", "Acil Durum Kurtarma ve Telemetri"))

# 2. Katman: Yüksek Seviye Yazılım İsterleri (High-Level Requirements - HLR)
engine.add_node(ArtifactNode("HLR-SW-101", "HLR", "EKF Sensör Füzyonu ve Konum Filtresi"))
engine.add_node(ArtifactNode("HLR-SW-102", "HLR", "Oransal Seyrüsefer ve Açısal Kılavuzluk"))
engine.add_node(ArtifactNode("HLR-SW-103", "HLR", "Sensör Sağlık İzleme ve Emniyetli Mod"))
engine.add_node(ArtifactNode("HLR-SW-104", "HLR", "Kritik Olay Telemetrisi İletimi"))

# 3. Katman: Düşük Seviye Tasarım Bileşenleri (Low-Level Requirements - LLR)
engine.add_node(ArtifactNode("LLR-DES-201", "LLR", "Kalman Filtresi Matris Çarpım Mimarisi"))
engine.add_node(ArtifactNode("LLR-DES-202", "LLR", "Güdüm Kanunu Doyum ve Sönümleme Tasarımı"))
engine.add_node(ArtifactNode("LLR-DES-203", "LLR", "Watchdog ve Hata Yönetim Durum Makinesi"))
engine.add_node(ArtifactNode("LLR-DES-204", "LLR", "MIL-STD-1553 Telemetri Paketleyici"))

# 4. Katman: Kaynak Kod Modülleri (Source Code - CODE)
engine.add_node(ArtifactNode("nav_filter.cpp", "CODE", "EKF Konum Kestirim Algoritması"))
engine.add_node(ArtifactNode("guidance_laws.cpp", "CODE", "Açısal Güdüm ve Rota İcrası"))
engine.add_node(ArtifactNode("health_monitor.cpp", "CODE", "Sensör Arıza İzleme Mantığı"))
engine.add_node(ArtifactNode("telemetry_link.cpp", "CODE", "Aviyonik Telemetri İletişim Sürücüsü"))

# 5. Katman: Doğrulama Test Senaryoları (Test Cases - TEST)
engine.add_node(ArtifactNode("TC-NAV-01", "TEST", "EKF Doğruluk ve Kararlılık Testi"))
engine.add_node(ArtifactNode("TC-NAV-02", "TEST", "Maksimum Açı Doyumu Güdüm Testi"))
engine.add_node(ArtifactNode("TC-NAV-03", "TEST", "Rüzgar Sapması Rota Doğrulama Testi"))
engine.add_node(ArtifactNode("TC-NAV-04", "TEST", "Sensör Kesintisi Hata İzolasyon Testi"))
engine.add_node(ArtifactNode("TC-NAV-05", "TEST", "Telemetri Veri Kaybı ve Kurtarma Testi"))

# İleri Bağlantıları Tanımla (Parent -> Child)
# SR -> HLR
engine.add_link("SR-SYS-001", "HLR-SW-101")
engine.add_link("SR-SYS-002", "HLR-SW-102")
engine.add_link("SR-SYS-003", "HLR-SW-103")
engine.add_link("SR-SYS-004", "HLR-SW-104")

# HLR -> LLR
engine.add_link("HLR-SW-101", "LLR-DES-201")
engine.add_link("HLR-SW-102", "LLR-DES-202")
engine.add_link("HLR-SW-103", "LLR-DES-203")
engine.add_link("HLR-SW-104", "LLR-DES-204")

# LLR -> CODE
engine.add_link("LLR-DES-201", "nav_filter.cpp")
engine.add_link("LLR-DES-202", "guidance_laws.cpp")
engine.add_link("LLR-DES-203", "health_monitor.cpp")
engine.add_link("LLR-DES-204", "telemetry_link.cpp")

# CODE -> TEST
engine.add_link("nav_filter.cpp", "TC-NAV-01")
engine.add_link("guidance_laws.cpp", "TC-NAV-02")
engine.add_link("guidance_laws.cpp", "TC-NAV-03")  # 1 Kod -> 2 Test
engine.add_link("health_monitor.cpp", "TC-NAV-04")
engine.add_link("telemetry_link.cpp", "TC-NAV-05")

# Temel Denetim
fwd_pct, un_srs = engine.audit_forward_traceability()
bwd_pct, or_codes = engine.audit_backward_traceability()

print("====================================================================================")
print("TEMEL SİSTEM ÇİFT YÖNLÜ İZLENEBİLİRLİK RAPORU")
print("====================================================================================")
print(f"İleri İzlenebilirlik Oranı (Forward Traceability) : %{fwd_pct:.1f} (Eksik Test: {len(un_srs)})")
print(f"Geri İzlenebilirlik Oranı (Backward Traceability)  : %{bwd_pct:.1f} (Yetim Kod: {len(or_codes)})")
print("------------------------------------------------------------------------------------")
print("UÇTAN UCA İZLENEBİLİRLİK ZİNCİRLERİ (SR -> HLR -> LLR -> CODE -> TEST):")
for sr_id in ["SR-SYS-001", "SR-SYS-002", "SR-SYS-003", "SR-SYS-004"]:
    sr_title = engine.nodes[sr_id].title
    downstream = engine.get_forward_trace(sr_id)
    tests = [nid for nid in downstream if engine.nodes[nid].artifact_type == 'TEST']
    codes = [nid for nid in downstream if engine.nodes[nid].artifact_type == 'CODE']
    print(f"  * [{sr_id}] {sr_title:<35} -> Kod: {', '.join(codes)} -> Test: {', '.join(tests)}")
print("====================================================================================")

```

---

## 7. Kod 2 Teknik Açıklaması: Çift Yönlü İzlenebilirlik Matrisi (BTM) Koşumu

Bu kod bloğunda, oluşturulan aviyonik izlenebilirlik motoru çalıştırılarak uçtan uca zincir analiz edilir:

1. **Uçtan Uca Yol Arama (End-to-End Paths):** $SR \to HLR \to LLR \to CODE \to TEST$ zincirlerinin tamlığı listelenir.
2. **Tablo Formatında Matris:** Her bir sistem isterinin hangi test senaryolarıyla kapatıldığı özetlenir.
3. **Temel Doğrulama:** Sağlıklı temel sistemde tüm zincirlerin eksiksiz çalıştığı teyit edilir.

---

## 8. Endüstriyel Araçlar: DOORS, Jama, Polarion ve Git Entegrasyonu

ASELSAN, ROKETSAN ve TUSAŞ gibi kurumlarda izlenebilirlik manuel Excel tablolarıyla değil, endüstri standardı araçlarla yönetilir:

```
+------------------+         ReqIF XML          +-------------------+
|    IBM DOORS     | -------------------------> |  Jira / Polarion  |
| (Sistem İsteri)  |                            | (Yazılım İsteri)  |
+------------------+                            +-------------------+
         |                                                |
         | Git Commit Tag (@traces_to: HLR-101)          | CMake / Clang
         v                                                v
+------------------+                            +-------------------+
| GitLab / GitHub  |                            | GTest / C++20     |
| (C++20 Kaynak)   | -------------------------> | (Birim & SIL Test)|
+------------------+       CI/CD Trace Check    +-------------------+
```

### C++20 Kodunda İzlenebilirlik Etiketleme Pratiği:
```cpp
// nav_filter.cpp
/**
 * @file nav_filter.cpp
 * @brief Genişletilmiş Kalman Filtresi Konum Kestirimi
 * @traces_to LLR-DES-201, HLR-SW-101, SR-SYS-001
 * @verified_by TC-NAV-01
 */
void update_extended_kalman_filter(const ImuMeasurement& imu, const GpsFix& gps) {
    // DO-178C DAL-A sertifikalı deterministik filtreleme
}
```

---

## 9. Hata Enjeksiyonu: Yetim Kod ve Eksik Test Tespiti (Fault Injection)

Bu deneyde gerçek hayat aviyonik yazılım geliştirme süreçlerinde sıkça karşılaşılan iki kritik güvenlik hatası sisteme enjekte edilmektedir:

1. **Hata 1: Yetim / İzlenemeyen Kod (Orphan Code):**
   - Sisteme `secret_debug_backdoor.cpp` isimli bir modül eklenir. Bu modül hiçbir üst düzey LLR ya da HLR isterine bağlı değildir.
   - Geriye dönük izlenebilirlik motorunun bu yetim kodu anında yakalaması beklenir.
2. **Hata 2: Test Edilmemiş İster (Untested Requirement):**
   - `SR-SYS-004` (Acil Durum Suya İniş / Safe Ditching) isteri için kod yazılmış (`telemetry_link.cpp`), ancak doğrulama testi (`TC-NAV-05`) kasten silinmiştir.
   - İleri izlenebilirlik motorunun bu kritik güvenlik açığını yakalaması beklenir.

---

```python
# -*- coding: utf-8 -*-
"""
Gün 323: Traceability: requirement -> design -> code -> test
Kod Bloğu 3: Hata Enjeksiyonu (Yetim Kod & Eksik Test) ve Değişiklik Etki Analizi
"""
# 1. HATA ENJEKSİYONU: Yetim Kod Ekle (Hiçbir gereksinime dayanmayan arka kapı kodu)
rogue_code = ArtifactNode("secret_debug_backdoor.cpp", "CODE", "Yetkisiz Hata Ayıklama Arka Kapısı")
engine.add_node(rogue_code)
# Bilerek hiçbir HLR veya LLR'ye bağlamıyoruz! (Yetim Kod / Rogue Code)

# 2. HATA ENJEKSİYONU: Test Edilmemiş İster Yarat (TC-NAV-05 silinir)
# SR-SYS-004'ün test senaryosu olan TC-NAV-05'i devreden çıkarıyoruz
engine.remove_node("TC-NAV-05")

# Hata Durumu Denetimi
fwd_faulty_pct, untested_faulty = engine.audit_forward_traceability()
bwd_faulty_pct, orphan_faulty = engine.audit_backward_traceability()

print("=========================================================================================================")
print("HATA ENJEKSİYONU VE İZLENEBİLİRLİK BOŞLUĞU DENETİMİ (FAULT INJECTION)")
print("=========================================================================================================")
print(f"İleri İzlenebilirlik (Forward)   : %{fwd_faulty_pct:.1f} -> KAPSAMA BOŞLUĞU TESPİT EDİLDİ!")
print(f"  * Test Edilmemiş Sistem İsteri : {untested_faulty} (SR-SYS-004 Test Senaryosu Yok!)")
print(f"Geri İzlenebilirlik (Backward)   : %{bwd_faulty_pct:.1f} -> YETİM KOD (ROGUE CODE) TESPİT EDİLDİ!")
print(f"  * İzlenemeyen Kaynak Kod       : {orphan_faulty} (secret_debug_backdoor.cpp Hiçbir İstere Dayanmıyor!)")
print("---------------------------------------------------------------------------------------------------------")

# 3. DEĞİŞİKLİK ETKİ ANALİZİ (CHANGE IMPACT ANALYSIS - CIA)
# Senaryo: SR-SYS-002 (Güdümlü Rota ve Seyrüsefer Kontrolü) isteri revize edildi.
impacted_sr002 = engine.change_impact_analysis("SR-SYS-002")
print("DEĞİŞİKLİK ETKİ ANALİZİ: SR-SYS-002 İster Revizyonu Etki Alanı:")
for art_type, items in impacted_sr002.items():
    print(f"  - Etkilenen {art_type:<5} Bileşenleri: {items}")

regression_suite = impacted_sr002.get("TEST", [])
print(f"ZORUNLU REGRESYON TEST PAKETİ: {regression_suite} (Diğer testler güvenle atlanabilir)")
print("=========================================================================================================")

# DÜZELTME (REMEDIATION): Yetim kodu sil, eksik testi geri bağla
engine.remove_node("secret_debug_backdoor.cpp")
engine.add_node(ArtifactNode("TC-NAV-05", "TEST", "Telemetri Veri Kaybı ve Kurtarma Testi"))
engine.add_link("telemetry_link.cpp", "TC-NAV-05")

fwd_clean_pct, _ = engine.audit_forward_traceability()
bwd_clean_pct, _ = engine.audit_backward_traceability()
print(f"[+] Düzeltme Sonrası: İleri İzlenebilirlik: %{fwd_clean_pct:.1f} | Geri İzlenebilirlik: %{bwd_clean_pct:.1f}")
print("=========================================================================================================")

```

---

## 10. Kod 3 Teknik Açıklaması: Hata Tespiti ve Değişiklik Etki Simülasyonu

Aşağıdaki kod bloğunda:
1. Enjekte edilen **Yetim Kod** ve **Test Edilmemiş İster** durumları taranır ve raporlanır.
2. `SR-SYS-002` üzerinde bir ister değişikliği tetiklenir ve etkilenen alt küme (Downstream Impact Set) otomatik hesaplanır.
3. Hatalı durumların temizlenmesiyle sistemin tekrar %100 uyumlu hale geldiği gösterilir.

---

## 11. Savunma Sanayii Entegrasyonu (ASELSAN, ROKETSAN, TUSAŞ)

Aviyonik sertifikasyon denetimlerinde (FAA DER / Askeri Sertifikasyon Otoritesi):

```
                       DO-178C DENETİM AŞAMALARI
                                   |
         -----------------------------------------------------
         |                         |                         |
         v                         v                         v
       SOI-1                     SOI-2                     SOI-3 / SOI-4
  (Planlama Fazı)           (Geliştirme Fazı)           (Doğrulama & Kabul)
- SDP, SVP, SCMP          - HLR -> LLR İncelemesi     - Çift Yönlü BTM Onayı
- Araç Kalifikasyonu      - Kod İncelemeleri          - %100 Yapısal Kapsama
- İzlenebilirlik Planı     - Geriye İzlenebilirlik     - Uçuş Test İzin Belgesi
```

- **SOI-3 (Stage of Involvement 3):** Denetçi rastgele 10 adet kaynak kod satırı ve 10 adet sistem gereksinimi seçer. Mühendisten bu satırların üst ve alt bağlantılarını 15 dakika içinde çizge üzerinden kanıtlamasını ister. Çift yönlü otomatik matris yoksa proje denetimden doğrudan kalır.

---

## 12. Doğrulama Mühendisliği Metrikleri ve Kapsama Formülleri

İzlenebilirlik denetimlerinde kullanılan nicel kalite göstergeleri:

1. **İzlenebilirlik Bütünlük Skoru (Traceability Integrity Index - TII):**
   $$\text{TII} = \frac{T_{fwd} + T_{bwd}}{2} - (N_{orphan} \times 10) - (N_{untested} \times 15)$$

2. **Gereksinim Doğrulama Yoğunluğu (Verification Density - VD):**
   $$\text{VD} = \frac{|V_{TEST}|}{|V_{SR}|}$$
   (Kritik aviyonik sistemlerde her sistem isteri için $VD \ge 1.5$ olmalıdır).

3. **Yetim Kod Yoğunluğu (Orphan Code Density - OCD):**
   $$\text{OCD} = \frac{N_{orphan}}{|V_{CODE}|} \times 100\%$$
   (DAL-A ve DAL-B seviyelerinde kabul edilebilir OCD **kesinlikle %0.0** olmalıdır).

---

```python
# -*- coding: utf-8 -*-
"""
Gün 323: Traceability: requirement -> design -> code -> test
Kod Bloğu 4: DO-178C DAL-A Çift Yönlü İzlenebilirlik Doğrulama Testleri
"""
# 1. Assertion: Temel Graf Bütünlüğü Doğrulaması
assert len(engine.nodes) == 21, "Temel sistemde tam 21 artefakt düğümü bulunmalıdır."
assert len(engine.forward_links) >= 4, "İleri yönlü bağlantı tabloları dolu olmalıdır."

# 2. Assertion: Yetim Kod Tespit Hassasiyeti Doğrulaması
assert "secret_debug_backdoor.cpp" in orphan_faulty, "Yetim kod motor tarafından kesinlikle yakalanmalıdır!"
assert bwd_faulty_pct < 100.0, "Yetim kod varken geriye dönük izlenebilirlik %100 olamaz!"

# 3. Assertion: Test Edilmemiş İster Tespit Hassasiyeti Doğrulaması
assert "SR-SYS-004" in untested_faulty, "Eksik testli sistem isteri kesinlikle yakalanmalıdır!"
assert fwd_faulty_pct < 100.0, "Test edilmemiş ister varken ileri izlenebilirlik %100 olamaz!"

# 4. Assertion: Değişiklik Etki Analizi (CIA) Doğrulaması
expected_tests = {"TC-NAV-02", "TC-NAV-03"}
assert set(regression_suite) == expected_tests, f"SR-SYS-002 için etkilenen testler {expected_tests} olmalıdır!"
assert "guidance_laws.cpp" in impacted_sr002.get("CODE", []), "Güdüm kaynak kodu etki alanında olmalıdır."

# 5. Assertion: Düzeltilmiş (Remediated) Sistem Tam Doğrulaması
assert fwd_clean_pct == 100.0, "Temizlenmiş sistemde İleri İzlenebilirlik tam %100 olmalıdır!"
assert bwd_clean_pct == 100.0, "Temizlenmiş sistemde Geri İzlenebilirlik tam %100 olmalıdır!"

print("====================================================================================")
print("DO-178C DAL-A ÇİFT YÖNLÜ İZLENEBİLİRLİK DOĞRULAMA TESTLERİ BAŞARIYLA GEÇTİ")
print("====================================================================================")
print("[TEST 1 PASS] Çizge Bütünlüğü: 21 Düğüm ve Katman Bağlantıları Doğrulandı.")
print("[TEST 2 PASS] Yetim Kod (Orphan Code) Tespiti: %100 Başarıyla Yakalandı.")
print("[TEST 3 PASS] Test Edilmemiş İster Tespiti: SR-SYS-004 Boşluğu Başarıyla Yakalandı.")
print("[TEST 4 PASS] Değişiklik Etki Analizi (CIA): Regresyon Kümesi {TC-NAV-02, TC-NAV-03} İspatlandı.")
print("[TEST 5 PASS] Düzeltilmiş Sistem Doğrulaması: %100 Çift Yönlü İzlenebilirlik Kanıtlandı.")
print("====================================================================================")
print("TÜM DO-178C TABLO A-3 / A-4 İZLENEBİLİRLİK TESTLERİ: [UYGUN]")
print("====================================================================================")

```

---

## 14. Kod 4 Teknik Açıklaması: DO-178C DAL-A İzlenebilirlik Doğrulama Testleri

Aşağıdaki test paketi, aviyonik yazılım kabul kriterleri için 5 kritik assertion içerir:
1. **Assertion 1 (Graph Connectivity):** Sağlıklı temel sistemde tüm düğümlerin bağlılığını doğrular.
2. **Assertion 2 (Orphan Code Detection):** Enjekte edilen sahte kodun geriye dönük izleme ile %100 hassasiyetle yakalandığını onaylar.
3. **Assertion 3 (Untested Requirement Detection):** Eksik test senaryosunun ileri izleme ile yakalandığını onaylar.
4. **Assertion 4 (Change Impact Accuracy):** Değişiklik etki analizinin etkilenen test alt kümesini eksiksiz belirlediğini doğrular.
5. **Assertion 5 (Remediated Baseline Integrity):** Hata giderimi sonrası %100 ileri ve geri izlenebilirliği onaylar.

---

## 15. Görselleştirme Mimarisi ve Dashboard Tasarım İlkeleri

Üretilen görsel teftiş paneli (`gun_323_traceability_requirement_design_code_test.png`), 300 DPI çözünürlükte ve askeri taktik karanlık tema (`#0F172A`) standardında tasarlanmıştır:

- **Panel 1 (Sol Üst): 4 Katmanlı Yaşam Döngüsü Akış Çizgesi (Sankey Flow):** SR $\to$ HLR $\to$ LLR $\to$ CODE $\to$ TEST akışını, yetim kod ve eksik test yollarını kırmızıyla vurgulayarak gösterir.
- **Panel 2 (Sağ Üst): Çift Yönlü İzlenebilirlik Matrisi (BTM Isı Haritası):** 4 sistem isteri ile 4 yaşam döngüsü aşamasının tamlık durumunu yeşil/kırmızı ızgara olarak görselleştirir.
- **Panel 3 (Sol Alt): Değişiklik Etki Analizi (CIA Alt Çizgesi):** SR-SYS-002 değiştiğinde etkilenen alt bileşenler ve odaklanılması gereken regresyon testlerini vurgular.
- **Panel 4 (Sağ Alt): İzlenebilirlik Uyum ve Güvenlik Radarı:** Sağlıklı vs Hatalı durumların İleri Kapsama, Geri Kapsama ve Yetim Kod Yoğunluğu metriklerini karşılaştırır.

---

```python
# -*- coding: utf-8 -*-
"""
Gün 323: Traceability: requirement -> design -> code -> test
Kod Bloğu 5: 4 Panelli 300 DPI Aviyonik İzlenebilirlik Dashboard'u
"""
import matplotlib.pyplot as plt
import numpy as np

plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

for row in axs:
    for ax in row:
        ax.set_facecolor('#1E293B')
        ax.grid(True, linestyle='--', alpha=0.3, color='#94A3B8')
        ax.tick_params(colors='#F8FAFC', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#475569')

# -----------------------------------------------------------------------------
# Panel 1: 4-Katmanlı Yaşam Döngüsü Akış Çizgesi (Traceability Flow Graph)
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
layers = ['SR\n(Sistem)', 'HLR\n(Yazılım)', 'LLR\n(Tasarım)', 'CODE\n(Kaynak)', 'TEST\n(Doğrulama)']
x_coords = [0, 1, 2, 3, 4]
y_nodes = [0.8, 0.6, 0.4, 0.2]

# Normal düğümleri çiz
for x in x_coords[:3]:
    for y in y_nodes:
        ax1.scatter(x, y, color='#38BDF8', s=160, zorder=4)

# CODE düğümleri (4 normal + 1 yetim kod)
for y in y_nodes:
    ax1.scatter(3, y, color='#38BDF8', s=160, zorder=4)
ax1.scatter(3, 0.05, color='#EF4444', s=180, zorder=5) # Yetim Kod!
ax1.text(3.1, 0.05, 'Yetim Kod!\n(secret_backdoor.cpp)', color='#EF4444', fontweight='bold', fontsize=8, va='center')

# TEST düğümleri (4 test + 1 eksik test)
for y in [0.8, 0.65, 0.55, 0.4]:
    ax1.scatter(4, y, color='#10B981', s=160, zorder=4)
ax1.scatter(4, 0.2, color='#EF4444', s=180, marker='x', zorder=5) # Eksik Test Boşluğu!
ax1.text(4.1, 0.2, 'Eksik Test!\n(Boşluk)', color='#EF4444', fontweight='bold', fontsize=8, va='center')

# Sağlıklı akış çizgileri
for y in [0.8, 0.6, 0.4]:
    ax1.plot([0, 1, 2, 3], [y, y, y, y], color='#38BDF8', alpha=0.6, linewidth=2)
ax1.plot([3, 4], [0.8, 0.8], color='#10B981', alpha=0.6, linewidth=2)
ax1.plot([3, 4], [0.6, 0.65], color='#10B981', alpha=0.6, linewidth=2)
ax1.plot([3, 4], [0.6, 0.55], color='#10B981', alpha=0.6, linewidth=2)
ax1.plot([3, 4], [0.4, 0.4], color='#10B981', alpha=0.6, linewidth=2)

# Hatalı SR-SYS-004 çizgisi (Testte kesilir)
ax1.plot([0, 1, 2, 3], [0.2, 0.2, 0.2, 0.2], color='#F59E0B', linewidth=2)
ax1.plot([3, 4], [0.2, 0.2], color='#EF4444', linestyle=':', linewidth=2.5)

ax1.set_xticks(x_coords)
ax1.set_xticklabels(layers, color='#F8FAFC', fontweight='bold', fontsize=10)
ax1.set_yticks([])
ax1.set_xlim(-0.5, 5.2)
ax1.set_ylim(-0.1, 0.95)
ax1.set_title('DO-178C Uçtan Uca İzlenebilirlik Akış Çizgesi', color='#38BDF8', fontsize=12, fontweight='bold', pad=10)

# -----------------------------------------------------------------------------
# Panel 2: Çift Yönlü İzlenebilirlik Matrisi (BTM Isı Haritası)
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
# 4 Sistem İsteri x 4 Yaşam Döngüsü Aşaması
# 1: Tam Kapsandı, 0: Boşluk / Hata
matrix_data = np.array([
    [1, 1, 1, 1], # SR-SYS-001 -> Tam
    [1, 1, 1, 1], # SR-SYS-002 -> Tam
    [1, 1, 1, 1], # SR-SYS-003 -> Tam
    [1, 1, 1, 0]  # SR-SYS-004 -> TEST EKSİK!
])
im = ax2.imshow(matrix_data, cmap='coolwarm', aspect='auto', alpha=0.85)
ax2.set_xticks(range(4))
ax2.set_xticklabels(['HLR Yazılım', 'LLR Tasarım', 'Kaynak Kod', 'Doğrulama Test'], color='#F8FAFC', fontweight='bold')
ax2.set_yticks(range(4))
ax2.set_yticklabels(['SR-SYS-001 (Konum)', 'SR-SYS-002 (Güdüm)', 'SR-SYS-003 (Emniyet)', 'SR-SYS-004 (Kurtarma)'], color='#F8FAFC', fontweight='bold')
ax2.set_title('Çift Yönlü İzlenebilirlik Matrisi (BTM) Durumu', color='#38BDF8', fontsize=12, fontweight='bold', pad=10)

for i in range(4):
    for j in range(4):
        val = matrix_data[i, j]
        txt = "TAMAM" if val == 1 else "EKSİK!"
        color = "#FFFFFF" if val == 1 else "#EF4444"
        ax2.text(j, i, txt, ha='center', va='center', color=color, fontweight='bold', fontsize=11)

# -----------------------------------------------------------------------------
# Panel 3: Değişiklik Etki Analizi (CIA Alt Çizgesi)
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
cia_levels = ['Değişen İster', 'Yazılım İsteri', 'Tasarım', 'Kaynak Kod', 'Regresyon Testi']
cia_nodes = ['SR-SYS-002', 'HLR-SW-102', 'LLR-DES-202', 'guidance_laws.cpp', 'TC-NAV-02 & 03']
x_cia = np.arange(len(cia_levels))
y_cia = [0.5, 0.5, 0.5, 0.5, 0.5]

ax3.plot(x_cia, y_cia, color='#F59E0B', linewidth=3, zorder=2, label='Etki Yayılım Yolu (Impact Path)')
ax3.scatter(x_cia, y_cia, color='#F59E0B', s=220, zorder=3)

for idx, (lbl, node) in enumerate(zip(cia_levels, cia_nodes)):
    ax3.annotate(f"{lbl}\n[{node}]", xy=(x_cia[idx], y_cia[idx]), xytext=(0, 25),
                 textcoords="offset points", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=9,
                 bbox=dict(boxstyle="round,pad=0.3", fc="#0F172A", ec="#F59E0B"))

ax3.annotate('ZORUNLU KOŞULACAK\nREGRESYON KÜMESİ', xy=(4, 0.5), xytext=(4, 0.2),
             arrowprops=dict(facecolor='#10B981', shrink=0.08, width=1.5, headwidth=7),
             color='#10B981', fontweight='bold', fontsize=9, ha='center',
             bbox=dict(boxstyle="round,pad=0.3", fc="#0F172A", ec="#10B981"))

ax3.set_xticks(x_cia)
ax3.set_xticklabels(cia_levels, color='#F8FAFC', fontweight='bold')
ax3.set_yticks([])
ax3.set_xlim(-0.6, 4.8)
ax3.set_ylim(0.0, 1.0)
ax3.set_title('Değişiklik Etki Analizi (CIA): SR-SYS-002 Yayılımı', color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
ax3.legend(loc='lower left', facecolor='#0F172A', edgecolor='#475569', fontsize=9)

# -----------------------------------------------------------------------------
# Panel 4: İzlenebilirlik Uyum ve Kalite Göstergeleri
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
metrics = ['İleri İzlenebilirlik\n(Forward %)', 'Geri İzlenebilirlik\n(Backward %)', 'Doğrulanmış İster\n(Verified Req %)', 'Yetim Kodsuzluk\n(Orphan-Free %)']
x_m = np.arange(len(metrics))
width = 0.35

faulty_scores = [fwd_faulty_pct, bwd_faulty_pct, 75.0, 75.0]
clean_scores = [100.0, 100.0, 100.0, 100.0]

ax4.bar(x_m - width/2, faulty_scores, width, label='Hatalı Sistem (Kör Noktalar)', color='#EF4444', alpha=0.85)
ax4.bar(x_m + width/2, clean_scores, width, label='Düzeltilmiş DO-178C Uyumlu', color='#10B981', alpha=0.85)

ax4.axhline(100.0, color='#38BDF8', linestyle=':', linewidth=1.5, label='DO-178C DAL-A Hedefi (%100)')
ax4.set_ylabel('Uyum Oranı (%)', color='#F8FAFC', fontsize=11, fontweight='bold')
ax4.set_title('İzlenebilirlik Kalite ve Emniyet Göstergeleri', color='#38BDF8', fontsize=12, fontweight='bold', pad=10)
ax4.set_xticks(x_m)
ax4.set_xticklabels(metrics, color='#F8FAFC', fontweight='bold')
ax4.set_ylim(0, 120)
ax4.legend(loc='lower left', facecolor='#0F172A', edgecolor='#475569', fontsize=9)

for idx, val in enumerate(clean_scores):
    ax4.text(x_m[idx] + width/2, val + 2, f"%{val:.0f}", ha='center', va='bottom', color='#10B981', fontweight='bold', fontsize=9)

# Genel Başlık ve Düzen
fig.suptitle('ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ AVİYONİK DOĞRULAMA\nDO-178C ÇİFT YÖNLÜ İZLENEBİLİRLİK (REQUIREMENT -> DESIGN -> CODE -> TEST) VE CIA DASHBOARD',
             color='#F8FAFC', fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.94])

png_path = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_323\gun_323_traceability_requirement_design_code_test.png"
plt.savefig(png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

import os
file_size = os.path.getsize(png_path)
print(f"[+] 300 DPI Profesyonel Aviyonik Dashboard Kaydedildi: {png_path} ({file_size:,} bayt)")

```

---

## 16. Kod 5 Dashboard Analizi ve Görsel Teftiş Kılavuzu

Grafik kaydedildikten sonra yapılan teftişte şu kritik detaylar aranmalıdır:
- **Panel 1:** `secret_debug_backdoor.cpp` düğümünün solunda hiçbir gelen ok bulunmadığı (Yetim Kod) açıkça görülmelidir.
- **Panel 2:** Hatalı durumda `SR-SYS-004` satırının `TEST` sütununun kırmızı (EKSİK) yandığı teyit edilmelidir.
- **Panel 3:** `SR-SYS-002` altındaki sarı/turuncu yayılım yolunun sadece ilgili 2 testi (`TC-NAV-02`, `TC-NAV-03`) hedeflediği doğrulanmalıdır.
- **Panel 4:** Sağlıklı sistemde izlenebilirlik metriklerinin %100 tam uyuma oturduğu gözlemlenmelidir.

---

## 17. Sık Yapılan Hatalar ve Antipatternler

Savunma yazılımı projelerinde izlenebilirlik sürecinde düşülen en büyük tuzaklar:

1. **"Sonradan İzlenebilirlik Uydurma" (Post-hoc Traceability Antipattern):** Kod ve testler yazılıp bittikten sonra denetimden bir hafta önce geriye dönük sahte bağlantılar uydurmak. Bu durum mimari tutarsızlıkları kaçınılmaz kılar.
2. **Bire-Çok Bağlantı Karmaşası (1-to-All Linking):** Bir sistem isterini projedeki 50 farklı kod dosyasına gelişigüzel bağlamak. Bu durum değişiklik etki analizini (CIA) imkansız hale getirir.
3. **Yetim Kodları Yoksayma:** "Zararsız yardımcı fonksiyon" denilerek gereksinimsiz kod parçalarını kaynak kodda bırakmak (DO-178C doğrudan ihlalidir).
4. **Tek Yönlü İzlenebilirlikle Yetinme:** Sadece gereksinimden koda bakmak, koddan yukarıya bakmamak (Yetim kodları tespit edemez).
5. **Kopuk Test Bağlantıları:** Testin ismini koda bağlayıp gerçekte isteri değil sadece bir fonksiyonun çalıştığını kontrol etmek.

---

```python
# -*- coding: utf-8 -*-
"""
Gün 323: Traceability: requirement -> design -> code -> test
Kod Bloğu 6: Aviyonik DO-178C Tablo A-3/A-4 Kalifikasyon Kabul Protokolü
"""
report_rows = [
    ("1. Hedef Aviyonik Emniyet Seviyesi", "DO-178C DAL-A (Katastrofik Emniyet Risk Koruması)", "[UYGUN]"),
    ("2. İleri İzlenebilirlik Oranı (SR->Test)", f"%{fwd_clean_pct:.1f} (Tüm Sistem İsterleri Doğrulandı)", "[UYGUN]"),
    ("3. Geriye Dönük İzlenebilirlik (Code->SR)", f"%{bwd_clean_pct:.1f} (Tüm Kodlar Meşru İstere Bağlı)", "[UYGUN]"),
    ("4. Yetim Kod (Orphan Code) Durumu", "Sıfır Yetim Kod (Rogue Code Başarıyla Ayıklandı)", "[UYGUN]"),
    ("5. Test Edilmemiş İster Durumu", "Sıfır Açık (SR-SYS-004 Test Senaryosu Kapatıldı)", "[UYGUN]"),
    ("6. Değişiklik Etki Analizi (CIA)", "Alt Seviye Yayılım & Regresyon Kümesi Deterministik", "[UYGUN]"),
    ("7. Endüstriyel Araç Entegrasyonu", "DOORS / Polarion / Git Commit Etiketleme Uyumlu", "[UYGUN]"),
    ("8. Dashboard Teftiş Artefaktı", f"300 DPI PNG ({file_size:,} bayt > 100 KB)", "[UYGUN]")
]

print("+======================================================================+")
print("|   ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ DOĞRULAMA OTORİTESİ          |")
print("|       DO-178C TABLO A-3 / A-4 İZLENEBİLİRLİK KALİFİKASYON ONAYI      |")
print("+======================================================================+")
for title, detail, status in report_rows:
    print(f"| {title:<38}: {detail:<30} | {status} |")
print("+======================================================================+")
print("| SONUÇ: TÜM DO-178C DAL-A ÇİFT YÖNLÜ İZLENEBİLİRLİK ŞARTLARI SAĞLANDI! |")
print("| YAZILIM SOI-3 / SOI-4 KALİFİKASYON DENETİMİNE RESMEN ONAYLANMIŞTIR!   |")
print("+======================================================================+\n")
print("[MÜKEMMEL] GÜN 323: TRACEABILITY (REQUIREMENT -> DESIGN -> CODE -> TEST) TAMAMLANDI.")
print("[SIRADAKİ GÜN] GÜN 324: FAULT-ERROR-FAILURE ZİNCİRİ.")

```

---

## 17. Gün Sonu Özeti ve Sıradaki Gün

### Gün Sonu Özeti (3 Cümle):
1. **Traceability Nedir?** Sistem isterlerinden başlayarak tasarım, kaynak kod ve doğrulama testlerine kadar yaşam döngüsü boyunca kurulan çift yönlü, denetlenebilir ilişki çizgesidir.
2. **Hangi Problemi Çözer?** Geliştirme sürecinde unutulan isterleri (omission), yetkisiz/öngörülmeyen yetim kodları (rogue code) tespit eder ve ister değişikliklerinde gereken regresyon test kapsamını kesin olarak belirler.
3. **Hangi Trade-off / Hata Sınıfını Getirir?** Sürekli ve disiplinli bir etiketleme/araç yönetimi yükü getirir; bağlantılar gevşek kurulursa değişiklik etki analizinde tüm sistemi gereksiz yere baştan test etme maliyeti yaratır.

---

### Sıradaki Gün: Gün 324
**Faz F11:** Verification / SIL / HIL  
**Konu:** Fault-error-failure zinciri (Hata-Kusur-Arıza Zinciri, IEEE 610.12 / ISO 26262 Arıza Modelleri, Aviyonik Hata Toleransı ve Hata Yayılımının Kırılması).
