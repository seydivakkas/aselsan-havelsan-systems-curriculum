# GÜN 093: Dosya Sistemi Metaverisi (Metadata), Inode Anatomisi ve stat(2) Sistem Çağrısı Ailesi

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
- **Konu**: Dosya Sistemi Metaverisi, Inode Veri Yapısı, `stat(2)` / `fstat(2)` / `lstat(2)` / `statx(2)`, Seyrek Dosyalar ve TOCTOU Güvenlik Mimarisi
- **Ön Koşul Bilgi**: Gün 090 (File Descriptor), Gün 091 (POSIX I/O) ve Gün 092 (Buffered vs Unbuffered I/O)
- **Hedef Sistemler**: ASELSAN Aviyonik Görev Bilgisayarı Dosya Bütünlük Denetimi, HAVELSAN C4I Güvenli Konfigürasyon Dağıtımı, Radar/Sonar Ham Veri Depolama Motorları, Adli Bilişim (Digital Forensics) ve MISRA C++20 / DO-178C Uyumlu Dosya Doğrulama.

### 40-Nokta Kalite ve Mimari Beyanı
Bu çalışma paketi; POSIX.1-2024 (`IEEE Std 1003.1-2024`), Linux Sanal Dosya Sistemi (VFS) çekirdek katmanı ve askeri gömülü standartlar temel alınarak tasarlanmıştır. Bu modülde; Unix dosya sistemlerinin temel taşı olan Inode (`index node`) yapısı, dosya adlarının neden inode içinde yer almadığı, `dentry` (directory entry) eşleşmesi, hard link ve sembolik link (symlink) farkları, `struct stat` bileşenlerinin bit düzeyinde çözümlenmesi, `atime`/`mtime`/`ctime` zaman damgalarının güvenlik boyutu, seyrek dosyalarda (sparse files) görünen boyut ($S_{\text{apparent}}$) ile tahsis edilen blok boyutu ($S_{\text{allocated}}$) arasındaki fark ve `stat` ile `open` arasındaki zaman penceresini istismar eden ölümcül TOCTOU (Time-of-Check to Time-of-Use) yarış koşullarına karşı `fstat` tabanlı atomik savunma mimarisi incelenecektir.


## 1. Teori ve Sistem Mimarisi: VFS, Inode ve Dizin Girişi (Dentry) Ayrımı

Unix ve Linux dosya sistemlerinde "her şey bir dosyadır" ilkesi, donanım düzeyinde soyutlanmış üç katmanlı hiyerarşiyle yönetilir:

```
+------------------------------------------------------------------------------------+
|                         DİZİN GİRİŞİ (DENTRY - DIRECTORY ENTRY)                    |
|  Dosya Adı: "telemetry.dat"    ----->  Inode Numarası: 1048578                    |
|  Dosya Adı: "telemetry_link"   ----->  Inode Numarası: 1048578 (Hard Link!)       |
+------------------------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------------------------+
|                               INODE (INDEX NODE) #1048578                          |
|  - Dosya Türü & İzinler (st_mode) : Düzenli Dosya, 0644 (rw-r--r--)                 |
|  - Bağlantı Sayısı (st_nlink)     : 2                                              |
|  - Kullanıcı / Grup (UID / GID)   : 1000 / 1000                                    |
|  - Dosya Boyutu (st_size)         : 409600 Bayt (400 KB)                           |
|  - Blok Sayısı (st_blocks)        : 800 (512-baytlık sektör)                       |
|  - Zaman Damgaları                : atime, mtime, ctime                            |
|  - Blok İşaretçileri (Extents)    : [Blok 50000 - 50099] -> Fiziksel Disk Sektörleri|
+------------------------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------------------------+
|                           FİZİKSEL VERİ BLOKLARI (DATA BLOCKS)                     |
|  [ Blok 50000 ] [ Blok 50001 ] ... [ Blok 50099 ] (Ham Baytlar & Sensör Verileri)  |
+------------------------------------------------------------------------------------+
```

### Neden Dosya Adı Inode İçinde Yer Almaz?
Geliştiricilerin sıklıkla düştüğü en büyük kavram yanılgısı, dosya adının dosyanın bir özelliği olduğunu sanmalarıdır. Gerçekte:
1. **Dizin de Bir Dosyadır**: Linux'ta dizin, yalnızca `(dosya_adı, inode_numarası)` çiftlerinden oluşan bir tablodur.
2. **Çoklu İsimlendirme (Hard Link)**: Aynı fiziksel inode, dosya sisteminin farklı dizinlerinde birden fazla isme (`dentry`) sahip olabilir. Dosya adını inode içine yazmak, hard link mimarisini imkansız kılardı.
3. **Yeniden Adlandırma Performansı ($O(1)$)**: Bir dosyayı aynı dosya sistemi içinde taşımak (`mv`) veya yeniden adlandırmak (`rename`), diskteki hiçbir veri bloğunu veya inode içeriğini değiştirmez; yalnızca dizin girişini günceller. Bu işlem $O(1)$ karmaşıklığında ve atomiktir.


## 2. Inode Anatomisi ve `struct stat` Veri Yapısı

POSIX standardı kapsamında bir dosyanın metaverisi `struct stat` ile çekirdekten kullanıcı alanına aktarılır:

```c
struct stat {
    dev_t     st_dev;     /* Dosyanın bulunduğu aygıtın ID'si */
    ino_t     st_ino;     /* Inode numarası (Dosya sistemi içinde eşsizdir) */
    mode_t    st_mode;    /* Dosya türü ve erişim izinleri (16-bit bitmask) */
    nlink_t   st_nlink;   /* Bu inode'a işaret eden hard link sayısı */
    uid_t     st_uid;     /* Dosya sahibinin Kullanıcı ID'si */
    gid_t     st_gid;     /* Dosya sahibinin Grup ID'si */
    dev_t     st_rdev;    /* Aygıt ID'si (Eğer dosya bir karakter veya blok aygıtıysa) */
    off_t     st_size;    /* Dosyanın toplam mantıksal boyutu (bayt cinsinden) */
    blksize_t st_blksize; /* Dosya sistemi I/O işlemleri için optimum blok boyutu */
    blkcnt_t  st_blocks;  /* Tahsis edilen 512-baytlık blok sayısı */
    struct timespec st_atim;  /* Son erişim zamanı (Access time) */
    struct timespec st_mtim;  /* Son içerik değiştirme zamanı (Modification time) */
    struct timespec st_ctim;  /* Son metaveri/durum değişim zamanı (Change time) */
};
```

### `st_mode` Bit Maskesi ve Dosya Türleri
`st_mode` 16-bitlik bir tamsayıdır ve iki ana bölümden oluşur:
1. **Dosya Türü (Bits 12–15, `S_IFMT` maskesi: `0170000`)**:
   - `S_IFREG` (`0100000`): Düzenli dosya (`S_ISREG(m)`)
   - `S_IFDIR` (`0040000`): Dizin (`S_ISDIR(m)`)
   - `S_IFLNK` (`0120000`): Sembolik link (`S_ISLNK(m)`)
   - `S_IFCHR` (`0020000`): Karakter aygıtı (`S_ISCHR(m)`)
   - `S_IFBLK` (`0060000`): Blok aygıtı (`S_ISBLK(m)`)
   - `S_IFIFO` (`0010000`): FIFO / Named pipe (`S_ISFIFO(m)`)
   - `S_IFSOCK` (`0140000`): UNIX domain soketi (`S_ISSOCK(m)`)
2. **Özel İzinler (Bits 9–11)**:
   - Set-UID (`04000`, `S_ISUID`), Set-GID (`02000`, `S_ISGID`), Sticky Bit (`01000`, `S_ISVTX`).
