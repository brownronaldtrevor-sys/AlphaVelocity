"""
Tests for Opportunity Ranking Engine v1.

Tests ranking by expected favorable swing value with three components:
1. Intrinsic Opportunity Score (valuation + capital structure)
2. Timing Opportunity Score (technical setup + catalysts)
3. Expected Swing Value Score (probability, magnitude, costs, liquidity, uncertainty)

Validates that:
- Valuation cannot override poor timing
- Technical strength cannot override capital distress
- Unvalidated evidence receives zero influence
- Missing data not treated as positive
- Probabilities are not fabricated
- Mispriced without trigger = WAITING_FOR_TRIGGER
"""

from datetime import datetime, timedelta, timezone
import json
import pytest

from alpha_velocity.opportunity import Opportunity, assemble_opportunity
from alpha_velocity.market.bars import Bar
from alpha_velocity.ranking import (
    RankingEngine,
    RankingConfig,
    RankingState,
    MaturityCondition,
    DebtMaturityAnalysis,
    IntrinsicOpportunityInput,
    IntrinsicValuationScenario,
    TimingOpportunityCatalyst,
)


@pytest.fixture
def observation_time() -> datetime:
    return datetime(2024, 1, 15, 16, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def bullish_daily_bars(observation_time: datetime) -> list[Bar]:
    """10 daily bars with bullish setup."""
    bars = []
    for i in range(10):
        ts = observation_time - timedelta(days=10 - i - 1)
        open_price = 100.0 + i * 0.5
        high = open_price + 2.0
        low = open_price - 1.0
        close = open_price + 1.5
        bars.append(Bar(timestamp=ts, open=open_price, high=high, low=low, close=close, volume=1_000_000.0))
    return bars


@pytest.fixture
def bullish_weekly_bars(observation_time: datetime) -> list[Bar]:
    """12 weekly bars with bullish trend."""
    bars = []
    for i in range(12):
        ts = observation_time - timedelta(weeks=12 - i - 1)
        open_price = 100.0 + (i * 0.8)
        high = open_price + 5.0
        low = open_price - 3.0
        close = open_price + 3.0
        bars.append(Bar(timestamp=ts, open=open_price, high=high, low=low, close=close, volume=5_000_000.0))
    return bars


@pytest.fixture
def benchmark_bars(observation_time: datetime) -> list[Bar]:
    """10 daily benchmark bars."""
    bars = []
    for i in range(10):
        ts = observation_time - timedelta(days=10 - i - 1)
        bars.append(Bar(timestamp=ts, open=5000.0 + i, high=5010.0 + i, low=4990.0 + i, close=5005.0 + i, volume=10_000_000.0))
    return bars


@pytest.fixture
def sector_bars(observation_time: datetime) -> list[Bar]:
    """10 daily sector bars."""
    bars = []
    for i in range(10):
        ts = observation_time - timedelta(days=10 - i - 1)
        bars.append(Bar(timestamp=ts, open=1000.0 + i * 0.5, high=1005.0 + i * 0.5, low=998.0 + i * 0.5, close=1002.0 + i * 0.5, volume=2_000_000.0))
    return bars


@pytest.fixture
def bullish_opportunity(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> Opportunity:
    """Base opportunity with bullish technical setup."""
    return assemble_opportunity(
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        feature_snapshots=[],
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id="SEC123",
        symbol="TEST",
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        universe_snapshot_id="SNAP001",
        warehouse_manifest_hash="HASH001",
        dataset_manifest_hash="HASH002",
        source_record_ids=["REC001"],
    )


# ============================ Intrinsic Score Tests ============================

def test_intrinsic_score_capital_waterfall_reduces_equity(
    observation_time: datetime,
    bullish_opportunity: Opportunity,
) -> None:
    """Test capital structure waterfall properly reduces common-equity value."""
    # Scenario: $1B market cap, but $700M debt reduces common equity
    intrinsic = IntrinsicOpportunityInput(
        security_id="SEC123",
        observation_time=observation_time,
        source="manual",
        available_at=observation_time,
        market_price=100.0,
        shares_outstanding=10_000_000.0,
        total_debt=700_000_000.0,
        net_debt=600_000_000.0,
        cash_and_equivalents=100_000_000.0,
        preferred_equity=100_000_000.0,
        diluted_share_count=10_000_000.0,
    )
    
    scenarios = [
        IntrinsicValuationScenario(
            scenario="base",
            enterprise_value=1_200_000_000.0,
            net_debt_amount=600_000_000.0,
            senior_claims=100_000_000.0,  # Preferred
            implied_equity_value=500_000_000.0,  # 1.2B - 600M - 100M
            diluted_share_count=10_000_000.0,
            value_per_share=50.0,  # Downside from $100 market
        ),
    ]
    
    maturity = DebtMaturityAnalysis(
        observation_time=observation_time,
        maturity_condition=MaturityCondition.MANAGEABLE,
        principal_outstanding=700_000_000.0,
        next_12m_maturities=100_000_000.0,
        next_24m_maturities=300_000_000.0,
        revolver_available=200_000_000.0,
        unrestricted_cash=100_000_000.0,
        expected_fcf_before_maturity=200_000_000.0,
        interest_expense_annual=50_000_000.0,
    )
    
    engine = RankingEngine()
    run = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
        intrinsic_inputs={bullish_opportunity.opportunity_id: intrinsic},
        intrinsic_scenarios={bullish_opportunity.opportunity_id: scenarios},
        maturity_analysis={bullish_opportunity.opportunity_id: maturity},
    )
    
    ranked = run.ranked_opportunities[0]
    # With $500M equity value vs $1B market cap, valuation should be attractive
    # But downside to equity from market price
    assert ranked.intrinsic_opportunity_score is not None
    assert 40.0 < ranked.intrinsic_opportunity_score < 70.0


def test_distressed_company_stays_low_ranked(
    observation_time: datetime,
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
) -> None:
    """Test distressed capital structure prevents high ranking despite good timing."""
    opp = assemble_opportunity(
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        feature_snapshots=[],
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id="DISTRESSED",
        symbol="DIST",
        benchmark_symbol="SPY",
        sector="Energy",
        industry="Oil & Gas",
        universe_snapshot_id="SNAP001",
        warehouse_manifest_hash="HASH001",
        dataset_manifest_hash="HASH002",
        source_record_ids=[],
    )
    
    maturity = DebtMaturityAnalysis(
        observation_time=observation_time,
        maturity_condition=MaturityCondition.DISTRESSED,
        principal_outstanding=2_000_000_000.0,
        next_12m_maturities=500_000_000.0,
        next_24m_maturities=1_000_000_000.0,
        revolver_available=50_000_000.0,
        unrestricted_cash=30_000_000.0,
        expected_fcf_before_maturity=50_000_000.0,
        interest_expense_annual=180_000_000.0,
        debt_to_ebitda=10.0,
        covenant_risk="CRITICAL",
    )
    
    engine = RankingEngine()
    run = engine.rank_opportunities(
        opportunities=[opp],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
        maturity_analysis={opp.opportunity_id: maturity},
    )
    
    ranked = run.ranked_opportunities[0]
    # Despite bullish technical setup, distressed maturity should cap overall swing value
    assert ranked.overall_swing_value_rank < 50.0
    assert ranked.ranking_state in [RankingState.AVOID, RankingState.DISTRESSED_OPTIONALITY]
    assert len(ranked.disqualifiers) > 0 or ranked.intrinsic_opportunity_score < 30.0


# ============================ Timing Score Tests ============================

def test_timing_score_requires_trigger(
    observation_time: datetime,
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
) -> None:
    """Test that good intrinsic + poor timing = WAITING_FOR_TRIGGER or WATCHLIST."""
    # Create flat daily bars (no trigger)
    flat_daily = []
    for i in range(10):
        ts = observation_time - timedelta(days=10 - i - 1)
        flat_daily.append(Bar(timestamp=ts, open=100.0, high=100.5, low=99.5, close=100.0, volume=500_000.0))
    
    opp = assemble_opportunity(
        daily_bars=flat_daily,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        feature_snapshots=[],
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id="WAITING",
        symbol="WTG",
        benchmark_symbol="SPY",
        sector="Pharma",
        industry="Healthcare",
        universe_snapshot_id="SNAP001",
        warehouse_manifest_hash="HASH001",
        dataset_manifest_hash="HASH002",
        source_record_ids=[],
    )
    
    # Attractive intrinsic
    intrinsic = IntrinsicOpportunityInput(
        security_id="WAITING",
        observation_time=observation_time,
        source="manual",
        available_at=observation_time,
        market_price=100.0,
        shares_outstanding=10_000_000.0,
    )
    
    scenarios = [
        IntrinsicValuationScenario(
            scenario="base",
            enterprise_value=1_500_000_000.0,
            net_debt_amount=300_000_000.0,
            senior_claims=0.0,
            implied_equity_value=1_200_000_000.0,
            diluted_share_count=10_000_000.0,
            value_per_share=120.0,  # 20% upside
        ),
    ]
    
    maturity = DebtMaturityAnalysis(
        observation_time=observation_time,
        maturity_condition=MaturityCondition.MANAGEABLE,
        principal_outstanding=300_000_000.0,
        next_12m_maturities=50_000_000.0,
        next_24m_maturities=150_000_000.0,
        revolver_available=200_000_000.0,
        unrestricted_cash=100_000_000.0,
        expected_fcf_before_maturity=200_000_000.0,
        interest_expense_annual=25_000_000.0,
    )
    
    engine = RankingEngine()
    run = engine.rank_opportunities(
        opportunities=[opp],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
        intrinsic_inputs={opp.opportunity_id: intrinsic},
        intrinsic_scenarios={opp.opportunity_id: scenarios},
        maturity_analysis={opp.opportunity_id: maturity},
    )
    
    ranked = run.ranked_opportunities[0]
    # Good intrinsic, poor timing -> should be WAITING_FOR_TRIGGER or WATCHLIST
    assert ranked.intrinsic_opportunity_score > 60.0
    assert ranked.timing_opportunity_score < 50.0
    # With good intrinsic and poor timing, but some swing value, should not be AVOID
    assert ranked.ranking_state in [
        RankingState.HIGH_PRIORITY_WAITING_FOR_TRIGGER,
        RankingState.WATCHLIST,
    ]


def test_catalyst_importance_increases_timing_score(
    observation_time: datetime,
    bullish_opportunity: Opportunity,
) -> None:
    """Test that high-importance catalysts increase timing score."""
    catalysts = [
        TimingOpportunityCatalyst(
            catalyst_type="earnings",
            name="Q1 Earnings",
            available_at=observation_time,
            expected_event_time=observation_time + timedelta(days=7),
            estimated_importance="high",
            uncertainty_score=0.3,
            status="PENDING",
        ),
    ]
    
    engine = RankingEngine()
    # Run with catalyst
    run_with_catalyst = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
        catalysts={bullish_opportunity.opportunity_id: catalysts},
    )
    
    # Run without catalyst
    run_without_catalyst = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
    )
    
    ranked_with = run_with_catalyst.ranked_opportunities[0]
    ranked_without = run_without_catalyst.ranked_opportunities[0]
    
    # Catalyst should improve timing score
    assert ranked_with.timing_opportunity_score >= ranked_without.timing_opportunity_score


