"""PARKUR-3 hedef mantığı — saf fonksiyonlar (ROS'suz, kamerasız, test edilebilir).

Şartname (2026 İDA, sha256 09116afe…, s.18/21-23):
  · Hedef dubası: **Ø640 mm × 950 mm**, silindir; renkler RAL 9005 (siyah),
    RAL 3026 (floresan kırmızı), RAL 6037 (saf yeşil).
  · P3 tamamlama: İHA'nın saptadığı renkteki hedefe **fiziksel temas**.
  · TS3 cezası acımasız: 1 yanlış temas 100→50, **2 yanlış temas 100→5**.
  · s.17 uyarısı: *"duba ve engellerin boyut ve renklerinde farklılıklar
    olabilecektir"* ⇒ 0,64'e katı bağlanılmaz, **tolerans bandı** kullanılır.

🔑 TASARIMIN TEMEL BULGUSU (10.08.2026 ölçümleri, `girdap_pc_testleri/`):
**Renk tek başına hedefi seçemez.** Eşik süpürmesinde çalışma noktası yok:
    S>100,V>60  -> turuncu kenar dubalarımızın %31,6'sı "kırmızı" (gerçek hedef %99,7)
    S>190,V>120 -> yanlış %0,1'e iner AMA gerçek hedef de %41'e düşer
Siyah daha kötü: V<55 tipik karenin **%14,8'ini** kaplıyor (koyu su, gölge, kıyı).
⇒ Renk **aday üretir**, kararı **BOYUT** verir.
"""
from __future__ import annotations

import math

# ───────────────────────────── şartname sabitleri ─────────────────────────
HEDEF_CAP_M = 0.64          # Ø640 mm (s.18)
HEDEF_YUKSEK_M = 0.95       # 950 mm
KENAR_CAP_M = 0.30          # P1/P2 dubası — ELENMESİ gereken şey
HFOV_RAD = math.radians(69.0)      # IMX214, OAK-D Lite CAM_A

# ───────────────────────────── boyut kapısı ───────────────────────────────
#: Kabul bandı: (pinhole_menzil / stereo_menzil) bu aralıkta olmalı.
#: NEDEN BU DEĞERLER — 0,64 varsayıp gerçek çap D ise oran = 0,64/D:
#:     D=0,64 -> 1,00   D=0,55 -> 1,16   D=0,45 -> 1,42   D=0,40 -> 1,60
#:     D=0,30 (BİZİM KENAR DUBASI) -> **2,13**   ← eleyeceğimiz şey
#: [0,70 · 1,50] bandı gerçek çapı **0,43-0,91 m** olan hedefi kabul eder,
#: 0,30 m kenar dubasını (2,13) **1,42 kat payla** eler. Şartnamenin "boyutlar
#: farklı olabilir" uyarısına karşı bol pay bırakır ama ayrımı kaybetmez.
BOYUT_BAND = (0.70, 1.50)

# ───────────────────────────── renk eşikleri ──────────────────────────────
#: OpenCV HSV (h 0-179 = derece/2). Ölçülen kendi dubalarımız: turuncu ~22°,
#: sarı ~58° (2.087 kare, 1.965+1.978 insan-etiketli kutu).
#: Kırmızı eşiği BİLEREK gevşek: boyut kapısı zaten yanlışları eliyor; burada
#: sıkı davranmak gerçek hedefi kaçırmak demek (süpürme: S>190 -> hedef %41).
RENK_ESIK = {
    "kirmizi": dict(h=((0, 7), (174, 179)), s=130, v=90),   # RAL 3026 ≈ 3,2°
    "yesil":   dict(h=((62, 85),),          s=80,  v=50),   # RAL 6037 ≈ 143,9°
    "siyah":   dict(h=None,                 s=None, v=-55), # v negatif = ÜST sınır
}
#: Kutu pikselinin bu oranı rengi tutmalı ki "o renk" densin.
RENK_ORANI = 0.25


def odak_px(genislik_px: float, hfov_rad: float = HFOV_RAD) -> float:
    """Pinhole odak (piksel): f = (W/2)/tan(HFOV/2). 416'da f ≈ 302,6 px."""
    return (genislik_px / 2.0) / math.tan(hfov_rad / 2.0)


