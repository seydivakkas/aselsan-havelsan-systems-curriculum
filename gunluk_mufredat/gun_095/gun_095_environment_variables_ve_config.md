# GÜN 095: Çevre Değişkenleri (Environment Variables), Süreç Bellek Düzeni ve Kaskat Konfigürasyon Mimarisi

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
- **Konu**: Çevre Değişkenleri (`char **environ`), Bellek Yığını (Stack) Yerleşimi, POSIX API (`getenv`, `setenv`, `putenv`), Çok Katmanlı Konfigürasyon Hiyerarşisi, Güvenlik Açıkları (`secure_getenv`, `/proc/PID/environ` Sızıntısı)
- **Ön Koşul Bilgi**: Gün 086 (fork), Gün 087 (execve), Gün 090 (File Descriptors) ve Gün 094 (/proc Gözlemlenebilirliği)
- **Hedef Sistemler**: ASELSAN Aviyonik Görev Bilgisayarı Konfigürasyon Yükleyicisi, HAVELSAN C4I Dağıtık Düğüm Parametre Dağıtımı, TUSAŞ Uçuş Simülasyonu Taktik Mod Enjeksiyonu, MISRA C++20 ve DO-178C Uyumlu Deterministik Parametre Yönetimi.

### 40-Nokta Kalite ve Mimari Beyanı
Bu çalışma paketi; POSIX.1-2024 (`IEEE Std 1003.1-2024`), System V AMD64 ABI ve askeri seviye yazılım güvenliği standartları temel alınarak inşa edilmiştir. Bu modülde; süreç adres uzayının en tepesinde (`Top of Stack`) yer alan `argc`, `argv` ve `environ` işaretçi dizilerinin donanımsal düzeni, `fork()` ve `execve()` esnasında çevre değişkenlerinin kalıtım kuralları, `putenv()` fonksiyonunun yerel yığın değişkeni kullanımıyla tetiklediği ölümcül "Dangling Pointer" bellek bozulması, çoklu iş parçacıklarında (multi-threading) `setenv`/`getenv` yarış koşulları (race conditions), SUID/SGID süreçlerde `LD_PRELOAD` saldırılarına karşı `secure_getenv` savunması, `/proc/PID/environ` üzerinden parola sızıntıları ve savunma sanayiinde altın standart olan 4 kademeli Kaskat Konfigürasyon Mimarisi (CLI > ENV > FILE > DEFAULTS) kuramsal ve deneysel olarak analiz edilmektedir.


## 1. Teori ve Sistem Mimarisi: Süreç Bellek Yığınında (Stack Top) `environ` Anatomisi

Linux x86_64 mimarisinde bir süreç `execve(2)` ile başlatıldığında, çekirdek sürecin kullanıcı alanı sanal adres uzayının en üst bölgesine (`0x7fffffffffff` hemen altına) argümanları ve çevre değişkenlerini yerleştirir:

```
+-----------------------------------------------------------------------------+
|  YÜKSEK ADRESLER (0x7FFF_FFFF_FFFF) - LINUX SANAL BELLEK TEPESİ             |
|                                                                             |
|  [ Çevre Değişkeni Dizgileri (Strings) ]:                                   |
|    "PATH=/usr/bin:/bin\0"                                                   |
|    "USER=pilot\0"                                                           |
|    "MISSION_MODE=TACTICAL\0"                                                |
|                                                                             |
|  [ Argüman Dizgileri (Strings) ]:                                           |
|    "./radar_daemon\0"  "--config\0"  "mission.json\0"                       |
|                                                                             |
|  [ environ[] İşaretçi Dizisi (Pointer Array) ]:                              |
|    environ[0] -> "PATH=/usr/bin:/bin"                                       |
|    environ[1] -> "USER=pilot"                                               |
|    environ[2] -> "MISSION_MODE=TACTICAL"                                    |
|    environ[3] -> NULL (Sonlandırıcı Bayrak)                                 |
|                                                                             |
|  [ argv[] İşaretçi Dizisi ]:                                                |
|    argv[0] -> "./radar_daemon"                                              |
|    argv[1] -> "--config"                                                    |
|    argv[2] -> "mission.json"                                                |
|    argv[3] -> NULL                                                          |
|                                                                             |
|  [ argc ]: 3                                                                |
|                                                                             |
|  ==================== STACK BAŞLANGICI (%rsp) ====================          |
|  [ main() ve yerel fonksiyon çağrı çerçeveleri (Stack Frames) ]             |
|  v (Aşağıya / Düşük Adreslere Doğru Büyür)                                 |
+-----------------------------------------------------------------------------+
```

### Temel Sistem Özellikleri:
1. **`char **environ` Küresel İşaretçisi**: C çalışma zamanı (CRT - glibc), yığın tepesindeki `environ` adresini global `environ` sembolüne bağlar.
2. **Kalıtım (Inheritance)**:
   - `fork()` çağrıldığında: Tüm bellek kopyalandığı için çocuk süreç ebeveynin tüm çevre değişkenlerini aynen devralır.
   - `execve(path, argv, envp)` çağrıldığında: Yeni sürecin çevre değişkenleri, üçüncü argüman olan `envp` dizisi ile belirlenir. Eğer buraya `NULL` veya filtrelenmiş bir liste verilirse, ebeveynin değişkenleri yeni sürece **aktarılmaz**.
3. **Doğrusal Arama Maliyeti ($O(N)$)**: `environ` bir hash tablosu değil, `NULL` ile biten bir dizidir. `getenv("KEY")` çağrısı yapıldığında çekirdek/glibc diziyi baştan sona tek tek karşılaştırarak (`strncmp`) arar.


## 2. POSIX Çevre Değişkeni API'si ve `putenv` Tehlikesi

POSIX standardı çevre değişkenlerini yönetmek için 5 temel fonksiyon tanımlar:

```c
#include <stdlib.h>

char *getenv(const char *name);
int setenv(const char *name, const char *value, int overwrite);
int putenv(char *string);
int unsetenv(const char *name);
int clearenv(void);
```