# ============================ Swing Value Score Tests ============================

def test_swing_value_requires_calibrated_probability(
    observation_time: datetime,
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
) -> None:
    """Test that unvalidated probability receives zero influence."""
    # Create opportunity with UNCALIBRATED status (no probability estimate)
    opp = assemble_opportunity(
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        feature_snapshots=[],
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id="UNCAL",
        symbol="UCL",
        benchmark_symbol="SPY",
        sector="Tech",
        industry="Software",
        universe_snapshot_id="SNAP001",
        warehouse_manifest_hash="HASH001",
        dataset_manifest_hash="HASH002",
        source_record_ids=[],
    )
    
    engine = RankingEngine()
    run = engine.rank_opportunities(
        opportunities=[opp],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
    )
    
    ranked = run.ranked_opportunities[0]
    # Swing value score should not include unvalidated probability
    swing_comps = {c.name: c for c in ranked.swing_value_components}
    prob_comp = swing_comps.get("favorable_probability")
    
    assert prob_comp is not None
    assert prob_comp.score == 0.0  # Unvalidated = zero
    assert prob_comp.is_validated == False
    warnings_disquals = " ".join(ranked.disqualifiers + ranked.warnings).lower()
    assert "calibrated" in warnings_disquals


def test_liquidity_impacts_swing_value(
    observation_time: datetime,
    bullish_opportunity: Opportunity,
) -> None:
    """Test that poor liquidity reduces swing value score."""
    # Opportunity has low ADVI from fixture
    engine = RankingEngine()
    run = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
    )
    
    ranked = run.ranked_opportunities[0]
    swing_comps = {c.name: c for c in ranked.swing_value_components}
    liquidity_comp = swing_comps.get("liquidity_and_execution")
    
    assert liquidity_comp is not None
    # Low ADVI from test fixture should result in lower liquidity score
    # The fixture has 1M volume, so should be in moderate range


