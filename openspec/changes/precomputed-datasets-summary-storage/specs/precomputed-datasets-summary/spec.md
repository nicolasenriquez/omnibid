## ADDED Requirements

### Requirement: Persist Dataset Summary Snapshots
The system SHALL persist dataset summary snapshots in operational storage with a complete counter set for source files, raw rows, and normalized rows, plus snapshot metadata (`generated_at`, refresh mode, and status).

#### Scenario: Successful refresh persists a complete snapshot
- **WHEN** a summary refresh completes successfully
- **THEN** the system stores one new snapshot row containing all required counters and metadata

### Requirement: Serve Summary From Persisted Snapshot By Default
The system SHALL serve `GET /datasets/summary` from the latest successful persisted snapshot when one exists, without recomputing full table counts on every default request.

#### Scenario: Default summary request uses persisted snapshot
- **WHEN** a client calls `GET /datasets/summary` with default mode
- **THEN** the response returns counters from the latest successful persisted snapshot and includes freshness metadata

### Requirement: Support Explicit Fresh Refresh Semantics
The system SHALL support explicit fresh refresh execution that recomputes full counts and persists a new snapshot for subsequent default requests.

#### Scenario: Fresh request recomputes and updates snapshot
- **WHEN** a client calls `GET /datasets/summary?mode=fresh`
- **THEN** the system recomputes counts, persists a new snapshot, and returns the new counters with updated generation metadata

### Requirement: Preserve Last Good Snapshot On Refresh Failure
The system SHALL preserve the last successful snapshot when a refresh attempt fails and SHALL expose response metadata indicating stale data was served.

#### Scenario: Refresh failure does not corrupt durable summary state
- **WHEN** a fresh refresh attempt fails due to database or runtime error
- **THEN** the system keeps the previous successful snapshot unchanged and returns stale/failure metadata
