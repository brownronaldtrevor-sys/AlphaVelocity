# Opportunity Ranking Engine

**Version**: 1.0.0  
**Status**: Production  
**Date**: 2026-07-15

---

## Core Objective

**Rank opportunities by the highest expected favorable swing value over the intended trading horizon.**

The engine does **not** optimize for:
- Cheapness alone
- Technical strength alone  
- Momentum alone
- Liquidity alone

Instead, it combines valuation, timing quality, and probability-magnitude into a single expected swing value metric that reflects the true economic opportunity.

---

## Three-Component Scoring Architecture

### Component 1: Intrinsic Opportunity Score (30% weight)

**What It Measures**: Fundamental valuation and capital structure health.

**Inputs**:
- Valuation expectation gap (current price vs fair value scenarios)
- Enterprise-to-equity value relationship
- Capital structure composition and safety
- Debt maturity profile and refinancing risk
- Liquidity runway
- Industry and company outlook

**Output**: 0-100 score representing how attractive the opportunity is from a fundamental perspective.

**Key Rule**: Intrinsic score reflects "if I hold this for its full thesis to play out, what's the value?" Independent of timing trigger.

---

### Component 2: Timing Opportunity Score (30% weight)

**What It Measures**: Technical setup quality and trigger readiness.

**Inputs**:
- Completed weekly structure (support, resistance established)
- Daily trigger state (triggered, confirmed, forming, none)
- Multi-timeframe alignment (aligned, forming, divergent)
- Relative strength and relative volume
- Volatility environment (contraction, expansion)
- Catalyst timing and importance
- Distance to invalidation

**Output**: 0-100 score representing how good the technical setup is right now.

**Key Rule**: Timing score answers "is this the right moment to enter?" Independent of valuation.

---

### Component 3: Expected Swing Value Score (40% weight)

**What It Measures**: Probability × magnitude × holding period × liquidity × uncertainty.

**Inputs**:
- Calibrated probability (when available from research)
- Expected move magnitude (% upside)
- Expected downside (% loss if wrong)
- Expected holding period to target
- Execution costs and slippage
- Average daily volume and bid-ask spread
- Analyst confidence and uncertainty

**Output**: 0-100 score representing the risk-adjusted expected value of the move.

**Key Rule**: Swing value answers "what's the real money at stake if this plays out?"

---

## Intrinsic Opportunity vs Timing Opportunity

### Why They're Separate

A company can be:
1. **Deeply undervalued but poorly timed** → HIGH_PRIORITY_WAITING_FOR_TRIGGER (intrinsic good, timing poor)
2. **Fairly valued with perfect technical trigger** → WATCHLIST or SPECULATIVE (intrinsic moderate, timing excellent)
3. **Expensive with broken structure** → AVOID (intrinsic bad, timing bad)
4. **Undervalued with excellent trigger** → HIGH_PRIORITY_TRIGGERED (intrinsic good, timing good)

### Hard Cap: Poor Timing Cannot Force Entry

If intrinsic is strong (≥ 60) but timing is poor (< 45):
- Overall ranking reduced by 15 points
- State classified as **HIGH_PRIORITY_WAITING_FOR_TRIGGER**
- Research indicates: "Wait for technical confirmation before entry"

**This prevents premature entries into undervalued companies before the technical setup completes.**

---

## Full-Capital-Stack Considerations

The Intrinsic Opportunity Score explicitly incorporates complete capital structure analysis:

### Debt Maturity Profile

```
Maturity Condition         Score   Liquidity Runway
─────────────────────────  ─────   ────────────────
WELL_FUNDED                95      3+ years
MANAGEABLE                 80      2-3 years
ADEQUATE                   60      1-2 years
REFINANCING_REQUIRED       50      < 1 year, refi needed
HIGH_RISK                  25      < 6 months, weak coverage
DISTRESSED                 5       < 3 months OR coverage < 1.5x
```

