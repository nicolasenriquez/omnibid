## Why

`GET /datasets/summary` still depends on live full-table counts and an in-memory TTL cache. This is acceptable for low-frequency use, but it is not reliable for sustained operational polling on large datasets.

## What Changes

- Add durable precomputed storage for dataset summary counters in operational persistence.
- Add a deterministic refresh flow that recomputes full counts and persists a new snapshot atomically.
- Update `/datasets/summary` to serve persisted snapshots by default and keep explicit fresh refresh semantics for operator-driven checks.
- Add fail-fast behavior and stale-state metadata when snapshot refresh fails.
- Add tests and runbook guidance for refresh cadence, staleness handling, and operator validation.

## Capabilities

### New Capabilities
- `precomputed-datasets-summary`: Persist and serve operational dataset summary snapshots with explicit refresh behavior and staleness metadata.

### Modified Capabilities
- None.

## Impact

- Affected code: `backend/api/routers/operations.py`, `backend/models/operational.py`, migration files, and API tests.
- Operational impact: reduces repeated expensive count queries and adds explicit summary freshness controls.
- Documentation impact: updates to operations/local runbooks and validation steps for summary refresh behavior.
