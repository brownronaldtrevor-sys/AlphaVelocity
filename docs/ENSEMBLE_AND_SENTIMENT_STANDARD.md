# Ensemble Modeling and Sentiment Feature Engineering Standard

## Ensemble requirements

1. Models must be trained and validated on temporally separated data.
2. Ensemble weights may not be optimized on the final evaluation period.
3. At least two genuinely different feature families are required.
4. Correlated variants of the same model do not count as independent evidence.
5. Every component model must pass calibration, uncertainty and validation thresholds.
6. Ensemble uncertainty must include cross-model disagreement.
7. Failed component models are logged and excluded rather than silently averaged.
8. Stacking requires nested walk-forward validation; otherwise it is prohibited.
9. Regime-dependent weights must be predeclared or trained out of sample.
10. No ensemble is presumed superior to its best simple constituent.

## Sentiment requirements

1. Every document needs `published_at` and `available_at`.
2. Revised transcripts or corrected filings must preserve version history.
3. Source classes remain separate before aggregation.
4. Social data receives low reliability unless independently validated.
5. Tone alone is insufficient; features include uncertainty, evasiveness, liquidity
   concerns, litigation, demand, pricing, guidance changes, novelty and contradiction.
6. All features must be computed only from documents available at the decision timestamp.
7. Novelty must eventually be measured against a point-in-time issuer and sector corpus.
8. Predictive value must be tested after controlling for price momentum and event timing.
9. Sentiment models must be checked for sector, speaker, transcription and source bias.
10. The system must distinguish sentiment that predicts returns from sentiment that merely
    restates information already reflected in price.

## Current implementation status

The included sentiment engineer is transparent and rule-based. It is an auditable feature
generator, not a validated alpha model.

The included ensemble is a conservative calibrated-weight combiner. It is not a trained
stacking model and does not claim performance improvement.
