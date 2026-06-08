# MahalleScore - Mahalle Kiyaslama Web Uygulamasi

## Proje Ozeti
MahalleScore, Turkiye'deki iki mahalleyi secip yasam olanaklari acisindan karsilastiran bir web uygulamasidir. Kullanici sehir, ilce ve mahalle secimi yapar; sistem secilen mahalleler icin OpenStreetMap verilerini ceker, MySQL'de cache'ler ve 5 ana kategori uzerinden 0-100 arasi skor hesaplar.

Uygulama mantigi Areavibes benzeri bir yaklasima dayanir: mahalle secilir, kategori skorlarina bakilir, iki mahalle grafikler ve detay tablolarla karsilastirilir.

## Kullanici Akisi
1. Kullanici 1. mahalle icin sehir > ilce > mahalle secer.
2. Kullanici 2. mahalle icin ayni secimi yapar.
3. "Kiyasla" butonuna basilir.
4. Frontend, backend'deki detay endpoint'ine iki mahalle icin sirayla istek atar.
5. Backend veriyi daha once cektiyse MySQL cache'inden doner.
6. Veri yoksa OpenStreetMap Overpass API'den tesisleri ceker, veritabanina kaydeder ve skor hesaplar.
7. Sonuc ekranda toplam skor, kategori kartlari, radar chart, bar chart ve detay tablosu olarak gosterilir.

## Karsilastirilan 5 Kategori
| Kategori | Bakilan OSM Verileri |
|----------|----------------------|
| Saglik | Hastane, klinik, eczane, doktor |
| Egitim | Okul, anaokulu, kolej, universite |
| Yesil Alan | Park, bahce, oyun alani, dogal koruma alani |
| Ulasim | Otobus duragi, tramvay duragi, istasyon, platform |
| Sosyal Imkanlar | Market, restoran, cafe, banka, ATM, fast food, firin |

## Skor Hesaplama Mantigi
Skor sistemi sadece tesis sayisini kullanmaz. Her kategori icin 3 faktor hesaplanir:

| Faktor | Agirlik | Aciklama |
|--------|---------|----------|
| Tip Agirligi | %40 | Daha onemli/nadir tesisler daha yuksek puan getirir. Ornek: hastane eczaneden daha degerlidir. |
| Cesitlilik | %30 | Kategoride kac farkli tesis tipi olduguna bakar. |
| Dagilim | %30 | Tesislerin koordinatlari arasindaki mesafeye gore mahalle geneline yayilip yayilmadigini olcer. |

Her kategori icin 0-100 arasi skor uretilir. Toplam skor, 5 kategori skorunun ortalamasidir.

## Teknik Yigin
| Katman | Teknoloji |
|--------|-----------|
| Frontend | React 19, Vite |
| Grafikler | Recharts |
| Backend | Python, FastAPI |
| Veritabani | MySQL 8.0 |
| Harici Veri | OpenStreetMap Overpass API |
| HTTP Istekleri | fetch, requests |
| Backend Calistirma | uvicorn |

## Genel Klasor Yapisi
```
bitirme/
  backend/
    api.py               # FastAPI endpoint'leri
    db_config.py         # MySQL baglanti ayarlari
    db_setup.py          # Veritabani ve tablolarin kurulumu
    location_service.py  # Sehir/ilce/mahalle verilerini OSM'den cekip cache'ler
    osm_service.py       # Mahalle tesis verilerini OSM'den cekip DB'ye kaydeder
    scoring.py           # Kategori ve toplam skor hesaplama sistemi
    requirements.txt     # Python bagimliliklari

  frontend/
    package.json         # React/Vite bagimliliklari ve script'leri
    vite.config.js       # Vite yapilandirmasi
    src/
      App.jsx            # Ana uygulama, karsilastirma akisi
      main.jsx           # React giris noktasi
      App.css
      index.css
      components/
        LocationSelector.jsx  # Sehir/ilce/mahalle secimi
        ScoreCard.jsx         # Kategori skor karti
        CompareCharts.jsx     # Radar chart, bar chart, detay tablosu
      services/
        locationService.js    # Yerel JSON tabanli konum yardimcilari; mevcut akista aktif kullanilmiyor
      data/
        il_ilce_mahalle.json  # Yerel konum veri dosyasi

  gorev.md
  ozet.md
```

## Backend Yapisi
Backend `api.py` dosyasindaki FastAPI uygulamasi uzerinden calisir.

### Endpoint'ler
| Endpoint | Gorev |
|----------|-------|
| `GET /api/sehirler` | OSM/cache uzerinden sehir listesini doner. |
| `GET /api/ilceler/{sehir}` | Secilen sehre ait ilceleri doner. |
| `GET /api/mahalleler/{sehir}/{ilce}` | Secilen ilceye ait mahalleleri doner. |
| `GET /api/mahalle-veri/{sehir}/{ilce}/{mahalle}` | Mahalle skorlarini ve tesis sayilarini doner. |
| `GET /api/mahalle-detay/{sehir}/{ilce}/{mahalle}` | Skorlar, tesis sayilari ve kategori bazli mekan listesini doner. |

