from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from alpha_velocity.market.bars import Bar


class EventType(str, Enum):
    MARKET_DATA = "MARKET_DATA"
    OPPORTUNITY = "OPPORTUNITY"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    DELISTING = "DELISTING"
    END_OF_DAY = "END_OF_DAY"


if TYPE_CHECKING:
    from alpha_velocity.opportunity.models import Opportunity


@dataclass(frozen=True)
class Event:
    event_time: datetime
    available_at: datetime
    sequence: int
    source: str = "unknown"

    def __post_init__(self) -> None:
        if self.available_at > self.event_time:
            raise ValueError("available_at cannot exceed event_time")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")


@dataclass(frozen=True)
class MarketDataEvent(Event):
    symbol: str = ""
    bar: Bar | None = None
    event_type: EventType = EventType.MARKET_DATA

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.symbol and self.bar is None:
            raise ValueError("market data requires a symbol or bar")


@dataclass(frozen=True)
class MarketBarEvent:
    """Market bar event for compatibility with existing tests."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class OpportunityEvent(Event):
    opportunity_id: str = ""
    opportunity: "Opportunity | None" = None
    event_type: EventType = EventType.OPPORTUNITY


@dataclass(frozen=True)
class SignalEvent(Event):
    strategy_id: str = ""
    symbol: str = ""
    side: str = "BUY"
    strength: float = 0.0
    reference_price: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    event_type: EventType = EventType.SIGNAL


class OrderEvent:
    """Order event for compatibility with existing tests."""
    def __init__(self, order_id, strategy_id, symbol, event_time, action, quantity, order_type):
        self.order_id = order_id
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.event_time = event_time
        self.timestamp = event_time  # Alias for compatibility
        self.available_at = event_time
        self.action = action
        self.quantity = quantity
        self.order_type = order_type
        self.limit_price = None
        self.stop_price = None
        self.sequence = 1
        self.source = ''
        self.event_type = EventType.ORDER


@dataclass(frozen=True)
class FillEvent(Event):
    order_id: str = ""
    symbol: str = ""
    action: str = "BUY"
    quantity: int = 0
    fill_price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    event_type: EventType = EventType.FILL


@dataclass(frozen=True)
class CorporateActionEvent(Event):
    symbol: str = ""
    action_type: str = "SPLIT"
    ratio: float | None = None
    cash_amount: float | None = None
    event_type: EventType = EventType.CORPORATE_ACTION


@dataclass(frozen=True)
class DelistingEvent(Event):
    symbol: str = ""
    event_type: EventType = EventType.DELISTING


@dataclass(frozen=True)
class EndOfDayEvent(Event):
    symbol: str = ""
    event_type: EventType = EventType.END_OF_DAY

