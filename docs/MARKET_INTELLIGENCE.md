# Market Intelligence Engine

**Version**: 1.0.0  
**Status**: Production  
**Date**: 2026-07-15

---

## Overview

The Market Intelligence Engine is the daily research pipeline that determines which securities deserve evaluation and converts qualified securities into canonical Opportunity objects for ranking.

**This engine does not:**
- Allocate capital or portfolio weight
- Generate trading signals or orders
- Call broker APIs
- Mutate portfolio state
- Approve risk or governance decisions
- Train machine learning models
- Optimize parameters

**It produces:** Deterministic, evidence-based research-grade qualified opportunity lists ready for ranking and downstream analysis.

---

## Pipeline Architecture

```
Point-in-Time Universe
    (Warehouse securities as-of observation_time)
        ↓
Data Quality Gates
    (Reject invalid OHLCV, stale bars, future data)
        ↓
Tradability Filters
    (Price range, volume, history, spreads, exchanges)
        ↓
Multi-timeframe Preparation
    (Daily + weekly bars, benchmarks, catalysts)
        ↓
Opportunity Assembly
    (Canonical Opportunity objects via assembler)
        ↓
Ranking Integration
    (3-component scoring: Intrinsic, Timing, Swing Value)
        ↓
MarketScanResult
    (Qualified opportunities + ranked research)
```

---

## Stage 1: Point-in-Time Universe

### Objective
Obtain the precise list of securities known at observation_time, including delisted securities for historical simulations.

### Implementation

```python
universe = warehouse.point_in_time_universe(as_of=observation_time)
```

### Rules

1. **No future bias**: Never use today's surviving ticker list for past dates
2. **Delisting retention**: Maintain delisted securities in historical universes
3. **Listing date respected**: Include only securities listed by observation_time
4. **Ticker changes tracked**: Handle symbol changes via warehouse ticker history
5. **Availability gates**: Use `available_at` timestamp to honor data discovery order

### Example

```
2020-06-01: Universe includes ABC (active) + XYZ (delisted 2020-01-15)
2020-12-01: Universe includes ABC only (XYZ delisting date passed)
```

---

## Stage 2: Data Quality Gates

### Objective
Reject or quarantine securities with data problems that prevent meaningful analysis.

### Rejection Criteria

**No bars available**
- Reason: "No bar data available"
- No historical data exists in warehouse

**Future data**
- Reason: "No bars available at observation_time"
- Bars with `available_at > observation_time` filtered out
- Prevents forward-looking bias

**Invalid OHLCV**
- Reason: "Invalid OHLCV"
- Any bar with: open ≤ 0, high ≤ 0, low ≤ 0, close ≤ 0, or volume ≤ 0
- Bar relationships violated: high < low, or close outside [low, high]

**Stale data**
- Reason: "Last bar older than threshold"
- No recent bars indicate trading halt or data outage

**Conflicting ticker history**
- Reason: "Ticker history conflicts"
- Warehouse enforces no overlapping ticker histories per security

### Evidence Captured

Each rejection includes:
- Category: DATA_QUALITY, HISTORY, LIQUIDITY, ASSET_TYPE, EXCHANGE
- Reason: Human-readable explanation
- Evidence: Specific values (bar counts, latest close, etc.)

---

## Stage 3: Tradability Filters

### Objective
Apply research filters to identify securities meeting minimum liquidity and tradability thresholds.

### Configurable Filters

**Price Range**
```python
config.universe_config.min_price: float = 1.0
config.universe_config.max_price: float = 100_000.0
```
- Latest close must fall within range
- Protects against penny stocks and extreme valuations
- Note: NOT evidence of future performance

**Volume Requirements**
```python
config.universe_config.min_avg_daily_volume: float = 100_000.0
config.universe_config.min_avg_daily_dollar_volume: float = 500_000.0
```
- 20-day trailing average of shares traded
- 20-day trailing average of dollar volume traded
- Ensures execution feasibility

