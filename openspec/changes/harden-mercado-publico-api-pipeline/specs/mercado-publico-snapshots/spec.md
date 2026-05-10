# Mercado Publico Snapshots Specification

## Purpose

Define the durable raw-payload and notice-snapshot contract for Mercado Publico observations.

## Requirements

### Requirement: Raw payloads MUST be preserved immutably
The system SHALL keep the upstream JSON payload as an immutable artifact and SHALL link it to the run and request that observed it.

#### Scenario: The same upstream payload is observed again
- **GIVEN** the same raw JSON is fetched twice
- **WHEN** the payload hash is computed
- **THEN** the system SHALL recognize the payload as the same artifact
- **AND** it SHALL not create a second semantic copy of the raw payload.

### Requirement: Notice snapshots MUST be idempotent by code and payload hash
The system SHALL deduplicate notice snapshots on `codigo_externo` plus payload hash or an equivalent canonical payload identity.

#### Scenario: The same code and same payload are observed twice
- **GIVEN** the same `codigo_externo` and payload hash are observed on the same day
- **WHEN** the snapshot persistence runs again
- **THEN** the system SHALL not create a duplicate semantic snapshot.

#### Scenario: The same code is observed with a changed payload
- **GIVEN** the same `codigo_externo` appears with a different payload hash
- **WHEN** the snapshot is persisted
- **THEN** the system SHALL create a new snapshot row
- **AND** it SHALL retain the earlier snapshot for auditability.

### Requirement: Snapshot lineage MUST remain explicit
The system SHALL store observed time, source endpoint, source mode, normalized status, and pipeline run linkage with every snapshot.

#### Scenario: An operator inspects a snapshot later
- **WHEN** the operator queries the notice snapshot history
- **THEN** they SHALL be able to see which mode observed it
- **AND** they SHALL be able to trace the snapshot back to the run that produced it.

### Requirement: The snapshot layer MUST stay separate from Silver
The system SHALL keep Mercado Publico snapshots as an operational observation layer and SHALL NOT introduce predictive columns into Silver as part of this change.

#### Scenario: A future Gold or ML idea is proposed
- **WHEN** the team reviews this specification
- **THEN** they SHALL see that the snapshot layer is observational
- **AND** they SHALL not infer that predictive scores belong in Silver.
