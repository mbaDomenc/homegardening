"""
Step 2: Feature Engineering
Crea feature derivate AVANZATE (VPD, AWC, Disease Risk).
"""

from typing import Dict, Any
from datetime import datetime, time
import math
from .base import ProcessorBase, PipelineContext, PipelineStage


class FeatureEngineer(ProcessorBase):
    
    def __init__(self):
        super().__init__("Feature Engineer")
        
    def _get_stage(self) -> PipelineStage:
        return PipelineStage.FEATURE_ENGINEERING
        
    def _execute(self, context: PipelineContext) -> Dict[str, Any]:
        if not context.cleaned_data:
            raise ValueError("Dati puliti non disponibili.")
        
        data = context.cleaned_data
        features = {}
        soil_type = data.get("soil", "universale")
        
        # --- 1. ANALISI SUOLO AVANZATA ---
        # Recupera proprietà idrologiche (Capacità di Campo, Punto Appassimento)
        soil_props = self._get_soil_properties(soil_type)
        features["soil_retention_factor"] = soil_props["retention_factor"]
        features["field_capacity"] = soil_props["field_capacity"] # Max acqua trattenuta
        features["wilting_point"] = soil_props["wilting_point"]   # Acqua inaccessibile (pianta muore)
        features["soil_behavior"] = soil_props["description"]
        
        # Calcola Acqua Disponibile (AWC - Available Water Content) attuale
        current_moisture = data.get("soil_moisture", 50)
        features["awc_percentage"] = self._calculate_awc(current_moisture, soil_props)

        # --- 2. METRICHE CLIMATICHE AVANZATE ---
        # VPD (Vapor Pressure Deficit)
        features["vpd"] = self._calculate_vpd(
            data.get("temperature", 20),
            data.get("humidity", 60)
        )
        
        # Rischio Malattie (Fungal Risk)
        features["disease_risk"] = self._calculate_disease_risk(
            data.get("temperature", 20),
            data.get("humidity", 60),
            features["vpd"]
        )

        # --- 3. METRICHE STANDARD ---
        features["water_stress_index"] = self._calculate_water_stress(
            current_moisture, data.get("temperature", 20), data.get("humidity", 60)
        )
        
        features["evapotranspiration"] = self._estimate_evapotranspiration(
            data.get("temperature", 20), data.get("humidity", 60), data.get("light", 10000)
        )
        
        features["day_phase"] = self._get_day_phase()
        features["season"] = self._get_season()
        
        features["climate_comfort_index"] = self._calculate_climate_comfort(
            data.get("temperature", 20), data.get("humidity", 60)
        )
        
        # Deficit (usando il fattore di ritenzione)
        features["water_deficit"] = self._calculate_water_deficit(
            current_moisture, features["evapotranspiration"], features["soil_retention_factor"]
        )
        
        # Urgenza
        features["irrigation_urgency"] = self._calculate_irrigation_urgency(
            features["water_stress_index"], features["water_deficit"], data.get("rainfall", 0)
        )
        
        context.features = features
        return {"features": features}

    # --- CALCOLI SULLA BASE SCIENTIFICA ---

    def _calculate_vpd(self, T, RH):
        """Calcola il Vapor Pressure Deficit in kPa."""
        # Pressione vapore saturo (es)
        es = 0.6108 * math.exp((17.27 * T) / (T + 237.3))
        # Pressione vapore attuale (ea)
        ea = es * (RH / 100.0)
        return round(es - ea, 2)

    def _calculate_disease_risk(self, T, RH, vpd):
        """Stima rischio malattie fungine (0-100)."""
        # Funghi amano: Alta umidità (>80%), Temp moderate (15-25), Basso VPD (<0.5)
        risk = 0
        if RH > 80: risk += 40
        elif RH > 70: risk += 20
        
        if 15 <= T <= 28: risk += 30 # Temperatura ottimali per funghi
        
        if vpd < 0.4: risk += 30 # Aria stagnante
        
        return min(100, risk)

    def _get_soil_properties(self, soil_type):
        """Restituisce parametri idrologici del terreno."""
        s = soil_type.lower()
        # FC = Field Capacity (%), WP = Wilting Point (%)
        if "sabbioso" in s:
            return {"retention_factor": 0.7, "field_capacity": 20, "wilting_point": 5, 
                    "description": "Sabbioso: Bassa ritenzione. L'acqua è subito disponibile ma si perde velocemente."}
        if "argilloso" in s:
            return {"retention_factor": 1.3, "field_capacity": 45, "wilting_point": 25, 
                    "description": "Argilloso: Alta ritenzione. Trattiene molta acqua, ma gran parte è 'incollata' al terreno e non disponibile."}
        if "torboso" in s:
            return {"retention_factor": 1.15, "field_capacity": 60, "wilting_point": 20, 
                    "description": "Torboso: Spugnoso. Ottima riserva idrica."}
        # Franco/Universale
        return {"retention_factor": 1.0, "field_capacity": 30, "wilting_point": 10, 
                "description": "Franco: Equilibrio ideale tra acqua disponibile e drenaggio."}

    def _calculate_awc(self, current_moisture, props):
        """
        Calcola % di acqua realmente disponibile per la pianta.
        0% = Punto Appassimento (Morte), 100% = Capacità di Campo (Ottimo).
        """
        fc = props["field_capacity"]
        wp = props["wilting_point"]
        
        if current_moisture <= wp: return 0.0
        if current_moisture >= fc: return 100.0
        
        # Normalizza nel range utile
        return round(((current_moisture - wp) / (fc - wp)) * 100, 1)

    # --- METODI STANDARD (INVARIATI) ---
    def _calculate_water_stress(self, soil_moisture, temperature, humidity):
        soil_stress = max(0, 100 - soil_moisture * 2)
        temp_stress = max(0, (temperature - 15) * 3)
        humidity_stress = max(0, 100 - humidity)
        stress = (soil_stress * 0.6 + temp_stress * 0.25 + humidity_stress * 0.15)
        return min(100, max(0, stress))
        
    def _estimate_evapotranspiration(self, temperature, humidity, light):
        base_et = 0.0
        if temperature > 0:
            base_et = 16 * (10 * temperature / 365) ** 1.5
        humidity_factor = 1 - (humidity / 100) * 0.3
        light_factor = 1 + (light / 100000) * 0.3
        et = base_et * humidity_factor * light_factor
        return round(max(0, min(15, et)), 2)
        
    def _calculate_water_deficit(self, soil_moisture, evapotranspiration, soil_factor):
        optimal = 60.0 
        moisture_deficit = (optimal - soil_moisture) / 10
        et_adjusted = evapotranspiration * (1.0 / soil_factor)
        return round(max(0, moisture_deficit + et_adjusted * 0.5), 2)
        
    def _get_day_phase(self):
        h = datetime.now().hour
        if 6 <= h < 12: return "morning"
        if 12 <= h < 18: return "afternoon"
        if 18 <= h < 22: return "evening"
        return "night"
            
    def _get_season(self):
        m = datetime.now().month
        if m in [12, 1, 2]: return "winter"
        if m in [3, 4, 5]: return "spring"
        if m in [6, 7, 8]: return "summer"
        return "autumn"
            
    def _calculate_climate_comfort(self, temperature, humidity):
        t_dev = abs(temperature - 21) / 15
        h_dev = abs(humidity - 60) / 40
        comfort = 100 - (t_dev * 50 + h_dev * 50)
        return max(0, min(100, comfort))
        
    def _calculate_irrigation_urgency(self, stress, deficit, rain):
        urgency = stress / 10 + deficit * 0.5
        if rain > 0: urgency -= rain * 0.3
        return int(max(0, min(10, urgency)))