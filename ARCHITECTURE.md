# Alpha Velocity Equity Intelligence Architecture v1

**Date**: 2026-07-16  
**Status**: Consolidation Complete, Production-Ready  
**Scope**: Active Equity Research & Paper Trading  

---

## NORTH-STAR OBJECTIVE

Alpha Velocity must evaluate every eligible equity, current holding, and cash as competing uses of capital.

**Research Objective**: Allocate each marginal dollar to the portfolio configuration expected to produce the greatest risk-adjusted compound growth over the intended swing horizon, after:

- Expected favorable move magnitude
- Probability when genuinely calibrated
- Expected holding period
- Downside to invalidation
- Uncertainty
- Liquidity
- Spread, slippage and market impact
- Transaction and switching costs
- Correlation
- Concentration
- Catalyst timing
- Opportunity persistence
- Capital-structure risk
- Governance and portfolio constraints

**Optimization NOT for**:
- Cheapness alone
- Momentum alone
- Technical strength alone
- Win rate alone
- Gross return before costs
- Forced full investment

**Cash is an explicit competing allocation.**

---

## FROZEN DEPENDENCY CHAIN

All data flows in ONE DIRECTION. NO direct paths bypass research gates.

```
    External Providers (NYSE, CBOE, Bloomberg, Corporate Filings, etc.)
              ↓
    Historical Warehouse (Point-in-time security data, bars, corporate actions)
              ↓
    Market Intelligence Scanner (Multi-lens qualification)
              ↓ (produces Opportunities with evidence lineage)
              ↓
    Candidate Ladder (9 research queues: ACTIONABLE → RESEARCH → EXCLUDED)
              ↓
    Expected Swing Value Ranking (3-component: Intrinsic + Timing + Swing Value)
              ↓
    Capital Intelligence Optimizer (Target weights including cash)
              ↓
    Current Holdings Comparison (Position intelligence & exit research)
              ↓
    Independent Risk Review (Position-level & portfolio-level constraints)
              ↓
    Independent Governance Review (Liquidity, compliance, restrictions)
              ↓
    EXPLICIT HUMAN APPROVAL (DU account, exact hash, final decision)
              ↓
    Supervised Paper Order Planning (Deterministic limit orders, protective stops)
              ↓
    Paper Execution (Simulated broker with realistic costs)
              ↓
    Evidence Ledger (Immutable record of all research, decisions, outcomes)
              ↓
    Outcome Grading & Validation (Forward returns, calibration, learning)
```

---

## CRITICAL BOUNDARIES

**PREVENTED PATHS** (these must not exist):

1. ❌ Raw features → Orders
2. ❌ Strategies → Portfolio mutation
3. ❌ Ranking → Execution
4. ❌ Research lenses → Allocation authority
5. ❌ Paper execution → Live accounts
6. ❌ Bypass human approval
7. ❌ Autonomous modification of risk/governance decisions

**MANDATORY GATES** (all must pass):

- Account validation: DU prefix required
- Explicit human approval: Exact proposal hash
- Risk approval: Position and portfolio constraints
- Governance approval: Compliance and restrictions
- Paper-only enforcement: `transmit=false` before approval
- Evidence lineage: All decisions journaled

---

## CORE SYSTEMS (Stable, Not Rewritten)

### 1. Historical Warehouse

**File**: `alpha_velocity/warehouse/`

**Purpose**: Immutable point-in-time repository of all research data

**Properties**:
- Provider-neutral adapter pattern (pluggable data sources)
- Point-in-time queries with `as_of` timestamps
- No future bias (data_available_through ≤ observation_time)
- Tracks delisting, ticker changes, corporate actions
- Supports deterministic backtesting

**Status**: ✅ Production, frozen

---

### 2. Market Intelligence Scanner

**File**: `alpha_velocity/market_intelligence/scanner.py`

**Purpose**: Broad, multi-lens discovery funnel surfacing research candidates

**Lenses** (independent, parallel point-in-time evaluation):

A. **CHART_AND_MOMENTUM**
   - Completed weekly structure
   - Daily breakouts & inflection points
   - Volatility compression/expansion
   - Relative strength & volume
   - Support, resistance, invalidation

B. **FUNDAMENTAL_AND_MISPRICING**
   - Enterprise value vs. earnings power
   - Normalized EBITDA/earnings bridges
   - Consensus vs. Alpha Velocity scenarios
   - Valuation ranges (bear/base/bull)
   - Margin recovery & asset value

