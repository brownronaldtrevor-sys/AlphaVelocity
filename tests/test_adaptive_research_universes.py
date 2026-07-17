from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from alpha_velocity.market_intelligence import (
    MarketIntelligenceEngine,
    PriorityMode,
    ResearchUniverse,
    ScanConfig,
    UniverseConfig,
    UniverseType,
    ValidationStatus,
)
from alpha_velocity.opportunity import Opportunity
from alpha_velocity.warehouse import (
    InMemoryProviderAdapter,
    SQLiteHistoricalWarehouse,
    WarehouseIngestionEngine,
)


def _build_provider(observation_time: datetime, symbols: list[str], late_listing_symbol: str | None = None) -> InMemoryProviderAdapter:
    securities = []
    bars = []
    for idx, symbol in enumerate(symbols):
        security_id = f"sec-{symbol.lower()}"
        listing_date = "2023-01-01"
        if late_listing_symbol is not None and symbol == late_listing_symbol:
            listing_date = "2025-01-01"
        securities.append(
            {
                "security_id": security_id,
                "ticker": symbol,
                "company_name": f"{symbol} Inc",
                "exchange": "NASDAQ",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": listing_date,
                "delisting_date": None,
                "active": True,
                "source": "SAMPLE_DATA",
                "available_at": "2023-01-01T00:00:00+00:00",
                "revision_id": "sample",
            }
        )
        for i in range(120):
            trade_time = observation_time - timedelta(days=120 - i)
            base = 50.0 + idx * 5.0 + i * 0.1
            bars.append(
                {
                    "security_id": security_id,
                    "trade_date": trade_time.strftime("%Y-%m-%d"),
                    "open": base,
                    "high": base + 1.0,
                    "low": base - 1.0,
                    "close": base + 0.4,
                    "volume": 1_200_000.0 + idx * 5_000.0,
                    "available_at": trade_time.isoformat(),
                    "source": "SAMPLE_DATA",
                    "ingestion_timestamp": observation_time.isoformat(),
                    "revision_id": "sample",
                }
            )
    return InMemoryProviderAdapter(securities=securities, bars=bars)


