# Engineering Standards

## Core Principles

- TDD-first for domain logic and contracts.
- Fail-fast behavior for invalid configuration, malformed inputs, and schema drift.
- Typed Python for core logic.
- Explicit SQLAlchemy models, keys, and constraints.
- Structured logs with `run_id` and `step_name`.
- No hidden transformations.
- Alembic as schema source of truth.
- `uv` as dependency/runtime standard.
- Justfile as operator interface.

## TDD Workflow

1. Write a failing unit test for expected behavior (`RED`).
2. Implement minimal code to pass (`GREEN`).
3. Refactor while keeping tests green (`REFACTOR`).
4. Run local gate before commit: `just quality`.

## Fail-Fast Rules

- Ingestion must fail when required columns are missing.
- Runtime must fail if `DATABASE_URL` points to a test database.
- Integration tests must fail if `TEST_DATABASE_URL` is missing or equals `DATABASE_URL`.
- Pipelines must mark run and step status as `failed` with explicit error payloads.

## Quality Gates

- Lint: `just lint`
- Type: `just type`
- Unit tests: `just test-unit`
- Local CI-fast gate: `just backend-ci-fast`
- Local CI gate: `just backend-ci`

## Reference Standards

- `docs/standards/ruff-standard.md`
- `docs/standards/black-standard.md`
- `docs/standards/mypy-standard.md`
- `docs/standards/pyright-standard.md`
- `docs/standards/ty-standard.md`
- `docs/standards/pytest-standard.md`
- `docs/standards/bandit-standard.md`
- `docs/standards/logging-standard.md`
- `docs/standards/postgres-standard.md`
- `docs/standards/pandas-standard.md`
