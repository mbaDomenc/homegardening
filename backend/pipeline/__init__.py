"""
Pipeline di processing per analisi dati sensori e suggerimenti irrigazione.
Implementa pattern Chain of Responsibility e Strategy.
"""

from .base import ProcessorBase, PipelineContext, PipelineStage, PipelineStatus
from .validators import DataValidator
from .feature_engineering import FeatureEngineer
from .estimators import IrrigationEstimator, PlantType, IrrigationDecision
from .anomaly_detector import AnomalyDetector
from .action_generator import ActionGenerator
from .pipeline_manager import PipelineManager

__all__ = [
    "ProcessorBase",
    "PipelineContext",
    "PipelineStage",
    "PipelineStatus",
    "DataValidator",
    "FeatureEngineer",
    "IrrigationEstimator",
    "PlantType",
    "IrrigationDecision",
    "AnomalyDetector",
    "ActionGenerator",
    "PipelineManager"
]
