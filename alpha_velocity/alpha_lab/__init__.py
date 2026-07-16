"""Alpha Lab - Strategy platform for research and paper trading.

ACTIVE STRATEGIES FOR EQUITY WORKFLOW:
- Swing Repricing: Equities with weekly structure, daily breakout, catalysts

EXPERIMENTAL STRATEGIES (disabled, zero influence):
- Turtle Trend: Moved to alpha_velocity/experimental_strategies/turtle_trend/
  (Futures-focused, requires separate infrastructure)
"""

from alpha_velocity.alpha_lab.models import (
    CandidateState,
    StrategyCandidate,
    StrategyContext,
    StrategyEvidence,
    StrategyRunResult,
    StrategyScorecard,
    StrategyState,
    StrategyValidationStatus,
)
from alpha_velocity.alpha_lab.protocol import StrategyProtocol
from alpha_velocity.alpha_lab.engine import AlphaLabEngine
from alpha_velocity.alpha_lab.strategies_swing_repricing import SwingRepricingStrategy
from alpha_velocity.alpha_lab.sample_data import (
    generate_sample_alpha_lab_data,
    generate_sample_csv_data,
)

__all__ = [
    "CandidateState",
    "StrategyCandidate",
    "StrategyContext",
    "StrategyEvidence",
    "StrategyProtocol",
    "StrategyRunResult",
    "StrategyScorecard",
    "StrategyState",
    "StrategyValidationStatus",
    "AlphaLabEngine",
    "SwingRepricingStrategy",
    "generate_sample_alpha_lab_data",
    "generate_sample_csv_data",
]
