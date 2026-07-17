# Opportunity Expressions v1

One thesis may have multiple expressions.

## Supported Expression Types
- EQUITY
- ETF
- BASKET
- PEER
- EXISTING_HOLDING
- WATCHLIST_SECURITY

## Expression Fields
Each expression carries:
- expression_id
- security_id or basket_id
- symbol when applicable
- expression_type
- role
- attractiveness
- research_confidence
- liquidity
- implementation_cost
- current_actionability
- relationship_to_thesis
- supporting_evidence
- contradictory_evidence
- available_at
- validation_status

## Boundaries
- No Best Expression Engine in this milestone.
- Expression attractiveness does not authorize execution.
- Canonical Opportunity keeps backward-compatible primary symbol fields.
