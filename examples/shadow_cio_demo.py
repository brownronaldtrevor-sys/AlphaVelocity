from alpha_velocity.shadow.cio import ShadowCIO
from alpha_velocity.shadow.integrator import reconcile_primary_and_shadow
from alpha_velocity.shadow.models import DecisionCandidate

candidates = [
    DecisionCandidate(
        opportunity_id="JELD",
        proposed_action="ADD",
        current_weight_pct=8,
        proposed_weight_pct=24,
        opportunity_score=0.62,
        readiness_score=49,
        expected_return_pct=65,
        expected_holding_days=60,
        downside_pct=24,
        uncertainty=74,
        liquidity_score=58,
        execution_quality=72,
        thesis_strength=78,
        technical_strength=46,
        macro_strength=45,
        evidence_count=7,
        contradiction_count=3,
        model_disagreement=38,
        data_trust_score=76,
        notes=["Early inflection; chart not fully confirmed."],
    ),
    DecisionCandidate(
        opportunity_id="COPPER_TREND",
        proposed_action="ADD",
        current_weight_pct=0,
        proposed_weight_pct=20,
        opportunity_score=0.88,
        readiness_score=86,
        expected_return_pct=15,
        expected_holding_days=18,
        downside_pct=6,
        uncertainty=34,
        liquidity_score=95,
        execution_quality=92,
        thesis_strength=70,
        technical_strength=90,
        macro_strength=82,
        evidence_count=10,
        contradiction_count=0,
        model_disagreement=14,
        data_trust_score=92,
    ),
]

shadow = ShadowCIO()
verdicts = shadow.review(candidates)

for verdict in verdicts:
    print(verdict)

primary = {"JELD": 24.0, "COPPER_TREND": 20.0}
print("\nFinal governed targets:")
for decision in reconcile_primary_and_shadow(primary, verdicts):
    print(decision)