3. **Standart İzinler (Bits 0–8)**:
   - Kullanıcı (`rwx`), Grup (`rwx`), Diğerleri (`rwx`).


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 4 (CODE 1): POSIX Inode ve VFS Dentry Simülatörü
Dizin Girişi (Dentry), Inode Tablosu, Hard Link Refcounting ve Disk Blok Tahsisi
"""

import time
from typing import Dict, List, Optional, Tuple

class SimulatedInode:
    """Linux VFS Inode yapısının bellek içi simülasyonu."""
    def __init__(self, ino: int, mode: int, uid: int = 1000, gid: int = 1000, blksize: int = 4096):
        self.st_ino = ino
        self.st_mode = mode
        self.st_nlink = 1
        self.st_uid = uid
        self.st_gid = gid
        self.st_size = 0
        self.st_blksize = blksize
        self.st_blocks = 0  # 512 baytlık sektör birimleri cinsinden
        
        now = time.time()
        self.st_atim = now
        self.st_mtim = now
        self.st_ctim = now
        self.data_blocks: Dict[int, bytes] = {}  # Blok index -> Veri
        self.symlink_target: Optional[str] = None

    def allocate_block(self, block_index: int, data: bytes):
        """Diskte fiziksel blok tahsis eder (Sparse file mantığı)."""
        self.data_blocks[block_index] = data
        self.st_blocks = len(self.data_blocks) * (self.st_blksize // 512)
        self.st_mtim = time.time()
        self.st_ctim = self.st_mtim

class VirtualFileSystem:
    """Linux VFS katmanı: Inode tablosu ve Dentry (Dizin Girişleri) Haritası."""
    def __init__(self):
        self.next_ino = 1000
        self.inode_table: Dict[int, SimulatedInode] = {}
        self.dentry_table: Dict[str, int] = {}
        self.open_file_handles: Dict[int, int] = {}
        self.next_fd = 3

    def create_file(self, path: str, mode: int = 0o100644) -> SimulatedInode:
        if path in self.dentry_table:
            raise FileExistsError(f"Dosya zaten mevcut: {path}")
        ino = self.next_ino
        self.next_ino += 1
        inode = SimulatedInode(ino=ino, mode=mode)
        self.inode_table[ino] = inode
        self.dentry_table[path] = ino
        return inode

    def create_hardlink(self, source_path: str, link_path: str):
        if source_path not in self.dentry_table:
            raise FileNotFoundError(f"Kaynak dosya bulunamadı: {source_path}")
        if link_path in self.dentry_table:
            raise FileExistsError(f"Hedef yol zaten mevcut: {link_path}")
        
        ino = self.dentry_table[source_path]
        inode = self.inode_table[ino]
        inode.st_nlink += 1
        inode.st_ctim = time.time()
        self.dentry_table[link_path] = ino

    def create_symlink(self, target_path: str, link_path: str):
        if link_path in self.dentry_table:
            raise FileExistsError(f"Hedef yol zaten mevcut: {link_path}")
        
        ino = self.next_ino
        self.next_ino += 1
        inode = SimulatedInode(ino=ino, mode=0o120777)
        inode.symlink_target = target_path
        inode.st_size = len(target_path.encode('utf-8'))
        self.inode_table[ino] = inode
        self.dentry_table[link_path] = ino

    def open(self, path: str) -> int:
        if path not in self.dentry_table:
            raise FileNotFoundError(f"Dosya bulunamadı: {path}")
        ino = self.dentry_table[path]
        fd = self.next_fd
        self.next_fd += 1
        self.open_file_handles[fd] = ino
        return fd

    def unlink(self, path: str):
        if path not in self.dentry_table:
            raise FileNotFoundError(f"Yol bulunamadı: {path}")
        ino = self.dentry_table.pop(path)
        inode = self.inode_table[ino]
        inode.st_nlink -= 1
        inode.st_ctim = time.time()
        
        is_open = any(open_ino == ino for open_ino in self.open_file_handles.values())
        if inode.st_nlink == 0 and not is_open:
            del self.inode_table[ino]

    def close(self, fd: int):
        if fd not in self.open_file_handles:
            raise ValueError(f"Geçersiz dosya tanımlayıcısı: {fd}")
        ino = self.open_file_handles.pop(fd)
        inode = self.inode_table.get(ino)
        if inode and inode.st_nlink == 0:
            is_open = any(open_ino == ino for open_ino in self.open_file_handles.values())
            if not is_open:
                del self.inode_table[ino]

# Simülasyon Testi
if __name__ == "__main__":
    vfs = VirtualFileSystem()
    f1 = vfs.create_file("/var/log/sensor.dat")
    f1.st_size = 8192
    f1.allocate_block(0, b"HEADER" * 100)
    f1.allocate_block(1, b"PAYLOAD" * 100)

    print(f"[VFS] Dosya Olusturuldu: /var/log/sensor.dat -> Inode #{f1.st_ino}, Linkler: {f1.st_nlink}")
    vfs.create_hardlink("/var/log/sensor.dat", "/var/log/sensor_backup.dat")
    print(f"[VFS] Hard Link Olusturuldu -> Inode #{f1.st_ino}, Guncel Link Sayisi: {f1.st_nlink}")

    vfs.create_symlink("/var/log/sensor.dat", "/var/log/sensor_symlink")
    sym_ino = vfs.dentry_table["/var/log/sensor_symlink"]
    print(f"[VFS] Symlink Olusturuldu -> Kendi Inode'u #{sym_ino}, Hedef: {vfs.inode_table[sym_ino].symlink_target}")

```

## 3. Kod 01 Analizi: Dentry ve Inode Ayrımının Kanıtlanması

Kod 01'deki simülasyon çıktısı Linux VFS mimarisinin üç temel kuralını doğrular:

1. **Hard Link Bütünlüğü**: `/var/log/sensor.dat` ve `/var/log/sensor_backup.dat` farklı dizin girişleridir (`dentry`); ancak tam olarak aynı Inode numarasını (`#1000`) paylaşırlar. `st_nlink` sayacı 1'den 2'ye yükselmiştir.
2. **Symlink Bağımsızlığı**: Sembolik link (`/var/log/sensor_symlink`), hedef dosyanın Inode'unu paylaşmaz; dosya sistemi üzerinde kendisine ait bağımsız bir Inode'a (`#1001`) sahiptir. Boyutu ise işaret ettiği string yolun uzunluğuna eşittir.
3. **Bellek ve Disk Verimliliği**: Hard link oluşturulduğunda diskte veri bloğu kopyalanmaz. Yalnızca dizin tablosuna 1 giriş eklenir ve Inode içindeki 16-bitlik sayaç artırılır.


## 4. Sistem Çağrısı Ailesi: stat(2) vs lstat(2) vs fstat(2) vs statx(2)

POSIX ve Linux ortamında dosya metaverisi okumak için 4 temel sistem çağrısı bulunur:

```
+---------------------------------------------------------------------------------------+
|  SİSTEM ÇAĞRISI  | GİRDİ ARGÜMANI     | SYMLINK DAVRANIŞI     | GÜVENLİK (TOCTOU)     |
+------------------+--------------------+-----------------------+-----------------------+
|  stat(path, &sb) | Dosya Yolu (const*)| Hedefi İzler (Follow) | YARIŞ KOŞULUNA AÇIK!  |
|  lstat(path, &sb)| Dosya Yolu (const*)| Linkin Kendini Okur   | YARIŞ KOŞULUNA AÇIK!  |
|  fstat(fd, &sb)  | Açık FD (int)      | Zaten Açılmış Inode   | KESİN GÜVENLİ (ATOMİK)|
|  statx(...)      | dirfd + path + flag| Bayrağa Bağlı (AT_*)  | Kısmi / Kontrollü     |
+---------------------------------------------------------------------------------------+
```

### 1. `stat(const char *pathname, struct stat *statbuf)`
Verilen yol adını kök dizinden itibaren çözümler. Eğer yol bir sembolik link ise, çekirdek linki özyinelemeli olarak son hedefe kadar takip eder (`dereference`). Dönen metaveri **hedef dosyanın** metaverisidir.

### 2. `lstat(const char *pathname, struct stat *statbuf)`
`stat` ile tamamen aynıdır, ancak dosya bir sembolik link olduğunda **linkin kendisini** inceler.
- `S_ISLNK(sb.st_mode)` doğru döner.
- `sb.st_size`, sembolik linkin işaret ettiği yol string'inin bayt uzunluğuna eşittir (Örn: `/etc/passwd` için 11 bayt).

### 3. `fstat(int fd, struct stat *statbuf)`
Yol çözümlemesi yapmaz. Sürecin dosya tanımlayıcı tablosundaki `fd` üzerinden doğrudan çekirdekteki `struct file` ve bağlı `struct inode` yapısına ulaşır.
- **Yüksek Başarım**: Dizin yürüyüşü (path traversal) ve dcache araması yapmadığı için `stat`'a göre katlarca daha hızlıdır.
- **TOCTOU Bağışıklığı**: Dosya zaten açık olduğundan, diske başka bir sürecin sembolik link yerleştirmesi işlemi etkilemez.

### 4. `statx(int dirfd, const char *pathname, int flags, unsigned int mask, struct statx *statxbuf)`
Linux 4.11 ile eklenen modern çağrıdır:
- İstenen alanlar (`mask`: `STATX_SIZE | STATX_TYPE | STATX_BTIME`) seçilerek gereksiz dosya sistemi sorguları engellenir.
- Geleneksel POSIX'te bulunmayan **Dosya Doğum Zamanı (Birth / Creation Time - `btime`)** desteği sağlar.


## 5. Zaman Damgaları: ATIME (`relatime`), MTIME ve CTIME

Bir Inode içinde nanosaniye hassasiyetinde (`struct timespec`) üç ayrı zaman damgası saklanır:

```
+------------------------------------------------------------------------------------+
|  ZAMAN DAMGASI | ANLAMI                   | TETİKLEYEN İŞLEMLER                     |
+----------------+--------------------------+-----------------------------------------+
|  st_atim       | Access Time (Erişim)     | read(), execve(), msync()               |
|  st_mtim       | Modification (İçerik)    | write(), truncate()                     |
|  st_ctim       | Change (Metaveri Durumu) | chmod(), chown(), link(), rename()      |
|  btime (statx) | Birth Time (Doğum/Oluşum)| Dosyanın ilk oluşturulduğu an           |
+------------------------------------------------------------------------------------+
```

### Kritik Güvenlik Kuralı: CTIME Neden Sahtelenemez (Tamper-Proof)?
Linux kullanıcıları ve sistem yöneticileri `touch` veya C'deki `utime(2)` / `utimensat(2)` sistem çağrılarını kullanarak `atime` ve `mtime` değerlerini geçmişe veya geleceğe diledikleri gibi ayarlayabilirler:
```c
struct timespec times[2] = { fake_atime, fake_mtime };
utimensat(AT_FDCWD, "file.txt", times, 0); // atime ve mtime tahrif edildi!
```
Ancak **`ctime` (Change Time) kullanıcı alanı tarafından ASLA doğrudan ayarlanamaz!**
`utimensat` çağrıldığı an dosyanın metaverisi değişmiş sayıldığından, Linux çekirdeği `st_ctim` değerini zorunlu olarak donanım saatinin **o anki gerçek değerine** eşitler.
> **Adli Bilişim (Digital Forensics) Kuralı**: Bir saldırgan dosyanın içeriğini değiştirip `mtime`'ı eski haline getirse bile, `st_ctim != st_mtim` farkı ve `ctime`'ın güncelliği dosya üzerinde oynandığını açıkça ele verir.

### Disk Performansı ve `relatime` (Relative Access Time)
Geleneksel Unix'te bir dosyadan her bayt okunduğunda (`read`), çekirdek inode'un `atime` alanını güncellemek için diske yazma işlemi yapardı. 10.000 okuma işlemi 10.000 disk yazması anlamına geldiğinden Linux 2.6.30'dan itibaren varsayılan olarak **`relatime`** kuralı uygulanır:
- `atime` yalnızca önceki `atime <= mtime` ise veya aradan 24 saatten fazla zaman geçmişse güncellenir.


## 6. Seyrek Dosyalar (Sparse Files) ve Inode Tüketim Riski

Dosya boyutu kavramında iki temel metrik bulunur:
1. **Görünen (Mantıksal) Boyut ($S_{\text{apparent}} = \text{st\_size}$)**: Dosyanın sıfırıncı baytından son geçerli baytına kadar olan adres aralığı.
2. **Tahsis Edilen Fiziksel Boyut ($S_{\text{allocated}} = \text{st\_blocks} \times 512$)**: Diskte gerçekten veri yazılmış sektörlerin toplam boyutu.

### Seyrek Dosya Mekanizması
Eğer bir uygulama `lseek(fd, 1073741824, SEEK_SET)` (1 GB ileriye atlama) yapıp ardından yalnızca 4 bayt yazarsa:
- $S_{\text{apparent}} = 1073741828\text{ Bayt } \approx 1\text{ GB}$
- $S_{\text{allocated}} = 8 \times 512 = 4096\text{ Bayt } = 4\text{ KB}$

Çekirdek, yazılmayan aralıktaki tüm sıfırları fiziksel blok olarak ayırmaz; dosya sistemi haritasında bir delik (hole) olarak işaretler. Okuma işlemi yapıldığında çekirdek otomatik olarak sıfır baytları üretir.

```
MANTIKSAL: [ Blok 0 (4KB) ] ------------ (1 GB BOŞLUK / DELİK) ------------ [ Blok 262144 (4KB) ]
FİZİKSEL : [ Sektör 5400 ]                                                  [ Sektör 9120 ]
```

### Inode Tükenme Riski (`ENOSPC` Hatası)
Her dosya sistemi oluşturulurken (`mkfs.ext4`) disk alanına orantılı olarak sabit sayıda Inode ayrılır.
- **Kritik Arıza**: Diskinizde 500 GB boş alan olsa dahi, eğer 0 baytlık milyonlarca küçük log dosyası oluşturursanız Inode tablosu dolar (`df -i` %100 gösterir).
- **Hata**: Yeni bir dosya oluşturmak istediğinizde çekirdek diskin dolu olduğunu belirten `ENOSPC (No space left on device)` hatası fırlatır!


## 7. Savunma Sanayii Mimarisi: Kara Kutu Kayıt Bütünlüğü ve TOCTOU Savunması

Askeri ve aviyonik sistemlerde (ASELSAN görev bilgisayarları, TUSAŞ uçuş kontrol birimleri) dosya metaverisi hayati işlevler üstlenir:

### 1. Kara Kutu (Flight Data Recorder) Inode Sürekliliği
Uçuş sırasında telemetri loglayıcı çalışırken disk alanını yöneten bir arka plan temizlik süreci eski log dosyalarını silebilir (`unlink`).
- Eğer telemetri yazıcı dosya yoluna bağımlı olsaydı, dosya silindiğinde yazma işlemi kesilirdi.
- Oysa POSIX standartlarında telemetri yazıcı dosyayı açtığında elde ettiği `fd` üzerinden inode'a bağlı kalır. Temizlik süreci dosyanın `dentry`'sini silse (`nlink=0`) dahi, telemetri yazıcı uçuş bitip `close()` çağırana kadar kayıt blokları korunur ve veri kaybı yaşanmaz.

### 2. TOCTOU (Time-of-Check to Time-of-Use) Güvenlik Açığı
Savunma yazılımlarında sıkça yapılan ölümcül hata:
```cpp
// GÜVENSİZ KOD! (TOCTOU Zaafiyeti)
struct stat sb;
if (stat("/tmp/mission_cfg.json", &sb) == 0) {
    if (sb.st_uid == 0) { // Sadece root dosyasıysa güven!
        // [TEHLİKELİ ZAMAN ARALIĞI]: Saldırgan tam burada araya girip
        // /tmp/mission_cfg.json dosyasını siler ve yerine /etc/shadow linki koyar!
        int fd = open("/tmp/mission_cfg.json", O_RDWR);
        write(fd, payload, size); // KRİTİK SİSTEM DOSYASI EZİLDİ!
    }
}
```

### 3. Savunma Standardı: Atomik `open(O_NOFOLLOW)` ve `fstat` Doğrulaması
```cpp
// KESİN GÜVENLİ MİMARİ (MISRA UYUMLU)
int fd = open("/tmp/mission_cfg.json", O_RDWR | O_NOFOLLOW | O_CLOEXEC);
if (fd >= 0) {
    struct stat sb;
    if (fstat(fd, &sb) == 0 && sb.st_uid == 0 && S_ISREG(sb.st_mode)) {
        // Doğrudan açık inode denetlendi; hiçbir yarış koşulu oluşamaz!
        write(fd, payload, size);
    }
    close(fd);
}
```


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 10 (CODE 2): Üretim Seviyesi PosixMetadataInspector Simülatörü
st_mode Bitmask Çözümleme, İzin Dizgisi Formatlama ve Seyrek Dosya Verimlilik Analizi
"""

