## ADDED Requirements

### Requirement: Restrict Silver to Deterministic Feature Foundations
The system SHALL persist only deterministic and reproducible feature foundations in Silver.

Allowed examples:
- normalized text variants (`*_raw`, `*_clean`)
- temporal durations and chain-integrity flags
- administrative and contractual flags
- structural and competition metrics
- factual notice-to-order materialization metrics

#### Scenario: Deterministic derivation is persisted
- **WHEN** a Silver derivation can be recomputed from current or prior event-state fields without future leakage
- **THEN** the derivation is eligible for Silver persistence

### Requirement: Prevent Predictive Business Outputs in Silver
The system SHALL NOT persist predictive business outputs in Silver.

Forbidden examples:
- opportunity ranking
- winnability/convenience scores
- final anomaly verdicts
- forecasting outputs
- recommendation outputs

#### Scenario: Predictive score is requested for Silver
- **WHEN** a derivation depends on predictive modeling or future outcomes
- **THEN** the system SHALL reject Silver persistence and require placement in downstream Gold/feature-serving layers

### Requirement: Persist Semantic Annotations as Versioned Technical Metadata
The system SHALL store NLP/semantic enrichments as versioned technical annotations, not as business truth.

#### Scenario: Annotation write includes version contract
- **WHEN** semantic annotation data is written for notices, lines, or purchase-order lines
- **THEN** each record includes an explicit `nlp_version` and deterministic artifact-reference metadata
- **AND** TF-IDF data is stored as artifact reference identifiers only, not serialized vectors

#### Scenario: Annotation data is consumed downstream
- **WHEN** downstream consumers read annotation entities
- **THEN** annotations are interpreted as reproducible technical metadata and not as final business decisions

### Requirement: Use Feature Extraction Pipelines Without Training Business Models in Silver
The system SHALL implement Silver NLP pipelines as deterministic feature extraction workflows and SHALL NOT train supervised business models in Silver.

Allowed implementation examples:
- deterministic tokenization/normalization
- `CountVectorizer`/n-gram extraction
- `TfidfVectorizer` artifact generation with reference-only persistence

Forbidden in Silver:
- train/test split and supervised classifier training for business outcomes
- persistence of prediction outputs or model-derived business scores

#### Scenario: Silver NLP pipeline runs for annotation generation
- **WHEN** text annotation jobs execute for notice, notice line, or purchase-order line entities
- **THEN** generated outputs are limited to technical annotation payloads plus versioned artifact references
- **AND** no supervised business model artifacts or prediction outputs are persisted in Silver

#### Scenario: A training-oriented NLP step is proposed in Silver
- **WHEN** a pipeline change introduces supervised model fitting or prediction outputs in Silver
- **THEN** the change SHALL be rejected at Silver scope and redirected to downstream Gold/feature-serving workflows

### Requirement: Enforce Leakage Guardrails for Feature Foundations
The system SHALL prevent Silver feature columns that require future-state knowledge at event time.

#### Scenario: Candidate feature uses future outcome data
- **WHEN** a candidate Silver feature references fields unavailable at event cutoff time
- **THEN** the feature SHALL be excluded from Silver and documented for later-stage modeling workflows
