# Data Engineering Hardening Plan (Waterfall)

Date: 2026-04-21

## Objective

Increase pipeline reliability and schema consistency before normalized domain expansion and Gold implementation.

## Execution Mode

Strict waterfall:

1. complete P0 gates
2. validate
3. unlock P1
4. validate
5. unlock domain expansion

No stage starts before the previous stage is green.

## P0 - Reliability Critical

### P0.1 Transaction rollback hardening

Scope:

- `scripts/ingest_raw.py`
- `scripts/build_normalized.py`

Goal:

- guarantee `session.rollback()` before reusing session state after SQL exceptions
- preserve explicit failed statuses for run/step/batch

Definition of done:

- integration test proves clean failure + retry path
- no aborted-session side effects after simulated DB error

### P0.2 ORM/Migration parity hardening

Scope:

- `backend/models/operational.py`
- `backend/models/raw.py`
- Alembic migration metadata review

Goal:

- align model metadata with actual migrated indexes/constraints
- prevent hidden schema drift in future revisions

Definition of done:

- declared indexes in models match migration intent for operational/raw tables
- autogenerate sanity check does not suggest unintended schema churn

## P1 - Operational Quality and Efficiency

### P1.1 Normalized quality issue persistence + thresholds

Scope:

- operational table `data_quality_issues`
- normalized build path + quality gate policy

Goal:

- persist quality issues by type/severity/entity
- enforce threshold-based warning/failure policy

Definition of done:

- controlled run persists issues
- threshold breach marks pipeline status as failed deterministically

### P1.2 API operational guardrails

Scope:

- `backend/api/routers/operations.py`

Goal:

- add bounded `limit` validation on list endpoints
- avoid expensive full-table summaries for frequent operational reads
- defer precomputed summary storage to a dedicated follow-up proposal

Definition of done:

- endpoint limits are bounded
- summary strategy documented and verified for large-table behavior
- follow-up proposal requirement is documented for precomputed summary persistence

## P2 - Domain Expansion Unlock

After P0 and P1 are green:

- proceed to normalized domain expansion (buyers/suppliers/categories and stronger relational contracts)

## Validation Baseline

- `just quality`
- targeted integration tests for transaction and DB behavior
- controlled `pipeline-raw` and `pipeline-normalized` evidence capture
