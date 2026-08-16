"""P3 hedef dubası OpenCV tespiti — senaryo testleri (kamera GEREKMEZ).

Kural 3: kod yazmadan önce *"ya şöyle olursa?"*. Buradaki her test, sahada
karşılaşacağımız bir yanlış-pozitif ya da kaçırma senaryosunu kapatıyor.
Sentetik kareler bellekte üretilir — gerçek görüntüye bağımlılık yok.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
np = pytest.importorskip("numpy")
cv2 = pytest.importorskip("cv2")

from p3_hedef.hedef_bul import Ayar, hedef_bul  # noqa: E402

# BGR — RAL 3026 kırmızı · RAL 6037 yeşil · RAL 9005 siyah
KIRMIZI = (33, 45, 255)
YESIL = (57, 143, 0)
SIYAH = (10, 10, 10)
SU = (150, 120, 95)          # mavimsi-gri su


def _kare(renk=None, yaricap=40, merkez=None, zemin=SU, boyut=(360, 480)):
    """Su zemininde tek dairesel cisim — duba vekili."""
    im = np.zeros((boyut[0], boyut[1], 3), np.uint8)
    im[:, :] = zemin
    im[: boyut[0] // 3, :] = (200, 180, 160)        # gökyüzü şeridi
    if renk is not None:
        cx, cy = merkez or (boyut[1] // 2, boyut[0] * 2 // 3)
        cv2.circle(im, (cx, cy), yaricap, renk, -1)
    return im


@pytest.mark.parametrize("renk,ad,kod", [(KIRMIZI, "kirmizi", 1),
                                         (YESIL, "yesil", 2),
                                         (SIYAH, "siyah", 3)])
def test_uc_hedef_rengi_de_bulunur(renk, ad, kod):
    """🔴 Siyah dahil — karar tarafının dosyasında siyah dedektörü YOKTU,
    şartnamenin üç renginden biri (RAL 9005) hiç görülemiyordu."""
    adaylar = hedef_bul(_kare(renk))
    assert any(a.renk == ad for a in adaylar), f"{ad} bulunamadi"
    assert next(a for a in adaylar if a.renk == ad).kod == kod


def test_bos_giris_cokmez():
    """Tanı/algı kodu görevi ASLA öldürmemeli."""
    assert hedef_bul(None) == []
    assert hedef_bul(np.zeros((0, 0, 3), np.uint8)) == []


def test_bos_sahnede_tespit_yok():
    assert hedef_bul(_kare(None)) == []


def test_serit_elenir():
    """Yol çizgisi / dalga izi / direk gölgesi — uzun-ince cisim duba değil."""
    im = _kare(None)
    cv2.rectangle(im, (60, 250), (420, 274), YESIL, -1)      # en/boy 15
    assert not [a for a in hedef_bul(im) if a.renk == "yesil"]


def test_cok_kucuk_leke_elenir():
    """Uzaktaki gürültü lekesi kilit açmamalı (min alan kapısı)."""
    assert hedef_bul(_kare(KIRMIZI, yaricap=6)) == []


def test_siyah_KOYULUK_ORANI_ile_ayrilir():
    """🔑 Siyah mutlak V eşiğiyle bulunamaz — eşik zemine bağımlıdır.

    Aynı gri cisim: KOYU suda (zemin de koyu) hedef DEĞİL; AÇIK suda hedef.
    Mutlak eşik kullansaydık ikisi de aynı sonucu verirdi.
    """
    gri = (70, 70, 70)
    acik_suda = hedef_bul(_kare(gri, zemin=(190, 170, 150)))
    koyu_suda = hedef_bul(_kare(gri, zemin=(75, 72, 70)))
    assert any(a.renk == "siyah" for a in acik_suda), "acik suda siyah bulunmali"
    assert not any(a.renk == "siyah" for a in koyu_suda), \
        "koyu suda gri cisim hedef sayilmamali (golge/koyu su)"


def test_dusuk_doygunlukta_da_bulunur():
    """F-P.21 (16.07 gerçek donanım): akşamüstü ışıkta dubanın doygunluğu
    S≈29-83 ölçüldü, sabit eşik 120'nin altında kalıp **hiç tespit edilemedi**.
    Doygunluk germesi bunu kurtarmalı."""
    im = _kare(YESIL)
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = (hsv[:, :, 1].astype(np.float32) * 0.22).astype(np.uint8)
    soluk = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    assert any(a.renk == "yesil" for a in hedef_bul(soluk)), \
        "soluk sahnede yesil kayboldu — doygunluk germesi calismiyor"


def test_renge_gore_AYRI_kapilar():
    """Kapılar renge göre ayrı ölçüldü; tek eşik hepsine uymuyor
    (ilk sürümde İHA plakasının 0,72 dolulugu hedefin %81'ini eliyordu)."""
    a = Ayar()
    assert a.kapi["siyah"]["doluluk"] > a.kapi["kirmizi"]["doluluk"]
    assert a.kapi["siyah"]["min_alan"] > a.kapi["yesil"]["min_alan"]


def test_kod_sozlesmesi_renk_kodu_ile_ayni():
    """🔴 DRIFT: bu tablo İHA reposunda ve karar tarafında da yaşıyor.
    Ayrışırsa İHA '3' der, İDA başka rengi avlar — ve bu SESSİZ olur."""
    from p3_hedef.hedef_bul import KOD
    assert KOD == {"kirmizi": 1, "yesil": 2, "siyah": 3}


# ── YOLO VETOSU (16.08.2026) ───────────────────────────────────────────────
def test_yolo_vetosu_kendi_dubamizi_eler():
    """Stereo yokken boyut kapısı işlevsiz; kırmızı ayırmıyor (gölgedeki
    turuncumuz RAL 3026 bandında okunuyor). Uçtan uca simülasyonda hakem
    'kırmızı' deseydi 6 bloğun 2'sinde YANLIŞ KİLİT kuruluyordu.
    Ölçüm: gerçek karelerdeki kırmızı adayların **%95'i** YOLO kutusuyla
    örtüşüyor — onlar bizim dubalarımız."""
    im = _kare(KIRMIZI)
    a = hedef_bul(im)
    assert any(x.renk == "kirmizi" for x in a)
    hedef = next(x for x in a if x.renk == "kirmizi")
    veto = [(hedef.cx, hedef.cy, hedef.w, hedef.h)]
    assert not hedef_bul(im, veto_kutulari=veto), "YOLO kutusuyla ortusen aday elenmeli"


def test_yolo_vetosu_UZAKTAKI_hedefi_elemez():
    """Gerçek hedef YOLO kutusuyla örtüşmez (model onu görmemeyi öğrendi)."""
    im = _kare(YESIL, merkez=(360, 250))
    uzak_veto = [(60.0, 250.0, 40.0, 40.0)]      # baska yerde bir duba
    assert any(x.renk == "yesil" for x in hedef_bul(im, veto_kutulari=uzak_veto))


def test_veto_verilmezse_davranis_AYNI():
    """Geri uyum: veto yoksa eski davranış bit birebir."""
    im = _kare(YESIL)
    assert len(hedef_bul(im)) == len(hedef_bul(im, veto_kutulari=None))


# ── PARKUR-3 KAPISI ────────────────────────────────────────────────────────
@pytest.mark.parametrize("durum", ["BEKLEMEDE", "PARKUR1", "PARKUR2",
                                   "TAMAMLANDI", "KILL", "", None])
def test_p3_disinda_hic_calismaz(durum):
    """P1/P2'de hedef tespiti anlamsız (`nisan_hedefi` zaten None döner) ⇒
    hesap yapılıp atılıyordu. Koşmayan kod yanlış pozitif de üretemez."""
    from p3_hedef.hedef_bul import hedef_bul_p3
    assert hedef_bul_p3(_kare(YESIL), durum) == []


def test_p3te_calisir():
    from p3_hedef.hedef_bul import hedef_bul_p3
    assert any(a.renk == "yesil" for a in hedef_bul_p3(_kare(YESIL), "PARKUR3"))


def test_kapi_buyuk_TESPITI_ayni_birakir():
    """Kapı yalnız P3 zincirine; `hedef_bul` (algının kullandığı) DEĞİŞMEZ."""
    from p3_hedef.hedef_bul import hedef_bul_p3
    assert len(hedef_bul(_kare(KIRMIZI))) == len(hedef_bul_p3(_kare(KIRMIZI), "PARKUR3"))
