"""
Controller per la pipeline di processing.
"""

import logging
from datetime import datetime
from fastapi import HTTPException
from pipeline.pipeline_manager import PipelineManager
from models.pipelineModel import (
    PipelineRequest, 
    PipelineResponse,
    IrrigationSuggestion,
    PipelineDetailsResponse,
    PipelineMetadataResponse,
    HealthCheckResponse
)


logger = logging.getLogger(__name__)


class PipelineController:
    """
    Controller per gestire le richieste alla pipeline.
    """
    
    SUPPORTED_PLANTS = ["tomato", "lettuce", "basil", "pepper", "cucumber", "generic"]
    
    def __init__(self):
        logger.info("✅ PipelineController inizializzato")
        
    def process_sensor_data(self, request: PipelineRequest) -> PipelineResponse:
        """
        Processa dati sensori attraverso la pipeline.
        
        Args:
            request: Richiesta con dati sensori e tipo pianta
            
        Returns:
            Risposta strutturata della pipeline
            
        Raises:
            HTTPException: Se plant_type non supportato o errore processing
        """
        try:
            # Valida plant_type
            if request.plant_type not in self.SUPPORTED_PLANTS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo pianta '{request.plant_type}' non supportato. "
                           f"Supportati: {', '.join(self.SUPPORTED_PLANTS)}"
                )
            
            logger.info(f"Inizio processing per pianta: {request.plant_type}")
            started_at = datetime.utcnow().isoformat()
            
            # Converti SensorDataInput a dict
            sensor_data = request.sensor_data.model_dump()
            
            # Crea pipeline manager per questo tipo di pianta
            pipeline = PipelineManager(plant_type=request.plant_type)
            
            # Esegui pipeline
            result = pipeline.process(sensor_data)
            
            logger.info(f"Processing completato con successo per {request.plant_type}")

            #RIGHE AGGIUNTE PER AVERE DEI SUGGERIMENTI 
            suggestions = result.get("details", {}).get("full_suggestions", {})
            main_action = suggestions.get("main_action", {})
            timing_info = suggestions.get("timing", {})
            
            # ✅ Struttura la risposta con PipelineResponse
            return PipelineResponse(
                status=result.get("status", "success"),
                suggestion=IrrigationSuggestion(
                    should_water=main_action.get("action") == "irrigate",
                    water_amount_liters=main_action.get("water_amount_liters", 0.0),
                    decision=main_action.get("decision", ""),
                    description=main_action.get("description", ""),
                    timing=timing_info.get("timing", ""),
                    priority=suggestions.get("priority", "medium")
                ),
                details=PipelineDetailsResponse(
                    cleaned_data=result.get("cleaned_data"),
                    features=result.get("features"),
                    estimation=result.get("estimation"),
                    anomalies=result.get("anomalies", []),
                    full_suggestions=result.get("details", {}).get("full_suggestions")
                ),
                metadata=PipelineMetadataResponse(
                    started_at=started_at,
                    completed_at=datetime.utcnow().isoformat(),
                    errors=result.get("errors", []),
                    warnings=result.get("warnings", []),
                    stage_results=result.get("stage_results", {})
                )
            )
            
        except HTTPException:
            # Ri-lancia HTTPException senza modifiche
            raise
        except ValueError as e:
            logger.warning(f"Dati non validi: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Dati sensori non validi: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Errore imprevisto durante processing: {str(e)}")
            # ✅ Ritorna errore strutturato con PipelineResponse
            return PipelineResponse(
                status="error",
                suggestion=None,
                details=None,
                metadata=PipelineMetadataResponse(
                    started_at=datetime.utcnow().isoformat(),
                    completed_at=datetime.utcnow().isoformat(),
                    errors=[str(e)],
                    warnings=[]
                )
            )
    
    def get_health_check(self) -> HealthCheckResponse:
        """Health check del sistema"""
        return HealthCheckResponse(
            status="healthy",
            pipeline_available=True,
            supported_plants=self.SUPPORTED_PLANTS,
            timestamp=datetime.utcnow().isoformat()
        )
