# SDD Reference — Mercado Publico Read-Model Propagation (2026-05-11)

## Purpose

Record the source-driven basis used for the Mercado Publico API read-model propagation implementation:
- staged daily DAG orchestration
- API payload canonicalization into existing Normalized + Silver tables
- complete-only upsert merge behavior

## Sources Consulted

1. SQLAlchemy ORM docs (2.x):
- `insert(...).on_conflict_do_update(...)` for PostgreSQL conflict handling
- typed ORM `Session.execute(...)` usage and update semantics

2. PostgreSQL `ON CONFLICT` semantics:
- deterministic key-based upsert contracts for canonical tables

3. Existing repository standards/docs:
- `AGENTS.md` execution and container-first policy
- `docs/architecture/external_api_ingestion.md`
- `docs/architecture/data_architecture.md`
- `docs/architecture/data_model.md`

## Design Notes Applied

- No parallel schema introduced; payload canonicalization reuses existing transform builders and existing canonical tables.
- Merge semantics remain complete-only through the current normalized upsert engine (`coalesce(incoming, existing)` style update expressions).
- Detail payload precedence is enforced by applying detail rows after rolling rows for duplicate business keys within the same propagation scope.
