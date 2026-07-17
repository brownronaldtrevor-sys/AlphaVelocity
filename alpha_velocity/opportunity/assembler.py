from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from alpha_velocity.market.bars import Bar
from alpha_velocity.opportunity.models import (
    Assumption,
    AssumptionStatus,
    ClaimSet,
    ConvictionAssessment,
    ConvictionState,
    EvidenceClaim,
    ExpressionType,
    HorizonAssessment,
    InvalidationProfile,
    LifecycleStage,
    Opportunity,
    OpportunityExpression,
    OpportunityLifecycle,
    RecognitionProfile,
    RecognitionState,
    ThesisIdentity,
    ThesisStatus,
    ThesisType,
    ValidationStatus,
)


def assemble_opportunity(
    *,
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    feature_snapshots: list[dict[str, Any]],
    known_events: list[dict[str, Any]],
    liquidity_history: list[dict[str, Any]],
    observation_time: datetime,
    security_id: str,
    symbol: str,
    benchmark_symbol: str,
    sector: str,
    industry: str,
    universe_snapshot_id: str,
    provisional_weekly_bars: list[Bar] | None = None,
    warehouse_manifest_hash: str,
    dataset_manifest_hash: str,
    source_record_ids: list[str],
) -> Opportunity:
    if not observation_time.tzinfo:
        raise ValueError("observation_time must be timezone-aware")
    completed_weekly = [bar for bar in weekly_bars if bar.timestamp <= observation_time]
    if not completed_weekly and weekly_bars:
        completed_weekly = []
    completed_daily = [bar for bar in daily_bars if bar.timestamp <= observation_time]
    if not completed_daily:
        completed_daily = []
    latest_daily = completed_daily[-1] if completed_daily else None
    latest_weekly = completed_weekly[-1] if completed_weekly else None
    weekly_support = _rolling_support_levels(completed_weekly)
    weekly_resistance = _rolling_resistance_levels(completed_weekly)
    daily_support = _rolling_support_levels(completed_daily)
    daily_resistance = _rolling_resistance_levels(completed_daily)
    weekly_breakout = _breakout_level(completed_weekly)
    daily_breakout = _breakout_level(completed_daily)
    weekly_invalidation = _invalidation_level(completed_weekly)
    daily_invalidation = _invalidation_level(completed_daily)
    alignment = _classify_alignment(completed_weekly, completed_daily)
    feature_values: dict[str, float] = {}
    feature_versions: dict[str, str] = {}
    model_versions: dict[str, str] = {}
    warnings: list[str] = []
    for snapshot in feature_snapshots:
        group_name = str(snapshot.get("group_name", "")).strip().lower()
        values = snapshot.get("feature_values") or {}
        weight = float(snapshot.get("approved_weight", 0.0))
        if not group_name:
            continue
        feature_values[group_name] = 0.0
        feature_versions[group_name] = str(snapshot.get("version") or "unknown")
        if weight <= 0.0:
            warnings.append(f"unvalidated feature group {group_name} is visible but cannot influence allocation")
            continue
        for key, value in values.items():
            feature_values[key] = float(value)
    if not feature_values:
        feature_values = {}
    probability_estimate = None
    expected_upside_pct = None
    expected_downside_pct = None
    expected_holding_days = None
    estimated_cost_bps = None
    calibration_status = "UNCALIBRATED"
    expected_value_score = 0.0
    if latest_daily is not None:
        close_price = latest_daily.close
    else:
        close_price = 0.0

    enrichment = _build_enrichment(
        symbol=symbol,
        security_id=security_id,
        observation_time=observation_time,
        source_record_ids=source_record_ids,
    )

    return Opportunity(
        opportunity_id=f"{symbol}-{observation_time.strftime('%Y%m%d%H%M%S')}",
        security_id=security_id,
        symbol=symbol,
        observation_time=observation_time,
        data_available_through=observation_time,
        universe_snapshot_id=universe_snapshot_id,
        benchmark_symbol=benchmark_symbol,
        sector=sector,
        industry=industry,
        market_regime="neutral",
        sector_regime="neutral",
        weekly_trend_state="bullish" if latest_weekly and latest_weekly.close >= latest_weekly.open else "bearish",
        weekly_range_position=0.5,
        weekly_support_levels=tuple(weekly_support),
        weekly_resistance_levels=tuple(weekly_resistance),
        weekly_breakout_level=weekly_breakout,
        weekly_invalidation_level=weekly_invalidation,
        weekly_volatility_state="neutral",
        weekly_relative_strength=1.0,
        weekly_structure_quality=0.5,
        daily_trend_state="bullish" if latest_daily and latest_daily.close >= latest_daily.open else "bearish",
        daily_range_position=0.5,
        daily_support_levels=tuple(daily_support),
        daily_resistance_levels=tuple(daily_resistance),
        daily_breakout_level=daily_breakout,
        daily_invalidation_level=daily_invalidation,
        daily_volatility_state="neutral",
        daily_relative_strength=1.0,
        daily_structure_quality=0.5,
        setup_type="breakout",
        trigger_state="watch",
        breakout_distance_pct=0.0,
        distance_to_support_pct=0.0,
        distance_to_resistance_pct=0.0,
        volatility_contraction=0.0,
        volatility_expansion=0.0,
        relative_volume=1.0,
        close_quality=0.5,
        failed_breakout=False,
        failed_breakdown=False,
        multi_timeframe_alignment=alignment,
        close_price=close_price,
        average_daily_dollar_volume=1_000_000.0,
        average_daily_volume=1000.0,
        spread_estimate_bps=1.0,
        atr_pct=0.02,
        capacity_warning=False,
        known_catalysts=tuple(known_events),
        next_known_event_time=None,
        catalyst_risk="low",
        event_data_available_at=observation_time,
        probability_estimate=probability_estimate,
        expected_upside_pct=expected_upside_pct,
        expected_downside_pct=expected_downside_pct,
        expected_holding_days=expected_holding_days,
        estimated_cost_bps=estimated_cost_bps,
        uncertainty_score=0.5,
        calibration_status=calibration_status,
        expected_value_score=expected_value_score,
        opportunity_cost_rank=None,
        correlation_bucket="medium",
        concentration_bucket="moderate",
        current_position_weight=0.0,
        primary_invalidation_price=0.0,
        thesis_invalidation_reasons=tuple(),
        liquidity_risk="low",
        gap_risk="low",
        model_disagreement=False,
        governance_eligible=True,
        risk_eligible=True,
        feature_values=feature_values,
        feature_versions=feature_versions,
        model_versions=model_versions,
        warehouse_manifest_hash=warehouse_manifest_hash,
        dataset_manifest_hash=dataset_manifest_hash,
        source_record_ids=tuple(source_record_ids),
        warnings=tuple(warnings),
        thesis_identity=enrichment["thesis_identity"],
        expressions=enrichment["expressions"],
        lifecycle=enrichment["lifecycle"],
        research_horizon=enrichment["research_horizon"],
        primary_repricing_horizon=enrichment["primary_repricing_horizon"],
        tactical_swing_horizon=enrichment["tactical_swing_horizon"],
        execution_horizon=enrichment["execution_horizon"],
        recognition_profile=enrichment["recognition_profile"],
        claim_set=enrichment["claim_set"],
        assumptions=enrichment["assumptions"],
        invalidation_profile=enrichment["invalidation_profile"],
        research_conviction=enrichment["research_conviction"],
        capital_conviction=enrichment["capital_conviction"],
        created_at=datetime.now(timezone.utc),
    )


