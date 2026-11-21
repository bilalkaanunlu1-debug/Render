# MEGA FAV — iPhone uyumlu web paneli

Bu depo MEGA FAV'ın FastAPI tabanlı, HTTPS üzerinde çalıştırılabilen üye ve yönetici panelini içerir.

## Mevcut özellikler
- Kurucu hesabı, en fazla dört yönetici ve üye rolleri
- M1–M4 dönemleri ve bağlantı akışı
- Üye oluşturma, etkin/pasif yapma, gönderi bağlantısı ekleme
- iPhone Safari uyumlu görünüm ve ana ekrana ekleme
- Otomatik beğeni/RT veya X API takibi **yapılmaz**

## Kaynak kodu ve Docker kurulumu
Kaynak kodu `bundle/part01.b64` – `bundle/part05.b64` dosyalarına bölünmüş, Brotli ile sıkıştırılmış bir tar arşividir.
`unpack_bundle.py`, kaynak arşivini SHA-256 ile doğrular ve Docker derlemesi sırasında `app.py`, `templates/`, `static/`, `sw.js` dosyalarını çıkarır. `generate_icons.py` iOS ikonlarını üretir.

Yerel çalıştırma:
```sh
docker build -t mega-fav-panel .
docker run --rm -p 8000:8000 -e MEGA_OWNER_USERNAME=kurucu -e MEGA_OWNER_PASSWORD="YOUR_LONG_UNIQUE_PASSWORD" -e MEGA_COOKIE_SECURE=0 -e MEGA_DB_PATH=/data/mega.db mega-fav-panel
```
Bu komut yerel deneme içindir; kalıcı veriye ihtiyaç varsa `/data` için volume bağlanmalıdır.

## Render yayını
`render.yaml` Frankfurt bölgesinde **Starter** web servisi ve **1 GB kalıcı disk** önerir. Bu ücretli olabilir; ücretli kaynaklar açık onay olmadan kurulmaz.

Kurulumda `MEGA_OWNER_PASSWORD` değerini Render'ın güvenli Environment alanında, **en az 12 karakterli güçlü bir parola** olarak girin. Parolayı GitHub'a veya sohbete yazmayın.

Canlı servisin health endpoint'i: `/healthz`.

Bu depo herkese açıksa kaynak kodu da herkese açıktır; hiçbir gerçek kimlik bilgisi depoya konmamalıdır. Panelin gerçek üye kullanımı öncesi güvenlik incelemesi ve düzenli yedekleme gerekir.
