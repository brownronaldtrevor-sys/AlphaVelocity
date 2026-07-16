"""
Expectations and mispricing research: reported facts, market expectations, and research scenarios.

Provides immutable data structures for:
- Reported financial facts (earnings, cash flow, balance sheet)
- Market and consensus expectations (analyst estimates, guidance)
- Alpha Velocity research scenarios (bear/base/bull forecasts)
- Normalized earnings bridges (adjustments from reported to normalized)
- Expectation gap analysis (comparing different expectation layers)
- Industry outlook and assumptions
- Forward company models
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, date
from enum import Enum
from typing import Any, Literal, Mapping


class ReportingPeriod(str, Enum):
    """Fiscal period classification."""
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    FY = "FY"


class ExpectationSource(str, Enum):
    """Source of expectation."""
    REPORTED = "REPORTED"
    MANAGEMENT_GUIDANCE = "MANAGEMENT_GUIDANCE"
    CONSENSUS = "CONSENSUS"
    RESEARCH_MODEL = "RESEARCH_MODEL"
    MARKET_IMPLIED = "MARKET_IMPLIED"
    INDUSTRY_SURVEY = "INDUSTRY_SURVEY"


class ConfidenceLevel(str, Enum):
    """Confidence classification for assumptions."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class AdjustmentCategory(str, Enum):
    """Classification of normalized earnings adjustments."""
    NONRECURRING_ITEM = "NONRECURRING_ITEM"
    ACQUISITION_INTEGRATION = "ACQUISITION_INTEGRATION"
    RESTRUCTURING = "RESTRUCTURING"
    STOCK_BASED_COMP = "STOCK_BASED_COMP"
    IMPAIRMENT = "IMPAIRMENT"
    PENSION = "PENSION"
    OTHER = "OTHER"


@dataclass(frozen=True)
class ReportedFacts:
    """Audited or company-reported financial facts."""
    security_id: str
    symbol: str
    observation_time: datetime
    available_at: datetime
    fiscal_year: int
    fiscal_period: ReportingPeriod
    filing_date: datetime
    period_end_date: datetime
    
    # Income statement
    revenue: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    gross_margin_pct: float | None = None
    operating_expenses: float | None = None
    ebitda: float | None = None
    ebitda_margin_pct: float | None = None
    ebit: float | None = None
    ebit_margin_pct: float | None = None
    interest_expense: float | None = None
    tax_expense: float | None = None
    tax_rate_pct: float | None = None
    net_income: float | None = None
    net_margin_pct: float | None = None
    eps: float | None = None
    
    # Management-adjusted figures (when disclosed)
    adjusted_ebitda: float | None = None
    adjusted_ebit: float | None = None
    adjusted_net_income: float | None = None
    adjusted_eps: float | None = None
    
    # Cash flow
    operating_cash_flow: float | None = None
    capital_expenditures: float | None = None
    free_cash_flow: float | None = None
    
    # Balance sheet
    total_assets: float | None = None
    cash_and_equivalents: float | None = None
    total_debt: float | None = None
    shareholders_equity: float | None = None
    shares_outstanding: float | None = None
    book_value_per_share: float | None = None
    
    # Metadata
    source: str = "SEC_FILING"
    adjustment_notes: str = ""
    revision_number: int = 0
    
    def __post_init__(self) -> None:
        if self.available_at > self.observation_time:
            raise ValueError("reported_facts available_at cannot exceed observation_time")
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")


@dataclass(frozen=True)
class MarketExpectation:
    """Single market or consensus expectation."""
    security_id: str
    symbol: str
    observation_time: datetime
    available_at: datetime
    source: ExpectationSource
    as_of: datetime  # When estimate was made
    horizon_year: int
    horizon_quarter: ReportingPeriod | None = None
    
    # Estimates
    revenue: float | None = None
    ebitda: float | None = None
    ebitda_margin_pct: float | None = None
    ebit: float | None = None
    ebit_margin_pct: float | None = None
    net_income: float | None = None
    net_margin_pct: float | None = None
    eps: float | None = None
    free_cash_flow: float | None = None
    
    # Metadata
    estimate_count: int | None = None  # For consensus: number of analysts
    dispersion_std_dev: float | None = None  # For consensus: std deviation
    revision_trend: str = ""  # "up", "down", "stable"
    
    def __post_init__(self) -> None:
        if self.available_at > self.observation_time:
            raise ValueError("market_expectation available_at cannot exceed observation_time")
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")


