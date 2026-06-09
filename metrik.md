# OSM Veri Cekim ve Skorlama Metrikleri

Bu dokuman, projenin OSM'den mahalle verisi cekerken hangi metrikleri kullandigini ve bu verileri nasil skora cevirdigini aciklar. Uygulamadaki ana kaynaklar `backend/osm_service.py` ve `backend/scoring.py` dosyalaridir.

## 1. Veri kaynaklari

Uygulama mahalle verisini oncelikle OpenStreetMap ekosisteminden alir:

- **Overpass API**: Mahalle siniri ve tesis verilerini cekmek icin kullanilir.
- **Nominatim**: Mahalle siniri veya merkez koordinati Overpass ad aramasi ile bulunamazsa geocoding/fallback icin kullanilir.
- **MySQL cache**: Daha once cekilen mahalle, kategori ve skor verileri tekrar kullanilir. `refresh=true` gonderilirse veri yeniden cekilir.

## 2. Mahalle alanini belirleme metrikleri

Veri cekimi icin once mahallenin kapsami bulunmaya calisilir:

1. **Resmi OSM idari siniri**
   - Il icin `admin_level=4`
   - Ilce icin `admin_level=6`
   - Mahalle icin `admin_level=8|9|10`
   - `boundary=administrative` ve mahalle/ilce/il adlari ile eslestirme yapilir.

2. **Nominatim OSM siniri**
   - Overpass ad aramasi siniri bulamazsa Nominatim'den relation/way id alinir.
   - Bu id Overpass area id'ye cevrilip ayni tesis sorgulari bu alan icinde calistirilir.

3. **Merkez noktanin icinde kaldigi OSM alani**
   - Mahalle merkezi Nominatim ile bulunur.
   - Overpass `is_in(lat, lon)` sorgusu ile noktanin icindeki idari alanlar aranir.

4. **Yaklasik yaricap fallback**
   - Mahalle siniri bulunamazsa merkez koordinat etrafinda yaricap sorgusu kullanilir.
   - Varsayilan yaricap: **1500 m**
   - Genis fallback: **3000 m**
   - Cok genis fallback: **5000 m**

Bu nedenle `veri_kaynagi` alani su degerlerden biri olabilir: `osm_sinir`, `nominatim_osm_sinir`, `osm_iceren_alan`, `yaklasik_yaricap`, `yaklasik_yaricap_genis`, `yaklasik_yaricap_cok_genis`, `osm_sinir_yetersiz_yaklasik_yaricap`, `osm_sinir_yetersiz_genis_yaricap`, `osm_sinir_veri_yetersiz`, `osm_veri_yetersiz`.

## 3. OSM'den cekilen kategori metrikleri

Uygulama 5 ana kategori icin OSM tag'lerini ceker. Her tesis icin `osm_id`, `isim`, `tip`, `lat`, `lon` kaydedilir.

| Kategori | OSM tag'leri |
| --- | --- |
| Saglik | `amenity=hospital`, `amenity=clinic`, `amenity=pharmacy`, `amenity=doctors` |
| Egitim | `amenity=school`, `amenity=kindergarten`, `amenity=college`, `amenity=university` |
| Yesil alan | `leisure=park`, `leisure=garden`, `leisure=playground`, `leisure=nature_reserve` |
| Ulasim | `highway=bus_stop`, `railway=tram_stop`, `railway=station`, `public_transport=platform` |
| Sosyal imkanlar | `shop=supermarket`, `amenity=restaurant`, `amenity=cafe`, `amenity=bank`, `amenity=atm`, `amenity=fast_food`, `shop=bakery` |

## 4. Skorda kullanilan ana metrikler

Her kategori icin skor 0-100 arasinda hesaplanir. Skor sayi saymaktan ziyade erisilebilirligi olcer.

### 4.1 Yakinlik skoru

Mahalle merkezinden her tesis tipinin en yakin ornegine olan mesafe hesaplanir. Mesafe Haversine formuluyle kilometre cinsinden bulunur.

- Mesafe ideal esigin altindaysa: **100 puan**
- Mesafe maksimum esigin ustundeyse: **0 puan**
- Ideal ile maksimum arasindaysa: **lineer dusus**

Yakinlik skoru, tesis tipi agirliklariyla agirlikli ortalama olarak hesaplanir.

### 4.2 Cesitlilik skoru

Mahalle merkezine **1.5 km** icindeki farkli tesis tipleri sayilir.

Formul:

```text
cesitlilik_skoru = min((yakindaki_farkli_tip_sayisi / kategori_max_tip_sayisi) * 100, 100)
```

Kategori maksimum tip sayilari:

| Kategori | Maksimum tip sayisi |
| --- | ---: |
| Saglik | 4 |
| Egitim | 4 |
| Yesil alan | 4 |
| Ulasim | 4 |
| Sosyal imkanlar | 7 |

### 4.3 Yogunluk skoru

Mahalle merkezine **1 km** icindeki tesis sayisi alternatif secenek olarak olculur.

| 1 km icindeki tesis sayisi | Yogunluk skoru |
| ---: | ---: |
| 0 | 0 |
| 1 | 40 |
| 2 | 55 |
| 3-4 | 70 |
| 5-7 | 85 |
| 8+ | 100 |

