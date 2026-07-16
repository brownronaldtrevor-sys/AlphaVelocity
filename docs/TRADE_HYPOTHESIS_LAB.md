# Trade Hypothesis Lab - Human Hypothesis Framework

**Date**: 2026-07-16  
**Purpose**: Adapter for researcher-authored investment theses  
**Status**: Experimental, zero allocation influence

---

## OVERVIEW

Researchers can author hypotheses in structured YAML/JSON, load them into the Opportunity Marketplace, and track their performance against market.

**Key constraints**:
- Zero allocation influence (no portfolio impact)
- Separate validation until promoted
- Full lineage and authorship recorded
- Non-exclusive (researcher can have many hypotheses)
- Can be linked to marketplace opportunities for tracking

---

## HYPOTHESIS TEMPLATE

```yaml
# Trade Hypothesis Template
# Save as: hypotheses/examples/YOUR_SYMBOL_YOUR_THESIS.yaml

hypothesis_id: null  # Auto-generated if omitted (HYP-XXXXXXXX)

# Security identification (required)
symbol: "SYMBOL"
security_id: "SEC_123456"

# Author and timing (required)
author: "Your Name"
created_at: null  # Auto-populated if omitted
observation_time: "2026-07-16T00:00:00Z"  # ISO datetime

# Core thesis (all required, 1-3 paragraphs each)
thesis_text: |
  One to three sentences describing the core thesis for repricing.
  Why should this equity move materially higher over the next 6 months?
  What is the business, asset value, or capital-stack opportunity?

rationale: |
  Detailed explanation building out the thesis narrative.
  Support with specific facts: revenue, margins, catalysts, valuations.
  Explain why the market is mispricing or unaware.
  Why now? What changes make this opportunity ripe?

required_confirmation: |
  What must happen to confirm the thesis is playing out?
  Examples:
    "Price closes above $50 on strong volume"
    "Quarterly guidance raised by >10% YoY"
    "Activist announces board seat or strategic initiatives"
    "Credit rating upgraded or covenant waived"

invalidation_trigger: |
  What breaks the thesis completely?
  Examples:
    "Quarterly guidance cut or covenant breach"
    "Activist exits position or loses board seat"
    "Debt matures without refinancing plan"
    "Key customer loss or margin compression"

# Optional confidence (required)
author_confidence: 0.7  # 0.0-1.0, default 0.5

# Allocation influence (always false initially)
allocation_influence_allowed: false  # Only true after external validation

# Optional fields
hypothesis_id: null  # Auto-generate if omitted
```

---

## LOADING HYPOTHESES

### From YAML

```python
from alpha_velocity.marketplace import TradeHypothesisAdapter

adapter = TradeHypothesisAdapter()
hypothesis = adapter.load_from_yaml("hypotheses/examples/JELD_EXAMPLE.yaml")
print(hypothesis.symbol, hypothesis.author_confidence)
```

### From Dict

```python
data = {
    "symbol": "JELD",
    "security_id": "SEC-JELD",
    "author": "John Doe",
    "thesis_text": "Thesis...",
    "rationale": "Rationale...",
    "required_confirmation": "Confirmation...",
    "invalidation_trigger": "Invalidation...",
    "author_confidence": 0.65,
}

hypothesis = adapter.load_from_dict(data)
```

### Validation

```python
data = {...}
valid, errors = adapter.validate_schema(data)
if not valid:
    for error in errors:
        print(error)
```

---

## LINKING TO OPPORTUNITIES

Hypotheses can be linked to marketplace opportunities:

```python
classification = OpportunityCandidateClassification(
    ...,
    human_hypothesis=hypothesis,
    marketplace_queues=(
        MarketplaceQueue.HUMAN_HYPOTHESIS,
        MarketplaceQueue.ASYMMETRIC_VALUE_RESEARCH,  # Can overlap
    ),
    ...
)
```

---

## EVIDENCE LEDGER RECORDING

All hypotheses are recorded in Evidence Ledger:
- hypothesis_id
- author
- observation_time
- symbol and security_id
- full thesis text
- author_confidence
- linked opportunity_ids
- creation_time

This enables post-hoc analysis of hypothesis accuracy and author calibration.

---

## PROMOTION PROCESS

A hypothesis remains zero-influence until:

