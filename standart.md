# 🏛️ ASELSAN & HAVELSAN 365 Günlük Mühendislik Müfredatı — 24-Hücreli Master Mimari Standardı

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

## 🎯 Belgenin Amacı ve Kapsamı
Bu standart; **365_Gun_ASELSAN_HAVELSAN_Tum_Kutuphaneler_Mekanizmalar_Guncel.xlsx** dosyasında yer alan 365 günün tamamında, junior bir mühendisi sıfırdan alarak **ASELSAN, HAVELSAN, Roketsan, TUSAŞ ve STM** seviyesinde kıdemli bir sistem/yazılım mimarına dönüştürecek pedagojik derinliği ve mühendislik disiplinini garanti altına alır.

Her gün, istisnasız olarak **24 Hücreli Değişmez Mimari Planı (18 Markdown + 6 Kod)** ve **4'lü Dosya Paketi** standardına göre üretilecek, doğrulanacak ve teslim edilecektir.

---

## 📁 4-Bileşenli Günlük Paket Mimarisi

Her gün `gunluk_mufredat/gun_xxx/` klasörü altında şu 4 dosya eksiksiz bulunmak zorundadır:

```
gunluk_mufredat/gun_xxx/
├── gun_xxx_[konu].md       <-- 24-Hücreli Master Doküman (18 MD + 6 Kod, Eksiksiz Anlatım)
├── gun_xxx_[konu].py       <-- Çalıştırılabilir Simülasyon, Sabotaj, Benchmark & Dashboard Motoru
├── gun_xxx_[konu].png      <-- 4-Panelli Yayın Kalitesinde Doğrulama Dashboard'u (300 DPI, Dark Tema)
└── gun_xxx_[konu].ipynb    <-- 24 Hücreli (18 Markdown + 6 Kod) İnteraktif Jupyter Notebook
```

---

## 📐 Sabitlenen 24-Hücreli Mimari Standardı Matrisi

