from __future__ import annotations

from backend.core.config import validate_database_runtime_contract
from backend.nlp.config import get_nlp_contract_config

_CONTRACT = get_nlp_contract_config()
IMPLEMENTED_SOURCE_PROFILE = _CONTRACT.supported_source_profiles[0]
DOCUMENTED_SOURCE_PROFILES = _CONTRACT.supported_source_profiles


def normalize_source_profile(source_profile: str) -> str:
    normalized = source_profile.strip().lower()
    if normalized != IMPLEMENTED_SOURCE_PROFILE:
        allowed_profiles = ", ".join(DOCUMENTED_SOURCE_PROFILES)
        raise ValueError(
            f"unsupported source profile: {normalized}. Supported profiles: {allowed_profiles}"
        )
    return normalized


def validate_nlp_runtime_contract(
    database_url: str,
    test_database_url: str,
    *,
    source_profile: str = IMPLEMENTED_SOURCE_PROFILE,
) -> None:
    normalize_source_profile(source_profile)
    validate_database_runtime_contract(database_url, test_database_url)
