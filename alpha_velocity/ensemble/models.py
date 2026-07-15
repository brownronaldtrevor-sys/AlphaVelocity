from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


@dataclass(frozen=True)
class ModelPrediction:
    model_id: str
    timestamp: datetime
    probability_up: float
    expected_return: float
    uncertainty: float
    calibration_brier: float
    validation_score: float
    regime: str
    feature_family: str


@dataclass(frozen=True)
class EnsemblePrediction:
    timestamp: datetime
    probability_up: float
    expected_return: float
    uncertainty: float
    active_models: tuple[str, ...]
    weights: Mapping[str, float]
    disagreement: float
    rejected_models: Mapping[str, str]
