# Alpha Velocity 2.0 — Integrated Controlled Paper Platform

This repository restores the integrated Alpha Velocity scope:

- IBKR TWS paper connection
- market-data research scanning
- technical and opportunity ranking
- event-driven simulation controls
- point-in-time data safeguards
- institutional strategy auditing
- ensemble and sentiment infrastructure
- compounding and exposure mathematics
- portfolio and risk controls
- Shadow CIO
- forecast journaling
- paper-order planning and bracket-order support
- outcome grading and challenger promotion gates
- ethical governance, restricted-information controls, and emergency kill switch

## Current status

The architecture and paper workflow are research-grade. The active selector remains an
unvalidated prototype. Paper trading is intended to collect evidence, test operations, and
measure calibration—not to imply proven profitability.

## Windows setup

1. Keep this repository outside OneDrive, preferably `C:\AlphaVelocity`.
2. Double-click `SETUP_WINDOWS.bat`.
3. Open TWS Simulated Trading.
4. Run the safe connection and research launchers included in the repository.
5. Review `ETHICAL_AND_GOVERNANCE_STANDARD.md`.

## Safety default

Paper only. Long common stocks only. Explicit human approval. Hard independent controls.
No automatic live transition.

## Milestone 2 — Validated Price Action Evidence

Price structure, support/resistance location, failures, gaps, compression/expansion,
relative volume, and accumulation/distribution features are now recorded in research reports.
They default to **zero blending weight** and cannot affect rankings unless the out-of-sample
validation pipeline writes an approved artifact. See `PRICE_ACTION_VALIDATION_STANDARD.md`.

## Milestone 3 — Leakage-Controlled Feature Store

A point-in-time feature-store and validation-dataset generator are now available in
`alpha_velocity.validation.feature_store`. It emits chronologically ordered feature rows keyed
by symbol, observation date, and availability timestamp, builds labels for forward returns and
excursions, enforces purge/embargo-aware splits, writes dataset manifests, and supports
feature-group ablation. No training logic or execution/risk changes were introduced.
