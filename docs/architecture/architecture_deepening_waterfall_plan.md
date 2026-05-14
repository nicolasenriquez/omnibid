# Architecture Deepening Waterfall Plan

## Scope

This plan sequences architecture deepening work into safe, dependency-ordered tasks.
Each task must pass its validation gate before the next task starts.

## Guardrails

- Docker-first execution path for validation.
- No schema drift unless explicitly required by a task.
- No behavior expansion while extracting seams.
- Keep routers thin; move cross-cutting logic into dedicated modules.

## Completed in This Branch

### Task 1 - Shared Dataset Summary Module seam

- Added shared summary module used by both operations and manual upload adapters.
- Removed duplicate dataset summary implementations from both routers.

Exit criteria:
- identical response keys and semantics
- no route behavior changes

Validation:
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync ruff check backend/api/dataset_summary.py backend/api/routers/manual_uploads.py backend/api/routers/operations.py tests/unit/test_dataset_summary_module.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync mypy backend/api/dataset_summary.py backend/api/routers/manual_uploads.py backend/api/routers/operations.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync pytest -q tests/unit/test_dataset_summary_module.py tests/unit/test_manual_uploads.py tests/unit/test_operations_api.py tests/unit/test_operations_summary_snapshots.py`

### Task 2 - Documentation/interface alignment seam

- Updated docs to mark investigation endpoints as planned/not wired.
- Removed stale "currently implemented" language where runtime wiring does not exist.

Exit criteria:
- docs API surface matches `backend/main.py` includes

Validation:
- static doc diff review
- `rg --line-number 'investigation|investigations' README.md docs/architecture/system_architecture.md backend/main.py`

### Task 3 - Pipeline application seam scaffold

- Added pipeline application module to host manual-upload pipeline adapters.
- Router now calls one adapter for raw ingest and one adapter for normalized build.
- Removed direct script imports from `manual_uploads` router.

Exit criteria:
- manual upload success path remains unchanged
- dataset routing (`licitacion` vs `orden_compra`) remains deterministic

Validation:
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync ruff check backend/pipeline/application.py backend/api/routers/manual_uploads.py tests/unit/test_pipeline_application_module.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync mypy backend/pipeline/application.py backend/api/routers/manual_uploads.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync pytest -q tests/unit/test_pipeline_application_module.py tests/unit/test_manual_uploads.py`

### Task 4 - Manual upload transport adapter seam

- Moved multipart parsing into a dedicated transport module.
- Router now delegates request parsing to transport adapter interface.
- Added focused tests for malformed body, missing dataset, and multi-file rejection.

Exit criteria:
- identical upload parsing error semantics
- router preflight continues to emit the same validation behavior

Validation:
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync ruff check backend/api/manual_upload_transport.py backend/api/routers/manual_uploads.py tests/unit/test_manual_upload_transport.py tests/unit/test_manual_uploads.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync mypy backend/api/manual_upload_transport.py backend/api/routers/manual_uploads.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync pytest -q tests/unit/test_manual_upload_transport.py tests/unit/test_manual_uploads.py`

### Task 5 - Opportunity filters deep module seam

- Added dedicated opportunities query interface module for shared filter generation.
- Centralized list/count/summary filter SQL construction behind one interface.
- Moved shared filter parameter mapping out of the router.

Exit criteria:
- list/count/summary continue consuming one shared parameter contract
- opportunities filter semantics stay stable under existing tests

Validation:
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync ruff check backend/api/opportunities_query.py backend/api/routers/opportunities.py tests/unit/test_opportunities_query.py tests/unit/test_opportunity_workspace_api.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync mypy backend/api/opportunities_query.py backend/api/routers/opportunities.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync pytest -q tests/unit/test_opportunities_query.py tests/unit/test_opportunity_workspace_api.py`

### Task 6 - Typed backend/frontend contract seam

- Added explicit opportunities response contract models in backend.
- Wired opportunities routes to enforce response models at route seam.
- Normalized purchase-order detail payload to include stable contract fields.
- Aligned frontend type for line correlative with backend numeric contract.

Exit criteria:
- backend opportunities responses validate against one explicit contract
- frontend type surface matches emitted payload shape for opportunities detail/list/summary

