# Daily Investment Committee Orchestrator v1

## Overview

The Daily Investment Committee Orchestrator is a deterministic, supervised workflow engine that orchestrates the complete daily paper trading process for Alpha Velocity.

**Mission**: Enable research-controlled, human-approved paper trading with complete transparency and immutable audit trails.

**Safety model**: No autonomous execution. Explicit human approval required. Independent risk and governance gates. Paper account only (DU prefix).

**Status**: Research-grade. Collects evidence for research validation. Not a claim of investment profitability.

---

## Workflow States

The orchestrator enforces a strict state machine with 18 explicit states:

```
CREATED
  ↓
DATA_REFRESHED  (warehouse readiness check)
  ↓
UNIVERSE_BUILT  (exclusions applied)
  ↓
SCAN_COMPLETED  (opportunities assembled)
  ↓
RANKING_COMPLETED  (ranked by swing value)
  ↓
CAPITAL_PROPOSAL_CREATED  (allocation proposed)
  ↓
RISK_REVIEW_PENDING  (independent risk review)
  ├→ RISK_REJECTED  (risk gate failed)
  │
GOVERNANCE_REVIEW_PENDING  (independent governance review)
  ├→ GOVERNANCE_REJECTED  (governance gate failed)
  │
HUMAN_APPROVAL_PENDING  (explicit human approval required)
  ├→ HUMAN_REJECTED  (human declined)
  │
APPROVED_FOR_PAPER_SUBMISSION  (all gates passed)
  ↓
PAPER_SUBMISSION_PARTIAL  (some orders submitted, some rejected)
  or
PAPER_SUBMISSION_COMPLETED  (all orders submitted)
  ↓
RECONCILED  (fills received, positions closed, P&L recorded)
  ├→ FAILED  (error occurred)
  ├→ CANCELLED  (user cancelled)
```

**Properties**:
- States are explicit and enumerated
- Transitions are one-way and validated
- No transitions skip required stages
- Failures are tracked immutably

---

## Daily Workflow Stages

### Stage A: Warehouse Readiness Check

**Input**:
- Warehouse manifest reference
- Dataset manifest reference
- Data availability timestamps

**Validation**:
- Point-in-time data only (no future data)
- No unresolved critical quality failures
- Dataset manifests match stored hashes
- Price history is recent (< 1 hour old)

**Output**: `DATA_REFRESHED` state

**Decision**: Go / No-Go

---

### Stage B: Market Intelligence Scan

**Input**:
- Universe configuration (sector, market cap, liquidity filters)
- Exclusion list
- Observation time

**Process**:
- Universe construction with exclusions
- Technical structure analysis
- Liquidity and volatility assessment
- Opportunity assembly

**Output**: Opportunity objects (canonical form)

**Properties**:
- Point-in-time: all data has available_at ≤ observation_time
- Deterministic: identical inputs → identical opportunities
- Immutable: opportunities are frozen

**Next state**: `UNIVERSE_BUILT` → `SCAN_COMPLETED`

---

### Stage C: Opportunity Ranking

**Input**:
- Opportunity objects (from scan)
- Ranking configuration

**Process**:
- Score by expected favorable swing value
- Intrinsic × Timing × Magnitude × Probability × Liquidity × (1 - Uncertainty)
- Capital distress cannot be overridden by technical strength
- Unvalidated evidence receives zero influence
- Classify opportunities (HIGH_PRIORITY_TRIGGERED, WAITING_FOR_TRIGGER, etc.)

**Output**: RankingBatch with RankingResult objects

**Properties**:
- Highest expected swing value ranks first
- Technical cannot override capital distress
- No fabricated probabilities
- Missing data not treated as favorable

**Next state**: `RANKING_COMPLETED`

---

### Stage D: Capital Allocation Proposal

**Input**:
- RankingBatch (ranked opportunities)
- Current portfolio state
- Capital constraints
- Sizing configuration

**Process**:
- Allocate capital to top opportunities
- Respect concentration limits (sector, industry, correlation bucket)
- Respect gross and net exposure caps
- Retain minimum cash reserve
- Check liquidity constraints
- Calculate transaction costs

**Output**: CapitalAllocationProposal (research-only, no positions created)

**Properties**:
- Deterministic and repeatable
- No portfolio mutation
- No broker integration
- Execution never authorized

