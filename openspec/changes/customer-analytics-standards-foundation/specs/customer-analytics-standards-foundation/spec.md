## ADDED Requirements

### Requirement: The repository MUST have a source-backed customer analytics standard
The system SHALL provide a repository-local customer analytics standard in `docs/standards/customer-analytics-standards.md` that defines the procurement analytics source contract, runtime contract, and Silver boundary.

#### Scenario: A future agent looks for the contract
- **WHEN** an agent starts work on procurement analytics
- **THEN** it can read the standard and understand the current source profile, runtime contract, and Silver rules without re-deriving them from code.

### Requirement: The standard MUST document the current source profiles
The system SHALL document `csv_drop`, `api_json`, and `open_data_snapshot` as explicit source profiles, and it SHALL keep the current CSV drop pipeline as the canonical implemented profile until a separate adapter proposal is approved.

#### Scenario: A source profile is chosen
- **WHEN** a pipeline slice is being planned
- **THEN** the chosen profile is explicit
- **AND** no agent silently treats the API and CSV contracts as interchangeable.

### Requirement: The runtime contract MUST stay explicit
The system SHALL document the host vs Docker environment split, the separate `DATABASE_URL` and `TEST_DATABASE_URL` values, and the effective Compose PostgreSQL 16 baseline before any later implementation work begins.

#### Scenario: The environment is reviewed
- **WHEN** a maintainer checks the docs before running a DB-backed job
- **THEN** the maintainer can see which URLs are for host use and which are for container use
- **AND** the docs match the actual Compose runtime instead of stale version text.

### Requirement: The repository MUST expose explicit pipeline contract code
The system SHALL route procurement analytics through explicit source-profile and runtime contract helpers instead of ad hoc branching on file names or environment assumptions.

#### Scenario: A pipeline job starts
- **WHEN** the current CSV pipeline runs
- **THEN** the code path uses an explicit source-profile contract
- **AND** unsupported or unknown profiles fail fast instead of being treated as equivalent.

### Requirement: The official source registry MUST cover the docs used by the standard
The system SHALL keep the official sources registry aligned with the Python stdlib, database, and ChileCompra/Mercado Publico docs used by the standard.

#### Scenario: A future agent needs a source URL
- **WHEN** the agent needs the official docs for CSV parsing, upserts, or ChileCompra source semantics
- **THEN** the registry provides the URLs directly
- **AND** the agent does not need to rediscover the same source set from scratch.

### Requirement: Silver MUST remain metadata-only and reference-only
The system SHALL keep the Silver annotation boundary unchanged: metadata and references only, no dense vectors, no scores, and no forecast outputs.

#### Scenario: A future implementation touches NLP annotations
- **WHEN** a later slice updates the text annotation path
- **THEN** it preserves `tfidf_artifact_ref` as a `tfidf://...` reference string
- **AND** it does not store serialized vectors or predictive scores in Silver.

### Requirement: The runtime contract MUST be validated by code
The system SHALL fail fast when the DB/runtime settings are inconsistent, missing, or mismatched to the current Docker-versus-host execution mode.

#### Scenario: A DB-backed job loads settings
- **WHEN** the job reads `.env` or `.env.docker`
- **THEN** it can distinguish host localhost URLs from Docker service-DNS URLs
- **AND** it fails immediately if the required runtime contract is incomplete.

### Requirement: The current runtime schema MUST remain unchanged in this slice
The system SHALL treat this change as documentation plus contract-code hardening only.

#### Scenario: The change is merged
- **WHEN** the OpenSpec change is applied
- **THEN** backend code changes stay limited to contract helpers, validation, and tests
- **AND** no Silver schema rewrite is required before a separate implementation proposal.
