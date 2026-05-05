## Why

Omnibid already has the procurement analytics contracts split across standards, pipeline wrappers, runtime config, and implementation code. The repo now needs one source-backed change that both documents the contract and hardens the code path that enforces it, so future agents do not have to rediscover where the real rules live.

The intended implementation is narrow:

- keep the current CSV drop pipeline as the canonical implemented source profile
- document `api_json` and `open_data_snapshot` as explicit source profiles for later implementation slices
- add code-level source-profile and runtime validation around the existing pipeline surface
- add tests for routing, env split, and Silver boundary behavior
- align the PostgreSQL baseline docs with the effective Compose runtime
- keep Silver metadata-only and reference-only
- keep downstream semantic/NLP work outside Silver

## What Changes

- Add `docs/standards/customer-analytics-standards.md`.
- Add `docs/references/sdd-customer-analytics-standards-2026-05-05.md`.
- Update `docs/references/sdd-official-sources-registry.md` with the official Python standard-library links used by the pipeline and the versioned PostgreSQL 16 reference.
- Update `docs/standards/postgres-standard.md` so the baseline matches the actual Compose image and not the stale 18-alpine wording.
- Extend the pipeline/runtime code surface with explicit contract helpers for source-profile selection and database-environment validation.
- Add tests for pipeline routing, runtime validation, and the existing Silver boundary.
- Keep the current CSV pipeline behavior unchanged in this slice while making the contract explicit in code.

## Capabilities

### New Capabilities

- `customer-analytics-source-contract-standard`
- `customer-analytics-runtime-contract`
- `customer-analytics-source-profile-routing`
- `customer-analytics-validation`
- `customer-analytics-sdd-traceability`

### Modified Capabilities

- `postgres-runtime-doc-alignment`
- `official-source-registry-alignment`

## Context

The repository already defines:

- current CSV profile handling in `scripts/profile_raw.py`
- raw ingestion and lineage in `scripts/ingest_raw.py`
- normalized and Silver construction in `scripts/build_normalized.py`
- pipeline orchestration helpers in `backend/pipeline/application.py`
- required-column contracts in `backend/ingestion/contracts.py`
- environment-driven DB config in `backend/core/config.py`
- identity resolution and `tfidf://` annotation references in `backend/normalized/transform.py`
- metadata-only Silver text annotation tables in `backend/models/normalized.py`
- upsert guardrails and quality gates in `backend/normalized/upsert_engine.py` and `backend/normalized/quality_gate.py`
- host vs Docker env separation in `.env` and `.env.docker`

The Compose runtime currently uses `postgres:16-alpine`, so the docs need to reflect the effective baseline before any later implementation slice starts.

## Verified Official Sources

1. Python stdlib: `csv`, `hashlib`, `pathlib`, `argparse`, `json`, `datetime`, `unicodedata`
2. Pydantic Settings
3. SQLAlchemy PostgreSQL insert/upsert and Session API
4. Alembic migrations
5. PostgreSQL 16 `INSERT` and numeric types
6. ChileCompra Datos Abiertos, API, and Mercado Publico portal pages

## Non-Goals

- No frontend work.
- No schema rewrite for the existing Silver tables.
- No new public API routes.
- No replacement of the current raw / normalized / Silver pipeline.
- No new API ingestion lane in this change.
- No downstream NLP or semantic model implementation in this slice.
- No Gold ranking or model-training slice; that work lives in `gold-procurement-line-ranking`.

## Impact

- `docs/standards/customer-analytics-standards.md`
- `docs/references/sdd-customer-analytics-standards-2026-05-05.md`
- `docs/references/sdd-official-sources-registry.md`
- `docs/standards/postgres-standard.md`
- `backend/pipeline/`
- `backend/core/config.py`
- `backend/ingestion/contracts.py`
- `tests/unit/test_pipeline_application_module.py`
- `tests/unit/test_ingestion_contracts.py`

Not impacted in this slice:

- `backend/main.py`
- `backend/api/routers/`
- `client/`
- `alembic/versions/`
- existing raw / normalized / Silver schema definitions

## Goals

- Make the procurement analytics standard source-backed and easy to find.
- Keep the current CSV pipeline canonical while documenting the next source profiles.
- Add code-level guardrails for source-profile routing and runtime validation.
- Align the docs with the actual Docker and `.env` runtime contract.
- Preserve the Silver boundary as deterministic and metadata-only.

## Open Questions

- Should `api_json` and `open_data_snapshot` remain documentation-only profiles for now, or should the next implementation slice add adapters for them?
- Should the code contract live only in `backend/pipeline/`, or should part of it be promoted into `backend/core/config.py` and shared helpers?
- Should future runtime changes move the Compose PostgreSQL baseline from 16 to a newer version, or is 16 the long-lived baseline for this repo?
- Should the current repo/app naming split (`omnibid` vs `app-chilecompra`) be resolved in a separate rename proposal?

## Validation Strategy

- verify the documentation links against the official source URLs
- confirm the doc and registry diffs are internally consistent
- confirm the PostgreSQL baseline doc matches the effective Compose image
- add focused unit tests for pipeline routing and runtime validation
- keep the first slice schema-neutral