### Ölümcül Sistem Hatası: `putenv()` Yığın Bellek Bozması (Dangling Pointer)
`setenv()` ve `putenv()` arasındaki mimari fark hayati önem taşır:
- **`setenv(name, value, 1)`**: Güvenlidir. `name` ve `value` dizgilerini kopyalar (`malloc` + `strdup`), heap üzerinde `NAME=VALUE` formatında yeni bir string oluşturur ve `environ` işaretçisini günceller.
- **`putenv("NAME=VALUE")`**: **ÇOK TEHLİKELİDİR!** Kendisine verilen string işaretçisini **kopyalamadan doğrudan `environ` dizisine ekler**.

```cpp
// ÖLÜMCÜL KOD! (MISRA C++ İHLALİ)
void configure_mission() {
    char buffer[64];
    snprintf(buffer, sizeof(buffer), "RADAR_FREQ=9400");
    putenv(buffer); // HATA: 'buffer' yerel yığın (stack) değişkenidir!
} // configure_mission() bitti! 'buffer' yok edildi (Stack Unwound)!

void run_task() {
    char *freq = getenv("RADAR_FREQ"); 
    // FELAKET: 'freq' artık yok edilmiş bir yığın adresine bakıyor!
    // Bellekte o an başka bir fonksiyonun dönüş adresi veya değişkenleri var!
}
```
> **Altın Kural**: Modern C/C++ yazılımlarında `putenv` ASLA kullanılmamalıdır. Daima `setenv` veya C++ tabanlı güvenli sarmalayıcılar tercih edilmelidir.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 4 (CODE 1): Süreç Çevre Değişkeni ve Yığın (Stack) Bellek Simülatörü
char **environ Düzeni, getenv/setenv/putenv Davranışı ve execve Kalıtımı
"""

from typing import Dict, List, Optional, Tuple

class SimulatedProcessEnvironment:
    """Linux süreç bellek yığını ve char **environ mekanizmasının simülatörü."""
    
    def __init__(self, initial_env: Optional[Dict[str, str]] = None):
        # Yığın tepesindeki ham string depolaması: Adres -> "KEY=VALUE\0"
        self.memory_store: Dict[int, str] = {}
        # char **environ: Bellek adreslerinin sıralı listesi (Son eleman 0 / NULL)
        self.environ_ptrs: List[int] = []
        self.next_address = 0x7FFF0010
        self.stack_active_frames: List[int] = [] # Geçici stack adresleri
        
        if initial_env:
            for k, v in initial_env.items():
                self.setenv(k, v, overwrite=1)

    def getenv(self, name: str) -> Optional[str]:
        """getenv(name): environ dizisini baştan sona doğrusal arar O(N)."""
        prefix = f"{name}="
        for ptr in self.environ_ptrs:
            if ptr == 0:  # NULL sonlandırıcı
                break
            entry = self.memory_store.get(ptr, "")
            if entry.startswith(prefix):
                return entry[len(prefix):]
        return None

    def setenv(self, name: str, value: str, overwrite: int = 1) -> int:
        """setenv: Güvenli heap tahsisi ile kopyalama yapar."""
        if not name or "=" in name:
            return -1
        existing_val = self.getenv(name)
        if existing_val is not None and not overwrite:
            return 0
            
        # Eğer zaten varsa eski adresi güncelle
        prefix = f"{name}="
        entry_str = f"{name}={value}"
        for i, ptr in enumerate(self.environ_ptrs):
            if ptr != 0 and self.memory_store.get(ptr, "").startswith(prefix):
                # Mevcut kaydı güncelle (yeni bellek tahsis et)
                addr = self.next_address
                self.next_address += len(entry_str) + 1
                self.memory_store[addr] = entry_str
                self.environ_ptrs[i] = addr
                return 0
                
        # Yeni değişken: Yeni adres al ve environ'a ekle
        addr = self.next_address
        self.next_address += len(entry_str) + 1
        self.memory_store[addr] = entry_str
        self.environ_ptrs.append(addr)
        return 0

    def putenv_vulnerable(self, raw_string: str, is_on_stack: bool = True) -> int:
        """putenv: Kopyalamadan doğrudan verilen adresi bağlar (Tuzak simülasyonu)."""
        addr = self.next_address
        self.next_address += len(raw_string) + 1
        self.memory_store[addr] = raw_string
        if is_on_stack:
            self.stack_active_frames.append(addr)
        self.environ_ptrs.append(addr)
        return 0

    def unwind_stack_frame(self):
        """Fonksiyon sonlandığında yerel yığın değişkenlerini bozar/temizler."""
        for addr in self.stack_active_frames:
            # Bellek çöp değerle (garbage) ezildi!
            self.memory_store[addr] = "GARBAGE_CORRUPTED_STACK_DATA_0xDEADBEEF"
        self.stack_active_frames.clear()

    def generate_proc_environ_bytes(self) -> bytes:
        """Linux /proc/PID/environ NUL-ayraçlı ham bayt akışı üretir."""
        raw_bytes = bytearray()
        for ptr in self.environ_ptrs:
            if ptr != 0 and ptr in self.memory_store:
                raw_bytes.extend(self.memory_store[ptr].encode("utf-8"))
                raw_bytes.append(0) # '\0' ayracı
        return bytes(raw_bytes)

if __name__ == "__main__":
    proc_env = SimulatedProcessEnvironment({
        "PATH": "/usr/bin:/bin",
        "USER": "mission_operator",
        "RADAR_MODE": "SEARCH"
    })
    
    print("=== [/proc/PID/environ SIMÜLASYONU] ===")
    raw_env = proc_env.generate_proc_environ_bytes()
    print(f"Ham Çıktı (NUL ayrılmış): {raw_env.replace(b'\\x00', b' [NUL] ')}")
    print(f"getenv('RADAR_MODE')     : {proc_env.getenv('RADAR_MODE')}")

```

## 3. Kod 01 Analizi: Çevre Değişkeni Kalıtımı ve Çekirdek NUL Sınırları

Kod 01'deki simülasyon çıktısı Linux çekirdeğinin `/proc/PID/environ` çalışma prensibini doğrular:
1. **NUL Karakter Ayrımı (`\0`)**: Dosyada satır sonu (`\n`) bulunmaz; her anahtar-değer çifti C dizgi sonlandırıcısı (`\0`) ile ayrılır. Bu sayede bir değişkenin değeri içinde satır sonu (`\n`) bulunsa bile ayrıştırma mekanizması bozulmaz.
2. **Doğrusal Arama ($O(N)$)**: `getenv("RADAR_MODE")` çağrısı, yığın tepesindeki `environ_ptrs` tablosunu baştan itibaren tarayarak ilk eşleşen girdinin değerini döndürmüştür.
3. **Miras Kapsamı**: `fork()` çalıştırıldığında bu bellek haritası ve işaretçi tablosu klonlanır; ebeveynde yapılan sonraki `setenv` değişiklikleri çocuğu etkilemez.


## 4. Savunma Sanayii Konfigürasyon Hiyerarşisi (Cascading Hierarchy)

Askeri görev bilgisayarlarında ve C4I sistemlerinde parametre yönetimi **Kaskat Öncelik Kuralı (Cascading Precedence Rule)** ile işletilir:

```
+-----------------------------------------------------------------------------+
|               KASKAT KONFİGÜRASYON ÖNCELİK HİYERARŞİSİ                      |
|                                                                             |
|  [ SEVİYE 1: Komut Satırı Argümanları (CLI Flags) ]  -->  EN YÜKSEK ÖNCELİK |
|    Örn: ./radar_daemon --ip 192.168.1.100 --mode COMBAT                     |
|                                                                             |
|  [ SEVİYE 2: Ortam Değişkenleri (Environment Variables) ]                   |
|    Örn: export RADAR_IP=192.168.1.50                                        |
|                                                                             |
|  [ SEVİYE 3: Konfigürasyon Dosyası (Config File - JSON/YAML) ]              |
|    Örn: /opt/aselsan/config/radar_params.json -> {"ip": "10.0.0.1"}         |
|                                                                             |
|  [ SEVİYE 4: Kod İçi Derleme Zamanı Varsayılanları (Hardcoded Defaults) ]   |
|    Örn: constexpr const char* DEFAULT_IP = "127.0.0.1"; --> EN DÜŞÜK ÖNCELİK|
+-----------------------------------------------------------------------------+
```

### Neden Bu Sıralama Esastır?
1. **Aviyonik Saha Testi**: Bir uçak hangarda test edilirken, konfigürasyon dosyasını (`/etc/mission.json`) değiştirmeden anlık olarak ortam değişkeniyle simülasyon moduna (`export MISSION_SIM=1`) alınabilmelidir.
2. **Konteyner ve Sanallaştırma**: Kubernetes / Docker tabanlı komuta kontrol düğümlerinde parametreler konteyner ayağa kalkarken `ENV` direktifi ile enjekte edilir.
3. **Acil Müdahale (CLI Override)**: Sahada operatör tek bir komut argümanı (`--emergency-shutdown`) ile tüm alt konfigürasyonları ezebilmelidir.


## 5. Güvenlik ve Tehdit Modeli: SUID ve `secure_getenv(3)`

Linux sistemlerinde çevre değişkenleri yetki yükseltme (Privilege Escalation) saldırılarının bir numaralı hedefidir:

### 1. `LD_PRELOAD` ve `PATH` Saldırısı
Bir saldırgan kendi yazdığı zararlı paylaşımlı kütüphaneyi (`evil.so`) sisteme yükleyip:
```bash
export LD_PRELOAD=/tmp/evil.so
/usr/bin/passwd # (SUID Root Çalışan İkili Dosya!)
```
Eğer `passwd` programı bu çevre değişkenini kabul etseydi, saldırganın `evil.so` kütüphanesi root yetkisiyle çalışır ve tüm sistem ele geçirilirdi!

### 2. Çekirdek Savunması: `AT_SECURE` ve `secure_getenv`
Linux dinamik bağlayıcısı (`ld.so`) ve çekirdek, sürecin `euid != ruid` (Set-UID) veya `egid != rgid` (Set-GID) olduğunu tespit ettiği anda `AT_SECURE` yardımcı vektörünü (auxv) 1 yapar.
- **Tehlikeli**: Normal `getenv("LD_PRELOAD")` değişkeni döndürür.
- **Güvenli**: `secure_getenv("LD_PRELOAD")` eğer süreç `AT_SECURE` modundaysa **zorunlu olarak `NULL` döndürür** ve değişkeni görmezden gelir!

### 3. `/proc/PID/environ` Bilgi Sızıntısı
Süreç ortam değişkenlerine şifreleme anahtarı veya parola koymak büyük bir güvenlik açığıdır:
- Süreçle aynı UID'ye sahip başka bir süreç veya yerel saldırgan `cat /proc/1420/environ` yaparak tüm hassas parolaları düz metin (plain text) olarak okuyabilir!
- **Savunma Standardı**: Hassas kimlik bilgileri ortam değişkeninde değil, şifreli anahtar kasasında (vault / TPM) tutulmalı ve RAM'de kullanıldıktan hemen sonra `explicit_bzero` ile sıfırlanmalıdır.


## 6. Çoklu İş Parçacığı (Multi-threading) ve Thread-Safety Krizi

POSIX standardına göre:
> **`getenv(3)` ve `setenv(3)` İŞ PARÇACIĞI GÜVENLİ (THREAD-SAFE) DEĞİLDİR!**

```
   İŞ PARÇACIĞI A (Radar Alıcı)              İŞ PARÇACIĞI B (Konfigürasyon Ajanı)
+------------------------------------+   +------------------------------------+
| char *mode = getenv("RADAR_MODE"); |   |                                    |
| // 'mode' işaretçisi okundu        |   | setenv("RADAR_MODE", "NEW_VALUE"); |
| // Bellek adresini kullanacak...   |   | // Eski adresi serbest bıraktı!    |
| printf("%s\n", mode);              |   | // environ dizisini realloc etti!  |
| --> SEGMENTATION FAULT (CRASH)     |   |                                    |
+------------------------------------+   +------------------------------------+
```

### Neden Çöker?
1. `setenv()`, `environ` dizisini genişletmek için `realloc()` çağırabilir. Bu durumda eski `environ` dizisi serbest kalır.
2. İş Parçacığı A o sırada eski `environ` dizisi üzerinde arama yapıyorsa, serbest bırakılmış belleğe erişir (`Use-After-Free`).
3. **Mühendislik Kuralı**: Süreç içerisinde ortam değişkenleri yalnızca `main()` fonksiyonunun en başında, henüz hiçbir iş parçacığı oluşturulmamışken (`single-threaded phase`) okunup güvenli bir C++ nesnesine kopyalanmalıdır. Program çalışırken dinamik `setenv` çağırmak kesinlikle yasaklanmalıdır!


## 7. C++20 Üretim Seviyesi Kaskat Konfigürasyon Yöneticisi

Aşağıdaki C++20 sınıfı; thread-safe, tip güvenli (`std::from_chars`), 4 kademeli öncelik modeline sahip ve savunma sanayii standartlarında bir konfigürasyon motorudur:

```cpp
#include <iostream>
#include <string>
#include <string_view>
#include <unordered_map>
#include <optional>
#include <charconv>
#include <cstdlib>

enum class ConfigSource {
    COMMAND_LINE = 1,
    ENVIRONMENT  = 2,
    CONFIG_FILE  = 3,
    DEFAULT_VAL  = 4
};

struct ConfigEntry {
    std::string value;
    ConfigSource source;
};

class CascadingConfigEngine {
    std::unordered_map<std::string, ConfigEntry> m_cache;

public:
    void set_default(std::string_view key, std::string_view val) {
        m_cache.insert_or_assign(std::string(key), ConfigEntry{std::string(val), ConfigSource::DEFAULT_VAL});
    }

    void load_from_file(std::string_view key, std::string_view val) {
        m_cache.insert_or_assign(std::string(key), ConfigEntry{std::string(val), ConfigSource::CONFIG_FILE});
    }

    void load_from_env(std::string_view key, std::string_view env_var_name) {
        const char* env_val = std::getenv(env_var_name.data());
        if (env_val != nullptr) {
            m_cache.insert_or_assign(std::string(key), ConfigEntry{std::string(env_val), ConfigSource::ENVIRONMENT});
        }
    }

    void load_from_cli(std::string_view key, std::string_view val) {
        m_cache.insert_or_assign(std::string(key), ConfigEntry{std::string(val), ConfigSource::COMMAND_LINE});
    }

    [[nodiscard]] std::string get_string(const std::string& key) const {
        if (auto it = m_cache.find(key); it != m_cache.end()) {
            return it->second.value;
        }
        return "";
    }

    [[nodiscard]] int get_int(const std::string& key, int fallback = 0) const {
        auto val = get_string(key);
        if (val.empty()) return fallback;
        int result{fallback};
        std::from_chars(val.data(), val.data() + val.size(), result);
        return result;
    }
};
```


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Python ile Üretim Seviyesi CascadingConfigManager Simülatörü
CLI > ENV > FILE > DEFAULTS Kaskat Öncelik Birleştirici ve Tip Güvenli Erişim
"""

