# girdap-ida-p3 — PARKUR-3 (kamikaze angajman) algı katmanı

**Neden AYRI repo:** `girdap-ida-algi` yarışma için donduruluyor (P1/P2 dağıtımı
doğrulandı ve `IDA_GIT` aynasına senkron). P3 farklı donanım/çalışma zamanı
içeriyor (İHA'nın kendi bilgisayarı + İDA'da ayrı bir topic) ve oraya kod
eklemek **çalışan dağıtımı riske atar**. Bu repo `IDA_GIT` aynasına DAHİL DEĞİL.

## Durum
🟡 Çekirdek mantık yazıldı ve test edildi (26 test, mutasyonla doğrulandı).
🔴 Sahaya çıkmadan önce kapatılması gerekenler README sonunda.

### ✅ 17.08.2026 — `hedef_bul.py` ARTIK ENTEGRE
`p3_hedef/hedef_bul.py` **algı node'una bağlandı**: `girdap-ida-algi`
(→ `IDA_GIT/son_kodv2/algi`) içine **kopyalandı** ve
`duba_gecis_navigator._p3_opencv_adaylari` tarafından çağrılıyor; çıktı
`/perception/targets`. Daha önce bu dosyayı **hiçbir node çağırmıyordu**.

🔴 **BU DOSYA KANONİK KAYNAKTIR.** Değişiklik burada yapılır, sonra kopya
(`girdap_ida_algi/p3_hedef_bul.py`) yenilenir ve başlığındaki sha256 güncellenir.
Orada `test_kopya_kanonik_kaynakla_AYNI` ayrışmayı yakalar (bu repo o makinede
yoksa SKIP eder). Şu anki kanonik sha256:
`191d29466097e0ba334e2f612f575a2962daae960f5dc5fc1d639dac8930dd6b`

Neden kopya, `import p3_hedef` değil: Jetson'da bu repo **kurulu bir paket
değil** ve sahada internet/pip **yok** (md 4.1) ⇒ tek `git pull` ile gelen kod
çalışmak zorunda; `sys.path`'e elle dizin eklemek "kurulum adımı unutulursa P3
sessizce ölür" demekti.

📏 **Entegrasyon ölçümleri (17.08, 240 gerçek göl karesi, 512×512, hedef YOK):**
kare başına yanlış aday **vetosuz 0,267 → YOLO vetolu 0,212** ·
`kırmızı 3→0` · `siyah 8→2` · **`yeşil 53→49`**. Maliyet **7,61 ms/kare**
(2 Hz'te koşuyor). 🔴 Yeşil yanlış adayların kaynağı **kıyı bitkisinin su
yüzeyindeki yansıması** (gözle doğrulandı); veto/konum/boyut ayırmıyor
⇒ hakem *"yeşil"* derse yanlış kilit riski en yüksek. Eşikler bilerek
değiştirilmedi — bkz. aşağıdaki süpürme tablosu (0,55→0,62 yanlışı 3 kat
keser, **bulmayı %88→%73 düşürür**); gerçek hedef karesi olmadan bu takas
tek taraflı verilmez.

## Kritik karar: **renk aday üretir, BOYUT karar verir**
10.08.2026 ölçümleri (gerçek veri, 2.087 kare / 5.166 kutu):

| bulgu | sayı |
|---|---|
| Naif "kırmızı" eşiği turuncu KENAR dubalarımızda patlıyor | **%14,8-31,6** (eşiğe göre) |
| Yanlış ateşlemeyi %0,1'e indiren eşik gerçek hedefi de düşürüyor | **%41'e** |
| Siyah (RAL 9005) eşiği tipik karenin kapladığı alan | **%14,8** |
| YOLO'muz kırmızıya boyanmış dubayı görüyor ve "kenar" diyor | **793/909** |
| Bbox en/boy oranı ayırıyor mu? | **HAYIR** (bizim 1,41 · hedef 1,48) |
| Boyut ayırıyor mu? | **EVET — 2,13 kat** |

⇒ `boyut_tutarli()` bu reponun kalbi. Stereo menzili ile "0,64 m varsayarak"
hesaplanan pinhole menzili karşılaştırılır; 0,30 m'lik kenar dubası **2,13 kat**
sapma verdiği için elenir. Kabul bandı **[0,70 · 1,50]** ⇒ gerçek çapı
**0,43-0,91 m** olan hedefi kabul eder (şartname s.17 "boyutlar farklı olabilir"),
kenar dubasını **1,42 kat payla** eler.

## Menzil doğruluğu (ölçüldü, 5.166 kutu — modelin GERÇEK bbox hatası taşındı)
| mesafe | bağıl hata | menzil hatası |
|---|---|---|
| 0-5 m | %1,3 | ±0,03 m |
| 5-8 m | %1,6 | ±0,10 m |
| 8-11 m | %2,2 | ±0,21 m |
| 11-15 m | %3,4 | ±0,45 m |
| 15-25 m | %6,4 | ±1,27 m |

416×416 **yeterli**. Hedef 2,13 kat büyük ⇒ aynı mesafede bağıl hata ~yarıya iner.

## 🔴 KAPATILMAMIŞ RİSKLER
| risk | not |
|---|---|
| **Stereo yoksa boyut kapısı çalışmaz** | `boyut_tutarli` kör kabul ediyor (True). Suda stereo sık başarısız ⇒ karar yalnız renge kalır ve renk yetmiyor. |
| **Plaka rengi/boyutu DSB** | Şartname s.23 "Daha Sonra Belirlenecek". İHA lens/irtifa seçimi buna bağlı — resmî kanaldan sorulmalı. |
| **İHA telsizi md 4.1 denetimi yapılmadı** | 2,4-2,8 / 5,15-5,85 GHz yasak (RC kumandanın kendisi serbest, **bandı** değil). FPV kesin yasak. |
| **Renk, tekne HAREKET ETMEDEN önce girmeli** | s.22: *"Hedef bilgisi İDA harekete başladıktan sonra İDA'ya aktarılamaz."* Koşu içi röle KURAL DIŞI. |
| **Fiziksel hedef dubamız yok** | Renk eşikleri boyanmış sentezle sınandı; gerçek RAL yüzeyinde doğrulanmadı. |
