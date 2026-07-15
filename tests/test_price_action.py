from datetime import datetime, timedelta

from alpha_velocity.market.bars import Bar
from alpha_velocity.price_action.features import compute_price_action_snapshot
from alpha_velocity.price_action.integration import blend_price_action_evidence
from alpha_velocity.price_action.validation import validate_incremental_price_action


def bars(count=100):
    output = []
    price = 10.0
    start = datetime(2020, 1, 1)
    for i in range(count):
        price *= 1.002
        output.append(
            Bar(
                start + timedelta(days=i),
                price * 0.995,
                price * 1.01,
                price * 0.99,
                price,
                100_000 + i * 100,
            )
        )
    return output


def test_price_action_features_are_bounded_and_have_invalidation():
    snapshot = compute_price_action_snapshot(bars())
    assert 0 <= snapshot.evidence_score <= 100
    assert 0 <= snapshot.close_location_1d <= 1
    assert snapshot.invalidation_price > 0


def test_unvalidated_price_action_cannot_change_baseline():
    result = blend_price_action_evidence(70, 100, approved_weight=0)
    assert result.blended_score == 70
    assert result.price_action_weight == 0


def test_weight_is_hard_capped():
    result = blend_price_action_evidence(50, 100, approved_weight=0.9)
    assert result.price_action_weight == 0.20
    assert result.blended_score == 60


def test_validation_rejects_small_sample_even_when_metrics_look_good():
    result = validate_incremental_price_action(
        feature_set_id="pa-v1",
        baseline_probabilities=[0.5] * 100,
        candidate_probabilities=[0.7] * 100,
        outcomes=[1] * 100,
        baseline_returns=[0.0] * 100,
        candidate_returns=[0.01] * 100,
        regime_passes=[True] * 100,
    )
    assert not result.approved
    assert result.approved_weight == 0


def test_validation_can_approve_incremental_value():
    n = 500
    result = validate_incremental_price_action(
        feature_set_id="pa-v1",
        baseline_probabilities=[0.5] * n,
        candidate_probabilities=[0.7] * n,
        outcomes=[1] * n,
        baseline_returns=[0.0] * n,
        candidate_returns=[0.01] * n,
        regime_passes=[True] * n,
    )
    assert result.approved
    assert 0 < result.approved_weight <= 0.20
