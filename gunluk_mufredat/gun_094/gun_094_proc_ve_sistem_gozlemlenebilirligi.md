# GÜN 094: /proc Sözde Dosya Sistemi (procfs) ve Çekirdek Düzeyi Sistem Gözlemlenebilirliği

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

---

## Müfredat ve Savunma Sanayii Seviyesi Bilgilendirmesi

- **Faz**: F2 — Linux / POSIX Sistem Programlama ve Donanım Yakın Mimari
- **Konu**: `/proc` Sanal Dosya Sistemi, Süreç Durumu İnceleme (`stat`, `status`, `cmdline`, `fd`), CPU ve Bellek Metrikleri, Bağlam Değişimi Analizi
- **Ön Koşul Bilgi**: Gün 090 (File Descriptor), Gün 091 (POSIX I/O), Gün 092 (Buffered I/O) ve Gün 093 (Inode & Metadata)
- **Hedef Sistemler**: ASELSAN Gerçek Zamanlı Görev Sağlık İzleme (Health Monitoring Watchdog), HAVELSAN C4I Süreç Telemetrisi, TUSAŞ Aviyonik Kaynak Sızıntı Tespit Birimi, Linux Gözlemlenebilirlik ve Adli Analiz Araçları.

### 40-Nokta Kalite ve Mimari Beyanı
Bu çalışma modülü; POSIX.1-2024 ve Linux çekirdek sanal dosya sistemi (`procfs`) spesifikasyonları temel alınarak hazırlanmıştır. Bu çalışmada; diskte hiçbir fiziksel bayt kaplamayan (`st_size = 0`) bellek içi dinamik sözde dosya sistemi mimarisi, `/proc/PID/stat` alanlarındaki 52 farklı çekirdek metriğinin ayrıştırılması, süreç adında parantez ve boşluk bulunması durumundaki parsing tuzakları, `/proc/PID/fd` üzerinden açık soket ve dosya sızıntılarının tespiti, `/proc/stat` üzerinden iki zaman aralığı ($\Delta t$) bazında gerçek `%CPU` kullanım hesabı ve askeri görev kritik sistemlerde arızalı süreçlerin (D-state, Z-state) tespiti ele alınacaktır.


## 1. Teori ve Sistem Mimarisi: procfs Bellek İçi Sürücü Mimarisi

Linux çekirdeğinde `/proc`, disk üzerinde sektörleri olan fiziksel bir dosya sistemi değildir. Çekirdeğin iç veri yapılarını (proses tablosu, bellek yöneticisi, CPU zamanlayıcı) kullanıcı alanına standart POSIX dosya API'si (`open`, `read`, `close`) üzerinden sunan **sanal bir penceredir (pseudo-filesystem)**:

```
+-----------------------------------------------------------------------------+
|               KULLANICI ALANI (USER SPACE) - UYGULAMA / WATCHDOG            |
|                                                                             |
|   int fd = open("/proc/1420/status", O_RDONLY);                             |
|   read(fd, buffer, 4096);  ----------------------------------------+        |
+--------------------------------------------------------------------|--------+
                                                                     | Syscall
+--------------------------------------------------------------------v--------+
|               LINUX ÇEKİRDEĞİ (KERNEL SPACE) - VFS VE PROCFS               |
|                                                                             |
|   1. VFS Katmanı: /proc mount noktasını tanır.                              |
|   2. procfs Sürücüsü: İstenen PID (1420) için 'find_task_by_vpid' çağırır.  |
|   3. struct task_struct* task = pid_task(...);                             |
|   4. seq_file Arayüzü: Çekirdek içi struct alanlarını metne döker:          |
|      - task->comm        -> "Name: mission_ctrl"                            |
|      - task->state       -> "State: S (sleeping)"                           |
|      - task->mm->rss     -> "VmRSS: 48200 kB"                               |
|   5. Veri doğrudan kullanıcı belleğine (buffer) kopyalanır (copy_to_user).  |
|   * DİSKTE HİÇBİR VERİ YAZILMAZ VEYA SAKLANMAZ (RAM-ONLY VFS DOKUSU)!       |
+-----------------------------------------------------------------------------+
```

### `procfs` Dosyalarının Fiziksel Özellikleri:
1. **Boyut Sıfırdır (`st_size == 0`)**: Dosyalar dinamik üretildiğinden çekirdek önceden kaç bayt çıkacağını hesaplamaz. `stat()` çağrısı boyutu daima `0` döner. Bu nedenle dosyanın boyutu `st_size` ile okunamaz; `read()` çağrısı `0` (EOF) dönene kadar okunmalıdır!
2. **Kök Inode ve Dinamik Inode'lar**: Her çalışan sürecin sonlandığı an `/proc/PID/` dizini çekirdek tarafından anında yok edilir.
3. **NUL Karakter Ayrımı (`\0`)**: `/proc/PID/cmdline` ve `/proc/PID/environ` gibi dosyalar satır sonu (`\n`) yerine NUL (`\0`) baytı ile ayrılmış dizgiler içerir.


## 2. `/proc/PID/stat` ve `/proc/PID/status` Anatomisi

Bir sürecin sağlık durumunu gözlemlemek için kullanılan iki temel dosya:

### 1. `/proc/PID/stat` (Yüksek Hızlı Makine Formatı)
Boşluklarla ayrılmış 52 alandan oluşur. En kritik alanlar:
- **Alan 1 (`pid`)**: Süreç ID.
- **Alan 2 (`comm`)**: Parantez içinde süreç adı (Örn: `(flight_app)` veya boşluklu `(telemetry worker)`).
- **Alan 3 (`state`)**: Süreç durumu:
  - `R` (Running): Çalışıyor veya çalışmaya hazır.
  - `S` (Interruptible Sleep): Olay/I/O bekliyor (Normal durum).
  - `D` (Uninterruptible Sleep): Çekirdek I/O kilitlenmesi (Tehlikeli! Sinyalle öldürülemez).
  - `Z` (Zombie): Ölmüş, ebeveyni tarafından beklenmeyen süreç.
  - `T` (Stopped): Sinyal ile durdurulmuş (`SIGSTOP`).
- **Alan 4 (`ppid`)**: Ebeveyn PID.
- **Alan 14 (`utime`)**: Kullanıcı alanında harcanan CPU saat vuruşu (clock ticks).
- **Alan 15 (`stime`)**: Çekirdek alanında harcanan CPU saat vuruşu.
- **Alan 20 (`num_threads`)**: Sürecin toplam iş parçacığı (thread) sayısı.
- **Alan 24 (`rss`)**: Fiziksel bellekteki sayfa sayısı (Resident Set Size).

