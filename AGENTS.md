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
- Current focus: deterministic procurement data engineering pipeline (Bronze/Silver foundation).

## Core Principles

- KISS and YAGNI.
- TDD-first when changing behavior.
- Fail-fast on schema drift, invalid config, malformed source files, or broken contracts.
- No silent fallbacks for required dependencies (database, migrations, required columns).
- Keep data lineage explicit: source file -> ingestion batch -> run -> step -> target table.

## Architecture Boundaries

- `backend/core`: config, errors, app wiring.
- `backend/db`: engine/session/base.
- `backend/api`: health + operations endpoints.
- `backend/ingestion`: file contracts and ingestion logic.
- `backend/silver`: normalization transforms.
- `backend/models`: operational, bronze, silver models.
- `scripts/`: operational pipeline entrypoints (`profile_files.py`, `ingest_raw.py`, `build_silver.py`).

## Data Engineering Rules

- Bronze remains traceable and append-oriented.
- Silver remains canonical and query-ready.
- Use business keys for dedup/upsert semantics.
- Never aggregate raw rows as business entities without normalizing grain first.
- Preserve source metadata (`source_file_id`, `ingestion_batch_id`, `pipeline_run_id`).

## Required Commands

- Setup: `just setup`
- DB bootstrap: `just db-bootstrap`
- Bronze profile/load: `just pipeline-1-bronze`
- Silver build from existing Bronze: `just pipeline-2-silver-from-bronze`
- End-to-end Bronze -> Silver: `just pipeline-all`
- API: `just api`

## Quality Gates

- Default local gate: `just quality`
- Extended CI-fast: `just backend-ci-fast`
- Extended CI: `just backend-ci`

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

## Documentation Discipline

- Keep architecture + runbooks aligned with code.
- Update standards docs when quality gates or workflow change.
