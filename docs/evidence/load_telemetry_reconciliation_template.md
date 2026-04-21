# Evidence Template - Load Telemetry Reconciliation

Date: `YYYY-MM-DD`

## Scope

- Verify raw telemetry uses deterministic reconciliation metrics.
- Verify normalized telemetry uses canonical metric taxonomy.
- Confirm runtime and logging volume remain bounded.

## Commands

```bash
# Raw (controlled sample)
DATASET_ROOT="<sample-root>" LIMIT_FILES=2 UV_NO_SYNC=1 just pipeline-raw

# Normalized (controlled sample)
NORMALIZED_DATASET=all \
NORMALIZED_LIMIT_ROWS=<n> \
NORMALIZED_FETCH_SIZE=<n> \
NORMALIZED_CHUNK_SIZE=<n> \
NORMALIZED_STATE_PATH="<state-path>" \
UV_NO_SYNC=1 \
just pipeline-normalized
```

## Raw Reconciliation

- `processed_rows`:
- `accepted_rows`:
- `deduplicated_rows`:
- `inserted_delta_rows`:
- `existing_or_updated_rows`:
- `rejected_rows`:

Operational metadata checks:

- `ingestion_batches.total_rows == processed_rows`
- `ingestion_batches.loaded_rows == inserted_delta_rows`
- `ingestion_batches.rejected_rows == existing_or_updated_rows`
- `pipeline_run_steps.rows_in == processed_rows`
- `pipeline_run_steps.rows_out == inserted_delta_rows`
- `pipeline_run_steps.rows_rejected == existing_or_updated_rows`

## Normalized Reconciliation

Per entity capture:

- `processed_rows`
- `accepted_rows`
- `deduplicated_rows`
- `inserted_delta_rows`
- `existing_or_updated_rows`
- `rejected_rows`

## Logging Efficiency

- Default run emitted checkpoint/summary logs only: `yes/no`
- Row-level logs observed in default mode: `yes/no`
- Debug mode enabled: `yes/no`

## Runtime / Log Volume Comparison

- Raw runtime (baseline vs updated):
- Normalized runtime (baseline vs updated):
- Log-line count (baseline vs updated):
- Material regression observed: `yes/no`

## Result

- Pass/Fail:
- Notes:
