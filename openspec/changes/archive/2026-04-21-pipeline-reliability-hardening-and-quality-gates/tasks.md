## 1. Transaction Safety Hardening

- [x] 1.1 Add explicit rollback-first exception handling in `scripts/ingest_raw.py` failure paths.
- [x] 1.2 Add explicit rollback-first exception handling in `scripts/build_normalized.py` failure paths.
- [x] 1.3 Add tests that simulate mid-run SQL failure and verify clean failed-state persistence after rollback.

## 2. ORM and Migration Parity

- [x] 2.1 Audit operational/raw migration-defined indexes and constraints against current model metadata.
- [x] 2.2 Update `backend/models/operational.py` and `backend/models/raw.py` to declare required index parity metadata.
- [x] 2.3 Run migration parity sanity checks and ensure no unintended schema churn is introduced.

## 3. Normalized Quality Gates

- [x] 3.1 Implement normalized quality issue persistence to `data_quality_issues` with issue typing and severity.
- [x] 3.2 Implement `quality_gate_policy_v1` defaults (`critical error exists` OR `error_rate > 0.5%` => fail; otherwise warn/pass).
- [x] 3.3 Add tests for persisted quality issues and threshold breach behavior.
- [x] 3.4 Persist quality-gate decision metadata (`policy_version`, thresholds, `decision_reason`) in run metadata.

## 4. Operations API Guardrails

- [x] 4.1 Add bounded `limit` validation for `/runs` and `/files` endpoints.
- [x] 4.2 Implement/document scalable dataset summary behavior for large-table operation with no new precomputed summary table in this change.
- [x] 4.3 Add/adjust API tests for limit validation and summary behavior contract.
- [x] 4.4 Document follow-up proposal requirement for precomputed dataset summary storage.

## 5. Validation and Evidence

- [x] 5.1 Run quality gates (`just quality`) and targeted integration checks for rollback/parity/quality-gate paths.
- [x] 5.2 Execute controlled `pipeline-raw` and `pipeline-normalized` runs and capture reliability evidence.
- [x] 5.3 Update runbooks/evidence docs and confirm readiness to start implementation apply phase.
