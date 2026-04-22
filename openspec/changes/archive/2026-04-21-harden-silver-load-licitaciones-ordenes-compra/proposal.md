## Why

The normalized load currently works but needs stronger safeguards for schema drift, idempotent upserts, and operational observability under large monthly licitaciones/ordenes-compra datasets.

## What Changes

- Harden normalized transforms for licitaciones and ordenes de compra with stricter contract checks and deterministic normalization.
- Improve fail-fast behavior for malformed records and ambiguous keys.
- Improve operational reporting of normalized load progress and rejected rows.
- Add tighter TDD coverage around key transforms and upsert behavior.

## Capabilities

### New Capabilities
- `silver-load-hardening`: Deterministic, fail-fast, and auditable normalized-layer load behavior for licitaciones and ordenes de compra (legacy capability name retained).

### Modified Capabilities
- None.

## Impact

- Affected areas: `scripts/build_normalized.py`, `backend/normalized/transform.py`, `backend/models/normalized.py`, and unit tests under `tests/unit/`.
- No API contract break expected in this phase.
- Documentation updates required in runbooks and standards where validation flow changes.
