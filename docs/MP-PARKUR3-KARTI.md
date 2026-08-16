# PARKUR-3 — Mission Planner Kartı

## 1. Görev dosyası (hakemden USB ile)
- [ ] Dosyayı MP'de **Load WP File** ile aç, araca **Write WPs** ile yaz.
- [ ] **Sadece WAYPOINT** komutu olsun. `RTL` / `LAND` / `DO_JUMP` **SİLİNECEK**.
      Kodumuz onları görev noktası saymaz **ama FC otopilotu ÇALIŞTIRIR** →
      tekne P3'e geçmeden eve döner.
- [ ] `Home` (index 0) MP'nin otomatik eklediği satırdır, silme — kod atlıyor.
- [ ] **P3 için waypoint YOK.** Son waypoint = Parkur-2'nin son noktası.

## 2. Renk yükleme — KALKIŞTAN ÖNCE
- [ ] İHA rengi bulur → operatör İDA'ya girer:
      `ros2 param set /perception_camera_node kamikaze_target_color <renk>`
      kabul edilenler: `kirmizi` · `yesil` · `siyah`
- [ ] Yüklendiğini doğrula: log'da `PARKUR-3 hedef rengi = <renk> (kod N)`
      kod eşlemesi: **1=kırmızı · 2=yeşil · 3=siyah**
- [ ] Renk **boşsa P3 hiç açılmaz** (tekne son noktada temiz durur, P1+P2 korunur).

## 3. Başlatma sonrası — DOKUNMA
- [ ] Başla komutundan sonra **renk gönderilmez/değiştirilmez** (şartname s.22,
      ihlal = **50 ceza**). Kod da reddediyor: PARKUR1/2/3'te `param set` geçmez.
- [ ] YKİ/RC'den başka komut yok (acil motor kesme hariç).

## 4. Koşuda beklenen zincir
```
son waypoint'e varıldı  +  renk yüklü   →  FSM: PARKUR3
PARKUR3'te OpenCV hedef tespiti açılır (öncesinde HİÇ koşmaz)
3 ardışık kare aynı hedef              →  kilit
ileri komut var + ilerleme yok         →  TAMAMLANDI (temas)
```

## 5. Koşu öncesi son kontrol
- [ ] `ros2 topic echo /girdap/mission/state` → `PARKUR1` görünüyor
- [ ] Renk parametresi dolu
- [ ] Görev listesinde RTL yok
- [ ] `sudo systemctl enable --now girdap-algi` yapıldı (yoksa **P1+P2 sıfır**)

---
🔴 **AÇIK MADDE (16.08.2026):** `kamikaze_target_color` parametresini barındıran
tek node `perception_camera_node` idi ve `camera-buoys-kaldirildi` dalında
silindi. O dal birleştirilirse **§2'deki komut çalışmaz** — parametre sahipsiz
kalır. Birleştirmeden önce `KamikazeHedefKapisi` başka bir node'a (fsm_node ya
da planning_node) taşınmalı.
