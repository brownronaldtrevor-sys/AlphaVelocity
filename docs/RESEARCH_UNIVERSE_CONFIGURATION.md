# Research Universe Configuration

Adaptive universes are configured through ScanConfig.research_universes with backward-compatible defaults.

## Per-Universe Configuration Fields
- universe_id
- name
- description
- universe_type
- membership_rules
- benchmark_ids
- enabled
- priority_mode
- capacity_limit
- minimum_liquidity
- minimum_data_quality
- minimum_candidate_count
- maximum_candidate_count
- tags
- schema_version

## Global ScanConfig Context
- user_watchlist_symbols
- current_holding_symbols
- benchmark_symbols

## Backward Compatibility
- If no research_universes are configured:
  - SAMPLE_DATA mode uses deterministic multi-universe defaults.
  - Non-sample mode uses a single BROAD_MARKET default universe.
- Existing configs continue to work unchanged.
