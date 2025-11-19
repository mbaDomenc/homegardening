"""
Modelli Pydantic per la pipeline di processing.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SensorDataInput(BaseModel):
    """Input: dati dai sensori"""
    soil_moisture: Optional[float] = Field(None, description="Umidità suolo (%)", ge=0, le=100)
    temperature: Optional[float] = Field(None, description="Temperatura (°C)", ge=-50, le=60)
    humidity: Optional[float] = Field(None, description="Umidità aria (%)", ge=0, le=100)
    light: Optional[float] = Field(None, description="Luce (lux)", ge=0)
    rainfall: Optional[float] = Field(0, description="Pioggia recente (mm)", ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "soil_moisture": 45.0,
                "temperature": 24.5,
                "humidity": 62.0,
                "light": 15000.0,
                "rainfall": 0.0
            }
        }


class MainActionResponse(BaseModel):
    """Azione principale raccomandata"""
    action: str = Field(..., description="Azione (irrigate/do_not_irrigate)")
    decision: str = Field(..., description="Decisione dettagliata")
    water_amount_ml: float = Field(..., description="Quantità acqua in millilitri")
    water_amount_liters: float = Field(..., description="Quantità acqua in litri")
    reasoning: str = Field(..., description="Motivazione della decisione")
    confidence: float = Field(..., description="Confidenza stima (0-1)", ge=0, le=1)
    description: str = Field(..., description="Descrizione testuale")


class SecondaryActionResponse(BaseModel):
    """Azione secondaria"""
    type: str = Field(..., description="Tipo (urgent/preventive/monitoring)")
    action: str = Field(..., description="Descrizione azione")
    reason: str = Field(..., description="Motivazione")


class TimingResponse(BaseModel):
    """Timing suggerito per irrigazione"""
    suggested_time: str = Field(..., description="Quando irrigare")
    next_window: str = Field(..., description="Prossima finestra ideale (ISO)")
    current_phase: str = Field(..., description="Fase corrente del giorno")
    ideal_hours: List[str] = Field(..., description="Ore ideali per irrigazione")


class AnomalyResponse(BaseModel):
    """Anomalia rilevata"""
    type: str = Field(..., description="Tipo anomalia")
    severity: str = Field(..., description="Severità (info/warning/critical)")
    value: float = Field(..., description="Valore rilevato")
    threshold: float = Field(..., description="Soglia")
    message: str = Field(..., description="Messaggio descrittivo")
    recommendation: str = Field(..., description="Raccomandazione")


class FeatureResponse(BaseModel):
    """Feature calcolate"""
    water_stress_index: float = Field(..., description="Indice stress idrico (0-100)")
    evapotranspiration: float = Field(..., description="Evapotraspirazione (mm/giorno)")
    day_phase: str = Field(..., description="Fase giorno")
    season: str = Field(..., description="Stagione")
    climate_comfort_index: float = Field(..., description="Indice comfort climatico (0-100)")
    water_deficit: float = Field(..., description="Deficit idrico (mm)")
    irrigation_urgency: int = Field(..., description="Urgenza irrigazione (0-10)")


class SuggestionsResponse(BaseModel):
    """Suggerimenti completi"""
    main_action: MainActionResponse
    secondary_actions: List[SecondaryActionResponse]
    timing: TimingResponse
    notes: List[str]
    priority: str = Field(..., description="Priorità (low/medium/high/urgent)")
    generated_at: str = Field(..., description="Timestamp generazione")


class IrrigationSuggestion(BaseModel):
    """Output: suggerimento irrigazione semplificato"""
    should_water: bool = Field(..., description="Se irrigare o meno")
    water_amount_liters: float = Field(..., description="Quantità acqua (litri)")
    decision: str = Field(..., description="Tipo di irrigazione")
    description: str = Field(..., description="Descrizione testuale")
    timing: str = Field(..., description="Quando irrigare")
    priority: str = Field(..., description="Priorità (low/medium/high/urgent)")


class PipelineDetailsResponse(BaseModel):
    """Dettagli completi pipeline"""
    cleaned_data: Optional[Dict[str, Any]] = Field(None, description="Dati puliti")
    features: Optional[Dict[str, Any]] = Field(None, description="Feature calcolate")
    estimation: Optional[Dict[str, Any]] = Field(None, description="Stima irrigazione")
    anomalies: List[Dict[str, Any]] = Field(default_factory=list, description="Anomalie rilevate")
    full_suggestions: Optional[Dict[str, Any]] = Field(None, description="Suggerimenti completi")


class PipelineMetadataResponse(BaseModel):
    """Metadata esecuzione pipeline"""
    started_at: str = Field(..., description="Inizio esecuzione (ISO)")
    completed_at: Optional[str] = Field(None, description="Fine esecuzione (ISO)")
    errors: List[str] = Field(default_factory=list, description="Errori riscontrati")
    warnings: List[str] = Field(default_factory=list, description="Warning")
    stage_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Risultati per stage")


class PipelineResponse(BaseModel):
    """Response completa della pipeline"""
    status: str = Field(..., description="Status (success/error)")
    suggestion: Optional[IrrigationSuggestion] = Field(None, description="Suggerimento principale")
    details: Optional[PipelineDetailsResponse] = Field(None, description="Dettagli completi")
    metadata: Optional[PipelineMetadataResponse] = Field(None, description="Metadata esecuzione")


class PipelineRequest(BaseModel):
    """Request per eseguire la pipeline"""
    sensor_data: SensorDataInput = Field(..., description="Dati sensori")
    plant_type: Optional[str] = Field("generic", description="Tipo pianta (tomato, lettuce, basil, pepper, cucumber, generic)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sensor_data": {
                    "soil_moisture": 45.0,
                    "temperature": 24.5,
                    "humidity": 62.0,
                    "light": 15000.0,
                    "rainfall": 0.0
                },
                "plant_type": "tomato"
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Status del servizio")
    pipeline_available: bool = Field(..., description="Pipeline disponibile")
    supported_plants: List[str] = Field(..., description="Tipi di pianta supportati")
    timestamp: str = Field(..., description="Timestamp check")
