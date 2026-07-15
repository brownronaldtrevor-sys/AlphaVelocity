from __future__ import annotations

from dataclasses import dataclass

from alpha_velocity.ensemble.models import ModelPrediction


@dataclass(frozen=True)
class EnsembleAuditConfig:
    max_brier_score: float = 0.24
    min_validation_score: float = 0.0
    max_uncertainty: float = 0.70
    min_model_count: int = 2
    max_same_family_share: float = 0.70
    max_pairwise_correlation: float = 0.90


class EnsembleAuditError(RuntimeError):
    pass


class EnsembleAuditor:
    """
    Validates ensemble eligibility before any prediction is combined.

    A model is rejected when its calibration, validation score, or uncertainty fails
    predeclared thresholds. The ensemble itself is rejected if model diversity is too low.
    """

    def __init__(self, config: EnsembleAuditConfig | None = None) -> None:
        self.config = config or EnsembleAuditConfig()

    def filter_models(
        self,
        predictions: list[ModelPrediction],
    ) -> tuple[list[ModelPrediction], dict[str, str]]:
        accepted: list[ModelPrediction] = []
        rejected: dict[str, str] = {}

        for p in predictions:
            if not 0.0 <= p.probability_up <= 1.0:
                rejected[p.model_id] = "Probability is outside [0, 1]."
            elif p.calibration_brier > self.config.max_brier_score:
                rejected[p.model_id] = (
                    f"Brier score {p.calibration_brier:.4f} exceeds "
                    f"{self.config.max_brier_score:.4f}."
                )
            elif p.validation_score < self.config.min_validation_score:
                rejected[p.model_id] = "Validation score is below threshold."
            elif p.uncertainty > self.config.max_uncertainty:
                rejected[p.model_id] = "Uncertainty is above threshold."
            else:
                accepted.append(p)

        if len(accepted) < self.config.min_model_count:
            raise EnsembleAuditError(
                f"Only {len(accepted)} eligible models remain; "
                f"{self.config.min_model_count} required."
            )

        family_counts: dict[str, int] = {}
        for p in accepted:
            family_counts[p.feature_family] = family_counts.get(p.feature_family, 0) + 1
        largest_family_share = max(family_counts.values()) / len(accepted)

        if largest_family_share > self.config.max_same_family_share:
            raise EnsembleAuditError(
                "Ensemble lacks feature-family diversity. "
                "Correlated models do not create independent evidence."
            )

        return accepted, rejected
