## 1. Investigation and Contract Baseline

- [x] 1.1 Validate current normalized source-column coverage for buyer/supplier/category identity fields across controlled sample datasets.
  Notes: Capture completeness metrics for `codigo_unidad_compra`, `codigo_proveedor`/`rut_proveedor`, and `codigo_categoria` to confirm rejection-risk baseline before schema changes.
  Notes: Baseline evidence captured in `docs/evidence/normalized_domain_identity_baseline_2026-04-22.md` using `202601_lic.csv` and `202604-oc.csv`.
- [x] 1.2 Confirm deterministic business-key precedence and fail-fast rejection contract for each new domain entity.
  Notes: Document precedence decisions in implementation notes and align with spec scenarios to avoid ambiguous matching behavior.
  Notes: Precedence confirmed as `buyer=CodigoUnidadCompra`, `supplier=CodigoProveedor -> RutProveedor`, `category=codigoCategoria` with deterministic rejection + quality issue persistence on missing identity.

## 2. Tests First (TDD)

- [x] 2.1 Add failing unit tests for buyer/supplier/category identity-key extraction and typed key formatting.
  Notes: Added `tests/unit/test_normalized_domain_entities_tdd.py` with red tests for `resolve_buyer_identity_key`, `resolve_supplier_identity_key`, and `resolve_category_identity_key` plus supplier typed-key precedence (`codigo:<value>` -> `rut:<value>`).
- [x] 2.2 Add failing loader tests for idempotent upsert semantics and duplicate-source convergence in new domain entities.
  Notes: Added red tests for explicit domain conflict constants and duplicate-row convergence expectations using `upsert_rows` with `NormalizedBuyer` / `NormalizedSupplier`.
- [x] 2.3 Add failing tests for rejection behavior and data-quality issue persistence when required domain identities are missing.
  Notes: Added red tests for missing-identity issue mapping (`normalized_buyers/suppliers/categories`) and `column_name` persistence to `data_quality_issues`.
  Notes: Red proof command: `uv run pytest -q tests/unit/test_normalized_domain_entities_tdd.py` -> `5 failed` (expected pre-implementation).

## 3. Schema and Model Foundation

- [x] 3.1 Add Alembic migration for `normalized_buyers`, `normalized_suppliers`, and `normalized_categories` with primary keys and query indexes.
  Notes: Added revision `alembic/versions/20260422172140_normalized_domain_normalized_domain_entities.py` with domain tables, indexes, and nullable relational-key columns/FKs on transactional normalized tables.
- [x] 3.2 Add ORM models and required relational fields/constraints in `backend/models/normalized.py`.
  Notes: Added `NormalizedBuyer`, `NormalizedSupplier`, `NormalizedCategory` plus `buyer_key` / `supplier_key` / `category_key` FK columns and indexes in `NormalizedOrdenCompra`, `NormalizedOferta`, and `NormalizedOrdenCompraItem`.
- [x] 3.3 Add schema parity assertions/tests to prevent ORM/migration drift for new domain entities.
  Notes: Added `tests/unit/test_normalized_domain_schema_parity.py` with index-contract and migration-parity assertions for new domain schema.
  Notes: Proof command: `uv run pytest -q tests/unit/test_normalized_domain_schema_parity.py` -> `2 passed`.

## 4. Normalized Build Integration

- [x] 4.1 Implement domain payload builders/helpers in `backend/normalized/transform.py` for deterministic identity extraction.
  Notes: Added deterministic identity helpers `resolve_buyer_identity_key`, `resolve_supplier_identity_key`, `resolve_category_identity_key` and domain payload builders for buyers/suppliers/categories.
- [x] 4.2 Integrate domain extraction and upsert steps into `scripts/build_normalized.py` after transactional entity upserts.
  Notes: Keep checkpoint behavior bounded and preserve current progress logging style.
  Notes: Added domain conflict constants and integrated buyers/suppliers/categories extraction + upsert in both dataset processors with bounded chunked flushing.
- [x] 4.3 Persist deterministic quality issues and quality-gate metrics for domain-identity rejections.
  Notes: `collect_normalized_quality_issues` now maps domain entities to `normalized_missing_domain_identity` with table + identity-column context; persistence now writes `column_name` into `data_quality_issues`.
  Notes: Proof command: `uv run pytest -q tests/unit/test_normalized_domain_entities_tdd.py` -> `5 passed`.

## 5. Validation and Documentation

- [x] 5.1 Run targeted unit tests for transform and loader helpers plus full unit suite.
  Notes: Executed targeted suites:
  - `uv run pytest -q tests/unit/test_normalized_domain_entities_tdd.py` -> `5 passed`
  - `uv run pytest -q tests/unit/test_normalized_loader_helpers.py tests/unit/test_normalized_quality_gates.py tests/unit/test_normalized_transform.py` -> `35 passed`
  - `uv run pytest -q tests/unit/test_normalized_domain_schema_parity.py` -> `2 passed`
  Notes: Full local gate passed with `just quality` (`ruff + mypy + unit tests`).
- [x] 5.2 Run controlled normalized pipeline validation and capture evidence for domain-entity counts, idempotency, and rejection metrics.
  Notes: Captured in `docs/evidence/normalized_domain_entities_validation_2026-04-22.md` using bounded dual-run replay (`--limit-rows 2000`) with idempotent second-run `inserted_delta=0` for buyers/suppliers/categories.
- [x] 5.3 Update architecture/runbooks and SDD evidence references for new domain contracts and operator validation flow.
  Notes: Updated architecture/runbooks and added SDD reference note `docs/references/sdd-normalized-domain-entities-2026-04-22.md`.
