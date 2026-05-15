## ADDED Requirements

### Requirement: Read contracts MUST remain backward-compatible
The system SHALL preserve the current opportunity and operations read contracts so existing workspace and ingestion flows keep working while the redesign is introduced.

#### Scenario: Existing opportunity list and detail calls are used
- **WHEN** the current clients call the opportunity read endpoints
- **THEN** the list and detail contracts still return the existing source-backed fields
- **AND** no breaking field removal is introduced by this change.

### Requirement: The API MUST expose explicit availability states for missing data
The backend SHALL provide the data-availability metadata needed for the UI to distinguish supported, partial, and unavailable facts.

#### Scenario: A detail field is not source-backed
- **WHEN** a request asks for a field such as documents, bases, or anexos that is not currently exposed
- **THEN** the contract returns an explicit unavailable state
- **AND** it does not fabricate a value or silently omit the gap.

### Requirement: Opportunity read contracts MUST stay source-backed and deterministic
The backend SHALL expose only source-backed facts, explicit derivations, and human-readable availability metadata for opportunity review.

#### Scenario: A client asks for prioritization data
- **WHEN** the opportunity API needs to support a prioritization view
- **THEN** it may expose deterministic derived buckets from existing facts
- **AND** it SHALL NOT expose predictive score, forecast, or recommendation fields as Silver truth.

### Requirement: The API MUST support source-backed workspace KPIs only
The backend SHALL expose summary metrics for the opportunity workspace only when they can be derived from persisted facts and read as authoritative counts.

#### Scenario: The workspace needs a KPI card not present today
- **WHEN** the redesign requires a top-level count such as `Nuevas hoy` or a similar read-only summary
- **THEN** the backend shall either expose a summary metric computed from persisted data or mark the KPI unavailable
- **AND** it SHALL NOT fake the count from a partial page or a client-local sample.

### Requirement: The API MUST expose ingestion lineage for the operational center
The backend SHALL expose runs, files, steps, ingestion batches, and request-ledger details needed to trace CSV and API ingestion history.

#### Scenario: User inspects a past ingestion run
- **WHEN** the Ingestion Center requests run or file history
- **THEN** the contract includes the source file, run ID, terminal state, and available telemetry
- **AND** any missing replay/payload details remain explicit rather than inferred.

### Requirement: Predictive outputs MUST stay out of Silver and out of these read contracts
The backend SHALL not introduce `*_score`, `*_probability`, `forecast_*`, or `recommendation_*` fields as facts in Silver or as implied truth in the read contracts.

#### Scenario: A future model asks for a score field
- **WHEN** an implementation proposes a predictive score or recommendation
- **THEN** the change SHALL route that work to a separate Gold-capability proposal
- **AND** it SHALL NOT be merged into this read-only contract slice.

