from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from alpha_velocity.learning.models import ForecastRecord, OutcomeRecord


class PredictionJournal:
    def __init__(self, folder: str | Path) -> None:
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.forecast_path = self.folder / "forecasts.jsonl"
        self.outcome_path = self.folder / "outcomes.jsonl"

    def append_forecast(self, record: ForecastRecord) -> None:
        with self.forecast_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")

    def append_outcome(self, record: OutcomeRecord) -> None:
        with self.outcome_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")

    def load_forecasts(self) -> list[dict]:
        if not self.forecast_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.forecast_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def load_outcomes(self) -> list[dict]:
        if not self.outcome_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.outcome_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
