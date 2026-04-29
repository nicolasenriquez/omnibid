# Operations Runbook

Pipeline lifecycle:
1. Register source file
2. Start run_id
3. Execute steps
4. Persist row counts + errors
5. Mark final status

Retry rule:
- Retry only with same run metadata and idempotent merge logic.

Hardening roadmap reference:
- `docs/runbooks/data_engineering_hardening_plan.md`

Fail-fast operational rules:
- Stop ingestion when required dataset columns are missing.
- Stop runtime if `DATABASE_URL` targets a `_test` database.
- Stop integration tests if `TEST_DATABASE_URL` is missing or equals runtime DB.

## Operations API Guardrails

List endpoint limits are bounded:

- `GET /runs?limit=<n>` supports `1..200` (default `50`).
- `GET /files?limit=<n>` supports `1..200` (default `100`).

Dataset summary strategy is persisted-snapshot-first for scale:

- `GET /datasets/summary` defaults to `mode=cached` and serves the latest successful persisted snapshot.
- If no snapshot exists yet, default mode performs a one-time bootstrap refresh and persists it.
- `GET /datasets/summary?mode=fresh` forces a recount and persists a new successful snapshot atomically.
- If a fresh refresh fails, the API preserves the last successful snapshot and returns stale/failure metadata instead of partial counts.
- Response includes `summary_meta` with:
  - `strategy=persisted_success_snapshot`
  - `precomputed_summary_storage=enabled`
  - `snapshot_id`, `snapshot_refresh_mode`, `snapshot_age_seconds`, `is_stale`, `refresh_status`

Operator guidance:

- Keep dashboards/pollers on default `mode=cached`.
- Use `mode=fresh` for deliberate operator checks or scheduled maintenance refreshes only.
- Investigate repeated `refresh_status=failed_using_last_successful_snapshot` before relying on `mode=fresh` outcomes.

## Canonical Telemetry Contract (Raw + Normalized)

The pipeline uses the same metric taxonomy across raw and normalized stages:

- `processed_rows`: input records iterated inside the run scope.
- `rejected_rows`: records rejected by contract/transform and not sent to storage.
- `accepted_rows`: `processed_rows - rejected_rows`.
- `deduplicated_rows`: payload rows after business-key dedupe for storage write.
- `inserted_delta_rows`: target-table row-count delta (`count_after - count_before`) in the scoped reconciliation query.

Required invariants:

- `inserted_delta_rows <= deduplicated_rows <= accepted_rows <= processed_rows`
- `existing_or_updated_rows = deduplicated_rows - inserted_delta_rows`
- Any contract failure that prevents deterministic metrics is fail-fast and marks the run as failed.

Raw-stage formulas:

- `processed_rows`: CSV rows read from file.
- `rejected_rows`: `0` for valid files (invalid files fail fast; they are not partially accepted).
- `accepted_rows`: `processed_rows`.
- `deduplicated_rows`: `accepted_rows` (raw ingest has no transform-level key collapse).
- `inserted_delta_rows`: delta count in raw target table scoped by `source_file_id`.

Normalized-stage formulas (per entity):

- `processed_rows`: raw rows scanned for the dataset.
- `rejected_rows`: builder returned `None` for the entity.
- `accepted_rows`: rows that produced entity payloads.
- `deduplicated_rows`: accepted payloads after conflict-key dedupe before upsert.
- `inserted_delta_rows`: row-count delta in target normalized table.

Compatibility mapping (existing operational columns):

- `ingestion_batches.total_rows <- processed_rows`
- `ingestion_batches.loaded_rows <- inserted_delta_rows`
- `ingestion_batches.rejected_rows <- deduplicated_rows - inserted_delta_rows`
- `pipeline_run_steps.rows_in <- processed_rows`
- `pipeline_run_steps.rows_out <- inserted_delta_rows`
- `pipeline_run_steps.rows_rejected <- deduplicated_rows - inserted_delta_rows`

## Telemetry Logging Efficiency Policy

Default mode is bounded and checkpoint-based:

- No row-level/per-record logs.
- Raw progress checkpoints: `max(50_000, chunk_size * 10)`.
- Normalized progress checkpoints: `max(10_000, fetch_size)`.
- Normalized state persistence checkpoints: `max(50_000, fetch_size * 5)`.
- Completion summary includes canonical metrics only.

Debug verbosity is opt-in for controlled runs only. The default operational mode must remain bounded for multi-million-row processing.

## Historical Telemetry Caveat (pre-reconciliation runs)

- Before reconciliation hardening (runs prior to 2026-04-21), `rowcount`-derived counters may be inaccurate (`loaded_rows < 0`, inflated derived rejects, negative `upserted` in normalized logs).
- These caveats apply to historical run evidence only.
- For historical audits, use reconciliation queries from `source_file_id`/table scope instead of trusting legacy `rowcount`-based fields.
- Baseline snapshot of the historical issue: `docs/evidence/load_telemetry_reconciliation_baseline_2026-04-21.md`.

## Normalized Layer Operational Expectations

### Deterministic upsert keys

