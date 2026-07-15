from __future__ import annotations

from math import sqrt
from statistics import mean, pstdev

from alpha_velocity.ensemble.auditor import EnsembleAuditor
from alpha_velocity.ensemble.models import EnsemblePrediction, ModelPrediction


class CalibratedWeightedEnsemble:
    """
    Conservative weighted ensemble.

    Weighting rewards out-of-sample validation and calibration while penalizing
    uncertainty. Weights are not optimized on the same sample used for evaluation.
    """

    def __init__(self, auditor: EnsembleAuditor | None = None) -> None:
        self.auditor = auditor or EnsembleAuditor()

    @staticmethod
    def _raw_weight(p: ModelPrediction) -> float:
        calibration_quality = max(1e-6, 1.0 - p.calibration_brier)
        validation_quality = max(1e-6, p.validation_score + 1.0)
        uncertainty_penalty = max(1e-6, 1.0 - p.uncertainty)
        return calibration_quality * validation_quality * uncertainty_penalty

    def combine(self, predictions: list[ModelPrediction]) -> EnsemblePrediction:
        accepted, rejected = self.auditor.filter_models(predictions)
        timestamp = accepted[0].timestamp
        if any(p.timestamp != timestamp for p in accepted):
            raise ValueError("All model predictions must share the same decision timestamp.")

        raw = {p.model_id: self._raw_weight(p) for p in accepted}
        denom = sum(raw.values())
        weights = {k: v / denom for k, v in raw.items()}

        probability_up = sum(weights[p.model_id] * p.probability_up for p in accepted)
        expected_return = sum(weights[p.model_id] * p.expected_return for p in accepted)

        probs = [p.probability_up for p in accepted]
        disagreement = pstdev(probs) if len(probs) > 1 else 0.0
        model_uncertainty = sum(weights[p.model_id] * p.uncertainty for p in accepted)

        # Ensemble uncertainty includes disagreement; it is not allowed to shrink
        # merely because many correlated models were added.
        uncertainty = min(1.0, model_uncertainty + disagreement)

        return EnsemblePrediction(
            timestamp=timestamp,
            probability_up=probability_up,
            expected_return=expected_return,
            uncertainty=uncertainty,
            active_models=tuple(p.model_id for p in accepted),
            weights=weights,
            disagreement=disagreement,
            rejected_models=rejected,
        )
