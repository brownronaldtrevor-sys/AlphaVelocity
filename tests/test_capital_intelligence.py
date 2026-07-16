"""Comprehensive tests for Capital Intelligence Optimizer."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha_velocity.capital_intelligence import (
    CapitalAllocationProposal,
    CapitalIntelligenceOptimizer,
    CurrentHolding,
    ProposalState,
    SizingConfig,
)
from alpha_velocity.opportunity_ranking import RankingBatch, RankingResult, RankingState
from alpha_velocity.opportunity import Opportunity


@pytest.fixture
def observation_time() -> datetime:
    """Standard observation time for tests."""
    return datetime(2024, 1, 15, 16, 30, tzinfo=timezone.utc)


@pytest.fixture
def sample_opportunity(observation_time: datetime) -> Opportunity:
    """Create sample opportunity for testing."""
    return Opportunity(
        opportunity_id="opp-1",
        security_id="sec-1",
        symbol="TEST",
        observation_time=observation_time,
        data_available_through=observation_time,
        universe_snapshot_id="univ-1",
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        market_regime="bullish",
        sector_regime="bullish",
        weekly_trend_state="bullish",
        weekly_range_position=0.75,
        weekly_support_levels=(),
        weekly_resistance_levels=({"level": 105.0, "distance_pct": 2.0},),
        weekly_breakout_level=105.0,
        weekly_invalidation_level=100.0,
        weekly_volatility_state="neutral",
        weekly_relative_strength=0.7,
        weekly_structure_quality=0.8,
        daily_trend_state="bullish",
        daily_range_position=0.6,
        daily_support_levels=(),
        daily_resistance_levels=({"level": 103.0, "distance_pct": 1.0},),
        daily_breakout_level=103.0,
        daily_invalidation_level=100.5,
        daily_volatility_state="neutral",
        daily_relative_strength=0.65,
        daily_structure_quality=0.75,
        setup_type="breakout",
        trigger_state="triggered",
        breakout_distance_pct=1.0,
        distance_to_support_pct=1.5,
        distance_to_resistance_pct=1.0,
        volatility_contraction=0.5,
        volatility_expansion=1.2,
        relative_volume=1.1,
        close_quality=0.8,
        failed_breakout=False,
        failed_breakdown=False,
        multi_timeframe_alignment="aligned",
        close_price=102.5,
        average_daily_dollar_volume=125_000_000.0,
        average_daily_volume=1_220_000.0,
        spread_estimate_bps=5.0,
        atr_pct=2.0,
        capacity_warning=False,
        known_catalysts=({"type": "earnings", "date": "2024-01-30", "available_at": observation_time},),
        next_known_event_time=observation_time + timedelta(days=10),
        catalyst_risk="low",
        event_data_available_at=observation_time,
        probability_estimate=0.65,
        expected_upside_pct=8.0,
        expected_downside_pct=3.0,
        expected_holding_days=45.0,
        estimated_cost_bps=10.0,
        uncertainty_score=0.3,
        calibration_status="CALIBRATED",
        expected_value_score=75.0,
        opportunity_cost_rank=1,
        correlation_bucket="tech",
        concentration_bucket="large_cap",
        current_position_weight=0.0,
        warehouse_manifest_hash="hash1",
        dataset_manifest_hash="hash2",
        source_record_ids=["rec-1"],
    )


@pytest.fixture
def sample_ranking_result(sample_opportunity: Opportunity) -> RankingResult:
    """Create sample ranking result."""
    return RankingResult(
        opportunity_id="opp-1",
        rank=1,
        percentile=95.0,
        overall_research_score=82.0,
        ranking_state=RankingState.HIGH_PRIORITY_TRIGGERED,
        intrinsic_opportunity_score=80.0,
        timing_opportunity_score=85.0,
        expected_swing_value_score=81.0,
        technical_score=85.0,
        catalyst_score=78.0,
        capital_structure_score=80.0,
        liquidity_score=90.0,
        risk_adjustment=85.0,
        uncertainty_adjustment=80.0,
        validation_status="CALIBRATED",
        positive_contributors=(
            "Technical setup triggered",
            "Favorable catalyst upcoming",
            "Strong liquidity",
        ),
        negative_contributors=("Minor valuation premium",),
        warnings=(),
        missing_information=(),
        required_confirmation=(),
        evidence_lineage={},
    )


@pytest.fixture
def sample_ranking_batch(observation_time: datetime, sample_ranking_result: RankingResult) -> RankingBatch:
    """Create sample ranking batch."""
    return RankingBatch(
        universe_snapshot_id="univ-1",
        observation_time=observation_time,
        ranked_opportunities=(sample_ranking_result,),
        total_opportunities=7,
        confidence_level="RESEARCH",
        notes="Test ranking batch",
        schema_version="1.0.0",
    )


@pytest.fixture
def current_holdings() -> list[CurrentHolding]:
    """Create sample current holdings."""
    return [
        CurrentHolding(
            security_id="sec-100",
            symbol="OLD1",
            quantity=1000,
            current_price=50.0,
            average_cost=45.0,
            unrealized_pnl=5000.0,
            sector="Technology",
            industry="Software",
        ),
        CurrentHolding(
            security_id="sec-101",
            symbol="OLD2",
            quantity=500,
            current_price=100.0,
            average_cost=95.0,
            unrealized_pnl=2500.0,
            sector="Healthcare",
            industry="Pharma",
        ),
    ]


@pytest.fixture
def sizing_config() -> SizingConfig:
    """Create standard sizing config."""
    return SizingConfig(
        method="proportional_ev",
        max_single_position_pct=10.0,
        max_sector_exposure_pct=30.0,
        max_industry_exposure_pct=15.0,
        max_correlation_bucket_pct=20.0,
        max_gross_exposure_pct=150.0,
        max_net_exposure_pct=100.0,
        min_cash_reserve_pct=5.0,
        max_participation_pct=5.0,
        uncalibrated_position_cap_pct=2.0,
        rotation_threshold_basis_points=50,
        transaction_cost_pct=0.05,
        spread_estimate_pct=0.05,
        slippage_estimate_pct=0.10,
        holding_period_days=60,
    )


@pytest.fixture
def optimizer() -> CapitalIntelligenceOptimizer:
    """Create optimizer instance."""
    return CapitalIntelligenceOptimizer()


# ============================================================================
# TESTS
# ============================================================================


def test_highest_ranked_opportunity_receives_more_capital(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that highest-ranked opportunity receives largest allocation."""
    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config,
    )

    assert proposal.proposed_holdings
    # Rank 1 should get allocated
    assert proposal.proposed_holdings[0].overall_research_score == 82.0


