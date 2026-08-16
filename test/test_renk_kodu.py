"""Renk kodu sözleşmesi — 16.08.2026'da bulunan SESSİZ hatanın regresyonu.

Arkadaşın taslağında tablo TERSTİ (1=siyah 2=kırmızı 3=yeşil); bizim üç
repomuzda 1=kırmızı 2=yeşil 3=siyah. İHA "1" gönderip siyah demek isterken
İDA kırmızı hedefe saldırırdı — hata basılmadan. TS3: 100 → 50 → 5.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from p3_hedef.renk_kodu import (ETIKET, IMZA, KOD_RENK, RENK_KOD,  # noqa: E402
                                dogrula, kod_dogru_mu)


def test_kanonik_tablo():
    """🔴 Bu sayılar üç repoda daha yaşıyor — değiştiren hepsini değiştirmeli."""
    assert KOD_RENK == {0: None, 1: "kirmizi", 2: "yesil", 3: "siyah"}
    assert RENK_KOD == {"kirmizi": 1, "yesil": 2, "siyah": 3}
    assert IMZA.endswith("1=kirmizi,2=yesil,3=siyah")


def test_arkadasin_TERS_tablosu_yakalanir():
    """Asıl regresyon: ters tablo sessizce geçmemeli."""
    ters = {0: None, 1: "siyah", 2: "kirmizi", 3: "yesil"}
    with pytest.raises(ValueError, match="AYRIŞMIŞ"):
        dogrula(ters)


def test_dogru_tablo_gecer():
    dogrula(dict(KOD_RENK))


@pytest.mark.parametrize("kod", [1, 2, 3])
def test_etiket_capraz_dogrulama_tutar(kod):
    assert kod_dogru_mu(kod, ETIKET[kod])


def test_etiket_capraz_dogrulama_CELISKIYI_yakalar():
    """Sürüm ayrışmasının tek görünür kanıtı: sayı ile etiketin çelişmesi."""
    assert not kod_dogru_mu(1, ETIKET[3])      # 1 geldi ama "SIYAH" yazıyor
    assert not kod_dogru_mu(2, "KIRMIZI-RAL3026")


def test_etiketler_RAL_kodunu_tasiyor():
    """Şartname s.18: 3026 kırmızı · 6037 yeşil · 9005 siyah."""
    assert "3026" in ETIKET[1] and "6037" in ETIKET[2] and "9005" in ETIKET[3]


def test_alici_celiskide_karari_GERI_ALIR():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "arac"))
    from ida_renk_al import Dinleyici
    d = Dinleyici(teyit=2)
    d.named_value(1); d.named_value(1)
    assert d.renk_kodu == 1
    assert not d.statustext("HEDEF_RNK=1 SIYAH-RAL9005")   # çelişki
    assert d.renk_kodu == 0, "çelişkide karar geri alınmalı"
    assert d.celiski == 1


def test_alici_tutarli_etikette_karari_KORUR():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "arac"))
    from ida_renk_al import Dinleyici
    d = Dinleyici(teyit=2)
    d.named_value(2); d.named_value(2)
    assert d.statustext(f"HEDEF_RNK=2 {ETIKET[2]}")
    assert d.renk_kodu == 2
