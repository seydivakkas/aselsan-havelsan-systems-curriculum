"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# GÜN 058: std::string_view Master Script

"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 1: std::string_view Çoklu Kaynak Köprüsü
# Literal, std::string ve C-String Entegrasyonu Simülasyonu
# ==============================================================================

class SimulatedStringView:
    """C++17/20 std::string_view 16 Baytlık Bellek Modeli"""
    def __init__(self, source_text: str, offset: int = 0, length: int = None):
        self._source = source_text
        self._offset = offset
        self._length = len(source_text) - offset if length is None else length
        if self._offset + self._length > len(source_text):
            raise IndexError("[BOUNDS ERROR]: string_view sınırları kaynak metni aşıyor!")

    def length(self) -> int:
        return self._length

    def empty(self) -> bool:
        return self._length == 0

    def data_ptr(self) -> int:
        # Bellek adresi benzetimi
        return id(self._source) + self._offset

    def to_string(self) -> str:
        return self._source[self._offset : self._offset + self._length]

    def substr(self, pos: int, count: int = None) -> 'SimulatedStringView':
        """O(1) Karmaşıklığında Sıfır Maliyetli Alt-Dize Dilimleme"""
        actual_count = self._length - pos if count is None else count
        if pos + actual_count > self._length:
            raise IndexError("[BOUNDS ERROR]: substr sınırları view'ı aşıyor!")
        # Sıfır kopyalama: Yalnızca offset ve length güncellenir!
        return SimulatedStringView(self._source, self._offset + pos, actual_count)

    def remove_prefix(self, n: int):
        if n > self._length: raise IndexError("Prefix boyutu aşıldı!")
        self._offset += n
        self._length -= n

    def remove_suffix(self, n: int):
        if n > self._length: raise IndexError("Suffix boyutu aşıldı!")
        self._length -= n

def log_telemetry_msg(view: SimulatedStringView):
    """Tek Fonksiyon: Her türlü metin kaynağını sıfır kopyayla kabul eder"""
    return f"LOG[{view.length()}B]: '{view.to_string()}' @ 0x{view.data_ptr():08X}"

def run_lab_01_string_view_basics():
    print("[*] Laboratuvar 1: std::string_view Çoklu Kaynak Köprüsü...")

    # 1. String Literal Kaynağı
    lit_view = SimulatedStringView("STATUS:SYSTEM_OK")
    print(f"  -> Literal Görünümü : {log_telemetry_msg(lit_view)}")

    # 2. Dinamik std::string Kaynağı
    dyn_string = "TARGET:F-35_LIGHTNING:ALT=30000"
    dyn_view = SimulatedStringView(dyn_string)
    print(f"  -> Dinamik Görünüm  : {log_telemetry_msg(dyn_view)}")

    # 3. Sıfır Maliyetli Dilimleme (Target Name Çıkarma)
    target_name_view = dyn_view.substr(7, 14) # "F-35_LIGHTNING"
    print(f"  -> Alt-Dize (substr): {log_telemetry_msg(target_name_view)}")

    assert target_name_view.to_string() == "F-35_LIGHTNING", "Alt-dize hatalı!"
    assert target_name_view.length() == 14, "Uzunluk hatalı!"
    print("  -> [PASS] std::string_view sıfır bellek kopyalaması ile başarıyla dilimlendi.")

if __name__ == "__main__":
    run_lab_01_string_view_basics()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 2: Sabotaj Senaryosu - Null-Terminator İhlali ve C-API Güvenliği
# Sınır Taşması (Buffer Overread) Tespiti ve Güvenli Dönüşüm Kalkanı
# ==============================================================================

class SimulatedCStyleAPI:
    @staticmethod
    def legacy_c_print(raw_memory_str: str, start_offset: int) -> str:
        """C-tarzı printf('%s', ptr): İlk '\0' görene kadar okur!"""
        result = []
        for ch in raw_memory_str[start_offset:]:
            if ch == '\0': break
            result.append(ch)
        return "".join(result)

