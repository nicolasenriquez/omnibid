# SDD: Mercado Publico API Notice Ingestion

## Decision

Implement a backend-only, operator-driven Mercado Publico API ingestion lane for notices, with three query modes:

- active discovery (`estado=activas`)
- rolling window (`fecha=T..T-3`, `DDMMAAAA`)
- detail by notice code (`codigo`)

The implementation keeps fail-fast config validation, ticket redaction in logs and canonical hashes, and explicit operational lineage through `PipelineRun` and `PipelineRunStep`.

## Verified Official Sources

1. Mercado Publico public API page
   - https://api.mercadopublico.cl/
   - Confirms public service base URL and licitaciones endpoint family.
2. Mercado Publico API licitaciones PDF guide
   - https://api.mercadopublico.cl/modules/mercadopublico/licitaciones-v1.pdf
   - Confirms request shapes (`estado`, `fecha`, `codigo`), date format (`DDMMAAAA`), and response field expectations used in parsing/contract tests.

## Repo Contract Alignment

- Config surface:
  - `MERCADO_PUBLICO_API_ENABLED`
  - `MERCADO_PUBLICO_API_KEY`
  - `MERCADO_PUBLICO_BASE_URL`
  - `MERCADO_PUBLICO_TIMEOUT_SECONDS`
  - `MERCADO_PUBLICO_RETRY_BUDGET`
  - `MERCADO_PUBLICO_DAILY_REQUEST_LIMIT`
  - `MERCADO_PUBLICO_CACHE_TTL_SECONDS`
- Secret handling:
  - request canonicalization excludes `ticket`
  - request hash is derived from canonical params
  - safe URLs redact sensitive query values
- Persistence lineage:
  - `api_source_request`
  - `api_source_payload`
  - `mercado_publico_notice_snapshot`
  - linked to `pipeline_run_id`

## Validation Snapshot

Container-first checks used for this slice:

- `just lint`
- `just type`
- `just test-unit`
- `just mp-api-smoke`

See `docs/evidence/mercado_publico_api_contract_smoke_2026-05-08.md` for run evidence.
