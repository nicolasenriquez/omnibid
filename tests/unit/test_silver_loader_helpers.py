from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD_SILVER_PATH = ROOT / "scripts" / "build_silver.py"
SPEC = importlib.util.spec_from_file_location("build_silver_script", BUILD_SILVER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load build_silver module from {BUILD_SILVER_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
dedupe_rows = MODULE.dedupe_rows


def test_dedupe_rows_keeps_latest_payload_for_same_business_key() -> None:
    rows = [
        {"codigo_externo": "L-1", "nombre": "old"},
        {"codigo_externo": "L-1", "nombre": "new"},
        {"codigo_externo": "L-2", "nombre": "only"},
    ]

    deduped = dedupe_rows(rows, ["codigo_externo"])

    by_key = {row["codigo_externo"]: row for row in deduped}
    assert len(deduped) == 2
    assert by_key["L-1"]["nombre"] == "new"
    assert by_key["L-2"]["nombre"] == "only"


def test_dedupe_rows_fails_when_business_key_is_missing() -> None:
    rows = [
        {"codigo_externo": "L-1", "nombre": "ok"},
        {"nombre": "missing-key"},
    ]

    with pytest.raises(ValueError, match="missing business key"):
        dedupe_rows(rows, ["codigo_externo"])


def test_dedupe_rows_fails_when_business_key_fields_are_empty() -> None:
    rows = [{"codigo_externo": "L-1"}]

    with pytest.raises(ValueError, match="conflict key fields"):
        dedupe_rows(rows, [])
