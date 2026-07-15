from __future__ import annotations

from alpha_velocity.models import (
    AssetClass,
    ConvictionTier,
    Instrument,
    Side,
    SignalProposal,
)
from alpha_velocity.strategies.base import Strategy


class DemonstrationStrategy(Strategy):
    """
    Wiring test only. This is NOT a production alpha model and should not be
    interpreted as a recommendation or evidence of profitability.
    """

    strategy_id = "DEMO_WIRING_TEST"

    def generate(self) -> list[SignalProposal]:
        return [
            SignalProposal(
                strategy_id=self.strategy_id,
                instrument=Instrument(
                    symbol="AAPL",
                    asset_class=AssetClass.STOCK,
                    exchange="SMART",
                    currency="USD",
                    primary_exchange="NASDAQ",
                ),
                side=Side.BUY,
                entry_price=100.0,
                stop_price=95.0,
                target_price=112.0,
                probability_target_before_stop=0.55,
                expected_holding_days=10,
                expected_return_pct=12.0,
                conviction_tier=ConvictionTier.NORMAL,
                thesis="Synthetic proposal used only to verify system wiring.",
                model_version="demo-0.1",
            )
        ]
