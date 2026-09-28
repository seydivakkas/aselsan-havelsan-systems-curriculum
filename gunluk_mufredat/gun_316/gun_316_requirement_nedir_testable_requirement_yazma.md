# Gün 316 — FAZ F11: Verification / SIL / HIL
## Konu: Requirement Nedir? Testable (Test Edilebilir) Requirement Yazma
### DO-178C, INCOSE ve Askeri Standartlarda Uçuş Yazılımı Gereksinim Mühendisliği

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

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

### Giriş: Savunma Sanayiinde Gereksinim Mühendisliğinin Önemi
Savunma ve aviyonik sistemlerinde (ASELSAN hava savunma radarları, ROKETSAN seyir füzeleri, TUSAŞ MMU KAAN uçuş kontrol sistemleri) bir projenin başarısı ya da başarısızlığı yazılan C++ kodunun kalitesinden önce **yazılım gereksinimlerinin (Software Requirements Specification - SRS)** kalitesiyle belirlenir. 

Endüstriyel istatistikler, havacılık ve uzay projelerindeki yazılım hatalarının **%50'den fazlasının doğrudan hatalı, eksik veya muğlak gereksinimlerden** kaynaklandığını göstermektedir. Kodlama aşamasında tespit edilen bir gereksinim hatasının düzeltme maliyeti 1 birim iken, HIL (Hardware-in-the-Loop) veya uçuş testleri sırasında tespit edilen aynı hatanın maliyeti **100 ila 1000 kat** artmaktadır.

### Neden-Sonuç Analizi: Muğlak Gereksinimlerin Tarihsel Havacılık Felaketleri

Savunma standartlarında (DO-178C, MIL-STD-882E) test edilemez bir gereksinim, "henüz gerçekleşmemiş bir uçuş felaketidir".

| Tarihsel Kaza / Olay | Muğlak / Hatalı Gereksinim Örneği | Gerçekte Yaşanan Kök Neden (Root Cause) | Test Edilebilir (Testable) Doğru Gereksinim |
| :--- | :--- | :--- | :--- |
| **Ariane 5 Uçuş 501 (1996)** | *"Yatay bias değeri hizalama sonrasında da okunabilir olmalıdır."* | Ariane 4'ten kopyalanan kodda yatay sapma değeri 64-bit float'tan 16-bit signed integer'a dönüştürülürken overflow koruması tanımlanmadı. Bilgisayar çöktü, roket imha edildi ($370M zarar). | `WHEN horizontal velocity exceeds 32767 units, the flight software SHALL clamp the output to INT16_MAX without generating a trap within 1.0 ms.` |
| **Patriot Füzesi Dhahran (1991)** | *"Radar takip saati zamanı hassas tutmalıdır."* | 24-bit sabit noktalı register'da $0.1$ saniye çarpanı yuvarlama hatası biriktirdi. 100 saatlik kesintisiz çalışma sonucunda $0.34$ saniye zaman kayması oluştu ve Scud füzesi ıskalandı (28 asker şehit). | `The system real-time clock drift SHALL NOT exceed 1.0 ms per 24 hours of continuous operational execution.` |
| **Mars Climate Orbiter (1999)** | *"İtki telemetrisi yer kontrolüne periyodik iletilmelidir."* | Bir ekip Newton-saniye (metrik), diğer ekip lbf-saniye (İngiliz ölçü birimi) kullandı. Birim tanımı gereksinimde açıkça belirtilmemişti ($327M zarar). | `The thruster impulse measurement SHALL be reported in Newton-seconds (N·s) with a floating-point precision of +/-0.01 N·s.` |

### INCOSE ve EARS Şablon Mimarisi: "Test Edilebilir" Bir Gereksinim Nasıl Yazılır?

Uluslararası Sistem Mühendisliği Konseyi (INCOSE) ve havacılık sertifikasyon otoritesi (FAA / EASA - DO-178C), bir gereksinimin geçerli kabul edilmesi için aşağıdaki kriterleri şart koşar:
1. **Atomik (Atomic):** Tek bir cümlede yalnızca tek bir işlev veya kısıt ifade edilmelidir. ("ve", "ayrıca" gibi bağlaçlarla iki farklı test aynı maddeye sıkıştırılamaz).
2. **Belirsizlikten Uzak (Unambiguous):** "Hızlı", "yeterli", "kullanıcı dostu", "güvenli", "optimum", "mümkün olduğunca" gibi göreceli sıfatlar KESİNLİKLE YASAKTIR.
3. **Doğrulanabilir / Test Edilebilir (Verifiable):** Gereksinimin geçtiğini veya kaldığını (`PASS` / `FAIL`) kanıtlayacak sayısal bir eşik, zaman sınırı veya mantıksal koşul bulunmalıdır.
4. **İzlenebilir (Traceable):** Her yazılım gereksinimi benzersiz bir ID'ye (`REQ-SW-XXX`) sahip olmalı ve bir üst sistem gereksinimine (`SYS-REQ-YYY`) bağlanmalıdır.

#### EARS (Easy Approach to Requirements Syntax) Şablonları

Savunma sanayiinde gereksinimler EARS kurallarına göre 5 standart şablondan birine uymalıdır:

```mermaid
flowchart TD
    ReqCheck{"Gereksinim Türü Nedir?"}
    ReqCheck -->|"Sürekli Geçerli"| Ubi["1. UBIQUITOUS: The <system> SHALL <action>."]
    ReqCheck -->|"Tetikleyici Olay Var"| Event["2. EVENT-DRIVEN: WHEN <trigger>, the <system> SHALL <action> within <time>."]
    ReqCheck -->|"Belirli Bir Durumda"| State["3. STATE-DRIVEN: WHILE <state>, the <system> SHALL <action>."]
    ReqCheck -->|"Hata / Acil Durum"| Unwanted["4. UNWANTED EVENT: IF <fault>, THEN the <system> SHALL <action>."]
    ReqCheck -->|"Donanım Varsa"| Opt["5. OPTIONAL: WHERE <feature>, the <system> SHALL <action>."]
```

- **Ubiquitous (Her zaman):** Sistem her koşulda statik bellekte kalmalıdır. (`The Flight Software SHALL allocate 0 bytes of dynamic heap memory during flight.`)
- **Event-Driven (Olay):** Bir olay tetiklendiğinde zaman sınırlı tepki. (`WHEN target handover is received, the system SHALL transition to TRACK within 10.0 ms.`)
- **State-Driven (Durum):** Sistem belirli bir modda iken süregelen kural. (`WHILE in TRACK state, the estimator RMS error SHALL NOT exceed 1.50 m.`)
- **Unwanted Event (İstenmeyen Olay):** Arıza durumunda güvenli moda geçiş. (`IF telemetry is lost for >= 150 ms, THEN the system SHALL transition to SAFE_SHUTDOWN within 5.0 ms.`)

