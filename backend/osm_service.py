"""
OSM'den mahalle tesis verisi çeker ve MySQL'e kaydeder.

Strateji:
  1. OSM'de mahalle idari sınırı varsa → sınır içinden çek (en doğru)
  2. Sınır yoksa → Nominatim'den merkez koordinatı al, 1km yarıçap içinden çek
     (yaklaşık ama veri döner; response'da 'yaklasik_alan' flag'i True olur)
"""
import requests
import time
import json
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional, Tuple
from db_config import get_connection

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_HTTP_TIMEOUT = 15
OVERPASS_MAX_RETRIES = 2

# Sınır bulunamayan mahallelerde son çare olarak kullanılacak yarıçap.
# Büyük yarıçap komşu mahalleleri skora dahil ettiği için bilinçli olarak dar tutulur.
FALLBACK_RADIUS_M = 1500
EXPANDED_FALLBACK_RADIUS_M = 3000
WIDE_FALLBACK_RADIUS_M = 5000
LIVE_FETCH_BUDGET_SEC = 70

KATEGORILER = {
    "saglik": {
        "tags": [
            ("amenity", "hospital"),
            ("amenity", "clinic"),
            ("amenity", "pharmacy"),
            ("amenity", "doctors"),
        ]
    },
    "egitim": {
        "tags": [
            ("amenity", "school"),
            ("amenity", "kindergarten"),
            ("amenity", "college"),
            ("amenity", "university"),
        ]
    },
    "yesil_alan": {
        "tags": [
            ("leisure", "park"),
            ("leisure", "garden"),
            ("leisure", "playground"),
            ("leisure", "nature_reserve"),
        ]
    },
    "ulasim": {
        "tags": [
            ("highway", "bus_stop"),
            ("railway", "tram_stop"),
            ("railway", "station"),
            ("public_transport", "platform"),
        ]
    },
    "sosyal_imkanlar": {
        "tags": [
            ("shop", "supermarket"),
            ("amenity", "restaurant"),
            ("amenity", "cafe"),
            ("amenity", "bank"),
            ("amenity", "atm"),
            ("amenity", "fast_food"),
            ("shop", "bakery"),
        ]
    },
}


# ─── YARDIMCI ────────────────────────────────────────────────

