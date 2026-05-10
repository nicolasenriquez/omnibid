## 1. Contract and Documentation

- [x] 1.1 Record the Supabase readiness lane in a dedicated operations runbook.
  Notes: document the Compose baseline, the local CLI sequence, the remote `login`/`link`/`db push` sequence, and the schema-first guardrails.
  Acceptance: a future agent can read one runbook and understand the transition path without re-deriving it from code.
- [x] 1.2 Update the runtime and architecture docs to link the readiness lane.
  Notes: keep the current Compose path canonical and make the Supabase doc discoverable from the main runtime docs.
  Acceptance: the repo clearly separates the live baseline from the readiness lane.

## 2. Config Surface

- [x] 2.1 Add Supabase readiness env settings.
  Notes: expose `SUPABASE_DB_URL`, `SUPABASE_PROJECT_REF`, and `SUPABASE_DB_POOL_MODE` while preserving `DATABASE_URL` and `TEST_DATABASE_URL`.
  Acceptance: the settings object parses the new contract and fails fast on invalid pool mode values.
- [x] 2.2 Pass the readiness env settings through Docker Compose.
  Notes: backend and tooling containers should carry the new vars without altering the current Compose runtime contract.
  Acceptance: the container env mirrors the documented readiness surface.

## 3. Supabase Scaffold

- [x] 3.1 Commit the `supabase/` local CLI scaffold.
  Notes: add `supabase/config.toml` and a versioned migration placeholder.
  Acceptance: the repo has a committed Supabase directory that can be extended by later migration files.

## 4. Source Registry and SDD

- [x] 4.1 Add the Supabase docs to the official source registry.
  Notes: register the CLI, local-development, config, migration, and connection-string docs used by the readiness lane.
  Acceptance: future agents can start from the repo-local registry instead of rediscovering the same docs.
- [x] 4.2 Record the source-backed decision in an SDD note.
  Notes: capture the rationale for CLI-first readiness and the no-abrupt-replacement boundary.
  Acceptance: the change is traceable in the repo's source-backed documentation trail.

## 5. Validation

- [x] 5.1 Add unit coverage for the new Supabase config contract.
  Notes: verify accepted pool modes and reject invalid values.
  Acceptance: the new config surface is guarded by tests.
- [x] 5.2 Preserve the current Compose baseline docs and validation path.
  Notes: keep `just compose-up` and `just docker-smoke` as the canonical local flow.
  Acceptance: the readiness work does not weaken the existing startup path.
