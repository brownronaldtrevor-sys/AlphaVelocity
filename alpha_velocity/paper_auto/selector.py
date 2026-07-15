from __future__ import annotations

from alpha_velocity.paper_auto.models import PaperSelection


class ConservativePaperSelector:
    """
    Prototype selector for paper-only use.

    It deliberately refuses concentration and only selects names whose research
    snapshots clear minimum trend, volume, liquidity, and risk thresholds.
    """

    def __init__(
        self,
        max_positions: int = 5,
        max_weight_pct: float = 15.0,
        minimum_composite: float = 60.0,
        minimum_price: float = 1.0,
        minimum_volume_ratio: float = 0.45,
    ) -> None:
        self.max_positions = max_positions
        self.max_weight_pct = max_weight_pct
        self.minimum_composite = minimum_composite
        self.minimum_price = minimum_price
        self.minimum_volume_ratio = minimum_volume_ratio

    def select(self, ranked_snapshots: list[dict]) -> list[PaperSelection]:
        eligible = [
            row for row in ranked_snapshots
            if float(row["technical_composite"]) >= self.minimum_composite
            and float(row["close"]) >= self.minimum_price
            and float(row["volume_ratio_20d"]) >= self.minimum_volume_ratio
            and row["state"] not in {"AVOID_OR_EXIT_REVIEW"}
        ][: self.max_positions]

        if not eligible:
            return []

        # Equal risk-budget prototype; no claim of optimality.
        target_weight = min(self.max_weight_pct, 60.0 / len(eligible))
        selections: list[PaperSelection] = []
        for row in eligible:
            atr_pct = float(row["atr_pct_14d"])
            target_pct = max(0.08, min(0.20, atr_pct * 3.0))
            stop_pct = max(0.04, min(0.10, atr_pct * 1.5))
            probability = max(
                0.50,
                min(0.68, 0.45 + float(row["technical_composite"]) / 300.0),
            )
            expected_return = (
                probability * target_pct
                - (1.0 - probability) * stop_pct
            ) * 100.0

            selections.append(
                PaperSelection(
                    symbol=row["symbol"],
                    rank=int(row["rank"]),
                    target_weight_pct=target_weight,
                    reference_price=float(row["close"]),
                    target_pct=target_pct,
                    stop_pct=stop_pct,
                    probability_target_before_stop=probability,
                    expected_return_pct=expected_return,
                    expected_adverse_pct=-stop_pct * 100.0,
                    rationale=(
                        f"technical composite {float(row['technical_composite']):.1f}",
                        f"trend score {float(row['trend_score']):.1f}",
                        f"volume ratio {float(row['volume_ratio_20d']):.2f}",
                        "paper-only prototype selection",
                    ),
                )
            )
        return selections
