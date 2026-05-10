## Why

The repository already has a validated Supabase readiness lane, but readiness is not the same as cutover.

This change creates a separate approval boundary for the long-term transition so the project can move from local schema validation to a controlled production deployment without collapsing readiness, schema parity, and runtime switch into one step.

## What Changes

- Formalize the schema-parity phase that follows readiness.
- Define the controlled cutover phase for remote `link` and `db push`.
- Make rollback expectations explicit before any production switch.
- Keep the current Docker Compose/Postgres baseline canonical until cutover is approved.
- Keep historical data migration outside the cutover change.

## Capabilities

- `supabase-cutover-governance`
- `schema-parity-validation`
- `controlled-db-cutover`
- `rollback-ready-deployment`

## Context

The readiness change already added:

- the Supabase CLI smoke lane
- the local `supabase start` smoke
- the committed `supabase/` scaffold
- the Supabase readiness configuration surface
- the operational readiness runbook

This change sits on top of that work and does not replace it.

## Source of Truth

- Alembic remains the source of authoring truth for the schema contract.
- The current database state is only a validation target for parity checks.
- Supabase migrations must reflect the Alembic-backed contract, not redefine it.

## Non-Goals

- No historical data backfill in this change.
- No self-hosted Supabase Compose replacement.
- No production runtime switch before local parity is proven.
- No speculative schema refactors outside the current migration path.

## Impact

- `docs/operations/supabase-cutover-plan.md`
- `openspec/changes/supabase-cutover-plan/specs/supabase-cutover-plan/spec.md`
- `openspec/changes/supabase-cutover-plan/tasks.md`

## Validation Strategy

- Verify the local Supabase schema can be reset from migrations.
- Verify `supabase db push --dry-run` matches the intended remote state.
- Verify the cutover checklist documents rollback and owner responsibilities.
- Verify the Compose/Postgres baseline remains documented as canonical until the switch is approved.
