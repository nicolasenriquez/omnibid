## Problem

Omnibid needs a clear path from the current Docker Compose/Postgres baseline to a Supabase-managed workflow, but the repository should not silently swap the runtime contract before the migration lane is prepared.

## Design Goals

1. Keep the current Compose/Postgres path canonical until a deliberate cutover is approved.
2. Stage Supabase as a CLI-first readiness lane, not a self-hosted stack replacement.
3. Make the local schema workflow explicit and versioned.
4. Preserve fail-fast behavior for configuration and runtime assumptions.
5. Keep data backfills and historical migration work separate from schema readiness.

## Proposed Flow

```text
Compose/Postgres baseline
  -> Supabase CLI init/start
  -> versioned local migrations
  -> db reset against the local Supabase stack
  -> login/link to a remote project
  -> db push --dry-run
  -> db push
```

## Contract Shape

### Runtime settings

- `DATABASE_URL` and `TEST_DATABASE_URL` remain the live runtime contract.
- `SUPABASE_DB_URL` and `SUPABASE_PROJECT_REF` are readiness values for the transition lane.
- `SUPABASE_DB_POOL_MODE` defaults to `transaction` and is validated against the supported Supabase pool modes.

### Repository scaffolding

- `supabase/config.toml` provides the local CLI scaffold.
- `supabase/migrations/` holds versioned SQL migration files.
- the first placeholder migration keeps the repo structure committed before the real schema lane is generated.

### Documentation

- the new operations runbook documents the CLI-first sequence and guardrails.
- the architecture and local development docs link to the readiness lane instead of implying a runtime replacement.
- the official sources registry includes the Supabase docs used for this change.

## Risks

- A placeholder migration can be mistaken for a real schema baseline.
- Operators could confuse readiness variables with the current runtime database contract.
- A future cutover could drift if the migration lane is not kept versioned and reviewed.

## Mitigations

- call the scaffold a readiness placeholder in both docs and comments
- keep Compose baseline language explicit in the runbook and runtime docs
- keep migration files versioned and schema-first
- leave historical backfill out of scope until a separate approved phase
