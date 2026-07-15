from __future__ import annotations

import math

from alpha_velocity.objective.models import (
    CompoundingObjectiveResult,
    ReturnDistributionForecast,
)


class CompoundingMathError(RuntimeError):
    pass


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def fractional_kelly_from_barriers(
    probability_target_before_stop: float,
    target_return: float,
    stop_loss: float,
) -> float:
    """
    Binary barrier approximation.

    target_return and stop_loss are decimal returns, e.g. 0.20 and 0.08.
    """
    if not 0 < probability_target_before_stop < 1:
        raise CompoundingMathError("Probability must be strictly between zero and one.")
    if target_return <= 0 or stop_loss <= 0:
        raise CompoundingMathError("Target and stop magnitudes must be positive.")

    b = target_return / stop_loss
    p = probability_target_before_stop
    q = 1.0 - p
    return max(0.0, (b * p - q) / b)


def expected_log_growth_binary(
    fraction: float,
    probability_target_before_stop: float,
    target_return: float,
    stop_loss: float,
) -> float:
    fraction = _clip(fraction, 0.0, 0.999)
    win_wealth = 1.0 + fraction * target_return
    loss_wealth = 1.0 - fraction * stop_loss
    if win_wealth <= 0 or loss_wealth <= 0:
        return float("-inf")
    p = probability_target_before_stop
    return p * math.log(win_wealth) + (1 - p) * math.log(loss_wealth)


def uncertainty_haircut(
    uncertainty: float,
    model_disagreement: float,
    data_trust_score: float,
    liquidity_score: float,
    event_risk: float,
) -> float:
    """
    Returns a multiplier in [0, 1].

    All inputs except liquidity/data trust are expected on [0, 1].
    data_trust_score and liquidity_score are expected on [0, 100].
    """
    base = 1.0
    base *= 1.0 - _clip(uncertainty, 0.0, 1.0)
    base *= 1.0 - 0.75 * _clip(model_disagreement, 0.0, 1.0)
    base *= _clip(data_trust_score / 100.0, 0.0, 1.0)
    base *= 0.5 + 0.5 * _clip(liquidity_score / 100.0, 0.0, 1.0)
    base *= 1.0 - 0.70 * _clip(event_risk, 0.0, 1.0)
    return _clip(base, 0.0, 1.0)


def cvar_proxy(
    expected_adverse_excursion: float,
    tail_loss_probability: float,
) -> float:
    return abs(expected_adverse_excursion) * (
        1.0 + 2.0 * _clip(tail_loss_probability, 0.0, 1.0)
    )


def _validate_forecast(forecast: ReturnDistributionForecast) -> None:
    probability_fields = {
        "probability_positive": forecast.probability_positive,
        "probability_target_before_stop": forecast.probability_target_before_stop,
        "tail_loss_probability": forecast.tail_loss_probability,
        "uncertainty": forecast.uncertainty,
        "model_disagreement": forecast.model_disagreement,
    }
    for name, value in probability_fields.items():
        if not 0.0 <= value <= 1.0:
            raise CompoundingMathError(f"{name} must be in [0, 1], got {value}.")
    if not 0.0 <= forecast.data_trust_score <= 100.0:
        raise CompoundingMathError("data_trust_score must be in [0, 100].")
    if forecast.expected_time_days <= 0:
        raise CompoundingMathError("expected_time_days must be positive.")
    if forecast.expected_adverse_excursion > 0:
        raise CompoundingMathError(
            "expected_adverse_excursion must be zero or negative decimal return."
        )


def evaluate_compounding_objective(
    forecast: ReturnDistributionForecast,
    target_return: float,
    stop_loss: float,
    liquidity_score: float,
    event_risk: float,
    execution_cost_pct: float,
    maximum_fraction: float = 0.80,
) -> CompoundingObjectiveResult:
    _validate_forecast(forecast)
    if not 0.0 <= liquidity_score <= 100.0:
        raise CompoundingMathError("liquidity_score must be in [0, 100].")
    if not 0.0 <= event_risk <= 1.0:
        raise CompoundingMathError("event_risk must be in [0, 1].")
    if execution_cost_pct < 0:
        raise CompoundingMathError("execution_cost_pct cannot be negative.")
    if not 0.0 < maximum_fraction < 1.0:
        raise CompoundingMathError("maximum_fraction must be strictly between 0 and 1.")
    raw_kelly = fractional_kelly_from_barriers(
        forecast.probability_target_before_stop,
        target_return,
        stop_loss,
    )
    haircut = uncertainty_haircut(
        forecast.uncertainty,
        forecast.model_disagreement,
        forecast.data_trust_score,
        liquidity_score,
        event_risk,
    )
    live_fraction = min(maximum_fraction, raw_kelly * haircut)

    growth = expected_log_growth_binary(
        live_fraction,
        forecast.probability_target_before_stop,
        target_return,
        stop_loss,
    )
    cvar_penalty = cvar_proxy(
        forecast.expected_adverse_excursion,
        forecast.tail_loss_probability,
    )
    execution_penalty = abs(execution_cost_pct)

    time = max(forecast.expected_time_days, 1.0)
    evidence_quality = (
        forecast.data_trust_score / 100.0
        * (1.0 - forecast.uncertainty)
        * (1.0 - forecast.model_disagreement)
    )

    risk_cost_floor = 0.01
    capital_priority = (
        max(growth, 0.0)
        * forecast.probability_target_before_stop
        * max(evidence_quality, 0.0)
    ) / (
        time
        * max(cvar_penalty + execution_penalty, risk_cost_floor)
    )

    return CompoundingObjectiveResult(
        opportunity_id=forecast.opportunity_id,
        expected_log_growth=growth,
        raw_kelly_fraction=raw_kelly,
        uncertainty_haircut=haircut,
        live_kelly_fraction=live_fraction,
        cvar_penalty=cvar_penalty,
        execution_penalty=execution_penalty,
        capital_priority_score=capital_priority,
    )