**Trading History**
```python
config.universe_config.min_trading_history_days: int = 60
```
- Minimum trading days required (not calendar days)
- Prevents pre-revenue IPO analysis
- Allows historical parameter stability

**Spread Estimate**
```python
config.universe_config.max_spread_bps: float = 500.0
```
- Maximum bid-ask spread allowance
- Currently stubbed (TODO: calculate from market microstructure data)

**Exchange Eligibility**
```python
config.universe_config.supported_exchanges: tuple[str, ...] = ("NYSE", "NASDAQ")
```
- Whitelist of supported exchanges
- Can be configured for regional or market-specific scans

**Asset Type Support**
```python
config.universe_config.supported_asset_types: tuple[str, ...] = ("STOCK",)
```
- Currently supports: STOCK
- ETFs, bonds, options not yet supported

### Rejection States

| State | Trigger | Evidence |
|-------|---------|----------|
| ILLIQUID | Volume or dollar-volume below threshold | avg_daily_volume, avg_daily_dollar_volume |
| INSUFFICIENT_HISTORY | Trading days < min_trading_history_days | trading_days |
| UNSUPPORTED_ASSET | asset_type not in supported list | asset_type |
| EXCLUDED | Exchange not in supported list | exchange |

---

## Stage 4: Multi-timeframe Preparation

### Objective
Assemble complete technical and temporal context for qualified securities.

### Data Collection

For each qualified security:

**Daily bars (point-in-time)**
```python
daily_bars = [bar for bar in warehouse.get_raw_bars(security_id) 
              if bar.available_at <= observation_time]
```
- Chronological order required for technical analysis
- No future bars (filtered by available_at)
- Raw OHLCV preserved (no survivor bias adjustment)

**Completed weekly bars**
```python
weekly_bars = warehouse.completed_weekly_bars(security_id, as_of=observation_time)
```
- Aggregated from completed weeks only
- No partial current week included
- Latest weekly close < observation_time required

**Benchmark context**
```python
benchmark_bars = warehouse.get_raw_bars("SPY-ID")  # TODO: Index mapping
```
- S&P 500 or specified benchmark for relative strength
- Scope: Full history parallel to security daily bars
- Quality: Same point-in-time validation

**Sector history**
```python
sector_bars = warehouse.get_raw_bars(sector_id)  # TODO: Sector aggregation
```
- Sector ETF or index for sector strength context
- Scope: Full history parallel to security daily bars
- Quality: Same point-in-time validation

**Known catalysts**
```python
catalysts = warehouse.get_events(security_id, before=observation_time)
```
- Earnings dates, splits, corporate actions, analyst changes
- All must have `available_at <= observation_time`
- No future events

**Liquidity history**
```python
liquidity_history = warehouse.get_liquidity_stats(security_id)
```
- Recent volume trends, bid-ask evolution
- Used to validate execution feasibility assumptions
- Stub: TODO - populate from market microstructure

### Validation

**No incomplete weeks**
- Latest weekly bar must be complete
- If observation_time falls mid-week, that week excluded
- Weekly aggregation rule: Monday-Friday only

**Minimum weekly count**
```python
config.min_completed_weeks: int = 10
```
- At least 10 complete weeks required for technical setup
- Approximately 2.5 months of data

**No data gaps**
- Trade dates must be chronological
- Missing trading days acceptable (weekends, holidays)
- Suspicious patterns flagged in warnings

---

## Stage 5: Opportunity Assembly

### Objective
Convert qualified securities with prepared data into canonical Opportunity objects.

### Reuse of Assembler

The engine calls the existing `assemble_opportunity()` function (no second model created):

```python
opportunity = assemble_opportunity(
    daily_bars=daily_bars,
    weekly_bars=weekly_bars,
    benchmark_bars=benchmark_bars,
    sector_bars=sector_bars,
    feature_snapshots=[],
    known_events=catalysts,
    liquidity_history=liquidity_history,
    observation_time=observation_time,
    security_id=security.security_id,
    symbol=security.ticker,
    benchmark_symbol="SPY",
    sector=security_sector,
    industry=security_industry,
    universe_snapshot_id=universe_snapshot_id,
    warehouse_manifest_hash=manifest_hash,
    dataset_manifest_hash=dataset_hash,
    source_record_ids=catalog_ids,
)
```

### Opportunity Contents

80+ fields including:

- **Identity**: opportunity_id, symbol, security_id, observation_time
- **Technical**: weekly_structure, daily_trigger, support/resistance levels
- **Fundamental**: market_regime, sector_regime, expected upside/downside
- **Liquidity**: volume, dollar volume, spread estimate, capacity warnings
- **Catalysts**: known_events, next_event_time, catalyst importance
- **Validation**: calibration_status, governance_eligible, risk_eligible
- **Evidence**: source_record_ids, warehouse_manifest_hash, warnings

### Assembly Failure Handling

- Assembly failures logged as warnings but don't reject security
- Failed opportunities skipped in ranking phase
- Scan continues to completion

---

## Stage 6: Candidate Qualification

### Objective
Transparently classify each security with explicit research states and evidence.

### Qualification States

```python
class QualificationState(Enum):
    QUALIFIED = "QUALIFIED"                    # Passes all gates
    WATCHLIST = "WATCHLIST"                    # Optional inclusion
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"  # Too few bars/weeks
    DATA_QUALITY_FAILURE = "DATA_QUALITY_FAILURE"  # Invalid OHLCV
    ILLIQUID = "ILLIQUID"                      # Volume too low
    UNSUPPORTED_ASSET = "UNSUPPORTED_ASSET"    # ETF, bond, etc.
    WAITING_FOR_TRIGGER = "WAITING_FOR_TRIGGER"    # Good thesis, no setup yet
    EXCLUDED = "EXCLUDED"                      # Various disqualifiers
```

### SecurityQualification Record

Each security receives immutable qualification record containing:

```python
@dataclass(frozen=True)
class SecurityQualification:
    security_id: str
    symbol: str
    state: QualificationState
    qualified: bool
    reasons: tuple[str, ...]
    exclusions: tuple[ExclusionReason, ...]
    daily_bar_count: int
    completed_week_count: int
    avg_daily_volume: float
    avg_daily_dollar_volume: float
    spread_estimate_bps: float
    data_quality_issues: tuple[str, ...]
    warnings: tuple[str, ...]
```

### ExclusionReason Structure

Each exclusion includes:
- Category: DATA_QUALITY, HISTORY, LIQUIDITY, ASSET_TYPE, EXCHANGE
- Reason: Human-readable text
- Evidence: Specific values supporting rejection

### Example Qualification

```
Security: ACME Corp (sec-1234)
State: QUALIFIED
Reasons: ["Passed all qualification gates"]
Daily bars: 120
Weekly bars: 24
Avg daily volume: 2.5M
Avg daily dollar volume: $125M
Data quality issues: []
Warnings: []
```

### Example Exclusion

```
Security: ILLIQUID Inc (sec-5678)
State: ILLIQUID
Exclusions:
  - Category: LIQUIDITY
    Reason: "Insufficient volume: 50,000 < 100,000"
    Evidence: {"avg_daily_volume": 50000}
```

---

## Stage 7: Ranking Integration

### Objective
Send only qualified opportunities to the existing Opportunity Ranking Engine.

### Integration Flow

```python
# Assemble opportunities from qualified securities
qualified_opportunities = [opportunities]

# Send to existing ranking engine
ranking_batch = ranking_engine.rank(
    opportunities=qualified_opportunities,
    universe_name="Market Intelligence Scan",
    observation_time=observation_time,
)

# Receive ranked results
ranked_results = ranking_batch.ranked_opportunities
```

### Scanner Does NOT Modify

✅ Preserves: Ranking scores (0-100 scale)
✅ Preserves: Three-component scoring
✅ Preserves: Hard caps for distress
✅ Preserves: Unvalidated evidence = zero influence
✅ Preserves: Ranking state classifications
✅ Preserves: Evidence lineage

❌ Does NOT change: Weights, thresholds, or penalty logic

