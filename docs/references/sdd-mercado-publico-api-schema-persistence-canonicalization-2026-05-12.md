# SDD Reference — MP API Schema Enrichment, Persistence & Canonicalization (2026-05-12)

Change: `mp-api-pipeline-hardening` (Sections 1–5)

## Official Sources Consulted

- Pydantic V2 model configuration, field aliases, validators, model validators:
  https://docs.pydantic.dev/latest/concepts/models/
  https://docs.pydantic.dev/latest/concepts/fields/#field-aliases
  https://docs.pydantic.dev/latest/concepts/validators/
- SQLAlchemy ORM 2.x column types, constraints, server defaults, indexes:
  https://docs.sqlalchemy.org/en/20/core/type_basics.html
  https://docs.sqlalchemy.org/en/20/core/constraints.html
- SQLAlchemy PostgreSQL dialect `INSERT ... ON CONFLICT DO UPDATE`:
  https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
- PostgreSQL string functions (`coalesce`, `nullif`, `btrim`):
  https://www.postgresql.org/docs/16/functions-conditional.html
  https://www.postgresql.org/docs/16/functions-string.html
- Alembic operations API (add_column, create_table, alter_column):
  https://alembic.sqlalchemy.org/en/latest/ops.html
- Existing repo standards:
  `AGENTS.md`, `docs/references/sdd-standard.md`

## Source-to-Decision Trace

### 1. Nested Pydantic models with fallback validators for dual-schema API payloads

- Decision: Use per-sub-object Pydantic models (`CompradorPayload`, `FechasPayload`, `ItemsPayload`, `AdjudicacionPayload`) with `model_config = ConfigDict(populate_by_name=True, extra="ignore")`, and a `@model_validator(mode="after")` on `LicitacionNotice` that applies nested-to-flat field fallbacks only when the nested object is present and the nested field is non-null.
- Why: The Mercado Publico API returns a flat summary schema for `estado=activas`/`fecha=DDMMAAAA` and a nested enriched schema for `codigo=<CodigoExterno>`. Pydantic `populate_by_name=True` with `Field(alias=...)` maps Spanish API keys to English Python attributes. `extra="ignore"` prevents breakage on unknown future fields. `@model_validator(mode="after")` applies fallback logic after all field-level validators have run, so both flat and nested sources are available.
- Code areas:
  - `backend/integrations/mercado_publico/schemas.py` — `LicitacionNotice._apply_nested_fallbacks`

### 2. Field-level anti-degradation via PostgreSQL `coalesce(nullif(btrim(incoming), ''), existing)`

- Decision: The existing upsert engine in `backend/normalized/upsert_engine.py` uses `_build_complete_only_update_expr` which wraps incoming values with `coalesce` against the target column. For text columns, a `nullif(btrim(incoming), '')` guard is applied so blank strings are treated as NULL. For non-text columns, `coalesce(incoming, existing)` is used directly.
- Why: This guarantees that a lower-priority source (e.g., summary-mode data) never overwrites a higher-priority source's non-null values with NULL. PostgreSQL `coalesce` returns the first non-null argument, meaning NULL incoming values leave existing values intact. The `nullif`/`btrim` pattern for text columns prevents whitespace-only strings from counting as valid values.
- Code areas:
  - `backend/normalized/upsert_engine.py` — `_build_complete_only_update_expr`
  - `backend/normalized/mp_api_read_model_bridge.py` — `canonicalize_api_snapshots_to_normalized`

### 3. Alembic migrations with additive nullable columns and new tables with UUID PK server defaults

- Decision: Add enriched columns to `mercado_publico_notice_snapshot` as nullable (no backfill required). Create `mercado_publico_notice_item_snapshot` with `server_default=sa.text("gen_random_uuid()")` on the UUID PK column, `sa.ForeignKey` references to `pipeline_runs`, `api_source_request`, and `api_source_payload`, and a `sa.UniqueConstraint` on `(payload_id, external_notice_code, item_correlative)`.
- Why: Additive nullable columns are backward-compatible and require no data migration. PostgreSQL `gen_random_uuid()` generates type-4 UUIDs as a server-side default, which avoids application-level UUID generation coupling. The unique constraint guarantees idempotent item persistence — duplicate items within the same payload are not re-inserted.
- Code areas:
  - `alembic/versions/2026051200_enriched_notice_snapshot_columns.py`
  - `alembic/versions/2026051201_notice_item_snapshot_table.py`
  - `backend/models/api_source.py` — `MercadoPublicoNoticeItemSnapshot`

### 4. Canonicalization source priority via deduplication by `external_notice_code`

- Decision: In `canonicalize_api_snapshots_to_normalized`, snapshots are fetched ordered by `synced_at DESC`, and only the latest snapshot per `external_notice_code` is used for canonicalization. This implements the `detail-by-codigo > rolling-window > active-discovery` priority implicitly because detail snapshots always have a later `synced_at` when ingested within the same pipeline run.
- Why: The pipeline runs detail-by-codigo immediately after rolling-window in the same pipeline run. The `ORDER BY synced_at DESC` + `latest_by_code` dedup naturally selects the detail snapshot when both exist. This avoids complex priority-tagging logic.
- Code areas:
  - `backend/normalized/mp_api_read_model_bridge.py` — `canonicalize_api_snapshots_to_normalized`

## Validation Linkage

- Unit tests: `uv run pytest tests/unit/ -v` (301 tests, all passing)
- Targeted contract checks:
  - `uv run pytest tests/unit/test_mercado_publico_schemas.py -v` (7 tests)
  - `uv run pytest tests/unit/test_mercado_publico_store.py -v` (9 tests)
  - `uv run pytest tests/unit/test_mercado_publico_sync.py -v` (11 tests)
  - `uv run pytest tests/unit/test_mp_api_read_model_bridge.py -v` (6 tests)
- Migration parity: `uv run pytest tests/unit/ -k "schema_parity"` (operational + domain + silver)
