# Incremental Ingestion Queue Runbook

This runbook describes the operational state flow for the incremental ingestion substrate.

## Claim Primitive

- Queue claims use `SELECT ... FOR UPDATE SKIP LOCKED` in one transaction.
- Deterministic order is fixed: `priority`, `available_at`, `created_at`, `id`.
- This runbook covers substrate behavior only; source-specific API fetch, raw strict dedupe, scoped normalization, and Silver refresh remain follow-on waves.

## Policy Summary

- Retry budget: 2 total attempts per job, meaning 1 retry after the first claim.
- Retry delay: 120 seconds for the retryable path.
- Contract phrasing: one transient retry, then `dead_letter`; non-retryable failures go to `dead_letter` immediately.
- Dead letters: terminal, visible, and not auto-replayed.
- Replay of dead letters: explicit operator action only.

## State Flow

```text
checkpoint persisted
  -> queued
  -> running
  -> completed

checkpoint persisted
  -> queued
  -> running
  -> retry_scheduled
  -> queued
  -> running
  -> completed

checkpoint persisted
  -> queued
  -> running
  -> retry_scheduled
  -> queued
  -> running
  -> dead_letter

dead_letter
  -> requeued by operator
  -> queued
```

## Who Does What

### Source intake process

- Persists the durable checkpoint before the queue row becomes eligible.
- Writes the source artifact and metadata needed for replay and audit.
- Never deletes the checkpoint until terminal success and retention policy allow cleanup.

### Worker process

- Claims only `queued` jobs that are already eligible.
- Marks jobs `running` inside the claim transaction.
- On transient failure, moves the job to `retry_scheduled` and advances `available_at`.
- On terminal failure after the retry budget is exhausted, moves the job to `dead_letter`.
- On success, marks the job `completed` and leaves lineage for audit.

### Operator

- Reviews `dead_letter` rows as the queue runs.
- Requeues a dead letter only through an explicit maintenance action.
- Does not rely on queue exhaustion as a signal to replay dead letters.

## Operational Rules

1. The queue must not invent work.
2. The queue must not auto-replay dead letters when no queued jobs remain.
3. The checkpoint must remain durable across crashes.
4. The worker must keep the claim order deterministic.
5. Replay actions must be auditable and attributable to an operator or maintenance flow.
6. Canonical merge uses complete-only updates: null/blank incoming values never erase existing non-empty values.

## Audit Fields To Check

- `pipeline_jobs.status`
- `pipeline_jobs.attempts`
- `pipeline_jobs.available_at`
- `pipeline_jobs.locked_at`
- `pipeline_jobs.locked_by`
- `pipeline_jobs.started_at`
- `pipeline_jobs.finished_at`
- `pipeline_jobs.failed_at`
- `pipeline_jobs.error_message`
- `ingestion_units.job_id`
- `ingestion_units.source_kind`
- `ingestion_units.dataset_type`
- `source_checkpoints.status`
- `source_checkpoints.storage_uri`
- `source_checkpoints.payload_hash_sha256`
- `source_checkpoints.consumed_at`

## When To Requeue A Dead Letter

Only requeue a dead letter if:

- the root cause has been fixed or understood
- the source checkpoint is still present or can be restored
- the operator wants the job to be attempted again
- the replay is recorded as a manual maintenance action

Do not requeue dead letters just because the queue is empty.