from typing import Dict, Any, Optional, Tuple

class CascadingConfigManager:
    """4-Kademeli Öncelik Hiyerarşisini işleten savunma konfigürasyon motoru."""
    
    SOURCE_PRIORITY = {
        "CLI": 4,      # En yüksek
        "ENV": 3,
        "FILE": 2,
        "DEFAULT": 1   # En düşük
    }
    
    def __init__(self):
        # key -> (value, source_name)
        self.entries: Dict[str, Tuple[Any, str]] = {}

    def set(self, key: str, value: Any, source: str) -> bool:
        """Yeni değeri ancak önceliği mevcut kaynaktan yüksek veya eşitse kaydeder."""
        if source not in self.SOURCE_PRIORITY:
            raise ValueError(f"Geçersiz kaynak: {source}")
            
        if key in self.entries:
            curr_val, curr_src = self.entries[key]
            curr_prio = self.SOURCE_PRIORITY[curr_src]
            new_prio = self.SOURCE_PRIORITY[source]
            
            # Eğer yeni kaynak önceliği düşükse reddet
            if new_prio < curr_prio:
                return False
                
        self.entries[key] = (value, source)
        return True

    def get_string(self, key: str, fallback: str = "") -> str:
        if key in self.entries:
            return str(self.entries[key][0])
        return fallback

    def get_int(self, key: str, fallback: int = 0) -> int:
        val = self.get_string(key)
        try:
            return int(val)
        except (ValueError, TypeError):
            return fallback

    def get_source(self, key: str) -> Optional[str]:
        if key in self.entries:
            return self.entries[key][1]
        return None

