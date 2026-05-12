## 1. Audit & Fixtures

- [x] 1.1 Create a detail-by-codigo JSON fixture from the empirically confirmed payload structure (Comprador nested, Fechas nested, Items with Listado, Descripcion, etc.)
- [x] 1.2 Create a summary-mode JSON fixture from active-discovery payload structure (flat buyer fields, no nested objects)
- [x] 1.3 Write a failing test `test_parse_detail_payload_discards_description` proving `Descripcion` is lost with current `LicitacionNotice`
- [x] 1.4 Write a failing test `test_parse_detail_payload_discards_nested_buyer` proving `Comprador.RegionUnidad` and `Comprador.ComunaUnidad` are lost
- [x] 1.5 Write a failing test `test_parse_detail_payload_discards_items` proving `Items.Listado` entries are discarded
- [x] 1.6 Write `docs/architecture/mp_api_pipeline_hardening_audit.md` documenting current gaps: which fields are in raw payload but not in parsed model, not in snapshot, and not in normalized/silver

## 2. Schema Enrichment

- [x] 2.1 Add `CompradorPayload` Pydantic model with all nested buyer fields (`CodigoOrganismo`, `NombreOrganismo`, `RutUnidad`, `CodigoUnidad`, `NombreUnidad`, `DireccionUnidad`, `ComunaUnidad`, `RegionUnidad`, `RutUsuario`, `CodigoUsuario`, `NombreUsuario`, `CargoUsuario`)
- [x] 2.2 Add `FechasPayload` Pydantic model with all extended date fields (`FechaCreacion`, `FechaCierre`, `FechaInicio`, `FechaFinal`, `FechaPubRespuestas`, `FechaActoAperturaTecnica`, `FechaActoAperturaEconomica`, `FechaPublicacion`, `FechaAdjudicacion`, `FechaEstimadaAdjudicacion`)
- [x] 2.3 Add `ItemPayload` and `ItemsPayload` Pydantic models (`Correlativo`, `CodigoProducto`, `CodigoCategoria`, `Categoria`, `NombreProducto`, `Descripcion`, `UnidadMedida`, `Cantidad`)
- [x] 2.4 Add `AdjudicacionPayload` Pydantic model (`Tipo`, `Fecha`, `Numero`, `NumeroOferentes`, `UrlActa`)
- [x] 2.5 Extend `LicitacionNotice` with new fields: `description` (alias `Descripcion`), `comprador` (nested `Comprador`), `fechas` (nested `Fechas`), `items` (nested `Items`), `adjudicacion` (nested `Adjudicacion`), `tipo`, `codigo_tipo`, `tipo_convocatoria`, `dias_cierre_licitacion`, `claim_count`, `funding_source`, `visibility_amount`
- [x] 2.6 Add `@property` fallbacks on `LicitacionNotice`: `publication_date` (prefer `Fechas.FechaPublicacion` over root `FechaPublicacion`), `close_date` (prefer `Fechas.FechaCierre` over root `FechaCierre`), `buyer_org_code` / `buyer_org_name` / `buyer_unit_code` / `buyer_unit_name` (prefer nested `Comprador` over flat root fields)
- [x] 2.7 Confirm existing summary-mode parsing tests still pass
- [x] 2.8 Confirm audit tests from 1.3-1.5 now pass

## 3. Persistence Migration

- [x] 3.1 Generate Alembic migration adding nullable enriched columns to `mercado_publico_notice_snapshot`: `description`, `buyer_unit_address`, `buyer_unit_commune`, `buyer_unit_region`, `buyer_user_rut`, `buyer_user_code`, `buyer_user_name`, `buyer_user_position`, `created_date`, `estimated_award_date`, `award_date`, `tipo`, `codigo_tipo`, `tipo_convocatoria`, `days_to_close`, `claim_count`, `funding_source`, `visibility_amount`, `api_completeness_level`
- [x] 3.2 Generate Alembic migration creating `mercado_publico_notice_item_snapshot` table with all required columns and unique constraint on `(payload_id, external_notice_code, item_correlative)`
- [x] 3.3 Add `MercadoPublicoNoticeItemSnapshot` ORM model in `backend/models/api_source.py`
- [x] 3.4 Extend `MercadoPublicoNoticeSnapshot` ORM model with new enriched columns
- [x] 3.5 Update `persist_notice_batch` in `store.py` to populate enriched snapshot fields from the extended `LicitacionNotice`
- [x] 3.6 Add item persistence in `persist_notice_batch`: iterate `notice.items.listado` and upsert rows into `mercado_publico_notice_item_snapshot`
- [x] 3.7 Write test `test_persist_detail_notice_populates_enriched_fields` verifying description, buyer_region, buyer_commune, buyer_address, tipo, api_completeness_level are persisted
- [x] 3.8 Write test `test_persist_detail_notice_persists_items` verifying item rows are created
- [x] 3.9 Write test `test_persist_summary_notice_leaves_enriched_fields_null` verifying summary-mode persistence is backward-compatible

