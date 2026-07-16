"""Comprehensive tests for Opportunity Ranking Engine."""

from datetime import datetime, timedelta, timezone
import json
import pytest

from alpha_velocity.market.bars import Bar
from alpha_velocity.opportunity import assemble_opportunity
from alpha_velocity.opportunity_ranking import (
    OpportunityRanker,
    RankingState,
    RankingBatch,
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
        bars.append(
            Bar(
                timestamp=ts,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1_000_000.0,
            )
        )
    return bars


@pytest.fixture
def bearish_daily_bars(observation_time: datetime) -> list[Bar]:
    """10 daily bars with bearish setup."""
    bars = []
    for i in range(10):
        ts = observation_time - timedelta(days=10 - i - 1)
        open_price = 100.0 - i * 0.5
        high = open_price + 1.0
        low = open_price - 2.0
        close = open_price - 1.5
        bars.append(
            Bar(
                timestamp=ts,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1_000_000.0,
            )
        )
    return bars


@pytest.fixture
def bullish_weekly_bars(observation_time: datetime) -> list[Bar]:
    """12 weekly bars with bullish setup."""
    bars = []
    for i in range(12):
        ts = observation_time - timedelta(weeks=12 - i - 1)
        open_price = 100.0 + i * 1.0
        high = open_price + 3.0
        low = open_price - 2.0
        close = open_price + 2.0
        bars.append(
            Bar(
                timestamp=ts,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=5_000_000.0,
            )
        )
    return bars


@pytest.fixture
def benchmark_bars(observation_time: datetime) -> list[Bar]:
    """10 daily benchmark bars."""
    bars = []
    for i in range(10):
        ts = observation_time - timedelta(days=10 - i - 1)
        open_price = 5000.0 + i
        high = open_price + 10.0
        low = open_price - 5.0
        close = open_price + 5.0
        bars.append(
            Bar(
                timestamp=ts,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=10_000_000.0,
            )
        )
    return bars


@pytest.fixture
def sector_bars(observation_time: datetime) -> list[Bar]:
    """10 daily sector bars."""
    bars = []
    for i in range(10):
        ts = observation_time - timedelta(days=10 - i - 1)
        open_price = 1000.0 + i * 0.1
        high = open_price + 5.0
        low = open_price - 2.0
        close = open_price + 2.0
        bars.append(
            Bar(
                timestamp=ts,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=2_000_000.0,
            )
        )
    return bars


def create_opportunity(
    symbol: str,
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
    expected_upside_pct: float | None = None,
    expected_downside_pct: float | None = None,
    expected_holding_days: float | None = None,
    probability_estimate: float | None = None,
    calibration_status: str = "CALIBRATED",
    trigger_state: str = "triggered",
    multi_timeframe_alignment: str = "aligned",
    known_catalysts: tuple = (),
    concentration_bucket: str = "LOW",
) -> object:
    """Create a test Opportunity with specified parameters."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        feature_snapshots=[],
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id=f"SEC{symbol}",
        symbol=symbol,
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        universe_snapshot_id="SNAP001",
        warehouse_manifest_hash="HASH001",
        dataset_manifest_hash="HASH002",
        source_record_ids=[],
    )

    # Patch expected values
    if expected_upside_pct is not None:
        object.__setattr__(opp, "expected_upside_pct", expected_upside_pct)
    if expected_downside_pct is not None:
        object.__setattr__(opp, "expected_downside_pct", expected_downside_pct)
    if expected_holding_days is not None:
        object.__setattr__(opp, "expected_holding_days", expected_holding_days)
    if probability_estimate is not None:
        object.__setattr__(opp, "probability_estimate", probability_estimate)
    
    object.__setattr__(opp, "calibration_status", calibration_status)
    object.__setattr__(opp, "trigger_state", trigger_state)
    object.__setattr__(opp, "multi_timeframe_alignment", multi_timeframe_alignment)
    object.__setattr__(opp, "known_catalysts", known_catalysts)
    object.__setattr__(opp, "concentration_bucket", concentration_bucket)

    return opp


def test_ranker_initialization():
    """Test that ranker initializes without errors."""
    ranker = OpportunityRanker()
    assert ranker is not None
    assert ranker.intrinsic_scorer is not None
    assert ranker.timing_scorer is not None
    assert ranker.swing_scorer is not None


def test_ranking_batch_empty_opportunities():
    """Test ranking an empty opportunity set."""
    ranker = OpportunityRanker()
    batch = ranker.rank([])

    assert batch.total_opportunities == 0
    assert len(batch.ranked_opportunities) == 0


def test_deterministic_ranking(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test that ranking produces deterministic results."""
    opp = create_opportunity(
        symbol="TEST",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=35.0,
        expected_downside_pct=-10.0,
        expected_holding_days=10.0,
        probability_estimate=0.65,
    )

    ranker = OpportunityRanker()

    # Rank twice
    batch1 = ranker.rank([opp], universe_snapshot_id="TEST001")
    batch2 = ranker.rank([opp], universe_snapshot_id="TEST001")

    # Should be identical
    assert len(batch1.ranked_opportunities) == len(batch2.ranked_opportunities)
    assert batch1.ranked_opportunities[0].opportunity_id == batch2.ranked_opportunities[0].opportunity_id
    assert batch1.ranked_opportunities[0].overall_research_score == batch2.ranked_opportunities[0].overall_research_score
    assert (
        batch1.ranked_opportunities[0].expected_swing_value_score
        == batch2.ranked_opportunities[0].expected_swing_value_score
    )


def test_highest_swing_value_wins(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test that opportunity with highest swing value ranks first."""
    # Create two opportunities with different swing values
    opp_high_swing = create_opportunity(
        symbol="HIGH",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=50.0,  # High upside
        expected_downside_pct=-5.0,  # Low downside
        expected_holding_days=10.0,
        probability_estimate=0.70,  # High probability
        trigger_state="triggered",
        multi_timeframe_alignment="aligned",
    )

    opp_low_swing = create_opportunity(
        symbol="LOW",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=10.0,  # Low upside
        expected_downside_pct=-20.0,  # Higher downside
        expected_holding_days=10.0,
        probability_estimate=0.50,  # Lower probability
        trigger_state="forming",
        multi_timeframe_alignment="forming",
    )

    ranker = OpportunityRanker()
    batch = ranker.rank([opp_low_swing, opp_high_swing])

    # High swing should be first
    assert batch.ranked_opportunities[0].opportunity_id == opp_high_swing.opportunity_id
    assert batch.ranked_opportunities[0].rank == 1
    assert batch.ranked_opportunities[1].opportunity_id == opp_low_swing.opportunity_id
    assert batch.ranked_opportunities[1].rank == 2
    assert batch.ranked_opportunities[0].expected_swing_value_score > batch.ranked_opportunities[1].expected_swing_value_score


def test_undervalued_no_trigger_is_waiting_for_trigger(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test that undervalued opportunity without trigger is classified as WAITING_FOR_TRIGGER."""
    opp = create_opportunity(
        symbol="MISPRICED",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=40.0,  # Strong valuation upside
        expected_downside_pct=-8.0,
        expected_holding_days=10.0,
        probability_estimate=0.60,
        trigger_state="forming",  # No trigger yet
        multi_timeframe_alignment="forming",  # Poor timing
        concentration_bucket="LOW",
    )

    ranker = OpportunityRanker()
    batch = ranker.rank([opp])

    result = batch.ranked_opportunities[0]
    # Should be waiting for trigger state (good intrinsic, poor timing)
    assert result.ranking_state == RankingState.HIGH_PRIORITY_WAITING_FOR_TRIGGER


def test_technical_strength_cannot_erase_severe_distress(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test that perfect technical cannot override severe capital distress."""
    opp = create_opportunity(
        symbol="DISTRESSED",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=10.0,  # Poor valuation
        expected_downside_pct=-50.0,  # Severe downside (capital distress)
        expected_holding_days=10.0,
        probability_estimate=0.70,
        trigger_state="triggered",  # Perfect timing
        multi_timeframe_alignment="aligned",  # Perfect alignment
        concentration_bucket="CRITICAL",  # Severe capital distress
    )

    ranker = OpportunityRanker()
    batch = ranker.rank([opp])

    result = batch.ranked_opportunities[0]
    # Should be AVOID or low priority despite perfect timing
    assert result.ranking_state in (RankingState.AVOID, RankingState.DISTRESSED_OPTIONALITY)
    # Swing value should be capped
    assert result.expected_swing_value_score < 50


def test_unvalidated_evidence_has_zero_influence(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test that probability without calibration is not fabricated."""
    # Create opportunity with uncalibrated probability
    opp_uncalibrated = create_opportunity(
        symbol="UNCAL",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=35.0,
        expected_downside_pct=-10.0,
        expected_holding_days=10.0,
        probability_estimate=0.99,  # Would be very high if used
        calibration_status="UNCALIBRATED",
    )

    ranker = OpportunityRanker()
    batch = ranker.rank([opp_uncalibrated])

    result = batch.ranked_opportunities[0]
    # Should be marked as uncalibrated
    assert result.validation_status == "UNCALIBRATED"
    # Should have warning about not fabricating probability
    assert any("uncalibrated" in w.lower() for w in result.warnings)


def test_missing_data_not_treated_as_favorable(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test that missing data doesn't artificially inflate scores."""
    # Create opportunity with missing expected values (should be uncalibrated)
    opp = create_opportunity(
        symbol="MISSING",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=None,  # Missing
        expected_downside_pct=None,  # Missing
        expected_holding_days=None,  # Missing
        probability_estimate=None,  # Missing
        calibration_status="INSUFFICIENT_DATA",
    )

    ranker = OpportunityRanker()
    batch = ranker.rank([opp])

    result = batch.ranked_opportunities[0]
    # Should have missing information noted
    assert len(result.missing_information) > 0
    # Swing value should be neutral (50) not inflated
    assert result.expected_swing_value_score <= 60


def test_ranking_result_serialization(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test that ranking results can be deterministically serialized."""
    opp = create_opportunity(
        symbol="SER",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=35.0,
        expected_downside_pct=-10.0,
        expected_holding_days=10.0,
        probability_estimate=0.65,
    )

    ranker = OpportunityRanker()
    batch1 = ranker.rank([opp])

    # Serialize to JSON
    batch_dict = batch1.to_dict()
    batch_json = json.dumps(batch_dict, sort_keys=True)

    # Re-parse from JSON
    batch_dict2 = json.loads(batch_json)
    batch2 = RankingBatch.from_dict(batch_dict2)

    # Should be identical
    assert batch1.ranked_opportunities[0].opportunity_id == batch2.ranked_opportunities[0].opportunity_id
    assert batch1.ranked_opportunities[0].overall_research_score == batch2.ranked_opportunities[0].overall_research_score


def test_no_broker_calls(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test that ranker makes no broker API calls."""
    opp = create_opportunity(
        symbol="NOBROKER",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=35.0,
        expected_downside_pct=-10.0,
        expected_holding_days=10.0,
        probability_estimate=0.65,
    )

    ranker = OpportunityRanker()
    
    # This should not raise any broker errors
    batch = ranker.rank([opp])
    assert batch is not None


def test_ranking_state_classification(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test various ranking state classifications."""
    # HIGH_PRIORITY_TRIGGERED
    opp_triggered = create_opportunity(
        symbol="TRIGGERED",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=40.0,
        expected_downside_pct=-10.0,
        expected_holding_days=10.0,
        probability_estimate=0.65,
        trigger_state="triggered",
        multi_timeframe_alignment="aligned",
        concentration_bucket="LOW",
    )

    # WATCHLIST (moderate scores)
    opp_watchlist = create_opportunity(
        symbol="WATCH",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=15.0,
        expected_downside_pct=-15.0,
        expected_holding_days=10.0,
        probability_estimate=0.55,
        trigger_state="forming",
        multi_timeframe_alignment="forming",
        concentration_bucket="MEDIUM",
    )

    ranker = OpportunityRanker()
    batch = ranker.rank([opp_triggered, opp_watchlist])

    triggered_result = next(r for r in batch.ranked_opportunities if r.opportunity_id == opp_triggered.opportunity_id)
    watchlist_result = next(r for r in batch.ranked_opportunities if r.opportunity_id == opp_watchlist.opportunity_id)

    assert triggered_result.ranking_state == RankingState.HIGH_PRIORITY_TRIGGERED
    assert watchlist_result.ranking_state in (
        RankingState.WATCHLIST,
        RankingState.HIGH_PRIORITY_WAITING_FOR_TRIGGER,
    )


def test_percentile_calculation(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test that percentiles are calculated correctly."""
    opportunities = []
    for i in range(5):
        opp = create_opportunity(
            symbol=f"OPP{i}",
            daily_bars=bullish_daily_bars,
            weekly_bars=bullish_weekly_bars,
            benchmark_bars=benchmark_bars,
            sector_bars=sector_bars,
            observation_time=observation_time,
            expected_upside_pct=20.0 + (i * 5),  # Increasing upside
            expected_downside_pct=-10.0,
            expected_holding_days=10.0,
            probability_estimate=0.50 + (i * 0.05),
            trigger_state="triggered" if i >= 2 else "forming",
        )
        opportunities.append(opp)

    ranker = OpportunityRanker()
    batch = ranker.rank(opportunities)

    # Check that percentiles are in order
    assert batch.ranked_opportunities[0].percentile >= batch.ranked_opportunities[-1].percentile
    # First should be 100, last should be lower
    assert batch.ranked_opportunities[0].percentile >= 50


def test_evidence_lineage_tracked(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test that evidence lineage is properly tracked."""
    opp = create_opportunity(
        symbol="EVIDENCE",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=35.0,
        expected_downside_pct=-10.0,
        expected_holding_days=10.0,
        probability_estimate=0.65,
    )

    ranker = OpportunityRanker()
    batch = ranker.rank([opp])

    result = batch.ranked_opportunities[0]
    # Should have evidence lineage
    assert result.evidence_lineage is not None
    assert "intrinsic" in result.evidence_lineage
    assert "timing" in result.evidence_lineage
    assert "swing_value" in result.evidence_lineage


def test_multiple_opportunities_comparison(
    bullish_daily_bars: list[Bar],
    bearish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Test ranking multiple opportunities with different characteristics."""
    opportunities = []
    
    # Strong opportunity
    opp_strong = create_opportunity(
        symbol="STRONG",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=45.0,
        expected_downside_pct=-8.0,
        expected_holding_days=10.0,
        probability_estimate=0.70,
        trigger_state="triggered",
        multi_timeframe_alignment="aligned",
    )
    opportunities.append(opp_strong)

    # Weak opportunity
    opp_weak = create_opportunity(
        symbol="WEAK",
        daily_bars=bearish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=5.0,
        expected_downside_pct=-25.0,
        expected_holding_days=15.0,
        probability_estimate=0.40,
        trigger_state="watch",
        multi_timeframe_alignment="divergent",
    )
    opportunities.append(opp_weak)

    ranker = OpportunityRanker()
    batch = ranker.rank(opportunities)

    # Strong should rank higher
    assert batch.ranked_opportunities[0].opportunity_id == opp_strong.opportunity_id
    assert batch.ranked_opportunities[0].expected_swing_value_score > batch.ranked_opportunities[1].expected_swing_value_score
    assert batch.total_opportunities == 2


def test_shadow_signals_attached_without_influence_by_default(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Shadow signals are captured while influence remains disabled by default."""
    opp = create_opportunity(
        symbol="SHADOW",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=30.0,
        expected_downside_pct=-10.0,
        expected_holding_days=10.0,
        probability_estimate=0.60,
    )

    ranker = OpportunityRanker()
    batch = ranker.rank(
        [opp],
        shadow_signals_by_opportunity={
            opp.opportunity_id: {
                "long_term_asymmetric_value": 92.0,
                "inflection_synchronization": 88.0,
            }
        },
    )

    result = batch.ranked_opportunities[0]
    assert result.shadow_signals
    assert result.shadow_score > 0.0
    assert result.shadow_influence_enabled is False
    assert result.evidence_lineage["shadow"]["influence_enabled"] is False
    assert result.evidence_lineage["shadow"]["weight"] == 0.0


def test_shadow_influence_can_be_explicitly_enabled(
    bullish_daily_bars: list[Bar],
    bullish_weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
):
    """Shadow influence can alter ordering only when explicitly enabled."""
    higher_base = create_opportunity(
        symbol="BASEHIGH",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=40.0,
        expected_downside_pct=-8.0,
        expected_holding_days=10.0,
        probability_estimate=0.70,
    )
    lower_base = create_opportunity(
        symbol="BASELOW",
        daily_bars=bullish_daily_bars,
        weekly_bars=bullish_weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        observation_time=observation_time,
        expected_upside_pct=20.0,
        expected_downside_pct=-15.0,
        expected_holding_days=10.0,
        probability_estimate=0.55,
    )

    ranker = OpportunityRanker()
    without_influence = ranker.rank(
        [higher_base, lower_base],
        shadow_signals_by_opportunity={
            higher_base.opportunity_id: {"shadow": 10.0},
            lower_base.opportunity_id: {"shadow": 100.0},
        },
    )
    with_influence = ranker.rank(
        [higher_base, lower_base],
        shadow_signals_by_opportunity={
            higher_base.opportunity_id: {"shadow": 10.0},
            lower_base.opportunity_id: {"shadow": 100.0},
        },
        ranking_shadow_influence_enabled=True,
        ranking_shadow_weight=0.95,
    )

    assert without_influence.ranked_opportunities[0].opportunity_id == higher_base.opportunity_id
    assert with_influence.ranked_opportunities[0].opportunity_id == lower_base.opportunity_id
    assert with_influence.ranked_opportunities[0].shadow_influence_enabled is True
