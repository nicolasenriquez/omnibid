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

The Opportunity Workspace frontend scaffold now exists under `client/`.

1. Install frontend dependencies:
   - `cd client`
   - `npm install`
2. Configure local frontend environment:
   - `copy .env.example .env.local`
   - ensure `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
3. Start backend API with the canonical Docker runtime from repo root:
   - `just docker-start`
4. Start frontend dev server from `client/`:
   - `npm run dev -- --hostname 127.0.0.1 --port 3000`
5. Open the workspace route:
   - `http://127.0.0.1:3000/licitaciones`
6. Run frontend validation from `client/`:
   - `npm run lint`
   - `npm run typecheck`
   - `npm run build`

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
