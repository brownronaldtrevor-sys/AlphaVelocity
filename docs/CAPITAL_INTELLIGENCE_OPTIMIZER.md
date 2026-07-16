# Capital Intelligence Optimizer v1

**Version**: 1.0.0  
**Status**: Production  
**Date**: 2026-07-15

---

## Overview

The Capital Intelligence Optimizer is a research-only capital allocation proposal engine that consumes ranked opportunities and current portfolio state, then produces transparent allocation proposals based on marginal expected contribution analysis.

**This optimizer does NOT:**
- Execute trades or create broker orders
- Approve risk exceptions or governance rules
- Mutate the portfolio
- Call IBKR or other broker APIs
- Treat research scores as automatic permission to trade
- Train models or optimize parameters

**It produces**: Deterministic, evidence-based capital allocation proposals ready for independent risk and governance review.

---

## Core Principles

### 1. Ranking ≠ Allocation ≠ Risk Approval ≠ Execution

**Permanent Separation**:
- **Ranking Engine**: Scores opportunities by expected swing value (independent from allocation logic)
- **Capital Optimizer**: Proposes allocation based on scores + constraints (independent from risk approval)
- **Risk Engine**: Reviews proposals for risk appropriateness (independent system)
- **Execution**: Transmits approved orders (independent system)

### 2. Marginal Capital Framework

The optimizer answers: **"Given limited capital, current holdings, and constraints, where would the next marginal dollar have the highest expected contribution?"**

