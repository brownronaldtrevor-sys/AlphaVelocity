from __future__ import annotations
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from alpha_velocity.data.csv_loader import load_universe
from alpha_velocity.paper.broker import SimulatedBroker
from alpha_velocity.paper.models import PaperOrder
from alpha_velocity.paper.opportunity_factory import from_technical
from alpha_velocity.portfolio.competition import build_report
from alpha_velocity.portfolio.exposure import DynamicExposureOptimizer, OpportunityType
from alpha_velocity.portfolio.rebalance import make_rebalance_instructions
from alpha_velocity.signals.technical import compute_snapshot

class DailyPaperPipeline:
    def __init__(
        self,
        symbols: list[str],
        data_folder: str,
        state_path: str,
        report_folder: str,
        starting_cash: float = 100_000,
    ) -> None:
        self.symbols = symbols
        self.data_folder = data_folder
        self.report_folder = Path(report_folder)
        self.report_folder.mkdir(parents=True, exist_ok=True)
        self.broker = SimulatedBroker(state_path, starting_cash=starting_cash)
        self.optimizer = DynamicExposureOptimizer(
            reserve_cash_pct=15.0,
            replacement_margin_pct=8.0,
            concentration_power=2.0,
        )

    def run(self) -> dict:
        universe = load_universe(self.data_folder, self.symbols)
        if not universe:
            raise RuntimeError("No symbol CSV files were found.")

        latest_prices = {s: bars[-1].close for s, bars in universe.items() if bars}
        self.broker.mark(latest_prices)
        equity = self.broker.account.equity()

        opportunities = []
        snapshots = {}
        for symbol, bars in universe.items():
            if len(bars) < 60:
                continue
            snapshot = compute_snapshot(bars)
            snapshots[symbol] = snapshot
            position = self.broker.account.positions.get(symbol)
            current_value = position.market_value if position else 0.0
            current_weight = 100 * current_value / equity if equity else 0.0

            kind = (
                OpportunityType.EARLY_INFLECTION
                if snapshot.reversal_score >= 65 and snapshot.trend_score < 60
                else OpportunityType.CONFIRMED_INFLECTION
            )
            max_weight = 10.0 if kind == OpportunityType.EARLY_INFLECTION else 25.0
            opportunities.append(from_technical(
                symbol=symbol,
                snapshot=snapshot,
                current_weight_pct=current_weight,
                opportunity_type=kind,
                max_weight_pct=max_weight,
            ))

        exposures = self.optimizer.allocate(opportunities)
        competition = build_report(opportunities, exposures)
        instructions = make_rebalance_instructions(exposures)

        fills = []
        for instruction in instructions:
            if instruction.opportunity_id not in latest_prices:
                continue
            price = latest_prices[instruction.opportunity_id]
            desired_value = equity * instruction.target_weight_pct / 100
            current = self.broker.account.positions.get(instruction.opportunity_id)
            current_value = current.market_value if current else 0.0
            delta_value = desired_value - current_value
            quantity = int(abs(delta_value) // price)
            if quantity < 1:
                continue
            action = "BUY" if delta_value > 0 else "SELL"
            fill = self.broker.execute(PaperOrder(
                symbol=instruction.opportunity_id,
                action=action,
                quantity=quantity,
                reference_price=price,
                reason=f"Target exposure {instruction.target_weight_pct:.2f}%",
            ))
            if fill:
                fills.append(asdict(fill))

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "equity_before_rebalance": equity,
            "best_opportunity": competition.best_opportunity_id,
            "current_portfolio_score": competition.current_portfolio_score,
            "proposed_portfolio_score": competition.proposed_portfolio_score,
            "snapshots": {k: asdict(v) for k, v in snapshots.items()},
            "target_exposures": [asdict(e) for e in exposures],
            "instructions": [asdict(i) for i in instructions],
            "fills": fills,
            "account_after": self.broker.account.to_dict(),
            "disclaimer": (
                "Test-only paper output. Technical estimates are prototype heuristics, "
                "not trained or validated production forecasts."
            ),
        }
        path = self.report_folder / f"paper_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(report, indent=2, sort_keys=True))
        return report
