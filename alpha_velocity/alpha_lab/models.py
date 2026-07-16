"""Alpha Lab shared strategy API models."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class CandidateState(str, Enum):
    """Transparent candidate state enumeration."""
    TRIGGERED = "TRIGGERED"
    WAITING_FOR_TRIGGER = "WAITING_FOR_TRIGGER"
    WATCHLIST = "WATCHLIST"
    INVALIDATED = "INVALIDATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    EXCLUDED = "EXCLUDED"
    SHADOW_ONLY = "SHADOW_ONLY"


class StrategyValidationStatus(str, Enum):
    """Strategy validation status."""
    UNCALIBRATED = "UNCALIBRATED"
    CALIBRATING = "CALIBRATING"
    CALIBRATED = "CALIBRATED"
    SHADOW = "SHADOW"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class StrategyContext:
    """Context passed to strategy during execution."""
    observation_time: datetime
    warehouse: Any  # SQLiteHistoricalWarehouse
    universe_snapshot_id: str
    universe_size: int
    dataset_manifest_hash: str
    warehouse_manifest_hash: str


@dataclass(frozen=True)
class StrategyEvidence:
    """Evidence components produced by a strategy."""
    intrinsic_opportunity_score: float = 0.0
    timing_opportunity_score: float = 0.0
    catalyst_score: float = 0.0
    capital_structure_score: float = 0.0
    expectation_gap_score: float = 0.0
    liquidity_score: float = 0.0
    risk_adjustment: float = 100.0
    uncertainty_adjustment: float = 100.0
    positive_contributors: tuple[str, ...] = ()
    negative_contributors: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    required_confirmation: tuple[str, ...] = ()
    invalidation_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyCandidate:
    """A candidate produced by a strategy."""
    candidate_id: str
    strategy_id: str
    symbol: str
    security_id: str
    observation_time: datetime
    data_available_through: datetime
    candidate_state: CandidateState
    evidence: StrategyEvidence
    explanation: str
    expected_upside_pct: float | None = None
    expected_downside_pct: float | None = None
    expected_holding_days: float | None = None
    probability_estimate: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        if self.data_available_through > self.observation_time:
            raise ValueError("data_available_through cannot exceed observation_time")


@dataclass(frozen=True)
class StrategyState:
    """Strategy execution state."""
    strategy_id: str
    strategy_name: str
    strategy_version: str
    observation_time: datetime
    validation_status: StrategyValidationStatus
    candidates_generated: int
    triggered_count: int
    waiting_count: int
    excluded_count: int
    error_count: int
    error_messages: tuple[str, ...] = ()
    execution_time_ms: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class StrategyRunResult:
    """Complete result from a strategy run."""
    run_id: str
    strategy_id: str
    strategy_name: str
    strategy_version: str
    observation_time: datetime
    candidates: tuple[StrategyCandidate, ...] = ()
    state: StrategyState | None = None
    warnings: tuple[str, ...] = ()
    execution_time_ms: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["observation_time"] = self.observation_time.isoformat()
        data["created_at"] = self.created_at.isoformat()
        if self.state:
            data["state"] = {
                "strategy_id": self.state.strategy_id,
                "strategy_name": self.state.strategy_name,
                "strategy_version": self.state.strategy_version,
                "observation_time": self.state.observation_time.isoformat(),
                "validation_status": self.state.validation_status.value,
                "candidates_generated": self.state.candidates_generated,
                "triggered_count": self.state.triggered_count,
                "waiting_count": self.state.waiting_count,
                "excluded_count": self.state.excluded_count,
                "error_count": self.state.error_count,
                "execution_time_ms": self.state.execution_time_ms,
                "created_at": self.state.created_at.isoformat(),
            }
        if self.candidates:
            data["candidates"] = [
                {
                    "candidate_id": c.candidate_id,
                    "strategy_id": c.strategy_id,
                    "symbol": c.symbol,
                    "security_id": c.security_id,
                    "observation_time": c.observation_time.isoformat(),
                    "data_available_through": c.data_available_through.isoformat(),
                    "candidate_state": c.candidate_state.value,
                    "explanation": c.explanation,
                    "expected_upside_pct": c.expected_upside_pct,
                    "expected_downside_pct": c.expected_downside_pct,
                    "expected_holding_days": c.expected_holding_days,
                    "probability_estimate": c.probability_estimate,
                    "created_at": c.created_at.isoformat(),
                }
                for c in self.candidates
            ]
        data["created_at"] = self.created_at.isoformat()
        return data


@dataclass(frozen=True)
class StrategyScorecard:
    """Performance scorecard for a strategy."""
    strategy_id: str
    strategy_name: str
    observation_time: datetime
    sample_count: int = 0
    triggered_count: int = 0
    waiting_count: int = 0
    excluded_count: int = 0
    hit_rate: float = 0.0
    average_gain_pct: float = 0.0
    average_loss_pct: float = 0.0
    payoff_ratio: float = 0.0
    expectancy: float = 0.0
    maximum_drawdown_pct: float = 0.0
    average_holding_days: float = 0.0
    turnover: float = 0.0
    validation_status: StrategyValidationStatus = StrategyValidationStatus.UNCALIBRATED
    recommendation: str = "REMAIN_SHADOW"
    warnings: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"
