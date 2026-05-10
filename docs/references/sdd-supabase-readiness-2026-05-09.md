# SDD Reference Note

## Metadata

- Change/Proposal: harden-api-pipeline-postgres-queue
- Date: 2026-05-09
- Author: Codex
- Area (backend/db/pipeline/api/tooling): docs / backend / db / tooling

## Question

- How should Omnibid stage a Supabase CLI transition without replacing the current Docker Compose/Postgres baseline too early?

## Official Sources Consulted

1. https://supabase.com/docs/guides/local-development/cli/getting-started
   - Topic/section: Supabase CLI quick start
   - Relevant contract: `supabase init` creates the local project scaffold and `supabase start` launches the local stack
2. https://supabase.com/docs/guides/cli/local-development
   - Topic/section: local development with schema migrations
   - Relevant contract: Supabase migrations are stored under `supabase/migrations/`, and local schema changes are validated with `supabase db reset`
3. https://supabase.com/docs/guides/local-development/managing-config
   - Topic/section: config and secrets
   - Relevant contract: `supabase/config.toml` is the local configuration file and may reference environment variables
4. https://supabase.com/docs/guides/deployment/database-migrations
   - Topic/section: deployment migrations
   - Relevant contract: versioned migration files are the deployment contract and should be reviewed before release
5. https://supabase.com/docs/guides/database/connecting-to-postgres/serverless-drivers
   - Topic/section: database connection modes
   - Relevant contract: Supabase projects expose connection strings and pooler modes, including transaction-mode guidance for transient clients

## Repository Context Consulted

1. `backend/core/config.py`
   - Topic/section: settings loader
   - Relevant contract: `DATABASE_URL` and `TEST_DATABASE_URL` remain the live Compose runtime baseline
2. `.env.example`
   - Topic/section: host runtime template
   - Relevant contract: operator-visible environment contract for local development
3. `.env.docker`
   - Topic/section: Docker runtime template
   - Relevant contract: Compose env injection for containerized runtime
4. `docker-compose.yml`
   - Topic/section: service environment
   - Relevant contract: backend and tooling containers keep the Compose Postgres runtime as the baseline
5. `docs/runbooks/local_development.md`
   - Topic/section: local runtime guidance
   - Relevant contract: Docker-first execution remains the primary path
6. `docs/architecture/system_architecture.md`
   - Topic/section: runtime boundary
   - Relevant contract: Compose remains the canonical runtime boundary until a separate cutover is approved
7. `docs/references/sdd-official-sources-registry.md`
   - Topic/section: source registry
   - Relevant contract: official Supabase sources must be tracked alongside the existing stack references

## Decision

- What was implemented: documented a CLI-first Supabase readiness lane, added readiness-only Supabase env settings, committed a minimal `supabase/` scaffold, and kept the Docker Compose/Postgres baseline unchanged.
- Why this matches official source: Supabase's own docs describe the local CLI workflow (`init`, `start`, migration files, `db reset`) and the remote workflow (`login`, `link`, `db push`) as a separate migration/deployment lane, so the repository should stage that path without replacing the current runtime before the transition is ready.

## Code Impact

- Files touched:
  - `docs/operations/supabase-readiness.md`
  - `docs/references/sdd-supabase-readiness-2026-05-09.md`
  - `docs/references/sdd-official-sources-registry.md`
  - `.env.example`
  - `.env.docker`
  - `README.md`
  - `docker-compose.yml`
  - `backend/core/config.py`
- Behavioral impact:
  - Compose remains the runtime baseline
  - Supabase readiness variables are now explicit and validated
  - the repo has a committed Supabase config/migration scaffold for the next schema-first step

## Validation

- Tests/checks executed:
  - reviewed the official Supabase CLI docs and the current repo runtime/config docs
  - updated the settings tests to cover Supabase pool-mode validation
- Result:
  - documentation and config scaffolding prepared successfully

## Notes / Risks

- Open questions:
  - which actual Supabase project ref and DB URL should be used when the transition is approved
  - whether the future cutover should keep the current Docker Compose baseline as a fallback or fully retire it
- Follow-up actions:
  - generate the first real `supabase/migrations/*.sql` file from the current schema when the CLI lane is ready
  - keep historical data backfill as a separate, explicitly approved phase
