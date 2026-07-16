# Expectations & Mispricing Research v1

**Purpose**: Independent research lens for analyzing expectation misalignment and analytical opportunities without directly influencing portfolio ranking or capital allocation until separately validated.

**Key Constraint**: `ranking_influence = 0.0`, `allocation_influence = 0.0` by design. These values cannot be modified through configuration; attempting to set them to non-zero raises `ValueError`.

## Architecture Overview

### Three Separate Expectation Layers

Expectations research maintains three independent layers, each with distinct data sources and validation requirements:

#### 1. **Reported Facts** (`ReportedFacts`)
- Audited financial figures from SEC filings, earnings calls
- Point-in-time: available_at ≤ observation_time
- Fields: Revenue, EBITDA, EBIT, net income, EPS, cash flow, balance sheet items
- Includes management adjustments (stock-based comp, nonrecurring items) tracked separately
- **Example**: Q4 2023 revenue $1B, EBITDA $250M filed on date X (available Jan 10)

#### 2. **Market Expectations** (`MarketExpectation`)
- Consensus analyst estimates, management guidance, market-implied metrics
- Separate records for each source type (consensus, guidance, market-implied)
- Timestamp: `as_of` indicates when estimate was current
- Point-in-time: available_at ≤ observation_time, as_of ≤ observation_time
- Fields: Revenue, EBITDA, EPS, FCF forecasts for horizon period
- **Example**: Consensus Q4 2024E revenue $1.05B (15 estimates, revision trend up)

#### 3. **Research Scenarios** (`ResearchScenario`)
- Alpha Velocity proprietary forecasts: bear, base, bull
- Horizon: Multiple-year forward period (e.g., 2024-2026)
- Independent assumptions per scenario
- CAGR expectations: Bear -3%, Base +3.5%, Bull +8%
- Provenance tracking: `human_authored` vs `model_generated`
- **Example**: Bull case revenue CAGR 8%, ebitda_margin 28.5%, FCF $210M by 2026

### Core Data Structures

```python
# Reported facts (immutable, frozen dataclass)
ReportedFacts(
    security_id="SEC123",
    symbol="TEST",
    observation_time=datetime(2024, 1, 15, tzinfo=UTC),
    available_at=datetime(2024, 1, 10, tzinfo=UTC),  # Point-in-time
    fiscal_year=2023,
    revenue=1_000_000_000,
    ebitda=250_000_000,
    eps=3.00,
)

# Market expectation (consensus, guidance, or market-implied)
MarketExpectation(
    source=ExpectationSource.CONSENSUS,
    as_of=datetime(2024, 1, 13, tzinfo=UTC),  # When estimate was current
    horizon_year=2024,
    revenue=1_050_000_000,  # $1.05B
    eps=3.30,
    estimate_count=15,
    revision_trend="up",
)

# Research scenario (bear/base/bull)
ResearchScenario(
    scenario="base",
    horizon_start_year=2024,
    horizon_end_year=2026,
    revenue_forecast_year_end=1_150_000_000,
    revenue_cagr_pct=3.5,
    ebitda_margin_pct=26.0,
)
```

## Normalized Earnings Bridge

Bridges reported figures to normalized metrics through documented adjustments.

### Bridge Concept

The bridge transforms reported EBITDA into normalized EBITDA by accounting for:
- One-time gains/losses (nonrecurring items)
- Restructuring charges
- Stock-based compensation (typically recurring)
- Acquisition integration costs
- Impairments or pension adjustments

### Example Bridge

```
Reported Revenue:              $1,000M
Reported EBITDA:              $250M

Adjustments (addbacks):
  (-) Restructuring:           $50M    (one-time)
  (-) Asset sale gain:         $40M    (nonrecurring)
  (-) Stock comp:              $20M    (recurring)

Normalized EBITDA:            $360M   (+=50+40+20)
Normalized Margin:            36.0%
```

### Adjustment Detail Fields

Each adjustment includes complete metadata:

```python
AdjustmentDetail(
    category=AdjustmentCategory.RESTRUCTURING,
    amount=50_000_000.0,
    rationale="Q1 restructuring initiative",
    source="earnings_call",
    available_at=datetime(2024, 1, 10, tzinfo=UTC),  # When known
    recurring=False,
    confidence=ConfidenceLevel.HIGH,
    validation_status="VALIDATED",
    supporting_detail="Management disclosed in 8-K",
)
```

### Reproducibility

