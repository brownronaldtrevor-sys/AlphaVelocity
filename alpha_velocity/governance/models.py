from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GovernanceDecision(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class GovernanceContext:
    broker_mode: str
    managed_accounts: tuple[str, ...]
    dry_run: bool
    strategy_id: str
    instrument_type: str
    side: str
    order_notional_pct: float
    projected_gross_exposure_pct: float
    projected_single_position_pct: float
    daily_loss_pct: float
    open_order_count: int
    has_stop: bool
    model_validated: bool
    data_lineage_valid: bool
    restricted_information_flag: bool = False
    manipulative_intent_flag: bool = False
    emergency_halt: bool = False


@dataclass(frozen=True)
class GovernanceResult:
    decision: GovernanceDecision
    reasons: tuple[str, ...]
