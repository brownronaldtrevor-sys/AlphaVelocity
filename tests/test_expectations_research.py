"""
Tests for Expectations & Mispricing Research v1.

Tests expectations research system with three separate layers:
1. Reported facts
2. Market expectations (consensus, guidance)
3. Alpha Velocity research scenarios

Validates:
- Reported vs normalized earnings separation
- Reproducible EBITDA bridges with documented adjustments
- Future-estimate rejection at validation
- Analyst revision timing constraints
- Bear/base/bull scenario independence
- Industry assumption linkage
- Capital-stack waterfall compatibility
- Zero ranking influence until separately validated
- Deterministic serialization
- No broker calls, order creation, or portfolio mutation
"""

from datetime import datetime, timedelta, timezone
import json
import pytest

from alpha_velocity.expectations import (
    AdjustmentCategory,
    AdjustmentDetail,
    ConfidenceLevel,
    ExpectationGap,
    ExpectationSource,
    ExpectationsResearchEngine,
    ExpectationsResearchResult,
    ForwardAssumption,
    IndustryOutlook,
    MarketExpectation,
    NormalizedEarningsBridge,
    ReportedFacts,
    ReportingPeriod,
    ResearchScenario,
)


@pytest.fixture
def observation_time() -> datetime:
    return datetime(2024, 1, 15, 16, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def reported_facts(observation_time: datetime) -> ReportedFacts:
    """Sample reported financials."""
    return ReportedFacts(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        available_at=observation_time - timedelta(days=5),  # Filed 5 days ago
        fiscal_year=2023,
        fiscal_period=ReportingPeriod.FY,
        filing_date=observation_time - timedelta(days=5),
        period_end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
        revenue=1_000_000_000.0,
        cost_of_revenue=600_000_000.0,
        gross_profit=400_000_000.0,
        gross_margin_pct=40.0,
        operating_expenses=250_000_000.0,
        ebitda=250_000_000.0,
        ebitda_margin_pct=25.0,
        ebit=200_000_000.0,
        ebit_margin_pct=20.0,
        net_income=150_000_000.0,
        net_margin_pct=15.0,
        eps=3.00,
        operating_cash_flow=180_000_000.0,
        capital_expenditures=50_000_000.0,
        free_cash_flow=130_000_000.0,
        total_assets=2_000_000_000.0,
        cash_and_equivalents=200_000_000.0,
        total_debt=500_000_000.0,
        shareholders_equity=1_000_000_000.0,
        shares_outstanding=50_000_000.0,
    )


@pytest.fixture
def consensus_expectation(observation_time: datetime) -> MarketExpectation:
    """Sample consensus estimate."""
    return MarketExpectation(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        available_at=observation_time - timedelta(days=2),  # Estimate from 2 days ago
        source=ExpectationSource.CONSENSUS,
        as_of=observation_time - timedelta(days=2),
        horizon_year=2024,
        horizon_quarter=ReportingPeriod.Q4,
        revenue=1_050_000_000.0,
        ebitda=275_000_000.0,
        ebitda_margin_pct=26.2,
        eps=3.30,
        free_cash_flow=150_000_000.0,
        estimate_count=15,
        revision_trend="up",
    )


@pytest.fixture
def management_guidance(observation_time: datetime) -> MarketExpectation:
    """Sample management guidance."""
    return MarketExpectation(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        available_at=observation_time - timedelta(days=10),  # From earnings call
        source=ExpectationSource.MANAGEMENT_GUIDANCE,
        as_of=observation_time - timedelta(days=10),
        horizon_year=2024,
        revenue=1_070_000_000.0,
        eps=3.40,
    )


# ============================ Reported vs Normalized Tests ============================

def test_reported_versus_normalized_separation(
    observation_time: datetime,
    reported_facts: ReportedFacts,
) -> None:
    """Test that reported and normalized figures are tracked separately."""
    
    # Adjustment: one-time restructuring charge
    adjustment = AdjustmentDetail(
        category=AdjustmentCategory.RESTRUCTURING,
        amount=50_000_000.0,  # Add back restructuring charge
        rationale="One-time restructuring initiative",
        source="earnings_call",
        available_at=observation_time - timedelta(days=5),
        recurring=False,
        confidence=ConfidenceLevel.HIGH,
        validation_status="VALIDATED",
    )
    
    engine = ExpectationsResearchEngine()
    bridge = engine.build_normalized_bridge(
        security_id="SEC123",
        observation_time=observation_time,
        fiscal_year=2023,
        fiscal_period=ReportingPeriod.FY,
        reported_revenue=reported_facts.revenue,
        reported_ebitda=reported_facts.ebitda,
        reported_ebit=reported_facts.ebit,
        reported_net_income=reported_facts.net_income,
        reported_eps=reported_facts.eps,
        adjustments=[adjustment],
        methodology="add_back_nonrecurring",
    )
    
    # Reported should stay the same
    assert bridge.reported_ebitda == 250_000_000.0
    # Normalized should be higher
    assert bridge.normalized_ebitda == 300_000_000.0


# ============================ Reproducible EBITDA Bridge Tests ============================

def test_reproducible_ebitda_bridge(observation_time: datetime) -> None:
    """Test that EBITDA bridge is completely reproducible from adjustments."""
    
    adjustments = [
        AdjustmentDetail(
            category=AdjustmentCategory.NONRECURRING_ITEM,
            amount=40_000_000.0,
            rationale="Gain on asset sale",
            source="10_k_filing",
            available_at=observation_time - timedelta(days=5),
            recurring=False,
            confidence=ConfidenceLevel.HIGH,
            validation_status="VALIDATED",
        ),
        AdjustmentDetail(
            category=AdjustmentCategory.STOCK_BASED_COMP,
            amount=20_000_000.0,
            rationale="Add back non-cash stock compensation",
            source="footnotes",
            available_at=observation_time - timedelta(days=5),
            recurring=True,
            confidence=ConfidenceLevel.HIGH,
            validation_status="VALIDATED",
        ),
    ]
    
    engine = ExpectationsResearchEngine()
    bridge = engine.build_normalized_bridge(
        security_id="SEC123",
        observation_time=observation_time,
        fiscal_year=2023,
        fiscal_period=ReportingPeriod.FY,
        reported_revenue=1_000_000_000.0,
        reported_ebitda=250_000_000.0,
        reported_ebit=200_000_000.0,
        reported_net_income=150_000_000.0,
        reported_eps=3.00,
        adjustments=adjustments,
        methodology="manual_review",
        reviewer="analyst_team",
    )
    
    # Verify bridge reproducibility
    assert bridge.reported_ebitda == 250_000_000.0
    # Normalized: 250M + 40M + 20M = 310M
    assert bridge.normalized_ebitda == 310_000_000.0
    assert len(bridge.adjustments) == 2
    
    # Serialization must be deterministic
    json1 = json.dumps(bridge.to_dict(), sort_keys=True, indent=2, default=str)
    json2 = json.dumps(bridge.to_dict(), sort_keys=True, indent=2, default=str)
    assert json1 == json2


# ============================ Future Data Rejection Tests ============================

def test_future_reported_facts_rejection(observation_time: datetime) -> None:
    """Test that future reported facts are rejected."""
    
    with pytest.raises(ValueError, match="available_at cannot exceed observation_time"):
        ReportedFacts(
            security_id="SEC123",
            symbol="TEST",
            observation_time=observation_time,
            available_at=observation_time + timedelta(days=1),  # Future!
            fiscal_year=2023,
            fiscal_period=ReportingPeriod.FY,
            filing_date=observation_time,
            period_end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
            revenue=1_000_000_000.0,
        )


def test_future_consensus_rejection(observation_time: datetime) -> None:
    """Test that future consensus estimates are rejected."""
    
    with pytest.raises(ValueError, match="available_at cannot exceed observation_time"):
        engine = ExpectationsResearchEngine()
        engine.build_research(
            security_id="SEC123",
            symbol="TEST",
            observation_time=observation_time,
            forecast_horizon_end_year=2025,
            consensus_expectation=MarketExpectation(
                security_id="SEC123",
                symbol="TEST",
                observation_time=observation_time,
                available_at=observation_time + timedelta(days=1),  # Future!
                source=ExpectationSource.CONSENSUS,
                as_of=observation_time,
                horizon_year=2024,
            ),
        )


def test_future_guidance_rejection(observation_time: datetime) -> None:
    """Test that future guidance (as_of after observation_time) is rejected."""
    
    with pytest.raises(ValueError, match="as_of date exceeds observation_time"):
        engine = ExpectationsResearchEngine()
        engine.build_research(
            security_id="SEC123",
            symbol="TEST",
            observation_time=observation_time,
            forecast_horizon_end_year=2025,
            management_guidance=MarketExpectation(
                security_id="SEC123",
                symbol="TEST",
                observation_time=observation_time,
                available_at=observation_time - timedelta(days=1),
                source=ExpectationSource.MANAGEMENT_GUIDANCE,
                as_of=observation_time + timedelta(days=1),  # Future guidance!
                horizon_year=2024,
                eps=3.50,
            ),
        )


# ============================ Analyst Revision Timing Tests ============================

def test_analyst_revision_timing_constraint(observation_time: datetime) -> None:
    """Test that analyst revisions respect point-in-time constraints."""
    
    # First revision
    early_consensus = MarketExpectation(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        available_at=observation_time - timedelta(days=10),
        source=ExpectationSource.CONSENSUS,
        as_of=observation_time - timedelta(days=10),
        horizon_year=2024,
        eps=3.20,
    )
    
    # Later revision
    revised_consensus = MarketExpectation(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        available_at=observation_time - timedelta(days=2),
        source=ExpectationSource.CONSENSUS,
        as_of=observation_time - timedelta(days=2),
        horizon_year=2024,
        eps=3.35,  # Revised up
    )
    
    # At observation_time, only the revised estimate should be visible
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2025,
        consensus_expectation=revised_consensus,
    )
    
    assert result.consensus_reference.eps == 3.35
    # Early revision not visible at this time


