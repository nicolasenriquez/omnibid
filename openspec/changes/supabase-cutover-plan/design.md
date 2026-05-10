## Design

### Problem

The repo now has a readiness lane for Supabase, but the next operational risk is a partial transition: local parity may succeed while remote deployment, rollback, and runtime switch remain under-defined.

Without a dedicated cutover change, the project risks:

- treating readiness as if it were production approval
- drifting between Alembic, Supabase migrations, and runtime configuration
- migrating historical data before the schema is stable
- losing a clear rollback path

### Approach

Model the transition as three distinct stages:

1. Readiness
2. Schema parity
3. Controlled cutover

The change only governs stages 2 and 3. Stage 1 is already implemented and remains the prerequisite.

### Operating Rules

- Keep Docker Compose/Postgres as the canonical runtime until cutover is approved.
- Treat Alembic as the source of authoring truth for the schema contract.
- Treat the current database as the validation target for parity checks.
- Treat Supabase migrations as the deployed form of the Alembic-backed contract, not a competing source of truth.
- Require local parity before any remote link or push.
- Require a reviewed dry run before any real production push.
- Keep historical backfill out of the cutover path.

### Cutover Sequence

1. Generate or finalize the first real migration baseline from the Alembic-backed schema contract.
2. Run `supabase db reset` locally and confirm the schema reproduces cleanly.
3. Compare the local result against the expected Alembic-backed schema contract and the current database snapshot.
4. Run `supabase db push --dry-run` against the linked project.
5. Review rollback instructions and assign cutover ownership.
6. Execute `supabase db push` only after the dry run and review pass.
7. Switch the application connection contract in a controlled window.

### Rollback

Rollback stays simple by design:

- keep the Compose baseline available until the new lane is stable
- preserve the previous connection contract until the switch is verified
- document the reversal path before the cutover window opens

### Success Criteria

- Local schema parity is reproducible from migrations.
- Remote dry-run deployment matches the local schema history.
- The cutover window has explicit ownership and rollback steps.
- The runtime switch is not attempted until the schema contract is stable.
