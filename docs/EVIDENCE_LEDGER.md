# Evidence Ledger v1: Immutable Point-in-Time Records of Research, Decisions, and Outcomes

**Purpose**: Record and grade what Alpha Velocity knew at each decision point, how each research lens contributed, and whether those decisions performed well.

**Status**: Complete, Research-Only, Append-Only, No Automatic Promotion

---

## Table of Contents

1. [Why the Evidence Ledger Exists](#why)
2. [Core Architecture](#architecture)
3. [Append-Only Behavior](#append-only)
4. [Point-in-Time Integrity](#point-in-time)
5. [Revisions and Supersession](#revisions)
6. [Shadow Research Integration](#shadow-research)
7. [Outcome Grading](#outcome-grading)
8. [Forecast Grading](#forecast-grading)
9. [Evidence-Stream Scorecards](#scorecards)
10. [Validation and Promotion Separation](#validation)
11. [Backtester and Paper Compatibility](#backtester)
12. [Known Limitations](#limitations)

---

## <a id="why"></a>Why the Evidence Ledger Exists

Alpha Velocity makes research-driven decisions in three stages:

1. **Market Intelligence** → Identifies opportunities
2. **Opportunity Ranking** → Scores and ranks opportunities
3. **Capital Intelligence** → Proposes allocations
4. **Risk & Governance** → Approves or rejects
5. **Execution** → Places orders (optional, separate system)

The Evidence Ledger records the **decision-making context** at stages 1-5, then **grades the outcomes** later to understand:

- **What research evidence existed at each point in time?**
- **Which evidence lenses contributed to each decision?**
- **How confident was each evidence stream?**
- **Did the proposed allocation make sense given the evidence?**
- **What was the actual outcome?**
- **Which evidence streams helped? Which hurt?**
- **Should unvalidated research move from shadow status to production?**

This is NOT about execution or performance chasing. It is about **honesty in the research process**: recording what we knew, when we knew it, and whether our research frameworks are actually helpful.

---

## <a id="architecture"></a>Core Architecture

```
Market Intelligence Engine
    ↓
Market Scan Results
    ↓
┌────────────────────────────────────────────────┐
│  Evidence Ledger Record (immutable snapshot)   │
├────────────────────────────────────────────────┤
│ • observation_time (when we observed)           │
│ • created_at (when we recorded it)              │
│ • all research evidence available at time       │
│ • ranking decision state at time                │
│ • allocation proposal at time                   │
│ • risk/governance status at time                │
│ • influence controls (shadow/validated)         │
└────────────────────────────────────────────────┘
    ↓ (stored in append-only ledger)
    ↓
    ├─ Record 1 (observation 2024-01-15 16:30)
    ├─ Record 2 (observation 2024-01-16 16:30)
    ├─ Revision 1.1 (supersedes Record 1)
    └─ Record 3 (observation 2024-01-17 16:30)
    ↓
┌────────────────────────────────────────────────┐
│  Later: Outcome Grading                        │
├────────────────────────────────────────────────┤
│ • Forward return (%)                           │
│ • Max favorable/adverse excursion               │
│ • Invalidation breach                          │
│ • Catalyst occurrence                          │
│ • Direction correctness                        │
└────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────┐
│  Evidence-Stream Scorecards                    │
├────────────────────────────────────────────────┤
│ • Technical: 100 samples, 95% graded           │
│   - Directional accuracy: 58%                  │
│   - Recommendation: REMAIN_SHADOW              │
│                                                │
│ • Expectations: 50 samples, 40% graded         │
│   - Directional accuracy: 52%                  │
│   - Recommendation: ELIGIBLE_FOR_VALIDATION    │
│                                                │
│ • Catalyst: 75 samples, 70% graded             │
│   - Directional accuracy: 67%                  │
│   - Recommendation: ELIGIBLE_FOR_VALIDATION    │
└────────────────────────────────────────────────┘
    ↓
    Scorecards inform validation decisions
    (manual review only; no automatic promotion)
```

---

## <a id="append-only"></a>Append-Only Behavior

The ledger is **immutable append-only**. Once a record is created, it cannot be overwritten or silently changed.

### Immutability Guarantee

```python
# Record created
record = EvidenceLedgerRecord(
    record_id="LEG-20240115-163000-abc123",
    observation_time=datetime(...),
    symbol="AAPL",
    overall_research_score=82.5,
)

ledger.add_record(record)

# Later, if data quality issue discovered, you CANNOT do this:
#   ledger.update_record(record_id, {"overall_research_score": 75.0})
# That would destroy audit trail

# Instead, you CREATE A NEW RECORD with supersession link:
revised = create_revision_record(
    original_record=record,
    revision_reason="Data quality correction: volatility data was stale",
    changes={"overall_research_score": 75.0},
)

ledger.add_record(revised)

# Now the ledger shows BOTH records:
# - Original (LEG-20240115-163000-abc123)
# - Revision that supersedes it
# - Full audit trail of why the change was made
```

### Query Behavior

By default, queries **exclude superseded records**:

```python
# Default: get only current version
current = ledger.get_records_by_symbol("AAPL", include_superseded=False)
# Returns only the REVISED record

# For audit, get full history
history = ledger.get_records_by_symbol("AAPL", include_superseded=True)
# Returns both original and revision, showing chain
```

---

## <a id="point-in-time"></a>Point-in-Time Integrity

Every evidence item has an **available_at** timestamp that records when that data became available to Alpha Velocity. The ledger enforces:

```
available_at <= observation_time
```

This prevents lookahead bias.

### What This Prevents

❌ **Future filings** (10-K not filed yet)  
❌ **Later analyst revisions** (forecast changed after decision)  
❌ **Future outcomes** (knowing a catalyst succeeded)  
❌ **Future earnings data** (Q4 results not announced yet)  
❌ **Later restated data** (company restated earnings after decision)  
❌ **Future catalyst results** (election result before voting)  
❌ **Later weekly bars** (using data from after observation date)

### What This Allows

✅ **Scheduled events** (known earnings date, known fed decision date) recorded as **scheduled**, not as known outcomes  
✅ **Analyst forecasts** (as of 2024-01-15) can be recorded  
✅ **Technical snapshots** (weekly bars through 2024-01-14) captured  
✅ **Valuation metrics** (trailing 12-month earnings)  
✅ **Known catalysts** (publicly announced events)

### Example: Earnings Report

```python
# Scheduled earnings announced before 2024-01-15 16:30
catalyst_evidence = CatalystEvidence(
    observation_time=datetime(2024, 1, 15, 16, 30, tzinfo=utc),
    available_at=datetime(2024, 1, 10, 9, 30, tzinfo=utc),  # When announced
    
    next_known_event_time=datetime(2024, 1, 25, 16, 30, tzinfo=utc),
    catalyst_magnitude_estimate="HIGH",
    
    # CANNOT fill in actual results until after 2024-01-25
    # Even if you know the results exist as of 2024-01-25 16:30
)

# Later, you can create a NEW ledger record with actual results:
# But that record would have observation_time=2024-01-25 16:30 or later

# The original record (2024-01-15) preserved forever
# showing what you knew at that time
```

---

## <a id="revisions"></a>Revisions and Supersession

When data is corrected or evidence is updated, create a revision record.

### Supersession Record Structure

Each revision contains:

```python
supersession = SupVersionRecord(
    record_id="LEG-20240115-163001-def456",
    supersedes_record_id="LEG-20240115-163000-abc123",
    record_type="REVISION",
    revision_reason="Data quality correction: technical data had 1-day lag",
    revised_at=datetime(2024, 1, 16, 10, 30, tzinfo=utc),
)
```

### Revision Examples

**Example 1: Technical Data Correction**
```python
revised = create_revision_record(
    original_record,
    "Data lag correction: weekly bars actually through 2024-01-12, not 2024-01-14",
    {
        "research_evidence": RevisedTechnicalEvidence(
            available_at=datetime(2024, 1, 12, 16, 30, tzinfo=utc),
            # Now correctly reflects available_at point-in-time
        ),
    },
)
```

**Example 2: Ranking Score Correction**
```python
revised = create_revision_record(
    original_record,
    "Ranking model bug fix: calibration factor was inverted",
    {
        "decision_state": RevisedDecisionState(
            ranking=RankingDecisionState(
                overall_research_score=75.0,  # Corrected from 82.5
            ),
        ),
    },
)
```

### Querying Supersession Chains

```python
# Get full chain of revisions for a record
chain = ledger.get_supersession_chain("LEG-20240115-163000-abc123")
# Returns: [original, revision1, revision2, ...]
# Showing complete audit trail

# Get only the latest version (default)
current = ledger.get_record("LEG-20240115-163000-abc123", include_superseded=False)
# Returns the most recent version
```

---

## <a id="shadow-research"></a>Shadow Research Integration

Unvalidated evidence streams (like Expectations & Mispricing Research) are recorded but have **zero influence** until validated.

### Shadow Controls

Each record specifies influence weights:

```python
influence_weights = InfluenceWeights(
    # Validated streams (full influence)
    technical_ranking_influence=1.0,
    technical_allocation_influence=1.0,
    
    catalyst_ranking_influence=1.0,
    catalyst_allocation_influence=1.0,
    
    # Shadow streams (zero influence)
    expectations_ranking_influence=0.0,      # NOT used in ranking
    expectations_allocation_influence=0.0,   # NOT used in allocation
    expectations_validation_status="SHADOW",
    
    # Partially-validated
    sentiment_ranking_influence=0.5,         # 50% weight
    sentiment_allocation_influence=0.0,      # Not used in allocation yet
)
```

### Key Properties

1. **Shadow evidence is still recorded** in the ledger (not hidden)
2. **Shadow evidence has zero ranking influence** (score 82.5 → 82.5, not changed)
3. **Shadow evidence has zero allocation influence** (weight 5% → 5%, not changed)
4. **Shadow evidence cannot be promoted automatically** (only by manual review)
5. **Shadow evidence is graded** (outcomes tracked, performance monitored)
6. **Shadow evidence gets scorecards** (accuracy measured separately)

### Workflow for Promoting Shadow Research

```python
# 1. Record ledger entries with expectations as SHADOW (influence = 0)
record = EvidenceLedgerRecord(
    research_evidence=ResearchEvidence(
        expectations_mispricing=ExpectationsAndMispricingEvidence(...),
    ),
    influence_weights=InfluenceWeights(
        expectations_ranking_influence=0.0,
        expectations_validation_status="SHADOW",
    ),
)

# 2. Collect outcomes and grade expectations
grader = OutcomeGrader(price_history)
grades = [grader.grade_record(record, horizon) for record in all_records]

# 3. Build scorecard for expectations
builder = EvidenceStreamScorecardBuilder()
scorecard = builder.build_scorecard("EXPECTATIONS", records_with_outcomes)

scorecard.directional_accuracy_pct  # 67%
scorecard.incremental_value_vs_baseline_pct  # +8%
scorecard.recommendation  # "ELIGIBLE_FOR_VALIDATION"

# 4. Manual review (human decision)
# "Results look good. Promote from SHADOW to CALIBRATED?"
# "Yes, as of 2024-02-01, promote with 50% influence initially"

# 5. New records going forward use elevated influence
new_record = EvidenceLedgerRecord(
    influence_weights=InfluenceWeights(
        expectations_ranking_influence=0.5,  # Elevated from 0
        expectations_validation_status="CALIBRATED",
    ),
)
```

---

## <a id="outcome-grading"></a>Outcome Grading

After sufficient time has passed, grade records against actual prices and events.

### Grading Horizons

```python
horizons = [
    OutcomeGradeHorizon.ONE_DAY,
    OutcomeGradeHorizon.FIVE_DAYS,
    OutcomeGradeHorizon.TEN_DAYS,
    OutcomeGradeHorizon.TWENTY_DAYS,
    OutcomeGradeHorizon.CATALYST_WINDOW,
    OutcomeGradeHorizon.INTENDED_HOLDING,
]
```

### Grading Metrics

For each horizon, calculate:

```python
grade = OutcomeGrade(
    horizon=OutcomeGradeHorizon.FIVE_DAYS,
    as_of_time=datetime(2024, 1, 20, 16, 30),
    days_elapsed=5,
    
    # Returns
    forward_return_pct=+6.5,  # price target achieved?
    
    # Excursions
    max_favorable_excursion_pct=+12.0,   # best case touched?
    max_adverse_excursion_pct=-8.0,      # worst case touched?
    
    # Direction
    direction_correct=True,  # Positive return?
    magnitude_error_pct=1.5,  # How far off prediction?
    
    # Technical
    invalidation_breach=False,  # Did price hit invalidation level?
    
    # Catalyst
    catalyst_occurred=True,  # Did scheduled event happen?
    
    # Timing
    timing_error_days=0,  # How far off expected timing?
)
```

### Data Integrity Principle

**Do not fabricate data**:

- No fill prices invented
- No price data fabricated
- If price history incomplete, grade returns `None`
- If catalyst not occurred yet, leave `catalyst_occurred=None`
- If forecast not available, leave grades as `None`

---

## <a id="forecast-grading"></a>Forecast Grading

For Expectations & Mispricing Research, grade forecasts against realized metrics when available.

### Forecast Metrics to Grade

```python
forecast_grade = ForecastGrade(
    security_id="sec-1",
    symbol="AAPL",
    forecast_date=datetime(2024, 1, 15, 16, 30),
    grading_date=datetime(2024, 2, 5, 16, 30),  # After Q4 earnings
    
    # Realized (actual from filings)
    realized_revenue=383_285_000_000.0,
    realized_ebitda=129_000_000_000.0,
    realized_margin=0.34,
    realized_fcf=110_000_000_000.0,
    realized_eps=6.05,
    
    # Forecast (predicted by model)
    forecast_revenue=385_000_000_000.0,
    forecast_ebitda=130_000_000_000.0,
    forecast_margin=0.34,
    forecast_fcf=112_000_000_000.0,
    forecast_eps=6.10,
    
    # Errors (calculated)
    revenue_error_pct=0.45,
    ebitda_error_pct=0.77,
    margin_error_bps=0,
    fcf_error_pct=1.82,
    eps_error_pct=0.83,
    
    # Consensus gap
    consensus_gap_direction_correct=True,
    consensus_gap_magnitude_error_pct=1.2,
    
    # Scenario analysis
    actual_scenario_match="BASE_CASE",
    scenario_probability_accuracy=0.92,
    
    # Bridge accuracy
    normalized_earnings_bridge_accuracy=0.97,
    industry_assumption_accuracy=0.89,
)
```

### Key Point: No Fabrication

- Only grade when **actual metrics are available** (filings published, earnings announced)
- If earnings not yet released, `grading_date` is `None`
- If metrics missing, leave as `None`
- Never invent "expected" values

---

## <a id="scorecards"></a>Evidence-Stream Scorecards

Aggregate performance by evidence stream to evaluate research quality.

### Scorecard Structure

```python
scorecard = EvidenceStreamScorecard(
    stream_name="TECHNICAL",
    
    # Coverage
    sample_count=128,          # Records using technical evidence
    graded_count=105,          # Records with outcomes
    availability_coverage_pct=82.0,
    
    # Performance
    directional_accuracy_pct=58.5,  # % of graded records with correct direction
    calibration_score=0.72,         # Are predictions reasonably calibrated?
    average_forward_return_by_score_bucket={
        "SCORE_80_100": +4.2,  # When technical score 80-100, avg return +4.2%
        "SCORE_60_80": +1.8,
        "SCORE_40_60": -0.5,
        "SCORE_0_40": -2.1,
    },
    
    # Value
    incremental_value_vs_baseline_pct=+2.3,  # vs random allocation
    
    # Quality
    failure_modes=[
        "INVALIDATION_BREACH",  # % of records hit invalidation level
        "HIGH_ADVERSE_EXCURSION",  # % with >20% drawdown
    ],
    regime_sensitivity="MEDIUM",  # Sensitive to market regimes?
    
    # Recommendation
    recommendation="REMAIN_SHADOW",  # Or ELIGIBLE_FOR_VALIDATION, RETIRE, QUARANTINE
    confidence_in_recommendation=0.85,
    reasoning="Directional accuracy 58.5% is below 60% threshold for promotion",
)
```

### Recommendation Logic

| Condition | Recommendation |
|-----------|----------------|
| < 40% directional accuracy | RETIRE |
| 40-50% directional accuracy | QUARANTINE |
| 50-60% directional accuracy | REMAIN_SHADOW |
| > 60% accuracy + > 3% incremental value | ELIGIBLE_FOR_VALIDATION |
| High failure rate | QUARANTINE |
| Insufficient data | INSUFFICIENT_DATA |

### No Automatic Promotion

**Important**: Scorecards are **advisory only**. They DO NOT automatically:

- Promote evidence streams
- Change influence weights
- Retire evidence
- Change validation status

All promotion/retirement decisions are **manual review** by humans.

---

## <a id="validation"></a>Validation and Promotion Separation

The Evidence Ledger **separates validation testing from actual usage**. This prevents:

- P-hacking (testing until something works)
- Overfitting to historical data
- Blind overconfidence in validated research

### The Three-Layer System

```
Layer 1: PRODUCTION (Ranked, Allocated)
├─ Technical (CALIBRATED)
├─ Catalyst (CALIBRATED)
├─ Valuation (CALIBRATED)
└─ Industry/Macro (CALIBRATED)

Layer 2: SHADOW (Recorded, Graded, Scored, but Zero Influence)
├─ Expectations & Mispricing (SHADOW)
└─ Sentiment (SHADOW)

Layer 3: QUARANTINE (Flagged for Investigation)
└─ (When scorecard recommends QUARANTINE)
```

### Workflow

```
1. Evidence is collected
   ↓
2. Used with current influence weights
   (shadow research has weight = 0)
   ↓
3. Decisions recorded (ranking, allocation)
   ↓
4. Time passes, outcomes realized
   ↓
5. Outcome grades calculated
   ↓
6. Scorecards generated
   ↓
7. Human review of scorecards
   ↓
8. IF recommend ELIGIBLE_FOR_VALIDATION:
   → Manual validation tests (independent data)
   → If validation passes, create new records with elevated influence
   → Future records use new influence weights
   → NEVER retroactively change past influence weights
```

### Immutability Protects Against Bias

By enforcing append-only records:

- We cannot retroactively adjust past decisions to look better
- We cannot hide unfavorable outcomes
- We cannot selectively promote evidence that worked
- Full audit trail is permanent

---

## <a id="backtester"></a>Backtester and Paper Compatibility

The Evidence Ledger provides **pure data interfaces** for backtesting and paper trading.

### Backtester Integration

```python
# Backtester processes market data
backtester = EventDrivenBacktest()

for market_event in market_data:
    # Get current ledger records available at this time
    current_records = ledger.get_records_by_date(market_event.date)
    
    # Each record contains:
    # - Ranking decisions
    # - Allocation proposals
    # - Risk/governance status
    # - Evidence used (with influence weights)
    
    # Backtester can replay:
    # 1. What did we know at this time?
    # 2. What did we decide?
    # 3. What happened?
    # 4. Compare decision quality over time
    
    for record in current_records:
        # Record contains deterministic decision data
        allocation = record.decision_state.allocation
        
        # Backtester applies this decision
        backtester.apply_proposal(
            proposal_id=allocation.proposal_id,
            weight=allocation.proposed_allocation_weight,
        )

# Later grade outcomes
for record in ledger.get_all_records():
    grade = outcome_grader.grade_record(
        record,
        OutcomeGradeHorizon.TWENTY_DAYS,
    )
    record_with_grade = (record, grade)
```

### Paper Trading Integration

```python
# Paper trading runs live but doesn't execute
paper_trader = PaperTradingSimulator()

# For each market day, load today's ledger records
records_today = ledger.get_records_by_date(today)

# Paper trader can:
# 1. Show what allocation would be proposed
# 2. Calculate what execution would cost
# 3. Track simulated performance
# 4. Compare to actual portfolio (if live)
# 5. Later grade outcomes to measure research quality

for record in records_today:
    paper_trader.simulate_allocation(record)
```

### Key Property: No Autonomous Execution

- Ledger produces **proposals**, not orders
- Ledger records **decisions**, not executions
- Ledger never calls broker APIs
- Backtester and paper trader are **pure simulation**
- execution_authorized is **always False**

---

## <a id="limitations"></a>Known Limitations

### Current Implementation (v1)

**By Design (Not Bugs)**:

1. **No automatic evidence promotion** - Scorecards are advisory only; promotion is manual
2. **No optimization** - Ledger records decisions, doesn't optimize parameters
3. **No scenario analysis** - Only grades actual outcomes, not counterfactuals
4. **No walk-forward validation** - Scorecards are descriptive, not predictive
5. **No live execution** - execution_authorized always False; separate system required
6. **No broker integration** - Ledger is data-only
7. **No autonomous paper trading** - Paper trading is simulation, not automation

**Implementation Stubs (Needs Future Work)**:

8. **Forecast grading incomplete** - Structured but not fully integrated with expectations system
9. **Regime sensitivity calculation basic** - Simple heuristic, not sophisticated analysis
10. **Failure mode classification limited** - Only captures obvious invalidations
11. **Scenario probability grading placeholder** - Framework present, logic basic
12. **Custom horizon support incomplete** - Honors CUSTOM horizon, but limited implementation
13. **Batch grading performance not optimized** - Works correctly, may be slow on large datasets

**Intentional Boundaries**:

14. **No parameter optimization** - This is research ledger, not backtester optimizer
15. **No profitability claims** - Ledger measures research quality, not trading returns
16. **No risk weighting** - Risk/governance engines handle risk; ledger just records
17. **No governance override** - Governance review is independent; ledger doesn't pre-approve
18. **No weakening of controls** - Constraints, validations, and safety checks always enforced

### Data Requirements

**Must Have**:
- Timezone-aware datetime (raises ValueError if naive)
- Point-in-time data (available_at ≤ observation_time)
- Price history for outcome grading (no interpolation or fabrication)

**Nice to Have**:
- Complete price history (handles gaps gracefully with None returns)
- Analyst forecasts (can be empty)
- Catalyst dates (handled as None if not available)

### What This Doesn't Do

- ❌ Execute trades
- ❌ Optimize parameters
- ❌ Make profitability claims
- ❌ Weaken governance
- ❌ Hide unfavorable outcomes
- ❌ Retroactively adjust past decisions
- ❌ Automatically promote evidence
- ❌ Fabricate missing data
- ❌ Override risk controls

### What This Does Do

- ✅ Records what we knew, when we knew it
- ✅ Preserves full audit trail of decisions
- ✅ Enforces point-in-time integrity
- ✅ Grades research quality honestly
- ✅ Provides scorecards for human review
- ✅ Supports backtesting with accurate historical context
- ✅ Enables paper trading simulation
- ✅ Never mutates past records
- ✅ Tracks revisions and corrections
- ✅ Treats shadow research carefully

---

## Architecture & Integration

**The Evidence Ledger sits AFTER all research systems:**

```
Market Intelligence Engine (produces opportunities)
                    ↓
Opportunity Ranking Engine (ranks opportunities)
                    ↓
Capital Intelligence Optimizer (proposes allocations)
                    ↓
Risk Engine (approves/rejects independently)
                    ↓
Governance Engine (checks compliance independently)
                    ↓
Evidence Ledger (RECORDS all of the above)
                    ↓
Outcome Grader (grades after time passes)
                    ↓
Scorecard Builder (aggregates performance by lens)
                    ↓
Human Review (decides on promotion/retirement)
```

**The Evidence Ledger does NOT:**
- Call market intelligence engine
- Call ranking engine
- Call capital optimizer
- Call risk or governance engines
- Create orders or execute trades
- Make investment decisions

**The Evidence Ledger DOES:**
- Record every decision made by upstream systems
- Maintain immutable audit trail
- Grade outcomes vs predictions
- Measure research quality
- Support backtesting
- Support paper trading
- Provide scorecard recommendations
- Enable validation decisions

---

## Summary

The Evidence Ledger is a **research honesty system**:

- **Immutable**: Cannot hide or cover up decisions
- **Point-in-time**: Cannot use future data
- **Evidence-tracked**: Records what informed each decision
- **Outcome-graded**: Measures whether research worked
- **Shadow-aware**: Keeps unvalidated research visible but separate
- **No-promotion-automatic**: Humans decide on validation
- **Backtester-compatible**: Pure data for simulations
- **Risk-preserving**: Never weakens governance

It doesn't execute trades, optimize parameters, or make profitability claims. It records and grades research quality so we can understand whether our evidence streams actually help.