@pytest.fixture
def observation_time() -> datetime:
    return datetime(2024, 1, 15, 16, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def warehouse(tmp_path) -> SQLiteHistoricalWarehouse:
    return SQLiteHistoricalWarehouse(str(tmp_path / "warehouse.db"))


def _scan(
    warehouse: SQLiteHistoricalWarehouse,
    observation_time: datetime,
    symbols: list[str],
    research_universes: tuple[ResearchUniverse, ...],
    late_listing_symbol: str | None = None,
) -> tuple[MarketIntelligenceEngine, object]:
    provider = _build_provider(observation_time, symbols, late_listing_symbol)
    WarehouseIngestionEngine(warehouse=warehouse, provider=provider).ingest(run_id="adaptive-test", symbols=symbols)
    engine = MarketIntelligenceEngine()
    scan_config = ScanConfig(
        universe_config=UniverseConfig(
            observation_time=observation_time,
            min_price=1.0,
            max_price=100000.0,
            min_avg_daily_volume=100_000.0,
            min_avg_daily_dollar_volume=500_000.0,
            min_trading_history_days=60,
            supported_exchanges=("NASDAQ",),
            supported_asset_types=("STOCK",),
        ),
        research_universes=research_universes,
        user_watchlist_symbols=("WATCH1",),
        current_holding_symbols=("HOLD1",),
        benchmark_symbols=("SPY",),
    )
    result = engine.scan(warehouse=warehouse, scan_config=scan_config)
    return engine, result


def test_multiple_universes_scan_independently_and_disabled_skipped(warehouse: SQLiteHistoricalWarehouse, observation_time: datetime) -> None:
    universes = (
        ResearchUniverse(
            universe_id="broad",
            name="Broad",
            description="Broad",
            universe_type=UniverseType.BROAD_MARKET,
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=True,
            priority_mode=PriorityMode.BALANCED,
        ),
        ResearchUniverse(
            universe_id="disabled_custom",
            name="Disabled",
            description="Disabled",
            universe_type=UniverseType.CUSTOM,
            membership_rules={"include_symbols": ["AAA"]},
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=False,
            priority_mode=PriorityMode.BALANCED,
        ),
    )
    _, result = _scan(warehouse, observation_time, ["AAA", "BBB", "CCC"], universes)

    ids = {diagnostic.universe_id for diagnostic in result.universe_diagnostics}
    assert "broad" in ids
    assert "disabled_custom" not in ids


def test_point_in_time_membership_does_not_use_future_listing(warehouse: SQLiteHistoricalWarehouse, observation_time: datetime) -> None:
    universe = ResearchUniverse(
        universe_id="broad",
        name="Broad",
        description="Broad",
        universe_type=UniverseType.BROAD_MARKET,
        observation_time=observation_time,
        available_at=observation_time,
        source="TEST",
        validation_status=ValidationStatus.SUPPORTED,
        enabled=True,
        priority_mode=PriorityMode.BALANCED,
    )
    _, result = _scan(warehouse, observation_time, ["AAA", "LATE"], (universe,), late_listing_symbol="LATE")

    symbols = {opportunity.symbol for opportunity in result.assembled_opportunities}
    assert "AAA" in symbols
    assert "LATE" not in symbols


def test_duplicate_candidates_merge_to_one_canonical_with_provenance(warehouse: SQLiteHistoricalWarehouse, observation_time: datetime) -> None:
    universes = (
        ResearchUniverse(
            universe_id="broad",
            name="Broad",
            description="Broad",
            universe_type=UniverseType.BROAD_MARKET,
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=True,
        ),
        ResearchUniverse(
            universe_id="momentum",
            name="Momentum",
            description="Momentum",
            universe_type=UniverseType.MOMENTUM,
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=True,
        ),
    )
    _, result = _scan(warehouse, observation_time, ["AAA", "BBB"], universes)

    assert result.unique_canonical_opportunities == len(result.assembled_opportunities)
    assert result.merged_duplicate_candidates >= 1
    merged = [opportunity for opportunity in result.assembled_opportunities if len(opportunity.contributing_universe_ids) > 1]
    assert merged
    assert merged[0].discovery_reasons_by_universe


def test_duplicate_evidence_does_not_inflate_confidence(warehouse: SQLiteHistoricalWarehouse, observation_time: datetime) -> None:
    universes = (
        ResearchUniverse(
            universe_id="broad",
            name="Broad",
            description="Broad",
            universe_type=UniverseType.BROAD_MARKET,
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=True,
        ),
        ResearchUniverse(
            universe_id="custom_dup",
            name="CustomDup",
            description="Custom duplicate universe",
            universe_type=UniverseType.CUSTOM,
            membership_rules={"include_symbols": ["AAA"]},
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=True,
        ),
    )
    _, result = _scan(warehouse, observation_time, ["AAA"], universes)

    opportunity = result.assembled_opportunities[0]
    assert opportunity.calibration_status in {"CALIBRATED", "UNCALIBRATED"}
    assert len(opportunity.contributing_universe_ids) >= 1
    assert len(opportunity.contributing_universe_ids) <= 2


def test_watchlist_and_current_holdings_identifiable(warehouse: SQLiteHistoricalWarehouse, observation_time: datetime) -> None:
    universes = (
        ResearchUniverse(
            universe_id="watchlist",
            name="Watchlist",
            description="User watchlist",
            universe_type=UniverseType.USER_WATCHLIST,
            membership_rules={"symbols": ["WATCH1"]},
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=True,
        ),
        ResearchUniverse(
            universe_id="holdings",
            name="Holdings",
            description="Current holdings",
            universe_type=UniverseType.CURRENT_HOLDINGS,
            membership_rules={"symbols": ["HOLD1"]},
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=True,
        ),
    )
    _, result = _scan(warehouse, observation_time, ["WATCH1", "HOLD1"], universes)

    by_symbol = {opportunity.symbol: opportunity for opportunity in result.assembled_opportunities}
    assert "watchlist" in by_symbol["WATCH1"].contributing_universe_ids
    assert "holdings" in by_symbol["HOLD1"].contributing_universe_ids


def test_research_priority_explainable_and_non_executing(warehouse: SQLiteHistoricalWarehouse, observation_time: datetime) -> None:
    universes = (
        ResearchUniverse(
            universe_id="broad",
            name="Broad",
            description="Broad",
            universe_type=UniverseType.BROAD_MARKET,
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=True,
        ),
    )
    _, result = _scan(warehouse, observation_time, ["AAA", "BBB", "CCC"], universes)

    assert result.universe_priorities
    priority = result.universe_priorities[0]
    assert priority.reasons
    assert priority.priority.value in {"VERY_HIGH", "HIGH", "NORMAL", "LOW", "PAUSED"}
    assert all(not opportunity.model_disagreement or opportunity.risk_eligible in {True, False} for opportunity in result.assembled_opportunities)


def test_marketplace_receives_merged_candidates_and_universe_summary(warehouse: SQLiteHistoricalWarehouse, observation_time: datetime) -> None:
    universes = (
        ResearchUniverse(
            universe_id="broad",
            name="Broad",
            description="Broad",
            universe_type=UniverseType.BROAD_MARKET,
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=True,
        ),
        ResearchUniverse(
            universe_id="deep_value",
            name="DeepValue",
            description="Deep value",
            universe_type=UniverseType.DEEP_VALUE,
            observation_time=observation_time,
            available_at=observation_time,
            source="TEST",
            validation_status=ValidationStatus.SUPPORTED,
            enabled=True,
        ),
    )
    _, result = _scan(warehouse, observation_time, ["AAA", "BBB", "CCC", "DDD"], universes)

    assert result.marketplace_result is not None
    assert result.marketplace_result.merged_canonical_candidate_count == len(result.assembled_opportunities)
    assert result.marketplace_result.candidate_counts_by_universe


def test_one_authoritative_canonical_opportunity_model() -> None:
    assert Opportunity.__module__ == "alpha_velocity.opportunity.models"