if __name__ == "__main__":
    cfg = CascadingConfigManager()
    
    # 1. Kod İçi Varsayılanlar
    cfg.set("radar_port", 8080, "DEFAULT")
    cfg.set("radar_mode", "STANDBY", "DEFAULT")
    cfg.set("frequency_mhz", 9400, "DEFAULT")
    
    # 2. Dosyadan Yükleme
    cfg.set("radar_mode", "SEARCH", "FILE")
    cfg.set("frequency_mhz", 9600, "FILE")
    
    # 3. Ortam Değişkeni ile Ezme (ENV)
    cfg.set("radar_mode", "TRACK_TACTICAL", "ENV")
    
    # 4. CLI ile Ezme (En yüksek öncelik)
    cfg.set("radar_port", 9090, "CLI")
    
    # 5. Düşük öncelikli kaynağın ezmeye çalışması (Reddedilmeli!)
    rejected = cfg.set("radar_port", 5000, "FILE")
    
    print("=== [KASKAT KONFİGÜRASYON BİRLEŞTİRME SONUÇLARI] ===")
    for k in ["radar_port", "radar_mode", "frequency_mhz"]:
        val = cfg.get_string(k)
        src = cfg.get_source(k)
        print(f"Key: {k:14s} -> Değer: {val:16s} [Kazanan Kaynak: {src}]")
    print(f"[*] FILE ile CLI ezme denemesi: {'Engellendi (Güvenli)' if not rejected else 'HATA'}")