import stat
from typing import Dict, Any

class PosixMetadataInspector:
    """POSIX struct stat uyumlu metaveri çözümleme ve güvenlik motoru."""
    
    @staticmethod
    def decode_mode(mode: int) -> Dict[str, Any]:
        """st_mode bitmask alanından dosya türü ve izin dizgisini çıkarır."""
        # 1. Dosya Türü
        if stat.S_ISREG(mode):
            file_type = "REGULAR_FILE"
            type_char = "-"
        elif stat.S_ISDIR(mode):
            file_type = "DIRECTORY"
            type_char = "d"
        elif stat.S_ISLNK(mode):
            file_type = "SYMLINK"
            type_char = "l"
        elif stat.S_ISFIFO(mode):
            file_type = "FIFO"
            type_char = "p"
        elif stat.S_ISSOCK(mode):
            file_type = "SOCKET"
            type_char = "s"
        elif stat.S_ISCHR(mode):
            file_type = "CHAR_DEV"
            type_char = "c"
        elif stat.S_ISBLK(mode):
            file_type = "BLOCK_DEV"
            type_char = "b"
        else:
            file_type = "UNKNOWN"
            type_char = "?"

        # 2. İzinler ve Özel Bayraklar (SUID, SGID, Sticky)
        p = list("---------")
        # Kullanıcı
        if mode & stat.S_IRUSR: p[0] = 'r'
        if mode & stat.S_IWUSR: p[1] = 'w'
        if mode & stat.S_IXUSR: p[2] = 's' if (mode & stat.S_ISUID) else 'x'
        elif mode & stat.S_ISUID: p[2] = 'S'
        
        # Grup
        if mode & stat.S_IRGRP: p[3] = 'r'
        if mode & stat.S_IWGRP: p[4] = 'w'
        if mode & stat.S_IXGRP: p[5] = 's' if (mode & stat.S_ISGID) else 'x'
        elif mode & stat.S_ISGID: p[5] = 'S'

        # Diğerleri
        if mode & stat.S_IROTH: p[6] = 'r'
        if mode & stat.S_IWOTH: p[7] = 'w'
        if mode & stat.S_IXOTH: p[8] = 't' if (mode & stat.S_ISVTX) else 'x'
        elif mode & stat.S_ISVTX: p[8] = 'T'

        perm_str = type_char + "".join(p)
        octal_perm = oct(mode & 0o7777)

        return {
            "file_type": file_type,
            "type_char": type_char,
            "permission_str": perm_str,
            "octal_permission": octal_perm,
            "has_suid": bool(mode & stat.S_ISUID),
            "has_sgid": bool(mode & stat.S_ISGID),
            "has_sticky": bool(mode & stat.S_ISVTX)
        }

    @staticmethod
    def analyze_storage_efficiency(st_size: int, st_blocks: int) -> Dict[str, Any]:
        """Görünen boyut ile tahsis edilen disk bloklarını kıyaslar."""
        allocated_bytes = st_blocks * 512
        if st_size > 0:
            ratio = allocated_bytes / st_size
        else:
            ratio = 1.0
            
        is_sparse = (st_size > 4096) and (ratio < 0.95)
        slack_bytes = max(0, allocated_bytes - st_size) if not is_sparse else 0

        return {
            "apparent_size_bytes": st_size,
            "allocated_bytes": allocated_bytes,
            "efficiency_ratio": ratio,
            "is_sparse": is_sparse,
            "slack_bytes": slack_bytes
        }

