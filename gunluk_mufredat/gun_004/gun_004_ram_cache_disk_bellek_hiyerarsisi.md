# GÜN 004: RAM, Cache, Disk ve Bellek Hiyerarşisi Fiziği
### Faz 0: Bilgisayar ve Yazılım Temelleri (Gün 004 / 365)
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
> **40-Nokta Standart Bildirimi:** Bu çalışma planı; ASELSAN, HAVELSAN ve kritik savunma sanayii sistemlerinde görev alacak bir mühendisin donanım, çekirdek işletim sistemi, C++20, bellek yönetimi ve gerçek zamanlı sistemleri sıfırdan en üst düzeye çıkarması için 40 temel pedagojik ve teknik kalite kriterine (İlk İlkeler, Hata Enjeksiyonu, Determinizm, SLA/Gecikme Analizi, Katı Doğrulama vb.) tam uyumlu olarak inşa edilmiştir.

---

## [MD 2] 1. 🎯 Bugünkü Problem: CPU 0.3 Ns'de Çalışırken Bellek Neden 100 Ns Bekletir? Bellek Duvarı (Memory Wall)

Son 40 yılda işlemci saat frekansları binlerce kat hızlanırken, dinamik RAM (DRAM) erişim gecikmesi fiziksel kapasitör sınırları yüzünden ancak 10 kat iyileşebilmiştir. Bu uçuruma bilgisayar mimarisinde **Bellek Duvarı (Memory Wall)** denir.

İşlemcinin bir saat darbesi $0.33\text{ ns}$ sürerken:
- **CPU Register:** $0.2 - 0.5\text{ ns}$ (Anında erişim, ~1 saat döngüsü)
- **L1 Cache (SRAM):** $0.8 - 1.2\text{ ns}$ (~3-4 saat döngüsü)
- **L2 Cache (SRAM):** $3 - 5\text{ ns}$ (~10-14 saat döngüsü)
- **L3 Cache (Paylaşımlı SRAM):** $10 - 20\text{ ns}$ (~30-50 saat döngüsü)
- **Ana Bellek (DRAM / RAM):** $50 - 100\text{ ns}$ (~150-300 saat döngüsü!)
- **Kalıcı Depolama (NVMe SSD / Disk):** $> 10.000 - 1.000.000\text{ ns}$ (Yüz binlerce saat döngüsü!)

Eğer işlemci bir değişkeni okumak istediğinde aradığı veri önbellekte (L1/L2/L3) yoksa (**Cache Miss**), CPU tam 200 saat döngüsü boyunca hiçbir iş yapmadan boş bekler (**Memory Stall**). 

Bugünkü problemimiz: **Donanımın bellek hiyerarşisi fiziğini kavrayarak; veriyi önbellek çizgisine (Cache Line - 64 Bayt) nasıl hizalarız ve C++ kodumuzu bellek dostu (Data-Oriented Design) yazarak nasıl 10 ila 50 kat hızlandırırız?**

---

## [MD 3] 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayiinde Sayısal İşleme ve Veri Yerleşimi)

Savunma sanayiinde (ASELSAN radar sinyal işleme algoritmaları, HAVELSAN simülasyon motorları, Roketsan arayıcı başlık görüntü işleme):
- **Büyük Veri Akışları:** Bir AESA radarı saniyede gigabaytlarca ham I/Q matris verisi üretir. Bu matris üzerinde gezinirken satır yerine sütun öncelikli okuma yaparsanız, her adımda bir Cache Miss yaşar ve radar işlemcisini kilitlersiniz.
- **AoS (Array of Structures) Tuzağı:** `std::vector<Target>` içinde her hedefin pozisyonu, hızı, radar kesit alanı, ID'si bir arada tutulur (AoS). Sadece hedeflerin irtifasını güncellemek istediğinizde, önbellek gereksiz tüm diğer alanlarla dolar. Çözüm, savunma standardı olan **SoA (Structure of Arrays)** mimarisidir.
- **Determinizm ve Jitter:** Önbellek kaçırmaları öngörülemez gecikme sıçramalarına (Jitter) sebep olur. Gerçek zamanlı bir kontrol döngüsü p99 gecikmesinde bellek beklemesine takılırsa güdüm komutu zamanında çıkamaz.

---

