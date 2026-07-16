"""Market Intelligence Engine v1.

Daily research pipeline that determines which securities deserve evaluation
and converts qualified securities into canonical Opportunity objects for ranking.
"""

from .models import (
    MarketScanResult,
    QualificationState,
    ScanConfig,
    UniverseConfig,
)
from .scanner import MarketIntelligenceEngine

__all__ = [
    "MarketIntelligenceEngine",
    "MarketScanResult",
    "QualificationState",
    "ScanConfig",
    "UniverseConfig",
]
