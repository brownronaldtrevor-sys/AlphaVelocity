from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class PriceActionSnapshot:
    close_location_1d: float
    range_position_20d: float
    range_position_60d: float
    trend_structure: float
    compression_ratio: float
    expansion_ratio: float
    gap_pct: float
    breakout_distance_20d: float
    breakdown_distance_20d: float
    failed_breakout: bool
    failed_breakdown: bool
    support_distance_60d: float
    resistance_distance_60d: float
    relative_volume: float
    accumulation_score: float
    distribution_score: float
    evidence_score: float
    invalidation_price: float
    feature_values: Mapping[str, float]


@dataclass(frozen=True)
class PriceActionValidation:
    feature_set_id: str
    sample_count: int
    baseline_brier: float
    candidate_brier: float
    baseline_log_loss: float
    candidate_log_loss: float
    baseline_mean_return: float
    candidate_mean_return: float
    brier_improvement: float
    log_loss_improvement: float
    mean_return_improvement: float
    regime_pass_rate: float
    approved: bool
    approved_weight: float
    reasons: tuple[str, ...]