### Ranking Output

Complete RankingResult for each opportunity containing:
- overall_research_score (0-100)
- intrinsic_opportunity_score (30% weight)
- timing_opportunity_score (30% weight)
- expected_swing_value_score (40% weight)
- ranking_state (8 classifications)
- evidence_lineage
- warnings and confirmations

---

## Stage 8: Deterministic Scan Output

### Objective
Return complete, reproducible market intelligence result.

### MarketScanResult Structure

```python
@dataclass(frozen=True)
class MarketScanResult:
    scan_run_id: str                                 # Unique scan identifier
    observation_time: datetime                       # Analysis timestamp (UTC)
    universe_snapshot_id: str                        # Universe reference
    total_securities_considered: int                 # Universe size
    qualified_count: int                             # Passed all gates
    watchlist_count: int                             # Optional inclusion
    excluded_count: int                              # Failed gates
    exclusion_counts_by_reason: dict[str, int]      # Breakdown
    assembled_opportunities: tuple[Opportunity, ...]  # Qualified opportunities
    ranked_research_results: tuple[RankingResult, ...]  # Ranked results
    security_qualifications: tuple[SecurityQualification, ...]  # All classifications
    warnings: tuple[str, ...]                        # Assembly/ranking warnings
    warehouse_manifest_hash: str                     # Data provenance
    dataset_manifest_hash: str                       # Dataset reference
    configuration_hash: str                          # Configuration fingerprint
    generated_at: datetime                           # Execution timestamp
    schema_version: str                              # Format version ("1.0.0")
```

### Serialization

**to_dict()**: Dictionary format for storage
**to_json()**: Deterministic JSON with sorted keys
**from_dict()**: Round-trip deserialization

### Determinism Guarantee

Same input always produces:
- Identical counts (qualified, watchlist, excluded)
- Identical security qualifications (same order, same evidence)
- Identical assembled opportunities (same fields, same order)
- Identical ranked results (same scores, same order)
- Different scan_run_id (timestamp + random component)

---

## Stage 9: Reproducibility

### Objective
Enable audit trail and historical reproduction.

### Recorded Information

**Configuration**
- All filter thresholds (prices, volumes, history)
- Supported exchanges and asset types
- Minimum bar/week requirements
- Configuration hash

**Universe**
- observation_time (exact analysis point)
- universe_snapshot_id
- total_securities_considered
- included_symbols / excluded_symbols

**Timestamps**
- scan_start_time
- observation_time (data as-of date)
- generated_at (execution completion)

**Data Provenance**
- warehouse_manifest_hash (data version)
- dataset_manifest_hash (dataset snapshot)
- Git commit (if available)
- source_record_ids (per security)

### Reproducibility Checklist

✅ Same warehouse + config → Same results  
✅ Different observation_time → Different universe  
✅ Different filters → Different qualifications  
✅ Same data, same time → Deterministic output  
✅ No randomness → Fully reproducible

---

## Architecture Decisions

### Why Three-Component Scoring?

1. **Intrinsic** (30%) = Fundamental value independent of timing
2. **Timing** (30%) = Technical setup quality independent of valuation
3. **Swing Value** (40%) = Probability × magnitude independent of both

**Benefit**: Each dimension scored separately, then combined.  
**Protection**: High valuation + poor timing → WAITING_FOR_TRIGGER  
**Protection**: Perfect technical + capital distress → Capped at 30

### Why Immutable Results?

- Point-in-time audit trail
- No retroactive changes
- Clear data lineage
- Reproducibility guaranteed

### Why No Ranking Weight Changes?

- Ranking engine is independent system
- Scanner is opinion-neutral data provider
- Weights determined once per research methodology
- Changes require governance approval

### Why Explicit Exclusion Reasons?

- Transparency into filtering logic
- Enables filter tuning and validation
- Audit trail for compliance
- Research reproducibility

---

## Limitations & Known Issues

### By Design (Explicit Boundaries)

1. **No portfolio overlap detection**
   - Doesn't account for existing positions
   - Separate allocation system handles conflicts