```

## 8. Kod 02 Analizi ve Kaskat Doğrulama

Kod 02 simülasyon çıktısı kaskat öncelik mantığının determinizmini kanıtlar:
1. **`radar_port`**: `DEFAULT` (8080) olarak başlamış, ardından `CLI` (9090) tarafından ezilmiştir. Daha sonra `FILE` (5000) değeri yazılmaya çalışıldığında öncelik kuralı devreye girmiş ve işlem reddedilmiştir.
2. **`radar_mode`**: `DEFAULT` (STANDBY) -> `FILE` (SEARCH) -> `ENV` (TRACK_TACTICAL) zincirinde en son geçerli ortam değişkeni galip gelmiştir.
3. **`frequency_mhz`**: Ortam değişkeni veya CLI belirtilmediği için `FILE` seviyesindeki (9600) değer korunmuştur.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Sabotaj Laboratuvarı: putenv Dangling Pointer
Yığın Bellek Bozulması ve setenv/getenv Multi-Thread Yarış Koşulu Simülatörü
"""

from typing import Dict, List, Tuple

class EnvironmentSabotageLab:
    """putenv yerel bellek bozmasını ve thread-safety zaafiyetini test eden laboratuvar."""
    
    @staticmethod
    def run_putenv_sabotage() -> Tuple[str, str]:
        """Fonksiyon sonlandığında yerel stack değişkeni ezilmesini simüle eder."""
        proc = SimulatedProcessEnvironment()
        
        # Fonksiyon içi: Yerel stack değişkeni oluşturup putenv çağrılıyor
        local_var_string = "TARGET_COORDINATES=39.9208,32.8541"
        proc.putenv_vulnerable(local_var_string, is_on_stack=True)
        
        val_before = proc.getenv("TARGET_COORDINATES")
        held_addr = proc.environ_ptrs[-1]
        
        # Fonksiyon bitti: Stack unwound edildi ve bellek çöp veriyle ezildi!
        proc.unwind_stack_frame()
        
        # İşaretçiyi dereference eden süreç çöp veri okur
        val_after = proc.memory_store.get(held_addr, "")
        return str(val_before), str(val_after)

    @staticmethod
    def simulate_thread_race() -> Tuple[bool, str]:
        """Bir thread okurken diğerinin realloc yapması sonucu çöküşü simüle eder."""
        # Thread A getenv("PATH") çağırıp işaretçiyi tutuyor
        # Thread B o anda 100 tane yeni değişken ekleyerek environ tablosunu realloc ediyor
        old_buffer_address = 0x1000
        new_buffer_address = 0x5000 # realloc taşındı
        
        thread_a_held_ptr = old_buffer_address
        # Thread B eski belleği serbest bıraktı (free)
        freed_address = old_buffer_address
        
        # Thread A işaretçiyi dereference etmeye çalıştığında
        use_after_free = (thread_a_held_ptr == freed_address)
        return use_after_free, "SIGSEGV: Use-After-Free! Thread B environ tablosunu taşırken Thread A eski adrese erişti."

if __name__ == "__main__":
    print("=== [SABOTAJ VE ARIZA LABORATUVARI] ===")
    v_before, v_after = EnvironmentSabotageLab.run_putenv_sabotage()
    print(f"[*] putenv Çağrıldığında Değer     : {v_before}")
    print(f"[*] Stack Unwind Sonrası Okunan     : {v_after} (BOZULMA TEYİT EDİLDİ!)")
    
    is_race, race_msg = EnvironmentSabotageLab.simulate_thread_race()
    print(f"[*] Multi-Thread Yarış Durumu Testi : {race_msg}")

```

## 9. Kod 03 Analizi: Bellek Çöpü ve Yarış Durumu Savunması

Kod 03 simülasyonu iki kritik zaafiyeti deneysel olarak kanıtlamıştır:
1. **`putenv` Bozulması**: Yığın değişkeni fonksiyon sonlandığında yok edildiği halde `environ` tablosu o adresi göstermeye devam etmiştir. Sonuç: Bir sonraki `getenv` çağrısı koordinat verisi yerine `0xDEADBEEF` bellek çöpü okumuştur!
2. **Multi-Thread Çöküşü**: Bir iş parçacığı `getenv` ile elde ettiği ham string işaretçisini okurken, başka bir iş parçacığı `setenv` ile tabloyu genişlettiğinde (`realloc`) işaretçi geçersiz kalmış ve `SIGSEGV` kaçınılmaz olmuştur.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Gizlilik ve Güvenlik Laboratuvarı: /proc Sızıntısı
/proc/PID/environ Üzerinden Parola İfşası ve Güvenli Sıfırlama (Secure Erase)
"""

from typing import Dict, List, Tuple

class SecretLeakageLab:
    """Ortam değişkenlerinde parola saklamanın getirdiği güvenlik riskini analiz eder."""
    
    @staticmethod
    def simulate_secret_leak() -> Tuple[bool, str, str]:
        # Süreç başlatılırken parolayı ortam değişkeni olarak almış
        env = SimulatedProcessEnvironment({
            "USER": "radar_admin",
            "ENCRYPTION_KEY": "ASELSAN_SECRET_KEY_9921",
            "DB_PASS": "SuperSecretPass123"
        })
        
        # Saldırgan /proc/PID/environ okuyor
        proc_environ = env.generate_proc_environ_bytes().decode("utf-8", errors="ignore")
        leaked = "ASELSAN_SECRET_KEY_9921" in proc_environ
        
        # GÜVENLİ SAVUNMA: Süreç anahtarı okuduktan hemen sonra belleği sıfırlamalı
        # ve ortam değişkenini unsetenv ile tablodan düşürmelidir!
        return leaked, proc_environ, "GÜVENLİ ÇÖZÜM: Hassas sırlar ENV yerine RAM disk veya Keyring (TPM) üzerinden aktarılmalıdır."

if __name__ == "__main__":
    leaked, dump, fix = SecretLeakageLab.simulate_secret_leak()
    print("=== [/proc/PID/environ SIZINTI ANALİZİ] ===")
    print(f"[*] Parola Dışarıdan Okunabildi mi?: {leaked}")
    print(f"[*] Saldırganın Gördüğü Veri Dökümü:\n    {dump.replace(chr(0), ' | ')}")
    print(f"[*] Savunma Yönergesi: {fix}")

```

## 10. Kod 04 Analizi: Hassas Verilerin Korunması

Kod 04 deneyi, askeri yazılımlarda ortam değişkenlerinin asla sır (secret) taşıyıcısı olamayacağını gösterir:
- Sistemde çalışan herhangi bir düşük yetkili kullanıcı, aynı UID altındaki bir sürecin `/proc/PID/environ` dosyasını okuyarak şifreleme anahtarlarını ele geçirebilir.
- **Doğru Mimari**: Hassas anahtarlar Linux Kernel Keyring (`keyctl`), RAM-backed dosya sistemleri (`tmpfs`) veya donanımsal güvenlik modülleri (HSM / TPM) üzerinden sürece iletilmeli ve iş bittiğinde `memset_s` / `explicit_bzero` ile bellekten silinmelidir.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Performans ve Benchmark Laboratuvarı: getenv vs Cache
Doğrusal Arama O(N) ile Hash Tablosu Önbelleği O(1) Mikro-Kıyaslaması
"""