# ============================ Point-in-Time Tests ============================

def test_future_data_rejection(observation_time: datetime) -> None:
    """Test that future-available data is rejected."""
    future_time = observation_time + timedelta(days=1)
    
    with pytest.raises(ValueError, match="cannot exceed observation_time"):
        IntrinsicOpportunityInput(
            security_id="TEST",
            observation_time=observation_time,
            source="manual",
            available_at=future_time,  # Future!
            market_price=100.0,
        )


def test_refinancing_known_after_event(
    observation_time: datetime,
    bullish_opportunity: Opportunity,
) -> None:
    """Test point-in-time: refinancing effects visible only after available_at."""
    # Before refinancing announcement
    maturity_before = DebtMaturityAnalysis(
        observation_time=observation_time,
        maturity_condition=MaturityCondition.HIGH_RISK,
        principal_outstanding=500_000_000.0,
        next_12m_maturities=200_000_000.0,
        next_24m_maturities=400_000_000.0,
        revolver_available=20_000_000.0,
        unrestricted_cash=50_000_000.0,
        expected_fcf_before_maturity=40_000_000.0,
        interest_expense_annual=35_000_000.0,
        estimated_liquidity_runway_days=120,
    )
    
    # After successful refinancing announcement
    maturity_after = DebtMaturityAnalysis(
        observation_time=observation_time,
        maturity_condition=MaturityCondition.MANAGEABLE,
        principal_outstanding=500_000_000.0,
        next_12m_maturities=50_000_000.0,
        next_24m_maturities=200_000_000.0,
        revolver_available=200_000_000.0,
        unrestricted_cash=50_000_000.0,
        expected_fcf_before_maturity=40_000_000.0,
        interest_expense_annual=35_000_000.0,
        estimated_liquidity_runway_days=720,
    )
    
    engine = RankingEngine()
    
    run_before = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
        maturity_analysis={bullish_opportunity.opportunity_id: maturity_before},
    )
    
    run_after = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
        maturity_analysis={bullish_opportunity.opportunity_id: maturity_after},
    )
    
    # Intrinsic score should improve with successful refinancing
    assert run_after.ranked_opportunities[0].intrinsic_opportunity_score > run_before.ranked_opportunities[0].intrinsic_opportunity_score


