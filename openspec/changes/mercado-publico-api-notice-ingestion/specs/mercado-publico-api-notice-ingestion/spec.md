## ADDED Requirements

### Requirement: Mercado Público notice sync MUST be notice-only and backend-only
The system SHALL ingest published licitaciones from Mercado Público in this change. It SHALL NOT add OC, buyer, or supplier fetchers yet, and it SHALL NOT call the external API from the frontend.

#### Scenario: Operator runs the daily sync
- **WHEN** the daily sync job runs
- **THEN** it uses the backend Mercado Público client only
- **AND** it fetches licitaciones for the target date in the published state
- **AND** no frontend component makes an external request to ChileCompra.

### Requirement: Technical identifiers MUST stay internal
The system SHALL keep request, payload, snapshot, and hash-field names internal, and it SHALL use Spanish procurement language with accents in any adjacent business copy.

#### Scenario: Future adjacent copy references the lane
- **WHEN** documentation or a neighboring user-facing surface describes this API lane
- **THEN** it uses terms such as `licitación`, `código externo`, `estado oficial`, `organismo comprador`, and `unidad de compra`
- **AND** it does not expose raw internal field names such as `request_hash` or `payload_sha256` as labels.

### Requirement: The API client MUST fail fast on invalid or incomplete configuration
The system SHALL reject Mercado Público API use when the feature is enabled but the ticket or core settings are missing or invalid.

#### Scenario: Enabled without ticket
- **GIVEN** `MERCADO_PUBLICO_API_ENABLED=true`
- **AND** the ticket is empty
- **WHEN** the client or sync job starts
- **THEN** it fails before any upstream request is made
- **AND** the error is explicit and actionable.

#### Scenario: Secret redaction
- **GIVEN** a configured ticket
- **WHEN** the client logs request metadata
- **THEN** the ticket is never emitted in clear text
- **AND** request diagnostics remain safe to store.

### Requirement: Daily notice sync MUST persist request, payload, and snapshot lineage
The system SHALL persist one request record, one raw payload snapshot, and one queryable notice snapshot for each successful daily sync slice.

#### Scenario: Same request repeated
- **WHEN** the same canonical request is executed twice
- **THEN** request hash dedupe prevents uncontrolled duplicate semantic work
- **AND** payload hash tracking preserves raw traceability
- **AND** the snapshot table stays queryable by run and date.

#### Scenario: Upstream returns a new payload
- **WHEN** the response body changes for the same endpoint and parameters
- **THEN** the payload snapshot remains immutable
- **AND** the new payload hash is recorded as a distinct snapshot.

### Requirement: Published notices MUST be queryable without parsing raw JSON
The system SHALL expose the daily published notices through a normalized snapshot table.

#### Scenario: Daily published notices available
- **WHEN** the sync completes successfully
- **THEN** each row exposes notice code, title, official status, publication date, close date, buyer info, and estimated amount where available
- **AND** missing values remain explicit `null` rather than inferred placeholders.

#### Scenario: Data is queried later
- **WHEN** an operator inspects the snapshot by date or notice code
- **THEN** the result is readable without reopening raw response JSON.

### Requirement: Sync MUST honor upstream limits and bounded retries
The system SHALL respect the official daily limit and shall use bounded retry/backoff for transient upstream failures.

#### Scenario: Upstream returns 429 or 5xx
- **WHEN** a transient failure occurs
- **THEN** the client retries only within the configured budget
- **AND** the sync stops once the budget is exhausted
- **AND** the run is marked failed with a concrete error summary.

#### Scenario: Daily limit is reached
- **WHEN** the configured request budget for the day is exhausted
- **THEN** the job stops before another upstream request is made
- **AND** the run reports a rate-limit exhaustion state.

### Requirement: Existing CSV pipeline MUST remain unchanged
The system SHALL keep the current CSV ingestion, normalization, Silver builds, and opportunity workspace behavior unchanged in this change.

#### Scenario: Sync disabled
- **WHEN** the Mercado Público API feature flag is disabled
- **THEN** the existing CSV pipeline still runs exactly as before
- **AND** no new runtime dependency on the API exists.

#### Scenario: Current product surfaces load
- **WHEN** `/opportunities` or other existing backend flows are used
- **THEN** their behavior remains unchanged by this change.
