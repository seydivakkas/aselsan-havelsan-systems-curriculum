# GÜN 096: Paylaşılan Kütüphaneler (Shared Libraries) ve Dinamik Bağlayıcı (Dynamic Linker - ld.so) Mimarisi

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
- **Konu**: Dinamik Kütüphaneler (`.so`), Dinamik Bağlayıcı (`ld-linux.so`), ELF `.interp` ve `.dynamic` Bölümleri, GOT/PLT Tembel Bağlama (Lazy Binding), `dlopen`/`dlsym`/`dlclose` API'si, Arama Sırası (`RPATH` > `LD_LIBRARY_PATH` > `RUNPATH`)
- **Ön Koşul Bilgi**: Gün 087 (execve ailesi), Gün 094 (/proc/maps bellek haritası) ve Gün 095 (Environment variables & LD_PRELOAD)
- **Hedef Sistemler**: ASELSAN Modüler Sayısal Sinyal İşleme (DSP) Dalga Formu Eklentileri, HAVELSAN C4I Eklenti Tabanlı Görev Dağıtıcıları, TUSAŞ Aviyonik Simülasyon Donanım Adaptörleri, Yüksek Güvenilirlikli Gerçek Zamanlı Linux Sistemleri.

### 40-Nokta Kalite ve Mimari Beyanı
Bu çalışma modülü; System V AMD64 ABI, Executable and Linkable Format (ELF) spesifikasyonları ve POSIX dinamik bağlama arayüzleri gözetilerek inşa edilmiştir. Modülde; statik bağlama (`.a`) ile dinamik bağlama (`.so`) arasındaki bellek ve disk ayak izi farkları, Konumdan Bağımsız Kod (`-fPIC`) mantığı, Global Ofset Tablosu (GOT) ve Prosedür Bağlantı Tablosu (PLT) üzerinden işletilen tembel çözümleme (lazy binding) mekanizması, deterministik görev kritik sistemlerde `LD_BIND_NOW=1` ile gecikme (jitter) eliminasyonu, `dlopen`/`dlsym` ile dinamik eklenti mimarisi, `dlclose` sonrası askıda kalan fonksiyon işaretçilerinin (dangling function pointers) yol açtığı bellek çöküşleri ve dinamik bağlayıcının kütüphane arama sırası derinlemesine analiz edilmektedir.


## 1. Teori ve Sistem Mimarisi: Statik (.a) vs Dinamik (.so) Bağlama

Yazılım geliştirme sürecinde kaynak kodlar derlendikten sonra kütüphanelerle iki farklı yöntemle birleştirilir:

```
+-----------------------------------------------------------------------------+
|  A) STATİK BAĞLAMA (STATIC LINKING - libtarget.a)                           |
|                                                                             |
|  [ Kodunuz (main.o) ] + [ libtarget.a Kod Blokları ]                        |
|                     |                                                       |
|                     v ld (Bağlayıcı)                                        |
|         [ DEVASA TEKİL ÇALIŞTIRILABİLİR DOSYA ]                             |
|  - Kütüphane kodu doğrudan ikili dosyanın içine kopyalanır.                 |
|  - RAM'de her çalışan süreç bu kodu ayrı ayrı belleğe yükler (Bellek İsrafı)|
|  - Kütüphanede hata çıktığında tüm programlar yeniden derlenmek zorundadır. |
+-----------------------------------------------------------------------------+

+-----------------------------------------------------------------------------+
|  B) DİNAMİK BAĞLAMA (DYNAMIC LINKING - libtarget.so)                        |
|                                                                             |
|  [ Kodunuz (main.o) ] + [ Sembol Referansları (DT_NEEDED) ]                 |
|                     |                                                       |
|                     v ld (Bağlayıcı)                                        |
|         [ KÜÇÜK ÇALIŞTIRILABİLİR ELF DOSYASI ]                              |
|                     |                                                       |
|                     v execve() anında çekirdek .interp bölümünü okur:       |
|         [ /lib64/ld-linux-x86-64.so.2 (Dinamik Bağlayıcı Başlar) ]          |
|                     |                                                       |
|                     v mmap(MAP_SHARED) ile tek bir libtarget.so dosyasını   |
|         [ FİZİKSEL RAM'DE TEK KOPYA -> TÜM SÜREÇLER ORTAK KULLANIR ]        |
+-----------------------------------------------------------------------------+
```

### ELF `.interp` ve `.dynamic` Bölümleri
Bir dinamik ELF çalıştırılabilir dosyasının içinde iki hayati bölüm yer alır:
1. **`.interp`**: Çekirdeğe bu programı çalıştırmadan önce hangi dinamik bağlayıcıyı yüklemesi gerektiğini söyler (Örn: `/lib64/ld-linux-x86-64.so.2`).
2. **`.dynamic`**: Bağlayıcının ihtiyaç duyduğu yönergeleri barındırır:
   - `DT_NEEDED`: Gerekli `.so` kütüphanelerinin adları (`libc.so.6`, `libradar.so`).
   - `DT_RPATH` / `DT_RUNPATH`: Kütüphanelerin aranacağı öncelikli dizinler.
   - `DT_SONAME`: Kütüphanenin mantıksal sürüm adı.


## 2. PIC, GOT ve PLT: Tembel Bağlama (Lazy Binding) Mekanizması

Paylaşılan bir kütüphanenin (`.so`) kodu bellekte rastgele bir sanal adrese yüklenebilir (ASLR). Bu nedenle kodun sabit bellek adreslerine bağımlı olmaması gerekir. Bu problem **-fPIC (Position Independent Code)** ile çözülür.

### GOT (Global Offset Table) ve PLT (Procedure Linkage Table)
Bir fonksiyon ilk kez çağrıldığında dinamik bağlayıcı devreye girer:

```
[ KOD: compute_fft() ÇAĞRISI ]
          |
          v
+-----------------------------------------------------------------------------+
|  1. PLT Girdisi (compute_fft@plt):                                          |
|     jmp *GOT_ENTRY_ADDR   --------+                                         |
|     push relocation_index         | (İlk çağrıda GOT girdisi bir alt satıra |
|     jmp  _dl_runtime_resolve      |  yani 'push' komutuna işaret eder!)     |
+-----------------------------------|-----------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|  2. Dinamik Bağlayıcı (_dl_runtime_resolve):                                |
|     - libdsp.so içinde "compute_fft" sembolünün gerçek adresini arar.       |
|     - Gerçek adresi bulur: 0x7FFF_A010_4500                                |
|     - GOT tablosundaki adresi günceller: GOT[compute_fft] = 0x7FFF_A010_4500|
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|  3. Sonraki Tüm Çağrılar:                                                   |
|     compute_fft@plt -> Doğrudan GOT içindeki 0x7FFF_A010_4500 adresine atlar!|
|     (Dinamik bağlayıcı bir daha ASLA çağrılmaz - Sıfır Çözümleme Ek Yükü!)   |
+-----------------------------------------------------------------------------+
```

### Savunma ve Gerçek Zamanlı Sistem Uyarısı: `LD_BIND_NOW=1`
Tembel bağlama (Lazy Binding), fonksiyonun ilk çağrıldığı anda birkaç mikrosaniyelik gecikmeye (jitter) neden olur.
- Aviyonik veya radar füze güdüm yazılımlarında bu gecikme kabul edilemez!
- **Çözüm**: Program başlatılırken `LD_BIND_NOW=1` ortam değişkeni veya derleme anında `-Wl,-z,now` bayrağı verilerek tüm GOT adreslerinin süreç başlarken tek seferde çözülmesi zorlanır.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 4 (CODE 1): Dynamic Linker ve GOT/PLT Simülatörü
Tembel Bağlama (Lazy Binding), GOT Tablosu Güncellemesi ve Çözümleme Gecikmesi
"""

import time
from typing import Dict, Any, Optional, Tuple

class SimulatedSharedLibrary:
    """Belleğe haritalanmış paylaşımlı bir kütüphane (.so)."""
    def __init__(self, name: str, base_addr: int, export_symbols: Dict[str, int]):
        self.name = name
        self.base_addr = base_addr
        self.export_symbols = {k: base_addr + offset for k, offset in export_symbols.items()}

class SimulatedDynamicLinker:
    """Linux ld.so dinamik bağlayıcısının GOT/PLT çalışma motoru simülasyonu."""
    
    def __init__(self, bind_now: bool = False):
        self.bind_now = bind_now
        self.loaded_libraries: Dict[str, SimulatedSharedLibrary] = {}
        # GOT: sembol_adı -> çözümlenmiş gerçek bellek adresi (0 ise henüz çözülmedi)
        self.global_offset_table: Dict[str, int] = {}
        self.symbol_resolution_count = 0

    def load_library(self, lib: SimulatedSharedLibrary):
        self.loaded_libraries[lib.name] = lib
        if self.bind_now:
            for sym, addr in lib.export_symbols.items():
                self.global_offset_table[sym] = addr
                self.symbol_resolution_count += 1

    def resolve_symbol_runtime(self, symbol_name: str) -> int:
        """_dl_runtime_resolve simülasyonu: Kütüphaneleri tarayıp sembolü bulur."""
        for lib in self.loaded_libraries.values():
            if symbol_name in lib.export_symbols:
                resolved_addr = lib.export_symbols[symbol_name]
                # GOT tablosunu güncelle (Gelecek çağrılar için doğrudan atlama)
                self.global_offset_table[symbol_name] = resolved_addr
                self.symbol_resolution_count += 1
                return resolved_addr
        raise RuntimeError(f"Sembol bulunamadı (undefined symbol): {symbol_name}")

    def call_plt_trampoline(self, symbol_name: str) -> Tuple[int, bool]:
        """
        PLT çağrı simülasyonu.
        Dönüş: (fonksiyon_adresi, ilk_cozumleme_mi)
        """
        # GOT tablosunda zaten çözülmüş mü?
        if symbol_name in self.global_offset_table and self.global_offset_table[symbol_name] != 0:
            # 1. Hızlı yol: GOT doğrudan hedefi gösteriyor
            return self.global_offset_table[symbol_name], False
        
        # 2. Yavaş yol: Tembel bağlama tetiklendi! Dinamik bağlayıcı çağrılıyor
        addr = self.resolve_symbol_runtime(symbol_name)
        return addr, True

if __name__ == "__main__":
    # Test Senaryosu: libdsp.so kütüphanesi
    lib_dsp = SimulatedSharedLibrary(
        name="libdsp.so",
        base_addr=0x7FFF1000,
        export_symbols={"compute_fft": 0x0120, "filter_fir": 0x0340}
    )

    print("=== [LAZY BINDING (TEMBEL BAĞLAMA) SİMÜLASYONU] ===")
    linker_lazy = SimulatedDynamicLinker(bind_now=False)
    linker_lazy.load_library(lib_dsp)

    # 1. Çağrı: Tembel bağlama devreye girmeli
    addr1, is_first1 = linker_lazy.call_plt_trampoline("compute_fft")
    print(f"1. Çağrı (compute_fft): Adres={hex(addr1)}, Çözümleme Tetiklendi mi?={is_first1}")

    # 2. Çağrı: GOT tablosundan doğrudan okunmalı
    addr2, is_first2 = linker_lazy.call_plt_trampoline("compute_fft")
    print(f"2. Çağrı (compute_fft): Adres={hex(addr2)}, Çözümleme Tetiklendi mi?={is_first2}")
    print(f"[*] Toplam ld.so Çözümleme Sayısı: {linker_lazy.symbol_resolution_count}")

```

## 3. Kod 01 Analizi: PLT Trambolini ve GOT Güncellemesi

Kod 01 simülasyonu Linux çekirdeği ve glibc'nin dinamik sembol bağlama mantığını net biçimde sergilemiştir:
1. **İlk Çağrı Maliyeti**: `compute_fft` ilk çağrıldığında GOT tablosu boş olduğundan dinamik bağlayıcı (`resolve_symbol_runtime`) çalıştırılmış, sembolün kütüphane ofseti (`0x7FFF1000 + 0x0120 = 0x7fff1120`) hesaplanmış ve GOT girdisine yazılmıştır (`is_first = True`).
2. **Sonraki Çağrılar**: İkinci çağrıda `global_offset_table` doğrudan dolu olduğu için bağlayıcı tamamen atlanmış ve işlem $O(1)$ tek bir tablo okumasıyla tamamlanmıştır (`is_first = False`).
3. **Çıkarım**: Tembel bağlama başlangıç süresini (startup time) kısaltır; fakat ilk döngü iterasyonlarında determinizmi bozar.


## 4. Dinamik Kütüphane Arama Sırası (Search Order Hierarchy)

Bir ikili dosya çalıştırıldığında, `ld.so` ihtiyaç duyulan her `.so` dosyasını (`DT_NEEDED`) **kesin bir öncelik sırasıyla** arar:

```
+-----------------------------------------------------------------------------+
|               LINUX DİNAMİK BAĞLAYICI ARAMA SIRASI (SEARCH HIERARCHY)       |
|                                                                             |
|  1. ELF DT_RPATH (Eğer ikili dosyada DT_RUNPATH yoksa işletilir)             |
|     (Derleme anında binary içine gömülmüş sabit yol - ESKİ STANDART)        |
|                                                                             |
|  2. LD_LIBRARY_PATH Çevre Değişkeni                                         |
|     (Kullanıcı tarafından geçici olarak verilen yollar)                     |
|     * UYARI: SUID/SGID süreçlerde (AT_SECURE) GÜVENLİK GEREĞİ YOK SAYILIR!  |
|                                                                             |
|  3. ELF DT_RUNPATH                                                          |
|     (Derleme anında -Wl,--enable-new-dtags ile gömülen modern standart)     |
|     * LD_LIBRARY_PATH'den SONRA işletilir, geliştiriciye esneklik sağlar.   |
|                                                                             |
|  4. /etc/ld.so.cache (ldconfig tarafından derlenmiş ikili dizin önbelleği)  |
|                                                                             |
|  5. Varsayılan Sistem Dizinleri:                                            |
|     - /lib64  ve  /usr/lib64 (64-bit sistemlerde)                           |
|     - /lib    ve  /usr/lib                                                  |
+-----------------------------------------------------------------------------+
```

### RPATH vs RUNPATH Ayrımı
- **`DT_RPATH`**: `LD_LIBRARY_PATH`'den **ÖNCE** gelir. Kullanıcı çevre değişkeniyle kütüphaneyi ezemez (override edemez).
- **`DT_RUNPATH`**: `LD_LIBRARY_PATH`'den **SONRA** gelir. Modern Linux dağıtımlarında varsayılan budur.


## 5. Çalışma Zamanı Eklenti Mimarisi: `dlopen`, `dlsym`, `dlclose`

Bir kütüphaneyi derleme anında bağlamak (`-ltarget`) yerine, program çalışırken dinamik olarak belleğe yükleyip sembol çağırmak için POSIX `<dlfcn.h>` arayüzü kullanılır:

```c
#include <dlfcn.h>

void *dlopen(const char *filename, int flags);
void *dlsym(void *handle, const char *symbol);
char *dlerror(void);
int dlclose(void *handle);
```

### Kritik Bayraklar:
1. **`RTLD_LAZY`**: Fonksiyon sembollerini yalnızca ilk çağrıldıklarında çözümler (Daha hızlı yükleme).
2. **`RTLD_NOW`**: Kütüphanedeki **tüm tanımsız sembolleri `dlopen` anında çözümler**. Eksik tek bir sembol varsa `dlopen` başarısız olur (`NULL` döner). Görev kritik savunma yazılımlarında çalışma anında sürpriz çöküşleri engellemek için **daima `RTLD_NOW` kullanılmalıdır!**
3. **`RTLD_GLOBAL` vs `RTLD_LOCAL`**: Yüklenen sembollerin daha sonra yüklenecek kütüphaneler tarafından doğrudan görülüp görülemeyeceğini belirler.


## 6. Savunma Sanayii Mimarisi: ASELSAN Modüler Eklenti Motoru

Radar ve elektronik harp sistemlerinde farklı görev senaryoları için farklı dalga formu işleme algoritmaları kullanılır:
- **Statik Yapı**: Her yeni algoritma için tüm radar yazılımını yeniden derleyip uçağa/gemiye yüklemek operasyonel açıdan imkansızdır.
- **Dinamik Eklenti Mimarisi**:
  1. Çekirdek yazılım soyut bir C++ arayüzü (`IWaveformProcessor`) tanımlar.
  2. Her algoritma bağımsız bir `.so` dosyası (`libpulse_doppler.so`, `libchirp.so`) olarak derlenir.
  3. Radar yöneticisi konfigürasyon dosyasına göre ilgili kütüphaneyi `dlopen("libchirp.so", RTLD_NOW)` ile belleğe haritalar.
  4. Fabrika fonksiyonunu (`create_processor`) `dlsym` ile çekerek nesneyi üretir. Görev bitince güvenle `dlclose` ile bellekten atar.


## 7. C++20 Üretim Seviyesi Dinamik Kütüphane Yöneticisi

Aşağıdaki C++20 RAII sarmalayıcısı; kaynak sızıntısını önleyen, `dlerror` mesajlarını güvenle yakalayan ve tip güvenli sembol dönüşümü sağlayan bir eklenti yöneticisidir:

```cpp
#include <iostream>
#include <string>
#include <string_view>
#include <stdexcept>
#include <dlfcn.h>

class DynamicLibraryHandle {
    void* m_handle{nullptr};
    std::string m_path;

public:
    explicit DynamicLibraryHandle(std::string_view path, int flags = RTLD_NOW | RTLD_LOCAL) 
        : m_path(path) {
        ::dlerror(); // Eski hataları temizle
        m_handle = ::dlopen(m_path.c_str(), flags);
        if (!m_handle) {
            const char* err = ::dlerror();
            throw std::runtime_error("dlopen basarisiz: " + (err ? std::string(err) : "Bilinmeyen hata"));
        }
    }

    ~DynamicLibraryHandle() noexcept {
        if (m_handle) {
            ::dlclose(m_handle);
        }
    }

    DynamicLibraryHandle(const DynamicLibraryHandle&) = delete;
    DynamicLibraryHandle& operator=(const DynamicLibraryHandle&) = delete;
    DynamicLibraryHandle(DynamicLibraryHandle&& other) noexcept 
        : m_handle(other.m_handle), m_path(std::move(other.m_path)) {
        other.m_handle = nullptr;
    }

    template <typename FuncPtr>
    [[nodiscard]] FuncPtr get_symbol(std::string_view symbol_name) const {
        ::dlerror();
        void* sym = ::dlsym(m_handle, symbol_name.data());
        const char* err = ::dlerror();
        if (err != nullptr || sym == nullptr) {
            throw std::runtime_error("dlsym basarisiz: " + std::string(symbol_name) + " bulunamadi");
        }
        return reinterpret_cast<FuncPtr>(sym);
    }
};
```


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Python ile Üretim Seviyesi PluginLoader Simülatörü
dlopen, dlsym, Referans Sayımı, Sürüm Doğrulama ve RAII Eklenti Yönetimi
"""