| No | Hücre Tipi | Başlık / Açıklama | Pedagojik & Teknik Amaç |
|:---|:---|:---|:---|
| 1 | **MD 1** | Başlık, Özel Lisans Uyarısı, Faz Bilgisi ve 40-Nokta Bildirimi | Telif, yasal çerçeve, faz ve 40-nokta kalite kriterleri bildirimi. |
| 2 | **MD 2** | 1. 🎯 Bugünkü Problem: [Günün Somut Mühendislik Problemi] | Konunun hangi darboğazı, arızayı ve donanımsal kısıtı çözdüğü. |
| 3 | **MD 3** | 2. ❓ Bu Konuyu Neden Öğreniyoruz? (Savunma Sanayii Gerekçesi) | Kritik sistemlerdeki (Radar, EW, Aviyonik) kavramsal derinlik ve tasarım zorunluluğu. |
| 4 | **MD 4** | 3. 🔍 5N1K Analizi (Sistem ve Donanım Sınırları) | Ne, Neden, Nerede, Nasıl, Ne Zaman, Kim ekseninde kapsamlı mühendislik analizi. |
| 5 | **MD 5** | 4. 💡 Günlük Hayat Benzetmesi (Zihinsel Model / Analoji) | Soyut donanım/yazılım kavramını somutlaştıran pedagojik zihinsel model. |
| 6 | **MD 6** | 5. 🧱 İlk İlkeler (First Principles) ve Matematiksel / Donanımsal Model | Fizik, bellek düzeni, transistör, CPU saat döngüsü veya matematiksel ispat. |
| 7 | **MD 7** | 6. 📐 ASCII ve Mermaid Sistem Mimarisi Şeması | Veri akışı, durum makineleri, bellek yerleşimi ve bileşen etkileşim diyagramları. |
| 8 | **CODE 1** | 7. Modül 1: Temel Çekirdek Mekanizma / Motor İmplemantasyonu | Çalıştırılabilir, bağımsız, minimal ve saf çekirdek mantık kodu. |
| 9 | **MD 8** | 8. Modül 2: Donanıma Yakın / İleri Düzey Alternatif Mekanizma | İleri düzey optimizasyon, sıfır kopyalama veya donanım katmanı analizi. |
| 10 | **CODE 2** | 9. Modül 2: İleri Düzey / Donanıma Yakın Mekanizma Kodu | Sıfır kopyalama, DMA, MMIO, atomic veya asenkron veri yolu uygulaması. |
| 11 | **MD 9** | 10. Modül 3: Dinamik Sınır Durumlar, Geri Basınç ve Kapasite | Kuyruk boyutlandırma, akış kontrolü (flow control) ve fast-fail tasarımı. |
| 12 | **CODE 3** | 11. Modül 3: Sınırlı Kuyruk ve Geri Basınç Boru Hattı Kodu | Taşmayı önleyen dayanıklı (resilient) ve geri basınçlı boru hattı kodu. |
| 13 | **MD 10** | 12. Sabotaj ve Arıza Enjeksiyonu (Chaos Engineering / Bilerek Boz) | Hata senaryosu, sınır ihlali, kaynak zehirlenmesi ve çöküş simülasyonu tasarımı. |
| 14 | **CODE 4** | 13. Sabotaj Senaryosu: Korumasız Çöküş vs Dayanıklı Savunma | Sistemin arıza anındaki davranışını ispatlayan canlı sabotaj ve savunma kodu. |
| 15 | **MD 11** | 14. Modül 4: Ampirik Kıyaslama ve SLA / Gecikme Analizi (p50/p95/p99) | İstatistiksel gecikme dağılımı, determinizm ve saat döngüsü ölçüm analizi. |
| 16 | **CODE 5** | 15. Kapsamlı Ampirik Kıyaslama ve Metrik Toplama Motoru | Yüksek çözünürlüklü zamanlayıcılarla mikro-benchmark ve veri toplama motoru. |
| 17 | **MD 12** | 16. Modül 5: 4-Panelli Yayın Kalitesinde Dayanıklılık Dashboard Planı | 4 alt panelin metrik hedefleri, eksen tanımları ve görselleştirme mimarisi. |
| 18 | **CODE 6** | 17. 4-Panelli Görselleştirme (.png) ve Katı Doğrulama (Assertions) | 300 DPI Matplotlib grafiği üretimi + çalışma zamanı assert doğrulama testleri. |
| 19 | **MD 13** | 18. ⚠️ 10 Ölümcül Anti-Pattern | Sahada, kod incelemelerinde ve teknik mülakatlarda yapılan en yaygın 10 tasarım hatası tablosu. |
| 20 | **MD 14** | 19. 🔬 Sektörel Standartlar (ASELSAN, HAVELSAN, MISRA, DO-178C) | Askeri, aviyonik ve endüstriyel standartlara doğrudan maddesel referanslar. |
| 21 | **MD 15** | 20. 🛠️ Üretim Kontrol Listesi (Production Checklist - 12 Katı Kural) | Canlı askeri sisteme çıkmadan önce mühendisin onaylaması gereken 12 maddelik kontrol listesi. |
| 22 | **MD 16** | 21. ❓ Sıkça Sorulan Sorular (Mülakat & Saha Soruları) | Kıdemli sistem mimarlığı mülakatlarında sorulan derin teknik sorular ve yanıtları. |
| 23 | **MD 17** | 22. 🔮 Gelecek Perspektifi (Donanım & Mimari Trendleri) | Yeni nesil işlemciler, fotonik, kuantum ve geleceğe yönelik mimari öngörü. |
| 24 | **MD 18** | 23. 🚪 Sonraki Güne Köprü (Neden-Sonuç Bağı) | Pedagojik olarak bir sonraki günün konusuna kesintisiz mantıksal geçiş. |

---

## 🛡️ Katı Kalite ve Üretim Kuralları

1. **Lisans Şartı:** Tüm `.md`, `.py` ve `.ipynb` dosyalarının en başında kullanıcının özel lisansı yer alacaktır. MIT veya açık kaynak lisansı kullanılmayacaktır.
2. **Hücre Sayısı ve Sırası:** 24 hücre kuralı tavizsizdir. 18 Markdown ve 6 Kod hücresi tam olarak yukarıdaki sırada oluşturulacaktır. Özet geçme, birleştirme veya kısaltma kesinlikle yasaktır.
3. **Grafik Standardı:** `.png` dashboard'u 4 panelli (2x2 grid), 300 DPI çözünürlükte, koyu arka planlı (`#0d1117`), yüksek kontrastlı bilimsel renk paletine sahip olacaktır.
4. **Doğrulama ve Assert:** Python motoru çalıştırıldığında tüm assert testlerinden `PASS` almalı ve sıfır hata ile `.png` dosyasını diske yazmalıdır.
5. **Notebook Eşleşmesi:** `.ipynb` dosyası, `.md` dosyasındaki 24 hücreyi birebir (18 MD hücresi + 6 Code hücresi) içerecektir.

---

## 🔍 Otomatik Denetim Betiği Rehberi (`verify_standart.py`)

Her günün üretimi bittiğinde bu standart belgesine göre otomatik kontrol çalıştırılır:
- 4 dosyanın varlığı denetlenir.
- `.md` içindeki 24 hücre başlığı regex ile taranır.
- `.ipynb` içindeki hücre sayısı (18 MD, 6 Code) sayılır.
- `.png` dosyasının boyutu ve çözünürlüğü teyit edilir.
- `.py` dosyası çalıştırılarak `verify_all()` fonksiyonunun `PASS` verdiği onaylanır.
