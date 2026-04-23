# App ChileCompra - Procurement Data Platform

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Data%20Layer-4169E1?logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-Migrations-222222)

Deterministic procurement data platform for ChileCompra workflows:
Raw ingestion + canonical normalization + Silver procurement-cycle modeling + deterministic enrichments + versioned NLP annotations + operational APIs.

## Overview

This monorepo implements a stage-gated data platform focused on trustworthy procurement analytics foundations.

Current product direction:

- System of record: ingest source CSV datasets with explicit lineage and fail-fast data contracts
- Canonical layer: normalize source grain into deterministic relational entities
- Silver layer: model full procurement cycle (notice -> line -> bid -> award -> purchase order -> purchase order line)
- Analytics foundation: add deterministic feature engineering and NLP annotations without predictive business scoring in Silver

## Current Platform Status

| Area | Current Status |
|---|---|
| Phase | Silver procurement-cycle foundation implemented; Gold deferred |
| Backend | FastAPI + SQLAlchemy + Alembic |
| Database | PostgreSQL |
| Data Layers | Raw + Normalized + Silver canonical entities |
| API Surface | 6 operational routes (`health`, `runs`, `files`, dataset summary) |
| Local CLI | 38 `just` recipes |
| OpenSpec Runtime | Latest change complete (`all_done`) and ready to archive |
| Version | `0.1.0` |
| Last Verified | 2026-04-23 |

## Main Capabilities

- raw dataset profiling and append-oriented ingestion with source lineage
- normalized deterministic entities (`licitaciones`, items, offers, purchase orders, buyers/suppliers/categories)
- Silver procurement-cycle canonical entities:
  - `silver_notice`
  - `silver_notice_line`
  - `silver_bid_submission`
  - `silver_award_outcome`
  - `silver_purchase_order`
  - `silver_purchase_order_line`
  - master/bridge entities (`silver_buying_org`, `silver_contracting_unit`, `silver_supplier`, `silver_category_ref`, `silver_notice_purchase_order_link`, `silver_supplier_participation`)
- deterministic feature engineering in Silver:
  - temporal durations
  - administrative flags
  - structural counts
  - competition metrics
  - notice -> purchase order materialization metrics
- versioned NLP annotation entities:
  - `silver_notice_text_ann`
  - `silver_notice_line_text_ann`
  - `silver_purchase_order_line_text_ann`
- strict Silver guardrails:
  - forbid predictive business fields (`*_score`, `*_probability`, `future_*`, forecast/recommendation fields)
  - enforce TF-IDF reference-only persistence (`tfidf_artifact_ref`)

## Architecture At a Glance

```mermaid
flowchart LR
  A[Source CSV Files<br/>licitaciones + ordenes_compra] --> B[Raw Ingestion]
  B --> C[Normalized Canonical Tables]
  C --> D[Silver Procurement Cycle]
  D --> E[Deterministic Enrichments]
  D --> F[Versioned NLP Annotations]
  E --> G[(PostgreSQL)]
  F --> G
  G --> H[Operations API<br/>health, runs, files, datasets summary]
  G --> I[Future Gold Layer<br/>scores/forecasting/anomalies]
```

## Core Workflow

```mermaid
flowchart TD
  S1[1. Register source files] --> S2[2. Profile raw datasets]
  S2 --> S3[3. Ingest raw records with lineage]
  S3 --> S4[4. Build normalized entities]
  S4 --> S5[5. Build Silver procurement-cycle entities]
  S5 --> S6[6. Refresh deterministic enrichments]
  S6 --> S7[7. Build versioned NLP annotation entities]
  S7 --> S8[8. Serve operations endpoints + readiness evidence]
```

## Repository Layout

```text
.
├── backend/
│   ├── api/                      # FastAPI routers (health, operations)
│   ├── core/                     # config and runtime settings
│   ├── db/                       # DB base/session wiring
│   ├── ingestion/                # ingestion contracts and source registration
│   ├── models/                   # operational/raw/normalized/silver ORM models
│   ├── normalized/               # deterministic transform builders
│   ├── observability/            # structured logging utilities
│   └── main.py
├── scripts/                      # pipeline/operator entrypoints
│   ├── profile_raw.py
│   ├── ingest_raw.py
│   └── build_normalized.py
├── alembic/                      # migration source of truth
├── data/                         # local artifacts/state
├── docs/                         # architecture, runbooks, standards, evidence
├── openspec/                     # change proposals/spec workflow
├── .codex/commands/              # repo-local Codex command workflows
├── justfile                      # unified local CLI
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL reachable from `DATABASE_URL`
- `just` (recommended workflow runner)

Install `just` on macOS:

```bash
brew install just
```

### Install and Bootstrap

```bash
cp .env.example .env
just setup
just db-bootstrap
```

### Configure Environment

Minimum expected variables in `.env`:

```bash
APP_ENV=local
APP_NAME=app-chilecompra
APP_PORT=8000
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra_test
LOG_LEVEL=INFO
DATASET_ROOT=/absolute/path/to/dataset-mercado-publico
```

### Run Pipelines and API

```bash
just pipeline-raw
just pipeline-normalized
just api
```

- API base: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`

## Local Quality Gates

```bash
just quality
just ci-fast
just ci
```

Targeted workflows:

- unit tests: `just test-unit`
- integration tests: `just test-integration`
- lint/type/security: `just lint`, `just type`, `just security`
- strict typing: `just type-strict`

## Unified CLI (`just`) Overview

- Setup: `setup`, `codex-sync`
- Database: `db-bootstrap`, `db-create`, `db-migrate`, `db-revision`
- Raw: `raw-profile`, `raw-ingest`, `pipeline-raw`
- Normalized/Silver build: `normalized-build`, `normalized-lic`, `normalized-oc`, `pipeline-normalized`
- End-to-end: `pipeline-full`, `pipeline-full-fast`
- API runtime: `api`
- Quality and CI: `quality`, `ci-fast`, `ci`, plus lint/type/test/security recipes

## API Surface (Current)

- Health:
  - `GET /health`
- Operations:
  - `GET /runs`
  - `GET /runs/{run_id}`
  - `GET /files`
  - `GET /files/{source_file_id}`
  - `GET /datasets/summary`

## Documentation Index

- docs home: [`docs/README.md`](docs/README.md)
- architecture: [`docs/architecture/`](docs/architecture)
- runbooks: [`docs/runbooks/`](docs/runbooks)
- product context: [`docs/product/`](docs/product)
- standards: [`docs/standards/`](docs/standards)
- references: [`docs/references/`](docs/references)
- evidence: [`docs/evidence/`](docs/evidence)

## Delivery Rules

- fail-fast on broken contracts, schema drift, or required dependency misconfiguration
- TDD-first for behavior changes
- SDD-first for framework/library usage (documented in `docs/references/`)
- no Gold/predictive business scoring inside Silver until stage-gate criteria are met
