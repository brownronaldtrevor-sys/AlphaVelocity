"""Marketplace classifier - assign opportunities to queues and discovery lenses."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from alpha_velocity.opportunity import Opportunity

from .models import (
    DiscoveryLens,
    DiscoveryLensType,
    ExecutionHorizonStatus,
    ExpectedMoveTimeProfile,
    FutureOutlookSummary,
    GroundedEvidence,
    InflectionDimensionAssessment,
    InflectionDimensionType,
    InflectionDirection,
    InflectionProfile,
    InflectionStage,
    InflectionSynchronizationProfile,
    LiquidityTier,
    MarketplaceQueue,
    HorizonAssessment,
    MomentumProfile,
    MomentumState,
    MultiHorizonProfile,
    OpportunityCandidateClassification,
    PatternProfile,
    StructuredThesis,
    ValidationStatus,
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

        multi_horizon_profile = MultiHorizonProfile(
            research_horizon=research_horizon,
            primary_repricing_horizon=primary_horizon,
            tactical_swing_horizon=tactical_horizon,
            execution_horizon=execution_horizon,
        )
        inflection_profile = self._build_inflection_profile(opportunity, observation_time)
        synchronization_profile = self._build_synchronization_profile(inflection_profile)
        momentum_profile = self._build_momentum_profile(opportunity)
        pattern_profile = self._build_pattern_profile(opportunity, pattern_family, pattern_provenance)
        future_outlook_summary = self._build_future_outlook_summary(opportunity)
        expected_move_time_profiles = self._build_expected_move_time_profiles(opportunity)
        grounded_evidence = self._build_grounded_evidence(opportunity, observation_time)
        known, unknown, most_sensitive_assumption, what_would_change_my_mind = self._build_epistemic_summary(
            opportunity=opportunity,
            inflection_profile=inflection_profile,
        )
        ranking_shadow_signals = self._build_ranking_shadow_signals(
            opportunity=opportunity,
            research_horizon=research_horizon,
            primary_horizon=primary_horizon,
            tactical_horizon=tactical_horizon,
            execution_horizon=execution_horizon,
            synchronization_profile=synchronization_profile,
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
            multi_horizon_profile=multi_horizon_profile,
            inflection_profile=inflection_profile,
            synchronization_profile=synchronization_profile,
            momentum_profile=momentum_profile,
            pattern_profile=pattern_profile,
            future_outlook_summary=future_outlook_summary,
            expected_move_time_profiles=expected_move_time_profiles,
            grounded_evidence=grounded_evidence,
            known=known,
            unknown=unknown,
            most_sensitive_assumption=most_sensitive_assumption,
            what_would_change_my_mind=what_would_change_my_mind,
            ranking_shadow_signals=ranking_shadow_signals,
            ranking_shadow_influence_enabled=False,
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
            status="BUILDING" if opportunity.expected_upside_pct is not None else "UNCONFIRMED",
            attractiveness=min(100.0, abs(opportunity.expected_upside_pct or 0.0) + research_confidence * 0.3),
            confidence=min(1.0, (research_confidence / 100.0) + (0.15 if opportunity.expected_upside_pct is not None else 0.0)),
            expected_realization_window="3-18 months",
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

        execution_status = self._derive_execution_horizon_status(opportunity, is_actionable)
        execution_horizon = HorizonAssessment(
            horizon_name="EXECUTION_HORIZON",
            status=execution_status.value,
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

    def _derive_execution_horizon_status(self, opportunity: Opportunity, is_actionable: bool) -> ExecutionHorizonStatus:
        trigger_state = str(opportunity.trigger_state).upper()
        if not opportunity.risk_eligible or not opportunity.governance_eligible:
            return ExecutionHorizonStatus.WAIT
        if opportunity.failed_breakout or opportunity.failed_breakdown:
            return ExecutionHorizonStatus.FAILED
        if opportunity.current_position_weight > 0.0 and trigger_state != "TRIGGERED":
            return ExecutionHorizonStatus.EXIT_REVIEW
        if is_actionable:
            if opportunity.breakout_distance_pct >= 4.0:
                return ExecutionHorizonStatus.EXTENDED
            if opportunity.calibration_status.upper() == "CALIBRATED":
                return ExecutionHorizonStatus.ACTIONABLE
            return ExecutionHorizonStatus.SCALE_ELIGIBLE
        if trigger_state == "TRIGGERED":
            return ExecutionHorizonStatus.STARTER_ELIGIBLE
        if trigger_state == "WAITING_FOR_TRIGGER":
            return ExecutionHorizonStatus.WATCH
        return ExecutionHorizonStatus.WAIT

    def _build_inflection_profile(self, opportunity: Opportunity, observation_time: datetime) -> InflectionProfile:
        dimensions: list[InflectionDimensionAssessment] = []
        improving = InflectionDirection.IMPROVING
        flat = InflectionDirection.FLAT
        deteriorating = InflectionDirection.DETERIORATING
        trigger_state = str(opportunity.trigger_state).upper()

        technical_stage = InflectionStage.CONFIRMED if trigger_state == "TRIGGERED" else InflectionStage.BUILDING
        if opportunity.failed_breakout or opportunity.failed_breakdown:
            technical_stage = InflectionStage.ROLLING_OVER

        fundamentals_stage = InflectionStage.BUILDING if (opportunity.expected_upside_pct or 0.0) >= 12.0 else InflectionStage.PRE_INFLECTION
        if not opportunity.risk_eligible:
            fundamentals_stage = InflectionStage.DETERIORATING

        recognition_stage = InflectionStage.EARLY_INFLECTION if trigger_state == "WAITING_FOR_TRIGGER" else InflectionStage.CONFIRMED
        if opportunity.breakout_distance_pct >= 5.0:
            recognition_stage = InflectionStage.EXTENDED

        dimensions.append(self._dimension(InflectionDimensionType.FUNDAMENTAL, fundamentals_stage, improving if fundamentals_stage != InflectionStage.DETERIORATING else deteriorating, opportunity, observation_time, "Scenario-driven upside with survivability checks"))
        dimensions.append(self._dimension(InflectionDimensionType.EARNINGS_AND_MARGIN, InflectionStage.BUILDING, improving if opportunity.expected_upside_pct is not None else flat, opportunity, observation_time, "Normalized earnings outlook inferred from expected upside"))
        dimensions.append(self._dimension(InflectionDimensionType.CAPITAL_STRUCTURE, InflectionStage.BUILDING if opportunity.risk_eligible else InflectionStage.DETERIORATING, improving if opportunity.risk_eligible else deteriorating, opportunity, observation_time, "Risk eligibility and liquidity constraints"))
        dimensions.append(self._dimension(InflectionDimensionType.INDUSTRY, InflectionStage.EARLY_INFLECTION if str(opportunity.sector_regime).upper() in {"EARLY_LEADERSHIP", "EMERGING_INFLECTION"} else InflectionStage.UNKNOWN, improving if str(opportunity.sector_regime).upper() in {"EARLY_LEADERSHIP", "ESTABLISHED_LEADER", "EMERGING_INFLECTION"} else flat, opportunity, observation_time, "Sector and industry regime alignment"))
        dimensions.append(self._dimension(InflectionDimensionType.PEER, InflectionStage.BUILDING if opportunity.weekly_relative_strength >= 1.0 else InflectionStage.PRE_INFLECTION, improving if opportunity.weekly_relative_strength >= 1.0 else flat, opportunity, observation_time, "Relative strength versus peer proxy"))
        dimensions.append(self._dimension(InflectionDimensionType.MACRO, InflectionStage.UNKNOWN, flat, opportunity, observation_time, "Macro state remains unmodeled in sample workflows"))
        dimensions.append(self._dimension(InflectionDimensionType.MANAGEMENT_EXPECTATIONS, InflectionStage.BUILDING if opportunity.known_catalysts else InflectionStage.UNKNOWN, improving if opportunity.known_catalysts else flat, opportunity, observation_time, "Catalyst and guidance proxy"))
        dimensions.append(self._dimension(InflectionDimensionType.ESTIMATE_REVISIONS, InflectionStage.BUILDING if opportunity.calibration_status.upper() == "CALIBRATED" else InflectionStage.PRE_INFLECTION, improving if opportunity.calibration_status.upper() == "CALIBRATED" else flat, opportunity, observation_time, "Calibration and probability availability"))
        dimensions.append(self._dimension(InflectionDimensionType.MARKET_RECOGNITION, recognition_stage, improving if trigger_state in {"TRIGGERED", "WAITING_FOR_TRIGGER"} else flat, opportunity, observation_time, "Trigger-state recognition tracking"))
        dimensions.append(self._dimension(InflectionDimensionType.TECHNICAL, technical_stage, improving if technical_stage in {InflectionStage.BUILDING, InflectionStage.CONFIRMED} else deteriorating, opportunity, observation_time, "Pattern and volume confirmation"))
        dimensions.append(self._dimension(InflectionDimensionType.CATALYST, InflectionStage.BUILDING if opportunity.known_catalysts else InflectionStage.UNKNOWN, improving if opportunity.known_catalysts else flat, opportunity, observation_time, "Known catalyst schedule"))
        dimensions.append(self._dimension(InflectionDimensionType.POSITION_LIFECYCLE, InflectionStage.EXTENDED if opportunity.current_position_weight > 0.0 and opportunity.breakout_distance_pct >= 4.0 else InflectionStage.EARLY_INFLECTION, improving if opportunity.current_position_weight == 0.0 else flat, opportunity, observation_time, "Position lifecycle and extension risk"))

        before_within_after = {
            "RESEARCH_HORIZON": "WITHIN" if fundamentals_stage in {InflectionStage.BUILDING, InflectionStage.CONFIRMED} else "BEFORE",
            "PRIMARY_REPRICING_HORIZON": "WITHIN" if recognition_stage in {InflectionStage.EARLY_INFLECTION, InflectionStage.BUILDING, InflectionStage.CONFIRMED} else "AFTER",
            "TACTICAL_SWING_HORIZON": "WITHIN" if technical_stage in {InflectionStage.EARLY_INFLECTION, InflectionStage.BUILDING, InflectionStage.CONFIRMED} else "AFTER",
            "EXECUTION_HORIZON": "WITHIN" if trigger_state == "TRIGGERED" else "BEFORE",
        }
        return InflectionProfile(dimensions=tuple(dimensions), before_within_after_by_horizon=before_within_after)

    def _dimension(
        self,
        dimension_type: InflectionDimensionType,
        stage: InflectionStage,
        direction: InflectionDirection,
        opportunity: Opportunity,
        observation_time: datetime,
        summary: str,
    ) -> InflectionDimensionAssessment:
        contradictory = tuple(opportunity.warnings[:1])
        required_confirmation = (
            "Volume confirmation above trigger",
            "No governance or risk rejection",
        )
        invalidation = f"Close below {opportunity.primary_invalidation_price:.2f}" if opportunity.primary_invalidation_price else "Loss of structural support"
        velocity = max(-1.0, min(1.0, (opportunity.relative_volume - 1.0)))
        confidence = min(1.0, max(0.0, (opportunity.weekly_structure_quality + opportunity.daily_structure_quality) / 2.0))
        return InflectionDimensionAssessment(
            dimension=dimension_type,
            stage=stage,
            direction=direction,
            velocity=velocity,
            confidence=confidence,
            evidence=(summary,),
            contradictory_evidence=contradictory,
            available_at=observation_time,
            required_confirmation=required_confirmation,
            invalidation=invalidation,
            calibration_status=opportunity.calibration_status,
        )

    def _build_synchronization_profile(self, inflection_profile: InflectionProfile) -> InflectionSynchronizationProfile:
        improving = [d for d in inflection_profile.dimensions if d.direction == InflectionDirection.IMPROVING]
        deteriorating = [d for d in inflection_profile.dimensions if d.direction == InflectionDirection.DETERIORATING]
        contradictions = tuple(
            f"{d.dimension.value}: {d.contradictory_evidence[0]}"
            for d in inflection_profile.dimensions
            if d.contradictory_evidence
        )
        agreement_strength = 0.0
        if inflection_profile.dimensions:
            agreement_strength = len(improving) / len(inflection_profile.dimensions)
        recognition_gap = 0.0
        fundamentals = next((d for d in inflection_profile.dimensions if d.dimension == InflectionDimensionType.FUNDAMENTAL), None)
        market_recognition = next((d for d in inflection_profile.dimensions if d.dimension == InflectionDimensionType.MARKET_RECOGNITION), None)
        if fundamentals and market_recognition:
            stage_delta = max(0.0, float(fundamentals.stage.value != market_recognition.stage.value))
            recognition_gap = min(1.0, stage_delta + max(0.0, fundamentals.confidence - market_recognition.confidence))
        lead_lag = (
            "FUNDAMENTAL_LEADS_MARKET_RECOGNITION"
            if recognition_gap >= 0.25
            else "TECHNICAL_AND_RECOGNITION_SYNCHRONIZED"
        )
        timing_opportunity = "EARLY" if recognition_gap >= 0.25 else ("ALIGNED" if agreement_strength >= 0.5 else "MIXED")
        contributors = {
            "improving_ratio": agreement_strength,
            "recognition_gap": recognition_gap,
            "deterioration_ratio": (len(deteriorating) / max(1, len(inflection_profile.dimensions))),
        }
        return InflectionSynchronizationProfile(
            improving_dimensions=len(improving),
            deteriorating_dimensions=len(deteriorating),
            agreement_strength=agreement_strength,
            contradictions=contradictions,
            lead_lag_relationships=(lead_lag,),
            recognition_gap=recognition_gap,
            timing_opportunity=timing_opportunity,
            contributors=contributors,
        )

    def _build_momentum_profile(self, opportunity: Opportunity) -> MomentumProfile:
        long_term_trend = str(opportunity.weekly_trend_state).upper()
        medium_term_trend = str(opportunity.daily_trend_state).upper()
        short_term_trend = "UP" if opportunity.breakout_distance_pct > 0.0 else "FLAT"
        trend_direction = "UP" if long_term_trend == "UPTREND" or medium_term_trend == "UPTREND" else "MIXED"
        trend_velocity = max(-1.0, min(1.0, (opportunity.relative_volume - 1.0) * 0.75))
        trend_persistence = min(1.0, max(0.0, (opportunity.weekly_structure_quality + opportunity.daily_structure_quality) / 2.0))

        momentum_state = MomentumState.UNKNOWN
        if opportunity.failed_breakout or opportunity.failed_breakdown:
            momentum_state = MomentumState.FAILED
        elif opportunity.breakout_distance_pct >= 5.0:
            momentum_state = MomentumState.EXTENDED
        elif opportunity.relative_volume >= 1.5:
            momentum_state = MomentumState.CONFIRMED_MOMENTUM
        elif opportunity.relative_volume >= 1.1:
            momentum_state = MomentumState.EARLY_MOMENTUM
        elif opportunity.relative_volume < 0.9:
            momentum_state = MomentumState.EXHAUSTING
        else:
            momentum_state = MomentumState.MATURE_MOMENTUM

        return MomentumProfile(
            long_term_trend=long_term_trend,
            medium_term_trend=medium_term_trend,
            short_term_trend=short_term_trend,
            trend_direction=trend_direction,
            trend_velocity=trend_velocity,
            trend_persistence=trend_persistence,
            trend_maturity=momentum_state,
            relative_strength_vs_market=opportunity.weekly_relative_strength,
            relative_strength_vs_sector=opportunity.daily_relative_strength,
            relative_strength_vs_peers=(opportunity.weekly_relative_strength + opportunity.daily_relative_strength) / 2.0,
            relative_volume=opportunity.relative_volume,
            liquidity_adjusted_momentum=max(0.0, opportunity.relative_volume * min(1.0, opportunity.average_daily_dollar_volume / 5_000_000.0)),
            volatility_state=str(opportunity.daily_volatility_state),
            acceleration=max(0.0, opportunity.volatility_expansion),
            deceleration=max(0.0, opportunity.volatility_contraction),
        )

    def _build_pattern_profile(
        self,
        opportunity: Opportunity,
        pattern_family: str,
        pattern_provenance: dict[str, float],
    ) -> PatternProfile:
        support = max(0.0, opportunity.close_price * (1.0 - (opportunity.distance_to_support_pct / 100.0)))
        resistance = max(0.0, opportunity.close_price * (1.0 + (opportunity.distance_to_resistance_pct / 100.0)))
        depth = abs(opportunity.distance_to_support_pct)
        duration_days = 20 if "base" in pattern_family else 10
        quality_warnings: list[str] = []
        if opportunity.relative_volume < 1.0:
            quality_warnings.append("relative_volume_below_confirmed_threshold")
        if opportunity.breakout_distance_pct >= 5.0:
            quality_warnings.append("extension_risk")
        if opportunity.failed_breakout:
            quality_warnings.append("failed_breakout_risk")
        return PatternProfile(
            pattern_name=pattern_family,
            calculation_window=f"{duration_days}_trading_days",
            pivot_or_trigger=opportunity.daily_breakout_level,
            support=support,
            resistance=resistance,
            depth=depth,
            duration_days=duration_days,
            volume_behavior="EXPANDING" if opportunity.relative_volume >= 1.1 else "NEUTRAL",
            volatility_behavior="CONTRACTION" if opportunity.volatility_contraction >= opportunity.volatility_expansion else "EXPANSION",
            distance_to_trigger=abs(opportunity.breakout_distance_pct),
            extension=max(0.0, opportunity.breakout_distance_pct),
            invalidation=f"Close below {opportunity.primary_invalidation_price:.2f}" if opportunity.primary_invalidation_price else "Loss of setup support",
            quality_warnings=tuple(quality_warnings),
            provenance=pattern_provenance,
        )

    def _build_future_outlook_summary(self, opportunity: Opportunity) -> FutureOutlookSummary:
        verified_facts = (
            f"trigger_state={opportunity.trigger_state}",
            f"weekly_trend_state={opportunity.weekly_trend_state}",
            f"daily_trend_state={opportunity.daily_trend_state}",
        )
        company_guidance = tuple(
            str(catalyst.get("name", "guidance_item"))
            for catalyst in opportunity.known_catalysts
            if isinstance(catalyst, dict)
        )
        third_party_estimates = ()
        alpha_velocity_scenarios = (
            f"expected_upside_pct={self._format_optional_pct(opportunity.expected_upside_pct)}",
            f"expected_downside_pct={self._format_optional_pct(opportunity.expected_downside_pct)}",
        )
        human_hypotheses = ()
        model_inference = (
            "momentum_state_inferred_from_relative_volume",
            "inflection_stage_inferred_from_trigger_and_regime",
        )
        unknowns = (
            "consensus_estimate_feed_unavailable" if opportunity.probability_estimate is None else "",
            "peer_revision_dataset_unavailable",
        )
        clean_unknowns = tuple(item for item in unknowns if item)
        return FutureOutlookSummary(
            verified_facts=verified_facts,
            company_guidance=company_guidance,
            third_party_estimates=third_party_estimates,
            alpha_velocity_scenarios=alpha_velocity_scenarios,
            human_hypotheses=human_hypotheses,
            model_inference=model_inference,
            unknowns=clean_unknowns,
        )

    def _build_expected_move_time_profiles(self, opportunity: Opportunity) -> tuple[ExpectedMoveTimeProfile, ...]:
        upside = self._format_optional_pct(opportunity.expected_upside_pct)
        downside = self._format_optional_pct(opportunity.expected_downside_pct)
        confidence = min(1.0, max(0.0, 1.0 - opportunity.uncertainty_score))
        profiles = (
            ExpectedMoveTimeProfile(
                horizon_name="PRIMARY_REPRICING_HORIZON",
                expected_move_range=upside,
                expected_realization_window="3-18 months",
                confidence=confidence,
                downside_range=downside,
                liquidity=opportunity.average_daily_dollar_volume,
                transaction_cost_estimate_bps=float(opportunity.estimated_cost_bps or 0.0),
                opportunity_cost_considerations=("cash_competes_as_default_candidate",),
                evidence_quality=ValidationStatus.SUPPORTED if opportunity.expected_upside_pct is not None else ValidationStatus.UNKNOWN,
            ),
            ExpectedMoveTimeProfile(
                horizon_name="TACTICAL_SWING_HORIZON",
                expected_move_range=upside,
                expected_realization_window="5-60 trading days",
                confidence=min(1.0, max(0.0, opportunity.relative_volume / 2.0)),
                downside_range=downside,
                liquidity=opportunity.average_daily_dollar_volume,
                transaction_cost_estimate_bps=float(opportunity.estimated_cost_bps or 0.0),
                opportunity_cost_considerations=("extension_risk_monitoring_required",),
                evidence_quality=ValidationStatus.SUPPORTED,
            ),
        )
        return profiles

    def _build_grounded_evidence(self, opportunity: Opportunity, observation_time: datetime) -> tuple[GroundedEvidence, ...]:
        lineage = tuple(opportunity.source_record_ids or ())
        source_id = opportunity.dataset_manifest_hash or opportunity.warehouse_manifest_hash or "unknown-dataset"
        return (
            GroundedEvidence(
                source="SAMPLE_DATA" if "sample" in source_id.lower() else "WAREHOUSE",
                document_or_dataset_id=source_id,
                observation_time=observation_time,
                available_at=opportunity.event_data_available_at,
                evidence_type="opportunity_features",
                confidence=min(1.0, max(0.0, 1.0 - opportunity.uncertainty_score)),
                validation_status=ValidationStatus.SUPPORTED,
                lineage=lineage,
            ),
        )

    def _build_epistemic_summary(
        self,
        *,
        opportunity: Opportunity,
        inflection_profile: InflectionProfile,
    ) -> tuple[tuple[str, ...], tuple[str, ...], str, str]:
        known = (
            f"trigger_state={opportunity.trigger_state}",
            f"relative_volume={opportunity.relative_volume:.2f}",
            f"sector_regime={opportunity.sector_regime}",
        )
        unknown = (
            "consensus_forward_estimates_missing" if opportunity.probability_estimate is None else "",
            "peer_margin_revision_history_missing",
            "macro_regime_mapping_partial",
        )
        unknown_clean = tuple(item for item in unknown if item)
        most_sensitive_assumption = "Recognition lag closes before technical setup expires"
        what_would_change_my_mind = "Technical trigger fails while inflection dimensions move to ROLLING_OVER or DETERIORATING"
        return known, unknown_clean, most_sensitive_assumption, what_would_change_my_mind

    def _build_ranking_shadow_signals(
        self,
        *,
        opportunity: Opportunity,
        research_horizon: HorizonAssessment,
        primary_horizon: HorizonAssessment,
        tactical_horizon: HorizonAssessment,
        execution_horizon: HorizonAssessment,
        synchronization_profile: InflectionSynchronizationProfile,
    ) -> dict[str, float]:
        return {
            "long_term_asymmetric_value": research_horizon.attractiveness,
            "primary_repricing_attractiveness": primary_horizon.attractiveness,
            "tactical_swing_attractiveness": tactical_horizon.attractiveness,
            "execution_readiness": execution_horizon.attractiveness,
            "inflection_synchronization": synchronization_profile.agreement_strength * 100.0,
            "recognition_gap": synchronization_profile.recognition_gap * 100.0,
            "research_confidence": max(0.0, min(100.0, 100.0 - (opportunity.uncertainty_score * 100.0))),
            "liquidity": min(100.0, opportunity.average_daily_dollar_volume / 100_000.0),
            "survivability": 100.0 if opportunity.risk_eligible else 20.0,
        }

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