def _build_enrichment(
    *,
    symbol: str,
    security_id: str,
    observation_time: datetime,
    source_record_ids: list[str],
) -> dict[str, Any]:
    is_sample = security_id.startswith("sample-") or symbol.startswith(("TRG", "START", "NEAR", "VAL", "MOM", "TOP", "EVT", "SPEC", "EXC", "WEAK"))
    source = "SAMPLE_DATA" if is_sample else "SCANNER"

    thesis_type = ThesisType.SWING_REPRICING
    lifecycle_stage = LifecycleStage.RESEARCH
    recognition_state = RecognitionState.BEGINNING
    research_state = ConvictionState.MEDIUM
    capital_state = ConvictionState.LOW
    execution_status = "WATCH"
    primary_status = "BUILDING"
    tactical_status = "SETUP"
    thesis_status = ThesisStatus.ACTIVE
    contradictory_claims: tuple[EvidenceClaim, ...] = ()

    if symbol.startswith("TRG"):
        lifecycle_stage = LifecycleStage.PRIMARY_MOVE
        recognition_state = RecognitionState.ACCELERATING
        research_state = ConvictionState.HIGH
        capital_state = ConvictionState.MEDIUM
        execution_status = "ACTIONABLE"
    elif symbol.startswith("VAL"):
        thesis_type = ThesisType.ASSET_VALUE
        research_state = ConvictionState.VERY_HIGH
        capital_state = ConvictionState.LOW
        execution_status = "WAIT"
    elif symbol.startswith("NEAR"):
        primary_status = "BUILDING"
        tactical_status = "NEAR_TRIGGER"
        execution_status = "WATCH"
    elif symbol.startswith("TOP"):
        thesis_type = ThesisType.INDUSTRY_RECOVERY
        research_state = ConvictionState.HIGH
        capital_state = ConvictionState.LOW
        execution_status = "WAIT"
    elif symbol.startswith("MOM"):
        lifecycle_stage = LifecycleStage.HARVEST
        recognition_state = RecognitionState.EXTENDED
        primary_status = "MATURE"
        tactical_status = "EXTENDED"
        execution_status = "EXIT_REVIEW"
    elif symbol.startswith("EXC"):
        thesis_status = ThesisStatus.INVALIDATED
        lifecycle_stage = LifecycleStage.INVALIDATED
        recognition_state = RecognitionState.FAILED
        execution_status = "WAIT"
        contradictory_claims = (
            EvidenceClaim(
                claim_id=f"{symbol}-contradiction",
                text="New contradictory evidence invalidated the thesis.",
                claim_type="CONTRADICTION",
                source=source,
                observation_time=observation_time,
                available_at=observation_time,
                confidence=0.9,
                validation_status=ValidationStatus.SUPPORTED,
                evidence_lineage=tuple(source_record_ids),
            ),
        )

    primary_expression = OpportunityExpression(
        expression_id=f"{symbol}-expr-primary",
        security_id=security_id,
        symbol=symbol,
        expression_type=ExpressionType.EQUITY,
        role="PRIMARY",
        attractiveness=0.55,
        research_confidence=0.6,
        liquidity=0.7,
        implementation_cost=0.1,
        current_actionability=execution_status,
        relationship_to_thesis="PRIMARY_EXPRESSION",
        supporting_evidence=("Baseline expression from scanner",),
        available_at=observation_time,
        validation_status=ValidationStatus.SUPPORTED,
    )

    expressions = [primary_expression]
    if symbol.startswith("TOP2"):
        expressions.append(
            OpportunityExpression(
                expression_id=f"{symbol}-expr-peer",
                security_id="",
                basket_id=f"basket-{symbol.lower()}",
                symbol="",
                expression_type=ExpressionType.BASKET,
                role="ALTERNATIVE",
                attractiveness=0.5,
                research_confidence=0.55,
                liquidity=0.8,
                implementation_cost=0.15,
                current_actionability="RESEARCH_ONLY",
                relationship_to_thesis="DIVERSIFIED_EXPRESSION",
                supporting_evidence=("Basket expression for thesis diversification",),
                available_at=observation_time,
                validation_status=ValidationStatus.UNTESTED,
            )
        )

    unknown_claim = EvidenceClaim(
        claim_id=f"{symbol}-unknown-1",
        text="Key evidence is still unavailable.",
        claim_type="UNKNOWN",
        source=source,
        observation_time=observation_time,
        available_at=observation_time,
        confidence=0.0,
        validation_status=ValidationStatus.UNKNOWN,
        evidence_lineage=tuple(source_record_ids),
    )

    if not symbol.startswith("WEAK"):
        unknowns = ()
    else:
        unknowns = (unknown_claim,)

    return {
        "thesis_identity": ThesisIdentity(
            thesis_id=f"THESIS-{symbol}",
            thesis_name=f"{symbol} thesis",
            thesis_summary="SAMPLE_DATA thesis summary" if is_sample else "Scanner-derived thesis summary",
            thesis_type=thesis_type,
            origin=source,
            created_at=observation_time,
            observation_time=observation_time,
            available_at=observation_time,
            version="1",
            status=thesis_status,
            evidence_lineage=tuple(source_record_ids),
        ),
        "expressions": tuple(expressions),
        "lifecycle": OpportunityLifecycle(
            current_stage=lifecycle_stage,
            prior_stage=LifecycleStage.RESEARCH if lifecycle_stage != LifecycleStage.RESEARCH else LifecycleStage.DISCOVERY,
            stage_changed_at=observation_time,
            stage_reason="SAMPLE_DATA lifecycle mapping" if is_sample else "Scanner lifecycle initialization",
            required_confirmation=("Confirm liquidity and catalyst timing",),
            advancement_conditions=("Sustained confirmation across evidence",),
            regression_conditions=("Deteriorating recognition and weak breadth",),
            invalidation_conditions=("Contradictory evidence persists",),
            evidence_lineage=tuple(source_record_ids),
        ),
        "research_horizon": HorizonAssessment(
            status="QUALIFIED",
            attractiveness=0.7,
            confidence=0.7,
            expected_realization_window="1-4 quarters",
            expected_move_range="15-45%",
            downside_range="-10% to -20%",
            supporting_evidence=("Research horizon remains favorable",),
            required_confirmation=("Keep validating thesis assumptions",),
            observation_time=observation_time,
            available_at=observation_time,
            validation_status=ValidationStatus.SUPPORTED,
        ),
        "primary_repricing_horizon": HorizonAssessment(
            status=primary_status,
            attractiveness=0.6,
            confidence=0.6,
            expected_realization_window="4-12 weeks",
            expected_move_range="10-25%",
            downside_range="-8% to -15%",
            supporting_evidence=("Primary repricing evidence is developing",),
            observation_time=observation_time,
            available_at=observation_time,
            validation_status=ValidationStatus.SUPPORTED,
        ),
        "tactical_swing_horizon": HorizonAssessment(
            status=tactical_status,
            attractiveness=0.55,
            confidence=0.55,
            expected_realization_window="5-20 trading days",
            expected_move_range="5-15%",
            downside_range="-4% to -9%",
            supporting_evidence=("Tactical setup status",),
            observation_time=observation_time,
            available_at=observation_time,
            validation_status=ValidationStatus.PARTIALLY_SUPPORTED,
        ),
        "execution_horizon": HorizonAssessment(
            status=execution_status,
            attractiveness=0.45,
            confidence=0.45,
            expected_realization_window="1-10 trading days",
            expected_move_range="3-10%",
            downside_range="-3% to -7%",
            supporting_evidence=("Execution horizon intentionally independent",),
            contradictory_evidence=("Execution may lag research quality",),
            observation_time=observation_time,
            available_at=observation_time,
            validation_status=ValidationStatus.UNTESTED,
        ),
        "recognition_profile": RecognitionProfile(
            state=recognition_state,
            prior_state=RecognitionState.BEGINNING,
            direction="IMPROVING" if recognition_state not in (RecognitionState.FAILED, RecognitionState.ROLLING_OVER) else "DETERIORATING",
            velocity=0.6 if recognition_state == RecognitionState.ACCELERATING else 0.3,
            changed_at=observation_time,
            reason="Recognition profile initialization",
            evidence=("Recognition evidence from SAMPLE_DATA",),
            contradictions=("Recognition can diverge from intrinsic value",),
            required_confirmation=("Confirm breadth and follow-through",),
            invalidation="Failed follow-through",
            applicable_horizon="TACTICAL_SWING_HORIZON",
            confidence=0.6,
            validation_status=ValidationStatus.PARTIALLY_SUPPORTED,
        ),
        "claim_set": ClaimSet(
            why_now=(
                EvidenceClaim(
                    claim_id=f"{symbol}-why-now-1",
                    text="New data changed the current opportunity profile.",
                    claim_type="WHY_NOW",
                    source=source,
                    observation_time=observation_time,
                    available_at=observation_time,
                    confidence=0.7,
                    validation_status=ValidationStatus.SUPPORTED,
                    evidence_lineage=tuple(source_record_ids),
                ),
            ),
            why_not_now=contradictory_claims,
            positive_changes=(),
            negative_changes=contradictory_claims,
            missing_information=unknowns,
            required_confirmation=(
                EvidenceClaim(
                    claim_id=f"{symbol}-req-1",
                    text="Need confirmation from next evidence refresh.",
                    claim_type="REQUIRED_CONFIRMATION",
                    source=source,
                    observation_time=observation_time,
                    available_at=observation_time,
                    confidence=0.6,
                    validation_status=ValidationStatus.UNTESTED,
                    evidence_lineage=tuple(source_record_ids),
                ),
            ),
            known=(
                EvidenceClaim(
                    claim_id=f"{symbol}-known-1",
                    text="Core structural setup is known.",
                    claim_type="KNOWN",
                    source=source,
                    observation_time=observation_time,
                    available_at=observation_time,
                    confidence=0.8,
                    validation_status=ValidationStatus.SUPPORTED,
                    evidence_lineage=tuple(source_record_ids),
                ),
            ),
            unknown=unknowns,
            what_would_change_my_mind=(
                EvidenceClaim(
                    claim_id=f"{symbol}-mind-1",
                    text="Repeated contradiction in key assumptions would change conviction.",
                    claim_type="CHANGE_MIND",
                    source=source,
                    observation_time=observation_time,
                    available_at=observation_time,
                    confidence=0.7,
                    validation_status=ValidationStatus.SUPPORTED,
                    evidence_lineage=tuple(source_record_ids),
                ),
            ),
            most_sensitive_assumption="Catalyst timing remains the key sensitivity.",
        ),
        "assumptions": (
            Assumption(
                assumption_id=f"{symbol}-asm-1",
                statement="Liquidity remains sufficient for staged execution.",
                category="LIQUIDITY",
                importance=0.8,
                sensitivity=0.7,
                dependency="MARKET_PARTICIPATION",
                status=AssumptionStatus.SUPPORTED,
                supporting_evidence=("Recent volume profile",),
                contradictory_evidence=(),
                validation_status=ValidationStatus.SUPPORTED,
                last_reviewed_at=observation_time,
                invalidation_condition="Sustained liquidity decline",
            ),
            Assumption(
                assumption_id=f"{symbol}-asm-2",
                statement="Recognition can continue independent of valuation quality.",
                category="RECOGNITION",
                importance=0.6,
                sensitivity=0.6,
                dependency="FLOW",
                status=AssumptionStatus.UNTESTED,
                supporting_evidence=(),
                contradictory_evidence=(),
                validation_status=ValidationStatus.UNKNOWN,
                last_reviewed_at=observation_time,
                invalidation_condition="Negative breadth and failed follow-through",
            ),
        ),
        "invalidation_profile": InvalidationProfile(
            thesis_invalidation=("Core thesis evidence contradicted",),
            tactical_invalidation=("Tactical trigger fails and structure breaks",),
            execution_invalidation=("Execution horizon remains WAIT under adverse slippage",),
            data_invalidation=("Source lineage missing or stale",),
        ),
        "research_conviction": ConvictionAssessment(
            state=research_state,
            confidence=0.75 if research_state in (ConvictionState.HIGH, ConvictionState.VERY_HIGH) else 0.55,
            evidence=("Research thesis has adequate underwriting depth",),
            contradictions=(),
            applicable_horizon="RESEARCH_HORIZON",
            required_confirmation=("Maintain evidence consistency",),
            validation_status=ValidationStatus.SUPPORTED,
        ),
        "capital_conviction": ConvictionAssessment(
            state=capital_state,
            confidence=0.35 if capital_state == ConvictionState.LOW else 0.55,
            evidence=("Capital allocation competes with cash and alternatives",),
            contradictions=("Execution horizon may not be ready",),
            applicable_horizon="EXECUTION_HORIZON",
            required_confirmation=("Execution horizon must improve",),
            validation_status=ValidationStatus.UNTESTED,
        ),
    }


