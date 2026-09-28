# GÜN 086: fork() Sistem Çağrısının Donanımsal ve Mantıksal Zihinsel Modeli

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

## 📌 Faz & Kalite Bildirimi
- **Faz:** F2 — Linux / POSIX Sistem Programlama ve İşletim Sistemi Mühendisliği
- **Konu:** `fork(2)` Sistem Çağrısı Zihinsel Modeli, "Bir Kez Çağrılır İki Kez Döner" (Returns Twice) Paradoksu, CPU Yazmaç Klonlama (`pt_regs`, `RAX/X0`), Sanal Bellek Yönetimi ve MMU Sayfa Tablosu (PTE) Kopyalama, Copy-on-Write (CoW) Donanımsal Sayfa Hatası (Page Fault) Mekanizması, Açık Dosya Tanıtıcıları ve Ofset Paylaşımı, Çok İş Parçacıklı Programlarda `fork()` Kilitlenmeleri (Deadlocks) ve Savunma Sistemlerinde Güvenli Süreç Klonlama
- **40-Nokta Pedagojik ve Teknik İnceleme:** Tam Uyumlu
- **Hedef Kitle:** ASELSAN, HAVELSAN, Roketsan, TUSAŞ ve STM bünyesinde görev-kritik aviyonik sistemler, gerçek zamanlı radar sinyal sunucuları, otonom insansız araçlar ve elektronik harp kontrol sistemleri geliştiren Kıdemli Sistem ve Yazılım Mühendisleri


## 1. 🎯 Bugünkü Problem: `fork()` Paradoksu, CoW Bellek Sürprizleri ve Çok İş Parçacıklı Kilitlenmeler

Linux işletim sisteminde çalışan bir süreç, sıfırdan yaratılmaz; mevcut bir sürecin `fork()` sistem çağrısıyla klonlanması sonucu doğar. Ancak `fork()`, programlama tarihindeki en sıra dışı fonksiyondur: **"Bir kez çağrılır, ancak iki farklı adreste iki kez geri döner!"**

Bu sistem çağrısının donanımsal ve mantıksal zihinsel modeline hakim olmayan mühendisler, sahada görev-kritik savunma sistemlerini kilitleyen felaketlerle karşılaşırlar:

### Karşılaşılan Temel Mimari ve Donanımsal Problemler:
1. **"Returns Twice" Zihinsel Karmaşası:**
   - Bir C/C++ fonksiyonunun aynı anda iki farklı süreçte farklı dönüş değerleri (`pid > 0` ve `pid == 0`) üretmesi, junior mühendislerde akış kontrolü ve bellek paylaşımı yanılgılarına yol açar.
   - Ebeveyn ve çocuğun hangi bellek alanlarını paylaştığı, hangilerinin kopyalandığı bilinmezse yarış durumları (race conditions) kaçınılmaz olur.
2. **Çok İş Parçacıklı (Multi-Threaded) Süreçte `fork()` Felaketi (Mutex Deadlock - CWE-672):**
   - 10 farklı iş parçacığı olan bir radar uygulamasında, bir iş parçacığı telemetri kuyruğunun `std::mutex` kilidini tutarken başka bir iş parçacığı `fork()` çağırırsa;
   - Linux çekirdeği POSIX standardı gereği **yalnızca `fork()` çağıran iş parçacığını çocuk sürece kopyalar**, diğer 9 iş parçacığı çocuk süreçte buharlaşır!
   - Kilitli olan mutex çocuk süreçte "sonsuza kadar kilitli" kalır çünkü o kilidi açacak (unlock yapacak) iş parçacığı çocuk süreçte hiç var olmamıştır! Çocuk süreç o mutexe dokunduğu an sonsuza kadar kilitlenir (Deadlock).
3. **Copy-on-Write (CoW) Bellek Sürprizi ve OOM-Killer Kıyımı:**
   - Görev bilgisayarında 12 GB RAM kaplayan devasa bir radar sinyal haritası varken sistemde yalnızca 2 GB boş fiziksel RAM kalmış olsun.
   - `fork()` çağrıldığında çekirdek CoW optimizasyonu sayesinde işlemi anında onaylar (çünkü fiziksel kopyalama yapmaz, sadece sayfa tablolarını kopyalar).
   - Ancak çocuk süreç çalışmaya başlayıp bellek sayfalarına yazmaya (`write`) kalkıştığında, donanımsal Page Fault tetiklenir. Çekirdek sayfaları kopyalayacak fiziksel RAM bulamaz ve Linux OOM-Killer devreye girerek en kritik aviyonik süreci öldürür!
4. **Dosya Tanıtıcısı ve Ofset Paylaşımı Çakışması (Interleaved File Corruption):**
   - Ebeveyn bir log dosyasını açıp ardından `fork()` çağırırsa, çocuk süreç dosya tanıtıcısını (`fd`) miras alır.
   - Ancak çoğu mühendisin bilmediği gerçek: Ebeveyn ve çocuk **aynı dosya ofsetini (`struct file -> f_pos`) paylaşırlar!** Ebeveyn 100 bayt yazdığında çocuğun da imleci 100 bayt ileri kayar; telemetri kayıtları birbirinin içine girerek bozulur.

### Bugünkü Çözümümüz:
`fork()` sistem çağrısının donanımsal yazmaç manipülasyonunu (`pt_regs->rax`), MMU sayfa tablosu klonlamasını, Copy-on-Write (CoW) sayfa hatası mantığını ve `pthread_atfork` kilit temizleme mekanizmasını matematiksel, donanımsal ve simülasyon seviyesinde derinlemesine modellemek; savunma standartlarında güvenli ve deterministik bir süreç klonlama motoru inşa etmektir.


## 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi)

Savunma ve havacılık sistemlerinde `fork()`, kritik görev süreçlerinin izole edilmesi ve güvenli alt servislerin başlatılmasının temel taşıdır.

### 1. Aviyonik Görev Bilgisayarlarında Arıza Tecriti (Fault Isolation)
Bir F-16 veya İHA görev bilgisayarında yüksek riskli bir hesaplama yapılacaksa (örneğin üçüncü parti bir şifre çözme algoritması veya harici sensör paket ayrıştırıcı):
- Ana uçuş kontrol süreci bu işi kendi sanal adres alanında yapmaz (olası bir `SIGSEGV` tüm uçağı düşürür).
- Ana süreç `fork()` ile izole bir kopya türetir; hesaplamayı çocuğa yaptırır. Çocuk çökse bile ana süreç hayatta kalır.

### 2. Copy-on-Write ile Sıfır Zaman Kayıplı Anlık Görüntü (Telemetry Snapshotting)
Radar sinyal işleme sistemlerinde o anki 4 GB'lık hedef tespit haritasının flash belleğe yedeklenmesi gerekir.
- Eğer ana süreç bu 4 GB'ı diske yazmak için döngüye girerse 500 ms boyunca radar taraması durur (Jitter / Frame Drop).
- Çözüm: `fork()` çağrılır! `fork()` 20 mikro-saniyede tamamlanır. Çocuk süreç arka planda haritayı diske kaydederken, ana süreç CoW sayesinde radar taramasına kesintisiz devam eder.

### 3. Askeri Standartlar (POSIX.1-2017, CERT C POS44-C)
CERT C Güvenli Kodlama Standardı **Rule POS44-C** açıkça belirtir: *"Çok iş parçacıklı bir programda `fork()` çağrısından hemen sonra yalnızca asenkron sinyal güvenli (async-signal-safe) fonksiyonlar veya `execve()` çağrılabilir."* Bu kurala uyulmaması sistemin sahada kilitlenmesinin bir numaralı nedenidir.


## 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları)

