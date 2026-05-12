# mp-pipeline-structure Specification

## Purpose
Define the formalized extract/transform/load module structure under `backend/pipeline/`, centralized pipeline operational config at `config/pipeline.yaml`, consolidated shared utilities, and documented pipeline layout following data engineering best practices.

## ADDED Requirements

### Requirement: The pipeline MUST have clear extract/transform/load boundaries
The system SHALL organize MP API pipeline modules under `backend/pipeline/extract/`, `backend/pipeline/transform/`, and `backend/pipeline/load/` so that each stage is independently testable and replaceable.

#### Scenario: Extract stage contains all upstream data acquisition logic
- **WHEN** a developer needs to add a new API source
- **THEN** they place the client adapter and schema models in `backend/pipeline/extract/`
- **AND** the extract module has no dependencies on transform or load stages.

#### Scenario: Transform stage contains all normalization and enrichment logic
- **WHEN** a developer needs to modify canonicalization rules
- **THEN** they edit files in `backend/pipeline/transform/`
- **AND** the transform module depends only on extract models and shared utilities.

#### Scenario: Load stage contains all persistence and upsert logic
- **WHEN** a developer needs to change how snapshots are persisted
- **THEN** they edit files in `backend/pipeline/load/`
- **AND** the load module depends on transform outputs and shared utilities.

### Requirement: Pipeline operational config MUST be centralized
The system SHALL provide a `config/pipeline.yaml` at the project root containing DB connection references, API endpoint templates, batch sizes, retry policy defaults, rolling window days, rate limit defaults, and environment overrides. Pipeline code SHALL NOT hard-code operational parameters.

#### Scenario: Operator changes rolling window days without editing code
- **WHEN** an operator sets `rolling_window_days: 7` in `config/pipeline.yaml`
- **THEN** the pipeline uses 7 days for rolling window syncs
- **AND** no Python file is modified.

#### Scenario: Config is environment-aware
- **WHEN** `APP_ENV=production` is set
- **THEN** the pipeline reads production overrides from `config/pipeline.yaml`
- **AND** development defaults are not used.

### Requirement: Shared utilities MUST be consolidated under a single module
The system SHALL consolidate data cleaning, validation, and common pipeline helpers under `backend/pipeline/shared/` to prevent copy-pasting helpers across scripts.

#### Scenario: Validation utility is reused across stages
- **WHEN** the extract stage validates an API response payload and the load stage validates a row before upsert
- **THEN** both use the same validator from `backend/pipeline/shared/validation.py`.

#### Scenario: Cleaning utility is imported from shared
- **WHEN** any pipeline stage needs to clean or normalize a text field
- **THEN** it imports the cleaning function from `backend/pipeline/shared/cleaning.py`.

### Requirement: Pipeline orchestration MUST be consolidated
The system SHALL consolidate daily pipeline orchestration, worker logic, and ingestion unit management under `backend/pipeline/orchestration/`.

#### Scenario: Daily pipeline run is orchestrated from a single module
- **WHEN** the daily MP API pipeline is triggered
- **THEN** `backend/pipeline/orchestration/daily_pipeline.py` runs extract → transform → load in dependency order
- **AND** all stage results are aggregated into a single run summary.

### Requirement: All data entry points MUST share the same pipeline structure
The system SHALL migrate CSV manual load and file ingestion contracts alongside MP API modules into `backend/pipeline/` so that all data entry points (API, CSV, file load) share the same extract/transform/load pipeline. `backend/integrations/` SHALL be preserved for non-pipeline integrations only.

#### Scenario: CSV ingestion is a pipeline entry point
- **WHEN** a CSV file is ingested via `scripts/ingest_raw.py`
- **THEN** the ingestion contracts are sourced from `backend/pipeline/extract/file_contracts.py`
- **AND** the CSV data flows through the same normalized transform and load stages as API data.

#### Scenario: Non-pipeline integration is not affected
- **WHEN** a future integration (e.g., a new external API unrelated to the procurement pipeline) is added
- **THEN** it can be placed in `backend/integrations/` without needing to conform to the pipeline ETL structure
- **AND** existing pipeline modules in `backend/pipeline/` are not affected.

### Requirement: Pipeline structure MUST be documented
The system SHALL include `docs/pipeline/structure.md` documenting the module layout, stage responsibilities, run command reference, config file reference, and a guide for extending the pipeline with new ingestion sources.

#### Scenario: New team member onboards to the pipeline
- **WHEN** a developer reads `docs/pipeline/structure.md`
- **THEN** they understand where to add a new API source, where to add transforms, and how to run the pipeline
- **AND** they do not need to ask questions about directory structure.

### Requirement: Migration MUST be gradual and test-backed
The system SHALL migrate modules stage by stage (extract → transform → load) with `just test-unit` passing after each stage. Old directories SHALL NOT be removed until all imports are verified to point to new locations.

#### Scenario: Extract stage migration completes without breaking tests
- **WHEN** the extract stage modules are moved to `backend/pipeline/extract/`
- **THEN** `just test-unit` passes
- **AND** existing sync commands continue working.

#### Scenario: Old directory is removed only after verification
- **WHEN** all modules in `backend/normalized/` have been migrated to `backend/pipeline/transform/`
- **AND** no imports reference `backend.normalized` anywhere in `backend/`, `scripts/`, or `tests/`
- **THEN** `backend/normalized/` directory is removed.