### Valuation Component (50% of intrinsic)

Measures gap between current market price and fair value across bear/base/bull scenarios.

### Capital Structure Component (50% of intrinsic)

Measures risk of forced liquidation, dilution, or missed opportunity due to capital constraints:
- Interest coverage ratios
- Debt covenants
- Refinancing timeline
- Liquidity buffers
- Senior claim priority

### Full-Stack Impact Example

```
Scenario: Stock trading at 5x book, 60% below DCF

Valuation alone: Would score 90+ (deep value)

But if capital structure is:
- Debt due in 3 months
- Negative operating cash flow
- Covenant violation risk
- Interest coverage < 1.5x

Then intrinsic score capped at: ~25 (DISTRESSED)

Overall ranking cannot exceed: 30 points (hard cap)

Even though timing might be perfect and swing magnitude high,
the severe capital distress prevents actionable ranking.
```

---

## Expected Swing Value Calculation

### Formula

```
Swing Value = (Prob × Magnitude × Time Factor × Liquidity) - Uncertainty Penalty
```

### Components in Detail

**Probability** (if available)
- Calibrated from research: Use directly (75%, 60%, 50%, etc.)
- If uncalibrated or missing: Mark UNCALIBRATED, apply -15 point penalty, use 50 (neutral)
- **Critical**: Do not fabricate probability

**Magnitude**
- Expected upside percentage from current market price
- Weighted against expected downside (upside/downside ratio)
- Ratio < 1.5:1 penalized (-20 points)
- Ratio 2.5:1+ not penalized

**Time Factor**
- Optimal holding: 5-20 trading days (100 points)
- Longer holds (20-60 days): declining value (60-80 points)
- Day trades (< 2 days): reduced value (30-50 points)

**Liquidity**
- Average daily volume / position size
- Bid-ask spread
- Expected execution slippage
- Volume < 2x position size severely penalizes

**Uncertainty Penalty**
- Analyst confidence level
- Data availability
- Model reliability
- Typically -5 to -20 points

---

## Validation Gates

### Unvalidated Evidence = Zero Influence

Any evidence not explicitly marked as validated receives zero contribution to the ranking:

**Unvalidated Probability**
- If probability source is unknown or not verified
- Swing value reduced by 15 points
- Marked UNCALIBRATED

**Unconfirmed Catalyst**
- If catalyst timing is not confirmed
- Catalyst contribution set to zero
- Marked as "potential but unconfirmed"

**Unvalidated Capital Structure**
- If debt profile not from latest 10-K/10-Q
- Uses conservative maturity estimate
- Triggers REQUIRED_CONFIRMATION flag

**Unconfirmed Technical Trigger**
- If daily close not yet above trigger
- Classified as FORMING not TRIGGERED
- Even if all other conditions met

### Missing Information ≠ Favorable

Missing data is **never** treated as positive:

- No EBITDA available → Conservative valuation multiplier used
- No recent volume data → Assumes illiquidity (low liquidity score)
- No catalyst timeline → Cannot factor catalyst contribution
- No probability data → Score as UNCALIBRATED

---

## Severe-Risk Caps

Hard caps prevent single-component override of safety considerations:

### Distress Cap

**Rule**: If intrinsic opportunity score < 20 (severe capital distress), overall ranking capped at 30 points maximum.

**Purpose**: Prevents technically perfect setup + high magnitude from forcing entry into companies with imminent solvency risk.

**Trigger**:
- Debt maturity < 3 months, OR
- Interest coverage < 1.5x with declining cash, OR
- Liquidity runway < 60 days

**Effect**: Even if timing = 100, magnitude = 50%, probability = 75%, overall ranking cannot exceed 30.

**Rationale**: Capital collapse is faster than swing thesis development.

### Poor Timing Penalty

**Rule**: If timing < 45 but intrinsic ≥ 60, reduce swing value by 15 points.

