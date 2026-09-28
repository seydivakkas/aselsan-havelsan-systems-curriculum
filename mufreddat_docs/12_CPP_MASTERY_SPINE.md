# 12_CPP_MASTERY_SPINE
**Kaynak:** 365_Gun_ASELSAN_HAVELSAN_Tum_Kutuphaneler_Mekanizmalar_Guncel.xlsx
**Satır sayısı:** 51
**Sütun sayısı:** 17

## C++ Mastery Spine — 50 Ünite

### CPP-001 (Gün 30) — S1 Core Language
**Konu:** Object lifetime, storage duration ve temporary materialization
**Neden Bu Aşamada?:** RAII ve pointer öğrenildikten hemen sonra lifetime hatalarını doğru modellemek gerekir.
**Önkoşul:** scope, stack/heap, constructor/destructor
**First-Principles Hedefi:** Bir nesne ne zaman gerçekten vardır, ne zaman yok olur; reference/pointer ne zaman dangling olur?
**Kod Laboratuvarı:** Temporary/reference lifetime deneyleri; destructor logları.
**Bilerek Boz / Failure:** Dangling reference üret; ASan/UBSan ile gözle.
**Ölçüm / Benchmark:** copy/move/destructor sayıları
**Savunma/Systems Bağlamı:** Telemetry/parser buffer ownership.

### CPP-002 (Gün 34) — S1 Core Language
**Konu:** Value categories: lvalue / xvalue / prvalue / glvalue
**Neden Bu Aşamada?:** Move semantics ezberlenmeden önce expression identity ve temporary davranışı anlaşılmalı.
**Önkoşul:** references, expressions, move basics
**First-Principles Hedefi:** Expression'ın tipi dışında value category'si neden API overload ve move davranışını değiştirir?
**Kod Laboratuvarı:** decltype((expr)) ile farklı ifadeleri sınıflandır; overload set oluştur.
**Bilerek Boz / Failure:** Yanlış std::move ile moved-from nesneyi hatalı kullan.
**Ölçüm / Benchmark:** copy vs move count
**Savunma/Systems Bağlamı:** Zero-copy buffer ve ownership API tasarımı.

### CPP-003 (Gün 38) — S1 Core Language
**Konu:** Perfect forwarding ve forwarding references
**Neden Bu Aşamada?:** Value categories oturduktan sonra generic API'de copy/move semantiğini korumayı öğrenmek anlamlıdır.
**Önkoşul:** templates, value categories, std::move
**First-Principles Hedefi:** Wrapper fonksiyon neden argümanın lvalue/rvalue niteliğini kaybeder ve std::forward neyi korur?
**Kod Laboratuvarı:** Factory/wrapper API: T&& + std::forward; overload counters.
**Bilerek Boz / Failure:** Her yerde std::move kullanarak lvalue semantiğini boz.
**Ölçüm / Benchmark:** copy/move/alloc count
**Savunma/Systems Bağlamı:** Generic middleware adapter ve message factory.

### CPP-004 (Gün 42) — S1 Core Language
**Konu:** Variadic templates ve fold expressions
**Neden Bu Aşamada?:** Template temeli sonrası heterojen/generic instrumentation ve compile-time yardımcılar için.
**Önkoşul:** function/class templates
**First-Principles Hedefi:** Parameter pack birden çok type/value'yu compile time'da nasıl temsil eder?
**Kod Laboratuvarı:** Variadic logger / static validation helper.
**Bilerek Boz / Failure:** Empty pack veya yanlış fold identity vakası.
**Ölçüm / Benchmark:** compile time + generated code size
**Savunma/Systems Bağlamı:** Typed logging/telemetry helpers.

### CPP-005 (Gün 46) — S1 Core Language
**Konu:** Type traits, SFINAE ve modern replacement'ları
**Neden Bu Aşamada?:** Generic code'un hangi type'larla geçerli olduğunun compile-time kontrolünü anlamak için.
**Önkoşul:** templates, overload resolution
**First-Principles Hedefi:** Bir template'in bazı type'lar için overload set'ten çıkarılması nasıl çalışır; concepts neden daha okunur?
**Kod Laboratuvarı:** enable_if/type_traits ile parser overload; sonra concept ile yeniden yaz.
**Bilerek Boz / Failure:** Ambiguous overload ve kötü error message üret.
**Ölçüm / Benchmark:** compile diagnostics readability
**Savunma/Systems Bağlamı:** Generic serialization ve device adapter API.

### CPP-006 (Gün 50) — S1 Core Language
**Konu:** Concepts ve constraints derin kullanım
**Neden Bu Aşamada?:** Template/SFINAE görüldükten sonra C++20'ın type contract mekanizmasını gerçek API'de kullanmak gerekir.
**Önkoşul:** templates, type traits
**First-Principles Hedefi:** Generic API'nin kabul ettiği type özellikleri declaration üzerinde nasıl ifade edilir?
**Kod Laboratuvarı:** Serializable / Sensor concept yaz; compile-time negative tests.
**Bilerek Boz / Failure:** Aşırı sıkı veya çok gevşek concept tasarla.
**Ölçüm / Benchmark:** diagnostic quality / compile checks
**Savunma/Systems Bağlamı:** Protocol/device interfaces.

