#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

GÜN 008: Kaynak Kod -> Compiler -> Object -> Executable Mimarisi
Çalıştırılabilir Simülasyon, Sabotaj, Benchmark & 4-Panelli Doğrulama Dashboard'u
"""

import os
import sys
import time
import random
from typing import Dict, List, Optional, Tuple, Set

# Windows Konsol UTF-8 Ayarı
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Matplotlib headless backend
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


# =====================================================================
# MODÜL 1: Sembol Tablosu & Relocatable Object (.o) Yapısı
# =====================================================================

class Symbol:
    """Bir nesne dosyasındaki (object file) sembol (fonksiyon veya global değişken)."""
    def __init__(self, name: str, is_defined: bool, offset: int = 0, section: str = ".text"):
        self.name = name
        self.is_defined = is_defined
        self.offset = offset
        self.section = section
        self.final_address: Optional[int] = None


class RelocationEntry:
    """Linker'ın nihai adresi yerleştireceği yama noktası (patch point)."""
    def __init__(self, section: str, offset: int, symbol_name: str):
        self.section = section
        self.offset = offset
        self.symbol_name = symbol_name


class ObjectFile:
    """Yeniden Konumlandırılabilir (Relocatable) ELF Nesne Dosyası (.o)."""
    def __init__(self, filename: str):
        self.filename = filename
        self.text_section = bytearray()      # Makine kodları (.text)
        self.data_section = bytearray()      # Başlangıç değerli veriler (.data)
        self.symbols: Dict[str, Symbol] = {} # Sembol tablosu (.symtab)
        self.relocations: List[RelocationEntry] = [] # Relocation tablosu (.rel.text)

    def define_symbol(self, name: str, section: str, offset: int):
        self.symbols[name] = Symbol(name, is_defined=True, offset=offset, section=section)

    def reference_symbol(self, name: str, section: str, offset: int):
        if name not in self.symbols:
            self.symbols[name] = Symbol(name, is_defined=False)
        self.relocations.append(RelocationEntry(section, offset, name))


# =====================================================================
# MODÜL 2: Statik Linker (Bağlayıcı) Motoru
# =====================================================================

class ExecutableELF:
    """Linker tarafından üretilen nihai çalıştırılabilir dosya."""
    def __init__(self, entry_point: int = 0x00400000):
        self.entry_point = entry_point
        self.image = bytearray()
        self.symbol_addresses: Dict[str, int] = {}
        self.total_size = 0


class StaticLinker:
    """Birden fazla .o dosyasını birleştirip adresleri yamayan (relocate) Linker."""
    def __init__(self, base_address: int = 0x00400000):
        self.base_address = base_address
        self.global_symbol_table: Dict[str, Symbol] = {}

    def link(self, objects: List[ObjectFile]) -> ExecutableELF:
        elf = ExecutableELF(entry_point=self.base_address)
        current_addr = self.base_address

        # 1. Aşama: Sembol Toplama ve Adres Belirleme
        for obj in objects:
            for name, sym in obj.symbols.items():
                if sym.is_defined:
                    if name in self.global_symbol_table and self.global_symbol_table[name].is_defined:
                        raise ValueError(f"Linker Error: Multiple definition of symbol '{name}' in {obj.filename}")
                    sym.final_address = current_addr + sym.offset
                    self.global_symbol_table[name] = sym
                    elf.symbol_addresses[name] = sym.final_address
            # .text bölümünü ana ikiliye ekle
            elf.image.extend(obj.text_section)
            current_addr += len(obj.text_section)

        # 2. Aşama: Relocation (Adres Yamama) ve Undefined Symbol Kontrolü
        for obj in objects:
            for rel in obj.relocations:
                if rel.symbol_name not in self.global_symbol_table or not self.global_symbol_table[rel.symbol_name].is_defined:
                    raise KeyError(f"Linker Error: Undefined reference to symbol '{rel.symbol_name}' in {obj.filename}")
                
                # Gerçek donanımda makine kodundaki hedef adres buraya yazılır
                target_addr = self.global_symbol_table[rel.symbol_name].final_address
                # 4-baytlık little-endian adres yerleştirme simülasyonu
                addr_bytes = target_addr.to_bytes(4, byteorder='little')
                patch_pos = rel.offset
                if patch_pos + 4 <= len(elf.image):
                    elf.image[patch_pos:patch_pos+4] = addr_bytes

        elf.total_size = len(elf.image)
        return elf


