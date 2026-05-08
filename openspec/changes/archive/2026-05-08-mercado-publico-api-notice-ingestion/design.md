## Context

This change adds a notice-only Mercado Público API lane. It is backend-only, operator-driven, and separate from the existing CSV pipeline. The first slice ends at a queryable published-notice snapshot plus request/payload lineage. It does not try to remap the data into current Silver tables yet.

The repo already has reusable operational primitives:
- `PipelineRun` and `PipelineRunStep` for job tracking
- Docker-first `just` recipes for runtime and verification
- structured config through `backend/core/config.py`
- a Docker backend image that installs the runtime with `uv sync --frozen --no-dev`

The operating model is API-first for live opportunities and CSV/manual for history:
- API discovery is the live sensor for current opportunities.
- CSV/manual loading stays the historical, backfill, and reconciliation path.
- Current API work should stay notice-only and backend-only.

That means this change can stay narrow:
- no frontend work
- no new public routes
- no CSV pipeline rewrites
- no direct Silver writes in the first slice
- no new runtime dependency churn in the backend image

## Verified Official Sources

1. `https://www.chilecompra.cl/api/`
   - API overview, ticket flow, daily limit, and nightly usage guidance.
2. `https://www.chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-Licitaciones.pdf`
   - licitacion field list, date format, and status codes.
3. `https://www.chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-oc.pdf`
   - future-scope reference only; not used in this change.
4. `docs/references/sdd-market-public-business-and-data-sources-2026-05-02.md`
   - repo-local business/source framing already exists and is consistent with an API-first live-opportunity lane.
5. `docs/references/sdd-mercado-publico-api-2026-05-04.md`
   - planned repo-local decision note for this API lane.

## Terminology Boundary

- Internal integration nouns stay technical: `request`, `payload`, `snapshot`, `notice`, and hash fields.
- Any adjacent business copy should use Spanish procurement language with accents: `licitación`, `código externo`, `estado oficial`, `organismo comprador`, `unidad de compra`, `publicación`, `cierre`, `monto estimado`.
- Do not surface raw internal field names as visible UI labels.

## Goals

- Fetch published licitaciones from Mercado Público using live-opportunity discovery and bounded refreshes.
- Persist raw request metadata, raw payload snapshots, and a queryable notice snapshot.
- Fail fast when the API is enabled but the key or core settings are invalid.
- Keep secret material out of logs and persisted telemetry.
- Make the sync idempotent by request hash and payload hash.
- Keep CSV/manual flows as the historical and reconciliation path.
- Keep the runtime dependency set stable by using the standard library HTTP client in the production slice.

## Non-Goals

- OC, buyer, or supplier endpoints in this change.
- Frontend calls to ChileCompra.
- Replacing CSV/manual historical loading or reconciliation.
- Writes into the current Silver procurement-cycle tables.
- Batch backfill of historical API data through this slice alone.
- Public dashboard, alerts, or notification delivery in this slice.

## Decisions

1. API-first for current opportunities, CSV/manual for historical backfill and reconciliation.
   - Mercado Público APIs are the operational sensor for live licitaciones.
   - CSV/manual remains the historical truth source and reconciliation path.

2. Notice-only first slice.
   - The first implementation focuses on published licitaciones only.
   - OC and entity lookup endpoints are follow-up work, not hidden dependencies.

3. Use active discovery and bounded refreshes.
   - `estado=activas` is the primary live-discovery query.
   - A short rolling window (`T`, `T-1`, `T-2`, `T-3`) captures late arrivals and status changes.
   - Code-based queries are reserved for candidate notices that deserve detail.

4. Use dedicated API lineage tables.
   - Persist API request metadata and raw payloads separately from CSV lineage.
   - Do not reuse `SourceFile` for remote JSON responses in this slice.

5. Use a queryable notice snapshot.
   - Store one normalized row per published notice so operators can inspect daily and intra-day results without parsing raw JSON.
   - Keep the snapshot table separate from current Silver tables.

6. Reuse operational run tracking.
   - `PipelineRun` and `PipelineRunStep` can track the API sync job with a Mercado Público dataset type and clear step names for discovery, refresh, and enrichment.
   - This gives run/step lineage without new operational tables.

7. Fail fast, do not guess.
   - If the API is enabled and the key is missing, start-up or client creation fails immediately.
   - If the upstream contract drifts, the job fails before partial persistence escapes the transaction.

8. Keep the sync backend-only.
   - No frontend direct calls to ChileCompra.
   - No new UI work in this change.

9. Keep the runtime HTTP client dependency-free.
   - Use the Python standard library in the production slice so the backend no-dev image does not need package churn.
   - Tests can still use the existing dev toolchain, but production code should not depend on a new runtime package.

## Architecture

### Flow

