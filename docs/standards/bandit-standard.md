# Bandit Standard: Security Scanning Configuration

## Overview

This project uses **Bandit** as a dedicated Python security scanner in addition to existing linting and typing checks.

Bandit analyzes Python AST patterns for common security risks and should be treated as a fail-fast security gate for application code.

## Why Bandit

- Detects common insecure coding patterns before runtime.
- Adds a focused security pass separate from style/type rules.
- Supports policy tuning by severity, confidence, and per-test controls.
- Produces machine-readable outputs for audit and changelog evidence.

## Scope and Gate Policy

- Primary scan target: `backend/`
- Exclude test and cache directories from blocking scans.
- Default enforcement: block on High severity and High confidence findings.
- Security exceptions require explicit, local justification.

## Installation

Use Bandit with TOML support so `pyproject.toml` can be the configuration source:

```bash
uv add --dev "bandit[toml]>=1.8.1"
```

## Configuration

Bandit supports configuration in `pyproject.toml`, but must be invoked with `-c pyproject.toml`.

Recommended baseline:

```toml
[tool.bandit]
exclude_dirs = [
    "tests",
    "alembic/versions",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
]
```

Optional hardening knobs:

```toml
[tool.bandit]
exclude_dirs = ["tests", "alembic/versions", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache"]
skips = ["B101"]  # only if assert-in-runtime policy is handled elsewhere
```

Notes:
- Prefer excluding test directories rather than broad global skips.
- Avoid large `skips` lists; treat them as exceptions, not defaults.

## Usage

### Security Gate (blocking)

```bash
uv run bandit -c pyproject.toml -r backend --severity-level high --confidence-level high
```

### Full visibility scan (non-filtered)

```bash
uv run bandit -c pyproject.toml -r backend
```

### JSON report for evidence

```bash
uv run bandit -c pyproject.toml -r backend -f json -o .artifacts/bandit-report.json
```

## Severity and Confidence

Bandit can be thresholded by:

- `--severity-level {all,low,medium,high}`
- `--confidence-level {all,low,medium,high}`

Equivalent short flags:
- `-l`, `-ll`, `-lll` for severity
- `-i`, `-ii`, `-iii` for confidence

## Handling False Positives

Use `# nosec` only when justified and documented.

Examples:

```python
token = hash(value)  # nosec B324 - non-cryptographic uniqueness only
```

```python
result = safe_wrapper(cmd)  # nosec B603 - validated internal command source
```

Rules:
- Scope suppressions to a specific test ID where possible.
- Add an inline reason that explains why the risk is acceptable.
- Revisit suppressions during refactors.

## Integration With Existing Repo Checks

Recommended validation order:

1. `uv run ruff check .`
2. `uv run bandit -c pyproject.toml -r backend --severity-level high --confidence-level high`
3. `uv run mypy backend scripts`
4. `uv run pyright backend scripts`
5. `uv run ty check backend`
6. `uv run pytest -v`

For DB-dependent slices, keep integration tests as a separate explicit step.

## Bandit and Ruff `S` Rules

This repository already uses Ruff `S` rules (flake8-bandit family).

Use both intentionally:
- Ruff `S`: fast, broad lint-stage security signal.
- Bandit: dedicated security scanner with richer filtering/reporting knobs.

Expect some overlap in findings. Keep policy explicit to avoid duplicated triage confusion.

## CI/CD and Hooks (Optional)

Example pre-commit hook:

```yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: "1.8.1"
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml", "-r", "app", "--severity-level", "high", "--confidence-level", "high"]
        additional_dependencies: ["bandit[toml]"]
```

## Troubleshooting

### "Bandit ignored my pyproject settings"

Use the config file explicitly:

```bash
uv run bandit -c pyproject.toml -r backend
```

### "Too many test-related findings"

Ensure `tests` is excluded via `exclude_dirs` in `[tool.bandit]` or use a separate non-blocking test scan profile.

### "Need to baseline existing findings"

Use Bandit's baseline mode with JSON output, then ratchet policy over time instead of disabling checks globally.

## Resources

- Bandit home: https://bandit.readthedocs.io/
- Bandit getting started: https://bandit.readthedocs.io/en/1.8.1/start.html
- Bandit configuration: https://bandit.readthedocs.io/en/1.7.10/config.html
- Bandit CLI reference: https://bandit.readthedocs.io/en/latest/man/bandit.html

---

**Last Updated:** 2026-03-21
