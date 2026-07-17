# Adaptive Universes Quickstart

## 1. Run a scan with defaults
- In SAMPLE_DATA mode, adaptive universes are enabled automatically.
- In non-sample mode, a safe BROAD_MARKET default is used.

## 2. Provide explicit universes
Create ScanConfig with research_universes and optional watchlist/holdings/benchmark symbols.

## 3. Inspect outputs
Read from MarketScanResult:
- universe_diagnostics
- universe_priorities
- candidate_counts_by_universe
- overlap_across_universes
- merged_duplicate_candidates
- unique_canonical_opportunities

## 4. Verify downstream invariants
- Marketplace queues are preserved.
- Ranking remains backward-compatible.
- Committee Review List and Top Five behavior remain unchanged.
- No autonomous execution paths are introduced.

## Known Limitations
- Basket Intelligence deferred.
- Relationship Intelligence deferred.
- Best Expression Engine deferred.
- Research Allocation Engine deferred.
- Intraday strategies deferred.
- Futures expansion deferred.
