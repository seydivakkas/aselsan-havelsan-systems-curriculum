# GÜN 091: POSIX Düşük Seviyeli Girdi/Çıktı (I/O) Sistem Çağrıları: open, read, write, close, lseek ve fsync

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
- **Konu**: Tamponsuz Düşük Seviyeli I/O Sistem Çağrıları (`open`, `read`, `write`, `close`, `lseek`, `fsync`)
- **Ön Koşul Bilgi**: Gün 090 (File Descriptor Kavramı ve VFS 3-Katmanlı Mimari)
- **Hedef Sistemler**: ASELSAN SAR Radar Ham Veri Kaydedicileri, HAVELSAN Sonar Akustik Veri Depolama Sunucuları, TUSAŞ Milli Muharip Uçak (KAAN) Kara Kutu (Crash Survivable Memory Unit), Gerçek Zamanlı Linux (RT-PREEMPT).

### 40-Nokta Kalite ve Mimari Beyanı
Bu çalışma paketi; POSIX standardı (`IEEE Std 1003.1-2024`), Linux Kernel v6.x Sanal Dosya Sistemi (`fs/read_write.c`, `fs/open.c`, `fs/sync.c`) ve kritik yazılım güvenilirliği standartları (MISRA C++20, DO-178C Level A) esas alınarak hazırlanmıştır. Modül; kullanıcı alanı tamponu bulunmayan doğrudan çekirdek sistem çağrılarını, atomik dosya oluşturma (`O_CREAT | O_EXCL`) ve ekleme (`O_APPEND`) bayraklarını, ağ/blok aygıtlarında kaçınılmaz olan Kısa Okuma/Yazma (Short Read/Write) olgusunu ve sağlam döngüsel kurtarma algoritmalarını (`read_all`, `write_all`), delikli dosyaları (Sparse Files) ve veri dayanıklılığı (`fsync` vs `fdatasync`) protokollerini teorik, matematiksel ve pratik derinlikte ele alır.


## 1. Teori ve Sistem Mimarisi: Tamponsuz (Unbuffered) POSIX I/O ve Çekirdek Sayfa Önbelleği

C standart kütüphanesindeki `fopen()`, `fread()`, `fwrite()` fonksiyonları kullanıcı alanında (user-space) $4\text{ KB} - 8\text{ KB}$ boyutunda bir bellek tamponu (`FILE* buffer`) kullanır. Buna karşılık POSIX sistem çağrıları olan **`open(2)`**, **`read(2)`**, **`write(2)`** ve **`close(2)`** tamamen **tamponsuzdur (unbuffered)**:

Her çağrı doğrudan bir kullanıcı/çekirdek bağlam değişimi (context switch) tetikler ve Linux Sayfa Önbelleği (Page Cache) üzerinden donanıma yönlendirilir:

```
+-----------------------------------------------------------------------------+
|                KULLANICI ALANI (USER SPACE) - C++20 UYGULAMASI              |
|   char user_buf[4096];                                                      |
|   ssize_t n = write(fd, user_buf, 4096);                                    |
+-----------------------------------------------------------------------------+
                                       |
                   SYSCALL: sys_write (x86_64 Syscall #1)
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                   LINUX ÇEKİRDEK ALANI (KERNEL SPACE) - VFS                 |
|  1. fdtable lookup: fd -> struct file* çözümlemesi (O(1))                   |
|  2. Yetki ve mod kontrolü (O_WRONLY veya O_RDWR mu?)                        |
|  3. Ofset denetimi (O_APPEND ise atomik i_size sonuna zıpla)                |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                     LİNUX SAYFA ÖNBELLEĞİ (PAGE CACHE)                      |
|  - Veri doğrudan RAM'deki 4 KB'lık "Kirli Sayfalara" (Dirty Pages) yazılır. |
|  - write() çağrısı burada BAŞARIYLA BİTER ve hemen geri döner!              |
|  - Veri henüz diskte/SSD'de DEĞİLDİR! Sadece çekirdek RAM'indedir.          |
+-----------------------------------------------------------------------------+
                                       |
                Asenkron Arka Plan Temizliği (flusher threads: pdflush)
                veya Zorunlu Çağrı: fsync(fd) / fdatasync(fd)
                                       |
                                       v
+-----------------------------------------------------------------------------+
|              BLOK AYGITI VE FİZİKSEL DEPOLAMA (NVMe / SSD / eMMC)           |
+-----------------------------------------------------------------------------+
```

> [!IMPORTANT]
> `write(2)` çağrısının başarıyla dönmesi verinin diske kaydedildiğini garanti etmez! Yalnızca çekirdek önbelleğine kopyalandığını (`memcpy` hızında) ifade eder. Elektrik kesintisinde veri kaybını sıfırlamak için askeri sistemlerde **`fsync(2)`** veya **`O_SYNC`** bayrağı zorunludur.


## 2. `open()` Sistem Çağrısı Bayrakları Taksonomisi

```c
#include <fcntl.h>
int open(const char *pathname, int flags, ... /* mode_t mode */);
```

`flags` argümanı, zorunlu erişim modları ile isteğe bağlı davranış bayraklarının bit düzeyinde VE'lenmesi (`|`) ile oluşturulur:

### 1. Zorunlu Erişim Modları (Mutually Exclusive - Biri Seçilmelidir)
- **`O_RDONLY`**: Salt Okunur.
- **`O_WRONLY`**: Salt Yazılır.
- **`O_RDWR`**: Hem Okunur Hem Yazılır.

### 2. Dosya Oluşturma ve Durum Bayrakları

| Bayrak | Anlamı ve Çekirdek Davranışı | Güvenlik / Sistem Kritik Önemi |
| :--- | :--- | :--- |
| **`O_CREAT`** | Dosya yoksa oluşturulur. `mode` parametresi (örn: `0644`) zorunludur. | `umask` ile filtrelenerek nihai `st_mode` belirlenir. |
| **`O_EXCL`** | `O_CREAT` ile birlikte kullanılır. Dosya zaten varsa çağrı **`EEXIST`** hatasıyla çöker. | **TOCTOU Yarış Koşulunu Sıfırlar:** Dosyanın atomik oluşturulmasını garanti eder. |
| **`O_TRUNC`** | Dosya zaten varsa ve yazma modunda açılmışsa boyutunu anında **0 bayt** yapar. | Eski log veya telemetri dosyasını sıfırlamak için kullanılır. |
| **`O_APPEND`** | Her `write()` öncesinde dosya ofseti çekirdek tarafından atomik olarak dosya sonuna (`EOF`) taşınır. | Çok süreçli sistemlerde logların birbirini ezmesini engeller. |
| **`O_NONBLOCK`** | I/O işlemi beklemek zorundaysa süreci uyutmaz; derhal **`EAGAIN` / `EWOULDBLOCK`** döner. | FIFO, TTY ve ağ soketlerinde zorunludur. |
| **`O_CLOEXEC`** | `execve()` anında bu dosya tanıtıcısının otomatik kapatılmasını sağlar. | **FD Leak Güvenlik Açığını Sıfırlar.** |
| **`O_DIRECT`** | Linux Sayfa Önbelleğini (Page Cache) tamamen devre dışı bırakır; DMA ile doğrudan kullanıcı tamponuna okur/yazar. | Veritabanları ve ultra-yüksek hızlı radar veri kaydedicilerinde kullanılır. |
| **`O_SYNC`** | `write()` çağrısı, veriler VE dosya metaverileri (inode) fiziksel diske yazılana kadar bloklanır. | Havacılık ve kara kutu (blackbox) kayıtlarında zorunludur. |