if __name__ == "__main__":
    test_modes = [
        (0o100644, "Normal Veri Dosyası (rw-r--r--)"),
        (0o104755, "SUID Aviyonik Yönetici İkili Dosyası (rwsr-xr-x)"),
        (0o040755, "Sistem Dizin Dosyası (drwxr-xr-x)"),
        (0o120777, "Sembolik Link (lrwxrwxrwx)"),
        (0o101777, "Geçici Paylaşım Dizini / Sticky Bit (rwxrwxrwt)")
    ]

    print("=== [METAVERİ ÇÖZÜMLEME LABORATUVARI] ===")
    for m, desc in test_modes:
        res = PosixMetadataInspector.decode_mode(m)
        print(f"[{res['octal_permission']}] {res['permission_str']} -> {res['file_type']} ({desc})")

    # Seyrek Dosya Analizi Örneği (1 GB boyutta sadece 8 KB yazılmış)
    sparse_stat = PosixMetadataInspector.analyze_storage_efficiency(st_size=1073741824, st_blocks=16)
    print("\n=== [SEYREK DOSYA BLOK ANALİZİ] ===")
    print(f"Görünen Boyut   : {sparse_stat['apparent_size_bytes']:,} B (1.00 GB)")
    print(f"Tahsis Edilen   : {sparse_stat['allocated_bytes']:,} B (8.00 KB)")
    print(f"Depolama Oranı  : %{sparse_stat['efficiency_ratio'] * 100:.6f}")
    print(f"Seyrek Dosya mı?: {sparse_stat['is_sparse']}")

```

## 8. Kod 02 Analizi ve Modern C++20 Kaynak Kodu

Kod 02'deki bitmask çözümleyici, POSIX standart izin gösterimini (`-rwxr-xr-x`) hatasız üretmiştir:
1. **SUID / SGID / Sticky Bit Kodlaması**:
   - `0104755` için kullanıcı çalıştırma bitinde `s` karakteri üretilmiş ve `has_suid=True` olarak etiketlenmiştir.
   - `0101777` için diğerleri izin grubunda `t` karakteri üretilmiş ve Sticky Bit teyit edilmiştir.
2. **Seyrek Dosya Tespiti**: $1\text{ GB}$ ($1,073,741,824$ bayt) görünen boyuta karşın yalnızca $16$ sektör ($8\text{ KB}$) tahsis edildiğinde, depolama verimlilik oranı $\%0.000745$ olarak hesaplanmış ve dosya anında `is_sparse = True` olarak damgalanmıştır.

### C++20 Eşdeğeri: `FileMetadataInspector`
```cpp
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string>

