from __future__ import annotations

from dataclasses import dataclass

from alpha_velocity.shadow.models import ShadowVerdict


@dataclass(frozen=True)
class FinalExposureDecision:
    opportunity_id: str
    primary_target_weight_pct: float
    shadow_target_weight_pct: float
    final_target_weight_pct: float
    governance_action: str
    explanation: str


def reconcile_primary_and_shadow(
    primary_targets: dict[str, float],
    shadow_verdicts: list[ShadowVerdict],
    shadow_veto_enabled: bool = True,
) -> list[FinalExposureDecision]:
    verdict_by_id = {v.opportunity_id: v for v in shadow_verdicts}
    results = []

    for opportunity_id, primary_weight in primary_targets.items():
        shadow = verdict_by_id.get(opportunity_id)
        if shadow is None:
            final = 0.0 if shadow_veto_enabled else primary_weight
            action = "BLOCK" if shadow_veto_enabled else "PRIMARY_ONLY"
            explanation = "No Shadow CIO review was available."
        else:
            if shadow_veto_enabled and shadow.verdict == "REJECT_OR_EXIT":
                final = 0.0
                action = "VETO"
                explanation = "Shadow CIO rejected the exposure."
            else:
                # Conservative production-governance default: use the lower target.
                final = min(primary_weight, shadow.shadow_target_weight_pct)
                action = "APPROVE_REDUCED" if final < primary_weight else "APPROVE"
                explanation = (
                    f"Primary target={primary_weight:.2f}%, "
                    f"Shadow target={shadow.shadow_target_weight_pct:.2f}%."
                )

        results.append(
            FinalExposureDecision(
                opportunity_id=opportunity_id,
                primary_target_weight_pct=primary_weight,
                shadow_target_weight_pct=(
                    shadow.shadow_target_weight_pct if shadow else 0.0
                ),
                final_target_weight_pct=round(final, 4),
                governance_action=action,
                explanation=explanation,
            )
        )
    return results
