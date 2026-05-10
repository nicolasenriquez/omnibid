# Supabase Cutover Plan

This plan defines the long-term path from the current Docker Compose/Postgres baseline to a Supabase-backed deployment flow.

OpenSpec change: `openspec/changes/supabase-cutover-plan/`

## Goal

Move schema validation and deployment to Supabase without letting the app runtime, migrations, and data backfill drift apart.

## Principle

- One runtime baseline at a time.
- One schema source of truth at a time.
- Alembic is the authoring source of truth for the schema contract.
- The current database is only a validation reference for parity checks.
- No historical data migration until schema parity is proven.
- No production cutover until local and remote dry runs are both green.

## Phase 1: Readiness

Status: current

Scope:

- `just compose-up`
- `just docker-smoke`
- `just supabase-cli-smoke`
- `just supabase-start-smoke`
- committed `supabase/` scaffold
- `SUPABASE_DB_URL`, `SUPABASE_PROJECT_REF`, `SUPABASE_DB_POOL_MODE`

Exit criteria:

- Supabase CLI installs and runs in a container.
- `supabase start` works against the Docker socket and host network.
- The readiness docs explicitly say Compose is still canonical.

## Phase 2: Schema Parity

Scope:

- generate the first real Supabase migration from the current schema
- run `supabase db reset` locally
- compare the resulting schema against Alembic-backed expectations
- validate `supabase db push --dry-run`

Exit criteria:

- a fresh Supabase local project reproduces the expected schema
- the generated migration is reviewed and committed
- any schema drift is resolved before remote linking

Guardrails:

- no data backfill
- no runtime cutover
- no new application behavior

## Phase 3: Controlled Cutover

Scope:

- `supabase login`
- `supabase link --project-ref <project-ref>`
- `supabase db push --dry-run`
- `supabase db push`
- controlled application switch to the new connection contract

Exit criteria:

- remote dry run matches local schema history
- production push is reviewed and scheduled
- the app reads the intended production database URL without breaking the test database contract

Guardrails:

- keep rollback instructions documented before the switch
- keep the Compose baseline available until production is stable
- move historical data only after schema stability is confirmed

## Recommended Ownership

- Backend/config owner: environment contract and connection validation
- Database owner: migration review and parity checks
- Operator owner: CLI execution, dry runs, and cutover window
- Reviewer: schema parity and rollback review

## Decision Record

Use `docs/references/sdd-supabase-readiness-2026-05-09.md` as the current source-backed readiness note.
