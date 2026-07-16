# Opportunity Marketplace v1 - Discovery, Classification & Research Organization

**Date**: 2026-07-16  
**Status**: Production-Ready  
**Tests**: 27 passing  

---

## OVERVIEW

The Opportunity Marketplace v1 organizes researched opportunities (from ranking engine) into 13 discovery queues and 8 independent research lenses.

**Mission**: Convert a filtered list of opportunities into a comprehensive research marketplace that distinguishes:
- Trade-ready candidates
- Starter-position candidates
- Near-trigger candidates  
- Active research opportunities
- Excluded securities with reasons

**Properties**:
- No duplicate Opportunity model (reuses canonical ranking output)
- Lenses are independent, non-exclusive (one opportunity in multiple queues)
- Human hypotheses integrated with zero allocation influence
- Complete evidence lineage preserved
- Fallback research mode when actionable candidates are scarce

---

## 13-QUEUE MARKETPLACE

### Trade-Ready (Actionable)

**1. ACTIONABLE_TRIGGERED**
- Trigger state: TRIGGERED
- Calibration: CALIBRATED (probability estimate available)
- Risk & Governance: Eligible
- Model agreement: No disagreement
- Action: Ready for position
- Committee priority: #1

Example: "Cup and handle completed, daily breakout on strong volume, calibrated 60% probability, earnings in 3 weeks"

**2. STARTER_POSITION_CANDIDATE**
- Trigger state: TRIGGERED
- Calibration: UNCALIBRATED (research-grade confidence)
- Risk & Governance: Eligible  
- Model agreement: No disagreement
- Action: Build starter, monitor for additional confirmation
- Committee priority: #2

Example: "Completed weekly base, daily breakout on moderate volume, thesis sound but model disagreement on entry timing"

**3. NEAR_TRIGGER**
- Trigger state: WAITING_FOR_TRIGGER
- Weekly trend: UPTREND
- Structure: Complete
- Action: Monitor for daily trigger
- Committee priority: #3

Example: "Cup and handle with target $50, currently trading $49.20, awaiting daily break above $50"

### Active Research

**4. ASYMMETRIC_VALUE_RESEARCH**
- Discovery: ASYMMETRIC_EQUITY lens found 3x+ scenarios
- Survivability: Confirmed  
- Technical: Incomplete structure (pre-trigger)
- Action: Monitor for chart setup completion
- Expected horizon: 30-90 days until trigger
- Queue size: Up to 20 candidates

Example: "Normalized FCF $3/share implies $9-12 target (3-4x), debt manageable, currently $7 trading 0.7x FCF"

**5. CHART_MOMENTUM_RESEARCH**
- Discovery: CHART_AND_RECOGNITION lens identified setup
- Structure: Complete but not yet broken
- Action: Monitor for daily breakout confirmation
- Expected horizon: 5-20 days until trigger
- Queue size: Up to 20 candidates

Example: "Inverted cup and handle identified, support at $48.50, resistance at $52, awaiting break"

**6. TOP_DOWN_INDUSTRY_RESEARCH**
- Discovery: TOP_DOWN_MARKET_AND_INDUSTRY lens selected company
- Sector leading: ESTABLISHED_LEADER or EARLY_LEADERSHIP
- Company positioning: Best-of-breed within group
- Action: Monitor sector leadership continuation
- Expected horizon: Sector-dependent
- Queue size: Up to 20 candidates

Example: "Semiconductor industry acceleration, Company X has highest FCF margin, best guide, expecting allocation flow"

**7. EVENT_ACTIVIST_RESEARCH**
- Discovery: CORPORATE_EVENT_AND_ACTIVIST lens surfaced catalyst
- Event types: Strategic review, 13D filing, asset sale, refinancing
- Timing: Catalysts identified but impact/timing unclear
- Action: Monitor SEC filings and news
- Expected horizon: Catalyst-dependent (30-180 days typical)
- Queue size: Up to 20 candidates

Example: "13D accumulation by activist, 5.1% stake disclosed 6 weeks ago, meeting held last week, expect announcement in 2-4 weeks"

