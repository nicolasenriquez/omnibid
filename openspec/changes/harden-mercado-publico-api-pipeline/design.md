## Problem

The Mercado Publico API lane is already functional, but the current implementation still leaves three operational gaps:

1. request budget enforcement is process-local instead of durable
2. concurrent syncs can overlap at the same logical unit of work
3. the run ledger and snapshot lineage are not yet formalized enough for a production-style schedule

The change must harden those gaps without breaking the current Compose baseline, the existing API lane, or the CSV historical path.

## Design Goals

1. Keep the current Compose/Postgres path canonical until a separate cutover is approved.
2. Harden the existing Mercado Publico lane in place rather than creating a parallel ingestion stack.
3. Make budget, locking, and idempotency durable across process restarts.
4. Preserve the existing request/payload/snapshot lineage and make it easier to inspect.
5. Keep Supabase readiness additive and separate from data backfill.
6. Keep the first phase simple enough to validate with unit and integration tests.

## Current-to-Target Mapping

The repo already has the right shape, but the logical contract needs to be made explicit:

- `pipeline_run` -> current `pipeline_runs`
- `api_request_ledger` -> current `api_source_request`
- `raw_payload_archive` -> current `api_source_payload`
- `mp_notice_snapshot` -> current `mercado_publico_notice_snapshot`

This change should harden those existing surfaces instead of introducing a duplicate API stack.

## Proposed Flow

```text
operator or scheduler
  -> create pipeline run
  -> acquire scoped advisory lock
  -> check persistent daily budget
  -> execute one of:
     - active-discovery
     - rolling-window
     - detail-by-codigo
  -> persist request ledger row
  -> persist raw payload artifact
  -> persist notice snapshot
  -> update run stats and status
  -> release lock
```

The daily Silver refresh remains a downstream composition step, not part of the API request budget logic.

## Contract Shape

### Run lifecycle

Logical run fields:

- provider
- mode
- status
- started_at
- finished_at
- requested_by
- parameters
- stats
- error_message

Recommended statuses:

- `pending`
- `running`
- `succeeded`
- `failed`
- `partial`

The implementation may map these semantics onto the existing status storage shape as long as the external contract remains consistent.

### Request ledger

The request ledger is the source of truth for daily budget tracking and auditability.

Recommended fields:

- provider
- endpoint
- request_method
- request_url_safe
- request_hash
- request_date
- requested_at
- status_code
- success
- cost_units
- response_hash
- error_type
- error_message
- pipeline_run_id
- metadata

Rules:

- `request_hash` MUST exclude ticket material.
- `request_url_safe` MUST redact the ticket and any other secret query fields.
- uniqueness SHOULD prevent duplicate semantic requests on the same day.
- the budget ledger MUST be queryable without reopening raw JSON.

### Snapshot layer

The raw payload archive and the queryable notice snapshot are separate concerns:

- the raw payload archive preserves the upstream JSON exactly once per unique response hash
- the notice snapshot stores the operational row shape used by operators and downstream refreshes
- both must carry `pipeline_run_id`

Recommended snapshot fields:

- codigo_externo
- observed_at
- source_endpoint
- source_mode
- payload_hash
- payload_jsonb or equivalent raw archive reference
- normalized_status
- fecha_publicacion
- fecha_cierre
- pipeline_run_id

Rules:

- same `codigo_externo` + same payload hash must not create duplicate semantic snapshots
- same `codigo_externo` + different payload hash must produce a new snapshot row
- the snapshot layer must stay separate from Silver and must not contain predictive scores

### Locking strategy

Use `pg_try_advisory_lock` for phase 1.

Why:

- the repo already runs through Postgres
- locks are scoped to a unit of work, not a global queue
- it is the smallest safe mechanism that prevents duplicate concurrent execution

Lock keys should be deterministic and derived from logical work:

- `mercado_publico:active_discovery:YYYY-MM-DD`
- `mercado_publico:rolling_window:YYYY-MM-DD:4d`
- `mercado_publico:detail_by_codigo:{codigo_externo}`
- `csv:licitaciones:YYYY-MM`
- `csv:ordenes_compra:YYYY-MM`

Do not use a global lock for the whole system.

If a later UI needs lock introspection, a dedicated lock table can be added in a future change, but it is not required for the first hardening slice.

### Budget strategy

The budget must be durable and transactional.

Recommended behavior:

1. count persisted ledger units for `provider + request_date`
2. compare against `MERCADO_PUBLICO_DAILY_REQUEST_LIMIT`
3. reserve or reject before the upstream call
4. store the ledger row together with the request outcome

The budget should not reset on process restart.

### Observability

Use structured events with the dotted namespace pattern already defined in the repo.

Required runtime context:

- `run_id`
- `provider`
- `mode`
- `requested_by`
- `request_hash`
- `request_date`
- `lock_key`
- `budget_used`
- `budget_limit`

Do not log tickets or other secrets.

### GitHub Actions

The workflow should be a separate operational lane from CI:

- `workflow_dispatch` for manual execution
- `schedule` for repeated runs
- secrets-only environment access
- fail fast on missing database URL, missing ticket, or budget exhaustion

The workflow should run the same operator script used locally, not a separate hidden code path.

### Supabase readiness

Supabase remains a readiness lane, not a cutover mandate.

The hardening change should:

- keep local Compose as the canonical day-to-day runtime
- keep the schema versioned and migration-backed
- ensure the API hardening works against Postgres local and Supabase remote
- keep historical backfill separate from operational sync

## Alternatives Considered

1. Add a dedicated lock table first.
   - Rejected for phase 1 because advisory locks are smaller and sufficient.
2. Replace the current API lane with a brand new ingestion stack.
   - Rejected because the current request/payload/snapshot lineage already exists and should be hardened, not discarded.
3. Keep budget tracking process-local.
   - Rejected because process-local state fails across restarts and concurrent jobs.

## Risks

- Advisory locks are invisible unless the job logs their acquisition and release.
- A durable budget ledger can be double-counted if reservation is not transactional.
- The current pluralized table names can create confusion if the logical contract is not documented clearly.
- A scheduled workflow can fail noisily if secrets or database URLs are not validated first.

## Mitigations

- log lock key acquisition and release with the run id
- reserve budget and write the ledger row in the same transaction where practical
- document the current-to-target mapping in the proposal and the design
- keep production config fail-fast
- keep Supabase readiness additive and separately documented
