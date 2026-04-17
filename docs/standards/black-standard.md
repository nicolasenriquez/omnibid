# Black Standard: Formatting Configuration and Validation Gate

## Overview

This document defines how to use **Black** as a deterministic Python formatting tool in this repository.

Black should be used to keep style changes mechanical, reproducible, and separate from logic or architecture changes.

## Why Black

- Deterministic formatting with minimal style debates.
- Stable `--check` gate for CI and local validation.
- Clear failure semantics for formatting drift.
- Widely adopted ecosystem integrations.

## Gate Philosophy

Black is a required validation gate in this repository.

- Treat Black as formatter authority for Python files.
- Keep Ruff focused on linting/security/type-adjacent rules.
- Avoid dual mandatory formatter gates (`black --check` and `ruff format --check`) unless explicitly running a temporary migration.

## Configuration

Black reads configuration from `pyproject.toml` under `[tool.black]`.

Recommended baseline for this repository:

```toml
[tool.black]
line-length = 100
target-version = ["py312"]
include = "\\.pyi?$"
exclude = '''
/(
    \.git
  | \.venv
  | \.mypy_cache
  | \.pytest_cache
  | \.ruff_cache
  | __pycache__
)/
'''
```

Notes:
- Keep `line-length` aligned with Ruff settings.
- Keep exclusions aligned with tooling caches and generated artifacts.

## Usage

### Format in place

```bash
uv run black .
```

### Check mode (validation gate)

```bash
uv run black . --check
```

### Check with diff output

```bash
uv run black . --check --diff
```

### Pin version in validation

```bash
uv run black . --check --required-version 26
```

## Exit Codes

Black check behavior:

- `0`: no changes required
- `1`: files would be reformatted
- `123`: internal tool error

These semantics are useful for strict CI gating and clear failure diagnosis.

## Integration With Ruff

Ruff and Black can be compatible when line length is consistent.

Recommended split when both are enabled:

- `uv run ruff check .` for lint/security/import/order rules
- `uv run black . --check --diff` for formatting gate

To avoid formatting drift:
- Do not require both `black --check` and `ruff format --check` as permanent hard gates.
- Keep `E501` policy aligned with formatter behavior.

## Suggested Validation Sequence

1. `uv run ruff check .`
2. `uv run black . --check --diff`
3. `uv run bandit -c pyproject.toml -r backend --severity-level high --confidence-level high`
4. `uv run mypy backend scripts`
5. `uv run pyright backend scripts`
6. `uv run ty check backend`
7. `uv run pytest -v`

Add integration/runtime checks only when scope requires them.

## CI/CD and Hooks (Optional)

Example pre-commit hook:

```yaml
repos:
  - repo: https://github.com/psf/black-pre-commit-mirror
    rev: "26.3.0"
    hooks:
      - id: black
```

Example GitHub Actions reference:

```yaml
- uses: actions/checkout@v5
- uses: psf/black@stable
```

## Troubleshooting

### "Black and Ruff disagree on some lines"

This can happen on edge cases. Choose one formatter authority for blocking checks and keep the other non-blocking.

### "Formatting keeps changing across machines"

Pin Black version in tool dependencies and optionally use `--required-version` in checks.

### "Black fails on Python 3.12.5 before checking files"

Python 3.12.5 has a known runtime issue that Black rejects for AST safety checks. Use Python `3.12.6+` (repository baseline is pinned via `.python-version`) and re-run:

```bash
uv run black . --check --diff
```

### "Black changed too many files"

Run formatting in a dedicated commit before logic changes to keep reviews focused.

## Resources

- Black basics: https://black.readthedocs.io/en/latest/usage_and_configuration/the_basics.html
- Black with other tools: https://black.readthedocs.io/en/latest/guides/using_black_with_other_tools.html
- Black source control integration: https://black.readthedocs.io/en/stable/integrations/source_version_control.html
- Ruff FAQ (Black compatibility context): https://docs.astral.sh/ruff/faq/

---

**Last Updated:** 2026-03-21
