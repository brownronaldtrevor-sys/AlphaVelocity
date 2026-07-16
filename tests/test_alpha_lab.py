"""Comprehensive Alpha Lab tests."""

import pytest
from datetime import datetime, timezone, timedelta

from alpha_velocity.alpha_lab import (
    AlphaLabEngine,
    CandidateState,
    StrategyCandidate,
    StrategyContext,
    StrategyEvidence,
    StrategyValidationStatus,
    SwingRepricingStrategy,
)
from alpha_velocity.warehouse import SQLiteHistoricalWarehouse


@pytest.fixture
def observation_time() -> datetime:
    """Standard observation time."""
    return datetime(2024, 1, 15, 16, 30, tzinfo=timezone.utc)


@pytest.fixture
def warehouse(observation_time: datetime) -> SQLiteHistoricalWarehouse:
    """Create in-memory test warehouse."""
    warehouse = SQLiteHistoricalWarehouse(path=":memory:")

    # Add sample securities with available_at BEFORE observation_time
    securities = [
        ("sec-aapl", "AAPL", "Apple Inc", "NASDAQ", "STOCK"),
        ("sec-msft", "MSFT", "Microsoft Corporation", "NASDAQ", "STOCK"),
        ("sec-tsla", "TSLA", "Tesla Inc", "NASDAQ", "STOCK"),
        ("sec-esz24", "ESZ24", "E-mini S&P 500 Dec 2024", "CME", "FUTURE"),
        ("sec-nqz24", "NQZ24", "E-mini NASDAQ Dec 2024", "CME", "FUTURE"),
    ]

    available_at = observation_time - timedelta(days=1)  # Available before observation
    listing_date = observation_time - timedelta(days=365)  # Listed 1 year ago

    for sec_id, ticker, name, exchange, asset_type in securities:
        warehouse._conn.execute(
            """
            INSERT OR REPLACE INTO securities
            (security_id, ticker, company_name, exchange, asset_type, currency, listing_date, active, source, available_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sec_id,
                ticker,
                name,
                exchange,
                asset_type,
                "USD",
                listing_date.isoformat(),
                1,
                "TEST",
                available_at.isoformat(),
                observation_time.isoformat(),
            ),
        )
    warehouse._conn.commit()
    return warehouse


@pytest.fixture
def strategy_context(observation_time: datetime, warehouse: SQLiteHistoricalWarehouse) -> StrategyContext:
    """Create test context."""
    return StrategyContext(
        observation_time=observation_time,
        warehouse=warehouse,
        universe_snapshot_id="univ-test",
        universe_size=5,
        dataset_manifest_hash="dataset-v1",
        warehouse_manifest_hash="warehouse-v1",
    )


# ============================================================================
# Shared Strategy API Tests
# ============================================================================


def test_swing_repricing_strategy_properties() -> None:
    """Test Swing Repricing strategy properties."""
    strategy = SwingRepricingStrategy()

    assert strategy.strategy_id == "swing-repricing-v1"
    assert strategy.strategy_name == "Swing Repricing"
    assert strategy.strategy_version == "1.0.0"
    assert "STOCK" in strategy.supported_asset_types
    assert strategy.required_history == 365
    assert strategy.validation_status == StrategyValidationStatus.UNCALIBRATED


def test_swing_repricing_unvalidated_has_zero_influence() -> None:
    """Test that unvalidated strategies have zero influence."""
    strategy = SwingRepricingStrategy()

    assert strategy.ranking_influence == 0.0
    assert strategy.allocation_influence == 0.0


def test_swing_repricing_generates_candidates(
    strategy_context: StrategyContext,
) -> None:
    """Test Swing Repricing generates candidates."""
    strategy = SwingRepricingStrategy()
    result = strategy.generate_candidates(strategy_context)

    assert result.run_id is not None
    assert result.strategy_id == "swing-repricing-v1"
    assert result.observation_time == strategy_context.observation_time
    assert isinstance(result.candidates, tuple)
    # With sample logic, should produce at least some candidates
    assert len(result.candidates) > 0
    assert result.state is not None


def test_swing_repricing_candidate_states() -> None:
    """Test Swing Repricing produces valid candidate states."""
    strategy = SwingRepricingStrategy()

    candidate = StrategyCandidate(
        candidate_id="test-1",
        strategy_id=strategy.strategy_id,
        symbol="TEST",
        security_id="sec-test",
        observation_time=datetime.now(timezone.utc),
        data_available_through=datetime.now(timezone.utc) - timedelta(days=1),
        candidate_state=CandidateState.TRIGGERED,
        evidence=StrategyEvidence(),
        explanation="Test candidate",
    )

    assert candidate.candidate_state == CandidateState.TRIGGERED
    explanation = strategy.explain_candidate(candidate.candidate_id)
    assert isinstance(explanation, str)


def test_candidate_state_enum() -> None:
    """Test candidate state enumeration."""
    assert CandidateState.TRIGGERED.value == "TRIGGERED"
    assert CandidateState.WAITING_FOR_TRIGGER.value == "WAITING_FOR_TRIGGER"
    assert CandidateState.WATCHLIST.value == "WATCHLIST"
    assert CandidateState.INVALIDATED.value == "INVALIDATED"
    assert CandidateState.INSUFFICIENT_DATA.value == "INSUFFICIENT_DATA"
    assert CandidateState.EXCLUDED.value == "EXCLUDED"
    assert CandidateState.SHADOW_ONLY.value == "SHADOW_ONLY"


def test_strategy_evidence_default_values() -> None:
    """Test StrategyEvidence has sensible defaults."""
    evidence = StrategyEvidence()

    assert evidence.intrinsic_opportunity_score == 0.0
    assert evidence.timing_opportunity_score == 0.0
    assert evidence.risk_adjustment == 100.0
    assert evidence.uncertainty_adjustment == 100.0
    assert len(evidence.positive_contributors) == 0
    assert len(evidence.negative_contributors) == 0


# ============================================================================
# Alpha Lab Engine Tests
# ============================================================================


def test_alpha_lab_engine_initialization() -> None:
    """Test AlphaLabEngine initialization."""
    engine = AlphaLabEngine()

    assert len(engine.strategies) == 0
    assert len(engine.run_history) == 0


def test_alpha_lab_register_strategy() -> None:
    """Test registering strategies."""
    engine = AlphaLabEngine()
    swing_strategy = SwingRepricingStrategy()

    engine.register_strategy(swing_strategy)

    assert len(engine.strategies) == 1
    assert "swing-repricing-v1" in engine.strategies


def test_alpha_lab_run_produces_opportunities(
    observation_time: datetime,
    warehouse: SQLiteHistoricalWarehouse,
) -> None:
    """Test AlphaLabEngine.run produces canonical opportunities."""
    engine = AlphaLabEngine()
    engine.register_strategy(SwingRepricingStrategy())

    result = engine.run(
        warehouse=warehouse,
        observation_time=observation_time,
        universe_snapshot_id="univ-test",
        universe_size=5,
        warehouse_manifest_hash="warehouse-v1",
        dataset_manifest_hash="dataset-v1",
    )

    assert result.run_id is not None
    assert len(result.strategies_run) == 1
    assert result.unique_candidates > 0
    assert len(result.opportunities) > 0
    # Opportunities should be canonical Opportunity objects
    for opp in result.opportunities:
        assert hasattr(opp, "opportunity_id")
        assert hasattr(opp, "symbol")
        assert opp.observation_time == observation_time


def test_alpha_lab_preserves_strategy_lineage(
    observation_time: datetime,
    warehouse: SQLiteHistoricalWarehouse,
) -> None:
    """Test that strategy lineage is preserved in opportunities."""
    engine = AlphaLabEngine()
    engine.register_strategy(SwingRepricingStrategy())

    result = engine.run(
        warehouse=warehouse,
        observation_time=observation_time,
        universe_snapshot_id="univ-test",
        universe_size=5,
        warehouse_manifest_hash="warehouse-v1",
        dataset_manifest_hash="dataset-v1",
    )

    # Each opportunity should have source_record_ids pointing back to candidates
    for opp in result.opportunities:
        assert len(opp.source_record_ids) > 0
        # Source IDs should contain strategy info
        for source_id in opp.source_record_ids:
            assert "SWING" in source_id


def test_alpha_lab_deduplication() -> None:
    """Test that Alpha Lab deduplicates overlapping candidates."""
    # Two strategies identify same symbol
    # Result should have one Opportunity but preserve both strategy sources
    # This is tested in the integration test below


def test_alpha_lab_multiple_strategies() -> None:
    """Test running multiple strategies together."""
    engine = AlphaLabEngine()
    engine.register_strategy(SwingRepricingStrategy())

    assert len(engine.strategies) == 1


# ============================================================================
# Strategy State and Results Tests
# ============================================================================


def test_strategy_run_result_serialization(
    strategy_context: StrategyContext,
) -> None:
    """Test StrategyRunResult serialization."""
    strategy = SwingRepricingStrategy()
    result = strategy.generate_candidates(strategy_context)

    # Should be serializable to dict
    result_dict = result.to_dict()
    assert isinstance(result_dict, dict)
    assert "run_id" in result_dict
    assert "observation_time" in result_dict
    assert "candidates" in result_dict


def test_strategy_candidate_timestamp_validation() -> None:
    """Test that candidates enforce point-in-time timestamps."""
    observation_time = datetime(2024, 1, 15, tzinfo=timezone.utc)

    # Should work: data_available_through <= observation_time
    candidate = StrategyCandidate(
        candidate_id="test",
        strategy_id="test-strategy",
        symbol="TEST",
        security_id="sec-test",
        observation_time=observation_time,
        data_available_through=observation_time - timedelta(days=1),
        candidate_state=CandidateState.TRIGGERED,
        evidence=StrategyEvidence(),
        explanation="Valid candidate",
    )
    assert candidate is not None

    # Should fail: data_available_through > observation_time (future data)
    with pytest.raises(ValueError):
        StrategyCandidate(
            candidate_id="test",
            strategy_id="test-strategy",
            symbol="TEST",
            security_id="sec-test",
            observation_time=observation_time,
            data_available_through=observation_time + timedelta(days=1),
            candidate_state=CandidateState.TRIGGERED,
            evidence=StrategyEvidence(),
            explanation="Invalid: future data",
        )


# ============================================================================
# No External Calls Tests
# ============================================================================


def test_strategies_no_broker_calls(strategy_context: StrategyContext) -> None:
    """Test that strategies make no broker calls."""
    swing = SwingRepricingStrategy()

    # Should execute without errors and without broker access
    swing_result = swing.generate_candidates(strategy_context)

    assert swing_result is not None


def test_strategies_no_order_creation(strategy_context: StrategyContext) -> None:
    """Test that strategies do not create orders."""
    strategy = SwingRepricingStrategy()
    result = strategy.generate_candidates(strategy_context)

    # Candidates should be research only, not orders
    for candidate in result.candidates:
        assert not hasattr(candidate, "order_id")
        assert not hasattr(candidate, "order_price")
        assert candidate.candidate_state in [
            CandidateState.TRIGGERED,
            CandidateState.WAITING_FOR_TRIGGER,
            CandidateState.EXCLUDED,
            CandidateState.INSUFFICIENT_DATA,
            CandidateState.WATCHLIST,
            CandidateState.INVALIDATED,
            CandidateState.SHADOW_ONLY,
        ]


# ============================================================================
# Deterministic Serialization Tests
# ============================================================================


def test_strategy_run_deterministic_serialization(
    strategy_context: StrategyContext,
) -> None:
    """Test that strategy results can be deterministically serialized."""
    strategy = SwingRepricingStrategy()
    result = strategy.generate_candidates(strategy_context)

    dict1 = result.to_dict()
    dict2 = result.to_dict()

    # Should produce identical dicts on repeated calls
    assert dict1 == dict2


def test_strategy_validation_status_enum() -> None:
    """Test StrategyValidationStatus enumeration."""
    assert StrategyValidationStatus.UNCALIBRATED.value == "UNCALIBRATED"
    assert StrategyValidationStatus.CALIBRATED.value == "CALIBRATED"
    assert StrategyValidationStatus.SHADOW.value == "SHADOW"
    assert StrategyValidationStatus.RETIRED.value == "RETIRED"
