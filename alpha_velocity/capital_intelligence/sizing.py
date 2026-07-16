"""Position sizing strategies for capital allocation."""

from __future__ import annotations

from typing import Any


class PositionSizer:
    """Base class for position sizing methods."""

    def size_position(
        self,
        *,
        opportunity_rank: int,
        ranking_score: float,
        calibration_status: str,
        available_capital: float,
        portfolio_equity: float,
        existing_positions_value: float,
        max_single_position_pct: float,
        uncalibrated_cap_pct: float,
    ) -> float:
        """Calculate position size in dollars. Must be overridden."""
        raise NotImplementedError


class ProportionalExpectedValueSizer(PositionSizer):
    """
    Size proportional to research score, capped by concentration limits.
    
    Higher-ranked opportunities get more capital, but no single position
    can exceed max_single_position_pct of portfolio equity.
    """

    def size_position(
        self,
        *,
        opportunity_rank: int,
        ranking_score: float,
        calibration_status: str,
        available_capital: float,
        portfolio_equity: float,
        existing_positions_value: float,
        max_single_position_pct: float,
        uncalibrated_cap_pct: float,
    ) -> float:
        """Size based on research score rank."""
        # Uncalibrated opportunities get reduced allocation
        score_multiplier = 1.0 if calibration_status == "CALIBRATED" else uncalibrated_cap_pct / max_single_position_pct
        
        # Base allocation proportional to rank (higher rank = more capital)
        base_allocation_pct = max_single_position_pct * (1.0 / max(opportunity_rank, 1))
        adjusted_allocation_pct = base_allocation_pct * score_multiplier
        
        # Hard cap at max position percentage
        final_allocation_pct = min(adjusted_allocation_pct, max_single_position_pct)
        
        # Apply capital constraints
        max_from_available = available_capital * 0.5  # Use at most 50% of available for one position
        position_size = portfolio_equity * (final_allocation_pct / 100.0)
        
        return min(position_size, max_from_available)


class RiskBudgetSizer(PositionSizer):
    """
    Allocate equal risk contribution across positions.
    
    If a position has higher volatility/uncertainty, it receives smaller notional size
    to maintain consistent risk contribution.
    """

    def size_position(
        self,
        *,
        opportunity_rank: int,
        ranking_score: float,
        calibration_status: str,
        available_capital: float,
        portfolio_equity: float,
        existing_positions_value: float,
        max_single_position_pct: float,
        uncalibrated_cap_pct: float,
    ) -> float:
        """Size based on risk budget (equal risk contribution)."""
        # For this milestone, approximate as proportional with uncertainty discount
        # In production: would use implied volatility and realized volatility
        
        score_multiplier = 1.0 if calibration_status == "CALIBRATED" else uncalibrated_cap_pct / max_single_position_pct
        
        # Equal-risk sizing: first rank positions get equal risk allocation
        equal_risk_allocation_pct = max_single_position_pct * score_multiplier
        
        position_size = portfolio_equity * (equal_risk_allocation_pct / 100.0)
        max_from_available = available_capital * 0.4
        
        return min(position_size, max_from_available)


class VolatilityAwareSizer(PositionSizer):
    """
    Adjust position size based on volatility regime.
    
    Higher volatility → smaller position. Maintains consistent volatility contribution.
    """

    def size_position(
        self,
        *,
        opportunity_rank: int,
        ranking_score: float,
        calibration_status: str,
        available_capital: float,
        portfolio_equity: float,
        existing_positions_value: float,
        max_single_position_pct: float,
        uncalibrated_cap_pct: float,
    ) -> float:
        """Size with volatility adjustment."""
        # For this milestone: stub implementation
        # Production would: calculate implied vol, adjust sizing inverse to vol
        score_multiplier = 1.0 if calibration_status == "CALIBRATED" else uncalibrated_cap_pct / max_single_position_pct
        
        # Base allocation
        base_allocation_pct = max_single_position_pct * 0.7 * score_multiplier
        
        position_size = portfolio_equity * (base_allocation_pct / 100.0)
        max_from_available = available_capital * 0.35
        
        return min(position_size, max_from_available)


