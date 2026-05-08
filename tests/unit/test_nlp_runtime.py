from __future__ import annotations

import pytest

from backend.nlp.runtime import (
    DOCUMENTED_SOURCE_PROFILES,
    IMPLEMENTED_SOURCE_PROFILE,
    normalize_source_profile,
    validate_nlp_runtime_contract,
)


def test_normalize_source_profile_accepts_only_csv_drop() -> None:
    assert IMPLEMENTED_SOURCE_PROFILE == "csv_drop"
    assert normalize_source_profile("csv_drop") == "csv_drop"
    assert DOCUMENTED_SOURCE_PROFILES == ("csv_drop", "api_json", "open_data_snapshot")


def test_normalize_source_profile_rejects_future_profiles() -> None:
    with pytest.raises(ValueError, match="unsupported source profile"):
        normalize_source_profile("api_json")


def test_validate_nlp_runtime_contract_accepts_matching_database_urls() -> None:
    validate_nlp_runtime_contract(
        "postgresql+psycopg://postgres:postgres@localhost:5432/chilecompra",
        "postgresql+psycopg://postgres:postgres@localhost:5433/chilecompra_test",
    )
