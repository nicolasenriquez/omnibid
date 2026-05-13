from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib import import_module
from inspect import Signature, signature
from types import ModuleType
from typing import Any

import pytest


def _load_module(module_path: str) -> ModuleType:
    try:
        return import_module(module_path)
    except ModuleNotFoundError as exc:
        pytest.fail(
            f"Missing required module '{module_path}'. "
            "Implement backend queue substrate tasks before enabling this test slice."
        )
        raise AssertionError("unreachable") from exc


def _require_callable(module: ModuleType, name: str) -> Signature:
    target = getattr(module, name, None)
    assert callable(target), f"{module.__name__}.{name} must be callable"
    return signature(target)


class _MappingResult:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    def mappings(self) -> "_MappingResult":
        return self

    def first(self) -> dict[str, Any] | None:
        return self._row


class _DummySession:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row
        self.update_params: dict[str, Any] | None = None

    def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _MappingResult:
        normalized = str(stmt).upper()
        if "SELECT ATTEMPTS, MAX_ATTEMPTS" in normalized:
            return _MappingResult(self._row)
        if "UPDATE PIPELINE_JOBS" in normalized and params is not None:
            self.update_params = params
            return _MappingResult(None)
        return _MappingResult(None)


def test_queue_contract_exposes_deterministic_claim_order_fields() -> None:
    queue = _load_module("backend.pipeline.load.queue")
    fields = getattr(queue, "CLAIM_ORDER_FIELDS", None)
    assert fields == ("priority", "available_at", "created_at", "id")


def test_claim_next_job_contract_includes_atomic_claim_inputs() -> None:
    queue = _load_module("backend.pipeline.load.queue")
    sig = _require_callable(queue, "claim_next_job")
    assert "session" in sig.parameters
    assert "worker_id" in sig.parameters
    assert "claim_time" in sig.parameters


def test_claim_next_job_contract_exposes_skip_locked_semantics() -> None:
    queue = _load_module("backend.pipeline.load.queue")
    claim_sql = getattr(queue, "CLAIM_NEXT_JOB_SQL", "")
    normalized = str(claim_sql).upper()
    assert "FOR UPDATE SKIP LOCKED" in normalized


def test_retry_schedule_is_deterministic_from_attempt_count() -> None:
    queue = _load_module("backend.pipeline.load.queue")
    _require_callable(queue, "compute_retry_available_at")
    start = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    next_at = queue.compute_retry_available_at(
        failure_at=start,
        attempts=1,
        retry_delay_seconds=120,
    )
    assert next_at == start + timedelta(seconds=120)


def test_retry_state_transitions_have_bounded_terminal_path() -> None:
    queue = _load_module("backend.pipeline.load.queue")
    _require_callable(queue, "resolve_failure_state")
    state, available_at = queue.resolve_failure_state(
        attempts=2,
        max_attempts=2,
        failure_at=datetime(2026, 5, 7, 10, 0, tzinfo=UTC),
        retry_delay_seconds=120,
    )
    assert state == "dead_letter"
    assert available_at is None


def test_retry_state_transitions_keep_future_available_at_when_retryable() -> None:
    queue = _load_module("backend.pipeline.load.queue")
    state, available_at = queue.resolve_failure_state(
        attempts=1,
        max_attempts=2,
        failure_at=datetime(2026, 5, 7, 10, 0, tzinfo=UTC),
        retry_delay_seconds=120,
    )
    assert state == "retry_scheduled"
    assert available_at == datetime(2026, 5, 7, 10, 2, tzinfo=UTC)


def test_mark_job_failure_honors_per_job_max_attempts() -> None:
    queue = _load_module("backend.pipeline.load.queue")
    session = _DummySession({"attempts": 2, "max_attempts": 2})
    state = queue.mark_job_failure(
        session,
        job_id="job-1",
        error_message="transient",
        retry_delay_seconds=120,
        max_attempts=5,
        retryable=True,
        failure_at=datetime(2026, 5, 7, 10, 0, tzinfo=UTC),
    )
    assert state == "dead_letter"
    assert session.update_params is not None
    assert session.update_params["status"] == "dead_letter"
    assert session.update_params["available_at"] is None