**Purpose**: Signals "wait for better entry" rather than forcing premature entry into undervalued companies.

**Trigger**:
- Technical setup incomplete (weekly structure not confirmed)
- Daily trigger not yet activated
- Multi-timeframe divergence present

**State**: Classified as HIGH_PRIORITY_WAITING_FOR_TRIGGER

**Rationale**: Thesis is sound but entry timing should be deferred.

### Uncalibrated Probability Penalty

**Rule**: If probability is uncalibrated or missing, swing value reduced by 15 points.

**Purpose**: Prevents fabricated probability from inflating opportunity ranking.

**Trigger**:
- Probability not provided by research
- Probability source unknown or not verified
- Data insufficient to calibrate

**Marking**: Result marked UNCALIBRATED

**Rationale**: Confidence must be earned from evidence, not assumed.

---

## Ranking vs Allocation vs Execution

### Ranking Engine (This System)

**Produces**:
- Deterministic ranked list of opportunities
- Evidence lineage for each ranking
- Research classification (8 states)
- Warnings and missing confirmations

**Does NOT**:
- Allocate portfolio weight
- Determine position size
- Create trading signals
- Generate orders
- Approve risk

**Example Output**:
```
Rank 1: ACME-2024-Q3 (Score: 72.5)
  State: HIGH_PRIORITY_TRIGGERED
  Positive: Undervalued + completed weekly + daily trigger confirmed
  Warnings: Refinancing due Q4 2026; confirm latest guidance
  Required: Confirm support level hasn't been broken

Rank 2: BETA-REFI-2025 (Score: 68.3)
  State: HIGH_PRIORITY_WAITING_FOR_TRIGGER
  Positive: Deep value + attractive thesis
  Negative: Timing setup incomplete; needs weekly confirmation
  Required: Monitor weekly structure formation
```

### Allocation Engine (Separate System)

Takes ranking output and:
- Decides position sizes
- Balances portfolio exposure
- Manages correlation risk
- Adjusts for risk budget
- Produces allocation target

**Input**: Ranked opportunities  
**Output**: Portfolio weights (%)

### Execution System (Separate System)

Takes allocation target and:
- Creates orders
- Manages entry timing
- Handles partial fills
- Monitors execution quality
- Updates position tracking

**Input**: Allocation target  
**Output**: Orders, fills, positions

### Clear Separation

```
Ranking Engine → (research output, no positions)
    ↓
Portfolio Optimization → (weights, no orders)
    ↓
Execution Engine → (orders, fills, positions)
```

Each system is independent. Ranking engine never:
- Assumes position sizes
- Allocates capital percentages
- Creates orders
- Modifies portfolio state
- Calls broker APIs

---

## Known Limitations

### By Design (Explicit Scope Boundaries)

1. **Does not allocate portfolio weight**
   - Returns ranking only
   - Separate allocation system assigns weights

2. **Does not create signals or orders**
   - Returns research classification only
   - Separate execution system creates orders

3. **Does not call broker APIs**
   - Read-only with respect to market data
   - No integration with brokerage systems

4. **Does not mutate portfolio state**
   - Input: Canonical Opportunity objects (immutable)
   - Output: Research ranking (no side effects)

5. **Does not integrate with Risk Engine**
   - Separate system for risk approval
   - Ranking provides evidence only

6. **Does not approve governance decisions**
   - Separate system for governance gates
   - Ranking provides analysis only

### Practical Limitations (Current Implementation)

7. **No position overlap detection**
   - Doesn't account for existing positions
   - Doesn't rank relative to portfolio

8. **No correlation bucketing**
   - Doesn't flag highly correlated opportunities
   - Separate system handles portfolio correlation

9. **Requires pre-calculated scenarios**
   - Scenarios must be provided externally
   - Does not generate valuation scenarios

10. **Requires calibrated probability from research**
    - Does not calculate probability
    - Marks as UNCALIBRATED if not provided