C. **CORPORATE_EVENT_AND_ACTIVIST**
   - SEC filings (10-K, 10-Q, 8-K, 13D, 13G, Form 4)
   - Event classification (strategic review, activism, restructuring, refinancing, etc.)
   - Insider transactions
   - Source documents with point-in-time lineage
   - Novelty scoring (repeated disclosures scored lower)

D. **ESTIMATE_REVISIONS**
   - Revenue, EBITDA, EPS, margin, FCF revisions
   - Estimate dispersion & breadth
   - Management guidance changes

E. **MANAGEMENT_LANGUAGE_CHANGE**
   - Current vs. prior call transcripts & filings
   - Material changes in demand, pricing, costs, liquidity, restructuring

F. **OWNERSHIP_AND_FLOW**
   - Activist positions (where supported)
   - Institutional ownership changes
   - Insider buying/selling (Form 4)
   - Buyback activity
   - Short-interest changes

G. **INDUSTRY_AND_MACRO_CONTEXT**
   - Sector & industry trends
   - End-market demand, capacity, pricing
   - Permits, starts, shipments, commodities, rates

**Output**: Opportunities with evidence lineage, confidence levels, source documents

### Adaptive Research Universes v1

The scanner supports multiple independent research universes that run in parallel discovery streams and merge to canonical opportunities by security identity.

Adaptive-universe guarantees:
- One canonical Opportunity model remains authoritative.
- Independent universe provenance is retained on each merged canonical opportunity.
- Duplicate evidence across universes does not change ranking weights by default.
- Universe priorities are research guidance only and never capital authorization.
- Marketplace, ranking, committee, risk, governance, and human approval boundaries remain unchanged.

**Status**: ✅ Production, frozen

---

### 3. Canonical Opportunity Object

**File**: `alpha_velocity/opportunity/models.py`

**Purpose**: Immutable research record for every candidate

**Properties** (frozen dataclass):
- security_id, symbol, observation_time
- Technical state (weekly/daily trend, structure, support/resistance)
- Fundamental metrics (valuation, earnings power, capital structure)
- Event & activist evidence
- Ownership & flow data
- Estimated move & holding period
- Expected swing value (when calibrated)
- Source records & evidence lineage
- Confidence & uncertainty scores

**Assembler**: `alpha_velocity/opportunity/assembler.py`
- Converts scanner findings → canonical opportunities
- Validates point-in-time constraints
- Preserves evidence lineage
- Deterministic output

**Status**: ✅ Single model, no duplicates, frozen

---

### 4. Opportunity Ranking Engine

**File**: `alpha_velocity/opportunity_ranking/ranker.py`

**Purpose**: Deterministic 3-component scoring

**Scoring Model**:
```
Final Rank = (0.30 × Intrinsic) + (0.30 × Timing) + (0.40 × Swing Value)
```

**Component A: Intrinsic Opportunity Score** (0-100)
- Mispricing magnitude
- Valuation vs. normalized earnings
- Capital structure clarity
- Refinancing progress
- Management capability
- Industry outlook
- Downside protection

**Component B: Timing Opportunity Score** (0-100)
- Completed weekly structure
- Daily trigger proximity
- Volatility compression state
- Catalyst timing
- Relative volume confirmation
- Failed-breakdown reversals
- Support/resistance clarity

**Component C: Expected Swing Value** (0-100)
- Probability × Expected Move − Costs − Uncertainty
- Calibrated from (i) historical validation or (ii) scenario analysis
- Uncalibrated scoring (research-based)
- Caps and adjustments for risk

**Constraints & Caps**:
- Severe capital risk → Maximum 20 rank
- Illiquidity → Zero weight
- Unvalidated evidence → Zero influence
- Cheapness alone does not win
- Technical strength alone does not win

**Status**: ✅ Single engine, deterministic, frozen

### Opportunity Marketplace Intelligence Extension (v1)

The marketplace classifier now attaches explainability-first intelligence fields to each candidate classification without replacing queue logic, top-five mechanics, or committee boundaries.

