from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum
from .base import ProcessorBase, PipelineContext, PipelineStage

class PlantType(str, Enum):
    TOMATO = "tomato"; POTATO = "potato"; PEACH = "peach"; GRAPE = "grape"; PEPPER = "pepper"; GENERIC = "generic"

class IrrigationDecision(str, Enum):
    DO_NOT_WATER = "do_not_water"
    WATER_INTEGRATION = "water_integration"
    WATER_STANDARD = "water_standard"
    WATER_HEAVY = "water_heavy"
    WATER_LIGHT = "water_light" 
    WATER_MODERATE = "water_moderate" 

class IrrigationStrategy(ABC):
    @abstractmethod
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]: pass
    
    # LOGICA PURA: FABBISOGNO CICLO - VERSATO CICLO
    def _calculate_budget(self, cycle_need_liters, added_cycle_liters):
        missing = cycle_need_liters - added_cycle_liters
        
        if missing <= 0.2: # Tolleranza 200ml
            return 0.0, IrrigationDecision.DO_NOT_WATER
        
        # Se manca acqua, decide quanto
        if missing < 1.0: decision = IrrigationDecision.WATER_INTEGRATION
        else: decision = IrrigationDecision.WATER_STANDARD
            
        return round(missing, 1), decision


#STRATEGIE PER LE DIVERSE PIANTE PRESENTI
class TomatoStrategy(IrrigationStrategy):
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        added = cleaned_data.get("water_added_24h", 0.0) 
        # Target per ciclo (es. 4 Litri ogni 3 giorni)
        TARGET = 4.0 
        amt, dec = self._calculate_budget(TARGET, added)
        return {"should_water": dec != IrrigationDecision.DO_NOT_WATER, "decision": dec.value, "water_amount_ml": amt * 1000, "confidence": 0.95, "reasoning": f"Target Ciclo: {TARGET}L. Versati: {added}L.", "plant_type": "tomato"}

class PotatoStrategy(IrrigationStrategy):
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        added = cleaned_data.get("water_added_24h", 0.0)
        TARGET = 3.5
        amt, dec = self._calculate_budget(TARGET, added)
        return {"should_water": dec != IrrigationDecision.DO_NOT_WATER, "decision": dec.value, "water_amount_ml": amt * 1000, "confidence": 0.9, "reasoning": f"Target Ciclo: {TARGET}L. Versati: {added}L.", "plant_type": "potato"}

class PepperStrategy(IrrigationStrategy):
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        added = cleaned_data.get("water_added_24h", 0.0)
        TARGET = 3.0
        amt, dec = self._calculate_budget(TARGET, added)
        return {"should_water": dec != IrrigationDecision.DO_NOT_WATER, "decision": dec.value, "water_amount_ml": amt * 1000, "confidence": 0.85, "reasoning": f"Target Ciclo: {TARGET}L. Versati: {added}L.", "plant_type": "pepper"}

class PeachStrategy(IrrigationStrategy):
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        added = cleaned_data.get("water_added_24h", 0.0)
        TARGET = 10.0 
        amt, dec = self._calculate_budget(TARGET, added)
        return {"should_water": dec != IrrigationDecision.DO_NOT_WATER, "decision": dec.value, "water_amount_ml": amt * 1000, "confidence": 0.85, "reasoning": f"Target Ciclo: {TARGET}L.", "plant_type": "peach"}

class GrapeStrategy(IrrigationStrategy):
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        added = cleaned_data.get("water_added_24h", 0.0)
        TARGET = 5.0
        amt, dec = self._calculate_budget(TARGET, added)
        return {"should_water": dec != IrrigationDecision.DO_NOT_WATER, "decision": dec.value, "water_amount_ml": amt * 1000, "confidence": 0.9, "reasoning": f"Target Ciclo: {TARGET}L.", "plant_type": "grape"}

class GenericStrategy(IrrigationStrategy):
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        added = cleaned_data.get("water_added_24h", 0.0)
        TARGET = 2.5
        amt, dec = self._calculate_budget(TARGET, added)
        return {"should_water": dec != IrrigationDecision.DO_NOT_WATER, "decision": dec.value, "water_amount_ml": amt * 1000, "confidence": 0.5, "reasoning": f"Target Ciclo: {TARGET}L.", "plant_type": "generic"}

class IrrigationEstimator(ProcessorBase):
    def __init__(self, plant_type: Optional[str] = None):
        super().__init__("Irrigation Estimator")
        self.strategies = {
            PlantType.TOMATO: TomatoStrategy(), PlantType.POTATO: PotatoStrategy(),
            PlantType.PEACH: PeachStrategy(), PlantType.GRAPE: GrapeStrategy(),
            PlantType.PEPPER: PepperStrategy(), PlantType.GENERIC: GenericStrategy()
        }
        self.plant_type = plant_type or PlantType.GENERIC.value
        
    def _get_stage(self) -> PipelineStage: return PipelineStage.ESTIMATION
    
    def _execute(self, context: PipelineContext) -> Dict[str, Any]:
        if not context.cleaned_data: raise ValueError("Dati puliti non disponibili.")
        pt = PlantType(self.plant_type) if self.plant_type in [p.value for p in PlantType] else PlantType.GENERIC
        estimation = self.strategies[pt].estimate(context.cleaned_data, context.features or {})
        context.estimation = estimation
        return {"estimation": estimation}