### CPP-007 (Gün 54) — S1 Core Language
**Konu:** constexpr / consteval / constinit
**Neden Bu Aşamada?:** Runtime ve compile-time hesap ayrımını template/concepts sonrasında görmek daha anlamlıdır.
**Önkoşul:** const, functions, templates
**First-Principles Hedefi:** Hangi hesap compile time'a taşınabilir; consteval neden zorunlu compile-time çağrıdır; constinit neyi garanti eder?
**Kod Laboratuvarı:** CRC lookup table / protocol constants compile-time üret.
**Bilerek Boz / Failure:** Runtime bağımlı değeri consteval'e sok; static init order riskini incele.
**Ölçüm / Benchmark:** runtime vs compile-time / binary size
**Savunma/Systems Bağlamı:** Protocol constants, lookup tables, embedded config.

### CPP-008 (Gün 58) — S1 Core Language
**Konu:** Ranges ve views
**Neden Bu Aşamada?:** STL algorithms ve lambda görüldükten sonra composable lazy data pipeline yaklaşımını öğrenmek için.
**Önkoşul:** STL algorithms, iterators, lambda
**First-Principles Hedefi:** Container kopyalamadan filter/transform pipeline nasıl ifade edilir?
**Kod Laboratuvarı:** Telemetry samples üzerinde filter→transform→take view.
**Bilerek Boz / Failure:** Dangling view / invalid source lifetime vakası.
**Ölçüm / Benchmark:** allocation count + readability
**Savunma/Systems Bağlamı:** Telemetry preprocessing / logs.

### CPP-009 (Gün 62) — S1 Core Language
**Konu:** Exception safety guarantees ve noexcept
**Neden Bu Aşamada?:** RAII oturduktan sonra error path'te invariant ve rollback davranışı tasarlanabilir.
**Önkoşul:** RAII, exceptions, move
**First-Principles Hedefi:** Basic/strong/nothrow guarantee neyi ifade eder; noexcept move container davranışını nasıl etkiler?
**Kod Laboratuvarı:** Transactional config update; throwing constructor tests.
**Bilerek Boz / Failure:** Mid-update exception ile partial state üret.
**Ölçüm / Benchmark:** rollback correctness / move behavior
**Savunma/Systems Bağlamı:** Mission config / resource management.

### CPP-010 (Gün 66) — S1 Core Language
**Konu:** Object model: alignment, padding, standard layout, vtable sezgisi
**Neden Bu Aşamada?:** Class/polymorphism sonrası bellekte gerçek temsil ve binary protocol sınırını ayırmak gerekir.
**Önkoşul:** class, inheritance, pointer, sizeof
**First-Principles Hedefi:** C++ object representation neden wire format değildir; padding/alignment neden oluşur?
**Kod Laboratuvarı:** sizeof/alignof/offsetof lab; struct layout karşılaştır.
**Bilerek Boz / Failure:** Native struct'ı doğrudan UDP'ye serialize et ve portability sorununu göster.
**Ölçüm / Benchmark:** size/padding/cache footprint
**Savunma/Systems Bağlamı:** Binary protocol, shared memory, embedded registers.

### CPP-011 (Gün 70) — S1 Core Language
**Konu:** Advanced STL: complexity, iterator/reference invalidation
**Neden Bu Aşamada?:** Vector/string/map kullanmak yeterli değildir; mutation'ın iterator/pointer geçerliliğine etkisi bilinmelidir.
**Önkoşul:** containers, iterators
**First-Principles Hedefi:** Container operasyonu hangi referans/iterator'ları bozar ve complexity garantisi neden mimari karardır?
**Kod Laboratuvarı:** vector reallocation invalidation; deque/map comparison.
**Bilerek Boz / Failure:** Invalid iterator kullan; sanitizer/debug iterator ile yakala.
**Ölçüm / Benchmark:** allocation/reallocation + complexity
**Savunma/Systems Bağlamı:** Queue/state containers.

### CPP-012 (Gün 74) — S1 Core Language
**Konu:** CRTP ve compile-time polymorphism
**Neden Bu Aşamada?:** Runtime virtual dispatch görüldükten sonra static polymorphism trade-off'u anlaşılır.
**Önkoşul:** templates, inheritance, polymorphism
**First-Principles Hedefi:** Runtime vtable olmadan interface reuse nasıl sağlanır; bunun coupling/code-size maliyeti nedir?
**Kod Laboratuvarı:** Static sensor adapter interface CRTP.
**Bilerek Boz / Failure:** Wrong derived contract / code bloat.
**Ölçüm / Benchmark:** binary size / call overhead
**Savunma/Systems Bağlamı:** Embedded driver abstraction.

