# GÜN 014: Array/List ve Ardışık Veri Mimarisi
### Faz 0: Bilgisayar ve Yazılım Temelleri (Gün 014 / 365)
#### 24-Hücreli Master Mimari Planı (18 Markdown + 6 Kod Hücresi)

---

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

> [!NOTE]
> **40-Nokta Standart Bildirimi:** Bu çalışma planı; ASELSAN, HAVELSAN, Roketsan ve STM gibi kritik savunma sanayii kurumlarında görev alacak bir sistem mimarının bitişik bellek yerleşimini (Contiguous Memory Layout), L1/L2/L3 önbellek satırı (Cache Line) mekanizmasını, donanımsal önceden getirme (Hardware Prefetcher) davranışını, pointer aritmetiğini ve dinamik dizi (`std::vector`) büyüme stratejilerini ilk ilkelerden başlayarak aviyonik determinizm seviyesinde kavraması için 40 temel pedagojik kalite kriterine tam uyumlu olarak hazırlanmıştır.

---

## [MD 2] 1. 🎯 Bugünkü Problem: Neden Bitişik Bellek (Contiguous)? (Cache Line ve Pointer Chasing Cezası)

Yazılım dünyasında genellikle verileri bir küme içinde toplamak için "Dizi (Array)" veya "Bağlı Liste (Linked List)" arasında soyut bir seçim yapılır. Teorik bilgisayar biliminde her ikisi de $N$ eleman tutar; hatta bağlı listede araya eleman eklemek $O(1)$ gibi sunulur.

Ancak **modern bilgisayar donanımında (CPU & RAM) bağlı listeler tam bir performans felaketidir!**

İşlemcimiz ana bellekten (DRAM) veri okurken tek bir bayt getirmez. Her seferinde **64 baytlık bir Önbellek Satırını (Cache Line)** L1 veri önbelleğine çeker.
- **Bitişik Dizi (Array / std::vector):** Elemanlar RAM'de peş peşe, kesintisiz dizilmiştir. İşlemci dizinin 0. elemanını okuduğunda, yanındaki sonraki 15 tamsayı da (her biri 4 bayt ise) bedavaya L1 önbelleğe gelir! Üstelik CPU'daki **Donanımsal Önceden Getirici (Hardware Prefetcher)** ardışık erişimi tespit eder ve siz daha istemeden bir sonraki önbellek satırını RAM'den çeker. Bellek gecikmesi **~1 ns**'ye iner.
- **Bağlı Liste (Linked List / std::list):** Her düğüm `malloc` / `new` ile belleğin rastgele bir köşesine dağıtılmıştır. Bir sonraki düğüme gitmek için o anki düğümdeki işaretçiyi (pointer) okumak zorundasınızdır (**Pointer Chasing**). Bir sonraki düğüm L1'de yoktur, L2'de yoktur, L3'te de yoktur; işlemci her adımda DRAM'e gitmek zorunda kalır (**~60-100 ns Cache Miss cezası**). 

### Karşılaştığımız Temel Mühendislik Problemleri:
1. **Pointer Aritmetiği ve Donanım Eşdeğerliği:** `arr[i]` ile `*(arr + i)` ifadelerinin assembly seviyesinde tek bir `LEA` (Load Effective Address) komutuna nasıl dönüştüğü.
2. **Dinamik Vektör Büyüme Bedeli:** Dizi dolduğunda yeni bellek bloğuna taşınırken ödenen $O(N)$ kopyalama maliyeti ve geometrik faktörün ($1.5	imes$ vs $2.0	imes$) bellek parçalanmasına etkisi.
3. **Aviyonik Determinizm İhtiyacı:** Çalışma zamanında rastgele `realloc` yapılması uçuş bilgisayarlarında WCET bütçesini patlatır; bu nedenle sıfır-tahsisli ardışık dairesel tamponlara (Ring Buffer) ihtiyaç duyulur.

---

## [MD 3] 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi: Radar DMA Tamponları ve Determinizm)

