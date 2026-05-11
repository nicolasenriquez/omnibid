# Supabase Readiness Delta

## ADDED Requirements

### Requirement: The repository MUST document that the Mercado Publico API hardening is additive to the Supabase readiness lane
The system SHALL document that the Mercado Publico API pipeline hardening schema changes (ledger, runs, snapshots, locks) are compatible with both local Compose Postgres and remote Supabase Postgres, and that no runtime switch or historical backfill is required by this hardening phase.

#### Scenario: A maintainer reviews the Supabase readiness contract after API hardening
- **WHEN** the maintainer opens the Supabase readiness runbook after the Mercado Publico API hardening is merged
- **THEN** they see an explicit statement that the hardening is additive and does not mandate a cutover
- **AND** they understand that local Compose remains the canonical day-to-day runtime
- **AND** the schema is versioned and migration-backed for both environments.

## MODIFIED Requirements

### Requirement: The repository MUST expose Supabase readiness settings without replacing the live runtime contract
The system SHALL expose `SUPABASE_DB_URL`, `SUPABASE_PROJECT_REF`, and `SUPABASE_DB_POOL_MODE` in the repository config surface while preserving `DATABASE_URL` and `TEST_DATABASE_URL` as the operational Compose contract, and SHALL validate that the Mercado Publico API pipeline works against both local and remote Postgres.

#### Scenario: A container starts with the new environment variables
- **WHEN** the backend or tooling container loads settings
- **THEN** it can read the Supabase readiness settings
- **AND** it still uses the existing Compose database contract for the live runtime
- **AND** the Mercado Publico API lane functions without a runtime-specific code path.

### Requirement: The repository MUST keep a versioned Supabase scaffold
The system SHALL commit a `supabase/` directory containing `config.toml` and versioned migration files, including Mercado Publico API hardening migrations, so the CLI-first lane can be extended without re-deriving the structure.

#### Scenario: A future migration is added
- **WHEN** the maintainer creates a new Supabase migration
- **THEN** it lands under `supabase/migrations/` with a versioned filename
- **AND** the repository keeps the local CLI scaffold committed.