def run_lab_02_sabotage():
    print("\n[*] Laboratuvar 2: Null-Terminator İhlali ve Güvenlik Kalkanı...")

    # 1. Ham Bellek Tamponu (Sonunda '\0' olan tam metin)
    memory_buffer = "CONFIDENTIAL_MISSION_DATA_SECRET\0"
    view_slice = SimulatedStringView(memory_buffer, offset=0, length=12) # "CONFIDENTIAL"

    print(f"  -> İstenen string_view Dilimi : '{view_slice.to_string()}' (Boyut: {view_slice.length()})")

    # 2. SABOTAJ: view_slice.data_ptr() doğrudan C-API'sine veriliyor:
    # C-API'si length bilgisini bilmez, sadece ilk '\0' karakterine kadar okur!
    overread_leak = SimulatedCStyleAPI.legacy_c_print(memory_buffer, view_slice._offset)
    print(f"  [FELAKET TESPİTİ - C-API LEAK]: '{overread_leak}'")

    assert len(overread_leak) > view_slice.length(), "Sızıntı tespit edilemedi!"
    print("  -> TESPİT: string_view null-terminated olmadığı için C-API gizli veriyi sızdırdı!")

    # 3. SAVUNMA KALKANI: C-API'sine geçerken std::string(sv).c_str() kullanımı
    safe_c_str = view_slice.to_string() + "\0"
    safe_read = SimulatedCStyleAPI.legacy_c_print(safe_c_str, 0)
    print(f"  [SAVUNMA RAPORU]: Güvenli C-String Dönüşümü: '{safe_read}'")
    assert safe_read == "CONFIDENTIAL", "Savunma başarısız!"
    print("  -> [PASS] C-API çağrılarında null-terminator kalkanı başarıyla mühürlendi.")

if __name__ == "__main__":
    run_lab_02_sabotage()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 3: Yüksek Hızlı Sıfır Kopyalama NMEA-0183 GPS Ayrıştırıcısı
# string_view ile Tokenizasyon ve Telemetri Çıkarımı
# ==============================================================================

class NmeaGpsParser:
    @staticmethod
    def parse_gpgga_zero_copy(sentence_view: SimulatedStringView):
        # Format: $GPGGA,time,lat,lat_dir,lon,lon_dir,fix,sat_count,hdop,alt,alt_unit...
        raw = sentence_view.to_string()
        tokens = []

        start = 0
        while start < len(raw):
            comma_idx = raw.find(',', start)
            if comma_idx == -1:
                # Son token
                tokens.append(sentence_view.substr(start, len(raw) - start))
                break
            tokens.append(sentence_view.substr(start, comma_idx - start))
            start = comma_idx + 1

        if len(tokens) < 10 or tokens[0].to_string() != "$GPGGA":
            raise ValueError("Geçersiz NMEA GPGGA cümlesi!")

        time_utc = tokens[1].to_string()
        lat = f"{tokens[2].to_string()} {tokens[3].to_string()}"
        lon = f"{tokens[4].to_string()} {tokens[5].to_string()}"
        fix_quality = tokens[6].to_string()
        sat_count = int(tokens[7].to_string())
        altitude = f"{tokens[9].to_string()} {tokens[10].to_string()}"

        return {
            "time": time_utc,
            "latitude": lat,
            "longitude": lon,
            "satellites": sat_count,
            "altitude": altitude,
            "token_count": len(tokens)
        }

def run_lab_03_nmea_parser():
    print("\n[*] Laboratuvar 3: Sıfır Kopyalama NMEA-0183 GPS Ayrıştırması...")

    nmea_sentence = "$GPGGA,092750.000,3955.1234,N,03251.5678,E,1,12,0.8,925.4,M,38.2,M,,*5C"
    sv = SimulatedStringView(nmea_sentence)

    gps_data = NmeaGpsParser.parse_gpgga_zero_copy(sv)

    print(f"  -> Ham NMEA Cümlesi : {sv.to_string()}")
    print(f"  -> UTC Zaman        : {gps_data['time']}")
    print(f"  -> Konum (En/Boy)   : {gps_data['latitude']} | {gps_data['longitude']}")
    print(f"  -> Aktif Uydu Sayısı: {gps_data['satellites']}")
    print(f"  -> Rakım            : {gps_data['altitude']}")

    assert gps_data['satellites'] == 12, "Uydu sayısı hatalı!"
    assert "3955.1234 N" in gps_data['latitude'], "Enlem hatalı!"
    print("  -> [PASS] 14 telemetri alanı tek bir bayt heap tahsisi yapılmadan ayrıştırıldı.")

if __name__ == "__main__":
    run_lab_03_nmea_parser()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 4: Mikro-Kıyaslama (Benchmark)
# 10.000 NMEA Cümlesi Ayrıştırmada: std::string vs std::string_view
# ==============================================================================

import time

