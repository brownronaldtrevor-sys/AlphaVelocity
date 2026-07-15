from __future__ import annotations
from alpha_velocity.portfolio.exposure import OpportunityState, OpportunityType
from alpha_velocity.signals.technical import TechnicalSnapshot

def from_technical(
    symbol: str,
    snapshot: TechnicalSnapshot,
    current_weight_pct: float,
    opportunity_type: OpportunityType = OpportunityType.CONFIRMED_INFLECTION,
    fundamental_strength: float = 50.0,
    macro_alignment: float = 50.0,
    uncertainty: float = 60.0,
    max_weight_pct: float = 20.0,
) -> OpportunityState:
    # Transparent test estimates. Production values require trained models.
    expected_return = max(4.0, min(35.0, 5 + snapshot.composite_score * 0.30))
    probability = max(0.35, min(0.72, 0.35 + snapshot.composite_score / 300))
    expected_days = max(5.0, 28 - snapshot.composite_score / 5)
    downside = max(5.0, min(20.0, snapshot.atr_pct_14d * 100 * 2.5))
    liquidity = max(20.0, min(95.0, 45 + snapshot.volume_ratio_20d * 15))
    execution = max(30.0, min(95.0, 80 - snapshot.atr_pct_14d * 100))

    return OpportunityState(
        opportunity_id=symbol,
        opportunity_type=opportunity_type,
        expected_return_pct=expected_return,
        probability_target_before_stop=probability,
        expected_holding_days=expected_days,
        downside_pct=downside,
        liquidity_score=liquidity,
        technical_readiness=snapshot.composite_score,
        fundamental_strength=fundamental_strength,
        macro_alignment=macro_alignment,
        execution_quality=execution,
        uncertainty=uncertainty,
        correlation_penalty=15.0,
        current_weight_pct=current_weight_pct,
        max_weight_pct=max_weight_pct,
        minimum_trade_weight_pct=2.0,
    )
