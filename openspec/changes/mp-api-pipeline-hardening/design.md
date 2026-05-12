## Context

The Mercado Publico API returns two schema shapes from the same `/licitaciones.json` endpoint:

| Mode | Params | Schema |
|---|---|---|
| Active discovery | `estado=activas` | Summary (~11 flat fields) |
| Rolling window | `fecha=DDMMAAAA` | Summary (~11 flat fields) |
| Detail by codigo | `codigo=<CodigoExterno>` | Full (nested Comprador, Fechas, Items, Descripcion) |

The current `LicitacionNotice` Pydantic model (`schemas.py:38-59`) captures only the summary fields and uses `extra="ignore"`. All enriched fields from detail-by-codigo are silently discarded at parse time. The raw JSON payload is preserved in `api_source_payload.payload_json` (JSONB), but the snapshot table `mercado_publico_notice_snapshot` and downstream normalized/silver layers never receive description, buyer region/commune/address, extended dates, items, or completeness metadata.

The existing sync pipeline (`sync.py`) already routes through three modes (`active-discovery`, `rolling-window`, `detail-by-codigo`) and passes raw payloads through `_with_raw` methods. The architecture boundary is well-defined: client → schemas → store → snapshot → normalized/silver.

## Goals / Non-Goals

**Goals:**
- Parse the full detail-by-codigo payload with nested Pydantic models for `Comprador`, `Fechas`, `Items`, and `Adjudicacion`
- Persist enriched fields (description, buyer region/commune/address, extended dates, items, tipo, funding source) to `mercado_publico_notice_snapshot` and a new `mercado_publico_notice_item_snapshot` table
- Support fallback between nested and flat buyer fields for summary-mode payloads
- Flow enriched API data into `normalized_licitaciones` and `normalized_licitacion_items` with anti-degradation semantics
- Add per-run coverage metrics to sync summaries
- Preserve all existing behavior: active-discovery, rolling-window, detail-by-codigo sync commands, idempotent upsert, request/payload lineage
- Formalize pipeline module structure with clear extract/transform/load boundaries under `backend/pipeline/`
- Create centralized pipeline operational config at `config/pipeline.yaml`
- Migrate MP API pipeline modules into ETL stages with test-backed gradual migration
- Consolidate shared utilities and orchestration logic

**Non-Goals:**
- New API endpoints (compradores, proveedores, etc.)
- Frontend or UI changes
- Schema-aware replay from raw payload (payload replay already works)
- Cross-source reconciliation with CSV paths
- Predictive or scoring fields
- Moving non-pipeline application modules (`backend/api/`, `backend/core/`, `backend/db/`, `backend/models/`, `backend/nlp/`)

## Decisions

### 1. Nested Pydantic models with fallback properties

**Why**: The API delivers `Comprador` as a sub-object in detail mode but flat fields in summary mode. Nested models (`CompradorPayload`, `FechasPayload`, `ItemsPayload`) capture the detail structure, while `@property` fallbacks on `LicitacionNotice` provide the flat-field compatibility path for summary-mode payloads.

**Alternatives considered**:
- *Union type (`CompradorPayload | dict | None`)*: Rejected. Pydantic unions with `extra="ignore"` are fragile and produce confusing parse errors.
- *Single flat model with optional nested fields*: Rejected. Loses the structural clarity of the API contract and makes it harder to distinguish summary vs detail.

### 2. Extend existing snapshot table + new item table

**Why**: Adding columns to `mercado_publico_notice_snapshot` is additive and backward-compatible. Items are a 1:N relationship so a separate table is required for normalized grain. This avoids the need for a parallel ingestion stack.

**Alternatives considered**:
- *Separate detail snapshot table*: Rejected. Creates table proliferation and requires merging logic in canonicalization.
- *JSONB column for all extra fields*: Rejected. Violates queryability and normalized storage policy.

### 3. Anti-degradation via field-level coalesce in canonicalization

**Why**: A summary-mode snapshot should never overwrite a detail-mode snapshot's non-null values with NULL. The canonicalization layer must prefer detail values and only fill gaps from lower-priority sources.

**Alternatives considered**:
- *Complete-only upsert (discard rows without detail)*: Rejected. Would lose summary data entirely.
- *Timestamp-based last-write-wins*: Rejected. A newer summary payload could overwrite an older detail payload.

### 4. Source priority: detail > rolling-window > active-discovery

**Why**: Detail-by-codigo is the canonical enriched payload. Rolling-window is more recent and may contain state changes. Active-discovery is broadest but least rich. This priority ensures the best data wins.

### 5. ETL stage separation under `backend/pipeline/`

**Why**: The current `backend/` structure intermixes extraction (integrations/), transformation (normalized/), and load (store.py inside integrations/). Separating into `extract/`, `transform/`, and `load/` under `backend/pipeline/` makes each stage independently testable and replaceable. The reference data engineering structure recommends this pattern to prevent copy-pasting helpers across scripts.

