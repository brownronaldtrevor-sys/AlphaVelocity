# Alpha Velocity v0.4 Paper Trading Runbook

## Purpose

This is the best current test build. It provides a complete offline paper loop:
data -> technical features -> opportunities -> capital competition -> target weights
-> simulated orders/fills -> persistent portfolio state -> JSON report.

It is intentionally not a validated investment strategy.

## Quick test with sample data

```bash
python examples/generate_sample_data.py
python -m alpha_velocity.paper_main \
  --symbols TURN,TREND,WEAK \
  --data-folder ./sample_data \
  --starting-cash 100000
```

Run the command repeatedly after adding new CSV rows to simulate daily operation.

## Your own market data

Create one CSV per symbol in a folder:

`JELD.csv`, `GNSS.csv`, etc.

Required columns:

```text
date,open,high,low,close,volume
2026-01-02,1.10,1.15,1.05,1.12,500000
```

Then run:

```bash
python -m alpha_velocity.paper_main \
  --symbols JELD,GNSS,HRTG,SM \
  --data-folder ./market_data \
  --state ./paper_state/account.json \
  --reports ./paper_reports \
  --starting-cash 10000
```

## IBKR paper-account path

The existing IBKR adapter remains in the package. Before transmitting paper orders,
the next integration step is to replace `SimulatedBroker.execute()` with the existing
IBKR `place_bracket()` route and use live IBKR historical bars.

Do not enable live-account mode. Keep:
- `broker.mode: PAPER`
- `execution.dry_run: true` until connection/order review is complete.

## Validation checklist

1. Confirm every calculated target weight is understandable.
2. Confirm entries and reductions match the intended exposure logic.
3. Review every fill and commission.
4. Test restart persistence.
5. Test missing and malformed data.
6. Test sharp gaps and illiquid names.
7. Compare decisions with your judgment.
8. Do not judge performance from a small number of trades.
9. Add point-in-time fundamentals before calling the output institutional.
10. Add trained, walk-forward models before any real-money use.
