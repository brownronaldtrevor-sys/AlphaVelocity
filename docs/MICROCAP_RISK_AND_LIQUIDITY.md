# Micro-Cap Risk Intelligence & Liquidity Tiers

**Date**: 2026-07-16  
**Scope**: Micro-cap and small-cap securities (< $5B market cap)  
**Purpose**: Track execution risk and position-sizing constraints

---

## LIQUIDITY TIERS

Securities classified by average daily dollar volume (20-day average):

### Tier 1: INSTITUTIONALLY_LIQUID
- ADDY: > $10M per day
- Characteristics: Typically $1-3B market cap, major indices
- Position sizing: Up to 5% of portfolio value
- Entry strategy: Market or better orders
- Exit strategy: Market orders within 1 day
- Spread: Typically < 1 bps
- Slippage: < 2 bps typical

### Tier 2: TRADEABLE_SMALL_CAP
- ADDY: $2M-$10M per day
- Characteristics: $300M-$1B market cap, liquid small-caps
- Position sizing: Up to 3% of portfolio value
- Entry strategy: Limit orders, scale over 2-3 days
- Exit strategy: Limit orders over 1-3 days
- Spread: 2-5 bps typical
- Slippage: 3-5 bps typical

### Tier 3: LIMITED_CAPACITY
- ADDY: $500K-$2M per day
- Characteristics: $100M-$300M market cap
- Position sizing: Up to 1% of portfolio value
- Entry strategy: Limit orders, scale over 3-5 days
- Exit strategy: Limit orders over multiple days
- Spread: 5-20 bps typical
- Slippage: 10-20 bps typical

### Tier 4: STARTER_ONLY
- ADDY: $100K-$500K per day
- Characteristics: $20M-$100M market cap, micro-caps
- Position sizing: Up to 0.5% of portfolio value
- Entry strategy: Limit orders, patient accumulation over 5-10 days
- Exit strategy: Limit orders, may take 2-4 weeks to unwind
- Spread: 20-50 bps typical
- Slippage: 30-50 bps typical

### Tier 5: RESEARCH_ONLY
- ADDY: $10K-$100K per day
- Characteristics: < $20M market cap, nano-caps
- Position sizing: 0% in production portfolio
- Allocation: Research and learning only
- Entry: Hypothetical analysis
- Exit: No realistic exit strategy

### Tier 6: UNTRADEABLE
- ADDY: < $10K per day
- Characteristics: Shell companies, penny stocks, distressed
- Position sizing: 0% (hard exclusion)
- Allocation: Excluded from marketplace

---

## MICRO-CAP WARNING SIGNALS

### Equity Structure Risks

**Shelf registration active** → Dilution risk
- Check: SEC EDGAR shelf status
- Impact: Expected equity dilution
- Action: Monitor quarterly dilution impact
- Threshold: Hard warning if >20% annual dilution expected

**At-the-market (ATM) offering active** → Ongoing dilution
- Check: SEC 424B5 filings
- Impact: Floating-supply headwind
- Action: Cap position size to 0.5% max
- Threshold: Hard exclusion if ATM proceeds > 30% current market cap

**Warrants outstanding** → Future dilution
- Check: Merger docs, annual reports
- Impact: Dilution upon warrant exercise
- Action: Model diluted share count
- Threshold: Hard exclusion if warrant overhang > 20% of shares

**Convertible debt** → Future dilution option
- Check: Debt schedule, conversion terms
- Impact: Dilution if conversion occurs
- Action: Model diluted scenarios
- Threshold: Hard exclusion if conversion in-the-money > 10%

**Repeated equity issuance** → Pattern of dilution
- Check: Historical equity rounds
- Impact: Structural shareholder value destruction
- Action: Hard exclusion if >3 equity raises in past 3 years
- Threshold: Hard exclusion (violates capital structure survivability)

---

### Stock Structure Risks

**Reverse splits** → Distress signal
- Check: Stock split history
- Impact: Psychological resistance at round numbers
- Action: Hard exclusion if reverse split <1 year ago
- Threshold: Hard exclusion (signals distressed capital structure)

**Low float** → Manipulation risk
- Check: Shares outstanding vs. public float
- Impact: High volatility, easier to manipulate
- Action: Hard exclusion if float < $1M
- Threshold: Hard exclusion (illiquidity + manipulation risk)

**Extreme dilution** → Shareholder destruction
- Check: Share count over time
- Impact: Per-share value deterioration
- Action: Hard exclusion if annualized dilution > 30%
- Threshold: Hard exclusion (capital structure broken)

---

### Governance & Control Risks

**Related-party transactions** → Conflict of interest
- Check: Proxy statements, 10-K disclosures
- Impact: Transactions may not be at market terms
- Action: Hard warning, reduce confidence
- Threshold: Hard exclusion if material without disclosure

**Auditor concerns** → Data integrity risk
- Check: Auditor qualifications, changes
- Impact: May indicate hidden problems
- Action: Hard exclusion if auditor qualified opinion or resignation
- Threshold: Hard exclusion

**Internal control failures** → Accounting risk
- Check: 404 attestation, management certifications
- Impact: May hide material issues
- Action: Hard exclusion if material control deficiency
- Threshold: Hard exclusion

**Paid promotion** → Conflict of interest
- Check: SEC EDGAR promoter filings
- Impact: May distort retail participation
- Action: Hard warning if identifiable
- Threshold: Hard warning (not hard exclusion, but major confidence reduction)

