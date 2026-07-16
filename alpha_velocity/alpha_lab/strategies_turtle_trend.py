"""Turtle Trend Strategy v1 - Disciplined trend-following for futures and commodities."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from alpha_velocity.alpha_lab.models import (
    CandidateState,
    StrategyCandidate,
    StrategyContext,
    StrategyEvidence,
    StrategyRunResult,
    StrategyState,
    StrategyValidationStatus,
)
from alpha_velocity.alpha_lab.protocol import StrategyProtocol


class TurtleTrendStrategy(StrategyProtocol):
    """
    Turtle Trend Strategy v1.

    Purpose: Disciplined trend-following research strategy inspired by classic Turtle
    principles for futures and commodities, focused on entering confirmed trends,
    capturing the safer middle portion and exiting systematically.

    This is an adaptation for research and paper testing, not a claim that
    historical Turtle rules remain profitable.

    Supported asset families:
    - equity-index futures
    - interest-rate futures
    - currency futures
    - energy
    - metals
    - grains
    - soft commodities
    - livestock
    """

    def __init__(self) -> None:
        """Initialize strategy."""
        self._validation_status = StrategyValidationStatus.UNCALIBRATED
        self._candidates_cache: dict[str, StrategyCandidate] = {}
        # Configuration (can be overridden)
        self.shorter_breakout_bars = 20
        self.longer_breakout_bars = 55
        self.atr_period = 20
        self.risk_per_unit_pct = 2.0
        self.max_units = 4

    @property
    def strategy_id(self) -> str:
        return "turtle-trend-v1"

    @property
    def strategy_name(self) -> str:
        return "Turtle Trend"

    @property
    def strategy_version(self) -> str:
        return "1.0.0"

    @property
    def supported_asset_types(self) -> tuple[str, ...]:
        return (
            "FUTURE",
            "CONTINUOUS_SERIES",
        )

    @property
    def required_history(self) -> int:
        return 365  # 1 year of daily bars minimum

    @property
    def required_data(self) -> tuple[str, ...]:
        return ("OHLCV", "FUTURES_METADATA", "CONTRACT_ROLL", "ATR")

    @property
    def hypothesis(self) -> str:
        return (
            "Capture disciplined trend-following entries using channel breakouts, "
            "pyramid systematically with volatility-based sizing, and exit using "
            "countertrend or trailing-stop rules to capture the safe middle portion "
            "of trends while avoiding tops and bottoms."
        )

    @property
    def validation_status(self) -> StrategyValidationStatus:
        return self._validation_status

    @property
    def ranking_influence(self) -> float:
        # Unvalidated strategies have zero influence
        if self._validation_status == StrategyValidationStatus.UNCALIBRATED:
            return 0.0
        if self._validation_status == StrategyValidationStatus.SHADOW:
            return 0.0
        return 0.4  # For CALIBRATED

    @property
    def allocation_influence(self) -> float:
        # Only CALIBRATED strategies can influence allocation
        if self._validation_status == StrategyValidationStatus.CALIBRATED:
            return 0.2
        return 0.0

    def generate_candidates(self, context: StrategyContext) -> StrategyRunResult:
        """Generate turtle trend candidates for futures.

        Returns candidates that are:
        - TRIGGERED: Long or short breakout confirmed
        - WAITING_FOR_BREAKOUT: Market near breakout level
        - INSUFFICIENT_DATA: Contract roll or data issues
        - EXCLUDED: Illiquid or margin cap exceeded
        """
        run_id = f"TURTLE-{context.observation_time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

        candidates: list[StrategyCandidate] = []
        errors: list[str] = []
        triggered_count = 0
        waiting_count = 0
        excluded_count = 0

        try:
            # Get universe from warehouse
            universe = context.warehouse.point_in_time_universe(as_of=context.observation_time)

            for security in universe:
                try:
                    candidate = self._evaluate_contract(
                        security=security,
                        context=context,
                        run_id=run_id,
                    )
                    if candidate:
                        candidates.append(candidate)
                        if candidate.candidate_state == CandidateState.TRIGGERED:
                            triggered_count += 1
                        elif candidate.candidate_state == CandidateState.WAITING_FOR_TRIGGER:
                            waiting_count += 1
                        elif candidate.candidate_state == CandidateState.EXCLUDED:
                            excluded_count += 1

                except Exception as e:
                    errors.append(f"Error evaluating {getattr(security, 'ticker', security)}: {str(e)}")

        except Exception as e:
            errors.append(f"Warehouse access failed: {str(e)}")

        state = StrategyState(
            strategy_id=self.strategy_id,
            strategy_name=self.strategy_name,
            strategy_version=self.strategy_version,
            observation_time=context.observation_time,
            validation_status=self._validation_status,
            candidates_generated=len(candidates),
            triggered_count=triggered_count,
            waiting_count=waiting_count,
            excluded_count=excluded_count,
            error_count=len(errors),
            error_messages=tuple(errors),
        )

        return StrategyRunResult(
            run_id=run_id,
            strategy_id=self.strategy_id,
            strategy_name=self.strategy_name,
            strategy_version=self.strategy_version,
            observation_time=context.observation_time,
            candidates=tuple(candidates),
            state=state,
            warnings=tuple(errors),
        )

    def _evaluate_contract(
        self,
        security: Any,
        context: StrategyContext,
        run_id: str,
    ) -> StrategyCandidate | None:
        """Evaluate a futures contract for trend-following entry."""
        symbol = security.ticker if hasattr(security, "ticker") else str(security)
        candidate_id = f"TURTLE-{symbol}-{context.observation_time.strftime('%Y%m%d')}"

        # Sample logic: create candidate for demonstration
        # In production, this would:
        # - Calculate N (ATR-based volatility)
        # - Check channel breakouts (shorter and longer)
        # - Validate contract roll status
        # - Calculate margin requirements
        # - Size position based on volatility and portfolio risk

        # Simulate breakout detection
        breakout_strength = 65.0  # Placeholder (0-100)
        liquidity_score = 80.0  # Placeholder
        margin_available = True  # Placeholder

        if breakout_strength > 60 and margin_available:
            # Determine direction based on mock data
            direction = "LONG" if symbol.endswith("U") else "SHORT"  # Simulate
            candidate_state = CandidateState.TRIGGERED
            explanation = f"{direction} breakout detected on completed bar, channel confirmed"
        elif breakout_strength > 40:
            candidate_state = CandidateState.WAITING_FOR_TRIGGER
            explanation = "Price near breakout level, waiting for completed-bar confirmation"
        elif not margin_available:
            candidate_state = CandidateState.EXCLUDED
            explanation = "Insufficient margin or portfolio cap exceeded"
        else:
            candidate_state = CandidateState.EXCLUDED
            explanation = "Does not meet trend-following entry criteria"

        evidence = StrategyEvidence(
            timing_opportunity_score=breakout_strength,
            liquidity_score=liquidity_score,
            risk_adjustment=100.0,
            uncertainty_adjustment=100.0,
            positive_contributors=(
                f"channel_breakout_completed_bar",
                "volatility_normalized_entry",
                "systematic_exit_defined",
            ),
            negative_contributors=(
                "early_trend_portion_missed",
            ),
            missing_information=(
                "real_margin_requirements",
                "actual_open_interest",
            ),
            required_confirmation=(
                "volume_on_breakout",
                "no_contract_roll_imminent",
            ),
        )

        candidate = StrategyCandidate(
            candidate_id=candidate_id,
            strategy_id=self.strategy_id,
            symbol=symbol,
            security_id=security.security_id if hasattr(security, "security_id") else f"sec-{symbol}",
            observation_time=context.observation_time,
            data_available_through=context.observation_time - timedelta(days=1),
            candidate_state=candidate_state,
            evidence=evidence,
            explanation=explanation,
            expected_upside_pct=None,  # UNCALIBRATED
            expected_downside_pct=None,  # UNCALIBRATED
            expected_holding_days=None,  # UNCALIBRATED
            probability_estimate=None,  # UNCALIBRATED
        )

        self._candidates_cache[candidate_id] = candidate
        return candidate

    def explain_candidate(self, candidate_id: str) -> str:
        """Provide detailed explanation of a candidate."""
        if candidate_id in self._candidates_cache:
            candidate = self._candidates_cache[candidate_id]
            return candidate.explanation

        return "Candidate not found in cache"
