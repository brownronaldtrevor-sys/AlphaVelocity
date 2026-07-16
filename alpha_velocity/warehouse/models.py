from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    SECURITY_CREATED = "SECURITY_CREATED"
    TICKER_CHANGE = "TICKER_CHANGE"
    DELISTING = "DELISTING"
    BAR_INGESTED = "BAR_INGESTED"
    QUALITY_FAILURE = "QUALITY_FAILURE"


@dataclass(frozen=True)
class CanonicalEvent:
    event_type: EventType
    security_id: str
    occurred_at: datetime
    available_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CorporateAction:
    security_id: str
    action_type: str
    effective_date: datetime
    from_ticker: str | None = None
    to_ticker: str | None = None
    source: str | None = None
    available_at: datetime | None = None
    revision_id: str | None = None


@dataclass(frozen=True)
class SecurityRecord:
    security_id: str
    ticker: str
    company_name: str
    exchange: str
    asset_type: str
    currency: str
    listing_date: datetime
    delisting_date: datetime | None
    active: bool
    source: str
    available_at: datetime
    revision_id: str | None = None


@dataclass(frozen=True)
class TickerHistoryEntry:
    security_id: str
    ticker: str
    valid_from: datetime
    valid_to: datetime | None
    active: bool
    available_at: datetime
    revision_id: str | None = None


@dataclass(frozen=True)
class BarRecord:
    security_id: str
    trade_date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    available_at: datetime
    source: str
    ingestion_timestamp: datetime
    revision_id: str | None = None
    quality_status: str = "VALID"
    bar_type: str = "RAW"