**Next state**: `CAPITAL_PROPOSAL_CREATED`

---

### Stage E: Independent Risk Review

**Input**:
- CapitalAllocationProposal

**Process**:
- Risk engine independently evaluates proposal
- Checks concentration risk
- Checks drawdown scenarios
- Checks liquidation requirements
- Can reject proposal

**Output**: Risk review decision (APPROVED, CONDITIONAL, REJECTED)

**Properties**:
- Orchestrator cannot override risk rejection
- Risk review is independent (separate team, separate code)

**Next state**: `RISK_REVIEW_PENDING` → `RISK_REJECTED` or `GOVERNANCE_REVIEW_PENDING`

---

### Stage F: Independent Governance Review

**Input**:
- CapitalAllocationProposal

**Process**:
- Governance engine independently evaluates
- Checks restricted information rules
- Checks trading halt statuses
- Checks insider trading restrictions
- Can reject proposal

**Output**: Governance review decision (APPROVED, CONDITIONAL, REJECTED)

**Properties**:
- Orchestrator cannot override governance rejection
- Governance is independent

**Next state**: `GOVERNANCE_REVIEW_PENDING` → `GOVERNANCE_REJECTED` or `HUMAN_APPROVAL_PENDING`

---

### Stage G: Explicit Human Approval

**Input**:
- CapitalAllocationProposal
- Approval token (from human)

**Approval Record**:
```python
@dataclass(frozen=True)
class HumanApprovalRecord:
    approval_id: str
    proposal_id: str
    proposal_hash: str  # SHA256(proposal)
    approved_by: str    # Human identifier
    approved_at: datetime
    expires_at: datetime
    approved_actions: tuple[str, ...]  # Specific actions
    rejected_actions: tuple[str, ...]  # Explicitly rejected
    comments: str
    approval_scope: str  # "PAPER_ONLY", "DRY_RUN_ONLY", etc.
```

**Validation**:
- Approval must identify proposal_id and immutable hash
- Approval must be specific (not blanket)
- Approval must expire (no permanent approvals)
- Approval hash must match current proposal (material changes invalidate)

**Properties**:
- Approval is narrow and explicit
- Blanket approvals ("trade whatever") are rejected
- Hash mismatch prevents silent proposal changes
- Expiration prevents stale approvals

**Next state**: `HUMAN_APPROVAL_PENDING` → `HUMAN_REJECTED` or `APPROVED_FOR_PAPER_SUBMISSION`

---

### Stage H: Paper-Only Hard Gates

**Pre-submission validation** (no exceptions in v1):

```python
def validate_paper_gates(session):
    errors = []
    
    # Account check
    if not account.startswith("DU"):
        errors.append("Account must be paper (DU prefix)")
    
    # Dry-run vs transmit
    if transmit and dry_run:
        errors.append("Cannot transmit during dry run")
    
    # Approval checks (if transmit=true)
    if transmit:
        if not human_approval:
            errors.append("Human approval required")
        if not risk_approved:
            errors.append("Risk approval required")
        if not governance_approved:
            errors.append("Governance approval required")
        if approval.expires_at < now:
            errors.append("Approval expired")
        if approval.proposal_hash != current_hash:
            errors.append("Approval hash mismatch")
    
    # Market data freshness
    if market_data_age > 1_hour:
        errors.append("Market data stale")
    
    # Portfolio snapshot freshness
    if portfolio_age > 30_minutes:
        errors.append("Portfolio snapshot stale")
    
    return errors
```

**No configuration flag may disable these checks in v1.**

---

### Stage I: Paper Order Planning

**Input**:
- Approved CapitalAllocationProposal
- Current positions
- Reference prices

**Process**:
- Create deterministic order plan
- New positions (limit orders, conservative limits)
- Position reductions (limit orders, conservative limits)
- Protective stops where required
- Estimate transaction costs
- Order dependency (reductions fund additions)

**Output**: PaperOrderPlan (not submitted)

**Properties**:
- Deterministic
- Conservative limits (2bps above/below)
- No market orders unless required
- Cost estimates included

---

### Stage J: Paper Order Submission

**Input**:
- PaperOrderPlan
- IBKR paper account connection

