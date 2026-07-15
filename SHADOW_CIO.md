# Shadow CIO — Independent Decision Intelligence

The Shadow CIO is deliberately separate from the alpha engines and portfolio allocator.

## Responsibilities

- Challenge proposed adds, reductions and exits.
- Compare current holdings with alternative opportunities and cash.
- Cap exposure when confirmation is incomplete.
- Veto decisions based on low-quality data.
- Detect excessive model disagreement and unresolved contradictions.
- Define required confirmations and invalidation conditions.
- Record counterfactual alternatives at decision time.
- Grade timing, sizing, thesis, execution and opportunity cost after outcomes occur.
- Learn whether the system was right for the right reasons.

## Governance

The default integration uses the lower of:
- the primary portfolio target; and
- the Shadow CIO target.

A Shadow CIO `REJECT_OR_EXIT` verdict can veto new paper exposure.

This is intentionally conservative for initial paper testing. Once enough paper and
historical evidence exists, governance rules can become regime-aware and probabilistic.

## What makes it "next level"

The architecture separates:
1. prediction quality;
2. decision quality;
3. execution quality; and
4. luck.

A profitable trade can receive a poor grade if the evidence was weak, sizing was
reckless or a much better alternative existed. A losing trade can receive a strong
decision grade if it was properly sized, well supported and statistically justified.

This is required for genuine learning rather than hindsight storytelling.