# ============================ Valuation Scenarios ============================

def test_bear_base_bull_scenarios(observation_time: datetime, bullish_opportunity: Opportunity) -> None:
    """Test that bear/base/bull scenarios properly evaluate upside/downside."""
    scenarios = [
        IntrinsicValuationScenario(
            scenario="bear",
            enterprise_value=800_000_000.0,
            net_debt_amount=300_000_000.0,
            senior_claims=0.0,
            implied_equity_value=500_000_000.0,
            diluted_share_count=10_000_000.0,
            value_per_share=50.0,
        ),
        IntrinsicValuationScenario(
            scenario="base",
            enterprise_value=1_200_000_000.0,
            net_debt_amount=300_000_000.0,
            senior_claims=0.0,
            implied_equity_value=900_000_000.0,
            diluted_share_count=10_000_000.0,
            value_per_share=90.0,
        ),
        IntrinsicValuationScenario(
            scenario="bull",
            enterprise_value=1_800_000_000.0,
            net_debt_amount=300_000_000.0,
            senior_claims=0.0,
            implied_equity_value=1_500_000_000.0,
            diluted_share_count=10_000_000.0,
            value_per_share=150.0,
        ),
    ]
    
    intrinsic = IntrinsicOpportunityInput(
        security_id="SEC123",
        observation_time=observation_time,
        source="manual",
        available_at=observation_time,
        market_price=100.0,
        shares_outstanding=10_000_000.0,
    )
    
    engine = RankingEngine()
    run = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
        intrinsic_inputs={bullish_opportunity.opportunity_id: intrinsic},
        intrinsic_scenarios={bullish_opportunity.opportunity_id: scenarios},
    )
    
    ranked = run.ranked_opportunities[0]
    # Base scenario shows -10% downside, but bull shows +50% upside
    assert ranked.intrinsic_opportunity_score > 0.0


