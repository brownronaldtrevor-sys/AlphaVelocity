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


class UniverseType(str, Enum):
    MICRO_CAP = "MICRO_CAP"
    SMALL_CAP = "SMALL_CAP"
    MID_CAP = "MID_CAP"
    LARGE_CAP = "LARGE_CAP"
    BROAD_MARKET = "BROAD_MARKET"
    SECTOR = "SECTOR"
    INDUSTRY = "INDUSTRY"
    SPECIAL_SITUATION = "SPECIAL_SITUATION"
    ACTIVIST = "ACTIVIST"
    TURNAROUND = "TURNAROUND"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    DEEP_VALUE = "DEEP_VALUE"
    MOMENTUM = "MOMENTUM"
    EVENT_DRIVEN = "EVENT_DRIVEN"
    CURRENT_HOLDINGS = "CURRENT_HOLDINGS"
    USER_WATCHLIST = "USER_WATCHLIST"
    ETF_BENCHMARK = "ETF_BENCHMARK"
    CUSTOM = "CUSTOM"


class PriorityMode(str, Enum):
    DENSITY = "DENSITY"
    BALANCED = "BALANCED"
    RESEARCH_DEBT = "RESEARCH_DEBT"
    HOLDINGS_AWARE = "HOLDINGS_AWARE"
    MANUAL = "MANUAL"


class ValidationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNTESTED = "UNTESTED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class ResearchPriorityLevel(str, Enum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    PAUSED = "PAUSED"


@dataclass(frozen=True)
class UniverseMembershipRecord:
    security_id: str
    symbol: str
    effective_from: datetime
    effective_to: datetime | None
    inclusion_reason: str
    exclusion_reason: str = ""
    source: str = ""
    available_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "security_id": self.security_id,
            "symbol": self.symbol,
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "inclusion_reason": self.inclusion_reason,
            "exclusion_reason": self.exclusion_reason,
            "source": self.source,
            "available_at": self.available_at.isoformat(),
            "validation_status": self.validation_status.value,
        }


@dataclass(frozen=True)
class ResearchUniverse:
    universe_id: str
    name: str
    description: str
    universe_type: UniverseType
    membership_rules: dict[str, Any] = field(default_factory=dict)
    benchmark_ids: tuple[str, ...] = ()
    point_in_time_membership: tuple[UniverseMembershipRecord, ...] = ()
    observation_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    available_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    enabled: bool = True
    priority_mode: PriorityMode = PriorityMode.BALANCED
    capacity_limit: int = 0
    minimum_liquidity: float = 0.0
    minimum_data_quality: float = 0.0
    minimum_candidate_count: int = 0
    maximum_candidate_count: int = 0
    tags: tuple[str, ...] = ()
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe_id": self.universe_id,
            "name": self.name,
            "description": self.description,
            "universe_type": self.universe_type.value,
            "membership_rules": self.membership_rules,
            "benchmark_ids": self.benchmark_ids,
            "point_in_time_membership": [m.to_dict() for m in self.point_in_time_membership],
            "observation_time": self.observation_time.isoformat(),
            "available_at": self.available_at.isoformat(),
            "source": self.source,
            "validation_status": self.validation_status.value,
            "enabled": self.enabled,
            "priority_mode": self.priority_mode.value,
            "capacity_limit": self.capacity_limit,
            "minimum_liquidity": self.minimum_liquidity,
            "minimum_data_quality": self.minimum_data_quality,
            "minimum_candidate_count": self.minimum_candidate_count,
            "maximum_candidate_count": self.maximum_candidate_count,
            "tags": self.tags,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class UniverseDiagnostics:
    universe_id: str
    universe_name: str
    universe_type: UniverseType
    securities_considered: int = 0
    securities_usable: int = 0
    candidates_discovered: int = 0
    candidates_qualified: int = 0
    duplicate_candidates_merged: int = 0
    excluded_count: int = 0
    data_unavailable_count: int = 0
    actionable_count: int = 0
    starter_count: int = 0
    near_trigger_count: int = 0
    research_only_count: int = 0
    average_research_confidence: float = 0.0
    average_capital_conviction: float = 0.0
    early_inflection_count: int = 0
    primary_move_count: int = 0
    warning_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["universe_type"] = self.universe_type.value
        return data


@dataclass(frozen=True)
class ResearchPriorityRecommendation:
    universe_id: str
    priority: ResearchPriorityLevel
    reasons: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    required_confirmation: tuple[str, ...] = ()
    confidence: float = 0.0
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe_id": self.universe_id,
            "priority": self.priority.value,
            "reasons": self.reasons,
            "contradictions": self.contradictions,
            "missing_information": self.missing_information,
            "required_confirmation": self.required_confirmation,
            "confidence": self.confidence,
            "validation_status": self.validation_status.value,
        }


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
    research_universes: tuple[ResearchUniverse, ...] = ()
    user_watchlist_symbols: tuple[str, ...] = ()
    current_holding_symbols: tuple[str, ...] = ()
    benchmark_symbols: tuple[str, ...] = ()

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
    marketplace_result: Any = None  # MarketplaceResult (optional, avoid circular import)
    universe_diagnostics: tuple[UniverseDiagnostics, ...] = ()
    universe_priorities: tuple[ResearchPriorityRecommendation, ...] = ()
    candidate_counts_by_universe: dict[str, int] = field(default_factory=dict)
    overlap_across_universes: int = 0
    merged_duplicate_candidates: int = 0
    unique_canonical_opportunities: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result_dict = {
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
            "universe_diagnostics": [diagnostic.to_dict() for diagnostic in self.universe_diagnostics],
            "universe_priorities": [priority.to_dict() for priority in self.universe_priorities],
            "candidate_counts_by_universe": self.candidate_counts_by_universe,
            "overlap_across_universes": self.overlap_across_universes,
            "merged_duplicate_candidates": self.merged_duplicate_candidates,
            "unique_canonical_opportunities": self.unique_canonical_opportunities,
            "generated_at": self.generated_at.isoformat(),
            "schema_version": self.schema_version,
        }
        if self.marketplace_result:
            result_dict["marketplace"] = self.marketplace_result.to_dict()
        return result_dict

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