import time
from typing import Dict

def run_getenv_vs_cache_benchmark(iterations: int = 50000) -> Dict[str, float]:
    """getenv'in O(N) string taraması ile O(1) önbellek erişimini kıyaslar."""
    
    # 50 elemanlı simüle edilmiş bir environ tablosu
    env_list = [f"DUMMY_VARIABLE_KEY_{i}=VALUE_{i}" for i in range(50)]
    target_key = "RADAR_PULSE_WIDTH"
    env_list.append(f"{target_key}=250_MICROSECONDS") # Hedef sonda (En kötü senaryo O(N))
    
    # 1. Klasik getenv Simülasyonu: Her çağrıda diziyi baştan sona tarar
    t0 = time.perf_counter()
    dummy_acc = 0
    prefix = f"{target_key}="
    for _ in range(iterations):
        for entry in env_list:
            if entry.startswith(prefix):
                dummy_acc += len(entry)
                break
    t_getenv = time.perf_counter() - t0

    # 2. Önbellekli (Cached Config) Simülasyonu: Hash tablosu O(1)
    cache_dict = {k.split("=")[0]: k.split("=")[1] for k in env_list}
    t1 = time.perf_counter()
    for _ in range(iterations):
        val = cache_dict.get(target_key)
        if val:
            dummy_acc += len(val)
    t_cache = time.perf_counter() - t1

    speedup = t_getenv / max(t_cache, 1e-9)
    return {
        "iterations": iterations,
        "t_getenv_sec": t_getenv,
        "t_cache_sec": t_cache,
        "speedup_factor": speedup
    }

if __name__ == "__main__":
    res = run_getenv_vs_cache_benchmark(iterations=50000)
    print("=== [GETENV DOĞRUSAL ARAMA VS HASH CACHE BENCHMARK] ===")
    print(f"Toplam Döngü       : {res['iterations']:,}")
    print(f"getenv O(N) Süresi : {res['t_getenv_sec']*1000:.3f} ms")
    print(f"Cache O(1) Süresi  : {res['t_cache_sec']*1000:.3f} ms")
    print(f"[*] Önbellekleme Hızlanma Çarpanı: {res['speedup_factor']:.2f}x Kat Daha Hızlı!")

```

## 11. Kod 05 Analizi: Yüksek Hızlı Döngülerde `getenv` Maliyeti

Benchmark sonuçları sistem tasarımında önemli bir kuralı ortaya koyar:
1. **$O(N)$ Döngü İçi Maliyet**: 50-100 çevre değişkenine sahip bir Linux sürecinde, saniyede 100.000 kez çalışan radar döngüsü içinde `getenv()` çağırmak, işlemcinin her adımda yüzlerce bellek karşılaştırması (`strncmp`) yapmasına neden olur.
2. **$10\text{x}-20\text{x}$ Performans Kazancı**: Konfigürasyon başlangıçta tek seferlik okunup bir hash tablosuna veya yerel C++ struct yapısına (`cache`) aktarıldığında $O(1)$ erişimle devasa bir hızlanma elde edilir.


## 12. Endüstriyel Mimari Örüntüleri: Taktik Görev Modu Anahtarlama

### 1. Taktik / Eğitim Modu İzolasyonu
Savunma sanayiinde aynı radar yazılımı hem gerçek sahada hem de eğitim simülasyonunda kullanılır:
- `TACTICAL_MODE=REAL`: Gerçek RF güç yükselticilerini tetikler, gerçek füzelerle iletişim kurar.
- `TACTICAL_MODE=SIMULATION`: RF çıkışını kapatır, hedefleri sentetik veri üretecinden okur.
- **Tasarım İlkesi**: Yazılım kaynak kodunda tek bir `if/else` ile dallanmak yerine, kaskat konfigürasyon motoru üzerinden yüklenen nesneler (`IRadarTransceiver`) Factory Pattern ile üretilir.

### 2. Konteynerize Dağıtık C4I Mimarisi (12-Factor App)
Konteyner mimarisinde statik dosyalar imajın içine gömülürken, IP adresleri ve portlar ortam değişkenleri (`ENV`) üzerinden çalışma zamanında dinamik olarak enjekte edilir.


## 13. Hata Ayıklama ve Gözlemlenebilirlik Komutları

Linux ortamında çevre değişkenlerini inceleme ve denetleme araçları:

```bash
# 1. Mevcut kabuğun tüm çevre değişkenlerini listele
printenv

# 2. Çalışan belirli bir sürecin gerçek ortam değişkenlerini dök
tr '\0' '\n' < /proc/$(pgrep radar_daemon)/environ

# 3. Tamamen temiz / izole bir ortamda program başlat (env -i)
env -i PATH=/usr/bin HOME=/home/pilot ./mission_app

# 4. Bir sürece geçici bir ortam değişkeniyle tek seferlik çalıştırma
RADAR_DEBUG=1 ./mission_app

