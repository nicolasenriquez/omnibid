# Environment Contract Matrix

This runbook defines the canonical environment contract separation for Omnibid.

## Canonical APP_ENV Values

- `development`
- `production`

Legacy aliases are accepted only for transition compatibility:
- `local` -> `development`
- `dev` -> `development`
- `prod` -> `production`

Any other `APP_ENV` value fails fast.

## Source-Of-Truth Matrix

| Runtime lane | Primary env source | Canonical `APP_ENV` | Secrets source |
|---|---|---|---|
| Host local development | `.env` | `development` | local `.env` only |
| Docker local development | `.env` + `.env.docker` via Compose | `development` | local `.env` for secrets; `.env.docker` for nonsecret Docker overrides |
| CI quality/test | workflow env + Compose files | `development` unless job explicitly sets `production` | GitHub Actions secrets/env |
| Production sync/runtime | workflow/deployment env injection | `production` | platform secret manager (GitHub Actions secrets, host secret store, etc.) |

## Docker Baseline Safety

- `.env.docker` keeps `MERCADO_PUBLICO_API_ENABLED=false` by default.
- This prevents accidental upstream API calls during routine local Docker usage.

## Explicit Operator Opt-In

The following `just` recipes inject `MERCADO_PUBLICO_API_ENABLED=true` in the command invocation:

- `mp-api-sync-active`
- `mp-api-sync-rolling`
- `mp-api-sync-detail`
- `mp-api-daily-refresh`

This keeps the sync lanes deterministic and independent from ambiguous template defaults.

The daily pipeline resolves its default target date using the `America/Santiago` date and falls back to the last business day, so weekend runs anchor to Friday instead of querying Sunday by default.

## Production Safety Contract

`APP_ENV=production` rejects unsafe database defaults:

- local hosts (`localhost`, `127.0.0.1`, `::1`)
- default credentials (`postgres:postgres`)

This validation is enforced by config loading and by operator sync scripts.
