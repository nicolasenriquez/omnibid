# Local Development Runbook

Canonical runtime is Docker-first. Use [`docker-local.md`](docker-local.md) as the primary runbook.

Agents should treat the container path as the first execution plan for backend, database, migration, pipeline, and quality work. Use host-local `.venv`, `uv run`, or direct Python commands only as fallback validation when Docker/Compose is unavailable, sandbox-blocked, or irrelevant to a frontend-only task. Record the fallback reason when using host-local execution.

## Quick Start

1. `cp .env.example .env`
2. Review `.env.docker` dataset mount/config values.
3. Start full local stack:
   - `just docker-start`
4. Open API docs:
   - `http://localhost:8000/docs`

## Daily Commands

- Full pipeline:
  - `just docker-pipeline-full`
- Health/status:
  - `just docker-smoke`
- Quality gate:
  - `just quality`

For agent-issued workflow commands, use the `rtk` prefix when available:

- `rtk just docker-start`
- `rtk just docker-pipeline-full`
- `rtk just quality`

Host-local equivalents such as `uv run pytest`, `.venv/bin/pytest`, or direct `python` commands are not the primary plan for agents. Prefer the matching container-backed `just` recipe first; fall back only with an explicit reason.

## Frontend Workflow (`client/`)

The Opportunity Workspace frontend is Docker-first.

1. Start the full local stack:
   - `just dev`
2. Open the workspace route:
   - `http://127.0.0.1:3000/licitaciones`
3. Run frontend validation through the containerized client service when needed:
   - `docker compose --env-file .env.docker -f docker-compose.yml run --rm client npm run lint`
   - `docker compose --env-file .env.docker -f docker-compose.yml run --rm client npm run typecheck`
   - `docker compose --env-file .env.docker -f docker-compose.yml run --rm client npm run build`

Host-local `client/` commands remain fallback only when the Docker path is unavailable.

## Manual CSV append from workspace

Use this flow when you need to append one late or corrected CSV through the UI instead of replaying the dataset folder.

1. Ensure backend is healthy first:
   - `just docker-start`
   - `just docker-smoke`
2. Open `http://127.0.0.1:3000/licitaciones`
3. Click `Cargar CSV`
4. Pick the dataset explicitly:
   - `Licitaciones`
   - `Ordenes de compra`
5. Choose one CSV file and run preflight
6. Confirm only after preflight reports:
   - dataset
   - row count
   - canonical filename
   - hash
   - duplicate warning when applicable
7. Review result telemetry after processing:
   - raw accepted rows
   - canonical inserted delta
   - duplicates/existing rows
   - normalized rows
   - silver rows

Important behavior:

- Uploaded filename does not decide dataset semantics.
- Manual append is single-file and bounded by default. It does not replace `just docker-pipeline-full`.
- Duplicate business rows may still appear as new raw lineage under a different source file while canonical layers remain idempotent.
- If the process request fails, query `GET /uploads/procurement-csv/jobs/{job_id}` or re-open the workspace and retry with a fresh preflight token.

Backend CORS explicitly allows the local frontend origins used by this runbook (`http://localhost:3000` and `http://127.0.0.1:3000`). Keep origins explicit; do not rely on wildcard origins for MVP browser integration.

## Current Code Paths

- Backend app entrypoint: `backend/main.py`
- API routers: `backend/api/routers/`
- Opportunity API: `backend/api/routers/opportunities.py`
- Investigation API: `backend/api/routers/investigations.py`
- Frontend route: `client/app/licitaciones/page.tsx`
- Frontend workspace feature: `client/src/features/opportunity-workspace/`
- Frontend API client: `client/src/lib/api/`

## Notes

- `docker-start` is the canonical startup command (build + DB bootstrap + backend up).
- Host-local runtime recipes are fallback/developer convenience paths. Keep docs and automation Docker-first unless a task is explicitly frontend-only.
