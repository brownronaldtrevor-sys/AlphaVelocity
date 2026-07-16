from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from alpha_velocity.market.bars import Bar
from alpha_velocity.price_action.features import compute_price_action_snapshot
from alpha_velocity.price_action.validation import load_approved_weight
from alpha_velocity.signals.technical import compute_snapshot
from alpha_velocity.validation.anti_lookahead import LookAheadViolation


@dataclass(frozen=True)
class FeatureRow:
    symbol: str
    observation_date: datetime
    available_at: datetime
    feature_values: dict[str, float]
    price_action_weight: float
    price_action_active: bool
    lineage_version: str


@dataclass(frozen=True)
class LabelRow:
    symbol: str
    observation_date: datetime
    available_at: datetime
    forward_return_1d: float
    forward_return_5d: float
    forward_return_20d: float
    forward_return_60d: float
    max_favorable_excursion: float
    max_adverse_excursion: float
    target_before_stop: float
    time_to_target_or_stop: float
    ambiguous: bool


@dataclass(frozen=True)
class FeatureStoreDataset:
    rows: list[FeatureRow]
    labels: list[LabelRow]
    manifest: dict[str, Any]


_FEATURE_GROUPS = {
    "technical": ["return_5d", "return_20d", "volatility_20d", "trend_score", "breakout_score"],
    "liquidity": ["volume_ratio_20d"],
    "volatility": ["atr_pct_14d"],
    "market_relative": ["distance_from_20d_high"],
    "price_action": ["close_location_1d", "range_position_20d", "range_position_60d", "trend_structure"],
}


def _validate_bar(bar: Bar) -> None:
    if not (bar.open > 0 and bar.high > 0 and bar.low > 0 and bar.close > 0):
        raise ValueError("OHLCV values must be strictly positive.")
    if bar.high < bar.low or bar.open < bar.low or bar.open > bar.high or bar.close < bar.low or bar.close > bar.high:
        raise ValueError("Invalid OHLCV values detected.")
    if bar.volume < 0:
        raise ValueError("Volume cannot be negative.")


def _safe_pct(a: float, b: float) -> float:
    return 0.0 if b == 0 else (a / b) - 1.0


def _build_feature_values(
    bars: list[Bar],
    *,
    price_action_weight: float,
    price_action_active: bool,
    feature_groups_to_exclude: set[str],
) -> dict[str, float]:
    if len(bars) < 60:
        raise ValueError("At least 60 bars are required to build features.")
    snapshot = compute_snapshot(bars)
    features = {
        "close": snapshot.close,
        "return_5d": snapshot.return_5d,
        "return_20d": snapshot.return_20d,
        "distance_from_20d_high": snapshot.distance_from_20d_high,
        "volume_ratio_20d": snapshot.volume_ratio_20d,
        "atr_pct_14d": snapshot.atr_pct_14d,
        "volatility_20d": snapshot.volatility_20d,
        "trend_score": snapshot.trend_score,
        "breakout_score": snapshot.breakout_score,
        "volume_score": snapshot.volume_score,
        "reversal_score": snapshot.reversal_score,
        "composite_score": snapshot.composite_score,
    }
    if "price_action" not in feature_groups_to_exclude:
        try:
            pa_snapshot = compute_price_action_snapshot(bars)
            features.update(pa_snapshot.feature_values)
        except ValueError:
            features.update({
                "close_location_1d": 0.0,
                "range_position_20d": 0.0,
                "range_position_60d": 0.0,
                "trend_structure": 0.0,
                "compression_ratio": 0.0,
                "expansion_ratio": 0.0,
                "gap_pct": 0.0,
                "breakout_distance_20d": 0.0,
                "breakdown_distance_20d": 0.0,
                "support_distance_60d": 0.0,
                "resistance_distance_60d": 0.0,
                "relative_volume": 0.0,
                "accumulation_score": 0.0,
                "distribution_score": 0.0,
            })
    features["price_action_weight"] = price_action_weight
    features["price_action_active"] = float(price_action_active)
    if "price_action" in feature_groups_to_exclude:
        for key in list(features):
            if key in _FEATURE_GROUPS["price_action"] or key in {"price_action_weight", "price_action_active"}:
                del features[key]
    return features


