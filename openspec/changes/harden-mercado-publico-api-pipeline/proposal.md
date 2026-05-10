## Why

Omnibid already has a working Mercado Publico API lane: `scripts/fetch_mp_api.py`, `scripts/run_mp_api_daily_pipeline.py`, `backend/integrations/mercado_publico/`, `api_source_request`, `api_source_payload`, `mercado_publico_notice_snapshot`, and the `pipeline_runs` ledger.

What is missing is operational hardening:

- the daily request budget is tracked inside a process, not as a durable operational budget
- concurrent runs can still overlap at the logical work-unit level
- request/payload/snapshot lineage exists, but it is not yet hardened for replay, max-request guardrails, or explicit operator provenance
- the current Supabase readiness lane exists, but the pipeline contract still needs to be proven compatible with both Compose local and Supabase remote execution

This change hardens the existing lane in place. It does not introduce a parallel ingestion stack, and it does not move predictive logic into Silver.

## What Changes

- Harden the Mercado Publico request ledger so daily API budget enforcement survives process restarts.
- Add logical run lifecycle metadata for provider, mode, requested-by, parameters, stats, and error handling.
- Add a lock strategy scoped to the unit of work so concurrent syncs do not overlap on the same business key.
- Extend the operator entrypoint with dry-run, max-requests, requested-by, and optional window bounds.
- Keep raw payload storage and queryable notice snapshots separate, but make the lineage and idempotency contract explicit.
- Add a GitHub Actions workflow for scheduled or manual sync execution using secrets only.
- Keep Supabase readiness explicit so the same schema and pipeline can run against local Postgres or remote Supabase without a logic rewrite.

## Capabilities

- `api-request-budget`
- `mercado-publico-sync-runs`
- `mercado-publico-snapshots`
- `pipeline-locking`
- `supabase-readiness`

## Context

The repository already defines the contract surface this change must respect:

- `backend/core/config.py` already has Mercado Publico budget, retry, and cache settings.
- `backend/models/api_source.py` and `alembic/versions/202605081910_mp_api_source.py` already persist request, payload, and notice snapshot lineage.
- `scripts/fetch_mp_api.py` already supports `active-discovery`, `rolling-window`, and `detail-by-codigo`.
- `scripts/run_mp_api_daily_pipeline.py` already composes API sync with Silver notice refresh.
- `docs/architecture/external_api_ingestion.md` and `docs/architecture/data_model.md` already document the API lane as backend-only operational lineage.
- `docs/operations/supabase-readiness.md` already separates readiness from cutover.

This change tightens the current operating lane. It does not redefine the product architecture.

## Verified Official Sources

1. PostgreSQL 16 documentation
2. GitHub Actions workflow syntax
3. GitHub Actions trigger behavior
4. GitHub Actions token permissions
5. Supabase CLI getting started
6. Supabase local development with schema migrations
7. Supabase database migrations
8. Supabase Postgres connection strings and pooler modes

## Non-Goals

- No predictive scoring in Silver.
- No frontend mutation workflow.
- No CSV historical backfill rewrite.
- No replacement of the existing Compose baseline.
- No mandatory new lock table if advisory locks satisfy the contract.
- No mass migration of historical API data in this phase.

## Impact

- `backend/core/config.py`
- `backend/integrations/mercado_publico/client.py`
- `backend/integrations/mercado_publico/rate_limit.py`
- `backend/integrations/mercado_publico/store.py`
- `backend/integrations/mercado_publico/sync.py`
- `backend/models/api_source.py`
- `backend/pipeline/application.py`
- `scripts/fetch_mp_api.py`
- `scripts/run_mp_api_daily_pipeline.py`
- `alembic/versions/`
- `tests/unit/test_mercado_publico_*.py`
- `tests/integration/test_mp_api_daily_pipeline.py`
- `.github/workflows/mp-api-sync.yml`
- `docs/architecture/external_api_ingestion.md`
- `docs/architecture/data_model.md`
- `docs/operations/supabase-readiness.md`
- `docs/references/sdd-mercado-publico-api-pipeline-hardening-2026-05-09.md`

## Validation Strategy

- verify daily budget behavior with unit tests around the request ledger
- verify safe URL redaction and canonical request hashing
- verify run lifecycle transitions and requested-by metadata
- verify snapshot idempotency for same-code same-payload and same-code changed-payload cases
- verify advisory-lock behavior for same-key and different-key concurrent runs
- verify dry-run returns a plan and performs no writes
- verify production config rejects trivial database credentials
- verify Docker-first smoke checks still work after the schema hardening
