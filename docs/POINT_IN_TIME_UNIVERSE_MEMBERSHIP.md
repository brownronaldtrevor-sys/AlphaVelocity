# Point-in-Time Universe Membership

Universe membership is point-in-time and auditable.

## Membership Record Fields
- security_id
- symbol
- effective_from
- effective_to
- inclusion_reason
- exclusion_reason
- source
- available_at
- validation_status

## Rules
- Membership cannot rely on future constituents.
- listing_date and delisting_date gates are applied at observation_time.
- available_at must be <= observation_time.
- Invalid identities or stale data are excluded explicitly.

## Deterministic Sample Mode
SAMPLE_DATA memberships are generated deterministically and labeled SAMPLE_DATA in source fields.
