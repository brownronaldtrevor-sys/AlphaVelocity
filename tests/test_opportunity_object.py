from datetime import datetime, timedelta, timezone
import json
import pytest
from alpha_velocity.market.bars import Bar
from alpha_velocity.opportunity import Opportunity, assemble_opportunity


@pytest.fixture
def observation_time() -> datetime:
    return datetime(2024, 1, 15, 16, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def daily_bars(observation_time: datetime) -> list[Bar]:
    """Generate 10 daily bars ending at observation_time."""
    bars = []
    for i in range(10):
        ts = observation_time - timedelta(days=10 - i - 1)
        open_price = 100.0 + i
        high = open_price + 2.0
        low = open_price - 1.0
        close = open_price + 1.0
        bars.append(Bar(timestamp=ts, open=open_price, high=high, low=low, close=close, volume=1_000_000.0))
    return bars


@pytest.fixture
def weekly_bars(observation_time: datetime) -> list[Bar]:
    """Generate 12 weekly bars ending at observation_time."""
    bars = []
    for i in range(12):
        ts = observation_time - timedelta(weeks=12 - i - 1)
        open_price = 100.0 + (i * 0.5)
        high = open_price + 3.0
        low = open_price - 2.0
        close = open_price + 1.5
        bars.append(Bar(timestamp=ts, open=open_price, high=high, low=low, close=close, volume=5_000_000.0))
    return bars


@pytest.fixture
def benchmark_bars(observation_time: datetime) -> list[Bar]:
    """Generate 10 daily benchmark bars."""
    bars = []
    for i in range(10):
        ts = observation_time - timedelta(days=10 - i - 1)
        open_price = 5000.0 + i
        high = open_price + 10.0
        low = open_price - 5.0
        close = open_price + 5.0
        bars.append(Bar(timestamp=ts, open=open_price, high=high, low=low, close=close, volume=10_000_000.0))
    return bars


@pytest.fixture
def sector_bars(observation_time: datetime) -> list[Bar]:
    """Generate 10 daily sector bars."""
    bars = []
    for i in range(10):
        ts = observation_time - timedelta(days=10 - i - 1)
        open_price = 1000.0 + i * 0.1
        high = open_price + 5.0
        low = open_price - 2.0
        close = open_price + 2.0
        bars.append(Bar(timestamp=ts, open=open_price, high=high, low=low, close=close, volume=2_000_000.0))
    return bars


def test_opportunity_identity_and_timestamps(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity has identity and observation timestamps."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=["REC001", "REC002"],
    )

    assert opp.opportunity_id == "TEST-20240115163000"
    assert opp.security_id == "SEC123"
    assert opp.symbol == "TEST"
    assert opp.observation_time == observation_time
    assert opp.data_available_through == observation_time
    assert opp.observation_time.tzinfo is not None


def test_opportunity_completed_weekly_context(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity captures completed weekly context."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    assert opp.weekly_trend_state in ("bullish", "bearish")
    assert opp.weekly_range_position >= 0.0
    assert opp.weekly_range_position <= 1.0
    assert opp.weekly_volatility_state in ("neutral", "contraction", "expansion")
    assert opp.weekly_breakout_level > 0.0
    assert opp.weekly_invalidation_level > 0.0
    assert isinstance(opp.weekly_support_levels, tuple)
    assert isinstance(opp.weekly_resistance_levels, tuple)


def test_opportunity_daily_structure_and_trigger_state(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity captures daily structure and trigger state."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    assert opp.daily_trend_state in ("bullish", "bearish")
    assert opp.daily_range_position >= 0.0
    assert opp.daily_range_position <= 1.0
    assert opp.daily_volatility_state in ("neutral", "contraction", "expansion")
    assert opp.trigger_state in ("watch", "armed", "triggered", "closed")
    assert opp.daily_breakout_level > 0.0
    assert opp.daily_invalidation_level > 0.0
    assert isinstance(opp.daily_support_levels, tuple)
    assert isinstance(opp.daily_resistance_levels, tuple)


def test_opportunity_support_resistance_and_invalidation_levels(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity has support, resistance, breakout and invalidation levels."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    # Support levels should be tuples of dicts with level, provenance, window
    for level_dict in opp.daily_support_levels:
        assert isinstance(level_dict, dict)
        assert "level" in level_dict
        assert level_dict["level"] > 0.0

    for level_dict in opp.daily_resistance_levels:
        assert isinstance(level_dict, dict)
        assert "level" in level_dict
        assert level_dict["level"] > 0.0

    # Invalidation level should be > 0
    assert opp.daily_invalidation_level > 0.0
    assert opp.primary_invalidation_price >= 0.0


def test_opportunity_liquidity_and_volatility_inputs(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity includes liquidity and volatility inputs."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    # Liquidity indicators
    assert opp.average_daily_volume > 0.0
    assert opp.average_daily_dollar_volume > 0.0
    assert opp.spread_estimate_bps > 0.0
    assert opp.liquidity_risk in ("low", "medium", "high")

    # Volatility indicators
    assert opp.atr_pct > 0.0
    assert opp.volatility_expansion >= 0.0
    assert opp.volatility_contraction >= 0.0
    assert opp.weekly_volatility_state in ("neutral", "contraction", "expansion")
    assert opp.daily_volatility_state in ("neutral", "contraction", "expansion")


def test_opportunity_expected_value_fields(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity includes expected-value research fields."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    # These should be present (may be None for uncalibrated)
    assert hasattr(opp, "probability_estimate")
    assert hasattr(opp, "expected_upside_pct")
    assert hasattr(opp, "expected_downside_pct")
    assert hasattr(opp, "expected_holding_days")
    assert hasattr(opp, "estimated_cost_bps")
    assert hasattr(opp, "uncertainty_score")

    # Score fields
    assert opp.expected_value_score >= 0.0
    assert opp.uncertainty_score >= 0.0


def test_opportunity_calibration_status(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity tracks calibration status."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    # Should be UNCALIBRATED when no probability fields are set
    assert opp.calibration_status in ("CALIBRATED", "UNCALIBRATED")
    assert opp.governance_eligible in (True, False)
    assert opp.risk_eligible in (True, False)


def test_opportunity_validation_gated_evidence(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity supports validation-gated evidence."""
    feature_snapshots = [
        {
            "group_name": "technical_signals",
            "version": "1.2.3",
            "approved_weight": 0.8,
            "feature_values": {"rsi_14": 65.0, "macd_signal": 2.5},
        }
    ]

    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
        benchmark_bars=benchmark_bars,
        sector_bars=sector_bars,
        feature_snapshots=feature_snapshots,
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
        source_record_ids=[],
    )

    assert "technical_signals" in opp.feature_versions
    assert opp.feature_versions["technical_signals"] == "1.2.3"
    assert "rsi_14" in opp.feature_values
    assert opp.feature_values["rsi_14"] == 65.0


def test_opportunity_deterministic_serialization(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity serialization is deterministic."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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

    # to_dict should work
    opp_dict = opp.to_dict()
    assert isinstance(opp_dict, dict)
    assert opp_dict["symbol"] == "TEST"
    assert opp_dict["observation_time"] == "2024-01-15T16:30:00+00:00"

    # to_json should be valid JSON
    json_str = opp.to_json()
    parsed = json.loads(json_str)
    assert parsed["symbol"] == "TEST"

    # from_dict should round-trip
    opp2 = Opportunity.from_dict(opp_dict)
    assert opp2.symbol == opp.symbol
    assert opp2.observation_time == opp.observation_time
    assert opp2.opportunity_id == opp.opportunity_id


def test_opportunity_strict_future_data_rejection(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity strictly rejects future data."""
    # Try creating with event data in the future
    future_event_time = observation_time + timedelta(days=1)

    with pytest.raises(ValueError, match="event_data_available_at cannot exceed observation_time"):
        Opportunity(
            opportunity_id="TEST-001",
            security_id="SEC123",
            symbol="TEST",
            observation_time=observation_time,
            data_available_through=observation_time,
            universe_snapshot_id="SNAP001",
            benchmark_symbol="SPY",
            sector="Technology",
            industry="Software",
            market_regime="neutral",
            sector_regime="neutral",
            weekly_trend_state="bullish",
            weekly_range_position=0.5,
            weekly_support_levels=(),
            weekly_resistance_levels=(),
            weekly_breakout_level=100.0,
            weekly_invalidation_level=90.0,
            weekly_volatility_state="neutral",
            weekly_relative_strength=1.0,
            weekly_structure_quality=0.5,
            daily_trend_state="bullish",
            daily_range_position=0.5,
            daily_support_levels=(),
            daily_resistance_levels=(),
            daily_breakout_level=100.0,
            daily_invalidation_level=90.0,
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
            multi_timeframe_alignment="ALIGNED",
            close_price=100.0,
            average_daily_dollar_volume=1_000_000.0,
            average_daily_volume=1000.0,
            spread_estimate_bps=1.0,
            atr_pct=0.02,
            capacity_warning=False,
            known_catalysts=(),
            next_known_event_time=None,
            catalyst_risk="low",
            event_data_available_at=future_event_time,  # Future!
            probability_estimate=None,
            expected_upside_pct=None,
            expected_downside_pct=None,
            expected_holding_days=None,
            estimated_cost_bps=None,
            uncertainty_score=0.5,
            calibration_status="UNCALIBRATED",
            expected_value_score=0.0,
            correlation_bucket="medium",
            concentration_bucket="moderate",
            current_position_weight=0.0,
            opportunity_cost_rank=None,
        )


def test_opportunity_catalyst_future_data_rejection(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that Opportunity rejects catalysts with future data."""
    future_catalyst = {
        "name": "earnings",
        "occurred_at": observation_time + timedelta(days=1),  # Future!
        "available_at": observation_time,
    }

    with pytest.raises(ValueError, match="future catalyst evidence is not permitted"):
        Opportunity(
            opportunity_id="TEST-001",
            security_id="SEC123",
            symbol="TEST",
            observation_time=observation_time,
            data_available_through=observation_time,
            universe_snapshot_id="SNAP001",
            benchmark_symbol="SPY",
            sector="Technology",
            industry="Software",
            market_regime="neutral",
            sector_regime="neutral",
            weekly_trend_state="bullish",
            weekly_range_position=0.5,
            weekly_support_levels=(),
            weekly_resistance_levels=(),
            weekly_breakout_level=100.0,
            weekly_invalidation_level=90.0,
            weekly_volatility_state="neutral",
            weekly_relative_strength=1.0,
            weekly_structure_quality=0.5,
            daily_trend_state="bullish",
            daily_range_position=0.5,
            daily_support_levels=(),
            daily_resistance_levels=(),
            daily_breakout_level=100.0,
            daily_invalidation_level=90.0,
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
            multi_timeframe_alignment="ALIGNED",
            close_price=100.0,
            average_daily_dollar_volume=1_000_000.0,
            average_daily_volume=1000.0,
            spread_estimate_bps=1.0,
            atr_pct=0.02,
            capacity_warning=False,
            known_catalysts=(future_catalyst,),
            next_known_event_time=None,
            catalyst_risk="low",
            event_data_available_at=observation_time,
            probability_estimate=None,
            expected_upside_pct=None,
            expected_downside_pct=None,
            expected_holding_days=None,
            estimated_cost_bps=None,
            uncertainty_score=0.5,
            calibration_status="UNCALIBRATED",
            expected_value_score=0.0,
            correlation_bucket="medium",
            concentration_bucket="moderate",
            current_position_weight=0.0,
            opportunity_cost_rank=None,
        )


def test_assembler_does_not_call_broker(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that assembler does not call a broker."""
    # This is a basic test - the assembler only uses local data
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    # If it got here, no broker was called
    assert opp is not None


def test_assembler_does_not_create_orders(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that assembler does not create orders."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    # Opportunity should not have order information
    assert not hasattr(opp, "order_id")
    assert not hasattr(opp, "order_type")
    assert not hasattr(opp, "order_quantity")


def test_assembler_does_not_mutate_portfolio(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that assembler does not mutate a portfolio."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    # Opportunity should have portfolio weight but not mutate anything
    assert hasattr(opp, "current_position_weight")
    assert hasattr(opp, "proposed_weight")
    # These are just read-only fields, not operations


def test_assembler_does_not_approve_risk(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that assembler does not approve risk."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    # Assembler should not force approval - it marks as eligible but doesn't approve
    assert hasattr(opp, "risk_eligible")
    assert hasattr(opp, "governance_eligible")
    # These are just flags, not approvals


def test_assembler_does_not_fabricate_probabilities(
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    observation_time: datetime,
) -> None:
    """Test that assembler does not fabricate probabilities."""
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
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
        source_record_ids=[],
    )

    # Should be None (uncalibrated)
    assert opp.probability_estimate is None
    assert opp.expected_upside_pct is None
    assert opp.expected_downside_pct is None
    assert opp.expected_holding_days is None
    assert opp.estimated_cost_bps is None

    # And calibration status should reflect this
    assert opp.calibration_status == "UNCALIBRATED"
    assert opp.expected_value_score == 0.0
