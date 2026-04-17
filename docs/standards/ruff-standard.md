# Ruff Standard: Linting Configuration

## Overview

This project uses **Ruff** as the primary linting tool. Ruff is an extremely fast Python linter written in Rust and replaces multiple lint tools (Flake8 plugins, isort, pyupgrade, and others) with one performant command.

**Why Ruff:**
- ⚡️ 10-100x faster than traditional Python linters
- 🔧 Auto-fixes most issues automatically
- 📦 Replaces many lint-only tools with one
- 🎯 AI-friendly: deterministic rule enforcement and output

## Configuration

All Ruff configuration is in `pyproject.toml` under `[tool.ruff]`.

### Target and Line Length

```toml
[tool.ruff]
target-version = "py312"
line-length = 100
```

- **Python 3.12+** syntax support
- **100 character line length** - balances readability with screen real estate
- Modern wide screens accommodate 100 chars comfortably

### Excluded Directories

```toml
exclude = [
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
]
```

Standard Python artifacts and virtual environments are excluded.

## Linting Rules

### Enabled Rule Categories

```toml
[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort (import sorting)
    "B",      # flake8-bugbear (catch mutable defaults, etc.)
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade (modernize syntax)
    "ANN",    # flake8-annotations (enforce type hints)
    "S",      # flake8-bandit (security)
    "DTZ",    # flake8-datetimez (timezone-aware datetimes)
    "RUF",    # Ruff-specific rules
    "ARG",    # flake8-unused-arguments
    "PTH",    # flake8-use-pathlib (prefer Path over os.path)
]
```

#### Rule Category Details

| Category | Purpose | Examples |
|----------|---------|----------|
| **E/W** | Code style (PEP 8) | Whitespace, indentation, line length |
| **F** | Logic errors | Undefined names, unused imports |
| **I** | Import organization | Sorted, grouped imports |
| **B** | Bug detection | Mutable defaults, strip/lstrip misuse |
| **C4** | Comprehensions | Unnecessary list/set/dict calls |
| **UP** | Syntax modernization | Use `dict \| dict` instead of `dict.update()` |
| **ANN** | Type annotations | Missing return types, argument types |
| **S** | Security vulnerabilities | Hardcoded secrets, SQL injection, `eval()` |
| **DTZ** | Timezone awareness | Naive datetime usage |
| **RUF** | Ruff-specific | Performance, best practices |
| **ARG** | Unused arguments | Detect unused function parameters |
| **PTH** | Path usage | Prefer `pathlib.Path` over `os.path` |

### Ignored Rules

```toml
ignore = [
    "S311",   # Standard random is fine for non-crypto use
    "E501",   # Line too long (formatter handles this)
]
```

- **S311**: Allow `random.random()` for non-cryptographic purposes (IDs, test data, etc.)
- **E501**: Line length handled by formatter; linter shouldn't duplicate

### Per-File Ignores

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "ANN", "ARG001", "D", "E731"]
"test_*.py" = ["S101", "ANN", "ARG001", "D", "E731"]
"**/tests/**/*.py" = ["S101", "ANN", "ARG001", "D", "E731"]
"__init__.py" = ["F401"]
"scripts/**/*.py" = ["T201"]
"backend/core/health.py" = ["B008"]
```

#### Test Files (`tests/**/*.py`, `test_*.py`, `**/tests/**/*.py`)

- **S101**: Allow `assert` in tests (required for pytest)
- **ANN**: Skip type annotations (test code can be less strict)
- **ARG001**: Allow unused arguments (pytest fixtures, test parameters)
- **D**: Skip docstring requirements (tests are self-documenting)
- **E731**: Allow lambda assignments (common in test fixtures)

#### Package Initialization (`__init__.py`)

- **F401**: Allow unused imports (re-exports, public API exposure)

#### Scripts (`scripts/**/*.py`)

- **T201**: Allow `print()` statements (acceptable for scripts)

#### Specific Files

- **`backend/core/health.py` - B008**: FastAPI `Depends()` in function defaults is the recommended pattern, not a bug

## Formatting Configuration

```toml
[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "auto"
```

- **Double quotes** for strings (consistent with Black)
- **Spaces** for indentation (4 spaces per PEP 8)
- **Auto line endings** - adapts to OS (LF on Unix, CRLF on Windows)

## Import Sorting (isort)

```toml
[tool.ruff.lint.isort]
known-first-party = ["app"]
```

Import order:
1. Standard library (e.g., `import os`)
2. Third-party packages (e.g., `from fastapi import FastAPI`)
3. First-party (your code: `from app.core import get_logger`)

## Usage

### Check Code

```bash
# Check all files
uv run ruff check .

# Check specific directory
uv run ruff check backend/

# Show fixes that would be applied
uv run ruff check . --diff
```

### Auto-fix Issues

```bash
# Fix all auto-fixable issues
uv run ruff check . --fix

# Fix specific directory
uv run ruff check backend/ --fix

# Fix and show what was changed
uv run ruff check . --fix --diff
```

### Format Code (optional local convenience)

```bash
# Format all files
uv run ruff format .

# Format specific file
uv run ruff format backend/main.py

# Note: repository formatting gate is Black, not `ruff format --check`
```

### Combined Workflow

```bash
# Lint + required formatter gate
uv run ruff check .
uv run black . --check --diff
```

## Common Issues and Fixes

### Missing Type Annotations (ANN)

```python
# ❌ Error: ANN001 Missing type annotation for function argument
def create_user(email):
    pass

# ✅ Fixed
def create_user(email: str) -> User:
    pass
```

### Mutable Default Arguments (B006)

```python
# ❌ Error: B006 Mutable default argument
def process_items(items=[]):
    pass

# ✅ Fixed
def process_items(items: list[str] | None = None) -> None:
    if items is None:
        items = []
```

### Unused Imports (F401)

```python
# ❌ Error: F401 'os' imported but unused
import os
from pathlib import Path

# ✅ Fixed - remove unused import
from pathlib import Path
```

### Security: Hardcoded Password (S105)

```python
# ❌ Error: S105 Hardcoded password
password = "secret123"

# ✅ Fixed
from os import environ
password = environ.get("PASSWORD")
```

### Timezone-Naive Datetime (DTZ)

```python
# ❌ Error: DTZ005 datetime.now() without timezone
from datetime import datetime
now = datetime.now()

# ✅ Fixed
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
```

### Prefer pathlib (PTH)

```python
# ❌ Error: PTH118 os.path.join should be replaced by Path
import os
path = os.path.join("app", "core", "config.py")

# ✅ Fixed
from pathlib import Path
path = Path("app") / "core" / "config.py"
```

## Integration with Git Hooks

Use `pre-commit` to automatically run Ruff on commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.2
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

## Integration with Editors

### VS Code

```json
{
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  }
}
```

### PyCharm/IntelliJ

Settings → Tools → Ruff → Enable Ruff

### Vim/Neovim

Use `null-ls` or `nvim-lint` with Ruff integration.

## AI Coding Guidelines

When working with AI coding assistants:

1. **Run Ruff frequently**: `uv run ruff check . --fix && uv run ruff format .`
2. **Include in prompts**: "Ensure Ruff passes with no errors"
3. **Auto-fix before review**: Let Ruff handle mechanical issues
4. **Focus human review**: On logic, architecture, and test assertions

### Prompt Template

```
[Your task description]

