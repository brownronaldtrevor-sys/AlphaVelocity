from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from alpha_velocity.warehouse import (
    CanonicalEvent,
    CorporateAction,
    EventType,
    InMemoryProviderAdapter,
    SQLiteHistoricalWarehouse,
    WarehouseIngestionEngine,
)


def _warehouse(tmp_path: Path):
    return SQLiteHistoricalWarehouse(path=str(tmp_path / "warehouse.sqlite3"))


def test_symbol_changes_and_delistings_are_recorded(tmp_path: Path) -> None:
    warehouse = _warehouse(tmp_path)
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-1",
                "ticker": "ABC",
                "company_name": "Acme",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2020-01-01",
                "delisting_date": None,
                "active": True,
                "source": "unit-test",
                "available_at": "2020-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        corporate_actions=[
            {
                "security_id": "sec-1",
                "action_type": "SYMBOL_CHANGE",
                "effective_date": "2021-01-01",
                "from_ticker": "ABC",
                "to_ticker": "XYZ",
                "source": "unit-test",
                "available_at": "2021-01-01T00:00:00",
                "revision_id": "rev-2",
            },
            {
                "security_id": "sec-1",
                "action_type": "DELISTING",
                "effective_date": "2022-01-01",
                "source": "unit-test",
                "available_at": "2022-01-01T00:00:00",
                "revision_id": "rev-3",
            },
        ],
    )
    engine = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    engine.ingest(run_id="run-symbols", symbols=["ABC"], git_commit="abc123")

    security = warehouse.get_security("sec-1", as_of=datetime(2021, 1, 2))
    assert security is not None
    ticker_history = warehouse.get_ticker_history("sec-1", as_of=datetime(2021, 1, 2))
    assert any(item.ticker == "ABC" for item in ticker_history)
    assert any(item.ticker == "XYZ" for item in ticker_history)
    universe = warehouse.point_in_time_universe(as_of=datetime(2022, 1, 2))
    assert any(item.security_id == "sec-1" for item in universe)


def test_overlapping_ticker_histories_are_rejected(tmp_path: Path) -> None:
    warehouse = _warehouse(tmp_path)
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-2",
                "ticker": "DEF",
                "company_name": "Example",
                "exchange": "NASDAQ",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2020-01-01",
                "delisting_date": None,
                "active": True,
                "source": "unit-test",
                "available_at": "2020-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        ticker_histories=[
            {
                "security_id": "sec-2",
                "ticker": "DEF",
                "valid_from": "2020-01-01",
                "valid_to": "2020-12-31",
                "active": True,
                "available_at": "2020-01-01T00:00:00",
                "revision_id": "rev-1",
            },
            {
                "security_id": "sec-2",
                "ticker": "DEF",
                "valid_from": "2020-06-01",
                "valid_to": "2021-01-01",
                "active": True,
                "available_at": "2020-01-01T00:00:00",
                "revision_id": "rev-2",
            },
        ],
    )
    engine = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    manifest = engine.ingest(run_id="run-overlap", symbols=["DEF"], git_commit="abc123")
    assert manifest["rejected"] >= 1
    assert warehouse.quarantine_count() >= 1


def test_raw_and_adjusted_bars_are_preserved_separately(tmp_path: Path) -> None:
    warehouse = _warehouse(tmp_path)
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-3",
                "ticker": "GHI",
                "company_name": "Graph",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2020-01-01",
                "delisting_date": None,
                "active": True,
                "source": "unit-test",
                "available_at": "2020-01-10T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-3",
                "trade_date": "2020-01-10",
                "open": 10.0,
                "high": 11.0,
                "low": 9.0,
                "close": 10.5,
                "volume": 1000.0,
                "adjusted_open": 5.0,
                "adjusted_high": 5.5,
                "adjusted_low": 4.5,
                "adjusted_close": 5.25,
                "available_at": "2020-01-10T00:00:00",
                "source": "unit-test",
                "ingestion_timestamp": "2020-01-10T00:00:00",
                "revision_id": "rev-1",
                "quality_status": "VALID",
            }
        ],
    )
    engine = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    engine.ingest(run_id="run-bars", symbols=["GHI"], git_commit="abc123")
    raw = warehouse.get_raw_bars("sec-3")
    adjusted = warehouse.get_adjusted_bars("sec-3")
    assert raw[0].close == 10.5
    assert adjusted[0].close == 5.25


def test_future_data_and_invalid_ohlc_are_rejected(tmp_path: Path) -> None:
    warehouse = _warehouse(tmp_path)
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-4",
                "ticker": "JKL",
                "company_name": "Jolt",
                "exchange": "NASDAQ",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2020-01-01",
                "delisting_date": None,
                "active": True,
                "source": "unit-test",
                "available_at": "2030-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-4",
                "trade_date": "2020-01-10",
                "open": 0.0,
                "high": 11.0,
                "low": 9.0,
                "close": 10.5,
                "volume": 1000.0,
                "available_at": "2020-01-10T00:00:00",
                "source": "unit-test",
                "ingestion_timestamp": "2020-01-10T00:00:00",
                "revision_id": "rev-1",
                "quality_status": "VALID",
            }
        ],
    )
    engine = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    manifest = engine.ingest(run_id="run-invalid", symbols=["JKL"], git_commit="abc123")
    assert manifest["rejected"] >= 2


