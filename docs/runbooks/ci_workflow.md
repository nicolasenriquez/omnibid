# CI Workflow Runbook

## Purpose

Define the local CI pipeline and the order of checks for this repository.

For GitHub-hosted CI governance and rollout procedure, see:

- `docs/standards/github-actions-ci-cd-standard.md`
- `docs/runbooks/github-actions-ci-container-first.md`

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
2. `just type-strict`
3. `just security`
4. `just test-integration`

## GitHub Required Checks (Remote)

The remote branch-protection checks mirror local policy:

1. `Secret Scan`
2. `Backend Gates`
3. `Frontend Gates`

## Individual Commands

- `just lint` -> Ruff lint checks
- `just type` -> MyPy checks (`backend/`, `scripts/`)
- `just black` -> Black formatting command
- `just type-strict` -> Pyright + ty
- `just security` -> Bandit scan on `backend/`
- `just quality` -> alias to `just ci-fast`

## Fail-Fast Policy

- Any failing step blocks progression.
- No fallback to soft warnings for required quality gates.
- Fix the first failing gate, then rerun the full command.