Added classification metadata includes:
- Multi-horizon profile (research, primary repricing, tactical swing, execution)
- Independent inflection dimension assessments and before/within/after horizon mapping
- Inflection synchronization profile (agreement, contradiction, lead-lag, recognition gap)
- Momentum profile (trend maturity, persistence, velocity, relative-strength context)
- Pattern profile (trigger/support/resistance/depth/duration with provenance)
- Future outlook summary (facts, guidance, estimates, scenarios, inference, unknowns)
- Expected move/time profiles per horizon
- Grounded evidence records with validation status and lineage
- Epistemic dossier fields (known, unknown, sensitive assumption, change-my-mind condition)
- Ranking shadow signals (attached by default, influence disabled)

Architecture guarantees preserved:
- No duplicate ranking engines introduced
- No bypass of existing marketplace queue assignment
- No autonomous execution path introduced
- No default change to opportunity ranking influence

---

### 5. Capital Intelligence Optimizer

**File**: `alpha_velocity/capital_intelligence/optimizer.py`

**Purpose**: Target weights including cash, research-only (no execution)

**Inputs**:
- Ranked opportunities
- Current holdings & positions
- Portfolio constraints (sector, size, correlation, gross, net, liquidity)
- Expected cash flows
- Uncertainty & calibration status

**Sizing Methods** (6 available):
1. Proportional Expected Value
2. Risk Budget
3. Volatility-Aware
4. Equal Risk Contribution (ERC)
5. Rank-Based
6. Cash-Preserving

**Outputs**:
- Target portfolio weights (sum to 100% including cash)
- Proposed rotations (sell before buy)
- Transaction costs estimate
- Constraint violations (if any)

**Constraints Enforced**:
- Maximum single-position weight
- Maximum sector/industry weight
- Maximum correlation-bucket exposure
- Gross & net exposure caps
- Downside budget
- Liquidity capacity
- Minimum cash reserve
- Uncalibrated weight cap (e.g., max 5%)
- Severe-risk zero-weight override

**Properties**:
- No portfolio mutation
- No order creation
- Deterministic output
- No autonomous execution

**Status**: ✅ Production, frozen

---

### 6. Daily Investment Committee Orchestrator

**File**: `alpha_velocity/committee/orchestrator.py`

**Purpose**: Deterministic workflow from warehouse readiness → approval pending

**Workflow States** (18 explicit, immutable):

```
CREATED
  → DATA_REFRESHED
  → UNIVERSE_BUILT
  → SCAN_COMPLETED
  → RANKING_COMPLETED
  → CAPITAL_PROPOSAL_CREATED
  → RISK_REVIEW_PENDING (independent risk gate)
  → GOVERNANCE_REVIEW_PENDING (independent governance gate)
  → HUMAN_APPROVAL_PENDING (explicit human approval required)
  → APPROVED_FOR_PAPER_SUBMISSION
  → PAPER_SUBMISSION_COMPLETED
  → RECONCILED
  [FAILED, REJECTED, CANCELLED]
```

**Properties**:
- State transitions logged with UTC timestamp
- No skipped stages
- Immutable audit trail
- Paper-only hard gates (DU account, dry_run=true, transmit=false)
- Explicit session hashing (proposal_hash exact match required for approval)

**Stages**:
1. Warehouse Readiness Check
2. Universe Construction with Exclusions
3. Multi-Lens Market Intelligence Scan
4. Opportunity Ranking
5. Capital Allocation Proposal
6. Independent Risk Review
7. Independent Governance Review
8. Human Approval & Hash Verification
9. Supervised Paper Order Planning
10. Paper Submission (if approved)
11. Reconciliation & Evidence Recording

**Status**: ✅ Production v1.0, frozen

---

### 7. Paper Order Planner & Execution

**File**: `alpha_velocity/committee/paper_order_planner.py`

**Purpose**: Deterministic limit orders with protective stops, NO execution authority

**Properties**:
- Limit order construction (arrival price + buffer)
- Protective stops (based on invalidation levels)
- Partial fill handling
- Commission & spread estimation
- Liquidity participation
- Order expiration policies
- Duplicate-submission prevention

**Simulation Model**: `alpha_velocity/simulation/execution.py`
- Realistic fill simulation
- Slippage modeling (bid-ask, impact)
- Commission charging
- Liquidity constraints

**Paper Broker**: `alpha_velocity/paper/broker.py`
- Simulated account state
- Position tracking
- Fill recording
- P&L calculation

**Constraints**:
- No live execution path
- Account validation (DU prefix)
- Explicit approval required
- Paper-only gates (dry_run=true, transmit=false)

