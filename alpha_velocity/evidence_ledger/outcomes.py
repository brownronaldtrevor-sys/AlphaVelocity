"""
Outcome grading: Grade evidence ledger records over configurable time horizons.

Does not fabricate data. Only grades outcomes from available price/event information.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence, Mapping, Any

from alpha_velocity.evidence_ledger.models import (
    EvidenceLedgerRecord,
    OutcomeGrade,
    OutcomeGradeHorizon,
)


@dataclass
class PricePoint:
    """Price data point for outcome grading."""
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int


class OutcomeGrader:
    """Grades evidence ledger records against actual outcomes."""
    
    def __init__(self, price_history: Mapping[str, Sequence[PricePoint]]) -> None:
        """
        Initialize grader with price history.
        
        Args:
            price_history: Dict mapping symbol to sequence of PricePoint objects,
                          sorted chronologically
        """
        self.price_history = price_history
    
    def grade_record(
        self,
        record: EvidenceLedgerRecord,
        horizon: OutcomeGradeHorizon,
        grading_date: datetime | None = None,
    ) -> OutcomeGrade | None:
        """
        Grade a record's outcome over specified horizon.
        
        Args:
            record: The evidence ledger record to grade
            horizon: Time horizon for grading
            grading_date: Optional specific date to grade through (defaults to now)
            
        Returns:
            OutcomeGrade if sufficient price history exists, None otherwise
        """
        if grading_date is None:
            grading_date = datetime.now(timezone.utc)
        
        if grading_date.tzinfo is None:
            raise ValueError("grading_date must be timezone-aware")
        
        # Get price history for symbol
        prices = self.price_history.get(record.symbol, [])
        if not prices:
            return None
        
        # Find entry price (observation close or current price target)
        entry_price = self._get_entry_price(record)
        if entry_price is None or entry_price <= 0:
            return None
        
        entry_date = record.observation_time
        
        # Calculate target date based on horizon
        target_date = self._calculate_target_date(entry_date, horizon, record)
        
        # Find prices in range
        entry_prices_list = [
            p for p in prices
            if p.timestamp.date() == entry_date.date()
        ]
        
        if not entry_prices_list:
            return None
        
        exit_prices_list = [
            p for p in prices
            if entry_date < p.timestamp <= target_date
        ]
        
        if not exit_prices_list:
            # Insufficient data for grading
            return None
        
        # Calculate outcomes
        exit_price = exit_prices_list[-1].close_price
        
        # Forward return
        forward_return_pct = ((exit_price - entry_price) / entry_price) * 100
        
        # Maximum favorable and adverse excursions
        prices_in_window = [
            p for p in prices
            if entry_date < p.timestamp <= target_date
        ]
        
        if prices_in_window:
            highs = [p.high_price for p in prices_in_window]
            lows = [p.low_price for p in prices_in_window]
            
            max_high = max(highs) if highs else entry_price
            min_low = min(lows) if lows else entry_price
            
            max_favorable_excursion_pct = ((max_high - entry_price) / entry_price) * 100
            max_adverse_excursion_pct = ((entry_price - min_low) / entry_price) * 100
        else:
            max_favorable_excursion_pct = None
            max_adverse_excursion_pct = None
        
        # Direction
        direction_correct = (forward_return_pct > 0) if forward_return_pct != 0 else None
        
        # Magnitude error vs predicted
        predicted_target = self._get_predicted_target(record)
        magnitude_error_pct = None
        if predicted_target and predicted_target > 0:
            predicted_return = ((predicted_target - entry_price) / entry_price) * 100
            magnitude_error_pct = abs(forward_return_pct - predicted_return)
        
        # Invalidation breach
        invalidation_breach = False
        if record.research_evidence.technical and record.research_evidence.technical.primary_invalidation_price:
            inv_price = record.research_evidence.technical.primary_invalidation_price
            if prices_in_window:
                min_low = min(p.low_price for p in prices_in_window)
                invalidation_breach = min_low < inv_price
        
        # Days elapsed
        days_elapsed = (target_date - entry_date).days
        
        return OutcomeGrade(
            horizon=horizon,
            as_of_time=grading_date,
            days_elapsed=days_elapsed,
            forward_return_pct=forward_return_pct,
            max_favorable_excursion_pct=max_favorable_excursion_pct,
            max_adverse_excursion_pct=max_adverse_excursion_pct,
            direction_correct=direction_correct,
            magnitude_error_pct=magnitude_error_pct,
            invalidation_breach=invalidation_breach,
        )
    
    def grade_batch(
        self,
        records: Sequence[EvidenceLedgerRecord],
        horizon: OutcomeGradeHorizon,
    ) -> Sequence[tuple[EvidenceLedgerRecord, OutcomeGrade]]:
        """Grade a batch of records."""
        results = []
        for record in records:
            grade = self.grade_record(record, horizon)
            if grade is not None:
                results.append((record, grade))
        return results
    
    def _get_entry_price(self, record: EvidenceLedgerRecord) -> float | None:
        """Get entry price from record."""
        # Use proposed price target if available, otherwise estimate from close
        if record.decision_state.allocation and record.decision_state.allocation.proposed_price_target:
            return record.decision_state.allocation.proposed_price_target
        
        # Could use historical prices near observation_time
        return None
    
    def _get_predicted_target(self, record: EvidenceLedgerRecord) -> float | None:
        """Get predicted target price from record."""
        if record.decision_state.allocation and record.decision_state.allocation.proposed_price_target:
            return record.decision_state.allocation.proposed_price_target
        return None
    
    def _calculate_target_date(
        self,
        entry_date: datetime,
        horizon: OutcomeGradeHorizon,
        record: EvidenceLedgerRecord,
    ) -> datetime:
        """Calculate target date based on horizon."""
        if horizon == OutcomeGradeHorizon.ONE_DAY:
            return entry_date + timedelta(days=1)
        elif horizon == OutcomeGradeHorizon.FIVE_DAYS:
            return entry_date + timedelta(days=5)
        elif horizon == OutcomeGradeHorizon.TEN_DAYS:
            return entry_date + timedelta(days=10)
        elif horizon == OutcomeGradeHorizon.TWENTY_DAYS:
            return entry_date + timedelta(days=20)
        elif horizon == OutcomeGradeHorizon.CATALYST_WINDOW:
            # Use next known event or default to 30 days
            if (record.research_evidence.catalysts and
                record.research_evidence.catalysts.next_known_event_time):
                return record.research_evidence.catalysts.next_known_event_time
            return entry_date + timedelta(days=30)
        elif horizon == OutcomeGradeHorizon.INTENDED_HOLDING:
            # Use expected holding days or default to 60
            expected_days = 60
            if record.research_evidence.expectations_mispricing:
                # Try to extract expected holding
                pass
            return entry_date + timedelta(days=expected_days)
        else:
            return entry_date + timedelta(days=20)


class ForecastGrader:
    """
    Grades Expectations & Mispricing forecasts against realized metrics.
    
    Does not fabricate data. Only grades when actual metrics available.
    """
    
    def __init__(self, actual_metrics: Mapping[tuple[str, str], Mapping[str, float]]) -> None:
        """
        Initialize with actual realized metrics.
        
        Args:
            actual_metrics: Dict mapping (security_id, period_id) to
                          dict of {"revenue": x, "ebitda": y, ...}
        """
        self.actual_metrics = actual_metrics
    
    def grade_forecast(
        self,
        security_id: str,
        symbol: str,
        forecast_date: datetime,
        forecast_metrics: Mapping[str, float | None],
        period_id: str,
        grading_date: datetime | None = None,
    ) -> Mapping[str, Any]:
        """Grade a forecast against realized metrics."""
        if grading_date is None:
            grading_date = datetime.now(timezone.utc)
        
        key = (security_id, period_id)
        if key not in self.actual_metrics:
            # Insufficient data
            return {"grading_status": "INSUFFICIENT_DATA"}
        
        actual = self.actual_metrics[key]
        results = {
            "forecast_date": forecast_date.isoformat(),
            "grading_date": grading_date.isoformat(),
            "period_id": period_id,
        }
        
        # Grade each metric
        metrics_to_grade = ["revenue", "ebitda", "eps", "fcf", "margin"]
        
        for metric in metrics_to_grade:
            forecast_value = forecast_metrics.get(metric)
            actual_value = actual.get(metric)
            
            if forecast_value is None or actual_value is None:
                results[f"{metric}_error_pct"] = None
                continue
            
            if actual_value == 0:
                results[f"{metric}_error_pct"] = None
                continue
            
            error_pct = abs((actual_value - forecast_value) / actual_value) * 100
            results[f"{metric}_error_pct"] = error_pct
        
        results["grading_status"] = "GRADED"
        return results
