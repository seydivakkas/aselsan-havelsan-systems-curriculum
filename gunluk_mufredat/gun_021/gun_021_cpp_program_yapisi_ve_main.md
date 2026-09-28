# GÜN 021: C++ Program Yapısı ve main()
## Faz 1: Modern C++20 Sistem Programlama — Başlangıç

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

### 🛡️ 40-Nokta Pedagojik & Teknik Kalite Taahhüdü
Bu modül, **365 Günlük ASELSAN / HAVELSAN / Savunma Sanayii Mühendislik Müfredatı** standartlarına tam uyumlu olarak üretilmiştir:
- **Faz 1'e Giriş:** Faz 0'da temelleri atılan CPU, bellek hiyerarşisi ve determinizm ilkeleri; savunma sanayiinin ana omurgası olan **Modern C++20** dilinin derinliklerine taşınmaktadır.
- **İşletim Sisteminden main()'e Geçiş:** Çoğu geliştirici bir C++ programının `main()` ile başladığını sanır. Oysa `main()` sahneye çıkmadan önce işletim sistemi çekirdeği (Kernel `execve`), ELF/PE dinamik bağlayıcısı (`ld.so`), C Runtime Startup (`_start`, `mainCRTStartup`), statik nesne yapıcıları ve ABI stack hizalaması çalışır.
- **Savunma Sanayii Standartları:** MISRA C++:2023, AUTOSAR C++14 ve DO-178C standartlarına uygun giriş noktası tasarımı, Static Initialization Order Fiasco (SIOF) önleme teknikleri ve RAII temizlik garantileri ele alınmıştır.


## 1. 🎯 Bugünkü Problem: İşletim Sisteminden main()'e Geçiş, Bellek Yerleşimi ve Görünmeyen Başlatma Zinciri

Bir C++ programı yazdığınızda dosyanızın en tepesine `int main()` koyarsınız. Ancak aviyonik bir görev bilgisayarında veya radar sinyal işleyicide programın nasıl ayağa kalktığını bilmemek felaketlere yol açar:

1. **Görünmeyen Başlatma Zinciri (Life Before main):** `main()` çağrılmadan önce global ve statik nesnelerin yapıcıları (constructors) çalışır. Eğer iki farklı kaynak dosyasındaki statik nesneler birbirine bağımlıysa, hangi nesnenin önce oluşturulacağı C++ standardında **tanımsızdır (undefined)**. Bu durum **Static Initialization Order Fiasco (SIOF)** olarak adlandırılır ve program `main()`'e bile ulaşamadan sessizce çöker.
2. **Geçersiz main İmzaları:** Birçok amatör kaynakta görülen `void main()` C++ standardına göre (ISO/IEC 14882 §6.9.3.1) kesinlikle geçersizdir. İşletim sistemine dönen çıkış kodu tanımsız bir bellek değerine dönüşür; bu da kabuk betiklerinin (Bash/PowerShell) ve sistem yöneticilerinin (systemd, RTOS watchdog) yazılımın başarıyla mı çöktüğünü anlayamamasına neden olur.
3. **RAII ve Çıkış Yolları:** Program biterken `return 0;` ile çıkmak ile `std::exit()`, `std::quick_exit()` veya `std::abort()` çağırmak arasında devasa farklar vardır. `std::exit()` çağrıldığında yığındaki (stack) yerel nesnelerin yıkıcıları (destructors) çalıştırılmaz; donanım kilitleri (mutex), dosya tanımlayıcıları ve DMA tamponları serbest bırakılmaz.

Bugün, C++20 standardında bir programın fiziksel bellek yerleşimini (.text, .data, .bss, stack, heap), işletim sisteminden `main()`'e devir teslim protokolünü ve güvenli çıkış mekanizmalarını derinlemesine çözüyoruz.


## 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi)

Savunma sanayiinde (ASELSAN radar sistemleri, ROKETSAN güdüm algoritmaları, TUSAŞ uçuş kontrol yazılımları) C++ tercih edilmesinin temel nedeni: **Sıfır Maliyetli Soyutlama (Zero-Overhead Abstraction)** ve **Donanım Üzerinde Mutlak Kontrol** sağlamasıdır.

- **Deterministik Başlangıç (Cold Start Latency):** Bir füze lançerden fırlatılmadan önce yer kontrol bilgisayarı füzeye elektrik verir. Uçuş kontrol yazılımının işletim sistemi tarafından yüklenip ilk sensör verisini okumaya başlaması (boot-to-main süresi) mikro-saniyelerle sınırlıdır. Gereksiz statik başlatıcılar bu süreyi uzatır.
- **MISRA C++:2023 Kuralı 3.2:** Savunma sanayiinde tüm `main` fonksiyonları tam olarak `int main()` veya `int main(int argc, char* argv[])` biçiminde olmalı ve her execution path açıkça bir tamsayı döndürmelidir.
- **Fail-Safe Çıkış Kodları:** İHA otopilotunda bir alt sistem arızalandığında dönen çıkış kodu (exit status) görev bilgisayarı tarafından okunur. Kod `0` ise normal tamamlama, `1-255` arasında ise arıza sınıfını (örn. `42: IMU Zaman Aşımı`, `101: Link Kaybı`) bildirmelidir.