class EqualRiskContributionSizer(PositionSizer):
    """
    Target equal risk contribution across all positions.
    
    Each position contributes the same risk dollars, regardless of volatility.
    """

    def size_position(
        self,
        *,
        opportunity_rank: int,
        ranking_score: float,
        calibration_status: str,
        available_capital: float,
        portfolio_equity: float,
        existing_positions_value: float,
        max_single_position_pct: float,
        uncalibrated_cap_pct: float,
    ) -> float:
        """Equal risk contribution sizing."""
        score_multiplier = 1.0 if calibration_status == "CALIBRATED" else uncalibrated_cap_pct / max_single_position_pct
        
        # ERC: each position gets equal allocation with calibration adjustment
        equal_allocation_pct = max_single_position_pct * 0.8 * score_multiplier
        
        position_size = portfolio_equity * (equal_allocation_pct / 100.0)
        max_from_available = available_capital * 0.45
        
        return min(position_size, max_from_available)


class RankBasedSizer(PositionSizer):
    """
    Size proportional to rank percentile.
    
    Top-ranked opportunity gets maximum, lower ranks get progressively smaller allocations.
    """

    def size_position(
        self,
        *,
        opportunity_rank: int,
        ranking_score: float,
        calibration_status: str,
        available_capital: float,
        portfolio_equity: float,
        existing_positions_value: float,
        max_single_position_pct: float,
        uncalibrated_cap_pct: float,
    ) -> float:
        """Rank-based sizing (top ranks get more)."""
        score_multiplier = 1.0 if calibration_status == "CALIBRATED" else uncalibrated_cap_pct / max_single_position_pct
        
        # Decrease allocation with rank (rank 1 gets max, rank 10 gets min)
        rank_factor = max(0.1, 1.0 - (opportunity_rank - 1) * 0.08)
        base_allocation_pct = max_single_position_pct * rank_factor * score_multiplier
        
        position_size = portfolio_equity * (base_allocation_pct / 100.0)
        max_from_available = available_capital * 0.5
        
        return min(position_size, max_from_available)


class CashPreservingSizer(PositionSizer):
    """
    Conservative sizing that prioritizes cash preservation.
    
    Sizes positions smaller to maintain larger cash buffer, useful when
    uncertainty is high or opportunities are uncalibrated.
    """

    def size_position(
        self,
        *,
        opportunity_rank: int,
        ranking_score: float,
        calibration_status: str,
        available_capital: float,
        portfolio_equity: float,
        existing_positions_value: float,
        max_single_position_pct: float,
        uncalibrated_cap_pct: float,
    ) -> float:
        """Conservative cash-preserving sizing."""
        score_multiplier = 1.0 if calibration_status == "CALIBRATED" else uncalibrated_cap_pct / max_single_position_pct
        
        # Reserve more capital: use only 50-60% of available
        conservative_allocation_pct = max_single_position_pct * 0.5 * score_multiplier
        
        position_size = portfolio_equity * (conservative_allocation_pct / 100.0)
        max_from_available = available_capital * 0.25  # Only 25% of available
        
        return min(position_size, max_from_available)


def get_sizer(method: str) -> PositionSizer:
    """Get a position sizer by method name."""
    sizers = {
        "proportional_ev": ProportionalExpectedValueSizer(),
        "risk_budget": RiskBudgetSizer(),
        "volatility_aware": VolatilityAwareSizer(),
        "equal_risk": EqualRiskContributionSizer(),
        "rank_based": RankBasedSizer(),
        "cash_preserving": CashPreservingSizer(),
    }
    
    if method not in sizers:
        raise ValueError(
            f"Unknown sizing method: {method}. "
            f"Choose from: {', '.join(sizers.keys())}"
        )
    
    return sizers[method]