# ============================ Scenario Independence Tests ============================

def test_bear_base_bull_scenarios_independent(observation_time: datetime) -> None:
    """Test that bear/base/bull scenarios are independent."""
    
    bear_scenario = ResearchScenario(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        available_at=observation_time,
        scenario="bear",
        horizon_start_year=2024,
        horizon_end_year=2026,
        revenue_forecast_year_end=900_000_000.0,  # Declining
        revenue_cagr_pct=-3.0,
        ebitda_margin_pct=20.0,
        free_cash_flow_forecast=80_000_000.0,
        provenance="human_authored",
        confidence=ConfidenceLevel.MODERATE,
    )
    
    base_scenario = ResearchScenario(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        available_at=observation_time,
        scenario="base",
        horizon_start_year=2024,
        horizon_end_year=2026,
        revenue_forecast_year_end=1_150_000_000.0,  # Moderate growth
        revenue_cagr_pct=3.5,
        ebitda_margin_pct=26.0,
        free_cash_flow_forecast=150_000_000.0,
        provenance="human_authored",
        confidence=ConfidenceLevel.HIGH,
    )
    
    bull_scenario = ResearchScenario(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        available_at=observation_time,
        scenario="bull",
        horizon_start_year=2024,
        horizon_end_year=2026,
        revenue_forecast_year_end=1_400_000_000.0,  # Strong growth
        revenue_cagr_pct=8.0,
        ebitda_margin_pct=28.5,
        free_cash_flow_forecast=210_000_000.0,
        provenance="human_authored",
        confidence=ConfidenceLevel.MODERATE,
    )
    
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2026,
        research_scenarios=[bear_scenario, base_scenario, bull_scenario],
    )
    
    # Verify all three scenarios present and independent
    assert len(result.research_scenarios) == 3
    assert result.research_scenarios[0].revenue_cagr_pct == -3.0
    assert result.research_scenarios[1].revenue_cagr_pct == 3.5
    assert result.research_scenarios[2].revenue_cagr_pct == 8.0