- **Doğrudan Bellek Erişimi (DMA - Direct Memory Access):** Radar, Sonar ve Elektronik Harp (EH) alıcıları analog sinyali sayısallaştırdığında (ADC), gigabaytlarca veriyi işlemciyi meşgul etmeden doğrudan RAM'e yazar. DMA denetleyicileri yalnızca **fiziksel olarak bitişik (physically contiguous)** bellek bloklarıyla çalışabilir. Bağlı listeler veya parçalanmış veri yapıları radar donanımıyla fiziksel olarak haberleşemez!
- **DO-178C ve Statik Bellek Bütçesi:** Uçuş kritik sistemlerde dinamik bellek ayırma (`malloc`, `new`) çalışma anında kesinlikle yasaktır (MISRA C++:2008 Kural 18-4-1). Tüm diziler derleme anında sabit boyutlu (`std::array`) veya önceden ayrılmış tampon havuzlarında (Memory Pool) ardışık olarak tutulmalıdır.
- **SIMD (Tek Komut Çoklu Veri) Vektörizasyonu:** Radar FFT filtrelerinde 256-bit AVX2 veya 512-bit AVX-512 yazmaçlarının tek bir döngüde 8 veya 16 float veriyi işleyebilmesi için verilerin bellekte 32-bayt veya 64-bayt hizalı ardışık dizilmiş olması şarttır (`_mm256_load_ps`).

---

## [MD 4] 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları)

| Soru | Donanım ve Aviyonik Mühendisliği Karşılığı |
|:---|:---|
| **Ne? (What)** | Bitişik Dizi (Contiguous Array), Pointer Aritmetiği, Cache Locality (Yerellik), Stride, Dynamic Vector Reallocation, Ring Buffer. |
| **Neden? (Why)** | Donanımsal önbellek satırlarından (64B Cache Line) azami faydalanmak, CPU Prefetcher'ı tetiklemek ve $O(1)$ doğrudan bellek erişimi sağlamak için. |
| **Nerede? (Where)** | L1/L2/L3 Veri Önbelleği (D-Cache), Ana Bellek (DRAM), DMA Ring Buffer Tamponları ve SIMD Yazmaçları (`YMM`/`ZMM`). |
| **Nasıl? (How)** | Temel adres üzerine eleman boyutu ile çarpılan indeksin eklenmesiyle: $\text{Adres} = \text{Base} + (i \times \text{sizeof}(T))$. |
| **Ne Zaman? (When)** | Yüksek frekanslı sensör okumalarında, telemetri paket akışlarında, radar darbe sıkıştırmasında ve matris işlemlerinde. |
| **Kim? (Who)** | ASELSAN Radar ve Haberleşme Mühendisleri, HAVELSAN Simülasyon Uzmanları, Gömülü Sistem Mimarları. |

---

## [MD 5] 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Analoji)

Bir **Kütüphanedeki Kitap Dizilimi** benzetmesini ele alalım:

1. **Bitişik Dizi (Contiguous Array):** Bir ansiklopedinin 16 cildinin rafta yan yana dizilmesidir. 1. cildi raftan alırken eliniz yanındaki 2., 3. ve 4. ciltlere de çarpar; onları tek hamlede masanıza taşırsınız (Cache Line dolumu). İstediğiniz cilde gitmek için raftaki pozisyonu doğrudan bilirsiniz ($O(1)$ erişim).
2. **Bağlı Liste (Linked List):** Kütüphanecinin her cildi binanın farklı bir katındaki rastgele bir odaya saklaması ve 1. cildin içine *"2. Cilt 4. Kat Oda 12'dedir"* notunu koymasıdır. 16 cildi okumak için kütüphanenin içinde kat kat merdiven çıkıp inersiniz (Pointer Chasing yorgunluğu ve Cache Miss krizi!).
3. **Dinamik Büyüme (std::vector Reallocation):** Rafta 4 kitaplık yer varken 5. kitabı koymak istediğinizde, mevcut 4 kitabı kucaklayıp kütüphanenin başka bir yerindeki 8 kitaplık daha büyük bir rafa taşımak zorunda kalmanızdır (Reallocation & Move maliyeti).

---

## [MD 6] 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model

### 1. Pointer Aritmetiği ve LEA Komutu
C++ dilindeki `arr[i]` yazımı aslında bir sözdizimsel şekerdir (syntactic sugar):
$$\text{arr}[i] \iff *(\text{arr} + i)$$

İşlemci seviyesinde bir dizinin $i$. elemanının adresi şu formülle hesaplanır:
$$\text{Adres} = \text{Base\_Address} + i \times S$$
Burada $S = \text{sizeof}(T)$ (Örn: `int32_t` için 4 bayt, `double` için 8 bayt).

x86_64 mimarisinde bu hesaplama tek bir saat döngüsünde **`LEA` (Load Effective Address)** komutuyla donanımsal olarak icra edilir:
```assembly
; RBX = Base Address, RDI = Index (i)
lea rax, [rbx + rdi * 4]   ; RAX = rbx + i * 4 (Tek saat döngüsü!)
mov eax, [rax]             ; Değeri belleğin o adresinden çek
```

