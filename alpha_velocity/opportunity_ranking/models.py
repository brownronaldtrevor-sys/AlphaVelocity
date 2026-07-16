"""Data models for opportunity ranking results and components."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Mapping
from enum import Enum


class RankingState(str, Enum):
    """Research classification states for ranked opportunities."""

    HIGH_PRIORITY_TRIGGERED = "HIGH_PRIORITY_TRIGGERED"
    HIGH_PRIORITY_WAITING_FOR_TRIGGER = "HIGH_PRIORITY_WAITING_FOR_TRIGGER"
    SPECULATIVE = "SPECULATIVE"
    REFINANCING_DEPENDENT = "REFINANCING_DEPENDENT"
    DISTRESSED_OPTIONALITY = "DISTRESSED_OPTIONALITY"
    WATCHLIST = "WATCHLIST"
    AVOID = "AVOID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class RankingResult:
    """Single ranked opportunity research result."""

    opportunity_id: str
    rank: int  # 1-based ranking by swing value
    percentile: float  # 0.0 to 100.0
    overall_research_score: float  # 0-100 aggregate score
    ranking_state: RankingState  # Classification state
    
    # Component scores (0-100)
    intrinsic_opportunity_score: float
    timing_opportunity_score: float
    expected_swing_value_score: float
    
    # Sub-component scores
    technical_score: float
    catalyst_score: float
    capital_structure_score: float
    liquidity_score: float
    
    # Adjustments (0-100, with penalties reducing from 100)
    risk_adjustment: float
    uncertainty_adjustment: float
    
    # Validation status
    validation_status: str  # "CALIBRATED", "UNCALIBRATED", "INSUFFICIENT_DATA"
    
    # Evidence breakdown
    positive_contributors: tuple[str, ...] = ()
    negative_contributors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    required_confirmation: tuple[str, ...] = ()
    
    # Evidence lineage
    evidence_lineage: dict[str, Any] = field(default_factory=dict)

    # Shadow ranking integration (default non-influential)
    shadow_signals: dict[str, float] = field(default_factory=dict)
    shadow_score: float = 0.0
    shadow_influence_enabled: bool = False
    
    # Schema version
    schema_version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate ranges."""
        if not (0 <= self.intrinsic_opportunity_score <= 100):
            raise ValueError(f"intrinsic_opportunity_score must be 0-100, got {self.intrinsic_opportunity_score}")
        if not (0 <= self.timing_opportunity_score <= 100):
            raise ValueError(f"timing_opportunity_score must be 0-100, got {self.timing_opportunity_score}")
        if not (0 <= self.expected_swing_value_score <= 100):
            raise ValueError(f"expected_swing_value_score must be 0-100, got {self.expected_swing_value_score}")
        if not (0 <= self.overall_research_score <= 100):
            raise ValueError(f"overall_research_score must be 0-100, got {self.overall_research_score}")
        if not (0 <= self.percentile <= 100):
            raise ValueError(f"percentile must be 0-100, got {self.percentile}")
        if not (0 <= self.shadow_score <= 100):
            raise ValueError(f"shadow_score must be 0-100, got {self.shadow_score}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["ranking_state"] = self.ranking_state.value
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RankingResult:
        """Create from dictionary."""
        data_copy = dict(data)
        if isinstance(data_copy.get("ranking_state"), str):
            data_copy["ranking_state"] = RankingState(data_copy["ranking_state"])
        return cls(**data_copy)


@dataclass(frozen=True)
class RankingBatch:
    """Complete ranking batch result."""

    universe_snapshot_id: str
    observation_time: datetime
    ranked_opportunities: tuple[RankingResult, ...] = ()
    total_opportunities: int = 0
    confidence_level: str = "RESEARCH"  # "RESEARCH", "PROVISIONAL", "CONFIRMED"
    notes: str = ""
    schema_version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "universe_snapshot_id": self.universe_snapshot_id,
            "observation_time": self.observation_time.isoformat(),
            "ranked_opportunities": [r.to_dict() for r in self.ranked_opportunities],
            "total_opportunities": self.total_opportunities,
            "confidence_level": self.confidence_level,
            "notes": self.notes,
            "schema_version": self.schema_version,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RankingBatch:
        """Create from dictionary."""
        ranked_opps = tuple(
            RankingResult.from_dict(r) for r in data.get("ranked_opportunities", [])
        )
        return cls(
            universe_snapshot_id=data["universe_snapshot_id"],
            observation_time=datetime.fromisoformat(data["observation_time"]),
            ranked_opportunities=ranked_opps,
            total_opportunities=data.get("total_opportunities", 0),
            confidence_level=data.get("confidence_level", "RESEARCH"),
            notes=data.get("notes", ""),
            schema_version=data.get("schema_version", "1.0.0"),
        )
