#!/usr/bin/env python3
"""FAZ 0 — Jetson kapasite ölçümü. TEK KOMUT, NET HÜKÜM.

    python3 arac/jetson_kapasite_olc.py

Neden: PC'de (i7-13620H @4,9 GHz) ölçtük — MPPI boru hattı adımı **85,8 ms**,
yani 10 Hz bütçesinin %86'sı. Orin Nano 1,5 GHz'te bunun kaç katı olduğunu
TAHMİN etmiyoruz, ÖLÇÜYORUZ. Kural 6: ölçüm kaynaktan üstündür.

Betik hiçbir şeyi değiştirmez — yalnız okur ve ölçer. ROS koşuyorsa canlı
topic hızlarını da alır; koşmuyorsa o bölümü atlar.

PC referansları (16.08.2026, i7-13620H, numpy, tek süreç):
    MPPI boru hattı adımı ... 85,81 ms  (ort)   p95 94,19   maks 104,75
    RRT* plan (8 duba) ...... 303,6 ms
    P3 OpenCV @640x480 ......   7,38 ms
    iSAM2 @6000 key .........   1,61 ms/güncelleme
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time

PC = {  # bu PC'de ölçülen referanslar (ms)
    "mppi_adim": 85.81,
    "rrt_plan": 303.6,
    "opencv_640": 7.38,
    "isam2_6000": 1.61,
}
BUTCE_MS = 100.0  # 10 Hz kontrol döngüsü


def bas(s: str = "") -> None:
    print(s, flush=True)


def baslik(s: str) -> None:
    bas("\n" + "=" * 72)
    bas(s)
    bas("=" * 72)


def kabuk(cmd: str, zaman_asimi: int = 10) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=zaman_asimi).stdout.strip()
    except Exception as e:  # noqa: BLE001 — tanı betiği asla ölmemeli
        return f"(alinamadi: {e})"


# ───────────────────────────── 1. DONANIM / GÜÇ ─────────────────────────────
def donanim() -> None:
    baslik("1. DONANIM VE GUC MODU")
    model = "(yok)"
    for p in ("/proc/device-tree/model", "/sys/firmware/devicetree/base/model"):
        if os.path.exists(p):
            model = open(p, "rb").read().decode(errors="ignore").strip("\x00")
            break
    bas(f"  Model      : {model}")
    bas(f"  Mimari     : {platform.machine()}   Cekirdek: {os.cpu_count()}")

    if shutil.which("nvpmodel"):
        q = kabuk("nvpmodel -q 2>/dev/null")
        bas(f"  Guc modu   : {q or '(okunamadi)'}")
        if "15W" not in q and "MAXN" not in q.upper():
            bas("  🔴 15W/MAXN DEGIL — CPU frekansi kisitli. Once:")
            bas("       sudo nvpmodel -m 0 && sudo jetson_clocks")
            bas("     (olcumu MUTLAKA bu ayarda tekrarla, yarisma da boyle kossun)")
    else:
        bas("  Guc modu   : nvpmodel yok (Jetson degil mi?)")

    freqler = kabuk("cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq "
                    "2>/dev/null | sort -rn | head -1")
    if freqler.isdigit():
        bas(f"  CPU tepe   : {int(freqler)/1e6:.2f} GHz")
    gov = kabuk("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null")
    if gov:
        bas(f"  Governor   : {gov}"
            + ("   🔴 'schedutil/powersave' ise jetson_clocks calistir"
               if gov != "performance" else ""))

    sicak = kabuk("cat /sys/devices/virtual/thermal/thermal_zone*/temp 2>/dev/null")
    if sicak:
        t = [int(x) / 1000 for x in sicak.split() if x.strip().isdigit()]
        if t:
            bas(f"  Sicaklik   : maks {max(t):.1f} °C"
                + ("   🔴 KISMA RISKI" if max(t) > 80 else ""))


# ───────────────────────────── 2. CUPY ─────────────────────────────
def cupy_kontrol() -> bool:
    baslik("2. CUPY (MPPI'nin GPU arka ucu)")
    try:
        import cupy  # noqa: PLC0415
        n = cupy.cuda.runtime.getDeviceCount()
        a = cupy.arange(1_000_000, dtype=cupy.float32)
        cupy.cuda.runtime.deviceSynchronize()
        t = time.perf_counter()
        for _ in range(20):
            (a * 2.0).sum()
        cupy.cuda.runtime.deviceSynchronize()
        bas(f"  ✅ cupy {cupy.__version__} CALISIYOR — {n} cihaz, "
            f"{(time.perf_counter()-t)/20*1e3:.2f} ms/kernel")
        bas("  ⇒ MPPI GPU'da kosabilir. Ama ACILIS LOGUNDA 'backend_adi' "
            "gercekten cupy mi, DOGRULA (mppi.py:81 sessizce numpy'a duser).")
        return True
    except Exception as e:  # noqa: BLE001
        bas(f"  🔴 cupy YOK/BOZUK: {type(e).__name__}: {e}")
        bas("  ⇒ MPPI numpy'da kosuyor. Asagidaki olcum bunun bedelini verir.")
        bas("  ⚠ 4 gun kala 'pip install cupy-cuda12x' DENEME: numpy 2.2.6'yi")
        bas("    surukluyor, scipy/ultralytics/algi yigini kirilabilir.")
        return False


# ───────────────────────────── 3. ÇEKİRDEK ÖLÇÜMLER ─────────────────────────
def _karar_kokunu_bul() -> str | None:
    adaylar = [
        os.path.expanduser("~/IDA_GIT/son_kodv2/karar"),
        os.path.expanduser("~/girdap-decision"),
        "/home/girdap/IDA_GIT/son_kodv2/karar",
    ]
    for a in adaylar:
        if os.path.isdir(os.path.join(a, "prototype", "planning")):
            return a
    return None


def planlama_olc() -> dict:
    baslik("3. PLANLAMA MALIYETI (asil soru)")
    kok = _karar_kokunu_bul()
    if not kok:
        bas("  🔴 karar deposu bulunamadi — yol elle verilmeli.")
        return {}
    bas(f"  Depo: {kok}")
    sys.path.insert(0, kok)
    sonuc = {}
    try:
        import numpy as np  # noqa: PLC0415
        from prototype.planning.pipeline import (  # noqa: PLC0415
            PlanningPipeline, PlanningPipelineConfig)
        from prototype.planning.rrt_star import (  # noqa: PLC0415
            Bounds, CircleObstacle)

        eng = [CircleObstacle(40.0, 4.0, 0.15), CircleObstacle(40.0, -4.0, 0.15),
               CircleObstacle(70.0, 4.0, 0.15), CircleObstacle(70.0, -4.0, 0.15),
               CircleObstacle(55.0, 1.5, 0.30), CircleObstacle(95.0, -2.0, 0.30)]

        for mode in ("mppi", "pid"):
            pp = PlanningPipeline(bounds=Bounds(-30.0, 230.0, -30.0, 230.0),
                                  cfg=PlanningPipelineConfig(control_mode=mode))
            pp.set_mission_state("PARKUR2")
            pp.set_waypoints([(60.0, 0.0), (120.0, 0.0), (180.0, 0.0)])
            pp.set_state(np.array([5.0, 0.0, 0.0, 1.0, 0.0, 0.0]))
            pp.set_obstacles(eng)
            pp.compute_control()                      # ısınma
            s = []
            for i in range(60):
                pp.set_state(np.array([5.0 + i * 0.1, 0.0, 0.0, 1.0, 0.0, 0.0]))
                pp.set_obstacles(eng)
                t = time.perf_counter()
                pp.compute_control()
                s.append((time.perf_counter() - t) * 1e3)
            s = np.array(s)
            sonuc[mode] = dict(ort=s.mean(), p95=float(np.percentile(s, 95)),
                               maks=s.max())
            durum = "✅ SIGIYOR" if s.mean() < BUTCE_MS * 0.6 else (
                "⚠ SINIRDA" if s.mean() < BUTCE_MS else "🔴 BUTCEYI ASIYOR")
            bas(f"  {mode.upper():5s} adim: ort {s.mean():7.2f} ms | "
                f"p95 {np.percentile(s,95):7.2f} | maks {s.max():7.2f}"
                f"   [{durum}]")
            if mode == "mppi":
                kat = s.mean() / PC["mppi_adim"]
                bas(f"        -> bu PC'nin {kat:.2f} KATI "
                    f"(PC: {PC['mppi_adim']:.1f} ms)")
                bas(f"        -> gercek kontrol hizi ~{1000.0/max(s.mean(),1e-6):.1f} Hz "
                    f"(hedef 10 Hz)")
    except Exception as e:  # noqa: BLE001
        bas(f"  🔴 olculemedi: {type(e).__name__}: {e}")
    return sonuc


def opencv_olc() -> None:
    baslik("4. PARKUR-3 OPENCV MALIYETI (yeni eklenen yuk)")
    kok = os.path.expanduser("~/girdap-ida-p3")
    if not os.path.isdir(os.path.join(kok, "p3_hedef")):
        bas("  (girdap-ida-p3 bulunamadi — atlandi)")
        return
    sys.path.insert(0, kok)
    try:
        import cv2  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415
        from p3_hedef.hedef_bul import hedef_bul  # noqa: PLC0415

        def kare(w, h):
            im = np.zeros((h, w, 3), np.uint8)
            im[:, :] = (150, 120, 95)
            im[:h // 3, :] = (200, 180, 160)
            for cx, cy, c in [(w // 3, h * 2 // 3, (33, 45, 255)),
                              (2 * w // 3, h * 3 // 5, (57, 143, 0)),
                              (w // 2, h * 7 // 10, (10, 10, 10))]:
                cv2.circle(im, (cx, cy), max(6, w // 24), c, -1)
            return im

        for w, h in ((640, 480), (416, 320)):
            im = kare(w, h)
            hedef_bul(im)
            t = time.perf_counter()
            for _ in range(20):
                hedef_bul(im)
            ms = (time.perf_counter() - t) / 20 * 1e3
            ek = "" if w != 640 else f"   (PC: {PC['opencv_640']:.2f} ms, " \
                                     f"kat {ms/PC['opencv_640']:.2f})"
            bas(f"  {w}x{h}: {ms:7.2f} ms/kare   10 FPS'te CPU payi "
                f"~%{ms/10:.1f}{ek}")
        bas("  NOT: PARKUR3 disinda hic kosmuyor (hedef_bul_p3 kapisi) — "
            "P1/P2'de bedeli SIFIR.")
    except Exception as e:  # noqa: BLE001
        bas(f"  olculemedi: {type(e).__name__}: {e}")


# ─────────────────────── 4.5 PUANI SIFIRLAYAN KONTROLLER ───────────────────
def puan_kontrolleri() -> list[str]:
    """Kapasiteyle ilgisi YOK ama yapılmazsa puan sıfırlanır.

    Hepsi sessiz arıza: sistem sağlıklı görünür, puan gelmez. Betik sadece
    söylemekle kalmaz, **düzeltme komutunu da basar**.
    """
    baslik("4.5 PUANI SIFIRLAYAN KONTROLLER (kapasiteden bagimsiz)")
    eksik: list[str] = []

    # 1) Algı servisi etkin mi — yapılmazsa P1+P2 = 0, belirti vermeden
    if shutil.which("systemctl"):
        durum = kabuk("systemctl is-enabled girdap-algi 2>&1")
        aktif = kabuk("systemctl is-active girdap-algi 2>&1")
        if durum.startswith("enabled"):
            bas(f"  ✅ girdap-algi: enabled / {aktif}")
        else:
            bas(f"  🔴 girdap-algi: {durum or '(yok)'} / {aktif}")
            bas("     ⇒ YAPILMAZSA P1+P2 = 0. Duzeltme:")
            bas("       sudo systemctl enable --now girdap-algi")
            eksik.append("girdap-algi etkin degil")

        # 2) Veri seti unit'i cihazda kaldıysa boot'ta tek OAK'ı kapar
        vs = kabuk("systemctl list-unit-files 2>/dev/null | grep -i veriseti")
        if vs:
            bas(f"  🔴 girdap-veriseti unit'i HALA KURULU:\n      {vs}")
            bas("     ⇒ Boot'ta kamerayi kapar, algi acilamaz. Duzeltme:")
            bas("       sudo systemctl disable --now girdap-veriseti")
            bas("       sudo rm /etc/systemd/system/girdap-veriseti.service")
            bas("       sudo systemctl daemon-reload")
            eksik.append("girdap-veriseti unit'i duruyor")
        else:
            bas("  ✅ girdap-veriseti unit'i yok")

        # 3) Karar servisi
        kd = kabuk("systemctl is-enabled girdap-karar 2>&1")
        bas(f"  {'✅' if kd.startswith('enabled') else '🔴'} girdap-karar: {kd or '(yok)'}")
        if not kd.startswith("enabled"):
            eksik.append("girdap-karar etkin degil")

    # 4) ROS_DOMAIN_ID — uyusmazsa iki taraf birbirini HIC gormez
    dom = os.environ.get("ROS_DOMAIN_ID")
    if dom == "42":
        bas("  ✅ ROS_DOMAIN_ID=42")
    else:
        bas(f"  🔴 ROS_DOMAIN_ID={dom or '(bos)'} — 42 olmali")
        bas("     ⇒ Uyusmazsa topic kesfi HIC calismaz (sessiz).")
        bas("       echo 'export ROS_DOMAIN_ID=42' >> ~/.bashrc")
        eksik.append("ROS_DOMAIN_ID yanlis")

    # 5) Disk — Dosya-1/2/3 surekli yaziyor; dolarsa teslim eksik = 5 ceza
    df = kabuk("df -h / | tail -1 | awk '{print $5\" dolu, \"$4\" bos\"}'")
    bas(f"  Disk: {df}")
    try:
        yuzde = int(df.split("%")[0])
        if yuzde > 85:
            bas("     🔴 %85 ustu — Dosya-1/2/3 yazamayabilir (her eksik dosya 5 ceza)")
            eksik.append("disk dolu")
    except Exception:  # noqa: BLE001
        pass

    # 6) Model dosyasi
    for yol in ("~/girdap-ida-algi/models/best.pt", "~/best.pt",
                "~/girdap_logs/best.pt"):
        p = os.path.expanduser(yol)
        if os.path.exists(p):
            bas(f"  ✅ model bulundu: {yol} ({os.path.getsize(p)/1e6:.1f} MB)")
            break
    else:
        bas("  ⚠ best.pt bulunamadi (blob ayri olabilir) — elle dogrula")

    return eksik


# ───────────────────────────── 5. CANLI SİSTEM ─────────────────────────────
def canli() -> None:
    baslik("5. CANLI SISTEM (ROS kosuyorsa)")
    if not shutil.which("ros2"):
        bas("  ros2 yok / source edilmemis — atlandi.")
        return
    topics = kabuk("ros2 topic list 2>/dev/null", 20)
    if not topics:
        bas("  Topic yok — sistem kapali. Sistemi acip TEKRAR calistir.")
        return
    for t in ("/mavros/setpoint_velocity/cmd_vel_unstamped",
              "/perception/classified_obstacles",
              "/perception/buoys",
              "/girdap/mission/state"):
        if t in topics:
            out = kabuk(f"timeout 6 ros2 topic hz {t} 2>/dev/null | head -2", 15)
            bas(f"  {t}\n      {out or '(veri akmiyor)'}")
        else:
            bas(f"  {t}\n      🔴 TOPIC YOK")
    bas("\n  🔑 cmd_vel 10 Hz'in ALTINDAYSA teshis dogrulandi.")
    bas("     3 sn'den uzun kesinti = ArduPilot tekneyi DURDURUR.")


# ───────────────────────────── HÜKÜM ─────────────────────────────
def hukum(cupy_var: bool, p: dict) -> None:
    baslik("HUKUM")
    if not p.get("mppi"):
        bas("  Planlama olculemedi — hukum verilemez.")
        return
    ort = p["mppi"]["ort"]
    maks = p["mppi"]["maks"]
    hz = 1000.0 / ort
    bas(f"  MPPI gercek hizi : {hz:.1f} Hz   (adim ort {ort:.0f} ms, maks {maks:.0f} ms)")
    bas(f"  PID  gercek hizi : {1000.0/max(p['pid']['ort'],1e-6):,.0f} Hz "
        f"(adim {p['pid']['ort']:.3f} ms)".replace(",", "."))
    bas("")
    if ort < 60:
        bas("  ✅ MPPI SIGIYOR — control_mode 'mppi' kalsin.")
        bas("     Yine de FAZ 1 sayaclarini ekle: sahada yuk artar.")
    elif ort < 100:
        bas("  ⚠ MPPI SINIRDA — tek basina sigiyor ama LiDAR/algi ile birlikte")
        bas("     asar. Once K'yi dusur (1000 -> 250, ~4x ucuz), yeniden olc.")
        bas("     Duzelmezse PID.")
    else:
        bas("  🔴 MPPI BUTCEYI ASIYOR — 10 Hz kontrol MUMKUN DEGIL.")
        bas("     Yarisma icin guvenli varsayilan:")
        bas("       ros2 launch girdap_decision hardware.launch.py "
            "planning.control_mode:=pid")
        bas("     PID donanimda kanitlanmis cascade heading PID'i; PID modunda")
        bas("     RRT*/MPPI hic KURULMUYOR (pipeline.py:245) => tikanmanin")
        bas("     kaynagi da kalkiyor.")
    if not cupy_var and ort >= 60:
        bas("\n  ⚠ cupy yok. 4 gun kala kurmayi DENEME (numpy 2.x cakismasi).")
        bas("    Kaldiraç K dusurmek ya da PID — ikisi de risksiz.")
    bas("\n  Her halukarda: heartbeat_timeout_s 5,0 -> 2,5 s "
        "(ArduPilot 3 sn'de durduruyor).")


if __name__ == "__main__":
    bas("GIRDAP IDA — JETSON KAPASITE OLCUMU (FAZ 0)")
    bas(f"Zaman: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    donanim()
    c = cupy_kontrol()
    p = planlama_olc()
    opencv_olc()
    eksik = puan_kontrolleri()
    canli()
    hukum(c, p)
    if eksik:
        bas("\n🔴 PUANI SIFIRLAYABILECEK ACIK MADDELER:")
        for e in eksik:
            bas(f"   - {e}")
    bas("\nBitti. Ciktinin TAMAMINI kaydet:")
    bas("  python3 arac/jetson_kapasite_olc.py 2>&1 | tee ~/faz0_olcum.txt")
