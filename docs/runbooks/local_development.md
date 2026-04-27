# Local Development Runbook

Canonical runtime is Docker-first. Use [`docker-local.md`](docker-local.md) as the primary runbook.

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

## Notes

- `docker-start` is the canonical startup command (build + DB bootstrap + backend up).
- Host-local runtime recipes were intentionally removed to keep operations deterministic across machines.