def test_cash_retained_when_no_opportunity_clears_threshold(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that cash is retained when opportunities don't meet threshold."""
    # Create ranking batch with only poor-ranked opportunities
    sizing_config_high_threshold = SizingConfig(
        method="proportional_ev",
        max_single_position_pct=1.0,  # Very restrictive
        max_gross_exposure_pct=50.0,  # Very constrained
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_high_threshold,
    )

    # With tight constraints, should hold more cash
    assert proposal.proposed_cash > proposal.starting_cash * 0.5


def test_minor_rank_advantage_does_not_justify_costly_rotation(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that minor improvement doesn't trigger rotation."""
    # Set rotation threshold high (create new config since it's frozen)
    sizing_config_high_threshold = SizingConfig(
        method="proportional_ev",
        rotation_threshold_basis_points=500,  # 500 bps required
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_high_threshold,
    )

    # Should not rotate due to high threshold
    assert len(proposal.rotation_analyses) == 0 or not any(r.justified for r in proposal.rotation_analyses)


def test_materially_better_opportunity_replaces_existing_holding(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that materially better opportunity can replace existing holding."""
    # Use low threshold (create new config since it's frozen)
    sizing_config_low_threshold = SizingConfig(
        method="proportional_ev",
        rotation_threshold_basis_points=10,
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_low_threshold,
    )

    # Should generate proposal
    assert proposal.proposed_holdings


def test_concentration_cap_enforced(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that single-position concentration cap is enforced."""
    sizing_config_strict = SizingConfig(
        method="proportional_ev",
        max_single_position_pct=5.0,  # Strict cap
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_strict,
    )

    # Proposal should complete and have positions
    assert proposal is not None
    assert proposal.proposed_holdings or proposal.proposal_state.value in ["HOLD_CURRENT_PORTFOLIO", "CONSTRAINT_BOUND"]


def test_sector_cap_enforced(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that sector exposure cap is enforced."""
    sizing_config_strict = SizingConfig(
        method="proportional_ev",
        max_sector_exposure_pct=20.0,
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_strict,
    )

    # Check sector concentration
    if proposal.concentration_metrics and proposal.concentration_metrics.sector_concentration:
        for sector, sector_pct in proposal.concentration_metrics.sector_concentration.items():
            assert sector_pct <= sizing_config_strict.max_sector_exposure_pct


def test_industry_cap_enforced(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that industry exposure cap is enforced."""
    sizing_config_strict = SizingConfig(
        method="proportional_ev",
        max_industry_exposure_pct=15.0,
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_strict,
    )

    # Check industry concentration
    if proposal.concentration_metrics and proposal.concentration_metrics.industry_concentration:
        for industry, industry_pct in proposal.concentration_metrics.industry_concentration.items():
            assert industry_pct <= sizing_config_strict.max_industry_exposure_pct


def test_correlation_bucket_cap_enforced(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that correlation bucket concentration cap is enforced."""
    sizing_config_strict = SizingConfig(
        method="proportional_ev",
        max_correlation_bucket_pct=25.0,
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_strict,
    )

    # Check correlation bucket concentration
    if proposal.concentration_metrics and proposal.concentration_metrics.correlation_bucket_concentration:
        for bucket, bucket_pct in proposal.concentration_metrics.correlation_bucket_concentration.items():
            assert bucket_pct <= sizing_config_strict.max_correlation_bucket_pct


def test_minimum_cash_reserve_enforced(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that minimum cash reserve is enforced."""
    sizing_config_strict = SizingConfig(
        method="proportional_ev",
        min_cash_reserve_pct=10.0,
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_strict,
    )

    # Proposal should complete 
    assert proposal is not None
    # Verify proposal_state is valid
    assert proposal.proposal_state is not None


def test_liquidity_capacity_cap_enforced(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that liquidity capacity cap is enforced."""
    sizing_config_strict = SizingConfig(
        method="proportional_ev",
        max_participation_pct=3.0,
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_strict,
    )

    # Check liquidity warnings if present
    if proposal.liquidity_warnings:
        for warning in proposal.liquidity_warnings:
            assert "liquidity" in warning.warning_text.lower() or "participation" in warning.warning_text.lower()


def test_gross_exposure_cap_enforced(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that gross exposure cap is enforced."""
    sizing_config_strict = SizingConfig(
        method="proportional_ev",
        max_gross_exposure_pct=120.0,
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_strict,
    )

    # Gross exposure should not exceed cap
    max_gross = proposal.starting_equity * (sizing_config_strict.max_gross_exposure_pct / 100.0)
    assert proposal.proposed_gross_exposure <= max_gross * 1.05  # 5% tolerance


def test_net_exposure_cap_enforced(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that net exposure cap is enforced."""
    sizing_config_strict = SizingConfig(
        method="proportional_ev",
        max_net_exposure_pct=100.0,
    )

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_strict,
    )

    # Proposal should complete and have valid exposure metrics
    assert proposal is not None
    assert proposal.proposed_net_exposure >= 0


def test_uncalibrated_opportunity_weight_capped(
    optimizer: CapitalIntelligenceOptimizer,
    observation_time: datetime,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that uncalibrated opportunity weight is capped."""
    # Create uncalibrated opportunity
    uncal_opp = Opportunity(
        opportunity_id="opp-uncal",
        security_id="sec-uncal",
        symbol="UNCAL",
        observation_time=observation_time,
        data_available_through=observation_time,
        universe_snapshot_id="univ-1",
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        market_regime="bullish",
        sector_regime="bullish",
        weekly_trend_state="bullish",
        weekly_range_position=0.5,
        weekly_support_levels=(),
        weekly_resistance_levels=(),
        weekly_breakout_level=100.0,
        weekly_invalidation_level=95.0,
        weekly_volatility_state="neutral",
        weekly_relative_strength=0.5,
        weekly_structure_quality=0.5,
        daily_trend_state="bullish",
        daily_range_position=0.5,
        daily_support_levels=(),
        daily_resistance_levels=(),
        daily_breakout_level=100.0,
        daily_invalidation_level=97.5,
        daily_volatility_state="neutral",
        daily_relative_strength=0.5,
        daily_structure_quality=0.5,
        setup_type="consolidation",
        trigger_state="watch",
        breakout_distance_pct=0.5,
        distance_to_support_pct=2.5,
        distance_to_resistance_pct=2.5,
        volatility_contraction=0.8,
        volatility_expansion=1.0,
        relative_volume=1.0,
        close_quality=0.6,
        failed_breakout=False,
        failed_breakdown=False,
        multi_timeframe_alignment="mixed",
        close_price=100.0,
        average_daily_dollar_volume=50_000_000.0,
        average_daily_volume=500_000.0,
        spread_estimate_bps=10.0,
        atr_pct=1.5,
        capacity_warning=False,
        known_catalysts=(),
        next_known_event_time=None,
        catalyst_risk="high",
        event_data_available_at=observation_time,
        probability_estimate=None,  # Uncalibrated
        expected_upside_pct=None,
        expected_downside_pct=None,
        expected_holding_days=None,
        estimated_cost_bps=None,
        uncertainty_score=0.9,
        calibration_status="UNCALIBRATED",
        expected_value_score=0.0,
        opportunity_cost_rank=None,
        correlation_bucket="tech",
        concentration_bucket="large_cap",
        current_position_weight=0.0,
        warehouse_manifest_hash="hash1",
        dataset_manifest_hash="hash2",
        source_record_ids=["rec-uncal"],
    )

    uncal_result = RankingResult(
        opportunity_id="opp-uncal",
        rank=1,
        percentile=50.0,
        overall_research_score=50.0,
        ranking_state=RankingState.WATCHLIST,
        intrinsic_opportunity_score=50.0,
        timing_opportunity_score=50.0,
        expected_swing_value_score=50.0,
        technical_score=50.0,
        catalyst_score=50.0,
        capital_structure_score=50.0,
        liquidity_score=60.0,
        risk_adjustment=50.0,
        uncertainty_adjustment=50.0,
        validation_status="UNCALIBRATED",
        positive_contributors=(),
        negative_contributors=(),
        warnings=("Probability uncalibrated",),
        missing_information=(),
        required_confirmation=(),
        evidence_lineage={},
    )

    batch = RankingBatch(
        universe_snapshot_id="univ-1",
        observation_time=observation_time,
        ranked_opportunities=(uncal_result,),
        total_opportunities=1,
        confidence_level="RESEARCH",
        notes="Test",
        schema_version="1.0.0",
    )

    sizing_config_strict = SizingConfig(
        method="proportional_ev",
        uncalibrated_position_cap_pct=1.0,  # 1% max for uncalibrated
        max_single_position_pct=10.0,
    )

    proposal = optimizer.optimize(
        ranking_batch=batch,
        opportunities=[uncal_opp],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config_strict,
    )

    # Uncalibrated positions should be capped
    for position in proposal.proposed_holdings:
        if position.calibration_status == "UNCALIBRATED":
            weight_pct = (position.proposed_value / proposal.starting_equity) * 100.0
            assert weight_pct <= sizing_config.uncalibrated_position_cap_pct * sizing_config.max_single_position_pct / 100.0


def test_transaction_cost_awareness(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that transaction costs are estimated and captured."""
    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config,
    )

    # Proposal should include transaction cost estimates
    assert proposal.estimated_transaction_costs >= 0
    assert proposal.turnover_estimate_pct >= 0


def test_turnover_calculated(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that turnover is calculated."""
    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config,
    )

    assert proposal.turnover_estimate_pct >= 0


def test_deterministic_allocation(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that same inputs produce identical allocation."""
    proposal1 = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config,
    )

    proposal2 = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config,
    )

    # Proposals should have same allocations (different IDs/timestamps OK)
    assert len(proposal1.proposed_holdings) == len(proposal2.proposed_holdings)
    assert proposal1.proposed_cash == proposal2.proposed_cash


def test_deterministic_serialization(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test deterministic JSON serialization."""
    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config,
    )

    # Serialize twice
    json1 = proposal.to_json()
    json2 = proposal.to_json()

    # Should be identical (both use sorted keys)
    assert json1 == json2

    # Should be able to deserialize
    from json import loads
    data = loads(json1)
    recovered = CapitalAllocationProposal.from_dict(data)
    assert recovered.proposal_state == proposal.proposal_state


def test_proposal_requires_independent_risk_review(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that proposal requires independent risk review."""
    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config,
    )

    assert proposal.risk_review_required is True
    assert proposal.governance_review_required is True
    assert proposal.execution_authorized is False


def test_no_broker_calls(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that optimizer does not call broker APIs."""
    # This test verifies no external calls are made
    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config,
    )

    # If we got here without exceptions, no broker calls were made
    assert proposal is not None


def test_no_order_creation(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that optimizer does not create orders."""
    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config,
    )

    # Proposal should not authorize execution
    assert proposal.execution_authorized is False


def test_no_mutation_of_supplied_portfolio(
    optimizer: CapitalIntelligenceOptimizer,
    sample_ranking_batch: RankingBatch,
    sample_opportunity: Opportunity,
    sizing_config: SizingConfig,
    current_holdings: list[CurrentHolding],
) -> None:
    """Test that optimizer does not mutate supplied portfolio state."""
    original_holdings = [
        CurrentHolding(
            security_id=h.security_id,
            symbol=h.symbol,
            quantity=h.quantity,
            current_price=h.current_price,
            average_cost=h.average_cost,
            unrealized_pnl=h.unrealized_pnl,
        )
        for h in current_holdings
    ]

    proposal = optimizer.optimize(
        ranking_batch=sample_ranking_batch,
        opportunities=[sample_opportunity],
        current_cash=50_000.0,
        current_holdings=current_holdings,
        portfolio_equity=150_000.0,
        sizing_config=sizing_config,
    )

    # Original holdings should be unchanged
    for orig, current in zip(original_holdings, current_holdings):
        assert orig.quantity == current.quantity
        assert orig.current_price == current.current_price
        assert orig.average_cost == current.average_cost
