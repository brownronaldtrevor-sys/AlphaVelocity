# Turtle Trend Strategy - Experimental & Deferred

**Status**: UNCALIBRATED, DISABLED BY DEFAULT  
**Location**: `alpha_velocity/experimental_strategies/turtle_trend/`  
**Influence**: ranking_influence = 0.0, allocation_influence = 0.0  
**Date**: 2026-07-16  

---

## Overview

The Turtle Trend strategy, formerly co-registered with Swing Repricing in the Alpha Lab, has been moved to the experimental_strategies directory as part of the Alpha Velocity Equity Intelligence consolidation.

**Current Status**:
- Source code retained (learning continuity)
- NO registration in Daily Investment Committee
- NO futures data ingestion in active equity workflow
- NO futures orders generated
- ZERO influence on equity ranking and allocation
- Separate research program deferred to future implementation

---

## Rationale for Experimental Status

### Infrastructure Separation

Futures require different data ingestion, management, and risk control than equities:

1. **Data Ingestion**
   - Continuous series & contract rolls (not standard equities)
   - Liquidity & open interest (not equity volume measures)
   - Margin requirements & settlement (different from equity T+2)
   - Volatility regimes (more extreme than equities)

2. **Position Management**
   - Portfolio margin (vs. buying power in equities)
   - Contract expiration & mandatory roll dates
   - Position size constraints (different calculation)
   - Intraday margin calls
   - Settlement procedures

3. **Risk Control**
   - Correlation with equity portfolio (unestablished)
   - Hedge ratio calculation (not yet determined)
   - Systematic portfolio drift (from rolling contracts)
   - Liquidity during gaps (different from equities)
   - Slippage in 24-hour markets

### Validation Requirements

Before integrating Turtle Trend with equity decisions, these must be complete:

1. **Data Quality**
   - Point-in-time continuous series with roll dates
   - Accurate open interest & volume metrics
   - Margin requirement feeds
   - Verified against CBOE, CME data

2. **Strategy Validation**
   - Backtesting on 10+ years of data
   - Drawdown & correlation analysis
   - Contract-roll handling validation
   - Slippage adjustment accuracy
   - Hit rate & payoff ratio calibration

3. **Portfolio Integration**
   - Correlation with equity holdings (by regime)
   - Hedge effectiveness (expected vs. realized)
   - Margin impact on equity capacity
   - Position-sizing interaction
   - Execution feasibility

4. **Execution Testing**
   - Paper trading (3+ months) with realistic fills
   - Partial fill handling
   - Market impact estimation
   - Slippage validation
   - Commission accuracy

5. **Risk Approval**
   - Separate risk policy for futures
   - Margin availability protocols
   - Hard stops for margin exceedance
   - Liquidation rules
   - Volatility & exposure caps

---

## Current Code Location

**Main Strategy**: `alpha_velocity/experimental_strategies/turtle_trend/strategy.py`

**Module Init**: `alpha_velocity/experimental_strategies/turtle_trend/__init__.py`

**Documentation**: This file

---

## Strategy Summary

### Hypothesis

*Capture disciplined trend-following entries using channel breakouts, pyramid systematically with volatility-based sizing, and exit using countertrend or trailing-stop rules to capture the safe middle portion of trends while avoiding tops and bottoms.*

### Parameters

```python
shorter_breakout_bars = 20   # 20-day channel (faster breakout)
longer_breakout_bars = 55    # 55-day channel (trend confirmation)
atr_period = 20              # Volatility normalization period
risk_per_unit_pct = 2.0      # Risk per contract unit
max_units = 4                # Maximum position size (units)
```

### Supported Asset Types

- Equity index futures (ES, NQ, etc.)
- Interest-rate futures (ZB, ZF, ZN, etc.)
- Currency futures (6E, 6J, etc.)
- Energy futures (CL, NG, etc.)
- Metal futures (GC, SI, etc.)
- Agricultural futures (ZW, ZC, ZS, etc.)
- Soft commodities (KC, SB, CT, etc.)
- Livestock futures (LE, LH, GF, etc.)

### Entry Logic

1. **Calculate channel breakouts**:
   - Shorter breakout (20-day high/low) for fast entry
   - Longer breakout (55-day high/low) for trend confirmation

2. **Assess volatility**:
   - Calculate 20-period ATR (Average True Range)
   - Normalize position size: risk_per_unit_pct / ATR

3. **Entry trigger**:
   - Long breakout: Close > 55-day high (with 20-day confirmation)
   - Short breakout: Close < 55-day low (with 20-day confirmation)
   - Volume confirmation required

