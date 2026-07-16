"""
Evidence ledger reporting: Generate deterministic JSON and Markdown reports.

Reports contain decision snapshots, evidence summaries, influence maps, and grades.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Sequence, Mapping, Any

from alpha_velocity.evidence_ledger.models import (
    EvidenceLedgerRecord,
    OutcomeGrade,
    EvidenceStreamScorecard,
)


class EvidenceLedgerReport:
    """Generates deterministic reports from evidence ledger records."""
    
    def __init__(self, record: EvidenceLedgerRecord) -> None:
        self.record = record
    
    def to_json(self) -> str:
        """Serialize report to deterministic JSON."""
        report_data = self._build_report_dict()
        return json.dumps(report_data, default=str, sort_keys=True, indent=2)
    
    def to_markdown(self) -> str:
        """Generate Markdown report."""
        lines = []
        
        # Header
        lines.append("# Evidence Ledger Report\n")
        lines.append(f"**Record ID**: {self.record.record_id}\n")
        lines.append(f"**Observation Time**: {self.record.observation_time.isoformat()}\n")
        lines.append(f"**Created At**: {self.record.created_at.isoformat()}\n")
        
        # Security
        lines.append(f"\n## Security\n")
        lines.append(f"- **Symbol**: {self.record.symbol}")
        lines.append(f"- **Security ID**: {self.record.security_id}")
        lines.append(f"- **Universe Snapshot**: {self.record.universe_snapshot_id}")
        
        # Decision Snapshot
        lines.append(self._markdown_decision_snapshot())
        
        # Evidence Summary
        lines.append(self._markdown_evidence_summary())
        
        # Influence Map
        lines.append(self._markdown_influence_map())
        
        # Outcomes
        if self.record.outcome_grades:
            lines.append(self._markdown_outcomes())
        
        # Scorecards
        if self.record.evidence_scorecards:
            lines.append(self._markdown_scorecards())
        
        return "\n".join(lines)
    
    def _build_report_dict(self) -> dict[str, Any]:
        """Build complete report dictionary."""
        return {
            "record_id": self.record.record_id,
            "observation_time": self.record.observation_time.isoformat(),
            "symbol": self.record.symbol,
            "security_id": self.record.security_id,
            "decision_snapshot": self._decision_snapshot_dict(),
            "evidence_summary": self._evidence_summary_dict(),
            "influence_map": self._influence_map_dict(),
            "outcomes": [asdict(g) for g in self.record.outcome_grades],
            "scorecards": [self._scorecard_dict(s) for s in self.record.evidence_scorecards],
        }
    
    def _decision_snapshot_dict(self) -> dict[str, Any]:
        """Build decision snapshot."""
        snapshot = {
            "opportunity_classification": self.record.decision_state.opportunity_classification,
        }
        
        if self.record.decision_state.ranking:
            r = self.record.decision_state.ranking
            snapshot["ranking"] = {
                "rank": r.rank,
                "percentile": r.percentile,
                "overall_score": r.overall_research_score,
                "state": r.ranking_state,
                "positive_contributors": r.positive_contributors,
                "negative_contributors": r.negative_contributors,
                "warnings": r.warnings,
            }
        
        if self.record.decision_state.allocation:
            a = self.record.decision_state.allocation
            snapshot["allocation"] = {
                "proposal_id": a.proposal_id,
                "proposed_weight": a.proposed_allocation_weight,
                "proposed_rotation": a.proposed_rotation,
                "rotation_target": a.rotation_target_symbol,
                "binding_constraints": a.binding_constraints,
            }
        
        rg = self.record.decision_state.risk_governance
        snapshot["risk_governance"] = {
            "risk_review_required": rg.risk_review_required,
            "risk_review_status": rg.risk_review_status,
            "governance_review_required": rg.governance_review_required,
            "governance_review_status": rg.governance_review_status,
            "execution_authorized": rg.execution_authorized,
        }
        
        return snapshot
    
    def _evidence_summary_dict(self) -> dict[str, Any]:
        """Build evidence summary."""
        summary = {}
        
        if self.record.research_evidence.technical:
            t = self.record.research_evidence.technical
            summary["technical"] = {
                "quality": t.weekly_structure_quality or t.daily_structure_quality,
                "trend": t.weekly_trend_state or t.daily_trend_state,
                "volatility": t.weekly_volatility_state or t.daily_volatility_state,
                "confidence": t.confidence_level,
            }
        
        if self.record.research_evidence.catalysts:
            c = self.record.research_evidence.catalysts
            summary["catalysts"] = {
                "next_event": c.next_known_event_time.isoformat() if c.next_known_event_time else None,
                "catalyst_risk": c.catalyst_risk,
                "confidence": c.confidence_level,
            }
        
        if self.record.research_evidence.valuation:
            v = self.record.research_evidence.valuation
            summary["valuation"] = {
                "pe_ratio": v.pe_ratio,
                "ev_to_ebitda": v.ev_to_ebitda,
                "free_cf_yield": v.free_cash_flow_yield,
                "confidence": v.confidence_level,
            }
        
        if self.record.research_evidence.expectations_mispricing:
            e = self.record.research_evidence.expectations_mispricing
            summary["expectations"] = {
                "mispricing_magnitude": e.mispricing_magnitude_estimate,
                "consensus_gap": e.consensus_gap_direction,
                "validation_status": e.validation_status,
                "confidence": e.confidence_level,
            }
        
        return summary
    
    def _influence_map_dict(self) -> dict[str, Any]:
        """Build influence map."""
        weights = self.record.influence_weights
        return {
            "technical": {
                "ranking_influence": weights.technical_ranking_influence,
                "allocation_influence": weights.technical_allocation_influence,
                "validation_status": weights.technical_validation_status,
            },
            "catalyst": {
                "ranking_influence": weights.catalyst_ranking_influence,
                "allocation_influence": weights.catalyst_allocation_influence,
                "validation_status": weights.catalyst_validation_status,
            },
            "valuation": {
                "ranking_influence": weights.valuation_ranking_influence,
                "allocation_influence": weights.valuation_allocation_influence,
                "validation_status": weights.valuation_validation_status,
            },
            "expectations": {
                "ranking_influence": weights.expectations_ranking_influence,
                "allocation_influence": weights.expectations_allocation_influence,
                "validation_status": weights.expectations_validation_status,
            },
            "industry": {
                "ranking_influence": weights.industry_ranking_influence,
                "allocation_influence": weights.industry_allocation_influence,
                "validation_status": weights.industry_validation_status,
            },
        }
    
    def _scorecard_dict(self, scorecard: EvidenceStreamScorecard) -> dict[str, Any]:
        """Convert scorecard to dict."""
        return {
            "stream_name": scorecard.stream_name,
            "sample_count": scorecard.sample_count,
            "graded_count": scorecard.graded_count,
            "directional_accuracy_pct": scorecard.directional_accuracy_pct,
            "incremental_value_vs_baseline_pct": scorecard.incremental_value_vs_baseline_pct,
            "regime_sensitivity": scorecard.regime_sensitivity,
            "recommendation": scorecard.recommendation,
            "confidence": scorecard.confidence_in_recommendation,
        }
    
    def _markdown_decision_snapshot(self) -> str:
        """Generate decision snapshot markdown."""
        lines = ["\n## Decision Snapshot\n"]
        
        lines.append(f"**Classification**: {self.record.decision_state.opportunity_classification}\n")
        
        if self.record.decision_state.ranking:
            r = self.record.decision_state.ranking
            lines.append(f"\n### Ranking\n")
            lines.append(f"- **Rank**: {r.rank}")
            lines.append(f"- **Percentile**: {r.percentile:.1f}%")
            lines.append(f"- **Overall Score**: {r.overall_research_score:.1f}/100")
            lines.append(f"- **State**: {r.ranking_state}")
            
            if r.positive_contributors:
                lines.append(f"\n**Positive Contributors**: {', '.join(r.positive_contributors)}")
            if r.negative_contributors:
                lines.append(f"**Negative Contributors**: {', '.join(r.negative_contributors)}")
            if r.warnings:
                lines.append(f"**Warnings**: {', '.join(r.warnings)}")
        
        if self.record.decision_state.allocation:
            a = self.record.decision_state.allocation
            lines.append(f"\n### Allocation\n")
            if a.proposed_allocation_weight:
                lines.append(f"- **Proposed Weight**: {a.proposed_allocation_weight*100:.1f}%")
            if a.proposed_rotation:
                lines.append(f"- **Rotation Target**: {a.rotation_target_symbol}")
            if a.binding_constraints:
                lines.append(f"- **Binding Constraints**: {', '.join(a.binding_constraints)}")
        
        rg = self.record.decision_state.risk_governance
        lines.append(f"\n### Risk & Governance\n")
        lines.append(f"- **Risk Review**: {rg.risk_review_status}")
        lines.append(f"- **Governance Review**: {rg.governance_review_status}")
        lines.append(f"- **Execution Authorized**: {rg.execution_authorized}")
        
        return "".join(lines)
    
    def _markdown_evidence_summary(self) -> str:
        """Generate evidence summary markdown."""
        lines = ["\n## Evidence Summary\n"]
        
        if self.record.research_evidence.technical:
            t = self.record.research_evidence.technical
            lines.append("### Technical\n")
            if t.weekly_structure_quality:
                lines.append(f"- **Weekly Structure**: {t.weekly_structure_quality:.1f}/100")
            if t.daily_structure_quality:
                lines.append(f"- **Daily Structure**: {t.daily_structure_quality:.1f}/100")
            lines.append(f"- **Alignment**: {t.multi_timeframe_alignment}")
            lines.append(f"- **Confidence**: {t.confidence_level}\n")
        
        if self.record.research_evidence.catalysts:
            c = self.record.research_evidence.catalysts
            lines.append("### Catalysts\n")
            if c.next_known_event_time:
                lines.append(f"- **Next Event**: {c.next_known_event_time.isoformat()}")
            lines.append(f"- **Catalyst Risk**: {c.catalyst_risk}\n")
        
        return "".join(lines)
    
    def _markdown_influence_map(self) -> str:
        """Generate influence map markdown."""
        lines = ["\n## Influence Map\n"]
        
        weights = self.record.influence_weights
        
        lines.append("| Evidence Stream | Ranking Influence | Allocation Influence | Validation |\n")
        lines.append("|---|---|---|---|\n")
        lines.append(f"| Technical | {weights.technical_ranking_influence} | {weights.technical_allocation_influence} | {weights.technical_validation_status} |\n")
        lines.append(f"| Catalyst | {weights.catalyst_ranking_influence} | {weights.catalyst_allocation_influence} | {weights.catalyst_validation_status} |\n")
        lines.append(f"| Valuation | {weights.valuation_ranking_influence} | {weights.valuation_allocation_influence} | {weights.valuation_validation_status} |\n")
        lines.append(f"| Expectations | {weights.expectations_ranking_influence} | {weights.expectations_allocation_influence} | {weights.expectations_validation_status} |\n")
        lines.append(f"| Industry | {weights.industry_ranking_influence} | {weights.industry_allocation_influence} | {weights.industry_validation_status} |\n")
        
        return "".join(lines)
    
    def _markdown_outcomes(self) -> str:
        """Generate outcomes markdown."""
        lines = ["\n## Outcomes\n"]
        
        for grade in self.record.outcome_grades:
            lines.append(f"### {grade.horizon.value}\n")
            if grade.forward_return_pct is not None:
                lines.append(f"- **Forward Return**: {grade.forward_return_pct:+.2f}%")
            if grade.max_favorable_excursion_pct is not None:
                lines.append(f"- **Max Favorable Excursion**: {grade.max_favorable_excursion_pct:.2f}%")
            if grade.direction_correct is not None:
                lines.append(f"- **Direction**: {'✓ Correct' if grade.direction_correct else '✗ Wrong'}")
            lines.append()
        
        return "".join(lines)
    
    def _markdown_scorecards(self) -> str:
        """Generate scorecards markdown."""
        lines = ["\n## Evidence-Stream Scorecards\n"]
        
        for scorecard in self.record.evidence_scorecards:
            lines.append(f"### {scorecard.stream_name}\n")
            lines.append(f"- **Samples**: {scorecard.graded_count}/{scorecard.sample_count}")
            if scorecard.directional_accuracy_pct:
                lines.append(f"- **Directional Accuracy**: {scorecard.directional_accuracy_pct:.1f}%")
            lines.append(f"- **Recommendation**: {scorecard.recommendation}\n")
        
        return "".join(lines)
    
    def _evidence_summary_dict(self) -> dict[str, Any]:
        """Build evidence summary."""
        summary = {}
        
        if self.record.research_evidence.technical:
            t = self.record.research_evidence.technical
            summary["technical"] = {
                "quality": t.weekly_structure_quality or t.daily_structure_quality,
                "trend": t.weekly_trend_state or t.daily_trend_state,
                "volatility": t.weekly_volatility_state or t.daily_volatility_state,
                "confidence": t.confidence_level,
            }
        
        if self.record.research_evidence.catalysts:
            c = self.record.research_evidence.catalysts
            summary["catalysts"] = {
                "next_event": c.next_known_event_time.isoformat() if c.next_known_event_time else None,
                "catalyst_risk": c.catalyst_risk,
                "confidence": c.confidence_level,
            }
        
        if self.record.research_evidence.valuation:
            v = self.record.research_evidence.valuation
            summary["valuation"] = {
                "pe_ratio": v.pe_ratio,
                "ev_to_ebitda": v.ev_to_ebitda,
                "free_cf_yield": v.free_cash_flow_yield,
                "confidence": v.confidence_level,
            }
        
        if self.record.research_evidence.expectations_mispricing:
            e = self.record.research_evidence.expectations_mispricing
            summary["expectations"] = {
                "mispricing_magnitude": e.mispricing_magnitude_estimate,
                "consensus_gap": e.consensus_gap_direction,
                "validation_status": e.validation_status,
                "confidence": e.confidence_level,
            }
        
        return summary


def asdict(obj: Any) -> dict[str, Any]:
    """Convert dataclass to dict."""
    from dataclasses import asdict as dc_asdict, is_dataclass
    if is_dataclass(obj):
        return dc_asdict(obj)
    return vars(obj) if hasattr(obj, '__dict__') else {}