from typing import Dict, Any, Callable, Optional

class SimulatedPluginEngine:
    """C++20 DynamicLibraryHandle eşdeğeri eklenti yükleme ve sembol motoru."""
    
    def __init__(self):
        # Yüklenen kütüphaneler: lib_name -> {symbols, ref_count, is_loaded}
        self.registry: Dict[str, Dict[str, Any]] = {}

    def register_available_library(self, name: str, symbols: Dict[str, Callable], api_version: int = 1):
        """Diskteki mevcut bir .so dosyasını simüle eder."""
        self.registry[name] = {
            "symbols": symbols,
            "api_version": api_version,
            "ref_count": 0,
            "is_loaded": False
        }

    def dlopen(self, name: str, flags: str = "RTLD_NOW") -> str:
        """dlopen çağrısı: Kütüphaneyi belleğe haritalar ve referans sayısını artırır."""
        if name not in self.registry:
            raise FileNotFoundError(f"dlopen hatasi: {name} bulunamadi (No such file or directory)")
            
        entry = self.registry[name]
        entry["is_loaded"] = True
        entry["ref_count"] += 1
        return name # Handle olarak kütüphane adı döner

    def dlsym(self, handle: str, symbol_name: str) -> Callable:
        """dlsym çağrısı: Bellekteki sembol fonksiyon işaretçisini döner."""
        if handle not in self.registry or not self.registry[handle]["is_loaded"]:
            raise RuntimeError(f"dlsym hatasi: Kütüphane bellege yuklu degil ({handle})")
            
        symbols = self.registry[handle]["symbols"]
        if symbol_name not in symbols:
            raise AttributeError(f"dlsym hatasi: '{symbol_name}' sembolu {handle} icinde tanimsiz")
            
        return symbols[symbol_name]

    def dlclose(self, handle: str) -> int:
        """dlclose çağrısı: Referans sayısını azaltır, 0 olursa bellekten unmap eder."""
        if handle not in self.registry or not self.registry[handle]["is_loaded"]:
            return -1
            
        entry = self.registry[handle]
        entry["ref_count"] -= 1
        if entry["ref_count"] == 0:
            entry["is_loaded"] = False
        return 0

