## 1. Investigation and Contract Freeze

- [ ] 1.1 Freeze the official licitaciones contract for the daily published-notice slice.
  Notes: use the ChileCompra API page plus the licitaciones PDF to lock `fecha=YYYYMMDD`, `estado=publicada`, status codes, date format, and required fields.
  Acceptance: the spec references only corroborated licitaciones fields and query shapes.
- [ ] 1.2 Freeze scope boundaries.
  Notes: this change stays notice-only, backend-only, and operator-driven; no OC, buyer, or supplier endpoints in this slice.
  Acceptance: proposal, design, and spec all agree on the same non-goals.
- [ ] 1.3 Confirm the operational run identity.
  Notes: use a new API-oriented `dataset_type` for `PipelineRun` tracking and keep CSV runs unchanged.
  Acceptance: the job lineage model is documented before implementation starts.

## 2. Tests First

- [ ] 2.1 Add client unit tests for config, URL building, and secret redaction.
  Notes: cover enabled-without-ticket fail-fast, canonical query params, and logs that never echo the ticket.
  Acceptance: tests fail before the client exists and pass once config and request builders are in place.
- [ ] 2.2 Add client unit tests for the licitaciones response schema.
  Notes: cover daily published notices, state codes, date parsing, and explicit null handling for missing fields.
  Acceptance: mocked API payloads are parsed into stable Pydantic models.
- [ ] 2.3 Add persistence tests for request hash and payload hash behavior.
  Notes: request dedupe is keyed on canonical request parameters, not on the secret ticket; identical payloads remain traceable.
  Acceptance: repeated requests do not create uncontrolled duplicate semantic rows.
- [ ] 2.4 Add sync orchestration tests.
  Notes: cover success, 429/5xx retry exhaustion, contract drift, and empty-result handling.
  Acceptance: the job state machine is deterministic under mocks.

## 3. Backend Foundation

- [ ] 3.1 Extend `backend/core/config.py` and env examples.
  Notes: add Mercado Público API base URL, enabled flag, ticket, timeout, retry budget, daily limit, and cache TTL settings.
  Acceptance: invalid or incomplete config fails fast.
- [ ] 3.2 Implement `backend/integrations/mercado_publico/`.
  Notes: add client, schemas, enums, errors, and rate-limit helpers; keep request logs redacted.
  Acceptance: the client can fetch the licitaciones endpoint for a canonical daily published-notice query.
- [ ] 3.3 Add `backend/models/api_source.py` and Alembic migration.
  Notes: create `api_source_request`, `api_source_payload`, and `mercado_publico_notice_snapshot` with indexes for hash and date lookups.
  Acceptance: schema is reversible and aligned with the ORM.
- [ ] 3.4 Add persistence service for request, payload, and snapshot writes.
  Notes: implement in `backend/integrations/mercado_publico/store.py`; wrap writes in one transaction and preserve `pipeline_run_id` lineage.
  Acceptance: one daily run can persist metadata, raw JSON, and normalized notice rows atomically.

## 4. Daily Sync and Recipes

- [ ] 4.1 Add `scripts/fetch_mp_api.py`.
  Notes: support a notice-only daily mode that fetches `licitaciones` for `estado=publicada`; keep the script generic enough for later endpoint growth.
  Acceptance: the script can run the daily sync without touching the CSV pipeline.
- [ ] 4.2 Add `justfile` recipes.
  Notes: add smoke and daily-sync recipes that wrap the new script and remain Docker-first.
  Acceptance: operators have one command for smoke and one command for the daily notice sync.
- [ ] 4.3 Wire job tracking through `PipelineRun` and `PipelineRunStep`.
  Notes: use a Mercado Público API dataset type and clear step names so the operations ledger stays readable.
  Acceptance: run history shows the API sync as its own operational job.

## 5. Docs and Validation

- [ ] 5.1 Add SDD and runbook docs.
  Notes: create `docs/references/sdd-mercado-publico-api-2026-05-04.md`, `docs/runbooks/mercado_publico_api_integration.md`, `docs/architecture/external_api_ingestion.md`, and `docs/evidence/mercado_publico_api_contract_smoke_YYYY-MM-DD.md`.
  Acceptance: the docs explain rate limits, nightly guidance, fail-fast behavior, and scope boundaries.
- [ ] 5.2 Update `CHANGELOG.md`.
  Notes: capture the new API lane under Unreleased when implementation lands.
  Acceptance: delivery history reflects the new capability.
- [ ] 5.3 Run validation.
  Notes: use the smallest backend-first command set that proves client, persistence, and sync behavior.
  Acceptance: unit tests, lint, type, and Docker smoke evidence are recorded.
