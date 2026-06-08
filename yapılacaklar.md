# Canlıya Alma Yapılacaklar Listesi

Bu dosya proje yapısını bozmadan, mevcut frontend/backend mimarisini koruyarak canlıya alma adımlarını takip etmek için hazırlanmıştır.

Hedef dağıtım:
- Frontend: Netlify
- Backend: Render
- Veritabanı: Canlı ortamdan erişilebilir MySQL

---

## 1. Mevcut Durumu Sabitle

- [x] Proje klasör yapısı korunacak:
  - `frontend/`
  - `backend/`
- [x] Backend FastAPI olarak kalacak.
- [x] Frontend React + Vite olarak kalacak.
- [x] Skorlama mantığı, OSM veri çekme mantığı ve DB tablo yapısı izinsiz değiştirilmeyecek.
- [x] Önce canlıya alma için gerekli minimum ayarlar yapılacak.

---

## 2. Backend İçin Hazırlık

### 2.1 Veritabanı Ayarlarını Canlıya Uygun Hale Getir

Şu an `backend/db_config.py` içinde veritabanı bilgileri doğrudan yazıyor. Render ortamında bu bilgiler environment variable olarak verilmelidir.

Yapılacaklar:

- [x] `DB_HOST`
- [x] `DB_USER`
- [x] `DB_PASSWORD`
- [x] `DB_NAME`
- [x] `DB_PORT`

değerleri Render environment bölümünden okunacak hale getirilecek.

Not:
Bu adım yapılmadan backend canlıda MySQL'e bağlanamaz.

### 2.2 Canlı MySQL Kararı

Render backend'in bağlanacağı MySQL veritabanı belirlenmeli.

Seçenekler:

- [ ] Railway MySQL
- [ ] Aiven MySQL
- [x] PlanetScale veya benzeri MySQL uyumlu servis
- [ ] Kendi sunucundaki MySQL

Dikkat:
Render'ın canlı backend'i local bilgisayardaki `localhost` MySQL'e bağlanamaz. Bu yüzden canlıdan erişilebilir bir MySQL gerekir.

### 2.3 Backend Başlatma Komutu

Render için backend start command:

```bash
uvicorn api:app --host 0.0.0.0 --port $PORT
```

Kontrol edilecekler:

- [x] `backend/requirements.txt` canlı için yeterli mi?
- [x] `fastapi`, `uvicorn`, `requests`, `mysql-connector-python` mevcut mu?
- [x] Render root directory `backend` olarak ayarlanacak mı?

---

## 3. Backend Render Deploy Adımları

- [x] Proje GitHub'a yüklenecek.
- [x] Render'da yeni Web Service oluşturulacak.
- [x] GitHub repo bağlanacak.
- [x] Root directory olarak `backend` seçilecek.
- [x] Build command:

```bash
pip install -r requirements.txt
```

- [x] Start command:

```bash
uvicorn api:app --host 0.0.0.0 --port $PORT
```

- [x] Environment variables girilecek:
  - `DB_HOST`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_NAME`
  - `DB_PORT`

- [x] Deploy sonrası backend URL alınacak.

Örnek:

```txt
https://yerini-bul-backend.onrender.com
```

---

## 4. Backend Canlı Testleri

Render deploy sonrası şu endpointler test edilecek:

- [x] Ana API ayakta mı?

```txt
https://BACKEND_URL/docs
```

- [x] Şehir listesi geliyor mu?

```txt
https://BACKEND_URL/api/sehirler
```

- [ ] İlçeler geliyor mu?

```txt
https://BACKEND_URL/api/ilceler/İstanbul
```

- [ ] Mahalleler geliyor mu?

```txt
https://BACKEND_URL/api/mahalleler/İstanbul/Kadıköy
```

- [x] Örnek mahalle skoru geliyor mu?

```txt
https://BACKEND_URL/api/mahalle-veri/İstanbul/Kadıköy/Caferağa%20Mah.
```

Dikkat:
İlk mahalle sorgusu OSM/Overpass yüzünden uzun sürebilir.

---

## 5. Frontend İçin Hazırlık

Frontend şu an API adresini `frontend/src/constants/config.js` içinden alıyor:

```js
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
```

Canlıda Netlify environment variable olarak backend URL verilecek:

```txt
VITE_API_URL=https://BACKEND_URL
```

Yapılacaklar:

- [x] Netlify'da `VITE_API_URL` tanımlanacak.
- [x] Değer Render backend URL olacak.
- [ ] Local fallback olan `http://localhost:8000` korunacak.

