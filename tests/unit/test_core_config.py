from __future__ import annotations

import pytest

from backend.core.config import (
    Settings,
    validate_database_runtime_contract,
    validate_mercado_publico_contract,
    validate_production_database_safety,
    validate_supabase_contract,
)


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


def test_validate_mercado_publico_contract_rejects_enabled_without_api_key() -> None:
    settings = Settings.model_construct(
        mercado_publico_api_enabled=True,
        mercado_publico_api_key="",
        mercado_publico_base_url="https://api.mercadopublico.cl/servicios/v1/publico",
        mercado_publico_timeout_seconds=30.0,
        mercado_publico_retry_budget=2,
        mercado_publico_daily_request_limit=10000,
        mercado_publico_cache_ttl_seconds=900,
    )

    with pytest.raises(ValueError, match="requires MERCADO_PUBLICO_API_KEY"):
        validate_mercado_publico_contract(settings)


def test_validate_mercado_publico_contract_accepts_disabled_without_key() -> None:
    settings = Settings.model_construct(
        mercado_publico_api_enabled=False,
        mercado_publico_api_key="",
        mercado_publico_base_url="https://api.mercadopublico.cl/servicios/v1/publico",
        mercado_publico_timeout_seconds=30.0,
        mercado_publico_retry_budget=2,
        mercado_publico_daily_request_limit=10000,
        mercado_publico_cache_ttl_seconds=900,
    )

    validate_mercado_publico_contract(settings)


@pytest.mark.parametrize("pool_mode", ["transaction", "session"])
def test_validate_supabase_contract_accepts_known_pool_modes(pool_mode: str) -> None:
    settings = Settings.model_construct(supabase_db_pool_mode=pool_mode)

    validate_supabase_contract(settings)


def test_validate_supabase_contract_rejects_unknown_pool_mode() -> None:
    settings = Settings.model_construct(supabase_db_pool_mode="pool")

    with pytest.raises(ValueError, match="SUPABASE_DB_POOL_MODE must be 'session' or 'transaction'"):
        validate_supabase_contract(settings)


def test_validate_production_database_safety_rejects_default_postgres_credentials() -> None:
    with pytest.raises(ValueError, match="rejects default postgres credentials"):
        validate_production_database_safety(
            "production",
            "postgresql+psycopg://postgres:postgres@db:5432/chilecompra",
        )


def test_validate_production_database_safety_rejects_localhost_in_production() -> None:
    with pytest.raises(ValueError, match="requires a non-local DATABASE_URL host"):
        validate_production_database_safety(
            "prod",
            "postgresql+psycopg://app_user:strong@localhost:5432/chilecompra",
        )


def test_validate_production_database_safety_allows_non_production_env() -> None:
    validate_production_database_safety(
        "local",
        "postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra",
    )


def test_validate_production_database_safety_password_check_is_case_sensitive() -> None:
    validate_production_database_safety(
        "production",
        "postgresql+psycopg://postgres:Postgres@db.internal:5432/chilecompra",
    )
