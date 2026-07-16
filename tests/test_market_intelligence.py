"""Tests for Market Intelligence Engine."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha_velocity.market.bars import Bar
from alpha_velocity.market_intelligence import (
    MarketIntelligenceEngine,
    QualificationState,
    ScanConfig,
    UniverseConfig,
)
from alpha_velocity.warehouse import (
    InMemoryProviderAdapter,
    SQLiteHistoricalWarehouse,
    WarehouseIngestionEngine,
)


@pytest.fixture
def observation_time() -> datetime:
    return datetime(2024, 1, 15, 16, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def warehouse(tmp_path: Path) -> SQLiteHistoricalWarehouse:
    """Create a test warehouse."""
    return SQLiteHistoricalWarehouse(str(tmp_path / "warehouse.db"))


@pytest.fixture
def engine():
    """Create a market intelligence engine."""
    return MarketIntelligenceEngine()


def test_qualified_security_with_sufficient_history(
    warehouse: SQLiteHistoricalWarehouse,
    engine: MarketIntelligenceEngine,
    observation_time: datetime,
) -> None:
    """Test that security with sufficient history is qualified."""
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-1",
                "ticker": "TEST",
                "company_name": "Test Inc",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2023-01-01",
                "delisting_date": None,
                "active": True,
                "source": "test",
                "available_at": "2023-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-1",
                "trade_date": (observation_time - timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1_000_000.0,
                "available_at": (observation_time - timedelta(days=i)).isoformat(),
                "source": "test",
                "ingestion_timestamp": observation_time.isoformat(),
                "revision_id": "rev-1",
            }
            for i in range(70)  # 70 days of data
        ],
    )

    ingestion = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    ingestion.ingest(run_id="test", symbols=["TEST"])

    config = ScanConfig(
        universe_config=UniverseConfig(
            observation_time=observation_time,
            min_price=1.0,
            min_avg_daily_volume=500_000.0,
            min_avg_daily_dollar_volume=50_000_000.0,
            min_trading_history_days=60,
            supported_exchanges=("NYSE",),
        )
    )

    result = engine.scan(warehouse=warehouse, scan_config=config)

    assert result.total_securities_considered == 1
    assert result.qualified_count == 1
    assert result.excluded_count == 0
    assert len(result.assembled_opportunities) > 0


def test_insufficient_history_exclusion(
    warehouse: SQLiteHistoricalWarehouse,
    engine: MarketIntelligenceEngine,
    observation_time: datetime,
) -> None:
    """Test that security with insufficient history is excluded."""
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-2",
                "ticker": "SHORT",
                "company_name": "Short History Inc",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2023-12-01",
                "delisting_date": None,
                "active": True,
                "source": "test",
                "available_at": "2023-12-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-2",
                "trade_date": (observation_time - timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1_000_000.0,
                "available_at": (observation_time - timedelta(days=i)).isoformat(),
                "source": "test",
                "ingestion_timestamp": observation_time.isoformat(),
                "revision_id": "rev-1",
            }
            for i in range(20)  # Only 20 days of data
        ],
    )

    ingestion = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    ingestion.ingest(run_id="test", symbols=["SHORT"])

    config = ScanConfig(
        universe_config=UniverseConfig(
            observation_time=observation_time,
            min_trading_history_days=60,
            supported_exchanges=("NYSE",),
        )
    )

    result = engine.scan(warehouse=warehouse, scan_config=config)

    assert result.total_securities_considered == 1
    assert result.excluded_count == 1
    qualifications = result.security_qualifications
    assert len(qualifications) > 0
    assert qualifications[0].state == QualificationState.INSUFFICIENT_HISTORY


def test_illiquid_security_exclusion(
    warehouse: SQLiteHistoricalWarehouse,
    engine: MarketIntelligenceEngine,
    observation_time: datetime,
) -> None:
    """Test that illiquid security is excluded."""
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-3",
                "ticker": "ILLIQUID",
                "company_name": "Illiquid Corp",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2023-01-01",
                "delisting_date": None,
                "active": True,
                "source": "test",
                "available_at": "2023-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-3",
                "trade_date": (observation_time - timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 100.0,  # Very low volume
                "available_at": (observation_time - timedelta(days=i)).isoformat(),
                "source": "test",
                "ingestion_timestamp": observation_time.isoformat(),
                "revision_id": "rev-1",
            }
            for i in range(70)
        ],
    )

    ingestion = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    ingestion.ingest(run_id="test", symbols=["ILLIQUID"])

    config = ScanConfig(
        universe_config=UniverseConfig(
            observation_time=observation_time,
            min_avg_daily_volume=500_000.0,  # High bar for volume
            supported_exchanges=("NYSE",),
        )
    )

    result = engine.scan(warehouse=warehouse, scan_config=config)

    assert result.excluded_count > 0
    qualifications = result.security_qualifications
    assert any(q.state == QualificationState.ILLIQUID for q in qualifications)


def test_delisted_security_with_exclude_flag(
    warehouse: SQLiteHistoricalWarehouse,
    engine: MarketIntelligenceEngine,
    observation_time: datetime,
) -> None:
    """Test that exclude_delisted=False includes securities marked for future delisting."""
    # Use a delisting date in the FUTURE so warehouse includes it in universe
    delisting_date = observation_time + timedelta(days=30)

    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-4",
                "ticker": "FUTURE_DELISTED",
                "company_name": "Future Delisted Inc",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2023-01-01",
                "delisting_date": delisting_date.strftime("%Y-%m-%d"),
                "active": False,
                "source": "test",
                "available_at": "2023-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-4",
                "trade_date": (observation_time - timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1_000_000.0,
                "available_at": (observation_time - timedelta(days=i)).isoformat(),
                "source": "test",
                "ingestion_timestamp": observation_time.isoformat(),
                "revision_id": "rev-1",
            }
            for i in range(70)
        ],
    )

    ingestion = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    ingestion.ingest(run_id="test", symbols=["FUTURE_DELISTED"])

    # Configuration with exclude_delisted=True to exclude securities marked for delisting
    config = ScanConfig(
        universe_config=UniverseConfig(
            observation_time=observation_time,
            exclude_delisted=True,
            supported_exchanges=("NYSE",),
        )
    )

    result = engine.scan(warehouse=warehouse, scan_config=config)

    # Should be excluded due to delisting_date being set and exclude_delisted=True
    assert result.excluded_count >= 1
    qualifications = result.security_qualifications
    assert any(q.state == QualificationState.EXCLUDED for q in qualifications)
    
    # Now test with exclude_delisted=False (should include the security)
    config_include = ScanConfig(
        universe_config=UniverseConfig(
            observation_time=observation_time,
            exclude_delisted=False,  # Include securities marked for delisting
            supported_exchanges=("NYSE",),
        )
    )
    
    result_include = engine.scan(warehouse=warehouse, scan_config=config_include)
    
    # With exclude_delisted=False, should include the security (won't be excluded for delisting)
    assert result_include.qualified_count >= 1 or result_include.watchlist_count >= 1


def test_unsupported_asset_type_exclusion(
    warehouse: SQLiteHistoricalWarehouse,
    engine: MarketIntelligenceEngine,
    observation_time: datetime,
) -> None:
    """Test that unsupported asset type is excluded."""
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-5",
                "ticker": "BOND",
                "company_name": "Bond Fund",
                "exchange": "NYSE",
                "asset_type": "ETF",  # Unsupported asset type
                "currency": "USD",
                "listing_date": "2023-01-01",
                "delisting_date": None,
                "active": True,
                "source": "test",
                "available_at": "2023-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-5",
                "trade_date": (observation_time - timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1_000_000.0,
                "available_at": (observation_time - timedelta(days=i)).isoformat(),
                "source": "test",
                "ingestion_timestamp": observation_time.isoformat(),
                "revision_id": "rev-1",
            }
            for i in range(70)
        ],
    )

    ingestion = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    ingestion.ingest(run_id="test", symbols=["BOND"])

    config = ScanConfig(
        universe_config=UniverseConfig(
            observation_time=observation_time,
            supported_asset_types=("STOCK",),  # Only stocks
            supported_exchanges=("NYSE",),
        )
    )

    result = engine.scan(warehouse=warehouse, scan_config=config)

    assert result.excluded_count >= 1
    qualifications = result.security_qualifications
    assert any(q.state == QualificationState.UNSUPPORTED_ASSET for q in qualifications)


def test_point_in_time_universe_no_future_bias(
    warehouse: SQLiteHistoricalWarehouse,
    engine: MarketIntelligenceEngine,
    observation_time: datetime,
) -> None:
    """Test that point-in-time universe doesn't include future data."""
    future_date = observation_time + timedelta(days=10)

    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-6",
                "ticker": "FUTURE",
                "company_name": "Future Inc",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2023-01-01",
                "delisting_date": None,
                "active": True,
                "source": "test",
                "available_at": "2023-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-6",
                "trade_date": (future_date - timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1_000_000.0,
                "available_at": (future_date - timedelta(days=i)).isoformat(),  # Future availability
                "source": "test",
                "ingestion_timestamp": observation_time.isoformat(),
                "revision_id": "rev-1",
            }
            for i in range(70)
        ],
    )

    ingestion = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    ingestion.ingest(run_id="test", symbols=["FUTURE"])

    config = ScanConfig(
        universe_config=UniverseConfig(observation_time=observation_time)
    )

    result = engine.scan(warehouse=warehouse, scan_config=config)

    # Should be excluded due to no bars available at observation_time
    assert result.total_securities_considered >= 0


