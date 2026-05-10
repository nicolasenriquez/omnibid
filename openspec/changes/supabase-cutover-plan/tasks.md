## 1. Prepare the Cutover Boundary

- [ ] 1.1 Confirm the readiness lane is complete and referenced from the cutover plan.
  Notes: the cutover change starts only after the CLI smoke, local start smoke, and readiness docs are in place.
  Exit criteria: the repo has a clear link between readiness and cutover, and no one can mistake readiness for production approval.
- [ ] 1.2 Keep the Compose/Postgres baseline marked as canonical.
  Notes: the operational docs and change artifacts must preserve the current runtime until the cutover is approved.
  Exit criteria: the repo still directs day-to-day local work to `just compose-up` and `just docker-smoke`.

## 2. Prove Schema Parity

- [ ] 2.1 Generate the first real Supabase migration baseline from the current schema.
  Notes: this should reflect the Alembic-backed contract, with the live database used only as a validation target.
  Exit criteria: the migration is committed and reviewable.
- [ ] 2.2 Run `supabase db reset` locally against the committed migrations.
  Notes: the reset must prove the schema can be recreated from scratch.
  Exit criteria: a fresh local project reaches the expected schema without manual repair.
- [ ] 2.3 Review the resulting schema against the Alembic-backed contract.
  Notes: resolve drift before any remote link or push; the current database snapshot is a reference for validation, not a competing source of truth.
  Exit criteria: no unresolved schema mismatch remains.
- [ ] 2.4 Run `supabase db push --dry-run` against the linked project.
  Notes: this is the first remote-facing gate, but it must remain non-destructive.
  Exit criteria: the dry run matches the migration history and shows no unexpected changes.

## 3. Execute Controlled Cutover

- [ ] 3.1 Prepare rollback instructions and cutover ownership.
  Notes: the window should be explicit before any production push is scheduled.
  Exit criteria: rollback is documented and an owner is named for the switch.
- [ ] 3.2 Run `supabase login` and `supabase link --project-ref <project-ref>`.
  Notes: only link after local parity is green.
  Exit criteria: the target project is linked and ready for dry-run deployment.
- [ ] 3.3 Run `supabase db push` only after the dry run is reviewed.
  Notes: production push should be a deliberate approval step, not an exploratory command.
  Exit criteria: the remote schema receives the reviewed migration history.
- [ ] 3.4 Switch the application connection contract in a controlled window.
  Notes: keep the previous baseline available until the new path is stable.
  Exit criteria: the app reads the intended production database URL and the baseline remains recoverable.

## 4. Close the Loop

- [ ] 4.1 Update the runbook with any new operational constraints discovered during parity or cutover.
  Notes: the doc trail should reflect the final operational contract.
  Exit criteria: the repo docs match the way the cutover was actually executed.
- [ ] 4.2 Record any remaining backlog items for data backfill or post-cutover cleanup.
  Notes: historical migration stays separate from this change.
  Exit criteria: outstanding follow-up work is captured outside the cutover path.
