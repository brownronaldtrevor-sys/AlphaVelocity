# Project Constitution

## Purpose
AlphaVelocity exists to generate research-grade opportunity intelligence that is evidence-led, auditable, and safe for human committee decision-making.

## Non-Negotiables
- No autonomous live trading execution from committee outputs.
- Research outputs must be point-in-time safe.
- Missing or unvalidated evidence cannot be treated as favorable.
- New intelligence layers must extend existing architecture, not duplicate systems.
- Ranking influence from experimental intelligence stays shadow-only unless explicitly enabled.

## Intelligence v1 Principles
- Multi-horizon analysis is mandatory: research, primary repricing, tactical swing, and execution horizons remain independent.
- Inflection must be measured across multiple dimensions with synchronization and contradiction tracking.
- Momentum and pattern outputs must include numeric provenance and explicit invalidation.
- Future outlook statements must separate verified facts, guidance, estimates, and inference.
- Expected move and expected time must be stated together with confidence and downside context.

## Governance
- Committee process remains dry-run unless separately approved.
- Human review is required before any action recommendation can be considered executable.
- All critical outputs should retain evidence lineage suitable for post-trade review and learning.

## Backward Compatibility
- Existing marketplace queues, top-five behavior, and committee integration are preserved.
- Opportunity ranking core remains deterministic with unchanged defaults.
- Shadow adapters may be added, but default behavior must remain baseline-equivalent.

## Canonical Opportunity Rule
- There is exactly one authoritative investment Opportunity model: alpha_velocity/opportunity/models.py -> Opportunity.
- Similarly named objects in ranking, paper, or transport layers are adapters or DTOs and must not replace canonical Opportunity.
- Canonical Opportunity enrichment must remain serializable, deterministic, and backward compatible with prior saved states.

## Milestone 2.1 Boundaries
- No additional marketplace/ranking/committee/capital/evidence subsystem creation.
- No architecture redesign and no autonomous execution path.
- Lifecycle, recognition, horizons, expressions, and convictions are representational structures and do not authorize execution.

## Deferred Work
- Adaptive Research Universes
- Basket Intelligence
- Relationship Intelligence
- Best Expression Engine
- Research Allocation
- Intraday strategies
- Futures expansion
