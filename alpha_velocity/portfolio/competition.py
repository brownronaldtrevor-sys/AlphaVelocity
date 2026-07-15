from __future__ import annotations

from dataclasses import dataclass

from alpha_velocity.portfolio.exposure import OpportunityState, TargetExposure


@dataclass(frozen=True)
class CapitalCompetitionReport:
    ranked_opportunities: list[OpportunityState]
    exposures: list[TargetExposure]
    best_opportunity_id: str | None
    current_portfolio_score: float
    proposed_portfolio_score: float


def build_report(
    opportunities: list[OpportunityState],
    exposures: list[TargetExposure],
) -> CapitalCompetitionReport:
    ranked = sorted(opportunities, key=lambda x: x.opportunity_score, reverse=True)
    current_score = sum(
        o.opportunity_score * max(o.current_weight_pct, 0.0) / 100.0
        for o in opportunities
    )
    weight_by_id = {e.opportunity_id: e.target_weight_pct for e in exposures}
    proposed_score = sum(
        o.opportunity_score * weight_by_id.get(o.opportunity_id, 0.0) / 100.0
        for o in opportunities
    )
    return CapitalCompetitionReport(
        ranked_opportunities=ranked,
        exposures=exposures,
        best_opportunity_id=ranked[0].opportunity_id if ranked else None,
        current_portfolio_score=current_score,
        proposed_portfolio_score=proposed_score,
    )
