"""
Opportunity ranking models: intrinsic value, timing signals, and expected swing value.

Provides immutable data structures for:
- Intrinsic opportunity analysis (capital-stack valuation, maturity risk)
- Timing opportunity analysis (technical setup, catalyst timing)
- Expected swing value (probability, magnitude, holding period, costs)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Mapping


class MaturityCondition(str, Enum):
    """Transparent debt maturity classification."""
    WELL_FUNDED = "WELL_FUNDED"
    MANAGEABLE = "MANAGEABLE"
    REFINANCING_REQUIRED = "REFINANCING_REQUIRED"
    HIGH_RISK = "HIGH_RISK"
    DISTRESSED = "DISTRESSED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class RankingState(str, Enum):
    """Research classification states (not trade instructions)."""
    HIGH_PRIORITY_TRIGGERED = "HIGH_PRIORITY_TRIGGERED"
    HIGH_PRIORITY_WAITING_FOR_TRIGGER = "HIGH_PRIORITY_WAITING_FOR_TRIGGER"
    WATCHLIST = "WATCHLIST"
    SPECULATIVE = "SPECULATIVE"
    REFINANCING_DEPENDENT = "REFINANCING_DEPENDENT"
    DISTRESSED_OPTIONALITY = "DISTRESSED_OPTIONALITY"
    AVOID = "AVOID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class IntrinsicOpportunityInput:
    """Full capital-stack valuation input for intrinsic analysis."""
    security_id: str
    observation_time: datetime
    source: str
    available_at: datetime
    
    # Market
    market_price: float | None = None
    shares_outstanding: float | None = None
    
    # Enterprise value inputs
    cash_and_equivalents: float | None = None
    total_debt: float | None = None
    net_debt: float | None = None
    preferred_equity: float | None = None
    minority_interest: float | None = None
    convertible_securities: float | None = None
    pension_obligations: float | None = None
    lease_liabilities: float | None = None
    
    # Dilution
    diluted_share_count: float | None = None
    potential_dilution_shares: float | None = None
    
    # Earnings power
    revenue: float | None = None
    normalized_earnings: float | None = None
    ebitda: float | None = None
    ebit: float | None = None
    free_cash_flow: float | None = None
    
    # Book value
    book_value: float | None = None
    tangible_book_value: float | None = None
    asset_value: float | None = None
    
    # Metadata
    reporting_period: str = ""
    filing_date: datetime | None = None
    revision_version: str = ""
    confidence_status: str = "UNKNOWN"
    
    def __post_init__(self) -> None:
        if self.available_at > self.observation_time:
            raise ValueError("intrinsic_input available_at cannot exceed observation_time")
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")


@dataclass(frozen=True)
class IntrinsicValuationScenario:
    """Single scenario (bear/base/bull) for intrinsic value estimation."""
    scenario: Literal["bear", "base", "bull"]
    enterprise_value: float
    net_debt_amount: float
    senior_claims: float  # Preferred, convertibles, etc.
    implied_equity_value: float
    diluted_share_count: float
    value_per_share: float
    assumptions: dict[str, str] = field(default_factory=dict)
    
    def upside_from_market(self, market_price: float) -> float | None:
        if market_price <= 0:
            return None
        return ((self.value_per_share - market_price) / market_price) * 100.0


@dataclass(frozen=True)
class DebtMaturityAnalysis:
    """Point-in-time debt maturity and refinancing analysis."""
    observation_time: datetime
    maturity_condition: MaturityCondition
    principal_outstanding: float
    next_12m_maturities: float
    next_24m_maturities: float
    revolver_available: float
    unrestricted_cash: float
    expected_fcf_before_maturity: float
    interest_expense_annual: float
    debt_to_ebitda: float | None = None
    interest_coverage: float | None = None
    covenant_risk: str = "UNKNOWN"
    estimated_liquidity_runway_days: int = 0
    notes: tuple[str, ...] = ()
    
    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")


@dataclass(frozen=True)
class TimingOpportunityCatalyst:
    """Known catalyst relevant to timing."""
    catalyst_type: str
    name: str
    available_at: datetime
    estimated_importance: Literal["low", "medium", "high", "transformational"] = "medium"
    expected_event_time: datetime | None = None
    occurred_at: datetime | None = None
    uncertainty_score: float = 0.5  # 0=certain, 1=uncertain
    status: str = "PENDING"
    evidence_source: str = ""
    
    def __post_init__(self) -> None:
        if self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")


@dataclass(frozen=True)
class ScoreComponentDetail:
    """Single component of a multi-part score."""
    name: str
    score: float  # 0-100
    weight: float  # 0-1
    contribution: float  # score * weight
    is_validated: bool
    data_available: bool
    explanation: str


@dataclass(frozen=True)
class RankedOpportunity:
    """Single opportunity with three-part ranking and evidence."""
    opportunity_id: str
    rank: int
    percentile: float  # 0-100
    
    # Three component scores (0-100)
    intrinsic_opportunity_score: float
    timing_opportunity_score: float
    expected_swing_value_score: float
    
    # Overall expected swing value ranking
    overall_swing_value_rank: float  # Weighted combination
    
    # Supporting scores
    intrinsic_components: tuple[ScoreComponentDetail, ...]
    timing_components: tuple[ScoreComponentDetail, ...]
    swing_value_components: tuple[ScoreComponentDetail, ...]
    
    # Status and classification
    ranking_state: RankingState
    validation_status: str  # VALIDATED, INCOMPLETE, INSUFFICIENT_DATA
    calibration_status: str  # CALIBRATED, UNCALIBRATED
    
    # Evidence
    positive_contributors: tuple[str, ...]
    negative_contributors: tuple[str, ...]
    disqualifiers: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence_lineage: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        if not (0.0 <= self.overall_swing_value_rank <= 100.0):
            raise ValueError("overall_swing_value_rank must be 0-100")
        if not (0.0 <= self.percentile <= 100.0):
            raise ValueError("percentile must be 0-100")


@dataclass(frozen=True)
class RankingRun:
    """Complete ranking run with configuration and results."""
    ranking_run_id: str
    observation_time: datetime
    universe_snapshot_id: str
    ranked_opportunities: tuple[RankedOpportunity, ...]
    
    # Configuration
    intrinsic_weight: float = 0.30
    timing_weight: float = 0.30
    swing_value_weight: float = 0.40
    
    thresholds: dict[str, float] = field(default_factory=dict)
    configuration: dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    total_opportunities_analyzed: int = 0
    opportunities_ranked: int = 0
    schema_version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        object.__setattr__(self, "ranked_opportunities", tuple(self.ranked_opportunities))
        
        # Validate weights sum to 1.0
        total_weight = self.intrinsic_weight + self.timing_weight + self.swing_value_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
    
    def to_dict(self) -> dict[str, Any]:
        """Deterministic dictionary representation."""
        payload = asdict(self)
        payload["observation_time"] = self._serialize_datetime(self.observation_time)
        payload["created_at"] = self._serialize_datetime(self.created_at)
        payload["ranked_opportunities"] = [
            self._ranked_opportunity_to_dict(opp) for opp in self.ranked_opportunities
        ]
        return payload
    
    def to_json(self) -> str:
        """Deterministic JSON serialization."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, default=str)
    
    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RankingRun":
        """Reconstruct from dict."""
        payload_copy = dict(payload)
        payload_copy["observation_time"] = cls._parse_datetime(payload_copy["observation_time"])
        payload_copy["created_at"] = cls._parse_datetime(payload_copy["created_at"])
        
        if "ranked_opportunities" in payload_copy:
            ranked_opps = []
            for opp_data in payload_copy["ranked_opportunities"]:
                ranked_opps.append(cls._ranked_opportunity_from_dict(opp_data))
            payload_copy["ranked_opportunities"] = tuple(ranked_opps)
        
        return cls(**payload_copy)
    
    @staticmethod
    def _serialize_datetime(dt: datetime | None) -> str | None:
        """Serialize datetime to ISO 8601."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    
    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Parse ISO 8601 to datetime."""
        if value is None or not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _ranked_opportunity_to_dict(opp: RankedOpportunity) -> dict[str, Any]:
        """Convert RankedOpportunity to dict."""
        d = asdict(opp)
        d["ranking_state"] = opp.ranking_state.value if isinstance(opp.ranking_state, RankingState) else opp.ranking_state
        d["intrinsic_components"] = [asdict(c) for c in opp.intrinsic_components]
        d["timing_components"] = [asdict(c) for c in opp.timing_components]
        d["swing_value_components"] = [asdict(c) for c in opp.swing_value_components]
        return d
    
    @staticmethod
    def _ranked_opportunity_from_dict(data: dict[str, Any]) -> RankedOpportunity:
        """Reconstruct RankedOpportunity from dict."""
        data_copy = dict(data)
        if "ranking_state" in data_copy and isinstance(data_copy["ranking_state"], str):
            data_copy["ranking_state"] = RankingState(data_copy["ranking_state"])
        
        for key in ["intrinsic_components", "timing_components", "swing_value_components"]:
            if key in data_copy:
                data_copy[key] = tuple(
                    ScoreComponentDetail(**c) for c in data_copy[key]
                )
        
        return RankedOpportunity(**data_copy)
