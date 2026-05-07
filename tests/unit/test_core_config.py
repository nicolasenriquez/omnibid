from __future__ import annotations

import pytest

from backend.core.config import validate_database_runtime_contract


@pytest.mark.parametrize(
    ("database_url", "test_database_url"),
    [
        (
            "postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra",
            "postgresql+psycopg://postgres:postgres@localhost:5433/chilecompra_test",
        ),
        (
            "postgresql+psycopg://postgres:postgres@db:5432/chilecompra",
            "postgresql+psycopg://postgres:postgres@db_test:5432/chilecompra_test",
        ),
    ],
)
def test_validate_database_runtime_contract_accepts_matching_runtime_families(
    database_url: str,
    test_database_url: str,
) -> None:
    validate_database_runtime_contract(database_url, test_database_url)


def test_validate_database_runtime_contract_rejects_identical_urls() -> None:
    database_url = "postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra"

    with pytest.raises(ValueError, match="TEST_DATABASE_URL must differ from DATABASE_URL"):
        validate_database_runtime_contract(database_url, database_url)


def test_validate_database_runtime_contract_rejects_mixed_runtime_families() -> None:
    with pytest.raises(ValueError, match="must not mix host and Docker runtime families"):
        validate_database_runtime_contract(
            "postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra",
            "postgresql+psycopg://postgres:postgres@db_test:5432/chilecompra_test",
        )


def test_validate_database_runtime_contract_rejects_runtime_test_database() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL must not target a test database"):
        validate_database_runtime_contract(
            "postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra_test",
            "postgresql+psycopg://postgres:postgres@localhost:5433/chilecompra",
        )


def test_validate_database_runtime_contract_rejects_blank_database_url() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL is not set"):
        validate_database_runtime_contract("   ", "postgresql+psycopg://postgres:postgres@localhost:5433/chilecompra_test")
