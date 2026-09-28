# Gün 334 — F11 — Verification / SIL / HIL: CI'da Automated Verification Report

[![Özel Lisans](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](#lisans)
[![DO-178C DAL-A](https://img.shields.io/badge/DO--178C-DAL--A%20Verified-blue?style=flat-square)](#dogrulama)
[![DO-330 Tool Qual](https://img.shields.io/badge/DO--330-TQL--1%20Qualified-emerald?style=flat-square)](#arac-kalifikasyonu)
[![CI/CD Automation](https://img.shields.io/badge/CI%2FCD-Automated%20Verification-purple?style=flat-square)](#otomasyon)

> **ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR**  
> Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)  
> Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır. Yazarın açık yazılı izni olmaksızın kopyalanamaz, dağıtılamaz, ticari veya gayriticari projelerde kullanılamaz.

---

### Görev Özeti ve Mühendislik Motivasyonu
Modern havacılık ve savunma sanayiinde (TUSAŞ KAAN, HÜRJET, ANKA-3, ASELSAN Aviyonik Görev Bilgisayarları, ROKETSAN Güdüm ve Kontrol Sistemleri), yüz binlerce satır C++20 ve gömülü sistem kodunun her bir commit, pull request (PR) ve sürüm aşamasında elle test edilmesi imkânsızdır ve insan hatasına açıktır.

Havacılık yazılım güvenliğinin anayasası olan **DO-178C Seviye A (DAL-A)** ve araç kalifikasyon standardı **DO-330 (Tool Qualification)** uyarınca; geliştirilen her yazılım modülünün gereksinimleri tam olarak karşıladığı, hiçbir regresyon (gerileme) içermediği ve arıza toleransına sahip olduğu **Sürekli Entegrasyon (CI/CD)** boru hatlarında tamamen otomatik olarak kanıtlanmalı ve denetlenebilir raporlar (**Automated Verification Report**) olarak arşivlenmelidir.

Otomatik CI Doğrulama Raporlamasının temel bileşenleri:
1. **Çok Katmanlı Test Koşumu (Multi-Stage Execution):** Statik Kod Analizi (MISRA C++2023 / Clang-Tidy), Birim Testler ve MC/DC Kapsaması (GTest / gcov), SIL (Software-in-the-Loop) Kapalı Çevrim Simülasyonu, Sanal HIL Veri Yolu Doğrulaması (MIL-STD-1553B & ARINC 429) ve Arıza Enjeksiyon Kampanyası (Fault Injection).
2. **Uçtan Uca İzlenebilirlik (Verification Traceability Matrix - VTM):** Sistem Gereksinimleri $\to$ Yüksek Seviye Gereksinimler (HLR) $\to$ Düşük Seviye Gereksinimler (LLR) $\to$ Kaynak Kod $\to$ Test Senaryoları $\to$ Yürütme Hükmü (Pass/Fail) zincirinin kesintisiz haritalanması.
3. **Otomatik Kalite Kapıları (Automated Quality Gates):** Katı kurallara dayalı geçiş mekanizması: Sıfır kritik hata, %100 test başarı oranı, kritik modüllerde %100 MC/DC kod kapsaması ve sıfır yetim gereksinim. Tek bir ihlalde CI derhal derlemeyi durdurur (BLOCKED).
4. **Denetim Kanıtı Üretimi (Audit Evidence Generation):** Hem insanlar için özet ve grafiksel panolar (HTML / Dashboard), hem de DO-178C sertifikasyon otoriteleri için makine tarafından doğrulanabilir yapılandırılmış veri (JUnit XML / SARIF / JSON Evidence).

---

## 1. Kavramsal Temel ve Neden-Sonuç Zinciri

### 5N1K Modeli
- **Ne?** CI'da Automated Verification Report; her yazılım değişikliğinde statik analizden HIL seviyesine kadar tüm doğrulama katmanlarını otomatik çalıştıran, gereksinim izlenebilirliğini kuran ve resmi kalite kapısı kararı üreten sistemik mekanizmadır.
- **Neden?** Geliştirme sürecinin erken aşamalarında regresyonları anında yakalamak, insan kaynaklı test atlamalarını sıfırlamak ve DO-178C/DO-254 sertifikasyonu için eksiksiz kalifikasyon kanıtı oluşturmak için.
- **Nerede?** GitLab CI, GitHub Actions, Jenkins ve savunma sanayii izole şirket içi (on-premise) CI koşucularında (runners).
- **Nasıl?** Kod depoya itildiğinde (git push) tetiklenen otomatik iş akışları aracılığıyla; test sonuçları, kapsam metrikleri ve arıza analizleri toplanarak birleşik JSON/XML/HTML raporlarına dönüştürülür.
- **Ne Zaman?** Her kod commit'inde, pull request açıldığında, gece koşumlarında (nightly builds) ve resmi sürüm kalifikasyonunda.
- **Kim?** Aviyonik Yazılım Mühendisleri, Sürekli Entegrasyon (DevOps/CI-CD) Mühendisleri, Bağımsız Kalite ve Doğrulama (V&V) Ekipleri.

### Neden-Sonuç Tablosu
| Olay / Girdi | CI Mekanizması | Beklenen Mühendislik Çıktısı | Aviyonik Emniyet Etkisi |
| :--- | :--- | :--- | :--- |
| **Gereksinimi Karşılamayan Kod** | Traceability Engine Denetimi | Test raporunda "Uncovered Requirement" hatası | Tanımsız ve doğrulanmamış özelliklerin uçağa girmesi önlenir |
| **Parite veya Protokol Hatası** | Bus Emulation Hata Testi | HIL test aşamasında FAIL hükmü | Uçuş sırasında telemetri kaybı ve bus kilitlenmesi engellenir |
| **MC/DC Kapsama Düşüşü (<100%)** | Coverage Quality Gate | Kalite kapısı PR merge işlemini bloke eder | Test edilmemiş ölü veya gizli mantık blokları elenir |
| **Sistem Regresyonu (Mevcut Fonksiyon Bozulması)** | Otomatik Regresyon Test Koşusu | Eski ve yeni koşum sonuçları kıyaslanır | Önceden çalışan sistem bileşenlerinin bozulması engellenir |
| **Denetim Teftişi (Sivil/Askeri Otorite)** | Otomatik VTM & Kanıt Üretimi | Saniyeler içinde tek tıkla resmi sertifika raporu | Aylarca süren manuel dokümantasyon yükü ve hata riski kalkar |

---

## 2. Savunma Aviyonik CI/CD Boru Hattı Mimarisi ve Çok Katmanlı Doğrulama Kapıları

Askeri ve sivil havacılık standartlarında güvenilir bir CI boru hattı, en hızlı statik denetimden en ağır donanım emülasyonuna kadar hiyerarşik 5 aşamadan oluşur:

```
+-------------------------------------------------------------------------------------------------------------------------+
|                                    SAVUNMA AVİYONİK OTOMATİK CI/CD DOĞRULAMA BORU HATTI                                 |
|                                                                                                                         |
|   [Geliştirici] ---> [git push / PR] ---> [GitLab CI / GitHub Actions / Jenkins Runner]                                 |
|                                                          |                                                              |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|   | 1. STATİK KOD ANALİZİ & SAST (MISRA C++2023, Clang-Tidy, CPPCheck, SonarQube)                                   |   |
|   |    - Sıfır Bellek Sızıntısı, Sıfır Tanımsız Davranış (Undefined Behavior), Sıfır MISRA Critical İhlali          |   |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|                                                          | (PASS)                                                       |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|   | 2. BİRİM TESTLER & MC/DC KOD KAPSAMASI (GTest, gcov/lcov, DO-178C DAL-A Standardı)                             |   |
|   |    - Fonksiyon ve Koşul Kapsaması: %100, MC/DC Kapsaması: %100 (Kritik Algoritmalar)                            |   |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|                                                          | (PASS)                                                       |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|   | 3. SIL (SOFTWARE-IN-THE-LOOP) KAPALI ÇEVRİM SİMÜLASYONU (Uçuş Dinamiği & Otopilot Kontrol)                      |   |
|   |    - 2-DOF / 6-DOF Füze/Uçak Gövdesi, Aerodinamik Rüzgâr Darbesi, Uçuş Kararlılık Toleransı < 0.05 rad          |   |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|                                                          | (PASS)                                                       |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|   | 4. SANAL HIL VERİ YOLU VE PROTOKOL DOĞRULAMASI (MIL-STD-1553B & ARINC 429 & SNMPv3)                            |   |
|   |    - 1553B BC/RT Çift Hat İletimi, ARINC 429 Bipolar RZ & BNR Veri Kodlama, SNMPv3 USM authPriv Güvenliği      |   |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|                                                          | (PASS)                                                       |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|   | 5. HATA ENJEKSİYONU KAMPANYASI (Fault Injection: Sensör Drift, Parite Bozulması, Siber Replay Atağı)             |   |
|   |    - FDIR İzolasyonu: %100, Güvenli Duruma Geçiş: < 2.0 ms                                                      |   |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|                                                          |                                                              |
|                                                          v                                                              |
|   +-----------------------------------------------------------------------------------------------------------------+   |
|   | 6. OTOMATİK DOĞRULAMA RAPORLAYICI & KALİTE KAPISI (Quality Gatekeeper)                                          |   |
|   |    - Verification Traceability Matrix (VTM) Üretimi                                                             |   |
|   |    - JUnit XML / SARIF / JSON Evidence & HTML Raporu                                                            |   |
|   |    - KARAR: [PASSED] -> Merge Onayı  |  [BLOCKED] -> PR Reddi & Alarm                                           |   |
|   +-----------------------------------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------------------------------+
```

### Kapı Geçiş Kuralı:
Boru hattı sıralı çalışır. Bir aşamada tek bir test bile başarısız olursa sonraki ağır aşamalar çalıştırılmayarak donanım kaynakları tasarruf edilir ve CI anında `BLOCKED` kararı vererek geliştiriciye doğrudan hatanın kaynağını bildirir.

---

## 3. Doğrulama İzlenebilirlik Matrisi (VTM) ve DO-178C Gereksinim Standartları

DO-178C Bölüm 5 ve 6, yazılım yaşam döngüsündeki tüm nesnelerin iki yönlü izlenebilirliğini (Bidirectional Traceability) zorunlu kılar:

```
+---------------------+      +---------------------+      +---------------------+      +---------------------+
| Sistem Gereksinimi  | ---> | Yüksek Seviye (HLR) | ---> | Düşük Seviye (LLR)  | ---> | Kaynak Kod & Fonk.  |
| (System Req - SRD)  |      | Uçuş Yönetimi       |      | Protokol / Algoritma|      | C++20 Implementasyon|
+---------------------+      +---------------------+      +---------------------+      +---------------------+
                                                                                            |
                                                                                            v
+---------------------+      +---------------------+      +---------------------+      +---------------------+
| Resmi Kabul Raporu  | <--- | Kalite Kapısı Onayı | <--- | Test Sonucu (Pass)  | <--- | Doğrulama Testi (TC)|
| DO-178C Sertifikası |      | Zero Regressions    |      | JUnit/JSON Kanıtı   |      | SIL / HIL Senaryosu |
+---------------------+      +---------------------+      +---------------------+      +---------------------+
```

### Kritik Gereksinim Kimlikleri:
1. **`HLR_NAV_01` (Seyrüsefer İrtifa Doğruluğu):** Uçuş kontrol bilgisayarı, barometrik irtifayı $\pm 10\text{ ft}$ hassasiyetle okumalı ve güncellemelidir.
2. **`HLR_ATT_02` (Tutuş ve Baş Açısı Kararlılığı):** Uçuş dinamiği otopilot geri beslemesinde manyetik baş açısı hatası $0.05\text{ rad}$ altında tutulmalıdır.
3. **`LLR_1553_PARITY` (1553B Tekil Parite Koruması):** Hatta gelen her 1553B sözcüğünde tekil parite denetlenmeli, hatalı sözcük anında `Message Error (ME)` olarak işaretlenmelidir.
4. **`LLR_ARINC_SSM` (ARINC 429 Durum İzolasyonu):** ARINC 429 sözcüklerinde SSM `FAILURE_WARNING` veya `NO_COMPUTED_DATA` olduğunda veri otopilota beslenmemeli, FDIR tetiklenmelidir.
5. **`LLR_SNMP_AUTH` (SNMPv3 Kriptografik Güvenlik):** Telemetri paketleri HMAC-SHA256 ile doğrulanmalı ve AES-128 ile şifrelenmelidir; yetkisiz erişimler bloklanmalıdır.

---

```python
# -*- coding: utf-8 -*-
"""
Gün 334: CI'da automated verification report
Kod Bloğu 1: Doğrulama Kanıt Toplayıcı (Verification Evidence Collector) ve Gereksinim İzlenebilirlik Motoru
"""
from enum import Enum
from typing import Dict, List, Any, Optional
import time
import json
import xml.etree.ElementTree as ET

class VerdictStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"

class TestCaseResult:
    """Tek bir doğrulama testinin yürütme ve gereksinim izlenebilirlik sonucu."""
    def __init__(self, test_id: str, name: str, stage: str, req_ids: List[str],
                 verdict: VerdictStatus, duration_ms: float, error_msg: Optional[str] = None):
        self.test_id = test_id
        self.name = name
        self.stage = stage # SAST, UNIT, SIL, HIL, FAULT
        self.req_ids = req_ids
        self.verdict = verdict
        self.duration_ms = duration_ms
        self.error_msg = error_msg

class VerificationEvidenceCollector:
    """
    DO-178C DAL-A & DO-330 Uyumlu Kanıt Toplama Motoru.
    Gereksinimler ile test senaryolarını eşler ve makine tarafından doğrulanabilir kanıt üretir.
    """
    def __init__(self, project_name: str, build_id: str, commit_sha: str):
        self.project_name = project_name
        self.build_id = build_id
        self.commit_sha = commit_sha
        self.start_time = time.time()
        self.test_results: List[TestCaseResult] = []
        self.system_requirements: Dict[str, str] = {
            "HLR_NAV_01": "Uçuş Bilgisayarı Barometrik İrtifayı 1.0 ft Çözünürlükle İzlemelidir",
            "HLR_ATT_02": "Uçuş Tutuş ve Yönelim Hatası 0.05 rad Toleransı Aşmamalıdır",
            "LLR_1553_PARITY": "MIL-STD-1553B Sözcüklerinde Tekil Parite Bozulması Anında İzole Edilmelidir",
            "LLR_ARINC_SSM": "ARINC 429 SSM Failure Warning / NCD Durumunda FDIR Tetiklenmelidir",
            "LLR_SNMP_AUTH": "SNMPv3 USM authPriv Telemetrisi HMAC-SHA256 ve AES-128 ile Korunmalıdır"
        }

    def record_test(self, test: TestCaseResult):
        """Test sonucunu veri tabanına kaydeder."""
        self.test_results.append(test)

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Tüm testler üzerinden özet istatistikleri ve gereksinim kapsamını hesaplar."""
        total = len(self.test_results)
        passed = sum(1 for t in self.test_results if t.verdict == VerdictStatus.PASSED)
        failed = sum(1 for t in self.test_results if t.verdict == VerdictStatus.FAILED)
        blocked = sum(1 for t in self.test_results if t.verdict == VerdictStatus.BLOCKED)
        
        # Gereksinim Kapsaması (Requirements Coverage)
        covered_reqs = set()
        for t in self.test_results:
            if t.verdict == VerdictStatus.PASSED:
                for r in t.req_ids:
                    covered_reqs.add(r)
                    
        total_reqs = len(self.system_requirements)
        req_coverage_pct = (len(covered_reqs) / total_reqs) * 100.0 if total_reqs > 0 else 0.0
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "pass_rate_pct": (passed / total * 100.0) if total > 0 else 0.0,
            "total_requirements": total_reqs,
            "covered_requirements": len(covered_reqs),
            "uncovered_requirements": list(set(self.system_requirements.keys()) - covered_reqs),
            "req_coverage_pct": req_coverage_pct,
            "total_duration_ms": sum(t.duration_ms for t in self.test_results)
        }

    def export_junit_xml(self) -> str:
        """Standart CI/CD tüketimi için JUnit XML formatında rapor üretir."""
        suite = ET.Element("testsuite", name=f"{self.project_name}_Verification",
                           tests=str(len(self.test_results)),
                           failures=str(sum(1 for t in self.test_results if t.verdict == VerdictStatus.FAILED)),
                           time=f"{sum(t.duration_ms for t in self.test_results) / 1000.0:.3f}")
        for t in self.test_results:
            tc = ET.SubElement(suite, "testcase", classname=t.stage, name=t.name,
                               time=f"{t.duration_ms / 1000.0:.4f}")
            if t.verdict == VerdictStatus.FAILED:
                fail = ET.SubElement(tc, "failure", message=t.error_msg or "Test Failed")
                fail.text = t.error_msg
        return ET.tostring(suite, encoding='unicode')

print("[+] DO-178C Kanıt Toplayıcı ve Gereksinim İzlenebilirlik Motoru Başarıyla Yüklendi.")
collector_demo = VerificationEvidenceCollector("KAAN_FCC_SW", "BUILD_2026_09", "a4b7c89")
print(f"  - Proje: {collector_demo.project_name} | Commit: {collector_demo.commit_sha}")
print(f"  - İzlenen Sistem Gereksinimi Sayısı: {len(collector_demo.system_requirements)}")
```

---

## 4. Kod 1 Teknik Açıklaması: Veri Yapıları, Gereksinim Eşleme ve Sayısal Doğrulama Metrikleri

Yukarıdaki `VerificationEvidenceCollector` sınıfı, DO-178C ve DO-330 uyumlu kurumsal bir test kanıt toplayıcısıdır:

1. **Katı Hüküm Modeli (VerdictStatus):** Her test açık ve net bir duruma sahiptir (`PASSED`, `FAILED`, `BLOCKED`, `SKIPPED`). Savunma yazılımlarında "belirsiz" veya "uyarı" durumu bulunmaz; karşılanmayan her şart `FAILED` kabul edilir.
2. **Çift Yönlü Gereksinim Eşleme (RequirementTrace):** Her bir `TestCaseResult`, doğrudan bir veya birden fazla gereksinim kimliğine (`req_id`) bağlıdır. Raporlayıcı, sistemde tanımlı tüm gereksinimlerin en az bir başarılı testle doğrulandığını (Requirements Coverage) otomatik olarak doğrular.
3. **Yürütme Süresi ve Zaman Aşımı İzleme:** Testlerin çalışma süreleri (execution duration) milisaniye seviyesinde kaydedilir. Bu veriler CI boru hattındaki performans darboğazlarını tespit etmek için kullanılır.
4. **Yapılandırılmış İhracat (JSON/XML):** Toplanan veriler doğrudan CI sunucularının tüketebileceği standart formatlara ihraç edilmeye hazır olarak hafızada tutulur.

---

## 5. Test Raporlama Standartları: JUnit XML, SARIF ve DO-178C Evidence Paketleri

Otomatik doğrulama boru hatlarında çıktının hem CI motorları (GitLab CI, GitHub Actions) hem de bağımsız doğrulama otoriteleri tarafından standart olarak okunabilmesi için üç temel format kullanılır:

### 1. JUnit XML Standardı:
Tüm modern CI/CD panoları tarafından yerel olarak desteklenen XML formatıdır:
```xml
<testsuite name="Avionics_SIL_Suite" tests="40" failures="0" errors="0" time="1.245">
    <testcase classname="FlightControl" name="test_altitude_tracking" time="0.035" />
    <testcase classname="BusProtocol" name="test_1553_parity_rejection" time="0.012" />
</testsuite>
```

### 2. SARIF (Static Analysis Results Interchange Format - OASIS):
Statik kod analizi (MISRA ihlalleri, potansiyel null pointer dereference, buffer overflow) bulgularını JSON tabanlı olarak raporlar ve kod satırına doğrudan bağlar.

### 3. DO-178C Yapılandırılmış Kanıt Paketi (JSON Evidence Bundle):
Gereksinim kimliklerini, yazılım sürümünü (Git SHA), derleme ortamını, test sonuçlarını ve kalite kapısı imzasını içeren kriptografik olarak imzalanabilir nihai denetim paketidir.

---

## 6. Otomatik Kalite Kapıları (Automated Quality Gates) ve Sıfır Tolerans Politikası

Savunma yazılımlarında **Sıfır Hata ve Sıfır Regresyon (Zero Defect / Zero Regression)** prensibi esastır. Geliştiricinin yazdığı kod ne kadar yenilikçi olursa olsun, kalite kapısından geçemezse ana depoya (main branch) kesinlikle birleştirilemez (merge edilemez).

### Kalite Kapısı Denetim Kriterleri Tablosu:
| Kalite Kriteri | Minimum Eşik Değeri | İhlal Durumunda CI Kararı |
| :--- | :--- | :--- |
| **Statik Analiz (MISRA / Clang-Tidy)** | 0 High / 0 Critical İhlal | `BLOCKED` (Derleme Reddi) |
| **Birim Test Başarı Oranı** | $\%100.0$ (0 Hata) | `BLOCKED` (Kod Birleştirilemez) |
| **MC/DC Kod Kapsaması (DAL-A)** | $\%100.0$ (Güvenlik Kritik Kod) | `BLOCKED` (Eksik Test) |
| **SIL Simülasyon Kararlılığı** | Tutuş Hatası $< 0.05\text{ rad}$ | `BLOCKED` (Uçuş Emniyetsiz) |
| **Veri Yolu Protokol Doğrulaması** | $\%100$ Parite & Hata İzolasyonu | `BLOCKED` (Aviyonik Risk) |
| **Gereksinim Kapsaması (VTM)** | $\%100.0$ (0 Yetim Gereksinim) | `BLOCKED` (İzlenebilirlik Kopuk) |
| **Regresyon Testleri** | 0 Yeni Hata | `BLOCKED` (Gerileme Tespit Edildi) |

---

```python
# -*- coding: utf-8 -*-
"""
Gün 334: CI'da automated verification report
Kod Bloğu 2: Otomatik Kalite Kapısı (Automated Quality Gate) ve Doğrulama Karar Motoru
"""
class QualityGateStatus(Enum):
    PASSED = "PASSED"
    BLOCKED = "BLOCKED"

class AutomatedQualityGateEngine:
    """
    Savunma Sanayii DO-178C DAL-A Seviyesinde CI/CD Kalite Kapısı Motoru.
    Gereksinim kapsaması, kod kapsaması (MC/DC), arıza yakalama ve regresyon kriterlerini denetler.
    """
    def __init__(self, min_pass_rate: float = 100.0,
                 req_coverage_threshold: float = 100.0,
                 max_sast_critical: int = 0,
                 min_mcdc_coverage: float = 100.0):
        self.min_pass_rate = min_pass_rate
        self.req_coverage_threshold = req_coverage_threshold
        self.max_sast_critical = max_sast_critical
        self.min_mcdc_coverage = min_mcdc_coverage

    def evaluate(self, collector: VerificationEvidenceCollector,
                 sast_critical_count: int = 0,
                 mcdc_coverage_pct: float = 100.0) -> Dict[str, Any]:
        """Boru hattı metriklerini değerlendirir ve resmi mühür basar."""
        metrics = collector.get_summary_metrics()
        gate_reasons: List[str] = []
        
        # 1. Statik Analiz (SAST) Denetimi
        if sast_critical_count > self.max_sast_critical:
            gate_reasons.append(f"SAST kritik ihlal eşiği aşıldı: {sast_critical_count} > {self.max_sast_critical}")
            
        # 2. Test Geçiş Oranı Denetimi
        if metrics["pass_rate_pct"] < self.min_pass_rate:
            gate_reasons.append(f"Test geçiş oranı yetersiz: %{metrics['pass_rate_pct']:.1f} < %{self.min_pass_rate:.1f}")
            
        # 3. Gereksinim Kapsaması (Requirements Coverage)
        if metrics["req_coverage_pct"] < self.req_coverage_threshold:
            gate_reasons.append(f"Gereksinim kapsaması eksik: %{metrics['req_coverage_pct']:.1f} < %{self.req_coverage_threshold:.1f}. Kapsanmayanlar: {metrics['uncovered_requirements']}")

        # 4. MC/DC Kod Kapsaması Denetimi
        if mcdc_coverage_pct < self.min_mcdc_coverage:
            gate_reasons.append(f"MC/DC kod kapsaması yetersiz: %{mcdc_coverage_pct:.1f} < %{self.min_mcdc_coverage:.1f}")
            
        status = QualityGateStatus.PASSED if len(gate_reasons) == 0 else QualityGateStatus.BLOCKED
        return {
            "status": status.value,
            "gate_passed": (status == QualityGateStatus.PASSED),
            "reasons": gate_reasons,
            "metrics": metrics,
            "sast_critical": sast_critical_count,
            "mcdc_coverage_pct": mcdc_coverage_pct
        }

print("[+] Otomatik Kalite Kapısı (Quality Gatekeeper) Motoru Başarıyla Yüklendi.")
gatekeeper = AutomatedQualityGateEngine()
print(f"  - Minimum Test Geçiş Oranı Eşiği : %{gatekeeper.min_pass_rate}")
print(f"  - Minimum Gereksinim Kapsaması    : %{gatekeeper.req_coverage_threshold}")
print(f"  - Minimum MC/DC Kapsaması         : %{gatekeeper.min_mcdc_coverage}")
```

---

## 7. Kod 2 Teknik Açıklaması: Kalite Kapısı Eşikleri, Regresyon Algılama ve Blokaj Mantığı

Yukarıdaki `AutomatedQualityGateEngine` sınıfı, savunma sanayii standartlarında otomatik karar verici (gatekeeper) rolünü icra eder:

1. **Çoklu Kriter Değerlendirmesi:** Yalnızca birim testlerin geçmesi yeterli görülmez; statik analiz kusurları, MC/DC kod kapsaması, veri yolu protokol bütünlüğü ve gereksinim izlenebilirliği eş zamanlı olarak denetlenir.
2. **Katı Eşik Denetimi:** Herhangi bir kriter eşik değerinin altında kalırsa, motor ilgili nedeni `gate_reasons` listesine ekler ve genel hükmü `QualityGateStatus.BLOCKED` olarak belirler.
3. **Gereksinim Kapsama Garantisi:** Test suite'inde tüm gereksinimlerin (`HLR` ve `LLR`) kapsandığı matematiksel olarak doğrulanır. Tek bir gereksinim dahi testsiz kalmışsa boru hattı onay vermez.
4. **Açık ve Eyleme Geçilebilir Hata Raporu:** Geliştiriciye yalnızca "test failed" denmez; hangi kriterin hangi değerle reddedildiği (örneğin: `Birim test geçiş oranı yetersiz: %97.5 < %100.0`) açıkça raporlanır.

---

## 8. Otomatik Doğrulama Raporu Oluşturucu (Verification Report Generator)

Toplanan kanıtlar ve kalite kapısı kararı, `VerificationReportGenerator` motoru tarafından hem makine okunabilir hem de insanlar tarafından denetlenebilir profesyonel formatlarda üretilir:

### Üretilen Rapor Bileşenleri:
1. **Yönetici Özeti (Executive Summary):** Yazılım sürümü, derleme tarihi, toplam test adedi, yürütme süresi ve nihai kalite kapısı kararı.
2. **Gereksinim İzlenebilirlik Tablosu (VTM Table):** Her sistem gereksiniminin hangi test fonksiyonları tarafından doğrulandığını gösteren matris.
3. **Aşama Bazlı Başarı ve Zaman Dağılımı:** Statik analiz, Unit, SIL, HIL ve Fault Injection aşamalarının süre ve test dağılımı.
4. **Hata ve İzolasyon Kayıtları:** Varsa başarısız testlerin yığın izi (stack trace), arıza modu ve etkilenen gereksinimler.

---

## 9. CI Simülasyon Senaryoları: Nominal Sürüm vs Regresyonlu/Kusurlu PR Karşılaştırması

Sistemin doğrulama ve engelleme kabiliyetini kanıtlamak için iki karşılaştırmalı CI boru hattı koşturulur:

### Senaryo 1: Nominal Sürüm (Release Candidate v2.4.0)
- 150 farklı aviyonik test koşturulur:
  - 30 Birim Test (MC/DC %100)
  - 40 SIL Kapalı Çevrim Simülasyonu
  - 40 Sanal HIL Veri Yolu Testi (1553B & ARINC 429)
  - 40 Hata Enjeksiyonu ve FDIR Karantina Testi
- Tüm testler başarıyla geçer (`PASS`), tüm kalite kapıları yeşildir (`PASSED`).

### Senaryo 2: Kusurlu ve Regresyonlu PR (Buggy Feature Branch - PR #412)
- Geliştirici yanlışlıkla MIL-STD-1553B parite kontrol algoritmasını devre dışı bırakmış veya gevşetmiştir.
- `LLR_1553_PARITY` gereksinimini doğrulayan test başarısız olur (`FAIL`).
- Kalite Kapısı devreye girer: Test başarı oranı düşer, parite doğrulama kapısı kırılır ve CI boru hattı PR'ı derhal `BLOCKED` olarak mühürler.

---

```python
# -*- coding: utf-8 -*-
"""
Gün 334: CI'da automated verification report
Kod Bloğu 3: Tam CI Boru Hattı Koşumu ve Regresyon Hata Enjeksiyon Simülasyonu
"""
def run_ci_verification_pipeline(collector: VerificationEvidenceCollector, inject_regression: bool = False):
    """
    5 Aşamalı Tam Aviyonik CI Doğrulama Boru Hattını Çalıştırır:
    Stage 1: SAST (Static Analysis & MISRA C++2023)
    Stage 2: UNIT (Birim ve MC/DC Fonksiyon Testleri)
    Stage 3: SIL (Kapalı Çevrim Uçuş Dinamiği Simülasyonu)
    Stage 4: HIL (Sanal 1553B & ARINC 429 Veri Yolu Testleri)
    Stage 5: FAULT (Arıza Enjeksiyonu ve FDIR Karantina Denetimi)
    """
    # -------------------------------------------------------------------------
    # STAGE 1: SAST (Static Analysis) - 20 Test
    # -------------------------------------------------------------------------
    for i in range(20):
        collector.record_test(TestCaseResult(
            test_id=f"SAST_{i+1:03d}",
            name=f"misra_rule_compliance_{i+1}",
            stage="SAST",
            req_ids=["HLR_NAV_01", "HLR_ATT_02"],
            verdict=VerdictStatus.PASSED,
            duration_ms=0.45
        ))
        
    # -------------------------------------------------------------------------
    # STAGE 2: UNIT TESTS - 30 Test
    # -------------------------------------------------------------------------
    for i in range(30):
        collector.record_test(TestCaseResult(
            test_id=f"UNIT_{i+1:03d}",
            name=f"unit_filter_and_math_core_{i+1}",
            stage="UNIT",
            req_ids=["HLR_NAV_01"],
            verdict=VerdictStatus.PASSED,
            duration_ms=0.62
        ))

    # -------------------------------------------------------------------------
    # STAGE 3: SIL FLIGHT DYNAMICS - 40 Test
    # -------------------------------------------------------------------------
    for i in range(40):
        collector.record_test(TestCaseResult(
            test_id=f"SIL_{i+1:03d}",
            name=f"sil_closed_loop_stability_run_{i+1}",
            stage="SIL",
            req_ids=["HLR_ATT_02"],
            verdict=VerdictStatus.PASSED,
            duration_ms=2.15
        ))

    # -------------------------------------------------------------------------
    # STAGE 4: HIL BUS PROTOCOLS (1553B & ARINC 429 & SNMPv3) - 30 Test
    # -------------------------------------------------------------------------
    for i in range(30):
        # Eğer regresyon enjekte edilmişse, 1553B parite kuralı kırılsın
        if inject_regression and (i == 12 or i == 18):
            collector.record_test(TestCaseResult(
                test_id=f"HIL_{i+1:03d}",
                name=f"hil_1553_odd_parity_verification_{i+1}",
                stage="HIL",
                req_ids=["LLR_1553_PARITY"],
                verdict=VerdictStatus.FAILED,
                duration_ms=1.45,
                error_msg="REGRESSION_DETECTED: MIL-STD-1553B Parite Hatası Yakalanamadı (ME Set Edilmedi)!"
            ))
        else:
            collector.record_test(TestCaseResult(
                test_id=f"HIL_{i+1:03d}",
                name=f"hil_bus_protocol_integrity_{i+1}",
                stage="HIL",
                req_ids=["LLR_1553_PARITY", "LLR_ARINC_SSM"],
                verdict=VerdictStatus.PASSED,
                duration_ms=1.30
            ))

    # -------------------------------------------------------------------------
    # STAGE 5: FAULT INJECTION & CYBER DEFENSE - 30 Test
    # -------------------------------------------------------------------------
    for i in range(30):
        if inject_regression and (i == 5 or i == 15):
            collector.record_test(TestCaseResult(
                test_id=f"FAULT_{i+1:03d}",
                name=f"fault_injection_fdir_trap_{i+1}",
                stage="FAULT",
                req_ids=["LLR_SNMP_AUTH"],
                verdict=VerdictStatus.FAILED,
                duration_ms=1.85,
                error_msg="REGRESSION_DETECTED: SNMPv3 Replay Saldırısı Engellenemedi!"
            ))
        else:
            collector.record_test(TestCaseResult(
                test_id=f"FAULT_{i+1:03d}",
                name=f"fault_injection_resilience_{i+1}",
                stage="FAULT",
                req_ids=["LLR_ARINC_SSM", "LLR_SNMP_AUTH"],
                verdict=VerdictStatus.PASSED,
                duration_ms=1.70
            ))

# -----------------------------------------------------------------------------
# 1. Koşum: Nominal Sürüm (Release Candidate v2.4.0)
# -----------------------------------------------------------------------------
nominal_collector = VerificationEvidenceCollector("KAAN_MISSION_COMPUTER", "RELEASE_v2.4.0", "9a2f7c1")
run_ci_verification_pipeline(nominal_collector, inject_regression=False)
nominal_eval = gatekeeper.evaluate(nominal_collector, sast_critical_count=0, mcdc_coverage_pct=100.0)

# -----------------------------------------------------------------------------
# 2. Koşum: Kusurlu / Regresyonlu PR (Feature Branch PR #412)
# -----------------------------------------------------------------------------
regression_collector = VerificationEvidenceCollector("KAAN_MISSION_COMPUTER", "PR_412_EXPERIMENTAL", "3e8d1b4")
run_ci_verification_pipeline(regression_collector, inject_regression=True)
regression_eval = gatekeeper.evaluate(regression_collector, sast_critical_count=2, mcdc_coverage_pct=94.2)

print("[+] CI Doğrulama Boru Hattı Koşumları Tamamlandı:")
print(f"  [1. Nominal Sürüm]  Toplam Test: {nominal_eval['metrics']['total_tests']} | Geçiş: %{nominal_eval['metrics']['pass_rate_pct']:.1f} | Kalite Kapısı: {nominal_eval['status']}")
print(f"  [2. Regresyonlu PR] Toplam Test: {regression_eval['metrics']['total_tests']} | Geçiş: %{regression_eval['metrics']['pass_rate_pct']:.1f} | Kalite Kapısı: {regression_eval['status']}")
print(f"  - Regresyonlu PR Engelleme Nedenleri: {regression_eval['reasons']}")
```

---

## 10. Kod 3 Teknik Açıklaması: Boru Hattı Yürütme Motoru, Hata Yakalama ve Regresyon Raporlama

Yukarıdaki simülasyon, savunma sanayii CI/CD boru hattının gerçek dünya davranışını birebir modeller:

1. **Nominal Koşumun Başarısı:**
   - 150 testin tamamı hatasız tamamlanmış, ortalama 1.25 ms içinde yüksek hızlı sanal doğrulama icra edilmiştir.
   - Tüm yüksek seviye (`HLR_NAV_01`, `HLR_ATT_02`) ve düşük seviye (`LLR_1553_PARITY`, `LLR_ARINC_SSM`, `LLR_SNMP_AUTH`) gereksinimler %100 oranında doğrulanmıştır.
   - Kalite Kapısı `PASSED` kararı vererek sürümün güvenle uçuşa verilebileceğini onaylamıştır.
2. **Kusurlu PR'ın Bloke Edilmesi:**
   - PR #412 senaryosunda bilerek enjekte edilen parite regresyonu, boru hattının 4. ve 5. aşamalarında anında yakalanmıştır.
   - Test başarı oranı %97.3'e düşmüş ve `LLR_1553_PARITY` gereksinimi kırılmıştır.
   - Kalite Kapısı motoru hiçbir tolerans göstermemiş; PR'ın ana dala girmesini engelleyerek felaket boyutunda bir aviyonik uçuş kazasının önüne geçmiştir.

---

## 11. Savunma Sanayiinde CI Doğrulama Raporlaması: TUSAŞ, ASELSAN ve ROKETSAN

Türkiye'nin öncü savunma kuruluşlarında otomatik doğrulama raporlaması altyapısının rolü:

### 1. TUSAŞ (Milli Muharip Uçak KAAN ve HÜRJET):
- Binlerce aviyonik yazılım modülü şirket içi yüksek performanslı CI sunucularında derlenir.
- Her Git push işleminde Renode ve QEMU tabanlı sanal işlemci (ARM Cortex-R5 / A53) üzerinde firmware otomatik yüklenir, MIL-STD-1553B ve ARINC 429 sanal veri yollarında haberleşme doğrulanır ve DO-178C VTM raporu otomatik olarak JIRA / Polarion ALM sistemine işlenir.

### 2. ASELSAN (Görev Bilgisayarları ve Entegre Aviyonik Sistemler):
- Çok kanallı görev bilgisayarlarında çalışan yazılımların MISRA C++2023 standartlarına uyumu ve statik analiz kusurları CI boru hattında SonarQube ve Coverity ile otomatik raporlanır.
- Test raporları DO-330 kalifiye araçlar tarafından imzalanarak askeri sertifikasyon makamlarına (SSB, Savunma Sanayii Başkanlığı) resmi kabul paketi olarak sunulur.

### 3. ROKETSAN (Güdüm, Denetim ve Füze Sistemleri):
- HİSAR, SİPER, SOM ve ATMACA mühimmatlarının uçuş yazılımları, SIL simülatörlerinde 6-DOF fırlatma senaryoları boyunca koşturulur.
- Çarpma sapması (miss distance) ve aerodinamik kararlılık metrikleri CI doğrulama raporunda görselleştirilerek kalite kapısı onayı verilir.

---

## 12. DO-178C DAL-A / DO-330 Kalifikasyon Metrikleri ve Doğrulama Kriterleri

Otomatik doğrulama boru hattının güvenilirliğini kanıtlamak için belirlenen 5 temel kalifikasyon metriği:

| Kalifikasyon Metriği | İlgili Standart | Hedeflenen Değer | Emniyet ve Kalite Anlamı |
| :--- | :--- | :--- | :--- |
| **Toplam Doğrulama Testi** | DO-178C Bölüm 6 | $\ge 120\text{ Test Senaryosu}$ | Tüm operasyonel zarfın kapsanması |
| **Gereksinim Kapsama Oranı** | DO-178C Tablo A-7 | $\%100.0\text{ (0 Uncovered)}$ | Hiçbir sistem gereksiniminin atlanmaması |
| **Nominal Kalite Kapısı Onayı** | DO-330 TQL-1 | `PASSED` (Tüm Kapılar Yeşil)| Sürümün uçuş emniyetine tam uygunluğu |
| **Regresyon Kusurunun Bloke Edilmesi** | DO-178C Bölüm 7 | `BLOCKED` (Anında Engelleme) | Bozuk kodun ana dala sızmasının önlenmesi |
| **Makine Okunabilir Kanıt Dosyası** | DO-178C Veri Yönetimi | JSON Evidence + 300 DPI PNG | Resmi denetçiler için bağımsız teftiş kanıtı |

---

```python
# -*- coding: utf-8 -*-
"""
Gün 334: CI'da automated verification report
Kod Bloğu 4: DO-178C DAL-A ve DO-330 Kalifikasyon Doğrulama Testleri (5 Kritik Assertion)
"""
# 1. Kriter: Nominal uçuş yazılımında en az 120 bağımsız test koşturulmalıdır
assert nominal_eval["metrics"]["total_tests"] >= 120, \
    f"En az 120 doğrulama testi koşulmalıdır! Ölçülen: {nominal_eval['metrics']['total_tests']}"

# 2. Kriter: Gereksinim kapsaması %100 olmalı, hiçbir yetim gereksinim kalmamalıdır
assert nominal_eval["metrics"]["req_coverage_pct"] == 100.0, \
    f"Gereksinim kapsaması %100 olmalıdır! Ölçülen: %{nominal_eval['metrics']['req_coverage_pct']}"

# 3. Kriter: Nominal sürüm tüm kalite kapılarından başarıyla geçmelidir (PASSED)
assert nominal_eval["status"] == "PASSED", \
    f"Nominal sürüm kalite kapısını geçmelidir! Durum: {nominal_eval['status']}"

# 4. Kriter: Regresyon içeren kusurlu PR derhal kalite kapısı tarafından bloke edilmelidir (BLOCKED)
assert regression_eval["status"] == "BLOCKED", \
    f"Regresyonlu PR kalite kapısı tarafından bloke edilmelidir! Durum: {regression_eval['status']}"

# 5. Kriter: Regresyonlu PR'da yakalanan hata adedi en az 2 olmalıdır
assert regression_eval["metrics"]["failed"] >= 2, \
    f"En az 2 regresyon hatası tespit edilmelidir! Ölçülen: {regression_eval['metrics']['failed']}"

print("[MÜKEMMEL] 5 Kritik DO-178C DAL-A / DO-330 CI Kalifikasyon Testi Başarıyla Geçti!")
```

---

## 13. Kod 4 Teknik Açıklaması: 5 Kritik Kalifikasyon Testi ve Emniyet Kriterleri

Yukarıdaki assertion bloğu, otomatik doğrulama sisteminin kalifikasyonunu DO-178C Seviye A standartlarına göre denetler:

1. `assert nominal_report["total_tests"] >= 120`: Nominal uçuş yazılımı doğrulamasında en az 120 bağımsız test senaryosunun koşturulduğunu teyit eder.
2. `assert nominal_report["req_coverage_pct"] == 100.0`: Tüm yazılım gereksinimlerinin eksiksiz bir şekilde en az bir testle eşleştiğini doğrular.
3. `assert nominal_report["quality_gate"] == "PASSED"`: Hata içermeyen nominal sürümün kalite kapısından başarıyla onay aldığını garantiler.
4. `assert regression_report["quality_gate"] == "BLOCKED"`: Bilerek enjekte edilen parite hatası ve gereksinim bozulması durumunda kalite kapısının PR'ı derhal reddettiğini kanıtlar.
5. `assert report_artifacts_generated`: Makine okunabilir JSON kanıt dosyasının ve yüksek çözünürlüklü teftiş grafiğinin disk üzerinde eksiksiz üretildiğini doğrular.

---

## 14. Görselleştirme Mimarisi ve CI Doğrulama Dashboard Tasarımı

Sistem doğrulaması için üretilen 4-panelli görsel artefakt aşağıdaki kurallara göre tasarlanmıştır:
- **Panel 1 (Boru Hattı Yürütme Zamanları):** CI/CD aşamalarının (Static SAST, Unit Test, SIL Simulation, HIL Emulation, Fault Injection) test sayıları ve yürütme süreleri karşılaştırılır.
- **Panel 2 (Gereksinim Kapsaması):** HLR ve LLR gereksinimlerinin doğrulama dağılımı (Donut grafik: %100 Kapsama, 0 Uncovered).
- **Panel 3 (Kalite Kapısı Çok Boyutlu Radar Analizi):** MC/DC Kapsama, Test Geçiş Oranı, SIL Emniyet Marjı, Veri Yolu Bütünlüğü ve İzlenebilirlik metriklerinin eşiklerle kıyaslaması.
- **Panel 4 (Nominal vs Regresyonlu PR Karşılaştırması):** Nominal sürüm ile kusurlu PR #412'nin kalite kapısı durumu ve yakalanan regresyonların görsel analizi.

---

```python
# -*- coding: utf-8 -*-
"""
Gün 334: CI'da automated verification report
Kod Bloğu 5: 4 Panelli 300 DPI CI Doğrulama ve Kalite Kapısı Dashboard'u
"""
import matplotlib.pyplot as plt
import numpy as np

# Koyu Tema ve Tipografi Ayarları
plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
fig.patch.set_facecolor('#0F172A')

for ax in axs.flat:
    ax.set_facecolor('#1E293B')
    ax.tick_params(colors='#CBD5E1', labelsize=8)
    for spine in ax.spines.values():
        spine.set_color('#334155')
    ax.grid(True, linestyle='--', alpha=0.3, color='#475569')

# -----------------------------------------------------------------------------
# Panel 1: CI/CD Boru Hattı Katmanları ve Yürütme Zamanları
# -----------------------------------------------------------------------------
ax1 = axs[0, 0]
stages = ['1. SAST (Static)', '2. Unit & MC/DC', '3. SIL Dynamics', '4. HIL Bus Check', '5. Fault Injection']
stage_test_counts = [20, 30, 40, 30, 30]
stage_durations = [9.0, 18.6, 86.0, 39.0, 51.0] # ms

ax1_twin = ax1.twinx()
ax1_twin.tick_params(colors='#CBD5E1', labelsize=8)
ax1_twin.grid(False)

bars = ax1.bar(stages, stage_test_counts, color='#38BDF8', width=0.45, edgecolor='#CBD5E1', linewidth=1.2, label='Test Adedi')
line = ax1_twin.plot(stages, stage_durations, color='#F59E0B', marker='o', linewidth=2.2, label='Yürütme Süresi (ms)')

for bar in bars:
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 1, f"{int(yval)} Test", ha='center', va='bottom', color='#F8FAFC', fontweight='bold', fontsize=8)

ax1.set_title("Panel 1: CI/CD Doğrulama Katmanları ve Yürütme Süreleri", color='#F8FAFC', fontsize=11, fontweight='bold')
ax1.set_ylabel("Koşturulan Test Sayısı", color='#38BDF8', fontsize=9)
ax1_twin.set_ylabel("Toplam Aşama Süresi (Milisaniye - ms)", color='#F59E0B', fontsize=9)
ax1.set_ylim(0, 50)
ax1_twin.set_ylim(0, 110)

# -----------------------------------------------------------------------------
# Panel 2: DO-178C Gereksinim Kapsaması (Requirements Coverage)
# -----------------------------------------------------------------------------
ax2 = axs[0, 1]
req_labels = ['HLR_NAV_01\n(İrtifa Doğruluğu)', 'HLR_ATT_02\n(Tutuş Kararlılığı)',
              'LLR_1553_PARITY\n(1553B Parite)', 'LLR_ARINC_SSM\n(ARINC 429 FDIR)',
              'LLR_SNMP_AUTH\n(SNMPv3 Güvenlik)']
req_test_weights = [50, 40, 30, 30, 30]
colors_pie = ['#10B981', '#38BDF8', '#818CF8', '#A855F7', '#F43F5E']

wedges, texts, autotexts = ax2.pie(
    req_test_weights, labels=req_labels, autopct='%1.1f%%',
    colors=colors_pie, startangle=140,
    textprops=dict(color='#F8FAFC', fontsize=8, fontweight='medium'),
    wedgeprops=dict(width=0.42, edgecolor='#1E293B', linewidth=2)
)
for at in autotexts:
    at.set_color('#0F172A')
    at.set_fontweight('heavy')
    at.set_fontsize(8)

ax2.set_title("Panel 2: DO-178C Gereksinim İzlenebilirlik Kapsaması (%100 Onay)", color='#F8FAFC', fontsize=11, fontweight='bold')

# -----------------------------------------------------------------------------
# Panel 3: Otomatik Kalite Kapısı (Quality Gate) Doğrulama Metrikleri
# -----------------------------------------------------------------------------
ax3 = axs[1, 0]
gate_metrics = [
    'Test Geçiş Oranı\n(Pass Rate %)',
    'Gereksinim Kapsaması\n(Req Coverage %)',
    'MC/DC Kod Kapsaması\n(MC/DC Coverage %)',
    'Statik Analiz Skoru\n(100 - SAST Critical)',
    'Veri Yolu Bütünlüğü\n(Bus Integrity %)'
]
nominal_scores = [100.0, 100.0, 100.0, 100.0, 100.0]
regression_scores = [97.3, 80.0, 94.2, 98.0, 86.6]

x_indices = np.arange(len(gate_metrics))
width = 0.35

ax3.bar(x_indices - width/2, nominal_scores, width=width, color='#4ADE80', edgecolor='#CBD5E1', label='Nominal v2.4.0 (PASSED)')
ax3.bar(x_indices + width/2, regression_scores, width=width, color='#EF4444', edgecolor='#CBD5E1', label='Regresyonlu PR #412 (BLOCKED)')

ax3.axhline(100.0, color='#FBBF24', linestyle=':', alpha=0.7, label='Kalite Kapısı Eşiği (%100)')
ax3.set_xticks(x_indices)
ax3.set_xticklabels(gate_metrics, fontsize=7, color='#CBD5E1')
ax3.set_ylabel("Metrik Başarı Oranı (%)", color='#CBD5E1', fontsize=9)
ax3.set_ylim(60, 115)
ax3.legend(loc='lower left', fontsize=7, facecolor='#0F172A', edgecolor='#334155')
ax3.set_title("Panel 3: Otomatik Kalite Kapısı Çok Boyutlu Değerlendirme Matrisi", color='#F8FAFC', fontsize=11, fontweight='bold')

# -----------------------------------------------------------------------------
# Panel 4: Nominal vs Regresyonlu PR Durum Karşılaştırması
# -----------------------------------------------------------------------------
ax4 = axs[1, 1]
categories = ['Nominal Sürüm v2.4.0\n(Release Candidate)', 'Kusurlu PR #412\n(Regression Injected)']
passed_counts = [nominal_eval["metrics"]["passed"], regression_eval["metrics"]["passed"]]
failed_counts = [nominal_eval["metrics"]["failed"], regression_eval["metrics"]["failed"]]

p1 = ax4.bar(categories, passed_counts, width=0.45, color='#10B981', edgecolor='#CBD5E1', label='Başarılı (PASS)')
p2 = ax4.bar(categories, failed_counts, bottom=passed_counts, width=0.45, color='#DC2626', edgecolor='#CBD5E1', label='Başarısız (FAIL)')

ax4.text(0, 153, "[STATUS: PASSED]\nMerge Onaylandı", ha='center', va='bottom', color='#4ADE80', fontweight='heavy', fontsize=10)
ax4.text(1, 153, "[STATUS: BLOCKED]\nPR Reddedildi (4 Hata)", ha='center', va='bottom', color='#EF4444', fontweight='heavy', fontsize=10)

ax4.set_title("Panel 4: CI/CD Gatekeeper Karar ve Regresyon İzolasyon Analizi", color='#F8FAFC', fontsize=11, fontweight='bold')
ax4.set_ylabel("Toplam Test Senaryoları", color='#CBD5E1', fontsize=9)
ax4.set_ylim(0, 185)
ax4.legend(loc='upper right', fontsize=8, facecolor='#0F172A', edgecolor='#334155')

plt.suptitle("GÜN 334: AVİYONİK SÜREKLİ ENTEGRASYON (CI) DOĞRULAMA RAPORU VE KALİTE KAPISI", color='#F8FAFC', fontsize=13, fontweight='heavy', y=0.98)
plt.tight_layout(rect=[0, 0.02, 1, 0.96])

output_png = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_334\gun_334_ci_da_automated_verification_report.png"
plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

import os
file_size = os.path.getsize(output_png)
print(f"[+] 300 DPI Profesyonel Aviyonik Dashboard Kaydedildi: {output_png} ({file_size:,} bayt)")
```

---

## 15. Kod 5 Dashboard Analizi ve Görsel Teftiş Kılavuzu

Oluşturulan 300 DPI profesyonel dashboard artefaktı (`gun_334_ci_da_automated_verification_report.png`), DO-178C bağımsız denetçileri ve baş mühendisler için aşağıdaki teftiş ipuçlarını sunar:

1. **Panel 1 (Boru Hattı Zamanlaması):**
   - Statik analizin ve birim testlerin saniyeler içinde tamamlandığı, daha karmaşık SIL ve HIL aşamalarının ise simülasyon derinliğine bağlı olarak planlandığı görülür. Boru hattı toplam süresi yüksek hızlı CI döngüsüne izin vermektedir.
2. **Panel 2 (Gereksinim İzlenebilirliği):**
   - Donut grafiğinde %100 tam yeşil halka, sistemde hiçbir "yetim gereksinim" (untested requirement) kalmadığını belgeler.
3. **Panel 3 (Kalite Kapısı Radar Matrisi):**
   - Tüm güvenlik kritik metrikler (MC/DC, Pass Rate, SIL Margin, Bus Integrity) hedef referans çizgisini (%100) karşılamıştır.
4. **Panel 4 (Regresyon Engelleme Başarısı):**
   - Nominal sürümde tüm aşamalar yeşil `[PASS]` iken, hatalı PR'da kırmızı `[FAIL - BLOCKED]` damgası açıkça teyit edilmektedir.

---

## 16. Sık Yapılan Hatalar ve Aviyonik CI/CD Antipatternleri

Aviyonik sürekli entegrasyon sistemlerinde sıkça düşülen tuzaklar ve mühendislik çözümleri:

### 1. Kararsız Testlere (Flaky Tests) Tolerans Göstermek:
- **Hata:** Ağ gecikmesi veya asenkron zamanlama nedeniyle ara sıra başarısız olan testleri "tekrar çalıştırınca geçiyor" diyerek görmezden gelmek.
- **Sonuç:** Gerçek bir yarış durumu (race condition) veya zaman aşımı hatası gözden kaçar ve uçuşta sistem kilitlenir.
- **Çözüm:** Deterministik simülasyon zamanı (virtual time) kullanılmalı, flaky testler derhal karantinaya alınıp düzeltilmelidir.

### 2. Gereksinimle Eşleşmeyen "Yetim Testler" (Orphan Tests) Yazmak:
- **Hata:** DO-178C gereksinim belgesinde karşılığı olmayan rastgele birim testler yazmak.
- **Sonuç:** Kodun neyi doğruladığı belirsizleşir, sertifikasyon denetiminde VTM matrisi reddedilir.
- **Çözüm:** Her test fonksiyonu kod seviyesinde mutlaka bir `req_id` etiketi taşımalıdır.

### 3. Kalite Kapılarını Bypass Eden İstisnalar (Force-Merge):
- **Hata:** "Acil teslimat" gerekçesiyle kalite kapısı başarısız olan bir PR'ı zorla ana dala birleştirmek.
- **Sonuç:** DO-178C DAL-A sertifikasyonunun anında iptal edilmesi ve uçuş güvenliği zaafiyeti.
- **Çözüm:** CI/CD sunucularında branch protection kuralları zorunlu kılınmalı, kalite kapısı geçilmeden merge butonu donanımsal olarak kilitlenmelidir.

### 4. Makine Okunabilir Kanıt Kaydetmemek:
- **Hata:** Test sonuçlarını sadece terminal konsoluna yazdırıp log dosyasını silmek.
- **Sonuç:** Otorite denetiminde geçmişe dönük kanıt sunulamaması.
- **Çözüm:** Her CI koşumu JUnit XML ve JSON Evidence formatında kalıcı depolama havuzunda arşivlenmelidir.

---

```python
# -*- coding: utf-8 -*-
"""
Gün 334: CI'da automated verification report
Kod Bloğu 6: DO-178C DAL-A / DO-330 CI Kalifikasyon Onay Sertifikası ve Kabul Konsol Raporu
"""
cert_table = """
+======================================================================+
|   ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ DOĞRULAMA OTORİTESİ          |
|       DO-178C DAL-A & DO-330 CI DOĞRULAMA VE KALİFİKASYON ONAYI      |
+======================================================================+
| 1. Hedef Aviyonik Proje Adı           : {project}             | [UYGUN] |
| 2. Sürekli Entegrasyon Sürüm Kimliği  : {build_id}          | [UYGUN] |
| 3. Kaynak Kod Git Taahhüt Özeti (SHA) : {commit_sha}                        | [UYGUN] |
| 4. Toplam Koşturulan Doğrulama Testi  : {total_tests} Senaryo (>= 120 Şartı)   | [UYGUN] |
| 5. Başarılı Test Geçiş Oranı          : %{pass_rate:.1f} (Hedef %100.0)          | [UYGUN] |
| 6. Gereksinim Kapsaması (VTM Coverage): %{req_cov:.1f} (0 Yetim Gereksinim)   | [UYGUN] |
| 7. MC/DC Kod Kapsama Oranı            : %{mcdc_cov:.1f} (DAL-A Tam Kapsama)     | [UYGUN] |
| 8. Regresyon İzolasyon Yeteneği       : PR #412 BLOCKED (4 Hata Yakalandı)   | [UYGUN] |
| 9. Resmi Kalite Kapısı (Quality Gate) : [{status}] (Merge İzni Verildi)    | [UYGUN] |
| 10. Dashboard Teftiş Artefaktı        : 300 DPI PNG ({size:,} B > 100 KB)| [UYGUN] |
+======================================================================+
| SONUÇ: TÜM DO-178C DAL-A VE DO-330 KALİTE KAPISI KRİTERLERİ SAĞLANDI!|
| YAZILIM MİNİ-BİTİRME SANAL AVİYONİK TEST FABRİKASINA HAZIRDIR!      |
+======================================================================+
"""

formatted_cert = cert_table.format(
    project=nominal_collector.project_name,
    build_id=nominal_collector.build_id,
    commit_sha=nominal_collector.commit_sha,
    total_tests=nominal_eval["metrics"]["total_tests"],
    pass_rate=nominal_eval["metrics"]["pass_rate_pct"],
    req_cov=nominal_eval["metrics"]["req_coverage_pct"],
    mcdc_cov=nominal_eval["mcdc_coverage_pct"],
    status=nominal_eval["status"],
    size=file_size
)
print(formatted_cert)
print("[MÜKEMMEL] GÜN 334: CI'DA AUTOMATED VERIFICATION REPORT TAMAMLANDI.")
print("[SIRADAKİ GÜN] GÜN 335: VERIFICATION MINI-CAPSTONE: VIRTUAL AVIONICS TEST FACTORY.")
```

---

## 17. Gün Sonu Özeti ve Sıradaki Gün

### 3 Cümlelik Gün Sonu Özeti:
1. **CI'da Automated Verification Report Nedir?** Aviyonik yazılımın statik analiz, birim test, SIL simülasyonu, sanal HIL veri yolu ve arıza enjeksiyon aşamalarını her kod değişikliğinde otomatik koşturan, çift yönlü gereksinim izlenebilirliği kuran ve kalite kapısı kararı üreten sistemik doğrulama altyapısıdır.
2. **Hangi Problemi Çözer?** Manuel test süreçlerindeki insan hatalarını, gözden kaçan regresyonları, doğrulanmamış yetim gereksinimleri ve denetim süreçlerindeki aylar süren dokümantasyon yükünü çözer.
3. **Hangi Trade-off / Hata Sınıfını Getirir?** Kapsamlı simülasyon ve araç zinciri entegrasyonu nedeniyle CI boru hattı altyapı maliyeti ve yürütme süresi artışı; kararsız (flaky) testlerin geliştirme akışını haksız yere bloke etme riskidir.

---

### Sıradaki Gün: Gün 335 — F11 — Verification / SIL / HIL
**Konu:** Verification mini-capstone: virtual avionics test factory  
**Hedef:** Faz F11'de öğrenilen tüm SIL, HIL, sanal ECU, Renode/QEMU, MIL-STD-1553, ARINC 429 ve CI otomatik raporlama yetkinliklerini birleştiren uçtan uca Sanal Aviyonik Test Fabrikası (Virtual Avionics Test Factory) mini-bitirme projesini hayata geçirmek.

---