def test_mark_job_failure_uses_fallback_max_attempts_when_row_value_missing() -> None:
    queue = _load_module("backend.pipeline.load.queue")
    session = _DummySession({"attempts": 1, "max_attempts": None})
    state = queue.mark_job_failure(
        session,
        job_id="job-1",
        error_message="transient",
        retry_delay_seconds=120,
        max_attempts=2,
        retryable=True,
        failure_at=datetime(2026, 5, 7, 10, 0, tzinfo=UTC),
    )
    assert state == "retry_scheduled"
    assert session.update_params is not None
    assert session.update_params["status"] == "retry_scheduled"
    assert session.update_params["available_at"] == datetime(2026, 5, 7, 10, 2, tzinfo=UTC)


def test_ingestion_unit_lineage_contract_persists_source_metadata() -> None:
    ingestion_units = _load_module("backend.pipeline.orchestration.worker")
    _require_callable(ingestion_units, "build_ingestion_unit_payload")
    payload = ingestion_units.build_ingestion_unit_payload(
        job={
            "id": "job-1",
            "source_kind": "manual_csv",
            "dataset_type": "licitacion",
            "payload": {"source_file_id": "file-1"},
        },
        metadata={"rows_read": 10},
    )

    assert payload["job_id"] == "job-1"
    assert payload["source_kind"] == "manual_csv"
    assert payload["dataset_type"] == "licitacion"
    assert payload["source_file_id"] == "file-1"
    assert payload["metadata"]["rows_read"] == 10


def test_ingestion_unit_lineage_contract_fails_fast_on_missing_source_kind() -> None:
    ingestion_units = _load_module("backend.pipeline.orchestration.worker")
    _require_callable(ingestion_units, "build_ingestion_unit_payload")
    with pytest.raises(ValueError, match="source_kind"):
        ingestion_units.build_ingestion_unit_payload(
            job={
                "id": "job-1",
                "source_kind": "",
                "dataset_type": "licitacion",
                "payload": {},
            },
            metadata={},
        )


def test_ingestion_unit_lineage_contract_fails_fast_on_missing_dataset_type() -> None:
    ingestion_units = _load_module("backend.pipeline.orchestration.worker")
    _require_callable(ingestion_units, "build_ingestion_unit_payload")
    with pytest.raises(ValueError, match="dataset_type"):
        ingestion_units.build_ingestion_unit_payload(
            job={
                "id": "job-1",
                "source_kind": "manual_csv",
                "dataset_type": "",
                "payload": {},
            },
            metadata={},
        )


