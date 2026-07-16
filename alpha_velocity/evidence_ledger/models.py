"""
Evidence Ledger: Immutable point-in-time records of research, decisions, outcomes, and performance.

Records what Alpha Velocity knew at each observation point, how each evidence lens
contributed to rankings and allocations, and how well those decisions performed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Mapping, Literal
from enum import Enum


class RecordType(str, Enum):
    """Type of evidence ledger record."""
    INITIAL = "INITIAL"
    REVISION = "REVISION"
    SUPPLEMENTAL = "SUPPLEMENTAL"


class ValidationStatus(str, Enum):
    """Validation status of evidence streams."""
    CALIBRATED = "CALIBRATED"  # Independently validated
    UNCALIBRATED = "UNCALIBRATED"  # Not yet validated
    SHADOW = "SHADOW"  # Under validation, zero influence
    QUARANTINE = "QUARANTINE"  # Flagged for review
    RETIRED = "RETIRED"  # No longer used


class EvidenceStreamRecommendation(str, Enum):
    """Scorecard recommendation for evidence stream."""
    REMAIN_SHADOW = "REMAIN_SHADOW"  # Keep under wraps
    ELIGIBLE_FOR_VALIDATION = "ELIGIBLE_FOR_VALIDATION"  # Ready to validate
    QUARANTINE = "QUARANTINE"  # Needs investigation
    RETIRE = "RETIRE"  # Stop using
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"  # Incomplete


class OutcomeGradeHorizon(str, Enum):
    """Time horizon for outcome grading."""
    ONE_DAY = "1D"
    FIVE_DAYS = "5D"
    TEN_DAYS = "10D"
    TWENTY_DAYS = "20D"
    CATALYST_WINDOW = "CATALYST"
    INTENDED_HOLDING = "HOLDING"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class TechnicalEvidence:
    """Technical analysis and price action evidence."""
    observation_time: datetime
    available_at: datetime
    
    # Structure quality
    weekly_structure_quality: float | None = None
    daily_structure_quality: float | None = None
    multi_timeframe_alignment: str | None = None
    
    # Price levels
    weekly_support_levels: tuple[dict[str, Any], ...] = ()
    weekly_resistance_levels: tuple[dict[str, Any], ...] = ()
    daily_support_levels: tuple[dict[str, Any], ...] = ()
    daily_resistance_levels: tuple[dict[str, Any], ...] = ()
    primary_invalidation_price: float | None = None
    invalidation_reasons: tuple[str, ...] = ()
    
    # Trend and ranges
    weekly_trend_state: str = ""
    daily_trend_state: str = ""
    weekly_range_position: float | None = None
    daily_range_position: float | None = None
    
    # Volatility
    weekly_volatility_state: str = ""
    daily_volatility_state: str = ""
    volatility_contraction: float | None = None
    volatility_expansion: float | None = None
    atr_pct: float | None = None
    
    # Setup quality
    setup_type: str = ""
    close_quality: float | None = None
    relative_volume: float | None = None
    failed_breakout: bool = False
    failed_breakdown: bool = False
    
    model_version: str = ""
    confidence_level: str = "MODERATE"

    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        if self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")
        if self.available_at > self.observation_time:
            raise ValueError(f"available_at {self.available_at} > observation_time {self.observation_time}")


@dataclass(frozen=True)
class CatalystEvidence:
    """Event-driven catalyst evidence."""
    observation_time: datetime
    available_at: datetime
    
    known_catalysts: tuple[dict[str, Any], ...] = ()
    next_known_event_time: datetime | None = None
    catalyst_risk: str = "unknown"
    
    # Materiality assessment
    catalyst_magnitude_estimate: str = ""  # "LOW", "MEDIUM", "HIGH"
    catalyst_probability_estimate: float | None = None
    expected_market_impact_pct: float | None = None
    
    model_version: str = ""
    confidence_level: str = "MODERATE"

    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        if self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")
        if self.available_at > self.observation_time:
            raise ValueError(f"available_at {self.available_at} > observation_time {self.observation_time}")


@dataclass(frozen=True)
class ValuationEvidence:
    """Valuation and capital structure evidence."""
    observation_time: datetime
    available_at: datetime
    
    # Capital structure
    debt_to_equity: float | None = None
    net_debt_to_ebitda: float | None = None
    interest_coverage: float | None = None
    maturity_schedule: dict[str, Any] = field(default_factory=dict)
    refinancing_risk: str = ""
    
    # Valuation metrics
    pe_ratio: float | None = None
    peg_ratio: float | None = None
    pb_ratio: float | None = None
    ev_to_revenue: float | None = None
    ev_to_ebitda: float | None = None
    dividend_yield: float | None = None
    free_cash_flow_yield: float | None = None
    
    # Relative valuation
    vs_industry_median: dict[str, float] = field(default_factory=dict)
    vs_peer_group_avg: dict[str, float] = field(default_factory=dict)
    
    model_version: str = ""
    confidence_level: str = "MODERATE"

    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        if self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")
        if self.available_at > self.observation_time:
            raise ValueError(f"available_at {self.available_at} > observation_time {self.observation_time}")


@dataclass(frozen=True)
class ExpectationsAndMispricingEvidence:
    """Shadow: Expectations & Mispricing Research (unvalidated)."""
    observation_time: datetime
    available_at: datetime
    
    # Research scores
    upside_case_score: float | None = None
    downside_case_score: float | None = None
    catalyst_realization_score: float | None = None
    
    # Consensus gap analysis
    consensus_gap_direction: str = ""  # "WIDE_UPSIDE", "MODERATE_UPSIDE", "NARROW", etc.
    estimated_gap_pct: float | None = None
    market_seems_to_be_missing: tuple[str, ...] = ()
    
    # Forecast model (point-in-time)
    revenue_forecast_fy1: float | None = None
    ebitda_forecast_fy1: float | None = None
    eps_forecast_fy1: float | None = None
    fcf_forecast_fy1: float | None = None
    
    # Industry and scenario
    industry_outlook: str = ""
    base_case_scenario: str = ""
    key_assumptions: dict[str, Any] = field(default_factory=dict)
    scenario_probabilities: dict[str, float] = field(default_factory=dict)
    
    # Evidence of mispricing
    mispricing_evidence: tuple[str, ...] = ()
    mispricing_magnitude_estimate: float | None = None  # pct
    mispricing_persistence_estimate: str = ""  # "TRANSIENT", "MEDIUM", "PERSISTENT"
    
    model_version: str = ""
    validation_status: str = "UNCALIBRATED"  # Always UNCALIBRATED until proven
    confidence_level: str = "MODERATE"
    
    source_record_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        if self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")
        if self.available_at > self.observation_time:
            raise ValueError(f"available_at {self.available_at} > observation_time {self.observation_time}")


@dataclass(frozen=True)
class IndustryAndMacroEvidence:
    """Industry outlook and macro evidence."""
    observation_time: datetime
    available_at: datetime
    
    sector: str = ""
    industry: str = ""
    industry_trend: str = ""  # "EXPANDING", "STABLE", "CONTRACTING"
    sector_momentum: float | None = None
    relative_strength: float | None = None
    
    macro_regime: str = ""
    rate_environment: str = ""
    policy_environment: tuple[str, ...] = ()
    competitive_dynamics: str = ""
    
    market_regime: str = ""
    sector_regime: str = ""
    
    model_version: str = ""
    confidence_level: str = "MODERATE"

    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        if self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")
        if self.available_at > self.observation_time:
            raise ValueError(f"available_at {self.available_at} > observation_time {self.observation_time}")


@dataclass(frozen=True)
class SentimentAndOtherEvidence:
    """Optional sentiment, alternative data, or other evidence."""
    observation_time: datetime
    available_at: datetime
    
    source_name: str = ""
    evidence_type: str = ""  # "SENTIMENT", "ALTERNATIVE_DATA", "CROWDSOURCED", etc.
    
    score: float | None = None
    direction: str = ""  # "BULLISH", "NEUTRAL", "BEARISH"
    confidence_level: str = "LOW"
    
    supporting_observations: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    
    model_version: str = ""
    validation_status: str = "UNCALIBRATED"

    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        if self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")
        if self.available_at > self.observation_time:
            raise ValueError(f"available_at {self.available_at} > observation_time {self.observation_time}")


@dataclass(frozen=True)
class ResearchEvidence:
    """Complete research evidence for a record."""
    
    technical: TechnicalEvidence | None = None
    catalysts: CatalystEvidence | None = None
    valuation: ValuationEvidence | None = None
    expectations_mispricing: ExpectationsAndMispricingEvidence | None = None
    industry_macro: IndustryAndMacroEvidence | None = None
    sentiment_other: tuple[SentimentAndOtherEvidence, ...] = ()
    
    # Feature snapshot (state of features at observation time)
    feature_snapshot_ids: tuple[str, ...] = ()
    

@dataclass(frozen=True)
class InfluenceWeights:
    """Controls for evidence influence (especially shadow research)."""
    
    technical_ranking_influence: float = 1.0
    technical_allocation_influence: float = 1.0
    
    catalyst_ranking_influence: float = 1.0
    catalyst_allocation_influence: float = 1.0
    
    valuation_ranking_influence: float = 1.0
    valuation_allocation_influence: float = 1.0
    
    expectations_ranking_influence: float = 0.0  # SHADOW by default
    expectations_allocation_influence: float = 0.0  # SHADOW by default
    
    industry_ranking_influence: float = 1.0
    industry_allocation_influence: float = 1.0
    
    sentiment_ranking_influence: float = 0.5  # Reduced
    sentiment_allocation_influence: float = 0.0  # Shadow
    
    # Validation status
    technical_validation_status: str = "CALIBRATED"
    catalyst_validation_status: str = "CALIBRATED"
    valuation_validation_status: str = "CALIBRATED"
    expectations_validation_status: str = "SHADOW"
    industry_validation_status: str = "CALIBRATED"
    sentiment_validation_status: str = "UNCALIBRATED"


@dataclass(frozen=True)
class RankingDecisionState:
    """Ranking engine decision state at observation time."""
    
    opportunity_id: str
    ranking_run_id: str
    rank: int
    percentile: float
    overall_research_score: float
    ranking_state: str
    
    # Component scores
    intrinsic_score: float
    timing_score: float
    swing_value_score: float
    technical_score: float
    catalyst_score: float
    capital_structure_score: float
    liquidity_score: float
    
    # Adjustments
    risk_adjustment: float
    uncertainty_adjustment: float
    
    # Evidence breakdown
    positive_contributors: tuple[str, ...] = ()
    negative_contributors: tuple[str, ...] = ()
    disqualifiers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    required_confirmation: tuple[str, ...] = ()
    
    validation_status: str = "CALIBRATED"


@dataclass(frozen=True)
class AllocationDecisionState:
    """Capital allocation decision state at observation time."""
    
    proposal_id: str | None = None  # None if not proposed
    proposed_allocation_weight: float | None = None
    proposed_quantity: float | None = None
    proposed_price_target: float | None = None
    
    proposed_rotation: bool = False
    rotation_target_symbol: str | None = None
    rotation_justification: str = ""
    
    rejected_alternatives: tuple[str, ...] = ()
    
    # Constraint binding
    binding_constraints: tuple[str, ...] = ()
    constraint_violations: tuple[str, ...] = ()


@dataclass(frozen=True)
class RiskGovernanceReviewState:
    """Risk and governance review state."""
    
    risk_review_required: bool = True
    risk_review_status: str = "PENDING"  # "PENDING", "APPROVED", "REJECTED", "CONDITIONAL"
    risk_review_restrictions: tuple[str, ...] = ()
    
    governance_review_required: bool = True
    governance_review_status: str = "PENDING"  # "PENDING", "APPROVED", "REJECTED", "CONDITIONAL"
    governance_review_restrictions: tuple[str, ...] = ()
    
    execution_authorized: bool = False  # Always False from optimizer


@dataclass(frozen=True)
class DecisionStateEvidence:
    """Complete decision state at observation time."""
    
    opportunity_classification: str = ""
    ranking: RankingDecisionState | None = None
    allocation: AllocationDecisionState | None = None
    risk_governance: RiskGovernanceReviewState = field(default_factory=RiskGovernanceReviewState)


@dataclass(frozen=True)
class OutcomeGrade:
    """Grade of opportunity performance after observation."""
    
    horizon: OutcomeGradeHorizon
    as_of_time: datetime
    days_elapsed: int
    
    # Price returns
    forward_return_pct: float | None = None
    max_favorable_excursion_pct: float | None = None
    max_adverse_excursion_pct: float | None = None
    
    # Directional and magnitude
    direction_correct: bool | None = None
    magnitude_error_pct: float | None = None
    timing_error_days: int | None = None
    
    # Technical
    invalidation_breach: bool = False
    
    # Catalyst
    catalyst_occurred: bool = False
    catalyst_size: str = ""  # "LOW", "MEDIUM", "HIGH"
    
    # Liquidity
    liquidity_achieved: float | None = None
    capacity_constraint_hit: bool = False
    
    # Ranking performance
    ranking_percentile_performance: float | None = None  # (current_price / predicted_target - 1) * 100
    
    # Allocation performance
    opportunity_cost_performance: float | None = None  # vs best alternative
    rotation_improved_results: bool | None = None  # did rotation pay off?
    
    # Grading notes
    notes: str = ""

    def __post_init__(self) -> None:
        if self.as_of_time.tzinfo is None:
            raise ValueError("as_of_time must be timezone-aware")


@dataclass(frozen=True)
class ForecastGrade:
    """Grade of Expectations & Mispricing forecasts."""
    
    security_id: str
    symbol: str
    forecast_date: datetime
    grading_date: datetime
    
    # Realized metrics (actual)
    realized_revenue: float | None = None
    realized_ebitda: float | None = None
    realized_margin: float | None = None
    realized_fcf: float | None = None
    realized_eps: float | None = None
    
    # Forecast metrics (predicted)
    forecast_revenue: float | None = None
    forecast_ebitda: float | None = None
    forecast_margin: float | None = None
    forecast_fcf: float | None = None
    forecast_eps: float | None = None
    
    # Error metrics
    revenue_error_pct: float | None = None
    ebitda_error_pct: float | None = None
    margin_error_bps: float | None = None
    fcf_error_pct: float | None = None
    eps_error_pct: float | None = None
    
    # Consensus gap realization
    consensus_gap_direction_correct: bool | None = None
    consensus_gap_magnitude_error_pct: float | None = None
    
    # Scenario calibration
    actual_scenario_match: str = ""  # Which scenario actually occurred
    scenario_probability_accuracy: float | None = None
    
    # Earnings bridge
    normalized_earnings_bridge_accuracy: float | None = None
    
    # Industry assumptions
    industry_assumption_accuracy: float | None = None
    
    # Notes
    notes: str = ""


@dataclass(frozen=True)
class EvidenceStreamScorecard:
    """Aggregated performance scorecard for an evidence stream."""
    
    stream_name: str  # "TECHNICAL", "CATALYST", "VALUATION", "EXPECTATIONS", etc.
    
    # Coverage
    sample_count: int = 0
    graded_count: int = 0
    availability_coverage_pct: float = 0.0
    
    # Performance
    directional_accuracy_pct: float | None = None
    calibration_score: float | None = None
    average_forward_return_by_score_bucket: dict[str, float] = field(default_factory=dict)
    
    # Value
    incremental_value_vs_baseline_pct: float | None = None
    
    # Quality
    failure_modes: tuple[str, ...] = ()
    regime_sensitivity: str = ""  # "LOW", "MEDIUM", "HIGH"
    
    # Recommendation
    recommendation: str = "REMAIN_SHADOW"  # EvidenceStreamRecommendation value
    confidence_in_recommendation: float = 0.5
    reasoning: str = ""
    
    validation_status: str = "UNCALIBRATED"


@dataclass(frozen=True)
class SupVersionRecord:
    """Tracks supersession and revisions."""
    
    record_id: str
    supersedes_record_id: str | None = None
    superseded_by_record_id: str | None = None
    record_type: str = "INITIAL"  # RecordType value
    revision_reason: str = ""
    revised_at: datetime | None = None


@dataclass(frozen=True)
class EvidenceLedgerRecord:
    """Immutable point-in-time evidence ledger record."""
    
    # Identity
    record_id: str
    observation_time: datetime
    created_at: datetime
    
    # Security and opportunity
    security_id: str
    symbol: str
    universe_snapshot_id: str
    
    # Runs and proposals
    market_scan_run_id: str | None = None
    opportunity_id: str | None = None
    ranking_run_id: str | None = None
    capital_proposal_id: str | None = None
    portfolio_snapshot_id: str | None = None
    
    # Hashes for reproducibility
    warehouse_manifest_hash: str = ""
    dataset_manifest_hash: str = ""
    git_commit: str = ""
    
    # Versioning
    schema_version: str = "1.0.0"
    
    # Research evidence
    research_evidence: ResearchEvidence = field(default_factory=ResearchEvidence)
    
    # Decision state
    decision_state: DecisionStateEvidence = field(default_factory=DecisionStateEvidence)
    
    # Influence controls
    influence_weights: InfluenceWeights = field(default_factory=InfluenceWeights)
    
    # Outcomes (populated later)
    outcome_grades: tuple[OutcomeGrade, ...] = ()
    forecast_grades: tuple[ForecastGrade, ...] = ()
    
    # Scorecards (aggregated later)
    evidence_scorecards: tuple[EvidenceStreamScorecard, ...] = ()
    
    # Supersession
    supersession: SupVersionRecord | None = None
    
    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.created_at < self.observation_time:
            raise ValueError(f"created_at {self.created_at} < observation_time {self.observation_time}")
        
        # Validate point-in-time integrity for all evidence
        for evidence_item in self._get_all_evidence_items():
            if evidence_item.available_at > self.observation_time:
                raise ValueError(
                    f"Evidence available_at {evidence_item.available_at} > "
                    f"observation_time {self.observation_time}"
                )

    def _get_all_evidence_items(self) -> list[Any]:
        """Get all evidence items for validation."""
        items = []
        if isinstance(self.research_evidence, ResearchEvidence):
            if self.research_evidence.technical:
                items.append(self.research_evidence.technical)
            if self.research_evidence.catalysts:
                items.append(self.research_evidence.catalysts)
            if self.research_evidence.valuation:
                items.append(self.research_evidence.valuation)
            if self.research_evidence.expectations_mispricing:
                items.append(self.research_evidence.expectations_mispricing)
            if self.research_evidence.industry_macro:
                items.append(self.research_evidence.industry_macro)
            items.extend(self.research_evidence.sentiment_other)
        return items

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON with deterministic ordering."""
        data = self.to_dict()
        # Custom serialization for datetime objects
        def json_encoder(obj: Any) -> str:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        return json.dumps(data, default=json_encoder, sort_keys=True, indent=2)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvidenceLedgerRecord:
        """Create from dictionary with datetime parsing."""
        data_copy = dict(data)
        
        # Parse datetime fields
        for field_name in ["observation_time", "created_at"]:
            if isinstance(data_copy.get(field_name), str):
                data_copy[field_name] = datetime.fromisoformat(data_copy[field_name])
        
        # Parse nested structures
        # TODO: Implement proper nested deserialization
        
        return cls(**data_copy)
