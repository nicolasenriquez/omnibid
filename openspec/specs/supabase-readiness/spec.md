# Supabase Readiness Specification

## Purpose

Document the CLI-first Supabase transition lane while preserving the current Compose/Postgres baseline.

## Requirements

### Requirement: The repository MUST keep the Compose baseline canonical
The system SHALL keep `just compose-up` and `just docker-smoke` as the current canonical runtime path until a separate cutover change is approved.

#### Scenario: A maintainer reviews the runtime docs
- **WHEN** the maintainer reads the main runtime documentation
- **THEN** they see that Docker Compose remains the live baseline
- **AND** they do not infer that Supabase has already replaced it.

### Requirement: The repository MUST expose Supabase readiness settings without replacing the live runtime contract
The system SHALL expose `SUPABASE_DB_URL`, `SUPABASE_PROJECT_REF`, and `SUPABASE_DB_POOL_MODE` in the repository config surface while preserving `DATABASE_URL` and `TEST_DATABASE_URL` as the operational Compose contract.

#### Scenario: A container starts with the new environment variables
- **WHEN** the backend or tooling container loads settings
- **THEN** it can read the Supabase readiness settings
- **AND** it still uses the existing Compose database contract for the live runtime.

### Requirement: The repository MUST keep a versioned Supabase scaffold
The system SHALL commit a `supabase/` directory containing `config.toml` and versioned migration files so the CLI-first lane can be extended without re-deriving the structure.

#### Scenario: A future migration is added
- **WHEN** the maintainer creates a new Supabase migration
- **THEN** it lands under `supabase/migrations/` with a versioned filename
- **AND** the repository keeps the local CLI scaffold committed.

### Requirement: The repository MUST document the CLI-first workflow and guardrails
The system SHALL document the local and remote Supabase CLI sequence, including `supabase init`, `supabase start`, `supabase migration new`, `supabase db reset`, `supabase login`, `supabase link --project-ref`, `supabase db push --dry-run`, and `supabase db push`, together with the schema-first and no-historical-backfill guardrails.

#### Scenario: An operator prepares the cutover lane
- **WHEN** the operator follows the Supabase readiness runbook
- **THEN** they can stage and review the local schema path before any remote push
- **AND** they see that historical data backfill is a separate phase.

### Requirement: The repository MUST retain source-backed documentation for the Supabase lane
The system SHALL record the official Supabase docs used by the readiness lane in `docs/references/` and keep the official source registry aligned with those docs.

#### Scenario: A future agent needs the sources
- **WHEN** the future agent opens the repo-local source registry or SDD note
- **THEN** they can identify the official Supabase CLI and deployment docs
- **AND** they do not need to rediscover the same source set from scratch.
