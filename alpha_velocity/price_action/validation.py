from __future__ import annotations

import math
from dataclasses import asdict
from pathlib import Path
import json

from alpha_velocity.price_action.models import PriceActionValidation


def _clip_probability(value: float) -> float:
    return max(1e-6, min(1.0 - 1e-6, value))


def brier_score(probabilities: list[float], outcomes: list[int]) -> float:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("Probabilities and outcomes must be non-empty and equally sized.")
    return sum((p - y) ** 2 for p, y in zip(probabilities, outcomes)) / len(outcomes)


def log_loss(probabilities: list[float], outcomes: list[int]) -> float:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("Probabilities and outcomes must be non-empty and equally sized.")
    losses = []
    for probability, outcome in zip(probabilities, outcomes):
        p = _clip_probability(probability)
        losses.append(-(outcome * math.log(p) + (1 - outcome) * math.log(1 - p)))
    return sum(losses) / len(losses)


def validate_incremental_price_action(
    *,
    feature_set_id: str,
    baseline_probabilities: list[float],
    candidate_probabilities: list[float],
    outcomes: list[int],
    baseline_returns: list[float],
    candidate_returns: list[float],
    regime_passes: list[bool],
    minimum_samples: int = 500,
    minimum_brier_improvement: float = 0.0025,
    minimum_log_loss_improvement: float = 0.0025,
    minimum_return_improvement: float = 0.0,
    minimum_regime_pass_rate: float = 0.60,
    maximum_weight: float = 0.20,
) -> PriceActionValidation:
    """Approve price action only when it adds incremental unseen-data value."""
    sizes = {
        len(baseline_probabilities), len(candidate_probabilities), len(outcomes),
        len(baseline_returns), len(candidate_returns), len(regime_passes),
    }
    if len(sizes) != 1:
        raise ValueError("Every validation input must contain the same observations.")
    sample_count = len(outcomes)
    if sample_count == 0:
        raise ValueError("Validation requires observations.")

    base_brier = brier_score(baseline_probabilities, outcomes)
    cand_brier = brier_score(candidate_probabilities, outcomes)
    base_loss = log_loss(baseline_probabilities, outcomes)
    cand_loss = log_loss(candidate_probabilities, outcomes)
    base_return = sum(baseline_returns) / sample_count
    cand_return = sum(candidate_returns) / sample_count
    regime_rate = sum(bool(value) for value in regime_passes) / sample_count

    brier_improvement = base_brier - cand_brier
    loss_improvement = base_loss - cand_loss
    return_improvement = cand_return - base_return

    reasons: list[str] = []
    if sample_count < minimum_samples:
        reasons.append(f"Only {sample_count} observations; {minimum_samples} required.")
    if brier_improvement < minimum_brier_improvement:
        reasons.append("Incremental Brier-score improvement is insufficient.")
    if loss_improvement < minimum_log_loss_improvement:
        reasons.append("Incremental log-loss improvement is insufficient.")
    if return_improvement <= minimum_return_improvement:
        reasons.append("Incremental net-return improvement is insufficient.")
    if regime_rate < minimum_regime_pass_rate:
        reasons.append("The feature set is not stable across enough regimes.")

    approved = not reasons
    # Weight grows only with proven calibration improvement and remains capped.
    earned_weight = 0.0
    if approved:
        quality = min(
            1.0,
            (brier_improvement / max(minimum_brier_improvement, 1e-12)
             + loss_improvement / max(minimum_log_loss_improvement, 1e-12)) / 4.0,
        )
        earned_weight = min(maximum_weight, maximum_weight * max(0.25, quality))

    return PriceActionValidation(
        feature_set_id=feature_set_id,
        sample_count=sample_count,
        baseline_brier=base_brier,
        candidate_brier=cand_brier,
        baseline_log_loss=base_loss,
        candidate_log_loss=cand_loss,
        baseline_mean_return=base_return,
        candidate_mean_return=cand_return,
        brier_improvement=brier_improvement,
        log_loss_improvement=loss_improvement,
        mean_return_improvement=return_improvement,
        regime_pass_rate=regime_rate,
        approved=approved,
        approved_weight=earned_weight,
        reasons=tuple(reasons or ["All predeclared incremental-value gates passed."]),
    )


def write_validation_artifact(result: PriceActionValidation, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")


def load_approved_weight(path: str | Path) -> float:
    source = Path(path)
    if not source.exists():
        return 0.0
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not bool(payload.get("approved", False)):
        return 0.0
    return max(0.0, min(0.20, float(payload.get("approved_weight", 0.0))))