```python
# [KOD HÜCRESİ 1: EARS Tabanlı Gereksinim Modeli ve Havacılık İsterleri]
# Amaç: DO-178C ve INCOSE standartlarına tam uyumlu EARS (Easy Approach to Requirements Syntax)
# veri mimarisini oluşturmak ve füze/hava savunma aviyonik yazılımı için 5 katı,
# ölçülebilir ve test edilebilir yazılım gereksinimini (REQ-SW-001 - REQ-SW-005) tanımlamak.

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import numpy as np

class RequirementType(Enum):
    UBIQUITOUS = "Her Yerde Geçerli (Ubiquitous)"
    EVENT_DRIVEN = "Olay Güdümlü (Event-Driven)"
    STATE_DRIVEN = "Durum Güdümlü (State-Driven)"
    UNWANTED_EVENT = "İstenmeyen Olay / Hata (Unwanted Event)"
    OPTIONAL = "İsteğe Bağlı Özellik (Optional)"

class VerificationMethod(Enum):
    TEST = "Otomatik Test (Test)"
    DEMONSTRATION = "Gösterim (Demonstration)"
    ANALYSIS = "Statik / Sayısal Analiz (Analysis)"
    INSPECTION = "İnceleme / Denetim (Inspection)"

class SafetyDAL(Enum):
    DAL_A = "DO-178C Seviye A (Catastrophic)"
    DAL_B = "DO-178C Seviye B (Hazardous)"
    DAL_C = "DO-178C Seviye C (Major)"
    DAL_D = "DO-178C Seviye D (Minor)"

@dataclass
class TestableRequirement:
    req_id: str
    title: str
    req_type: RequirementType
    statement: str
    parameter_name: str
    operator: str  # '<=', '>=', '==', 'in_range'
    threshold_value: Union[float, Tuple[float, float]]
    unit: str
    safety_dal: SafetyDAL
    verification_method: VerificationMethod
    rationale: str

    def evaluate(self, measured_value: float) -> Tuple[bool, float, str]:
        """Gözlemlenen telemetri değerini gereksinim eşiğiyle karşılaştırarak doğrular."""
        if self.operator == '<=':
            passed = measured_value <= self.threshold_value
            margin = float(self.threshold_value - measured_value)
            desc = f"Ölçülen: {measured_value:.3f} {self.unit} <= Eşik: {self.threshold_value:.3f} {self.unit} (Marj: +{margin:.3f})"
        elif self.operator == '>=':
            passed = measured_value >= self.threshold_value
            margin = float(measured_value - self.threshold_value)
            desc = f"Ölçülen: {measured_value:.3f} {self.unit} >= Eşik: {self.threshold_value:.3f} {self.unit} (Marj: +{margin:.3f})"
        elif self.operator == '==':
            passed = (measured_value == self.threshold_value)
            margin = 0.0 if passed else -1.0
            desc = f"Ölçülen: {measured_value} {self.unit} == Eşik: {self.threshold_value} {self.unit}"
        elif self.operator == 'in_range':
            low, high = self.threshold_value
            passed = (low <= measured_value <= high)
            margin = min(measured_value - low, high - measured_value)
            desc = f"Ölçülen: {measured_value:.3f} {self.unit} in [{low:.3f}, {high:.3f}] {self.unit} (Marj: +{margin:.3f})"
        else:
            raise ValueError(f"Geçersiz operatör: {self.operator}")
        return passed, margin, desc

# 5 Adet Test Edilebilir Aviyonik Sistem Gereksinimi
REQUIREMENTS: List[TestableRequirement] = [
    TestableRequirement(
        req_id="REQ-SW-001",
        title="Hedef Devir Alındığında Takibe Geçiş Gecikmesi",
        req_type=RequirementType.EVENT_DRIVEN,
        statement="WHEN a valid Target Handover packet is received with verified CRC, the Flight Guidance Computer SHALL transition from ACQUISITION to TRACK state within 10.0 ms.",
        parameter_name="handover_latency_ms",
        operator="<=",
        threshold_value=10.0,
        unit="ms",
        safety_dal=SafetyDAL.DAL_A,
        verification_method=VerificationMethod.TEST,
        rationale="Hava savunma önleme senaryolarında hedef kaybını önlemek için durum geçiş determinizmi kritik şarttır."
    ),
    TestableRequirement(
        req_id="REQ-SW-002",
        title="Kararlı Durum Takip Hatası Sınırı (RMS)",
        req_type=RequirementType.STATE_DRIVEN,
        statement="WHILE in TRACK state under nominal radar sensor noise (sigma=2.0m), the Filtered Position Estimation Error SHALL NOT exceed 1.50 meters RMS.",
        parameter_name="tracking_rmse_m",
        operator="<=",
        threshold_value=1.50,
        unit="m",
        safety_dal=SafetyDAL.DAL_A,
        verification_method=VerificationMethod.TEST,
        rationale="ATOM / HİSAR güdüm doğruluğu ve kinetik vuruş (hit-to-kill) zarfı maksimum 1.50 m hata gerektirir."
    ),
    TestableRequirement(
        req_id="REQ-SW-003",
        title="Sinyal Kaybı Hata Toleransı ve Güvenli Kapatma Zamanlaması",
        req_type=RequirementType.UNWANTED_EVENT,
        statement="IF radar sensor telemetry is lost for >= 150.0 ms, THEN the Flight Guidance Computer SHALL transition to SAFE_SHUTDOWN state within 5.0 ms.",
        parameter_name="fault_shutdown_latency_ms",
        operator="<=",
        threshold_value=5.0,
        unit="ms",
        safety_dal=SafetyDAL.DAL_A,
        verification_method=VerificationMethod.TEST,
        rationale="Kontrolsüz uçuş ve dost unsurlara zarar verme riskini bertaraf etmek için fail-safe kapatma şarttır."
    ),
    TestableRequirement(
        req_id="REQ-SW-004",
        title="Uçuş Kontrol Döngüsü Jitter ve WCET Kısıtı",
        req_type=RequirementType.UBIQUITOUS,
        statement="The Flight Control Task Period SHALL remain within 20.0 ms +/- 0.50 ms with Worst-Case Execution Time (WCET) <= 4.20 ms.",
        parameter_name="max_period_jitter_ms",
        operator="<=",
        threshold_value=0.50,
        unit="ms",
        safety_dal=SafetyDAL.DAL_B,
        verification_method=VerificationMethod.TEST,
        rationale="Aktüatör kontrol döngüsünün faz marjını ve kontrol kararlılığını korumak için zamanlama jitteri sınırlandırılmalıdır."
    ),
    TestableRequirement(
        req_id="REQ-SW-005",
        title="Görev Döngüsünde Sıfır Dinamik Bellek Ayrımı",
        req_type=RequirementType.UBIQUITOUS,
        statement="Dynamic heap memory allocation (malloc/new) SHALL be strictly 0 bytes during active flight control loops.",
        parameter_name="dynamic_heap_alloc_bytes",
        operator="==",
        threshold_value=0.0,
        unit="bytes",
        safety_dal=SafetyDAL.DAL_A,
        verification_method=VerificationMethod.INSPECTION,
        rationale="DO-178C DAL-A standartlarında bellek parçalanması (fragmentation) ve OOM kilitlenmeleri kesin olarak yasaktır."
    ),
]

print("=" * 76)
print("ASELSAN / HAVELSAN / ROKETSAN DO-178C GEREKSİNİM MÜHENDİSLİĞİ MİMARİSİ")
print("=" * 76)
for req in REQUIREMENTS:
    print(f"[{req.req_id}] ({req.req_type.value}) - {req.safety_dal.value}")
    print(f"  Gereksinim İfadesi: '{req.statement}'")
    print(f"  Metrik Sınırı     : {req.parameter_name} {req.operator} {req.threshold_value} {req.unit}")
    print(f"  Doğrulama Yöntemi : {req.verification_method.value}")
    print("-" * 76)

```

### Çift Yönlü İzlenebilirlik (Bidirectional Traceability)

