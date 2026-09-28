# 00_BASLA
**Kaynak:** 365_Gun_ASELSAN_HAVELSAN_Tum_Kutuphaneler_Mekanizmalar_Guncel.xlsx
**Satır sayısı:** 70
**Sütun sayısı:** 8

365 GÜN — ASELSAN / HAVELSAN ODAKLI YAZILIM + SYSTEMS + AI MÜFREDATI

Amaç: Hiçbir şey bilmeyen yeni lisans öğrencisini; temel bilgisayar modelinden başlayıp C++20'yi yalnız bir dil olarak değil 365 gün boyunca devam eden ana systems-engineering omurgası haline getirerek Linux/POSIX, concurrency/IPC, TCP/UDP/protocol, embedded/RTOS, DDS/ROS2/Gazebo, PX4/MAVLink, production CV/TensorRT, control/RL, radar/DSP, verification/SIL/HIL, 5G/distributed systems ve AI engineering düzeyine çıkarmak. C++ Mastery Spine; language internals, ABI, generic programming, atomics/lock-free, allocators, async I/O, cross-compilation, SIMD, profiling/PGO/LTO, fuzzing ve large-scale architecture boyunca devam eder.

KPI | Değer | NASIL KULLANACAKSIN?

Toplam gün | 365 | 1 | 01_GUN_365_ANA_PLAN | Bugünün satırını oku. Ön Bilgi kısmını notsuz anlatamıyorsan önce tekrar et.

Ana faz | 14 | 2 | 05_KOD_LABORATUVARLARI | Minimal kodu kendin yaz. Kopyala-yapıştır yalnız doğrulama sonrası.

Ana plan sütunu | 18 | 3 | 06_GORSELLESTIRME_LAB | Memory/packet/thread/TF/signal/latency gibi görünmeyen sistemi görselleştir.

Kod laboratuvarı | 365 | 4 | Bilerek Boz | Normal çalışmayı gördükten sonra varsayımı kır; failure belirtisini tahmin et.

Görselleştirme labı | 365 | 5 | 07_AKTIF_HATIRLAMA | D+1/D+3/D+7/D+14/D+30 tekrarlarını yap ve skor ver.

Yetkinlik kapısı | 30 | 6 | 09_YETKINLIK_KAPILARI | Gate PASS olmadan kritik bir sonraki faza geçme.

Proje hazırlık matrisi | 12 | 7 | 10_PROJELERE_HAZIRLIK | Kavramlar biriktiğinde mini labları ana GitHub projelerinde birleştir.

Resmi/temel kaynak | 38

Recall 'Geçti' | 0

Gate PASS | 0

C++ Mastery ünitesi | 50

C++ Mastery gate PASS | 0

Faz | Alan | Başlangıç | Bitiş | Gün | Ana Çıkış | Proje Bağı

F0 | Bilgisayar ve Yazılım Temelleri | 1 | 20 | 20 | Bilgisayar/program zihinsel modeli + Git/terminal | Tümü

F1 | C++20 | 21 | 75 | 55 | C++20 Core + Mastery Spine S1; ileri C++ sonraki fazlarda devam eder | P1/P2/P9/P11

F2 | Linux / POSIX | 76 | 105 | 30 | Linux telemetry daemon + profiling | P1/P2/P12

F3 | Threads / Concurrency / IPC | 106 | 130 | 25 | TSan-clean concurrent processing pipeline | P1/P10

F4 | TCP/UDP / Protocol / Serialization | 131 | 160 | 30 | Resilient binary telemetry protocol | P1/P3/P10/P12

F5 | Embedded / RTOS / STM32 | 161 | 195 | 35 | RTOS avionics sensor/network gateway | P9/P11

F6 | DDS / ROS2 / Gazebo | 196 | 225 | 30 | ROS2/Gazebo autonomous UGV skeleton | P2/P10

F7 | PX4 / MAVLink | 226 | 245 | 20 | PX4/MAVLink telemetry & verification | P1/P8

F8 | Computer Vision / TensorRT | 246 | 275 | 30 | TensorRT real-time perception pipeline | P3/P5/P7

F9 | Control / Reinforcement Learning | 276 | 295 | 20 | PID/LQR vs RL quadcopter evaluation | P4

F10 | Radar / DSP / Communications | 296 | 315 | 20 | Radar/EO fused tracking pipeline | P7

F11 | Verification / SIL / HIL | 316 | 335 | 20 | Virtual avionics verification factory | P1/P5/P11

F12 | 5G / Distributed Systems | 336 | 350 | 15 | 5G resilient telemetry testbed | P12

F13 | AI Engineering / Architecture / Portfolio | 351 | 365 | 15 | AI engineering + 6 pinned repo release | P6/P8/Tüm portföy

DOĞRULUK VE ÖĞRENME KURALLARI

