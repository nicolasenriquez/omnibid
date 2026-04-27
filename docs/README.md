# Documentation Index

This directory contains the operating and architecture knowledge for `app-chilecompra`.

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
2. [`architecture/data_architecture.md`](architecture/data_architecture.md)
3. [`architecture/data_model.md`](architecture/data_model.md)
4. [`runbooks/local_development.md`](runbooks/local_development.md)
5. [`runbooks/operations.md`](runbooks/operations.md)

## Current Focus

The repository is in the Silver procurement-cycle implementation stage:

- canonical procurement entities are implemented
- deterministic enrichments are implemented
- NLP semantic annotations are implemented (reference-only TF-IDF contract)
- Gold scoring/forecasting remains deferred

For current implementation details, see:
- [`runbooks/silver_procurement_cycle_implementation_plan.md`](runbooks/silver_procurement_cycle_implementation_plan.md)
- [`evidence/silver_procurement_cycle_validation_2026-04-23.md`](evidence/silver_procurement_cycle_validation_2026-04-23.md)
