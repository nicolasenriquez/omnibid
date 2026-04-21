# System Architecture

Monorepo with modular backend:
- backend/core: config, settings, logging
- backend/db: engine, session, models
- backend/ingestion: file discovery + registration
- backend/profiling: schema/stats profiling
- backend/raw: raw persistence + lineage
- backend/normalized: normalized entities
- backend/gold: minimal aggregates
- backend/api: health + operations endpoints
- client/: frontend placeholder for future UI
