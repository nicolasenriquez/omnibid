# SDD Note - Normalized Domain Entities (2026-04-22)

Change: `expand-normalized-domain-buyers-suppliers-categories`

## Official Sources Consulted

- SQLAlchemy ORM / Core (table metadata, constraints, indexes, upsert helpers):  
  https://docs.sqlalchemy.org/en/20/
- SQLAlchemy PostgreSQL dialect (`INSERT .. ON CONFLICT`):  
  https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
- Alembic operations API (table/column/index/fk migration operations):  
  https://alembic.sqlalchemy.org/en/latest/ops.html
- PostgreSQL constraints/index semantics reference:  
  https://www.postgresql.org/docs/current/

## Source-to-Decision Trace

1. Deterministic business-key upserts for domain entities
- Decision: use explicit conflict sets:
  - `buyers`: `buyer_key`
  - `suppliers`: `supplier_key`
  - `categories`: `category_key`
- Why: stable idempotent replay behavior with `ON CONFLICT` semantics.
- Code areas:
  - `scripts/build_normalized.py`
  - `backend/models/normalized.py`

2. Migration-controlled schema changes (no drift)
- Decision: introduce domain tables and relational FK columns only via Alembic migration.
- Why: schema source of truth remains migration history and parity can be tested.
- Code areas:
  - `alembic/versions/20260422172140_normalized_domain_normalized_domain_entities.py`
  - `tests/unit/test_normalized_domain_schema_parity.py`

3. Domain identity rejection persistence in operational quality issues
- Decision: persist `normalized_missing_domain_identity` with `record_ref` and `column_name`.
- Why: fail-fast/observability requirement for missing business keys in canonical domain modeling.
- Code areas:
  - `scripts/build_normalized.py`
  - `backend/models/operational.py`
  - `tests/unit/test_normalized_domain_entities_tdd.py`

## Validation Linkage

- Unit validation: `just test-unit`
- Targeted parity/contract checks:
  - `uv run pytest -q tests/unit/test_normalized_domain_schema_parity.py`
  - `uv run pytest -q tests/unit/test_normalized_domain_entities_tdd.py`
