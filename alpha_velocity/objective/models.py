from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


@dataclass(frozen=True)
class ReturnDistributionForecast:
    opportunity_id: str
    timestamp: datetime
    probability_positive: float
    probability_target_before_stop: float
    expected_return: float
    median_return: float
    expected_favorable_excursion: float
    expected_adverse_excursion: float
    tail_loss_probability: float
    expected_time_days: float
    uncertainty: float
    data_trust_score: float
    model_disagreement: float
    source_weights: Mapping[str, float]


@dataclass(frozen=True)
class CompoundingObjectiveResult:
    opportunity_id: str
    expected_log_growth: float
    raw_kelly_fraction: float
    uncertainty_haircut: float
    live_kelly_fraction: float
    cvar_penalty: float
    execution_penalty: float
    capital_priority_score: float
