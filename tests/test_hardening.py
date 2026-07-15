from datetime import datetime, timezone

import pytest

from alpha_velocity.models import (
    AssetClass,
    ConvictionTier,
    Instrument,
    Side,
    SignalProposal,
)
from alpha_velocity.objective.compounding import (
    CompoundingMathError,
    evaluate_compounding_objective,
)
from alpha_velocity.objective.models import ReturnDistributionForecast
from alpha_velocity.validation.readiness import LiveReadinessError, ModelReadiness


def test_dataclass_timestamp_is_not_shared():
    kwargs = dict(
        strategy_id="x",
        instrument=Instrument("X", AssetClass.STOCK),
        side=Side.BUY,
        entry_price=10,
        stop_price=9,
        target_price=12,
        probability_target_before_stop=.6,
        expected_holding_days=10,
        expected_return_pct=20,
        conviction_tier=ConvictionTier.NORMAL,
        thesis="x",
        model_version="1",
    )
    a = SignalProposal(**kwargs)
    b = SignalProposal(**kwargs)
    assert a.generated_at is not b.generated_at


def test_invalid_probability_is_rejected():
    f = ReturnDistributionForecast(
        opportunity_id="X",
        timestamp=datetime.now(timezone.utc),
        probability_positive=1.2,
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
        source_weights={"x": 1.0},
    )
    with pytest.raises(CompoundingMathError):
        evaluate_compounding_objective(f, .2, .08, 90, .1, .002)


def test_heuristic_model_is_never_live_ready():
    readiness = ModelReadiness("H", True, True, True, True, 1000, known_heuristic=True)
    with pytest.raises(LiveReadinessError):
        readiness.assert_live_ready()