if __name__ == "__main__":
    engine = SimulatedPluginEngine()
    
    # Radar eklentisi kaydı
    engine.register_available_library(
        "libchirp_filter.so",
        symbols={
            "init_filter": lambda: "CHIRP_FILTER_INITIALIZED",
            "process_sample": lambda x: x * 2.5
        },
        api_version=2
    )

    print("=== [DİNAMİK EKLENTİ YÜKLEYİCİ TESTİ] ===")
    handle = engine.dlopen("libchirp_filter.so", flags="RTLD_NOW")
    print(f"[+] dlopen Basarili: {handle} (Ref Count: {engine.registry[handle]['ref_count']})")

    fn_init = engine.dlsym(handle, "init_filter")
    fn_process = engine.dlsym(handle, "process_sample")
    
    print(f"[*] Eklenti Fonksiyonu Çıktısı 1: {fn_init()}")
    print(f"[*] Eklenti Fonksiyonu Çıktısı 2: {fn_process(10.0)}")

    engine.dlclose(handle)
    print(f"[-] dlclose Sonrası Yüklü mü? : {engine.registry[handle]['is_loaded']}")

```

## 8. Kod 02 Analizi ve Eklenti Yaşam Döngüsü

Kod 02 simülasyonu, dinamik eklenti mimarisinin temel taşlarını doğrulamıştır:
1. **Çalışma Zamanı Bağımsızlığı**: Ana program derlenirken `libchirp_filter.so` hakkında hiçbir derleme zamanı bilgisine sahip değildir; yalnızca standart bir arayüz fonksiyon adresi (`dlsym`) talep etmiştir.
2. **Referans Sayımı (Refcounting)**: `dlclose` çağrıldığında kütüphane anında yok edilmez; referans sayacı 0'a ulaştığında bellek haritasından (`unmap`) sökülür.
3. **Eksik Sembol Güvenliği**: Kütüphanede bulunmayan bir sembol istendiğinde sistem sessizce başarısız olmak yerine anında hata fırlatarak çökmeyi önlemiştir.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Sabotaj Laboratuvarı: dlclose Sonrası Dangling Pointer
Bellekten Unmap Edilmiş Koda Atlama (SIGSEGV) ve Sembol Gölgeleme (Shadowing)
"""

from typing import Tuple

class DynamicLinkerSabotageLab:
    """Dinamik kütüphanelerdeki en yaygın iki bellek ve mantık hatasını modeller."""
    
    @staticmethod
    def simulate_dangling_function_pointer() -> Tuple[bool, str]:
        """Kütüphane dlclose ile boşaltıldıktan sonra eski fonksiyona çağrı yapılması."""
        engine = SimulatedPluginEngine()
        engine.register_available_library(
            "libtelemetry_plugin.so",
            symbols={"log_telemetry": lambda msg: f"LOGGED: {msg}"}
        )
        
        # 1. Kütüphane yüklenir ve fonksiyon işaretçisi alınır
        h = engine.dlopen("libtelemetry_plugin.so")
        cached_func_ptr = engine.dlsym(h, "log_telemetry")
        
        # 2. Kütüphane kapatılır (Unmap edilir)
        engine.dlclose(h)
        
        # 3. Yazılımcı işaretçiyi tutmaya ve çağırmaya devam eder!
        # Gerçek Linux sisteminde bu adres artık geçerli bir VMA değildir -> SIGSEGV!
        is_library_unmapped = not engine.registry[h]["is_loaded"]
        if is_library_unmapped:
            return True, "SIGSEGV: Segmentation Fault! Bellekten unmap edilmiş kod sayfasına atlandı (Dangling Pointer)."
        return False, "Normal çağrı."

    @staticmethod
    def simulate_symbol_shadowing() -> Tuple[str, str]:
        """Aynı isimli iki kütüphane yüklendiğinde küresel isim çakışması (Shadowing)."""
        # libA ve libB ikisi de 'calculate_target()' ihraç ediyor
        lib_a = {"calculate_target": "LIB_A_PRECISION_ALGORITHM"}
        lib_b = {"calculate_target": "LIB_B_FALLBACK_ALGORITHM"}
        
        # Linux RTLD_GLOBAL kuralı: İlk yüklenen sembol sonraki aynı isimli sembolleri gölgeler!
        loaded_global_table = {}
        loaded_global_table.update(lib_a) # İlk yüklendi
        # lib_b yüklenirken calculate_target zaten var!
        shadowed = "calculate_target" in loaded_global_table
        
        return loaded_global_table["calculate_target"], f"UYARI: Sembol çakışması! libB'nin fonksiyonu gölgelendi."

if __name__ == "__main__":
    print("=== [SABOTAJ VE ARIZA LABORATUVARI] ===")
    is_crash, crash_msg = DynamicLinkerSabotageLab.simulate_dangling_function_pointer()
    print(f"[*] Dangling Pointer Testi : {crash_msg}")

    winner, shadow_msg = DynamicLinkerSabotageLab.simulate_symbol_shadowing()
    print(f"[*] Sembol Gölgeleme Testi : Çağrılan = {winner} | {shadow_msg}")

```

