"""Data models for Capital Intelligence Optimizer."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class ProposalState(str, Enum):
    """Research states for capital allocation proposals."""

    PROPOSAL_READY_FOR_RISK_REVIEW = "PROPOSAL_READY_FOR_RISK_REVIEW"
    HOLD_CURRENT_PORTFOLIO = "HOLD_CURRENT_PORTFOLIO"
    RAISE_CASH = "RAISE_CASH"
    PARTIAL_ROTATION = "PARTIAL_ROTATION"
    FULL_ROTATION_PROHIBITED = "FULL_ROTATION_PROHIBITED"
    INSUFFICIENT_CALIBRATION = "INSUFFICIENT_CALIBRATION"
    CONSTRAINT_BOUND = "CONSTRAINT_BOUND"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class CurrentHolding:
    """Current portfolio position."""

    security_id: str
    symbol: str
    quantity: float
    current_price: float
    average_cost: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    sector: str = ""
    industry: str = ""
    correlation_bucket: str = ""

    @property
    def current_value(self) -> float:
        """Current market value."""
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        """Total cost basis."""
        return self.quantity * self.average_cost

    @property
    def weight_pct(self) -> float:
        """Current weight as percentage of notional (not accounting for cash)."""
        return self.current_value  # Will be normalized by portfolio equity


@dataclass(frozen=True)
class ProposedPosition:
    """Proposed portfolio position."""

    opportunity_id: str
    security_id: str
    symbol: str
    ranking_state: str
    overall_research_score: float
    intrinsic_score: float
    timing_score: float
    swing_value_score: float
    calibration_status: str
    proposed_quantity: float
    proposed_price_target: float
    current_holding_id: str | None = None  # If replacing existing position
    replacement_reason: str = ""
    sector: str = ""
    industry: str = ""
    correlation_bucket: str = ""

    @property
    def proposed_value(self) -> float:
        """Proposed notional value."""
        return self.proposed_quantity * self.proposed_price_target


@dataclass(frozen=True)
class RotationAnalysis:
    """Analysis of proposed position rotation."""

    existing_holding_symbol: str
    proposed_opportunity_symbol: str
    existing_ranking_score: float
    proposed_ranking_score: float
    score_improvement: float
    estimated_sale_proceeds: float
    estimated_transaction_costs: float
    net_proceeds_after_costs: float
    switching_benefit_pct: float
    sector_overlap_pct: float
    industry_overlap_pct: float
    correlation_overlap: float
    justified: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConcentrationMetrics:
    """Portfolio concentration analysis."""

    largest_position_pct: float
    top_5_positions_pct: float
    top_10_positions_pct: float
    sector_concentration: dict[str, float] = field(default_factory=dict)
    industry_concentration: dict[str, float] = field(default_factory=dict)
    correlation_bucket_concentration: dict[str, float] = field(default_factory=dict)
    herfindahl_index: float = 0.0
    effective_positions: float = 0.0


@dataclass(frozen=True)
class LiquidityWarning:
    """Liquidity and capacity warning."""

    symbol: str
    issue: str
    available_capacity_pct: float = 0.0
    participation_pct: float = 0.0
    recommendation: str = ""


@dataclass(frozen=True)
class CapitalAllocationProposal:
    """Complete capital allocation proposal."""

    proposal_id: str
    observation_time: datetime
    portfolio_snapshot_id: str
    ranking_run_id: str
    proposal_state: ProposalState

    # Starting conditions
    starting_cash: float
    starting_equity: float
    starting_gross_exposure: float
    starting_net_exposure: float
    current_holdings: tuple[CurrentHolding, ...] = ()

    # Proposed allocation
    proposed_holdings: tuple[ProposedPosition, ...] = ()
    proposed_cash: float = 0.0
    proposed_gross_exposure: float = 0.0
    proposed_net_exposure: float = 0.0
    proposed_cash_weight_pct: float = 0.0

    # Position-level details
    position_level_weights: dict[str, float] = field(default_factory=dict)
    target_dollar_amounts: dict[str, float] = field(default_factory=dict)
    proposed_increases: dict[str, float] = field(default_factory=dict)  # by symbol
    proposed_reductions: dict[str, float] = field(default_factory=dict)  # by symbol
    proposed_exits: tuple[str, ...] = ()  # symbols to exit
    proposed_new_positions: tuple[str, ...] = ()  # symbols to add

    # Return expectations
    expected_portfolio_contribution_pct: float = 0.0
    expected_upside_contribution_pct: float = 0.0
    expected_downside_contribution_pct: float = 0.0
    uncertainty_contribution_pct: float = 0.0

    # Costs and thresholds
    turnover_estimate_pct: float = 0.0
    estimated_transaction_costs: float = 0.0
    switching_cost_estimate: float = 0.0

    # Metrics
    concentration_metrics: ConcentrationMetrics | None = None
    rotation_analyses: tuple[RotationAnalysis, ...] = ()
    liquidity_warnings: tuple[LiquidityWarning, ...] = ()

    # Rejected opportunities
    rejected_opportunities: dict[str, str] = field(default_factory=dict)  # opp_id -> reason
    constraint_violations: tuple[str, ...] = ()

    # Risk and governance
    risk_review_required: bool = True
    governance_review_required: bool = True
    execution_authorized: bool = False

    # Evidence
    warnings: tuple[str, ...] = ()
    sizing_method_used: str = ""
    constraint_binding: tuple[str, ...] = ()
    evidence_lineage: dict[str, Any] = field(default_factory=dict)
    configuration_manifest: dict[str, Any] = field(default_factory=dict)

    # Metadata
    schema_version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate proposal."""
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["proposal_state"] = self.proposal_state.value
        data["observation_time"] = self.observation_time.isoformat()
        data["created_at"] = self.created_at.isoformat()
        return data

    def to_json(self) -> str:
        """Serialize to deterministic JSON."""
        data = self.to_dict()
        return json.dumps(data, sort_keys=True, default=str)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CapitalAllocationProposal:
        """Create from dictionary."""
        data_copy = dict(data)
        if isinstance(data_copy.get("proposal_state"), str):
            data_copy["proposal_state"] = ProposalState(data_copy["proposal_state"])
        # Parse ISO format datetime strings
        if isinstance(data_copy.get("observation_time"), str):
            data_copy["observation_time"] = datetime.fromisoformat(data_copy["observation_time"])
        if isinstance(data_copy.get("created_at"), str):
            data_copy["created_at"] = datetime.fromisoformat(data_copy["created_at"])
        return cls(**data_copy)


@dataclass(frozen=True)
class SizingConfig:
    """Configuration for position sizing method."""

    method: str  # "proportional_ev", "risk_budget", "volatility_aware", "equal_risk", "rank_based", "cash_preserving"
    max_single_position_pct: float = 10.0
    max_sector_exposure_pct: float = 30.0
    max_industry_exposure_pct: float = 15.0
    max_correlation_bucket_pct: float = 20.0
    max_gross_exposure_pct: float = 150.0
    max_net_exposure_pct: float = 100.0
    min_cash_reserve_pct: float = 5.0
    max_participation_pct: float = 5.0  # Max % of avg daily volume
    uncalibrated_position_cap_pct: float = 2.0
    rotation_threshold_basis_points: int = 50  # 50 bps improvement required
    transaction_cost_pct: float = 0.05  # 5 bps for round-trip
    spread_estimate_pct: float = 0.05  # 5 bps
    slippage_estimate_pct: float = 0.10  # 10 bps
    holding_period_days: int = 60

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not 0 < self.max_single_position_pct <= 100:
            raise ValueError("max_single_position_pct must be between 0 and 100")
        if not 0 < self.max_gross_exposure_pct <= 500:
            raise ValueError("max_gross_exposure_pct must be between 0 and 500")
