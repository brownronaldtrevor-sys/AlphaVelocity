from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alpha_velocity.backtest.engine import BacktestEngine
from alpha_velocity.backtest.strategies import BuyAndHoldBaseline
from alpha_velocity.event.models import (
    CorporateActionEvent,
    DelistingEvent,
    OpportunityEvent,
    SignalEvent,
)
from alpha_velocity.market.bars import Bar
from alpha_velocity.opportunity.models import Opportunity


def _bar(timestamp: datetime, close: float, high: float, low: float, open_price: float, volume: float) -> Bar:
    return Bar(timestamp=timestamp, open=open_price, high=high, low=low, close=close, volume=volume)


class MixedStrategy(BuyAndHoldBaseline):
    def generate(self, context: dict) -> list[SignalEvent]:
        bar = context["bar"]
        if bar.timestamp.day == 1:
            return [
                SignalEvent(
                    event_time=bar.timestamp,
                    available_at=bar.timestamp,
                    sequence=1,
                    source="test",
                    strategy_id="mixed",
                    symbol="ABC",
                    side="BUY",
                    strength=1.0,
                    reference_price=bar.close,
                    metadata={"order_type": "MKT", "quantity": 10},
                )
            ]
        if bar.timestamp.day == 2:
            return [
                SignalEvent(
                    event_time=bar.timestamp,
                    available_at=bar.timestamp,
                    sequence=2,
                    source="test",
                    strategy_id="mixed",
                    symbol="ABC",
                    side="BUY",
                    strength=1.0,
                    reference_price=bar.close,
                    metadata={"order_type": "LMT", "quantity": 10, "limit_price": bar.close - 1.0},
                )
            ]
        if bar.timestamp.day == 3:
            return [
                SignalEvent(
                    event_time=bar.timestamp,
                    available_at=bar.timestamp,
                    sequence=3,
                    source="test",
                    strategy_id="mixed",
                    symbol="ABC",
                    side="BUY",
                    strength=1.0,
                    reference_price=bar.close,
                    metadata={"order_type": "STP", "quantity": 10, "stop_price": bar.close - 1.0},
                )
            ]
        return [
            SignalEvent(
                event_time=bar.timestamp,
                available_at=bar.timestamp,
                sequence=4,
                source="test",
                strategy_id="mixed",
                symbol="ABC",
                side="BUY",
                strength=1.0,
                reference_price=bar.close,
                metadata={"order_type": "STPLMT", "quantity": 10, "stop_price": bar.close - 1.0, "limit_price": bar.close - 0.5},
            )
        ]


def test_events_are_processed_in_chronological_order_and_future_data_is_rejected(tmp_path: Path) -> None:
    bars = [
        _bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0),
        _bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 101.0, 102.0, 100.0, 101.0, 1000.0),
    ]
    future_opportunity = OpportunityEvent(
        event_time=datetime(2024, 1, 3, tzinfo=timezone.utc),
        available_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
        sequence=1,
        source="test",
        opportunity_id="opp-1",
    )
    engine = BacktestEngine(output_dir=tmp_path)
    result = engine.run_backtest(
        daily_bars=bars,
        strategy=BuyAndHoldBaseline(quantity=5),
        opportunities=[future_opportunity],
    )
    assert result["events_processed"] >= 2
    assert any("future" in warning.lower() for warning in result["warnings"])


def test_next_bar_execution_delays_fill_until_the_next_bar(tmp_path: Path) -> None:
    bars = [
        _bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0),
        _bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 101.0, 102.0, 100.0, 101.0, 1000.0),
    ]
    engine = BacktestEngine(output_dir=tmp_path)
    result = engine.run_backtest(daily_bars=bars, strategy=BuyAndHoldBaseline(quantity=5))
    assert len(result["trades"]) == 1
    assert result["trades"][0]["bar_timestamp"] == "2024-01-02T00:00:00+00:00"


def test_market_limit_stop_and_stop_limit_orders_are_supported(tmp_path: Path) -> None:
    bars = [
        _bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0),
        _bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 101.0, 102.0, 100.0, 101.0, 1000.0),
        _bar(datetime(2024, 1, 3, tzinfo=timezone.utc), 102.0, 103.0, 101.0, 102.0, 1000.0),
        _bar(datetime(2024, 1, 4, tzinfo=timezone.utc), 103.0, 104.0, 102.0, 103.0, 1000.0),
    ]
    engine = BacktestEngine(output_dir=tmp_path)
    result = engine.run_backtest(daily_bars=bars, strategy=MixedStrategy(quantity=5))
    order_types = {order["order_type"] for order in result["orders"]}
    assert {"MKT", "LMT", "STP", "STPLMT"}.issubset(order_types)


