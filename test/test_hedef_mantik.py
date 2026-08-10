"""P3 hedef mantığı — senaryo testleri. Kamera/ROS gerekmez.

Kural 3 (mantık/senaryo avı): kod yazmadan önce "ya şöyle olursa?" — buradaki
her test bir yanlış-angajman senaryosunu kapatıyor. TS3 cezası acımasız
(1 yanlış temas 100→50, 2 yanlış temas 100→5) ⇒ "emin değilsek vurma".
"""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from p3_hedef import hedef_mantik as hm  # noqa: E402

F416 = hm.odak_px(416.0)


def _w(z, cap):
    """`cap` çapındaki cismin `z` metrede kaç piksel geldiği (416 uzayı)."""
    return F416 * cap / z


# ── BOYUT KAPISI — asıl ayırıcı ────────────────────────────────────────────
@pytest.mark.parametrize("z", [3.0, 5.0, 8.0, 12.0, 20.0])
def test_kenar_dubasi_hedef_sanilmaz(z):
    """🔴 P1/P2'nin 0,30 m dubası HEDEF sayılırsa tekne ona çarpar (TS3)."""
    assert hm.boyut_tutarli(z, _w(z, hm.KENAR_CAP_M), F416) is False


@pytest.mark.parametrize("cap", [0.45, 0.55, 0.64, 0.75, 0.90])
def test_gercek_hedef_tolerans_icinde_kabul(cap):
    """Şartname s.17: boyutlar farklı olabilir ⇒ 0,64'e katı bağlanma."""
    z = 10.0
    assert hm.boyut_tutarli(z, _w(z, cap), F416) is True


@pytest.mark.parametrize("cap", [0.35, 0.40, 1.10])
def test_bandin_disi_reddedilir(cap):
    z = 10.0
    assert hm.boyut_tutarli(z, _w(z, cap), F416) is False


def test_stereo_yoksa_kor_reddetme_yapilmaz():
    """Stereo ölçemezse çelişki İDDİA EDİLEMEZ → True. Ama bu KÖR bir kabul:
    o hâlde karar yalnız renge kalır ve renk tek başına yetmiyor (ölçüldü)."""
    assert hm.boyut_tutarli(None, _w(10.0, hm.KENAR_CAP_M), F416) is True
    assert hm.boyut_tutarli(10.0, None, F416) is True


def test_band_kenar_dubasini_paylla_eler():
    """0,30 m duba 2,13 kat sapma verir; üst sınır bunun ALTINDA kalmalı."""
    assert hm.BOYUT_BAND[1] < (hm.HEDEF_CAP_M / hm.KENAR_CAP_M), \
        "üst sınır 2,13'e ulaşırsa kenar dubası hedef sanılır"


# ── RENK ───────────────────────────────────────────────────────────────────
def _yama(h, s, v, n=400):
    return (np.full(n, h), np.full(n, s), np.full(n, v))


def test_kirmizi_hedef_taninir():
    assert hm.renk_sinifla(*_yama(2, 200, 180))[0] == "kirmizi"


def test_yesil_hedef_taninir():
    assert hm.renk_sinifla(*_yama(72, 150, 120))[0] == "yesil"


def test_siyah_hedef_taninir():
    assert hm.renk_sinifla(*_yama(0, 10, 30))[0] == "siyah"


def test_bizim_turuncu_dubamiz_kirmizi_DEGIL():
    """Ölçülen turuncumuz ~22° (OpenCV h≈11) — kırmızı bandının (h≤7) dışında.
    🔴 Ama gölgede %14,8'i kırmızıya düşüyordu ⇒ boyut kapısı ŞART."""
    assert hm.renk_sinifla(*_yama(11, 200, 180))[0] != "kirmizi"


def test_bizim_sari_dubamiz_yesil_DEGIL():
    assert hm.renk_sinifla(*_yama(29, 200, 200))[0] != "yesil"


def test_renkli_eslesme_siyaha_gore_oncelikli():
    """Gölgeli kırmızı hem 'kirmizi' hem 'siyah' tutabilir; renkli kazanmalı,
    yoksa kırmızı hedefe 'siyah' deyip YANLIŞ hedefe angajman olur."""
    h = np.concatenate([np.full(300, 2), np.full(100, 0)])
    s = np.concatenate([np.full(300, 200), np.full(100, 5)])
    v = np.concatenate([np.full(300, 100), np.full(100, 20)])
    assert hm.renk_sinifla(h, s, v)[0] == "kirmizi"


