# Pipeline Reliability Hardening Validation

Date: 2026-04-22
Change: `pipeline-reliability-hardening-and-quality-gates`

## Scope

Validation evidence for:

- rollback hardening paths (raw/normalized)
- ORM/migration parity safety
- normalized quality-gate persistence and policy behavior
- operations API guardrails

## 1) Quality Gates and Targeted Checks (Task 5.1)

### Command: `just quality`

Result:

- `ruff check`: pass
- `mypy backend scripts`: pass
- `pytest -m "not integration"`: `46 passed, 2 skipped`
  - skipped files require optional `httpx` for API TestClient:
    - `tests/unit/test_health_api.py`
    - `tests/unit/test_operations_api.py`

### Targeted rollback + quality-gate checks

Command:

- `uv run pytest -q tests/unit/test_pipeline_failure_recovery.py tests/unit/test_normalized_quality_gates.py`

Result:

- `8 passed`

### Targeted API guardrail checks with `httpx`

Command:

- `uv run --with httpx python -m pytest -q tests/unit/test_operations_api.py`

Result:

- `5 passed`

### Migration parity sanity (autogenerate)

Command:

- `uv run alembic revision --autogenerate -m "tmp_reliability_parity_check"`

Result:

- generated temporary revision `915449131776_tmp_reliability_parity_check.py`
- `upgrade()` and `downgrade()` contained only `pass`
- no unintended schema churn detected
- temporary revision removed after inspection

## 2) Controlled Pipeline Runs (Task 5.2)

Controlled sample dataset root:

- `data/samples/20260422_reliability_gate/`

State file used to force incremental processing only for newly ingested rows:

- `data/runtime/normalized_build_state_20260422_reliability_gate.json`

### Raw controlled run

Command:

- `DATASET_ROOT=<sample_root> CHUNK_SIZE=100 LIMIT_FILES=0 UV_NO_SYNC=1 just raw-ingest-fast`

Observed output:

- `OK ..._licitacion.csv: processed=5 accepted=5 deduplicated=5 inserted_delta=5 existing_or_updated=0`
- `OK ..._orden_compra.csv: processed=5 accepted=5 deduplicated=5 inserted_delta=5 existing_or_updated=0`

Runtime log:

- `docs/evidence/runtime_logs/2026-04-22_pipeline_raw_controlled.log`

### Normalized controlled run

Command:

- `NORMALIZED_STATE_PATH=<state_path> NORMALIZED_DATASET=all NORMALIZED_FETCH_SIZE=100 NORMALIZED_CHUNK_SIZE=50 NORMALIZED_LIMIT_ROWS=0 UV_NO_SYNC=1 just normalized-build`

Observed output:

- `licitacion`: processed `5`, all entities accepted/deduplicated, rejected `0`
- `orden_compra`: processed `5`, all entities accepted/deduplicated, rejected `0`

Runtime log:

- `docs/evidence/runtime_logs/2026-04-22_pipeline_normalized_controlled.log`

### Post-run DB evidence snapshot

Observed:

- source files loaded with status `loaded` (2 files)
- ingestion batches `completed` with `total_rows=5`, `loaded_rows=5`, `rejected_rows=0`
- normalized pipeline runs `completed` with `quality_gate` metadata persisted:
  - `policy_version=quality_gate_policy_v1`
  - thresholds include `max_error_rate=0.005`
  - `decision=passed`
  - `decision_reason=no_quality_issues`
- `data_quality_issues` count for those runs: `0`

## 3) Readiness Statement (Task 5.3)

The reliability-hardening slice is validated for:

- transaction rollback safety paths
- ORM/migration parity safety
- deterministic normalized quality-gate policy persistence
- API limit guardrails and summary scaling strategy

This change is ready to continue in strict stage-gated sequence.
