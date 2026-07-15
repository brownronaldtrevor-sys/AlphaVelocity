from datetime import datetime

from alpha_velocity.objective.compounding import evaluate_compounding_objective
from alpha_velocity.objective.models import ReturnDistributionForecast
from alpha_velocity.portfolio_math.allocator import (
    CvarAwareAllocator,
    PortfolioCandidate,
)


forecast = ReturnDistributionForecast(
    opportunity_id="DEMO",
    timestamp=datetime(2026, 1, 1),
    probability_positive=0.62,
    probability_target_before_stop=0.58,
    expected_return=0.18,
    median_return=0.10,
    expected_favorable_excursion=0.24,
    expected_adverse_excursion=-0.08,
    tail_loss_probability=0.10,
    expected_time_days=15,
    uncertainty=0.25,
    data_trust_score=88,
    model_disagreement=0.12,
    source_weights={"technical": 0.35, "fundamental": 0.35, "sentiment": 0.30},
)

objective = evaluate_compounding_objective(
    forecast=forecast,
    target_return=0.20,
    stop_loss=0.08,
    liquidity_score=85,
    event_risk=0.10,
    execution_cost_pct=0.003,
)

candidate = PortfolioCandidate(
    opportunity_id="DEMO",
    forecast=forecast,
    objective=objective,
    maximum_weight=0.40,
    current_weight=0.10,
    liquidity_score=85,
    correlation_cluster="industrials",
    execution_cost_pct=0.003,
)

print(objective)
print(CvarAwareAllocator().allocate([candidate]))
