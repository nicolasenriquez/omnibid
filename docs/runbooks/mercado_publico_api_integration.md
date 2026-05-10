# Mercado Publico API Integration Runbook

This runbook describes how to operate:

- the notice-only Mercado Publico API sync lane
- the daily notice canonicalization lane (rolling sync + Silver notice refresh)

## Scope

- Backend-only.
- Operator-driven execution.
- Notice sync and notice-level Silver refresh only.
- No CSV historical backfill replacement and no line/bid/award/order synthesis in this lane.

## Runtime Preconditions

- Docker daemon available.
- Local stack uses `docker-compose.yml` + both `.env` and `.env.docker`.
- `.env` carries the local Mercado Publico API ticket.
- `.env.docker` carries Docker-specific nonsecret overrides.
- API sync enabled and key configured:
  - `MERCADO_PUBLICO_API_ENABLED=true`
  - `MERCADO_PUBLICO_API_KEY=<ticket>`

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

## Daily Canonical Notice Lane

Purpose:

- Run the daily rolling-window sync and refresh canonical `silver_notice` rows in one operator command.
- Preserve API lineage even if Silver refresh fails.

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
  - `mp_api_notice_silver_refresh`

Daily runs also register a logical API snapshot `source_files` artifact (`dataset_type=mercado_publico_api_notice`) so `source_file_id` lineage is preserved for downstream canonical Silver rows.

## Security Notes

- `ticket` is excluded from canonical request hash inputs.
- safe URLs/logging paths redact sensitive query parameters.
- this lane remains bounded to notice sync + notice Silver refresh; it does not replace CSV/manual ingestion flows.
