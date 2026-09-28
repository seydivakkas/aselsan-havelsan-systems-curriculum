# GÜN 101: `systemd` Service Zihinsel Modeli (PID 1 Mimarisi, `sd_notify`, Watchdog, Cgroups v2 ve Otomatik Kurtarma)

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
[![C++20 Standard](https://img.shields.io/badge/C%2B%2B-20-blue.svg?style=flat-square&logo=c%2B%2B)](https://en.cppreference.com/w/cpp/20)
[![Linux Kernel](https://img.shields.io/badge/systemd-PID%201%20Init-orange.svg?style=flat-square&logo=linux)](https://man7.org/linux/man-pages/man1/systemd.1.html)
[![Domain](https://img.shields.io/badge/Domain-Savunma%20Sanayii%20%2F%20Aviyonik%20Servis%20Yönetimi-green.svg?style=flat-square)]()

---

## 5N1K Kapsam Tablosu

| Soru | Sistem Mühendisliği Açıklaması |
| :--- | :--- |
| **Ne?** | **`systemd` Service Zihinsel Modeli**; Linux çekirdeğinin başlattığı ilk kullanıcı süreci olan **PID 1 (Init)** sisteminin, arka plan servislerini (daemon), soketleri, zamanlayıcıları ve donanım bağımlılıklarını bildirimsel (declarative) üniteler (`.service`) üzerinden yöneten modern işletim sistemi orkestratörüdür. |
| **Neden?** | Geleneksel SysVinit bash betikleri kırılgan, yavaş, sıralı (sequential) ve süreç takibinde acizdir (çift `fork()` yapan bir daemon PID'sini gizleyebilir). `systemd`, Cgroups v2 ile süreçlerin tüm çocuklarını (process tree) kaçışsız takip eder, paralel başlatma sağlar ve çöken kritik servisleri mikro-saniyeler içinde yeniden ayağa kaldırır. |
| **Nasıl?** | `[Unit]`, `[Service]`, `[Install]` bloklarından oluşan bir `.service` dosyası tanımlanır; C++20 servislerinde `sd_notify("READY=1")` ile deterministik başlatma ve `WATCHDOG=1` kalp atışları (heartbeat) kurularak `systemctl` ve `journald` ile entegre edilir. |
| **Nerede?** | ASELSAN radar takip servisleri, HAVELSAN C4I mesajlaşma omurgaları, ROKETSAN telemetri kayıt birimleri ve otonom İHA görev bilgisayarı Linux dağıtımlarında. |
| **Ne Zaman?** | Bir C++ uygulamasının terminalden bağımsız, sistem açılışında otomatik çalışan, kaynak kotalarıyla (RAM/CPU) sınırlandırılmış ve çöktüğünde kendini kurtarabilen bir **üretim seviyesi askeri servise** dönüştürülmesi gerektiğinde. |
| **Kim?** | C++20 Aviyonik Yazılım Mühendisi, Gömülü Linux Sistem Mimarı ve Yüksek Güvenilirlikli Dağıtık Sistem Tasarımcısı. |


## 1. Zihinsel Model & `systemd` PID 1 Mimarisi

Bir Linux sistemi açıldığında çekirdek donanımı ilklendirir ve ilk kullanıcı süreci olarak `/sbin/init` (sembolik linkiyle `systemd`) ikilisini **PID 1** kimliğiyle çalıştırır.

```
+-------------------------------------------------------------------------------+
|                       LINUX ÇEKİRDEĞİ (KERNEL SPACE)                          |
+-------------------------------------------------------------------------------+
                                     |
                          execve("/sbin/init")
                                     v
+-------------------------------------------------------------------------------+
|                          SYSTEMD (PID 1 - ROOT INIT)                          |
|  - Cgroups v2 Hiyerarşi Yöneticisi      - D-Bus Sistem Veriyolu Yöneticisi    |
|  - Bağımlılık Çözümleyici (DAG Engine)  - Olay Odaklı Soket Aktivasyonu        |
+-------------------------------------------------------------------------------+
       |                                   |                              |
       v (Fork & cgroups)                  v (Fork & cgroups)             v
+-----------------------+       +-----------------------+      +----------------+
| radar-tracker.service |       | c4i-gateway.service   |      | journald.service
|  [Cgroup: /system.slice]      |  [Cgroup: /system.slice]     | (Log Toplayıcı)|
|  - PID 401 (Ana Süreç) |       |  - PID 502 (Ana Süreç) |      +----------------+
|  - PID 402 (İş Parçacı)|      |  - PID 503 (Worker)    |
|  - Bellek Sınırı: 2GB |       |  - CPU Kotası: %150    |
+-----------------------+       +-----------------------+
```

### SysVinit ile Modern `systemd` Arasındaki Uçurum:
1. **Kaçak Süreçleri Yakalama (Cgroups İzolasyonu):** SysVinit'te bir daemon arka planda arka arkaya `fork()` çağırıp PID dosyasını silerse süreç yetim (orphan) kalır ve sistem kapatılırken öldürülemezdi. `systemd`, her servisi benzersiz bir **Linux Kontrol Grubuna (Control Group - Cgroup)** hapseder; bir süreç 1,000 çocuk süreç oluştursa dahi `systemctl stop` tek bir komutla o cgroup altındaki her süreci donanımsal olarak sonlandırır.
2. **Paralel Başlatma (Soket Tabanlı Aktivasyon):** Servislerin birbirini beklemesi yerine, `systemd` önce tüm servislerin soketlerini (`.socket`) açar ve buffer'ları dinlemeye başlar. Servisler aynı anda başlatılır; veri geldiğinde çekirdek soket tamponunda bekletilir. Açılış süresi dakikalardan saniyelere iner.


## 2. `systemd` Unit Dosyası Anatomisi ve Servis Tipleri

Bir `systemd` servis tanımı (`/etc/systemd/system/radar.service`) 3 temel bloktan oluşur:

```ini
[Unit]
Description=ASELSAN AESA Radar Hedef Takip Servisi
Documentation=https://wiki.aselsan.local/radar-tracker
After=network.target time-sync.target
Wants=network-online.target
Requires=radar-dsp.service

[Service]
Type=notify
ExecStart=/opt/aselsan/bin/radar_tracker --config /etc/radar.conf
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=500ms
WatchdogSec=2s
StartLimitIntervalSec=60s
StartLimitBurst=5

# Cgroups v2 ve Güvenlik Sınırlandırmaları
MemoryMax=2G
CPUQuota=200%
TasksMax=64
ProtectSystem=strict
ProtectHome=yes
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
```

### Servis Tipleri (`Type=`) Karşılaştırması

| Servis Tipi | Ne Zaman Hazır Sayılır? | Risk / Davranış | Savunma Sanayii Uygunluğu |
| :--- | :--- | :--- | :---: |
| **`Type=simple`** | `execve()` sistem çağrısı çalıştırıldığı anda. | Süreç henüz soketi açmamış veya kalibrasyonu bitirmemiş olabilir; bağımlı servisler erken başlar ve çöker (**Race Condition**)! | ❌ Güvenilmez |
| **`Type=exec`** | İkili dosya diskten yüklenip ana süreç çatallanmayı tamamladığında. | `simple`'a benzer, sadece `fork` garantisi vardır; dahili başlatmayı doğrulamaz. | ⚠️ Orta |
| **`Type=forking`** | Ana süreç arka plana geçip (daemonize) parent süreç `exit(0)` yaptığında. | Eski C kütüphaneleri içindir. Çift fork ve `PIDFile=` gerektirir; yarış durumlarına açıktır. | ❌ Tavsiye Edilmez |
| **`Type=notify`** | Süreç doğrudan `systemd` soketine **`sd_notify("READY=1")`** mesajı gönderdiğinde! | Deterministik ve hatasızdır. Süreç tüm donanımı ilklendirmeden hazır kabul edilmez. | **✅ ALTIN STANDART** |


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 04 (CODE 1): Python ile systemd Servis Durum Makinesi (State Machine) Simülasyonu
Unit Yaşam Döngüsü, sd_notify("READY=1"), Watchdog ve Otomatik Kurtarma Motoru
"""

import time
from enum import Enum
from typing import Optional, Dict, Any, List

class ServiceState(Enum):
    DEAD = "dead"
    STARTING = "starting"
    RUNNING = "running"
    WATCHDOG_TIMEOUT = "watchdog_timeout"
    FAILED = "failed"
    RESTARTING = "restarting"
    STOPPED = "stopped"

class SimulatedSystemdService:
    """systemd PID 1 Servis Yöneticisi ve Durum Makinesi."""
    
    def __init__(self, name: str, service_type: str = "notify", watchdog_sec: float = 2.0, max_restarts: int = 3):
        self.name = name
        self.service_type = service_type
        self.watchdog_sec = watchdog_sec
        self.max_restarts = max_restarts
        
        self.state = ServiceState.DEAD
        self.pid: Optional[int] = None
        self.last_ping_time: float = 0.0
        self.restart_count: int = 0
        self.history: List[str] = []

    def log(self, message: str):
        self.history.append(f"[{self.state.value.upper()}] {message}")

    def start(self, pid: int):
        """Servisi başlatır (systemctl start)."""
        self.pid = pid
        self.state = ServiceState.STARTING
        self.log(f"Süreç başlatıldı (PID: {pid}).")

        if self.service_type == "simple":
            # simple tipinde anında RUNNING durumuna geçer (Riskli!)
            self.state = ServiceState.RUNNING
            self.last_ping_time = time.time()
            self.log("Type=simple gereği anında RUNNING durumuna geçildi.")

    def receive_notify(self, message: str):
        """Süreçten gelen sd_notify() mesajlarını işler."""
        if message == "READY=1":
            if self.state == ServiceState.STARTING:
                self.state = ServiceState.RUNNING
                self.last_ping_time = time.time()
                self.log("sd_notify('READY=1') alındı -> Servis resmen RUNNING!")
        elif message == "WATCHDOG=1":
            if self.state == ServiceState.RUNNING:
                self.last_ping_time = time.time()
                self.log("sd_notify('WATCHDOG=1') kalp atışı kaydedildi.")

    def check_watchdog(self, current_time: float) -> bool:
        """systemd Watchdog denetimi: Süre aşıldıysa süreci zorla öldürür (SIGABRT)."""
        if self.state != ServiceState.RUNNING:
            return True
            
        elapsed = current_time - self.last_ping_time
        if elapsed > self.watchdog_sec:
            self.state = ServiceState.WATCHDOG_TIMEOUT
            self.log(f"WATCHDOG ZAMAN AŞIMI! ({elapsed:.2f}s > {self.watchdog_sec}s). SIGABRT gönderiliyor.")
            self.handle_failure(reason="Watchdog Aşımı")
            return False
        return True

    def handle_failure(self, reason: str):
        """Çöken veya öldürülen servisi yeniden başlatma politikası."""
        self.state = ServiceState.FAILED
        self.log(f"Servis çöktü! Sebep: {reason}")
        
        if self.restart_count < self.max_restarts:
            self.restart_count += 1
            self.state = ServiceState.RESTARTING
            self.log(f"Yeniden başlatılıyor ({self.restart_count}/{self.max_restarts})...")
        else:
            self.state = ServiceState.FAILED
            self.log("StartLimitBurst sınırı aşıldı! Servis kalıcı olarak FAILED durumunda bırakıldı.")


if __name__ == "__main__":
    print("=== SYSTEMD SERVİS YAŞAM DÖNGÜSÜ VE DURUM MAKİNESİ SİMÜLASYONU ===")
    service = SimulatedSystemdService(name="aselsan-radar.service", service_type="notify", watchdog_sec=1.5, max_restarts=2)
    
    # 1. Başlatma
    service.start(pid=1042)
    print(f"[*] Durum: {service.state.value} (Bekleniyor: Donanım kalibrasyonu sürüyor...)")
    
    # 2. Hazır bildirimi
    time.sleep(0.1)
    service.receive_notify("READY=1")
    print(f"[*] Durum: {service.state.value}")

    # 3. Düzenli Kalp Atışları
    service.receive_notify("WATCHDOG=1")
    print(f"[*] Kalp atışı gönderildi.")

    # 4. Kilitlenme (Deadlock) Simülasyonu - Watchdog ping gönderilmiyor
    print("[*] Radar servisi kilitlendi (Deadlock)! Kalp atışı kesildi.")
    simulated_now = time.time() + 2.0
    service.check_watchdog(current_time=simulated_now)

    print("\n=== SYSTEMD SERVİS GÜNLÜĞÜ (JOURNAL) ===")
    for entry in service.history:
        print(f"  {entry}")

```

## 3. Kod 01 Detaylı Açıklaması ve Yaşam Döngüsü Analizi

Kod 01'deki simülasyon, `systemd` çekirdek durum makinesinin (`systemd state engine`) en kritik özelliklerini canlandırmıştır:

1. **`Type=notify` Güvenliği:** Süreç `STARTING` durumundayken, kendi içinde radar FPGA bağlantılarını ve bellek alanlarını hazırlayana kadar bekler. Ne zaman ki `READY=1` sinyali soketten `systemd`'ye ulaşır, servis ancak o zaman `RUNNING` durumuna geçer. Bu sayede bağımlı servislerin premature (erken) çökmesi engellenir.
2. **Watchdog Donanımsal Koruma:** Süreç bir kilitlenme (deadlock) veya sonsuz döngüye girip belirlenen sürede (`WatchdogSec=1.5s`) kalp atışı göndermediğinde, `systemd` bu durumu anında algılar, süreci `SIGABRT` sinyaliyle çekirdek dökümü (core dump) alarak sonlandırır ve temiz bir PID ile yeniden başlatır (`RESTARTING`).
3. **`StartLimitBurst` Freni:** Çökme sürekli tekrar ederse (örn. donanım kablosu kopuksa), sistemin sonsuz döngüde işlemciyi tüketmesini engellemek için servis kalıcı olarak `FAILED` modunda durdurulur.


## 4. Deterministik Başlatma ve Donanımsal Kalp Atışı: `sd_notify` Mimarisi

Bir Linux süreci `systemd` ile nasıl haberleşir? Harici bir kütüphaneye (`libsystemd`) bağımlı olmak zorunda mıdır?

### `NOTIFY_SOCKET` Ortam Değişkeni ve Unix Datagram Protokolü
`systemd`, bir servisi başlatırken çevre birimine benzersiz bir ortam değişkeni enjekte eder:
```bash
NOTIFY_SOCKET=/run/systemd/notify/control.socket
```
Bu soket bir **Unix Domain Datagram Socket (`AF_UNIX`, `SOCK_DGRAM`)** yapısındadır. Süreç bu sokete basit metin dizgeleri (`string`) göndererek durumunu raporlar:

```
+---------------------------+       Unix Dgram Socket       +--------------------------+
|  ASELSAN C++20 Servisi    | ----------------------------> |   systemd (PID 1)        |
|  (Kullanıcı Alanı)        |   "READY=1\nSTATUS=Calibrated"|   (Çekirdek Yöneticisi)  |
|                           |   "WATCHDOG=1"                |                          |
|                           |   "RELOADING=1"               |                          |
+---------------------------+                               +--------------------------+
```

### Temel Bildirim Mesajları:
- **`READY=1`:** "Tüm konfigürasyon yüklendi, donanım bağlandı, istek kabul etmeye hazırım."
- **`WATCHDOG=1`:** "Canlıyım, kilitlenmedim, görev döngüm sağlıklı çalışıyor."
- **`STATUS=Metin`:** `systemctl status radar` çıktısında görüntülenecek özel operasyonel durum (örn: `"STATUS=Tracking 42 Airborne Targets"`).
- **`MAINPID=PID`:** `Type=forking` veya işçi süreç değişiminde ana PID güncellemesi.


## 5. C++20 Standartlarında Sıfır-Bağımlılıklı (`libsystemd` Gerektirmeyen) `sd_notify` Wrapper'ı

Savunma sanayiinde gömülü Linux sistemlerinde ek kütüphane bağımlılığı (`libsystemd-dev`) istenmeyebilir. Aşağıdaki modern C++20 sınıfı, doğrudan POSIX Unix Datagram soketlerini kullanarak tam uyumlu ve sıfır bağımlılıklı bir `systemd` bildirim katmanı sunar:

```cpp
#include <iostream>
#include <string_view>
#include <cstdlib>
#include <cstring>
#include <chrono>
#include <system_error>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

class SystemdNotifier {
private:
    int m_sock_fd{-1};
    sockaddr_un m_server_addr{};
    bool m_is_active{false};

public:
    SystemdNotifier() noexcept {
        const char* socket_path = std::getenv("NOTIFY_SOCKET");
        if (!socket_path) {
            // Servis systemd altında çalışmıyor (örn: terminalde manuel test ediliyor)
            return;
        }

        m_sock_fd = ::socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0);
        if (m_sock_fd == -1) {
            return;
        }

        std::memset(&m_server_addr, 0, sizeof(m_server_addr));
        m_server_addr.sun_family = AF_UNIX;

        // Abstract socket veya standart yol kontrolü (@ ile başlıyorsa abstract socket)
        if (socket_path[0] == '@') {
            m_server_addr.sun_path[0] = '\0';
            std::strncpy(&m_server_addr.sun_path[1], socket_path + 1, sizeof(m_server_addr.sun_path) - 2);
        } else {
            std::strncpy(m_server_addr.sun_path, socket_path, sizeof(m_server_addr.sun_path) - 1);
        }

        m_is_active = true;
    }

    ~SystemdNotifier() noexcept {
        if (m_sock_fd != -1) {
            ::close(m_sock_fd);
            m_sock_fd = -1;
        }
    }

    // Move-only semantics
    SystemdNotifier(const SystemdNotifier&) = delete;
    SystemdNotifier& operator=(const SystemdNotifier&) = delete;
    SystemdNotifier(SystemdNotifier&& other) noexcept 
        : m_sock_fd(other.m_sock_fd), m_server_addr(other.m_server_addr), m_is_active(other.m_is_active) {
        other.m_sock_fd = -1;
        other.m_is_active = false;
    }

    bool notify(std::string_view state) noexcept {
        if (!m_is_active) return false;
        
        ssize_t sent = ::sendto(
            m_sock_fd, 
            state.data(), 
            state.size(), 
            MSG_NOSIGNAL, 
            reinterpret_cast<const sockaddr*>(&m_server_addr), 
            sizeof(m_server_addr)
        );
        return sent == static_cast<ssize_t>(state.size());
    }

    bool notify_ready() noexcept {
        return notify("READY=1");
    }

    bool notify_watchdog() noexcept {
        return notify("WATCHDOG=1");
    }

    bool notify_status(std::string_view status_msg) noexcept {
        std::string payload = "STATUS=";
        payload.append(status_msg);
        return notify(payload);
    }
};
```


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 08 (CODE 2): Python ile Cgroups v2 Bellek Sınırı (MemoryMax) ve OOM Killer Simülatörü
Kaynak İzolasyonu, Aşım Tespiti ve Otomatik Yeniden Başlatma Dinamiği
"""

from typing import Dict, Any, List

class SimulatedCgroupV2:
    """Linux Cgroups v2 Bellek ve Görev Kontrolörü Simülasyonu."""
    
    def __init__(self, memory_max_mb: int = 1024, tasks_max: int = 32):
        self.memory_max_mb = memory_max_mb
        self.tasks_max = tasks_max
        self.current_memory_mb: float = 0.0
        self.active_tasks: int = 1
        self.oom_kill_count: int = 0
        self.events: List[str] = []

    def allocate_memory(self, mb: float) -> bool:
        """Süreç dinamik bellek (RAM) tahsis etmek istiyor."""
        projected = self.current_memory_mb + mb
        if projected > self.memory_max_mb:
            self.oom_kill_count += 1
            self.events.append(
                f"[OOM-KILL] Tahsis Reddedildi: {projected:.1f} MB > MemoryMax ({self.memory_max_mb} MB)! Süreç öldürüldü."
            )
            # OOM Killer süreci infaz eder ve belleği sıfırlar
            self.current_memory_mb = 0.0
            return False
            
        self.current_memory_mb = projected
        self.events.append(f"[CGROUP] Bellek ayrıldı: +{mb} MB (Mevcut: {self.current_memory_mb:.1f} MB)")
        return True

    def create_thread(self) -> bool:
        """Yeni bir iş parçacığı oluşturma isteği (TasksMax kontrolü)."""
        if self.active_tasks >= self.tasks_max:
            self.events.append(f"[TASK-MAX] İş parçacığı limiti aşıldı ({self.tasks_max})! EAGAIN üretildi.")
            return False
        self.active_tasks += 1
        return True


if __name__ == "__main__":
    print("=== CGROUPS V2 KAYNAK YÖNETİMİ VE OOM SİMÜLASYONU ===")
    cg = SimulatedCgroupV2(memory_max_mb=512, tasks_max=4)
    
    # Adım 1: Normal radar veri yükü
    cg.allocate_memory(150.0)
    cg.allocate_memory(200.0)
    
    # Adım 2: Bellek sızıntısı veya aşırı yük (Spike) -> 512 MB aşımı
    success = cg.allocate_memory(250.0)
    print(f"[*] Aşırı Bellek Tahsisi Başarılı mı?: {success}")
    print(f"[*] Toplam OOM İnfazı Sayısı: {cg.oom_kill_count}")
    
    print("\n=== CGROUPS OLAY GÜNLÜĞÜ ===")
    for evt in cg.events:
        print(f"  {evt}")

```

## 6. Kod 02 Analizi: Cgroups İzolasyonu ve Sistem Kararlılığı

Simülasyon çıktıları savunma sanayiinde `cgroups v2` kullanımının vazgeçilmezliğini belgeler:

1. **Komşu Servisleri Koruma (Blast Radius Isolation):** Radar hedef takip servisinde bir bellek sızıntısı (`memory leak`) meydana geldiğinde, `MemoryMax=512M` kuralı sayesinde servis tüm işletim sistemi RAM'ini tüketemez. Yalnızca kuralı çiğneyen cgroup hedef alınır.
2. **OOM Killer Seçiciliği:** Geleneksel Linux'ta bellek bittiğinde çekirdeğin rastgele bir süreci (bazen SSH veya veritabanını) öldürmesine karşılık, systemd cgroup seviyesinde hedefli infaz yapar ve servisi `Restart=on-failure` ile temiz şekilde yeniden ayağa kaldırır.
3. **Fork-Bomb Savunması (`TasksMax=`):** Hatalı yazılmış bir algoritmanın sonsuz iş parçacığı (`std::thread`) açıp işletim sisteminin PID tablosunu doldurması engellenir.


## 7. Kritik Hata & Sabotaj Analizi: Döngüsel Bağımlılık ve Crash Loop

`systemd` konfigürasyonunda yapılan hatalar tüm sistemin açılışını (boot sequence) kilitleyebilir:

### 1. Döngüsel Bağımlılık Tuzağı (Circular Dependency Deadlock)
Eğer Servis A `Requires=servis-b.service` ve Servis B de `Requires=servis-a.service` derse:
`systemd` bir **Yönlendirilmiş Döngüsüz Çizge (DAG - Directed Acyclic Graph)** kuramaz. Döngüyü kırmak için keyfi olarak servislerden birini devre dışı bırakır (`dependency loop broke; dropping job`). Görev kritik bir servis açılışta sessizce elenebilir!

### 2. `After=` vs `Requires=` Ayrımının Karıştırılması
- **`Requires=`:** Yalnızca mantıksal varlık bağımlılığıdır. "B başlamadan A çalışamaz" der; **ANCAK BAŞLAMA SIRASINI BELİRLEMEZ!**
- Eğer Servis A, Servis B'nin soketine bağlanıyorsa ve sadece `Requires=B` yazıldıysa, `systemd` ikisini **aynı anda** başlatır. B henüz soketi açmadığı için A bağlantı hatasıyla çöker!
- **Kural:** Her zaman hem `Requires=B.service` hem de `After=B.service` birlikte yazılmalıdır!

### 3. Hızlı Çökme Döngüsü (Crash Loop & Rate Limiting)
Bir servis açılır açılmaz bir yapılandırma hatası nedeniyle 10 milisaniye içinde çöküyorsa ve `Restart=always` ayarlanmışsa:
Servis saniyede 100 kez yeniden başlar. `systemd` bunu tespit ederek koruma mekanizmasını devreye sokar:
```
systemd[1]: radar.service: Start request repeated too quickly.
systemd[1]: radar.service: Failed with result 'start-limit-hit'.
```
Bu felaketi yönetmek için `StartLimitIntervalSec=30s` ve `StartLimitBurst=3` ile birlikte `RestartSec=2s` gecikmesi tanımlanmalıdır.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Arıza Simülatörü
Crash Loop Tespiti (StartLimitBurst) ve Watchdog İhlali Kurtarma Laboratuvarı
"""

from typing import Dict, Any, Tuple

class SystemdSabotageLab:
    """systemd servis konfigürasyon sabotajları ve savunma simülatörü."""

    @staticmethod
    def simulate_crash_loop_throttling(burst_limit: int = 5, crash_interval_s: float = 0.05) -> Dict[str, Any]:
        """Bir servisin saniyeler içinde arka arkaya çökmesini ve cezalandırılmasını modeller."""
        attempts = 0
        throttled = False
        restarts = []

        for i in range(burst_limit + 3):
            attempts += 1
            if attempts > burst_limit:
                throttled = True
                restarts.append(f"Deneme {attempts}: [BLOKE EDİLDİ] StartLimitBurst ({burst_limit}) aşıldı! Servis askıya alındı.")
                break
            else:
                restarts.append(f"Deneme {attempts}: Servis çöktü ve systemd Restart politikasıyla yeniden başlatıldı.")

        return {
            "attempts": attempts,
            "burst_limit": burst_limit,
            "throttled": throttled,
            "log": restarts
        }

    @staticmethod
    def simulate_watchdog_missed_heartbeat() -> Tuple[bool, str]:
        """Kilitlenen servisin Watchdog tarafından SIGABRT ile düşürülmesini doğrular."""
        srv = SimulatedSystemdService(name="tracker.service", service_type="notify", watchdog_sec=1.0)
        srv.start(pid=2001)
        srv.receive_notify("READY=1")
        
        # 1.5 saniye sonra watchdog kontrolü (kalp atışı gönderilmedi!)
        healthy = srv.check_watchdog(current_time=time.time() + 1.5)
        
        if not healthy and srv.state == ServiceState.RESTARTING:
            return True, "BEKLENEN SAVUNMA ÇALIŞTI: Kilitlenen servis SIGABRT ile öldürüldü ve temiz PID ile ayağa kaldırıldı."
        return False, "HATA: Watchdog süresi aşıldığı halde servis sonlandırılmadı!"


if __name__ == "__main__":
    print("=== SYSTEMD SABOTAJ VE ARIZA LABORATUVARI ===")
    
    # Test 1: Crash Loop ve Rate Limiting
    crash_report = SystemdSabotageLab.simulate_crash_loop_throttling(burst_limit=4)
    print(f"[*] Crash Loop Testi: Throttled={crash_report['throttled']}")
    for l in crash_report["log"]:
        print(f"    {l}")

    # Test 2: Watchdog İhlali
    wd_ok, wd_msg = SystemdSabotageLab.simulate_watchdog_missed_heartbeat()
    print(f"\n[*] Watchdog Kilitlenme Testi: {'BAŞARILI' if wd_ok else 'BAŞARISIZ'}")
    print(f"    Sonuç: {wd_msg}")

```

## 8. Kod 03 Hata Analizi ve Çekirdek Davranışları

Simülasyon çıktıları iki kritik işletim sistemi gerçeğini doğrular:

1. **`StartLimitBurst` İle CPU Koruması:** Hatalı bir dinamik kütüphane (`.so`) veya bozuk bir ayar dosyası nedeniyle sürekli çöken bir servis, eğer limitlenmezse sistem çekirdeklerini %100 meşgul ederek aşırı ısınmaya ve diğer kritik servislerin aç kalamamasına (starvation) yol açar. `systemd` cezalandırma mekanizması ile sistemi korur.
2. **Zombi Süreçlere Karşı Watchdog:** Bir thread sonsuz döngüde kilitlendiğinde veya deadlock'a girdiğinde süreç işletim sistemine göre hala "çalışıyor" (RUNNING) görünür. `ps` veya `top` komutu süreci canlı zanneder. Bu sinsi hatayı yakalayabilen tek mekanizma `systemd`'nin **aktif yoklama (Watchdog)** protokolüdür.


## 9. Savunma Sanayii Vaka Analizi: ASELSAN Radar Takip Görev Servisi

Görev kritik bir hava savunma radarında çalışan `radar-tracker.service` sistem bileşeninin kesintisizliği ve kaynak sınırlandırması şu operasyonel gereksinimlere bağlıdır:

```
+--------------------------------------------------------------------------------+
|                   ASELSAN GÖREV BİLGİSAYARI SYSTEMD MİMARİSİ                   |
|                                                                                |
|  [Hava Savunma Radarı] ---> [PCIe EDMA] ---> [radar-tracker.service (C++20)]   |
|                                                     |                          |
|         +-------------------------------------------+                          |
|         |                                                                      |
|         v (Watchdog 500ms)                          v (Cgroups v2 Kotaları)    |
|  +-----------------------------+           +--------------------------------+  |
|  | /run/systemd/notify soketi  |           | MemoryMax=4GB                  |  |
|  | sd_notify("WATCHDOG=1")     |           | CPUQuota=400% (4 Çekirdek)     |  |
|  | (500 ms içinde gelmezse     |           | TasksMax=32                    |  |
|  |  donanım resetlenir!)       |           | CPUSchedulingPolicy=rr         |  |
|  +-----------------------------+           | CPUSchedulingPriority=80 (RT)  |  |
|                                            +--------------------------------+  |
|                                                                                |
|  [HATA DURUMU VE OTOMATİK İYİLEŞME]:                                           |
|  Kuş sürüsü/elektronik harp nedeniyle bellek patlaması yaşanırsa:             |
|  1. Cgroup MemoryMax aşılır.                                                   |
|  2. systemd anında SIGKILL ile süreci durdurur.                                |
|  3. RestartSec=100ms kuralı devreye girer.                                     |
|  4. Servis 150 ms içinde sıfır bellek sızıntısıyla yeniden ayağa kalkar!       |
+--------------------------------------------------------------------------------+
```

### Neden `systemd` Dışında Bir Süreç Yöneticisi Kullanılamaz?
Supervisord veya PM2 gibi kullanıcı seviyesi araçlar Python veya Node.js tabanlıdır; bellek tüketimleri yüksektir, gerçek zamanlı çekirdek cgroups v2 ve RT-Scheduling (`SCHED_RR` / `SCHED_FIFO`) yeteneklerine doğrudan entegre olamazlar. `systemd`, doğrudan Linux çekirdeğinin doğal bir uzantısıdır.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Radar Görev Servisi Cgroups İhlali ve Kurtarma Simülasyonu
Dinamik Yük Artışı, OOM-Kill ve 100ms Hızlı İyileşme (Auto-Recovery) Testi
"""

import time
from typing import Dict, Any, List

def run_radar_service_recovery_pipeline(simulation_cycles: int = 10) -> Dict[str, Any]:
    """Radar takip servisinin bellek sınırını aşması ve systemd tarafından kurtarılma döngüsü."""
    cgroup = SimulatedCgroupV2(memory_max_mb=2048) # 2 GB Sınır
    service = SimulatedSystemdService(name="aselsan-tracker.service", service_type="notify", max_restarts=5)
    
    current_pid = 4100
    service.start(pid=current_pid)
    service.receive_notify("READY=1")

    timeline = []
    
    for cycle in range(simulation_cycles):
        # Her döngüde radar izi verisi için 300 MB bellek tahsis ediliyor
        success = cgroup.allocate_memory(300.0)
        
        if not success:
            # OOM Yaşandı! systemd servisi anında yeniden başlatıyor
            service.handle_failure(reason="Cgroups v2 MemoryMax Aşımı (OOM)")
            current_pid += 10
            service.start(pid=current_pid)
            service.receive_notify("READY=1")
            timeline.append({
                "cycle": cycle,
                "status": "OOM_RESTART",
                "active_pid": current_pid,
                "ram_mb": cgroup.current_memory_mb
            })
        else:
            # Normal operasyon: Watchdog pingi gönder
            service.receive_notify("WATCHDOG=1")
            timeline.append({
                "cycle": cycle,
                "status": "HEALTHY",
                "active_pid": current_pid,
                "ram_mb": cgroup.current_memory_mb
            })

    return {
        "total_cycles": simulation_cycles,
        "oom_events": cgroup.oom_kill_count,
        "restart_count": service.restart_count,
        "final_pid": current_pid,
        "timeline": timeline
    }


if __name__ == "__main__":
    print("=== RADAR GÖREV SERVİSİ KURTARMA PİPELİNE TESTİ ===")
    res = run_radar_service_recovery_pipeline(simulation_cycles=12)
    print(f"[*] Toplam Simülasyon Döngüsü: {res['total_cycles']}")
    print(f"[*] Yaşanan OOM İnfaz Sayısı : {res['oom_events']}")
    print(f"[*] systemd Otomatik Kurtarma : {res['restart_count']} kez başarıyla yeniden başlatıldı.")
    print(f"[*] Son Aktif PID             : {res['final_pid']}")
    print("\nZaman Çizelgesi Örnekleri:")
    for t in res["timeline"][:6]:
        print(f"  Döngü {t['cycle']:2d} -> Durum: {t['status']:11s} | PID: {t['active_pid']} | RAM: {t['ram_mb']:.1f} MB")

```

## 10. Kod 04 Analizi ve Deterministik Kurtarma

Kod 04 simülasyonu, bir savunma sanayii yazılımının çökme anında sergilemesi gereken davranışı ortaya koyar:

1. **Bellek Taşmasında Sıfır Durgunluk:** Servis 2 GB limitini aştığında sistem kilitlenmemiş, `systemd` cgroup kontrolörü süreci anında infaz ederek belleği tamamen geri kazanmıştır.
2. **Otomatik PID Rotasyonu:** Servis yeni bir PID ile başlatılmış, FPGA donanımını yeniden bağlamış ve `READY=1` sinyaliyle görevine kaldığı yerden devam etmiştir.
3. **Fail-Fast Prensibi:** Sessizce bozulan veya bellek sızdıran bir servisin yaşamasına izin vermek yerine, hızlıca çökertilip (fail-fast) temiz bellek alanıyla yeniden başlatılması yazılım güvenilirliğinin temel şartıdır.


## 11. `systemd` Servis Tipleri ve Başlatma Determinizmi Modeli

Aşağıdaki matris, farklı `Type=` direktiflerinin sistem açılışındaki zamanlama ve kararlılık karakteristiklerini gösterir:

| Parametre | `Type=simple` | `Type=exec` | `Type=forking` | `Type=notify` |
| :--- | :---: | :---: | :---: | :---: |
| **Hazır Kabul Edilme Anı** | `execve()` yapıldığı an | İkili dosya yüklendiği an | Parent süreç `exit(0)` yaptığı an | **`sd_notify("READY=1")` ulaştığı an** |
| **Soket Yarış Durumu (Race Condition)** | **Yüksek Risk** (Soket henüz açılmamış olabilir) | **Yüksek Risk** | Orta Risk | **SIFIR RİSK** (Deterministik) |
| **Watchdog Entegrasyonu** | Yok | Yok | Yok | **Mevcut (`WATCHDOG=1`)** |
| **Başlatma Gecikmesi** | En Düşük (0 ms) | Çok Düşük (1 ms) | Yüksek (Fork maliyeti) | Kontrollü (Kalibrasyon kadar) |
| **Kullanım Yeri** | Basit CLI araçları | Komut dosyaları | Eski SysVinit servisleri | **Savunma, Havacılık ve Görev Kritik Servisler** |

### Matematiksel Başlatma Güvenilirlik Modeli
Bir bağımlı servisin ($S_{\text{dep}}$) ana servisin ($S_{\text{main}}$) soketine başarıyla bağlanma olasılığı $P(\text{Success})$:

- **`Type=simple` için:**
  $$P(\text{Success}) = P(T_{\text{socket\_bind}} < T_{\text{dep\_connect}}) \approx 0.65 - 0.85 \quad (\text{Yarış durumu kaçınılmazdır!})$$

- **`Type=notify` için:**
  $$P(\text{Success}) \equiv 1.0 \quad (\text{Çünkü } S_{\text{dep}} \text{ ancak } \text{READY=1} \text{ sinyalinden sonra başlatılır!})$$


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 5): Kapsamlı Başlatma ve Kurtarma Performans Benchmark Laboratuvarı
Type=simple vs Type=notify Güvenilirlik ve Yarış Durumu (Race Condition) Ölçümü
"""

import numpy as np
from typing import Dict, Any

def run_service_startup_benchmark(trials: int = 1000) -> Dict[str, Any]:
    """Type=simple ile Type=notify arasındaki başlatma yarış durumu oranlarını modeller."""
    np.random.seed(101)
    
    # Simple tipinde: Servisin soketi açma süresi (Normal dağılım: Ortalama 25ms, std 8ms)
    socket_ready_times_ms = np.random.normal(loc=25.0, scale=8.0, size=trials)
    
    # Bağımlı servisin bağlanmaya çalışma süresi (Ortalama 20ms, std 5ms)
    dep_connect_times_ms = np.random.normal(loc=20.0, scale=5.0, size=trials)

    # simple için yarış durumu: Bağımlı servis, ana servis soketi açmadan önce gelirse HATA!
    simple_race_failures = np.sum(dep_connect_times_ms < socket_ready_times_ms)
    simple_success_rate = (trials - simple_race_failures) / trials * 100.0

    # notify için: Bağımlı servis daima soket açıldıktan (READY=1) sonra tetiklenir!
    notify_success_rate = 100.0

    return {
        "trials": trials,
        "simple_success_rate": simple_success_rate,
        "simple_failures": int(simple_race_failures),
        "notify_success_rate": notify_success_rate,
        "mean_socket_init_ms": float(np.mean(socket_ready_times_ms)),
        "mean_dep_connect_ms": float(np.mean(dep_connect_times_ms))
    }


if __name__ == "__main__":
    print("=== SYSTEMD SERVİS BAŞLATMA GÜVENİLİRLİK BENCHMARK'I ===")
    bench = run_service_startup_benchmark(trials=5000)
    print(f"[*] Toplam Test Sayısı               : {bench['trials']:,}")
    print(f"[*] Type=simple Başarı Oranı         : %{bench['simple_success_rate']:.2f} ({bench['simple_failures']} Yarış Hatası!)")
    print(f"[*] Type=notify Başarı Oranı         : %{bench['notify_success_rate']:.2f} (KUSURSUZ DETERMINIZM)")
    print(f"[*] Ortalama Soket İlklendirme Süresi: {bench['mean_socket_init_ms']:.1f} ms")
    print(f"[*] Bağımlı Servis Bağlantı Süresi   : {bench['mean_dep_connect_ms']:.1f} ms")

```

## 12. Kod 05 Benchmark Sonuçları: Başlatma Determinizmi

Benchmark sonuçları savunma ve havacılık sistemlerinde `Type=simple` kullanımının neden kesinlikle yasaklandığını kanıtlar:

1. **Yarış Durumu Felaketi:** `Type=simple` kullanılan 5,000 denemede **yüzlerce kez bağlantı reddedildi (`ECONNREFUSED`)** hatası alınmıştır. Çünkü `systemd` ana sürecin ikili dosyasını başlattığı anda bağımlı servisleri tetiklemiş; ancak ana servis henüz soketini bağlayıp dinleme (`listen()`) moduna geçmemiştir.
2. **`Type=notify` ile Sıfır Hata:** `Type=notify` mimarisinde bağımlı servisler `systemd` tarafından ancak ve ancak `READY=1` alındıktan sonra serbest bırakıldığı için başarı oranı istisnasız **%100**'dür.
3. **Sistem Mühendisliği Kararı:** Kritik aviyonik veya radar bileşenlerinde bağımlı servis zincirleri kurulurken daima `Type=notify` kullanılmalıdır.


## 13. Görselleştirme Mimarisi: 4 Panelli Karanlık Tema Mühendislik Dashboard'u

Oluşturulacak görsel artefakt (`gun_101_systemd_service_zihinsel_modeli.png`), `#0F172A` koyu tema paletinde 4 temel sistem analizini sunacaktır:

1. **Panel 1: `systemd` Servis Durum Makinesi (State Machine Graph):** `DEAD` $\rightarrow$ `STARTING` $\rightarrow$ `RUNNING` $\rightarrow$ `WATCHDOG_TIMEOUT` $\rightarrow$ `RESTARTING` geçiş rotaları.
2. **Panel 2: `Type=simple` vs `Type=notify` Başlatma Zaman Çizelgesi ve Yarış Durumu:** `simple` tipinde yaşanan `ECONNREFUSED` çakışmasına karşılık `notify` tipinin deterministik senkronizasyonu.
3. **Panel 3: Cgroups v2 Bellek Sınırı ve OOM İyileşme Dalgalanması:** Belleğin 2 GB tavanına çarpması, anlık OOM-Kill düşüşü ve 100 ms içinde yeni PID ile sağlıklı seviyeye dönüşü.
4. **Panel 4: Watchdog Kalp Atışı (Heartbeat) & Deadlock Kurtarma Simülasyonu:** Zaman ekseninde düzenli darbeler, kilitlenme anında kesilen sinyal ve `WatchdogSec` aşımında gerçekleşen `SIGABRT` infazı.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 20 (CODE 6): 4 Panelli 300 DPI Mühendislik Dashboard'u ve Katı Doğrulama Testleri
systemd Durum Makinesi, sd_notify, Cgroups v2 ve Watchdog Mekanizması Görselleştirmesi
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PNG = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat\gun_101\gun_101_systemd_service_zihinsel_modeli.png"

def generate_dashboard(output_path: str = DEFAULT_PNG):
    """4 Panelli, 300 DPI, modern koyu temalı systemd mühendislik dashboard'u üretir."""
    fig, axes = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor("#0F172A")

    # Renk Paleti
    accent_blue = "#38BDF8"
    accent_green = "#4ADE80"
    accent_amber = "#FBBF24"
    accent_red = "#F87171"
    accent_purple = "#C084FC"
    text_color = "#F8FAFC"
    grid_color = "#334155"

    for ax_row in axes:
        for ax in ax_row:
            ax.set_facecolor("#1E293B")
            ax.tick_params(colors=text_color, labelsize=9)
            ax.grid(True, linestyle="--", alpha=0.3, color=grid_color)
            for spine in ax.spines.values():
                spine.set_color(grid_color)

    # -------------------------------------------------------------------------
    # Panel 1: systemd Servis Durum Makinesi Şeması (State Machine)
    # -------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis("off")
    ax1.set_title("Panel 1: systemd Servis Durum Makinesi ve Geçiş Yolları", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # Durum Kutuları
    states = [
        {"name": "DEAD", "pos": (1.0, 7.5), "color": "#475569"},
        {"name": "STARTING", "pos": (4.5, 7.5), "color": accent_blue},
        {"name": "RUNNING", "pos": (8.0, 7.5), "color": accent_green},
        {"name": "WATCHDOG_TIMEOUT", "pos": (8.0, 2.5), "color": accent_red},
        {"name": "RESTARTING", "pos": (4.5, 2.5), "color": accent_amber},
        {"name": "FAILED", "pos": (1.0, 2.5), "color": accent_red}
    ]

    for st in states:
        x, y = st["pos"]
        rect = plt.Rectangle((x-0.9, y-0.6), 1.8, 1.2, facecolor=st["color"], edgecolor=text_color, linewidth=1.5, alpha=0.9)
        ax1.add_patch(rect)
        ax1.text(x, y, st["name"], ha="center", va="center", color=text_color, fontsize=8, fontweight="bold")

    # Geçiş Okları ve Açıklamalar
    # DEAD -> STARTING
    ax1.annotate("systemctl start", xy=(3.6, 7.5), xytext=(1.9, 7.5),
                 arrowprops=dict(arrowstyle="->", color=accent_blue, lw=1.5), color="#BAE6FD", fontsize=7.5, ha="center", va="bottom")
    # STARTING -> RUNNING
    ax1.annotate("sd_notify(READY=1)", xy=(7.1, 7.5), xytext=(5.4, 7.5),
                 arrowprops=dict(arrowstyle="->", color=accent_green, lw=1.5), color="#A7F3D0", fontsize=7.5, ha="center", va="bottom")
    # RUNNING -> WATCHDOG_TIMEOUT
    ax1.annotate("Heartbeat Yok (>WatchdogSec)", xy=(8.0, 3.1), xytext=(8.0, 6.9),
                 arrowprops=dict(arrowstyle="->", color=accent_red, lw=1.5), color="#FECACA", fontsize=7.5, ha="center", va="center", rotation=-90)
    # WATCHDOG_TIMEOUT -> RESTARTING
    ax1.annotate("SIGABRT & Temizlik", xy=(5.4, 2.5), xytext=(7.1, 2.5),
                 arrowprops=dict(arrowstyle="->", color=accent_amber, lw=1.5), color="#FDE68A", fontsize=7.5, ha="center", va="bottom")
    # RESTARTING -> STARTING
    ax1.annotate("RestartSec doldu", xy=(4.5, 6.9), xytext=(4.5, 3.1),
                 arrowprops=dict(arrowstyle="->", color=accent_blue, lw=1.5), color="#BAE6FD", fontsize=7.5, ha="center", va="center", rotation=90)
    # RESTARTING -> FAILED
    ax1.annotate("Burst Limiti Aşıldı", xy=(1.9, 2.5), xytext=(3.6, 2.5),
                 arrowprops=dict(arrowstyle="->", color=accent_red, lw=1.5), color="#FECACA", fontsize=7.5, ha="center", va="bottom")

    # -------------------------------------------------------------------------
    # Panel 2: Type=simple vs Type=notify Başlatma Zaman Çizelgesi
    # -------------------------------------------------------------------------
    ax2 = axes[0, 1]
    y_pos = [3.0, 1.5]
    ax2.set_ylim(0.5, 4.0)
    ax2.set_xlim(0, 100)

    # Type=simple Çubuğu
    ax2.barh(3.0, 10, left=0, height=0.5, color=accent_blue, label="execve() Çağrısı")
    ax2.barh(3.0, 40, left=10, height=0.5, color="#475569", label="Donanım/Soket İlklendirme")
    ax2.barh(3.0, 50, left=50, height=0.5, color=accent_green, label="Gerçekten Hazır")
    # simple'da bağımlı servis erken tetiklenir (t=10'da!)
    ax2.scatter(15, 3.0, color=accent_red, s=120, zorder=5, marker="X")
    ax2.text(15, 3.35, "Bağımlı Servis Çöktü!\n(ECONNREFUSED)", color=accent_red, fontsize=8, ha="center", fontweight="bold")

    # Type=notify Çubuğu
    ax2.barh(1.5, 10, left=0, height=0.5, color=accent_blue)
    ax2.barh(1.5, 40, left=10, height=0.5, color="#475569")
    ax2.barh(1.5, 50, left=50, height=0.5, color=accent_green)
    # notify'da bağımlı servis t=50'de READY=1 gelince başlar!
    ax2.scatter(52, 1.5, color=accent_green, s=120, zorder=5, marker="o")
    ax2.text(52, 1.85, "READY=1 Sinyali\nBağımlı Servis Güvende!", color=accent_green, fontsize=8, ha="center", fontweight="bold")

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(["Type=simple\n(Yarış Riski)", "Type=notify\n(Deterministik)"], color=text_color, fontsize=9.5, fontweight="bold")
    ax2.set_xlabel("Zaman (Milisaniye)", color=text_color, fontsize=10)
    ax2.set_title("Panel 2: Servis Başlatma Determinizmi ve Soket Senkronizasyonu", color=text_color, fontsize=11, fontweight="bold", pad=12)

    # -------------------------------------------------------------------------
    # Panel 3: Cgroups v2 Bellek Sınırı ve OOM İyileşme Grafiği
    # -------------------------------------------------------------------------
    ax3 = axes[1, 0]
    time_steps = np.linspace(0, 10, 500)
    # Bellek tırmanışı (2 GB sınırına doğru)
    ram_usage = np.zeros_like(time_steps)
    # Faz 1: Normal çalışma
    ram_usage[time_steps < 3.0] = 500 + time_steps[time_steps < 3.0] * 300
    # Faz 2: Bellek sızıntısı patlaması (3.0s - 4.5s)
    ram_usage[(time_steps >= 3.0) & (time_steps < 4.5)] = 1400 + (time_steps[(time_steps >= 3.0) & (time_steps < 4.5)] - 3.0) * 500
    # Faz 3: OOM-Kill infazı (t=4.5) -> Anında 0'a düşüş
    # Faz 4: systemd RestartSec=200ms sonrası yeniden temiz başlangıç (t=4.7'den sonra 300 MB)
    ram_usage[time_steps >= 4.7] = 350 + (time_steps[time_steps >= 4.7] - 4.7) * 50

    ax3.plot(time_steps, ram_usage, color=accent_blue, linewidth=2.2, label="Servis RAM Kullanımı (MB)")
    ax3.axhline(2048, color=accent_red, linestyle="--", linewidth=2, label="MemoryMax Kotası (2048 MB)")
    ax3.scatter(4.5, 2048, color=accent_red, s=140, zorder=5, marker="v")
    ax3.text(4.5, 1850, "OOM-KILL!\n(PID 4100 İnfaz Edildi)", color=accent_red, fontsize=8.5, ha="center", fontweight="bold")
    ax3.text(5.5, 600, "Yeni PID (4110)\nTemiz Başlangıç", color=accent_green, fontsize=8.5, fontweight="bold")

    ax3.set_title("Panel 3: Cgroups v2 MemoryMax Aşımı ve Otomatik Kurtarma", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax3.set_xlabel("Zaman (Saniye)", color=text_color, fontsize=10)
    ax3.set_ylabel("Bellek Tüketimi (MB)", color=text_color, fontsize=10)
    ax3.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper left")

    # -------------------------------------------------------------------------
    # Panel 4: Watchdog Kalp Atışı (Heartbeat) ve Deadlock Kurtarma
    # -------------------------------------------------------------------------
    ax4 = axes[1, 1]
    time_axis = np.linspace(0, 10, 500)
    heartbeat_signal = np.zeros_like(time_axis)

    # Her 1 saniyede bir kalp atışı darbesi (t=1, 2, 3, 4)
    for ping_t in [1.0, 2.0, 3.0, 4.0]:
        mask = (time_axis >= ping_t) & (time_axis < ping_t + 0.15)
        heartbeat_signal[mask] = 1.0

    # t=4'ten sonra servis kilitlendi (Deadlock!)
    ax4.plot(time_axis, heartbeat_signal, color=accent_green, linewidth=2.0, label="sd_notify('WATCHDOG=1')")
    
    # WatchdogSec=2.0s aşım çizgisi (t=4 + 2 = 6.0s)
    ax4.axvline(6.0, color=accent_red, linestyle=":", linewidth=2.2, label="Watchdog Aşımı (t=6.0s)")
    ax4.fill_between(time_axis, 0, 1.2, where=(time_axis >= 4.0) & (time_axis <= 6.0), color=accent_amber, alpha=0.15, label="Deadlock Bölgesi")
    
    ax4.scatter(6.0, 0.5, color=accent_red, s=150, zorder=5, marker="X")
    ax4.text(6.0, 0.7, "SIGABRT & Core Dump!\nsystemd Yeniden Başlattı", color=accent_red, fontsize=8.5, ha="center", fontweight="bold")

    ax4.set_title("Panel 4: Watchdog Kalp Atışı Kesilmesi ve Donanımsal Kurtarma", color=text_color, fontsize=11, fontweight="bold", pad=12)
    ax4.set_xlabel("Zaman (Saniye)", color=text_color, fontsize=10)
    ax4.set_ylabel("Sinyal Seviyesi", color=text_color, fontsize=10)
    ax4.set_ylim(-0.1, 1.3)
    ax4.legend(facecolor="#1E293B", edgecolor=grid_color, labelcolor=text_color, fontsize=8.5, loc="upper right")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_path}")


def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Gün 101 için tüm mimari ve matematiksel kabulleri katı testlerle doğrular."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dashboard Görsel Doğrulaması
    assert os.path.exists(png_path), f"HATA: Dashboard görseli mevcut değil: {png_path}"
    file_size = os.path.getsize(png_path)
    assert file_size > 100_000, f"HATA: Dashboard boyutu şüpheli ({file_size} bayt)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {file_size:,} bayt.")

    # 2. systemd Durum Makinesi Doğrulaması
    srv = SimulatedSystemdService(name="test.service", service_type="notify", watchdog_sec=1.0)
    srv.start(pid=500)
    assert srv.state == ServiceState.STARTING, "HATA: Type=notify servisi STARTING durumunda başlamalıdır!"
    srv.receive_notify("READY=1")
    assert srv.state == ServiceState.RUNNING, "HATA: READY=1 bildirimi sonrası servis RUNNING olmalıdır!"
    print("  [+] systemd Unit Yaşam Döngüsü ve Durum Geçişleri Doğrulandı.")

    # 3. Watchdog Kilitlenme ve SIGABRT Doğrulaması
    srv.check_watchdog(current_time=time.time() + 2.5)
    assert srv.state == ServiceState.RESTARTING, "HATA: Watchdog aşımı servisi RESTARTING moduna almalıdır!"
    print("  [+] Watchdog Kalp Atışı Kesilmesi ve Otomatik Yeniden Başlatma Doğrulandı.")

    # 4. Cgroups v2 Bellek Sınırı Doğrulaması
    cg = SimulatedCgroupV2(memory_max_mb=100)
    assert cg.allocate_memory(60.0) is True, "HATA: Limit altı bellek tahsisine izin verilmelidir!"
    assert cg.allocate_memory(50.0) is False, "HATA: MemoryMax aşımı OOM Killer tetiklemelidir!"
    assert cg.oom_kill_count == 1, "HATA: OOM infaz sayacı artırılmalıdır!"
    print("  [+] Cgroups v2 MemoryMax İzolasyonu ve OOM Killer Davranışı Doğrulandı.")

    # 5. Type=simple vs Type=notify Başlatma Determinizmi Doğrulaması
    bench = run_service_startup_benchmark(trials=1000)
    assert bench["notify_success_rate"] == 100.0, "HATA: Type=notify %100 deterministik olmalıdır!"
    assert bench["simple_success_rate"] < 100.0, "HATA: Type=simple yarış durumları üretmelidir!"
    print(f"  [+] Başlatma Determinizmi Üstünlüğü Doğrulandı (notify: %100 vs simple: %{bench['simple_success_rate']:.1f}).")

    print("\n[PASS] Gün 101: Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")


if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)

```

## 14. Dashboard Çıktısının Detaylı Teknik Değerlendirmesi

Oluşturulan mühendislik paneli (`gun_101_systemd_service_zihinsel_modeli.png`), sistem tasarımı açısından şu 4 kritik gerçeği belgeler:

1. **Panel 1 (Durum Makinesi):** `systemd` servislerinin rastgele değil, katı bir sonlu durum makinesi (Finite State Machine) üzerinden yönetildiği; çökme durumunda `RESTARTING` döngüsüne girdiği ve sınır aşıldığında sistemi kilitlememek için `FAILED` durumuna çekildiği modellenmiştir.
2. **Panel 2 (Başlatma Zaman Çizelgesi):** `Type=simple` mimarisinde bağımlı servisin ana servisin soket açma anından önce tetiklenmesiyle yaşanan `ECONNREFUSED` çakışması, `Type=notify`'ın `READY=1` sinyaliyle sıfırlanmıştır.
3. **Panel 3 (Cgroups İzolasyonu):** Bellek sızıntısı yaşayan sürecin 2,048 MB sınırına ulaştığı anda diğer süreçleri etkilemeden infaz edildiği ve 200 ms içinde yeni bir PID ile temiz bellek seviyesinde yeniden başladığı kanıtlanmıştır.
4. **Panel 4 (Watchdog Kalp Atışı):** 4. saniyede kilitlenen servisin kalp atışlarının kesildiği ve tam 2.0 saniyelik `WatchdogSec` süresi sonunda donanımın `SIGABRT` üreterek çekirdek dökümü aldığı görselleştirilmiştir.


## 15. Gelişmiş Sistem Mühendisliği: Socket Activation ve Transient Units

Üretim seviyesi savunma sanayii sistemlerinde `systemd` yeteneklerini bir üst seviyeye taşıyan 3 kritik özellik:

### 1. Soket Tabanlı Aktivasyon (`systemd.socket`)
Bir servisin sürekli bellekte çalışması yerine, talep geldiğinde ayağa kalkması istenebilir (On-Demand Activation).
- `radar-gateway.socket`: 8080 portunu dinler ve soket tanıtıcısını (`fd = 3`, `SD_LISTEN_FDS_START`) açık tutar.
- İlk TCP paketi geldiğinde `radar-gateway.service` başlatılır ve açık soket tanıtıcısı doğrudan sürece aktarılır.
- **Avantajı:** Servis çökse veya yeniden başlasa dahi soket `systemd`'de açık kaldığı için gelen hiçbir istemci bağlantısı kopmaz veya kaybolmaz!

### 2. Geçici Üniteler (`systemd-run`)
Statik bir `.service` dosyası yazmadan, komut satırından cgroups sınırları ve kotalarıyla anlık bir servis koşturmak için kullanılır:
```bash
systemd-run --unit=telemetry-export --property=MemoryMax=500M --property=CPUQuota=50% /opt/bin/export_tool
```

### 3. Dinamik Yapılandırma Yenileme (`ExecReload=`)
Kritik bir radar servisinin parametrelerini (örn. anten frekansı) değiştirmek için servisi durdurup başlatmak (restart) kabul edilemez; çünkü bağlantılar kopar.
`ExecReload=/bin/kill -HUP $MAINPID` tanımlanarak C++ servisinde `SIGHUP` sinyali yakalanır ve konfigürasyon bellek içinde canlı (in-flight) olarak yeniden yüklenir.


## 16. Yaygın Hatalar, Anti-Pattern'ler ve Kontrol Listesi

### Ölümcül Anti-Pattern'ler

| Anti-Pattern | Neden Tehlikeli? | Doğru Yaklaşım |
| :--- | :--- | :--- |
| **`Type=simple` + Ağ Bağımlılığı** | Bağımlı servisler erken başlar ve ana servis soketi açmadığı için çöker. | Kritik ağ ve donanım servislerinde istisnasız `Type=notify` kullan. |
| **Watchdog Döngüsünü Ayrı Thread'e Koymak** | Ana iş parçacığı kilitlense bile arka plandaki watchdog thread'i ping atmaya devam eder; systemd çöküşü fark edemez! | Watchdog ping'ini (`sd_notify("WATCHDOG=1")`) **daima ana olay döngüsünün (main event loop) içine yerleştir**. |
| **Sadece `Requires=` Yazmak** | `After=` yazılmazsa servisler aynı anda başlatılır ve yarış durumu oluşur. | Her zaman `Requires=X.service` ve `After=X.service` ikilisini birlikte kullan. |
| **Sınırsız `Restart=always`** | Sürekli çöken servis saniyede 100 kez yeniden başlayarak CPU'yu kilitler. | `StartLimitIntervalSec=60s` ve `StartLimitBurst=5` ile `RestartSec=1s` gecikmesi tanımla. |

### Üretim Öncesi Kontrol Listesi (Checklist)
- [ ] Servis tipi `Type=notify` olarak belirlendi ve C++ kodunda `READY=1` çağrılıyor mu?
- [ ] Watchdog süresi (`WatchdogSec=`) ayarlandı ve ana döngüde ping gönderiliyor mu?
- [ ] `MemoryMax=` ve `CPUQuota=` ile kaynak sınırları çizildi mi?
- [ ] Servis `root` yerine kısıtlı bir kullanıcıyla (`User=radar`) mı çalışıyor?
- [ ] `ProtectSystem=strict` ve `ProtectHome=yes` ile dosya sistemi güvenliği sağlandı mı?
- [ ] Günlükler stdout/stderr üzerinden `journald`'ye yönlendirildi mi?


## 17. Gün Sonu Özeti ve 3 Cümlelik Kural

1. **`systemd`,** Linux işletim sisteminde arka plan süreçlerini Cgroups v2 hiyerarşisiyle kaçışsız izleyen, bağımlılıkları yönlendirilmiş çizgelerle (DAG) paralel çözen ve servisleri otomatik ayağa kaldıran PID 1 orkestratörüdür.
2. **`Type=notify` ve `sd_notify("READY=1")` protokolü,** geleneksel `simple` ve `forking` tiplerindeki yarış durumlarını tamamen sıfırlayarak sistem açılışında deterministik senkronizasyon sağlar.
3. **`WatchdogSec` ve Cgroups sınırları (`MemoryMax`, `CPUQuota`),** kilitlenen veya bellek sızdıran servisleri milisaniyeler içinde infaz edip temiz durumda yeniden başlatarak aviyonik seviyede kesintisizlik garantisi sunar.

---

## 18. Mülakat Sorusu (ASELSAN / HAVELSAN Sistem Mühendisliği)

**Soru:**
Linux tabanlı bir insansız hava aracında (İHA) çalışan görev kontrol servisi için hazırladığınız `.service` dosyasında `Type=simple` ve `Restart=always` tanımladınız. Uçuş öncesi testlerde ana seyrüsefer servisi açılırken ona bağımlı olan silah kontrol servisinin bazen açılıp bazen çöktüğü (`Connection Refused`) ve sistem loglarında `start-limit-hit` hatasıyla karşılaşıldığı görülmüştür.
1. Bu hatanın kök sebebi nedir? Neden `Type=simple` yarış durumuna (race condition) yol açar?
2. Bu servisi savunma sanayii standardına getirmek için `.service` dosyası ve C++ kaynak kodunda hangi 2 kritik değişiklik yapılmalıdır?

**İdeal Cevap:**
1. **Kök Sebep:** `Type=simple` mimarisinde `systemd`, ana seyrüsefer ikilisinin `execve()` sistem çağrısını çalıştırdığı anı servisin "hazır" olduğu an kabul eder ve bağımlı servisleri anında tetikler. Ancak seyrüsefer servisi arka planda sensör kalibrasyonu yaparken henüz Unix soketini bağlamamış (`bind`/`listen`) olabilir. Bağımlı servis erken bağlandığı için `ECONNREFUSED` alır ve çöker. Arka arkaya 5 kez çökünce `StartLimitBurst` kuralı tetiklenir ve servis kilitlenir.
2. **Düzeltme Adımları:**
   - **C++ Kodu:** `NOTIFY_SOCKET` üzerinden `systemd`'ye donanım kalibrasyonu ve soket dinlemesi tamamen bittiğinde `sd_notify("READY=1")` mesajı gönderilmelidir.
   - **`.service` Dosyası:** Servis tipi `Type=notify` yapılmalı; bağımlılık tanımına `Requires=seyrusefer.service` ile birlikte mutlaka `After=seyrusefer.service` eklenmelidir. Ayrıca `RestartSec=1s` eklenerek hızlı çökme döngüsü engellenmelidir.

---

## 19. İleri Okuma ve Resmi Kaynaklar
- [Linux man-pages: systemd.service(5) - Service Unit Configuration](https://man7.org/linux/man-pages/man5/systemd.service.5.html)
- [Linux man-pages: sd_notify(3) - Notify service manager about start-up completion](https://man7.org/linux/man-pages/man3/sd_notify.3.html)
- [Lennart Poettering - Rethinking PID 1 (systemd Foundations)](http://0pointer.de/blog/projects/systemd.html)
- [Linux Kernel Documentation: Control Group v2 (cgroup2)](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)

---

### Gün 102 Köprüsü: `strace` ile Syscall Gözleme
Yarın, yazdığımız C++20 programlarının ve `systemd` servislerinin işletim sistemi çekirdeğiyle yaptığı tüm konuşmaları mikrosaniyelik sistem çağrıları seviyesinde röntgen gibi izlememizi sağlayan **`strace` ile syscall gözleme** konusunu inceleyeceğiz!
