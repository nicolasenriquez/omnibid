## ADDED Requirements

### Requirement: ETL failure paths MUST rollback before failure-state persistence
Raw and normalized pipeline scripts MUST call transaction rollback before persisting failed run/step/batch states when a SQL operation fails and the same session is reused.

#### Scenario: Raw ingest SQL failure in an active session
- **WHEN** raw ingest raises an exception after a SQL operation and before completion
- **THEN** the script MUST execute rollback before writing failed operational statuses

#### Scenario: Normalized build SQL failure in an active session
- **WHEN** normalized build raises an exception during dataset processing
- **THEN** the script MUST execute rollback before persisting failed dataset/run state

### Requirement: Operational and raw ORM metadata MUST match migrated index contracts
Operational and raw models MUST declare index/constraint metadata that matches migrated schema contracts so schema intent is explicit in code and migration drift is minimized.

#### Scenario: Parity check against migration-defined indexes
- **WHEN** the repository validates schema metadata for operational/raw tables
- **THEN** model metadata MUST include the migrated index contracts required for those tables

#### Scenario: Parity-safe migration review
- **WHEN** migration sanity checks are executed after parity updates
- **THEN** no unintended schema churn MUST be introduced by parity alignment changes

### Requirement: Normalized quality issues MUST be persisted and threshold-gated
Normalized processing MUST persist quality issues in `data_quality_issues` with issue type, severity, and context; run outcome MUST follow deterministic threshold rules.

#### Scenario: Default policy v1 failure conditions
- **WHEN** normalized quality gate evaluation runs with default policy
- **THEN** the run MUST fail if any critical `severity=error` issue exists
- **AND** the run MUST fail if dataset `error_rate` is greater than `0.5%`

#### Scenario: Policy metadata persistence
- **WHEN** a normalized run completes quality gate evaluation
- **THEN** run metadata MUST persist `policy_version`, threshold values, and `decision_reason`

#### Scenario: Threshold breach causes deterministic failure
- **WHEN** persisted issue counts exceed configured failure thresholds for a run
- **THEN** the run MUST be marked as failed with explicit quality-gate reason

#### Scenario: Warning-level issues below failure threshold
- **WHEN** quality issues are present but below failure thresholds
- **THEN** the run MUST complete with warnings and persisted issue evidence

### Requirement: Operations API MUST enforce bounded list limits and scalable summary behavior
Operations list endpoints MUST validate `limit` with bounded ranges, and dataset summary behavior MUST avoid unbounded expensive usage patterns for large tables.

#### Scenario: Out-of-range list limit request
- **WHEN** a client requests `/runs` or `/files` with an out-of-range limit
- **THEN** the API MUST reject the request with validation error

#### Scenario: Large-table summary operation policy
- **WHEN** operators use dataset summary in high-volume environments
- **THEN** the implementation MUST follow a documented scalable summary strategy rather than relying on unbounded frequent full-table counting

#### Scenario: Precomputed summary storage deferred in this change
- **WHEN** this capability is implemented
- **THEN** it MUST NOT require introducing a new precomputed summary persistence table in this change
- **AND** precomputed summary storage MUST be handled in a follow-up proposal
