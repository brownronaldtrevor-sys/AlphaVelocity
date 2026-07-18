from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from alpha_velocity.event.models import SignalEvent


class StrategyBase(ABC):
    """Read-only strategy interface for research backtests."""

    def __init__(self, quantity: int = 1) -> None:
        self.quantity = quantity

    @abstractmethod
    def generate(self, context: dict[str, Any]) -> list[SignalEvent]:
        """Generate signals from the current market context.

        A strategy may only:
        - Read current market state
        - Read portfolio state
        - Emit SignalEvent objects

        A strategy may NOT:
        - Mutate cash or positions
        - Create fills
        - Approve risk
        - Call a broker
        - Bypass governance
        """


class BuyAndHoldBaseline(StrategyBase):
    """Research baseline: buy once at the first bar, hold to the end."""

    def generate(self, context: dict[str, Any]) -> list[SignalEvent]:
        bar = context["bar"]
        index = context["index"]

        if index == 0:
            return [
                SignalEvent(
                    event_time=bar.timestamp,
                    available_at=bar.timestamp,
                    sequence=1,
                    source="buy_and_hold",
                    strategy_id="buy_and_hold",
                    symbol=bar.symbol,
                    side="BUY",
                    strength=1.0,
                    reference_price=bar.close,
                    metadata={"order_type": "MKT", "quantity": self.quantity},
                )
            ]
        return []


class MovingAverageCrossoverBaseline(StrategyBase):
    """Research baseline: buy on SMA20 > SMA50 crossover."""

    def __init__(self, quantity: int = 1, fast_period: int = 20, slow_period: int = 50) -> None:
        super().__init__(quantity)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.prior_fast_avg: float | None = None
        self.prior_slow_avg: float | None = None

    def generate(self, context: dict[str, Any]) -> list[SignalEvent]:
        bar = context["bar"]
        portfolio = context.get("portfolio")

        bar_history = getattr(context.get("strategy"), "bar_history", [])
        if not bar_history or len(bar_history) < self.slow_period:
            return []

        recent_closes = [b.close for b in bar_history[-self.slow_period :]]
        fast_avg = sum(recent_closes[-self.fast_period :]) / self.fast_period
        slow_avg = sum(recent_closes) / self.slow_period

        if self.prior_fast_avg is None or self.prior_slow_avg is None:
            self.prior_fast_avg = fast_avg
            self.prior_slow_avg = slow_avg
            return []

        if self.prior_fast_avg <= self.prior_slow_avg and fast_avg > slow_avg:
            return [
                SignalEvent(
                    event_time=bar.timestamp,
                    available_at=bar.timestamp,
                    sequence=1,
                    source="moving_average_crossover",
                    strategy_id="ma_crossover",
                    symbol=bar.symbol,
                    side="BUY",
                    strength=0.8,
                    reference_price=bar.close,
                    metadata={"order_type": "MKT", "quantity": self.quantity},
                )
            ]
        elif self.prior_fast_avg >= self.prior_slow_avg and fast_avg < slow_avg:
            return [
                SignalEvent(
                    event_time=bar.timestamp,
                    available_at=bar.timestamp,
                    sequence=1,
                    source="moving_average_crossover",
                    strategy_id="ma_crossover",
                    symbol=bar.symbol,
                    side="SELL",
                    strength=0.8,
                    reference_price=bar.close,
                    metadata={"order_type": "MKT", "quantity": self.quantity},
                )
            ]

        self.prior_fast_avg = fast_avg
        self.prior_slow_avg = slow_avg
        return []


class ValidationGatedOpportunityBaseline(StrategyBase):
    """Research baseline: rank Opportunity objects by validation status and score."""

    def __init__(self, quantity: int = 1) -> None:
        super().__init__(quantity)
        self.triggered_once = False

    def generate(self, context: dict[str, Any]) -> list[SignalEvent]:
        if self.triggered_once:
            return []

        bar = context["bar"]
        opportunities = context.get("opportunities", [])

        if not opportunities:
            return []

        ranked = sorted(
            opportunities,
            key=lambda opp: (opp.calibration_status == "CALIBRATED", opp.expected_value_score or 0.0),
            reverse=True,
        )

        top_opp = ranked[0]

        if top_opp.expected_value_score and top_opp.expected_value_score > 0:
            self.triggered_once = True
            return [
                SignalEvent(
                    event_time=bar.timestamp,
                    available_at=bar.timestamp,
                    sequence=1,
                    source="validation_gated_opportunity",
                    strategy_id="validation_gated",
                    symbol=bar.symbol,
                    side="BUY",
                    strength=top_opp.expected_value_score,
                    reference_price=bar.close,
                    metadata={
                        "order_type": "MKT",
                        "quantity": self.quantity,
                        "opportunity_id": top_opp.opportunity_id,
                    },
                )
            ]

        return []