Bridge recalculation from adjustments tuple must be deterministic:
1. Start with reported figures (revenue, EBITDA, EBIT, net income, EPS)
2. Sum all adjustments by category
3. Add adjustments to reported figures
4. Serialize with sorted keys, ISO 8601 dates

**Test**: `test_reproducible_ebitda_bridge` verifies identical JSON serialization across multiple calculations.

## Expectation Gap Analysis

Compares reported vs consensus, guidance vs consensus, research vs market expectations.

### Gap Calculation

```
Gap Analysis Output:
  - gap_type: "consensus_vs_reported"
  - metric: "revenue"
  - layer_1_value: $1.00B (reported)
  - layer_2_value: $1.05B (consensus)
  - gap_amount: +$50M
  - gap_pct: +5.0%
  - gap_direction: "bullish"
  - catalyst_required: "Execution on volume targets"
```

### Gap Direction Logic

- **Bullish**: Consensus/guidance/research > reported
- **Bearish**: Consensus/guidance/research < reported
- **Neutral**: Consensus/guidance/research ≈ reported (within 2%)

Gap direction informs thesis development but does not directly rank securities.

## Company Forecasting Drivers

Research scenarios document explicit assumptions about company performance.

### Assumption Types

1. **Market/Macro Drivers**
   - Market growth rate (e.g., enterprise software +12% CAGR)
   - Pricing power (industry pricing +2% annually)
   - Market share assumptions

2. **Company-Specific Drivers**
   - Product adoption timeline
   - Margin expansion path (R&D leverage)
   - Capital efficiency (capex/revenue declining)
   - Customer concentration risks

3. **Capital Structure**
   - Interest rate assumptions
   - Refinancing risk timeline
   - Dilution expectations (equity issuance)

### Forward Assumptions Structure

```python
ForwardAssumption(
    name="market_growth_assumption",
    value=12.0,
    unit="pct",
    rationale="Linked to enterprise software industry growth",
    source="ref:industry:TECH_SOFTWARE",
    confidence=ConfidenceLevel.HIGH,
    horizon_year=2024,
)
```

Assumptions can reference industry outlook via `source="ref:industry:{industry_id}"`.

## Industry Outlook

Captures industry-level assumptions and constraints that affect company forecasts.

### Outlook Dimensions

```python
IndustryOutlook(
    industry_id="TECH_SOFTWARE",
    industry_name="Enterprise Software",
    observation_time=datetime(2024, 1, 15, tzinfo=UTC),
    
    # Demand environment
    demand_outlook="strong_growth",  # Options: strong_growth, modest_growth, stable, contraction
    demand_growth_rate_pct=12.0,
    
    # Pricing environment
    pricing_power="strong",  # Options: strong, moderate, weak
    expected_price_change_pct=2.0,
    
    # Supply/capacity
    capacity_utilization_pct=82.0,
    capacity_additions_outlook="accelerating",
    
    # Input costs
    input_cost_outlook="stable",  # Options: declining, stable, rising
    
    # Supply chain
    supply_chain_risk="low",  # Options: low, moderate, high
    
    # Macro sensitivity
    rate_sensitivity="moderate",
    credit_conditions_outlook="normal",
    
    # Cycle timing
    cycle_stage="peak",  # Options: recovery, peak, contraction, trough
)
```

### Cycle Stage Framework

- **Recovery**: Rising volumes, capacity utilization climbing, pricing stable
- **Peak**: High utilization, pricing power maximum, competitive intensity increasing
- **Contraction**: Volume decline, pricing pressure, capacity rationalization
- **Trough**: Stabilization signals emerging, pricing power improving, consolidation

## Capital Structure Constraints

Research output tracks capital-stack implications separately from valuation assumptions.

### Capital-Stack Components

1. **Net Debt Outlook**: Total debt minus cash
2. **Leverage Ratio**: Net debt / EBITDA
3. **Interest Coverage**: EBITDA / Interest expense
4. **Refinancing Dependencies**: Maturity schedule, rates at refinancing
5. **Dilution Concerns**: Equity issuance needs based on FCF/debt reduction

### Example: Strong EBITDA Growth + Distressed Capital Structure

```
Bull Case:
  EBITDA CAGR: +8%
  FCF: $250M annually
  
Capital Constraints:
  - Net debt rising to $800M despite strong FCF
  - Interest expense consuming 20% of EBITDA
  - Refinancing due 2025 at likely higher rates
  - Equity issuance likely needed to deleverage

Implication: FCF growth doesn't translate to equity value while leveraged
```