### Veritabani Tablolari
`db_setup.py` calistirildiginda su tablolar olusturulur:

| Tablo | Amac |
|-------|------|
| `mahalleler` | Secilen mahalle kayitlari ve son veri cekim zamani |
| `kategori_verileri` | OSM'den gelen ham tesis verileri |
| `skorlar` | Hesaplanmis kategori skorlari, toplam skor ve detay JSON'lari |
| `kullanici_puanlari` | Kullanici yorum/puan sistemi icin hazir tablo |
| `location_cache` | Sehir, ilce ve mahalle dropdown verilerinin cache'i |

### Cache Mantigi
- Bir mahalle ilk kez sorgulaninca OSM'den veriler cekilir.
- Cekilen tesisler `kategori_verileri` tablosuna kaydedilir.
- Skorlar hesaplanip `skorlar` tablosuna yazilir.
- `mahalleler.last_fetched` doluysa ayni mahalle tekrar OSM'den cekilmez; veriler MySQL'den doner.
- Sehir/ilce/mahalle dropdown verileri de `location_cache` tablosunda saklanir.

## Frontend Yapisi
Frontend React + Vite ile yazilmistir.

Ana akisi `src/App.jsx` yonetir:
- Iki adet `LocationSelector` ile mahalle secimi yapilir.
- Secimler tamamlaninca `Kiyasla` butonu aktif olur.
- API istekleri `http://localhost:8000` adresindeki backend'e gider.
- Overpass rate limit riskini azaltmak icin iki mahalle verisi ayni anda degil, sirayla cekilir.
- Sonuclar `ScoreCard` ve `CompareCharts` bilesenleriyle gosterilir.

`LocationSelector.jsx`, sehir/ilce/mahalle listesini backend endpoint'lerinden dinamik olarak alir. `src/services/locationService.js` ve `src/data/il_ilce_mahalle.json` yerel veri kullanan yardimci yapi olarak duruyor, fakat mevcut secim bileseni API tabanli calisiyor.

## Proje Durumu
- [x] React arayuz ve iki mahalle secim akisi
- [x] FastAPI backend
- [x] MySQL veritabani kurulum script'i
- [x] OSM Overpass API entegrasyonu
- [x] Dropdown verileri icin OSM/cache mantigi
- [x] Mahalle tesis verileri icin DB cache sistemi
- [x] 5 kategorili akilli skor sistemi
- [x] Toplam skor, kategori kartlari, radar chart, bar chart ve detay tablosu
- [x] Kullanici puanlari icin veritabani tablosu
- [ ] Kullanici puanlari icin frontend/backend aktif ozelligi
- [ ] Otomatik testler
- [ ] Harita entegrasyonu

## Kurulum Gereksinimleri
- Node.js 18+
- Python 3.10+
- MySQL 8.0+
- Git opsiyonel

## Kurulum ve Calistirma

### 1. MySQL Ayari
MySQL 8.0 kurulu ve calisir durumda olmali. Root sifresi `backend/db_config.py` icinde guncellenmelidir:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "SENIN_SIFREN",
    "database": "mahalle_score",
    "charset": "utf8mb4",
}
```

### 2. Backend Kurulumu
```bash
cd bitirme/backend
pip install -r requirements.txt
python db_setup.py
uvicorn api:app --reload --port 8000
```

### 3. Frontend Kurulumu
```bash
cd bitirme/frontend
npm install
npm run dev
```

### 4. Kullanim
Tarayicida `http://localhost:5173` adresi acilir. Iki mahalle secildikten sonra "Kiyasla" butonu ile sonuc ekrani gorulur.

## Dikkat Edilecek Noktalar
- Ilk mahalle sorgusu OSM'den veri cektigi icin uzun surebilir.
- `osm_service.py` her kategori arasinda 5 saniye bekler; bu Overpass API rate limit'ini azaltmak icindir.
- Overpass API yogun oldugunda 429 veya 504 hatalari alinabilir; sistem alternatif Overpass sunucusunu da dener.
- Cache'e giren mahalleler daha sonra hizli doner.
- Kod yorumlarinda bazi Turkce karakterler bozuk gorunuyor; bu muhtemelen dosya encoding gecmisinden kaynaklaniyor, calisma mantigini bozmaz.

## Sunum Icin Vurgulanabilecek Noktalar
1. Gercek OpenStreetMap verisi kullaniliyor.
2. Veriler MySQL'de cache'lenerek tekrar sorgularda hiz kazaniyor.
3. Skor sistemi sadece sayim yapmiyor; tesis onemi, cesitlilik ve dagilimi birlikte degerlendiriyor.
4. React arayuz, FastAPI backend ve MySQL veritabani ayrik katmanlar halinde tasarlanmis.
5. Sonuclar hem sayisal kartlarla hem de radar/bar grafiklerle gorsellestiriliyor.







SET SQL_SAFE_UPDATES = 0;

DELETE FROM kategori_verileri;
DELETE FROM skorlar;
DELETE FROM mahalleler;

SET SQL_SAFE_UPDATES = 1;


uvicorn api:app --reload --port 8000