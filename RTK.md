# RTK.md

Runtime Toolkit conventions for this repository.

## Command Interface

- Prefer `just <recipe>` for all common workflows.
- Use `uv run ...` for direct tool execution.
- Do not use `pip` for dependency operations in this repo.

## Canonical Workflows

- Setup: `just setup`
- DB + migrations: `just db-bootstrap`
- Raw: `just pipeline-raw`
- Normalized (from Raw already loaded): `just pipeline-normalized`
- End-to-end Raw -> Normalized: `just pipeline-full`
- Quality: `just quality`
- CI-fast local: `just ci-fast`
- CI local full: `just ci`

## Guardrails

- No destructive git operations.
- No hidden fallback behavior for missing required config/services.
- Fail fast with explicit error context.