1. Sürüm/kurulum/API gibi değişebilen bilgilerde 11_KAYNAKLAR sayfasındaki resmi dokümanı kontrol et.
2. Bir teknolojiyi sırf popüler olduğu için öğrenme; önce 04_TEKNOLOJI_NEDEN_VAR sayfasında çözdüğü problemi oku.
3. 'Çalıştı' başarı değildir: en az bir failure case ve konuya uygun ölçüm/test olmalı.
4. GitHub'a 365 mini repo koyma. Mini-lablar öğrenme alanında; yalnız 10_PROJELERE_HAZIRLIK'taki ana projeler portföy reposu olur.
5. Simülasyon sonucunu gerçek-hardware sertifikasyonu gibi sunma. SIL/HIL/gerçek test ayrımını README'de açık yaz.
6. 8 GB VRAM nedeniyle VLM/CV tarafında küçük modeller, FP16/INT8 ve kontrollü çözünürlük/batch kullan.

KAPSAM SINIRI: Bu dosya 'yazılım dünyasındaki her teknoloji' iddiasında değildir. ASELSAN/HAVELSAN hedefi için gerekli olan bilgisayar temeli + C++/Linux/systems + embedded + robotics/autonomy + CV/AI + signal/verification + distributed/5G + AI engineering hattını, bağımlılıklarıyla kapsamlı biçimde işler. Web/mobile/game/blockchain gibi hedef dışı alanlar yalnız gerekli oldukları yerde yardımcı teknoloji olarak ele alınır.

C++ MASTERY SPINE — 365 GÜN BOYUNCA DEVAM EDEN ANA OMURGA

Aşama | Gün Aralığı | Ana Odak | Final Kanıt | Yıl sonu hedef ifadesi:

“Modern C++20 ile Linux, multithreading, networking, embedded ve robotics sistemleri geliştirebiliyorum; ownership/lifetime, generic programming, atomics/concurrency, debugging, profiling, testing/fuzzing, cross-compilation ve performance optimization konularında production-grade çalışabiliyorum.”

Hedef 'C++'ın tamamını ezbere biliyorum' değildir; kanıtlanabilir production systems yetkinliğidir.

S1 Core Language | 21–75 | value categories, forwarding, templates/concepts, constexpr, ranges, exception safety, object model, STL invalidation, CRTP | CPP-GATE-1

S2 Systems C++ | 76–160 | ABI/linker, CMake packaging, dependency mgmt, atomics, lock-free, cache, epoll/Asio, parser, fuzz/static analysis | CPP-GATE-2

S3 Embedded/Robotics C++ | 161–245 | cross-compilation, freestanding restrictions, deterministic allocation, pmr/pools, adapters, coroutines, tail-latency | CPP-GATE-3

S4 Performance/Numerical | 246–315 | AoS/SoA, SIMD, branches, assembly, LTO/PGO, profiling, numerical robustness, zero-copy buffers | CPP-GATE-4

S5 Architecture/Hardening | 316–365 | patterns/trade-offs, large codebase, code review, modules, API design, multi-layer quality, benchmark/release | CPP-GATE-5

KÜTÜPHANE / KOMUT / MEKANİZMA KATALOĞU

Sayfa | Kapsam | Satır | Nasıl Kullan? | Kullanım kuralı:

1) 21_OGRENME_SIRASI'nda bulunduğun checkpoint'i seç.
2) 13_STACK_ALT_BASLIKLAR'da mekanizma zincirini oku.
3) İlgili katalog sayfasında Ad → Nedir → Problem → Önkoşul → API/komut → Mini lab → Proje → Seviye → Resmi kaynak satırını tamamla.
4) Mini lab PASS olmadan yalnız API isimlerini ezberleyip ilerleme.
5) A1 = zorunlu çekirdek, A2 = güçlü ikinci öncelik, B1/C = gerektiğinde/uzmanlaşma.

Kapsam: ASELSAN/HAVELSAN hedefli systems/autonomy/embedded/CV/radar/5G/AI engineering stack'inin seçilmiş çekirdek + ileri evrenidir.

13_STACK_ALT_BASLIKLAR | Ana sistem katmanları ve neden-sonuç sırası | 42 | Önce hangi alanın neden var olduğunu gör.

14_PYTHON_KUTUPHANELERI | Python stdlib + numerical/ML/CV/network/backend/test | 62 | Ad→problem→API→mini lab→proje sırasıyla ilerle.

15_CPP_KUTUPHANELERI | STL + systems/network/robotics/CV/DSP/embedded C++ | 54 | Header/API ezberlemek yerine mekanizmayı öğren.

16_LINUX_KOMUTLARI | Filesystem/process/network/build/debug/perf/container/git | 74 | Komutu gerçek sistem problemini çözerken kullan.

17_RADAR_DSP_SISTEMLERI | DSP→radar→tracking→fusion→communications | 55 | Sinyal zincirini sırayla uygula.

18_5G_DISTRIBUTED_SISTEM | 5G NF/interface/procedure + distributed mechanisms | 57 | Registration→PDU→user-plane ve failure zincirini izle.

19_EMBEDDED_RTOS_STACK | MCU/bus/DMA/debug/RTOS/network/security/simulation | 37 | Önce virtual hardware, sonra gerçek board.

20_ROS2_PX4_CV_STACK | DDS/ROS2/Gazebo/PX4/MAVLink/CV/deployment | 48 | Robot/UAV sistem zincirini katman katman kur.

21_OGRENME_SIRASI | 365 güne bağlanmış 52 checkpoint | 52 | Sadece sıralı öğrenme için ana navigasyon sayfası.

