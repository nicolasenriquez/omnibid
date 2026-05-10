# SDD: Mercado Publico API Pipeline Hardening

## Decision

Harden the existing Mercado Publico API lane by adding durable request-budget enforcement, scoped locking, explicit run provenance, and safer operator controls while keeping the current Compose baseline and Supabase readiness separate.

## Verified Official Sources

1. PostgreSQL 16 documentation
2. GitHub Actions workflow syntax and trigger docs
3. GitHub Actions token permissions and hardening docs
4. Supabase CLI local development, schema migration, and connection docs

## Repo Contract Alignment

- The current API lane already persists request, payload, and notice snapshot lineage.
- The current API lane already uses `pipeline_runs` and `pipeline_run_steps` for job tracking.
- The current API budget setting is process-level; this change makes the budget durable.
- The current Supabase readiness lane stays additive and separate from historical backfill.
- No predictive scoring belongs in Silver as part of this hardening phase.

## Why This Note Exists

This note captures the source-backed reasoning for the hardening phase so future changes can reuse the same operational contract without re-deriving the decision from scattered implementation files.
