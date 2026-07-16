from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alpha_velocity.config import RiskConfig
from alpha_velocity.event.models import (
    CorporateActionEvent,
    DelistingEvent,
    OpportunityEvent,
    SignalEvent,
)
from alpha_velocity.governance.engine import EthicalGovernanceEngine
from alpha_velocity.governance.models import GovernanceContext, GovernanceDecision
from alpha_velocity.market.bars import Bar
from alpha_velocity.models import (
    AccountState,
    AssetClass,
    ConvictionTier,
    Instrument,
    Side,
    SignalProposal,
)
from alpha_velocity.risk.engine import RiskEngine


@dataclass(frozen=True)
class FillAssumptions:
    commission_per_share: float = 0.005
    minimum_commission: float = 1.0
    half_spread_bps: float = 8.0
    market_impact_coefficient: float = 0.10
    max_participation_rate: float = 0.05


@dataclass
class Trade:
    symbol: str
    bar_timestamp: datetime
    signal_timestamp: datetime
    order_type: str
    action: str
    ordered_quantity: int
    filled_quantity: int
    fill_price: float
    commission: float
    slippage: float
    order_id: str | None = None


@dataclass
class Order:
    order_id: str
    symbol: str
    action: str
    quantity: int
    order_type: str
    limit_price: float | None = None
    stop_price: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "CREATED"


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    average_cost: float = 0.0
    total_cost: float = 0.0


@dataclass
class PortfolioState:
    starting_cash: float
    cash: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    commissions: float = 0.0
    slippage: float = 0.0

    @property
    def total_position_value(self) -> float:
        return sum(p.total_cost for p in self.positions.values())

    @property
    def gross_exposure_pct(self) -> float:
        equity = self.cash + self.total_position_value + self.realized_pnl
        if equity <= 0:
            return 0.0
        return self.total_position_value / equity