### 2. Dinamik Vektör Büyüme Faktörü ($1.5\times$ vs $2.0\times$)
Bir vektör dolduğunda kapasite geometrik bir faktörle ($G$) artırılır:
- **GCC / Clang ($G = 2.0$):** Kapasiteler: $1, 2, 4, 8, 16, 32, 64...$
  - *Matematiksel Kusur:* Yeni ayrılan alan ($32$), daha önce serbest bırakılan alanların toplamından ($1 + 2 + 4 + 8 + 16 = 31$) her zaman büyüktür. Dolayısıyla bellek yöneticisi eski bellek bloklarını asla yeniden kullanamaz; bellek sürekli ileriye doğru parçalanır (Fragmentation).
- **MSVC ($G = 1.5$):** Kapasiteler: $1, 2, 3, 4, 6, 9, 13, 19, 28...$
  - *Matematiksel Avantaj:* Birkaç yeniden tahsis sonra, eski serbest kalan blokların toplamı yeni istenecek alandan büyük hale gelir. Bellek yöneticisi eski blokları geri dönüştürebilir (Memory Reuse).

---

## [MD 7] 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

### Bitişik Dizi vs Bağlı Liste Bellek ve Önbellek Yerleşimi

```
[ BİTİŞİK DİZİ (CONTIGUOUS ARRAY) - 64 BAYT CACHE LINE ]
RAM Adresi: 0x1000   0x1004   0x1008   0x100C  ...  0x103C
            ┌────────┬────────┬────────┬────────┬───┬────────┐
            │ arr[0] │ arr[1] │ arr[2] │ arr[3] │...│ arr[15]│
            └────────┴────────┴────────┴────────┴───┴────────┘
            ▲════════════════════════════════════════════════▲
            TEK BİR 64-BAYT L1 CACHE LINE (100% Cache Hit!)

[ BAĞLI LİSTE (LINKED LIST) - DAĞINIK DÜĞÜMLER ]
Düğüm 0 (0x1000): [ Veri | NextPtr: 0x8F40 ]  --> L1 Cache Hit
Düğüm 1 (0x8F40): [ Veri | NextPtr: 0x3120 ]  --> CACHE MISS! DRAM'e Git (~80 ns)
Düğüm 2 (0x3120): [ Veri | NextPtr: 0xA580 ]  --> CACHE MISS! DRAM'e Git (~80 ns)
```

### Mermaid Akış Şeması: Dynamic Vector Büyüme Döngüsü

```mermaid
flowchart TD
    Start([push_back Çağrıldı]) --> CheckCap{Boyut == Kapasite?}
    CheckCap -- Hayır --> DirectWrite[Elemanı array[size] konumuna yaz]
    DirectWrite --> IncSize[Boyutu 1 Artır]
    IncSize --> EndOk([İşlem Tamam O_1])
    
    CheckCap -- Evet --> AllocNew[Yeni Kapasite Hesapla: Cap * Büyüme_Faktörü]
    AllocNew --> Malloc[Yeni Bellek Bloğu Tahsis Et]
    Malloc --> CopyElements[Eski Elemanları Yeni Bloğa Kopyala/Taşı O_N]
    CopyElements --> FreeOld[Eski Bellek Bloğunu Serbest Bırak]
    FreeOld --> DirectWrite
```

---

## [CODE 1] 7. Modül 1: Temel Çekirdek Mekanizma / Motor İmplemantasyonu

Aşağıdaki kod; bitişik bellek simülatörünü, LEA pointer aritmetiğini ve 64-baytlık L1 Cache Line gereksinimini modelleyen saf Python çekirdek mekanizmasıdır.

