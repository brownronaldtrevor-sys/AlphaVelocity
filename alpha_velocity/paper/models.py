from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class PaperPosition:
    symbol: str
    quantity: int
    average_cost: float
    last_price: float
    target_weight_pct: float = 0.0
    stop_price: float | None = None
    target_price: float | None = None

    @property
    def market_value(self) -> float:
        return self.quantity * self.last_price

    @property
    def unrealized_pnl(self) -> float:
        return self.quantity * (self.last_price - self.average_cost)

@dataclass
class PaperOrder:
    symbol: str
    action: str
    quantity: int
    reference_price: float
    reason: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class PaperFill:
    symbol: str
    action: str
    quantity: int
    fill_price: float
    commission: float
    slippage: float
    filled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class PaperAccount:
    cash: float
    starting_equity: float
    positions: dict[str, PaperPosition]

    def equity(self) -> float:
        return self.cash + sum(p.market_value for p in self.positions.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "cash": self.cash,
            "starting_equity": self.starting_equity,
            "equity": self.equity(),
            "positions": {k: asdict(v) for k, v in self.positions.items()},
        }