### CPP-013 (Gün 82) — S2 Systems C++
**Konu:** ABI, name mangling ve calling convention sezgisi
**Neden Bu Aşamada?:** Linux/shared-library aşamasında source uyumu ile binary uyum farkı görünür hale gelir.
**Önkoşul:** compiler/linker, functions, classes
**First-Principles Hedefi:** C++ symbol neden mangled olur; binary boundary'de compiler/standard-library seçimi neden önemlidir?
**Kod Laboratuvarı:** nm/c++filt ile symbol inspection; C API wrapper karşılaştır.
**Bilerek Boz / Failure:** İmza değiştirip eski binary'yi kır.
**Ölçüm / Benchmark:** symbol diff / binary compatibility
**Savunma/Systems Bağlamı:** Plugin, SDK ve long-lived defense software.

### CPP-014 (Gün 86) — S2 Systems C++
**Konu:** Static/shared library, linker ve symbol visibility
**Neden Bu Aşamada?:** POSIX/Linux uygulamalarında modüler C++ deployment için.
**Önkoşul:** object files, linker, ABI
**First-Principles Hedefi:** Link-time ve run-time symbol resolution nasıl ayrılır; visibility neden API yüzeyini küçültür?
**Kod Laboratuvarı:** libtelemetry.so + executable; hidden/default visibility.
**Bilerek Boz / Failure:** Missing symbol / wrong SONAME.
**Ölçüm / Benchmark:** binary size / exported symbol count
**Savunma/Systems Bağlamı:** Reusable subsystem libraries.

### CPP-015 (Gün 90) — S2 Systems C++
**Konu:** CMake ileri: presets, install, export, package
**Neden Bu Aşamada?:** Birden çok repo/CI/build type için reproducible build gereklidir.
**Önkoşul:** targets, build types, libraries
**First-Principles Hedefi:** Build tree ile install/package tree nasıl ayrılır; consumer projeye target nasıl export edilir?
**Kod Laboratuvarı:** Installable telemetry library + CMake package config.
**Bilerek Boz / Failure:** Absolute include path / global flags ile portability boz.
**Ölçüm / Benchmark:** fresh build/install/consumer time
**Savunma/Systems Bağlamı:** Production C++ repository hygiene.

### CPP-016 (Gün 94) — S2 Systems C++
**Konu:** Dependency management: Conan/vcpkg zihinsel modeli
**Neden Bu Aşamada?:** Third-party C++ bağımlılıklarında sürüm, binary ve transitive dependency yönetimi gerekir.
**Önkoşul:** CMake, libraries
**First-Principles Hedefi:** Dependency graph nasıl reproducible ve platform-aware tutulur?
**Kod Laboratuvarı:** Small library dependency via Conan veya vcpkg; lock/version note.
**Bilerek Boz / Failure:** Unpinned dependency ile reproducibility boz.
**Ölçüm / Benchmark:** clean setup time
**Savunma/Systems Bağlamı:** MAVSDK/FastDDS/test libs integration.

### CPP-017 (Gün 102) — S2 Systems C++
**Konu:** API vs ABI stability
**Neden Bu Aşamada?:** Daemon/library sınırları görülünce interface evolution problemini öğrenmek anlamlıdır.
**Önkoşul:** ABI, shared libraries, semantic versioning
**First-Principles Hedefi:** Header/API değişmeden ABI nasıl kırılabilir; pImpl neyi azaltır?
**Kod Laboratuvarı:** v1/v2 shared lib compatibility experiment.
**Bilerek Boz / Failure:** Class member ekleyip client binary compatibility boz.
**Ölçüm / Benchmark:** ABI diff / rebuild requirement
**Savunma/Systems Bağlamı:** Long-lived subsystem interfaces.

### CPP-018 (Gün 112) — S2 Systems C++
**Konu:** Atomics ve memory model derinliği
**Neden Bu Aşamada?:** Thread/mutex temeli sonrası lock-free tasarıma geçmeden happens-before anlaşılmalıdır.
**Önkoşul:** threads, atomics basics
**First-Principles Hedefi:** Atomicity ile visibility/order neden farklıdır; happens-before nasıl kurulur?
**Kod Laboratuvarı:** release/acquire message passing; relaxed counter.
**Bilerek Boz / Failure:** Yanlış relaxed synchronization ile invariant boz.
**Ölçüm / Benchmark:** ops/s + TSan + correctness
**Savunma/Systems Bağlamı:** High-rate telemetry counters/state.

