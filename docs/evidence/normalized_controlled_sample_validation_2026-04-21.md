# Normalized Controlled Sample Validation (Task 4.2 Follow-up)

Date: 2026-04-21

## Scope

- Execute normalized pipeline against a controlled sample.
- Confirm progress/summary telemetry is emitted for both datasets.
- Record any operational caveats observed during execution.

## Command

```bash
UV_NO_SYNC=1 \
NORMALIZED_DATASET=all \
NORMALIZED_LIMIT_ROWS=2000 \
NORMALIZED_FETCH_SIZE=500 \
NORMALIZED_CHUNK_SIZE=200 \
just pipeline-normalized
```

## Result

- Command completed successfully (exit code 0).
- Runtime summary:
  - Alembic migration check: completed.
  - normalized licitaciones: processed `2,000/2,000`
  - normalized ordenes_compra: processed `2,000/2,000`

Observed summary lines:

- `rejected(header/items/ofertas)=0/0/0`
- `rejected(header/items)=0/0`
- `upserted(...)` counters were reported as `-10` for both datasets.

## Interpretation

- Controlled-sample execution is operationally runnable in the local environment.
- Progress and summary telemetry are present as expected.
- `upserted(...)` values are currently non-authoritative due PostgreSQL `rowcount` behavior on upsert statements; this requires telemetry reconciliation before using these counters for audit-grade reporting.
