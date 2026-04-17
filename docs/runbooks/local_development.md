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

## Bronze Pipeline Loop

Canonical step:

- `just pipeline-1-bronze`

Equivalent low-level sequence:

1. Profile source files: `just profile-files`
2. Ingest raw Bronze: `just ingest-raw`
3. Inspect API endpoints:
   - `GET /health`
   - `GET /runs`
   - `GET /files`
   - `GET /datasets/summary`

## Silver Pipeline Loop (Hardened)

Run a controlled sample first before full historical load:

```bash
UV_NO_SYNC=1 \
SILVER_DATASET=all \
SILVER_LIMIT_ROWS=2000 \
SILVER_FETCH_SIZE=500 \
SILVER_CHUNK_SIZE=200 \
just pipeline-2-silver-from-bronze
```

Expected operational output includes:

- progress lines per dataset:
  - `[silver] licitaciones progress: ...`
  - `[silver] ordenes_compra progress: ...`
- summary lines with rejection/upsert metrics:
  - `rejected(header/items/ofertas)=...` for licitaciones
  - `rejected(header/items)=...` for ordenes_compra
  - `upserted(...)` counters per entity

For full load, remove `SILVER_LIMIT_ROWS` or set it to `0`.

## Canonical Sequential Commands

Use these names as the default operating convention:

1. `just pipeline-1-bronze`
2. `just pipeline-2-silver-from-bronze`
3. (future) `just pipeline-3-gold`

End-to-end shortcuts:

- `just pipeline-all`
- `just pipeline-all-fast` (skips profiling in Bronze)
