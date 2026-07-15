from __future__ import annotations

import math
from dataclasses import dataclass

from alpha_velocity.config import RiskConfig
from alpha_velocity.models import (
    AccountState,
    ApprovedOrderPlan,
    AssetClass,
    ConvictionTier,
    PositionState,
    Rejection,
    Side,
    SignalProposal,
)


@dataclass(frozen=True)
class RiskDecision:
    approved: ApprovedOrderPlan | None = None
    rejected: Rejection | None = None

    @property
    def is_approved(self) -> bool:
        return self.approved is not None


class RiskEngine:
    """Independent, deterministic controls. Strategy code cannot bypass this class."""

    def __init__(self, config: RiskConfig) -> None:
        self.config = config
        self.kill_switch_active = False

    def activate_kill_switch(self) -> None:
        self.kill_switch_active = True

    def clear_kill_switch(self) -> None:
        self.kill_switch_active = False

    def _tier_cap(self, tier: ConvictionTier) -> float:
        if tier == ConvictionTier.GENERATIONAL:
            return self.config.absolute_position_cap_pct
        if tier == ConvictionTier.EXCEPTIONAL:
            return self.config.exceptional_position_pct
        if tier == ConvictionTier.STRONG:
            return self.config.max_single_position_pct
        return min(self.config.max_single_position_pct, 0.10)

    def evaluate(
        self,
        proposal: SignalProposal,
        account: AccountState,
        positions: list[PositionState],
    ) -> RiskDecision:
        if self.kill_switch_active:
            return RiskDecision(rejected=Rejection("Global kill switch is active."))

        if account.net_liquidation <= 0:
            return RiskDecision(rejected=Rejection("Net liquidation must be positive."))

        if account.daily_pnl <= -account.net_liquidation * self.config.max_daily_loss_pct:
            return RiskDecision(rejected=Rejection("Daily loss limit reached."))

        if account.open_orders >= self.config.max_open_orders:
            return RiskDecision(rejected=Rejection("Maximum open-order count reached."))

        if proposal.side == Side.SELL and not self.config.allow_shorting:
            return RiskDecision(rejected=Rejection("Shorting is disabled."))

        if proposal.instrument.asset_class == AssetClass.FUTURE and not self.config.allow_futures:
            return RiskDecision(rejected=Rejection("Futures trading is disabled."))

        if proposal.instrument.asset_class == AssetClass.OPTION and not self.config.allow_options:
            return RiskDecision(rejected=Rejection("Options trading is disabled."))

        if proposal.entry_price <= 0 or proposal.stop_price <= 0 or proposal.target_price <= 0:
            return RiskDecision(rejected=Rejection("Prices must be positive."))

        if proposal.risk_per_unit <= 0:
            return RiskDecision(rejected=Rejection("Stop must define positive risk."))

        if proposal.reward_to_risk < self.config.minimum_reward_to_risk:
            return RiskDecision(
                rejected=Rejection(
                    f"Reward/risk {proposal.reward_to_risk:.2f} is below "
                    f"{self.config.minimum_reward_to_risk:.2f}."
                )
            )

        if not 0 < proposal.probability_target_before_stop < 1:
            return RiskDecision(rejected=Rejection("Probability must be between zero and one."))

        existing_value = sum(abs(p.market_value) for p in positions)
        max_gross = account.net_liquidation * self.config.max_gross_exposure_pct
        gross_capacity = max(0.0, max_gross - existing_value)

        tier_cap = self._tier_cap(proposal.conviction_tier)
        concentration_capacity = account.net_liquidation * tier_cap
        standard_notional_cap = account.net_liquidation * self.config.max_order_notional_pct

        # Exceptional tiers may exceed the standard order cap, but never the tier cap.
        if proposal.conviction_tier in {
            ConvictionTier.EXCEPTIONAL,
            ConvictionTier.GENERATIONAL,
        }:
            notional_capacity = concentration_capacity
        else:
            notional_capacity = min(concentration_capacity, standard_notional_cap)

        dollar_risk_budget = account.net_liquidation * self.config.max_risk_per_trade_pct
        quantity_by_risk = math.floor(dollar_risk_budget / proposal.risk_per_unit)
        quantity_by_notional = math.floor(
            min(notional_capacity, gross_capacity, account.available_funds)
            / proposal.entry_price
        )
        quantity = min(quantity_by_risk, quantity_by_notional)

        if quantity < 1:
            return RiskDecision(rejected=Rejection("No positive quantity fits current limits."))

        notional = quantity * proposal.entry_price
        dollar_risk = quantity * proposal.risk_per_unit
        allocation = notional / account.net_liquidation

        return RiskDecision(
            approved=ApprovedOrderPlan(
                proposal=proposal,
                quantity=quantity,
                estimated_notional=notional,
                estimated_dollar_risk=dollar_risk,
                allocation_pct=allocation,
                approval_reason=(
                    f"Approved by deterministic risk controls; tier cap={tier_cap:.1%}, "
                    f"trade risk={dollar_risk/account.net_liquidation:.2%}, "
                    f"reward/risk={proposal.reward_to_risk:.2f}."
                ),
            )
        )
