## Why

Operators need a safe way to append a small, manually supplied ChileCompra CSV file into the existing pipeline without replaying the full historical dataset. The current pipeline already supports deterministic raw ingestion, normalized/Silver builders, lineage, and idempotent database writes, but the operator workflow assumes files are discovered from the mounted dataset folders. That is risky for late monthly files, corrected file names, or ad hoc evidence drops because the user must place files manually and trust that the filename and directory imply the right dataset.

The Opportunity Workspace also needs a tighter premium SaaS visual pass based on the supplied references: a stronger header, clearer KPI hierarchy, a green manual-upload entry point, and a more polished expanded evidence section while preserving the current read-only opportunity-browsing boundary.

## What Changes

- Add a manual CSV append workflow for:
  - `licitacion`
  - `orden_compra`
- Require the user to choose the target pipeline/dataset explicitly before processing.
- Validate CSV format and required columns before any write.
- Stage uploaded files into a controlled server-side intake area with canonical naming and metadata.
- Reuse the existing raw ingestion, normalized build, Silver build, lineage, telemetry, and idempotent upsert semantics.
- Process only the uploaded file and its downstream affected rows; do not rerun the full historical dataset by default.
- Add UI affordances:
  - green upload button in the `/licitaciones` workspace header.
  - modal or sheet with drop zone and file picker.
  - pipeline selector for `Licitaciones` vs `Ordenes de compra`.
  - preflight summary before commit.
  - post-run status with inserted, skipped/duplicate, rejected, and normalized/Silver outcome counts.
- Polish the workspace header, KPI snapshot, pulse metrics, and expanded evidence panel using a premium operational SaaS style.

## Capabilities

### New Capabilities

- `manual-csv-append-ingestion`: Operator-driven CSV intake that appends one selected file into the existing pipeline with explicit dataset selection, validation, lineage, idempotent deduplication, and bounded downstream processing.
- `opportunity-workspace-premium-polish`: Visual and interaction polish for the `/licitaciones` header, KPI visualization, upload entry point, and expanded evidence section.

### Modified Capabilities

- `opportunity-workspace-premium-frontend`: Extend the existing read-only workspace visual system with manual upload entry affordances while keeping opportunity browsing and Radar actions non-mutating unless the user enters the upload flow.

## Impact

- Affected backend areas:
  - `backend/api/routers/` for manual upload/preflight/run/status endpoints.
  - `backend/ingestion/` for scoped file intake helpers and contract validation.
  - `scripts/ingest_raw.py` for single-file or manifest-scoped ingestion support if not already cleanly reusable.
  - `scripts/build_normalized.py` for scoped incremental downstream processing by dataset/source-file boundary.
  - `backend/models/operational.py` or a small Alembic migration if manual intake job state cannot be represented safely with existing operational tables.
- Affected frontend areas:
  - `client/app/licitaciones/`
  - `client/src/features/opportunity-workspace/`
  - `client/src/lib/api/`
  - `client/src/types/`
  - `client/src/styles/workspace.css`
- Affected contracts:
  - explicit dataset selection is authoritative; uploaded filename is metadata only.
  - raw and normalized/Silver writes remain idempotent.
  - list/Radar opportunity views stay notice-level and read-only.
- Documentation impact:
  - update operator runbooks for manual CSV append behavior, validation, dedupe expectations, and recovery.
  - update `CHANGELOG.md` when implemented.
- Operational impact:
  - file uploads introduce trust, size, content-type, path, and retry boundaries.
  - Docker-first backend runtime remains canonical for validation.
