# Incremental Ingestion Foundation Specification

## Purpose

Define the reusable ingestion job queue, durable checkpoint, and lineage substrate that source-specific handlers will build on.

## Requirements

### Requirement: The system MUST provide a reusable ingestion job queue
The system SHALL store pending ingestion work in a Postgres-backed queue rather than in an external broker.

#### Scenario: One worker claims one job
- **GIVEN** a queued ingestion job and one worker session
- **WHEN** the worker claims the next available job
- **THEN** the system SHALL lock and mark the job running atomically
- **AND** the job SHALL not be claimable by another worker at the same time.

#### Scenario: Two workers race for the same queue
- **GIVEN** two workers asking for the same queued job set
- **WHEN** both attempt to claim work concurrently
- **THEN** only one worker SHALL receive a given job
- **AND** skipped locked rows SHALL remain available for the other worker to pick next.

#### Scenario: Claim order is deterministic
- **GIVEN** multiple queued jobs with different priorities and availability windows
- **WHEN** a worker claims the next job
- **THEN** the system SHALL pick the lowest `priority`
- **AND** among equal priorities SHALL prefer the earliest eligible `available_at`
- **AND** among equal eligibility SHALL prefer the earliest `created_at`
- **AND** if still tied SHALL use a stable `id` tie-breaker.

### Requirement: The system MUST persist a durable checkpoint before queue execution
The system SHALL persist the source artifact and its metadata before a job becomes eligible for worker execution.

#### Scenario: Intake is accepted but the worker has not started yet
- **GIVEN** a source file or snapshot has been staged and registered
- **WHEN** the process stops before the worker claims the job
- **THEN** the checkpoint remains available in durable storage
- **AND** the queue row still references the same checkpoint on restart.

#### Scenario: Worker crashes after checkpoint creation
- **GIVEN** a durable checkpoint exists and the job is queued
- **WHEN** the worker crashes before finishing the job
- **THEN** the source artifact is still recoverable
- **AND** the job can be retried or reclaimed without losing the input.

#### Scenario: Terminal success allows cleanup only after consumption
- **GIVEN** the job reaches a terminal success state
- **WHEN** the retention policy permits cleanup
- **THEN** the staged bytes may be deleted
- **AND** the durable metadata remains available for audit.

### Requirement: The queue MUST keep explicit retry state
The system SHALL track attempts, retry scheduling, and terminal failure state for each job.

#### Scenario: Retry budget is exhausted
- **GIVEN** a job that has failed the configured number of times
- **WHEN** it fails again
- **THEN** the system SHALL move it to a terminal dead-letter state
- **AND** SHALL not retry it again automatically.

#### Scenario: Transient failure schedules a future retry
- **GIVEN** a running job that fails transiently before its retry budget is exhausted
- **WHEN** the worker marks the failure retryable
- **THEN** the system SHALL increment the attempt count
- **AND** SHALL move the job to `retry_scheduled`
- **AND** SHALL set a later `available_at` before the next claim can occur
- **AND** SHALL compute that `available_at` deterministically from `failure_at`, `attempts`, and configured retry delay.

#### Scenario: Non-retryable failure goes dead-letter immediately
- **GIVEN** a running job that fails with a non-retryable error
- **WHEN** the worker marks the failure terminal
- **THEN** the system SHALL move the job to `dead_letter`
- **AND** SHALL not schedule another retry.

#### Scenario: Dead letters remain quarantined until replay is explicit
- **GIVEN** a job in `dead_letter`
- **WHEN** the queue becomes empty
- **THEN** the system SHALL keep the dead-letter job terminal
- **AND** SHALL not requeue it automatically
- **AND** SHALL only allow replay through an explicit operator action or maintenance flow.

### Requirement: The system MUST persist ingestion-unit lineage
The system SHALL create an ingestion-unit ledger row for each job that begins meaningful work.

#### Scenario: A job creates lineage
- **GIVEN** a claimed ingestion job
- **WHEN** the job starts work
- **THEN** the system SHALL persist a lineage row linked to the job
- **AND** the lineage SHALL record source kind, dataset type, and job metadata.

### Requirement: The substrate MUST stay separate from source-specific handlers
The system SHALL keep the queue and lineage substrate independent from Mercado Público fetches, raw dedupe, scoped normalization, and Silver refresh logic.

#### Scenario: Base change remains small
- **WHEN** this change is implemented
- **THEN** it SHALL not add Mercado Público API fetches
- **AND** it SHALL not change the raw dedupe contract
- **AND** it SHALL not change scoped normalization or Silver refresh behavior.

### Requirement: Canonical merge policy MUST preserve existing non-empty values
The system SHALL define complete-only canonical merge semantics for API + CSV convergence so missing fields do not regress existing canonical data.

#### Scenario: Incoming source has missing value and canonical already has data
- **GIVEN** a canonical record with a non-empty value for a column
- **WHEN** a later ingestion for the same business key brings `NULL` or blank for that column
- **THEN** the canonical value SHALL remain unchanged
- **AND** the merge SHALL treat that incoming field as "no new information."

#### Scenario: Incoming source provides a new materially present value
- **GIVEN** a canonical record and a later ingestion for the same business key
- **WHEN** the incoming column value is materially present
- **THEN** the canonical column SHALL update
- **AND** the provenance metadata SHALL remain auditable.

#### Scenario: Non-empty conflicting values require explicit precedence
- **GIVEN** two non-empty conflicting values for the same canonical column
- **WHEN** the system resolves the merge
- **THEN** it SHALL apply an explicit per-column precedence rule
- **AND** it SHALL not rely on implicit source arrival order alone.

#### Scenario: Default precedence matrix is deterministic
- **GIVEN** two non-empty conflicting values with no custom override for that column
- **WHEN** the merge engine resolves the value
- **THEN** identifier columns SHALL remain immutable after first assignment
- **AND** descriptive columns SHALL prefer CSV over API
- **AND** lifecycle columns SHALL prefer API over CSV
- **AND** numeric rollups SHALL prefer the newest event timestamp, with CSV used as tie-breaker.
