# AGENTS.md

@RTK.md

This file defines repository behavior guidance for coding agents in `app-chilecompra`.

## Instruction Precedence

- Canonical repository behavior policy lives in this file.
- `openspec/` and product docs provide project context, not behavior policy.
- If guidance conflicts, follow: system/developer instructions > `AGENTS.md` > project docs.

## Project Overview

- Stack: FastAPI + PostgreSQL + SQLAlchemy + Alembic.
- Runtime/package manager: `uv`.
- Operator interface: `just`.
- Architecture: monorepo with `backend/` + future `client/`, plus data pipeline modules.
- Current focus: deterministic procurement data engineering pipeline (Raw/Normalized foundation).

## Core Principles

- KISS and YAGNI.
- SDD-first for framework/library behavior: consult official docs first and record the source used in `docs/references/`.
- TDD-first when changing behavior.
- Fail-fast on schema drift, invalid config, malformed source files, or broken contracts.
- No silent fallbacks for required dependencies (database, migrations, required columns).
- Keep data lineage explicit: source file -> ingestion batch -> run -> step -> target table.

## Architecture Boundaries

- `backend/core`: config, errors, app wiring.
- `backend/db`: engine/session/base.
- `backend/api`: health + operations endpoints.
- `backend/ingestion`: file contracts and ingestion logic.
- `backend/normalized`: normalization transforms.
- `backend/models`: operational, raw, normalized models.
- `scripts/`: operational pipeline entrypoints (`profile_raw.py`, `ingest_raw.py`, `build_normalized.py`).

## Data Engineering Rules

- Raw remains traceable and append-oriented.
- Normalized remains canonical and query-ready.
- Use business keys for dedup/upsert semantics.
- Never aggregate raw rows as business entities without normalizing grain first.
- Preserve source metadata (`source_file_id`, `ingestion_batch_id`, `pipeline_run_id`).

## Required Commands

- Setup: `just uv-sync`
- Docker start (one command): `just docker-start`
- Docker build: `just docker-build`
- Docker bootstrap: `just docker-bootstrap`
- Docker full pipeline: `just docker-pipeline-full`

## Quality Gates

- Default local gate: `just quality`
- Extended CI-fast: `just ci-fast`
- Extended CI: `just ci`

## Docker Local Runtime Policy

- Canonical Docker runtime uses `docker-compose.yml` + `.env.docker`.
- Container-internal PostgreSQL host must be service DNS (`db` / `db_test`), never `localhost`.
- Keep dataset bind mount read-only at `/datasets/mercado-publico`.
- Keep published ports localhost-bound (`127.0.0.1`) for local development.
- Do not commit real secrets in Compose/env files; use local overrides when needed.
- Keep API container non-root and preserve hardening defaults (`no-new-privileges`, read-only root fs, health checks).

## Testing Policy

- Unit tests first for transformation and contract logic.
- Integration tests for database behavior and migration interactions.
- Keep tests deterministic and isolated.

## Type and Lint Policy

- Type hints are required for production code.
- Keep MyPy clean for `backend/` and `scripts/`.
- Keep Ruff clean for `backend/`, `scripts/`, and `tests/`.

## Logging Policy

- Prefer structured events with explicit context (`run_id`, `step_name`, dataset/file info).
- Event naming style: `domain.component.action_state`.
- Include actionable error payloads.

## Security and Migrations

- Alembic is schema source of truth.
- Do not introduce schema drift outside migrations.
- Keep SQL changes explicit and reviewable.
- Keep Alembic `revision` ids compact enough for `alembic_version.version_num` (`VARCHAR(32)`); generate timestamped short ids with `uv run alembic revision --rev-id <id> -m "<name>"`.

## Documentation Discipline

- Keep architecture + runbooks aligned with code.
- Update standards docs when quality gates or workflow change.