**8. SPECIAL_SITUATION**
- Discovery: Multiple conflicting lens signals
- Thesis complexity: Requires detailed case-by-case analysis
- Action: Schedule deep research session
- Example drivers: Restructuring with activist, industry recovery + capital return, M&A rumor + management dispute
- Queue size: Up to 10 candidates

Example: "Bankruptcy emerging from distressed restructuring, activist pushing exit strategy, industry recovery beginning"

**9. HUMAN_HYPOTHESIS**
- Author: Named researcher
- Thesis: Structured, text-based
- Allocation influence: Zero (research-only until promoted)
- Action: Track against market for hypothesis validation
- Status: Not in automatic Top Five
- Queue size: As authored by research team

Example: "Management change signals strategic shift; expect margin expansion 200bps over next 2 years"

### Monitoring & Exclusions

**10. CURRENT_HOLDING_REVIEW**
- Status: Active position in portfolio
- Action: Thesis refresh, exit decision point monitoring
- Review frequency: Daily updates on thesis invalidation, momentum, alternatives
- Exclusion from research pipeline (covered separately in Position Intelligence)

**11. WAITING_FOR_CONFIRMATION**
- Thesis complete but: Technical trigger not yet, catalyst timing unclear, or setup incomplete
- Action: Maintain on watchlist
- Review frequency: Daily technical, weekly fundamental
- Move trigger: Setup completion or catalyst timing clarity

Example: "Thesis sound but chart structure not yet complete; current price $48 but invalidation $40 = 20% risk; need support retest"

**12. HIGH_RISK_SPECULATIVE**
- Expected upside: Very high (100%+)
- Risk: Severe capital structure, execution, or governance concerns
- Rank caps: Capped at 20 max composite score
- Allocation eligibility: Zero during this sprint
- Action: Research-only, monitor for risk reduction
- Expected horizon: 6-12 months for resolution

Example: "Distressed restructuring with 3x equity upside if successful, but 50% bankruptcy risk; tracking covenant covenant waivers"

**13. EXCLUDED**
- Reasons recorded: Invalid data, stale data, untradeable liquidity, governance failure, critical risk
- Review frequency: Quarterly
- Move trigger: Reason resolved (e.g., liquidity tier improves)
- Archive: Permanent record in Evidence Ledger

Example: "Untradeable liquidity ($2K daily dollar volume), shelf registration active (dilution risk), related-party transactions (governance concern)"

---

## 8 INDEPENDENT DISCOVERY LENSES

Each lens runs independently, surfaces evidence, and populates marketplace queues. Lenses are **non-exclusive** (one opportunity can have multiple lenses).

### Lens A: ASYMMETRIC_EQUITY
**Purpose**: Surface micro-cap and small-cap candidates with 3x+, 5x+ or 10x equity scenarios

**Evidence captured**:
- Normalized revenue, EBITDA, EBIT, FCF scenarios
- Enterprise value calculation
- Capital stack waterfall
- Senior claims quantification
- Common equity value (bear/base/bull)
- Dilution sensitivity
- Realization horizon

**Example output**: "EV $50M, 2x normalized FCF ($3M) = $6M equity value = $15/share (2x from $7); bear case $8 (breakeven), base case $15, bull case $25"

**Scoring**: 0-100 based on:
- Clarity of scenarios (50 points max)
- Scenario probability assessment (30 points max)
- Survivor­ability in bear case (20 points max)

**Action**: If score ≥ 60, add to ASYMMETRIC_VALUE_RESEARCH queue

---

### Lens B: SURVIVABILITY_AND_CAPITAL_STACK
**Purpose**: Confirm equity survives until catalyst

**Evidence captured**:
- Cash and liquidity position (absolute and runway)
- Debt schedule and maturities
- Interest coverage ratio
- Covenant compliance
- Refinancing gap and market access
- Preferred and senior claims
- Dilution scenarios
- Restructuring risk

**Example output**: "Cash $15M runway 18 months at current burn; senior debt $60M matures 2028 (refinanceable); equity survives across base/bear"