## 4. Canonicalization

- [x] 4.1 Audit existing normalized transform builders for API-to-normalized mapping coverage
- [x] 4.2 Map API snapshot enriched fields into `normalized_licitaciones` columns (description, region, commune, address, tipo, extended dates)
- [x] 4.3 Map API item snapshots into `normalized_licitacion_items`
- [x] 4.4 Implement anti-degradation logic: field-level coalesce preferring non-null existing values over NULL incoming values
- [x] 4.5 Write test `test_api_detail_canonicalizes_to_normalized_licitaciones` with full field mapping
- [x] 4.6 Write test `test_api_items_canonicalize_to_normalized_licitacion_items`
- [x] 4.7 Write test `test_nulls_do_not_overwrite_existing_non_null_values`

## 5. Coverage Metrics & Observability

- [x] 5.1 Extend `SyncSummary` dataclass with coverage fields: `notices_with_description`, `notices_missing_description`, `notices_with_buyer_region`, `notices_missing_buyer_region`, `notices_with_items`, `notices_missing_items`, `items_seen`, `items_persisted`, `detail_calls_made`, `detail_calls_failed`
- [x] 5.2 Compute coverage counts in `_summary_from_batches` from parsed notices and persisted batches
- [x] 5.3 Include coverage metrics in `mark_sync_run_completed` run stats

## 6. Final Validation

- [ ] 6.1 Run `just lint` and fix any Ruff issues
- [ ] 6.2 Run `just type` and fix any MyPy issues
- [ ] 6.3 Run `just test-unit` and ensure all existing and new tests pass
- [ ] 6.4 Run `just docker-start` then `just mp-api-smoke` to verify sync commands still function
- [ ] 6.5 Verify migration applies and rolls back cleanly with `uv run alembic upgrade head` and `uv run alembic downgrade -1`

## 7. Pipeline Structure Foundation

Notes: Create new module boundaries alongside existing code. No files are moved yet — this establishes the target structure. All existing code and tests continue working unchanged.

- [x] 7.1 Create `config/pipeline.yaml` with centralized pipeline config: DB connection references, API endpoint templates, batch sizes (`RAW_CHUNK_SIZE`, `NORMALIZED_CHUNK_SIZE`), retry policy defaults, rolling window days default, rate limit defaults, and environment overrides
- [x] 7.2 Create `backend/pipeline/extract/__init__.py` (empty module boundary for extraction stage)
- [x] 7.3 Create `backend/pipeline/transform/__init__.py` (empty module boundary for transformation stage)
- [x] 7.4 Create `backend/pipeline/load/__init__.py` (empty module boundary for load/persistence stage)
- [x] 7.5 Create `backend/pipeline/shared/__init__.py` and move `backend/shared/cleaning.py` → `backend/pipeline/shared/cleaning.py`
- [x] 7.6 Create `backend/pipeline/shared/validation.py` with input/output validators for pipeline stage boundaries (e.g., validate notice payload before persistence, validate canonicalized row before upsert)
- [x] 7.7 Add `docs/pipeline/structure.md` documenting the new layout, stage responsibilities, run command reference, and extension guide for adding new ingestion sources

## 8. Extract Stage Migration

Notes: Move MP API extraction logic and CSV file ingestion contracts into `backend/pipeline/extract/`. All data entry points (API, CSV, file load) are part of the same pipeline. `backend/integrations/` is preserved for future non-pipeline integrations only.