class BacktestEngine:
    def __init__(
        self,
        output_dir: Path | str = ".",
        fill_model_config: dict[str, Any] | None = None,
        risk_config: RiskConfig | None = None,
        governance_enabled: bool = False,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fill_assumptions = FillAssumptions(**(fill_model_config or {}))
        self.risk_config = risk_config or RiskConfig()
        self.risk_engine = RiskEngine(self.risk_config)
        self.governance_engine = EthicalGovernanceEngine()
        self.governance_enabled = governance_enabled
        self.trades: list[Trade] = []
        self.orders: list[Order] = []
        self.rejected_orders: list[dict[str, Any]] = []
        self.portfolio = PortfolioState(starting_cash=100_000.0)
        self.portfolio.cash = self.portfolio.starting_cash
        self.events: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self.ambiguous_outcomes: list[dict[str, Any]] = []

    def run_backtest(
        self,
        daily_bars: list[Bar],
        strategy: Any,
        weekly_bars: list[Bar] | None = None,
        benchmark_bars: list[Bar] | None = None,
        opportunities: list[OpportunityEvent] | None = None,
        corporate_actions: list[CorporateActionEvent] | None = None,
        delistings: list[DelistingEvent] | None = None,
        order_type: str = "MKT",
        stop_price: float | None = None,
        target_price: float | None = None,
    ) -> dict[str, Any]:
        """Run a complete backtest with the given bars and strategy."""
        if not daily_bars:
            raise ValueError("daily_bars cannot be empty")

        self.trades = []
        self.orders = []
        self.rejected_orders = []
        self.portfolio = PortfolioState(starting_cash=100_000.0)
        self.portfolio.cash = self.portfolio.starting_cash
        self.events = []
        self.warnings = []
        self.ambiguous_outcomes = []

        symbols = set(bar.symbol for bar in daily_bars)
        if not symbols:
            raise ValueError("No symbols found in bars")

        symbol = list(symbols)[0]
        prior_bar: Bar | None = None

        for i, bar in enumerate(daily_bars):
            if bar.timestamp.tzinfo is None:
                raise ValueError(f"Bar {bar.symbol} at {bar.timestamp} is not timezone-aware")

            # Add market data event
            self.events.append(
                {
                    "event_type": "MARKET_DATA",
                    "timestamp": bar.timestamp.isoformat(),
                    "symbol": bar.symbol,
                }
            )

            strategy_context = {
                "bar": bar,
                "portfolio": self.portfolio,
                "prior_bar": prior_bar,
                "index": i,
                "total_bars": len(daily_bars),
            }

            signals = strategy.generate(strategy_context)

            for signal in signals:
                if signal.available_at > bar.timestamp:
                    self.warnings.append(
                        f"Future data: signal available_at {signal.available_at} exceeds bar timestamp {bar.timestamp}"
                    )
                    continue

                next_bar_idx = i + 1
                order = self._create_order_from_signal(signal, bar)
                self.orders.append(order)

                if next_bar_idx >= len(daily_bars):
                    continue

                next_bar = daily_bars[next_bar_idx]
                fill = self._try_fill_order(order, next_bar, signal, bar)
                if fill:
                    self.trades.append(fill)
                    self._update_portfolio(fill)
                else:
                    self.rejected_orders.append(
                        {
                            "order_id": order.order_id,
                            "symbol": order.symbol,
                            "reason": "No fill",
                            "timestamp": next_bar.timestamp.isoformat(),
                        }
                    )

            if stop_price is not None and target_price is not None:
                if (bar.high >= target_price and bar.low <= stop_price):
                    self.ambiguous_outcomes.append(
                        {
                            "timestamp": bar.timestamp.isoformat(),
                            "symbol": symbol,
                            "ambiguous": True,
                            "touched_stop": bar.low <= stop_price,
                            "touched_target": bar.high >= target_price,
                        }
                    )

            if corporate_actions:
                for action in corporate_actions:
                    if action.event_time <= bar.timestamp and action.symbol == symbol:
                        if action.ratio and action.ratio != 1.0:
                            if symbol in self.portfolio.positions:
                                pos = self.portfolio.positions[symbol]
                                pos.quantity = int(pos.quantity * action.ratio)
                                pos.average_cost = pos.average_cost / action.ratio
                        self.events.append(
                            {
                                "event_type": "CORPORATE_ACTION",
                                "timestamp": action.event_time.isoformat(),
                                "symbol": symbol,
                                "action_type": action.action_type,
                            }
                        )

            if opportunities:
                for opp in opportunities:
                    if opp.event_time <= bar.timestamp:
                        self.events.append(
                            {
                                "event_type": "OPPORTUNITY",
                                "timestamp": opp.event_time.isoformat(),
                                "opportunity_id": opp.opportunity_id,
                            }
                        )

            if delistings:
                for delisting in delistings:
                    if delisting.event_time <= bar.timestamp and delisting.symbol == symbol:
                        if symbol in self.portfolio.positions:
                            pos = self.portfolio.positions[symbol]
                            terminal_value = pos.quantity * bar.close
                            self.portfolio.realized_pnl += terminal_value - pos.total_cost
                            del self.portfolio.positions[symbol]
                        self.events.append(
                            {
                                "event_type": "DELISTING",
                                "timestamp": delisting.event_time.isoformat(),
                                "symbol": symbol,
                            }
                        )

            prior_bar = bar

        # Check for opportunities beyond backtest window
        if opportunities and daily_bars:
            last_bar_time = daily_bars[-1].timestamp
            for opp in opportunities:
                if opp.event_time > last_bar_time:
                    self.warnings.append(
                        f"Future data: opportunity {opp.opportunity_id} at {opp.event_time} is beyond backtest window"
                    )

        metrics = self._calculate_metrics(daily_bars, benchmark_bars or [])
        report = self._generate_report(metrics)
        self._save_report(report)

        return report

    def _create_order_from_signal(self, signal: SignalEvent, bar: Bar) -> Order:
        order_type = signal.metadata.get("order_type", "MKT")
        quantity = signal.metadata.get("quantity", 1)
        limit_price = signal.metadata.get("limit_price")
        stop_price = signal.metadata.get("stop_price")

        order_id = f"ORD-{len(self.orders) + 1}-{bar.timestamp.strftime('%Y%m%d%H%M%S')}"
        return Order(
            order_id=order_id,
            symbol=bar.symbol,
            action="BUY" if signal.side == "BUY" else "SELL",
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            created_at=bar.timestamp,
        )

    def _try_fill_order(
        self, order: Order, bar: Bar, signal: SignalEvent, prior_bar: Bar | None
    ) -> Trade | None:
        if order.symbol != bar.symbol:
            return None

        proposed = SignalProposal(
            strategy_id="backtest",
            instrument=Instrument(symbol=bar.symbol, asset_class=AssetClass.STOCK),
            side=Side.BUY if order.action == "BUY" else Side.SELL,
            entry_price=bar.open,
            stop_price=order.stop_price or (bar.open * 0.80),
            target_price=order.limit_price or (bar.open * 1.40),
            probability_target_before_stop=0.6,
            expected_holding_days=10.0,
            expected_return_pct=40.0,
            conviction_tier=ConvictionTier.NORMAL,
            thesis="backtest",
            model_version="1.0",
        )

        account = AccountState(
            net_liquidation=self.portfolio.cash + self.portfolio.total_position_value,
            available_funds=self.portfolio.cash,
            gross_position_value=self.portfolio.total_position_value,
            daily_pnl=0.0,
            open_orders=len(self.orders),
        )

        risk_result = self.risk_engine.evaluate(proposed, account, [])
        if not risk_result.is_approved:
            self.rejected_orders.append(
                {
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "reason": risk_result.rejected.reason if risk_result.rejected else "Unknown",
                    "timestamp": bar.timestamp.isoformat(),
                }
            )
            return None

        # Check notional value limit
        notional_value = order.quantity * bar.open
        max_notional = self.portfolio.cash * 5.0  # Max 5x account value
        if notional_value > max_notional:
            self.rejected_orders.append(
                {
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "reason": f"Notional value ${notional_value:,.0f} exceeds max ${max_notional:,.0f}",
                    "timestamp": bar.timestamp.isoformat(),
                }
            )
            return None

        if self.governance_enabled:
            gov_context = GovernanceContext(
                broker_mode="PAPER",
                managed_accounts=("DU1234567",),
                dry_run=True,
                strategy_id="backtest",
                instrument_type="STOCK",
                side=order.action,
                order_notional_pct=0.05,
                projected_gross_exposure_pct=self.portfolio.gross_exposure_pct,
                projected_single_position_pct=0.05,
                daily_loss_pct=0.0,
                open_order_count=len(self.orders),
                has_stop=order.stop_price is not None,
                model_validated=True,
                data_lineage_valid=True,
            )
            gov_result = self.governance_engine.evaluate(gov_context)
            if gov_result.decision == GovernanceDecision.BLOCK:
                self.rejected_orders.append(
                    {
                        "order_id": order.order_id,
                        "symbol": order.symbol,
                        "reason": gov_result.reasons[0] if gov_result.reasons else "Governance blocked",
                        "timestamp": bar.timestamp.isoformat(),
                    }
                )
                return None

        filled_qty = min(order.quantity, int(bar.volume * self.fill_assumptions.max_participation_rate))
        if filled_qty < 1:
            self.warnings.append(f"Insufficient volume to fill {order.order_id} at {bar.symbol}")
            return None

        direction = 1 if order.action == "BUY" else -1
        spread = bar.open * self.fill_assumptions.half_spread_bps / 10_000
        impact = bar.open * self.fill_assumptions.market_impact_coefficient * (filled_qty / max(bar.volume, 1))
        fill_price = bar.open + direction * (spread + impact)

        commission = max(self.fill_assumptions.minimum_commission, filled_qty * self.fill_assumptions.commission_per_share)
        slippage = abs(fill_price - bar.open)

        if prior_bar and prior_bar.close < bar.open:
            self.warnings.append(f"Adverse gap detected: prior close {prior_bar.close} < bar open {bar.open}")

        return Trade(
            symbol=order.symbol,
            bar_timestamp=bar.timestamp,
            signal_timestamp=signal.event_time,
            order_type=order.order_type,
            action=order.action,
            ordered_quantity=order.quantity,
            filled_quantity=filled_qty,
            fill_price=fill_price,
            commission=commission,
            slippage=slippage,
            order_id=order.order_id,
        )

    def _update_portfolio(self, trade: Trade) -> None:
        if trade.action == "BUY":
            cost = trade.filled_quantity * trade.fill_price + trade.commission
            if trade.symbol in self.portfolio.positions:
                pos = self.portfolio.positions[trade.symbol]
                new_qty = pos.quantity + trade.filled_quantity
                new_avg = (pos.average_cost * pos.quantity + trade.fill_price * trade.filled_quantity) / new_qty
                pos.quantity = new_qty
                pos.average_cost = new_avg
                pos.total_cost = new_qty * new_avg
            else:
                self.portfolio.positions[trade.symbol] = Position(
                    symbol=trade.symbol,
                    quantity=trade.filled_quantity,
                    average_cost=trade.fill_price,
                    total_cost=cost,
                )
            self.portfolio.cash -= cost
        elif trade.action == "SELL":
            if trade.symbol in self.portfolio.positions:
                pos = self.portfolio.positions[trade.symbol]
                proceeds = trade.filled_quantity * trade.fill_price - trade.commission
                realized = proceeds - (trade.filled_quantity * pos.average_cost)
                self.portfolio.realized_pnl += realized
                pos.quantity -= trade.filled_quantity
                if pos.quantity == 0:
                    del self.portfolio.positions[trade.symbol]
                else:
                    pos.total_cost = pos.quantity * pos.average_cost
                self.portfolio.cash += proceeds

        self.portfolio.commissions += trade.commission
        self.portfolio.slippage += trade.slippage

    def _calculate_metrics(self, daily_bars: list[Bar], benchmark_bars: list[Bar]) -> dict[str, Any]:
        if not daily_bars:
            return {}

        total_position_value = sum(p.total_cost for p in self.portfolio.positions.values())
        ending_equity = self.portfolio.cash + total_position_value + self.portfolio.realized_pnl
        total_return_pct = (ending_equity - self.portfolio.starting_cash) / self.portfolio.starting_cash * 100

        days = max((daily_bars[-1].timestamp - daily_bars[0].timestamp).days, 1)
        years = days / 365.25
        cagr = ((ending_equity / self.portfolio.starting_cash) ** (1 / max(years, 0.01)) - 1) * 100

        benchmark_return_pct = 0.0
        if benchmark_bars:
            benchmark_start = benchmark_bars[0].close
            benchmark_end = benchmark_bars[-1].close
            benchmark_return_pct = (benchmark_end - benchmark_start) / benchmark_start * 100

        trades_count = len(self.trades)
        wins = sum(1 for t in self.trades if t.action == "BUY" and t.filled_quantity > 0)
        hit_rate_pct = (wins / max(trades_count, 1)) * 100 if trades_count > 0 else 0.0

        return {
            "total_return_pct": round(total_return_pct, 2),
            "cagr_pct": round(cagr, 2),
            "ending_equity": round(ending_equity, 2),
            "benchmark_return_pct": round(benchmark_return_pct, 2),
            "benchmark_relative_return": round(total_return_pct - benchmark_return_pct, 2),
            "benchmark_relative_drawdown": 0.0,
            "trades": trades_count,
            "win_rate_pct": round(hit_rate_pct, 2),
            "commissions": round(self.portfolio.commissions, 2),
            "slippage": round(self.portfolio.slippage, 2),
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown_pct": 0.0,
        }

    def _generate_report(self, metrics: dict[str, Any]) -> dict[str, Any]:
        return {
            "backtest_id": datetime.now(timezone.utc).isoformat(),
            "events_processed": len(self.events),
            "trades": [
                {
                    **asdict(t),
                    "bar_timestamp": t.bar_timestamp.isoformat(),
                    "signal_timestamp": t.signal_timestamp.isoformat(),
                }
                for t in self.trades
            ],
            "orders": [
                {
                    "order_id": o.order_id,
                    "symbol": o.symbol,
                    "action": o.action,
                    "quantity": o.quantity,
                    "order_type": o.order_type,
                    "status": o.status,
                    "created_at": o.created_at.isoformat(),
                }
                for o in self.orders
            ],
            "rejected_orders": self.rejected_orders,
            "portfolio": {
                "starting_cash": self.portfolio.starting_cash,
                "ending_cash": round(self.portfolio.cash, 2),
                "positions": {
                    symbol: {
                        "quantity": pos.quantity,
                        "average_cost": round(pos.average_cost, 2),
                        "total_cost": round(pos.total_cost, 2),
                    }
                    for symbol, pos in self.portfolio.positions.items()
                },
            },
            "metrics": metrics,
            "events": self.events,
            "ambiguous_outcomes": self.ambiguous_outcomes,
            "warnings": self.warnings,
            "broker_transmissions": 0,
        }

    def _save_report(self, report: dict[str, Any]) -> None:
        report_path = self.output_dir / "backtest_report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str))
