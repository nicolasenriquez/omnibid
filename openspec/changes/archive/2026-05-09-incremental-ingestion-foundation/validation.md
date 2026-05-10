# Validation Evidence

Date: 2026-05-07

## 1) Canonical container-first path

Command:

```powershell
rtk just test-unit
```

Result:

- Passed after global test-surface fixes:
  - `213 passed, 1 deselected in 2.12s`

Applied global fixes:

- include `config/` in Docker `tools` and `runtime` stages so NLP config files are present in test containers
- ignore temporary `tests/_tmp_test_db_guard` path in pytest collection

## 2) Host-local fallback (same backend scope, targeted)

Command:

```powershell
rtk powershell -NoProfile -Command ".venv/Scripts/python.exe -m pytest -q tests/unit/test_ingestion_queue_foundation_tdd.py tests/unit/test_normalized_loader_helpers.py tests/unit/test_core_config.py"
```

Result:

- `35 passed, 1 warning in 0.62s`
- Warning was pytest cache path creation (`.pytest_cache`) and does not affect test correctness.

## 3) Coverage intent for this change

- Queue claim semantics (`FOR UPDATE SKIP LOCKED`)
- Retry/dead-letter transitions (2 total attempts, 120s retry delay)
- Ingestion-unit lineage payload contract
- Complete-only merge semantics (`no overwrite with null/blank`)
