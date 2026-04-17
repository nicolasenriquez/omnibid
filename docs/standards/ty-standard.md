# ty Standard: Type Checking Configuration and Validation Gate

## Overview

This project uses **ty** as an additional high-performance type checker alongside MyPy and Pyright.

ty is designed for very fast checks and rich diagnostics, and helps surface typing issues with a different analysis model than MyPy/Pyright.

## Why ty

- Very fast project-scale type checking.
- Complementary diagnostics to MyPy and Pyright.
- Configurable rule severities and per-file overrides.
- First-class `pyproject.toml` support for repository-level policy.

## Gate Philosophy

ty is a required validation gate in this repository.

- Keep MyPy and Pyright as mandatory gates.
- Add ty as a third mandatory static type check.
- Keep ty configuration explicit and reproducible in `pyproject.toml`.

## Installation

Add ty as a dev dependency so all contributors use the same version:

```bash
uv add --dev "ty>=0.0.24"
```

Run via project environment:

```bash
uv run ty check backend
```

## Configuration

ty supports configuration in `pyproject.toml` under `[tool.ty.*]`.

Recommended repository baseline:

```toml
[tool.ty.environment]
python-version = "3.12"

[tool.ty.src]
include = ["backend"]
exclude = ["**/tests/**"]

[[tool.ty.overrides]]
include = ["backend/core/middleware.py"]

[tool.ty.overrides.rules]
invalid-argument-type = "ignore"
```

### Why these settings

- `python-version = "3.12"` keeps ty aligned with repo runtime target.
- `src.include = ["backend"]` scopes checks to the backend source tree.
- `src.exclude = ["**/tests/**"]` avoids current pytest-specific noise in ty while tests remain covered by MyPy/Pyright/Pytest.
- The narrow middleware override is a framework-typing interoperability exception for FastAPI/Starlette middleware registration.

## Usage

### Type gate command (blocking)

```bash
uv run ty check backend
```

### Advisory mode (non-blocking, when diagnosing)

```bash
uv run ty check backend --exit-zero
```

### Warn-level strictness (optional)

```bash
uv run ty check backend --error-on-warning
```

## Exit Codes

ty CLI exit behavior:

- `0`: no error-level diagnostics
- `1`: error-level diagnostics found
- `2`: invalid options/config or IO errors
- `101`: internal error

## Suppression Policy

Prefer repository config overrides for known framework-specific limitations and keep them narrow.

For line-level suppressions, use ty-specific comments with explicit rule codes:

```python
value = call()  # ty: ignore[invalid-argument-type]
```

Rules:
- suppress the smallest possible scope
- always include rule code
- document rationale in code/docs
- revisit exceptions when upgrading ty/frameworks

## Integration With Existing Repo Checks

Recommended validation order:

1. `uv run ruff check .`
2. `uv run black . --check --diff`
3. `uv run bandit -c pyproject.toml -r backend --severity-level high --confidence-level high`
4. `uv run mypy backend scripts`
5. `uv run pyright backend scripts`
6. `uv run ty check backend`
7. `uv run pytest -v`

For DB-dependent slices, run integration tests separately:

```bash
uv run pytest -v -m integration
```

## CI/CD and Hooks (Optional)

Example pre-commit hook:

```yaml
repos:
  - repo: local
    hooks:
      - id: ty-check
        name: ty check
        entry: uv run ty check backend
        language: system
        pass_filenames: false
```

## Troubleshooting

### "ty reports diagnostics not seen in MyPy/Pyright"

This is expected in some cases. Confirm whether it is:
- a real typing issue
- a third-party/framework typing limitation
- a rule-level policy decision requiring explicit override

### "ty fails because of tests"

This repository currently excludes `**/tests/**` for ty checks. Keep tests enforced through MyPy, Pyright, and pytest while ty coverage is expanded incrementally.

### "Environment/import resolution issues"

Ensure commands are run with `uv run` so ty sees the project environment and installed dependencies.

## Resources

- ty repository: https://github.com/astral-sh/ty
- ty docs: https://docs.astral.sh/ty/
- ty installation: https://docs.astral.sh/ty/installation/
- ty type checking guide: https://docs.astral.sh/ty/type-checking/
- ty configuration reference: https://docs.astral.sh/ty/reference/configuration/
- ty CLI reference: https://docs.astral.sh/ty/reference/cli/
- ty exit codes: https://docs.astral.sh/ty/reference/exit-codes/
- ty suppression: https://docs.astral.sh/ty/suppression/

---

**Last Updated:** 2026-03-21