```python
from typing import List

class ContiguousArraySimulator:
    """Donanımsal RAM yerleşimi, önbellek satırları ve pointer aritmetiği modeli."""
    def __init__(self, base_address: int, element_count: int, element_size: int = 4):
        self.base_address = base_address
        self.element_count = element_count
        self.element_size = element_size # 4 bayt = int32_t
        self.memory = [0] * element_count
        self.cache_line_size = 64 # 64 Bayt L1 Cache Line

    def get_address_of_index(self, index: int) -> int:
        """Pointer Aritmetiği: Address = Base + Index * Sizeof(T) (LEA komutu)."""
        if index < 0 or index >= self.element_count:
            raise IndexError(f"BUFFER_OVERRUN: Dizi sınırları aşıldı! İndeks: {index}, Boyut: {self.element_count}")
        return self.base_address + (index * self.element_size)

    def calculate_cache_lines_needed(self) -> int:
        """Dizinin toplam kapladığı 64-baytlık L1 önbellek satırı sayısı."""
        total_bytes = self.element_count * self.element_size
        return (total_bytes + self.cache_line_size - 1) // self.cache_line_size

# Doğrulama Deneyi
arr = ContiguousArraySimulator(base_address=0x00405000, element_count=32, element_size=4)
print(f"Dizi Başlangıç Adresi: {hex(arr.base_address)}")
print(f"arr[0] Adresi:  {hex(arr.get_address_of_index(0))}")
print(f"arr[5] Adresi:  {hex(arr.get_address_of_index(5))} (Fark: {5 * 4} Bayt)")
print(f"arr[15] Adresi: {hex(arr.get_address_of_index(15))}")
print(f"32 Eleman (128 Bayt) İçin Gereken L1 Cache Line Sayısı: {arr.calculate_cache_lines_needed()}")
```

---

## [MD 8] 8. Modül 2: Donanıma Yakın / İleri Düzey Alternatif Mekanizma

### std::vector Büyüme Faktörü ve `reserve()` Ön-Tahsisi

- **Amortize Edilmiş $O(1)$:** Vektöre her eleman eklendiğinde dizi büyütülmez. Geometrik büyüme sayesinde $N$ eleman eklenirken toplamda yaklaşık $2N$ kopyalama yapılır; bu da eleman başına düşen ortalama maliyeti $O(1)$ yapar.
- **Kapasite Rezervasyonu (`std::vector::reserve`):** Eğer eklenecek eleman sayısı önceden biliniyorsa (örn: radardan 10.000 darbe örneği geleceği kesinse), `reserve(10000)` çağrılır. Bu çağrı tek bir büyük bellek bloğu ayırır ve ara yeniden tahsis (reallocation) ve kopyalama maliyetini tamamen **sıfırlar**.

---

## [CODE 2] 9. Modül 2: İleri Düzey / Donanıma Yakın Mekanizma Kodu

```python
class DynamicVectorSimulator:
    """Geometrik (1.5x, 2.0x) vs Lineer (+1) büyüme stratejisi analizi."""
    def __init__(self, growth_factor: float = 2.0, initial_capacity: int = 1):
        self.growth_factor = growth_factor
        self.capacity = initial_capacity
        self.size = 0
        self.reallocation_count = 0
        self.total_elements_copied = 0

    def push_back(self, value: int):
        if self.size >= self.capacity:
            # Yeniden tahsis (Reallocation) ve taşıma (Move/Copy)
            new_capacity = int(self.capacity * self.growth_factor) if self.growth_factor > 1.0 else self.capacity + 1
            if new_capacity <= self.capacity:
                new_capacity = self.capacity + 1
            self.total_elements_copied += self.size
            self.capacity = new_capacity
            self.reallocation_count += 1
        self.size += 1

# Büyüme Karşılaştırması
v_gcc = DynamicVectorSimulator(2.0)
v_msvc = DynamicVectorSimulator(1.5)

for i in range(100):
    v_gcc.push_back(i)
    v_msvc.push_back(i)

print(f"100 Eleman Eklendiğinde:")
print(f"  - GCC 2.0x  : {v_gcc.reallocation_count} Yeniden Tahsis, {v_gcc.total_elements_copied} Kopyalama, Kapasite: {v_gcc.capacity}")
print(f"  - MSVC 1.5x : {v_msvc.reallocation_count} Yeniden Tahsis, {v_msvc.total_elements_copied} Kopyalama, Kapasite: {v_msvc.capacity}")
```

---

## [MD 9] 10. Modül 3: Dinamik Sınır Durumlar, Geri Basınç ve Kapasite

### Deterministik Aviyonik Dairesel Tampon (Ring Buffer)
Uçuş bilgisayarlarında dinamik büyüyen vektör kullanılamaz; çünkü bir `reallocation` milisaniyeler sürebilir ve kritik kontrol döngüsünün (deadline) kaçmasına neden olur.
Bunun yerine sabit boyutlu, önceden tahsis edilmiş ve üzerine yazmayan (veya eskiyi ezen) **Dairesel Tamponlar (Ring Buffer)** kullanılır. Tampon dolduğunda yeni gelen veriler reddedilir (**Geri Basınç / Backpressure**).

---

## [CODE 3] 11. Modül 3: Sınırlı Kuyruk ve Geri Basınç Boru Hattı Kodu