### 2. `/proc/PID/status` (İnsan Okunabilir Format)
Anahtar-değer çiftleri halindedir:
```text
Name:   sensor_collector
State:  S (sleeping)
Tgid:   2104
Pid:    2104
PPid:   1
VmPeak:    85240 kB    (Sürecin ulaştığı tepe sanal bellek boyutu)
VmSize:    81920 kB    (Mevcut toplam sanal bellek)
VmHWM:     24560 kB    (High Water Mark: Tepe fiziksel bellek)
VmRSS:     22140 kB    (Gerçek fiziksel RAM tüketimi)
Threads:   8           (İş parçacığı sayısı)
voluntary_ctxt_switches:    14205 (Gönüllü bağlam değişimi - I/O bekleyişi)
nonvoluntary_ctxt_switches: 312   (Zorunlu bağlam değişimi - Zaman aşımı)
```


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 4 (CODE 1): procfs Simülasyon Motoru ve Süreç Metrik Üreticisi
Süreç Tablosu, /proc/PID/stat ve /proc/PID/status Çekirdek Üreticisi
"""

import time
from typing import Dict, List, Any, Optional

class SimulatedProcess:
    """Linux çekirdeğindeki struct task_struct yapısının simülasyonu."""
    def __init__(self, pid: int, comm: str, ppid: int = 1, state: str = "S"):
        self.pid = pid
        self.comm = comm # Süreç adı (Boşluk içerebilir!)
        self.ppid = ppid
        self.state = state
        self.utime = 150 # Kullanıcı modu saat vuruşu (ticks)
        self.stime = 45  # Çekirdek modu saat vuruşu
        self.cutime = 0
        self.cstime = 0
        self.priority = 20
        self.nice = 0
        self.num_threads = 4
        self.starttime = int(time.time() * 100)
        self.vsize = 104857600  # 100 MB sanal bellek
        self.rss = 12500        # Sayfa sayısı (12500 * 4KB = 50 MB)
        self.open_fds = {0: "/dev/null", 1: "/var/log/app.log", 2: "/var/log/app.err", 3: "socket:[40960]"}

    def generate_stat_line(self) -> str:
        """Linux /proc/PID/stat formatına birebir uygun 52 alanlık satır üretir."""
        fields = [
            str(self.pid),
            f"({self.comm})", # Alan 2 daima parantez içindedir
            self.state,
            str(self.ppid),
            "1000", "1000", "0", "0", "0", "0", "0", "0", "0",
            str(self.utime),
            str(self.stime),
            str(self.cutime),
            str(self.cstime),
            str(self.priority),
            str(self.nice),
            str(self.num_threads),
            "0",
            str(self.starttime),
            str(self.vsize),
            str(self.rss),
            "18446744073709551615" # rsslim
        ]
        # Kalan alanlar için varsayılan sıfırlar ekle
        while len(fields) < 52:
            fields.append("0")
        return " ".join(fields)

    def generate_status_text(self) -> str:
        """Linux /proc/PID/status insan-okunabilir formatı üretir."""
        rss_kb = (self.rss * 4096) // 1024
        vsize_kb = self.vsize // 1024
        return (
            f"Name:\t{self.comm}\n"
            f"State:\t{self.state} (simulated)\n"
            f"Tgid:\t{self.pid}\n"
            f"Pid:\t{self.pid}\n"
            f"PPid:\t{self.ppid}\n"
            f"VmSize:\t{vsize_kb:8d} kB\n"
            f"VmRSS:\t{rss_kb:8d} kB\n"
            f"Threads:\t{self.num_threads}\n"
            f"voluntary_ctxt_switches:\t18204\n"
            f"nonvoluntary_ctxt_switches:\t452\n"
        )

# Test çalıştırması
if __name__ == "__main__":
    proc = SimulatedProcess(pid=1420, comm="telemetry worker", ppid=1, state="S")
    stat_raw = proc.generate_stat_line()
    print("=== [SIMÜLE EDİLMİŞ /proc/1420/stat ÇIKTISI] ===")
    print(stat_raw[:120] + " ... [TOPLAM 52 ALAN]")
    print("\n=== [SIMÜLE EDİLMİŞ /proc/1420/status ÇIKTISI] ===")
    print(proc.generate_status_text())

```

## 3. Kod 01 Analizi: Süreç Adı Ayrıştırma (Parsing) Tuzağı

Kod 01'deki çıktı incelendiğinde sistem mühendisliğindeki en meşhur bug'lardan biri ortaya çıkar:
- **Basit Ayrıştırma Hatası**: Birçok amatör araç `/proc/PID/stat` dosyasını boşluk karakterinden (`line.split(" ")`) ayırarak alanlara erişmeye çalışır.
- **Ölümcül Tuzak**: Süreç adı (`comm`), kullanıcının veya uygulamanın belirlediği herhangi bir metin olabilir: örneğin `(telemetry worker)` veya `(evil ) process)`.
- Eğer basitçe boşluktan ayrılırsa, süreç adı içerisindeki boşluklar alan indislerini kaydırır! `state` alanı Alan 3 yerine Alan 4 veya 5 haline gelir ve CPU/bellek hesaplamaları tamamen saçmalar.

### Kesin Çözüm Algoritması (Sağdan Sola Tarama)
Linux çekirdeği süreç adını daima parantez içerisine alır. Güvenli ayrıştırma:
1. Satırdaki **ilk parantezin (`(`)** yerini bul.
2. Satırdaki **son parantezin (`)`)** yerini bul (`rfind`).
3. İki parantez arasındaki bölümü `comm` olarak al.
4. Son parantezden sonraki metni boşluktan ayırarak kalan alanları ($3, 4, \dots, 52$) güvenle oku!


## 4. CPU Kullanım Oranı Hesabı: `/proc/stat` ve Zaman Türevi

Linux'ta bir anlık "CPU kullanımı" diye bir değer yoktur. CPU kullanımı daima iki zaman noktası ($t_1$ ve $t_2$) arasındaki **zaman türevidir**.

`/proc/stat` dosyasının ilk satırı (`cpu`) sistem genelindeki tüm işlemcilerin toplam saat vuruşlarını (jiffies / ticks) verir:
```text
cpu  user   nice  system  idle      iowait  irq  softirq  steal  guest
cpu  10145  201   4230    1984200   120     45   82       0      0
```

### Matematiksel Hesaplama Modeli
İki örnekleme anı ($t_1$ ve $t_2$) arasındaki CPU kullanım oranı:

$$\text{Total Time} = \text{user} + \text{nice} + \text{system} + \text{idle} + \text{iowait} + \text{irq} + \text{softirq} + \text{steal}$$

$$\text{Idle Time} = \text{idle} + \text{iowait}$$

$$\Delta \text{Total} = \text{Total}_{t_2} - \text{Total}_{t_1}, \quad \Delta \text{Idle} = \text{Idle}_{t_2} - \text{Idle}_{t_1}$$

$$\text{Sistem CPU \%} = \left( 1 - \frac{\Delta \text{Idle}}{\Delta \text{Total}} \right) \times 100$$

### Süreç Başına CPU Kullanım Oranı (Per-Process CPU %)
Bir sürecin harcadığı CPU:

$$\Delta \text{Process} = (\text{utime}_{t_2} + \text{stime}_{t_2}) - (\text{utime}_{t_1} + \text{stime}_{t_1})$$

$$\text{Süreç CPU \%} = \left( \frac{\Delta \text{Process}}{\Delta \text{Total}} \right) \times 100 \times N_{\text{CPU}}$$


## 5. `/proc/PID/fd` ve Kaynak Sızıntısı (FD Leak) Tespiti

Bir sürecin açık tuttuğu tüm dosya tanımlayıcıları `/proc/PID/fd/` dizini altında sembolik linkler olarak temsil edilir:

```bash
$ ls -l /proc/1420/fd
lrwx------ 1 root root 64 Sep 22 01:00 0 -> /dev/null
l-wx------ 1 root root 64 Sep 22 01:00 1 -> /var/log/radar.log
lrwx------ 1 root root 64 Sep 22 01:00 3 -> socket:[40960]
lr-x------ 1 root root 64 Sep 22 01:00 4 -> pipe:[51200]
lrwx------ 1 root root 64 Sep 22 01:00 5 -> anon_inode:[eventfd]
```

### Savunma Mühendisliği Açısından Önemi:
1. **Dosya Tanımlayıcı Sızıntısı (FD Leak)**: Yüksek hızlı bir C4I soket sunucusunda bağlantı kapandığında `close(fd)` çağrısı unutulursa, `/proc/PID/fd` altındaki link sayısı sürekli artar. Sayı `RLIMIT_NOFILE` limitine (genellikle 1024) ulaştığında sistem `EMFILE` hatası verir ve yeni bağlantı kabul edemez hale gelir.
2. **Kayıp Dosyayı Kurtarma**: Diskten `unlink` edilmiş ancak bir süreçte açık kalan dosyalar burada `(deleted)` ekiyle görünür. `cat /proc/1420/fd/1 > kurtarilan.log` komutuyla silinmiş dosyanın içeriği eksiksiz kurtarılabilir!


## 6. Savunma Sanayii Mimarisi: ASELSAN Görev Sağlık İzleyicisi (Watchdog)

Askeri görev bilgisayarlarında çalışan kritik süreçler (örneğin radar hedef takip veya aviyonik seyrüsefer yazılımı) harici bir gözetmen (Watchdog) süreci tarafından `/proc` üzerinden izlenir:

```
+-----------------------------------------------------------------------------+
|                  ASELSAN REAL-TIME HEALTH MONITORING DAEMON                 |
|                                                                             |
| Periyodik Döngü (100 ms):                                                   |
|   1. Hedef PID'nin /proc/PID/stat dosyasını oku:                            |
|      - State == 'D' mi? -> [KRİTİK UYARI]: Çekirdek I/O Kilitlenmesi!       |
|      - State == 'Z' mi? -> [HATA]: Süreç zombi olmuş, ebeveyn reaped yapmıyor|
|   2. /proc/PID/status dosyasından VmRSS ve VmHWM oku:                       |
|      - VmRSS > 500 MB mi? -> [BELLEK SIZINTISI]: Süreci kontrollü yeniden   |
|        başlat ve telemetri alarmı üret!                                     |
|   3. /proc/PID/fd dizinini say:                                             |
|      - FD Sayısı > 900 mü? -> [KAYNAK TÜKENME RİSKİ]: Alarm bayrağı kaldır. |
+-----------------------------------------------------------------------------+
```


## 7. C++20 Üretim Seviyesi `/proc` Ayrıştırıcı Mimarisi

Aşağıdaki C++20 sınıfı; süreç adı parantez tuzaklarına bağışık, sıfır-kopyalama (`std::string_view`) kullanan ve savunma standartlarına uygun bir `/proc` gözlemcisidir:

```cpp
#include <iostream>
#include <fstream>
#include <string>
#include <string_view>
#include <vector>
#include <charconv>

struct ProcessStatMetrics {
    int pid{0};
    std::string comm;
    char state{'?'};
    int ppid{0};
    unsigned long utime{0};
    unsigned long stime{0};
    long num_threads{0};
    unsigned long vsize{0};
    long rss_pages{0};
};

class SecureProcStatParser {
public:
    static bool parse(std::string_view line, ProcessStatMetrics& out) {
        // 1. İlk '(' ve son ')' karakterlerini bul
        auto open_paren = line.find('(');
        auto close_paren = line.rfind(')');
        if (open_paren == std::string_view::npos || close_paren == std::string_view::npos || close_paren < open_paren) {
            return false;
        }

        // PID ayrıştırma
        std::string_view pid_part = line.substr(0, open_paren - 1);
        std::from_chars(pid_part.data(), pid_part.data() + pid_part.size(), out.pid);

        // Comm (süreç adı) parantez içidir
        out.comm = std::string(line.substr(open_paren + 1, close_paren - open_paren - 1));

        // Kalan alanlar son parantezden sonradır
        std::string_view rest = line.substr(close_paren + 2);
        
        // Boşluklardan ayırarak alanları doldur
        std::vector<std::string_view> tokens;
        size_t start = 0;
        while (start < rest.size()) {
            size_t next = rest.find(' ', start);
            if (next == std::string_view::npos) {
                tokens.push_back(rest.substr(start));
                break;
            }
            tokens.push_back(rest.substr(start, next - start));
            start = next + 1;
        }

        if (tokens.size() < 22) return false;
        out.state = tokens[0][0];
        std::from_chars(tokens[1].data(), tokens[1].data() + tokens[1].size(), out.ppid);
        std::from_chars(tokens[11].data(), tokens[11].data() + tokens[11].size(), out.utime);
        std::from_chars(tokens[12].data(), tokens[12].data() + tokens[12].size(), out.stime);
        std::from_chars(tokens[17].data(), tokens[17].data() + tokens[17].size(), out.num_threads);
        std::from_chars(tokens[20].data(), tokens[20].data() + tokens[20].size(), out.vsize);
        std::from_chars(tokens[21].data(), tokens[21].data() + tokens[21].size(), out.rss_pages);

        return true;
    }
};
```


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Python ile Üretim Seviyesi ProcObserver Motoru
Güvenli Parantez Çözümleme, CPU Oranı ve Bellek Telemetrisi Hesaplayıcı
"""