11. **Catalyst timing must be known**
    - Does not predict catalyst dates
    - Must be populated in Opportunity.known_catalysts

12. **Technical setup must be available**
    - Requires daily/weekly bar data
    - Does not fetch market data independently

13. **Capital structure data must be current**
    - Relies on most recent 10-K/10-Q
    - Does not infer debt changes

14. **No machine learning scoring**
    - Deterministic rules only
    - No neural networks or learned weights

15. **No predictive analysis**
    - All inputs are historical or known
    - Does not forecast future market conditions

### Input Quality Assumptions

16. **Assumes Opportunity data is accurate**
    - Does not validate underlying data
    - Relies on source system accuracy

17. **Assumes bar data is complete**
    - Does not fill gaps or adjust for splits
    - Requires clean price history

18. **Assumes sector/market regime is current**
    - Uses provided regime classification
    - Does not re-classify regime

---

## Integration Example

```python
from alpha_velocity.opportunity_ranking import RankingEngine
from alpha_velocity.opportunity import assemble_opportunity

# 1. Initialize engine
engine = RankingEngine()

# 2. Create or retrieve Opportunity objects
opportunities = [
    assemble_opportunity(symbol='ACME', data={...}),
    assemble_opportunity(symbol='BETA', data={...}),
    # ... more opportunities
]

# 3. Rank them
ranking_result = engine.rank(
    opportunities=opportunities,
    universe_name='Active Watch List',
    observation_time=datetime.now(timezone.utc),
)

# 4. Use results for research
for ranked_opp in ranking_result.ranked_opportunities:
    print(f"{ranked_opp.rank}. {ranked_opp.opportunity_id}")
    print(f"   Score: {ranked_opp.overall_research_score:.1f}")
    print(f"   State: {ranked_opp.ranking_state}")
    
    if ranked_opp.ranking_state == "HIGH_PRIORITY_TRIGGERED":
        print("   → Pass to Portfolio Optimizer")
    elif ranked_opp.ranking_state == "HIGH_PRIORITY_WAITING_FOR_TRIGGER":
        print("   → Add to watchlist, wait for trigger")
    else:
        print(f"   → {ranked_opp.ranking_state}")

# 5. Export for downstream systems
json_report = ranking_result.to_json()
csv_report = ranking_result.to_csv()
```

---

## Test Coverage

Focused tests validate:

✅ Deterministic ranking (identical results on repeated calls)  
✅ Highest expected swing value wins (ranks first)  
✅ Undervalued but no trigger → HIGH_PRIORITY_WAITING  
✅ Technical strength cannot override distress cap  
✅ Unvalidated evidence has zero influence  
✅ Missing data not treated as favorable  
✅ Uncalibrated probabilities not fabricated  
✅ Opportunity cost comparison  
✅ Deterministic serialization (same JSON every time)  
✅ No broker calls (pure research)  
✅ No order creation (ranking only)  
✅ No portfolio mutation (read-only output)  

Run tests:
```bash
.\.venv\Scripts\python.exe -m pytest tests/test_opportunity_ranking.py -q
```

---

## Version History

### v1.0.0 (2026-07-15)
- Initial production release
- Three-component scoring (intrinsic, timing, swing value)
- Eight ranking states
- Hard caps for distress and poor timing
- Uncalibrated probability handling
- Deterministic serialization
- Complete evidence lineage

---

## References

**Production Code**:
- `alpha_velocity/opportunity_ranking/__init__.py` — Package exports
- `alpha_velocity/opportunity_ranking/models.py` — Data structures
- `alpha_velocity/opportunity_ranking/scoring.py` — Scoring rules
- `alpha_velocity/opportunity_ranking/ranker.py` — Main engine

**Tests**:
- `tests/test_opportunity_ranking.py` — Comprehensive test suite

**Documentation**:
- `docs/OPPORTUNITY_RANKING.md` — This file
