"""Main opportunity ranking orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Mapping
from alpha_velocity.opportunity import Opportunity
from alpha_velocity.opportunity_ranking.models import RankingResult, RankingBatch, RankingState
from alpha_velocity.opportunity_ranking.scoring import (
    IntrinsicScorer,
    TimingScorer,
    SwingValueScorer,
    CapitalStructureScorer,
    LiquidityScorer,
    CatalystScorer,
    TechnicalScorer,
)


class OpportunityRanker:
    """
    Ranks opportunities by expected favorable swing value.
    
    Ranking Philosophy:
    - Highest expected swing value wins
    - Swing value = Probability × Magnitude × Time × Liquidity × (1 - Uncertainty)
    - Technical strength cannot override capital distress
    - Unvalidated evidence receives zero influence
    - Missing data is not treated as favorable
    """

    def __init__(self):
        """Initialize ranker with scorers."""
        self.intrinsic_scorer = IntrinsicScorer()
        self.timing_scorer = TimingScorer()
        self.swing_scorer = SwingValueScorer()
        self.capital_structure_scorer = CapitalStructureScorer()
        self.liquidity_scorer = LiquidityScorer()
        self.catalyst_scorer = CatalystScorer()
        self.technical_scorer = TechnicalScorer()

    def rank(
        self,
        opportunities: Sequence[Opportunity],
        universe_snapshot_id: str = "UNKNOWN",
        confidence_level: str = "RESEARCH",
    ) -> RankingBatch:
        """
        Rank a collection of opportunities.
        
        Args:
            opportunities: Canonical Opportunity objects to rank
            universe_snapshot_id: Snapshot identifier for batch traceability
            confidence_level: "RESEARCH", "PROVISIONAL", or "CONFIRMED"
            
        Returns:
            RankingBatch with ranked opportunities sorted by swing value
        """
        if not opportunities:
            return RankingBatch(
                universe_snapshot_id=universe_snapshot_id,
            observation_time=datetime.now(timezone.utc),
                confidence_level=confidence_level,
                notes="No opportunities to rank",
            )

        # Score each opportunity
        ranking_results = []
        for opp in opportunities:
            result = self._rank_single_opportunity(opp)
            ranking_results.append(result)

        # Sort by swing value (descending)
        ranking_results.sort(key=lambda r: r.expected_swing_value_score, reverse=True)

        # Assign rank and percentile
        ranked_with_position = []
        total = len(ranking_results)
        for idx, result in enumerate(ranking_results, start=1):
            percentile = (1.0 - (idx - 1) / max(1, total - 1)) * 100 if total > 1 else 100
            ranked_result = RankingResult(
                opportunity_id=result.opportunity_id,
                rank=idx,
                percentile=percentile,
                overall_research_score=result.overall_research_score,
                ranking_state=result.ranking_state,
                intrinsic_opportunity_score=result.intrinsic_opportunity_score,
                timing_opportunity_score=result.timing_opportunity_score,
                expected_swing_value_score=result.expected_swing_value_score,
                technical_score=result.technical_score,
                catalyst_score=result.catalyst_score,
                capital_structure_score=result.capital_structure_score,
                liquidity_score=result.liquidity_score,
                risk_adjustment=result.risk_adjustment,
                uncertainty_adjustment=result.uncertainty_adjustment,
                validation_status=result.validation_status,
                positive_contributors=result.positive_contributors,
                negative_contributors=result.negative_contributors,
                warnings=result.warnings,
                missing_information=result.missing_information,
                required_confirmation=result.required_confirmation,
                evidence_lineage=result.evidence_lineage,
            )
            ranked_with_position.append(ranked_result)

        return RankingBatch(
            universe_snapshot_id=universe_snapshot_id,
            observation_time=datetime.now(timezone.utc),
            ranked_opportunities=tuple(ranked_with_position),
            total_opportunities=total,
            confidence_level=confidence_level,
            notes=f"Ranked {total} opportunities by expected favorable swing value",
        )

    def _rank_single_opportunity(self, opp: Opportunity) -> RankingResult:
        """
        Rank a single opportunity across all dimensions.
        
        Returns:
            Intermediate ranking result with all components
        """
        # Score all components
        intrinsic_result = self.intrinsic_scorer.score(opp)
        timing_result = self.timing_scorer.score(opp)
        swing_result = self.swing_scorer.score(opp)
        capital_result = self.capital_structure_scorer.score(opp)
        liquidity_result = self.liquidity_scorer.score(opp)
        catalyst_result = self.catalyst_scorer.score(opp)
        technical_result = self.technical_scorer.score(opp)

        # Aggregate component scores
        intrinsic_score = intrinsic_result.score
        timing_score = timing_result.score
        swing_score = swing_result.score

        # Sub-component scores
        technical_score = technical_result.score
        catalyst_score = catalyst_result.score
        capital_structure_score = capital_result.score
        liquidity_score = liquidity_result.score

        # Calculate risk adjustment (capital structure health check)
        risk_adjustment = 100.0
        if capital_structure_score < 35:
            # Severe capital distress caps the ranking
            risk_adjustment = 100 - (1.0 - (capital_structure_score / 35)) * 50
            swing_score = min(swing_score, 40)  # Cap swing value if severe distress
        
        # Additional check for extreme downside risk
        if opp.expected_downside_pct is not None and abs(opp.expected_downside_pct) >= 40:
            risk_adjustment = min(risk_adjustment, 80)
            swing_score = min(swing_score, 45)

        # Calculate uncertainty adjustment
        uncertainty_adjustment = 100.0
        if opp.uncertainty_score is not None:
            uncertainty_adjustment = 100 - (opp.uncertainty_score * 100)

        # Determine validation status
        validation_status = "CALIBRATED"
        if opp.calibration_status != "CALIBRATED":
            validation_status = "UNCALIBRATED"
        if intrinsic_score == 50 and timing_score == 50 and swing_score == 50:
            validation_status = "INSUFFICIENT_DATA"

        # Aggregate all evidence
        positive_contributors = (
            tuple(intrinsic_result.contributors)
            + tuple(timing_result.contributors)
            + tuple(swing_result.contributors)
            + tuple(catalyst_result.contributors)
            + tuple(technical_result.contributors)
        )

        negative_contributors = (
            tuple(intrinsic_result.detractors)
            + tuple(timing_result.detractors)
            + tuple(swing_result.detractors)
            + tuple(capital_result.detractors)
            + tuple(technical_result.detractors)
        )

        warnings = (
            tuple(intrinsic_result.warnings)
            + tuple(timing_result.warnings)
            + tuple(swing_result.warnings)
            + tuple(liquidity_result.warnings)
        )

        missing_information = (
            tuple(intrinsic_result.missing)
            + tuple(timing_result.missing)
            + tuple(swing_result.missing)
        )

        # Determine required confirmations
        required_confirmation = []
        if opp.calibration_status != "CALIBRATED":
            required_confirmation.append("Probability calibration required before execution")
        if not opp.governance_eligible:
            required_confirmation.append("Governance approval required")
        if not opp.risk_eligible:
            required_confirmation.append("Risk approval required")

        # Calculate overall research score
        overall_score = (
            (intrinsic_score * 0.30)
            + (timing_score * 0.30)
            + (swing_score * 0.40)
        ) * (risk_adjustment / 100.0) * (uncertainty_adjustment / 100.0)
        overall_score = max(0, min(100, overall_score))

        # Determine ranking state
        ranking_state = self._determine_ranking_state(
            opp,
            intrinsic_score,
            timing_score,
            swing_score,
            capital_structure_score,
            overall_score,
        )

        # Build evidence lineage
        evidence_lineage = {
            "intrinsic": intrinsic_result.details,
            "timing": timing_result.details,
            "swing_value": swing_result.details,
            "capital_structure": capital_result.details,
            "liquidity": liquidity_result.details,
            "catalyst": catalyst_result.details,
            "technical": technical_result.details,
            "observation_time": opp.observation_time.isoformat(),
            "universe_snapshot_id": opp.universe_snapshot_id,
        }

        return RankingResult(
            opportunity_id=opp.opportunity_id,
            rank=0,  # Will be set during batch ranking
            percentile=0.0,  # Will be set during batch ranking
            overall_research_score=overall_score,
            ranking_state=ranking_state,
            intrinsic_opportunity_score=intrinsic_score,
            timing_opportunity_score=timing_score,
            expected_swing_value_score=swing_score,
            technical_score=technical_score,
            catalyst_score=catalyst_score,
            capital_structure_score=capital_structure_score,
            liquidity_score=liquidity_score,
            risk_adjustment=risk_adjustment,
            uncertainty_adjustment=uncertainty_adjustment,
            validation_status=validation_status,
            positive_contributors=positive_contributors,
            negative_contributors=negative_contributors,
            warnings=warnings,
            missing_information=missing_information,
            required_confirmation=tuple(required_confirmation),
            evidence_lineage=evidence_lineage,
        )

    def _determine_ranking_state(
        self,
        opp: Opportunity,
        intrinsic_score: float,
        timing_score: float,
        swing_score: float,
        capital_structure_score: float,
        overall_score: float,
    ) -> RankingState:
        """
        Classify opportunity into one of 8 ranking states.
        
        States represent research classifications, not trade signals:
        - HIGH_PRIORITY_TRIGGERED: Good opportunity, ready now
        - HIGH_PRIORITY_WAITING_FOR_TRIGGER: Good opportunity, await trigger
        - SPECULATIVE: High swing, higher risk
        - REFINANCING_DEPENDENT: Upside depends on refinancing success
        - DISTRESSED_OPTIONALITY: Poor capital, good near-term catalyst
        - WATCHLIST: Moderate interest
        - AVOID: Severe issues
        - INSUFFICIENT_DATA: Cannot classify
        """
        # Check for disqualifiers (AVOID state)
        if capital_structure_score <= 35 and swing_score < 50:
            return RankingState.AVOID
        if swing_score < 20:
            return RankingState.AVOID
        if opp.failed_breakout or opp.failed_breakdown:
            return RankingState.AVOID

        # Check for insufficient data
        if intrinsic_score == 50 and timing_score == 50 and swing_score == 50:
            return RankingState.INSUFFICIENT_DATA

        # Distressed optionality: poor capital but good timing/catalyst (highest priority for distress)
        if capital_structure_score <= 35 and timing_score >= 60:
            return RankingState.DISTRESSED_OPTIONALITY

        # Speculative: high swing but elevated risk
        if swing_score >= 75 and capital_structure_score < 50:
            return RankingState.SPECULATIVE

        # High priority triggered: good timing + good intrinsic + good swing
        if timing_score >= 60 and intrinsic_score >= 60 and swing_score >= 65:
            return RankingState.HIGH_PRIORITY_TRIGGERED

        # High priority waiting for trigger: good intrinsic + poor timing + good swing
        if intrinsic_score >= 60 and timing_score < 45 and swing_score >= 40:
            return RankingState.HIGH_PRIORITY_WAITING_FOR_TRIGGER

        # Refinancing dependent: moderate capital risk with decent swing
        if (
            capital_structure_score >= 30
            and capital_structure_score < 50
            and swing_score >= 60
        ):
            return RankingState.REFINANCING_DEPENDENT

        # Watchlist: moderate scores
        if 40 <= swing_score <= 65:
            return RankingState.WATCHLIST

        # Default to WATCHLIST for anything else with moderate interest
        return RankingState.WATCHLIST
