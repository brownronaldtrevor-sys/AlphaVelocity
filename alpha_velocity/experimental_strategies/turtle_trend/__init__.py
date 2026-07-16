"""Experimental Turtle Trend strategy - DISABLED BY DEFAULT.

This module contains the Turtle Trend strategy implementation, moved to the
experimental_strategies directory as part of the Equity Intelligence consolidation.

The Turtle Trend strategy is deferred for a separate research program focusing on
futures and commodities. It is not registered in the Daily Investment Committee
and has zero influence on equity ranking and allocation.

Rationale for deferral:
- Futures require different infrastructure than equities
- Margin and contract-roll management separate from equity workflow
- Data ingest separate (continuous series, roll dates, margin requirements)
- Validate independently before integrating with equity portfolio decisions
- No established hedge ratio or correlation regime rules with equity positions

To enable for experimental research:
1. Implement comprehensive futures data ingestion
2. Build position-level margin tracking
3. Validate contract-roll behavior
4. Establish correlation and hedge ratios with equity holdings
5. Complete end-to-end execution testing in paper

Current status: UNCALIBRATED, ranking_influence=0, allocation_influence=0
"""

DISABLED_BY_DEFAULT = True

__all__ = ["DISABLED_BY_DEFAULT"]
