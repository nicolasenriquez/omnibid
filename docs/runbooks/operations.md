# Operations Runbook

Pipeline lifecycle:
1. Register source file
2. Start run_id
3. Execute steps
4. Persist row counts + errors
5. Mark final status

Retry rule:
- Retry only with same run metadata and idempotent merge logic.

Fail-fast operational rules:
- Stop ingestion when required dataset columns are missing.
- Stop runtime if `DATABASE_URL` targets a `_test` database.
- Stop integration tests if `TEST_DATABASE_URL` is missing or equals runtime DB.

## Current Telemetry Caveat (as of 2026-04-21)

- `loaded_rows` and derived `rejected_rows` in raw ingest metadata can be inaccurate when PostgreSQL reports `rowcount = -1` for large `INSERT ... ON CONFLICT` statements.
- Normalized summaries can exhibit the same symptom in `upserted(...)` counters.
- Until telemetry reconciliation is implemented, treat these counters as indicative only; do not use them as final audit totals.
- For operational reconciliation, cross-check totals using table counts grouped by `source_file_id` and ingestion batch metadata.

## Normalized Layer Operational Expectations

### Deterministic upsert keys

- `normalized_licitaciones`: `codigo_externo`
- `normalized_licitacion_items`: `codigo_externo + codigo_item`
- `normalized_ofertas`: `oferta_key_sha256`
- `normalized_ordenes_compra`: `codigo_oc`
- `normalized_ordenes_compra_items`: `codigo_oc + id_item`

### Fail-fast key validation

Normalized loader must fail fast when:

- conflict key set is empty
- a conflict key value is missing/empty in payload rows
- configured conflict fields are not present in payload schema

### Transform-level rejection behavior

Rows are rejected (not upserted) when required builder keys are missing:

- licitación header requires `CodigoExterno` + `Codigo`
- licitación item requires `CodigoExterno` + `Codigoitem/CodigoItem`
- oferta requires `CodigoExterno` + supplier identity (`CodigoProveedor` or `RutProveedor`)
- OC header requires `Codigo`
- OC item requires `Codigo` + `IDItem`

### Parsing normalization behavior

- Sentinel dates like `1900-01-01` and `1900-01-01 00:00:00` normalize to null.
- Currency formats like `"$1.234,56"` normalize to decimal.
- Boolean variants include `si/no`, `1/0`, and `verdadero/falso`.
- Text values are preserved as business text; normalization is for comparisons and keys, not for stripping accents from stored content.
- Timestamp-bearing source columns should preserve the time component when present; do not downcast to date-only if the source carries `HH:MM:SS`.
- The reviewed `202601_lic.csv` and `202601-oc.csv` samples expose date-only values in the mapped date fields; if future source drops include time in termination fields, add a dedicated timestamp column in the normalized layer.
- CSV inputs are currently parsed as `latin1` and semicolon-delimited; keep that explicit in ingestion so accent-bearing content round-trips cleanly.

### Expected Normalized execution telemetry

Each dataset execution prints:

- Raw row totals and target rows
- progress checkpoints
- completion summary with `processed`, `rejected`, and `upserted` counters per entity
- Note: upsert counters are currently non-authoritative under the caveat above.