### CPP-019 (Gün 116) — S2 Systems C++
**Konu:** Lock-free SPSC / bounded MPMC yapılarına giriş
**Neden Bu Aşamada?:** Queue/backpressure görüldükten sonra lock contention trade-off'unu ölçmek için.
**Önkoşul:** atomics, cache, bounded queue
**First-Principles Hedefi:** Lock-free ilerleme garantisi ne demektir; neden her zaman daha hızlı değildir?
**Kod Laboratuvarı:** Mutex queue vs SPSC ring benchmark.
**Bilerek Boz / Failure:** ABA/overflow/incorrect wrap logic vakası.
**Ölçüm / Benchmark:** throughput + p99 + CPU
**Savunma/Systems Bağlamı:** Sensor/telemetry pipelines.

### CPP-020 (Gün 120) — S2 Systems C++
**Konu:** Cache locality, false sharing ve data layout
**Neden Bu Aşamada?:** Multithread benchmark sonrası CPU cache davranışı gerçek performans nedeni olarak görünür.
**Önkoşul:** cache, atomics, structs
**First-Principles Hedefi:** Contiguous data ve cache line paylaşımı latency'yi nasıl etkiler?
**Kod Laboratuvarı:** Padded counters; AoS vs SoA microbenchmark.
**Bilerek Boz / Failure:** False sharing'i bilinçli üret.
**Ölçüm / Benchmark:** cycles/item, cache misses
**Savunma/Systems Bağlamı:** CV/radar/telemetry hot paths.

### CPP-021 (Gün 136) — S2 Systems C++
**Konu:** Async I/O mimarisi: epoll ve Boost.Asio
**Neden Bu Aşamada?:** Socket temeli görüldükten sonra thread-per-connection yerine event-driven I/O öğrenilir.
**Önkoşul:** Linux fd, TCP/UDP, callbacks
**First-Principles Hedefi:** Kernel readiness notification ile application async state machine nasıl kurulur?
**Kod Laboratuvarı:** epoll UDP/TCP server; sonra Asio version.
**Bilerek Boz / Failure:** Callback lifetime/use-after-free; cancellation race.
**Ölçüm / Benchmark:** connections/s + p99 + CPU
**Savunma/Systems Bağlamı:** Telemetry gateway/network services.

### CPP-022 (Gün 148) — S2 Systems C++
**Konu:** Robust binary parsing ve serialization architecture
**Neden Bu Aşamada?:** Protocol/framing sonrası untrusted bytes için bounds/validation merkezli parser tasarımı gerekir.
**Önkoşul:** span, endian, protocol, CRC
**First-Principles Hedefi:** Parser input'a güvenmez; length/overflow/version/endianness nasıl doğrulanır?
**Kod Laboratuvarı:** span-based zero-copy parser + fuzz corpus.
**Bilerek Boz / Failure:** Truncated/oversized/malformed frames.
**Ölçüm / Benchmark:** msgs/s + allocation count + fuzz findings
**Savunma/Systems Bağlamı:** MAVLink/telemetry/custom protocol safety.

### CPP-023 (Gün 154) — S2 Systems C++
**Konu:** Property-based testing ve fuzz testing
**Neden Bu Aşamada?:** Parser/network layer artık yeterince karmaşık olduğunda hand-written case'lerin ötesine geçilir.
**Önkoşul:** unit tests, parser
**First-Principles Hedefi:** Test örnekleri yerine invariant üretmek ve random input ile state space taramak ne kazandırır?
**Kod Laboratuvarı:** Round-trip serialization property + libFuzzer parser target.
**Bilerek Boz / Failure:** Crash/hang/UB corpus üret.
**Ölçüm / Benchmark:** exec/s + unique crashes + coverage
**Savunma/Systems Bağlamı:** Protocol hardening.

### CPP-024 (Gün 158) — S2 Systems C++
**Konu:** Static analysis ve clang-tidy/Clang Static Analyzer
**Neden Bu Aşamada?:** Dynamic testlerin erişemediği code path ve suspicious pattern'ları derleme öncesi yakalamak için.
**Önkoşul:** C++ codebase, warnings
**First-Principles Hedefi:** Path-sensitive analysis hangi bug sınıflarını bulur; false positive nasıl yönetilir?
**Kod Laboratuvarı:** scan-build/clang-tidy CI gate.
**Bilerek Boz / Failure:** Intentional null/resource bug.
**Ölçüm / Benchmark:** findings count / false-positive triage
**Savunma/Systems Bağlamı:** Defense-style quality gates.

### CPP-025 (Gün 166) — S3 Embedded/Robotics C++
**Konu:** Cross-compilation ve CMake toolchain files
**Neden Bu Aşamada?:** STM32/ARM fazına geçildiğinde host compiler ile target compiler ayrımı zorunlu hale gelir.
**Önkoşul:** CMake, compiler/linker, architecture
**First-Principles Hedefi:** Host'ta build etmek ile target için code üretmek nasıl ayrılır?
**Kod Laboratuvarı:** Minimal ARM cross-compiled static library / firmware target.
**Bilerek Boz / Failure:** Host header/lib accidentally link et.
**Ölçüm / Benchmark:** build reproducibility / binary size
**Savunma/Systems Bağlamı:** STM32/ARM deploy.