from typing import Dict, Any, Optional

class ProcObserver:
    """Linux /proc/PID/stat ve /proc/stat ayrıştırma ve gözlem motoru."""
    
    @staticmethod
    def parse_stat_line(raw_line: str) -> Dict[str, Any]:
        """Süreç adındaki boşluk ve parantez tuzaklarına bağışık ayrıştırıcı."""
        raw_line = raw_line.strip()
        open_paren = raw_line.find("(")
        close_paren = raw_line.rfind(")")
        
        if open_paren == -1 or close_paren == -1 or close_paren < open_paren:
            raise ValueError(f"Geçersiz stat satır formatı: {raw_line}")
            
        pid = int(raw_line[:open_paren].strip())
        comm = raw_line[open_paren + 1 : close_paren]
        rest = raw_line[close_paren + 1 :].strip().split()
        
        # POSIX stat alan indeksleri (0 tabanlı rest listesi):
        # rest[0]  -> state (Field 3)
        # rest[1]  -> ppid (Field 4)
        # rest[11] -> utime (Field 14)
        # rest[12] -> stime (Field 15)
        # rest[17] -> num_threads (Field 20)
        # rest[20] -> vsize (Field 23)
        # rest[21] -> rss (Field 24)
        
        state = rest[0]
        ppid = int(rest[1])
        utime = int(rest[11])
        stime = int(rest[12])
        num_threads = int(rest[17])
        vsize_bytes = int(rest[20])
        rss_pages = int(rest[21])
        rss_bytes = rss_pages * 4096

        return {
            "pid": pid,
            "comm": comm,
            "state": state,
            "ppid": ppid,
            "utime": utime,
            "stime": stime,
            "total_time": utime + stime,
            "num_threads": num_threads,
            "vsize_mb": vsize_bytes / (1024 * 1024),
            "rss_mb": rss_bytes / (1024 * 1024)
        }

    @staticmethod
    def calculate_cpu_delta(t1_stat: Dict[str, Any], t2_stat: Dict[str, Any], 
                            delta_total_ticks: int, num_cpus: int = 4) -> float:
        """İki örnekleme anı arasındaki süreç CPU kullanım yüzdesini hesaplar."""
        delta_proc = t2_stat["total_time"] - t1_stat["total_time"]
        if delta_total_ticks <= 0:
            return 0.0
        cpu_usage = (delta_proc / delta_total_ticks) * 100.0 * num_cpus
        return min(cpu_usage, 100.0 * num_cpus)