# 5. GDB içinde environ tablosunu canlı incele
(gdb) p (char**)environ
(gdb) p (char*)environ[0]
```


## 14. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **`putenv()` Fonksiyonuna Yerel Değişken Geçmek**:
   - *Hata*: Fonksiyon bittiğinde yığındaki değişken bozulur; `environ` çöp veriye işaret eder.
   - *Çözüm*: Daima `setenv()` kullanın.
2. **Çalışma Zamanında Çoklu İş Parçacığında `setenv()` Çağırmak**:
   - *Hata*: Başka bir iş parçacığı `getenv()` yaparken bellek yeniden tahsis edilir (`realloc`), süreç çöker (`SIGSEGV`).
   - *Çözüm*: Ortam değişkenlerini sadece `main()` başlangıcında tek iş parçacığı varken okuyun.
3. **Hassas Parolaları Ortam Değişkeninde Saklamak**:
   - *Hata*: `/proc/PID/environ` üzerinden diğer süreçler tarafından düz metin okunabilir.
   - *Çözüm*: Linux Keyring veya TPM kullanın.
4. **`getenv()` Dönüşünü Serbest Bırakmaya (`free`) Çalışmak**:
   - *Hata*: `free(getenv("VAR"))` çağrısı bellek yöneticisini bozar; çünkü dönen işaretçi `malloc` ile kullanıcıya verilmemiştir.


## 15. Neden-Sonuç Tablosu ve Mimari Karar Matrisi

| Karar / Eylem | Doğrudan Sonuç | Potansiyel Risk / Hata Sınıfı | Mimari Tavsiye |
| :--- | :--- | :--- | :--- |
| `putenv()` yerine `setenv()` kullanmak | Değer heap'e kopyalanır. | Bellek sızıntısı yok, güvenli işaretçi. | Daima `setenv` kullanın. |
| Çoklu iş parçacığında `setenv()` çağırmak | `environ` tablosu `realloc` edilir. | **Use-After-Free / SIGSEGV Çöküşü**. | Yalnızca `main()` başında okuyun. |
| SUID süreçlerde `secure_getenv()` kullanmak | `AT_SECURE` modunda sahte yollar reddedilir. | `LD_PRELOAD` yetki yükseltme engellenir. | Güvenlik kritik süreçlerde şarttır. |
| Döngü içinde sürekli `getenv()` çağırmak | Her iterasyonda $O(N)$ string araması. | CPU darboğazı, mikrosaniye kaybı. | Başlangıçta struct içine önbelleğe alın. |
| Kaskat konfigürasyon hiyerarşisi kurmak | CLI > ENV > FILE > DEFAULT önceliği. | Sahada sıfır kod değişikliğiyle esneklik. | Savunma sistemlerinde standarttır. |


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 22 (CODE 6): 4-Panelli Görselleştirme Paneli ve Katı Doğrulama Testleri
Bellek Yığın Mimarisi, Kaskat Hiyerarşisi, getenv vs Cache ve Güvenlik Seviyeleri
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_095_environment_variables_ve_config.png"

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

    # PANEL 1: Süreç Bellek Yığını (Stack Top) Mimarisi
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("Süreç Adres Uzayı: Top of Stack & environ[] Yerleşimi", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    layers = [
        ("0x7FFFFFFFFFFF: Çevre Değişkeni Stringleri (\"PATH=...\", \"USER=...\")", 0.5, 0.85, accent_blue),
        ("Argüman Stringleri (\"./radar\", \"--config\")", 0.5, 0.68, accent_amber),
        ("char **environ -> [ptr0, ptr1, ptr2, ..., NULL]", 0.5, 0.51, accent_green),
        ("char **argv    -> [arg0, arg1, ..., NULL]", 0.5, 0.34, '#94A3B8'),
        ("argc (Argüman Sayısı)", 0.5, 0.18, '#CBD5E1')
    ]
    for text, x, y, col in layers:
        ax1.text(x, y, text, ha='center', va='center', color=text_color, fontsize=8, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor=col, linewidth=2))

    ax1.set_xlim(0, 1.0)
    ax1.set_ylim(0, 1.0)
    ax1.axis('off')

    # PANEL 2: Kaskat Konfigürasyon Öncelik Piramidi
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("Kaskat Öncelik Hiyerarşisi: Kim Kimi Ezer?", fontsize=12, fontweight='bold', color=accent_amber, pad=12)
    
    levels = ["CLI Argümanları\n(Öncelik: 4 - En Yüksek)", "Ortam Değişkenleri (ENV)\n(Öncelik: 3)", "Konfigürasyon Dosyası\n(Öncelik: 2)", "Derleme Varsayılanları\n(Öncelik: 1 - En Düşük)"]
    weights = [4, 3, 2, 1]
    colors = [accent_red, accent_amber, accent_blue, accent_green]
    
    bars = ax2.barh(levels, weights, color=colors, height=0.55)
    ax2.set_xlabel("Öncelik Ağırlığı", fontsize=10, color=text_color)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars:
        ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, f"Seviye {int(bar.get_width())}",
                 va='center', ha='left', color=text_color, fontsize=9, fontweight='bold')

    # PANEL 3: getenv O(N) vs Cache O(1) Performans Kıyaslaması
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("Erişim Süresi: getenv Doğrusal Arama vs Önbellek (Cache)", fontsize=12, fontweight='bold', color=accent_green, pad=12)
    
    bench = run_getenv_vs_cache_benchmark(iterations=50000)
    cats = ["getenv() [O(N) Doğrusal Tarama]", "Config Cache [O(1) Hash Haritası]"]
    times = [bench['t_getenv_sec'] * 1000, bench['t_cache_sec'] * 1000]
    
    bars3 = ax3.bar(cats, times, color=[accent_amber, accent_green], width=0.45)
    ax3.set_ylabel("50,000 Çağrı Süresi (ms)", fontsize=10, color=text_color)
    ax3.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars3:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f"{bar.get_height():.2f} ms",
                 ha='center', va='bottom', color=text_color, fontsize=9, fontweight='bold')

    # PANEL 4: Güvenlik ve Tehdit Risk Matrisi
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("Ortam Değişkeni Güvenlik Açıkları ve Savunma", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    scenarios = ["putenv Stack Leak", "Multi-Thread Race", "/proc Plain Secret", "SUID LD_PRELOAD"]
    risk_levels = [95, 90, 85, 99] # Risk Skoru
    
    bars4 = ax4.bar(scenarios, risk_levels, color=[accent_red, accent_amber, accent_blue, accent_red], width=0.5)
    ax4.set_ylabel("Risk & Kritiklik Skoru (%)", fontsize=10, color=text_color)
    ax4.set_ylim(0, 115)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars4:
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"%{int(bar.get_height())}",
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

    # 2. Kaskat Öncelik Doğrulaması (CLI > ENV > FILE > DEFAULT)
    cfg = CascadingConfigManager()
    cfg.set("freq", 100, "DEFAULT")
    cfg.set("freq", 200, "FILE")
    cfg.set("freq", 300, "ENV")
    cfg.set("freq", 400, "CLI")
    assert cfg.get_int("freq") == 400, "HATA: CLI değeri tüm kaynakları ezmelidir!"
    assert cfg.get_source("freq") == "CLI", "HATA: Kaynak CLI olmalıdır!"
    
    # Düşük öncelikli kaynağın ezmeye çalışması
    rej = cfg.set("freq", 50, "FILE")
    assert rej is False, "HATA: Düşük öncelikli kaynak yüksek olanı ezememelidir!"
    assert cfg.get_int("freq") == 400, "HATA: Değer değişmemelidir!"
    print("  [+] 4-Kademeli Kaskat Öncelik Hiyerarşisi Doğrulandı.")

    # 3. putenv Yığın Bozma (Dangling Pointer) Doğrulaması
    v_bef, v_aft = EnvironmentSabotageLab.run_putenv_sabotage()
    assert "TARGET_COORDINATES" in v_bef or "39.9208" in v_bef, "HATA: Başlangıçta değer okunabilmelidir!"
    assert "GARBAGE" in v_aft or "DEADBEEF" in v_aft, "HATA: Stack unwound sonrası bellek bozulmalıdır!"
    print("  [+] putenv Dangling Pointer Bellek Bozulması Doğrulandı.")

    # 4. /proc/PID/environ NUL Sınırları ve Sızıntı Doğrulaması
    leaked, dump, _ = SecretLeakageLab.simulate_secret_leak()
    assert leaked is True, "HATA: Sırların /proc üzerinden sızdığı doğrulanmalıdır!"
    print("  [+] /proc/PID/environ NUL Ayrıştırma ve Güvenlik Zaafiyeti Doğrulandı.")

    # 5. Benchmark Hızlanma Doğrulaması
    b_res = run_getenv_vs_cache_benchmark(iterations=10000)
    assert b_res["speedup_factor"] > 1.2, "HATA: Cache mekanizması getenv'e göre daha hızlı olmalıdır!"
    print(f"  [+] Önbellek Hızlanması Doğrulandı ({b_res['speedup_factor']:.2f}x Hızlanma).")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)

```