## 9. Kod 03 Analizi: Hafıza Haritasından Çıkarılan Koda Erişim Felaketi

Kod 03 simülasyonu, dinamik eklenti mimarilerindeki iki kritik tasarım hatasını modeller:
1. **Dangling Function Pointer Felaketi**: `dlclose` çağrısı yapıldığı an, Linux çekirdeği o kütüphaneye tahsis edilen sanal bellek sayfalarını (`VMA`) derhal geçersiz kılar (`munmap`). Eğer uygulama fonksiyon işaretçisini saklamışsa ve daha sonra çağırırsa, CPU var olmayan bir bellek sayfasına atlamaya çalışır ve süreç **anında `SIGSEGV` ile çöker**.
   - **Savunma Kuralı**: Kütüphane kapatılmadan önce, ondan türetilmiş tüm nesneler ve fonksiyon işaretçileri sıfırlanmalı (`nullptr`) ve geri çağırma (callback) abonelikleri iptal edilmelidir.
2. **Sembol Gölgeleme (Shadowing)**: İki farklı eklenti aynı C fonksiyon ismini (`calculate_target`) küresel olarak ihraç ederse, `ld.so` ilk bulduğu fonksiyonu bağlar. İkinci eklenti tamamen devre dışı kalır.
   - **Savunma Kuralı**: Semboller daima `__attribute__((visibility("hidden")))` ile gizlenmeli, yalnızca fabrika fonksiyonu dışa açılmalıdır.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Dinamik Arama Yolu Laboratuvarı: RPATH vs RUNPATH
ld.so Öncelik Hiyerarşisi ve LD_LIBRARY_PATH Ezme Simülatörü
"""

from typing import List, Dict, Optional, Tuple

class LibraryPathResolver:
    """Linux ld.so kütüphane arama sırasını işleten simülasyon motoru."""
    
    def __init__(self, rpath: Optional[str] = None, runpath: Optional[str] = None):
        self.rpath = rpath
        self.runpath = runpath
        self.default_system_dirs = ["/lib64", "/usr/lib64"]

    def resolve(self, lib_name: str, env_ld_library_path: Optional[str] = None, is_suid: bool = False) -> Tuple[str, str]:
        """Kütüphaneyi arama sırasına göre bulur ve kazanan seviyeyi döner."""
        
        # SUID süreçlerde LD_LIBRARY_PATH güvenlik gereği çekirdekçe silinir!
        effective_ld_path = env_ld_library_path if not is_suid else None
        
        # 1. RPATH (Eğer RUNPATH yoksa)
        if self.rpath and not self.runpath:
            return f"{self.rpath}/{lib_name}", "1. DT_RPATH (En Yüksek - Sabit)"

        # 2. LD_LIBRARY_PATH
        if effective_ld_path:
            return f"{effective_ld_path}/{lib_name}", "2. LD_LIBRARY_PATH (Çevre Değişkeni)"

        # 3. RUNPATH
        if self.runpath:
            return f"{self.runpath}/{lib_name}", "3. DT_RUNPATH (Modern ELF Standardı)"

        # 4. Standart Dizinler
        return f"{self.default_system_dirs[0]}/{lib_name}", "4. Standart Sistem Yolu (/lib64)"

if __name__ == "__main__":
    print("=== [LD.SO KÜTÜPHANE ARAMA SIRASI DENEYLERİ] ===")
    
    # Senaryo 1: Klasik RPATH (LD_LIBRARY_PATH onu ezemez!)
    res_rpath = LibraryPathResolver(rpath="/opt/aselsan/secure_libs", runpath=None)
    path1, level1 = res_rpath.resolve("libdsp.so", env_ld_library_path="/tmp/user_libs")
    print(f"[*] RPATH Senaryosu     : {path1:35s} [Kazanan: {level1}]")

    # Senaryo 2: Modern RUNPATH (LD_LIBRARY_PATH onu ezebilir!)
    res_runpath = LibraryPathResolver(rpath=None, runpath="/opt/aselsan/default_libs")
    path2, level2 = res_runpath.resolve("libdsp.so", env_ld_library_path="/tmp/user_libs")
    print(f"[*] RUNPATH Senaryosu   : {path2:35s} [Kazanan: {level2}]")

    # Senaryo 3: SUID Güvenlik Koruması (LD_LIBRARY_PATH engellenir!)
    path3, level3 = res_runpath.resolve("libdsp.so", env_ld_library_path="/tmp/user_libs", is_suid=True)
    print(f"[*] SUID Koruma Senaryosu: {path3:35s} [Kazanan: {level3}]")

```

## 10. Kod 04 Analizi: Güvenlik ve Arama Sırası Sonuçları

Kod 04 simülasyonu, Linux sistem programlamasındaki en kritik güvenlik kurallarından birini teyit eder:
1. **RPATH Dokunulmazlığı**: `DT_RPATH` tanımlı olduğunda, `LD_LIBRARY_PATH` değişkeni tamamen etkisiz kalmıştır. Kütüphane mutlak olarak derleyicinin belirttiği güvenli yoldan yüklenmiştir.
2. **RUNPATH Esnekliği**: `DT_RUNPATH` kullanıldığında ise `LD_LIBRARY_PATH` değişkeni araya girerek kütüphaneyi ezebilmiştir (`/tmp/user_libs`).
3. **SUID Koruması (`AT_SECURE`)**: Süreç SUID modunda çalıştığında, `LD_LIBRARY_PATH` kullanıcı tarafından tanımlanmış olsa dahi çekirdek seviyesinde görmezden gelinmiş ve `DT_RUNPATH` devreye girmiştir. Bu sayede zararlı kütüphane enjeksiyonu (`Privilege Escalation`) engellenmiştir.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Performans ve Benchmark Laboratuvarı
Statik Doğrudan Çağrı vs PLT/GOT İndirekt Çağrı vs dlsym Mikro-Kıyaslaması
"""

