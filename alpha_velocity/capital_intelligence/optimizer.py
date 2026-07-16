"""Capital Intelligence Optimizer: research-only allocation proposal engine."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from alpha_velocity.capital_intelligence.models import (
    CapitalAllocationProposal,
    ConcentrationMetrics,
    CurrentHolding,
    LiquidityWarning,
    ProposalState,
    ProposedPosition,
    RotationAnalysis,
    SizingConfig,
)
from alpha_velocity.capital_intelligence.sizing import get_sizer
from alpha_velocity.opportunity_ranking import RankingBatch, RankingResult, RankingState


class CapitalIntelligenceOptimizer:
    """
    Research-only capital allocation optimizer.
    
    Consumes ranked opportunities and portfolio state to produce transparent
    allocation proposals. Does NOT execute, approve risk, or modify portfolio.
    """

    def __init__(self) -> None:
        """Initialize the optimizer."""
        pass

    def optimize(
        self,
        *,
        ranking_batch: RankingBatch,
        opportunities: list[Any],
        current_cash: float,
        current_holdings: list[CurrentHolding],
        portfolio_equity: float,
        sizing_config: SizingConfig,
        warehouse_manifest_hash: str = "",
        dataset_manifest_hash: str = "",
    ) -> CapitalAllocationProposal:
        """
        Generate capital allocation proposal from ranked opportunities.
        
        Args:
            ranking_batch: RankingBatch with ranked opportunities (RankingResult objects)
            opportunities: List of Opportunity objects matching ranked results
            current_cash: Available cash in dollars
            current_holdings: List of current positions
            portfolio_equity: Total portfolio equity
            sizing_config: SizingConfig for position sizing method and constraints
            warehouse_manifest_hash: Data provenance hash
            dataset_manifest_hash: Dataset snapshot hash
            
        Returns:
            CapitalAllocationProposal with transparent research allocation
        """
        observation_time = ranking_batch.observation_time
        proposal_id = f"PROPOSAL-{observation_time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        portfolio_snapshot_id = f"SNAP-{observation_time.strftime('%Y%m%d-%H%M%S')}"

        # Start with current state
        starting_cash = current_cash
        starting_equity = portfolio_equity
        current_gross = sum(abs(h.current_value) for h in current_holdings)
        current_net = sum(h.current_value for h in current_holdings)
        starting_gross_exposure = current_gross
        starting_net_exposure = current_net

        # Available capital for new allocations
        available_capital = starting_cash
        
        # Track proposed allocations
        proposed_positions: list[ProposedPosition] = []
        rejected_opportunities: dict[str, str] = {}
        constraint_binding: list[str] = []
        warnings: list[str] = []
        
        # Sizing method
        sizer = get_sizer(sizing_config.method)
        
        # Build opportunity lookup by ID
        opportunity_map = {opp.opportunity_id: opp for opp in opportunities}
        
        # Process ranked opportunities
        rank = 1
        for ranked_result in ranking_batch.ranked_opportunities:
            # Look up the corresponding opportunity object
            opp_opportunity = opportunity_map.get(ranked_result.opportunity_id)
            if not opp_opportunity:
                rejected_opportunities[ranked_result.opportunity_id] = "Opportunity details not provided"
                rank += 1
                continue
            
            # Check if opportunity meets calibration threshold
            if ranked_result.validation_status == "UNCALIBRATED":
                calibration_multiplier = sizing_config.uncalibrated_position_cap_pct / sizing_config.max_single_position_pct
                max_position_pct = sizing_config.max_single_position_pct * calibration_multiplier
            else:
                max_position_pct = sizing_config.max_single_position_pct
            
            # Calculate position size
            position_size = sizer.size_position(
                opportunity_rank=rank,
                ranking_score=ranked_result.overall_research_score,
                calibration_status=ranked_result.validation_status,
                available_capital=available_capital,
                portfolio_equity=portfolio_equity,
                existing_positions_value=current_gross,
                max_single_position_pct=max_position_pct,
                uncalibrated_cap_pct=sizing_config.uncalibrated_position_cap_pct,
            )
            
            # Check if position would exceed constraints
            if position_size <= 0:
                rejected_opportunities[ranked_result.opportunity_id] = "Insufficient capital or size zero"
                rank += 1
                continue
            
            # Check gross exposure constraint
            if current_gross + position_size > portfolio_equity * (sizing_config.max_gross_exposure_pct / 100.0):
                rejected_opportunities[ranked_result.opportunity_id] = "Gross exposure limit"
                constraint_binding.append("max_gross_exposure_pct")
                break  # No point checking further if constrained
            
            # Check liquidity constraints
            liquidity_ok, liquidity_warning = self._check_liquidity(
                symbol=opp_opportunity.symbol,
                position_size=position_size,
                portfolio_equity=portfolio_equity,
                sizing_config=sizing_config,
            )
            
            if not liquidity_ok:
                rejected_opportunities[ranked_result.opportunity_id] = f"Liquidity: {liquidity_warning}"
                continue
            
            # Deduct from available capital
            available_capital -= position_size
            current_gross += position_size
            
            # Create proposed position
            existing_holding = self._find_existing_holding(current_holdings, opp_opportunity.symbol)
            
            # Get target price from resistance levels if available
            target_price = 0.0
            if hasattr(opp_opportunity, 'weekly_resistance_levels') and opp_opportunity.weekly_resistance_levels:
                target_price = opp_opportunity.weekly_resistance_levels[0].get("level", 0.0) if isinstance(opp_opportunity.weekly_resistance_levels[0], dict) else 0.0
            
            proposed = ProposedPosition(
                opportunity_id=ranked_result.opportunity_id,
                security_id=opp_opportunity.security_id,
                symbol=opp_opportunity.symbol,
                ranking_state=ranked_result.ranking_state.value,
                overall_research_score=ranked_result.overall_research_score,
                intrinsic_score=ranked_result.intrinsic_opportunity_score,
                timing_score=ranked_result.timing_opportunity_score,
                swing_value_score=ranked_result.expected_swing_value_score,
                calibration_status=ranked_result.validation_status,
                proposed_quantity=position_size / max(getattr(opp_opportunity, 'weekly_structure_quality', 0.5), 0.1),  # Normalize by quality
                proposed_price_target=target_price,
                current_holding_id=existing_holding.security_id if existing_holding else None,
                sector=getattr(opp_opportunity, 'sector', ''),
                industry=getattr(opp_opportunity, 'industry', ''),
            )
            
            proposed_positions.append(proposed)
            rank += 1
        
        # Determine proposal state
        proposal_state = self._determine_proposal_state(
            proposed_positions=proposed_positions,
            available_capital=available_capital,
            starting_cash=starting_cash,
            sizing_config=sizing_config,
            ranking_batch=ranking_batch,
        )
        
        # Calculate concentration metrics
        concentration_metrics = self._calculate_concentration(
            proposed_positions=proposed_positions,
            portfolio_equity=portfolio_equity,
        )
        
        # Calculate expected contributions
        exp_upside = sum(p.swing_value_score * (p.proposed_value / portfolio_equity) for p in proposed_positions) / 100.0
        exp_downside = 0.0  # Would calculate from downside estimates
        total_contribution = exp_upside + exp_downside
        
        # Proposed cash
        proposed_cash = starting_cash - sum(p.proposed_value for p in proposed_positions)
        proposed_gross = current_gross
        proposed_net = current_net + sum(p.proposed_value for p in proposed_positions)
        
        # Calculate turnover and costs
        turnover = self._calculate_turnover(
            current_holdings=current_holdings,
            proposed_positions=proposed_positions,
        )
        estimated_costs = turnover * (sizing_config.transaction_cost_pct / 100.0)
        
        # Build proposal
        proposal = CapitalAllocationProposal(
            proposal_id=proposal_id,
            observation_time=observation_time,
            portfolio_snapshot_id=portfolio_snapshot_id,
            ranking_run_id=ranking_batch.universe_snapshot_id,
            proposal_state=proposal_state,
            starting_cash=starting_cash,
            starting_equity=starting_equity,
            starting_gross_exposure=starting_gross_exposure,
            starting_net_exposure=starting_net_exposure,
            current_holdings=tuple(current_holdings),
            proposed_holdings=tuple(proposed_positions),
            proposed_cash=proposed_cash,
            proposed_gross_exposure=proposed_gross,
            proposed_net_exposure=proposed_net,
            proposed_cash_weight_pct=(proposed_cash / portfolio_equity) * 100.0 if portfolio_equity > 0 else 0.0,
            expected_portfolio_contribution_pct=total_contribution * 100.0,
            expected_upside_contribution_pct=exp_upside * 100.0,
            expected_downside_contribution_pct=exp_downside * 100.0,
            turnover_estimate_pct=turnover * 100.0,
            estimated_transaction_costs=estimated_costs,
            concentration_metrics=concentration_metrics,
            rejected_opportunities=rejected_opportunities,
            constraint_violations=tuple(set(constraint_binding)),
            warnings=tuple(warnings),
            sizing_method_used=sizing_config.method,
            constraint_binding=tuple(set(constraint_binding)),
            evidence_lineage={
                "ranking_batch_id": ranking_batch.universe_snapshot_id,
                "observation_time": observation_time.isoformat(),
                "opportunities_evaluated": len(ranking_batch.ranked_opportunities),
                "opportunities_proposed": len(proposed_positions),
                "opportunities_rejected": len(rejected_opportunities),
            },
            configuration_manifest={
                "sizing_method": sizing_config.method,
                "max_single_position_pct": sizing_config.max_single_position_pct,
                "max_gross_exposure_pct": sizing_config.max_gross_exposure_pct,
                "min_cash_reserve_pct": sizing_config.min_cash_reserve_pct,
                "uncalibrated_position_cap_pct": sizing_config.uncalibrated_position_cap_pct,
            },
        )
        
        return proposal

    def _find_existing_holding(
        self, current_holdings: list[CurrentHolding], symbol: str
    ) -> CurrentHolding | None:
        """Find existing holding by symbol."""
        for holding in current_holdings:
            if holding.symbol == symbol:
                return holding
        return None

    def _check_liquidity(
        self,
        *,
        symbol: str,
        position_size: float,
        portfolio_equity: float,
        sizing_config: SizingConfig,
    ) -> tuple[bool, str]:
        """Check if position respects liquidity constraints."""
        # Stub: in production would check avg daily volume, bid-ask spread, etc.
        position_pct = (position_size / portfolio_equity) * 100.0
        
        if position_pct > sizing_config.max_participation_pct * 100.0:
            return False, f"Position would be {position_pct:.2f}% of portfolio, max {sizing_config.max_participation_pct * 100:.2f}%"
        
        return True, ""

    def _determine_proposal_state(
        self,
        *,
        proposed_positions: list[ProposedPosition],
        available_capital: float,
        starting_cash: float,
        sizing_config: SizingConfig,
        ranking_batch: RankingBatch,
    ) -> ProposalState:
        """Determine the proposal state based on conditions."""
        if not proposed_positions:
            return ProposalState.HOLD_CURRENT_PORTFOLIO
        
        # Check if any opportunities are uncalibrated
        uncalibrated = any(p.calibration_status == "UNCALIBRATED" for p in proposed_positions)
        if uncalibrated and len(proposed_positions) < 3:
            return ProposalState.INSUFFICIENT_CALIBRATION
        
        # Check cash position
        cash_pct = (available_capital / (available_capital + sum(p.proposed_value for p in proposed_positions))) * 100.0
        if cash_pct > 50.0:
            return ProposalState.RAISE_CASH
        
        # Default: ready for risk review
        return ProposalState.PROPOSAL_READY_FOR_RISK_REVIEW

    def _calculate_concentration(
        self,
        *,
        proposed_positions: list[ProposedPosition],
        portfolio_equity: float,
    ) -> ConcentrationMetrics:
        """Calculate concentration metrics for proposed portfolio."""
        if not proposed_positions:
            return ConcentrationMetrics(
                largest_position_pct=0.0,
                top_5_positions_pct=0.0,
                top_10_positions_pct=0.0,
            )
        
        position_pcts = sorted(
            [(p.proposed_value / portfolio_equity) * 100.0 for p in proposed_positions],
            reverse=True,
        )
        
        return ConcentrationMetrics(
            largest_position_pct=position_pcts[0] if position_pcts else 0.0,
            top_5_positions_pct=sum(position_pcts[:5]),
            top_10_positions_pct=sum(position_pcts[:10]),
        )

    def _calculate_turnover(
        self,
        *,
        current_holdings: list[CurrentHolding],
        proposed_positions: list[ProposedPosition],
    ) -> float:
        """Calculate portfolio turnover as fraction of equity."""
        total_sales = 0.0
        
        # Sales of positions not in proposal
        proposed_symbols = {p.symbol for p in proposed_positions}
        for holding in current_holdings:
            if holding.symbol not in proposed_symbols:
                total_sales += holding.current_value
        
        # Buys of new positions
        total_buys = sum(p.proposed_value for p in proposed_positions)
        
        # Turnover is average of buys and sells
        turnover = (total_buys + total_sales) / 2.0
        
        return turnover
