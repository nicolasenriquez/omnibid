from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from backend.api.routers import manual_uploads
from backend.ingestion.manual_uploads import (
    ManualUploadError,
    build_manual_csv_preflight,
    format_manual_upload_size_limit,
    validate_manual_upload_content_type,
    validate_manual_upload_dataset_type,
    validate_manual_upload_filename,
)
from backend.main import app


LICITACION_CSV = (
    '"Codigo";"CodigoExterno";"Tipo de Adquisicion";"FechaPublicacion";'
    '"FechaCierre";"Codigoitem"\n'
    '"1";"LIC-2026-4";"Licitacion Publica";"2026-04-01";"2026-04-08";"1"\n'
)

ORDEN_COMPRA_CSV = (
    '"Codigo";"FechaEnvio";"Estado";"DescripcionTipoOC";"IDItem";'
    '"codigoProductoONU";"totalLineaNeto"\n'
    '"1";"2026-04-01";"ACEPTADA";"Compra";"1";"12345678";"1000"\n'
)


class _FakeRequest:
    def __init__(self, *, content_type: str, body: bytes) -> None:
        self.headers = {"content-type": content_type}
        self._body = body

    async def body(self) -> bytes:
        return self._body


class _DummyResult:
    def __init__(
        self,
        *,
        rows: list[Any] | None = None,
        scalar: int | None = None,
    ) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def scalar_one(self) -> int:
        if self._scalar is None:
            raise AssertionError("scalar_one requested but no scalar value was configured")
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._rows[0] if self._rows else None


class _DummySession:
    def __init__(self, responses: list[_DummyResult | Exception]) -> None:
        self._responses = responses
        self.execute_calls = 0
        self.add_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0

    def execute(self, _stmt: object) -> _DummyResult:
        if not self._responses:
            raise AssertionError("no dummy response available for execute call")
        self.execute_calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def add(self, _obj: object) -> None:
        self.add_calls += 1

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


def _multipart_request(
    *,
    dataset_type: str,
    filename: str,
    payload: bytes,
    file_content_type: str = "text/csv",
) -> _FakeRequest:
    boundary = f"----manual-upload-{uuid4().hex}"
    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        b'Content-Disposition: form-data; name="dataset_type"\r\n\r\n',
        dataset_type.encode("utf-8"),
        b"\r\n",
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"),
        f"Content-Type: {file_content_type}\r\n\r\n".encode("utf-8"),
        payload,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    return _FakeRequest(
        content_type=f"multipart/form-data; boundary={boundary}",
        body=b"".join(parts),
    )


def _run_async(coro: Any) -> Any:
    return asyncio.run(coro)


def _settings(*, root: Path, max_bytes: int) -> SimpleNamespace:
    return SimpleNamespace(manual_upload_root=root, manual_upload_max_bytes=max_bytes)


@pytest.fixture
def tmp_path() -> Path:
    workspace_root = Path(__file__).resolve().parents[2] / ".tmp-test-manual-uploads"
    workspace_root.mkdir(parents=True, exist_ok=True)
    path = workspace_root / f"manual-upload-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_manual_upload_routes_are_registered() -> None:
    route_paths = {route.path for route in app.routes}

    assert "/uploads/procurement-csv/preflight" in route_paths
    assert "/uploads/procurement-csv/{file_token}/process" in route_paths
    assert "/uploads/procurement-csv/jobs/{job_id}" in route_paths


def test_validate_manual_upload_filename_rejects_path_like_names() -> None:
    with pytest.raises(ManualUploadError, match="must not contain path components"):
        validate_manual_upload_filename("../lic_2026-4.csv")


def test_build_manual_csv_preflight_rejects_wrong_extension(tmp_path: Path) -> None:
    with pytest.raises(ManualUploadError, match="must have a \\.csv extension"):
        build_manual_csv_preflight(
            dataset_type="licitacion",
            original_filename="lic_2026-4.txt",
            payload=LICITACION_CSV.encode("utf-8"),
            intake_root=tmp_path,
            max_bytes=1024 * 1024,
        )


def test_build_manual_csv_preflight_rejects_empty_file(tmp_path: Path) -> None:
    with pytest.raises(ManualUploadError, match="Uploaded CSV is empty"):
        build_manual_csv_preflight(
            dataset_type="licitacion",
            original_filename="lic_2026-4.csv",
            payload=b"",
            intake_root=tmp_path,
            max_bytes=1024 * 1024,
        )


def test_build_manual_csv_preflight_rejects_missing_required_columns(tmp_path: Path) -> None:
    payload = (
        '"Codigo";"CodigoExterno";"Tipo de Adquisicion"\n'
        '"1";"LIC-2026-4";"Licitacion Publica"\n'
    ).encode("utf-8")

    with pytest.raises(ManualUploadError, match="Missing required columns for dataset=licitacion"):
        build_manual_csv_preflight(
            dataset_type="licitacion",
            original_filename="lic_2026-4.csv",
            payload=payload,
            intake_root=tmp_path,
            max_bytes=1024 * 1024,
        )