## 5. Alt faktor agirliklari

Kategori icindeki nihai skor, AHP ile hesaplanan alt faktor agirliklariyla bulunur:

| Alt faktor | Agirlik |
| --- | ---: |
| Yakinlik | 0.5396 |
| Cesitlilik | 0.2970 |
| Yogunluk | 0.1634 |

Formul:

```text
kategori_skoru =
  yakinlik_skoru * 0.5396 +
  cesitlilik_skoru * 0.2970 +
  yogunluk_skoru * 0.1634
```

Alt faktor AHP tutarlilik orani yaklasik **0.0079**'dur.

## 6. Kategori agirliklari

Toplam mahalle skoru, kategori skorlarinin AHP agirlikli ortalamasidir.

| Kategori | Agirlik |
| --- | ---: |
| Saglik | 0.3000 |
| Egitim | 0.2500 |
| Ulasim | 0.2000 |
| Yesil alan | 0.1500 |
| Sosyal imkanlar | 0.1000 |

Formul:

```text
toplam_skor =
  saglik * 0.3000 +
  egitim * 0.2500 +
  ulasim * 0.2000 +
  yesil_alan * 0.1500 +
  sosyal_imkanlar * 0.1000
```

Kategori AHP tutarlilik orani neredeyse **0**'dir.

## 7. Tesis tipi agirliklari

Bazi tesis tipleri ayni kategori icinde daha onemli kabul edilir.

| Kategori | Tip agirliklari |
| --- | --- |
| Saglik | `hospital=5`, `clinic=3`, `doctors=3`, `pharmacy=2` |
| Egitim | `university=5`, `college=4`, `school=3`, `kindergarten=2` |
| Yesil alan | `nature_reserve=4`, `park=3`, `garden=2`, `playground=2` |
| Ulasim | `station=5`, `tram_stop=4`, `platform=3`, `bus_stop=2` |
| Sosyal imkanlar | `supermarket=3`, `bank=3`, `restaurant=2`, `cafe=2`, `bakery=2`, `fast_food=1`, `atm=2` |

## 8. Ideal ve maksimum erisim esikleri

Her tesis tipi icin ideal ve maksimum mesafe esikleri farklidir. Ideal mesafeye kadar tam puan, maksimum mesafeden sonra 0 puan verilir.

| Kategori | Tip | Ideal km | Maksimum km |
| --- | --- | ---: | ---: |
| Saglik | hospital | 2.0 | 5.0 |
| Saglik | clinic | 1.0 | 3.0 |
| Saglik | doctors | 1.0 | 3.0 |
| Saglik | pharmacy | 0.5 | 1.5 |
| Egitim | university | 3.0 | 8.0 |
| Egitim | college | 2.0 | 6.0 |
| Egitim | school | 0.8 | 2.0 |
| Egitim | kindergarten | 0.5 | 1.5 |
| Yesil alan | nature_reserve | 3.0 | 8.0 |
| Yesil alan | park | 0.5 | 1.5 |
| Yesil alan | garden | 0.5 | 1.5 |
| Yesil alan | playground | 0.3 | 1.0 |
| Ulasim | station | 1.5 | 4.0 |
| Ulasim | tram_stop | 0.5 | 1.5 |
| Ulasim | platform | 0.5 | 1.5 |
| Ulasim | bus_stop | 0.3 | 1.0 |
| Sosyal imkanlar | supermarket | 0.5 | 1.5 |
| Sosyal imkanlar | bank | 1.0 | 2.5 |
| Sosyal imkanlar | restaurant | 0.5 | 1.5 |
| Sosyal imkanlar | cafe | 0.5 | 1.5 |
| Sosyal imkanlar | bakery | 0.3 | 1.0 |
| Sosyal imkanlar | fast_food | 0.5 | 1.5 |
| Sosyal imkanlar | atm | 0.5 | 1.5 |

## 9. Veri guveni ve uyari metrikleri

API cevabinda veri guveni de uretilir:

- **Yuksek**: Resmi OSM mahalle siniri veya esdeger OSM alani kullanildiysa.
- **Orta**: Mahalle siniri bulunamadigi icin merkez + yaricap kullanildiysa.
- **Dusuk**: OSM'de yeterli tesis verisi bulunamadiysa.

`yaklasik_alan=true` ise skorlar resmi mahalle sinirindan degil, merkez koordinat etrafindaki yaklasik yaricaptan hesaplanmistir.

## 10. API'de donen metrik alanlari

Mahalle skor endpoint'leri su metrikleri dondurur:

- `counts`: Her kategori icin bulunan tesis sayisi.
- `skorlar`: Her kategori icin 0-100 arasi skor.
- `skor_detaylari`: Yakinlik, cesitlilik, yogunluk, en yakin mesafe, farkli tipler ve AHP detaylari.
- `toplam_skor`: Kategori agirliklariyla hesaplanan genel mahalle skoru.
- `veri_kaynagi`: Verinin hangi yontemle cekildigi.
- `veri_guveni`: Yuksek/orta/dusuk guven seviyesi.
- `veri_uyarisi`: Yaklasik alan veya veri yetersizligi durumunda aciklama.
