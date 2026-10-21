# GTA LIVE V8 — GitHub Pages, orijinal V7 tasarımı korunarak

Bu proje **ücretsiz GitHub Pages** üzerinde çalışır. 97 kanal adı ve sponsor bilgisi `channels.json` içindedir. Önceki sürümlerde kullanılan ve kullanıcı tarafından istenmeyen **“Kick’te izle”** ve **“Yayın videoları”** düğmeleri kaldırıldı. **Kanal adına tıklamak** yine Kick kanalına gider.

## Ne değişti?

- **Canlı oynatıcı otomatik açılır:** Kartı ekranda görünen ve `live` durumu başarıyla doğrulanmış kanalın `https://player.kick.com/KANAL?autoplay=true&muted=true` iframe'i tıklama gerektirmeden açılır.
- **API durum bilgisi eksikse:** Üstteki **“Durumu bilinmeyen kanalları da dene”** seçeneği varsayılan olarak açıktır. Bu, mevcut durum yanlış/eksik olsa bile görünür kartlarda oynatıcıyı deneyebilir; çevrimdışı kanallar için yayın garanti değildir.
- **Performans:** Görünür alandaki **en fazla 4 otomatik** iframe aynı anda çalışır. Aşağı kaydırınca artık görünmeyen *otomatik* iframe kapatılır ve alttaki açılır. Kullanıcının **elle** açtığı oynatıcılar kaydırma nedeniyle kapatılmaz. Bu sınır bilinçlidir: 97 videonun aynı anda açılması bilgisayar ve interneti aşırı yorar.
- **İsteğe bağlı kapatma:** “Otomatik oynat” kutusunu kapatınca yalnız otomatik iframe'ler durur. Oynatıcının **✕ Kapat** düğmesi kullanıcı kapatmışsa aynı kartı otomatik tekrar başlatmaz; **Yayını aç** ile elle açabilirsin.
- **Profil fotoğrafları:** Tarayıcıda önce GitHub Pages'teki `assets/avatars/` önbelleği, sonra Kick API'den gelen profil resmi, sonra eski CDN adresi denenir. İş akışı, güvenli biçimde doğrulayabildiği fotoğrafları `avatar_cache.py` ile statik dosyalara kaydeder. Üçü de erişilemiyorsa doğru resim **uydurulmaz**, isim baş harfleri görünür.
- **Canlılık:** Doğrulanmamış API hatası çevrimdışı sayılmaz. Resmî Kick API entegrasyonu `kick_official.py`, eski uç nokta (erişirse) `kick_legacy.py` ile korunur.
- Arama, favori, filtre, sıralama, son yayın tarihleri ve sponsor kartı korunur.

## GitHub deposuna yükleme

1. ZIP'i aç ve içindeki dosyaları mevcut `gta5` depo köküne kopyala. **Gizli `.github` klasörünü de** kopyala.
2. VS Code Terminal'de:

```powershell
git add -A
git commit -m "GTA LIVE V8 otomatik yayin ve profil goruntuleri"
git push origin main
```

3. Depo **Settings → Pages → Source: GitHub Actions** olmalı.
4. **Actions → GTA LIVE — Pages V8 → Run workflow** ile çalıştır (veya `main` push ile otomatik çalışır).
5. `https://keem-piu.github.io/gta5/` adresinde `Ctrl+Shift+R` ile yenile.

### Gerçek canlı durum ve profil resimleri için

GitHub deposu **Settings → Secrets and variables → Actions** kısmında Kick geliştirici panelinden aldığın iki secret bulunmalı:

- `KICK_CLIENT_ID`
- `KICK_CLIENT_SECRET`

Bu değerleri hiçbir zaman `index.html`, `app.js`, `channels.json` veya herkese açık `data/streamers.json` dosyasına yazma. İki secret yoksa GitHub Actions eski gayriresmî Kick endpoint'ini dener; Kick bunu 403/429 ile engelleyebilir. Böyle bir durumda **durumu bilinmeyenler için otomatik oynatmayı dene** seçeneği çalışır, ancak API'den doğrulanmamış izleyici sayıları ve profil fotoğrafları üretilmez.

### Fotoğraflar hâlâ eksikse

`data/streamers.json` içindeki `profileImage` ve `avatarCached` değerlerini kontrol et. İkisi de boşsa ve CDN resmi açılmıyorsa Kick o kanalın resmine site dışından erişim sağlamamış demektir; yalnız CSS/JavaScript bunu çözemez. `assets/avatars/` içinde görsel dosyaları olanlar Pages üzerinden doğrudan yüklenir. İstersen yasal kullanabileceğin kanal görsellerini aynı adla (`kanal.webp`, `kanal.png` veya `kanal.jpg`) bu klasöre kendin ekleyebilirsin, ancak bu dosyaların yolu `data/streamers.json` içindeki `avatarCached` alanında da işaretlenmelidir.

## Gerçek Kick videosu hakkında

Bu proje Kick'in resmî iframe adresini kullanır. `autoplay=true&muted=true` parametreleri Kick yardım merkezinde belgelidir. Ancak üçüncü taraf oynatmayı Kick, tarayıcı engelleyicisi, çerez politikası veya ağ engelleyebilir. **GitHub Pages üzerinden gerçek Kick video akışının başladığı bu ortamda doğrulanamadı.**

Son durum verisi yaklaşık saatlik GitHub Actions kontrolünden gelir; saniye saniye gerçek zamanlı değildir. Oynatıcı sayfa görünür olduğunda açılmaya *çalışır*, medya akışı sağlayıcının kontrolündedir.

## Yerelde çalıştırma

```powershell
py -m http.server 8080
```

`http://localhost:8080` adresini aç. Python gerekmiyorsa VS Code Live Server da kullanılabilir.

## Kontroller

```powershell
py -m unittest discover -s tests -v
py build_pages.py
```

`tests/browser_v8.py` kontrollü/sahte Kick yanıtlarıyla çalışır ve Playwright/Chromium gerektirir. Bu tarayıcı testi gerçek Kick videolarını doğrulamaz.

## Güvenlik ve dosyalar

- `.github/workflows/publish.yml`: Actions API güncellemesi, resim önbelleği, Pages deploy.
- `update_snapshot.py`: Önceki geçerli fotoğraf/tarihleri korur; API başarısızlığını `unknown` yapar.
- `avatar_cache.py`: Yalnız izin verilen Kick görsel sunucularından sınırlı boyutlu dosyaları indirir; uygunsuz içerik kaydetmez.
- `build_pages.py`: Yalnız statik HTML/JS/JSON ve avatarları yayımlar; Python/secret dosyaları sunulmaz.
- `ORIJINAL_KAYNAK/`: Kullanıcının orijinal projesi, karşılaştırma için.
