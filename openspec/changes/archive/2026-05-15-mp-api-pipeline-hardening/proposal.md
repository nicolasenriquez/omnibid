## Why

Empirical testing confirms the Mercado Publico API returns two distinct schemas: `estado=activas` and `fecha=DDMMAAAA` return a summary schema with ~11 flat fields, while `codigo=<CodigoExterno>` returns a full enriched schema with nested `Comprador`, `Fechas`, `Items`, `Descripcion`, and operational metadata. The current `LicitacionNotice` Pydantic model uses `extra="ignore"` and only captures the flat summary fields, silently discarding all enriched data at parse time. The raw payload is preserved in `api_source_payload`, but the snapshot and downstream layers never receive description, buyer region/commune/address, extended dates, items, or completeness metadata.

For open/publicada notices, the contract is stage-aware: Mercado Publico API is the source of truth for pre-close intelligence, while the monthly CSV load remains the source for post-close and adjudication enrichment. The fix is not to force every field onto every open row. The fix is to propagate the MP detail fields that are actually present before close, and to keep CSV-only fields unavailable until the close/adjudication stage.

## What Changes

- Extend Pydantic schemas with nested models for `CompradorPayload`, `FechasPayload`, `ItemPayload`, `ItemsPayload`, and `AdjudicacionPayload`; add fallback properties for summary-mode flat buyer fields  
- Add enriched columns to `mercado_publico_notice_snapshot` (description, buyer region/commune/address, extended dates, tipo, funding source, etc.) via Alembic migration  
- Create `mercado_publico_notice_item_snapshot` table for per-item lineage from detail payloads  
- Update `persist_notice_batch` to populate enriched columns and item snapshots  
- Add coverage metrics to `SyncSummary` (description %, region %, items %)  
- Implement anti-degradation canonicalization: never overwrite non-null normalized/silver values with NULL from a lower-priority source  
- Add parsing, persistence, and canonicalization tests with real detail-by-codigo fixtures  
- Keep the pipeline stage-aware: MP API enriches open/publicada intelligence, monthly CSV enriches closed/adjudicated outcomes, and CSV-only fields must not leak into open rows  
- Formalize pipeline structure with clear extract/transform/load boundaries under `backend/pipeline/`  
- Create centralized pipeline config at `config/pipeline.yaml` for DB connections, API endpoints, batch sizes, and operational parameters  
- Migrate MP API pipeline modules into extract/transform/load stages with gradual, test-backed migration  
- Consolidate shared utilities and validation into `backend/pipeline/shared/`  
- Consolidate orchestration logic into `backend/pipeline/orchestration/`  
- Add `docs/pipeline/structure.md` documenting the pipeline layout, run commands, and extension guide  

## Capabilities

### New Capabilities
- `mp-api-detail-parsing`: Nested Pydantic models that capture the full detail-by-codigo payload including `Comprador` sub-object, `Fechas` sub-object, `Items` list, and field fallbacks for summary-mode flat representations  
- `mp-api-detail-persistence`: Extended snapshot columns on `mercado_publico_notice_snapshot` plus new `mercado_publico_notice_item_snapshot` table with per-item lineage  
- `mp-api-canonicalization`: Enriched API snapshots flow into `normalized_licitaciones` and `normalized_licitacion_items` with anti-degradation semantics that prevent NULL overwrites  
- `mp-pipeline-structure`: Formalized extract/transform/load boundaries under `backend/pipeline/`, centralized pipeline config at `config/pipeline.yaml`, consolidated shared utilities and validation, and documented pipeline structure  

### Modified Capabilities
- `mercado-publico-snapshots`: Extending the snapshot ORM model with enriched columns (description, buyer_region, buyer_commune, buyer_address, extended dates, tipo, completeness flags)  
- `mercado-publico-sync-runs`: Adding per-run coverage metrics (notices_with_description, notices_with_items, notices_with_buyer_region) to sync summaries  

## Impact

- `backend/integrations/mercado_publico/schemas.py` — new nested models, extended `LicitacionNotice`, fallback properties  
- `backend/integrations/mercado_publico/store.py` — extended `persist_notice_batch`, new item persistence  
- `backend/integrations/mercado_publico/sync.py` — extended `SyncSummary` with coverage fields  
- `backend/models/api_source.py` — extended `MercadoPublicoNoticeSnapshot`, new `MercadoPublicoNoticeItemSnapshot`  
- Alembic migration — new columns + new table  
- `backend/normalized/` transform builders — canonicalization mapping  
- `config/pipeline.yaml` — new centralized pipeline operational config  
- `backend/pipeline/extract/`, `backend/pipeline/transform/`, `backend/pipeline/load/` — new ETL module boundaries  
- `backend/pipeline/shared/` — consolidated utilities and validation  
- `backend/pipeline/orchestration/` — consolidated pipeline orchestration  
- `backend/ingestion/`, `backend/shared/`, `backend/normalized/` — migrated into `backend/pipeline/` as data entry points and processing stages under the same raw→normalized→silver pipeline  
- `docs/pipeline/structure.md` — new pipeline structure documentation  

## Required Fix Steps

1. Classify each Explorer field by stage and source ownership: MP API open/publicada, MP API detail-by-codigo, or monthly CSV post-close.
2. Keep `select_detail_enrichment_candidates(...)` focused on open/closing-soon notices that still need MP detail enrichment, without exceeding the request budget.
3. Keep `canonicalize_api_snapshots_to_normalized(...)` as the source-aware bridge for MP API snapshots, with detail > rolling-window > active-discovery precedence and anti-degradation semantics.
4. Preserve monthly CSV ingestion as the downstream source for closed/adjudicated enrichments only; do not backfill open rows with CSV-only fields.
5. Add regression tests for one summary-only open notice, one MP detail-enriched open notice, and one CSV-backed closed/adjudicated notice.
6. Re-run the May 12 refresh and confirm the Explorer only shows non-null values for fields that the current stage/source can actually provide.
