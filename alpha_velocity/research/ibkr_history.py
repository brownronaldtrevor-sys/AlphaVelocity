from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from alpha_velocity.market.bars import Bar


class HistoricalDataMixin:
    """IBKR callback/request support for finalized historical bars.

    This mixin intentionally does not expose any order method. Requests are serialized
    by the research runner to reduce pacing and callback-completion ambiguity.
    """

    def _init_historical_state(self) -> None:
        self._historical_lock = threading.Lock()
        self._historical_events: dict[int, threading.Event] = {}
        self._historical_bars: dict[int, list[Bar]] = {}
        self._historical_errors: dict[int, str] = {}

    def historicalData(self, reqId: int, bar: Any) -> None:  # noqa: N802
        raw_date = str(bar.date)
        # Daily bars normally arrive as YYYYMMDD. Intraday support can be added later
        # with explicit exchange-time-zone handling.
        timestamp = datetime.strptime(raw_date, "%Y%m%d")
        with self._historical_lock:
            self._historical_bars.setdefault(reqId, []).append(
                Bar(
                    timestamp=timestamp,
                    open=float(bar.open),
                    high=float(bar.high),
                    low=float(bar.low),
                    close=float(bar.close),
                    volume=float(bar.volume),
                )
            )

    def historicalDataEnd(self, reqId: int, start: str, end: str) -> None:  # noqa: N802
        event = self._historical_events.get(reqId)
        if event:
            event.set()
        self.audit.record(
            "ibkr_historical_data_end",
            {"request_id": reqId, "start": start, "end": end},
        )

    def request_daily_bars(
        self,
        req_id: int,
        contract: Any,
        duration: str = "1 Y",
        timeout_seconds: int = 30,
    ) -> list[Bar]:
        if req_id in self._historical_events:
            raise ValueError(f"Historical request id {req_id} was already used.")
        event = threading.Event()
        self._historical_events[req_id] = event
        self._historical_bars[req_id] = []
        self.client.reqHistoricalData(
            req_id,
            contract,
            "",
            duration,
            "1 day",
            "TRADES",
            1,
            1,
            False,
            [],
        )
        if not event.wait(timeout_seconds):
            self.client.cancelHistoricalData(req_id)
            raise TimeoutError(
                f"IBKR historical request {req_id} did not finish within "
                f"{timeout_seconds}s."
            )
        bars = sorted(self._historical_bars.get(req_id, []), key=lambda b: b.timestamp)
        if len(bars) < 60:
            raise RuntimeError(
                f"IBKR returned only {len(bars)} finalized daily bars; at least 60 required."
            )
        return bars
