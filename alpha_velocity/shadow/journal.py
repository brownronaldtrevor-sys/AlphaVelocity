from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from alpha_velocity.shadow.models import CounterfactualRecord, DecisionGrade


class ShadowDecisionJournal:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_decision(self, record: CounterfactualRecord) -> None:
        self._append({"type": "decision", **asdict(record)})

    def append_grade(self, grade: DecisionGrade) -> None:
        self._append({"type": "grade", **asdict(grade)})

    def _append(self, payload: dict) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
