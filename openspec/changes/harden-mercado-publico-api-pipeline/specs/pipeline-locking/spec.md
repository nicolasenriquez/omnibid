# Pipeline Locking Specification

## Purpose

Define a lock strategy that prevents overlapping execution of the same logical Mercado Publico work unit without blocking the whole system.

## Requirements

### Requirement: The lock MUST be scoped to a logical unit of work
The system SHALL lock by provider, mode, and work identity, and it SHALL NOT use a global lock for the whole application.

#### Scenario: Active discovery and rolling window run at the same time
- **GIVEN** the two runs use different logical lock keys
- **WHEN** both jobs start
- **THEN** the system SHALL allow them to proceed independently.

#### Scenario: Two runs target the same logical work unit
- **GIVEN** the same provider/mode/date key is already locked
- **WHEN** a second job tries to start
- **THEN** the second job SHALL not run concurrently.

### Requirement: The lock key MUST be deterministic
The system SHALL derive lock keys from stable business inputs such as provider, mode, date, window size, or notice code.

#### Scenario: The same rolling window is requested twice
- **GIVEN** the same date and window size are used twice
- **WHEN** the lock key is derived
- **THEN** both attempts SHALL compute the same key.

### Requirement: Lock acquisition and release MUST be observable
The system SHALL record lock acquisition attempts, lock key, and lock outcome in run stats or logs.

#### Scenario: The lock is contested
- **WHEN** a second job cannot acquire the same key
- **THEN** the system SHALL emit an observable failure path
- **AND** it SHALL not silently continue as if the lock had succeeded.

### Requirement: Advisory locking SHOULD be the first-phase implementation
The system SHOULD use `pg_try_advisory_lock` for this phase because the repository already runs through Postgres and the contract only needs scoped mutual exclusion.

#### Scenario: A future operator needs lock introspection
- **WHEN** a later phase needs visible lock rows or admin UI inspection
- **THEN** the team MAY add a dedicated table later
- **AND** this specification SHALL still remain valid for the current phase.
