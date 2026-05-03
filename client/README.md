# Opportunity Workspace Client

Next.js frontend for the read-only ChileCompra Opportunity Workspace.

## Scope

- Primary route: `/licitaciones`
- API base: `NEXT_PUBLIC_API_BASE_URL`
- Backend source: Docker-first FastAPI runtime from repo root
- UI language: Spanish
- Views: `Explorador` table and `Radar` board
- Detail model: shared read-only `Detalle de licitación` drawer

## Local Run

From repo root, start the full Docker dev stack:

```bash
rtk just dev
```

Open:

- `http://127.0.0.1:3000/licitaciones`

This starts PostgreSQL, applies backend migrations, starts FastAPI, then starts Next.js. The Docker client service installs npm dependencies inside a Docker volume and exposes Next.js on localhost only.

Host-local fallback from `client/`:

```bash
npm.cmd install
copy .env.example .env.local
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `.env.local`.

## Validation

From repo root:

```bash
rtk just dev
docker compose --env-file .env.docker -f docker-compose.yml run --rm client npm run lint
docker compose --env-file .env.docker -f docker-compose.yml run --rm client npm run typecheck
docker compose --env-file .env.docker -f docker-compose.yml run --rm client npm run build
```

## Code Paths

- Route: `app/licitaciones/page.tsx`
- Workspace feature: `src/features/opportunity-workspace/`
- API clients: `src/lib/api/`
- URL state: `src/lib/url-state/`
- Shared UI: `src/components/ui/`
- Design tokens/styles: `src/styles/`

Keep list views at notice grain. Use detail views for child lines, offers, awards, purchase orders, and relationship evidence.

## Product Boundaries

- `Pulso de oportunidades` uses `/opportunities/summary`; unavailable metrics are shown as unavailable, not inferred from a page of list data.
- `Explorador` and `Radar` render one parent item per licitación/notice.
- Child lines, offers, purchase orders, certainty, and metadata are shown in expansion or the shared drawer only when the API provides data.
- MVP actions are read-only: copy code and open the public licitación URL when an external code exists.
- No assignment, notes, discard, AI analysis, scoring, workflow mutation, or persistent drag-and-drop behavior is implemented.
