# RTK.md

Runtime Toolkit conventions for this repository.

## Command Interface

- Prefer `just <recipe>` for all common workflows.
- Use `uv run ...` for direct tool execution.
- Do not use `pip` for dependency operations in this repo.

## Canonical Workflows

- Setup: `just setup`
- DB + migrations: `just db-bootstrap`
- Bronze: `just pipeline-1-bronze`
- Silver (from Bronze already loaded): `just pipeline-2-silver-from-bronze`
- End-to-end Bronze -> Silver: `just pipeline-all`
- Quality: `just quality`
- CI-fast local: `just backend-ci-fast`
- CI local full: `just backend-ci`

## Guardrails

- No destructive git operations.
- No hidden fallback behavior for missing required config/services.
- Fail fast with explicit error context.
