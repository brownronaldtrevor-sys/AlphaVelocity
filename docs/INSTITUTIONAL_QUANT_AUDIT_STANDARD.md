# Institutional Quantitative Development and Risk Audit Standard

This codebase does not assume profitability. Every attractive result is presumed false until timing, data lineage, execution, and statistics are verified.

## Non-negotiable rules

1. Event-driven simulation only.
2. No value may be consumed before its `available_at` timestamp.
3. Signals calculated from a closing bar cannot fill at that same close.
4. Fundamentals, filings, calls, estimates, and macro releases require vintage timestamps.
5. Revised data cannot replace the original vintage.
6. Delisted securities and corporate actions must be present.
7. Costs include spread, commission, impact, and participation limits.
8. Shorts include borrow availability, fees, recalls, and forced buy-ins.
9. Futures include rolls, multipliers, margin, calendars, and limit moves.
10. Every tunable parameter is declared and counted.
11. Parameter-heavy strategies are refused before coding or optimization.
12. Every hypothesis search is logged and corrected for multiple testing.
13. Train, validation, and test periods are temporally separated.
14. Overlapping labels require purging and embargo.
15. Paper performance is not live evidence.
16. Live deployment begins with a small sleeve and independent kill switches.
