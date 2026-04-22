## Why

The normalized layer is operationally stable, but buyer, supplier, and category attributes are still embedded in wide transactional tables. This blocks canonical domain contracts and increases downstream complexity for analytics and future Gold outputs.

## What Changes

- Add canonical normalized domain entities for buyers, suppliers, and categories with explicit business keys.
- Add deterministic population flows from existing normalized transactional datasets into the new domain entities.
- Add explicit relational contracts from transactional normalized entities to canonical domain entities where keys are present.
- Add fail-fast validation for missing required domain keys during canonicalization and deterministic handling of optional links.
- Add test coverage, migration parity checks, and runbook updates for domain-entity build behavior.

## Capabilities

### New Capabilities
- `normalized-domain-entities`: Canonical buyer, supplier, and category entities with deterministic upsert semantics and traceable links from normalized transactional data.

### Modified Capabilities
- None.

## Impact

- Affected code: `backend/models/normalized.py`, `scripts/build_normalized.py`, `backend/normalized/transform.py`, Alembic revisions, and tests for transforms/loader behavior.
- Operational impact: introduces additional normalized write paths and domain-level quality checks before Gold expansion.
- Documentation impact: updates to architecture/runbooks and evidence for domain canonicalization validation.
