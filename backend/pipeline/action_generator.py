"""
Step 5: Action Suggestion Generator
Genera suggerimenti finali di azione basati su tutti i dati processati.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base import ProcessorBase, PipelineContext, PipelineStage


class ActionGenerator(ProcessorBase):
    """
    Generatore di suggerimenti di azione.
    Combina tutti i risultati della pipeline per creare suggerimenti chiari e attuabili.
    """
    
    def __init__(self):
        super().__init__("Action Generator")
        
    def _get_stage(self) -> PipelineStage:
        return PipelineStage.ACTION_GENERATION
        
    def _execute(self, context: PipelineContext) -> Dict[str, Any]:
        """Genera suggerimenti di azione"""
        
        if not context.estimation:
            raise ValueError("Estimation non disponibile.")
        
        # Genera suggerimento principale
        main_action = self._generate_main_action(context)
        
        # Genera azioni secondarie
        secondary_actions = self._generate_secondary_actions(context)
        
        # Genera timing suggerito
        timing = self._suggest_timing(context)
        
        # Genera note e avvisi
        notes = self._generate_notes(context)
        
        # Componi suggerimento completo
        suggestions = {
            "main_action": main_action,
            "secondary_actions": secondary_actions,
            "timing": timing,
            "notes": notes,
            "priority": self._calculate_priority(context),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Salva nel contesto
        context.suggestions = suggestions
        
        return {
            "suggestions": suggestions
        }
        
    def _generate_main_action(self, context: PipelineContext) -> Dict[str, Any]:
        """Genera azione principale"""
        estimation = context.estimation
        
        return {
            "action": "irrigate" if estimation["should_water"] else "do_not_irrigate",
            "decision": estimation["decision"],
            "water_amount_ml": estimation["water_amount_ml"],
            "water_amount_liters": round(estimation["water_amount_ml"] / 1000, 2),
            "reasoning": estimation["reasoning"],
            "confidence": estimation["confidence"],
            "description": self._get_action_description(estimation)
        }
        
    def _get_action_description(self, estimation: Dict[str, Any]) -> str:
        """Genera descrizione testuale dell'azione"""
        if not estimation["should_water"]:
            return "Non è necessario irrigare in questo momento."
        
        amount_liters = estimation["water_amount_ml"] / 1000
        decision = estimation["decision"]
        
        descriptions = {
            "water_light": f"Irrigazione leggera consigliata: circa {amount_liters:.1f} litri.",
            "water_moderate": f"Irrigazione moderata consigliata: circa {amount_liters:.1f} litri.",
            "water_heavy": f"Irrigazione abbondante necessaria: circa {amount_liters:.1f} litri."
        }
        
        return descriptions.get(decision, f"Irrigare con {amount_liters:.1f} litri.")
        
    def _generate_secondary_actions(self, context: PipelineContext) -> List[Dict[str, Any]]:
        """Genera azioni secondarie basate su anomalie e condizioni"""
        actions = []
        
        # Azioni basate su anomalie critiche
        for anomaly in context.anomalies:
            if anomaly["severity"] == "critical":
                actions.append({
                    "type": "urgent",
                    "action": anomaly["recommendation"],
                    "reason": anomaly["message"]
                })
        
        # Azioni basate su features
        if context.features:
            features = context.features
            
            # Suggerisci ombreggiatura se troppo caldo
            if context.cleaned_data.get("temperature", 0) > 30:
                actions.append({
                    "type": "preventive",
                    "action": "Fornire ombreggiatura nelle ore più calde",
                    "reason": f"Temperatura elevata: {context.cleaned_data['temperature']}°C"
                })
            
            # Suggerisci ventilazione se umidità alta
            if context.cleaned_data.get("humidity", 0) > 85:
                actions.append({
                    "type": "preventive",
                    "action": "Migliorare ventilazione",
                    "reason": f"Umidità elevata: {context.cleaned_data['humidity']}%"
                })
            
            # Suggerisci monitoraggio se stress alto
            if features.get("water_stress_index", 0) > 60:
                actions.append({
                    "type": "monitoring",
                    "action": "Monitorare attentamente nelle prossime 24h",
                    "reason": f"Stress idrico elevato: {features['water_stress_index']:.1f}/100"
                })
        
        return actions
        
    def _suggest_timing(self, context: PipelineContext) -> Dict[str, Any]:
        """Suggerisce timing per l'irrigazione"""
        now = datetime.now()
        features = context.features or {}
        day_phase = features.get("day_phase", "unknown")
        
        # Timing ideale: mattina presto o sera
        if day_phase == "morning":
            suggested_time = "ora (mattino)"
            next_window = now
        elif day_phase == "afternoon":
            # Suggerisci sera
            suggested_time = "sera (dopo le 18:00)"
            next_window = now.replace(hour=18, minute=0, second=0)
            if next_window < now:
                next_window += timedelta(days=1)
        elif day_phase == "evening":
            suggested_time = "ora (sera)"
            next_window = now
        else:  # night
            suggested_time = "domani mattina (6:00-9:00)"
            next_window = (now + timedelta(days=1)).replace(hour=7, minute=0, second=0)
        
        # Se urgente, irrigare immediatamente
        urgency = features.get("irrigation_urgency", 0)
        if urgency >= 9:
            suggested_time = "IMMEDIATAMENTE"
            next_window = now
        
        return {
            "suggested_time": suggested_time,
            "next_window": next_window.isoformat(),
            "current_phase": day_phase,
            "ideal_hours": ["06:00-09:00", "18:00-21:00"]
        }
        
    def _generate_notes(self, context: PipelineContext) -> List[str]:
        """Genera note e avvisi"""
        notes = []
        
        # Aggiungi warning dalla pipeline
        if context.warnings:
            notes.extend(context.warnings)
        
        # Note su anomalie
        warning_anomalies = [a for a in context.anomalies if a["severity"] == "warning"]
        if warning_anomalies:
            notes.append(f"Rilevate {len(warning_anomalies)} condizioni che richiedono attenzione.")
        
        # Note su features
        if context.features:
            comfort = context.features.get("climate_comfort_index", 100)
            if comfort < 50:
                notes.append(f"Condizioni climatiche non ottimali (comfort: {comfort:.0f}/100).")
        
        # Note su confidenza
        if context.estimation and context.estimation.get("confidence", 1.0) < 0.7:
            notes.append("Stima con confidenza moderata. Consigliato controllo manuale.")
        
        return notes
        
    def _calculate_priority(self, context: PipelineContext) -> str:
        """Calcola priorità dell'azione (low, medium, high, urgent)"""
        
        # Controlla anomalie critiche
        critical_count = len([a for a in context.anomalies if a["severity"] == "critical"])
        if critical_count > 0:
            return "urgent"
        
        # Controlla urgenza irrigazione
        if context.features:
            urgency = context.features.get("irrigation_urgency", 0)
            if urgency >= 8:
                return "urgent"
            elif urgency >= 6:
                return "high"
            elif urgency >= 3:
                return "medium"
        
        return "low"