def menzil_genislikten(w_px: float, f_px: float, cap_m: float = HEDEF_CAP_M):
    """Bilinen çaptan menzil: z = f·D/w. Geçersiz genişlikte None.

    ÖLÇÜLEN DOĞRULUK (10.08, 5.166 eşleşen kutu, modelin GERÇEK bbox hatası
    menzile taşınarak): 0-5 m %1,3 · 5-8 m %1,6 · 8-11 m %2,2 · 11-15 m %3,4 ·
    15-25 m %6,4. Hedef dubası 2,13 kat büyük ⇒ aynı mesafede 2,13 kat fazla
    piksel ⇒ bağıl hata kabaca yarıya iner (20 m'de ~%2).
    """
    if w_px is None or w_px <= 0.0 or f_px <= 0.0:
        return None
    return f_px * cap_m / w_px


def boyut_tutarli(z_stereo, w_px, f_px, band=BOYUT_BAND) -> bool:
    """Bu tespit 0,64 m'lik bir HEDEF olabilir mi? (kenar dubası mı değil mi)

    Stereo menzili ile "0,64 m varsayarak" hesaplanan pinhole menzilini
    karşılaştırır. 0,30 m'lik kenar dubası 0,64 sanılırsa menzil **2,13 kat**
    şişer ⇒ banda düşmez ⇒ elenir.

    🔴 Stereo YOKSA karar VERİLEMEZ → True döner (kör reddetme yapmayız; aynı
    kural `girdap-ida-algi/gecit_mantik.menzil_tutarli`'da da geçerli). Bu
    durumda hedef seçimi yalnız renge kalır ve **riskli**dir — çağıran bunu
    `kaynak` alanıyla görünür kılmalı.
    """
    z_pin = menzil_genislikten(w_px, f_px, HEDEF_CAP_M)
    if z_stereo is None or z_pin is None or z_stereo <= 0.0:
        return True
    oran = z_pin / z_stereo
    return band[0] <= oran <= band[1]


def kapsanan_oran(h, s, v, esik) -> float:
    """Piksel dizilerinin `esik`e uyan oranı. h/s/v numpy dizisi ya da liste."""
    import numpy as np
    h = np.asarray(h); s = np.asarray(s); v = np.asarray(v)
    if esik["h"] is None:                       # siyah: yalnız parlaklık ÜST sınırı
        return float((v < -esik["v"]).mean())
    m = np.zeros(h.shape, bool)
    for lo, hi in esik["h"]:
        m |= (h >= lo) & (h <= hi)
    return float((m & (s > esik["s"]) & (v > esik["v"])).mean())


def renk_sinifla(h, s, v, oran: float = RENK_ORANI):
    """Yamanın P3 rengi: "kirmizi"|"yesil"|"siyah"|None (+ kapsama oranı).

    Birden fazla renk eşiği tutarsa **en yüksek kapsama** kazanır. Siyah en son
    bakılır: düşük parlaklık gölgeli kırmızı/yeşilde de olur, renkli bir eşleşme
    varsa o önceliklidir (yanlış hedefe angajman = TS3, puanı yarıya düşürür).
    """
    skor = {ad: kapsanan_oran(h, s, v, e) for ad, e in RENK_ESIK.items()}
    renkli = {a: k for a, k in skor.items() if a != "siyah" and k > oran}
    if renkli:
        en = max(renkli, key=renkli.get)
        return en, renkli[en]
    if skor["siyah"] > oran:
        return "siyah", skor["siyah"]
    return None, 0.0


def hedef_sec(adaylar, istenen_renk):
    """İHA'nın bildirdiği renkteki EN YAKIN geçerli hedefi seç.

    `adaylar`: (renk, z_m, x_m, boyut_ok) beşlisi yerine sözlük listesi:
        {"renk": str, "z": float, "x": float, "boyut_ok": bool}
    Boyut kapısından geçmeyen aday **hiç değerlendirilmez** — yanlış hedefe
    angajman TS3'ü artırır (1 temas 100→50, 2 temas 100→5).
    En yakını seçilir: temas hedefi, yaklaşma ne kadar kısaysa sapma o kadar az.
    """
    uygun = [a for a in adaylar
             if a.get("boyut_ok", False) and a.get("renk") == istenen_renk
             and a.get("z") is not None and a["z"] > 0.0]
    if not uygun:
        return None
    return min(uygun, key=lambda a: a["z"])