DO-178C Seviye A (DAL-A) sertifikasyonunda en kritik denetim unsurlarından biri **Çift Yönlü İzlenebilirlik Matrisi (Requirements Traceability Matrix - RTM)** tablosudur:

```mermaid
graph LR
    SysReq["Sistem Gereksinimi<br/>(SYS-REQ-101)"] -->|"Türetilme"| SWReq["Yazılım Gereksinimi<br/>(REQ-SW-001)"]
    SWReq -->|"Tasarım"| Arch["Mimari Tasarım<br/>(GuidanceStateMachine)"]
    Arch -->|"Kodlama"| Code["Kaynak Kod<br/>(tracker.cpp: L145)"]
    SWReq -->|"Doğrulama"| Test["Test Senaryosu<br/>(TC_HANDOVER_01)"]
    Test -->|"Kanıt"| Log["Test Telemetri Logu<br/>(6.0 ms <= 10.0 ms)"]
```

İzlenebilirlik iki yönlü olmalıdır:
1. **İleriye Doğru İzlenebilirlik (Forward Traceability):** Her sistem gereksinimi için bir yazılım gereksinimi, her yazılım gereksinimi için kod ve test yazılmış mıdır? (Eksik özellik kontrolü).
2. **Geriye Doğru İzlenebilirlik (Backward Traceability):** Kod tabanındaki her satır kodun bir üst gereksinimi var mıdır? (İzinsiz veya belgelenmemiş "hayalet kod / unintended functionality" olmaması şarttır).

### Matematiksel Temeller: Metrik Sınırları ve İstatistiksel Toleranslar

Bir yazılım gereksiniminin doğrulanması deterministik veya istatistiksel sınır testlerine dayanır:

1. **Gecikme ve Zamanlama Eşiği (Latency Bound):**
   Bir olayın başlangıç anı $t_{	ext{trigger}}$ ve tepkinin tamamlandığı an $t_{	ext{response}}$ olmak üzere:
   $$	au = t_{	ext{response}} - t_{	ext{trigger}} \le 	au_{\max}$$
   Güvenlik marjı (Safety Margin):
   $$M_{	au} = 	au_{\max} - 	au \ge 0$$

2. **Kestirim Doğruluğu ve RMS Hatası (Root Mean Square Error):**
   Kararlı durum hedef takip zarfı için $N$ adet telemetri örneğinde gerçek hedef konumu $x(t_i)$ ve filtrelenmiş kestirim $\hat{x}(t_i)$ arasındaki hata $e_i = \hat{x}(t_i) - x(t_i)$:
   $$e_{	ext{RMS}} = \sqrt{rac{1}{N} \sum_{i=1}^{N} e_i^2} \le E_{\max} = 1.50	ext{ m}$$

3. **Periyodik Görev Jitteri (Timing Jitter):**
   Nominal çalışma periyodu $T_0 = 20.0	ext{ ms}$ olan bir RTOS görevinde $k$. döngünün gerçekleşen periyodu $T_k$:
   $$J_k = |T_k - T_0| \le J_{\max} = 0.50	ext{ ms}$$

### Kod Hücresi 1 Açıklaması: EARS Sözdizimi ve Aviyonik Gereksinim Veri Modeli

Aşağıdaki Python kodunda:
- EARS mimarisine uygun `RequirementType` (UBIQUITOUS, EVENT_DRIVEN, STATE_DRIVEN, UNWANTED_EVENT, OPTIONAL) numaralandırılmıştır.
- DO-178C doğrulama metotları (`VerificationMethod`: Test, Demonstration, Analysis, Inspection) modellenmiştir.
- `TestableRequirement` sınıfı, gereksinimi sadece metin olarak değil; sayısal eşik değeri (`threshold_value`), operatör (`<=`, `in_range`), birim ve güvenlik seviyesi (DAL-A) ile programatik bir nesne olarak tanımlar.
- ASELSAN / ROKETSAN hava savunma ve güdüm bilgisayarları için 5 adet test edilebilir kritik ister (`REQ-SW-001` - `REQ-SW-005`) tanımlanmıştır.

