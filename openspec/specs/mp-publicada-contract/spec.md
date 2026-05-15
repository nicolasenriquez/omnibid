# mp-publicada-contract Specification

## Purpose

Define the official Mercado Público state contract, source-aware Silver refresh behavior, lifecycle-aware availability semantics, and `source_view=publicadas` discovery behavior for the opportunity read model.

## Requirements

### Requirement: Use official Mercado Público licitación states

The system SHALL store and expose the official Mercado Público state code and state name.

#### Scenario: Publicada tender

- **WHEN** an API licitación with `CodigoEstado = 5` and `Estado = Publicada` is ingested
- **THEN** the read model SHALL expose `mp_estado_codigo = 5`, `mp_estado_nombre = Publicada`, and `mp_estado_canonical = publicada`.

#### Scenario: Known official states

- **WHEN** an API licitación with a known `CodigoEstado` is ingested
- **THEN** the system SHALL map 5→Publicada, 6→Cerrada, 7→Desierta, 8→Adjudicada, 18→Revocada, 19→Suspendida.

### Requirement: Parse official Mercado Público field names

The system SHALL parse the official Mercado Público field names that appear in the API payload and preserve them in the public contract without inventing alternate public terminology.

#### Scenario: Licitación surface fields are present

- **WHEN** an API payload contains licitación root data, buyer data, date data, items, or adjudication data
- **THEN** the system SHALL parse and expose those fields in the current opportunity contract when they belong to the public licitación surface.

#### Scenario: Non-contract fields appear in payload

- **WHEN** an API payload contains fields that are not part of the current opportunity contract
- **THEN** those fields SHALL remain in `payload_json`
- **AND** they SHALL be available for drift detection or future contract expansion.

#### Scenario: Detail payload contains VisibilidadMonto

- **WHEN** an API payload has `VisibilidadMonto` populated
- **THEN** the public contract SHALL expose `VisibilidadMonto` as part of the parsed opportunity data.

#### Scenario: Detail payload contains FuenteFinanciamiento

- **WHEN** an API payload has `FuenteFinanciamiento` populated
- **THEN** the public contract SHALL expose `FuenteFinanciamiento` as part of the parsed opportunity data.

#### Scenario: Detail payload contains Informada

- **WHEN** an API payload has `Informada` populated
- **THEN** the public contract SHALL expose `Informada` and the read model SHALL use it when deriving lifecycle expectations for offers.

### Requirement: Silver refresh SHALL populate fields from snapshot-enriched columns

The system SHALL NOT hardcode `None` or `False` for fields that exist in the snapshot-enriched contract.

#### Scenario: Snapshot has description

- **WHEN** a snapshot has `description` populated
- **THEN** `build_silver_notice_payload_from_snapshot` SHALL set `notice_description_raw` from the snapshot value
- **AND** `notice_description_raw` SHALL NOT be null.

#### Scenario: Snapshot has claim_count

- **WHEN** a snapshot has `claim_count` populated
- **THEN** the Silver notice SHALL have `complaint_count` populated from the snapshot value.

#### Scenario: Snapshot has created_date

- **WHEN** a snapshot has `created_date` populated
- **THEN** the Silver notice SHALL have `created_date` populated from the snapshot value.

#### Scenario: Snapshot has official tender metadata

- **WHEN** a snapshot has `codigo_tipo`, `tipo`, `tipo_convocatoria`, `visibilidad_monto`, or `fuente_financiamiento` populated
- **THEN** the Silver notice SHALL expose the corresponding official Mercado Público metadata instead of forcing default `None` or `False` values.

### Requirement: Distinguish lifecycle-pending data from missing pipeline data

The system SHALL NOT treat unavailable post-close data as ingestion failure for Estado Publicada.

#### Scenario: Publicada tender has no adjudication

- **WHEN** an API licitación with `CodigoEstado = 5` has no `Adjudicacion`
- **THEN** `award_availability` SHALL be `not_yet_public`
- **AND** it SHALL NOT be `pipeline_missing`.

#### Scenario: Publicada tender has no purchase orders

- **WHEN** an API licitación with `CodigoEstado = 5` is returned by `/opportunities`
- **THEN** purchase order fields SHALL be marked as `not_yet_public`
- **AND** the frontend SHALL NOT render them as generic `No disponible`.

#### Scenario: Publicada tender has no participants or offers

- **WHEN** an API licitación with `CodigoEstado = 5` is returned by `/opportunities`
- **THEN** `participants_availability` and `offers_availability` SHALL be `not_yet_public`.

#### Scenario: Informada tender receives offers outside the portal

- **WHEN** an API licitación has `Informada` set in the official payload
- **THEN** the system SHALL treat portal-native offers as not guaranteed and SHALL derive availability accordingly.

### Requirement: Support `source_view=publicadas` discovery

The system SHALL support filtering opportunities by `source_view=publicadas` to discover API-sourced Publicada opportunities.

#### Scenario: Filter by `source_view=publicadas`

- **WHEN** `/opportunities?source_view=publicadas` is queried
- **THEN** only tenders with `mp_estado_canonical = 'publicada'` or `data_source_kind IN ('api_publicada', 'api_detail')` SHALL be returned.

#### Scenario: `source_view=publicadas` excludes historical CSV-only tenders

- **WHEN** a historical CSV-sourced tender has `data_source_kind = null` or is not in the API source kinds
- **THEN** it SHALL NOT appear when `source_view=publicadas` is set.

### Requirement: Keep historical CSV compatibility

The system SHALL preserve existing historical CSV behavior.

#### Scenario: Historical tender exists in normalized CSV tables

- **WHEN** a tender exists in `normalized_licitaciones` from CSV ingestion
- **THEN** existing historical fields SHALL continue to be available in `/opportunities` responses.

#### Scenario: API-only Publicada tender does not exist in normalized CSV tables

- **WHEN** a tender exists only in API payloads and not in historical CSV tables
- **THEN** the tender SHALL still appear in `/opportunities` with all public API fields available.

### Requirement: derivedStage remains backward-compatible

The system SHALL preserve the `derivedStage` field in `/opportunities` responses.

#### Scenario: derivedStage is present in list and detail responses

- **WHEN** `/opportunities` or `/opportunities/{notice_id}` is queried
- **THEN** `derivedStage` SHALL be present with the same values as before (open/closing_soon/closed/awarded/revoked_or_suspended/unknown)
- **AND** consumers using `derivedStage` SHALL NOT break.

### Requirement: Expose official state and availability in the response contract

The system SHALL expose official state metadata and availability fields in the `/opportunities` response contract.

#### Scenario: List item includes official state fields

- **WHEN** `/opportunities` returns a list of tenders
- **THEN** each item SHALL include `mpEstadoCodigo`, `mpEstadoNombre`, `mpEstadoCanonical`, `dataSourceKind`, and `availabilityContext`.

#### Scenario: Detail response includes availability fields

- **WHEN** `/opportunities/{notice_id}` returns a tender detail
- **THEN** the response SHALL include `participantsAvailability`, `offersAvailability`, `awardAvailability`, `purchaseOrderAvailability`, and `descriptionAvailability`.