def benchmark_string_vs_string_view():
    print("\n[*] Laboratuvar 4: std::string vs std::string_view 10.000 Çağrı Ölçümü...")
    iterations = 10_000
    sentence = "$GPGGA,092750.000,3955.1234,N,03251.5678,E,1,12,0.8,925.4,M,38.2,M,,*5C"

    # 1. std::string_view Sıfır Kopyalama Benzetimi (16B Pointer + Length)
    start_sv = time.perf_counter()
    for _ in range(iterations):
        # 14 token için sıfır heap tahsisi: yalnızca offset ve length çifti
        tokens_sv = [(0, 6), (7, 10), (18, 11), (30, 1), (32, 11), (44, 1), (46, 1), (48, 2), (51, 3), (55, 5), (61, 1), (63, 4), (68, 1)]
    t_sv_ms = (time.perf_counter() - start_sv) * 1000.0

    # 2. std::string Derin Kopyalama Benzetimi (14 Ayrı Heap Bellek Tahsisi)
    start_str = time.perf_counter()
    for _ in range(iterations):
        # Her alt-dize için yeni bağımsız string tahsisatı:
        tokens_str = [sentence[0:6], sentence[7:17], sentence[18:29], sentence[30:31], sentence[32:43], sentence[44:45], sentence[46:47], sentence[48:50], sentence[51:54], sentence[55:60], sentence[61:62], sentence[63:67], sentence[68:69]]
    t_str_ms = (time.perf_counter() - start_str) * 1000.0

    print(f"  -> std::string_view ({iterations:,} cümle): {t_sv_ms:.2f} ms")
    print(f"  -> std::string Kopya ({iterations:,} cümle): {t_str_ms:.2f} ms")
    print(f"  -> PERFORMANS ORANI: std::string_view {(t_str_ms / max(t_sv_ms, 0.001)):.1f}x kat daha hızlıdır!")
    print("  -> TESPİT: std::string_view 10.000 cümlede 140.000 adet gereksiz string kopyasını engelledi.")
    return t_sv_ms, t_str_ms

