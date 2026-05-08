## 1. Contract Freeze and Shape

- [x] 1.1 Freeze job queue and ingestion-unit contract.
  Notes: keep the change substrate-only; downstream source-specific processing stays in follow-on proposals.
  Acceptance: state model, lineage fields, and claim rules are explicit and small enough to validate.
- [x] 1.2 Freeze the first-wave non-goals.
  Notes: no Mercado Público API fetch, no raw strict dedupe, no scoped normalization, no Silver refresh.
  Acceptance: proposal, design, and spec all agree on the same boundary.
- [x] 1.3 Freeze queue ordering and retry eligibility.
  Notes: claim order is `priority`, `available_at`, `created_at`, then `id`; retry scheduling must move `available_at` forward deterministically.
  Acceptance: the queue has one deterministic pick order and one bounded retry path.
- [x] 1.4 Freeze the durable checkpoint contract.
  Notes: source bytes must be committed before queue eligibility, and cleanup can only happen after terminal success.
  Acceptance: proposal, design, and spec all agree that a crash cannot lose unprocessed input.

## 2. Tests First

- [x] 2.1 Add unit tests for atomic claim semantics.
  Notes: cover the `queued -> running` transition, one-job/two-worker contention, and skipped locked rows.
  Acceptance: tests fail before the queue exists and pass once claim logic is in place.
- [x] 2.2 Add unit tests for retry state transitions.
  Notes: cover bounded retry, dead-letter, completed transitions, and future `available_at` updates after transient failure.
  Acceptance: the job state machine is deterministic under mocks.
- [x] 2.3 Add persistence tests for ingestion-unit lineage.
  Notes: verify that a claimed job can create a lineage row with the expected source metadata.
  Acceptance: lineage data is stored without guessing or silent fallback.
- [x] 2.4 Add durability tests for the checkpoint lifecycle.
  Notes: cover staged source bytes surviving a worker crash, queue rows still referencing the durable checkpoint, and cleanup only after success.
  Acceptance: tests fail if input can be lost between staging and execution.

## 3. Backend Foundation

- [x] 3.1 Add queue, checkpoint, and ingestion-unit models plus migration.
  Notes: use a compact schema that can support future CSV/API work without baking in the later handlers yet, and make the source checkpoint durable before queue eligibility.
  Acceptance: schema is reversible and aligned with the ORM.
- [x] 3.1a Add checkpoint persistence and recovery wiring first.
  Notes: persist the source artifact and metadata before the queue row is claimable; prove the checkpoint can be reloaded after process restart.
  Acceptance: a crash before claim does not lose the staged input.
- [x] 3.1b Add queue eligibility on top of the durable checkpoint.
  Notes: make the queue row reference the durable checkpoint and keep claim semantics separate from source persistence.
  Acceptance: jobs can only be claimed after the checkpoint exists.
- [x] 3.2 Add the generic worker harness.
  Notes: keep handler dispatch simple, and make claim order explicit in code so workers cannot drift on queue semantics or checkpoint recovery.
  Acceptance: the harness can claim, run, finish, retry, dead-letter jobs, and resume from a durable source checkpoint.
- [x] 3.3 Add the operator entrypoint and just recipe.
  Notes: keep the entrypoint backend-only and Docker-first so the queue can be exercised from the canonical runtime path.
  Acceptance: operators can run the worker flow without touching frontend code.
- [x] 3.4 Add the minimal queue config surface.
  Notes: include a bounded 2-attempt retry budget, 120-second retry delay, dead-letter retention, and poll cadence defaults only; do not add source-specific toggles here.
  Acceptance: runtime settings are explicit and fail fast when malformed.

## 4. Docs and Validation

- [x] 4.1 Add the SDD note and runbook entry.
  Notes: record the queue claim source, claim order, checkpoint retention policy, retry budget, dead-letter replay policy, and the boundary that keeps this slice substrate-only.
  Acceptance: docs explain why `SKIP LOCKED` is the claim primitive and why later waves stay separate.
- [x] 4.2 Run targeted validation.
  Notes: use the smallest backend-first command set that proves the claim path and lineage behavior.
  Acceptance: tests and smoke checks are recorded before the change is considered ready for execution.
- [x] 4.3 Update `CHANGELOG.md`.
  Notes: capture the new substrate in Unreleased once implementation lands.
  Acceptance: delivery history reflects the queue foundation without mixing in later source-specific work.
- [x] 4.4 Freeze the canonical merge policy for API + CSV convergence.
  Notes: define complete-only merge semantics (`no overwrite with null/blank`) and explicit per-column precedence for non-empty conflicts.
  Acceptance: proposal, design, and spec all capture the same merge contract before source-specific implementation starts.
