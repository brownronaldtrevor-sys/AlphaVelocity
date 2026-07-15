# Alpha Velocity v1.1 — Automatic Paper Trading and Controlled Learning

## What this release does

1. Runs the research-only IBKR scan.
2. Selects up to three long stock candidates.
3. Refuses to execute unless every connected account identifier begins with `DU`.
4. Requires complete account, position, and open-order reconciliation.
5. Refuses symbols with existing positions or API-visible open orders.
6. Passes every proposed entry through the deterministic Risk Engine.
7. Journals each forecast before sending the order.
8. Sends an IBKR paper bracket order with entry, target, and stop.
9. Later grades target-versus-stop outcomes from IBKR historical bars.
10. Prevents challenger-model promotion until predeclared sample and calibration gates pass.

## Daily workflow

1. Open TWS and log into Simulated Trading.
2. Ensure TWS API Read-Only is OFF. The program still hard-blocks non-DU accounts.
3. Run `RUN_RESEARCH_ONLY.bat`.
4. Review the new research JSON.
5. Run `RUN_AUTOMATIC_PAPER_TRADING.bat`.
6. Confirm the Windows prompt only when you are ready to transmit to the paper account.
7. Check TWS Orders and Trades.
8. Run `GRADE_PENDING_OUTCOMES.bat` daily. Forecasts are graded when a target, stop, or
   20-trading-day horizon is reached.

## Initial hard limits

- Three positions maximum from the selector.
- Ten percent notional cap per position.
- Thirty percent gross exposure cap.
- 0.5% account risk budget per trade.
- Long U.S. stocks only.
- No options, futures, or shorts.
- No automatic pyramiding.
- No live-account execution.

## Important warning

The selector remains a transparent technical prototype. It is being paper traded to collect
evidence, not because an edge has been proven. Paper fills do not establish live profitability.
