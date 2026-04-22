# Load Telemetry Reconciliation Baseline (Tasks 1.2-1.3)

Date: 2026-04-21

## Scope

- Capture a pre-implementation baseline for raw/normalized telemetry drift.
- Quantify where `rowcount`-based counters are non-authoritative.
- Confirm reconciliation query scope and runtime characteristics.

## Baseline Query Method

Executed with local runtime DB using SQLAlchemy session:

- aggregate drift query over `ingestion_batches`
- latest sample rows from `ingestion_batches`
- `pipeline_run_steps` summary for raw-ingest steps
- `EXPLAIN ANALYZE` for reconciliation-count query candidates

## 1) Current Drift Snapshot

Raw ingest aggregate from `ingestion_batches`:

- `total_batches`: `32`
- `batches_loaded_negative`: `32`
- `min_loaded_rows`: `-94`
- `max_loaded_rows`: `-1`
- `sum_total_rows`: `8,554,933`
- `sum_loaded_rows`: `-1,725`
- `sum_rejected_rows`: `8,556,658`

Observation:

- `loaded_rows` is negative in all sampled batches.
- `rejected_rows > total_rows` appears in recent rows, confirming `rowcount` drift propagation.

Recent sample (`ingestion_batches`, last 5 rows):

- `202604-oc.csv`: `total=208,252`, `loaded=-42`, `rejected=208,294`
- `202601-oc.csv`: `total=419,463`, `loaded=-84`, `rejected=419,547`
- `202602-oc.csv`: `total=358,229`, `loaded=-72`, `rejected=358,301`
- `202603-oc.csv`: `total=350,241`, `loaded=-71`, `rejected=350,312`
- `202605-oc.csv`: `total=428,480`, `loaded=-86`, `rejected=428,566`

`pipeline_run_steps` snapshot:

- `step_name=bronze_ingest`, `n=32`, `min_rows_out=-94`, `max_rows_out=-1`, `sum_rows_out=-1725`

## 2) Reconciliation Query Scope and Runtime

Execution-time highlights from `EXPLAIN (ANALYZE)`:

- Scoped raw count (`raw_licitaciones` by `source_file_id`): `~0.77 ms`
- Scoped raw count (`raw_ordenes_compra` by `source_file_id`): `~381.39 ms`
- Full normalized count (`normalized_licitaciones`): `~175.02 ms`
- Full normalized count (`normalized_licitacion_items`): `~986.48 ms`
- Full normalized count (`normalized_ofertas`): `~3651.93 ms`
- Full normalized count (`normalized_ordenes_compra`): `~2931.92 ms`
- Full normalized count (`normalized_ordenes_compra_items`): `~6082.94 ms`

Interpretation:

- Raw reconciliation queries should be scoped by `source_file_id` and remain low overhead.
- Normalized full-table reconciliation is materially more expensive and must be checkpoint-bounded (not per chunk/row).
- This baseline supports a checkpoint-summary telemetry strategy instead of verbose logging.

## 3) Baseline Logging Volume (Pre-change)

Current scripts already avoid row-level logs by default and emit:

- stage start lines
- bounded progress/checkpoint lines
- one completion summary per dataset/file

Operational requirement for the change:

- keep default bounded logging behavior
- preserve completion summaries with canonical metrics
- make additional detail opt-in only (debug mode)