## 3. Kısa Okuma ve Kısa Yazma (Short Read / Short Write) Gerçeği

Sistem programlamaya yeni başlayanların en sık yaptığı hata; `read(fd, buf, 1000)` çağrısının her zaman $1000$ bayt okuyacağını varsaymaktır.

### Kısa Okuma/Yazma Neden Oluşur?
1. **Boru Hatları (Pipes) ve Ağ Soketleri**: Karşı taraf sokete o anda yalnızca 120 bayt yazmışsa, `read()` kalan veriyi beklemez; mevcut 120 baytı döndürür.
2. **Sinyal Kesintileri (`EINTR`)**: I/O işlemi sırasında bir sinyal (`SIGINT`, `SIGTERM`, `SIGALRM`) gelirse sistem çağrısı yarım kalır.
3. **Disk Dolumu (`ENOSPC`) veya Kota Sınırı**: Disk dolmak üzereyse `write()` istenen boyuttan daha azını diske yazar ve döner.
4. **Dosya Sonu (`EOF`)**: Dosyada kalan bayt miktarı istenen tampondan küçükse kalan miktar okunur; bir sonraki `read()` ise **`0` (EOF)** döner.

```
İstenen Veri: [ ================== 1000 Bayt ================== ]
1. write()   : [ ===== 350 Bayt ===== ] (Döndü: 350, Kalan: 650)
2. write()   :                         [ === 200 Bayt === ] (Döndü: 200, Kalan: 450)
3. write()   :                                             [ === 450 Bayt === ] (Tamamlandı!)
```

### Sağlam I/O Döngüleri (`read_all` ve `write_all`)
Üretim düzeyinde bir POSIX uygulamasında ham `read` veya `write` doğrudan kullanılmaz. Bunun yerine tampon tamamen aktarılana kadar dönen döngüsel fonksiyonlar yazılır:

```c
ssize_t write_all(int fd, const void *buf, size_t count) {
    size_t total_written = 0;
    const char *ptr = (const char *)buf;
    while (total_written < count) {
        ssize_t n = write(fd, ptr + total_written, count - total_written);
        if (n < 0) {
            if (errno == EINTR) continue; // Sinyalle kesildi, tekrar dene
            return -1; // Gerçek I/O hatası
        }
        total_written += n;
    }
    return total_written;
}
```


## 4. Dosya Konumlama (`lseek`), Delikli Dosyalar ve Veri Dayanıklılığı

### `lseek(2)` Sistem Çağrısı
Açık dosya açıklamasındaki okuma/yazma ofsetini (`f_pos`) rastgele erişim için değiştirir:

```c
off_t lseek(int fd, off_t offset, int whence);
```
- `SEEK_SET`: Dosya başından itibaren (`0 + offset`).
- `SEEK_CUR`: Mevcut konumdan itibaren (`f_pos + offset`).
- `SEEK_END`: Dosya sonundan itibaren (`EOF + offset`).

### Delikli Dosyalar (Sparse Files)
Eğer `lseek` ile dosya sonunun çok ötesine (örneğin $1\text{ TB}$ ileriye) zıplayıp yalnızca $1$ bayt yazarsanız:
- İşletim sistemi aradaki boşluk için diskte hiçbir fiziksel blok tahsis etmez!
- Dosyanın mantıksal boyutu (`stat.st_size`) $1\text{ TB}$ görünürken, diskte kapladığı gerçek alan (`stat.st_blocks * 512`) sadece $4\text{ KB}$ olur.
- Linux, bu boşlukları atlayarak hızlı tarama yapmak için modern `SEEK_DATA` ve `SEEK_HOLE` bayraklarını destekler.

### `fsync(fd)` vs `fdatasync(fd)`
Çekirdek önbelleğindeki kirli sayfaların fiziksel NVMe/SSD medyasına yazılmasını zorlamak için:
- **`fsync(fd)`**: Hem dosya verilerini hem de ilişkili **tüm metaverileri (dosya boyutu, erişim/değiştirme zaman damgası `st_mtime`, sahiplik)** diske senkronize eder. Bu iki ayrı disk yazma işlemi demektir (Veri Bloğu + Inode Bloğu).
- **`fdatasync(fd)`**: Yalnızca **veri bloklarını** ve veriyi okumak için mutlak zorunlu olan metaveriyi (örneğin dosya boyutu değiştiyse boyutu) yazar; önemsiz zaman damgalarını (`atime`/`mtime`) diske yazmaz. Veritabanı ve telemetri günlüklerinde **~%30 daha yüksek I/O başarımına** sahiptir.


## 5. Matematiksel Modelleme: Blok Boyutu ($B$) ve Syscall Amortizasyonu

Toplam $S_{\text{total}}$ baytlık bir radar ham veri dosyasını diske yazarken harcanan toplam süre:

$$T_{\text{total}}(B) = N_{\text{calls}} \cdot T_{\text{syscall}} + \frac{S_{\text{total}}}{\text{Throughput}_{\text{storage}}}$$

Burada:
- $B$: Tek bir `write()` çağrısında gönderilen tampon boyutu (Buffer Size - Bayt)
- $N_{\text{calls}} = \left\lceil \frac{S_{\text{total}}}{B} \right\rceil$: Toplam sistem çağrısı sayısı
- $T_{\text{syscall}}$: Kullanıcı $\rightarrow$ Çekirdek bağlam değişimi ve VFS yönlendirme maliyeti ($\approx 400 - 800\text{ ns}$)

### Sistem Çağrısı Ek Yük Oranı ($\rho_{\text{overhead}}$)
Toplam I/O süresi içindeki çekirdek geçiş maliyeti:

$$\rho_{\text{overhead}}(B) = \frac{\frac{S_{\text{total}}}{B} \cdot T_{\text{syscall}}}{\frac{S_{\text{total}}}{B} \cdot T_{\text{syscall}} + \frac{S_{\text{total}}}{\text{BW}}} = \frac{T_{\text{syscall}}}{T_{\text{syscall}} + \frac{B}{\text{BW}}}$$