def build_feature_rows(
    symbol_bars: dict[str, list[Bar]] | None = None,
    observation_date: datetime | None = None,
    available_at: datetime | None = None,
    lineage_version: str | None = None,
    validation_artifact_path: str | Path | None = None,
    feature_groups_to_exclude: set[str] | None = None,
    observation_horizon: int = 20,
    label_horizon: int = 20,
) -> list[FeatureRow]:
    if symbol_bars is None:
        raise ValueError("symbol_bars is required")
    if lineage_version is None:
        raise ValueError("lineage_version is required")
    feature_groups_to_exclude = set(feature_groups_to_exclude or set())
    if observation_date is None:
        observation_date = datetime.now()
    if available_at is None:
        available_at = observation_date
    if available_at < observation_date:
        raise ValueError("available_at cannot precede observation_date")

    rows: list[FeatureRow] = []
    for symbol, bars in symbol_bars.items():
        if not bars:
            continue
        for bar in bars:
            _validate_bar(bar)
        if len(bars) < 60 + observation_horizon + label_horizon:
            raise ValueError(f"At least {60 + observation_horizon + label_horizon} bars are required for {symbol}")
        start_idx = max(observation_horizon, 59)
        for idx in range(start_idx, len(bars) - label_horizon):
            bar = bars[idx]
            if bar.timestamp > observation_date:
                continue
            if bar.timestamp > available_at:
                raise LookAheadViolation(f"No data may be available after {available_at}")
            lookback = bars[max(0, idx - 59): idx + 1]
            if len(lookback) < 60:
                continue
            row_available_at = bar.timestamp
            if row_available_at < bar.timestamp:
                raise ValueError("Row availability cannot precede the observation timestamp")
            approved_weight = 0.0
            price_action_active = False
            if validation_artifact_path is not None:
                approved_weight = load_approved_weight(validation_artifact_path)
                price_action_active = approved_weight > 0.0
            feature_values = _build_feature_values(
                lookback,
                price_action_weight=approved_weight,
                price_action_active=price_action_active,
                feature_groups_to_exclude=feature_groups_to_exclude,
            )
            if "price_action" in feature_groups_to_exclude:
                feature_values["price_action_weight"] = 0.0
                feature_values["price_action_active"] = 0.0
            rows.append(
                FeatureRow(
                    symbol=symbol,
                    observation_date=bar.timestamp,
                    available_at=row_available_at,
                    feature_values=feature_values,
                    price_action_weight=approved_weight,
                    price_action_active=price_action_active,
                    lineage_version=lineage_version,
                )
            )
    return rows


def validate_feature_rows(rows: list[FeatureRow], *, expected_lineage_version: str | None = None) -> None:
    seen: set[tuple[str, datetime, datetime]] = set()
    for row in rows:
        key = (row.symbol, row.observation_date, row.available_at)
        if key in seen:
            raise ValueError("Duplicate primary key detected")
        seen.add(key)
        if row.available_at is None or row.observation_date is None:
            raise ValueError("Observation and availability timestamps are required")
        if row.available_at < row.observation_date:
            raise ValueError("Observed timestamp cannot be after availability timestamp")
        if not row.lineage_version:
            raise ValueError("Lineage version is required")
        if expected_lineage_version is not None and row.lineage_version != expected_lineage_version:
            raise ValueError("Lineage version is stale")
        if not row.feature_values:
            raise ValueError("Feature values must not be empty")
        if row.feature_values.get("price_action_active", 0.0) and row.price_action_weight <= 0.0:
            raise ValueError("Activated price-action features must have a positive approved weight")
        if row.feature_values.get("price_action_weight", 0.0) < 0.0:
            raise ValueError("Price-action weight cannot be negative")


def build_labels(
    *,
    symbol_bars: dict[str, list[Bar]],
    observation_horizon: int,
    label_horizon: int,
) -> list[LabelRow]:
    labels: list[LabelRow] = []
    for symbol, bars in symbol_bars.items():
        if len(bars) < 60 + observation_horizon + label_horizon:
            raise ValueError(f"Insufficient bars for labels for {symbol}")
        start_idx = max(observation_horizon, 59)
        for idx in range(start_idx, len(bars) - label_horizon):
            observation_bar = bars[idx]
            current_close = observation_bar.close
            if current_close <= 0:
                continue
            favorable: list[float] = []
            adverse: list[float] = []
            for step in range(1, label_horizon + 1):
                candidate = bars[idx + step]
                favorable.append(candidate.high - current_close)
                adverse.append(current_close - candidate.low)
            max_favorable = max(favorable) / current_close if favorable else 0.0
            max_adverse = max(adverse) / current_close if adverse else 0.0
            ambiguous = abs(max_favorable - max_adverse) < 1e-6
            target_before_stop = 0.0
            if not ambiguous:
                target_before_stop = 1.0 if max_favorable > max_adverse else 0.0
            time_to_target_or_stop = 0.0
            if favorable or adverse:
                for step, (fav, adv) in enumerate(zip(favorable, adverse), start=1):
                    if fav >= max_favorable or adv >= max_adverse:
                        time_to_target_or_stop = float(step)
                        break
            labels.append(
                LabelRow(
                    symbol=symbol,
                    observation_date=observation_bar.timestamp,
                    available_at=observation_bar.timestamp,
                    forward_return_1d=_safe_pct(bars[idx + 1].close, current_close) if idx + 1 < len(bars) else 0.0,
                    forward_return_5d=_safe_pct(bars[idx + 5].close, current_close) if idx + 5 < len(bars) else 0.0,
                    forward_return_20d=_safe_pct(bars[idx + 20].close, current_close) if idx + 20 < len(bars) else 0.0,
                    forward_return_60d=_safe_pct(bars[idx + 60].close, current_close) if idx + 60 < len(bars) else 0.0,
                    max_favorable_excursion=max_favorable,
                    max_adverse_excursion=max_adverse,
                    target_before_stop=target_before_stop,
                    time_to_target_or_stop=time_to_target_or_stop or float(label_horizon),
                    ambiguous=ambiguous,
                )
            )
    return labels


