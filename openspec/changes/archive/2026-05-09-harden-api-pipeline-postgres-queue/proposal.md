## Why

Omnibid already has a stable Docker Compose/Postgres baseline, but the repository now needs a documented transition path to Supabase CLI so future schema work can be staged locally before any remote deploy.

The missing piece is not a runtime replacement. The missing piece is a readiness lane that makes the migration path explicit:

- keep Compose as the current operational baseline
- add a Supabase CLI local-development scaffold
- keep migrations schema-first and versioned
- document the remote `link` + `db push` path without enabling a sudden stack replacement

This change defines that readiness lane so later implementation work can move from local schema validation to remote deployment with less drift.

## What Changes

- Add a Supabase readiness runbook under `docs/operations/`.
- Add Supabase CLI entries to the official source registry and record the SDD decision in a repo-local note.
- Add `SUPABASE_DB_URL`, `SUPABASE_PROJECT_REF`, and `SUPABASE_DB_POOL_MODE` to the repository config surface while preserving `DATABASE_URL` and `TEST_DATABASE_URL` as the live Compose baseline.
- Add a committed `supabase/` scaffold with `config.toml` and a versioned migration placeholder.
- Update the runtime docs so the CLI-first transition is documented as additive, not a replacement for the current Compose flow.

## Capabilities

- `supabase-readiness`
- `cli-first-postgres-transition`
- `schema-first-migration-staging`
- `runtime-baseline-preservation`

## Context

The repository already defines the runtime boundary this change must respect:

- `docs/runbooks/local_development.md` and `docs/runbooks/docker-local.md` already say Docker-first is canonical.
- `backend/core/config.py` currently fails fast on missing or inconsistent Compose database URLs.
- `docker-compose.yml` already carries the live runtime contract for backend and tools containers.
- `docs/architecture/system_architecture.md` already treats Compose as the canonical runtime boundary.

This change adds a readiness path, not a new operating mode.

## Verified Official Sources

1. Supabase CLI getting started
2. Supabase local development with schema migrations
3. Supabase config and secrets
4. Supabase database migrations
5. Supabase Postgres connection strings and pooler modes

## Non-Goals

- No self-hosted Supabase Compose replacement in this phase.
- No historical data backfill in this phase.
- No change to the live Compose database baseline.
- No runtime switch from `DATABASE_URL` to Supabase URLs yet.

## Impact

- `docs/operations/supabase-readiness.md`
- `docs/references/sdd-supabase-readiness-2026-05-09.md`
- `docs/references/sdd-official-sources-registry.md`
- `README.md`
- `.env.example`
- `.env.docker`
- `backend/core/config.py`
- `tests/unit/test_core_config.py`
- `docker-compose.yml`
- `supabase/config.toml`
- `supabase/migrations/20260509000000_readiness_baseline.sql`

## Validation Strategy

- verify the new settings parse and reject invalid pool modes
- verify the new docs make the CLI-first sequence explicit
- verify the existing Compose startup path still remains the baseline documented flow
- verify the new `supabase/` scaffold is committed and versioned
