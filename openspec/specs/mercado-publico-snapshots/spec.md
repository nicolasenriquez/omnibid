# mercado-publico-snapshots Specification

## Purpose

Define the snapshot persistence contract for Mercado Público API notices, including enriched detail-by-codigo fields, item snapshots, and API completeness level tracking.

## Requirements

### Requirement: The system MUST persist idempotent notice snapshots

The system SHALL persist `mercado_publico_notice_snapshot` rows with idempotent upsert semantics so that the same `codigo_externo` + same `payload_sha256` does not create duplicate semantic rows. The snapshot SHALL include enriched fields (`description`, `buyer_unit_address`, `buyer_unit_commune`, `buyer_unit_region`, `buyer_user_rut`, `buyer_user_code`, `buyer_user_name`, `buyer_user_position`, `created_date`, `estimated_award_date`, `award_date`, `tipo`, `codigo_tipo`, `tipo_convocatoria`, `days_to_close`, `claim_count`, `funding_source`, `visibility_amount`, `api_completeness_level`) populated when available from the source payload.

#### Scenario: The same notice payload is ingested twice

- **WHEN** a Mercado Publico sync ingests a notice with the same `codigo_externo` and the same payload hash as an already-persisted snapshot
- **THEN** the system does not create a duplicate row
- **AND** the existing snapshot row is preserved.

#### Scenario: A notice payload changes

- **WHEN** a Mercado Publico sync ingests a notice with the same `codigo_externo` but a different payload hash than the existing snapshot
- **THEN** the system creates a new snapshot row
- **AND** the previous snapshot row is retained for lineage.

#### Scenario: Detail payload persists enriched fields

- **WHEN** a detail-by-codigo sync persists a notice
- **THEN** the snapshot row includes `description`, `buyer_unit_region`, `buyer_unit_commune`, `buyer_unit_address`, `buyer_user_position`, `tipo`, `days_to_close`, and `api_completeness_level = "detail"`.

### Requirement: Snapshots MUST carry lineage metadata

The system SHALL store `pipeline_run_id`, `source_mode`, `observed_at`, and `payload_sha256` on every snapshot row so that the ingestion lineage is traceable from snapshot back to run.

#### Scenario: An operator traces a snapshot to its source run

- **WHEN** the operator queries a `mercado_publico_notice_snapshot` row
- **THEN** the row includes a `pipeline_run_id` that links to the originating `pipeline_runs` record
- **AND** the `observed_at` timestamp records when the snapshot was captured.

### Requirement: Raw payloads and queryable snapshots MUST remain separate

The system SHALL keep the raw JSON payload archive (`api_source_payload`) and the queryable notice snapshot (`mercado_publico_notice_snapshot`) as separate tables with a shared `pipeline_run_id` reference.

#### Scenario: A raw payload is stored

- **WHEN** the system persists a raw API response
- **THEN** it is stored in `api_source_payload` exactly once per unique response hash
- **AND** the corresponding notice snapshot is stored in `mercado_publico_notice_snapshot`
- **AND** both carry the same `pipeline_run_id`.

### Requirement: The system MUST persist item snapshots from detail payloads

The system SHALL persist rows in `mercado_publico_notice_item_snapshot` for each item in a detail-by-codigo notice's `Items.Listado`, with lineage back to `payload_id`, `request_id`, and `pipeline_run_id`.

#### Scenario: Detail payload items are persisted

- **WHEN** a detail-by-codigo notice contains two items
- **THEN** two rows are inserted into `mercado_publico_notice_item_snapshot`
- **AND** each row includes `product_code`, `product_name`, `quantity`, and `item_description`.

### Requirement: The system MUST track API completeness level per snapshot

The system SHALL set `api_completeness_level` to `"detail"` for snapshots from detail-by-codigo mode and `"summary"` for snapshots from active-discovery or rolling-window modes.

#### Scenario: Completeness level distinguishes summary from detail

- **WHEN** an operator queries snapshots for a notice code
- **THEN** `api_completeness_level` indicates whether the snapshot came from a summary source or a detail source.
