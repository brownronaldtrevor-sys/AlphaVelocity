from __future__ import annotations
import json
from pathlib import Path

from alpha_velocity.paper.models import PaperAccount, PaperFill, PaperOrder, PaperPosition

class SimulatedBroker:
    """Deterministic paper broker with configurable slippage and commissions."""

    def __init__(
        self,
        account_path: str,
        starting_cash: float = 100_000.0,
        slippage_bps: float = 8.0,
        commission_per_share: float = 0.005,
        minimum_commission: float = 1.0,
    ) -> None:
        self.account_path = Path(account_path)
        self.account_path.parent.mkdir(parents=True, exist_ok=True)
        self.slippage_bps = slippage_bps
        self.commission_per_share = commission_per_share
        self.minimum_commission = minimum_commission
        self.account = self._load_or_create(starting_cash)

    def _load_or_create(self, starting_cash: float) -> PaperAccount:
        if not self.account_path.exists():
            return PaperAccount(starting_cash, starting_cash, {})
        raw = json.loads(self.account_path.read_text())
        positions = {k: PaperPosition(**v) for k, v in raw.get("positions", {}).items()}
        return PaperAccount(
            cash=float(raw["cash"]),
            starting_equity=float(raw.get("starting_equity", starting_cash)),
            positions=positions,
        )

    def save(self) -> None:
        self.account_path.write_text(json.dumps(self.account.to_dict(), indent=2, sort_keys=True))

    def mark(self, prices: dict[str, float]) -> None:
        for symbol, price in prices.items():
            if symbol in self.account.positions:
                self.account.positions[symbol].last_price = price

    def execute(self, order: PaperOrder) -> PaperFill | None:
        if order.quantity <= 0 or order.reference_price <= 0:
            return None
        direction = 1 if order.action == "BUY" else -1
        slip = order.reference_price * self.slippage_bps / 10_000
        fill_price = order.reference_price + direction * slip
        commission = max(self.minimum_commission, order.quantity * self.commission_per_share)

        if order.action == "BUY":
            affordable = int(max(0, (self.account.cash - commission) // fill_price))
            qty = min(order.quantity, affordable)
            if qty <= 0:
                return None
            commission = max(self.minimum_commission, qty * self.commission_per_share)
            cost = qty * fill_price + commission
            self.account.cash -= cost
            existing = self.account.positions.get(order.symbol)
            if existing:
                total_qty = existing.quantity + qty
                avg = (existing.quantity * existing.average_cost + qty * fill_price) / total_qty
                existing.quantity = total_qty
                existing.average_cost = avg
                existing.last_price = fill_price
            else:
                self.account.positions[order.symbol] = PaperPosition(
                    symbol=order.symbol,
                    quantity=qty,
                    average_cost=fill_price,
                    last_price=fill_price,
                )
        elif order.action == "SELL":
            existing = self.account.positions.get(order.symbol)
            if not existing:
                return None
            qty = min(order.quantity, existing.quantity)
            commission = max(self.minimum_commission, qty * self.commission_per_share)
            self.account.cash += qty * fill_price - commission
            existing.quantity -= qty
            existing.last_price = fill_price
            if existing.quantity == 0:
                del self.account.positions[order.symbol]
        else:
            raise ValueError(f"Unsupported action: {order.action}")

        self.save()
        return PaperFill(
            symbol=order.symbol,
            action=order.action,
            quantity=qty,
            fill_price=fill_price,
            commission=commission,
            slippage=abs(fill_price - order.reference_price),
        )
