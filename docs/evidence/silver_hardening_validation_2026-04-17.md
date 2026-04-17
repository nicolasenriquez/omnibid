# Silver Hardening Validation (Tasks 4.1-4.2)

Date: 2026-04-17

## Scope

- Validate hardened Silver behavior with test and lint checks.
- Attempt controlled sample execution of `build-silver`.
- Record blockers observed in current execution sandbox.

## 4.1 Validation Commands

### Command

```bash
just test-unit
```

### Result

- **Blocked in this sandbox** due `uv run` dependency resolution hitting network/DNS.
- Error observed while resolving `pytest` from `https://pypi.org/simple/pytest/`.

### Fallback executed

```bash
./.venv/bin/pytest -q tests/unit/test_silver_transform.py tests/unit/test_silver_loader_helpers.py
```

Result:

- **15 passed**

Additional targeted lint check:

```bash
./.venv/bin/ruff check backend/silver scripts/build_silver.py tests/unit/test_silver_transform.py tests/unit/test_silver_loader_helpers.py
```

Result:

- **All checks passed**

## 4.2 Controlled Sample Build Command

### Command attempted

```bash
UV_NO_SYNC=1 \
SILVER_DATASET=all \
SILVER_LIMIT_ROWS=2000 \
SILVER_FETCH_SIZE=500 \
SILVER_CHUNK_SIZE=200 \
just build-silver
```

### Result

- **Blocked in this sandbox** due denied TCP connection to local PostgreSQL (`localhost:5432`, `Operation not permitted`).
- This is an environment restriction of the execution sandbox, not an application-level loader exception.

## Operator Re-run Checklist (Local Machine)

Run these directly in your local shell (outside restricted sandbox):

1. `just test-unit`
2. `UV_NO_SYNC=1 SILVER_DATASET=all SILVER_LIMIT_ROWS=2000 SILVER_FETCH_SIZE=500 SILVER_CHUNK_SIZE=200 just build-silver`
3. Confirm Silver output includes:
   - licitaciones progress + summary
   - ordenes_compra progress + summary
   - rejection and upsert counters per entity
