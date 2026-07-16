# Expected Move And Time v1

## Objective
Expected move must always be paired with expected realization window to avoid magnitude-only bias.

## Profile Structure
Each `ExpectedMoveTimeProfile` contains:
- Horizon name
- Expected move range
- Expected realization window
- Confidence
- Downside range
- Liquidity context
- Transaction cost estimate (bps)
- Opportunity cost considerations
- Evidence quality status

## Current Horizons
Marketplace classification currently emits profiles for:
- Primary repricing horizon
- Tactical swing horizon

## Interpretation Rule
A high expected move without sufficient confidence or liquidity context is not automatically favorable.