def _escape_overpass(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _tr_lower(text: str) -> str:
    return text.translate(str.maketrans(
        "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ",
        "abcçdefgğhıijklmnoöprsştuüvyz"
    ))


def _tr_title(text: str) -> str:
    """Türkçe uyumlu Title Case — boşluk ve tire sonrasını büyütür."""
    lower = _tr_lower(text)
    upper_map = str.maketrans(
        "abcçdefgğhıijklmnoöprsştuüvyz",
        "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ"
    )
    result = []
    cap = True
    for ch in lower:
        if ch in (" ", "-"):
            result.append(ch)
            cap = True
        elif cap:
            result.append(ch.translate(upper_map))
            cap = False
        else:
            result.append(ch)
    return "".join(result)


def _format_osm_name(name: str) -> str:
    if name == name.upper():
        name = _tr_title(name)
    if name.endswith(" Mah."):
        name = name[:-5] + " Mahallesi"
    return name


def _canonical_mahalle_name(name: str) -> str:
    return _format_osm_name(name.strip())


def _normalize_ilce(ilce: str) -> str:
    """
    JSON ilçe ismini OSM formatına çevirir.
    BAYBURT-İL MERKEZİ  → Bayburt
    GÜZELYURT           → Güzelyurt  (değişmez)
    """
    # Önce Türkçe title case
    ilce = _tr_title(ilce)
    # '-İl Merkezi' ekini kaldır (title case sonrası)
    lower = _tr_lower(ilce)
    for suffix in ["-il merkezi", " il merkezi"]:
        if lower.endswith(suffix):
            return ilce[: -len(suffix)]
    return ilce


def _extract_core_name(name: str) -> str:
    for suffix in [" Mahallesi", " Mah.", " mahallesi", " mah."]:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _name_variants(name: str) -> list[str]:
    formatted = _format_osm_name(name)
    core = _extract_core_name(formatted)
    seen = set()
    result = []
    for v in [
        name,
        formatted,
        core,
        f"{core} Mahallesi",
        f"{core} Mah.",
        f"{core} Mahalle",
    ]:
        v = v.strip()
        if v and v not in seen:
            result.append(v)
            seen.add(v)
    return result


def _ilce_name_variants(ilce: str) -> list[str]:
    normalized = _normalize_ilce(ilce)
    formatted = _tr_title(ilce) if ilce == ilce.upper() else ilce
    seen = set()
    result = []
    for v in [formatted, normalized]:
        v = v.strip()
        if v and v not in seen:
            result.append(v)
            seen.add(v)
    return result


def _relation_union_lines(admin_level: int, names: list[str], area_filter: str = None) -> str:
    area_part = f"({area_filter})" if area_filter else ""
    lines = []
    for n in names:
        safe = _escape_overpass(n)
        lines.append(
            f'rel["boundary"="administrative"]["admin_level"="{admin_level}"]["name"="{safe}"]{area_part};'
        )
    return "\n      ".join(lines)


def _mahalle_relation_lines(names: list[str]) -> str:
    lines = []
    for n in names:
        safe = _escape_overpass(n)
        lines.append(
            f'rel["boundary"="administrative"]["admin_level"~"^(8|9|10)$"]["name"="{safe}"](area.ilce);'
        )
    return "\n      ".join(lines)


def _nominatim_area_id(osm_type: str, osm_id: int) -> Optional[int]:
    """
    Overpass area id dönüşümü:
      relation -> 3600000000 + id
      way      -> 2400000000 + id
    """
    if not osm_id:
        return None
    if osm_type == "relation":
        return 3600000000 + int(osm_id)
    if osm_type == "way":
        return 2400000000 + int(osm_id)
    return None


def _matches_place_context(result: dict, sehir: str, ilce: str) -> bool:
    text = _tr_lower(result.get("display_name", ""))
    sehir_ok = _tr_lower(sehir) in text
    ilce_ok = _tr_lower(_normalize_ilce(ilce)) in text or _tr_lower(ilce) in text
    return sehir_ok and ilce_ok


def _normalize_match_text(text: str) -> str:
    text = _tr_lower(_extract_core_name(_format_osm_name(text or "")))
    text = re.sub(r"\b(mahallesi|mahalle|mah)\b", "", text)
    text = re.sub(r"[^a-zçğıöşü0-9]+", "", text)
    return text


def _names_match(candidate: str, target: str) -> bool:
    candidate_core = _normalize_match_text(candidate)
    target_core = _normalize_match_text(target)
    return bool(candidate_core and target_core and candidate_core == target_core)


def _names_similar(candidate: str, target: str) -> bool:
    candidate_core = _normalize_match_text(candidate)
    target_core = _normalize_match_text(target)
    if not candidate_core or not target_core:
        return False
    if candidate_core == target_core:
        return True
    return SequenceMatcher(None, candidate_core, target_core).ratio() >= 0.86


def _nominatim_candidate_names(result: dict) -> list[str]:
    names = []
    for key in ("name", "display_name", "namedetails"):
        value = result.get(key)
        if isinstance(value, str):
            names.append(value.split(",")[0])
        elif isinstance(value, dict):
            names.extend(str(v) for v in value.values() if v)

    address = result.get("address") or {}
    for key in ("neighbourhood", "suburb", "quarter", "city_district", "village", "town"):
        value = address.get(key)
        if value:
            names.append(str(value))
    return names


def _matches_mahalle_name(result: dict, mahalle: str) -> bool:
    return any(_names_similar(candidate, mahalle) for candidate in _nominatim_candidate_names(result))


def _select_nominatim_result(results: list[dict], sehir: str, ilce: str, mahalle: str, require_polygon: bool = False) -> Optional[dict]:
    for item in results:
        if not _matches_place_context(item, sehir, ilce):
            continue
        if not _matches_mahalle_name(item, mahalle):
            continue
        if require_polygon:
            geojson = item.get("geojson") or {}
            if geojson.get("type") not in ("Polygon", "MultiPolygon"):
                continue
        return item
    return None


def _elapsed_sec(started_at: float) -> float:
    return time.monotonic() - started_at


# ─── OVERPASS ────────────────────────────────────────────────

def overpass_query(query: str, max_retries: int = OVERPASS_MAX_RETRIES, timeout_sec: int = OVERPASS_HTTP_TIMEOUT):
    """
    Tüm sunucuları sırayla dener. Herhangi biri 200 dönerse sonuç verir.
    406 dahil her hata durumunda bir sonraki sunucuya geçer.
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "MahalleScore/1.0 (educational local project)",
    }
    for attempt in range(max_retries):
        url = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        try:
            print(f"  Sunucu: {url.split('/')[2]} (deneme {attempt + 1})")
            response = requests.post(
                url,
                data={"data": query},
                headers=headers,
                timeout=timeout_sec
            )
            if response.status_code == 200:
                return response.json()
            # 429/504 → beklemeden varsa diğer Overpass sunucusuna geç.
            if response.status_code in (429, 504):
                print(f"  {response.status_code}, sonraki Overpass sunucusu deneniyor...")
                continue
            # 406 veya diğer hatalar → hemen sonraki sunucuya geç
            print(f"  Overpass hata {response.status_code}, sonraki sunucu deneniyor...")
            time.sleep(2)
            continue
        except Exception as e:
            print(f"  Bağlantı hatası: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            continue
    print("  Tüm Overpass sunucuları başarısız.")
    return None


# ─── CENTROİD: OSM sınır relation'ından ──────────────────────

def _fetch_centroid_from_boundary(sehir: str, ilce: str, mahalle: str) -> Tuple[Optional[float], Optional[float]]:
    """OSM idari sınır relation'ından centroid çeker."""
    sehir_lines = _relation_union_lines(4, _name_variants(sehir))
    ilce_lines = _relation_union_lines(6, _ilce_name_variants(ilce), "area.sehir")
    mahalle_lines = _mahalle_relation_lines(_name_variants(mahalle))

    query = f"""
    [out:json][timeout:18];
    (
      {sehir_lines}
    )->.sehirRel;
    .sehirRel map_to_area -> .sehir;
    (
      {ilce_lines}
    )->.ilceRel;
    .ilceRel map_to_area -> .ilce;
    (
      {mahalle_lines}
    );
    out center;
    """

    data = overpass_query(query, timeout_sec=18)
    if not data:
        return None, None

    elements = data.get("elements", [])
    if not elements:
        return None, None

    el = elements[0]
    center = el.get("center", {})
    lat = center.get("lat") or el.get("lat")
    lon = center.get("lon") or el.get("lon")

    if lat and lon:
        print(f"  Sınır centroid'i bulundu: {lat:.4f}, {lon:.4f}")
        return float(lat), float(lon)
    return None, None


# ─── CENTROİD: Nominatim fallback ────────────────────────────

def _fetch_centroid_from_nominatim(sehir: str, ilce: str, mahalle: str) -> Tuple[Optional[float], Optional[float]]:
    """
    OSM sınırı bulunamayan mahalleler için Nominatim geocoding kullanır.
    Türkiye + il + ilçe + mahalle kombinasyonunu arar.
    """
    # Farklı sorgu formatları dene
    ilce_norm = _normalize_ilce(ilce)
    mahalle_core = _extract_core_name(mahalle)
    queries = [
        f"{mahalle_core} Mahallesi, {ilce_norm}, {sehir}, Turkey",
        f"{mahalle_core}, {ilce_norm}, {sehir}, Turkey",
        f"{mahalle_core}, {sehir}, Turkey",          # ilçesiz dene
    ]

    headers = {"User-Agent": "MahalleScore/1.0 (educational project)"}

    for q in queries:
        try:
            resp = requests.get(
                NOMINATIM_URL,
                params={
                    "q": q,
                    "format": "json",
                    "limit": 5,
                    "countrycodes": "tr",
                    "addressdetails": 1,
                    "namedetails": 1,
                },
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            results = resp.json()
            item = _select_nominatim_result(results, sehir, ilce, mahalle)
            if item:
                lat = float(item["lat"])
                lon = float(item["lon"])
                print(f"  Nominatim centroid ({q!r}): {lat:.4f}, {lon:.4f}")
                return lat, lon
            time.sleep(1)  # Nominatim rate limit
        except Exception as e:
            print(f"  Nominatim hata: {e}")
            continue

    return None, None


# ─── CENTROİD: Ana fonksiyon ─────────────────────────────────

def fetch_mahalle_centroid(sehir: str, ilce: str, mahalle: str) -> Tuple[Optional[float], Optional[float], bool]:
    """
    Mahallenin merkez koordinatını bulur.
    Returns: (lat, lon, sinir_var)
      sinir_var=True  → OSM sınırı bulundu, tesis çekimi sınır içinden yapılacak
      sinir_var=False → Nominatim/ilçe merkezi kullanıldı, yarıçap sorgusu yapılacak
    """
    # Önce OSM sınır relation'ını dene
    lat, lon = _fetch_centroid_from_boundary(sehir, ilce, mahalle)
    if lat and lon:
        return lat, lon, True

    print(f"  OSM sınırı bulunamadı, Nominatim deneniyor...")
    time.sleep(1)

    # Nominatim fallback
    lat, lon = _fetch_centroid_from_nominatim(sehir, ilce, mahalle)
    if lat and lon:
        return lat, lon, False

    print(f"  Centroid hiç bulunamadı.")
    return None, None, False


# ─── TESİS VERİSİ: Sınır içinden ────────────────────────────

def _build_nwr_lines(area_filter: str) -> str:
    """Tüm kategorilerin tüm tag'lerini tek blokta döner."""
    lines = []
    for kat, info in KATEGORILER.items():
        for key, value in info["tags"]:
            lines.append(f'nwr({area_filter})["{key}"="{value}"];')
    return "\n      ".join(lines)


def _build_kategori_nwr_lines(kategori: str, area_filter: str) -> str:
    """Tek kategoriye ait tag'leri Overpass nwr bloklarına çevirir."""
    lines = []
    for key, value in KATEGORILER[kategori]["tags"]:
        lines.append(f'nwr({area_filter})["{key}"="{value}"];')
    return "\n      ".join(lines)


def _parse_all_kategoriler(data: dict) -> dict[str, list]:
    """Overpass yanıtını kategori → tesis listesi şeklinde parse eder."""
    # Her tag hangi kategoriye ait?
    tag_to_kategori = {}
    for kat, info in KATEGORILER.items():
        for key, value in info["tags"]:
            tag_to_kategori[(key, value)] = kat

    result = {k: [] for k in KATEGORILER}
    seen = {k: set() for k in KATEGORILER}
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")

        # Hangi kategoriye giriyor?
        kategori = None
        tip = None
        for key, value in [(k, v) for kat_info in KATEGORILER.values() for k, v in kat_info["tags"]]:
            if tags.get(key) == value:
                kategori = tag_to_kategori.get((key, value))
                tip = value
                break

        if kategori:
            unique_key = (el.get("type"), el.get("id"))
            if unique_key in seen[kategori]:
                continue
            seen[kategori].add(unique_key)
            result[kategori].append({
                "osm_id": el.get("id"),
                "isim": tags.get("name", ""),
                "tip": tip or tags.get("amenity") or tags.get("shop") or tags.get("leisure") or "",
                "lat": lat,
                "lon": lon,
            })

    return result


def _total_result_count(results: dict[str, list]) -> int:
    if not results:
        return 0
    return sum(len(items) for items in results.values())


def _empty_kategori_results() -> dict[str, list]:
    return {k: [] for k in KATEGORILER}


def _extract_boundary_center(data: dict) -> Tuple[Optional[float], Optional[float]]:
    """Kombine Overpass yanıtındaki mahalle relation merkezini döndürür."""
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        if el.get("type") == "relation" and tags.get("boundary") == "administrative":
            center = el.get("center", {})
            lat = center.get("lat") or el.get("lat")
            lon = center.get("lon") or el.get("lon")
            if lat and lon:
                return float(lat), float(lon)
    return None, None


def fetch_boundary_snapshot(sehir: str, ilce: str, mahalle: str) -> Tuple[Optional[float], Optional[float], Optional[dict[str, list]]]:
    """
    Mahalle sınırını, sınır centroid'ini ve tüm kategori verisini tek Overpass
    çağrısında çeker. Sınır bulunamazsa (None, None, None) döner.
    """
    nwr_lines = _build_nwr_lines("area.mahalle")
    sehir_lines = _relation_union_lines(4, _name_variants(sehir))
    ilce_lines = _relation_union_lines(6, _ilce_name_variants(ilce), "area.sehir")
    mahalle_lines = _mahalle_relation_lines(_name_variants(mahalle))

    query = f"""
    [out:json][timeout:18];
    (
      {sehir_lines}
    )->.sehirRel;
    .sehirRel map_to_area -> .sehir;
    (
      {ilce_lines}
    )->.ilceRel;
    .ilceRel map_to_area -> .ilce;
    (
      {mahalle_lines}
    )->.mahalleRel;
    .mahalleRel out center tags;
    .mahalleRel map_to_area -> .mahalle;
    (
      {nwr_lines}
    );
    out center tags qt;
    """

    data = overpass_query(query, timeout_sec=18)
    if not data:
        return None, None, None

    lat, lon = _extract_boundary_center(data)
    if not lat or not lon:
        return None, None, None

    print(f"  Sınır ve tesisler tek sorguda bulundu: {lat:.4f}, {lon:.4f}")
    return lat, lon, _parse_all_kategoriler(data)


def fetch_boundary_snapshot_from_nominatim(sehir: str, ilce: str, mahalle: str) -> Tuple[Optional[float], Optional[float], Optional[dict[str, list]]]:
    """
    Overpass ad araması sınırı bulamazsa Nominatim'den OSM relation/way id'sini
    alır ve aynı resmi OSM alanını Overpass area id ile sorgular.
    """
    ilce_norm = _normalize_ilce(ilce)
    mahalle_core = _extract_core_name(mahalle)
    queries = [
        f"{mahalle_core} Mahallesi, {ilce_norm}, {sehir}, Turkey",
        f"{mahalle_core}, {ilce_norm}, {sehir}, Turkey",
    ]
    headers = {"User-Agent": "MahalleScore/1.0 (educational project)"}

    for q in queries:
        try:
            resp = requests.get(
                NOMINATIM_URL,
                params={
                    "q": q,
                    "format": "json",
                    "limit": 5,
                    "countrycodes": "tr",
                    "polygon_geojson": 1,
                    "addressdetails": 1,
                    "namedetails": 1,
                    "extratags": 1,
                },
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                continue

            item = _select_nominatim_result(resp.json(), sehir, ilce, mahalle, require_polygon=True)
            if item:
                area_id = _nominatim_area_id(item.get("osm_type"), item.get("osm_id"))
                if not area_id:
                    time.sleep(1)
                    continue

                lat = float(item["lat"])
                lon = float(item["lon"])
                nwr_lines = _build_nwr_lines("area.mahalle")
                query = f"""
                [out:json][timeout:18];
                area({area_id})->.mahalle;
                (
                  {nwr_lines}
                );
                out center tags qt;
                """

                data = overpass_query(query, timeout_sec=18)
                if data is None:
                    time.sleep(1)
                    continue

                print(f"  Nominatim OSM alanı kullanıldı ({item.get('osm_type')} {item.get('osm_id')}): {lat:.4f}, {lon:.4f}")
                return lat, lon, _parse_all_kategoriler(data)

            time.sleep(1)
        except Exception as e:
            print(f"  Nominatim sınır hatası: {e}")
            continue

    return None, None, None


def fetch_boundary_snapshot_from_containing_area(sehir: str, ilce: str, mahalle: str) -> Tuple[Optional[float], Optional[float], Optional[dict[str, list]]]:
    """
    Son resmi OSM denemesi: Nominatim'in bulduğu merkez noktasından, o noktanın
    içinde kaldığı idari alanları bulur. İsimle arama kaçırıyorsa bu yakalayabilir.
    """
    lat, lon = _fetch_centroid_from_nominatim(sehir, ilce, mahalle)
    if not lat or not lon:
        return None, None, None

    query = f"""
    [out:json][timeout:6];
    is_in({lat},{lon})->.containing;
    area.containing["boundary"="administrative"]["admin_level"~"^(8|9|10)$"];
    out tags;
    """
    data = overpass_query(query, max_retries=1, timeout_sec=6)
    if not data:
        return lat, lon, None

    candidates = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:tr") or tags.get("official_name") or ""
        if _names_match(name, mahalle):
            candidates.append(el)

    if not candidates:
        return lat, lon, None

    area_id = candidates[0].get("id")
    if not area_id:
        return lat, lon, None

    nwr_lines = _build_nwr_lines("area.mahalle")
    query = f"""
    [out:json][timeout:18];
    area({area_id})->.mahalle;
    (
      {nwr_lines}
    );
    out center tags qt;
    """
    data = overpass_query(query, timeout_sec=18)
    if data is None:
        return lat, lon, None

    print(f"  Merkez noktanın içinde bulunduğu OSM alanı kullanıldı (area {area_id}): {lat:.4f}, {lon:.4f}")
    return lat, lon, _parse_all_kategoriler(data)


def fetch_all_kategoriler_by_boundary(sehir: str, ilce: str, mahalle: str) -> dict[str, list]:
    """Mahalle sınırı içindeki TÜM kategorileri TEK sorguda çeker."""
    nwr_lines = _build_nwr_lines("area.mahalle")
    sehir_lines = _relation_union_lines(4, _name_variants(sehir))
    ilce_lines = _relation_union_lines(6, _ilce_name_variants(ilce), "area.sehir")
    mahalle_lines = _mahalle_relation_lines(_name_variants(mahalle))

    query = f"""
    [out:json][timeout:18];
    (
      {sehir_lines}
    )->.sehirRel;
    .sehirRel map_to_area -> .sehir;
    (
      {ilce_lines}
    )->.ilceRel;
    .ilceRel map_to_area -> .ilce;
    (
      {mahalle_lines}
    )->.mahalleRel;
    .mahalleRel map_to_area -> .mahalle;
    (
      {nwr_lines}
    );
    out center tags qt;
    """
    data = overpass_query(query, timeout_sec=18)
    if not data:
        return {k: [] for k in KATEGORILER}
    return _parse_all_kategoriler(data)


def fetch_all_kategoriler_by_radius_split(lat: float, lon: float, radius_m: int) -> Optional[dict[str, list]]:
    """
    Tek büyük radius sorgusu Overpass'ta patlarsa aynı gerçek veriyi kategori
    bazında daha küçük sorgularla çeker. Kısmi sonuç döndürmez.
    """
    combined = {k: [] for k in KATEGORILER}
    for kategori in KATEGORILER:
        nwr_lines = _build_kategori_nwr_lines(kategori, f"around:{radius_m},{lat},{lon}")
        query = f"""
        [out:json][timeout:18];
        (
          {nwr_lines}
        );
        out center tags qt;
        """
        data = overpass_query(query, timeout_sec=18)
        if data is None:
            print(f"  {kategori} kategori sorgusu yanıt vermedi.")
            return None
        parsed = _parse_all_kategoriler(data)
        combined[kategori] = parsed.get(kategori, [])
    return combined


def fetch_all_kategoriler_by_radius(lat: float, lon: float, radius_m: int = FALLBACK_RADIUS_M) -> Optional[dict[str, list]]:
    """Koordinat + yarıçap içindeki TÜM kategorileri çeker."""
    nwr_lines = _build_nwr_lines(f"around:{radius_m},{lat},{lon}")

    query = f"""
    [out:json][timeout:15];
    (
      {nwr_lines}
    );
    out center tags qt;
    """
    data = overpass_query(query, timeout_sec=15)
    if data is not None:
        return _parse_all_kategoriler(data)

    print("  Tek radius sorgusu yanıt vermedi; kategori bazlı radius sorguları deneniyor...")
    return fetch_all_kategoriler_by_radius_split(lat, lon, radius_m)


# ─── DB FONKSİYONLARI ────────────────────────────────────────

def get_or_create_mahalle(sehir: str, ilce: str, mahalle: str) -> Tuple[int, Optional[datetime]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, last_fetched FROM mahalleler WHERE sehir=%s AND ilce=%s AND mahalle=%s",
        (sehir, ilce, mahalle)
    )
    row = cursor.fetchone()
    if row:
        cursor.close()
        conn.close()
        return row[0], row[1]

    cursor.execute(
        "INSERT INTO mahalleler (sehir, ilce, mahalle) VALUES (%s, %s, %s)",
        (sehir, ilce, mahalle)
    )
    conn.commit()
    mahalle_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return mahalle_id, None


def save_centroid_to_db(mahalle_id: int, lat: float, lon: float, yaklasik: bool = False):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE mahalleler SET centroid_lat=%s, centroid_lon=%s, yaklasik_alan=%s WHERE id=%s",
        (lat, lon, yaklasik, mahalle_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_centroid_from_db(mahalle_id: int) -> Tuple[Optional[float], Optional[float]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT centroid_lat, centroid_lon FROM mahalleler WHERE id=%s",
        (mahalle_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row and row[0] and row[1]:
        return float(row[0]), float(row[1])
    return None, None


def save_kategori_to_db(mahalle_id: int, kategori: str, results: list[dict]):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM kategori_verileri WHERE mahalle_id=%s AND kategori=%s",
        (mahalle_id, kategori)
    )
    for r in results:
        cursor.execute(
            """INSERT INTO kategori_verileri (mahalle_id, kategori, osm_id, isim, tip, lat, lon)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (mahalle_id, kategori, r["osm_id"], r["isim"], r["tip"], r["lat"], r["lon"])
        )
    conn.commit()
    cursor.close()
    conn.close()


def get_total_kategori_count(mahalle_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM kategori_verileri WHERE mahalle_id=%s", (mahalle_id,)
    )
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count


def get_scores_from_db(mahalle_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM skorlar WHERE mahalle_id=%s", (mahalle_id,))
    skor_row = cursor.fetchone()

    cursor.execute("SELECT * FROM mahalleler WHERE id=%s", (mahalle_id,))
    mahalle_row = cursor.fetchone()

    cursor.execute(
        "SELECT kategori, COUNT(*) as c FROM kategori_verileri WHERE mahalle_id=%s GROUP BY kategori",
        (mahalle_id,)
    )
    counts = {row["kategori"]: row["c"] for row in cursor.fetchall()}
    for k in KATEGORILER:
        counts.setdefault(k, 0)

    cursor.close()
    conn.close()

    yaklasik_alan = bool(mahalle_row.get("yaklasik_alan"))
    last_fetched = mahalle_row.get("last_fetched")
    last_fetched_iso = last_fetched.isoformat() if last_fetched else None
    detay_kolonlari = {
        "saglik": "saglik_detay",
        "egitim": "egitim_detay",
        "yesil_alan": "yesil_alan_detay",
        "ulasim": "ulasim_detay",
        "sosyal_imkanlar": "sosyal_imkanlar_detay",
    }
    skor_detaylari = {}
    for kategori, kolon in detay_kolonlari.items():
        raw = skor_row.get(kolon) if skor_row else None
        if raw:
            try:
                skor_detaylari[kategori] = json.loads(raw)
            except Exception:
                skor_detaylari[kategori] = {}
        else:
            skor_detaylari[kategori] = {}

    return {
        "mahalle_id": mahalle_id,
        "sehir": mahalle_row["sehir"],
        "ilce": mahalle_row["ilce"],
        "mahalle": mahalle_row["mahalle"],
        "last_fetched": last_fetched_iso,
        "yaklasik_alan": yaklasik_alan,
        "veri_kaynagi": "yaklasik_yaricap" if yaklasik_alan else "osm_sinir",
        "veri_guveni": "orta" if yaklasik_alan else "yuksek",
        "veri_uyarisi": (
            "OSM'de idari mahalle siniri bulunamadigi icin veriler merkez koordinat etrafindaki yaklasik yaricapla hesaplanmistir."
            if yaklasik_alan else None
        ),
        "counts": counts,
        "skorlar": {
            "saglik": skor_row["saglik"] if skor_row else 0,
            "egitim": skor_row["egitim"] if skor_row else 0,
            "yesil_alan": skor_row["yesil_alan"] if skor_row else 0,
            "ulasim": skor_row["ulasim"] if skor_row else 0,
            "sosyal_imkanlar": skor_row["sosyal_imkanlar"] if skor_row else 0,
        },
        "skor_detaylari": skor_detaylari,
        "toplam_skor": skor_row["toplam_skor"] if skor_row else 0,
    }


# ─── ANA FONKSİYON ────────────────────────────────────────────

def get_mahalle_data(sehir: str, ilce: str, mahalle: str, force_refresh: bool = False) -> dict:
    from scoring import hesapla_tum_skorlar

    started_at = time.monotonic()
    mahalle = _canonical_mahalle_name(mahalle)
    mahalle_id, last_fetched = get_or_create_mahalle(sehir, ilce, mahalle)

    # Cache kontrolü: sadece gerçek tesis verisi olan kayıtları cache kabul et.
    # Veri-yetersiz/0 tesis sonuçları last_fetched dolu olsa bile tekrar denenir.
    cache_dolu = get_total_kategori_count(mahalle_id) > 0
    if cache_dolu and not force_refresh:
        print(f"Cache'den getiriliyor: {mahalle} (son çekim: {last_fetched})")
        return get_scores_from_db(mahalle_id)

    print(f"OSM'den çekiliyor: {sehir} > {ilce} > {mahalle}")
    bos_sonuc_gecerli = False

    # 1. En doğru mod: OSM idari mahalle sınırı içinden çek.
    centroid_lat, centroid_lon, tum_sonuclar = fetch_boundary_snapshot(sehir, ilce, mahalle)
    sinir_var = bool(centroid_lat and centroid_lon and tum_sonuclar is not None)
    veri_kaynagi = "osm_sinir" if sinir_var else None

    if not sinir_var:
        print("  Overpass ad araması sınırı bulamadı; Nominatim OSM alanı deneniyor...")
        centroid_lat, centroid_lon, tum_sonuclar = fetch_boundary_snapshot_from_nominatim(sehir, ilce, mahalle)
        sinir_var = bool(centroid_lat and centroid_lon and tum_sonuclar is not None)
        if sinir_var:
            veri_kaynagi = "nominatim_osm_sinir"

    if not sinir_var:
        print("  Nominatim alanı bulunamadı; merkez noktanın içindeki OSM sınırı deneniyor...")
        centroid_lat, centroid_lon, tum_sonuclar = fetch_boundary_snapshot_from_containing_area(sehir, ilce, mahalle)
        sinir_var = bool(centroid_lat and centroid_lon and tum_sonuclar is not None)
        if sinir_var:
            veri_kaynagi = "osm_iceren_alan"

    if sinir_var:
        if _total_result_count(tum_sonuclar) == 0 and centroid_lat and centroid_lon:
            print(f"  Boundary returned 0 places; trying ~{EXPANDED_FALLBACK_RADIUS_M}m radius fallback...")
            fallback_sonuclar = fetch_all_kategoriler_by_radius(
                centroid_lat,
                centroid_lon,
                radius_m=EXPANDED_FALLBACK_RADIUS_M,
            )
            if fallback_sonuclar is not None and _total_result_count(fallback_sonuclar) > 0:
                tum_sonuclar = fallback_sonuclar
                sinir_var = False
                veri_kaynagi = "osm_sinir_yetersiz_yaklasik_yaricap"
            else:
                print(f"  Radius fallback returned 0 places; trying ~{WIDE_FALLBACK_RADIUS_M}m wide fallback...")
                fallback_sonuclar = fetch_all_kategoriler_by_radius(
                    centroid_lat,
                    centroid_lon,
                    radius_m=WIDE_FALLBACK_RADIUS_M,
                )
                if fallback_sonuclar is not None and _total_result_count(fallback_sonuclar) > 0:
                    tum_sonuclar = fallback_sonuclar
                    sinir_var = False
                    veri_kaynagi = "osm_sinir_yetersiz_genis_yaricap"
        if _total_result_count(tum_sonuclar) == 0:
            sinir_var = False
            veri_kaynagi = "osm_sinir_veri_yetersiz"
        print("  Çekim modu: idari mahalle sınırı")
    else:
        print("  Mahalle sınırı bulunamadı; merkez + yarıçap fallback kullanılacak.")
        if not centroid_lat or not centroid_lon:
            centroid_lat, centroid_lon = get_centroid_from_db(mahalle_id)
        if not centroid_lat:
            print("  Mahalle merkezi Nominatim'den aranıyor...")
            centroid_lat, centroid_lon = _fetch_centroid_from_nominatim(sehir, ilce, mahalle)

        if not centroid_lat:
            print("  Nominatim merkez bulamadı; son çare idari sınır merkezi deneniyor...")
            centroid_lat, centroid_lon = _fetch_centroid_from_boundary(sehir, ilce, mahalle)

        if not centroid_lat:
            print("  Merkez bulunamadı, veri çekilemeyecek.")
            if cache_dolu:
                result = get_scores_from_db(mahalle_id)
                result["uyari"] = "Canli OSM cekimi basarisiz oldu; mevcut cache sonucu gosteriliyor."
                return result
            raise RuntimeError("OSM/Nominatim bu mahalle icin merkez veya sinir verisi dondurmedi.")

        print(f"  Çekim modu: yaklaşık ~{FALLBACK_RADIUS_M}m yarıçap")
        veri_kaynagi = "yaklasik_yaricap"
        tum_sonuclar = fetch_all_kategoriler_by_radius(centroid_lat, centroid_lon)

        if tum_sonuclar is None:
            print("  Overpass yarıçap sorgusu yanıt vermedi.")
            if cache_dolu:
                result = get_scores_from_db(mahalle_id)
                result["uyari"] = "Canli OSM cekimi basarisiz oldu; mevcut cache sonucu gosteriliyor."
                return result
            raise RuntimeError("OSM/Overpass yogun veya yanit vermiyor; bu mahalle icin skor su an hesaplanamadi.")

    if (
        not sinir_var
        and _total_result_count(tum_sonuclar) == 0
        and centroid_lat
        and centroid_lon
        and _elapsed_sec(started_at) < LIVE_FETCH_BUDGET_SEC
    ):
        print(f"  İlk çekim 0 tesis döndürdü; ~{EXPANDED_FALLBACK_RADIUS_M}m geniş fallback deneniyor...")
        tum_sonuclar = fetch_all_kategoriler_by_radius(
            centroid_lat,
            centroid_lon,
            radius_m=EXPANDED_FALLBACK_RADIUS_M,
        )
        if tum_sonuclar is None:
            print("  Geniş fallback Overpass yanıtı alamadı.")
            if cache_dolu:
                result = get_scores_from_db(mahalle_id)
                result["uyari"] = "Canli OSM cekimi basarisiz oldu; mevcut cache sonucu gosteriliyor."
                return result
            raise RuntimeError("OSM/Overpass yogun veya yanit vermiyor; bu mahalle icin skor su an hesaplanamadi.")
        sinir_var = False
        veri_kaynagi = "yaklasik_yaricap_genis"

    if (
        not sinir_var
        and _total_result_count(tum_sonuclar) == 0
        and centroid_lat
        and centroid_lon
        and _elapsed_sec(started_at) < LIVE_FETCH_BUDGET_SEC
    ):
        print(f"  Wide fallback returned 0 places; trying ~{WIDE_FALLBACK_RADIUS_M}m showcase fallback...")
        wide_sonuclar = fetch_all_kategoriler_by_radius(
            centroid_lat,
            centroid_lon,
            radius_m=WIDE_FALLBACK_RADIUS_M,
        )
        if wide_sonuclar is not None:
            tum_sonuclar = wide_sonuclar
        sinir_var = False
        veri_kaynagi = "yaklasik_yaricap_cok_genis"

    elif not sinir_var and _total_result_count(tum_sonuclar) == 0 and centroid_lat and centroid_lon:
        print("  İlk çekim 0 tesis döndürdü; süre bütçesi dolduğu için geniş fallback atlandı.")
        bos_sonuc_gecerli = True

    if not sinir_var and _total_result_count(tum_sonuclar) == 0 and not bos_sonuc_gecerli:
        print("  OSM veri çekimi 0 tesis döndürdü; boş sonuç başarılı cache olarak kaydedilmeyecek.")
        if cache_dolu:
            result = get_scores_from_db(mahalle_id)
            result["uyari"] = "Canli OSM cekimi basarisiz oldu; mevcut cache sonucu gosteriliyor."
            return result
        print("  OSM returned 0 places; returning a low-confidence empty result instead of failing.")
        tum_sonuclar = _empty_kategori_results()
        veri_kaynagi = veri_kaynagi or "osm_veri_yetersiz"
        bos_sonuc_gecerli = True

    all_counts = {}
    save_centroid_to_db(mahalle_id, centroid_lat, centroid_lon, yaklasik=not sinir_var)
    for kategori, results in tum_sonuclar.items():
        save_kategori_to_db(mahalle_id, kategori, results)
        all_counts[kategori] = len(results)
        print(f"  {kategori}: {len(results)} tesis")

    # 3. Skor hesapla
    skorlar, toplam, detaylar = hesapla_tum_skorlar(mahalle_id)
    last_fetched_iso = datetime.now().isoformat()
    veri_yetersiz = _total_result_count(tum_sonuclar) == 0

    return {
        "mahalle_id": mahalle_id,
        "sehir": sehir,
        "ilce": ilce,
        "mahalle": mahalle,
        "last_fetched": last_fetched_iso,
        "yaklasik_alan": not sinir_var,
        "veri_kaynagi": veri_kaynagi,
        "veri_guveni": "dusuk" if veri_yetersiz else ("yuksek" if sinir_var else "orta"),
        "veri_uyarisi": (
            "OSM'de bu mahalle icin yeterli tesis verisi bulunamadigi icin skorlar veri yetersiz olarak gosterilmistir."
            if veri_yetersiz else (
                "OSM'de idari mahalle siniri bulunamadigi veya sinir verisi yetersiz oldugu icin veriler merkez koordinat etrafindaki yaklasik yaricapla hesaplanmistir."
                if not sinir_var else None
            )
        ),
        "counts": all_counts,
        "skorlar": skorlar,
        "skor_detaylari": detaylar,
        "toplam_skor": toplam,
    }
