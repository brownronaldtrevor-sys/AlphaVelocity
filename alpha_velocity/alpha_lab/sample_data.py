"""Alpha Lab sample data generator for demonstration and testing."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import csv

from alpha_velocity.warehouse import SQLiteHistoricalWarehouse


def generate_sample_alpha_lab_data(db_path: str = "./warehouse.db") -> tuple[int, int]:
    """Generate sample equity and futures data for Alpha Lab.

    Returns:
        (equities_count, futures_count)
    """
    warehouse = SQLiteHistoricalWarehouse(path=db_path)

    # Sample equities for Swing Repricing
    equities = [
        {
            "security_id": "eq-aapl",
            "ticker": "AAPL",
            "company_name": "Apple Inc",
            "exchange": "NASDAQ",
            "asset_type": "STOCK",
        },
        {
            "security_id": "eq-msft",
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "exchange": "NASDAQ",
            "asset_type": "STOCK",
        },
        {
            "security_id": "eq-tsla",
            "ticker": "TSLA",
            "company_name": "Tesla Inc",
            "exchange": "NASDAQ",
            "asset_type": "STOCK",
        },
        {
            "security_id": "eq-nvda",
            "ticker": "NVDA",
            "company_name": "NVIDIA Corporation",
            "exchange": "NASDAQ",
            "asset_type": "STOCK",
        },
        {
            "security_id": "eq-nflx",
            "ticker": "NFLX",
            "company_name": "Netflix Inc",
            "exchange": "NASDAQ",
            "asset_type": "STOCK",
        },
    ]

    # Sample futures for Turtle Trend
    futures = [
        {
            "security_id": "fut-es",
            "ticker": "ESZ24",
            "company_name": "E-mini S&P 500 Dec 2024",
            "exchange": "CME",
            "asset_type": "FUTURE",
        },
        {
            "security_id": "fut-nq",
            "ticker": "NQZ24",
            "company_name": "E-mini NASDAQ Dec 2024",
            "exchange": "CME",
            "asset_type": "FUTURE",
        },
        {
            "security_id": "fut-cl",
            "ticker": "CLZ24",
            "company_name": "WTI Crude Oil Dec 2024",
            "exchange": "CME",
            "asset_type": "FUTURE",
        },
        {
            "security_id": "fut-gc",
            "ticker": "GCZ24",
            "company_name": "Gold Futures Dec 2024",
            "exchange": "CME",
            "asset_type": "FUTURE",
        },
    ]

    all_securities = equities + futures

    # Add securities to warehouse
    for security in all_securities:
        try:
            warehouse._conn.execute(
                """
                INSERT OR REPLACE INTO securities
                (security_id, ticker, company_name, exchange, asset_type, currency, listing_date, active, source, available_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    security["security_id"],
                    security["ticker"],
                    security["company_name"],
                    security["exchange"],
                    security["asset_type"],
                    "USD",
                    "2020-01-01",
                    1,
                    "SAMPLE_DATA",
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        except Exception as e:
            print(f"Warning: Could not add security {security['ticker']}: {e}")

    warehouse._conn.commit()
    return (len(equities), len(futures))


def generate_sample_csv_data(output_dir: str = "./sample_data") -> int:
    """Generate sample CSV files for equities and futures.

    Returns:
        Number of files generated
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    base_date = datetime(2024, 1, 15, tzinfo=timezone.utc)
    samples = [
        {
            "symbol": "AAPL",
            "start_price": 180.00,
            "description": "Apple - Triggered Swing Repricing candidate",
        },
        {
            "symbol": "MSFT",
            "start_price": 380.00,
            "description": "Microsoft - Waiting for Trigger candidate",
        },
        {
            "symbol": "TSLA",
            "start_price": 240.00,
            "description": "Tesla - Excluded due to capital structure",
        },
        {
            "symbol": "ESZ24",
            "start_price": 5000.0,
            "description": "E-mini S&P 500 - Turtle Trend long breakout",
        },
        {
            "symbol": "NQZ24",
            "start_price": 20000.0,
            "description": "E-mini NASDAQ - Turtle Trend short breakout",
        },
        {
            "symbol": "CLZ24",
            "start_price": 75.50,
            "description": "Crude Oil - Waiting for breakout",
        },
    ]

    file_count = 0
    for sample in samples:
        symbol = sample["symbol"]
        csv_path = output_path / f"{symbol}_sample.csv"

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["date", "open", "high", "low", "close", "volume", "available_at"]
            )

            # Generate 250 bars (1 year)
            price = sample["start_price"]
            for i in range(250):
                date = base_date - timedelta(days=250 - i)
                open_p = price
                high_p = price * (1 + 0.02)  # 2% intraday high
                low_p = price * (1 - 0.01)  # 1% intraday low
                close_p = price * (1 + (0.005 if i % 2 == 0 else -0.003))
                volume = 1_000_000 + (i * 100)

                writer.writerow(
                    [
                        date.strftime("%Y-%m-%d"),
                        f"{open_p:.2f}",
                        f"{high_p:.2f}",
                        f"{low_p:.2f}",
                        f"{close_p:.2f}",
                        volume,
                        date.strftime("%Y-%m-%d"),
                    ]
                )
                price = close_p

        print(f"Generated: {csv_path} - {sample['description']}")
        file_count += 1

    return file_count
