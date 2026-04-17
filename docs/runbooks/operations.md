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

## Silver Hardening Operational Expectations

### Deterministic upsert keys

- `silver_licitaciones`: `codigo_externo`
- `silver_licitacion_items`: `codigo_externo + codigo_item`
- `silver_ofertas`: `oferta_key_sha256`
- `silver_ordenes_compra`: `codigo_oc`
- `silver_ordenes_compra_items`: `codigo_oc + id_item`

### Fail-fast key validation

Silver loader must fail fast when:

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

### Expected Silver execution telemetry

Each dataset execution prints:

- Bronze row totals and target rows
- progress checkpoints
- completion summary with `processed`, `rejected`, and `upserted` counters per entity
