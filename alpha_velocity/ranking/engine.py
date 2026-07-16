"""
Opportunity ranking engine: intrinsic value + timing signals + expected swing value.

Ranks opportunities by expected favorable swing value over trading horizon.
Separate components ensure valuation cannot override poor timing, and technical
strength cannot erase severe capital distress.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from alpha_velocity.opportunity import Opportunity
from alpha_velocity.ranking.models import (
    DebtMaturityAnalysis,
    IntrinsicOpportunityInput,
    IntrinsicValuationScenario,
    MaturityCondition,
    RankedOpportunity,
    RankingRun,
    RankingState,
    ScoreComponentDetail,
    TimingOpportunityCatalyst,
)


@dataclass
class RankingConfig:
    """Configuration for three-component ranking."""
    # Weights sum to 1.0
    intrinsic_weight: float = 0.30
    timing_weight: float = 0.30
    swing_value_weight: float = 0.40
    
    # Hard penalties and caps
    high_distress_cap: float = 30.0
    poor_timing_penalty: float = 25.0
    uncalibrated_probability_penalty: float = 20.0
    
    # Technical/timing thresholds
    min_timing_for_triggered: float = 50.0
    max_timing_for_waiting: float = 45.0
    
    # Intrinsic thresholds
    min_intrinsic_for_high_priority: float = 60.0
    
    def __post_init__(self) -> None:
        total = self.intrinsic_weight + self.timing_weight + self.swing_value_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


class RankingEngine:
    """Rank opportunities by expected favorable swing value."""
    
    def __init__(self, config: RankingConfig | None = None) -> None:
        self.config = config or RankingConfig()
    
    def rank_opportunities(
        self,
        opportunities: Sequence[Opportunity],
        universe_snapshot_id: str,
        observation_time: datetime,
        intrinsic_inputs: dict[str, IntrinsicOpportunityInput] | None = None,
        intrinsic_scenarios: dict[str, Sequence[IntrinsicValuationScenario]] | None = None,
        maturity_analysis: dict[str, DebtMaturityAnalysis] | None = None,
        catalysts: dict[str, Sequence[TimingOpportunityCatalyst]] | None = None,
    ) -> RankingRun:
        """
        Rank opportunities by expected swing value.
        
        Returns RankingRun with three-component scores and evidence.
        """
        if observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        
        ranked_list: list[RankedOpportunity] = []
        
        for opp in opportunities:
            if opp.observation_time != observation_time:
                continue
            
            ranked_opp = self._rank_single_opportunity(
                opp=opp,
                intrinsic_input=intrinsic_inputs.get(opp.opportunity_id) if intrinsic_inputs else None,
                intrinsic_scenarios=intrinsic_scenarios.get(opp.opportunity_id) if intrinsic_scenarios else None,
                maturity=maturity_analysis.get(opp.opportunity_id) if maturity_analysis else None,
                catalysts_list=catalysts.get(opp.opportunity_id) if catalysts else None,
            )
            ranked_list.append(ranked_opp)
        
        # Sort by swing value rank descending
        ranked_list.sort(key=lambda x: x.overall_swing_value_rank, reverse=True)
        
        # Assign ranks and percentiles
        total_ranked = len(ranked_list)
        final_list: list[RankedOpportunity] = []
        for idx, ranked_opp in enumerate(ranked_list):
            percentile = 100.0 * (1.0 - (idx / max(total_ranked, 1)))
            updated = RankedOpportunity(
                opportunity_id=ranked_opp.opportunity_id,
                rank=idx + 1,
                percentile=percentile,
                intrinsic_opportunity_score=ranked_opp.intrinsic_opportunity_score,
                timing_opportunity_score=ranked_opp.timing_opportunity_score,
                expected_swing_value_score=ranked_opp.expected_swing_value_score,
                overall_swing_value_rank=ranked_opp.overall_swing_value_rank,
                intrinsic_components=ranked_opp.intrinsic_components,
                timing_components=ranked_opp.timing_components,
                swing_value_components=ranked_opp.swing_value_components,
                ranking_state=ranked_opp.ranking_state,
                validation_status=ranked_opp.validation_status,
                calibration_status=ranked_opp.calibration_status,
                positive_contributors=ranked_opp.positive_contributors,
                negative_contributors=ranked_opp.negative_contributors,
                disqualifiers=ranked_opp.disqualifiers,
                warnings=ranked_opp.warnings,
                evidence_lineage=ranked_opp.evidence_lineage,
            )
            final_list.append(updated)
        
        # Create run
        ranking_run_id = str(uuid.uuid4())
        run = RankingRun(
            ranking_run_id=ranking_run_id,
            observation_time=observation_time,
            universe_snapshot_id=universe_snapshot_id,
            ranked_opportunities=tuple(final_list),
            intrinsic_weight=self.config.intrinsic_weight,
            timing_weight=self.config.timing_weight,
            swing_value_weight=self.config.swing_value_weight,
            total_opportunities_analyzed=len(opportunities),
            opportunities_ranked=len(final_list),
        )
        
        return run
    
    def _rank_single_opportunity(
        self,
        opp: Opportunity,
        intrinsic_input: IntrinsicOpportunityInput | None = None,
        intrinsic_scenarios: Sequence[IntrinsicValuationScenario] | None = None,
        maturity: DebtMaturityAnalysis | None = None,
        catalysts_list: Sequence[TimingOpportunityCatalyst] | None = None,
    ) -> RankedOpportunity:
        """Rank single opportunity with three components."""
        
        positive_contrib: list[str] = []
        negative_contrib: list[str] = []
        disqualifiers: list[str] = []
        warnings: list[str] = []
        evidence: dict[str, Any] = {}
        
        # Component 1: Intrinsic Opportunity Score
        intrinsic_score, intrinsic_comps = self._score_intrinsic_opportunity(
            intrinsic_input=intrinsic_input,
            scenarios=intrinsic_scenarios,
            maturity=maturity,
            warnings=warnings,
            disqualifiers=disqualifiers,
        )
        if intrinsic_score < 20.0:
            negative_contrib.append("Severe capital structure or valuation risk")
        elif intrinsic_score > 70.0:
            positive_contrib.append("Attractive intrinsic opportunity")
        
        # Component 2: Timing Opportunity Score
        timing_score, timing_comps = self._score_timing_opportunity(
            opp=opp,
            catalysts_list=catalysts_list,
            warnings=warnings,
        )
        if timing_score > 70.0:
            positive_contrib.append("Strong timing: validated trigger or catalyst")
        elif timing_score < 30.0:
            negative_contrib.append("Poor timing: no clear trigger or catalyst")
        
        # Component 3: Expected Swing Value Score
        swing_score, swing_comps = self._score_expected_swing_value(
            opp=opp,
            intrinsic_score=intrinsic_score,
            timing_score=timing_score,
            has_distress=intrinsic_score < 20.0,
            warnings=warnings,
        )
        
        # Calculate overall swing value rank
        overall_swing = (
            (intrinsic_score * self.config.intrinsic_weight)
            + (timing_score * self.config.timing_weight)
            + (swing_score * self.config.swing_value_weight)
        )
        
        # Apply hard caps and penalties
        if intrinsic_score < 20.0:  # Severe distress
            overall_swing = min(overall_swing, self.config.high_distress_cap)
            disqualifiers.append("Severe capital structure distress precludes high swing ranking")
        
        if timing_score < 20.0 and intrinsic_score > 60.0:  # Mispriced but no trigger
            overall_swing = max(0.0, overall_swing - self.config.poor_timing_penalty)
            negative_contrib.append("Poor timing limits actionability despite attractive valuation")
        
        if opp.calibration_status == "UNCALIBRATED" and not opp.probability_estimate:
            overall_swing = max(0.0, overall_swing - self.config.uncalibrated_probability_penalty)
            disqualifiers.append("Unvalidated probability estimate reduces swing value confidence")
        
        overall_swing = max(0.0, min(100.0, overall_swing))
        
        # Determine ranking state
        ranking_state = self._determine_ranking_state(
            intrinsic_score=intrinsic_score,
            timing_score=timing_score,
            swing_score=swing_score,
            opp=opp,
            maturity=maturity,
            disqualifiers=disqualifiers,
        )
        
        # Build evidence lineage
        evidence = {
            "intrinsic_input_available": intrinsic_input is not None,
            "scenarios_provided": intrinsic_scenarios is not None and len(intrinsic_scenarios) > 0,
            "maturity_analysis_available": maturity is not None,
            "catalysts_available": catalysts_list is not None and len(catalysts_list) > 0,
            "technical_data": {
                "weekly_trend": opp.weekly_trend_state,
                "daily_trend": opp.daily_trend_state,
                "alignment": opp.multi_timeframe_alignment,
                "trigger_state": opp.trigger_state,
            },
            "probability_calibrated": opp.calibration_status == "CALIBRATED",
        }
        
        return RankedOpportunity(
            opportunity_id=opp.opportunity_id,
            rank=0,  # Will be assigned
            percentile=0.0,
            intrinsic_opportunity_score=intrinsic_score,
            timing_opportunity_score=timing_score,
            expected_swing_value_score=swing_score,
            overall_swing_value_rank=overall_swing,
            intrinsic_components=intrinsic_comps,
            timing_components=timing_comps,
            swing_value_components=swing_comps,
            ranking_state=ranking_state,
            validation_status="VALIDATED" if (intrinsic_input and maturity) else "INCOMPLETE",
            calibration_status=opp.calibration_status,
            positive_contributors=tuple(positive_contrib),
            negative_contributors=tuple(negative_contrib),
            disqualifiers=tuple(disqualifiers),
            warnings=tuple(warnings),
            evidence_lineage=evidence,
        )
    
    def _score_intrinsic_opportunity(
        self,
        intrinsic_input: IntrinsicOpportunityInput | None,
        scenarios: Sequence[IntrinsicValuationScenario] | None,
        maturity: DebtMaturityAnalysis | None,
        warnings: list[str],
        disqualifiers: list[str],
    ) -> tuple[float, tuple[ScoreComponentDetail, ...]]:
        """Score 1: Intrinsic opportunity (valuation + capital structure + maturity)."""
        
        components: list[ScoreComponentDetail] = []
        score = 50.0  # Neutral default
        
        # Valuation component
        if intrinsic_input and scenarios and len(scenarios) > 0:
            base_scenario = next((s for s in scenarios if s.scenario == "base"), scenarios[0])
            if base_scenario and intrinsic_input.market_price and intrinsic_input.market_price > 0:
                upside = base_scenario.upside_from_market(intrinsic_input.market_price)
                if upside is not None:
                    val_score = min(100.0, max(0.0, 50.0 + upside / 10.0))
                    components.append(ScoreComponentDetail(
                        name="valuation_analysis",
                        score=val_score,
                        weight=0.5,
                        contribution=val_score * 0.5,
                        is_validated=True,
                        data_available=True,
                        explanation=f"Base scenario: {upside:+.1f}% from market, ${base_scenario.value_per_share:.2f}/share vs ${intrinsic_input.market_price:.2f}",
                    ))
                    score = score * 0.5 + val_score * 0.5
            else:
                warnings.append("Valuation analysis incomplete: missing market price or scenarios")
        else:
            warnings.append("No intrinsic input or valuation scenarios provided")
        
        # Maturity/capital structure component
        if maturity:
            mat_scores = {
                MaturityCondition.WELL_FUNDED: 95.0,
                MaturityCondition.MANAGEABLE: 80.0,
                MaturityCondition.REFINANCING_REQUIRED: 50.0,
                MaturityCondition.HIGH_RISK: 25.0,
                MaturityCondition.DISTRESSED: 5.0,
                MaturityCondition.INSUFFICIENT_DATA: 50.0,
            }
            mat_score = mat_scores.get(maturity.maturity_condition, 50.0)
            
            components.append(ScoreComponentDetail(
                name="maturity_and_capital_structure",
                score=mat_score,
                weight=0.5,
                contribution=mat_score * 0.5,
                is_validated=True,
                data_available=True,
                explanation=f"Maturity condition: {maturity.maturity_condition.value}, runway: {maturity.estimated_liquidity_runway_days} days",
            ))
            
            score = score * 0.5 + mat_score * 0.5
            
            if maturity.maturity_condition == MaturityCondition.DISTRESSED:
                disqualifiers.append("Distressed maturity condition")
        else:
            components.append(ScoreComponentDetail(
                name="maturity_and_capital_structure",
                score=50.0,
                weight=0.5,
                contribution=25.0,
                is_validated=False,
                data_available=False,
                explanation="No maturity analysis provided",
            ))
            warnings.append("No maturity analysis provided - treating as unknown risk")
        
        return max(0.0, min(100.0, score)), tuple(components)
    
    def _score_timing_opportunity(
        self,
        opp: Opportunity,
        catalysts_list: Sequence[TimingOpportunityCatalyst] | None,
        warnings: list[str],
    ) -> tuple[float, tuple[ScoreComponentDetail, ...]]:
        """Score 2: Timing opportunity (technical setup + catalysts)."""
        
        components: list[ScoreComponentDetail] = []
        score = 50.0
        
        # Technical trigger component
        tech_score = 50.0
        tech_explanation = "No clear technical trigger"
        
        if opp.trigger_state in ["triggered", "confirmed"]:
            tech_score = 80.0
            tech_explanation = f"Strong trigger: {opp.trigger_state}"
        elif opp.trigger_state in ["forming", "watch"]:
            tech_score = 60.0
            tech_explanation = f"Forming trigger: {opp.trigger_state}"
        else:
            tech_score = 35.0
            tech_explanation = f"No trigger: {opp.trigger_state}"
        
        if opp.failed_breakout:
            tech_score -= 20.0
            tech_explanation += " (failed breakout risk)"
        
        components.append(ScoreComponentDetail(
            name="technical_trigger",
            score=tech_score,
            weight=0.4,
            contribution=tech_score * 0.4,
            is_validated=True,
            data_available=True,
            explanation=tech_explanation,
        ))
        
        # Multi-timeframe alignment component
        alignment_score = 50.0
        alignment_explanation = "No clear alignment"
        
        if opp.multi_timeframe_alignment == "ALIGNED":
            alignment_score = 85.0
            alignment_explanation = "Strong: weekly and daily aligned"
        elif opp.multi_timeframe_alignment == "FORMING":
            alignment_score = 65.0
            alignment_explanation = "Forming: weekly and daily convergence"
        else:
            alignment_score = 30.0
            alignment_explanation = "Divergent: weekly and daily conflict"
        
        components.append(ScoreComponentDetail(
            name="multiframe_alignment",
            score=alignment_score,
            weight=0.4,
            contribution=alignment_score * 0.4,
            is_validated=True,
            data_available=True,
            explanation=alignment_explanation,
        ))
        
        # Catalyst component
        catalyst_score = 50.0
        catalyst_explanation = "No known catalysts"
        
        if opp.known_catalysts and len(opp.known_catalysts) > 0:
            catalyst_score += 15.0
            catalyst_explanation = f"{len(opp.known_catalysts)} known catalyst(s)"
        
        if catalysts_list and len(catalysts_list) > 0:
            high_importance = sum(1 for c in catalysts_list if c.estimated_importance in ["high", "transformational"])
            if high_importance > 0:
                catalyst_score += min(20.0, high_importance * 10.0)
                catalyst_explanation = f"{high_importance} high-importance catalyst(s)"
        
        if opp.catalyst_risk == "high":
            catalyst_score -= 15.0
        
        components.append(ScoreComponentDetail(
            name="catalysts",
            score=min(100.0, max(0.0, catalyst_score)),
            weight=0.2,
            contribution=min(100.0, max(0.0, catalyst_score)) * 0.2,
            is_validated=catalysts_list is not None,
            data_available=catalysts_list is not None or len(opp.known_catalysts) > 0,
            explanation=catalyst_explanation,
        ))
        
        score = (tech_score * 0.4 + alignment_score * 0.4 + min(100.0, max(0.0, catalyst_score)) * 0.2)
        
        return max(0.0, min(100.0, score)), tuple(components)
    
    def _score_expected_swing_value(
        self,
        opp: Opportunity,
        intrinsic_score: float,
        timing_score: float,
        has_distress: bool,
        warnings: list[str],
    ) -> tuple[float, tuple[ScoreComponentDetail, ...]]:
        """Score 3: Expected swing value (probability, magnitude, costs, liquidity, uncertainty)."""
        
        components: list[ScoreComponentDetail] = []
        score = 50.0
        
        # Probability component (calibrated only)
        if opp.calibration_status == "CALIBRATED" and opp.probability_estimate is not None:
            prob = min(1.0, max(0.0, opp.probability_estimate))
            prob_score = prob * 100.0
            components.append(ScoreComponentDetail(
                name="favorable_probability",
                score=prob_score,
                weight=0.3,
                contribution=prob_score * 0.3,
                is_validated=True,
                data_available=True,
                explanation=f"Calibrated probability: {prob:.1%}",
            ))
        else:
            components.append(ScoreComponentDetail(
                name="favorable_probability",
                score=0.0,  # Unvalidated = zero influence
                weight=0.3,
                contribution=0.0,
                is_validated=False,
                data_available=False,
                explanation="Uncalibrated - probability not fabricated",
            ))
            warnings.append("Probability estimate not calibrated - swing value based on alternative inputs only")
        
        # Expected magnitude component
        if opp.expected_upside_pct is not None and opp.expected_upside_pct > 0:
            magnitude_score = min(100.0, 50.0 + (opp.expected_upside_pct / 10.0))
            components.append(ScoreComponentDetail(
                name="expected_magnitude",
                score=magnitude_score,
                weight=0.25,
                contribution=magnitude_score * 0.25,
                is_validated=True,
                data_available=True,
                explanation=f"Expected upside: {opp.expected_upside_pct:.1f}%",
            ))
        else:
            components.append(ScoreComponentDetail(
                name="expected_magnitude",
                score=50.0,
                weight=0.25,
                contribution=12.5,
                is_validated=False,
                data_available=False,
                explanation="Expected magnitude unavailable",
            ))
        
        # Holding period and costs component
        holding_score = 60.0
        holding_explanation = "Holding period data unavailable"
        
        if opp.expected_holding_days is not None and opp.expected_holding_days > 0:
            # Favor 5-20 day holding periods (swing trades)
            if 5 <= opp.expected_holding_days <= 20:
                holding_score = 85.0
                holding_explanation = f"Optimal swing horizon: {opp.expected_holding_days:.0f} days"
            elif opp.expected_holding_days < 5:
                holding_score = 60.0
                holding_explanation = f"Short holding: {opp.expected_holding_days:.0f} days (scalp risk)"
            else:
                holding_score = 50.0
                holding_explanation = f"Extended holding: {opp.expected_holding_days:.0f} days"
        
        # Adjust for costs
        if opp.estimated_cost_bps is not None and opp.estimated_cost_bps > 0:
            cost_pct = opp.estimated_cost_bps / 100.0
            if opp.expected_upside_pct and opp.expected_upside_pct > 0:
                net_upside = opp.expected_upside_pct - cost_pct
                if net_upside < 0:
                    holding_score *= 0.5
                    holding_explanation += f" (costs {cost_pct:.2f}% erode upside)"
        
        components.append(ScoreComponentDetail(
            name="holding_period_and_costs",
            score=holding_score,
            weight=0.25,
            contribution=holding_score * 0.25,
            is_validated=opp.expected_holding_days is not None,
            data_available=opp.expected_holding_days is not None,
            explanation=holding_explanation,
        ))
        
        # Liquidity and execution component
        liquidity_score = 50.0
        if opp.average_daily_dollar_volume and opp.average_daily_dollar_volume > 10_000_000:
            liquidity_score = 85.0
        elif opp.average_daily_dollar_volume and opp.average_daily_dollar_volume > 1_000_000:
            liquidity_score = 65.0
        elif opp.average_daily_dollar_volume and opp.average_daily_dollar_volume > 100_000:
            liquidity_score = 40.0
        else:
            liquidity_score = 20.0
        
        if opp.capacity_warning:
            liquidity_score -= 20.0
        
        components.append(ScoreComponentDetail(
            name="liquidity_and_execution",
            score=max(0.0, liquidity_score),
            weight=0.15,
            contribution=max(0.0, liquidity_score) * 0.15,
            is_validated=True,
            data_available=True,
            explanation=f"ADVI: ${opp.average_daily_dollar_volume:,.0f}, spread: {opp.spread_estimate_bps:.1f}bps",
        ))
        
        # Uncertainty component
        uncertainty_score = 100.0 - (opp.uncertainty_score * 100.0)
        components.append(ScoreComponentDetail(
            name="uncertainty_and_confidence",
            score=uncertainty_score,
            weight=0.05,
            contribution=uncertainty_score * 0.05,
            is_validated=True,
            data_available=True,
            explanation=f"Uncertainty: {opp.uncertainty_score:.1%}",
        ))
        
        # Calculate composite swing value score
        score = sum(c.contribution for c in components)
        score = max(0.0, min(100.0, score))
        
        # Technical strength cannot override capital distress
        if has_distress:
            score = min(score, 40.0)
        
        return score, tuple(components)
    
    def _determine_ranking_state(
        self,
        intrinsic_score: float,
        timing_score: float,
        swing_score: float,
        opp: Opportunity,
        maturity: DebtMaturityAnalysis | None,
        disqualifiers: list[str],
    ) -> RankingState:
        """Determine research classification state."""
        
        # AVOID - severe issues (but not just uncalibrated probability)
        severe_disqualifiers = [d for d in disqualifiers if "Unvalidated probability" not in d]
        if len(severe_disqualifiers) > 0 or swing_score < 20.0:
            return RankingState.AVOID
        
        # INSUFFICIENT_DATA - cannot classify
        if swing_score == 50.0 and intrinsic_score == 50.0 and timing_score == 50.0:
            return RankingState.INSUFFICIENT_DATA
        
        # DISTRESSED_OPTIONALITY - bad capital structure, good timing
        if intrinsic_score < 30.0 and timing_score > 70.0:
            return RankingState.DISTRESSED_OPTIONALITY
        
        # REFINANCING_DEPENDENT - good upside but dependent on refinancing
        if maturity and maturity.maturity_condition == MaturityCondition.REFINANCING_REQUIRED:
            if swing_score > 60.0:
                return RankingState.REFINANCING_DEPENDENT
        
        # HIGH_PRIORITY_TRIGGERED - good timing, good intrinsic, good swing value
        if timing_score >= self.config.min_timing_for_triggered:
            if intrinsic_score >= self.config.min_intrinsic_for_high_priority:
                if swing_score > 65.0:
                    return RankingState.HIGH_PRIORITY_TRIGGERED
        
        # HIGH_PRIORITY_WAITING_FOR_TRIGGER - good intrinsic, poor timing, good swing value
        if timing_score < self.config.max_timing_for_waiting:
            if intrinsic_score >= self.config.min_intrinsic_for_high_priority:
                if swing_score > 40.0:  # Lower threshold: swing may be limited by incomplete data
                    return RankingState.HIGH_PRIORITY_WAITING_FOR_TRIGGER
        
        # SPECULATIVE - high swing value but elevated risk
        if swing_score > 75.0:
            return RankingState.SPECULATIVE
        
        # WATCHLIST - moderate interest
        if 40.0 <= swing_score <= 65.0:
            return RankingState.WATCHLIST
        
        return RankingState.WATCHLIST