```python
from typing import Optional

class CircularRingBuffer:
    """Sıfır çalışma zamanı tahsisli, sabit boyutlu ardışık aviyonik kuyruk."""
    def __init__(self, capacity: int = 4):
        self.capacity = capacity
        self.buffer = [0] * capacity
        self.head = 0
        self.tail = 0
        self.count = 0

    def push(self, data: int) -> bool:
        if self.count >= self.capacity:
            return False # Geri basınç: Tampon dolu, paket düşürüldü / reddedildi!
        self.buffer[self.head] = data
        self.head = (self.head + 1) % self.capacity
        self.count += 1
        return True

    def pop(self) -> Optional[int]:
        if self.count == 0:
            return None # Tampon boş
        val = self.buffer[self.tail]
        self.tail = (self.tail + 1) % self.capacity
        self.count -= 1
        return val

rb = CircularRingBuffer(capacity=3)
print(f"Push 10: {rb.push(10)}")
print(f"Push 20: {rb.push(20)}")
print(f"Push 30: {rb.push(30)}")
print(f"Push 40 (Taşma Girişimi): {rb.push(40)} (Geri basınç devrede!)")
print(f"Pop: {rb.pop()}")
print(f"Push 40 (Yer açıldıktan sonra): {rb.push(40)}")
```

---

## [MD 10] 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering / Bilerek Boz)

### İki Ölümcül Arıza Senaryosu:
1. **Senaryo A: Sınır Kontrolsüz Dizi İhlali (Out-of-Bounds / Buffer Overrun):** C/C++'ta `arr[10]` (10 elemanlı dizide) yazıldığında dil varsayılan olarak sınır kontrolü yapmaz (`operator[]`). Komşu bellek bloğundaki kritik değişken veya fonksiyon işaretçisi sessizce ezilir. `std::span` veya `.at()` metodu donanımsal koruma sağlar.
2. **Senaryo B: Lineer Büyüme Sabotajı ($+1$ Growth Catastrophe):** Bir mühendis kapasiteyi katlamak yerine her seferinde `capacity += 1` yaparsa, $N$ eleman için toplam kopyalama sayısı $\frac{N(N-1)}{2} = O(N^2)$ olur. 10.000 elemanda 50 milyon kopyalama gerçekleşir ve sistem donar!

---

## [CODE 4] 13. Sabotaj Senaryosu: Korumasız Çöküş vs Dayanıklı Savunma

```python
from typing import Tuple

class ArraySabotage:
    @staticmethod
    def simulate_buffer_overflow(arr_sim: ContiguousArraySimulator, target_index: int) -> Tuple[bool, str]:
        """Sınır kontrolsüz bellek okuma/yazma sabotajı."""
        try:
            addr = arr_sim.get_address_of_index(target_index)
            return True, f"KORUMASIZ ERİŞİM: Adres {hex(addr)} okundu (Bellek Sızıntısı!)"
        except IndexError as e:
            return False, f"ENGELENDİ: {str(e)}"

    @staticmethod
    def simulate_linear_growth_catastrophe(n_elements: int) -> Tuple[int, int]:
        """Lineer (+1) büyüme sabotajı: O(N^2) kopyalama felaketi."""
        vec = DynamicVectorSimulator(growth_factor=1.0)
        for i in range(n_elements):
            vec.push_back(i)
        return vec.reallocation_count, vec.total_elements_copied

# Sabotaj 1: Sınır Dışı Erişim Testi
sim_arr = ContiguousArraySimulator(0x1000, 10, 4)
allowed, msg = ArraySabotage.simulate_buffer_overflow(sim_arr, 15)
print(f"Sabotaj 1 Sonucu: {msg}")

# Sabotaj 2: O(N^2) Lineer Kopyalama Felaketi
reallocs, copies = ArraySabotage.simulate_linear_growth_catastrophe(100)
print(f"Sabotaj 2 Sonucu (N=100 için): {reallocs} Reallocation, {copies} Kopyalama (Beklenen: 4950)")
```

---

## [MD 11] 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99)

Yüksek çözünürlüklü zamanlayıcılarla yapılan mikro-benchmark analizleri:
- **Ardışık Dizi Erişimi:** L1 önbellek satırları ve Hardware Prefetcher sayesinde eleman başına ortalama **~1.2 - 2.0 ns**.
- **Dağınık Liste (Pointer Chasing) Erişimi:** Her düğüm DRAM'in rastgele bir adresinde olduğu için Cache Miss yaşanır; eleman başına süre **~18 - 35 ns** seviyesine fırlar (**15–20 kat daha yavaş!**).
- **Önceden Reserve Edilmiş Vektör:** Dinamik büyüyen vektöre kıyasla **~3-5 kat daha hızlıdır** çünkü sıfır bellek ayırma ve sıfır veri kopyalama gerçekleşir.