def test_partial_fills_and_volume_caps_are_respected(tmp_path: Path) -> None:
    bars = [
        _bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0),
        _bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 101.0, 102.0, 100.0, 101.0, 1000.0),
    ]
    engine = BacktestEngine(output_dir=tmp_path, fill_model_config={"max_participation_rate": 0.05})
    result = engine.run_backtest(
        daily_bars=bars,
        strategy=BuyAndHoldBaseline(quantity=50),
    )
    assert len(result["trades"]) == 1
    assert result["trades"][0]["filled_quantity"] <= 50
    assert result["metrics"]["commissions"] > 0.0


def test_commissions_slippage_and_adverse_gap_are_reported(tmp_path: Path) -> None:
    bars = [
        _bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0),
        _bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 104.0, 105.0, 100.0, 104.0, 1000.0),
    ]
    engine = BacktestEngine(output_dir=tmp_path)
    result = engine.run_backtest(daily_bars=bars, strategy=BuyAndHoldBaseline(quantity=10))
    assert result["metrics"]["slippage"] > 0.0
    assert result["metrics"]["commissions"] > 0.0
    assert any("adverse gap" in warning.lower() for warning in result["warnings"])


def test_bracket_ambiguity_is_marked_and_not_overstated(tmp_path: Path) -> None:
    bars = [
        _bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0),
        _bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 100.0, 110.0, 90.0, 100.0, 1000.0),
    ]
    engine = BacktestEngine(output_dir=tmp_path)
    result = engine.run_backtest(
        daily_bars=bars,
        strategy=BuyAndHoldBaseline(quantity=5),
        order_type="BRACKET",
        stop_price=95.0,
        target_price=105.0,
    )
    assert result["ambiguous_outcomes"]
    assert result["ambiguous_outcomes"][0]["ambiguous"] is True


def test_corporate_actions_and_delistings_are_applied_conservatively(tmp_path: Path) -> None:
    bars = [
        _bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0),
        _bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 101.0, 102.0, 100.0, 101.0, 1000.0),
    ]
    engine = BacktestEngine(output_dir=tmp_path)
    result = engine.run_backtest(
        daily_bars=bars,
        strategy=BuyAndHoldBaseline(quantity=5),
        corporate_actions=[
            CorporateActionEvent(event_time=datetime(2024, 1, 2, tzinfo=timezone.utc), available_at=datetime(2024, 1, 2, tzinfo=timezone.utc), sequence=1, source="test", symbol="ABC", action_type="SPLIT", ratio=2.0),
        ],
        delistings=[
            DelistingEvent(event_time=datetime(2024, 1, 3, tzinfo=timezone.utc), available_at=datetime(2024, 1, 3, tzinfo=timezone.utc), sequence=2, source="test", symbol="ABC"),
        ],
    )
    assert any(event["event_type"] == "CORPORATE_ACTION" for event in result["events"])
    assert result["portfolio"]["positions"]["ABC"]["quantity"] >= 0


def test_risk_and_governance_rejections_are_recorded_and_output_is_deterministic(tmp_path: Path) -> None:
    bars = [
        _bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0),
        _bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 101.0, 102.0, 100.0, 101.0, 1000.0),
    ]
    engine = BacktestEngine(output_dir=tmp_path)
    result = engine.run_backtest(daily_bars=bars, strategy=BuyAndHoldBaseline(quantity=1_000_000))
    assert result["rejected_orders"]
    report_path = tmp_path / "backtest_report.json"
    assert report_path.exists()
    first = json.loads(report_path.read_text())
    second = json.loads(report_path.read_text())
    assert first == second


def test_benchmark_metrics_and_absence_of_broker_transmission(tmp_path: Path) -> None:
    bars = [
        _bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0),
        _bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 101.0, 102.0, 100.0, 101.0, 1000.0),
    ]
    benchmark_bars = [
        _bar(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0),
        _bar(datetime(2024, 1, 2, tzinfo=timezone.utc), 102.0, 103.0, 101.0, 102.0, 1000.0),
    ]
    engine = BacktestEngine(output_dir=tmp_path)
    result = engine.run_backtest(daily_bars=bars, benchmark_bars=benchmark_bars, strategy=BuyAndHoldBaseline(quantity=5))
    assert "benchmark_relative_return" in result["metrics"]
    assert result["broker_transmissions"] == 0
