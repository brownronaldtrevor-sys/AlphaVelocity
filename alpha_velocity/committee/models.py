"""Data models for Daily Investment Committee Orchestrator."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class WorkflowState(str, Enum):
    """Explicit workflow states for daily investment committee."""

    CREATED = "CREATED"
    DATA_REFRESHED = "DATA_REFRESHED"
    UNIVERSE_BUILT = "UNIVERSE_BUILT"
    SCAN_COMPLETED = "SCAN_COMPLETED"
    RANKING_COMPLETED = "RANKING_COMPLETED"
    CAPITAL_PROPOSAL_CREATED = "CAPITAL_PROPOSAL_CREATED"
    RISK_REVIEW_PENDING = "RISK_REVIEW_PENDING"
    RISK_REJECTED = "RISK_REJECTED"
    GOVERNANCE_REVIEW_PENDING = "GOVERNANCE_REVIEW_PENDING"
    GOVERNANCE_REJECTED = "GOVERNANCE_REJECTED"
    HUMAN_APPROVAL_PENDING = "HUMAN_APPROVAL_PENDING"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    APPROVED_FOR_PAPER_SUBMISSION = "APPROVED_FOR_PAPER_SUBMISSION"
    PAPER_SUBMISSION_PARTIAL = "PAPER_SUBMISSION_PARTIAL"
    PAPER_SUBMISSION_COMPLETED = "PAPER_SUBMISSION_COMPLETED"
    RECONCILED = "RECONCILED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class HumanApprovalRecord:
    """Validated human approval record with explicit scope."""

    approval_id: str
    proposal_id: str
    proposal_hash: str  # SHA256 of immutable proposal
    approved_by: str  # User identifier
    approved_at: datetime
    expires_at: datetime
    approved_actions: tuple[str, ...] = ()  # Specific actions approved
    rejected_actions: tuple[str, ...] = ()  # Explicitly rejected actions
    comments: str = ""
    approval_scope: str = ""  # e.g., "PAPER_ONLY", "DRY_RUN_ONLY"
    schema_version: str = "1.0.0"

    def is_valid_for(
        self,
        proposal_id: str,
        proposal_hash: str,
        at_time: datetime | None = None,
    ) -> bool:
        """Check if approval is valid for given proposal at given time."""
        if at_time is None:
            at_time = datetime.now(timezone.utc)

        return (
            self.proposal_id == proposal_id
            and self.proposal_hash == proposal_hash
            and at_time <= self.expires_at
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "approval_id": self.approval_id,
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "approved_actions": self.approved_actions,
            "rejected_actions": self.rejected_actions,
            "comments": self.comments,
            "approval_scope": self.approval_scope,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class DailyCommitteeSession:
    """Single daily committee session with complete state and decisions."""

    session_id: str
    observation_time: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Input configuration
    dry_run: bool = True
    transmit: bool = False
    approval_expires_minutes: int = 120

    # Warehouse and data configuration
    warehouse_manifest_hash: str = ""
    dataset_manifest_hash: str = ""
    universe_config: dict[str, Any] = field(default_factory=dict)
    scan_config: dict[str, Any] = field(default_factory=dict)
    ranking_config: dict[str, Any] = field(default_factory=dict)
    capital_config: dict[str, Any] = field(default_factory=dict)
    risk_config: dict[str, Any] = field(default_factory=dict)
    governance_config: dict[str, Any] = field(default_factory=dict)
    paper_account_identifier: str = ""  # Must start with DU for paper accounts

    # Current portfolio state
    current_portfolio_snapshot_id: str = ""
    current_cash: float = 0.0
    current_equity: float = 0.0

    # Workflow state machine
    workflow_state: WorkflowState = WorkflowState.CREATED
    state_transitions: tuple[tuple[WorkflowState, datetime], ...] = ()

    # Scan results
    universe_size: int = 0
    exclusions_count: int = 0
    scan_report_id: str = ""

    # Ranking results
    ranking_run_id: str = ""
    total_opportunities_ranked: int = 0
    high_priority_triggered: int = 0
    high_priority_waiting: int = 0

    # Capital proposal
    proposal_id: str = ""
    proposal_hash: str = ""
    proposed_cash: float = 0.0
    proposed_gross_exposure: float = 0.0

    # Risk review
    risk_review_id: str = ""
    risk_approved: bool = False
    risk_rejection_reasons: tuple[str, ...] = ()

    # Governance review
    governance_review_id: str = ""
    governance_approved: bool = False
    governance_rejection_reasons: tuple[str, ...] = ()

    # Human approval
    human_approval: HumanApprovalRecord | None = None
    human_approval_received_at: datetime | None = None

    # Paper submission
    submitted_orders: tuple[str, ...] = ()  # Order IDs
    rejected_orders: tuple[str, ...] = ()
    partial_orders: tuple[str, ...] = ()
    paper_submission_report_id: str = ""

    # Reconciliation
    filled_orders: tuple[str, ...] = ()
    cancelled_orders: tuple[str, ...] = ()
    closing_positions: dict[str, float] = field(default_factory=dict)
    closing_cash: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    reconciliation_notes: str = ""

    # Failure tracking
    failure_reason: str = ""
    failures: tuple[str, ...] = ()

    # Reports
    morning_report_id: str = ""
    reconciliation_report_id: str = ""

    # Schema version
    schema_version: str = "1.0.0"

    def add_transition(self, new_state: WorkflowState) -> DailyCommitteeSession:
        """Create new session with state transition."""
        now = datetime.now(timezone.utc)
        new_transitions = self.state_transitions + ((self.workflow_state, now),)
        return DailyCommitteeSession(
            session_id=self.session_id,
            observation_time=self.observation_time,
            created_at=self.created_at,
            dry_run=self.dry_run,
            transmit=self.transmit,
            approval_expires_minutes=self.approval_expires_minutes,
            warehouse_manifest_hash=self.warehouse_manifest_hash,
            dataset_manifest_hash=self.dataset_manifest_hash,
            universe_config=self.universe_config,
            scan_config=self.scan_config,
            ranking_config=self.ranking_config,
            capital_config=self.capital_config,
            risk_config=self.risk_config,
            governance_config=self.governance_config,
            paper_account_identifier=self.paper_account_identifier,
            current_portfolio_snapshot_id=self.current_portfolio_snapshot_id,
            current_cash=self.current_cash,
            current_equity=self.current_equity,
            workflow_state=new_state,
            state_transitions=new_transitions,
            universe_size=self.universe_size,
            exclusions_count=self.exclusions_count,
            scan_report_id=self.scan_report_id,
            ranking_run_id=self.ranking_run_id,
            total_opportunities_ranked=self.total_opportunities_ranked,
            high_priority_triggered=self.high_priority_triggered,
            high_priority_waiting=self.high_priority_waiting,
            proposal_id=self.proposal_id,
            proposal_hash=self.proposal_hash,
            proposed_cash=self.proposed_cash,
            proposed_gross_exposure=self.proposed_gross_exposure,
            risk_review_id=self.risk_review_id,
            risk_approved=self.risk_approved,
            risk_rejection_reasons=self.risk_rejection_reasons,
            governance_review_id=self.governance_review_id,
            governance_approved=self.governance_approved,
            governance_rejection_reasons=self.governance_rejection_reasons,
            human_approval=self.human_approval,
            human_approval_received_at=self.human_approval_received_at,
            submitted_orders=self.submitted_orders,
            rejected_orders=self.rejected_orders,
            partial_orders=self.partial_orders,
            paper_submission_report_id=self.paper_submission_report_id,
            filled_orders=self.filled_orders,
            cancelled_orders=self.cancelled_orders,
            closing_positions=self.closing_positions,
            closing_cash=self.closing_cash,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
            reconciliation_notes=self.reconciliation_notes,
            failure_reason=self.failure_reason,
            failures=self.failures,
            morning_report_id=self.morning_report_id,
            reconciliation_report_id=self.reconciliation_report_id,
            schema_version=self.schema_version,
        )

    def mark_failed(self, reason: str) -> DailyCommitteeSession:
        """Mark session as failed."""
        session = self.add_transition(WorkflowState.FAILED)
        # Update the failure_reason in the new session
        return DailyCommitteeSession(
            session_id=session.session_id,
            observation_time=session.observation_time,
            created_at=session.created_at,
            dry_run=session.dry_run,
            transmit=session.transmit,
            approval_expires_minutes=session.approval_expires_minutes,
            warehouse_manifest_hash=session.warehouse_manifest_hash,
            dataset_manifest_hash=session.dataset_manifest_hash,
            universe_config=session.universe_config,
            scan_config=session.scan_config,
            ranking_config=session.ranking_config,
            capital_config=session.capital_config,
            risk_config=session.risk_config,
            governance_config=session.governance_config,
            paper_account_identifier=session.paper_account_identifier,
            current_portfolio_snapshot_id=session.current_portfolio_snapshot_id,
            current_cash=session.current_cash,
            current_equity=session.current_equity,
            workflow_state=session.workflow_state,
            state_transitions=session.state_transitions,
            universe_size=session.universe_size,
            exclusions_count=session.exclusions_count,
            scan_report_id=session.scan_report_id,
            ranking_run_id=session.ranking_run_id,
            total_opportunities_ranked=session.total_opportunities_ranked,
            high_priority_triggered=session.high_priority_triggered,
            high_priority_waiting=session.high_priority_waiting,
            proposal_id=session.proposal_id,
            proposal_hash=session.proposal_hash,
            proposed_cash=session.proposed_cash,
            proposed_gross_exposure=session.proposed_gross_exposure,
            risk_review_id=session.risk_review_id,
            risk_approved=session.risk_approved,
            risk_rejection_reasons=session.risk_rejection_reasons,
            governance_review_id=session.governance_review_id,
            governance_approved=session.governance_approved,
            governance_rejection_reasons=session.governance_rejection_reasons,
            human_approval=session.human_approval,
            human_approval_received_at=session.human_approval_received_at,
            submitted_orders=session.submitted_orders,
            rejected_orders=session.rejected_orders,
            partial_orders=session.partial_orders,
            paper_submission_report_id=session.paper_submission_report_id,
            filled_orders=session.filled_orders,
            cancelled_orders=session.cancelled_orders,
            closing_positions=session.closing_positions,
            closing_cash=session.closing_cash,
            realized_pnl=session.realized_pnl,
            unrealized_pnl=session.unrealized_pnl,
            reconciliation_notes=session.reconciliation_notes,
            failure_reason=reason,
            failures=session.failures,
            morning_report_id=session.morning_report_id,
            reconciliation_report_id=session.reconciliation_report_id,
            schema_version=session.schema_version,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "observation_time": self.observation_time.isoformat(),
            "created_at": self.created_at.isoformat(),
            "dry_run": self.dry_run,
            "transmit": self.transmit,
            "approval_expires_minutes": self.approval_expires_minutes,
            "warehouse_manifest_hash": self.warehouse_manifest_hash,
            "dataset_manifest_hash": self.dataset_manifest_hash,
            "universe_config": self.universe_config,
            "scan_config": self.scan_config,
            "ranking_config": self.ranking_config,
            "capital_config": self.capital_config,
            "risk_config": self.risk_config,
            "governance_config": self.governance_config,
            "paper_account_identifier": self.paper_account_identifier,
            "current_portfolio_snapshot_id": self.current_portfolio_snapshot_id,
            "current_cash": self.current_cash,
            "current_equity": self.current_equity,
            "workflow_state": self.workflow_state.value,
            "state_transitions": [(s.value, t.isoformat()) for s, t in self.state_transitions],
            "universe_size": self.universe_size,
            "exclusions_count": self.exclusions_count,
            "scan_report_id": self.scan_report_id,
            "ranking_run_id": self.ranking_run_id,
            "total_opportunities_ranked": self.total_opportunities_ranked,
            "high_priority_triggered": self.high_priority_triggered,
            "high_priority_waiting": self.high_priority_waiting,
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "proposed_cash": self.proposed_cash,
            "proposed_gross_exposure": self.proposed_gross_exposure,
            "risk_review_id": self.risk_review_id,
            "risk_approved": self.risk_approved,
            "risk_rejection_reasons": self.risk_rejection_reasons,
            "governance_review_id": self.governance_review_id,
            "governance_approved": self.governance_approved,
            "governance_rejection_reasons": self.governance_rejection_reasons,
            "human_approval": self.human_approval.to_dict() if self.human_approval else None,
            "human_approval_received_at": self.human_approval_received_at.isoformat() if self.human_approval_received_at else None,
            "submitted_orders": self.submitted_orders,
            "rejected_orders": self.rejected_orders,
            "partial_orders": self.partial_orders,
            "paper_submission_report_id": self.paper_submission_report_id,
            "filled_orders": self.filled_orders,
            "cancelled_orders": self.cancelled_orders,
            "closing_positions": self.closing_positions,
            "closing_cash": self.closing_cash,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "reconciliation_notes": self.reconciliation_notes,
            "failure_reason": self.failure_reason,
            "failures": self.failures,
            "morning_report_id": self.morning_report_id,
            "reconciliation_report_id": self.reconciliation_report_id,
            "schema_version": self.schema_version,
        }


def generate_proposal_hash(proposal_dict: dict[str, Any]) -> str:
    """Generate SHA256 hash of proposal for immutability tracking."""
    import json

    # Create canonical JSON representation
    canonical = json.dumps(proposal_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