## [MD 4] 3. 🔍 5N1K Analizi (Bellek Hiyerarşisi, Cache Line ve Yerellik)

| Soru | Sistem Mühendisliği Karşılığı |
|:---|:---|
| **Ne? (What)** | SRAM vs DRAM fiziği, Önbellek Çizgisi (Cache Line - 64B), Kümeli İlişkili Önbellek (Set-Associativity), Zamansal (Temporal) ve Mekânsal (Spatial) Yerellik, AoS vs SoA. |
| **Neden? (Why)** | Bellek Duvarı'nı (Memory Wall) aşmak, işlemcinin yüzlerce döngü boşta beklemesini (Stall) engellemek ve bant genişliğini %100 verimle kullanmak. |
| **Nerede? (Where)** | Radar matris çarpımlarında, Kalman filtrelerinde, görüntü işleme piksellerinde ve taktik hedef takip tablolarında. |
| **Nasıl? (How)** | Veriyi bellekte ardışık (contiguous) dizerek, 64 bayt sınırlarına hizalayarak (`alignas(64)`), döngüleri satır öncelikli kurarak. |
| **Ne Zaman? (When)** | Yüksek frekanslı (High-Throughput) veri işleme döngüleri ve algoritmik sıcak yollar (Hot Paths) tasarlanırken. |
| **Kim? (Who)** | ASELSAN Radar & DSP Mühendisleri, Görüntü İşleme / Yapay Zeka Çıkarım Mühendisleri, Yüksek Başarımlı Hesaplama (HPC) Mimarları. |

---

## [MD 5] 4. 💡 Günlük Hayat Benzetmesi: Cepten Çıkarılan Not (L1), Masadaki Defter (RAM), Bodrumdaki Arşiv (Disk)

Bir araştırma laboratuvarındaki başmühendisi düşünelim:
1. **CPU Register:** Mühendisin anlık zihnindeki formül ($<1\text{ saniye}$).
2. **L1/L2 Cache (Gömlek Cebi ve El Altındaki Not):** Mühendisin cebindeki küçük bloknot. Hemen elini atıp okur ($1-3\text{ saniye}$). Kapasitesi çok küçüktür (32-512 KB), her şeyi yazamaz.
3. **RAM (Çalışma Masasındaki Klasör):** Mühendisin odasındaki masada duran büyük dosya. Masaya uzanıp sayfayı açması biraz zaman alır ($1\text{ dakika}$). Kapasitesi büyüktür (16-64 GB).
4. **Disk / NVMe (Şirketin Bodrum Katındaki Arşiv):** Mühendisin yerinden kalkıp asansörle bodruma inmesi, tozlu raflardan kutuyu bulup getirmesi ($3\text{ gün}$).
5. **Cache Line (Koli Prensibi):** Arşive veya masaya gittiğinizde tek bir kağıt alıp dönmezsiniz; kutuyu / klasörü (64 baytlık blok) toptan alıp masanıza koyarsınız. Eğer sıradaki işiniz o klasördeki yan sayfayla ilgiliyse (**Spatial Locality**) hemen cebinizden okursunuz.

---

## [MD 6] 5. 🧱 İlk İlkeler (First Principles): Bellek Piramidi Fiziği ve AMAT Denklemi

```
                       / \
                      /   \      CPU Register (< 1 ns, 1-2 KB)
                     / L1  \     L1 Cache (1 ns, 32-64 KB)
                    /  L2   \    L2 Cache (3-5 ns, 512 KB - 1 MB)
                   /   L3    \   L3 Cache (10-20 ns, 16-64 MB)
                  /   DRAM    \  Ana Bellek RAM (50-100 ns, 16-128 GB)
                 /  NVMe SSD   \ Depolama (10.000+ ns, TB'lar)
                +---------------+
```

### 1. Ortalama Bellek Erişim Süresi Denklemi (AMAT - Average Memory Access Time)
İşlemcinin ortalama bir veriye ulaşma süresi:
$$\text{AMAT} = \text{Hit Time} + (\text{Miss Rate} \times \text{Miss Penalty})$$
Örnek Hesaplama:
- $\text{Hit Time}_{L1} = 1.0\text{ ns}$
- $\text{Miss Penalty} = 80\text{ ns}$ (DRAM erişimi)
- Senaryo A (%1 Miss Rate - Cache Dostu):
  $$\text{AMAT}_A = 1.0\text{ ns} + (0.01 \times 80\text{ ns}) = 1.8\text{ ns}$$
