from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SentimentSource(str, Enum):
    SEC_FILING = "SEC_FILING"
    EARNINGS_CALL = "EARNINGS_CALL"
    PRESS_RELEASE = "PRESS_RELEASE"
    NEWS = "NEWS"
    ANALYST = "ANALYST"
    SOCIAL = "SOCIAL"


@dataclass(frozen=True)
class SentimentDocument:
    document_id: str
    source: SentimentSource
    issuer: str
    published_at: datetime
    available_at: datetime
    text: str
    speaker: str | None = None
    section: str | None = None
    revision_id: str | None = None


@dataclass(frozen=True)
class SentimentFeatureVector:
    issuer: str
    as_of: datetime
    source: SentimentSource
    document_count: int
    tone: float
    uncertainty: float
    optimism: float
    negativity: float
    litigation_risk: float
    liquidity_concern: float
    demand_strength: float
    pricing_power: float
    guidance_change: float
    evasiveness: float
    novelty: float
    contradiction: float
    source_reliability: float
