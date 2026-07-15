# Alpha Velocity Ethical and Governance Standard

## Purpose

Alpha Velocity may research and paper trade lawful market opportunities. It may not
pursue returns by deception, market manipulation, misuse of restricted information,
circumvention of controls, or privacy violations.

## Non-negotiable prohibitions

- No spoofing, layering, wash trading, quote stuffing, marking the close, or deceptive orders.
- No trading on material non-public information.
- No use of stolen credentials, unlawfully obtained datasets, or private personal data.
- No evasion of broker, exchange, legal, regulatory, suitability, margin, or risk restrictions.
- No automatic migration from paper to live trading.
- No disabling audit logs, account verification, data-lineage checks, or kill switches.

## Independent controls

The Governance Engine runs separately from the alpha selector. Strategy code cannot approve
its own exceptions. The default release:

- recognizes only IBKR `DU...` paper accounts;
- blocks live-account identifiers;
- allows long common stocks only;
- caps positions and gross exposure;
- requires protective stops;
- enforces a daily-loss kill switch;
- blocks orders with invalid point-in-time data lineage;
- requires explicit human approval before paper-order transmission;
- records all decisions and overrides.

## Model ethics and integrity

- Heuristic scores must be labeled as unvalidated.
- Probabilities must not be presented as calibrated until calibration is demonstrated.
- Failed features and models are retained in an audit trail.
- Challenger models cannot self-promote.
- Results must include costs, failed orders, missing data, and unfavorable outcomes.
- Backtests must include survivorship, delisting, revision, and selection-bias controls.

## Privacy and security

Never store IBKR passwords, two-factor codes, recovery details, or withdrawal credentials in
the repository. Local account configuration, reports, journals, data, and logs are excluded
from Git by default.