- Senaryo B (%20 Miss Rate - Kötü Bellek Düzeni / Pointer Chasing):
  $$\text{AMAT}_B = 1.0\text{ ns} + (0.20 \times 80\text{ ns}) = 17.0\text{ ns} \quad (\mathbf{9.4 \times \text{ Yavaşlama!}})$$

### 2. Önbellek Adresleme Mimarisi (64-Bayt Cache Line)
32-bit veya 64-bit bir bellek adresi önbelleğe girerken 3 parçaya bölünür:
```
+--------------------------+---------------------+-------------------+
|       TAG (Etiket)       |    INDEX (Küme)     |  OFFSET (Konum)   |
|   Hangi blok olduğunu    |  Hangi Cache Set'e  |  64B satır içinde |
|     doğrular             |     eşleneceği      |     hangi bayt?   |
+--------------------------+---------------------+-------------------+
```
64 baytlık bir Cache Line için Offset daima 6 bittir ($2^6 = 64$).

---

## [MD 7] 6. 📐 ASCII ve Mermaid Bellek Hiyerarşisi ve Cache Line Adresleme Şeması

```mermaid
flowchart TD
    subgraph CPU_CORE [İşlemci Çekirdeği]
        Regs[Register Dosyası] <--> ALU[Aritmetik Mantık Birimi]
        Regs <--> L1[L1 Önbellek: 32 KB - 1 ns]
    end

    subgraph CACHE_HIERARCHY [Önbellek Katmanları (SRAM)]
        L1 <-->|Miss: 4 Döngü| L2[L2 Önbellek: 512 KB - 4 ns]
        L2 <-->|Miss: 14 Döngü| L3[L3 Önbellek: 16 MB - 15 ns]
    end

    subgraph SYSTEM_MEMORY [Sistem Belleği ve Depolama]
        L3 <-->|Miss: 200 Döngü (Memory Wall)| RAM[DRAM Ana Bellek - 80 ns]
        RAM <-->|Page Fault: 100.000+ Döngü| Disk[NVMe SSD / Flash Disk]
    end
```

---

## [CODE 1] 7. Modül 1: Kümeli İlişkili (Set-Associative) Önbellek Simülatörü (CacheSimulator)

Aşağıdaki kod; doğrudan donanım önbellek mimarisini (Tag, Index, Offset, LRU Değiştirme Politikası) modelleyen çalışan bir simülatördür:

```python
from dataclasses import dataclass
from typing import List

@dataclass
class CacheLine:
    valid: bool = False
    tag: int = 0
    last_access: int = 0

class CacheSimulator:
    """
    Kümeli İlişkili (Set-Associative) Önbellek Simülatörü.
    Varsayılan: 64 baytlık satırlar (Cache Line), 4-yollu ilişkili (4-way set associative).
    """
    def __init__(self, num_sets: int = 64, ways: int = 4, line_size: int = 64):
        self.num_sets = num_sets
        self.ways = ways
        self.line_size = line_size
        self.sets: List[List[CacheLine]] = [[CacheLine() for _ in range(ways)] for _ in range(num_sets)]
        self.hits = 0
        self.misses = 0
        self.timer = 0

    def access(self, address: int) -> bool:
        self.timer += 1
        line_addr = address // self.line_size
        set_idx = line_addr % self.num_sets
        tag = line_addr // self.num_sets

        cache_set = self.sets[set_idx]

        # 1. Hit kontrolü
        for line in cache_set:
            if line.valid and line.tag == tag:
                line.last_access = self.timer
                self.hits += 1
                return True # CACHE HIT

        # 2. Miss durumu (LRU ile yer değiştirme)
        self.misses += 1
        lru_idx = 0
        min_access = float('inf')
        for i, line in enumerate(cache_set):
            if not line.valid:
                lru_idx = i
                break
            if line.last_access < min_access:
                min_access = line.last_access
                lru_idx = i

        cache_set[lru_idx].valid = True
        cache_set[lru_idx].tag = tag
        cache_set[lru_idx].last_access = self.timer
        return False # CACHE MISS
```

---