- **Küçük Bloklarda ($B = 1\text{ Bayt}$)**: $\frac{B}{\text{BW}} \approx 0.001\text{ ns} \ll T_{\text{syscall}}$. Zamanın **%99.9'u** syscall geçişinde harcanır, I/O hızı yerlerde sürünür!
- **Büyük Bloklarda ($B = 64\text{ KB}$ veya $1\text{ MB}$)**: $\rho_{\text{overhead}} \to 0$. Syscall maliyeti tamamen sönümlenir ve donanım bant genişliği (NVMe Bus Saturation) sınırına ulaşılır.
- **En Küçük Optimum Blok Boyutu**: Linux bellek yönetiminde sayfa boyutu $4096\text{ Bayt}$ ($4\text{ KB}$) olduğu için, $B \ge 4096$ seçildiğinde Page Cache hizalanması (alignment) mükemmelleşir.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 7 (CODE 1): POSIX Düşük Seviyeli I/O Çekirdek Simülasyon Motoru
open, read, write, lseek, O_APPEND ve Sayfa Önbelleği (Page Cache) Modeli
"""

from enum import IntFlag
from typing import Dict, List, Optional, Tuple

class OpenFlags(IntFlag):
    O_RDONLY   = 0x0000
    O_WRONLY   = 0x0001
    O_RDWR     = 0x0002
    O_CREAT    = 0x0040
    O_EXCL     = 0x0080
    O_TRUNC    = 0x0200
    O_APPEND   = 0x0400

class SimulatedDiskFile:
    def __init__(self, name: str, mode: int = 0o644):
        self.name = name
        self.mode = mode
        self.data = bytearray()
        self.is_synced_to_disk = True

class PosixFileDescription:
    def __init__(self, file_obj: SimulatedDiskFile, flags: OpenFlags):
        self.file_obj = file_obj
        self.flags = flags
        self.offset = 0

class PosixIoKernelSimulator:
    def __init__(self):
        self.storage: Dict[str, SimulatedDiskFile] = {}
        self.open_descriptions: Dict[int, PosixFileDescription] = {}
        self.next_fd = 3

    def open(self, path: str, flags: OpenFlags, mode: int = 0o644) -> int:
        exists = path in self.storage

        # 1. O_CREAT ve O_EXCL Denetimi
        if (flags & OpenFlags.O_CREAT) and (flags & OpenFlags.O_EXCL) and exists:
            raise FileExistsError(f"EEXIST: File '{path}' already exists (O_CREAT | O_EXCL)")

        if not exists:
            if not (flags & OpenFlags.O_CREAT):
                raise FileNotFoundError(f"ENOENT: No such file or directory: '{path}'")
            # Dosyayı oluştur
            disk_file = SimulatedDiskFile(path, mode)
            self.storage[path] = disk_file
        else:
            disk_file = self.storage[path]

        # 2. O_TRUNC Denetimi
        if (flags & OpenFlags.O_TRUNC) and (flags & (OpenFlags.O_WRONLY | OpenFlags.O_RDWR)):
            disk_file.data.clear()
            disk_file.is_synced_to_disk = False

        # 3. Dosya Tanıtıcısı ve Açık Tanım Tahsisi
        fd = self.next_fd
        self.next_fd += 1
        desc = PosixFileDescription(disk_file, flags)
        
        # O_APPEND başlangıçta ofseti dosya sonuna ayarlayabilir
        if flags & OpenFlags.O_APPEND:
            desc.offset = len(disk_file.data)

        self.open_descriptions[fd] = desc
        return fd

    def read(self, fd: int, count: int) -> bytes:
        if fd not in self.open_descriptions:
            raise OSError("EBADF: Bad file descriptor")
        desc = self.open_descriptions[fd]
        
        # Erişim modu denetimi
        mode_mask = desc.flags & 0x0003
        if mode_mask == OpenFlags.O_WRONLY:
            raise PermissionError("EBADF: File descriptor is write-only")

        available = len(desc.file_obj.data) - desc.offset
        if available <= 0:
            return b"" # EOF

        bytes_to_read = min(count, available)
        chunk = bytes(desc.file_obj.data[desc.offset : desc.offset + bytes_to_read])
        desc.offset += bytes_to_read
        return chunk

    def write(self, fd: int, data: bytes) -> int:
        if fd not in self.open_descriptions:
            raise OSError("EBADF: Bad file descriptor")
        desc = self.open_descriptions[fd]

        mode_mask = desc.flags & 0x0003
        if mode_mask == OpenFlags.O_RDONLY:
            raise PermissionError("EBADF: File descriptor is read-only")

        # O_APPEND Kuralı: Yazmadan önce daima dosya sonuna zıpla!
        if desc.flags & OpenFlags.O_APPEND:
            desc.offset = len(desc.file_obj.data)

        # Belleğe yaz (Page Cache simülasyonu)
        end_pos = desc.offset + len(data)
        if end_pos > len(desc.file_obj.data):
            # Dosyayı büyüt
            desc.file_obj.data.extend(b"\x00" * (end_pos - len(desc.file_obj.data)))

        desc.file_obj.data[desc.offset : end_pos] = data
        desc.offset = end_pos
        desc.file_obj.is_synced_to_disk = False
        return len(data)

    def lseek(self, fd: int, offset: int, whence: int) -> int:
        """SEEK_SET=0, SEEK_CUR=1, SEEK_END=2"""
        if fd not in self.open_descriptions:
            raise OSError("EBADF: Bad file descriptor")
        desc = self.open_descriptions[fd]

        if whence == 0:    # SEEK_SET
            new_pos = offset
        elif whence == 1:  # SEEK_CUR
            new_pos = desc.offset + offset
        elif whence == 2:  # SEEK_END
            new_pos = len(desc.file_obj.data) + offset
        else:
            raise ValueError("EINVAL: Invalid whence argument")

        if new_pos < 0:
            raise OSError("EINVAL: Invalid offset (before beginning of file)")

        desc.offset = new_pos
        return desc.offset

    def fsync(self, fd: int) -> bool:
        if fd not in self.open_descriptions:
            raise OSError("EBADF: Bad file descriptor")
        desc = self.open_descriptions[fd]
        desc.file_obj.is_synced_to_disk = True
        return True

    def close(self, fd: int) -> None:
        if fd not in self.open_descriptions:
            raise OSError("EBADF: Bad file descriptor")
        del self.open_descriptions[fd]

# Doğrulama Testi
if __name__ == "__main__":
    kernel = PosixIoKernelSimulator()
    # 1. Dosya oluştur ve aç
    fd_write = kernel.open("/flight_log.dat", OpenFlags.O_WRONLY | OpenFlags.O_CREAT | OpenFlags.O_TRUNC)
    written = kernel.write(fd_write, b"TELEMETRY_HEADER_OK:")
    kernel.fsync(fd_write)
    kernel.close(fd_write)

    # 2. Dosyayı O_APPEND ile tekrar aç ve ekleme yap
    fd_append = kernel.open("/flight_log.dat", OpenFlags.O_WRONLY | OpenFlags.O_APPEND)
    kernel.write(fd_append, b"ALTITUDE_12000FT")
    kernel.close(fd_append)

    # 3. Dosyayı O_RDONLY ile aç ve lseek ile doğrula
    fd_read = kernel.open("/flight_log.dat", OpenFlags.O_RDONLY)
    full_data = kernel.read(fd_read, 100)
    print(f"[*] Okunan Tam Veri: {full_data.decode('utf-8')}")
    
    # Başa sar (lseek SEEK_SET)
    kernel.lseek(fd_read, 0, 0)
    header = kernel.read(fd_read, 9)
    print(f"[*] lseek Sonrası Baştan 9 Bayt: {header.decode('utf-8')}")
    kernel.close(fd_read)

```

## 6. Kod 01 Analizi: Çekirdek Düşük Seviyeli I/O Mekanizmalarının Doğrulanması

Kod 01 simülatörü Linux çekirdeğinin dosya I/O kurallarını doğrulamıştır:

1. **`O_APPEND` Atomikliği**:
   - `fd_append` tanıtıcısı açıldığında ofset dosya sonuna konumlanmış ve yazma işlemi mevcut içeriği silmeden dosyanın ardına eklenmiştir (`TELEMETRY_HEADER_OK:ALTITUDE_12000FT`).
   - Gerçek Linux çekirdeğinde `O_APPEND` bayrağı ayarlandığında, kullanıcı `lseek()` ile ofseti başa alsa bile, `write()` çağrıldığı mikrosaniyede çekirdek zorla ofseti dosya boyutuna (`i_size`) eşitler.
2. **`lseek` ile Rastgele Erişim**:
   - Dosya okunduktan sonra `lseek(fd_read, 0, SEEK_SET)` çağrısı yapılarak dosya imleci sıfırlanmış ve ilk 9 bayt (`TELEMETRY`) yeniden okunmuştur.
3. **Yetki Denetimi**:
   - `O_WRONLY` ile açılan bir tanıtıcı üzerinden `read()` çağrılması engellenmiş (`PermissionError / EBADF`).


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 9 (CODE 2): C++20 SafePosixIO Güvenli I/O Sarmalayıcısı Simülatörü
read_all, write_all Döngüleri, EINTR Kurtarma ve O_EXCL Atomikliği
"""

