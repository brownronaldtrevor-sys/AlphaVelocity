from datetime import datetime

from alpha_velocity.objective.compounding import (
    evaluate_compounding_objective,
    fractional_kelly_from_barriers,
)
from alpha_velocity.objective.models import ReturnDistributionForecast
from alpha_velocity.shadow_math.intervention import (
    GraduatedShadowCIO,
    InterventionLevel,
)


def forecast(**overrides):
    values = dict(
        opportunity_id="X",
        timestamp=datetime(2026, 1, 1),
        probability_positive=.6,
        probability_target_before_stop=.6,
        expected_return=.2,
        median_return=.1,
        expected_favorable_excursion=.25,
        expected_adverse_excursion=-.08,
        tail_loss_probability=.1,
        expected_time_days=10,
        uncertainty=.2,
        data_trust_score=90,
        model_disagreement=.1,
        source_weights={"technical": .5, "sentiment": .5},
    )
    values.update(overrides)
    return ReturnDistributionForecast(**values)


def test_kelly_positive_for_favorable_barrier():
    assert fractional_kelly_from_barriers(.6, .2, .08) > 0


def test_uncertainty_reduces_live_fraction():
    low = evaluate_compounding_objective(
        forecast(), .2, .08, 90, .1, .002
    )
    high = evaluate_compounding_objective(
        forecast(uncertainty=.8), .2, .08, 90, .1, .002
    )
    assert high.live_kelly_fraction < low.live_kelly_fraction


def test_shadow_silent_when_clean():
    result = GraduatedShadowCIO().evaluate(
        "X", .2, 95, .05, .03, False, False, 0
    )
    assert result.level == InterventionLevel.SILENT


def test_shadow_blocks_control_failure():
    result = GraduatedShadowCIO().evaluate(
        "X", .2, 95, .05, .03, True, False, 0
    )
    assert result.level == InterventionLevel.BLOCK
