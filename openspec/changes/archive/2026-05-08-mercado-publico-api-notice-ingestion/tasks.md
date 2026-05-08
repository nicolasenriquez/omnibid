## 1. Investigation and Contract Freeze

- [x] 1.1 Freeze the official licitaciones contract for active discovery, rolling-window refresh, and detail-by-code query shapes.
  Notes: use the ChileCompra API page plus the licitaciones PDF to lock `estado=activas`, `fecha=DDMMAAAA`, `codigo=...`, status codes, date format, and the fields that are actually returned in each query mode.
  Acceptance: the spec references only corroborated licitaciones fields and query shapes.
- [x] 1.2 Freeze scope boundaries.
  Notes: this change stays notice-only, backend-only, and operator-driven; CSV/manual historical loading and reconciliation remain the complementary path, not a hidden dependency of the API slice.
  Acceptance: proposal, design, and spec all agree on the same non-goals.
- [x] 1.3 Confirm the operational run identity.
  Notes: use a Mercado Público API `dataset_type` for `PipelineRun` tracking and keep the step names explicit for discovery, rolling refresh, and candidate-detail enrichment.
  Acceptance: the job lineage model is documented before implementation starts.

## Checkpoint: After 1.1-1.3
- [x] Contract shape is pinned
- [x] Scope boundaries are explicit
- [x] Run identity is documented
- [x] Ready to write tests first

## 2. Tests First

- [x] 2.1 Add client unit tests for config, URL building, and secret redaction.
  Notes: cover enabled-without-key fail-fast, canonical query params for active discovery and detail-by-code requests, and logs that never echo the ticket.
  Acceptance: tests fail before the client exists and pass once config and request builders are in place.
- [x] 2.2 Add client unit tests for the licitaciones response schema.
  Notes: cover active-discovery payloads, rolling-window payloads, detail-by-code payloads, date parsing, and explicit null handling for missing fields.
  Acceptance: mocked API payloads are parsed into stable models.
- [x] 2.3 Add persistence tests for request hash and payload hash behavior.
  Notes: request dedupe is keyed on canonical request parameters, not on the secret ticket; repeated discovery and rolling-window calls remain traceable.
  Acceptance: repeated requests do not create uncontrolled duplicate semantic rows.
- [x] 2.4 Add sync orchestration tests.
  Notes: cover active discovery, rolling-window refresh, candidate detail-by-code enrichment, 429/5xx retry exhaustion, contract drift, and empty-result handling.
  Acceptance: the job state machine is deterministic under mocks.

## Checkpoint: After 2.1-2.4
- [x] Tests fail for the intended reasons before implementation
- [x] Config and parsing contracts are captured
- [x] Ready for backend foundation work

## 3. Backend Foundation

- [x] 3.1 Extend `backend/core/config.py` and env examples.
  Notes: add Mercado Público API base URL, enabled flag, API key, timeout, retry budget, daily limit, and cache TTL settings; keep the key out of example env files.
  Acceptance: invalid or incomplete config fails fast.
- [x] 3.2 Implement `backend/integrations/mercado_publico/`.
  Notes: add client, schemas, enums, errors, and rate-limit helpers; keep request logs redacted; support active discovery, rolling refresh, and detail-by-code requests.
  Acceptance: the client can fetch the licitaciones endpoint for each supported query shape.
- [x] 3.3 Add `backend/models/api_source.py` and Alembic migration.
  Notes: create `api_source_request`, `api_source_payload`, and `mercado_publico_notice_snapshot` with indexes for hash and date lookups.
  Acceptance: schema is reversible and aligned with the ORM.
- [x] 3.4 Add persistence service for request, payload, and snapshot writes.
  Notes: implement in `backend/integrations/mercado_publico/store.py`; wrap writes in one transaction and preserve `pipeline_run_id` lineage.
  Acceptance: one daily run can persist metadata, raw JSON, and normalized notice rows atomically.

## Checkpoint: After 3.1-3.4
- [x] Config is wired
- [x] Client exists and is redacted
- [x] Schema and persistence are aligned
- [x] Ready for operator scripts and recipes

## 4. Daily Sync and Recipes

- [x] 4.1 Add `scripts/fetch_mp_api.py`.
  Notes: support a notice-only active-discovery mode, a rolling-window mode (`T` through `T-3`), and a candidate-detail-by-code mode; keep the script generic enough for later endpoint growth.
  Acceptance: the script can run the API sync without touching the CSV pipeline.
- [x] 4.2 Add `justfile` recipes.
  Notes: add smoke and job-specific recipes that wrap the new script and remain Docker-first.
  Acceptance: operators have one command for smoke and one command for each supported API sync mode.
- [x] 4.3 Wire job tracking through `PipelineRun` and `PipelineRunStep`.
  Notes: use a Mercado Público API dataset type and clear step names so the operations ledger stays readable.
  Acceptance: run history shows the API sync as its own operational job.

## Checkpoint: After 4.1-4.3
- [x] Operator entrypoint exists
- [x] Recipes are available
- [x] Run history is readable
- [x] Ready for docs and validation

## 5. Docs and Validation

- [x] 5.1 Add SDD and runbook docs.
  Notes: create `docs/references/sdd-mercado-publico-api-2026-05-04.md`, `docs/runbooks/mercado_publico_api_integration.md`, `docs/architecture/external_api_ingestion.md`, and `docs/evidence/mercado_publico_api_contract_smoke_YYYY-MM-DD.md`.
  Acceptance: the docs explain rate limits, nightly guidance, fail-fast behavior, API-first live discovery, and the CSV/manual boundary.
- [x] 5.2 Update `CHANGELOG.md`.
  Notes: capture the new API lane under Unreleased when implementation lands.
  Acceptance: delivery history reflects the new capability.
- [x] 5.3 Run validation.
  Notes: use the smallest backend-first command set that proves client, persistence, and sync behavior.
  Acceptance: unit tests, lint, type, and Docker smoke evidence are recorded.

## Checkpoint: Complete
- [x] Implementation is coherent
- [x] Documentation is aligned
- [x] Validation evidence is recorded
- [x] Ready for `/execute`