---

## 6. Frontend Netlify Deploy Adımları

- [x] Netlify'da yeni site oluşturulacak.
- [x] GitHub repo bağlanacak.
- [x] Base directory:

```txt
frontend
```

- [x] Build command:

```bash
npm run build
```

- [x] Publish directory:

```txt
dist
```

Not:
Netlify'da `Base directory` alanı `frontend` ise publish directory `dist` olmalı.
Eğer base directory boş bırakılırsa publish directory `frontend/dist` kullanılabilir.

- [x] Environment variable girilecek:

```txt
VITE_API_URL=https://BACKEND_URL
```

- [x] Deploy alınacak.

---

## 7. CORS Kontrolü

Backend `api.py` içinde CORS şu an local frontend adreslerine izin veriyor.

Canlı Netlify URL de CORS listesine eklenmeli.

Örnek:

```txt
https://yerini-bul.netlify.app
```

Yapılacaklar:

- [x] Netlify canlı URL alınacak.
- [x] Backend CORS `allow_origins` listesine eklenecek.
- [ ] Backend tekrar deploy edilecek.

Not:
Bu yapılmazsa frontend canlıdan backend'e istek atarken tarayıcı CORS hatası verebilir.

---

## 8. Veritabanı Kurulumu

Canlı MySQL hazır olduktan sonra tablolar oluşturulmalı.

Yapılacaklar:

- [x] Canlı DB bilgileri ile backend environment ayarları girilecek.
- [ ] Render shell veya geçici local bağlantı üzerinden:

```bash
python db_setup.py
```

çalıştırılacak.

- [x] `mahalle_score` veritabanı ve tablolar oluştu mu kontrol edilecek.

Tablolar:

- `mahalleler`
- `kategori_verileri`
- `skorlar`
- `kullanici_puanlari`
- `location_cache`

---

## 9. Canlı Uçtan Uca Test

Netlify frontend ve Render backend yayına çıktıktan sonra:

- [x] Netlify site açılıyor mu?
- [x] Şehir dropdown doluyor mu?
- [ ] İlçe dropdown doluyor mu?
- [ ] Mahalle dropdown doluyor mu?
- [ ] İki mahalle seçilip karşılaştırma başlıyor mu?
- [ ] Loading ekranı görünüyor mu?
- [ ] Sonuç kartları geliyor mu?
- [ ] Radar chart ve bar chart görünüyor mu?
- [ ] Yaklaşık alan uyarısı gerekiyorsa görünüyor mu?
- [ ] Backend loglarında hata var mı?
- [ ] MySQL tablolarına kayıt düşüyor mu?

---

## 10. Gerçekçi Sonuç Kontrolü

Canlı testte özellikle şu alanlara bakılacak:

- [ ] `veri_kaynagi` değeri ne geliyor?
  - `osm_sinir` ise daha güvenilir.
  - `yaklasik_yaricap` ise sonuç temkinli okunmalı.
- [ ] `veri_guveni` değeri ne geliyor?
- [ ] Tesis sayıları mantıklı mı?
- [ ] Aynı mahalle tekrar sorgulanınca cache hızlı dönüyor mu?
- [ ] Çok düşük veya 0 skorlar gerçekten veri yokluğundan mı geliyor?
- [ ] OSM/Overpass hatası olduğunda frontend anlaşılır hata gösteriyor mu?

---

## 11. Son Kontroller

- [ ] `db_config.py` içinde canlı şifre düz yazı kalmayacak.
- [ ] Netlify frontend URL backend CORS listesinde olacak.
- [ ] Render backend URL frontend `VITE_API_URL` içinde olacak.
- [ ] Backend `/docs` sayfası açılıyor olacak.
- [ ] Frontend build hatasız olacak.
- [ ] Gereksiz büyük değişiklik yapılmayacak.
- [ ] Proje sahibi mantığı bozulmadan deploy tamamlanacak.

---

## Önerilen Sıra

1. Canlı MySQL servisini belirle.
2. Backend DB ayarlarını environment variable'a uygun hale getir.
3. Backend'i Render'a deploy et.
4. Backend endpointlerini test et.
5. Frontend'e `VITE_API_URL` ver.
6. Frontend'i Netlify'a deploy et.
7. Netlify URL'i backend CORS listesine ekle.
8. Uçtan uca canlı test yap.
9. Gerçekçi sonuçları örnek mahallelerle kontrol et.
