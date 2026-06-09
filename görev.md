# GÃ¶rev PlanÄ±: Ä°lÃ§e ve Åehir Fallback Sistemi

## AmaÃ§

Projede mahalle bazlÄ± OSM verisi bazÄ± yerlerde yetersiz kalabiliyor. Bu durumda kullanÄ±cÄ±ya hata gÃ¶stermek veya 0 skorla bÄ±rakmak yerine, daha Ã¼st coÄŸrafi seviyelerden yaklaÅŸÄ±k skor Ã¼retilecek.

Hedef akÄ±ÅŸ:

```txt
Mahalle sÄ±nÄ±rÄ±
â†’ Mahalle merkezi yarÄ±Ã§ap
â†’ GeniÅŸ mahalle yarÄ±Ã§ap
â†’ Ä°lÃ§e merkezi fallback
â†’ Åehir merkezi fallback
â†’ Veri yetersiz sonucu
```

Bu sayede sistem her mahalle seÃ§imi iÃ§in mÃ¼mkÃ¼n olduÄŸunca sonuÃ§ Ã¼retir. Sonucun ne kadar gÃ¼venilir olduÄŸu `veri_kaynagi`, `veri_guveni` ve `veri_uyarisi` alanlarÄ±yla aÃ§Ä±kÃ§a belirtilir.

---

## 1. Mevcut AkÄ±ÅŸÄ± Koruma

- [x] Mevcut `osm_sinir` akÄ±ÅŸÄ± bozulmayacak.
- [x] Mahalle sÄ±nÄ±rÄ± bulunuyorsa Ã¶nce yine o kullanÄ±lacak.
- [x] Mevcut mahalle merkezi ve geniÅŸ yarÄ±Ã§ap fallback yapÄ±sÄ± korunacak.
- [x] Skorlama algoritmasÄ±na dokunulmayacak.
- [x] DB tablo yapÄ±sÄ± mÃ¼mkÃ¼nse deÄŸiÅŸtirilmeyecek.

---

## 2. Yeni Fallback Seviyeleri

- [x] `ilce_fallback` veri kaynaÄŸÄ± backend response deÄŸerlerine eklenecek.
- [x] `sehir_fallback` veri kaynaÄŸÄ± backend response deÄŸerlerine eklenecek.
- [x] Yeni fallback kaynaklarÄ± frontend etiketlerinde gÃ¶sterilecek.

Yeni veri kaynaklarÄ±:

```txt
ilce_fallback
sehir_fallback
```

Yeni gÃ¼ven seviyeleri:

```txt
osm_sinir                  â†’ yuksek
nominatim_osm_sinir        â†’ yuksek
osm_iceren_alan            â†’ yuksek
yaklasik_yaricap           â†’ orta
yaklasik_yaricap_genis     â†’ orta
yaklasik_yaricap_cok_genis â†’ dusuk
ilce_fallback              â†’ dusuk
sehir_fallback             â†’ dusuk
osm_veri_yetersiz          â†’ dusuk
```

---

## 3. Ä°lÃ§e Merkezi Bulma

Backend iÃ§inde ilÃ§e merkezi iÃ§in yardÄ±mcÄ± fonksiyon eklenecek.

Ã–nerilen fonksiyon:

```python
def _fetch_ilce_centroid_from_nominatim(sehir: str, ilce: str):
    ...
```

Arama Ã¶rnekleri:

```txt
{ilce}, {sehir}, Turkey
{normalize_ilce(ilce)}, {sehir}, Turkey
```

Beklenen Ã§Ä±ktÄ±:

```python
(lat, lon)
```

Bulunamazsa:

```python
(None, None)
```

- [x] İlçe merkezi Nominatim yardımcı fonksiyonu eklendi.
- [x] Fonksiyon `(lat, lon)` veya `(None, None)` dönecek şekilde bağlandı.
- [x] Mahalle merkezi bulunamazsa ilçe merkezi fallback akışına alındı.

Not:
Projede bu yardımcı fonksiyon şu adla uygulanmıştır:

```python
def _fetch_ilce_center_from_nominatim(sehir: str, ilce: str):
    ...
```

---

## 4. Åehir Merkezi Bulma

Durum:
- [x] Sehir merkezi Nominatim yardimci fonksiyonu eklendi.
- [x] Fonksiyon `(lat, lon)` veya `(None, None)` donecek sekilde baglandi.
- [x] Ilce fallback de sonuc vermezse sehir merkezi fallback akisina alindi.

Not:
Projede bu yardimci fonksiyon su adla uygulanmistir:

```python
def _fetch_sehir_center_from_nominatim(sehir: str):
    ...
```

Backend iÃ§inde ÅŸehir merkezi iÃ§in yardÄ±mcÄ± fonksiyon eklenecek.

Ã–nerilen fonksiyon:

