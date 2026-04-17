## Why

`silver_load` currently works but needs stronger safeguards for schema drift, idempotent upserts, and operational observability under large monthly licitaciones/ordenes-compra datasets.

## What Changes

- Harden Silver transforms for licitaciones and ordenes de compra with stricter contract checks and deterministic normalization.
- Improve fail-fast behavior for malformed records and ambiguous keys.
- Improve operational reporting of Silver load progress and rejected rows.
- Add tighter TDD coverage around key transforms and upsert behavior.

## Capabilities

### New Capabilities
- `silver-load-hardening`: Deterministic, fail-fast, and auditable Silver load behavior for licitaciones and ordenes de compra.

### Modified Capabilities
- None.

## Impact

- Affected areas: `scripts/build_silver.py`, `backend/silver/transform.py`, `backend/models/silver.py`, and unit tests under `tests/unit/`.
- No API contract break expected in this phase.
- Documentation updates required in runbooks and standards where validation flow changes.
