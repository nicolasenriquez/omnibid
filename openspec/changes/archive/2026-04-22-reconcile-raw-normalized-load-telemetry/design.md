## Context

The current pipeline already delivers raw ingestion and normalized transformation with idempotent conflict handling. However, execution telemetry still interprets `rowcount` as authoritative for inserted/upserted totals, which is unsafe for conflict-heavy statements and some PostgreSQL driver paths. The project roadmap now requires Bronze/Raw reliability hardening before Gold work, so trusted operational metrics are a blocking dependency.

## Goals / Non-Goals

**Goals:**
- Define canonical, deterministic metric formulas for raw and normalized runs.
- Remove dependency on ambiguous `rowcount` for operator-facing counters.
- Keep implementation localized to pipeline scripts and existing operational metadata paths.
- Preserve current data contracts for domain entities.
- Keep telemetry logging bounded and low-overhead for large-volume runs.

**Non-Goals:**
- Redesign the business entity model.
- Build Gold/business outputs.
- Introduce a new observability platform or external telemetry stack.

## Decisions

1. **Use formula-based telemetry as source of truth**
Why: `rowcount` can be non-deterministic for upsert/do-nothing operations. We will compute counters from explicit run inputs and reconciliation queries.
Alternatives considered:
- Keep `rowcount` and document caveat: rejected because it preserves non-auditable behavior.
- Disable conflict handling to force deterministic inserts: rejected because it breaks idempotent semantics.

2. **Track both pipeline-flow and storage-reconciliation metrics**
Why: operators need to distinguish transform acceptance from table growth.
Chosen metrics (per dataset/entity):
- `processed_rows`
- `rejected_rows`
- `accepted_rows`
- `deduplicated_rows` (post-key-dedupe payload count)
- `inserted_delta_rows` (table row-count delta in scoped window)
Alternatives considered:
- Expose only inserted delta: rejected because it hides transform-level quality.

3. **Persist metrics in existing operational structures first**
Why: fastest low-risk path is to reuse `ingestion_batches` and `pipeline_run_steps` fields/details without introducing a broad schema redesign.
Alternatives considered:
- New telemetry tables in this change: deferred to later if needed after operational validation.

4. **Default to checkpoint summaries, not per-row logs**
Why: row-level logging on multi-million-row workloads causes avoidable CPU/IO overhead and noisy operational output.
Chosen approach:
- Emit summary metrics at deterministic checkpoints and completion.
- Keep row-level diagnostics disabled by default.
- Allow optional debug verbosity for short controlled runs only.
Alternatives considered:
- Keep detailed logging always on: rejected due runtime and storage overhead.
- Remove progress logs entirely: rejected because operators still need execution visibility.

## Risks / Trade-offs

- [Risk] Additional reconciliation queries may add runtime overhead on large loads.
  → Mitigation: scope queries by `source_file_id`, run checkpoints at bounded intervals, and reuse existing indexes.

- [Risk] Operators may misinterpret metric categories during transition.
  → Mitigation: update runbooks and evidence templates with explicit definitions and examples.

- [Risk] Inserted delta does not count updates in upsert paths.
  → Mitigation: keep `inserted_delta_rows` explicitly named and pair with `accepted_rows`/`deduplicated_rows` for full interpretation.

- [Risk] Excessive telemetry logs can degrade performance or increase log storage costs.
  → Mitigation: enforce bounded checkpoint logging with configurable interval and debug-gated detailed output.

## Migration Plan

1. Implement deterministic metric computation in raw and normalized scripts behind current command interface (`pipeline-raw`, `pipeline-normalized`).
2. Update logging summaries and operational metadata writes to the new metric taxonomy.
3. Add/adjust tests to lock formulas and rerun behavior.
4. Validate with controlled sample runs and capture evidence.
5. Validate runtime overhead and log volume against baseline.
6. Remove telemetry caveat from operations docs once validation is complete.

Rollback:
- Revert script-level telemetry changes and restore previous summary format if metrics prove unstable under production-like volumes.

## Open Questions

None.
