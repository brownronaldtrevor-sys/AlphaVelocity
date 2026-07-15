# Code Audit v0.8.1

## Verified

- Python source compiles.
- Automated tests pass.
- Event-driven same-bar fill prohibition exists.
- Point-in-time availability controls exist.
- Parameter burden and ensemble diversity guards exist.

## Critical hardening changes

1. Removed the possibility that the connection-test CLI transmits the synthetic demo strategy.
2. Broker account summaries, positions and open orders must finish loading before the connection test succeeds.
3. Added a broker-boundary prohibition on transmitting `DEMO_WIRING_TEST`.
4. Replaced import-time dataclass timestamps with per-instance factories.
5. Corrected package metadata from v0.1 to v0.8.1.
6. Added strict range and unit checks to compounding mathematics.
7. Reduced capital-priority instability by adding a risk-cost floor and requiring positive expected log growth.
8. Added an explicit live-readiness refusal gate for heuristic or insufficiently validated models.

## Unresolved institutional gaps

This remains a research platform, not a validated trading model. It does not yet have:

- a point-in-time survivorship-free security master;
- corporate-action and delisting ingestion;
- a complete futures roll/margin/calendar model;
- short borrow availability, recalls and fee history;
- trained and calibrated distributional forecasts;
- purged walk-forward cross-validation with embargo;
- capacity estimates based on bid/ask and depth;
- IBKR reconnect, idempotency and order-reconciliation integration tests;
- deterministic disaster recovery testing;
- independent reproduction of research results.

No live capital should be enabled until these gaps relevant to the chosen strategy are closed.
