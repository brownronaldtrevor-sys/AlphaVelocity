from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RebalanceInstruction:
    opportunity_id: str
    action: str
    current_weight_pct: float
    target_weight_pct: float
    change_weight_pct: float


def make_rebalance_instructions(exposures) -> list[RebalanceInstruction]:
    instructions = []
    for e in exposures:
        if e.opportunity_id == "CASH":
            continue
        change = e.target_weight_pct - e.current_weight_pct
        if abs(change) < 0.5:
            continue
        instructions.append(
            RebalanceInstruction(
                opportunity_id=e.opportunity_id,
                action=e.action,
                current_weight_pct=e.current_weight_pct,
                target_weight_pct=e.target_weight_pct,
                change_weight_pct=round(change, 4),
            )
        )
    return instructions
