from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OpportunityType(str, Enum):
    EARLY_INFLECTION = "EARLY_INFLECTION"
    CONFIRMED_INFLECTION = "CONFIRMED_INFLECTION"
    SYSTEMATIC_TREND = "SYSTEMATIC_TREND"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    SHORT = "SHORT"
    CASH = "CASH"


@dataclass(frozen=True)
class OpportunityState:
    opportunity_id: str
    opportunity_type: OpportunityType
    expected_return_pct: float
    probability_target_before_stop: float
    expected_holding_days: float
    downside_pct: float
    liquidity_score: float
    technical_readiness: float
    fundamental_strength: float
    macro_alignment: float
    execution_quality: float
    uncertainty: float
    correlation_penalty: float
    current_weight_pct: float = 0.0
    max_weight_pct: float = 100.0
    minimum_trade_weight_pct: float = 0.0

    @property
    def payoff_ratio(self) -> float:
        loss = max(abs(self.downside_pct), 0.01)
        return max(self.expected_return_pct, 0.0) / loss

    @property
    def readiness_score(self) -> float:
        return (
            0.30 * self.technical_readiness
            + 0.25 * self.fundamental_strength
            + 0.20 * self.macro_alignment
            + 0.15 * self.execution_quality
            + 0.10 * self.liquidity_score
        )

    @property
    def opportunity_score(self) -> float:
        days = max(self.expected_holding_days, 1.0)
        gross = (
            self.probability_target_before_stop
            * max(self.expected_return_pct, 0.0)
            * max(self.payoff_ratio, 0.0)
            * max(self.readiness_score, 1.0)
        )
        penalty = (
            max(self.uncertainty, 1.0)
            * max(self.correlation_penalty, 1.0)
            * days
        )
        return gross / penalty


@dataclass(frozen=True)
class TargetExposure:
    opportunity_id: str
    current_weight_pct: float
    target_weight_pct: float
    action: str
    opportunity_score: float
    reason: str


class DynamicExposureOptimizer:
    """
    Converts opportunity quality into a target portfolio weight.

    This is deterministic prototype logic. Production weights should ultimately
    be learned from point-in-time historical data and constrained by account risk.
    """

    def __init__(
        self,
        reserve_cash_pct: float = 10.0,
        replacement_margin_pct: float = 10.0,
        concentration_power: float = 2.0,
    ) -> None:
        if not 0 <= reserve_cash_pct <= 100:
            raise ValueError("reserve_cash_pct must be between 0 and 100.")
        self.reserve_cash_pct = reserve_cash_pct
        self.replacement_margin_pct = replacement_margin_pct
        self.concentration_power = concentration_power

    def allocate(self, opportunities: list[OpportunityState]) -> list[TargetExposure]:
        if not opportunities:
            return []

        tradable = [
            o for o in opportunities
            if o.opportunity_type != OpportunityType.CASH
            and o.opportunity_score > 0
            and o.readiness_score >= 35
        ]

        available_pct = max(0.0, 100.0 - self.reserve_cash_pct)

        # Stronger opportunities receive disproportionately more capital.
        powered = {
            o.opportunity_id: o.opportunity_score ** self.concentration_power
            for o in tradable
        }
        denominator = sum(powered.values()) or 1.0

        provisional: dict[str, float] = {}
        for o in tradable:
            raw = available_pct * powered[o.opportunity_id] / denominator
            capped = min(raw, o.max_weight_pct)
            provisional[o.opportunity_id] = capped

        # Redistribute unused capital from caps to uncapped names.
        for _ in range(10):
            allocated = sum(provisional.values())
            remaining = available_pct - allocated
            if remaining <= 1e-8:
                break
            eligible = [
                o for o in tradable
                if provisional[o.opportunity_id] + 1e-8 < o.max_weight_pct
            ]
            if not eligible:
                break
            extra_denom = sum(powered[o.opportunity_id] for o in eligible) or 1.0
            changed = False
            for o in eligible:
                add = remaining * powered[o.opportunity_id] / extra_denom
                new_weight = min(
                    o.max_weight_pct,
                    provisional[o.opportunity_id] + add
                )
                if new_weight > provisional[o.opportunity_id]:
                    changed = True
                provisional[o.opportunity_id] = new_weight
            if not changed:
                break

        results: list[TargetExposure] = []
        for o in opportunities:
            if o.opportunity_type == OpportunityType.CASH:
                continue

            target = provisional.get(o.opportunity_id, 0.0)
            if 0 < target < o.minimum_trade_weight_pct:
                target = 0.0

            delta = target - o.current_weight_pct
            threshold = max(0.5, o.current_weight_pct * self.replacement_margin_pct / 100)

            if delta > threshold:
                action = "ADD"
            elif delta < -threshold:
                action = "REDUCE"
            else:
                action = "HOLD"

            results.append(
                TargetExposure(
                    opportunity_id=o.opportunity_id,
                    current_weight_pct=o.current_weight_pct,
                    target_weight_pct=round(target, 4),
                    action=action,
                    opportunity_score=o.opportunity_score,
                    reason=(
                        f"Target derived from portfolio-wide opportunity competition; "
                        f"readiness={o.readiness_score:.1f}, "
                        f"score={o.opportunity_score:.3f}, "
                        f"max_weight={o.max_weight_pct:.1f}%."
                    ),
                )
            )

        allocated = sum(r.target_weight_pct for r in results)
        results.append(
            TargetExposure(
                opportunity_id="CASH",
                current_weight_pct=0.0,
                target_weight_pct=round(max(0.0, 100.0 - allocated), 4),
                action="HOLD",
                opportunity_score=0.0,
                reason="Residual capital and explicit reserve remain in cash.",
            )
        )
        return sorted(results, key=lambda r: r.target_weight_pct, reverse=True)