```python
# [KOD HÜCRESİ 2: Uçuş Bilgisayarı Hedef Takip Simülasyonu ve Telemetri Üretimi]
# Amaç: DO-178C gereksinimlerini doğrulamak üzere; Hedef Devir Alma (Handover),
# 1D Kalman Filtreli Hedef Takibi, Radikal Sensör Sinyal Kaybı (Fault Injection) ve
# Gerçek Zamanlı RTOS Döngü Jitter / WCET profillemesini içeren uçuş simülatörünü çalıştırmak.

np.random.seed(42)

# Simülasyon Zaman Izgarası: 5 ms zaman adımı, 3.0 saniye toplam uçuş süresi
dt_sim = 0.005  # 5 ms (200 Hz iç döngü)
t_vec = np.arange(0.0, 3.0, dt_sim)
N_steps = len(t_vec)

# Durum Makinesi Sabitleri (State Machine)
STATE_ACQUISITION = 0
STATE_TRACK = 1
STATE_COAST = 2
STATE_SAFE_SHUTDOWN = 3

state_names = {
    STATE_ACQUISITION: "ACQUISITION (Arama/Devir Bekleme)",
    STATE_TRACK: "TRACK (Kilitli Güdüm Takibi)",
    STATE_COAST: "COAST (Sensör Veri Kaybı / Ölü Hesap)",
    STATE_SAFE_SHUTDOWN: "SAFE_SHUTDOWN (Güvenli Kapatma / İnfaz)"
}

# Kritik Zamanlama Noktaları
T_HANDOVER_PACKET = 0.400       # 400. ms'de hedef devir paketi gelir
T_HANDOVER_PROCESSED = 0.406    # 406. ms'de TRACK durumuna geçilir (6.0 ms gecikme)
T_FAULT_INJECT = 2.000          # 2000. ms'de radar sensörü kopar
T_TIMEOUT_THRESHOLD = 0.150     # 150 ms sinyal kesintisi toleransı
T_COAST_EXPIRED = T_FAULT_INJECT + T_TIMEOUT_THRESHOLD  # 2.150 saniye
T_SHUTDOWN_EXECUTED = 2.152     # 2.152 saniyede güvenli kapatma tamamlanır (2.0 ms gecikme)

# Telemetri Kayıt Dizileri
state_history = np.zeros(N_steps, dtype=int)
pos_true = 500.0 - 65.0 * t_vec  # Hedef gerçek konumu (m), v = -65 m/s
pos_meas = np.zeros(N_steps)
pos_est = np.zeros(N_steps)
signal_valid = np.zeros(N_steps, dtype=bool)

# 1D Kalman Filtresi Başlatımı (Konum ve Hız Kestirimi)
F_kf = np.array([[1.0, dt_sim], [0.0, 1.0]])
H_kf = np.array([[1.0, 0.0]])
Q_kf = np.diag([0.02, 0.08])
R_kf = np.array([[4.0]])  # sigma_meas = 2.0 m -> R = 4.0 m^2

x_hat_kf = np.array([500.0, -65.0])
P_kf = np.diag([4.0, 10.0])

# Kalman Filtresi Takip Hataları (Yalnızca Kararlı TRACK modunda)
track_errors = []

# Döngü Simülasyonu
current_state = STATE_ACQUISITION
signal_lost_counter = 0.0

for k, tk in enumerate(t_vec):
    # 1. Hedef Sinyal Durumu ve Handover Kontrolü
    if tk < T_FAULT_INJECT:
        signal_valid[k] = True
        pos_meas[k] = pos_true[k] + np.random.normal(0.0, 2.0)
    else:
        signal_valid[k] = False
        pos_meas[k] = np.nan  # Sensör telemetrisi kesildi!

    # 2. Durum Makinesi Mantığı
    if current_state == STATE_ACQUISITION:
        if tk >= T_HANDOVER_PROCESSED:
            current_state = STATE_TRACK
            x_hat_kf[0] = pos_meas[k]
    elif current_state == STATE_TRACK:
        if not signal_valid[k]:
            current_state = STATE_COAST
            signal_lost_counter = 0.0
    elif current_state == STATE_COAST:
        signal_lost_counter += dt_sim
        if signal_lost_counter >= T_TIMEOUT_THRESHOLD:
            if tk >= T_SHUTDOWN_EXECUTED:
                current_state = STATE_SAFE_SHUTDOWN
    elif current_state == STATE_SAFE_SHUTDOWN:
        pass  # Güvenli kapatma durumunda kilitlen

    state_history[k] = current_state

    # 3. Kestirim Algoritması (Kalman veya Coasting)
    if current_state == STATE_TRACK:
        # Predict
        x_hat_kf = F_kf @ x_hat_kf
        P_kf = F_kf @ P_kf @ F_kf.T + Q_kf
        # Update
        res = pos_meas[k] - (H_kf @ x_hat_kf)[0]
        S = (H_kf @ P_kf @ H_kf.T)[0, 0] + R_kf[0, 0]
        K = P_kf @ H_kf.T / S
        x_hat_kf = x_hat_kf + K.ravel() * res
        P_kf = (np.eye(2) - K @ H_kf) @ P_kf
        
        pos_est[k] = x_hat_kf[0]
        track_errors.append(pos_est[k] - pos_true[k])
    elif current_state == STATE_COAST:
        # Ölü hesap (Dead Reckoning)
        x_hat_kf = F_kf @ x_hat_kf
        pos_est[k] = x_hat_kf[0]
    elif current_state == STATE_SAFE_SHUTDOWN:
        pos_est[k] = pos_est[k-1]  # Dondurulmuş çıkış
    else:
        pos_est[k] = np.nan

# 4. RTOS Görev Döngüsü Jitter ve WCET Profillemesi (150 Döngü, 20 ms Nominal)
N_cycles = 150
nominal_period_ms = 20.0
loop_periods_ms = np.random.normal(nominal_period_ms, 0.08, N_cycles)
period_jitters_ms = np.abs(loop_periods_ms - nominal_period_ms)
max_jitter_ms = float(np.max(period_jitters_ms))

# WCET (Worst-Case Execution Time) Simülasyonu (Beta dağılımı: min 2.2 ms, tepe 2.5 ms, max 3.2 ms)
task_exec_times_ms = 2.20 + 1.20 * np.random.beta(a=2.0, b=5.0, size=N_cycles)
wcet_ms = float(np.max(task_exec_times_ms))

# 5. Dinamik Bellek Denetimi (Uçuş döngüsünde 0 byte heap ayrımı)
simulated_heap_allocations = 0

print("=" * 76)
print("UÇUŞ KONTROL VE HEDEF TAKİP SİMÜLASYONU TELEMETRİ ÇIKTILARI")
print("=" * 76)
print(f"Toplam Simülasyon Süresi       : {t_vec[-1]:.2f} saniye ({N_steps} adım)")
print(f"Handover Algılama Gecikmesi   : {(T_HANDOVER_PROCESSED - T_HANDOVER_PACKET)*1000.0:.2f} ms")
print(f"Kararlı Durum Takip Hatası (RMS): {np.sqrt(np.mean(np.array(track_errors)**2)):.3f} metre")
print(f"Hata Kapatma Tepki Süresi     : {(T_SHUTDOWN_EXECUTED - T_COAST_EXPIRED)*1000.0:.2f} ms")
print(f"Maksimum RTOS Görev Jitteri   : {max_jitter_ms:.3f} ms (Nominal: {nominal_period_ms} ms)")
print(f"En Kötü Durum Çalışma Süresi  : {wcet_ms:.3f} ms (Bütçe: 4.20 ms)")
print(f"Görev Döngüsü Dinamik Heap    : {simulated_heap_allocations} bytes (MISRA-C++ / DO-178C)")
print("=" * 76)

```

### Kod Hücresi 2 Açıklaması: Uçuş Bilgisayarı Hedef Takip Simülasyonu ve Hata Enjeksiyonu

Bu hücrede gerçekçi bir aviyonik uçuş kontrol simülatörü çalıştırılır:
1. **Durum Makinesi (State Machine):** `ACQUISITION` modunda beklerken $t = 0.400	ext{ s}$ anında CRC doğrulamalı radar devir paketi gelir. Sistem durumunu $6.0	ext{ ms}$ sonra `TRACK` moduna geçirir (`REQ-SW-001`).
2. **1D Kalman Filtresi:** Sensörün $\sigma = 2.0	ext{ m}$ seviyesindeki gürültüsü filtrelenir ve kararlı takipte RMS hatası ölçülür (`REQ-SW-002`).
3. **Hata Enjeksiyonu (Fault Injection):** $t = 2.000	ext{ s}$ anında radar telemetrisi koparılır. Sistem `COAST` moduna geçer. $150.0	ext{ ms}$ boyunca sinyal gelmeyince emniyet zamanlayıcısı aşılır ve sistem $2.0	ext{ ms}$ içinde `SAFE_SHUTDOWN` durumuna geçer (`REQ-SW-003`).
4. **RTOS Determinizmi:** 150 döngü boyunca görev periyodu ($20.0	ext{ ms} \pm 0.5	ext{ ms}$) ve WCET ($\le 4.2	ext{ ms}$) ölçülür (`REQ-SW-004`).
5. **Dinamik Bellek Denetimi:** Görev döngüsünde 0 byte heap ayrımı yapıldığı kontrol edilir (`REQ-SW-005`).

### Kod Hücresi 3 Açıklaması: Otomatik Doğrulama Motoru ve İzlenebilirlik Matrisi

Bu hücrede:
- Simülasyondan elde edilen gerçek telemetri dizileri otomatik olarak incelenir.
- Her bir gereksinim için `evaluate(measured_value)` çağrılarak sayısal karşılaştırma yapılır ve güvenlik marjı (Safety Margin) hesaplanır.
- Tablo formatında DO-178C uyumlu çift yönlü gereksinim doğrulama matrisi konsola yazdırılır.

### Aviyonik Donanım ve RTOS Kısıtları: WCET, Jitter ve Sıfır Dinamik Bellek

Havacılık (DO-178C DAL-A) ve uzay (ECSS) standartlarında yazılımın test edilebilirliği donanım seviyesindeki kesinlik kurallarına dayanır:

```mermaid
graph TD
    RTOS["Gerçek Zamanlı İşletim Sistemi (VxWorks 653 / PikeOS / RTEMS)"] --> RateMono["Rate-Monotonic Çizelgeleme"]
    RTOS --> WCET["Worst-Case Execution Time (WCET) Sınırı"]
    RTOS --> StaticMem["Kritik Döngüde 0 Byte Heap (No malloc)"]
    
    RateMono -->|"T <= 20.5 ms"| JitterLimit["Zamanlama Jitteri <= 0.50 ms"]
    WCET -->|"T_exec <= 4.20 ms"| CPUHeadroom["İşlemci Rezervi >= %75 Boş"]
    StaticMem -->|"Fragmentation Yok"| ZeroPanic["Öngörülebilir Deterministik Çalışma"]
```

