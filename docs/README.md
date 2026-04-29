# Documentation Index

This directory contains the operating and architecture knowledge for `app-chilecompra`.

The repository is Docker-first. Start runtime decisions from [`runbooks/docker-local.md`](runbooks/docker-local.md), then use [`runbooks/local_development.md`](runbooks/local_development.md) for frontend/backend development flow.

## Structure

- [`architecture/`](architecture)
  - system, data architecture, and data model references
- [`runbooks/`](runbooks)
  - local development, operations, CI, and implementation runbooks
  - Docker local runtime: [`runbooks/docker-local.md`](runbooks/docker-local.md)
- [`product/`](product)
  - product vision and stage-gated delivery priorities
- [`standards/`](standards)
  - engineering standards (typing, linting, testing, security, logging, SQL)
- [`references/`](references)
  - SDD source registry and external technical references
- [`evidence/`](evidence)
  - validation artifacts, baselines, and runtime logs

## Priority Read Order

1. [`../AGENTS.md`](../AGENTS.md)
2. [`../README.md`](../README.md)
3. [`runbooks/docker-local.md`](runbooks/docker-local.md)
4. [`runbooks/local_development.md`](runbooks/local_development.md)
5. [`architecture/system_architecture.md`](architecture/system_architecture.md)
6. [`architecture/data_architecture.md`](architecture/data_architecture.md)
7. [`architecture/data_model.md`](architecture/data_model.md)
8. [`runbooks/operations.md`](runbooks/operations.md)

## Agent Routing Guide

- Runtime and pipelines: `just docker-start`, `just docker-pipeline-full`, `just docker-smoke`.
- Backend routes: `backend/api/routers/`.
- Backend config/database/model work: `backend/core/`, `backend/db/`, `backend/models/`, `alembic/versions/`.
- Data pipeline work: `backend/ingestion/`, `backend/normalized/`, `scripts/`.
- Frontend work: `client/app/licitaciones/`, `client/src/features/opportunity-workspace/`, `client/src/lib/api/`.
- Change artifacts: `openspec/changes/<change>/`.
- Validation evidence: `docs/evidence/`.

## Current Focus

The repository is past the Silver procurement-cycle foundation and now has read-only workspace slices:

- canonical procurement entities are implemented
- deterministic enrichments are implemented
- NLP semantic annotations are implemented (reference-only TF-IDF contract)
- procurement line investigation APIs are implemented under `/investigations`
- opportunity read APIs and the `/licitaciones` frontend workspace are present
- Gold scoring/forecasting remains deferred

For current implementation details, see:
- [`runbooks/silver_procurement_cycle_implementation_plan.md`](runbooks/silver_procurement_cycle_implementation_plan.md)
- [`evidence/silver_procurement_cycle_validation_2026-04-23.md`](evidence/silver_procurement_cycle_validation_2026-04-23.md)
- [`runbooks/procurement_investigation_workspace_plan.md`](runbooks/procurement_investigation_workspace_plan.md)
- [`runbooks/opportunity_workspace_frontend_mvp_plan.md`](runbooks/opportunity_workspace_frontend_mvp_plan.md)