if __name__ == "__main__":
    # Test Verisi (Süreç adında boşluk ve parantez içeren zorlu durum)
    tricky_stat = "2410 (telemetry (worker)) S 1 1000 1000 0 0 0 0 0 0 0 450 180 0 0 20 0 8 0 1000 157286400 16384 18446744073709551615"
    parsed = ProcObserver.parse_stat_line(tricky_stat)
    
    print("=== [GÜVENLİ STAT PARSER DOĞRULAMA] ===")
    print(f"PID          : {parsed['pid']}")
    print(f"Süreç Adı    : '{parsed['comm']}' (Tuzak parantez başarıyla korundu)")
    print(f"Durum        : {parsed['state']} (Sleeping)")
    print(f"İş Parçacığı : {parsed['num_threads']}")
    print(f"Sanal Bellek : {parsed['vsize_mb']:.2f} MB")
    print(f"Fiziksel RAM : {parsed['rss_mb']:.2f} MB")

```

## 8. Kod 02 Analizi ve Dayanıklı Ayrıştırma

Kod 02'deki ayrıştırıcı, zorlu test girdisi `(telemetry (worker))` üzerinde denenmiştir:
1. **İç İçe Parantez Dayanıklılığı**: `rfind(')')` kullanımı sayesinde iç içe geçmiş veya adında parantez bulunan süreç isimleri dahi hatasız olarak tek bir string halinde (`'telemetry (worker)'`) yakalanmıştır.
2. **Bellek Dönüşümü**: Sayfa cinsinden gelen `rss` (Resident Set Size), Linux x86_64 mimarisinde $4096$ bayt ile çarpılarak anlık fiziksel RAM tüketimine ($64.00\text{ MB}$) dönüştürülmüştür.
3. **Determinizm**: Regex veya string split karmaşası yerine $O(N)$ indis taraması kullanıldığı için gerçek zamanlı gözetleme döngülerinde mikrosaniyeler mertebesinde çalışır.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Sabotaj Laboratuvarı: D-State Süreç ve FD Sızıntısı
Ölümsüz Süreçler (D-State), Zombi Süreçler ve FD Tükenme Krizi Simülatörü
"""

from typing import Dict, List, Tuple

class ProcessSabotageLab:
    """Arızalı süreç durumlarını (/proc üzerinden) tespit eden simülasyon laboratuvarı."""
    
    @staticmethod
    def simulate_fd_leak(max_limit: int = 1024) -> Tuple[int, bool, str]:
        """Sürekli soket açıp kapatmayan bir sürecin FD tükenme krizini modeller."""
        open_fds = []
        for fd in range(3, 1100):
            if len(open_fds) >= max_limit - 3: # 0, 1, 2 hariç
                return len(open_fds), True, "EMFILE: Too many open files! Sistem bağlantı kabul edemiyor."
            open_fds.append(f"socket:[{fd*100}]")
        return len(open_fds), False, "Normal çalışma."

    @staticmethod
    def analyze_process_health(state: str, num_fds: int, rss_mb: float) -> Tuple[str, str]:
        """Süreç sağlık teşhisi koyar."""
        if state == "D":
            return "KRITIK_TEHLIKE", "Süreç kesintisiz uykuda (D-State)! Çekirdek I/O kilitlenmesi, kill -9 dahi durduramaz."
        elif state == "Z":
            return "HATA_ZOMBI", "Süreç zombi (Z-State)! Ebeveyn wait() çağrısı yapmıyor, PID tablosunu kirletiyor."
        elif num_fds > 900:
            return "KAYNAK_SIZINTISI", f"Kritik FD sızıntısı tespit edildi ({num_fds} açık FD)! EMFILE riski yüksek."
        elif rss_mb > 500:
            return "BELLEK_SIZINTISI", f"Aşırı RAM tüketimi ({rss_mb:.1f} MB)! OOM-Killer riski."
        return "SAGLIKLI", "Süreç normal çalışma sınırlarında."

if __name__ == "__main__":
    print("=== [SABOTAJ VE ARIZA TEŞHİS LABORATUVARI] ===")
    
    # Senaryo 1: FD Sızıntısı
    count, leaked, err_msg = ProcessSabotageLab.simulate_fd_leak(max_limit=1024)
    print(f"[*] FD Sızıntı Testi: Açık FD Sayısı = {count} -> {err_msg}")

    # Senaryo 2: D-State Süreç Analizi
    sev1, msg1 = ProcessSabotageLab.analyze_process_health(state="D", num_fds=25, rss_mb=45.0)
    print(f"[*] D-State Analizi : [{sev1}] {msg1}")

    # Senaryo 3: Zombi Süreç Analizi
    sev2, msg2 = ProcessSabotageLab.analyze_process_health(state="Z", num_fds=5, rss_mb=0.0)
    print(f"[*] Zombi Analizi   : [{sev2}] {msg2}")

```

