"""
Step 1: Data Validator / Cleaner
Valida e pulisce i dati in ingresso dai sensori.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import math
from .base import ProcessorBase, PipelineContext, PipelineStage


class DataValidator(ProcessorBase):
    """
    Validatore e pulitore dati.
    - Valida formato e range dei dati
    - Rimuove outlier
    - Imputa valori mancanti
    """
    
    def __init__(self):
        super().__init__("Data Validator")
        
        # Definisci range validi per ogni sensore
        self.valid_ranges = {
            "soil_moisture": (0, 100),      # %
            "temperature": (-10, 50),        # °C
            "humidity": (0, 100),            # %
            "light": (0, 100000),            # lux
            "rainfall": (0, 500),            # mm
        }
        
        # Valori default per imputazione
        self.default_values = {
            "soil_moisture": 50.0,
            "temperature": 20.0,
            "humidity": 60.0,
            "light": 10000.0,
            "rainfall": 0.0,
        }
        
    def _get_stage(self) -> PipelineStage:
        return PipelineStage.VALIDATION
        
    def _execute(self, context: PipelineContext) -> Dict[str, Any]:
        """Valida e pulisce i dati"""
        raw_data = context.raw_data
        cleaned = {}
        issues = []
        
        # Valida ogni campo
        for field, value in raw_data.items():
            if field not in self.valid_ranges:
                # Campo non riconosciuto, mantienilo così
                cleaned[field] = value
                continue
                
            # Valida valore
            cleaned_value, issue = self._validate_value(field, value)
            cleaned[field] = cleaned_value
            
            if issue:
                issues.append(issue)
                context.add_warning(self.name, issue)
        
        # Imputa valori mancanti
        for field in self.valid_ranges.keys():
            if field not in cleaned or cleaned[field] is None:
                cleaned[field] = self.default_values[field]
                issues.append(f"Campo '{field}' mancante, usato default: {self.default_values[field]}")
                context.add_warning(self.name, issues[-1])
        
        # Salva dati puliti nel contesto
        context.cleaned_data = cleaned
        
        return {
            "cleaned_data": cleaned,
            "issues_found": len(issues),
            "issues": issues
        }
        
    def _validate_value(self, field: str, value: Any) -> tuple[float, Optional[str]]:
        """
        Valida un singolo valore.
        Returns: (valore_pulito, messaggio_errore_opzionale)
        """
        # Converti a float
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            return self.default_values[field], f"Valore non numerico per '{field}': {value}"
        
        # Controlla NaN/Inf
        if math.isnan(numeric_value) or math.isinf(numeric_value):
            return self.default_values[field], f"Valore invalido per '{field}': {value}"
        
        # Controlla range
        min_val, max_val = self.valid_ranges[field]
        if numeric_value < min_val or numeric_value > max_val:
            # Clamp al range valido
            clamped = max(min_val, min(max_val, numeric_value))
            return clamped, f"Valore fuori range per '{field}': {numeric_value} (clamped a {clamped})"
        
        return numeric_value, None
