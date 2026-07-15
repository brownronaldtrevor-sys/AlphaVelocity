from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from alpha_velocity.learning.journal import PredictionJournal
from alpha_velocity.learning.models import ForecastRecord
from alpha_velocity.paper_auto.planner import PaperOrderPlanner
from alpha_velocity.paper_auto.selector import ConservativePaperSelector


class PaperLearningController:
    """
    Converts a completed research report into a paper portfolio proposal.

    Broker submission is deliberately separated. This controller journals forecasts
    first, then emits an order plan. A later explicit paper-broker adapter transmits it.
    """

    def __init__(
        self,
        journal_folder: str | Path = "learning_journal",
        output_folder: str | Path = "paper_plans",
    ) -> None:
        self.journal = PredictionJournal(journal_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.selector = ConservativePaperSelector()
        self.planner = PaperOrderPlanner()

    def build_plan(
        self,
        research_report: dict,
        account_equity: float,
        current_positions: dict[str, dict],
    ) -> dict:
        selections = self.selector.select(research_report["technical_rank"])

        for selection in selections:
            self.journal.append_forecast(
                ForecastRecord(
                    forecast_id=str(uuid.uuid4()),
                    model_id="champion_technical_prototype_v1",
                    symbol=selection.symbol,
                    decision_time=research_report["generated_at"],
                    horizon_days=20,
                    probability_target_before_stop=selection.probability_target_before_stop,
                    expected_return_pct=selection.expected_return_pct,
                    expected_adverse_pct=selection.expected_adverse_pct,
                    target_pct=selection.target_pct * 100.0,
                    stop_pct=selection.stop_pct * 100.0,
                    feature_snapshot={
                        "reference_price": selection.reference_price,
                        "target_weight_pct": selection.target_weight_pct,
                    },
                    rationale=list(selection.rationale),
                )
            )

        orders = self.planner.build_orders(
            selections,
            account_equity,
            current_positions,
        )

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "PAPER_PLAN_ONLY",
            "model_id": "champion_technical_prototype_v1",
            "selections": [asdict(s) for s in selections],
            "proposed_orders": [asdict(o) for o in orders],
            "orders_submitted": 0,
            "warning": (
                "This file is a paper order plan. It does not submit orders by itself. "
                "The forecast probabilities are unvalidated prototype estimates."
            ),
        }
        path = self.output_folder / (
            "paper_plan_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
        )
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        payload["plan_path"] = str(path.resolve())
        return payload
