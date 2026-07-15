from alpha_velocity.config import RiskConfig
from alpha_velocity.models import (
    AccountState,
    AssetClass,
    ConvictionTier,
    Instrument,
    Side,
    SignalProposal,
)
from alpha_velocity.risk.engine import RiskEngine


def proposal(**overrides):
    values = dict(
        strategy_id="test",
        instrument=Instrument("TEST", AssetClass.STOCK),
        side=Side.BUY,
        entry_price=10,
        stop_price=9,
        target_price=13,
        probability_target_before_stop=0.60,
        expected_holding_days=10,
        expected_return_pct=30,
        conviction_tier=ConvictionTier.NORMAL,
        thesis="test",
        model_version="1",
    )
    values.update(overrides)
    return SignalProposal(**values)


def account(**overrides):
    values = dict(
        net_liquidation=10_000,
        available_funds=10_000,
        gross_position_value=0,
        daily_pnl=0,
        open_orders=0,
    )
    values.update(overrides)
    return AccountState(**values)


def test_sizes_by_trade_risk():
    engine = RiskEngine(RiskConfig(max_risk_per_trade_pct=0.01))
    result = engine.evaluate(proposal(), account(), [])
    assert result.is_approved
    assert result.approved.quantity == 100
    assert result.approved.estimated_dollar_risk == 100


def test_rejects_low_reward_to_risk():
    engine = RiskEngine(RiskConfig(minimum_reward_to_risk=2.0))
    result = engine.evaluate(proposal(target_price=11), account(), [])
    assert not result.is_approved


def test_daily_loss_kill():
    engine = RiskEngine(RiskConfig(max_daily_loss_pct=0.03))
    result = engine.evaluate(proposal(), account(daily_pnl=-301), [])
    assert not result.is_approved


def test_global_kill_switch():
    engine = RiskEngine(RiskConfig())
    engine.activate_kill_switch()
    result = engine.evaluate(proposal(), account(), [])
    assert not result.is_approved
