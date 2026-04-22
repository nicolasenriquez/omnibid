## Why

The pipeline now has deterministic telemetry, but it still has reliability gaps that can cause operational failures under load or during exception paths. Before Silver domain expansion, we need to harden transaction handling, schema/ORM parity, quality gates, and operational API guardrails.

## What Changes

- Add explicit transaction rollback guarantees in raw and normalized pipeline failure paths.
- Align operational/raw ORM metadata with migrated indexes and constraints to avoid schema drift.
- Persist normalized data quality issues and enforce configurable threshold-based fail/warn gating.
- Add operational API guardrails for bounded list limits and a scalable dataset summary strategy.
- Extend runbooks and evidence workflow for reliability-hardening validation.

## Capabilities

### New Capabilities
- `pipeline-reliability-quality-gates`: Hardening capability covering ETL transaction safety, schema parity, normalized quality gates, and operational API guardrails in strict waterfall order.

### Modified Capabilities
- None.

## Impact

- Affected code: `scripts/ingest_raw.py`, `scripts/build_normalized.py`, `backend/models/operational.py`, `backend/models/raw.py`, `backend/api/routers/operations.py`.
- Affected migrations: potential Alembic revision for model/index parity where required.
- Affected docs: runbooks, evidence templates, and roadmap alignment docs.
- No external API contract break is required; list endpoints keep the same shape with safer bounds.