def test_build_manual_csv_preflight_rejects_wrong_selected_dataset(tmp_path: Path) -> None:
    with pytest.raises(ManualUploadError, match="Missing required columns for dataset=licitacion"):
        build_manual_csv_preflight(
            dataset_type="licitacion",
            original_filename="2026-4.csv",
            payload=ORDEN_COMPRA_CSV.encode("utf-8"),
            intake_root=tmp_path,
            max_bytes=1024 * 1024,
        )


def test_build_manual_csv_preflight_accepts_semicolon_csv(tmp_path: Path) -> None:
    preflight = build_manual_csv_preflight(
        dataset_type="licitacion",
        original_filename="lic_2026-4.csv",
        payload=LICITACION_CSV.encode("utf-8"),
        intake_root=tmp_path,
        max_bytes=1024 * 1024,
        content_type="text/csv; charset=utf-8",
    )

    assert preflight.dataset_type == "licitacion"
    assert preflight.original_filename == "lic_2026-4.csv"
    assert preflight.content_type == "text/csv"
    assert preflight.row_count == 1
    assert preflight.missing_required_columns == ()
    assert preflight.file_hash_sha256
    assert Path(preflight.staged_file_path).exists()
    assert Path(preflight.metadata_path).exists()


def test_manual_upload_content_type_and_size_helpers() -> None:
    assert validate_manual_upload_dataset_type("  ORDEN_COMPRA  ") == "orden_compra"
    assert validate_manual_upload_content_type("text/csv; charset=utf-8") == "text/csv"
    assert format_manual_upload_size_limit(5 * 1024 * 1024) == "5 MiB"


def test_manual_upload_telemetry_distinguishes_raw_and_canonical_deltas() -> None:
    payload = manual_uploads._manual_upload_telemetry(  # type: ignore[attr-defined]
        {
            "processed_rows": 100,
            "accepted_rows": 100,
            "inserted_delta_rows": 100,
            "existing_or_updated_rows": 0,
            "rejected_rows": 0,
        },
        {
            "licitaciones": {"inserted_delta_rows": 10},
            "licitacion_items": {"inserted_delta_rows": 30},
            "silver_notice": {"inserted_delta_rows": 8},
            "silver_notice_line": {"inserted_delta_rows": 24},
        },
    )

    assert payload["accepted_rows"] == 100
    assert payload["inserted_delta_rows"] == 100
    assert payload["normalized_rows"] == 40
    assert payload["silver_rows"] == 32


def test_preflight_endpoint_returns_summary_and_duplicate_hint(tmp_path: Path) -> None:
    duplicate_hash = hashlib.sha256(LICITACION_CSV.encode("utf-8")).hexdigest()
    duplicate_source = SimpleNamespace(
        id=uuid4(),
        dataset_type="licitacion",
        file_name="existing.csv",
        file_path=str(tmp_path / "existing.csv"),
        file_hash_sha256=duplicate_hash,
        status="registered",
        registered_at=datetime.now(UTC),
        source_meta={"manual_upload": {"file_token": "existing"}},
    )
    session = _DummySession(
        [
            _DummyResult(rows=[duplicate_source]),
            _DummyResult(scalar=7),
            _DummyResult(scalar=11),
            _DummyResult(scalar=13),
            _DummyResult(scalar=17),
            _DummyResult(scalar=19),
            _DummyResult(scalar=23),
            _DummyResult(scalar=29),
            _DummyResult(scalar=31),
        ]
    )
    request = _multipart_request(
        dataset_type="licitacion",
        filename="lic_2026-4.csv",
        payload=LICITACION_CSV.encode("utf-8"),
    )

    payload = _run_async(
        manual_uploads.preflight_manual_csv(
            request=request,
            db=session,
            settings=_settings(root=tmp_path, max_bytes=5 * 1024 * 1024),
        )
    )

    assert payload["dataset_type"] == "licitacion"
    assert payload["original_filename"] == "lic_2026-4.csv"
    assert payload["row_count"] == 1
    assert payload["file_hash_sha256"] == duplicate_hash
    assert payload["duplicate_source_file"]["file_hash_sha256"] == duplicate_hash
    assert payload["dataset_summary"]["source_files_count"] == 7
    assert payload["upload_limits"]["max_size_bytes"] == 5 * 1024 * 1024
    assert session.execute_calls == 9
    assert session.add_calls == 0
    assert session.commit_calls == 0
    assert session.rollback_calls == 0