### CPP-026 (Gün 170) — S3 Embedded/Robotics C++
**Konu:** Embedded C++ restrictions ve freestanding zihniyeti
**Neden Bu Aşamada?:** MCU'da heap, exceptions, RTTI ve OS varsayımları maliyetli/uygunsuz olabilir.
**Önkoşul:** C++ core, MCU, linker
**First-Principles Hedefi:** Hosted C++ ile freestanding/embedded environment hangi varsayımlarda ayrılır?
**Kod Laboratuvarı:** No-exception/no-RTTI small target build; fixed-capacity container.
**Bilerek Boz / Failure:** Dynamic allocation failure / exception unavailable path.
**Ölçüm / Benchmark:** flash/RAM / binary size
**Savunma/Systems Bağlamı:** Avionics firmware.

### CPP-027 (Gün 176) — S3 Embedded/Robotics C++
**Konu:** Deterministic allocation ve no-heap regions
**Neden Bu Aşamada?:** Real-time task ve embedded hot path'te unpredictable allocation latency'sini kontrol etmek gerekir.
**Önkoşul:** heap, RTOS, latency
**First-Principles Hedefi:** Allocation ne zaman ve nerede yapılırsa deadline jitter azaltılır?
**Kod Laboratuvarı:** Preallocated message pool; runtime allocation counter.
**Bilerek Boz / Failure:** Hot loop içinde allocation aç ve jitter ölç.
**Ölçüm / Benchmark:** p99 latency + allocations
**Savunma/Systems Bağlamı:** RTOS/mission hot paths.

### CPP-028 (Gün 180) — S3 Embedded/Robotics C++
**Konu:** std::pmr ve polymorphic memory resources
**Neden Bu Aşamada?:** Allocator problemi görüldükten sonra memory strategy'yi container API'den ayırmayı öğrenmek için.
**Önkoşul:** allocators, STL containers
**First-Principles Hedefi:** Container type'ını değiştirmeden allocation policy nasıl değiştirilebilir?
**Kod Laboratuvarı:** monotonic_buffer_resource ile telemetry batch.
**Bilerek Boz / Failure:** Buffer exhaustion / upstream resource behavior.
**Ölçüm / Benchmark:** allocation count + latency
**Savunma/Systems Bağlamı:** Bounded telemetry/message processing.

### CPP-029 (Gün 184) — S3 Embedded/Robotics C++
**Konu:** Arena/pool allocator ve custom memory management
**Neden Bu Aşamada?:** pmr sonrası gerçek fixed-pool davranışı ve fragmentation trade-off'u görülür.
**Önkoşul:** alignment, allocation, pmr
**First-Principles Hedefi:** General heap yerine workload-specific allocator ne kazandırır/ne kaybettirir?
**Kod Laboratuvarı:** Fixed-block pool for messages.
**Bilerek Boz / Failure:** Double free / alignment error / pool exhaustion.
**Ölçüm / Benchmark:** alloc/free latency + fragmentation proxy
**Savunma/Systems Bağlamı:** Embedded/network message pools.

### CPP-030 (Gün 204) — S3 Embedded/Robotics C++
**Konu:** C++ interface tasarımı: ROS2/DDS adapter boundaries
**Neden Bu Aşamada?:** DDS/ROS2 ile framework type'larını domain logic'ten ayırmak büyük codebase için kritik hale gelir.
**Önkoşul:** interfaces, templates, DDS/ROS2
**First-Principles Hedefi:** Domain model neden middleware message type'ına doğrudan bağımlı olmamalı?
**Kod Laboratuvarı:** Domain VehicleState + ROS2/DDS adapters.
**Bilerek Boz / Failure:** Core library'yi rclcpp type'larıyla kirlet.
**Ölçüm / Benchmark:** rebuild dependency / test isolation
**Savunma/Systems Bağlamı:** Reusable autonomy subsystem.

### CPP-031 (Gün 214) — S3 Embedded/Robotics C++
**Konu:** Coroutines: state machine ve async abstraction
**Neden Bu Aşamada?:** Event-driven/network/robot callbacks görüldükten sonra coroutine'in hangi problemi çözdüğü anlaşılır.
**Önkoşul:** callbacks, state machines, lifetime
**First-Principles Hedefi:** Coroutine compiler tarafından hangi state machine'e dönüşür; lifetime/cancellation neden kritik?
**Kod Laboratuvarı:** Small task coroutine / async timer abstraction.
**Bilerek Boz / Failure:** Dangling coroutine frame / forgotten cancellation.
**Ölçüm / Benchmark:** allocation + scheduling overhead
**Savunma/Systems Bağlamı:** Async mission/network orchestration.

