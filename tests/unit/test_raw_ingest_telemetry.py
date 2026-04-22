from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INGEST_RAW_PATH = ROOT / "scripts" / "ingest_raw.py"
SPEC = importlib.util.spec_from_file_location("ingest_raw_script", INGEST_RAW_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load ingest_raw module from {INGEST_RAW_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_raw_ingest_metrics = MODULE.build_raw_ingest_metrics


def test_build_raw_ingest_metrics_duplicate_heavy_rerun() -> None:
    metrics = build_raw_ingest_metrics(
        processed_rows=1_000,
        before_scope_rows=1_000,
        after_scope_rows=1_005,
    )

    assert metrics["processed_rows"] == 1_000
    assert metrics["accepted_rows"] == 1_000
    assert metrics["deduplicated_rows"] == 1_000
    assert metrics["inserted_delta_rows"] == 5
    assert metrics["existing_or_updated_rows"] == 995
    assert metrics["rejected_rows"] == 0


def test_build_raw_ingest_metrics_noop_rerun() -> None:
    metrics = build_raw_ingest_metrics(
        processed_rows=10_000,
        before_scope_rows=10_000,
        after_scope_rows=10_000,
    )

    assert metrics["inserted_delta_rows"] == 0
    assert metrics["existing_or_updated_rows"] == 10_000


def test_build_raw_ingest_metrics_fails_when_after_scope_decreases() -> None:
    with pytest.raises(ValueError, match="after_scope_rows must be >= before_scope_rows"):
        build_raw_ingest_metrics(
            processed_rows=100,
            before_scope_rows=120,
            after_scope_rows=110,
        )


def test_build_raw_ingest_metrics_fails_when_inserted_delta_exceeds_input() -> None:
    with pytest.raises(ValueError, match="inserted_delta_rows cannot exceed deduplicated_rows"):
        build_raw_ingest_metrics(
            processed_rows=100,
            before_scope_rows=0,
            after_scope_rows=101,
        )