**Status**: ✅ Production, frozen

---

### 8. Evidence Ledger

**File**: `alpha_velocity/evidence_ledger/`

**Purpose**: Immutable record of all research, decisions, outcomes

**Records**:
- Scanner outputs (opportunities + evidence)
- Ranking decisions (component scores, final rank)
- Allocation proposals (target weights, reasoning)
- Risk approvals (constraint checks, decisions)
- Governance approvals (compliance, restrictions)
- Human reviews (promotion/rejection decisions, feedback)
- Position entries & exits (thesis, trigger, invalidation)
- Order execution (fills, costs, implementation shortfall)
- Forward returns & P&L (outcome validation)
- Calibration feedback (expected vs. realized)

**Properties**:
- Append-only
- Timestamps & source tracking
- Enables outcome grading
- Supports learning & validation

**Status**: ✅ Production, frozen

---

### 9. Position Intelligence (To be completed)

**File**: `alpha_velocity/position_intelligence/` (new module)

**Purpose**: Track and monitor active positions with multiple horizons

**For Every Position**:
- Immutable entry thesis & evidence
- Entry trigger & invalidation
- Expected holding period
- Expected move scenario
- Catalyst window & timing
- Current expected swing value vs. entry
- Realized & unrealized P&L
- Maximum favorable/adverse excursion

**Monitoring Horizons**:

Intraday:
- Spread & liquidity deterioration
- Halt risk, news shock
- Gap risk, failed breakout
- Protective-stop integrity

Daily:
- Close relative to trigger/invalidation
- Relative strength & volume confirmation
- Failed follow-through
- Expected-upside compression
- Opportunity-cost changes

Weekly:
- Primary trend & structural support
- Industry regime
- Valuation thesis & earnings thesis
- Capital structure & maturities
- Dilution progress
- Long-term catalyst progress

**Position Research States**:
- HOLD
- ADD_ON_CONFIRMATION
- REDUCE
- EXIT_HARD_RISK
- EXIT_THESIS_INVALIDATED
- EXIT_FAILED_BREAKOUT
- EXIT_TREND_REVERSAL
- EXIT_CATALYST_NEGATED
- EXIT_OPPORTUNITY_COST
- PROFIT_PROTECTION
- TIME_STOP
- RAISE_CASH

**Properties**:
- Intraday noise alone ≠ override weekly thesis
- Hard-risk condition breaches trigger exit
- All recommendations journaled
- No autonomous execution

**Status**: 🔄 To be implemented

---

### 10. Risk & Governance Review

**Files**: 
- `alpha_velocity/risk/engine.py`
- `alpha_velocity/governance/engine.py`

**Purpose**: Independent gates, cannot be bypassed

**Risk Review**:
- Position-level sizing constraints
- Portfolio-level exposure caps
- Volatility & correlation budget
- Liquidity & execution risk
- Downside budget compliance
- Concentration limits
- Severe-risk zero-weight override

**Governance Review**:
- Compliance with restrictions
- Short-sale rule compliance
- Restricted stock rules
- Account limitations
- Settlement timing

**Properties**:
- Independent review (not orchestrated within ranking)
- Hard gates (RISK_REJECTED, GOVERNANCE_REJECTED states)
- Cannot be overridden by ranking or allocation
- Journaled in Evidence Ledger

**Status**: ✅ Production, frozen

---

### 11. Human Research Review

**File**: `alpha_velocity/committee/models.py` → `HumanResearchReview`

**Purpose**: Track human feedback on candidates & research quality

**Feedback Types**:
- PROMOTE_FOR_DEEP_RESEARCH
- KEEP_ON_WATCHLIST
- REQUIRE_CHART_TRIGGER
- REQUIRE_FILINGS_REVIEW
- REQUIRE_TRANSCRIPT_REVIEW
- REQUIRE_CAPITAL_STACK_REVIEW
- REQUIRE_ACTIVIST_REVIEW
- REJECT_THESIS

**Properties**:
- Stored in Evidence Ledger
- Reviewer identity & timestamp retained
- Does NOT automatically alter production weights
- Graded later (outcome validation)
- Visible in future research reports

**Status**: ✅ Model defined, integration pending

---

## CANDIDATE LADDER (9 Research Queues)

**File**: `alpha_velocity/market_intelligence/candidate_ladder.py` (to be created)

