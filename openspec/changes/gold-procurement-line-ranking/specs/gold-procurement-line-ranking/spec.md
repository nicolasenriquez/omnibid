## ADDED Requirements

### Requirement: The Gold layer MUST rank suppliers at a time-aware notice-line grain
The system SHALL materialize Gold ranking rows at `supplier_key × notice_id × item_code × snapshot_time` and SHALL use only facts available as of the snapshot cutoff.

#### Scenario: A line later receives evidence that was not available at the cutoff
- **GIVEN** a notice line that is still open at `snapshot_time`
- **WHEN** the Gold dataset is built
- **THEN** the candidate row SHALL reflect only evidence available up to `snapshot_time`
- **AND** later bids, awards, or purchase-order links SHALL NOT alter the earlier row.

### Requirement: The Gold layer MUST derive labels from Silver in a hierarchical way
The system SHALL derive `participation_label`, `award_label`, and `materialization_label` from Silver procurement-cycle facts, and it SHALL treat `participation_label` as the first production target.

#### Scenario: A supplier participates and later wins
- **GIVEN** a supplier appears in `silver_bid_submission`
- **AND** the same supplier appears in `silver_award_outcome`
- **WHEN** labels are built
- **THEN** `participation_label` SHALL be positive
- **AND** `award_label` SHALL be positive
- **AND** the row SHALL remain time-aware with respect to the snapshot cutoff.

#### Scenario: A supplier only materializes later
- **GIVEN** a purchase-order link that appears after the cutoff
- **WHEN** labels are built for an earlier snapshot
- **THEN** `materialization_label` SHALL remain negative for that earlier row.

### Requirement: The Gold layer MUST keep feature selection leakage-safe and versioned
The system SHALL use an explicit feature registry for structured, sparse text, and graph features, and it SHALL exclude any feature that depends on information after the snapshot cutoff.

#### Scenario: A post-snapshot field is proposed as a feature
- **GIVEN** a field that is only known after award or materialization
- **WHEN** the feature registry is validated
- **THEN** the field SHALL be rejected as a Gold feature
- **AND** the validation SHALL fail fast.

### Requirement: The Gold layer MUST use an ordered baseline model stack
The system SHALL evaluate a calibrated linear model and a tree-based challenger first, and it SHALL choose the production winner using out-of-time validation.

#### Scenario: A random split looks better than the time-based split
- **WHEN** model evaluation is run
- **THEN** the system SHALL prefer the out-of-time validation result
- **AND** it SHALL NOT select a model based on random-split metrics alone.

### Requirement: The Gold layer MUST include sparse text evidence and graph features
The system SHALL build deterministic sparse text features and deterministic graph features, and it SHALL keep dense embeddings out of the first slice.

#### Scenario: The ranking job processes procurement text
- **WHEN** text features are built
- **THEN** the system SHALL use deterministic sparse representations
- **AND** it SHALL surface evidence refs from similar historical text
- **AND** it SHALL NOT require dense embeddings for the first production release.

#### Scenario: The ranking job processes graph context
- **WHEN** graph features are built
- **THEN** the system SHALL use a time-filtered heterogeneous procurement graph
- **AND** the graph SHALL include only edges valid up to the snapshot cutoff.

### Requirement: The Gold layer MUST persist versioned decision outputs
The system SHALL persist ranked supplier outputs and model-run metadata in additive Gold tables or views, and it SHALL keep the output contract queryable by the read-only investigation flow.

#### Scenario: A new model version is released
- **WHEN** the Gold score is rebuilt
- **THEN** the system SHALL write a new versioned output set
- **AND** it SHALL retain `model_version`, `feature_set_version`, `snapshot_cutoff`, score, rank, and evidence references.

### Requirement: The Gold layer MUST preserve the repository runtime contract
The system SHALL run under the repository's Docker-first DB contract and SHALL fail fast if the runtime settings are inconsistent.

#### Scenario: The Gold job runs in Docker
- **WHEN** the job loads its database settings
- **THEN** it SHALL use the container runtime contract and the correct database URLs
- **AND** it SHALL reject host-only settings that would break the containerized path.
