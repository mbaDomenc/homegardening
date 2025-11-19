"""
Step 4: Anomaly Detector
Rileva anomalie nei dati e nelle condizioni ambientali.
"""

from typing import Dict, Any, List
from .base import ProcessorBase, PipelineContext, PipelineStage


class AnomalyDetector(ProcessorBase):
    """
    Rilevatore di anomalie.
    Identifica valori e pattern sospetti che richiedono attenzione.
    """
    
    def __init__(self):
        super().__init__("Anomaly Detector")
        
        # Soglie critiche
        self.critical_thresholds = {
            "soil_moisture": {"min": 20, "max": 90},
            "temperature": {"min": 5, "max": 40},
            "humidity": {"min": 20, "max": 95},
            "water_stress_index": {"max": 80},
            "irrigation_urgency": {"max": 9}
        }
        
    def _get_stage(self) -> PipelineStage:
        return PipelineStage.ANOMALY_DETECTION
        
    def _execute(self, context: PipelineContext) -> Dict[str, Any]:
        """Rileva anomalie"""
        
        anomalies = []
        
        # Controlla dati puliti
        if context.cleaned_data:
            anomalies.extend(self._check_data_anomalies(context.cleaned_data))
        
        # Controlla features
        if context.features:
            anomalies.extend(self._check_feature_anomalies(context.features))
        
        # Controlla estimation
        if context.estimation:
            anomalies.extend(self._check_estimation_anomalies(context.estimation))
        
        # Salva anomalie nel contesto
        context.anomalies = anomalies
        
        # Genera warning se ci sono anomalie critiche
        critical_anomalies = [a for a in anomalies if a["severity"] == "critical"]
        if critical_anomalies:
            for anomaly in critical_anomalies:
                context.add_warning(self.name, f"Anomalia critica: {anomaly['message']}")
        
        return {
            "anomalies_found": len(anomalies),
            "critical_count": len(critical_anomalies),
            "anomalies": anomalies
        }
        
    def _check_data_anomalies(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Controlla anomalie nei dati sensori"""
        anomalies = []
        
        # Controllo umidità suolo
        soil_moisture = data.get("soil_moisture")
        if soil_moisture is not None:
            if soil_moisture < self.critical_thresholds["soil_moisture"]["min"]:
                anomalies.append({
                    "type": "low_soil_moisture",
                    "severity": "critical",
                    "value": soil_moisture,
                    "threshold": self.critical_thresholds["soil_moisture"]["min"],
                    "message": f"Umidità suolo criticamente bassa: {soil_moisture}%",
                    "recommendation": "Irrigazione urgente necessaria!"
                })
            elif soil_moisture > self.critical_thresholds["soil_moisture"]["max"]:
                anomalies.append({
                    "type": "high_soil_moisture",
                    "severity": "warning",
                    "value": soil_moisture,
                    "threshold": self.critical_thresholds["soil_moisture"]["max"],
                    "message": f"Umidità suolo molto alta: {soil_moisture}%",
                    "recommendation": "Verificare drenaggio. Rischio marciume radicale."
                })
        
        # Controllo temperatura
        temperature = data.get("temperature")
        if temperature is not None:
            if temperature < self.critical_thresholds["temperature"]["min"]:
                anomalies.append({
                    "type": "low_temperature",
                    "severity": "critical",
                    "value": temperature,
                    "threshold": self.critical_thresholds["temperature"]["min"],
                    "message": f"Temperatura criticamente bassa: {temperature}°C",
                    "recommendation": "Proteggere piante dal freddo!"
                })
            elif temperature > self.critical_thresholds["temperature"]["max"]:
                anomalies.append({
                    "type": "high_temperature",
                    "severity": "critical",
                    "value": temperature,
                    "threshold": self.critical_thresholds["temperature"]["max"],
                    "message": f"Temperatura criticamente alta: {temperature}°C",
                    "recommendation": "Ombreggiare e aumentare irrigazione!"
                })
        
        # Controllo umidità aria
        humidity = data.get("humidity")
        if humidity is not None:
            if humidity < self.critical_thresholds["humidity"]["min"]:
                anomalies.append({
                    "type": "low_humidity",
                    "severity": "warning",
                    "value": humidity,
                    "threshold": self.critical_thresholds["humidity"]["min"],
                    "message": f"Umidità aria molto bassa: {humidity}%",
                    "recommendation": "Aumentare frequenza irrigazione e nebulizzazione."
                })
            elif humidity > self.critical_thresholds["humidity"]["max"]:
                anomalies.append({
                    "type": "high_humidity",
                    "severity": "warning",
                    "value": humidity,
                    "threshold": self.critical_thresholds["humidity"]["max"],
                    "message": f"Umidità aria molto alta: {humidity}%",
                    "recommendation": "Migliorare ventilazione. Rischio funghi."
                })
        
        return anomalies
        
    def _check_feature_anomalies(self, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Controlla anomalie nelle features calcolate"""
        anomalies = []
        
        # Controllo stress idrico
        stress_index = features.get("water_stress_index")
        if stress_index is not None and stress_index > self.critical_thresholds["water_stress_index"]["max"]:
            anomalies.append({
                "type": "high_water_stress",
                "severity": "critical",
                "value": stress_index,
                "threshold": self.critical_thresholds["water_stress_index"]["max"],
                "message": f"Stress idrico critico: {stress_index:.1f}/100",
                "recommendation": "Azione immediata richiesta: irrigare e monitorare."
            })
        
        # Controllo urgenza irrigazione
        urgency = features.get("irrigation_urgency")
        if urgency is not None and urgency >= self.critical_thresholds["irrigation_urgency"]["max"]:
            anomalies.append({
                "type": "critical_irrigation_needed",
                "severity": "critical",
                "value": urgency,
                "threshold": self.critical_thresholds["irrigation_urgency"]["max"],
                "message": f"Urgenza irrigazione massima: {urgency}/10",
                "recommendation": "Irrigare immediatamente!"
            })
        
        # Controllo deficit idrico elevato
        deficit = features.get("water_deficit", 0)
        if deficit > 10:
            anomalies.append({
                "type": "high_water_deficit",
                "severity": "warning",
                "value": deficit,
                "threshold": 10,
                "message": f"Deficit idrico elevato: {deficit:.1f}mm",
                "recommendation": "Programmare irrigazione abbondante."
            })
        
        # Controllo comfort climatico basso
        comfort = features.get("climate_comfort_index", 100)
        if comfort < 30:
            anomalies.append({
                "type": "poor_climate_conditions",
                "severity": "warning",
                "value": comfort,
                "threshold": 30,
                "message": f"Condizioni climatiche sfavorevoli: {comfort:.1f}/100",
                "recommendation": "Monitorare attentamente le piante."
            })
        
        return anomalies
        
    def _check_estimation_anomalies(self, estimation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Controlla anomalie nella stima irrigazione"""
        anomalies = []
        
        # Controllo quantità acqua eccessiva
        water_amount = estimation.get("water_amount_ml", 0)
        if water_amount > 3000:
            anomalies.append({
                "type": "excessive_water_recommendation",
                "severity": "info",
                "value": water_amount,
                "threshold": 3000,
                "message": f"Raccomandazione irrigazione elevata: {water_amount}ml",
                "recommendation": "Verificare se la pianta può gestire questa quantità."
            })
        
        # Controllo confidence bassa
        confidence = estimation.get("confidence", 1.0)
        if confidence < 0.5:
            anomalies.append({
                "type": "low_confidence_estimation",
                "severity": "info",
                "value": confidence,
                "threshold": 0.5,
                "message": f"Stima con bassa confidenza: {confidence:.0%}",
                "recommendation": "Verificare manualmente le condizioni."
            })
        
        return anomalies