1. **Research validation**: Independent researcher reviews thesis
2. **Market feedback**: Hypothesis tracked for 20+ days of market action
3. **Promotion vote**: Research team votes to enable allocation influence
4. **Record update**: Allocation_influence_allowed set to true (externally)
5. **Committee integration**: Next day, hypothesis influences allocation

Promotion is explicit, documented, and reversible.

---

## EXAMPLE: JELD-WEN (JELD)

**File**: `hypotheses/examples/JELD_EXAMPLE.yaml`

```yaml
hypothesis_id: HYP-JELD-2026
symbol: JELD
security_id: SEC-JELD
author: Research Team
created_at: "2026-07-15T00:00:00Z"
observation_time: "2026-07-16T00:00:00Z"

thesis_text: |
  JELD-WEN has normalized EBITDA of $300M on annualized revenue,
  implying 4.2x EBITDA on current market cap of $300M.
  Housing recovery beginning post-cycle, margins inflecting.
  Activist accumulation signals structural change underway.

rationale: |
  Historical context: JELD-WEN trades 3-5x EBITDA peer average.
  Current: 3.5x EBITDA on normalized earnings despite improving backlog.
  Activist: 13D filed March 1 for 5.1% stake. Meeting April 15.
  Catalyst: Q2 earnings Aug 1 expected to show continued margin recovery.
  Base case: 2027E EBITDA $350M (17% growth) → $1.4B enterprise value.
  Bull case: Activist board seat + buyback program → $1.6B valuation.
  DCF: $12-18 target range; current $7 = 70-157% upside.

required_confirmation: |
  Q2 earnings beat and raised guidance (>8% EPS beat).
  Form 4 filings show continuing insider buying or activist buying.
  Technical: Break above $8 on volume confirmation.

invalidation_trigger: |
  Q2 earnings miss or guidance cut.
  Activist walks away from stake.
  Housing starts data disappoints (reverse to negative).
  Debt covenant concerns emerge.

author_confidence: 0.72
allocation_influence_allowed: false
```

---

## HYPOTHESIS STATUS TRACKING

After loading into marketplace, hypothesis moves through states:

1. **CREATED** - Initial load
2. **TRACKING** - Monitored daily for confirmation/invalidation
3. **INVALIDATED** - Trigger condition met, thesis broken
4. **CONFIRMED** - Confirmation condition met, thesis playing out
5. **PROMOTION_ELIGIBLE** - Confirmed, ready for allocation influence review
6. **PROMOTED** - Research team voted to enable allocation influence
7. **ACTIVE_IN_ALLOCATION** - Now influences daily committee decisions
8. **CLOSED** - Position exited, thesis graded

---

## OUTPUT: HYPOTHESIS PERFORMANCE REPORT

After N weeks:

```
Hypothesis: JELD-WEN Activist Margin Inflection
Author: Research Team (confidence: 0.72)
Created: 2026-07-16
Status: TRACKING (Day 15)

Market price: $7.20 (entry $7.00) = +2.8%
Confirmation tracking:
  - Q2 earnings: Not yet (due August 1)
  - Form 4: 2 insider buy forms filed (positive signal)
  - Technical: $8 resistance remains 11% away

Invalidation monitoring:
  - Housing starts: On trend (no threat)
  - Activist: Continued accumulation reported (positive)
  - Debt: No new concerns (positive)

Thesis health: GREEN (no invalidations, early confirmation signals)
Recommendation: HOLD HYPOTHESIS, monitor Q2 earnings August 1

Historical calibration:
  - Prior 50 theses: 60% hit required confirmation
  - Average time to confirmation: 28 days
  - Confidence premium: Theses 0.70+ have 72% hit rate
```

---

## KNOWN LIMITATIONS

1. **Manual authorship** - Hypotheses are human-written, not algorithmic
2. **Narrative bias** - Authors may cherry-pick facts
3. **Delayed promotions** - Promotion vote delays allocation integration
4. **No automated grading** - Outcome labels applied manually post-close
5. **Researcher availability** - Promotion process requires research team voting

---

## RECOMMENDATION

Use human hypotheses to:
- Document researcher insights not yet quantified
- Track emerging theses until market recognition
- Calibrate researcher judgment and prediction accuracy
- Preserve institutional knowledge across team turnover

Do NOT use hypotheses as substitutes for systematic research—always require quantification and third-party validation before allocation influence.

---

**Status**: Framework stable, awaiting hypothesis submissions from research team