### CPP-032 (Gün 238) — S3 Embedded/Robotics C++
**Konu:** Real-time-ish latency engineering in C++
**Neden Bu Aşamada?:** PX4/MAVLink ve simulator pipeline'da end-to-end deadline düşüncesi artık somutlaşmıştır.
**Önkoşul:** threads, memory, network, allocation
**First-Principles Hedefi:** Worst-tail latency'yi hangi C++ kararları büyütür: allocation, locks, cache misses, I/O?
**Kod Laboratuvarı:** Telemetry pipeline latency budget instrumentation.
**Bilerek Boz / Failure:** Allocation/lock contention inject et.
**Ölçüm / Benchmark:** p50/p95/p99/max + CPU
**Savunma/Systems Bağlamı:** Mission telemetry/control support.

### CPP-033 (Gün 250) — S4 Performance/Numerical
**Konu:** AoS vs SoA ve data-oriented design
**Neden Bu Aşamada?:** Image/radar/numerical workload'a geçince data layout CPU/GPU throughput için belirginleşir.
**Önkoşul:** cache locality, structs, vectors
**First-Principles Hedefi:** Kod hiyerarşisi değil data access pattern performansı nasıl belirler?
**Kod Laboratuvarı:** Point/track array AoS vs SoA processing.
**Bilerek Boz / Failure:** Pointer-rich layout ve random access.
**Ölçüm / Benchmark:** cache misses + throughput
**Savunma/Systems Bağlamı:** Tracking/radar/CV metadata.

### CPP-034 (Gün 256) — S4 Performance/Numerical
**Konu:** SIMD / vectorization
**Neden Bu Aşamada?:** Contiguous numerical loops görüldüğünde CPU vector units kullanımı anlamlı hale gelir.
**Önkoşul:** arrays, loops, compiler optimization
**First-Principles Hedefi:** Bir instruction ile birden çok data lane işlemek hangi koşullarda mümkün?
**Kod Laboratuvarı:** Scalar vs auto-vectorized numerical kernel; compiler vector report.
**Bilerek Boz / Failure:** Aliasing/alignment ile vectorization engelle.
**Ölçüm / Benchmark:** ns/item / GB/s
**Savunma/Systems Bağlamı:** DSP/CV preprocessing.

### CPP-035 (Gün 262) — S4 Performance/Numerical
**Konu:** Branch prediction ve branchless trade-off
**Neden Bu Aşamada?:** Hot loops/filters artık ölçülebilir olduğunda control-flow maliyeti incelenebilir.
**Önkoşul:** CPU pipeline, conditionals, perf
**First-Principles Hedefi:** Unpredictable branch pipeline'ı neden yavaşlatabilir; branchless kod neden her zaman iyi değildir?
**Kod Laboratuvarı:** Predictable/random branch benchmark.
**Bilerek Boz / Failure:** Branchless dönüşümü gereksiz yap ve performansı düşür.
**Ölçüm / Benchmark:** branch-misses + cycles
**Savunma/Systems Bağlamı:** Signal/CV hot paths.

### CPP-036 (Gün 268) — S4 Performance/Numerical
**Konu:** Compiler optimizations ve generated assembly okuma
**Neden Bu Aşamada?:** Performance iddiasını kaynak kod sezgisi yerine compiler output ile doğrulamak için.
**Önkoşul:** C++/compiler/CPU basics
**First-Principles Hedefi:** Optimizer hangi abstraction'ları silebilir; hangi pointer/aliasing koşulları engel olur?
**Kod Laboratuvarı:** -O0/-O2/-O3 assembly karşılaştır; Compiler Explorer benzeri local objdump.
**Bilerek Boz / Failure:** UB'ye dayanan 'optimization' varsayımı.
**Ölçüm / Benchmark:** instruction count / runtime
**Savunma/Systems Bağlamı:** Hot loop optimization.

### CPP-037 (Gün 274) — S4 Performance/Numerical
**Konu:** LTO ve PGO
**Neden Bu Aşamada?:** Birden çok translation unit ve gerçek workload benchmark'ı varken whole-program/profile guided optimization anlamlıdır.
**Önkoşul:** release builds, benchmark
**First-Principles Hedefi:** Link-time visibility ve runtime profile compiler'a hangi ek bilgiyi verir?
**Kod Laboratuvarı:** Baseline vs LTO vs PGO benchmark.
**Bilerek Boz / Failure:** Training profile'i yanlış workload'dan üret.
**Ölçüm / Benchmark:** binary size + p99 + throughput
**Savunma/Systems Bağlamı:** Deployment optimization.

### CPP-038 (Gün 282) — S4 Performance/Numerical
**Konu:** Profiling ve flamegraph metodolojisi
**Neden Bu Aşamada?:** Control/CV workload'unda optimize edilmesi gereken yer ölçümle seçilmelidir.
**Önkoşul:** perf, symbols, release/debug info
**First-Principles Hedefi:** Wall time nereye gidiyor; sampling profiler neyi ölçer ve neyi ölçmez?
**Kod Laboratuvarı:** perf record/report; flamegraph benzeri call stack visualization.
**Bilerek Boz / Failure:** Microbenchmark sonucuyla tüm sistemi yanlış optimize et.
**Ölçüm / Benchmark:** CPU samples / hotspots
**Savunma/Systems Bağlamı:** CV/control/radar pipeline.

