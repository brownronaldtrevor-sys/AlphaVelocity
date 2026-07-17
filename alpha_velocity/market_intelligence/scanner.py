"""Market Intelligence Engine scanner implementation."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from alpha_velocity.market.bars import Bar
from alpha_velocity.marketplace import OpportunityMarketplace
from alpha_velocity.opportunity import Opportunity, assemble_opportunity
from alpha_velocity.opportunity_ranking import OpportunityRanker
from alpha_velocity.warehouse import SQLiteHistoricalWarehouse

from .models import (
    ExclusionReason,
    MarketScanResult,
    PriorityMode,
    QualificationState,
    ResearchPriorityLevel,
    ResearchPriorityRecommendation,
    ResearchUniverse,
    ScanConfig,
    SecurityQualification,
    UniverseDiagnostics,
    UniverseMembershipRecord,
    UniverseType,
    ValidationStatus,
)


class MarketIntelligenceEngine:
    """Daily research pipeline for opportunity discovery and qualification."""

    def __init__(self) -> None:
        """Initialize the engine."""
        self.ranking_engine = OpportunityRanker()
        self.marketplace = OpportunityMarketplace()

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

        universe = warehouse.point_in_time_universe(as_of=observation_time)
        security_by_id = {security.security_id: security for security in universe}

        qualification_by_security: dict[str, SecurityQualification] = {}
        opportunity_by_security: dict[str, Opportunity] = {}
        universe_diagnostics: list[UniverseDiagnostics] = []
        universe_priorities: list[ResearchPriorityRecommendation] = []
        candidate_counts_by_universe: dict[str, int] = {}
        merged_duplicate_candidates = 0
        warnings: list[str] = []
        exclusion_counts: dict[str, int] = {}
        overlap_tracker: dict[str, set[str]] = {}

        security_metrics = {
            security.security_id: self._compute_security_metrics(
                warehouse=warehouse,
                security_id=security.security_id,
                observation_time=observation_time,
            )
            for security in universe
        }

        research_universes = self._resolve_research_universes(
            securities=universe,
            scan_config=scan_config,
            observation_time=observation_time,
        )

        for research_universe in research_universes:
            if not research_universe.enabled:
                continue

            try:
                membership = self._build_point_in_time_membership(
                    universe=research_universe,
                    securities=universe,
                    scan_config=scan_config,
                    security_metrics=security_metrics,
                    observation_time=observation_time,
                )
                diagnostics = self._empty_universe_diagnostics(research_universe)
                diagnostics = UniverseDiagnostics(
                    **{
                        **diagnostics.__dict__,
                        "securities_considered": len(membership),
                    }
                )

                for member in membership:
                    security = security_by_id.get(member.security_id)
                    if security is None:
                        diagnostics = UniverseDiagnostics(
                            **{
                                **diagnostics.__dict__,
                                "data_unavailable_count": diagnostics.data_unavailable_count + 1,
                                "warning_count": diagnostics.warning_count + 1,
                            }
                        )
                        continue

                    qualification = self._qualify_security(
                        security=security,
                        warehouse=warehouse,
                        config=scan_config,
                        universe_snapshot_id=universe_snapshot_id,
                        warehouse_manifest_hash=universe_manifest_hash,
                        dataset_manifest_hash=dataset_manifest_hash,
                    )

                    best_existing = qualification_by_security.get(security.security_id)
                    if best_existing is None or (not best_existing.qualified and qualification.qualified):
                        qualification_by_security[security.security_id] = qualification

                    if not qualification.qualified:
                        diagnostics = UniverseDiagnostics(
                            **{
                                **diagnostics.__dict__,
                                "excluded_count": diagnostics.excluded_count + 1,
                                "data_unavailable_count": diagnostics.data_unavailable_count
                                + (1 if qualification.state == QualificationState.DATA_QUALITY_FAILURE else 0),
                            }
                        )
                        for exclusion in qualification.exclusions:
                            exclusion_counts[exclusion.category] = exclusion_counts.get(exclusion.category, 0) + 1
                        continue

                    diagnostics = UniverseDiagnostics(
                        **{
                            **diagnostics.__dict__,
                            "securities_usable": diagnostics.securities_usable + 1,
                            "candidates_discovered": diagnostics.candidates_discovered + 1,
                            "candidates_qualified": diagnostics.candidates_qualified + 1,
                        }
                    )

                    opportunity = self._assemble_opportunity(
                        security=security,
                        warehouse=warehouse,
                        observation_time=observation_time,
                        universe_snapshot_id=universe_snapshot_id,
                        warehouse_manifest_hash=universe_manifest_hash,
                        dataset_manifest_hash=dataset_manifest_hash,
                    )
                    if opportunity is None:
                        diagnostics = UniverseDiagnostics(
                            **{
                                **diagnostics.__dict__,
                                "warning_count": diagnostics.warning_count + 1,
                            }
                        )
                        continue

                    self._attach_universe_provenance(
                        opportunity=opportunity,
                        universe=research_universe,
                        membership=member,
                        discovery_reason=member.inclusion_reason,
                    )

                    if security.security_id in opportunity_by_security:
                        self._merge_universe_provenance(
                            target=opportunity_by_security[security.security_id],
                            incoming=opportunity,
                        )
                        merged_duplicate_candidates += 1
                        diagnostics = UniverseDiagnostics(
                            **{
                                **diagnostics.__dict__,
                                "duplicate_candidates_merged": diagnostics.duplicate_candidates_merged + 1,
                            }
                        )
                    else:
                        opportunity_by_security[security.security_id] = opportunity

                    overlap_tracker.setdefault(security.security_id, set()).add(research_universe.universe_id)

                    actionable, starter, near_trigger = self._classify_actionability(opportunity)
                    diagnostics = UniverseDiagnostics(
                        **{
                            **diagnostics.__dict__,
                            "actionable_count": diagnostics.actionable_count + (1 if actionable else 0),
                            "starter_count": diagnostics.starter_count + (1 if starter else 0),
                            "near_trigger_count": diagnostics.near_trigger_count + (1 if near_trigger else 0),
                            "research_only_count": diagnostics.research_only_count + (0 if (actionable or starter or near_trigger) else 1),
                            "early_inflection_count": diagnostics.early_inflection_count
                            + (1 if self._is_early_inflection(opportunity) else 0),
                            "primary_move_count": diagnostics.primary_move_count
                            + (1 if self._is_primary_move(opportunity) else 0),
                        }
                    )

                diagnostics = self._finalize_universe_diagnostics(diagnostics, opportunity_by_security)
                priority = self._recommend_research_priority(diagnostics, research_universe)
                universe_diagnostics.append(diagnostics)
                universe_priorities.append(priority)
                candidate_counts_by_universe[research_universe.universe_id] = diagnostics.candidates_discovered
            except Exception as exc:
                warnings.append(f"Universe {research_universe.universe_id} failed: {exc}")
                universe_diagnostics.append(
                    UniverseDiagnostics(
                        universe_id=research_universe.universe_id,
                        universe_name=research_universe.name,
                        universe_type=research_universe.universe_type,
                        warning_count=1,
                    )
                )
                universe_priorities.append(
                    ResearchPriorityRecommendation(
                        universe_id=research_universe.universe_id,
                        priority=ResearchPriorityLevel.PAUSED,
                        reasons=("Universe scan failed",),
                        contradictions=("Scan execution error",),
                        confidence=0.0,
                        validation_status=ValidationStatus.UNKNOWN,
                    )
                )

        qualified_opportunities = list(opportunity_by_security.values())

        # Rank qualified opportunities
        ranked_results = tuple()
        if qualified_opportunities:
            try:
                ranking_batch = self.ranking_engine.rank(
                    opportunities=qualified_opportunities,
                    universe_snapshot_id=universe_snapshot_id,
                    confidence_level="RESEARCH",
                )
                ranked_results = ranking_batch.ranked_opportunities
            except Exception as e:
                warnings.append(f"Ranking failed: {str(e)}")

        # Organize into marketplace (classify into queues and discovery lenses)
        marketplace_result = None
        if qualified_opportunities:
            try:
                marketplace_result = self.marketplace.organize(
                    opportunities=list(qualified_opportunities),
                    observation_time=observation_time,
                    universe_metadata={
                        "candidate_counts_by_universe": candidate_counts_by_universe,
                        "overlap_across_universes": sum(1 for universes in overlap_tracker.values() if len(universes) > 1),
                        "merged_canonical_candidate_count": len(qualified_opportunities),
                        "research_priority_summary": {
                            recommendation.universe_id: recommendation.priority.value
                            for recommendation in universe_priorities
                        },
                    },
                )
                warnings.extend(marketplace_result.warnings)
            except Exception as e:
                warnings.append(f"Marketplace organization failed: {str(e)}")

        qualifications = tuple(sorted(qualification_by_security.values(), key=lambda q: q.symbol))

        qualified_count = sum(1 for q in qualifications if q.qualified)
        watchlist_count = sum(1 for q in qualifications if q.state == QualificationState.WATCHLIST)
        excluded_count = max(0, len(universe) - qualified_count - watchlist_count)

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
            security_qualifications=qualifications,
            warnings=tuple(warnings),
            warehouse_manifest_hash=universe_manifest_hash,
            dataset_manifest_hash=dataset_manifest_hash,
            configuration_hash=config_hash,
            marketplace_result=marketplace_result,
            universe_diagnostics=tuple(universe_diagnostics),
            universe_priorities=tuple(universe_priorities),
            candidate_counts_by_universe=candidate_counts_by_universe,
            overlap_across_universes=sum(1 for universes in overlap_tracker.values() if len(universes) > 1),
            merged_duplicate_candidates=merged_duplicate_candidates,
            unique_canonical_opportunities=len(qualified_opportunities),
        )

        return result

    def _resolve_research_universes(
        self,
        *,
        securities: list[Any],
        scan_config: ScanConfig,
        observation_time: datetime,
    ) -> tuple[ResearchUniverse, ...]:
        if scan_config.research_universes:
            return tuple(universe for universe in scan_config.research_universes if universe.enabled)

        is_sample_mode = any(str(getattr(security, "source", "")).upper() == "SAMPLE_DATA" for security in securities)
        if is_sample_mode:
            return self._build_sample_research_universes(observation_time, scan_config)

        return (
            ResearchUniverse(
                universe_id="broad_market",
                name="Broad Market",
                description="Default broad market universe",
                universe_type=UniverseType.BROAD_MARKET,
                observation_time=observation_time,
                available_at=observation_time,
                source="SYSTEM",
                validation_status=ValidationStatus.SUPPORTED,
                enabled=True,
                priority_mode=PriorityMode.BALANCED,
                capacity_limit=0,
            ),
        )

    def _build_sample_research_universes(
        self,
        observation_time: datetime,
        scan_config: ScanConfig,
    ) -> tuple[ResearchUniverse, ...]:
        shared = {
            "observation_time": observation_time,
            "available_at": observation_time,
            "source": "SAMPLE_DATA",
            "validation_status": ValidationStatus.SUPPORTED,
            "enabled": True,
            "priority_mode": PriorityMode.BALANCED,
            "capacity_limit": 0,
        }
        return (
            ResearchUniverse(universe_id="micro_cap", name="Micro Cap", description="Smallest cap proxy bucket", universe_type=UniverseType.MICRO_CAP, membership_rules={"market_cap_proxy_max": 2.5e7}, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="small_cap", name="Small Cap", description="Small cap proxy bucket", universe_type=UniverseType.SMALL_CAP, membership_rules={"market_cap_proxy_min": 2.5e7, "market_cap_proxy_max": 1.0e8}, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="mid_cap", name="Mid Cap", description="Mid cap proxy bucket", universe_type=UniverseType.MID_CAP, membership_rules={"market_cap_proxy_min": 1.0e8, "market_cap_proxy_max": 4.0e8}, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="large_cap", name="Large Cap", description="Large cap proxy bucket", universe_type=UniverseType.LARGE_CAP, membership_rules={"market_cap_proxy_min": 4.0e8}, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="broad_market", name="Broad Market", description="Broad coverage universe", universe_type=UniverseType.BROAD_MARKET, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="special_situation", name="Special Situations", description="Complex and contradictory setups", universe_type=UniverseType.SPECIAL_SITUATION, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="turnaround", name="Turnaround", description="Recovery and restructuring candidates", universe_type=UniverseType.TURNAROUND, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="event_driven", name="Event Driven", description="Catalyst and event-oriented names", universe_type=UniverseType.EVENT_DRIVEN, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="momentum", name="Momentum", description="Relative strength and trend persistence", universe_type=UniverseType.MOMENTUM, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="deep_value", name="Deep Value", description="Discounted and mean-reversion candidates", universe_type=UniverseType.DEEP_VALUE, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="high_volatility", name="High Volatility", description="High-volatility opportunities", universe_type=UniverseType.HIGH_VOLATILITY, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="current_holdings", name="Current Holdings", description="Existing holdings universe", universe_type=UniverseType.CURRENT_HOLDINGS, membership_rules={"symbols": list(scan_config.current_holding_symbols or ("HOLD1", "HOLD2", "AAPL"))}, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="user_watchlist", name="User Watchlist", description="User-defined watchlist symbols", universe_type=UniverseType.USER_WATCHLIST, membership_rules={"symbols": list(scan_config.user_watchlist_symbols or ("WATCH1", "WATCH2", "WEAK"))}, tags=("SAMPLE_DATA",), **shared),
            ResearchUniverse(universe_id="etf_benchmark", name="ETF Benchmark", description="Benchmark ETF and proxy names", universe_type=UniverseType.ETF_BENCHMARK, membership_rules={"symbols": list(scan_config.benchmark_symbols or ("SPY", "QQQ", "IWM", "DIA"))}, tags=("SAMPLE_DATA",), **shared),
        )

    def _build_point_in_time_membership(
        self,
        *,
        universe: ResearchUniverse,
        securities: list[Any],
        scan_config: ScanConfig,
        security_metrics: dict[str, dict[str, float]],
        observation_time: datetime,
    ) -> tuple[UniverseMembershipRecord, ...]:
        members: list[UniverseMembershipRecord] = []
        include_symbols = {symbol.upper() for symbol in universe.membership_rules.get("symbols", [])}
        for security in securities:
            security_id = str(getattr(security, "security_id", "") or "")
            symbol = str(getattr(security, "ticker", "") or "")
            if not security_id or not symbol:
                continue

            available_at = getattr(security, "available_at", observation_time)
            if available_at and available_at > observation_time:
                continue

            listing_date = getattr(security, "listing_date", observation_time)
            delisting_date = getattr(security, "delisting_date", None)
            if listing_date and listing_date > observation_time:
                continue
            if delisting_date and delisting_date < observation_time:
                continue

            metrics = security_metrics.get(security_id, {})
            include = self._security_in_universe(
                universe=universe,
                symbol=symbol,
                security=security,
                metrics=metrics,
                include_symbols=include_symbols,
            )
            if not include:
                continue

            members.append(
                UniverseMembershipRecord(
                    security_id=security_id,
                    symbol=symbol,
                    effective_from=listing_date or observation_time,
                    effective_to=delisting_date,
                    inclusion_reason=self._membership_reason(universe, symbol),
                    source=str(getattr(security, "source", "")) or universe.source,
                    available_at=available_at if available_at else observation_time,
                    validation_status=ValidationStatus.SUPPORTED,
                )
            )

        return tuple(sorted(members, key=lambda item: item.symbol))

    def _security_in_universe(
        self,
        *,
        universe: ResearchUniverse,
        symbol: str,
        security: Any,
        metrics: dict[str, float],
        include_symbols: set[str],
    ) -> bool:
        symbol_u = symbol.upper()
        market_cap_proxy = float(metrics.get("market_cap_proxy", 0.0))
        avg_dollar_volume = float(metrics.get("avg_dollar_volume", 0.0))
        volatility = float(metrics.get("volatility", 0.0))
        latest_close = float(metrics.get("latest_close", 0.0))

        if universe.universe_type == UniverseType.BROAD_MARKET:
            return True
        if universe.universe_type == UniverseType.MICRO_CAP:
            return market_cap_proxy <= float(universe.membership_rules.get("market_cap_proxy_max", 2.5e7))
        if universe.universe_type == UniverseType.SMALL_CAP:
            return (
                market_cap_proxy >= float(universe.membership_rules.get("market_cap_proxy_min", 2.5e7))
                and market_cap_proxy <= float(universe.membership_rules.get("market_cap_proxy_max", 1.0e8))
            )
        if universe.universe_type == UniverseType.MID_CAP:
            return (
                market_cap_proxy >= float(universe.membership_rules.get("market_cap_proxy_min", 1.0e8))
                and market_cap_proxy <= float(universe.membership_rules.get("market_cap_proxy_max", 4.0e8))
            )
        if universe.universe_type == UniverseType.LARGE_CAP:
            return market_cap_proxy >= float(universe.membership_rules.get("market_cap_proxy_min", 4.0e8))
        if universe.universe_type == UniverseType.SPECIAL_SITUATION:
            return symbol_u.startswith(("SPEC", "EXC", "EVT"))
        if universe.universe_type == UniverseType.ACTIVIST:
            return symbol_u.startswith(("ACT", "EVT"))
        if universe.universe_type == UniverseType.TURNAROUND:
            return symbol_u.startswith(("TURN", "TRN", "FIX")) or symbol_u in {"TURN"}
        if universe.universe_type == UniverseType.HIGH_VOLATILITY:
            return volatility >= 0.03
        if universe.universe_type == UniverseType.DEEP_VALUE:
            return latest_close > 0 and latest_close < 120.0 and avg_dollar_volume >= 500_000.0
        if universe.universe_type == UniverseType.MOMENTUM:
            return metrics.get("momentum", 0.0) > 0.0
        if universe.universe_type == UniverseType.EVENT_DRIVEN:
            return symbol_u.startswith(("EVT", "TURN", "SPEC"))
        if universe.universe_type == UniverseType.CURRENT_HOLDINGS:
            return symbol_u in include_symbols
        if universe.universe_type == UniverseType.USER_WATCHLIST:
            return symbol_u in include_symbols
        if universe.universe_type == UniverseType.ETF_BENCHMARK:
            return symbol_u in include_symbols
        if universe.universe_type == UniverseType.CUSTOM:
            excludes = {item.upper() for item in universe.membership_rules.get("exclude_symbols", [])}
            includes = {item.upper() for item in universe.membership_rules.get("include_symbols", [])}
            if includes and symbol_u not in includes:
                return False
            if symbol_u in excludes:
                return False
            return True
        return False

    @staticmethod
    def _membership_reason(universe: ResearchUniverse, symbol: str) -> str:
        return f"{symbol} matched {universe.universe_type.value} universe rules"

    @staticmethod
    def _classify_actionability(opportunity: Opportunity) -> tuple[bool, bool, bool]:
        trigger_state = str(opportunity.trigger_state).upper()
        weekly_trend = str(opportunity.weekly_trend_state).upper()
        actionable = (
            trigger_state == "TRIGGERED"
            and str(opportunity.calibration_status).upper() == "CALIBRATED"
            and opportunity.risk_eligible
            and opportunity.governance_eligible
            and not opportunity.model_disagreement
        )
        starter = (
            trigger_state == "TRIGGERED"
            and opportunity.risk_eligible
            and opportunity.governance_eligible
            and not opportunity.model_disagreement
            and not actionable
        )
        near_trigger = trigger_state == "WAITING_FOR_TRIGGER" and weekly_trend == "UPTREND" and opportunity.breakout_distance_pct <= 5.0
        return actionable, starter, near_trigger

    @staticmethod
    def _is_early_inflection(opportunity: Opportunity) -> bool:
        setup = str(opportunity.setup_type).upper()
        return "EARLY" in setup or setup in {"CONSTRUCTIVE_PULLBACK", "BASE_ON_BASE"}

    @staticmethod
    def _is_primary_move(opportunity: Opportunity) -> bool:
        return str(opportunity.trigger_state).upper() == "TRIGGERED" and str(opportunity.weekly_trend_state).upper() == "UPTREND"

    @staticmethod
    def _empty_universe_diagnostics(universe: ResearchUniverse) -> UniverseDiagnostics:
        return UniverseDiagnostics(
            universe_id=universe.universe_id,
            universe_name=universe.name,
            universe_type=universe.universe_type,
        )

    @staticmethod
    def _finalize_universe_diagnostics(
        diagnostics: UniverseDiagnostics,
        opportunities_by_security: dict[str, Opportunity],
    ) -> UniverseDiagnostics:
        if diagnostics.candidates_qualified == 0:
            return diagnostics

        values = list(opportunities_by_security.values())
        avg_research_conf = 0.0
        avg_capital_conviction = 0.0
        if values:
            avg_research_conf = sum(1.0 if opportunity.expected_upside_pct is not None else 0.3 for opportunity in values) / len(values)
            avg_capital_conviction = sum(0.8 if str(opportunity.calibration_status).upper() == "CALIBRATED" else 0.3 for opportunity in values) / len(values)

        return UniverseDiagnostics(
            **{
                **diagnostics.__dict__,
                "average_research_confidence": avg_research_conf,
                "average_capital_conviction": avg_capital_conviction,
            }
        )

    @staticmethod
    def _recommend_research_priority(
        diagnostics: UniverseDiagnostics,
        universe: ResearchUniverse,
    ) -> ResearchPriorityRecommendation:
        density = diagnostics.candidates_qualified / max(1, diagnostics.securities_considered)
        if diagnostics.candidates_qualified == 0:
            priority = ResearchPriorityLevel.PAUSED
            reasons = ("No qualified candidates discovered",)
        elif density >= 0.45 or diagnostics.early_inflection_count >= 4:
            priority = ResearchPriorityLevel.VERY_HIGH
            reasons = ("High opportunity density or strong early inflection breadth",)
        elif density >= 0.30:
            priority = ResearchPriorityLevel.HIGH
            reasons = ("Healthy qualified opportunity density",)
        elif density >= 0.15:
            priority = ResearchPriorityLevel.NORMAL
            reasons = ("Moderate opportunity density",)
        else:
            priority = ResearchPriorityLevel.LOW
            reasons = ("Sparse opportunity density",)

        contradictions = ()
        if diagnostics.warning_count > 0:
            contradictions = ("Data warnings reduce priority confidence",)

        return ResearchPriorityRecommendation(
            universe_id=universe.universe_id,
            priority=priority,
            reasons=reasons,
            contradictions=contradictions,
            missing_information=("Further validation of universe membership quality",),
            required_confirmation=("Reconfirm priority on next observation",),
            confidence=max(0.1, min(0.9, 0.3 + density)),
            validation_status=ValidationStatus.PARTIALLY_SUPPORTED,
        )

    def _compute_security_metrics(
        self,
        *,
        warehouse: SQLiteHistoricalWarehouse,
        security_id: str,
        observation_time: datetime,
    ) -> dict[str, float]:
        bars = [bar for bar in warehouse.get_raw_bars(security_id) if bar.available_at <= observation_time]
        if not bars:
            return {
                "latest_close": 0.0,
                "avg_dollar_volume": 0.0,
                "market_cap_proxy": 0.0,
                "volatility": 0.0,
                "momentum": 0.0,
            }

        recent = bars[-20:]
        latest_close = float(recent[-1].close)
        avg_dollar_volume = sum(float(bar.close) * float(bar.volume) for bar in recent) / max(1, len(recent))
        returns = []
        for idx in range(1, len(recent)):
            prev_close = float(recent[idx - 1].close)
            current_close = float(recent[idx].close)
            if prev_close <= 0:
                continue
            returns.append((current_close - prev_close) / prev_close)
        volatility = (sum(abs(value) for value in returns) / max(1, len(returns))) if returns else 0.0
        momentum = (float(recent[-1].close) - float(recent[0].close)) / max(1e-6, float(recent[0].close))
        return {
            "latest_close": latest_close,
            "avg_dollar_volume": avg_dollar_volume,
            "market_cap_proxy": avg_dollar_volume * 20.0,
            "volatility": volatility,
            "momentum": momentum,
        }

    @staticmethod
    def _attach_universe_provenance(
        *,
        opportunity: Opportunity,
        universe: ResearchUniverse,
        membership: UniverseMembershipRecord,
        discovery_reason: str,
    ) -> None:
        object.__setattr__(opportunity, "contributing_universe_ids", (universe.universe_id,))
        object.__setattr__(opportunity, "primary_discovery_universe", universe.universe_id)
        object.__setattr__(opportunity, "universe_membership_evidence", (membership.to_dict(),))
        object.__setattr__(opportunity, "discovery_reasons_by_universe", {universe.universe_id: (discovery_reason,)})
        object.__setattr__(opportunity, "universe_priority_context", {universe.universe_id: "NORMAL"})

    @staticmethod
    def _merge_universe_provenance(
        *,
        target: Opportunity,
        incoming: Opportunity,
    ) -> None:
        merged_universe_ids = tuple(sorted(set(target.contributing_universe_ids) | set(incoming.contributing_universe_ids)))
        merged_membership = tuple(list(target.universe_membership_evidence) + list(incoming.universe_membership_evidence))

        merged_reasons: dict[str, tuple[str, ...]] = {}
        for source in (target.discovery_reasons_by_universe, incoming.discovery_reasons_by_universe):
            for key, values in source.items():
                merged_reasons[key] = tuple(sorted(set(merged_reasons.get(key, ()) + tuple(values))))

        merged_priority_context = dict(target.universe_priority_context)
        merged_priority_context.update(incoming.universe_priority_context)

        object.__setattr__(target, "contributing_universe_ids", merged_universe_ids)
        object.__setattr__(target, "universe_membership_evidence", merged_membership)
        object.__setattr__(target, "discovery_reasons_by_universe", merged_reasons)
        object.__setattr__(target, "universe_priority_context", merged_priority_context)

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
            if security.source == "SAMPLE_DATA":
                self._apply_sample_profile_overrides(opportunity, security.ticker)
            return opportunity
        except Exception as e:
            # Return None on assembly failure; warning will be recorded in scan
            return None

    def _apply_sample_profile_overrides(self, opportunity: Opportunity, symbol: str) -> None:
        """Apply deterministic sample-mode profiling so fixture families map to distinct queues."""
        prefix = symbol.upper()

        profile: dict[str, Any] | None = None
        if prefix.startswith("TRG") or prefix in {"AAPL", "ESZ24"}:
            profile = {
                "market_regime": "TRENDING",
                "sector_regime": "EARLY_LEADERSHIP",
                "weekly_trend_state": "UPTREND",
                "daily_trend_state": "UPTREND",
                "setup_type": "RELATIVE_STRENGTH_BREAKOUT",
                "trigger_state": "TRIGGERED",
                "breakout_distance_pct": 2.5,
                "distance_to_support_pct": 6.0,
                "distance_to_resistance_pct": 4.0,
                "volatility_contraction": 0.35,
                "volatility_expansion": 0.12,
                "relative_volume": 1.8,
                "close_quality": 0.85,
                "failed_breakout": False,
                "failed_breakdown": False,
                "multi_timeframe_alignment": "ALIGNED",
                "average_daily_dollar_volume": 6_500_000.0,
                "average_daily_volume": 250_000.0,
                "probability_estimate": 0.66,
                "expected_upside_pct": 18.0,
                "expected_downside_pct": -7.0,
                "expected_holding_days": 12.0,
                "estimated_cost_bps": 4.0,
                "calibration_status": "CALIBRATED",
                "expected_value_score": 82.0,
                "opportunity_cost_rank": 1,
                "catalyst_risk": "LOW",
                "known_catalysts": ({"name": "sample catalyst", "type": "TRIGGER"},),
                "model_disagreement": False,
            }
        elif prefix.startswith("START") or prefix in {"MSFT", "NQZ24"}:
            profile = {
                "market_regime": "TRENDING",
                "sector_regime": "EMERGING_INFLECTION",
                "weekly_trend_state": "UPTREND",
                "daily_trend_state": "UPTREND",
                "setup_type": "CONSTRUCTIVE_PULLBACK",
                "trigger_state": "TRIGGERED",
                "breakout_distance_pct": 1.2,
                "distance_to_support_pct": 7.5,
                "distance_to_resistance_pct": 5.0,
                "volatility_contraction": 0.28,
                "volatility_expansion": 0.10,
                "relative_volume": 1.2,
                "close_quality": 0.78,
                "failed_breakout": False,
                "failed_breakdown": False,
                "multi_timeframe_alignment": "ALIGNED",
                "average_daily_dollar_volume": 5_200_000.0,
                "average_daily_volume": 180_000.0,
                "probability_estimate": None,
                "expected_upside_pct": 16.0,
                "expected_downside_pct": -6.0,
                "expected_holding_days": 10.0,
                "estimated_cost_bps": 4.5,
                "calibration_status": "UNCALIBRATED",
                "expected_value_score": 58.0,
                "opportunity_cost_rank": 2,
                "catalyst_risk": "LOW",
                "known_catalysts": (),
                "model_disagreement": False,
            }
        elif prefix.startswith("NEAR") or prefix in {"TREND", "GCZ24"}:
            profile = {
                "market_regime": "TRENDING",
                "sector_regime": "EARLY_LEADERSHIP",
                "weekly_trend_state": "UPTREND",
                "daily_trend_state": "UPTREND",
                "setup_type": "FLAT_BASE",
                "trigger_state": "WAITING_FOR_TRIGGER",
                "breakout_distance_pct": 0.8,
                "distance_to_support_pct": 8.5,
                "distance_to_resistance_pct": 2.0,
                "volatility_contraction": 0.42,
                "volatility_expansion": 0.08,
                "relative_volume": 0.95,
                "close_quality": 0.74,
                "failed_breakout": False,
                "failed_breakdown": False,
                "multi_timeframe_alignment": "ALIGNED",
                "average_daily_dollar_volume": 4_800_000.0,
                "average_daily_volume": 150_000.0,
                "probability_estimate": 0.52,
                "expected_upside_pct": 14.0,
                "expected_downside_pct": -5.0,
                "expected_holding_days": 18.0,
                "estimated_cost_bps": 4.0,
                "calibration_status": "CALIBRATED",
                "expected_value_score": 55.0,
                "opportunity_cost_rank": 3,
                "catalyst_risk": "LOW",
                "known_catalysts": (),
                "model_disagreement": False,
            }
        elif prefix.startswith("VAL"):
            profile = {
                "market_regime": "NEUTRAL",
                "sector_regime": "ESTABLISHED_LEADER",
                "weekly_trend_state": "UPTREND",
                "daily_trend_state": "PULLBACK",
                "setup_type": "CONSTRUCTIVE_PULLBACK",
                "trigger_state": "WAITING_FOR_TRIGGER",
                "breakout_distance_pct": -0.8,
                "distance_to_support_pct": 5.0,
                "distance_to_resistance_pct": 11.0,
                "volatility_contraction": 0.22,
                "volatility_expansion": 0.05,
                "relative_volume": 0.88,
                "close_quality": 0.68,
                "failed_breakout": False,
                "failed_breakdown": False,
                "multi_timeframe_alignment": "WEEKLY_BULLISH_DAILY_PULLBACK",
                "average_daily_dollar_volume": 8_000_000.0,
                "average_daily_volume": 300_000.0,
                "probability_estimate": 0.59,
                "expected_upside_pct": 38.0,
                "expected_downside_pct": -9.0,
                "expected_holding_days": 45.0,
                "estimated_cost_bps": 5.0,
                "calibration_status": "CALIBRATED",
                "expected_value_score": 72.0,
                "opportunity_cost_rank": 4,
                "catalyst_risk": "LOW",
                "known_catalysts": ({"name": "valuation re-rating", "type": "EARNINGS"},),
                "model_disagreement": False,
            }
        elif prefix.startswith("MOM"):
            profile = {
                "market_regime": "TRENDING",
                "sector_regime": "EMERGING_INFLECTION",
                "weekly_trend_state": "UPTREND",
                "daily_trend_state": "UPTREND",
                "setup_type": "EARLY_MOMENTUM_ENTRY",
                "trigger_state": "WAITING_FOR_TRIGGER",
                "breakout_distance_pct": 1.5,
                "distance_to_support_pct": 4.5,
                "distance_to_resistance_pct": 3.5,
                "volatility_contraction": 0.30,
                "volatility_expansion": 0.12,
                "relative_volume": 1.45,
                "close_quality": 0.82,
                "failed_breakout": False,
                "failed_breakdown": False,
                "multi_timeframe_alignment": "ALIGNED",
                "average_daily_dollar_volume": 5_500_000.0,
                "average_daily_volume": 220_000.0,
                "probability_estimate": 0.55,
                "expected_upside_pct": 24.0,
                "expected_downside_pct": -8.0,
                "expected_holding_days": 20.0,
                "estimated_cost_bps": 4.0,
                "calibration_status": "CALIBRATED",
                "expected_value_score": 68.0,
                "opportunity_cost_rank": 5,
                "catalyst_risk": "LOW",
                "known_catalysts": (),
                "model_disagreement": False,
            }
        elif prefix.startswith("TOP"):
            profile = {
                "market_regime": "TRENDING",
                "sector_regime": "EARLY_LEADERSHIP",
                "weekly_trend_state": "UPTREND",
                "daily_trend_state": "UPTREND",
                "setup_type": "BASE_ON_BASE",
                "trigger_state": "WAITING_FOR_TRIGGER",
                "breakout_distance_pct": 0.4,
                "distance_to_support_pct": 6.5,
                "distance_to_resistance_pct": 2.8,
                "volatility_contraction": 0.26,
                "volatility_expansion": 0.06,
                "relative_volume": 1.05,
                "close_quality": 0.77,
                "failed_breakout": False,
                "failed_breakdown": False,
                "multi_timeframe_alignment": "ALIGNED",
                "average_daily_dollar_volume": 6_000_000.0,
                "average_daily_volume": 260_000.0,
                "probability_estimate": 0.54,
                "expected_upside_pct": 20.0,
                "expected_downside_pct": -7.0,
                "expected_holding_days": 30.0,
                "estimated_cost_bps": 4.0,
                "calibration_status": "CALIBRATED",
                "expected_value_score": 60.0,
                "opportunity_cost_rank": 6,
                "catalyst_risk": "LOW",
                "known_catalysts": (),
                "model_disagreement": False,
            }
        elif prefix.startswith("EVT") or prefix in {"TURN"}:
            profile = {
                "market_regime": "NEUTRAL",
                "sector_regime": "EMERGING_INFLECTION",
                "weekly_trend_state": "UPTREND",
                "daily_trend_state": "UPTREND",
                "setup_type": "SPECIAL_SITUATION",
                "trigger_state": "WAITING_FOR_TRIGGER",
                "breakout_distance_pct": 0.2,
                "distance_to_support_pct": 7.0,
                "distance_to_resistance_pct": 3.0,
                "volatility_contraction": 0.33,
                "volatility_expansion": 0.13,
                "relative_volume": 1.1,
                "close_quality": 0.73,
                "failed_breakout": False,
                "failed_breakdown": True,
                "multi_timeframe_alignment": "ALIGNED",
                "average_daily_dollar_volume": 4_200_000.0,
                "average_daily_volume": 180_000.0,
                "probability_estimate": 0.49,
                "expected_upside_pct": 32.0,
                "expected_downside_pct": -12.0,
                "expected_holding_days": 28.0,
                "estimated_cost_bps": 6.0,
                "calibration_status": "CALIBRATED",
                "expected_value_score": 63.0,
                "opportunity_cost_rank": 7,
                "catalyst_risk": "MODERATE",
                "known_catalysts": ({"name": "sample event", "type": "CORPORATE_EVENT"},),
                "model_disagreement": True,
            }
        elif prefix.startswith("SPEC") or prefix in {"TSLA", "WEAK"}:
            profile = {
                "market_regime": "VOLATILE",
                "sector_regime": "EMERGING_INFLECTION",
                "weekly_trend_state": "UPTREND",
                "daily_trend_state": "VOLATILE",
                "setup_type": "FAILED_BREAKOUT_REVERSAL",
                "trigger_state": "WAITING_FOR_TRIGGER",
                "breakout_distance_pct": 4.5,
                "distance_to_support_pct": 3.0,
                "distance_to_resistance_pct": 7.5,
                "volatility_contraction": 0.12,
                "volatility_expansion": 0.42,
                "relative_volume": 1.8,
                "close_quality": 0.58,
                "failed_breakout": True,
                "failed_breakdown": False,
                "multi_timeframe_alignment": "CONFLICTED",
                "average_daily_dollar_volume": 1_500_000.0,
                "average_daily_volume": 80_000.0,
                "probability_estimate": 0.35,
                "expected_upside_pct": 110.0,
                "expected_downside_pct": -55.0,
                "expected_holding_days": 60.0,
                "estimated_cost_bps": 12.0,
                "calibration_status": "UNCALIBRATED",
                "expected_value_score": 41.0,
                "opportunity_cost_rank": 8,
                "catalyst_risk": "HIGH",
                "known_catalysts": (),
                "model_disagreement": True,
            }
        elif prefix.startswith("EXC"):
            profile = {
                "market_regime": "NEUTRAL",
                "sector_regime": "NEUTRAL",
                "weekly_trend_state": "DOWNTREND",
                "daily_trend_state": "DOWNTREND",
                "setup_type": "UNUSABLE",
                "trigger_state": "WAITING_FOR_TRIGGER",
                "breakout_distance_pct": -2.0,
                "distance_to_support_pct": 1.0,
                "distance_to_resistance_pct": 15.0,
                "volatility_contraction": 0.05,
                "volatility_expansion": 0.20,
                "relative_volume": 0.4,
                "close_quality": 0.40,
                "failed_breakout": False,
                "failed_breakdown": True,
                "multi_timeframe_alignment": "CONFLICTED",
                "average_daily_dollar_volume": 5_000.0,
                "average_daily_volume": 1_000.0,
                "probability_estimate": None,
                "expected_upside_pct": None,
                "expected_downside_pct": None,
                "expected_holding_days": None,
                "estimated_cost_bps": None,
                "calibration_status": "UNCALIBRATED",
                "expected_value_score": 0.0,
                "opportunity_cost_rank": None,
                "catalyst_risk": "HIGH",
                "known_catalysts": (),
                "model_disagreement": True,
                "governance_eligible": False,
                "risk_eligible": False,
            }

        if profile is None:
            return

        for field_name, value in profile.items():
            object.__setattr__(opportunity, field_name, value)

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
            "research_universes": [
                {
                    "universe_id": universe.universe_id,
                    "universe_type": universe.universe_type.value,
                    "enabled": universe.enabled,
                    "priority_mode": universe.priority_mode.value,
                    "capacity_limit": universe.capacity_limit,
                    "minimum_liquidity": universe.minimum_liquidity,
                    "minimum_data_quality": universe.minimum_data_quality,
                    "minimum_candidate_count": universe.minimum_candidate_count,
                    "maximum_candidate_count": universe.maximum_candidate_count,
                    "membership_rules": universe.membership_rules,
                    "benchmark_ids": sorted(universe.benchmark_ids),
                    "tags": sorted(universe.tags),
                }
                for universe in sorted(config.research_universes, key=lambda item: item.universe_id)
            ],
            "user_watchlist_symbols": sorted(config.user_watchlist_symbols),
            "current_holding_symbols": sorted(config.current_holding_symbols),
            "benchmark_symbols": sorted(config.benchmark_symbols),
        }
        config_json = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()[:16]