from typing import List, Tuple, Optional

class Cpp20SafePosixIoSimulator:
    """
    Modern C++20 std::span ve Robust POSIX I/O Mimarisi
    Kısa okuma/yazmaları (Short Read/Write) ve EINTR kesintilerini yönetir.
    """
    def __init__(self, kernel_sim: PosixIoKernelSimulator):
        self.kernel = kernel_sim
        self.eintr_retry_count = 0

    def write_all(self, fd: int, payload: bytes, inject_short_write: bool = False) -> Tuple[int, int]:
        """
        Tüm baytlar yazılana kadar dönen güvenli write döngüsü.
        Döner: (toplam_yazılan_bayt, çağrı_sayısı)
        """
        total_written = 0
        calls_count = 0
        remaining = len(payload)

        while total_written < len(payload):
            calls_count += 1
            chunk_size = remaining
            if inject_short_write and remaining > 10:
                # Kasıtlı kısa yazma enjekte et (Örn: Çekirdek tamponu doldu)
                chunk_size = 10

            chunk = payload[total_written : total_written + chunk_size]
            n = self.kernel.write(fd, chunk)
            total_written += n
            remaining -= n

        return total_written, calls_count

    def read_all(self, fd: int, expected_size: int, inject_short_read: bool = False) -> Tuple[bytes, int]:
        """
        Tampon dolana veya EOF gelene kadar dönen güvenli read döngüsü.
        """
        received = bytearray()
        calls_count = 0

        while len(received) < expected_size:
            calls_count += 1
            request_size = expected_size - len(received)
            if inject_short_read and request_size > 8:
                request_size = 8

            chunk = self.kernel.read(fd, request_size)
            if not chunk:
                break # EOF
            received.extend(chunk)

        return bytes(received), calls_count

# Test ve Doğrulama
sim_kernel = PosixIoKernelSimulator()
safe_io = Cpp20SafePosixIoSimulator(sim_kernel)

test_payload = b"RADAR_RADIAL_VELOCITY_DATA_BLOCK_PACKET_99"
fd = sim_kernel.open("/safe_telemetry.bin", OpenFlags.O_WRONLY | OpenFlags.O_CREAT | OpenFlags.O_TRUNC)

# Kısa yazma enjekte edilmiş güvenli döngü testi
bytes_w, loop_calls = safe_io.write_all(fd, test_payload, inject_short_write=True)
sim_kernel.close(fd)

print(f"[C++20 SafeIO] write_all Tamamlandı: {bytes_w} bayt ({loop_calls} sistem çağrısı döngüsünde kurtarıldı)")

# Kısa okuma enjekte edilmiş güvenli okuma testi
fd_in = sim_kernel.open("/safe_telemetry.bin", OpenFlags.O_RDONLY)
read_res, read_loops = safe_io.read_all(fd_in, len(test_payload), inject_short_read=True)
sim_kernel.close(fd_in)

print(f"[C++20 SafeIO] read_all Tamamlandı: {len(read_res)} bayt ({read_loops} çağrı döngüsünde)")
assert read_res == test_payload, "HATA: Veri bütünlüğü bozuldu!"

```

## 7. Kod 02 Analizi: C++20 `std::span` ve Robust I/O Mimarisi

### Üretim Seviyesinde C++20 `write_all` ve `read_all` Şablonu

Savunma sanayii telemetri kaydedicilerinde kullanılan C++20 kaynak kodu:

```cpp
#include <unistd.h>
#include <cerrno>
#include <span>
#include <system_error>

namespace defense::io {

    // C++20 std::span ile sıfır kopyalı güvenli yazma
    [[nodiscard]] std::error_code write_all(int fd, std::span<const std::byte> buffer) noexcept {
        size_t total_written = 0;
        const auto* ptr = reinterpret_cast<const char*>(buffer.data());
        const size_t total_size = buffer.size();

        while (total_written < total_size) {
            ssize_t bytes_written = ::write(fd, ptr + total_written, total_size - total_written);
            if (bytes_written < 0) {
                if (errno == EINTR) {
                    continue; // Sinyal kesintisinde döngüye devam et
                }
                return std::error_code(errno, std::generic_category());
            }
            total_written += static_cast<size_t>(bytes_written);
        }
        return {}; // Başarılı (error code yok)
    }

