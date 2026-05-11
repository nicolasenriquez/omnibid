# Mercado Publico Snapshots Specification

## ADDED Requirements

### Requirement: The system MUST persist idempotent notice snapshots
The system SHALL persist `mercado_publico_notice_snapshot` rows with idempotent upsert semantics so that the same `codigo_externo` + same `payload_sha256` does not create duplicate semantic rows.

#### Scenario: The same notice payload is ingested twice
- **WHEN** a Mercado Publico sync ingests a notice with the same `codigo_externo` and the same payload hash as an already-persisted snapshot
- **THEN** the system does not create a duplicate row
- **AND** the existing snapshot row is preserved.

#### Scenario: A notice payload changes
- **WHEN** a Mercado Publico sync ingests a notice with the same `codigo_externo` but a different payload hash than the existing snapshot
- **THEN** the system creates a new snapshot row
- **AND** the previous snapshot row is retained for lineage.

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
