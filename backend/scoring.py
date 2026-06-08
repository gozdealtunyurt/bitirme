"""
Gerçek Yaşanılabilirlik Skoru Hesaplama Sistemi

Arevibes mantığı: "Sayı değil, erişilebilirlik önemli."

Her kategori için şu soruyu sorar:
  "Mahallenin merkezinden en yakın tesise kaç dakika yürünür?"

Skor Faktörleri:
  1. Yakınlık     - En yakın tesis kaç km uzakta?
  2. Çeşitlilik  - Kaç farklı tesis tipi erişilebilir?
  3. Yoğunluk    - 1km içinde kaç tesis var? (alternatif seçenek)

Faktör ve kategori ağırlıkları AHP (Analitik Hiyerarşi Süreci)
ikili karşılaştırma matrislerinden hesaplanır.

İdeal mesafeler (yürüme):
  - 500m  → 100 puan (5-6 dakika)
  - 1km   → 75 puan  (12 dakika)
  - 2km   → 40 puan  (25 dakika, zorlayıcı)
  - 3km+  → 0 puan   (araç gerekli)
"""
import math
import json
from datetime import datetime
from db_config import get_connection


# ─── KATEGORİ YAKIN LIK EŞİKLERİ (km) ───────────────────
# Her kategori için "kabul edilebilir" mesafe farklıdır.
# Hastaneye 3km normal ama bakkala 3km çok uzak.

ERISIM_ESIKLERI = {
    "saglik": {
        "hospital": {"ideal": 2.0, "max": 5.0},    # Hastaneye 2km normal
        "clinic":   {"ideal": 1.0, "max": 3.0},    # Kliniğe 1km iyi
        "doctors":  {"ideal": 1.0, "max": 3.0},
        "pharmacy": {"ideal": 0.5, "max": 1.5},    # Eczane çok yakın olmalı
    },
    "egitim": {
        "university": {"ideal": 3.0, "max": 8.0},
        "college":    {"ideal": 2.0, "max": 6.0},
        "school":     {"ideal": 0.8, "max": 2.0},  # İlkokul yürüme mesafesinde
        "kindergarten": {"ideal": 0.5, "max": 1.5},
    },
    "yesil_alan": {
        "nature_reserve": {"ideal": 3.0, "max": 8.0},
        "park":           {"ideal": 0.5, "max": 1.5},  # Park çok yakın olmalı
        "garden":         {"ideal": 0.5, "max": 1.5},
        "playground":     {"ideal": 0.3, "max": 1.0},
    },
    "ulasim": {
        "station":          {"ideal": 1.5, "max": 4.0},
        "tram_stop":        {"ideal": 0.5, "max": 1.5},
        "platform":         {"ideal": 0.5, "max": 1.5},
        "bus_stop":         {"ideal": 0.3, "max": 1.0},  # Otobüs durağı çok yakın
    },
    "sosyal_imkanlar": {
        "supermarket": {"ideal": 0.5, "max": 1.5},
        "bank":        {"ideal": 1.0, "max": 2.5},
        "restaurant":  {"ideal": 0.5, "max": 1.5},
        "cafe":        {"ideal": 0.5, "max": 1.5},
        "bakery":      {"ideal": 0.3, "max": 1.0},
        "fast_food":   {"ideal": 0.5, "max": 1.5},
        "atm":         {"ideal": 0.5, "max": 1.5},
    },
}

# Tip ağırlıkları: daha önemli tesisler daha yüksek katkı sağlar
TIP_AGIRLIKLARI = {
    "saglik": {
        "hospital": 5, "clinic": 3, "doctors": 3, "pharmacy": 2,
    },
    "egitim": {
        "university": 5, "college": 4, "school": 3, "kindergarten": 2,
    },
    "yesil_alan": {
        "nature_reserve": 4, "park": 3, "garden": 2, "playground": 2,
    },
    "ulasim": {
        "station": 5, "tram_stop": 4, "platform": 3, "bus_stop": 2,
    },
    "sosyal_imkanlar": {
        "supermarket": 3, "bank": 3, "restaurant": 2,
        "cafe": 2, "bakery": 2, "fast_food": 1, "atm": 2,
    },
}

MAX_TIP_SAYISI = {
    "saglik": 4, "egitim": 4, "yesil_alan": 4,
    "ulasim": 4, "sosyal_imkanlar": 7,
}

# Tesis varsa ama mahalle merkezine göre ideal erişim eşiğinin dışındaysa
# kategori tamamen 0 görünmesin. 0, "hiç tesis yok" anlamına saklanır.
UZAK_ERISIM_TABAN_SKORU = {
    "saglik": 10,
    "egitim": 10,
    "yesil_alan": 8,
    "ulasim": 8,
    "sosyal_imkanlar": 6,
}