```python
def _fetch_sehir_centroid_from_nominatim(sehir: str):
    ...
```

Arama Ã¶rneÄŸi:

```txt
{sehir}, Turkey
```

Beklenen Ã§Ä±ktÄ±:

```python
(lat, lon)
```

Bulunamazsa:

```python
(None, None)
```

---

## 5. Ä°lÃ§e Fallback Veri Ã‡ekimi

Durum:
- [x] `ILCE_FALLBACK_RADIUS_M = 5000` backend sabiti eklendi.
- [x] Mahalle seviyesindeki denemeler 0 donerse ilce merkezi fallback devreye giriyor.
- [x] Veri gelirse `veri_kaynagi = "ilce_fallback"`, `veri_guveni = "dusuk"`, `yaklasik_alan = true` donuyor.
- [x] Kullaniciya dusuk guven uyarisi donuyor.

Mahalle seviyesi tÃ¼m denemelerden sonra hÃ¢lÃ¢ 0 tesis dÃ¶nerse ilÃ§e fallback Ã§alÄ±ÅŸacak.

Ã–nerilen yarÄ±Ã§ap:

```txt
ILCE_FALLBACK_RADIUS_M = 5000
```

AkÄ±ÅŸ:

```txt
1. Ä°lÃ§e merkezi bulunur.
2. Ä°lÃ§e merkezi Ã§evresinde 5000m yarÄ±Ã§ap ile kategori verisi Ã§ekilir.
3. Veri gelirse:
   veri_kaynagi = "ilce_fallback"
   veri_guveni = "dusuk"
   yaklasik_alan = true
4. KullanÄ±cÄ±ya uyarÄ± dÃ¶ner.
```

UyarÄ± metni:

```txt
Mahalle icin yeterli OSM verisi bulunamadigi icin skor ilce merkezi cevresinden yaklasik hesaplanmistir.
```

---

## 6. Åehir Fallback Veri Ã‡ekimi

Durum:
- [x] `SEHIR_FALLBACK_RADIUS_M = 8000` backend sabiti eklendi.
- [x] Ilce fallback 0 donerse sehir merkezi fallback devreye giriyor.
- [x] Mahalle/ilce merkezi bulunamazsa sehir merkezi de son fallback olarak deneniyor.
- [x] Veri gelirse `veri_kaynagi = "sehir_fallback"`, `veri_guveni = "dusuk"`, `yaklasik_alan = true` donuyor.
- [x] Kullaniciya dusuk guven uyarisi donuyor.

Ä°lÃ§e fallback de 0 dÃ¶nerse ÅŸehir fallback Ã§alÄ±ÅŸacak.

Ã–nerilen yarÄ±Ã§ap:

```txt
SEHIR_FALLBACK_RADIUS_M = 8000
```

AkÄ±ÅŸ:

```txt
1. Åehir merkezi bulunur.
2. Åehir merkezi Ã§evresinde 8000m yarÄ±Ã§ap ile kategori verisi Ã§ekilir.
3. Veri gelirse:
   veri_kaynagi = "sehir_fallback"
   veri_guveni = "dusuk"
   yaklasik_alan = true
4. KullanÄ±cÄ±ya uyarÄ± dÃ¶ner.
```

UyarÄ± metni:

```txt
Mahalle ve ilce icin yeterli OSM verisi bulunamadigi icin skor sehir merkezi cevresinden yaklasik hesaplanmistir.
```

---

## 7. Veri Yetersiz Son Ã‡are

Durum:
- [x] Tum fallbackler 0 donerse backend artik hata firlatmadan `osm_veri_yetersiz` cevabi donduruyor.
- [x] Bu sonuc DBye basarili cache gibi kaydedilmiyor.
- [x] `toplam_skor = 0`, kategori skorlari 0 ve `veri_guveni = "dusuk"` donuyor.

Åehir fallback de 0 dÃ¶nerse sistem hata vermeyecek.

Son cevap:

```txt
veri_kaynagi = "osm_veri_yetersiz"
veri_guveni = "dusuk"
toplam_skor = 0
```

UyarÄ±:

```txt
OSM'de bu mahalle icin yeterli tesis verisi bulunamadigi icin skorlar veri yetersiz olarak gosterilmistir.
```

Bu mevcut davranÄ±ÅŸ korunacak.

---

## 8. Cache MantÄ±ÄŸÄ±

Durum:
- [x] Cache sadece gercek tesis verisi varsa gecerli kabul ediliyor.
- [x] `cache_dolu = get_total_kategori_count(mahalle_id) > 0` kurali korunuyor.
- [x] 0 tesis sonucu sonraki denemelerde tekrar OSMden denenebilir durumda kaliyor.

HatalÄ± 0 cache problemi tekrar oluÅŸmamalÄ±.

Kural:

```txt
Sadece gerÃ§ek tesis verisi olan kayÄ±tlar cache kabul edilir.
```

