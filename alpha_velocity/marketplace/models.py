"""Opportunity Marketplace models and classifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class MarketplaceQueue(str, Enum):
    """Candidate marketplace queues and research stages."""

    # Actionable (trade-ready)
    ACTIONABLE_TRIGGERED = "ACTIONABLE_TRIGGERED"
    STARTER_POSITION_CANDIDATE = "STARTER_POSITION_CANDIDATE"

    # Near-trigger (monitoring)
    NEAR_TRIGGER = "NEAR_TRIGGER"

    # Active research
    ASYMMETRIC_VALUE_RESEARCH = "ASYMMETRIC_VALUE_RESEARCH"
    CHART_MOMENTUM_RESEARCH = "CHART_MOMENTUM_RESEARCH"
    TOP_DOWN_INDUSTRY_RESEARCH = "TOP_DOWN_INDUSTRY_RESEARCH"
    EVENT_ACTIVIST_RESEARCH = "EVENT_ACTIVIST_RESEARCH"
    SPECIAL_SITUATION = "SPECIAL_SITUATION"

    # Human-directed research
    HUMAN_HYPOTHESIS = "HUMAN_HYPOTHESIS"

    # Research qualified, not yet execution eligible
    RESEARCH_ONLY = "RESEARCH_ONLY"

    # Holding review
    CURRENT_HOLDING_REVIEW = "CURRENT_HOLDING_REVIEW"

    # Exclusions
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    HIGH_RISK_SPECULATIVE = "HIGH_RISK_SPECULATIVE"
    EXCLUDED = "EXCLUDED"


class DiscoveryLensType(str, Enum):
    """Independent research lenses discovering opportunities."""

    ASYMMETRIC_EQUITY = "ASYMMETRIC_EQUITY"
    SURVIVABILITY_AND_CAPITAL_STACK = "SURVIVABILITY_AND_CAPITAL_STACK"
    CHART_AND_RECOGNITION = "CHART_AND_RECOGNITION"
    CORPORATE_EVENT_AND_ACTIVIST = "CORPORATE_EVENT_AND_ACTIVIST"
    EXPECTATIONS_AND_REVISIONS = "EXPECTATIONS_AND_REVISIONS"
    MANAGEMENT_LANGUAGE_CHANGE = "MANAGEMENT_LANGUAGE_CHANGE"
    TOP_DOWN_MARKET_AND_INDUSTRY = "TOP_DOWN_MARKET_AND_INDUSTRY"
    TURTLE_TREND_RESEARCH_LENS = "TURTLE_TREND_RESEARCH_LENS"


class LiquidityTier(str, Enum):
    """Micro-cap liquidity classification."""

    INSTITUTIONALLY_LIQUID = "INSTITUTIONALLY_LIQUID"
    TRADEABLE_SMALL_CAP = "TRADEABLE_SMALL_CAP"
    LIMITED_CAPACITY = "LIMITED_CAPACITY"
    STARTER_ONLY = "STARTER_ONLY"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    UNTRADEABLE = "UNTRADEABLE"


class MarketLeaderLabel(str, Enum):
    """Evaluation labels for forward-return grading (not available during ranking)."""

    TOP_1PCT_5DAY = "TOP_1PCT_5DAY"
    TOP_5PCT_20DAY = "TOP_5PCT_20DAY"
    TOP_DECILE_60DAY = "TOP_DECILE_60DAY"
    GAIN_20PCT_BEFORE_10PCT_DD = "GAIN_20PCT_BEFORE_10PCT_DD"
    GAIN_50PCT_WITHIN_6M = "GAIN_50PCT_WITHIN_6M"
    DOUBLE = "DOUBLE"
    TRIPLE = "TRIPLE"
    FIVE_BAGGER = "FIVE_BAGGER"
    MFE_ONLY = "MFE_ONLY"
    MAE_ONLY = "MAE_ONLY"
    FLAT = "FLAT"


@dataclass(frozen=True)
class DiscoveryLens:
    """Record of which lens(es) discovered this opportunity."""

    lens_type: DiscoveryLensType
    discovery_score: float  # 0-100 confidence this lens surfaced a real opportunity
    evidence_summary: str
    source_documents: tuple[str, ...] = ()
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "lens_type": self.lens_type.value,
            "discovery_score": self.discovery_score,
            "evidence_summary": self.evidence_summary,
            "source_documents": self.source_documents,
            "discovered_at": self.discovered_at.isoformat(),
        }


@dataclass(frozen=True)
class HorizonAssessment:
    """Structured assessment for one investment horizon."""

    horizon_name: str
    status: str
    attractiveness: float
    confidence: float
    expected_realization_window: str
    supporting_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()
    required_confirmation: tuple[str, ...] = ()
    invalidation: str = ""
    calibration_status: str = "UNCALIBRATED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "horizon_name": self.horizon_name,
            "status": self.status,
            "attractiveness": self.attractiveness,
            "confidence": self.confidence,
            "expected_realization_window": self.expected_realization_window,
            "supporting_evidence": self.supporting_evidence,
            "contradictory_evidence": self.contradictory_evidence,
            "required_confirmation": self.required_confirmation,
            "invalidation": self.invalidation,
            "calibration_status": self.calibration_status,
        }


@dataclass(frozen=True)
class StructuredThesis:
    """Thesis structure separating facts, assumptions, forecasts and opinions."""

    thesis_id: str
    observation_time: datetime
    why_surfaced: str  # Why the security surfaced
    primary_repricing_mechanism: str  # Primary catalyst for repricing
    business_or_asset_value_thesis: str  # What's the actual value opportunity
    survivability_conclusion: str  # Can equity remain intact until catalyst?
    market_misunderstanding: str  # What is the market missing?
    catalyst_description: str  # What triggers the repricing?
    recognition_state: str  # Current recognition level
    bear_outcome: str  # Bear case outcome
    base_outcome: str  # Base case outcome
    bull_outcome: str  # Bull case outcome
    primary_horizon_days: int  # Expected holding days
    tactical_horizon_days: int  # Near-term target
    required_confirmation: str  # What confirms the thesis?
    invalidation_condition: str  # What breaks the thesis?
    strongest_bull_argument: str
    strongest_bear_argument: str
    highest_sensitivity_assumption: str
    confidence_score: float = 0.5  # 0-1 research confidence
    source_lineage: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "thesis_id": self.thesis_id,
            "observation_time": self.observation_time.isoformat(),
            "why_surfaced": self.why_surfaced,
            "primary_repricing_mechanism": self.primary_repricing_mechanism,
            "business_or_asset_value_thesis": self.business_or_asset_value_thesis,
            "survivability_conclusion": self.survivability_conclusion,
            "market_misunderstanding": self.market_misunderstanding,
            "catalyst_description": self.catalyst_description,
            "recognition_state": self.recognition_state,
            "bear_outcome": self.bear_outcome,
            "base_outcome": self.base_outcome,
            "bull_outcome": self.bull_outcome,
            "primary_horizon_days": self.primary_horizon_days,
            "tactical_horizon_days": self.tactical_horizon_days,
            "required_confirmation": self.required_confirmation,
            "invalidation_condition": self.invalidation_condition,
            "strongest_bull_argument": self.strongest_bull_argument,
            "strongest_bear_argument": self.strongest_bear_argument,
            "highest_sensitivity_assumption": self.highest_sensitivity_assumption,
            "confidence_score": self.confidence_score,
            "source_lineage": self.source_lineage,
        }


@dataclass(frozen=True)
class HumanHypothesis:
    """Human-authored research hypothesis."""

    hypothesis_id: str
    symbol: str
    security_id: str
    author: str
    created_at: datetime
    observation_time: datetime
    thesis_text: str
    rationale: str
    required_confirmation: str
    invalidation_trigger: str
    author_confidence: float = 0.5  # 0-1
    allocation_influence_allowed: bool = False  # Always zero influence initially
    source_yaml_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "symbol": self.symbol,
            "security_id": self.security_id,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "observation_time": self.observation_time.isoformat(),
            "thesis_text": self.thesis_text,
            "rationale": self.rationale,
            "required_confirmation": self.required_confirmation,
            "invalidation_trigger": self.invalidation_trigger,
            "author_confidence": self.author_confidence,
            "allocation_influence_allowed": self.allocation_influence_allowed,
            "source_yaml_path": self.source_yaml_path,
        }


@dataclass(frozen=True)
class OpportunityCandidateClassification:
    """Classification of opportunity into marketplace queues."""

    opportunity_id: str
    security_id: str
    symbol: str
    observation_time: datetime
    marketplace_queues: tuple[MarketplaceQueue, ...] = ()
    discovery_lenses: tuple[DiscoveryLens, ...] = ()
    structured_thesis: StructuredThesis | None = None
    human_hypothesis: HumanHypothesis | None = None
    liquidity_tier: LiquidityTier = LiquidityTier.RESEARCH_ONLY
    research_confidence: float = 0.0  # Separate from opportunity attractiveness
    opportunity_attractiveness: float = 0.0  # Ranking score
    is_actionable: bool = False
    requires_confirmation: tuple[str, ...] = ()
    is_excluded: bool = False
    exclusion_reason: str = ""
    microcap_warnings: tuple[str, ...] = ()
    top_five_eligible: bool = False
    top_five_rank: int | None = None
    fallback_research_mode: bool = False
    execution_eligible: bool = False
    research_qualified: bool = False
    pattern_family: str = ""
    pattern_provenance: dict[str, float] = field(default_factory=dict)
    research_horizon: HorizonAssessment | None = None
    primary_repricing_horizon: HorizonAssessment | None = None
    tactical_swing_horizon: HorizonAssessment | None = None
    execution_horizon: HorizonAssessment | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "security_id": self.security_id,
            "symbol": self.symbol,
            "observation_time": self.observation_time.isoformat(),
            "marketplace_queues": [q.value for q in self.marketplace_queues],
            "discovery_lenses": [lens.to_dict() for lens in self.discovery_lenses],
            "structured_thesis": self.structured_thesis.to_dict() if self.structured_thesis else None,
            "human_hypothesis": self.human_hypothesis.to_dict() if self.human_hypothesis else None,
            "liquidity_tier": self.liquidity_tier.value,
            "research_confidence": self.research_confidence,
            "opportunity_attractiveness": self.opportunity_attractiveness,
            "is_actionable": self.is_actionable,
            "requires_confirmation": self.requires_confirmation,
            "is_excluded": self.is_excluded,
            "exclusion_reason": self.exclusion_reason,
            "microcap_warnings": self.microcap_warnings,
            "top_five_eligible": self.top_five_eligible,
            "top_five_rank": self.top_five_rank,
            "fallback_research_mode": self.fallback_research_mode,
            "execution_eligible": self.execution_eligible,
            "research_qualified": self.research_qualified,
            "pattern_family": self.pattern_family,
            "pattern_provenance": self.pattern_provenance,
            "research_horizon": self.research_horizon.to_dict() if self.research_horizon else None,
            "primary_repricing_horizon": self.primary_repricing_horizon.to_dict() if self.primary_repricing_horizon else None,
            "tactical_swing_horizon": self.tactical_swing_horizon.to_dict() if self.tactical_swing_horizon else None,
            "execution_horizon": self.execution_horizon.to_dict() if self.execution_horizon else None,
        }


@dataclass(frozen=True)
class MarketplaceResult:
    """Complete marketplace discovery and classification result."""

    run_id: str
    observation_time: datetime
    total_opportunities: int
    actionable_count: int
    starter_count: int
    near_trigger_count: int
    research_count: int
    excluded_count: int
    discovered_count: int = 0
    queue_counts: dict[str, int] = field(default_factory=dict)
    candidate_classifications: tuple[OpportunityCandidateClassification, ...] = ()
    committee_review_list: tuple[OpportunityCandidateClassification, ...] = ()
    top_five: tuple[OpportunityCandidateClassification, ...] = ()
    warnings: tuple[str, ...] = ()
    fallback_research_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "observation_time": self.observation_time.isoformat(),
            "total_opportunities": self.total_opportunities,
            "actionable_count": self.actionable_count,
            "starter_count": self.starter_count,
            "near_trigger_count": self.near_trigger_count,
            "research_count": self.research_count,
            "excluded_count": self.excluded_count,
            "discovered_count": self.discovered_count,
            "queue_counts": self.queue_counts,
            "committee_review_list_count": len(self.committee_review_list),
            "top_five_count": len(self.top_five),
            "fallback_research_mode": self.fallback_research_mode,
            "warnings": self.warnings,
        }