- [x] 8.1 Move `backend/integrations/mercado_publico/client.py` → `backend/pipeline/extract/mp_api_client.py`
- [x] 8.2 Move `backend/integrations/mercado_publico/schemas.py` → `backend/pipeline/extract/mp_api_schemas.py`
- [x] 8.3 Move `backend/integrations/mercado_publico/config.py` and `backend/integrations/mercado_publico/rate_limit.py` → `backend/pipeline/extract/`
- [x] 8.3b Move `backend/integrations/mercado_publico/errors.py` and `backend/integrations/mercado_publico/enums.py` → `backend/pipeline/extract/`
- [x] 8.4 Move file ingestion contracts from `backend/ingestion/contracts.py` → `backend/pipeline/extract/file_contracts.py`
- [x] 8.5 Update `__init__.py` re-exports in `backend/integrations/mercado_publico/` to point to new locations (backward-compatible shim for existing importers)
- [x] 8.6 Update all imports in `backend/pipeline/application.py`, `scripts/fetch_mp_api.py`, `scripts/run_mp_api_daily_pipeline.py`, and tests to use new extract module paths
- [x] 8.7 Run `just test-unit` to verify extract migration is clean

## 9. Transform Stage Migration

Notes: Move normalization and transform builders into `backend/pipeline/transform/`. Only MP API transform code is migrated.

- [ ] 9.1 Move `backend/normalized/transform_common.py` and `backend/normalized/transform_identity.py` → `backend/pipeline/transform/`
- [ ] 9.2 Move `backend/normalized/transform_normalized_payloads.py` and `backend/normalized/transform_silver_payloads.py` → `backend/pipeline/transform/`
- [ ] 9.3 Move `backend/normalized/upsert_engine.py` → `backend/pipeline/transform/upsert_engine.py`
- [ ] 9.4 Move `backend/normalized/quality_gate.py` → `backend/pipeline/transform/quality_gate.py`
- [ ] 9.5 Move `backend/normalized/mp_api_notice_refresh.py` and `backend/normalized/mp_api_read_model_bridge.py` → `backend/pipeline/transform/`
- [ ] 9.6 Update all imports in `backend/pipeline/application.py`, `backend/pipeline/extract/`, and tests to use new transform paths
- [ ] 9.7 Run `just test-unit` to verify transform migration is clean

## 10. Load Stage Migration

Notes: Move persistence and load logic into `backend/pipeline/load/`.

- [ ] 10.1 Move `backend/integrations/mercado_publico/store.py` → `backend/pipeline/load/mp_api_store.py`
- [ ] 10.2 Move `backend/ingestion/queue.py` and `backend/ingestion/checkpoints.py` → `backend/pipeline/load/`
- [ ] 10.3 Move `backend/normalized/postprocess.py` → `backend/pipeline/load/postprocess.py`
- [ ] 10.4 Update all imports in `backend/pipeline/application.py`, `backend/pipeline/worker.py`, and tests to use new load paths
- [ ] 10.5 Run `just test-unit` to verify load migration is clean

## 11. Orchestration Consolidation & Cleanup

Notes: Consolidate orchestration logic, remove empty legacy directories, and run final validation.

- [ ] 11.1 Consolidate `backend/pipeline/application.py` → `backend/pipeline/orchestration/daily_pipeline.py`
- [ ] 11.2 Consolidate `backend/pipeline/worker.py` and `backend/pipeline/ingestion_units.py` → `backend/pipeline/orchestration/worker.py`
- [ ] 11.2b Move `backend/integrations/mercado_publico/sync.py` → `backend/pipeline/orchestration/sync.py` and update all imports in `application.py`, scripts, and tests to use the new path
- [ ] 11.3 Remove empty legacy directories (`backend/ingestion/`, `backend/normalized/`, `backend/shared/`) after verifying no orphaned imports via `rg "from backend\.(ingestion|normalized|shared)" backend/ scripts/ tests/`
- [ ] 11.4 Update `scripts/fetch_mp_api.py` and `scripts/run_mp_api_daily_pipeline.py` to use new orchestration imports
- [ ] 11.5 Run `just lint && just type && just test-unit` to verify all migrations are clean
- [ ] 11.6 Run `just docker-start && just mp-api-smoke` to verify sync commands still function end-to-end
- [ ] 11.7 Verify migration applies and rolls back cleanly with `uv run alembic upgrade head && uv run alembic downgrade -1`