# ─── AHP AĞIRLIKLARI ─────────────────────────────────────────
# Saaty ölçeği: 1=eșit önemli, 2=hafif güçlü, 3=güçlü, ...
# CR < 0.10 ise ikili karşılaştırmalar tutarlı kabul edilir.

RI_DEGERLERI = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
}


def _ahp_agirliklari(kriterler: list[str], matris: list[list[float]]) -> tuple[dict[str, float], float]:
    """
    AHP ağırlıklarını geometrik ortalama yöntemiyle hesaplar.
    Returns: (kriter -> ağırlık, tutarlılık_oranı)
    """
    n = len(kriterler)
    geometrik_ortalamalar = [
        math.prod(satir) ** (1 / n)
        for satir in matris
    ]
    toplam = sum(geometrik_ortalamalar)
    agirlik_listesi = [deger / toplam for deger in geometrik_ortalamalar]

    lambda_max = 0
    for i, satir in enumerate(matris):
        agirlikli_toplam = sum(satir[j] * agirlik_listesi[j] for j in range(n))
        lambda_max += agirlikli_toplam / agirlik_listesi[i]
    lambda_max /= n

    ci = (lambda_max - n) / (n - 1) if n > 1 else 0
    ri = RI_DEGERLERI.get(n, 1.49)
    cr = ci / ri if ri else 0

    return dict(zip(kriterler, agirlik_listesi)), cr


ALT_FAKTORLER = ["yakinlik", "cesitlilik", "yogunluk"]
ALT_FAKTOR_KARSILASTIRMA = [
    [1,   2,   3],
    [1/2, 1,   2],
    [1/3, 1/2, 1],
]
ALT_FAKTOR_AGIRLIKLARI, ALT_FAKTOR_TUTARLILIK = _ahp_agirliklari(
    ALT_FAKTORLER,
    ALT_FAKTOR_KARSILASTIRMA,
)