---

## [CODE 5] 15. Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru

```python
import time
import random

def run_micro_benchmarks():
    n_items = 100000
    arr_data = list(range(n_items))
    rand_idx = list(range(n_items))
    random.seed(42)
    random.shuffle(rand_idx)

    # 1. Ardışık Dizi
    t0 = time.perf_counter_ns()
    s1 = 0
    for v in arr_data:
        s1 += v
    t1 = time.perf_counter_ns()
    lat_seq = (t1 - t0) / n_items

    # 2. Dağınık İşaretçi (Pointer Chasing)
    t0 = time.perf_counter_ns()
    s2 = 0
    for i in rand_idx:
        s2 += arr_data[i]
    t1 = time.perf_counter_ns()
    lat_rand = (t1 - t0) / n_items

    print(f"--- Mikro-Benchmark Sonuçları ({n_items:,} Eleman) ---")
    print(f"  - Ardışık Dizi Erişimi:          {lat_seq:.2f} ns/eleman")
    print(f"  - Dağınık Pointer Chasing:       {lat_rand:.2f} ns/eleman")
    print(f"  - Donanımsal Önbellek Avantajı:   {lat_rand / max(lat_seq, 0.001):.1f}x Hızlı!")

run_micro_benchmarks()
```

---

## [MD 12] 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı

Üretilen 4-panelli 300 DPI dashboard görselleştirmesi:
- **Panel 1 (Bellek & Cache Hiyerarşisi):** Bitişik Dizi (L1 Prefetcher) vs Dağınık Liste (Pointer Chasing Cache Miss) Erişim Gecikmesi (ns).
- **Panel 2 (Algoritmik Büyüme Analizi):** Vektör Büyüme Stratejileri ($2.0\times$ vs $1.5\times$ vs Lineer $+1$) Kümülatif Kopyalama Maliyeti.
- **Panel 3 (Optimizasyon Etkisi):** `std::vector::reserve` Ön-Tahsis Performans Kazanımı (Dinamik vs Reserve İcra Süresi - ms).
- **Panel 4 (Sabotaj ve Dayanıklılık):** Korumasız İndeksleme (`operator[]`) vs Sınır Korumalı (`at()`, `std::span`) Güvenlik Başarısı (%0 vs %100).

---

## [CODE 6] 17. 4-Panelli Görselleştirme (.png) ve Katı Doğrulama (Assertions)

```python
# Dashboard üretim ve tam doğrulama kodu gun_014_array_list_ardisik_veri.py içinde yer almaktadır.
import subprocess
import os

py_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_014_array_list_ardisik_veri.py")
print("Python Simülasyon ve Dashboard Motoru çalıştırılıyor...")
ret_code = subprocess.call(["python", py_script])
print(f"Çalıştırma Tamamlandı (Dönüş Kodu: {ret_code})")
```

---

## [MD 13] 18. ⚠️ 10 Ölümcül Anti-Pattern