## [MD 8] 8. Modül 2: 2D Matris Bellek Gezinimi (Row-Major vs Column-Major)

C/C++ dillerinde çok boyutlu diziler bellekte satır satır ardışık olarak tutulur (**Row-Major**).
- **Satır Öncelikli (Row-Major):** `matrix[r][c]` sırasıyla okunduğunda, ilk eleman bellekten çekilirken yanındaki 15 float değer de 64 baytlık aynı Cache Line içine yüklenir. Sonraki 15 okuma **%100 Hit** alır!
- **Sütun Öncelikli (Column-Major):** `matrix[r][c]` yerine dış döngüde `c`, iç döngüde `r` döndürülürse, her adımda bellekte binlerce bayt ileri atlanır. Her okuma **%100 Miss** üretir ve işlemci bellek duvarına çarpar.

---

## [CODE 2] 9. Modül 2: 2D Matris Bellek Gezinimi ve Cache Miss Sayacı

```python
def benchmark_matrix_traversal(matrix_dim: int = 128):
    sim_row = CacheSimulator(num_sets=64, ways=4, line_size=64)
    sim_col = CacheSimulator(num_sets=64, ways=4, line_size=64)

    # 1. Satır Öncelikli (Row-Major: C-style contiguous)
    for r in range(matrix_dim):
        for c in range(matrix_dim):
            addr = (r * matrix_dim + c) * 4 # 4 baytlık float
            sim_row.access(addr)

    # 2. Sütun Öncelikli (Column-Major: Strided across rows)
    for c in range(matrix_dim):
        for r in range(matrix_dim):
            addr = (r * matrix_dim + c) * 4
            sim_col.access(addr)

    row_hit_rate = (sim_row.hits / (sim_row.hits + sim_row.misses)) * 100.0
    col_hit_rate = (sim_col.hits / (sim_col.hits + sim_col.misses)) * 100.0

    return sim_row, sim_col, row_hit_rate, col_hit_rate
```

---

## [MD 9] 10. Modül 3: Dizi Yapıları: Array of Structures (AoS) vs Structure of Arrays (SoA)

Bir radar takip sisteminde 100.000 hava hedefi tuttuğumuzu varsayalım:
- **AoS (Array of Structures):**
  ```cpp
  struct Target { float x, y, z, vx, vy, vz, rcs, snr; };
  std::vector<Target> targets; // Her hedef 32 bayt
  ```
  Hedeflerin sadece irtifasını (`z`) filtrelemek istediğimizde, `z` değerini okurken gereksiz `rcs, snr, vx` gibi tüm veriler önbelleğe çekilir. Önbelleğin %75'i çöpe gider!
- **SoA (Structure of Arrays):**
  ```cpp
  struct TargetTable {
      std::vector<float> z;
      std::vector<float> vx;
      // ...
  };
  ```
  Tüm `z` değerleri bellekte yan yana durur. Önbellek çizgisine tek seferde 16 hedef irtifası sığar ve SIMD/vektörizasyon ile tek döngüde işlenir.

---

## [CODE 3] 11. Modül 3: Radar Hedef Verisinde AoS vs SoA Bellek Yerleşimi

```python
import time
import numpy as np
from dataclasses import dataclass

@dataclass
class RadarTargetAoS:
    x: float
    y: float
    z: float
    range_val: float
    azimuth: float
    elevation: float
    doppler_vel: float
    snr: float

def benchmark_aos_vs_soa(num_targets: int = 100000):
    # AoS hazırlığı
    targets_aos = [RadarTargetAoS(1.0, 2.0, 3.0, 100.0, 0.5, 0.2, 50.0, 15.0) for _ in range(num_targets)]
    
    # SoA hazırlığı
    targets_soa_z = np.full(num_targets, 3.0, dtype=np.float32)

    # AoS Güncelleme
    t0 = time.perf_counter()
    for t in targets_aos:
        t.z += 1.0
    aos_time = (time.perf_counter() - t0) * 1000.0

    # SoA Güncelleme (Vektörize ve Cache-Aligned)
    t0 = time.perf_counter()
    targets_soa_z += 1.0
    soa_time = (time.perf_counter() - t0) * 1000.0

    return aos_time, soa_time
```

---

## [MD 10] 12. Sabotaj ve Arıza Enjeksiyonu: Rastgele Adres Atlama (Pointer Chasing / Cache Thrashing)