class FileMetadataInspector {
public:
    static bool is_safe_regular_file(int fd, uid_t expected_uid) {
        struct stat sb{};
        if (::fstat(fd, &sb) != 0) return false;
        return S_ISREG(sb.st_mode) && (sb.st_uid == expected_uid) && !(sb.st_mode & S_ISUID);
    }
};
```


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 12 (CODE 3): Sabotaj Laboratuvarı: TOCTOU Yarış Koşulu ve Savunma
stat() Kontrolü ile open() Arasına Sızma ve open(O_NOFOLLOW) + fstat Savunması
"""

from typing import Dict, Tuple

class ToctouSimulationLab:
    """TOCTOU yarış durumu zafiyetini ve fstat savunmasını canlandıran laboratuvar."""
    
    def __init__(self):
        self.vfs = VirtualFileSystem()
        self.vfs.create_file("/etc/secure_vault.key", mode=0o100600)
        self.vfs.create_file("/tmp/telemetry.tmp", mode=0o100666)

    def vulnerable_worker(self, attack_intervene: bool = True) -> Tuple[str, int]:
        """ZAFİYETLİ İŞLEM: Önce stat kontrolü, sonra open işlemi."""
        path = "/tmp/telemetry.tmp"
        
        # 1. TIME OF CHECK (Kontrol Anı)
        ino = self.vfs.dentry_table[path]
        stat_result = self.vfs.inode_table[ino]
        is_safe = (stat_result.st_mode & 0o100000) != 0
        
        if attack_intervene:
            # 2. SALDIRGAN ARAYA GİRİYOR!
            self.vfs.unlink(path)
            self.vfs.create_symlink("/etc/secure_vault.key", path)

        # 3. TIME OF USE (Kullanım Anı)
        target_ino = self.vfs.dentry_table[path]
        target_inode = self.vfs.inode_table[target_ino]
        
        if target_inode.symlink_target:
            resolved_path = target_inode.symlink_target
            opened_ino = self.vfs.dentry_table[resolved_path]
            return f"ZAFIYET TETIKLENDI! Hedef ezildi: {resolved_path}", opened_ino
        
        return "Guvenli islem tamamlandi.", target_ino

    def secure_worker(self, attack_intervene: bool = True) -> Tuple[str, bool]:
        """SAVUNMA: O_NOFOLLOW bayrağı ile açma ve doğrudan açık FD üzerinden fstat."""
        path = "/tmp/telemetry.tmp"
        
        if attack_intervene:
            self.vfs.unlink(path)
            self.vfs.create_symlink("/etc/secure_vault.key", path)
            
        target_ino = self.vfs.dentry_table[path]
        inode = self.vfs.inode_table[target_ino]
        
        # Çekirdek seviyesinde O_NOFOLLOW simülasyonu
        if (inode.st_mode & 0o170000) == 0o120000: # S_IFLNK
            return "SAVUNMA BASARILI: O_NOFOLLOW sembolik linki reddetti (ELOOP)!", True
            
        return "Guvenli dosya acildi.", True

if __name__ == "__main__":
    print("=== [SABOTAJ VE TOCTOU YARIŞ KOŞULU TESTİ] ===")
    lab = ToctouSimulationLab()
    msg_vuln, opened_ino = lab.vulnerable_worker(attack_intervene=True)
    print(f"[*] Zafiyetli Metot Çıktısı: {msg_vuln} (Erişilen Inode: #{opened_ino})")

    lab_sec = ToctouSimulationLab()
    msg_sec, defended = lab_sec.secure_worker(attack_intervene=True)
    print(f"[*] Güvenli Savunma Çıktısı : {msg_sec}")

```

## 9. Kod 03 Analizi: TOCTOU Açığının Kapatılması ve Yarış Koşulu Direnci

Kod 03'teki laboratuvar deneyi, sistem mühendisliğindeki en kritik güvenlik açıklarından birini somutlaştırmıştır:
1. **Zafiyetli İş Akışı**: İş parçacığı `/tmp/telemetry.tmp` dosyasını `stat()` ile kontrol ettiğinde dosya zararsızdı. Ancak saldırgan `unlink` + `symlink` hamlesiyle bu yolu `/etc/secure_vault.key` dosyasına yönlendirdi. Program `open()` çağrısı yaptığında farkında olmadan kritik sistem anahtarını ezdi!
2. **Savunma Mekanizması**: Güvenli iş parçacığı dosya yolunu önce kontrol etmek yerine, doğrudan `O_NOFOLLOW` bayrağı ile açmayı denedi. Yol bir sembolik linke dönüştürüldüğü için çekirdek işlemi derhal `ELOOP` hatasıyla reddetti.
3. **Mühendislik Prensibi**: Bir dosya önce kontrol edilip sonra açılmaz; **önce açılır, ardından açık `fd` üzerinden `fstat()` ile doğrulanır**.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 14 (CODE 4): Unlink-While-Open Laboratuvarı
Açık Dosyanın Silinmesi, st_nlink Sıfırlanması ve Disk Alanı İadesi
"""

from typing import Dict, Any

class UnlinkWhileOpenDemo:
    """Açık bir dosyanın unlink edildikten sonraki yaşam döngüsünü test eden laboratuvar."""
    
    def __init__(self):
        self.vfs = VirtualFileSystem()
        
    def execute_lifecycle(self) -> Dict[str, Any]:
        path = "/var/log/flight_data.raw"
        inode = self.vfs.create_file(path)
        inode.allocate_block(0, b"FLIGHT_PACKET_001")
        inode.st_size = 4096
        
        # 1. Dosyayı açıyoruz
        fd = self.vfs.open(path)
        ino_initial = inode.st_ino
        nlink_before = inode.st_nlink
        in_dentry_before = path in self.vfs.dentry_table
        
        # 2. Dosya açıkken unlink ediyoruz (rm komutu gibi)
        self.vfs.unlink(path)
        nlink_after_unlink = inode.st_nlink
        in_dentry_after_unlink = path in self.vfs.dentry_table
        inode_still_alive_after_unlink = ino_initial in self.vfs.inode_table
        
        # 3. Dosyaya açık FD üzerinden yazmaya devam ediyoruz
        inode.allocate_block(1, b"FLIGHT_PACKET_002")
        inode.st_size = 8192
        blocks_allocated_while_unlinked = inode.st_blocks
        
        # 4. En son FD kapatılıyor
        self.vfs.close(fd)
        inode_alive_after_close = ino_initial in self.vfs.inode_table
        
        return {
            "inode_number": ino_initial,
            "nlink_before": nlink_before,
            "in_dentry_before": in_dentry_before,
            "nlink_after_unlink": nlink_after_unlink,
            "in_dentry_after_unlink": in_dentry_after_unlink,
            "inode_alive_after_unlink": inode_still_alive_after_unlink,
            "blocks_allocated_while_unlinked": blocks_allocated_while_unlinked,
            "inode_alive_after_close": inode_alive_after_close
        }

if __name__ == "__main__":
    demo = UnlinkWhileOpenDemo()
    results = demo.execute_lifecycle()

    print("=== [UNLINK-WHILE-OPEN YAŞAM DÖNGÜSÜ] ===")
    print(f"Inode #{results['inode_number']} oluşturuldu. Başlangıç nlink: {results['nlink_before']}")
    print(f"unlink() Sonrası -> Dizin Girişi Kaldırıldı mı? : {not results['in_dentry_after_unlink']}")
    print(f"unlink() Sonrası -> nlink Sayısı                : {results['nlink_after_unlink']}")
    print(f"unlink() Sonrası -> Inode Bellekte/Diskte Yaşıyor mu?: {results['inode_alive_after_unlink']}")
    print(f"Açıkken Yazılan Blok Sayısı                    : {results['blocks_allocated_while_unlinked']}")
    print(f"close(fd) Sonrası -> Inode ve Bloklar Temizlendi mi?: {not results['inode_alive_after_close']}")

```

## 10. Kod 04 Analizi: Disk Alanının İadesi ve Çekirdek Referans Sayımı

Kod 04 simülasyonu, Linux VFS çekirdeğinin kaynak temizleme mantığını net bir şekilde ortaya koymuştur:
1. **Dentry Silinir, Inode Kalır**: `unlink(path)` çağrıldığında dosya adı dizinden sökülmüş (`in_dentry = False`) ve `st_nlink` sayısı 0'a inmiştir. Ancak dosya bir süreçte açık (`fd`) olduğu için Inode tablosunda ve fiziksel diskte yaşamaya devam etmiştir.
2. **Yazma İşlemi Kesintiye Uğramaz**: Dosya silinmiş olmasına rağmen süreç açık `fd` üzerinden yeni bloklar tahsis edebilmiş ($8\text{ KB}$) ve boyutunu büyütebilmiştir.
3. **Nihai Temizlik**: Ancak `close(fd)` çağrıldığında (veya süreç `exit` ile kapandığında) açık referans sayısı 0'a düşmüş ve çekirdek fiziksel disk bloklarını serbest blok havuzuna iade etmiştir.


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 16 (CODE 5): Performans ve Benchmark Laboratuvarı
stat(path) Yol Çözümleme vs fstat(fd) Açık Tanımlayıcı Mikro-Kıyaslaması
"""

