"""
Pipeline Manager: Orchestratore della pipeline di processing.
"""

from typing import Dict, Any, Optional
from .base import PipelineContext
from .validators import DataValidator
from .feature_engineering import FeatureEngineer
from .estimators import IrrigationEstimator
from .anomaly_detector import AnomalyDetector
from .action_generator import ActionGenerator


class PipelineManager:
    """
    Gestisce l'intera pipeline di processing.
    Implementa Chain of Responsibility collegando tutti i processori.
    """
    
    def __init__(self, plant_type: Optional[str] = None):
        """
        Inizializza la pipeline.
        
        Args:
            plant_type: Tipo di pianta (tomato, lettuce, basil, etc.)
        """
        self.plant_type = plant_type
        
        # Crea i processori
        self.validator = DataValidator()
        self.feature_engineer = FeatureEngineer()
        self.estimator = IrrigationEstimator(plant_type)
        self.anomaly_detector = AnomalyDetector()
        self.action_generator = ActionGenerator()
        
        # Collega la catena (Chain of Responsibility)
        self.validator.set_next(self.feature_engineer) \
                      .set_next(self.estimator) \
                      .set_next(self.anomaly_detector) \
                      .set_next(self.action_generator)
        
        print(f"✅ Pipeline inizializzata per pianta: {plant_type or 'generic'}")
        
    def process(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa dati sensori attraverso l'intera pipeline.
        
        Args:
            sensor_data: Dati grezzi dai sensori
            
        Returns:
            Risultato completo della pipeline con suggerimenti
        """
        print(f"\n{'='*60}")
        print("🚀 Avvio Pipeline di Processing")
        print(f"{'='*60}")
        
        # Crea contesto
        context = PipelineContext(sensor_data)
        
        # Esegui pipeline
        try:
            context = self.validator.process(context)
            context.complete()
            
            print(f"\n{'='*60}")
            print("✅ Pipeline Completata")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"❌ Pipeline Fallita: {str(e)}")
            print(f"{'='*60}\n")
            context.add_error("Pipeline", str(e))
            context.complete()
        
        # Ritorna risultato
        return self._format_output(context)
        
    def _format_output(self, context: PipelineContext) -> Dict[str, Any]:
        """Formatta output della pipeline"""
        
        # Estrai suggerimento principale
        main_suggestion = None
        if context.suggestions:
            main_suggestion = {
                "should_water": context.suggestions["main_action"]["action"] == "irrigate",
                "water_amount_liters": context.suggestions["main_action"]["water_amount_liters"],
                "decision": context.suggestions["main_action"]["decision"],
                "description": context.suggestions["main_action"]["description"],
                "timing": context.suggestions["timing"]["suggested_time"],
                "priority": context.suggestions["priority"]
            }
        
        return {
            "status": "success" if not context.errors else "error",
            "suggestion": main_suggestion,
            "details": {
                "cleaned_data": context.cleaned_data,
                "features": context.features,
                "estimation": context.estimation,
                "anomalies": context.anomalies,
                "full_suggestions": context.suggestions
            },
            "metadata": {
                "started_at": context.started_at.isoformat(),
                "completed_at": context.completed_at.isoformat() if context.completed_at else None,
                "errors": context.errors,
                "warnings": context.warnings,
                "stage_results": context.stage_results
            }
        }
