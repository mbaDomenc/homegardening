import os
from typing import Optional, Dict, Any
import httpx
from datetime import datetime, timezone
import math

NASA_POWER_BASE = os.getenv("NASA_POWER_BASE_URL", "https://power.larc.nasa.gov")
NASA_TIMEOUT = float(os.getenv("NASA_POWER_TIMEOUT", "6"))

SENTINELS = {-999, -999.0, -9999, -9999.0}

def _day_of_year(dt: datetime) -> int:
    return int(dt.timetuple().tm_yday)

def _extraterrestrial_radiation_ra(lat_deg: float, doy: int) -> float:
    """
    Ra [MJ/m^2/day], FAO-56 eq.
    """
    lat = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365.0)          # inverse relative distance Earth-Sun
    delta = 0.409 * math.sin(2 * math.pi * doy / 365.0 - 1.39)    # solar declination
    w_s = math.acos(-math.tan(lat) * math.tan(delta))              # sunset hour angle
    G_sc = 0.0820  # MJ m^-2 min^-1
    Ra = (24 * 60 / math.pi) * G_sc * dr * (
        w_s * math.sin(lat) * math.sin(delta) +
        math.cos(lat) * math.cos(delta) * math.sin(w_s)
    )
    return Ra  # MJ/m^2/day

def compute_et0_hargreaves(lat: float, tmin: float, tmax: float, tmean: float,
                           now: Optional[datetime] = None) -> Optional[float]:
    """
    Hargreaves–Samani (FAO-56):
      ET0 = 0.0023 * (Tmean + 17.8) * sqrt(Tmax - Tmin) * Ra
    Ra in MJ/m^2/day, ET0 in mm/day.
    """
    try:
        now = now or datetime.utcnow()
        doy = _day_of_year(now)
        Ra = _extraterrestrial_radiation_ra(lat, doy)
        td = max(0.0, (tmax - tmin))
        et0 = 0.0023 * (tmean + 17.8) * math.sqrt(td) * Ra
        return round(float(et0), 2) if 0.0 <= et0 <= 20.0 else None
    except Exception:
        return None

def _first_value(d: Optional[Dict[str, Any]]) -> Optional[float]:
    if not isinstance(d, dict) or not d:
        return None
    try:
        k = sorted(d.keys())[0]  # daily → {"YYYYMMDD"}
        return d.get(k)
    except Exception:
        return None

def _san(v):
    return None if (v is None or v in SENTINELS) else float(v)

def get_daily_point(lat: float, lng: float, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """
    Chiama NASA POWER (community=AG) per il giorno 'now' (UTC) e restituisce parametri giornalieri
    + calcola ET0 con Hargreaves quando possibile.
    """
    try:
        now = now or datetime.utcnow().replace(tzinfo=timezone.utc)
        ymd = now.strftime("%Y%m%d")
        params = ",".join([
            "T2M", "T2M_MIN", "T2M_MAX",
            "RH2M", "WS2M",
            "ALLSKY_SFC_SW_DWN",
            "PRECTOTCORR"
        ])
        url = (
            f"{NASA_POWER_BASE}/api/temporal/daily/point"
            f"?parameters={params}&start={ymd}&end={ymd}"
            f"&latitude={lat}&longitude={lng}&community=AG&format=JSON"
        )

        with httpx.Client(timeout=NASA_TIMEOUT) as cli:
            r = cli.get(url)
            r.raise_for_status()
            j = r.json()

        data = j.get("properties", {}).get("parameter", {})
        t_mean = _san(_first_value(data.get("T2M")))
        t_min  = _san(_first_value(data.get("T2M_MIN")))
        t_max  = _san(_first_value(data.get("T2M_MAX")))
        rh     = _san(_first_value(data.get("RH2M")))
        ws     = _san(_first_value(data.get("WS2M")))
        rs     = _san(_first_value(data.get("ALLSKY_SFC_SW_DWN")))  # MJ/m2/day
        pr     = _san(_first_value(data.get("PRECTOTCORR")))        # mm/day

        et0 = None
        if t_min is not None and t_max is not None and t_mean is not None:
            et0 = compute_et0_hargreaves(lat, t_min, t_max, t_mean, now=now)

        return {
            "temp": t_mean if isinstance(t_mean, float) else None,
            "tempMin": t_min if isinstance(t_min, float) else None,
            "tempMax": t_max if isinstance(t_max, float) else None,
            "humidity": rh if isinstance(rh, float) else None,
            "wind": ws if isinstance(ws, float) else None,
            "solarRadiation": rs if isinstance(rs, float) else None,
            "precipDaily": pr if isinstance(pr, float) else None,
            "et0": et0 if isinstance(et0, float) else None,
            "source": "NASA_POWER",
            "ymd": ymd,
        }
    except Exception:
        return None