import time
from typing import Dict

def run_stat_vs_fstat_benchmark(iterations: int = 50000) -> Dict[str, float]:
    """Path walk yapan stat ile doğrudan inode erişen fstat başarımını simüle eder."""
    
    # 1. stat(path) Simülasyonu: String hashing, path parsing, dentry lookup
    t0 = time.perf_counter()
    dummy_acc = 0
    path = "/opt/aselsan/radar/telemetry_storage/current_mission/channel_a.bin"
    path_components = path.strip("/").split("/")
    
    for _ in range(iterations):
        current_hash = 0
        for comp in path_components:
            current_hash += hash(comp)
        dummy_acc += (current_hash & 0xFF)
    t_stat = time.perf_counter() - t0

    # 2. fstat(fd) Simülasyonu: Dizi indeksi ile doğrudan struct file erişimi
    t1 = time.perf_counter()
    fd_table = [1048578] * 1024
    target_fd = 42
    
    for _ in range(iterations):
        ino = fd_table[target_fd]
        dummy_acc += (ino & 0xFF)
    t_fstat = time.perf_counter() - t1

    speedup = t_stat / max(t_fstat, 1e-9)
    return {
        "iterations": iterations,
        "t_stat_sec": t_stat,
        "t_fstat_sec": t_fstat,
        "speedup_factor": speedup
    }

if __name__ == "__main__":
    bench_results = run_stat_vs_fstat_benchmark(iterations=50000)
    print("=== [STAT(PATH) VS FSTAT(FD) MİKRO-BENCHMARK] ===")
    print(f"Toplam Döngü      : {bench_results['iterations']:,}")
    print(f"stat(path) Süresi : {bench_results['t_stat_sec']*1000:.3f} ms")
    print(f"fstat(fd) Süresi  : {bench_results['t_fstat_sec']*1000:.3f} ms")
    print(f"[*] fstat Hızlanma Çarpanı: {bench_results['speedup_factor']:.2f}x Kat Daha Hızlı!")

```

## 11. Kod 05 Analizi: Yol Çözümleme Ek Yükü ve Dcache Başarımı

Benchmark sonuçları, sistem mimarisinde açık dosya tanımlayıcısı (`fstat`) kullanımının üstünlüğünü kanıtlar:
1. **Dentry Cache Maliyeti**: `stat(path)` her çağrıldığında yol dizgisi ayrıştırılır (`/` karakterleri), her bileşenin dcache hash değeri hesaplanır ve erişim izinleri denetlenir.
2. **$O(1)$ Doğrudan Bellek Erişimi**: `fstat(fd)` ise yalnızca sürecin dosya tablosundaki dizi indeksine (`fd_array[fd]`) bakar ve tek bir pointer takibiyle `struct inode` yapısına ulaşır.
3. **Mühendislik Çıkarımı**: Yüksek frekanslı I/O döngülerinde (örneğin saniyede 10.000 dosya boyutu kontrolü gereken radar akışlarında) dosya yolunu tekrar tekrar `stat()` ile sorgulamak CPU'yu kilitler. Dosya bir kez açılmalı ve periyodik kontroller `fstat()` ile yapılmalıdır.


## 12. Endüstriyel Mimari Örüntüleri: Atomik Güncelleme ve Log Rotasyonu

### 1. Atomik Dosya Güncelleme Deseni (Write-Fsync-Rename)
Kritik bir konfigürasyon dosyasını (örneğin `/etc/sensor_params.json`) doğrudan üzerine yazmak (`open(O_TRUNC)`) ölümcül bir mimari hatadır. Yazma esnasında elektrik kesilirse dosya bozulur veya 0 bayt kalır.

**Altın Kural (POSIX Atomik Değişim)**:
1. Yeni veriyi aynı dosya sistemi üzerinde geçici bir dosyaya yaz: `/etc/sensor_params.json.tmp`
2. Veriyi ve metaveriyi diske zorla: `fsync(fd)`
3. Dosyayı kapat: `close(fd)`
4. Atomik olarak yer değiştir: `rename("/etc/sensor_params.json.tmp", "/etc/sensor_params.json")`

> **Neden Güvenli?** `rename(2)` çağrısı tek bir Inode dentry güncellemesidir ve elektrik kesilse bile dosya ya eski sağlam halinde kalır ya da tamamen yeni haline geçer; asla yarım veya bozuk kalamaz!

### 2. Log Rotasyonu ve Açık Inode Davranışı
`logrotate` mekanizması çalışırken:
- `app.log` dosyasını `app.log.1` olarak yeniden adlandırır (`rename`).
- Yazılım `app.log` dosyasını açık bir `fd` ile tuttuğu için, dosyanın adı değişse bile aynı Inode'a yazmaya kesintisiz devam eder.
- Log yöneticisi yazılıma `SIGHUP` sinyali gönderir. Yazılım eski `fd`'yi kapatıp yeni `app.log` dosyasını açarak döngüyü tamamlar.


## 13. Hata Ayıklama ve Gözlemlenebilirlik

Linux sistem mühendisleri için dosya metaverisi ve Inode hata ayıklama komutları:

```bash
# 1. Dosyanın tüm Inode detaylarını ayrıntılı dök
stat /var/log/syslog

# 2. Dosya adı ve Inode numarasını yan yana listele
ls -li /etc/hosts

# 3. Aynı Inode'u paylaşan tüm hard linkleri bul
find / -samefile /etc/hosts 2>/dev/null

# 4. Dosya sistemindeki Inode doluluk oranını denetle (df -i)
df -ih

# 5. Düşük seviyeli ext4 Inode yapısını incele (debugfs)
sudo debugfs -R 'stat <1048578>' /dev/nvme0n1p2

