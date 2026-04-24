## 1. Contract Baseline and Scope Lock

- [x] 1.1 Capture and store source-grain evidence for licitaciones and OC datasets used in this change.
  Notes: include row counts, unique business-key counts, and optional-linkage ratios.
  Acceptance: evidence file is committed under `docs/evidence/` with reproducible command history.
  Notes: Evidence captured in `docs/evidence/silver_procurement_cycle_grain_baseline_2026-04-22.md` with parser-level metrics for `202603_lic.csv` and `202604-oc.csv`.
- [x] 1.2 Freeze canonical table grain definitions and key contracts for all target entities.
  Notes: document PK/FK and nullable relationships explicitly.
  Acceptance: architecture and spec files are internally consistent and review-approved.
  Notes: Naming decision frozen to concise physical `silver_*` tables (`silver_notice`, `silver_notice_line`, `silver_bid_submission`, `silver_award_outcome`, `silver_purchase_order`, `silver_purchase_order_line`, and related master/bridge/annotation tables).
  Notes: TF-IDF persistence frozen to artifact references only (no serialized vector snapshots in Silver tables).

## 2. Schema and Model Expansion (Additive)

- [x] 2.1 Add migrations/models for core process entities:
  - procurement notices
  - notice lines
  - bid submissions
  - award outcomes
  - purchase orders
  - purchase order lines
  Acceptance: migration/ORM parity tests pass and no unintended autogenerate drift.
  Notes: Added core ORM entities in `backend/models/normalized.py` with frozen concise naming (`silver_notice`, `silver_notice_line`, `silver_bid_submission`, `silver_award_outcome`, `silver_purchase_order`, `silver_purchase_order_line`).
  Notes: Added Alembic migration `alembic/versions/202604230010_silver_core_entities.py` with additive schema only.
  Notes: Task-local proof: `uv run pytest -q tests/unit/test_silver_core_schema_parity.py` and `uv run ruff check ...` passed.
- [x] 2.2 Add migrations/models for master and bridge entities:
  - buying organizations
  - contracting units
  - supplier registry
  - category reference
  - notice-purchase-order links
  - supplier participation facts
  Acceptance: deterministic key constraints and FK integrity tests pass.
  Notes: Added ORM entities in `backend/models/normalized.py` for `silver_buying_org`, `silver_contracting_unit`, `silver_supplier`, `silver_category_ref`, `silver_notice_purchase_order_link`, and `silver_supplier_participation`.
  Notes: Added Alembic migration `alembic/versions/202604230020_silver_master_bridge_entities.py` with additive FK-safe contracts.
  Notes: Task-local proof: `uv run pytest -q tests/unit/test_silver_core_schema_parity.py tests/unit/test_silver_master_bridge_schema_parity.py` and targeted Ruff checks passed.

## 3. Builder and Transform Integration

- [x] 3.1 Implement deterministic payload builders for new entities and relationship links.
  Notes: preserve fail-fast behavior for required identities and deterministic rejection accounting.
  Acceptance: targeted transform tests pass for each entity grain.
  Notes: Added deterministic transform builders and identity helpers in `backend/normalized/transform.py` for all new core/master/bridge Silver entities.
  Notes: Added focused unit suite `tests/unit/test_silver_transform_builders.py` covering required keys, identity precedence, and deterministic mapping behavior.
  Notes: Task-local proof: `uv run pytest -q tests/unit/test_silver_transform_builders.py` and targeted Ruff checks passed.
- [x] 3.2 Integrate additive upsert flows into normalized pipeline in deterministic execution order.
  Notes: preserve run telemetry and lineage fields (`source_file_id`, `ingestion_batch_id`, `pipeline_run_id` where applicable).
  Acceptance: replay idempotency tests show zero semantic duplicates.
  Notes: Integrated additive Silver write paths in `scripts/build_normalized.py` for core/master/bridge entities with explicit conflict contracts and deterministic flush ordering.
  Notes: Added deterministic flush-order + conflict-contract + idempotent upsert unit coverage in `tests/unit/test_normalized_domain_entities_tdd.py`.
  Notes: Task-local proof: targeted pytest and Ruff checks passed (`tests/unit/test_normalized_domain_entities_tdd.py`, `tests/unit/test_silver_transform_builders.py`, `tests/unit/test_silver_*_schema_parity.py`).

## 4. Deterministic Enrichment Layer

