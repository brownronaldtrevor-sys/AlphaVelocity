from __future__ import annotations

from alpha_velocity.shadow.models import DecisionGrade


class ShadowDecisionGrader:
    """Grades decision quality separately from whether the trade happened to win."""

    def grade(
        self,
        decision_id: str,
        opportunity_id: str,
        realized_return_pct: float,
        benchmark_return_pct: float,
        best_alternative_return_pct: float,
        expected_return_pct: float,
        chosen_weight_pct: float,
        ideal_hindsight_weight_pct: float,
        execution_slippage_pct: float,
        thesis_outcome_score: float,
    ) -> DecisionGrade:
        timing_quality = max(
            0.0,
            min(100.0, 50 + (realized_return_pct - benchmark_return_pct) * 2.5),
        )
        sizing_error = abs(chosen_weight_pct - ideal_hindsight_weight_pct)
        sizing_quality = max(0.0, 100.0 - sizing_error * 2.0)
        opportunity_cost = best_alternative_return_pct - realized_return_pct
        thesis_accuracy = max(0.0, min(100.0, thesis_outcome_score))
        execution_quality = max(0.0, min(100.0, 100 - abs(execution_slippage_pct) * 20))

        forecast_error = abs(expected_return_pct - realized_return_pct)
        calibration_quality = max(0.0, 100 - forecast_error * 2.0)

        overall = (
            0.22 * timing_quality
            + 0.20 * sizing_quality
            + 0.18 * thesis_accuracy
            + 0.15 * execution_quality
            + 0.15 * calibration_quality
            + 0.10 * max(0.0, 100 - max(opportunity_cost, 0) * 3)
        )

        lessons = []
        if opportunity_cost > 5:
            lessons.append("Capital would have compounded faster in the best available alternative.")
        if sizing_quality < 60:
            lessons.append("Position size was materially different from the hindsight-efficient size.")
        if execution_quality < 75:
            lessons.append("Execution quality reduced realized returns.")
        if calibration_quality < 60:
            lessons.append("Expected return estimate was poorly calibrated.")
        if thesis_accuracy < 60:
            lessons.append("Core thesis evidence did not develop as expected.")
        if not lessons:
            lessons.append("Decision quality was broadly consistent with the evidence available.")

        return DecisionGrade(
            decision_id=decision_id,
            opportunity_id=opportunity_id,
            realized_return_pct=realized_return_pct,
            benchmark_return_pct=benchmark_return_pct,
            best_alternative_return_pct=best_alternative_return_pct,
            timing_quality=round(timing_quality, 2),
            sizing_quality=round(sizing_quality, 2),
            opportunity_cost_pct=round(opportunity_cost, 2),
            thesis_accuracy=round(thesis_accuracy, 2),
            execution_quality=round(execution_quality, 2),
            overall_grade=round(overall, 2),
            lessons=lessons,
        )
