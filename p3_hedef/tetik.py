"""P3 tespitinin NE ZAMAN ve HANGİ HIZDA koşacağı — saf mantık.

Eyüp (11.08): *"P3'e geçince OpenCV otomatik açılsın."* ✅ — ama tek şartla:
**sinyal hiç gelmezse sessiz kalmasın.**

🔴 NEDEN: `/girdap/mission/state` bugün PARKUR3'e **hiç geçmiyor** — FSM'in tek
tetiği (`/perception/gate_passed`) P2'yi kırdığı için bilerek kapalı. Düzeltilene
kadar da geçmeyecek. "Yalnız sinyal gelince çalış" dersek ve sinyal gelmezse
hedefi hiç aramamış oluruz ⇒ 145 puan sessizce gider.
Aynı hata ailesi: bir güvenlik şartı, sağlanmadığında sistemi KİLİTLİYORSA o
şart güvenlik değil kilittir (11.08 dersi — `gate_count ≥ 2` VE'lemesi geri alındı).

⇒ ÇÖZÜM: **iki hız.** Süreç hep ayakta:
  · BEKLEME  — 0,5 Hz, maliyeti yok denecek kadar az, ama KÖR DEĞİLİZ
  · AKTİF    — 5 Hz, PARKUR3 duyulunca ya da kanıt görülünce

Ölçülen maliyet (11.08): P3 pası Jetson'da ~10,5 ms/kare tahmini.
0,5 Hz ⇒ tek çekirdeğin **%0,5'i** · 5 Hz ⇒ **%5'i**. İkisi de ayrı süreçte,
algı node'unun kare bütçesine hiç girmiyor.
"""
from __future__ import annotations

BEKLEME_HZ = 0.5
AKTIF_HZ = 5.0
#: Bu kadar saniye HİÇ durum mesajı gelmezse "sinyal yok" sayılır (yayıncı
#: yok ya da domain uyuşmuyor). Kör kalmamak için bekleme hızında sürülür.
SINYAL_ZAMAN_ASIMI_S = 20.0


class P3Tetik:
    """Hangi hızda koşmalıyız? Tek yönlü: aktifleşince geri dönmez.

    Neden tek yönlü: P3 son parkur, geri dönüş yok. Durum mesajı tek karelik
    bozulsa (DDS paketi düştü, FSM anlık başka durum bastı) tespit susmamalı —
    hedefe yaklaşırken körleşmek angajmanı kaybettirir.
    """

    def __init__(self) -> None:
        self._aktif = False
        self._son_durum = None
        self._son_mesaj_t = None
        self._gerekce = "baslangic"

    # ---------------------------------------------------------------- girdi
    def durum_geldi(self, durum: str, t: float) -> None:
        """`/girdap/mission/state` mesajı (PARKUR1/PARKUR2/PARKUR3/…)."""
        self._son_durum = durum
        self._son_mesaj_t = t
        if durum and durum.upper().replace("_", "") in ("PARKUR3", "TAMAMLANDI"):
            if not self._aktif:
                self._gerekce = f"durum={durum}"
            self._aktif = True

    def kanit_geldi(self, t: float) -> None:
        """Boyut kapısından geçmiş bir HEDEF görüldü (0,64 m'lik cisim).

        Karar tarafının sinyali hiç gelmese bile bu tek başına aktifleştirir:
        hedefi görüyorsak P3 bölgesindeyiz demektir. Sinyale bağımlılığı kırar.
        """
        if not self._aktif:
            self._gerekce = "hedef_gorundu"
        self._aktif = True

    # ---------------------------------------------------------------- çıktı
    def hz(self, simdi: float) -> float:
        return AKTIF_HZ if self._aktif else BEKLEME_HZ

    @property
    def aktif(self) -> bool:
        return self._aktif

    @property
    def gerekce(self) -> str:
        return self._gerekce

    def sinyal_var_mi(self, simdi: float) -> bool:
        """Karar tarafından durum mesajı akıyor mu? Akmıyorsa journal'a
        basılmalı: sahada SSH yok, sessiz kopukluk tek görünmez arızadır."""
        if self._son_mesaj_t is None:
            return False
        return (simdi - self._son_mesaj_t) <= SINYAL_ZAMAN_ASIMI_S