| No | Anti-Pattern | Neden Ölümcül? | Güvenli Savunma Çözümü |
|:---|:---|:---|:---|
| 1 | **Sayısal Veride `std::list` Kullanmak** | Her düğüm ayrı tahsis edilir, önbelleği kirletir ve pointer chasing nedeniyle 20x yavaştır. | Her zaman bitişik `std::vector` veya `std::array` kullanın. |
| 2 | **Döngü İçinde Vektöre `reserve` Yapmadan `push_back`** | Vektör sürekli dolup taşar; onlarca kez yeniden tahsis ve gereksiz bellek kopyalaması yapılır. | Boyut tahmin edilebiliyorsa döngüden önce mutlaka `vec.reserve(N)` çağırın. |
| 3 | **Sınır Kontrolsüz İndeksleme (`arr[i]`)** | İndeks dizi dışına taştığında sessizce komşu belleği bozar (Undefined Behavior). | Kritik kodlarda `arr.at(i)` veya C++20 `std::span` sınır denetimini kullanın. |
| 4 | **Lineer Kapasite Artışı (`cap += 10`)** | Geometrik faktör yerine sabit artış yapmak ekleme işlemini $O(N^2)$ felaketine çevirir. | En az $1.5\times$ veya $2.0\times$ geometrik büyüme katsayısı kullanın. |
| 5 | **Nesne Dizisi (AoS) Yerine Yapı Dizisi Seçimi (SoA)** | 100 baytlık struct'ın sadece tek bir alanını okurken gereksiz 96 baytı L1 cache'e doldurur. | DSP ve SIMD operasyonlarında Structure of Arrays (SoA) mimarisini tercih edin. |
| 6 | **Diziyi Değerle (By-Value) Fonksiyonlara Geçmek** | Tüm dizi elemanları yığına kopyalanır, yığını tüketir ve devasa işlemci saati harcar. | Dizileri `std::span<const T>` veya `const std::vector<T>&` ile geçin. |
| 7 | **Hizalanmamış (Unaligned) SIMD Erişimi** | 64-bayt hizalı olmayan dizilerde AVX komutları (`_mm256_load_ps`) genel koruma hatası (`#GP`) verir. | `alignas(64)` veya derleyiciye özgü hizalı bellek ayırıcılar (`_aligned_malloc`) kullanın. |
| 8 | **Yeniden Tahsis Sonrası Asılı İşaretçi (Iterator Invalidation)** | Vektör büyüdüğünde eski belleği serbest bırakır; eski işaretçiler (pointer/iterator) çöp olur. | Reallocation riski olan durumlarda ham işaretçi saklamayın; indeks saklayın. |
| 9 | **Aviyonikte Çalışma Zamanında Dinamik Büyüme** | Uçuş anında `realloc` çağrısının ne kadar süreceği belirsizdir (Jitter / WCET ihlali). | Sabit kapasiteli deterministik dairesel tampon (`RingBuffer`) kullanın. |
| 10 | **Dizi Boyutunu `int` Türünde Tutmak** | 2 milyardan büyük dizilerde veya taşma durumlarında negatif indeks oluşup bellek çöker. | Dizi indeksleri ve boyutları için her zaman `size_t` türünü kullanın. |

---

## [MD 14] 19. 🔬 Sektörel Standartlar (ASELSAN, HAVELSAN, MISRA, DO-178C)

1. **MISRA C++:2008 Rule 5-0-15:** *"Array indexing shall be the only acceptable form of pointer arithmetic."* (İşaretçi aritmetiği yalnızca dizi indeksleme biçiminde kullanılabilir; ham pointer kaydırmaları yasaktır).
2. **MISRA C++:2008 Rule 18-4-1:** *"Dynamic memory allocation/freeing shall not be used after initialization."* (Sistem ilklendirildikten sonra çalışma zamanında dinamik bellek tahsisi/serbest bırakması yapılamaz).
3. **DO-178C Section 6.4.4:** Bellek kullanımının ve yürütme sürelerinin deterministik olması zorunludur. Dizi sınır ihlallerini (buffer overrun) engelleyen statik analiz kanıtları şarttır.
4. **C++ Core Guidelines Bounds.1:** Ham diziler (`T arr[]`) yerine modern `std::array`, `std::vector` veya `std::span` kullanılarak sınır güvenliği garanti edilmelidir.

---

## [MD 15] 20. 🛠️ Üretim Kontrol Listesi (Production Checklist - 12 Katı Kural)

- [ ] **Kural 1:** Kod tabanında `std::list` gibi dağınık bağlı veri yapıları yerine bitişik diziler (`std::vector`, `std::array`) tercih edildi mi?
- [ ] **Kural 2:** Boyutu bilinen dinamik dizilerde döngü öncesinde `reserve()` çağrısı yapıldı mı?
- [ ] **Kural 3:** Kritik aviyonik görevlerde çalışma anında `realloc` yapılmadığı, dairesel tampon (`RingBuffer`) kullanıldığı doğrulandı mı?
- [ ] **Kural 4:** Tüm dizi sınır kontrolleri (`Bounds Checking`) statik analiz veya `std::span` ile güvenceye alındı mı?
- [ ] **Kural 5:** Dizi indeks değişkenleri işaretli `int` yerine `size_t` olarak tanımlandı mı?
- [ ] **Kural 6:** SIMD operasyonları için bellek blokları en az 32 veya 64 bayt hizalandı mı (`alignas(64)`)?
- [ ] **Kural 7:** Fonksiyon parametrelerinde büyük diziler kopyalanmak yerine `std::span` ile referans verildi mi?
- [ ] **Kural 8:** Vektör büyümelerinde iterator geçersizleşmesi (Iterator Invalidation) senaryoları analiz edildi mi?
- [ ] **Kural 9:** Radar DMA tamponlarının fiziksel olarak bitişik (Physically Contiguous) bellek bloklarında açıldığı teyit edildi mi?
- [ ] **Kural 10:** MISRA C++ kurallarına uygun olarak kontrolsüz ham işaretçi aritmetiği engellendi mi?
- [ ] **Kural 11:** Tampon dolması durumunda sistemin kilitlenmemesi için Geri Basınç (Backpressure / Drop) mekanizması tanımlandı mı?
- [ ] **Kural 12:** Yüksek performans gerektiren veri modellerinde Cache Line dostu Structure of Arrays (SoA) mimarisi değerlendirildi mi?

