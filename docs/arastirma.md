# P3 araştırma defteri

Ayrıntılı şartname alıntıları, puan tablosu, İHA haberleşme zinciri ve ölçüm
kayıtları memory'de: `pc-memory/parkur3-kamikaze-arastirmasi.md`.
Bu dosya yalnız **koda dönüşen** kararları taşır.

## Neden bu sabitler
- `HEDEF_CAP_M = 0.64` · `HEDEF_YUKSEK_M = 0.95` — şartname s.18 (Ø640×950 mm).
- `KENAR_CAP_M = 0.30` — elenmesi gereken şey; kodda **belge olarak** duruyor.
- `BOYUT_BAND = (0.70, 1.50)` — türetimi:
  0,64 varsayıp gerçek çap D ise oran = 0,64/D.
  `D=0,64→1,00 · 0,55→1,16 · 0,45→1,42 · 0,40→1,60 · 0,30→2,13`
  Üst sınır **2,13'ün altında** kalmalı, yoksa kenar dubası hedef sanılır.
- `RENK_ESIK` — süpürmeden (bkz. README tablosu). Kırmızı bilerek **gevşek**:
  sıkı eşik gerçek hedefi kaçırıyor, yanlışları zaten boyut kapısı eliyor.

## Test edilen senaryolar (test/test_hedef_mantik.py)
kenar dubası hedef sanılmaz (5 mesafede) · gerçek hedef 0,45-0,90 m arasında
kabul · band dışı red · stereo yoksa kör reddetme yok · band üst sınırı 2,13'ün
altında · 3 renk tanınır · bizim turuncu/sarı hedef sayılmaz · gölgeli kırmızı
"siyah" olmaz · en yakın hedef seçilir · **boyut kapısından geçmeyen seçilmez** ·
**hedef yoksa None döner (uydurmaz)**.