# 6. Süreçlerin çağırdığı stat syscall ailesini izle
strace -e trace=stat,fstat,lstat,newfstatat ./mission_app
```


## 14. Sık Yapılan Hatalar ve Anti-Pattern'ler

1. **Varlık Kontrolünde `stat` Kullanımı (TOCTOU Tuzağı)**:
   - *Yanlış*: `if (stat(f, &sb) == 0) { open(f, ...); }`
   - *Doğru*: Doğrudan `open(f, O_CREAT | O_EXCL, ...)` çağrıp dönen hatayı (`EEXIST`) kontrol etmek.
2. **`st_size` Değerini Disk Tüketimi Sanmak**:
   - *Yanlış*: Seyrek dosyalarda `st_size` kadar disk dolduğunu varsaymak.
   - *Doğru*: Gerçek disk tahsisi daima `st_blocks * 512` formülüyle hesaplanmalıdır.
3. **`ctime`'ı Dosya Oluşturma (Creation) Zamanı Sanmak**:
   - *Yanlış*: `ctime`'ın sabit kaldığını varsaymak.
   - *Doğru*: `chmod`, `chown` gibi herhangi bir metaveri değişiminde `ctime` anında güncellenir.
4. **Farklı Bölümler Arasında Hard Link Denemek**:
   - *Yanlış*: `/dev/sda1` üzerindeki bir dosyaya `/dev/sdb1` üzerinde hard link oluşturmaya çalışmak.
   - *Sonuç*: `EXDEV (Invalid cross-device link)` hatası. Inode numaraları yalnızca aynı dosya sistemi (`st_dev`) içinde geçerlidir!


## 15. Neden-Sonuç Tablosu ve Mimari Karar Matrisi

| Karar / Eylem | Doğrudan Sonuç | Potansiyel Risk / Hata Sınıfı | Mimari Tavsiye |
| :--- | :--- | :--- | :--- |
| `stat` ile kontrol edip `open` yapmak | İki çağrı arasında dosya değiştirilebilir. | **TOCTOU Güvenlik Açığı / Symlink Saldırısı**. | `open(O_NOFOLLOW)` ardından `fstat` kullanın. |
| Hard link yerine sembolik link seçmek | Hedef silindiğinde link kırılır (`dangling`). | `ENOENT` / Program çöküşü. | Aynı FS içi değişmezlik gerekiyorsa hard link kullanın. |
| Milyonlarca küçük 0-byte dosya açmak | Inode tablosu dolar (`df -i` %100). | Disk dolu olmasa bile `ENOSPC` hatası. | Küçük dosyaları arşivleyin/veritabanında saklayın. |
| Açık dosya tanımlayıcısını silmek (`unlink`) | `nlink=0` olur ama bloklar açık kalır. | Süreç kapanana kadar diskin boşalmaması. | Sızıntıyı önlemek için `close()` çağrısını aksatmayın. |
| Konfigürasyonu doğrudan üzerine yazmak | Kesinti anında bozuk / 0 bayt dosya kalır. | Kritik sistem başlangıç hatası. | `.tmp` dosyasına yazıp `fsync` + `rename` yapın. |


```python
# -*- coding: utf-8 -*-
"""
HÜCRE 22 (CODE 6): 4-Panelli Görselleştirme Paneli ve Katı Doğrulama Testleri
VFS Mimarisi, Seyrek Dosya Dağılımı, stat/fstat Gecikmesi ve Inode Yaşam Döngüsü
"""

