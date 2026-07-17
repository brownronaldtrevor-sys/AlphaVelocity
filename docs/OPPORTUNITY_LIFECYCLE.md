# Opportunity Lifecycle v1

Lifecycle is explicit and auditable, not inferred from price alone.

## Stages
- DISCOVERY
- RESEARCH
- WATCH
- STARTER
- PRIMARY_MOVE
- MANAGE
- HARVEST
- EXIT_REVIEW
- CLOSED
- INVALIDATED

## Transition Rules
- current_stage, prior_stage, stage_changed_at, and stage_reason are preserved.
- transition_lifecycle validates monotonic time progression.
- INVALIDATED is terminal.
- evidence_lineage records transition history.

## Safety Constraint
Lifecycle stage does not authorize execution.
Risk, governance, human approval, and dry-run safeguards remain independent.