## 9. Kod 03 Analizi: D-State ve Zombi Süreç Teşhisi

Kod 03 simülasyonu, savunma yazılımlarındaki en tehlikeli işletim sistemi krizlerini modellemiştir:
1. **D-State (Uninterruptible Sleep) Krizi**: Süreç arızalı bir NFS paylaşımı veya donanım sürücüsü üzerinde bloklanmış I/O beklerken çekirdek tarafından `TASK_UNINTERRUPTIBLE` durumuna alınır. Bu süreç sinyal kabul etmez; `kill -9` dahi süreci sonlandıramaz! Tek çözüm arızalı sürücüyü düzeltmek veya sistemi yeniden başlatmaktır. Watchdog süreci bu durumu anında alarm olarak raporlamalıdır.
2. **FD Tükenmesi (`EMFILE`)**: Limit 1024 iken soketler kapatılmadığında sistem 1021. tanımlayıcıda kilitlenir. Watchdog, `/proc/PID/fd` altındaki link sayısının 900'ü aştığını görünce erken müdahale alarmı üretmelidir.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Gerçek Zamanlı CPU Yüzdesi Hesaplama Laboratuvarı
İki Örnekleme Arasındaki Toplam ve Süreç Ticks Farkından %CPU Hesabı
"""

import time
from typing import Dict, List, Tuple

class CpuMonitorDemo:
    """İki zaman aralığında /proc/stat ve /proc/PID/stat delta hesaplayıcı."""
    
    def __init__(self, num_cores: int = 4):
        self.num_cores = num_cores
        
    def simulate_telemetry_stream(self) -> List[Dict[str, float]]:
        """10 adımlık zaman serisinde CPU kullanım değişimini simüle eder."""
        timeline = []
        
        # Başlangıç durumu (t0)
        sys_total = 100000
        proc_total = 5000
        
        # Simüle edilen iş yükü profili (Düşük -> Ağır Radar DSP -> Normal)
        workload_deltas = [20, 30, 80, 250, 400, 380, 150, 50, 30, 20]
        
        for step, p_delta in enumerate(workload_deltas):
            delta_total = 500 # Sistem genelinde geçen 500 tick
            sys_total += delta_total
            proc_total += p_delta
            
            # %CPU = (delta_proc / delta_total) * 100 * num_cores
            cpu_pct = (p_delta / delta_total) * 100.0 * self.num_cores
            cpu_pct = min(cpu_pct, 100.0 * self.num_cores)
            
            timeline.append({
                "step": step,
                "process_ticks_delta": p_delta,
                "total_ticks_delta": delta_total,
                "cpu_percent": cpu_pct
            })
            
        return timeline

if __name__ == "__main__":
    monitor = CpuMonitorDemo(num_cores=4)
    data = monitor.simulate_telemetry_stream()
    
    print("=== [GERÇEK ZAMANLI CPU YÜZDESİ ZAMAN SERİSİ] ===")
    for d in data:
        bar = "#" * int(d["cpu_percent"] / 10)
        print(f"Zaman T+{d['step']:02d}: Delta={d['process_ticks_delta']:3d} ticks -> CPU: %{d['cpu_percent']:5.1f} | {bar}")

```

## 10. Kod 04 Analizi: Çok Çekirdekli Sistemde CPU %100 Aşımı

Kod 04 simülasyon çıktısında önemli bir sistem kuralı gözlemlenir:
1. **Çok Çekirdek Çarpanı**: Linux'ta `top` ve `ps` komutları varsayılan olarak **Irix Modunda** çalışır. 4 çekirdekli bir sistemde bir süreç birden fazla iş parçacığıyla tüm çekirdekleri doyurursa, CPU kullanımı **%400.0**'e kadar çıkabilir!
2. **Normalizasyon (Solaris Modu)**: Eğer kullanımın %0 ile %100 arasında sınırlandırılması isteniyorsa, hesaplanan değer toplam çekirdek sayısına ($N_{\text{cores}}$) bölünmelidir.
3. **Zaman Aralığı ($\Delta t$) Seçimi**: Örnekleme aralığı çok kısa seçilirse (örneğin 1 ms), zamanlayıcı hassasiyeti nedeniyle gürültülü (noisy) sıçramalar görülür; çok uzun seçilirse (örneğin 10 saniye), ani CPU patlamaları (spikes) yakalanamaz. Savunma sistemlerinde altın standart **$100\text{ ms} - 500\text{ ms}$** aralığıdır.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): /proc/PID/maps Sanal Bellek Haritalama Analizi
VMA Alanları, Paylaşılan Kütüphaneler, Yığın (Stack) ve Öbek (Heap) İncelemesi
"""

from typing import List, Dict, Any

