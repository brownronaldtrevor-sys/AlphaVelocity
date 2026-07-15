from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ForecastRecord:
    forecast_id: str
    model_id: str
    symbol: str
    decision_time: str
    horizon_days: int
    probability_target_before_stop: float
    expected_return_pct: float
    expected_adverse_pct: float
    target_pct: float
    stop_pct: float
    feature_snapshot: dict[str, float]
    rationale: list[str]
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class OutcomeRecord:
    forecast_id: str
    symbol: str
    evaluation_time: str
    realized_return_pct: float
    target_hit: bool
    stop_hit: bool
    target_before_stop: bool | None
    maximum_favorable_excursion_pct: float
    maximum_adverse_excursion_pct: float
    bars_observed: int


@dataclass(frozen=True)
class ModelScorecard:
    model_id: str
    sample_count: int
    brier_score: float | None
    mean_return_pct: float | None
    hit_rate: float | None
    average_mfe_pct: float | None
    average_mae_pct: float | None
    eligible_for_promotion: bool
    reasons: list[str]
