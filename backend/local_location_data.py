"""
Local JSON'dan il/ilçe/mahalle verisi çeker.
JSON'daki isimler BÜYÜK HARF formatında (ör: 'ADANA', 'BOZTAHTA Mah.')
Bu modül onları düzgün Title Case'e çevirir ve normalize ederek eşleştirir.
"""
import json
import os
import unicodedata

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "frontend",
    "src",
    "data",
    "il_ilce_mahalle.json",
)

# Türkçe büyük/küçük harf eşleşme tabloları
_TR_UPPER = str.maketrans(
    "abcçdefgğhıijklmnoöprsştuüvyz",
    "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ"
)
_TR_LOWER = str.maketrans(
    "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ",
    "abcçdefgğhıijklmnoöprsştuüvyz"
)


def _load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _norm(value: str) -> str:
    """Karşılaştırma için normalize et: küçük harf, aksansız."""
    text = str(value or "").strip()
    # Türkçe özel harfleri koru, sonra aksanları kaldır
    text = text.translate(_TR_LOWER)
    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def _to_title(text: str) -> str:
    """
    BÜYÜK HARF metni Türkçe uyumlu Title Case'e çevirir.
    'BOZTAHTA Mah.' → 'Boztahta Mah.'
    'CERİTLER Mah.' → 'Ceritler Mah.'
    """
    lower = text.translate(_TR_LOWER)
    words = lower.split()
    result = []
    for w in words:
        if w:
            first = w[0].translate(_TR_UPPER)
            result.append(first + w[1:])
    return " ".join(result)


def _format_display(name: str) -> str:
    """
    JSON'daki ismi kullanıcıya gösterilecek formata çevirir.
    'BOZTAHTA Mah.' → 'Boztahta Mah.'
    'ADANA' → 'Adana'
    """
    return _to_title(name)


def _find_key(mapping: dict, name: str):
    """Normalize edilmiş isimle dict key'i bul."""
    target = _norm(name)
    for key in mapping:
        if _norm(key) == target:
            return key
    return None


def get_sehirler() -> list[str]:
    data = _load_data()
    return sorted(
        [_format_display(k) for k in data.keys()],
        key=lambda x: _norm(x)
    )


def get_ilceler(sehir: str) -> list[str]:
    data = _load_data()
    sehir_key = _find_key(data, sehir)
    if not sehir_key:
        return []
    return sorted(
        [_format_display(k) for k in data[sehir_key].keys()],
        key=lambda x: _norm(x)
    )


def get_mahalleler(sehir: str, ilce: str) -> list[str]:
    data = _load_data()
    sehir_key = _find_key(data, sehir)
    if not sehir_key:
        return []
    ilce_key = _find_key(data[sehir_key], ilce)
    if not ilce_key:
        return []
    raw = data[sehir_key][ilce_key]
    seen = set()
    result = []
    for m in raw:
        display = _format_display(m)
        if display not in seen:
            seen.add(display)
            result.append(display)
    return sorted(result, key=lambda x: _norm(x))