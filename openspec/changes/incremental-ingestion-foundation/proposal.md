## Why

Omnibid needs a shared incremental ingestion substrate before it can safely grow beyond one-off pipeline slices.

The current Mercado Público notice change is intentionally narrow: it is notice-only, backend-only, and keeps the CSV pipeline unchanged. That is the right boundary for that slice, but it does not solve the broader problem of how future CSV loads, manual file loads, and API-driven jobs should be queued, claimed, retried, and audited.

This proposal creates that shared base. It keeps the first change small enough to plan and validate, while leaving raw dedupe, scoped normalization, Mercado Público API fetches, and Silver refresh logic for follow-on changes.

## What Changes

- Add a Postgres-backed ingestion job queue with atomic claim, deterministic ordering, and retry state.
- Add an ingestion-unit ledger that records source lineage and links work to a job.
- Add a durable intake checkpoint so source bytes and metadata are committed before a job becomes eligible for execution.
- Add a minimal worker harness and operator entrypoint for claiming and finishing jobs.
- Add a minimal config surface for queue defaults and worker polling behavior.
- Add tests for claim semantics, retry state, and lineage persistence.
- Keep the existing CSV pipeline and the current Mercado Público notice-only change untouched.

## Capabilities

### New Capabilities

- `ingestion-job-queue`
- `ingestion-unit-ledger`
- `ingestion-worker-harness`
- `ingestion-ops-runbook`

### Modified Capabilities

- None.

## Impact

- `backend/models/ingestion_jobs.py`
- `backend/ingestion/queue.py`
- `backend/models/operational.py`
- `backend/pipeline/worker.py`
- `backend/pipeline/ingestion_units.py`
- `backend/core/config.py`
- `scripts/run_ingestion_jobs.py`
- `alembic/versions/`
- `tests/unit/`
- `tests/integration/`
- `justfile`
- `docs/references/`
- `docs/runbooks/`
- `docs/architecture/`
- `CHANGELOG.md`

Not impacted in this slice:

- `client/`
- `backend/api/routers/`
- the existing CSV ingest and normalize contracts
- the Mercado Público API notice-only lane

## Goals

- Create one reusable ingestion substrate for future queue-driven work.
- Keep job claim semantics explicit and auditable.
- Keep claim ordering deterministic and stable under contention.
- Keep retry scheduling deterministic from failure timestamp, attempt number, and configured delay.
- Keep source lineage attached to the job that created the work.
- Keep source bytes durable before queue execution so a worker crash cannot lose unprocessed input.
- Keep the first slice small enough to validate without broad pipeline rewrites.

## Retry and Dead-Letter Policy

- Default retry budget: 2 total attempts per job, meaning 1 retry after the first claim.
- Default retry delay: 120 seconds, applied deterministically from the failure timestamp and attempt count.
- Retry growth: linear backoff is enough for this slice; there is only one retry interval in the base contract.
- Contract phrasing: one transient retry, then `dead_letter`; non-retryable failures go to `dead_letter` immediately.
- Dead letters are terminal and operator-visible.
- Dead letters are not auto-replayed when the queue empties.
- Any replay must be an explicit operator action or a separate maintenance flow.

## Field Merge Policy (Next Wave Contract)

This contract applies when the same business key arrives from API and later from CSV with additional fields.

- Merge mode: complete-only updates.
- Rule 1: do not overwrite an existing non-empty canonical value with `NULL`, empty string, or whitespace-only text.
- Rule 2: overwrite is allowed when the incoming value is materially present.
- Rule 3: for text values, normalize trim before deciding empty vs present.
- Rule 4: for numeric/date/boolean values, `NULL` means "no new information" and must not erase an existing value.
- Rule 5: for additive or multiplicity fields (for example item counts), update only from an authoritative recomputation path, not from blind overwrite.
- Rule 6: preserve `updated_at` and provenance fields so operators can see which source completed each column.
- Precedence baseline by column family:
  - identifiers and business keys: first non-empty wins, immutable after first canonical assignment
  - descriptive master fields (names, descriptions, optional attributes): `manual_csv`/`bulk_csv` preferred over API when both are non-empty
  - operational lifecycle fields (status, publication dates, closing dates): API preferred over CSV when both are non-empty
  - monetary rollups and counts: newest event timestamp wins; if timestamps tie, CSV preferred
  - link fields between entities (for example OC -> licitacion): keep existing non-empty link unless incoming source provides a non-empty conflicting link with newer event timestamp

This proposal freezes the policy and keeps implementation in the next source-specific normalization wave.

## Implementation Waves

These are target dates for the foundation slice, not hard release commitments.

- Wave 0, 2026-05-07 to 2026-05-08: capture the durable checkpoint contract in spec, design, and tasks.
- Wave 1A, 2026-05-08: persist the checkpoint before enqueueing and prove the source artifact survives a crash before any queue claim exists.
- Wave 1B, 2026-05-09: add queue eligibility and claim logic that references the durable checkpoint.
- Wave 2, 2026-05-10: prove crash recovery, retry, and consumption semantics with tests and worker flow.

Recommended implementation order:

1. Durable checkpoint persistence.
2. Queue claim against durable checkpoint.
3. Worker harness and retry transitions.
4. Consumption cleanup and audit retention.

## Non-Goals

- No Mercado Público API fetch implementation.
- No raw strict deduplication contract change.
- No scoped normalized rebuild logic.
- No Silver refresh logic.
- No frontend work.
- No LISTEN/NOTIFY orchestration.
- No advisory-lock coordination in the hot claim path.
- No ephemeral-only intake path that can lose source bytes before the job is complete.

## Open Questions

None.