### CPP-039 (Gün 300) — S4 Performance/Numerical
**Konu:** Numerical robustness in C++
**Neden Bu Aşamada?:** Radar/DSP fazında floating-point comparison, precision ve overflow gerçek correctness konusu olur.
**Önkoşul:** floating point, DSP math
**First-Principles Hedefi:** Floating point real sayı değildir; precision/range/error accumulation nasıl yönetilir?
**Kod Laboratuvarı:** float vs double FFT/filter metric comparison; epsilon-aware tests.
**Bilerek Boz / Failure:** Exact equality ve overflow üret.
**Ölçüm / Benchmark:** error vs runtime
**Savunma/Systems Bağlamı:** DSP/radar/control numerical code.

### CPP-040 (Gün 310) — S4 Performance/Numerical
**Konu:** Zero-copy buffer ownership across C++ CV/media boundaries
**Neden Bu Aşamada?:** OpenCV/GStreamer/TensorRT gibi farklı runtime'lar arasında frame copy maliyeti artık kritik hale gelir.
**Önkoşul:** RAII, spans, image buffers, lifetime
**First-Principles Hedefi:** Buffer'ı kim allocate/free eder; view ne kadar yaşar; copy hangi sınırda gerçekten gereklidir?
**Kod Laboratuvarı:** Frame buffer wrapper + view adapters; copy counter.
**Bilerek Boz / Failure:** Use-after-free/double ownership.
**Ölçüm / Benchmark:** copies/frame + latency
**Savunma/Systems Bağlamı:** Production CV/video.

### CPP-041 (Gün 320) — S5 Architecture/Hardening
**Konu:** Design patterns as trade-offs: Strategy/Adapter/State/Observer
**Neden Bu Aşamada?:** Birden çok gerçek subsystem görüldükten sonra pattern isimlerini değil değişim eksenlerini anlamak gerekir.
**Önkoşul:** interfaces, composition, state machines
**First-Principles Hedefi:** Pattern hangi coupling/dependency/değişim problemini çözer; ne zaman overengineering olur?
**Kod Laboratuvarı:** P1 adapter + state machine refactor.
**Bilerek Boz / Failure:** Pattern-everywhere anti-pattern oluştur.
**Ölçüm / Benchmark:** test isolation / dependency count
**Savunma/Systems Bağlamı:** Mission/middleware/test architecture.

### CPP-042 (Gün 326) — S5 Architecture/Hardening
**Konu:** Large-scale C++ codebase organization
**Neden Bu Aşamada?:** Verification ve distributed fazında repository/component sınırları artık kritik hale gelir.
**Önkoşul:** CMake, interfaces, libraries, tests
**First-Principles Hedefi:** Source tree component boundaries dependency graph'ı nasıl etkiler?
**Kod Laboratuvarı:** Apps/libs/adapters/tests split; dependency direction check.
**Bilerek Boz / Failure:** Circular dependency oluştur.
**Ölçüm / Benchmark:** incremental build / dependency graph
**Savunma/Systems Bağlamı:** Defense-scale modular codebase.

### CPP-043 (Gün 332) — S5 Architecture/Hardening
**Konu:** Coding standard ve code review pratiği
**Neden Bu Aşamada?:** Kalite artık bireysel kod değil ekipte sürdürülebilirlik problemidir.
**Önkoşul:** C++ quality tooling, architecture
**First-Principles Hedefi:** Review'da style değil correctness/ownership/concurrency/API/test riskleri nasıl önceliklenir?
**Kod Laboratuvarı:** PR checklist + deliberate buggy change review.
**Bilerek Boz / Failure:** Style-only review ile concurrency bug kaçır.
**Ölçüm / Benchmark:** review findings / escaped defects
**Savunma/Systems Bağlamı:** Team-grade engineering evidence.

### CPP-044 (Gün 338) — S5 Architecture/Hardening
**Konu:** C++ modules: amaç, sınırlar ve build gerçekliği
**Neden Bu Aşamada?:** Header/include/linker problemlerini yaşadıktan sonra modules'ın hangi problemi hedeflediği anlaşılır.
**Önkoşul:** translation units, templates, build systems
**First-Principles Hedefi:** Textual inclusion yerine module interface neyi değiştirir; toolchain portability durumu neden değerlendirilmelidir?
**Kod Laboratuvarı:** Small module interface experiment supported toolchain'de.
**Bilerek Boz / Failure:** Toolchain/build portability assumption.
**Ölçüm / Benchmark:** build time / compatibility
**Savunma/Systems Bağlamı:** Future-facing large C++ codebase.

