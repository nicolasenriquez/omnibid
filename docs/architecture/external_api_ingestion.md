# External API Ingestion Architecture

## Purpose

Define the architecture boundary for external API ingestion, starting with Mercado Publico notice sync.

## Boundary

- In scope:
  - external API request execution
  - response contract parsing
  - request/payload persistence
  - notice snapshot materialization
  - operator-run orchestration and run ledger tracking
- Out of scope:
  - CSV/manual historical import replacement
  - cross-source reconciliation workflows
  - frontend mutation workflows

## Components

## Current-to-Target Hardening Contract

The hardening phase is additive to the existing Mercado Publico lane and keeps current persisted surfaces as the contract baseline:

- logical `pipeline_run` -> current `pipeline_runs`
- logical `api_request_ledger` -> current `api_source_request`
- logical `raw_payload_archive` -> current `api_source_payload`
- logical `mp_notice_snapshot` -> current `mercado_publico_notice_snapshot`

This mapping is the default for `harden-mercado-publico-api-pipeline`; no parallel ingestion stack is introduced in this slice.

### Configuration

- `backend/core/config.py`
- `backend/integrations/mercado_publico/config.py`

Provides fail-fast settings and runtime validation for API enablement, key presence, timeout, retries, and request budgets.

### API Client

- `backend/integrations/mercado_publico/client.py`
- `backend/integrations/mercado_publico/rate_limit.py`

Responsibilities:
- build canonical request params per mode
- execute upstream calls with bounded retry policy
- redact sensitive query params in safe URL surfaces
- parse payloads into strict typed schema models

### Persistence

- `backend/integrations/mercado_publico/store.py`
- `backend/models/api_source.py`

Tables:
- `api_source_request`
- `api_source_payload`
- `mercado_publico_notice_snapshot`

Key rules:
- request hash based on canonical non-secret parameters
- payload hash based on deterministic JSON serialization
- snapshots linked to request + payload + pipeline run

### Orchestration

- `backend/integrations/mercado_publico/sync.py`
- `scripts/fetch_mp_api.py`
- `backend/pipeline/orchestration/daily_pipeline.py`
- `backend/pipeline/orchestration/sync.py`
- `scripts/run_mp_api_daily_pipeline.py`

Modes:
- `active-discovery`
- `rolling-window`
- `detail-by-codigo`
- `daily rolling-window + selective detail + canonicalization + Silver postprocess`

Operational lineage:
- dataset type: `mercado_publico_api_notice`
- step names:
  - `mp_api_discovery_active`
  - `mp_api_rolling_refresh`
  - `mp_api_detail_enrichment`
  - `mp_api_payload_canonicalization` (daily pipeline only)
  - `mp_api_silver_postprocess` (daily pipeline only)

Daily pipeline behavior:
- one parent run composes rolling sync + selective detail sync + canonicalization + Silver postprocess
- logical API snapshot artifact is registered in `source_files`
- read-model canonicalization uses existing transform builders and complete-only upsert semantics
- `silver_notice` upsert keeps stable `notice_id` and deterministic row hash
- replay can run from persisted snapshots without upstream API calls

### Operator Surface

- `just mp-api-smoke`
- `just mp-api-sync-active`
- `just mp-api-sync-rolling`
- `just mp-api-sync-detail`
- `just mp-api-daily-refresh`

All recipes are Docker-first and build-aware so command execution uses current image contents.

## Reliability and Security

- Fail-fast config validation before runtime operations.
- Retry budget bounded by configuration.
- Daily request budget guard.
- Secret ticket excluded from canonical request hash and redacted in safe URL/logging paths.
- Clear error propagation for upstream exhaustion and contract drift.

## Related Architecture Docs

- runtime and module boundaries: `docs/architecture/system_architecture.md`
- data layers and read-model boundaries: `docs/architecture/data_architecture.md`
- operational table inventory and lineage context: `docs/architecture/data_model.md`
