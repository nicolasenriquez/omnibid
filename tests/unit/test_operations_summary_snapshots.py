from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api.routers import operations
from backend.models.operational import DatasetSummarySnapshot


class _DummyResult:
    def __init__(
        self,
        *,
        scalar_value: int | None = None,
        scalar_or_none_value: Any = None,
    ) -> None:
        self._scalar_value = scalar_value
        self._scalar_or_none_value = scalar_or_none_value

    def scalar_one(self) -> int:
        if self._scalar_value is None:
            raise AssertionError("scalar_one requested but scalar_value is not set")
        return self._scalar_value

    def scalar_one_or_none(self) -> Any:
        return self._scalar_or_none_value


class _DummySession:
    def __init__(self, responses: list[_DummyResult | Exception]) -> None:
        self._responses = responses
        self.execute_calls = 0
        self.rollback_calls = 0
        self.add_calls = 0
        self.commit_calls = 0
        self.refresh_calls = 0

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

    def refresh(self, obj: DatasetSummarySnapshot) -> None:
        self.refresh_calls += 1
        if obj.id is None:
            obj.id = uuid4()
        if obj.generated_at is None:
            obj.generated_at = datetime.now(UTC)

    def rollback(self) -> None:
        self.rollback_calls += 1


def _snapshot(
    *,
    source_files_count: int = 1,
    age_seconds: int = 60,
) -> DatasetSummarySnapshot:
    snapshot = DatasetSummarySnapshot(
        refresh_mode="fresh",
        status="success",
        source_files_count=source_files_count,
        raw_licitaciones_count=2,
        raw_ordenes_compra_count=3,
        normalized_licitaciones_count=4,
        normalized_licitacion_items_count=5,
        normalized_ofertas_count=6,
        normalized_ordenes_compra_count=7,
        normalized_ordenes_compra_items_count=8,
        error_details={},
    )
    snapshot.id = uuid4()
    snapshot.generated_at = datetime.now(UTC) - timedelta(seconds=age_seconds)
    return snapshot


def test_cached_mode_uses_latest_snapshot_without_recount() -> None:
    existing_snapshot = _snapshot(source_files_count=11, age_seconds=30)
    session = _DummySession([_DummyResult(scalar_or_none_value=existing_snapshot)])

    payload = operations.datasets_summary(mode="cached", max_age_seconds=300, db=session)

    assert payload["source_files"] == 11
    assert payload["summary_meta"]["refresh_status"] == "not_requested"
    assert payload["summary_meta"]["snapshot_refresh_mode"] == "fresh"
    assert payload["summary_meta"]["strategy"] == "persisted_success_snapshot"
    assert session.execute_calls == 1
    assert session.add_calls == 0
    assert session.commit_calls == 0


def test_cached_mode_bootstraps_snapshot_when_missing() -> None:
    responses: list[_DummyResult | Exception] = [_DummyResult(scalar_or_none_value=None)]
    responses.extend(_DummyResult(scalar_value=value) for value in [10, 20, 30, 40, 50, 60, 70, 80])
    session = _DummySession(responses)

    payload = operations.datasets_summary(mode="cached", max_age_seconds=300, db=session)

    assert payload["source_files"] == 10
    assert payload["raw_rows"]["licitaciones"] == 20
    assert payload["summary_meta"]["refresh_status"] == "not_requested"
    assert payload["summary_meta"]["snapshot_refresh_mode"] == "bootstrap"
    assert session.execute_calls == 9
    assert session.add_calls == 1
    assert session.commit_calls == 1
    assert session.refresh_calls == 1
    assert session.rollback_calls == 0


def test_fresh_mode_persists_new_snapshot() -> None:
    fixed_now = datetime(2026, 4, 22, 12, 0, 0, tzinfo=UTC)

    class _FixedDateTime:
        @staticmethod
        def now(_tz: object) -> datetime:
            return fixed_now

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(operations, "datetime", _FixedDateTime)

    responses: list[_DummyResult | Exception] = [_DummyResult(scalar_or_none_value=_snapshot())]
    responses.extend(_DummyResult(scalar_value=value) for value in [100, 200, 300, 400, 500, 600, 700, 800])
    session = _DummySession(responses)

    try:
        payload = operations.datasets_summary(mode="fresh", max_age_seconds=300, db=session)
    finally:
        monkeypatch.undo()

    assert payload["source_files"] == 100
    assert payload["summary_meta"]["refresh_status"] == "refreshed"
    assert payload["summary_meta"]["snapshot_refresh_mode"] == "fresh"
    assert payload["summary_meta"]["generated_at"] == fixed_now.isoformat()
    assert payload["summary_meta"]["snapshot_age_seconds"] == 0
    assert payload["summary_meta"]["is_stale"] is False
    assert session.execute_calls == 9
    assert session.add_calls == 1
    assert session.commit_calls == 1
    assert session.rollback_calls == 0


def test_fresh_mode_failure_falls_back_to_last_successful_snapshot() -> None:
    existing_snapshot = _snapshot(source_files_count=33, age_seconds=400)
    session = _DummySession(
        [
            _DummyResult(scalar_or_none_value=existing_snapshot),
            RuntimeError("count query failed"),
            _DummyResult(scalar_or_none_value=existing_snapshot),
        ]
    )

    payload = operations.datasets_summary(mode="fresh", max_age_seconds=300, db=session)

    assert payload["source_files"] == 33
    assert payload["summary_meta"]["refresh_status"] == "failed_using_last_successful_snapshot"
    assert payload["summary_meta"]["refresh_error"] == "RuntimeError"
    assert payload["summary_meta"]["is_stale"] is True
    assert session.execute_calls == 3
    assert session.rollback_calls == 1
    assert session.add_calls == 0
    assert session.commit_calls == 0


def test_fresh_mode_failure_without_snapshot_raises_503() -> None:
    session = _DummySession(
        [
            _DummyResult(scalar_or_none_value=None),
            RuntimeError("count query failed"),
            _DummyResult(scalar_or_none_value=None),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        operations.datasets_summary(mode="fresh", max_age_seconds=300, db=session)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == operations.SUMMARY_REFRESH_FAILED_NO_FALLBACK_DETAIL
    assert session.rollback_calls == 1