- [x] 4.1 Add allowed Silver enrichments:
  - `*_raw` and `*_clean` text fields
  - temporal durations and chain-integrity flags
  - administrative/contract flags
  - structural and competition metrics
  - materialization metrics
  Acceptance: derivation formulas are documented and deterministic tests pass.
  Notes: Added additive enrichment migration `alembic/versions/202604230030_silver_deterministic_enrichment.py` plus ORM/transform/pipeline refresh paths for notice, notice-line, and purchase-order deterministic metrics.
  Notes: Added explicit derivation catalog in `docs/runbooks/silver_procurement_cycle_implementation_plan.md` (M3 section).
  Notes: Deterministic tests added for refresh SQL coverage in `tests/unit/test_normalized_domain_entities_tdd.py`.
  Notes: Task-local proof: `uv run pytest -q tests/unit/test_normalized_domain_entities_tdd.py tests/unit/test_silver_transform_builders.py` and `uv run ruff check ...` passed.
- [x] 4.2 Add leakage guardrails for feature engineering readiness.
  Notes: features depending on future information must be blocked from Silver.
  Acceptance: tests/assertions enforce forbidden future-dependent derivations.
  Notes: Added fail-fast Silver leakage guardrails in `scripts/build_normalized.py` (`validate_silver_feature_guardrails`) enforcing forbidden predictive/future-prefixed feature columns.
  Notes: Added guardrail tests in `tests/unit/test_normalized_domain_entities_tdd.py` rejecting `*_score` and `future_*` payload columns for Silver entities.

## 5. Semantic Annotation Contracts

- [x] 5.1 Add versioned annotation entities for notice, notice line, and purchase-order line text.
  Notes: include `nlp_version`, annotation payloads, and artifact references.
  Notes: use sklearn feature extraction primitives only (`CountVectorizer`/`TfidfVectorizer`/n-grams), without supervised model training in Silver.
  Acceptance: schema contracts and sample writes are deterministic and replay-safe.
  Notes: Added Alembic migration `alembic/versions/202604230040_silver_text_annotations.py` for `silver_notice_text_ann`, `silver_notice_line_text_ann`, and `silver_purchase_order_line_text_ann`.
  Notes: Added ORM entities and deterministic annotation builders in `backend/models/normalized.py` and `backend/normalized/transform.py`.
  Notes: Integrated additive upsert/write paths and metrics in `scripts/build_normalized.py` for licitación and OC pipelines.
  Notes: Added schema parity coverage in `tests/unit/test_silver_text_annotation_schema_parity.py` and builder coverage in `tests/unit/test_silver_transform_builders.py`.
- [x] 5.2 Define annotation policy boundaries in docs and validation checks.
  Notes: annotation-only semantics, no business score persistence in Silver.
  Notes: TF-IDF must remain reference-only (`tfidf_artifact_ref`), never serialized vectors in Silver tables.
  Acceptance: documentation and tests explicitly separate annotation from scoring.
  Notes: Implemented annotation contract validation in `scripts/build_normalized.py` (`tfidf_artifact_ref` must use `tfidf://` and serialized vector fields are rejected).
  Notes: Added guardrail tests in `tests/unit/test_normalized_domain_entities_tdd.py` for non-reference TF-IDF and forbidden vector columns.
  Notes: Updated M4 policy details in `docs/runbooks/silver_procurement_cycle_implementation_plan.md`.

## 6. Validation, Operations, and Handoff

- [x] 6.1 Run quality gates and controlled pipeline validations for each milestone slice.
  Acceptance: `just quality` plus targeted pipeline runs complete with evidence capture.
  Notes: `just quality` passed (`ruff` + `mypy` + `pytest -m \"not integration\"`: 118 passed, 2 skipped).
  Notes: Controlled pipeline validations succeeded with limited slices for both datasets:
  - `--dataset licitacion --limit-rows 50`
  - `--dataset orden_compra --limit-rows 50`
  Notes: Evidence captured in `docs/evidence/silver_procurement_cycle_validation_2026-04-23.md`.
- [x] 6.2 Update architecture/runbooks with final "current vs target" state and migration playbook.
  Acceptance: docs are implementation-aligned and ready for Gold/feature-store follow-up proposals.
  Notes: Updated architecture docs to reflect implemented Silver current-state:
  - `docs/architecture/data_model.md`
  - `docs/architecture/data_architecture.md`
  Notes: Updated implementation runbook with current-state and migration playbook:
  - `docs/runbooks/silver_procurement_cycle_implementation_plan.md`