class MemoryMapsParser:
    """Linux /proc/PID/maps dosyasını ayrıştıran bellek analiz motoru."""
    
    @staticmethod
    def parse_maps_text(maps_content: str) -> List[Dict[str, Any]]:
        segments = []
        for line in maps_content.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            # Örnek satır: 00400000-00452000 r-xp 00000000 08:02 173521 /opt/aselsan/radar_app
            addr_range = parts[0].split("-")
            start_addr = int(addr_range[0], 16)
            end_addr = int(addr_range[1], 16)
            perms = parts[1]
            offset = parts[2]
            dev = parts[3]
            inode = parts[4]
            pathname = parts[5] if len(parts) > 5 else "[anon]"
            
            size_kb = (end_addr - start_addr) // 1024
            segments.append({
                "start": hex(start_addr),
                "end": hex(end_addr),
                "size_kb": size_kb,
                "perms": perms,
                "path": pathname
            })
        return segments

# Simüle edilmiş maps içeriği
sample_maps = """
00400000-0040c000 r-xp 00000000 08:01 1048576 /opt/aselsan/radar_app
0060b000-0060c000 r--p 0000b000 08:01 1048576 /opt/aselsan/radar_app
0060c000-0060d000 rw-p 0000c000 08:01 1048576 /opt/aselsan/radar_app
01420000-01450000 rw-p 00000000 00:00 0       [heap]
7f8a1000-7f9a1000 r-xp 00000000 08:01 2097152 /lib/x86_64-linux-gnu/libc.so.6
7ffd5000-7ffd7000 rw-p 00000000 00:00 0       [stack]
"""

if __name__ == "__main__":
    parsed_segments = MemoryMapsParser.parse_maps_text(sample_maps)
    print("=== [/proc/PID/maps SANAL BELLEK HARİTASI] ===")
    total_vma_kb = 0
    for s in parsed_segments:
        total_vma_kb += s['size_kb']
        print(f"[{s['start']} - {s['end']}] {s['perms']:4s} | {s['size_kb']:6d} KB | {s['path']}")
    print(f"\n[*] Toplam Haritalanmış Sanal Bellek: {total_vma_kb:,} KB ({total_vma_kb/1024:.2f} MB)")

```

## 11. Kod 05 Analizi: $W \oplus X$ Güvenlik İlkesi ve Bellek İncelemesi

`/proc/PID/maps` çıktısı savunma yazılımlarının güvenliğini doğrulamak için kritik bir kanıttır:
1. **$W \oplus X$ (Write XOR Execute) Doğrulaması**: Modern güvenli sistemlerde hiçbir bellek alanı aynı anda hem **Yazılabilir (`w`)** hem de **Çalıştırılabilir (`x`)** olamaz (`rwx` yasaktır).
   - Kod segmenti: `r-xp` (Okunabilir, Çalıştırılabilir, Yazılamaz).
   - Veri/Öbek segmenti: `rw-p` (Okunabilir, Yazılabilir, Çalıştırılamaz).
   - Eğer `/proc/PID/maps` içinde `rwxp` yetkisine sahip bir alan tespit edilirse, bu durum bir JIT motoru veya sisteme sızmış bir zararlı yazılım (shellcode) göstergesidir!
2. **Kütüphane Paylaşımı**: `/lib/libc.so.6` dosyasının `r-xp` alanı fiziksel bellekte tek bir kopyadır ve sistemdeki yüzlerce süreç tarafından ortaklaşa kullanılır.


## 12. Endüstriyel Mimari: Watchdog ve Otomatik Kurtarma

Savunma sanayiinde yüksek güvenilirlikli (High-Availability) servis mimarisi:

```
                  +-----------------------------------+
                  |   ASELSAN WATCHDOG DAEMON         |
                  +-----------------------------------+
                                    |
                    Her 200 ms'de   |  /proc/PID/stat & status
                    Polling         v
                  +-----------------------------------+
                  |   RADAR GÖREV SÜRECİ (PID: 1420)  |
                  +-----------------------------------+
                                    |
        +---------------------------+---------------------------+
        | Normal                    | Anomali                   | Çöküş
        v                           v                           v
  [ İŞLEME DEVAM ]         [ SAĞLIK ALARMI ]           [ OTOMATİK KURTARMA ]
  - RSS stabil             - RSS > Eşik (Sızıntı)       - PID kayboldu (Öldü)
  - State == 'S'/'R'       - FD > 900 (FD Leak)         - Yeniden başlat (fork+exec)
                           - State == 'D' (Kilitlenme)  - Olayı kara kutuya yaz
```


## 13. Hata Ayıklama ve Gözlemlenebilirlik Komutları

Sistem yöneticileri ve gömülü sistem mühendisleri için `/proc` analiz komutları:

```bash
# 1. Belirli bir sürecin anlık durum ve bellek dökümünü al
cat /proc/$(pgrep mission_app)/status

# 2. Açık tüm dosya ve soketleri gerçek hedefleriyle listele
ls -l /proc/$(pgrep mission_app)/fd

# 3. Sürecin çalışma argümanlarını NUL ayracı olmadan temiz oku
tr '\0' ' ' < /proc/$(pgrep mission_app)/cmdline; echo

# 4. Sistem genelindeki CPU kullanım sayaçlarını izle
head -n 1 /proc/stat

# 5. Sürecin kullandığı dinamik kütüphaneleri ve haritaları dök
cat /proc/$(pgrep mission_app)/maps