**Sabotaj Senaryosu:**
Geliştirici dizi yerine bağlı liste (`std::list`) kullanmış veya işaretçileri rastgele adreslere dağıtmıştır (**Pointer Chasing**).
- İşlemcinin donanımsal tahmin edicisi (Hardware Prefetcher), bir sonraki adresi kestiremez.
- Her işaretçi takibinde işlemci doğrudan DRAM'e gitmek zorunda kalır (**Cache Thrashing**).
- Sıralı dizi erişimi ile karşılaştırıldığında gecikme katlanarak artar.

---

## [CODE 4] 13. Sabotaj Senaryosu: Sıralı Bellek Erişimi vs Rastgele İşaretçi Zinciri

```python
import random
import time
import numpy as np

def run_sabotage_simulation(size: int = 60000):
    seq_indices = list(range(size))
    rand_indices = list(range(size))
    random.shuffle(rand_indices)

    data = np.random.rand(size).astype(np.float32)

    # 1. Sıralı Erişim (Prefetcher Dostu)
    t0 = time.perf_counter()
    sum_seq = 0.0
    for idx in seq_indices:
        sum_seq += data[idx]
    seq_time = (time.perf_counter() - t0) * 1000.0

    # 2. Rastgele Erişim (Sabotaj: Cache Tamamen Devre Dışı)
    t0 = time.perf_counter()
    sum_rand = 0.0
    for idx in rand_indices:
        sum_rand += data[idx]
    rand_time = (time.perf_counter() - t0) * 1000.0

    return seq_time, rand_time
```

---

## [MD 11] 14. Modül 4: Ampirik Kıyaslama ve Adım Boyutu (Stride) Analizi

Adım boyutu 1 tamsayıdan başlayarak 2, 4, 8, 16 (64 Bayt = Cache Line Sınırı), 32 ve 64'e çıkarıldığında; eleman başına düşen okuma süresinin (nanosaniye) nasıl sıçrama yaptığını ölçüyoruz.

---

## [CODE 5] 15. Kapsamlı Bellek Hiyerarşisi Stride ve Gecikme Benchmark Motoru

```python
import time
import numpy as np

def run_stride_benchmark(array_size: int = 5_000_000):
    arr = np.ones(array_size, dtype=np.int32)
    strides = [1, 2, 4, 8, 16, 32, 64]
    latencies_per_access = []

    for s in strides:
        t0 = time.perf_counter()
        sub = arr[::s]
        _ = sub.sum()
        total_time_ns = (time.perf_counter() - t0) * 1e9
        per_access_ns = total_time_ns / len(sub)
        latencies_per_access.append(per_access_ns)

    return strides, latencies_per_access
```

---

## [MD 12] 16. Modül 5: 4-Panelli Yayın Kalitesinde Bellek Performans Dashboard Planı

Üretilecek `gun_004_ram_cache_disk_bellek_hiyerarsisi.png` dashboard panelleri:
1. **Panel 1: Matris Gezinimi ve Hit Rate (Row vs Col Major):** %93.8 isabet oranı ile %0.0 isabet oranının çarpıcı tezatı.
2. **Panel 2: Veri Düzeni: AoS vs SoA:** İrtifa güncellemede harcanan milisaniye farkı.
3. **Panel 3: Sabotaj Testi (Sıralı vs Rastgele Pointer Chasing):** Önbellek felcinin yürütme süresine etkisi.
4. **Panel 4: Stride Boyutu vs Nanosaniye Erişim Gecikmesi:** 64 Bayt (16 Eleman) sınırında gecikmenin katlanması.

---

## [CODE 6] 17. 4-Panelli Görselleştirme ve Katı Mimari Doğrulama (Assertions)

