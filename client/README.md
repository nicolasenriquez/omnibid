# Opportunity Workspace Client

Next.js frontend for the read-only ChileCompra Opportunity Workspace.

## Scope

- Primary route: `/licitaciones`
- API base: `NEXT_PUBLIC_API_BASE_URL`
- Backend source: Docker-first FastAPI runtime from repo root
- UI language: Spanish

## Local Run

From repo root, start the full Docker dev stack:

```bash
just dev
```

Open:

- `http://127.0.0.1:3000/licitaciones`

This starts PostgreSQL, applies backend migrations, starts FastAPI, then starts Next.js. The Docker client service installs npm dependencies inside a Docker volume and exposes Next.js on localhost only.

Host-local fallback from `client/`:

```bash
npm install
copy .env.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `.env.local`.

## Validation

```bash
npm run lint
npm run typecheck
npm run build
```

## Code Paths

- Route: `app/licitaciones/page.tsx`
- Workspace feature: `src/features/opportunity-workspace/`
- API clients: `src/lib/api/`
- URL state: `src/lib/url-state/`
- Shared UI: `src/components/ui/`
- Design tokens/styles: `src/styles/`

Keep list views at notice grain. Use detail views for child lines, offers, awards, purchase orders, and relationship evidence.
