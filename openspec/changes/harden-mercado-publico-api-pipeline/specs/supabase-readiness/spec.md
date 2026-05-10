# Supabase Readiness Specification

## Purpose

Keep the Mercado Publico hardening lane compatible with both the current Compose/Postgres baseline and the future Supabase remote path.

## Requirements

### Requirement: The repository MUST keep the current Compose baseline canonical
The system SHALL keep the existing Docker Compose runtime as the canonical local baseline until a separate cutover is approved.

#### Scenario: A maintainer reads the runtime docs
- **WHEN** the maintainer reviews the repository docs
- **THEN** they SHALL see that Compose remains the current baseline
- **AND** they SHALL not infer that Supabase already replaced it.

### Requirement: The pipeline MUST remain compatible with Supabase remote execution
The system SHALL be able to run the hardening lane against local Postgres or a Supabase-hosted Postgres connection without changing the business logic.

#### Scenario: The job runs locally
- **WHEN** the job uses the Docker Compose database URL
- **THEN** it SHALL use the same operational contract as the existing local stack.

#### Scenario: The job runs remotely
- **WHEN** the job is pointed at a Supabase database URL
- **THEN** it SHALL still use the same migration-backed schema and pipeline logic
- **AND** it SHALL not rely on frontend-only secrets.

### Requirement: Production config MUST fail fast on trivial credentials
The system SHALL reject obviously unsafe production database defaults and SHALL require explicit database configuration in production.

#### Scenario: Production is configured with postgres/postgres
- **WHEN** the app starts in production mode
- **THEN** it SHALL fail fast
- **AND** it SHALL not silently accept trivial credentials.

### Requirement: Supabase documentation MUST stay additive
The system SHALL keep Supabase CLI readiness documented as an additive lane and SHALL keep historical migration/backfill work separate.

#### Scenario: An operator follows the readiness docs
- **WHEN** the operator reads the Supabase readiness guidance
- **THEN** they SHALL see the local CLI flow, the remote link/push flow, and the cutover boundary
- **AND** they SHALL not see historical backfill folded into the readiness step.

### Requirement: Supabase secrets MUST stay backend-only
The system SHALL keep Supabase service-role credentials out of frontend code, frontend environment examples, and public-facing docs snippets.

#### Scenario: A frontend contributor copies config examples
- **WHEN** the contributor reviews the repo examples
- **THEN** they SHALL not find a service-role secret in frontend examples
- **AND** they SHALL not infer that the browser can call Supabase with elevated credentials.