@dataclass(frozen=True)
class AdjustmentDetail:
    """Single line item in normalized earnings bridge."""
    category: AdjustmentCategory
    amount: float
    rationale: str
    source: str
    available_at: datetime
    recurring: bool
    confidence: ConfidenceLevel
    validation_status: str = "UNVALIDATED"
    supporting_detail: str = ""


@dataclass(frozen=True)
class NormalizedEarningsBridge:
    """Documented bridge from reported to normalized results."""
    security_id: str
    observation_time: datetime
    available_at: datetime
    fiscal_year: int
    fiscal_period: ReportingPeriod
    
    reported_revenue: float
    reported_ebitda: float
    reported_ebit: float
    reported_net_income: float
    reported_eps: float
    
    adjustments: tuple[AdjustmentDetail, ...] = ()
    
    normalized_revenue: float = 0.0
    normalized_ebitda: float = 0.0
    normalized_ebit: float = 0.0
    normalized_net_income: float = 0.0
    normalized_eps: float = 0.0
    
    # Metadata
    methodology: str = ""
    reviewer: str = ""
    validation_status: str = "UNVALIDATED"
    warnings: tuple[str, ...] = ()
    
    def __post_init__(self) -> None:
        if self.available_at > self.observation_time:
            raise ValueError("normalized_bridge available_at cannot exceed observation_time")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "schema_version": "1.0.0",
            "security_id": self.security_id,
            "observation_time": self.observation_time.isoformat(),
            "available_at": self.available_at.isoformat(),
            "fiscal_year": self.fiscal_year,
            "fiscal_period": self.fiscal_period.value,
            "reported_revenue": self.reported_revenue,
            "reported_ebitda": self.reported_ebitda,
            "reported_ebit": self.reported_ebit,
            "reported_net_income": self.reported_net_income,
            "reported_eps": self.reported_eps,
            "adjustments": [asdict(a) for a in self.adjustments],
            "normalized_revenue": self.normalized_revenue,
            "normalized_ebitda": self.normalized_ebitda,
            "normalized_ebit": self.normalized_ebit,
            "normalized_net_income": self.normalized_net_income,
            "normalized_eps": self.normalized_eps,
            "methodology": self.methodology,
            "reviewer": self.reviewer,
            "validation_status": self.validation_status,
            "warnings": list(self.warnings),
        }
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        from datetime import datetime as dt_class
        
        def default_serializer(obj: Any) -> Any:
            if isinstance(obj, (dt_class, date)):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Not JSON serializable: {type(obj)}")
        
        return json.dumps(self.to_dict(), sort_keys=True, default=default_serializer, indent=2)


@dataclass(frozen=True)
class ForwardAssumption:
    """Single forward-period assumption for company model."""
    name: str
    value: float
    unit: str
    rationale: str
    source: str
    confidence: ConfidenceLevel
    horizon_year: int
    horizon_quarter: ReportingPeriod | None = None


@dataclass(frozen=True)
class ResearchScenario:
    """Bear/base/bull scenario with explicit assumptions."""
    security_id: str
    symbol: str
    observation_time: datetime
    available_at: datetime
    scenario: Literal["bear", "base", "bull"]
    
    # Forecast period
    horizon_start_year: int
    horizon_end_year: int
    
    # Revenue and margins
    revenue_forecast_year_end: float | None = None
    revenue_cagr_pct: float | None = None
    revenue_assumptions: tuple[ForwardAssumption, ...] = ()
    
    gross_margin_pct: float | None = None
    operating_margin_pct: float | None = None
    ebitda_margin_pct: float | None = None
    ebit_margin_pct: float | None = None
    net_margin_pct: float | None = None
    
    # Cash flow
    free_cash_flow_forecast: float | None = None
    fcf_assumptions: tuple[ForwardAssumption, ...] = ()
    
    # Balance sheet and capital
    net_debt_outlook: float | None = None
    debt_maturity_schedule: tuple[dict[str, Any], ...] = ()
    interest_rate_assumption_pct: float | None = None
    tax_rate_assumption_pct: float | None = None
    
    # Share count and dilution
    dilution_assumption_pct: float | None = None
    share_buyback_assumption: float | None = None
    share_count_horizon: float | None = None
    
    # Metadata
    provenance: str = ""  # "human_authored" or "model_generated"
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    key_risks: tuple[str, ...] = ()
    validation_status: str = "UNVALIDATED"
    
    def __post_init__(self) -> None:
        if self.available_at > self.observation_time:
            raise ValueError("research_scenario available_at cannot exceed observation_time")


