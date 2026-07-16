from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from alpha_velocity.market.bars import Bar
from alpha_velocity.opportunity import Opportunity, assemble_opportunity


def _bar(timestamp: datetime, close: float, high: float, low: float, open_price: float, volume: float) -> Bar:
    return Bar(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def test_opportunity_is_immutable_and_serializes_deterministically() -> None:
    observation_time = datetime(2024, 1, 10, tzinfo=timezone.utc)
    opp = Opportunity(
        opportunity_id="opp-1",
        security_id="sec-1",
        symbol="ABC",
        observation_time=observation_time,
        data_available_through=observation_time,
        universe_snapshot_id="u-1",
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        market_regime="bullish",
        sector_regime="bullish",
        weekly_trend_state="bullish",
        weekly_range_position=0.75,
        weekly_support_levels=[{"level": 10.0, "provenance": "rolling_low", "window": 20}],
        weekly_resistance_levels=[{"level": 12.0, "provenance": "rolling_high", "window": 20}],
        weekly_breakout_level=12.0,
        weekly_invalidation_level=9.0,
        weekly_volatility_state="expanding",
        weekly_relative_strength=1.1,
        weekly_structure_quality=0.8,
        daily_trend_state="bullish",
        daily_range_position=0.6,
        daily_support_levels=[{"level": 10.4, "provenance": "swing_low", "window": 10}],
        daily_resistance_levels=[{"level": 11.5, "provenance": "swing_high", "window": 10}],
        daily_breakout_level=11.5,
        daily_invalidation_level=10.0,
        daily_volatility_state="contracting",
        daily_relative_strength=1.05,
        daily_structure_quality=0.7,
        setup_type="breakout",
        trigger_state="triggered",
        breakout_distance_pct=0.04,
        distance_to_support_pct=0.02,
        distance_to_resistance_pct=0.03,
        volatility_contraction=0.2,
        volatility_expansion=0.0,
        relative_volume=1.4,
        close_quality=0.8,
        failed_breakout=False,
        failed_breakdown=False,
        multi_timeframe_alignment="ALIGNED_BULLISH",
        close_price=11.0,
        average_daily_dollar_volume=1_000_000.0,
        average_daily_volume=1000.0,
        spread_estimate_bps=1.5,
        atr_pct=0.03,
        capacity_warning=False,
        known_catalysts=[],
        next_known_event_time=None,
        catalyst_risk="low",
        event_data_available_at=observation_time,
        probability_estimate=0.6,
        expected_upside_pct=0.1,
        expected_downside_pct=0.03,
        expected_holding_days=10.0,
        estimated_cost_bps=20.0,
        uncertainty_score=0.2,
        calibration_status="CALIBRATED",
        expected_value_score=0.8,
        opportunity_cost_rank=1,
        correlation_bucket="low",
        concentration_bucket="moderate",
        current_position_weight=0.05,
        primary_invalidation_price=9.8,
        thesis_invalidation_reasons=["price closes below support"],
        liquidity_risk="low",
        gap_risk="moderate",
        model_disagreement=False,
        governance_eligible=True,
        risk_eligible=True,
        feature_values={"price_action": 0.5},
        feature_versions={"price_action": "v1"},
        model_versions={"price_action": "m1"},
        warehouse_manifest_hash="w1",
        dataset_manifest_hash="d1",
        source_record_ids=["r1"],
        warnings=[],
        created_at=observation_time,
    )
    payload = opp.to_dict()
    restored = Opportunity.from_dict(payload)
    assert restored == opp
    assert payload["schema_version"] == "1.0.0"
    assert payload["multi_timeframe_alignment"] == "ALIGNED_BULLISH"


def test_future_data_is_rejected() -> None:
    observation_time = datetime(2024, 1, 10, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        Opportunity(
            opportunity_id="opp-2",
            security_id="sec-2",
            symbol="XYZ",
            observation_time=observation_time,
            data_available_through=observation_time,
            universe_snapshot_id="u-1",
            benchmark_symbol="SPY",
            sector="Technology",
            industry="Software",
            market_regime="bullish",
            sector_regime="bullish",
            weekly_trend_state="bullish",
            weekly_range_position=0.4,
            weekly_support_levels=[],
            weekly_resistance_levels=[],
            weekly_breakout_level=0.0,
            weekly_invalidation_level=0.0,
            weekly_volatility_state="neutral",
            weekly_relative_strength=1.0,
            weekly_structure_quality=0.5,
            daily_trend_state="bullish",
            daily_range_position=0.5,
            daily_support_levels=[],
            daily_resistance_levels=[],
            daily_breakout_level=0.0,
            daily_invalidation_level=0.0,
            daily_volatility_state="neutral",
            daily_relative_strength=1.0,
            daily_structure_quality=0.5,
            setup_type="breakout",
            trigger_state="watch",
            breakout_distance_pct=0.0,
            distance_to_support_pct=0.0,
            distance_to_resistance_pct=0.0,
            volatility_contraction=0.0,
            volatility_expansion=0.0,
            relative_volume=1.0,
            close_quality=0.5,
            failed_breakout=False,
            failed_breakdown=False,
            multi_timeframe_alignment="INSUFFICIENT_DATA",
            close_price=10.0,
            average_daily_dollar_volume=1_000_000.0,
            average_daily_volume=1000.0,
            spread_estimate_bps=1.0,
            atr_pct=0.02,
            capacity_warning=False,
            known_catalysts=[{"event_type": "earnings", "occurred_at": observation_time + timedelta(days=1), "available_at": observation_time}],
            next_known_event_time=observation_time + timedelta(days=1),
            catalyst_risk="low",
            event_data_available_at=observation_time,
            probability_estimate=None,
            expected_upside_pct=None,
            expected_downside_pct=None,
            expected_holding_days=None,
            estimated_cost_bps=None,
            uncertainty_score=0.5,
            calibration_status="UNCALIBRATED",
            expected_value_score=0.0,
            opportunity_cost_rank=2,
            correlation_bucket="medium",
            concentration_bucket="moderate",
            current_position_weight=0.1,
            primary_invalidation_price=9.0,
            thesis_invalidation_reasons=[],
            liquidity_risk="low",
            gap_risk="low",
            model_disagreement=False,
            governance_eligible=True,
            risk_eligible=True,
            feature_values={},
            feature_versions={},
            model_versions={},
            warehouse_manifest_hash="w",
            dataset_manifest_hash="d",
            source_record_ids=[],
            warnings=[],
            created_at=observation_time,
        )


def test_assembler_uses_completed_weekly_bars_only_and_provisional_weekly_bars_are_ignored() -> None:
    observation_time = datetime(2024, 1, 10, tzinfo=timezone.utc)
    daily_bars = [
        _bar(observation_time - timedelta(days=20), 10.0, 10.5, 9.5, 10.0, 1000.0),
        _bar(observation_time - timedelta(days=10), 11.0, 11.5, 10.5, 10.8, 1200.0),
        _bar(observation_time, 11.5, 12.0, 11.0, 11.2, 1500.0),
    ]
    weekly_bars = [
        _bar(observation_time - timedelta(days=14), 10.0, 10.5, 9.5, 10.0, 1000.0),
        _bar(observation_time - timedelta(days=7), 11.0, 11.5, 10.5, 10.8, 1200.0),
    ]
    provisional_weekly_bars = [
        _bar(observation_time, 11.5, 12.0, 11.0, 11.2, 1500.0),
    ]
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
        benchmark_bars=[],
        sector_bars=[],
        feature_snapshots=[],
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id="sec-3",
        symbol="ABC",
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        universe_snapshot_id="u-3",
        provisional_weekly_bars=provisional_weekly_bars,
        warehouse_manifest_hash="w3",
        dataset_manifest_hash="d3",
        source_record_ids=["r3"],
    )
    assert opp.weekly_support_levels
    assert opp.weekly_resistance_levels
    assert opp.multi_timeframe_alignment in {"ALIGNED_BULLISH", "WEEKLY_BULLISH_DAILY_PULLBACK", "INSUFFICIENT_DATA"}


def test_alignment_states_are_classified_transparently() -> None:
    observation_time = datetime(2024, 1, 10, tzinfo=timezone.utc)
    daily_bars = [
        _bar(observation_time - timedelta(days=2), 10.0, 10.5, 9.5, 10.0, 1000.0),
        _bar(observation_time - timedelta(days=1), 10.2, 10.7, 10.0, 10.2, 1100.0),
        _bar(observation_time, 10.4, 10.8, 10.1, 10.3, 1200.0),
    ]
    weekly_bars = [
        _bar(observation_time - timedelta(days=10), 9.8, 10.2, 9.4, 9.7, 900.0),
        _bar(observation_time - timedelta(days=3), 10.0, 10.6, 9.8, 10.0, 1000.0),
    ]
    opp = assemble_opportunity(
        daily_bars=daily_bars,
        weekly_bars=weekly_bars,
        benchmark_bars=[],
        sector_bars=[],
        feature_snapshots=[],
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id="sec-4",
        symbol="XYZ",
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        universe_snapshot_id="u-4",
        warehouse_manifest_hash="w4",
        dataset_manifest_hash="d4",
        source_record_ids=["r4"],
    )
    assert opp.multi_timeframe_alignment in {"ALIGNED_BULLISH", "WEEKLY_BULLISH_DAILY_PULLBACK", "CONFLICTED", "INSUFFICIENT_DATA"}


def test_uncalibrated_expected_value_status_is_used_when_probabilities_are_missing() -> None:
    observation_time = datetime(2024, 1, 10, tzinfo=timezone.utc)
    opp = assemble_opportunity(
        daily_bars=[_bar(observation_time, 10.0, 10.5, 9.5, 10.0, 1000.0)],
        weekly_bars=[_bar(observation_time - timedelta(days=7), 9.8, 10.2, 9.5, 9.9, 1000.0)],
        benchmark_bars=[],
        sector_bars=[],
        feature_snapshots=[],
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id="sec-5",
        symbol="QRS",
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        universe_snapshot_id="u-5",
        warehouse_manifest_hash="w5",
        dataset_manifest_hash="d5",
        source_record_ids=["r5"],
    )
    assert opp.calibration_status == "UNCALIBRATED"
    assert opp.expected_value_score == 0.0


def test_validation_gated_feature_influence_is_not_used_for_confidence() -> None:
    observation_time = datetime(2024, 1, 10, tzinfo=timezone.utc)
    feature_snapshots = [
        {"group_name": "price_action", "feature_values": {"trend_structure": 0.9}, "approved_weight": 0.0, "available_at": observation_time},
        {"group_name": "sentiment", "feature_values": {"sentiment_score": 0.8}, "approved_weight": 0.1, "available_at": observation_time},
    ]
    opp = assemble_opportunity(
        daily_bars=[_bar(observation_time, 10.0, 10.5, 9.5, 10.0, 1000.0)],
        weekly_bars=[_bar(observation_time - timedelta(days=7), 9.8, 10.2, 9.5, 9.9, 1000.0)],
        benchmark_bars=[],
        sector_bars=[],
        feature_snapshots=feature_snapshots,
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id="sec-6",
        symbol="TUV",
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        universe_snapshot_id="u-6",
        warehouse_manifest_hash="w6",
        dataset_manifest_hash="d6",
        source_record_ids=["r6"],
    )
    assert any("unvalidated" in warning.lower() for warning in opp.warnings)
    assert opp.feature_values["sentiment"] == 0.0


def test_json_output_and_no_order_or_portfolio_fields() -> None:
    observation_time = datetime(2024, 1, 10, tzinfo=timezone.utc)
    opp = assemble_opportunity(
        daily_bars=[_bar(observation_time, 10.0, 10.5, 9.5, 10.0, 1000.0)],
        weekly_bars=[_bar(observation_time - timedelta(days=7), 9.8, 10.2, 9.5, 9.9, 1000.0)],
        benchmark_bars=[],
        sector_bars=[],
        feature_snapshots=[],
        known_events=[],
        liquidity_history=[],
        observation_time=observation_time,
        security_id="sec-7",
        symbol="VWX",
        benchmark_symbol="SPY",
        sector="Technology",
        industry="Software",
        universe_snapshot_id="u-7",
        warehouse_manifest_hash="w7",
        dataset_manifest_hash="d7",
        source_record_ids=["r7"],
    )
    payload = opp.to_json()
    assert '"schema_version": "1.0.0"' in payload
    assert "orders" not in opp.to_dict()
    assert "fills" not in opp.to_dict()
    assert "portfolio" not in opp.to_dict()