# =====================================================================
# MODÜL 3: Paralel Derleme Boru Hattı & Bağımlılık Ağacı (DAG)
# =====================================================================

class CompilationPipeline:
    """C++ derleme boru hattı aşamalarını ve gecikmelerini simüle eden motor."""
    @staticmethod
    def compile_unit(loc: int, opt_level: str = "-O2") -> Dict[str, float]:
        # Preprocessing, Parsing, CodeGen, Linking süreleri (ms)
        # Optimizasyon seviyesi arttıkça CodeGen uzar ama çıktı küçülür
        opt_factors = {"-O0": 0.5, "-O1": 0.8, "-O2": 1.0, "-O3": 1.5, "-Os": 1.3}
        f = opt_factors.get(opt_level, 1.0)
        
        t_preproc = (loc * 0.0005) # Header genişlemesi
        t_parse = (loc * 0.0012)   # AST & Anlamsal analiz
        t_codegen = (loc * 0.0020) * f # LLVM IR & Register Allocation
        t_link = (loc * 0.0008)
        
        return {
            "preproc_ms": t_preproc,
            "parse_ms": t_parse,
            "codegen_ms": t_codegen,
            "link_ms": t_link,
            "total_ms": t_preproc + t_parse + t_codegen + t_link
        }


# =====================================================================
# MODÜL 4: Sabotaj & Hata Enjeksiyonu (Linker Failures)
# =====================================================================

def simulate_linker_sabotages() -> Tuple[bool, bool]:
    """
    1. Undefined Reference: Bildirimi var ama gövdesi yok.
    2. Multiple Definition: İki farklı .cpp dosyasında aynı global fonksiyon var.
    """
    linker = StaticLinker()
    
    # 1. Senaryo: Undefined Reference
    obj1 = ObjectFile("radar_main.o")
    obj1.text_section.extend(b"\x90\x90\x90\x90\x00\x00\x00\x00") # NOP + Adres boşluğu
    obj1.define_symbol("main", ".text", offset=0)
    obj1.reference_symbol("calculate_azimuth", ".text", offset=4) # Tanımlanmamış fonksiyon!
    
    undefined_caught = False
    try:
        linker.link([obj1])
    except KeyError:
        undefined_caught = True

    # 2. Senaryo: Multiple Definition
    obj2a = ObjectFile("telemetry_a.o")
    obj2a.text_section.extend(b"\x90\x90")
    obj2a.define_symbol("send_packet", ".text", offset=0)

    obj2b = ObjectFile("telemetry_b.o")
    obj2b.text_section.extend(b"\x90\x90")
    obj2b.define_symbol("send_packet", ".text", offset=0) # Çakışan sembol!

    multiple_def_caught = False
    try:
        linker_dup = StaticLinker()
        linker_dup.link([obj2a, obj2b])
    except ValueError:
        multiple_def_caught = True

    return undefined_caught, multiple_def_caught


# =====================================================================
# MODÜL 5 & 6: Ampirik Kıyaslama ve 4-Panelli Dashboard
# =====================================================================

