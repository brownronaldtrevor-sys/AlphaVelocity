"""Data models for Market Intelligence Engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Mapping

from enum import Enum


class QualificationState(str, Enum):
    """Research classification for securities in the universe."""

    QUALIFIED = "QUALIFIED"
    WATCHLIST = "WATCHLIST"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    DATA_QUALITY_FAILURE = "DATA_QUALITY_FAILURE"
    ILLIQUID = "ILLIQUID"
    UNSUPPORTED_ASSET = "UNSUPPORTED_ASSET"
    WAITING_FOR_TRIGGER = "WAITING_FOR_TRIGGER"
    EXCLUDED = "EXCLUDED"


@dataclass(frozen=True)
class UniverseConfig:
    """Configuration for point-in-time universe construction."""

    observation_time: datetime
    min_price: float = 1.0
    max_price: float = 100_000.0
    min_avg_daily_volume: float = 100_000.0
    min_avg_daily_dollar_volume: float = 500_000.0
    min_trading_history_days: int = 60
    max_spread_bps: float = 500.0
    supported_exchanges: tuple[str, ...] = ("NYSE", "NASDAQ")
    supported_asset_types: tuple[str, ...] = ("STOCK",)
    exclude_delisted: bool = False

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")


@dataclass(frozen=True)
class ScanConfig:
    """Configuration for market intelligence scan."""

    universe_config: UniverseConfig
    min_bars_for_weekly: int = 50
    min_completed_weeks: int = 10
    include_watchlist: bool = False
    include_insufficient_history: bool = False

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.min_bars_for_weekly < 1:
            raise ValueError("min_bars_for_weekly must be >= 1")


@dataclass(frozen=True)
class ExclusionReason:
    """Record of why a security was excluded."""

    category: str  # "DATA_QUALITY", "LIQUIDITY", "ASSET_TYPE", "EXCHANGE", "HISTORY"
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "reason": self.reason,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class SecurityQualification:
    """Qualification result for a single security."""

    security_id: str
    symbol: str
    state: QualificationState
    qualified: bool
    reasons: tuple[str, ...] = ()
    exclusions: tuple[ExclusionReason, ...] = ()
    daily_bar_count: int = 0
    completed_week_count: int = 0
    avg_daily_volume: float = 0.0
    avg_daily_dollar_volume: float = 0.0
    spread_estimate_bps: float = 0.0
    data_quality_issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "security_id": self.security_id,
            "symbol": self.symbol,
            "state": self.state.value,
            "qualified": self.qualified,
            "reasons": self.reasons,
            "exclusions": [ex.to_dict() for ex in self.exclusions],
            "daily_bar_count": self.daily_bar_count,
            "completed_week_count": self.completed_week_count,
            "avg_daily_volume": self.avg_daily_volume,
            "avg_daily_dollar_volume": self.avg_daily_dollar_volume,
            "spread_estimate_bps": self.spread_estimate_bps,
            "data_quality_issues": self.data_quality_issues,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class MarketScanResult:
    """Complete market intelligence scan result."""

    scan_run_id: str
    observation_time: datetime
    universe_snapshot_id: str
    total_securities_considered: int
    qualified_count: int
    watchlist_count: int
    excluded_count: int
    exclusion_counts_by_reason: dict[str, int] = field(default_factory=dict)
    assembled_opportunities: tuple[Any, ...] = ()  # Opportunity objects
    ranked_research_results: tuple[Any, ...] = ()  # RankingResult objects
    security_qualifications: tuple[SecurityQualification, ...] = ()
    warnings: tuple[str, ...] = ()
    warehouse_manifest_hash: str = ""
    dataset_manifest_hash: str = ""
    configuration_hash: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "scan_run_id": self.scan_run_id,
            "observation_time": self.observation_time.isoformat(),
            "universe_snapshot_id": self.universe_snapshot_id,
            "total_securities_considered": self.total_securities_considered,
            "qualified_count": self.qualified_count,
            "watchlist_count": self.watchlist_count,
            "excluded_count": self.excluded_count,
            "exclusion_counts_by_reason": self.exclusion_counts_by_reason,
            "assembled_opportunities_count": len(self.assembled_opportunities),
            "ranked_results_count": len(self.ranked_research_results),
            "warnings": self.warnings,
            "warehouse_manifest_hash": self.warehouse_manifest_hash,
            "dataset_manifest_hash": self.dataset_manifest_hash,
            "configuration_hash": self.configuration_hash,
            "generated_at": self.generated_at.isoformat(),
            "schema_version": self.schema_version,
        }

    def to_json(self) -> str:
        """Deterministic JSON serialization."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MarketScanResult:
        """Create from dictionary."""
        return cls(
            scan_run_id=str(data["scan_run_id"]),
            observation_time=datetime.fromisoformat(str(data["observation_time"])),
            universe_snapshot_id=str(data["universe_snapshot_id"]),
            total_securities_considered=int(data["total_securities_considered"]),
            qualified_count=int(data["qualified_count"]),
            watchlist_count=int(data["watchlist_count"]),
            excluded_count=int(data["excluded_count"]),
            exclusion_counts_by_reason=dict(data.get("exclusion_counts_by_reason") or {}),
            warnings=tuple(data.get("warnings") or []),
            warehouse_manifest_hash=str(data.get("warehouse_manifest_hash") or ""),
            dataset_manifest_hash=str(data.get("dataset_manifest_hash") or ""),
            configuration_hash=str(data.get("configuration_hash") or ""),
            generated_at=datetime.fromisoformat(str(data.get("generated_at") or datetime.now(timezone.utc).isoformat())),
            schema_version=str(data.get("schema_version") or "1.0.0"),
        )