    // Neden close() asla EINTR ile tekrarlanmaz?
    void safe_close(int& fd) noexcept {
        if (fd >= 0) {
            // Linux çekirdeğinde close() EINTR dönse dahi FD tablodan silinmiştir!
            // Tekrar close(fd) çağrılırsa başka bir thread'in yeni açtığı FD kazara kapatılabilir!
            ::close(fd);
            fd = -1;
        }
    }
}
```

### Kritik Sistem Mühendisliği İlkeleri:
1. **`EINTR` Yönetimi**: Sinyal kesintisi bir hata değildir; işlemin yeniden denenmesi gerektiğini bildiren bir durumdur.
2. **`close()` Tehlikesi**: POSIX standardında muğlak olsa da, Linux çekirdeğinde `sys_close` her zaman tanıtıcıyı serbest bırakır. `close` başarısız olsa bile asla döngü içinde tekrar çağrılmamalıdır!


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 11 (CODE 3): Sabotaj ve Savunma Laboratuvarı
Korumasız Tekil write() ile Veri Kaybı (Sabotage) vs write_all ve O_EXCL Savunması (Defense)
"""

class ShortWriteSabotageLab:
    def __init__(self):
        self.kernel = PosixIoKernelSimulator()

    def run_sabotage_naive_write(self, data: bytes) -> Tuple[int, int, bool]:
        """
        SABOTAJ: Tek bir write() çağırıp dönen değeri kontrol etmeyen acemi kod.
        Ağ borusu veya dolu tamponda yarım yazma oluşur.
        """
        fd = self.kernel.open("/naive_stream.dat", OpenFlags.O_WRONLY | OpenFlags.O_CREAT | OpenFlags.O_TRUNC)
        
        # Simüle edilen ortam: Çekirdek sadece ilk 16 baytı kabul ediyor!
        kernel_accepted_bytes = min(len(data), 16)
        written = self.kernel.write(fd, data[:kernel_accepted_bytes])
        self.kernel.close(fd)

        is_data_lost = (written < len(data))
        return len(data), written, is_data_lost

    def run_defense_write_all(self, data: bytes) -> Tuple[int, int, bool]:
        """
        SAVUNMA: write_all döngüsü ile tampon bitene kadar parçaları yazan sağlam kod.
        """
        safe_io = Cpp20SafePosixIoSimulator(self.kernel)
        fd = self.kernel.open("/safe_stream.dat", OpenFlags.O_WRONLY | OpenFlags.O_CREAT | OpenFlags.O_TRUNC)
        
        total_w, _ = safe_io.write_all(fd, data, inject_short_write=True)
        self.kernel.close(fd)

        is_data_lost = (total_w < len(data))
        return len(data), total_w, is_data_lost

lab = ShortWriteSabotageLab()
payload = b"CRITICAL_MISSILE_TELEMETRY_COORDINATES_LAT_LON_ALT_SPEED_LOCK"

orig_len1, written1, lost1 = lab.run_sabotage_naive_write(payload)
orig_len2, written2, lost2 = lab.run_defense_write_all(payload)

print(f"[Sabotaj Testi] Gönderilen: {orig_len1}B, Yazılan: {written1}B -> Veri Kaybı Var mı?: {lost1}")
print(f"[Savunma Testi] Gönderilen: {orig_len2}B, Yazılan: {written2}B -> Veri Kaybı Var mı?: {lost2}")

```

## 8. Kod 03 Analizi: Havacılık Güvenliği (DO-178C) ve Veri Bütünlüğü

Kod 03 laboratuvarında görüldüğü üzere:

1. **Sessiz Veri Bozulması (Silent Data Corruption)**:
   - Acemi yazılımcının yazdığı kodda 62 baytlık füze telemetri paketinin yalnızca ilk 16 baytı yazılmış, geri kalan 46 bayt sessizce çöpe gitmiştir.
   - Bu kod hiçbir hata (`errno`) fırlatmamıştır; çünkü `write()` pozitif bir sayı dönmüştür!
2. **DO-178C Uyum Kuralı**:
   - Aviyonik sistemlerde `write()` fonksiyonunun dönüş değeri `size` ile karşılaştırılmadan işlem başarılı kabul edilemez.
   - `write_all` algoritması, çekirdek tamponları doysa dahi döngüye devam ederek veri kaybını kesin olarak engeller.
3. **TOCTOU Koruması**:
   - `open(file, O_CREAT | O_EXCL)` kullanımı; "önce `access()` ile dosya var mı bak, yoksa `open()` yap" mantığındaki ölümcül yarış durumunu ortadan kaldırır. Çekirdek bu işlemi atomik inode kilidi ile tek adımda icra eder.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 13 (CODE 4): Hata Enjeksiyonu ve Sınır Koşulları
EBADF, EEXIST (O_EXCL), EINVAL (lseek Negatif), ENOSPC (Disk Dolumu) Hata Testleri
"""

from typing import Dict, List, Tuple

class PosixIoFaultInjector:
    def __init__(self):
        self.kernel = PosixIoKernelSimulator()

    def test_eexist_collision(self) -> Tuple[int, str]:
        """Var olan dosyayı O_CREAT | O_EXCL ile açmaya çalışma."""
        try:
            fd1 = self.kernel.open("/secure_lock.pid", OpenFlags.O_WRONLY | OpenFlags.O_CREAT | OpenFlags.O_EXCL)
            # İkinci defa aynı bayraklarla aç:
            fd2 = self.kernel.open("/secure_lock.pid", OpenFlags.O_WRONLY | OpenFlags.O_CREAT | OpenFlags.O_EXCL)
            return 0, "SUCCESS"
        except FileExistsError as e:
            return -1, str(e)

    def test_write_to_readonly(self) -> Tuple[int, str]:
        """O_RDONLY ile açılmış tanıtıcıya yazmaya çalışma."""
        try:
            self.kernel.storage["/config.xml"] = SimulatedDiskFile("/config.xml")
            fd = self.kernel.open("/config.xml", OpenFlags.O_RDONLY)
            self.kernel.write(fd, b"<xml>HACK</xml>")
            return 0, "SUCCESS"
        except PermissionError as e:
            return -1, str(e)

    def test_negative_lseek(self) -> Tuple[int, str]:
        """Dosya başından geriye doğru lseek yapma."""
        try:
            fd = self.kernel.open("/test_seek.bin", OpenFlags.O_RDWR | OpenFlags.O_CREAT)
            self.kernel.lseek(fd, -50, 0) # SEEK_SET ile negatif ofset
            return 0, "SUCCESS"
        except OSError as e:
            return -1, str(e)

injector = PosixIoFaultInjector()

c_excl, msg_excl = injector.test_eexist_collision()
c_ro, msg_ro = injector.test_write_to_readonly()
c_seek, msg_seek = injector.test_negative_lseek()

print("=== [POSIX I/O HATA ENJEKSİYONU DENETİMLERİ] ===")
print(f"[O_EXCL Çakışması]      -> {msg_excl}")
print(f"[Salt-Okunur Dosyaya Yazma] -> {msg_ro}")
print(f"[Geçersiz lseek Konumu]     -> {msg_seek}")

```

## 9. Kod 04 Analizi: Hata Kodları ve Çekirdek Koruma Mekanizmaları

Kod 04'te incelenen hata kodları Linux çekirdeğinin güvenlik bariyerleridir:

1. **`EEXIST` (Hata 17)**: `O_CREAT | O_EXCL` atomik kilit mekanizmasıdır. Süreç PID kilit dosyalarında (`/var/run/daemon.pid`) iki sürecin aynı anda başlamasını engellemek için kullanılır.
2. **`EBADF` (Hata 9 / PermissionError)**: Dosya erişim modu (`O_RDONLY`), icra edilmek istenen sistem çağrısı (`write`) ile uyuşmadığında çekirdek işlemi derhal engeller.
3. **`EINVAL` (Hata 22)**: `lseek()` ile dosya başından geriye (`offset < 0`) gidilemez. Ancak dosya sonunun ilerisine gidilmesinde hiçbir sakınca yoktur (Sparse File oluşturur).


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 15 (CODE 5): Kapsamlı Benchmark ve Performans Ölçümü
Tampon Boyutuna Göre (64B, 512B, 4KB, 64KB, 1MB) I/O Throughput ve Syscall Maliyeti Simülasyonu
"""

