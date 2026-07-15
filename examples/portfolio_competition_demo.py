from alpha_velocity.portfolio.competition import build_report
from alpha_velocity.portfolio.exposure import (
    DynamicExposureOptimizer,
    OpportunityState,
    OpportunityType,
)
from alpha_velocity.portfolio.rebalance import make_rebalance_instructions


opportunities = [
    OpportunityState(
        opportunity_id="JELD",
        opportunity_type=OpportunityType.EARLY_INFLECTION,
        expected_return_pct=65,
        probability_target_before_stop=0.48,
        expected_holding_days=55,
        downside_pct=22,
        liquidity_score=58,
        technical_readiness=47,
        fundamental_strength=62,
        macro_alignment=44,
        execution_quality=70,
        uncertainty=72,
        correlation_penalty=25,
        current_weight_pct=35,
        max_weight_pct=25,
        minimum_trade_weight_pct=3,
    ),
    OpportunityState(
        opportunity_id="GNSS",
        opportunity_type=OpportunityType.EARLY_INFLECTION,
        expected_return_pct=35,
        probability_target_before_stop=0.55,
        expected_holding_days=30,
        downside_pct=16,
        liquidity_score=45,
        technical_readiness=70,
        fundamental_strength=52,
        macro_alignment=50,
        execution_quality=60,
        uncertainty=65,
        correlation_penalty=20,
        current_weight_pct=0,
        max_weight_pct=12,
        minimum_trade_weight_pct=2,
    ),
    OpportunityState(
        opportunity_id="COPPER_TREND",
        opportunity_type=OpportunityType.SYSTEMATIC_TREND,
        expected_return_pct=14,
        probability_target_before_stop=0.62,
        expected_holding_days=18,
        downside_pct=6,
        liquidity_score=95,
        technical_readiness=88,
        fundamental_strength=55,
        macro_alignment=80,
        execution_quality=92,
        uncertainty=38,
        correlation_penalty=12,
        current_weight_pct=0,
        max_weight_pct=30,
        minimum_trade_weight_pct=3,
    ),
]

optimizer = DynamicExposureOptimizer(
    reserve_cash_pct=10,
    replacement_margin_pct=8,
    concentration_power=2.2,
)
exposures = optimizer.allocate(opportunities)
report = build_report(opportunities, exposures)

print("Best opportunity:", report.best_opportunity_id)
for exposure in report.exposures:
    print(exposure)
print("Rebalance:")
for instruction in make_rebalance_instructions(exposures):
    print(instruction)
