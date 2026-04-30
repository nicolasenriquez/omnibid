from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

ROOT = Path(__file__).resolve().parents[2]

INGEST_RAW_PATH = ROOT / "scripts" / "ingest_raw.py"
INGEST_SPEC = importlib.util.spec_from_file_location("ingest_raw_script", INGEST_RAW_PATH)
if INGEST_SPEC is None or INGEST_SPEC.loader is None:
    raise RuntimeError(f"Unable to load ingest_raw module from {INGEST_RAW_PATH}")
INGEST_MODULE = importlib.util.module_from_spec(INGEST_SPEC)
INGEST_SPEC.loader.exec_module(INGEST_MODULE)

BUILD_NORMALIZED_PATH = ROOT / "scripts" / "build_normalized.py"
BUILD_SPEC = importlib.util.spec_from_file_location("build_normalized_script", BUILD_NORMALIZED_PATH)
if BUILD_SPEC is None or BUILD_SPEC.loader is None:
    raise RuntimeError(f"Unable to load build_normalized module from {BUILD_NORMALIZED_PATH}")
BUILD_MODULE = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(BUILD_MODULE)


@pytest.fixture
def tmp_path() -> Path:
    workspace_root = Path(__file__).resolve().parents[2] / ".tmp-test-scoped-pipeline"
    workspace_root.mkdir(parents=True, exist_ok=True)
    path = workspace_root / f"scoped-pipeline-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class _DummySession:
    def __init__(self) -> None:
        self.commit_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1


def test_process_registered_file_updates_existing_pipeline_records(monkeypatch: Any, tmp_path: Path) -> None:
    path = tmp_path / "licitacion.csv"
    path.write_text("ignored", encoding="utf-8")
    source_file = SimpleNamespace(
        id=uuid4(),
        source_meta={"ingestion_mode": "manual_upload"},
        status="registered",
    )
    batch = SimpleNamespace(
        total_rows=None,
        loaded_rows=None,
        rejected_rows=None,
        status="started",
        finished_at=None,
    )
    run = SimpleNamespace(config={}, status="running", finished_at=None)
    step = SimpleNamespace(
        status="running",
        finished_at=None,
        rows_in=None,
        rows_out=None,
        rows_rejected=None,
    )
    session = _DummySession()
    raw_scope_counts = iter([0, 9])

    monkeypatch.setattr(INGEST_MODULE, "count_csv_rows", lambda _path: 9)
    monkeypatch.setattr(
        INGEST_MODULE,
        "count_raw_rows_for_source_file",
        lambda *_args, **_kwargs: next(raw_scope_counts),
    )
    monkeypatch.setattr(INGEST_MODULE, "ingest_file", lambda **_kwargs: 9)

    metrics = INGEST_MODULE.process_registered_file(
        session=session,
        dataset_type="licitacion",
        path=path,
        source_file=source_file,
        batch=batch,
        run=run,
        step=step,
        chunk_size=5000,
        show_progress=False,
        precount=True,
    )

    assert metrics["processed_rows"] == 9
    assert metrics["inserted_delta_rows"] == 9
    assert source_file.status == "loaded"
    assert batch.loaded_rows == 9
    assert step.rows_out == 9
    assert run.config["raw_ingest_metrics"]["processed_rows"] == 9
    assert session.commit_calls == 1


def test_raw_scope_filters_add_source_file_clause() -> None:
    source_file_id = uuid4()
    stmt = sa.select(BUILD_MODULE.RawLicitacion).where(
        *BUILD_MODULE._raw_scope_filters(  # type: ignore[attr-defined]
            BUILD_MODULE.RawLicitacion,
            start_after_id=123,
            source_file_id=source_file_id,
        )
    )

    compiled = str(stmt.compile(dialect=postgresql.dialect()))

    assert "raw_licitaciones.id >" in compiled
    assert "raw_licitaciones.source_file_id =" in compiled
