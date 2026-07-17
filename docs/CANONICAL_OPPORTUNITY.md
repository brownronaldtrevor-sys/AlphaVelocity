# Canonical Opportunity v2.1

## Rule
Alpha Velocity has one authoritative investment opportunity model:
alpha_velocity/opportunity/models.py -> Opportunity.

Transport DTOs and specialized ranking inputs may exist in other modules, but they are not canonical investment opportunities.

## Thesis Versus Expression
- Thesis identity captures the investment idea.
- Expressions represent one or more ways to express that thesis.
- The security symbol remains backward compatible as the primary expression.

## Enrichment Surfaces
Opportunity now carries:
- thesis_identity
- expressions
- lifecycle
- four separate horizons
- recognition_profile
- claim_set for why_now/why_not_now
- change_windows
- assumptions
- invalidation_profile
- research_conviction and capital_conviction

## Serialization and Versioning
- Deterministic JSON via Opportunity.to_json.
- Stable enum serialization to string values.
- Backward-compatible loading with defaults for missing v2.1 fields.
- schema_version retained and persisted.

## Known Limitations
- This milestone adds deterministic structures and defaults, not adaptive intelligence.
- No Best Expression selection engine yet.
- No autonomous execution behavior introduced.

## Deferred Work
- Adaptive Research Universes
- Basket Intelligence
- Relationship Intelligence
- Best Expression Engine
- Research Allocation
- Intraday strategies
- Futures expansion
