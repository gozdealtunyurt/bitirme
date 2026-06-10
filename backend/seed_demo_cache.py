"""
Demo mahalle havuzunu OSM'den cekip veritabanina cache'ler.

Kullanim:
  cd backend
  python seed_demo_cache.py --limit 10
  python seed_demo_cache.py --force-refresh
"""
import argparse
import json
import time
from pathlib import Path

from osm_service import get_mahalle_data


DEFAULT_LIST_PATH = Path(__file__).with_name("demo_seed_locations.json")


def load_locations(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        locations = json.load(f)
    if not isinstance(locations, list):
        raise ValueError("Seed dosyasi liste formatinda olmali.")
    return locations


def seed_locations(locations: list[dict], force_refresh: bool, start: int, limit: int | None, sleep_sec: float) -> int:
    selected = locations[start:]
    if limit is not None:
        selected = selected[:limit]

    success_count = 0
    for idx, item in enumerate(selected, start=start + 1):
        sehir = item["sehir"]
        ilce = item["ilce"]
        mahalle = item["mahalle"]
        title = f"{idx}/{len(locations)} {sehir} > {ilce} > {mahalle}"
        print(f"\n[SEED] {title}")
        try:
            result = get_mahalle_data(sehir, ilce, mahalle, force_refresh=force_refresh)
            source = result.get("veri_kaynagi")
            trust = result.get("veri_guveni")
            score = result.get("toplam_skor")
            ref_count = result.get("referans_mahalle_sayisi")
            ref_text = f", referans={ref_count}" if ref_count else ""
            print(f"[OK] skor={score}, kaynak={source}, guven={trust}{ref_text}")
            success_count += 1
        except Exception as exc:
            print(f"[HATA] {title}: {exc}")
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    print(f"\nBitti. Basarili: {success_count}/{len(selected)}")
    return success_count


def main():
    parser = argparse.ArgumentParser(description="Demo mahalle havuzunu cache'e alir.")
    parser.add_argument("--file", default=str(DEFAULT_LIST_PATH), help="Seed JSON dosyasi")
    parser.add_argument("--force-refresh", action="store_true", help="Cache olsa bile yeniden OSM'den cek")
    parser.add_argument("--start", type=int, default=0, help="Listedeki baslangic index'i")
    parser.add_argument("--limit", type=int, default=None, help="Kac mahalle islenecek")
    parser.add_argument("--sleep", type=float, default=1.5, help="Istekler arasi bekleme saniyesi")
    args = parser.parse_args()

    locations = load_locations(Path(args.file))
    seed_locations(
        locations=locations,
        force_refresh=args.force_refresh,
        start=max(args.start, 0),
        limit=args.limit,
        sleep_sec=max(args.sleep, 0),
    )


if __name__ == "__main__":
    main()
