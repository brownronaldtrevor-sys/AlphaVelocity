from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import BarRecord, CanonicalEvent, CorporateAction, EventType, SecurityRecord, TickerHistoryEntry


def _to_utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        text = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    raise TypeError(type(value))


def _fmt(value: datetime | str | None) -> str | None:
    parsed = _to_utc(value)
    if parsed is None:
        return None
    return parsed.isoformat()


class SQLiteHistoricalWarehouse:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS securities (
                security_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                company_name TEXT,
                exchange TEXT,
                asset_type TEXT,
                currency TEXT,
                listing_date TEXT,
                delisting_date TEXT,
                active INTEGER,
                source TEXT,
                available_at TEXT,
                revision_id TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS ticker_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                security_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                active INTEGER,
                available_at TEXT NOT NULL,
                revision_id TEXT,
                UNIQUE(security_id, ticker, valid_from, revision_id)
            );
            CREATE TABLE IF NOT EXISTS corporate_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                security_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                effective_date TEXT NOT NULL,
                from_ticker TEXT,
                to_ticker TEXT,
                source TEXT,
                available_at TEXT,
                revision_id TEXT,
                UNIQUE(security_id, action_type, effective_date, revision_id)
            );
            CREATE TABLE IF NOT EXISTS bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                security_id TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                adjusted_open REAL,
                adjusted_high REAL,
                adjusted_low REAL,
                adjusted_close REAL,
                available_at TEXT NOT NULL,
                source TEXT,
                ingestion_timestamp TEXT,
                revision_id TEXT,
                quality_status TEXT,
                bar_type TEXT NOT NULL,
                UNIQUE(security_id, trade_date, bar_type, revision_id)
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                security_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                available_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                security_id TEXT,
                reason TEXT NOT NULL,
                payload TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS manifests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                manifest_hash TEXT NOT NULL,
                inserted INTEGER NOT NULL,
                rejected INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(run_id, manifest_hash)
            );
            """
        )
        self._conn.commit()

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        self._conn.execute(query, params)
        self._conn.commit()

    def insert_security(self, security: SecurityRecord) -> None:
        self._execute(
            """
            INSERT OR IGNORE INTO securities (
                security_id, ticker, company_name, exchange, asset_type, currency,
                listing_date, delisting_date, active, source, available_at, revision_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                security.security_id,
                security.ticker,
                security.company_name,
                security.exchange,
                security.asset_type,
                security.currency,
                _fmt(security.listing_date),
                _fmt(security.delisting_date),
                int(security.active),
                security.source,
                _fmt(security.available_at),
                security.revision_id,
                _fmt(datetime.now(timezone.utc)),
            ),
        )

    def insert_ticker_history(self, entry: TickerHistoryEntry) -> None:
        self._execute(
            """
            INSERT OR IGNORE INTO ticker_history (
                security_id, ticker, valid_from, valid_to, active, available_at, revision_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.security_id,
                entry.ticker,
                _fmt(entry.valid_from),
                _fmt(entry.valid_to),
                int(entry.active),
                _fmt(entry.available_at),
                entry.revision_id,
            ),
        )

    def insert_corporate_action(self, action: CorporateAction) -> None:
        self._execute(
            """
            INSERT OR IGNORE INTO corporate_actions (
                security_id, action_type, effective_date, from_ticker, to_ticker, source, available_at, revision_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action.security_id,
                action.action_type,
                _fmt(action.effective_date),
                action.from_ticker,
                action.to_ticker,
                action.source,
                _fmt(action.available_at),
                action.revision_id,
            ),
        )

    def insert_bar(self, bar: BarRecord) -> None:
        self._execute(
            """
            INSERT OR IGNORE INTO bars (
                security_id, trade_date, open, high, low, close, volume,
                adjusted_open, adjusted_high, adjusted_low, adjusted_close,
                available_at, source, ingestion_timestamp, revision_id, quality_status, bar_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bar.security_id,
                _fmt(bar.trade_date),
                bar.open,
                bar.high,
                bar.low,
                bar.close,
                bar.volume,
                None,
                None,
                None,
                None,
                _fmt(bar.available_at),
                bar.source,
                _fmt(bar.ingestion_timestamp),
                bar.revision_id,
                bar.quality_status,
                bar.bar_type,
            ),
        )

    def insert_event(self, event: CanonicalEvent) -> None:
        self._execute(
            """
            INSERT INTO events (event_type, security_id, occurred_at, available_at, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event.event_type.value,
                event.security_id,
                _fmt(event.occurred_at),
                _fmt(event.available_at),
                json.dumps(event.payload, sort_keys=True),
            ),
        )

    def insert_failure(self, *, run_id: str, security_id: str | None, reason: str, payload: dict[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO failures (run_id, security_id, reason, payload, occurred_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_id,
                security_id,
                reason,
                json.dumps(payload, sort_keys=True),
                _fmt(datetime.now(timezone.utc)),
            ),
        )

    def insert_manifest(self, *, run_id: str, manifest: dict[str, Any]) -> None:
        payload = json.dumps(manifest, sort_keys=True)
        manifest_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self._execute(
            """
            INSERT OR IGNORE INTO manifests (run_id, manifest_hash, inserted, rejected, failed, created_at, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                manifest_hash,
                manifest["inserted"],
                manifest["rejected"],
                manifest["failed"],
                _fmt(datetime.now(timezone.utc)),
                payload,
            ),
        )

    def get_security(self, security_id: str, *, as_of: datetime | None = None) -> SecurityRecord | None:
        row = self._conn.execute("SELECT * FROM securities WHERE security_id = ?", (security_id,)).fetchone()
        if row is None:
            return None
        record = SecurityRecord(
            security_id=row["security_id"],
            ticker=row["ticker"],
            company_name=row["company_name"] or "",
            exchange=row["exchange"] or "",
            asset_type=row["asset_type"] or "",
            currency=row["currency"] or "USD",
            listing_date=_to_utc(row["listing_date"]) or datetime.now(timezone.utc),
            delisting_date=_to_utc(row["delisting_date"]),
            active=bool(row["active"]),
            source=row["source"] or "",
            available_at=_to_utc(row["available_at"]) or datetime.now(timezone.utc),
            revision_id=row["revision_id"],
        )
        if as_of is not None:
            as_of_value = _to_utc(as_of)
            if as_of_value is not None and record.available_at > as_of_value:
                return None
        return record

    def get_ticker_history(self, security_id: str, *, as_of: datetime | None = None) -> list[TickerHistoryEntry]:
        rows = self._conn.execute("SELECT * FROM ticker_history WHERE security_id = ? ORDER BY valid_from", (security_id,)).fetchall()
        history: list[TickerHistoryEntry] = []
        for row in rows:
            entry = TickerHistoryEntry(
                security_id=row["security_id"],
                ticker=row["ticker"],
                valid_from=_to_utc(row["valid_from"]) or datetime.now(timezone.utc),
                valid_to=_to_utc(row["valid_to"]),
                active=bool(row["active"]),
                available_at=_to_utc(row["available_at"]) or datetime.now(timezone.utc),
                revision_id=row["revision_id"],
            )
            if as_of is not None:
                as_of_value = _to_utc(as_of)
                if as_of_value is not None and entry.available_at > as_of_value:
                    continue
                if entry.valid_to is not None and as_of_value is not None and entry.valid_to < as_of_value:
                    continue
            history.append(entry)
        return history

    def point_in_time_universe(self, *, as_of: datetime | None = None) -> list[SecurityRecord]:
        rows = self._conn.execute("SELECT * FROM securities ORDER BY security_id").fetchall()
        results: list[SecurityRecord] = []
        for row in rows:
            record = SecurityRecord(
                security_id=row["security_id"],
                ticker=row["ticker"],
                company_name=row["company_name"] or "",
                exchange=row["exchange"] or "",
                asset_type=row["asset_type"] or "",
                currency=row["currency"] or "USD",
                listing_date=_to_utc(row["listing_date"]) or datetime.now(timezone.utc),
                delisting_date=_to_utc(row["delisting_date"]),
                active=bool(row["active"]),
                source=row["source"] or "",
                available_at=_to_utc(row["available_at"]) or datetime.now(timezone.utc),
                revision_id=row["revision_id"],
            )
            if as_of is not None:
                as_of_value = _to_utc(as_of)
                if as_of_value is not None and record.available_at > as_of_value:
                    continue
                if record.delisting_date is not None and as_of_value is not None and as_of_value >= record.delisting_date:
                    continue
                if record.listing_date is not None and as_of_value is not None and record.listing_date > as_of_value:
                    continue
            results.append(record)
        return results

    def get_raw_bars(self, security_id: str) -> list[BarRecord]:
        return self._bars_for_security(security_id, bar_type="RAW")

    def get_adjusted_bars(self, security_id: str) -> list[BarRecord]:
        return self._bars_for_security(security_id, bar_type="ADJUSTED")

    def _bars_for_security(self, security_id: str, *, bar_type: str) -> list[BarRecord]:
        rows = self._conn.execute("SELECT * FROM bars WHERE security_id = ? AND bar_type = ? ORDER BY trade_date", (security_id, bar_type)).fetchall()
        return [
            BarRecord(
                security_id=row["security_id"],
                trade_date=_to_utc(row["trade_date"]) or datetime.now(timezone.utc),
                open=float(row["open"] or 0.0),
                high=float(row["high"] or 0.0),
                low=float(row["low"] or 0.0),
                close=float(row["close"] or 0.0),
                volume=float(row["volume"] or 0.0),
                available_at=_to_utc(row["available_at"]) or datetime.now(timezone.utc),
                source=row["source"] or "",
                ingestion_timestamp=_to_utc(row["ingestion_timestamp"]) or datetime.now(timezone.utc),
                revision_id=row["revision_id"],
                quality_status=row["quality_status"] or "VALID",
                bar_type=row["bar_type"] or bar_type,
            )
            for row in rows
        ]

    def completed_weekly_bars(self, security_id: str, *, as_of: datetime) -> list[BarRecord]:
        bars = self.get_raw_bars(security_id)
        if not bars:
            return []
        grouped: dict[tuple[int, int], list[BarRecord]] = {}
        as_of_value = _to_utc(as_of)
        for bar in bars:
            week = bar.trade_date.isocalendar()[:2]
            grouped.setdefault(week, []).append(bar)
        results: list[BarRecord] = []
        for week, week_bars in grouped.items():
            if not week_bars:
                continue
            latest_date = max(bar.trade_date for bar in week_bars)
            if as_of_value is not None and as_of_value >= latest_date:
                results.append(
                    BarRecord(
                        security_id=security_id,
                        trade_date=latest_date,
                        open=week_bars[0].open,
                        high=max(bar.high for bar in week_bars),
                        low=min(bar.low for bar in week_bars),
                        close=week_bars[-1].close,
                        volume=sum(bar.volume for bar in week_bars),
                        available_at=as_of_value or as_of,
                        source="warehouse",
                        ingestion_timestamp=as_of_value or as_of,
                        revision_id=None,
                        quality_status="VALID",
                        bar_type="WEEKLY",
                    )
                )
        return sorted(results, key=lambda item: item.trade_date)

    def quarantine_count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM failures").fetchone()[0])

    def failure_count(self) -> int:
        return self.quarantine_count()

    def latest_manifest(self) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT payload FROM manifests ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return json.loads(row[0])
