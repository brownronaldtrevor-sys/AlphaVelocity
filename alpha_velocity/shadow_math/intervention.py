from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InterventionLevel(str, Enum):
    SILENT = "SILENT"
    OBSERVATION = "OBSERVATION"
    CONCERN = "CONCERN"
    MAJOR_CONCERN = "MAJOR_CONCERN"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ShadowIntervention:
    opportunity_id: str
    level: InterventionLevel
    disagreement_score: float
    message: str
    recommended_weight_cap: float | None = None


class GraduatedShadowCIO:
    """
    Shadow CIO does not lead. It escalates only as evidence quality deteriorates.
    """

    def evaluate(
        self,
        opportunity_id: str,
        primary_weight: float,
        data_trust_score: float,
        model_disagreement: float,
        tail_loss_probability: float,
        execution_failure: bool,
        mandate_violation: bool,
        unresolved_contradictions: int,
    ) -> ShadowIntervention:
        if execution_failure or mandate_violation or data_trust_score < 40:
            return ShadowIntervention(
                opportunity_id,
                InterventionLevel.BLOCK,
                100.0,
                "Critical control failure: execution, mandate, or data integrity.",
                0.0,
            )

        score = (
            model_disagreement * 45
            + tail_loss_probability * 35
            + unresolved_contradictions * 8
            + max(0.0, 70 - data_trust_score) * 0.6
        )
        score = max(0.0, min(100.0, score))

        if score < 15:
            return ShadowIntervention(
                opportunity_id,
                InterventionLevel.SILENT,
                score,
                "No material objection.",
                None,
            )
        if score < 30:
            return ShadowIntervention(
                opportunity_id,
                InterventionLevel.OBSERVATION,
                score,
                "Minor discrepancy; no override.",
                None,
            )
        if score < 50:
            return ShadowIntervention(
                opportunity_id,
                InterventionLevel.CONCERN,
                score,
                "Moderate concern; review evidence before increasing exposure.",
                min(primary_weight, 0.15),
            )
        if score < 75:
            return ShadowIntervention(
                opportunity_id,
                InterventionLevel.MAJOR_CONCERN,
                score,
                "Material disagreement or tail risk; cap exposure pending confirmation.",
                min(primary_weight, 0.08),
            )
        return ShadowIntervention(
            opportunity_id,
            InterventionLevel.BLOCK,
            score,
            "Risk evidence is too weak or contradictory to justify exposure.",
            0.0,
        )