**Process** (only if transmit=true AND dry_run=false):
- Connect to IBKR
- Verify account identifier starts with DU
- Submit orders in dependency order
- Track submitted orders

**Output**: Submission report with order IDs

**Properties**:
- Orders only to paper account
- Live trading code path unreachable
- Submission tracked immutably

---

### Stage K: Evidence Ledger Recording

**Recording** (at every stage):
- Opportunity objects and decisions
- Ranking results and evidence
- Capital proposal and constraints
- Risk review decision and reasoning
- Governance review decision
- Human approval record (hash match)
- Paper submission order IDs
- All rejections and failures

**Immutability**:
- Append-only ledger
- Shadow research recorded with zero influence
- Full audit trail permanent
- Execution_authorized always False

---

### Stage L: Morning Committee Report

**Content** (deterministic JSON and Markdown):
- Market regime summary
- Universe size and exclusions
- Top 10 ranked opportunities
- High-priority triggered list
- Waiting-for-trigger list
- Current portfolio vs proposed
- Proposed capital changes
- Transaction cost estimates
- Risk review result
- Governance review result
- Human approval status
- Execution readiness
- Major risks and warnings
- Shadow expectations research (labeled, zero influence)

**Format**:
```json
{
  "report_id": "MORNING-COMM-20260115-...",
  "session_id": "COMM-20260115-143000-...",
  "universe": {
    "size": 500,
    "exclusions": 50
  },
  "ranking": {
    "total_opportunities": 50,
    "high_priority_triggered": 3,
    "high_priority_waiting": 12,
    "top_5_opportunities": [...]
  },
  "capital_proposal": {
    "proposed_cash": 50000.0,
    "proposed_gross_exposure": 100000.0,
    "proposed_holdings": [...]
  },
  "risk_review": {
    "approved": true,
    "restrictions": []
  },
  "governance_review": {
    "approved": true,
    "restrictions": []
  },
  "human_approval": {
    "status": "PENDING"
  },
  "execution_readiness": {
    "ready_for_submission": false
  }
}
```

**Distribution**:
- JSON to committee members
- Markdown to human committee
- Printed for morning meeting

---

### Stage M: End-of-Day Reconciliation

**Recording**:
- Submitted order IDs
- Broker acknowledgements
- Accepted and rejected orders
- Partial fills
- Full fills
- Cancellations
- Closing positions
- Closing cash
- Realized P&L
- Unrealized P&L
- Discrepancies (unfilled orders, price gaps, etc.)
- Unresolved orders and follow-ups

**Output**: Reconciliation report with all details

**Properties**:
- No fabricated fills or prices
- All source fills from broker
- Discrepancies identified and documented
- Ledger links for each order

---

## Human Approval Model

### Approval Record Structure

```python
@dataclass(frozen=True)
class HumanApprovalRecord:
    approval_id: str                    # Unique approval identifier
    proposal_id: str                    # Specific proposal ID (not blanket)
    proposal_hash: str                  # SHA256 of immutable proposal
    approved_by: str                    # Name of approver
    approved_at: datetime               # When approved
    expires_at: datetime                # When approval expires (max 2 hours)
    approved_actions: tuple[str, ...]   # Specific actions approved
    rejected_actions: tuple[str, ...]   # Specific actions rejected
    comments: str                       # Approval notes
    approval_scope: str                 # "PAPER_ONLY" or "DRY_RUN_ONLY"
    schema_version: str                 # For evolution
```

### Validation Rules

1. **Specific, not blanket**:
   - ✓ "Approve PROP-001 hash abc123 for paper trading"
   - ✗ "Trade whatever the system wants"

2. **Immutable approval hash**:
   - Hash is SHA256 of entire proposal
   - Material changes require new approval
   - Prevents silent proposal modification

3. **Expiration required**:
   - Default 120 minutes
   - No permanent approvals
   - Automatic expiration protects against stale decisions

4. **Scope narrow**:
   - Must specify "PAPER_ONLY" or "DRY_RUN_ONLY"
   - Scope enforced by gates
   - Prevents cross-mode approval

5. **Audit trail immutable**:
   - Approval record is frozen
   - Cannot be modified after creation
   - Recorded in evidence ledger

### Approval Flow