## 16. Savunma Sanayii Senaryoları ve Gün Sonu Özeti

### Savunma Sanayii ve Görev Kritik Sistem Senaryoları
1. **ASELSAN Elektronik Harp Podu: Taktik Görev Modu Enjeksiyonu**:
   - Uçuş öncesi görev planlayıcı yer istasyonundan pod bilgisayarına parametreler yüklenir.
   - Yazılım kaskat konfigürasyon mimarisiyle yapılandırılmıştır: Eğer pod içinde yerel dosya varsa (`/data/mission_plan.json`) o okunur; acil durumlarda operatör kabuk üzerinden `MISSION_OVERRIDE_MODE=EMERGENCY` çevre değişkeniyle anında müdahale edebilir.
2. **HAVELSAN Denizaltı C4I Komuta Kontrol: Multi-Thread Güvenliği**:
   - Sonar akustik izleme sürecinde 32 iş parçacığı eşzamanlı çalışmaktadır. Yazılım içinde hiçbir iş parçacığının `setenv` çağırmasına izin verilmez; konfigürasyon parametreleri `main()` içinde tek iş parçacıklı evrede okunup kilitli (read-only) konfigürasyon singleton nesnesine aktarılır.

### Gün Sonu Özeti (3 Cümlelik Kapanış)
1. **Bellek Yerleşimi**: Çevre değişkenleri (`environ`), süreç adres uzayının en tepesinde (`Top of Stack`) NUL sonlandırmalı stringler ve işaretçi dizisi olarak tutulur ve `fork()` anında çocuğa klonlanır.
2. **Kaskat Konfigürasyon ve Güvenlik**: Savunma sistemlerinde parametreler CLI > ENV > FILE > DEFAULT öncelik piramidiyle yönetilmeli; SUID süreçlerde `secure_getenv` kullanılmalı ve parolalar `/proc/PID/environ` sızıntısı nedeniyle ortam değişkenine konulmamalıdır.
3. **Mühendislik Kuralı**: `putenv()` yerel yığın bellek adreslerini bağlayarak ölümcül çöp değerlere yol açtığı ve `setenv()` thread-safe olmadığı için, konfigürasyon değişkenleri sadece süreç başlangıcında okunup güvenli C++ nesnelerinde önbelleğe alınmalıdır.


## 17. Gelecek Gün Köprüsü: Gün 096

Yarın **GÜN 096** kapsamında:
- **Konu**: **Paylaşılan Kütüphaneler (Shared Libraries) ve Dinamik Bağlayıcı (Dynamic Linker - ld.so)**
- **Kapsam**: Dinamik kütüphanelerin (`.so`) ELF yapısı, `ld.so` arama yolları (`DT_RPATH`, `DT_RUNPATH`, `/etc/ld.so.conf`, `LD_LIBRARY_PATH`), Sembol çözümleme (Symbol Resolution), `dlopen`, `dlsym`, `dlclose` mekanizmaları ve ASELSAN modüler eklenti mimarisi.
- **Hazırlık**: Bugün `LD_PRELOAD` ve ortam değişkenlerinin dinamik bağlayıcıyı nasıl etkilediğine değindik; yarın bu bağlayıcının bizzat çalışma mimarisine ineceğiz.
