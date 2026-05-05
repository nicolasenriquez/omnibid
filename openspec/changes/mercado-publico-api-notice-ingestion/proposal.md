## Why

Omnibid already has deterministic CSV ingestion, canonical normalization, Silver procurement-cycle modeling, and read-only opportunity APIs. What it does not yet have is a safe Mercado Público API lane that can answer, every day, which licitaciones were published, without hand-downloading files, duplicating requests, or wiring ChileCompra directly into the frontend.

The official ChileCompra API page and licitaciones PDF confirm the needed operational shape:
- licitaciones data is available through GET requests under `https://api.mercadopublico.cl/servicios/v1/publico`
- access requires a ticket requested with Clave Unica
- the documented daily request limit is 10,000 per ticket
- high-volume use is recommended between 22:00 and 07:00
- licitaciones can be queried by date, state, active status, code, buyer, and supplier
- the licitacion contract exposes stable fields and status codes suitable for a daily published-notice snapshot
- The terminology boundary stays explicit: integration internals keep `request`, `payload`, `snapshot`, and `notice` as technical nouns, while adjacent product copy must use Spanish business terms such as `licitación`, `código externo`, `estado oficial`, `organismo comprador`, and `unidad de compra`.

This lane is an upstream data freshness step for the same procurement-intelligence program. It can later feed the Silver-to-Gold decision stack, but it does not replace the CSV foundation and it does not depend on the workspace change.

## What Changes

- Add a Mercado Público API client foundation for licitaciones only in this change.
- Add fail-fast config, ticket validation, redacted logging, and bounded retry/backoff.
- Add API request and payload ledger tables with request hash and payload hash tracking.
- Add a queryable published-notice snapshot table and a daily sync job.
- Add tests, SDD docs, runbook, and operator recipes.
- Keep CSV ingestion, current Silver tables, and frontend untouched in this slice.

## Capabilities

### New Capabilities

- `mercado-publico-api-client-foundation`
- `mercado-publico-api-request-ledger`
- `mercado-publico-notice-snapshot-read-model`
- `mercado-publico-daily-notice-sync`
- `mercado-publico-api-ops-runbook`

### Modified Capabilities

- None.

## Impact

- `backend/core/config.py`
- `backend/integrations/mercado_publico/`
- `backend/models/api_source.py`
- `alembic/versions/`
- `scripts/fetch_mp_api.py`
- `justfile`
- `tests/unit/integrations/`
- `tests/integration/`
- `docs/references/sdd-mercado-publico-api-2026-05-04.md`
- `docs/runbooks/mercado_publico_api_integration.md`
- `docs/architecture/external_api_ingestion.md`
- `docs/evidence/mercado_publico_api_contract_smoke_YYYY-MM-DD.md`
- `CHANGELOG.md`

Not impacted in this slice:
- `backend/main.py`
- `backend/api/routers/`
- `client/`
- existing CSV raw/normalized/Silver pipeline