**Scoring**: 0-100 based on:
- Runway sufficiency (40 points)
- Senior claims manageable (35 points)
- Covenant compliance (25 points)

**Action**: If score ≥ 70, eligible for ASYMMETRIC_VALUE_RESEARCH and higher tiers

---

### Lens C: CHART_AND_RECOGNITION
**Purpose**: Detect completed technical setups with numeric provenance

**Evidence captured**:
- Weekly structure (base, cup, flat base, base-on-base, etc.)
- Weekly support/resistance levels (calculated from data)
- Weekly breakout level with distance to trigger
- Daily structure (continuation, reversal, breakout)
- Daily support/resistance with exact prices
- Relative strength vs. sector, market
- Relative volume (current vs. 20-day average)
- Invalidation level (where thesis breaks)
- Setup extension (how extended is move after trigger)

**Example output**: "Cup and handle: weekly high 102, current 101, support 98 (recent low), weekly base well-defined 12 weeks, invalidation 97, extended 0 (not yet triggered)"

**Scoring**: 0-100 based on:
- Setup quality (40 points: defined support, resistance, clear structure)
- Trigger proximity (30 points: how close to breakout)
- Relative strength/volume confirmation (30 points)

**Action**: If score ≥ 65, add to CHART_MOMENTUM_RESEARCH queue

---

### Lens D: CORPORATE_EVENT_AND_ACTIVIST
**Purpose**: Surface catalysts with documented timeline and impact

**Evidence captured**:
- SEC filing type (10-K, 10-Q, 8-K, 13D, Form 4, proxy)
- Announcement date and available_at timestamp
- Event classification (strategic review, asset sale, restructuring, etc.)
- Materiality assessment (high/moderate/low)
- Timeline/milestones
- Insider transactions (Form 4: buyer/seller, quantity, price)
- Activist positions (13D, amended 13D timing, accumulation plan)
- Source documents with point-in-time lineage

**Example output**: "Activist 13D filed March 1 (5.1% stake disclosed); meeting held April 15; expect announcement Q2 2026; Form 4 insiders buying mid-market prices"

**Scoring**: 0-100 based on:
- Event materiality (50 points)
- Timeline clarity (30 points)
- Corroborating evidence (insider action, regulatory filings) (20 points)

**Action**: If score ≥ 60, add to EVENT_ACTIVIST_RESEARCH queue

---

### Lens E: EXPECTATIONS_AND_REVISIONS
**Purpose**: Track estimate momentum and expectation gaps

**Evidence captured**:
- Consensus revenue, EBITDA, EPS
- Estimate revisions (up/down 1, 3, 6 months)
- Estimate dispersion (std dev of analyst estimates)
- Company guidance (offered and track record)
- Alpha Velocity scenarios (bear/base/bull vs. consensus)
- Normalized earnings bridges
- Expectation gaps (when reality beats guidance)

**Example output**: "EPS revisions: +8% in 1-month (15 analysts), +5% in 3-month (consensus rising); company guidance conservative historically (beat by 8% on average)"

**Scoring**: 0-100 based on:
- Revision momentum (40 points)
- Estimate dispersion (bullish signal: narrow despite recent revisions) (30 points)
- Normalized earnings opportunity (30 points)

**Action**: If score ≥ 65 and revisions positive, add to ASYMMETRIC_VALUE_RESEARCH

---

### Lens F: MANAGEMENT_LANGUAGE_CHANGE
**Purpose**: Detect material thesis changes in filings and calls

**Evidence captured**:
- Filing types: Current quarter call vs. prior quarter, 10-Q vs. prior 10-Q
- Metrics discussed: Demand, pricing, backlog, margins, costs, liquidity
- Tone and language: Material shifts in emphasis
- Source passages: Direct quotes with timestamps
- Recency: Is this change recent or established?

**Example output**: "Q2 call: management stated 'pricing has stabilized' vs. Q1 'pricing pressure intensifying'; margin guidance raised 150bps on cost efficiency"