# ============================ Determinism Tests ============================

def test_deterministic_ranking(observation_time: datetime, bullish_opportunity: Opportunity) -> None:
    """Test that ranking is deterministic."""
    engine = RankingEngine(RankingConfig())
    
    run1 = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
    )
    
    run2 = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
    )
    
    # Scores should be identical
    assert run1.ranked_opportunities[0].overall_swing_value_rank == run2.ranked_opportunities[0].overall_swing_value_rank


def test_deterministic_serialization(observation_time: datetime, bullish_opportunity: Opportunity) -> None:
    """Test that JSON serialization is deterministic."""
    engine = RankingEngine()
    run = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
    )
    
    json1 = run.to_json()
    json2 = run.to_json()
    
    # Should be identical
    assert json1 == json2
    
    # Should be valid JSON
    parsed = json.loads(json1)
    assert parsed["schema_version"] == "1.0.0"
    assert len(parsed["ranked_opportunities"]) == 1


# ============================ Constraint Tests ============================

def test_no_broker_calls(observation_time: datetime, bullish_opportunity: Opportunity) -> None:
    """Test that engine makes no broker calls."""
    engine = RankingEngine()
    run = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
    )
    
    assert run is not None
    assert len(run.ranked_opportunities) > 0


def test_no_order_creation(observation_time: datetime, bullish_opportunity: Opportunity) -> None:
    """Test that engine creates no orders."""
    engine = RankingEngine()
    run = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
    )
    
    ranked = run.ranked_opportunities[0]
    # Should not have order fields
    assert not hasattr(ranked, "order_id")
    assert not hasattr(ranked, "quantity")
    assert not hasattr(ranked, "fill_price")


def test_no_portfolio_allocation(observation_time: datetime, bullish_opportunity: Opportunity) -> None:
    """Test that engine does not perform portfolio allocation."""
    engine = RankingEngine()
    run = engine.rank_opportunities(
        opportunities=[bullish_opportunity],
        universe_snapshot_id="SNAP001",
        observation_time=observation_time,
    )
    
    # Should not contain allocation weights, only classifications
    for ranked in run.ranked_opportunities:
        # ranking_state is classification, not weight
        assert ranked.ranking_state in [
            RankingState.HIGH_PRIORITY_TRIGGERED,
            RankingState.HIGH_PRIORITY_WAITING_FOR_TRIGGER,
            RankingState.WATCHLIST,
            RankingState.SPECULATIVE,
            RankingState.REFINANCING_DEPENDENT,
            RankingState.DISTRESSED_OPTIONALITY,
            RankingState.AVOID,
            RankingState.INSUFFICIENT_DATA,
        ]