def _rolling_support_levels(bars: list[Bar]) -> list[dict[str, Any]]:
    if not bars:
        return []
    recent = bars[-min(len(bars), 10):]
    low = min(bar.low for bar in recent)
    return [{"level": low, "provenance": "rolling_low", "window": len(recent)}]


def _rolling_resistance_levels(bars: list[Bar]) -> list[dict[str, Any]]:
    if not bars:
        return []
    recent = bars[-min(len(bars), 10):]
    high = max(bar.high for bar in recent)
    return [{"level": high, "provenance": "rolling_high", "window": len(recent)}]


def _breakout_level(bars: list[Bar]) -> float:
    if not bars:
        return 0.0
    return max(bar.high for bar in bars[-min(len(bars), 5):])


def _invalidation_level(bars: list[Bar]) -> float:
    if not bars:
        return 0.0
    return min(bar.low for bar in bars[-min(len(bars), 5):])


def _classify_alignment(weekly_bars: list[Bar], daily_bars: list[Bar]) -> str:
    if not weekly_bars or not daily_bars:
        return "INSUFFICIENT_DATA"
    if len(weekly_bars) < 2 or len(daily_bars) < 2:
        return "INSUFFICIENT_DATA"
    weekly_change = weekly_bars[-1].close - weekly_bars[-2].close
    daily_change = daily_bars[-1].close - daily_bars[-2].close
    if weekly_change > 0 and daily_change > 0:
        return "ALIGNED_BULLISH"
    if weekly_change > 0 and daily_change < 0:
        return "WEEKLY_BULLISH_DAILY_PULLBACK"
    if weekly_change < 0 and daily_change > 0:
        return "WEEKLY_NEUTRAL_DAILY_BREAKOUT"
    return "CONFLICTED"
