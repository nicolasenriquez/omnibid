## Why

Omnibid already has a mature Silver procurement-cycle layer, deterministic text annotations, and read-only investigation surfaces, but it still lacks the Gold decision layer that ranks suppliers for a notice line in a time-aware, leakage-safe way.

The missing piece is not another ingestion path. The missing piece is an implementation-ready Gold mart and model pipeline that can:

- turn existing Silver facts into ranked supplier candidates
- keep labels, features, and model selection time-aware
- combine structured procurement facts, sparse text evidence, and graph signals
- expose scores, confidence, and evidence through the existing read-only investigation flow

The repository is already at the right maturity point for this work:

- Silver procurement-cycle entities are implemented and stable
- Silver text annotations are metadata-only and reference-only
- Docker-first DB execution is already the canonical runtime
- the current search surface is still lexical, so a Gold ranking layer would add real value

This change is downstream of the foundation slices in `customer-analytics-standards-foundation` and `nlp-standard-and-pipeline-foundation`, and it is the decision-layer consumer for the workspace upgrade slice.

This change defines the first implementation-ready Gold ML slice:

- a supplier-ranking mart at `supplier × notice_line × snapshot_time`
- hierarchical labels derived from Silver events
- leakage-safe structured, sparse text, and graph features
- baseline model selection using out-of-time validation
- versioned Gold outputs and evidence artifacts for the workspace

## What Changes

- Add a Gold decision-layer standard and SDD note under `docs/standards/` and `docs/references/`.
- Add a `backend/gold/` package for candidate generation, feature assembly, graph features, sparse retrieval, scoring, and explanation artifacts.
- Add a `config/gold/` surface for versioned defaults, thresholds, feature-set definitions, and model selection metadata.
- Add an operator script for training the Gold line-ranking model and another for building/scoring the Gold decision mart.
- Add additive Gold tables or materialized views for ranked supplier candidates and model-run metadata.
- Extend the read-only investigation API or read-model layer to consume Gold ranking outputs without introducing write semantics.
- Add unit and integration tests for time-based splits, leakage guards, feature selection, ranking determinism, and persistence.
- Add the required ML runtime dependencies to the Python project metadata if they are not already present, at minimum `numpy`, `pandas`, `scikit-learn`, and `networkx` for the first slice.

## Capabilities

### New Capabilities

- `gold-procurement-line-ranking`
- `supplier-opportunity-prioritization`
- `time-aware-label-building`
- `graph-augmented-ranking`
- `evidence-backed-decision-output`

### Modified Capabilities

- `gold-procurement-line-investigation`
- `read-only-investigation-workspace`
- `procurement-nlp-evidence-consumption`

## Context

The repository already defines the contract surface that this change must respect:

- `docs/architecture/data_architecture.md` defines Gold as the next stage after Silver maturity gates pass.
- `docs/architecture/data_model.md` already describes the initial Gold investigation contracts.
- `docs/runbooks/silver_procurement_cycle_implementation_plan.md` keeps Silver deterministic and reference-only.
- `docs/standards/customer-analytics-standards.md` and `docs/standards/nlp-standards.md` define the current runtime and NLP boundaries.
- `backend/normalized/transform.py` still has lightweight annotation logic, which is fine for Silver but not sufficient for Gold ranking.
- `backend/api/opportunities_query.py` still relies on lexical search, so it does not yet provide the ranking or evidence layer this change introduces.

The current data volume is sufficient for a professional first baseline:

- the Silver procurement-cycle layer has enough rows for time-based splits
- text annotations are populated at the same grain as their parent entities
- the relational model already contains buyers, suppliers, categories, notices, lines, bids, awards, and purchase-order links

## Verified Official Sources

1. scikit-learn preprocessing, feature extraction, model selection, and calibration docs
2. NetworkX graph construction, centrality, and link-prediction docs
3. PostgreSQL `INSERT` and `ON CONFLICT` docs
4. SQLAlchemy PostgreSQL insert/upsert and session docs
5. Pydantic Settings docs for environment-driven configuration

## Non-Goals

- No dense embeddings or transformer rerankers in the first slice.
- No real-time or streaming inference.
- No write APIs or automated action execution.
- No Silver schema rewrite.
- No replacement of the existing read-only workspace.
- No attempt to skip time-based validation in favor of random splits.

## Impact

- `docs/standards/gold-decision-layer.md`
- `docs/references/sdd-gold-procurement-line-ranking-2026-05-05.md`
- `docs/architecture/data_model.md`
- `backend/gold/`
- `config/gold/`
- `backend/models/gold.py` or equivalent Gold persistence models
- `scripts/train_gold_line_ranking.py`
- `scripts/build_gold_line_ranking.py`
- `alembic/versions/`
- `tests/unit/test_gold_*.py`
- `tests/integration/test_gold_*.py`
- `pyproject.toml`

Not impacted in this slice:

- `backend/normalized/`
- `backend/ingestion/`
- `client/`
- existing Silver table definitions

## Goals

- Make the Gold decision layer explicit, versioned, and reproducible.
- Rank suppliers for notice lines using a time-aware candidate grain.
- Keep the first production target explainable and dense-data-friendly.
- Combine structured facts, sparse text evidence, and graph features without leakage.
- Persist only versioned Gold outputs and artifact references, not training state in Silver.

## Validation Strategy

- verify candidate generation with unit tests on a fixed fixture set
- verify time-based label building and split boundaries with unit tests
- verify feature selection excludes post-snapshot fields
- verify ranking determinism under fixed seeds and fixed snapshots
- verify out-of-time model selection using PR-AUC, Recall@K, and calibration
- verify Gold persistence and read-model wiring against the test database
- run Docker-first smoke checks before broader quality gates
