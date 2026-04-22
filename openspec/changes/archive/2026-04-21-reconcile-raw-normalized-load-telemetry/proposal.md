## Why

Current raw and normalized pipeline counters rely on PostgreSQL/driver `rowcount` behavior for `INSERT ... ON CONFLICT`, which can return non-authoritative values (for example `-1`). This blocks stage-gated reliability goals because operators cannot trust `loaded`, `rejected`, or `upserted` totals as audit evidence.

## What Changes

- Introduce deterministic telemetry reconciliation for raw ingestion and normalized builders using explicit metric formulas instead of driver-reported `rowcount`.
- Standardize per-run metric taxonomy (processed, accepted, deduplicated, inserted-delta, rejected) and emit it consistently in logs and operational metadata.
- Add bounded logging strategy (checkpoint-based summaries, no row-level logging by default, and debug-only deep detail) to keep pipeline execution efficient on large datasets.
- Update operational runbooks and evidence workflow so operators validate reconciliation metrics from canonical sources.
- Add tests covering duplicate-heavy reruns and no-op reruns to prevent telemetry regressions.

## Capabilities

### New Capabilities
- `load-telemetry-reconciliation`: Deterministic and auditable raw/normalized pipeline metrics independent of database driver `rowcount` semantics.

### Modified Capabilities
- None.

## Impact

- Affected areas: `scripts/ingest_raw.py`, `scripts/build_normalized.py`, operational metadata persistence (`ingestion_batches`/`pipeline_run_steps` usage), and associated unit tests.
- Documentation updates: operations/local runbooks and evidence docs for telemetry validation.
- No external API contract break required in this phase.
