from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DecisionCandidate:
    opportunity_id: str
    proposed_action: str
    current_weight_pct: float
    proposed_weight_pct: float
    opportunity_score: float
    readiness_score: float
    expected_return_pct: float
    expected_holding_days: float
    downside_pct: float
    uncertainty: float
    liquidity_score: float
    execution_quality: float
    thesis_strength: float
    technical_strength: float
    macro_strength: float
    evidence_count: int
    contradiction_count: int
    model_disagreement: float
    data_trust_score: float
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ShadowVerdict:
    opportunity_id: str
    verdict: str
    shadow_target_weight_pct: float
    confidence: float
    challenge_score: float
    opportunity_cost_rank: int | None
    reasons: list[str]
    required_confirmations: list[str]
    invalidation_conditions: list[str]


@dataclass(frozen=True)
class CounterfactualRecord:
    decision_id: str
    opportunity_id: str
    decision_time: str
    chosen_action: str
    chosen_weight_pct: float
    alternatives: dict[str, float]
    expected_metrics: dict[str, float]
    evidence_snapshot: dict[str, Any]


@dataclass(frozen=True)
class DecisionGrade:
    decision_id: str
    opportunity_id: str
    realized_return_pct: float
    benchmark_return_pct: float
    best_alternative_return_pct: float
    timing_quality: float
    sizing_quality: float
    opportunity_cost_pct: float
    thesis_accuracy: float
    execution_quality: float
    overall_grade: float
    lessons: list[str]
    graded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