```text
Mercado Público licitaciones endpoint
  -> active discovery / rolling refresh / candidate detail-by-code
  -> MercadoPublicoClient
  -> api_source_request
  -> api_source_payload
  -> mercado_publico_notice_snapshot
  -> operator sync command / DB query
```

### Components

- `backend/integrations/mercado_publico/config.py`
  - settings access and validation glue.
- `backend/integrations/mercado_publico/client.py`
  - request builder, key injection, redaction, retry/backoff, response parsing.
- `backend/integrations/mercado_publico/schemas.py`
  - models for the licitaciones response contract.
- `backend/integrations/mercado_publico/enums.py`
  - notice state codes and text labels.
- `backend/integrations/mercado_publico/errors.py`
  - typed failures for config, contract drift, upstream errors, and rate-limit exhaustion.
- `backend/integrations/mercado_publico/rate_limit.py`
  - local daily limit tracking and bounded retry policy.
- `backend/models/api_source.py`
  - request ledger, raw payload snapshot, and published-notice snapshot ORM.
- `backend/integrations/mercado_publico/store.py`
  - persistence helpers for request, payload, and snapshot writes.
- `scripts/fetch_mp_api.py`
  - generic operator entrypoint for active discovery, rolling refresh, and candidate detail enrichment.
- `justfile`
  - recipes for smoke, job-specific syncs, and focused validation.

## Data Model

### `api_source_request`

Purpose:
- one row per normalized API request intent
- dedupe key for repeated requests

Core fields:
- `id`
- `pipeline_run_id`
- `source_system`
- `endpoint_name`
- `resource_type`
- `resource_key`
- `request_params_json`
- `request_hash`
- `requested_at`
- `completed_at`
- `http_status`
- `success`
- `error_type`
- `error_message`
- `response_payload_id`
- `cache_hit`
- `rate_limit_day`

Rules:
- `request_hash` excludes ticket material.
- request parameters are canonicalized before hashing.
- one ticket-day counter can be derived from `rate_limit_day`.

### `api_source_payload`

Purpose:
- immutable raw JSON snapshot for each successful or intentionally retained response

Core fields:
- `id`
- `pipeline_run_id`
- `source_system`
- `endpoint_name`
- `resource_type`
- `resource_key`
- `fetched_at`
- `payload_json`
- `payload_sha256`
- `api_version`
- `source_fecha_creacion`
- `source_count`
- `schema_observed_keys`

Rules:
- payloads are append-only snapshots.
- identical JSON can reuse dedupe logic, but the raw hash remains visible.

### `mercado_publico_notice_snapshot`

Purpose:
- query-friendly daily and intra-day published-notice read model

Core fields:
- `id`
- `pipeline_run_id`
- `request_id`
- `payload_id`
- `endpoint_name`
- `resource_key`
- `notice_id`
- `external_notice_code`
- `notice_title`
- `official_status_code`
- `official_status_name`
- `publication_date`
- `close_date`
- `buyer_org_code`
- `buyer_org_name`
- `buyer_unit_code`
- `buyer_unit_name`
- `currency_code`
- `estimated_amount`
- `snapshot_date`
- `synced_at`

Rules:
- one row per notice in the published slice.
- fields remain explicit `null` when the API omits them.
- snapshot is queryable without reopening raw JSON.

## Failure Modes

1. Missing key or disabled config.
   - Fail before request execution.

2. Contract drift.
   - Fail before partial commit.
   - Do not infer missing fields.

3. 429, timeouts, or 5xx responses.
   - Retry only within bounded policy.
   - Stop once upstream limits or retry budget are exhausted.

4. Duplicate request intent.
   - Reuse the request hash and cached payload path when applicable.
   - Do not create duplicate semantic work for the same canonical request.

5. Secret leakage.
   - The ticket never gets logged, stored, or echoed in request diagnostics.

## Blast Radius

### Current slice

- config surface expands in `backend/core/config.py`
- new integration package under `backend/integrations/mercado_publico/`
- new ORM file plus Alembic revision
- new operator script and `justfile` recipes
- new tests for client, ledger, and sync behavior
- new docs in `docs/references/`, `docs/runbooks/`, and `docs/architecture/`

### Downstream

- future change may map the notice snapshot into `silver_notice` and the existing `/opportunities` read model
- future change may add `ordenesdecompra` and entity lookup endpoints
- operations list will show a new `dataset_type` for API sync runs
- future follow-up may add explicit API sync state tables if the operator cadence needs deeper observability

### Blocking vs non-blocking

- Blocking: missing key handling, contract drift handling, and duplicate request hashing must be explicit before execution.
- Non-blocking by design: Silver convergence, OC integration, and buyer/supplier lookups are follow-up work.

## Validation Strategy

- unit tests first for client validation and response parsing
- DB-backed tests for request/payload/snapshot persistence
- targeted sync smoke test with mocked HTTP
- Docker-first runtime verification

## Open Questions

None.