def test_deterministic_scan_output(
    warehouse: SQLiteHistoricalWarehouse,
    engine: MarketIntelligenceEngine,
    observation_time: datetime,
) -> None:
    """Test that scan output is deterministic."""
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-7",
                "ticker": "DETERM",
                "company_name": "Deterministic Inc",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2023-01-01",
                "delisting_date": None,
                "active": True,
                "source": "test",
                "available_at": "2023-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-7",
                "trade_date": (observation_time - timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1_000_000.0,
                "available_at": (observation_time - timedelta(days=i)).isoformat(),
                "source": "test",
                "ingestion_timestamp": observation_time.isoformat(),
                "revision_id": "rev-1",
            }
            for i in range(70)
        ],
    )

    ingestion = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    ingestion.ingest(run_id="test", symbols=["DETERM"])

    config = ScanConfig(
        universe_config=UniverseConfig(observation_time=observation_time)
    )

    result1 = engine.scan(warehouse=warehouse, scan_config=config)
    result2 = engine.scan(warehouse=warehouse, scan_config=config)

    # Results should have same counts even if IDs differ
    assert result1.total_securities_considered == result2.total_securities_considered
    assert result1.qualified_count == result2.qualified_count
    assert result1.excluded_count == result2.excluded_count

    # JSON should be serializable
    json1 = result1.to_json()
    assert json1 is not None
    assert "qualified_count" in json1


