# Local Development Runbook

## Bootstrap

0. Install `uv` locally
1. `cp .env.example .env`
2. Set `DATABASE_URL`, `TEST_DATABASE_URL`, and `DATASET_ROOT` in `.env`
3. `just setup`
4. `just db-bootstrap`

## TDD Daily Loop

1. Write a failing test in `tests/unit/`
2. Run unit tests: `just test-unit`
3. Implement the minimal fix
4. Run `just quality`

### Offline fallback for unit tests

If `uv run` tries to resolve dependencies and fails due network/DNS constraints, run local venv tests directly:

```bash
./.venv/bin/pytest -q -m "not integration"
```

## Raw Pipeline Loop

Canonical step:

- `just pipeline-raw`

Equivalent low-level sequence:

1. Profile source files: `just raw-profile`
2. Ingest raw files: `just raw-ingest`
3. Inspect API endpoints:
   - `GET /health`
   - `GET /runs?limit=50` (bounded to `1..200`)
   - `GET /files?limit=100` (bounded to `1..200`)
   - `GET /datasets/summary` (default `mode=cached`, reads latest persisted snapshot)
   - `GET /datasets/summary?mode=fresh` (explicit recount that persists a new snapshot)

## Persisted Summary Validation Loop

1. Seed or refresh summary snapshot:
   - `uv run python -c "from backend.api.routers.operations import datasets_summary; from backend.db.session import SessionLocal; s=SessionLocal(); print(datasets_summary(mode='fresh', max_age_seconds=300, db=s)['summary_meta']); s.close()"`
2. Validate default read path returns persisted metadata:
   - `summary_meta.strategy == persisted_success_snapshot`
   - `summary_meta.precomputed_summary_storage == enabled`
   - `summary_meta.refresh_status == not_requested` when using `mode=cached`
3. Validate failure fallback behavior (unit-test backed):
   - `uv run pytest -q tests/unit/test_operations_summary_snapshots.py`
   - confirm `test_fresh_mode_failure_falls_back_to_last_successful_snapshot` passes.

## Normalized Pipeline Loop (Hardened)

Run a controlled sample first before full historical load:

```bash
UV_NO_SYNC=1 \
NORMALIZED_DATASET=all \
NORMALIZED_LIMIT_ROWS=2000 \
NORMALIZED_FETCH_SIZE=500 \
NORMALIZED_CHUNK_SIZE=200 \
just pipeline-normalized
```

Expected operational output includes:

- progress lines per dataset:
  - `[normalized] licitaciones progress: ...`
  - `[normalized] ordenes_compra progress: ...`
- summary lines with rejection/upsert metrics:
  - licitaciones summary includes `header/items/ofertas/suppliers{accepted,deduplicated,inserted_delta,existing_or_updated,rejected}`
  - ordenes_compra summary includes `header/items/buyers/suppliers/categories{accepted,deduplicated,inserted_delta,existing_or_updated,rejected}`

For full load, remove `NORMALIZED_LIMIT_ROWS` or set it to `0`.

## Domain Entity Validation Loop

1. Run bounded normalized replay twice:

```bash
uv run python scripts/build_normalized.py \
  --dataset all \
  --fetch-size 500 \
  --chunk-size 200 \
  --limit-rows 2000 \
  --state-path data/runtime/normalized_domain_validation_state.json \
  --reset-state \
  --no-resume \
  --no-incremental

uv run python scripts/build_normalized.py \
  --dataset all \
  --fetch-size 500 \
  --chunk-size 200 \
  --limit-rows 2000 \
  --state-path data/runtime/normalized_domain_validation_state.json \
  --no-resume \
  --no-incremental
```

2. Validate idempotency:
   - second run reports `inserted_delta=0` for `buyers`, `suppliers`, and `categories`.
3. Validate domain identity issue persistence:
   - query `data_quality_issues` for `issue_type=normalized_missing_domain_identity`.
   - confirm `record_ref` and `column_name` identify the affected domain contract.

## Canonical Sequential Commands

Use these names as the default operating convention:

1. `just pipeline-raw`
2. `just pipeline-normalized`
3. (future) `just pipeline-gold`

End-to-end shortcuts:

- `just pipeline-full`
- `just pipeline-full-fast` (skips profiling in Raw)

## Stage-Gated Continuation Policy

Do not advance to Gold until previous stages are verifiably stable:

1. Bronze/Raw ingestion foundation completed (contracts, lineage, idempotent replay).
2. Bronze/Raw reliability hardening completed (trusted load telemetry, rejection accountability).
3. Silver/Normalized core canonicalization completed (deterministic rebuild + stable keys).
4. Silver/Normalized domain expansion completed (buyer/supplier/category domain tables and contracts).
5. Gold implementation starts only after stage 1-4 are accepted.
