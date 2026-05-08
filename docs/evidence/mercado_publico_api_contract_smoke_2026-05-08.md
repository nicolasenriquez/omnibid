# Mercado Publico API Contract Smoke Validation

Date: 2026-05-08  
Change: `mercado-publico-api-notice-ingestion`

## Scope

Validate backend API-lane readiness for Mercado Publico notice ingestion with:

- Docker-first operator entrypoint execution
- lint and type gates
- unit test coverage for client/schema/store/sync/script paths

## Commands Run

1. Lint gate:

```bash
just lint
```

Result:
- `All checks passed!`

2. Type gate:

```bash
just type
```

Result:
- `Success: no issues found in 73 source files`

3. Unit tests:

```bash
just test-unit
```

Result:
- `245 passed, 1 deselected`

4. API smoke (dry run, Docker):

```bash
just mp-api-smoke
```

Result:
- `[mp-api-sync] dry-run ok mode=active-discovery ...`

## Notes

- Smoke validation confirms the operator entrypoint and Docker recipe wiring for `scripts/fetch_mp_api.py`.
- Secret-handling and request/payload contract behavior are covered by unit tests in:
  - `tests/unit/test_mercado_publico_client.py`
  - `tests/unit/test_mercado_publico_schemas.py`
  - `tests/unit/test_mercado_publico_store.py`
  - `tests/unit/test_mercado_publico_sync.py`
  - `tests/unit/test_fetch_mp_api_script.py`
