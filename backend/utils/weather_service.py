import os
import time
from typing import Optional, Dict, Any, List
import httpx
from datetime import datetime

_WEATHER_CACHE: Dict[str, Dict[str, Any]] = {}

# Config da ENV
_WEATHER_TTL_SECONDS = int(os.getenv("WEATHER_TTL_SECONDS", "1800"))
_WEATHER_GRID_PRECISION = int(os.getenv("WEATHER_GRID_PRECISION", "2"))

def _grid_key(lat: float, lng: float, precision: int = None) -> str:
    p = _WEATHER_GRID_PRECISION if precision is None else precision
    return f"{round(lat, p)}:{round(lng, p)}"

def _expired(entry: Dict[str, Any]) -> bool:
    return time.time() > entry.get("expires_at", 0)

def _parse_om_time(t: str) -> Optional[datetime]:
    """Gestisce eventuale suffisso 'Z' (ISO UTC)."""
    if not t:
        return None
    try:
        return datetime.fromisoformat(str(t).replace('Z', ''))
    except Exception:
        return None

def _find_start_index(times: list) -> int:
    """
    Trova l'indice della prima ora >= adesso nella lista times di Open-Meteo.
    'times' è una lista di stringhe ISO (es. '2025-01-12T14:00').
    Se qualcosa va storto, torna 0.
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

def _avg(arr: List[float]) -> Optional[float]:
    arr = [x for x in (arr or []) if isinstance(x, (int, float))]
    if not arr:
        return None
    return sum(arr) / len(arr)

def get_weather(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """
    Usa Open-Meteo:
      - current_weather: temperatura
      - hourly: precipitation, relativehumidity_2m, temperature_2m, windspeed_10m
      - daily: temperature_2m_min, temperature_2m_max, precipitation_sum
    Ritorna:
      {
        temp, humidity, rainNext24h, windMean,
        dailyTempMin, dailyTempMax, precipDaily
      }
    """
    # Guardia se lat/lng non validi
    if lat is None or lng is None:
        return None

    key = _grid_key(lat, lng)
    if key in _WEATHER_CACHE and not _expired(_WEATHER_CACHE[key]):
        return _WEATHER_CACHE[key]["value"]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lng,
        "current_weather": "true",
        "hourly": "temperature_2m,relativehumidity_2m,precipitation,windspeed_10m",
        "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum",
        "forecast_days": 2,
        "timezone": "UTC",
    }

    try:
        with httpx.Client(timeout=6.0) as cli:
            r = cli.get(url, params=params)
            r.raise_for_status()
            j = r.json()
    except Exception:
        return None

    #current
    temp = j.get("current_weather", {}).get("temperature")

    #hourly
    hourly = j.get("hourly", {}) or {}
    times = hourly.get("time", []) or []
    start_idx = _find_start_index(times)

    prec_list = hourly.get("precipitation", []) or []
    hum_list  = hourly.get("relativehumidity_2m", []) or []
    wind_list = hourly.get("windspeed_10m", []) or []

    # Rain: somma prossime 24h
    rainNext24h = 0.0
    window_prec = prec_list[start_idx:start_idx + 24]
    if window_prec and all(isinstance(x, (int, float)) for x in window_prec):
        rainNext24h = float(sum(window_prec))

    #Humidity: media prossime 6h
    humidity = None
    small_h = hum_list[start_idx:start_idx + 6]
    if small_h and all(isinstance(x, (int, float)) for x in small_h):
        humidity = sum(small_h) / len(small_h)

    #Wind: media prossime 6h
    windMean = None
    small_w = wind_list[start_idx:start_idx + 6]
    if small_w and all(isinstance(x, (int, float)) for x in small_w):
        windMean = sum(small_w) / len(small_w)

    #daily (primo giorno = oggi)
    daily = j.get("daily", {}) or {}
    def _first(arr):
        return arr[0] if isinstance(arr, list) and arr else None

    daily_tmin = _first(daily.get("temperature_2m_min"))
    daily_tmax = _first(daily.get("temperature_2m_max"))
    daily_prcp = _first(daily.get("precipitation_sum"))

    value = {
        "temp": float(temp) if isinstance(temp, (int, float)) else None,
        "humidity": round(humidity, 1) if isinstance(humidity, (int, float)) else None,
        "rainNext24h": round(rainNext24h, 1),
        "windMean": round(windMean, 1) if isinstance(windMean, (int, float)) else None,
        "dailyTempMin": float(daily_tmin) if isinstance(daily_tmin, (int, float)) else None,
        "dailyTempMax": float(daily_tmax) if isinstance(daily_tmax, (int, float)) else None,
        "precipDaily": float(daily_prcp) if isinstance(daily_prcp, (int, float)) else None,
    }

    _WEATHER_CACHE[key] = {
        "value": value,
        "expires_at": time.time() + _WEATHER_TTL_SECONDS,
    }
    return value