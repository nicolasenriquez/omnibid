# Pipeline Structure

## Purpose

Document the ETL pipeline module layout, stage responsibilities, run commands, and the procedure for adding new ingestion sources.

## Layout

```
backend/pipeline/
  __init__.py              # Pipeline module boundary

  extract/                 # Extraction stage — API clients, file contracts, data entry points
    __init__.py

  transform/               # Transformation stage — normalization builders, upsert engine, quality gates
    __init__.py

  load/                    # Load stage — persistence, queue management, checkpoint logic
    __init__.py

  orchestration/           # Orchestration — daily pipeline, sync, worker entrypoints
    __init__.py
    daily_pipeline.py      # Orchestration entrypoints (raw ingest, normalized build, MP API daily)
    sync.py                # Mercado Publico API sync logic
    worker.py              # Ingestion queue worker

  shared/                  # Shared utilities — cleaning, validation, common helpers
    __init__.py
    cleaning.py            # Text normalization, UTM cleaning, eligibility rules
    validation.py          # Stage-boundary contract validators (fail-fast guards)
```

Supporting directories:
```
config/
  pipeline.yaml            # Centralized operational config (batch sizes, rate limits, retry policy)

scripts/
  fetch_mp_api.py          # MP API sync CLI (active-discovery, rolling-window, detail-by-codigo)
  run_mp_api_daily_pipeline.py  # Daily pipeline: rolling sync → detail enrichment → canonicalization → silver
  ingest_raw.py            # Raw ingest (CSV/file sources)
  build_normalized.py      # Normalized build (licitaciones, ordenes_compra)
  run_ingestion_jobs.py    # Ingestion queue worker runner
```

## Backward-Compatible Shims

The pipeline hardening migration (`openspec/changes/mp-api-pipeline-hardening/`) moved canonical code into `backend/pipeline/`. Two legacy directories persist as backward-compatible re-export shims until all callers are migrated:

- `backend/normalized/transform.py` — re-exports symbols from `backend/pipeline/transform/` modules. Actively imported by `backend/pipeline/transform/mp_api_read_model_bridge.py`.
- `backend/normalized/transform_annotations.py` — re-exports from `backend/nlp/`.
- `backend/ingestion/manual_uploads.py` — original implementation; actively imported by `backend/api/routers/manual_uploads.py`.

When documenting, always reference the canonical `backend/pipeline/` locations. Do not write new imports against the legacy paths.

## Stage Responsibilities

### Extract

Entry point for all external data into the pipeline. Current module boundary established; implementation modules (MP API client, MP API schemas, MP API config, CSV file contracts) will be migrated here in the ETL migration phase.

- **Input**: External API endpoints, CSV files, manual uploads
- **Output**: Parsed domain objects (e.g., `LicitacionNotice`, CSV row mappings)
- **Contracts**: API response schemas (`backend/pipeline/extract/mp_api_schemas.py`), file column requirements (`backend/pipeline/extract/file_contracts.py`)

### Transform

Converts extracted raw records into canonical normalized entities. Applies business rules, text cleaning, type coercion, and field-level anti-degradation semantics.

- **Input**: Parsed records, snapshot rows
- **Output**: Canonicalized dict payloads ready for upsert
- **Contracts**: Normalized table schemas, conflict field sets, upsert engine coalesce semantics

### Load

Persists canonicalized rows into target tables with idempotent upsert semantics. Manages ingestion queues, checkpoints, and request/payload lineage tracking.

- **Input**: Canonicalized dict payloads
- **Output**: Upserted rows in normalized/silver tables, queue state transitions
- **Contracts**: Business key conflict sets, ingestion unit lineage metadata

### Shared

Cross-cutting utilities used by all stages. No stage-specific logic belongs here.

- `cleaning.py`: `normalize_text_base`, `normalize_tipo_adquisicion`, `is_licitacion_elegible`
- `validation.py`: `validate_notice_before_persistence`, `validate_canonicalized_row_before_upsert`, `validate_no_duplicate_business_keys`

## Run Commands

All commands assume Docker runtime as the canonical path per `AGENTS.md`. Host-local fallback commands are documented where the container path is unavailable.

### Docker (canonical)

```
just compose-up                  # Start database + backend containers
just mp-api-smoke                # Smoke-check MP API config (dry-run)
just mp-api-sync-active          # Run active-discovery sync
just mp-api-sync-rolling         # Run rolling-window sync
just mp-api-sync-detail          # Run detail-by-codigo sync
just mp-api-daily-refresh        # Full daily pipeline: rolling → detail → canonicalization → silver
just docker-pipeline-full        # Full pipeline: raw ingest → normalized build
just docker-smoke                # Health-check containers
just ingestion-worker            # Run ingestion queue worker
```

### Host-local (fallback)

```
uv run python scripts/fetch_mp_api.py --mode rolling-window --dry-run
uv run python scripts/fetch_mp_api.py --mode active-discovery
uv run python scripts/fetch_mp_api.py --mode detail-by-codigo --codigos 1274285-76-LR25
uv run python scripts/run_mp_api_daily_pipeline.py
uv run python scripts/ingest_raw.py --dataset licitacion --file path/to/file.csv
uv run python scripts/build_normalized.py --dataset licitacion
```

## Operational Config

`config/pipeline.yaml` centralizes pipeline parameters separate from application runtime config (`backend/core/config.py`):

| Parameter | Default | Purpose |
|---|---|---|
| `pipeline.raw_chunk_size` | 5000 | Rows per raw ingest chunk |
| `pipeline.normalized_chunk_size` | 500 | Rows per normalized upsert chunk |
| `mercado_publico_api.daily_request_limit` | 10000 | Max API requests per day |
| `mercado_publico_api.retry.max_attempts` | 3 | Retry budget + 1 |
| `mercado_publico_api.rolling_window.default_window_days` | 4 | Days to look back in rolling sync |
| `mercado_publico_api.detail_enrichment.backfill_interval_days` | 7 | Look-back days for detail enrichment candidates |

Environment-specific overrides live under `environments.*` in the same file.

## Extension Guide — Adding a New Ingestion Source

1. **Extract**: Add a client module under `extract/` (e.g., `extract/new_source_client.py`) with API call logic and response parsing. Add Pydantic schemas for the response contract. Add file contracts in `extract/file_contracts.py` if CSV/TSV ingestion is needed.

2. **Transform**: Add a read-model bridge under `transform/` (e.g., `transform/new_source_read_model_bridge.py`) that maps extracted records into normalized/silver table payloads. Define conflict fields for upsert deduplication.

3. **Load**: Add a store module under `load/` (e.g., `load/new_source_store.py`) with `persist_batch` and `reserve_budget` functions. Reuse the shared upsert engine and validation guards.

4. **Config**: Add source-specific sections to `config/pipeline.yaml` (endpoints, rate limits, retry policy). Add environment override sections for dev/test/prod.

5. **Orchestration**: Add a sync mode to `orchestration/daily_pipeline.py` and a CLI entrypoint in `scripts/`. Add just recipes in `justfile` for the Docker path.

6. **Tests**: Add unit tests for parsing (response → domain object), persistence (domain object → snapshot row), and canonicalization (snapshot → normalized payload). Use the `tests/fixtures/` directory for real payload fixtures.

7. **Docs**: Update this document with the new source's run commands and config parameters.
