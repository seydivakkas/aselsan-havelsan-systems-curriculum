#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.

Otomatik Standart Doğrulama Betiği (verify_standart.py)
gunluk_mufredat altındaki günlerin 24-Hücreli Master Mimari Planına ve 4-dosyalı pakete
uygunluğunu katı kurallarla denetler.
"""

import os
import sys
import json
import re

# Windows Konsol UTF-8 Ayarı
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def verify_day(day_dir: str) -> bool:
    day_name = os.path.basename(day_dir)
    print(f"\n=======================================================")
    print(f"[DENETLEME] {day_name}")
    print(f"=======================================================")
    
    files = os.listdir(day_dir)
    md_files = [f for f in files if f.endswith(".md")]
    py_files = [f for f in files if f.endswith(".py")]
    png_files = [f for f in files if f.endswith(".png")]
    ipynb_files = [f for f in files if f.endswith(".ipynb")]
    
    # 1. 4-Dosyalı Paket Kontrolü
    errors = []
    if not md_files: errors.append("EKSİK: .md dosyası bulunamadı!")
    if not py_files: errors.append("EKSİK: .py dosyası bulunamadı!")
    if not png_files: errors.append("EKSİK: .png dosyası bulunamadı!")
    if not ipynb_files: errors.append("EKSİK: .ipynb dosyası bulunamadı!")
    
    if errors:
        for e in errors: print(f"[-] {e}")
        return False
        
    md_path = os.path.join(day_dir, md_files[0])
    py_path = os.path.join(day_dir, py_files[0])
    png_path = os.path.join(day_dir, png_files[0])
    ipynb_path = os.path.join(day_dir, ipynb_files[0])
    
    print(f"[+] 4'lü Dosya Paketi Mevcut:")
    print(f"  - MD:    {md_files[0]}")
    print(f"  - PY:    {py_files[0]}")
    print(f"  - PNG:   {png_files[0]} ({os.path.getsize(png_path):,} bayt)")
    print(f"  - IPYNB: {ipynb_files[0]}")
    
    # 2. Lisans Kontrolü
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    if "ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR" not in md_content or "Seydi Eryılmaz" not in md_content:
        print("[-] HATA: Özel Lisans metni .md dosyasında eksik!")
        return False
    else:
        print("[+] Özel Lisans Uyarısı Onaylandı.")
        
    # 3. IPYNB 24 Hücre Denetimi
    try:
        with open(ipynb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        cells = nb.get("cells", [])
        md_cells = [c for c in cells if c.get("cell_type") == "markdown"]
        code_cells = [c for c in cells if c.get("cell_type") == "code"]
        
        print(f"[+] Notebook Hücre Yapısı: {len(cells)} Toplam (MD: {len(md_cells)}, CODE: {len(code_cells)})")
        if len(cells) != 24 or len(md_cells) != 18 or len(code_cells) != 6:
            print(f"[-] HATA: Notebook hücre sayısı 24 değil (18 MD + 6 Code olmalı)!")
            return False
    except Exception as e:
        print(f"[-] HATA: Notebook JSON okunamadı: {e}")
        return False

    print(f"[PASS] {day_name} 24-Hücreli Master Mimari Standardına %100 Uygun!\n")
    return True

def main():
    base_dir = r"c:\Users\seydieryilmaz\Downloads\Olay_Proje\gunluk_mufredat"
    days = sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d.startswith("gun_")])
    
    all_ok = True
    print(f"\nToplam {len(days)} gün denetleniyor...\n")
    for d in days:
        day_path = os.path.join(base_dir, d)
        ok = verify_day(day_path)
        if not ok:
            all_ok = False
            
    if all_ok:
        print("\n[MÜKEMMEL] TÜM GÜNLER 24-HÜCRELİ MASTER MİMARİ STANDARDINA %100 UYGUNDUR!")
    else:
        print("\n[UYARI] BAZI GÜNLERDE STANDART DIŞI DURUMLAR TESPİT EDİLDİ!")

if __name__ == "__main__":
    main()
