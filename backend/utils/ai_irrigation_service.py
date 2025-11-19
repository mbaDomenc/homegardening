# backend/utils/ai_irrigation_service.py
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import math

# Helpers: fuzzy membership

def tri(x, a, b, c):
    """Triangolare."""
    if x is None:
        return 0.0
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return (x - a) / (b - a + 1e-9)
    return (c - x) / (c - b + 1e-9)

def trap(x, a, b, c, d):
    """Trapezoidale."""
    if x is None:
        return 0.0
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if a < x < b:
        return (x - a) / (b - a + 1e-9)
    return (d - x) / (d - c + 1e-9)

def clamp01(v):
    return max(0.0, min(1.0, float(v)))

# Baseline per stage (fallback)
def baseline_from_stage(stage: Optional[str]) -> int:
    """
    Fallback per intervallo se manca plant.wateringIntervalDays.
    """
    if not stage:
        return 3
    s = stage.lower()
    if "semina" in s:
        return 2
    if "cresc" in s:
        return 2
    if "fiori" in s:
        return 2
    if "raccolta" in s:
        return 3
    return 3


# Input normalization
def _extract_soil_moisture(weather: Dict[str, Any]) -> Optional[float]:
    if weather is None:
        return None
    # privilegia 0-7 cm se presente
    sm07 = weather.get("soilMoisture0to7cm")
    if isinstance(sm07, (int, float)):
        return float(sm07)
    approx = weather.get("soilMoistureApprox")
    if isinstance(approx, (int, float)):
        return float(approx)
    return None

def _days_since_last(last_dt: Optional[datetime], now: datetime) -> Optional[int]:
    if not last_dt:
        return None
    try:
        return max(0, (now - last_dt).days)
    except Exception:
        return None

