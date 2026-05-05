# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Procurement investigation workspace API routes (documented, pending wiring in `backend/main.py`)
- Gold-layer predictive scoring and forecasting (stage-gated; forbidden in Silver)

---

## [0.1.0] — 2026-04-17 to 2026-05-02

### Added

#### Data Pipeline — Raw Layer
- **Raw dataset profiling and append-oriented ingestion** with explicit source lineage (`source_file_id`, `ingestion_batch_id`, `pipeline_run_id`).
- **Reconciled load telemetry** replacing rowcount-based metrics with deterministic counters: `accepted`, `deduplicated`, `inserted_delta`, `existing_or_updated`. Includes tests for duplicate-heavy reruns and no-op reruns.
- **Pipeline reliability hardening**: rollback-first state persistence, retry-safe checkpoint behavior, and bounded dataset summary caching to prevent partial payload retention after transient failures.
- **Scoped pipeline processing**: support `source_file_id` filtering in raw/normalized builders for bounded reprocessing of individual files.

#### Data Pipeline — Normalized Layer
- **Normalized domain entities**: buyers, suppliers, and category dimensions with migrations, ORM models, and identity-resolution logic.
- **FK-safe chunk flushing**: forced dimension flush before fact chunks to prevent foreign-key violations during bulk inserts.
- **Normalized quality-gate evaluation**: persistent checkpoint metrics with retry-safe semantics.

#### Data Pipeline — Silver Layer
- **Silver procurement-cycle core entities**: `silver_notice`, `silver_notice_line`, `silver_bid_submission`, `silver_award_outcome`, `silver_purchase_order`, `silver_purchase_order_line`.
- **Silver master/bridge entities**: `silver_buying_org`, `silver_contracting_unit`, `silver_supplier`, `silver_category_ref`, `silver_notice_purchase_order_link`, `silver_supplier_participation`.
- **Deterministic feature engineering** in Silver: temporal durations, administrative flags, structural counts, competition metrics, and notice-to-purchase-order materialization metrics.
- **Versioned NLP annotation entities**: `silver_notice_text_ann`, `silver_notice_line_text_ann`, `silver_purchase_order_line_text_ann`.
- **Silver guardrails**: strict prohibition of predictive business fields (`*_score`, `*_probability`, `future_*`, forecast/recommendation); TF-IDF artifacts stored by reference only (`tfidf_artifact_ref`).
- **Defensive typing in Silver transforms**: sanitize corrupted `dict` values from `raw_json` before persistence to prevent psycopg2 adaptation errors.

#### API Backend
- **Operations endpoints**: `GET /runs`, `GET /runs/{run_id}`, `GET /files`, `GET /files/{source_file_id}`, `GET /datasets/summary`.
- **Dataset summary snapshots**: durable `dataset_summary_snapshots` table with default reads from the latest successful snapshot; `mode=fresh` triggers explicit recount with safe fallback to last known good state.
- **Opportunity read APIs**: `GET /opportunities`, `GET /opportunities/summary`, `GET /opportunities/{notice_id}` aligned with frontend contract (count keys, line-level certainty metadata).
- **Manual CSV upload API**: `/manual-uploads` router with file size limits (50 MB default), structured temp storage, CSV validation, and pipeline integration.
- **Health endpoint**: `GET /health`.

#### Frontend — Opportunity Workspace
- **Next.js application** under `client/` with primary route `/licitaciones`.
- **Explorer + Radar layout**: read-only workspace with shared detail drawer, keyboard navigation, and process-level KPIs.
- **Detail context enrichment**: normalized licitacion dates as Silver fallback, offer evidence with supplier/item/amount/quantity/unit price.
- **Manual upload workspace flow**: drag-and-drop CSV upload sheet, live processing console with timeline entries and color-coded log levels, dataset pill-toggle selector (Licitaciones / Órdenes de compra).
- **Responsive design**: mobile/tablet breakpoints for header, dataset toggle, and upload sheet.

#### Infrastructure / DevOps
- **Docker-first local runtime**: `docker-compose.yml` + `.env.docker` with non-root API container, read-only root fs, `no-new-privileges`, and health checks.
- **Unified CLI (`just`)**: `docker-start`, `docker-build`, `docker-bootstrap`, `docker-pipeline-full`, `docker-smoke`, plus quality/test/lint/type recipes.
- **GitHub Actions CI**: automated checks and dependency automation.
- **Container-internal PostgreSQL host policy**: service DNS (`db` / `db_test`), never `localhost`.

#### Documentation & Standards
- **SDD-first methodology**: formalized standards, official source registry, and reference template under `docs/references/`.
- **OpenSpec change workflow**: proposals, designs, specs, tasks, and validation evidence under `openspec/changes/`.
- **Architecture docs**: raw/normalized/silver data lineage, runbooks, and agent path guides.

### Changed
- Renamed pipeline terminology and project layout from Bronze/Silver to **Raw/Normalized** across backend, scripts, migrations, and Codex paths.
- Progress rendering switched to `tqdm` for positioned footer bars while preserving Rich for unpositioned output.
- Dataset summary endpoint moved from runtime counting to snapshot-first reads with optional fresh recount.

### Fixed
- SQLAlchemy ProgrammingError in Silver caused by nested JSON structures in ingested `raw_json`.
- Stale summary fixture in opportunity tests; added detail contract coverage.
- Missing backend startup cleanup: removed stale investigations router import.
- Windows `spawn EPERM` during Next.js build handled via outside-sandbox rerun.

### Security
- API rate-limiting and bounds on operations endpoints.
- Manual upload file size cap (`MANUAL_UPLOAD_MAX_BYTES=52428800`) and structured temp storage.
- Gitleaks config schema alignment for CI.

---

## Notes for AI Agents

- **Versioning**: this project uses SemVer. Minor bumps signal additive features; patch bumps signal fixes or hardening.
- **Changelog updates**: after every implementation slice, append a concise entry under `[Unreleased]` or the current version, grouped by `Added` / `Changed` / `Fixed` / `Removed` / `Security`.
- **Context preservation**: when resuming work, read the latest section first to understand the current baseline and avoid re-implementing what already exists.
- **SDD/TDD trail**: significant changes must include OpenSpec evidence and test coverage; document validation results in the corresponding change folder under `openspec/changes/`.
