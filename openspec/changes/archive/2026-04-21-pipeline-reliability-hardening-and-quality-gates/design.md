## Context

The repository completed telemetry reconciliation and now reports deterministic raw/normalized load metrics. The next stage requires reliability hardening before any normalized domain expansion: ETL failure-path transaction safety, schema/ORM parity, persisted quality gates, and API operational guardrails. Current scripts and metadata show that these concerns span multiple modules (`scripts/`, `backend/models/`, `backend/api/`, migrations), so this change is cross-cutting and should be implemented with strict stage gates.

## Goals / Non-Goals

**Goals:**
- Guarantee safe rollback semantics in ETL exception paths before any failure-state writes.
- Ensure operational/raw ORM metadata reflects migrated indexes and constraints.
- Persist normalized data quality issues and enforce deterministic threshold-based fail/warn behavior.
- Add API guardrails for list limits and define a scalable summary strategy for large tables.
- Provide validation evidence and runbook updates for operators.

**Non-Goals:**
- Redesign normalized domain model entities (buyers/suppliers/categories).
- Implement Gold/business-layer outputs.
- Replace current pipeline architecture with a new orchestration system.

## Decisions

1. **Rollback-first failure handling in ETL scripts**
   - Decision: enforce `session.rollback()` immediately inside ETL exception paths before reusing the same session for failure-state persistence.
   - Why: SQLAlchemy aborted transactions can poison subsequent writes if rollback is skipped.
   - Alternative considered: separate session for failure-state writes only; rejected for now due to extra complexity and no immediate need.

2. **Model/migration parity as source-of-truth hardening**
   - Decision: declare operational/raw indexes in ORM metadata to match migrated schema; add migration adjustment only when true parity gaps are found in runtime DB.
   - Why: avoids schema drift confusion and unstable autogenerate output.
   - Alternative considered: keep indexes migration-only; rejected because it weakens metadata readability and maintainability.

3. **Threshold-gated quality persistence in normalized flow**
   - Decision: implement `quality_gate_policy_v1` and persist policy metadata per run. Policy defaults:
     - `FAIL` when any `severity=error` issue exists for critical issue types.
     - `FAIL` when dataset-level `error_rate > 0.5%`.
     - `WARN` when only warning issues exist and fail conditions are not met.
     - Persist `policy_version`, thresholds, and `decision_reason` in run metadata.
   - Why: makes quality checks auditable and operationally enforceable.
   - Alternative considered: log-only quality checks; rejected because they do not create enforceable run gates.

4. **Bounded operational API responses**
   - Decision: apply bounded `limit` validation to `/runs` and `/files`; in this change, implement only documented scalable usage policy for summary reads and defer precomputed summary storage to a follow-up change.
   - Why: prevents expensive unbounded reads and protects API stability under larger datasets.
   - Alternative considered: keep current behavior with operator discipline; rejected due to weak guardrails.
   - Alternative considered: implement a new precomputed summary table in this slice; rejected to keep this change focused on reliability P0/P1 gates.

## Risks / Trade-offs

- [Risk] Rollback placement changes may alter current failure logging order.
  - Mitigation: add integration tests that assert both rollback safety and persisted failed statuses.

- [Risk] ORM parity updates may surface latent migration inconsistencies.
  - Mitigation: run schema sanity checks and targeted migration validation before merge.

- [Risk] Threshold rules may fail runs that currently pass.
  - Mitigation: start with conservative defaults and explicit documented thresholds.

- [Risk] API caps may affect existing consumers requesting large limits.
  - Mitigation: document bounds and provide pagination guidance in runbooks.

## Migration Plan

1. Implement and test ETL rollback hardening in scripts.
2. Apply ORM parity updates and validate migration metadata behavior.
3. Implement quality issue persistence and threshold gate evaluation.
4. Add API limit caps and summary strategy updates.
5. Run full quality checks and controlled pipeline evidence capture.
6. Rollback plan: revert this change set and restore previous behavior if thresholds or parity checks cause unstable operational outcomes.

## Open Questions

None.
