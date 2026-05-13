from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from backend.pipeline.orchestration import daily_pipeline as application


def test_run_registered_raw_ingest_uses_manual_upload_defaults() -> None:
    captured: dict[str, Any] = {}

    def _fake_process_registered_file(**kwargs: Any) -> dict[str, int]:
        captured.update(kwargs)
        return {"processed_rows": 1}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(application, "process_registered_file", _fake_process_registered_file)

    try:
        result = application.run_registered_raw_ingest(
            session=object(),  # type: ignore[arg-type]
            dataset_type="licitacion",
            source_profile="csv_drop",
            path=Path("input.csv"),
            source_file=object(),  # type: ignore[arg-type]
            batch=object(),  # type: ignore[arg-type]
            run=object(),  # type: ignore[arg-type]
            step=object(),  # type: ignore[arg-type]
            expected_rows=99,
            on_progress=None,
        )
    finally:
        monkeypatch.undo()

    assert result == {"processed_rows": 1}
    assert captured["chunk_size"] == application.RAW_CHUNK_SIZE
    assert captured["show_progress"] is False
    assert captured["precount"] is False
    assert captured["expected_rows"] == 99


def test_normalize_source_profile_accepts_only_csv_drop() -> None:
    assert application.normalize_source_profile("csv_drop") == "csv_drop"


def test_normalize_source_profile_rejects_documented_future_profiles() -> None:
    with pytest.raises(ValueError, match="unsupported source profile"):
        application.normalize_source_profile("api_json")


def test_run_registered_raw_ingest_rejects_unsupported_source_profile() -> None:
    with pytest.raises(ValueError, match="unsupported source profile"):
        application.run_registered_raw_ingest(
            session=object(),  # type: ignore[arg-type]
            dataset_type="licitacion",
            source_profile="api_json",
            path=Path("input.csv"),
            source_file=object(),  # type: ignore[arg-type]
            batch=object(),  # type: ignore[arg-type]
            run=object(),  # type: ignore[arg-type]
            step=object(),  # type: ignore[arg-type]
        )


def test_run_normalized_build_routes_dataset_type() -> None:
    called: list[str] = []

    def _fake_licitaciones(**_kwargs: Any) -> dict[str, Any]:
        called.append("licitacion")
        return {"dataset": "licitacion"}

    def _fake_ordenes(**_kwargs: Any) -> dict[str, Any]:
        called.append("orden_compra")
        return {"dataset": "orden_compra"}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(application, "process_licitaciones", _fake_licitaciones)
    monkeypatch.setattr(application, "process_ordenes_compra", _fake_ordenes)

    try:
        first = application.run_normalized_build(
            session=object(),  # type: ignore[arg-type]
            dataset_type="licitacion",
            source_profile="csv_drop",
            source_file_id="file-1",
        )
        second = application.run_normalized_build(
            session=object(),  # type: ignore[arg-type]
            dataset_type="orden_compra",
            source_profile="csv_drop",
            source_file_id="file-2",
        )
    finally:
        monkeypatch.undo()

    assert first["dataset"] == "licitacion"
    assert second["dataset"] == "orden_compra"
    assert called == ["licitacion", "orden_compra"]


def test_run_normalized_build_rejects_unknown_dataset_type() -> None:
    with pytest.raises(ValueError, match="unsupported dataset type"):
        application.run_normalized_build(
            session=object(),  # type: ignore[arg-type]
            dataset_type="unknown",
            source_profile="csv_drop",
            source_file_id="file-3",
        )


def test_run_normalized_build_rejects_unsupported_source_profile() -> None:
    with pytest.raises(ValueError, match="unsupported source profile"):
        application.run_normalized_build(
            session=object(),  # type: ignore[arg-type]
            dataset_type="licitacion",
            source_profile="open_data_snapshot",
            source_file_id="file-4",
        )
