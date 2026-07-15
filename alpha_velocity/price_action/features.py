from __future__ import annotations

from statistics import mean

from alpha_velocity.market.bars import Bar
from alpha_velocity.price_action.models import PriceActionSnapshot


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe_div(num: float, den: float) -> float:
    return 0.0 if den == 0 else num / den


def _true_ranges(bars: list[Bar]) -> list[float]:
    values: list[float] = []
    for previous, current in zip(bars[:-1], bars[1:]):
        values.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    return values


def compute_price_action_snapshot(bars: list[Bar]) -> PriceActionSnapshot:
    """Compute transparent structure features from finalized bars only.

    The output is evidence, not a forecast. No feature is permitted to receive
    portfolio weight until a separate out-of-sample validation artifact approves it.
    """
    if len(bars) < 80:
        raise ValueError("At least 80 finalized daily bars are required.")

    last = bars[-1]
    previous = bars[-2]
    closes = [bar.close for bar in bars]
    volumes = [max(0.0, bar.volume) for bar in bars]

    one_day_range = max(last.high - last.low, 1e-12)
    close_location = _clip((last.close - last.low) / one_day_range)

    low20 = min(bar.low for bar in bars[-20:])
    high20 = max(bar.high for bar in bars[-20:])
    low60 = min(bar.low for bar in bars[-60:])
    high60 = max(bar.high for bar in bars[-60:])
    range_position_20 = _clip(_safe_div(last.close - low20, high20 - low20))
    range_position_60 = _clip(_safe_div(last.close - low60, high60 - low60))

    ma10 = mean(closes[-10:])
    ma20 = mean(closes[-20:])
    ma50 = mean(closes[-50:])
    higher_highs = sum(
        1 for earlier, later in zip(bars[-10:-1], bars[-9:]) if later.high > earlier.high
    ) / 9.0
    higher_lows = sum(
        1 for earlier, later in zip(bars[-10:-1], bars[-9:]) if later.low > earlier.low
    ) / 9.0
    trend_alignment = mean(
        [
            1.0 if last.close > ma10 else 0.0,
            1.0 if ma10 > ma20 else 0.0,
            1.0 if ma20 > ma50 else 0.0,
            higher_highs,
            higher_lows,
        ]
    )

    true_ranges = _true_ranges(bars[-61:])
    atr5 = mean(true_ranges[-5:])
    atr20 = mean(true_ranges[-20:])
    atr60 = mean(true_ranges[-60:])
    compression_ratio = _clip(_safe_div(atr5, atr20), 0.0, 3.0)
    expansion_ratio = _clip(_safe_div(atr5, atr60), 0.0, 3.0)

    gap_pct = _safe_div(last.open, previous.close) - 1.0
    prior_high20 = max(bar.high for bar in bars[-21:-1])
    prior_low20 = min(bar.low for bar in bars[-21:-1])
    breakout_distance = _safe_div(last.close, prior_high20) - 1.0
    breakdown_distance = _safe_div(last.close, prior_low20) - 1.0

    failed_breakout = last.high > prior_high20 and last.close < prior_high20
    failed_breakdown = last.low < prior_low20 and last.close > prior_low20

    support_distance = _safe_div(last.close, low60) - 1.0
    resistance_distance = _safe_div(high60, last.close) - 1.0
    average_volume = mean(volumes[-21:-1]) or 1.0
    relative_volume = volumes[-1] / average_volume

    signed_volume = []
    for bar in bars[-20:]:
        location = _clip(_safe_div(bar.close - bar.low, max(bar.high - bar.low, 1e-12)))
        signed_volume.append((2.0 * location - 1.0) * bar.volume)
    total_volume = sum(bar.volume for bar in bars[-20:]) or 1.0
    flow = sum(signed_volume) / total_volume
    accumulation = _clip((flow + 1.0) / 2.0)
    distribution = _clip((1.0 - flow) / 2.0)

    compression_quality = 1.0 - _clip(compression_ratio / 1.25)
    breakout_quality = _clip(0.5 + breakout_distance * 20.0)
    failure_quality = 1.0 if failed_breakdown else 0.0
    location_quality = mean([close_location, range_position_20, range_position_60])
    volume_quality = _clip(relative_volume / 2.0)

    evidence = 100.0 * mean(
        [
            trend_alignment,
            compression_quality,
            breakout_quality,
            failure_quality,
            location_quality,
            volume_quality,
            accumulation,
        ]
    )

    # Conservative structural invalidation: lowest low of the last ten finalized bars.
    invalidation = min(bar.low for bar in bars[-10:])

    features = {
        "close_location_1d": close_location,
        "range_position_20d": range_position_20,
        "range_position_60d": range_position_60,
        "trend_structure": trend_alignment,
        "compression_ratio": compression_ratio,
        "expansion_ratio": expansion_ratio,
        "gap_pct": gap_pct,
        "breakout_distance_20d": breakout_distance,
        "breakdown_distance_20d": breakdown_distance,
        "support_distance_60d": support_distance,
        "resistance_distance_60d": resistance_distance,
        "relative_volume": relative_volume,
        "accumulation_score": accumulation,
        "distribution_score": distribution,
    }

    return PriceActionSnapshot(
        close_location_1d=close_location,
        range_position_20d=range_position_20,
        range_position_60d=range_position_60,
        trend_structure=trend_alignment,
        compression_ratio=compression_ratio,
        expansion_ratio=expansion_ratio,
        gap_pct=gap_pct,
        breakout_distance_20d=breakout_distance,
        breakdown_distance_20d=breakdown_distance,
        failed_breakout=failed_breakout,
        failed_breakdown=failed_breakdown,
        support_distance_60d=support_distance,
        resistance_distance_60d=resistance_distance,
        relative_volume=relative_volume,
        accumulation_score=accumulation,
        distribution_score=distribution,
        evidence_score=max(0.0, min(100.0, evidence)),
        invalidation_price=invalidation,
        feature_values=features,
    )
