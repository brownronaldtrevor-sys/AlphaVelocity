from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timezone

from alpha_velocity.audit import AuditLogger
from alpha_velocity.broker.ibkr import IBKRApp
from alpha_velocity.learning.journal import PredictionJournal
from alpha_velocity.learning.models import ForecastRecord
from alpha_velocity.models import (
    AccountState,
    AssetClass,
    ConvictionTier,
    Instrument,
    PositionState,
    Side,
    SignalProposal,
)
from alpha_velocity.paper_auto.account_gate import require_ibkr_paper_account
from alpha_velocity.paper_auto.selector import ConservativePaperSelector
from alpha_velocity.risk.engine import RiskEngine


class PaperExecutionController:
    def __init__(
        self,
        app: IBKRApp,
        risk: RiskEngine,
        audit: AuditLogger,
        journal: PredictionJournal,
    ) -> None:
        self.app = app
        self.risk = risk
        self.audit = audit
        self.journal = journal
        self.selector = ConservativePaperSelector(
            max_positions=3,
            max_weight_pct=10.0,
            minimum_composite=62.0,
            minimum_price=1.0,
            minimum_volume_ratio=0.45,
        )

    def execute_from_report(self, report: dict) -> dict:
        require_ibkr_paper_account(
            configured_mode=self.app.config.broker.mode,
            accounts=self.app.accounts,
            dry_run=self.app.config.execution.dry_run,
        )
        if not self.app.open_orders_complete.is_set():
            raise RuntimeError(
                "Open-order reconciliation did not complete. Automatic paper execution is blocked."
            )

        snapshot = self.app.require_account_snapshot()
        account_state = AccountState(
            net_liquidation=snapshot["NetLiquidation"],
            available_funds=snapshot["AvailableFunds"],
            gross_position_value=snapshot["GrossPositionValue"],
            daily_pnl=0.0,  # Daily P&L subscription is not yet wired; conservative limits still apply.
            open_orders=len(self.app.open_order_ids),
        )

        ranked = report.get("technical_rank", [])
        selections = self.selector.select(ranked)

        latest_by_symbol = {
            str(row["symbol"]): float(row["close"])
            for row in ranked
        }
        positions = [
            PositionState(
                symbol=symbol,
                quantity=float(raw.get("quantity", 0.0)),
                market_price=latest_by_symbol.get(symbol, float(raw.get("avg_cost", 0.0))),
            )
            for symbol, raw in self.app.positions.items()
            if float(raw.get("quantity", 0.0)) != 0
        ]

        results = []
        for selection in selections:
            if selection.symbol in self.app.open_order_symbols:
                results.append({
                    "symbol": selection.symbol,
                    "status": "SKIPPED",
                    "reason": "An API-visible open order already exists for this symbol.",
                })
                continue
            existing_qty = float(self.app.positions.get(selection.symbol, {}).get("quantity", 0.0))
            if existing_qty > 0:
                results.append({
                    "symbol": selection.symbol,
                    "status": "SKIPPED",
                    "reason": "A long position already exists; v1.1 does not pyramid automatically.",
                })
                continue

            entry = selection.reference_price * 1.001
            stop = selection.reference_price * (1.0 - selection.stop_pct)
            target = selection.reference_price * (1.0 + selection.target_pct)

            forecast_id = str(uuid.uuid4())
            proposal = SignalProposal(
                strategy_id="PAPER_LEARNING_V1",
                instrument=Instrument(
                    symbol=selection.symbol,
                    asset_class=AssetClass.STOCK,
                    exchange="SMART",
                    currency="USD",
                ),
                side=Side.BUY,
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                probability_target_before_stop=selection.probability_target_before_stop,
                expected_holding_days=20.0,
                expected_return_pct=selection.expected_return_pct,
                conviction_tier=ConvictionTier.NORMAL,
                thesis="; ".join(selection.rationale),
                model_version="champion_technical_prototype_v1",
            )

            decision = self.risk.evaluate(proposal, account_state, positions)
            if not decision.is_approved:
                results.append({
                    "symbol": selection.symbol,
                    "status": "REJECTED_BY_RISK",
                    "reason": decision.rejected.reason,
                })
                continue

            approved = decision.approved
            self.journal.append_forecast(
                ForecastRecord(
                    forecast_id=forecast_id,
                    model_id=proposal.model_version,
                    symbol=selection.symbol,
                    decision_time=proposal.generated_at.isoformat(),
                    horizon_days=20,
                    probability_target_before_stop=proposal.probability_target_before_stop,
                    expected_return_pct=proposal.expected_return_pct,
                    expected_adverse_pct=-selection.stop_pct * 100.0,
                    target_pct=selection.target_pct * 100.0,
                    stop_pct=selection.stop_pct * 100.0,
                    feature_snapshot={
                        "entry_price": entry,
                        "stop_price": stop,
                        "target_price": target,
                        "technical_rank": float(selection.rank),
                    },
                    rationale=list(selection.rationale),
                )
            )

            order_ids = self.app.place_bracket(approved)
            results.append({
                "symbol": selection.symbol,
                "status": "PAPER_BRACKET_SUBMITTED",
                "forecast_id": forecast_id,
                "order_ids": order_ids,
                "quantity": approved.quantity,
                "entry_price": entry,
                "stop_price": stop,
                "target_price": target,
                "allocation_pct": approved.allocation_pct,
                "estimated_dollar_risk": approved.estimated_dollar_risk,
            })

            # Update local capacity so several orders cannot each consume the original snapshot.
            account_state = AccountState(
                net_liquidation=account_state.net_liquidation,
                available_funds=max(
                    0.0, account_state.available_funds - approved.estimated_notional
                ),
                gross_position_value=(
                    account_state.gross_position_value + approved.estimated_notional
                ),
                daily_pnl=account_state.daily_pnl,
                open_orders=account_state.open_orders + 3,
            )
            positions.append(
                PositionState(
                    symbol=selection.symbol,
                    quantity=approved.quantity,
                    market_price=entry,
                )
            )

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "IBKR_PAPER_AUTOMATIC",
            "accounts": self.app.accounts,
            "model_id": "champion_technical_prototype_v1",
            "results": results,
            "warning": (
                "Orders were sent only after the connected account passed the DU paper-account gate. "
                "The stock selector remains an unvalidated technical prototype."
            ),
        }
        self.audit.record("paper_learning_execution_complete", payload)
        return payload