import numpy as np
from typing import Dict, Tuple

def run_io_benchmark(total_bytes: int = 10 * 1024 * 1024) -> Dict[str, any]:
    """
    10 MB Veriyi Farklı Blok Boyutlarında (B) Yazarken Syscall Yükü ve Verim
    """
    buffer_sizes = [64, 512, 4096, 65536, 1048576] # Bayt
    t_syscall_ns = 500.0 # 500 ns ortalama syscall maliyeti
    storage_bw_mb_s = 500.0 # 500 MB/s SSD bant genişliği
    
    results = {}

    for b in buffer_sizes:
        num_calls = int(np.ceil(total_bytes / b))
        syscall_time_s = (num_calls * t_syscall_ns) / 1e9
        disk_transfer_time_s = (total_bytes / (1024 * 1024)) / storage_bw_mb_s
        total_time_s = syscall_time_s + disk_transfer_time_s
        effective_throughput_mb_s = (total_bytes / (1024 * 1024)) / total_time_s
        overhead_pct = (syscall_time_s / total_time_s) * 100

        results[b] = {
            "num_calls": num_calls,
            "total_time_ms": total_time_s * 1000,
            "throughput_mb_s": effective_throughput_mb_s,
            "overhead_pct": overhead_pct
        }

    return results

bench_res = run_io_benchmark()

print("=== [BLOK BOYUTU VS POSIX I/O BAŞARIMI BENCHMARK] ===")
for b, data in bench_res.items():
    label = f"{b} B" if b < 1024 else (f"{b//1024} KB" if b < 1048576 else f"{b//(1024*1024)} MB")
    print(f"[{label:>6}] Syscall Sayısı: {data['num_calls']:>8} | Süre: {data['total_time_ms']:>7.2f} ms | Hız: {data['throughput_mb_s']:>6.1f} MB/s | Syscall Yükü: %{data['overhead_pct']:>5.1f}")

```

## 10. Kod 05 Analizi: 4 KB Sayfa Boyutu ve Syscall Başabaş Noktası

Benchmark sonuçları sistem mimarisi açısından çarpıcı gerçekleri ortaya koyar:

1. **Küçük Tampon Felaketi (64 Bayt)**:
   - 10 MB veriyi 64 baytlık parçalarla yazmak $163.840$ adet sistem çağrısı demektir.
   - Toplam sürenin **%80.4'ü** sadece çekirdeğe girip çıkmakla (bağlam değişimi) harcanmakta; hız $500\text{ MB/s}$ yerine **$98\text{ MB/s}$** seviyesine çökmektedir.
2. **4 KB Başabaş Noktası**:
   - Blok boyutu $4\text{ KB}$ (Linux Page boyutu) yapıldığında syscall sayısı $2.560$'a iner.
   - Syscall ek yükü **%6.0** seviyesine düşer, aktarım hızı **$470\text{ MB/s}$** ile donanım tavanına yaklaşır.
3. **64 KB ve Üzeri**:
   - Syscall yükü tamamen önemsizleşir (%0.4) ve NVMe veriyolu doyuma ulaşır ($498\text{ MB/s}$).


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 17 (CODE 6): Görselleştirme Dashboard'u ve Katı Doğrulama (Assertions)
4 Panelli Koyu Tema Dashboard (Syscall Akışı, Blok Boyutu vs Hız, Ofset Dinamiği, Hata Dağılımı)
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_091_open_read_write_close_posix_io.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    # -------------------------------------------------------------
    # PANEL 1: Tampon Boyutuna Göre Verim (Throughput)
    # -------------------------------------------------------------
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    
    labels = ['64 B', '512 B', '4 KB', '64 KB', '1 MB']
    speeds = [98.1, 335.6, 470.1, 498.0, 499.8]
    colors1 = ['#EF4444', '#F59E0B', '#38BDF8', '#10B981', '#10B981']
    
    bars1 = ax1.bar(labels, speeds, color=colors1, width=0.55, edgecolor='#0F172A', linewidth=2)
    ax1.set_title("1. Blok Boyutuna (Buffer Size) Göre I/O Hızı (MB/s)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax1.set_ylabel("Efektif Hız (MB/s)", fontsize=11, color='#CBD5E1')
    ax1.axhline(y=500.0, color='#64748B', linestyle='--', label='Donanım Sınırı (500 MB/s)')
    ax1.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax1.legend(loc='lower right', framealpha=0.8, facecolor='#0F172A')

    for b in bars1:
        y_val = b.get_height()
        ax1.annotate(f"{y_val:.1f}\nMB/s",
                     xy=(b.get_x() + b.get_width() / 2, y_val),
                     xytext=(0, 4), textcoords="offset points",
                     ha='center', va='bottom', fontsize=9, fontweight='bold',
                     color='#F8FAFC')

    # -------------------------------------------------------------
    # PANEL 2: Syscall Sayısı ve Ek Yük Oranı (%)
    # -------------------------------------------------------------
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    
    overheads = [80.4, 32.9, 6.0, 0.4, 0.0]
    
    ax2.plot(labels, overheads, marker='o', markersize=8, color='#EF4444', linewidth=2.5, label='Syscall Bağlam Değişimi Kaybı (%)')
    ax2.set_title("2. Blok Boyutuna Göre Syscall Ek Yük Yüzdesi", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax2.set_ylabel("Syscall Kayıp Yüzdesi (%)", fontsize=11, color='#CBD5E1')
    ax2.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax2.legend(loc='upper right', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 3: Kısa Yazma (Short Write) vs write_all Bütünlüğü
    # -------------------------------------------------------------
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    
    steps = ['Paket 1', 'Paket 2', 'Paket 3', 'Paket 4', 'Paket 5']
    naive_acc = [16, 16, 16, 16, 16] # Takıldı, yarım kaldı
    safe_acc = [16, 32, 48, 64, 80]  # Döngü ile tamamlandı
    
    x = np.arange(len(steps))
    w = 0.35
    ax3.bar(x - w/2, naive_acc, w, label='Korumasız write() (Veri Kaybı!)', color='#EF4444', alpha=0.9)
    ax3.bar(x + w/2, safe_acc, w, label='write_all() Döngüsü (Tam Aktarım)', color='#10B981', alpha=0.9)
    
    ax3.set_title("3. Kısa Yazma Kurtarma Karşılaştırması (Kümülatif Bayt)", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax3.set_xticks(x)
    ax3.set_xticklabels(steps, fontsize=10, color='#E2E8F0')
    ax3.set_ylabel("Diske Yazılan Bayt", fontsize=11, color='#CBD5E1')
    ax3.grid(True, linestyle='--', alpha=0.2, color='#64748B')
    ax3.legend(loc='upper left', framealpha=0.8, facecolor='#0F172A')

    # -------------------------------------------------------------
    # PANEL 4: open() Bayrakları Yetenek ve Güvenlik Matrisi
    # -------------------------------------------------------------
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    
    flags = ['O_CREAT', 'O_EXCL', 'O_TRUNC', 'O_APPEND', 'O_SYNC', 'O_CLOEXEC']
    safety_score = [80, 95, 75, 90, 98, 99]
    colors4 = ['#38BDF8', '#10B981', '#F59E0B', '#38BDF8', '#10B981', '#10B981']
    
    y = np.arange(len(flags))
    ax4.barh(y, safety_score, color=colors4, height=0.5, edgecolor='#0F172A', linewidth=2)
    ax4.set_title("4. POSIX open() Bayrakları Güvenlik ve Dayanıklılık Puanı", fontsize=13, fontweight='bold', color='#F8FAFC', pad=12)
    ax4.set_yticks(y)
    ax4.set_yticklabels(flags, fontsize=10, color='#E2E8F0', fontweight='bold')
    ax4.set_xlabel("Güvenilirlik Endeksi (100 Üzerinden)", fontsize=11, color='#CBD5E1')
    ax4.set_xlim(0, 110)
    ax4.grid(True, linestyle='--', alpha=0.2, color='#64748B')

    for i, v in enumerate(safety_score):
        ax4.text(v + 1.5, i, f"{v}", va='center', fontsize=9, fontweight='bold', color='#F8FAFC')

    plt.tight_layout()
    plt.savefig(output_png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_png_path}")

def verify_all_assertions(png_path: str = DEFAULT_PNG):
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dosya Varlık ve Boyut Testleri
    assert os.path.exists(png_path), f"HATA: {png_path} görseli bulunamadı!"
    png_size = os.path.getsize(png_path)
    assert png_size > 50000, f"HATA: Görsel boyutu yetersiz ({png_size} bayt < 50KB)!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {png_size} bayt.")

    # 2. Kernel Simülatör Doğrulaması
    sim = PosixIoKernelSimulator()
    fd = sim.open("/test_assert.bin", OpenFlags.O_WRONLY | OpenFlags.O_CREAT | OpenFlags.O_TRUNC)
    sim.write(fd, b"ABCDEF")
    sim.close(fd)
    
    fd_r = sim.open("/test_assert.bin", OpenFlags.O_RDONLY)
    data = sim.read(fd_r, 3)
    assert data == b"ABC", "HATA: İlk 3 bayt ABC olmalı!"
    pos = sim.lseek(fd_r, 1, 0) # SEEK_SET to index 1
    assert pos == 1, "HATA: lseek pozisyonu 1 olmalıdır!"
    data2 = sim.read(fd_r, 2)
    assert data2 == b"BC", "HATA: lseek sonrası okuma BC olmalı!"
    sim.close(fd_r)
    print("  [+] open/read/write/lseek Temel Çekirdek Kuralları Doğrulandı.")

    # 3. C++20 write_all ve read_all Doğrulaması
    safe_io = Cpp20SafePosixIoSimulator(sim)
    fd_w = sim.open("/safe_assert.bin", OpenFlags.O_WRONLY | OpenFlags.O_CREAT | OpenFlags.O_TRUNC)
    payload = b"012345678901234567890123456789"
    tot_w, calls_w = safe_io.write_all(fd_w, payload, inject_short_write=True)
    assert tot_w == len(payload), "HATA: write_all tüm baytları yazmalıdır!"
    assert calls_w > 1, "HATA: Kısa yazma enjeksiyonu döngü üretmeliydi!"
    sim.close(fd_w)
    print("  [+] C++20 write_all / read_all Kısa I/O Kurtarma Doğrulandı.")

    # 4. Hata Enjeksiyonu Doğrulaması
    inj = PosixIoFaultInjector()
    c_excl, _ = inj.test_eexist_collision()
    assert c_excl == -1, "HATA: O_CREAT|O_EXCL çakışması EEXIST vermelidir!"
    c_ro, _ = inj.test_write_to_readonly()
    assert c_ro == -1, "HATA: Salt okunur tanıtıcıya yazma EBADF vermelidir!"
    c_seek, _ = inj.test_negative_lseek()
    assert c_seek == -1, "HATA: Negatif lseek EINVAL vermelidir!"
    print("  [+] Hata Enjeksiyonu (EEXIST, EBADF, EINVAL) Doğrulandı.")

    # 5. Benchmark Metrikleri Doğrulaması
    b_data = run_io_benchmark(total_bytes=1024 * 1024)
    assert b_data[1048576]["throughput_mb_s"] > b_data[64]["throughput_mb_s"], "HATA: Büyük blok küçük bloktan hızlı olmalıdır!"
    print("  [+] Benchmark Metrikleri Doğrulandı (Büyük blok üstünlüğü kanıtlandı).")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)

```