# Fuzzification
def fuzzify_inputs(signals: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """
    Ritorna membership per:
    - soil: dry, moist, wet
    - rain: low, medium, high
    - ratio (days/baseline): early, due, overdue
    - temp: low, moderate, high
    - et0: low, moderate, high (se disponibile)
    """
    soil = signals.get("soilMoisture")  # 0..100
    rain = signals.get("rainNext24h")   # mm
    ratio = signals.get("ratio")        # daysSinceLast / baselineInterval
    temp  = signals.get("temp")         # °C
    et0   = signals.get("et0")          # mm/day approx

    out = {}

    # Suolo (in %)
    out["soil"] = {
        "dry":  trap(soil, 0, 15, 30, 45),
        "moist":tri(soil, 35, 55, 75),
        "wet":  trap(soil, 70, 80, 100, 110),
    }

    # Pioggia (mm / 24h)
    out["rain"] = {
        "low":    trap(rain, -1, 0, 1.5, 2.5),
        "medium": tri(rain, 2.0, 3.5, 5.0),
        "high":   trap(rain, 4.0, 6.0, 10.0, 20.0),
    }

    # Rapporto giorni/intervallo
    out["ratio"] = {
        "early":   trap(ratio, -0.1, 0.0, 0.6, 0.8),
        "due":     tri(ratio, 0.8, 1.0, 1.2),
        "overdue": trap(ratio, 1.0, 1.3, 2.0, 3.0),
    }

    # Temperatura (°C)
    out["temp"] = {
        "low":      trap(temp, -5, 0, 10, 15),
        "moderate": tri(temp, 15, 22, 28),
        "high":     trap(temp, 26, 30, 36, 42),
    }

    # ET0 (mm/day) se presente
    if isinstance(et0, (int, float)):
        out["et0"] = {
            "low":      trap(et0, -0.1, 0.0, 1.5, 2.0),
            "moderate": tri(et0, 1.5, 3.0, 4.5),
            "high":     trap(et0, 4.0, 5.0, 7.0, 9.0),
        }
    else:
        out["et0"] = {}

    # clamp
    for grp in out.values():
        for k, v in list(grp.items()):
            grp[k] = clamp01(v)

    return out

# Rule base
def evaluate_rules(deg: Dict[str, Dict[str, float]]) -> list:
    """
    Ritorna lista di regole attivate: [{id, action, weight, because}, ...]
    action ∈ {"irrigate_today","irrigate_tomorrow","skip"}
    """
    soil = deg.get("soil", {})
    rain = deg.get("rain", {})
    ratio = deg.get("ratio", {})
    temp = deg.get("temp", {})
    et0  = deg.get("et0", {})

    rules = []

    # R1: rain high OR soil wet -> skip
    r1 = max(rain.get("high", 0), soil.get("wet", 0))
    if r1 > 0:
        rules.append({
            "id": "R1",
            "action": "skip",
            "weight": r1,
            "because": "Pioggia alta o suolo già bagnato"
        })

    # R2: rain medium AND soil moist -> irrigate_tomorrow
    r2 = min(rain.get("medium", 0), soil.get("moist", 0))
    if r2 > 0:
        rules.append({
            "id": "R2",
            "action": "irrigate_tomorrow",
            "weight": r2,
            "because": "Pioggia media e suolo umido → meglio rimandare"
        })

    # R3: overdue AND rain low AND (soil NOT wet) -> irrigate_today
    not_wet = 1.0 - soil.get("wet", 0)
    r3 = min(ratio.get("overdue", 0), rain.get("low", 0), not_wet)
    if r3 > 0:
        rules.append({
            "id": "R3",
            "action": "irrigate_today",
            "weight": r3,
            "because": "Intervallo superato, poca pioggia e suolo non bagnato"
        })

    # R4: due AND rain low AND (soil NOT wet) -> irrigate_tomorrow
    r4 = min(ratio.get("due", 0), rain.get("low", 0), not_wet)
    if r4 > 0:
        rules.append({
            "id": "R4",
            "action": "irrigate_tomorrow",
            "weight": r4,
            "because": "Intervallo in arrivo, poca pioggia e suolo non bagnato"
        })

    # R5: temp high AND soil dry -> irrigate_today
    r5 = min(temp.get("high", 0), soil.get("dry", 0))
    if r5 > 0:
        rules.append({
            "id": "R5",
            "action": "irrigate_today",
            "weight": r5,
            "because": "Fa caldo e il suolo è secco"
        })

    # R6 (opzionale): et0 high AND soil dry -> irrigate_today
    if et0:
        r6 = min(et0.get("high", 0), soil.get("dry", 0))
        if r6 > 0:
            rules.append({
                "id": "R6",
                "action": "irrigate_today",
                "weight": r6,
                "because": "Evapotraspirazione elevata e suolo secco"
            })

    # Se nessuna regola ha dato peso, default: skip (peso minimo)
    if not rules:
        rules.append({
            "id": "R0",
            "action": "skip",
            "weight": 0.2,
            "because": "Nessuna condizione critica"
        })

    # ordina per peso desc
    rules.sort(key=lambda r: r["weight"], reverse=True)
    return rules

def aggregate_scores(rules: list) -> Dict[str, float]:
    scores = {"irrigate_today": 0.0, "irrigate_tomorrow": 0.0, "skip": 0.0}
    for r in rules:
        a = r["action"]
        scores[a] = max(scores[a], r["weight"])  # max-aggregation
    return scores

def choose_action(scores: Dict[str, float]) -> (str, float):
    pairs = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_action, best_w = pairs[0]
    second_w = pairs[1][1] if len(pairs) > 1 else 0.0
    denom = best_w + second_w + 1e-9
    confidence = best_w / denom if denom > 0 else best_w
    return best_action, float(round(confidence, 3))

def build_reason(rules: list, action: str) -> str:
    """Prendi la prima regola a favore dell'azione selezionata, usa sua 'because'."""
    for r in rules:
        if r["action"] == action:
            return r["because"]
    return "Regole neutre → nessun intervento urgente"

# API principale
def compute(*, plant: Dict[str, Any], weather: Optional[Dict[str, Any]], now: datetime) -> Dict[str, Any]:
    """
    Ritorna recommendation + explain-tech (fuzzy).
    """
    # segnali base
    baseline = plant.get("wateringIntervalDays")
    if not isinstance(baseline, int):
        baseline = baseline_from_stage(plant.get("stage"))

    last = plant.get("lastWateredAt")
    days = _days_since_last(last, now) if isinstance(last, datetime) else None

    soil = _extract_soil_moisture(weather)  # % (può essere None)
    rain = weather.get("rainNext24h") if weather else None
    temp = weather.get("temp") if weather else None
    et0  = weather.get("et0") if weather else None
    hum  = weather.get("humidity") if weather else None

    # ratio giorni/intervallo
    ratio = None
    if isinstance(days, int) and baseline and baseline > 0:
        ratio = days / float(baseline)

    # Fuzzy pipeline
    signals = {
        "daysSinceLast": days,
        "baselineInterval": baseline,
        "ratio": ratio,
        "soilMoisture": soil,
        "rainNext24h": rain,
        "temp": temp,
        "humidity": hum,
        "et0": et0,
    }

    deg = fuzzify_inputs(signals)
    rules = evaluate_rules(deg)
    scores = aggregate_scores(rules)
    action, conf = choose_action(scores)
    reason = build_reason(rules, action)

    # nextDate (indicativa)
    if action == "irrigate_today":
        next_date = now
    elif action == "irrigate_tomorrow":
        next_date = now + timedelta(days=1)
    else:
        # skip: suggerisci controllo in baseline/2 giorni
        step = max(1, baseline // 2)
        next_date = now + timedelta(days=step)

    result = {
        "recommendation": action,
        "reason": reason,
        "nextDate": next_date.isoformat(),
        "confidence": conf,
        "signals": {
            "daysSinceLast": days,
            "baselineInterval": baseline,
            "rainNext24h": rain,
            "temp": temp,
            "humidity": hum,
            "soilMoisture": soil,
            "et0": et0,
        },
        "tech": {  # Dettagli tecnici per il modal
            "memberships": deg,      # {soil:{dry:..}, rain:{..}, ratio:{..}, temp:{..}, et0:{..}}
            "rules": rules,          # [{id, action, weight, because}]
            "actionScores": scores,  # {"irrigate_today":w,..}
        }
    }
    return result