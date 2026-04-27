# Docker Local Runbook

Use this runbook when running `app-chilecompra` with Docker Desktop on Windows/Linux/macOS.

## Scope

- Backend only (`backend` + `db`, optional `db_test` profile).
- No local Python or local PostgreSQL required on the host.
- Dataset mounted read-only into `/datasets/mercado-publico`.

## Prerequisites

- Docker Desktop installed and running.
- Dataset directory available on host (example: `C:/Users/<you>/OneDrive/Documents/dataset-mercado-publico`).

## Initial Setup

1. Review `.env.docker`.
2. Set `DATASET_HOST_PATH` to your local dataset folder.
3. If needed, change `POSTGRES_PASSWORD` and update `DATABASE_URL` / `TEST_DATABASE_URL` accordingly.

## Canonical Commands

1. One-command startup (recommended):
   - `just docker-start`
2. Open docs:
   - `http://localhost:8000/docs`

Low-level equivalent sequence:

1. Build images:
   - `just docker-build`
2. Bootstrap DB + migrations:
   - `just docker-bootstrap`
3. Start backend:
   - `docker compose --env-file .env.docker -f docker-compose.yml up -d backend`

Equivalent direct Compose commands:

- `docker compose --env-file .env.docker -f docker-compose.yml build`
- `docker compose --env-file .env.docker -f docker-compose.yml up -d db`
- `docker compose --env-file .env.docker -f docker-compose.yml run --rm backend uv run --no-sync alembic upgrade head`
- `docker compose --env-file .env.docker -f docker-compose.yml up -d backend`

## Pipeline Commands (Docker)

- Full pipeline:
  - `just docker-pipeline-full`
- Smoke check:
  - `just docker-smoke`

## Security Defaults

- API and PostgreSQL ports publish to `127.0.0.1` only.
- API runs as non-root user in the container.
- API container uses `no-new-privileges`, `read_only` root filesystem, and `tmpfs` for `/tmp`.
- Dataset mount is read-only.
- Compose service DNS names (`db`, `db_test`) are required inside containers; do not use `localhost` there.

## Optional Test Database

Start `db_test` only when needed:

- `docker compose --env-file .env.docker -f docker-compose.yml --profile test up -d db_test`

## Shutdown

- `docker compose --env-file .env.docker -f docker-compose.yml down --remove-orphans`