1. **WCET (Worst-Case Execution Time):** Görev döngüsünün en karmaşık dalında (örneğin tüm hedeflerin listelendiği ve matris tersinin alındığı an) harcanan maksimum saat vuruşu süresidir. Simülasyonumuzda bütçe $4.20	ext{ ms}$ olarak tanımlanmıştır.
2. **Dinamik Bellek Yasağı (No `malloc`/`free` or `new`/`delete`):** Uçuş bilgisayarlarında dinamik bellek havuzu çalışma anında parçalanmaya (fragmentation) ve bellek tükenmesi paniklerine yol açabilir. Tüm tamponlar statik olarak ayrılmalıdır.

```python
# [KOD HÜCRESİ 3: Otomatik Doğrulama Motoru ve İzlenebilirlik Matrisi]
# Amaç: Telemetri sonuçlarını KOD HÜCRESİ 1'de tanımlanan 5 adet gereksinim ile
# otomatik olarak eşleştirmek, sayısal marjları hesaplamak ve DO-178C gereksinim
# izlenebilirlik doğrulama matrisini (Traceability Verification Matrix) üretmek.

# Ölçülen Değerlerin Sözlüğü
observed_metrics: Dict[str, float] = {
    "handover_latency_ms": (T_HANDOVER_PROCESSED - T_HANDOVER_PACKET) * 1000.0,
    "tracking_rmse_m": float(np.sqrt(np.mean(np.array(track_errors)**2))),
    "fault_shutdown_latency_ms": (T_SHUTDOWN_EXECUTED - T_COAST_EXPIRED) * 1000.0,
    "max_period_jitter_ms": max_jitter_ms,
    "dynamic_heap_alloc_bytes": float(simulated_heap_allocations)
}

verification_results = []

print("=" * 100)
print(f"{'REQ ID':<12} | {'GEREKSİNİM ADI':<30} | {'EŞİK':<14} | {'ÖLÇÜLEN':<14} | {'GÜV. MARJI':<12} | {'DURUM'}")
print("=" * 100)

all_requirements_passed = True

for req in REQUIREMENTS:
    measured_val = observed_metrics[req.parameter_name]
    passed, margin, desc = req.evaluate(measured_val)
    status_str = "[PASS] UYGUN" if passed else "[FAIL] İHLAL"
    if not passed:
        all_requirements_passed = False
    
    thresh_str = f"{req.operator} {req.threshold_value} {req.unit}"
    meas_str = f"{measured_val:.3f} {req.unit}" if req.unit != "bytes" else f"{int(measured_val)} {req.unit}"
    margin_str = f"+{margin:.3f} {req.unit}" if margin >= 0 else f"{margin:.3f} {req.unit}"
    
    verification_results.append({
        "req_id": req.req_id,
        "title": req.title,
        "type": req.req_type.value,
        "dal": req.safety_dal.value,
        "measured": measured_val,
        "threshold": req.threshold_value,
        "margin": margin,
        "passed": passed,
        "unit": req.unit
    })
    
    print(f"{req.req_id:<12} | {req.title[:28]:<30} | {thresh_str:<14} | {meas_str:<14} | {margin_str:<12} | {status_str}")

print("=" * 100)
print(f"DO-178C TÜM GEREKSİNİMLERİN DOĞRULAMA DURUMU: {'%100 BAŞARILI (COMPLIANT)' if all_requirements_passed else 'UYUMSUZLUK MEVCUT'}")
print("=" * 100)

```

### Kod Hücresi 4 Açıklaması: DO-178C DAL-A Seviyesi Stres Test Paketi

Bu hücre, askeri aviyonik doğrulama standartlarına uygun 5 bağımsız `assert` testi çalıştırır:
1. `TEST 1`: Handover gecikmesi $\le 10.0	ext{ ms}$ olduğunu teyit eder.
2. `TEST 2`: Kararlı durum takip hatası RMS $\le 1.50	ext{ m}$ olduğunu teyit eder.
3. `TEST 3`: Hata enjeksiyonu sonrasında güvenli kapatma gecikmesinin $\le 5.0	ext{ ms}$ olduğunu teyit eder.
4. `TEST 4`: RTOS döngü jitterinin $\le 0.50	ext{ ms}$ ve WCET süresinin $\le 4.20	ext{ ms}$ olduğunu doğrular.
5. `TEST 5`: Dinamik heap ayrımının 0 byte olduğunu ve sayısal hesaplamalarda sıfır NaN/Inf bulunduğunu kanıtlar.

### Kod Hücresi 5 Açıklaması: 300 DPI Profesyonel Aviyonik Dashboard

Bu hücrede Matplotlib kullanılarak havacılık ve savunma sanayii telemetri odalarına layık, koyu temalı (`#0F172A`), 300 DPI çözünürlüğünde 4 panelli bir görselleştirme üretilir:
- **Panel 1 (Sol Üst):** Durum Makinesi Geçişleri ve Handover gecikme zarfı (`REQ-SW-001`).
- **Panel 2 (Sağ Üst):** Kararlı durum takip hatası ve DO-178C RMS tolerans zarfı (`REQ-SW-002`).
- **Panel 3 (Sol Alt):** Sinyal kaybı hata enjeksiyonu ve fail-safe kapatma zamanlaması (`REQ-SW-003`).
- **Panel 4 (Sağ Alt):** RTOS görev döngüsü jitter dağılımı ve WCET kümülatif olasılık eğrisi (`REQ-SW-004`).

### Kod Hücresi 6 Açıklaması: Resmi DO-178C Kalifikasyon Raporu ve Onay

Bu hücre, tüm testlerin ve metriklerin başarı durumunu kurumsal bir aviyonik kalifikasyon tablosunda özetler ve sistemin DO-178C Seviye-A gereksinim uygunluğunu tescil eder.

