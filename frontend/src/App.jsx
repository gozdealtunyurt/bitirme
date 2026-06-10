import { useState } from "react";
import LocationSelector from "./components/LocationSelector";
import ScoreCard from "./components/ScoreCard";
import CompareCharts from "./components/CompareCharts";
import { API_URL, KATEGORI_LABELS } from "./constants/config";
import heroImage from "./assets/neighborhood-compare-hero.png";
import "./App.css";

function App() {
  const [mahalle1, setMahalle1] = useState(null);
  const [mahalle2, setMahalle2] = useState(null);
  const [data1, setData1] = useState(null);
  const [data2, setData2] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");
  const [error, setError] = useState(null);

  const canCompare = mahalle1 && mahalle2;

  const formatLocation = (location) =>
    `${location.mahalle} - ${location.ilce}, ${location.sehir}`;

  const fetchMahalleData = async (location) => {
    const url = `${API_URL}/api/mahalle-detay/${encodeURIComponent(location.sehir)}/${encodeURIComponent(
      location.ilce,
    )}/${encodeURIComponent(location.mahalle)}`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 90000);

    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) {
        let message = `API hatası: ${response.status}`;
        try {
          const errorData = await response.json();
          message = errorData.detail || message;
        } catch {
          // JSON olmayan hata yanıtında status mesajı yeterli.
        }
        throw new Error(message);
      }
      return response.json();
    } catch (err) {
      if (err.name === "AbortError") {
        throw new Error(
          "Veri çekme 90 saniyeyi aştı. OSM/Overpass yavaş veya yanıt vermiyor; birazdan tekrar deneyin.",
        );
      }
      if (err.message?.startsWith("OSM/") || err.message?.startsWith("Canli") || err.message?.includes("Overpass")) {
        throw err;
      }
      throw new Error(
        "Backend'e ulaşılamıyor. Backend çalışıyor mu? Terminalde backend klasöründe: python -m uvicorn api:app --reload --port 8000",
      );
    } finally {
      clearTimeout(timeout);
    }
  };

  const compareMahalleler = async () => {
    if (!canCompare) return;

    setLoading(true);
    setLoadingMessage("");
    setError(null);
    setShowResults(false);

    try {
      setLoadingMessage(`1/2 çekiliyor: ${formatLocation(mahalle1)}`);
      const firstData = await fetchMahalleData(mahalle1);
      setData1(firstData);

      await new Promise((resolve) => setTimeout(resolve, 750));

      setLoadingMessage(`2/2 çekiliyor: ${formatLocation(mahalle2)}`);
      const secondData = await fetchMahalleData(mahalle2);
      setData1(firstData);
      setData2(secondData);
      setShowResults(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setLoadingMessage("");
    }
  };

  const handleMahalleSelect = (side, location) => {
    if (side === 1) {
      setMahalle1(location);
      setData1(null);
    } else {
      setMahalle2(location);
      setData2(null);
    }
    setShowResults(false);
    setError(null);
  };

  const getDataSourceLabel = (source) =>
    ({
      osm_sinir: "OSM idari sınırı",
      nominatim_osm_sinir: "Nominatim OSM sınırı",
      osm_iceren_alan: "OSM içeren alan",
      yaklasik_yaricap: "Yaklaşık yarıçap",
      yaklasik_yaricap_genis: "Geniş yaklaşık yarıçap",
      yaklasik_yaricap_cok_genis: "Çok geniş yaklaşık yarıçap",
      ilce_fallback: "İlçe merkezi yaklaşık veri",
      sehir_fallback: "Şehir merkezi yaklaşık veri",
      ilce_ortalama_fallback: "İlçe ortalaması referans",
      sehir_ortalama_fallback: "Şehir ortalaması referans",
      osm_veri_yetersiz: "Veri yetersiz",
      osm_sinir_veri_yetersiz: "Sınır verisi yetersiz",
    })[source] || "Veri kaynağı";

  const formatFetchedDate = (value) => {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const renderFetchedInfo = (data, location) => {
    const fetchedDate = formatFetchedDate(data?.last_fetched);
    if (!fetchedDate) return null;

    return (
      <div className="data-fetched-info">
        <strong>{location.mahalle}</strong>
        <span>OSM verisi son güncelleme: {fetchedDate}</span>
      </div>
    );
  };

  const renderDataWarning = (data, location) => {
    if (!data?.yaklasik_alan && !data?.veri_uyarisi) return null;

    return (
      <div className="data-warning" role="note">
        <div>
          <strong>{location.mahalle}</strong>
          <span>{data.veri_uyarisi || "Bu mahalle için yaklaşık alan kullanıldı."}</span>
        </div>
        <span className="data-source-pill">{getDataSourceLabel(data.veri_kaynagi)}</span>
      </div>
    );
  };

  const getCompareButtonText = () => {
    if (loading) return "Karşılaştırılıyor...";
    if (!mahalle1 && !mahalle2) return "İki şehir seç";
    if (!mahalle1) return "İlk şehri seç";
    if (!mahalle2) return "İkinci şehri seç";
    return "Karşılaştır";
  };

  return (
    <div className="app">
      <header className="app-header">
        <a className="brand-mark" href="#top" aria-label="Yerini Bul home">
          <span className="brand-icon">YB</span>
          <span className="app-logo">Yerini Bul</span>
        </a>
        <nav className="top-nav" aria-label="Ana gezinme">
          <a href="#compare">Şehirleri Karşılaştır</a>
        </nav>
      </header>

      <main id="top" className="app-main">
        <section className="comparison-stage" aria-label="Şehir karşılaştırma sayfası">
          <div className="hero-section">
            <img className="hero-image" src={heroImage} alt="" aria-hidden="true" />
            <div className="hero-overlay" />
            <div className="hero-content">
              <p className="hero-kicker">Şehirleri Karşılaştır</p>
              <h1>Şehir Karşılaştırması</h1>
              <p className="app-tagline">
                İki şehir veya mahalle seç; yaşam kalitesi, günlük imkanlar, ulaşım, eğitim, konut çevresi ve
                mahalle ölçeğindeki yaşanabilirlik sinyallerini karşılaştır.
              </p>
            </div>
          </div>

          <section id="compare" className="comparison-shell" aria-label="Şehir karşılaştırma formu">
            <div className="compare-toolbar">
              <div>
                <span className="section-eyebrow">Karşılaştırma Aracı</span>
                <h2>Karşılaştırmak için iki yer seç</h2>
              </div>
              <div className="score-scale" aria-label="Score scale from 0 to 100">
                <span>0</span>
                <div className="scale-line" />
                <span>100</span>
              </div>
            </div>

            <div className="compare-grid">
              <LocationSelector label="İlk Şehir" onMahalleSelect={(location) => handleMahalleSelect(1, location)} />
              <div className="vs-divider">
                <span className="vs-badge">vs</span>
              </div>
              <LocationSelector
                label="İkinci Şehir"
                onMahalleSelect={(location) => handleMahalleSelect(2, location)}
              />
            </div>

            <div className="compare-action">
              <button
                className={`compare-btn ${canCompare && !loading ? "active" : ""}`}
                onClick={compareMahalleler}
                disabled={!canCompare || loading}
                type="button"
              >
                {getCompareButtonText()}
              </button>
            </div>

            <div className="feature-strip" aria-label="Comparison metrics">
              <span>5 kategori</span>
              <span>Mesafe bazlı skor</span>
              <span>Önbellekli sonuçlar</span>
              <span>0-100 skor</span>
            </div>
          </section>
        </section>

        <section id="about-tool" className="info-layer" aria-labelledby="info-title">
          <div className="info-copy">
            <span className="section-eyebrow">Neden karşılaştırmalı?</span>
            <h2 id="info-title">Taşınmadan, yatırım yapmadan veya keşfe çıkmadan önce daha net karar ver.</h2>
            <p>
              Şehir karşılaştırma aracı, iki yer arasındaki temel farkları tek ekranda anlamayı kolaylaştırır.
              Sağlık, eğitim, yeşil alan, ulaşım ve sosyal imkanlar mesafe bazlı skorlanır: sadece "kaç tane var"
              değil, "ne kadar yakın" ölçülür.
            </p>
            <p>
              Veriler OpenStreetMap'ten gerçek zamanlı çekilir, mahalle sınırlarına göre filtrelenir ve merkeze olan
              yürüme mesafesine göre 0-100 arası puanlanır.
            </p>
          </div>
          <div className="metric-list" aria-label="Karşılaştırılan konular">
            <span>Yaşam kalitesi</span>
            <span>Yürünebilirlik</span>
            <span>Ulaşım erişimi</span>
            <span>Eğitim erişimi</span>
            <span>Parklar ve yeşil alan</span>
            <span>Sosyal imkanlar</span>
          </div>
        </section>

        <section className="system-layer" aria-label="System states">
          {loading && (
            <div className="state-card loading-msg">
              <div className="loading-visual" aria-hidden="true">
                <span className="loading-spinner" />
                <span className="loading-pulse" />
              </div>
              <div className="loading-copy">
                <strong>Karşılaştırma yükleniyor</strong>
                <span>{loadingMessage || "Konum verileri OSM'den toplanıyor. Bu işlem biraz zaman alabilir."}</span>
                <small>Mahalle sınırı, tesis listesi ve skor detayları hazırlanıyor.</small>
              </div>
            </div>
          )}

          {error && (
            <div className="state-card error-msg">
              <strong>Bir sorun oluştu</strong>
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && !showResults && (
            <div className="state-card empty-msg">
              <strong>Henüz karşılaştırma yok</strong>
              <span>Skor raporunu görmek için iki şehir seçip Karşılaştır butonuna bas.</span>
            </div>
          )}
        </section>

        {showResults && data1 && data2 && (
          <section className="compare-result" aria-label="Karşılaştırma sonuçları">
            <div className="result-heading">
              <span className="section-eyebrow">Sonuç raporu</span>
              <h3>Karşılaştırma Sonuçları</h3>
            </div>

            <div className="total-scores">
              <div className={`total-score-card ${data1.toplam_skor >= data2.toplam_skor ? "winner" : ""}`}>
                <span className="total-label">{formatLocation(mahalle1)}</span>
                <span className="total-number">{data1.toplam_skor}</span>
                <span className="total-sub">/100</span>
              </div>
              <span className="total-vs">vs</span>
              <div className={`total-score-card ${data2.toplam_skor >= data1.toplam_skor ? "winner" : ""}`}>
                <span className="total-label">{formatLocation(mahalle2)}</span>
                <span className="total-number">{data2.toplam_skor}</span>
                <span className="total-sub">/100</span>
              </div>
            </div>

            <div className="data-warning-list" aria-label="Veri güvenilirliği uyarıları">
              {renderDataWarning(data1, mahalle1)}
              {renderDataWarning(data2, mahalle2)}
            </div>

            <div className="data-fetched-list" aria-label="Veri güncelleme tarihleri">
              {renderFetchedInfo(data1, mahalle1)}
              {renderFetchedInfo(data2, mahalle2)}
            </div>

            <div className="category-comparison">
              {Object.keys(KATEGORI_LABELS).map((key) => (
                <ScoreCard
                  key={key}
                  kategori={KATEGORI_LABELS[key]}
                  skor1={data1.skorlar[key]}
                  skor2={data2.skorlar[key]}
                  count1={data1.counts[key]}
                  count2={data2.counts[key]}
                  detail1={data1.skor_detaylari?.[key]}
                  detail2={data2.skor_detaylari?.[key]}
                  mahalle1={mahalle1.mahalle}
                  mahalle2={mahalle2.mahalle}
                />
              ))}
            </div>

            <CompareCharts data1={data1} data2={data2} mahalle1={mahalle1.mahalle} mahalle2={mahalle2.mahalle} />
          </section>
        )}
      </main>

      <footer className="site-footer">
        <div className="footer-brand">
          <span className="brand-icon">YB</span>
          <span>Yerini Bul</span>
        </div>
        <nav className="footer-links" aria-label="Alt bilgi gezinmesi">
          <a href="#about">Hakkımızda</a>
          <a href="#methodology">Metodoloji</a>
          <a href="#terms">Kullanım Şartları</a>
          <a href="#privacy">Gizlilik Politikası</a>
          <a href="#contact">İletişim</a>
        </nav>
        <div className="footer-bottom">
          <div className="social-links" aria-label="Social media links">
            <a href="#x" aria-label="X">
              X
            </a>
            <a href="#in" aria-label="LinkedIn">
              in
            </a>
            <a href="#yt" aria-label="YouTube">
              yt
            </a>
          </div>
          <span>Copyright 2026 Yerini Bul. Tüm hakları saklıdır.</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
