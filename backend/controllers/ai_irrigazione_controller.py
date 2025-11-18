from datetime import datetime
from fastapi import HTTPException

# Importiamo i tuoi servizi esistenti per il recupero dati
from utils.ai_inputs_aggregator import get_inputs as aggregate_inputs
from controllers.sensor_controller import get_latest_readings
from utils.ai_explainer_service import explain_irrigation

# Importiamo la NUOVA Pipeline
from backend.services.pipeline import GardeningPipelineService

# Istanza Singleton del servizio pipeline
pipeline_service = GardeningPipelineService()

async def compute_for_plant(plant: dict):
    """
    Endpoint logico per calcolare il consiglio AI.
    1. Recupera dati esterni (NASA/Meteo) e interni (Sensori IoT).
    2. Esegue la Pipeline a 5 step.
    3. Genera spiegazione LLM e formatta la risposta.
    """
    if not plant:
        raise HTTPException(status_code=404, detail="Pianta non trovata")
    
    now = datetime.utcnow()

    # 1. DATI ESTERNI (Agregatore esistente)
    # Recupera meteo, profilo FAO, dati Copernicus
    agg = aggregate_inputs(plant, now=now) or {}

    # 2. DATI LOCALI (Sensori IoT)
    local_sensor_data = {}
    try:
        loc = plant.get("location")
        if loc:
            # get_latest_readings è ASYNC, usiamo await
            readings = await get_latest_readings(location=loc)
            
            # Cerchiamo specificamente il sensore di umidità del suolo
            # (Compatibile con la struttura che hai in sensor_simulator/controller)
            soil = readings.get("soil_moisture") or readings.get("moisture")
            if soil:
                local_sensor_data = {
                    "value": soil.get("value"),
                    "unit": soil.get("unit"),
                    "timestamp": soil.get("timestamp")
                }
    except Exception as e:
        print(f"[AI Controller] Warning lettura sensori: {e}")
        # Non blocchiamo: la pipeline gestirà l'assenza di sensori nel DataValidator

    # 3. ESECUZIONE PIPELINE
    # Passiamo tutto al motore che esegue Validator -> Features -> Strategy -> Anomaly -> Action
    ctx = pipeline_service.run(plant, agg, local_sensor_data)
    
    # Estraiamo i risultati finali dal contesto
    decision = ctx.estimation
    anomalies = ctx.anomalies
    suggestion = ctx.suggestion # "Annaffiare / Non annaffiare + quantità"
    
    # 4. SPIEGAZIONE LLM (Opzionale)
    # Usiamo il risultato della pipeline per alimentare l'explainer LLM esistente
    llm_result = {"text": None}
    try:
        # Passiamo la decisione calcolata dalla pipeline all'explainer
        # Nota: L'explainer si aspetta 'recommendation', che è presente in decision
        llm_result = explain_irrigation(plant=plant, agg=agg, decision=decision, now=now)
    except Exception:
        pass

    # 5. FORMATTAZIONE RISPOSTA (Compatibile col Frontend React)
    wx = agg.get("weather") or {}
    
    return {
        "plantId": str(plant.get("_id")),
        
        # Risultato Core Pipeline
        "recommendation": decision.get("recommendation"), # irrigate_today / irrigate_tomorrow / skip
        "reason": suggestion,                             # Messaggio generato dall'ActionGenerator Step
        "confidence": decision.get("confidence", 0.0),
        "nextDate": decision.get("nextDate"),
        
        # Dati e Segnali (Per la UI Card)
        "signals": {
            # Se c'è il sensore locale usa quello, altrimenti la stima
            "soilMoisture": local_sensor_data.get("value") or wx.get("soilMoistureApprox"),
            "rainNext24h": wx.get("rainNext24h"),
            "temp": wx.get("temp"),
            "humidity": wx.get("humidity"),
            # Nuovi campi generati dalla pipeline
            "anomalies": anomalies, 
            "features": ctx.features,
            "estimatedAmount": decision.get("estimated_amount_ml")
        },
        
        # Metadati Tecnici (Per il Drawer 'Dettagli AI')
        "meta": {
            "weather": wx,
            "profile": agg.get("profile"),
            "fuzzy": decision.get("tech"), # Dettagli membership fuzzy
            "pipeline_valid": ctx.is_valid
        },
        
        # Spiegazione Generativa
        "explanationLLM": llm_result.get("text"),
        "explanationMeta": {
             "usedLLM": llm_result.get("usedLLM"),
             "model": llm_result.get("model")
        },
        
        "generatedAt": now.isoformat() + "Z"
    }

async def compute_batch(plant_ids: list, current_user: dict):
    # Placeholder per implementazione futura batch
    return []
