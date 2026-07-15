from alpha_velocity.portfolio.exposure import (
    DynamicExposureOptimizer,
    OpportunityState,
    OpportunityType,
)


def make_opportunity(
    opportunity_id,
    score_inputs=(20, 0.60, 10, 8, 80, 80, 70, 70, 80, 40, 10),
    current=0,
    max_weight=50,
):
    (
        expected_return, probability, days, downside, liquidity,
        technical, fundamental, macro, execution, uncertainty, correlation
    ) = score_inputs
    return OpportunityState(
        opportunity_id=opportunity_id,
        opportunity_type=OpportunityType.CONFIRMED_INFLECTION,
        expected_return_pct=expected_return,
        probability_target_before_stop=probability,
        expected_holding_days=days,
        downside_pct=downside,
        liquidity_score=liquidity,
        technical_readiness=technical,
        fundamental_strength=fundamental,
        macro_alignment=macro,
        execution_quality=execution,
        uncertainty=uncertainty,
        correlation_penalty=correlation,
        current_weight_pct=current,
        max_weight_pct=max_weight,
    )


def test_best_opportunity_receives_more_weight():
    best = make_opportunity(
        "BEST",
        score_inputs=(30, .70, 8, 7, 90, 90, 80, 80, 90, 30, 8),
    )
    weaker = make_opportunity(
        "WEAKER",
        score_inputs=(12, .52, 18, 9, 70, 60, 60, 55, 70, 55, 20),
    )
    optimizer = DynamicExposureOptimizer(reserve_cash_pct=10)
    result = optimizer.allocate([best, weaker])
    weights = {x.opportunity_id: x.target_weight_pct for x in result}
    assert weights["BEST"] > weights["WEAKER"]
    assert round(sum(weights.values()), 6) == 100.0


def test_max_weight_is_respected():
    best = make_opportunity(
        "CAPPED",
        score_inputs=(50, .80, 5, 5, 95, 95, 95, 95, 95, 20, 5),
        max_weight=20,
    )
    other = make_opportunity("OTHER", max_weight=80)
    optimizer = DynamicExposureOptimizer(reserve_cash_pct=0)
    result = optimizer.allocate([best, other])
    weights = {x.opportunity_id: x.target_weight_pct for x in result}
    assert weights["CAPPED"] <= 20