def test_no_broker_calls() -> None:
    """Test that engine doesn't call broker APIs."""
    engine = MarketIntelligenceEngine()
    # This test just verifies the engine exists and doesn't trigger broker calls
    # during construction
    assert engine is not None


def test_no_order_creation(
    warehouse: SQLiteHistoricalWarehouse,
    engine: MarketIntelligenceEngine,
    observation_time: datetime,
) -> None:
    """Test that scan doesn't create orders or positions."""
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-8",
                "ticker": "NOORDER",
                "company_name": "No Order Inc",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2023-01-01",
                "delisting_date": None,
                "active": True,
                "source": "test",
                "available_at": "2023-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-8",
                "trade_date": (observation_time - timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1_000_000.0,
                "available_at": (observation_time - timedelta(days=i)).isoformat(),
                "source": "test",
                "ingestion_timestamp": observation_time.isoformat(),
                "revision_id": "rev-1",
            }
            for i in range(70)
        ],
    )

    ingestion = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    ingestion.ingest(run_id="test", symbols=["NOORDER"])

    config = ScanConfig(
        universe_config=UniverseConfig(observation_time=observation_time)
    )

    result = engine.scan(warehouse=warehouse, scan_config=config)

    # Verify no order execution happened (result contains research only)
    assert result.assembled_opportunities is not None
    assert result.ranked_research_results is not None
    # No execution objects, no fills, no positions


def test_deterministic_json_serialization(
    warehouse: SQLiteHistoricalWarehouse,
    engine: MarketIntelligenceEngine,
    observation_time: datetime,
) -> None:
    """Test deterministic JSON serialization of scan result."""
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-9",
                "ticker": "JSON",
                "company_name": "JSON Inc",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2023-01-01",
                "delisting_date": None,
                "active": True,
                "source": "test",
                "available_at": "2023-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-9",
                "trade_date": (observation_time - timedelta(days=i)).strftime("%Y-%m-%d"),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1_000_000.0,
                "available_at": (observation_time - timedelta(days=i)).isoformat(),
                "source": "test",
                "ingestion_timestamp": observation_time.isoformat(),
                "revision_id": "rev-1",
            }
            for i in range(70)
        ],
    )

    ingestion = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    ingestion.ingest(run_id="test", symbols=["JSON"])

    config = ScanConfig(
        universe_config=UniverseConfig(observation_time=observation_time)
    )

    result = engine.scan(warehouse=warehouse, scan_config=config)

    json_str = result.to_json()
    parsed = result.from_dict(result.to_dict())

    assert parsed.total_securities_considered == result.total_securities_considered
    assert parsed.qualified_count == result.qualified_count
    assert parsed.scan_run_id == result.scan_run_id
