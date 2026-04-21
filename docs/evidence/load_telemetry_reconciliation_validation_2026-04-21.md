# Load Telemetry Reconciliation Validation (Tasks 4.3-4.4)

Date: 2026-04-21

## Scope

- Execute controlled `pipeline-raw` and `pipeline-normalized` runs after telemetry reconciliation changes.
- Validate persisted raw metrics and normalized summary metrics against the canonical contract.
- Compare runtime and log volume against baseline expectations from the pre-change evidence.

## Controlled Sample Setup

Sample root:

- `/Users/NicolasEnriquez/Desktop/App ChileCompra/app-chilecompra/data/samples/telemetry_reconciliation_20260421`

Files:

- `licitacion/202601_lic_sample.csv` (`1,014` data rows)
- `orden-compra/202601_oc_sample.csv` (`292` data rows)

## Commands

```bash
UV_NO_SYNC=1 \
DATASET_ROOT="/Users/NicolasEnriquez/Desktop/App ChileCompra/app-chilecompra/data/samples/telemetry_reconciliation_20260421" \
LIMIT_FILES=2 \
CHUNK_SIZE=500 \
just pipeline-raw
```

```bash
UV_NO_SYNC=1 \
NORMALIZED_DATASET=all \
NORMALIZED_FETCH_SIZE=500 \
NORMALIZED_CHUNK_SIZE=200 \
NORMALIZED_STATE_PATH="data/runtime/telemetry_reconciliation/normalized_state_seed.json" \
just pipeline-normalized
```

## Raw Reconciliation Results

Raw ingest log summaries:

- `202601_lic_sample.csv`: `processed=1,014 accepted=1,014 deduplicated=1,014 inserted_delta=1,014 existing_or_updated=0`
- `202601_oc_sample.csv`: `processed=292 accepted=292 deduplicated=292 inserted_delta=292 existing_or_updated=0`

Persisted metadata validation:

- `ingestion_batches`:
  - lic sample: `total_rows=1014`, `loaded_rows=1014`, `rejected_rows=0`
  - oc sample: `total_rows=292`, `loaded_rows=292`, `rejected_rows=0`
- `pipeline_run_steps`:
  - lic sample: `rows_in=1014`, `rows_out=1014`, `rows_rejected=0`
  - oc sample: `rows_in=292`, `rows_out=292`, `rows_rejected=0`
- `source_files.source_meta.raw_ingest_metrics` and `pipeline_runs.config.raw_ingest_metrics` match the canonical metric set.

Result:

- Raw telemetry is deterministic and auditable for this controlled run.
- No negative counters observed in new run records.

## Normalized Reconciliation Results

Licitaciones dataset summary:

- `processed=1,014`
- header: `accepted=1,014 deduplicated=78 inserted_delta=0 existing_or_updated=78 rejected=0`
- items: `accepted=1,014 deduplicated=262 inserted_delta=0 existing_or_updated=262 rejected=0`
- ofertas: `accepted=1,014 deduplicated=1,014 inserted_delta=0 existing_or_updated=1,014 rejected=0`

Ordenes de compra dataset summary:

- `processed=292`
- header: `accepted=292 deduplicated=95 inserted_delta=0 existing_or_updated=95 rejected=0`
- items: `accepted=292 deduplicated=292 inserted_delta=0 existing_or_updated=292 rejected=0`

Interpretation:

- Canonical metric taxonomy is emitted in normalized completion summaries.
- `inserted_delta=0` is correctly differentiated from accepted/deduplicated flow counts for idempotent updates/no-growth scenarios.

## Runtime and Log-Volume Comparison

Baseline references:

- Pre-change drift/performance baseline: `docs/evidence/load_telemetry_reconciliation_baseline_2026-04-21.md`
- Prior normalized controlled-sample caveat: `docs/evidence/normalized_controlled_sample_validation_2026-04-21.md`

Updated run metrics:

- Raw pipeline (profile + ingest on controlled sample): raw ingest stage `13.1s` (`15.4s` command wall time).
- Normalized pipeline (incremental controlled sample): licitaciones `15.2s`, ordenes_compra `28.3s` (`75.0s` command wall time including migration + both datasets).
- Log lines:
  - `pipeline_raw_20260421.log`: `15` lines
  - `pipeline_normalized_20260421.log`: `14` lines

Efficiency conclusion:

- Logging remains bounded (checkpoint + summary only, no row-level emission in default mode).
- Runtime behavior is consistent with baseline expectation that reconciliation queries are bounded and not per-row.
- No material efficiency regression observed in this controlled validation.