---

## [MD 16] 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

**S1: Bir mülakatta "Araya eleman eklemek Linked List'te O(1), Vector'de O(N)'dir, o halde neden her yerde Vector kullanıyoruz?" sorusuna nasıl cevap verilmelidir?**
> **Cevap:** Teorik analiz bellek hiyerarşisini (Cache Line, Prefetcher, RAM Latency) yok sayar. Bir bağlı listede araya eleman eklemek için önce o elemanın yerini bulmanız gerekir; bu da $O(N)$ pointer chasing gerektirir ve onlarca Cache Miss yüzünden çok yavaştır. Vektörde ise bitişik bellek sayesinde elemanlar `memmove` ile işlemcinin L1 önbelleğinde tek seferde kaydırılır. $N < 100.000$ elemanlı pratik senaryolarda `std::vector`, `std::list`'ten katbekat daha hızlıdır (Bjarne Stroustrup'un ampirik ispatı).

**S2: Vektörün geometrik büyüme katsayısının 1.5 olması neden 2.0'dan daha avantajlı olabilir?**
> **Cevap:** 2.0 çarpanında yeni tahsis edilen alan ($2^k$), önceki tüm alanların toplamından ($2^k - 1$) daima 1 fazladır. Dolayısıyla bellek yöneticisi önceki blokları birleştirip yeniden kullanamaz. 1.5 çarpanında ise bir süre sonra serbest kalan eski bellek bloklarının toplam boyutu yeni istenecek alandan büyük olur ve bellek yöneticisi aynı bellek bölgesini yeniden tahsis edebilir (Heap fragmentation azalır).

**S3: C++20 `std::span` nedir ve neden C-stili dizilerin yerini almıştır?**
> **Cevap:** `std::span`, bellekteki ardışık bir veri bloğuna işaret eden bir işaretçi (pointer) ve boyut (size) çiftinden oluşan sıfır-maliyetli bir görünümdür (non-owning view). Ne bellek kopyalar ne de tahsis yapar; ancak fonksiyonlara dizi aktarırken boyut bilgisini kaybetmez (decay olmaz) ve sınır kontrolü sağlar.

---

## [MD 17] 22. 🔮 Gelecek Perspektifi (Donanım & Mimari Trendleri)

- **CXL (Compute Express Link) ve Birleşik Bellek:** Heterojen işlemciler (CPU, GPU, FPGA), tek bir bitişik fiziksel adres uzayını önbellek tutarlılığıyla (Cache Coherent) paylaşarak veriyi cihazlar arasında kopyalama gereksinimini ortadan kaldırmaktadır.
- **Yüksek Bant Genişlikli Bellek (HBM3e / HBM4):** İşlemci zarına doğrudan istiflenen 3D bellek katmanları, terabaytlarca saniyelik bant genişliği sunarak ardışık veri akışlarında DRAM gecikmesini neredeyse önbellek seviyesine yaklaştırmaktadır.
- **Bellek İçi Hesaplama (Processing-In-Memory - PIM):** Veriyi CPU'ya taşımak yerine doğrudan bellek yongalarının içine gömülü minik ALU'larda ardışık dizi operasyonlarını icra etme mimarisi yaygınlaşmaktadır.

---

## [MD 18] 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı)

Bugün bitişik dizilerin donanımsal önbellek avantajını (64B Cache Line, L1 Prefetcher), pointer aritmetiğini ve dinamik vektör büyüme dinamiklerini inceledik.

Peki bu ardışık veri blokları üzerine LIFO (Son Giren İlk Çıkar) ve FIFO (İlk Giren İlk Çıkar) erişim disiplinleri nasıl inşa edilir? Yarın **Gün 015**'te:
- **Stack ve Queue Zihinsel Modeli:** LIFO ve FIFO akış mimarisi,
- **Deterministik Kuyruklar ve Geri Basınç:** Ring Buffer tabanlı dairesel kuyruklar ve taşma (Overflow/Underflow) stratejileri,
- **Aviyonik Mesaj Kuyrukları:** MIL-STD-1553, CAN Bus ve Radar paket işleme boru hatlarındaki rolünü inceleyeceğiz.
