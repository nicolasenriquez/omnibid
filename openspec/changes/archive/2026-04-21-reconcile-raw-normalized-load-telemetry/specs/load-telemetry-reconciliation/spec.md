## ADDED Requirements

### Requirement: Raw ingestion metrics MUST be deterministic and auditable
Raw ingestion runs MUST publish deterministic counters derived from explicit formulas and reconciliation queries, not from database driver `rowcount` for conflict-aware inserts.

#### Scenario: Reprocessing an already loaded file
- **WHEN** a source file is ingested again with identical content and idempotent conflict handling
- **THEN** `processed_rows` MUST equal the number of CSV rows read
- **AND** `inserted_delta_rows` MUST be `0`
- **AND** duplicate/non-inserted rows MUST be reported through deterministic derived metrics

### Requirement: Normalized builder metrics MUST distinguish flow and storage outcomes
Normalized runs MUST report transform-flow outcomes and storage reconciliation outcomes as separate metrics per dataset/entity.

#### Scenario: Mixed insert/update run
- **WHEN** normalized processing includes both new business keys and existing keys that only update mutable fields
- **THEN** the run MUST report `accepted_rows` and `deduplicated_rows` from transform flow
- **AND** the run MUST report `inserted_delta_rows` from target table growth
- **AND** operator output MUST avoid labeling `inserted_delta_rows` as total upserts

### Requirement: Operational telemetry MUST use a standardized metric taxonomy
Raw and normalized operational output MUST use a shared metric naming contract so runbooks and evidence checks are consistent across stages.

#### Scenario: Operator validates pipeline evidence
- **WHEN** an operator reviews run logs and persisted run metadata
- **THEN** metric names and definitions MUST match the documented taxonomy
- **AND** each reported metric MUST have a reproducible calculation path from run inputs and database state

### Requirement: Telemetry logging MUST be resource-efficient by default
Raw and normalized pipelines MUST keep telemetry output bounded for high-volume runs by using checkpoint summaries and completion summaries as the default behavior.

#### Scenario: Large-volume execution in default mode
- **WHEN** a pipeline run processes a high-volume dataset in default runtime mode
- **THEN** telemetry logging MUST avoid row-level or per-record log emission
- **AND** progress output MUST be emitted at bounded checkpoints
- **AND** completion summaries MUST contain the canonical metric set for operator audit

#### Scenario: Debug detail requested for controlled investigation
- **WHEN** an operator explicitly enables debug verbosity for a controlled run
- **THEN** additional detail MAY be emitted
- **AND** default bounded logging behavior MUST remain unchanged when debug mode is not enabled
