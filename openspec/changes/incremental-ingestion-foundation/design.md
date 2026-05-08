## Problem

Omnibid has enough pipeline depth now that future work needs a reusable incremental substrate.

Without a shared job queue and ingestion-unit ledger, each new source or batch shape risks inventing its own claim rules, retry rules, and lineage model. That would make the next API lane or CSV increment feel like a one-off repair instead of a stable platform contract.

## Design Goals

1. Keep the first slice substrate-only.
2. Make job claim semantics atomic and auditable.
3. Keep lineage explicit from job to ingestion unit.
4. Avoid Redis, Celery, or broader orchestration until the base contract proves itself.
5. Preserve Docker-first validation and fail-fast behavior.

## Proposed Architecture

```text
source event
  -> durable checkpoint
  -> pipeline_jobs
  -> atomic claim with FOR UPDATE SKIP LOCKED
  -> worker harness
  -> ingestion_unit ledger
  -> downstream source-specific handler
```

The first change stops at the shared substrate:

- source bytes are committed before queue eligibility
- queue rows exist
- jobs can be claimed safely
- retries are explicit
- ingestion units carry lineage
- downstream source-specific handlers remain future work

### Component Boundaries

- `backend/models/ingestion_jobs.py`
  - ORM for job rows and ingestion-unit rows.
- `backend/models/operational.py`
  - durable source checkpoint rows and file metadata.
- `backend/ingestion/queue.py`
  - claim, release, retry, and dead-letter helpers.
- `backend/pipeline/worker.py`
  - generic worker loop and handler dispatch.
- `backend/pipeline/ingestion_units.py`
  - ingestion-unit creation and lineage helpers.
- `backend/core/config.py`
  - queue defaults, retry budgets, and worker poll cadence.
- `scripts/run_ingestion_jobs.py`
  - operator entrypoint for queue-driven work.
- `alembic/versions/`
  - schema migration for queue and ledger tables.
- `tests/unit/`
  - claim and retry behavior.
- `tests/integration/`
  - database-backed queue semantics.

## Queue Contract

Suggested job states:

- `queued`
- `running`
- `completed`
- `failed`
- `retry_scheduled`
- `dead_letter`
- `cancelled`

Queue claim policy:

- use one transaction to select the next eligible job
- only consider rows with `status = queued`
- only consider rows with `available_at <= now()`
- order candidates by `priority ASC, available_at ASC, created_at ASC, id ASC`
- lock candidate rows with `FOR UPDATE SKIP LOCKED`
- update the claimed row in the same transaction
- keep table locks out of the hot path

Retry eligibility:

- increment `attempts` on each claim
- if the worker signals a transient failure, move the row to `retry_scheduled`
- set `available_at = failure_at + (retry_delay_seconds * attempts)` so retries are deterministic
- use a default `retry_delay_seconds` of 120 for the first retry
- keep the default retry budget bounded at 2 total attempts
- one transient retry is the base contract; non-retryable failures move to `dead_letter` immediately
- if `attempts >= max_attempts`, move the row to `dead_letter`
- do not auto-requeue dead letters when the queue becomes empty
- replay dead letters only through an explicit operator or maintenance action

Advisory locks are not required for the basic claim path. If a later slice needs a coarse mutual exclusion rule, that should be a separate decision.

## Ingestion Unit Contract

The ingestion-unit ledger should capture:

- `job_id`
- `source_kind`
- `dataset_type`
- `source_file_id` or future source reference
- `api_call_id` or future source reference
- `status`
- `metadata`

The ledger exists to keep the downstream work auditable. It should not be used as a hidden place to smuggle raw dedupe or normalization scope into this slice.

## Canonical Merge Contract (Defined Here, Implemented Next Wave)

When two sources contribute to the same business key, canonical updates use complete-only merge semantics:

- incoming `NULL`/blank values do not erase existing canonical values
- incoming materially present values can update canonical values
- normalization must evaluate empty vs present after trimming/coercion by type
- additive fields are updated by explicit recomputation rules, not generic overwrite
- source precedence for non-empty conflicts must be explicit per column:
  - identifiers: immutable once assigned
  - descriptive fields: CSV preferred
  - lifecycle fields: API preferred
  - numeric rollups: newer event timestamp wins; CSV breaks ties

This keeps the queue substrate independent while preventing ambiguity in the API + CSV convergence path.

Implementation target for follow-on wave:

- apply per-column merge expressions in normalized upsert paths
- use type-aware "present value" checks before update assignment
- keep audit provenance (`source_kind`, ingestion timestamp, job id) for field-level diagnostics

## Durable Checkpoint Contract

The checkpoint is the durable source artifact that exists before a queue job can be run.

- A source file, staged upload, or API snapshot must be persisted before queue eligibility.
- The queue job should reference the checkpoint by durable identifier, not by in-memory payload.
- If a worker crashes after the checkpoint is created but before the job completes, the checkpoint remains available for replay.
- Staged bytes should not be deleted until the job reaches a terminal success state and the retention policy explicitly allows cleanup.
- Metadata should remain even when the bytes are later cleaned up, so the lineage trail stays auditable.

For this slice, the checkpoint can be modeled with the existing `source_files` / staged-file path pattern rather than a separate temporary broker. That keeps the recovery contract close to the data and avoids inventing a second queue.

### Ordering and Fairness

- `priority` is the primary control for work ordering.
- `available_at` gates when a job becomes eligible.
- `created_at` provides FIFO behavior inside the same priority and availability window.
- `id` is the stable final tie-breaker so claim order is deterministic.

## Alternatives Considered

1. Redis queue.
   - Rejected for this slice because Postgres already owns the operational source of truth and the queue needs to stay close to the data.
2. Celery now.
   - Rejected because it adds broader runtime surface before the base ingestion contract is proven.
3. Table locks for claim.
   - Rejected because they are too coarse for a queue-like table.
4. Listen/Notify first.
   - Rejected as the primary mechanism because the queue can start with polling and row locks.

## Risks

- If the queue contract drifts, later source-specific changes will fork the lineage model.
- If the worker harness is too generic, it can become a second orchestration layer with no clear owner.
- If retries are not bounded, failed jobs can churn forever.
- If later raw or API work gets folded into this slice, the change becomes too large and loses its foundation purpose.
- If the claim order is not fixed now, future workers can disagree on which eligible job should run next.
- If the checkpoint is only ephemeral, a crash can orphan unprocessed source bytes and the queue becomes non-recoverable.

## Mitigations

- keep the job state machine explicit and test it first
- keep the worker harness generic but small
- keep retry budgets configurable and bounded
- keep source-specific processing out of this change
- split raw dedupe, normalization scope, and API ingestion into follow-on proposals
- keep `priority`, `available_at`, `created_at`, and `id` as the only queue ordering inputs
- persist source bytes before queue eligibility and keep metadata even after cleanup

## Validation Plan

- unit tests for atomic claim behavior
- unit tests for retry and dead-letter transitions
- integration tests for one job claimed by one worker only
- integration tests for lineage persistence from job to ingestion unit
- Docker-first smoke checks if any runtime entrypoint changes land in the slice