@dataclass(frozen=True)
class IndustryOutlook:
    """Industry observation and assumption."""
    industry_id: str
    industry_name: str
    observation_time: datetime
    available_at: datetime
    demand_outlook: str  # "strong_growth", "modest_growth", "stable", "contraction"
    pricing_power: str  # "strong", "moderate", "weak"
    input_cost_outlook: str  # "declining", "stable", "rising"
    supply_chain_risk: str  # "low", "moderate", "high"
    rate_sensitivity: str  # "high", "moderate", "low"
    credit_conditions_outlook: str  # "tight", "normal", "loose"
    cycle_stage: str  # "recovery", "peak", "contraction", "trough"
    
    # Optional numeric values
    demand_growth_rate_pct: float | None = None
    capacity_utilization_pct: float | None = None
    expected_price_change_pct: float | None = None
    
    # Optional strings with defaults
    capacity_additions_outlook: str = ""
    source: str = ""
    expected_inflection_timing: str = ""
    
    # Optional collections
    leading_indicators: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    
    # Metadata
    horizon_year: int = 1
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    
    def __post_init__(self) -> None:
        if self.available_at > self.observation_time:
            raise ValueError("industry_outlook available_at cannot exceed observation_time")


@dataclass(frozen=True)
class ExpectationGap:
    """Gap between two expectation layers."""
    gap_type: str  # "consensus_vs_reported", "guidance_vs_consensus", etc.
    metric: str  # "revenue", "ebitda", "eps", etc.
    layer_1_value: float | None = None
    layer_1_source: str = ""
    layer_2_value: float | None = None
    layer_2_source: str = ""
    
    gap_amount: float | None = None
    gap_pct: float | None = None
    gap_direction: str = ""  # "bullish", "bearish", "neutral"
    
    horizon: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE
    catalyst_required: str = ""
    evidence_quality: str = "LOW"
    missing_information: tuple[str, ...] = ()
    
    def __post_init__(self) -> None:
        if self.layer_1_value is not None and self.layer_2_value is not None:
            gap = self.layer_2_value - self.layer_1_value
            gap_pct = (gap / self.layer_1_value * 100.0) if self.layer_1_value != 0 else None
            object.__setattr__(self, "gap_amount", gap)
            object.__setattr__(self, "gap_pct", gap_pct)


