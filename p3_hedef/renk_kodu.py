"""Parkur-3 hedef rengi — **SAYISAL KOD SÖZLEŞMESİ** (tek kaynak).

🔴🔴 NEDEN BU DOSYA VAR (16.08.2026): aynı tablo dört ayrı yerde elle
kopyalanmıştı ve **biri ters yazılmıştı**:

    arkadaşın `iha_renk_gonder.py`/`ida_renk_al.py`:  1=siyah 2=kırmızı 3=yeşil
    bizim üç repomuz:                                1=kırmızı 2=yeşil 3=siyah

İHA "1" gönderip *siyah* demek isterken İDA "1" okuyup **kırmızı hedefe**
saldırırdı — ve **hiçbir hata mesajı çıkmadan**. Şartname s.25: 1 yanlış temas
100 → **50**, 2 yanlış temas 100 → **5**.

Bu, `karar/prototype/mission/renk_kodu.py`'nin kendi uyarısının gerçekleşmesiydi:
*"tablo iki ayrı repoda yaşıyor… ayrışırsa İHA '3' der, İDA başka rengi avlar
ve bu SESSİZ olur."*

⇒ Kural: **tabloyu elle kopyalama, buradan import et.** Kopyalamak zorundaysan
(farklı makine, farklı repo) `dogrula()` çağır — açılışta gürültüyle patlasın,
sahada sessizce yanlış hedefe gitmesin.

Renkler şartname s.18: RAL 3026 (kırmızı) · RAL 6037 (yeşil) · RAL 9005 (siyah).
"""
from __future__ import annotations

from typing import Optional

#: 0 = KARAR YOK, bilerek ayrı değer: operatör *"sistem çalışmıyor"* ile
#: *"renk belirsiz"*i ayırt edebilmeli; İHA emin değilse **susmalı**
#: (yanlış renk bildirmek hiç bildirmemekten pahalı).
KOD_RENK: dict[int, Optional[str]] = {
    0: None,        # karar yok / hedef atanmamış
    1: "kirmizi",   # RAL 3026
    2: "yesil",     # RAL 6037
    3: "siyah",     # RAL 9005
}
RENK_KOD: dict[str, int] = {v: k for k, v in KOD_RENK.items() if v}

#: İnsan-okunur etiket (telemetri/log). Kod ile BİRLİKTE gönderilir ki
#: alıcı **çapraz doğrulayabilsin** — sürüm ayrışması sessiz kalmasın.
ETIKET: dict[int, str] = {
    0: "YOK",
    1: "KIRMIZI-RAL3026",
    2: "YESIL-RAL6037",
    3: "SIYAH-RAL9005",
}

#: Tablonun parmak izi. Kopyalayan taraf bunu doğrular.
IMZA = "p3renk-v1:0=yok,1=kirmizi,2=yesil,3=siyah"


def dogrula(kod_renk: dict) -> None:
    """Kopyalanmış bir tabloyu kanonik olanla karşılaştır; ayrışıksa PATLA.

    Sessiz yanlış eşleme, gürültülü çökmeden **çok** daha pahalıdır.
    """
    if kod_renk != KOD_RENK:
        raise ValueError(
            "RENK KODU SÖZLEŞMESİ AYRIŞMIŞ!\n"
            f"  beklenen: {KOD_RENK}\n"
            f"  gelen   : {kod_renk}\n"
            "  ⇒ İHA ile İDA farklı renk konuşuyor. Yanlış hedefe angajman "
            "TS3'te 100→50 puan (şartname s.25). Tabloyu p3_hedef/renk_kodu.py'ye eşitle."
        )


def kod_dogru_mu(kod: int, etiket: str) -> bool:
    """Gelen (kod, etiket) çifti kendi içinde tutarlı mı?

    🔑 Asıl koruma bu: sayı tek başına sürüm ayrışmasını yakalayamaz, ama
    yanına insan-okunur etiket konursa alıcı çelişkiyi **görebilir**.
    Çelişkide karar: **REDDET** — yanlış renkle angajman, angajman
    yapmamaktan pahalı (100→50 ↔ P3 puanı).
    """
    return ETIKET.get(int(kod)) == (etiket or "").strip()
