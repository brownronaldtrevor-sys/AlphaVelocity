from __future__ import annotations

import os
import threading
from decimal import Decimal
from typing import Any

from alpha_velocity.audit import AuditLogger
from alpha_velocity.config import AppConfig
from alpha_velocity.models import ApprovedOrderPlan, Side
from alpha_velocity.broker.contracts import to_ib_contract
from alpha_velocity.research.ibkr_history import HistoricalDataMixin

try:
    from ibapi.client import EClient
    from ibapi.order import Order
    from ibapi.wrapper import EWrapper
except ImportError:
    EClient = None  # type: ignore[assignment]
    EWrapper = object  # type: ignore[assignment]
    Order = None  # type: ignore[assignment]


class IBKRApp(HistoricalDataMixin, EWrapper):
    def __init__(self, config: AppConfig, audit: AuditLogger) -> None:
        if EClient is None:
            raise RuntimeError(
                "Official IBKR TWS Python API is not installed. "
                "Install the API package distributed by Interactive Brokers."
            )
        EWrapper.__init__(self)
        self.client = EClient(self)
        self.config = config
        self.audit = audit
        self.next_order_id: int | None = None
        self.connected_event = threading.Event()
        self.accounts: list[str] = []
        self.account_values: dict[str, float] = {}
        self.positions: dict[str, dict[str, Any]] = {}
        self.open_order_ids: set[int] = set()
        self.open_order_symbols: set[str] = set()
        self.account_summary_complete = threading.Event()
        self.positions_complete = threading.Event()
        self.open_orders_complete = threading.Event()
        self._init_historical_state()

    def connect_and_start(self) -> None:
        self.client.connect(
            self.config.broker.host,
            self.config.broker.port,
            self.config.broker.client_id,
        )
        thread = threading.Thread(target=self.client.run, daemon=True)
        thread.start()
        if not self.connected_event.wait(self.config.broker.connect_timeout_seconds):
            raise TimeoutError("IBKR connection did not deliver nextValidId in time.")
        self.client.reqManagedAccts()
        self.client.reqPositions()
        self.client.reqOpenOrders()
        self.client.reqAccountSummary(
            9001,
            "All",
            "NetLiquidation,AvailableFunds,GrossPositionValue",
        )
        timeout = self.config.broker.connect_timeout_seconds
        required = [
            (self.account_summary_complete, "account summary"),
            (self.positions_complete, "positions"),
        ]
        for event, name in required:
            if not event.wait(timeout):
                raise TimeoutError(f"IBKR did not complete {name} within {timeout}s.")

        # Open-order reconciliation is useful, but some TWS/API combinations do not
        # deliver openOrderEnd promptly when there are no API-visible orders. Do not
        # misclassify an otherwise healthy read-only connection as a total failure.
        # Production trading must run a separate reconciliation gate before orders.
        if not self.open_orders_complete.wait(min(timeout, 5)):
            self.audit.record(
                "ibkr_open_orders_incomplete_warning",
                {
                    "message": (
                        "TWS did not deliver openOrderEnd during the safe connection test. "
                        "Account and position connectivity may still be healthy. "
                        "Order transmission remains disabled until reconciliation passes."
                    )
                },
            )

    def disconnect(self) -> None:
        self.client.disconnect()

    def nextValidId(self, orderId: int) -> None:  # noqa: N802
        self.next_order_id = orderId
        self.connected_event.set()
        self.audit.record("ibkr_next_valid_id", {"order_id": orderId})

    def managedAccounts(self, accountsList: str) -> None:  # noqa: N802
        self.accounts = [a for a in accountsList.split(",") if a]
        self.audit.record("ibkr_managed_accounts", {"accounts": self.accounts})

    def accountSummary(  # noqa: N802
        self, reqId: int, account: str, tag: str, value: str, currency: str
    ) -> None:
        try:
            self.account_values[tag] = float(value)
        except ValueError:
            pass
        self.audit.record(
            "ibkr_account_summary",
            {"account": account, "tag": tag, "value": value, "currency": currency},
        )


    def accountSummaryEnd(self, reqId: int) -> None:  # noqa: N802
        self.account_summary_complete.set()
        self.audit.record("ibkr_account_summary_end", {"request_id": reqId})

    def positionEnd(self) -> None:  # noqa: N802
        self.positions_complete.set()
        self.audit.record("ibkr_position_end", {})

    def openOrderEnd(self) -> None:  # noqa: N802
        self.open_orders_complete.set()
        self.audit.record("ibkr_open_order_end", {})

    def require_account_snapshot(self) -> dict[str, float]:
        required = ("NetLiquidation", "AvailableFunds", "GrossPositionValue")
        missing = [key for key in required if key not in self.account_values]
        if missing:
            raise RuntimeError(
                "Incomplete IBKR account snapshot; missing: " + ", ".join(missing)
            )
        if self.account_values["NetLiquidation"] <= 0:
            raise RuntimeError("IBKR reported non-positive NetLiquidation.")
        return {key: self.account_values[key] for key in required}

    def position(self, account, contract, position, avgCost) -> None:
        self.positions[contract.symbol] = {
            "account": account,
            "quantity": float(position),
            "avg_cost": float(avgCost),
            "sec_type": contract.secType,
        }
        self.audit.record("ibkr_position", self.positions[contract.symbol])

    def openOrder(self, orderId, contract, order, orderState) -> None:  # noqa: N802
        self.open_order_ids.add(orderId)
        self.open_order_symbols.add(contract.symbol)
        self.audit.record(
            "ibkr_open_order",
            {
                "order_id": orderId,
                "symbol": contract.symbol,
                "action": order.action,
                "type": order.orderType,
                "quantity": str(order.totalQuantity),
                "status": orderState.status,
            },
        )

    def orderStatus(  # noqa: N802
        self, orderId, status, filled, remaining, avgFillPrice,
        permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice
    ) -> None:
        if status in {"Filled", "Cancelled", "ApiCancelled", "Inactive"}:
            self.open_order_ids.discard(orderId)
        self.audit.record(
            "ibkr_order_status",
            {
                "order_id": orderId,
                "status": status,
                "filled": str(filled),
                "remaining": str(remaining),
                "avg_fill_price": avgFillPrice,
            },
        )

    def execDetails(self, reqId, contract, execution) -> None:  # noqa: N802
        self.audit.record(
            "ibkr_execution",
            {
                "symbol": contract.symbol,
                "exec_id": execution.execId,
                "side": execution.side,
                "shares": str(execution.shares),
                "price": execution.price,
                "order_id": execution.orderId,
            },
        )

    def error(self, reqId, *args) -> None:
        """Handle both pre-10.33 and 10.33+ IBKR error callback signatures.

        Older API versions call:
            error(reqId, errorCode, errorString, advancedOrderRejectJson)

        API 10.33+ calls:
            error(reqId, errorTime, errorCode, errorString, advancedOrderRejectJson)

        IBKR also routes informational connectivity notices through this callback.
        """
        error_time = None
        advanced_reject = ""

        if len(args) == 4:
            error_time, error_code, error_string, advanced_reject = args
        elif len(args) == 3:
            error_code, error_string, advanced_reject = args
        elif len(args) == 2:
            error_code, error_string = args
        elif len(args) == 1:
            error_code = None
            error_string = str(args[0])
        else:
            error_code = None
            error_string = f"Unexpected IBKR error callback arguments: {args!r}"

        if isinstance(reqId, int) and reqId in getattr(self, "_historical_events", {}):
            if error_code not in {2104, 2106, 2158}:
                self._historical_errors[reqId] = str(error_string)

        self.audit.record(
            "ibkr_message",
            {
                "request_id": reqId,
                "error_time": error_time,
                "code": error_code,
                "message": error_string,
                "advanced_reject": advanced_reject,
            },
        )

    def _validate_live_authority(self) -> None:
        if self.config.broker.mode == "LIVE":
            ack = os.getenv("ALPHA_VELOCITY_LIVE_ACK", "")
            if ack != "I_ACCEPT_LIVE_TRADING_RISK":
                raise PermissionError(
                    "Live trading blocked. Required acknowledgement environment "
                    "variable is absent."
                )
            if self.config.execution.dry_run:
                raise PermissionError("Live mode is incompatible with dry_run=true.")

    def _next_id(self) -> int:
        if self.next_order_id is None:
            raise RuntimeError("No valid IBKR order ID is available.")
        value = self.next_order_id
        self.next_order_id += 1
        return value

    def place_bracket(self, plan: ApprovedOrderPlan) -> list[int]:
        if plan.proposal.strategy_id == "DEMO_WIRING_TEST":
            raise PermissionError("Synthetic demonstration strategies may never be transmitted.")
        self._validate_live_authority()
        self.audit.record("approved_order_plan", plan)

        if self.config.execution.dry_run:
            self.audit.record("dry_run_order_not_transmitted", plan)
            return []

        proposal = plan.proposal
        contract = to_ib_contract(proposal.instrument)
        is_buy = proposal.side == Side.BUY
        exit_action = "SELL" if is_buy else "BUY"
        parent_id = self._next_id()

        parent = Order()
        parent.orderId = parent_id
        parent.action = proposal.side.value
        parent.orderType = "LMT"
        parent.totalQuantity = Decimal(plan.quantity)
        parent.lmtPrice = proposal.entry_price
        parent.transmit = False
        parent.outsideRth = self.config.execution.outside_rth
        parent.orderRef = (
            f"{self.config.execution.order_ref_prefix}:"
            f"{proposal.strategy_id}:{proposal.model_version}"
        )

        target = Order()
        target.orderId = self._next_id()
        target.action = exit_action
        target.orderType = "LMT"
        target.totalQuantity = Decimal(plan.quantity)
        target.lmtPrice = proposal.target_price
        target.parentId = parent_id
        target.transmit = False
        target.outsideRth = self.config.execution.outside_rth
        target.orderRef = parent.orderRef

        stop = Order()
        stop.orderId = self._next_id()
        stop.action = exit_action
        stop.orderType = "STP"
        stop.totalQuantity = Decimal(plan.quantity)
        stop.auxPrice = proposal.stop_price
        stop.parentId = parent_id
        stop.transmit = True
        stop.outsideRth = self.config.execution.outside_rth
        stop.orderRef = parent.orderRef

        self.client.placeOrder(parent.orderId, contract, parent)
        self.client.placeOrder(target.orderId, contract, target)
        self.client.placeOrder(stop.orderId, contract, stop)

        ids = [parent.orderId, target.orderId, stop.orderId]
        self.audit.record("bracket_transmitted", {"order_ids": ids, "plan": plan})
        return ids

    def global_cancel(self) -> None:
        self.client.reqGlobalCancel()
        self.audit.record("global_cancel_requested", {})