Capital-stack constraints are documented but **do not reduce ranking score** until separately validated in capital structure analysis.

## Point-in-Time Validation

All timestamps enforce historical consistency.

### Validation Rules

1. **Available dates**: `available_at ≤ observation_time`
   - Reported facts cannot be available before filing date
   - Consensus estimates cannot be available before publication
   - Adjustments cannot be known before disclosure

2. **Guidance as-of dates**: `as_of ≤ observation_time`
   - Management guidance effective date must precede analysis date
   - Prevents "future guidance" scenarios

3. **Scenario dates**: All input data must be contemporaneous with observation_time
   - Rejects scenarios built on future information

### Enforcement

```python
# Raises ValueError if violated
ReportedFacts(
    observation_time=datetime(2024, 1, 15),
    available_at=datetime(2024, 1, 20),  # ❌ Future!
)

# Raises ValueError if violated
engine.build_research(
    observation_time=datetime(2024, 1, 15),
    management_guidance=MarketExpectation(
        as_of=datetime(2024, 1, 20),  # ❌ Future guidance!
    ),
)
```

## Validation Gates & Confidence Scoring

Confidence in expectations research reflects data quality and coverage.

### Confidence Components

| Component | Points | Logic |
|-----------|--------|-------|
| Reported facts | +2 | Complete 10-K/10-Q |
| Consensus estimates | +1 | Analyst coverage |
| Management guidance | +1 | Guidance released |
| Industry outlook | +1 | Macro research |
| Scenarios (1+) | +1 | At least one scenario |
| Scenarios (3+) | +2 | Full bear/base/bull |
| Bridges (% validated) | 0-2 | Adjustment quality |
| **Per warning** | -1 | Data gaps, low confidence |

### Confidence Thresholds

- **HIGH** (8+): Multi-layer consensus, validated bridges, few warnings
- **MODERATE** (5-7): Mix of reported/guidance/scenarios, some gaps
- **LOW** (<5): Limited data, missing key assumptions

## Zero Influence Enforcement

Expectations research output has **zero influence on portfolio ranking and allocation by default**.

### Design Rationale

1. **Separation of concerns**: Analysis lens independent from portfolio decision
2. **Multi-stage validation**: Gaps require separate catalyst/validation before impacting rank
3. **No leakage**: Researcher cannot accidentally influence live signals

### Implementation

```python
# ExpectationsResearchResult.__post_init__ enforces:
if ranking_influence != 0.0 or allocation_influence != 0.0:
    raise ValueError("ranking_influence and allocation_influence must be 0.0")

# Result always carries:
result.ranking_influence = 0.0
result.allocation_influence = 0.0
```

Attempting to set influence to non-zero raises `ValueError` immediately.

## Integration with Opportunity Ranking

Expectations research feeds **read-only insights** to ranking engine.

### Usage Pattern

1. **Expectations Run**: `engine.build_research()` produces independent analysis
2. **Validation Lens**: Separate validation artifact (not yet implemented) evaluates gaps
3. **Conditional Influence**: Once validated, ranking engine can optionally reference
4. **Audit Trail**: All influence decisions logged in ranking lineage

### Current Constraints

- ✅ Zero influence by default
- ✅ Point-in-time validation enforced
- ✅ No broker calls, order creation, portfolio mutation
- ✅ Immutable output (frozen dataclasses)
- ⏳ Validation artifact (future work)
- ⏳ Dynamic influence adjustment (future work)

## Deterministic Serialization

All output serializes identically across runs for audit and reconstruction.

### Serialization Rules

1. **Dictionary format**: `to_dict()` with flattened structure
2. **Sorting**: Keys sorted alphabetically
3. **Dates**: ISO 8601 format with timezone
4. **Enums**: Serialized as string values
5. **Collections**: Tuples converted to lists

### Example

```python
# Two calls produce identical JSON
result1 = engine.build_research(...)
result2 = engine.build_research(...)

json1 = result1.to_json()
json2 = result2.to_json()

assert json1 == json2  # ✅ Always true
```

**Test**: `test_deterministic_serialization` verifies identical output.

## Rejection of Future Data

System validates against predictive contamination.

### Rejected Scenarios