def test_process_and_status_endpoints_use_single_use_preflight_token(tmp_path: Path) -> None:
    preflight = build_manual_csv_preflight(
        dataset_type="orden_compra",
        original_filename="2026-4.csv",
        payload=ORDEN_COMPRA_CSV.encode("utf-8"),
        intake_root=tmp_path,
        max_bytes=1024 * 1024,
        content_type="text/csv",
    )
    process_session = _DummySession([_DummyResult(rows=[None])])
    original_pipeline_runner = manual_uploads._run_manual_upload_pipeline
    manual_uploads._run_manual_upload_pipeline = lambda **_kwargs: {  # type: ignore[assignment]
        "processed_rows": 1,
        "accepted_rows": 1,
        "inserted_delta_rows": 1,
        "duplicate_existing_rows": 0,
        "rejected_rows": 0,
        "normalized_rows": 4,
        "silver_rows": 6,
        "normalized_inserted_delta_rows": 4,
        "silver_inserted_delta_rows": 6,
        "raw_ingest": {
            "processed_rows": 1,
            "accepted_rows": 1,
            "inserted_delta_rows": 1,
            "existing_or_updated_rows": 0,
            "rejected_rows": 0,
        },
        "entity_metrics": {
            "ordenes_compra": {"inserted_delta_rows": 1},
            "ordenes_compra_items": {"inserted_delta_rows": 2},
            "buyers": {"inserted_delta_rows": 1},
            "silver_purchase_order": {"inserted_delta_rows": 3},
            "silver_purchase_order_line": {"inserted_delta_rows": 3},
        },
    }

    try:
        process_payload = manual_uploads.process_manual_csv(
            file_token=preflight.file_token,
            db=process_session,
            settings=_settings(root=tmp_path, max_bytes=1024 * 1024),
        )
    finally:
        manual_uploads._run_manual_upload_pipeline = original_pipeline_runner  # type: ignore[assignment]

    assert process_payload["status"] == "completed"
    assert process_payload["terminal_state"] is True
    assert process_payload["telemetry"]["processed_rows"] == 1
    assert process_payload["telemetry"]["normalized_rows"] == 4
    assert process_payload["telemetry"]["silver_rows"] == 6
    assert process_payload["source_file"]["file_hash_sha256"] == preflight.file_hash_sha256
    assert process_session.execute_calls == 1
    assert process_session.add_calls == 4
    assert process_session.commit_calls == 2
    assert process_session.rollback_calls == 0

    metadata = json.loads(Path(preflight.metadata_path).read_text(encoding="utf-8"))
    assert metadata["consumed_job_id"] == process_payload["job_id"]
    assert metadata["consumed_at"] is not None

    with pytest.raises(manual_uploads.HTTPException) as exc_info:
        manual_uploads.process_manual_csv(
            file_token=preflight.file_token,
            db=_DummySession([]),
            settings=_settings(root=tmp_path, max_bytes=1024 * 1024),
        )

    assert exc_info.value.status_code == 409
    assert "already consumed" in str(exc_info.value.detail).lower()

    status_job_id = UUID(process_payload["job_id"])
    status_source = SimpleNamespace(
        id=uuid4(),
        dataset_type=process_payload["dataset_type"],
        file_name=process_payload["canonical_filename"],
        file_path=process_payload["source_file"]["file_path"],
        file_hash_sha256=process_payload["file_hash_sha256"],
        status="registered",
        registered_at=datetime.now(UTC),
        source_meta={"manual_upload": process_payload},
        file_size_bytes=preflight.file_size_bytes,
    )
    status_run = SimpleNamespace(
        id=status_job_id,
        run_key=process_payload["pipeline_run"]["run_key"],
        dataset_type=process_payload["dataset_type"],
        status="completed",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        error_summary=None,
        source_file_id=status_source.id,
        config={
            "file_token": preflight.file_token,
            "telemetry": process_payload["telemetry"],
            "original_filename": preflight.original_filename,
            "canonical_filename": preflight.canonical_filename,
            "file_hash_sha256": preflight.file_hash_sha256,
        },
    )
    status_step = SimpleNamespace(
        id=uuid4(),
        run_id=status_job_id,
        step_name=manual_uploads.MANUAL_UPLOAD_STEP_NAME,
        status="completed",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        rows_in=1,
        rows_out=0,
        rows_rejected=0,
        error_details={},
    )
    status_batch = SimpleNamespace(
        id=uuid4(),
        source_file_id=status_source.id,
        batch_key=process_payload["ingestion_batch"]["batch_key"],
        status="completed",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        total_rows=1,
        loaded_rows=1,
        rejected_rows=0,
    )
    status_session = _DummySession(
        [
            _DummyResult(rows=[status_run]),
            _DummyResult(rows=[status_step]),
            _DummyResult(rows=[status_source]),
            _DummyResult(rows=[status_batch]),
        ]
    )

    status_payload = manual_uploads.get_manual_csv_job_status(
        job_id=status_job_id,
        db=status_session,
    )

    assert status_payload["job_id"] == process_payload["job_id"]
    assert status_payload["terminal_state"] is True
    assert status_payload["step"]["status"] == "completed"
    assert status_payload["telemetry"]["processed_rows"] == 1
    assert status_session.execute_calls == 4
