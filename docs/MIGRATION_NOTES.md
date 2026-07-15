# Migration notes

The previous builds contain useful brokerage, portfolio, exposure, and Shadow CIO infrastructure. Their heuristic predictive scores are **not certified**.

Before an existing strategy can trade:
1. Create a `StrategySpecification`.
2. Clear every CRITICAL audit finding.
3. Declare and count all parameters.
4. Pass `ParameterGuard`.
5. Map every feature to a point-in-time source.
6. Simulate chronologically.
7. Model costs and liquidity.
8. Run walk-forward tests with untouched holdouts.
9. Paper trade and reconcile every order.
10. Begin only a limited live sleeve after independent review.
