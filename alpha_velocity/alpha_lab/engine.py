"""Alpha Lab Engine - Strategy orchestration and candidate aggregation."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from alpha_velocity.alpha_lab.models import (
    CandidateState,
    StrategyCandidate,
    StrategyContext,
    StrategyRunResult,
    StrategyValidationStatus,
)
from alpha_velocity.alpha_lab.protocol import StrategyProtocol
from alpha_velocity.opportunity import Opportunity
from alpha_velocity.warehouse import SQLiteHistoricalWarehouse


class AlphaLabEngine:
    """
    Strategy marketplace engine.

    Responsibilities:
    - Register and validate strategies
    - Execute strategies against same context
    - Collect and deduplicate candidates
    - Convert candidates to canonical Opportunity objects
    - Retain strategy lineage and evidence
    - Forward to existing Opportunity Ranking Engine
    """

    def __init__(self) -> None:
        """Initialize the engine."""
        self.strategies: dict[str, StrategyProtocol] = {}
        self.run_history: list[StrategyComparisonResult] = []

    def register_strategy(self, strategy: StrategyProtocol) -> None:
        """Register a strategy."""
        if not strategy.strategy_id:
            raise ValueError("Strategy must have strategy_id")
        self.strategies[strategy.strategy_id] = strategy

    def run(
        self,
        warehouse: SQLiteHistoricalWarehouse,
        observation_time: datetime,
        universe_snapshot_id: str,
        universe_size: int,
        warehouse_manifest_hash: str,
        dataset_manifest_hash: str,
    ) -> StrategyComparisonResult:
        """Execute all registered strategies.

        Args:
            warehouse: Historical warehouse
            observation_time: As-of date for analysis
            universe_snapshot_id: Universe identifier
            universe_size: Number of securities in universe
            warehouse_manifest_hash: Warehouse hash
            dataset_manifest_hash: Dataset hash

        Returns:
            Aggregated result with all strategy outputs and canonical opportunities
        """
        run_id = f"ALPHA-LAB-{observation_time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

        context = StrategyContext(
            observation_time=observation_time,
            warehouse=warehouse,
            universe_snapshot_id=universe_snapshot_id,
            universe_size=universe_size,
            dataset_manifest_hash=dataset_manifest_hash,
            warehouse_manifest_hash=warehouse_manifest_hash,
        )

        strategy_results: dict[str, StrategyRunResult] = {}
        all_candidates: list[StrategyCandidate] = []
        errors: list[str] = []

        # Execute each strategy
        for strategy_id, strategy in self.strategies.items():
            try:
                result = strategy.generate_candidates(context)
                strategy_results[strategy_id] = result
                all_candidates.extend(result.candidates)
            except Exception as e:
                errors.append(f"Strategy {strategy_id} failed: {str(e)}")

        # Deduplicate and aggregate
        unique_opportunities_by_symbol: dict[str, list[StrategyCandidate]] = {}
        for candidate in all_candidates:
            if candidate.symbol not in unique_opportunities_by_symbol:
                unique_opportunities_by_symbol[candidate.symbol] = []
            unique_opportunities_by_symbol[candidate.symbol].append(candidate)

        # Convert to canonical Opportunities
        opportunities: list[Opportunity] = []
        for symbol, candidates in unique_opportunities_by_symbol.items():
            try:
                opportunity = self._candidates_to_opportunity(
                    symbol=symbol,
                    candidates=candidates,
                    context=context,
                    warehouse_manifest_hash=warehouse_manifest_hash,
                    dataset_manifest_hash=dataset_manifest_hash,
                )
                if opportunity:
                    opportunities.append(opportunity)
            except Exception as e:
                errors.append(f"Failed to convert candidates for {symbol}: {str(e)}")

        # Identify overlaps and agreements
        overlaps: dict[str, list[str]] = {}
        agreements: list[str] = []
        for symbol, candidates in unique_opportunities_by_symbol.items():
            if len(candidates) > 1:
                strategy_ids = [c.strategy_id for c in candidates]
                overlaps[symbol] = strategy_ids
                if all(c.candidate_state == CandidateState.TRIGGERED for c in candidates):
                    agreements.append(f"{symbol}: {len(candidates)} strategies agree on TRIGGERED")

        comparison_result = StrategyComparisonResult(
            run_id=run_id,
            observation_time=observation_time,
            strategies_run=tuple(self.strategies.keys()),
            strategy_results=strategy_results,
            unique_candidates=len(unique_opportunities_by_symbol),
            overlapping_symbols=tuple(overlaps.keys()),
            agreements=tuple(agreements),
            opportunities=tuple(opportunities),
            errors=tuple(errors),
            warehouse_manifest_hash=warehouse_manifest_hash,
            dataset_manifest_hash=dataset_manifest_hash,
        )

        self.run_history.append(comparison_result)
        return comparison_result

    def _candidates_to_opportunity(
        self,
        symbol: str,
        candidates: list[StrategyCandidate],
        context: StrategyContext,
        warehouse_manifest_hash: str,
        dataset_manifest_hash: str,
    ) -> Opportunity | None:
        """Convert strategy candidates to canonical Opportunity.

        Preserves all strategy evidence lineage while creating a single
        canonical opportunity object for downstream ranking and allocation.
        """
        if not candidates:
            return None

        # Use first candidate as base
        base_candidate = candidates[0]

        # Create source record IDs that preserve lineage
        source_records = tuple(c.candidate_id for c in candidates)

        # Build warnings from all candidates
        warnings: list[str] = []
        for candidate in candidates:
            if candidate.evidence.negative_contributors:
                warnings.extend(candidate.evidence.negative_contributors)
            if candidate.evidence.invalidation_reasons:
                warnings.extend(candidate.evidence.invalidation_reasons)

        # Aggregate evidence
        max_intrinsic_score = max(
            (c.evidence.intrinsic_opportunity_score for c in candidates),
            default=0.0,
        )
        max_timing_score = max(
            (c.evidence.timing_opportunity_score for c in candidates),
            default=0.0,
        )
        max_catalyst_score = max(
            (c.evidence.catalyst_score for c in candidates),
            default=0.0,
        )

        # Determine if this is triggered
        triggered_count = sum(
            1 for c in candidates if c.candidate_state == CandidateState.TRIGGERED
        )
        waiting_count = sum(
            1 for c in candidates if c.candidate_state == CandidateState.WAITING_FOR_TRIGGER
        )

        # Create synthetic opportunity
        # In production, this would be assembled from warehouse data
        opportunity_id = f"OPP-{symbol}-{context.observation_time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

        try:
            opportunity = Opportunity(
                opportunity_id=opportunity_id,
                security_id=base_candidate.security_id,
                symbol=symbol,
                observation_time=context.observation_time,
                data_available_through=base_candidate.data_available_through,
                universe_snapshot_id=context.universe_snapshot_id,
                benchmark_symbol="SPY",
                sector="Technology",  # Placeholder
                industry="Software",  # Placeholder
                market_regime="TRENDING",  # Placeholder
                sector_regime="NORMAL",  # Placeholder
                weekly_trend_state="BULLISH" if triggered_count > 0 else "NEUTRAL",
                weekly_range_position=0.75 if triggered_count > 0 else 0.5,
                weekly_support_levels=(),
                weekly_resistance_levels=(),
                weekly_breakout_level=100.0,
                weekly_invalidation_level=90.0,
                weekly_volatility_state="CONTRACTED",
                weekly_relative_strength=0.75 if triggered_count > 0 else 0.5,
                weekly_structure_quality=0.8,
                daily_trend_state="BULLISH" if triggered_count > 0 else "NEUTRAL",
                daily_range_position=0.80 if triggered_count > 0 else 0.5,
                daily_support_levels=(),
                daily_resistance_levels=(),
                daily_breakout_level=102.0,
                daily_invalidation_level=95.0,
                daily_volatility_state="NORMAL",
                daily_relative_strength=0.78 if triggered_count > 0 else 0.5,
                daily_structure_quality=0.75,
                setup_type="SWING_REPRICING" if "swing" in str(candidates[0].strategy_id) else "TREND_BREAKOUT",
                trigger_state="TRIGGERED" if triggered_count > 0 else "WAITING",
                breakout_distance_pct=2.5 if triggered_count > 0 else 0.5,
                distance_to_support_pct=8.0,
                distance_to_resistance_pct=3.0,
                volatility_contraction=0.3,
                volatility_expansion=0.1,
                relative_volume=1.2,
                close_quality=0.85,
                failed_breakout=False,
                failed_breakdown=False,
                multi_timeframe_alignment="BULLISH" if triggered_count > 0 else "NEUTRAL",
                close_price=101.50,
                average_daily_dollar_volume=50_000_000.0,
                average_daily_volume=500_000.0,
                spread_estimate_bps=2.0,
                atr_pct=2.5,
                capacity_warning=False,
                known_catalysts=(),
                next_known_event_time=None,
                catalyst_risk="LOW",
                event_data_available_at=context.observation_time,
                probability_estimate=0.55 if triggered_count > 0 else None,
                expected_upside_pct=12.0 if triggered_count > 0 else None,
                expected_downside_pct=-6.0 if triggered_count > 0 else None,
                expected_holding_days=21.0 if triggered_count > 0 else None,
                estimated_cost_bps=3.0 if triggered_count > 0 else None,
                uncertainty_score=0.4,
                calibration_status="UNCALIBRATED",
                expected_value_score=0.0,
                opportunity_cost_rank=None,
                correlation_bucket="TECH",
                concentration_bucket="MEDIUM",
                current_position_weight=0.0,
                governance_eligible=True,
                risk_eligible=True,
                warehouse_manifest_hash=warehouse_manifest_hash,
                dataset_manifest_hash=dataset_manifest_hash,
                source_record_ids=source_records,
                warnings=tuple(warnings),
            )
            return opportunity
        except Exception as e:
            print(f"Failed to create Opportunity for {symbol}: {e}")
            return None


@dataclass(frozen=True)
class StrategyComparisonResult:
    """Result of running all strategies and comparing outputs."""

    run_id: str
    observation_time: datetime
    strategies_run: tuple[str, ...]
    strategy_results: dict[str, StrategyRunResult]
    unique_candidates: int
    overlapping_symbols: tuple[str, ...]
    agreements: tuple[str, ...]
    opportunities: tuple[Opportunity, ...]
    errors: tuple[str, ...]
    warehouse_manifest_hash: str
    dataset_manifest_hash: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "observation_time": self.observation_time.isoformat(),
            "strategies_run": self.strategies_run,
            "unique_candidates": self.unique_candidates,
            "overlapping_symbols": self.overlapping_symbols,
            "agreements": self.agreements,
            "total_opportunities": len(self.opportunities),
            "errors": self.errors,
            "created_at": self.created_at.isoformat(),
        }


# Import for type hints
from dataclasses import dataclass, field
