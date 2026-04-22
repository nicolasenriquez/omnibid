# Engineering Standards

## Core Principles

- SDD-first for framework/library/platform behavior.
- TDD-first for domain logic and contracts.
- Fail-fast behavior for invalid configuration, malformed inputs, and schema drift.
- Typed Python for core logic.
- Explicit SQLAlchemy models, keys, and constraints.
- Structured logs with `run_id` and `step_name`.
- No hidden transformations.
- Alembic as schema source of truth.
- `uv` as dependency/runtime standard.
- Justfile as operator interface.

## SDD Workflow

1. Identify the exact behavior/API to implement.
2. Consult the official source first (framework docs, language docs, or vendor docs).
3. Record the reference in `docs/references/` using the SDD template.
4. Implement based on the documented contract.
5. Validate with tests and quality gates.

SDD rules:

- Prefer primary official documentation over blogs/posts.
- If sources conflict, the official source wins.
- If no official source exists, document the fallback rationale explicitly.
- Keep references actionable (URL + section/topic + decision taken).

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
- Local CI-fast gate: `just ci-fast`
- Local CI gate: `just ci`

## Reference Standards

### SDD References

- `docs/references/sdd-standard.md`
- `docs/references/sdd-official-sources-registry.md`
- `docs/references/sdd-reference-template.md`

### Library/Module Standards

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
