# Backend Yapisi Ozeti

## Klasor Yapisi

Backend klasoru FastAPI, MySQL ve OpenStreetMap Overpass API uzerine kurulu sade bir servis yapisina sahip.

```text
backend/
  api.py
  db_config.py
  db_setup.py
  location_service.py
  osm_service.py
  scoring.py
  requirements.txt
  __pycache__/
```

## Dosyalarin Gorevleri

### api.py
FastAPI uygulamasinin giris noktasi.

Gorevleri:
- CORS ayarlarini yapar.
- Frontend'in kullanacagi API endpointlerini tanimlar.
- Sehir, ilce ve mahalle dropdown verilerini doner.
- Mahalle skor ve detay verilerini frontend'e verir.

Mevcut endpointler:
- `GET /api/sehirler`
- `GET /api/ilceler/{sehir}`
- `GET /api/mahalleler/{sehir}/{ilce}`
- `GET /api/mahalle-veri/{sehir}/{ilce}/{mahalle}`
- `GET /api/mahalle-detay/{sehir}/{ilce}/{mahalle}`

### db_config.py
MySQL baglanti ayarlarini tutar.

Gorevleri:
- `DB_CONFIG` ile host, user, password, database ve charset bilgisini saklar.
- `get_connection()` ile MySQL baglantisi olusturur.

Not:
- Su anda veritabani sifresi dosya icinde duz yazi olarak duruyor. Proje baskasina pushlanacagi icin ileride environment variable veya ornek config yapisina gecmek daha guvenli olur.

### db_setup.py
Veritabani ve tablo kurulum scriptidir.

Gorevleri:
- `mahalle_score` veritabanini olusturur.
- Backend icin gerekli tablolari kurar.

Olusturulan tablolar:
- `mahalleler`
- `kategori_verileri`
- `skorlar`
- `kullanici_puanlari`
- `location_cache`

### location_service.py
Dropdown verilerini OpenStreetMap'ten ceker ve MySQL'de cache'ler.

Gorevleri:
- Turkiye sehir listesini ceker.
- Secilen sehre gore ilceleri ceker.
- Secilen ilceye gore mahalleleri ceker.
- Cekilen verileri `location_cache` tablosunda saklar.

Veri kaynagi:
- OpenStreetMap Overpass API

### osm_service.py
Mahalle bazli tesis verilerini OSM'den ceker ve veritabanina kaydeder.

Gorevleri:
- Saglik, egitim, yesil alan, ulasim ve sosyal imkan kategorilerini tanimlar.
- Her kategori icin ilgili OSM tag'lerini sorgular.
- OSM'den gelen tesisleri `kategori_verileri` tablosuna kaydeder.
- Daha once cekilmis mahalle varsa cache'den veri doner.
- Yeni veri cekildikten sonra skor hesaplamasini tetikler.

Kategoriler:
- `saglik`
- `egitim`
- `yesil_alan`
- `ulasim`
- `sosyal_imkanlar`

### scoring.py
Mahalle skorlarini hesaplayan servis dosyasidir.

Gorevleri:
- Her kategori icin 0-100 arasi skor hesaplar.
- Toplam mahalle skorunu uretir.
- Skorlari `skorlar` tablosuna kaydeder.

Skor faktorleri:
- Tesis tip agirligi
- Cesitlilik
- Dagilim / erisilebilirlik

### requirements.txt
Backend Python bagimliliklarini listeler.

Mevcut paketler:
- `mysql-connector-python`
- `requests`
- `fastapi`
- `uvicorn`

### __pycache__/
Python tarafindan otomatik olusturulan cache klasorudur. Projenin calisma mantigi icin elle duzenlenmez.

## Genel Backend Mimarisi

Backend katmanlari su sekilde ayrilmis:

1. API katmani: `api.py`
2. Veritabani baglanti katmani: `db_config.py`
3. Veritabani kurulum katmani: `db_setup.py`
4. Lokasyon verisi servisi: `location_service.py`
5. OSM mahalle verisi servisi: `osm_service.py`
6. Skor hesaplama servisi: `scoring.py`

Bu yapi MVP icin anlasilir ve yeterli. Dosyalar gorevlerine gore ayrilmis durumda.

## Veri Akisi

