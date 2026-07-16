# Market Leader Labels - Evaluation Framework

**Date**: 2026-07-16  
**Purpose**: Outcome evaluation labels for future grading  
**Timing**: Applied during post-trade analysis, NOT during ranking

---

## LABELS (No leakage into ranking model)

These labels are applied AFTER trading is closed, using forward-return data unavailable during position entry.

### Performance Thresholds

- **TOP_1PCT_5DAY** - Top 1% of market 5-day forward return
- **TOP_5PCT_20DAY** - Top 5% of market 20-day forward return
- **TOP_DECILE_60DAY** - Top 10% of market 60-day forward return
- **GAIN_20PCT_BEFORE_10PCT_DD** - 20% max favorable excursion before 10% max adverse excursion
- **GAIN_50PCT_WITHIN_6M** - 50%+ return within 6 months
- **DOUBLE** - 2x entry price
- **TRIPLE** - 3x entry price
- **FIVE_BAGGER** - 5x entry price

### Excursion Labels

- **MFE_ONLY** - Moved favorably but no exit taken, closed underwater
- **MAE_ONLY** - Moved adversely immediately, thesis never confirmed
- **FLAT** - Moved less than 5% in any direction

---

## GRADING FRAMEWORK

After each position closes or reaches milestone:

1. **Calculate forward returns**
   - Intra-trade: Entry to exit
   - Multi-day: Entry to N days later
   - Multi-week: Entry to N weeks later
   - Multi-month: Entry to N months later

2. **Calculate excursions**
   - Maximum Favorable Excursion (MFE): Highest price since entry
   - Maximum Adverse Excursion (MAE): Lowest price since entry

3. **Apply labels**
   - All applicable labels recorded
   - Non-exclusive (position can have multiple)
   - Forward-return data only
   - Calibration feedback to model

4. **Record in Evidence Ledger**
   - Market leader labels table
   - Entry thesis vs. realized outcome
   - Calibration delta (expected vs. actual return)
   - Time-to-move metrics

---

## LEARNING FEEDBACK

Market leader labels enable calibration:
- Did we overestimate probability? (Many 20% odds hits turned MAE_ONLY?)
- Did we underestimate upside? (Many GAIN_50PCT_WITHIN_6M in 20-day window?)
- Did triggers work as expected? (Failed breakouts → TOP_DECILE performance?)
- Which thesis elements predicted outcome? (Fundamental vs. technical vs. catalyst-driven winners?)

This data becomes feature engineering for future model refinement.

---

**Constraint**: These labels are applied ONLY during post-trade analysis. Never leak into ranking model during candidate selection.
