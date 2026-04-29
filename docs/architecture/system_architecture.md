# System Architecture

Monorepo with modular backend:
- backend/core: config, settings, logging
- backend/db: engine, session, models
- backend/ingestion: file discovery + registration
- backend/normalized: normalized entities
- backend/models: operational, raw, normalized, and Silver ORM entities
- backend/api: health, operations, opportunities, and investigations endpoints
- backend/observability: structured logging and CLI display helpers
- scripts/: operator entrypoints for raw profiling, raw ingestion, and normalized/Silver builds
- client/: Next.js Opportunity Workspace frontend

## Runtime Boundary

Local runtime is Docker-first:

- `just docker-start` builds the backend image, boots PostgreSQL, runs migrations, and starts the API.
- `just docker-pipeline-full` runs raw profiling/ingestion and normalized/Silver builds inside the backend container.
- `just docker-smoke` checks Compose services and backend health.
- `.env.docker` is the canonical local runtime env file.
- Container-internal PostgreSQL hostnames must be Compose service DNS names (`db`, `db_test`), not `localhost`.
- Dataset access is through the read-only Docker bind mount at `/datasets/mercado-publico`.

Host `uv` commands are optional fallback/developer convenience, not canonical runtime.

## Opportunity Workspace Boundary

The Opportunity Workspace keeps frontend and backend responsibilities explicit:

- frontend route: `/licitaciones`
- backend API route family: `/opportunities`
- frontend package boundary: `client/`
- backend source boundary: `backend/api` routes over Silver-first read contracts with documented Normalized fallback joins where Silver lacks display fields

Implemented read endpoints:

- `GET /opportunities/summary`
- `GET /opportunities`
- `GET /opportunities/{notice_id}`

The frontend must consume typed API contracts and map DTOs into semantic view models before rendering. Components must not depend on raw database column names.

The MVP is read-only. Assignment, discard, notes, AI summaries, scores, workflow edits, reminders, and other mutation workflows remain future scope.

## Procurement Investigation Boundary

The first Gold-facing investigation slice is read-only and evidence-oriented:

- `GET /investigations/procurement-lines`
- `GET /investigations/procurement-lines/{notice_id}/{item_code}`

Investigation responses are derived from Silver procurement-cycle facts. They may expose relationship certainty and bounded handoff context, but they must not persist agent narrative or predictive business truth as canonical data.

## Agent Path Rules

- Add or change API routes in `backend/api/routers/`.
- Add or change schema through Alembic revisions in `alembic/versions/` and keep ORM models in `backend/models/` aligned.
- Add pipeline behavior in `backend/ingestion/`, `backend/normalized/`, or `scripts/` based on existing ownership.
- Add frontend UI/API integration in `client/`.
- Keep proposal/task state under `openspec/changes/<change>/`.