### Dropdown veri akisi
1. Frontend `/api/sehirler` endpointine istek atar.
2. `api.py`, `location_service.get_sehirler()` fonksiyonunu cagirir.
3. `location_service.py` once MySQL cache kontrolu yapar.
4. Cache varsa veri DB'den doner.
5. Cache yoksa Overpass API'den veri cekilir.
6. Veri `location_cache` tablosuna kaydedilir.
7. Frontend'e sehir listesi doner.

Ayni mantik ilce ve mahalle listeleri icin de uygulanir.

### Mahalle skor veri akisi
1. Frontend `/api/mahalle-detay/{sehir}/{ilce}/{mahalle}` endpointine istek atar.
2. `api.py`, `osm_service.get_mahalle_data()` fonksiyonunu cagirir.
3. `osm_service.py` mahalle kaydini `mahalleler` tablosunda arar.
4. `last_fetched` doluysa veriler cache'den okunur.
5. Cache yoksa OSM Overpass API'den kategori bazli tesisler cekilir.
6. Tesisler `kategori_verileri` tablosuna yazilir.
7. `scoring.py` kategori skorlarini ve toplam skoru hesaplar.
8. Skorlar `skorlar` tablosuna kaydedilir.
9. API sonucu frontend'e doner.

## Hata Yonetimi

Mevcut durumda:
- API endpointleri genel `try/except` ile hatayi yakalayip HTTP 500 donuyor.
- Dropdown verisi cekilemezse HTTP 503 donuyor.
- Overpass API tarafinda 429 ve 504 gibi durumlarda tekrar deneme var.

Gelistirilebilir noktalar:
- Veritabani baglanti hatalari daha acik mesajlarla ayrilabilir.
- OSM hatalari ile DB hatalari farkli HTTP kodlariyla donulebilir.
- Loglama `print()` yerine ileride `logging` modulu ile yapilabilir.

## Tespit Edilen Gelistirme Alanlari

1. DB bilgileri dosyada duz yazi olarak duruyor.
   - Pushlanacak proje icin bu riskli.
   - Environment variable veya ornek config dosyasi daha uygun.

2. Encoding bozuk yorumlar var.
   - Kodun calismasini bozmaz.
   - Okunabilirlik icin temizlenebilir.

3. Cache suresi yok.
   - `last_fetched` varsa mahalle verisi sonsuza kadar cache'den geliyor.
   - Ileride 7 gun / 30 gun gibi cache yenileme mantigi eklenebilir.

4. DB baglantilari elle acilip kapaniyor.
   - Bazi yerlerde hata olursa connection kapanmayabilir.
   - `try/finally` veya context manager yapisi daha guvenli olur.

5. OSM sorgu mantigi iki dosyada benzer.
   - `location_service.py` ve `osm_service.py` icinde Overpass request/retry yapisi benzer.
   - Gereksiz buyuk refactor yapmadan ortak yardimci fonksiyon dusunulebilir.

6. Health endpoint yok.
   - Backend ayakta mi, DB baglantisi var mi hizlica kontrol icin `/api/health` eklenebilir.

## Onerilen Gelistirme Sirasi

1. `db_config.py` guvenli hale getirilsin.
   - Sifreyi direkt kodda tutmak yerine environment variable okunabilir.
   - Projeyi baskasina pushlamak icin daha uygun olur.

2. `api.py` icine basit health endpoint eklensin.
   - Backend calisiyor mu hizlica gorulur.

3. Encoding bozuk yorumlar temizlensin.
   - Islev degismez, okunabilirlik artar.

4. Cache yenileme mantigi planlansin.
   - Hemen uygulamak sart degil; proje demosu icin mevcut cache mantigi yeterli olabilir.

5. DB connection kapanislari daha guvenli hale getirilsin.
   - Gereksiz refactor yapmadan kritik fonksiyonlarda `try/finally` kullanilabilir.

## Mevcut Durum Degerlendirmesi

Backend genel olarak calisir bir MVP mimarisine sahip. Frontend'in ihtiyaci olan ana endpointler mevcut. Veri kaynagi gercek OSM verisi oldugu icin proje sunum acisindan guclu. En oncelikli konu, proje baskasina pushlanacagi icin veritabani ayarlarinin makineye gore degisebilir ve guvenli hale getirilmesidir.