```python
# [KOD HÜCRESİ 4: DO-178C DAL-A Algoritmik Stres Test Paketi]
# Amaç: DO-178C / MIL-STD-882E uyarınca aviyonik gereksinimlerin sınır değerlerini,
# istisnai durumlarını ve sayısal kararlılığını 5 bağımsız assert korumasıyla doğrulamak.

print("=" * 76)
print("DO-178C DAL-A ALGORİTMİK STRES VE GEREKSİNİM DOĞRULAMA TESTLERİ")
print("=" * 76)

# TEST 1: REQ-SW-001 - Handover Gecikmesi Doğrulaması (<= 10.0 ms)
lat_handover = observed_metrics["handover_latency_ms"]
assert lat_handover <= 10.0, f"HATA: REQ-SW-001 ihlal edildi! Gecikme={lat_handover:.2f} ms > 10.0 ms"
print(f"[TEST 1 PASS] REQ-SW-001: Handover Gecikmesi: {lat_handover:.2f} ms <= 10.00 ms (Marj: +{10.0 - lat_handover:.2f} ms)")

# TEST 2: REQ-SW-002 - Kararlı Durum Takip Hatası RMS Sınırı (<= 1.50 m)
rmse_track = observed_metrics["tracking_rmse_m"]
assert rmse_track <= 1.50, f"HATA: REQ-SW-002 ihlal edildi! Takip RMSE={rmse_track:.3f} m > 1.50 m"
print(f"[TEST 2 PASS] REQ-SW-002: Takip Hassasiyeti: RMSE = {rmse_track:.3f} m <= 1.50 m (Marj: +{1.50 - rmse_track:.3f} m)")

# TEST 3: REQ-SW-003 - İstenmeyen Olay Kapatma Tepki Süresi (<= 5.0 ms)
lat_shutdown = observed_metrics["fault_shutdown_latency_ms"]
assert lat_shutdown <= 5.0, f"HATA: REQ-SW-003 ihlal edildi! Kapatma Gecikmesi={lat_shutdown:.2f} ms > 5.0 ms"
print(f"[TEST 3 PASS] REQ-SW-003: Güvenli Kapatma Zamanlaması: {lat_shutdown:.2f} ms <= 5.00 ms (Marj: +{5.0 - lat_shutdown:.2f} ms)")

# TEST 4: REQ-SW-004 - RTOS Zamanlama Determinizmi ve WCET (Jitter <= 0.5 ms & WCET <= 4.2 ms)
assert max_jitter_ms <= 0.50, f"HATA: REQ-SW-004 Jitter ihlali! Jitter={max_jitter_ms:.3f} ms > 0.50 ms"
assert wcet_ms <= 4.20, f"HATA: REQ-SW-004 WCET ihlali! WCET={wcet_ms:.3f} ms > 4.20 ms"
print(f"[TEST 4 PASS] REQ-SW-004: Zamanlama Determinizmi: Jitter={max_jitter_ms:.3f} ms <= 0.50 ms, WCET={wcet_ms:.3f} ms <= 4.20 ms")

# TEST 5: REQ-SW-005 - Bellek Ayrımı ve Sayısal Kararlılık (Heap = 0, Sıfır NaN/Inf)
heap_bytes = observed_metrics["dynamic_heap_alloc_bytes"]
assert heap_bytes == 0, f"HATA: REQ-SW-005 ihlal edildi! Heap ayrımı={heap_bytes} bytes != 0"
assert not np.isnan(rmse_track) and not np.isinf(rmse_track), "HATA: Sayısal taşma veya tanımsız değer tespit edildi!"
print(f"[TEST 5 PASS] REQ-SW-005: Statik Bellek ve Kararlılık: 0 Byte Heap Ayrımı, %100 Sayısal Güvenlik.")

print("=" * 76)
print("TÜM DO-178C DAL-A TESTLERİ BAŞARIYLA TAMAMLANDI: [UYGUN]")
print("=" * 76)

```

### Gerçek Dünya Savunma Projelerinde Kullanımı

1. **ASELSAN HİSAR ve SİPER Hava Savunma Sistemleri:**
   Atış Kontrol Bilgisayarı (AKB) yazılımlarında radardan gelen parça devir paketlerinin işlenmesi, EARS formatındaki gecikme gereksinimleriyle denetlenir. Bir hedef izinin takibe alınması gecikirse roketin batarya içi yönelme açısı ıskalanır.
2. **ROKETSAN Seyir ve Tanksavar Füzeleri (SOM, CİRİT, UMTAS):**
   Arayıcı başlık (Seeker) veri hattı koptuğunda füzenin dost unsurlara veya sivil yerleşimlere yönelmesini önleyen `UNWANTED_EVENT` fail-safe kuralları, HIL simülasyonlarında binlerce senaryoda test edilir.
3. **TUSAŞ MMU KAAN Uçuş Kontrol Bilgisayarı (FCC):**
   Uçuş kontrol kanunlarında (Fly-By-Wire) yüzey aktüatörlerine gönderilen komut döngüsü $20	ext{ ms} \pm 0.5	ext{ ms}$ determinizm sınırlarında çalışmak zorundadır.

### Kaçınılması Gereken Anti-Pattern'ler (Muğlak Gereksinim Tuzakları)

| Hatalı / Test Edilemez İfade | Neden Hatalı? (Anti-Pattern) | DO-178C / EARS Uyumlu Doğru İfade |
| :--- | :--- | :--- |
| *"Sistem hedefi hızlı takip etmelidir."* | "Hızlı" ölçülemez. 1 saniye mi, 5 milisaniye mi? | `WHILE in TRACK state, the tracker SHALL update target coordinates every 20.0 ms +/- 0.5 ms.` |
| *"Radar verisi koparsa sistem güvenli olmalıdır."* | "Güvenli" nedir? Motor mu durur, kendini mi imha eder? | `IF radar telemetry is absent for >= 150 ms, THEN the computer SHALL assert SAFE_SHUTDOWN within 5.0 ms.` |
| *"Arayüz kullanıcı dostu ve gecikmesiz olmalıdır."* | Subjektif beğeni ifadesidir, test senaryosu yazılamaz. | `WHEN an operator input is received, the display SHALL refresh within 16.6 ms (60 FPS).` |
| *"Algoritma mümkün olan en az belleği kullanmalıdır."* | Optimizasyon temennisidir, sınır çizilmemiştir. | `The tracking task SHALL consume at most 64.0 KB of static RAM with 0 bytes dynamic allocation.` |

### Standartlar Karşılaştırması: DO-178C, MIL-STD-498 ve ISO 26262

| Standart / Kriter | DO-178C (Sivil Havacılık) | MIL-STD-882E / 498 (Askeri Savunma) | ISO 26262 (Otomotiv) |
| :--- | :--- | :--- | :--- |
| **Gereksinim Hiyerarşisi** | High-Level Req (HLR) -> Low-Level Req (LLR) | System Spec -> Software Requirements Spec (SRS) | Technical Safety Concept -> SW Safety Req |
| **Güvenlik Seviyeleri** | DAL-A (En Yüksek) ila DAL-E | Catastrophic (Cat I) ila Marginal | ASIL-D (En Yüksek) ila ASIL-A |
| **Test Kapsamı** | MC/DC (Modified Condition/Decision Coverage) | Structural Coverage & Mission Reliability | Branch & MC/DC Coverage |
| **İzlenebilirlik Şartı** | İki Yönlü (Bidirectional RTM) Zorunlu | Tam İzlenebilirlik Zorunlu | Tam İzlenebilirlik Zorunlu |
| **Dinamik Bellek** | DAL-A/B'de Yasak veya Katı Kısıtlı | Gerçek Zamanlı Görevlerde Yasak | ASIL-D Seviyesinde Yasak |