KATEGORI_SIRASI = ["saglik", "egitim", "yesil_alan", "ulasim", "sosyal_imkanlar"]
# Hedef önem sırası:
# sağlık 0.30, eğitim 0.25, ulaşım 0.20, yeşil alan 0.15, sosyal imkanlar 0.10.
# Matris bu oranlardan türetildiği için CR değeri 0'a yakın çıkar.
KATEGORI_KARSILASTIRMA = [
    [1,     1.2,   2,     1.5,   3],
    [1/1.2, 1,     1.667, 1.25,  2.5],
    [1/2,   1/1.667, 1,   0.75,  1.5],
    [1/1.5, 1/1.25, 1/0.75, 1,   2],
    [1/3,   1/2.5, 1/1.5, 1/2,   1],
]
KATEGORI_AGIRLIKLARI, KATEGORI_TUTARLILIK = _ahp_agirliklari(
    KATEGORI_SIRASI,
    KATEGORI_KARSILASTIRMA,
)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """İki koordinat arası mesafe (km)."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _hesapla_yakinlik_skoru(tesisler: list, kategori: str) -> tuple[int, dict]:
    """
    Faktör 1: Yakınlık (%50)

    Her tip için en yakın tesise olan mesafeyi ölç.
    Mesafeyi ideal/max eşiklerine göre 0-100 arası skora çevir.
    Tiplerin ağırlıklı ortalamasını al.
    """
    esikler = ERISIM_ESIKLERI.get(kategori, {})
    agirliklar = TIP_AGIRLIKLARI.get(kategori, {})

    if not tesisler:
        return 0, {}

    # Tip başına en yakın mesafeyi bul
    tip_en_yakin = {}
    for t in tesisler:
        if not t.get("lat") or not t.get("lon") or not t.get("merkez_lat"):
            continue
        tip = t.get("tip", "")
        mesafe = t.get("mesafe_km", 999)
        if tip not in tip_en_yakin or mesafe < tip_en_yakin[tip]:
            tip_en_yakin[tip] = mesafe

    if not tip_en_yakin:
        # Koordinat yoksa tesis sayısına göre basit skor
        return min(len(tesisler) * 10, 60), {}

    # Her tip için yakınlık skoru
    tip_skorlari = {}
    toplam_agirlik = 0
    agirlikli_toplam = 0

    for tip, en_yakin in tip_en_yakin.items():
        esik = esikler.get(tip, {"ideal": 1.0, "max": 3.0})
        ideal = esik["ideal"]
        maks = esik["max"]
        agirlik = agirliklar.get(tip, 1)

        if en_yakin <= ideal:
            skor = 100
        elif en_yakin >= maks:
            skor = 0
        else:
            # Lineer düşüş: ideal → max arasında 100 → 0
            skor = round(100 * (1 - (en_yakin - ideal) / (maks - ideal)))

        tip_skorlari[tip] = {"mesafe_km": round(en_yakin, 2), "skor": skor}
        agirlikli_toplam += skor * agirlik
        toplam_agirlik += agirlik

    nihai = round(agirlikli_toplam / toplam_agirlik) if toplam_agirlik > 0 else 0
    return nihai, tip_skorlari


def _hesapla_cesitlilik_skoru(tesisler: list, kategori: str, merkez_lat: float, merkez_lon: float) -> int:
    """
    Faktör 2: Çeşitlilik (%30)

    1km yarıçap içinde kaç farklı tesis tipi erişilebilir?
    Hastane + klinik + eczane = 3 tip = yüksek çeşitlilik
    """
    if not tesisler:
        return 0

    # 1.5km içindeki farklı tipler (mahalle ölçeği)
    tipler_yakin = set()
    for t in tesisler:
        if t.get("mesafe_km", 999) <= 1.5 and t.get("tip"):
            tipler_yakin.add(t["tip"])

    max_tip = MAX_TIP_SAYISI.get(kategori, 4)
    return round(min((len(tipler_yakin) / max_tip) * 100, 100))


def _hesapla_yogunluk_skoru(tesisler: list) -> int:
    """
    Faktör 3: Yoğunluk (%20)

    1km içinde kaç tesis var? Alternatif seçenek sağlar.
    """
    yakin_sayisi = sum(1 for t in tesisler if t.get("mesafe_km", 999) <= 1.0)

    # 0 → 0, 1 → 40, 3 → 70, 5+ → 100
    if yakin_sayisi == 0:
        return 0
    elif yakin_sayisi == 1:
        return 40
    elif yakin_sayisi == 2:
        return 55
    elif yakin_sayisi <= 4:
        return 70
    elif yakin_sayisi <= 7:
        return 85
    else:
        return 100


def _hesapla_uzak_erisim_taban_skoru(tesisler: list, kategori: str) -> int:
    """
    Tesis var ama tamamı yakın erişim eşiğinin dışındaysa düşük bir taban puan verir.
    Böylece 0 puan yalnızca gerçekten tesis/veri yok durumunu ifade eder.
    """
    if not tesisler:
        return 0

    mesafeler = [
        t["mesafe_km"]
        for t in tesisler
        if t.get("mesafe_km") is not None
    ]
    if not mesafeler:
        return min(len(tesisler) * 5, UZAK_ERISIM_TABAN_SKORU.get(kategori, 6))

    en_yakin = min(mesafeler)
    taban = UZAK_ERISIM_TABAN_SKORU.get(kategori, 6)

    if en_yakin <= 2.0:
        return taban
    if en_yakin <= 3.0:
        return max(round(taban * 0.7), 1)
    if en_yakin <= 5.0:
        return max(round(taban * 0.4), 1)
    return 1


def hesapla_kategori_skoru(mahalle_id: int, kategori: str, merkez_lat: float = None, merkez_lon: float = None) -> tuple[int, dict]:
    """
    Bir kategori için nihai yaşanılabilirlik skoru.
    3 faktörün ağırlıklı ortalaması.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Mahallenin centroid'ini al (yoksa parametreden)
    if not merkez_lat or not merkez_lon:
        cursor.execute(
            "SELECT centroid_lat, centroid_lon FROM mahalleler WHERE id=%s",
            (mahalle_id,)
        )
        row = cursor.fetchone()
        if row and row.get("centroid_lat"):
            merkez_lat = row["centroid_lat"]
            merkez_lon = row["centroid_lon"]

    cursor.execute(
        "SELECT isim, tip, lat, lon FROM kategori_verileri WHERE mahalle_id=%s AND kategori=%s",
        (mahalle_id, kategori)
    )
    raw_tesisler = cursor.fetchall()
    cursor.close()
    conn.close()

    # Her tesise merkeze olan mesafeyi ekle
    tesisler = []
    for t in raw_tesisler:
        tesis = dict(t)
        if merkez_lat and merkez_lon and t.get("lat") and t.get("lon"):
            tesis["mesafe_km"] = _haversine(merkez_lat, merkez_lon, t["lat"], t["lon"])
            tesis["merkez_lat"] = merkez_lat
        else:
            tesis["mesafe_km"] = None
        tesisler.append(tesis)

    # 3 faktörü hesapla
    yakinlik_skor, tip_detaylari = _hesapla_yakinlik_skoru(tesisler, kategori)
    cesitlilik_skor = _hesapla_cesitlilik_skoru(tesisler, kategori, merkez_lat, merkez_lon)
    yogunluk_skor = _hesapla_yogunluk_skoru(tesisler)

    # AHP ağırlıklı ortalama
    nihai_skor = round(
        yakinlik_skor * ALT_FAKTOR_AGIRLIKLARI["yakinlik"] +
        cesitlilik_skor * ALT_FAKTOR_AGIRLIKLARI["cesitlilik"] +
        yogunluk_skor * ALT_FAKTOR_AGIRLIKLARI["yogunluk"]
    )

    if tesisler and nihai_skor == 0:
        nihai_skor = _hesapla_uzak_erisim_taban_skoru(tesisler, kategori)

    # En yakın tesisin mesafesini bul
    mesafeler = [t["mesafe_km"] for t in tesisler if t.get("mesafe_km") is not None]
    en_yakin_mesafe = round(min(mesafeler), 2) if mesafeler else None

    detay = {
        "tesis_sayisi": len(tesisler),
        "yakinlik_skoru": yakinlik_skor,
        "cesitlilik_skoru": cesitlilik_skor,
        "yogunluk_skoru": yogunluk_skor,
        "uzak_erisim_taban_skoru": nihai_skor if tesisler and yakinlik_skor == 0 and cesitlilik_skor == 0 and yogunluk_skor == 0 else 0,
        "en_yakin_mesafe_km": en_yakin_mesafe,
        "tip_detaylari": tip_detaylari,
        "farkli_tipler": list({t.get("tip", "") for t in tesisler if t.get("tip")}),
        "ahp_agirliklari": ALT_FAKTOR_AGIRLIKLARI,
        "ahp_tutarlilik_orani": round(ALT_FAKTOR_TUTARLILIK, 4),
    }

    return nihai_skor, detay


