from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaperSelection:
    symbol: str
    rank: int
    target_weight_pct: float
    reference_price: float
    target_pct: float
    stop_pct: float
    probability_target_before_stop: float
    expected_return_pct: float
    expected_adverse_pct: float
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class ProposedPaperOrder:
    symbol: str
    action: str
    quantity: int
    order_type: str
    reference_price: float
    limit_price: float | None
    stop_price: float | None
    target_price: float | None
    reason: str