def _serialize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {str(key): _serialize_payload(value) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_serialize_payload(item) for item in payload]
    if isinstance(payload, datetime):
        return payload.isoformat()
    if isinstance(payload, float):
        return float(payload)
    if isinstance(payload, bool):
        return bool(payload)
    return payload


def _hash_payload(payload: Any) -> str:
    json_bytes = json.dumps(_serialize_payload(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def build_validation_dataset(
    *,
    symbol_bars: dict[str, list[Bar]],
    observation_horizon: int,
    label_horizon: int,
    lineage_version: str,
    validation_artifact_path: str | Path | None = None,
    validation_fraction: float = 0.15,
    test_fraction: float = 0.15,
    feature_groups_to_exclude: set[str] | None = None,
    output_dir: str | Path | None = None,
) -> FeatureStoreDataset:
    feature_groups_to_exclude = set(feature_groups_to_exclude or set())
    if not 0.0 < validation_fraction < 0.5:
        raise ValueError("validation_fraction must lie in (0,0.5)")
    if not 0.0 < test_fraction < 0.5:
        raise ValueError("test_fraction must lie in (0,0.5)")
    if validation_fraction + test_fraction >= 1.0:
        raise ValueError("validation and test fractions must leave room for training")

    rows = build_feature_rows(
        symbol_bars,
        observation_date=None,
        available_at=None,
        lineage_version=lineage_version,
        validation_artifact_path=validation_artifact_path,
        feature_groups_to_exclude=feature_groups_to_exclude,
        observation_horizon=observation_horizon,
        label_horizon=label_horizon,
    )
    validate_feature_rows(rows, expected_lineage_version=lineage_version)
    labels = build_labels(
        symbol_bars=symbol_bars,
        observation_horizon=observation_horizon,
        label_horizon=label_horizon,
    )
    if len(rows) != len(labels):
        raise ValueError("Feature rows and labels must be aligned")

    manifest = {
        "source_versions": {"lineage": lineage_version},
        "feature_definitions": _FEATURE_GROUPS,
        "date_ranges": {
            "start": min(row.observation_date for row in rows).isoformat() if rows else None,
            "end": max(row.observation_date for row in rows).isoformat() if rows else None,
        },
        "symbols": sorted({row.symbol for row in rows}),
        "row_counts": {"features": len(rows), "labels": len(labels)},
        "hashes": {
            "rows": _hash_payload([asdict(row) for row in rows]),
            "labels": _hash_payload([asdict(label) for label in labels]),
        },
        "generation_timestamp": datetime.now().isoformat(),
        "validation_fraction": validation_fraction,
        "test_fraction": test_fraction,
    }
    if output_dir is not None:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return FeatureStoreDataset(rows=rows, labels=labels, manifest=manifest)


def build_chronological_splits(rows: list[FeatureRow], *, label_horizon: int) -> dict[str, list[FeatureRow]]:
    if not rows:
        raise ValueError("Rows are required to build splits")
    sorted_rows = sorted(rows, key=lambda row: (row.observation_date, row.symbol))
    total = len(sorted_rows)
    if total < 3:
        raise ValueError("At least three rows are required for splits")
    purge = max(60, label_horizon)
    embargo = max(10, label_horizon // 4)
    train_end = max(purge, total // 2)
    validation_end = min(total - 1, train_end + max(1, (total - train_end) // 2))
    train = sorted_rows[:train_end]
    validation = sorted_rows[train_end + embargo:validation_end]
    test = sorted_rows[validation_end + embargo:]
    return {"train": train, "validation": validation, "test": test}