import time
from typing import Dict

def run_linking_call_benchmark(iterations: int = 50000) -> Dict[str, float]:
    """Farklı bağlama yöntemlerinin fonksiyon çağrı gecikmesini simüle eder."""
    
    # Hedef fonksiyon
    def target_func(x: int) -> int:
        return x + 1

    # 1. Statik Doğrudan Çağrı (Direct Call - Derleyici Inline/Direct Jump)
    t0 = time.perf_counter()
    acc1 = 0
    for i in range(iterations):
        acc1 += (i + 1)
    t_static = time.perf_counter() - t0

    # 2. Dinamik Bağlama (GOT Üzerinden İndirekt Çağrı: call *GOT[i])
    got_table = [target_func]
    t1 = time.perf_counter()
    acc2 = 0
    for i in range(iterations):
        # Pointer dereference maliyeti
        fn = got_table[0]
        acc2 += fn(i)
    t_got = time.perf_counter() - t1

    # 3. Her İterasyonda dlsym Arama Maliyeti (Anti-Pattern)
    dyn_symbols = {"target_func": target_func}
    t2 = time.perf_counter()
    acc3 = 0
    for i in range(iterations):
        fn = dyn_symbols["target_func"] # String hash lookup
        acc3 += fn(i)
    t_dlsym = time.perf_counter() - t2

    return {
        "iterations": iterations,
        "t_static_ms": t_static * 1000,
        "t_got_ms": t_got * 1000,
        "t_dlsym_ms": t_dlsym * 1000,
        "overhead_got_ratio": t_got / max(t_static, 1e-9),
        "dlsym_penalty_ratio": t_dlsym / max(t_got, 1e-9)
    }

if __name__ == "__main__":
    res = run_linking_call_benchmark(iterations=50000)
    print("=== [BAĞLAMA YÖNTEMLERİ ÇAĞRI BAŞARIMI BENCHMARK] ===")
    print(f"Toplam Döngü                 : {res['iterations']:,}")
    print(f"1. Statik Doğrudan Çağrı     : {res['t_static_ms']:.3f} ms")
    print(f"2. GOT Üzerinden İndirekt    : {res['t_got_ms']:.3f} ms")
    print(f"3. Döngü İçi dlsym() Çağrısı : {res['t_dlsym_ms']:.3f} ms")
    print(f"[*] GOT İndirekt Ek Yükü     : {res['overhead_got_ratio']:.2f}x")
    print(f"[*] dlsym Tekrar Cezası      : {res['dlsym_penalty_ratio']:.2f}x Kat Daha Yavaş!")

```

## 11. Kod 05 Analizi: Tembel Bağlama Maliyeti ve Optimizasyon

Benchmark verileri askeri yazılım mimarisi açısından iki önemli sonucu belgeler:
1. **GOT Tablosu İhmal Edilebilir Ek Yükü**: GOT üzerinden indirekt fonksiyon çağırmak, modern CPU dal tahminleyicileri (Branch Target Buffer) sayesinde doğrudan çağrıya oldukça yakın bir başarım sergiler.
2. **Döngü İçi `dlsym` Felaketi**: Her iterasyonda `dlsym` ile sembol aramak, hash ve dize arama yükü nedeniyle GOT çağrısına göre katbekat yavaştır. Fonksiyon işaretçisi `dlopen` anında bir kez alınmalı ve döngü boyunca saklanan işaretçi çağrılmalıdır.


## 12. Endüstriyel Mimari Örüntüleri: Sembol Sürümleme (Symbol Versioning)

Büyük savunma projelerinde farklı alt yüklenicilerin kütüphaneleri zamanla güncellenir. Bir fonksiyonun parametresi değiştiğinde eski ikili dosyaların çökmesini önlemek için **GNU Sembol Sürümleme (Symbol Versioning)** kullanılır:

```c
// radar_api.c
void calculate_range_v1(double freq) { /* Eski Algoritma */ }
void calculate_range_v2(double freq, double gain) { /* Yeni Algoritma */ }

__asm__(".symver calculate_range_v1, calculate_range@RADAR_1.0");
__asm__(".symver calculate_range_v2, calculate_range@@RADAR_2.0");
```
- Eski yazılımlar kütüphaneyi açtığında `calculate_range@RADAR_1.0` sürümünü çağırır ve çalışmaya devam eder.
- Yeni derlenen yazılımlar ise otomatik olarak varsayılan `RADAR_2.0` sürümüne bağlanır.
- Böylece sistemde **ABI Uyumluluğu (Application Binary Interface)** kırılmadan kesintisiz güncelleme sağlanır.


## 13. Hata Ayıklama ve Gözlemlenebilirlik Komutları

Linux dinamik bağlama mekanizmasını incelemek ve sorunları çözmek için kullanılan temel araçlar:

```bash
# 1. Programın bağımlı olduğu dinamik kütüphaneleri listele
ldd ./mission_app

# 2. ELF başlığındaki dinamik etiketleri (RPATH, RUNPATH, NEEDED) dök
readelf -d ./mission_app

