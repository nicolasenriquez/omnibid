# App ChileCompra - Data Platform Foundation

## Scope (Phase 1)
Historical batch pipeline only:
- Register bulk files
- Profile raw datasets
- Build Bronze/Silver/Gold foundations
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
4. `just pipeline-1-bronze`
5. `just pipeline-2-silver-from-bronze`
6. `just api`

## Quality Workflow
- Unit tests: `just test-unit`
- Integration tests: `just test-integration`
- Static checks: `just lint`, `just type`, `just black-check`, `just security`
- Strict typing: `just type-strict` (`pyright` + `ty`)
- Local gates: `just quality`, `just backend-ci-fast`, `just backend-ci`

## Agent/Codex Assets
- `AGENTS.md` and `RTK.md` were added for repo-level agent behavior.
- `codex/` contains imported command/skill assets from the reference project.
- `codex/LOCAL_ADAPTATIONS.md` documents the mapping to this repo (`backend/`, `client/`, CI commands).
- Note: this execution sandbox blocks creating a literal `.codex/` path, so `codex/` is used as the mirror path.
- If you want canonical `.codex/` locally, run: `just codex-sync`.

## Bronze Canonical Command
- `just pipeline-1-bronze`
  - runs: `db-bootstrap` -> `profile-files` -> `ingest-raw`

## Silver Canonical Command
- `just pipeline-2-silver-from-bronze`
  - transforms Bronze -> Silver with idempotent upserts

## Current API
- `GET /health`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /files`
- `GET /files/{source_file_id}`
- `GET /datasets/summary`

## Next Steps
- Gold outputs and data quality dashboards
- Silver data-quality issue persistence and thresholds
- Incremental serving endpoints for filtered opportunities
