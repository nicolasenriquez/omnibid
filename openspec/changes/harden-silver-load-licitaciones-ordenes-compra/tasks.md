## 1. Investigation and Baseline

- [x] 1.1 Confirm current Silver load baseline on one licitaciones file and one orden-compra file.
  Notes: Baseline evidence captured in `docs/evidence/silver_load_baseline_2026-04-17.md` using `202601_lic.csv` and `202604-oc.csv` with current Silver builders.
  Notes: Builder-level results: LIC rows=116,658 (unique codigo_externo=7,149), OC rows=208,252 (unique codigo_oc=71,082), transform exceptions=0 for both files.
  Notes: DB-level upsert telemetry could not be captured in this sandbox because localhost:5432 is blocked; this is deferred to local operator run.
- [x] 1.2 Identify current edge cases in numeric/date/boolean parsing from recent datasets.
  Notes: Edge-case scan across selected numeric/date/boolean fields for `202601_lic.csv` and `202604-oc.csv` found no parse failures with current parser rules.
  Notes: Hardening focus remains on fail-fast contracts and explicit rejection accounting for future source schema drift, not current-file parser breakage.

## 2. Tests First (TDD)

- [x] 2.1 Add failing tests for missing critical keys per Silver entity builder.
  Notes: Added strict oferta identity test in `tests/unit/test_silver_transform.py` requiring supplier identity (`CodigoProveedor` or `RutProveedor`) instead of accepting only offer-name signal.
  Notes: Current behavior intentionally fails this test (red phase) and shows contract gap.
- [x] 2.2 Add failing tests for parsing edge cases (numeric scientific notation, sentinel dates, boolean variants).
  Notes: Added red tests for `"$1.234,56"` decimal parsing, `"verdadero"/"falso"` boolean parsing, and sentinel datetime `"1900-01-01 00:00:00"` null handling in `tests/unit/test_silver_transform.py`.
  Notes: Existing scientific notation coverage (`"6,8e+08"`) remains green.
- [x] 2.3 Add failing tests for idempotent upsert behavior in Silver loader helpers.
  Notes: Added `tests/unit/test_silver_loader_helpers.py` with red fail-fast expectations for `dedupe_rows` when conflict fields are empty or business key values are missing.
  Notes: Also added a green check that latest payload wins for duplicate business keys.

## 3. Silver Hardening Implementation

- [x] 3.1 Harden transform builders in `backend/silver/transform.py` while preserving current behavior.
  Notes: Added stricter normalization for sentinel datetimes with time (`1900-01-01 00:00:00` and variants), currency-safe decimal parsing (`$1.234,56`), and expanded boolean parsing (`verdadero/falso`).
  Notes: Oferta builder now requires supplier identity (`CodigoProveedor` or `RutProveedor`) while preserving existing offer-signal gating.
- [x] 3.2 Harden loader behavior in `scripts/build_silver.py` with explicit rejection accounting.
  Notes: Added per-dataset rejection and upsert counters with summary logging for licitaciones and ordenes_compra.
  Notes: Flush helpers now return upsert counts; process summaries print processed/rejected/upserted metrics.
- [x] 3.3 Keep business-key conflict sets explicit and validated.
  Notes: Introduced explicit conflict-key constants for all Silver entities.
  Notes: `dedupe_rows` now fail-fast validates conflict key definitions and missing business-key values; `upsert_rows` validates conflict keys exist in payload.

## 4. Validation and Documentation

- [x] 4.1 Run `just test-unit` and targeted checks for Silver modules.
  Notes: `just test-unit` was executed but blocked in this sandbox due `uv` dependency resolution requiring network/DNS.
  Notes: Targeted fallback validation passed with `.venv` tooling:
  - `./.venv/bin/pytest -q tests/unit/test_silver_transform.py tests/unit/test_silver_loader_helpers.py` -> 15 passed
  - `./.venv/bin/ruff check backend/silver scripts/build_silver.py tests/unit/test_silver_transform.py tests/unit/test_silver_loader_helpers.py` -> passed
- [ ] 4.2 Run `just build-silver` against a controlled sample and verify outputs.
  Notes: Command attempted with controlled sample env (`SILVER_LIMIT_ROWS=2000`, `SILVER_FETCH_SIZE=500`, `SILVER_CHUNK_SIZE=200`) but execution is blocked in this sandbox due denied connection to local PostgreSQL (`localhost:5432`, `Operation not permitted`).
  Notes: Local operator re-run command documented in `docs/evidence/silver_hardening_validation_2026-04-17.md`.
- [x] 4.3 Update docs/runbooks with hardened Silver behavior and operational expectations.
  Notes: Updated:
  - `docs/runbooks/local_development.md` (Silver controlled-sample workflow + expected telemetry)
  - `docs/runbooks/operations.md` (deterministic conflict keys, fail-fast semantics, parsing behavior, telemetry expectations)
  - `docs/evidence/silver_hardening_validation_2026-04-17.md` (validation evidence and blocked-command diagnostics)
