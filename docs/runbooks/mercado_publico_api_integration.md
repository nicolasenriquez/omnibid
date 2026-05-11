# Mercado Publico API Integration Runbook

This runbook describes how to operate:

- the Mercado Publico API sync lane (active/rolling/detail)
- the daily read-model propagation lane (rolling sync + selective detail + canonicalization + Silver postprocess)

## Scope

- Backend-only.
- Operator-driven execution.
- API request/payload/snapshot persistence.
- API payload canonicalization into existing Normalized + Silver canonical tables.
- No frontend contract mutations in this lane.

## Runtime Preconditions

- Docker daemon available.
- Local stack uses `docker-compose.yml` + both `.env` and `.env.docker`.
- `.env` can carry a local Mercado Publico API ticket when running sync commands locally.
- `.env.docker` is safe-by-default and keeps `MERCADO_PUBLICO_API_ENABLED=false`.
- Sync commands opt in explicitly at runtime with `MERCADO_PUBLICO_API_ENABLED=true`.
- API key is still required when sync is enabled:
  - `MERCADO_PUBLICO_API_KEY=<ticket>`

See [`environment-contract.md`](environment-contract.md) for the full host/Docker/CI/production authority matrix.

## Sync-Only Modes (Troubleshooting and Replay)

### 1) Active discovery

Purpose:
- Fetch current active notices.

Command:

```bash
just mp-api-sync-active
```

### 2) Rolling window

Purpose:
- Refresh notices for a bounded date window (`T..T-3` by default).

Command:

```bash
just mp-api-sync-rolling --target-date YYYY-MM-DD --window-days 4
```

Optional:
- `--estado <value>`
- `--requested-by <label>`
- `--max-requests <n>`
- `--start-date YYYY-MM-DD --end-date YYYY-MM-DD` (explicit range; derives `window-days`)

### 3) Detail by code

Purpose:
- Enrich selected notice candidates by official notice code.

Command:

```bash
just mp-api-sync-detail --codigo <code1> --codigo <code2>
```

Optional:
- `--requested-by <label>`
- `--max-requests <n>`

## Daily Read-Model Propagation Lane

Purpose:

- Run one staged daily DAG in a single operator command:
  - rolling-window discovery sync
  - selective `detail-by-codigo` enrichment
  - canonicalization bridge into existing Normalized + Silver tables
  - Silver postprocess refresh
- Preserve API lineage end-to-end even when downstream canonicalization fails.

Command:

```bash
just mp-api-daily-refresh --target-date YYYY-MM-DD --window-days 4
```

Optional:

- `--estado <value>`
- `--requested-by <label>`
- `--max-requests <n>`

Replay without upstream API calls:

```bash
just mp-api-daily-refresh --target-date YYYY-MM-DD --window-days 4 --refresh-only
```

`--refresh-only` reuses persisted snapshots for the target window and skips upstream sync intentionally.

If `--target-date` is omitted, the daily pipeline uses the current `America/Santiago` date on weekdays and the previous Friday on weekends.

Implementation note:
- `just mp-api-daily-refresh` sets `MERCADO_PUBLICO_API_ENABLED=true` inline in the Compose run command.
- This prevents accidental dependence on `.env.docker` defaults.

## Smoke Check

Validate config and command wiring without external API writes:

```bash
just mp-api-smoke
```

Expected signal:
- `dry-run ok`
- the printed plan includes resolved mode/window plus `requested_by` and `max_requests`.

## Persistent Budget and Lock Strategy

Request-budget enforcement is persistent and restart-safe:

- budget reservations are written to `api_source_request` before upstream API calls.
- daily limits are enforced by `source_system + rate_limit_day` and canonical request hash.
- repeated same-day canonical requests reuse the reserved ledger identity instead of charging again.

Scoped lock behavior is per logical work unit (not global):

- `active-discovery`: lock key by mode + UTC day.
- `rolling-window`: lock key by mode + date + window + `estado`.
- `detail-by-codigo`: lock key by mode + external notice code.

Operational intent:

- prevent concurrent duplicate execution on the same work unit.
- allow independent work units to run in parallel.

## Fail-Fast Behavior

Execution stops with clear errors when:

- API lane is disabled but run requested.
- API key is missing while enabled.
- timeout/retry/daily-limit config values are invalid.
- `APP_ENV=production` uses unsafe database defaults (`localhost`/`127.0.0.1`/`::1` host or `postgres:postgres` credentials).
- response contract parsing fails.
- retry budget is exhausted on transient upstream failures.
- the daily request budget reaches its configured limit.

## Operational Lineage

Sync-only executions write operational run tracking:

- `PipelineRun.dataset_type=mercado_publico_api_notice`
- step names:
  - `mp_api_discovery_active`
  - `mp_api_rolling_refresh`
  - `mp_api_detail_enrichment`

Daily executions write one parent run with ordered steps:

- `PipelineRun.dataset_type=mercado_publico_api_notice`
- step names:
  - `mp_api_rolling_refresh`
  - `mp_api_detail_enrichment`
  - `mp_api_payload_canonicalization`
  - `mp_api_silver_postprocess`

Daily runs also register a logical API snapshot `source_files` artifact (`dataset_type=mercado_publico_api_notice`) so `source_file_id` lineage is preserved for downstream canonical Normalized + Silver rows.

## Security Notes

- `ticket` is excluded from canonical request hash inputs.
- safe URLs/logging paths redact sensitive query parameters.
- this lane remains bounded to API-source read-model propagation; it does not replace CSV/manual ingestion flows.
- GitHub Actions scheduled/manual sync runs with `APP_ENV=production`, `DATABASE_URL` from `MP_API_DATABASE_URL`, and `MERCADO_PUBLICO_API_KEY` from repository secrets.
