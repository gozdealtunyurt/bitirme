"""
İl/ilçe/mahalle dropdown verisi.
Primary kaynak: local JSON (hızlı, güvenilir, 81 il eksiksiz).
OSM: tesis verisi çekmek için kullanılır, dropdown için DEĞİL.
"""
from local_location_data import (
    get_sehirler as local_sehirler,
    get_ilceler as local_ilceler,
    get_mahalleler as local_mahalleler,
)


def get_sehirler() -> list[str]:
    """Türkiye'deki 81 ili döner (local JSON'dan, anlık)."""
    return local_sehirler()


def get_ilceler(sehir: str) -> list[str]:
    """Seçilen şehre ait ilçeleri döner (local JSON'dan)."""
    return local_ilceler(sehir)


def get_mahalleler(sehir: str, ilce: str) -> list[str]:
    """Seçilen ilçeye ait mahalleleri döner (local JSON'dan)."""
    return local_mahalleler(sehir, ilce)