# ── SEÇİM ──────────────────────────────────────────────────────────────────
def test_istenen_renkteki_en_yakin_secilir():
    a = [{"renk": "kirmizi", "z": 12.0, "x": 1.0, "boyut_ok": True},
         {"renk": "kirmizi", "z": 6.0, "x": -1.0, "boyut_ok": True},
         {"renk": "yesil", "z": 3.0, "x": 0.0, "boyut_ok": True}]
    assert hm.hedef_sec(a, "kirmizi")["z"] == 6.0


def test_boyut_kapisindan_gecmeyen_secilmez():
    """🔴 En kritik test: renk doğru ama boyut yanlışsa VURMA."""
    a = [{"renk": "kirmizi", "z": 5.0, "x": 0.0, "boyut_ok": False}]
    assert hm.hedef_sec(a, "kirmizi") is None


def test_hedef_yoksa_None_doner_UYDURMAZ():
    """Yanlış hedefe vurmaktansa hiç vurmamak: TS3=1 bile puanı YARIYA düşürür."""
    a = [{"renk": "yesil", "z": 5.0, "x": 0.0, "boyut_ok": True}]
    assert hm.hedef_sec(a, "kirmizi") is None
    assert hm.hedef_sec([], "kirmizi") is None


# ── MENZİL ─────────────────────────────────────────────────────────────────
def test_menzil_pinhole_dogru():
    assert hm.menzil_genislikten(_w(10.0, hm.HEDEF_CAP_M), F416) == pytest.approx(10.0)


def test_gecersiz_genislik_None():
    assert hm.menzil_genislikten(0.0, F416) is None
    assert hm.menzil_genislikten(-3.0, F416) is None


# ══ TETİK: ne zaman / hangi hızda koşulacak ═══════════════════════════════
from p3_hedef.tetik import P3Tetik, BEKLEME_HZ, AKTIF_HZ  # noqa: E402


def test_baslangicta_bekleme_hizinda_ama_KOR_DEGIL():
    """🔴 Sinyal gelmeden de bakıyoruz — 'yalnız PARKUR3'te çalış' dersek ve
    sinyal hiç gelmezse (bugünkü durum) hedefi hiç aramayız."""
    t = P3Tetik()
    assert t.aktif is False
    # 🪤 KENDİNE REFERANS TUZAĞI: `== BEKLEME_HZ` yazılırsa sabit 0 yapılsa bile
    # test yeşil kalır (11.08 mutasyonu yakaladı). MUTLAK alt sınır konur:
    # bekleme hızı 0 olursa sinyal gelmediğinde HİÇ bakmayız = kör kalırız.
    assert t.hz(0.0) > 0.0, "bekleme hızı 0 olamaz — sinyalsizken kör kalırız"
    assert 0.2 <= t.hz(0.0) <= 1.0


def test_parkur3_duyulunca_aktif():
    t = P3Tetik(); t.durum_geldi("PARKUR3", 1.0)
    assert t.aktif and t.hz(1.0) == AKTIF_HZ and "PARKUR3" in t.gerekce


def test_parkur1_2_aktiflestirmez():
    t = P3Tetik()
    t.durum_geldi("PARKUR1", 1.0); t.durum_geldi("PARKUR2", 2.0)
    assert t.aktif is False


def test_hedef_gorulurse_sinyalsiz_de_aktif():
    """Karar tarafı hiç PARKUR3 demese bile: hedefi görüyorsak oradayız."""
    t = P3Tetik(); t.kanit_geldi(5.0)
    assert t.aktif and t.gerekce == "hedef_gorundu"


def test_aktiflik_GERI_DONMEZ():
    """Tek karelik durum bozulması tespiti susturmamalı — hedefe yaklaşırken
    körleşmek angajmanı kaybettirir."""
    t = P3Tetik(); t.durum_geldi("PARKUR3", 1.0); t.durum_geldi("PARKUR2", 2.0)
    assert t.aktif and t.hz(2.0) == AKTIF_HZ


def test_sinyal_kopuklugu_gorunur():
    """Sahada SSH yok; sessiz kopukluk tek görünmez arızadır."""
    t = P3Tetik()
    assert t.sinyal_var_mi(0.0) is False
    t.durum_geldi("PARKUR2", 10.0)
    assert t.sinyal_var_mi(15.0) is True
    assert t.sinyal_var_mi(40.0) is False
