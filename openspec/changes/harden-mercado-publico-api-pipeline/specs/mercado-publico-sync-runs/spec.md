# Mercado Publico Sync Runs Specification

## Purpose

Define the lifecycle and operator contract for Mercado Publico sync runs.

## Requirements

### Requirement: Every sync execution MUST create a tracked run
The system SHALL create a run record for each logical Mercado Publico execution and SHALL track provider, mode, requested-by, parameters, stats, and final state.

#### Scenario: A run starts normally
- **GIVEN** an operator launches `active-discovery`
- **WHEN** the job begins
- **THEN** the system SHALL create a run in `running` state
- **AND** it SHALL persist the provider and mode.

#### Scenario: A run finishes successfully
- **GIVEN** the sync completes without error
- **WHEN** the job finalizes
- **THEN** the system SHALL mark the run as `succeeded`
- **AND** it SHALL persist finish time and final stats.

#### Scenario: A run raises an exception
- **GIVEN** an exception occurs during the job
- **WHEN** the runner handles the failure
- **THEN** the system SHALL mark the run as `failed`
- **AND** it SHALL persist an error message.

### Requirement: The CLI MUST support the operational modes needed by the lane
The system SHALL support `active-discovery`, `rolling-window`, and `detail-by-codigo`, and it SHALL support `dry-run`, `max-requests`, `requested-by`, and explicit window bounds.

#### Scenario: The operator requests a dry run
- **WHEN** the CLI runs with `--dry-run`
- **THEN** the system SHALL validate config and arguments
- **AND** it SHALL not write request, payload, or snapshot rows.

#### Scenario: The operator caps a run with max requests
- **WHEN** the CLI runs with `--max-requests 500`
- **THEN** the job SHALL stop before exceeding 500 counted requests
- **AND** it SHALL finalize the run with a bounded status.

### Requirement: Requested-by metadata MUST be preserved
The system SHALL persist whether the run was launched by local CLI, manual operator action, or GitHub Actions.

#### Scenario: GitHub Actions launches the run
- **WHEN** the workflow starts the sync command
- **THEN** the run SHALL record `requested_by=github_actions`
- **AND** the logs SHALL remain secret-safe.

### Requirement: The daily API sync MAY compose with downstream Silver refresh
The system MAY keep the existing daily pipeline composition, but the API sync stage and the Silver refresh stage MUST remain separately observable.

#### Scenario: The daily runner finishes both stages
- **WHEN** the API sync succeeds and Silver refresh runs afterwards
- **THEN** the system SHALL preserve the API run lineage
- **AND** it SHALL keep the downstream Silver stage readable as a separate step.
