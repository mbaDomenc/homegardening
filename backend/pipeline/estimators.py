"""
Step 3: Estimator / Rule Engine (Strategy Pattern)
Applica regole per stimare fabbisogno idrico e generare raccomandazioni.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum
from .base import ProcessorBase, PipelineContext, PipelineStage


class PlantType(str, Enum):
    """Tipi di pianta supportati"""
    TOMATO = "tomato"
    LETTUCE = "lettuce"
    BASIL = "basil"
    PEPPER = "pepper"
    CUCUMBER = "cucumber"
    GENERIC = "generic"


class IrrigationDecision(str, Enum):
    """Decisione sull'irrigazione"""
    DO_NOT_WATER = "do_not_water"
    WATER_LIGHT = "water_light"
    WATER_MODERATE = "water_moderate"
    WATER_HEAVY = "water_heavy"


class IrrigationStrategy(ABC):
    """
    Strategy Pattern: strategia di irrigazione specifica per tipo di pianta.
    """
    
    @abstractmethod
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stima fabbisogno idrico per questa pianta.
        
        Returns:
            {
                "should_water": bool,
                "decision": IrrigationDecision,
                "water_amount_ml": float,
                "confidence": float (0-1),
                "reasoning": str
            }
        """
        pass


class TomatoStrategy(IrrigationStrategy):
    """Strategia per pomodori"""
    
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        soil_moisture = cleaned_data.get("soil_moisture", 50)
        stress_index = features.get("water_stress_index", 50)
        urgency = features.get("irrigation_urgency", 5)
        
        # Pomodori: preferiscono suolo costantemente umido (60-80%)
        if soil_moisture < 50:
            decision = IrrigationDecision.WATER_HEAVY
            water_amount = 2000  # ml
            reasoning = "Suolo troppo secco per pomodori. Irrigazione abbondante necessaria."
        elif soil_moisture < 60:
            decision = IrrigationDecision.WATER_MODERATE
            water_amount = 1500
            reasoning = "Suolo sotto ottimale per pomodori. Irrigazione moderata."
        elif soil_moisture < 70:
            decision = IrrigationDecision.WATER_LIGHT
            water_amount = 1000
            reasoning = "Suolo leggermente secco. Irrigazione leggera."
        else:
            decision = IrrigationDecision.DO_NOT_WATER
            water_amount = 0
            reasoning = "Suolo sufficientemente umido. Non irrigare."
            
        return {
            "should_water": decision != IrrigationDecision.DO_NOT_WATER,
            "decision": decision.value,
            "water_amount_ml": water_amount,
            "confidence": 0.85,
            "reasoning": reasoning,
            "plant_type": PlantType.TOMATO.value
        }


class LettuceStrategy(IrrigationStrategy):
    """Strategia per lattuga"""
    
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        soil_moisture = cleaned_data.get("soil_moisture", 50)
        
        # Lattuga: richiede suolo sempre umido (70-85%)
        if soil_moisture < 60:
            decision = IrrigationDecision.WATER_HEAVY
            water_amount = 1800
            reasoning = "Lattuga necessita suolo molto umido. Irrigare abbondantemente."
        elif soil_moisture < 70:
            decision = IrrigationDecision.WATER_MODERATE
            water_amount = 1200
            reasoning = "Suolo sotto ottimale per lattuga."
        elif soil_moisture < 80:
            decision = IrrigationDecision.WATER_LIGHT
            water_amount = 800
            reasoning = "Mantenimento umidità per lattuga."
        else:
            decision = IrrigationDecision.DO_NOT_WATER
            water_amount = 0
            reasoning = "Suolo ottimale per lattuga."
            
        return {
            "should_water": decision != IrrigationDecision.DO_NOT_WATER,
            "decision": decision.value,
            "water_amount_ml": water_amount,
            "confidence": 0.80,
            "reasoning": reasoning,
            "plant_type": PlantType.LETTUCE.value
        }


class BasilStrategy(IrrigationStrategy):
    """Strategia per basilico"""
    
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        soil_moisture = cleaned_data.get("soil_moisture", 50)
        
        # Basilico: suolo moderatamente umido (55-70%)
        if soil_moisture < 45:
            decision = IrrigationDecision.WATER_HEAVY
            water_amount = 1500
            reasoning = "Basilico richiede irrigazione frequente."
        elif soil_moisture < 55:
            decision = IrrigationDecision.WATER_MODERATE
            water_amount = 1000
            reasoning = "Suolo sotto ottimale per basilico."
        elif soil_moisture < 65:
            decision = IrrigationDecision.WATER_LIGHT
            water_amount = 700
            reasoning = "Leggera irrigazione per basilico."
        else:
            decision = IrrigationDecision.DO_NOT_WATER
            water_amount = 0
            reasoning = "Suolo adeguato per basilico."
            
        return {
            "should_water": decision != IrrigationDecision.DO_NOT_WATER,
            "decision": decision.value,
            "water_amount_ml": water_amount,
            "confidence": 0.78,
            "reasoning": reasoning,
            "plant_type": PlantType.BASIL.value
        }


class GenericStrategy(IrrigationStrategy):
    """Strategia generica per piante non specificate"""
    
    def estimate(self, cleaned_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        soil_moisture = cleaned_data.get("soil_moisture", 50)
        stress_index = features.get("water_stress_index", 50)
        urgency = features.get("irrigation_urgency", 5)
        
        # Logica generica basata su stress e urgenza
        if urgency >= 8 or stress_index >= 70:
            decision = IrrigationDecision.WATER_HEAVY
            water_amount = 2000
            reasoning = "Alto stress idrico rilevato."
        elif urgency >= 5 or stress_index >= 50:
            decision = IrrigationDecision.WATER_MODERATE
            water_amount = 1500
            reasoning = "Stress idrico moderato."
        elif urgency >= 3 or stress_index >= 30:
            decision = IrrigationDecision.WATER_LIGHT
            water_amount = 1000
            reasoning = "Leggero stress idrico."
        else:
            decision = IrrigationDecision.DO_NOT_WATER
            water_amount = 0
            reasoning = "Condizioni idriche adeguate."
            
        return {
            "should_water": decision != IrrigationDecision.DO_NOT_WATER,
            "decision": decision.value,
            "water_amount_ml": water_amount,
            "confidence": 0.70,
            "reasoning": reasoning,
            "plant_type": PlantType.GENERIC.value
        }


class IrrigationEstimator(ProcessorBase):
    """
    Rule Engine che applica strategie di irrigazione.
    Usa Strategy Pattern per diverse piante.
    """
    
    def __init__(self, plant_type: Optional[str] = None):
        super().__init__("Irrigation Estimator")
        
        # Registro delle strategie disponibili
        self.strategies = {
            PlantType.TOMATO: TomatoStrategy(),
            PlantType.LETTUCE: LettuceStrategy(),
            PlantType.BASIL: BasilStrategy(),
            PlantType.PEPPER: GenericStrategy(),
            PlantType.CUCUMBER: GenericStrategy(),
            PlantType.GENERIC: GenericStrategy()
        }
        
        # Imposta tipo pianta (default: generic)
        self.plant_type = plant_type or PlantType.GENERIC.value
        
    def _get_stage(self) -> PipelineStage:
        return PipelineStage.ESTIMATION
        
    def _execute(self, context: PipelineContext) -> Dict[str, Any]:
        """Applica strategia di irrigazione"""
        
        if not context.cleaned_data:
            raise ValueError("Dati puliti non disponibili.")
        
        if not context.features:
            raise ValueError("Features non disponibili.")
        
        # Seleziona strategia appropriata
        plant_type_enum = PlantType(self.plant_type) if self.plant_type in [pt.value for pt in PlantType] else PlantType.GENERIC
        strategy = self.strategies[plant_type_enum]
        
        # Applica strategia
        estimation = strategy.estimate(context.cleaned_data, context.features)
        
        # Salva nel contesto
        context.estimation = estimation
        
        return {
            "estimation": estimation,
            "strategy_used": plant_type_enum.value
        }