4. **Pyramid strategy**:
   - First unit: On confirmed breakout
   - Subsequent units: At progressive breakout levels (max 4 units)
   - Scaling reduces risk per unit as trend gains traction

### Exit Logic

1. **Hard stop**: Invalidation level (opposite channel)
2. **Trailing stop**: Breakout of shorter lookback (20-day) in opposite direction
3. **Profit protection**: Time-based (exit if trend stalls after N bars)
4. **Volatility stop**: Extreme ATR expansion

---

## Why Not Yet Active

### Missing Futures Infrastructure

Current Active Equity workflow cannot safely accommodate futures without:

1. **Data Layer**
   - Continuous series transformation (roll dates, splits)
   - Margin requirement ingestion
   - Open interest tracking
   - Realistic slippage tables

2. **Order System**
   - Contract specification (multiplier, point value, decimal places)
   - Margin calculation in order sizing
   - Expiration enforcement
   - Roll management (close near leg, open far leg)

3. **Risk Layer**
   - Margin availability protocol
   - Intraday margin requirement handling
   - Position liquidation rules
   - Correlation-based hedge ratio

4. **Execution Layer**
   - 24-hour trading hour support (E-mini markets)
   - Afterhours liquidity handling
   - Contract roll execution
   - Liquidity forecasting (open interest decline pre-expiration)

---

## Path to Activation

### Phase 1: Data Integration (Week 1-2)
- [ ] Continuous series data ingestion (CME, CBOE)
- [ ] Open interest & volume tracking
- [ ] Margin requirement feeds
- [ ] Point-in-time validation

### Phase 2: Strategy Validation (Week 3-8)
- [ ] Backtesting on 10+ year dataset
- [ ] Correlation analysis vs. equity holdings
- [ ] Hit rate & payoff ratio calibration
- [ ] Drawdown analysis
- [ ] Parameter sensitivity analysis

### Phase 3: Paper Trading (Week 9-14)
- [ ] 3+ months simulated trading
- [ ] Slippage validation
- [ ] Margin management testing
- [ ] Execution quality analysis
- [ ] Risk approval finalization

### Phase 4: Risk & Governance (Week 15-16)
- [ ] Risk policy development
- [ ] Margin availability protocols
- [ ] Liquidation rules
- [ ] Volatility & exposure caps
- [ ] Governance approval

### Phase 5: Integration (Week 17-20)
- [ ] Portfolio-level margin calculation
- [ ] Hedge ratio incorporation
- [ ] Position intelligence extension
- [ ] Integrated risk approval
- [ ] Execution system integration

---

## How to Re-Enable (for Research)

**To use Turtle Trend for experimental research only**:

```python
# Import from experimental
from alpha_velocity.experimental_strategies.turtle_trend.strategy import TurtleTrendStrategy

# Create engine with experimental strategy
engine = AlphaLabEngine()
engine.register_strategy(TurtleTrendStrategy())

# Run (generates candidates with zero influence on production allocation)
result = engine.run(warehouse=warehouse, observation_time=now)

# Results logged separately for validation
# NO integration with Daily Committee
# NO impact on equity ranking/allocation
```

**To enable in Daily Committee** (NOT RECOMMENDED without completion of Phase 1-5):

1. Move `strategies_turtle_trend.py` back to `alpha_velocity/alpha_lab/`
2. Update `alpha_velocity/alpha_lab/__init__.py` to re-export
3. Update `alpha_velocity/alpha_lab_main.py` to register by default
4. Update Daily Committee to include futures in data flows
5. Implement futures-specific margin & roll management
6. Complete validation & approval process

---

## Preserved History & Learning

The Turtle Trend source code is retained in full, enabling:

- Historical reference for strategy design patterns
- Learning from implementation experience
- Future research (pattern recognition, regime analysis)
- Institutional knowledge preservation

All Git history is retained. No code is silently deleted.

---

## Testing

Current test status:
- ✅ Alpha Lab tests: 18/18 passing (Swing Repricing only)
- ✅ Full suite: 229/229 passing
- ✅ Turtle Trend: NOT registered, NOT executed
- ✅ No futures influence on equity workflow

---

## Questions & Contact

For questions on re-enabling Turtle Trend or futures research:
- See Phase 1-5 roadmap above
- Consult ARCHITECTURE.md for portfolio integration requirements
- Review Risk & Governance policies for margin requirements

---

**Deferred**: 2026-07-16  
**Status**: Preserved, Not Integrated  
**Influence**: Zero  
**Path Forward**: See Phase 1-5 roadmap above
