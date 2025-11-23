from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SensorDataInput(BaseModel):
    soil_moisture: Optional[float] = Field(None, ge=0, le=100)
    temperature: Optional[float] = Field(None, ge=-50, le=60)
    humidity: Optional[float] = Field(None, ge=0, le=100)
    light: Optional[float] = Field(None, ge=0)
    rainfall: Optional[float] = Field(0, ge=0)
    
    class Config:
        # Pydantic V2 config
        json_schema_extra = {
            "example": {
                "soil_moisture": 45.0,
                "temperature": 24.5,
                "humidity": 62.0,
                "light": 15000.0,
                "rainfall": 0.0
            }
        }

class IrrigationSuggestion(BaseModel):
    """Output: suggerimento irrigazione + concimazione"""
    should_water: bool
    water_amount_liters: float
    decision: str
    description: str
    timing: str
    priority: str
    
    # 🟢 CAMPI FONDAMENTALI PER VISUALIZZARE I NUOVI DATI
    frequency_estimation: Optional[Dict[str, str]] = Field(None, description="Stima frequenza")
    fertilizer_estimation: Optional[Dict[str, str]] = Field(None, description="Stima concimazione")

class PipelineDetailsResponse(BaseModel):
    """
    Dettagli completi.
    Usiamo Dict[str, Any] per 'features' così accetta 
    qualsiasi nuovo indice (VPD, AWC, Soil Behavior) senza filtrarlo.
    """
    cleaned_data: Optional[Dict[str, Any]] = None
    
    # 🟢 IMPORTANTE: Lasciare questo come Dict generico permette di passare 
    # soil_behavior, vpd, awc_percentage senza doverli dichiarare uno per uno.
    features: Optional[Dict[str, Any]] = None 
    
    estimation: Optional[Dict[str, Any]] = None
    anomalies: List[Dict[str, Any]] = []
    full_suggestions: Optional[Dict[str, Any]] = None

class PipelineMetadataResponse(BaseModel):
    started_at: str
    completed_at: Optional[str] = None
    errors: List[str] = []
    warnings: List[str] = []
    stage_results: Dict[str, Dict[str, Any]] = {}

class PipelineResponse(BaseModel):
    status: str
    suggestion: Optional[IrrigationSuggestion] = None
    details: Optional[PipelineDetailsResponse] = None
    metadata: Optional[PipelineMetadataResponse] = None

class PipelineRequest(BaseModel):
    sensor_data: SensorDataInput
    plant_type: Optional[str] = "generic"
    soil_type: Optional[str] = None # Usato per i test, opzionale

class HealthCheckResponse(BaseModel):
    status: str
    pipeline_available: bool
    supported_plants: List[str]
    timestamp: str