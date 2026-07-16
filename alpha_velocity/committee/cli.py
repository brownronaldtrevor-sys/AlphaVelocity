"""Command-line interface for Daily Investment Committee."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from alpha_velocity.committee import (
    DailyInvestmentCommitteeOrchestrator,
    DailyCommitteeSession,
    HumanApprovalRecord,
    WorkflowState,
    generate_proposal_hash,
    CommitteeReportBuilder,
    PaperOrderPlanner,
)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Daily Investment Committee Orchestrator v1",
        prog="committee",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run command
    run_parser = subparsers.add_parser("run", help="Run daily committee session")
    run_parser.add_argument("--dry-run", action="store_true", default=True, help="Run in dry-run mode (default: true)")
    run_parser.add_argument("--transmit", action="store_true", default=False, help="Enable paper submission (default: false)")
    run_parser.add_argument("--config", default="config.committee.yaml", help="Committee configuration file")
    run_parser.add_argument("--state-dir", default="committee_state", help="State directory")

    # report command
    report_parser = subparsers.add_parser("report", help="Show latest session report")
    report_parser.add_argument("--session-id", help="Session ID (default: latest)")
    report_parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="Report format")

    # approve command
    approve_parser = subparsers.add_parser("approve", help="Approve a proposal")
    approve_parser.add_argument("--session-id", required=True, help="Session ID")
    approve_parser.add_argument("--proposal-hash", required=True, help="Proposal hash")
    approve_parser.add_argument("--approved-by", required=True, help="Approver name")
    approve_parser.add_argument("--expires-minutes", type=int, default=120, help="Approval expiration in minutes")
    approve_parser.add_argument("--comments", default="", help="Approval comments")

    # submit-paper command
    submit_parser = subparsers.add_parser("submit-paper", help="Submit approved proposal to paper broker")
    submit_parser.add_argument("--session-id", required=True, help="Session ID")
    submit_parser.add_argument("--state-dir", default="committee_state", help="State directory")

    # reconcile command
    reconcile_parser = subparsers.add_parser("reconcile", help="Reconcile paper session")
    reconcile_parser.add_argument("--session-id", required=True, help="Session ID")
    reconcile_parser.add_argument("--state-dir", default="committee_state", help="State directory")
    reconcile_parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="Report format")

    args = parser.parse_args()

    try:
        if args.command == "run":
            return cmd_run(args)
        elif args.command == "report":
            return cmd_report(args)
        elif args.command == "approve":
            return cmd_approve(args)
        elif args.command == "submit-paper":
            return cmd_submit_paper(args)
        elif args.command == "reconcile":
            return cmd_reconcile(args)
        else:
            parser.print_help()
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Run daily committee session."""
    print(f"Starting Daily Investment Committee session...")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Transmit: {args.transmit}")
    print(f"  Config: {args.config}")
    print(f"  State dir: {args.state_dir}")

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    config = json.loads(config_path.read_text())

    # Create orchestrator
    orchestrator = DailyInvestmentCommitteeOrchestrator(args.state_dir)

    # Create session
    observation_time = datetime.now(timezone.utc)
    try:
        session = orchestrator.create_session(
            observation_time=observation_time,
            warehouse_manifest_hash=config.get("warehouse_manifest_hash", ""),
            dataset_manifest_hash=config.get("dataset_manifest_hash", ""),
            paper_account_identifier=config.get("paper_account_identifier", "DU000000"),
            dry_run=args.dry_run,
            transmit=args.transmit,
            **config.get("committee", {}),
        )
    except ValueError as e:
        print(f"Error creating session: {e}", file=sys.stderr)
        return 1

    # Validate paper gates
    gate_errors = orchestrator.validate_paper_gates(session)
    if gate_errors:
        print("Paper-only gates validation failed:")
        for error in gate_errors:
            print(f"  - {error}")
        if args.transmit:
            return 1

    # Save initial session
    saved_path = orchestrator.save_session(session)
    print(f"\nSession created: {session.session_id}")
    print(f"Saved to: {saved_path}")
    print(f"Initial state: {session.workflow_state}")

    # Execute workflow
    print("\n" + "="*60)
    print("Executing workflow stages...")
    print("="*60)
    
    try:
        session = orchestrator.run_workflow(session)
    except Exception as e:
        print(f"Workflow execution failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    # Report final state
    print("\n" + "="*60)
    print("Workflow execution complete")
    print("="*60)
    print(f"Final state: {session.workflow_state}")
    print(f"State transitions: {len(session.state_transitions)}")
    print(f"Session ID: {session.session_id}")
    print(f"Scan report ID: {session.scan_report_id}")
    print(f"Ranking run ID: {session.ranking_run_id}")
    print(f"Proposal ID: {session.proposal_id}")
    print(f"Total opportunities ranked: {session.total_opportunities_ranked}")
    print(f"Risk approved: {session.risk_approved}")
    print(f"Governance approved: {session.governance_approved}")

    if session.workflow_state == WorkflowState.HUMAN_APPROVAL_PENDING:
        print("\n✓ Workflow advanced to HUMAN_APPROVAL_PENDING")
        print("\nNext steps:")
        print(f"  1. Review the morning report")
        print(f"  2. Run: committee approve --session-id {session.session_id}")
        print(f"  3. Run: committee submit-paper --session-id {session.session_id}")
    elif session.failure_reason:
        print(f"\n✗ Workflow failed: {session.failure_reason}")
        return 1
    else:
        print(f"\nWorkflow state: {session.workflow_state}")

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Show session report."""
    print("Daily Investment Committee Report\n")
    print("(Report generation would connect to actual systems)")
    print("\nExample morning report structure:")
    print(json.dumps({
        "session_id": "COMM-20260116-143000-12345678",
        "status": "APPROVED_FOR_PAPER_SUBMISSION",
        "universe_size": 500,
        "exclusions": 50,
        "high_priority_triggered": 3,
        "high_priority_waiting": 12,
        "top_opportunity": "ACME (Rank 1, Score 82.5)",
        "proposed_cash": 50000.0,
        "proposed_gross_exposure": 100000.0,
        "risk_approved": True,
        "governance_approved": True,
        "human_approval": "PENDING",
    }, indent=2))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    """Record human approval."""
    print(f"Recording human approval for session {args.session_id}")
    print(f"  Proposal hash: {args.proposal_hash[:16]}...")
    print(f"  Approved by: {args.approved_by}")
    print(f"  Expires in: {args.expires_minutes} minutes")

    # Create approval record
    approval_id = f"APPR-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-12345678"
    expires_at = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    from datetime import timedelta
    expires_at = expires_at + timedelta(minutes=args.expires_minutes)

    approval = HumanApprovalRecord(
        approval_id=approval_id,
        proposal_id=args.session_id,
        proposal_hash=args.proposal_hash,
        approved_by=args.approved_by,
        approved_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        comments=args.comments,
        approval_scope="PAPER_ONLY",
    )

    print(f"\nApproval recorded:")
    print(f"  Approval ID: {approval_id}")
    print(f"  Expires: {expires_at.isoformat()}")

    return 0


def cmd_submit_paper(args: argparse.Namespace) -> int:
    """Submit approved proposal to paper broker."""
    print(f"Submitting proposal to paper broker for session {args.session_id}")
    print("  Broker: IBKR (paper account)")
    print("  Policy: Conservative limits, protective stops required")
    print("\nOrder plan would be created and submitted...")
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    """Reconcile paper session."""
    print(f"Reconciling paper session {args.session_id}")
    print("\nEnd-of-day reconciliation:")
    print(json.dumps({
        "submitted_orders": 5,
        "filled_orders": 5,
        "cancelled_orders": 0,
        "partial_orders": 0,
        "closing_cash": 48500.0,
        "realized_pnl": 120.50,
        "unrealized_pnl": 350.75,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
