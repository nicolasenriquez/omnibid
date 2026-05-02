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

## Execution Order Policy

- Agents MUST plan backend, database, migration, pipeline, and quality-gate execution through the container runtime first.
- The canonical path is `rtk just docker-start`, `rtk just docker-pipeline-full`, `rtk just docker-smoke`, and container-backed `just` recipes.
- Use host-local `uv`, `.venv`, or direct Python commands only as an explicit fallback when the container path is unavailable, blocked by sandbox permissions, or the task is clearly frontend-only.
- When falling back to host-local execution, say why the container path was not used and keep the fallback command as close as possible to the equivalent container/`just` recipe.
- Do not make local venv behavior the documented default for future agents.

## Agent Shell Command Policy

- Agent-issued shell commands must be prefixed with `rtk` when `rtk` is available in the active shell.
- Apply the prefix to local workflow commands such as `just`, `uv`, `docker`, `git`, and test/lint/type commands.
- Invoke project workflows as `rtk just <recipe>` rather than rewriting `justfile` recipe bodies to call `rtk` internally.
- Keep repository scripts and `justfile` recipes portable; do not make human/local development depend on RTK unless explicitly requested.
- If `rtk` is unavailable, report that clearly before running required local commands without the prefix.

## Quality Gates

- Default gate: run the container-first recipe path for the relevant scope, then `just quality` when appropriate.
- Extended CI-fast: `just ci-fast`
- Extended CI: `just ci`
- Host `.venv`/`uv run` test, lint, type, or migration commands are fallback validation only, not the first plan.

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

## Browser and Interactive Auditing Policy

- Agents MUST perform static code analysis first before opening a browser.
- Browser access is reserved for interactive flows that cannot be validated by reading code (e.g., drag-and-drop, polling UI states, modal transitions).
- When browser access is required, prefer `browser_get_text` or `browser_get_a11y_tree` over screenshots.
- Screenshots are prohibited unless explicitly requested by the user.
- The canonical browser tool is Playwright MCP via `npx @anthropic-ai/playwright-mcp`.

## Documentation Discipline

- Keep architecture + runbooks aligned with code.
- Update standards docs when quality gates or workflow change.