**Alternatives considered**:
- *Keep current flat structure*: Rejected. As the pipeline grows (more API sources, more transforms), the flat structure becomes harder to navigate and test.
- *Root-level `etl/` directory*: Rejected. Keeps everything under `backend/` to maintain the existing monorepo architecture boundaries and avoid disrupting `backend/api/`, `backend/core/`, `backend/db/` which are application infrastructure, not pipeline code.

### 6. Centralized pipeline config at `config/pipeline.yaml`

**Why**: The reference structure places `config/` at project root. The repo already has `config/` at root (with `config/nlp/`). Pipeline operational parameters (batch sizes, retry policies, window days, rate limits) are distinct from application runtime config (`backend/core/config.py`). Centralizing them in `config/pipeline.yaml` gives operators one file to change without reading application code.

**Alternatives considered**:
- *Extend `backend/core/config.py`*: Rejected. Mixes application settings (FastAPI, DB URLs) with pipeline operational parameters. Operators shouldn't need to read application code to change a batch size.
- *Put under `backend/pipeline/config/`*: Rejected. The repo already has `config/` at root; extending the existing pattern is clearer.

### 7. Gradual migration with test-backed safety

**Why**: The migration moves working, tested code from existing locations to new ETL stages. The API parsing work (Sections 1-6) must complete first so the modules being migrated are in their final enriched state. Each stage migration (extract → transform → load) is atomic: move files, update imports, run `just test-unit`, then proceed. Old directories are removed only after all imports are verified.

**Alternatives considered**:
- *Big-bang migration*: Rejected. Moving all modules at once makes import breakage hard to isolate and debug.
- *New parallel structure then delete old*: Rejected. Creates confusion about which path is canonical during the transition.

### 8. Unified pipeline for all data entry points

**Why**: The repo has three data entry points — massive file load, CSV manual load, and MP API — all feeding the same raw→normalized→silver pipeline. Rather than leaving CSV/manual load paths in a separate `backend/ingestion/` location, they are migrated alongside the MP API modules into `backend/pipeline/` so all entry points share the same extract/transform/load structure. `backend/integrations/` is preserved for non-pipeline integrations only.

**Alternatives considered**:
- *Keep CSV paths separate*: Rejected. CSV and API are both data entry points into the same normalization pipeline. Keeping them in separate directories creates fragmentation and makes the pipeline harder to understand.

## Risks / Trade-offs

- **Migration on populated tables**: Adding nullable columns to `mercado_publico_notice_snapshot` is safe (no rewrite). The new item table is empty initially. → Low risk.
- **Schema evolution**: If the API adds new fields in future, `extra="ignore"` still prevents breakage, but new fields must be explicitly added to capture them. → Acceptable trade-off for fail-fast parsing.
- **Memory from large item lists**: Detail payloads can have many items. Pydantic parsing and per-item persistence adds overhead proportional to item count. → Mitigated by existing per-codigo rate limiting in `detail-by-codigo` mode.
- **Fallback field ambiguity**: When both nested and flat fields are present (e.g., a summary payload incorrectly includes a partial `Comprador` object), the fallback logic may pick the wrong source. → Unlikely in practice; the API is consistent about schema per mode.
- **Import breakage during ETL migration**: Moving modules to new paths can break imports in `scripts/`, tests, and application code. → Mitigated by stage-at-a-time migration with `just test-unit` after each stage. Old directories are not removed until all imports are verified.
- **Dual module paths during transition**: During migration, some code may reference old paths while new code uses new paths. → Mitigated by completing each stage migration fully before starting the next. No dual paths within a single stage.

## Migration Plan

### Database Migration
1. Create Alembic migration adding nullable enriched columns to `mercado_publico_notice_snapshot`
2. Create Alembic migration for `mercado_publico_notice_item_snapshot` table
3. Deploy schema changes (backward-compatible — new columns are nullable)
4. Deploy code changes (Pydantic models, persistence, canonicalization)
5. Existing sync commands continue working unchanged; new detail-by-codigo runs populate enriched fields
6. Rollback: drop new columns/table, revert code — no data loss in existing columns

### Pipeline Structure Migration (after Sections 1-6 complete)
7. Create new ETL module boundaries under `backend/pipeline/` alongside existing code
8. Create `config/pipeline.yaml` with centralized pipeline config
9. Migrate extract stage: MP API client, schemas, CSV file contracts → `backend/pipeline/extract/`
10. Migrate transform stage: normalized builders, upsert engine, quality gates → `backend/pipeline/transform/`
11. Migrate load stage: store, queue, checkpoints → `backend/pipeline/load/`
12. Consolidate orchestration: application.py, worker.py → `backend/pipeline/orchestration/`
13. Remove empty legacy directories after all imports verified
14. Add `docs/pipeline/structure.md` documenting the final layout

## Open Questions

None.
