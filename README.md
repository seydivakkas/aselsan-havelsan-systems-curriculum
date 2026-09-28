# 🛡️ ASELSAN & HAVELSAN Odaklı 365 Günlük Sistem Mühendisliği ve Yazılım Mimarisi Müfredatı

[![License: All Rights Reserved](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](https://github.com/seydivakkas)
[![C++ Standard](https://img.shields.io/badge/C%2B%2B-20-00599C?style=flat-square&logo=c%2B%2B)](https://en.cppreference.com/)
[![Standard](https://img.shields.io/badge/Standard-24--H%C3%BCcreli%20Master%20Mimari-blueviolet?style=flat-square)](standart.md)
[![Curriculum](https://img.shields.io/badge/Curriculum-365%20G%C3%BCn%20%2F%2014%20Faz-success?style=flat-square)](mufreddat_docs/01_GUN_365_ANA_PLAN.md)
[![Target](https://img.shields.io/badge/Industry-Savunma%20Sanayii%20%26%20G%C3%B6rev%20Kritik-darkred?style=flat-square)](https://github.com/seydivakkas)

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

---

## 🎯 Vizyon ve Kapsam

Bu depo; sıfır noktasından başlayarak bir mühendisi **ASELSAN, HAVELSAN, ROKETSAN, TUSAŞ ve STM** seviyesinde kıdemli bir **Görev Kritik Sistemler ve Yazılım Mimarına (Mission-Critical Systems & Software Architect)** dönüştürmek üzere kurgulanmış 365 günlük eksiksiz bir mühendislik omurgasıdır.

Müfredat, salt kodlama veya soyut kütüphane kullanımının ötesine geçerek; **C++20 Mastery Omurgası**, donanım-yazılım arayüzü (HAL/MMIO), deterministik gerçek zamanlı işletim sistemleri (**RTOS**), havacılık ve savunma standartları (**DO-178C, MISRA C++**), radar/DSP sinyal işleme, otonom güdüm (**ROS 2 / PX4**) ve uçta çalışan yapay zeka (**TensorRT**) disiplinlerini bir araya getirir.

---

## 🏛️ 24-Hücreli Master Mimari Standardı & 4'lü Paket Mimarisi

Her gün, tavizsiz bir şekilde **[standart.md](standart.md)** belgesinde tarif edilen **24 Hücreli (18 Markdown + 6 Kod)** mimariye ve 4 bileşenden oluşan dosya paketine sahiptir:

```
gunluk_mufredat/gun_xxx/
├── gun_xxx_[konu].md       <-- 24-Hücreli Master Doküman (18 MD + 6 Kod, Eksiksiz Anlatım)
├── gun_xxx_[konu].py       <-- Çalıştırılabilir Simülasyon, Sabotaj, Benchmark & Dashboard Motoru
├── gun_xxx_[konu].png      <-- 4-Panelli Yayın Kalitesinde Doğrulama Dashboard'u (300 DPI, Dark Tema)
└── gun_xxx_[konu].ipynb    <-- 24 Hücreli (18 Markdown + 6 Kod) İnteraktif Jupyter Notebook
```

### 📐 24-Hücre Matrisi
| No | Tip | Bölüm | İçerik ve Pedagojik Hedef |
|:---:|:---:|:---|:---|
| 1 | **MD 1** | Başlık & Özel Lisans | Telif, yasal çerçeve, faz tanımı ve 40-nokta kalite kriterleri |
| 2 | **MD 2** | 1. 🎯 Bugünkü Problem | Çözülen somut mühendislik darboğazı, donanımsal kısıt ve arıza senaryosu |
| 3 | **MD 3** | 2. ❓ Neden Öğreniyoruz? | Radar, Elektronik Harp, Aviyonik ve Görev Sistemlerindeki gerekçe |
| 4 | **MD 4** | 3. 🔍 5N1K Analizi | Sistem, bellek ve donanım sınırlarında çok boyutlu mühendislik tahlili |
| 5 | **MD 5** | 4. 💡 Zihinsel Model (Analoji) | Soyut donanım/yazılım kavramını somutlaştıran pedagojik zihinsel model |
| 6 | **MD 6** | 5. 🧱 İlk İlkeler (First Principles) | Fizik, bellek düzeni, transistör, CPU saat çevrimi ve matematiksel ispat |
| 7 | **MD 7** | 6. 📐 Sistem Mimarisi Şeması | ASCII ve Mermaid ile veri akışı, durum makinesi ve bileşen topolojisi |
| 8 | **CODE 1** | 7. Modül 1: Çekirdek Motor | Çalıştırılabilir, minimal ve saf çekirdek mantık kodu |
| 9 | **MD 8** | 8. Modül 2: Donanıma Yakın Analiz | Sıfır kopyalama (Zero-copy), MMIO, DMA veya donanım katmanı incelemesi |
| 10 | **CODE 2** | 9. Modül 2: Donanıma Yakın Kod | Sıfır kopyalama, atomic veri yolları veya asenkron donanım soyutlaması |
| 11 | **MD 9** | 10. Modül 3: Sınır Durumlar & Kapasite | Kuyruk boyutlandırma, akış kontrolü (flow control), geri basınç (backpressure) |
| 12 | **CODE 3** | 11. Modül 3: Dayanıklı Kuyruk Kodu | Taşmayı önleyen, geri basınçlı dayanıklı boru hattı uygulaması |
| 13 | **MD 10** | 12. Sabotaj & Arıza Enjeksiyonu | Chaos Engineering: sınır ihlali, bellek sızıntısı ve kaynak zehirlenmesi |
| 14 | **CODE 4** | 13. Sabotaj Senaryo Kodu | Korumasız Çöküş vs Dayanıklı Savunma canlı simülasyonu |
| 15 | **MD 11** | 14. Modül 4: Ampirik Kıyaslama | SLA, gecikme analizi, p50/p95/p99 determinizm ve saat döngüsü ölçümü |
| 16 | **CODE 5** | 15. Mikro-Benchmark Motoru | Yüksek çözünürlüklü zamanlayıcılarla ampirik metrik toplama motoru |
| 17 | **MD 12** | 16. Modül 5: 4-Panelli Görsel Planı | 4 alt panelin metrik hedefleri, eksen tanımları ve renk paleti mimarisi |
| 18 | **CODE 6** | 17. 4-Panelli Dashboard & Assert | 300 DPI Matplotlib grafiği üretimi + çalışma zamanı `assert` testleri |
| 19 | **MD 13** | 18. ⚠️ 10 Ölümcül Anti-Pattern | Sahada, kod incelemelerinde ve mülakatlarda yapılan 10 kritik tasarım hatası |
| 20 | **MD 14** | 19. 🔬 Sektörel Standartlar | ASELSAN, HAVELSAN, MISRA C++, DO-178C, POSIX standart maddeleri |
| 21 | **MD 15** | 20. 🛠️ Üretim Kontrol Listesi | Canlı göreve çıkmadan önce mühendisin onaylaması gereken 12 katı kural |
| 22 | **MD 16** | 21. ❓ Sıkça Sorulan Sorular | Kıdemli mimarlık mülakatlarında sorulan derin teknik sorular ve yanıtları |
| 23 | **MD 17** | 22. 🔮 Gelecek Perspektifi | Yeni nesil işlemciler, fotonik, kuantum ve mimari gelecek projeksiyonu |
| 24 | **MD 18** | 23. 🚪 Sonraki Güne Köprü | Pedagojik olarak bir sonraki günün konusuna kesintisiz mantıksal geçiş |

---

## 🗺️ 365 Günlük Faz Yol Haritası

Müfredat 14 ana faz altında kurgulanmıştır:

| Faz | Kapsam | Gün Aralığı | Süre | Odak Alanı & Temel Çıktı |
|:---:|:---|:---:|:---:|:---|
| **F0** | Bilgisayar ve Yazılım Temelleri | Gün 1 - 20 | 20 Gün | Donanım modeli, bellek hiyerarşisi, Linux terminali, Git disiplini |
| **F1** | C++20 Core & Mastery Spine | Gün 21 - 75 | 55 Gün | Modern C++20, RAII, Smart Pointers, Move Semantics, Concepts, Ranges |
| **F2** | Linux / POSIX Sistem Programlama | Gün 76 - 105 | 30 Gün | Dosya tanımlayıcıları, epoll, sinyaller, bellek haritalama (mmap), daemon mimarisi |
| **F3** | Threads / Concurrency / IPC | Gün 106 - 130 | 25 Gün | Lock-free yapılar, atomic işlemler, semaforlar, paylaşımlı bellek, TSan |
| **F4** | TCP/UDP / Protokol / Serileştirme | Gün 131 - 160 | 30 Gün | Özel ikili telemetri protokolleri, Protobuf, FlatBuffers, akış kontrolü |
| **F5** | Gömülü Sistemler / RTOS / STM32 | Gün 161 - 195 | 35 Gün | FreeRTOS, kesme servis rutinleri (ISR), donanım zamanlayıcıları, DMA |
| **F6** | DDS / ROS 2 / Gazebo | Gün 196 - 225 | 30 Gün | Gerçek zamanlı veri dağıtım servisi (DDS), ROS 2 nodları, UGV simülasyonu |
| **F7** | PX4 / MAVLink Aviyonik | Gün 226 - 245 | 20 Gün | İHA aviyonik haberleşmesi, MAVLink protokolü, durum tahmini, SIL testi |
| **F8** | Bilgisayarlı Görü / TensorRT | Gün 246 - 275 | 30 Gün | Hedef tespiti, gerçek zamanlı kenar yapay zeka (Edge AI), CUDA & TensorRT |
| **F9** | Kontrol Teorisi & Pekiştirmeli Öğrenme | Gün 276 - 295 | 20 Gün | PID, LQR, durum-uzayı modelleri, insansız sistemler için RL algoritmaları |
| **F10** | Radar / DSP / Sayısal Haberleşme | Gün 296 - 315 | 20 Gün | Sayısal sinyal işleme, FFT, darbe sıkıştırma, radar/EO sensör füzyonu |
| **F11** | Doğrulama / SIL / HIL / Test Fabrikası | Gün 316 - 335 | 20 Gün | Sanal aviyonik doğrulama, HIL test donanımları, DO-178C gereksinim takibi |
| **F12** | 5G & Dağıtık Görev Sistemleri | Gün 336 - 350 | 15 Gün | Düşük gecikmeli taktik haberleşme, dağıtık mutabakat, güvenli veri yolları |
| **F13** | Savunma AI Mühendisliği & Büyük Mimari | Gün 351 - 365 | 15 Gün | Büyük ölçekli sistem entegrasyonu, mimari incelemeler, bitirme projeleri |

---

## 📊 Örnek Doğrulama Dashboard'u

Her gün üretilen `gun_xxx.png` dosyası; 300 DPI baskı kalitesinde, karanlık temalı (`#0d1117`) ve 4 kritik mühendislik metriğini aynı anda gösteren bir analiz paneli sunar:

```
+------------------------------------+------------------------------------+
|  Panel 1: Çekirdek Metrik & Veri   |  Panel 2: Donanım & Bellek Profili |
|  (Throughput / Sinyal / Durum)     |  (Cache Hit, Heap vs Stack, MMIO)  |
+------------------------------------+------------------------------------+
|  Panel 3: Sabotaj & Arıza Tepkisi  |  Panel 4: SLA & Determinizm (p99)  |
|  (Korumasız Çöküş vs Savunma)      |  (Gecikme Dağılımı & Jitter Çiti)  |
+------------------------------------+------------------------------------+
```

---

## 🔍 Otomatik Kalite Denetimi (`verify_standart.py`)

Müfredat içerisindeki her gün, otomatik doğrulama betiği ile katı kurallara göre denetlenir:

```bash
python verify_standart.py
```

Denetlenen maddeler:
- [x] Her klasörde 4 zorunlu dosyanın (`.md`, `.py`, `.png`, `.ipynb`) varlığı
- [x] 24 hücre başlığının regex ile doğrulanması
- [x] `.ipynb` dosyasındaki hücre sayısı ve tür dağılımı (18 MD + 6 Code)
- [x] Dashboard görselinin 300 DPI çözünürlük doğrulaması
- [x] Simülasyon kodundaki `assert` testlerinin çalışma zamanında sıfır hata ile tamamlanması

---

## 📚 Dokümantasyon Rehberi

Daha fazla ayrıntı için `mufreddat_docs/` dizinini inceleyebilirsiniz:
- [00_BASLA.md](mufreddat_docs/00_BASLA.md) — Müfredatın Başlangıç Kılavuzu & Kullanım Prensipleri
- [01_GUN_365_ANA_PLAN.md](mufreddat_docs/01_GUN_365_ANA_PLAN.md) — 365 Günün Konu ve Çıktı Listesi
- [03_KAVRAM_HARITASI.md](mufreddat_docs/03_KAVRAM_HARITASI.md) — Kavramsal Bağımlılık Ağları
- [12_CPP_MASTERY_SPINE.md](mufreddat_docs/12_CPP_MASTERY_SPINE.md) — 50 Ünitelik C++20 Ustalık Omurgası
- [17_RADAR_DSP_SISTEMLERI.md](mufreddat_docs/17_RADAR_DSP_SISTEMLERI.md) — Radar ve DSP Sistemleri Rehberi
- [19_EMBEDDED_RTOS_STACK.md](mufreddat_docs/19_EMBEDDED_RTOS_STACK.md) — Gömülü RTOS Mimarisi

---

## ⚖️ Lisans ve Kullanım Koşulları

Bu çalışma **açık kaynaklı bir yazılım değildir**. Telif hakları tamamen saklıdır.

Yalnızca GitHub üzerinde eğitim/inceleme amaçlı görüntülemeye izin verilmiştir. Yazılı izin olmaksızın kopyalanamaz, çoğaltılamaz, dağıtılamaz veya ticari projelerde kullanılamaz.

**İletişim ve İzin Talepleri:** [GitHub @seydivakkas](https://github.com/seydivakkas)