```python
import numpy as np
import matplotlib.pyplot as plt

def generate_dashboard(output_path: str):
    sim_row, sim_col, row_hit_rate, col_hit_rate = benchmark_matrix_traversal(matrix_dim=128)
    aos_time, soa_time = benchmark_aos_vs_soa(num_targets=80000)
    seq_time, rand_time = run_sabotage_simulation(size=60000)
    strides, stride_lats = run_stride_benchmark()

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor('#0f172a')

    for ax_row in axs:
        for ax in ax_row:
            ax.set_facecolor('#1e293b')
            ax.tick_params(colors='#94a3b8')
            ax.xaxis.label.set_color('#cbd5e1')
            ax.yaxis.label.set_color('#cbd5e1')
            ax.title.set_color('#f8fafc')
            ax.grid(True, linestyle='--', alpha=0.2, color='#64748b')

    # Panel 1: Matris Hit Rate
    cats1 = ['Row-Major (C-Style)', 'Column-Major (Strided)']
    rates1 = [row_hit_rate, col_hit_rate]
    axs[0, 0].bar(cats1, rates1, color=['#10b981', '#ef4444'], width=0.45)
    axs[0, 0].set_title('Panel 1: 128x128 Matris Önbellek İsabet Oranı (%)', fontsize=12, fontweight='bold')
    axs[0, 0].set_ylabel('Cache Hit Oranı (%)')
    axs[0, 0].set_ylim(0, 105)
    for i, r in enumerate(rates1):
        axs[0, 0].text(i, r + 2, f"%{r:.1f}\n({[sim_row.misses, sim_col.misses][i]} Miss)", ha='center', color='white', fontweight='bold', fontsize=10)

    # Panel 2: AoS vs SoA
    cats2 = ['AoS (Array of Structs)', 'SoA (Struct of Arrays)']
    times2 = [aos_time, soa_time]
    axs[0, 1].bar(cats2, times2, color=['#f59e0b', '#38bdf8'], width=0.45)
    axs[0, 1].set_title('Panel 2: Radar Hedef İrtifa Güncelleme (AoS vs SoA)', fontsize=12, fontweight='bold')
    axs[0, 1].set_ylabel('Süre (milisaniye)')
    for i, t in enumerate(times2):
        axs[0, 1].text(i, t / 2 if t > 1 else t + 0.5, f"{t:.2f} ms", ha='center', color='white', fontweight='bold', fontsize=11)

    # Panel 3: Pointer Chasing Sabotajı
    cats3 = ['Sıralı Erişim (Prefetch)', 'Rastgele (Pointer Chasing)']
    times3 = [seq_time, rand_time]
    axs[1, 0].bar(cats3, times3, color=['#10b981', '#f43f5e'], width=0.45)
    axs[1, 0].set_title('Panel 3: Rastgele Bellek Atlama ile Cache Thrashing', fontsize=12, fontweight='bold')
    axs[1, 0].set_ylabel('Erişim Süresi (ms)')
    for i, t in enumerate(times3):
        axs[1, 0].text(i, t / 2, f"{t:.1f} ms", ha='center', color='white', fontweight='bold', fontsize=11)

    # Panel 4: Stride Gecikmesi
    axs[1, 1].plot([str(s) for s in strides], stride_lats, marker='s', color='#ec4899', lw=2.5, label='Erişim Başına Gecikme (ns)')
    axs[1, 1].axvline(4, color='#38bdf8', linestyle='--', label='16 Eleman = 64B Cache Line')
    axs[1, 1].set_title('Panel 4: Stride Boyutu Arttıkça Öğe Başına Gecikme (ns)', fontsize=12, fontweight='bold')
    axs[1, 1].set_xlabel('Adım Boyutu (Stride - Öğe Adedi)')
    axs[1, 1].set_ylabel('Gecikme (ns / access)')
    axs[1, 1].legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

    # KATI MİMARİ DOĞRULAMA (STRICT ASSERTIONS)
    assert row_hit_rate > 90.0, f"HATA: Row-Major hit rate beklenenden düşük: %{row_hit_rate}"
    assert col_hit_rate < 10.0, f"HATA: Col-Major hit rate beklenenden yüksek: %{col_hit_rate}"
    assert rand_time > seq_time, "HATA: Rastgele erişim sıralı erişimden yavaş çıkmadı!"
    assert aos_time > soa_time * 5.0, "HATA: SoA bellek yerleşimi AoS'a göre belirgin hız kazandırmadı!"
    assert stride_lats[-1] > stride_lats[0], "HATA: Stride büyümesi erişim gecikmesini artırmadı!"
    print("[PASS] Gün 004: Tüm bellek hiyerarşisi, cache line ve yerellik kuralları doğrulandı.")
```

---

