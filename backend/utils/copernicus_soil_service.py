import os
import time
from typing import Optional, Dict, Any
import httpx
from datetime import datetime

# Cache in memoria
_SOIL_CACHE: Dict[str, Dict[str, Any]] = {}

# Configurabili via ENV
_SOIL_TTL_SECONDS = int(os.getenv("SOIL_TTL_SECONDS", "1800"))          # 30 min
_SOIL_GRID_PRECISION = int(os.getenv("SOIL_GRID_PRECISION", "2"))       # 0.01° ≈ ~1km

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
# Variabili ERA5-Land esposte da Open-Meteo (unità: m3/m3)
HOURLY_VARS = "soil_moisture_0_to_7cm,soil_moisture_7_to_28cm"

def _grid_key(lat: float, lng: float, precision: int = None) -> str:
    p = _SOIL_GRID_PRECISION if precision is None else precision
    return f"{round(lat, p)}:{round(lng, p)}"

def _expired(entry: Dict[str, Any]) -> bool:
    return time.time() > entry.get("expires_at", 0)

def _parse_om_time(t: str) -> Optional[datetime]:
    """Gestisce anche eventuale suffisso 'Z'."""
    if not t:
        return None
    try:
        return datetime.fromisoformat(t.replace('Z', ''))
    except Exception:
        return None

def _find_start_index(times: list) -> int:
    """
    Trova l'indice della prima ora >= adesso nella lista times (ISO stringhe).
    Se fallisce, torna 0.
    """
    if not times:
        return 0
    now_utc = datetime.utcnow()
    try:
        for i, t in enumerate(times):
            dt = _parse_om_time(t)
            if dt and dt >= now_utc:
                return i
    except Exception:
        pass
    return 0

def _to_percent(vol: Optional[float]) -> Optional[float]:
    """
    Converte m3/m3 (0..1) → percentuale 0..100, clamp e round(1).
    Se input non valido, None.
    """
    if not isinstance(vol, (int, float)):
        return None
    # Alcune reanalisi possono dare valori > 1 in particolari condizioni → clamp
    pct = max(0.0, min(100.0, float(vol) * 100.0))
    return round(pct, 1)

def get_soil_moisture(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """
    Ritorna l'umidità del suolo derivata da ERA5-Land via Open-Meteo (senza token):
      {
        "soilMoisture0to7cm": <float %> | None,
        "soilMoisture7to28cm": <float %> | None,
        "source": "OPEN-METEO/ERA5-LAND",
        "raw": {
          "unit": "m3/m3",
          "value0to7": <float m3/m3> | None,
          "value7to28": <float m3/m3> | None,
          "time": <string ISO> | None
        }
      }
    Se errore → None (l'aggregator farà fallback su stima da RH aria).
    """
    # Guardia geo
    if lat is None or lng is None:
        return None

    key = _grid_key(lat, lng)
    if key in _SOIL_CACHE and not _expired(_SOIL_CACHE[key]):
        return _SOIL_CACHE[key]["value"]

    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": HOURLY_VARS,
        "forecast_days": 2,
        "timezone": "UTC",
    }

    try:
        with httpx.Client(timeout=6.0) as cli:
            r = cli.get(OPEN_METEO_URL, params=params)
            r.raise_for_status()
            j = r.json()
    except Exception:
        return None

    hourly = j.get("hourly", {}) or {}
    times = hourly.get("time", []) or []
    sm0_list = hourly.get("soil_moisture_0_to_7cm", []) or []
    sm7_list = hourly.get("soil_moisture_7_to_28cm", []) or []

    idx = _find_start_index(times)

    raw0 = None
    raw7 = None
    t_str = None

    # Prendi il valore all'ora "corrente" (fallback 0)
    if sm0_list and 0 <= idx < len(sm0_list):
        v0 = sm0_list[idx]
        if isinstance(v0, (int, float)):
            raw0 = float(v0)

    if sm7_list and 0 <= idx < len(sm7_list):
        v7 = sm7_list[idx]
        if isinstance(v7, (int, float)):
            raw7 = float(v7)

    if times and 0 <= idx < len(times):
        t_str = times[idx]

    value = {
        "soilMoisture0to7cm": _to_percent(raw0),
        "soilMoisture7to28cm": _to_percent(raw7),
        "source": "OPEN-METEO/ERA5-LAND",
        "raw": {
            "unit": "m3/m3",
            "value0to7": raw0,
            "value7to28": raw7,
            "time": t_str
        }
    }

    _SOIL_CACHE[key] = {
        "value": value,
        "expires_at": time.time() + _SOIL_TTL_SECONDS,
    }
    return value