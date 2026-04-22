# Official Sources Registry (SDD)

This registry defines the preferred official sources for this repository stack.

## Runtime and Language

- Python: https://docs.python.org/3/
- uv: https://docs.astral.sh/uv/
- Just: https://just.systems/man/en/

## API and Validation

- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/

## Persistence and Migrations

- SQLAlchemy 2.x: https://docs.sqlalchemy.org/en/20/
- Alembic: https://alembic.sqlalchemy.org/en/latest/
- PostgreSQL: https://www.postgresql.org/docs/

## Testing and Quality

- pytest: https://docs.pytest.org/en/stable/
- mypy: https://mypy.readthedocs.io/en/stable/
- Ruff: https://docs.astral.sh/ruff/
- Pyright: https://microsoft.github.io/pyright/
- Bandit: https://bandit.readthedocs.io/en/latest/

## OpenSpec Workflow

- OpenSpec (project local conventions): `openspec/` artifacts in this repository

## Usage Rule

When implementing behavior tied to one of these tools/frameworks:

1. start from this registry
2. consult the matching official source
3. document the resulting decision in an SDD note/template record
