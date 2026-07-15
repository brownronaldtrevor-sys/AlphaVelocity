from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from alpha_velocity.objective.models import CompoundingObjectiveResult, ReturnDistributionForecast


@dataclass(frozen=True)
class PortfolioCandidate:
    opportunity_id: str
    forecast: ReturnDistributionForecast
    objective: CompoundingObjectiveResult
    maximum_weight: float
    current_weight: float
    liquidity_score: float
    correlation_cluster: str
    execution_cost_pct: float


@dataclass(frozen=True)
class PortfolioAllocation:
    opportunity_id: str
    target_weight: float
    current_weight: float
    action: str
    rationale: str


class CvarAwareAllocator:
    """
    Conservative deterministic allocator.

    This is not a convex optimizer. It is an auditable ranking-and-capping layer
    intended for paper testing before a formal optimizer is introduced.
    """

    def __init__(
        self,
        gross_exposure_limit: float = 1.0,
        cash_reserve: float = 0.10,
        cluster_limit: float = 0.40,
        replacement_margin: float = 0.10,
    ) -> None:
        self.gross_exposure_limit = gross_exposure_limit
        self.cash_reserve = cash_reserve
        self.cluster_limit = cluster_limit
        self.replacement_margin = replacement_margin

    def allocate(self, candidates: list[PortfolioCandidate]) -> list[PortfolioAllocation]:
        if not candidates:
            return []

        usable = max(0.0, self.gross_exposure_limit - self.cash_reserve)
        ranked = sorted(
            candidates,
            key=lambda c: c.objective.capital_priority_score,
            reverse=True,
        )

        positive = [
            c for c in ranked
            if c.objective.capital_priority_score > 0
            and c.objective.expected_log_growth > 0
        ]
        if not positive:
            return [
                PortfolioAllocation(
                    opportunity_id=c.opportunity_id,
                    target_weight=0.0,
                    current_weight=c.current_weight,
                    action="EXIT" if c.current_weight > 0 else "AVOID",
                    rationale="Does not clear positive expected-log-growth hurdle.",
                )
                for c in candidates
            ]

        scores = [max(c.objective.capital_priority_score, 1e-12) ** 1.5 for c in positive]
        score_total = sum(scores)
        targets: dict[str, float] = {c.opportunity_id: 0.0 for c in candidates}
        cluster_used: dict[str, float] = {}

        for c, score in zip(positive, scores):
            raw = usable * score / score_total
            kelly_cap = c.objective.live_kelly_fraction
            cluster_remaining = max(
                0.0,
                self.cluster_limit - cluster_used.get(c.correlation_cluster, 0.0),
            )
            target = min(raw, c.maximum_weight, kelly_cap, cluster_remaining)
            targets[c.opportunity_id] = target
            cluster_used[c.correlation_cluster] = (
                cluster_used.get(c.correlation_cluster, 0.0) + target
            )

        results = []
        for c in candidates:
            target = targets[c.opportunity_id]
            delta = target - c.current_weight
            threshold = max(0.005, c.current_weight * self.replacement_margin)

            if target == 0 and c.current_weight > 0:
                action = "EXIT"
            elif delta > threshold:
                action = "ADD"
            elif delta < -threshold:
                action = "REDUCE"
            else:
                action = "HOLD"

            results.append(
                PortfolioAllocation(
                    opportunity_id=c.opportunity_id,
                    target_weight=round(target, 6),
                    current_weight=c.current_weight,
                    action=action,
                    rationale=(
                        f"Capital priority={c.objective.capital_priority_score:.6f}; "
                        f"expected log growth={c.objective.expected_log_growth:.6f}; "
                        f"Kelly cap={c.objective.live_kelly_fraction:.2%}; "
                        f"CVaR proxy={c.objective.cvar_penalty:.4f}."
                    ),
                )
            )

        return sorted(results, key=lambda x: x.target_weight, reverse=True)