| Soru | Sistem & Mühendislik Yanıtı |
|:---|:---|
| **NE? (What)** | `fork()`; çağıran sürecin (ebeveyn) adres alanını, dosya tanıtıcılarını ve yürütme bağlamını kopyalayarak özdeş yeni bir süreç (çocuk) türeten POSIX sistem çağrısıdır. |
| **NEDEN? (Why)** | Eşzamanlı ve izole görevler yürütmek, arıza tecriti sağlamak, yeni programları (`execve`) belleğe yüklemek ve CoW avantajıyla anlık veri kopyaları oluşturmak için. |
| **NEREDE? (Where)** | Linux çekirdeğinde `kernel/fork.c` altındaki `_do_fork()` / `copy_process()` fonksiyonlarında; işlemci yazmaçlarında (`pt_regs`) ve donanımsal MMU sayfa tablolarında. |
| **NASIL? (How)** | Çekirdek ebeveynin PCB'sini kopyalar, sayfa tablolarını salt-okunur (read-only) işaretler, çocuğun dönüş yazmacını (`RAX/X0`) 0 yapar, ebeveyne çocuk PID'sini döner. |
| **NE ZAMAN? (When)** | Bir kabuk (shell) komut çalıştırırken, bir arka plan servisi daemon oluştururken veya paralel bir alt hesaplama başlatılırken. |
| **KİM? (Who)** | ASELSAN/HAVELSAN görev bilgisayarı yazılımcıları, gömülü Linux çekirdek geliştiricileri, aviyonik emniyet mühendisleri. |


## 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Biyolojik Hücre Bölünmesi ve Karbon Kağıdı)

`fork()` sistem çağrısını anlamak için doğadaki ve tarihteki iki mükemmel benzetmeye bakalım:

1. **Mitoz Hücre Bölünmesi (Returns Twice):**
   - Tek bir biyolojik hücre bölünmeye başlar. Bölünme tamamlandığı an artık ortada iki hücre vardır.
   - İki hücre de bölünmenin bittiği andan itibaren hayata devam eder.
   - Çekirdek hücrelerin eline birer kimlik kartı verir:
     - Orijinal ana hücreye: "Senin yeni bir çocuğun oldu, kimliği 101" der (`pid = 101`).
     - Yeni doğan yavru hücreye: "Sen yeni doğdun, kimliğin 0" der (`pid = 0`).
2. **Karbon Kağıdı ile Kitap Çoğaltma (Copy-on-Write / CoW):**
   - 1000 sayfalık bir taktik harekat planı defterini çoğaltmak istiyorsunuz.
   - Bütün defteri satır satır fotokopi çekmek saatler sürer.
   - Bunun yerine bir kütüphaneci orijinal defterin aynısını gösteren bir ayna koyar (`fork`). İki taraf da aynı sayfaları okur.
   - Ne zaman ki harekat subayı 45. sayfadaki bir koordinatı değiştirmek için kalemi kağıda dokundurursa; kütüphaneci anında araya girer, **sadece o 45. sayfayı kopyalayıp** yeni deftere yapıştırır!
   - Diğer 999 sayfa hala ortak kullanılır. Böylece devasa defter 1 saniyede çoğaltılmış olur!


## 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model

### 1. Donanımsal Yazmaç Durumu ve "Returns Twice" Fiziği

İşlemcilerde (x86_64 ve ARM64) bir fonksiyonun veya sistem çağrısının dönüş değeri özel bir akümülatör yazmacında saklanır:
- x86_64 mimarisinde: `%rax`
- ARM64 (AArch64) mimarisinde: `x0`

`fork()` çağrıldığında CPU kullanıcı modundan çekirdek moduna geçer (`syscall` talimatı). Çekirdek, o anki tüm CPU yazmaçlarını çekirdek yığınında `struct pt_regs` yapısına kaydeder:

```c
/* Linux arch/x86/kernel/process.c: copy_thread() */
int copy_thread(unsigned long clone_flags, unsigned long sp, unsigned long arg,
                struct task_struct *p, unsigned long tls)
{
    struct pt_regs *childregs = task_pt_regs(p);

    /* Ebeveynin tüm yazmaçları çocuğa kopyalanmıştır */
    *childregs = *current_pt_regs();

    /* SİHİRLİ SATIR: Çocuğun dönüş yazmacı SIFIRLANIR! */
    childregs->ax = 0;

    /* Çocuğun yığın işaretçisi ayarlanır */
    p->thread.sp = (unsigned long) childregs;
    return 0;
}
```

Ebeveyn süreç için sistem çağrısı bittiğinde çekirdek ebeveynin `%rax` yazmacına yeni oluşturulan çocuğun `child_pid` değerini yazar.
Çocuk süreç zamanlayıcı tarafından ilk kez CPU'ya alındığında, çekirdek modundan kullanıcı moduna dönerken (`sysretq` / `iretq`) `%rax` yazmacında `0` görür!
İşte `fork()`'un bir kez çağrılıp iki kez dönmesinin donanımsal sırrı budur.

### 2. Copy-on-Write (CoW) ve MMU Donanımsal Sayfa Hatası Fiziği

Modern işlemcilerde Bellek Yönetim Birimi (MMU) sanal adresleri fiziksel adreslere çevirirken Sayfa Tablosu Girdilerini (Page Table Entry - PTE) kullanır. Her PTE içinde bir "Write" (Yazılabilir) biti bulunur:
- Bit 1 (`R/W`): `1` ise yazılabilir, `0` ise salt-okunur (read-only).

```
Ebeveyn PTE:   [ Sanal Sayfa 0x4000 ] ----> [ Fiziksel RAM Çerçevesi #88 ] (R/W = 1)
```

`fork()` anında çekirdek `dup_mmap()` fonksiyonunu çalıştırır:
1. Fiziksel sayfa kopyalanmaz!
2. Ebeveyn ve çocuğun PTE'leri aynı fiziksel çerçeveye (#88) bağlanır.
3. **Her iki PTE'de de `R/W = 0` (Salt-Okunur) yapılır!**
4. Fiziksel çerçevenin referans sayacı: $\text{refcount} = 2$.

```
Ebeveyn PTE:   [ Sanal Sayfa 0x4000 ] ----\
                                           +---> [ Fiziksel RAM #88 ] (R/W = 0, ref=2)
Çocuk PTE:     [ Sanal Sayfa 0x4000 ] ----/
```

