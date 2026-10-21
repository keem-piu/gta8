# V8 — Görünür kanallarda otomatik video ve fotoğraf dayanıklılığı

Kaynak: V7 ZIP. Orijinal 97 kanal, HTML/CSS kart temeli, Kick embed URL'si ve API katmanı korundu.

## Kanıtlanmış V7 davranışı

- `makeCard()` profil resmini API alanı yoksa yalnız eski CDN adresinden yükler; başarısız resimde baş harfleri gösterir.
- V7 `openPlayer()` sadece `Yayını aç` butonuna basıldığında çağrılır.
- Her kartta kanal adının bağlantısına ek olarak iki dış bağlantı daha vardır.

## V8 kod değişiklikleri

- `app.js`: Görünür kartları `IntersectionObserver` ile takip eden oynatıcı yöneticisi. Otomatik canlı yayın açılır. İsteyen kullanıcı bilinmeyen kanalları da dener. Aynı anda en fazla dört otomatik iframe. Elle açılan iframe'e müdahale edilmez; kapatılan oynatıcı yeniden zorla açılmaz.
- `app.js`: Kanal adına zaten link verildiği için duplicate Kick/Video düğmeleri silindi.
- `app.js`: Profil resmi deneme sırası: yerel cache → API'den sağlanan HTTPS URL → Kick CDN. Son aday da başarısızsa baş harfleri görünür. İmaj kaynağı değişince yeniden denenir; aynı kaynakla sonsuz hata döngüsü oluşmaz.
- `avatar_cache.py`: Her GitHub Actions çalışmasında kullanılabilir/izinli Kick görsellerini boyut ve dosya imzası doğrulaması ile indirip `assets/avatars` altına yazar; istek başarısızlığında eski görsel korunur.
- `.github/workflows/publish.yml`, `build_pages.py`, `update_snapshot.py`: Fotoğraf dosyalarının Actions üzerinden kalıcı saklanması ve statik Pages yayını.
- `index.html`: Oynatmayı ve bilinmeyenleri denemeyi kontrol etmek için iki seçenek.

## Test seviyesi

- Python 16/16 testi: resmi API ayrıştırma, legacy ayrıştırma, hatalarda unknown, fotoğraf cache şeması/sürdürme, URL ve imza denetimi.
- Kontrollü Chromium + Playwright: 97 kart, canlı durumunda otomatik iframe oluşturma, bilinmeyen kanala otomatik deneme, kullanıcı kapattıktan sonra açılmama, otomatik açmayı kapatma, manuel açma, gereksiz link olmaması, JS istisnası olmaması.
- Node sözdizimi kontrolü ve Pages üretim dosyası allowlist kontrolü geçti.

## Gerçekten doğrulanmayanlar

- Gerçek Kick oynatıcısının video/ses akışı. Test tarayıcısında dış URL'lere erişim idari politikayla engelleniyor.
- Resmi Kick API/GitHub Actions hesap bilgilerinin kullanıcı hesabında doğru kurulumu.
- 97 kanalın tümünde profil fotoğrafına erişim. Bazı Kick görüntü URL'leri servis sağlayıcı kaynaklı kısıtlı veya hiç bulunmayabilir.
