"""
Router API per la pipeline di processing.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from models.pipelineModel import (
    PipelineRequest,
    PipelineResponse,
    HealthCheckResponse,
    SensorDataInput
)
from controllers.pipelineController import PipelineController


# Inizializza router
router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Inizializza controller
controller = PipelineController()


@router.post("/process", response_model=PipelineResponse, summary="Processa dati sensori")
async def process_sensor_data(request: PipelineRequest):
    """
    Processa dati sensori attraverso la pipeline completa.
    
    La pipeline esegue:
    1. **Data Validation**: Pulisce e valida i dati
    2. **Feature Engineering**: Calcola feature derivate
    3. **Estimation**: Applica regole di irrigazione
    4. **Anomaly Detection**: Rileva condizioni anomale
    5. **Action Generation**: Genera suggerimenti finali
    
    Args:
        request: Dati sensori e tipo pianta
        
    Returns:
        Suggerimento irrigazione con dettagli completi
    """
    return controller.process_sensor_data(request)


@router.post("/suggest", summary="Suggerimento rapido (alias)")
async def suggest_irrigation(sensor_data: SensorDataInput, plant_type: str = "generic"):
    """
    Endpoint semplificato per ottenere solo il suggerimento principale.
    
    Args:
        sensor_data: Dati dai sensori
        plant_type: Tipo di pianta (default: generic)
        
    Returns:
        Suggerimento irrigazione semplificato
    """
    request = PipelineRequest(sensor_data=sensor_data, plant_type=plant_type)
    result = controller.process_sensor_data(request)
    
    # Ritorna solo il suggerimento principale
    return {
        "status": result.status,
        "suggestion": result.suggestion
    }


@router.get("/health", response_model=HealthCheckResponse, summary="Health check")
async def health_check():
    """
    Verifica stato del servizio pipeline.
    
    Returns:
        Stato del servizio e piante supportate
    """
    return controller.get_health_check()


@router.get("/plants", summary="Lista piante supportate")
async def list_supported_plants():
    """
    Lista dei tipi di pianta supportati dalla pipeline.
    
    Returns:
        Lista di tipi pianta con descrizione
    """
    return {
        "plants": [
            {
                "id": "tomato",
                "name": "Pomodoro",
                "description": "Preferisce suolo costantemente umido (60-80%)",
                "optimal_moisture": "60-80%"
            },
            {
                "id": "lettuce",
                "name": "Lattuga",
                "description": "Richiede suolo molto umido (70-85%)",
                "optimal_moisture": "70-85%"
            },
            {
                "id": "basil",
                "name": "Basilico",
                "description": "Suolo moderatamente umido (55-70%)",
                "optimal_moisture": "55-70%"
            },
            {
                "id": "pepper",
                "name": "Peperone",
                "description": "Irrigazione regolare moderata",
                "optimal_moisture": "55-75%"
            },
            {
                "id": "cucumber",
                "name": "Cetriolo",
                "description": "Richiede umidità costante",
                "optimal_moisture": "65-80%"
            },
            {
                "id": "generic",
                "name": "Generica",
                "description": "Strategia generica per piante non specificate",
                "optimal_moisture": "50-70%"
            }
        ]
    }
