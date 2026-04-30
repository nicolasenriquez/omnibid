## 1. Investigation and Contract Freeze

- [x] 1.1 Inspect current raw ingestion, normalized/Silver incremental state, and source-file lineage paths.
  Notes: focus on `scripts/ingest_raw.py`, `scripts/build_normalized.py`, `backend/ingestion/contracts.py`, and `backend/models/operational.py`.
  Acceptance: exact reusable functions and missing seams for single-file processing are documented before code edits.
- [x] 1.2 Verify duplicate behavior across Raw, Normalized, and Silver for a renamed file with repeated business rows.
  Notes: raw may accept rows under a new source file while normalized/Silver should dedupe by business keys; this distinction must be visible to operators.
  Acceptance: test plan identifies where duplicates are skipped and where they are retained as lineage.
- [x] 1.3 Freeze API and UI labels for dataset selection and upload states.
  Notes: selected dataset, not filename, determines `licitacion` vs `orden_compra`.
  Notes: use `C:\Users\nenri\Downloads\2026-4 (1)\lic_2026-4.csv` as the motivating licitaciones fixture shape when documenting the filename-independent behavior.
  Notes: use `C:\Users\nenri\Downloads\2026-4\2026-4.csv` as the motivating orden-compra fixture shape because the file name is dataset-ambiguous.
  Acceptance: Spanish labels and API enum values are explicit.

## 2. Backend Manual Intake

- [x] 2.1 Add focused tests for CSV preflight validation.
  Notes: cover wrong extension, empty file, missing required columns, wrong selected dataset, path-like filename, and valid semicolon-delimited CSV.
  Notes: include a fixture modeled after `lic_2026-4.csv`: non-canonical name, semicolon delimiter, quoted header, and valid licitacion required columns.
  Notes: include a fixture modeled after `2026-4.csv`: dataset-ambiguous name, semicolon delimiter, quoted header, and valid orden-compra required columns.
  Acceptance: failing tests describe required validation behavior before implementation.
- [x] 2.2 Implement controlled upload staging and preflight endpoint.
  Notes: sanitize names, compute hash, enforce size limit, validate required columns, and return a short-lived file token.
  Acceptance: invalid files fail before writes; valid files return row count and dataset summary.
- [x] 2.3 Implement process and status endpoints.
  Notes: status must expose step, terminal state, telemetry, and actionable errors without returning raw file contents.
  Acceptance: process can be started from a preflight token and observed until success/failure.

## 3. Scoped Pipeline Processing

- [x] 3.1 Add or expose single-file raw ingest support.
  Notes: reuse existing `SourceFile`, `IngestionBatch`, `PipelineRun`, `PipelineRunStep`, contract validation, and raw insert code.
  Acceptance: only the staged uploaded file is ingested.
- [x] 3.2 Add bounded normalized/Silver processing for the selected dataset and uploaded raw scope.
  Notes: do not run all historical rows by default; use existing incremental/raw-id/source-file boundaries where safe.
  Acceptance: adding an April licitaciones file does not replay all historical licitaciones by default.
- [x] 3.3 Persist and return deterministic telemetry for inserted, skipped, duplicate/existing, rejected, normalized, and Silver outcomes.
  Notes: metrics should match existing telemetry naming where practical.
  Acceptance: UI can distinguish accepted raw rows from canonical inserted deltas.

## 4. Workspace UI and Visual Polish

- [ ] 4.1 Run current-state critique/audit for header, KPIs, pulse chips, expanded evidence panel, and action affordances.
  Notes: `/impeccable` is installed under `.codex/skills/impeccable/`; run its preflight and command-reference gates before UI file edits.
  Acceptance: visual issues are listed before CSS/component edits.
- [ ] 4.2 Add green `Cargar CSV` entry point to the workspace header.
  Notes: keep Explorer/Radar actions read-only; upload is a separate operator flow.
  Acceptance: CTA is visually primary but does not crowd existing snapshot metrics.
- [ ] 4.3 Build upload modal/sheet with drop zone, file picker, dataset selector, preflight summary, confirm action, progress, and result states.
  Notes: include disabled, loading, error, duplicate warning, retry, and cancel paths.
  Acceptance: user must choose dataset before processing.
- [ ] 4.4 Improve premium header and KPI visualization.
  Notes: use the reference for composition and hierarchy, not literal copying; keep readable contrast and compact operational density.
  Acceptance: header snapshot and pulse KPIs remain complete, clearer, and responsive.
- [ ] 4.5 Improve expanded evidence panel look and feel.
  Notes: preserve all relevant KPIs and evidence; use document-like hierarchy for title, status, dates, amount, buyer, lines, offers, OC evidence, and certainty.
  Acceptance: existing evidence is not removed or made ambiguous.

## 5. Documentation and Validation

- [ ] 5.1 Update runbooks for manual CSV append.
  Notes: document dataset selector semantics, no-full-reprocess default, dedupe expectations, staged-file behavior, and recovery.
  Acceptance: docs explain how to safely append one file.
- [ ] 5.2 Update `CHANGELOG.md`.
  Notes: required because behavior, operator workflow, and UI change.
  Acceptance: entry summarizes manual append and workspace polish.
- [ ] 5.3 Run focused backend validation.
  Notes: prefer container-backed commands per repo policy; use host fallback only if Docker path is blocked.
  Acceptance: preflight, process, idempotency, and scoped processing tests pass.
- [ ] 5.4 Run frontend validation and browser smoke.
  Notes: validate typecheck/lint/build and inspect `/licitaciones` in the browser.
  Acceptance: upload flow, header/KPIs, expanded evidence, focus states, and responsive layout are checked.