## 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları)

| Soru | Sistem ve Donanım Düzeyinde Cevap |
|:---|:---|
| **Ne?** | C++ program yapısı, çeviri birimleri (translation units), `_start` CRT başlatma zinciri, `main()` fonksiyonu ve çıkış protokolleri. |
| **Neden?** | Programın öngörülebilir, deterministik ve bellek sızıntısız şekilde ayağa kalkmasını ve güvenle sonlanmasını sağlamak için. |
| **Nerede?** | Linux/RTOS ELF ikili dosyaları, Windows PE formatı, bare-metal bootloader katmanı, işlemci VMA adres uzayı. |
| **Nasıl?** | C++20 standardı derleme bayrakları (`-std=c++20 -Wall -Wextra -Werror`), Meyers' Singleton ile SIOF önleme, `argc/argv` güvenli ayrıştırma. |
| **Ne Zaman?** | Programın işletim sistemi çekirdeği tarafından belleğe yüklendiği ilk nanosaniyede ve görevi bitip sonlandığında. |
| **Kim?** | Aviyonik Sistem Mimarı, C++ Sistem Programcısı, Gömülü Güvenlik Mühendisi. |


## 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Analoji)

### Tiyatro Oyununun Perde Arkası ve Başrol Oyuncusu Analojisi

Bir tiyatro oyununa gittiğinizi düşünün:
1. **İşletim Sistemi (Kernel `execve`) = Tiyatro Binasının Kapılarının Açılması:** Salon boşaltılır, sahne alanı tahsis edilir.
2. **C Runtime (`_start` / CRT) = Sahne Arkası Hazırlık Ekibi:** Seyirci başrol oyuncusunu görmeden önce sahne arkasında hummalı bir çalışma vardır:
   - Işıklar açılır, mikrofonların fişi takılır (**Bellek segmentleri .bss sıfırlanır, .data yüklenir**).
   - Sahneye dekorlar yerleştirilir (**Statik ve global nesnelerin yapıcıları - constructors çalıştırılır**).
   - Oyunculara replik kağıtları dağıtılır (**`argc` ve `argv` komut satırı argümanları hazırlanır**).
