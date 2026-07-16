from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .models import BarRecord, CanonicalEvent, CorporateAction, EventType, SecurityRecord, TickerHistoryEntry
from .providers import InMemoryProviderAdapter
from .sqlite_store import SQLiteHistoricalWarehouse


class WarehouseIngestionEngine:
    def __init__(self, *, warehouse: SQLiteHistoricalWarehouse, provider: InMemoryProviderAdapter) -> None:
        self.warehouse = warehouse
        self.provider = provider

    def ingest(self, *, run_id: str, symbols: list[str] | None = None, git_commit: str | None = None) -> dict[str, Any]:
        manifest: dict[str, Any] = {
            "run_id": run_id,
            "symbols": sorted(symbols or []),
            "git_commit": git_commit or "",
            "inserted": 0,
            "rejected": 0,
            "failed": 0,
            "hash": "",
            "quality_summary": {"valid": 0, "rejected": 0, "failures": 0},
        }
        securities = self.provider.list_securities(symbols)
        for security_payload in securities:
            security_id = str(security_payload.get("security_id") or security_payload.get("ticker") or "")
            if not security_id:
                manifest["rejected"] += 1
                self.warehouse.insert_failure(
                    run_id=run_id,
                    security_id=None,
                    reason="missing-security-id",
                    payload=security_payload,
                )
                continue
            existing = self.warehouse.get_security(security_id)
            if existing is not None:
                manifest["rejected"] += 1
                self.warehouse.insert_failure(
                    run_id=run_id,
                    security_id=security_id,
                    reason="duplicate-security",
                    payload=security_payload,
                )
                continue

            security = self._coerce_security(security_payload)
            future_security = self._is_future_data(security.available_at)
            if future_security:
                manifest["rejected"] += 1
                self.warehouse.insert_failure(run_id=run_id, security_id=security_id, reason="future-data", payload=security_payload)
            else:
                self.warehouse.insert_security(security)
                self.warehouse.insert_ticker_history(
                    TickerHistoryEntry(
                        security_id=security.security_id,
                        ticker=security.ticker,
                        valid_from=security.listing_date,
                        valid_to=security.delisting_date,
                        active=security.active,
                        available_at=security.available_at,
                        revision_id=security.revision_id,
                    )
                )
                self.warehouse.insert_event(
                    CanonicalEvent(
                        event_type=EventType.SECURITY_CREATED,
                        security_id=security.security_id,
                        occurred_at=security.listing_date,
                        available_at=security.available_at,
                        payload={"ticker": security.ticker, "source": security.source},
                    )
                )
                manifest["inserted"] += 1
                manifest["quality_summary"]["valid"] += 1

            ticker_histories = self.provider.list_ticker_histories(symbols)
            if ticker_histories:
                entries = [self._coerce_ticker_history(entry, security_id) for entry in ticker_histories]
                if self._has_overlapping_history(entries):
                    manifest["rejected"] += 1
                    self.warehouse.insert_failure(run_id=run_id, security_id=security_id, reason="overlapping-ticker-history", payload={"ticker_histories": ticker_histories})
                else:
                    for entry in entries:
                        self.warehouse.insert_ticker_history(entry)
                        if not future_security:
                            manifest["inserted"] += 1

            for action_payload in self.provider.list_corporate_actions(symbols):
                if str(action_payload.get("security_id")) != security_id:
                    continue
                action = self._coerce_action(action_payload)
                if self._is_future_data(action.available_at):
                    manifest["rejected"] += 1
                    self.warehouse.insert_failure(run_id=run_id, security_id=security_id, reason="future-action", payload=action_payload)
                    continue
                self.warehouse.insert_corporate_action(action)
                if action.action_type == "SYMBOL_CHANGE" and action.to_ticker:
                    self.warehouse.insert_ticker_history(
                        TickerHistoryEntry(
                            security_id=action.security_id,
                            ticker=action.to_ticker,
                            valid_from=action.effective_date,
                            valid_to=None,
                            active=True,
                            available_at=action.available_at or security.available_at,
                            revision_id=action.revision_id,
                        )
                    )
                if action.action_type == "DELISTING":
                    self.warehouse.insert_event(
                        CanonicalEvent(
                            event_type=EventType.DELISTING,
                            security_id=action.security_id,
                            occurred_at=action.effective_date,
                            available_at=action.available_at or security.available_at,
                            payload={"action_type": action.action_type},
                        )
                    )
                else:
                    self.warehouse.insert_event(
                        CanonicalEvent(
                            event_type=EventType.TICKER_CHANGE,
                            security_id=action.security_id,
                            occurred_at=action.effective_date,
                            available_at=action.available_at or security.available_at,
                            payload={"from_ticker": action.from_ticker, "to_ticker": action.to_ticker},
                        )
                    )
                manifest["inserted"] += 1

            for bar_payload in self.provider.list_bars(symbols):
                if str(bar_payload.get("security_id")) != security_id:
                    continue
                bar = self._coerce_bar(bar_payload)
                if self._is_future_data(bar.available_at):
                    manifest["rejected"] += 1
                    self.warehouse.insert_failure(run_id=run_id, security_id=security_id, reason="future-bar", payload=bar_payload)
                    continue
                if not self._is_valid_ohlc(bar):
                    manifest["rejected"] += 1
                    self.warehouse.insert_failure(run_id=run_id, security_id=security_id, reason="invalid-ohlc", payload=bar_payload)
                    continue
                self.warehouse.insert_bar(bar)
                if bar.bar_type == "RAW":
                    adjusted = self._coerce_adjusted(bar_payload, bar)
                    if adjusted is not None:
                        self.warehouse.insert_bar(adjusted)
                manifest["inserted"] += 1
                manifest["quality_summary"]["valid"] += 1

        manifest["failed"] = self.warehouse.failure_count()
        manifest["quality_summary"]["failures"] = manifest["failed"]
        manifest["quality_summary"]["rejected"] = manifest["rejected"]
        payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        manifest["hash"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.warehouse.insert_manifest(run_id=run_id, manifest=manifest)
        return manifest

    def _is_future_data(self, available_at: datetime | None) -> bool:
        if available_at is None:
            return False
        return available_at > datetime.now(timezone.utc)

    def _is_valid_ohlc(self, bar: BarRecord) -> bool:
        return bool(bar.open > 0 and bar.high > 0 and bar.low > 0 and bar.close > 0 and bar.high >= bar.low and bar.open >= bar.low and bar.open <= bar.high and bar.close >= bar.low and bar.close <= bar.high)

    def _coerce_security(self, payload: dict[str, Any]) -> SecurityRecord:
        return SecurityRecord(
            security_id=str(payload.get("security_id") or payload.get("ticker") or ""),
            ticker=str(payload.get("ticker") or ""),
            company_name=str(payload.get("company_name") or ""),
            exchange=str(payload.get("exchange") or ""),
            asset_type=str(payload.get("asset_type") or "STOCK"),
            currency=str(payload.get("currency") or "USD"),
            listing_date=self._parse_date(payload.get("listing_date")),
            delisting_date=self._parse_date(payload.get("delisting_date")),
            active=bool(payload.get("active", True)),
            source=str(payload.get("source") or "provider"),
            available_at=self._parse_timestamp(payload.get("available_at")),
            revision_id=str(payload.get("revision_id") or ""),
        )

    def _coerce_action(self, payload: dict[str, Any]) -> CorporateAction:
        return CorporateAction(
            security_id=str(payload.get("security_id") or ""),
            action_type=str(payload.get("action_type") or ""),
            effective_date=self._parse_date(payload.get("effective_date")),
            from_ticker=str(payload.get("from_ticker") or None),
            to_ticker=str(payload.get("to_ticker") or None),
            source=str(payload.get("source") or "provider"),
            available_at=self._parse_timestamp(payload.get("available_at")),
            revision_id=str(payload.get("revision_id") or ""),
        )

    def _coerce_ticker_history(self, payload: dict[str, Any], security_id: str) -> TickerHistoryEntry:
        return TickerHistoryEntry(
            security_id=security_id,
            ticker=str(payload.get("ticker") or ""),
            valid_from=self._parse_date(payload.get("valid_from")),
            valid_to=self._parse_date(payload.get("valid_to")),
            active=bool(payload.get("active", True)),
            available_at=self._parse_timestamp(payload.get("available_at")),
            revision_id=str(payload.get("revision_id") or ""),
        )

    def _has_overlapping_history(self, entries: list[TickerHistoryEntry]) -> bool:
        ordered = sorted(entries, key=lambda item: (item.valid_from, item.valid_to or datetime.max.replace(tzinfo=timezone.utc)))
        for index in range(1, len(ordered)):
            previous = ordered[index - 1]
            current = ordered[index]
            prev_end = previous.valid_to or datetime.max.replace(tzinfo=timezone.utc)
            if current.valid_from <= prev_end:
                return True
        return False

    def _coerce_bar(self, payload: dict[str, Any]) -> BarRecord:
        trade_date = self._parse_date(payload.get("trade_date"))
        bar_type = "RAW"
        return BarRecord(
            security_id=str(payload.get("security_id") or ""),
            trade_date=trade_date,
            open=float(payload.get("open") or 0.0),
            high=float(payload.get("high") or 0.0),
            low=float(payload.get("low") or 0.0),
            close=float(payload.get("close") or 0.0),
            volume=float(payload.get("volume") or 0.0),
            available_at=self._parse_timestamp(payload.get("available_at")),
            source=str(payload.get("source") or "provider"),
            ingestion_timestamp=self._parse_timestamp(payload.get("ingestion_timestamp")),
            revision_id=str(payload.get("revision_id") or ""),
            quality_status=str(payload.get("quality_status") or "VALID"),
            bar_type=bar_type,
        )

    def _coerce_adjusted(self, payload: dict[str, Any], raw_bar: BarRecord) -> BarRecord | None:
        adjusted_open = payload.get("adjusted_open")
        adjusted_high = payload.get("adjusted_high")
        adjusted_low = payload.get("adjusted_low")
        adjusted_close = payload.get("adjusted_close")
        if adjusted_open is None or adjusted_high is None or adjusted_low is None or adjusted_close is None:
            return None
        return BarRecord(
            security_id=raw_bar.security_id,
            trade_date=raw_bar.trade_date,
            open=float(adjusted_open),
            high=float(adjusted_high),
            low=float(adjusted_low),
            close=float(adjusted_close),
            volume=raw_bar.volume,
            available_at=raw_bar.available_at,
            source=raw_bar.source,
            ingestion_timestamp=raw_bar.ingestion_timestamp,
            revision_id=raw_bar.revision_id,
            quality_status=raw_bar.quality_status,
            bar_type="ADJUSTED",
        )

    def _parse_date(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return datetime.now(timezone.utc)
            if "T" in text:
                return self._parse_timestamp(text)
            try:
                return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)

    def _parse_timestamp(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return datetime.now(timezone.utc)
            text = text.replace("Z", "+00:00")
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        return datetime.now(timezone.utc)