def test_worker_completion_uses_checkpoint_source_file_id_and_fresh_finished_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = _load_module("backend.pipeline.orchestration.worker")
    claim_time = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    finished_at = datetime(2026, 5, 7, 10, 5, tzinfo=UTC)
    job = {
        "id": "11111111-1111-1111-1111-111111111111",
        "job_type": "csv_ingest_file",
        "source_checkpoint_id": "22222222-2222-2222-2222-222222222222",
        "source_kind": "manual_csv",
        "dataset_type": "licitacion",
        "payload": {},
    }
    source_checkpoint = {"source_file_id": "33333333-3333-3333-3333-333333333333"}
    captured: dict[str, Any] = {}

    def fake_create_ingestion_unit(
        session: Any,
        *,
        job: dict[str, Any],
        source_file_id: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        captured["source_file_id"] = source_file_id
        captured["metadata"] = dict(metadata or {})
        return type("FakeIngestionUnit", (), {"id": "44444444-4444-4444-4444-444444444444"})()

    def fake_mark_ingestion_unit_completed(
        session: Any,
        *,
        ingestion_unit_id: Any,
        metadata_patch: dict[str, Any] | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        captured["unit_completed_at"] = finished_at
        captured["metadata_patch"] = dict(metadata_patch or {})

    def fake_mark_source_checkpoint_consumed(
        session: Any,
        *,
        checkpoint_id: Any,
        consumed_job_id: Any,
        consumed_at: datetime | None = None,
    ) -> None:
        captured["consumed_at"] = consumed_at

    def fake_mark_job_completed(
        session: Any,
        *,
        job_id: Any,
        finished_at: datetime | None = None,
    ) -> None:
        captured["job_completed_at"] = finished_at

    monkeypatch.setattr(worker, "_utc_now", lambda: finished_at)
    monkeypatch.setattr(worker.queue, "claim_next_job", lambda *args, **kwargs: job)
    monkeypatch.setattr(worker.queue, "fetch_source_checkpoint", lambda *args, **kwargs: source_checkpoint)
    monkeypatch.setattr(worker, "create_ingestion_unit", fake_create_ingestion_unit)
    monkeypatch.setattr(worker, "mark_ingestion_unit_completed", fake_mark_ingestion_unit_completed)
    monkeypatch.setattr(worker, "mark_ingestion_unit_failed", lambda *args, **kwargs: pytest.fail("unexpected failure"))
    monkeypatch.setattr(worker, "mark_source_checkpoint_consumed", fake_mark_source_checkpoint_consumed)
    monkeypatch.setattr(worker.queue, "mark_job_completed", fake_mark_job_completed)
    monkeypatch.setattr(worker.queue, "mark_job_failure", lambda *args, **kwargs: pytest.fail("unexpected failure"))

    result = worker.run_worker_once(
        object(),  # session is unused by the monkeypatched path
        worker_id="worker-1",
        handlers={"csv_ingest_file": lambda **kwargs: {"rows_read": 1}},
        retry_delay_seconds=120,
        max_attempts=2,
        claim_time=claim_time,
    )

    assert result.action == "completed"
    assert captured["source_file_id"] == source_checkpoint["source_file_id"]
    assert captured["unit_completed_at"] == finished_at
    assert captured["consumed_at"] == finished_at
    assert captured["job_completed_at"] == finished_at


def test_worker_retryable_failure_uses_fresh_failure_at(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = _load_module("backend.pipeline.orchestration.worker")
    claim_time = datetime(2026, 5, 7, 10, 0, tzinfo=UTC)
    failed_at = datetime(2026, 5, 7, 10, 6, tzinfo=UTC)
    job = {
        "id": "11111111-1111-1111-1111-111111111111",
        "job_type": "csv_ingest_file",
        "source_checkpoint_id": "22222222-2222-2222-2222-222222222222",
        "source_kind": "manual_csv",
        "dataset_type": "licitacion",
        "payload": {},
    }
    source_checkpoint = {"source_file_id": "33333333-3333-3333-3333-333333333333"}
    captured: dict[str, Any] = {}

    def fake_create_ingestion_unit(
        session: Any,
        *,
        job: dict[str, Any],
        source_file_id: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        captured["source_file_id"] = source_file_id
        return type("FakeIngestionUnit", (), {"id": "44444444-4444-4444-4444-444444444444"})()

    def fake_mark_ingestion_unit_failed(
        session: Any,
        *,
        ingestion_unit_id: Any,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None:
        captured["unit_failed_at"] = failed_at

    def fake_mark_job_failure(
        session: Any,
        *,
        job_id: Any,
        error_message: str,
        retry_delay_seconds: int,
        max_attempts: int,
        retryable: bool,
        failure_at: datetime | None = None,
    ) -> str:
        captured["job_failure_at"] = failure_at
        captured["retryable"] = retryable
        return "retry_scheduled"

    monkeypatch.setattr(worker, "_utc_now", lambda: failed_at)
    monkeypatch.setattr(worker.queue, "claim_next_job", lambda *args, **kwargs: job)
    monkeypatch.setattr(worker.queue, "fetch_source_checkpoint", lambda *args, **kwargs: source_checkpoint)
    monkeypatch.setattr(worker, "create_ingestion_unit", fake_create_ingestion_unit)
    monkeypatch.setattr(worker, "mark_ingestion_unit_completed", lambda *args, **kwargs: pytest.fail("unexpected success"))
    monkeypatch.setattr(worker, "mark_ingestion_unit_failed", fake_mark_ingestion_unit_failed)
    monkeypatch.setattr(worker, "mark_source_checkpoint_consumed", lambda *args, **kwargs: pytest.fail("unexpected success"))
    monkeypatch.setattr(worker.queue, "mark_job_completed", lambda *args, **kwargs: pytest.fail("unexpected success"))
    monkeypatch.setattr(worker.queue, "mark_job_failure", fake_mark_job_failure)

    def retryable_handler(**kwargs: Any) -> Any:
        raise worker.RetryableJobError("transient")

    result = worker.run_worker_once(
        object(),  # session is unused by the monkeypatched path
        worker_id="worker-1",
        handlers={"csv_ingest_file": retryable_handler},
        retry_delay_seconds=120,
        max_attempts=2,
        claim_time=claim_time,
    )

    assert result.action == "failed"
    assert result.job_status == "retry_scheduled"
    assert captured["source_file_id"] == source_checkpoint["source_file_id"]
    assert captured["unit_failed_at"] == failed_at
    assert captured["job_failure_at"] == failed_at
    assert captured["retryable"] is True