def hesapla_tum_skorlar(mahalle_id: int) -> tuple[dict, int, dict]:
    """Tüm kategoriler için skorları hesaplar ve DB'ye kaydeder."""
    # Centroid'i bir kez çek
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT centroid_lat, centroid_lon FROM mahalleler WHERE id=%s",
        (mahalle_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    merkez_lat = row["centroid_lat"] if row else None
    merkez_lon = row["centroid_lon"] if row else None

    kategoriler = KATEGORI_SIRASI
    skorlar = {}
    detaylar = {}

    for kategori in kategoriler:
        skor, detay = hesapla_kategori_skoru(mahalle_id, kategori, merkez_lat, merkez_lon)
        skorlar[kategori] = skor
        detaylar[kategori] = detay

    toplam = round(
        sum(skorlar[kategori] * KATEGORI_AGIRLIKLARI[kategori] for kategori in kategoriler)
    )

    # DB'ye kaydet
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO skorlar
           (mahalle_id, saglik, egitim, yesil_alan, ulasim, sosyal_imkanlar, toplam_skor,
            saglik_detay, egitim_detay, yesil_alan_detay, ulasim_detay, sosyal_imkanlar_detay)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE
           saglik=%s, egitim=%s, yesil_alan=%s, ulasim=%s, sosyal_imkanlar=%s, toplam_skor=%s,
           saglik_detay=%s, egitim_detay=%s, yesil_alan_detay=%s,
           ulasim_detay=%s, sosyal_imkanlar_detay=%s""",
        (
            mahalle_id,
            skorlar["saglik"], skorlar["egitim"], skorlar["yesil_alan"],
            skorlar["ulasim"], skorlar["sosyal_imkanlar"], toplam,
            json.dumps(detaylar["saglik"], ensure_ascii=False),
            json.dumps(detaylar["egitim"], ensure_ascii=False),
            json.dumps(detaylar["yesil_alan"], ensure_ascii=False),
            json.dumps(detaylar["ulasim"], ensure_ascii=False),
            json.dumps(detaylar["sosyal_imkanlar"], ensure_ascii=False),
            # ON DUPLICATE KEY UPDATE değerleri
            skorlar["saglik"], skorlar["egitim"], skorlar["yesil_alan"],
            skorlar["ulasim"], skorlar["sosyal_imkanlar"], toplam,
            json.dumps(detaylar["saglik"], ensure_ascii=False),
            json.dumps(detaylar["egitim"], ensure_ascii=False),
            json.dumps(detaylar["yesil_alan"], ensure_ascii=False),
            json.dumps(detaylar["ulasim"], ensure_ascii=False),
            json.dumps(detaylar["sosyal_imkanlar"], ensure_ascii=False),
        )
    )

    cursor.execute(
        "UPDATE mahalleler SET last_fetched=%s WHERE id=%s",
        (datetime.now(), mahalle_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return skorlar, toplam, detaylar