# 6. Sistemdeki toplam açık dosya tanımlayıcı sayısını kontrol et
cat /proc/sys/fs/file-nr
```


## 14. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **`/proc` Dosyalarını `st_size` ile Okumaya Çalışmak**:
   - *Yanlış*: `stat("/proc/PID/stat", &sb); char *buf = malloc(sb.st_size);` (`sb.st_size == 0` olduğu için 0 bayt ayrılır!).
   - *Doğru*: Sabit bir tampon (örneğin 4 KB) tahsis edip `read()` döngüsüyle `0` (EOF) gelene kadar okumak.
2. **`stat` Dosyasını Basitçe Boşluktan Bölmek**:
   - *Yanlış*: Süreç adında boşluk veya parantez olduğunda alan indislerinin kayması.
   - *Doğru*: İlk `(` ve son `)` indislerini bularak iki aşamalı ayrıştırma yapmak.
3. **Anlık CPU Değerini Tek Bir Örneklemeyle Bulmaya Çalışmak**:
   - *Yanlış*: `/proc/stat` dosyasını bir kez okuyup doğrudan oran çıkarmak.
   - *Doğru*: En az iki örnekleme alıp aradaki farkı ($\Delta \text{ticks}$) zaman farkına bölmek.
4. **`/proc/PID/fd` Dizinini `unlink` Etmeye Çalışmak**:
   - *Yanlış*: Sanal bir sembolik linki silerek dosya kapatmaya çalışmak.
   - *Sonuç*: `EPERM (Operation not permitted)` hatası. Dosyalar yalnızca sürecin `close()` çağrısıyla kapatılabilir.


## 15. Neden-Sonuç Tablosu ve Mimari Karar Matrisi

| Karar / Eylem | Doğrudan Sonuç | Potansiyel Risk / Hata Sınıfı | Mimari Tavsiye |
| :--- | :--- | :--- | :--- |
| `stat` dosyasını `rfind(')')` ile ayrıştırmak | Süreç adı ne olursa olsun metrikler kaymaz. | Sıfır hata ile kararlı telemetri. | Daima parantez aralığı arayın. |
| `/proc` okumalarında `lseek` varsaymak | Çekirdek seq_file yapısı seek desteklemeyebilir. | Bozuk veri veya sonsuz döngü. | Dosyayı baştan açıp sıralı okuyun. |
| Periyodik Watchdog aralığını 1 ms yapmak | Çekirdek VFS'ye aşırı syscall baskısı. | CPU'nun gözetleme işine harcanması. | İdeal aralık: $100\text{ ms} - 500\text{ ms}$. |
| FD sızıntılarını izlememek | Zamanla `RLIMIT_NOFILE` sınırına ulaşılır. | `EMFILE` hatası / Servis çöküşü. | `/proc/PID/fd` sayısını eşik değerle izleyin. |
| D-State sürecini `kill -9` ile durdurmaya çalışmak | Sinyal çekirdek tarafından teslim edilmez. | Zombi/asılan süreç birikimi. | Altta yatan I/O/donanım arızasını çözün. |


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 22 (CODE 6): 4-Panelli Görselleştirme Paneli ve Katı Doğrulama Testleri
procfs Mimarisi, %CPU Zaman Serisi, Bellek Dağılımı ve Süreç Durum Dağılımı
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_094_proc_ve_sistem_gozlemlenebilirligi.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    """4-panelli, koyu tema, 300 DPI kurumsal sistem mimarisi paneli üretir."""
    
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    accent_blue = '#38BDF8'
    accent_amber = '#F59E0B'
    accent_green = '#10B981'
    accent_red = '#EF4444'
    text_color = '#F8FAFC'

    # PANEL 1: procfs Sanal Dosya Sistemi Mimarisi
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("procfs Çekirdek-Kullanıcı Alanı Köprüsü (RAM-Only VFS)", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    boxes = [
        ("Kullanıcı Alanı: open('/proc/1420/stat')", 0.20, 0.80, accent_blue),
        ("Linux VFS: procfs Sürücüsü (No Disk I/O)", 0.20, 0.50, accent_amber),
        ("struct task_struct (Çekirdek Belleği)", 0.20, 0.20, accent_green),
        ("stat: 52 Metrik\n[utime, stime, state]", 0.70, 0.75, accent_blue),
        ("status: İnsan Okunabilir\n[VmSize, VmRSS, Threads]", 0.70, 0.45, accent_amber),
        ("fd/: Sembolik Linkler\n[socket, pipe, files]", 0.70, 0.15, accent_green)
    ]
    for text, x, y, col in boxes:
        ax1.text(x, y, text, ha='center', va='center', color=text_color, fontsize=8, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor=col, linewidth=2))

    ax1.annotate("", xy=(0.20, 0.60), xytext=(0.20, 0.72), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax1.annotate("", xy=(0.20, 0.30), xytext=(0.20, 0.42), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax1.annotate("", xy=(0.55, 0.75), xytext=(0.38, 0.50), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax1.annotate("", xy=(0.55, 0.45), xytext=(0.38, 0.50), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax1.annotate("", xy=(0.55, 0.15), xytext=(0.38, 0.50), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))

    ax1.set_xlim(0, 1.0)
    ax1.set_ylim(0, 1.0)
    ax1.axis('off')

    # PANEL 2: Çok Çekirdekli Sistemde Gerçek Zamanlı CPU Yüzdesi
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("Telemetri İzleme: İki Zaman Noktası Arasındaki %CPU Değişimi", fontsize=12, fontweight='bold', color=accent_amber, pad=12)
    
    steps = np.arange(10)
    cpu_vals = [16.0, 24.0, 64.0, 200.0, 320.0, 304.0, 120.0, 40.0, 24.0, 16.0]
    
    ax2.plot(steps, cpu_vals, marker='o', linewidth=2.5, color=accent_red, label='Radar Görev Süreci (4 Çekirdek Toplamı)')
    ax2.axhline(100.0, color=accent_amber, linestyle='--', label='1 Çekirdek Doyum Eşiği (%100)')
    ax2.axhline(300.0, color=accent_blue, linestyle=':', label='Kritik Alarm Eşiği (%300)')
    
    ax2.set_xlabel("Örnekleme Zamanı (T+100ms)", fontsize=10, color=text_color)
    ax2.set_ylabel("CPU Kullanımı (%)", fontsize=10, color=text_color)
    ax2.legend(facecolor='#0F172A', edgecolor='#334155', fontsize=8)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#475569')

    # PANEL 3: Sanal Bellek (VSize) vs Fiziksel Bellek (RSS) Dağılımı
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("Süreç Bellek Profili: VmSize vs VmRSS vs VmHWM", fontsize=12, fontweight='bold', color=accent_green, pad=12)
    
    processes = ["Radar DSP", "Navigasyon", "C4I Broker", "Watchdog"]
    vsize_vals = [250.0, 120.0, 180.0, 35.0]
    rss_vals = [65.0, 42.0, 58.0, 12.0]
    
    x = np.arange(len(processes))
    width = 0.35
    
    ax3.bar(x - width/2, vsize_vals, width, label='VmSize (Sanal Bellek MB)', color=accent_blue, alpha=0.85)
    ax3.bar(x + width/2, rss_vals, width, label='VmRSS (Fiziksel RAM MB)', color=accent_green, alpha=0.9)
    
    ax3.set_ylabel("Bellek (MB)", fontsize=10, color=text_color)
    ax3.set_xticks(x)
    ax3.set_xticklabels(processes, fontsize=9, color=text_color)
    ax3.legend(facecolor='#0F172A', edgecolor='#334155', fontsize=8)
    ax3.grid(True, linestyle='--', alpha=0.3, color='#475569')

    # PANEL 4: Linux Süreç Durum Dağılımı ve Tehlike Seviyeleri
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("Süreç Durumları ve Watchdog Müdahale Matrisi", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    states = ["S (Sleeping)", "R (Running)", "D (Disk/IO Wait)", "Z (Zombie)"]
    counts = [184, 8, 2, 1]
    colors = [accent_green, accent_blue, accent_red, accent_amber]
    
    bars = ax4.bar(states, counts, color=colors, width=0.55)
    ax4.set_ylabel("Sistemdeki Süreç Sayısı", fontsize=10, color=text_color)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars:
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"{int(bar.get_height())}",
                 ha='center', va='bottom', color=text_color, fontsize=9, fontweight='bold')

    plt.tight_layout()
    output_dir = os.path.dirname(os.path.abspath(output_png_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    plt.savefig(output_png_path, facecolor=fig.get_facecolor(), edgecolor='none', dpi=300)
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_png_path}")

def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Sistem varsayımlarını ve mimari sınırları doğrulayan katı testler."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")
    
    # 1. Dashboard Varlık Kontrolü
    assert os.path.exists(png_path), f"HATA: Dashboard görseli üretilemedi: {png_path}"
    assert os.path.getsize(png_path) > 100_000, "HATA: Dashboard görsel boyutu yetersiz!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {os.path.getsize(png_path):,} bayt.")

    # 2. Dayanıklı Ayrıştırma Doğrulaması (Parantez Tuzağı)
    test_proc = SimulatedProcess(pid=999, comm="complex (nested) app", ppid=1, state="R")
    test_proc.num_threads = 4
    test_line = test_proc.generate_stat_line()
    p = ProcObserver.parse_stat_line(test_line)
    assert p["pid"] == 999, "HATA: PID doğru ayrıştırılamadı!"
    assert p["comm"] == "complex (nested) app", "HATA: Süreç adı parantez tuzağında bozuldu!"
    assert p["state"] == "R", "HATA: State alanı kaydı!"
    assert p["num_threads"] == 4, "HATA: Thread sayısı yanlış okundu!"
    print("  [+] Dayanıklı /proc/PID/stat Ayrıştırma Mantığı Doğrulandı.")

    # 3. CPU Yüzdesi Hesaplama Doğrulaması
    t1 = {"total_time": 1000}
    t2 = {"total_time": 1100} # 100 ticks harcandı
    cpu = ProcObserver.calculate_cpu_delta(t1, t2, delta_total_ticks=1000, num_cpus=4)
    # (100 / 1000) * 100 * 4 = %40.0
    assert abs(cpu - 40.0) < 1e-5, f"HATA: Beklenen CPU %40.0, Hesaplanan: {cpu}"
    print("  [+] Çok Çekirdekli %CPU Delta Formülasyonu Doğrulandı.")

    # 4. FD Sızıntısı ve Limit Aşımı Doğrulaması
    count, leaked, _ = ProcessSabotageLab.simulate_fd_leak(max_limit=1024)
    assert leaked is True, "HATA: FD sızıntısı EMFILE krizini tetiklemelidir!"
    assert count >= 1020, "HATA: Limit civarında sızıntı yakalanmalıdır!"
    print("  [+] FD Sızıntısı (EMFILE) ve Eşik Değer Alarmı Doğrulandı.")

    # 5. D-State ve Zombi Teşhis Doğrulaması
    sev_d, _ = ProcessSabotageLab.analyze_process_health("D", 50, 100.0)
    assert sev_d == "KRITIK_TEHLIKE", "HATA: D-state süreç kritik tehlike olarak etiketlenmelidir!"
    sev_z, _ = ProcessSabotageLab.analyze_process_health("Z", 10, 0.0)
    assert sev_z == "HATA_ZOMBI", "HATA: Zombi süreç tespit edilmelidir!"
    print("  [+] D-State ve Z-State Çekirdek Arıza Teşhisi Doğrulandı.")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)

```

