## 1. Telemetry Contract and Baseline

- [x] 1.1 Define canonical metric taxonomy and formulas for raw and normalized runs.
- [x] 1.2 Capture a baseline sample showing current counter drift to validate improvement criteria.
- [x] 1.3 Confirm reconciliation query scope and performance constraints for large datasets.
- [x] 1.4 Define bounded logging policy (default checkpoint interval, completion summaries, and debug verbosity guardrails).

## 2. Raw Ingestion Reconciliation

- [x] 2.1 Implement deterministic raw metrics in `scripts/ingest_raw.py` without relying on `rowcount` for conflict-aware inserts.
- [x] 2.2 Persist and log the new raw metrics through existing operational metadata paths.
- [x] 2.3 Add/adjust tests for duplicate-heavy reruns and no-op reruns.

## 3. Normalized Reconciliation

- [x] 3.1 Replace rowcount-based normalized summary counters with deterministic flow/storage metrics in `scripts/build_normalized.py`.
- [x] 3.2 Update normalized progress/summary output naming to match the telemetry contract.
- [x] 3.3 Add/adjust tests for accepted, deduplicated, and inserted-delta metric behavior.
- [x] 3.4 Ensure normalized logging remains checkpoint-based by default and does not emit row-level logs in normal mode.

## 4. Documentation and Validation

- [x] 4.1 Update runbooks and evidence templates with metric definitions and operator validation steps.
- [x] 4.2 Run targeted quality checks (`test-unit`, lint, type) for touched modules.
- [x] 4.3 Execute controlled sample runs (`pipeline-raw`, `pipeline-normalized`) and capture reconciliation evidence.
- [x] 4.4 Compare runtime and log-volume baseline vs updated implementation to confirm no material efficiency regression.
