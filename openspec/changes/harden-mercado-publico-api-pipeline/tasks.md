## 1. Contract and Documentation

- [x] 1.1 Freeze the hardening contract against the current Mercado Publico lane.
  Notes: document the mapping from `pipeline_run` to `pipeline_runs`, `api_request_ledger` to `api_source_request`, and `mp_notice_snapshot` to the current snapshot/payload pair.
  Notes: mapping is now explicit in `design.md` and `docs/architecture/external_api_ingestion.md` under "Current-to-Target Hardening Contract".
  Acceptance: the change is clearly additive to the current lane instead of duplicating it.
- [x] 1.2 Add or update the SDD note for this hardening phase.
  Notes: record the official Postgres, GitHub Actions, and Supabase sources used to justify locks, workflow triggers, and readiness boundaries.
  Notes: added `docs/references/sdd-mercado-publico-api-pipeline-hardening-2026-05-09.md` and indexed it in `docs/README.md`.
  Acceptance: the repo has a source-backed note that explains the operational hardening decision.
- [x] 1.3 Cross-link the runtime and data architecture docs.
  Notes: make the API lane, run ledger, and snapshot contract discoverable from the existing architecture docs.
  Notes: architecture cross-links now connect `system_architecture.md`, `external_api_ingestion.md`, `data_architecture.md`, and `data_model.md`.
  Acceptance: a future agent can locate the lane and its guardrails from repo docs alone.

## 2. Schema and Ledger Hardening

- [x] 2.1 Extend the operational tables with the missing hardening fields and constraints.
  Notes: add the durable run metadata, request budget fields, snapshot lineage fields, and idempotency constraints required by the spec.
  Notes: `pipeline_runs`, `api_source_request`, and `mercado_publico_notice_snapshot` now include hardening fields for run metadata, budget ledger, and snapshot lineage in ORM + Alembic.
  Acceptance: the database schema supports persistent budget, run lineage, and snapshot dedupe.
- [x] 2.2 Add or adjust indexes for the request ledger and snapshot lookup paths.
  Notes: optimize by provider, request date, request hash, pipeline run id, external code, and snapshot time.
  Notes: added composite indexes for provider/mode runs, source/day request lookups, and external notice + snapshot date/payload hash paths.
  Acceptance: the main operator and audit lookups are index-backed.
- [x] 2.3 Keep the migration reversible and additive.
  Notes: prefer additive migration steps and avoid changing Silver tables in this slice.
  Notes: added `alembic/versions/202605091540_mp_api_hardening.py` and validated `upgrade -> downgrade -1 -> upgrade` on temporary `db_test` smoke database `chilecompra_schema_smoke_20260509_2x`.
  Acceptance: Alembic can upgrade and downgrade cleanly.

## 3. Pipeline Services

- [x] 3.1 Implement durable request-budget enforcement.
  Notes: make the budget persistent across restarts and enforce it before upstream calls.
  Notes: added DB-backed reservation in `backend/integrations/mercado_publico/store.py::reserve_request_budget` using day-scoped advisory transaction lock and persisted ledger rows before API calls.
  Acceptance: a new run cannot silently exceed the daily limit.
- [x] 3.2 Implement run lifecycle handling for Mercado Publico syncs.
  Notes: create, update, and finalize the run record with requested-by, parameters, stats, and error summary.
  Notes: sync run creation/completion/failure now writes `provider`, `run_mode`, `requested_by`, `run_parameters_json`, `run_stats_json`, and durable final status metadata.
  Acceptance: every execution ends with a durable final status.
- [x] 3.3 Implement snapshot persistence and dedupe hardening.
  Notes: keep raw payloads and queryable notice snapshots separate but linked.
  Notes: snapshot writes now persist `source_mode`, `payload_sha256`, `observed_at`, and continue idempotent upsert semantics per notice/payload identity.
  Acceptance: repeated payloads do not create accidental duplicate semantic rows.
- [x] 3.4 Implement scoped advisory locking.
  Notes: lock per logical unit of work, not per whole system.
  Notes: added `pg_try_advisory_lock` guards in sync execution for `active-discovery`, `rolling-window` (per date/window/estado), and `detail-by-codigo` work units.
  Acceptance: concurrent identical runs do not execute together.

## 4. Operator Entry Points