**Scoring**: 0-100 based on:
- Magnitude of language shift (50 points)
- Economic consequence of shift (30 points)
- Recency and corroboration (20 points)

**Action**: If score ≥ 70 and shift is positive, add to ASYMMETRIC_VALUE_RESEARCH

---

### Lens G: TOP_DOWN_MARKET_AND_INDUSTRY
**Purpose**: Rank sectors and select best companies within improving groups

**Evidence captured**:
- Sector performance (absolute, relative to market)
- Performance acceleration (accelerating up or decelerating down)
- Industry breadth (how many stocks participating)
- Volume participation (spreading across names or concentrated)
- Estimate revision breadth (industry vs. stock specific)
- Margin trends (improving or deteriorating across group)
- Pricing power and competitive dynamics
- Industry-specific leading indicators

**Example output**: "Semiconductor complex up 12% YTD vs. SPY +8%; acceleration accelerating; 80% of constituents positive; estimate revisions +6% across group; Company X has highest FCF margin (28%) and best absolute performance (+18%)"

**Scoring**: 0-100 based on:
- Sector strength (40 points)
- Company positioning within group (40 points)
- Relative upside within group (20 points)

**Action**: If score ≥ 70, add to TOP_DOWN_INDUSTRY_RESEARCH queue

---

### Lens H: TURTLE_TREND_RESEARCH_LENS (Experimental, Zero Production Influence)
**Purpose**: Trend-following channel breakout principles as independent research opinion

**Evidence captured**:
- Shorter breakout (20-day channel)
- Longer breakout (55-day channel)
- ATR/volatility-normalized sizing
- Channel exit (opposite direction)
- Trend maturity (how many bars extended)
- ATR state (volatility compression vs. expansion)

**Example output**: "20-day high 102.50, 55-day high 103.20, 20-day low 98.50, 55-day low 97.00; channel breakout trigger at 103.21 (above 55-day high); ATR 1.8 (not contracted, normal)"

**Scoring**: 0-100 based on:
- Channel clarity (40 points)
- Volatility normalization (30 points)
- Trend maturity (30 points)

**Action**: If score ≥ 60, add to CHART_MOMENTUM_RESEARCH as secondary lens

**IMPORTANT**: Turtle Trend has ZERO influence on production allocation this sprint. Integrated only as research opinion.

---

## OPPORTUNITY CANDIDATE CLASSIFICATION

Each opportunity receives:

```python
OpportunityCandidateClassification(
    opportunity_id="OPP-001",
    symbol="TEST",
    observation_time=datetime(...),
    marketplace_queues=(
        MarketplaceQueue.ACTIONABLE_TRIGGERED,
        MarketplaceQueue.ASYMMETRIC_VALUE_RESEARCH,  # Can be in multiple
    ),
    discovery_lenses=(
        DiscoveryLens(
            lens_type=DiscoveryLensType.CHART_AND_RECOGNITION,
            discovery_score=82.5,
            evidence_summary="Cup and handle, 12 weeks, relative strength +1.2x"
        ),
        DiscoveryLens(
            lens_type=DiscoveryLensType.ASYMMETRIC_EQUITY,
            discovery_score=75.0,
            evidence_summary="3x normalized FCF, $15 target vs. $7 current"
        ),
    ),
    structured_thesis=StructuredThesis(
        why_surfaced="Identified by 2 independent lenses",
        primary_repricing_mechanism="FCF recovery + multiple expansion",
        business_or_asset_value_thesis="Mature company with normalized 25% margins possible",
        survivability_conclusion="18+ month runway, debt manageable",
        market_misunderstanding="Market underappreciating margin recovery visibility",
        catalyst_description="Q3 earnings on August 1; expect beat + raised guidance",
        required_confirmation="Price stays above weekly support (98); earnings beat by >5%",
        invalidation_condition="Break below 97; guidance cut or margin compression",
        confidence_score=0.75,
    ),
    liquidity_tier=LiquidityTier.TRADEABLE_SMALL_CAP,
    research_confidence=78.0,
    opportunity_attractiveness=72.5,  # Ranking score
    is_actionable=True,
    top_five_eligible=True,
    top_five_rank=2,
)
```

