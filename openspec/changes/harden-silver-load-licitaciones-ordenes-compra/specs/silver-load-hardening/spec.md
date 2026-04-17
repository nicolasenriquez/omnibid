# Capability: silver-load-hardening

## ADDED Requirements

### Requirement: Deterministic business-key upsert for Silver entities
Silver load MUST upsert licitaciones, licitacion_items, ofertas, ordenes_compra, and ordenes_compra_items using explicit business conflict keys so reruns remain idempotent.

#### Scenario: Reprocessing already-loaded rows
- **GIVEN** the same Bronze rows are loaded more than once
- **WHEN** Silver load runs with business-key upserts
- **THEN** duplicate business entities are not created
- **AND** mutable non-key fields are updated deterministically

### Requirement: Fail-fast transform contract for critical keys
Silver transform builders MUST reject records missing critical keys required to build canonical entities.

#### Scenario: Missing mandatory identifiers
- **GIVEN** a Bronze row missing required keys for a target Silver entity
- **WHEN** the transform builder processes that row
- **THEN** the row is rejected instead of silently coerced
- **AND** the rejection is surfaced in operational output

### Requirement: Observable Silver load execution
Silver load MUST expose processed and rejected row outcomes per dataset so operators can diagnose data quality and ingestion drift.

#### Scenario: Monitoring Silver run outcomes
- **GIVEN** a Silver load execution for licitaciones or ordenes_compra
- **WHEN** the run completes
- **THEN** progress and completion metrics are available per dataset
- **AND** rejection/error signals are observable in run output and runbooks
