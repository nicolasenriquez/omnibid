# CI Workflow Runbook

## Purpose

Define the local CI pipeline and the order of checks for this repository.

## Fast Gate (default)

Use this in daily development:

```bash
just ci-fast
```

This runs:
1. `just lint`
2. `just type`
3. `just test-unit`

## Full Local CI Gate

Use before merge or major refactor:

```bash
just ci
```

This runs:
1. `just ci-fast`
2. `just black-check`
3. `just type-strict`
4. `just security`
5. `just test-integration`

## Individual Commands

- `just lint` -> Ruff lint checks
- `just type` -> MyPy checks (`backend/`, `scripts/`)
- `just black-check` -> Black formatting gate
- `just type-strict` -> Pyright + ty
- `just security` -> Bandit scan on `backend/`
- `just quality` -> alias to `just ci-fast`

## Fail-Fast Policy

- Any failing step blocks progression.
- No fallback to soft warnings for required quality gates.
- Fix the first failing gate, then rerun the full command.