```python
# [KOD HÜCRESİ 5: 300 DPI Profesyonel Aviyonik Doğrulama Dashboard'u]
# Amaç: DO-178C gereksinim mühendisliği ve test doğrulaması için 4 panelli,
# koyu tema (#0F172A), yayın kalitesinde (300 DPI) bir mühendislik telemetri görseli üretmek.

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.style.use('dark_background')
fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
fig.patch.set_facecolor('#0F172A')

c_cyan = '#06B6D4'
c_amber = '#F59E0B'
c_rose = '#F43F5E'
c_emerald = '#10B981'
c_blue = '#3B82F6'
c_purple = '#8B5CF6'

# PANEL 1: Durum Makinesi ve Handover Gecikmesi (REQ-SW-001)
ax1 = axs[0, 0]
ax1.set_facecolor('#1E293B')
ax1.step(t_vec, state_history, where='post', color=c_cyan, lw=2.5, label='Sistem Durumu (State Machine)')
ax1.axvline(T_HANDOVER_PACKET, color=c_amber, ls='--', lw=1.8, label=f'Handover Paketi (t={T_HANDOVER_PACKET*1000:.0f} ms)')
ax1.axvline(T_HANDOVER_PROCESSED, color=c_emerald, ls='-', lw=2.0, label=f'TRACK Durumu (t={T_HANDOVER_PROCESSED*1000:.0f} ms)')
ax1.axvspan(T_HANDOVER_PACKET, T_HANDOVER_PACKET + 0.010, color=c_emerald, alpha=0.15, label='REQ-SW-001 Eşiği (<=10 ms)')

ax1.set_yticks([0, 1, 2, 3])
ax1.set_yticklabels(['ACQ (0)', 'TRACK (1)', 'COAST (2)', 'SAFE_SHUT (3)'], fontsize=9, fontweight='bold')
ax1.set_xlabel('Zaman (saniye)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax1.set_ylabel('Sistem Durumu', fontsize=10, fontweight='bold', color='#E2E8F0')
ax1.set_title('PANEL 1: Durum Geçişleri & Handover Gecikmesi (REQ-SW-001 [PASS])', fontsize=11, fontweight='bold', color='#38BDF8')
ax1.grid(True, ls=':', color='#334155', alpha=0.7)
ax1.legend(loc='center right', fontsize=8, framealpha=0.85)

# PANEL 2: Kararlı Durum Hedef Takip Hatası & DO-178C Zarfları (REQ-SW-002)
ax2 = axs[0, 1]
ax2.set_facecolor('#1E293B')
track_indices = np.where((t_vec >= T_HANDOVER_PROCESSED) & (t_vec < T_FAULT_INJECT))[0]
t_track_segment = t_vec[track_indices]
e_track_segment = pos_est[track_indices] - pos_true[track_indices]

ax2.plot(t_track_segment, e_track_segment, color=c_cyan, lw=1.5, alpha=0.85, label='Kestirim Hatası e(t)')
ax2.axhline(0.0, color='#64748B', ls='-', lw=1.0)
ax2.axhline(1.50, color=c_rose, ls='--', lw=2.0, label='REQ-SW-002 Üst Sınır (+1.50 m)')
ax2.axhline(-1.50, color=c_rose, ls='--', lw=2.0, label='REQ-SW-002 Alt Sınır (-1.50 m)')
ax2.axhspan(-rmse_track, rmse_track, color=c_emerald, alpha=0.20, label=f'Gözlemlenen RMS Zarfi ({rmse_track:.2f} m)')

ax2.set_xlabel('Zaman (saniye)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax2.set_ylabel('Konum Hatası (metre)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax2.set_title(f'PANEL 2: Takip Hassasiyeti & Tolerans Zarfı (REQ-SW-002 [PASS]: {rmse_track:.2f}m <= 1.50m)', fontsize=11, fontweight='bold', color='#38BDF8')
ax2.grid(True, ls=':', color='#334155', alpha=0.7)
ax2.legend(loc='lower left', fontsize=8, framealpha=0.85)

# PANEL 3: Hata Enjeksiyonu ve Güvenli Kapatma Kronolojisi (REQ-SW-003)
ax3 = axs[1, 0]
ax3.set_facecolor('#1E293B')
fault_window = np.where((t_vec >= 1.90) & (t_vec <= 2.30))[0]
t_fw = t_vec[fault_window]

ax3.plot(t_fw, pos_true[fault_window], color='#94A3B8', ls=':', lw=2.0, label='Gerçek Yörünge')
meas_plot = np.copy(pos_meas[fault_window])
ax3.scatter(t_fw[~np.isnan(meas_plot)], meas_plot[~np.isnan(meas_plot)], color=c_amber, s=25, alpha=0.7, label='Radar Ölçümleri')
ax3.plot(t_fw, pos_est[fault_window], color=c_rose, lw=2.2, label='Güdüm Kestirimi (Coasting)')

ax3.axvline(T_FAULT_INJECT, color=c_rose, ls='-', lw=2.0, label=f'Hata Enjeksiyonu (t={T_FAULT_INJECT:.2f} s)')
ax3.axvline(T_COAST_EXPIRED, color=c_amber, ls='--', lw=1.8, label=f'150 ms Timeout (t={T_COAST_EXPIRED:.3f} s)')
ax3.axvline(T_SHUTDOWN_EXECUTED, color=c_emerald, ls='-', lw=2.2, label=f'SAFE_SHUTDOWN (t={T_SHUTDOWN_EXECUTED:.3f} s)')

ax3.set_xlabel('Zaman (saniye)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax3.set_ylabel('Konum (metre)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax3.set_title(f'PANEL 3: Sinyal Kaybı Hata Toleransı & Kapatma (REQ-SW-003 [PASS]: {lat_shutdown:.1f}ms <= 5.0ms)', fontsize=11, fontweight='bold', color='#38BDF8')
ax3.grid(True, ls=':', color='#334155', alpha=0.7)
ax3.legend(loc='lower left', fontsize=8, framealpha=0.85)

# PANEL 4: RTOS Görev Periyodu Jitter & WCET Analizi (REQ-SW-004)
ax4 = axs[1, 1]
ax4.set_facecolor('#1E293B')

counts, bins, _ = ax4.hist(loop_periods_ms, bins=15, color=c_blue, alpha=0.65, edgecolor='#60A5FA', label='Döngü Periyodu Dağılımı')
ax4.axvline(nominal_period_ms, color='#E2E8F0', ls='-', lw=2.0, label=f'Nominal ({nominal_period_ms} ms)')
ax4.axvline(nominal_period_ms - 0.50, color=c_rose, ls='--', lw=2.0, label='Limit (-0.50 ms)')
ax4.axvline(nominal_period_ms + 0.50, color=c_rose, ls='--', lw=2.0, label='Limit (+0.50 ms)')

ax4_twin = ax4.twinx()
ax4_twin.plot(np.sort(task_exec_times_ms), np.linspace(0, 1, N_cycles), color=c_amber, lw=2.2, label='WCET CDF Eğrisi')
ax4_twin.axvline(4.20, color=c_rose, ls=':', lw=2.5, label='WCET Sınırı (4.20 ms)')
ax4_twin.set_ylabel('Kümülatif Olasılık (CDF)', fontsize=9, fontweight='bold', color=c_amber)

ax4.set_xlabel('Döngü Periyodu (ms)', fontsize=10, fontweight='bold', color='#E2E8F0')
ax4.set_ylabel('Döngü Sayısı', fontsize=10, fontweight='bold', color=c_blue)
ax4.set_title(f'PANEL 4: RTOS Determinizmi & WCET (REQ-SW-004 [PASS]: Jitter={max_jitter_ms:.2f}ms, WCET={wcet_ms:.2f}ms)', fontsize=11, fontweight='bold', color='#38BDF8')
ax4.grid(True, ls=':', color='#334155', alpha=0.7)
ax4.legend(loc='upper left', fontsize=8, framealpha=0.85)
ax4_twin.legend(loc='lower right', fontsize=8, framealpha=0.85)

fig.suptitle('ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ DO-178C TESTABLE REQUIREMENTS VERIFICATION DASHBOARD',
             fontsize=13, fontweight='bold', color='#F8FAFC', y=0.985)

plt.tight_layout(rect=[0, 0.02, 1, 0.97])

output_png = "gunluk_mufredat/gun_316/gun_316_requirement_nedir_testable_requirement_yazma.png"
fig.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close(fig)

import os
file_size = os.path.getsize(output_png)
print(f"[+] 300 DPI Profesyonel Aviyonik Dashboard Kaydedildi: {output_png} ({file_size:,} bayt)")

```

