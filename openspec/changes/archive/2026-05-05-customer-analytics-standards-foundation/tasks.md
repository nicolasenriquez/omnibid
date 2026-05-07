## 1. Standard and Traceability

- [x] 1.1 Create `docs/standards/customer-analytics-standards.md`.
  Notes: the document must cover source profiles, runtime/env contract, deterministic ingestion, identity and grain, Silver boundary, validation, and official sources.
  Acceptance: a future agent can read one standard and understand the procurement analytics contract without reconstructing it from scattered docs.
- [x] 1.2 Create `docs/references/sdd-customer-analytics-standards-2026-05-05.md`.
  Notes: capture the official URLs and the repository context used to write the standard.
  Acceptance: the note is linked from future implementation work.

## 2. Registry and Baseline Alignment

- [x] 2.1 Update `docs/references/sdd-official-sources-registry.md`.
  Notes: add the Python stdlib modules used by the pipeline and the versioned PostgreSQL 16 reference.
  Acceptance: future agents have a single registry entry point for the official docs used by this change.
- [x] 2.2 Align `docs/standards/postgres-standard.md` with the effective Compose image.
  Notes: keep the baseline and source URL consistent with `postgres:16-alpine`.
  Acceptance: no doc in this slice still claims PostgreSQL 18 as the current runtime baseline.

## 3. Pipeline Contract Code

- [x] 3.1 Add or extend source-profile routing helpers under `backend/pipeline/`.
  Notes: make the current CSV profile explicit in code and keep unknown or unsupported profiles fail-fast; `csv_drop` is the only implemented profile in the current pipeline and `api_json` / `open_data_snapshot` are rejected until a separate adapter slice exists.
  Acceptance: the pipeline surface routes through an explicit contract instead of ad hoc branching.
- [x] 3.2 Add runtime validation for the DB/env split.
  Notes: keep host and Docker settings separate and fail fast on missing or inconsistent database settings; `backend/core/config.py` now requires both `DATABASE_URL` and `TEST_DATABASE_URL` and rejects mixed host/Docker families.
  Acceptance: DB-backed work cannot proceed with an invalid runtime contract.
- [x] 3.3 Tighten the existing contract helpers used by ingestion and pipeline orchestration.
  Notes: keep `backend/ingestion/contracts.py`, `backend/core/config.py`, and `backend/pipeline/application.py` aligned with the standard; unsupported dataset types now fail fast before ingestion or normalized build routing.
  Acceptance: the code paths used by the current CSV pipeline stay canonical and explicit.
- [x] 3.4 Add unit tests for routing and runtime validation.
  Notes: cover source-profile routing, dataset-type rejection, and env validation edge cases; covered by `tests/unit/test_pipeline_application_module.py`, `tests/unit/test_ingestion_contracts.py`, and `tests/unit/test_core_config.py`.
  Acceptance: the tests prove the new guardrails without requiring a schema migration.

## 4. Validation and Handoff

- [x] 4.1 Review the docs and code for internal consistency.
  Notes: check that the source profile names, env split, Silver boundary language, and pipeline code do not conflict with the codebase; reviewed against the customer analytics standard, PostgreSQL baseline doc, runtime config, and pipeline entrypoints.
  Acceptance: the proposal is ready for implementation planning.
- [x] 4.2 Keep the runtime schema unchanged in this slice.
  Notes: the change adds contract code and tests, not a Silver schema rewrite; no schema migration or table shape change was introduced in this slice.
  Acceptance: no backend migration is required before a separate implementation proposal.
