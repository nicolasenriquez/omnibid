### Requirement: Use a canonical Spanish NLP pipeline

The system SHALL process procurement text through a canonical Spanish NLP pipeline rather than through ad hoc tokenization or per-call heuristics.

#### Scenario: Spanish notice text is annotated deterministically
- **GIVEN** a procurement notice or line text written in Spanish
- **WHEN** the NLP pipeline processes the text
- **THEN** the system SHALL use the canonical spaCy Spanish pipeline
- **AND** SHALL produce deterministic token, lemma, POS, and entity annotations for the configured `nlp_version`

### Requirement: Detect language on normalized UTF-8 text

The system SHALL normalize input text to UTF-8 before language detection and SHALL use fastText for offline language identification.

#### Scenario: Short or low-confidence input falls back safely
- **GIVEN** a text fragment that is too short or below the configured confidence threshold
- **WHEN** language detection runs
- **THEN** the system SHALL mark the language as `und`
- **AND** SHALL NOT pretend the language is known

### Requirement: The repository MUST expose explicit NLP pipeline contract code
The system SHALL route NLP processing through explicit helpers and job entrypoints instead of ad hoc branching on filenames or runtime assumptions.

#### Scenario: A job starts
- **WHEN** the NLP annotation build begins
- **THEN** the entrypoint uses explicit source/profile and runtime validation
- **AND** unsupported or unknown profiles fail fast before any persistence work starts.

### Requirement: Persist only metadata and artifact references in Silver

The system SHALL keep Silver annotation rows metadata-only and reference-only.

#### Scenario: A Silver annotation row is written
- **GIVEN** a notice, notice-line, or purchase-order-line annotation
- **WHEN** the row is persisted to Silver
- **THEN** the system SHALL store versioned metadata such as `nlp_version`, `corpus_scope`, token payloads, n-gram payloads, and `tfidf_artifact_ref`
- **AND** the system SHALL NOT persist serialized vectors or business prediction scores

### Requirement: Keep semantic embeddings outside Silver

The system SHALL allow Sentence Transformers or Hugging Face-based semantic workflows only outside Silver.

#### Scenario: An embedding job is executed
- **GIVEN** a downstream semantic search or reranking job
- **WHEN** it produces embeddings or scores
- **THEN** the outputs SHALL be written only to an external artifact or downstream Gold layer
- **AND** the Silver tables SHALL remain unchanged

### Requirement: Respect the repository database environment contract

The system SHALL use the repository's existing `.env` and `.env.docker` database contract for any database-backed NLP work.

#### Scenario: The pipeline runs inside Docker
- **GIVEN** the job runs through the container-first workflow
- **WHEN** it reads database settings
- **THEN** it SHALL use `DATABASE_URL` and `TEST_DATABASE_URL` as defined by the Docker runtime template
- **AND** it SHALL use `db` and `db_test` service DNS names rather than `localhost`

#### Scenario: The pipeline runs locally
- **GIVEN** a host-local development session
- **WHEN** the job reads settings from `.env`
- **THEN** it SHALL use the localhost database URLs defined by the repository
- **AND** it SHALL fail fast if required settings are missing

### Requirement: The runtime contract MUST be validated by code
The system SHALL reject inconsistent NLP runtime settings before any DB-backed persistence work begins.

#### Scenario: The runtime is misconfigured
- **GIVEN** a missing or mismatched database setting
- **WHEN** the NLP job loads its runtime contract
- **THEN** it SHALL fail immediately
- **AND** it SHALL not fall back silently to an alternate database target.

### Requirement: Preserve explicit versioning and determinism

The system SHALL keep NLP outputs reproducible by version.

#### Scenario: The pipeline behavior changes
- **GIVEN** a change to model choice, rule patterns, or vectorizer configuration
- **WHEN** the pipeline is updated
- **THEN** the implementation SHALL bump `nlp_version`
- **AND** SHALL keep the row hash and artifact reference behavior deterministic for the new version
