# API Request Budget Specification

## Purpose

Define a persistent daily budget for Mercado Publico API requests that survives process restarts and is enforced transactionally.

## Requirements

### Requirement: The request budget MUST be persisted in Postgres
The system SHALL record counted API usage in a durable ledger and SHALL use that ledger as the source of truth for daily consumption.

#### Scenario: A process restarts in the middle of the day
- **GIVEN** one or more requests were already counted before restart
- **WHEN** a new process starts and checks the budget
- **THEN** the system SHALL see the existing counted rows
- **AND** it SHALL NOT reset the daily counter to zero.

### Requirement: The request budget MUST be enforced before the upstream call
The system SHALL allow a request when the day's counted units are below the configured limit and SHALL reject the request when the limit is reached.

#### Scenario: The ledger has 9999 counted units and the limit is 10000
- **GIVEN** the configured limit is 10000
- **AND** the ledger already contains 9999 cost units for the day
- **WHEN** the next counted request is reserved
- **THEN** the system SHALL allow exactly one more unit.

#### Scenario: The ledger already reached the limit
- **GIVEN** the configured limit is 10000
- **AND** the ledger already contains 10000 cost units for the day
- **WHEN** another counted request is requested
- **THEN** the system SHALL fail fast before the upstream call executes.

### Requirement: Canonical request identity MUST exclude secrets
The system SHALL compute request identity from non-secret canonical parameters, SHALL redact secrets from safe URLs, and SHALL deduplicate on provider + request hash + request date.

#### Scenario: The same canonical request is repeated on the same day
- **GIVEN** a request with the same canonical parameters is reissued on the same date
- **WHEN** the ledger reservation runs again
- **THEN** the system SHALL not create a second semantic charge for the same request
- **AND** it SHALL not expose the ticket in the persisted safe URL.

### Requirement: Request execution metadata MUST remain auditable
The system SHALL store endpoint, method, status code, success flag, response hash, error details, and pipeline run linkage for each counted request.

#### Scenario: A request fails with 429
- **WHEN** the request is recorded
- **THEN** the ledger SHALL capture the status code, failure type, and run reference
- **AND** the operator SHALL be able to inspect the failed attempt without the ticket secret.
