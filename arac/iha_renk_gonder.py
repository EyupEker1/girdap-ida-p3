#!/usr/bin/env python3
"""İHA → İDA hedef rengi GÖNDERİCİ (Raspberry Pi / pymavlink, ROS'suz).

Arkadaşın taslağından türetildi; **üç düzeltme** yapıldı, hepsi gerekçeli:

🔴 1. RENK KODLARI TERSTİ. Taslakta 1=siyah 2=kırmızı 3=yeşil; bizim üç
   repomuzda 1=kırmızı 2=yeşil 3=siyah. İHA "1" gönderip *siyah* demek isterken
   İDA **kırmızı hedefe** saldırırdı ve hiçbir hata basılmazdı. Artık tablo
   `p3_hedef.renk_kodu`'dan geliyor — elle kopya YOK.

🔴 2. KOŞU BOYUNCA 5 Hz YAYIN KURAL DIŞI. Şartname s.22: *"Hedef bilgisi İDA
   harekete başladıktan sonra İDA'ya aktarılamaz."* İhlal = **50 ceza puanı**
   (s.26). Ayrıca taslaktaki *"şartname 6.2'de 5 Hz"* dayanağı YOK — şartname
   tam tarandı, 6. bölüm ÖDÜL ve "5 Hz" hiç geçmiyor (geçen tek şart Dosya-1
   için "en az 1 Hz"). ⇒ Yayın artık **KALKIŞ ÖNCESİ**, sınırlı sayıda tekrarla.

🔴 3. "GÖNDERDİM" HİÇBİR ŞEY KANITLAMIYORDU. Taslak seri porta yazıp mutlu
   mesut *"Gonderildi"* basıyordu. Bant/netID tutmazsa (İDA 868, İHA 433 —
   memory 13.08) **tam sessizlik** olur, iki taraf da sağlıklı görünür ve P3
   sıfırlanır. ⇒ Artık İDA'nın HEARTBEAT'i görülmeden gönderim BAŞLAMAZ.

Ayrıca kod ile birlikte **insan-okunur etiket** gönderilir; alıcı ikisini
çapraz doğrular (sürüm ayrışması sessiz kalmasın).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from p3_hedef.renk_kodu import ETIKET, KOD_RENK, RENK_KOD  # noqa: E402


def _mav():
    from pymavlink import mavutil
    return mavutil


def baglan(port, baud, sysid, compid):
    mavutil = _mav()
    m = mavutil.mavlink_connection(port, baud=baud,
                                   source_system=sysid, source_component=compid)
    print(f"[İHA] telemetri açıldı: {port} @ {baud}")
    return m


def ida_duyuluyor_mu(master, ida_sysid: int, saniye: float = 10.0) -> bool:
    """İDA'dan HEARTBEAT bekle — link GERÇEKTEN var mı?

    🔑 Bant/netID uyuşmazlığında hiçbir paket geçmez ama gönderen taraf bunu
    ASLA fark etmez (seri porta yazmak başarılıdır). Tek kanıt: karşıdan
    paket gelmesi.
    """
    bitis = time.time() + saniye
    while time.time() < bitis:
        msg = master.recv_match(type="HEARTBEAT", blocking=True, timeout=1.0)
        if msg is not None and msg.get_srcSystem() == ida_sysid:
            return True
    return False


def renk_gonder(master, kod: int) -> None:
    """Kod + insan-okunur etiketi birlikte gönder (çapraz doğrulama için)."""
    mavutil = _mav()
    zaman_ms = int(time.time() * 1000) & 0xFFFFFFFF
    master.mav.named_value_int_send(zaman_ms, b"HEDEF_RNK", int(kod))
    # Etiket, alıcının kodu doğrulamasını sağlar — sürüm ayrışması yakalanır.
    master.mav.statustext_send(
        mavutil.mavlink.MAV_SEVERITY_INFO,
        f"HEDEF_RNK={kod} {ETIKET[kod]}".encode("ascii", "ignore")[:50],
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("renk", choices=sorted(RENK_KOD), help="tespit edilen hedef rengi")
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=57600)
    ap.add_argument("--iha-sysid", type=int, default=2)
    ap.add_argument("--iha-compid", type=int, default=191)
    ap.add_argument("--ida-sysid", type=int, default=1)
    ap.add_argument("--tekrar", type=int, default=20,
                    help="kaç kez gönderilsin (2 Hz). Koşu BAŞLAMADAN ÖNCE!")
    ap.add_argument("--link-yok-devam", action="store_true",
                    help="İDA duyulmasa da gönder (yalnız masa testi için)")
    a = ap.parse_args(argv)

    kod = RENK_KOD[a.renk]
    master = baglan(a.port, a.baud, a.iha_sysid, a.iha_compid)

    print("[İHA] İDA'nın heartbeat'i bekleniyor (link kanıtı)...")
    if not ida_duyuluyor_mu(master, a.ida_sysid):
        print("🔴 İDA DUYULMUYOR. Paket gitmiyor olabilir — bant/netID/baud "
              "uyuşmazlığında hiçbir hata basılmaz, iki taraf da sağlıklı görünür.\n"
              "   Kontrol: iki modül aynı frekans BANDINDA mı (868 ↔ 433 konuşmaz), "
              "netID ve air-rate aynı mı, baud aynı mı.\n"
              "   Yedek yol KURAL DIŞI DEĞİL: rengi operatör koşudan ÖNCE elle girer "
              "(şartname s.22 buna izin veriyor).")
        if not a.link_yok_devam:
            return 2

    print(f"[İHA] gönderiliyor: {a.renk} → kod {kod} ({ETIKET[kod]})")
    for i in range(a.tekrar):
        renk_gonder(master, kod)
        time.sleep(0.5)
    print(f"[İHA] {a.tekrar} tekrar gönderildi. "
          "🔴 KOŞU BAŞLADIKTAN SONRA TEKRAR GÖNDERME (şartname s.22, 50 ceza).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
