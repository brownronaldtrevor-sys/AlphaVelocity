"""Marketplace classifier - assign opportunities to queues and discovery lenses."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from alpha_velocity.opportunity import Opportunity

from .models import (
    DiscoveryLens,
    DiscoveryLensType,
    LiquidityTier,
    MarketplaceQueue,
    HorizonAssessment,
    OpportunityCandidateClassification,
    StructuredThesis,
)


class MarketplaceClassifier:
    """Classify opportunities into marketplace queues and discovery lenses."""

    def classify(
        self,
        opportunity: Opportunity,
        observation_time: datetime | None = None,
    ) -> OpportunityCandidateClassification:
        """Classify a single opportunity.

        Args:
            opportunity: Opportunity object from ranking engine
            observation_time: Point-in-time reference (defaults to opportunity.observation_time)

        Returns:
            OpportunityCandidateClassification with queues and lenses
        """
        if observation_time is None:
            observation_time = opportunity.observation_time

        # Determine discovery lenses
        lenses = self._identify_lenses(opportunity)

        # Determine marketplace queues
        queues = self._classify_queues(opportunity, lenses)

        # Determine liquidity tier
        liquidity_tier = self._classify_liquidity_tier(opportunity)

        # Determine actionability and research qualification
        is_actionable = self._is_actionable(opportunity, queues)
        research_qualified = bool(lenses) or any(
            queue in queues
            for queue in (
                MarketplaceQueue.ASYMMETRIC_VALUE_RESEARCH,
                MarketplaceQueue.CHART_MOMENTUM_RESEARCH,
                MarketplaceQueue.TOP_DOWN_INDUSTRY_RESEARCH,
                MarketplaceQueue.EVENT_ACTIVIST_RESEARCH,
                MarketplaceQueue.SPECIAL_SITUATION,
                MarketplaceQueue.HUMAN_HYPOTHESIS,
                MarketplaceQueue.RESEARCH_ONLY,
            )
        )

        # Build basic thesis (can be overridden by human hypothesis later)
        thesis = self._build_basic_thesis(opportunity, lenses, observation_time)

        # Determine if excluded
        is_excluded = MarketplaceQueue.EXCLUDED in queues
        exclusion_reason = self._get_exclusion_reason(opportunity) if is_excluded else ""

        # Check for micro-cap warnings
        warnings = self._check_microcap_warnings(opportunity)

        # Calculate research and attractiveness confidence
        research_confidence = self._calculate_research_confidence(lenses, opportunity)
        opportunity_attractiveness = self._calculate_opportunity_attractiveness(
            opportunity=opportunity,
            lenses=lenses,
            research_confidence=research_confidence,
        )

        pattern_family, pattern_provenance = self._identify_pattern_family(opportunity)

        research_horizon, primary_horizon, tactical_horizon, execution_horizon = self._build_horizon_assessments(
            opportunity=opportunity,
            lenses=lenses,
            research_confidence=research_confidence,
            opportunity_attractiveness=opportunity_attractiveness,
            is_actionable=is_actionable,
            pattern_family=pattern_family,
        )

        # Top Five eligibility
        top_five_eligible = is_actionable or research_qualified or any(
            q in queues
            for q in [
                MarketplaceQueue.STARTER_POSITION_CANDIDATE,
                MarketplaceQueue.NEAR_TRIGGER,
                MarketplaceQueue.RESEARCH_ONLY,
            ]
        )

        return OpportunityCandidateClassification(
            opportunity_id=opportunity.opportunity_id,
            security_id=opportunity.security_id,
            symbol=opportunity.symbol,
            observation_time=observation_time,
            marketplace_queues=queues,
            discovery_lenses=lenses,
            structured_thesis=thesis,
            liquidity_tier=liquidity_tier,
            research_confidence=research_confidence,
            opportunity_attractiveness=opportunity_attractiveness,
            is_actionable=is_actionable,
            execution_eligible=is_actionable,
            research_qualified=research_qualified,
            is_excluded=is_excluded,
            exclusion_reason=exclusion_reason,
            microcap_warnings=warnings,
            top_five_eligible=top_five_eligible,
            pattern_family=pattern_family,
            pattern_provenance=pattern_provenance,
            research_horizon=research_horizon,
            primary_repricing_horizon=primary_horizon,
            tactical_swing_horizon=tactical_horizon,
            execution_horizon=execution_horizon,
        )

    def _identify_lenses(self, opportunity: Opportunity) -> tuple[DiscoveryLens, ...]:
        """Identify which discovery lenses found this opportunity."""
        lenses: list[DiscoveryLens] = []

        trigger_state = str(opportunity.trigger_state).upper()
        weekly_trend = str(opportunity.weekly_trend_state).upper()
        daily_trend = str(opportunity.daily_trend_state).upper()
        setup_type = str(opportunity.setup_type).upper()

        # CHART_AND_RECOGNITION lens
        if self._passes_chart_lens(opportunity):
            lenses.append(
                DiscoveryLens(
                    lens_type=DiscoveryLensType.CHART_AND_RECOGNITION,
                    discovery_score=self._score_chart_setup(opportunity),
                    evidence_summary=f"{setup_type} setup, {weekly_trend} weekly trend, "
                    f"trigger_state={trigger_state}, relative_volume={opportunity.relative_volume:.2f}",
                )
            )

        # ASYMMETRIC_EQUITY lens (proxy: check for expected value potential)
        if opportunity.expected_upside_pct is not None and opportunity.expected_upside_pct >= 20.0:
            lenses.append(
                DiscoveryLens(
                    lens_type=DiscoveryLensType.ASYMMETRIC_EQUITY,
                    discovery_score=min(100.0, 30.0 + opportunity.expected_upside_pct),
                    evidence_summary=f"Asymmetric upside potential: {opportunity.expected_upside_pct:.1f}% expected move "
                    f"vs {self._format_optional_pct(opportunity.expected_downside_pct)} downside",
                )
            )

        # TOP_DOWN_MARKET_AND_INDUSTRY lens
        if str(opportunity.sector_regime).upper() in ["ESTABLISHED_LEADER", "EARLY_LEADERSHIP", "EMERGING_INFLECTION"]:
            lenses.append(
                DiscoveryLens(
                    lens_type=DiscoveryLensType.TOP_DOWN_MARKET_AND_INDUSTRY,
                    discovery_score=75.0,
                    evidence_summary=f"Sector leading: {opportunity.sector_regime}, market_regime={opportunity.market_regime}",
                )
            )

        if weekly_trend == "UPTREND" and daily_trend == "UPTREND" and opportunity.relative_volume >= 1.1:
            lenses.append(
                DiscoveryLens(
                    lens_type=DiscoveryLensType.MANAGEMENT_LANGUAGE_CHANGE,
                    discovery_score=55.0,
                    evidence_summary=(
                        f"Constructive momentum with {opportunity.relative_volume:.2f}x relative volume and "
                        f"{opportunity.close_quality:.2f} close quality"
                    ),
                )
            )

        if "TURTLE" in setup_type or (weekly_trend == "UPTREND" and opportunity.volatility_contraction > 0.15):
            lenses.append(
                DiscoveryLens(
                    lens_type=DiscoveryLensType.TURTLE_TREND_RESEARCH_LENS,
                    discovery_score=60.0,
                    evidence_summary=(
                        f"Trend persistence with volatility contraction={opportunity.volatility_contraction:.2f}, "
                        f"breakout_distance={opportunity.breakout_distance_pct:.2f}"
                    ),
                )
            )

        # SURVIVABILITY_AND_CAPITAL_STACK lens (proxy: no liquidation risk warning)
        if not any("liquidation" in w.lower() for w in opportunity.warnings) and opportunity.average_daily_dollar_volume > 0:
            lenses.append(
                DiscoveryLens(
                    lens_type=DiscoveryLensType.SURVIVABILITY_AND_CAPITAL_STACK,
                    discovery_score=70.0,
                    evidence_summary="No immediate survivability concerns detected",
                )
            )

        # EXPECTATIONS_AND_REVISIONS lens (proxy: check calibration)
        if str(opportunity.calibration_status).upper() == "CALIBRATED" or opportunity.probability_estimate is not None:
            lenses.append(
                DiscoveryLens(
                    lens_type=DiscoveryLensType.EXPECTATIONS_AND_REVISIONS,
                    discovery_score=80.0 if str(opportunity.calibration_status).upper() == "CALIBRATED" else 65.0,
                    evidence_summary="Calibrated probability estimate available"
                    if str(opportunity.calibration_status).upper() == "CALIBRATED"
                    else "Probability estimate available for structured review",
                )
            )

        # CORPORATE_EVENT_AND_ACTIVIST lens (proxy: check catalysts)
        if opportunity.known_catalysts and len(opportunity.known_catalysts) > 0:
            lenses.append(
                DiscoveryLens(
                    lens_type=DiscoveryLensType.CORPORATE_EVENT_AND_ACTIVIST,
                    discovery_score=65.0,
                    evidence_summary=f"{len(opportunity.known_catalysts)} known catalyst(s) identified",
                )
            )

        return tuple(lenses)

    def _passes_chart_lens(self, opportunity: Opportunity) -> bool:
        """Check if opportunity passes chart and recognition lens."""
        trigger_state = str(opportunity.trigger_state).upper()
        weekly_trend = str(opportunity.weekly_trend_state).upper()
        daily_trend = str(opportunity.daily_trend_state).upper()
        return (
            trigger_state == "TRIGGERED"
            or (weekly_trend == "UPTREND" and daily_trend == "UPTREND")
            or opportunity.failed_breakout
            or opportunity.failed_breakdown
            or opportunity.breakout_distance_pct > 0.0
        )

    def _score_chart_setup(self, opportunity: Opportunity) -> float:
        """Score chart setup quality (0-100)."""
        score = 50.0
        if str(opportunity.trigger_state).upper() == "TRIGGERED":
            score += 30.0
        if opportunity.multi_timeframe_alignment == "ALIGNED":
            score += 20.0
        if opportunity.relative_volume > 1.0:
            score += 10.0
        if opportunity.breakout_distance_pct > 0.0:
            score += min(10.0, opportunity.breakout_distance_pct * 2.0)
        return min(100.0, score)

    def _classify_queues(
        self,
        opportunity: Opportunity,
        lenses: tuple[DiscoveryLens, ...],
    ) -> tuple[MarketplaceQueue, ...]:
        """Classify opportunity into marketplace queues."""
        queues: list[MarketplaceQueue] = []
        trigger_state = str(opportunity.trigger_state).upper()
        weekly_trend = str(opportunity.weekly_trend_state).upper()
        daily_trend = str(opportunity.daily_trend_state).upper()
        setup_type = str(opportunity.setup_type).upper()
        calibration_status = str(opportunity.calibration_status).upper()

        # Hard exclusions first
        if self._is_hard_excluded(opportunity):
            queues.append(MarketplaceQueue.EXCLUDED)
            return tuple(queues)

        # ACTIONABLE_TRIGGERED
        if (
            trigger_state == "TRIGGERED"
            and calibration_status == "CALIBRATED"
            and opportunity.risk_eligible
            and opportunity.governance_eligible
            and not opportunity.model_disagreement
        ):
            queues.append(MarketplaceQueue.ACTIONABLE_TRIGGERED)
        # STARTER_POSITION_CANDIDATE
        elif (
            trigger_state == "TRIGGERED"
            and opportunity.risk_eligible
            and opportunity.governance_eligible
            and not opportunity.model_disagreement
        ):
            queues.append(MarketplaceQueue.STARTER_POSITION_CANDIDATE)
        # NEAR_TRIGGER
        elif (
            trigger_state == "WAITING_FOR_TRIGGER"
            and weekly_trend == "UPTREND"
            and opportunity.breakout_distance_pct <= 5.0
        ):
            queues.append(MarketplaceQueue.NEAR_TRIGGER)

        if opportunity.current_position_weight > 0.0:
            queues.append(MarketplaceQueue.CURRENT_HOLDING_REVIEW)

        # Research queues based on lenses (not mutually exclusive)
        if any(lens.lens_type == DiscoveryLensType.ASYMMETRIC_EQUITY for lens in lenses):
            queues.append(MarketplaceQueue.ASYMMETRIC_VALUE_RESEARCH)

        if any(lens.lens_type == DiscoveryLensType.CHART_AND_RECOGNITION for lens in lenses):
            queues.append(MarketplaceQueue.CHART_MOMENTUM_RESEARCH)

        if any(lens.lens_type == DiscoveryLensType.TOP_DOWN_MARKET_AND_INDUSTRY for lens in lenses):
            queues.append(MarketplaceQueue.TOP_DOWN_INDUSTRY_RESEARCH)

        if any(lens.lens_type == DiscoveryLensType.CORPORATE_EVENT_AND_ACTIVIST for lens in lenses):
            queues.append(MarketplaceQueue.EVENT_ACTIVIST_RESEARCH)

        if any(lens.lens_type == DiscoveryLensType.TURTLE_TREND_RESEARCH_LENS for lens in lenses):
            queues.append(MarketplaceQueue.CHART_MOMENTUM_RESEARCH)

        # Special situations (multiple conflicting signals)
        if (len(lenses) >= 3 and opportunity.model_disagreement) or opportunity.failed_breakout or opportunity.failed_breakdown:
            queues.append(MarketplaceQueue.SPECIAL_SITUATION)

        if opportunity.known_catalysts and len(opportunity.known_catalysts) > 0 and MarketplaceQueue.EVENT_ACTIVIST_RESEARCH not in queues:
            queues.append(MarketplaceQueue.EVENT_ACTIVIST_RESEARCH)

        if opportunity.expected_upside_pct is not None and opportunity.expected_upside_pct >= 80.0:
            queues.append(MarketplaceQueue.HIGH_RISK_SPECULATIVE)

        has_research_queue = any(
            q in queues
            for q in (
                MarketplaceQueue.ASYMMETRIC_VALUE_RESEARCH,
                MarketplaceQueue.CHART_MOMENTUM_RESEARCH,
                MarketplaceQueue.TOP_DOWN_INDUSTRY_RESEARCH,
                MarketplaceQueue.EVENT_ACTIVIST_RESEARCH,
                MarketplaceQueue.SPECIAL_SITUATION,
                MarketplaceQueue.HIGH_RISK_SPECULATIVE,
                MarketplaceQueue.CURRENT_HOLDING_REVIEW,
            )
        )

        # If nothing else, mark as research-only or waiting-for-confirmation
        research_candidate = self._is_research_candidate(opportunity, lenses)

        if not queues:
            if research_candidate:
                queues.append(MarketplaceQueue.RESEARCH_ONLY)
                if trigger_state == "WAITING_FOR_TRIGGER" and weekly_trend == "UPTREND":
                    queues.append(MarketplaceQueue.WAITING_FOR_CONFIRMATION)
            else:
                queues.append(MarketplaceQueue.WAITING_FOR_CONFIRMATION)

        if not has_research_queue and research_candidate:
            queues.append(MarketplaceQueue.RESEARCH_ONLY)

        return tuple(queues)

    def _classify_liquidity_tier(self, opportunity: Opportunity) -> LiquidityTier:
        """Classify security liquidity tier."""
        avg_daily_dollar_vol = opportunity.average_daily_dollar_volume

        if avg_daily_dollar_vol >= 10_000_000:
            return LiquidityTier.INSTITUTIONALLY_LIQUID
        elif avg_daily_dollar_vol >= 2_000_000:
            return LiquidityTier.TRADEABLE_SMALL_CAP
        elif avg_daily_dollar_vol >= 500_000:
            return LiquidityTier.LIMITED_CAPACITY
        elif avg_daily_dollar_vol >= 100_000:
            return LiquidityTier.STARTER_ONLY
        elif avg_daily_dollar_vol >= 10_000:
            return LiquidityTier.RESEARCH_ONLY
        else:
            return LiquidityTier.UNTRADEABLE

    def _is_actionable(
        self,
        opportunity: Opportunity,
        queues: tuple[MarketplaceQueue, ...],
    ) -> bool:
        """Determine if opportunity is actionable (trade-ready)."""
        if MarketplaceQueue.EXCLUDED in queues:
            return False

        return (
            str(opportunity.trigger_state).upper() == "TRIGGERED"
            and opportunity.risk_eligible
            and opportunity.governance_eligible
            and not opportunity.model_disagreement
        )

    def _is_hard_excluded(self, opportunity: Opportunity) -> bool:
        """Check for hard exclusions."""
        # Invalid or stale data
        if opportunity.data_available_through > opportunity.observation_time:
            return True

        # Missing required data
        if opportunity.average_daily_dollar_volume <= 0:
            return True

        # Untradeable liquidity
        if opportunity.average_daily_dollar_volume < 10_000:
            return True

        # Governance failure
        if not opportunity.governance_eligible:
            return True

        # Critical risk
        if "critical" in opportunity.liquidity_risk.lower() or "critical" in opportunity.gap_risk.lower():
            return True

        return False

    def _get_exclusion_reason(self, opportunity: Opportunity) -> str:
        """Get reason for exclusion."""
        if opportunity.data_available_through > opportunity.observation_time:
            return "Stale or future-dated data"
        if opportunity.average_daily_dollar_volume <= 0:
            return "Invalid liquidity data"
        if opportunity.average_daily_dollar_volume < 10_000:
            return "Untradeable liquidity"
        if not opportunity.governance_eligible:
            return "Governance restriction"
        if "critical" in opportunity.liquidity_risk.lower():
            return "Critical liquidity risk"
        if "critical" in opportunity.gap_risk.lower():
            return "Critical gap risk"
        return "Hard exclusion criteria met"

    def _is_research_candidate(self, opportunity: Opportunity, lenses: tuple[DiscoveryLens, ...]) -> bool:
        return bool(lenses) or opportunity.expected_upside_pct is not None or opportunity.known_catalysts

    def _identify_pattern_family(self, opportunity: Opportunity) -> tuple[str, dict[str, float]]:
        trigger_state = str(opportunity.trigger_state).upper()
        weekly_trend = str(opportunity.weekly_trend_state).upper()
        daily_trend = str(opportunity.daily_trend_state).upper()
        setup_type = str(opportunity.setup_type).upper()

        provenance = {
            "breakout_distance_pct": float(opportunity.breakout_distance_pct),
            "distance_to_support_pct": float(opportunity.distance_to_support_pct),
            "distance_to_resistance_pct": float(opportunity.distance_to_resistance_pct),
            "relative_volume": float(opportunity.relative_volume),
            "volatility_contraction": float(opportunity.volatility_contraction),
            "volatility_expansion": float(opportunity.volatility_expansion),
            "weekly_relative_strength": float(opportunity.weekly_relative_strength),
            "daily_relative_strength": float(opportunity.daily_relative_strength),
        }

        if opportunity.failed_breakout:
            return "failed_breakout_reversal", provenance
        if opportunity.failed_breakdown:
            return "undercut_and_reclaim", provenance
        if "CUP" in setup_type or "HANDLE" in setup_type:
            return "cup_and_handle", provenance
        if "BASE_ON_BASE" in setup_type or (weekly_trend == "UPTREND" and opportunity.volatility_contraction >= 0.2):
            return "base_on_base", provenance
        if "FLAT" in setup_type:
            return "flat_base", provenance
        if "PULLBACK" in setup_type or (weekly_trend == "UPTREND" and daily_trend != "UPTREND"):
            return "constructive_pullback", provenance
        if trigger_state == "TRIGGERED" and opportunity.relative_volume >= 1.2:
            return "relative_strength_breakout", provenance
        if opportunity.relative_volume >= 1.3 and opportunity.breakout_distance_pct > 0.0:
            return "early_momentum_entry", provenance
        return "general_research", provenance

    def _build_horizon_assessments(
        self,
        *,
        opportunity: Opportunity,
        lenses: tuple[DiscoveryLens, ...],
        research_confidence: float,
        opportunity_attractiveness: float,
        is_actionable: bool,
        pattern_family: str,
    ) -> tuple[HorizonAssessment, HorizonAssessment, HorizonAssessment, HorizonAssessment]:
        lens_names = tuple(lens.lens_type.value for lens in lenses)
        supporting = lens_names if lens_names else (pattern_family,)
        contradictions = tuple(opportunity.warnings[:3])
        required_confirmation = tuple(opportunity.thesis_invalidation_reasons) if opportunity.thesis_invalidation_reasons else (
            "price and volume confirmation",
        )
        invalidation = f"Close below {opportunity.primary_invalidation_price:.2f}" if opportunity.primary_invalidation_price else "structural breakdown"

        research_horizon = HorizonAssessment(
            horizon_name="RESEARCH_HORIZON",
            status="QUALIFIED" if lenses else "MONITOR",
            attractiveness=min(100.0, max(research_confidence, opportunity_attractiveness * 0.6)),
            confidence=min(1.0, max(0.0, research_confidence / 100.0)),
            expected_realization_window="2-5 years",
            supporting_evidence=supporting,
            contradictory_evidence=contradictions,
            required_confirmation=required_confirmation,
            invalidation=invalidation,
            calibration_status=str(opportunity.calibration_status),
        )

        primary_horizon = HorizonAssessment(
            horizon_name="PRIMARY_REPRICING_HORIZON",
            status="POSSIBLE" if opportunity.expected_upside_pct is not None else "UNCONFIRMED",
            attractiveness=min(100.0, abs(opportunity.expected_upside_pct or 0.0) + research_confidence * 0.3),
            confidence=min(1.0, (research_confidence / 100.0) + (0.15 if opportunity.expected_upside_pct is not None else 0.0)),
            expected_realization_window=f"{int(opportunity.expected_holding_days or 20)} trading days",
            supporting_evidence=supporting,
            contradictory_evidence=contradictions,
            required_confirmation=required_confirmation,
            invalidation=invalidation,
            calibration_status=str(opportunity.calibration_status),
        )

        tactical_horizon = HorizonAssessment(
            horizon_name="TACTICAL_SWING_HORIZON",
            status="SETUP" if opportunity.relative_volume >= 1.0 else "WAIT",
            attractiveness=min(100.0, (opportunity.relative_volume * 25.0) + max(0.0, opportunity.breakout_distance_pct * 4.0)),
            confidence=min(1.0, opportunity.relative_volume / 2.0),
            expected_realization_window="5-60 trading days",
            supporting_evidence=supporting,
            contradictory_evidence=contradictions,
            required_confirmation=("breakout confirmation",) if not is_actionable else ("execution plan complete",),
            invalidation=invalidation,
            calibration_status=str(opportunity.calibration_status),
        )

        execution_horizon = HorizonAssessment(
            horizon_name="EXECUTION_HORIZON",
            status="READY" if is_actionable else ("AWAITING_CONFIRMATION" if opportunity.trigger_state.upper() == "WAITING_FOR_TRIGGER" else "RESEARCH_ONLY"),
            attractiveness=100.0 if is_actionable else (75.0 if opportunity.trigger_state.upper() == "TRIGGERED" else 25.0),
            confidence=1.0 if is_actionable else 0.4,
            expected_realization_window="1-10 trading days",
            supporting_evidence=supporting,
            contradictory_evidence=contradictions,
            required_confirmation=required_confirmation,
            invalidation=invalidation,
            calibration_status=str(opportunity.calibration_status),
        )

        return research_horizon, primary_horizon, tactical_horizon, execution_horizon

    @staticmethod
    def _format_optional_pct(value: float | None) -> str:
        return f"{value:.1f}%" if value is not None else "n/a"

    def _calculate_opportunity_attractiveness(
        self,
        *,
        opportunity: Opportunity,
        lenses: tuple[DiscoveryLens, ...],
        research_confidence: float,
    ) -> float:
        base = float(opportunity.expected_value_score or 0.0)
        if base <= 0.0:
            base = 0.0
            if opportunity.expected_upside_pct is not None:
                base += min(40.0, max(0.0, float(opportunity.expected_upside_pct)))
            base += min(20.0, float(opportunity.relative_volume) * 10.0)
            base += min(20.0, float(opportunity.daily_relative_strength) * 10.0)
            base += min(20.0, float(opportunity.weekly_relative_strength) * 10.0)
            if str(opportunity.trigger_state).upper() == "TRIGGERED":
                base += 10.0
            if opportunity.failed_breakout or opportunity.failed_breakdown:
                base -= 10.0
            base += min(10.0, len(lenses) * 2.0)
            base += min(10.0, research_confidence / 10.0)
        return max(0.0, min(100.0, base))

    def _check_microcap_warnings(self, opportunity: Opportunity) -> tuple[str, ...]:
        """Check for micro-cap specific warnings."""
        warnings: list[str] = []

        if any("shelf" in w.lower() for w in opportunity.warnings):
            warnings.append("shelf_registration_active")

        if any("atm" in w.lower() for w in opportunity.warnings):
            warnings.append("at_market_offering_active")

        if any("warrant" in w.lower() for w in opportunity.warnings):
            warnings.append("warrants_outstanding")

        if any("convertible" in w.lower() for w in opportunity.warnings):
            warnings.append("convertibles_outstanding")

        if any("dilution" in w.lower() for w in opportunity.warnings):
            warnings.append("potential_dilution_risk")

        if any("float" in w.lower() for w in opportunity.warnings):
            warnings.append("low_float_risk")

        if any("auditor" in w.lower() for w in opportunity.warnings):
            warnings.append("auditor_concerns")

        return tuple(warnings)

    def _calculate_research_confidence(
        self,
        lenses: tuple[DiscoveryLens, ...],
        opportunity: Opportunity,
    ) -> float:
        """Calculate research confidence (separate from opportunity attractiveness)."""
        if not lenses:
            return 0.0

        # Average discovery score across lenses
        avg_score = sum(lens.discovery_score for lens in lenses) / len(lenses)

        # Adjust based on calibration
        if opportunity.calibration_status == "CALIBRATED":
            avg_score *= 1.1

        # Penalize for model disagreement
        if opportunity.model_disagreement:
            avg_score *= 0.8

        return min(100.0, avg_score)

    def _build_basic_thesis(
        self,
        opportunity: Opportunity,
        lenses: tuple[DiscoveryLens, ...],
        observation_time: datetime,
    ) -> StructuredThesis | None:
        """Build a basic structured thesis from opportunity data."""
        if not lenses:
            return None

        thesis_id = f"THESIS-{uuid.uuid4().hex[:8]}"

        lens_names = ", ".join(str(lens.lens_type.value) for lens in lenses)

        return StructuredThesis(
            thesis_id=thesis_id,
            observation_time=observation_time,
            why_surfaced=f"Discovered by {len(lenses)} independent research lens(es): {lens_names}",
            primary_repricing_mechanism=f"{opportunity.trigger_state} - {opportunity.setup_type} setup with "
            f"{self._format_optional_pct(opportunity.expected_upside_pct)} expected upside",
            business_or_asset_value_thesis=f"Weekly {opportunity.weekly_trend_state}, Daily {opportunity.daily_trend_state}, "
            f"Structure Quality: {opportunity.weekly_structure_quality:.2f}",
            survivability_conclusion="No immediate survival threats detected" if opportunity.risk_eligible else "Risk constraints active",
            market_misunderstanding=f"Market may not recognize the opportunity in {opportunity.setup_type} setup",
            catalyst_description=f"Next catalyst: {opportunity.next_known_event_time if opportunity.next_known_event_time else 'TBD'}",
            recognition_state=f"{opportunity.calibration_status}",
            bear_outcome=f"Down {self._format_optional_pct(opportunity.expected_downside_pct)} to invalidation",
            base_outcome=f"Modest gains in base scenario",
            bull_outcome=f"Up {self._format_optional_pct(opportunity.expected_upside_pct)} in bull scenario",
            primary_horizon_days=int(opportunity.expected_holding_days or 20),
            tactical_horizon_days=5,
            required_confirmation=f"Price must stay above {opportunity.daily_support_levels[0] if opportunity.daily_support_levels else 'prior low'}",
            invalidation_condition=f"Close below {opportunity.primary_invalidation_price:.2f}",
            strongest_bull_argument=f"Weekly structure completion + relative strength during broad market strength",
            strongest_bear_argument=f"Limited catalysts and execution risk remain",
            highest_sensitivity_assumption=f"Catalyst timing - if pushed 30+ days, opportunity may dissipate",
            confidence_score=self._calculate_research_confidence(lenses, opportunity) / 100.0,
        )

    def classify_batch(
        self,
        opportunities: list[Opportunity],
        observation_time: datetime | None = None,
    ) -> dict[str, OpportunityCandidateClassification]:
        """Classify multiple opportunities.

        Args:
            opportunities: List of Opportunity objects
            observation_time: Point-in-time reference

        Returns:
            Dictionary of opportunity_id -> OpportunityCandidateClassification
        """
        result = {}
        for opp in opportunities:
            classification = self.classify(opp, observation_time)
            result[opp.opportunity_id] = classification
        return result
