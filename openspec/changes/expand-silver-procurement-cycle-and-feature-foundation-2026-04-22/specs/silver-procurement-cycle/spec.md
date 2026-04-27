## ADDED Requirements

### Requirement: Model Canonical Procurement Lifecycle Entities
The system SHALL represent procurement in Silver as explicit canonical entities with defined grain:
- notice
- notice line
- bid submission
- award outcome
- purchase order
- purchase order line

#### Scenario: Notice-level grain remains one row per notice
- **WHEN** Silver rebuild processes licitación source data
- **THEN** each canonical notice entity is upserted once per notice business key and is not duplicated per supplier

#### Scenario: Notice-line grain remains independent from offers
- **WHEN** Silver rebuild processes licitación source data with item information
- **THEN** each canonical notice-line entity is upserted independently of offer presence

#### Scenario: Offer and award semantics are separated
- **WHEN** source data includes both offer and adjudication fields in the same raw row
- **THEN** Silver persists offer state in bid-submission entities and adjudication state in award-outcome entities as distinct contracts

### Requirement: Keep Purchase-Order Linkage to Notice Explicit and Optional
The system SHALL model notice-to-purchase-order linkage as an explicit relationship that allows null linkage.

#### Scenario: OC row with notice code creates an explicit link
- **WHEN** purchase-order source data includes `CodigoLicitacion`
- **THEN** Silver persists an explicit notice-purchase-order link record with deterministic linkage type metadata

#### Scenario: OC row without notice code remains valid
- **WHEN** purchase-order source data lacks `CodigoLicitacion`
- **THEN** Silver SHALL still persist purchase order and purchase-order-line entities without forcing synthetic notice linkage

### Requirement: Persist Canonical Master Entities With Deterministic Identity
The system SHALL maintain canonical buyer/unit/supplier/category master entities with deterministic business-key contracts and explicit relations from transactional entities.

#### Scenario: Master entities are reused across process tables
- **WHEN** multiple process entities reference the same buyer, unit, supplier, or category key
- **THEN** Silver joins resolve to one canonical master entity per key contract

### Requirement: Preserve Lineage and Deterministic Replay Semantics
The system SHALL preserve source lineage metadata and deterministic idempotent rebuild behavior across new canonical entities.

#### Scenario: Replay on unchanged source state is convergent
- **WHEN** Silver rebuild is replayed with unchanged source inputs
- **THEN** canonical process entities converge without duplicate semantic rows and telemetry reflects deterministic outcomes