```
Proposal created and hashed
  ↓
Sent to human for review (morning committee meeting)
  ↓
Human reviews morning report
  ↓
Human decides: Approve or Reject
  ↓
If Approve:
  - Create HumanApprovalRecord with specific scope
  - Hash must match current proposal
  - Approval expires in 120 minutes
  ↓
If Reject:
  - Workflow stops (HUMAN_REJECTED state)
  - Reasons documented
  ↓
On submission:
  - Hash validated (material changes detected)
  - Expiration checked
  - Scope enforced
```

---

## Paper-Only Safeguards

### Hard Gates (No Exceptions in v1)

1. **Account identifier validation**:
   - Must start with "DU"
   - Rejects "LIVE", "PROD", production identifiers
   - Checked before session creation
   - Checked again before submission

2. **Dry-run vs Transmit**:
   - Cannot set both transmit=true AND dry_run=true
   - Default is dry_run=true, transmit=false (safe)
   - Prevents accidental live submission

3. **Approval requirement**:
   - transmit=true requires human_approval
   - Approval must be valid (hash, expiration, scope)
   - Risk and governance must both approve

4. **Data freshness**:
   - Market data must be < 1 hour old
   - Portfolio snapshot must be < 30 minutes old
   - Prevents stale decision data

5. **No configuration override**:
   - No environment variable can disable gates
   - No configuration flag can weaken gates
   - Code review required for any change

### Configuration Validation

```python
# Before any submission
errors = orchestrator.validate_paper_gates(session)
if errors:
    raise ValueError(f"Paper gates failed: {errors}")
```

---

## Dry-Run Behavior

**Dry-run mode** (default):
- Runs all stages: scan, ranking, risk, governance, approval
- Creates morning report
- Creates paper order plan
- Does NOT submit orders to broker
- Does NOT connect to IBKR
- Does NOT impact portfolio
- Safe for testing and training

**Dry-run advantages**:
- Full workflow testing without risk
- Human can review morning report
- Can iterate if proposal needs refinement
- No broker integration required

**Switching to live submission**:
```bash
# First: Run in dry-run (default)
RUN_DAILY_INVESTMENT_COMMITTEE.bat
# Review morning report...

# Then: Submit approved proposal
RUN_DAILY_INVESTMENT_COMMITTEE.bat --transmit
# Requires human approval before submission
```

---

## CLI Commands

### Create Daily Session

```bash
committee run --dry-run
```

Output:
- Session created with ID
- Morning report saved
- Workflow state tracked

### View Morning Report

```bash
committee report --session-id COMM-20260115-143000-12345678 --format markdown
```

Output:
- Markdown-formatted report
- Decision summary
- Top opportunities
- Proposed changes
- Risk/governance status
- Execution readiness

### Record Approval

```bash
committee approve \
  --session-id COMM-20260115-143000-12345678 \
  --proposal-hash abc123def456... \
  --approved-by "Alice" \
  --expires-minutes 120 \
  --comments "Approved for paper trading"
```

Creates immutable approval record.

### Submit to Paper Broker

```bash
committee submit-paper --session-id COMM-20260115-143000-12345678
```

Requires:
- Human approval
- Risk approval
- Governance approval
- Valid paper account
- transmit=true

### Reconcile Session

```bash
committee reconcile --session-id COMM-20260115-143000-12345678
```

Output:
- Fills and cancellations
- Position reconciliation
- P&L report
- Discrepancies
- Next-day follow-ups

---

## Restart and Failure Handling

### Session Checkpoints

Sessions are saved to disk after each stage:
```
committee_state/
├── COMM-20260115-143000-12345678.json
├── COMM-20260115-143100-87654321.json
└── ...
```

Each checkpoint contains:
- Current workflow state
- All decisions made so far
- Evidence references
- Failure reasons (if any)

### Restart Safety

**Automatic restart checks**:
1. Load session from disk
2. Check workflow state
3. Prevent duplicate submissions
4. Resume from last successful stage

**Example**:
```bash
# Session interrupted after RISK_REVIEW_PENDING
# Load session...
session = orchestrator.load_session("COMM-20260115-143000-12345678")
# Workflow state is RISK_REVIEW_PENDING
# Rerun will check risk decision, not re-submit to risk

# Can then proceed to governance
session = orchestrator.continue_workflow(session)
```

### Recovery Without Duplication