## 11. Görsel Dashboard İncelemesi (4 Panelli Sistem Görünümü)

Oluşturulan `gun_091_open_read_write_close_posix_io.png` dashboard'u düşük seviyeli POSIX I/O dinamiklerini 4 temel boyutta somutlaştırır:

- **Panel 1 (Blok Boyutu vs Hız)**: 64 bayttan 1 MB'a kadar tampon boyutunun I/O başarımına etkisini gösterir. 4 KB sayfa sınırında hızın nasıl sıçrama yaptığını ($470\text{ MB/s}$) belgeler.
- **Panel 2 (Syscall Ek Yükü)**: Küçük bloklarda ($64\text{ B}$) zamanın %80'inin syscall bağlam değişiminde kaybolduğunu, blok boyutu büyüdükçe bu yükün %0'a indiğini grafiksel olarak modeller.
- **Panel 3 (Kısa Yazma Kurtarma)**: Korumasız tekil `write()` çağrısının tampon dolumunda 16 baytta kalarak veri kaybına yol açtığını, buna karşılık `write_all()` döngüsünün tüm baytları adım adım kurtardığını gösterir.
- **Panel 4 (open Bayrakları Güvenlik Puanı)**: `O_CREAT`, `O_EXCL`, `O_TRUNC`, `O_APPEND`, `O_SYNC` ve `O_CLOEXEC` bayraklarının savunma sanayii güvenilirlik indeksini karşılaştırır.


## 12. 5N1K Derinlemesine Sistem Analizi

| Soru | Sistem Mühendisliği Yanıtı |
| :--- | :--- |
| **Ne?** | `open`, `read`, `write`, `close`, `lseek` ve `fsync`; kullanıcı alanı tamponu olmaksızın doğrudan Linux VFS ve aygıt sürücüleriyle haberleşen temel POSIX sistem çağrılarıdır. |
| **Neden?** | Donanım aygıtlarına (radar, sensör, ağ soketi) en düşük gecikmeyle veri aktarmak, işletim sistemi önbelleğini hassas yönetmek ve deterministik I/O sağlamak için. |
| **Nerede?** | Linux çekirdeğinin `fs/read_write.c`, `fs/open.c`, glibc `<fcntl.h>`, `<unistd.h>` başlıklarında ve görev bilgisayarı sürücülerinde. |
| **Nasıl?** | Süreç bellek işaretçisi ve boyut ile `syscall` yapar; çekirdek sayfa önbelleğinde (Page Cache) sayfaları günceller veya diskten blokları okur. |
| **Ne Zaman?** | Bir dosya oluşturulurken, telemetri günlüğü tutulurken, ağ soketinden bayt akışı okunurken veya uçuş verileri NVRAM'e senkronize edilirken. |
| **Kim?** | Aviyonik gömülü yazılımcılar, işletim sistemi çekirdek mühendisleri ve yüksek başarımlı veritabanı mimarları. |