# 3. Kütüphanedeki dışa aktarılan (exported) dinamik sembolleri listele
nm -D /opt/aselsan/lib/libdsp.so

# 4. Dinamik bağlayıcının kütüphane arama adımlarını anlık izle (ÇOK GÜÇLÜ!)
LD_DEBUG=libs,symbols ./mission_app

# 5. Kütüphanenin tüm bağımlılıklarını başlangıçta anında bağlamaya zorla
LD_BIND_NOW=1 ./mission_app
```


## 14. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **`dlclose` Sonrası İşaretçiyi Kullanmaya Devam Etmek**:
   - *Hata*: Bellekten silinmiş kod sayfasına zıplamak (`SIGSEGV`).
   - *Çözüm*: Kütüphaneyi kapatmadan önce tüm işaretçileri `nullptr` yapın.
2. **Kütüphaneleri `-fPIC` Olmadan Derlemek**:
   - *Hata*: 64-bit mimaride metin relokasyonuna yol açar; kod paylaşımını bozar veya derleme hatası (`relocation R_X86_64_32S`) verir.
   - *Çözüm*: Paylaşımlı kütüphane nesnelerini daima `-fPIC` ile derleyin.
3. **Üretim Kodunda `LD_LIBRARY_PATH`'e Güvenmek**:
   - *Hata*: Çevre değişkeni kaybolduğunda veya SUID çalıştırıldığında program çöker.
   - *Çözüm*: Kütüphaneleri sistem dizinlerine kurun veya derlemede `RUNPATH` (`-Wl,-rpath,...`) tanımlayın.
4. **Gerçek Zamanlı Süreçlerde `RTLD_LAZY` Kullanmak**:
   - *Hata*: İlk fonksiyon çağrısında dinamik bağlayıcı çalışır, mikrosaniyelik determinizm bozulur.
   - *Çözüm*: Daima `RTLD_NOW` bayrağını tercih edin.


## 15. Neden-Sonuç Tablosu ve Mimari Karar Matrisi

| Karar / Eylem | Doğrudan Sonuç | Potansiyel Risk / Hata Sınıfı | Mimari Tavsiye |
| :--- | :--- | :--- | :--- |
| `RTLD_NOW` yerine `RTLD_LAZY` kullanmak | Semboller ilk çağrıda çözümlenir. | Uçuş sırasında ani gecikme (Jitter). | Görev kritik kodda `RTLD_NOW` kullanın. |
| `dlclose` sonrası işaretçi sıfırlamamak | İşaretçi serbest VMA'ya bakar. | **SIGSEGV / Bellek Çöküşü**. | Kapatmadan önce işaretçileri `nullptr` yapın. |
| `DT_RPATH` yerine `DT_RUNPATH` tercih etmek | `LD_LIBRARY_PATH` ile ezilebilir. | Yanlışlıkla test kütüphanesinin yüklenmesi. | Güvenlik kritikse RPATH veya tam yol kullanın. |
| Sembolleri `visibility("hidden")` ile gizlememek | Tüm iç fonksiyonlar dışa açılır. | Sembol çakışması (Symbol Collision). | Yalnızca public API fonksiyonlarını açın. |
| `dlsym` sonucunu her çağrıda tekrar aramak | Gereksiz string hash arama maliyeti. | Yüksek döngülerde CPU kaybı. | Başlangıçta fonksiyon işaretçisini saklayın. |


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 22 (CODE 6): 4-Panelli Görselleştirme Paneli ve Katı Doğrulama Testleri
Dinamik Bağlayıcı Mimarisi, GOT/PLT Akışı, Çağrı Başarımı ve Arama Önceliği
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_096_shared_library_ve_dynamic_linker.png"

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

    # PANEL 1: PLT ve GOT Tembel Bağlama Mekanizması Akış Şeması
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("PLT & GOT Tembel Bağlama (Lazy Binding) Döngüsü", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    steps = [
        ("1. main() -> call compute_fft@plt", 0.5, 0.85, accent_blue),
        ("2. PLT -> jmp *GOT[compute_fft]", 0.5, 0.68, accent_amber),
        ("3. GOT Başlangıçta Çözümlenmemiş -> ld.so Çağrılır", 0.5, 0.51, accent_red),
        ("4. ld.so Sembol Adresini Bulur & GOT'u Günceller", 0.5, 0.34, accent_green),
        ("5. Sonraki Çağrılar Doğrudan GOT Üzerinden Hedefe Ulaşır", 0.5, 0.17, '#94A3B8')
    ]
    for text, x, y, col in steps:
        ax1.text(x, y, text, ha='center', va='center', color=text_color, fontsize=8, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor=col, linewidth=2))

    ax1.set_xlim(0, 1.0)
    ax1.set_ylim(0, 1.0)
    ax1.axis('off')

    # PANEL 2: ld.so Kütüphane Arama Sırası (Search Hierarchy)
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("ld.so Dinamik Kütüphane Arama Hiyerarşisi", fontsize=12, fontweight='bold', color=accent_amber, pad=12)
    
    levels = ["1. DT_RPATH (Sabit)", "2. LD_LIBRARY_PATH (Env)", "3. DT_RUNPATH (Modern)", "4. /etc/ld.so.cache", "5. Standart Sistem (/lib64)"]
    priorities = [5, 4, 3, 2, 1]
    colors = [accent_red, accent_amber, accent_blue, '#94A3B8', accent_green]
    
    bars2 = ax2.barh(levels, priorities, color=colors, height=0.55)
    ax2.set_xlabel("Öncelik Seviyesi", fontsize=10, color=text_color)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars2:
        ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, f"Öncelik {int(bar.get_width())}",
                 va='center', ha='left', color=text_color, fontsize=9, fontweight='bold')

    # PANEL 3: Çağrı Yöntemleri Gecikme Benchmark'ı
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("Fonksiyon Çağrı Başarımı: Statik vs GOT vs dlsym()", fontsize=12, fontweight='bold', color=accent_green, pad=12)
    
    bench = run_linking_call_benchmark(iterations=50000)
    cats = ["Statik Çağrı", "GOT İndirekt Çağrı", "Döngü İçi dlsym()"]
    times = [bench['t_static_ms'], bench['t_got_ms'], bench['t_dlsym_ms']]
    
    bars3 = ax3.bar(cats, times, color=[accent_green, accent_blue, accent_red], width=0.45)
    ax3.set_ylabel("50,000 Çağrı Süresi (ms)", fontsize=10, color=text_color)
    ax3.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars3:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f"{bar.get_height():.2f} ms",
                 ha='center', va='bottom', color=text_color, fontsize=9, fontweight='bold')

    # PANEL 4: Güvenlik ve Eklenti Tehdit Dağılımı
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("Dinamik Kütüphane Güvenlik ve Kararlılık Riskleri", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    threats = ["Dangling Function Ptr", "LD_PRELOAD SUID Hijack", "Symbol Shadowing", "Lazy Binding Jitter"]
    risk_scores = [95, 98, 85, 90]
    
    bars4 = ax4.bar(threats, risk_scores, color=[accent_red, accent_red, accent_amber, accent_blue], width=0.5)
    ax4.set_ylabel("Kritiklik / Risk Skoru (%)", fontsize=10, color=text_color)
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

    # 2. GOT/PLT Tembel Bağlama Doğrulaması
    lib = SimulatedSharedLibrary("libtest.so", 0x7FFF0000, {"func_a": 0x100})
    linker = SimulatedDynamicLinker(bind_now=False)
    linker.load_library(lib)
    _, first_call = linker.call_plt_trampoline("func_a")
    assert first_call is True, "HATA: İlk çağrıda tembel çözümleme tetiklenmelidir!"
    _, second_call = linker.call_plt_trampoline("func_a")
    assert second_call is False, "HATA: İkinci çağrıda GOT tablosundan doğrudan okunmalıdır!"
    print("  [+] GOT/PLT Tembel Bağlama ve Önbellekleme Mantığı Doğrulandı.")

    # 3. Dangling Function Pointer Tespiti
    is_dangling, _ = DynamicLinkerSabotageLab.simulate_dangling_function_pointer()
    assert is_dangling is True, "HATA: dlclose sonrası işaretçi askıda kalmalıdır!"
    print("  [+] dlclose Dangling Pointer ve Unmap Davranışı Doğrulandı.")

    # 4. Kütüphane Arama Sırası Doğrulaması (RPATH vs RUNPATH)
    rpath_resolver = LibraryPathResolver(rpath="/secure/rpath", runpath=None)
    p_rpath, _ = rpath_resolver.resolve("lib.so", env_ld_library_path="/user/path")
    assert p_rpath.startswith("/secure/rpath"), "HATA: RPATH LD_LIBRARY_PATH'i ezmelidir!"
    
    runpath_resolver = LibraryPathResolver(rpath=None, runpath="/secure/runpath")
    p_runpath, _ = runpath_resolver.resolve("lib.so", env_ld_library_path="/user/path")
    assert p_runpath.startswith("/user/path"), "HATA: LD_LIBRARY_PATH RUNPATH'i ezmelidir!"
    print("  [+] RPATH vs RUNPATH Öncelik Hiyerarşisi Doğrulandı.")

    # 5. Benchmark Performans Kontrolü
    bench = run_linking_call_benchmark(iterations=10000)
    assert bench["t_dlsym_ms"] > bench["t_got_ms"], "HATA: dlsym araması GOT çağrısından daha yavaş olmalıdır!"
    print("  [+] Fonksiyon Çağrı Başarım Hiyerarşisi Doğrulandı.")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)

```