---

### Market Microstructure Risks

**Abnormal price/volume spikes** → Potential manipulation
- Check: Technical analysis, trading patterns
- Impact: May indicate artificially elevated prices
- Action: Hard warning, avoid entry on spikes
- Threshold: Hard warning (no hard exclusion, but avoid entry during spike)

**Borrow stress signals** → Short squeeze risk
- Check: Shares on loan, borrow rates > 5%
- Impact: Short covering may be artificial catalyst
- Action: Hard warning if short interest > 30%
- Threshold: Hard warning (track separately from fundamental thesis)

**Promotional social activity** → Retail pump signals
- Check: StockTwits, Reddit, Twitter engagement spikes
- Impact: May indicate retail speculation separate from fundamentals
- Action: Shadow-only evidence (not allowed in hard scoring)
- Threshold: No hard impact (research-only alert)

---

## CONFIDENCE ADJUSTMENTS FOR MICRO-CAP WARNINGS

Base research confidence scores are adjusted:

| Warning | Adjustment | Impact |
|---------|-----------|--------|
| Shelf registration active | -10 points | Reduces confidence, stay lower position size |
| ATM offering active | -15 points | Larger reduction, consider exclusion |
| Warrant overhang > 20% | -10 points | Reduces confidence |
| Reverse split < 1 year | Exclusion | Hard exclusion |
| Float < $1M | Exclusion | Hard exclusion |
| Auditor qualified opinion | Exclusion | Hard exclusion |
| Material related-party TX | Exclusion | Hard exclusion |

---

## POSITION SIZING FRAMEWORK FOR MICRO-CAPS

```
Max Position Size = min(
    Liquidity Tier Cap,           # e.g., 1% for LIMITED_CAPACITY
    Expected Swing Value × 2,     # Higher conviction → higher sizing
    Volatility Budget / Asset,    # Risk-adjusted
    Market Impact Budget / 50 bps, # Spread/slippage cost
    Confidence × Attractiveness,  # Both must be high
) * (1 - Micro Cap Penalty)

Micro Cap Penalty = Sum of warning adjustments / 100
```

**Example**:
- Security: JELD, LIMITED_CAPACITY tier (1% max)
- Expected swing value: 0.75 (75 points)
- Volatility adjusted: 0.8%
- Liquidity impact: 0.9% (spread + slippage)
- Confidence: 0.65 (65 points, mild shelf warning)
- Attractiveness: 0.72 (72 points)

Max = min(1.0, 1.5, 0.8, 0.9, 0.65*0.72) * (1-0.1) = min(1.0, 1.5, 0.8, 0.9, 0.47) * 0.9 = **0.42% position size**

---

## EXECUTION SLIPPAGE MODELING

For micro-caps, expected slippage on fills:

| Tier | Entry Model | Exit Model | Spread | Implementation Shortfall |
|------|-----------|----------|--------|-------------------------|
| Institutional | AON, 1-3 days | Same-day | 1-2 bps | 2 bps |
| Small-Cap | Limit over 3 days | 1-3 days | 5 bps | 7 bps |
| Limited Cap | Limit over 5 days | 3 days | 15 bps | 25 bps |
| Starter | Limit over 10 days | 2-4 weeks | 40 bps | 80 bps |

These costs are deducted from expected swing value when calculating attractiveness.

---

## REAL CASH FLOW IMPACT

For a $10M portfolio with JELD (LIMITED_CAPACITY, 0.42% position = $42K):

```
Entry:
- Desired: 5,000 shares at $8.00 = $40,000
- Market: Bid $7.97, Ask $8.03
- Actual cost over 5 days: $7.98 average = $39,900
- Entry slippage: -$100 (-0.25%)

Exit after 30 days:
- Price target: $10.00 = $50,000
- Exit over 3 days into $9.95-$10.05 market
- Actual proceeds: $9.92 average = $49,600
- Exit slippage: -$400 (-0.40%)

Total net after costs:
- Target: $50,000 (25% gain)
- Actual: $49,600 - $39,900 = $9,700 (24.3% gain)
- Implementation shortfall: 0.70% (slippage + spread)
```

---

## MONITORING & REAL-TIME UPDATES

Daily:
- ADDY update (20-day rolling average)
- Float monitoring (any sudden changes indicate restructuring)
- Borrow rate tracking (micro-caps especially vulnerable to squeezes)
- Technical: Support/resistance invalidation alerts

Weekly:
- SEC filing check (8-K, shelf updates, Form 4)
- Activist position tracking (13D amendments)
- Auditor status verification

Quarterly:
- Full liquidity tier re-evaluation
- Dilution impact assessment
- Capital structure refresh

---

## HARD EXCLUSIONS FOR MICRO-CAP RISKS

Automatically exclude:
1. Average daily dollar volume < $10,000
2. Float < $1,000,000
3. Auditor qualified opinion or resignation
4. Reverse split within 12 months
5. Internal control material deficiency
6. Related-party transaction without disclosure
7. Warrant overhang > 30% in-the-money
8. Reverse stock split + AT-the-market offering combination

---

## SUMMARY

Micro-cap trading requires disciplined risk management beyond standard portfolio constraints. Liquidity tiers drive position sizing, execution timing, and exit flexibility. Governance and capital structure risks disproportionately affect small companies—careful monitoring is essential.

**Remember**: Liquidity, not just return potential, determines position viability.
