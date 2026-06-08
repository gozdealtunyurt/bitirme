"""
Backend API - React frontend'in çağıracağı endpoint'ler.
Çalıştır: uvicorn api:app --reload --port 8000
"""
import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(__file__))

from osm_service import get_mahalle_data, KATEGORILER
from location_service import get_sehirler as osm_sehirler, get_ilceler as osm_ilceler, get_mahalleler as osm_mahalleler
from db_config import get_connection

app = FastAPI(title="MahalleScore API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── DROPDOWN ENDPOINT'LERI (OSM'den, cache'li) ─────────────


@app.get("/api/sehirler")
def api_sehirler():
    """Turkiye'deki 81 ili doner (OSM'den, cache'li)."""
    sehirler = osm_sehirler()
    if not sehirler:
        raise HTTPException(status_code=503, detail="OSM'den veri cekilemedi, tekrar deneyin")
    return {"sehirler": sehirler}


@app.get("/api/ilceler/{sehir}")
def api_ilceler(sehir: str):
    """Secilen sehre ait ilceleri doner (OSM'den, cache'li)."""
    ilceler = osm_ilceler(sehir)
    if not ilceler:
        raise HTTPException(status_code=503, detail="OSM'den veri cekilemedi, tekrar deneyin")
    return {"ilceler": ilceler}


@app.get("/api/mahalleler/{sehir}/{ilce}")
def api_mahalleler(sehir: str, ilce: str):
    """Secilen ilceye ait mahalleleri doner (OSM'den, cache'li)."""
    mahalleler = osm_mahalleler(sehir, ilce)
    if not mahalleler:
        raise HTTPException(status_code=503, detail="OSM'den veri cekilemedi, tekrar deneyin")
    return {"mahalleler": mahalleler}


# ─── VERİ ENDPOINT'LERI ─────────────────────────────────────


@app.get("/api/mahalle-veri/{sehir}/{ilce}/{mahalle}")
def get_mahalle_veri(sehir: str, ilce: str, mahalle: str, refresh: bool = False):
    """Mahalle skorlarini doner. DB'de varsa cache'den, yoksa OSM'den ceker."""
    try:
        result = get_mahalle_data(sehir, ilce, mahalle, force_refresh=refresh)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/mahalle-detay/{sehir}/{ilce}/{mahalle}")
def get_mahalle_detay(sehir: str, ilce: str, mahalle: str, refresh: bool = False):
    """Mahalle skorlari + mekanlarin listesi."""
    try:
        result = get_mahalle_data(sehir, ilce, mahalle, force_refresh=refresh)
        mahalle_id = result["mahalle_id"]

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        mekanlar = {}
        for kategori in KATEGORILER:
            cursor.execute(
                "SELECT isim, tip, lat, lon FROM kategori_verileri WHERE mahalle_id=%s AND kategori=%s",
                (mahalle_id, kategori)
            )
            mekanlar[kategori] = cursor.fetchall()

        cursor.close()
        conn.close()

        result["mekanlar"] = mekanlar
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
