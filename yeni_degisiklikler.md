# Yeni Degisiklikler Ozeti

Bu not, mahalle verilerinin yanlis veya 0 gelmesi ve OSM/Overpass isteklerinin cok uzun surmesi sorunlari icin bu sohbette yapilan degisiklikleri ozetler.

## Degisen dosya

- `backend/osm_service.py`

## 1. Overpass sorgu suresi azaltildi

Onceki akista Overpass her sorguda listedeki tum sunuculari deneyebiliyordu. Her sunucu 15-18 saniye beklediginde tek mahalle cekimi kolayca frontend tarafindaki 90 saniyelik limite takiliyordu.

Yapilan degisiklik:

- `OVERPASS_MAX_RETRIES` degeri 4 sunucu yerine 2 denemeye indirildi.
- Boylece yavas veya cevap vermeyen Overpass sunuculari yuzunden canli veri cekiminin gereksiz uzamasi azaltilmis oldu.

## 2. Nominatim sonucu artik daha dikkatli seciliyor

Onceki davranista Nominatim'den gelen ilk sonuc, il ve ilce baglami tutuyorsa kolayca kabul edilebiliyordu. Bu durum ayni veya benzer adli mahallelerde yanlis merkez koordinati secilmesine ve sonuc olarak 0 veri donmesine yol acabiliyordu.

Yapilan degisiklikler:

- Mahalle adi normalize ediliyor.
- `Mah.`, `Mahallesi`, bosluk, noktalama ve Turkce buyuk/kucuk harf farklari temizleniyor.
- Nominatim sonucundaki `display_name`, `name`, `namedetails` ve `address` alanlarindan mahalle aday adlari okunuyor.
- Aday mahalle adi hedef mahalleyle birebir ayni degilse benzerlik oraniyla kontrol ediliyor.
- Il ve ilce baglami tutsa bile mahalle adi benzemiyorsa sonuc kabul edilmiyor.

Eklenen yardimci mantik:

- `_normalize_match_text`
- `_names_similar`
- `_nominatim_candidate_names`
- `_matches_mahalle_name`
- `_select_nominatim_result`

## 3. Ilce merkezine dusen hatali fallback kaldirildi

Onceki Nominatim centroid aramasinda son care olarak ilce merkezi deneniyordu. Bu, mahalle bulunamadiginda ilce merkezinin mahalle merkezi gibi kullanilmasina sebep olabiliyordu.

Yapilan degisiklik:

- Nominatim merkez sorgularindan `ilce, sehir, Turkey` fallback'i kaldirildi.
- Artik mahalle bulunamiyorsa sistem rastgele ilce merkezini kullanmak yerine daha dusuk guvenli veya basarisiz veri durumuna duser.

Bu degisiklik yanlis mahalleye ait skor uretme riskini azaltir.

## 4. Bulunan Nominatim merkezi tekrar kaybedilmiyor

Onceki akista Nominatim ile merkez bulunup `is_in` sinir aramasi basarisiz olursa, merkez koordinati kaybedilebiliyor ve sonra ayni Nominatim aramasi tekrar yapilabiliyordu.

Yapilan degisiklik:

- `fetch_boundary_snapshot_from_containing_area` sinir bulamasa bile buldugu merkezi geri dondurebiliyor.
- Ana fallback akisi, elinde merkez varsa veritabanindan veya Nominatim'den tekrar merkez aramiyor.

Bu hem sureyi kisaltir hem de ayni dis istegin tekrar edilmesini azaltir.

## 5. Haritadaki polygon siniri ile veri cekme eklendi

Projede zaten OSM relation/area uzerinden mahalle siniri kullaniliyordu. Fakat bazi mahallelerde Nominatim haritada polygon gosterse bile Overpass `area(id)` sorgusu 0 donebiliyor veya area id kullanilamiyor.

Yapilan degisiklik:

- Nominatim'den gelen GeoJSON polygon siniri okunuyor.
- GeoJSON koordinatlari Overpass `poly` formatina cevriliyor.
- Overpass area sorgusu cevap vermezse, area id yoksa veya area sorgusu 0 tesis dondururse ayni mahalle siniri `poly` sorgusuyla tekrar deneniyor.

Eklenen yardimci fonksiyonlar:

- `_ring_area_score`
- `_sample_ring`
- `_geojson_to_overpass_poly`
- `fetch_all_kategoriler_by_polygon`

Bu degisiklik, "haritada sinir var ama proje 0 0 donduruyor" problemini azaltmak icin eklendi.

## 6. Eski 0 sonuc cache'i artik dogrudan kullanilmiyor

Onceki cache kontrolunde `last_fetched` varsa, kategori verisi 0 olsa bile sonuc cache'den donebiliyordu. Bu nedenle daha once hatali veya eksik cekilmis 0 sonuc, yeni duzeltmeler calismadan tekrar ekrana gelebiliyordu.

Yapilan degisiklik:

- Cache ancak kategori verisi sayisi 0'dan buyukse direkt kullaniliyor.
- Cache kaydi var ama tesis sayisi 0 ise canli OSM verisi tekrar deneniyor.
- Log'a `Cache 0 tesis iceriyor; guncel OSM verisi tekrar denenecek` mesaji eklendi.

## 7. Beklenen etki

Bu degisikliklerden sonra:

- Yanlis mahalle merkezinin secilme ihtimali azalir.
- Nominatim sonucunda mahalle adi dogrulanir.
- OSM area sorgusu 0 donerse haritadaki polygon siniriyle tekrar veri cekilir.
- Eski 0 sonuc cache'i yeni denemeleri engellemez.
- Overpass yavasladiginda 90 saniye timeout'a takilma ihtimali azalir.

## 8. Hala mumkun olan sinirlar

Bu duzeltmeler OSM/Nominatim verisini daha iyi kullanir, fakat tamamen garanti vermez.

Su durumlarda hala 0 veya dusuk guvenli sonuc gelebilir:

- OSM'de mahalle polygon'u hic yoksa.
- Polygon var ama mahalle icindeki tesisler OSM'de etiketlenmemisse.
- Overpass sunuculari gecici olarak yogunsa veya cevap vermiyorsa.
- Mahalle adi resmi listede farkli, OSM'de farkli yazilmissa ve benzerlik esigi bunu yakalayamazsa.

## 9. Kontrol

Python soz dizimi kontrolu calistirildi:

```bash
python -m py_compile backend\osm_service.py backend\api.py
```

Kontrol basarili oldu.
