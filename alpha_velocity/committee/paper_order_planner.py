"""Paper order planning and execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class PaperOrderPlan:
    """Deterministic plan for paper order submission."""

    plan_id: str
    session_id: str
    proposal_id: str
    observation_time: datetime
    
    # Positions to open/increase
    new_positions: tuple[dict[str, Any], ...] = ()
    
    # Positions to reduce/exit
    reduction_positions: tuple[dict[str, Any], ...] = ()
    
    # Protective stops required
    protective_stops: tuple[dict[str, Any], ...] = ()
    
    # Dependency order (reductions fund additions)
    submission_order: tuple[str, ...] = ()  # Symbol order
    
    # Cost estimates
    estimated_transaction_costs: float = 0.0
    estimated_commissions: float = 0.0
    
    # Totals
    total_new_notional: float = 0.0
    total_reduction_notional: float = 0.0
    net_cash_impact: float = 0.0
    
    # Policy
    limit_or_market: str = "LIMIT"  # "LIMIT" or "MARKET"
    conservative_limits: bool = True
    
    notes: str = ""
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "session_id": self.session_id,
            "proposal_id": self.proposal_id,
            "observation_time": self.observation_time.isoformat(),
            "new_positions": self.new_positions,
            "reduction_positions": self.reduction_positions,
            "protective_stops": self.protective_stops,
            "submission_order": self.submission_order,
            "estimated_transaction_costs": self.estimated_transaction_costs,
            "estimated_commissions": self.estimated_commissions,
            "total_new_notional": self.total_new_notional,
            "total_reduction_notional": self.total_reduction_notional,
            "net_cash_impact": self.net_cash_impact,
            "limit_or_market": self.limit_or_market,
            "conservative_limits": self.conservative_limits,
            "notes": self.notes,
            "schema_version": self.schema_version,
        }


class PaperOrderPlanner:
    """Creates deterministic paper order plans from approved capital proposals."""

    def create_plan(
        self,
        session_id: str,
        proposal: dict[str, Any],
        current_positions: dict[str, float],
        reference_prices: dict[str, float],
    ) -> PaperOrderPlan:
        """Create paper order plan from proposal."""
        import uuid

        plan_id = f"PLAN-{uuid.uuid4().hex[:8]}"
        proposal_id = proposal.get("proposal_id", "")
        observation_time = datetime.now(timezone.utc)

        # Determine new positions and reductions
        new_positions = []
        reduction_positions = []
        protective_stops = []
        submission_order = []

        proposed_holdings = proposal.get("proposed_holdings", [])
        for holding in proposed_holdings:
            symbol = holding.get("symbol", "")
            current_qty = current_positions.get(symbol, 0.0)
            proposed_qty = holding.get("proposed_quantity", 0.0)
            price = reference_prices.get(symbol, 0.0)

            if proposed_qty > current_qty:
                # New position or increase
                delta_qty = proposed_qty - current_qty
                new_positions.append({
                    "symbol": symbol,
                    "quantity": int(delta_qty),
                    "reference_price": price,
                    "order_type": "BUY",
                    "limit_price": price * 1.002,  # Conservative limit above current
                    "tif": "DAY",
                })
                submission_order.append(symbol)

                # Add protective stop if configured
                if holding.get("protective_stop_pct"):
                    stop_price = price * (1.0 - holding.get("protective_stop_pct", 0.02))
                    protective_stops.append({
                        "symbol": symbol,
                        "quantity": int(delta_qty),
                        "stop_price": stop_price,
                        "order_type": "SELL",
                    })

            elif proposed_qty < current_qty and current_qty > 0:
                # Reduction or exit
                delta_qty = current_qty - proposed_qty
                reduction_positions.append({
                    "symbol": symbol,
                    "quantity": int(delta_qty),
                    "reference_price": price,
                    "order_type": "SELL",
                    "limit_price": price * 0.998,  # Conservative limit below current
                    "tif": "DAY",
                })
                submission_order.append(symbol)

        # Calculate costs
        transaction_cost = sum(
            pos.get("quantity", 0) * pos.get("reference_price", 0) * 0.0001
            for pos in new_positions + reduction_positions
        )
        commissions = len(new_positions) * 1.0 + len(reduction_positions) * 1.0

        total_new = sum(
            pos.get("quantity", 0) * pos.get("reference_price", 0)
            for pos in new_positions
        )
        total_reduction = sum(
            pos.get("quantity", 0) * pos.get("reference_price", 0)
            for pos in reduction_positions
        )

        return PaperOrderPlan(
            plan_id=plan_id,
            session_id=session_id,
            proposal_id=proposal_id,
            observation_time=observation_time,
            new_positions=tuple(new_positions),
            reduction_positions=tuple(reduction_positions),
            protective_stops=tuple(protective_stops),
            submission_order=tuple(submission_order),
            estimated_transaction_costs=transaction_cost,
            estimated_commissions=commissions,
            total_new_notional=total_new,
            total_reduction_notional=total_reduction,
            net_cash_impact=total_reduction - total_new,
            limit_or_market="LIMIT",
            conservative_limits=True,
        )
