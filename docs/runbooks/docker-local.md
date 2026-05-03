# Docker Local Runbook

Use this runbook when running `app-chilecompra` with Docker Desktop on Windows/Linux/macOS.

## Scope

- Backend runtime (`backend` + `db`, optional `db_test` profile).
- Frontend runs in the `client` container service and talks to the Docker backend.
- Quality and test commands use the Docker tooling stage; host-local commands remain fallback only.
- No local Python or local PostgreSQL required on the host.
- Dataset mounted read-only into `/datasets/mercado-publico`.

For agents, this runbook is the first execution plan for backend, database, migration, pipeline, smoke, and quality work. Host-local `.venv` or `uv run` commands are fallback paths only when Docker/Compose is unavailable, blocked, or not relevant to the task.

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

When issuing commands as an agent and `rtk` is available, prefix workflow commands:

- `rtk just docker-start`
- `rtk just docker-pipeline-full`
- `rtk just docker-smoke`

If a container-backed command cannot be used, state the reason before using the closest host-local fallback. Do not promote the fallback command to the canonical workflow.

## Frontend Pairing

Run the frontend through the Docker stack after the backend is healthy:

```bash
just dev
```

Open:

- `http://127.0.0.1:3000/licitaciones`

If you need a host-local fallback from `client/`, use the commands in `client/README.md`.

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