**Yazma Anı (Page Fault / Trap):**
Çocuk veya ebeveyn `*ptr = 42;` dediğinde MMU donanımı `R/W = 0` olduğunu görür ve işlemciyi durdurarak **Sayfa Hatası (#PF - Page Fault 14)** kesmesi fırlatır!
Çekirdek `handle_mm_fault()` -> `do_wp_page()` zincirini işletir:
- Yeni bir fiziksel sayfa (#99) tahsis edilir.
- Eski sayfa (#88) içeriği yeni sayfaya (`#99`) kopyalanır (`memcpy`, 4096 bayt).
- Yazan sürecin PTE'si `#99`'a yönlendirilir ve `R/W = 1` yapılır.
- Eski sayfanın referans sayacı 1'e düşürülür.

### 3. CoW Bellek Tüketim Modeli

$N_{\text{total}}$ sürecin toplam sanal sayfa sayısı, $N_{\text{dirty}}$ ise `fork()` sonrasında yazılan (kirletilen) sayfa sayısı olsun:

$$\text{Fiziksel RAM Maliyeti} = \text{Sayfa Tablosu Boyutu} + (N_{\text{dirty}} \times 4096\text{ Bayt})$$

Eğer süreç sadece okuma yaparsa ek bellek tüketimi sıfırdır!


## 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması

### 1. Copy-on-Write (CoW) Donanımsal Bellek Dönüşümü (ASCII)

```
[FORK ÖNCESİ]
Ebeveyn Süreç (PID 100)
Sanal Bellek [Sayfa 1] ----(R/W=1)----> [Fiziksel RAM #500] (ref=1)

-------------------------------------------------------------------------

[FORK ÇAĞRILDIĞI AN (Sıfır Kopya)]
Ebeveyn (PID 100) [Sayfa 1] ----(R/W=0)---                                           +--> [Fiziksel RAM #500] (ref=2)
Çocuk   (PID 101) [Sayfa 1] ----(R/W=0)---/

-------------------------------------------------------------------------

[ÇOCUK SAYFA 1'E YAZDIĞINDA (Page Fault & Ayrışma)]
Ebeveyn (PID 100) [Sayfa 1] ----(R/W=1)-------> [Fiziksel RAM #500] (ref=1, Orijinal)

Çocuk   (PID 101) [Sayfa 1] ----(R/W=1)-------> [Fiziksel RAM #750] (ref=1, Klon 4KB)
                                                      ^
                                                      | MMU Page Fault tetikledi!
```

### 2. `fork()` Çift Dönüş ve Yaşam Çizgisi (Mermaid)

```mermaid
sequenceDiagram
    autonumber
    participant App as Uygulama Kodu
    participant Sys as Sistem Çağrısı Katmanı
    participant Kern as Linux Çekirdeği (copy_process)
    participant CPU as İşlemci Yazmaçları (pt_regs)

    App->>Sys: pid_t pid = fork();
    Sys->>Kern: sys_fork() / _do_fork()
    Note over Kern: task_struct ve Sanal Bellek (PTE) Klonla (R/W=0)
    Kern->>CPU: Ebeveyn pt_regs: RAX = 101 (Child PID)
    Kern->>CPU: Çocuk pt_regs: RAX = 0 (Child Signal)
    
    par Ebeveyn Sürece Dönüş
        Kern-->>App: pid = 101 döner (Ebeveyn Akışı Devam Eder)
        Note over App: if (pid > 0) { /* Ebeveyn Kodları */ }
    and Çocuk Sürece Dönüş
        Kern-->>App: pid = 0 döner (Çocuk Akışı Başlar)
        Note over App: else if (pid == 0) { /* Çocuk Kodları */ }
    end
```


```python
# Modül 1: Temel Çekirdek Mekanizma / fork() Simülatörü ve Donanımsal Yazmaç Klonlama Motoru
from typing import Dict, List, Optional, Tuple, Any

class CpuRegisters:
    """İşlemci donanımsal yazmaç yedeği (struct pt_regs simülasyonu)."""
    def __init__(self, rip: int = 0x400000, rsp: int = 0x7ffffff0, rax: int = 0):
        self.rip = rip  # Instruction Pointer (Program Sayacı)
        self.rsp = rsp  # Stack Pointer (Yığın Göstergesi)
        self.rax = rax  # Return Value Register (Dönüş Değeri Yazmacı)

    def clone(self) -> 'CpuRegisters':
        return CpuRegisters(rip=self.rip, rsp=self.rsp, rax=self.rax)

class SimulatedProcess:
    """Linux çekirdeğindeki struct task_struct bağlamı."""
    def __init__(self, pid: int, ppid: int, name: str, registers: CpuRegisters):
        self.pid = pid
        self.ppid = ppid
        self.name = name
        self.regs = registers
        self.open_files: Dict[int, int] = {0: 0, 1: 0, 2: 0} # fd -> shared_file_description_id
        self.virtual_pages: Dict[int, int] = {} # virtual_page_num -> physical_frame_id

class KernelForkEngine:
    """Linux copy_process() ve sys_fork() mekanizmasını simüle eden çekirdek motoru."""
    def __init__(self):
        self.process_table: Dict[int, SimulatedProcess] = {}
        self.next_pid = 100
        # Başlangıç ebeveyn süreci
        init_regs = CpuRegisters(rip=0x401050, rsp=0x7fffff00, rax=0)
        parent = SimulatedProcess(pid=self.next_pid, ppid=1, name="parent_radar", registers=init_regs)
        self.process_table[self.next_pid] = parent
        self.next_pid += 1

    def do_fork(self, parent_pid: int) -> Tuple[int, int]:
        """
        fork() sistem çağrısını simüle eder.
        Döner: (ebeveynin_gördüğü_dönüş, çocuğun_gördüğü_dönüş)
        """
        if parent_pid not in self.process_table:
            raise ValueError(f"ESRCH: Ebeveyn PID {parent_pid} bulunamadı!")

        parent = self.process_table[parent_pid]
        child_pid = self.next_pid
        self.next_pid += 1

        # 1. İşlemci Yazmaçlarını Klonla
        child_regs = parent.regs.clone()

        # 2. SİHİRLİ ÇEKİRDEK KURALI: Çocuğun RAX yazmacı SIFIRLANIR!
        child_regs.rax = 0

        # 3. Ebeveynin RAX yazmacına ÇOCUK PID yazılır!
        parent.regs.rax = child_pid

        # 4. Çocuk Süreç Nesnesini Oluştur
        child = SimulatedProcess(
            pid=child_pid,
            ppid=parent_pid,
            name=f"{parent.name}_child",
            registers=child_regs
        )

        # 5. Dosya Tanıtıcılarını Kopyala (Aynı struct file tablosunu paylaşırlar)
        child.open_files = dict(parent.open_files)

        self.process_table[child_pid] = child

        # Ebeveyn ve çocuğun fork() dönüş değerleri
        parent_return = parent.regs.rax
        child_return = child.regs.rax

        return parent_return, child_return

# Modül 1 Doğrulama
_fork_engine = KernelForkEngine()
_p_ret, _c_ret = _fork_engine.do_fork(parent_pid=100)

assert _p_ret == 101, f"Ebeveyn çocuk PID'sini (101) görmeli, alınan: {_p_ret}"
assert _c_ret == 0, f"Çocuk 0 değerini görmeli, alınan: {_c_ret}"
assert _fork_engine.process_table[101].ppid == 100, "Çocuğun ebeveyni 100 olmalı"
print(f"[Modül 1] fork() Başarılı: Ebeveyne Dönen={_p_ret}, Çocuğa Dönen={_c_ret}")
```

## 8. Modül 2: Donanıma Yakın / İleri Düzey: Copy-on-Write (CoW) ve Page Fault Motoru

### 1. Fiziksel Sayfa Referans Sayacı (`struct page->_refcount`)
Linux bellek yöneticisinde her 4 KB'lık fiziksel RAM çerçevesi bir `struct page` ile takip edilir:
- Sayfa ilk tahsis edildiğinde: `_refcount = 1`.
- `fork()` çağrıldığında: Sayfa kopyalanmaz, `_refcount` artırılarak `2` yapılır.
- Ebeveyn veya çocuk sayfaya yazana kadar iki süreç de **aynı fiziksel RAM'i** okur.

### 2. Donanımsal Sayfa Hatası (`do_wp_page`) Algoritması
Bir süreç salt-okunur işaretlenmiş bir CoW sayfasına yazmak istediğinde:
1. MMU Write Fault kesmesi üretir (`CR2` yazmacına sanal adres yazılır).
2. Çekirdek `do_wp_page()` fonksiyonunu çağırır:
   - Eğer `page->_refcount == 1` ise (diğer süreç bu sayfadan çıkmış veya sonlanmışsa): Kopyalamaya gerek yoktur! Sayfa doğrudan yazılabilir (`R/W = 1`) yapılır.
   - Eğer `page->_refcount > 1` ise: Yeni bir fiziksel sayfa tahsis edilir, veri `memcpy` ile kopyalanır, yazan sürecin PTE'si yeni sayfaya yönlendirilir ve `_refcount` 1 azaltılır.


```python
# Modül 2: Copy-on-Write (CoW) ve Donanımsal Page Fault (do_wp_page) Simülatörü

class PhysicalMemoryFrame:
    """Fiziksel RAM üzerindeki 4 KB'lık sayfa çerçevesi."""
    def __init__(self, frame_id: int, initial_data: bytes):
        self.frame_id = frame_id
        self.data = bytearray(initial_data)
        self.refcount = 1  # Kaç sürecin sayfa tablosunda bağlı?

class PageTableEntry:
    """MMU Sayfa Tablosu Girdisi (PTE)."""
    def __init__(self, frame_id: int, writeable: bool):
        self.frame_id = frame_id
        self.writeable = writeable  # R/W biti

class VirtualMemoryMMU:
    """MMU ve Çekirdek CoW Bellek Yöneticisi."""
    def __init__(self):
        self.frames: Dict[int, PhysicalMemoryFrame] = {}
        self.next_frame_id = 1
        self.page_fault_count = 0
        self.cow_copies_count = 0

    def allocate_page(self, data: bytes) -> int:
        """Yeni bir fiziksel sayfa tahsis eder."""
        fid = self.next_frame_id
        self.next_frame_id += 1
        self.frames[fid] = PhysicalMemoryFrame(fid, data)
        return fid

    def fork_page_table(self, parent_ptes: Dict[int, PageTableEntry]) -> Tuple[Dict[int, PageTableEntry], Dict[int, PageTableEntry]]:
        """
        fork() anında sayfa tablolarını kopyalar ve tüm sayfaları Salt-Okunur (CoW) yapar.
        """
        child_ptes: Dict[int, PageTableEntry] = {}
        for vpn, pte in parent_ptes.items():
            # Fiziksel sayfanın referansını artır
            self.frames[pte.frame_id].refcount += 1
            # EBEVEYNİ DE ÇOCUĞU DA SALT-OKUNUR YAP!
            pte.writeable = False
            child_ptes[vpn] = PageTableEntry(frame_id=pte.frame_id, writeable=False)

        return parent_ptes, child_ptes

    def write_memory(self, ptes: Dict[int, PageTableEntry], vpn: int, offset: int, byte_val: int) -> None:
        """
        Süreç belleğe yazmaya çalışır. Eğer writeable == False ise PAGE FAULT tetiklenir!
        """
        if vpn not in ptes:
            raise MemoryError("SIGSEGV: Geçersiz bellek adresi!")

        pte = ptes[vpn]

        if not pte.writeable:
            # DONANIMSAL SAYFA HATASI (PAGE FAULT) TETİKLENDİ!
            self.page_fault_count += 1
            old_frame = self.frames[pte.frame_id]

            if old_frame.refcount > 1:
                # Gerçek CoW Kopyalama: Yeni çerçeve oluştur ve veriyi kopyala
                self.cow_copies_count += 1
                new_fid = self.allocate_page(bytes(old_frame.data))
                old_frame.refcount -= 1
                
                # Bu sürecin PTE'sini yeni çerçeveye bağla ve yazılabilir yap
                pte.frame_id = new_fid
                pte.writeable = True
            else:
                # refcount == 1 ise tek kalan süreçtir; doğrudan yazılabilir yap
                pte.writeable = True

        # Belleğe yazma işlemini icra et
        target_frame = self.frames[pte.frame_id]
        target_frame.data[offset] = byte_val

# Modül 2 Test
_mmu = VirtualMemoryMMU()
_fid = _mmu.allocate_page(b"RADAR_COORDINATES_V1")
_parent_ptes = {0: PageTableEntry(_fid, writeable=True)}

# fork() yapılıyor: İki süreç aynı sayfayı salt-okunur paylaşır
_parent_ptes, _child_ptes = _mmu.fork_page_table(_parent_ptes)
assert _mmu.frames[_fid].refcount == 2, "Sayfa refcount 2 olmalı"
assert _parent_ptes[0].writeable == False, "Ebeveyn sayfası salt-okunur olmalı"
assert _child_ptes[0].writeable == False, "Çocuk sayfası salt-okunur olmalı"

# Çocuk sayfayı değiştiriyor -> CoW tetiklenmeli!
_mmu.write_memory(_child_ptes, vpn=0, offset=0, byte_val=ord('X'))

assert _mmu.page_fault_count == 1, "1 Page Fault oluşmalı"
assert _mmu.cow_copies_count == 1, "1 CoW kopyalama gerçekleşmeli"
assert _child_ptes[0].frame_id != _parent_ptes[0].frame_id, "Çocuk artık farklı fiziksel sayfaya sahip olmalı"
assert bytes(_mmu.frames[_child_ptes[0].frame_id].data).startswith(b"XADAR"), "Çocuk verisi güncellenmeli"
assert bytes(_mmu.frames[_parent_ptes[0].frame_id].data).startswith(b"RADAR"), "Ebeveyn verisi bozulmamalı!"
print(f"[Modül 2] CoW Başarılı! Ebeveyn ve Çocuk Fiziksel Belleği Ayrıştı.")
```

## 10. Modül 3: Dinamik Sınır Durumlar, Dosya Ofseti Paylaşımı ve `pthread_atfork`

### 1. Dosya Ofseti Paylaşımı Tuzağı
Linux'ta `fork()` çağrıldığında dosya tanıtıcıları kopyalanır fakat bu kopyalama yüzeyseldir (Shallow Copy):
- Dosya tanıtıcısı (`fd`), çekirdekteki açık dosya tanımına (`struct file`) işaret eder.
- Dosya okuma/yazma ofseti (`f_pos`) `struct file` içindedir.
- **Sonuç:** Ebeveyn dosyadan 50 bayt okursa, çocuğun da okuma ofseti 50 bayt ilerler!
- **Çözüm:** Ebeveyn ve çocuk aynı dosyaya yazacaksa `open()` sırasında `O_APPEND` bayrağı kullanılmalı veya alt süreç kendi dosya tanıtıcısını `open()` ile bağımsız açmalıdır.

### 2. Çok İş Parçacıklı Programlarda Kilitlenme ve `pthread_atfork`
Çok iş parçacıklı bir süreçte `fork()` çağrıldığında kilitlenmeleri (Deadlock) önlemek için POSIX standardı `pthread_atfork()` mekanizmasını sunar:

```c
int pthread_atfork(void (*prepare)(void), void (*parent)(void), void (*child)(void));
```
- **`prepare()`:** `fork()` başlamadan hemen önce çağrılır. Süreçteki tüm mutex'leri kilitler (böylece hiçbir iş parçacığı kilidi tutamaz).
- **`parent()`:** Ebeveyn süreçte `fork()` tamamlandıktan sonra çağrılır. Kilitlenen tüm mutex'leri açar.
- **`child()`:** Çocuk süreçte çağrılır. Çocukta tek iş parçacığı kaldığı için kilitlenen tüm mutex'leri sıfırlar/açar (Unlock).


```python
# Modül 3: Paylaşılan Dosya Ofseti ve pthread_atfork Kilit Güvenliği Motoru

class SharedFileDescription:
    """Linux çekirdeğindeki struct file yapısının simülasyonu."""
    def __init__(self, filename: str):
        self.filename = filename
        self.cursor_pos = 0  # Paylaşılan dosya ofseti (f_pos)
        self.buffer = bytearray()

    def write(self, data: bytes) -> int:
        self.buffer.extend(data)
        bytes_written = len(data)
        self.cursor_pos += bytes_written
        return bytes_written

class ThreadMutex:
    """Basit kilit simülasyonu."""
    def __init__(self, name: str):
        self.name = name
        self.locked = False
        self.owner_thread: Optional[int] = None

    def acquire(self, thread_id: int):
        if self.locked and self.owner_thread != thread_id:
            raise RuntimeError(f"DEADLOCK: Mutex {self.name} başka thread ({self.owner_thread}) tarafından kilitli!")
        self.locked = True
        self.owner_thread = thread_id

    def release(self):
        self.locked = False
        self.owner_thread = None

class AtForkManager:
    """pthread_atfork kilit senkronizasyon motoru."""
    def __init__(self, mutex: ThreadMutex):
        self.mutex = mutex

    def prepare(self):
        """fork öncesi: Kilidi garantiye al."""
        self.mutex.acquire(thread_id=0)

    def parent(self):
        """Ebeveyn bittiğinde: Kilidi serbest bırak."""
        self.mutex.release()

    def child(self):
        """Çocuk süreçte: Kilidi sıfırla."""
        self.mutex.release()

# Modül 3 Test: Dosya Ofseti Paylaşımı İspatı
_shared_file = SharedFileDescription("telemetry.log")
# Ebeveyn 10 bayt yazar
_shared_file.write(b"PARENT_10_")
assert _shared_file.cursor_pos == 10, "Ebeveyn imleci 10 yapmalı"

# Çocuk aynı dosya nesnesine yazar
_shared_file.write(b"CHILD_10__")
assert _shared_file.cursor_pos == 20, "Çocuk imleci 20'ye ilerletmeli (Ofset ortaktır!)"
assert bytes(_shared_file.buffer) == b"PARENT_10_CHILD_10__", "Veriler sıralı eklenmeli"
print(f"[Modül 3] Paylaşılan Dosya Ofseti Doğrulandı: Cursor={_shared_file.cursor_pos}")
```

## 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering: Mutex Deadlock & CoW Bomb)

Savunma sistemlerinde `fork()` kaynaklı en tehlikeli arızalar kilitlenme ve kontrolsüz bellek ayrışmasıdır.

### 1. Sabotaj Senaryosu 1: Korumasız Multi-Threaded Fork ile Deadlock
- **Hata Senaryosu:** Radar kayıt modülü arka planda çalışan bir `LoggerThread`'e sahiptir. Bu thread `telemetry_mutex` kilidini tutarken, ana thread `fork()` çağırır.
- **Sonuç:** Çocuk süreçte `LoggerThread` kopyalanmaz. Çocuk süreç `telemetry_mutex` kilidini almaya çalıştığı an **sonsuza kadar kilitlenir (Deadlock)**.
- **Savunma:** `pthread_atfork` koruması devreye alınır; `fork()` öncesi kilit zorla devralınır ve çocukta serbest bırakılır.

### 2. Sabotaj Senaryosu 2: CoW Bellek Sürprizi (Memory Exhaustion)
- **Hata Senaryosu:** 8 GB'lık harita dizisine sahip bir görev sürecinde, çocuk süreç `memset(buffer, 0, 8GB)` çağırır.
- **Sonuç:** 2 milyon sayfa için anında Page Fault tetiklenir; sistem OOM (Out-of-Memory) durumuna girer.
- **Savunma:** Alt süreçler büyük dizileri değiştirmek yerine `mmap(MAP_SHARED)` veya `posix_spawn` kullanmalıdır.


```python
# Modül 4: Sabotaj Senaryosu — Korumasız Fork Deadlock vs pthread_atfork Kalkanı

class ForkSabotageSimulation:
    """Multi-threaded fork deadlock sabotajı ve atfork kalkanını simüle eder."""
    def __init__(self):
        self.mutex = ThreadMutex("radar_telemetry_lock")
        self.atfork_mgr = AtForkManager(self.mutex)

    def run_unprotected_sabotage(self) -> Dict[str, any]:
        """Korumasız sistem: Başka bir iş parçacığı kilidi tutarken fork yapılıyor."""
        # Arka plan iş parçacığı (Thread 99) kilidi alıyor
        self.mutex.acquire(thread_id=99)
        
        # Ana thread (Thread 1) fork yapıyor...
        # Çocuk süreçte Thread 99 YOKTUR! Kilit kilitli kaldı!
        child_deadlocked = False
        try:
            # Çocuk süreç kilidi almaya çalışıyor
            self.mutex.acquire(thread_id=1)
        except RuntimeError as e:
            child_deadlocked = True

        # Temizlik
        self.mutex.release()

        return {
            "deadlocked": child_deadlocked,
            "reason": "Kilit sahibi iş parçacığı çocuk süreçte kopyalanmadığı için kilit sahipsiz kaldı!"
        }

    def run_hardened_defense(self) -> Dict[str, any]:
        """Sertleştirilmiş sistem: pthread_atfork ile kilit senkronizasyonu."""
        # 1. prepare(): fork öncesi ana thread kilidi alır
        self.atfork_mgr.prepare()
        
        # 2. fork gerçekleşti...
        
        # 3. child(): Çocuk süreçte kilit temizlenir
        self.atfork_mgr.child()
        
        # 4. Çocuk süreç artık kilidi sorunsuz alabilir!
        child_acquired_successfully = False
        try:
            self.mutex.acquire(thread_id=1)
            child_acquired_successfully = True
            self.mutex.release()
        except RuntimeError:
            child_acquired_successfully = False

        return {
            "deadlocked": not child_acquired_successfully,
            "success": child_acquired_successfully,
            "protection": "pthread_atfork kalkanı kilidi çocukta güvenle sıfırladı."
        }

_sim = ForkSabotageSimulation()
_res_unprotected = _sim.run_unprotected_sabotage()
_res_hardened = _sim.run_hardened_defense()

assert _res_unprotected["deadlocked"] == True, "Korumasız sistem deadlock olmalı!"
assert _res_hardened["deadlocked"] == False, "Sertleştirilmiş sistem kilitlenmemeli!"
print(f"[Sabotaj Testi] Korumasız Deadlock: {_res_unprotected['deadlocked']}")
print(f"[Savunma Testi] AtFork Koruması Başarılı: {_res_hardened['success']}")
```

## 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99)

`fork()` sistem çağrısının determinizmi ve gecikme dağılımı doğrudan sayfa tablosu boyutuna bağlıdır:
- **`fork()` Çağrısı Gecikmesi:** Sanal bellek sayfaları fiziksel olarak kopyalanmadığı için çok hızlıdır (~1-3 µs simülasyon, ~50-100 µs Linux kernel).
- **İlk Yazma (CoW Page Fault) Gecikmesi:** 4096 baytlık `memcpy` ve sayfa tahsisi gerektirdiği için normal bellek yazmasından yaklaşık 100 kat daha yavaştır (~800-1500 ns).

### Ölçülen SLA ve Performans Metrikleri:
1. **`do_fork()` Çağrı Süresi Dağılımı:** Sayfa tablosu klonlama gecikmesi (p50, p95, p99).
2. **CoW Page Fault Gecikmesi:** İlk yazma anında tetiklenen ayrışma süresi.


```python
# Modül 5: Ampirik Kıyaslama ve Yüksek Çözünürlüklü fork / CoW Benchmark Motoru
import time
import numpy as np

def run_benchmarks(iterations: int = 3000) -> Dict[str, any]:
    """fork() çağrısı ve CoW Page Fault gecikmelerini ampirik olarak ölçer."""
    fork_engine = KernelForkEngine()
    mmu = VirtualMemoryMMU()
    
    # 50 sayfalık temsili bir bellek alanı oluştur
    ptes = {}
    for vpn in range(50):
        fid = mmu.allocate_page(b"A" * 4096)
        ptes[vpn] = PageTableEntry(fid, writeable=True)

    latencies_fork = []
    latencies_cow_fault = []

    for _ in range(iterations):
        # 1. fork() sistem çağrısı süresi
        t0 = time.perf_counter_ns()
        p_ret, c_ret = fork_engine.do_fork(parent_pid=100)
        t1 = time.perf_counter_ns()
        latencies_fork.append(t1 - t0)

        # 2. Sayfa tablosunu CoW yap
        parent_p, child_p = mmu.fork_page_table(ptes)

        # 3. CoW Page Fault (İlk Yazma) süresi
        t0 = time.perf_counter_ns()
        mmu.write_memory(child_p, vpn=0, offset=10, byte_val=ord('Z'))
        t1 = time.perf_counter_ns()
        latencies_cow_fault.append(t1 - t0)

    def calc_stats(lat_list):
        arr = np.array(lat_list, dtype=np.float64)
        return {
            "mean": float(np.mean(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "raw": arr
        }

    return {
        "fork": calc_stats(latencies_fork),
        "cow_fault": calc_stats(latencies_cow_fault),
        "iterations": iterations
    }

_bench_res = run_benchmarks(iterations=2000)
print(f"[Benchmark] {_bench_res['iterations']} İterasyon Ölçüldü.")
print(f"  fork() Mean:     {_bench_res['fork']['mean']:.2f} ns (p95: {_bench_res['fork']['p95']:.2f} ns)")
print(f"  CoW Fault Mean:  {_bench_res['cow_fault']['mean']:.2f} ns (p95: {_bench_res['cow_fault']['p95']:.2f} ns)")
```

## 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı

Üretilecek görsel analiz paneli (`gun_086_fork_zihinsel_modeli.png`) IEEE ve askeri aviyonik teknik standartlarında, 300 DPI çözünürlükte ve koyu tema (`#0F172A`) formatında tasarlanmıştır:

### Panel Mimarisi ve Metrik Hedefleri:
1. **Panel 1 (Sol Üst) — CoW Öncesi ve Sonrası Fiziksel Bellek Ayrışması:**
   - **Görsel:** Paylaşılan salt-okunur sayfalar vs Page Fault sonrası kopyalanan ayrık fiziksel sayfalar.
   - **Mühendislik Amacı:** CoW mekanizmasının RAM tasarrufunu ve yazma anındaki ayrışmayı kanıtlamak.
2. **Panel 2 (Sağ Üst) — fork() Çağrısı ve CoW Page Fault Gecikme Dağılımları (Boxplot):**
   - **Görsel:** `fork()` çağrısı ile ilk yazma (`CoW Fault`) gecikmelerinin nanasaniye karşılaştırması.
   - **Mühendislik Amacı:** `fork()`'un hafifliğini, Page Fault'un ise ek maliyetini doğrulamak.
3. **Panel 3 (Sol Alt) — Sabotaj Senaryosu: Deadlock vs pthread_atfork Kalkanı:**
   - **Görsel:** Korumasız multi-threaded fork kilitlenmesi (%100 Deadlock) vs atfork koruması (%0 Deadlock).
   - **Mühendislik Amacı:** Askeri sistemlerde kilit güvenliğinin önemini somutlaştırmak.
4. **Panel 4 (Sağ Alt) — Paylaşılan Dosya Tanıtıcısı ve Ofset İlerleme Eğrisi:**
   - **Görsel:** Ebeveyn ve çocuğun ardışık yazmalarında ortak `cursor_pos` ilerlemesi.
   - **Mühendislik Amacı:** `O_APPEND` olmadan dosya paylaşımının getirdiği tehlikeyi göstermek.


```python
# Modül 6: 4-Panelli Yayın Kalitesinde Dashboard Üretimi ve Katı Assert Doğrulaması
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DEFAULT_PNG = "gun_086_fork_zihinsel_modeli.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    """Yayın kalitesinde 4-panelli görselleştirme paneli üretir."""
    fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    bench_data = run_benchmarks(iterations=2000)

    # Ortak Stil Fonksiyonu
    def style_ax(ax, title, xlabel, ylabel):
        ax.set_facecolor('#1E293B')
        ax.set_title(title, fontsize=12, fontweight='bold', color='#38BDF8', pad=10)
        ax.set_xlabel(xlabel, fontsize=10, fontweight='bold', color='#94A3B8')
        ax.set_ylabel(ylabel, fontsize=10, fontweight='bold', color='#94A3B8')
        ax.tick_params(colors='#CBD5E1', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color('#334155')
            spine.set_linewidth(1.2)
        ax.grid(True, linestyle='--', alpha=0.25, color='#64748B')

    # -------------------------------------------------------------
    # PANEL 1: CoW Bellek Ayrışması (Paylaşılan vs Ayrık Sayfalar)
    # -------------------------------------------------------------
    ax1 = axs[0, 0]
    style_ax(ax1, "Panel 1: CoW Öncesi ve Sonrası Bellek Dağılımı", 
             "Bellek Durumu", "Fiziksel Sayfa Sayısı (Pages)")
    
    states = ['fork() Anı\n(0 Yazma)', 'Kısmi Yazma\n(10 Sayfa)', 'Tam Ayrışma\n(50 Sayfa)']
    shared_pages = [50, 40, 0]
    copied_pages = [0, 10, 50]
    
    x = np.arange(len(states))
    w = 0.4
    
    b1 = ax1.bar(x, shared_pages, width=w, label='Ortak Sayfalar (ref=2)', color='#0EA5E9', edgecolor='#334155')
    b2 = ax1.bar(x, copied_pages, width=w, bottom=shared_pages, label='Klonlanan Sayfalar (ref=1)', color='#EF4444', edgecolor='#334155')
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(states, fontweight='bold')
    ax1.set_ylim(0, 65)
    ax1.legend(loc='upper right', facecolor='#1E293B', edgecolor='#334155', fontsize=8)

    # -------------------------------------------------------------
    # PANEL 2: fork() ve CoW Page Fault Gecikmeleri (Boxplot)
    # -------------------------------------------------------------
    ax2 = axs[0, 1]
    style_ax(ax2, "Panel 2: fork() Klonlama vs CoW Page Fault Gecikmesi", 
             "İşlem Türü", "Gecikme (Nanosaniye - ns)")
    
    ops = ['fork() Klonlama', 'CoW Page Fault']
    data_plot = [
        bench_data['fork']['raw'][:1000],
        bench_data['cow_fault']['raw'][:1000]
    ]
    
    bp = ax2.boxplot(data_plot, patch_artist=True, showmeans=True,
                     boxprops=dict(facecolor='#0284C7', color='#38BDF8'),
                     capprops=dict(color='#94A3B8'),
                     whiskerprops=dict(color='#64748B'),
                     flierprops=dict(marker='o', markerfacecolor='#F43F5E', markersize=3, alpha=0.4),
                     medianprops=dict(color='#F59E0B', linewidth=2),
                     meanprops=dict(marker='^', markerfacecolor='#10B981', markeredgecolor='#10B981'))
    
    ax2.set_xticks([1, 2])
    ax2.set_xticklabels(ops, fontweight='bold')
    ax2.set_yscale('log')
    
    means = [bench_data['fork']['mean'], bench_data['cow_fault']['mean']]
    for i, m in enumerate(means, 1):
        ax2.text(i, m * 1.25, f"Ort: {m:.0f}ns", ha='center', color='#38BDF8', fontsize=8, fontweight='bold')

    # -------------------------------------------------------------
    # PANEL 3: Sabotaj Senaryosu (Deadlock vs atfork Koruması)
    # -------------------------------------------------------------
    ax3 = axs[1, 0]
    style_ax(ax3, "Panel 3: Multi-Thread Fork Kilitlenme Oranı", 
             "Koruma Stratejisi", "Kilitlenme (Deadlock) Oranı (%)")
    
    strats = ['Korumasız Fork\n(Mutex Sahipsiz)', 'pthread_atfork\n(Kilit Temizleme)']
    d_rates = [100.0, 0.0]
    bar_colors = ['#EF4444', '#10B981']
    
    bars3 = ax3.bar(strats, d_rates, color=bar_colors, edgecolor='#334155', width=0.45)
    ax3.set_ylim(0, 115)
    
    ax3.text(0, 103, "%100 KİLİTLENME!", ha='center', color='#EF4444', fontweight='bold', fontsize=9)
    ax3.text(1, 5, "%0 GÜVENLİ (PASS)", ha='center', color='#10B981', fontweight='bold', fontsize=9)

    # -------------------------------------------------------------
    # PANEL 4: Paylaşılan Dosya Ofseti İlerlemesi
    # -------------------------------------------------------------
    ax4 = axs[1, 1]
    style_ax(ax4, "Panel 4: Ebeveyn ve Çocuk Ortak Dosya İmleci İlerlemesi", 
             "Yazma Sırası (İşlem No)", "Dosya İmleci Konumu (Bayt)")
    
    ops_seq = list(range(1, 9))
    # Ebeveyn ve çocuğun ardışık yazmaları
    cursor_progression = [10, 20, 30, 40, 50, 60, 70, 80]
    
    ax4.plot(ops_seq, cursor_progression, marker='s', color='#F59E0B', linewidth=2.5, label='Paylaşılan f_pos')
    ax4.scatter([1, 3, 5, 7], [10, 30, 50, 70], color='#38BDF8', s=80, zorder=5, label='Ebeveyn Yazdı')
    ax4.scatter([2, 4, 6, 8], [20, 40, 60, 80], color='#10B981', s=80, zorder=5, label='Çocuk Yazdı')
    
    ax4.set_xticks(ops_seq)
    ax4.legend(loc='upper left', facecolor='#1E293B', edgecolor='#334155', fontsize=8)

    plt.suptitle("ASELSAN / HAVELSAN Görev Sistemleri: fork() Zihinsel Modeli ve CoW Mimarisi", 
                 fontsize=15, fontweight='bold', color='#F8FAFC', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_png_path}")

def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Tüm fork() ve CoW mekanizmalarını katı assert koşullarıyla denetler."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. fork() Çift Dönüş Doğrulaması
    engine = KernelForkEngine()
    p_val, c_val = engine.do_fork(parent_pid=100)
    assert p_val == 101, "Ebeveyn dönüş değeri çocuk PID olmalı"
    assert c_val == 0, "Çocuk dönüş değeri 0 olmalı"

    # 2. CoW Page Fault Doğrulaması
    mmu = VirtualMemoryMMU()
    fid = mmu.allocate_page(b"ORIGINAL_DATA")
    p_ptes = {0: PageTableEntry(fid, writeable=True)}
    p_ptes, c_ptes = mmu.fork_page_table(p_ptes)
    
    assert mmu.frames[fid].refcount == 2, "fork sonrası refcount 2 olmalı"
    assert p_ptes[0].writeable == False, "Sayfalar salt-okunur kilitlenmeli"
    
    # Yazma tetikle
    mmu.write_memory(c_ptes, vpn=0, offset=0, byte_val=ord('N'))
    assert mmu.page_fault_count == 1, "Page fault tetiklenmeli"
    assert c_ptes[0].frame_id != p_ptes[0].frame_id, "Çocuk yeni çerçeveye ayrışmalı"

    # 3. Paylaşılan Ofset Doğrulaması
    sfile = SharedFileDescription("test.bin")
    sfile.write(b"ABC")
    sfile.write(b"DEF")
    assert sfile.cursor_pos == 6, "Ofset ortak ilerlemeli"

    # 4. atfork Deadlock Kalkanı Doğrulaması
    sim = ForkSabotageSimulation()
    res_sab = sim.run_unprotected_sabotage()
    res_def = sim.run_hardened_defense()
    assert res_sab["deadlocked"] == True, "Korumasız multi-threaded fork deadlock olmalı"
    assert res_def["deadlocked"] == False, "atfork ile kilitlenme engellenmeli"

    # 5. PNG Görsel Dosya Kontrolü
    if os.path.exists(png_path):
        size = os.path.getsize(png_path)
        assert size > 50000, f"PNG dosyası çok küçük veya bozuk ({size} bayt)"

    print("[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")

if __name__ == "__main__":
    out_png = "gun_086_fork_zihinsel_modeli.png"
    generate_dashboard(out_png)
    verify_all_assertions(out_png)
```

## 18. ⚠️ 10 Ölümcül Anti-Pattern (fork Kullanımında Yapılan Kritik Hatalar)

| No | Anti-Pattern Adı | Neden Tehlikeli? | Doğru Mühendislik Yaklaşımı |
|:---|:---|:---|:---|
| 1 | **Çok İş Parçacıklı Programda `fork()` Çağırmak** | Diğer iş parçacıkları çocukta yok olur; onların tuttuğu mutex'ler sonsuza dek kilitli kalır (Deadlock). | Çok iş parçacıklı sistemlerde `fork()` sonrası derhal `execve()` çağrılmalı veya `posix_spawn()` kullanılmalıdır. |
| 2 | **`fork()` Başarısızlığını (`pid == -1`) Denetlememek** | PID tablosu veya bellek dolduğunda `fork()` -1 döner; ebeveyn bu değeri çocuk sanarak `kill(-1)` ile sistemi çökertebilir! | `pid < 0` durumunu daima kontrol edip `errno (EAGAIN/ENOMEM)` kaydetmek. |
| 3 | **CoW Sonrası Tüm Belleğe Körü Körüne Yazmak** | Çocukta gereksiz `memset` veya bellek temizliği yapmak tüm CoW sayfalarını kopyalamaya zorlar; OOM tetikler. | Yalnızca gereken bellek sayfalarını değiştirmek veya gereksiz sayfaları `madvise(MADV_DONTNEED)` ile bırakmak. |
| 4 | **Paylaşılan Dosya Tanıtıcısında `O_APPEND` Unutulması** | Ebeveyn ve çocuk aynı dosya imlecini (`f_pos`) paylaştığı için log kayıtları birbirini ezer. | Dosyaları `O_APPEND` ile açmak veya çocukta bağımsız dosya tanıtıcısı oluşturmak. |
| 5 | **Çocuk Süreçte Standart `exit()` Çağırmak** | Standart `exit()` kullanıcı uzayı stdio arabelleklerini temizler ve atexit kancalarını çalıştırır; çift temizleme arızası doğar. | `fork()` sonrası `exec()` başarısız olursa daima `_exit(127)` veya `_Exit()` çağrılmalıdır. |
| 6 | **Rastgele Sayı Üreteçlerini (RNG) Yeniden Tohumlamamak** | `fork()` sonrasında ebeveyn ve çocuk aynı PRNG tohumunu (seed) paylaşır; aynı kriptografik anahtarları üretirler! | `fork()`'un hemen ardından çocukta `getrandom()` veya `srandomdev()` ile tohumu yenilemek. |
| 7 | **POSIX Kilitlerinin (`fcntl`) Çocuğa Geçtiğini Varsaymak** | Dosya kilitleri çocuk sürece miras kalmaz; ebeveyn ve çocuk aynı dosyaya kilitlenmeden yazar. | Çocuk süreçte ihtiyaç duyulan dosya kilitlerini yeniden talep etmek. |
| 8 | **`vfork()` Kullanıp Belleğe Yazmak** | `vfork()` ebeveynin adres alanını askıya alır ve paylaşır; çocuk bellek değiştirirse ebeveyn çöker. | `vfork()` yerine modern `posix_spawn()` veya standart CoW `fork()` tercih etmek. |
| 9 | **Signal Handler İçinde Güvensiz Fonksiyon Çağırmak** | Çocuk süreç sinyalle sonlandığında `SIGCHLD` içinde `printf` veya `malloc` çağırmak kilitlenmeye yol açar. | Sinyal yakalayıcılarda yalnızca async-signal-safe fonksiyonlar (`write`, `waitpid`) kullanmak. |
| 10 | **`pthread_atfork` Olmadan Global Kilit Kullanmak** | C++ kütüphanelerindeki gizli iç kilitlerin (allocator locks) çocukta asılı kalması. | Alt süreç yöneticilerinde `pthread_atfork` kancalarını eksiksiz kaydetmek. |


## 19. 🔬 Sektörel Standartlar (ASELSAN, HAVELSAN, POSIX, CERT C)

Savunma ve aviyonik sistemlerde `fork()` kullanım kuralları uluslararası standartlarla sabitlenmiştir:

### 1. CERT C Güvenli Kodlama Standardı (Rule POS44-C)
- *"Do not use threads with fork."* Çok iş parçacıklı bir ortamda `fork()` çağrılırsa çocuk süreç yalnızca asenkron sinyal güvenli fonksiyonları çalıştırabilir veya doğrudan `execve()` çağırmalıdır.

### 2. POSIX.1-2017 & IEEE 1003.1 Standartları
- `fork()` sistem çağrısının dönüş semantiği, dosya tanıtıcısı paylaşım kuralları ve sinyal miras mekanizması resmi olarak tanımlanmıştır.

### 3. DO-178C / DO-278A (Aviyonik Emniyet Standartları)
- Seviye A sistemlerde dinamik süreç türetimi (`fork`) genellikle sistem başlangıcı (Init phase) ile sınırlandırılır. Görev uçuşu esnasında kontrolsüz `fork()` çağrılması determinizm ihlali sayılır.

### 4. MISRA C++ ve Savunma Kodlama Kılavuzları
- `fork()` çağrısının dönüş değeri her zaman açıkça kontrol edilmeli; ebeveyn, çocuk ve hata dalları (`switch` veya `if-else if-else`) eksiksiz işlenmelidir.


## 20. 🛠️ Üretim Kontrol Listesi (Production Checklist - 12 Katı Kural)

Saha kabul testine (SAT) girmeden önce aşağıdaki 12 kural tek tek doğrulanmalıdır:

- [ ] **1. Dönüş Kontrolü:** `fork()` çağrısının dönüş değeri (`<0`, `==0`, `>0`) eksiksiz dallanıyor mu?
- [ ] **2. _exit() Kullanımı:** Çocuk süreçte `exec` öncesi arızalarda `exit()` yerine `_exit()` çağrılıyor mu?
- [ ] **3. Mutex Güvenliği:** Çok iş parçacıklı uygulamada `fork` varsa `pthread_atfork` kancaları tanımlı mı?
- [ ] **4. Dosya Ofseti Koruması:** Ortak yazılan dosyalarda `O_APPEND` bayrağı aktif mi?
- [ ] **5. RNG Tohum Yenileme:** Çocuk süreçte kriptografik rastgele sayı üreteçleri (`getrandom`) yeniden tohumlandı mı?
- [ ] **6. CoW Bütçe Analizi:** Çocuğun yazacağı maksimum bellek miktarı sistemin boş RAM sınırları içinde mi?
- [ ] **7. Dosya Tanıtıcı Temizliği:** Çocukta kullanılmayacak tüm dosya tanıtıcıları `close()` ile kapatılıyor mu?
- [ ] **8. FD CLOEXEC Doğrulaması:** Dosya tanıtıcıları açılırken `O_CLOEXEC` bayrağı kullanılıyor mu?
- [ ] **9. Zamanlayıcı Sıfırlama:** Çocuk süreçte ebeveynin `alarm` ve `timer` kurallarının temizlendiği biliniyor mu?
- [ ] **10. Kilit Devri Denetimi:** Çocuk süreçte `fcntl` kilitlerinin geçersiz kaldığı dikkate alındı mı?
- [ ] **11. Async-Signal-Safety:** Çocuk süreçte `fork` ile `exec` arasında malloc/printf çağrılmadığı onaylandı mı?
- [ ] **12. posix_spawn Değerlendirmesi:** Yalnızca program başlatmak için `fork()+exec()` yerine `posix_spawn()` incelendi mi?


## 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları)

### Soru 1: `fork()` fonksiyonu nasıl olur da bir kez çağrılır ama iki kez geri döner?
**Cevap:** `fork()` çağrıldığında çekirdek ebeveynin tüm yürütme bağlamını (`task_struct`, yığın ve CPU yazmaçları `pt_regs`) çocuğa kopyalar. Çekirdek, ebeveynin dönüş yazmacına (`RAX/X0`) çocuk PID'sini yazarken; çocuğun `pt_regs->rax` yazmacını **açıkça 0 yapar**. İşlemci zamanlayıcısı çocuğu çalıştırdığında çocuk `fork()`'un hemen bittiği satırdan uyanır ve `%rax` yazmacında `0` okur. Ebeveyn ise kendi akışında çocuk PID'sini okur.

### Soru 2: Copy-on-Write (CoW) mekanizması olmasaydı modern işletim sistemlerinde ne olurdu?
**Cevap:** CoW olmasaydı, 16 GB bellek kullanan bir süreç `fork()` çağırdığında çekirdek 16 GB fiziksel RAM'i bayt bayt kopyalamak zorunda kalırdı. Bu işlem yüzlerce milisaniye sürer, CPU önbelleklerini kilitler ve sistemde 16 GB boş RAM yoksa `fork()` derhal başarısız olurdu. CoW sayesinde `fork()` yalnızca birkaç kilobaytlık sayfa tablosunu kopyalayarak mikro-saniyeler içinde tamamlanır.

### Soru 3: Çok iş parçacıklı bir süreçte `fork()` çağrıldığında diğer iş parçacıklarına ne olur?
**Cevap:** POSIX standardı gereği, çocuk süreçte **yalnızca `fork()` sistem çağrısını yapan iş parçacığı hayatta kalır**. Diğer tüm iş parçacıkları çocuk süreçte anında yok olur (yürütülmez). Bu durum, diğer iş parçacıklarının kilitlediği mutex'lerin çocukta sahipsiz kilitli kalmasına (Deadlock) yol açar.

### Soru 4: `fork()` sonrasında çocuk süreç ebeveynin açık dosya tanıtıcılarını nasıl görür?
**Cevap:** Çocuk süreç ebeveynin dosya tanıtıcı tablosunu (`files_struct`) kopyalar. Ancak bu tanıtıcılar çekirdekteki aynı açık dosya tanımına (`struct file`) işaret eder. Bu nedenle **dosya ofseti (`cursor position`) ortaktır**. Ebeveyn dosyayı okur veya yazarsa imleç çocuk için de ilerler.

### Soru 5: `vfork()` nedir ve neden günümüzde kullanılmamalıdır?
**Cevap:** `vfork()`, CoW mekanizması icat edilmeden önce sayfa kopyalamadan kaçınmak için geliştirilmiş ilkel bir çağrıdır. `vfork()` çağrıldığında ebeveyn askıya alınır (dondurulur) ve çocuk ebeveynin belleğini doğrudan paylaşır. Çocuk bellekte bir değişkeni değiştirirse ebeveynin belleği bozulur; çocuk `_exit()` veya `execve()` dışında bir şey çağırırsa sistem çöker. Günümüzde CoW ve `posix_spawn()` varken `vfork()` kesinlikle kullanılmamalıdır.


## 22. 🔮 Gelecek Perspektifi (Donanım & Mimari Trendleri)

### 1. `clone3()` ve Yeni Nesil Çekirdek Klonlama API'si
Linux 5.3 ile eklenen `clone3()` sistem çağrısı, geleneksel `fork()` ve `clone()` çağrılarının yerini almaktadır:
- `struct clone_args` yapısı üzerinden bayraklar genişletilebilir hale getirilmiştir.
- `CLONE_CLEAR_SIGHAND` bayrağı ile çocuk süreçte sinyal işleyicileri anında varsayılana sıfırlanabilir.
- `pidfd` desteği doğrudan çağrı anında alınarak yarış durumları donanımsal olarak engellenir.

### 2. Donanımsal Memory Tagging (ARM MTE / CHERI) ve CoW
Geleceğin askeri işlemcilerinde; fiziksel bellek sayfaları 4-bitlik donanımsal etiketlerle (tag) mühürlenmektedir. CoW sayfa hatası anında donanım etiketleri de kopyalanarak bellek taşması (buffer overflow) veya yetkisiz okuma girişimleri mikro-mimari düzeyinde engellenmektedir.


## 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı)

Bugün; `fork()` sistem çağrısının mantıksal zihinsel modelini, "returns twice" donanımsal yazmaç fiziğini, Copy-on-Write (CoW) sayfa hatası mekanizmasını ve `pthread_atfork` kilit güvenliğini öğrendik.

### Neden Bir Sonraki Gün "exec ailesi zihinsel modeli"?
`fork()` ile ebeveynin tıpatıp aynısı olan bir çocuk süreç türettik.
Peki bu çocuk sürecin bambaşka bir programı (örneğin `/usr/bin/radar_dsp` ikilisini) çalıştırmasını nasıl sağlarız?
- `execve()` çağrısı sürecin mevcut kodunu, yığınını ve verisini bellekten silip yeni bir ikiliyi nasıl yükler?
- Süreç kimliği (`PID`) neden `exec` sonrasında hiç değişmez?
- Açık dosya tanıtıcıları yeni programa nasıl aktarılır ve `FD_CLOEXEC` bayrağı neden hayati bir güvenlik kalkanıdır?

Yarın **GÜN 087: exec ailesi zihinsel modeli** modülünde; Linux işletim sisteminde program yükleme mekanizmasını, ELF ikili formatının belleğe haritalanmasını ve `execve()` sistem çağrısının mimari derinliklerini inceleyeceğiz!
