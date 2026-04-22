## 1. Persistence Foundation

- [x] 1.1 Add operational persistence model for dataset summary snapshots with required metadata fields.
- [x] 1.2 Add Alembic migration for the snapshot table and indexes aligned with query patterns.
- [x] 1.3 Add schema parity checks to ensure ORM and migration metadata stay aligned.

## 2. Summary Read/Refresh Behavior

- [x] 2.1 Refactor `/datasets/summary` default path to read from latest successful persisted snapshot.
- [x] 2.2 Implement `mode=fresh` recomputation flow that persists a new snapshot atomically.
- [x] 2.3 Enforce fail-safe behavior so failed refresh attempts preserve the last successful snapshot.

## 3. API Metadata and Guardrails

- [x] 3.1 Expose snapshot freshness/staleness metadata in response payloads.
- [x] 3.2 Preserve bounded query parameters and avoid reintroducing expensive default full counts.
- [x] 3.3 Ensure transient refresh failures are surfaced without caching partial/failed snapshot payloads.

## 4. Tests and Verification

- [x] 4.1 Add unit tests for snapshot read path and fresh refresh success path.
- [x] 4.2 Add failure-path tests covering refresh exceptions and stale snapshot fallback behavior.
- [x] 4.3 Add migration/model parity validation checks in quality workflow for affected persistence artifacts.

## 5. Documentation and Evidence

- [x] 5.1 Update operations runbook with snapshot refresh semantics and operator guidance.
- [x] 5.2 Update local development runbook with validation steps for persisted summaries.
- [x] 5.3 Capture validation evidence for normal and failure refresh scenarios before merge.