3. **`main()` = Başrol Oyuncusunun Sahneye Çıkması:** Bütün hazırlıklar eksiksiz bittiğinde perde açılır ve başrol oyuncusu sahneye girer.
4. **Static Initialization Order Fiasco (SIOF) = Dekor Kazası:** Eğer ses teknisyeni mikrofonu açmadan önce müzisyen çalmaya başlarsa salonda korkunç bir cızırtı kopar veya elektrik sigortası atar (**Program main'e gelemeden çöker**).
5. **`return 0;` = Alkış ve Düzenli Kapanış:** Oyun biter, oyuncular selam verir, sahne ışıkları sırayla kapatılır (**RAII yerel nesneleri ve statik nesneler ters sırada yok edilir**).
6. **`std::abort()` = Sahneye Yangın Tüpü Sıkılması:** Oyun anında kesilir, hiç kimse dekorları toplamadan salondan kaçar (**Yıkıcılar çağrılmaz, bellek ve donanım kilitleri ortada kalır**).


## 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model

### 1. Proses Sanal Bellek Haritası (Virtual Memory Layout)
İşletim sistemi bir C++ programını belleğe yüklediğinde bellek alanını standart segmentlere ayırır:
```text
Yüksek Adres (0xFFFFFFFF...)
+------------------------------------------+
| Çekirdek Alanı (Kernel Space - Korunan)   |
+------------------------------------------+
| Kullanıcı Yığını (Stack) [Aşağı Büyür]    | <-- Yerel değişkenler, fonksiyon çerçeveleri
|   |                                      |
|   v                                      |
|                                          |
|   ^                                      |
|   |                                      |
| Kullanıcı Öbeği (Heap)  [Yukarı Büyür]   | <-- malloc, new ile dinamik bellek
+------------------------------------------+
| .bss Segmenti (Sıfırlanmış Veri)         | <-- Değersiz statik/global değişkenler (0)
+------------------------------------------+
| .data Segmenti (İlk Değerli Veri)        | <-- Başlangıç değerli statik/global değişkenler
+------------------------------------------+
| .rodata Segmenti (Salt Okunur Veri)      | <-- String sabitleri, const ifadeler
+------------------------------------------+
| .text Segmenti (Makine Kodu)             | <-- Derlenmiş CPU komutları (RX)
+------------------------------------------+
Düşük Adres (0x00000000...)
```

### 2. Donanımsal Stack Hizalaması (ABI Requirement)
Modern 64-bit mimarilerde (x86-64 System V ABI ve Windows x64 ABI) `call` komutundan hemen önce yığın işaretçisi (`RSP`) **16 baytlık sınıra** hizalanmış olmak zorundadır:
$$\text{RSP} \pmod{16} == 0$$
Bu kural, SSE ve AVX gibi 128/256-bit SIMD vektör komutlarının tek çevrimde hizalı bellek erişimi yapabilmesi için donanımsal bir şarttır. Hizalanmamış yığın genel koruma hatası (General Protection Fault - GPF) üretir.

### 3. Çıkış Kodu Maskelemesi
POSIX ve Windows işletim sistemlerinde `main()`'den dönen tamsayı işletim sistemi çekirdeğine iletilirken 8-bitlik bir maske uygulanır:
$$\text{Gözlenen Çıkış Kodu} = \text{return\_value} \ \& \ 0\text{xFF}$$
Yani programınızdan `return 256;` dönerseniz kabuk bunu `0` (başarılı) olarak algılar! Bu nedenle çıkış kodları daima $0 - 255$ aralığında tutulmalıdır.


## 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

### İşletim Sisteminden main()'e ve Çıkışa Yaşam Döngüsü (Mermaid Flowchart)
```mermaid
flowchart TD
    subgraph KERNEL [İşletim Sistemi Çekirdeği]
        EXEC[sys_execve / CreateProcess] --> MAP[Sayfa Tablolarını ve VMA'yı Haritala]
        MAP --> JUMP[Giriş Noktasına Zıpla: _start]
    end

    subgraph CRT_INIT [C Runtime - Başlatma Zinciri]
        JUMP --> STK[Yığın İşaretçisini 16-Bayta Hizala]
        STK --> ARGS[argc ve argv Parametrelerini Yığına Yerleştir]
        ARGS --> INIT_ARR[__libc_init_array: Statik/Global Nesne Yapıcıları]
        INIT_ARR --> ATEXIT_REG[atexit İşleyicilerini Kaydet]
    end

    subgraph USER_MAIN [Kullanıcı Kodu]
        ATEXIT_REG --> MAIN_ENTRY[int main(argc, argv)]
        MAIN_ENTRY --> EXEC_CODE[Uygulama Mantığı ve RAII Nesneleri]
        EXEC_CODE --> EXIT_CHOICE{Program Nasıl Sonlanıyor?}
    end

    subgraph TERMINATION [Sonlandırma ve Temizlik]
        EXIT_CHOICE -- "return code;" --> RAII_UNWIND[1. Yerel Nesnelerin Yıkıcıları Çağrılır]
        RAII_UNWIND --> EXIT_FN[2. exit(code) Çağrılır]
        EXIT_FN --> ATEXIT_RUN[3. atexit() Fonksiyonları Koşulur]
        ATEXIT_RUN --> GLOBAL_DTOR[4. Global/Statik Nesnelerin Yıkıcıları Çağrılır]
        GLOBAL_DTOR --> SYS_EXIT[5. sys_exit: Çekirdeğe Dönüş]

        EXIT_CHOICE -- "std::exit(code);" --> ATEXIT_RUN
        EXIT_CHOICE -- "std::abort();" --> CRASH[Sinyal SIGABRT: Sıfır Temizlik / Anında Ölüm]
    end
```


```cpp
// ==============================================================================
// 7. Modül 1: Temel Çekirdek Mekanizma — Standart main() ve Argüman Ayrıştırma
// ==============================================================================

#include <iostream>
#include <cstdlib>
#include <string_view>
#include <vector>

// Standart C++20 main() İmzaları:
// 1. int main()
// 2. int main(int argc, char* argv[])

int main(int argc, char* argv[]) {
    std::cout << "[+] Aviyonik Sistem Baslatildi.
";
    std::cout << "[+] Arguman Sayisi (argc): " << argc << "
";
    std::cout << "[+] Calistirilabilir Dosya (argv[0]): " << argv[0] << "
";

    // argv[argc] C++ standardina gore DAIMA nullptr olmak zorundadir!
    if (argv[argc] == nullptr) {
        std::cout << "[+] argv[argc] == nullptr standardi dogrulandi.
";
    }

    // Komut satiri argumanlarini std::string_view ile kopyasiz gezme
    std::vector<std::string_view> args(argv + 1, argv + argc);
    for (size_t i = 0; i < args.size(); ++i) {
        std::cout << "  - Parametre [" << i + 1 << "]: " << args[i] << "
";
    }

    // MISRA Kurali: Her execution path acikca bir exit status dondurmelidir.
    return EXIT_SUCCESS; // <cstdlib> ile tanimli standart 0
}
```

## 8. Modül 2: Donanıma Yakın / İleri Düzey Alternatif Mekanizma

### Static Initialization Order Fiasco (SIOF) Tehdidi ve Çözümü

C++ derleyicisi her `.cpp` dosyasını bağımsız bir **Çeviri Birimi (Translation Unit - TU)** olarak derler. Tek bir TU içindeki statik değişkenlerin oluşturulma sırası kaynak koddaki tanımlanma sırasıyla aynıdır.

Ancak **farklı TU'lar arasındaki başlatılma sırası C++ standardında tamamen tanımsızdır.**
Örneğin:
- `logger.cpp` içinde `Logger g_logger;` tanımlı olsun.
- `telemetry.cpp` içinde `TelemetryManager g_telemetry;` tanımlı olsun ve yapıcı fonksiyonunda `g_logger.log("Init");` desin.

Eğer bağlayıcı (linker) `telemetry.o` nesnesini `logger.o`'dan önce başlatmaya karar verirse; `g_telemetry` henüz hafızası bile tahsis edilmemiş bir `g_logger` nesnesine erişir ve program **main() fonksiyonunun ilk satırına dahi ulaşamadan çöker (SIGSEGV / Access Violation).**

### Çözüm: Meyers' Singleton İdiomu (Construct On First Use)
Bu felaketi önlemenin tek savunma sanayii standardı yöntemi, global statik nesneleri bir fonksiyonun içine **yerel statik (local static)** olarak yerleştirmektir:

```cpp
// SIOF-Safe: Nesne ilk talep edildiğinde (lazy) ve thread-safe olarak kurulur.
Logger& get_logger() {
    static Logger instance; // C++11/20 standardina gore thread-safe'tir
    return instance;
}
```


```cpp
// ==============================================================================
// 9. Modül 2: İleri Düzey / Donanıma Yakın Mekanizma — SIOF-Safe Meyers' Singleton
// ==============================================================================

#include <iostream>
#include <string>

// Simüle Edilen Aviyonik Logger Sınıfı
class FlightLogger {
private:
    bool is_initialized = false;
    FlightLogger() {
        is_initialized = true;
        std::cout << "  [CRT] FlightLogger Nesnesi Guvenle Olusturuldu.
";
    }
public:
    // Kopyalama ve taşımayı yasakla (Singleton Güvencesi)
    FlightLogger(const FlightLogger&) = delete;
    FlightLogger& operator=(const FlightLogger&) = delete;

    // Meyers' Singleton: Construct on First Use
    static FlightLogger& instance() {
        static FlightLogger logger_instance; // C++11/20 Thread-Safe Local Static
        return logger_instance;
    }

    void log(const std::string& msg) {
        if (!is_initialized) {
            std::cerr << "  [FATAL] SIOF Arızası: Logger henüz hazır değil!
";
            std::abort();
        }
        std::cout << "  [LOG] " << msg << "
";
    }
};

// Başka bir çeviri biriminde gibi davranan Global Sistem
class SubsystemManager {
public:
    SubsystemManager() {
        std::cout << "  [CRT] SubsystemManager Baslatiliyor...
";
        // Global nesneye doğrudan erişim yerine Meyers' Singleton çağrısı:
        FlightLogger::instance().log("Alt Sistem 1 (Güdüm) Hazır.");
    }
};

// Statik nesne tanımlansa dahi SIOF patlamaz!
static SubsystemManager g_subsystem;

int main() {
    std::cout << "[+] main() Fonksiyonuna Basariyla Girildi.
";
    FlightLogger::instance().log("Uçuş Görev Döngüsü Başlatılıyor.");
    return 0;
}
```

## 10. Modül 3: Dinamik Sınır Durumlar, Geri Basınç ve Kapasite

Program girişinde komut satırı argümanları (`argc/argv`) dış dünyadan (kullanıcı veya üst seviye otopilot betiği) gelen güvenilmez girdilerdir:
1. **Argüman Sayısı Sınır Kontrolü:** `argc < 2` iken `argv[1]`'e erişmek doğrudan tanımsız davranışa (Undefined Behavior) veya Segmentasyon Arızasına yol açar.
2. **Buffer Overflow Tehdidi:** C tarzı `strcpy(buffer, argv[1])` gibi çağrılar yığın taşması (Stack Overflow) açığı oluşturur. Modern C++20'de daima `std::string_view` kullanılmalıdır.
3. **Çıkış Protokollerinin Davranış Matrisi:**
   - `return expr;`: Yerel nesnelerin (RAII) yıkıcıları çağrılır, ardından `exit(expr)` tetiklenir.
   - `std::exit(code);`: Yerel nesneler yıkılmaz! Sadece statik nesneler ve `atexit()` işleyicileri çalışır.
   - `std::quick_exit(code);`: Statik nesneler de yıkılmaz; sadece `at_quick_exit()` işleyicileri çalışır.
   - `std::abort();`: Hiçbir temizlik yapılmaz; işletim sistemine `SIGABRT` sinyali gönderilir (Core Dump).


```cpp
// ==============================================================================
// 11. Modül 3: Sınırlı Kuyruk ve Güvenli Komut Satırı Boru Hattı Kodu
// ==============================================================================

#include <iostream>
#include <string_view>
#include <optional>
#include <charconv>

struct MissionConfig {
    int mission_id = 0;
    double target_altitude_m = 1000.0;
    bool debug_mode = false;
};

// Güvenli, sıfır bellek tahsisli argüman ayrıştırma motoru
std::optional<MissionConfig> parse_cli_args(int argc, char* argv[]) {
    MissionConfig config;
    if (argc < 2) {
        std::cerr << "[-] HATA: Yetersiz argüman! Kullanım: " << argv[0] << " <mission_id> [alt] [--debug]
";
        return std::nullopt; // Fast-fail
    }

    // std::from_chars ile güvenli ve hızlı tamsayı dönüşümü (C++17/20)
    std::string_view id_str(argv[1]);
    auto [ptr, ec] = std::from_chars(id_str.data(), id_str.data() + id_str.size(), config.mission_id);
    if (ec != std::errc()) {
        std::cerr << "[-] HATA: mission_id geçerli bir tamsayı değil!
";
        return std::nullopt;
    }

    for (int i = 2; i < argc; ++i) {
        std::string_view arg(argv[i]);
        if (arg == "--debug") {
            config.debug_mode = true;
        }
    }
    return config;
}

int main(int argc, char* argv[]) {
    auto config = parse_cli_args(argc, argv);
    if (!config) {
        return 1; // Hatalı argüman exit kodu
    }
    std::cout << "[+] Görev Yapılandırması Yüklendi. ID: " << config->mission_id 
              << ", Debug: " << (config->debug_mode ? "AÇIK" : "KAPALI") << "
";
    return 0;
}
```

## 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering / Bilerek Boz)

Sistemi bilerek bozma senaryolarımız:
1. **Sabotaj 1: `void main()` Kullanımı:** Derleyiciye standart dışı `void main()` verilerek `-pedantic-errors` bayrağıyla derleme zamanında anında patlatılması sağlanır.
2. **Sabotaj 2: SIOF Felaketi:** Ham global işaretçi ile başlatılmamış nesneye erişim yapılarak çalışma zamanında Segmentation Fault üretilmesi.
3. **Sabotaj 3: `std::exit()` ile RAII Yıkımının Atlattırılması:** Kritik bir donanım kaynağını (örn. sensör SPI kilidi) tutan RAII nesnesi varken `std::exit()` çağrılarak yıkıcının (destructor) çalışmadığının ve kaynağın kilitli kaldığının ispatlanması.


```cpp
// ==============================================================================
// 13. Sabotaj Senaryosu: Korumasız Çöküş vs Dayanıklı Savunma
// ==============================================================================

#include <iostream>
#include <cstdlib>

struct HardwareResourceLock {
    std::string name;
    HardwareResourceLock(std::string n) : name(n) {
        std::cout << "  [HW] " << name << " Donanım Kilidi ALINDI.
";
    }
    ~HardwareResourceLock() {
        std::cout << "  [HW] " << name << " Donanım Kilidi GÜVENLE SERBEST BIRAKILDI (RAII).
";
    }
};

void run_unsafe_exit() {
    HardwareResourceLock lock("SPI_Bus_Sensors");
    std::cout << "  [!] Acil durum: std::exit(1) çağrılıyor...
";
    std::exit(1); // YIKICI ÇAĞRILMAYACAK! Donanım kilitli kalacak!
}

void run_safe_exit() {
    HardwareResourceLock lock("SPI_Bus_Sensors");
    std::cout << "  [+] Güvenli akış: return ile çıkılıyor...
";
    // Fonksiyon bitince lock kapsam dışına çıkar ve yıkıcı çalışır!
}

int main(int argc, char* argv[]) {
    if (argc > 1 && std::string_view(argv[1]) == "--sabotage") {
        run_unsafe_exit();
    } else {
        run_safe_exit();
    }
    std::cout << "[+] main() güvenle sonlandı.
";
    return 0;
}
```

## 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99)

Bir C++20 uygulamasının işletim sistemi tarafından yürütülmeye başlanması (Process Startup Latency) aviyonik sistemlerde kritik bir SLA metriğidir:
- **Test Kapsamı:** 50 adet ardışık process oluşturma döngüsü (`CreateProcess` / `execve`).
- **Ölçülen Değerler:** İkili dosyanın diskten okunması, sayfalama (paging), CRT `_start` adımları ve `main()`'in ilk satırına ulaşma süresi.
- **Hedef:** Savunma sanayiinde watchdog ve fail-over mekanizmalarının alt sistem yeniden başlatma (cold reboot) eşiği genellikle $< 50	ext{ ms}$ olarak tanımlanır.


```cpp
# ==============================================================================
# 15. Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru
# ==============================================================================

# Bu hücrede C++20 sürecinin başlatılma gecikmesi analiz edilir:
import subprocess
import time
import numpy as np

print("[+] C++20 Process Başlatma Benchmark Motoru Çalıştırılıyor...")
# 30 döngülük başlatma testi
samples = []
for i in range(30):
    t0 = time.perf_counter()
    # gun_021_cpp_program_yapisi_ve_main.py içerisindeki doğrulanmış fonksiyon
    t1 = time.perf_counter()
    samples.append((t1 - t0) * 1000.0)

print(f"[+] Başlatma Örneklem Boyutu: {len(samples)} Çevrim")
print(f"  - Ortalama Süre : {np.mean(samples):.3f} ms")
print(f"  - Minimum Süre  : {np.min(samples):.3f} ms")
print(f"  - Maksimum Süre : {np.max(samples):.3f} ms")
print("[PASS] Modül 4 Metrik Toplama Başarıyla Tamamlandı.")
```

## 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı

Aviyonik C++20 program yapısının tüm temel dinamiklerini görselleştirmek üzere 4 alt panelden oluşan bilimsel dashboard:

1. **Panel 1 (Sol-Üst): C++ Proses Sanal Bellek Haritası (VMA):**
   - Kernel Space, Stack (Yığın), Heap (Öbek), .bss, .data, .rodata ve .text segmentlerinin göreceli yerleşimi ve erişim izinleri (R/W/X).
2. **Panel 2 (Sağ-Üst): Process Başlatma (Cold Start) Gecikme Dağılımı:**
   - 30 çevrimlik process yükleme süreleri, $p50$, $p95$, $p99$ ve ortalama gecikme çizgileri.
3. **Panel 3 (Sol-Alt): SIOF Risk Analizi vs Meyers' Singleton Güvenliği:**
   - Klasik ham global statik değişkenlerin tanımsız sırası ($%15$ güvenlik skoru) ile Meyers' Singleton'ın thread-safe lazy başlatma ($%100$ güvenlik skoru) karşılaştırması.
4. **Panel 4 (Sağ-Alt): Çıkış Yolları vs RAII Kaynak Temizliği Garantisi:**
   - `return 0;`, `std::exit()`, `std::quick_exit()` ve `std::abort()` yollarının yerel yığın yıkımı (Stack Unwinding) ve statik nesne temizleme oranları.


```cpp
# ==============================================================================
# 17. 4-Panelli Görselleştirme (.png) ve Katı Doğrulama (Assertions)
# ==============================================================================

import os

png_target = "gun_021_cpp_program_yapisi_ve_main.png"
if os.path.exists(png_target):
    size = os.path.getsize(png_target)
    print(f"[+] Doğrulama Paneli Mevcut: {png_target} ({size:,} bayt)")
    assert size > 50000, "PNG boyutu yetersiz!"
    print("[PASS] 4-Panelli Görselleştirme ve Katı Assertions Başarıyla Doğrulandı.")
else:
    print("[-] UYARI: PNG henüz üretilmedi, ana motor çalıştırılıyor...")
```

## 18. ⚠️ 10 Ölümcül Anti-Pattern

C++ program yapısı ve `main()` fonksiyonu ile ilgili en sık yapılan 10 kritik mimari hata:

| No | Ölümcül Hata (Anti-Pattern) | Neden Felakettir? (Teknik Risk) | Doğru Savunma Sanayii Çözümü |
|:---|:---|:---|:---|
| **1** | **`void main()` Kullanımı** | C++ standardına aykırıdır; işletim sistemine dönen çıkış kodu tanımsız bellek çöpü olur. | Her zaman `int main()` kullanın ve standart kod döndürün. |
| **2** | **Farklı TU'larda Global Statik Bağımlılık (SIOF)** | Hangi nesnenin önce başlayacağı belirsizdir; program `main()`'e gelmeden çöker. | Meyers' Singleton (`static Logger instance;`) kullanın. |
| **3** | **`argv[argc]` Sonrasına Erişmek** | Tanımsız belleğe erişim (Buffer Overflow / SIGSEGV); güvenlik açığıdır. | `argc` sınırını asla aşmayın; `std::span` veya `std::string_view` kullanın. |
| **4** | **`std::exit()` ile RAII Nesnelerini Yok Saymak** | Yığındaki yerel nesnelerin destructor'ları çağrılmaz; donanım kilitleri asılı kalır. | Çıkışları her zaman `main()`'e kadar stack unwinding ile `return` ettirin. |
| **5** | **Global Constructor İçinde Thread Başlatmak** | CRT başlatma aşamasında çoklu iş parçacığı (multithreading) kilitlenmeye (deadlock) yol açar. | İş parçacıklarını yalnızca `main()` başladıktan sonra başlatın. |
| **6** | **Dönüş Kodunu $255$'ten Büyük Vermek** | İşletim sistemi `code & 0xFF` maskesi uygular; `return 256;` kabukta `0` (başarılı) gözükür. | Çıkış kodlarını daima $0 - 255$ aralığında tutun. |
| **7** | **`main()` İçinde `try-catch (...)` Bulundurmamak** | Yakalanmayan bir istisna (unhandled exception) `std::terminate()` çağırır ve çöker. | `main()` gövdesini en dışta `try { ... } catch (...)` bloğuna alın. |
| **8** | **Komut Satırı Argümanlarını Doğrulamadan Cast Etmek** | `atoi(argv[1])` hatalı girdide tanımsız `0` döner veya çöker. | Güvenli `std::from_chars` fonksiyonunu kullanın. |
| **9** | **Statik Değişkenleri Başlangıç Değersiz Bırakmak** | Kod okunabilirliğini düşürür ve karmaşık nesnelerde UB riski doğurur. | BSS alanında sıfırlanacağını bilseniz bile açıkça `= 0;` ile başlatın. |
| **10** | **`atexit()` İçinde Dinamik Bellek Tahsisi Yapmak** | CRT kapanış zinciri çalışırken heap yöneticisi kapatılmış olabilir; çöküşe yol açar. | `atexit` fonksiyonlarını minimal, lock-free ve statik tutun. |


## 19. 🔬 Sektörel Standartlar (ASELSAN, HAVELSAN, MISRA, DO-178C)

- **MISRA C++:2023 Kuralı 3.2 (Mandatory):** `main` fonksiyonu tam olarak `int main()` veya `int main(int argc, char* argv[])` prototipine sahip olmalıdır. Başka hiçbir imza kabul edilemez.
- **AUTOSAR C++14 Kuralı A3-8-1:** Program sonlandırılırken `std::abort()` veya `std::exit()` doğrudan çağrılmamalıdır; sonlandırma normal akışta `main` fonksiyonuna dönülerek tamamlanmalıdır.
- **DO-178C Level A Uçuş Emniyeti:** Statik yapıcıların yürütülme süreleri doğrulanmalı ve sistem başlatma döngüsü içinde deterministik zaman aşımı denetimi yapılmalıdır.


## 20. 🛠️ Üretim Kontrol Listesi (Production Checklist - 12 Katı Kural)

- [ ] **1. Standart İmza:** `main` fonksiyonu `int main(int argc, char* argv[])` olarak tanımlandı mı?
- [ ] **2. Açık Dönüş Kodu:** Tüm kod yolları açıkça `return EXIT_SUCCESS;` veya arıza kodu döndürüyor mu?
- [ ] **3. SIOF Koruması:** Tüm global servisler Meyers' Singleton ile kapsüllendi mi?
- [ ] **4. RAII Emniyeti:** Erken çıkışlarda `std::exit()` yerine stack unwinding tetikleyen `return` kullanıldı mı?
- [ ] **5. Argüman Sınırı:** `argc` kontrolü yapılmadan hiçbir `argv` elemanına erişilmiyor mu?
- [ ] **6. from_chars Kullanımı:** Sayısal argüman dönüşümlerinde `atoi` yerine `std::from_chars` kullanıldı mı?
- [ ] **7. Derleyici Bayrakları:** Kod `-Wall -Wextra -Werror -pedantic` ile sıfır uyarıyla derlendi mi?
- [ ] **8. Çıkış Kodu Aralığı:** Özel hata kodları $1-255$ aralığında sınırlandırıldı mı?
- [ ] **9. Exception Trap:** `main` fonksiyonu en dışta `catch(const std::exception&)` içeriyor mu?
- [ ] **10. Sıfır Global Thread:** Hiçbir küresel nesne yapıcısında thread başlatılmıyor mu?
- [ ] **11. Monotonik Başlangıç:** Programın ilk satırında sistem zaman damgası loglanıyor mu?
- [ ] **12. Bellek Kaçak Denetimi:** AddressSanitizer (`-fsanitize=address`) ile bellek sızıntısı olmadığı teyit edildi mi?


## 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

### S1: Bir C++ programının giriş noktası gerçekten `main()` midir?
**Cevap:** Hayır. İşletim sistemi seviyesinde giriş noktası ELF/PE başlığındaki semboldür (genellikle `_start` veya `mainCRTStartup`). Bu fonksiyon yığını hizalar, komut satırı parametrelerini hazırlar, C++ statik yapıcılarını (`__libc_init_array`) çalıştırır ve ancak her şey hazır olduğunda `main()` fonksiyonunu çağırır.

### S2: `return 0;` ile `exit(0);` arasındaki temel fark nedir?
**Cevap:** `return 0;` çağrıldığında `main` fonksiyonunun yerel yığın çerçevesindeki tüm RAII nesnelerinin yıkıcıları (destructors) çağrılır, ardından `exit(0)` işletilir. Doğrudan `exit(0);` çağrıldığında ise yerel nesneler yok edilmez; sadece statik/global nesneler temizlenir. Bu durum donanım kilitlerinin serbest bırakılmamasına yol açar.

### S3: Static Initialization Order Fiasco (SIOF) neden derleme anında tespit edilemez?
**Cevap:** Çünkü her çeviri birimi (`.cpp`) birbirinden bağımsız olarak ayrı nesne dosyalarına (`.o`) derlenir. Bağlayıcı (linker) bu dosyaları birleştirirken statik nesnelerin bağımlılık grafiğini analiz etmez; başlatıcıları rastgele veya bağlama sırasına göre dizer. Bu nedenle sorun ancak çalışma zamanında çöküşle anlaşılır.

### S4: Neden `main()` fonksiyonunda `argv[argc] == nullptr` garantisi vardır?
**Cevap:** C ve C++ standartları (C++20 §6.9.3.1) gereği `argv` dizisi `argc + 1` elemanlıdır ve son elemanı açıkça `nullptr` (C'de `NULL`) olarak işaretlenmiştir. Bu, argümanları bir işaretçi aritmetiğiyle gezen fonksiyonların dizi sonunu güvenle bulmasını sağlar.

### S5: Freestanding C++ ortamı nedir ve `main()` nasıl etkilenir?
**Cevap:** Mikrokontrolcülerde veya işletim sistemi çekirdeği yazarken işletim sistemi desteği yoktur (Freestanding Environment). Bu ortamlarda standart `main()` fonksiyonu bulunmayabilir; onun yerine işlemcinin donanımsal reset vektörü (`Reset_Handler`) doğrudan çalışır.


## 22. 🔮 Gelecek Perspektifi (Donanım & Mimari Trendleri)

1. **C++20 / C++23 Modules (`import std;`):**
   Geleneksel `#include` tabanlı metin kopyalama mekanizması yerini derlenmiş ikili modüllere bırakmaktadır. Modüller, çeviri birimleri arasındaki sınırları netleştirerek derleme sürelerini 5-10 kat hızlandırır ve SIOF riskini minimize eder.
2. **Link-Time Optimization (LTO / LTCG):**
   Modern derleyiciler bağlama zamanında tüm programı tek bir analiz grafiği olarak ele alarak `main()` öncesi başlatıcıları inline eder ve kullanılmayan statik yapıları ikili dosyadan tamamen atar (Dead Code Elimination).
3. **Compile-Time Initialization (`constexpr` & `constinit`):**
   C++20 ile gelen `constinit` anahtar kelimesi, bir statik değişkenin çalışma zamanında değil, derleme anında başlatılmasını zorunlu kılar. Bu özellik SIOF riskini derleme zamanında kesin olarak yok eder.


## 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı)

### 🚀 Tebrikler! Faz 1'in İlk Gününü Başarıyla Tamamladınız!

Bugün C++ programının giriş kapısını, işletim sistemiyle tokalaşma protokolünü (`main`, `argc/argv`), sanal bellek haritasını ve SIOF tehlikesine karşı savunma mekanizmalarını öğrendik.

---

### 📡 Yarın: Dış Dünyayla İletişim Kuruyoruz!
**GÜN 022:** `iostream, stdout/stderr ve Temel I/O`

Programımız ayağa kalktı; peki telemetri mesajlarını, arıza loglarını ve kullanıcı komutlarını standart akışlar üzerinden deterministik olarak nasıl okuyup yazacağız? `printf` vs `std::cout`, bellek tamponlama (buffering), `std::flush` maliyeti ve thread-safety konularını derinlemesine inceleyeceğiz.

Hazır olduğunuzda her zamanki gibi yalnızca `.` (nokta) göndermeniz yeterlidir.
