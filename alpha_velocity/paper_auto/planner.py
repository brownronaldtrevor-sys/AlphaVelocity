from __future__ import annotations

from alpha_velocity.paper_auto.models import PaperSelection, ProposedPaperOrder


class PaperOrderPlanner:
    def __init__(
        self,
        minimum_order_value: float = 100.0,
        limit_offset_bps: float = 10.0,
    ) -> None:
        self.minimum_order_value = minimum_order_value
        self.limit_offset_bps = limit_offset_bps

    def build_orders(
        self,
        selections: list[PaperSelection],
        account_equity: float,
        current_positions: dict[str, dict],
    ) -> list[ProposedPaperOrder]:
        orders: list[ProposedPaperOrder] = []

        desired_symbols = {s.symbol for s in selections}

        # Exit paper positions no longer selected.
        for symbol, position in current_positions.items():
            if symbol not in desired_symbols and int(position.get("quantity", 0)) > 0:
                orders.append(
                    ProposedPaperOrder(
                        symbol=symbol,
                        action="SELL",
                        quantity=int(position["quantity"]),
                        order_type="MKT",
                        reference_price=float(position.get("market_price", 0.0)),
                        limit_price=None,
                        stop_price=None,
                        target_price=None,
                        reason="No longer selected by the paper portfolio.",
                    )
                )

        for selection in selections:
            desired_value = account_equity * selection.target_weight_pct / 100.0
            existing = current_positions.get(selection.symbol, {})
            current_quantity = int(existing.get("quantity", 0))
            desired_quantity = int(desired_value // selection.reference_price)
            delta = desired_quantity - current_quantity

            if abs(delta) * selection.reference_price < self.minimum_order_value:
                continue

            if delta > 0:
                limit_price = selection.reference_price * (
                    1.0 + self.limit_offset_bps / 10_000.0
                )
                orders.append(
                    ProposedPaperOrder(
                        symbol=selection.symbol,
                        action="BUY",
                        quantity=delta,
                        order_type="LMT",
                        reference_price=selection.reference_price,
                        limit_price=limit_price,
                        stop_price=selection.reference_price * (1.0 - selection.stop_pct),
                        target_price=selection.reference_price * (1.0 + selection.target_pct),
                        reason="Paper selection with predeclared target and stop.",
                    )
                )
            elif delta < 0:
                orders.append(
                    ProposedPaperOrder(
                        symbol=selection.symbol,
                        action="SELL",
                        quantity=abs(delta),
                        order_type="MKT",
                        reference_price=selection.reference_price,
                        limit_price=None,
                        stop_price=None,
                        target_price=None,
                        reason="Reduce to the new paper target weight.",
                    )
                )
        return orders