## 16. Savunma Sanayii Senaryoları ve Gün Sonu Özeti

### Savunma Sanayii ve Görev Kritik Sistem Senaryoları
1. **ASELSAN Aviyonik Görev Bilgisayarı Watchdog Ajanı**:
   - Uçuş sırasında görev bilgisayarında koşan hedef izleme yazılımının bellek sızıntısı (`VmRSS`) yapıp yapmadığı, `/proc/PID/status` üzerinden sürekli denetlenir. Belirlenen 500 MB eşiği aşıldığında sistem bir sonraki görev döngüsünde yedeğe (redundant node) devreder.
2. **HAVELSAN C4I Ağ Geçidi FD Kaçak Önleme**:
   - Yüksek tempolu taktik veri linki (Link-16 / JREAP) dağıtıcısında istemci bağlantıları koptuğunda soket tanımlayıcıları (`/proc/PID/fd`) izlenir. Sızıntı tespit edilirse sunucu kilitlenmeden önce soketler zorla süpürülür.

### Gün Sonu Özeti (3 Cümlelik Kapanış)
1. **Sanal Dosya Sistemi Mantığı**: `/proc`, diskte hiçbir fiziksel alan kaplamayan (`st_size=0`), çekirdeğin veri yapılarını dinamik olarak kullanıcı alanına açan bellek içi bir VFS sürücüsüdür.
2. **Gözlemlenebilirlik ve Ayrıştırma Güvenliği**: `/proc/PID/stat` dosyasındaki süreç adı tuzakları son parantez (`rfind`) tespitiyle aşılırken, CPU kullanım yüzdesi iki zaman noktası arasındaki saat vuruşu farkı ($\Delta \text{ticks}$) ile hesaplanır.
3. **Mühendislik Kuralı**: Görev kritik sistemlerde süreçlerin sağlık durumu yalnızca dönüş kodlarıyla değil; `/proc` üzerinden D-state kilitlenmesi, zombi durumu ve FD sızıntısı metrikleriyle sürekli denetlenmelidir.


## 17. Gelecek Gün Köprüsü: Gün 095

Yarın **GÜN 095** kapsamında:
- **Konu**: **Hafıza Haritalama (`mmap`), MAP_SHARED vs MAP_PRIVATE ve Sıfır Kopyalama (Zero-Copy I/O)**
- **Kapsam**: `mmap(2)`, `munmap(2)`, `msync(2)` sistem çağrıları, dosya destekli (file-backed) bellek haritaları, anonim bellek (`MAP_ANONYMOUS`), sayfa hataları (Page Fault) mekanizması ve yüksek hızlı radar telemetrisinde `read`/`write` yerine doğrudan bellek erişimi.
- **Hazırlık**: Bugün `/proc/PID/maps` üzerinden sanal bellek alanlarını gözlemledik; yarın bizzat kendi uygulamamızda dosyaları sanal bellek adres uzayımıza haritalayacağız.
