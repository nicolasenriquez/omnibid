# Changelog

## 2026-04-30

### Added

- Manual CSV append workflow for ChileCompra procurement files through `/licitaciones`, including:
  - explicit dataset selector for `licitacion` and `orden_compra`
  - preflight validation before writes
  - staged server-side file token flow
  - process/status endpoints
  - deterministic telemetry for raw accepted rows, canonical inserted delta, duplicates, rejected rows, normalized rows, and Silver rows

### Changed

- Opportunity Workspace header now separates read-only exploration from operator upload actions with a green `Cargar CSV` CTA.
- Opportunity Workspace upload sheet now supports dataset selection, drop zone/file picker, duplicate warnings, retry/cancel states, and terminal result summaries.
- Opportunity Workspace header snapshot and KPI composition were refined for clearer hierarchy and denser operational scanning.
- Expanded evidence panel was restyled into a flatter document-like summary while preserving existing evidence fields and read-only detail actions.

### Documentation

- Added manual CSV append runbook guidance covering dataset semantics, bounded processing defaults, dedupe expectations, staged-file behavior, and recovery steps.
