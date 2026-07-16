"""
Evidence-stream scorecards: Aggregate performance and recommendations by evidence lens.

Produces scorecards that track coverage, accuracy, value, and make recommendations
for validation, shadow status, or retirement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence, Mapping, Any
from collections import defaultdict

from alpha_velocity.evidence_ledger.models import (
    EvidenceLedgerRecord,
    OutcomeGrade,
    EvidenceStreamScorecard,
    EvidenceStreamRecommendation,
)


@dataclass
class ScorecardMetrics:
    """Working metrics for scorecard calculation."""
    
    stream_name: str
    sample_count: int = 0
    graded_count: int = 0
    
    # Directional
    correct_direction: int = 0
    total_graded: int = 0
    
    # Returns by bucket
    returns_by_score_bucket: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    
    # Value
    incremental_values: list[float] = field(default_factory=list)
    
    # Quality
    failures: list[str] = field(default_factory=list)
    regime_sensitivity_indicators: list[float] = field(default_factory=list)


class EvidenceStreamScorecardBuilder:
    """Builds evidence-stream scorecards from ledger records."""
    
    def build_scorecard(
        self,
        stream_name: str,
        records_with_outcomes: Sequence[tuple[EvidenceLedgerRecord, Sequence[OutcomeGrade]]],
    ) -> EvidenceStreamScorecard:
        """
        Build a comprehensive scorecard for an evidence stream.
        
        Args:
            stream_name: Name of evidence stream ("TECHNICAL", "CATALYST", etc.)
            records_with_outcomes: List of (record, outcome_grades) tuples
            
        Returns:
            EvidenceStreamScorecard with recommendations
        """
        metrics = ScorecardMetrics(stream_name=stream_name)
        
        # Process each record
        for record, outcomes in records_with_outcomes:
            if not self._uses_evidence_stream(record, stream_name):
                continue
            
            metrics.sample_count += 1
            
            if not outcomes:
                continue
            
            metrics.graded_count += 1
            
            # Process outcomes
            for outcome in outcomes:
                self._process_outcome(metrics, record, outcome)
        
        # Calculate metrics
        directional_accuracy_pct = None
        if metrics.total_graded > 0:
            directional_accuracy_pct = (metrics.correct_direction / metrics.total_graded) * 100
        
        avg_returns_by_bucket = {}
        for bucket, returns in metrics.returns_by_score_bucket.items():
            if returns:
                avg_returns_by_bucket[bucket] = sum(returns) / len(returns)
        
        incremental_value_vs_baseline_pct = None
        if metrics.incremental_values:
            avg_value = sum(metrics.incremental_values) / len(metrics.incremental_values)
            incremental_value_vs_baseline_pct = avg_value
        
        regime_sensitivity = "LOW"
        if metrics.regime_sensitivity_indicators:
            avg_sensitivity = sum(metrics.regime_sensitivity_indicators) / len(metrics.regime_sensitivity_indicators)
            if avg_sensitivity > 0.6:
                regime_sensitivity = "HIGH"
            elif avg_sensitivity > 0.3:
                regime_sensitivity = "MEDIUM"
        
        # Generate recommendation
        recommendation, confidence, reasoning = self._generate_recommendation(
            stream_name=stream_name,
            metrics=metrics,
            directional_accuracy_pct=directional_accuracy_pct,
            incremental_value=incremental_value_vs_baseline_pct,
        )
        
        return EvidenceStreamScorecard(
            stream_name=stream_name,
            sample_count=metrics.sample_count,
            graded_count=metrics.graded_count,
            availability_coverage_pct=(metrics.graded_count / metrics.sample_count * 100) if metrics.sample_count > 0 else 0.0,
            directional_accuracy_pct=directional_accuracy_pct,
            average_forward_return_by_score_bucket=avg_returns_by_bucket,
            incremental_value_vs_baseline_pct=incremental_value_vs_baseline_pct,
            failure_modes=tuple(set(metrics.failures)),
            regime_sensitivity=regime_sensitivity,
            recommendation=recommendation,
            confidence_in_recommendation=confidence,
            reasoning=reasoning,
        )
    
    def _uses_evidence_stream(self, record: EvidenceLedgerRecord, stream_name: str) -> bool:
        """Check if record uses specified evidence stream."""
        stream_map = {
            "TECHNICAL": record.research_evidence.technical,
            "CATALYST": record.research_evidence.catalysts,
            "VALUATION": record.research_evidence.valuation,
            "EXPECTATIONS": record.research_evidence.expectations_mispricing,
            "INDUSTRY_MACRO": record.research_evidence.industry_macro,
            "SENTIMENT": len(record.research_evidence.sentiment_other) > 0,
        }
        
        evidence = stream_map.get(stream_name)
        return evidence is not None and evidence
    
    def _process_outcome(
        self,
        metrics: ScorecardMetrics,
        record: EvidenceLedgerRecord,
        outcome: OutcomeGrade,
    ) -> None:
        """Process a single outcome for metrics calculation."""
        
        # Direction
        if outcome.direction_correct is not None:
            metrics.total_graded += 1
            if outcome.direction_correct:
                metrics.correct_direction += 1
        
        # Return by score bucket
        if outcome.forward_return_pct is not None:
            # Get ranking score for bucket
            if record.decision_state.ranking:
                score = record.decision_state.ranking.overall_research_score
                if 80 <= score <= 100:
                    bucket = "SCORE_80_100"
                elif 60 <= score < 80:
                    bucket = "SCORE_60_80"
                elif 40 <= score < 60:
                    bucket = "SCORE_40_60"
                else:
                    bucket = "SCORE_0_40"
                
                metrics.returns_by_score_bucket[bucket].append(outcome.forward_return_pct)
        
        # Failures
        if outcome.invalidation_breach:
            metrics.failures.append("INVALIDATION_BREACH")
        
        if outcome.max_adverse_excursion_pct and outcome.max_adverse_excursion_pct > 20:
            metrics.failures.append("HIGH_ADVERSE_EXCURSION")
        
        # Regime sensitivity
        if outcome.max_favorable_excursion_pct and outcome.forward_return_pct:
            if outcome.max_favorable_excursion_pct > 0:
                realized_pct_of_max = (
                    outcome.forward_return_pct / outcome.max_favorable_excursion_pct
                )
                if realized_pct_of_max < 0.3:
                    metrics.regime_sensitivity_indicators.append(0.8)  # High sensitivity
                elif realized_pct_of_max > 0.8:
                    metrics.regime_sensitivity_indicators.append(0.2)  # Low sensitivity
                else:
                    metrics.regime_sensitivity_indicators.append(0.5)
    
    def _generate_recommendation(
        self,
        stream_name: str,
        metrics: ScorecardMetrics,
        directional_accuracy_pct: float | None,
        incremental_value: float | None,
    ) -> tuple[str, float, str]:
        """Generate recommendation for evidence stream."""
        
        if metrics.sample_count == 0:
            return (
                EvidenceStreamRecommendation.INSUFFICIENT_DATA.value,
                0.9,
                "No samples graded yet"
            )
        
        if metrics.graded_count < metrics.sample_count * 0.5:
            return (
                EvidenceStreamRecommendation.INSUFFICIENT_DATA.value,
                0.8,
                f"Only {metrics.graded_count}/{metrics.sample_count} graded"
            )
        
        # Check for high failure rate
        if "INVALIDATION_BREACH" in metrics.failures:
            failure_rate = len(metrics.failures) / metrics.graded_count
            if failure_rate > 0.3:
                return (
                    EvidenceStreamRecommendation.QUARANTINE.value,
                    0.85,
                    f"High failure rate: {failure_rate*100:.1f}%"
                )
        
        # Check directional accuracy
        if directional_accuracy_pct is not None:
            if directional_accuracy_pct < 45:
                return (
                    EvidenceStreamRecommendation.RETIRE.value,
                    0.85,
                    f"Poor directional accuracy: {directional_accuracy_pct:.1f}%"
                )
            
            if directional_accuracy_pct > 60:
                # Check incremental value
                if incremental_value and incremental_value > 5:
                    return (
                        EvidenceStreamRecommendation.ELIGIBLE_FOR_VALIDATION.value,
                        0.8,
                        f"Good accuracy ({directional_accuracy_pct:.1f}%) and value ({incremental_value:.1f}%)"
                    )
        
        # For shadow/unvalidated streams
        if stream_name in ["EXPECTATIONS", "SENTIMENT"]:
            return (
                EvidenceStreamRecommendation.REMAIN_SHADOW.value,
                0.7,
                f"Continue as shadow research pending validation"
            )
        
        # Default
        return (
            EvidenceStreamRecommendation.REMAIN_SHADOW.value,
            0.5,
            "Insufficient evidence for strong recommendation"
        )
    
    def build_aggregate_scorecard(
        self,
        all_records_with_outcomes: Sequence[tuple[EvidenceLedgerRecord, Sequence[OutcomeGrade]]],
    ) -> Sequence[EvidenceStreamScorecard]:
        """Build scorecards for all evidence streams."""
        
        streams = ["TECHNICAL", "CATALYST", "VALUATION", "EXPECTATIONS", "INDUSTRY_MACRO", "SENTIMENT"]
        scorecards = []
        
        for stream in streams:
            scorecard = self.build_scorecard(stream, all_records_with_outcomes)
            scorecards.append(scorecard)
        
        return scorecards
