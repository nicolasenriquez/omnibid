# api-request-budget Specification

## Purpose
TBD - created by archiving change harden-mercado-publico-api-pipeline. Update Purpose after archive.
## Requirements
### Requirement: The system MUST enforce a durable daily request budget
The system SHALL track daily API request consumption in the persisted request ledger (`api_source_request`) and compare total consumed units against `MERCADO_PUBLICO_DAILY_REQUEST_LIMIT` before issuing any upstream Mercado Publico call.

#### Scenario: A new run starts within the daily budget
- **WHEN** a Mercado Publico sync run starts and the current day's consumed request count is below the configured limit
- **THEN** the system reserves a budget unit in the ledger before calling the upstream API
- **AND** the reservation is persisted transactionally.

#### Scenario: A new run exceeds the daily budget
- **WHEN** a Mercado Publico sync run starts and the current day's consumed request count has already reached the configured limit
- **THEN** the system rejects the upstream call with a clear budget-exhausted error
- **AND** no API request is issued.

### Requirement: The budget MUST survive process restarts
The system SHALL persist budget consumption in the database so that a process restart does not reset the daily counter.

#### Scenario: A sync process is restarted mid-day
- **WHEN** a Mercado Publico sync process is killed and a new process starts on the same day
- **THEN** the new process reads the persisted ledger count for the current day
- **AND** the remaining budget reflects real consumption, not a fresh zero.

### Requirement: The request ledger MUST redact secrets
The system SHALL store `request_url_safe` with the ticket query parameter removed and SHALL compute `request_hash` over the safe URL so that the raw ticket is never persisted in queryable ledger columns.

#### Scenario: An operator inspects the request ledger
- **WHEN** the operator queries `api_source_request`
- **THEN** the `request_url_safe` column does not contain the API ticket value
- **AND** the `request_hash` column is computed from the safe URL.
