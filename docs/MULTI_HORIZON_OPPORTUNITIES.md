# Multi-Horizon Opportunities v1

## Rationale
A single security can be attractive on one horizon and unattractive on another. AlphaVelocity stores horizon views independently to prevent mixing signals.

## Horizons
- Research Horizon: long-cycle thesis quality and asymmetry.
- Primary Repricing Horizon: medium-cycle expected mispricing resolution.
- Tactical Swing Horizon: shorter-cycle setup and confirmation quality.
- Execution Horizon: near-term action readiness and trigger state.

## Data Model
`MultiHorizonProfile` stores all four horizon assessments explicitly.

Each `HorizonAssessment` includes:
- Status
- Attractiveness
- Confidence
- Expected realization window
- Expected move range
- Downside range
- Invalidation criteria
- Required confirmation
- Supporting and contradictory evidence

## Design Constraint
Horizon states are additive metadata and do not replace legacy queue assignment logic.
