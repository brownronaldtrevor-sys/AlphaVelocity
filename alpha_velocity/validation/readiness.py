from __future__ import annotations

from dataclasses import dataclass


class LiveReadinessError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelReadiness:
    model_id: str
    point_in_time_validated: bool
    walk_forward_validated: bool
    execution_validated: bool
    calibration_validated: bool
    paper_observations: int
    known_heuristic: bool = False

    def assert_live_ready(self, minimum_paper_observations: int = 100) -> None:
        failures: list[str] = []
        if self.known_heuristic:
            failures.append("model is explicitly marked heuristic")
        if not self.point_in_time_validated:
            failures.append("point-in-time validation missing")
        if not self.walk_forward_validated:
            failures.append("walk-forward validation missing")
        if not self.execution_validated:
            failures.append("execution validation missing")
        if not self.calibration_validated:
            failures.append("probability calibration missing")
        if self.paper_observations < minimum_paper_observations:
            failures.append(
                f"only {self.paper_observations} paper observations; "
                f"{minimum_paper_observations} required"
            )
        if failures:
            raise LiveReadinessError(
                f"Model {self.model_id!r} is not live-ready: " + "; ".join(failures)
            )