@dataclass(frozen=True)
class ExpectationsResearchResult:
    """Complete expectations and mispricing research output."""
    security_id: str
    symbol: str
    observation_time: datetime
    forecast_horizon_end_year: int
    
    # References
    reported_facts_reference: ReportedFacts | None = None
    consensus_reference: MarketExpectation | None = None
    management_guidance_reference: MarketExpectation | None = None
    industry_outlook_reference: IndustryOutlook | None = None
    
    # Research
    normalized_bridges: tuple[NormalizedEarningsBridge, ...] = ()
    research_scenarios: tuple[ResearchScenario, ...] = ()
    expectation_gaps: tuple[ExpectationGap, ...] = ()
    
    # Capital stack
    capital_stack_commentary: str = ""
    capital_constraints: tuple[str, ...] = ()
    refinancing_dependencies: tuple[str, ...] = ()
    dilution_concerns: tuple[str, ...] = ()
    
    # Catalysts and invalidation
    catalysts: tuple[str, ...] = ()
    thesis_invalidation_conditions: tuple[str, ...] = ()
    
    # Metadata
    confidence_status: ConfidenceLevel = ConfidenceLevel.LOW
    validation_status: str = "UNVALIDATED"
    warnings: tuple[str, ...] = ()
    lineage: dict[str, Any] = field(default_factory=dict)
    
    # Influence controls (always default to zero)
    ranking_influence: float = 0.0
    allocation_influence: float = 0.0
    
    schema_version: str = "1.0.0"
    
    def __post_init__(self) -> None:
        if self.observation_time.tzinfo is None:
            raise ValueError("observation_time must be timezone-aware")
        # Influence stays at zero until separately validated
        if self.ranking_influence != 0.0:
            raise ValueError("ranking_influence must be 0 until separately validated")
        if self.allocation_influence != 0.0:
            raise ValueError("allocation_influence must be 0 until separately validated")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with sorted keys."""
        return {
            "schema_version": self.schema_version,
            "security_id": self.security_id,
            "symbol": self.symbol,
            "observation_time": self.observation_time.isoformat(),
            "forecast_horizon_end_year": self.forecast_horizon_end_year,
            "reported_facts": asdict(self.reported_facts_reference) if self.reported_facts_reference else None,
            "consensus": asdict(self.consensus_reference) if self.consensus_reference else None,
            "management_guidance": asdict(self.management_guidance_reference) if self.management_guidance_reference else None,
            "industry_outlook": asdict(self.industry_outlook_reference) if self.industry_outlook_reference else None,
            "normalized_bridges": [asdict(b) for b in self.normalized_bridges],
            "research_scenarios": [asdict(s) for s in self.research_scenarios],
            "expectation_gaps": [asdict(g) for g in self.expectation_gaps],
            "capital_stack_commentary": self.capital_stack_commentary,
            "capital_constraints": list(self.capital_constraints),
            "refinancing_dependencies": list(self.refinancing_dependencies),
            "dilution_concerns": list(self.dilution_concerns),
            "catalysts": list(self.catalysts),
            "thesis_invalidation_conditions": list(self.thesis_invalidation_conditions),
            "confidence_status": self.confidence_status.value,
            "validation_status": self.validation_status,
            "warnings": list(self.warnings),
            "ranking_influence": self.ranking_influence,
            "allocation_influence": self.allocation_influence,
        }
    
    def to_json(self) -> str:
        """Serialize to deterministic JSON."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpectationsResearchResult:
        """Deserialize from dictionary."""
        # Reconstruct nested objects
        reported = None
        if data.get("reported_facts"):
            reported = ReportedFacts(**data["reported_facts"])
        
        consensus = None
        if data.get("consensus"):
            consensus = MarketExpectation(**data["consensus"])
        
        guidance = None
        if data.get("management_guidance"):
            guidance = MarketExpectation(**data["management_guidance"])
        
        industry = None
        if data.get("industry_outlook"):
            industry = IndustryOutlook(**data["industry_outlook"])
        
        bridges = tuple(NormalizedEarningsBridge(**b) for b in data.get("normalized_bridges", []))
        scenarios = tuple(ResearchScenario(**s) for s in data.get("research_scenarios", []))
        gaps = tuple(ExpectationGap(**g) for g in data.get("expectation_gaps", []))
        
        return cls(
            security_id=data["security_id"],
            symbol=data["symbol"],
            observation_time=datetime.fromisoformat(data["observation_time"]),
            forecast_horizon_end_year=data["forecast_horizon_end_year"],
            reported_facts_reference=reported,
            consensus_reference=consensus,
            management_guidance_reference=guidance,
            industry_outlook_reference=industry,
            normalized_bridges=bridges,
            research_scenarios=scenarios,
            expectation_gaps=gaps,
            capital_stack_commentary=data.get("capital_stack_commentary", ""),
            capital_constraints=tuple(data.get("capital_constraints", [])),
            refinancing_dependencies=tuple(data.get("refinancing_dependencies", [])),
            dilution_concerns=tuple(data.get("dilution_concerns", [])),
            catalysts=tuple(data.get("catalysts", [])),
            thesis_invalidation_conditions=tuple(data.get("thesis_invalidation_conditions", [])),
            confidence_status=ConfidenceLevel(data.get("confidence_status", "LOW")),
            validation_status=data.get("validation_status", "UNVALIDATED"),
            warnings=tuple(data.get("warnings", [])),
        )