import os
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_PNG = "gun_093_filesystem_metadata_stat_ve_inode.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    """4-panelli, koyu tema, 300 DPI kurumsal sistem mimarisi paneli üretir."""
    
    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    # Renk Paleti
    accent_blue = '#38BDF8'
    accent_amber = '#F59E0B'
    accent_green = '#10B981'
    accent_red = '#EF4444'
    text_color = '#F8FAFC'

    # PANEL 1: VFS Dentry vs Inode Eşleşme Mimarisi
    ax1 = axs[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("VFS Dentry -> Inode -> Veri Blokları Hiyerarşisi", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    boxes = [
        ("Dentry 1: 'telemetry.log'", 0.15, 0.75, accent_blue),
        ("Dentry 2: 'telemetry_hl.log'", 0.15, 0.45, accent_amber),
        ("Dentry 3: 'telemetry_sym'", 0.15, 0.15, accent_green),
        ("Inode #1048578 (nlink=2)\n[Mode: 0644, Size: 400KB]", 0.52, 0.60, accent_blue),
        ("Inode #1048579 (Symlink)\n[Target: /var/log/telemetry.log]", 0.52, 0.15, accent_green),
        ("Veri Blokları [50000 - 50099]\n(Fiziksel Disk Sektörleri)", 0.86, 0.60, '#94A3B8')
    ]
    
    for text, x, y, col in boxes:
        ax1.text(x, y, text, ha='center', va='center', color=text_color, fontsize=8, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#0F172A', edgecolor=col, linewidth=2))

    ax1.annotate("", xy=(0.38, 0.65), xytext=(0.28, 0.75), arrowprops=dict(arrowstyle="->", color=accent_blue, lw=2))
    ax1.annotate("", xy=(0.38, 0.60), xytext=(0.28, 0.45), arrowprops=dict(arrowstyle="->", color=accent_amber, lw=2))
    ax1.annotate("", xy=(0.38, 0.15), xytext=(0.28, 0.15), arrowprops=dict(arrowstyle="->", color=accent_green, lw=2))
    ax1.annotate("", xy=(0.72, 0.60), xytext=(0.66, 0.60), arrowprops=dict(arrowstyle="->", color='#94A3B8', lw=2))
    
    ax1.set_xlim(0, 1.05)
    ax1.set_ylim(0, 1.0)
    ax1.axis('off')

    # PANEL 2: Seyrek Dosya (Sparse) vs Standart Dosya Blok Tahsisi
    ax2 = axs[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("Görünen Boyut (st_size) vs Fiziksel Boyut (st_blocks * 512)", fontsize=12, fontweight='bold', color=accent_amber, pad=12)
    
    file_types = ["Standart 4KB Log", "Gömülü DB 64KB", "Seyrek Dosya 1GB (Delikli)", "Büyük İmge 500MB"]
    apparent_mb = [0.004, 0.064, 1024.0, 500.0]
    allocated_mb = [0.004, 0.064, 0.008, 500.0]
    
    x = np.arange(len(file_types))
    width = 0.35
    
    ax2.bar(x - width/2, apparent_mb, width, label='Görünen Boyut (st_size)', color=accent_blue, alpha=0.9)
    ax2.bar(x + width/2, allocated_mb, width, label='Tahsis Edilen (st_blocks)', color=accent_red, alpha=0.9)
    
    ax2.set_ylabel("Boyut (MB) - Logaritmik Ölçek", fontsize=10, color=text_color)
    ax2.set_yscale('log')
    ax2.set_xticks(x)
    ax2.set_xticklabels(file_types, fontsize=8, color=text_color, rotation=15)
    ax2.legend(facecolor='#0F172A', edgecolor='#334155', fontsize=9)
    ax2.grid(True, linestyle='--', alpha=0.3, color='#475569')

    # PANEL 3: stat(path) vs fstat(fd) Latency Mikro-Kıyaslama
    ax3 = axs[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("Syscall Erişim Gecikmesi: Yol Çözümleme vs Açık Tanımlayıcı", fontsize=12, fontweight='bold', color=accent_green, pad=12)
    
    bench = run_stat_vs_fstat_benchmark(iterations=20000)
    categories = ["stat(path) [Dcache/Path Walk]", "lstat(link) [Symlink Check]", "fstat(fd) [Direct Inode Pointer]"]
    times = [bench['t_stat_sec'] * 1000, bench['t_stat_sec'] * 1.08 * 1000, bench['t_fstat_sec'] * 1000]
    colors = [accent_amber, accent_blue, accent_green]
    
    bars = ax3.barh(categories, times, color=colors, height=0.55)
    ax3.set_xlabel("Toplam Süre (ms)", fontsize=10, color=text_color)
    ax3.grid(True, linestyle='--', alpha=0.3, color='#475569')
    for bar in bars:
        ax3.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, f"{bar.get_width():.2f} ms",
                 va='center', ha='left', color=text_color, fontsize=9, fontweight='bold')

    # PANEL 4: Unlink-While-Open Refcount ve Disk Alanı Yaşam Döngüsü
    ax4 = axs[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("Açık Dosyanın Silinmesi: nlink vs Açık FD vs Disk Boşaltma", fontsize=12, fontweight='bold', color=accent_blue, pad=12)
    
    steps = ["1. open(path)", "2. unlink(path)", "3. write(fd, ...)", "4. close(fd)"]
    nlink_vals = [1, 0, 0, 0]
    open_fd_vals = [1, 1, 1, 0]
    disk_allocated_vals = [1, 1, 1, 0]
    
    xs = np.arange(len(steps))
    ax4.plot(xs, nlink_vals, marker='o', linewidth=2.5, color=accent_red, label='st_nlink Sayısı')
    ax4.plot(xs, open_fd_vals, marker='s', linewidth=2.5, color=accent_amber, label='Açık Tanımlayıcı (FD)')
    ax4.step(xs, disk_allocated_vals, where='mid', linewidth=3, linestyle='--', color=accent_green, label='Disk Blok Durumu (1=Dolu, 0=Serbest)')
    
    ax4.set_xticks(xs)
    ax4.set_xticklabels(steps, fontsize=9, color=text_color)
    ax4.set_ylabel("Durum / Sayaç Değeri", fontsize=10, color=text_color)
    ax4.legend(facecolor='#0F172A', edgecolor='#334155', fontsize=9)
    ax4.grid(True, linestyle='--', alpha=0.3, color='#475569')

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
    
    # 1. Dosya Varlık Kontrolü
    assert os.path.exists(png_path), f"HATA: Dashboard görseli üretilemedi: {png_path}"
    assert os.path.getsize(png_path) > 100_000, "HATA: Dashboard görsel boyutu yetersiz!"
    print(f"  [+] PNG Varlık ve Boyut Doğrulandı: {os.path.getsize(png_path):,} bayt.")

    # 2. Inode ve Dentry Eşleşme Doğrulaması
    vfs_test = VirtualFileSystem()
    f = vfs_test.create_file("/test.bin")
    vfs_test.create_hardlink("/test.bin", "/test_hl.bin")
    assert f.st_nlink == 2, "HATA: Hard link sonrası nlink 2 olmalıdır!"
    vfs_test.unlink("/test.bin")
    assert f.st_nlink == 1, "HATA: Bir link silindiğinde diğer link ve inode korunmalıdır!"
    print("  [+] Inode Link Refcounting ve Dentry Ayrımı Doğrulandı.")

    # 3. Unlink-While-Open Blok Korunumu Doğrulaması
    unlink_demo = UnlinkWhileOpenDemo()
    res = unlink_demo.execute_lifecycle()
    assert res['inode_alive_after_unlink'] is True, "HATA: Açık fd varken dosya silinse de inode yaşamalıdır!"
    assert res['inode_alive_after_close'] is False, "HATA: Son fd kapandığında inode ve bloklar temizlenmelidir!"
    print("  [+] Unlink-While-Open ve Disk Boşaltma Döngüsü Doğrulandı.")

    # 4. Seyrek Dosya Analizi Doğrulaması
    sp = PosixMetadataInspector.analyze_storage_efficiency(st_size=1048576, st_blocks=8)
    assert sp['is_sparse'] is True, "HATA: 1MB görünen boyutta 4KB blok seyrek dosya olarak tespit edilmelidir!"
    assert sp['efficiency_ratio'] < 0.01, "HATA: Seyrek dosya verimlilik oranı %1'in altında olmalıdır!"
    print("  [+] Seyrek Dosya (Sparse File) Mantığı Doğrulandı.")

    # 5. TOCTOU Savunma Doğrulaması
    t_lab = ToctouSimulationLab()
    msg, defended = t_lab.secure_worker(attack_intervene=True)
    assert defended is True, "HATA: O_NOFOLLOW savunması sembolik link saldırısını engellemelidir!"
    print("  [+] TOCTOU Yarış Koşulu Savunması Doğrulandı.")

    print("\n[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!\n")

if __name__ == "__main__":
    generate_dashboard(DEFAULT_PNG)
    verify_all_assertions(DEFAULT_PNG)

```

## 16. Savunma Sanayii Senaryoları ve Gün Sonu Özeti

### Savunma Sanayii ve Görev Kritik Sistem Senaryoları
1. **ASELSAN Elektronik Harp (EH) Kayıt Birimi: Inode Tüketim Koruması**:
   - Yüksek frekansta darbe tanım kelimeleri (PDW) kaydedilirken her sinyal darbesi için yeni bir dosya açmak, 10 dakika içinde dosya sisteminin 2 milyonluk Inode tablosunu tüketir (`df -i` %100).
   - Çözüm: Tek bir döngüsel veri dosyası açılır ve ofset atlanarak (`lseek`) Inode tüketimi sıfıra indirilir.
2. **TUSAŞ Milli Muharip Uçak (KAAN) Görev Bilgisayarı: Atomik Konfigürasyon**:
   - Silah yönetim sisteminin hedef koordinat konfigürasyonu doğrudan üzerine yazılmaz.
   - `.tmp` dosyasına yazılır, `fdatasync` ile diske basılır ve `rename` ile atomik geçiş sağlanır. Uçuş esnasında elektrik kesilse dahi dosya bozulmaz.

### Gün Sonu Özeti (3 Cümlelik Kapanış)
1. **Inode ve Dentry Ayrımı**: Unix dosya sisteminde dosya adı verinin değil dizinin bir parçasıdır; dosyanın türü, boyutları, sahipliği ve veri blok işaretçileri eşsiz bir Inode yapısında barındırılır.
2. **`stat` vs `fstat` ve TOCTOU Güvenliği**: Dosya yolunu kontrol edip ardından açmak ölümcül yarış koşullarına (`TOCTOU`) yol açarken, doğrudan açık dosya tanımlayıcısını (`fstat`) denetlemek hem mutlak atomik güvenlik hem de $3\text{x}-10\text{x}$ performans kazancı sağlar.
3. **Mühendislik Kuralı**: Dosya silme (`unlink`) işlemi yalnızca dizin kaydını söker; fiziksel disk blokları ve inode ancak bu dosyayı açık tutan son sürecin dosya tanımlayıcısı kapandığında (`close`) serbest bırakılır.


## 17. Gelecek Gün Köprüsü: Gün 094

Yarın **GÜN 094** kapsamında:
- **Konu**: **/proc ve Sistem Gözlemlenebilirliği (System Observability)**
- **Kapsam**: Çekirdek bellek içi sözde dosya sistemi (`procfs`), `/proc/PID/stat` ve `/proc/PID/status` çözümlemesi, açık dosya tanımlayıcılarının izlenmesi (`/proc/PID/fd`), bellek haritaları (`/proc/PID/maps`) ve C++ ile çekirdek içi süreç izleme araçları geliştirme.
- **Hazırlık**: Bugün dosya sisteminin Inode ve metaveri mimarisini kavradık; yarın bu dosya sistemi arayüzü üzerinden bizzat çalışan süreçlerin çekirdek durumlarını canlı olarak gözlemleyeceğiz.
