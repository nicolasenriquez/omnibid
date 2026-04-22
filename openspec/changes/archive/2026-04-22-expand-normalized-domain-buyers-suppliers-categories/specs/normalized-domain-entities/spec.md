## ADDED Requirements

### Requirement: Persist Canonical Buyer Entities
The system SHALL persist canonical buyer entities in normalized storage using deterministic identity keys and idempotent upsert semantics.

#### Scenario: Buyer row with valid identity is upserted
- **WHEN** normalized build processes a transactional row with a non-empty `codigo_unidad_compra`
- **THEN** the system upserts one buyer entity using that business key and updates mutable descriptive attributes deterministically

#### Scenario: Buyer row missing required identity is rejected for buyer domain
- **WHEN** normalized build processes a transactional row without a valid buyer business key
- **THEN** the system SHALL NOT write a buyer entity, SHALL persist a data-quality issue for the rejection, and SHALL keep the run telemetry consistent

### Requirement: Persist Canonical Supplier Entities
The system SHALL persist canonical supplier entities using deterministic identity precedence (`codigo_proveedor`, fallback `rut_proveedor`) and idempotent upsert semantics.

#### Scenario: Supplier row uses preferred supplier code
- **WHEN** a source transactional row includes `codigo_proveedor`
- **THEN** the system upserts the supplier entity with canonical key format `codigo:<codigo_proveedor>`

#### Scenario: Supplier row falls back to RUT identity
- **WHEN** `codigo_proveedor` is missing and `rut_proveedor` is present
- **THEN** the system upserts the supplier entity with canonical key format `rut:<rut_proveedor>`

#### Scenario: Supplier row without identity is rejected
- **WHEN** both `codigo_proveedor` and `rut_proveedor` are missing or empty
- **THEN** the system SHALL NOT write a supplier entity and SHALL persist a quality issue for deterministic rejection accounting

### Requirement: Persist Canonical Category Entities
The system SHALL persist canonical category entities from normalized transactional item rows using `codigo_categoria` as the business key.

#### Scenario: Category row with code is upserted
- **WHEN** normalized item data includes `codigo_categoria`
- **THEN** the system upserts one canonical category entity keyed by `codigo_categoria`

#### Scenario: Category row without code is rejected
- **WHEN** normalized item data lacks a valid `codigo_categoria`
- **THEN** the system SHALL NOT write a category entity and SHALL persist a quality issue for category rejection

### Requirement: Preserve Deterministic Build and Lineage Semantics
The system SHALL execute domain-entity population as part of the normalized build in deterministic order with explicit telemetry and unchanged lineage contracts.

#### Scenario: Domain population runs after transactional canonicalization
- **WHEN** normalized build executes for a dataset
- **THEN** domain entity extraction/upserts execute after transactional entity upserts in the same run lifecycle

#### Scenario: Repeated run remains idempotent
- **WHEN** the normalized build is replayed with unchanged source state
- **THEN** canonical domain tables converge without duplicate semantic entities and run telemetry reflects deterministic inserted/existing counts
