# Mathematical Objective Standard

## North Star

Maximize expected compounded wealth per unit of calendar time while keeping the
estimated probability of irreversible capital impairment below a predefined limit.

## Implemented components

- distributional opportunity forecast object;
- probability of target before stop;
- expected return and median return;
- expected favorable and adverse excursion;
- tail-loss probability;
- expected time to realization;
- binary-barrier fractional Kelly sizing;
- uncertainty, disagreement, data-trust, liquidity and event-risk haircuts;
- expected-log-growth evaluation;
- CVaR proxy penalty;
- execution-cost penalty;
- capital-priority score;
- correlation-cluster limits;
- cash reserve;
- graduated Shadow CIO intervention.

## Institutional warnings

1. Binary Kelly is only an approximation.
2. Barrier probabilities must be calibrated out of sample.
3. Kelly sizing is extremely sensitive to probability error.
4. CVaR proxies are not substitutes for full tail simulation.
5. Capital-priority scores must not be tuned repeatedly on the final test set.
6. Correlations are unstable and must be estimated point in time.
7. Expected time-to-target labels overlap and require purged validation.
8. Maximum concentration is an authority ceiling, not a recommendation.
9. Cash remains the default when no opportunity clears positive expected-log-growth.
10. The Shadow CIO may block only for control failures or extreme evidence weakness.