Requirements:
- Follow existing code patterns in backend/
- Ensure type hints on all functions (ANN rules)
- Use timezone-aware datetimes (DTZ rules)
- Run `uv run ruff check . --fix`
- Run `uv run black . --check --diff`
- All Ruff checks must pass
```

## Ruff vs Other Tools

| Tool | Replaced By Ruff | Notes |
|------|------------------|-------|
| Flake8 | ✅ Yes | Ruff implements most Flake8 rules |
| Black | ❌ No | Black is the required formatter gate in this repo |
| isort | ✅ Yes | `I` rules handle import sorting |
| pyupgrade | ✅ Yes | `UP` rules modernize syntax |
| pydocstyle | ⚠️ Partial | `D` rules available but not enabled |
| Bandit | ⚠️ Partial | Keep dedicated Bandit gate for depth/reporting |
| MyPy | ❌ No | Type checking requires MyPy/Pyright |
| Pylint | ⚠️ Partial | Most checks covered, some Pylint-specific missing |

## Performance

Ruff is **10-100x faster** than traditional Python linters:

```bash
# Typical timing on this project
$ time uv run ruff check .
All checks passed!
uv run ruff check .  0.02s user 0.01s system 96% cpu 0.033 total

# Compare to Flake8 (if installed)
$ time flake8 .
# Would take 0.5-2 seconds on same codebase
```

## Updating Ruff

```bash
# Update to latest version
uv sync --upgrade-package ruff

# Or update all dev dependencies
uv sync --upgrade
```

## Configuration Best Practices

### ✅ DO

- Enable strict rules early (easier than retrofitting)
- Use per-file ignores for legitimate exceptions
- Document why rules are ignored (inline comments)
- Run Ruff in CI/CD pipelines
- Configure editor integration

### ❌ DON'T

- Disable entire rule categories without reason
- Add blanket ignores to hide problems
- Skip Ruff checks during rapid prototyping (debt accumulates)
- Ignore security rules (S) without explicit justification
- Use multiple mandatory formatter gates without a single authority

## Troubleshooting

### "E501 line too long" still appearing

Ruff formatter respects 100-char limit but doesn't break comments/strings. Manually wrap long comments.

### "ANN401 Any is not allowed"

If you must use `Any`, document why:
```python
from typing import Any

def process_dynamic(data: Any) -> dict[str, Any]:  # type: ignore[ANN401]
    # Any required for dynamic external API responses
    return {"processed": data}
```

### "F401 unused import" in `__init__.py`

Expected for re-exports. Already ignored via per-file rules.

### Conflicts with Black

Use Black as the required formatter authority and Ruff for linting. Avoid dual mandatory formatter checks (`black --check` and `ruff format --check`) in the same gate.

## Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff Rules Reference](https://docs.astral.sh/ruff/rules/)
- [Ruff Settings](https://docs.astral.sh/ruff/settings/)
- [Ruff FAQ](https://docs.astral.sh/ruff/faq/)

---

**Last Updated:** 2026-03-21
**Ruff Version:** 0.14.2+
**Python Version:** 3.12+