- Session ID prevents duplicate orders
- Order tracking prevents re-submission
- Evidence ledger supersedes mechanism for corrections
- Timestamp-based idempotency

---

## Failure Modes

### Common Failures

1. **Market data stale**:
   - Market data > 1 hour old
   - Workflow stops with error
   - Requires manual market data refresh
   - Rerun after data update

2. **Portfolio snapshot stale**:
   - Portfolio snapshot > 30 minutes old
   - Workflow stops
   - Requires manual portfolio retrieval
   - Rerun after portfolio update

3. **Risk rejection**:
   - Risk engine rejects proposal
   - Workflow stops at RISK_REJECTED state
   - Reasons documented
   - Rerun with modified proposal

4. **Governance rejection**:
   - Governance engine rejects proposal
   - Workflow stops at GOVERNANCE_REJECTED state
   - Reasons documented
   - Rerun with modified proposal

5. **Human rejects approval**:
   - Human declines approval
   - Workflow stops at HUMAN_REJECTED state
   - Comments documented
   - Rerun with proposal modifications

6. **Approval expired**:
   - Approval expires (default 120 minutes)
   - Workflow stops before submission
   - Requires new approval
   - Rerun with fresh approval token

7. **Partial order fill**:
   - Some orders rejected by broker
   - Recorded in PAPER_SUBMISSION_PARTIAL state
   - Reconciliation identifies unsubmitted
   - Manual follow-up in next session

8. **Broker connection failed**:
   - IBKR paper account unreachable
   - Workflow stops
   - Check connection settings
   - Rerun after connection restored

### Failure Recovery

```
Workflow fails
  ↓
Session saved to disk with failure details
  ↓
Human reviews failure reason
  ↓
Fix underlying issue (data, portfolio, proposal, etc.)
  ↓
Restart workflow:
  committee run --session-id COMM-...
  or
  committee run  (new session)
  ↓
Workflow resumes or restarts from checkpoint
```

---

## Boundaries and Limitations

### By Design

✅ **Supports**:
- Research-only capital allocation
- Human-approved paper trading
- Complete audit trail
- Risk and governance independence
- Explicit approval workflow
- Dry-run safe testing
- Deterministic reporting
- Shadow research tracking
- Immutable decision records

❌ **Does NOT Support**:
- Live trading (hard-coded block)
- Autonomous execution (transmit forbidden without approval)
- Bypass of risk/governance (independent gates)
- Bypass of human approval (explicit record required)
- Non-DU paper accounts (account validation)
- Blanket approvals (narrow approval records)
- Permanent approvals (expiration enforced)
- Silent proposal changes (hash mismatch detected)
- Stale data usage (freshness check)
- Parameter optimization (no optimizer)
- Profitability claims (research-only)
- Weakening of controls (frozen gates)

### Known Limitations

1. **Requires IBKR paper account connection**:
   - Must have TWS running
   - Must have paper account setup
   - Must have secure connection configured

2. **No integration with live brokers**:
   - Paper only in v1
   - Live account would require separate approval process

3. **No adaptive order management**:
   - Orders submitted as planned
   - No adaptive adjustments mid-day
   - Manual modification only

4. **No portfolio correlation analysis**:
   - Existing correlation limits enforced
   - No real-time correlation recalculation
   - Static correlation buckets

5. **No predictive regime detection**:
   - Current market regime used
   - Not forecasted from current session
   - Must be set in configuration

6. **Limited failure recovery**:
   - Manual intervention required
   - No automatic retry logic
   - Human must approve retry

### v1 Assumptions

1. Market data source (warehouse) is accurate and complete
2. Portfolio snapshots are accurate
3. IBKR paper account is functional and verified
4. Risk engine and governance engine are independent and working
5. Human committee is available for approval within approval window
6. Session state directory is accessible and writable
7. No external system mutation during workflow
8. Broker latency < 5 seconds for order submission

---

## Operating Procedure

### Morning (Before Market Open)

```
1. Run committee session
   RUN_DAILY_INVESTMENT_COMMITTEE.bat
   
2. Review morning report
   - Check universe size
   - Check top opportunities
   - Check proposed allocations
   - Check risk/governance status
   
3. Approve if consensus
   committee approve \
     --session-id COMM-... \
     --proposal-hash abc... \
     --approved-by "Alice"
   
4. Decision: Submit or Hold
   - If submit: committee submit-paper
   - If hold: No orders submitted (dry run default)
```