- [x] 4.1 Extend `scripts/fetch_mp_api.py`.
  Notes: add dry-run, max-requests, requested-by, and optional explicit date/window bounds.
  Notes: added `--max-requests`, `--requested-by`, `--start-date`, `--end-date` and rolling-window bound normalization with fail-fast validation; dry-run now prints resolved operational plan.
  Acceptance: the CLI can show the plan without writing data.
- [x] 4.2 Keep the daily pipeline runner compatible with the new metadata.
  Notes: preserve the current daily API sync plus Silver refresh behavior.
  Notes: daily runner now accepts `--requested-by` and `--max-requests` and propagates both into `run_mp_api_daily_notice_pipeline` and run metadata without altering sync+Silver composition.
  Acceptance: the daily runner still composes the same operational stages.
- [x] 4.3 Add or update a GitHub Actions workflow for scheduled sync.
  Notes: use dispatch and schedule triggers with secrets only.
  Notes: added `.github/workflows/mp-api-sync.yml` with `schedule` + `workflow_dispatch`, fail-fast secret validation, and backend container execution using `MP_API_DATABASE_URL` + `MERCADO_PUBLICO_API_KEY` secrets only.
  Acceptance: the workflow can be run manually and on a timer without exposing secrets.

## 5. Tests

- [x] 5.1 Add unit coverage for budget, redaction, and idempotency.
  Notes: cover the same-day budget limit, the safe URL contract, and repeat-request behavior.
  Notes: added `tests/unit/test_mercado_publico_store.py` coverage for same-day budget ceiling, same-day repeat idempotent reservation, and persisted safe URL ticket non-disclosure.
  Acceptance: the tests fail before the implementation and pass after it.
- [x] 5.2 Add unit or integration coverage for run lifecycle and locking.
  Notes: cover running/succeeded/failed/partial transitions and same-key lock contention.
  Notes: added `tests/unit/test_mercado_publico_sync.py` lifecycle assertions for run creation + success/failure finalization metadata and a lock-contention fast-fail test that prevents upstream execution.
  Acceptance: the job lifecycle and lock contract are proven.
- [x] 5.3 Add coverage for dry-run and production safety.
  Notes: dry-run must not write data, and production config must reject weak defaults.
  Notes: added production DB safety guard in `scripts/fetch_mp_api.py` and tests in `tests/unit/test_fetch_mp_api_script.py` for dry-run no-session path plus production rejection of localhost/default postgres credentials.
  Acceptance: the operator path is safe to use in CI and local validation.

## 6. Docs and Handoff

- [x] 6.1 Update the Mercado Publico runbook.
  Notes: document the new operator flags, the persistent budget behavior, and the lock strategy.
  Notes: updated `docs/runbooks/mercado_publico_api_integration.md` with `--requested-by`, `--max-requests`, explicit date-range options, persistent budget semantics, scoped lock strategy, and production fail-fast safety notes.
  Acceptance: an operator can run the lane without reading implementation code.
- [x] 6.2 Update Supabase readiness docs if the contract changes.
  Notes: keep the transition lane additive and separate from historical migration work.
  Notes: updated `docs/operations/supabase-readiness.md` baseline with explicit additive-boundary statement for Mercado Publico API hardening and no-runtime-switch/no-backfill guarantees.
  Acceptance: local Compose and Supabase remote remain clearly separated but compatible.
- [x] 6.3 Record the validation evidence.
  Notes: run the smallest useful smoke set first, then the broader quality gates.
  Notes: smoke-first evidence:
  - `rtk docker compose run --rm --no-deps backend-tools uv run --no-sync python scripts/fetch_mp_api.py --mode active-discovery --dry-run --requested-by unit_test --max-requests 3`
  - `rtk docker compose run --rm --no-deps backend-tools uv run --no-sync python scripts/run_mp_api_daily_pipeline.py --dry-run --requested-by unit_test --max-requests 3`
  Notes: targeted gate evidence:
  - `rtk docker compose run --rm --no-deps backend-tools uv run --no-sync pytest -q tests/unit/test_core_config.py tests/unit/test_mercado_publico_sync.py tests/unit/test_mercado_publico_store.py` -> `32 passed`
  - `rtk docker compose run --rm --no-deps backend-tools uv run --no-sync ruff check backend/core/config.py backend/integrations/mercado_publico/sync.py tests/unit/test_core_config.py tests/unit/test_mercado_publico_sync.py tests/unit/test_mercado_publico_store.py` -> `All checks passed`
  Acceptance: the change has a clear verification trail before implementation merge.
