# Görev Planı - Mahalle Kıyaslama Web Uygulaması

## Proje Hedefi
Arevibes tarzı React arayüzü. Açılır dropdown'larla şehir > ilçe > mahalle seçimi. Mahalleler 5 kategoride kıyaslanacak. OSM'den çekilen veriler MySQL'e kaydedilecek. Mevcut Python scriptlerinde minimum değişiklik.

---

## ÖNCELİK SIRASI

### Bölüm 1: React Projesi + Dropdown Sistemi ✅ TAMAMLANDI
> **İlk yapılacak iş:** Arevibes tarzı arayüz ve şehir > ilçe > mahalle zincirleme dropdown'ları

- [x] React (Vite) projesi oluştur (`frontend/`)
- [x] Ana sayfa layout'u (Arevibes tarzı temiz, modern tasarım)
- [x] Şehir dropdown'u - Türkiye'deki 81 il
- [x] İlçe dropdown'u - Seçilen şehre göre ilçeler otomatik gelsin
- [x] Mahalle dropdown'u - Seçilen ilçeye göre mahalleler otomatik gelsin
- [x] Dropdown veri kaynağı: `il_ilce_mahalle.json` (statik JSON)
- [x] Dropdown'lar arası bağımlılık (zincirleme)
- [x] Seçilen mahallenin bilgisi state'te tutulsun

**Dosyalar:**
- `frontend/src/components/LocationSelector.jsx` - Zincirleme dropdown bileşeni
- `frontend/src/components/LocationSelector.css` - Dropdown stilleri
- `frontend/src/services/locationService.js` - JSON'dan veri okuma servisi
- `frontend/src/data/il_ilce_mahalle.json` - 81 il, ilçe, mahalle verisi
- `frontend/src/App.jsx` - Ana sayfa
- `frontend/src/App.css` - Ana sayfa stilleri
- `frontend/src/index.css` - Global stiller

### Bölüm 2: MySQL Veritabanı ✅ TAMAMLANDI
- [x] MySQL 8.0.33 bağlantısı (root / gözdem)
- [x] `mahalle_score` veritabanı
- [x] `mahalleler` tablosu (sehir, ilce, mahalle, last_fetched)
- [x] `kategori_verileri` tablosu (mahalle_id, kategori, osm_id, isim, tip, lat, lon)
- [x] `skorlar` tablosu (+ JSON detay kolonları)
- [x] `kullanici_puanlari` tablosu (ileride kullanılabilir)
- [x] Cache kontrolü: last_fetched varsa DB'den, yoksa OSM'den çek ve kaydet
- [x] OSM veri çekme servisi - 5 kategori destekli

**Dosyalar:**
- `backend/db_config.py` - MySQL bağlantı ayarları
- `backend/db_setup.py` - Veritabanı ve tabloları oluşturur
- `backend/osm_service.py` - OSM'den veri çekme + DB kayıt + cache
- `backend/requirements.txt` - Python bağımlılıkları

### Bölüm 3: Backend API (FastAPI) ✅ TAMAMLANDI
- [x] FastAPI ile API oluşturuldu
- [x] CORS desteği (React frontend erişimi)
- [x] API endpoint'leri:
  - `GET /api/sehirler` - 81 il
  - `GET /api/ilceler/{sehir}` - İlçeler
  - `GET /api/mahalleler/{sehir}/{ilce}` - Mahalleler
  - `GET /api/mahalle-veri/{sehir}/{ilce}/{mahalle}` - Skorlar + sayılar
  - `GET /api/mahalle-detay/{sehir}/{ilce}/{mahalle}` - Skorlar + mekan listesi
- [x] 5 kategori OSM sorguları:
  - Sağlık (hospital, clinic, pharmacy, doctors)
  - Eğitim (school, kindergarten, college, university)
  - Yeşil Alan (park, garden, playground, nature_reserve)
  - Ulaşım (bus_stop, tram_stop, subway, station)
  - Sosyal İmkanlar (supermarket, restaurant, cafe, bank, atm, fast_food, bakery)
- [x] İsim dönüşümü: Dropdown formatı → OSM formatı (BÜYÜK HARF → Title Case, Mah. → Mahallesi)
- [x] Regex tabanlı eşleşme (tam isim yerine içeriyor kontrolü)

**Dosyalar:**
- `backend/api.py` - FastAPI uygulaması (5 endpoint)

### Bölüm 4: Akıllı Skor Sistemi + Arayüz Entegrasyonu ✅ TAMAMLANDI
- [x] 3 faktörlü akıllı skor hesaplama:
  - Tesis Tip Ağırlığı (%40) - Hastane 5p > Eczane 1p
  - Çeşitlilik (%30) - Kaç farklı tesis tipi var
  - Dağılım/Erişilebilirlik (%30) - Koordinat bazlı yayılım analizi
- [x] Frontend-Backend entegrasyonu (API çağrıları)
- [x] Kıyaslama sonuç ekranı: toplam skor + kategori bazlı karşılaştırma
- [x] ScoreCard bileşeni: renk kodlu puanlar, kazanan vurgulama
- [x] Loading ve hata durumları
- [x] Sıralı veri çekme (Overpass rate limit koruması)

**Dosyalar:**
- `backend/scoring.py` - Akıllı skor hesaplama (3 faktör)
- `frontend/src/App.jsx` - API entegrasyonu + kıyaslama sonuçları
- `frontend/src/components/ScoreCard.jsx` - Kategori skor kartı
- `frontend/src/components/ScoreCard.css` - Skor kartı stilleri

### Bölüm 5: Kıyaslama Grafikleri ✅ TAMAMLANDI
- [x] Radar chart ile görsel kıyaslama (Recharts)
- [x] Bar chart ile kategori bazlı karşılaştırma
- [x] Detay tablosu: skor, tesis sayısı, fark, kazanan bilgisi
- [x] Responsive tasarım

**Dosyalar:**
- `frontend/src/components/CompareCharts.jsx` - Radar + Bar chart + Detay tablosu
- `frontend/src/components/CompareCharts.css` - Grafik stilleri

### Bölüm 6: Test ve İyileştirme
- [ ] Uçtan uca test (farklı mahallelerle)
- [ ] Overpass hata yönetimi iyileştirmeleri
- [ ] Cache'li verilerle hız testi

### Bölüm 7: Son Dokunuşlar
- [ ] Responsive tasarım (mobil iyileştirme)
- [ ] Harita entegrasyonu (Leaflet)
- [ ] Deploy hazırlığı

---

## Teknik Yığın
| Katman | Teknoloji |
|--------|-----------|
| Frontend | React 19 + Vite |
| Backend | Python + FastAPI |
| Veritabanı | MySQL 8.0 |
| Veri Kaynağı | OpenStreetMap (Overpass API) |
| Grafikler | Recharts |
| Harita | Leaflet.js (planlandı) |

---

## Çalıştırma
```
# Backend
cd backend && uvicorn api:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

---

> **Kurallar:**
> 1. Mevcut Python scriptlerinde minimum değişiklik
> 2. Flask kullanılmayacak (FastAPI kullanıldı)
> 3. Arayüz tamamen React ile yazılacak
> 4. Her bölüm sırasıyla, kullanıcının emriyle uygulanacak


DELETE FROM kategori_verileri;
DELETE FROM skorlar;
DELETE FROM mahalleler;

SET SQL_SAFE_UPDATES = 1;