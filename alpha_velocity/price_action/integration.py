from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceBlend:
    baseline_score: float
    price_action_score: float
    price_action_weight: float
    blended_score: float


def blend_price_action_evidence(
    baseline_score: float,
    price_action_score: float,
    approved_weight: float,
) -> EvidenceBlend:
    """Blend only a validated, capped price-action contribution.

    With no approved validation artifact, approved_weight is zero and the baseline
    is unchanged. This prevents feature accumulation from degrading the objective.
    """
    weight = max(0.0, min(0.20, approved_weight))
    baseline = max(0.0, min(100.0, baseline_score))
    price = max(0.0, min(100.0, price_action_score))
    blended = (1.0 - weight) * baseline + weight * price
    return EvidenceBlend(baseline, price, weight, blended)
