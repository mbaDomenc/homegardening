"""
Classi base per il pattern Chain of Responsibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class PipelineStage(str, Enum):
    """Stage della pipeline"""
    VALIDATION = "validation"
    FEATURE_ENGINEERING = "feature_engineering"
    ESTIMATION = "estimation"
    ANOMALY_DETECTION = "anomaly_detection"
    ACTION_GENERATION = "action_generation"


class PipelineStatus(str, Enum):
    """Stato della pipeline"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class PipelineContext:
    """
    Contesto condiviso tra tutti i processori della pipeline.
    Contiene dati, metadata e risultati intermedi.
    """
    
    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data
        self.cleaned_data: Optional[Dict[str, Any]] = None
        self.features: Optional[Dict[str, Any]] = None
        self.estimation: Optional[Dict[str, Any]] = None
        self.anomalies: List[Dict[str, Any]] = []
        self.suggestions: Optional[Dict[str, Any]] = None
        
        # Metadata
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stage_results: Dict[str, Dict[str, Any]] = {}
        
    def add_error(self, stage: str, message: str):
        """Aggiungi errore"""
        self.errors.append(f"[{stage}] {message}")
        
    def add_warning(self, stage: str, message: str):
        """Aggiungi warning"""
        self.warnings.append(f"[{stage}] {message}")
        
    def set_stage_result(self, stage: PipelineStage, status: PipelineStatus, data: Dict[str, Any]):
        """Salva risultato di uno stage"""
        self.stage_results[stage.value] = {
            "status": status.value,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def complete(self):
        """Marca la pipeline come completata"""
        self.completed_at = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """Serializza il contesto"""
        return {
            "raw_data": self.raw_data,
            "cleaned_data": self.cleaned_data,
            "features": self.features,
            "estimation": self.estimation,
            "anomalies": self.anomalies,
            "suggestions": self.suggestions,
            "metadata": {
                "started_at": self.started_at.isoformat(),
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "errors": self.errors,
                "warnings": self.warnings,
                "stage_results": self.stage_results
            }
        }


class ProcessorBase(ABC):
    """
    Classe base per tutti i processori della pipeline.
    Implementa pattern Chain of Responsibility.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._next_processor: Optional['ProcessorBase'] = None
        
    def set_next(self, processor: 'ProcessorBase') -> 'ProcessorBase':
        """Imposta il prossimo processore nella catena"""
        self._next_processor = processor
        return processor
        
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Processa il contesto e passa al prossimo se esiste.
        Template Method Pattern.
        """
        try:
            print(f"🔄 [{self.name}] Processando...")
            
            # Esegui la logica specifica del processore
            result = self._execute(context)
            
            # Salva risultato
            stage = self._get_stage()
            context.set_stage_result(
                stage,
                PipelineStatus.SUCCESS if not context.errors else PipelineStatus.WARNING,
                result
            )
            
            print(f"✅ [{self.name}] Completato")
            
        except Exception as e:
            print(f"❌ [{self.name}] Errore: {str(e)}")
            context.add_error(self.name, str(e))
            context.set_stage_result(
                self._get_stage(),
                PipelineStatus.ERROR,
                {"error": str(e)}
            )
            
        # Passa al prossimo processore
        if self._next_processor:
            return self._next_processor.process(context)
            
        return context
        
    @abstractmethod
    def _execute(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Logica specifica del processore.
        Da implementare nelle sottoclassi.
        """
        pass
        
    @abstractmethod
    def _get_stage(self) -> PipelineStage:
        """Ritorna lo stage della pipeline"""
        pass
