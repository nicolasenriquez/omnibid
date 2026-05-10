# Supabase CLI Readiness

This runbook records the CLI-first transition path for Omnibid's Postgres stack.

For the longer-term phase map, see [`supabase-cutover-plan.md`](supabase-cutover-plan.md).

## Baseline

- `just compose-up` remains the canonical local startup path.
- `just docker-smoke` remains the canonical smoke check for the current runtime.
- `DATABASE_URL` and `TEST_DATABASE_URL` remain the live runtime contract for the Compose baseline.
- `SUPABASE_DB_URL`, `SUPABASE_PROJECT_REF`, and `SUPABASE_DB_POOL_MODE=transaction` are readiness-only until a deliberate cutover is approved.
- Mercado Publico API hardening remains additive in this phase:
  - durable request budget + scoped lock + run metadata are implemented in shared Postgres schema/migrations.
  - no runtime switch is implied; local Compose remains canonical.
  - historical backfill strategy remains out of scope for this lane.

## Local CLI Flow

Use this sequence when preparing or validating the local Supabase migration lane:

1. `supabase init`
2. `supabase start`
3. `supabase migration new <name>`
4. Edit the generated `supabase/migrations/<timestamp>_<name>.sql` file with the schema change.
5. `supabase db reset`

Notes:

- `supabase start` uses Docker containers and requires a local Docker-compatible runtime.
- `supabase init` creates `supabase/config.toml`; keep that file committed once the transition lane is enabled.
- `supabase db reset` reapplies the migrations in `supabase/migrations/` to the local Supabase stack.

## Remote CLI Flow

Use this sequence only when the project is ready for a linked Supabase deployment:

1. `supabase login`
2. `supabase link --project-ref <project-ref>`
3. `supabase db push --dry-run`
4. `supabase db push`

Notes:

- `supabase db push` requires a linked project.
- Keep `SUPABASE_DB_POOL_MODE=transaction` for remote application traffic unless a separate connection decision is documented.
- Do not add historical backfills in this phase.

## Guardrails

- Schema-first: create and review migrations before any data migration or history replay.
- No abrupt runtime replacement: keep the existing Compose runtime baseline in place until a separate cutover change is approved.
- No self-hosted full Supabase replacement in Compose in this phase.
- No mass historical backfill: data migration comes after the schema and queue/pipeline readiness work is stable.
- No silent fallback: missing or invalid readiness settings should be handled as explicit configuration, not guessed at runtime.

## Verification

Verify the readiness lane in this order:

1. `just compose-up`
2. `just docker-smoke`
3. `just supabase-cli-smoke`
4. `just supabase-start-smoke`
5. `supabase start`
6. `supabase db reset`
7. `supabase db push --dry-run`

If the Supabase CLI is not installed yet, keep the runbook and config scaffold committed and verify the Compose baseline only.

The containerized `supabase start` smoke uses the Docker socket plus host networking so the CLI can reach the locally published Postgres port that Supabase checks after startup.
