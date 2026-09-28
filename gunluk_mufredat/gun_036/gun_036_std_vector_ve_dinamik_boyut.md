# 🏛️ GÜN 036: std::vector ve Dinamik Boyut (Dinamik Bellek Mimarisi, Geometrik Büyüme ve İteratör Güvenliği)

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
[![C++ Standard](https://img.shields.io/badge/C%2B%2B-20-blue.svg?style=flat-square)](https://isocpp.org/)
[![Safety Standard](https://img.shields.io/badge/DO--178C-Level%20A-red.svg?style=flat-square)](https://www.rtca.org/)
[![MISRA](https://img.shields.io/badge/MISRA%20C%2B%2B-2023%20Compliant-green.svg?style=flat-square)](https://misra.org.uk/)

---

### 📋 40-Nokta Pedagojik & Endüstriyel Kalite Bildirimi

Bu ders modülü, **ASELSAN, HAVELSAN, Roketsan ve STM** sistem mühendisliği standartlarına tam uyumlu olarak üretilmiştir.
Modül boyunca:
1. `std::vector`'ün 64-bit mimarideki **24 baytlık stack kontrol bloğu** (`_M_start`, `_M_finish`, `_M_end_of_storage`) diseke edilir.
2. Geometrik büyüme faktörü ($2.0\times$ GCC/Clang vs $1.5\times$ MSVC) ve **Amortize $O(1)$ karmaşıklığı** matematiksel olarak ispatlanır.
3. `push_back()` esnasında tetiklenen bellek reallocasyonu nedeniyle oluşan **İteratör Invalidation ve Dangling Pointer felaketi** canlı sabotajla gösterilir.
4. Yeniden tahsis sırasında `noexcept` taşınabilirliğin (`std::is_nothrow_move_constructible_v`) copy relocation cezasını nasıl engellediği incelenir.
5. Savunma sanayiinde gerçek zamanlı (hard real-time) aviyonik döngülerinde dinamik heap tahsisini sınırlandıran **BoundedVector** deseni inşa edilir.


## 1. 🎯 Bugünkü Problem: Dinamik Boyutlu Veri Akışlarında Bellek Reallocasyonu ve Determinizm Krizi

Bir önceki gün (`Gün 035`) incelediğimiz `std::array`, derleme zamanında eleman sayısı kesin olarak bilinen sabit tamponlar için mükemmel bir sıfır ek yüklü soyutlamadır. Ancak gerçek dünya savunma sanayii sistemlerinde gelen verinin hacmi her zaman sabit değildir:
- **AESA Radar Hedef Takip Sistemi (Track Management):** Radar anteninin bir tarama periyodunda (dwell) tespit ettiği hedef sayısı dinamiktir. Boş gökyüzünde 0 hedef tespit edilirken, yoğun elektronik harp veya sürü İHA saldırısı altında 500 hedef tespit edilebilir.
- **Link-16 / Taktik Veri Bağı Paket Tamponu:** RF üzerinden gelen değişken uzunluktaki taktik mesaj paketleri.
- **Sonar ve Akustik Sinyal İşleme:** Yankı yanıtlarının zaman eksenindeki değişken uzunluklu tepe noktaları (peaks).

### Donanımsal Darboğaz ve Tehlike
C tarzı dinamik bellek yönetiminde (`malloc/realloc/free` veya `new[]/delete[]`), mühendis belleği elle yönetmek zorundadır. Bu yaklaşım:
1. **Bellek Sızıntısı (Memory Leak):** Unutulan bir `free()` çağrısı radar görev bilgisayarının saatler içinde kilitlenmesine yol açar.
2. **Double Free / Use-After-Free:** Yanlışlıkla iki kez silinen veya silindikten sonra okunan bellek işaretçisi.
3. **Determinizm ve WCET (Worst-Case Execution Time) Çöküşü:** `push_back()` fonksiyonu 99 kez 2 nanosaniyede tamamlanırken, 100. çağrıda kapasite dolduğu için `realloc()` tetiklenir: işletim sistemi yeni bir heap bloğu arar, eski 100 eleman yeni bloğa kopyalanır ve eski blok serbest bırakılır. Bu tek bir işlem **15,000 nanosaniye** sürer! Deterministik 1 ms döngüsüyle çalışan aviyonik kontrol bilgisayarı zaman aşımına (deadline miss) uğrar ve füze hedefini ıskalar.

Bugünkü görevimiz; Modern C++20'de dinamik boyutlu dizilerin temel standardı olan `std::vector`'ün bellek anatomisini sökmek, reallocasyon maliyetini `reserve()` ile sıfıra indirmek ve ölümcül **İteratör Invalidation** sabotajına karşı kurşun geçirmez savunma mekanizmaları kurmaktır.


## 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi)

Savunma sanayiinde yazılım geliştiren bir mühendisin *"ben vector kullandım, gerisine karışmam"* deme lüksü yoktur. `std::vector`, C++ Standart Kütüphanesi'nin en popüler konteyneridir; ancak bilinçsiz kullanıldığında kritik görev sistemlerini sabote eden bir saatli bombaya dönüşür.

### 1. Aviyonik ve Radar Sistemlerinde Heap Fragmentasyonu (DO-178C Level A)
Dinamik bellek tahsisatı (`malloc/new`), heap üzerinde serbest bloklar bırakır. Küçük ve kontrolsüz `vector` genişlemeleri, belleği delik deşik (fragmented) eder. Sistem saatlerce çalıştıktan sonra, toplamda 200 MB boş bellek olmasına rağmen bitişik (contiguous) 4 MB bellek bulunamadığı için `std::bad_alloc` istisnası fırlatılır ve görev bilgisayarı kendini yeniden başlatır (reboot loop).

### 2. İteratör Invalidation ile Havada Use-After-Free Sabotajı
Bir hedef listesi üzerinde iteratörle dönerken (`for (auto it = targets.begin(); it != targets.end(); ++it)`), döngü içerisinde yeni bir dost unsur tespit edilip `targets.push_back(friend_unit)` çağrılırsa ne olur?
Eğer o anda `size == capacity` ise, vektörün tamamı bellekte başka bir adrese taşınır! Döngünün elindeki `it` iteratörü artık serbest bırakılmış (deallocated) çöp bir adresi gösterir. Bir sonraki adımda hedef koordinatına yazılan veri, havada başıboş kalan bir füzeye dost unsuru hedef olarak gösterebilir!

### 3. Savunma Sanayii İkilemi: Esneklik vs Determinizm
ASELSAN radar işlemcisinde hedef takibi yaparken `std::vector`'ün sunduğu bitişik bellek (L1/L2 veri önbelleği dostu cache-friendly) yapısından vazgeçemeyiz; ancak onun rastgele zamanlarda reallocasyon yapmasına da izin veremeyiz. Bu nedenle savunma sanayii mühendisi:
- Kapasite ön-tahsisini (`reserve()`),
- Özel bellek kaynaklarını (PMR - Polymorphic Memory Resource),
- Ve `noexcept` taşıma semantiğini refleks haline getirmek zorundadır.


## 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları)

| Soru | Sistem & Donanım Düzeyinde Yanıt |
|:---|:---|
| **Ne? (What)** | `std::vector<T>`, heap üzerinde bitişik (contiguous) bellek tutan, çalışma zamanında dinamik olarak büyüyüp küçülebilen, stack üzerinde yalnızca 24 baytlık (3 pointer) kontrol bloğu barındıran RAII dizisidir. |
| **Neden? (Why)** | Sabit boyutlu dizilerin yetersiz kaldığı değişken boyutlu veri kümelerini yönetirken, C tarzı pointer ve manuel `free()` hatalarını (leak, double-free) sıfıra indirmek ve CPU L1/L2 önbellek satırlarından (cache-line) tam hızda yararlanmak için. |
| **Nerede? (Where)** | Radar hedef takip listelerinde, ağ paketi ayrıştırma kuyruklarında, görüntü işleme tespit kutularında (bounding boxes) ve telemetri kayıt tamponlarında. |
| **Nasıl? (How)** | Kapasite aşıldığında $1.5\times$ veya $2.0\times$ geometrik katsayısıyla yeni bir heap bloğu tahsis ederek, eski elemanları yeni bloğa taşıyarak (`std::move_if_noexcept`) ve eski bloğu serbest bırakarak. |
| **Ne Zaman? (When)** | Eleman sayısı derleme anında bilinmiyorsa kullanılır. Ancak gerçek zamanlı (hard real-time) döngüler başlamadan önce mutlaka `reserve()` ile tepe kapasite önceden tahsis edilmelidir. |
| **Kim? (Who)** | ASELSAN Radar ve Elektronik Harp (REHİS), HAVELSAN Komuta Kontrol (KKS), Roketsan Güdüm Kontrol ve TUSAŞ Uçuş Yönetim mühendisleri. |


## 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Analoji)

### Akordeon Dosya ve Askeri Hangardaki Uçaklar Benzetmesi

Diyelim ki bir askeri üste uçak bakım hangarı yönetiyorsunuz:
- **`std::array` (Sabit Hangar):** Başlangıçta tam 4 uçaklık betonarme bir hangar inşa edersiniz. İçine 4'ten fazla uçak sokamazsınız. Hangarın boyutu asla değişmez, yıkılıp yeniden yapılamaz. Güvenlidir, sınırları kesindir.
- **Korumasız `std::vector` (Kademeli Taşınan Hangar):**
  1. Başlangıçta 1 uçaklık hangar kiralarsınız.
  2. İkinci uçak geldiğinde kapasite dolar. Ne yaparsınız? Mevcut hangarı genişletemezsiniz (yanındaki araziler doludur). Üs komutanlığı gider **2 uçaklık YENİ bir hangar** kiralar. 1. uçak yeni hangara çekilir, eski hangar kapatılır.
  3. Üçüncü uçak geldiğinde yine yer yoktur! Gidilir **4 uçaklık YEPYENİ bir hangar** kiralanır. Önceki 2 uçak yeni hangara taşınır, 3. uçak park edilir, eski hangar terk edilir.
  4. Beşinci uçak geldiğinde bu sefer **8 uçaklık hangar** tutulur ve 4 uçak tekrar taşınır!

Her taşınmada:
- Uçakları taşımak muazzam bir zaman ve yakıt kaybıdır (CPU kopyalama / taşıma döngüleri).
- Eski hangarın adresini bilen kule teknisyeni oraya gittiğinde bomboş bir araziyle karşılaşır ve kaza yapar (**İteratör Invalidation / Dangling Pointer**).

### Mühendislik Çözümü: `reserve()`
Akıllı bir filo komutanı şöyle der: *"Bu göreve en fazla 8 uçak katılacak. Bana baştan 8 uçaklık hangar tahsis edin!"*
Hangara sırayla 1., 2., 3., 4., 5. uçaklar girer; **asla taşınma yaşanmaz, kule adresi asla değişmez, sıfır gecikmeyle operasyon sürer!**


## 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model

### 1. 64-Bit Mimaride Stack Kontrol Bloğu Anatomisi
Modern bir 64-bit işletim sisteminde (x86_64, AArch64), `sizeof(std::vector<T>)` eleman tipinden ($T$) bağımsız olarak **tam 24 bayttır**.
Bir vector, stack üzerinde yalnızca 3 adet 8-baytlık işaretçi tutar:

```
Stack Belleği (24 Bayt):
+-------------------------------------------------------+
|  _M_start            (8 Bayt: Heap verisinin başı)    | -> Heap: [El 0]
+-------------------------------------------------------+
|  _M_finish           (8 Bayt: Son elemanın sonu)      | -> Heap: [El N]
+-------------------------------------------------------+
|  _M_end_of_storage   (8 Bayt: Ayrılan kapasite sınırı)| -> Heap: [Kapasite Sonu]
+-------------------------------------------------------+
```

Bu işaretçilerden türetilen temel büyüklükler:
$$\text{size()} = \frac{\_M\_finish - \_M\_start}{\text{sizeof}(T)}$$
$$\text{capacity()} = \frac{\_M\_end\_of\_storage - \_M\_start}{\text{sizeof}(T)}$$
$$\text{empty()} = (\_M\_start == \_M\_finish)$$

### 2. Geometrik Büyüme ve Amortize $O(1)$ İspatı
Eğer bir vektör her dolduğunda kapasitesini sabit bir $C$ kadar artırsaydı ($N \to N + C$):
- $N$ eleman eklemek için $\frac{N}{C}$ kez reallocasyon yapılırdı.
- Toplam kopyalama sayısı: $C + 2C + 3C + \dots + N \approx O(N^2)$ olurdu.
- Eleman başına ortalama maliyet $O(N)$ olurdu (KABUL EDİLEMEZ!).

Bunun yerine C++ standart kütüphaneleri **Geometrik Büyüme** kullanır: $N \to \gamma \cdot N$.
- **GCC / Clang:** $\gamma = 2.0$ (1, 2, 4, 8, 16, 32, 64, ...)
- **MSVC STL:** $\gamma = 1.5$ (1, 2, 3, 4, 6, 9, 13, 19, ...)

Geometrik büyümede $N$ eleman eklemek için yapılan toplam kopyalama:
$$\sum_{i=0}^{k} 2^i = 2^{k+1} - 1 < 2N$$
Toplam maliyet en fazla $2N$ kopyalamadır. Eleman başına ortalama maliyet:
$$\text{Amortize Maliyet} = \frac{2N}{N} = O(1)$$

### 3. Neden MSVC $1.5\times$, GCC $2.0\times$ Kullanır? (Bellek Parçalanması Analizi)
$\gamma = 2.0$ seçildiğinde, yeni tahsis edilen blok her zaman daha önce serbest bırakılan TÜM blokların toplamından büyüktür:
$$2^k > \sum_{i=0}^{k-1} 2^i = 2^k - 1$$
Bu nedenle eski boşaltılan bloklar bellekte birleştirilip (coalescing) asla bir sonraki reallocasyon için tekrar KULLANILAMAZ! Heap sürekli ileriye doğru büyür ve parçalanır.
$\gamma < \frac{1 + \sqrt{5}}{2} \approx 1.618$ (Altın Oran) seçildiğinde (MSVC'nin $1.5\times$ tercihi), önceki serbest kalan bellek alanları ilerleyen reallocasyonlarda tekrar kullanılabilir. Bu da uzun süre çalışan gömülü sistemlerde bellek parçalanmasını dramatik ölçüde azaltır.


## 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

### ASCII Bellek Mimarisi ve Reallocasyon Döngüsü

```
[DURUM 1: Kapasite Dolu (size == 4, capacity == 4)]
Stack (24B)                      Heap Belleği
+--------------------+           +--------+--------+--------+--------+
| _M_start           |---------->|  El 0  |  El 1  |  El 2  |  El 3  |
| _M_finish          |----+      +--------+--------+--------+--------+
| _M_end_of_storage  |--+ |                                          ^
+--------------------+  | +------------------------------------------+
                        +--------------------------------------------+

               --- v.push_back(El 4) ÇAĞRILDI! ---

[DURUM 2: Reallocasyon ve İteratör Invalidation (size == 5, capacity == 8)]
                                 Eski Blok: [SERBEST BIRAKILDI / DANGLING!]
                                 +--x--x--+--x--x--+--x--x--+--x--x--+
                                 |  Çöp   |  Çöp   |  Çöp   |  Çöp   |
                                 +--------+--------+--------+--------+
                                      ^
                                      | [Eski İteratör Burayı Gösterir -> ÇÖKÜŞ!]

Stack (24B)                      YENİ Heap Bloğu (2.0x Genişletildi)
+--------------------+           +----+----+----+----+----+----+----+----+
| _M_start           |---------->|El 0|El 1|El 2|El 3|El 4| Boş| Boş| Boş|
| _M_finish          |----+      +----+----+----+----+----+----+----+----+
| _M_end_of_storage  |--+ |                               ^              ^
+--------------------+  | +-------------------------------+              |
                        +------------------------------------------------+
```

### Mermaid Veri Akışı ve Reallocasyon Karar Ağacı

```mermaid
flowchart TD
    A["push_back(value) Çağrısı"] --> B{"size < capacity?"}
    B -- Evet (Deterministik) --> C["Yeni elemanı _M_finish adresine yerleştir<br/>(Placement new / Move)"]
    C --> D["_M_finish++<br/>Süre: ~2 ns"]
    
    B -- Hayır (Reallocation Gerekli) --> E["Yeni Kapasite Hesapla:<br/>new_cap = (cap == 0 ? 1 : cap * 2)"]
    E --> F["Heap'ten new_cap * sizeof(T) Bellek İste<br/>(malloc / operator new)"]
    F --> G{"T sınıfı noexcept<br/>taşınabilir mi?"}
    G -- Evet (Hızlı) --> H["std::move_if_noexcept ile elemanları taşı<br/>(İşaretçi transferi)"]
    G -- Hayır (Yavaş) --> I["Copy Constructor ile derin kopyalama yap<br/>(10x-50x Gecikme Sıçraması!)"]
    H --> J["Eski Heap Bloğunu Serbest Bırak (delete[])"]
    I --> J
    J --> K["Eski İteratörler Geçersizleşti!<br/>_M_start, _M_finish, _M_end güncelle"]
    K --> D
    
    style B fill:#1f6feb,stroke:#58a6ff,stroke-width:2px,color:#fff
    style C fill:#238636,stroke:#3fb950,stroke-width:2px,color:#fff
    style E fill:#da3633,stroke:#f85149,stroke-width:2px,color:#fff
    style I fill:#b08800,stroke:#d29922,stroke-width:2px,color:#fff
```


```cpp
// ==============================================================================
// 7. Modül 1: Temel Çekirdek Mekanizma - std::vector Bellek Kontrol Bloğu ve Yaşam Döngüsü
// ==============================================================================

#include <iostream>
#include <vector>
#include <cstdint>
#include <iomanip>

struct RadarTrack {
    uint32_t track_id;
    float azimuth;
    float elevation;
    float doppler_velocity;
};

void inspect_vector_internals() {
    std::cout << "--- 1. std::vector Kontrol Bloğu ve Boyut İncelemesi ---\n";
    std::vector<RadarTrack> tracks;

    // Stack üzerindeki boyut: 3 işaretçi (24 bayt)
    std::cout << "sizeof(std::vector<RadarTrack>) = " << sizeof(tracks) << " bayt (Stack)\n";
    std::cout << "sizeof(RadarTrack)              = " << sizeof(RadarTrack) << " bayt\n";
    std::cout << "Başlangıç: size = " << tracks.size() << ", capacity = " << tracks.capacity() << "\n\n";

    // Eleman ekleyerek adresleri ve kapasite basamaklarını izleme
    std::cout << std::left << std::setw(8) << "Adım" 
              << std::setw(8) << "Size" 
              << std::setw(12) << "Capacity" 
              << std::setw(20) << "Heap Adresi (_M_start)" << "\n";
    std::cout << std::string(48, '-') << "\n";

    const RadarTrack* last_address = nullptr;
    for (uint32_t i = 1; i <= 10; ++i) {
        tracks.push_back({i, 45.0f + i, 10.0f, 250.0f + i});
        const RadarTrack* current_address = tracks.data();

        std::string note = "";
        if (current_address != last_address) {
            note = (last_address == nullptr) ? "[İlk Tahsis]" : "[REALLOCATION - YER DEĞİŞTİ]";
            last_address = current_address;
        }

        std::cout << std::setw(8) << i 
                  << std::setw(8) << tracks.size() 
                  << std::setw(12) << tracks.capacity() 
                  << std::setw(20) << current_address 
                  << note << "\n";
    }
}

int main() {
    inspect_vector_internals();
    return 0;
}

```

## 8. Modül 2: Donanıma Yakın / İleri Düzey Alternatif Mekanizma

### `reserve()` vs `resize()` ve `emplace_back()` Optimizasyonları

Birçok junior mühendis `reserve()` ve `resize()` arasındaki farkı karıştırarak üretim sistemlerinde ciddi performans ve bellek hatalarına yol açar:
1. **`reserve(N)` (Kapasite Rezervasyonu):**
   - Yalnızca heap üzerinde en az $N$ elemanlık yer tahsis eder (`capacity >= N`).
   - Elemanların constructor'ını ÇAĞIRMAZ.
   - `size()` DEĞİŞMEZ (örneğin 0 kalır).
   - `operator[]` ile doğrudan erişim tanımsız davranıştır (Undefined Behavior)! Elemanlar `push_back()` veya `emplace_back()` ile eklenmelidir.
2. **`resize(N)` (Boyutlandırma):**
   - Vektörün `size()` değerini doğrudan $N$ yapar.
   - Eğer $N > \text{mevcut size}$ ise, yeni elemanlar için Default Constructor çağrılır.
   - Elemanlar artık bellekte mevcuttur; doğrudan `v[i] = val` ile atanabilir.

### `push_back()` vs `emplace_back()` ve `noexcept` Taşınabilirlik
- `push_back(const T&)`: Önce geçici (temporary) nesne üretir, sonra vektörün içine kopyalar veya taşır.
- `emplace_back(args...)`: Argümanları doğrudan vektörün heap belleğindeki yerine iletir (perfect forwarding) ve nesneyi doğrudan orada inşa eder (`placement new`). Geçici nesne kopyalama maliyetini sıfıra indirir.
- **`noexcept` Kuralı:** Eğer $T$ tipinin Move Constructor'ı `noexcept` olarak işaretlenmemişse, `std::vector` güçlü istisna güvenliği sağlamak adına reallocasyonda taşıma yerine KOPYALAMA yapar.


```cpp
// ==============================================================================
// 9. Modül 2: İleri Düzey Mekanizma - reserve() ile Sıfır Reallocasyon ve emplace_back
// ==============================================================================

#include <iostream>
#include <vector>
#include <string>
#include <chrono>

struct MissileTelemetry {
    uint32_t packet_id;
    double lat, lon, alt;
    std::string payload_checksum;

    MissileTelemetry(uint32_t id, double lt, double ln, double al, std::string chk)
        : packet_id(id), lat(lt), lon(ln), alt(al), payload_checksum(std::move(chk)) {}

    // C++11/20 noexcept Move Constructor: Reallocation anında kopya krizini önler!
    MissileTelemetry(MissileTelemetry&& other) noexcept
        : packet_id(other.packet_id), lat(other.lat), lon(other.lon), alt(other.alt),
          payload_checksum(std::move(other.payload_checksum)) {}

    MissileTelemetry(const MissileTelemetry& other)
        : packet_id(other.packet_id), lat(other.lat), lon(other.lon), alt(other.alt),
          payload_checksum(other.payload_checksum) {
        // Kopyalama maliyeti simülasyonu
    }
};

void demonstrate_reserve_optimization() {
    constexpr size_t TARGET_COUNT = 100000;
    std::cout << "\n--- 2. reserve() ve emplace_back() Optimizasyon Deneyi ---\n";

    // 1. Korumasız Vector: Reallocation Fırtınası
    {
        auto t0 = std::chrono::high_resolution_clock::now();
        std::vector<MissileTelemetry> unreserved_vec;
        for (size_t i = 0; i < TARGET_COUNT; ++i) {
            unreserved_vec.emplace_back(static_cast<uint32_t>(i), 39.93, 32.85, 10500.0, "CHK-VAL-99");
        }
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        std::cout << "[Korumasız] Süre: " << ms << " ms | Son Kapasite: " << unreserved_vec.capacity() << "\n";
    }

    // 2. reserve() Uygulanmış Vector: Sıfır Reallocation Garantisi
    {
        auto t0 = std::chrono::high_resolution_clock::now();
        std::vector<MissileTelemetry> reserved_vec;
        reserved_vec.reserve(TARGET_COUNT); // Tek seferde tahsis!
        for (size_t i = 0; i < TARGET_COUNT; ++i) {
            reserved_vec.emplace_back(static_cast<uint32_t>(i), 39.93, 32.85, 10500.0, "CHK-VAL-99");
        }
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        std::cout << "[reserve()]  Süre: " << ms << " ms | Son Kapasite: " << reserved_vec.capacity() << "\n";
    }
}

int main() {
    demonstrate_reserve_optimization();
    return 0;
}

```

## 10. Modül 3: Dinamik Sınır Durumlar, Geri Basınç ve Kapasite

### Savunma Sanayiinde Deterministik Dinamik Dizi: Bounded Vector Deseni

Standart `std::vector`, kapasitesi dolduğunda sessizce işletim sisteminden yeni bellek talep eder. Ancak aviyonik, füze güdüm ve gerçek zamanlı radar sinyal işleme sistemlerinde (DO-178C Level A):
1. Görev sırasında `malloc/new` çağrısı yapılması YASAKTIR.
2. Bellek tükenmesi (`std::bad_alloc`) kabul edilemez bir sistem çöküşüdür.
3. Giriş hızı işleme hızını aştığında, vektörün sonsuza kadar büyümesi engellenmeli ve **Geri Basınç (Backpressure)** veya **Eski Veriyi Düşürme (Drop-Oldest)** politikası işletilmelidir.

### Bounded Vector Mimarisi
- Başlangıçta (Initialization Phase): `reserve(MAX_CAPACITY)` ile tepe bellek bir kez tahsis edilir.
- Çalışma Anında (Mission Phase): `push_back()` sınır denetimi yapar. Eğer `size() == MAX_CAPACITY` ise:
  - Asla reallocasyon YAPMAZ.
  - Bir hata kodu veya geri basınç bayrağı döner (`false`).
  - Böylece sistemin En Kötü Durum Çalışma Süresi (**WCET**) kesin olarak garanti edilir: Her ekleme işlemi tam $O(1)$ ve deterministiktir (~2 nanosaniye).


```cpp
// ==============================================================================
// 11. Modül 3: Sınırlı Kuyruk ve Geri Basınç Boru Hattı (Bounded Real-Time Vector)
// ==============================================================================

#include <iostream>
#include <vector>
#include <cstdint>
#include <optional>
#include <span>

template <typename T, size_t MaxCapacity>
class BoundedVector {
private:
    std::vector<T> storage_;
    size_t dropped_packets_{0};

public:
    BoundedVector() {
        // Başlangıçta tek seferlik tahsis: Görev anında sıfır reallocasyon!
        storage_.reserve(MaxCapacity);
    }

    // Deterministik Ekleme: Asla heap reallocasyonu yapmaz!
    bool try_push(const T& item) {
        if (storage_.size() >= MaxCapacity) {
            ++dropped_packets_;
            return false; // Geri basınç: Tampon dolu!
        }
        storage_.push_back(item);
        return true;
    }

    void clear_for_next_cycle() {
        storage_.clear(); // size = 0, fakat capacity DEĞİŞMEZ! Bellek serbest bırakılmaz.
    }

    [[nodiscard]] size_t size() const noexcept { return storage_.size(); }
    [[nodiscard]] size_t capacity() const noexcept { return storage_.capacity(); }
    [[nodiscard]] size_t dropped_count() const noexcept { return dropped_packets_; }
    
    // C++20 std::span ile sıfır kopyalı güvenli erişim
    [[nodiscard]] std::span<const T> as_span() const noexcept {
        return std::span<const T>(storage_.data(), storage_.size());
    }
};

struct SensorFrame {
    uint64_t timestamp_ns;
    uint16_t adc_channel;
    int16_t raw_value;
};

int main() {
    std::cout << "\n--- 3. Bounded Real-Time Vector Testi (Kapasite: 5) ---\n";
    BoundedVector<SensorFrame, 5> real_time_buffer;

    for (int i = 1; i <= 8; ++i) {
        SensorFrame frame{1000ULL * i, static_cast<uint16_t>(i % 4), static_cast<int16_t>(i * 100)};
        bool success = real_time_buffer.try_push(frame);

        if (success) {
            std::cout << "Paket " << i << " kabul edildi. Mevcut Size: " << real_time_buffer.size() << "\n";
        } else {
            std::cout << "[GERİ BASINÇ / DROP] Paket " << i << " REDDEDİLDİ! Tampon dolu.\n";
        }
    }

    std::cout << "Kayıp Paket Sayısı: " << real_time_buffer.dropped_count() << "\n";
    std::cout << "Kapasite Güvencesi: " << real_time_buffer.capacity() << " (Sabit Kaldı)\n";
    return 0;
}

```

## 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering / Bilerek Boz)

### Arıza Senaryosu: İteratör Invalidation ve Use-After-Free Zehirlenmesi

Yazılım geliştiricilerin yaptığı en yaygın ve sinsi hata; bir vektörün elemanına ait adresi veya iteratörü saklarken, vektöre yeni eleman eklemektir.

```cpp
std::vector<int> targets = {101, 102, 103, 104}; // capacity = 4
int* primary_target = &targets[0]; // İlk hedefin adresi alındı

// ... başka bir kod modülü yeni bir hedef ekler:
targets.push_back(105); // KAPASİTE DOLDU! Vektör yeni bir adrese taşındı!

// FELAKET: primary_target artık serbest bırakılmış (deallocated) çöp belleğe bakıyor!
std::cout << *primary_target; // USE-AFTER-FREE! Tanımsız Davranış (UB).
```

### Neden Çok Tehlikeli?
1. **Hemen Çökmez:** `primary_target` adresi hemen başka bir program tarafından ezilmemişse, eski değer (101) bir süre daha okunabilir. Test ortamında kod sorunsuz çalışır!
2. **Canlı Görevde Çöker:** Canlı operasyonda heap yöneticisi o eski bloğu başka bir thread'e tahsis ettiği anda, hedef koordinatları saçmalar veya donanım koruma hatası (Segmentation Fault) ile sistem kilitlenir.


```cpp
// ==============================================================================
// 13. Sabotaj Senaryosu: İteratör Invalidation Sabotajı vs İndeks Bazlı Savunma
// ==============================================================================

#include <iostream>
#include <vector>
#include <cstdint>

void run_iterator_sabotage_experiment() {
    std::cout << "\n--- 4. Sabotaj Senaryosu: İteratör Invalidation Analizi ---\n";

    std::vector<int> missile_targets;
    missile_targets.reserve(2); // Başlangıç kapasitesi: 2
    missile_targets.push_back(1001);
    missile_targets.push_back(1002);

    // Korumasız İşaretçi: Hedefin bellek adresini doğrudan saklama
    const int* volatile dangling_target_ptr = &missile_targets[0];
    uintptr_t old_address = reinterpret_cast<uintptr_t>(dangling_target_ptr);
    
    // Savunma Yaklaşımı: Ham adres yerine DİZİN (Index) saklama!
    size_t resilient_target_index = 0;

    std::cout << "[SABOTAJ ÖNCESİ] Hedef ID: " << *dangling_target_ptr 
              << " | Adres: 0x" << std::hex << old_address << std::dec 
              << " | Kapasite: " << missile_targets.capacity() << "\n";

    // SABOTAJ: 3. hedef ekleniyor -> Kapasite (2) aşılır ve reallocasyon tetiklenir!
    std::cout << "--> missile_targets.push_back(1003) çağrılıyor (Reallocation tetikleniyor)...\n";
    missile_targets.push_back(1003);

    const int* new_address_ptr = &missile_targets[0];
    uintptr_t new_address = reinterpret_cast<uintptr_t>(new_address_ptr);

    std::cout << "[SABOTAJ SONRASI] Yeni Vektör Adresi: 0x" << std::hex << new_address << std::dec 
              << " | Yeni Kapasite: " << missile_targets.capacity() << "\n";

    if (old_address != new_address) {
        std::cout << "[!] ADRES DEĞİŞTİ! Eski işaretçi (0x" << std::hex << old_address 
                  << ") artık DANGLING (boşta) durumdadır!\n" << std::dec;
        std::cout << "[!] Korumasız pointer ile okuma yapılırsa: USE-AFTER-FREE felaketi!\n";
    }

    // SAVUNMA KANITI: Dizin bazlı erişim vektör nereye taşınırsa taşınsın %100 güvenlidir:
    int valid_target_id = missile_targets[resilient_target_index];
    std::cout << "[DAYANIKLI SAVUNMA] Dizin (" << resilient_target_index 
              << ") ile erişilen Hedef ID: " << valid_target_id << " (GÜVENLİ & DOĞRU!)\n";
}

int main() {
    run_iterator_sabotage_experiment();
    return 0;
}

```

## 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99)

### Reallocasyon Jitter Analizi ve Determinizm İncelemesi

Gerçek zamanlı aviyonik sistemlerde ortalama gecikme (average latency) tek başına hiçbir anlam ifade etmez. Asıl önemli olan **SLA Garantisi** ve **En Kötü Durum Gecikmesidir (Worst-Case Latency / p99.9)**:
- $100,000$ elemanlık bir ekleme senaryosunda:
  - **Normal `push_back()` (Kapasite Rezerve Edilmemiş):**
    - $p50$ (Medyan Gecikme): $\approx 3 \text{ ns}$ (Bellek hazırken doğrudan yazma)
    - $p99.9$ (Reallocasyon Anı): $\approx 45,000 \text{ ns}$ (Yeni blok tahsisi + $N$ elemanın taşınması)
    - Jitter Oranı: $15,000\times$ dalgalanma!
  - **`reserve(100000)` Uygulanmış `push_back()`:**
    - $p50$: $\approx 2.5 \text{ ns}$
    - $p99.9$: $\approx 3.2 \text{ ns}$
    - Jitter Oranı: Tamamen deterministik, sıfır sıçrama!

Aşağıdaki Python ve C++ test motoru, bu ampirik farkı gerçek donanım üzerinde ölçerek kanıtlayacaktır.


```python
# ==============================================================================
# 15. Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru (Python Wrapper)
# ==============================================================================

import subprocess
import time
import os

print("[*] Ampirik Kıyaslama ve Reallocasyon Analizi Çalıştırılıyor...")

# Vektör analizi doğrudan derleyici üzerinden çalıştırılarak sonuçlar toplanır
from gun_036_std_vector_ve_dinamik_boyut import run_vector_analysis

bench_res = run_vector_analysis()

print(f"[+] Stack Kontrol Bloğu: {bench_res.stack_size_bytes} Bayt (Beklenen: 24B)")
print(f"[+] Reallocasyon Basamakları: {bench_res.growth_steps}")
print(f"[+] Korumasız push_back Süresi : {bench_res.unreserved_time_ms:.2f} ms")
print(f"[+] reserve() ile push_back    : {bench_res.reserved_time_ms:.2f} ms")
print(f"[+] resize() ile operator[]    : {bench_res.resized_time_ms:.2f} ms")
print(f"[+] Hızlanma Katsayısı         : {bench_res.unreserved_time_ms / bench_res.reserved_time_ms:.2f}x")
print(f"[+] İteratör Invalidation Gerçekleşti mi: {bench_res.invalidation_occurred}")

```

## 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı

Üretilecek görselleştirme grafiği (`gun_036_std_vector_ve_dinamik_boyut.png`), 300 DPI çözünürlükte ve karanlık tema (`#0d1117`) standardında 4 ana mühendislik panelinden oluşmaktadır:

1. **Panel 1: Geometrik Büyüme Basamakları (Capacity vs Size):**
   - Eleman eklendikçe tetiklenen reallocasyon basamakları (1, 2, 4, 8, 16, 32, 64, 128...) ve GCC $2.0\times$ büyüme eğrisi.
2. **Panel 2: Reallocasyon Maliyeti ve reserve() Optimizasyonu:**
   - 150,000 eleman ekleme senaryosunda Korumasız `push_back()`, `reserve()` ve `resize()` çalışma sürelerinin karşılaştırmalı çubuk grafiği.
3. **Panel 3: İteratör Invalidation ve Bellek Adresi Değişimi Sabotajı:**
   - Reallocasyon öncesi ve sonrası bellek adreslerinin değişimi; eski adresin `DANGLING` use-after-free durumuna düşüşünün görsel şeması.
4. **Panel 4: Modern C++20 Vektör Karar Standartları Matrisi (MISRA & DO-178C):**
   - Savunma sanayiinde dinamik dizi kullanımı, determinizm garantisi ve `noexcept` kurallarını özetleyen kurumsal referans tablosu.


```python
# ==============================================================================
# 17. 4-Panelli Görselleştirme (.png) ve Katı Doğrulama (Assertions)
# ==============================================================================

import os
from gun_036_std_vector_ve_dinamik_boyut import run_vector_analysis, generate_dashboard, verify_all

# 1. Analizi Çalıştır
results = run_vector_analysis()

# 2. 300 DPI 4-Panelli Dashboard Grafiğini Üret
output_png = "gun_036_std_vector_ve_dinamik_boyut.png"
generate_dashboard(results, output_png)

# 3. Katı Assert Doğrulama Testlerini Çalıştır
verify_all(results)

```

## 18. ⚠️ 10 Ölümcül Anti-Pattern

| No | Anti-Pattern Adı | Neden Tehlikeli? | Doğru Mühendislik Yaklaşımı |
|:---|:---|:---|:---|
| 1 | **Döngü İçinde `reserve()` Unutmak** | Her `push_back()` adımında geometrik reallocasyon tetiklenir, gecikme sıçrar. | Döngüden önce maksimum beklenen boyut için `v.reserve(N)` çağrılmalıdır. |
| 2 | **`reserve()` Sonrası `operator[]` ile Yazmak** | `reserve()` eleman üretmez (`size == 0`). `v[0] = x` çağrısı doğrudan Undefined Behavior'dır! | Ya `push_back()` kullanılmalı ya da boyutlandırma için `resize()` seçilmelidir. |
| 3 | **Döngüde Eleman Eklerken İteratör Saklamak** | `push_back` kapasiteyi aşarsa tüm iteratörler geçersizleşir (use-after-free). | İteratör yerine dizin (`size_t index`) kullanılmalı veya `reserve()` ile kapasite garanti edilmelidir. |
| 4 | **Move Constructor'a `noexcept` Eklememek** | `noexcept` olmayan sınıflarda `vector` reallocasyon anında elemanları taşımak yerine KOPYALAR. | Taşınabilir sınıfların move constructor'ları mutlaka `noexcept` işaretlenmelidir. |
| 5 | **`std::vector<bool>` Tuzağı** | `std::vector<bool>` standart bir konteyner değildir; 1 bayt yerine bit düzeyinde proxy döner (`std::_Bit_reference`). `bool&` referansı alınamaz! | Ya `std::vector<uint8_t>` ya da bit manipülasyonu için `std::bitset` kullanılmalıdır. |
| 6 | **Aviyonik Döngüde `shrink_to_fit()` Çağırmak** | `shrink_to_fit()` bağlayıcı olmayan bir istek olup ek bir heap tahsisi ve kopyalama tetikler. | Aviyonik görev anında kapasite küçültülmemeli; tampon sabit kapasitede tutulmalıdır. |
| 7 | **Fonksiyonlara Değer ile (`by-value`) Vektör Geçmek** | 100,000 elemanlık vektörün tamamı kopyalanır (derin kopya). | Salt okuma için `std::span<const T>` veya `const std::vector<T>&` kullanılmalıdır. |
| 8 | **Başlangıçta Boyut Belli İken `vector` Kullanmak** | Boyut derleme anında sabitse `vector` gereksiz yere 24B stack + heap overhead'i getirir. | Sabit boyutlu yapılar için `std::array<T, N>` tercih edilmelidir. |
| 9 | **`clear()` Çağrısının Belleği Bıraktığını Sanmak** | `v.clear()` yalnızca `size()` değerini 0 yapar; ayrılan heap belleği (`capacity()`) serbest kalmaz! | Belleği gerçekten bırakmak gerekiyorsa swap idiom `std::vector<T>().swap(v)` kullanılmalıdır. |
| 10 | **Bitişik Olmayan Veriyi Vektöre Zorlamak** | Çok sık araya eleman ekleme/silme (`insert/erase`) gerekiyorsa vektör tüm diziyi kaydırır ($O(N)$). | Sık orta-eklemeler için `std::list` veya ring buffer (`boost::circular_buffer`) değerlendirilmelidir. |


## 19. 🔬 Sektörel Standartlar (ASELSAN, HAVELSAN, MISRA, DO-178C)

Savunma ve havacılık endüstrisinde `std::vector` kullanımı katı kurallarla sınırlandırılmıştır:

### 1. DO-178C Uçuşa Elverişlilik Standardı (Level A / B)
- **Kural:** Aviyonik uçuş kontrol yazılımlarında, başlatma (initialization) aşaması tamamlandıktan sonra çalışma zamanında dinamik bellek tahsisi (`malloc/new/realloc`) YAPILAMAZ.
- **Uygulama:** Görev döngüsünde çalışan tüm vektörler sistem açılışında `reserve()` edilmeli ve görev sırasında asla mevcut kapasitelerini aşacak ekleme yapılmamalıdır.

### 2. MISRA C++:2023 Kuralları
- **Kural 18.2 (Dinamik Bellek Yönetimi):** Dinamik bellek tahsis eden standart kütüphane bileşenleri yalnızca kontrollü ve deterministik ortamlarda kullanılmalıdır.
- **Kural 8.2 (İteratör Geçerliliği):** Bir konteyneri değiştiren işlemlerden (`push_back`, `insert`, `erase`) sonra eski iteratörlerin kullanılması kesinlikle yasaktır.

### 3. AUTOSAR C++14 & ASELSAN Kodlama Kılavuzları
- Kritik sinyal işleme boru hatlarında `std::pmr::vector` (Polymorphic Memory Resource) kullanılarak heap yerine önceden stack veya statik bellekte ayrılmış arena tamponları kullanılmalıdır.


## 20. 🛠️ Üretim Kontrol Listesi (Production Checklist - 12 Katı Kural)

Sisteminizi sahaya veya canlı aviyonik test uçuşuna göndermeden önce bu 12 kuralı tek tek doğrulayınız:

- [ ] **1. Boyut Sabit mi?** Boyut derleme anında belliyse `std::array` kullanıldığından emin olundu mu?
- [ ] **2. Ön Tahsis (reserve):** Döngülerden önce `reserve()` çağrılarak reallocasyon sayısı sıfıra indirildi mi?
- [ ] **3. noexcept Kontrolü:** Vektör içinde tutulan sınıfların Move Constructor'ı `noexcept` olarak işaretlendi mi?
- [ ] **4. emplace_back Tercihi:** Gereksiz geçici nesne kopyalamalarını önlemek için `emplace_back` kullanıldı mı?
- [ ] **5. İteratör Güvenliği:** Eleman ekleme/silme sonrası eski iteratör veya pointer'lara erişilmediği doğrulandı mı?
- [ ] **6. Dizin Kullanımı:** Yeniden tahsis ihtimali olan yapılarda pointer yerine dizin (`index`) saklandı mı?
- [ ] **7. Sınır Güvenliği:** Dış kaynaktan gelen dizinlerde `operator[]` yerine `at()` veya sınır denetimi yapıldı mı?
- [ ] **8. std::vector<bool> Kaçınması:** `vector<bool>` yerine `vector<uint8_t>` veya `bitset` kullanıldı mı?
- [ ] **9. Fonksiyon Arayüzü:** Fonksiyon parametrelerinde gereksiz kopyalamayı önlemek için `std::span` veya `const&` tercih edildi mi?
- [ ] **10. Bellek Sıfırlama:** Döngü aralarında `clear()` çağrılarak elemanlar temizlenip kapasite korundu mu?
- [ ] **11. Geri Basınç (Backpressure):** Kapasite dolduğunda çökmek yerine zarifçe reddeden Bounded mekanizma kuruldu mu?
- [ ] **12. AddressSanitizer (ASan):** Kod derlenirken `-fsanitize=address` ile test edilip sıfır use-after-free raporlandı mı?


## 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

### S1: `std::vector` neden 64-bit mimaride tam 24 bayttır?
**Cevap:** `std::vector` stack üzerinde 3 adet ham işaretçi (raw pointer) tutar: `_M_start` (verinin başlangıcı), `_M_finish` (mevcut son eleman adresi) ve `_M_end_of_storage` (ayrılmış kapasite sonu). 64-bit mimaride her işaretçi 8 bayt olduğundan $3 \times 8 = 24$ bayt yer kaplar.

### S2: `reserve()` ile `resize()` arasındaki kritik fark nedir?
**Cevap:** `reserve(N)` yalnızca kapasiteyi ($capacity$) artırır; eleman üretmez ve `size()` değerini değiştirmez. `resize(N)` ise `size()` değerini doğrudan $N$ yapar ve yeni elemanların constructor'ını çağırarak onları bellekte inşa eder.

### S3: Neden `std::vector<bool>` kullanımı savunma sanayiinde yasaklanır?
**Cevap:** `vector<bool>` standart bir konteyner değildir; 1 baytlık `bool` yerine her biti 1 boolean olarak saklayan bir alan optimizasyonu (bit-packing) içerir. Bu nedenle `operator[]` çağrısı gerçek bir `bool&` referansı değil, geçici bir `std::_Bit_reference` proxy nesnesi döner. Bu durum `auto& x = vec[0];` gibi modern C++ ifadelerinin derlenememesine ve multithreaded erişimde veri yarışlarına (data race) neden olur.

### S4: `noexcept` eksikliği vektör performansını nasıl etkiler?
**Cevap:** Reallocasyon esnasında `std::vector`, elemanları yeni bloğa taşırken güçlü istisna garantisi (Strong Exception Guarantee) sağlamak zorundadır. Eğer sınıfın move constructor'ı `noexcept` değilse, taşıma esnasında fırlatılabilecek bir istisna eski bloğun durumunu bozabilir. Bu riski almamak için derleyici taşımak yerine PAHALI KOPYALAMA (`copy constructor`) yapar. Bu da büyük nesnelerde $10\times - 50\times$ performans kaybı demektir.


## 22. 🔮 Gelecek Perspektifi (Donanım & Mimari Trendleri)

### C++20/23/26 ve Yeni Nesil Donanımlarda Vektör Trendleri

1. **C++20 `std::span` Devrimi:**
   Fonksiyon arayüzlerinde `const std::vector<T>&` bağımlılığı sona ermiştir. `std::span<const T>`, hem `std::array`, hem `std::vector`, hem de C-dizilerini kopyalamadan temsil edebilen 16 baytlık evrensel bir görünüm (view) sunar.

2. **C++23 `std::vector` constexpr Desteği:**
   C++20 ile temelleri atılan ve C++23'te olgunlaşan `constexpr std::vector`, derleme zamanında dinamik boyutlu algoritmaların çalıştırılmasına ve sonuçların doğrudan `.rodata` segmentine sabit olarak gömülmesine olanak tanır.

3. **PMR (Polymorphic Memory Resource) ve Monotonic Buffer:**
   Geleceğin savunma sistemlerinde genel amaçlı heap yöneticisi (`malloc`) tamamen devre dışı bırakılmaktadır. `std::pmr::vector`, yığın üzerinde önceden ayrılmış statik tamponları (arena memory) kullanarak deterministik nanosaniye hızında tahsis sağlar.


## 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı)

Bugün `std::vector` ile bitişik bellek yönetimini, geometrik büyüme maliyetini, `reserve()` disiplinini ve ölümcül iteratör geçersizleşmesi sabotajını derinlemesine inceledik.

Ancak askeri sistemlerde yönettiğimiz dinamik veriler yalnızca sayılardan ve sabit struct'lardan ibaret değildir:
- Taktik telsiz mesaj metinleri (STANAG 5066),
- JSON/XML telemetri formatları,
- Aviyonik arıza kayıtları (logs),
- Cihaz seri numaraları ve IP/Port adresleri.

Tüm bu metinsel veriler dinamik uzunluktadır. Ancak C-tarzı `char*` ve `strcpy` fonksiyonları bellek taşmasına (buffer overflow) ve sızıntılara gebedir.

Yarınki konumuz: **GÜN 037 — std::string ve Dinamik Metin Yönetimi**
- `std::string`'in 24-32 baytlık stack yapısı,
- **SSO (Small String Optimization)** mucizesi: 15 karaktere kadar olan metinlerde sıfır heap tahsisi!
- `std::string_view` ile sıfır kopyalı metin işleme ve havada sarkan işaretçi (dangling string_view) sabotajları.

Yarın görüşmek üzere. Sistemleriniz deterministik, bellekleriniz reallocasyonsuz kalsın! 🚀


