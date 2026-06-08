// src/components/ScoreCard.jsx
import { getScoreColor, getScoreLabel } from "../utils/scoreUtils";
import "./ScoreCard.css";

function ScoreCard({ kategori, skor1, skor2, count1, count2, detail1, detail2, mahalle1, mahalle2 }) {
  const winner = skor1 > skor2 ? 1 : skor2 > skor1 ? 2 : 0;

  const formatDistance = (value) => {
    if (value === null || value === undefined) return "Yok";
    return `${Number(value).toFixed(2)} km`;
  };

  const renderDetails = (detail) => {
    if (!detail || Object.keys(detail).length === 0) {
      return (
        <div className="score-explain empty">
          <span>Detay verisi yok</span>
        </div>
      );
    }

    return (
      <div className="score-explain">
        <span>Yakınlık {detail.yakinlik_skoru ?? 0}</span>
        <span>Çeşitlilik {detail.cesitlilik_skoru ?? 0}</span>
        <span>Yoğunluk {detail.yogunluk_skoru ?? 0}</span>
        <span>En yakın {formatDistance(detail.en_yakin_mesafe_km)}</span>
      </div>
    );
  };

  return (
    <div className="score-card">
      <div className="score-card-header">
        <span className="score-card-title">{kategori}</span>
      </div>
      <div className="score-card-body">
        <div className={`score-side ${winner === 1 ? "side-winner" : ""}`}>
          <div className="score-circle" style={{ borderColor: getScoreColor(skor1) }}>
            <span className="score-num" style={{ color: getScoreColor(skor1) }}>{skor1}</span>
          </div>
          <span className="score-mahalle">{mahalle1}</span>
          <span className="score-detail">{count1} yer</span>
          <span className="score-badge" style={{ background: getScoreColor(skor1) }}>
            {getScoreLabel(skor1)}
          </span>
          {renderDetails(detail1)}
        </div>
        <div className="score-vs-line">vs</div>
        <div className={`score-side ${winner === 2 ? "side-winner" : ""}`}>
          <div className="score-circle" style={{ borderColor: getScoreColor(skor2) }}>
            <span className="score-num" style={{ color: getScoreColor(skor2) }}>{skor2}</span>
          </div>
          <span className="score-mahalle">{mahalle2}</span>
          <span className="score-detail">{count2} yer</span>
          <span className="score-badge" style={{ background: getScoreColor(skor2) }}>
            {getScoreLabel(skor2)}
          </span>
          {renderDetails(detail2)}
        </div>
      </div>
    </div>
  );
}

export default ScoreCard;