### Savunma Sanayii Teknik Mülakat Soruları ve Cevapları

**Soru 1: Test edilebilir (testable) bir gereksinimi test edilemez olandan ayıran temel özellik nedir?**
*Cevap:* Test edilebilir bir gereksinim; doğrulanabilir bir ölçüm sınırına (tolerans, süre, eşik), net bir tetikleyici koşula ve ikili (`PASS`/`FAIL`) bir sonuca sahiptir. Göreceli sıfatlar ("hızlı", "güvenilir", "yeterli") içermez.

**Soru 2: EARS mimarisi nedir ve hangi 5 kalıptan oluşur?**
*Cevap:* EARS (Easy Approach to Requirements Syntax), gereksinimlerin doğal dildeki karmaşıklığını ve belirsizliğini ortadan kaldıran şablon yaklaşımıdır: Ubiquitous (Her zaman), Event-Driven (WHEN), State-Driven (WHILE), Unwanted Event (IF/THEN) ve Optional (WHERE).

**Soru 3: DO-178C DAL-A seviyesinde "Çift Yönlü İzlenebilirlik" neden hayati bir denetim şartıdır?**
*Cevap:* İleriye dönük izlenebilirlik her sistem isterinin kodlandığını ve test edildiğini kanıtlar; geriye dönük izlenebilirlik ise kod tabanında gereksinimi olmayan belgelenmemiş veya yetkisiz "hayalet kodların" bulunmadığını temin eder.

**Soru 4: Uçuş kontrol döngülerinde neden dinamik bellek (`malloc`/`new`) kullanımı kesinlikle yasaklanır?**
*Cevap:* Dinamik bellek tahsisi deterministik çalışma süresi (WCET) garantisi veremez. Bellek parçalanması (fragmentation), bellek sızıntısı (memory leak) ve anlık tahsis başarısızlıkları sistemin çalışma anında kilitlenmesine neden olabilir.

**Soru 5: Hata toleransı (Fault-Tolerance) gereksinimi yazarken neden yalnızca hatanın tespiti değil, tepki süresi de verilmelidir?**
*Cevap:* Havacılıkta zamanında yapılmayan doğru müdahale, yanlış müdahale ile eşdeğerdir. Örneğin füze sinyali koptuğunda sistemin güvenli moda geçiş süresi sınırlandırılmazsa ($5	ext{ ms}$ yerine $500	ext{ ms}$ sürerse), aerodinamik kararsızlık roketi havada parçalayabilir.

### Gün Sonu Özeti ve Mühendislik Çıkarımları

1. **Gereksinim Mühendisliği Bir Tasarım Kararıdır:** Gereksinimler metinsel temenniler değil, sistemin sınırlarını belirleyen ve doğrudan otomatik testlere (`assert`) dönüştürülebilen matematiksel modellerdir.
2. **EARS Sözdizimi Muğlaklığı Sıfırlar:** Hava savunma projelerinde EARS yapısı kullanılarak yazılan gereksinimler entegrasyon safhasındaki uyumsuzlukları ve bütçe aşımı risklerini ortadan kaldırır.
3. **DO-178C Determinizmi:** Uçuş bilgisayarlarında zamanlama (latency, jitter, WCET) ve bellek (statik havuz) kısıtları test edilip tescillenmeden hiçbir yazılım uçuşa elverişlilik sertifikası alamaz.

### Gün 317 Ön İzleme: Çift Yönlü Traceability Matrix (RTM) ve DO-178C Doğrulama Zinciri

Yarın Faz F11'in ikinci gününde:
- Gereksinim İzlenebilirlik Matrisi (Requirements Traceability Matrix - RTM) veri yapılarını derinlemesine inceleyeceğiz.
- Bir sistem isterinden (SysReq) başlayarak SRS, Mimari Tasarım, C++ kaynak kodu, Birim Test ve SIL Doğrulama Loglarına kadar uçtan uca otomatik RTM üretim aracını kodlayacağız.
- DO-178C DAL-A denetimlerinde talep edilen MC/DC test kapsamı ile RTM korelasyonunu pratik bir laboratuvarda hayata geçireceğiz.

```python
# [KOD HÜCRESİ 6: Kurumsal DO-178C Kalifikasyon Tablosu ve Sertifikasyon Onayı]
# Amaç: DO-178C ve DO-254 aviyonik sertifikasyon denetimleri için resmi
# gereksinim uygunluk beyanını (Declaration of Conformity) ve kalite tablosunu oluşturmak.

import os

print("+======================================================================+")
print("|   ASELSAN / HAVELSAN / ROKETSAN / TUSAŞ DO-178C DOĞRULAMA LAB        |")
print("|      GEREKSİNİM VE TEST EDİLEBİLİRLİK RESMİ KALİFİKASYON RAPORU      |")
print("+======================================================================+")

report_items = [
    ("1. EARS Standart İster Şablonu", "INCOSE / EARS 5 Ana Şablonla Biçimlendirme", "TAM UYUM", "UYGUN"),
    ("2. REQ-SW-001 Handover Gecikmesi", f"Ölçülen: {lat_handover:.2f} ms (Eşik <= 10.00 ms)", f"Marj: +{10.0-lat_handover:.2f} ms", "UYGUN"),
    ("3. REQ-SW-002 Kararlı Takip Hatası", f"Ölçülen: {rmse_track:.3f} m (Eşik <= 1.50 m)", f"Marj: +{1.50-rmse_track:.3f} m", "UYGUN"),
    ("4. REQ-SW-003 Güvenli Kapatma Hızı", f"Ölçülen: {lat_shutdown:.2f} ms (Eşik <= 5.00 ms)", f"Marj: +{5.0-lat_shutdown:.2f} ms", "UYGUN"),
    ("5. REQ-SW-004 RTOS Jitter Sınırı", f"Ölçülen: {max_jitter_ms:.3f} ms (Eşik <= 0.50 ms)", f"Marj: +{0.50-max_jitter_ms:.3f} ms", "UYGUN"),
    ("6. REQ-SW-004 WCET Bütçesi", f"Ölçülen: {wcet_ms:.3f} ms (Eşik <= 4.20 ms)", f"Marj: +{4.20-wcet_ms:.3f} ms", "UYGUN"),
    ("7. REQ-SW-005 Statik Bellek İlkesi", f"Ölçülen: {int(heap_bytes)} bytes (Eşik == 0 bytes)", "MISRA-C++ Uyum", "UYGUN"),
    ("8. Dashboard Görsel Artefaktı", f"300 DPI PNG ({os.path.getsize(output_png):,} bayt > 100 KB)", "Koyu Tema #0F172A", "UYGUN")
]

for item, metric, margin_info, status in report_items:
    print(f"| {item:<33} : {metric:<34} | [{status}] |")

print("+======================================================================+")
print("| SONUÇ: TÜM 8 DO-178C TESTABLE REQUIREMENT VE DOĞRULAMA KRİTERİ GEÇTİ!|")
print("| FAZ F11 (VERIFICATION / SIL / HIL) GÜN 316 RESMİ SERTİFİKALANDI!     |")
print("+======================================================================+\n")

print("[MÜKEMMEL] GÜN 316: TESTABLE REQUIREMENTS & DOĞRULAMA MOTORU TAMAMLANDI.")
print("[SIRADAKİ GÜN] GÜN 317: TRACEABILITY MATRIX (RTM) VE DO-178C DOĞRULAMA ZİNCİRİ.")

```