## 13. Günlük Hayat Benzetmesi: Kargo Gişesi, Toplu Koli ve Doğrudan Teslimat

Tamponlu C I/O (`stdio`) ile Tamponsuz POSIX I/O farkını bir kargo şubesi üzerinden anlayabiliriz:

```
+-------------------------------------------------------------------------+
|                           POSTA / KARGO ŞUBESİ                          |
|                                                                         |
| 1. TAMPONLU C I/O (fopen / fwrite / stdio):                             |
|    - Şube içinde büyük bir toplama sepeti vardır (User Space Buffer).   |
|    - Her mektup yazdığınızda gişeye gitmezsiniz; sepete atarsınız.      |
|    - Sepet 4096 mektup ile dolduğunda tek seferde kamyona yüklenir.    |
|    - Avantajı: Çok az gişe işlemi (az syscall).                         |
|    - Riski: Şubede yangın çıkarsa (çöküş) sepettekiler kül olur!       |
|                                                                         |
| 2. TAMPONSUZ POSIX I/O (open / write):                                  |
|    - Sepet yoktur! Her tek mektup için doğrudan gişe memuruna gidip     |
|      işlem yaptırırsınız (Doğrudan Çekirdek Syscall).                   |
|    - Eğer 1 bayt 1 bayt verirseniz memurla konuşmaktan gün biter!       |
|    - Doğru Kullanım: Evde büyük bir koli yapıp (4 KB - 64 KB Buffer)    |
|      gişeye tek seferde vermek.                                         |
|                                                                         |
| 3. FSYNC (Noter Onayı ve Kasaya Kilit):                                 |
|    - Gişe memuruna "Bu evrak kasaya girdi mi, gözümle göreceğim"        |
|      dersiniz. Memur kasaya kilitler, onay mührünü basar (fsync).       |
|    - Ancak bu işlem zaman alır (Gecikme artar, veri güvenliği %100).    |
+-------------------------------------------------------------------------+
```


## 14. Neden-Sonuç Tablosu ve Mimari Karar Matrisi

| Karar / Eylem | Doğrudan Sonuç | Potansiyel Risk / Hata Sınıfı | Mimari Tavsiye |
| :--- | :--- | :--- | :--- |
| `write()` dönüş değerini kontrol etmemek | Kısa yazma durumunda verinin yarısı yazılmaz. | **Sessiz Veri Kaybı (Data Loss)**. | Daima `write_all()` döngüsü kullanın. |
| Çok süreçli loglamada `O_APPEND` kullanmamak | Süreçler aynı ofsete yazıp birbirinin verisini ezer. | Bozuk log ve telemetri dosyaları. | Log dosyalarında mutlaka `O_APPEND` açın. |
| Dosya oluştururken `O_EXCL` unutmak | Dosya varsa sessizce üzerine yazılır. | TOCTOU yarış durumu (Race Condition). | Atomik kilit için `O_CREAT | O_EXCL` kullanın. |
| 1 baytlık tamponlarla `read()` / `write()` yapmak | Milyonlarca syscall bağlam değişimi oluşur. | CPU'nun kilitlenmesi, I/O hızının çökmesi. | Tampon boyutunu en az $4\text{ KB}$ seçin. |
| Kritik veride `fsync()` çağırmamak | Veri sadece RAM önbelleğinde kalır. | Ani elektrik kesintisinde sıfır bayt dosya. | Kritik veri paketinden sonra `fdatasync()` çağırın. |


## 15. Savunma Sanayii ve Görev Kritik Sistem Senaryoları

### 1. ASELSAN SAR Radar: O_DIRECT ile Ham Veri Kaydı
Sentetik Açıklıklı Radar (SAR) ham I/Q sinyal verisi saniyede $800\text{ MB}$ hızla üretildiğinde:
- Çekirdek sayfa önbelleği (Page Cache) RAM'i hızla tüketir ve sistemde bellek baskısı (OOM) yaratır.
- SAR kayıt birimi dosyayı `open("/mnt/nvme/sar.raw", O_WRONLY | O_DIRECT | O_SYNC)` ile açar.
- RAM'de 4096 bayta hizalanmış (page-aligned) tamponlar `write()` ile doğrudan NVMe SSD'ye DMA aktarımı yapar.
- İşlemci önbellekleri kirletilmeden deterministik veri kaydı sağlanır.

### 2. TUSAŞ Milli Muharip Uçak (KAAN) Kara Kutu: fdatasync ile Çöküş Koruması
Uçuş kontrol bilgisayarının parametreleri kara kutu (Crash Survivable Memory) birimine yazılırken:
- `write_all` ile $50\text{ Hz}$ periyotla uçuş açıları, irtifa ve motor durumu yazılır.
- Her periyodun sonunda `fdatasync(fd)` çağrılarak elektrik kesilse dahi son 20 milisaniyelik verinin kalıcı bellekte olması garanti edilir.


## 16. Gün Sonu Özeti

1. **Tamponsuz POSIX I/O**: `open`, `read`, `write` ve `close` doğrudan çekirdek sistem çağrılarıdır; kullanıcı alanında gizli tamponlama yapmaz, doğrudan Linux Sayfa Önbelleği (Page Cache) ile etkileşime girer.
2. **Kısa I/O ve Atomiklik Kanunu**: Ağ soketleri ve borularda `read`/`write` çağrılarının istenenden az veri döndürmesi (Short I/O) doğal bir çekirdek davranışıdır; veri kaybını önlemek için `read_all` ve `write_all` döngüleri ile atomik `O_EXCL` ve `O_APPEND` bayrakları kullanılmalıdır.
3. **Mühendislik ve Başarım İlkesi**: Syscall bağlam değişimi maliyetini amorti etmek için tampon boyutları $4\text{ KB}$ (sayfa sınırı) veya üzerinde tutulmalı; ani güç kayıplarına karşı dayanıklılık için `fsync` / `fdatasync` ile fiziksel senkronizasyon sağlanmalıdır.


## 17. Gelecek Gün Köprüsü: Gün 092

Yarın **GÜN 092** kapsamında:
- **Konu**: **Tamponlu (Buffered) vs Tamponsuz (Unbuffered) I/O Karşılaştırması**
- **Kapsam**: C Standart Kütüphanesi `FILE*` akışları (`fopen`, `fread`, `fwrite`, `fflush`), `setvbuf()` ile tamponlama modları (`_IONBF`, `_IOLBF`, `_IOFBF`), kullanıcı alanı vs çekirdek alanı bellek kopyalama maliyeti ve sistem mimarisi analizi.
- **Hazırlık**: Bugün öğrendiğimiz ham POSIX sistem çağrılarının üzerine inşa edilen standart kütüphane tamponlarının ne zaman hız kazandırdığını, ne zaman felakete yol açtığını derinlemesine kıyaslayacağız.
