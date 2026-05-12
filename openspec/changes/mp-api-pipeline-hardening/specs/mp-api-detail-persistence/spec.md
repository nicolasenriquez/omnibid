# mp-api-detail-persistence Specification

## Purpose
Define the persistence contract for enriched detail-by-codigo fields in `mercado_publico_notice_snapshot` and the new `mercado_publico_notice_item_snapshot` table.

## ADDED Requirements

### Requirement: The system MUST persist enriched notice fields from detail payloads
The system SHALL persist `description`, `buyer_unit_address`, `buyer_unit_commune`, `buyer_unit_region`, `buyer_user_rut`, `buyer_user_code`, `buyer_user_name`, `buyer_user_position`, `created_date`, `estimated_award_date`, `award_date`, `tipo`, `codigo_tipo`, `tipo_convocatoria`, `days_to_close`, `claim_count`, `funding_source`, `visibility_amount`, and `api_completeness_level` to `mercado_publico_notice_snapshot`.

#### Scenario: Detail-by-codigo sync persists enriched notice
- **WHEN** a detail-by-codigo sync runs and persists a notice batch
- **THEN** the snapshot row contains `description`, `buyer_unit_region`, `buyer_unit_commune`, `buyer_unit_address`, and extended date fields from the parsed detail payload
- **AND** `api_completeness_level` is set to `"detail"`.

#### Scenario: Summary-mode sync persists notice with completeness marked
- **WHEN** an active-discovery or rolling-window sync persists a notice batch
- **THEN** the snapshot row contains only the summary fields
- **AND** enriched fields are NULL
- **AND** `api_completeness_level` is set to `"summary"`.

### Requirement: The system MUST create a notice item snapshot table
The system SHALL create `mercado_publico_notice_item_snapshot` with columns `id`, `pipeline_run_id`, `request_id`, `payload_id`, `external_notice_code`, `item_correlative`, `codigo_producto`, `codigo_categoria`, `categoria`, `nombre_producto`, `descripcion`, `unidad_medida`, `cantidad`, `observed_at`, `synced_at`.

#### Scenario: Item snapshot table exists after migration
- **WHEN** the Alembic migration for this change is applied
- **THEN** `mercado_publico_notice_item_snapshot` is queryable with all required columns
- **AND** a unique constraint exists on `(payload_id, external_notice_code, item_correlative)`.

### Requirement: The system MUST persist items from detail payloads
The system SHALL insert or skip (on conflict) item rows into `mercado_publico_notice_item_snapshot` during `persist_notice_batch` when the notice contains `Items.Listado`.

#### Scenario: Detail payload with items persists item rows
- **WHEN** a detail-by-codigo notice has two items in `Items.Listado`
- **THEN** two rows are inserted into `mercado_publico_notice_item_snapshot`
- **AND** each row references the same `payload_id`, `request_id`, and `pipeline_run_id`
- **AND** each row carries `codigo_producto`, `nombre_producto`, `cantidad`, `descripcion`.

#### Scenario: Summary payload with no items does not create item rows
- **WHEN** a summary-mode notice has no `Items` field
- **THEN** no rows are inserted into `mercado_publico_notice_item_snapshot`
- **AND** no error is raised.

### Requirement: Raw payload preservation MUST remain unchanged
The system SHALL continue to persist the full raw JSON payload in `api_source_payload.payload_json` exactly as received, without truncation or field filtering.

#### Scenario: Detail payload is stored in full
- **WHEN** a detail-by-codigo response is persisted
- **THEN** `api_source_payload.payload_json` contains the complete raw JSON including all nested objects
- **AND** `schema_observed_keys` includes all top-level keys from the response.
