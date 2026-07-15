from alpha_velocity.shadow.cio import ShadowCIO
from alpha_velocity.shadow.models import DecisionCandidate


def candidate(**overrides):
    values = dict(
        opportunity_id="TEST",
        proposed_action="ADD",
        current_weight_pct=0,
        proposed_weight_pct=20,
        opportunity_score=0.8,
        readiness_score=80,
        expected_return_pct=25,
        expected_holding_days=12,
        downside_pct=8,
        uncertainty=30,
        liquidity_score=90,
        execution_quality=90,
        thesis_strength=80,
        technical_strength=85,
        macro_strength=75,
        evidence_count=10,
        contradiction_count=0,
        model_disagreement=10,
        data_trust_score=90,
        notes=[],
    )
    values.update(overrides)
    return DecisionCandidate(**values)


def test_strong_candidate_can_keep_proposed_weight():
    verdict = ShadowCIO().review([candidate()])[0]
    assert verdict.shadow_target_weight_pct == 20
    assert verdict.verdict == "ADD"


def test_unconfirmed_candidate_is_capped():
    verdict = ShadowCIO().review([
        candidate(readiness_score=45, proposed_weight_pct=30, uncertainty=70)
    ])[0]
    assert verdict.shadow_target_weight_pct <= 8


def test_low_data_trust_is_rejected():
    verdict = ShadowCIO().review([candidate(data_trust_score=40)])[0]
    assert verdict.shadow_target_weight_pct == 0
    assert verdict.verdict == "REJECT_OR_EXIT"
