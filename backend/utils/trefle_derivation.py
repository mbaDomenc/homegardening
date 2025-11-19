from typing import Any, Dict, Optional

def derive_sunlight(growth: Dict[str, Any]) -> Optional[str]:
    shade_tol = (growth.get("shade_tolerance") or "").lower()
    if shade_tol == "tolerant":
        return "ombra"
    if shade_tol == "intermediate":
        return "mezz'ombra"

    light = growth.get("light")
    if isinstance(light, (int, float)):
        if light >= 7:
            return "pieno sole"
        if 4 <= light < 7:
            return "mezz'ombra"
        return "ombra"

    return None

def derive_watering_interval_days(growth: Dict[str, Any]) -> Optional[int]:
    precip_min = growth.get("precipitation_min")
    precip_max = growth.get("precipitation_max")
    hum = (growth.get("atmospheric_humidity") or "").lower()

    base = None
    mm = precip_min if isinstance(precip_min, (int, float)) else precip_max
    if isinstance(mm, (int, float)):
        if mm >= 60:
            base = 8
        elif 30 <= mm < 60:
            base = 5
        else:
            base = 3
    else:
        base = 4

    if hum == "high":
        base += 2
    elif hum == "low":
        base = max(2, base - 1)

    return int(base)