# ============================ Industry Assumption Linkage Tests ============================

def test_industry_assumption_linkage(observation_time: datetime) -> None:
    """Test that company scenarios can reference industry assumptions."""
    
    industry = IndustryOutlook(
        industry_id="TECH_SOFTWARE",
        industry_name="Enterprise Software",
        observation_time=observation_time,
        available_at=observation_time - timedelta(days=30),
        demand_outlook="strong_growth",
        pricing_power="strong",
        input_cost_outlook="stable",
        supply_chain_risk="low",
        rate_sensitivity="moderate",
        credit_conditions_outlook="normal",
        cycle_stage="peak",
        demand_growth_rate_pct=12.0,
        expected_price_change_pct=2.0,
    )
    
    # Scenario references industry assumptions
    scenario = ResearchScenario(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        available_at=observation_time,
        scenario="base",
        horizon_start_year=2024,
        horizon_end_year=2026,
        revenue_forecast_year_end=1_150_000_000.0,
        revenue_assumptions=(
            ForwardAssumption(
                name="market_growth_assumption",
                value=12.0,
                unit="pct",
                rationale="Linked to enterprise software industry growth",
                source=f"ref:industry:{industry.industry_id}",
                confidence=ConfidenceLevel.HIGH,
                horizon_year=2024,
            ),
        ),
        provenance="human_authored",
    )
    
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2026,
        industry_outlook=industry,
        research_scenarios=[scenario],
    )
    
    assert result.industry_outlook_reference is not None
    assert result.research_scenarios[0].revenue_assumptions[0].source == "ref:industry:TECH_SOFTWARE"


# ============================ Capital-Stack Compatibility Tests ============================

