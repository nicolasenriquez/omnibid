# Source-Driven Development (SDD) Standard

## Purpose

Ensure every relevant implementation decision is grounded in official documentation and leaves an auditable technical rationale.

## Scope

Applies to all changes affecting:

- framework behavior (FastAPI, SQLAlchemy, Alembic, Pydantic, pytest)
- database behavior and SQL semantics (PostgreSQL)
- tooling behavior (uv, mypy, ruff, pyright, ty)
- integration contracts and runtime behavior

## Mandatory Rules

1. Consult official documentation before coding behavior that depends on external frameworks/tools.
2. Record consulted sources in `docs/standards/` before or during implementation.
3. Link source to decision:
   - what was implemented
   - why this behavior is correct
   - where in code it applies
4. Prefer official sources over third-party summaries.
5. If no official source is available:
   - document the fallback source
   - explain risk and validation approach

## Minimum SDD Evidence per Change

- A short source note (or reference file update) including:
  - source URL
  - topic/section used
  - decision derived from that source
  - impacted files/modules

## Review Checklist

- Is each non-trivial framework/tool behavior backed by an official source?
- Is the source-to-code decision trace clear?
- Are assumptions explicit where official docs are ambiguous?
- Do tests validate the documented behavior?

## Relationship with Existing Practices

- SDD complements TDD:
  - SDD defines what should be built based on official contracts.
  - TDD verifies behavior through executable tests.
- SDD complements fail-fast:
  - authoritative contracts reduce hidden behavior and ambiguous fallbacks.