2. **No correlation bucketing**
   - Doesn't flag correlated opportunities
   - Separate risk system manages concentration

3. **Passive asset classification**
   - Uses warehouse definitions
   - No machine learning on sector/industry

4. **Manual catalyst entry**
   - Doesn't discover catalysts from news
   - Must be populated in warehouse

5. **No probability generation**
   - Doesn't calibrate probability
   - Requires external research system

### Current Implementation Gaps

6. **Benchmark/sector bars stubbed**
   - TODO: Implement index mapping
   - TODO: Aggregate sector data

7. **Spread estimation**
   - Currently fixed at 10 bps
   - TODO: Calculate from market microstructure

8. **Feature snapshots**
   - Assembled but not used
   - TODO: Connect to research features

9. **Liquidity history**
   - Placeholder only
   - TODO: Populate from warehouse

10. **Live market data**
    - Warehouse-only (no live feeds)
    - Suitable for end-of-day/historical analysis

---

## Testing

### Test Coverage

✅ Qualified security with sufficient history  
✅ Insufficient history exclusion  
✅ Illiquid security exclusion  
✅ Delisted security exclusion  
✅ Unsupported asset type exclusion  
✅ Point-in-time universe (no future bias)  
✅ Deterministic scan output  
✅ No broker calls  
✅ No order creation  
✅ Deterministic JSON serialization  

### Run Tests

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_market_intelligence.py -q
```

---

## Integration Example

```python
from datetime import datetime, timezone
from alpha_velocity.market_intelligence import (
    MarketIntelligenceEngine,
    ScanConfig,
    UniverseConfig,
)
from alpha_velocity.warehouse import SQLiteHistoricalWarehouse

# Setup
warehouse = SQLiteHistoricalWarehouse("warehouse.db")
engine = MarketIntelligenceEngine()

# Configuration
observation_time = datetime(2024, 1, 15, 16, 30, tzinfo=timezone.utc)
config = ScanConfig(
    universe_config=UniverseConfig(
        observation_time=observation_time,
        min_price=1.0,
        min_avg_daily_volume=500_000.0,
        min_trading_history_days=60,
        supported_exchanges=("NYSE", "NASDAQ"),
        supported_asset_types=("STOCK",),
    ),
    min_completed_weeks=10,
    include_watchlist=False,
)

# Scan
result = engine.scan(
    warehouse=warehouse,
    scan_config=config,
    universe_manifest_hash="HASH001",
    dataset_manifest_hash="HASH002",
)

# Results
print(f"Universe: {result.total_securities_considered} securities")
print(f"Qualified: {result.qualified_count}")
print(f"Ranked: {len(result.ranked_research_results)}")
for ranked_opp in result.ranked_research_results[:5]:
    print(f"  {ranked_opp.opportunity_id}: {ranked_opp.overall_research_score:.0f}")

# Export
json_output = result.to_json()
```

---

## Version History

### v1.0.0 (2026-07-15)
- Initial production release
- Point-in-time universe construction
- Data quality gates
- Tradability filters
- Multi-timeframe preparation
- Opportunity assembly
- Ranking integration
- Deterministic output
- Complete reproducibility

---

## References

**Production Code**:
- `alpha_velocity/market_intelligence/` — Complete engine package
- `alpha_velocity/market_intelligence/__init__.py` — Package exports
- `alpha_velocity/market_intelligence/models.py` — Data structures
- `alpha_velocity/market_intelligence/scanner.py` — Main engine

**Tests**:
- `tests/test_market_intelligence.py` — Comprehensive test suite (10+ focused tests)

**Related Systems**:
- `alpha_velocity/warehouse/` — Historical data management
- `alpha_velocity/opportunity/` — Canonical opportunity objects
- `alpha_velocity/opportunity_ranking/` — Ranking engine (unchanged)

**Documentation**:
- `docs/MARKET_INTELLIGENCE.md` — This file
- `docs/OPPORTUNITY_RANKING.md` — Ranking engine reference