### CPP-045 (Gün 344) — S5 Architecture/Hardening
**Konu:** Compile-time vs runtime polymorphism final trade-off
**Neden Bu Aşamada?:** CRTP/concepts/virtual interfaces artık gerçek project evidence ile kıyaslanabilir.
**Önkoşul:** CRTP, concepts, vtable, code size
**First-Principles Hedefi:** Virtual dispatch, templates/concepts ve type erasure arasında extension/build-size/runtime trade-off'u nedir?
**Kod Laboratuvarı:** Three implementations of Sensor/Transport interface.
**Bilerek Boz / Failure:** Template code bloat vs virtual coupling.
**Ölçüm / Benchmark:** binary size + dispatch benchmark
**Savunma/Systems Bağlamı:** Driver/middleware/plugin boundaries.

### CPP-046 (Gün 350) — S5 Architecture/Hardening
**Konu:** API design: ownership, nullability, errors, units ve strong types
**Neden Bu Aşamada?:** Public subsystem API artık diğer projelerce tüketileceği için yanlış kullanım zorlaştırılmalıdır.
**Önkoşul:** RAII, optional/expected mindset, concepts
**First-Principles Hedefi:** İyi API caller'ın illegal state üretmesini nasıl zorlaştırır?
**Kod Laboratuvarı:** Strong types for meters/ms/SystemId; explicit ownership API.
**Bilerek Boz / Failure:** Raw int/string ile unit/id mixup üret.
**Ölçüm / Benchmark:** compile-time rejected misuse
**Savunma/Systems Bağlamı:** Safety-relevant interfaces.

### CPP-047 (Gün 354) — S5 Architecture/Hardening
**Konu:** Fuzzing + sanitizer + static analysis combined quality gate
**Neden Bu Aşamada?:** Final projelerde tek test tekniği yerine defense-in-depth kalite hattı kurulmalıdır.
**Önkoşul:** ASan/UBSan/TSan, libFuzzer, static analyzer
**First-Principles Hedefi:** Dynamic instrumentation, random exploration ve symbolic/static analysis hangi farklı bug sınıflarını hedefler?
**Kod Laboratuvarı:** CI pipeline: unit→sanitizers→fuzz smoke→static analysis.
**Bilerek Boz / Failure:** Bir gate'i kapatıp intentional bug'ın kaçtığını göster.
**Ölçüm / Benchmark:** findings / time / false positives
**Savunma/Systems Bağlamı:** Release hardening.

### CPP-048 (Gün 358) — S5 Architecture/Hardening
**Konu:** Benchmark engineering for C++
**Neden Bu Aşamada?:** Final performans iddiaları microbenchmark hatalarına düşmeden sunulmalıdır.
**Önkoşul:** chrono, perf, compiler optimization, statistics
**First-Principles Hedefi:** Warmup, dead-code elimination, CPU frequency, input distribution ve percentile neden önemlidir?
**Kod Laboratuvarı:** Microbenchmark harness; black-box result use; repeated distributions.
**Bilerek Boz / Failure:** Optimizer tüm işi silsin / tek run ölç.
**Ölçüm / Benchmark:** median/p95/confidence spread
**Savunma/Systems Bağlamı:** Recruiter-facing measurable claims.

### CPP-049 (Gün 362) — S5 Architecture/Hardening
**Konu:** Final C++ subsystem library: versioned, tested, packaged
**Neden Bu Aşamada?:** Yıl boyunca öğrenilen dil/build/quality kavramlarını tek reusable artefact'ta birleştirmek için.
**Önkoşul:** S1-S5 tamamı
**First-Principles Hedefi:** Bir production C++ component'in source dışındaki kalite özellikleri nelerdir?
**Kod Laboratuvarı:** Telemetry/common library: API, CMake package, tests, sanitizer, docs, benchmark.
**Bilerek Boz / Failure:** ABI-breaking change + rollback/versioning exercise.
**Ölçüm / Benchmark:** build/test/benchmark/ABI matrix
**Savunma/Systems Bağlamı:** P1/P9/P10 reusable core.

### CPP-050 (Gün 365) — S5 Architecture/Hardening
**Konu:** C++ mastery defense review
**Neden Bu Aşamada?:** Final gün: syntax değil production systems yeterliliğini kanıtlamak için.
**Önkoşul:** Tüm mastery spine
**First-Principles Hedefi:** C++ kararlarını ownership→memory→generic→concurrency→OS/network→embedded→performance→quality→architecture zincirinde savunabilir misin?
**Kod Laboratuvarı:** 90 dk closed-notes implementation + 30 dk design review + bug hunt.
**Bilerek Boz / Failure:** Deliberate race/UB/API/ABI/performance bug setini teşhis et.
**Ölçüm / Benchmark:** correctness + p99 + diagnostics
**Savunma/Systems Bağlamı:** ASELSAN/HAVELSAN systems profile final evidence.