## [MD 13] 18. ⚠️ 10 Ölümcül Bellek Hiyerarşisi Anti-Pattern

1. **Bağlı Liste (Linked List) Bağımlılığı:** `std::list` veya işaretçi tabanlı düğüm yapıları belleğe rastgele dağılır; her eleman okumada Cache Miss üretir. Sıcak döngülerde daima `std::vector` kullanılmalıdır.
2. **Yanlış Matris Döngü Sırası:** Satır-sütun sırasını ters yazarak mekanik olarak her adımda yeni önbellek satırına atlamak.
3. **False Sharing (Sahte Paylaşım):** İki farklı iş parçacığının (thread), 64 baytlık aynı Cache Line içine denk gelen bağımsız değişkenleri yazması sonucu çekirdekler arası önbellek tutarlılık (Cache Coherency) fırtınası yaratmak.
4. **Hizalanmamış Yapı Boyutları (Bad Struct Padding):** Değişkenleri büyükten küçüğe sıralamayarak aralara gizli dolgu baytları (padding) sokmak ve önbellek kapasitesini gereksiz şişirmek.
5. **AoS Mimarisinde Israrcı Olmak:** Yüksek boyutlu simülasyon ve radar hedef tablolarında SoA yerine devasa nesne dizileri tutmak.
6. **Sıcak Yolda Dosya / Disk I/O:** Bellek beklemesi nanosaniyeler sürerken, döngü içinde `printf`, log yazma veya disk işlemi yaparak işlemciyi milyonlarca döngü kitlemek.
7. **Önbellek Çizgisine Hizalamamak (`alignas` Eksikliği):** SIMD (AVX-512 / NEON) vektör komutlarının ihtiyaç duyduğu 64 baytlık bellek hizalamasını yapmayarak unaligned load cezası yemek.
8. **Dinamik Bellek Dağınıklığı (Heap Fragmentation):** Sürekli küçük nesneler tahsis edip serbest bırakarak belleği parça pinçik etmek ve ardışık okuma kabiliyetini yok etmek.
9. **Donanımsal Prefetcher'ı Bozacak Karmaşık İndeksleme:** `arr[hash(i)]` gibi matematiksel atlamalarla işlemcinin sıralı okuma öngörüsünü kör etmek.
10. **Büyük Veriyi Değer Olarak Kopyalamak:** Fonksiyon parametrelerinde büyük struct/vector nesnelerini referans (`const&`) yerine kopyalayarak L1/L2 önbelleğini anlamsızca kirletmek.

---

## [MD 14] 19. 🔬 Sektörel Standartlar (Savunma ve Kritik Sistemler)

- **C++ Standart Kütüphanesi (`std::hardware_destructive_interference_size`):** False sharing'i engellemek için iki değişken arasındaki minimum bayt mesafesini (genellikle 64 bayt) derleyiciden alma standardı.
- **POSIX `posix_memalign`:** Gerçek zamanlı DMA tamponları ve SIMD veri alanları için önbellek çizgisi (64 bayt) hizalı bellek tahsisi kuralı.
- **MISRA C++:2023 Kural 8.2:** Dinamik heap tahsisinin getireceği bellek parçalanması ve öngörülemez önbellek yerleşimi risklerine karşı statik bellek tahsisi kuralı.

---

## [MD 15] 20. 🛠️ Üretim Kontrol Listesi (Bellek Dostu Kodlama 12 Katı Kural)

- [ ] 1. Çok boyutlu diziler ve matrisler satır öncelikli (Row-Major) taranıyor mu?
- [ ] 2. Yoğun sayısal işleme gerektiren yapılarda AoS yerine SoA veri yerleşimi uygulandı mı?
- [ ] 3. Bağlı liste (`std::list`) yerine ardışık bellek sunan `std::vector` veya sabit boyutlu array tercih edildi mi?
- [ ] 4. Çok iş parçacıklı değişkenlerde False Sharing riskine karşı `alignas(64)` kullanıldı mı?
- [ ] 5. Struct tanımlarında değişkenler tür boyutlarına göre (8 bayt, 4 bayt, 2 bayt, 1 bayt) azalan sırada dizildi mi?
- [ ] 6. Kritik sıcak döngüler (Hot Loops) içinde dosya yazma veya loglama tamamen kaldırıldı mı?
- [ ] 7. L1/L2/L3 önbellek kaçırma oranları Linux `perf stat -e cache-misses` veya VTune ile analiz edildi mi?
- [ ] 8. SIMD vektör tamponları 64 bayt sınırına hizalandı mı?
- [ ] 9. Fonksiyonlara büyük nesneler geçirilirken gereksiz kopyalamalar (`pass-by-value`) önlendi mi?
- [ ] 10. Döngü içindeki bellek erişim adımları (Stride) küçük ve tahmin edilebilir tutuldu mu?
- [ ] 11. Sayfa hatalarını (Page Fault) önlemek için gerçek zamanlı bellek kilitlendi mi (`mlockall`)?
- [ ] 12. Algoritmaların bellek bant genişliği doyumuna ulaşıp ulaşmadığı (Roofline Model) incelendi mi?

