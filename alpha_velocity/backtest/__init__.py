from .engine import BacktestEngine
from .strategies import BuyAndHoldBaseline, MovingAverageCrossoverBaseline, ValidationGatedOpportunityBaseline

__all__ = [
    "BacktestEngine",
    "BuyAndHoldBaseline",
    "MovingAverageCrossoverBaseline",
    "ValidationGatedOpportunityBaseline",
]
