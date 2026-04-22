## Context

`/datasets/summary` currently relies on runtime full-count queries and process-local cache behavior. This creates avoidable load for frequent operational polling and does not provide durable summary history semantics across process restarts.

The repository already marks precomputed summary persistence as a deferred follow-up requirement in operations API metadata and runbooks. This change closes that gap before moving to broader domain expansion work.

## Goals / Non-Goals

**Goals:**
- Persist durable dataset summary snapshots in operational storage.
- Serve default summary responses from persisted snapshots.
- Keep explicit `mode=fresh` behavior for operator-controlled refreshes.
- Ensure refresh failures do not overwrite last known good snapshot.

**Non-Goals:**
- Introduce Gold/business-layer aggregations.
- Add asynchronous schedulers or external queue infrastructure in this slice.
- Redesign unrelated operations endpoints.

## Decisions

1. **Use operational relational storage for summary snapshots.**
   - Rationale: durable, queryable, migration-controlled state aligned with existing operational tables.
   - Alternatives considered:
   - Keep only in-memory cache: rejected (non-durable, process-bound).
   - Materialized view as first step: rejected for this slice to avoid expanding migration/runtime complexity.

2. **Keep `mode=fresh` as explicit synchronous refresh path.**
   - Rationale: preserves current operator UX while making refresh side effects durable.
   - Alternatives considered:
   - Background-only refresh job: rejected for this slice; adds scheduling/runtime dependencies not required for initial hardening.

3. **Never replace last successful snapshot on failed refresh.**
   - Rationale: fail-safe operational behavior and deterministic fallback during transient faults.
   - Alternatives considered:
   - Overwrite with partial/failed payload: rejected because it propagates transient faults into durable state.

4. **Expose freshness/staleness metadata in responses.**
   - Rationale: operators need explicit visibility into data recency and fallback behavior.

## Risks / Trade-offs

- **[Risk] Snapshot refresh may still execute expensive counts during `mode=fresh`.** → Mitigation: keep fresh mode explicit and document operational usage.
- **[Risk] Schema additions can drift from ORM declarations over time.** → Mitigation: include migration/ORM parity checks in validation tasks.
- **[Risk] Race conditions under concurrent fresh refresh requests.** → Mitigation: use transaction and write semantics that produce one consistent latest successful snapshot.

## Migration Plan

1. Add migration for the operational snapshot table and supporting indexes.
2. Add ORM model metadata for the new table.
3. Implement API read path from persisted snapshot.
4. Implement fresh refresh write path and failure fallback semantics.
5. Validate with unit tests and targeted operational checks.

Rollback strategy:
- Revert to previous runtime-count path by disabling snapshot read/write logic and rolling back the migration if needed.

## Open Questions

- None.