Validation:
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync ruff check backend/api/opportunities_contract.py backend/api/opportunities_query.py backend/api/routers/opportunities.py tests/unit/test_opportunities_contract_models.py tests/unit/test_opportunities_query.py tests/unit/test_opportunity_workspace_api.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync mypy backend/api/opportunities_contract.py backend/api/opportunities_query.py backend/api/routers/opportunities.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync pytest -q tests/unit/test_opportunities_contract_models.py tests/unit/test_opportunities_query.py tests/unit/test_opportunity_workspace_api.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm client sh -lc 'corepack enable && corepack prepare pnpm@11.0.8 --activate && pnpm typecheck'`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm client sh -lc 'corepack enable && corepack prepare pnpm@11.0.8 --activate && pnpm lint'`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm client sh -lc 'corepack enable && corepack prepare pnpm@11.0.8 --activate && pnpm build'`

## Remaining Waterfall Tasks

### Task 7 - Workspace UI deep module decomposition

Goal:
- split `workspace.tsx` by query-state, upload state machine, detail panel, and view adapters.

Unlocks:
- reduced state/effect coupling and better behavior test locality.

Validation gate:
- existing workspace tests and build
- manual smoke on `/licitaciones`

Progress:
- Slice 7.1 complete: extracted query-state seam (`useOpportunityWorkspaceQueryState`) from `workspace.tsx` into dedicated feature module.
- Slice 7.2 complete: extracted upload workflow state machine seam into `upload-workflow-state.ts`.
- Slice 7.3 complete: extracted detail pane render module seam into `workspace-detail-pane.tsx`.
- Slice 7.4 complete: extracted explorer/radar adapters into `workspace-list-views.tsx`.

Validation:
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm client sh -lc 'corepack enable && corepack prepare pnpm@11.0.8 --activate && pnpm typecheck'`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm client sh -lc 'corepack enable && corepack prepare pnpm@11.0.8 --activate && pnpm lint'`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm client sh -lc 'corepack enable && corepack prepare pnpm@11.0.8 --activate && pnpm build'`

### Task 8 - Normalized builder seam extraction

Goal:
- separate orchestration, quality gates, and entity upsert implementations now concentrated in `build_normalized.py`.

Unlocks:
- smaller test surfaces and safer iterative changes.

Validation gate:
- focused normalized loader/helper tests
- pipeline smoke with `just docker-pipeline-full` (or targeted equivalent)

Progress:
- Extracted quality-gate module seam to `backend/normalized/quality_gate.py` and rewired `scripts/build_normalized.py`.
- Extracted upsert engine module seam to `backend/normalized/upsert_engine.py` and rewired `scripts/build_normalized.py`.
- Preserved script-level API compatibility for existing normalized tests (re-exported expected helpers/constants from script surface).

Validation:
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync ruff check backend/normalized/quality_gate.py backend/normalized/upsert_engine.py scripts/build_normalized.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync mypy backend/normalized/quality_gate.py backend/normalized/upsert_engine.py scripts/build_normalized.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync pytest -q tests/unit/test_normalized_loader_helpers.py tests/unit/test_normalized_quality_gates.py tests/unit/test_normalized_domain_entities_tdd.py`

### Task 9 - Type strictness recovery path

Goal:
- progressively remove strict-type bypasses for critical backend modules.

Unlocks:
- tighter contract safety and earlier drift detection.

Validation gate:
- module-level MyPy/Pyright passes
- no new suppressions without documented rationale

Progress:
- Removed strict-type bypasses from `pyproject.toml` for:
  - `backend/api/routers/opportunities.py`
  - `backend/api/routers/operations.py`
  - `backend/ingestion/manual_uploads.py`
  - `scripts/ingest_raw.py`
- Kept bypasses for:
  - `backend/api/routers/manual_uploads.py`
  - `scripts/build_normalized.py`
  because strict-type debt remains high and was left explicit instead of adding suppressions.

Validation:
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync mypy backend/api/routers/opportunities.py backend/api/routers/operations.py backend/ingestion/manual_uploads.py scripts/ingest_raw.py`
- `rtk docker compose --env-file .env.docker -f docker-compose.yml run --rm --build backend-tools uv run --no-sync pyright backend/api/routers/opportunities.py backend/api/routers/operations.py backend/ingestion/manual_uploads.py scripts/ingest_raw.py`

## Execution Rule

Do not start Task `N+1` until Task `N` has:

1. code merged on branch,
2. validation evidence captured,
3. no unresolved blocking defects.
