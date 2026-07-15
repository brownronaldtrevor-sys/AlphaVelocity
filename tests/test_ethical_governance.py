from alpha_velocity.governance.engine import EthicalGovernanceEngine
from alpha_velocity.governance.models import (
    GovernanceContext,
    GovernanceDecision,
)


def clean_context(**changes):
    values = dict(
        broker_mode="PAPER",
        managed_accounts=("DU1234567",),
        dry_run=False,
        strategy_id="PAPER_TEST",
        instrument_type="STOCK",
        side="BUY",
        order_notional_pct=0.05,
        projected_gross_exposure_pct=0.20,
        projected_single_position_pct=0.05,
        daily_loss_pct=0.0,
        open_order_count=0,
        has_stop=True,
        model_validated=False,
        data_lineage_valid=True,
    )
    values.update(changes)
    return GovernanceContext(**values)


def test_clean_unvalidated_order_requires_human_approval():
    result = EthicalGovernanceEngine().evaluate(clean_context())
    assert result.decision == GovernanceDecision.REQUIRE_HUMAN_APPROVAL


def test_live_account_is_blocked():
    result = EthicalGovernanceEngine().evaluate(
        clean_context(managed_accounts=("U1234567",))
    )
    assert result.decision == GovernanceDecision.BLOCK


def test_restricted_information_is_blocked():
    result = EthicalGovernanceEngine().evaluate(
        clean_context(restricted_information_flag=True)
    )
    assert result.decision == GovernanceDecision.BLOCK


def test_manipulative_intent_is_blocked():
    result = EthicalGovernanceEngine().evaluate(
        clean_context(manipulative_intent_flag=True)
    )
    assert result.decision == GovernanceDecision.BLOCK


def test_emergency_halt_is_blocked():
    result = EthicalGovernanceEngine().evaluate(
        clean_context(emergency_halt=True)
    )
    assert result.decision == GovernanceDecision.BLOCK
