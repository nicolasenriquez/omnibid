from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
NLP_CONFIG_DIR = REPO_ROOT / "config" / "nlp"
NLP_CONFIG_FILE = "nlp_config_v1.json"
NLP_PATTERNS_FILE = "nlp_patterns_v1.json"


@dataclass(frozen=True)
class NLPContractConfig:
    nlp_version: str
    canonical_model: str
    default_language: str
    low_confidence_language_label: str
    minimum_language_tokens: int
    max_annotation_tokens: int
    max_annotation_ngrams: int
    supported_source_profiles: tuple[str, ...]
    domain_keywords: dict[str, tuple[str, ...]]


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"NLP config file not found: {path}")
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"NLP config file must contain a JSON object: {path}")
    return data  # pyright: ignore[reportUnknownVariableType]


def _coerce_text_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"NLP config field {field_name} must be a JSON array")
    items: list[str] = [str(item).strip() for item in value if str(item).strip()]  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
    if not items:
        raise ValueError(f"NLP config field {field_name} must not be empty")
    return tuple(items)


def _coerce_keyword_map(value: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, dict):
        raise ValueError("NLP patterns file must contain a JSON object")

    keyword_map: dict[str, tuple[str, ...]] = {}
    for domain, keywords in value.items():  # pyright: ignore[reportUnknownVariableType]
        domain_name = str(domain).strip()  # pyright: ignore[reportUnknownArgumentType]
        if not domain_name:
            raise ValueError("NLP patterns file contains an empty domain name")
        keyword_map[domain_name] = _coerce_text_tuple(keywords, field_name=f"patterns.{domain_name}")
    if not keyword_map:
        raise ValueError("NLP patterns file must define at least one domain")
    return keyword_map


def load_nlp_contract_config(config_dir: Path | None = None) -> NLPContractConfig:
    base_dir = NLP_CONFIG_DIR if config_dir is None else Path(config_dir)
    general = _read_json_object(base_dir / NLP_CONFIG_FILE)
    patterns = _read_json_object(base_dir / NLP_PATTERNS_FILE)

    required_text_fields = (
        "nlp_version",
        "canonical_model",
        "default_language",
        "low_confidence_language_label",
    )
    parsed_text_fields: dict[str, str] = {}
    for field_name in required_text_fields:
        raw_value = general.get(field_name)
        if raw_value is None:
            raise ValueError(f"missing NLP config field: {field_name}")
        parsed_value = str(raw_value).strip()
        if not parsed_value:
            raise ValueError(f"NLP config field {field_name} must not be empty")
        parsed_text_fields[field_name] = parsed_value

    parsed_int_fields: dict[str, int] = {}
    for field_name in ("minimum_language_tokens", "max_annotation_tokens", "max_annotation_ngrams"):
        raw_value = general.get(field_name)
        if raw_value is None:
            raise ValueError(f"missing NLP config field: {field_name}")
        parsed_int_value = int(raw_value)
        if parsed_int_value <= 0:
            raise ValueError(f"NLP config field {field_name} must be > 0")
        parsed_int_fields[field_name] = parsed_int_value

    supported_source_profiles = _coerce_text_tuple(
        general.get("supported_source_profiles"),
        field_name="supported_source_profiles",
    )
    domain_keywords = _coerce_keyword_map(patterns)

    return NLPContractConfig(
        nlp_version=parsed_text_fields["nlp_version"],
        canonical_model=parsed_text_fields["canonical_model"],
        default_language=parsed_text_fields["default_language"],
        low_confidence_language_label=parsed_text_fields["low_confidence_language_label"],
        minimum_language_tokens=parsed_int_fields["minimum_language_tokens"],
        max_annotation_tokens=parsed_int_fields["max_annotation_tokens"],
        max_annotation_ngrams=parsed_int_fields["max_annotation_ngrams"],
        supported_source_profiles=supported_source_profiles,
        domain_keywords=domain_keywords,
    )


@lru_cache(maxsize=1)
def get_nlp_contract_config() -> NLPContractConfig:
    return load_nlp_contract_config()