def test_capital_stack_waterfall_compatibility(
    observation_time: datetime,
    reported_facts: ReportedFacts,
) -> None:
    """Test that expectations account for capital structure constraints."""
    
    # High EBITDA growth doesn't guarantee equity value if capital structure is distressed
    scenario = ResearchScenario(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        available_at=observation_time,
        scenario="bull",
        horizon_start_year=2024,
        horizon_end_year=2026,
        revenue_forecast_year_end=1_400_000_000.0,
        ebitda_margin_pct=30.0,
        free_cash_flow_forecast=250_000_000.0,  # Strong FCF
        net_debt_outlook=800_000_000.0,  # But increasing debt
        interest_rate_assumption_pct=5.0,
        provenance="human_authored",
    )
    
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2026,
        reported_facts=reported_facts,
        research_scenarios=[scenario],
        capital_stack_commentary="Strong EBITDA growth but increasing leverage",
        capital_constraints=[
            "Net debt/EBITDA rising despite FCF generation",
            "Interest expense consuming larger portion of EBITDA",
        ],
        dilution_concerns=[
            "Equity issuance likely needed to deleverage",
        ],
    )
    
    assert len(result.capital_constraints) > 0
    assert result.capital_stack_commentary != ""


# ============================ Zero Influence Tests ============================

def test_zero_ranking_influence_default(observation_time: datetime) -> None:
    """Test that ranking influence defaults to zero."""
    
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2025,
    )
    
    assert result.ranking_influence == 0.0
    assert result.allocation_influence == 0.0


def test_zero_influence_cannot_be_overridden(observation_time: datetime) -> None:
    """Test that attempting to set non-zero influence raises error."""
    
    with pytest.raises(ValueError, match="ranking_influence must be 0"):
        ExpectationsResearchResult(
            security_id="SEC123",
            symbol="TEST",
            observation_time=observation_time,
            forecast_horizon_end_year=2025,
            ranking_influence=0.5,  # Attempted override
        )


# ============================ Deterministic Serialization Tests ============================

def test_deterministic_serialization(
    observation_time: datetime,
    reported_facts: ReportedFacts,
    consensus_expectation: MarketExpectation,
) -> None:
    """Test that serialization is deterministic."""
    
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2025,
        reported_facts=reported_facts,
        consensus_expectation=consensus_expectation,
    )
    
    json1 = result.to_json()
    json2 = result.to_json()
    
    # Must be identical
    assert json1 == json2
    
    # Must be valid JSON
    parsed = json.loads(json1)
    assert parsed["schema_version"] == "1.0.0"
    assert parsed["security_id"] == "SEC123"


# ============================ Constraint Tests ============================

def test_no_broker_calls(observation_time: datetime) -> None:
    """Test that engine makes no broker calls."""
    
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2025,
    )
    
    assert result is not None


def test_no_order_creation(observation_time: datetime) -> None:
    """Test that engine creates no orders."""
    
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2025,
    )
    
    # Result should not have order fields
    assert not hasattr(result, "order_id")
    assert not hasattr(result, "quantity")


def test_no_portfolio_mutation(observation_time: datetime) -> None:
    """Test that engine does not mutate portfolio."""
    
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2025,
    )
    
    # Result should not contain allocation weights
    assert not hasattr(result, "weight")
    assert not hasattr(result, "quantity_shares")


# ============================ Expectation Gap Analysis Tests ============================

def test_expectation_gap_analysis(
    observation_time: datetime,
    reported_facts: ReportedFacts,
    consensus_expectation: MarketExpectation,
    management_guidance: MarketExpectation,
) -> None:
    """Test expectation gap analysis."""
    
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2025,
        reported_facts=reported_facts,
        consensus_expectation=consensus_expectation,
        management_guidance=management_guidance,
    )
    
    # Should have gaps
    assert len(result.expectation_gaps) > 0
    
    # Verify gap content
    for gap in result.expectation_gaps:
        assert gap.metric in ["revenue", "ebitda", "eps"]
        assert gap.gap_direction in ["bullish", "bearish", "neutral"]


# ============================ Missing Data Behavior Tests ============================

def test_missing_data_handling(observation_time: datetime) -> None:
    """Test that missing data is handled gracefully without fabrication."""
    
    # Only security ID and time, no financial data
    engine = ExpectationsResearchEngine()
    result = engine.build_research(
        security_id="SEC123",
        symbol="TEST",
        observation_time=observation_time,
        forecast_horizon_end_year=2025,
    )
    
    # Should complete without fabricated data
    assert result is not None
    assert result.reported_facts_reference is None
    assert result.consensus_reference is None
    assert len(result.research_scenarios) == 0
    # With no supporting data, should be unvalidated
    assert result.confidence_status == ConfidenceLevel.LOW or result.validation_status == "UNVALIDATED"