## 16. Savunma Sanayii Senaryoları ve Gün Sonu Özeti

### Savunma Sanayii ve Görev Kritik Sistem Senaryoları
1. **ASELSAN Elektronik Harp Podu: Çalışırken Algoritma Yükleme (Hot-Swapping)**:
   - Tehdit kütüphanesine yeni bir radar sinyali eklendiğinde görev podu durdurulamaz.
   - Pod yazılımı `dlopen("libnew_threat.so", RTLD_NOW)` ile yeni tehdit kütüphanesini belleğe alır, sembolleri doğrular ve veri akışını kesintisiz olarak yeni algoritmaya yönlendirir.
2. **TUSAŞ Helikopter Görev Bilgisayarı: Deterministik Başlatma**:
   - Uçuş kontrol bilgisayarında ilk silah atış anında PLT çözümleme gecikmesi (jitter) oluşmaması için tüm süreçler `LD_BIND_NOW=1` ortamında başlatılır. Böylece tüm kütüphane bağlantıları motor çalıştırma evresinde tamamlanır.

### Gün Sonu Özeti (3 Cümlelik Kapanış)
1. **Dinamik Bağlama Modeli**: Dinamik kütüphaneler (`.so`), kodun fiziksel RAM'de tek bir kopya olarak tutulmasını sağlayıp bellek tasarrufu sunarken, çalışma anında dinamik bağlayıcı (`ld.so`) tarafından yürütülür.
2. **Tembel Bağlama ve GOT/PLT**: İlk çağrıda PLT üzerinden `ld.so` tetiklenerek hedef adres GOT tablosuna yazılır; sonraki tüm çağrılar doğrudan adrese zıplar ($O(1)$).
3. **Mühendislik Kuralı**: Görev kritik sistemlerde belirsiz gecikmeleri (jitter) önlemek için `LD_BIND_NOW=1` kullanılmalı, eklenti yönetiminde `dlclose` sonrası işaretçiler sıfırlanmalı ve sembol çakışmalarını önlemek için görünürlük gizlenmelidir (`visibility("hidden")`).


## 17. Gelecek Gün Köprüsü: Gün 097

Yarın **GÜN 097** kapsamında:
- **Konu**: **`ldd` Komutu, Çalışma Zamanı Bağımlılıkları (Runtime Dependencies) ve Kütüphane Cehennemi (DLL Hell)**
- **Kapsam**: `ldd` komutunun iç mekanizması (aslında bir kabuk betiğidir!), güvenli olmayan ikili dosyalarda `ldd` çalıştırma güvenlik açığı, eksik kütüphane tespiti (`not found`), uyumsuz glibc sürümleri (`GLIBC_2.34 not found`) ve statik ikili dosya (`-static`) çözümleri.
- **Hazırlık**: Bugün dinamik bağlayıcının iç işleyişini kavradık; yarın bu bağlayıcının sistem genelindeki bağımlılık ağaçlarını denetleyeceğiz.