---

## COMMITTEE INTEGRATION

The Daily Investment Committee receives marketplace-organized opportunities:

```
Warehouse Data
    ↓
Market Intelligence Scanner (qualified securities)
    ↓
Ranking Engine (scored opportunities)
    ↓
Opportunity Marketplace (classified into queues & lenses)
    ↓
Committee Orchestrator:
    - Extract Top Five
    - Set fallback_research_mode if no actionable candidates
    - Pass to Risk Review
    - Pass to Governance Review
    - Await Human Approval
    ↓
Evidence Ledger Records
    ↓
Paper Execution (if approved)
```

**Morning Report sections**:
- Market regime summary
- Sector and industry map (top performers, revisions, momentum)
- Top 10 overall opportunities (highest expected value)
- Committee Top Five (proposed allocation)
- Actionable opportunities (count, symbols, attractiveness scores)
- Starter candidates (count, symbols)
- Near triggers (count, symbols, distance to trigger)
- Asymmetric-value queue (count, representative symbols)
- Chart and recognition queue (count, representative symbols)
- Top-down industry queue (count, leading sectors)
- Event and activist queue (count, catalysts coming)
- Special situations (count, brief descriptions)
- Human hypotheses (count, authors)
- Current holdings review (thesis refresh status)
- Exclusions with counts and primary reasons
- Target allocation including cash
- Risk review results
- Governance review results
- Human approval state

---

## SAMPLE MARKETPLACE

Sample mode includes:
- 15 diverse securities (mix of liquidity tiers)
- 5-6 ACTIONABLE_TRIGGERED or STARTER_POSITION candidates
- 2-3 NEAR_TRIGGER candidates
- 3-4 ASYMMETRIC_VALUE_RESEARCH candidates
- 2-3 CHART_MOMENTUM_RESEARCH candidates
- 1-2 TOP_DOWN_INDUSTRY_RESEARCH candidates
- 1 EVENT_ACTIVIST_RESEARCH candidate
- 1 SPECIAL_SITUATION candidate
- 1 HUMAN_HYPOTHESIS candidate
- 1-2 EXCLUDED candidates (with reasons)
- Exactly 5 Committee Top Five

All labeled: `source="SAMPLE_DATA"` to prevent accidental live execution.

---

## KNOWN LIMITATIONS

**Data availability challenges**:
- Live market data ingestion not yet implemented
- Options and ownership data structure incomplete
- Transcript analysis requires external provider
- Activist database requires Bloomberg/CapitalIQ
- Estimate revisions require consensus provider

**Model limitations**:
- Turtle Trend: Zero influence until futures infrastructure complete
- Sentiment/alternative data: Shadow-only
- Machine learning models: Not yet validated on real outcomes
- Language change detection: Pattern-based, not semantic NLP

**Operational constraints**:
- Sample data only; real data provider requirements document needed
- Committee workflow reaches HUMAN_APPROVAL_PENDING, not execution
- Paper execution only (no live broker path)
- Outcome grading awaits forward-return data

---

## DOCUMENTATION REFERENCES

See also:
- [INVESTMENT_PHILOSOPHY.md](INVESTMENT_PHILOSOPHY.md) - Research framework
- [ARCHITECTURE.md](ARCHITECTURE.md) - Frozen dependency chain
- [docs/OPPORTUNITY_DOSSIER.md](docs/OPPORTUNITY_DOSSIER.md) - Detailed structure
- [docs/MARKET_LEADER_LABELS.md](docs/MARKET_LEADER_LABELS.md) - Evaluation labels
- [docs/TRADE_HYPOTHESIS_LAB.md](docs/TRADE_HYPOTHESIS_LAB.md) - Human hypothesis framework

---

**Status**: Production-ready for supervised paper trading  
**Test Coverage**: 27 tests passing  
**Integration**: Patched into existing scanner, no duplicates  
**Next**: Live data ingestion, outcome grading validation
