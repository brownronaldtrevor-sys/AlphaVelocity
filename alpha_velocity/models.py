from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal


class AssetClass(str, Enum):
    STOCK = "STOCK"
    FUTURE = "FUTURE"
    OPTION = "OPTION"


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ConvictionTier(str, Enum):
    NORMAL = "NORMAL"
    STRONG = "STRONG"
    EXCEPTIONAL = "EXCEPTIONAL"
    GENERATIONAL = "GENERATIONAL"


@dataclass(frozen=True)
class Instrument:
    symbol: str
    asset_class: AssetClass
    exchange: str = "SMART"
    currency: str = "USD"
    expiry: str | None = None
    multiplier: str | None = None
    primary_exchange: str | None = None


@dataclass(frozen=True)
class SignalProposal:
    strategy_id: str
    instrument: Instrument
    side: Side
    entry_price: float
    stop_price: float
    target_price: float
    probability_target_before_stop: float
    expected_holding_days: float
    expected_return_pct: float
    conviction_tier: ConvictionTier
    thesis: str
    model_version: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def risk_per_unit(self) -> float:
        return abs(self.entry_price - self.stop_price)

    @property
    def reward_per_unit(self) -> float:
        return abs(self.target_price - self.entry_price)

    @property
    def reward_to_risk(self) -> float:
        if self.risk_per_unit <= 0:
            return 0.0
        return self.reward_per_unit / self.risk_per_unit

    @property
    def alpha_velocity(self) -> float:
        days = max(self.expected_holding_days, 1.0)
        return (
            self.probability_target_before_stop
            * self.expected_return_pct
            * max(self.reward_to_risk, 0.0)
            / days
        )


@dataclass(frozen=True)
class AccountState:
    net_liquidation: float
    available_funds: float
    gross_position_value: float
    daily_pnl: float
    open_orders: int = 0


@dataclass(frozen=True)
class PositionState:
    symbol: str
    quantity: float
    market_price: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.market_price


@dataclass(frozen=True)
class ApprovedOrderPlan:
    proposal: SignalProposal
    quantity: int
    estimated_notional: float
    estimated_dollar_risk: float
    allocation_pct: float
    approval_reason: str


@dataclass(frozen=True)
class Rejection:
    reason: str
