"""
Step 2: Feature Engineering
Crea feature derivate dai dati puliti per migliorare le stime.
"""

from typing import Dict, Any
from datetime import datetime, time
from .base import ProcessorBase, PipelineContext, PipelineStage


class FeatureEngineer(ProcessorBase):
    """
    Feature Engineer: crea feature derivate dai dati sensori.
    
    Feature create:
    - Indice di stress idrico (combinazione umidità suolo + temperatura + umidità aria)
    - Evapotraspirazione stimata
    - Fase del giorno (mattina/pomeriggio/sera/notte)
    - Stagione
    - Indice climatico
    """
    
    def __init__(self):
        super().__init__("Feature Engineer")
        
    def _get_stage(self) -> PipelineStage:
        return PipelineStage.FEATURE_ENGINEERING
        
    def _execute(self, context: PipelineContext) -> Dict[str, Any]:
        """Crea feature derivate"""
        
        if not context.cleaned_data:
            raise ValueError("Dati puliti non disponibili. Esegui prima DataValidator.")
        
        data = context.cleaned_data
        features = {}
        
        # 1. Indice di stress idrico (0-100, più alto = più stress)
        features["water_stress_index"] = self._calculate_water_stress(
            data.get("soil_moisture", 50),
            data.get("temperature", 20),
            data.get("humidity", 60)
        )
        
        # 2. Evapotraspirazione stimata (mm/giorno)
        features["evapotranspiration"] = self._estimate_evapotranspiration(
            data.get("temperature", 20),
            data.get("humidity", 60),
            data.get("light", 10000)
        )
        
        # 3. Fase del giorno
        features["day_phase"] = self._get_day_phase()
        
        # 4. Stagione
        features["season"] = self._get_season()
        
        # 5. Indice climatico (comfort per piante)
        features["climate_comfort_index"] = self._calculate_climate_comfort(
            data.get("temperature", 20),
            data.get("humidity", 60)
        )
        
        # 6. Deficit idrico stimato (mm)
        features["water_deficit"] = self._calculate_water_deficit(
            data.get("soil_moisture", 50),
            features["evapotranspiration"]
        )
        
        # 7. Urgenza irrigazione (0-10 scala)
        features["irrigation_urgency"] = self._calculate_irrigation_urgency(
            features["water_stress_index"],
            features["water_deficit"],
            data.get("rainfall", 0)
        )
        
        # Salva nel contesto
        context.features = features
        
        return {
            "features_created": len(features),
            "features": features
        }
        
    def _calculate_water_stress(self, soil_moisture: float, temperature: float, humidity: float) -> float:
        """
        Calcola indice di stress idrico (0-100).
        Più alto = più stress = più bisogno di acqua.
        """
        # Formula semplificata
        # Stress aumenta se:
        # - Umidità suolo bassa
        # - Temperatura alta
        # - Umidità aria bassa
        
        soil_stress = max(0, 100 - soil_moisture * 2)  # Inverte e scala
        temp_stress = max(0, (temperature - 15) * 3)    # Aumenta con temp
        humidity_stress = max(0, 100 - humidity)        # Aumenta se aria secca
        
        # Media ponderata
        stress = (soil_stress * 0.6 + temp_stress * 0.25 + humidity_stress * 0.15)
        return min(100, max(0, stress))
        
    def _estimate_evapotranspiration(self, temperature: float, humidity: float, light: float) -> float:
        """
        Stima evapotraspirazione in mm/giorno.
        Formula semplificata basata su temperatura, umidità e luce.
        """
        # Formula di Thornthwaite semplificata
        base_et = 0.0
        
        if temperature > 0:
            base_et = 16 * (10 * temperature / 365) ** 1.5
            
        # Correggi per umidità (più umidità = meno ET)
        humidity_factor = 1 - (humidity / 100) * 0.3
        
        # Correggi per luce (più luce = più ET)
        light_factor = 1 + (light / 100000) * 0.3
        
        et = base_et * humidity_factor * light_factor
        return round(max(0, min(15, et)), 2)  # Clamp 0-15 mm/giorno
        
    def _get_day_phase(self) -> str:
        """Ritorna fase del giorno basata sull'ora corrente"""
        now = datetime.now().time()
        
        if time(6, 0) <= now < time(12, 0):
            return "morning"
        elif time(12, 0) <= now < time(18, 0):
            return "afternoon"
        elif time(18, 0) <= now < time(22, 0):
            return "evening"
        else:
            return "night"
            
    def _get_season(self) -> str:
        """Ritorna stagione corrente (emisfero nord)"""
        month = datetime.now().month
        
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"
            
    def _calculate_climate_comfort(self, temperature: float, humidity: float) -> float:
        """
        Calcola indice di comfort climatico per le piante (0-100).
        100 = condizioni ottimali.
        """
        # Range ottimale: 18-24°C, 50-70% umidità
        temp_optimal = 21.0
        humidity_optimal = 60.0
        
        # Distanza dalla condizione ottimale
        temp_deviation = abs(temperature - temp_optimal) / 15  # Normalizza
        humidity_deviation = abs(humidity - humidity_optimal) / 40
        
        # Comfort index (più alto = meglio)
        comfort = 100 - (temp_deviation * 50 + humidity_deviation * 50)
        return max(0, min(100, comfort))
        
    def _calculate_water_deficit(self, soil_moisture: float, evapotranspiration: float) -> float:
        """
        Calcola deficit idrico in mm.
        Positivo = serve acqua, Negativo = troppa acqua.
        """
        # Umidità ottimale del suolo
        optimal_moisture = 60.0
        
        # Deficit basato su umidità
        moisture_deficit = (optimal_moisture - soil_moisture) / 10
        
        # Aggiungi ET
        total_deficit = moisture_deficit + evapotranspiration * 0.5
        
        return round(max(0, total_deficit), 2)
        
    def _calculate_irrigation_urgency(self, stress_index: float, deficit: float, rainfall: float) -> int:
        """
        Calcola urgenza irrigazione su scala 0-10.
        0 = non necessaria, 10 = urgente.
        """
        # Base da stress index
        urgency = stress_index / 10
        
        # Aumenta con deficit
        urgency += deficit * 0.5
        
        # Riduci se ha piovuto recentemente
        if rainfall > 0:
            urgency -= rainfall * 0.3
            
        return int(max(0, min(10, urgency)))