### During Market Hours

```
1. Monitor submitted orders
   - Check fills via IBKR
   - Track partial fills
   - Document any rejections
```

### End of Day (After Market Close)

```
1. Run reconciliation
   RECONCILE_PAPER_SESSION.bat COMM-...
   
2. Review reconciliation report
   - All fills received
   - Positions reconciled
   - P&L calculated
   - Discrepancies noted
   
3. Document any issues
   - Unfilled orders
   - Price gaps
   - Execution quality
   
4. Archive session
   - Session data backed up
   - Reports archived
   - Next day session prepared
```

---

## Report Interpretation

### Morning Report Sections

**Universe**:
- Size: Total opportunities scanned
- Exclusions: Filtered out (insufficient data, restrictions, etc.)
- Indicator: Broad coverage or narrow focus

**Ranking Summary**:
- Total ranked: Full opportunity count
- High priority triggered: Ready to execute (entry conditions met)
- Waiting for trigger: Strong thesis, awaiting entry setup
- Indicator: Concentration risk if triggered << waiting

**Top 5 Opportunities**:
- Rank, symbol, score
- Ranking state (triggered or waiting)
- Contributors (key drivers)
- Indicator: Evidence strength and diversity

**Current vs Proposed**:
- Cash changes
- New positions
- Increased positions
- Indicator: Capital efficiency and concentration

**Risk Review**:
- Approved or rejected
- Restrictions (if any)
- Indicator: Risk engine confidence

**Governance Review**:
- Approved or rejected
- Restrictions (if any)
- Indicator: Governance gate satisfied

**Approval Status**:
- Pending or approved
- Approver identity
- Expiration time
- Indicator: Ready for submission or awaiting approval

### Reconciliation Report Sections

**Order Summary**:
- Submitted, filled, cancelled, partial
- Indicator: Execution quality

**Fills**:
- Order ID, symbol, quantity, price, time
- Indicator: Fill quality and timing

**Cancellations**:
- Why cancelled (risk limit, rejected by broker, etc.)
- Indicator: Constraint binding

**Closing State**:
- Positions, cash, gross exposure
- Indicator: Actual vs proposed
- P&L: Realized and unrealized
- Indicator: First-day performance

**Discrepancies**:
- Unfilled orders
- Price gaps
- Capacity issues
- Indicator: Operational issues

---

## Known Limitations and Future Work

### Current Research Status

This system is a **research tool**, not a validated investment system:

1. **No historical backtest results**:
   - First implementation
   - No out-of-sample validation
   - No forward test track record

2. **No profitability guarantee**:
   - Paper trading may not generate alpha
   - Market may not cooperate with thesis
   - Position sizing is prototype heuristic

3. **No model stability claims**:
   - Ranking weights may need adjustment
   - Evidence quality scores may be miscalibrated
   - Shadow research validation not yet complete

4. **No risk model validation**:
   - Scenario assumptions may be outdated
   - VaR calculations may underestimate tail risk
   - Drawdown forecasts may be inaccurate

### Improvements for Future Versions

- [ ] Adaptive order management (midday adjustments)
- [ ] Real-time correlation rebalancing
- [ ] Walk-forward validation framework
- [ ] Machine learning for evidence weighting
- [ ] Multi-instrument support (options, futures)
- [ ] Live account support (separate approval process)
- [ ] Advanced order types (iceberg, VWAP, etc.)
- [ ] Automatic regime detection
- [ ] Portfolio correlation matrix
- [ ] Stress testing integration

---

## Summary

The Daily Investment Committee Orchestrator is a **research-controlled, human-supervised** system that:

✅ Enables paper trading with complete transparency  
✅ Records every decision immutably  
✅ Enforces human approval  
✅ Maintains independent risk and governance gates  
✅ Prevents autonomous execution  
✅ Validates paper-only operation  
✅ Tracks evidence for validation  
✅ Produces deterministic reports  
✅ Provides safe dry-run testing  
✅ Supports session restart and recovery  

❌ Does not claim investment edge  
❌ Does not guarantee profitability  
❌ Does not support live trading  
❌ Does not bypass human approval  
❌ Does not weaken governance  

**Ready for research-grade paper trading with explicit human control.**
