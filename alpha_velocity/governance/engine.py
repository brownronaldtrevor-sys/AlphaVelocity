from __future__ import annotations

from alpha_velocity.governance.models import (
    GovernanceContext,
    GovernanceDecision,
    GovernanceResult,
)


class EthicalGovernanceEngine:
    """Independent hard controls that strategy code cannot override."""

    def __init__(
        self,
        max_order_notional_pct: float = 0.10,
        max_gross_exposure_pct: float = 0.30,
        max_single_position_pct: float = 0.10,
        max_daily_loss_pct: float = 0.02,
        max_open_orders: int = 12,
        require_human_approval: bool = True,
    ) -> None:
        self.max_order_notional_pct = max_order_notional_pct
        self.max_gross_exposure_pct = max_gross_exposure_pct
        self.max_single_position_pct = max_single_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_open_orders = max_open_orders
        self.require_human_approval = require_human_approval

    def evaluate(self, ctx: GovernanceContext) -> GovernanceResult:
        reasons: list[str] = []

        if ctx.emergency_halt:
            reasons.append("Emergency halt is active.")
        if ctx.broker_mode != "PAPER":
            reasons.append("Only PAPER broker mode is authorized.")
        if not ctx.managed_accounts:
            reasons.append("No managed IBKR account was received.")
        if any(not account.upper().startswith("DU") for account in ctx.managed_accounts):
            reasons.append("A connected account is not positively identified as an IBKR paper account.")
        if ctx.restricted_information_flag:
            reasons.append("Restricted or potentially material non-public information is flagged.")
        if ctx.manipulative_intent_flag:
            reasons.append("Potential manipulative trading intent is flagged.")
        if not ctx.data_lineage_valid:
            reasons.append("Required point-in-time data lineage is invalid or incomplete.")
        if ctx.order_notional_pct > self.max_order_notional_pct:
            reasons.append("Order notional exceeds the governance limit.")
        if ctx.projected_gross_exposure_pct > self.max_gross_exposure_pct:
            reasons.append("Projected gross exposure exceeds the governance limit.")
        if ctx.projected_single_position_pct > self.max_single_position_pct:
            reasons.append("Projected position concentration exceeds the governance limit.")
        if ctx.daily_loss_pct <= -abs(self.max_daily_loss_pct):
            reasons.append("Daily-loss kill switch has been reached.")
        if ctx.open_order_count >= self.max_open_orders:
            reasons.append("Open-order limit has been reached.")
        if not ctx.has_stop:
            reasons.append("A protective stop is required.")
        if ctx.instrument_type.upper() not in {"STOCK"}:
            reasons.append("Only common-stock paper orders are authorized in this baseline.")
        if ctx.side.upper() != "BUY":
            reasons.append("Shorting and non-long directions are disabled in this baseline.")

        if reasons:
            return GovernanceResult(GovernanceDecision.BLOCK, tuple(reasons))

        if self.require_human_approval or not ctx.model_validated:
            approval_reasons = []
            if self.require_human_approval:
                approval_reasons.append("Explicit human approval is required before paper transmission.")
            if not ctx.model_validated:
                approval_reasons.append("The active selector is not yet statistically validated.")
            return GovernanceResult(
                GovernanceDecision.REQUIRE_HUMAN_APPROVAL,
                tuple(approval_reasons),
            )

        return GovernanceResult(GovernanceDecision.ALLOW, ("All governance checks passed.",))