Kontrol:

```python
cache_dolu = get_total_kategori_count(mahalle_id) > 0
```

Bu korunacak.

---

## 9. API Response AlanlarÄ±

Durum:
- [x] API response icinde `veri_kaynagi`, `veri_guveni`, `veri_uyarisi`, `yaklasik_alan` alanlari fallbacklere gore donuyor.
- [x] `ilce_fallback` ve `sehir_fallback` icin dusuk guven seviyesi baglandi.
- [x] `osm_veri_yetersiz` son cevap formati eklendi.

API yanÄ±tÄ±nda ÅŸu alanlar doÄŸru dÃ¶nmeli:

```json
{
  "veri_kaynagi": "ilce_fallback",
  "veri_guveni": "dusuk",
  "veri_uyarisi": "...",
  "yaklasik_alan": true
}
```

veya:

```json
{
  "veri_kaynagi": "sehir_fallback",
  "veri_guveni": "dusuk",
  "veri_uyarisi": "...",
  "yaklasik_alan": true
}
```

---

## 10. Frontend Etkisi

Durum:
- [x] Frontend veri uyarisi alanini zaten gosteriyor.
- [x] Frontend veri kaynagi etiket listesine `ilce_fallback`, `sehir_fallback`, `osm_veri_yetersiz` eklendi.
- [x] Buyuk frontend akisi degistirilmedi.

Frontend tarafÄ±nda bÃ¼yÃ¼k deÄŸiÅŸiklik gerekmemeli.

Mevcut frontend zaten:

- `veri_uyarisi`
- `veri_kaynagi`
- `yaklasik_alan`

alanlarÄ±nÄ± gÃ¶sterebiliyor.

Gerekirse sadece veri kaynaÄŸÄ± label listesine ÅŸunlar eklenir:

```js
ilce_fallback: "Ä°lÃ§e merkezi yaklaÅŸÄ±k veri"
sehir_fallback: "Åehir merkezi yaklaÅŸÄ±k veri"
osm_veri_yetersiz: "Veri yetersiz"
```

---

## 11. Test PlanÄ±

Durum:
- [x] Test senaryolari gorev planinda belirlendi.
- [x] Backend syntax kontrolu localde gecti.
- [ ] Canli API ve Netlify testi, kod GitHuba push edilip Render deploy aldiktan sonra manuel yapilacak.

### 11.1 Mevcut GÃ¼Ã§lÃ¼ Mahalle

Ã–rnek:

```txt
Ä°stanbul > KadÄ±kÃ¶y > CaferaÄŸa Mah.
```

Beklenen:

```txt
veri_kaynagi = osm_sinir
veri_guveni = yuksek
toplam_skor > 0
```

### 11.2 Veri ZayÄ±f Mahalle

Ã–rnek:

```txt
Ã‡obanlar Mah.
```

Beklenen:

```txt
Ã–nce mahalle fallbackleri denenir.
Veri bulunursa ilce_fallback veya sehir_fallback dÃ¶ner.
Frontend hata vermez.
```

### 11.3 TÃ¼m Fallbackler BoÅŸ

Beklenen:

```txt
veri_kaynagi = osm_veri_yetersiz
veri_guveni = dusuk
toplam_skor = 0
Frontend hata vermez.
```

---

## 12. CanlÄ±ya Alma AdÄ±mlarÄ±

- [ ] Kod deÄŸiÅŸikliÄŸi localde yapÄ±lacak.
- [ ] Backend syntax kontrolÃ¼ yapÄ±lacak:

```bash
python -m py_compile api.py db_config.py db_setup.py local_location_data.py location_service.py osm_service.py scoring.py
```

- [ ] Local test yapÄ±lacak.
- [ ] GitHub'a commit/push yapÄ±lacak.
- [ ] Render otomatik deploy kontrol edilecek.
- [ ] CanlÄ± endpoint test edilecek.
- [ ] Netlify frontend Ã¼zerinden karÅŸÄ±laÅŸtÄ±rma denenerek doÄŸrulanacak.

---

## 13. Commit MesajÄ± Ã–nerisi

```txt
Add district and city fallback for sparse OSM data
```

---

## 14. Dikkat Edilecekler

- [ ] Bu fallbackler sonucu daha yaklaÅŸÄ±k yapar.
- [ ] KullanÄ±cÄ±ya veri gÃ¼veni aÃ§Ä±kÃ§a gÃ¶sterilmeli.
- [ ] Ä°lÃ§e/ÅŸehir fallback sonuÃ§larÄ± mahalleye Ã¶zel kesin skor gibi sunulmamalÄ±.
- [ ] Demo ve gerÃ§ek kullanÄ±mda `veri_guveni` alanÄ± Ã¶nemlidir.
- [ ] OSM/Overpass yoÄŸunluÄŸu hÃ¢lÃ¢ gecikme yaratabilir.