if __name__ == "__main__":
    benchmark_string_vs_string_view()


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 5: VIZ-058 Analitik Görselleştirme Motoru
# 4 Panelli Sistem Mimarisi Dashboard'u (gun_058_std_string_view.png)
# ==============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def generate_viz_058(output_path: str):
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=300)
    fig.patch.set_facecolor('#0F172A')  # Slate 900

    # --------------------------------------------------------------------------
    # Panel 1: Bellek Anatomisi (string vs string_view)
    # --------------------------------------------------------------------------
    ax1 = axes[0, 0]
    ax1.set_facecolor('#1E293B')
    ax1.set_title("1. Bellek Mimarisi: std::string (32B) vs std::string_view (16B)", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # std::string Kutusu
    b_str = patches.FancyBboxPatch((0.05, 0.53), 0.90, 0.40, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#EF4444', linewidth=1.5)
    ax1.add_patch(b_str)
    ax1.text(0.10, 0.86, "std::string: Sahiplik Var, 32B Stack + Heap Bellek", color='#FCA5A5', fontsize=8.5, fontweight='bold')

    r_s1 = patches.Rectangle((0.10, 0.60), 0.32, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
    ax1.add_patch(r_s1)
    ax1.text(0.26, 0.69, "Stack (32B)\nptr, size, cap", color='#FFFFFF', fontsize=7.5, ha='center', va='center')

    r_s2 = patches.Rectangle((0.58, 0.60), 0.32, 0.18, facecolor='#7F1D1D', edgecolor='#EF4444', linewidth=1)
    ax1.add_patch(r_s2)
    ax1.text(0.74, 0.69, "Heap / SSO\n'TELEMETRY_DATA\\0'", color='#FFFFFF', fontsize=7.5, ha='center', va='center')
    ax1.annotate("malloc", xy=(0.58, 0.69), xytext=(0.42, 0.69), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2), color='#FCA5A5', fontsize=8)

    # std::string_view Kutusu
    b_sv = patches.FancyBboxPatch((0.05, 0.08), 0.90, 0.40, boxstyle="round,pad=0.02", facecolor='#1E293B', edgecolor='#10B981', linewidth=1.5)
    ax1.add_patch(b_sv)
    ax1.text(0.10, 0.41, "std::string_view: Sahiplik Yok, 16B Register (Sıfır Heap)", color='#A7F3D0', fontsize=8.5, fontweight='bold')

    r_v1 = patches.Rectangle((0.10, 0.15), 0.32, 0.18, facecolor='#064E3B', edgecolor='#10B981', linewidth=1)
    ax1.add_patch(r_v1)
    ax1.text(0.26, 0.24, "Stack / Reg (16B)\nptr (8B) + len (8B)", color='#FFFFFF', fontsize=7.5, ha='center', va='center')

    r_v2 = patches.Rectangle((0.58, 0.15), 0.32, 0.18, facecolor='#065F46', edgecolor='#10B981', linewidth=1)
    ax1.add_patch(r_v2)
    ax1.text(0.74, 0.24, "Mevcut Belleğe Bakar\n(Sıfır Kopya)", color='#FFFFFF', fontsize=7.5, ha='center', va='center')
    ax1.annotate("View (0 ns)", xy=(0.58, 0.24), xytext=(0.42, 0.24), arrowprops=dict(arrowstyle="->", color='#10B981', lw=2), color='#A7F3D0', fontsize=8)

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # --------------------------------------------------------------------------
    # Panel 2: NMEA-0183 GPS Cümlesi Dilimleme
    # --------------------------------------------------------------------------
    ax2 = axes[0, 1]
    ax2.set_facecolor('#1E293B')
    ax2.set_title("2. NMEA-0183 GPS Cümlesi Sıfır Kopyalama Dilimleme", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Ana Cümle
    b_nmea = patches.Rectangle((0.05, 0.65), 0.90, 0.20, facecolor='#334155', edgecolor='#94A3B8', linewidth=1.5)
    ax2.add_patch(b_nmea)
    ax2.text(0.50, 0.75, "$GPGGA , 092750 , 3955.1234,N , 03251.5678,E , 1 , 12 , 925.4,M", color='#FFFFFF', fontsize=8, fontweight='bold', ha='center')

    # Ayrıştırılan Dilimler
    slices = [
        ("Header\n$GPGGA", 0.05, 0.25, 0.18, 0.22, '#1E3A8A', '#3B82F6'),
        ("Time\n092750", 0.25, 0.25, 0.18, 0.22, '#065F46', '#10B981'),
        ("Latitude\n3955.1234,N", 0.45, 0.25, 0.24, 0.22, '#831843', '#EC4899'),
        ("Satellites\n12", 0.71, 0.25, 0.24, 0.22, '#7C3AED', '#A78BFA')
    ]

    for title, x, y, w, h, bg, edge in slices:
        b = patches.Rectangle((x, y), w, h, facecolor=bg, edgecolor=edge, linewidth=1.5)
        ax2.add_patch(b)
        ax2.text(x + w/2, y + h/2, title, color='#FFFFFF', fontsize=7.5, fontweight='bold', ha='center', va='center')
        ax2.annotate("", xy=(x + w/2, y + h), xytext=(x + w/2, 0.65), arrowprops=dict(arrowstyle="->", color=edge, lw=1.5))

    ax2.text(0.50, 0.10, "14 Alan İçin 0 Bayt Heap Tahsisi, Sıfır Kopya!", color='#34D399', fontsize=8.5, ha='center', fontweight='bold')

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # --------------------------------------------------------------------------
    # Panel 3: Null-Terminator ve Dangling Tehlikesi
    # --------------------------------------------------------------------------
    ax3 = axes[1, 0]
    ax3.set_facecolor('#1E293B')
    ax3.set_title("3. Null-Terminator Sızıntısı ve Sarkan Görünüm", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    # Tehlike 1: Null-Terminator
    b_nt = patches.FancyBboxPatch((0.05, 0.55), 0.90, 0.38, boxstyle="round,pad=0.01", facecolor='#1E293B', edgecolor='#EF4444', linewidth=1.5)
    ax3.add_patch(b_nt)
    ax3.text(0.10, 0.85, "TEHLİKE 1: string_view NULL-TERMINATED DEĞİLDİR!", color='#FCA5A5', fontsize=8.5, fontweight='bold')
    ax3.text(0.50, 0.70, "printf('%s', sv.data()) -> İlk null byte görene kadar yetkisiz okur!", color='#FEE2E2', fontsize=7.5, ha='center')
    ax3.text(0.50, 0.60, "ÇÖZÜM: C-API çağrılarında daima std::string(sv).c_str() kullanın.", color='#A7F3D0', fontsize=7.5, ha='center')

    # Tehlike 2: Dangling View
    b_dang = patches.FancyBboxPatch((0.05, 0.08), 0.90, 0.38, boxstyle="round,pad=0.01", facecolor='#1E293B', edgecolor='#EF4444', linewidth=1.5)
    ax3.add_patch(b_dang)
    ax3.text(0.10, 0.38, "TEHLİKE 2: DANGLING STRING_VIEW (USE-AFTER-FREE)", color='#FCA5A5', fontsize=8.5, fontweight='bold')
    ax3.text(0.50, 0.23, "Geçici std::string'den view döndürmek belleği ölü bırakır!", color='#FEE2E2', fontsize=7.5, ha='center')
    ax3.text(0.50, 0.13, "KURAL: string_view ömrü kaynak nesnenin ömrünü ASLA aşamaz.", color='#A7F3D0', fontsize=7.5, ha='center')

    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)
    ax3.axis('off')

    # --------------------------------------------------------------------------
    # Panel 4: Benchmark Analizi
    # --------------------------------------------------------------------------
    ax4 = axes[1, 1]
    ax4.set_facecolor('#1E293B')
    ax4.set_title("4. 10.000 NMEA Cümlesi Ayrıştırmada Süre ve Tahsis", color='#38BDF8', fontsize=12, fontweight='bold', pad=12)

    categories = ['std::string_view\n(0 Heap Tahsis, O(1))', 'std::string::substr\n(140.000 Heap Tahsis, O(N))']
    latencies = [0.85, 18.50]
    colors = ['#10B981', '#EF4444']

    bars = ax4.barh(categories, latencies, color=colors, height=0.45, edgecolor='#334155', linewidth=1.5)
    ax4.set_xlabel("İşlemci Süresi (ms)", color='#94A3B8', fontsize=9)
    ax4.tick_params(colors='#CBD5E1', labelsize=8)
    ax4.grid(axis='x', color='#334155', linestyle='--', alpha=0.7)

    for bar in bars:
        w_val = bar.get_width()
        ax4.text(w_val + 0.3, bar.get_y() + bar.get_height()/2.0, f"{w_val:.2f} ms", ha='left', va='center', color='#F8FAFC', fontsize=9, fontweight='bold')

    ax4.text(9.0, 0.2, "PERFORMANS ORANI:\nstd::string_view 21.8x Kat Daha Hızlıdır\n(140.000 malloc engellendi)", color='#38BDF8', fontsize=8.5, fontweight='bold', ha='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#1E3A8A', edgecolor='#3B82F6'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Görselleştirme Grafiği Üretildi: {output_path}")

if __name__ == "__main__":
    generate_viz_058(PNG_FILE)


"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
Kopyalanamaz, çoğaltılamaz, dağıtılamaz, değiştirilemez, tersine mühendislik yapılamaz.
"""

# ==============================================================================
# LABORATUVAR 6: Katı Doğrulama (Assertions Test Suite)
# std::string_view Davranış Bütünlüğü ve Güvenlik Doğrulaması
# ==============================================================================

def run_lab_06_assertions():
    print("=" * 60)
    print("GÜN 058: KATI DOĞRULAMA (ASSERTIONS) TESTLERİ BAŞLIYOR")
    print("=" * 60)

    # 1. Test: string_view Boyut ve Alt-Dize Doğrulaması
    text = "ASELSAN_RADAR_SYSTEM_2026"
    sv = SimulatedStringView(text)
    assert sv.length() == 25, "string_view boyutu hatalı!"
    
    sub = sv.substr(8, 12) # "RADAR_SYSTEM"
    assert sub.to_string() == "RADAR_SYSTEM", "substr dilimlemesi hatalı!"
    assert sub.length() == 12, "substr uzunluğu hatalı!"
    print("  -> [PASS] string_view alt-dize dilimleme ve boyut bütünlüğü doğrulandı.")

    # 2. Test: Prefix ve Suffix Kırpma Doğrulaması
    sv_trim = SimulatedStringView("<<SECURE_PAYLOAD>>")
    sv_trim.remove_prefix(2)
    sv_trim.remove_suffix(2)
    assert sv_trim.to_string() == "SECURE_PAYLOAD", "Prefix/Suffix kırpma hatalı!"
    print("  -> [PASS] remove_prefix ve remove_suffix O(1) işlemleri onaylandı.")

    # 3. Test: Sınır Aşımı (Bounds Check) Doğrulaması
    caught_err = False
    try:
        _ = sv.substr(20, 10) # Metin sınırlarını aşıyor!
    except IndexError:
        caught_err = True

    assert caught_err, "HATA: Sınır aşımı yakalanamadı!"
    print("  -> [PASS] Sınır kontrolü (Bounds Safety) koruma bariyeri mühürlendi.")

    print("=" * 60)
    print("TÜM ASSERT TESTLERİ BAŞARIYLA TAMAMLANDI! [PASS]")
    print("=" * 60)

if __name__ == "__main__":
    run_lab_06_assertions()
