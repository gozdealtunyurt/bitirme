// src/utils/scoreUtils.js

export function getScoreColor(score) {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#84cc16";
  if (score >= 40) return "#eab308";
  if (score >= 20) return "#f97316";
  return "#ef4444";
}

export function getScoreLabel(score) {
  if (score >= 80) return "Çok İyi";
  if (score >= 60) return "İyi";
  if (score >= 40) return "Orta";
  if (score >= 20) return "Düşük";
  return "Sınırlı";
}
