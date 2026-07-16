"""Scoring logic for opportunity ranking components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from alpha_velocity.opportunity import Opportunity


@dataclass
class ScoringResult:
    """Result of a scoring component."""

    score: float  # 0-100
    contributors: list[str]
    detractors: list[str]
    warnings: list[str]
    missing: list[str]
    details: dict[str, Any]


class IntrinsicScorer:
    """Scores valuation and capital structure aspects."""

    @staticmethod
    def score(opp: Opportunity) -> ScoringResult:
        """
        Score intrinsic opportunity: valuation gap + capital structure.
        
        Measures:
        - Expectation gap (expected upside)
        - Capital structure health (concentration risk)
        - Industry/sector outlook
        - Company fundamentals
        """
        score = 50.0  # Base neutral
        contributors = []
        detractors = []
        warnings = []
        missing = []
        details = {}

        # Expected upside is primary intrinsic indicator
        if opp.expected_upside_pct is not None:
            upside = opp.expected_upside_pct
            if upside >= 50:
                contributors.append(f"Strong expected upside ({upside:.1f}%)")
                score = min(100, 50 + (upside / 50) * 25)
            elif upside >= 20:
                contributors.append(f"Moderate expected upside ({upside:.1f}%)")
                score = min(100, 50 + (upside / 20) * 15)
            elif upside >= 0:
                contributors.append(f"Small expected upside ({upside:.1f}%)")
                score = min(100, 50 + (upside / 20) * 5)
            else:
                detractors.append(f"Negative expected upside ({upside:.1f}%)")
                score = max(0, 50 + upside)
            details["expected_upside_pct"] = upside
        else:
            missing.append("Expected upside percentage not available")

        # Expected downside indicates risk
        if opp.expected_downside_pct is not None:
            downside = abs(opp.expected_downside_pct)
            if downside > 30:
                detractors.append(f"Large expected downside ({downside:.1f}%)")
                score *= 0.8
            elif downside > 15:
                warnings.append(f"Moderate expected downside ({downside:.1f}%)")
                score *= 0.9
            details["expected_downside_pct"] = downside
        else:
            missing.append("Expected downside not available")

        # Concentration bucket indicates capital concentration risk
        if opp.concentration_bucket:
            if opp.concentration_bucket == "LOW":
                contributors.append("Low concentration risk")
                score *= 1.05
            elif opp.concentration_bucket == "MEDIUM":
                score = score  # Neutral
            elif opp.concentration_bucket in ("HIGH", "CRITICAL"):
                detractors.append(f"High concentration risk ({opp.concentration_bucket})")
                score *= 0.7
            details["concentration_bucket"] = opp.concentration_bucket

        # Sector and industry outlook
        if opp.sector_regime and opp.market_regime:
            if opp.sector_regime == "FAVORABLE" and opp.market_regime == "EXPANSION":
                contributors.append("Favorable sector in expansion regime")
                score = min(100, score + 5)
            elif opp.sector_regime == "UNFAVORABLE":
                detractors.append(f"Unfavorable sector ({opp.sector_regime})")
                score *= 0.85
            details["sector_regime"] = opp.sector_regime
            details["market_regime"] = opp.market_regime

        # Clamp to 0-100
        score = max(0, min(100, score))

        return ScoringResult(
            score=score,
            contributors=contributors,
            detractors=detractors,
            warnings=warnings,
            missing=missing,
            details=details,
        )


class TimingScorer:
    """Scores technical setup and catalyst timing."""

    @staticmethod
    def score(opp: Opportunity) -> ScoringResult:
        """
        Score timing opportunity: trigger state + multi-timeframe alignment.
        
        Measures:
        - Daily trigger state (triggered/confirmed/forming/none)
        - Multi-timeframe alignment (ALIGNED/FORMING/DIVERGENT)
        - Breakout distance and invalidation proximity
        - Volatility contraction/expansion
        - Catalyst timing
        """
        score = 50.0  # Base neutral
        contributors = []
        detractors = []
        warnings = []
        missing = []
        details = {}

        # Trigger state is most important timing signal
        trigger_state = opp.trigger_state.upper() if opp.trigger_state else "NONE"
        if trigger_state == "TRIGGERED":
            contributors.append("Daily trigger confirmed")
            score = min(100, 50 + 30)
        elif trigger_state == "CONFIRMED":
            contributors.append("Daily trigger confirmed")
            score = min(100, 50 + 25)
        elif trigger_state == "FORMING":
            warnings.append("Daily trigger forming (not yet triggered)")
            score = max(0, 50 - 10)
        else:
            detractors.append(f"No daily trigger ({trigger_state})")
            score = max(0, 50 - 30)
        details["trigger_state"] = trigger_state

        # Multi-timeframe alignment is critical
        alignment = opp.multi_timeframe_alignment.upper() if opp.multi_timeframe_alignment else "DIVERGENT"
        if alignment == "ALIGNED":
            contributors.append("Multi-timeframe alignment confirmed")
            score = min(100, score + 15)
        elif alignment == "FORMING":
            warnings.append("Multi-timeframe alignment forming")
            score = max(0, score - 5)
        else:
            detractors.append(f"Multi-timeframe divergence ({alignment})")
            score = max(0, score - 20)
        details["multi_timeframe_alignment"] = alignment

        # Setup quality
        if opp.daily_structure_quality is not None:
            quality = opp.daily_structure_quality
            if quality >= 75:
                contributors.append(f"High-quality daily setup ({quality:.0f}%)")
                score = min(100, score + 10)
            elif quality >= 50:
                score = score  # Neutral
            else:
                detractors.append(f"Poor daily setup quality ({quality:.0f}%)")
                score = max(0, score - 10)
            details["daily_structure_quality"] = quality

        # Distance to invalidation
        if opp.daily_invalidation_level > 0 and opp.close_price > 0:
            distance_to_invalidation_pct = abs(opp.close_price - opp.daily_invalidation_level) / opp.close_price * 100
            if distance_to_invalidation_pct >= 10:
                contributors.append(f"Setup not at risk of immediate invalidation ({distance_to_invalidation_pct:.1f}%)")
                score = min(100, score + 5)
            elif distance_to_invalidation_pct >= 5:
                warnings.append(f"Setup near invalidation ({distance_to_invalidation_pct:.1f}%)")
                score = max(0, score - 5)
            else:
                detractors.append(f"Setup at extreme invalidation risk ({distance_to_invalidation_pct:.1f}%)")
                score = max(0, score - 15)
            details["distance_to_invalidation_pct"] = distance_to_invalidation_pct

        # Volatility state
        if opp.daily_volatility_state:
            vol_state = opp.daily_volatility_state.upper()
            if vol_state in ("CONTRACTION", "SUPPRESSED"):
                contributors.append("Volatility suppressed (potential breakout setup)")
                score = min(100, score + 8)
            elif vol_state in ("EXPANSION", "ELEVATED"):
                warnings.append(f"Volatility elevated ({vol_state})")
                score = max(0, score - 5)
            details["daily_volatility_state"] = vol_state

        # Relative volume
        if opp.relative_volume is not None:
            rel_vol = opp.relative_volume
            if rel_vol >= 1.3:
                contributors.append(f"Elevated relative volume ({rel_vol:.2f}x)")
                score = min(100, score + 5)
            elif rel_vol >= 1.0:
                score = score  # Neutral
            else:
                detractors.append(f"Below-average volume ({rel_vol:.2f}x)")
                score = max(0, score - 8)
            details["relative_volume"] = rel_vol

        # Catalyst timing (if upcoming known catalyst)
        if opp.known_catalysts and len(opp.known_catalysts) > 0:
            next_catalyst_str = "Known catalyst upcoming"
            for cat in opp.known_catalysts:
                if isinstance(cat, Mapping) and cat.get("importance") in ("HIGH", "TRANSFORMATIONAL"):
                    contributors.append(f"{next_catalyst_str} ({cat.get('type', 'unknown')})")
                    score = min(100, score + 10)
                    break
            details["has_catalysts"] = True
        else:
            details["has_catalysts"] = False

        # Clamp to 0-100
        score = max(0, min(100, score))

        return ScoringResult(
            score=score,
            contributors=contributors,
            detractors=detractors,
            warnings=warnings,
            missing=missing,
            details=details,
        )


class SwingValueScorer:
    """Scores expected swing value: probability × magnitude × factors."""

    @staticmethod
    def score(opp: Opportunity) -> ScoringResult:
        """
        Score expected swing value: the core ranking factor.
        
        Measures:
        - Calibrated probability (if available)
        - Expected magnitude (upside - downside)
        - Expected holding period optimization
        - Execution costs and liquidity
        - Uncertainty and confidence
        
        Swing Value = Probability × Magnitude × Time_Factor × Liquidity × (1 - Uncertainty)
        """
        score = 50.0  # Base neutral
        contributors = []
        detractors = []
        warnings = []
        missing = []
        details = {}

        # Probability is critical but must be calibrated
        probability = 0.5  # Default neutral
        is_calibrated = opp.calibration_status == "CALIBRATED"

        if opp.probability_estimate is not None and is_calibrated:
            probability = min(1.0, max(0.0, opp.probability_estimate))
            if probability >= 0.7:
                contributors.append(f"High calibrated probability ({probability*100:.0f}%)")
                score = min(100, 50 + (probability - 0.5) * 100)
            elif probability >= 0.5:
                contributors.append(f"Fair calibrated probability ({probability*100:.0f}%)")
                score = min(100, 50 + (probability - 0.5) * 50)
            elif probability >= 0.3:
                detractors.append(f"Low calibrated probability ({probability*100:.0f}%)")
                score = max(0, 50 + (probability - 0.5) * 50)
            else:
                detractors.append(f"Very low calibrated probability ({probability*100:.0f}%)")
                score = max(0, 50 + (probability - 0.5) * 100)
            details["calibrated_probability"] = probability
        elif opp.probability_estimate is not None and not is_calibrated:
            # Uncalibrated probability gets warning but is not excluded
            warnings.append("Probability estimate is uncalibrated; using neutral 50% for swing calculation")
            details["uncalibrated_probability"] = opp.probability_estimate
            details["note"] = "probability fabrication prevented; using neutral assumption"
        else:
            missing.append("No probability estimate available")
            warnings.append("Using neutral 50% probability assumption (not fabricated)")

        # Expected magnitude (upside relative to downside)
        magnitude = 0.0
        if opp.expected_upside_pct is not None and opp.expected_downside_pct is not None:
            upside = opp.expected_upside_pct
            downside = abs(opp.expected_downside_pct)
            magnitude = upside - downside
            if magnitude >= 50:
                contributors.append(f"Large expected swing ({magnitude:.1f}%)")
                score = min(100, score + (magnitude / 50) * 20)
            elif magnitude >= 20:
                contributors.append(f"Moderate expected swing ({magnitude:.1f}%)")
                score = min(100, score + 10)
            elif magnitude >= 0:
                detractors.append(f"Small expected swing ({magnitude:.1f}%)")
                score = max(0, score - 5)
            else:
                detractors.append(f"Negative expected swing ({magnitude:.1f}%)")
                score = max(0, score - 20)
            details["expected_swing_pct"] = magnitude
        else:
            missing.append("Expected upside/downside not fully available")

        # Holding period optimization (5-20 days is ideal)
        if opp.expected_holding_days is not None:
            holding_days = opp.expected_holding_days
            if 5 <= holding_days <= 20:
                contributors.append(f"Optimal holding period ({holding_days:.0f} days)")
                score = min(100, score + 10)
            elif 3 <= holding_days < 5:
                warnings.append(f"Short holding period ({holding_days:.0f} days)")
                score = max(0, score - 5)
            elif holding_days > 20:
                detractors.append(f"Long holding period ({holding_days:.0f} days)")
                score = max(0, score - 10)
            details["expected_holding_days"] = holding_days
        else:
            missing.append("Expected holding period not specified")

        # Liquidity and execution costs
        if opp.estimated_cost_bps is not None:
            cost_bps = opp.estimated_cost_bps
            if cost_bps <= 5:
                contributors.append(f"Low execution costs ({cost_bps:.0f} bps)")
                score = min(100, score + 5)
            elif cost_bps <= 15:
                score = score  # Neutral
            elif cost_bps <= 30:
                warnings.append(f"Elevated execution costs ({cost_bps:.0f} bps)")
                score = max(0, score - 5)
            else:
                detractors.append(f"High execution costs ({cost_bps:.0f} bps)")
                score = max(0, score - 10)
            details["estimated_cost_bps"] = cost_bps
        else:
            missing.append("Estimated execution cost not available")

        # Liquidity bucket
        if opp.liquidity_risk and opp.liquidity_risk.upper() in ("HIGH", "EXTREME"):
            detractors.append(f"Liquidity risk: {opp.liquidity_risk}")
            score = max(0, score - 15)
            details["liquidity_risk"] = opp.liquidity_risk
        elif opp.average_daily_dollar_volume is not None:
            if opp.average_daily_dollar_volume >= 10_000_000:
                contributors.append(f"High liquidity (${opp.average_daily_dollar_volume/1_000_000:.0f}M ADVI)")
                score = min(100, score + 5)
            details["average_daily_dollar_volume"] = opp.average_daily_dollar_volume

        # Uncertainty score (0 = high certainty, 1 = high uncertainty)
        if opp.uncertainty_score is not None:
            uncertainty = opp.uncertainty_score
            if uncertainty <= 0.3:
                contributors.append(f"Low uncertainty ({uncertainty:.0%})")
                score = min(100, score + 10)
            elif uncertainty <= 0.6:
                score = score  # Neutral
            else:
                warnings.append(f"High uncertainty ({uncertainty:.0%})")
                score = max(0, score - (uncertainty - 0.6) * 50)
            details["uncertainty_score"] = uncertainty

        # Clamp to 0-100
        score = max(0, min(100, score))

        return ScoringResult(
            score=score,
            contributors=contributors,
            detractors=detractors,
            warnings=warnings,
            missing=missing,
            details=details,
        )


class CapitalStructureScorer:
    """Scores capital structure and refinancing risk."""

    @staticmethod
    def score(opp: Opportunity) -> ScoringResult:
        """Score capital structure health."""
        score = 50.0
        contributors = []
        detractors = []
        warnings = []
        missing = []
        details = {}

        # Concentration and sector concentration indicate capital structure concerns
        if opp.concentration_bucket:
            if opp.concentration_bucket == "LOW":
                contributors.append("Low capital concentration")
            elif opp.concentration_bucket in ("HIGH", "CRITICAL"):
                detractors.append(f"High capital concentration ({opp.concentration_bucket})")
                score *= 0.7
            details["concentration_bucket"] = opp.concentration_bucket

        return ScoringResult(
            score=score,
            contributors=contributors,
            detractors=detractors,
            warnings=warnings,
            missing=missing,
            details=details,
        )


class LiquidityScorer:
    """Scores liquidity and execution feasibility."""

    @staticmethod
    def score(opp: Opportunity) -> ScoringResult:
        """Score liquidity and execution."""
        score = 50.0
        contributors = []
        detractors = []
        warnings = []
        missing = []
        details = {}

        # Average daily dollar volume
        if opp.average_daily_dollar_volume is not None:
            advi = opp.average_daily_dollar_volume
            if advi >= 50_000_000:
                contributors.append(f"Excellent liquidity (${advi/1_000_000:.0f}M ADVI)")
                score = min(100, 50 + 30)
            elif advi >= 10_000_000:
                contributors.append(f"Good liquidity (${advi/1_000_000:.0f}M ADVI)")
                score = min(100, 50 + 15)
            elif advi >= 1_000_000:
                score = max(0, 50 - 10)
            else:
                detractors.append(f"Poor liquidity (${advi/1_000_000:.0f}M ADVI)")
                score = max(0, 50 - 30)
            details["average_daily_dollar_volume"] = advi
        else:
            missing.append("Average daily volume not available")

        # Spread estimate
        if opp.spread_estimate_bps is not None:
            spread = opp.spread_estimate_bps
            if spread <= 5:
                contributors.append(f"Tight spread ({spread:.0f} bps)")
                score = min(100, score + 10)
            elif spread <= 15:
                score = score
            else:
                detractors.append(f"Wide spread ({spread:.0f} bps)")
                score = max(0, score - 10)
            details["spread_estimate_bps"] = spread

        return ScoringResult(
            score=score,
            contributors=contributors,
            detractors=detractors,
            warnings=warnings,
            missing=missing,
            details=details,
        )


class CatalystScorer:
    """Scores known catalysts and event timing."""

    @staticmethod
    def score(opp: Opportunity) -> ScoringResult:
        """Score catalyst quality and timing."""
        score = 50.0
        contributors = []
        detractors = []
        warnings = []
        missing = []
        details = {}

        if opp.known_catalysts and len(opp.known_catalysts) > 0:
            catalysts_count = len(opp.known_catalysts)
            details["catalysts_count"] = catalysts_count
            
            for cat in opp.known_catalysts:
                if isinstance(cat, Mapping):
                    importance = cat.get("importance", "LOW").upper()
                    cat_type = cat.get("type", "unknown")
                    
                    if importance == "TRANSFORMATIONAL":
                        contributors.append(f"Transformational catalyst ({cat_type})")
                        score = min(100, score + 20)
                    elif importance == "HIGH":
                        contributors.append(f"High-impact catalyst ({cat_type})")
                        score = min(100, score + 10)
                    elif importance == "MEDIUM":
                        score += 5
            
            if catalysts_count > 1:
                contributors.append(f"Multiple catalysts ({catalysts_count})")
                score = min(100, score + 5)
        else:
            warnings.append("No known catalysts")
            details["catalysts_count"] = 0

        # Catalyst risk
        if opp.catalyst_risk and opp.catalyst_risk.upper() in ("HIGH", "EXTREME"):
            detractors.append(f"Catalyst execution risk: {opp.catalyst_risk}")
            score = max(0, score - 10)
            details["catalyst_risk"] = opp.catalyst_risk

        return ScoringResult(
            score=max(0, min(100, score)),
            contributors=contributors,
            detractors=detractors,
            warnings=warnings,
            missing=missing,
            details=details,
        )


class TechnicalScorer:
    """Scores technical setup quality."""

    @staticmethod
    def score(opp: Opportunity) -> ScoringResult:
        """Score technical analysis."""
        score = 50.0
        contributors = []
        detractors = []
        warnings = []
        missing = []
        details = {}

        # Weekly structure
        if opp.weekly_structure_quality is not None:
            quality = opp.weekly_structure_quality
            if quality >= 75:
                contributors.append(f"High-quality weekly structure ({quality:.0f}%)")
                score = min(100, score + 10)
            elif quality < 50:
                detractors.append(f"Poor weekly structure ({quality:.0f}%)")
                score = max(0, score - 10)
            details["weekly_structure_quality"] = quality

        # Daily structure
        if opp.daily_structure_quality is not None:
            quality = opp.daily_structure_quality
            if quality >= 75:
                contributors.append(f"High-quality daily structure ({quality:.0f}%)")
                score = min(100, score + 10)
            elif quality < 50:
                detractors.append(f"Poor daily structure ({quality:.0f}%)")
                score = max(0, score - 10)
            details["daily_structure_quality"] = quality

        # Relative strength
        if opp.daily_relative_strength is not None:
            rs = opp.daily_relative_strength
            if rs >= 70:
                contributors.append(f"Strong relative strength ({rs:.0f}%)")
                score = min(100, score + 10)
            elif rs < 30:
                detractors.append(f"Weak relative strength ({rs:.0f}%)")
                score = max(0, score - 10)
            details["daily_relative_strength"] = rs

        return ScoringResult(
            score=max(0, min(100, score)),
            contributors=contributors,
            detractors=detractors,
            warnings=warnings,
            missing=missing,
            details=details,
        )