```python
# ❌ Reported fact filed in future
ReportedFacts(
    observation_time=datetime(2024, 1, 15),
    available_at=datetime(2024, 1, 20),  # ValueError
)

# ❌ Consensus estimate published in future
MarketExpectation(
    observation_time=datetime(2024, 1, 15),
    available_at=datetime(2024, 1, 20),  # ValueError
)

# ❌ Adjustment amount known after observation
AdjustmentDetail(
    available_at=datetime(2024, 1, 20),  # ValueError if available_at > observation_time
)
```

All create `ValueError` with clear message.

## Limitations & Future Work

### Current Limitations

1. **No FCF Forecasting**: Placeholder field only, no auto-projection logic
2. **No Macro Integration**: Interest rate scenarios static
3. **No Covenant Triggers**: Doesn't predict debt covenant violations
4. **No Dynamic Dilution**: Dilution model is static ("concerns" list only)
5. **No Validation Artifact**: Gaps exist but are not validated separately
6. **Manual Assumption Input**: All assumptions require manual entry

### Future Work

1. **FCF Bridge**: Detailed cash flow build-up from EBIT
2. **Macro Scenarios**: Auto-project rates, inflation, currency
3. **Covenant Analysis**: Auto-check covenant breach probabilities
4. **Dynamic Dilution**: Model share count impact of financing
5. **Validation Engine**: Separate artifact validating gaps before ranking
6. **Auto Assumptions**: ML/domain model for assumption defaults

## Files & Structure

```
alpha_velocity/expectations/
  __init__.py           # Package exports
  models.py             # All immutable dataclasses (800 lines)
  engine.py             # ExpectationsResearchEngine (350 lines)

tests/
  test_expectations_research.py  # 17 comprehensive tests
```

## Testing

Run expectations-specific tests:

```bash
pytest tests/test_expectations_research.py -v
```

Expected output: 17/17 passing

Test categories:
- **Reported vs Normalized** (1 test): Separation of concerns
- **Reproducible Bridge** (1 test): Deterministic recalculation
- **Future Rejection** (3 tests): Validation of point-in-time
- **Analyst Timing** (1 test): Revision history constraints
- **Scenarios** (1 test): Independent bear/base/bull
- **Industry Linkage** (1 test): Assumption references
- **Capital-Stack** (1 test): Constraint tracking
- **Zero Influence** (2 tests): Default and enforcement
- **Serialization** (1 test): Deterministic JSON
- **Constraints** (3 tests): No broker/orders/mutations
- **Gap Analysis** (1 test): Expectation comparison
- **Missing Data** (1 test): Graceful handling

## Example Usage

```python
from datetime import datetime, timezone, timedelta
from alpha_velocity.expectations import (
    ExpectationsResearchEngine,
    ReportedFacts,
    MarketExpectation,
    ResearchScenario,
    ConfidenceLevel,
)

observation_time = datetime(2024, 1, 15, tzinfo=timezone.utc)

# Populate reported facts
reported = ReportedFacts(
    security_id="SEC123",
    symbol="TEST",
    observation_time=observation_time,
    available_at=observation_time - timedelta(days=5),
    fiscal_year=2023,
    revenue=1_000_000_000,
    ebitda=250_000_000,
    eps=3.00,
)

# Consensus estimates
consensus = MarketExpectation(
    security_id="SEC123",
    observation_time=observation_time,
    available_at=observation_time - timedelta(days=2),
    source=ExpectationSource.CONSENSUS,
    as_of=observation_time - timedelta(days=2),
    horizon_year=2024,
    revenue=1_050_000_000,
    eps=3.30,
)

# Build research
engine = ExpectationsResearchEngine()
result = engine.build_research(
    security_id="SEC123",
    symbol="TEST",
    observation_time=observation_time,
    forecast_horizon_end_year=2025,
    reported_facts=reported,
    consensus_expectation=consensus,
)

# Output is read-only, zero influence
print(f"Ranking influence: {result.ranking_influence}")  # 0.0
print(f"Gaps: {len(result.expectation_gaps)}")
print(f"Confidence: {result.confidence_status}")  # ConfidenceLevel.MODERATE
```

## Summary

Expectations & Mispricing Research v1 provides a **provider-neutral, point-in-time system** for tracking expectation misalignment across three independent layers (reported, market, research). All output is **immutable, zero-influence by default**, and **deterministically serialized** for audit. The system rejects future data, validates historical consistency, and documents all assumptions for reproducibility.

Key design principle: **Independent research lens, not a ranking signal—until separately validated.**
