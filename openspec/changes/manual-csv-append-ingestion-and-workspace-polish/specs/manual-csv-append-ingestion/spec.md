## ADDED Requirements

### Requirement: Manual CSV upload MUST require explicit dataset selection
The system SHALL require an operator to select the target dataset before preflight or processing of a manually uploaded CSV.

#### Scenario: Operator selects licitaciones
- **WHEN** an operator uploads a CSV and selects `licitacion`
- **THEN** the system validates the file against the licitacion required-column contract
- **AND** the uploaded filename does not override the selected dataset

#### Scenario: Operator uploads non-canonical licitaciones filename
- **WHEN** an operator uploads a file named like `lic_2026-4.csv` from a non-dataset folder
- **AND** selects `licitacion`
- **AND** the CSV header contains the required licitacion columns
- **THEN** preflight accepts the file shape as licitaciones
- **AND** the system stores the original filename as metadata
- **AND** the system generates its own canonical staged filename for processing

#### Scenario: Operator selects ordenes de compra
- **WHEN** an operator uploads a CSV and selects `orden_compra`
- **THEN** the system validates the file against the orden-compra required-column contract
- **AND** the uploaded filename does not override the selected dataset

#### Scenario: Operator uploads ambiguous orden-compra filename
- **WHEN** an operator uploads a file named like `2026-4.csv` from a non-dataset folder
- **AND** selects `orden_compra`
- **AND** the CSV header contains the required orden-compra columns
- **THEN** preflight accepts the file shape as ordenes de compra
- **AND** the system stores the original filename as metadata
- **AND** the system generates its own canonical staged filename for processing

#### Scenario: Operator does not select a dataset
- **WHEN** an operator attempts to preflight or process a file without selecting a dataset
- **THEN** the system rejects the request before staging or processing
- **AND** the response explains that `licitacion` or `orden_compra` must be selected

### Requirement: Manual CSV preflight MUST fail before data writes on invalid input
The system SHALL validate manual CSV uploads before writing raw, normalized, or Silver data.

#### Scenario: Uploaded file is not a CSV
- **WHEN** the uploaded file extension or content is not CSV-compatible
- **THEN** preflight fails
- **AND** no pipeline run, ingestion batch, raw row, normalized row, or Silver row is created

#### Scenario: Uploaded file exceeds max-size policy
- **WHEN** the uploaded file is larger than the configured manual upload size limit
- **THEN** preflight fails before staging or processing
- **AND** the response tells the operator the configured size limit

#### Scenario: Uploaded CSV lacks required columns
- **WHEN** the uploaded CSV is missing required columns for the selected dataset
- **THEN** preflight fails with the missing column names
- **AND** no data rows are written

#### Scenario: Uploaded CSV is valid
- **WHEN** the uploaded CSV passes preflight
- **THEN** the system returns a staged file token, original filename, canonical filename, SHA-256 hash, selected dataset, and row count
- **AND** the system does not process the file until the operator confirms processing

#### Scenario: CSV header cannot be parsed safely
- **WHEN** the uploaded CSV cannot be decoded or parsed without corrupting required header names
- **THEN** preflight fails before data writes
- **AND** the response tells the operator that the CSV encoding or delimiter must be corrected

### Requirement: Manual append processing MUST preserve lineage and idempotency
The system SHALL process a confirmed manual CSV upload through existing lineage and idempotent pipeline contracts.

#### Scenario: Valid file is processed
- **WHEN** an operator confirms processing for a valid preflight token
- **THEN** the system registers source-file lineage
- **AND** creates pipeline run, pipeline step, and ingestion batch metadata
- **AND** writes raw rows associated with the uploaded source file

#### Scenario: Same file is processed again
- **WHEN** an identical uploaded file is processed again
- **THEN** the system does not duplicate canonical normalized or Silver business entities
- **AND** result telemetry distinguishes inserted rows from skipped, duplicate, existing, or updated rows

### Requirement: Manual append MUST process only the uploaded file scope by default
The system SHALL avoid full historical reprocessing when a manual CSV upload is processed.

#### Scenario: Operator uploads one monthly licitaciones file
- **WHEN** the uploaded file belongs to a single month of licitaciones
- **THEN** raw ingestion processes only that uploaded source file
- **AND** downstream normalized/Silver processing is bounded to the selected dataset and uploaded/new raw scope
- **AND** the full historical licitaciones corpus is not replayed by default

#### Scenario: Scoped downstream processing is unsafe
- **WHEN** the system cannot prove bounded downstream processing for the uploaded scope
- **THEN** processing fails closed or remains disabled
- **AND** the response explains the missing scope guarantee instead of running a full replay silently

### Requirement: Manual upload status MUST expose actionable telemetry
The system SHALL expose job status and outcome metrics for manual upload processing.

#### Scenario: Processing succeeds
- **WHEN** a manual upload job reaches a terminal success state
- **THEN** the status response includes processed, accepted, inserted, duplicate/existing, rejected, normalized, and Silver outcome counts where available
- **AND** the UI can render those counts without inferring them from page totals

#### Scenario: Processing fails
- **WHEN** a manual upload job fails
- **THEN** the status response includes the failed step and an actionable error message
- **AND** partial writes remain auditable through pipeline and source-file metadata
