from __future__ import annotations

from datetime import datetime
from typing import Any


class InMemoryProviderAdapter:
    def __init__(
        self,
        *,
        securities: list[dict[str, Any]] | None = None,
        corporate_actions: list[dict[str, Any]] | None = None,
        bars: list[dict[str, Any]] | None = None,
        ticker_histories: list[dict[str, Any]] | None = None,
    ) -> None:
        self._securities = list(securities or [])
        self._corporate_actions = list(corporate_actions or [])
        self._bars = list(bars or [])
        self._ticker_histories = list(ticker_histories or [])

    def list_securities(self, symbols: list[str] | None = None) -> list[dict[str, Any]]:
        if not symbols:
            return list(self._securities)
        wanted = {symbol.upper() for symbol in symbols}
        return [entry for entry in self._securities if str(entry.get("ticker", "")).upper() in wanted]

    def list_corporate_actions(self, symbols: list[str] | None = None) -> list[dict[str, Any]]:
        symbol_set = {symbol.upper() for symbol in symbols or []}
        items = list(self._corporate_actions)
        if not symbol_set:
            return items
        return [entry for entry in items if str(entry.get("security_id", "")).upper() in symbol_set or str(entry.get("from_ticker", "")).upper() in symbol_set or str(entry.get("to_ticker", "")).upper() in symbol_set]

    def list_bars(self, symbols: list[str] | None = None) -> list[dict[str, Any]]:
        symbol_set = {symbol.upper() for symbol in symbols or []}
        items = list(self._bars)
        if not symbol_set:
            return items
        security_ids = {
            str(entry.get("security_id", "")).upper(): str(entry.get("ticker", "")).upper()
            for entry in self._securities
            if entry.get("security_id")
        }
        return [
            entry
            for entry in items
            if str(entry.get("security_id", "")).upper() in symbol_set
            or security_ids.get(str(entry.get("security_id", "")).upper(), "") in symbol_set
        ]

    def list_ticker_histories(self, symbols: list[str] | None = None) -> list[dict[str, Any]]:
        symbol_set = {symbol.upper() for symbol in symbols or []}
        items = list(self._ticker_histories)
        if not symbol_set:
            return items
        return [
            entry
            for entry in items
            if str(entry.get("security_id", "")).upper() in symbol_set or str(entry.get("ticker", "")).upper() in symbol_set
        ]
