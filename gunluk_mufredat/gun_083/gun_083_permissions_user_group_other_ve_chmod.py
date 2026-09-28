# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
"""

# GÜN 083: Linux Dosya İzinleri, DAC & chmod Master Script

# Modül 1: Temel Çekirdek Mekanizma / POSIX DAC İzin Doğrulayıcı ve chmod Motoru
import stat
from typing import Dict, List, Tuple, Optional

# POSIX st_mode İzin Sabitleri
S_ISUID = 0o4000  # Set User ID
S_ISGID = 0o2000  # Set Group ID
S_ISVTX = 0o1000  # Sticky Bit (Save text image)

S_IRUSR = 0o0400  # Read by owner
S_IWUSR = 0o0200  # Write by owner
S_IXUSR = 0o0100  # Execute by owner

S_IRGRP = 0o0040  # Read by group
S_IWGRP = 0o0020  # Write by group
S_IXGRP = 0o0010  # Execute by group

S_IROTH = 0o0004  # Read by others
S_IWOTH = 0o0002  # Write by others
S_IXOTH = 0o0001  # Execute by others

# Erişim İstek Maskeleri
WANT_READ    = 4
WANT_WRITE   = 2
WANT_EXECUTE = 1

class ProcessCredentials:
    """Linux çekirdeğindeki struct cred yapısının temsili."""
    def __init__(self, uid: int, gid: int, euid: int, egid: int, 
                 fsuid: int, fsgid: int, groups: Optional[List[int]] = None):
        self.uid = uid
        self.gid = gid
        self.euid = euid
        self.egid = egid
        self.fsuid = fsuid
        self.fsgid = fsgid
        self.groups = groups if groups is not None else [gid]

class InodeEntry:
    """Linux çekirdeğindeki struct inode yapısının temsili."""
    def __init__(self, inode_num: int, name: str, uid: int, gid: int, mode: int, is_dir: bool = False):
        self.inode_num = inode_num
        self.name = name
        self.uid = uid
        self.gid = gid
        self.mode = mode
        self.is_dir = is_dir
        self.data = b""

    @property
    def permissions_str(self) -> str:
        """ls -l formatında izin katarı üretir (örn: -rwxr-xr-x)."""
        prefix = 'd' if self.is_dir else '-'
        
        # User
        ur = 'r' if (self.mode & S_IRUSR) else '-'
        uw = 'w' if (self.mode & S_IWUSR) else '-'
        if self.mode & S_ISUID:
            ux = 's' if (self.mode & S_IXUSR) else 'S'
        else:
            ux = 'x' if (self.mode & S_IXUSR) else '-'
            
        # Group
        gr = 'r' if (self.mode & S_IRGRP) else '-'
        gw = 'w' if (self.mode & S_IWGRP) else '-'
        if self.mode & S_ISGID:
            gx = 's' if (self.mode & S_IXGRP) else 'S'
        else:
            gx = 'x' if (self.mode & S_IXGRP) else '-'
            
        # Other
        otr = 'r' if (self.mode & S_IROTH) else '-'
        ow = 'w' if (self.mode & S_IWOTH) else '-'
        if self.mode & S_ISVTX:
            ox = 't' if (self.mode & S_IXOTH) else 'T'
        else:
            ox = 'x' if (self.mode & S_IXOTH) else '-'
            
        return f"{prefix}{ur}{uw}{ux}{gr}{gw}{gx}{otr}{ow}{ox}"

def posix_generic_permission(inode: InodeEntry, cred: ProcessCredentials, want_mask: int) -> Tuple[bool, str]:
    """
    Linux çekirdeği generic_permission (fs/namei.c) mantığını birebir işletir.
    Geri döner: (izin_verildi_mi, neden_kodu)
    """
    # 1. Root Kontrolü (CAP_DAC_OVERRIDE & CAP_DAC_READ_SEARCH)
    if cred.fsuid == 0:
        # Root her şeyi okuyabilir ve yazabilir
        if want_mask & WANT_EXECUTE:
            # Çalıştırma için dosyada en az bir 'x' biti olmalıdır
            has_any_x = bool(inode.mode & (S_IXUSR | S_IXGRP | S_IXOTH))
            if not has_any_x and not inode.is_dir:
                return False, "EACCES: Root dahi olsa dosyada hiçbir 'x' biti tanımlı değil"
        return True, "SUCCESS: Root (UID 0) ayrıcalığı onaylandı"

    # 2. Dosya Sahibi (Owner) Kontrolü
    if cred.fsuid == inode.uid:
        mode_shifted = (inode.mode >> 6) & 7
        if (mode_shifted & want_mask) == want_mask:
            return True, "SUCCESS: Dosya Sahibi (Owner) izni eşleşti"
        return False, "EACCES: Dosya Sahibi (Owner) talep edilen izne sahip değil (First Match Kuralı)"

    # 3. Grup Kontrolü
    if cred.fsgid == inode.gid or inode.gid in cred.groups:
        mode_shifted = (inode.mode >> 3) & 7
        if (mode_shifted & want_mask) == want_mask:
            return True, "SUCCESS: Grup (Group) izni eşleşti"
        return False, "EACCES: Grup (Group) talep edilen izne sahip değil"

    # 4. Diğerleri (Other) Kontrolü
    mode_shifted = inode.mode & 7
    if (mode_shifted & want_mask) == want_mask:
        return True, "SUCCESS: Diğerleri (Other) izni eşleşti"
    return False, "EACCES: Diğerleri (Other) için izin tanımlı değil"

def sys_chmod(inode: InodeEntry, cred: ProcessCredentials, new_mode: int) -> Tuple[bool, str]:
    """POSIX chmod(2) sistem çağrısı simülasyonu."""
    # Sadece root veya dosya sahibi chmod yapabilir
    if cred.fsuid != 0 and cred.fsuid != inode.uid:
        return False, "EPERM: chmod yalnızca dosya sahibi veya root tarafından çağrılabilir"
    
    # Dosya tipi bitlerini koru (örn: S_IFREG, S_IFDIR), sadece izin ve özel bitleri güncelle
    type_bits = inode.mode & 0o170000
    perm_bits = new_mode & 0o7777
    inode.mode = type_bits | perm_bits
    return True, f"SUCCESS: İzinler {oct(perm_bits)} olarak güncellendi ({inode.permissions_str})"

# Minimal Doğrulama
_sample_inode = InodeEntry(101, "radar_ctrl", uid=1000, gid=1000, mode=0o100750)
_cred_owner = ProcessCredentials(1000, 1000, 1000, 1000, 1000, 1000)
_cred_other = ProcessCredentials(2000, 2000, 2000, 2000, 2000, 2000)

_ok1, _ = posix_generic_permission(_sample_inode, _cred_owner, WANT_READ | WANT_WRITE | WANT_EXECUTE)
_ok2, _ = posix_generic_permission(_sample_inode, _cred_other, WANT_READ)
assert _ok1 == True, "Owner 0750 dosyada rwx yapabilmeli"
assert _ok2 == False, "Other 0750 dosyada read yapamamalı"
print("[Modül 1] POSIX DAC İzin Doğrulayıcı Başarıyla Hazırlandı.")


# Modül 2: umask Maskeleme, SUID/SGID Efektif Kimlik Geçişi ve Sticky Bit Motoru

class LinuxFileSystemVFS:
    """Linux VFS dosya ve dizin oluşturma, umask ve izin yönetim motoru."""
    def __init__(self, default_umask: int = 0o022):
        self.inodes: Dict[int, InodeEntry] = {}
        self.next_ino = 1000
        self.default_umask = default_umask

    def sys_umask(self, new_mask: int) -> int:
        """umask(2) sistem çağrısı: Eski maskeyi döner, yenisini ayarlar."""
        old = self.default_umask
        self.default_umask = new_mask & 0o777
        return old

    def sys_creat(self, name: str, cred: ProcessCredentials, mode: int, 
                  parent_dir: Optional[InodeEntry] = None) -> InodeEntry:
        """
        open(..., O_CREAT, mode) simülasyonu.
        Efektif mod = mode & ~umask
        """
        # umask uygula
        effective_mode = mode & (~self.default_umask)
        
        # Dosya sahibi fsuid, grubu ise fsgid'dir
        file_uid = cred.fsuid
        file_gid = cred.fsgid

        # Üst dizinde SGID varsa, dosya grubunu üst dizinden miras al
        if parent_dir and (parent_dir.mode & S_ISGID):
            file_gid = parent_dir.gid

        ino = self.next_ino
        self.next_ino += 1
        entry = InodeEntry(ino, name, file_uid, file_gid, 0o100000 | effective_mode, is_dir=False)
        self.inodes[ino] = entry
        return entry

    def sys_mkdir(self, name: str, cred: ProcessCredentials, mode: int,
                  parent_dir: Optional[InodeEntry] = None) -> InodeEntry:
        """mkdir(2) simülasyonu."""
        effective_mode = mode & (~self.default_umask)
        dir_uid = cred.fsuid
        dir_gid = cred.fsgid
        
        # Üst dizinden SGID mirası
        inherit_sgid = 0
        if parent_dir and (parent_dir.mode & S_ISGID):
            dir_gid = parent_dir.gid
            inherit_sgid = S_ISGID

        ino = self.next_ino
        self.next_ino += 1
        entry = InodeEntry(ino, name, dir_uid, dir_gid, 0o040000 | inherit_sgid | effective_mode, is_dir=True)
        self.inodes[ino] = entry
        return entry

    def sys_unlink(self, parent_dir: InodeEntry, target: InodeEntry, cred: ProcessCredentials) -> Tuple[bool, str]:
        """
        unlink(2) / rm simülasyonu: Sticky Bit (S_ISVTX) kontrolü!
        """
        # 1. Dizin yazma/yürütme izni var mı?
        ok, why = posix_generic_permission(parent_dir, cred, WANT_WRITE | WANT_EXECUTE)
        if not ok:
            return False, f"EACCES: Üst dizinde yazma/arama izni yok ({why})"

        # 2. Sticky Bit Kontrolü
        if parent_dir.mode & S_ISVTX:
            # Sadece root, dizin sahibi veya dosya sahibi silebilir
            is_root = (cred.fsuid == 0)
            is_file_owner = (cred.fsuid == target.uid)
            is_dir_owner = (cred.fsuid == parent_dir.uid)
            
            if not (is_root or is_file_owner or is_dir_owner):
                return False, "EPERM: Sticky Bit devrede! Yalnızca dosya sahibi veya root silebilir."

        if target.inode_num in self.inodes:
            del self.inodes[target.inode_num]
        return True, "SUCCESS: Dosya güvenli şekilde silindi."

    def execve_transition(self, binary: InodeEntry, caller_cred: ProcessCredentials) -> ProcessCredentials:
        """
        execve(2) çağrısında SUID / SGID bitlerine göre efektif kimlik dönüşümü.
        """
        new_euid = caller_cred.euid
        new_egid = caller_cred.egid
        new_fsuid = caller_cred.fsuid
        new_fsgid = caller_cred.fsgid

        # SUID Geçişi
        if binary.mode & S_ISUID:
            new_euid = binary.uid
            new_fsuid = binary.uid

        # SGID Geçişi
        if binary.mode & S_ISGID:
            new_egid = binary.gid
            new_fsgid = binary.gid

        return ProcessCredentials(
            uid=caller_cred.uid,
            gid=caller_cred.gid,
            euid=new_euid,
            egid=new_egid,
            fsuid=new_fsuid,
            fsgid=new_fsgid,
            groups=list(caller_cred.groups)
        )

# Modül 2 Test
_vfs = LinuxFileSystemVFS(default_umask=0o027) # Askeri güvenli umask
_cred_pilot = ProcessCredentials(1001, 1001, 1001, 1001, 1001, 1001)
_new_doc = _vfs.sys_creat("flight_plan.dat", _cred_pilot, 0o666)

# 0666 & ~0027 = 0640 (rw-r-----)
assert (_new_doc.mode & 0o777) == 0o640, f"Beklenen 0640, Gerçekleşen {oct(_new_doc.mode & 0o777)}"
print(f"[Modül 2] umask 0027 ile yaratılan dosya izni: {oct(_new_doc.mode & 0o777)} ({_new_doc.permissions_str})")


# Modül 3: Dizin Gezinme (Path Traversal) ve İzin Sınır Durumları Boru Hattı

class DirectoryTraversalEngine:
    """Linux VFS Path Lookup (namei) adımlarını simüle eden gezinme motoru."""
    def __init__(self, vfs: LinuxFileSystemVFS):
        self.vfs = vfs

    def resolve_path_and_access(self, path_components: List[InodeEntry], target_file: InodeEntry,
                                cred: ProcessCredentials, want_mask: int) -> Tuple[bool, str]:
        """
        Bir dosya açılırken yol üzerindeki tüm dizinlerde WANT_EXECUTE izni aranır.
        En son hedef dosyada ise want_mask doğrulanır.
        """
        # 1. Yol üzerindeki tüm ara dizinlerin 'x' (arama) izinlerini denetle
        for idx, directory in enumerate(path_components):
            if not directory.is_dir:
                return False, f"ENOTDIR: Bileşen {directory.name} bir dizin değil"
            
            ok, why = posix_generic_permission(directory, cred, WANT_EXECUTE)
            if not ok:
                return False, f"EACCES: Yol üzerindeki '{directory.name}' dizininde arama (x) izni yok! ({why})"

        # 2. Hedef dosyanın kendi izinlerini denetle
        ok, why = posix_generic_permission(target_file, cred, want_mask)
        if not ok:
            return False, f"EACCES: Hedef dosyada '{target_file.name}' erişim izni yok! ({why})"

        return True, "SUCCESS: Dosyaya başarıyla erişildi"

# Modül 3 Test: x biti olmayan dizin senaryosu
_vfs_m3 = LinuxFileSystemVFS(default_umask=0o022)
_root_cred = ProcessCredentials(0, 0, 0, 0, 0, 0)
_user_cred = ProcessCredentials(1005, 1005, 1005, 1005, 1005, 1005)

_dir_locked = InodeEntry(200, "locked_dir", uid=0, gid=0, mode=0o040744, is_dir=True) # r--r--r-- (x YOK!)
_file_inside = InodeEntry(201, "secret.txt", uid=1005, gid=1005, mode=0o100777, is_dir=False) # Dosya 0777!

_engine = DirectoryTraversalEngine(_vfs_m3)
_res_user, _msg_user = _engine.resolve_path_and_access([_dir_locked], _file_inside, _user_cred, WANT_READ)
assert _res_user == False, "Dizinde 'x' yoksa dosya 0777 olsa bile erişilememeli!"
print(f"[Modül 3] Sınır Testi Başarılı: {_msg_user}")


# Modül 4: Sabotaj Senaryosu — 0777 Zehirleme & SUID Yetki Yükseltme vs Dayanıklı Savunma

class SecuritySabotageSimulation:
    """Savunma sanayii izin sabotajlarını ve hardening savunmalarını simüle eder."""
    def __init__(self):
        self.vfs = LinuxFileSystemVFS(default_umask=0o022)
        self.attack_events = []
        self.defense_events = []

    def run_unprotected_sabotage(self) -> Dict[str, any]:
        """Korumasız sistem: 0777 izinli kritik dosya ve denetimsiz SUID binary."""
        # 1. Kritik Güdüm Dosyası 0777 olarak açılıyor
        guidance_file = InodeEntry(301, "guidance.conf", uid=0, gid=0, mode=0o100777)
        guidance_file.data = b"TARGET_COORD=39.9255,32.8662"
        
        # 2. Saldırgan (Düşük Yetkili Misafir Kullanıcı)
        attacker = ProcessCredentials(uid=9999, gid=9999, euid=9999, egid=9999, fsuid=9999, fsgid=9999)
        
        # Saldırgan dosyaya yazabiliyor mu?
        can_write, _ = posix_generic_permission(guidance_file, attacker, WANT_WRITE)
        poisoned = False
        if can_write:
            guidance_file.data = b"TARGET_COORD=0.0000,0.0000;ABORT_MISSION"
            poisoned = True
            self.attack_events.append("POISON_SUCCESS: 0777 dosyaya sahte koordinat yazıldı!")

        # 3. Denetimsiz SUID Binary İstismarı
        suid_tool = InodeEntry(302, "diag_tool", uid=0, gid=0, mode=0o104755) # SUID root!
        hijacked_cred = self.vfs.execve_transition(suid_tool, attacker)
        priv_escalated = (hijacked_cred.fsuid == 0)
        if priv_escalated:
            self.attack_events.append("PRIV_ESC_SUCCESS: SUID ile root yetkisi gasbedildi!")

        return {
            "poisoned": poisoned,
            "priv_escalated": priv_escalated,
            "final_data": guidance_file.data.decode()
        }

    def run_hardened_defense(self) -> Dict[str, any]:
        """Sertleştirilmiş Savunma: umask 0077, 0640 izinleri ve nosuid mount bayrağı."""
        # 1. Askeri İzin: 0640, Sahip: root (0), Grup: guidance_ops (100)
        guidance_file = InodeEntry(401, "guidance.conf", uid=0, gid=100, mode=0o100640)
        guidance_file.data = b"TARGET_COORD=39.9255,32.8662"
        
        # 2. Saldırgan
        attacker = ProcessCredentials(uid=9999, gid=9999, euid=9999, egid=9999, fsuid=9999, fsgid=9999)
        
        can_write, reason = posix_generic_permission(guidance_file, attacker, WANT_WRITE)
        poisoned = False
        if not can_write:
            self.defense_events.append(f"POISON_BLOCKED: {reason}")
        else:
            guidance_file.data = b"POISONED"
            poisoned = True

        # 3. nosuid Mount Koruması Simülasyonu
        suid_tool = InodeEntry(402, "diag_tool", uid=0, gid=0, mode=0o104755)
        # Sistem nosuid ile mount edildiğinde çekirdek S_ISUID bitini göz ardı eder
        mount_has_nosuid = True
        if mount_has_nosuid:
            # SUID biti maskelenir
            effective_mode = suid_tool.mode & ~S_ISUID
            suid_tool_safe = InodeEntry(402, "diag_tool", uid=0, gid=0, mode=effective_mode)
            hijacked_cred = self.vfs.execve_transition(suid_tool_safe, attacker)
        else:
            hijacked_cred = self.vfs.execve_transition(suid_tool, attacker)

        priv_escalated = (hijacked_cred.fsuid == 0)
        if not priv_escalated:
            self.defense_events.append("PRIV_ESC_BLOCKED: nosuid mount bayrağı SUID geçişini engelledi!")

        return {
            "poisoned": poisoned,
            "priv_escalated": priv_escalated,
            "final_data": guidance_file.data.decode()
        }

# Sabotaj ve Savunmayı Çalıştır
_sim = SecuritySabotageSimulation()
_res_unprotected = _sim.run_unprotected_sabotage()
_res_hardened = _sim.run_hardened_defense()

assert _res_unprotected["poisoned"] == True, "Korumasız sistem zehirlenmeli"
assert _res_unprotected["priv_escalated"] == True, "Korumasız sistemde yetki yükseltilmeli"
assert _res_hardened["poisoned"] == False, "Sertleştirilmiş sistemde zehirleme engellenmeli"
assert _res_hardened["priv_escalated"] == False, "nosuid ile yetki yükseltme engellenmeli"
print(f"[Sabotaj Testi] Korumasız: {_res_unprotected}")
print(f"[Savunma Testi] Sertleştirilmiş: {_res_hardened}")


# Modül 5: Ampirik Kıyaslama ve Yüksek Çözünürlüklü İzin Doğrulama Benchmark Motoru
import time
import numpy as np

def run_benchmarks(iterations: int = 10000) -> Dict[str, any]:
    """DAC doğrulama hızlarını ve gecikme yüzdeliklerini ampirik olarak ölçer."""
    vfs = LinuxFileSystemVFS(default_umask=0o027)
    
    inode_test = InodeEntry(500, "telemetry.bin", uid=1000, gid=1000, mode=0o100750)
    
    cred_root = ProcessCredentials(0, 0, 0, 0, 0, 0)
    cred_owner = ProcessCredentials(1000, 1000, 1000, 1000, 1000, 1000)
    cred_group = ProcessCredentials(2000, 1000, 2000, 1000, 2000, 1000)
    cred_other = ProcessCredentials(3000, 3000, 3000, 3000, 3000, 3000)

    latencies_root = []
    latencies_owner = []
    latencies_group = []
    latencies_other = []

    # Benchmark Döngüsü
    for _ in range(iterations):
        # 1. Root
        t0 = time.perf_counter_ns()
        posix_generic_permission(inode_test, cred_root, WANT_READ)
        t1 = time.perf_counter_ns()
        latencies_root.append(t1 - t0)

        # 2. Owner
        t0 = time.perf_counter_ns()
        posix_generic_permission(inode_test, cred_owner, WANT_READ | WANT_WRITE)
        t1 = time.perf_counter_ns()
        latencies_owner.append(t1 - t0)

        # 3. Group
        t0 = time.perf_counter_ns()
        posix_generic_permission(inode_test, cred_group, WANT_READ | WANT_EXECUTE)
        t1 = time.perf_counter_ns()
        latencies_group.append(t1 - t0)

        # 4. Other
        t0 = time.perf_counter_ns()
        posix_generic_permission(inode_test, cred_other, WANT_READ)
        t1 = time.perf_counter_ns()
        latencies_other.append(t1 - t0)

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
        "root": calc_stats(latencies_root),
        "owner": calc_stats(latencies_owner),
        "group": calc_stats(latencies_group),
        "other": calc_stats(latencies_other),
        "iterations": iterations
    }

_bench_res = run_benchmarks(iterations=5000)
print(f"[Benchmark] {_bench_res['iterations']} İterasyon Tamamlandı.")
print(f"  Root Mean:  {_bench_res['root']['mean']:.2f} ns (p95: {_bench_res['root']['p95']:.2f} ns)")
print(f"  Owner Mean: {_bench_res['owner']['mean']:.2f} ns (p95: {_bench_res['owner']['p95']:.2f} ns)")
print(f"  Other Mean: {_bench_res['other']['mean']:.2f} ns (p95: {_bench_res['other']['p95']:.2f} ns)")


# Modül 6: 4-Panelli Yayın Kalitesinde Dashboard Üretimi ve Katı Assert Doğrulaması
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DEFAULT_PNG = "gun_083_permissions_user_group_other_ve_chmod.png"

def generate_dashboard(output_png_path: str = DEFAULT_PNG):
    """Yayın kalitesinde 4-panelli görselleştirme paneli üretir."""
    fig, axs = plt.subplots(2, 2, figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor('#0F172A')

    bench_data = run_benchmarks(iterations=3000)

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
    # PANEL 1: DAC Doğrulama Gecikme Dağılımı (Boxplot)
    # -------------------------------------------------------------
    ax1 = axs[0, 0]
    style_ax(ax1, "Panel 1: VFS generic_permission() Çekirdek Gecikmesi", 
             "Erişim Rolü", "Gecikme (Nanisaniye - ns)")
    
    roles = ['Root', 'Owner', 'Group', 'Other']
    data_to_plot = [
        bench_data['root']['raw'][:1000],
        bench_data['owner']['raw'][:1000],
        bench_data['group']['raw'][:1000],
        bench_data['other']['raw'][:1000]
    ]
    
    bp = ax1.boxplot(data_to_plot, patch_artist=True, showmeans=True,
                     boxprops=dict(facecolor='#0284C7', color='#38BDF8'),
                     capprops=dict(color='#94A3B8'),
                     whiskerprops=dict(color='#64748B'),
                     flierprops=dict(marker='o', markerfacecolor='#F43F5E', markersize=3, alpha=0.5),
                     medianprops=dict(color='#F59E0B', linewidth=2),
                     meanprops=dict(marker='^', markerfacecolor='#10B981', markeredgecolor='#10B981'))
    
    ax1.set_xticks(range(1, 5))
    ax1.set_xticklabels(roles, fontweight='bold')
    
    means = [bench_data[r.lower()]['mean'] for r in roles]
    for i, m in enumerate(means, 1):
        ax1.text(i, m + 2, f"Ort: {m:.1f}ns", ha='center', color='#38BDF8', fontsize=8, fontweight='bold')

    # -------------------------------------------------------------
    # PANEL 2: Inode 16-Bit st_mode Oktal Ağırlıkları
    # -------------------------------------------------------------
    ax2 = axs[0, 1]
    style_ax(ax2, "Panel 2: Inode st_mode 16-Bit Alanı ve İzin Ağırlıkları", 
             "İzin / Bayrak Kategorisi", "Oktal Sayısal Değer")
    
    bit_names = ['Sticky\n(01000)', 'SGID\n(02000)', 'SUID\n(04000)', 
                 'Other rwx\n(0007)', 'Group rwx\n(0070)', 'User rwx\n(0700)']
    bit_values = [0o1000, 0o2000, 0o4000, 0o0007, 0o0070, 0o0700]
    colors_p2 = ['#F59E0B', '#F97316', '#EF4444', '#64748B', '#0EA5E9', '#10B981']
    
    bars2 = ax2.bar(range(len(bit_names)), bit_values, color=colors_p2, edgecolor='#334155', width=0.6)
    ax2.set_xticks(range(len(bit_names)))
    ax2.set_xticklabels(bit_names, fontsize=8)
    ax2.set_yscale('log')
    
    for bar, val in zip(bars2, bit_values):
        ax2.text(bar.get_x() + bar.get_width()/2, val * 1.15, f"{oct(val)}", 
                 ha='center', color='#F8FAFC', fontsize=8, fontweight='bold')

    # -------------------------------------------------------------
    # PANEL 3: Sabotaj vs Savunma İhlal/Engelleme Metrikleri
    # -------------------------------------------------------------
    ax3 = axs[1, 0]
    style_ax(ax3, "Panel 3: Sabotaj Senaryosu (0777 & SUID) Güvenlik Skoru", 
             "Güvenlik Konfigürasyonu", "Başarılı Engelleme Oranı (%)")
    
    configs = ['Korumasız (0777+SUID)', 'Sertleştirilmiş (0640+nosuid)']
    block_rates = [0.0, 100.0]
    bar_colors = ['#EF4444', '#10B981']
    
    bars3 = ax3.bar(configs, block_rates, color=bar_colors, edgecolor='#334155', width=0.45)
    ax3.set_ylim(0, 115)
    
    for bar, rate in zip(bars3, block_rates):
        ax3.text(bar.get_x() + bar.get_width()/2, rate + 3, f"%{rate:.1f} Engelleme", 
                 ha='center', color='#F8FAFC', fontsize=9, fontweight='bold')
    
    ax3.axhline(100, color='#10B981', linestyle=':', alpha=0.5)

    # -------------------------------------------------------------
    # PANEL 4: umask Değerlerine Göre Efektif İzin Seviyeleri
    # -------------------------------------------------------------
    ax4 = axs[1, 1]
    style_ax(ax4, "Panel 4: umask Değerlerinin Efektif İzinlere Etkisi", 
             "umask Yapılandırması", "Erişim Kısıtlama Düzeyi (Bit Sayısı)")
    
    umasks = ['0000 (Tehlikeli)', '0022 (Standart)', '0027 (Askeri)', '0077 (Maksimum)']
    mask_vals = [0o000, 0o022, 0o027, 0o077]
    bits_blocked = [bin(m).count('1') for m in mask_vals]
    
    bars4 = ax4.bar(umasks, bits_blocked, color=['#EF4444', '#F59E0B', '#0EA5E9', '#10B981'], 
                    edgecolor='#334155', width=0.5)
    ax4.set_ylim(0, 8)
    
    for bar, bits, m in zip(bars4, bits_blocked, mask_vals):
        file_mode = oct(0o666 & ~m)
        dir_mode = oct(0o777 & ~m)
        ax4.text(bar.get_x() + bar.get_width()/2, bits + 0.3, 
                 f"Dosya: {file_mode}\nDizin: {dir_mode}", 
                 ha='center', color='#CBD5E1', fontsize=8, fontweight='bold')

    plt.suptitle("ASELSAN / HAVELSAN Görev Sistemleri: Linux İzinleri, DAC & chmod Mimarisi", 
                 fontsize=15, fontweight='bold', color='#F8FAFC', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[Dashboard] Görselleştirme başarıyla oluşturuldu: {output_png_path}")

def verify_all_assertions(png_path: str = DEFAULT_PNG):
    """Tüm sistem mekanizmalarını katı assert koşullarıyla denetler."""
    print("[*] Katı Doğrulama Testleri (Assertions) Başlatılıyor...")

    # 1. Dosya Sistemi VFS ve umask Doğrulaması
    vfs = LinuxFileSystemVFS(default_umask=0o027)
    cred_user = ProcessCredentials(1001, 1001, 1001, 1001, 1001, 1001)
    file_entry = vfs.sys_creat("crypto_key.pem", cred_user, 0o666)
    
    # 0666 & ~0027 = 0640 (-rw-r-----)
    assert (file_entry.mode & 0o777) == 0o640, f"umask 0027 sonrası dosya 0640 olmalı, alınan: {oct(file_entry.mode)}"
    assert file_entry.permissions_str == "-rw-r-----", f"ls -l çıktısı hatalı: {file_entry.permissions_str}"

    # 2. Dizin umask Doğrulaması
    dir_entry = vfs.sys_mkdir("secure_dir", cred_user, 0o777)
    # 0777 & ~0027 = 0750 (drwxr-x---)
    assert (dir_entry.mode & 0o777) == 0o750, f"umask 0027 sonrası dizin 0750 olmalı, alınan: {oct(dir_entry.mode)}"
    assert dir_entry.permissions_str == "drwxr-x---", f"ls -l dizin çıktısı hatalı: {dir_entry.permissions_str}"

    # 3. DAC First Match Prensibi Doğrulaması
    # Dosya sahibi root, izin 0o040 (Group read only, Owner NO READ)
    weird_inode = InodeEntry(999, "weird", uid=1001, gid=1001, mode=0o100040)
    # Owner dosyayı okumaya çalışıyor
    can_read, msg = posix_generic_permission(weird_inode, cred_user, WANT_READ)
    assert can_read == False, "First Match kuralı: Owner'da r biti yoksa grup r olsa dahi reddedilmeli!"

    # 4. Sticky Bit Doğrulaması
    sticky_dir = InodeEntry(100, "tmp", uid=0, gid=0, mode=0o041777, is_dir=True) # Sticky bit açık
    file_alice = InodeEntry(101, "alice.txt", uid=1001, gid=1001, mode=0o100644)
    cred_bob = ProcessCredentials(1002, 1002, 1002, 1002, 1002, 1002)
    
    unlink_ok, _ = vfs.sys_unlink(sticky_dir, file_alice, cred_bob)
    assert unlink_ok == False, "Sticky bit olan dizinde başkasının dosyası silinemez!"

    cred_alice = ProcessCredentials(1001, 1001, 1001, 1001, 1001, 1001)
    unlink_alice_ok, _ = vfs.sys_unlink(sticky_dir, file_alice, cred_alice)
    assert unlink_alice_ok == True, "Sticky bit olan dizinde dosya sahibi kendi dosyasını silebilir!"

    # 5. SUID Geçiş Doğrulaması
    suid_bin = InodeEntry(102, "suid_root", uid=0, gid=0, mode=0o104755)
    elevated_cred = vfs.execve_transition(suid_bin, cred_alice)
    assert elevated_cred.fsuid == 0, "SUID binary çalıştırıldığında fsuid 0 olmalı!"
    assert elevated_cred.uid == 1001, "Gerçek UID (ruid) değişmemeli!"

    # 6. PNG Görsel Dosya Kontrolü
    if os.path.exists(png_path):
        size = os.path.getsize(png_path)
        assert size > 50000, f"PNG dosyası çok küçük veya bozuk ({size} bayt)"

    print("[PASS] Tüm Katı Doğrulama Testleri (Assertions) Başarıyla Geçti!")

if __name__ == "__main__":
    out_png = "gun_083_permissions_user_group_other_ve_chmod.png"
    generate_dashboard(out_png)
    verify_all_assertions(out_png)
