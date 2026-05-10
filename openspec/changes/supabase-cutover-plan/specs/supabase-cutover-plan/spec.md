# Supabase Cutover Specification

## Purpose

Formalize the long-term path from the current Docker Compose/Postgres baseline to a controlled Supabase cutover.

## Requirements

### Requirement: The repository MUST treat Alembic as the schema source of truth
The system SHALL treat Alembic as the authoring source for the schema contract and use the current database only as a validation target for parity checks.

#### Scenario: A maintainer updates the cutover baseline
- **WHEN** the maintainer prepares the Supabase baseline
- **THEN** they derive it from the Alembic-backed contract
- **AND** they do not redefine the contract from the live database snapshot.

### Requirement: The repository MUST keep the Compose/Postgres baseline canonical until cutover is approved
The system SHALL continue to present `just compose-up` and `just docker-smoke` as the canonical local runtime path until the cutover change is explicitly approved.

#### Scenario: A maintainer reads the runtime docs
- **WHEN** the maintainer reads the runtime and operations docs
- **THEN** they see that Compose remains the baseline
- **AND** they do not infer that Supabase has already replaced it.

### Requirement: The repository MUST prove schema parity before any remote cutover
The system SHALL require a successful local schema reset and review against the current contract before `supabase link` or `supabase db push` can be treated as production-ready.

#### Scenario: The operator prepares the remote deployment
- **WHEN** the operator has not yet proven local parity
- **THEN** the change is not ready for remote deployment
- **AND** schema drift must be resolved first.

### Requirement: The repository MUST require a non-destructive dry run before a production push
The system SHALL require `supabase db push --dry-run` to be reviewed before any real `supabase db push` is executed.

#### Scenario: The operator is about to push to the remote project
- **WHEN** the dry run has not been checked
- **THEN** the production push is not approved
- **AND** the operator must stop and review the diff first.

### Requirement: The repository MUST keep historical data backfill outside the cutover path
The system SHALL treat historical data migration as a separate phase after schema parity and runtime cutover are stable.

#### Scenario: A planner adds migration tasks
- **WHEN** the planner reviews the cutover tasks
- **THEN** they see no historical backfill work in the cutover scope
- **AND** any data migration is tracked separately.

### Requirement: The repository MUST document rollback readiness before switching runtime contracts
The system SHALL document rollback instructions and cutover ownership before the runtime connection contract is switched.

#### Scenario: The cutover window is scheduled
- **WHEN** the cutover window opens
- **THEN** the rollback path is already documented
- **AND** an owner is assigned to execute the switch.
