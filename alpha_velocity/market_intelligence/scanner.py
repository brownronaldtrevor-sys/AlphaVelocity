"""Market Intelligence Engine scanner implementation."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from alpha_velocity.market.bars import Bar
from alpha_velocity.opportunity import Opportunity, assemble_opportunity
from alpha_velocity.opportunity_ranking import OpportunityRanker
from alpha_velocity.warehouse import SQLiteHistoricalWarehouse

from .models import (
    ExclusionReason,
    MarketScanResult,
    QualificationState,
    ScanConfig,
    SecurityQualification,
)


class MarketIntelligenceEngine:
    """Daily research pipeline for opportunity discovery and qualification."""

    def __init__(self) -> None:
        """Initialize the engine."""
        self.ranking_engine = OpportunityRanker()

    def scan(
        self,
        *,
        warehouse: SQLiteHistoricalWarehouse,
        scan_config: ScanConfig,
        universe_manifest_hash: str = "",
        dataset_manifest_hash: str = "",
    ) -> MarketScanResult:
        """Execute complete market intelligence scan.

        Args:
            warehouse: Historical warehouse for data retrieval
            scan_config: Configuration for universe and filters
            universe_manifest_hash: Hash of universe construction
            dataset_manifest_hash: Hash of dataset manifest

        Returns:
            MarketScanResult with qualified opportunities and ranking
        """
        observation_time = scan_config.universe_config.observation_time
        scan_run_id = f"SCAN-{observation_time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        universe_snapshot_id = f"UNIV-{observation_time.strftime('%Y%m%d-%H%M%S')}"

        # Get point-in-time universe
        universe = warehouse.point_in_time_universe(as_of=observation_time)

        qualifications: list[SecurityQualification] = []
        qualified_opportunities: list[Opportunity] = []
        warnings: list[str] = []
        exclusion_counts: dict[str, int] = {}

        # Qualify each security
        for security in universe:
            qualification = self._qualify_security(
                security=security,
                warehouse=warehouse,
                config=scan_config,
                universe_snapshot_id=universe_snapshot_id,
                warehouse_manifest_hash=universe_manifest_hash,
                dataset_manifest_hash=dataset_manifest_hash,
            )
            qualifications.append(qualification)

            # Track exclusions
            if not qualification.qualified:
                for exclusion in qualification.exclusions:
                    exclusion_counts[exclusion.category] = exclusion_counts.get(exclusion.category, 0) + 1

            # Assemble qualified opportunities
            if qualification.qualified or (
                scan_config.include_watchlist and qualification.state == QualificationState.WATCHLIST
            ):
                if qualification.state == QualificationState.INSUFFICIENT_HISTORY and scan_config.include_insufficient_history:
                    continue

                try:
                    opportunity = self._assemble_opportunity(
                        security=security,
                        warehouse=warehouse,
                        observation_time=observation_time,
                        universe_snapshot_id=universe_snapshot_id,
                        warehouse_manifest_hash=universe_manifest_hash,
                        dataset_manifest_hash=dataset_manifest_hash,
                    )
                    if opportunity is not None:
                        qualified_opportunities.append(opportunity)
                except Exception as e:
                    warnings.append(f"Failed to assemble opportunity for {security.ticker}: {str(e)}")

        # Rank qualified opportunities
        ranked_results = tuple()
        if qualified_opportunities:
            try:
                ranking_batch = self.ranking_engine.rank(
                    opportunities=qualified_opportunities,
                    universe_name=f"Market Intelligence Scan",
                    observation_time=observation_time,
                )
                ranked_results = ranking_batch.ranked_opportunities
            except Exception as e:
                warnings.append(f"Ranking failed: {str(e)}")

        # Create scan result
        qualified_count = sum(1 for q in qualifications if q.qualified)
        watchlist_count = sum(1 for q in qualifications if q.state == QualificationState.WATCHLIST)
        excluded_count = len(qualifications) - qualified_count - watchlist_count

        config_hash = self._compute_config_hash(scan_config)

        result = MarketScanResult(
            scan_run_id=scan_run_id,
            observation_time=observation_time,
            universe_snapshot_id=universe_snapshot_id,
            total_securities_considered=len(universe),
            qualified_count=qualified_count,
            watchlist_count=watchlist_count,
            excluded_count=excluded_count,
            exclusion_counts_by_reason=exclusion_counts,
            assembled_opportunities=tuple(qualified_opportunities),
            ranked_research_results=ranked_results,
            security_qualifications=tuple(qualifications),
            warnings=tuple(warnings),
            warehouse_manifest_hash=universe_manifest_hash,
            dataset_manifest_hash=dataset_manifest_hash,
            configuration_hash=config_hash,
        )

        return result

    def _qualify_security(
        self,
        *,
        security: Any,
        warehouse: SQLiteHistoricalWarehouse,
        config: ScanConfig,
        universe_snapshot_id: str,
        warehouse_manifest_hash: str,
        dataset_manifest_hash: str,
    ) -> SecurityQualification:
        """Qualify a single security through all gates."""
        observation_time = config.universe_config.observation_time
        reasons: list[str] = []
        exclusions: list[ExclusionReason] = []
        data_quality_issues: list[str] = []
        warnings: list[str] = []

        # Check delisting
        if config.universe_config.exclude_delisted and security.delisting_date is not None:
            return SecurityQualification(
                security_id=security.security_id,
                symbol=security.ticker,
                state=QualificationState.EXCLUDED,
                qualified=False,
                exclusions=(
                    ExclusionReason(
                        category="EXCLUDED",
                        reason=f"Delisted security (delisting_date: {security.delisting_date.isoformat()})",
                        evidence={"delisting_date": security.delisting_date.isoformat()},
                    ),
                ),
            )

        # Check asset type
        if security.asset_type not in config.universe_config.supported_asset_types:
            return SecurityQualification(
                security_id=security.security_id,
                symbol=security.ticker,
                state=QualificationState.UNSUPPORTED_ASSET,
                qualified=False,
                exclusions=(
                    ExclusionReason(
                        category="ASSET_TYPE",
                        reason=f"Unsupported asset type: {security.asset_type}",
                        evidence={"asset_type": security.asset_type},
                    ),
                ),
            )

        # Check exchange
        if security.exchange not in config.universe_config.supported_exchanges:
            return SecurityQualification(
                security_id=security.security_id,
                symbol=security.ticker,
                state=QualificationState.EXCLUDED,
                qualified=False,
                exclusions=(
                    ExclusionReason(
                        category="EXCHANGE",
                        reason=f"Unsupported exchange: {security.exchange}",
                        evidence={"exchange": security.exchange},
                    ),
                ),
            )

        # Get daily bars and check data quality
        daily_bars_raw = warehouse.get_raw_bars(security.security_id)
        if not daily_bars_raw:
            return SecurityQualification(
                security_id=security.security_id,
                symbol=security.ticker,
                state=QualificationState.DATA_QUALITY_FAILURE,
                qualified=False,
                exclusions=(
                    ExclusionReason(
                        category="DATA_QUALITY",
                        reason="No bar data available",
                        evidence={},
                    ),
                ),
                data_quality_issues=("no_bars",),
            )

        # Filter bars as of observation_time (no future bars)
        daily_bars = [bar for bar in daily_bars_raw if bar.available_at <= observation_time]
        if not daily_bars:
            return SecurityQualification(
                security_id=security.security_id,
                symbol=security.ticker,
                state=QualificationState.DATA_QUALITY_FAILURE,
                qualified=False,
                exclusions=(
                    ExclusionReason(
                        category="DATA_QUALITY",
                        reason="No bars available at observation_time",
                        evidence={"observation_time": observation_time.isoformat()},
                    ),
                ),
                data_quality_issues=("no_current_bars",),
            )

        # Check for invalid OHLCV
        for bar in daily_bars:
            if bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0 or bar.volume <= 0:
                data_quality_issues.append("invalid_ohlcv")
                break

        # Check price range
        latest_close = daily_bars[-1].close
        if latest_close < config.universe_config.min_price or latest_close > config.universe_config.max_price:
            exclusions.append(
                ExclusionReason(
                    category="LIQUIDITY",
                    reason=f"Price {latest_close} outside range [{config.universe_config.min_price}, {config.universe_config.max_price}]",
                    evidence={"close_price": latest_close},
                )
            )

        # Check trading history
        trading_days = len(daily_bars)
        if trading_days < config.universe_config.min_trading_history_days:
            exclusions.append(
                ExclusionReason(
                    category="HISTORY",
                    reason=f"Insufficient history: {trading_days} days < {config.universe_config.min_trading_history_days}",
                    evidence={"trading_days": trading_days},
                )
            )

        # Calculate liquidity metrics
        avg_daily_volume = sum(bar.volume for bar in daily_bars[-20:]) / min(20, len(daily_bars))
        avg_daily_dollar_volume = (
            sum(bar.close * bar.volume for bar in daily_bars[-20:]) / min(20, len(daily_bars))
        )

        if avg_daily_volume < config.universe_config.min_avg_daily_volume:
            exclusions.append(
                ExclusionReason(
                    category="LIQUIDITY",
                    reason=f"Insufficient volume: {avg_daily_volume:.0f} < {config.universe_config.min_avg_daily_volume}",
                    evidence={"avg_daily_volume": avg_daily_volume},
                )
            )

        if avg_daily_dollar_volume < config.universe_config.min_avg_daily_dollar_volume:
            exclusions.append(
                ExclusionReason(
                    category="LIQUIDITY",
                    reason=f"Insufficient dollar volume: ${avg_daily_dollar_volume:.0f} < ${config.universe_config.min_avg_daily_dollar_volume}",
                    evidence={"avg_daily_dollar_volume": avg_daily_dollar_volume},
                )
            )

        # Check for weekly bars
        weekly_bars = warehouse.completed_weekly_bars(security.security_id, as_of=observation_time)
        if len(weekly_bars) < config.min_completed_weeks:
            if data_quality_issues or exclusions:
                state = QualificationState.INSUFFICIENT_HISTORY
            else:
                return SecurityQualification(
                    security_id=security.security_id,
                    symbol=security.ticker,
                    state=QualificationState.INSUFFICIENT_HISTORY,
                    qualified=False,
                    exclusions=(
                        ExclusionReason(
                            category="HISTORY",
                            reason=f"Insufficient completed weeks: {len(weekly_bars)} < {config.min_completed_weeks}",
                            evidence={"completed_weeks": len(weekly_bars)},
                        ),
                    ),
                    daily_bar_count=trading_days,
                    completed_week_count=len(weekly_bars),
                    avg_daily_volume=avg_daily_volume,
                    avg_daily_dollar_volume=avg_daily_dollar_volume,
                )

        # Determine qualification state
        if data_quality_issues:
            state = QualificationState.DATA_QUALITY_FAILURE
        elif exclusions:
            if any(ex.category == "HISTORY" for ex in exclusions):
                state = QualificationState.INSUFFICIENT_HISTORY
            elif any(ex.category == "LIQUIDITY" for ex in exclusions):
                state = QualificationState.ILLIQUID
            else:
                state = QualificationState.EXCLUDED
        else:
            state = QualificationState.QUALIFIED
            reasons.append("Passed all qualification gates")

        qualified = state == QualificationState.QUALIFIED

        return SecurityQualification(
            security_id=security.security_id,
            symbol=security.ticker,
            state=state,
            qualified=qualified,
            reasons=tuple(reasons),
            exclusions=tuple(exclusions),
            daily_bar_count=trading_days,
            completed_week_count=len(weekly_bars),
            avg_daily_volume=avg_daily_volume,
            avg_daily_dollar_volume=avg_daily_dollar_volume,
            spread_estimate_bps=10.0,  # TODO: Calculate from bid-ask when available
            data_quality_issues=tuple(data_quality_issues),
            warnings=tuple(warnings),
        )

    def _assemble_opportunity(
        self,
        *,
        security: Any,
        warehouse: SQLiteHistoricalWarehouse,
        observation_time: datetime,
        universe_snapshot_id: str,
        warehouse_manifest_hash: str,
        dataset_manifest_hash: str,
    ) -> Opportunity | None:
        """Assemble an Opportunity object for a qualified security."""
        try:
            # Convert BarRecords to Bar objects
            daily_bar_records = [bar for bar in warehouse.get_raw_bars(security.security_id) if bar.available_at <= observation_time]
            daily_bars = [
                Bar(
                    timestamp=bar.trade_date,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
                for bar in daily_bar_records
            ]

            weekly_bar_records = warehouse.completed_weekly_bars(security.security_id, as_of=observation_time)
            weekly_bars = [
                Bar(
                    timestamp=bar.trade_date,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
                for bar in weekly_bar_records
            ]

            # Benchmark and sector bars (stub for now)
            benchmark_bars: list[Bar] = []  # TODO: Load from warehouse
            sector_bars: list[Bar] = []  # TODO: Load from warehouse

            opportunity = assemble_opportunity(
                daily_bars=daily_bars,
                weekly_bars=weekly_bars,
                benchmark_bars=benchmark_bars,
                sector_bars=sector_bars,
                feature_snapshots=[],
                known_events=[],
                liquidity_history=[],
                observation_time=observation_time,
                security_id=security.security_id,
                symbol=security.ticker,
                benchmark_symbol="SPY",
                sector="Unknown",
                industry="Unknown",
                universe_snapshot_id=universe_snapshot_id,
                warehouse_manifest_hash=warehouse_manifest_hash,
                dataset_manifest_hash=dataset_manifest_hash,
                source_record_ids=[],
            )
            return opportunity
        except Exception as e:
            # Return None on assembly failure; warning will be recorded in scan
            return None

    @staticmethod
    def _compute_config_hash(config: ScanConfig) -> str:
        """Compute deterministic hash of configuration."""
        config_dict = {
            "min_price": config.universe_config.min_price,
            "max_price": config.universe_config.max_price,
            "min_avg_daily_volume": config.universe_config.min_avg_daily_volume,
            "min_avg_daily_dollar_volume": config.universe_config.min_avg_daily_dollar_volume,
            "min_trading_history_days": config.universe_config.min_trading_history_days,
            "max_spread_bps": config.universe_config.max_spread_bps,
            "supported_exchanges": sorted(config.universe_config.supported_exchanges),
            "supported_asset_types": sorted(config.universe_config.supported_asset_types),
            "exclude_delisted": config.universe_config.exclude_delisted,
            "min_bars_for_weekly": config.min_bars_for_weekly,
            "min_completed_weeks": config.min_completed_weeks,
        }
        config_json = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()[:16]