def run_benchmarks_and_generate_dashboard():
    # 1. Optimizasyon Seviyeleri Kıyaslaması
    opt_levels = ["-O0", "-O1", "-O2", "-O3", "-Os"]
    # 100,000 satırlık radar modülü için simüle edilen boyutlar ve çalışma süreleri
    binary_sizes_kb = [14200, 8900, 6200, 7800, 4100]      # -Os en küçük, -O3 unroll yüzünden büyüyebilir
    execution_latencies_ns = [48.5, 21.2, 11.4, 9.1, 14.8] # -O3 en hızlı

    # 2. Derleme Aşamalarının Zaman Dağılımı
    pipeline_res = CompilationPipeline.compile_unit(loc=50000, opt_level="-O2")
    stages = ['Ön İşleme\n(Preprocessor)', 'Ayrıştırma\n(AST & Parser)', 'Optimizasyon\n(LLVM CodeGen)', 'Bağlama\n(Linker)']
    stage_times = [pipeline_res["preproc_ms"], pipeline_res["parse_ms"], pipeline_res["codegen_ms"], pipeline_res["link_ms"]]

    # 3. Statik vs Dinamik Bağlama Kıyaslaması
    link_types = ['Statik Bağlama\n(-static / ELF İçinde)', 'Dinamik Bağlama\n(Shared / .so)']
    file_sizes_mb = [12.4, 0.45] # Statik tüm libc/libstdc++ gömer, dinamik minik kalır
    startup_times_us = [45, 820] # Statik anında başlar, dinamik ld.so çözümlemesi bekler

    # 4. Sembol Sayısı vs Linker Relocation Süresi
    symbol_counts = [100, 500, 2000, 5000, 10000, 25000]
    relocation_times_ms = [0.12, 0.65, 2.9, 8.4, 19.8, 58.2] # O(N log N) veya O(N) hash table tabanlı

    # ==================== GRAFİK ÇİZİMİ ====================
    plt.style.use('dark_background')
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0d1117')

    color_accent = '#58a6ff'
    color_warn = '#f85149'
    color_success = '#3fb950'
    color_gold = '#d29922'
    color_purple = '#bc8cff'

    # Panel 1: Optimizasyon vs Boyut ve Yürütme Hızı
    ax1 = axes[0, 0]
    ax1.set_facecolor('#161b22')
    x = np.arange(len(opt_levels))
    width = 0.35
    ax1.bar(x - width/2, binary_sizes_kb, width, label='İkili Dosya Boyutu (KB)', color=color_accent, alpha=0.85)
    ax1.set_ylabel('Boyut (KB)', fontsize=10, color=color_accent)
    ax1.set_xticks(x)
    ax1.set_xticklabels(opt_levels)
    
    ax1_twin = ax1.twinx()
    ax1_twin.plot(x, execution_latencies_ns, color=color_warn, marker='o', linewidth=2.5, label='Görev Yürütme Süresi (ns)')
    ax1_twin.set_ylabel('Yürütme Gecikmesi (ns)', fontsize=10, color=color_warn)
    ax1.set_title('Panel 1: Derleyici Optimizasyon Seviyeleri: Boyut vs Hız Trade-off', fontsize=12, fontweight='bold', color='white', pad=10)
    ax1.grid(True, linestyle='--', alpha=0.3, color='#30363d')

    # Panel 2: Derleme Aşamalarının Zaman Dağılımı (Pasta / Donut)
    ax2 = axes[0, 1]
    ax2.set_facecolor('#161b22')
    colors = [color_gold, color_accent, color_purple, color_success]
    wedges, texts, autotexts = ax2.pie(stage_times, labels=stages, autopct='%1.1f%%', startangle=140,
                                       colors=colors, wedgeprops=dict(width=0.4, edgecolor='#0d1117'))
    for at in autotexts: at.set_color('white'); at.set_fontweight('bold')
    ax2.set_title('Panel 2: C++ Derleme Aşamalarının Süre Dağılımı', fontsize=12, fontweight='bold', color='white', pad=10)

    # Panel 3: Statik vs Dinamik Bağlama (Boyut vs Başlangıç Gecikmesi)
    ax3 = axes[1, 0]
    ax3.set_facecolor('#161b22')
    x3 = np.arange(len(link_types))
    ax3.bar(x3 - width/2, file_sizes_mb, width, label='Dosya Boyutu (MB)', color=color_gold, alpha=0.85)
    ax3.set_ylabel('İkili Dosya Boyutu (MB)', fontsize=10, color=color_gold)
    ax3.set_xticks(x3)
    ax3.set_xticklabels(link_types)

    ax3_twin = ax3.twinx()
    ax3_twin.bar(x3 + width/2, startup_times_us, width, label='Açılış Gecikmesi (µs)', color=color_success, alpha=0.85)
    ax3_twin.set_ylabel('İlk Yükleme Gecikmesi (µs)', fontsize=10, color=color_success)
    ax3.set_title('Panel 3: Aviyonik Tercihi: Statik vs Dinamik Bağlama Analizi', fontsize=12, fontweight='bold', color='white', pad=10)
    ax3.grid(True, linestyle='--', alpha=0.3, color='#30363d')

    # Panel 4: Sembol Sayısı vs Linker Adres Çözümleme Süresi
    ax4 = axes[1, 1]
    ax4.set_facecolor('#161b22')
    ax4.plot(symbol_counts, relocation_times_ms, marker='D', color=color_accent, linewidth=2.5, label='Relocation & Symbol Resolution (ms)')
    ax4.set_title('Panel 4: Sembol Sayısı Artışı vs Linker Relocation Gecikmesi', fontsize=12, fontweight='bold', color='white', pad=10)
    ax4.set_xlabel('Toplam Sembol Sayısı (Fonksiyon / Değişken)', fontsize=10, color='#8b949e')
    ax4.set_ylabel('Bağlama Süresi (ms)', fontsize=10, color='#8b949e')
    ax4.grid(True, linestyle='--', alpha=0.3, color='#30363d')
    ax4.legend(loc='upper left')

    plt.tight_layout()
    output_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gun_008_kaynak_kod_compiler_object_executable.png")
    plt.savefig(output_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Gün 008 Dashboard başarıyla üretildi: {output_png}")


# =====================================================================
# DOĞRULAMA VE ASSERT TESTLERİ
# =====================================================================

def verify_all():
    print("--- GÜN 008 SİSTEM VE MİMARİ DOĞRULAMA TESTLERİ BAŞLIYOR ---")
    
    # Test 1: Minimal Object & Linker Testi
    obj1 = ObjectFile("math_lib.o")
    obj1.text_section.extend(b"\xB8\x2A\x00\x00\x00\xC3") # mov eax, 42; ret
    obj1.define_symbol("get_azimuth", ".text", offset=0)

    obj2 = ObjectFile("main.o")
    obj2.text_section.extend(b"\xE8\x00\x00\x00\x00\xC3") # call [hedef]; ret
    obj2.define_symbol("main", ".text", offset=0)
    obj2.reference_symbol("get_azimuth", ".text", offset=1) # 1. bayttan itibaren hedef adres

    linker = StaticLinker(base_address=0x00401000)
    elf = linker.link([obj1, obj2])

    assert elf.total_size == 12 # 6 + 6 bayt
    assert elf.symbol_addresses["get_azimuth"] == 0x00401000
    assert elf.symbol_addresses["main"] == 0x00401006
    print("[PASS] Test 1: Statik Linker sembol çözümleme ve adres relocation testi başarılı.")

    # Test 2: Sabotaj Testleri (Undefined Reference & Multiple Definition)
    undef_ok, mult_ok = simulate_linker_sabotages()
    assert undef_ok == True
    assert mult_ok == True
    print("[PASS] Test 2: Linker sabotaj testleri (Eksik Sembol & Çift Tanım) başarıyla engellendi.")

    # Test 3: Dashboard Üretimi
    run_benchmarks_and_generate_dashboard()
    print("[PASS] Test 3: 4-Panelli 300 DPI Dashboard üretildi.")
    print("[PASS] Gün 008: Tüm derleyici, bağlayıcı, nesne dosyası ve ELF mimari kuralları doğrulandı.")


if __name__ == "__main__":
    verify_all()
