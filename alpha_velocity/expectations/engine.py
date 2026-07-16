"""
Expectations research engine: orchestrates reported facts, market expectations, and research scenarios.

Validates point-in-time data, builds normalized earnings bridges, analyzes expectation gaps,
and maintains capital-stack compatibility without ranking influence or execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

from alpha_velocity.expectations.models import (
    AdjustmentCategory,
    AdjustmentDetail,
    ConfidenceLevel,
    ExpectationGap,
    ExpectationSource,
    ExpectationsResearchResult,
    IndustryOutlook,
    MarketExpectation,
    NormalizedEarningsBridge,
    ReportedFacts,
    ResearchScenario,
    ReportingPeriod,
)


class ExpectationsResearchEngine:
    """
    Orchestrates expectations research: reported facts, market expectations, and scenarios.
    
    This engine:
    - Validates point-in-time data (rejects future information)
    - Supports normalized earnings bridges with documented adjustments
    - Compares reported vs market vs research expectations
    - Analyzes expectation gaps and catalysts
    - Maintains capital-stack compatibility
    - Makes NO ranking calls, order creation, or broker interaction
    - Defaults all influence parameters to zero
    """
    
    def __init__(self) -> None:
        pass
    
    def build_research(
        self,
        security_id: str,
        symbol: str,
        observation_time: datetime,
        forecast_horizon_end_year: int,
        reported_facts: ReportedFacts | None = None,
        consensus_expectation: MarketExpectation | None = None,
        management_guidance: MarketExpectation | None = None,
        industry_outlook: IndustryOutlook | None = None,
        research_scenarios: Sequence[ResearchScenario] | None = None,
        normalized_bridges: Sequence[NormalizedEarningsBridge] | None = None,
        capital_stack_commentary: str = "",
        capital_constraints: Sequence[str] | None = None,
        refinancing_dependencies: Sequence[str] | None = None,
        dilution_concerns: Sequence[str] | None = None,
        catalysts: Sequence[str] | None = None,
        invalidation_conditions: Sequence[str] | None = None,
    ) -> ExpectationsResearchResult:
        """
        Build complete expectations research output.
        
        Validates all point-in-time data, ensures no future information leaked,
        and returns result with zero ranking/allocation influence.
        """
        
        if observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        
        warnings: list[str] = []
        
        # Validate no future data
        if reported_facts:
            if reported_facts.available_at > observation_time:
                raise ValueError(f"Reported facts available_at {reported_facts.available_at} exceeds observation_time {observation_time}")
        
        if consensus_expectation:
            if consensus_expectation.available_at > observation_time:
                raise ValueError(f"Consensus expectation available_at exceeds observation_time")
            if consensus_expectation.as_of > observation_time:
                raise ValueError(f"Consensus estimate as_of date exceeds observation_time")
        
        if management_guidance:
            if management_guidance.available_at > observation_time:
                raise ValueError(f"Management guidance available_at exceeds observation_time")
            if management_guidance.as_of > observation_time:
                raise ValueError(f"Management guidance as_of date exceeds observation_time")
        
        if industry_outlook:
            if industry_outlook.available_at > observation_time:
                raise ValueError(f"Industry outlook available_at exceeds observation_time")
        
        scenarios = tuple(research_scenarios or [])
        for scenario in scenarios:
            if scenario.available_at > observation_time:
                raise ValueError(f"Research scenario available_at exceeds observation_time")
        
        bridges = tuple(normalized_bridges or [])
        for bridge in bridges:
            if bridge.available_at > observation_time:
                raise ValueError(f"Normalized bridge available_at exceeds observation_time")
        
        # Analyze expectation gaps
        gaps = self._analyze_gaps(
            reported_facts=reported_facts,
            consensus=consensus_expectation,
            guidance=management_guidance,
            scenarios=scenarios,
        )
        
        # Validate normalized bridges
        for bridge in bridges:
            self._validate_normalized_bridge(bridge, reported_facts, warnings)
        
        # Determine confidence
        confidence = self._assess_confidence(
            reported_facts=reported_facts,
            consensus=consensus_expectation,
            guidance=management_guidance,
            industry=industry_outlook,
            scenarios=scenarios,
            bridges=bridges,
            warnings=warnings,
        )
        
        # Build result
        return ExpectationsResearchResult(
            security_id=security_id,
            symbol=symbol,
            observation_time=observation_time,
            forecast_horizon_end_year=forecast_horizon_end_year,
            reported_facts_reference=reported_facts,
            consensus_reference=consensus_expectation,
            management_guidance_reference=management_guidance,
            industry_outlook_reference=industry_outlook,
            normalized_bridges=bridges,
            research_scenarios=scenarios,
            expectation_gaps=tuple(gaps),
            capital_stack_commentary=capital_stack_commentary,
            capital_constraints=tuple(capital_constraints or []),
            refinancing_dependencies=tuple(refinancing_dependencies or []),
            dilution_concerns=tuple(dilution_concerns or []),
            catalysts=tuple(catalysts or []),
            thesis_invalidation_conditions=tuple(invalidation_conditions or []),
            confidence_status=confidence,
            validation_status="VALIDATED" if all(b.validation_status == "VALIDATED" for b in bridges) else "UNVALIDATED",
            warnings=tuple(warnings),
            lineage={
                "has_reported_facts": reported_facts is not None,
                "has_consensus": consensus_expectation is not None,
                "has_management_guidance": management_guidance is not None,
                "has_industry_outlook": industry_outlook is not None,
                "scenario_count": len(scenarios),
                "bridge_count": len(bridges),
                "gap_count": len(gaps),
            },
            ranking_influence=0.0,  # ALWAYS zero
            allocation_influence=0.0,  # ALWAYS zero
        )
    
    def _analyze_gaps(
        self,
        reported_facts: ReportedFacts | None,
        consensus: MarketExpectation | None,
        guidance: MarketExpectation | None,
        scenarios: Sequence[ResearchScenario],
    ) -> list[ExpectationGap]:
        """Analyze gaps between different expectation layers."""
        gaps: list[ExpectationGap] = []
        
        # Consensus vs reported
        if reported_facts and consensus:
            for metric in ["revenue", "ebitda", "eps"]:
                rep_val = getattr(reported_facts, metric, None)
                con_val = getattr(consensus, metric, None)
                
                if rep_val is not None and con_val is not None:
                    direction = ""
                    if con_val > rep_val:
                        direction = "bullish"
                    elif con_val < rep_val:
                        direction = "bearish"
                    else:
                        direction = "neutral"
                    
                    gap = ExpectationGap(
                        gap_type="consensus_vs_reported",
                        metric=metric,
                        layer_1_value=rep_val,
                        layer_1_source="reported",
                        layer_2_value=con_val,
                        layer_2_source="consensus",
                        gap_direction=direction,
                        confidence=ConfidenceLevel.MODERATE,
                    )
                    gaps.append(gap)
        
        # Guidance vs consensus
        if consensus and guidance:
            for metric in ["revenue", "eps"]:
                con_val = getattr(consensus, metric, None)
                guid_val = getattr(guidance, metric, None)
                
                if con_val is not None and guid_val is not None:
                    direction = ""
                    if guid_val > con_val:
                        direction = "bullish"
                    elif guid_val < con_val:
                        direction = "bearish"
                    else:
                        direction = "neutral"
                    
                    gap = ExpectationGap(
                        gap_type="guidance_vs_consensus",
                        metric=metric,
                        layer_1_value=con_val,
                        layer_1_source="consensus",
                        layer_2_value=guid_val,
                        layer_2_source="guidance",
                        gap_direction=direction,
                        confidence=ConfidenceLevel.HIGH,
                    )
                    gaps.append(gap)
        
        return gaps
    
    def _validate_normalized_bridge(
        self,
        bridge: NormalizedEarningsBridge,
        reported_facts: ReportedFacts | None,
        warnings: list[str],
    ) -> None:
        """Validate normalized earnings bridge consistency."""
        
        if reported_facts is None:
            warnings.append(f"Normalized bridge for {bridge.fiscal_period} lacks reported facts reference")
            return
        
        # Check bridge calculation
        if bridge.reported_revenue != reported_facts.revenue:
            warnings.append(f"Bridge reported_revenue mismatch: {bridge.reported_revenue} vs {reported_facts.revenue}")
        
        if bridge.reported_ebitda and reported_facts.ebitda:
            if abs(bridge.reported_ebitda - reported_facts.ebitda) > 0.01 * reported_facts.ebitda:
                warnings.append(f"Bridge reported_ebitda mismatch: {bridge.reported_ebitda} vs {reported_facts.ebitda}")
        
        # Validate adjustment details
        for adj in bridge.adjustments:
            if adj.recurring and adj.category in [
                AdjustmentCategory.NONRECURRING_ITEM,
                AdjustmentCategory.IMPAIRMENT,
            ]:
                warnings.append(f"Adjustment {adj.category.value} marked recurring: {adj.rationale}")
            
            if adj.confidence == ConfidenceLevel.LOW:
                warnings.append(f"Low-confidence adjustment: {adj.category.value}, amount: {adj.amount}")
    
    def _assess_confidence(
        self,
        reported_facts: ReportedFacts | None,
        consensus: MarketExpectation | None,
        guidance: MarketExpectation | None,
        industry: IndustryOutlook | None,
        scenarios: Sequence[ResearchScenario],
        bridges: Sequence[NormalizedEarningsBridge],
        warnings: list[str],
    ) -> ConfidenceLevel:
        """Assess overall research confidence."""
        
        score = 0
        
        # Data completeness
        if reported_facts:
            score += 2
        if consensus:
            score += 1
        if guidance:
            score += 1
        if industry:
            score += 1
        
        # Scenario coverage
        if len(scenarios) >= 3:
            score += 2
        elif len(scenarios) >= 1:
            score += 1
        
        # Bridge validation
        validated_bridges = sum(1 for b in bridges if b.validation_status == "VALIDATED")
        if len(bridges) > 0:
            bridge_score = (validated_bridges / len(bridges)) * 2
            score += bridge_score
        
        # Warning penalty
        score -= min(len(warnings), 3)
        
        # Map to confidence level
        if score >= 8:
            return ConfidenceLevel.HIGH
        elif score >= 5:
            return ConfidenceLevel.MODERATE
        else:
            return ConfidenceLevel.LOW
    
    def build_normalized_bridge(
        self,
        security_id: str,
        observation_time: datetime,
        fiscal_year: int,
        fiscal_period: ReportingPeriod,
        reported_revenue: float,
        reported_ebitda: float,
        reported_ebit: float,
        reported_net_income: float,
        reported_eps: float,
        adjustments: Sequence[AdjustmentDetail] | None = None,
        methodology: str = "",
        reviewer: str = "",
    ) -> NormalizedEarningsBridge:
        """Build normalized earnings bridge with documented adjustments."""
        
        if observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        
        adjs = tuple(adjustments or [])
        
        # Recalculate normalized figures from adjustments
        normalized_revenue = reported_revenue
        normalized_ebitda = reported_ebitda
        normalized_ebit = reported_ebit
        normalized_net_income = reported_net_income
        normalized_eps = reported_eps
        
        for adj in adjs:
            # All adjustments add to EBITDA by default
            normalized_ebitda += adj.amount
            normalized_ebit += adj.amount
            # Net income adjustments are typically at net level
            if adj.category in [
                AdjustmentCategory.STOCK_BASED_COMP,
                AdjustmentCategory.RESTRUCTURING,
                AdjustmentCategory.NONRECURRING_ITEM,
            ]:
                normalized_net_income += adj.amount
        
        warnings: list[str] = []
        
        # Validate bridge logic
        for adj in adjs:
            if adj.available_at > observation_time:
                raise ValueError(f"Adjustment available_at {adj.available_at} exceeds observation_time")
            
            if adj.confidence == ConfidenceLevel.LOW:
                warnings.append(f"Low-confidence adjustment: {adj.category.value}")
        
        return NormalizedEarningsBridge(
            security_id=security_id,
            observation_time=observation_time,
            available_at=observation_time,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            reported_revenue=reported_revenue,
            reported_ebitda=reported_ebitda,
            reported_ebit=reported_ebit,
            reported_net_income=reported_net_income,
            reported_eps=reported_eps,
            adjustments=adjs,
            normalized_revenue=normalized_revenue,
            normalized_ebitda=normalized_ebitda,
            normalized_ebit=normalized_ebit,
            normalized_net_income=normalized_net_income,
            normalized_eps=normalized_eps,
            methodology=methodology,
            reviewer=reviewer,
            validation_status="VALIDATED" if len(warnings) == 0 else "UNVALIDATED",
            warnings=tuple(warnings),
        )
