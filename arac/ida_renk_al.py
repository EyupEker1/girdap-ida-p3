#!/usr/bin/env python3
"""İDA tarafı hedef rengi ALICI (Jetson / pymavlink, ROS'suz).

Arkadaşın taslağından türetildi. Düzeltmeler:

🔴 1. RENK KODLARI TERSTİ (1=siyah 2=kırmızı 3=yeşil idi) — artık tablo
   `p3_hedef.renk_kodu`'dan, elle kopya yok.
🔴 2. ÇAPRAZ DOĞRULAMA: gelen sayının yanında insan-okunur etiket de gelir.
   Çelişirlerse **REDDEDİLİR** — çünkü çelişki, iki ucun farklı sürüm
   konuştuğunun tek görünür kanıtı ve yanlış renkle angajman TS3'te
   100 → 50 puan (şartname s.25).
🪤 3. Taslakta `if b"..." in msg.text.encode() if isinstance(...) else msg.text`
   satırı Python'da yanlış önceliklendiriliyordu (koşullu ifade `in`'den sonra
   bağlanıyor) ⇒ bazı girişlerde TypeError. Düzeltildi.

Çıktı: kod stdout'a **tek satır** basılır (`RENK=2`) ki çağıran betik/operatör
doğrudan `ros2 param set ... kamikaze_target_color` ile yükleyebilsin.

🔴 ŞARTNAME s.22: renk yalnız **görev yüklemesinde ya da başlama komutundan
önce** aktarılabilir. Bu betik koşu sırasında çalıştırılmaz.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from p3_hedef.renk_kodu import ETIKET, KOD_RENK, kod_dogru_mu  # noqa: E402


class Dinleyici:
    """Aynı rengi `teyit` kez üst üste görmeden karar verme.

    Tek paket bozulabilir; ama asıl koruma **etiket çapraz doğrulaması**:
    sayı doğru gelse bile etiket tutmuyorsa iki uç farklı sürümde demektir.
    """

    def __init__(self, teyit: int = 3):
        self.teyit = int(teyit)
        self._aday = None
        self._sayac = 0
        self.renk_kodu = 0
        self.celiski = 0

    def named_value(self, kod: int) -> None:
        if kod not in KOD_RENK:
            return
        if kod == self._aday:
            self._sayac += 1
        else:
            self._aday, self._sayac = kod, 1
        if self._sayac >= self.teyit and kod != 0:
            self.renk_kodu = kod

    def statustext(self, metin: str) -> bool:
        """`HEDEF_RNK=<kod> <ETIKET>` biçimini doğrula. False = ÇELİŞKİ."""
        if "HEDEF_RNK=" not in (metin or ""):
            return True                       # bizi ilgilendirmiyor
        try:
            govde = metin.split("HEDEF_RNK=", 1)[1].strip()
            kod_s, etiket = govde.split(None, 1)
            kod = int(kod_s)
        except (ValueError, IndexError):
            return True                       # bozuk metin — sessizce geç
        if not kod_dogru_mu(kod, etiket):
            self.celiski += 1
            self.renk_kodu = 0                # 🔴 kararı GERİ AL
            self._aday, self._sayac = None, 0
            return False
        return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=57600)
    ap.add_argument("--ida-sysid", type=int, default=1)
    ap.add_argument("--ida-compid", type=int, default=191)
    ap.add_argument("--iha-sysid", type=int, default=2)
    ap.add_argument("--sure", type=float, default=60.0, help="en fazla bekleme (sn)")
    ap.add_argument("--teyit", type=int, default=3)
    a = ap.parse_args(argv)

    from pymavlink import mavutil
    m = mavutil.mavlink_connection(a.port, baud=a.baud,
                                   source_system=a.ida_sysid,
                                   source_component=a.ida_compid)
    print(f"[İDA] dinleniyor: {a.port} @ {a.baud} (en fazla {a.sure:.0f} sn)")
    d = Dinleyici(a.teyit)
    bitis = time.time() + a.sure
    while time.time() < bitis and not d.renk_kodu:
        msg = m.recv_match(blocking=True, timeout=1.0)
        if msg is None or msg.get_srcSystem() != a.iha_sysid:
            continue
        tip = msg.get_type()
        if tip == "NAMED_VALUE_INT":
            ad = msg.name.decode() if isinstance(msg.name, bytes) else str(msg.name)
            if ad.strip("\x00") == "HEDEF_RNK":
                d.named_value(int(msg.value))
        elif tip == "STATUSTEXT":
            ham = msg.text
            metin = ham.decode("ascii", "ignore") if isinstance(ham, bytes) else str(ham)
            if not d.statustext(metin):
                print("🔴 ÇELİŞKİ: gelen kod ile etiket uyuşmuyor — İHA ile İDA "
                      "FARKLI renk tablosu konuşuyor. Karar geri alındı.\n"
                      f"   gelen: {metin!r}\n"
                      "   ⇒ iki tarafı p3_hedef/renk_kodu.py'ye eşitleyin. "
                      "Yanlış renkle angajman TS3'te 100→50 puan (s.25).")

    if not d.renk_kodu:
        print("🔴 RENK ALINAMADI. Link yoksa hiçbir hata basılmaz — bant/netID/"
              "baud uyuşmazlığında tam sessizlik olur.\n"
              "   Yedek yol: rengi operatör koşudan ÖNCE elle girer (şartname s.22).")
        return 2
    print(f"[İDA] TEYİTLİ: {ETIKET[d.renk_kodu]}")
    print(f"RENK={d.renk_kodu}")
    print("   ⇒ yükle:  ros2 param set /perception_camera_node "
          f"kamikaze_target_color {KOD_RENK[d.renk_kodu]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