- `normalized_licitaciones`: `codigo_externo`
- `normalized_licitacion_items`: `codigo_externo + codigo_item`
- `normalized_ofertas`: `oferta_key_sha256`
- `normalized_ordenes_compra`: `codigo_oc`
- `normalized_ordenes_compra_items`: `codigo_oc + id_item`
- `normalized_buyers`: `buyer_key` (`CodigoUnidadCompra`)
- `normalized_suppliers`: `supplier_key` (`codigo:<CodigoProveedor>` else `rut:<RutProveedor>`)
- `normalized_categories`: `category_key` (`codigoCategoria`)

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
- buyer domain row requires `CodigoUnidadCompra`
- supplier domain row requires (`CodigoProveedor` or `RutProveedor`)
- category domain row requires `codigoCategoria`

Domain identity rejections are persisted as `data_quality_issues` with:
- `issue_type=normalized_missing_domain_identity`
- `record_ref` (`buyers` | `suppliers` | `categories`)
- `column_name` set to the missing identity column contract

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
- completion summary with `processed`, `accepted`, `deduplicated`, `inserted_delta`, and `rejected` counters per entity

## Operator Validation Steps

1. Run controlled sample pipelines:
   - `docker compose --env-file .env.docker -f docker-compose.yml run --rm backend uv run --no-sync python scripts/ingest_raw.py --dataset-root /datasets/mercado-publico/dataset-mercado-publico --limit-files 2`
   - `docker compose --env-file .env.docker -f docker-compose.yml run --rm backend uv run --no-sync python scripts/build_normalized.py --dataset all --state-path <state-path>`
2. Validate raw persisted telemetry:
   - `ingestion_batches.total_rows == processed_rows`
   - `ingestion_batches.loaded_rows == inserted_delta_rows`
   - `ingestion_batches.rejected_rows == existing_or_updated_rows`
   - `pipeline_run_steps.rows_in/out/rejected` matches the same mapping.
3. Validate normalized summary telemetry:
   - each entity summary includes `accepted`, `deduplicated`, `inserted_delta`, `existing_or_updated`, `rejected`.
   - confirm `inserted_delta <= deduplicated <= accepted <= processed`.
4. Validate domain replay idempotency:
   - run the same bounded normalized command twice (`--no-resume --no-incremental`) against the same row window.
   - confirm second run has `inserted_delta=0` for `buyers`, `suppliers`, and `categories`.
5. Validate domain rejection persistence:
   - query `data_quality_issues` for `issue_type=normalized_missing_domain_identity`.
   - confirm `column_name` and `record_ref` match the affected domain entity.
6. Validate logging efficiency:
   - default mode emits checkpoints and completion summaries only.
   - no row-level telemetry appears unless debug telemetry is explicitly enabled.
7. Validate operations API guardrails:
   - out-of-range limits on `/runs` and `/files` return validation errors.
   - `/datasets/summary` default mode serves the latest persisted snapshot (`summary_meta.strategy=persisted_success_snapshot`).
   - `/datasets/summary?mode=fresh` returns a new persisted snapshot on success (`summary_meta.refresh_status=refreshed`).
   - if fresh refresh fails, response keeps the last successful snapshot and reports `summary_meta.refresh_status=failed_using_last_successful_snapshot`.

## Post-Domain Expansion Backlog

1. evaluate cross-source buyer identity unification strategy when `CodigoUnidadCompra` is unavailable
2. add operational read endpoints for domain entities and domain-quality issues
3. define Gold-layer contract slices on top of canonical buyers/suppliers/categories

## Procurement Investigation Workspace

The first Gold investigation slice exposes read-only procurement line investigations:

- `GET /investigations/procurement-lines`
- `GET /investigations/procurement-lines/{notice_id}/{item_code}`

Operator guidance:

- Use the list endpoint for bounded workspace/table/board views.
- Use the detail endpoint for one line's summary, offer evidence, purchase evidence, open questions, and context export.
- Treat `purchase_order_line_match_certainty=low` as ambiguous evidence requiring review.
- Do not treat ONU-only line-to-purchase-order-line matches as conclusive.
- Do not persist agent-generated narrative as canonical business data.

Reference:

- `docs/runbooks/procurement_investigation_workspace_plan.md`
- `docs/evidence/procurement_investigation_workspace_join_profile_2026-04-28.md`

## Opportunity Workspace Operations

The Opportunity Workspace exposes read-only opportunity endpoints over Silver-first data:

- `GET /opportunities`
- `GET /opportunities/summary`
- `GET /opportunities/{notice_id}`

Operator guidance:

- Start backend with `just docker-start` (`rtk just docker-start` for agent-issued commands when available).
- Run `just docker-smoke` before frontend browser checks.
- For agents, run backend/API checks through the container-backed `just` path first; use host-local `.venv` or `uv run` only as a fallback with the reason recorded.
- Keep `/opportunities` at notice grain; do not join child rows into the list in a way that duplicates parent notices.
- Use detail endpoint evidence for lines, offers, and purchase orders.
- Keep frontend API base in `client/.env.local` as `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.
- Validate frontend from `client/` with `npm run lint`, `npm run typecheck`, and `npm run build`.

Reference:

- `docs/runbooks/opportunity_workspace_frontend_mvp_plan.md`
- `docs/evidence/opportunity_workspace_frontend_scaffold_validation_2026-04-28.md`
