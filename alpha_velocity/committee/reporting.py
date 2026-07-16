"""Morning committee and end-of-day reconciliation reporting."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class CommitteeReportBuilder:
    """Builds deterministic morning and end-of-day reports."""

    @staticmethod
    def build_morning_report(
        session: Any,  # DailyCommitteeSession
        ranking_batch: Any,  # RankingBatch
        proposal: dict[str, Any],
        risk_decision: dict[str, Any],
        governance_decision: dict[str, Any],
        market_regime: str = "neutral",
    ) -> dict[str, Any]:
        """Build morning investment committee report."""
        ranked_ops = ranking_batch.get("ranked_opportunities", [])

        high_priority_triggered = [
            op for op in ranked_ops
            if op.get("ranking_state") == "HIGH_PRIORITY_TRIGGERED"
        ]
        high_priority_waiting = [
            op for op in ranked_ops
            if op.get("ranking_state") == "HIGH_PRIORITY_WAITING_FOR_TRIGGER"
        ]

        return {
            "report_id": f"MORNING-{session.session_id}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "session_id": session.session_id,
            "observation_time": session.observation_time.isoformat(),
            "dry_run": session.dry_run,
            "transmit": session.transmit,
            "market_regime": market_regime,
            "universe": {
                "size": session.universe_size,
                "exclusions": session.exclusions_count,
            },
            "ranking": {
                "total_opportunities": session.total_opportunities_ranked,
                "high_priority_triggered": len(high_priority_triggered),
                "high_priority_waiting": len(high_priority_waiting),
                "top_5_opportunities": [
                    {
                        "rank": op.get("rank"),
                        "symbol": op.get("opportunity_id", ""),
                        "score": op.get("overall_research_score"),
                        "state": op.get("ranking_state"),
                        "contributors": op.get("positive_contributors", [])[:3],
                    }
                    for op in ranked_ops[:5]
                ],
                "high_priority_triggered_list": [
                    {
                        "rank": op.get("rank"),
                        "symbol": op.get("opportunity_id", ""),
                        "score": op.get("overall_research_score"),
                    }
                    for op in high_priority_triggered[:10]
                ],
                "waiting_for_trigger_list": [
                    {
                        "rank": op.get("rank"),
                        "symbol": op.get("opportunity_id", ""),
                        "score": op.get("overall_research_score"),
                    }
                    for op in high_priority_waiting[:10]
                ],
            },
            "capital_proposal": {
                "proposal_id": proposal.get("proposal_id"),
                "proposed_cash": proposal.get("proposed_cash", 0.0),
                "proposed_gross_exposure": proposal.get("proposed_gross_exposure", 0.0),
                "proposed_holdings_count": len(proposal.get("proposed_holdings", [])),
                "estimated_transaction_costs": proposal.get("estimated_costs", 0.0),
            },
            "current_portfolio": {
                "equity": session.current_equity,
                "cash": session.current_cash,
                "gross_exposure": session.current_equity - session.current_cash,
            },
            "proposed_changes": {
                "new_positions": len([h for h in proposal.get("proposed_holdings", []) if h.get("current_holding_id") is None]),
                "increased_positions": len([h for h in proposal.get("proposed_holdings", []) if h.get("current_holding_id") is not None]),
                "closed_positions": 0,  # Would calculate from proposal
                "cash_impact": proposal.get("proposed_cash", 0.0) - session.current_cash,
            },
            "risk_review": {
                "review_id": session.risk_review_id,
                "approved": session.risk_approved,
                "rejection_reasons": list(session.risk_rejection_reasons) if not session.risk_approved else [],
            },
            "governance_review": {
                "review_id": session.governance_review_id,
                "approved": session.governance_approved,
                "rejection_reasons": list(session.governance_rejection_reasons) if not session.governance_approved else [],
            },
            "human_approval": {
                "status": "APPROVED" if session.human_approval else "PENDING",
                "approved_by": session.human_approval.approved_by if session.human_approval else "",
                "approved_at": session.human_approval.approved_at.isoformat() if session.human_approval else None,
                "expires_at": session.human_approval.expires_at.isoformat() if session.human_approval else None,
            },
            "execution_readiness": {
                "workflow_state": session.workflow_state.value,
                "ready_for_submission": (
                    session.workflow_state == "APPROVED_FOR_PAPER_SUBMISSION"
                ),
            },
            "major_risks": [
                "Capital concentration in single opportunity",
                "Liquidity constraints on paper account",
                "Market regime shift not yet reflected",
            ],
            "unresolved_warnings": [],
            "schema_version": "1.0.0",
        }

    @staticmethod
    def build_reconciliation_report(
        session: Any,  # DailyCommitteeSession
        fills: list[dict[str, Any]],
        cancellations: list[dict[str, Any]],
        closing_positions: dict[str, float],
        closing_cash: float,
        realized_pnl: float,
        unrealized_pnl: float,
    ) -> dict[str, Any]:
        """Build end-of-day reconciliation report."""
        return {
            "report_id": f"RECON-{session.session_id}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "session_id": session.session_id,
            "observation_time": session.observation_time.isoformat(),
            "submitted_orders": {
                "total": len(session.submitted_orders),
                "filled": len(session.filled_orders),
                "cancelled": len(session.cancelled_orders),
                "partial": len(session.partial_orders),
            },
            "fills": [
                {
                    "order_id": f.get("order_id"),
                    "symbol": f.get("symbol"),
                    "quantity": f.get("quantity"),
                    "filled_price": f.get("filled_price"),
                    "filled_at": f.get("filled_at"),
                    "fill_type": f.get("fill_type", "FULL"),
                }
                for f in fills[:50]
            ],
            "cancellations": [
                {
                    "order_id": c.get("order_id"),
                    "symbol": c.get("symbol"),
                    "quantity": c.get("quantity"),
                    "reason": c.get("reason"),
                }
                for c in cancellations[:20]
            ],
            "closing_state": {
                "positions": closing_positions,
                "cash": closing_cash,
                "gross_exposure": sum(abs(v) for v in closing_positions.values()),
            },
            "pnl": {
                "realized": realized_pnl,
                "unrealized": unrealized_pnl,
                "total": realized_pnl + unrealized_pnl,
            },
            "discrepancies": [],
            "unresolved_orders": [],
            "next_day_follow_ups": [],
            "ledger_record": session.morning_report_id,
            "schema_version": "1.0.0",
        }

    @staticmethod
    def to_markdown(
        morning_report: dict[str, Any],
        session_id: str,
    ) -> str:
        """Convert morning report to human-readable Markdown."""
        lines = []
        lines.append("# Daily Investment Committee Report\n")
        lines.append(f"**Session ID**: {session_id}")
        lines.append(f"**Generated**: {morning_report.get('generated_at')}")
        lines.append(f"**Observation Time**: {morning_report.get('observation_time')}\n")

        lines.append("## Market Regime")
        lines.append(f"- Regime: {morning_report.get('market_regime', 'neutral')}\n")

        lines.append("## Universe")
        lines.append(f"- Total opportunities: {morning_report.get('universe', {}).get('size', 0)}")
        lines.append(f"- Exclusions: {morning_report.get('universe', {}).get('exclusions', 0)}\n")

        ranking = morning_report.get("ranking", {})
        lines.append("## Ranking Summary")
        lines.append(f"- Total ranked: {ranking.get('total_opportunities', 0)}")
        lines.append(f"- High priority triggered: {ranking.get('high_priority_triggered', 0)}")
        lines.append(f"- Waiting for trigger: {ranking.get('high_priority_waiting', 0)}\n")

        lines.append("### Top 5 Opportunities")
        for op in ranking.get("top_5_opportunities", []):
            lines.append(f"- Rank {op.get('rank')}: {op.get('symbol')} ({op.get('score', 0):.1f})")
            lines.append(f"  State: {op.get('state')}")
            lines.append(f"  Drivers: {', '.join(op.get('contributors', [])[:2])}\n")

        lines.append("## Current Portfolio vs Proposal")
        current = morning_report.get("current_portfolio", {})
        proposed = morning_report.get("proposed_changes", {})
        lines.append(f"- Current cash: ${current.get('cash', 0):,.0f}")
        lines.append(f"- Proposed cash: ${morning_report.get('capital_proposal', {}).get('proposed_cash', 0):,.0f}")
        lines.append(f"- New positions: {proposed.get('new_positions', 0)}")
        lines.append(f"- Increased positions: {proposed.get('increased_positions', 0)}\n")

        lines.append("## Risk and Governance")
        risk = morning_report.get("risk_review", {})
        gov = morning_report.get("governance_review", {})
        lines.append(f"- Risk approved: {'✓' if risk.get('approved') else '✗'}")
        if risk.get("rejection_reasons"):
            lines.append(f"  Reasons: {', '.join(risk['rejection_reasons'])}")
        lines.append(f"- Governance approved: {'✓' if gov.get('approved') else '✗'}")
        if gov.get("rejection_reasons"):
            lines.append(f"  Reasons: {', '.join(gov['rejection_reasons'])}\n")

        lines.append("## Approval Status")
        approval = morning_report.get("human_approval", {})
        lines.append(f"- Status: {approval.get('status', 'PENDING')}")
        if approval.get("approved_by"):
            lines.append(f"- Approved by: {approval.get('approved_by')}")
            lines.append(f"- Expires: {approval.get('expires_at')}\n")

        lines.append("## Execution Readiness")
        readiness = morning_report.get("execution_readiness", {})
        lines.append(f"- Workflow state: {readiness.get('workflow_state', 'UNKNOWN')}")
        lines.append(f"- Ready for submission: {'Yes' if readiness.get('ready_for_submission') else 'No'}\n")

        lines.append("## Major Risks")
        for risk in morning_report.get("major_risks", []):
            lines.append(f"- {risk}\n")

        return "\n".join(lines)
