# App ChileCompra - Data Platform Foundation

## Scope (Phase 1)
Historical batch pipeline only:
- Register bulk files
- Profile raw datasets
- Build raw/normalized foundations (Gold is deferred until normalized analytical readiness)
- Persist in PostgreSQL
- Expose minimal operational FastAPI endpoints
- Enforce TDD + fail-fast quality gates

## Stack
- Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- uv + Justfile for local workflows

## Quickstart
1. `cp .env.example .env`
2. `just setup` (instala dependencias con `uv`)
3. `just db-bootstrap`
4. `just pipeline-raw`
5. `just pipeline-normalized`
6. `just api`

## Quality Workflow
- Unit tests: `just test-unit`
- Integration tests: `just test-integration`
- Static checks: `just lint`, `just type`, `just black-check`, `just security`
- Strict typing: `just type-strict` (`pyright` + `ty`)
- Local gates: `just quality`, `just ci-fast`, `just ci`

## Development Methodology
- **Fail-fast**: invalid config/schema/contracts must stop execution with explicit errors.
- **TDD-first**: behavior changes start with tests before implementation.
- **SDD-first**: implementation decisions for frameworks/libraries are grounded on official documentation and recorded in `docs/references/`.

## Agent/Codex Assets
- `AGENTS.md` and `RTK.md` were added for repo-level agent behavior.
- `codex/` contains imported command/skill assets from the reference project.
- `codex/LOCAL_ADAPTATIONS.md` documents the mapping to this repo (`backend/`, `client/`, CI commands).
- Note: this execution sandbox blocks creating a literal `.codex/` path, so `codex/` is used as the mirror path.
- If you want canonical `.codex/` locally, run: `just codex-sync`.

## Raw Canonical Command
- `just pipeline-raw`
  - runs: `db-bootstrap` -> `raw-profile` -> `raw-ingest`

## Normalized Canonical Command
- `just pipeline-normalized`
  - transforms raw -> normalized with idempotent upserts

## Stage-Gated Roadmap
This repository follows a controlled sequence where each stage must meet acceptance criteria before moving forward:

1. **Bronze/Raw Ingestion Foundation**: Source registration, contracts, lineage, and idempotent ingestion baseline.
2. **Bronze/Raw Reliability Hardening**: Auditable load telemetry, deterministic replay behavior, and data-quality visibility.
3. **Silver/Normalized Core Canonicalization**: Deterministic entity builders, conflict-key upserts, and reproducible rebuild from raw.
4. **Silver/Normalized Domain Expansion**: Add buyer/supplier/category domain models and stronger relational contracts.
5. **Gold Business Layer**: Start only after normalized layer is stable and operationally trusted.

## Current API
- `GET /health`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /files`
- `GET /files/{source_file_id}`
- `GET /datasets/summary`

## Next Steps
- Transactional hardening in pipeline scripts (`session.rollback()` guarantees after SQL failures).
- ORM/migration schema parity hardening for operational/raw indexes and constraints.
- Normalized data-quality issue persistence + threshold gates before domain expansion.
- API operational guardrails (`limit` caps and scalable dataset summary strategy).
- Gold outputs and downstream serving endpoints only after stage-gate completion.