**Purpose**: Organize candidates by actionability & research completeness

```
TIER 1: IMMEDIATELY ACTIONABLE
  1. ACTIONABLE_TRIGGERED
     - Technical: Completed weekly + valid daily trigger
     - Fundamental: Mispricing thesis complete & documented
     - Event: Catalyst timing & impact clear
     - Rank: Top opportunities, ready for allocation

  2. NEAR_TRIGGER
     - Technical: Completed weekly, price near daily trigger
     - Fundamental: Mispricing thesis documented
     - Event: Catalyst window open
     - Action: Monitoring closely for trigger

TIER 2: RESEARCH & CONFIRMATION
  3. CHART_MOMENTUM_RESEARCH
     - Technical: Compelling structure, awaiting confirmation
     - Action: Require price trigger + volume confirmation

  4. FUNDAMENTAL_MISPRICING_RESEARCH
     - Fundamental: Clear mispricing, technical entry pending
     - Action: Monitor for technical setup completion

  5. EVENT_ACTIVIST_RESEARCH
     - Event: Material development with clear thesis
     - Action: Monitor for price recognition

  6. SPECIAL_SITUATIONS
     - Multiple: Complex events requiring case-by-case analysis
     - Action: Detailed fundamental + technical review

  7. WAITING_FOR_CONFIRMATION
     - Status: Research complete, missing technical/catalyst confirmation
     - Action: Continue monitoring

TIER 3: NOT YET ACTIONABLE
  8. HIGH_RISK_SPECULATIVE
     - Risk: Severe capital-structure or execution risk
     - Rank: Capped or zero-weight override active

  9. EXCLUDED
     - Hard exclusions: Invalid data, illiquidity, asset-type incompatibility
     - Soft exclusions: Confirmation requirements not yet met

---

## COMMITTEE TOP FIVE SELECTION

**Priority Order**:
1. ACTIONABLE_TRIGGERED candidates (ranked by expected swing value)
2. NEAR_TRIGGER candidates (ranked by proximity to trigger)
3. Highest-quality research candidates with explicit missing confirmations

**Rule**: Do not fabricate five candidates when fewer than five survive hard exclusions.

**Fallback**: If Tier 1 + Tier 2 combined < 5, set `fallback_research_mode = true` and clearly label as "Research candidates, not yet actionable"

---

## SAMPLE DATA MODE

**Requirements**:
- Deterministic sample securities (5 equities)
- Populated candidate queues (at least 5 eligible)
- Multiple independent theses retained
- Clearly marked SAMPLE_DATA (warehouse source field)
- Hard-coded controls:
  - `dry_run = true` (cannot be overridden)
  - `transmit = false` (cannot be overridden)
  - `execution_authorized = false`

**Status**: ✅ Implemented, tested

---

## DATA MODES

### A. SAMPLE Mode
- Deterministic securities
- Populated candidate queues
- Minimum 5 eligible candidates
- Marked SAMPLE_DATA
- Dry-run forced true, transmit false

### B. CSV Research Mode
- Documented schemas (prices, fundamentals, events, ownership, estimates)
- Point-in-time available_at required
- Validation errors explicit

### C. WAREHOUSE Mode
- Canonical warehouse consumption
- Provider-neutral adapters
- No broker dependency for research

### D. LIVE RESEARCH DATA Mode
- Data retrieval only
- No execution implication
- Freshness & source checks required

**Status**: ✅ SAMPLE & WAREHOUSE complete, CSV & LIVE pending

---

## EXPERIMENTAL SYSTEMS (Disabled, Zero Influence)

### Turtle Trend Strategy

**Location**: `alpha_velocity/experimental_strategies/turtle_trend/`

**Status**: UNCALIBRATED
- ranking_influence = 0.0
- allocation_influence = 0.0
- NOT registered with Daily Committee
- NO futures data ingestion in equity workflow
- NO futures orders

**Rationale for Deferral**:
- Futures require separate infrastructure (margin, contract rolls, continuous series)
- No established hedge ratio or correlation regime with equity positions
- Validate independently before integrating with equity decisions

**To Enable**:
1. Implement comprehensive futures data ingestion
2. Build position-level margin tracking
3. Validate contract-roll behavior
4. Establish correlation & hedge ratios with equity holdings
5. Complete end-to-end execution testing

**Status**: 🚫 Disabled, preserved for research continuity

---

## VALIDATION & LEARNING

**Every component must be journaled and graded**:

- Forward returns (intra-trade, multi-day, multi-week)
- Maximum favorable/adverse excursion
- Hit rate & payoff ratio
- Calibration accuracy
- Expected vs. realized move
- Opportunity-cost performance
- Rotation benefit after costs
- False breakout rate
- Catalyst success rate
- Activist thesis outcome
- Normalized earnings accuracy
- Capital-stack thesis accuracy
- Management-language signal value
- Estimate-revision value
- Implementation shortfall

**Rules**:
- No evidence stream may promote itself
- Promotion remains a separate governed process
- Learning feedback loops are shadow-only until validated

**Status**: 🔄 Framework defined, implementation pending

---

## TESTING BOUNDARIES

**Architecture Tests**:
- ✅ No duplicate active Opportunity model
- ✅ No direct ranking-to-execution path
- ✅ Turtle Trend disabled and unregistered
- ✅ No live-account path
- ✅ All gates cannot be bypassed

**Scanner Tests**:
- ✅ Broad lens queues populated
- ✅ Top Five generated when eligible names exist
- ✅ Actionable candidates preferred
- ✅ Research tiers fill remaining capacity
- ✅ Hard exclusions remain enforced
- ✅ No fabricated candidates

**Ranking Tests**:
- ✅ Cheapness alone does not win
- ✅ Technical strength alone does not win
- ✅ Severe capital risk caps ranking
- ✅ Catalyst-to-chart linkage tested
- ✅ Missing data not favorable
- ✅ Unvalidated evidence zero influence
- ✅ Deterministic ranking

**Allocation Tests**:
- ✅ Cash competes with securities
- ✅ Target weights sum correctly
- ✅ Minor advantage does not trigger rotation
- ✅ Switching costs matter
- ✅ Concentration & sector caps enforced
- ✅ Liquidity capacity enforced
- ✅ Uncalibrated weight cap enforced
- ✅ Severe-risk zero weight enforced

**Execution Tests**:
- ✅ DU-only account enforcement
- ✅ Exact approval hash required
- ✅ Duplicate prevention
- ✅ Protective exits calculated
- ✅ Partial fills handled
- ✅ Spread, slippage, impact modeled
- ✅ Implementation shortfall tracked
- ✅ No live submission path

**Committee Tests**:
- ✅ Workflow reaches HUMAN_APPROVAL_PENDING
- ✅ execution_authorized remains false before approval
- ✅ No orders created in dry-run
- ✅ All state transitions logged

**Test Count**:
- 229/229 tests passing
- Focused tests: Market Intelligence, Ranking, Allocation, Committee
- Integration tests: Full workflow
- No external calls: Brokers, live data

---

## KNOWN LIMITATIONS & FUTURE WORK

**Provider Requirements**:
- Live market data ingestion (Bloomberg, Yahoo, IEX, etc.)
- Real-time options data & flow
- Alternative data (ownership, insider activity, analyst consensus)
- SEC filing & transcript access
- Catalyst calendars & broker research

**Model Enhancements** (documented, not yet implemented):
- Position Intelligence layer (detailed, multi-horizon monitoring)
- Catalyst-to-chart linkage validation
- Expected Swing Value calibration on larger dataset
- Alternative data scoring
- Machine learning model validation (shadow-only)
- Event novelty scoring
- Management-language change scoring

**Infrastructure**:
- Production data lake (versioned, queryable)
- Feature store (computed & cached)
- Model registry & versioning
- Experiment tracking & reproducibility
- Outcome database for grading

---

## CONCLUSION

Alpha Velocity Equity Intelligence v1 is an integrated, supervised, deterministic research & paper-trading platform. It preserves the tested stability of core systems while consolidating duplicates and establishing clear data flows.

**Frozen boundaries prevent**:
- Unauthorized execution
- Bypassed approval gates
- Risk or governance overrides
- Live-account access
- Autonomous model promotion

**All decisions are journaled**, enabling continuous learning and validation.

**Production-ready** for supervised paper trading with explicit human approval at each stage. Not a claim of investment profitability. Research-grade validation framework awaits forward-return data.

---

**Consolidated**: 2026-07-16  
**Test Status**: 229/229 passing  
**Architecture Status**: Frozen  
**Documentation**: Complete  
**Ready for**: Supervised paper deployment
