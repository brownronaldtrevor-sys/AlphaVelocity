from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from alpha_velocity.market.bars import Bar
from alpha_velocity.validation.feature_store import (
    FeatureRow,
    FeatureStoreDataset,
    build_feature_rows,
    build_validation_dataset,
    build_chronological_splits,
    validate_feature_rows,
)


def _bars(count: int = 120, seed: float = 10.0, drift: float = 0.001) -> list[Bar]:
    output: list[Bar] = []
    price = seed
    start = datetime(2020, 1, 2)
    for i in range(count):
        price *= 1.0 + drift
        if i % 20 == 0:
            price *= 1.01
        output.append(
            Bar(
                timestamp=start + timedelta(days=i),
                open=price * 0.995,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=100_000 + i * 100,
            )
        )
    return output


def _bars_with_ambiguity() -> list[Bar]:
    bars = _bars(count=140)
    base = bars[-1].close
    ambiguous = Bar(
        timestamp=bars[-1].timestamp + timedelta(days=1),
        open=base * 1.03,
        high=base * 1.08,
        low=base * 0.92,
        close=base * 1.00,
        volume=100_000,
    )
    return bars + [ambiguous]


def test_feature_rows_are_point_in_time_and_leakage_free() -> None:
    dataset = build_validation_dataset(
        symbol_bars={"AAPL": _bars(count=140)},
        observation_horizon=20,
        label_horizon=20,
        lineage_version="lineage-v1",
        validation_artifact_path=None,
    )
    assert isinstance(dataset, FeatureStoreDataset)
    assert dataset.rows
    first = dataset.rows[0]
    assert first.symbol == "AAPL"
    assert first.observation_date == first.available_at
    assert first.feature_values["return_5d"] <= 1.0
    assert "close_location_1d" in first.feature_values
    assert "price_action_weight" in first.feature_values
    assert first.price_action_weight == 0.0


def test_labels_capture_target_and_stop_ambiguity() -> None:
    dataset = build_validation_dataset(
        symbol_bars={"AAPL": _bars_with_ambiguity()},
        observation_horizon=20,
        label_horizon=20,
        lineage_version="lineage-v1",
        validation_artifact_path=None,
    )
    assert dataset.labels
    assert dataset.labels[-1].forward_return_1d != 0.0
    assert dataset.labels[-1].target_before_stop in {0.0, 1.0}


def test_chronological_splits_include_purge_and_embargo() -> None:
    dataset = build_validation_dataset(
        symbol_bars={"AAPL": _bars(count=260)},
        observation_horizon=20,
        label_horizon=20,
        lineage_version="lineage-v1",
        validation_artifact_path=None,
        validation_fraction=0.2,
        test_fraction=0.2,
    )
    splits = build_chronological_splits(dataset.rows, label_horizon=20)
    assert set(splits) == {"train", "validation", "test"}
    assert splits["train"]
    assert splits["validation"]
    assert splits["test"]
    assert splits["train"][-1].observation_date < splits["validation"][0].observation_date
    assert splits["validation"][-1].observation_date < splits["test"][0].observation_date


def test_manifest_and_ablation_support() -> None:
    output_dir = Path("/tmp/alpha_velocity_test_dataset")
    dataset = build_validation_dataset(
        symbol_bars={"AAPL": _bars(count=140)},
        observation_horizon=20,
        label_horizon=20,
        lineage_version="lineage-v1",
        validation_artifact_path=None,
        feature_groups_to_exclude={"price_action"},
        output_dir=output_dir,
    )
    manifest_path = output_dir / "dataset_manifest.json"
    assert manifest_path.exists()
    assert dataset.manifest["row_counts"]["features"] == len(dataset.rows)
    assert dataset.manifest["hashes"]
    assert all("close_location_1d" not in row.feature_values for row in dataset.rows)


def test_validation_rejects_invalid_inputs() -> None:
    duplicate_rows = [
        FeatureRow(
            symbol="AAPL",
            observation_date=datetime(2020, 1, 3),
            available_at=datetime(2020, 1, 3),
            feature_values={"return_5d": 0.01},
            price_action_weight=0.0,
            price_action_active=False,
            lineage_version="lineage-v1",
        )
    ] * 2
    with pytest.raises(ValueError):
        validate_feature_rows(duplicate_rows)

    bad_bar = Bar(
        timestamp=datetime(2020, 1, 1),
        open=1.0,
        high=0.5,
        low=0.6,
        close=0.8,
        volume=-1.0,
    )
    with pytest.raises(ValueError):
        build_feature_rows({"AAPL": [bad_bar]}, observation_date=datetime(2020, 1, 1), available_at=datetime(2020, 1, 1), lineage_version="lineage-v1")