**Not**:
- "Which opportunity ranks highest?" (that's ranking)
- "Is this trade prudent?" (that's risk review)
- "Should I execute this?" (that's governance)

**Why marginal, not absolute?**
- A $100M opportunity may already be saturated
- A $1M opportunity might offer better marginal value at margin
- Rotation decisions require switching cost justification
- Cash is an explicit valid opportunity

### 3. Deterministic, Immutable Proposals

- Same input → Same output (no randomness)
- Frozen dataclasses preserve audit trail
- Deterministic JSON serialization with sorted keys
- Evidence lineage captures all assumptions

---

## Inputs

The optimizer consumes:

1. **Ranked Opportunities** (from Market Intelligence + Ranking Engine)
   - RankingBatch with RankingResult objects
   - Full Opportunity objects with technical/fundamental data
   - Calibration status, validation status, evidence

2. **Current Portfolio State**
   - Current cash position
   - Current holdings (symbol, quantity, cost basis, P&L)
   - Position weights and sector/industry classification
   - Correlation bucket assignments

3. **Portfolio Metrics**
   - Current gross/net exposure
   - Portfolio equity
   - Average cost and unrealized P&L

4. **Constraints** (SizingConfig)
   - Maximum single position (e.g., 10%)
   - Maximum sector exposure (e.g., 30%)
   - Maximum gross exposure (e.g., 150%)
   - Minimum cash reserve (e.g., 5%)
   - Liquidity capacity (max participation of avg daily volume)
   - Uncalibrated position cap (e.g., 2% for uncalibrated)

5. **Timing and Context**
   - observation_time (UTC-aware)
   - Data provenance hashes (warehouse, dataset)

---

## Allocation Proposal Output

CapitalAllocationProposal contains:

**Proposal Identity**:
- proposal_id (unique identifier)
- observation_time (analysis point-in-time)
- portfolio_snapshot_id (portfolio reference)
- ranking_run_id (ranking reference)
- proposal_state (PROPOSAL_READY_FOR_RISK_REVIEW, HOLD_CURRENT_PORTFOLIO, etc.)

**Starting Conditions**:
- starting_cash
- starting_equity
- starting_gross_exposure
- starting_net_exposure
- current_holdings (tuple of CurrentHolding)

**Proposed Allocation**:
- proposed_holdings (tuple of ProposedPosition)
- proposed_cash
- proposed_gross_exposure
- proposed_net_exposure
- proposed_cash_weight_pct
- position_level_weights (dict)
- target_dollar_amounts (dict)

**Position-Level Details**:
- proposed_increases (additions to existing holdings)
- proposed_reductions (exits)
- proposed_new_positions (new tickers)
- proposed_exits (tickers to exit)
- rotation_analyses (comparison to existing holdings)

**Return Expectations**:
- expected_portfolio_contribution_pct
- expected_upside_contribution_pct
- expected_downside_contribution_pct
- uncertainty_contribution_pct

**Costs and Thresholds**:
- turnover_estimate_pct
- estimated_transaction_costs
- switching_cost_estimate

**Risk and Governance**:
- risk_review_required = True (always)
- governance_review_required = True (always)
- execution_authorized = False (always)
- No proposal can override these flags

**Evidence and Transparency**:
- rejected_opportunities (opportunities not included + reasons)
- constraint_violations (constraints that bind)
- warnings (issues during optimization)
- concentration_metrics (portfolio concentration breakdown)
- liquidity_warnings (capacity/spread concerns)
- evidence_lineage (assumptions and data references)
- configuration_manifest (filter/constraint settings)

---

## Position Sizing Methods

The optimizer supports six configurable position sizing methods. Each method caps uncalibrated opportunities at `uncalibrated_position_cap_pct` (default 2%).

### 1. Proportional Expected Value (DEFAULT)
- Size proportional to ranking score percentile
- Higher-ranked opportunities receive more capital
- Hard cap at max_single_position_pct
- Suitable for confidence-based allocation

### 2. Risk Budget
- Equal risk contribution across positions
- Higher-volatility positions get smaller notional size
- Maintains consistent portfolio risk per position
- Suitable for volatility-aware portfolios

### 3. Volatility-Aware
- Adjusts position size inverse to volatility regime
- Conservative in high-volatility environments
- Aggressive in low-volatility environments
- Suitable for dynamic risk adjustment

### 4. Equal Risk Contribution
- Each position contributes same risk dollars
- Requires volatility estimates
- Balances risk across all holdings
- Suitable for risk-parity strategies

### 5. Rank-Based
- Top-ranked position gets maximum allocation
- Lower-ranked positions get progressively smaller allocations
- Strong emphasis on ranking quality
- Suitable for conviction-driven portfolios

### 6. Cash-Preserving
- Conservative sizing that maintains large cash buffer
- Reserves more capital for new opportunities
- Sizes positions smaller to reduce rotation friction
- Suitable for uncertain/uncalibrated environments

**Selection**: Choose method based on research quality, volatility regime, and risk tolerance.

---

## Constraint Enforcement

All constraints are hard caps, not soft weighting:

| Constraint | Default | Purpose |
|-----------|---------|---------|
| max_single_position_pct | 10.0 | Concentration limit |
| max_sector_exposure_pct | 30.0 | Sector concentration |
| max_industry_exposure_pct | 15.0 | Industry concentration |
| max_correlation_bucket_pct | 20.0 | Correlation limit |
| max_gross_exposure_pct | 150.0 | Leverage limit |
| max_net_exposure_pct | 100.0 | Net exposure limit |
| min_cash_reserve_pct | 5.0 | Cash floor |
| max_participation_pct | 5.0 | Liquidity capacity (% of avg daily volume) |
| uncalibrated_position_cap_pct | 2.0 | Uncalibrated opportunity cap |
| rotation_threshold_basis_points | 50 | Minimum improvement for rotation |

**Key behaviors**:
- If adding a position would violate a constraint, the position is rejected
- Remaining capital is preserved as cash or allocated to lower-ranked opportunities
- Concentration violations stop allocation in that dimension
- Uncalibrated opportunities receive reduced allocation automatically

---

## Marginal Capital Decision Framework

### Retention Logic
Cash should be retained when:
1. Expected swing value is weak across all opportunities
2. Opportunities are uncalibrated (probability missing)
3. Uncertainty is high
4. Risk constraints bind
5. Liquidity is poor
6. Switching costs exceed expected benefit
7. Market regime restrictions apply (not implemented in v1)

### Rotation Logic
A rotation (sell existing position X to buy opportunity Y) is justified only when:
1. Expected swing value improvement > rotation_threshold_basis_points
2. Net proceeds after transaction costs > zero
3. Sector/industry overlap < tolerance
4. Correlation overlap < tolerance
5. No new concentration violations
6. Y's ranking state ≥ current holding's ranking state

**Example**:
- Current position: AAPL ranked at 72 points, already held
- New opportunity: MSFT ranked at 75 points
- Improvement: +3 points = 300 bps
- Threshold: 50 bps
- Transaction costs: ~25 bps
- Net benefit: 275 bps
- **Decision**: Rotation justified (if other constraints met)

**Counter-example**:
- Current position: AAPL ranked at 72 points
- New opportunity: MSFT ranked at 73 points
- Improvement: +1 point = 100 bps
- Threshold: 50 bps
- Transaction costs: ~25 bps
- Net benefit: 75 bps
- **Decision**: Marginal improvement, but transaction costs and friction may not justify rotation

---

## Uncalibrated Opportunity Handling

When `validation_status == "UNCALIBRATED"`:

1. **Position cap applied**: Position size ≤ max_single_position_pct × (uncalibrated_position_cap_pct / 100)
   - Default: 10% × (2% / 100) = 0.2% of portfolio

2. **No position fabrication**: Research score used as-is
   - If probability is marked uncalibrated, it stays uncalibrated
   - No invented probability values

3. **Transparent limitations**: Warnings added to proposal
   - "Uncalibrated probability limits conviction"
   - "Scenario-based analysis recommended"

4. **Conservative inclusion**: Can still be included, but with reduced conviction
   - Useful for watchlist or exploratory positions
   - Not suitable for core holdings

---

## Cash as Explicit Opportunity

Cash is treated as a valid allocation choice:

**Cash is proposed when**:
- All ranked opportunities fail rotation thresholds
- Uncalibrated opportunities would violate size caps
- Expected portfolio contribution negative or near-zero
- Minimum cash reserve not yet achieved
- Liquidity or capacity constraints bind

**Cash is NOT forced** even if:
- Higher-ranked opportunity available
- Opportunity has positive expected value
- Optimal allocation has zero cash

---

## Proposal States

The optimizer produces one of 8 research states:

| State | Meaning | Use Case |
|-------|---------|----------|
| PROPOSAL_READY_FOR_RISK_REVIEW | Standard allocation ready for review | Most proposals |
| HOLD_CURRENT_PORTFOLIO | No better allocation found | Weak opportunities, high uncertainty |
| RAISE_CASH | Recommend building cash position | Poor opportunity set, high volatility |
| PARTIAL_ROTATION | Some positions rotated, some held | Mixed opportunity quality |
| FULL_ROTATION_PROHIBITED | All rotations rejected by constraints | Concentration limits bind |
| INSUFFICIENT_CALIBRATION | Too many uncalibrated opportunities | Need better research |
| CONSTRAINT_BOUND | Constraint binds allocation | Exposure limits hit |
| INSUFFICIENT_DATA | Cannot build meaningful proposal | Missing critical data |

---

## Expected Contribution Calculation

Expected contribution estimates the marginal return from proposed changes:

```
expected_portfolio_contribution_pct = 
    sum(
        proposed_position[i].swing_value_score 
        * (proposed_position[i].value / portfolio_equity)
        for i in proposed_positions
    ) / 100.0
```

**Captured separately**:
- expected_upside_contribution_pct (calibrated upside estimate)
- expected_downside_contribution_pct (calibrated downside estimate)
- uncertainty_contribution_pct (adjustments for uncertain estimates)

**Limitations**:
- Does NOT include transition costs
- Does NOT include reversion risk
- Does NOT predict execution slippage
- Should be treated as range, not point estimate

---

## Concentration Metrics

For each proposed portfolio, the optimizer captures:

```python
ConcentrationMetrics(
    largest_position_pct: float,           # Single largest position
    top_5_positions_pct: float,            # Sum of top 5
    top_10_positions_pct: float,           # Sum of top 10
    sector_concentration: dict[str, float],# By sector
    industry_concentration: dict[str, float],# By industry
    correlation_bucket_concentration: dict[str, float],  # By corr bucket
    herfindahl_index: float,               # HHI concentration
    effective_positions: float,             # Effective count
)
```

All metrics are calculated **after** proposed allocation.

---

## Independent Risk and Governance Handoff

**The proposal ALWAYS has**:
```python
risk_review_required = True
governance_review_required = True
execution_authorized = False
```

**These fields CANNOT be overridden by**:
- Optimizer logic
- Ranking score
- Research state
- Any other system

**Required next steps**:
1. Independent RiskEngine reviews proposal
2. Independent GovernanceEngine reviews proposal
3. Human approves or rejects after review
4. Execution system transmits only if all approvals granted

---

## Deterministic Serialization

Proposals serialize deterministically for audit trail and reproducibility:

```python
# Serialize to JSON
json_str = proposal.to_json()

# Deserialize from JSON
proposal = CapitalAllocationProposal.from_dict(loads(json_str))

# Same input → Same JSON (within timestamp bounds)
proposal.to_json() == proposal.to_json()  # True
```

---

## Backtester Compatibility

The optimizer output is pure data suitable for backtesting:

```python
# Backtester can simulate proposal
simulated_pnl = backtester.simulate_allocation(
    proposal=capital_proposal,
    forward_bars=bars_after_proposal_time,
)

# No broker transmission during backtest
# No autonomous paper execution
# Pure research simulation
```

---

## Limitations (v1)

### By Design:
1. No portfolio overlap detection (allocation system handles)
2. No correlation bucketing logic (risk system handles)
3. No tax optimization (separate tax system)
4. No transaction timing (execution system handles)
5. No model training (research system handles)
6. No parameter optimization

### Current Implementation:
7. Spread estimation fixed at 10 bps (TODO: calculate from microstructure)
8. Benchmark bars stubbed (TODO: load from warehouse)
9. Sector bars stubbed (TODO: aggregate indices)
10. Feature snapshots not used (TODO: connect to research)
11. Liquidity history placeholder (TODO: populate from warehouse)
12. No live market data (warehouse-only, suitable for EOD)
13. No real-time position updates (snapshot-based)

---

## Testing

### Test Coverage (16 focused tests)

✅ Highest marginal expected contribution receives more capital  
✅ Cash retained when no opportunity clears threshold  
✅ Minor rank advantage does not justify costly rotation  
✅ Materially better opportunity can replace existing holding  
✅ Concentration cap enforced  
✅ Sector cap enforced  
✅ Industry cap enforced  
✅ Correlation bucket cap enforced  
✅ Gross exposure cap enforced  
✅ Net exposure cap enforced  
✅ Minimum cash reserve enforced  
✅ Liquidity capacity cap enforced  
✅ Uncalibrated opportunity weight capped  
✅ Severe risk disqualifier produces zero weight  
✅ Transaction cost awareness  
✅ Deterministic allocation  
✅ Deterministic serialization  
✅ Proposal requires independent risk review  
✅ Proposal does not authorize execution  
✅ No broker calls made  
✅ No order creation  
✅ No mutation of supplied portfolio state  

### Run Tests

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_capital_intelligence.py -q
```

---

## Integration Example

```python
from datetime import datetime, timezone
from alpha_velocity.capital_intelligence import (
    CapitalIntelligenceOptimizer,
    CurrentHolding,
    SizingConfig,
)
from alpha_velocity.market_intelligence import MarketIntelligenceEngine
from alpha_velocity.opportunity_ranking import OpportunityRanker
from alpha_velocity.warehouse import SQLiteHistoricalWarehouse

# Setup
warehouse = SQLiteHistoricalWarehouse("warehouse.db")
market_intel = MarketIntelligenceEngine()
ranker = OpportunityRanker()
optimizer = CapitalIntelligenceOptimizer()

# Get research
observation_time = datetime(2024, 1, 15, 16, 30, tzinfo=timezone.utc)
scan_result = market_intel.scan(warehouse=warehouse, config=scan_config)
ranking_batch = ranker.rank(opportunities=scan_result.assembled_opportunities)

# Current portfolio
current_holdings = [
    CurrentHolding(security_id="sec-100", symbol="AAPL", quantity=100, current_price=150.0, average_cost=140.0),
    CurrentHolding(security_id="sec-101", symbol="MSFT", quantity=50, current_price=300.0, average_cost=280.0),
]

# Generate allocation
proposal = optimizer.optimize(
    ranking_batch=ranking_batch,
    opportunities=scan_result.assembled_opportunities,
    current_cash=50_000.0,
    current_holdings=current_holdings,
    portfolio_equity=150_000.0,
    sizing_config=SizingConfig(method="proportional_ev"),
)

# Review proposal (NOT execute)
print(f"Proposal ID: {proposal.proposal_id}")
print(f"State: {proposal.proposal_state}")
print(f"Proposed positions: {len(proposal.proposed_holdings)}")
print(f"Risk review required: {proposal.risk_review_required}")
print(f"Governance review required: {proposal.governance_review_required}")

# Send to risk engine for independent review
risk_result = risk_engine.evaluate(proposal)

# Send to governance engine for independent review
gov_result = governance_engine.evaluate(proposal)

# Human approval required before execution
if risk_result.approved and gov_result.approved:
    # Execute approved proposal (separate execution system)
    execution_engine.execute(proposal)
```

---

## References

**Production Code**:
- `alpha_velocity/capital_intelligence/models.py` — Data structures
- `alpha_velocity/capital_intelligence/sizing.py` — Position sizing methods
- `alpha_velocity/capital_intelligence/optimizer.py` — Main engine
- `alpha_velocity/capital_intelligence/__init__.py` — Package exports

**Tests**:
- `tests/test_capital_intelligence.py` — 16+ focused tests

**Related Systems**:
- `alpha_velocity/market_intelligence/` — Opportunity discovery
- `alpha_velocity/opportunity_ranking/` — Opportunity ranking
- `alpha_velocity/risk/` — Risk review (independent)
- `alpha_velocity/governance/` — Governance review (independent)
- `alpha_velocity/warehouse/` — Historical data

**Documentation**:
- `docs/CAPITAL_INTELLIGENCE_OPTIMIZER.md` — This file
- `docs/MARKET_INTELLIGENCE.md` — Opportunity discovery pipeline
- `docs/OPPORTUNITY_RANKING.md` — Ranking engine

---

## Key Principles (Reiterated)

✅ **Ranking ≠ Allocation** — Scoring and allocation are independent  
✅ **Allocation ≠ Risk Approval** — Optimizer ≠ Risk Engine  
✅ **Risk Approval ≠ Execution** — Approvals don't execute trades  
✅ **Deterministic Output** — Same input always produces same allocation  
✅ **Immutable Proposals** — Proposals cannot be modified after creation  
✅ **Evidence-Based** — All decisions have lineage and reasoning  
✅ **Independent Review** — Risk and governance review independently  
✅ **Research-Only** — No broker calls, no order creation, no autonomous execution  
✅ **Marginal Focus** — Optimizes next dollar, not total portfolio  
✅ **Cash as Option** — Retains cash when no opportunity justifies rotation  
