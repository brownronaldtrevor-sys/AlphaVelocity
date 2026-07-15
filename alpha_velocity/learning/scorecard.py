from __future__ import annotations

from collections import defaultdict
from statistics import mean

from alpha_velocity.learning.models import ModelScorecard


class ChallengerPromotionGate:
    """
    A challenger cannot replace the champion based on a few paper trades.

    Promotion requires enough completed outcomes, acceptable calibration, positive
    mean return after modeled costs, and no material degradation in adverse excursion.
    """

    def __init__(
        self,
        minimum_samples: int = 100,
        maximum_brier_score: float = 0.23,
        minimum_mean_return_pct: float = 0.0,
        minimum_hit_rate: float = 0.52,
    ) -> None:
        self.minimum_samples = minimum_samples
        self.maximum_brier_score = maximum_brier_score
        self.minimum_mean_return_pct = minimum_mean_return_pct
        self.minimum_hit_rate = minimum_hit_rate

    def build_scorecards(
        self,
        forecasts: list[dict],
        outcomes: list[dict],
    ) -> list[ModelScorecard]:
        outcome_by_id = {o["forecast_id"]: o for o in outcomes}
        grouped: dict[str, list[tuple[dict, dict]]] = defaultdict(list)

        for forecast in forecasts:
            outcome = outcome_by_id.get(forecast["forecast_id"])
            if outcome is not None:
                grouped[forecast["model_id"]].append((forecast, outcome))

        results: list[ModelScorecard] = []
        for model_id, pairs in grouped.items():
            probabilities = [float(f["probability_target_before_stop"]) for f, _ in pairs]
            actuals = [
                1.0 if bool(o.get("target_before_stop")) else 0.0
                for _, o in pairs
                if o.get("target_before_stop") is not None
            ]
            paired_probs = [
                float(f["probability_target_before_stop"])
                for f, o in pairs
                if o.get("target_before_stop") is not None
            ]

            brier = (
                mean((p - y) ** 2 for p, y in zip(paired_probs, actuals))
                if actuals else None
            )
            returns = [float(o["realized_return_pct"]) for _, o in pairs]
            hit_rate = mean(actuals) if actuals else None
            mfe = mean(float(o["maximum_favorable_excursion_pct"]) for _, o in pairs)
            mae = mean(float(o["maximum_adverse_excursion_pct"]) for _, o in pairs)

            reasons: list[str] = []
            if len(pairs) < self.minimum_samples:
                reasons.append(
                    f"Only {len(pairs)} completed outcomes; {self.minimum_samples} required."
                )
            if brier is None or brier > self.maximum_brier_score:
                reasons.append("Calibration does not pass the Brier-score threshold.")
            if mean(returns) <= self.minimum_mean_return_pct:
                reasons.append("Mean paper return does not clear the promotion threshold.")
            if hit_rate is None or hit_rate < self.minimum_hit_rate:
                reasons.append("Target-before-stop hit rate is below threshold.")

            results.append(
                ModelScorecard(
                    model_id=model_id,
                    sample_count=len(pairs),
                    brier_score=brier,
                    mean_return_pct=mean(returns) if returns else None,
                    hit_rate=hit_rate,
                    average_mfe_pct=mfe,
                    average_mae_pct=mae,
                    eligible_for_promotion=not reasons,
                    reasons=reasons or ["All predeclared promotion gates passed."],
                )
            )
        return results
