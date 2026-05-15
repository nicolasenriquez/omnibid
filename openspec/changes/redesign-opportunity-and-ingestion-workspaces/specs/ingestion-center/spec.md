## ADDED Requirements

### Requirement: The Ingestion Center MUST surface operational state from source-backed read contracts
The Ingestion Center SHALL expose runs, files, dataset summary snapshots, and manual upload jobs as the backbone of the operational surface.

#### Scenario: User opens the Ingestion Center overview
- **WHEN** the overview renders
- **THEN** it shows recent runs, recent files, and dataset summary information when those contracts are available
- **AND** any unsupported KPI is rendered as unavailable rather than implied.

### Requirement: The Ingestion Center MUST preserve the manual upload lifecycle
The Ingestion Center SHALL preserve the current preflight, process, progress, and job-detail flow for CSV uploads.

#### Scenario: User uploads a CSV file
- **WHEN** the preflight and process steps run
- **THEN** the UI can show progress, telemetry, and terminal job state from the current manual upload contract
- **AND** schema validation failures remain visible and explicit.

### Requirement: The Ingestion Center MUST distinguish CSV lineage from API lineage
The Ingestion Center SHALL separate manual CSV lineage from API request lineage so traceability remains clear.

#### Scenario: User reviews a successful CSV job
- **WHEN** the job detail opens
- **THEN** it shows the source file, pipeline run, ingestion batch, and step lineage
- **AND** it does not merge those facts with API request lineage.

### Requirement: The Ingestion Center MUST expose operational diagnostics only when they are source-backed
The Ingestion Center SHALL show API request, HTTP status, rate-limit, latency, and error diagnostics only when those values are backed by current models or an explicit read-only extension.

#### Scenario: A diagnostic field is not available
- **WHEN** the UI needs to render live worker status, request latency, or a request-ledger detail that does not exist yet
- **THEN** it shows an explicit unavailable state
- **AND** it does not synthesize a fake metric.

### Requirement: The Ingestion Center MUST support reproducibility and replay auditing
The Ingestion Center SHALL surface file hashes, run IDs, source metadata, and telemetry so operators can trace a job end-to-end.

#### Scenario: User inspects a past run
- **WHEN** the history row opens
- **THEN** the UI can show the related source file, pipeline run, and terminal status
- **AND** if a payload or replay trace is not stored, the UI shows that gap explicitly.

### Requirement: The Ingestion Center MUST stay visually separate from commercial review
The Ingestion Center SHALL not dominate the opportunity review surface.

#### Scenario: User switches between opportunity review and ingestion operations
- **WHEN** the user moves from `/licitaciones` into the Ingestion Center
- **THEN** the operational diagnostics live in a separate surface
- **AND** the commercial review shell remains concise and focused on decision work.

