from datetime import datetime
from fastapi import HTTPException

from utils.ai_inputs_aggregator import get_inputs as aggregate_inputs
from utils.ai_irrigation_service import compute as compute_irrigation
from utils.weather_service import get_weather  # fallback leggero
from utils.ai_explainer_service import explain_irrigation  # LLM spiegazione


def compute_for_plant(plant: dict):
    """
    Restituisce il consiglio AI di irrigazione per una singola pianta.
    Pipeline:
      1) Aggregatore (NASA/OM/Copernicus) → 'agg'
      2) Motore fuzzy (FAO-like) → 'decision'
      3) Spiegazione LLM (non bloccante) → 'explanationLLM'
    Esporta SEMPRE i campi meteo attesi dalla Card (temp, humidity, rainNext24h, soil*).
    Aggiunge inoltre:
      - tech (fuzzy memberships, regole, punteggi)
      - meta.weather con campi avanzati (et0, radiazione, vento, precipDaily)
      - _debug per retro-compatibilità
      - generatedAt timestamp ISO
    """
    if not plant:
        raise HTTPException(status_code=404, detail="Pianta non trovata")

    now = datetime.utcnow()

    # 1) Aggrega input (profilo FAO, meteo, ecc.)
    agg = aggregate_inputs(plant, now=now) or {}

    # 2) Normalizza 'weather' (garantiamo i campi attesi dalla Card)
    wx = agg.get("weather") or {}
    # Se per qualche motivo non abbiamo nulla, prova fallback Open-Meteo
    if not wx and plant.get("geoLat") is not None and plant.get("geoLng") is not None:
        fallback = get_weather(plant["geoLat"], plant["geoLng"]) or {}
        wx = {**wx, **fallback}

    # Chiavi base per la Card (non toccare: la UI si aspetta questi)
    card_weather = {
        "temp": wx.get("temp"),
        "humidity": wx.get("humidity"),
        "rainNext24h": wx.get("rainNext24h"),
        "soilMoistureApprox": wx.get("soilMoistureApprox"),
        "soilMoisture0to7cm": wx.get("soilMoisture0to7cm"),
    }
    # meta.weather = full (anche et0/vento/radiazione/precipDaily)
    meta_weather = {**wx, **card_weather}

    # 3) Decisione fuzzy (usa wx normalizzato)
    decision = compute_irrigation(plant=plant, weather=wx, now=now) or {}

    # 4) Spiegazione LLM (non blocca: se fallisce → fallback interno)
    try:
        llm = explain_irrigation(plant=plant, agg=agg, decision=decision, now=now) or {}
    except Exception:
        llm = {"text": None, "usedLLM": False, "model": None, "tokens": None}

    # 5) Risposta per il frontend
    result = {
        "recommendation": decision.get("recommendation"),
        "reason": decision.get("reason"),
        "nextDate": decision.get("nextDate"),
        "confidence": decision.get("confidence"),

        # segnali esposti (inclusi quelli usati dalla Card)
        "signals": {
            "daysSinceLast": (decision.get("signals") or {}).get("daysSinceLast"),
            "baselineInterval": (decision.get("signals") or {}).get("baselineInterval"),
            "rainNext24h": card_weather["rainNext24h"],
            "temp": card_weather["temp"],
            "humidity": card_weather["humidity"],
            # soil usato dal fuzzy (converge da 0-7cm o approx dentro ai_utils)
            "soilMoisture": (decision.get("signals") or {}).get("soilMoisture"),
            "soilMoistureApprox": card_weather["soilMoistureApprox"],
            "soilMoisture0to7cm": card_weather["soilMoisture0to7cm"],
            "et0": (agg.get("weather") or {}).get("et0"),
            "hadGeo": bool(plant.get("geoLat") and plant.get("geoLng")),
        },

        # meteo per la Card (sintetico)
        "weather": card_weather,

        # meta per il Drawer (completo)
        "meta": {
            "weather": meta_weather,     # include et0 / vento / radiazione / precipDaily (se presenti)
            "profile": agg.get("profile"),
            "sources": agg.get("raw"),   # raw: nasa/openmeteo/soil
            "geo": {
                "lat": plant.get("geoLat"),
                "lng": plant.get("geoLng"),
            },
            "fuzzy": decision.get("tech"),  # memberships / regole / scores
        },

        #  spiegazione generativa pronta da mostrare nel Drawer
        "explanationLLM": llm.get("text"),
        "explanationMeta": {
            "usedLLM": llm.get("usedLLM"),
            "model": llm.get("model"),
            "tokens": llm.get("tokens"),
            "error": llm.get("error"),
        },

        # comodo: esportiamo anche 'tech' top-level (mirror di meta.fuzzy)
        "tech": decision.get("tech"),

        # compatibilità per vecchie Card che leggevano _debug.weather
        "_debug": {
            "weather": meta_weather,
            "profile": agg.get("profile"),
            "sources": agg.get("raw"),
            "geo": {
                "lat": plant.get("geoLat"),
                "lng": plant.get("geoLng"),
            },
        },

        # timestamp generazione risposta lato backend
        "generatedAt": now.isoformat() + "Z",
    }

    return result

def compute_batch(plants: list):
    """
    Calcola il consiglio AI per una lista di piante.
    Mantiene compatibilità con routers/plantsRouter.py che importa compute_batch.
    Ritorna una lista di record: [{ id, ...risultato } | { id, error }]
    """
    results = []
    for p in (plants or []):
        # prova ad estrarre un id leggibile (sia _id Mongo che id string)
        pid = str(p.get("_id") or p.get("id") or "")
        try:
            res = compute_for_plant(p)
            # includi l'id in cima per comodità del frontend
            results.append({ "id": pid, **res })
        except Exception as e:
            results.append({
                "id": pid,
                "error": str(e)
            })
    return results