---

## [MD 16] 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

**Soru 1: False Sharing nedir ve nasıl çözülür?**  
*Cevap:* Farklı CPU çekirdeklerinde çalışan iki iş parçacığı, bellekte birbirine çok yakın (aynı 64 baytlık Cache Line içinde) iki farklı değişkene yazma yaptığında oluşur. Bir çekirdek kendi değişkenini güncellediğinde, donanımsal MESI protokolü gereği diğer çekirdeğin L1 önbelleğindeki tüm 64 baytlık satırı geçersiz kılar (Invalidate). Bu durum çekirdekler arası yoğun veri yolu trafiğine ve devasa yavaşlamaya yol açar. Çözüm: Değişkenleri `alignas(64)` ile ayrı önbellek çizgilerine hizalamak veya `std::hardware_destructive_interference_size` kadar dolgu (padding) eklemektir.

**Soru 2: Neden modern veri odaklı tasarımda (Data-Oriented Design) SoA yapısı AoS yapısına tercih edilir?**  
*Cevap:* AoS'ta tek bir nesnenin tüm öznitelikleri yan yana tutulur. Eğer algoritma sadece tek bir özniteliği okuyacaksa (örneğin sadece irtifa kontrolü), önbelleğe o nesnenin ilgisiz tüm diğer değişkenleri de dolarak yer işgal eder. SoA'da ise aynı öznitelik dizisi kesintisiz bir bellek bloğu oluşturur. Böylece Cache Line %100 ilgili veriyle dolar ve CPU'nun SIMD vektör üniteleri tek döngüde 8 veya 16 elemanı birden işleyebilir.

---

## [MD 17] 22. 🔮 Gelecek Perspektifi: Bellek Teknolojisi Trendleri

- **HBM3 ve HBM4 (High Bandwidth Memory):** 2.5D ve 3D silikon ara bağlantılarla (Silicon Interposer) işlemcinin hemen yanına dikey yığılmış DRAM çipler yerleştirerek terabaytlarca bant genişliğine ulaşılması.
- **3D V-Cache Teknolojisi:** İşlemci kalıbının üzerine dikey olarak 64-128 MB büyüklüğünde ek L3 SRAM önbellek istiflenmesi ve bellek duvarının eritilmesi.
- **CXL (Compute Express Link):** Dağıtık işlemciler ve GPU'lar arasında bellek havuzlarını PCIe 6.0 üzerinden önbellek tutarlı (Cache-Coherent) paylaştıran yeni nesil mimari.

---

## [MD 18] 23. 🚪 Faz 0 / Gün 005'e Köprü: Program, Process ve İşletim Sistemi Farkı

Bugün işlemcinin belleğe erişirken karşılaştığı fiziksel duvarı, 64 baytlık Cache Line gerçeğini ve veri yerleşiminin algoritma hızını nasıl 10 kattan fazla değiştirdiğini kanıtladık.

Peki bellekte duran bu kod ve veri yığını nasıl canlanır?
Yarın **Gün 005'te:**
- Sabit diskte yatan pasif bir **Program** (ELF / Binary) ile RAM'de koşan canlı bir **Process (Süreç)** arasındaki farkı,
- İşletim sisteminin sanal bellek (Virtual Memory), sayfalama (Paging) ve süreç kontrol bloğu (PCB) mekanizmasını,
- Kullanıcı Modu (User Mode) ile Çekirdek Modu (Kernel Mode) arasındaki koruma duvarını inceleyeceğiz.