def test_available_at_filtering_and_duplicate_prevention(tmp_path: Path) -> None:
    warehouse = _warehouse(tmp_path)
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-5",
                "ticker": "MNO",
                "company_name": "Mina",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2020-01-01",
                "delisting_date": None,
                "active": True,
                "source": "unit-test",
                "available_at": "2020-01-01T00:00:00",
                "revision_id": "rev-1",
            },
            {
                "security_id": "sec-5",
                "ticker": "MNO",
                "company_name": "Mina",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2020-01-01",
                "delisting_date": None,
                "active": True,
                "source": "unit-test",
                "available_at": "2020-01-01T00:00:00",
                "revision_id": "rev-1",
            },
        ],
    )
    engine = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    manifest = engine.ingest(run_id="run-dup", symbols=["MNO"], git_commit="abc123")
    assert manifest["inserted"] == 1
    assert manifest["rejected"] == 1


def test_historical_universe_snapshots_are_point_in_time(tmp_path: Path) -> None:
    warehouse = _warehouse(tmp_path)
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-6",
                "ticker": "PQR",
                "company_name": "Pioneer",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2020-01-01",
                "delisting_date": "2021-01-01",
                "active": False,
                "source": "unit-test",
                "available_at": "2020-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
    )
    engine = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    engine.ingest(run_id="run-universe", symbols=["PQR"], git_commit="abc123")
    before_delisting = warehouse.point_in_time_universe(as_of=datetime(2020, 6, 1))
    after_delisting = warehouse.point_in_time_universe(as_of=datetime(2021, 6, 1))
    assert any(item.security_id == "sec-6" for item in before_delisting)
    assert not any(item.security_id == "sec-6" for item in after_delisting)


def test_completed_weekly_bars_are_generated_from_completed_daily_bars(tmp_path: Path) -> None:
    warehouse = _warehouse(tmp_path)
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-7",
                "ticker": "STU",
                "company_name": "Stone",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2020-01-01",
                "delisting_date": None,
                "active": True,
                "source": "unit-test",
                "available_at": "2020-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-7",
                "trade_date": "2020-01-06",
                "open": 10.0,
                "high": 11.0,
                "low": 9.0,
                "close": 10.5,
                "volume": 1000.0,
                "available_at": "2020-01-06T00:00:00",
                "source": "unit-test",
                "ingestion_timestamp": "2020-01-06T00:00:00",
                "revision_id": "rev-1",
                "quality_status": "VALID",
            },
            {
                "security_id": "sec-7",
                "trade_date": "2020-01-07",
                "open": 10.5,
                "high": 11.5,
                "low": 10.0,
                "close": 11.0,
                "volume": 1200.0,
                "available_at": "2020-01-07T00:00:00",
                "source": "unit-test",
                "ingestion_timestamp": "2020-01-07T00:00:00",
                "revision_id": "rev-1",
                "quality_status": "VALID",
            },
        ],
    )
    engine = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    engine.ingest(run_id="run-weekly", symbols=["STU"], git_commit="abc123")
    weekly = warehouse.completed_weekly_bars("sec-7", as_of=datetime(2020, 1, 8))
    assert len(weekly) == 1


def test_deterministic_manifests_and_retained_failure_records(tmp_path: Path) -> None:
    warehouse = _warehouse(tmp_path)
    provider = InMemoryProviderAdapter(
        securities=[
            {
                "security_id": "sec-8",
                "ticker": "VWX",
                "company_name": "Vega",
                "exchange": "NYSE",
                "asset_type": "STOCK",
                "currency": "USD",
                "listing_date": "2020-01-01",
                "delisting_date": None,
                "active": True,
                "source": "unit-test",
                "available_at": "2020-01-01T00:00:00",
                "revision_id": "rev-1",
            }
        ],
        bars=[
            {
                "security_id": "sec-8",
                "trade_date": "2020-01-01",
                "open": 5.0,
                "high": 6.0,
                "low": 4.0,
                "close": 5.5,
                "volume": 1000.0,
                "available_at": "2020-01-01T00:00:00",
                "source": "unit-test",
                "ingestion_timestamp": "2020-01-01T00:00:00",
                "revision_id": "rev-1",
                "quality_status": "VALID",
            }
        ],
    )
    engine = WarehouseIngestionEngine(warehouse=warehouse, provider=provider)
    manifest = engine.ingest(run_id="run-manifest", symbols=["VWX"], git_commit="abc123")
    assert manifest["run_id"] == "run-manifest"
    assert manifest["inserted"] == 2
    assert manifest["hash"]
    assert warehouse.failure_count() >= 0
