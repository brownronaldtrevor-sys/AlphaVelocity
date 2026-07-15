from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from alpha_velocity.shadow.models import DecisionCandidate, ShadowVerdict


@dataclass(frozen=True)
class ShadowCIOConfig:
    maximum_unconfirmed_weight_pct: float = 8.0
    maximum_high_uncertainty_weight_pct: float = 12.0
    minimum_data_trust_score: float = 60.0
    minimum_readiness_for_add: float = 58.0
    minimum_readiness_for_heavy_add: float = 78.0
    maximum_model_disagreement_for_heavy_add: float = 22.0
    contradiction_penalty_per_item: float = 6.0
    confirmation_bonus_per_item: float = 2.0
    cash_hurdle_score: float = 0.20
    replacement_margin: float = 0.15


class ShadowCIO:
    """
    Independent adversarial evaluator.

    It does not place orders. It reviews proposed portfolio decisions, challenges
    assumptions, compares every candidate with alternatives and cash, and returns
    an independent target weight plus explicit reasons.
    """

    def __init__(self, config: ShadowCIOConfig | None = None) -> None:
        self.config = config or ShadowCIOConfig()

    def _evidence_quality(self, c: DecisionCandidate) -> float:
        balance = (
            c.evidence_count * self.config.confirmation_bonus_per_item
            - c.contradiction_count * self.config.contradiction_penalty_per_item
        )
        quality = (
            0.24 * c.data_trust_score
            + 0.20 * c.readiness_score
            + 0.14 * c.thesis_strength
            + 0.12 * c.technical_strength
            + 0.10 * c.macro_strength
            + 0.10 * c.liquidity_score
            + 0.10 * c.execution_quality
            + balance
            - 0.25 * c.uncertainty
            - 0.30 * c.model_disagreement
        )
        return max(0.0, min(100.0, quality))

    def _shadow_weight(self, c: DecisionCandidate, evidence_quality: float) -> float:
        requested = max(0.0, c.proposed_weight_pct)

        if c.data_trust_score < self.config.minimum_data_trust_score:
            return 0.0

        if c.readiness_score < 40:
            return min(requested, 2.0)

        if c.readiness_score < self.config.minimum_readiness_for_add:
            return min(requested, self.config.maximum_unconfirmed_weight_pct)

        if c.uncertainty >= 70 or c.model_disagreement >= 45:
            return min(requested, self.config.maximum_high_uncertainty_weight_pct)

        if (
            c.readiness_score >= self.config.minimum_readiness_for_heavy_add
            and c.model_disagreement <= self.config.maximum_model_disagreement_for_heavy_add
            and evidence_quality >= 75
            and c.contradiction_count == 0
        ):
            return requested

        # Moderate confirmation: allow most, but not all, of the proposal.
        scale = max(0.25, min(1.0, evidence_quality / 85.0))
        return requested * scale

    def review(
        self,
        candidates: list[DecisionCandidate],
    ) -> list[ShadowVerdict]:
        ranked = sorted(candidates, key=lambda c: c.opportunity_score, reverse=True)
        rank_by_id = {c.opportunity_id: i + 1 for i, c in enumerate(ranked)}
        top_score = ranked[0].opportunity_score if ranked else 0.0

        verdicts: list[ShadowVerdict] = []
        for c in candidates:
            evidence_quality = self._evidence_quality(c)
            target = self._shadow_weight(c, evidence_quality)
            reasons: list[str] = []
            confirmations: list[str] = []
            invalidations: list[str] = []

            if c.data_trust_score < self.config.minimum_data_trust_score:
                reasons.append("Data trust is below the minimum decision threshold.")
                confirmations.append("Resolve missing, stale, conflicting or low-confidence data.")
            if c.readiness_score < self.config.minimum_readiness_for_add:
                reasons.append("Opportunity is not fully ready; provisional exposure only.")
                confirmations.append("Require stronger price, volume or fundamental confirmation.")
            if c.model_disagreement > self.config.maximum_model_disagreement_for_heavy_add:
                reasons.append("Models disagree materially about the opportunity.")
                confirmations.append("Wait for disagreement to narrow or reduce proposed size.")
            if c.contradiction_count > 0:
                reasons.append(f"{c.contradiction_count} material contradictions remain unresolved.")
                confirmations.append("Investigate and clear the strongest contradictory evidence.")
            if c.uncertainty >= 70:
                reasons.append("Outcome uncertainty is elevated.")
                invalidations.append("Reduce immediately if the thesis weakens or liquidity deteriorates.")
            if c.downside_pct >= max(15.0, c.expected_return_pct):
                reasons.append("Downside is too large relative to expected upside.")
            if c.execution_quality < 50:
                reasons.append("Execution quality is weak at the current price/liquidity.")
                confirmations.append("Wait for a more favorable spread, volume window or entry structure.")

            opportunity_gap = top_score - c.opportunity_score
            if opportunity_gap > self.config.replacement_margin:
                reasons.append("Stronger competing opportunities currently exist.")
            if c.opportunity_score <= self.config.cash_hurdle_score:
                reasons.append("The opportunity does not clear the cash hurdle.")
                target = 0.0

            delta = target - c.current_weight_pct
            if target == 0:
                verdict = "REJECT_OR_EXIT"
            elif delta > max(0.5, c.current_weight_pct * 0.08):
                verdict = "ADD"
            elif delta < -max(0.5, c.current_weight_pct * 0.08):
                verdict = "REDUCE"
            else:
                verdict = "HOLD"

            challenge_score = max(
                0.0,
                min(
                    100.0,
                    100
                    - evidence_quality
                    + c.model_disagreement * 0.35
                    + c.contradiction_count * 8,
                ),
            )
            confidence = max(
                0.0,
                min(
                    100.0,
                    evidence_quality
                    * (1 - min(c.uncertainty, 100.0) / 180.0),
                ),
            )

            if not invalidations:
                invalidations.extend([
                    "Thesis strength falls materially.",
                    "Price structure fails its defined invalidation level.",
                    "A superior opportunity exceeds the replacement threshold.",
                ])

            verdicts.append(
                ShadowVerdict(
                    opportunity_id=c.opportunity_id,
                    verdict=verdict,
                    shadow_target_weight_pct=round(target, 4),
                    confidence=round(confidence, 2),
                    challenge_score=round(challenge_score, 2),
                    opportunity_cost_rank=rank_by_id.get(c.opportunity_id),
                    reasons=reasons or ["No major objection found."],
                    required_confirmations=confirmations,
                    invalidation_conditions=invalidations,
                )
            )
        return verdicts
