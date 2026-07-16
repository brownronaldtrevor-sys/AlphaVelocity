from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from alpha_velocity.market.bars import Bar
from alpha_velocity.opportunity.models import Opportunity


def assemble_opportunity(
    *,
    daily_bars: list[Bar],
    weekly_bars: list[Bar],
    benchmark_bars: list[Bar],
    sector_bars: list[Bar],
    feature_snapshots: list[dict[str, Any]],
    known_events: list[dict[str, Any]],
    liquidity_history: list[dict[str, Any]],
    observation_time: datetime,
    security_id: str,
    symbol: str,
    benchmark_symbol: str,
    sector: str,
    industry: str,
    universe_snapshot_id: str,
    provisional_weekly_bars: list[Bar] | None = None,
    warehouse_manifest_hash: str,
    dataset_manifest_hash: str,
    source_record_ids: list[str],
) -> Opportunity:
    if not observation_time.tzinfo:
        raise ValueError("observation_time must be timezone-aware")
    completed_weekly = [bar for bar in weekly_bars if bar.timestamp <= observation_time]
    if not completed_weekly and weekly_bars:
        completed_weekly = []
    completed_daily = [bar for bar in daily_bars if bar.timestamp <= observation_time]
    if not completed_daily:
        completed_daily = []
    latest_daily = completed_daily[-1] if completed_daily else None
    latest_weekly = completed_weekly[-1] if completed_weekly else None
    weekly_support = _rolling_support_levels(completed_weekly)
    weekly_resistance = _rolling_resistance_levels(completed_weekly)
    daily_support = _rolling_support_levels(completed_daily)
    daily_resistance = _rolling_resistance_levels(completed_daily)
    weekly_breakout = _breakout_level(completed_weekly)
    daily_breakout = _breakout_level(completed_daily)
    weekly_invalidation = _invalidation_level(completed_weekly)
    daily_invalidation = _invalidation_level(completed_daily)
    alignment = _classify_alignment(completed_weekly, completed_daily)
    feature_values: dict[str, float] = {}
    feature_versions: dict[str, str] = {}
    model_versions: dict[str, str] = {}
    warnings: list[str] = []
    for snapshot in feature_snapshots:
        group_name = str(snapshot.get("group_name", "")).strip().lower()
        values = snapshot.get("feature_values") or {}
        weight = float(snapshot.get("approved_weight", 0.0))
        if not group_name:
            continue
        feature_values[group_name] = 0.0
        feature_versions[group_name] = str(snapshot.get("version") or "unknown")
        if weight <= 0.0:
            warnings.append(f"unvalidated feature group {group_name} is visible but cannot influence allocation")
            continue
        for key, value in values.items():
            feature_values[key] = float(value)
    if not feature_values:
        feature_values = {}
    probability_estimate = None
    expected_upside_pct = None
    expected_downside_pct = None
    expected_holding_days = None
    estimated_cost_bps = None
    calibration_status = "UNCALIBRATED"
    expected_value_score = 0.0
    if latest_daily is not None:
        close_price = latest_daily.close
    else:
        close_price = 0.0
    return Opportunity(
        opportunity_id=f"{symbol}-{observation_time.strftime('%Y%m%d%H%M%S')}",
        security_id=security_id,
        symbol=symbol,
        observation_time=observation_time,
        data_available_through=observation_time,
        universe_snapshot_id=universe_snapshot_id,
        benchmark_symbol=benchmark_symbol,
        sector=sector,
        industry=industry,
        market_regime="neutral",
        sector_regime="neutral",
        weekly_trend_state="bullish" if latest_weekly and latest_weekly.close >= latest_weekly.open else "bearish",
        weekly_range_position=0.5,
        weekly_support_levels=tuple(weekly_support),
        weekly_resistance_levels=tuple(weekly_resistance),
        weekly_breakout_level=weekly_breakout,
        weekly_invalidation_level=weekly_invalidation,
        weekly_volatility_state="neutral",
        weekly_relative_strength=1.0,
        weekly_structure_quality=0.5,
        daily_trend_state="bullish" if latest_daily and latest_daily.close >= latest_daily.open else "bearish",
        daily_range_position=0.5,
        daily_support_levels=tuple(daily_support),
        daily_resistance_levels=tuple(daily_resistance),
        daily_breakout_level=daily_breakout,
        daily_invalidation_level=daily_invalidation,
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
        multi_timeframe_alignment=alignment,
        close_price=close_price,
        average_daily_dollar_volume=1_000_000.0,
        average_daily_volume=1000.0,
        spread_estimate_bps=1.0,
        atr_pct=0.02,
        capacity_warning=False,
        known_catalysts=tuple(known_events),
        next_known_event_time=None,
        catalyst_risk="low",
        event_data_available_at=observation_time,
        probability_estimate=probability_estimate,
        expected_upside_pct=expected_upside_pct,
        expected_downside_pct=expected_downside_pct,
        expected_holding_days=expected_holding_days,
        estimated_cost_bps=estimated_cost_bps,
        uncertainty_score=0.5,
        calibration_status=calibration_status,
        expected_value_score=expected_value_score,
        opportunity_cost_rank=None,
        correlation_bucket="medium",
        concentration_bucket="moderate",
        current_position_weight=0.0,
        primary_invalidation_price=0.0,
        thesis_invalidation_reasons=tuple(),
        liquidity_risk="low",
        gap_risk="low",
        model_disagreement=False,
        governance_eligible=True,
        risk_eligible=True,
        feature_values=feature_values,
        feature_versions=feature_versions,
        model_versions=model_versions,
        warehouse_manifest_hash=warehouse_manifest_hash,
        dataset_manifest_hash=dataset_manifest_hash,
        source_record_ids=tuple(source_record_ids),
        warnings=tuple(warnings),
        created_at=datetime.now(timezone.utc),
    )


def _rolling_support_levels(bars: list[Bar]) -> list[dict[str, Any]]:
    if not bars:
        return []
    recent = bars[-min(len(bars), 10):]
    low = min(bar.low for bar in recent)
    return [{"level": low, "provenance": "rolling_low", "window": len(recent)}]


def _rolling_resistance_levels(bars: list[Bar]) -> list[dict[str, Any]]:
    if not bars:
        return []
    recent = bars[-min(len(bars), 10):]
    high = max(bar.high for bar in recent)
    return [{"level": high, "provenance": "rolling_high", "window": len(recent)}]


def _breakout_level(bars: list[Bar]) -> float:
    if not bars:
        return 0.0
    return max(bar.high for bar in bars[-min(len(bars), 5):])


def _invalidation_level(bars: list[Bar]) -> float:
    if not bars:
        return 0.0
    return min(bar.low for bar in bars[-min(len(bars), 5):])


def _classify_alignment(weekly_bars: list[Bar], daily_bars: list[Bar]) -> str:
    if not weekly_bars or not daily_bars:
        return "INSUFFICIENT_DATA"
    if len(weekly_bars) < 2 or len(daily_bars) < 2:
        return "INSUFFICIENT_DATA"
    weekly_change = weekly_bars[-1].close - weekly_bars[-2].close
    daily_change = daily_bars[-1].close - daily_bars[-2].close
    if weekly_change > 0 and daily_change > 0:
        return "ALIGNED_BULLISH"
    if weekly_change > 0 and daily_change < 0:
        return "WEEKLY_BULLISH_DAILY_PULLBACK"
    if weekly_change < 0 and daily_change > 0:
        return "WEEKLY_NEUTRAL_DAILY_BREAKOUT"
    return "CONFLICTED"
