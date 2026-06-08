"""
Manuel doğrulama tablosu için istatistiksel kontrol scripti.

Kullanım:
  python istatistiksel_dogrulama.py
  python istatistiksel_dogrulama.py manuel_dogrulama_tablosu.csv

Beklenen CSV kolonları:
  model_skoru
  manuel_skor

Not:
  manuel_skor kolonu yoksa manuel_beklenen_seviye metni yaklaşık puana çevrilir.
  En güvenilir kullanım için CSV'ye 0-100 arası manuel_skor kolonu eklenmesi önerilir.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


DEFAULT_CSV = Path("manuel_dogrulama_tablosu.csv")

SEVIYE_PUANLARI = {
    "cok dusuk": 20,
    "çok düşük": 20,
    "dusuk": 35,
    "düşük": 35,
    "dusuk-orta": 45,
    "düşük-orta": 45,
    "orta": 55,
    "orta-yuksek": 72,
    "orta-yüksek": 72,
    "yuksek": 85,
    "yüksek": 85,
    "cok yuksek": 95,
    "çok yüksek": 95,
}


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _sample_variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    return sum((value - avg) ** 2 for value in values) / (len(values) - 1)


def pearson_correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = _mean(xs)
    mean_y = _mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return None
    return numerator / (denom_x * denom_y)


def cronbach_alpha(items: list[list[float]]) -> float | None:
    """
    rows x items biçiminde veri bekler.
    Bu kullanımda iki değerlendirici/madde vardır: model_skoru ve manuel_skor.
    """
    if not items or len(items) < 2:
        return None
    item_count = len(items[0])
    if item_count < 2:
        return None

    item_columns = [
        [row[index] for row in items]
        for index in range(item_count)
    ]
    item_variance_sum = sum(_sample_variance(column) for column in item_columns)
    total_scores = [sum(row) for row in items]
    total_variance = _sample_variance(total_scores)
    if total_variance == 0:
        return None

    return (item_count / (item_count - 1)) * (1 - item_variance_sum / total_variance)


def read_validation_rows(path: Path) -> tuple[list[dict], list[str]]:
    warnings = []
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        if "model_skoru" not in fieldnames:
            warnings.append("CSV'de model_skoru kolonu yok.")
        if "manuel_skor" not in fieldnames:
            warnings.append(
                "CSV'de manuel_skor kolonu yok; manuel_beklenen_seviye metninden yaklaşık puan üretilecek."
            )

        for line_no, row in enumerate(reader, start=2):
            model_score = _to_float(row.get("model_skoru"))
            manual_score = _to_float(row.get("manuel_skor"))

            if manual_score is None:
                level = _normalize_text(row.get("manuel_beklenen_seviye"))
                manual_score = SEVIYE_PUANLARI.get(level)

            if model_score is None or manual_score is None:
                warnings.append(f"{line_no}. satır atlandı: model_skoru veya manuel_skor eksik.")
                continue

            rows.append({
                "label": f"{row.get('il', '')} / {row.get('ilce', '')} / {row.get('mahalle', '')}",
                "model_skoru": model_score,
                "manuel_skor": manual_score,
            })

    return rows, warnings


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not path.exists():
        print(f"Dosya bulunamadı: {path}")
        return 1

    rows, warnings = read_validation_rows(path)

    print("İstatistiksel Doğrulama Raporu")
    print("=" * 34)
    print(f"Dosya: {path}")
    print(f"Kullanılan satır sayısı: {len(rows)}")

    if warnings:
        print("\nUyarılar:")
        for warning in warnings:
            print(f"- {warning}")

    if len(rows) < 3:
        print("\nSonuç hesaplanamadı: En az 3 dolu gözlem önerilir.")
        return 0

    model_scores = [row["model_skoru"] for row in rows]
    manual_scores = [row["manuel_skor"] for row in rows]

    pearson = pearson_correlation(model_scores, manual_scores)
    alpha = cronbach_alpha([[row["model_skoru"], row["manuel_skor"]] for row in rows])

    print("\nSonuçlar:")
    print(f"- Pearson korelasyon: {pearson:.3f}" if pearson is not None else "- Pearson korelasyon: hesaplanamadı")
    print(f"- Cronbach's Alpha: {alpha:.3f}" if alpha is not None else "- Cronbach's Alpha: hesaplanamadı")

    print("\nYorumlama Notu:")
    print("- Pearson korelasyon model skoru ile manuel değerlendirme arasındaki doğrusal ilişkiyi gösterir.")
    print("- Cronbach's Alpha iki ölçümün birlikte ne kadar tutarlı davrandığına dair destekleyici bir göstergedir.")
    print("- Az sayıda mahalle ile yapılan analiz rapor eki niteliğindedir; genelleme amacı taşımaz.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
