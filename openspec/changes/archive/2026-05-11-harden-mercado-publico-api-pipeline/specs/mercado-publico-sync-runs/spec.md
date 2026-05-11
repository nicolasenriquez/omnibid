# Mercado Publico Sync Runs Specification

## ADDED Requirements

### Requirement: Every sync execution MUST produce a durable run record
The system SHALL create a `pipeline_runs` record at the start of each Mercado Publico sync execution and SHALL update it with a final status (`succeeded`, `failed`, or `partial`) before the process exits.

#### Scenario: A sync completes successfully
- **WHEN** a Mercado Publico sync finishes without errors
- **THEN** the `pipeline_runs` record is updated with status `succeeded`, `finished_at` timestamp, and aggregate `run_stats_json`
- **AND** the record is durable in the database regardless of subsequent process termination.

#### Scenario: A sync fails during execution
- **WHEN** a Mercado Publico sync encounters an unrecoverable error
- **THEN** the `pipeline_runs` record is updated with status `failed`, an `error_message`, and `finished_at`
- **AND** partial work completed before the failure is preserved.

### Requirement: Run records MUST include operator provenance
The system SHALL store `provider`, `run_mode`, `requested_by`, and `run_parameters_json` on every `pipeline_runs` row so that each execution is traceable to a specific operator, mode, and parameter set.

#### Scenario: An operator triggers a manual sync
- **WHEN** the operator runs `scripts/fetch_mp_api.py` with `--requested-by operator_name --mode rolling-window`
- **THEN** the resulting `pipeline_runs` record includes `requested_by = operator_name`, `run_mode = rolling-window`, and the window parameters in `run_parameters_json`.

### Requirement: Concurrent runs MUST NOT share the same run record
The system SHALL create a distinct `pipeline_runs` row per execution so that each sync cycle has its own lifecycle and stats.

#### Scenario: Two syncs are started by different operators
- **WHEN** operator A and operator B each start a Mercado Publico sync
- **THEN** each sync produces its own `pipeline_runs` row with distinct `requested_by` values
- **AND** their stats and statuses are independently tracked.
