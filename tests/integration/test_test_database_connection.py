from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.integration
def test_test_database_url_accepts_basic_connection() -> None:
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    assert test_database_url, "TEST_DATABASE_URL must be set for integration tests"

    engine = create_engine(test_database_url, pool_pre_ping=True, future=True)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
